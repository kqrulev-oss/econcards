#!/usr/bin/env python3
"""Находит ответы к заданиям банка ФИПИ и проверяет их на сайте ФИПИ.

В открытом банке ответов нет, но есть проверка (solve.php): «3» — верно,
«2» — неверно. В набор попадает только ответ, который ФИПИ признал верным.

  • выбор ответа — перебираем варианты, пока ФИПИ не скажет «верно»;
  • краткий ответ — кандидаты из файла (--candidates) или от Gemini (GEMINI_KEY),
    каждый проверяется на сайте; решение Gemini к подтверждённому ответу
    становится разбором карточки;
  • развёрнутый ответ ФИПИ не проверяет — с --solutions Gemini пишет решение-образец
    (в карточке помечено как решение ИИ).

Запуск (ключ только из окружения, в файлы не пишется):
  python3 tools/fipi_answers.py                     # все скачанные предметы ЕГЭ, только выбор ответа
  GEMINI_KEY=… python3 tools/fipi_answers.py physics --ai
  python3 tools/fipi_answers.py math_prof --candidates my.json   # {"40B442": ["29"], …}

Результат — data/source/fipi/<exam>-<предмет>-answers.json:
  {qid: {"a": "29", "any": 1?, "e": "решение"?, "no": ["неверные попытки"]?, "sol": "решение ИИ"?}}
  any — порядок цифр в ответе не важен (ФИПИ принял и перестановку).
"""
import argparse
import base64
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fipi_bank import OUT, ROOT, SUBJECTS, Client, FipiError  # noqa: E402

MODELS = ['gemini-flash-latest', 'gemini-flash-lite-latest']
SOLVE = """Ты решаешь задание {exam} по предмету «{subject}» из открытого банка ФИПИ.
Реши внимательно, проверь вычисления. Ответ запиши так, как его вписывают в бланк ответов:
- число — цифрами, десятичная дробь через запятую, без единиц измерения и пробелов;
- последовательность цифр — подряд, без пробелов и запятых;
- слово или слова — как требует задание, без пробелов и знаков препинания, если не сказано иное.
Решение пиши без LaTeX; формулы со степенями и дробями оборачивай в ⟦ ⟧, степени внутри — x^2 или x^{n+1}.
Верни только JSON: {{"answer": "…", "alt": ["другой возможный ответ, если сомневаешься"], "solution": "краткое решение, 2–8 строк"}}"""
WRITE = """Ты эксперт ЕГЭ по предмету «{subject}». Напиши образцовое решение задания с развёрнутым
ответом так, как его оценил бы эксперт на максимальный балл: по шагам, кратко, без LaTeX.
Формулы со степенями оборачивай в ⟦ ⟧, степени внутри — x^2 или x^{n+1}, дроби — a/b.
Верни только JSON: {{"solution": "…"}}"""


def gemini(key, system, task, model=None):
    parts = [{'text': task['text']}]
    for src in task.get('img', [])[:6]:
        path = ROOT / src
        if path.exists():
            mime = 'image/' + {'jpg': 'jpeg', 'svg': 'svg+xml'}.get(path.suffix[1:].lower(), path.suffix[1:].lower())
            parts.append({'inlineData': {'mimeType': mime, 'data': base64.b64encode(path.read_bytes()).decode()}})
    for i, o in enumerate(task.get('opts', [])):
        parts.append({'text': f'Вариант {o["id"]}: {o["text"]}'})
    payload = json.dumps({
        'systemInstruction': {'parts': [{'text': system}]},
        'contents': [{'role': 'user', 'parts': parts}],
        'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 8192, 'responseMimeType': 'application/json'},
    }).encode()
    for m in ([model] if model else MODELS):
        for wait in (0, 3, 8, 20):
            time.sleep(wait)
            req = urllib.request.Request(
                f'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent',
                data=payload, headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = json.load(r)
                return json.loads(''.join(p.get('text', '') for p in data['candidates'][0]['content']['parts']))
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 503):
                    raise
            except (TimeoutError, urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError):
                pass
    return None


def norm(ans):
    """Ответ в формате бланка: без пробелов, десятичная запятая, без точки в конце."""
    s = re.sub(r'\s+', '', str(ans or '')).rstrip('.')
    if re.fullmatch(r'-?\d+\.\d+', s):
        s = s.replace('.', ',')
    return s.replace('−', '-')


class Checker:
    """Проверка ответов на сайте ФИПИ; сессию прогревает сам и обновляет при сбросе."""

    def __init__(self, exam, key, insecure):
        self.client = Client(exam, insecure=insecure, delay=0.5)
        self.proj = SUBJECTS[exam][key][1]
        self.lock = threading.Lock()
        self.warm = False

    def warmup(self):
        self.client.fetch('index.php')
        self.client.fetch('index.php', {'proj': self.proj})
        self.client.fetch('questions.php', {'proj': self.proj, 'page': 0, 'pagesize': 5})
        self.warm = True

    def check(self, guid, answer):
        with self.lock:
            for _ in range(3):
                if not self.warm:
                    self.warmup()
                r = self.client.fetch('solve.php', data={'proj': self.proj, 'guid': guid, 'answer': answer,
                                                         'chkcode': '', 'ajax': '1'}).strip()
                if r in ('0', '1', '2', '3'):
                    return r
                self.warm = False  # «Пользователь не определён» — сессия истекла
            return r


def solve_subject(exam, key, args, gem_key):
    src = OUT / f'{exam}-{key}.json'
    if not src.exists():
        print(f'{exam}-{key}: нет {src.relative_to(ROOT)}, сначала tools/fipi_bank.py')
        return
    data = json.loads(src.read_text('utf-8'))
    out = OUT / f'{exam}-{key}-answers.json'
    answers = json.loads(out.read_text('utf-8')) if out.exists() else {}
    cands = json.loads(Path(args.candidates).read_text('utf-8')) if args.candidates else {}
    checker = Checker(exam, key, args.insecure)
    lock = threading.RLock()  # ответы меняются из нескольких потоков
    stats = {'select': 0, 'short': 0, 'full': 0, 'miss': 0}
    done = [0]

    def save():
        with lock:
            out.write_text(json.dumps(answers, ensure_ascii=False, indent=0, sort_keys=True) + '\n', 'utf-8')

    def verify(t, tries, extra=None):
        """Первый подтверждённый ФИПИ ответ из списка; неверные запоминаем, чтобы не повторять."""
        with lock:
            return _verify(t, tries, extra)

    def _verify(t, tries, extra):
        rec = answers.get(t['id'], {})
        try:
            return _try(t, tries, extra, rec)
        finally:
            if rec:
                answers[t['id']] = rec

    def _try(t, tries, extra, rec):
        for a in tries:
            a = norm(a)
            if not a or a in rec.get('no', []):
                continue
            r = checker.check(t['guid'], a)
            if r == '3':
                rec.pop('no', None)
                rec['a'] = a
                if extra:
                    rec.update(extra)
                # Ответ-набор цифр («запишите номера…»): если ФИПИ принимает перестановку, порядок не важен
                if (re.fullmatch(r'\d{2,}', a) and len(set(a)) == len(a) and re.search(r'цифр|номер', t['text'], re.I)
                        and checker.check(t['guid'], a[::-1]) == '3'):
                    rec['any'] = 1
                return True
            if r == '2':
                rec.setdefault('no', []).append(a)
        return False

    todo = [t for t in data['tasks'] if not t.get('media') and 'a' not in answers.get(t['id'], {})]
    if args.limit:
        todo = todo[:args.limit]

    def run(t):
        if t['kind'] == 'select' and t.get('opts'):
            if verify(t, [o['id'] for o in t['opts']]):
                stats['select'] += 1
        elif t['kind'] == 'short':
            ok = verify(t, cands.get(t['id'], []))
            if not ok and args.ai and gem_key:
                r = gemini(gem_key, SOLVE.format(exam='ЕГЭ' if exam == 'ege' else 'ОГЭ', subject=data['title']), t, args.model)
                if r and r.get('answer'):
                    ok = verify(t, [r['answer']] + list(r.get('alt') or [])[:2],
                                {'e': r['solution'].strip()} if r.get('solution') else None)
            stats['short' if ok else 'miss'] += 1
        elif t['kind'] == 'full' and args.solutions and gem_key and not answers.get(t['id'], {}).get('sol'):
            r = gemini(gem_key, WRITE.format(subject=data['title']), t, args.model)
            if r and r.get('solution'):
                with lock:
                    answers.setdefault(t['id'], {})['sol'] = r['solution'].strip()
                    stats['full'] += 1
        with lock:
            done[0] += 1
            if done[0] % 20 == 0:
                save()
                print(f'  {exam}-{key}: {done[0]}/{len(todo)} {stats}', flush=True)

    # Gemini думает долго — несколько заданий параллельно; к ФИПИ запросы всё равно по одному
    with ThreadPoolExecutor(max_workers=4 if args.ai or args.solutions else 1) as pool:
        for f in [pool.submit(run, t) for t in todo]:
            try:
                f.result()
            except Exception as e:  # одно упавшее задание не должно ронять остальные
                print('  ошибка:', e, flush=True)
    save()
    have = sum(1 for v in answers.values() if 'a' in v)
    print(f'{exam}-{key}: {stats}, всего с ответом {have} из {len(data["tasks"])} → {out.relative_to(ROOT)}')


def main():
    ap = argparse.ArgumentParser(description='Ответы к банку ФИПИ с проверкой на сайте')
    ap.add_argument('subjects', nargs='*')
    ap.add_argument('--exam', choices=['ege', 'oge'], default='ege')
    ap.add_argument('--ai', action='store_true', help='кандидаты кратких ответов от Gemini (нужен GEMINI_KEY)')
    ap.add_argument('--solutions', action='store_true', help='решения-образцы к развёрнутым заданиям (Gemini)')
    ap.add_argument('--candidates', help='JSON {qid: [ответы]} — свои кандидаты для проверки')
    ap.add_argument('--model', help='модель Gemini вместо списка по умолчанию')
    ap.add_argument('--limit', type=int, default=0, help='не больше N заданий на предмет (для пробы)')
    ap.add_argument('--insecure', action='store_true', help='не проверять сертификат ФИПИ')
    args = ap.parse_args()
    gem_key = os.environ.get('GEMINI_KEY')
    if (args.ai or args.solutions) and not gem_key:
        sys.exit('Для --ai и --solutions нужен GEMINI_KEY в окружении')
    keys = args.subjects or [k for k in SUBJECTS[args.exam] if (OUT / f'{args.exam}-{k}.json').exists()]
    for key in keys:
        try:
            solve_subject(args.exam, key, args, gem_key)
        except FipiError as e:  # найденные ответы уже сохранены, повторный запуск продолжит
            print(f'{args.exam}-{key}: {e}')


if __name__ == '__main__':
    main()
