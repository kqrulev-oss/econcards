#!/usr/bin/env python3
"""Находит ответы к заданиям банка ФИПИ и проверяет их на сайте ФИПИ.

В открытом банке ответов нет, но есть проверка (solve.php): «3» — верно,
«2» — неверно. В набор попадает только ответ, который ФИПИ признал верным.

  • выбор ответа — перебираем варианты, пока ФИПИ не скажет «верно»;
  • краткий ответ — кандидаты из файлов (--candidates, например ответы ChatGPT)
    или от Gemini (GEMINI_KEY), каждый проверяется на сайте; решение к ответу,
    который ФИПИ подтвердил, становится разбором карточки;
  • развёрнутый ответ ФИПИ не проверяет — решение-образец берём из файла или
    от Gemini (--solutions), в карточке оно помечено как решение ИИ.

Запуск (ключ только из окружения, в файлы не пишется):
  python3 tools/fipi_answers.py                     # все скачанные предметы ЕГЭ, только выбор ответа
  GEMINI_KEY=… python3 tools/fipi_answers.py physics --ai

С ChatGPT (или любым другим чатом): выгрузить пачку заданий, отдать чату, проверить ответы.
  python3 tools/fipi_answers.py physics --export 0 > batch.json         # пачка №0, 40 заданий
  python3 tools/fipi_answers.py physics --export 0 --kind full --batch 10   # развёрнутые — пачками поменьше
  python3 tools/fipi_answers.py physics --candidates gpt-*.json
Файл кандидатов: {qid: ["ответ", "запасной"]} или {qid: {"a": [...], "e": "решение", "sol": "решение"}};
  e — решение к первому ответу из a, sol — решение развёрнутого задания. Обёртка ```json не мешает.

Результат — data/source/fipi/<exam>-<предмет>-answers.json:
  {qid: {"a": "29", "any": 1?, "e": "решение"?, "no": ["неверные попытки"]?, "sol": "решение ИИ"?}}
  any — порядок цифр в ответе не важен (ФИПИ принял и перестановку).
"""
import argparse
import base64
import itertools
import json
import os
import queue
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
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


def gemini(key, system, task, model=None, passage=None):
    parts = ([{'text': 'Текст к заданию:\n' + passage}] if passage else []) + [{'text': task['text']}]
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


def choice(t, ans):
    """Ответ-выбор «134», «1, 3, 4» или «2» → номера вариантов по порядку, None — если таких нет."""
    ids = [o['id'] for o in t['opts']]
    s = str(ans).strip()
    single = all(len(i) == 1 for i in ids)
    parts = [x for x in (list(s) if single and not re.search(r'[\s,;]', s) else re.split(r'[\s,;]+', s)) if x]
    if not parts or len(set(parts)) != len(parts) or any(x not in ids for x in parts):
        return None
    if t['kind'] == 'select' and len(parts) != 1:
        return None
    return sorted(parts, key=ids.index)


def wire(t, parts):
    """Как ответ-выбор уходит на сайт: маска «01100» или номер варианта."""
    if t.get('mask'):
        return ''.join('1' if o['id'] in parts else '0' for o in t['opts'])
    return ','.join(parts)


NUMBERS = {'один': 1, 'одно': 1, 'одну': 1, 'два': 2, 'две': 2, 'двух': 2, 'три': 3, 'трёх': 3, 'трех': 3,
           'четыре': 4, 'четырёх': 4}
HOW_MANY = re.compile(r'(?:выберите|найдите|укажите|определите|какие|отметьте)\s+(?:[а-яё]+\s+){0,2}?('
                      + '|'.join(NUMBERS) + r')\b', re.I)


def how_many(text):
    """Сколько вариантов верных, если условие говорит («выберите две реакции», «какие три…»)."""
    m = HOW_MANY.search(text)
    return NUMBERS[m.group(1).lower()] if m else None


def combos(t, seen=None):
    """Перебор ответов с несколькими вариантами: сначала столько, сколько назвало условие,
    иначе — самые частые в предмете размеры ответа (seen: Counter), по умолчанию 2, 3, 1, 4."""
    ids = [o['id'] for o in t['opts']]
    k = how_many(t['text'])
    sizes = [k for k in (2, 3, 1, 4) if k <= len(ids)] + list(range(5, len(ids) + 1))
    if seen:
        sizes.sort(key=lambda x: -seen.get(x, 0))
    if k in sizes:
        sizes = [k] + [x for x in sizes if x != k]
    return [''.join(c) if all(len(i) == 1 for i in ids) else ','.join(c)
            for k in sizes for c in itertools.combinations(ids, k)]


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
                r = self.client.post_fast('solve.php', {'proj': self.proj, 'guid': guid, 'answer': answer,
                                                        'chkcode': '', 'ajax': '1'}).strip()
                if r in ('0', '1', '2', '3'):
                    return r
                self.warm = False  # «Пользователь не определён» — сессия истекла
            return r


def passage(data, t):
    """Общий текст группы задания, если он не само это задание."""
    g = data.get('groups', {}).get(t.get('group')) or {}
    return None if g.get('from') == t['id'] else g.get('text')


def load_candidates(paths):
    """Ответы и решения из файлов: {qid: [ответы]} или {qid: {"a": …, "e": "…", "sol": "…"}}.
    Возвращает {qid: [попытка, …]} — по попытке на файл, решение остаётся при своих ответах."""
    out = {}
    for path in paths or []:
        raw = Path(path).read_text('utf-8').strip()
        raw = re.sub(r'^```\w*\s*|\s*```$', '', raw)  # чаты любят заворачивать JSON в ```json
        try:
            items = json.loads(raw)
        except json.JSONDecodeError as e:
            sys.exit(f'{path}: не JSON ({e}). Попросите чат вернуть только JSON-объект.')
        for qid, v in items.items():
            v = v if isinstance(v, dict) else {'a': v}
            a = v.get('a') or []
            att = {'a': [str(x) for x in (a if isinstance(a, list) else [a]) if str(x).strip()]}
            for k in ('e', 'sol'):
                if str(v.get(k) or '').strip():
                    att[k] = str(v[k]).strip()
            out.setdefault(qid.strip().upper(), []).append(att)
    return out


def load_subject(exam, key):
    src = OUT / f'{exam}-{key}.json'
    if not src.exists():
        sys.exit(f'{exam}-{key}: нет {src.relative_to(ROOT)}, сначала tools/fipi_bank.py')
    out = OUT / f'{exam}-{key}-answers.json'
    return json.loads(src.read_text('utf-8')), out, json.loads(out.read_text('utf-8')) if out.exists() else {}


def export(exam, key, batch, size, kinds):
    """Пачка заданий для чата: без ответа или без решения, без картинок (чат их не видит)."""
    data, _, answers = load_subject(exam, key)
    items = []
    for t in data['tasks']:
        rec = answers.get(t['id'], {})
        if t.get('media') or t.get('img') or t['kind'] not in kinds:
            continue
        if t['kind'] == 'full' and rec.get('sol') or t['kind'] != 'full' and 'a' in rec and 'e' in rec:
            continue
        if t['kind'] in ('select', 'multi') and not t.get('opts'):
            continue
        item = {'id': t['id'], 'type': t['kind'], 'text': t['text']}
        text = passage(data, t)
        if text:
            item['passage'] = text  # общий текст группы заданий
        if t['kind'] in ('select', 'multi'):
            item['options'] = [{'id': o['id'], 'text': o['text']} for o in t['opts']]
        if rec.get('no'):
            item['wrong'] = rec['no']  # ФИПИ уже сказал «неверно» — чат не должен их повторять
        items.append(item)
    pages = -(-len(items) // size)
    print(f'{exam}-{key}: заданий для чата {len(items)}, пачек по {size}: {pages}' +
          (f', это пачка {batch}' if batch < pages else ' — такой пачки нет'), file=sys.stderr)
    print(json.dumps(items[batch * size:(batch + 1) * size], ensure_ascii=False, indent=1))


def solve_subject(exam, key, args, gem_key):
    data, out, answers = load_subject(exam, key)
    if args.forget_wrong:  # варианты пересобраны — прежние «неверно» у выбора могли быть по другим вариантам
        for t in data['tasks']:
            rec = answers.get(t['id'])
            if rec and t.get('opts') and 'a' not in rec:
                rec.pop('no', None)
    cands = load_candidates(args.candidates)
    # Несколько независимых сессий ФИПИ: сайт отвечает секунды, по одной проверке — очень долго
    checkers = queue.Queue()
    for _ in range(max(1, min(args.jobs, 4))):
        checkers.put(Checker(exam, key, args.insecure))
    lock = threading.RLock()  # ответы меняются из нескольких потоков
    stats = {'select': 0, 'short': 0, 'full': 0, 'miss': 0, 'e': 0}
    done = [0]
    # Сколько вариантов обычно верно в этом предмете — по уже найденным ответам
    sizes = Counter(len(choice(t, answers[t['id']]['a']) or []) for t in data['tasks']
                    if t['kind'] == 'multi' and t.get('opts') and 'a' in answers.get(t['id'], {}))

    def save():
        """Пишем с учётом того, что уже на диске: если параллельно работал другой запуск,
        его подтверждённые ответы и решения не теряются."""
        with lock:
            disk = json.loads(out.read_text('utf-8')) if out.exists() else {}
            for qid, rec in disk.items():
                mine = answers.setdefault(qid, {})
                if 'a' in rec and 'a' not in mine:
                    mine.clear()
                    mine.update(rec)
                for k in ('e', 'sol', 'any'):
                    if k in rec and k not in mine and mine.get('a') == rec.get('a'):
                        mine[k] = rec[k]
            out.write_text(json.dumps(answers, ensure_ascii=False, indent=0, sort_keys=True) + '\n', 'utf-8')

    def verify(t, tries, extra=None):
        """Первый подтверждённый ФИПИ ответ из списка; неверные запоминаем, чтобы не повторять.
        Каждое задание проверяет один поток, поэтому запись о нём правим копией."""
        with lock:
            rec = json.loads(json.dumps(answers.get(t['id'], {})))
        checker = checkers.get()
        try:
            return _try(t, tries, extra, rec, checker)
        finally:
            checkers.put(checker)
            with lock:
                if rec:
                    answers[t['id']] = rec

    def _try(t, tries, extra, rec, checker):
        for i, cand in enumerate(tries):
            if t.get('opts'):  # выбор: номера вариантов, на сайт — маской
                parts = choice(t, cand)
                sent = {(''.join(parts) if all(len(x) == 1 for x in parts) else ','.join(parts)): wire(t, parts)} if parts else {}
            else:  # слово — как прислали, затем строчными и заглавными: неизвестно, важен ли ФИПИ регистр
                sent = {a: a for a in (norm(cand), norm(cand).lower(), norm(cand).upper())}
            for a, w in sent.items():
                if not a or a in rec.get('no', []):
                    continue
                r = checker.check(t['guid'], w)
                if r == '3':
                    rec.pop('no', None)
                    rec['a'] = a
                    if extra and i == 0:  # решение написано к первому ответу, к запасному оно не подходит
                        rec.update(extra)
                    # Ответ-набор цифр («запишите номера…»): если ФИПИ принимает перестановку, порядок не важен
                    if (not t.get('opts') and re.fullmatch(r'\d{2,}', a) and len(set(a)) == len(a)
                            and re.search(r'цифр|номер', t['text'], re.I) and checker.check(t['guid'], a[::-1]) == '3'):
                        rec['any'] = 1
                    return True
                if r == '2':
                    rec.setdefault('no', []).append(a)
        return False

    todo = [t for t in data['tasks'] if not t.get('media') and ('a' not in answers.get(t['id'], {}) or t['id'] in cands)]
    if args.limit:
        todo = todo[:args.limit]

    def ex(att):
        return {'e': att['e']} if att.get('e') else None

    def attach(t, atts):
        """Решение к уже подтверждённому ответу — если оно написано к этому же ответу."""
        with lock:
            known = answers.get(t['id'], {})
            att = next((x for x in atts if x.get('e') and x['a'] and norm(x['a'][0]).lower() == known.get('a', '').lower()), None)
            if att and 'a' in known and 'e' not in known:
                known['e'] = att['e']
                stats['e'] += 1

    def run(t):
        atts = cands.get(t['id'], [])
        known = answers.get(t['id'], {})
        if 'a' in known:
            pass  # ответ уже подтверждён — ниже только решение к нему (attach)
        elif t['kind'] in ('select', 'multi') and t.get('opts'):
            # Сначала ответ чата (с его решением), потом перебор: один вариант — всегда,
            # несколько — с --brute (до 2^n − 1 проверок на задание)
            ok = any(verify(t, x['a'][:1], ex(x)) for x in atts)
            if not ok and (t['kind'] == 'select' or args.brute):
                ok = verify(t, [o['id'] for o in t['opts']] if t['kind'] == 'select' else combos(t, sizes))
            if ok:
                with lock:
                    stats['select'] += 1
                    if t['kind'] == 'multi':
                        sizes[len(choice(t, answers[t['id']]['a']) or [])] += 1
        elif t['kind'] == 'short':
            ok = any(verify(t, x['a'], ex(x)) for x in atts)
            if not ok and args.ai and gem_key:
                r = gemini(gem_key, SOLVE.format(exam='ЕГЭ' if exam == 'ege' else 'ОГЭ', subject=data['title']), t, args.model, passage(data, t))
                if r and r.get('answer'):
                    ok = verify(t, [r['answer']] + list(r.get('alt') or [])[:2],
                                {'e': r['solution'].strip()} if r.get('solution') else None)
            if ok or atts or args.ai:
                with lock:
                    stats['short' if ok else 'miss'] += 1  # miss — ни один кандидат не подошёл
        elif t['kind'] == 'full' and not known.get('sol'):
            sol = next((x['sol'] for x in atts if x.get('sol')), None)
            if not sol and args.solutions and gem_key:
                r = gemini(gem_key, WRITE.format(subject=data['title']), t, args.model, passage(data, t))
                sol = r and (r.get('solution') or '').strip()
            if sol:
                with lock:
                    answers.setdefault(t['id'], {})['sol'] = sol
                    stats['full'] += 1
        attach(t, atts)
        with lock:
            done[0] += 1
            if done[0] % 20 == 0:
                save()
                print(f'  {exam}-{key}: {done[0]}/{len(todo)} {stats}', flush=True)

    # Gemini думает долго, ФИПИ отвечает секунды — несколько заданий параллельно
    with ThreadPoolExecutor(max_workers=max(checkers.qsize(), 4 if args.ai or args.solutions else 1)) as pool:
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
    ap.add_argument('--candidates', nargs='+', help='файлы с ответами и решениями (например, от ChatGPT)')
    ap.add_argument('--brute', action='store_true',
                    help='подбирать перебором и ответы с несколькими вариантами (до 31 проверки на задание из 5 вариантов)')
    ap.add_argument('--forget-wrong', action='store_true',
                    help='забыть прежние неверные попытки у заданий с выбором (после пересборки вариантов)')
    ap.add_argument('--jobs', type=int, default=1, help='параллельных сессий проверки на сайте ФИПИ (не больше 4)')
    ap.add_argument('--export', type=int, metavar='N', help='вывести пачку №N заданий для чата и выйти (без сети)')
    ap.add_argument('--batch', type=int, default=40, help='заданий в пачке для --export')
    ap.add_argument('--kind', default='short,select,multi', help='какие задания выгружать: short,select,multi,full')
    ap.add_argument('--model', help='модель Gemini вместо списка по умолчанию')
    ap.add_argument('--limit', type=int, default=0, help='не больше N заданий на предмет (для пробы)')
    ap.add_argument('--insecure', action='store_true', help='не проверять сертификат ФИПИ')
    args = ap.parse_args()
    if args.export is not None:
        if len(args.subjects) != 1:
            sys.exit('Для --export укажите один предмет, например: physics --export 0')
        export(args.exam, args.subjects[0], args.export, args.batch, set(args.kind.split(',')))
        return
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
