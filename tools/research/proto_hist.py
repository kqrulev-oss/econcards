"""История: прототипы заданий ЕГЭ (нумерация проекта КИМ 2027, 22 задания) и ОГЭ (2027, 23 задания)
и генераторы аналогов из базы событий data/research/history-events.json.

Правила:
- факты (даты, участники, процессы) берутся только из базы, и только из событий с checked=true;
- ответ каждой карточки считает код; функция verify() пересчитывает его независимо (другим путём —
  по индексу базы, а не по данным, из которых собиралась карточка);
- задания с картами, изображениями, источниками и развёрнутым ответом — только рецепты (llm / bank),
  генератора у них нет;
- тексты ФИПИ и коммерческих банков не используются; формулировки — свои.

Формат карточки: {"k": one|many|match|seq|word|num|open, "q", "a", "e", "data"}; поле data — структура,
по которой verify() пересчитывает ответ.
"""
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENTS_PATH = ROOT / 'data/research/history-events.json'

WORLD_SECTIONS = {'5', '11', '12'}
LETTERS = 'АБВГДЕ'
ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV',
         'XVI', 'XVII', 'XVIII', 'XIX', 'XX', 'XXI']

# ---------------------------------------------------------------- база событий


def _year(s):
    """Год начала и конца из строки даты базы ('1380', '1558–1583', '1941-06-22', '776 до н. э.')."""
    s = s.strip()
    bc = 'до н. э.' in s
    nums = [int(x) for x in re.findall(r'\d{3,4}', s.split('-')[0] if re.fullmatch(r'\d{4}-\d{2}-\d{2}', s) else s)]
    if not nums:
        return None, None
    a, b = nums[0], nums[-1]
    if bc:
        a, b = -a, -b
    return a, b


def load_events():
    data = json.loads(EVENTS_PATH.read_text('utf-8'))
    out = []
    for e in data['events']:
        if not e.get('checked'):
            continue
        a, b = _year(e['date'])
        if a is None:
            continue
        sec = e['codifier'].split('.')[0]
        out.append({
            'event': e['event'], 'date': e['date'], 'start': a, 'end': b, 'persons': list(e['persons']),
            'process': e['process'], 'section': sec, 'world': sec in WORLD_SECTIONS,
            'century': (a - 1) // 100 + 1 if a > 0 else -((-a - 1) // 100 + 1),
            'one_century': ((a - 1) // 100 == (b - 1) // 100) if a > 0 else True,
            'full_date': bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', e['date'])),
        })
    return out


def _unique_names(events):
    """События с одинаковыми названиями («Русско-турецкая война» ×3) без даты неоднозначны — в карточки не идут."""
    cnt = {}
    for e in events:
        cnt[e['event']] = cnt.get(e['event'], 0) + 1
    return [e for e in events if cnt[e['event']] == 1]


EVENTS = _unique_names(load_events())
BY_EVENT = {e['event']: e for e in EVENTS}
assert len(BY_EVENT) == len(EVENTS)
RUSSIA = [e for e in EVENTS if not e['world']]
WORLD = [e for e in EVENTS if e['world']]


def date_label(e):
    """'1380 г.', '1558–1583 гг.', '776 г. до н. э.'; полные даты — только год."""
    if e['start'] < 0:
        return f'{-e["start"]} г. до н. э.'
    if e['start'] != e['end']:
        return f'{e["start"]}–{e["end"]} гг.'
    return f'{e["start"]} г.'


def century_label(c):
    return f'{ROMAN[c]} в.' if c > 0 else f'{ROMAN[-c]} в. до н. э.'


def decade_label(e):
    return f'{e["start"] // 10 * 10}-е гг.' if e['start'] > 0 else date_label(e)


def cap_first(s):
    return s[:1].upper() + s[1:]


def numbered(items):
    return ' '.join(f'{i + 1}) {t}' for i, t in enumerate(items))


def lettered(items):
    return ' '.join(f'{LETTERS[i]}) {t}' for i, t in enumerate(items))


def pick_distinct_centuries(rng, pool, k, need_persons=False, one_century=True):
    """k событий из разных веков (чтобы участники и годы не пересекались)."""
    cands = [e for e in pool if (e['persons'] or not need_persons) and (e['one_century'] or not one_century)]
    rng.shuffle(cands)
    chosen, seen = [], set()
    for e in cands:
        if e['century'] in seen:
            continue
        chosen.append(e)
        seen.add(e['century'])
        if len(chosen) == k:
            return chosen
    return None


def norm_word(s):
    return re.sub(r'[\s\-–—.]', '', s).upper().replace('Ё', 'Е')


def leaks(event, person):
    """Имя участника «просвечивает» в названии события (Восстание Ивана Болотникова ↔ Иван Болотников)."""
    ev = event.lower()
    return any(tok[:5] in ev for tok in re.split(r'[\s\-]', person.lower()) if len(tok) >= 5)


def has_year(event):
    return bool(re.search(r'\d{3,4}', event))


# ---------------------------------------------------------------- ЕГЭ 1: события — годы


SINGLE = [e for e in RUSSIA if e['start'] == e['end'] and not has_year(e['event'])]
SINGLE_ALL = SINGLE + [e for e in WORLD if e['start'] == e['end'] and e['start'] > 0 and not has_year(e['event'])]


def gen_ege1(rng):
    ev = pick_distinct_centuries(rng, SINGLE, 4)
    years = [e['start'] for e in ev]
    extra = []
    others = [x for x in RUSSIA if x['start'] not in years and x['century'] in {e['century'] for e in ev}]
    rng.shuffle(others)
    for x in others:
        if x['start'] not in extra:
            extra.append(x['start'])
        if len(extra) == 2:
            break
    opts = sorted(years + extra)
    if len(set(opts)) < 6:
        return None
    ans = ''.join(str(opts.index(e['start']) + 1) for e in ev)
    q = ('Установите соответствие между событиями и годами: к каждой позиции первого столбца подберите '
         'соответствующую позицию из второго столбца. СОБЫТИЯ: ' + lettered([e['event'] for e in ev]) +
         '. ГОДЫ: ' + numbered([f'{y} г.' for y in opts]) + ' Запишите в ответ цифры под соответствующими буквами.')
    e_txt = '; '.join(f'{LETTERS[i]} — {date_label(e)}' for i, e in enumerate(ev))
    return {'k': 'match', 'q': q, 'a': ans, 'e': e_txt, 'data': {'events': [e['event'] for e in ev], 'opts': opts}}


def ver_ege1(card):
    d = card['data']
    return ''.join(str(d['opts'].index(BY_EVENT[n]['start']) + 1) for n in d['events'])


# ---------------------------------------------------------------- ЕГЭ 2 / ОГЭ 2: последовательность


def _non_overlapping(evs):
    s = sorted(evs, key=lambda e: e['start'])
    return all(s[i]['end'] < s[i + 1]['start'] for i in range(len(s) - 1))


def gen_seq(rng, n=3, with_world=True, pool=None):
    for _ in range(40):
        ru = rng.sample(RUSSIA if pool is None else pool, n - 1 if with_world else n)
        evs = ru + ([rng.choice(WORLD)] if with_world else [])
        if len({e['century'] for e in evs}) < 2 or not _non_overlapping(evs):
            continue
        order = list(range(n))
        rng.shuffle(order)
        shown = [evs[i] for i in order]
        ans = ''.join(str(shown.index(e) + 1) for e in sorted(evs, key=lambda e: e['start']))
        q = ('Расположите в хронологической последовательности исторические события. Запишите цифры, которыми '
             'обозначены события, в правильной последовательности. ' + numbered([e['event'] for e in shown]))
        return {'k': 'seq', 'q': q, 'a': ans,
                'e': ' → '.join(f'{e["event"]} ({date_label(e)})' for e in sorted(evs, key=lambda e: e['start'])),
                'data': {'shown': [e['event'] for e in shown]}}
    return None


def ver_seq(card):
    shown = card['data']['shown']
    ranked = sorted(range(len(shown)), key=lambda i: BY_EVENT[shown[i]]['start'])
    return ''.join(str(i + 1) for i in ranked)


# ---------------------------------------------------------------- ЕГЭ 3: процессы — факты


def gen_ege3(rng):
    procs = {}
    for e in RUSSIA:
        procs.setdefault(e['process'], []).append(e)
    names = [p for p, v in procs.items() if len(v) >= 1]
    for _ in range(40):
        chosen = rng.sample(names, 4)
        cents = [procs[p][0]['century'] for p in chosen]
        if len(set(cents)) < 4:
            continue
        facts = [rng.choice(procs[p]) for p in chosen]
        if any(norm_word(f['event'])[:12] in norm_word(p) or norm_word(p)[:12] in norm_word(f['event']) for f, p in zip(facts, chosen)):
            continue
        others = [e for e in RUSSIA if e['process'] not in chosen and e['century'] in set(cents)]
        if len(others) < 2:
            continue
        extra = rng.sample(others, 2)
        opts = facts + extra
        rng.shuffle(opts)
        ans = ''.join(str(opts.index(f) + 1) for f in facts)
        q = ('Установите соответствие между процессами (явлениями, событиями) и фактами, относящимися к этим '
             'процессам: к каждой позиции первого столбца подберите соответствующую позицию из второго столбца. '
             'ПРОЦЕССЫ: ' + lettered(chosen) + '. ФАКТЫ: ' + numbered([o['event'] for o in opts]) +
             '. Запишите в ответ цифры под соответствующими буквами.')
        return {'k': 'match', 'q': q, 'a': ans, 'e': '; '.join(f'{LETTERS[i]} — {f["event"]}' for i, f in enumerate(facts)),
                'data': {'procs': chosen, 'opts': [o['event'] for o in opts]}}
    return None


def ver_ege3(card):
    d = card['data']
    out = ''
    for p in d['procs']:
        hits = [i for i, o in enumerate(d['opts']) if BY_EVENT[o]['process'] == p]
        if len(hits) != 1:
            return None
        out += str(hits[0] + 1)
    return out


# ---------------------------------------------------------------- ЕГЭ 4: таблица событие — время — участник


def gen_ege4(rng):
    pool = [e for e in RUSSIA if not has_year(e['event']) and any(not leaks(e['event'], p) for p in e['persons'])]
    ev = pick_distinct_centuries(rng, pool, 3, need_persons=True)
    if not ev:
        return None
    rows, correct, gaps = [], [], []
    cents = {e['century'] for e in ev}
    for e in ev:
        cells = [e['event'], decade_label(e), rng.choice([p for p in e['persons'] if not leaks(e['event'], p)])]
        hidden = rng.sample(range(3), 2)
        row = []
        for j, c in enumerate(cells):
            if j in hidden:
                gaps.append((len(gaps), c, j))
                row.append(f'____({LETTERS[len(gaps) - 1]})')
            else:
                row.append(c)
        rows.append(row)
        correct += [cells[j] for j in sorted(hidden)]
    # три лишних элемента из других веков: событие, десятилетие, участник
    all_p = {p for e in ev for p in e['persons']}
    far = [x for x in RUSSIA if x['century'] not in cents and x['persons'] and not set(x['persons']) & all_p]
    rng.shuffle(far)
    extra = [far[0]['event'], decade_label(far[1]), far[2]['persons'][0]]
    if extra[1] in correct or len(set(correct + extra)) < 9:
        return None
    opts = correct + extra
    rng.shuffle(opts)
    ans = ''.join(str(opts.index(c) + 1) for c in correct)
    table = ' | '.join(f'{r[0]} — {r[1]} — {r[2]}' for r in rows)
    q = ('Заполните пустые ячейки таблицы, используя приведённый список пропущенных элементов: для каждого пропуска, '
         'обозначенного буквой, выберите номер нужного элемента. Столбцы: событие — время — участник. ' + table +
         '. Пропущенные элементы: ' + numbered(opts) + '. Запишите в ответ цифры под соответствующими буквами.')
    return {'k': 'match', 'q': q, 'a': ans, 'e': '; '.join(f'{LETTERS[i]} — {c}' for i, c in enumerate(correct)),
            'data': {'rows': rows, 'events': [e['event'] for e in ev], 'opts': opts}}


def ver_ege4(card):
    d = card['data']
    out = ''
    for row, name in zip(d['rows'], d['events']):
        e = BY_EVENT[name]
        for j, cell in enumerate(row):
            if cell.startswith('____'):
                if j == 0:
                    val = e['event']
                elif j == 1:
                    val = decade_label(e)
                else:
                    hits = [p for p in e['persons'] if p in d['opts']]
                    if len(hits) != 1:
                        return None
                    val = hits[0]
                out += str(d['opts'].index(val) + 1)
    return out


# ---------------------------------------------------------------- ЕГЭ 5: события — участники


def gen_ege5(rng, pool=None):
    pool = [e for e in (pool or RUSSIA) if any(not leaks(e['event'], p) for p in e['persons'])]
    ev = pick_distinct_centuries(rng, pool, 4, need_persons=True)
    if not ev:
        return None
    persons = [rng.choice([p for p in e['persons'] if not leaks(e['event'], p)]) for e in ev]
    for i, p in enumerate(persons):  # деятель не должен участвовать в другом выбранном событии (Пётр I в 1697 и 1721 гг.)
        if any(p in e['persons'] for j, e in enumerate(ev) if j != i):
            return None
    cents = {e['century'] for e in ev}
    all_p = {p for e in ev for p in e['persons']}
    far = [p for x in pool if x['century'] not in cents for p in x['persons'] if p not in all_p]
    if len(set(far)) < 2:
        return None
    extra = rng.sample(sorted(set(far)), 2)
    opts = persons + extra
    rng.shuffle(opts)
    ans = ''.join(str(opts.index(p) + 1) for p in persons)
    q = ('Установите соответствие между событиями и участниками этих событий: к каждой позиции первого столбца '
         'подберите соответствующую позицию из второго столбца. СОБЫТИЯ: ' + lettered([e['event'] for e in ev]) +
         '. УЧАСТНИКИ: ' + numbered(opts) + '. Запишите в ответ цифры под соответствующими буквами.')
    return {'k': 'match', 'q': q, 'a': ans, 'e': '; '.join(f'{LETTERS[i]} — {p}' for i, p in enumerate(persons)),
            'data': {'events': [e['event'] for e in ev], 'opts': opts}}


def ver_ege5(card):
    d = card['data']
    out = ''
    for n in d['events']:
        hits = [i for i, p in enumerate(d['opts']) if p in BY_EVENT[n]['persons']]
        if len(hits) != 1:
            return None
        out += str(hits[0] + 1)
    return out


# ---------------------------------------------------------------- ЕГЭ 7 / ОГЭ 14: памятники культуры (словарь)

# Свой краткий словарь; век и автор — общеизвестные факты (сверены с базой событий, где есть соответствующее событие).
MONUMENTS = [
    ('«Повесть временных лет»', 'литература', 12, 'Нестор', None),
    ('Софийский собор в Киеве', 'архитектура', 11, None, 'Ярослава Мудрого'),
    ('«Слово о полку Игореве»', 'литература', 12, None, None),
    ('Церковь Покрова на Нерли', 'архитектура', 12, None, 'Андрея Боголюбского'),
    ('Успенский собор во Владимире', 'архитектура', 12, None, 'Андрея Боголюбского'),
    ('«Задонщина»', 'литература', 15, None, None),
    ('Икона «Троица»', 'живопись', 15, 'Андрей Рублёв', None),
    ('Успенский собор Московского Кремля', 'архитектура', 15, 'Аристотель Фиораванти', 'Ивана III'),
    ('Грановитая палата', 'архитектура', 15, None, 'Ивана III'),
    ('«Хожение за три моря»', 'литература', 15, 'Афанасий Никитин', None),
    ('Собор Покрова на Рву (храм Василия Блаженного)', 'архитектура', 16, None, 'Ивана IV'),
    ('Церковь Вознесения в Коломенском', 'архитектура', 16, None, None),
    ('«Домострой»', 'литература', 16, None, None),
    ('«Апостол» — первая датированная печатная книга', 'литература', 16, 'Иван Фёдоров', 'Ивана IV'),
    ('«Житие протопопа Аввакума»', 'литература', 17, 'Аввакум', None),
    ('Дворец в Коломенском (деревянный)', 'архитектура', 17, None, 'Алексея Михайловича'),
    ('Церковь Покрова в Филях', 'архитектура', 17, None, None),
    ('Парсуна «Скопин-Шуйский»', 'живопись', 17, None, None),
    ('Здание Двенадцати коллегий', 'архитектура', 18, 'Доменико Трезини', 'Петра I'),
    ('Петропавловский собор', 'архитектура', 18, 'Доменико Трезини', 'Петра I'),
    ('Зимний дворец', 'архитектура', 18, 'Бартоломео Растрелли', None),
    ('«Медный всадник»', 'скульптура', 18, 'Этьен Фальконе', 'Екатерины II'),
    ('«Недоросль»', 'литература', 18, 'Денис Фонвизин', None),
    ('«Путешествие из Петербурга в Москву»', 'литература', 18, 'Александр Радищев', None),
    ('Казанский собор в Петербурге', 'архитектура', 19, 'Андрей Воронихин', 'Александра I'),
    ('«Последний день Помпеи»', 'живопись', 19, 'Карл Брюллов', None),
    ('Исаакиевский собор', 'архитектура', 19, 'Огюст Монферран', None),
    ('«Явление Христа народу»', 'живопись', 19, 'Александр Иванов', None),
    ('«Бурлаки на Волге»', 'живопись', 19, 'Илья Репин', None),
    ('«Утро стрелецкой казни»', 'живопись', 19, 'Василий Суриков', None),
    ('Храм Христа Спасителя (первый)', 'архитектура', 19, 'Константин Тон', None),
    ('«Чёрный квадрат»', 'живопись', 20, 'Казимир Малевич', None),
    ('Мавзолей В.И. Ленина (каменный)', 'архитектура', 20, 'Алексей Щусев', None),
    ('Скульптура «Рабочий и колхозница»', 'скульптура', 20, 'Вера Мухина', None),
    ('Главное здание МГУ на Воробьёвых горах', 'архитектура', 20, 'Лев Руднев', None),
    ('Поэма «Василий Тёркин»', 'литература', 20, 'Александр Твардовский', None),
]
MON = [{'name': n, 'kind': k, 'century': c, 'author': a, 'ruler': r} for n, k, c, a, r in MONUMENTS]
MON_BY = {m['name']: m for m in MON}


def _mon_chars(m):
    ch = [(f'создан в {century_label(m["century"])}', 'century', m['century'])]
    if m['author']:
        ch.append((f'автор — {m["author"]}', 'author', m['author']))
    if m['ruler']:
        ch.append((f'создан в правление {m["ruler"]}', 'ruler', m['ruler']))
    return ch


def gen_ege7(rng):
    for _ in range(40):
        ms = rng.sample(MON, 4)
        if len({m['century'] for m in ms}) < 4:
            continue
        chars = [rng.choice(_mon_chars(m)) for m in ms]
        used_cent = {m['century'] for m in ms}
        used_auth = {m['author'] for m in ms if m['author']}
        pool = [(f'создан в {century_label(c)}', 'century', c) for c in range(11, 21) if c not in used_cent]
        pool += [(f'автор — {m["author"]}', 'author', m['author']) for m in MON if m['author'] and m['author'] not in used_auth]
        extra = rng.sample(pool, 2)
        opts = chars + extra
        rng.shuffle(opts)
        ans = ''.join(str(opts.index(c) + 1) for c in chars)
        q = ('Установите соответствие между памятниками культуры и их краткими характеристиками: к каждой позиции '
             'первого столбца подберите соответствующую позицию из второго столбца. ПАМЯТНИКИ КУЛЬТУРЫ: ' +
             lettered([m['name'] for m in ms]) + '. ХАРАКТЕРИСТИКИ: ' + numbered([o[0] for o in opts]) +
             ' Запишите в ответ цифры под соответствующими буквами.')
        return {'k': 'match', 'q': q, 'a': ans, 'e': '; '.join(f'{LETTERS[i]} — {c[0]}' for i, c in enumerate(chars)),
                'data': {'mons': [m['name'] for m in ms], 'opts': [[o[1], o[2]] for o in opts]}}
    return None


def ver_ege7(card):
    d = card['data']
    out = ''
    for name in d['mons']:
        m = MON_BY[name]
        hits = [i for i, (t, v) in enumerate(d['opts'])
                if (t == 'century' and v == m['century']) or (t == 'author' and v == m['author']) or (t == 'ruler' and v == m['ruler'])]
        if len(hits) != 1:
            return None
        out += str(hits[0] + 1)
    return out


def gen_oge14(rng):
    for _ in range(40):
        ms = rng.sample(MON, 4)
        target = ms[0]
        mode = rng.choice(['century', 'author', 'ruler'])
        if mode == 'century':
            if sum(1 for m in ms if m['century'] == target['century']) != 1:
                continue
            ask = f'создан в {century_label(target["century"])}'
        elif mode == 'author' and target['author']:
            ask = None
        elif mode == 'ruler' and target['ruler']:
            if sum(1 for m in ms if m['ruler'] == target['ruler']) != 1:
                continue
            ask = f'создан в правление {target["ruler"]}'
        else:
            continue
        rng.shuffle(ms)
        if ask is None:
            q = (f'Автором какого из перечисленных памятников культуры является {target["author"]}? Укажите порядковый номер этого памятника. ' +
                 numbered([m['name'] for m in ms]))
        else:
            q = (f'Какой из перечисленных памятников культуры {ask}? Укажите порядковый номер этого памятника. ' +
                 numbered([m['name'] for m in ms]))
        return {'k': 'one', 'q': q, 'a': str(ms.index(target) + 1), 'e': target['name'],
                'data': {'mons': [m['name'] for m in ms], 'mode': mode, 'target': target['name']}}
    return None


def ver_oge14(card):
    d = card['data']
    t = MON_BY[d['target']]
    key = {'century': 'century', 'author': 'author', 'ruler': 'ruler'}[d['mode']]
    hits = [i for i, n in enumerate(d['mons']) if MON_BY[n][key] == t[key]]
    return str(hits[0] + 1) if len(hits) == 1 else None


# ---------------------------------------------------------------- термины (словарь для ОГЭ 3, 5; ЕГЭ 20)

# (термин, определение своими словами, раздел кодификатора, эпоха словами, группа)
TERMS = [
    ('полюдье', 'объезд князем с дружиной подвластных земель для сбора дани', '1', 'Древняя Русь', 'повинности'),
    ('вече', 'народное собрание в древнерусских городах, решавшее важнейшие вопросы', '1', 'Древняя Русь', 'органы власти'),
    ('вотчина', 'наследственное земельное владение, передававшееся от отца к сыну', '1', 'Древняя Русь', 'землевладение'),
    ('дружина', 'вооружённый отряд при князе, участвовавший в войнах и управлении', '1', 'Древняя Русь', 'военное дело'),
    ('уроки', 'фиксированный размер дани, установленный княгиней Ольгой', '1', 'Древняя Русь', 'повинности'),
    ('смерды', 'свободные земледельцы-общинники в Древней Руси', '1', 'Древняя Русь', 'категории населения'),
    ('холопы', 'зависимые люди, по положению близкие к рабам', '1', 'Древняя Русь', 'категории населения'),
    ('баскак', 'представитель ордынского хана, следивший за сбором дани в русских землях', '1', 'Русь под властью Орды', 'повинности'),
    ('ярлык', 'ханская грамота, дававшая право на княжение', '1', 'Русь под властью Орды', 'документы'),
    ('выход', 'дань, которую русские земли платили Золотой Орде', '1', 'Русь под властью Орды', 'повинности'),
    ('кормление', 'содержание должностных лиц за счёт местного населения', '1', 'Русское государство XV–XVI вв.', 'органы власти'),
    ('поместье', 'земельное владение, дававшееся за военную службу без права наследования по общему правилу', '2', 'Россия XVI–XVII вв.', 'землевладение'),
    ('опричнина', 'политика Ивана IV: особый удел царя и террор против «изменников»', '2', 'Россия XVI в.', 'внутренняя политика'),
    ('приказы', 'центральные органы управления в России XVI–XVII вв.', '2', 'Россия XVI–XVII вв.', 'органы власти'),
    ('Земский собор', 'сословно-представительное собрание в России XVI–XVII вв.', '2', 'Россия XVI–XVII вв.', 'органы власти'),
    ('стрельцы', 'служилые люди, составлявшие постоянное войско с огнестрельным оружием', '2', 'Россия XVI–XVII вв.', 'военное дело'),
    ('заповедные лета', 'годы, когда крестьянам запрещался переход от одного владельца к другому', '2', 'Россия XVI в.', 'крепостное право'),
    ('урочные лета', 'срок сыска беглых крестьян', '2', 'Россия XVI–XVII вв.', 'крепостное право'),
    ('местничество', 'порядок назначения на должности по знатности рода', '2', 'Россия XVI–XVII вв.', 'органы власти'),
    ('Семибоярщина', 'боярское правительство в Москве после свержения Василия Шуйского', '2', 'Смутное время', 'органы власти'),
    ('раскол', 'разделение Русской церкви после реформ патриарха Никона', '2', 'Россия XVII в.', 'церковь'),
    ('старообрядцы', 'противники церковной реформы Никона, сохранившие старые обряды', '2', 'Россия XVII в.', 'церковь'),
    ('мануфактура', 'крупное предприятие с ручным трудом и разделением труда', '2', 'Россия XVII в.', 'хозяйство'),
    ('Сенат', 'высший орган управления и суда, созданный Петром I', '3', 'Россия XVIII в.', 'органы власти'),
    ('коллегии', 'центральные учреждения, заменившие приказы при Петре I', '3', 'Россия XVIII в.', 'органы власти'),
    ('Синод', 'высший орган управления церковью, учреждённый Петром I', '3', 'Россия XVIII в.', 'церковь'),
    ('рекруты', 'лица, набранные в армию по повинности от податных сословий', '3', 'Россия XVIII в.', 'военное дело'),
    ('подушная подать', 'прямой налог с каждой мужской души податных сословий', '3', 'Россия XVIII в.', 'повинности'),
    ('Табель о рангах', 'закон о порядке государственной службы и чинах', '3', 'Россия XVIII в.', 'документы'),
    ('Кондиции', 'условия, которые Верховный тайный совет предложил Анне Иоанновне', '3', 'Россия XVIII в.', 'документы'),
    ('секуляризация', 'передача церковных земель и имущества в собственность государства', '3', 'Россия XVIII в.', 'церковь'),
    ('Уложенная комиссия', 'собрание представителей сословий для составления нового свода законов при Екатерине II', '3', 'Россия XVIII в.', 'органы власти'),
    ('министерства', 'центральные органы управления, созданные при Александре I вместо коллегий', '4', 'Россия XIX в.', 'органы власти'),
    ('Государственный совет', 'высший законосовещательный орган Российской империи, учреждённый в 1810 г.', '4', 'Россия XIX в.', 'органы власти'),
    ('военные поселения', 'особая форма содержания войск, при которой солдаты совмещали службу с сельским трудом', '4', 'Россия XIX в.', 'военное дело'),
    ('декабристы', 'участники тайных обществ, поднявших восстание в декабре 1825 г.', '4', 'Россия XIX в.', 'общественное движение'),
    ('западники', 'сторонники развития России по европейскому пути', '4', 'Россия XIX в.', 'общественное движение'),
    ('славянофилы', 'сторонники самобытного пути развития России', '4', 'Россия XIX в.', 'общественное движение'),
    ('временнообязанные', 'крестьяне, после 1861 г. несущие повинности до выкупа земли', '4', 'Россия XIX в.', 'крепостное право'),
    ('земства', 'выборные органы местного самоуправления, созданные в 1864 г.', '4', 'Россия XIX в.', 'органы власти'),
    ('народники', 'участники движения, видевшего основу будущего в крестьянской общине', '4', 'Россия XIX в.', 'общественное движение'),
    ('отрезки', 'часть земли, отошедшая помещикам от крестьянских наделов при реформе 1861 г.', '4', 'Россия XIX в.', 'крепостное право'),
    ('Государственная дума', 'выборный законодательный орган, созданный в ходе революции 1905–1907 гг.', '4', 'Россия начала XX в.', 'органы власти'),
    ('отруб', 'участок земли, выделенный крестьянину в одном месте при выходе из общины', '4', 'Россия начала XX в.', 'землевладение'),
    ('хутор', 'обособленное крестьянское хозяйство с усадьбой на выделенной земле', '4', 'Россия начала XX в.', 'землевладение'),
    ('продразвёрстка', 'обязательная сдача крестьянами государству излишков хлеба по твёрдым нормам', '7', 'Советская Россия', 'хозяйство'),
    ('нэп', 'экономическая политика 1920-х гг. с допущением частной торговли и рынка', '7', 'СССР 1920-х гг.', 'хозяйство'),
    ('коллективизация', 'объединение крестьянских хозяйств в колхозы', '7', 'СССР 1930-х гг.', 'хозяйство'),
    ('индустриализация', 'создание крупной промышленности, прежде всего тяжёлой', '7', 'СССР 1930-х гг.', 'хозяйство'),
    ('ГУЛАГ', 'система лагерей для заключённых в СССР', '7', 'СССР 1930-х гг.', 'внутренняя политика'),
    ('совнархозы', 'территориальные органы управления промышленностью, созданные при Хрущёве', '9', 'СССР 1950–1960-х гг.', 'органы власти'),
    ('целина', 'освоение неиспользуемых земель в Казахстане и Сибири в 1950-х гг.', '9', 'СССР 1950-х гг.', 'хозяйство'),
    ('гласность', 'политика открытости и свободы обсуждения в годы перестройки', '9', 'СССР 1980-х гг.', 'внутренняя политика'),
    ('приватизация', 'передача государственной собственности в частные руки', '10', 'Россия 1990-х гг.', 'хозяйство'),
]
TERM = [{'term': t, 'def': d, 'section': s, 'era': e, 'group': g} for t, d, s, e, g in TERMS]
TERM_BY = {t['term']: t for t in TERM}
SECTION_ORDER = ['1', '2', '3', '4', '7', '9', '10']


def gen_oge3(rng):
    t = rng.choice(TERM)
    q = f'Запишите термин, о котором идёт речь. {cap_first(t["def"])}.'
    return {'k': 'word', 'q': q, 'a': norm_word(t['term']), 'e': f'{t["term"]} ({t["era"]})', 'data': {'def': t['def']}}


def ver_oge3(card):
    hits = [t for t in TERM if t['def'] == card['data']['def']]
    return norm_word(hits[0]['term']) if len(hits) == 1 else None


def gen_oge5(rng):
    for _ in range(40):
        sec = rng.choice(SECTION_ORDER)
        same = [t for t in TERM if t['section'] == sec]
        if len(same) < 4:
            continue
        far_secs = [s for s in SECTION_ORDER if abs(SECTION_ORDER.index(s) - SECTION_ORDER.index(sec)) >= 2]
        far = [t for t in TERM if t['section'] in far_secs]
        row = rng.sample(same, 4) + [rng.choice(far)]
        odd = row[-1]
        rng.shuffle(row)
        era = same[0]['era'] if len({t['era'] for t in same}) == 1 else {
            '1': 'истории Руси IX–XV вв.', '2': 'истории России XVI–XVII вв.', '3': 'истории России XVIII в.',
            '4': 'истории России XIX – начала XX в.', '7': 'истории СССР 1917–1930-х гг.', '9': 'истории СССР 1945–1991 гг.',
            '10': 'истории России 1990-х гг.'}[sec]
        era_txt = era if era.startswith('истории') else 'периоду: ' + era
        q = (f'Ниже приведён перечень терминов. Все они, за исключением одного, относятся к {era_txt.rstrip(".")}. '
             'Найдите и укажите порядковый номер термина, «выпадающего» из данного ряда. ' +
             '; '.join(f'{i + 1}) {t["term"]}' for i, t in enumerate(row)) + '.')
        return {'k': 'one', 'q': q, 'a': str(row.index(odd) + 1), 'e': f'{odd["term"]} — {odd["era"]}',
                'data': {'row': [t['term'] for t in row], 'section': sec}}
    return None


def ver_oge5(card):
    d = card['data']
    hits = [i for i, n in enumerate(d['row']) if TERM_BY[n]['section'] != d['section']]
    return str(hits[0] + 1) if len(hits) == 1 else None


def gen_ege20(rng):
    t = rng.choice(TERM)
    q = (f'Вспомните смысл понятия «{t["term"]}». Дайте определение понятия и укажите, к какому периоду истории России '
         'оно относится.')
    return {'k': 'open', 'q': q, 'a': f'{cap_first(t["def"])}; {t["era"]}', 'e': 'проверка по словарю терминов',
            'data': {'term': t['term']}}


def ver_ege20(card):
    t = TERM_BY[card['data']['term']]
    return f'{cap_first(t["def"])}; {t["era"]}'


# ---------------------------------------------------------------- ОГЭ 1: события — годы (3×5)


def gen_oge1(rng):
    ev = pick_distinct_centuries(rng, SINGLE_ALL, 3)
    years = [e['start'] for e in ev]
    if any(y <= 0 for y in years):
        return None
    others = [x['start'] for x in RUSSIA if x['start'] not in years and x['century'] in {e['century'] for e in ev} and x['start'] > 0]
    extra = []
    rng.shuffle(others)
    for y in others:
        if y not in extra:
            extra.append(y)
        if len(extra) == 2:
            break
    opts = sorted(years + extra)
    if len(set(opts)) < 5:
        return None
    ans = ''.join(str(opts.index(y) + 1) for y in years)
    q = ('Установите соответствие между событиями и годами: к каждой позиции первого столбца подберите '
         'соответствующую позицию из второго столбца. СОБЫТИЯ: ' + lettered([e['event'] for e in ev]) +
         '. ГОДЫ: ' + numbered([f'{y} г.' for y in opts]) + ' Запишите в ответ цифры под соответствующими буквами.')
    return {'k': 'match', 'q': q, 'a': ans, 'e': '; '.join(f'{LETTERS[i]} — {date_label(e)}' for i, e in enumerate(ev)),
            'data': {'events': [e['event'] for e in ev], 'opts': opts}}


# ---------------------------------------------------------------- ОГЭ 4: несколько верных из пяти (участники / события периода)


def gen_oge4_persons(rng):
    procs = {}
    for e in RUSSIA:
        procs.setdefault(e['process'], []).append(e)
    for _ in range(60):
        p, evs = rng.choice(list(procs.items()))
        persons = sorted({x for e in evs for x in e['persons']})
        cands = [x for x in persons if not leaks(p, x)]
        if len(cands) < 2:
            continue
        k = min(len(cands), rng.choice([2, 3]))
        right = rng.sample(cands, k)
        cents = {e['century'] for e in evs}
        far = sorted({x for e in RUSSIA if e['century'] not in cents for x in e['persons']} - set(persons))
        wrong = rng.sample(far, 5 - k)
        opts = right + wrong
        rng.shuffle(opts)
        ans = ''.join(sorted(str(opts.index(x) + 1) for x in right))
        q = (f'Кто из перечисленных исторических деятелей был участником событий, относящихся к процессу '
             f'«{p}»? Найдите в приведённом списке {"двух" if k == 2 else "трёх"} деятелей и запишите цифры, под '
             'которыми они указаны. ' + numbered(opts))
        return {'k': 'many', 'q': q, 'a': ans, 'e': ', '.join(right), 'data': {'process': p, 'opts': opts}}
    return None


def ver_oge4_persons(card):
    d = card['data']
    persons = {x for e in RUSSIA if e['process'] == d['process'] for x in e['persons']}
    return ''.join(sorted(str(i + 1) for i, o in enumerate(d['opts']) if o in persons))


def gen_oge4_century(rng):
    for _ in range(40):
        c = rng.choice(range(10, 21))
        inside = [e for e in RUSSIA if e['century'] == c and e['one_century']]
        outside = [e for e in RUSSIA if e['one_century'] and abs(e['century'] - c) >= 2]
        if len(inside) < 3 or len(outside) < 3:
            continue
        k = rng.choice([2, 3])
        right = rng.sample(inside, k)
        opts = right + rng.sample(outside, 5 - k)
        rng.shuffle(opts)
        ans = ''.join(sorted(str(opts.index(x) + 1) for x in right))
        q = (f'Какие из перечисленных событий произошли в {century_label(c)}? Найдите в приведённом списке '
             f'{"два" if k == 2 else "три"} события и запишите цифры, под которыми они указаны. ' +
             numbered([o['event'] for o in opts]))
        return {'k': 'many', 'q': q, 'a': ans, 'e': '; '.join(f'{r["event"]} ({date_label(r)})' for r in right),
                'data': {'century': c, 'opts': [o['event'] for o in opts]}}
    return None


def ver_oge4_century(card):
    d = card['data']
    return ''.join(sorted(str(i + 1) for i, o in enumerate(d['opts']) if BY_EVENT[o]['century'] == d['century']))


# ---------------------------------------------------------------- ОГЭ 12: пропуск в схеме (событие — год)


def gen_oge12(rng):
    procs = {}
    for e in RUSSIA:
        if e['start'] == e['end'] and not e['full_date']:
            procs.setdefault(e['process'], []).append(e)
    good = [(p, v) for p, v in procs.items() if len(v) >= 3]
    p, evs = rng.choice(good)
    three = sorted(rng.sample(evs, 3), key=lambda e: e['start'])
    if len({e['start'] for e in three}) < 3:
        return None
    hidden = three.pop(rng.randrange(3))
    three.append(hidden)
    q = (f'Заполните пропуск в схеме. «{p}»: ' + '; '.join(f'{e["event"]} — {e["start"]} г.' for e in three[:-1]) +
         f'; {hidden["event"]} — ? Запишите год.')
    return {'k': 'num', 'q': q, 'a': str(hidden['start']), 'e': f'{hidden["event"]} — {date_label(hidden)}',
            'data': {'hidden': hidden['event']}}


def ver_oge12(card):
    return str(BY_EVENT[card['data']['hidden']]['start'])


# ---------------------------------------------------------------- ОГЭ 15–16: всеобщая история


def gen_oge15(rng):
    for _ in range(40):
        evs = pick_distinct_centuries(rng, WORLD, 4, need_persons=True, one_century=False)
        if not evs:
            return None
        target = rng.choice(evs)
        person = rng.choice(target['persons'])
        if any(person in e['persons'] for e in evs if e is not target):
            continue
        q = (f'Прочитайте перечень событий, процессов из истории зарубежных стран: ' + numbered([e['event'] for e in evs]) +
             f'. Участником какого из перечисленных событий, процессов был {person}? Укажите порядковый номер этого события.')
        return {'k': 'one', 'q': q, 'a': str(evs.index(target) + 1), 'e': f'{target["event"]} ({date_label(target)})',
                'data': {'opts': [e['event'] for e in evs], 'person': person}}
    return None


def ver_oge15(card):
    d = card['data']
    hits = [i for i, n in enumerate(d['opts']) if d['person'] in BY_EVENT[n]['persons']]
    return str(hits[0] + 1) if len(hits) == 1 else None


def gen_oge16(rng):
    for _ in range(40):
        evs = pick_distinct_centuries(rng, WORLD, 4)
        if not evs:
            return None
        target = rng.choice(evs)
        mode = rng.choice(['century', 'earliest', 'latest'])
        if mode == 'century':
            ask = f'Какое из перечисленных событий произошло в {century_label(target["century"])}?'
        elif mode == 'earliest':
            target = min(evs, key=lambda e: e['start'])
            ask = 'Какое из перечисленных событий произошло раньше остальных?'
        else:
            target = max(evs, key=lambda e: e['start'])
            ask = 'Какое из перечисленных событий произошло позже остальных?'
        q = ('Прочитайте перечень событий, процессов из истории зарубежных стран: ' + numbered([e['event'] for e in evs]) +
             f'. {ask} Укажите порядковый номер этого события.')
        return {'k': 'one', 'q': q, 'a': str(evs.index(target) + 1), 'e': f'{target["event"]} ({date_label(target)})',
                'data': {'opts': [e['event'] for e in evs], 'mode': mode, 'century': target['century']}}
    return None


def ver_oge16(card):
    d = card['data']
    es = [BY_EVENT[n] for n in d['opts']]
    if d['mode'] == 'century':
        hits = [i for i, e in enumerate(es) if e['century'] == d['century']]
        return str(hits[0] + 1) if len(hits) == 1 else None
    key = min if d['mode'] == 'earliest' else max
    t = key(es, key=lambda e: e['start'])
    return str(es.index(t) + 1)


# ---------------------------------------------------------------- ОГЭ 21 (2027): найди ошибки в тексте


def gen_oge21(rng):
    procs = {}
    for e in RUSSIA:
        if e['persons'] and e['start'] == e['end'] and not e['full_date']:
            procs.setdefault(e['process'], []).append(e)
    good = [(p, v) for p, v in procs.items() if len(v) >= 3]
    for _ in range(40):
        p, evs = rng.choice(good)
        three = rng.sample(evs, 3)
        cents = {e['century'] for e in three}
        far = [x for x in RUSSIA if x['century'] not in cents and x['persons'] and x['start'] > 0]
        sents, truth = [], []
        for e in three:
            person = rng.choice(e['persons'])
            sents.append({'event': e['event'], 'year': e['start'], 'person': person})
            truth.append(True)
        # две ошибки: дата и участник — из событий других веков
        bad_idx = rng.sample(range(3), 2)
        f1, f2 = rng.sample(far, 2)
        sents[bad_idx[0]]['year'] = f1['start']
        sents[bad_idx[1]]['person'] = f2['persons'][0]
        order = list(range(3))
        rng.shuffle(order)
        shown = [sents[i] for i in order]
        text = ' '.join(f'({i + 1}) {cap_first(s["event"])} — событие {s["year"]} г.; среди его участников — {s["person"]}.' for i, s in enumerate(shown))
        wrong = sorted(str(order.index(i) + 1) for i in bad_idx)
        q = (f'Прочитайте текст о процессе «{p}», в котором допущены две фактические ошибки. Укажите номера предложений, '
             'в которых допущены ошибки. ' + text)
        return {'k': 'many', 'q': q, 'a': ''.join(wrong),
                'e': f'ошибки: год «{f1["start"]}» относится к событию «{f1["event"]}»; {f2["persons"][0]} — участник события «{f2["event"]}»',
                'data': {'shown': shown}}
    return None


def ver_oge21(card):
    out = []
    for i, s in enumerate(card['data']['shown']):
        e = BY_EVENT[s['event']]
        if s['year'] != e['start'] or s['person'] not in e['persons']:
            out.append(str(i + 1))
    return ''.join(out)


# ---------------------------------------------------------------- «что раньше» (тренировочная форма для ЕГЭ 2 / ОГЭ 2)


def gen_earlier(rng):
    for _ in range(40):
        a, b = rng.sample(RUSSIA, 2)
        if a['century'] == b['century'] or not _non_overlapping([a, b]):
            continue
        first = a if a['start'] < b['start'] else b
        q = f'Какое событие произошло раньше? 1) {a["event"]} 2) {b["event"]}'
        return {'k': 'one', 'q': q, 'a': '1' if first is a else '2', 'e': f'{first["event"]} — {date_label(first)}',
                'data': {'opts': [a['event'], b['event']]}}
    return None


def ver_earlier(card):
    o = card['data']['opts']
    return '1' if BY_EVENT[o[0]]['start'] < BY_EVENT[o[1]]['start'] else '2'


# ---------------------------------------------------------------- каталог


def P(pid, exam, n, title, kes, invariant, varies, answer_rule, mistakes, level, score, answer, gen=None, ver=None,
      kind='param', recipe=None, need=None, n2026=None, mini=None):
    g = {'kind': kind}
    if gen is not None:
        g['fn'] = f'proto_hist.{gen.__name__}'
    if recipe:
        g['recipe'] = recipe
    if need:
        g['need'] = need
    if mini:
        g['mini'] = mini
    return {
        'id': pid, 'exam': exam, 'n': n, 'n2026': n2026, 'title': title, 'kes': kes,
        'invariant': invariant, 'varies': varies, 'answer_rule': answer_rule, 'mistakes': mistakes,
        'gen': g, 'passport': {'level': level, 'score': score, 'answer': answer, 'form': 'бланк ответов № 1' if answer != 'развёрнутый' else 'бланк ответов № 2', 'kes': kes},
        '_gen': gen, '_ver': ver,
    }


DATES = 'даты; соседние годы одного процесса; события одного правления'
WORLD_MIX = 'одно из событий — всеобщая история'

PROTOS = [
    # --- ЕГЭ (2027)
    P('hist-ege-01-event-year', 'ЕГЭ', 1, 'Соответствие: события — годы (4×6)', 'Знание дат: история России IX–XXI вв.',
      'четыре события из разных веков, шесть годов; два лишних года — годы других событий тех же веков',
      'события, годы, порядок', 'по базе событий: год начала события; ответ — четыре цифры под буквами А–Г',
      ['соседние годы одного процесса', 'век события помнится, год — нет'], 'Б', 2, '4 цифры', gen_ege1, ver_ege1),
    P('hist-ege-02-seq-world', 'ЕГЭ', 2, 'Хронологическая последовательность: 2 события России + 1 всеобщей истории', 'Хронология',
      'три события, одно из всеобщей истории; события не пересекаются по годам', 'события, порядок предъявления',
      'сортировка по году начала; ответ — три цифры в порядке следования',
      ['событие всеобщей истории не привязано к русской хронологии', 'путают начало и конец длительного процесса'],
      'Б', 1, '3 цифры', lambda r: gen_seq(r, 3, True), ver_seq),
    P('hist-ege-02-seq-russia', 'ЕГЭ', 2, 'Хронологическая последовательность: 3 события истории России', 'Хронология',
      'три события истории России из разных веков', 'события, порядок', 'сортировка по году начала; ответ — три цифры',
      ['события одного века без опоры на дату'], 'Б', 1, '3 цифры', lambda r: gen_seq(r, 3, False), ver_seq),
    P('hist-ege-03-process-fact', 'ЕГЭ', 3, 'Соответствие: процессы — факты (4×6)', 'Процессы и относящиеся к ним факты',
      'четыре процесса из разных веков, шесть фактов; два лишних — события других процессов тех же веков',
      'процессы, факты', 'факт относится к процессу по полю process базы; ответ — четыре цифры',
      ['факт того же века, но другого процесса'], 'Б', 2, '4 цифры', gen_ege3, ver_ege3),
    P('hist-ege-04-table', 'ЕГЭ', 4, 'Таблица: событие — время — участник (6 пропусков, 9 элементов)', 'Систематизация фактов',
      'три строки из разных веков, в каждой скрыты две из трёх ячеек; три лишних элемента — из других веков',
      'события, скрытые ячейки, участники', 'по базе: событие → десятилетие и участник; ответ — шесть цифр под А–Е',
      ['десятилетие вместо года: «1550-е гг.» для события 1552 г.', 'участник соседнего события того же правления'],
      'П', 3, '6 цифр', gen_ege4, ver_ege4),
    P('hist-ege-05-event-person', 'ЕГЭ', 5, 'Соответствие: события — участники (4×6)', 'Исторические деятели',
      'четыре события из разных веков, шесть участников; два лишних — деятели других веков',
      'события, участники', 'участник указан в поле persons события; ответ — четыре цифры',
      ['современник, не участвовавший в событии', 'полководец соседней войны'], 'Б', 2, '4 цифры', gen_ege5, ver_ege5),
    P('hist-ege-06-source-true', 'ЕГЭ', 6, 'Письменный источник: верные суждения', 'Работа с историческим источником',
      'отрывок из источника в общественном достоянии, шесть суждений, три верных', 'источник, суждения',
      'три цифры в любом порядке', ['суждение о соседнем событии', 'дата по автору, а не по событию'], 'П', 2, '3 цифры',
      kind='bank', recipe='Отрывки только из документов в общественном достоянии (указы, манифесты, летописи в старом переводе); суждения пишет ИИ по базе событий, даты и участники — только из базы; вычитка экспертом.',
      need='банк источников'),
    P('hist-ege-07-culture-match', 'ЕГЭ', 7, 'Культура: памятники — характеристики (4×6)', 'Культура России',
      'четыре памятника из разных веков, шесть характеристик (век, автор, правление); две лишних',
      'памятники, вид характеристики', 'по словарю памятников (36 строк); ответ — четыре цифры',
      ['памятник XVII в. относят к XVI в.', 'Растрелли ↔ Трезини'], 'Б', 2, '4 цифры', gen_ege7, ver_ege7, kind='dict'),
    P('hist-ege-08-vov-image', 'ЕГЭ', 8, 'Великая Отечественная война: изображение → слово', 'Великая Отечественная война',
      'плакат, марка или карта-схема; пропуск в предложении', 'изображение, предложение', 'слово (словосочетание)',
      ['год выпуска марки путают с годом события'], 'Б', 1, 'слово', kind='bank',
      recipe='Только изображения со свободной лицензией (фото Wikimedia Commons, документы); плакаты с живыми правами не брать. Пропуск — из базы событий раздела 8.', need='изображения'),
    P('hist-ege-09-map-ruler', 'ЕГЭ', 9, 'Карта: правитель / век события (слово)', 'Историческая карта',
      'схема военных действий или территориальных изменений; пропуск в предложении', 'карта, вопрос', 'слово',
      ['правитель по столице, а не по дате'], 'Б', 1, 'слово', kind='bank',
      recipe='Своя SVG-схема по контурам из открытых источников; вопросы «в правление кого», «в каком веке» — из базы событий.', need='карта-схема'),
    P('hist-ege-10-map-object', 'ЕГЭ', 10, 'Карта: название объекта (город, река) под цифрой', 'Историческая карта',
      'та же схема; объект обозначен цифрой', 'объект', 'слово', ['современное название вместо исторического'], 'Б', 1, 'слово',
      kind='bank', recipe='Та же схема, что для 9; список объектов и их исторические названия — своя таблица.', need='карта-схема'),
    P('hist-ege-11-map-text', 'ЕГЭ', 11, 'Карта + текст: пропущенное название', 'Историческая карта',
      'текст о событиях схемы с пропуском', 'текст, пропуск', 'слово', ['пропуск заполняют по тексту, не по карте'], 'П', 1, 'слово',
      kind='llm', recipe='Текст пишет ИИ по базе событий и легенде схемы; пропущенное слово — из легенды; проверка совпадения кодом.', need='карта-схема'),
    P('hist-ege-12-map-true', 'ЕГЭ', 12, 'Карта: верные суждения (3 из 6)', 'Историческая карта',
      'шесть суждений о схеме, три верных', 'суждения', 'три цифры в любом порядке',
      ['суждение верно для эпохи, но не для схемы'], 'Б', 2, '3 цифры', kind='llm',
      recipe='Суждения о датах, правителях, городах — по базе событий и легенде схемы; неверные — замена года/правителя из базы; вычитка.', need='карта-схема'),
    P('hist-ege-13-source-attr', 'ЕГЭ', 13, 'Источник: атрибуция (автор, год, правитель)', 'Работа с источником',
      'отрывок, два вопроса на атрибуцию', 'источник', 'развёрнутый', ['год по дате публикации, а не события'], 'П', 2, 'развёрнутый',
      kind='bank', recipe='Источники в общественном достоянии; ключ — из базы событий.', need='банк источников'),
    P('hist-ege-14-source-info', 'ЕГЭ', 14, 'Источник: поиск информации', 'Работа с источником',
      'вопрос по содержанию отрывка', 'источник, вопрос', 'развёрнутый', ['ответ «от себя», не из текста'], 'Б', 2, 'развёрнутый',
      kind='bank', recipe='Тот же банк источников; вопрос и ключ пишет ИИ, проверка — цитата из отрывка должна содержать ответ.', need='банк источников'),
    P('hist-ege-15-world-source', 'ЕГЭ', 15, 'Источник по всеобщей истории: контекст (новое в 2027)', 'Всеобщая история',
      'отрывок из документа всеобщей истории; вопрос на контекст (страна, событие, век)', 'источник', 'развёрнутый',
      ['перенос контекста истории России на всеобщую'], 'П', 2, 'развёрнутый', kind='bank',
      recipe='Документы в общественном достоянии (декларации, хартии, договоры до XX в.); ключ — из событий разделов 5, 11, 12 базы.', need='банк источников'),
    P('hist-ege-16-image-conclusion', 'ЕГЭ', 16, 'Изображение: вывод + объяснение', 'Культура, ВОВ', 'изображение (марка, медаль, плакат)',
      'изображение', 'развёрнутый', ['вывод без опоры на изображение'], 'П', 2, 'развёрнутый', kind='bank', n2026=15,
      recipe='Изображения со свободной лицензией; ключ — из базы событий.', need='изображения'),
    P('hist-ege-17-image-choice', 'ЕГЭ', 17, 'Изображение: выбор памятника + факт', 'Культура', 'четыре изображения, выбор по признаку',
      'изображения', 'развёрнутый', ['век памятника'], 'П', 2, 'развёрнутый', kind='bank', n2026=16,
      recipe='Изображения памятников архитектуры, чьи авторы умерли более 70 лет назад; признаки — из словаря памятников.', need='изображения'),
    P('hist-ege-18-vov-two-sources', 'ЕГЭ', 18, 'Великая Отечественная война: два источника', 'Великая Отечественная война',
      'два отрывка об одном событии', 'отрывки', 'развёрнутый', ['битва по географии, а не по описанию'], 'П', 3, 'развёрнутый',
      kind='bank', n2026=17, recipe='Официальные сводки Совинформбюро и приказы (общественное достояние); мемуары — только с истёкшими правами.', need='банк источников'),
    P('hist-ege-19-causes', 'ЕГЭ', 19, 'Причины и следствия (а, б, в)', 'Причинно-следственные связи',
      'событие, три пункта: причина, следствие, влияние', 'событие', 'развёрнутый', ['следствие названо причиной'], 'В', 3, 'развёрнутый',
      kind='llm', n2026=18, recipe='ИИ пишет пункты по событию из базы; проверка вторым проходом: каждый пункт должен опираться на событие базы с датой; спорные — в ручную очередь.'),
    P('hist-ege-20-term', 'ЕГЭ', 20, 'Историческое понятие: смысл и период', 'Исторические понятия',
      'понятие из словаря терминов (55 строк): определение + период', 'термин', 'развёрнутый (мини: сверка с определением словаря)',
      ['определение соседнего термина', 'период указан веком раньше'], 'П', 2, 'развёрнутый', gen_ege20, ver_ege20, kind='dict',
      n2026=19, mini='в КИМ ещё вопрос на факт о понятии; здесь — определение и период'),
    P('hist-ege-21-compare', 'ЕГЭ', 21, 'Сравнение: тезис о сходстве/различии + два обоснования', 'Сравнение процессов',
      'два процесса из базы, тезис, два обоснования фактами', 'процессы', 'развёрнутый', ['обоснование без факта'], 'В', 3, 'развёрнутый',
      kind='llm', n2026=20, recipe='Пары процессов подбирает код (одна тема, разные века); тезис и обоснования пишет ИИ, факты проверяются по базе.'),
    P('hist-ege-22-arguments', 'ЕГЭ', 22, 'Аргументы к точке зрения (история России)', 'Аргументация',
      'точка зрения; два аргумента с фактами', 'точка зрения', 'развёрнутый', ['аргумент — пересказ точки зрения'], 'В', 3, 'развёрнутый',
      kind='llm', n2026=21, recipe='Точки зрения — из своего списка; ИИ-проверка аргументов на наличие факта из базы событий.'),
    # --- ОГЭ (2027)
    P('hist-oge-01-event-year', 'ОГЭ', 1, 'Соответствие: события — годы (3×5)', 'Знание дат',
      'три события из разных веков (возможно одно из всеобщей истории), пять годов', 'события, годы', 'год начала по базе; ответ — три цифры',
      ['соседние годы одного века'], 'Б', 2, '3 цифры', gen_oge1, ver_ege1),
    P('hist-oge-02-seq', 'ОГЭ', 2, 'Хронологическая последовательность (3 события, одно — всеобщая история)', 'Хронология',
      'три события, одно из всеобщей истории', 'события', 'сортировка по году начала; ответ — три цифры',
      ['всеобщая история не привязана к русской хронологии'], 'П', 1, '3 цифры', lambda r: gen_seq(r, 3, True), ver_seq),
    P('hist-oge-02-earlier', 'ОГЭ', 2, 'Что раньше: два события (тренировочная форма)', 'Хронология',
      'два события разных веков', 'события', 'меньший год начала; ответ — 1 или 2', ['события одного правления'], 'П', 1, '1 цифра',
      gen_earlier, ver_earlier, mini='упражнение к заданию 2, в КИМ такой формы нет'),
    P('hist-oge-03-term-def', 'ОГЭ', 3, 'Термин по определению (слово)', 'Исторические понятия',
      'определение из словаря терминов', 'термин', 'слово; сравнение без регистра и ё', ['смерды ↔ холопы', 'заповедные ↔ урочные лета'],
      'Б', 1, 'слово', gen_oge3, ver_oge3, kind='dict'),
    P('hist-oge-04-persons', 'ОГЭ', 4, 'Участники процесса: несколько верных из пяти', 'Исторические деятели',
      'процесс из базы, пять деятелей, двое или трое — участники его событий; лишние — из других веков',
      'процесс, деятели', 'участник хотя бы одного события процесса; ответ — цифры в любом порядке',
      ['современник, но не участник'], 'Б', 2, '2–3 цифры', gen_oge4_persons, ver_oge4_persons),
    P('hist-oge-04-century', 'ОГЭ', 4, 'События века: несколько верных из пяти', 'Хронология',
      'век, пять событий, два или три — этого века; лишние — на два века и дальше', 'век, события', 'век по году начала; ответ — цифры',
      ['событие на границе веков'], 'Б', 2, '2–3 цифры', gen_oge4_century, ver_oge4_century),
    P('hist-oge-05-odd-term', 'ОГЭ', 5, 'Термин, «выпадающий» из ряда по периоду', 'Исторические понятия',
      'пять терминов, четыре — одного раздела кодификатора, один — из раздела на две ступени дальше', 'термины', 'номер лишнего термина',
      ['термин, доживший до следующей эпохи (приказы, стрельцы)'], 'Б', 1, '1 цифра', gen_oge5, ver_oge5, kind='dict'),
    P('hist-oge-06-thesis-fact', 'ОГЭ', 6, 'Тезис ↔ факт (два тезиса, два факта)', 'Аргументация',
      'четыре предложения: два тезиса, два факта', 'предложения', 'четыре цифры: тезис 1, факт 1, тезис 2, факт 2',
      ['факт принимают за тезис'], 'Б', 1, '4 цифры', kind='llm',
      recipe='Тезисы — из своего списка обобщений по процессам базы; факты — события базы того же процесса; ИИ только переформулирует, проверка совпадения с базой кодом.'),
    P('hist-oge-07-stat-table', 'ОГЭ', 7, 'Статистическая таблица: начала — окончания суждений', 'Работа с таблицей',
      'таблица с показателями по годам/регионам, три начала суждений и пять окончаний', 'таблица', 'три цифры',
      ['сравнивают не те столбцы'], 'Б', 2, '3 цифры', kind='llm',
      recipe='Учебные таблицы генерирует код (помечены как учебные данные); суждения о «больше/меньше/росте» считает код; ИИ не нужен, но требуется сюжет — пока рецепт.'),
    P('hist-oge-08-map', 'ОГЭ', 8, 'Историческая карта: правитель / век (слово)', 'Историческая карта', 'схема с легендой', 'схема', 'слово',
      ['правитель по столице'], 'Б', 1, 'слово', kind='bank', recipe='Своя SVG-схема; вопросы из базы событий.', need='карта-схема'),
    P('hist-oge-09-map-object', 'ОГЭ', 9, 'Историческая карта: объект под цифрой', 'Историческая карта', 'та же схема', 'объект', 'слово',
      ['современное название'], 'П', 1, 'слово', kind='bank', recipe='Та же схема; своя таблица названий.', need='карта-схема'),
    P('hist-oge-10-map-text', 'ОГЭ', 10, 'Карта + текст: пропущенное название', 'Историческая карта', 'текст с пропуском по схеме', 'текст', 'слово',
      ['пропуск по тексту, не по карте'], 'П', 1, 'слово', kind='llm', recipe='Как ЕГЭ 11.', need='карта-схема'),
    P('hist-oge-11-image', 'ОГЭ', 11, 'Изображение: монета, медаль, марка, плакат', 'Культура', 'изображение и вопрос с выбором', 'изображение', '1 цифра',
      ['год выпуска ↔ год события'], 'П', 1, '1 цифра', kind='bank', recipe='Только свободные изображения; ключ — из базы событий.', need='изображения'),
    P('hist-oge-12-scheme-year', 'ОГЭ', 12, 'Пропуск в схеме: событие — год', 'Хронология',
      'процесс из базы, три события с годами, один год скрыт', 'процесс, события', 'год по базе; ответ — число',
      ['год соседнего события процесса'], 'Б', 1, 'число', gen_oge12, ver_oge12),
    P('hist-oge-13-culture-two', 'ОГЭ', 13, 'Культура: два памятника по признаку (список + изображения)', 'Культура',
      'перечень из пяти памятников (три названием, два изображением), выбор двух по веку', 'перечень', '2 цифры',
      ['век памятника'], 'Б', 2, '2 цифры', kind='bank',
      recipe='Список — из словаря памятников; изображения — только свободные; без изображений форма не воспроизводится.', need='изображения'),
    P('hist-oge-14-culture-one', 'ОГЭ', 14, 'Культура: один памятник по признаку (век, автор, правление)', 'Культура',
      'четыре памятника из словаря, признак у одного', 'памятники, признак', 'по словарю памятников; ответ — цифра',
      ['век', 'автор соседнего памятника'], 'Б', 1, '1 цифра', gen_oge14, ver_oge14, kind='dict',
      mini='в КИМ памятники частично даны изображениями; здесь все — названиями'),
    P('hist-oge-15-world-person', 'ОГЭ', 15, 'Всеобщая история: участник события', 'Всеобщая история',
      'перечень из четырёх событий всеобщей истории разных веков, деятель одного из них', 'события, деятель', 'по полю persons базы; ответ — цифра',
      ['деятель соседнего века'], 'Б', 1, '1 цифра', gen_oge15, ver_oge15),
    P('hist-oge-16-world-fact', 'ОГЭ', 16, 'Всеобщая история: событие века / раньше / позже', 'Всеобщая история',
      'тот же перечень, вопрос о веке или порядке', 'события, вопрос', 'по году начала; ответ — цифра', ['век на границе'],
      'Б', 1, '1 цифра', gen_oge16, ver_oge16),
    P('hist-oge-17-world-source', 'ОГЭ', 17, 'Всеобщая история: источник → событие', 'Всеобщая история',
      'отрывок из документа, перечень событий', 'источник', '1 цифра', ['страна по имени монарха'], 'Б', 1, '1 цифра', kind='bank',
      recipe='Документы в общественном достоянии; перечень — из базы событий разделов 5, 11, 12.', need='банк источников'),
    P('hist-oge-18-source-attr', 'ОГЭ', 18, 'Источник: атрибуция', 'Работа с источником', 'отрывок', 'источник', 'развёрнутый', ['век по языку'],
      'П', 2, 'развёрнутый', kind='bank', recipe='Как ЕГЭ 13.', need='банк источников'),
    P('hist-oge-19-source-info', 'ОГЭ', 19, 'Источник: поиск информации', 'Работа с источником', 'отрывок, вопрос', 'источник', 'развёрнутый',
      ['ответ не из текста'], 'Б', 2, 'развёрнутый', kind='bank', recipe='Как ЕГЭ 14.', need='банк источников'),
    P('hist-oge-20-source-context', 'ОГЭ', 20, 'Источник: контекст', 'Работа с источником', 'отрывок, вопрос на контекст', 'источник', 'развёрнутый',
      ['контекст соседнего царствования'], 'В', 2, 'развёрнутый', kind='bank', recipe='Тот же банк; ключ — события базы того же процесса.', need='банк источников'),
    P('hist-oge-21-find-errors', 'ОГЭ', 21, 'Найди ошибки в тексте (две ошибки: год и участник)', 'Систематизация фактов',
      'три предложения о событиях одного процесса: событие — год — участник; в двух подменены год и участник событиями других веков',
      'процесс, события, места ошибок', 'предложение ошибочно, если год или участник не совпадают с базой; ответ — номера предложений',
      ['ошибку ищут в названии события, а не в дате'], 'П', 3, '2 цифры', gen_oge21, ver_oge21, n2026=22,
      mini='в КИМ ученик выписывает и исправляет ошибки; здесь — номера ошибочных предложений'),
    P('hist-oge-22-compare', 'ОГЭ', 22, 'Сравнение двух событий/процессов', 'Сравнение', 'два процесса, общее и различное', 'процессы', 'развёрнутый',
      ['различие без указания, у кого какой признак'], 'В', 2, 'развёрнутый', kind='llm', n2026=23, recipe='Как ЕГЭ 21, проще.'),
    P('hist-oge-23-situation', 'ОГЭ', 23, 'Анализ исторической ситуации', 'Причинно-следственные связи', 'ситуация, три вопроса', 'ситуация', 'развёрнутый',
      ['ответы без опоры на ситуацию'], 'В', 3, 'развёрнутый', kind='llm', n2026=24, recipe='Сюжет по событию базы пишет ИИ; ключ — факты базы; вычитка.'),
]
