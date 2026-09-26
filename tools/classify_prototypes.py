#!/usr/bin/env python3
"""Раскладывает карточки ЕГЭ по русскому на прототипы внутри каждого задания.

Для каждого номера отправляет в Gemini все его карточки и просит выделить
3–6 типовых подтипов (как в каталогах «по прототипам») и отнести к ним
каждую карточку. Результат — data/source/ege-rus-prototypes.json, его
читает build_packs.py.

Запуск (ключ только из окружения, в файлы не пишется):
  GEMINI_KEY=… python3 tools/classify_prototypes.py [номер задания …]
"""
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'data' / 'source'
OUT = SRC / 'ege-rus-prototypes.json'
MODELS = ['gemini-flash-latest', 'gemini-flash-lite-latest']

SYSTEM = """Ты методист ЕГЭ по русскому языку. Тебе дают все тренировочные карточки
одного задания ЕГЭ. Раздели их на прототипы — устойчивые подтипы этого задания,
как в каталогах заданий «по прототипам» (например, для задания 15: «Н/НН в
отымённых прилагательных», «Н/НН в причастиях и отглагольных прилагательных»,
«Н/НН в кратких формах»).
Правила:
- 2–6 прототипов; если карточек меньше 10 — 1–3.
- Название прототипа — до 45 символов, понятное ученику, без номера задания.
- tip — одно предложение: главный приём, как решать карточки этого прототипа.
- Каждую карточку отнеси ровно к одному прототипу.
- Карточки-вопросы по теории (что такое…, как называется…) — отдельный прототип
  «Теория и термины», если их больше трёх.
Верни только JSON:
{"prototypes":[{"id":"p1","title":"…","tip":"…"}],"assign":{"0":"p1","1":"p2"}}"""


sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_packs import exam_task  # noqa: E402


def card_ids():
    """Те же id, что даёт build_packs.py для набора ege-rus."""
    bank = json.loads((SRC / 'sotka-bank.json').read_text('utf-8'))
    out = {}
    for i, x in enumerate(bank):
        cid = x.get('id') or f'rus-{x["k"]}-{x["task"]}-{i}'
        out.setdefault(exam_task(x), []).append((cid, x))
    return out


def describe(x):
    q = ' '.join(x['q'].split())[:220]
    if x['k'] == 'mc':
        ans = next((o['t'] for o in x['o'] if o['id'] == x['c']), '')
    elif x['k'] == 'multi':
        ans = ', '.join(o['t'] for o in x['o'] if o['id'] in x['cs'])
    elif x['k'] == 'flip':
        ans = x['a']
    else:
        ans = 'соответствие'
    return f'{q} || ответ: {" ".join(str(ans).split())[:80]}'


def ask(key, text):
    payload = json.dumps({
        'systemInstruction': {'parts': [{'text': SYSTEM}]},
        'contents': [{'role': 'user', 'parts': [{'text': text}]}],
        'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 16384, 'responseMimeType': 'application/json'},
    }).encode()
    for model in MODELS:
        for wait in (0, 3, 8, 20):
            time.sleep(wait)
            req = urllib.request.Request(
                f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                data=payload, headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = json.load(r)
                return json.loads(''.join(p.get('text', '') for p in data['candidates'][0]['content']['parts']))
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 503):
                    raise
            except (TimeoutError, urllib.error.URLError, json.JSONDecodeError, KeyError):
                pass
    raise RuntimeError('Gemini не ответил')


def classify(key, task, items):
    text = f'Задание {task}. Карточки ({len(items)}):\n' + '\n'.join(f'{i}. {describe(x)}' for i, (_, x) in enumerate(items))
    r = ask(key, text)
    protos = [{'id': f't{task}-{p["id"]}', 'title': p['title'].strip(), 'tip': p.get('tip', '').strip()}
              for p in r['prototypes']]
    valid = {p['id'] for p in protos}
    assign = {}
    for i, (cid, _) in enumerate(items):
        pid = f't{task}-{r["assign"].get(str(i), "")}'
        assign[cid] = pid if pid in valid else protos[0]['id']
    missing = sum(1 for i in range(len(items)) if str(i) not in r['assign'])
    return {'prototypes': protos, 'assign': assign}, missing


def main():
    key = os.environ.get('GEMINI_KEY')
    if not key:
        sys.exit('Нужен GEMINI_KEY в окружении')
    result = json.loads(OUT.read_text('utf-8')) if OUT.exists() else {}
    tasks = card_ids()
    only = {int(a) for a in sys.argv[1:]}
    todo = [t for t in sorted(tasks) if not only or t in only]
    lock = threading.Lock()

    def run(task):
        info, missing = classify(key, task, tasks[task])
        with lock:
            result[str(task)] = info
            OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', 'utf-8')
            counts = {p['title']: sum(1 for v in info['assign'].values() if v == p['id']) for p in info['prototypes']}
            print(f'{task}: {counts}' + (f' (без ответа ИИ: {missing})' if missing else ''), flush=True)

    # Несколько заданий параллельно: Gemini отвечает по 1–3 минуты на задание
    with ThreadPoolExecutor(max_workers=4) as pool:
        for f in [pool.submit(run, t) for t in todo]:
            try:
                f.result()
            except Exception as e:  # одно упавшее задание не должно ронять остальные
                print('ошибка:', e, flush=True)


if __name__ == '__main__':
    main()
