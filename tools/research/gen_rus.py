#!/usr/bin/env python3
"""Генератор аналогов по прототипам заданий ЕГЭ и ОГЭ по русскому языку.

Словарные прототипы (орфография, орфоэпия, паронимы, формы слов) строятся из
фактов: как пишется слово (data/source/rus-lex.json), где ударение
(data/source/udarenie.json), какие у слова формы (OpenCorpora через pymorphy3,
CC BY-SA 3.0). Каждый факт сверяется со словарём до попадания в карточку.

    python3 tools/research/gen_rus.py --list              # прототипы с генератором
    python3 tools/research/gen_rus.py --show e9-mix -n 3  # примеры карточек
    python3 tools/research/gen_rus.py --check [--fipi bank.json]
    python3 tools/research/gen_rus.py --dump out/         # все карточки в JSON

Зависимости: pip install pymorphy3 pymorphy3-dicts-ru

Карточки — в формате packs/*.json: k='many' (a — список номеров) или
k='word' (новый тип: ввести слово; a — ответ, варианты через «|»).
--fipi — локальный файл с текстами ФИПИ (список строк или объектов с полем
text) для проверки сходства; в репозиторий его класть нельзя.
"""
import argparse
import functools
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEX = json.loads((ROOT / 'data/source/rus-lex.json').read_text())
UDAR = json.loads((ROOT / 'data/source/udarenie.json').read_text())

try:
    import pymorphy3
    MORPH = pymorphy3.MorphAnalyzer()
except ImportError:  # без словаря генератор не работает: проверка обязательна
    sys.exit('нужен pymorphy3: pip install pymorphy3 pymorphy3-dicts-ru')

VOWELS = 'аеёиоуыэюя'
# какие буквы подставляет ученик вместо верной: слово с ними должно быть не словом
ALT = {'а': 'о', 'о': 'а', 'е': 'ия', 'и': 'еы', 'я': 'еа', 'ы': 'и', 'ё': 'о',
       'з': 'с', 'с': 'з', 'ъ': 'ь', 'ь': 'ъ', 'у': 'ю', 'ю': 'у', 'ч': 'щ', 'щ': 'ч',
       'нн': 'н', 'н': 'нн'}
DROPPED = []  # (источник, слово, причина) — что не прошло сверку


PROPER = {'Name', 'Surn', 'Patr', 'Geox', 'Orgn', 'Trad', 'Abbr', 'Init'}


@functools.lru_cache(None)
def known(w):
    """Слово есть в словаре OpenCorpora как нарицательное (имена и названия не в счёт)."""
    w = w.lower().replace('́', '')
    if not MORPH.word_is_known(w):
        return False
    return any(p.is_known and not PROPER & set(p.tag.grammemes) for p in MORPH.parse(w))


def yo(s):
    return s.replace('ё', 'е').replace('Ё', 'Е')


# ---------- слова с пропуском ----------

class Gap:
    """Слово с одним пропуском: 'з[а]ря|подсказка'."""

    def __init__(self, raw, cat):
        self.raw, self.cat = raw, cat
        word, _, self.hint = raw.partition('|')
        m = re.fullmatch(r'([^\[\]]*)\[([^\[\]]+)\]([^\[\]]*)', word)
        if not m:
            raise ValueError('разметка')
        self.pre, self.letter, self.post = m.groups()
        self.full = self.pre + self.letter + self.post

    def show(self):
        s = self.pre + '..' + self.post
        return f'{s} ({self.hint})' if self.hint else s

    def check(self):
        if not known(self.full):
            return 'нет в словаре'
        alts = set(ALT.get(self.letter, ''))
        if self.pre.lower().endswith('пр'):  # пр..бежать: при-, пре- и про- все годятся в слово
            alts |= set('иео')
        for a in sorted(alts):
            if a != self.letter and known(self.pre + a + self.post) and not self.hint:
                return f'с «{a}» тоже слово'
        return ''


def gaps(lst, cat, src):
    out = []
    for raw in lst:
        try:
            g = Gap(raw, cat)
        except ValueError:
            DROPPED.append((src, raw, 'разметка'))
            continue
        why = g.check()
        if why:
            DROPPED.append((src, raw, why))
        else:
            out.append(g)
    return out


PSSV_PRES = {'видеть', 'слышать', 'ненавидеть', 'гнать', 'терпеть', 'любить', 'носить', 'возить',
             'ценить', 'строить', 'колебаться', 'читать', 'решать', 'держать', 'водить'}


def verb_gaps():
    """ЕГЭ 12: личные окончания и суффиксы причастий — формы берём из OpenCorpora."""
    out = []
    forms = [  # (граммемы, где пропуск, подсказка)
        ({'plur', '3per'}, r'(?=т(ся)?$)', '(они)'),
        ({'sing', '2per'}, r'(?=шь(ся)?$)', '(ты)'),
        ({'sing', '3per'}, r'(?=т(ся)?$)', '(он)'),
        ({'PRTF', 'actv', 'pres', 'masc', 'sing', 'nomn'}, r'(?=щий(ся)?$)', ''),
        ({'PRTF', 'pssv', 'pres', 'masc', 'sing', 'nomn'}, r'(?=мый$)', ''),
        ({'PRTF', 'actv', 'past', 'masc', 'sing', 'nomn'}, r'(?=вший(ся)?$)', ''),
        ({'PRTF', 'pssv', 'past', 'masc', 'sing', 'nomn'}, r'(?=нный$)', ''),
    ]
    for conj, verbs in LEX['verbs12'].items():
        for v in verbs:
            p = next((p for p in MORPH.parse(v) if p.tag.POS == 'INFN'), None)
            if not p:
                DROPPED.append(('verbs12', v, 'не глагол'))
                continue
            for gram, rx, hint in forms:
                f = next((x.word for x in p.lexeme if gram <= set(x.tag.grammemes)
                          and 'futr' not in x.tag and 'Infr' not in x.tag), None)
                if not f:
                    continue
                # редкие причастия (будимый, каченный) не берём: страдательные — только частотные
                if 'pssv' in gram and 'pres' in gram and v not in PSSV_PRES:
                    continue
                if 'pssv' in gram and 'past' in gram and 'perf' not in p.tag:
                    continue
                m = re.search(rx, f)
                if not m or m.start() == 0 or f[m.start() - 1] not in VOWELS:
                    continue
                i = m.start() - 1
                if f[i] == 'ё':  # ударная ё — не орфограмма
                    continue
                raw = f'{f[:i]}[{f[i]}]{f[i+1:]}' + (f'|{hint[1:-1]}' if hint else '')
                g = Gap(raw, f'verb{conj}')
                g.lemma, g.conj, g.form = v, conj, tuple(sorted(gram))
                why = g.check()
                if why:
                    DROPPED.append(('verbs12', f, why))
                else:
                    out.append(g)
    return out


def hint_front(g):
    """Подсказку-подлежащее ставим перед глаголом, как на экзамене: (они) стро..т."""
    if g.hint in ('они', 'ты', 'он'):
        return f'({g.hint}) {g.pre}..{g.post}'
    return g.show()


# ---------- пулы ----------

POOLS = {}


def pool(name):
    if name in POOLS:
        return POOLS[name]
    r, p, s = LEX['roots'], LEX['prefixes'], LEX['suffixes']
    if name == 'roots':
        v = gaps(r['chk'], 'chk', 'roots') + gaps(r['unchk'], 'unchk', 'roots') + gaps(r['alt'], 'alt', 'roots')
    elif name == 'prefixes':
        v = sum((gaps(p[k], k, 'prefixes') for k in p), [])
    elif name == 'suffixes':
        v = sum((gaps(s[k], k, 'suffixes') for k in s), [])
    elif name == 'verbs':
        v = verb_gaps()
    else:
        raise KeyError(name)
    POOLS[name] = v
    return v


# ---------- ЕГЭ 9–12: ряды слов ----------

def rows_card(rng, items, n_words, same_ok=lambda row: len({g.letter for g in row}) == 1,
              pick_same=None, disp=Gap.show):
    """5 рядов; верные — где во всех словах одна и та же буква (или своё условие)."""
    by_letter = {}
    for g in items:
        by_letter.setdefault(g.letter, []).append(g)
    letters = [L for L, v in by_letter.items() if len(v) >= n_words]
    n_ok = rng.choice([2, 3, 3, 4])
    kinds = [True] * n_ok + [False] * (5 - n_ok)
    rng.shuffle(kinds)
    used, rows = set(), []
    for ok in kinds:
        for _ in range(200):
            if ok:
                row = pick_same(rng) if pick_same else rng.sample(by_letter[rng.choice(letters)], n_words)
            else:
                row = rng.sample(items, n_words)
            if row is None or any(g.full in used for g in row):
                continue
            if len({g.full for g in row}) < n_words or same_ok(row) != ok:
                continue
            break
        else:
            return None
        used.update(g.full for g in row)
        rows.append(row)
    return rows


def rows_to_card(rows, q, cond, disp=Gap.show):
    o = [{'id': str(i + 1), 't': ', '.join(disp(g) for g in row)} for i, row in enumerate(rows)]
    a = [str(i + 1) for i, row in enumerate(rows) if cond(row)]
    e = '; '.join(f'{i + 1}) ' + ', '.join(g.full for g in row) for i, row in enumerate(rows))
    return {'k': 'many', 'q': q, 'o': o, 'a': a, 'e': e}


Q_SAME = ('Укажите варианты ответов, в которых {all} одного ряда пропущена одна и та же буква. '
          'Запишите номера ответов.')


def g_rows(src, n_words, cats=None):
    def gen(rng):
        items = [g for g in pool(src) if not cats or g.cat in cats]
        rows = rows_card(rng, items, n_words)
        if not rows:
            return None
        same = lambda row: len({g.letter for g in row}) == 1
        q = Q_SAME.format(all='во всех словах' if n_words > 2 else 'в обоих словах')
        disp = hint_front if src == 'verbs' else Gap.show
        return rows_to_card(rows, q, same, disp)
    return gen


def g_rows_cat(cat, title):
    """ЕГЭ 9, старый вид: во всех словах ряда — гласная одного типа (проверяемая и т. п.)."""
    def gen(rng):
        items = pool('roots')
        mine = [g for g in items if g.cat == cat]
        cond = lambda row: all(g.cat == cat for g in row)
        rows = rows_card(rng, items, 3, same_ok=cond, pick_same=lambda r: r.sample(mine, 3))
        if not rows:
            return None
        return rows_to_card(rows, f'Укажите варианты ответов, в которых во всех словах одного ряда пропущена {title}. '
                            'Запишите номера ответов.', cond)
    return gen


# ---------- ЕГЭ 4: ударение ----------

@functools.lru_cache(None)
def stress_words():
    out = []
    for _, words in UDAR['data']:
        for w in words.split():
            caps = [i for i, ch in enumerate(w) if ch.isupper()]
            if len(caps) == 1 and w[caps[0]].lower() in VOWELS:
                out.append((w.lower(), caps[0]))
    return out


def show_stress(w, i):
    return w[:i] + w[i].upper() + w[i + 1:]


def wrong_stress(rng, w, i):
    if 'ё' in w:
        return None  # ё всегда ударная: неверное ударение видно сразу
    other = [j for j, ch in enumerate(w) if ch in VOWELS and j != i]
    return rng.choice(other) if other else None


def g_e4_right(rng):
    ws = rng.sample(stress_words(), 5)
    n_ok = rng.choice([2, 3, 3, 4])
    o, a, e = [], [], []
    for k, (w, i) in enumerate(ws):
        j = i if k < n_ok else wrong_stress(rng, w, i)
        if j is None:
            return None
        o.append(show_stress(w, j))
        e.append(show_stress(w, i))
    order = list(range(5))
    rng.shuffle(order)
    return {'k': 'many', 'q': 'Укажите варианты ответов, в которых верно выделена буква, обозначающая '
            'ударный гласный звук. Запишите номера ответов.',
            'o': [{'id': str(n + 1), 't': o[k]} for n, k in enumerate(order)],
            'a': [str(n + 1) for n, k in enumerate(order) if k < n_ok],
            'e': 'Верно: ' + ', '.join(e[k] for k in order)}


def g_e4_word(rng):
    ws = rng.sample(stress_words(), 5)
    w, i = ws[0]
    j = wrong_stress(rng, w, i)
    if j is None:
        return None
    shown = [show_stress(w, j)] + [show_stress(x, k) for x, k in ws[1:]]
    rng.shuffle(shown)
    return {'k': 'word', 'q': 'В одном из приведённых ниже слов допущена ошибка в постановке ударения: НЕВЕРНО '
            'выделена буква, обозначающая ударный гласный звук. Выпишите это слово.',
            't': ', '.join(shown), 'a': w, 'e': 'Правильно: ' + show_stress(w, i)}


# ---------- ЕГЭ 5: паронимы ----------

def inflect_like(form, lemma_from, lemma_to):
    """Поставить lemma_to в ту же форму, в которой стоит form (слово от lemma_from)."""
    ps = [p for p in MORPH.parse(form.lower()) if yo(p.normal_form) == yo(lemma_from)]
    if not ps:
        return None
    src = ps[0]
    tos = [p for p in MORPH.parse(lemma_to) if yo(p.normal_form) == yo(lemma_to) and p.tag.POS == (
        'ADJF' if src.tag.POS in ('ADJF', 'ADJS', 'COMP') else src.tag.POS)]
    if not tos:
        return None
    keep = {g for g in src.tag.grammemes if g in {
        'nomn', 'gent', 'datv', 'accs', 'ablt', 'loct', 'sing', 'plur', 'masc', 'femn', 'neut',
        'ADJS', 'COMP', 'past', 'pres', 'futr', 'impr', '1per', '2per', '3per', 'INFN', 'anim', 'inan'}}
    try:
        r = tos[0].inflect(keep)
    except ValueError:
        r = None
    return r.word if r else None


@functools.lru_cache(None)
def paronym_ctx():
    out = []  # (группа, лемма, предложение, выделенное слово)
    for gi, grp in enumerate(LEX['paronyms']):
        for lem, sents in grp['ctx'].items():
            for s in sents:
                m = re.search(r'[А-ЯЁ]{3,}', s)
                if not m:
                    DROPPED.append(('paronyms', s, 'нет выделенного слова'))
                    continue
                w = m.group(0).lower()
                if not known(w) or not any(yo(p.normal_form) == yo(lem) for p in MORPH.parse(w)):
                    DROPPED.append(('paronyms', w, f'не форма слова {lem}'))
                    continue
                out.append((gi, lem, s, w))
    return out


def g_e5(rng):
    ctx = paronym_ctx()
    groups = list({c[0] for c in ctx})
    gs = rng.sample(groups, 5)
    picks = [rng.choice([c for c in ctx if c[0] == g]) for g in gs]
    gi, lem, s, w = picks[0]
    others = [x for x in LEX['paronyms'][gi]['w'] if x != lem]
    rng.shuffle(others)
    for other in others:
        bad = inflect_like(w, lem, other)
        if bad and known(bad) and yo(bad) != yo(w):
            break
    else:
        return None
    lines = [s.replace(w.upper(), bad.upper(), 1)] + [p[2] for p in picks[1:]]
    rng.shuffle(lines)
    return {'k': 'word', 'q': 'В одном из приведённых ниже предложений НЕВЕРНО употреблено выделенное слово. '
            'Исправьте лексическую ошибку, подобрав к выделенному слову пароним. Запишите подобранное '
            'слово, соблюдая нормы современного русского литературного языка.', 't': '\n'.join(lines),
            'a': w, 'e': f'{bad.upper()} → {w}: {s}'}


# ---------- ЕГЭ 7, ОГЭ 8: формы слов ----------

GENERIC = {  # свои рамки для ОГЭ 8: подходят к любому слову нужной формы
    'plur,gent': ['несколько ({})', 'много ({})', 'не хватает ({})', 'без ({})', 'около десяти ({})'],
    'plur,nomn': ['({}) уже на месте', 'новые ({})', 'все ({}) готовы', 'эти ({})'],
    'COMP': ['Стало ({}), чем раньше.', 'С каждым днём всё ({}).', 'Теперь здесь ещё ({}).'],
    'impr,sing': ['({}), пожалуйста!', 'Сейчас же ({})!', 'Ну-ка, ({}).'],
    'past,masc': ['Вчера он совсем ({}).', 'К вечеру он ({}).'],
}


@functools.lru_cache(None)
def form_items():
    out = []
    for it in LEX['o8']['forms']:
        lem = it.get('lemma2') or it['lemma']
        ok = it['ok']
        g = set(it['g'].split(','))
        if 'impr' in g:
            g |= {'excl'}
        want = None
        for p in MORPH.parse(lem):
            if yo(p.normal_form) != yo(lem):
                continue
            try:
                r = p.inflect(g)
            except ValueError:
                r = None
            if r:
                want = r.word
                if yo(want) == yo(ok):
                    break
        if not known(ok) or (want and yo(want) != yo(ok) and not it.get('free')):
            DROPPED.append(('forms', ok, f'словарь даёт «{want}»'))
            continue
        if yo(it['bad']) == yo(ok):
            DROPPED.append(('forms', ok, 'ошибка совпадает с нормой'))
            continue
        out.append(it)
    return out


def g_e7(rng):
    items = form_items()
    pick = []
    cats = {}
    for it in rng.sample(items, len(items)):
        if cats.get(it['cat'], 0) < 2:
            cats[it['cat']] = cats.get(it['cat'], 0) + 1
            pick.append(it)
        if len(pick) == 5:
            break
    lines = []
    for k, it in enumerate(pick):
        w = it['bad'] if k == 0 else it['ok']
        lines.append(rng.choice(it['ctx']).replace('({})', w.upper()))
    bad = lines[0]
    rng.shuffle(lines)
    return {'k': 'word', 'q': 'В одном из выделенных ниже слов допущена грамматическая ошибка. Исправьте ошибку и '
            'запишите слово правильно.', 't': '\n'.join(lines), 'a': pick[0]['ok'],
            'e': f'{bad} → {pick[0]["ok"]}'}


def nom_form(it):
    lem = it['lemma']
    if it['g'].startswith('plur'):
        p = next((p for p in MORPH.parse(lem) if p.tag.POS == 'NOUN'), None)
        r = p.inflect({'plur', 'nomn'}) if p else None
        return r.word if r else lem
    return lem


def g_o8_forms(cats):
    def gen(rng):
        items = [it for it in form_items() if it['cat'] in cats]
        it = rng.choice(items)
        frames = list(it['ctx']) + GENERIC.get(it['g'], [])
        fr = rng.choice(frames)
        lemma = nom_form(it)
        return {'k': 'word', 'q': f'Раскройте скобки и запишите слово «{lemma}» в соответствующей форме, соблюдая '
                'нормы современного русского литературного языка.', 't': fr.replace('{}', lemma), 'a': it['ok'],
                'e': fr.replace('({})', it['ok'])}
    return gen


NUM_FRAMES = [  # (падеж, рамка, существительные) — свои предложения
    ('gent', 'Длина маршрута составила около ({}) {n}.', ['километр', 'метр']),
    ('gent', 'В библиотеке не хватает ({}) {n}.', ['книга', 'учебник', 'стул']),
    ('gent', 'На конференцию приехали больше ({}) {n}.', ['участник', 'гость', 'учёный']),
    ('gent', 'Выставка собрала свыше ({}) {n}.', ['экспонат', 'картина', 'рисунок']),
    ('datv', 'Благодарности вручили ({}) {n}.', ['участник', 'волонтёр', 'учитель']),
    ('datv', 'Грамоты разослали ({}) {n}.', ['школа', 'библиотека', 'клуб']),
    ('ablt', 'Музей располагает более чем ({}) {n}.', ['экспонат', 'картина', 'рукопись']),
    ('ablt', 'Бригада справилась с ({}) {n} за неделю.', ['заказ', 'задание', 'заявка']),
    ('loct', 'В отчёте говорится о ({}) {n}.', ['участник', 'школа', 'проект']),
    ('loct', 'Журналист написал о ({}) {n}.', ['доброволец', 'семья', 'спортсмен']),
]


def num_case(num, case, noun):
    p = next((p for p in MORPH.parse(num) if p.tag.POS == 'NUMR'), None)
    if not p:
        return None, None
    g = MORPH.parse(noun)[0]
    gender = g.tag.gender
    if num in ('оба', 'обе', 'полтора'):
        want = {'femn'} if gender == 'femn' else {'masc'}
        if (num == 'обе') != (gender == 'femn'):
            return None, None
    else:
        want = set()
    r = p.inflect({case} | want) if p.inflect({case} | want) else p.inflect({case})
    nf = g.inflect({'plur', case})
    return (r.word if r else None), (nf.word if nf else None)


def g_o8_num(rng):
    num = rng.choice(LEX['o8']['nums'])
    case, fr, nouns = rng.choice(NUM_FRAMES)
    noun = rng.choice(nouns)
    w, nf = num_case(num, case, noun)
    if not w or not nf or not known(w) or yo(w) == yo(num) and case != 'nomn':
        return None
    return {'k': 'word', 'q': f'Раскройте скобки и запишите слово «{num}» в соответствующей форме, соблюдая '
            'нормы современного русского литературного языка.',
            't': fr.format('{}', n=nf).replace('{}', num), 'a': w,
            'e': fr.format('{}', n=nf).replace('({})', w)}


def g_o9(kind, label):
    def gen(rng):
        src, dst = rng.choice(LEX['o9'][kind])
        if not all(known(x) for x in re.findall(r'[а-яё-]+', dst)):
            return None
        a, b = label.split(' → ')
        return {'k': 'word', 'q': f'Замените словосочетание «{src}», построенное на основе {a}, '
                f'синонимичным словосочетанием со связью {b}. Напишите получившееся словосочетание.',
                'a': dst, 'e': f'{src} → {dst}'}
    return gen


# ---------- ЕГЭ 15: Н и НН ----------

NN_FRAMES = ['В описи старой усадьбы значатся: {}.', 'Среди находок экспедиции — {}.',
             'На выставке показали: {}.', 'В витрине музея: {}.']


@functools.lru_cache(None)
def nn_items():
    out = []
    for raw, noun in LEX['nn']:
        try:
            g = Gap(raw, 'nn')
        except ValueError:
            DROPPED.append(('nn', raw, 'разметка'))
            continue
        why = g.check()
        if why:
            DROPPED.append(('nn', raw, why))
            continue
        np = next((p for p in MORPH.parse(noun) if p.tag.POS == 'NOUN' and 'nomn' in p.tag), None)
        ap = next((p for p in MORPH.parse(g.full) if p.tag.POS in ('ADJF', 'PRTF')), None)
        if not np or not ap:
            DROPPED.append(('nn', raw, 'нет разбора'))
            continue
        gend = np.tag.gender or 'masc'
        r = ap.inflect({gend, 'sing', 'nomn'})
        if not r or not r.word.startswith(g.pre + g.letter):
            DROPPED.append(('nn', raw, 'не согласуется'))
            continue
        tail = r.word[len(g.pre) + len(g.letter):]
        if known(g.pre + ALT[g.letter] + tail):
            DROPPED.append(('nn', raw, 'в нужной форме оба написания — слова'))
            continue
        g.phrase = (g.pre, tail, noun)
        out.append(g)
    return out


def g_e15(target):
    def gen(rng):
        items = nn_items()
        k = rng.choice([4, 5, 5, 6])
        pick = rng.sample(items, k)
        a = [str(i + 1) for i, g in enumerate(pick) if g.letter == target]
        if not 1 <= len(a) < k:
            return None
        parts = [f'{g.phrase[0]}({i + 1}){g.phrase[1]} {g.phrase[2]}' for i, g in enumerate(pick)]
        q = 'Укажите цифру(-ы), на месте которой(-ых) пишется ' + ('НН.' if target == 'нн' else 'одна буква Н.')
        return {'k': 'many', 'q': q, 't': rng.choice(NN_FRAMES).format(', '.join(parts)),
                'o': [{'id': str(i + 1), 't': str(i + 1)} for i in range(k)], 'a': a,
                'e': ', '.join(g.pre + g.letter + g.phrase[1] for g in pick)}
    return gen


# ---------- ОГЭ 6: объяснение написания ----------

VOICELESS = 'кпстфхцчшщ'
ALT_ROOTS = [  # (регулярка на корень, правило, буква по правилу)
    (r'ла[г]|ло[ж]', 'зависит от последующей согласной: перед Г пишется А, перед Ж — О'),
    (r'ра[сщ]|ро[с]', 'зависит от последующей согласной: перед СТ и Щ пишется А, перед С — О'),
    (r'(б|д|м|п|т|бл|ж|ст|ч)[еи](р|ст|г|л|т|ч|с)', 'зависит от суффикса: перед суффиксом -А- пишется И'),
    (r'к[ао]с', 'зависит от суффикса: перед суффиксом -А- пишется А'),
    (r'(жи|чи|ни|ми)ма|чина', 'перед суффиксом -А- в корне пишется -ИМ-/-ИН-'),
    (r'г[ао]р', 'безударной пишется О'),
    (r'з[ао]р', 'безударной пишется А'),
    (r'кл[ао]н', 'безударной пишется О'),
    (r'тв[ао]р', 'безударной пишется О'),
    (r'пл[ао]в', 'пишется А (исключения: пловец, пловчиха)'),
    (r'р[ао]вн', 'зависит от значения: «равный, наравне» — А, «ровный, прямой» — О'),
]


@functools.lru_cache(None)
def o6_facts():
    """Верные и неверные объяснения для слов из словаря (свои формулировки)."""
    facts = []  # (слово, верное, неверное)
    for g in pool('prefixes'):
        W = g.full.upper()
        if g.cat == 'zs':
            nxt = g.post[:1]
            kind = 'глухой' if nxt in VOICELESS else 'звонкий'
            other = 'звонкий' if kind == 'глухой' else 'глухой'
            L = g.letter.upper()
            facts.append((W, f'на конце приставки перед буквой, обозначающей {kind} согласный, пишется {L}',
                          f'на конце приставки перед буквой, обозначающей {other} согласный, пишется {L}'))
        elif g.cat == 'yi' and g.letter == 'ы' and g.pre[-1:] not in VOWELS:
            facts.append((W, 'после русской приставки на согласный вместо И пишется Ы',
                          'после русской приставки на согласный сохраняется И'))
        elif g.cat == 'yi' and g.letter == 'и' and re.match(r'(меж|сверх|дез|контр|пост|суб|пан|транс|пед|спорт)', g.pre):
            facts.append((W, 'после приставок МЕЖ-, СВЕРХ-, иноязычных приставок и в сложносокращённых словах сохраняется И',
                          'после приставки на согласный вместо И пишется Ы'))
        elif g.cat == 'hard' and g.letter == 'ъ':
            facts.append((W, 'разделительный Ъ пишется после приставки или первой части слова на согласный перед Е, Ё, Ю, Я',
                          'разделительный Ь пишется после приставки на согласный перед Е, Ё, Ю, Я'))
        elif g.cat == 'hard' and g.letter == 'ь':
            facts.append((W, 'разделительный Ь пишется внутри корня или перед окончанием перед Е, Ё, Ю, Я, И',
                          'разделительный Ъ пишется после приставки перед Е, Ё, Ю, Я'))
    for g in pool('roots'):
        if g.cat != 'alt':
            continue
        for rx, rule in ALT_ROOTS:
            if re.search(rx, g.pre[-3:] + g.letter + g.post[:3]):
                facts.append((g.full.upper(), 'написание безударной чередующейся гласной в корне ' + rule,
                              'безударная гласная в корне проверяется ударением'))
                break
    for g in pool('verbs'):
        if g.form == ('3per', 'plur'):
            ex = g.lemma in ('гнать', 'держать', 'дышать', 'слышать', 'видеть', 'обидеть', 'терпеть',
                             'вертеть', 'зависеть', 'ненавидеть', 'смотреть')
            c, wrong = ('II', 'I') if g.conj == 'II' else ('I', 'II')
            note = ' (глагол-исключение)' if ex else ''
            facts.append((f'(ОНИ) {g.full.upper()}', f'в окончании глагола {c} спряжения{note} пишется {g.letter.upper()}',
                          f'в окончании глагола {wrong} спряжения пишется {g.letter.upper()}'))
    for g in nn_items():
        W = (g.pre + g.letter + g.phrase[1]).upper()
        if g.letter == 'н' and re.search(r'(ян|ан|ин)$', g.pre + g.letter) and g.pre[-2:] in ('ин', 'ян', 'ан', 'ьи') or \
                g.letter == 'н' and g.pre[-1:] in 'яаи':
            facts.append((W, 'в суффиксе прилагательного -АН-/-ЯН-/-ИН- пишется одна Н',
                          'в суффиксе прилагательного -ЕНН-/-ОНН- пишется НН'))
        elif g.letter == 'нн' and g.pre.endswith(('ио', 'уе', 'ве', 'це')):
            facts.append((W, 'в прилагательном с суффиксом -ОНН- или -ЕНН- пишется НН',
                          'в прилагательном с суффиксом -АН-/-ЯН- пишется одна Н'))
        elif g.full in ('деревянный', 'стеклянный', 'оловянный'):
            facts.append((W, 'слово-исключение: пишется НН, хотя суффикс -ЯН-',
                          'в суффиксе -ЯН- пишется одна Н без исключений'))
    return facts


def g_o6(rng):
    facts = o6_facts()
    pick = []
    seen = set()
    for f in rng.sample(facts, len(facts)):
        rule = f[1].split(' (')[0][:40]
        if f[0] in seen or sum(1 for p in pick if p[1][:40] == rule) >= 2:
            continue
        seen.add(f[0])
        pick.append(f)
        if len(pick) == 5:
            break
    n_ok = rng.choice([2, 3, 3, 4])
    o, a = [], []
    for i, (w, ok, bad) in enumerate(pick):
        right = i < n_ok
        o.append((w + ' — ' + (ok if right else bad), right))
    rng.shuffle(o)
    return {'k': 'many', 'q': 'Укажите варианты ответов, в которых дано верное объяснение написания выделенного '
            'слова. Запишите номера ответов.',
            'o': [{'id': str(i + 1), 't': t} for i, (t, _) in enumerate(o)],
            'a': [str(i + 1) for i, (_, r) in enumerate(o) if r],
            'e': 'Неверные объяснения подменяют правило.'}


# ---------- ОГЭ 7: маска для текста, написанного ИИ ----------

def o7_mask(text, letter=None, rng=None):
    """Найти в тексте слова из словаря и закрыть пропуски (1)..(9). Для рецепта llm-o7."""
    rng = rng or random.Random(0)
    bank = {g.full: g for g in pool('roots') + pool('prefixes') + pool('suffixes') + pool('verbs')}
    words = re.findall(r'[а-яё]+', text.lower())
    hits = [bank[w] for w in dict.fromkeys(words) if w in bank]
    if len(hits) < 6:
        return None
    hits = hits[:9]
    out, a = text, []
    for i, g in enumerate(hits, 1):
        out = re.sub(r'(?i)\b' + g.full + r'\b', g.pre + f'..({i})' + g.post, out, count=1)
        if letter and g.letter == letter:
            a.append(str(i))
    return {'k': 'many', 't': out, 'a': a}


# ---------- реестр ----------

GEN = {
    'e4-right': g_e4_right,
    'e4-word': g_e4_word,
    'e5-paronym': g_e5,
    'e7-form': g_e7,
    'e9-mix': g_rows('roots', 3),
    'e9-chk': g_rows_cat('chk', 'безударная проверяемая гласная корня'),
    'e9-unchk': g_rows_cat('unchk', 'безударная непроверяемая гласная корня'),
    'e9-alt': g_rows_cat('alt', 'чередующаяся гласная корня'),
    'e10-mix': g_rows('prefixes', 3),
    'e10-prepri': g_rows('prefixes', 3, {'prepri', 'fixed'}),
    'e10-zs': g_rows('prefixes', 3, {'zs', 'fixed'}),
    'e10-sign': g_rows('prefixes', 3, {'hard', 'yi'}),
    'e11-mix': g_rows('suffixes', 2),
    'e11-noun': g_rows('suffixes', 2, {'noun'}),
    'e11-adjverb': g_rows('suffixes', 2, {'adj', 'verb'}),
    'e12-mix': g_rows('verbs', 2),
    'e15-nn': g_e15('нн'),
    'e15-n': g_e15('н'),
    'o6-expl': g_o6,
    'o8-num': g_o8_num,
    'o8-noun': g_o8_forms({'noun'}),
    'o8-other': g_o8_forms({'adj', 'verb', 'pron'}),
    'o9-upr2sogl': g_o9('upr2sogl', 'управления → согласование'),
    'o9-sogl2upr': g_o9('sogl2upr', 'согласования → управление'),
    'o9-prim2upr': g_o9('prim2upr', 'примыкания → управление'),
    'o9-upr2prim': g_o9('upr2prim', 'управления → примыкание'),
}
# прототипы, у которых вариантов по построению меньше 200 (одна пара — одна карточка)
SMALL = {'o9-upr2sogl', 'o9-sogl2upr', 'o9-prim2upr', 'o9-upr2prim'}


def key(card):
    """Ключ для поиска дублей: те же пункты в другом порядке — дубль."""
    parts = sorted(o['t'] for o in card.get('o', [])) if card['k'] == 'many' and 't' not in card \
        else [card.get('t', ''), card['a'] if isinstance(card['a'], str) else '']
    if card['k'] == 'word' and card.get('t'):
        parts = sorted(card['t'].split('\n')) + [card['a']]
    return yo(card.get('q', '') + '|' + '|'.join(parts)).lower()


def generate(pid, n, seed=1):
    rng = random.Random(f'{pid}:{seed}')
    out, seen = [], set()
    tries = 0
    while len(out) < n and tries < n * 30:
        tries += 1
        c = GEN[pid](rng)
        if not c:
            continue
        k = key(c)
        if k in seen:
            continue
        seen.add(k)
        c = {'id': f'{pid}-{len(out) + 1:03d}', 'p': pid, **c}
        out.append(c)
    return out


# ---------- проверка карточек, написанных ИИ (рецепты llm) ----------

def check_llm(c):
    """Проверки правилом для аналогов по рецептам llm. Пустая строка — всё в порядке."""
    pid, k, t, a = c.get('proto', ''), c.get('k'), c.get('t', ''), c.get('a')
    if k not in ('many', 'word', 'match') or not c.get('q'):
        return 'нет формата или формулировки'
    if k == 'many':
        ids = [o['id'] for o in c.get('o', [])]
        pos = re.findall(r'\((\d+)\)', t) if not ids else []
        dom = set(ids or pos)
        if not isinstance(a, list) or not a or not set(a) <= dom:
            return f'ответ {a} вне вариантов {sorted(dom)}'
        if len(a) == len(dom) and not pid.startswith(('e26', 'e21')):
            return 'верны все варианты'
        if pos and [int(x) for x in pos] != sorted(int(x) for x in pos):
            return 'позиции идут не по порядку'
    if k == 'match' and not re.fullmatch(r'\d{3,5}', str(a)):
        return 'ответ соответствия — не 3–5 цифр'
    if k == 'word':
        words = [w for w in str(a).split('|') if w]
        if not words:
            return 'пустой ответ'
        if pid.startswith(('e25', 'o12-meaning', 'o12-syn', 'e6-excess')):
            low = yo(t.lower())
            if not any(yo(w.lower()) in low for w in words):
                return 'выписываемого слова нет в тексте'
        if pid == 'e6-excess' and sum(yo(t.lower()).count(yo(w.lower())) for w in words[:1]) != 1:
            return 'лишнее слово встречается не один раз'
    if pid == 'o7-letters':
        m = re.search(r'буква ([А-ЯЁ])', c['q'])
        bank = {g.full: g for g in pool('roots') + pool('prefixes') + pool('suffixes')}
        got = []
        for w_pre, i, w_post in re.findall(r'([а-яё]*)\.\.\((\d)\)([а-яё]*)', t.lower()):
            fills = [L for L in 'аоеиыяюуёзсъь' if known(w_pre + L + w_post)]
            if len(fills) != 1:
                return f'пропуск ({i}) неоднозначен или не слово: {w_pre}..{w_post} → {fills}'
            if m and fills[0] == m.group(1).lower():
                got.append(i)
        if m and sorted(got) != sorted(a):
            return f'по словарю ответ {got}, в карточке {a}'
    return ''


# ---------- самопроверка ----------

def verify(card):
    """Пересчитать ответ независимо от генератора. Пустая строка — всё в порядке."""
    pid, k = card['p'], card['k']
    if k == 'many':
        ids = {o['id'] for o in card['o']}
        if not card['a'] or not set(card['a']) <= ids or len(card['a']) == len(ids):
            return 'ответ пуст, вне вариантов или все варианты верны'
    if pid.startswith(('e9', 'e10', 'e11', 'e12')):
        allg = {g.show(): g for g in pool('roots') + pool('prefixes') + pool('suffixes') + pool('verbs')}
        allg.update({hint_front(g): g for g in pool('verbs')})
        for o in card['o']:
            row = [allg.get(x.strip()) for x in re.split(r', (?![^()]*\))', o['t'])]
            if None in row:
                return 'слово ряда не найдено в словаре: ' + o['t']
            if pid in ('e9-chk', 'e9-unchk', 'e9-alt'):
                cat = pid.split('-')[1]
                ok = all(g.cat == cat for g in row)
            else:
                ok = len({g.letter for g in row}) == 1
            if ok != (o['id'] in card['a']):
                return 'ответ не сходится в ряду ' + o['id']
            for g in row:
                if not known(g.full):
                    return 'нет в словаре: ' + g.full
    elif pid == 'e4-right':
        good = {show_stress(w, i) for w, i in stress_words()}
        for o in card['o']:
            if (o['t'] in good) != (o['id'] in card['a']):
                return 'ударение не сходится: ' + o['t']
    elif pid == 'e4-word':
        good = {show_stress(w, i) for w, i in stress_words()}
        bad = [x for x in card['t'].split(', ') if x not in good]
        if len(bad) != 1 or bad[0].lower() != card['a']:
            return 'неверное ударение не одно'
    elif pid == 'e5-paronym':
        if not known(card['a']):
            return 'ответа нет в словаре'
        lines = card['t'].split('\n')
        good = {c[2] for c in paronym_ctx()}
        if sum(1 for x in lines if x not in good) != 1:
            return 'ошибка не в одном предложении'
    elif pid == 'e15-nn' or pid == 'e15-n':
        t = card['t']
        for m in re.finditer(r'([а-яё]+)\((\d)\)([а-яё]+)', t):
            pre, i, post = m.groups()
            one, two = known(pre + 'н' + post), known(pre + 'нн' + post)
            if one == two:
                return 'Н/НН неоднозначно: ' + pre + '_' + post
            right = 'нн' if two else 'н'
            if (right == ('нн' if pid == 'e15-nn' else 'н')) != (i in card['a']):
                return 'ответ не сходится в позиции ' + i
    elif k == 'word':
        for w in re.findall(r'[а-яё]+', card['a'].lower()):
            if not known(w):
                return 'ответа нет в словаре: ' + w
    return ''


def shingles(text, n=5):
    toks = re.findall(r'[а-яё0-9]+', yo(text.lower()))
    return {' '.join(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def card_text(c, with_q=False):
    parts = ([c.get('q', '')] if with_q else []) + [c.get('t', '')] + [o['t'] for o in c.get('o', [])]
    return ' '.join(parts)


def load_fipi(path):
    data = json.loads(Path(path).read_text())
    texts = [x['text'] if isinstance(x, dict) else x for x in data]
    sh = set()
    for t in texts:
        sh |= shingles(t)
    return sh


def check(n, fipi):
    fsh = load_fipi(fipi) if fipi else None
    ok_all = True
    print(f'{"прототип":14} {"карт.":>5} {"ошибок":>6} {"дублей":>6} {"сходство":>9}  итог')
    for pid in GEN:
        cards = generate(pid, n)
        errs = [(c['id'], e) for c in cards if (e := verify(c))]
        dups = len(cards) - len({key(c) for c in cards})
        sim = 0.0
        if fsh:
            for c in cards:
                s = shingles(card_text(c))
                if s:
                    sim = max(sim, len(s & fsh) / len(s))
        need = 1 if pid in SMALL else n
        good = not errs and not dups and len(cards) >= need and sim < 0.3
        ok_all &= good
        simt = f'{sim:.0%}' if fsh else '—'
        print(f'{pid:14} {len(cards):5} {len(errs):6} {dups:6} {simt:>9}  {"ок" if good else "НЕТ"}')
        for e in errs[:3]:
            print('    ', *e)
    print(f'\nОтсеяно при сверке со словарём: {len(DROPPED)}')
    for src, w, why in DROPPED:
        print(f'  {src}: {w} — {why}')
    return ok_all


def render(c):
    lines = [c.get('q', '')]
    if c.get('t'):
        lines.append(c['t'])
    lines += [f'{o["id"]}) {o["t"]}' for o in c.get('o', [])] if 't' not in c or c['k'] != 'many' or 'e15' not in c['p'] else []
    lines.append('Ответ: ' + (''.join(c['a']) if isinstance(c['a'], list) else c['a']))
    return '\n'.join(x for x in lines if x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--show')
    ap.add_argument('-n', type=int, default=3)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--fipi')
    ap.add_argument('--dump')
    ap.add_argument('--check-llm', help='JSON с аналогами по рецептам llm')
    ap.add_argument('--capacity', action='store_true', help='сколько разных карточек даёт прототип (до 2000)')
    args = ap.parse_args()
    if args.list:
        for pid in GEN:
            print(pid)
    elif args.show:
        for c in generate(args.show, args.n):
            print(render(c), end='\n\n')
    elif args.capacity:
        for pid in GEN:
            print(pid, len(generate(pid, 2000)))
    elif args.dump:
        d = Path(args.dump)
        d.mkdir(parents=True, exist_ok=True)
        for pid in GEN:
            (d / f'{pid}.json').write_text(json.dumps(generate(pid, args.n), ensure_ascii=False, indent=1))
    elif args.check_llm:
        cards = json.loads(Path(args.check_llm).read_text())
        fsh = load_fipi(args.fipi) if args.fipi else None
        bad = 0
        for i, c in enumerate(cards):
            e = check_llm(c)
            sim = 0.0
            if fsh:
                sh = shingles(card_text(c))
                sim = len(sh & fsh) / len(sh) if sh else 0
                if sim >= 0.3:
                    e = (e + '; ' if e else '') + f'сходство с ФИПИ {sim:.0%}'
            if e:
                bad += 1
                print(i, c.get('proto'), e)
        print(f'{len(cards) - bad}/{len(cards)} прошли проверку правилом')
    elif args.check:
        sys.exit(0 if check(max(args.n, 200), args.fipi) else 1)
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
