#!/usr/bin/env python3
"""Собирает наборы карточек для приложения из data/source/ в packs/.

Запуск: python3 tools/build_packs.py

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
    return {
        'id': 'ege-rus', 'title': 'ЕГЭ: русский язык', 'subject': 'Русский язык',
        'desc': 'Все тестовые задания ЕГЭ с разборами и теорией по Розенталю',
        'color': '#E4572E', 'topics': topics, 'theory': theory, 'cards': cards,
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
        'color': '#8A4FFF', 'topics': topics, 'theory': theory, 'cards': cards,
    }


if __name__ == '__main__':
    index = [write(econ_pack()), write(rus_pack()), write(stress_pack())]
    (OUT / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=1) + '\n', 'utf-8')
    print('packs/index.json')
