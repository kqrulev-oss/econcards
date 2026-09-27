#!/usr/bin/env python3
"""Собирает наборы карточек для приложения из data/source/ в packs/.

Запуск: python3 tools/build_packs.py            — всё: наборы, index.json и производные
        python3 tools/build_packs.py --derived  — только производные из готовых packs/<id>.json

Производные файлы (собираются из готовых наборов, без data/source/):
  packs/<id>.free.json      бесплатная часть библиотеки — сервер отдаёт её вместо полного
                            набора тем, у кого нет доступа (правила — как trimLibrary
                            в worker/billing.js)
  packs/sample-<предмет>.json  маленький «Готовый пример» для студии: 3 темы по 12 карточек
                            с теорией; поля — как у наборов библиотеки

Формат набора (packs/<id>.json):
  id, title, subject, desc, color
  topics:  [{id, title, section}]
  theory:  [{id, topic, title, min, html}]
  cards:   [{id, t, k, q, o?, a, e?, img?, src?}]

Карточка: t — тема, k — тип:
  one    — один верный вариант, a = id варианта
  many   — несколько верных, a = [id, ...]
  match  — соответствие, o = {left, right}, a = {левый id: правый id}
  flip   — вопрос → ответ (самопроверка), a = текст ответа
  open   — развёрнутое решение, a = эталонное решение (проверка ИИ или самим)
  stress — ударение, a = слово с заглавной ударной гласной
"""
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'data' / 'source'
OUT = ROOT / 'packs'


def load(name):
    return json.loads((SRC / f'{name}.json').read_text('utf-8'))


def esc(s):
    return html.escape(str(s or ''), quote=False)


def supify(t):
    t = re.sub(r'\^\{([^}]*)\}', r'<sup>\1</sup>', t)
    t = re.sub(r'\^\(([^)]*)\)', r'<sup>\1</sup>', t)
    return re.sub(r'\^([0-9A-Za-zА-Яа-яα-ωΑ-Ω]|[+\-−][0-9]+)', r'<sup>\1</sup>', t)


def inline(s):
    """Экранирует текст, включает **жирный** и формулы ⟦…⟧ (как text() в lib.js)."""
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', esc(s))
    solo = re.fullmatch(r'\s*⟦(.+)⟧\s*', s)
    if solo:
        return f'<span class="fblock">{supify(solo.group(1))}</span>'
    return re.sub(r'⟦(.+?)⟧', lambda m: f'<span class="f">{supify(m.group(1))}</span>', s)


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def strip_condition(solution, question):
    """В части решений заново переписано условие — оставляем с «Ответ» и дальше."""
    if norm(solution).startswith(norm(question)[:80]):
        i = solution.find('Ответ', len(question) // 2)
        if i > 0:
            return solution[i:]
    return solution


def text_to_html(body):
    """Простой текст курса → абзацы и списки."""
    out = []
    for chunk in re.split(r'\n\s*\n', body.strip()):
        lines = [l.strip() for l in chunk.split('\n') if l.strip()]
        if lines and all(re.match(r'^(\d+[.)]|[—–•-])\s', l) for l in lines):
            tag = 'ol' if re.match(r'^\d', lines[0]) else 'ul'
            items = ''.join('<li>' + inline(re.sub(r'^(\d+[.)]|[—–•-])\s+', '', l)) + '</li>' for l in lines)
            out.append(f'<{tag}>{items}</{tag}>')
        else:
            out.append('<p>' + '<br>'.join(inline(l) for l in lines) + '</p>')
    return ''.join(out)


def blocks_to_html(blocks):
    """Блоки уроков Сотки (p, tb, ex, wr, st) → HTML."""
    out = []
    for b in blocks:
        if b.get('h'):
            out.append(f'<h3>{esc(b["h"])}</h3>')
        for it in b['items']:
            t = it['t']
            if t == 'p':
                out.append(f'<p>{inline(it["s"])}</p>')
            elif t == 'tb':
                rows = ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>' for r in it['rows'])
                head = ''
                if it.get('head'):
                    head = '<tr>' + ''.join(f'<th>{esc(c)}</th>' for c in it['head']) + '</tr>'
                out.append(f'<table>{head}{rows}</table>')
            elif t in ('ex', 'wr', 'st'):
                cls = {'ex': 'note', 'wr': 'warn', 'st': 'steps'}[t]
                tag = 'ol' if t == 'st' else 'ul'
                items = ''.join(f'<li>{inline(x)}</li>' for x in it['items'])
                title = {'ex': 'Пример', 'wr': 'Типичные ошибки', 'st': 'Алгоритм'}[t]
                out.append(f'<div class="{cls}"><b>{title}</b><{tag}>{items}</{tag}></div>')
    return ''.join(out)


def write(pack):
    OUT.mkdir(exist_ok=True)
    used = Counter(c['t'] for c in pack['cards'])
    pack['topics'] = [t for t in pack['topics'] if used[t['id']] or any(x['topic'] == t['id'] for x in pack['theory'])]
    ids = Counter(c['id'] for c in pack['cards'])
    dup = [i for i, n in ids.items() if n > 1]
    assert not dup, f'{pack["id"]}: повторяются id {dup[:5]}'
    (OUT / f'{pack["id"]}.json').write_text(json.dumps(pack, ensure_ascii=False, separators=(',', ':')), 'utf-8')
    kinds = Counter(c['k'] for c in pack['cards'])
    print(f'packs/{pack["id"]}.json: {len(pack["cards"])} карточек {dict(kinds)}, теория {len(pack["theory"])}')
    return {
        'id': pack['id'], 'title': pack['title'], 'subject': pack['subject'], 'desc': pack['desc'],
        'color': pack['color'], 'cards': len(pack['cards']), 'topics': len(pack['topics']),
        'theory': len(pack['theory']),
    }


# ---------- Олимпиадная экономика ----------

def econ_pack():
    src = load('econcards')
    courses = load('econ-courses')['courses']
    olymp = {o['id']: o for o in src['olympiads']}
    stages = {(o['id'], s['id']): s['title'] for o in src['olympiads'] for s in o['stages']}

    def source(c):
        o = c.get('olympiad')
        if not o:
            return None
        grade = next((t for t in c['tags'] if 'класс' in t), '')
        parts = [olymp[o['olympiadID']]['title'], stages.get((o['olympiadID'], o['stage']), ''), str(o['year']), grade]
        return ' · '.join(p for p in parts if p)

    cards = []
    for c in src['cards']:
        if c['direction'] != 'olympiad':
            continue
        x = c['content']
        card = {'id': c['id'], 't': c['topicID'], 'q': x['text']}
        if x.get('options') and x.get('correctOptionID'):
            card.update(k='one', o=[{'id': o['id'], 't': o['text']} for o in x['options']], a=x['correctOptionID'])
            if x.get('explanation'):
                card['e'] = x['explanation']
        elif x.get('solution'):
            card.update(k='open', a=strip_condition(x['solution'], x['text']))
        else:
            continue  # без ключа и без решения тренировать нечего
        if x.get('images'):
            card['img'] = ['img/' + i for i in x['images']]
        s = source(c)
        if s:
            card['src'] = s
        cards.append(card)

    topics = [{'id': t['id'], 'title': t['title'], 'section': t['section']}
              for t in src['topics'] if t['direction'] == 'olympiad']
    theory = []
    for course in courses:
        if course['id'] == 'ege-rus':
            continue
        for l in course['lessons']:
            theory.append({'id': l['id'], 'topic': l['topic'], 'title': l['t'], 'min': l['min'],
                           'section': course['title'], 'html': text_to_html(l['body'])})
    return {
        'id': 'econ-olymp', 'title': 'Олимпиадная экономика', 'subject': 'Экономика',
        'desc': 'Задачи ВсОШ, Высшей пробы, МОШ, СПбГУ, РАНХиГС, Сибириады, РЭШ и IEO с разборами',
        'color': '#2F6BFF', 'topics': topics, 'theory': theory, 'cards': cards,
    }


# ---------- ЕГЭ: русский язык ----------

def add_essay(topics, theory, cards):
    """Задание 27 из приложения «Сочинение»: уроки с нуля, справочник, критерии,
    упражнения (карточки), письменные тренировки (проверка ИИ) и аргументы."""
    src = load('essay')
    t27 = next(t for t in topics if t['id'] == 'task-27')
    school = {'id': 't27-school', 'title': 'Сочинение по шагам: проблема, комментарий, позиция',
              'tip': 'Проблема — вопрос из текста; два примера с пояснениями и связью; позиция автора — его ответ на этот вопрос.'}
    write = {'id': 't27-write', 'title': 'Пишем фрагменты сочинения',
             'tip': 'Сначала сформулируй сам, потом сверь с образцом или попроси ИИ проверить.'}
    args = {'id': 't27-args', 'title': 'Литературные аргументы',
            'tip': 'Для каждой частой проблемы держи в голове одно произведение и эпизод из него.'}
    t27['protos'] = [school, write, args] + t27.get('protos', [])
    for n, lesson in enumerate(src['SCHOOL'], 1):
        theory.append({'id': f'essay-{lesson["id"]}', 'topic': 'task-27', 'title': f'{n}. {lesson["t"]}',
                       'min': 5, 'section': 'Сочинение с нуля', 'html': f'<p class="muted">{esc(lesson["sub"])}</p>{lesson["theory"]}'})
        for i, d in enumerate(lesson.get('drills', [])):
            ids = 'абвгде'
            cards.append({'id': f'essay-{lesson["id"]}-d{i + 1}', 't': 'task-27', 'p': school['id'], 'k': 'one', 'q': d['q'],
                          'o': [{'id': ids[j], 't': o} for j, o in enumerate(d['o'])], 'a': ids[d['a']], 'e': d.get('e', '')})
        if lesson.get('write'):
            w = lesson['write']
            cards.append({'id': f'essay-{lesson["id"]}-w', 't': 'task-27', 'p': write['id'], 'k': 'open',
                          'q': w['task'], 'a': w['sample']})
    for n, ref in enumerate(src['REF'], 1):
        theory.append({'id': f'essay-ref{n}', 'topic': 'task-27', 'title': ref['t'], 'min': ref.get('min', 5),
                       'section': 'Справочник', 'html': ref['html']})
    crit = ''.join(f'<tr><td>{esc(c)}</td><td>{p}</td></tr>' for c, p in src['CRIT_EGE'])
    theory.insert(len(theory) - len(src['REF']) - len(src['SCHOOL']), {
        'id': 'essay-crit', 'topic': 'task-27', 'title': 'Критерии К1–К12: за что дают 22 балла', 'min': 3,
        'section': 'Сочинение с нуля',
        'html': f'<table><tr><th>Критерий</th><th>Баллы</th></tr>{crit}</table>'
                f'<p>Всего: {sum(p for _, p in src["CRIT_EGE"])} первичных баллов.</p>'})
    for i, a in enumerate(src['EGE'], 1):
        cards.append({'id': f'essay-arg{i}', 't': 'task-27', 'p': args['id'], 'k': 'flip',
                      'q': f'Какой литературный аргумент подойдёт к теме «{a["p"]}»?', 'a': a['lit']})


def exam_task(x):
    """Номер задания по действующей спецификации ЕГЭ.

    В банке Сотки карточки заданий 1–3 пронумерованы по старой схеме: стили
    речи лежат в 1, подбор связующего слова — во 2, лексическое значение — в 3.
    Раскладываем их по содержанию вопроса, остальные номера совпадают.
    """
    n, q, les = x['task'], x['q'].lower(), x.get('les')
    if n == 1:
        return 1 if 'на месте пропуска' in q or les in ('RU010', 'RU016') else 3
    if n == 2:
        return 2 if les in ('RU001', 'RU015') or 'обозначает' in q else 1
    if n == 3:
        return 3 if 'стил' in q or les in ('RU014', 'RU070', 'RU071', 'RU072') else 2
    return n


def rus_pack():
    bank = load('sotka-bank')
    lessons = load('sotka-lessons')
    exam = load('sotka-exam')
    econ = load('econcards')

    cards, seen = [], set()

    def key(q, opts):
        return (re.sub(r'\s+', ' ', q).strip().lower(), tuple(sorted(o.lower() for o in opts)))

    for i, x in enumerate(bank):
        t = f'task-{exam_task(x)}'
        cid = x.get('id') or f'rus-{x["k"]}-{x["task"]}-{i}'
        card = {'id': cid, 't': t, 'q': x['q']}
        if x['k'] == 'mc':
            card.update(k='one', o=[{'id': o['id'], 't': o['t']} for o in x['o']], a=x['c'])
            seen.add(key(x['q'], [o['t'] for o in x['o']]))
        elif x['k'] == 'multi':
            card.update(k='many', o=[{'id': o['id'], 't': o['t']} for o in x['o']], a=x['cs'])
        elif x['k'] == 'flip':
            card.update(k='flip', a=x['a'])
        elif x['k'] == 'match':
            card.update(k='match', o={'left': x['left'], 'right': x['right']}, a=x['map'])
        if x.get('e'):
            card['e'] = x['e']
        cards.append(card)

    # Карточки из EconCards, которых нет в банке Сотки (там старая нумерация 1–3)
    renum = {1: 3, 2: 1, 3: 2}
    added = 0
    for c in econ['cards']:
        if c['direction'] != 'ege_rus':
            continue
        x = c['content']
        if not (x.get('options') and x.get('correctOptionID')):
            continue
        k = key(x['text'], [o['text'] for o in x['options']])
        if k in seen:
            continue
        seen.add(k)
        n = int(c['topicID'].split('-t')[1])
        card = {'id': 'ec-' + c['id'], 't': f'task-{renum.get(n, n)}', 'k': 'one', 'q': x['text'],
                'o': [{'id': o['id'], 't': o['text']} for o in x['options']], 'a': x['correctOptionID']}
        if x.get('explanation'):
            card['e'] = x['explanation']
        cards.append(card)
        added += 1
    print(f'  ЕГЭ: из EconCards добавлено {added} карточек, которых не было в Сотке')

    topics = [{'id': f'task-{e["n"]}', 'title': f'{e["n"]}. {e["title"]}', 'section': 'Задания ЕГЭ',
               'n': e['n'], 'pts': e['pts']} for e in exam]
    # Прототипы внутри заданий (tools/classify_prototypes.py): подтипы и привязка карточек
    proto_file = SRC / 'ege-rus-prototypes.json'
    if proto_file.exists():
        protos = json.loads(proto_file.read_text('utf-8'))
        for t in topics:
            info = protos.get(str(t['n']))
            if info:
                t['protos'] = info['prototypes']
        assign = {cid: pid for info in protos.values() for cid, pid in info['assign'].items()}
        for c in cards:
            if c['id'] in assign:
                c['p'] = assign[c['id']]
        print(f'  прототипы: {sum(len(t.get("protos", [])) for t in topics)} в {sum(1 for t in topics if t.get("protos"))} заданиях, '
              f'карточек с прототипом {sum(1 for c in cards if "p" in c)} из {len(cards)}')
    lesson_topic = {}
    for e in exam:
        for l in e['lessons']:
            lesson_topic.setdefault(l, f'task-{e["n"]}')
    theory = []
    for l in lessons:
        topic = lesson_topic.get(l['id']) or (f'task-{l["tasks"][0]}' if l.get('tasks') else 'task-1')
        theory.append({'id': l['id'], 'topic': topic, 'title': l['title'], 'min': 10,
                       'section': 'Теория', 'html': blocks_to_html(l['blocks'])})
    add_essay(topics, theory, cards)
    return {
        'id': 'ege-rus', 'title': 'ЕГЭ: русский язык', 'subject': 'Русский язык',
        'desc': 'Все тестовые задания ЕГЭ с разборами и теорией по Розенталю',
        'color': '#5B3DF5', 'topics': topics, 'theory': theory, 'cards': cards,
    }


# ---------- Ударения ----------

def stress_pack():
    src = load('udarenie')
    names = {'n': 'Существительные', 'a': 'Прилагательные', 'v': 'Глаголы',
             'p': 'Причастия', 'd': 'Деепричастия и наречия'}
    # Правила разбиты мельче, чем словарь: vPast, vInf… относятся к теме «v»
    rule_titles = {'vPast': 'Прошедшее время', 'vInf': 'Инфинитив', 'vPres': 'Настоящее и будущее время',
                   'pEnn': 'Суффикс -ённ-', 'pT': 'Суффиксы -т-, -нут-', 'pVsh': 'Суффикс -вш-',
                   'pSch': 'Суффикс -щ-'}
    cards, seen = [], set()
    for cat, words in src['data']:
        for w in words.split():
            if w.lower() in seen:
                continue
            seen.add(w.lower())
            cards.append({'id': f'st-{len(cards) + 1}', 't': f'st-{cat}', 'k': 'stress',
                          'q': 'Где ударение?', 'a': w})
    topics = [{'id': f'st-{c}', 'title': names[c], 'section': 'Задание 4'} for c, _ in src['data']]
    theory = [{'id': f'rule-{k}', 'topic': f'st-{k[0]}', 'title': rule_titles.get(k, names[k[0]]), 'min': 1,
               'section': 'Правила', 'html': text_to_html(r)} for k, r in src['rules'].items()]
    return {
        'id': 'udarenie', 'title': 'Ударения', 'subject': 'Русский язык',
        'desc': 'Орфоэпический минимум ФИПИ для задания 4 ЕГЭ',
        'color': '#C2185B', 'topics': topics, 'theory': theory, 'cards': cards,
    }


# ---------- ЕГЭ: профильная математика ----------

# Правки к анализу GPT (data/source/ege-math-gpt.json). Все ответы проверены
# вручную; эти карточки GPT сам пометил как ошибочные — убираем или чиним.
MATH_DROP = {('t2-p2', 0),   # ответ √34 — не формат краткого ответа ЕГЭ
             ('t4-p1', 0),   # 1/3 — бесконечная дробь
             ('t5-p5', 1),   # 2/15 — бесконечная дробь
             ('t7-p2', 1),   # 3√2 — не формат краткого ответа
             ('t10-p4', 0)}  # D = 756, корень нецелый
MATH_FIX = {('t2-p3', 1): {'a': '12'},   # (4;1)·(2;4) = 12, в анализе стояло 16
            ('t7-p5', 0): {'a': '3'}}    # 3⁷/3⁶ = 3, в анализе стояло 1
MATH_FILES = ['ege-math-gpt', 'ege-math-gpt-6-10', 'ege-math-11-19']  # 11–19: tools/math_11_19.py


# ---------- графики для задания 8 (SVG, строятся из формул) ----------

def _svg_plot(fn, x0, x1, y0, y1, extra='', width=360):
    """График на квадратной клетчатой сетке, как в КИМ: fn — функция, оси подписаны."""
    u = (width - 40) / (x1 - x0)
    w, h = width, (y1 - y0) * u + 30
    sx = lambda x: 20 + (x - x0) * u
    sy = lambda y: 15 + (y1 - y) * u
    grid = ''.join(f'<line x1="{sx(i):.1f}" y1="{sy(y0):.1f}" x2="{sx(i):.1f}" y2="{sy(y1):.1f}"/>' for i in range(int(x0), int(x1) + 1))
    grid += ''.join(f'<line x1="{sx(x0):.1f}" y1="{sy(j):.1f}" x2="{sx(x1):.1f}" y2="{sy(j):.1f}"/>' for j in range(int(y0), int(y1) + 1))
    # Линия рвётся там, где функция уходит за рисунок или не определена (асимптоты)
    segs, pts = [], []
    n = 400
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        try:
            y = fn(x)
        except (ZeroDivisionError, ValueError):
            y = None
        if y is not None and y0 - 3 <= y <= y1 + 3:
            pts.append(f'{sx(x):.1f},{sy(y):.1f}')
        elif pts:
            segs.append(pts)
            pts = []
    if pts:
        segs.append(pts)
    lines = ''.join(f'<polyline fill="none" stroke="#2F6BFF" stroke-width="2.4" points="{" ".join(s)}"/>' for s in segs)
    axes = (f'<line x1="{sx(x0):.1f}" y1="{sy(0):.1f}" x2="{sx(x1):.1f}" y2="{sy(0):.1f}" stroke="#15181E" stroke-width="1.4" marker-end="url(#a)"/>'
            f'<line x1="{sx(0):.1f}" y1="{sy(y0):.1f}" x2="{sx(0):.1f}" y2="{sy(y1):.1f}" stroke="#15181E" stroke-width="1.4" marker-end="url(#a)"/>'
            f'<text x="{sx(x1) - 10:.1f}" y="{sy(0) - 6:.1f}">x</text><text x="{sx(0) + 6:.1f}" y="{sy(y1) + 10:.1f}">y</text>'
            f'<text x="{sx(1) - 3:.1f}" y="{sy(0) + 14:.1f}">1</text><text x="{sx(0) - 12:.1f}" y="{sy(1) + 4:.1f}">1</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="Arial" font-size="12" fill="#15181E">'
            '<defs><marker id="a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z"/></marker></defs>'
            f'<rect width="{w}" height="{h}" fill="#fff"/><g stroke="#E3E6EC" stroke-width="1">{grid}</g>{axes}'
            f'<clipPath id="c"><rect x="{sx(x0):.1f}" y="{sy(y1):.1f}" width="{sx(x1) - sx(x0):.1f}" height="{sy(y0) - sy(y1):.1f}"/></clipPath>'
            f'<g clip-path="url(#c)">{lines}'
            f'{extra(sx, sy) if extra else ""}</g></svg>')


def _spline(xs, ys):
    """Монотонная кубическая интерполяция (PCHIP, Fritsch–Carlson): гладкая и
    без выбросов между точками — график не пересекает ось там, где не должен."""
    n = len(xs) - 1
    h = [xs[i + 1] - xs[i] for i in range(n)]
    dl = [(ys[i + 1] - ys[i]) / h[i] for i in range(n)]
    m = [dl[0]] + [0.0] * (n - 1) + [dl[-1]]
    for i in range(1, n):
        if dl[i - 1] * dl[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / dl[i - 1] + w2 / dl[i])

    def f(x):
        j = max(0, min(n - 1, next((i for i in range(n) if x <= xs[i + 1]), n - 1)))
        t = (x - xs[j]) / h[j]
        h00, h10, h01, h11 = 2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t, -2 * t**3 + 3 * t**2, t**3 - t**2
        return h00 * ys[j] + h10 * h[j] * m[j] + h01 * ys[j + 1] + h11 * h[j] * m[j + 1]
    return f


def derivative_graph(zeros, double, sign, x0, x1):
    """Гладкий график f′(x): нули в zeros (смена знака) и double (касание оси),
    знаки на промежутках — как у sign·∏(x − z)·∏(x − d)²."""
    raw = lambda x: sign * _prod(x - z for z in zeros) * _prod((x - d) ** 2 for d in double)
    cuts = sorted(zeros + double)
    bounds = [x0] + cuts + [x1]
    heights = [2.4, 1.6, 2.9, 1.9, 2.6, 1.7]
    xs, ys = [x0], [None]
    for i, (a, b) in enumerate(zip(bounds, bounds[1:])):
        sg = 1 if raw((a + b) / 2) > 0 else -1
        amp = heights[i % len(heights)] * (0.6 if (a in double or b in double) else 1)
        if i == 0:
            ys[0] = sg * min(3.6, amp + 1.2)
        xs.append((a + b) / 2)
        ys.append(sg * amp)
        if b in double:
            # Касание оси: подходим плавно и остаёмся на своей стороне
            xs += [b - 0.7, b, b + 0.7]
            ys += [sg * 0.6, sg * 0.02, sg * 0.6]
        else:
            xs.append(b)
            ys.append(0 if b != x1 else sg * min(3.6, amp + 1.2))
    fn = _spline(xs, ys)
    return fn, _svg_plot(fn, x0, x1, -4, 4)


def _prod(it):
    r = 1
    for v in it:
        r *= v
    return r


def tangent_graph(p1, p2):
    """График функции и касательной через две узловые точки (p1, p2)."""
    k = (p2[1] - p1[1]) / (p2[0] - p1[0])
    line = lambda x: p1[1] + k * (x - p1[0])
    xt = (p1[0] + p2[0]) / 2 + 0.5
    fn = lambda x: line(x) - 0.35 * (x - xt) ** 2
    xs = [p1[0], p2[0]]
    ys = [p1[1], p2[1]]
    x0, x1 = min(xs + [0]) - 2, max(xs + [0]) + 3
    y0, y1 = min(ys + [0]) - 2, max(ys + [0]) + 2

    def extra(sx, sy):
        tl = f'<line x1="{sx(x0):.1f}" y1="{sy(line(x0)):.1f}" x2="{sx(x1):.1f}" y2="{sy(line(x1)):.1f}" stroke="#E4572E" stroke-width="2"/>'
        dots = ''.join(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="4" fill="#E4572E"/>' for x, y in (p1, p2))
        touch = f'<circle cx="{sx(xt):.1f}" cy="{sy(line(xt)):.1f}" r="3.5" fill="#15181E"/><text x="{sx(xt) - 6:.1f}" y="{sy(y0) - 4:.1f}">x₀</text>'
        guide = f'<line x1="{sx(xt):.1f}" y1="{sy(line(xt)):.1f}" x2="{sx(xt):.1f}" y2="{sy(y0):.1f}" stroke="#15181E" stroke-dasharray="3 3"/>'
        return tl + guide + dots + touch
    return fn, _svg_plot(fn, x0, x1, y0, y1, extra)


# Карточки задания 8: (прототип, номер) → формулировка как в КИМ и график.
# Знаки производной считаются из формулы, а не переписываются вручную.
MAX_Q = 'На рисунке изображён график y = f′(x) — производной функции f(x), определённой на интервале ({a}; {b}). Найдите количество точек {kind} функции f(x) на этом интервале.'
TAN_Q = 'На рисунке изображены график функции y = f(x) и касательная к нему в точке с абсциссой x₀. Найдите значение производной функции f(x) в точке x₀.'
# Для касательных координаты в условии не нужны — берём компактные узлы с тем же наклоном
MATH_GRAPHS = {
    ('t8-p1', 0): ('tan', (-1, -2), (1, 2)),
    ('t8-p1', 1): ('tan', (-2, 3), (0, -1)),
    ('t8-p1', 2): ('tan', (-3, -1), (1, 0)),
    ('t8-p2', 0): ('der', 'максимума', [-4, -1, 2, 5], [], 1, -6, 6),
    ('t8-p2', 1): ('der', 'максимума', [-3, 4], [0], -1, -5, 6),
    ('t8-p2', 2): ('der', 'максимума', [1, 3, 6], [8], -1, 0, 9),
    ('t8-p3', 0): ('der', 'минимума', [-5, -2, 1, 4], [], -1, -6, 5),
    ('t8-p3', 1): ('der', 'минимума', [-2, 5], [2], 1, -4, 7),
    ('t8-p3', 2): ('der', 'минимума', [1, 7], [4], -1, 0, 8),
}


def extrema_count(fn, a, b, kind):
    """Считает смены знака производной на (a; b): максимум + → −, минимум − → +."""
    xs = [a + (b - a) * i / 4000 for i in range(1, 4000)]
    signs = [1 if fn(x) > 1e-9 else -1 if fn(x) < -1e-9 else 0 for x in xs]
    signs = [v for v in signs if v]
    changes = list(zip(signs, signs[1:]))
    return sum(1 for s1, s2 in changes if (s1, s2) == ((1, -1) if kind == 'максимума' else (-1, 1)))


def graph_card(card, spec):
    if spec[0] == 'tan':
        _, p1, p2 = spec
        _, svg = tangent_graph(p1, p2)
        k = (p2[1] - p1[1]) / (p2[0] - p1[0])
        assert abs(k - float(card['a'].replace(',', '.'))) < 1e-9, (card['id'], k, card['a'])
        card['q'] = TAN_Q
    else:
        _, kind, zeros, double, sign, a, b = spec
        fn, svg = derivative_graph(zeros, double, sign, a, b)
        got = extrema_count(fn, a, b, kind)
        assert str(got) == card['a'], (card['id'], got, card['a'])
        # Сплайн не должен давать лишних нулей: смен знака столько же, сколько простых корней
        xs = [a + (b - a) * i / 4000 for i in range(1, 4000)]
        sg = [v for v in (1 if fn(x) > 1e-6 else -1 if fn(x) < -1e-6 else 0 for x in xs) if v]
        assert sum(1 for p, q in zip(sg, sg[1:]) if p != q) == len(zeros), (card['id'], 'лишние нули')
        card['q'] = MAX_Q.format(a=a, b=b, kind=kind)
    card['svg'] = svg


def is_number(s):
    return bool(re.fullmatch(r'-?\d+([.,]\d+)?', str(s).strip()))


def math_pack():
    src = [task for f in MATH_FILES for task in load(f)]
    topics, theory, cards = [], [], []
    for task in src:
        tid = f'm-task-{task["task"]}'
        protos = []
        for pr in task['prototypes']:
            pid = f'm-{pr["id"]}'
            protos.append({'id': pid, 'title': pr['title'], 'tip': ' → '.join(pr['algorithm'][:3])})
            theory.append({
                'id': f'th-{pid}', 'topic': tid, 'title': pr['title'], 'min': 3, 'section': task['title'],
                'html': (f'<p>{inline(pr["wording"])}</p><div class="steps"><b>Алгоритм</b><ol>'
                         + ''.join(f'<li>{inline(x)}</li>' for x in pr['algorithm'])
                         + '</ol></div><div class="warn"><b>Типичные ошибки</b><ul>'
                         + ''.join(f'<li>{inline(x)}</li>' for x in pr['mistakes']) + '</ul></div>'),
            })
            for i, c in enumerate(pr['cards']):
                if (pr['id'], i) in MATH_DROP:
                    continue
                c = {**c, **MATH_FIX.get((pr['id'], i), {})}
                card = {'id': f'{pid}-{i + 1}', 't': tid, 'p': pid, 'q': c['q']}
                final = re.search(r'Ответ:\s*(-?\d+(?:[.,]\d+)?)\s*°?\.?\s*$', c['a']) if c['k'] == 'open' else None
                if c['k'] == 'flip' and is_number(c['a']):
                    # Краткий ответ ЕГЭ — число: ученик вводит его, приложение проверяет
                    card.update(k='num', a=str(c['a']).replace('.', ','))
                elif final:
                    # Решение с числовым ответом: ученик вводит число, полное решение — в разборе
                    card.update(k='num', a=final.group(1).replace('.', ','), e=c['a'])
                else:
                    card.update(k=c['k'], a=c['a'])
                if c.get('e') and 'e' not in card:
                    card['e'] = c['e']
                for key in ('o', 'svg'):
                    if key in c:
                        card[key] = c[key]
                if (pr['id'], i) in MATH_GRAPHS:
                    graph_card(card, MATH_GRAPHS[(pr['id'], i)])
                cards.append(card)
        topics.append({'id': tid, 'title': f'{task["task"]}. {task["title"]}', 'section': 'Задания ЕГЭ',
                       'n': task['task'], 'pts': task['points'], 'protos': protos})
        theory.insert(len(theory) - len(task['prototypes']), {
            'id': f'th-{tid}', 'topic': tid, 'title': f'Что проверяет задание {task["task"]}', 'min': 2,
            'section': task['title'],
            'html': f'<p>{inline(task["checks"])}</p><div class="note"><b>Темы кодификатора</b><ul>'
                    + ''.join(f'<li>{inline(x)}</li>' for x in task['codifier']) + '</ul></div>'
                    + f'<p class="muted">Балл: {task["points"]} · примерно {task["minutes"]} мин на задание</p>',
        })
    return {
        'id': 'ege-math', 'title': 'ЕГЭ: профильная математика', 'subject': 'Математика',
        'desc': 'Все 19 заданий по прототипам: от геометрии и вероятности до параметров и экономической задачи',
        'color': '#0E7C86', 'topics': topics, 'theory': theory, 'cards': cards,
    }


# ---------- производные: бесплатная часть библиотеки и «Готовый пример» ----------

# Наборы библиотеки с платным доступом — как LIB_PACKS в worker/billing.js
LIB_PACKS = ['ege-rus', 'ege-math', 'econ-olymp', 'udarenie']
FREE_PROTOS = 2    # без доступа: по 2 первых прототипа в каждом задании
FREE_PER_TOPIC = 15  # в наборах без прототипов — первые 15 карточек темы


def trim_library(pack):
    """Бесплатная часть: все правила и теория, а задания — по 2 первых прототипа
    в каждом задании (карточки без прототипа — первые 15 в теме). Правила и порядок
    полей — ровно как trimLibrary() в worker/billing.js: результат тот же, что
    сервер раньше собирал на каждый запрос."""
    keep = set()
    for t in pack['topics']:
        for p in (t.get('protos') or [])[:FREE_PROTOS]:
            keep.add(p.get('id'))
    per_topic = Counter()
    cards = []
    for c in pack['cards']:
        if c.get('p'):
            if c['p'] in keep:
                cards.append(c)
            continue
        per_topic[c['t']] += 1
        if per_topic[c['t']] <= FREE_PER_TOPIC:
            cards.append(c)
    return {**pack, 'cards': cards, 'limited': {'shown': len(cards), 'total': len(pack['cards'])}}


# «Готовый пример» в студии: набор-источник, темы, карточек на тему
SAMPLES = {
    'rus': ('ege-rus', ['task-4', 'task-13', 'task-15']),
    'math': ('ege-math', ['m-task-1', 'm-task-5', 'm-task-6']),
}
SAMPLE_PER_TOPIC = 12


def sample_pack(key, pack, tids, per_topic=SAMPLE_PER_TOPIC):
    """Маленький пример из библиотеки: выбранные темы, их теория и по per_topic
    карточек на тему — по очереди из каждого прототипа, чтобы первые карточки были
    разными (у темы остаются только прототипы, из которых взяты карточки). id тем
    и карточек — как в библиотеке: потом можно добавить всю тему без повторов."""
    topics, cards = [], []
    for tid in tids:
        t = next(x for x in pack['topics'] if x['id'] == tid)
        pool = [c for c in pack['cards'] if c['t'] == tid]
        protos = t.get('protos') or []
        known = {p['id'] for p in protos}
        groups = [[c for c in pool if c.get('p') == p['id']] for p in protos]
        groups.append([c for c in pool if c.get('p') not in known])
        picked = []
        while len(picked) < per_topic and any(groups):
            for g in groups:
                if g and len(picked) < per_topic:
                    picked.append(g.pop(0))
        used = {c.get('p') for c in picked}
        topic = dict(t)
        if protos:
            topic['protos'] = [p for p in protos if p['id'] in used]
        topics.append(topic)
        cards += picked
    theory = [l for l in pack['theory'] if l['topic'] in tids]
    return {
        'id': f'sample-{key}', 'title': pack['title'], 'subject': pack['subject'],
        'desc': f'Пример тренажёра: {len(tids)} темы, {len(cards)} карточек с теорией',
        'color': pack['color'], 'topics': topics, 'theory': theory, 'cards': cards,
    }


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), 'utf-8')


def derived(packs=None):
    """packs/<id>.free.json и packs/sample-*.json из собранных наборов
    (packs — уже собранные в этом запуске, остальные читаются из packs/)."""
    packs = dict(packs or {})
    for pid in set(LIB_PACKS) | {src for src, _ in SAMPLES.values()}:
        if pid not in packs:
            packs[pid] = json.loads((OUT / f'{pid}.json').read_text('utf-8'))
    for pid in LIB_PACKS:
        free = trim_library(packs[pid])
        write_json(f'{pid}.free.json', free)
        print(f'packs/{pid}.free.json: {free["limited"]["shown"]} из {free["limited"]["total"]} карточек')
    for key, (src, tids) in SAMPLES.items():
        # Пример публичный (его видит любой гость) — только из бесплатной части библиотеки
        s = sample_pack(key, trim_library(packs[src]), tids)
        write_json(f'{s["id"]}.json', s)
        print(f'packs/{s["id"]}.json: {len(s["cards"])} карточек в {len(s["topics"])} темах, теория {len(s["theory"])}')


if __name__ == '__main__':
    if '--derived' in sys.argv:
        derived()
        sys.exit()
    built = [rus_pack(), math_pack(), econ_pack(), stress_pack()]
    index = [write(p) for p in built]
    (OUT / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=1) + '\n', 'utf-8')
    print('packs/index.json')
    derived({p['id']: p for p in built})
