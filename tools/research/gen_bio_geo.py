#!/usr/bin/env python3
"""Прототип генераторов карточек по биологии и географии (ЕГЭ/ОГЭ, 5–9 класс).

Исследовательский прототип: в сборку наборов (tools/build_packs.py) не подключён.

Запуск:
  python3 tools/research/gen_bio_geo.py            # самопроверка: 200 вариантов на тип
  python3 tools/research/gen_bio_geo.py --n 500    # другое число вариантов
  python3 tools/research/gen_bio_geo.py --sample b_mono 3   # показать примеры карточек
  python3 tools/research/gen_bio_geo.py --dump out.json     # выгрузить все карточки

Каждый генератор — функция gen_<тип>(rng) → карточка в формате наборов
(см. начало tools/build_packs.py): {id, t, k, q, o?, a, e, p?, src}.
  k = 'num' — краткий ответ: число или последовательность цифр (sameNumber в lib.js);
  k = 'one' — один верный вариант, неверные варианты — типичные ошибки.
Поле `chk` — параметры задачи для независимой проверки (при сборке его убрать).

Самопроверка для каждого типа:
  1) ответ пересчитывается другим способом (перебор решётки Пеннета, datetime,
     прямое моделирование) функцией check_<тип>(chk) и сверяется с `a`;
  2) структура карточки корректна (варианты различны, `a` среди них, число парсится);
  3) нет дубликатов текста вопроса; отдельно считается число различных задач по сути
     (без учёта имён организмов/городов) — чтобы честно видеть, где разнообразие косметическое.
"""
import argparse
import datetime as dt
import itertools
import json
import random
import re
import sys
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP, getcontext
from fractions import Fraction
from math import gcd
from functools import reduce
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ru_morph import agree, inflect, ob, plural_of, predicate, short_adj, which  # noqa: E402

# ---------------------------------------------------------------- общее

getcontext().prec = 40


def fmt(x, nd=None):
    """Число в формате бланка ЕГЭ: запятая, без лишних нулей.

    Округление — как в школе (половина вверх), по точному значению: передавайте Fraction.
    """
    if not isinstance(x, Fraction):
        x = Fraction(str(x))
    if nd is not None:
        d = Decimal(x.numerator) / Decimal(x.denominator)
        d = d.quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)
    else:
        d = Decimal(x.numerator) / Decimal(x.denominator)
    s = format(d.normalize(), 'f')
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s.replace('.', ',')


def one(rng, correct, wrong, n=4):
    """Карточка 'one': правильный вариант + различные неверные, перемешанные."""
    seen, opts = {correct}, [correct]
    for w in wrong:
        if w not in seen:
            seen.add(w)
            opts.append(w)
        if len(opts) == n:
            break
    rng.shuffle(opts)
    ids = '123456'                          # в КИМ варианты нумеруются цифрами
    o = [{'id': ids[i], 't': t} for i, t in enumerate(opts)]
    return o, ids[opts.index(correct)]


def card(kind, topic, q, a, e, chk, o=None, core=None):
    minus = lambda t: re.sub(r'(?<!\.)\.\.(?!\.)', '.', re.sub(r'(?<![\w\-−])-(?=\d)', '−', t))   # минус; «з.д..» → «з.д.»
    c = {'k': kind, 't': topic, 'q': minus(q), 'a': a, 'e': minus(e), 'src': 'gen:' + kind, 'chk': chk}
    if o is not None:
        c['o'] = o
    c['core'] = json.dumps(core if core is not None else chk, ensure_ascii=False, sort_keys=True)
    return c


def sp(n):
    """Целое с пробелами между разрядами: 2 500 000."""
    return f'{n:,}'.replace(',', '\u00a0')


def half_up(x, nd):
    """Округление половины вверх целочисленно (для проверок, независимо от Decimal в fmt)."""
    k = Fraction(10) ** nd
    y = x * k
    sign = -1 if y < 0 else 1
    y = abs(y)
    r = (y.numerator * 2 + y.denominator) // (2 * y.denominator)
    return Fraction(sign * r) / k


def ratio(counts):
    """Счётчик классов → соотношение по убыванию, сокращённое."""
    vals = sorted(counts, reverse=True)
    g = reduce(gcd, vals)
    return [v // g for v in vals]


# ================================================================ БИОЛОГИЯ

# 2n — общеизвестные справочные значения (школьные учебники, ЕГЭ)
KARYO = {
    'человека': 46, 'шимпанзе': 48, 'собаки': 78, 'кошки': 38, 'лошади': 64,
    'крупного рогатого скота': 60, 'свиньи': 38, 'курицы': 78, 'дрозофилы': 8,
    'гороха': 14, 'мягкой пшеницы': 42, 'кукурузы': 20, 'картофеля': 48,
    'ржи': 14, 'томата': 24, 'риса': 24, 'кролика': 44, 'домовой мыши': 40,
    'лука': 16, 'овса': 42, 'ячменя': 14, 'яблони': 34, 'карпа': 104, 'осла': 62,
}

# фаза → (множитель n, множитель c) для одной клетки
PHASES = {
    'в клетке в пресинтетическом периоде (G1) интерфазы': (2, 2),
    'в клетке после синтетического периода (S) интерфазы': (2, 4),
    'в профазе митоза': (2, 4), 'в метафазе митоза': (2, 4),
    'в анафазе митоза': (4, 4), 'в каждой дочерней клетке после митоза': (2, 2),
    'в профазе мейоза I': (2, 4), 'в метафазе мейоза I': (2, 4),
    'в анафазе мейоза I': (2, 4), 'в каждой клетке после телофазы мейоза I': (1, 2),
    'в метафазе мейоза II': (1, 2), 'в анафазе мейоза II': (2, 2),
    'в гамете': (1, 1),
}


def gen_b_chromo(rng):
    org = rng.choice(list(KARYO))
    n2 = KARYO[org]
    ph = rng.choice(list(PHASES))
    what = rng.choice(['хромосом', 'молекул ДНК'])
    kn, kc = PHASES[ph]
    ans = n2 // 2 * (kn if what == 'хромосом' else kc)
    q = (f'В соматических клетках {org} содержится {agree(n2, "хромосома")}. Сколько {what} содержится {ph}? '
         'В ответе запишите только число.')
    e = (f'n = {n2 // 2}. {ph[0].upper() + ph[1:]} набор {kn}n{kc}c: '
         f'{what} = {ans}.')
    return card('num', 'bio-ege-3', q, str(ans), e, {'n2': n2, 'ph': ph, 'what': what},
                core={'n2': n2, 'ph': ph, 'what': what})


def check_b_chromo(c):
    # моделирование: считаем хроматиды у каждой хромосомы по ходу деления
    n = c['n2'] // 2
    ph = c['ph']
    # (число хромосом, хроматид в каждой)
    if 'G1' in ph:
        chrom, cht = 2 * n, 1
    elif ph in ('в клетке после синтетического периода (S) интерфазы', 'в профазе митоза',
                'в метафазе митоза', 'в профазе мейоза I', 'в метафазе мейоза I', 'в анафазе мейоза I'):
        chrom, cht = 2 * n, 2          # в анафазе I к полюсам идут целые двухроматидные хромосомы
    elif ph == 'в анафазе митоза':
        chrom, cht = 4 * n, 1          # хроматиды разошлись и стали хромосомами, клетка ещё одна
    elif ph == 'в каждой дочерней клетке после митоза':
        chrom, cht = 2 * n, 1
    elif ph in ('в каждой клетке после телофазы мейоза I', 'в метафазе мейоза II'):
        chrom, cht = n, 2
    elif ph == 'в анафазе мейоза II':
        chrom, cht = 2 * n, 1
    else:
        chrom, cht = n, 1
    return str(chrom if c['what'] == 'хромосом' else chrom * cht)


def gen_b_chargaff(rng):
    base = rng.choice('АТГЦ')
    pct = rng.choice([x for x in range(8, 43)])
    pair = {'А': 'Т', 'Т': 'А', 'Г': 'Ц', 'Ц': 'Г'}
    other = [b for b in 'АТГЦ' if b not in (base, pair[base])]
    ask = rng.choice(other + [pair[base]])
    ans = pct if ask == pair[base] else 50 - pct
    q = (f'В молекуле двуцепочечной ДНК на долю нуклеотидов с {base} приходится {pct} %. '
         f'Определите долю (%) нуклеотидов с {ask}. В ответе запишите только число.')
    e = (f'По правилу Чаргаффа А = Т, Г = Ц. {base} = {pair[base]} = {pct} %, '
         f'на две другие вместе 100 − 2·{pct} = {100 - 2 * pct} %, каждой по {50 - pct} %.')
    return card('num', 'bio-ege-3', q, str(ans), e, {'base': base, 'pct': pct, 'ask': ask})


def check_b_chargaff(c):
    # строим «модельную» ДНК из 200 пар и считаем доли
    pct = c['pct']
    n = 1000
    a_t = pct * n // 100 if c['base'] in 'АТ' else (50 - pct) * n // 100
    g_c = n // 2 - a_t
    cnt = {'А': a_t, 'Т': a_t, 'Г': g_c, 'Ц': g_c}
    return str(cnt[c['ask']] * 100 // n)


def gen_b_coding(rng):
    n = rng.randint(20, 600)
    mode = rng.choice(['mrna', 'dna2', 'dna1', 'trna', 'triplets', 'back'])
    if mode == 'back':
        q = (f'Фрагмент иРНК (без стоп-кодона) содержит {agree(3 * n, "нуклеотид")}. Сколько аминокислот '
             'кодирует этот фрагмент? В ответе запишите только число.')
        a, e = n, f'Одну аминокислоту кодирует триплет: {3 * n} : 3 = {n}.'
    elif mode == 'len':
        L = 3 * n * Fraction(34, 100)
        q = (f'Белок состоит из {n} аминокислот. Определите длину (нм) участка одной цепи ДНК, '
             'кодирующего этот белок, если расстояние между соседними нуклеотидами 0,34 нм. '
             'Стоп-кодон не учитывайте. Ответ округлите до десятых.')
        a, e = fmt(L, 1), f'{n} × 3 = {3 * n} нуклеотидов; {3 * n} × 0,34 = {fmt(L)} нм.'
        return card('num', 'bio-ege-3', q, a, e, {'n': n, 'mode': mode})
    else:
        what = {'mrna': 'нуклеотидов в иРНК', 'dna2': 'нуклеотидов в двуцепочечном участке гена',
                'dna1': 'нуклеотидов в матричной цепи ДНК', 'trna': 'молекул тРНК участвовали в синтезе',
                'triplets': 'триплетов в иРНК'}[mode]
        mult = {'mrna': 3, 'dna2': 6, 'dna1': 3, 'trna': 1, 'triplets': 1}[mode]
        a = n * mult
        q = (f'Белок состоит из {agree(n, "аминокислота", "gent")}. Сколько {what}? Стоп-кодон и некодирующие '
             'участки не учитывайте. В ответе запишите только число.')
        e = {1: f'Одна аминокислота — один триплет и одна тРНК: {n}.',
             3: f'Одна аминокислота — три нуклеотида: {n} × 3 = {3 * n}.',
             6: f'{n} × 3 = {3 * n} в одной цепи, в двух цепях {6 * n}.'}[mult]
    return card('num', 'bio-ege-3', q, str(a), e, {'n': n, 'mode': mode})


def check_b_coding(c):
    # строим модельную иРНК из n кодонов и считаем всё по ней
    n, m = c['n'], c['mode']
    codons = ['NNN'] * n
    mrna = ''.join(codons)
    gene = (mrna, mrna)                       # две цепи ДНК той же длины
    if m == 'back':
        return str(len(mrna) // 3)
    if m == 'len':
        return fmt(len(gene[0]) * Fraction(34, 100), 1)
    return str({'mrna': len(mrna), 'dna1': len(gene[0]), 'dna2': len(gene[0]) + len(gene[1]),
                'trna': len(codons), 'triplets': len(codons)}[m])


# ---- пищевые цепи (правило 10 %)
CHAINS = [
    ['трава', 'заяц', 'лисица'], ['трава', 'кузнечик', 'лягушка', 'уж', 'орёл'],
    ['фитопланктон', 'зоопланктон', 'сельдь', 'тюлень'], ['водоросли', 'рачки', 'плотва', 'щука'],
    ['листья дуба', 'гусеница', 'синица', 'ястреб'], ['трава', 'мышь', 'сова'],
    ['семена', 'полёвка', 'ласка', 'филин'], ['трава', 'корова', 'человек'],
    ['фитопланктон', 'криль', 'синий кит'], ['злаки', 'саранча', 'ящерица', 'змея', 'коршун'],
    ['листья', 'тля', 'божья коровка', 'скворец'], ['хвоя', 'сосновый шелкопряд', 'кукушка', 'ястреб-перепелятник'],
    ['водоросли', 'моллюски', 'вобла', 'судак', 'человек'], ['трава', 'олень', 'волк'],
]


def gen_b_food(rng):
    ch = rng.choice(CHAINS)
    L = len(ch)
    mode = rng.choice(['need', 'energy', 'top'])
    chain = f'Пищевая цепь: {" → ".join(ch)}.'
    if mode == 'need':
        top = rng.choice([1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30]) * (100 if ch[-1] in ('синий кит', 'тюлень') else 1)
        ans = top * 10 ** (L - 1)
        q = (f'{chain} Используя правило экологической пирамиды (10 %), определите, какая масса (кг) '
             f'организмов первого звена ({ch[0]}) необходима, чтобы масса {inflect(ch[-1], "gent")} увеличилась на {top} кг. '
             'В ответе запишите только число.')
        e = f'Звеньев {L}, переходов {L - 1}: {top} × 10^{L - 1} = {ans} кг.'
        chk = {'L': L, 'mode': mode, 'x': top}
    elif mode == 'energy':
        k = rng.randint(2, L)
        e1 = rng.choice([1, 2, 3, 4, 5, 6, 8]) * 10 ** rng.randint(max(k - 1, 3), 6)
        ans = Fraction(e1, 10 ** (k - 1))
        q = (f'{chain} Продуценты накопили {e1} кДж энергии. '
             f'Сколько энергии (кДж) перейдёт к организмам {k}-го трофического уровня ({ch[k - 1]}) '
             'по правилу 10 %? В ответе запишите только число.')
        e = f'С каждого уровня на следующий переходит 10 %: {e1} / 10^{k - 1} = {fmt(ans)} кДж.'
        ans = fmt(ans)
        chk = {'L': L, 'mode': mode, 'x': e1, 'k': k}
    else:
        m1 = rng.choice([1, 2, 3, 4, 5, 6, 8]) * 10 ** max(L - 1, 3) * rng.choice([1, 10])
        ans = Fraction(m1, 10 ** (L - 1))
        q = (f'{chain} Биомасса первого звена ({ch[0]}) — {m1} кг. '
             f'Какая биомасса (кг) {inflect(ch[-1], "gent")} может образоваться за счёт этой пищи по правилу 10 %? '
             'В ответе запишите только число.')
        e = f'{m1} / 10^{L - 1} = {fmt(ans)} кг.'
        ans = fmt(ans)
        chk = {'L': L, 'mode': mode, 'x': m1}
    return card('num', 'bio-ege-3', q, str(ans), e, chk)


def check_b_food(c):
    x = Fraction(c['x'])
    if c['mode'] == 'need':
        for _ in range(c['L'] - 1):
            x /= Fraction(1, 10)
    else:
        steps = (c['k'] - 1) if c['mode'] == 'energy' else c['L'] - 1
        for _ in range(steps):
            x *= Fraction(1, 10)
    return fmt(x)


# ---- генетика: признаки (доминантный, рецессивный) — стандартные учебные примеры
TRAITS = [
    ('горох', 'жёлтые семена', 'зелёные семена'), ('горох', 'гладкие семена', 'морщинистые семена'),
    ('горох', 'высокий стебель', 'карликовый стебель'), ('горох', 'пурпурные цветки', 'белые цветки'),
    ('томат', 'красные плоды', 'жёлтые плоды'), ('томат', 'высокий стебель', 'карликовый стебель'),
    ('морская свинка', 'чёрная шерсть', 'белая шерсть'), ('морская свинка', 'вихрастая шерсть', 'гладкая шерсть'),
    ('крупный рогатый скот', 'комолость', 'рогатость'), ('дрозофила', 'серое тело', 'чёрное тело'),
    ('дрозофила', 'нормальные крылья', 'зачаточные крылья'), ('тыква', 'белые плоды', 'жёлтые плоды'),
    ('кролик', 'мохнатый мех', 'гладкий мех'), ('овёс', 'раннеспелость', 'позднеспелость'),
    ('собака', 'жёсткая шерсть', 'мягкая шерсть'), ('человек', 'карие глаза', 'голубые глаза'),
]
# неполное доминирование: (организм, AA, Aa, aa)
INCOMPLETE = [
    ('ночная красавица', 'красные цветки', 'розовые цветки', 'белые цветки'),
    ('львиный зев', 'красные цветки', 'розовые цветки', 'белые цветки'),
    ('земляника', 'красные ягоды', 'розовые ягоды', 'белые ягоды'),
    ('андалузские куры', 'чёрное оперение', 'голубое оперение', 'белое оперение'),
    ('крупный рогатый скот (шортгорнская порода)', 'красная масть', 'чалая масть', 'белая масть'),
]
GENO1 = ['AA', 'Aa', 'aa']
GNAME = {'AA': 'гомозиготных доминантных', 'Aa': 'гетерозиготных', 'aa': 'гомозиготных рецессивных'}


def cross1(p1, p2):
    """Моногибридное скрещивание по формуле: вероятности генотипов."""
    fa = {'AA': Fraction(1), 'Aa': Fraction(1, 2), 'aa': Fraction(0)}
    a1, a2 = fa[p1], fa[p2]
    return {'AA': a1 * a2, 'Aa': a1 * (1 - a2) + (1 - a1) * a2, 'aa': (1 - a1) * (1 - a2)}


def seq(r):
    return ''.join(str(x) for x in r)


def gen_b_mono(rng):
    """ЕГЭ 4: моногибридное скрещивание; chk kind=ratio (соотношение) или prob (вероятность, %)."""
    kind = rng.choice(['ratio', 'prob'])
    inc = rng.random() < 0.3
    for _ in range(100):
        p1, p2 = rng.choice([('Aa', 'Aa'), ('Aa', 'aa'), ('AA', 'aa'), ('AA', 'Aa'), ('Aa', 'Aa'), ('Aa', 'aa')])
        g = cross1(p1, p2)
        if kind == 'ratio' and sum(1 for v in g.values() if v) > 1:
            break
        if kind == 'prob' and 'Aa' in (p1, p2):
            break
    if inc:
        org, ph_aa, ph_Aa, ph_a = rng.choice(INCOMPLETE)
        desc = {'AA': ph_aa, 'Aa': ph_Aa, 'aa': ph_a}
        intro = (f'У {inflect(org, "gent")} признак наследуется по типу неполного доминирования: '
                 f'AA — {ph_aa}, Aa — {ph_Aa}, aa — {ph_a}.')
        phen = {desc[k]: v for k, v in g.items() if v}
    else:
        org, dom, rec = rng.choice(TRAITS)
        desc = {'AA': dom, 'Aa': dom, 'aa': rec}
        intro = f'У {inflect(org, "gent")} ген, определяющий {inflect(dom, "accs")} (A), доминирует над геном, определяющим {inflect(rec, "accs")} (a).'
        phen = Counter()
        for k, v in g.items():
            if v:
                phen[desc[k]] += v
    word = lambda gt: {'AA': 'гомозиготную доминантную', 'Aa': 'гетерозиготную', 'aa': 'гомозиготную рецессивную'}[gt]
    word2 = lambda gt: {'AA': 'гомозиготной доминантной', 'Aa': 'гетерозиготной', 'aa': 'гомозиготной рецессивной'}[gt]
    parents = f'Скрестили {word(p1)} особь с {word2(p2)}.'
    gt = None
    if kind == 'ratio':
        mode = rng.choice(['phen', 'gen']) if inc or len(phen) != sum(1 for v in g.values() if v) else 'phen'
        if mode == 'phen' and len(phen) == 1:
            mode = 'gen'
        r = ratio([int(v * 4) for v in (phen.values() if mode == 'phen' else [v for v in g.values() if v])])
        what = 'фенотипов' if mode == 'phen' else 'генотипов'
        q = f'{intro} {parents} Определите соотношение {what} в потомстве. Ответ запишите в виде последовательности цифр, показывающих соотношение получившихся {what}, в порядке их убывания.'
        a = seq(r)
    else:
        mode = 'prob'
        opts = [x for x in GENO1 if 0 < g[x] < 1] or GENO1
        gt = rng.choice(opts)
        if inc:
            q = f'{intro} {parents} Какова вероятность (%) появления в потомстве особей, имеющих {inflect(desc[gt], "accs")}? В ответе запишите только число.'
        else:
            q = f'{intro} {parents} Какова вероятность (%) появления в потомстве {GNAME[gt]} особей? В ответе запишите только число.'
        a = fmt(g[gt] * 100)
    tab = ', '.join(f'{k} — {fmt(v * 100)} %' for k, v in g.items() if v)
    e = f'Генотипы потомков: {tab}.'
    chk = {'p1': p1, 'p2': p2, 'inc': inc, 'mode': mode, 'gt': gt, 'kind': kind}
    return card('num', 'bio-ege-4', q, a, e, chk, core=chk)


def punnett(p1, p2):
    """Независимая проверка: перебор гамет (решётка Пеннета)."""
    out = Counter()
    for x in p1:
        for y in p2:
            out[''.join(sorted(x + y))] += 1   # 'AA', 'Aa', 'aa' (A < a)
    return out


def check_b_mono(c):
    pun = punnett(c['p1'], c['p2'])
    tot = sum(pun.values())
    if c['mode'] == 'gen':
        return seq(ratio(list(pun.values())))
    if c['mode'] == 'prob':
        return fmt(Fraction(pun.get(c['gt'], 0) * 100, tot))
    ph = Counter()
    for gt, n in pun.items():
        ph[gt if c['inc'] else ('dom' if 'A' in gt else 'rec')] += n
    if c['mode'] == 'nphen':
        return str(len(ph))
    return seq(ratio(list(ph.values())))


def gametes(gt):
    """Типы гамет по генотипу 'AaBb' (гены не сцеплены)."""
    pairs = [gt[i:i + 2] for i in range(0, len(gt), 2)]
    return [''.join(p) for p in itertools.product(*[sorted(set(pr)) for pr in pairs])]


def gen_b_dihybrid(rng):
    mode = rng.choice(['phen', 'prob', 'gam', 'nphen', 'ngen'])
    if mode == 'ngen':
        p1, p2 = rng.choice([('AaBb', 'AaBb'), ('AaBb', 'aabb'), ('AaBb', 'Aabb'), ('AaBb', 'aaBb'), ('AaBB', 'AaBb'), ('Aabb', 'aaBb')])
        n = len({''.join(sorted(x[0] + y[0])) + ''.join(sorted(x[1] + y[1])) for x in gametes(p1) for y in gametes(p2)})
        q = (f'Скрестили особей с генотипами {p1} и {p2} (гены не сцеплены, доминирование полное). '
             'Сколько разных генотипов может получиться в потомстве? В ответе запишите только число.')
        return card('num', 'bio-ege-4', q, str(n), f'Перебор гамет {", ".join(gametes(p1))} × {", ".join(gametes(p2))}: генотипов {n}.',
                    {'p1': p1, 'p2': p2, 'mode': mode})
    if mode == 'gam':
        k = rng.randint(2, 5)
        letters = 'ABCDE'[:k]
        gt = ''.join(rng.choice([l + l, l + l.lower(), l.lower() * 2]) for l in letters)
        het = sum(1 for i in range(0, 2 * k, 2) if gt[i] != gt[i + 1])
        q = f'Сколько типов гамет образует особь с генотипом {gt}, если гены наследуются независимо? В ответе запишите только число.'
        return card('num', 'bio-ege-4', q, str(2 ** het), f'Гетерозиготных пар {het}, типов гамет 2^{het} = {2 ** het}.',
                    {'gt': gt, 'mode': mode})
    choice = lambda l: rng.choice([l + l, l + l.lower(), l.lower() * 2])
    while True:
        p1, p2 = choice('A') + choice('B'), choice('A') + choice('B')
        if not (p1.count('a') + p1.count('b') + p2.count('a') + p2.count('b') and ('Aa' in p1 + p2 or 'Bb' in p1 + p2)):
            continue
        ga_ = cross1(p1[:2], p2[:2])
        gb_ = cross1(p1[2:].replace('B', 'A').replace('b', 'a'), p2[2:].replace('B', 'A').replace('b', 'a'))
        if mode in ('phen', 'nphen') and (ga_['AA'] + ga_['Aa'] in (0, 1) and gb_['AA'] + gb_['Aa'] in (0, 1)):
            continue                     # один фенотипический класс — вырожденная задача
        break
    ga = cross1(p1[:2], p2[:2])
    gb = cross1(p1[2:].replace('B', 'A').replace('b', 'a'), p2[2:].replace('B', 'A').replace('b', 'a'))
    pa = {'A_': ga['AA'] + ga['Aa'], 'aa': ga['aa']}
    pb = {'B_': gb['AA'] + gb['Aa'], 'bb': gb['aa']}
    phen = {x + y: pa[x] * pb[y] for x in pa for y in pb if pa[x] * pb[y]}
    q0 = f'Скрестили особей с генотипами {p1} и {p2} (гены не сцеплены, доминирование полное).'
    if mode == 'phen':
        r = ratio([int(v * 16) for v in phen.values()])
        q = q0 + ' Определите соотношение фенотипов потомков. Ответ запишите в виде последовательности цифр в порядке их убывания.'
        a = seq(r)
    elif mode == 'nphen':
        q = q0 + ' Сколько фенотипических классов получится в потомстве? В ответе запишите только число.'
        a = str(len(phen))
    else:
        ok = [t for t in phen if (phen[t] * 100).denominator == 1 and phen[t] < 1]
        if not ok:
            return gen_b_dihybrid(rng)
        target = rng.choice(ok)
        name = {'A_B_': 'с обоими доминантными признаками', 'A_bb': 'с доминантным первым и рецессивным вторым признаком',
                'aaB_': 'с рецессивным первым и доминантным вторым признаком', 'aabb': 'с обоими рецессивными признаками'}[target]
        q = q0 + f' Какова вероятность (%) появления потомков {name}? В ответе запишите только число.'
        a = fmt(phen[target] * 100)
        mode = 'prob:' + target
    e = 'Фенотипы: ' + ', '.join(f'{k} — {fmt(v * 100, 2)} %' for k, v in phen.items()) + '. Признаки наследуются независимо, вероятности перемножаются.'
    return card('num', 'bio-ege-4', q, a, e, {'p1': p1, 'p2': p2, 'mode': mode})


def check_b_dihybrid(c):
    if c['mode'] == 'gam':
        return str(len(set(gametes(c['gt']))))
    if c['mode'] == 'ngen':
        return str(len(Counter(tuple(sorted([x[0], y[0]]) + sorted([x[1], y[1]])) for x in gametes(c['p1']) for y in gametes(c['p2']))))
    g1, g2 = gametes(c['p1']), gametes(c['p2'])
    ph = Counter()
    for x in g1:
        for y in g2:
            A = 'A_' if 'A' in x[0] + y[0] else 'aa'
            B = 'B_' if 'B' in x[1] + y[1] else 'bb'
            ph[A + B] += 1
    tot = len(g1) * len(g2)
    if c['mode'] == 'phen':
        return seq(ratio(list(ph.values())))
    if c['mode'] == 'nphen':
        return str(len(ph))
    return fmt(Fraction(ph[c['mode'].split(':')[1]] * 100, tot))


BLOOD = {'I⁰I⁰': 'I', 'IᴬIᴬ': 'II', 'IᴬI⁰': 'II', 'IᴮIᴮ': 'III', 'IᴮI⁰': 'III', 'IᴬIᴮ': 'IV'}
ALLELES = {'I⁰I⁰': ['0', '0'], 'IᴬIᴬ': ['A', 'A'], 'IᴬI⁰': ['A', '0'], 'IᴮIᴮ': ['B', 'B'],
           'IᴮI⁰': ['B', '0'], 'IᴬIᴮ': ['A', 'B']}


def blood_of(x, y):
    s = {x, y}
    if s == {'A', 'B'}:
        return 'IV'
    if 'A' in s:
        return 'II'
    if 'B' in s:
        return 'III'
    return 'I'


RH = {'RR': 'резус-положительный', 'Rr': 'резус-положительный', 'rr': 'резус-отрицательный'}


def gen_b_blood(rng):
    m, f = rng.choice(list(BLOOD)), rng.choice(list(BLOOD))
    probs = Counter()
    for x in ALLELES[m]:
        for y in ALLELES[f]:
            probs[blood_of(x, y)] += Fraction(1, 4)
    mode = rng.choice(['p', 'p', 'n'])
    base = f'Мать имеет генотип {m} ({BLOOD[m]} группа крови), отец — {f} ({BLOOD[f]} группа).'
    grp = rng.choice(['I', 'II', 'III', 'IV'])
    chk = {'m': m, 'f': f, 'grp': grp, 'mode': mode}
    e = ('Гаметы матери: ' + ', '.join(ALLELES[m]) + '; отца: ' + ', '.join(ALLELES[f]) + '. '
         + ', '.join(f'{k} — {fmt(v * 100)} %' for k, v in sorted(probs.items())) + '. Iᴬ и Iᴮ кодоминантны, I⁰ рецессивен.')
    if mode == 'n':
        chk['grp'] = None
        q = base + ' Сколько разных групп крови может быть у их детей? В ответе запишите только число.'
        return card('num', 'bio-ege-4', q, str(len(probs)), e, chk)
    if mode == 'rh':
        rm, rf = rng.choice(list(RH)), rng.choice(list(RH))
        want = rng.choice(['RR', 'rr', 'R_'])
        pr = {'RR': Fraction(rm.count('R'), 2) * Fraction(rf.count('R'), 2),
              'rr': Fraction(rm.count('r'), 2) * Fraction(rf.count('r'), 2)}
        pr['R_'] = 1 - pr['rr']
        name = {'RR': 'резус-положительного гомозиготного (RR)', 'rr': 'резус-отрицательного', 'R_': 'резус-положительного'}[want]
        ans = fmt(probs[grp] * pr[want] * 100, 2)
        q = (f'Мать — {m}{rm}, отец — {f}{rf} (R — резус-положительность, доминирует; гены не сцеплены). '
             f'Какова вероятность (%) рождения {name} ребёнка с {grp} группой крови? Ответ округлите до сотых.')
        chk.update(rm=rm, rf=rf, want=want)
        return card('num', 'bio-ege-4', q, ans, e + f' По резусу: {fmt(pr[want] * 100, 2)} %; вероятности перемножаются.', chk)
    if not probs[grp] and rng.random() < 0.85:
        return gen_b_blood(rng)
    q = base + f' Какова вероятность (%) рождения ребёнка с {grp} группой крови? В ответе запишите только число.'
    return card('num', 'bio-ege-4', q, fmt(probs[grp] * 100), e, chk)


def _grp(x, y):
    ag = frozenset(''.join({x, y} - {'0'}))
    return {frozenset(): 'I', frozenset('A'): 'II', frozenset('B'): 'III', frozenset('AB'): 'IV'}[ag]


def check_b_blood(c):
    # перебор через антигены на эритроцитах: A-антиген, B-антиген
    groups = Counter(_grp(x, y) for x in ALLELES[c['m']] for y in ALLELES[c['f']])
    if c['mode'] == 'n':
        return str(len(groups))
    if c['mode'] == 'rh':
        hit = tot = 0
        for x in ALLELES[c['m']]:
            for y in ALLELES[c['f']]:
                for a in c['rm']:
                    for b in c['rf']:
                        rh = ''.join(sorted(a + b))
                        ok_rh = {'RR': rh == 'RR', 'rr': rh == 'rr', 'R_': 'R' in rh}[c['want']]
                        tot += 1
                        hit += _grp(x, y) == c['grp'] and ok_rh
        return fmt(Fraction(hit * 100, tot), 2)
    return fmt(Fraction(groups[c['grp']] * 100, 4))


XL = [('гемофилия', 'H', 'h'), ('дальтонизм', 'D', 'd'), ('отсутствие потовых желёз', 'A', 'a')]
XD = [('гипофосфатемический рахит', 'R', 'r'), ('коричневая эмаль зубов', 'B', 'b')]   # X-сцепленные доминантные


def gen_b_xlinked(rng):
    dom = rng.random() < 0.35
    dis, D, d = rng.choice(XD if dom else XL)
    mom = rng.choice([f'X{D}X{D}', f'X{D}X{d}', f'X{d}X{d}'])
    dad = rng.choice([f'X{D}Y', f'X{d}Y'])
    who = rng.choice(['всех детей', 'сыновей', 'дочерей'])
    what = rng.choice(['больных', 'здоровых'] + ([] if dom or who == 'сыновей' else ['девочек-носительниц']))
    kids = [m + f for m in (mom[:2], mom[2:]) for f in (dad[:2], dad[2:])]
    pool = [k for k in kids if who == 'всех детей' or (('Y' in k) == (who == 'сыновей'))]
    if dom:
        sick = lambda k: ('X' + D) in k
    else:
        sick = lambda k: (k.count('X' + d) == 2) or ('Y' in k and 'X' + d in k)
    carrier = lambda k: 'Y' not in k and k.count('X' + d) == 1
    good = {'больных': sick, 'здоровых': lambda k: not sick(k), 'девочек-носительниц': carrier}[what]
    n = sum(good(k) for k in pool)
    if n in (0, len(pool)) and rng.random() < 0.85:
        return gen_b_xlinked(rng)
    ans = fmt(Fraction(100 * n, len(pool)))
    kind = 'доминантного' if dom else 'рецессивного'
    q = (f'Ген {kind} признака «{dis}» ({D if dom else d}) сцеплен с X-хромосомой. Мать — {mom}, отец — {dad}. '
         f'Какова вероятность (%) рождения {what} среди {who}? В ответе запишите только число.')
    e = f'Возможные дети: {", ".join(kids)}. Среди {who}: {n} из {len(pool)} — {what}.'
    norm = lambda g: g.replace(D, 'D').replace(d, 'd')
    return card('num', 'bio-ege-4', q, ans, e, {'mom': mom, 'dad': dad, 'who': who, 'what': what, 'd': d, 'D': D, 'dom': dom},
                core={'mom': norm(mom), 'dad': norm(dad), 'who': who, 'what': what, 'dom': dom})


def check_b_xlinked(c):
    D, d = c['D'], c['d']
    mg = [c['mom'][i:i + 2] for i in (0, 2)]
    fg = [c['dad'][:2], 'Y']
    tot = hit = 0
    for m in mg:
        for f in fg:
            son = f == 'Y'
            if c['who'] == 'сыновей' and not son or c['who'] == 'дочерей' and son:
                continue
            alleles = [m] + ([] if son else [f])
            n_rec = alleles.count('X' + d)
            ill = n_rec < len(alleles) if c['dom'] else n_rec == len(alleles)
            carrier = not son and n_rec == 1
            tot += 1
            hit += {'больных': ill, 'здоровых': not ill, 'девочек-носительниц': carrier}[c['what']]
    return fmt(Fraction(100 * hit, tot))


def gen_b_linkage(rng):
    dist = rng.randint(5, 30)
    cis = rng.random() < 0.6
    geno = 'AB//ab' if cis else 'Ab//aB'
    parental = {'AaBb', 'aabb'} if cis else {'Aabb', 'aaBb'}
    if rng.random() < 0.3:
        total = rng.choice([200, 400, 500, 800, 1000, 1200, 1600, 2000])
        rec = total * dist // 100
        if rec % 2 or total * dist % 100:
            return gen_b_linkage(rng)
        nonrec = total - rec
        cls = sorted(parental) + sorted({'AaBb', 'aabb', 'Aabb', 'aaBb'} - parental)
        counts = [nonrec // 2, nonrec // 2, rec // 2, rec // 2]
        mix = list(zip(cls, counts))
        rng.shuffle(mix)
        cls, counts = [x for x, _ in mix], [y for _, y in mix]
        q = (f'При анализирующем скрещивании дигетерозиготы {geno} с ab//ab получено потомство: '
             + ', '.join(f'{g} — {n}' for g, n in zip(cls, counts))
             + '. Определите расстояние между генами A и B (сМ). В ответе запишите только число.')
        e = f'Кроссоверных потомков {rec // 2} + {rec // 2} = {rec} из {total}: {rec} / {total} × 100 = {dist} сМ.'
        return card('num', 'bio-ege-4', q, str(dist), e, {'mode': 'rev', 'cls': cls, 'counts': counts, 'cis': cis})
    dist -= dist % 2                   # проценты классов — целые
    cls = rng.choice(['AaBb', 'aabb', 'Aabb', 'aaBb'])
    val = Fraction(100 - dist, 2) if cls in parental else Fraction(dist, 2)
    q = (f'Гены A и B расположены в одной хромосоме, частота кроссинговера между ними — {dist} % (расстояние {dist} сМ). Дигетерозиготную особь {geno} '
         f'скрестили с рецессивной дигомозиготой ab//ab. Какой процент потомков будет иметь генотип {cls}? '
         'В ответе запишите только число.')
    e = (f'Кроссоверных гамет {dist} %, по {fmt(Fraction(dist, 2))} % каждого типа; некроссоверных '
         f'по {fmt(Fraction(100 - dist, 2))} %. {cls} — {"некроссоверный" if cls in parental else "кроссоверный"} класс.')
    return card('num', 'bio-ege-4', q, fmt(val), e, {'mode': 'fwd', 'dist': dist, 'cis': cis, 'cls': cls})


def check_b_linkage(c):
    if c['mode'] == 'rev':
        # кроссоверные классы — те, что реже всего встречаются
        by = sorted(zip(c['counts'], c['cls']))
        rec = by[0][0] + by[1][0]
        return fmt(Fraction(rec * 100, sum(c['counts'])))
    # моделируем 10000 гамет дигетерозиготы
    N = 10000
    chroms = ('AB', 'ab') if c['cis'] else ('Ab', 'aB')
    rec = N * c['dist'] // 100
    gam = Counter({chroms[0]: Fraction(N - rec, 2), chroms[1]: Fraction(N - rec, 2)})
    gam[chroms[0][0] + chroms[1][1]] += Fraction(rec, 2)
    gam[chroms[1][0] + chroms[0][1]] += Fraction(rec, 2)
    t = c['cls']
    want = ('A' if 'A' in t else 'a') + ('B' if 'B' in t else 'b')
    return fmt(gam[want] * 100 / N)


def gen_b_hardy(rng):
    q_ = Fraction(rng.randint(1, 99), 100)
    p_ = 1 - q_
    mode = rng.choice(['het', 'dom', 'p', 'q'])
    rec = q_ * q_
    if mode in ('het', 'dom', 'p', 'q'):
        base = f'В равновесной популяции доля особей с рецессивным признаком (aa) составляет {fmt(rec * 100, 4)} %.'
    if mode == 'het':
        ans, what = fmt(2 * p_ * q_ * 100, 2), 'долю гетерозигот (%)'
    elif mode == 'dom':
        ans, what = fmt(p_ * p_ * 100, 2), 'долю доминантных гомозигот (%)'
    elif mode == 'p':
        ans, what = fmt(p_, 2), 'частоту доминантного аллеля A (в долях единицы)'
    else:
        ans, what = fmt(q_, 2), 'частоту рецессивного аллеля a (в долях единицы)'
    q = f'{base} Используя закон Харди — Вайнберга, определите {what}. Ответ округлите до сотых.'
    e = f'q² = {fmt(rec, 4)} → q = {fmt(q_)}, p = 1 − q = {fmt(p_)}; p² = {fmt(p_ * p_, 4)}, 2pq = {fmt(2 * p_ * q_, 4)}.'
    return card('num', 'bio-ege-27', q, ans, e, {'rec': str(rec), 'mode': mode})


def check_b_hardy(c):
    rec = Fraction(c['rec'])
    # ищем q перебором с шагом 0.0001 (независимо от генератора)
    qq = min((Fraction(i, 10000) for i in range(10001)), key=lambda x: abs(x * x - rec))
    pp = 1 - qq
    return {'het': fmt(2 * pp * qq * 100, 2), 'dom': fmt(pp * pp * 100, 2), 'p': fmt(pp, 2), 'q': fmt(qq, 2)}[c['mode']]


# ---- молекулярная биология: транскрипция, трансляция, антикодон
CODE = {}
_B = 'УЦАГ'
_AA = ('Фен Фен Лей Лей Сер Сер Сер Сер Тир Тир стоп стоп Цис Цис стоп Трп '
       'Лей Лей Лей Лей Про Про Про Про Гис Гис Глн Глн Арг Арг Арг Арг '
       'Иле Иле Иле Мет Тре Тре Тре Тре Асн Асн Лиз Лиз Сер Сер Арг Арг '
       'Вал Вал Вал Вал Ала Ала Ала Ала Асп Асп Глу Глу Гли Гли Гли Гли').split()
for i1, b1 in enumerate(_B):
    for i2, b2 in enumerate(_B):
        for i3, b3 in enumerate(_B):
            CODE[b1 + b2 + b3] = _AA[i1 * 16 + i2 * 4 + i3]

DNA_C = {'А': 'Т', 'Т': 'А', 'Г': 'Ц', 'Ц': 'Г'}
RNA_FROM_DNA = {'А': 'У', 'Т': 'А', 'Г': 'Ц', 'Ц': 'Г'}   # матрица ДНК → РНК
RNA_C = {'А': 'У', 'У': 'А', 'Г': 'Ц', 'Ц': 'Г'}


def rand_coding(rng, codons):
    """Кодирующая цепь ДНК 5'→3' из смысловых кодонов (без стоп-кодонов)."""
    sense = [c for c, aa in CODE.items() if aa != 'стоп']
    return ''.join(rng.choice(sense) for _ in range(codons)).replace('У', 'Т')


def gen_b_transcr(rng):
    coding = rand_coding(rng, rng.randint(4, 6))
    templ = ''.join(DNA_C[b] for b in coding)            # 3'→5' под кодирующей
    mrna = coding.replace('Т', 'У')
    top_is_templ = rng.random() < 0.5
    if top_is_templ:   # матричная цепь сверху, записана 5'→3'
        up, down = templ[::-1], coding[::-1]
        q = (f"Фрагмент ДНК (верхняя цепь матричная):\n5ʹ-{up}-3ʹ\n3ʹ-{down}-5ʹ\n"
             'Определите последовательность иРНК, синтезируемой на этом фрагменте.')
    else:
        up, down = coding, templ
        q = (f"Фрагмент ДНК (нижняя цепь матричная):\n5ʹ-{up}-3ʹ\n3ʹ-{down}-5ʹ\n"
             'Определите последовательность иРНК, синтезируемой на этом фрагменте.')
    ok = f"5ʹ-{mrna}-3ʹ"
    wrong = [f"5ʹ-{coding}-3ʹ",                                   # не заменили Т на У
             f"5ʹ-{templ.replace('Т', 'У')}-3ʹ",                   # переписали матрицу
             f"5ʹ-{mrna[::-1]}-3ʹ",                                # перепутали направление
             f"5ʹ-{''.join(RNA_C[b] for b in mrna)}-3ʹ"]           # комплементарна не той цепи
    o, a = one(rng, ok, wrong)
    e = ('иРНК комплементарна матричной цепи и антипараллельна ей; вместо Т — У. '
         'Она совпадает с кодирующей (смысловой) цепью, где Т заменён на У.')
    return card('one', 'bio-ege-27', q, a, e, {'up': up, 'down': down, 'top_is_templ': top_is_templ, 'ok': ok}, o=o)


def check_b_transcr(c):
    # берём матричную цепь, читаем её 3'→5' и строим РНК 5'→3'
    templ_5to3 = c['up'] if c['top_is_templ'] else c['down'][::-1]
    rna_3to5_read = templ_5to3[::-1]       # читаем матрицу от 3' к 5'
    rna = ''.join(RNA_FROM_DNA[b] for b in rna_3to5_read)
    return f'5ʹ-{rna}-3ʹ' == c['ok']


def gen_b_transl(rng):
    n = rng.randint(3, 5)
    sense = [c for c, aa in CODE.items() if aa != 'стоп']
    codons = [rng.choice(sense) for _ in range(n)]
    mrna = ''.join(codons)
    pep = '-'.join(CODE[c] for c in codons)
    rev = mrna[::-1]
    rev_pep = '-'.join(CODE[rev[i:i + 3]] for i in range(0, len(rev), 3))
    comp = ''.join(RNA_C[b] for b in mrna)
    comp_pep = '-'.join(CODE[comp[i:i + 3]] for i in range(0, len(comp), 3))
    shift = mrna[1:] + mrna[0]
    shift_pep = '-'.join(CODE[shift[i:i + 3]] for i in range(0, len(shift), 3))
    q = (f"Фрагмент иРНК: 5ʹ-{mrna}-3ʹ. Определите последовательность аминокислот во фрагменте белка, "
         'используя таблицу генетического кода.')
    o, a = one(rng, pep, [rev_pep, comp_pep, shift_pep, '-'.join(reversed(pep.split('-')))])
    e = f"Кодоны читаются с 5ʹ-конца по три: {' '.join(codons)} → {pep}."
    return card('one', 'bio-ege-27', q, a, e, {'mrna': mrna, 'pep': pep}, o=o)


def check_b_transl(c):
    # независимая таблица: по правилам «второе основание»
    second = {'У': None, 'Ц': None, 'А': None, 'Г': None}
    table = {
        ('У', 'У'): 'Фен Фен Лей Лей', ('У', 'Ц'): 'Сер Сер Сер Сер', ('У', 'А'): 'Тир Тир стоп стоп', ('У', 'Г'): 'Цис Цис стоп Трп',
        ('Ц', 'У'): 'Лей Лей Лей Лей', ('Ц', 'Ц'): 'Про Про Про Про', ('Ц', 'А'): 'Гис Гис Глн Глн', ('Ц', 'Г'): 'Арг Арг Арг Арг',
        ('А', 'У'): 'Иле Иле Иле Мет', ('А', 'Ц'): 'Тре Тре Тре Тре', ('А', 'А'): 'Асн Асн Лиз Лиз', ('А', 'Г'): 'Сер Сер Арг Арг',
        ('Г', 'У'): 'Вал Вал Вал Вал', ('Г', 'Ц'): 'Ала Ала Ала Ала', ('Г', 'А'): 'Асп Асп Глу Глу', ('Г', 'Г'): 'Гли Гли Гли Гли',
    }
    del second
    m = c['mrna']
    out = []
    for i in range(0, len(m), 3):
        c1, c2, c3 = m[i:i + 3]
        out.append(table[(c1, c2)].split()[_B.index(c3)])
    return '-'.join(out) == c['pep']


def gen_b_anticodon(rng):
    sense = [c for c, aa in CODE.items() if aa != 'стоп']
    cod = rng.choice(sense)
    anti_3to5 = ''.join(RNA_C[b] for b in cod)
    anti = anti_3to5[::-1]
    mode = rng.choice(['codon', 'anti', 'dna'])
    if mode == 'codon':
        q = (f"Кодон иРНК 5ʹ-{cod}-3ʹ. Какой антикодон тРНК (запись 5ʹ→3ʹ) ему соответствует и какую "
             'аминокислоту переносит эта тРНК?')
        ok = f"5ʹ-{anti}-3ʹ, {CODE[cod]}"
        wrong = [f"5ʹ-{anti_3to5}-3ʹ, {CODE[cod]}",            # не развернули направление
                 f"5ʹ-{anti}-3ʹ, {CODE[anti]}",                  # аминокислоту искали по антикодону
                 f"5ʹ-{cod}-3ʹ, {CODE[cod]}",
                 f"5ʹ-{anti_3to5}-3ʹ, {CODE[anti_3to5]}"]
        extra = []
    else:
        if mode == 'anti':
            q = f"Антикодон тРНК 5ʹ-{anti}-3ʹ. Какую аминокислоту переносит эта тРНК? Используйте таблицу генетического кода."
            wrong = [CODE[anti], CODE[anti_3to5], CODE[cod[::-1]]]
        else:
            templ = ''.join({'А': 'Т', 'У': 'А', 'Г': 'Ц', 'Ц': 'Г'}[b] for b in cod)[::-1]   # матрица 5'→3'
            q = f"Триплет матричной цепи ДНК 5ʹ-{templ}-3ʹ. Какую аминокислоту кодирует этот триплет?"
            wrong = [CODE[templ.replace('Т', 'У')], CODE[templ[::-1].replace('Т', 'У')], CODE[cod[::-1]]]
        ok = CODE[cod]
        wrong = [w for w in wrong if w != 'стоп']
        extra = sorted({a for a in _AA if a not in ('стоп', ok)})
        rng.shuffle(extra)
    o, a = one(rng, ok, wrong + extra)
    e = (f"Кодон иРНК 5ʹ-{cod}-3ʹ ↔ антикодон 3ʹ-{anti_3to5}-5ʹ (= 5ʹ-{anti}-3ʹ). "
         f"Аминокислоту находят только по кодону иРНК: {CODE[cod]}.")
    return card('one', 'bio-ege-27', q, a, e, {'cod': cod, 'ok': ok, 'mode': mode}, o=o)


def check_b_anticodon(c):
    cod = c['cod']
    # антипараллельное спаривание: позиция i кодона ↔ позиция 2−i антикодона (5'→3')
    anti = ['?'] * 3
    for i, b in enumerate(cod):
        anti[2 - i] = {'А': 'У', 'У': 'А', 'Г': 'Ц', 'Ц': 'Г'}[b]
    if c['mode'] == 'codon':
        return f"5ʹ-{''.join(anti)}-3ʹ, {CODE[cod]}" == c['ok']
    # для 'anti' и 'dna' восстанавливаем кодон обратно из антикодона
    back = ''.join({'А': 'У', 'У': 'А', 'Г': 'Ц', 'Ц': 'Г'}[b] for b in reversed(anti))
    return CODE[back] == c['ok']


# ---- систематика (ЕГЭ 12, ОГЭ 3): последовательность таксонов
TAXA = [
    ['Животные', 'Хордовые', 'Млекопитающие', 'Хищные', 'Псовые', 'Волк', 'Волк серый'],
    ['Животные', 'Хордовые', 'Млекопитающие', 'Хищные', 'Медвежьи', 'Медведь', 'Медведь бурый'],
    ['Животные', 'Хордовые', 'Млекопитающие', 'Хищные', 'Кошачьи', 'Рысь', 'Рысь обыкновенная'],
    ['Животные', 'Хордовые', 'Млекопитающие', 'Зайцеобразные', 'Зайцевые', 'Заяц', 'Заяц-беляк'],
    ['Животные', 'Хордовые', 'Млекопитающие', 'Грызуны', 'Беличьи', 'Белка', 'Белка обыкновенная'],
    ['Животные', 'Хордовые', 'Птицы', 'Воробьинообразные', 'Синицевые', 'Синица', 'Большая синица'],
    ['Животные', 'Хордовые', 'Лучепёрые рыбы', 'Окунеобразные', 'Окунёвые', 'Окунь', 'Окунь речной'],
    ['Животные', 'Хордовые', 'Лучепёрые рыбы', 'Щукообразные', 'Щуковые', 'Щука', 'Щука обыкновенная'],
    ['Животные', 'Членистоногие', 'Насекомые', 'Перепончатокрылые', 'Настоящие пчёлы', 'Пчела', 'Пчела медоносная'],
    ['Животные', 'Членистоногие', 'Насекомые', 'Чешуекрылые', 'Белянки', 'Белянка', 'Белянка капустная'],
    ['Растения', 'Покрытосеменные', 'Двудольные', None, 'Паслёновые', 'Паслён', 'Паслён клубненосный (картофель)'],
    ['Растения', 'Покрытосеменные', 'Двудольные', None, 'Бобовые', 'Горох', 'Горох посевной'],
    ['Растения', 'Покрытосеменные', 'Двудольные', None, 'Крестоцветные', 'Капуста', 'Капуста огородная'],
    ['Растения', 'Покрытосеменные', 'Двудольные', None, 'Розоцветные', 'Шиповник', 'Шиповник майский'],
    ['Растения', 'Покрытосеменные', 'Двудольные', None, 'Сложноцветные', 'Ромашка', 'Ромашка аптечная'],
    ['Растения', 'Покрытосеменные', 'Однодольные', None, 'Злаки', 'Пшеница', 'Пшеница мягкая'],
    ['Растения', 'Голосеменные', 'Хвойные', None, 'Сосновые', 'Сосна', 'Сосна обыкновенная'],
    ['Растения', 'Голосеменные', 'Хвойные', None, 'Сосновые', 'Ель', 'Ель европейская'],
]
RANKS_A = ['царство', 'тип', 'класс', 'отряд', 'семейство', 'род', 'вид']
RANKS_P = ['царство', 'отдел', 'класс', 'порядок', 'семейство', 'род', 'вид']


def gen_b_taxa(rng):
    """ЕГЭ 12 — 6 таксонов (часто с доменом Эукариоты, ранги можно не называть); ОГЭ 3 — 5 таксонов, ранг всегда указан."""
    row0 = rng.choice(TAXA)
    row = ['Эукариоты'] + row0
    ranks = ['домен'] + (RANKS_A if row0[0] == 'Животные' else RANKS_P)
    m = rng.choice([5, 6])
    avail = [i for i, x in enumerate(row) if x and (m == 6 or i > 0)]
    for _ in range(50):
        pick = sorted(rng.sample(avail, min(m, len(avail))))
        if m == 5 or 0 in pick or rng.random() < 0.3:
            break
    named = m == 5 or rng.random() < 0.5
    items = [(i, f'{ranks[i]} {row[i]}' if named and i > 0 else row[i]) for i in pick]
    shown = items[:]
    rng.shuffle(shown)
    top_down = rng.random() < 0.5
    order = sorted(shown, key=lambda x: x[0], reverse=not top_down)
    ans = ''.join(str(shown.index(x) + 1) for x in order)
    lst = '\n'.join(f'{j + 1}) {t}' for j, (_, t) in enumerate(shown))
    what = 'систематических групп' if m == 6 else 'систематических таксонов'
    start = ('наибольшего' if top_down else 'наименьшего') if m == 5 else ('самой крупной' if top_down else 'самой мелкой')
    q = (f'Расположите {"систематические группы" if m == 6 else "систематические таксоны"} по рангу, начиная с {start}.\n{lst}\n'
         'Запишите в таблицу соответствующую последовательность цифр.')
    e = 'Порядок рангов: ' + ' → '.join(ranks[i] for i in pick) + '.'
    return card('num', 'bio-ege-12' if m == 6 else 'bio-oge-3', q, ans, e,
                {'row': row[-1], 'k': row0[0], 'm': len(shown), 'shown': [i for i, _ in shown], 'top_down': top_down})


def check_b_taxa(c):
    idx = c['shown']
    order = sorted(range(len(idx)), key=lambda j: idx[j], reverse=not c['top_down'])
    return ''.join(str(j + 1) for j in order)


# ---- пищевые сети (ОГЭ био 19–21): кто кого ест — общеизвестные связи
WEBS = {
    'смешанный лес': {
        'дуб': [], 'трава': [], 'ель': [],
        'гусеница': ['дуб'], 'заяц': ['трава', 'дуб'], 'мышь': ['трава', 'ель'], 'белка': ['ель'],
        'синица': ['гусеница'], 'лисица': ['заяц', 'мышь'], 'сова': ['мышь', 'синица'],
        'куница': ['белка', 'синица'], 'ястреб': ['синица', 'белка'],
    },
    'пресный водоём': {
        'водоросли': [], 'ряска': [],
        'дафния': ['водоросли'], 'прудовик': ['водоросли', 'ряска'], 'личинка стрекозы': ['дафния'],
        'карась': ['дафния', 'прудовик'], 'лягушка': ['личинка стрекозы'], 'щука': ['карась', 'лягушка'],
        'цапля': ['лягушка', 'карась'],
    },
    'Южный океан': {
        'фитопланктон': [], 'криль': ['фитопланктон'], 'рыба': ['криль'], 'кальмар': ['рыба', 'криль'],
        'тюлень-крабоед': ['криль'], 'синий кит': ['криль'], 'императорский пингвин': ['рыба', 'кальмар'],
        'морской леопард': ['императорский пингвин', 'тюлень-крабоед'], 'косатка': ['морской леопард', 'тюлень-крабоед'],
    },
    'степь': {
        'злаки': [], 'полынь': [], 'саранча': ['злаки', 'полынь'], 'суслик': ['злаки'],
        'жаворонок': ['саранча'], 'ящерица': ['саранча'], 'степная гадюка': ['ящерица', 'суслик'],
        'степной орёл': ['суслик', 'степная гадюка'], 'корсак': ['суслик', 'жаворонок'],
    },
}


def web_chains(web, length):
    """Все цепи питания заданной длины, начиная с продуцента (поиск в ширину)."""
    eaters = {x: [y for y, food in web.items() if x in food] for x in web}
    chains = [[p] for p, food in web.items() if not food]
    for _ in range(length - 1):
        chains = [ch + [e] for ch in chains for e in eaters[ch[-1]]]
    return chains


def gen_b_foodweb(rng):
    name = rng.choice(list(WEBS))
    web = WEBS[name]
    mode = rng.choice(['chain', 'level', 'change'])
    letters = dict(zip(sorted(web, key=lambda _: rng.random()), 'АБВГДЕЖЗИКЛМН'))
    listing = '; '.join(f'{letters[x]} — {x}' for x in sorted(web, key=lambda x: letters[x]))
    links = '; '.join(f'{x} питается: {", ".join(f)}' for x, f in web.items() if f)
    if mode == 'chain':
        L = rng.choice([3, 4, 4])
        chains = web_chains(web, L)
        pool = Counter(x for ch in chains for x in ch[1:])
        cand = [x for x in pool if sum(x in ch for ch in chains) == 1]
        if not cand:
            return gen_b_foodweb(rng)
        x = rng.choice(cand)
        ch = next(c for c in chains if x in c)
        ans = ''.join(letters[o] for o in ch)
        q = (f'Экосистема «{name}». Организмы: {listing}. Связи: {links}. Составьте пищевую цепь из {L} организмов, '
             f'в которую входит {x}. Начните с продуцента, запишите буквы.')
        e = 'Цепь: ' + ' → '.join(ch) + '.'
        return card('flip', 'bio-oge-20', q, ans, e, {'web': name, 'mode': mode, 'x': x, 'L': L, 'ans': ch})
    if mode == 'level':
        chains = web_chains(web, rng.choice([3, 4]))
        if not chains:
            return gen_b_foodweb(rng)
        ch = rng.choice(chains)
        k = rng.randrange(len(ch))
        x = ch[k]
        levels = {len(c) and c.index(x) for c in web_chains(web, 3) + web_chains(web, 4) + web_chains(web, 5) if x in c}
        if len(levels) != 1:
            return gen_b_foodweb(rng)
        names = ['продуцент', 'консумент I порядка', 'консумент II порядка', 'консумент III порядка', 'консумент IV порядка']
        o, a = one(rng, names[k], [n for n in names if n != names[k]])
        q = f'Экосистема «{name}». Связи: {links}. Кем является {x} во всех пищевых цепях этой экосистемы?'
        return card('one', 'bio-oge-19', q, a, f'Цепь: {" → ".join(ch)}.', {'web': name, 'mode': mode, 'x': x, 'ok': names[k]}, o=o)
    # change: если численность X выросла, как изменится численность его пищи и его единственного врага
    eaters = {x: [y for y, food in web.items() if x in food] for x in web}
    cand = [x for x in web if web[x] and eaters[x] and all(len(eaters[f]) >= 1 for f in web[x])]
    if not cand:
        return gen_b_foodweb(rng)
    x = rng.choice(cand)
    food = rng.choice(web[x])
    pred = rng.choice(eaters[x])
    swap = rng.random() < 0.5
    A, B = (pred, food) if swap else (food, pred)
    ans = '12' if swap else '21'
    q = (f'Экосистема «{name}». Связи: {links}. Несколько лет росла численность организма «{x}». Как изменится '
         f'численность: А) {A}; Б) {B}? 1 — увеличится, 2 — уменьшится, 3 — не изменится. Запишите две цифры.')
    return card('num', 'bio-oge-21', q, ans, f'{x} сильнее выедает {food} (уменьшится), у {pred} больше корма (увеличится).',
                {'web': name, 'mode': mode, 'x': x, 'A': A, 'B': B})


def check_b_foodweb(c):
    web = WEBS[c['web']]
    if c['mode'] == 'chain':
        # поиск в глубину от хищника вниз к продуценту
        def down(path):
            last = path[-1]
            if not web[last]:
                yield path[::-1]
            for f in web[last]:
                yield from down(path + [f])
        found = [p for top in web for p in down([top]) if len(p) == c['L'] and c['x'] in p]
        found = [list(p) for p in {tuple(p) for p in found}]
        return len(found) == 1 and found[0] == c['ans']
    if c['mode'] == 'level':
        depth = {}
        def lvl(x):
            if x not in depth:
                depth[x] = {0} if not web[x] else {l + 1 for f in web[x] for l in lvl(f)}
            return depth[x]
        names = ['продуцент', 'консумент I порядка', 'консумент II порядка', 'консумент III порядка', 'консумент IV порядка']
        L = lvl(c['x'])
        return len(L) == 1 and names[L.pop()] == c['ok']
    # пища X убывает (2), хищник X растёт (1); каждую из двух позиций определяем по связям
    code = lambda y: '2' if y in web[c['x']] else '1' if c['x'] in web[y] else '3'
    return code(c['A']) + code(c['B'])


# ---- рацион (ОГЭ био 26): свои условные данные калорийности в тексте задачи
DISHES = {  # блюдо: ккал на порцию (условные учебные значения задаются в условии)
    'омлет': 250, 'каша овсяная': 180, 'бутерброд с сыром': 260, 'сырники': 320, 'йогурт': 120,
    'суп куриный': 150, 'борщ': 170, 'котлета с пюре': 420, 'плов': 520, 'гречка с курицей': 380,
    'салат овощной': 90, 'пицца (кусок)': 290, 'чай с сахаром': 60, 'компот': 90, 'сок апельсиновый': 110,
    'яблоко': 50, 'банан': 95, 'шоколадный батончик': 230, 'булочка': 280, 'макароны по-флотски': 450,
}


def gen_b_menu(rng):
    need = rng.choice([2200, 2400, 2500, 2600, 2800, 3000])
    share = rng.choice([(25, 'завтрак'), (35, 'обед'), (15, 'полдник'), (25, 'ужин')])
    dishes = rng.sample(list(DISHES), rng.randint(3, 4))
    total = sum(DISHES[d] for d in dishes)
    norm = need * share[0] // 100
    mode = rng.choice(['sum', 'diff'])
    table = '; '.join(f'{d} — {DISHES[d]} ккал' for d in dishes)
    if mode == 'sum':
        q = f'Подросток заказал на {share[1]}: {table}. Определите энергетическую ценность заказа (ккал). Ответ запишите в виде числа.'
        return card('num', 'bio-oge-26', q, str(total), f'{" + ".join(str(DISHES[d]) for d in dishes)} = {total} ккал.',
                    {'mode': mode, 'dishes': dishes})
    q = (f'Суточная потребность подростка — {need} ккал, на {share[1]} должно приходиться {share[0]} %. Он заказал: {table}. '
         f'На сколько ккал заказ отличается от нормы? Если заказ больше нормы — число положительное, меньше — отрицательное.')
    return card('num', 'bio-oge-26', q, str(total - norm), f'Норма {need} × {share[0]} % = {norm} ккал; заказ {total}; разница {total - norm}.',
                {'mode': mode, 'dishes': dishes, 'need': need, 'share': share[0]})


def check_b_menu(c):
    tot = 0
    for d in c['dishes']:
        tot += DISHES[d]
    if c['mode'] == 'sum':
        return str(tot)
    return str(tot - Fraction(c['need'] * c['share'], 100).__floor__())


# ================================================================ ГЕОГРАФИЯ

# Город: (субъект РФ, широта, долгота, UTC-смещение) — ФЗ № 107-ФЗ «Об исчислении времени»
CITIES = {
    'Калининград': ('Калининградская область', 54.7, 20.5, 2), 'Москва': ('Москва', 55.8, 37.6, 3),
    'Санкт-Петербург': ('Санкт-Петербург', 59.9, 30.3, 3), 'Мурманск': ('Мурманская область', 69.0, 33.1, 3),
    'Архангельск': ('Архангельская область', 64.5, 40.5, 3), 'Нижний Новгород': ('Нижегородская область', 56.3, 44.0, 3),
    'Казань': ('Республика Татарстан', 55.8, 49.1, 3), 'Волгоград': ('Волгоградская область', 48.7, 44.5, 3),
    'Ростов-на-Дону': ('Ростовская область', 47.2, 39.7, 3), 'Краснодар': ('Краснодарский край', 45.0, 39.0, 3),
    'Самара': ('Самарская область', 53.2, 50.1, 4), 'Ижевск': ('Удмуртская Республика', 56.9, 53.2, 4),
    'Астрахань': ('Астраханская область', 46.4, 48.0, 4), 'Саратов': ('Саратовская область', 51.5, 46.0, 4),
    'Ульяновск': ('Ульяновская область', 54.3, 48.4, 4), 'Екатеринбург': ('Свердловская область', 56.8, 60.6, 5),
    'Челябинск': ('Челябинская область', 55.2, 61.4, 5), 'Пермь': ('Пермский край', 58.0, 56.2, 5),
    'Уфа': ('Республика Башкортостан', 54.7, 56.0, 5), 'Тюмень': ('Тюменская область', 57.2, 65.5, 5),
    'Оренбург': ('Оренбургская область', 51.8, 55.1, 5), 'Салехард': ('Ямало-Ненецкий АО', 66.5, 66.6, 5),
    'Омск': ('Омская область', 55.0, 73.4, 6), 'Новосибирск': ('Новосибирская область', 55.0, 82.9, 7),
    'Барнаул': ('Алтайский край', 53.4, 83.8, 7), 'Томск': ('Томская область', 56.5, 85.0, 7),
    'Красноярск': ('Красноярский край', 56.0, 92.9, 7), 'Кемерово': ('Кемеровская область — Кузбасс', 55.4, 86.1, 7),
    'Абакан': ('Республика Хакасия', 53.7, 91.4, 7), 'Кызыл': ('Республика Тыва', 51.7, 94.5, 7),
    'Иркутск': ('Иркутская область', 52.3, 104.3, 8), 'Улан-Удэ': ('Республика Бурятия', 51.8, 107.6, 8),
    'Чита': ('Забайкальский край', 52.0, 113.5, 9), 'Якутск': ('Республика Саха (Якутия)', 62.0, 129.7, 9),
    'Благовещенск': ('Амурская область', 50.3, 127.5, 9), 'Хабаровск': ('Хабаровский край', 48.5, 135.1, 10),
    'Владивосток': ('Приморский край', 43.1, 131.9, 10), 'Магадан': ('Магаданская область', 59.6, 150.8, 11),
    'Южно-Сахалинск': ('Сахалинская область', 47.0, 142.7, 11),
    'Петропавловск-Камчатский': ('Камчатский край', 53.0, 158.7, 12), 'Анадырь': ('Чукотский АО', 64.7, 177.5, 12),
}


TIME_EVENTS = ['трансляция финального матча', 'онлайн-урок', 'прямой эфир концерта', 'старт всероссийской олимпиады',
               'видеоконференция', 'запуск космического корабля', 'вебинар', 'телемост']
MULTIZONE = {'Республика Саха (Якутия)', 'Сахалинская область'}      # несколько часовых зон в субъекте


def gen_g_time(rng):
    """ЕГЭ 14: msk — из Москвы на восток (МСК+1…+9); west — в пункт с меньшим поясным временем (часто через полночь)."""
    mode = rng.choice(['msk', 'west'])
    if mode == 'msk':
        a = 'Москва'
        b = rng.choice([c for c in CITIES if 4 <= CITIES[c][3] <= 12 and CITIES[c][0] not in MULTIZONE])
    else:
        while True:
            a, b = rng.sample(list(CITIES), 2)
            if CITIES[b][3] < CITIES[a][3] and not {CITIES[a][0], CITIES[b][0]} & MULTIZONE and (b == 'Калининград' or rng.random() < 0.8):
                break
    h, m = rng.randint(0, 23), rng.choice([0, 0, 15, 30, 45])
    ua, ub = CITIES[a][3], CITIES[b][3]
    if mode == 'west' and h >= ua - ub and rng.random() < 0.6:
        h = rng.randint(0, ua - ub - 1)                   # переход через полночь назад
    ans = (h + ub - ua) % 24
    ev = rng.choice(TIME_EVENTS)
    where = 'по московскому времени' if a == 'Москва' else f'по местному времени города {a}'
    q = (f'{cap(ev)} начался в {h} ч {m:02d} мин {where}. Который час по местному времени был в этот момент в городе {b} '
         f'({CITIES[b][0]})? Ответ запишите в виде числа (только часы).').replace('(Москва)', '')
    if ev.split()[0] in ('трансляция', 'видеоконференция'):
        q = q.replace('начался', 'началась', 1)
    e = (f'{a}: МСК{ua - 3:+d}, {b}: МСК{ub - 3:+d}. Разница {ub - ua:+d} ч: '
         f'{h} {"+" if ub >= ua else "−"} {abs(ub - ua)} = {ans} ч{" (предыдущие сутки)" if h + ub - ua < 0 else ""}.').replace('МСК+0', 'МСК')
    return card('num', 'geo-ege-14', q, str(ans), e, {'a': a, 'b': b, 'h': h, 'mode': mode})


def check_g_time(c):
    ua, ub = CITIES[c['a']][3], CITIES[c['b']][3]
    t = dt.datetime(2026, 5, 12, c['h'], 0, tzinfo=dt.timezone(dt.timedelta(hours=ua)))
    return str(t.astimezone(dt.timezone(dt.timedelta(hours=ub))).hour)


def gen_g_newyear(rng):
    while True:
        cs = rng.sample([c for c in CITIES if CITIES[c][0] not in MULTIZONE and c not in ('Москва', 'Санкт-Петербург')], 3)
        if len({CITIES[c][3] for c in cs}) == 3:
            break
    regs = [CITIES[c][0] for c in cs]
    order = sorted(range(3), key=lambda i: -CITIES[cs[i]][3])
    ans = ''.join(str(i + 1) for i in order)
    ev = rng.choice(['Новый год', 'полдень (12 ч по местному времени)', 'начало рабочего дня (9 ч по местному времени)'])
    q = (f'Расположите регионы России по порядку наступления события «{ev}» — первым укажите регион, '
         'где это происходит раньше всего: ' + '; '.join(f'{i + 1}) {r}' for i, r in enumerate(regs))
         + '. Запишите в таблицу получившуюся последовательность цифр.')
    e = 'Раньше встречают там, где больше смещение от UTC: ' + ', '.join(f'{r} — МСК{CITIES[c][3] - 3:+d}' for r, c in zip(regs, cs)) + '.'
    return card('num', 'geo-oge-26', q, ans, e, {'cs': cs})


def check_g_newyear(c):
    moments = []
    for i, city in enumerate(c['cs']):
        tz = dt.timezone(dt.timedelta(hours=CITIES[city][3]))
        moments.append((dt.datetime(2027, 1, 1, tzinfo=tz).astimezone(dt.timezone.utc), i))
    return ''.join(str(i + 1) for _, i in sorted(moments))


def fhm(m):
    return f'{m // 60} ч {m % 60:02d} мин'


def gen_g_sollon(rng):
    """ЕГЭ 28: lon — долгота пункта по разнице солнечного времени; time — солнечное время на другом меридиане."""
    mode = rng.choice(['lon', 'time'])
    if mode == 'lon':
        ref = rng.choice([0, 0, 15, 30, 45, 60, 90, 120])         # опорный меридиан, в.д.
        lon = rng.choice([x for x in range(-175, 176, 5) if x != ref and abs(x - ref) <= 150])
        t0 = rng.randint(6, 18) * 60 + rng.choice([0, 20, 40])
        tl = (t0 + 4 * (lon - ref)) % 1440
        L = lambda x: 'нулевом меридиане' if x == 0 else f'меридиане {abs(x)}° {"в.д." if x > 0 else "з.д."}'
        q = (f'Определите географическую долготу пункта, если известно, что в полдень по солнечному времени пункта '
             f'на {L(ref)} в этот момент {fhm((720 - 4 * (lon - ref)) % 1440)} (солнечное время). Пункт находится в том же полушарии '
             'относительно 180-го меридиана, что и опорный меридиан (линию перемены дат не пересекаем). Запишите решение.')
        ok = f'{abs(lon)}° {"в.д." if lon > 0 else "з.д."}' if lon else '0°'
        e = (f'Разница солнечного времени {fhm(abs(4 * (lon - ref)))} = {abs(lon - ref)}° (1° = 4 мин). '
             f'В пункте полдень наступил {"раньше" if lon > ref else "позже"} — он {"восточнее" if lon > ref else "западнее"} опорного меридиана: {ok}.')
        c = card('flip', 'geo-ege-28', q, ok, e, {'mode': mode, 'ref': ref, 'lon': lon, 'ok': ok})
        c['x'] = ok
        return c
    ref = rng.choice([x for x in range(-150, 151, 15)])
    lon = rng.choice([x for x in range(-175, 176, 5) if x != ref])
    t0 = rng.randint(0, 23) * 60 + rng.choice([0, 0, 30])
    tl = t0 + 4 * (lon - ref)
    L = lambda x: 'нулевом меридиане' if x == 0 else f'меридиане {abs(x)}° {"в.д." if x > 0 else "з.д."}'
    q = (f'На {L(ref)} солнечное время {fhm(t0)}. Определите, какое солнечное время в этот момент на {L(lon)}. '
         'Ответ запишите в формате «ч мин» и укажите, те же ли это сутки.')
    day = '' if 0 <= tl < 1440 else (' (следующие сутки)' if tl >= 1440 else ' (предыдущие сутки)')
    ans = fhm(tl % 1440) + day
    e = f'Разность долгот {abs(lon - ref)}° × 4 мин = {fhm(abs(4 * (lon - ref)))}; к востоку время больше, к западу — меньше: {ans}.'
    c = card('flip', 'geo-ege-28', q, ans, e, {'mode': mode, 'ref': ref, 'lon': lon, 't0': t0, 'ok': ans})
    c['x'] = ans
    return c


def check_g_sollon(c):
    if c['mode'] == 'lon':
        noon_ref = (720 - 4 * (c['lon'] - c['ref'])) % 1440           # время на опорном меридиане в полдень пункта
        d = 720 - noon_ref                                             # насколько пункт «впереди» опорного
        if d > 720:
            d -= 1440
        if d < -720:
            d += 1440
        lon = c['ref'] + d // 4
        ok = f'{abs(lon)}° {"в.д." if lon > 0 else "з.д."}' if lon else '0°'
        return ok == c['ok']
    tl = c['t0'] + 4 * (c['lon'] - c['ref'])
    day = '' if 0 <= tl < 1440 else (' (следующие сутки)' if tl >= 1440 else ' (предыдущие сутки)')
    return fhm(tl % 1440) + day == c['ok']


def gen_g_meridian(rng):
    """ЕГЭ 28: судно и порт на одном меридиане; cross — по разные стороны экватора, same — в одном полушарии."""
    mode = rng.choice(['same', 'cross'])
    lon = rng.randint(1, 179)
    hemi = rng.choice(['в.д.', 'з.д.'])
    while True:
        p1, p2 = rng.randint(1, 70), rng.randint(1, 70)
        if mode == 'cross':
            s1, s2 = rng.sample(['с.ш.', 'ю.ш.'], 2)
        else:
            s1 = s2 = rng.choice(['с.ш.', 'ю.ш.'])
        if p1 != p2 or mode == 'cross':
            break
    lat1 = p1 if s1 == 'с.ш.' else -p1
    lat2 = p2 if s2 == 'с.ш.' else -p2
    d = abs(lat1 - lat2)
    ans = d * 111
    q = (f'Судно находится в точке с координатами {p1}° {s1} {lon}° {hemi}, порт назначения — в точке {p2}° {s2} {lon}° {hemi}. '
         'Определите расстояние (км) между ними по меридиану. Длину дуги 1° меридиана примите равной 111 км. Запишите решение.')
    how = (f'точки по разные стороны от экватора — широты складываются: {p1} + {p2}' if s1 != s2
           else f'точки в одном полушарии — из большей широты вычитаем меньшую: {max(p1, p2)} − {min(p1, p2)}')
    e = f'Точки на одном меридиане; {how} = {d}°; {d} × 111 = {ans} км.'
    c = card('num', 'geo-ege-28', q, str(ans), e, {'lat1': lat1, 'lat2': lat2, 'mode': mode}, core={'d': d, 'mode': mode})
    return c


def check_g_meridian(c):
    arc_deg = abs(c['lat1'] - c['lat2'])
    return str(round(arc_deg / 360 * 360 * 111))


def gen_g_scale(rng):
    """ОГЭ 9: расстояние на местности по карте масштаба 1:N, ответ в метрах с округлением до десятков."""
    scale = rng.choice([5000, 10000, 10000, 20000, 25000])
    for _ in range(30):                # чаще — с округлением (некратно 10 м)
        mm = rng.randint(8, 90)
        m = Fraction(mm, 1000) * scale
        if m >= 100 and m % 10:
            break
    ans = fmt(half_up(m / 10, 0) * 10)
    a_, b_ = rng.choice([('родника', 'школы'), ('моста', 'церкви'), ('колодца', 'дома лесника'), ('пристани', 'маяка'),
                         ('отдельно стоящего дерева', 'родника'), ('часовни', 'моста через реку')])
    q = (f'Расстояние на карте масштаба 1:{sp(scale)} от {a_} до {b_} по прямой составляет {fmt(Fraction(mm, 10))} см. '
         'Определите расстояние на местности между этими объектами. Измерение проводите между центрами условных знаков. '
         'Полученный результат округлите до десятков метров. Ответ запишите цифрами (м).')
    e = f'В 1 см {fmt(Fraction(scale, 100))} м: {fmt(Fraction(mm, 10))} × {fmt(Fraction(scale, 100))} = {fmt(m)} м ≈ {ans} м.'
    return card('num', 'geo-oge-9', q, ans, e, {'mode': 'dist', 'scale': scale, 'mm': mm})


def check_g_scale(c):
    m = Fraction(c['mm'], 1000) * c['scale']
    return fmt(half_up(m, -1))


DIRS = ['север', 'северо-восток', 'восток', 'юго-восток', 'юг', 'юго-запад', 'запад', 'северо-запад']


def gen_g_azimuth(rng):
    mode = rng.choice(['dir', 'az', 'back'])
    k = rng.randrange(8)
    if mode == 'dir':
        az = k * 45 + rng.randint(-20, 20)
        az %= 360
        q = f'Азимут от родника на школу {az}°. В каком направлении от родника находится школа?'
        o, a = one(rng, DIRS[k], [DIRS[(k + 4) % 8], DIRS[(k + 2) % 8], DIRS[(k - 2) % 8], DIRS[(k + 1) % 8]])
        e = 'Азимут отсчитывают от направления на север по часовой стрелке: 0° — С, 90° — В, 180° — Ю, 270° — З.'
        return card('one', 'geo-oge-10', q, a, e, {'mode': mode, 'az': az, 'ok': DIRS[k]}, o=o)
    if mode == 'az':
        q = f'Турист идёт строго на {DIRS[k].replace("север", "север").replace("юг", "юг")}. Каков азимут его движения (°)? Ответ запишите в виде числа.'
        return card('num', 'geo-oge-10', q, str(k * 45), 'Азимут: С 0°, СВ 45°, В 90°, ЮВ 135°, Ю 180°, ЮЗ 225°, З 270°, СЗ 315°.',
                    {'mode': mode, 'k': k})
    az = rng.randrange(0, 360, 5)
    q = f'Азимут от точки А на точку Б {az}°. Каков обратный азимут — от Б на А (°)? Ответ запишите в виде числа.'
    return card('num', 'geo-oge-10', q, str((az + 180) % 360), f'Обратный азимут отличается на 180°: {az} ± 180 = {(az + 180) % 360}°.',
                {'mode': mode, 'az': az})


def check_g_azimuth(c):
    import math
    if c['mode'] == 'dir':
        x, y = math.sin(math.radians(c['az'])), math.cos(math.radians(c['az']))
        ang = math.degrees(math.atan2(x, y)) % 360
        return DIRS[int((ang + 22.5) // 45) % 8] == c['ok']
    if c['mode'] == 'az':
        return str(c['k'] * 45)
    x, y = -math.sin(math.radians(c['az'])), -math.cos(math.radians(c['az']))
    return str(round(math.degrees(math.atan2(x, y)) % 360) % 360)


def gen_g_altitude(rng):
    """ОГЭ 13: temp/temp_up (температура с высотой), press/height (давление с высотой); ЕГЭ 2: slope_t (три станции на склоне)."""
    mode = rng.choice(['temp', 'temp_up', 'press', 'height', 'slope_t'])
    if mode == 'temp':
        h = rng.choice(range(500, 5001, 500))
        t0 = rng.randint(10, 30)
        ans = fmt(t0 - Fraction(6, 1000) * h, 1)
        q = (f'Определите, какая температура воздуха будет на вершине горы высотой {h} м, если у её подножия (на уровне моря) '
             f'температура составляет +{t0} °С и известно, что температура понижается на 0,6 °С на каждые 100 м. '
             'Ответ запишите в виде числа.')
        e = f'{h} / 100 × 0,6 = {fmt(Fraction(6, 1000) * h)} °С; {t0} − {fmt(Fraction(6, 1000) * h)} = {ans} °С.'
        chk = {'mode': mode, 'h': h, 't0': t0}
    elif mode == 'temp_up':
        h = rng.choice(range(500, 5001, 500))
        t1 = rng.randint(-15, 8)
        ans = fmt(t1 + Fraction(6, 1000) * h, 1)
        q = (f'На вершине горы высотой {h} м температура воздуха {t1:+d} °С. Определите температуру воздуха у подножия горы '
             '(на уровне моря), если известно, что температура понижается на 0,6 °С на каждые 100 м. Ответ запишите в виде числа.')
        e = f'{t1} + {h} / 100 × 0,6 = {ans} °С.'
        chk = {'mode': mode, 'h': h, 't1': t1}
    elif mode == 'press':
        h = rng.choice(range(200, 3001, 100))
        p0 = rng.choice([750, 755, 760, 760, 760, 765])
        ans = str(p0 - h // 10)
        q = (f'Определите, какое атмосферное давление будет на вершине горы высотой {h} м, если у её подножия оно составляет '
             f'{p0} мм рт. ст. и известно, что давление понижается на 1 мм рт. ст. на каждые 10 м подъёма. Ответ запишите в виде числа.')
        e = f'{h} / 10 = {h // 10} мм; {p0} − {h // 10} = {ans}.'
        chk = {'mode': mode, 'h': h, 'p0': p0}
    elif mode == 'height':
        p0 = rng.choice([750, 755, 760, 765])
        dp = rng.randint(12, 150)
        ans = str(dp * 10)
        q = (f'У подножия горы атмосферное давление {p0} мм рт. ст., на вершине — {p0 - dp} мм рт. ст. Определите относительную '
             'высоту горы (м), если давление понижается на 1 мм рт. ст. на каждые 10 м подъёма. Ответ запишите в виде числа.')
        e = f'{p0} − {p0 - dp} = {dp} мм; {dp} × 10 = {ans} м.'
        chk = {'mode': mode, 'p0': p0, 'dp': dp}
    else:
        while True:
            ts = rng.sample(range(-12, 15), 3)
            if min(ts) < 0 < max(ts) and min(abs(x - y) for x, y in itertools.combinations(ts, 2)) >= 2:
                break
        q = ('Три метеостанции стоят на одном горном склоне на разной высоте. В один и тот же момент на них записали температуру воздуха: ' + '; '.join(f'метеостанция {i + 1} — {t:+d} °С'.replace('+0', '0') for i, t in enumerate(ts))
             + '. Расположите метеостанции по возрастанию высоты, на которой они находятся, — от самой низкой к самой высокой. '
             'Запишите в таблицу получившуюся последовательность цифр.')
        ans = ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: -ts[i]))
        return card('num', 'geo-ege-2', q, ans, 'В тропосфере температура с высотой понижается: чем выше станция, тем холоднее.',
                    {'mode': mode, 'ts': ts})
    return card('num', 'geo-oge-13', q, ans, e, chk)


def check_g_altitude(c):
    m = c['mode']
    if m == 'temp':
        t = Fraction(c['t0'])
        for _ in range(c['h'] // 50):
            t -= Fraction(3, 10)
        return fmt(t, 1)
    if m == 'temp_up':
        return fmt(Fraction(c['t1']) + Fraction(6, 1000) * c['h'], 1)
    if m == 'press':
        p = c['p0']
        for _ in range(c['h'] // 10):
            p -= 1
        return str(p)
    if m == 'slope_t':
        h = [-(t - 20) / Fraction(6, 1000) for t in c['ts']]     # высота из градиента 0,6 °С/100 м
        return ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: h[i]))
    return str(c['dp'] * 10)


# максимальное содержание водяного пара (г/м³) при температуре — справочная таблица школьного атласа
SAT = {-20: Fraction('0.9'), -10: Fraction('2.3'), 0: Fraction('4.8'), 10: Fraction('9.4'), 20: Fraction('17.3'), 30: Fraction('30.4')}


def gen_g_humidity(rng):
    """ОГЭ 13: rh (расчёт относительной влажности); ЕГЭ 2: rh_order, temp_order, press (упорядочить метеостанции)."""
    mode = rng.choice(['rh', 'rh_order', 'temp_order', 'press'])
    if mode == 'rh':
        t = rng.choice([-10, 0, 10, 20, 30])
        for _ in range(100):
            a = Fraction(rng.randint(3, int(SAT[t] * 10) - 2), 10)
            phi = 100 * a / SAT[t]
            if phi % 10 and 15 < phi < 98:
                break
        ans = fmt(half_up(phi, 0))
        q = (f'Температура воздуха {t:+d} °С, содержание водяного пара в нём {fmt(a)} г/м³. Какова относительная влажность воздуха, '
             f'если при такой температуре максимально возможное содержание водяного пара составляет {fmt(SAT[t])} г/м³? '
             'Полученный результат округлите до целого числа.').replace('+0 °С', '0 °С')
        e = f'{fmt(a)} / {fmt(SAT[t])} × 100 % ≈ {ans} %.'
        return card('num', 'geo-oge-13', q, ans, e, {'mode': mode, 't': t, 'a': str(a)})
    if mode == 'rh_order':
        for _ in range(200):
            ts = rng.sample([-10, 0, 10, 20, 30], 3)
            aa = [Fraction(rng.randint(3, int(SAT[t] * 9)), 10) for t in ts]
            rh = [a / SAT[t] for a, t in zip(aa, ts)]
            if min(abs(x - y) for x, y in itertools.combinations(rh, 2)) > Fraction(5, 100):
                break
        rows = '; '.join(f'Метеостанция {i + 1}: температура {t:+d} °С, содержание водяного пара {fmt(a)} г/м³'.replace('+0 °С', '0 °С')
                         for i, (t, a) in enumerate(zip(ts, aa)))
        sat = ', '.join(f'{t:+d} °С — {fmt(SAT[t])} г/м³'.replace('+0 °С', '0 °С') for t in sorted(ts))
        q = (f'На трёх метеостанциях одновременно измерили температуру воздуха и содержание в нём водяного пара. {rows}. '
             f'Максимально возможное содержание водяного пара: {sat}. Расположите метеостанции в порядке повышения '
             'относительной влажности воздуха (от наименьшей к наибольшей). Запишите в таблицу получившуюся последовательность цифр.')
        ans = ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: rh[i]))
        e = 'Относительная влажность: ' + ', '.join(f'{i + 1}) {fmt(100 * r, 0)} %' for i, r in enumerate(rh)) + '.'
        return card('num', 'geo-ege-2', q, ans, e, {'mode': mode, 'ts': ts, 'aa': [str(a) for a in aa]})
    if mode == 'temp_order':
        phi = rng.choice([55, 60, 65, 70, 75, 80, 85, 90])
        ts = rng.sample([-10, 0, 10, 20, 30], 3)
        aa = [half_up(SAT[t] * phi / 100, 1) for t in ts]
        q = ('На трёх метеостанциях одновременно измерили содержание водяного пара в воздухе: '
             + '; '.join(f'метеостанция {i + 1} — {fmt(a)} г/м³' for i, a in enumerate(aa))
             + f'. Относительная влажность воздуха на всех станциях одинакова и составляет {phi} %. Расположите метеостанции '
             'в порядке повышения температуры воздуха на них. Запишите в таблицу получившуюся последовательность цифр.')
        ans = ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: ts[i]))
        e = 'При одинаковой относительной влажности пара больше там, где теплее: ' + ', '.join(f'{i + 1}) {t:+d} °С' for i, t in enumerate(ts)) + '.'
        return card('num', 'geo-ege-2', q, ans, e, {'mode': mode, 'aa': [str(a) for a in aa], 'phi': phi})
    while True:
        ps = rng.sample(range(600, 761), 3)
        if min(abs(x - y) for x, y in itertools.combinations(ps, 2)) >= 8:
            break
    q = ('Три метеостанции стоят на одном горном склоне на разной высоте. В один и тот же момент на них записали атмосферное давление: '
         + '; '.join(f'метеостанция {i + 1} — {p} мм рт. ст.' for i, p in enumerate(ps))
         + '. Расположите метеостанции по возрастанию высоты, на которой они находятся, — от самой низкой к самой высокой. '
         'Запишите в таблицу получившуюся последовательность цифр.').replace('ст..', 'ст.')
    ans = ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: -ps[i]))
    return card('num', 'geo-ege-2', q, ans, 'С высотой давление понижается: выше станция — ниже давление.', {'mode': mode, 'ps': ps})


def check_g_humidity(c):
    m = c['mode']
    if m == 'rh':
        return fmt(half_up(100 * Fraction(c['a']) / SAT[c['t']], 0))
    if m == 'rh_order':
        rh = [Fraction(a) / SAT[t] for a, t in zip(c['aa'], c['ts'])]
        return ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: rh[i]))
    if m == 'temp_order':
        sat = [Fraction(a) * 100 / c['phi'] for a in c['aa']]     # насыщающее содержание растёт с температурой
        return ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: sat[i]))
    import math
    h = [18400 * math.log10(760 / p) for p in c['ps']]   # барометрическая формула: высота растёт при падении P
    return ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: h[i]))


# запасы и добыча (порядок величин — по открытым отраслевым обзорам 2020-х; в задаче значения слегка варьируются)
RESOURCES = {
    'нефти': ('млрд т', 'млн т', {'Саудовская Аравия': (40.9, 520), 'Россия': (14.8, 540), 'Канада': (27.1, 270),
                                   'Венесуэла': (48.0, 40), 'Ирак': (19.6, 210), 'Иран': (21.7, 170), 'ОАЭ': (13.0, 180),
                                   'Кувейт': (14.0, 140), 'США': (8.2, 750), 'Казахстан': (3.9, 90), 'Норвегия': (1.1, 90),
                                   'Бразилия': (1.7, 170), 'Нигерия': (5.0, 80), 'Ливия': (6.3, 60)}),
    'природного газа': ('трлн м³', 'млрд м³', {'Россия': (37.4, 690), 'Иран': (32.1, 250), 'Катар': (23.8, 175),
                                             'Туркменистан': (13.6, 80), 'США': (12.6, 1000), 'Саудовская Аравия': (6.0, 115),
                                             'Норвегия': (1.4, 120), 'Алжир': (2.3, 100), 'Австралия': (2.4, 150), 'Китай': (8.4, 220)}),
    'угля': ('млрд т', 'млн т', {'Китай': (143, 4500), 'США': (249, 540), 'Индия': (111, 900), 'Австралия': (150, 450),
                                 'Россия': (162, 440), 'Индонезия': (35, 690), 'ЮАР': (10, 230), 'Казахстан': (25, 110),
                                 'Польша': (28, 100), 'Колумбия': (4.5, 60)}),
}
ARABLE = {'Россия': (146, 123), 'Канада': (39, 38), 'Индия': (1430, 155), 'Китай': (1410, 119), 'США': (335, 158),
          'Австралия': (27, 31), 'Казахстан': (20, 30), 'Бразилия': (216, 63), 'Египет': (112, 3.3), 'Япония': (124, 4.1),
          'Украина': (37, 32), 'Аргентина': (46, 33), 'Германия': (84, 11.7), 'Франция': (68, 18)}      # млн чел., млн га пашни
SEAS = {'Балтийского моря': 7, 'Чёрного моря': 18, 'Азовского моря': 11, 'Белого моря': 26, 'Средиземного моря': 38,
        'Красного моря': 41, 'Баренцева моря': 34, 'Японского моря': 34, 'Карибского моря': 36}


RES_ABLT = {'нефти': 'нефтью', 'природного газа': 'природным газом', 'угля': 'углём'}


def of_country(name):
    """«Саудовской Аравии»; несклоняемые — «страны США»."""
    g = inflect(name, 'gent')
    return g if g != name else f'страны {name}'


def years_word(n):
    n = abs(int(n))
    return 'год' if n % 10 == 1 and n % 100 != 11 else ('года' if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else 'лет')


def jitter(rng, v, pct=8, nd=1):
    return half_up(Fraction(str(v)) * (100 + rng.randint(-pct, pct)) / 100, nd)


# субъекты с естественным приростом населения в 2022–2024 гг. (по данным Росстата); в остальных — убыль
NAT_GROWTH = {'Чечня', 'Чеченская Республика', 'Ингушетия', 'Республика Ингушетия', 'Дагестан', 'Республика Дагестан',
              'Тыва', 'Республика Тыва', 'Ямало-Ненецкий автономный округ', 'Ханты-Мансийский автономный округ — Югра',
              'Ханты-Мансийский автономный округ', 'Тюменская область', 'Якутия', 'Республика Саха (Якутия)'}


def subj(rng, big=False):
    S = FACTS['geo']['ru_subjects']
    name = rng.choice([k for k, v in S.items() if v.get('pop') and v.get('area') and k not in FED_CITIES
                       and (not big or v['pop'] > 800000)])
    return name, S[name]


def demo_rows(rng, years=2):
    """Реальный субъект: численность на 1 января, естественный и миграционный прирост с реалистичными коэффициентами."""
    name, v = subj(rng, True)
    p = [v['pop'] + rng.randint(-3000, 3000)]
    nats, migs = [], []
    pos = name in NAT_GROWTH
    for _ in range(years):
        if pos:                            # регионы с естественным приростом (Росстат, 2022–2024)
            br, dr = Fraction(rng.randint(120, 190), 10), Fraction(rng.randint(40, 80), 10)
        else:                              # остальные — естественная убыль
            br, dr = Fraction(rng.randint(65, 95), 10), Fraction(rng.randint(115, 165), 10)
        nat = int((br - dr) * p[-1] / 1000) + rng.randint(-50, 50)
        mig = int(p[-1] * Fraction(rng.randint(-80, 80), 10000)) + rng.randint(-50, 50)
        nats.append(nat)
        migs.append(mig)
        p.append(p[-1] + nat + mig)
    return name, p, nats, migs


def gen_g_demo(rng):
    mode = rng.choice(['density', 'natural', 'migr', 'urban', 'supply', 'reserves', 'birth', 'salinity', 'nat_abs'])
    Y = rng.choice([2022, 2023, 2024])
    if mode == 'density':
        name, v = subj(rng)
        pop, area = v['pop'], v['area']
        ans = fmt(half_up(Fraction(pop, area), 1), 1)
        q = (f'Численность населения субъекта РФ «{name}» на 1 января 2025 г. составляла {sp(pop)} человек, площадь территории — '
             f'{sp(area)} км². Определите среднюю плотность населения (чел./км²). Полученный результат округлите до десятых.')
        e = f'{sp(pop)} : {sp(area)} ≈ {ans} чел./км².'
        chk = {'mode': mode, 'pop': pop, 'area': area}
    elif mode in ('natural', 'migr', 'nat_abs'):
        name, p, nats, migs = demo_rows(rng, 1)
        tab = (f'Используя эти данные, ', f'Численность населения субъекта РФ «{name}»: на 1 января {Y} г. — {sp(p[0])} чел., '
               f'на 1 января {Y + 1} г. — {sp(p[1])} чел.')
        if mode == 'natural':
            avg = Fraction(p[0] + p[1], 2)
            ans = fmt(half_up(nats[0] * 1000 / avg, 1), 1)
            q = (f'{tab[1]} Естественный прирост населения за {Y} г. составил {sp(nats[0])} чел. {tab[0]}определите величину '
                 f'естественного прироста населения (в ‰) в {Y} г. При расчётах используйте показатель среднегодовой численности '
                 'населения. Полученный результат округлите до десятых.')
            e = f'Среднегодовая численность ({sp(p[0])} + {sp(p[1])}) : 2 = {fmt(avg, 1)}; {nats[0]} : {fmt(avg, 1)} × 1000 ≈ {ans} ‰.'
            chk = {'mode': mode, 'p': p, 'nat': nats[0]}
        elif mode == 'migr':
            ans = str(migs[0])
            q = (f'{tab[1]} Естественный прирост населения за {Y} г. составил {sp(nats[0])} чел. {tab[0]}определите величину '
                 f'миграционного прироста (убыли) населения в {Y} г. (чел.). Убыль запишите со знаком «минус».')
            e = f'Общий прирост {p[1] - p[0]}; миграционный = общий − естественный = {p[1] - p[0]} − ({nats[0]}) = {ans}.'
            chk = {'mode': mode, 'p1': p[0], 'p2': p[1], 'nat': nats[0]}
        else:
            ans = str(nats[0])
            q = (f'{tab[1]} Миграционный прирост населения за {Y} г. составил {sp(migs[0])} чел. {tab[0]}определите величину '
                 f'естественного прироста (убыли) населения в {Y} г. (чел.). Убыль запишите со знаком «минус».')
            e = f'Общий прирост {p[1] - p[0]}; естественный = общий − миграционный = {p[1] - p[0]} − ({migs[0]}) = {ans}.'
            chk = {'mode': mode, 'p1': p[0], 'p2': p[1], 'mig': migs[0]}
    elif mode == 'urban':
        C = FACTS['geo']['countries']
        iso = rng.choice([i for i in C if wbv(i, 'urban') and wbv(i, 'pop') and wbv(i, 'pop') > 2e6])
        tot = int(wbv(iso, 'pop'))
        urb = int(tot * Fraction(str(round(wbv(iso, 'urban'), 1))) / 100)
        ans = fmt(half_up(Fraction(urb * 100, tot), 0))
        q = (f'Численность населения {of_country(C[iso]["name"])} — {sp(tot)} человек, из них в городах проживает {sp(urb)} человек. '
             'Определите долю городского населения (%). Полученный результат округлите до целого числа.')
        e = f'{sp(urb)} : {sp(tot)} × 100 ≈ {ans} %.'
        chk = {'mode': mode, 'tot': tot, 'urb': urb}
    elif mode in ('supply', 'reserves'):
        res_name = rng.choice(list(RESOURCES))
        ru, pu, T = RESOURCES[res_name]
        rows = rng.sample(list(T), 3)
        vals = {c: (jitter(rng, T[c][0], 8, 1), jitter(rng, T[c][1], 8, 0)) for c in rows}
        ask = rng.choice(rows)
        R, P = vals[ask]
        k = 1000
        table = '; '.join(f'{c} — запасы {fmt(vals[c][0])} {ru}, добыча {fmt(vals[c][1])} {pu} в год' for c in rows)
        if mode == 'supply':
            ans = fmt(half_up(R * k / P, 0))
            q = (f'В таблице приведены данные о разведанных запасах и добыче {res_name} в {Y} г.: {table}. Используя данные таблицы, '
                 f'определите ресурсообеспеченность {of_country(ask)} {RES_ABLT[res_name]} (в годах). Полученный результат округлите до целого числа.')
            e = f'{fmt(R)} {ru} = {fmt(R * k)} {pu}; {fmt(R * k)} : {fmt(P)} ≈ {ans} лет.'
            chk = {'mode': mode, 'R': str(R), 'P': str(P)}
        else:
            yrs = int(half_up(R * k / P, 0))
            ans = fmt(half_up(P * yrs / k, 1), 1)
            q = (f'Годовая добыча {res_name} в {inflect(ask, "loct") if inflect(ask, "loct") != ask else "стране " + ask} в {Y} г. составила {fmt(P)} {pu}. '
                 f'Ресурсообеспеченность {of_country(ask)} {RES_ABLT[res_name]} при таком уровне добычи — {yrs} {years_word(yrs)}. Определите разведанные запасы {res_name} ({ru}). '
                 'Полученный результат округлите до десятых.')
            e = f'{fmt(P)} × {yrs} = {fmt(P * yrs)} {pu} = {ans} {ru}.'
            chk = {'mode': mode, 'P': str(P), 'yrs': yrs}
    elif mode == 'salinity':
        sea = rng.choice(list(SEAS))
        L = rng.choice([1, 2, 3, 4, 5])
        g = SEAS[sea] * L + rng.randint(-L, L)
        ans = fmt(half_up(Fraction(g, L), 0))
        q = (f'Учащиеся определили, что в {agree(L, "литр")} воды {sea} растворено {g} г солей. '
             'Определите солёность воды (‰). Полученный результат округлите до целого числа.').replace(' 1 литр ', ' 1 литре ')
        q = re.sub(r'в (\d+) литра? ', lambda m_: f'в {m_.group(1)} {"литре" if m_.group(1) == "1" else "литрах"} ', q)
        e = f'Солёность — граммы солей в 1 л (кг) воды: {g} : {L} ≈ {ans} ‰.'
        chk = {'mode': mode, 'g': g, 'L': L}
    else:
        C = FACTS['geo']['countries']
        iso = rng.choice([i for i in C if wbv(i, 'birth') and wbv(i, 'pop') and wbv(i, 'pop') > 2e6])
        pop = int(wbv(iso, 'pop'))
        b = int(Fraction(str(round(wbv(iso, 'birth'), 1))) * pop / 1000)
        ans = fmt(half_up(Fraction(b * 1000, pop), 1), 1)
        q = (f'Численность населения {of_country(C[iso]["name"])} — {sp(pop)} человек, за год родилось {sp(b)} детей. '
             'Определите коэффициент рождаемости (‰). Полученный результат округлите до десятых.')
        e = f'{sp(b)} : {sp(pop)} × 1000 ≈ {ans} ‰.'
        chk = {'mode': mode, 'pop': pop, 'b': b}
    topic = {'salinity': 'geo-oge-13', 'density': 'geo-oge-13', 'urban': 'geo-oge-13'}.get(mode, 'geo-ege-16')
    return card('num', topic, q, ans, e, chk)


def check_g_demo(c):
    m = c['mode']
    F = Fraction
    if m == 'density':
        return fmt(half_up(F(c['pop'], c['area']), 1), 1)
    if m == 'natural':
        return fmt(half_up(F(c['nat'] * 2000, c['p'][0] + c['p'][1]), 1), 1)
    if m == 'migr':
        return str((c['p2'] - c['p1']) - c['nat'])
    if m == 'nat_abs':
        return str((c['p2'] - c['p1']) - c['mig'])
    if m == 'urban':
        return fmt(half_up(F(c['urb'] * 100, c['tot']), 0))
    if m == 'supply':
        return fmt(half_up(F(c['R']) * 1000 / F(c['P']), 0))
    if m == 'reserves':
        return fmt(half_up(F(c['P']) * c['yrs'] / 1000, 1), 1)
    if m == 'salinity':
        return fmt(half_up(F(c['g'], c['L']), 0))
    return fmt(half_up(F(c['b'] * 1000, c['pop']), 1), 1)


def gen_g_sun(rng):
    lat = rng.randint(0, 66)
    hemi = rng.choice(['с.ш.', 'ю.ш.'])
    day = rng.choice(['21 марта', '23 сентября', '22 июня', '22 декабря'])
    decl = {'21 марта': 0, '23 сентября': 0, '22 июня': 23.5, '22 декабря': -23.5}[day]
    phi = lat if hemi == 'с.ш.' else -lat
    h = 90 - abs(phi - decl)
    ans = fmt(h, 1)
    q = (f'Определите высоту Солнца над горизонтом (°) в полдень {day} в пункте на широте {lat}° {hemi}. '
         'Ответ запишите в виде числа.')
    e = f'h = 90° − |φ − δ|, склонение Солнца {day} {fmt(decl)}°: 90 − |{phi} − ({fmt(decl)})| = {ans}°.'
    return card('num', 'geo-ege-27', q, ans, e, {'phi': phi, 'day': day})


def check_g_sun(c):
    import math
    decl = {'21 марта': 0, '23 сентября': 0, '22 июня': 23.5, '22 декабря': -23.5}[c['day']]
    # вектор на Солнце и зенит в полдень: угол между ними — зенитное расстояние
    z = math.degrees(math.acos(math.cos(math.radians(c['phi'] - decl))))
    return fmt(round(90 - z, 1), 1)


DATES = [('22 июня', 173), ('22 декабря', 356), ('22 ноября', 326), ('15 января', 15), ('1 мая', 121),
         ('20 июля', 201), ('10 февраля', 41), ('25 октября', 298), ('15 августа', 227), ('1 апреля', 91)]


def gen_g_daylen(rng):
    while True:
        cs = rng.sample(list(CITIES), 3)
        lats = [CITIES[c][1] for c in cs]
        if min(abs(a - b) for a, b in itertools.combinations(lats, 2)) >= 2:
            break
    day, doy = rng.choice(DATES)
    asc = rng.random() < 0.5
    sign = 1 if 80 < doy < 266 else -1            # между равноденствиями летом день длиннее севернее
    key = lambda i: sign * CITIES[cs[i]][1]
    order = sorted(range(3), key=key, reverse=not asc)
    ans = ''.join(str(i + 1) for i in order)
    q = (f'Дата — {day}. Упорядочьте города от {"самого короткого" if asc else "самого длинного"} светового дня '
         f'к {"самому длинному" if asc else "самому короткому"}: '
         + '; '.join(f'{i + 1}) {c}' for i, c in enumerate(cs)) + '. Запишите в таблицу получившуюся последовательность цифр.')
    e = ('Между весенним и осенним равноденствием в Северном полушарии день тем длиннее, чем севернее пункт; в остальное время — наоборот. Широты: '
         + ', '.join(f'{c} {fmt(CITIES[c][1])}°' for c in cs) + '.')
    return card('num', 'geo-ege-3', q, ans, e, {'cs': cs, 'day': day, 'doy': doy, 'asc': asc})


def check_g_daylen(c):
    import math
    decl = -23.44 * math.cos(math.radians(360 / 365 * (c['doy'] + 10)))   # склонение Солнца (приближение)

    def length(lat):
        x = -math.tan(math.radians(lat)) * math.tan(math.radians(decl))
        x = max(-1, min(1, x))
        return 2 * math.degrees(math.acos(x)) / 15

    L = [length(CITIES[x][1]) for x in c['cs']]
    return ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: L[i], reverse=not c['asc']))


# ---- горные системы по долготе (ЕГЭ гео 4): приблизительная долгота центра, Wikidata/атлас
MOUNTAINS = {
    'Евразии': {'Пиренеи': 0, 'Альпы': 10, 'Карпаты': 24, 'Большой Кавказ': 44, 'Уральские горы': 59, 'Памир': 73,
                'Тянь-Шань': 80, 'Алтай': 88, 'Восточный Саян': 98, 'Становой хребет': 125, 'Сихотэ-Алинь': 137,
                'Скандинавские горы': 15, 'Загрос': 48, 'Хибины': 34},
    'Северной Америки': {'Аппалачи': -79, 'Скалистые горы': -110, 'Сьерра-Невада': -119, 'Береговые хребты Аляски': -150},
    'Африки': {'Атлас': -3, 'Драконовы горы': 29, 'Эфиопское нагорье': 39, 'Ахаггар': 6},
}


def gen_g_lonorder(rng):
    cont = rng.choice(list(MOUNTAINS))
    m = MOUNTAINS[cont]
    while True:
        pick = rng.sample(list(m), 3)
        lons = sorted(m[x] for x in pick)
        if min(b - a for a, b in zip(lons, lons[1:])) >= 8:
            break
    east = rng.random() < 0.5
    order = sorted(range(3), key=lambda i: m[pick[i]], reverse=not east)
    ans = ''.join(str(i + 1) for i in order)
    q = (f'Расположите горные системы {cont} {"с запада на восток" if east else "с востока на запад"}: '
         + '; '.join(f'{i + 1}) {x}' for i, x in enumerate(pick)) + '. Запишите в таблицу получившуюся последовательность цифр.')
    return card('num', 'geo-ege-4', q, ans, 'Долготы центров: ' + ', '.join(f'{x} ≈ {abs(m[x])}° {"в.д." if m[x] >= 0 else "з.д."}' for x in pick) + '.',
                {'cont': cont, 'pick': pick, 'east': east})


def check_g_lonorder(c):
    import math
    m = MOUNTAINS[c['cont']]
    # проекция на ось запад-восток через синус угла от меридиана 180°: монотонна в (−180; 180)
    key = lambda i: math.sin(math.radians((m[c['pick'][i]] + 180) / 2 - 90))
    return ''.join(str(i + 1) for i in sorted(range(3), key=key, reverse=not c['east']))



MONTHS = 'я ф м а м и и а с о н д'.split()


def gen_g_climate(rng):
    kind = rng.choice(['cont', 'marine', 'south'])
    jan = {'cont': rng.randint(-40, -10), 'marine': rng.randint(-8, 8), 'south': rng.randint(18, 28)}[kind]
    jul = {'cont': rng.randint(12, 25), 'marine': rng.randint(12, 18), 'south': rng.randint(-5, 12)}[kind]
    mode = rng.choice(['amp', 'sum'])
    if mode == 'amp':
        ans = str(abs(jul - jan))
        q = (f'По климатограмме средняя температура января {jan:+d} °С, июля {jul:+d} °С; остальные месяцы между ними. '
             'Определите годовую амплитуду температур (°С). Ответ запишите в виде числа.')
        e = f'Амплитуда — разность самого тёплого и самого холодного месяцев: {max(jan, jul)} − ({min(jan, jul)}) = {ans} °С.'
        return card('num', 'geo-oge-18', q, ans, e, {'mode': mode, 'jan': jan, 'jul': jul})
    pr = [rng.randint(5, 150) for _ in range(12)]
    ans = str(sum(pr))
    q = ('Месячные суммы осадков (мм) по климатограмме: ' + ', '.join(f'{m} {p}' for m, p in zip(MONTHS, pr))
         + '. Определите годовое количество осадков (мм). Ответ запишите в виде числа.')
    return card('num', 'geo-oge-18', q, ans, 'Годовая сумма — сумма по всем 12 месяцам.', {'mode': mode, 'pr': pr})


def check_g_climate(c):
    if c['mode'] == 'amp':
        temps = [c['jan'], c['jul']]
        return str(max(temps) - min(temps))
    s = 0
    for p in c['pr']:
        s += p
    return str(s)


# ================================================================ ТАБЛИЦЫ ФАКТОВ И СЛОВАРНЫЕ ДВИЖКИ
#
# Словарные генераторы (dict) берут факты из data/source/bio-facts.json и data/source/geo-facts.json.
# Формат таблиц — см. раздел «Таблицы фактов» в docs/research/bio-geo-prototypes.md. Главное правило для
# sets — «закрытый мир»: свойство верно ровно для объектов из его списка yes, для остальных объектов
# набора — неверно. Поэтому неверные варианты ответа берутся из того же набора (свойства соседей).
#
# Движок вызывается строкой-спецификацией из поля gen прототипа: 'd_match:bio/organelles',
# 'd_class:bio/kingdoms,k=4,n=4,each', 'g_demo@mode=migr' (фильтр по полю chk) и т. п.

ROOT = Path(__file__).resolve().parents[2]


def _load(name):
    p = ROOT / 'data' / 'source' / name
    return json.loads(p.read_text('utf-8')) if p.exists() else {}


FACTS = {'bio': _load('bio-facts.json'), 'geo': _load('geo-facts.json')}

# словари параметрических генераторов пополняются из таблиц фактов: систематика (b_taxa) и пищевые сети (b_foodweb)
_known = {row[-1] for row in TAXA}
for _chain in FACTS['bio'].get('taxonomy', {}).values():
    if len(_chain) == 7 and _chain[-1] not in _known:
        TAXA.append(_chain)
        _known.add(_chain[-1])
for _name, _web in FACTS['bio'].get('webs', {}).items():
    WEBS.setdefault(_name, _web)
LET = 'АБВГДЕЖЗИК'


def table(ref, section):
    """'bio/organelles' → раздел section файла bio-facts.json, запись organelles."""
    ns, name = ref.split('/', 1)
    try:
        return FACTS[ns][section][name]
    except KeyError:
        raise KeyError(f'нет таблицы {section}:{ref}') from None


def parse_args(args):
    """['bio/x', 'k=4', 'each'] → ('bio/x', {'k': '4', 'each': True})."""
    pos, kw = [], {}
    for a in args:
        if '=' in a:
            k, v = a.split('=', 1)
            kw[k] = v
        elif a in ('each', 'diff', 'obj', 'prop', 'cls', 'rev', 'max', 'min', 'ru', 'world', 'same', 'city', 'center'):  # флаги
            kw[a] = True
        else:
            pos.append(a)
    return pos, kw


class Skip(Exception):
    """Генератор не смог собрать карточку из этих параметров — попробовать другие."""


def numbered(items):
    return [{'id': str(i + 1), 't': t} for i, t in enumerate(items)]


def match_card(topic, q, left, right, ans_idx, e, chk):
    """left — тексты для букв, right — тексты для цифр, ans_idx[i] — индекс right для left[i]."""
    o = {'left': [{'id': LET[i], 't': t} for i, t in enumerate(left)], 'right': numbered(right)}
    a = {LET[i]: str(j + 1) for i, j in enumerate(ans_idx)}
    c = card('match', topic, q, a, e, chk, o=o)
    c['x'] = ''.join(str(j + 1) for j in ans_idx)
    return c


def many_card(topic, q, items, good, e, chk):
    """items — тексты вариантов, good — индексы верных; ответ ЕГЭ — цифры по возрастанию."""
    c = card('many', topic, q, [str(i + 1) for i in sorted(good)], e, chk, o=numbered(items))
    c['x'] = ''.join(str(i + 1) for i in sorted(good))
    return c


def seq_card(topic, q, shown, order, e, chk, tail='Запишите в таблицу соответствующую последовательность цифр.'):
    """shown — перемешанные тексты, order — индексы shown в верном порядке."""
    ans = ''.join(str(i + 1) for i in order)
    q = q.rstrip('.:') + ': ' + '; '.join(f'{i + 1}) {t}' for i, t in enumerate(shown)) + '. ' + tail
    c = card('num', topic, q, ans, e, chk)
    c['x'] = ans
    return c


def cap(s):
    return s[:1].upper() + s[1:]


# формулировки КИМ (свои, в стиле экзамена)
TAIL_MATCH = 'Запишите в таблицу выбранные цифры под соответствующими буквами.'
TAIL_MANY = 'Выберите три верных ответа из шести и запишите в таблицу цифры, под которыми они указаны.'
NUM_WORD = {2: 'два', 3: 'три', 4: 'четыре', 5: 'пять', 6: 'шесть'}
NUM_GEN = {2: 'двух', 3: 'трёх', 4: 'четырёх', 5: 'пяти', 6: 'шести'}


def table_lvl_ok(T, kw):
    """Вся таблица помечена уровнем (level: ege) — для другого экзамена не берём."""
    want = kw.get('lvl')
    return not want or T.get('level') not in ('ege' if want == 'oge' else 'oge',)


def lvl_ok(item, kw, S=None):
    """Уровень: для ОГЭ (lvl=oge) не берём помеченное "ege", для ЕГЭ (lvl=ege) — помеченное "oge"."""
    want = kw.get('lvl')
    if not want:
        return True
    other = 'ege' if want == 'oge' else 'oge'
    if isinstance(item, dict) and item.get('level') == other:
        return False
    name = item['t'] if isinstance(item, dict) else item
    if S is not None and name in S.get(f'{other}_only', []):
        return False
    return True


# ---------------------------------------------------------------- sets: объекты × свойства

def set_matrix(S, kw=None):
    kw = kw or {}
    objs = [o for o in S['objects'] if lvl_ok(o, kw, S)]
    props = [(p['t'], set(p['yes']) & set(objs), p.get('syn')) for p in S['props'] if lvl_ok(p, kw, S)]
    return objs, [(t, y, syn) for t, y, syn in props if y]


def false_about(S, x, props, near, pool):
    """Неверные утверждения об x: свойства ближайших соседей (кроме not_for: x) + типичные ошибки из таблицы (errors)."""
    nf = {p['t']: set(p.get('not_for', [])) for p in S['props']}
    bad = [t for t, s_, _ in props if x not in s_ and s_ & set(near) and x not in nf.get(t, ())]
    bad += [e['t'] for e in S.get('errors', []) if e.get('obj') == x and e['t'] not in bad]
    bad += [t for t in (S.get('not') or {}).get(x, []) if t not in bad]
    return bad


def pool_of(S, kw, objs=None):
    g = kw.get('g')
    pool = list(S['groups'][g]) if g else list(S['objects'])
    return [o for o in pool if objs is None or o in objs]


def no_syn(chosen, props):
    """Не ставить в одну карточку два свойства из одной группы синонимов."""
    syn = {t: s for t, _, s in props}
    seen = set()
    for t in chosen:
        s = syn.get(t)
        for g in (s if isinstance(s, list) else [s] if s else []):
            if g in seen:
                return False
            seen.add(g)
    return True


def gen_d_match(rng, args, topic='dict'):
    """Соответствие «характеристика → объект» (ЕГЭ 6, 10, 14, 19; ОГЭ 11, 18): 2–3 объекта, 6 характеристик,
    распределение ответов не хуже 3–2–1 (для двух объектов — 4–2)."""
    (ref,), kw = parse_args(args)
    S = table(ref, 'sets')
    objs, props = set_matrix(S, kw)
    pool = pool_of(S, kw, objs)
    k = int(kw.get('k', rng.choice([2, 2, 3] if len(pool) >= 3 else [2])))
    if len(pool) < k:
        raise Skip(ref)
    n = int(kw.get('n', 6))
    cap_ = 3 if k >= 3 else 4
    for _ in range(80):
        chosen = rng.sample(pool, k)
        cand = [(t, [o for o in chosen if o in y]) for t, y, _ in props]
        cand = [(t, hit[0]) for t, hit in cand if len(hit) == 1]
        by = {o: [t for t, h in cand if h == o] for o in chosen}
        if any(len(v) < 1 for v in by.values()) or len(cand) < n:
            continue
        pick = [rng.choice(by[o]) for o in chosen]
        rest = [t for t, _ in cand if t not in pick]
        rng.shuffle(rest)
        who = dict(cand)
        cnt = Counter(who[t] for t in pick)
        for t in rest:
            if len(pick) == n:
                break
            if cnt[who[t]] < cap_ and no_syn(pick + [t], props):
                pick.append(t)
                cnt[who[t]] += 1
        if len(pick) < n or not no_syn(pick, props):
            continue
        rng.shuffle(pick)
        right = sorted(chosen, key=lambda o: objs.index(o))
        ans = [right.index(who[t]) for t in pick]
        q = (f'Установите соответствие между характеристиками и {S.get("q_obj", "объектами")}: к каждой позиции, данной '
             f'в первом столбце, подберите соответствующую позицию из второго столбца. {TAIL_MATCH}')
        e = '; '.join(f'{LET[i]} — {right[j]}' for i, j in enumerate(ans)) + '.'
        return match_card(topic, q, pick, right, ans, e, {'eng': 'd_match', 'ref': ref, 'objs': right, 'props': pick})
    raise Skip(ref)


def check_d_match(c):
    S = table(c['ref'], 'sets')
    yes = {p['t']: set(p['yes']) for p in S['props']}
    out = ''
    for t in c['props']:
        hits = [i for i, o in enumerate(c['objs']) if o in yes[t]]
        if len(hits) != 1:
            return False
        out += str(hits[0] + 1)
    return out


def similarity_order(x, objs, props):
    """Соседи объекта по доле общих свойств — из них берём неверные варианты (типичная путаница)."""
    own = {t for t, y, _ in props if x in y}
    def sim(o):
        other = {t for t, y, _ in props if o in y}
        return len(own & other) / (len(own | other) or 1)
    return sorted((o for o in objs if o != x), key=sim, reverse=True)


def gen_d_many(rng, args, topic='dict'):
    """3 верных из 6 (ЕГЭ 7, 11, 15, 18; ОГЭ 9, 16, 17). Неверные — свойства ближайших «соседей» объекта.
    Режим diff: «Какие признаки характерны для X, в отличие от Y?»"""
    (ref,), kw = parse_args(args)
    S = table(ref, 'sets')
    objs, props = set_matrix(S, kw)
    pool = pool_of(S, kw, objs)
    n_true, n_all = int(kw.get('t', 3)), int(kw.get('n', 6))
    for _ in range(80):
        if kw.get('diff'):
            if len(pool) < 2:
                raise Skip(ref)
            x = rng.choice(pool)
            y = similarity_order(x, pool, props)[0] if rng.random() < 0.7 else rng.choice([o for o in pool if o != x])
            good = [t for t, s, _ in props if x in s and y not in s]
            bad = [t for t, s, _ in props if y in s and x not in s]
            q = (f'Чем {x} {"отличаются" if plural_of(x) == "plur" else "отличается"} от {inflect(y, "gent")}? Выберите признаки, которые есть только у {inflect(x, "gent")}. '
                 f'{TAIL_MANY.replace("три", NUM_WORD[n_true]).replace("шести", NUM_GEN[n_all])}')
        else:
            x = rng.choice(pool)
            y = None
            near = similarity_order(x, pool, props)[:2]
            good = [t for t, s, _ in props if x in s and not set(pool) <= s]
            bad = [t for t, s, _ in props if x not in s and s & set(near)] or \
                  [t for t, s, _ in props if x not in s and s & set(pool)]
            q = (f'Какие признаки характерны для {inflect(x, "gent")}? '
                 f'{TAIL_MANY.replace("три", NUM_WORD[n_true]).replace("шести", NUM_GEN[n_all])}')
        if len(good) < n_true or len(bad) < n_all - n_true:
            continue
        items = rng.sample(good, n_true)
        if not no_syn(items, props):
            continue
        items += rng.sample(bad, n_all - n_true)
        rng.shuffle(items)
        gi = [i for i, t in enumerate(items) if t in good]
        e = 'Верно: ' + '; '.join(items[i] for i in gi) + '.'
        return many_card(topic, q, items, gi, e, {'eng': 'd_many', 'ref': ref, 'x': x, 'y': y, 'items': items})
    raise Skip(ref)


def check_d_many(c):
    S = table(c['ref'], 'sets')
    yes = {p['t']: set(p['yes']) for p in S['props']}
    ok = [i for i, t in enumerate(c['items'])
          if c['x'] in yes[t] and (c['y'] is None or c['y'] not in yes[t])]
    return [str(i + 1) for i in ok]


def gen_d_one(rng, args, topic='dict'):
    """Один из четырёх: верное утверждение об объекте или объект по признаку (ОГЭ 14, 15; текстовая замена рисунков)."""
    (ref,), kw = parse_args(args)
    S = table(ref, 'sets')
    objs, props = set_matrix(S, kw)
    pool = pool_of(S, kw, objs)
    by_obj = kw.get('obj') or (not kw.get('prop') and rng.random() < 0.5)
    for _ in range(80):
        if by_obj:                                   # «Какой … ?» — признак → объект
            t, s, _ = rng.choice(props)
            yes = [o for o in pool if o in s]
            no = [o for o in pool if o not in s]
            if len(yes) != 1 or len(no) < 3:
                continue
            x = yes[0]
            o, a = one(rng, x, similarity_order(x, no, props)[:3])
            noun = S.get('q_one', 'из перечисленных структур')
            q = f'{which(noun)} {noun} {t}?' if S.get('q_one') else f'Какая из перечисленных структур характеризуется так: {t}?'
            return card('one', topic, q, a, f'{cap(t)} — {x}.', {'eng': 'd_one', 'ref': ref, 'mode': 'obj', 't': t,
                        'opts': [z['t'] for z in o]}, o=o)
        x = rng.choice(pool)
        near = similarity_order(x, pool, props)[:2]
        good = [t for t, s, _ in props if x in s and not set(pool) <= s]
        bad = false_about(S, x, props, near, pool)
        if not good or len(bad) < 3:
            continue
        t = rng.choice(good)
        o, a = one(rng, t, rng.sample(bad, 3))
        q = f'Какое утверждение {ob(inflect(x, "loct"))} верно?'
        return card('one', topic, q, a, f'{cap(x)}: {t}.', {'eng': 'd_one', 'ref': ref, 'mode': 'prop', 'x': x,
                    'opts': [z['t'] for z in o]}, o=o)
    raise Skip(ref)


def check_d_one(c):
    S = table(c['ref'], 'sets')
    yes = {p['t']: set(p['yes']) for p in S['props']}
    if c['mode'] == 'obj':
        ok = [i for i, o in enumerate(c['opts']) if o in yes[c['t']]]
    else:
        ok = [i for i, t in enumerate(c['opts']) if c['x'] in yes.get(t, ())]     # errors — заведомо неверны
    return '123456'[ok[0]] if len(ok) == 1 else None


JUDGE = ['верно только А', 'верно только Б', 'верны оба суждения', 'оба суждения неверны']


def gen_d_judge(rng, args, topic='dict'):
    """Верны ли суждения А и Б (ОГЭ 12): два предложения об ОДНОМ объекте; неверное — свойство ближайшего соседа."""
    (ref,), kw = parse_args(args)
    S = table(ref, 'sets')
    objs, props = set_matrix(S, kw)
    pool = pool_of(S, kw, objs)
    want = rng.choice([(1, 0), (0, 1), (1, 1), (0, 0)])
    for _ in range(80):
        x = rng.choice(pool)
        near = similarity_order(x, pool, props)[:2]
        good = [t for t, s, _ in props if x in s and not set(pool) <= s]
        bad = false_about(S, x, props, near, pool)
        if len(good) < 2 or len(bad) < 2:
            continue
        g = rng.sample(good, 2)
        b = rng.sample(bad, 2)
        sts = [(x, g[i] if want[i] else b[i], want[i]) for i in range(2)]
        if not no_syn([t for _, t, _ in sts], props):
            continue
        ans = {(1, 0): 0, (0, 1): 1, (1, 1): 2, (0, 0): 3}[want]
        o = [{'id': str(i + 1), 't': t} for i, t in enumerate(JUDGE)]
        about = inflect(x, 'loct')
        q = (f'Верны ли следующие суждения {ob(about)}? А. {predicate(x, sts[0][1])}. Б. {predicate(x, sts[1][1])}.')
        e = f'А — {"верно" if sts[0][2] else "неверно"}, Б — {"верно" if sts[1][2] else "неверно"}.'
        return card('one', topic, q, str(ans + 1), e, {'eng': 'd_judge', 'ref': ref, 'st': [[x_, t] for x_, t, _ in sts]}, o=o)
    raise Skip(ref)


def check_d_judge(c):
    S = table(c['ref'], 'sets')
    yes = {p['t']: set(p['yes']) for p in S['props']}
    A, B = (x in yes.get(t, ()) for x, t in c['st'])
    return '1234'[{(True, False): 0, (False, True): 1, (True, True): 2, (False, False): 3}[(A, B)]]


def attr_pairs(S, attr):
    vals = S['attrs'][attr]
    return {o: v for o, v in vals.items() if list(vals.values()).count(v) == 1}


def cols_of(title, C=None):
    if C and C.get('cols'):
        return C['cols']
    if '→' in title:
        a, b = [x.strip() for x in title.split('→', 1)]
        return [cap(a), cap(b)]
    return ['Объект', 'Характеристика']


EXTRA_CLASSES = {  # правдоподобные неверные варианты, когда классов в таблице мало
    'geo/peoples_religion': ['католицизм', 'протестантизм', 'иудаизм', 'индуизм'],
}


def gen_d_analogy(rng, args, topic='dict'):
    """Таблица «объект — характеристика» с пропуском (ЕГЭ 1 — ответ словом; ОГЭ 8 — выбор 1 из 4)."""
    (ref,), kw = parse_args(args)
    if kw.get('cls'):
        C = table(ref, 'classes')
        if not table_lvl_ok(C, kw):
            raise Skip(ref)
        items = {k: v for k, v in C['items'].items() if lvl_ok(k, kw, C) and lvl_ok(v, kw, C)}
        x, y = rng.sample(list(items), 2)
        vx, vy = items[x], items[y]
        if vx == vy:
            raise Skip(ref)
        classes = [c for c in C['classes'] if c in set(items.values())]
        wrong = [c for c in classes if c not in (vy, vx)]
        wrong += [c for c in EXTRA_CLASSES.get(ref, []) if c not in wrong and c not in (vx, vy)]
        if len(wrong) < 3:
            raise Skip(ref)
        # корень ответа не должен стоять в описании (иначе ответ подсказан)
        stem = re.sub(r'(ия|ика|ие|ый|ой|ий|ая)$', '', vy.lower())[:6]
        if len(stem) >= 5 and stem in y.lower():
            raise Skip(ref)
        o, a = one(rng, vy, rng.sample(wrong, 3))
        cols = cols_of(C['title'], C)
        chk = {'eng': 'd_analogy', 'ref': ref, 'cls': True, 'y': y, 'opts': [z['t'] for z in o]}
        acc = (C.get('answers') or C.get('accept') or {}).get(vy)
        if acc:
            chk['answers'] = acc              # допустимые написания для ответа словом
    else:
        S = table(ref, 'sets')
        attr = kw.get('a') or rng.choice(list(S['attrs']))
        pairs = attr_pairs(S, attr)
        dom = S.get('domain', {})
        if len(pairs) < 4:
            raise Skip(ref)
        x, y = rng.sample(list(pairs), 2)
        if dom and dom.get(x) != dom.get(y):
            raise Skip(ref)
        vx, vy = pairs[x], pairs[y]
        same = [k for k in pairs if k not in (x, y) and (not dom or dom.get(k) == dom.get(y))]
        if len(same) < 3:
            raise Skip(ref)
        o, a = one(rng, vy, [pairs[k] for k in rng.sample(same, 3)])
        cols = [S.get('q_one', 'Объект').capitalize(), cap(attr)]
        chk = {'eng': 'd_analogy', 'ref': ref, 'attr': attr, 'y': y, 'opts': [z['t'] for z in o]}
    title = kw.get('title') or f'{cols[0]} и {cols[1].lower()}'
    first = kw.get('cls') and C.get('cols')          # в таблице фактов cols = [класс, объект], как в КИМ
    r1, r2 = (f'{vx} | {x}', f'? | {y}') if first else (f'{x} | {vx}', f'{y} | ?')
    q = (f'Рассмотрите таблицу «{title}» и заполните пустую ячейку. | {cols[0]} | {cols[1]} | — | {r1} | — '
         f'| {r2} | Какое понятие следует вписать на место вопроса?')
    return card('one', topic, q, a, f'{cap(y)} — {vy}.', chk, o=o)


def check_d_analogy(c):
    if c.get('cls'):
        v = table(c['ref'], 'classes')['items'][c['y']]
    else:
        v = table(c['ref'], 'sets')['attrs'][c['attr']][c['y']]
    ok = [i for i, t in enumerate(c['opts']) if t == v]
    return '123456'[ok[0]] if len(ok) == 1 else None


def gen_d_table(rng, args, topic='dict'):
    """Таблица (ЕГЭ 20): 3 строки × «объект + 2 атрибута», пропуски А–В в разных столбцах, список из 8 элементов."""
    (ref,), kw = parse_args(args)
    S = table(ref, 'sets')
    attrs = [a for a in S.get('attrs', {}) if len(attr_pairs(S, a)) >= 4]
    if len(attrs) < 2:
        raise Skip(ref)
    cols = rng.sample(attrs, 2)
    rows = [o for o in S['objects'] if all(o in attr_pairs(S, a) for a in cols)]
    if len(rows) < 5:
        raise Skip(ref)
    rows = rng.sample(rows, 3)
    head = [S.get('q_one', 'Объект').capitalize()] + [cap(a) for a in cols]
    # пропуски: в каждой строке ровно один, в разных столбцах (включая столбец объекта)
    colidx = rng.sample(range(3), 3)
    hide = [(rows[i], colidx[i]) for i in range(3)]
    def val(r, j):
        return r if j == 0 else attr_pairs(S, cols[j - 1])[r]
    true = [val(r, j) for r, j in hide]
    others = [o for o in S['objects'] if o not in rows and all(o in attr_pairs(S, a) for a in cols)]
    distr = set()
    for o in others:
        distr.add(o)
        for a in cols:
            distr.add(attr_pairs(S, a)[o])
    distr -= set(true)
    nd = int(kw.get('opts', 8)) - 3
    if len(distr) < nd:
        raise Skip(ref)
    items = true + rng.sample(sorted(distr), nd)
    rng.shuffle(items)
    lines = []
    for r in rows:
        cells = []
        for j in range(3):
            cells.append(f'({LET[[h[0] for h in hide].index(r)]})' if (r, j) in hide else val(r, j))
        lines.append(' | '.join(cells))
    q = (f'Проанализируйте таблицу «{S["title"]}». Заполните пустые ячейки таблицы, используя элементы, приведённые в списке: '
         f'для каждой ячейки, обозначенной буквой, выберите соответствующий элемент. | {" | ".join(head)} | — '
         + ' — '.join(f'| {l} |' for l in lines) + ' Список элементов: ' +
         '; '.join(f'{i + 1}) {t}' for i, t in enumerate(items)) + '. Запишите в таблицу выбранные цифры под соответствующими буквами.')
    ans = ''.join(str(items.index(v) + 1) for v in true)
    c = card('num', topic, q, ans, '; '.join(f'{LET[i]} — {v}' for i, v in enumerate(true)) + '.',
             {'eng': 'd_table', 'ref': ref, 'cols': cols, 'hide': hide, 'items': items})
    c['x'] = ans
    return c


def check_d_table(c):
    S = table(c['ref'], 'sets')
    out = ''
    for r, j in c['hide']:
        v = r if j == 0 else S['attrs'][c['cols'][j - 1]][r]
        hits = [i for i, t in enumerate(c['items']) if t == v]
        if len(hits) != 1:
            return None
        out += str(hits[0] + 1)
    return out


# ---------------------------------------------------------------- seqs, classes, effects, texts

def gen_d_seq(rng, args, topic='dict'):
    """Последовательность (ЕГЭ 8, 16; ОГЭ 5): шаги процесса в исходном порядке, перемешанные; ключевые звенья (keep)
    из таблицы всегда входят в выборку."""
    (ref,), kw = parse_args(args)
    Q = table(ref, 'seqs')
    full = Q['steps']
    drop = set(Q.get('ege_only', [])) if kw.get('lvl') == 'oge' else set(Q.get('oge_only', [])) if kw.get('lvl') == 'ege' else set()
    steps = [t for t in full if t not in drop]
    keep_t = [full[i] for i in Q.get('keep', []) if i < len(full) and full[i] not in drop]
    if kw.get('m') and len(steps) < int(kw['m']):
        raise Skip(ref)                                 # прототип требует ровно m элементов, как в КИМ
    m = min(int(kw.get('m', rng.choice([5, 6]))), len(steps))
    if m < 4:
        raise Skip(ref)
    keep = [steps.index(t) for t in keep_t]
    if rng.random() < 0.5 and len(steps) > m and not keep:
        s0 = rng.randrange(len(steps) - m + 1)
        idx = list(range(s0, s0 + m))
    else:
        rest = [i for i in range(len(steps)) if i not in keep]
        idx = sorted(rng.sample(keep, m) if len(keep) > m else keep + rng.sample(rest, m - len(keep)))
    shown = idx[:]
    rng.shuffle(shown)
    order = sorted(range(m), key=lambda j: shown[j])
    e = 'Порядок: ' + ' → '.join(steps[i] for i in idx) + '.'
    q = Q['q'] if Q['q'].startswith('Установите') else 'Установите последовательность: ' + Q['q'][:1].lower() + Q['q'][1:]
    return seq_card(topic, q, [steps[i] for i in shown], order, e, {'eng': 'd_seq', 'ref': ref, 'shown': [steps[i] for i in shown]})


def check_d_seq(c):
    steps = table(c['ref'], 'seqs')['steps']
    pos = [steps.index(t) for t in c['shown']]
    return ''.join(str(j + 1) for j in sorted(range(len(pos)), key=lambda j: pos[j]))


def gen_d_class(rng, args, topic='dict'):
    """Отнести элементы к классам (ОГЭ 2, 11, 18; ЕГЭ 19): k классов, n элементов; each — по одному на класс.
    Распределение не хуже 3–2–1 (две категории — не хуже 4–2)."""
    (ref,), kw = parse_args(args)
    C = table(ref, 'classes')
    if not table_lvl_ok(C, kw):
        raise Skip(ref)
    only = set(kw['only'].split('+')) if kw.get('only') else None
    by = {}
    for it, cl in C['items'].items():
        if not lvl_ok(it, kw, C) or (only and cl not in only) or it in C.get('hint_items', []) or it in C.get('hint', []):
            continue
        by.setdefault(cl, []).append(it)
    classes = [c for c in C['classes'] if len(by.get(c, [])) >= 1]
    k = min(int(kw.get('k', rng.choice([2, 3]))), len(classes))
    n = int(kw.get('n', 6 if k <= 3 else k))
    if k < 2:
        raise Skip(ref)
    cap_ = 3 if k >= 3 else 4
    for _ in range(80):
        cls = rng.sample(classes, k)
        if kw.get('each'):
            items = [rng.choice(by[c]) for c in cls]
        else:
            if any(len(by[c]) < 1 for c in cls) or sum(min(len(by[c]), cap_) for c in cls) < n:
                continue
            items = [rng.choice(by[c]) for c in cls]
            cnt = Counter(C['items'][it] for it in items)
            pool = [it for c in cls for it in by[c] if it not in items]
            rng.shuffle(pool)
            for it in pool:
                if len(items) == n:
                    break
                if cnt[C['items'][it]] < cap_:
                    items.append(it)
                    cnt[C['items'][it]] += 1
            if len(items) < n:
                continue
        rng.shuffle(items)
        right = [c for c in C['classes'] if c in cls]
        ans = [right.index(C['items'][it]) for it in items]
        base = C.get('q') or f'Установите соответствие: {C["title"]}'
        q = f'{base.rstrip(".")}: к каждой позиции, данной в первом столбце, подберите соответствующую позицию из второго столбца. {TAIL_MATCH}'
        e = '; '.join(f'{it} — {C["items"][it]}' for it in items) + '.'
        return match_card(topic, q, items, right, ans, e, {'eng': 'd_class', 'ref': ref, 'items': items, 'right': right})
    raise Skip(ref)


def check_d_class(c):
    C = table(c['ref'], 'classes')
    return ''.join(str(c['right'].index(C['items'][it]) + 1) for it in c['items'])


CHANGE = ['увеличится', 'уменьшится', 'не изменится']


def gen_d_change(rng, args, topic='dict'):
    """Как изменится величина (ЕГЭ 2): ситуация и ровно две величины (как в КИМ), ответы 1/2/3, цифры могут повторяться."""
    (ref,), kw = parse_args(args)
    E = FACTS[ref.split('/')[0]]['effects']
    keys = kw['keys'].split('+') if kw.get('keys') else list(E)
    if kw.get('grp'):
        keys = [k for k in E if E[k].get('group') in kw['grp'].split('+')] or keys
    keys = [k for k in keys if k in E]
    name = rng.choice(keys)
    sit = E[name]
    vals = list(sit['values'])
    m = min(int(kw.get('m', 2)), len(vals))
    pick = rng.sample(vals, m)
    ans = [CHANGE.index(sit['values'][v]) for v in pick]
    q = (f'{sit["situation"].rstrip(".")}. Как изменятся при этом {" и ".join(pick)}? Для каждой величины определите '
         'соответствующий характер её изменения. Запишите в таблицу выбранные цифры для каждой величины. '
         'Цифры в ответе могут повторяться.')
    return match_card(topic, q, pick, CHANGE, ans, '; '.join(f'{v} — {sit["values"][v]}' for v in pick) + '.',
                      {'eng': 'd_change', 'ref': ref, 'sit': name, 'pick': pick})


def check_d_change(c):
    sit = FACTS[c['ref'].split('/')[0]]['effects'][c['sit']]
    return ''.join(str(CHANGE.index(sit['values'][v]) + 1) for v in c['pick'])


def gen_d_text(rng, args, topic='dict'):
    """Вставить термины в текст (ОГЭ 10, ЕГЭ гео 5): свой текст со слотами, список = ответы + шум."""
    (ref,), kw = parse_args(args)
    ns, key = ref.split('/', 1)
    T = [t for t in FACTS[ns][key] if not kw.get('topic') or t.get('topic', '').startswith(kw['topic'])]
    if not T:
        raise Skip(ref)
    t = rng.choice(T)
    slots = list(t['slots'])
    items = [t['slots'][s] for s in slots] + list(t['noise'])
    rng.shuffle(items)
    ans = ''.join(str(items.index(t['slots'][s]) + 1) for s in slots)
    text = t['t']
    for s in slots:
        text = text.replace('{' + s + '}', f'({s})')
    ttl = f' «{t["title"]}»' if t.get('title') else ''
    q = (f'Вставьте в текст{ttl} пропущенные термины из предложенного перечня, используя для этого цифровые обозначения. '
         f'{text} Перечень терминов: ' +
         '; '.join(f'{i + 1}) {x}' for i, x in enumerate(items)) + f'. Запишите в таблицу цифры выбранных ответов в порядке букв ({", ".join(slots)}).')
    c = card('num', topic, q, ans, '; '.join(f'{s} — {t["slots"][s]}' for s in slots) + '.',
             {'eng': 'd_text', 'ref': ref, 'text': t['t'], 'items': items})
    c['x'] = ans
    return c


def check_d_text(c):
    ns, key = c['ref'].split('/', 1)
    t = next(x for x in FACTS[ns][key] if x['t'] == c['text'])
    return ''.join(str(c['items'].index(t['slots'][s]) + 1) for s in t['slots'])

CMANY_Q = {  # таблица → (начало вопроса, именная группа с {x} в им. падеже — склоняется в вин. падеж) или шаблон с «{x}»
    'species_criterion': ('Какие примеры иллюстрируют', '{x} критерий вида'),
    'selection_form': ('Какие примеры иллюстрируют', '{x} форма естественного отбора'),
    'speciation': ('Какие примеры иллюстрируют', '{x} видообразование'),
    'evo_path': ('Какие примеры иллюстрируют', '{x}'),
    'biotic_relation': ('Какие примеры иллюстрируют', '{x}'),
    'variability_examples': ('Какие примеры иллюстрируют', '{x}'),
    'adaptation_type': ('Какие примеры иллюстрируют', '{x} приспособление'),
    'evo_evidence': 'Какие примеры относят к доказательствам эволюции группы «{x}»?',
    'eco_factor': 'Какие из перечисленных факторов относят к группе «{x}»?',
    'trophic_role': 'Какие из перечисленных организмов в экосистеме выполняют роль «{x}»?',
    'biosphere_substance': 'Какие примеры относят к веществу биосферы, которое В. И. Вернадский назвал «{x}»?',
    'cycle_process': 'Какие процессы относятся к круговороту {x}?',
    'anthropo_factor': 'Какие из перечисленных факторов антропогенеза относят к группе «{x}»?',
    'mutation_types': 'Какие примеры относят к мутациям типа «{x}»?',
    'organ_system': 'Какие органы относят к системе «{x}»?',
    'disease_cause': 'Какие заболевания относят к группе «{x}»?',
    'animal_class': 'Какие из перечисленных животных относят к классу «{x}»?',
    'habitat': 'Какие из перечисленных организмов обитают в среде «{x}»?',
    'development_examples': 'У каких из перечисленных животных {x}?',
    'germ_layers': 'Какие органы развиваются из зародышевого листка «{x}»?',
    'breeding_examples': 'Какие примеры иллюстрируют метод селекции «{x}»?',
    'organ_modification': 'Какие примеры относят к видоизменениям «{x}»?',
}


def cmany_question(ref, x):
    t = CMANY_Q.get(ref.split('/', 1)[1], 'Какие примеры относятся к понятию «{x}»?')
    if isinstance(t, tuple):
        return f'{t[0]} {inflect(t[1].format(x=x), "accs")}?'
    return t.format(x=x)


def gen_d_cmany(rng, args, topic='dict'):
    """Выбрать 3 из 6 примеров, относящихся к одному понятию (ЕГЭ 17, 18; ОГЭ 9, 17): по таблице classes."""
    (ref,), kw = parse_args(args)
    C = table(ref, 'classes')
    by = {}
    for it, cl in C['items'].items():
        if lvl_ok(it, kw, C):
            by.setdefault(cl, []).append(it)
    t, n = int(kw.get('t', 3)), int(kw.get('n', 6))
    cls = [c for c in C['classes'] if len(by.get(c, [])) >= t]
    if not cls:
        raise Skip(ref)
    x = rng.choice(cls)
    others = [it for c, its in by.items() if c != x for it in its]
    if len(others) < n - t:
        raise Skip(ref)
    items = rng.sample(by[x], t) + rng.sample(others, n - t)
    rng.shuffle(items)
    gi = [i for i, it in enumerate(items) if C['items'][it] == x]
    q = cmany_question(ref, x) + ' ' + TAIL_MANY.replace('три', NUM_WORD[t]).replace('шести', NUM_GEN[n])
    e = '; '.join(f'{it} — {C["items"][it]}' for it in items) + '.'
    return many_card(topic, q, items, gi, e, {'eng': 'd_cmany', 'ref': ref, 'x': x, 'items': items})


def check_d_cmany(c):
    C = table(c['ref'], 'classes')
    return [str(i + 1) for i, it in enumerate(c['items']) if C['items'][it] == c['x']]


def gen_d_ctable(rng, args, topic='dict'):
    """Таблица «пример | категория» (ЕГЭ 20): 3 строки разных категорий, 3 пропуска, список из 6 элементов."""
    (ref,), kw = parse_args(args)
    C = table(ref, 'classes')
    by = {}
    for it, cl in C['items'].items():
        by.setdefault(cl, []).append(it)
    cls = [c for c in C['classes'] if by.get(c)]
    if len(cls) < 4:
        raise Skip(ref)
    rows_c = rng.sample(cls, 3)
    rows = [(rng.choice(by[c]), c) for c in rows_c]
    hide = [(i, rng.randrange(2)) for i in range(3)]   # в каждой строке пропущена ровно одна ячейка
    true = [rows[i][j] for i, j in hide]
    # шум: категории не из таблицы и примеры категорий не из таблицы — чтобы не было второго подходящего
    spare_c = [c for c in cls if c not in rows_c]
    spare_i = [it for c in spare_c for it in by[c]]
    nd = int(kw.get('opts', 8)) - 3
    nc = min(len(spare_c), nd // 2 + 1)
    if len(spare_i) < nd - nc:
        raise Skip(ref)
    distr = rng.sample(spare_c, nc) + rng.sample(spare_i, nd - nc)
    items = true + distr
    rng.shuffle(items)
    head = cols_of(C['title'], C)
    lines = []
    for i, (it, c) in enumerate(rows):
        v = [it, c]
        for j in range(2):
            if (i, j) in hide:
                v[j] = f'({LET[hide.index((i, j))]})'
        lines.append(' | '.join(v))
    q = (f'Проанализируйте таблицу «{head[0]} и {head[1].lower()}». Заполните пустые ячейки таблицы, используя элементы, '
         f'приведённые в списке. | {head[0]} | {head[1]} | — ' + ' — '.join(f'| {l} |' for l in lines) +
         ' Список элементов: ' + '; '.join(f'{k + 1}) {t}' for k, t in enumerate(items)) +
         '. Запишите в таблицу выбранные цифры под соответствующими буквами.')
    ans = ''.join(str(items.index(v) + 1) for v in true)
    c = card('num', topic, q, ans, '; '.join(f'{LET[k]} — {v}' for k, v in enumerate(true)) + '.',
             {'eng': 'd_ctable', 'ref': ref, 'rows': rows, 'hide': hide, 'items': items})
    c['x'] = ans
    return c


def check_d_ctable(c):
    C = table(c['ref'], 'classes')
    out = ''
    for i, j in c['hide']:
        it, cl = c['rows'][i]
        if j == 0:     # пропущен пример: подходит любой элемент списка этой категории
            ok = [k for k, v in enumerate(c['items']) if C['items'].get(v) == cl]
        else:          # пропущена категория: подходит категория показанного/пропущенного примера
            ok = [k for k, v in enumerate(c['items']) if v == C['items'][it]]
        if len(ok) != 1:
            return None
        out += str(ok[0] + 1)
    return out


def gen_d_kinds(rng, args, topic='dict'):
    """ОГЭ гео 29: «назовите ещё один вид явления» — выбрать вид того же понятия (1 из 4)."""
    (ref,), kw = parse_args(args)
    ns, key = ref.split('/', 1)
    K = FACTS[ns][key]
    cands = [c for c, v in K.items() if len(v['kinds']) >= 2]
    c = rng.choice(cands)
    shown, ok = rng.sample(K[c]['kinds'], 2)
    other = [k for d, v in K.items() if d != c for k in v['kinds'] if k not in K[c]['kinds']]
    o, a = one(rng, ok, rng.sample(other, 3))
    q = f'В тексте упомянут один из видов понятия «{c}»: {shown}. Какой из перечисленных — ещё один вид этого же понятия?'
    return card('one', topic, q, a, f'Виды ({K[c]["hint"]}): {", ".join(K[c]["kinds"])}.',
                {'eng': 'd_kinds', 'ref': ref, 'c': c, 'opts': [x['t'] for x in o]}, o=o)


def check_d_kinds(c):
    ns, key = c['ref'].split('/', 1)
    kinds = FACTS[ns][key][c['c']]['kinds']
    ok = [i for i, t in enumerate(c['opts']) if t in kinds]
    return '123456'[ok[0]] if len(ok) == 1 else None


def gen_d_gloss(rng, args, topic='dict'):
    """ЕГЭ гео 22, ОГЭ 29: термин по определению (1 из 4), своё определение из глоссария."""
    (ref,), kw = parse_args(args)
    ns, key = ref.split('/', 1)
    G = FACTS[ns][key]
    t = rng.choice(list(G))
    o, a = one(rng, t, rng.sample([x for x in G if x != t], 3))
    q = f'Какому понятию соответствует определение: «{G[t]["def"]}»?'
    return card('one', topic, q, a, f'{cap(t)}: ' + '; '.join(G[t].get('keys', [])) + '.',
                {'eng': 'd_gloss', 'ref': ref, 'def': G[t]['def'], 'opts': [x['t'] for x in o]}, o=o)


def check_d_gloss(c):
    ns, key = c['ref'].split('/', 1)
    G = FACTS[ns][key]
    ok = [i for i, t in enumerate(c['opts']) if G[t]['def'] == c['def']]
    return '123456'[ok[0]] if len(ok) == 1 else None


# ---------------------------------------------------------------- география: таблицы с числами и тегами

NOT_CITY = {'Адлерский район'}
FED_CITIES = {'Москва', 'Санкт-Петербург', 'Севастополь'}   # вне масштаба остальных — в сравнения городов не берём


def geo_rows(tab):
    """Строки таблицы geo-facts как {название: запись}; у стран — по школьному названию."""
    G = FACTS['geo']
    if tab == 'countries':
        return {r['name']: r for r in G['countries'].values()}
    if tab == 'stations':
        return {r['name']: r for r in G.get('stations', []) if r.get('school') is not False}
    if tab.startswith('obj'):
        cls = tab.split(':', 1)[1] if ':' in tab else None
        return {r['name']: r for r in G.get('objects', []) if (cls is None or r['class'] == cls) and r.get('school') is not False}
    if tab == 'capitals':
        return {r['name']: {'lat': v[0], 'lon': v[1]} for r in G['countries'].values()
                if len(r.get('capital_coords', {})) == 1 for v in r['capital_coords'].values()}
    if tab == 'ru_cities':                 # не город (район Сочи) — исключаем всюду
        return {k: v for k, v in G[tab].items() if k not in NOT_CITY}
    return G[tab]


def geo_value(tab, row, field):
    """Значение показателя и год (или None). Производные поля считаются здесь же."""
    if tab == 'countries':
        wb = row['wb']
        if field == 'natinc':                        # естественный прирост, ‰
            if 'birth' in wb and 'death' in wb:
                return round(wb['birth'][0] - wb['death'][0], 1), wb['birth'][1]
            return None
        if field == 'area' and 'land' in wb and wb['area'][0] > wb['land'][0] * 1.3:
            return None                              # в ряду World Bank 2023 площадь у части стран завышена (Канада, Норвегия…)
        if field in wb:
            return wb[field][0], wb[field][1]
        return None
    if tab == 'stations':
        if row.get('check'):                          # у пункта расхождение источников — в задания не берём
            return None
        t, p = row.get('t') or [], row.get('p') or []
        full_t = len(t) == 12 and None not in t
        full_p = len(p) == 12 and None not in p
        if field == 't_jan' and full_t:
            return t[0], row.get('period')
        if field == 't_jul' and full_t:
            return t[6], row.get('period')
        if field == 'amp' and full_t:
            return round(max(t) - min(t), 1), row.get('period')
        if field == 'p_year' and full_p:
            return round(sum(p)), row.get('period')
        if field in ('t_jan', 't_jul', 'amp', 'p_year'):
            return None
        v = row.get(field)
        return (v, row.get('period')) if v is not None else None
    v = row.get(field)
    if v is None:
        return None
    return v, (row.get('pop_date', '') or '')[:4] or None


ORDER_Q = {  # (таблица, показатель) → (что упорядочиваем, показатель в род. падеже, единицы, источник)
    ('countries', 'density'): ('страны', 'средней плотности населения', 'чел./км²', 'World Bank'),
    ('countries', 'natinc'): ('страны', 'естественного прироста населения', '‰', 'World Bank (рождаемость − смертность)'),
    ('countries', 'birth'): ('страны', 'рождаемости', '‰', 'World Bank'),
    ('countries', 'urban'): ('страны', 'доли городского населения', '%', 'World Bank'),
    ('countries', 'age65'): ('страны', 'доли населения в возрасте 65 лет и старше', '%', 'World Bank'),
    ('countries', 'age0014'): ('страны', 'доли детей до 15 лет в населении', '%', 'World Bank'),
    ('countries', 'life'): ('страны', 'ожидаемой продолжительности жизни', 'лет', 'World Bank'),
    ('countries', 'gdp_pc'): ('страны', 'ВВП на душу населения', 'долл.', 'World Bank'),
    ('countries', 'agr_gdp'): ('страны', 'доли сельского хозяйства в ВВП', '%', 'World Bank'),
    ('countries', 'agr_emp'): ('страны', 'доли занятых в сельском хозяйстве', '%', 'World Bank'),
    ('countries', 'pop'): ('страны', 'численности населения', 'чел.', 'World Bank'),
    ('countries', 'area'): ('страны', 'площади территории', 'км²', 'World Bank'),
    ('ru_subjects', 'density'): ('субъекты РФ', 'средней плотности населения', 'чел./км²', 'Росстат через Wikidata'),
    ('ru_subjects', 'pop'): ('субъекты РФ', 'численности населения', 'чел.', 'Росстат через Wikidata'),
    ('ru_subjects', 'area'): ('субъекты РФ', 'площади территории', 'км²', 'Wikidata'),
    ('ru_cities', 'pop'): ('города', 'численности населения', 'чел.', 'Росстат через Wikidata'),
    ('stations', 't_jan'): ('пункты', 'средней температуры января', '°C', 'климатические нормы'),
    ('stations', 't_jul'): ('пункты', 'средней температуры июля', '°C', 'климатические нормы'),
    ('stations', 'amp'): ('пункты', 'годовой амплитуды температур', '°C', 'климатические нормы'),
    ('stations', 'p_year'): ('пункты', 'годового количества осадков', 'мм', 'климатические нормы'),
    ('rivers', 'len_km'): ('реки', 'длины', 'км', 'Wikidata'),
    ('lakes', 'area_km2'): ('озёра', 'площади', 'км²', 'Wikidata'),
    ('peaks', 'elev_m'): ('вершины', 'абсолютной высоты', 'м', 'Wikidata'),
    ('obj:река', 'length_km'): ('реки', 'длины', 'км', 'Wikidata / ru.wikipedia'),
    ('obj:вершина', 'elev_m'): ('вершины', 'абсолютной высоты', 'м', 'Wikidata'),
    ('obj:озеро', 'area_km2'): ('озёра', 'площади', 'км²', 'Wikidata'),
    ('objects', 'lon'): ('объекты', 'долготы', '°', 'Wikidata'),
    ('objects', 'lat'): ('объекты', 'широты', '°', 'Wikidata'),
    ('ru_regions', 'soil_rank'): ('субъекты РФ', 'естественного плодородия преобладающих почв', 'балла (шкала 1–5)', 'почвенная карта атласа'),
}


def geo_filter(tab, rows, kw):
    """Фильтры: cont=Африка (часть света стран), ru=1 (пункты России), min=N (порог показателя)."""
    out = {}
    for k, r in rows.items():
        if kw.get('cont') and kw['cont'] not in r.get('continent', []):
            continue
        if kw.get('ru') and r.get('country') not in (None, 'Россия'):
            continue
        if kw.get('world') and r.get('country') in (None, 'Россия'):
            continue
        if kw.get('big') and tab == 'countries' and (geo_value(tab, r, 'pop') or (0,))[0] < float(kw['big']):
            continue
        if tab in ('ru_cities', 'ru_subjects') and k in FED_CITIES and not kw.get('fed'):
            continue
        out[k] = r
    return out


def spaced(vals, gap, rel=True):
    s = sorted(vals)
    if rel:
        return all(b >= a * gap if a > 0 else b - a >= gap for a, b in zip(s, s[1:]))
    return all(b - a >= gap for a, b in zip(s, s[1:]))


def gen_d_order(rng, args, topic='dict'):
    """Порядок объектов по показателю (ЕГЭ гео 3, 8, 19; ОГЭ 1, 3, 19). gap — минимальный разрыв соседей."""
    (tab, field), kw = parse_args(args)
    what, label, unit, srcname = ORDER_Q[(tab, field)]
    rows = geo_filter(tab, geo_rows(tab), kw)
    vals = {k: geo_value(tab, r, field) for k, r in rows.items()}
    vals = {k: v for k, v in vals.items() if v is not None and v[0] is not None}
    k = int(kw.get('k', 3))
    if len(vals) < k + 2:
        raise Skip(f'{tab}.{field}: мало данных')
    rel = field not in ('t_jan', 't_jul', 'natinc', 'soil_rank', 'lat', 'lon')
    gap = float(kw.get('gap', 1.3 if rel else 3))
    for _ in range(80):
        pick = rng.sample(list(vals), k)
        if not spaced([vals[p][0] for p in pick], gap, rel):
            continue
        if kw.get('same') and len({rows[p].get('continent_ocean') for p in pick}) > 1:
            continue
        asc = rng.random() < 0.5
        order = sorted(range(k), key=lambda i: vals[pick[i]][0], reverse=not asc)
        if field in ('lon', 'lat'):
            way = {('lon', True): 'с запада на восток', ('lon', False): 'с востока на запад',
                   ('lat', True): 'с юга на север', ('lat', False): 'с севера на юг'}[(field, asc)]
            q = f'Расположите географические объекты {way}'
        else:
            q = (f'Расположите {what} в порядке {"возрастания" if asc else "убывания"} {label}, начиная с '
                 f'{"наименьшего" if asc else "наибольшего"} значения')
        yr = sorted({str(vals[p][1]) for p in pick if vals[p][1]})
        e = (f'{cap(label)}: ' + '; '.join(f'{p} — {fmt(Fraction(str(vals[p][0])))} {unit}' for p in pick) +
             f' ({srcname}{", " + "/".join(yr) if yr else ""}).')
        return seq_card(topic, q, pick, order, e, {'eng': 'd_order', 'tab': tab, 'field': field, 'pick': pick, 'asc': asc})
    raise Skip(f'{tab}.{field}')


def check_d_order(c):
    rows = geo_rows(c['tab'])
    v = [geo_value(c['tab'], rows[p], c['field'])[0] for p in c['pick']]
    return ''.join(str(i + 1) for i in sorted(range(len(v)), key=lambda i: v[i], reverse=not c['asc']))


TAG_Q = {  # (поле, тег) → окончание вопроса «Выберите … , в которых …»
    ('hazards', 'permafrost'): 'распространена многолетняя мерзлота',
    ('hazards', 'seismic'): 'высока опасность сильных землетрясений',
    ('hazards', 'volcano'): 'есть действующие вулканы',
    ('hazards', 'tsunami'): 'побережья подвержены цунами',
    ('hazards', 'typhoon'): 'бывают тайфуны',
    ('hazards', 'mudflow'): 'часто сходят сели',
    ('hazards', 'avalanche'): 'велика лавинная опасность',
    ('hazards', 'drought'): 'часты засухи и суховеи',
    ('hazards', 'dust_storm'): 'бывают пыльные бури',
    ('hazards', 'flood_spring'): 'часты весенние наводнения',
    ('hazards', 'surge_flood'): 'бывают нагонные наводнения',
    ('arctic', True): 'часть территории лежит за Северным полярным кругом',
}


PICK_NOM = {  # показатель → (именительный падеж, «наибольший», «наименьший») для вопроса «в которых … наибольшая»
    'density': ('средняя плотность населения', 'наибольшая', 'наименьшая'),
    'pop': ('численность населения', 'наибольшая', 'наименьшая'),
    'area': ('площадь территории', 'наибольшая', 'наименьшая'),
    'urban': ('доля городского населения', 'наибольшая', 'наименьшая'),
}

TAG_FIELD = {  # поле со списком тегов → окончание вопроса «…, в которых …»
    'industries': 'одна из отраслей специализации — {}',
    'tags': 'развита отрасль «{}»',
    'plants': 'работает крупная {}',
    'resources': 'добывают или есть крупные запасы: {}',
    'seas': 'территория имеет выход к морю: {}',
    'borders': 'проходит государственная граница с государством: {}',
    'zones': 'есть природная зона «{}»',
}


TAG_INTRO = {  # практическая вводная, как в КИМ
    ('hazards', 'permafrost'): 'При строительстве домов и дорог в некоторых регионах приходится учитывать особые свойства грунтов. ',
    ('hazards', 'seismic'): 'В ряде регионов здания возводят по нормам сейсмостойкого строительства. ',
    ('hazards', 'mudflow'): 'Для защиты посёлков в горных долинах строят противоселевые дамбы. ',
    ('hazards', 'avalanche'): 'На горных дорогах и курортах работают службы противолавинной защиты. ',
    ('hazards', 'drought'): 'Для защиты посевов от засух создают лесополосы и оросительные системы. ',
    ('hazards', 'flood_spring'): 'Ежегодно весной МЧС готовится к подъёму воды в реках. ',
    ('hazards', 'surge_flood'): 'В устьях некоторых рек при сильном ветре с моря вода поднимается и затапливает побережье. ',
    ('hazards', 'dust_storm'): 'Сильные ветры в засушливых районах поднимают в воздух частицы почвы. ',
    ('hazards', 'typhoon'): 'Летом и в начале осени сюда приходят тропические циклоны. ',
}
COMPOSITE = {'Тюменская область', 'Архангельская область'}   # включают автономные округа — ответ неоднозначен


def geo_point(tab, name):
    """Координаты объекта таблицы (центр субъекта или город) для правила «далёких» неверных вариантов."""
    G = FACTS['geo']
    if tab == 'ru_regions':
        r = G['ru_regions'].get(name, {})
        s_ = G['ru_subjects'].get(r.get('wd_name', name), {})
        return (s_['center_lat'], s_['center_lon']) if 'center_lat' in s_ else None
    if tab == 'city_industries':
        c = G['ru_cities'].get(name)
        if c:
            return (c['lat'], c['lon'])
        subj = G['city_industries'][name].get('subject')
        return geo_point('ru_regions', subj) if subj else None
    return None


def tag_rows(tab, field, tag):
    rows = geo_rows(tab)
    def has(r):
        v = r.get(field)
        return tag in v if isinstance(v, list) else v == tag
    return rows, has


def gen_d_pick(rng, args, topic='dict'):
    """Выбрать k из n (ЕГЭ гео 6, 9; ОГЭ 14, 25, 27): по тегу (field=tag) или по крайним значениям показателя."""
    (tab, field, *rest), kw = parse_args(args)
    k, n = int(kw.get('k', 2)), int(kw.get('n', 5))
    noun = kw.get('noun', 'субъекта' if tab.startswith('ru_') else 'страны')
    if rest:                                          # теговый режим
        tag = rest[0]
        tag_v = True if tag == 'true' else tag
        rows, has = tag_rows(tab, field, tag_v)
        rows = geo_filter(tab, rows, kw)
        minor = lambda r_: tag_v in (r_.get(field + '_minor') or []) or (field == 'tags' and tag_v in (r_.get('tags_minor') or []))
        rows = {x: r_ for x, r_ in rows.items() if not minor(r_) and not r_.get('school') is False}   # второстепенное — ни «да», ни «нет»
        yes = [r for r in rows if has(rows[r])]
        no = [r for r in rows if not has(rows[r]) and not rows[r].get('new')]
        yes = [r for r in yes if not rows[r].get('new')]
        if len(yes) < k or len(no) < n - k:
            raise Skip(f'{tab}.{field}={tag}')
        # теги заданы только положительно («где есть»), поэтому неверные варианты берём далеко от всех «да»:
        # иначе в них попадают регионы, где явление тоже есть (второй верный ответ)
        far = float(kw.get('far', 500 if tab == 'ru_regions' else 250))
        pts = {x: geo_point(tab, x) for x in yes + no}
        no = [x for x in no if x not in COMPOSITE and pts.get(x) and
              all(pts.get(y) is None or dist_km(pts[x], pts[y]) >= far for y in yes)]
        if len(no) < n - k:
            raise Skip(f'{tab}.{field}={tag}: мало далёких неверных вариантов')
        items = rng.sample(yes, k) + rng.sample(no, n - k)
        rng.shuffle(items)
        good = [i for i, x in enumerate(items) if x in yes]
        phrase = TAG_Q.get((field, tag_v)) or TAG_FIELD.get(field, 'есть признак «{}»').format(tag)
        intro = TAG_INTRO.get((field, tag_v), '')
        many_word = {2: 'двух', 3: 'трёх'}.get(k, str(k))
        plural = {'субъекта': 'субъектов России', 'города': 'городов', 'страны': 'стран'}.get(noun, noun)
        q = f'{intro}В каких {many_word} из перечисленных {plural} {phrase}? Запишите цифры, под которыми они указаны'
        e = 'Верно: ' + ', '.join(items[i] for i in good) + '.'
        return many_card(topic, q + '.', items, good, e, {'eng': 'd_pick', 'tab': tab, 'field': field, 'tag': tag_v, 'items': items})
    what, label, unit, srcname = ORDER_Q[(tab, field)]
    rows = geo_filter(tab, geo_rows(tab), kw)
    vals = {x: geo_value(tab, r, field) for x, r in rows.items()}
    vals = {x: v for x, v in vals.items() if v is not None and v[0] is not None}
    if len(vals) < n + 2:
        raise Skip(f'{tab}.{field}: мало данных')
    top = kw.get('max') or (not kw.get('min') and rng.random() < 0.5)
    gap = float(kw.get('gap', 1.25))
    for _ in range(80):
        items = rng.sample(list(vals), n)
        s = sorted(items, key=lambda x: vals[x][0], reverse=top)
        a, b = vals[s[k - 1]][0], vals[s[k]][0]
        lo, hi = min(a, b), max(a, b)
        if not (lo > 0 and hi >= lo * gap):
            continue
        good = [i for i, x in enumerate(items) if x in s[:k]]
        nom = PICK_NOM.get(field)
        if nom:
            q = f'Выберите {k} {noun}, в которых {nom[0]} {nom[1] if top else nom[2]}. Запишите цифры, под которыми они указаны.'
        else:
            q = f'Выберите {k} {noun} с {"наибольшим" if top else "наименьшим"} значением показателя «{label}». Запишите цифры, под которыми они указаны.'
        e = '; '.join(f'{x} — {fmt(Fraction(str(vals[x][0])), 1)} {unit}' for x in items) + f' ({srcname}).'
        return many_card(topic, q, items, good, e, {'eng': 'd_pick', 'tab': tab, 'field': field, 'top': top, 'k': k, 'items': items})
    raise Skip(f'{tab}.{field}')


def check_d_pick(c):
    rows = geo_rows(c['tab'])
    if 'tag' in c:
        _, has = tag_rows(c['tab'], c['field'], c['tag'])
        return [str(i + 1) for i, x in enumerate(c['items']) if has(rows[x])]
    v = {x: geo_value(c['tab'], rows[x], c['field'])[0] for x in c['items']}
    best = sorted(c['items'], key=lambda x: v[x], reverse=c['top'])[:c['k']]
    return [str(i + 1) for i, x in enumerate(c['items']) if x in best]


def dist_km(a, b):
    import math
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    d = math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(math.radians(lo1 - lo2))))
    return 6371 * d


def gen_d_coords(rng, args, topic='dict'):
    """Координаты → объект (ЕГЭ гео 1, ОГЭ 7): центр субъекта РФ или столица страны; варианты — ближайшие соседи."""
    (tab,), kw = parse_args(args)
    rows = geo_rows(tab)
    pts = {}
    for k, r in rows.items():
        if tab == 'ru_subjects' and 'center_lat' in r and r.get('center'):
            pts[k] = (r['center_lat'], r['center_lon'])
        elif tab == 'capitals' and 'lat' in r:
            pts[k] = (r['lat'], r['lon'])
    x = rng.choice(list(pts))
    lat, lon = round(pts[x][0]), round(pts[x][1])
    near = sorted((p for p in pts if p != x), key=lambda p: dist_km(pts[x], pts[p]))
    wrong = [p for p in near if dist_km((lat, lon), pts[p]) > dist_km((lat, lon), pts[x]) + 150][:3]
    if len(wrong) < 3:
        raise Skip(x)
    o, a = one(rng, x, wrong)
    ns = 'с. ш.' if lat >= 0 else 'ю. ш.'
    ew = 'в. д.' if lon >= 0 else 'з. д.'
    what = 'столицей (административным центром) какого субъекта Российской Федерации' if tab == 'ru_subjects' else 'столицей какого государства'
    q = f'Город имеет координаты {abs(lat)}° {ns} и {abs(lon)}° {ew} Этот город является {what}?'
    if kw.get('city') and tab == 'capitals':          # ОГЭ 7: назвать сам город-столицу
        caps = {r['name']: next(iter(r['capital_coords'])) for r in FACTS['geo']['countries'].values() if len(r.get('capital_coords', {})) == 1}
        o = [{'id': z['id'], 't': caps[z['t']]} for z in o]
        q = (f'Определите по координатам {abs(lat)}° {ns} и {abs(lon)}° {ew} столицу государства, '
             'которая имеет такие географические координаты.')
    e = f'{x}: центр {pts[x][0]}°, {pts[x][1]}°; ближе всех к точке ({lat}°, {lon}°).'
    return card('one', topic, q, a, e, {'eng': 'd_coords', 'tab': tab, 'pt': [lat, lon], 'city': bool(kw.get('city')),
                                         'opts': [z['t'] for z in o]}, o=o)


def check_d_coords(c):
    rows = geo_rows(c['tab'])
    def pt(k):
        r = rows[k]
        return (r['center_lat'], r['center_lon']) if c['tab'] == 'ru_subjects' else (r['lat'], r['lon'])
    if c['tab'] == 'capitals' and c.get('city'):
        caps = {next(iter(r['capital_coords'])): r['name'] for r in FACTS['geo']['countries'].values() if len(r.get('capital_coords', {})) == 1}
        d = [dist_km(tuple(c['pt']), pt(caps[k])) for k in c['opts']]
    else:
        d = [dist_km(tuple(c['pt']), pt(k)) for k in c['opts']]
    return '123456'[d.index(min(d))]


CLUE = {  # поле субъекта → формулировка признака
    'fo': 'входит в {} федеральный округ',
    'borders': 'граничит с государством {}',
    'seas': 'имеет выход к морю: {}',
    'arctic': 'часть территории лежит за Северным полярным кругом',
    'industries': 'одна из отраслей специализации — {}',
    'zones': 'на территории есть природная зона «{}»',
    'resources': 'есть месторождения: {}',
    'hazards_txt': '{}',
}
HAZ_TXT = {'permafrost': 'распространена многолетняя мерзлота', 'seismic': 'высокая сейсмичность', 'volcano': 'есть действующие вулканы',
           'tsunami': 'побережье подвержено цунами', 'typhoon': 'бывают тайфуны', 'mudflow': 'сходят сели', 'avalanche': 'есть лавиноопасные горы',
           'drought': 'часты засухи', 'dust_storm': 'бывают пыльные бури', 'flood_spring': 'часты весенние наводнения', 'surge_flood': 'бывают нагонные наводнения'}


def region_clues(r):
    out = [('fo', r['fo'])] if r.get('fo') else []
    for f in ('borders', 'seas', 'industries', 'zones', 'resources'):
        out += [(f, v) for v in r.get(f, [])]
    out += [('hazards', h) for h in r.get('hazards', []) if h in HAZ_TXT]
    if r.get('arctic'):
        out.append(('arctic', True))
    if not r.get('seas'):
        out.append(('seas', None))
    return out


def clue_minor(r, f, v):
    """Признак есть, но второстепенный (industries_minor и т. п.) — такой субъект не годится ни в ответ, ни в дистрактор."""
    return isinstance(v, str) and v in (r.get(f + '_minor') or [])


def clue_ok(r, f, v):
    if f == 'fo':
        return r.get('fo') == v
    if f == 'arctic':
        return bool(r.get('arctic'))
    if f == 'seas' and v is None:
        return not r.get('seas')
    return v in r.get(f, [])


def clue_text(f, v):
    if f == 'hazards':
        return HAZ_TXT[v]
    if f == 'seas' and v is None:
        return 'не имеет выхода к морю'
    return CLUE[f].format(v)


def gen_d_region(rng, args, topic='dict'):
    """ЕГЭ гео 18, 21; ОГЭ 21: субъект РФ (или экономический район) по описанию из 3–5 признаков."""
    (tab, *rest), kw = parse_args(args)
    R = {k: v for k, v in FACTS['geo'][tab].items() if not v.get('new')}
    econ = 'econ' in rest
    for _ in range(100):
        x = rng.choice(list(R))
        clues = region_clues(R[x])
        rng.shuffle(clues)
        chosen = []
        for c in clues:
            chosen.append(c)
            fit = [k for k, r in R.items() if all(clue_ok(r, *cc) for cc in chosen)]
            target = {R[k]['econ'] for k in fit} if econ else set(fit)
            if len(target) == 1 and len(chosen) >= 3:
                break
        else:
            continue
        if len(chosen) > 5:
            continue
        desc = '; '.join(clue_text(*c) for c in chosen)
        if econ:
            right = R[x]['econ']
            wrong = rng.sample(sorted({r['econ'] for r in R.values()} - {right}), 3)
            o, a = one(rng, right, wrong)
            q = f'Субъект Российской Федерации: {desc}. К какому экономическому району он относится?'
        else:
            near = [k for k in R if k != x and R[k]['econ'] == R[x]['econ']] + list(R[x].get('neighbors', []))
            near = [k for k in dict.fromkeys(near) if k in R and k != x and not any(clue_minor(R[k], *cc) for cc in chosen)]
            if len(near) < 3:
                near += rng.sample([k for k in R if k != x and k not in near], 3 - len(near))
            o, a = one(rng, x, rng.sample(near, 3))
            q = f'Определите субъект Российской Федерации по описанию: {desc}.'
        return card('one', topic, q, a, f'{x}: {desc}.', {'eng': 'd_region', 'tab': tab, 'econ': econ,
                    'clues': chosen, 'opts': [z['t'] for z in o]}, o=o)
    raise Skip(tab)


def check_d_region(c):
    R = FACTS['geo'][c['tab']]
    fit = [k for k, r in R.items() if not r.get('new') and all(clue_ok(r, f, v) for f, v in c['clues'])]
    if c['econ']:
        ans = {R[k]['econ'] for k in fit}
        ok = [i for i, t in enumerate(c['opts']) if t in ans]
    else:
        ok = [i for i, t in enumerate(c['opts']) if t in fit]
    return '123456'[ok[0]] if len(ok) == 1 else None


def gen_d_district(rng, args, topic='dict'):
    """ОГЭ гео 27: отрасли специализации экономического района (2 из 5)."""
    (tab,), kw = parse_args(args)
    D = FACTS['geo'][tab]
    x = rng.choice(list(D))
    own = D[x]['industries']
    other = sorted({b for d, v in D.items() for b in v['industries']} - set(own))
    k, n = int(kw.get('k', 2)), int(kw.get('n', 5))
    if len(own) < k or len(other) < n - k:
        raise Skip(x)
    items = rng.sample(own, k) + rng.sample(other, n - k)
    rng.shuffle(items)
    gi = [i for i, b in enumerate(items) if b in own]
    q = f'Какие из перечисленных отраслей относятся к отраслям специализации района «{x}»? Запишите цифры, под которыми они указаны.'
    return many_card(topic, q, items, gi, f'{x}: ' + ', '.join(own) + '.', {'eng': 'd_district', 'tab': tab, 'x': x, 'items': items})


def check_d_district(c):
    own = FACTS['geo'][c['tab']][c['x']]['industries']
    return [str(i + 1) for i, b in enumerate(c['items']) if b in own]


CONTINENTS = ['Австралия', 'Антарктида', 'Африка', 'Евразия (Азия)', 'Евразия (Европа)', 'Северная Америка', 'Южная Америка']
OCEANS = ['Атлантический', 'Индийский', 'Тихий', 'Северный Ледовитый']


def obj_place(r):
    """Материк или океан объекта, если он однозначен (проливы между двумя морями и т. п. не берём)."""
    v = (r.get('continent_ocean') or '').replace(' океан', '')
    return v if v in CONTINENTS or v in OCEANS else None


def gen_d_objone(rng, args, topic='dict'):
    """ЕГЭ гео 4, 21; ОГЭ 1, 2: где находится объект номенклатуры — материк/океан (1 из 4)."""
    (tab,), kw = parse_args(args)
    rows = geo_rows(tab)
    x = rng.choice([k for k, r in rows.items() if obj_place(r)])
    right = obj_place(rows[x])
    pool = CONTINENTS if right in CONTINENTS else OCEANS
    o, a = one(rng, right, rng.sample([v for v in pool if v != right], 3))
    q = f'Где находится объект «{x}» ({rows[x]["class"]})? Выберите материк или океан.'
    return card('one', topic, q, a, f'{x} — {right}.', {'eng': 'd_objone', 'tab': tab, 'x': x, 'opts': [z['t'] for z in o]}, o=o)


def check_d_objone(c):
    v = obj_place(geo_rows(c['tab'])[c['x']])
    return '123456'[c['opts'].index(v)]


def gen_d_producers(rng, args, topic='dict'):
    """ЕГЭ гео 9 (мир): три страны из шести, входящие в пятёрку крупнейших производителей/экспортёров продукта."""
    (group,), kw = parse_args(args)
    P = FACTS['geo']['producers']
    keys = [k for k in kw.get('p', '').split('+') if k in P] or list(P)
    k = rng.choice([x for x in keys if len([t for t in P[x]['top'] if t.get('country')]) >= 5])
    top = [t['country'] for t in P[k]['top'] if t.get('country')][:5]
    pool = sorted({r['name'] for r in FACTS['geo']['country_tags'].values()} - set(top))
    items = rng.sample(top, 3) + rng.sample(pool, 3)
    rng.shuffle(items)
    gi = [i for i, x in enumerate(items) if x in top]
    T = P[k]
    q = (f'Какие три страны из перечисленных входят в пятёрку мировых лидеров: {T["title"].lower()} — {T["role"]} '
         f'({T["year"]} г.)? Запишите цифры, под которыми они указаны.')
    e = 'Пятёрка: ' + ', '.join(top) + f' ({T["src"][0].split(",")[0]}).'
    return many_card(topic, q, items, gi, e, {'eng': 'd_producers', 'k': k, 'items': items})


def check_d_producers(c):
    top = [t['country'] for t in FACTS['geo']['producers'][c['k']]['top'] if t.get('country')][:5]
    return [str(i + 1) for i, x in enumerate(c['items']) if x in top]


def chron_age(ev):
    G = FACTS['geo']['geochron']
    if ev.get('period'):
        per = {p['name']: p for p in G['periods'] + G.get('precambrian_periods', [])}
        p = per.get(ev['period'])
        if p:
            return p['start_ma'], p['end_ma']
    era = {e['name']: e for e in G['eras']}[ev['era']]
    return era['start_ma'], era['end_ma']


def gen_d_chron(rng, args, topic='dict'):
    """ЕГЭ гео 13: события истории Земли от древних к молодым; интервалы событий не перекрываются."""
    mode = args[0]                                     # mixed | same | pre
    ev = [e for e in FACTS['geo']['geochron']['events'] if e.get('era')]
    for _ in range(300):
        pick = rng.sample(ev, 3)
        span = [chron_age(e) for e in pick]
        s = sorted(span, reverse=True)
        if any(a[1] < b[0] for a, b in zip(s, s[1:])):     # интервалы пересекаются — порядок неоднозначен
            continue
        eras = [e['era'] for e in pick]
        pre = sum(e['era'] in ('архейская', 'протерозойская') for e in pick)
        if mode == 'mixed' and len(set(eras)) < 3:
            continue
        if mode == 'same' and len(set(eras)) > 2:
            continue
        if mode == 'pre' and pre != 1:
            continue
        old_first = rng.random() < 0.6
        order = sorted(range(3), key=lambda i: span[i][0], reverse=old_first)
        q = f'Расположите события в порядке {"от самого древнего к самому молодому" if old_first else "от самого молодого к самому древнему"}'
        e = '; '.join(f'{x["text"]} — {x.get("period") or x["era"]}' for x in pick) + ' (шкала ICS 2024).'
        return seq_card(topic, q, [x['text'] for x in pick], order, e, {'eng': 'd_chron', 'texts': [x['text'] for x in pick], 'old': old_first})
    raise Skip(mode)


def check_d_chron(c):
    ev = {e['text']: e for e in FACTS['geo']['geochron']['events']}
    start = [chron_age(ev[t])[0] for t in c['texts']]
    return ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: start[i], reverse=c['old']))


COUNTRY_CLUE = {
    'part': 'расположена в регионе: {}', 'gov': 'форма правления — {}', 'structure': 'форма устройства — {}',
    'coast': 'по положению относительно моря — {}', 'oceans': 'омывается водами океана: {}', 'groups': 'входит в объединение: {}',
    'language': 'государственный язык — {}', 'special': '{}',
}


def country_clues(r):
    out = []
    for f in ('part', 'gov', 'structure', 'coast'):
        if r.get(f):
            out.append((f, r[f]))
    for f in ('groups',):              # язык и океан — прямые подсказки, в КИМ их не дают
        out += [(f, v) for v in r.get(f) or []]
    return out


def ct_ok(r, f, v):
    x = r.get(f)
    return v in x if isinstance(x, list) else x == v


def gen_d_country(rng, args, topic='dict'):
    """ЕГЭ гео 17, ОГЭ 21: страна по описанию (3–5 признаков + один характерный факт), 1 из 4."""
    C = FACTS['geo']['country_tags']
    for _ in range(100):
        iso = rng.choice(list(C))
        r = C[iso]
        cl = country_clues(r)
        rng.shuffle(cl)
        chosen = []
        for c in cl:
            chosen.append(c)
            fit = [k for k, x in C.items() if all(ct_ok(x, *cc) for cc in chosen)]
            if len(fit) <= 3 and len(chosen) >= 3:
                break
        if len(chosen) > 4 or not r.get('special'):
            continue
        sp_ = rng.choice(r['special'])
        fit = [k for k, x in C.items() if all(ct_ok(x, *cc) for cc in chosen)]
        others = [k for k in C if k != iso and C[k].get('part') == r.get('part')] or [k for k in C if k != iso]
        wrong = [k for k in fit if k != iso] + [k for k in others if k not in fit]
        if len(wrong) < 3:
            continue
        wrong = wrong[:3] if len(fit) > 1 else rng.sample(wrong, 3)
        # характерный факт не должен подходить к другим вариантам (у соседних стран бывают одинаковые формулировки)
        if any(all(ct_ok(C[k], *cc) for cc in chosen) and sp_ in (C[k].get('special') or []) for k in wrong):
            continue
        o, a = one(rng, r['name'], [C[k]['name'] for k in wrong])
        desc = '; '.join(COUNTRY_CLUE[f].format(v) for f, v in chosen) + f'; {sp_}'
        q = f'Определите страну по описанию: {desc}.'
        return card('one', topic, q, a, f'{r["name"]}.', {'eng': 'd_country', 'clues': chosen, 'special': sp_,
                    'opts': [z['t'] for z in o]}, o=o)
    raise Skip('country')


def check_d_country(c):
    C = {x['name']: x for x in FACTS['geo']['country_tags'].values()}
    ok = [i for i, t in enumerate(c['opts'])
          if all(ct_ok(C[t], f, v) for f, v in c['clues']) and c['special'] in (C[t].get('special') or [])]
    return '123456'[ok[0]] if len(ok) == 1 else None


def gen_d_city(rng, args, topic='dict'):
    """ЕГЭ гео 21: в каком субъекте РФ находится город (1 из 4, варианты — соседние субъекты)."""
    S = FACTS['geo']['ru_subjects']
    cities = {k: v for k, v in FACTS['geo']['ru_cities'].items() if isinstance(v['subject'], str) and v['subject'] in S
              and S[v['subject']].get('center') != k and 'center_lat' in S[v['subject']]}
    x = rng.choice(list(cities))
    subj = cities[x]['subject']
    pt = (cities[x]['lat'], cities[x]['lon'])
    near = sorted((s for s in S if s != subj and 'center_lat' in S[s]), key=lambda s: dist_km(pt, (S[s]['center_lat'], S[s]['center_lon'])))[:3]
    o, a = one(rng, subj, near)
    q = f'В каком субъекте Российской Федерации находится город {x}?'
    return card('one', topic, q, a, f'{x} — {subj}.', {'eng': 'd_city', 'x': x, 'opts': [z['t'] for z in o]}, o=o)


def check_d_city(c):
    return '123456'[c['opts'].index(FACTS['geo']['ru_cities'][c['x']]['subject'])]


STMT_Q = {  # о чём говорится в верных высказываниях — формулировка стема КИМ
    'urbanization': 'о процессе урбанизации', 'suburbanization': 'о процессе субурбанизации', 'migration': 'о миграциях населения',
    'natural_reproduction': 'о естественном движении населения', 'demographic_policy': 'о демографической политике',
    'aging': 'о старении населения', 'integration': 'о процессах экономической интеграции', 'globalization': 'о глобализации',
    'specialization': 'о международной специализации производства', 'river_regime': 'о режиме реки', 'river_feeding': 'о питании реки',
    'climate': 'о климате', 'weather': 'о погоде', 'tectonics': 'о проявлениях внутренних процессов, формирующих рельеф',
    'erosion': 'о проявлениях внешних процессов, формирующих рельеф', 'rational_use': 'о рациональном природопользовании',
    'irrational_use': 'о нерациональном природопользовании',
}


def gen_d_statements(rng, args, topic='dict'):
    """Высказывания о процессе (ЕГЭ гео 12, ОГЭ 15, 22): свой банк с тегами; k верных из n.
    Высказывания части явления (субурбанизация ⊂ урбанизация, near_ok: false) и помеченные not_near неверными не даём."""
    (ref, tag), kw = parse_args(args)
    ns, key = ref.split('/', 1)
    B = FACTS[ns][key]
    k, n = int(kw.get('k', rng.choice([2, 3]))), int(kw.get('n', 5))
    near = [t for t in kw.get('near', '').split('+') if t in B] or [t for t in B if t != tag]
    near = [t for t in near if not (B[t].get('near_ok') is False and B[t].get('part_of') == tag)]
    good = rng.sample(B[tag]['items'], k)
    bad_pool = [s for t in near for s in B[t]['items'] if s not in set((B[t].get('not_near') or {}).get(tag, []))
                and s not in B[tag]['items']]
    if len(bad_pool) < n - k:
        raise Skip(tag)
    bad = rng.sample(bad_pool, n - k)
    items = good + bad
    rng.shuffle(items)
    gi = [i for i, s in enumerate(items) if s in good]
    about = STMT_Q.get(tag, f'о явлении «{B[tag]["title"]}»')
    q = f'Выберите все высказывания, в которых говорится {about}. Запишите цифры, под которыми они указаны.'
    if tag in ('rational_use', 'irrational_use'):
        kind = 'рационального' if tag == 'rational_use' else 'нерационального'
        q = (f'Какие {"два" if k == 2 else "три"} из перечисленных видов деятельности являются примерами {kind} природопользования? '
             'Запишите цифры, под которыми они указаны.')
    return many_card(topic, q, items, gi, 'Верно: ' + ' '.join(items[i] for i in gi),
                     {'eng': 'd_statements', 'ref': ref, 'tag': tag, 'items': items})


def check_d_statements(c):
    ns, key = c['ref'].split('/', 1)
    B = FACTS[ns][key]
    return [str(i + 1) for i, s in enumerate(c['items']) if s in B[c['tag']]['items']]



# ---- новые параметрические генераторы по прототипам (этап «прототипы → аналоги»)

# график/таблица опыта (ЕГЭ 21, ОГЭ 4): свои контексты; утверждения — только проверяемые по данным
# (фактор, ед., значения x, показатель, ед., форма, категория, (мин, макс) показателя, знаков после запятой)
# диапазоны — типичные учебные/справочные значения
GRAPH_CTX = [
    ('температура', '°C', [5, 10, 15, 20, 25, 30, 35, 40], 'скорость фотосинтеза элодеи', 'пузырьков O₂ в минуту', 'bell', 'plant', (3, 42), 0),
    ('температура', '°C', [0, 10, 20, 30, 40, 50, 60], 'активность амилазы слюны', 'усл. ед.', 'bell', 'human', (5, 100), 0),
    ('pH среды', '', [1, 2, 3, 4, 5, 6, 7, 8], 'активность пепсина', 'усл. ед.', 'bell', 'human', (2, 100), 0),
    ('возраст', 'лет', [10, 20, 30, 40, 50, 60, 70], 'жизненная ёмкость лёгких', 'л', 'bell', 'human', (2.4, 4.8), 1),
    ('время после приёма пищи', 'ч', [0, 0.5, 1, 1.5, 2, 2.5, 3], 'концентрация глюкозы в крови', 'ммоль/л', 'bell', 'human', (4.4, 8.2), 1),
    ('доза азотного удобрения', 'кг/га', [0, 30, 60, 90, 120, 150, 180], 'урожайность пшеницы', 'ц/га', 'bell', 'plant', (18, 46), 0),
    ('температура', '°C', [0, 5, 10, 15, 20, 25, 30, 35], 'скорость прорастания семян гороха', '% проросших за 5 суток', 'bell', 'plant', (4, 96), 0),
    ('освещённость', 'тыс. лк', [0, 5, 10, 15, 20, 25, 30], 'интенсивность фотосинтеза', 'мг CO₂ на 100 см² листа в час', 'sat', 'plant', (1, 24), 0),
    ('концентрация CO₂ в воздухе', '%', [0.01, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12], 'интенсивность фотосинтеза', 'усл. ед.', 'sat', 'plant', (8, 60), 0),
    ('концентрация субстрата', 'ммоль/л', [1, 2, 4, 6, 8, 10, 12], 'скорость ферментативной реакции', 'мкмоль/мин', 'sat', 'enzyme', (6, 58), 0),
    ('время бега', 'мин', [0, 2, 4, 6, 8, 10, 12], 'частота сердечных сокращений', 'уд./мин', 'sat', 'human', (72, 168), 0),
    ('время откорма', 'недель', [0, 4, 8, 12, 16, 20, 24], 'масса тела поросёнка', 'кг', 'sat', 'animal', (20, 108), 0),
    ('время физической нагрузки', 'мин', [0, 5, 10, 15, 20, 25, 30], 'частота дыхания', 'вдохов в минуту', 'sat', 'human', (16, 42), 0),
    ('температура воды', '°C', [0, 5, 10, 15, 20, 25, 30], 'содержание растворённого кислорода', 'мг/л', 'decline', 'eco', (7.6, 14.6), 1),
    ('концентрация раствора соли', '%', [0, 0.5, 1, 1.5, 2, 3, 4], 'масса кусочка картофеля после опыта', 'г', 'decline', 'plant', (7.4, 10.8), 1),
    ('концентрация пестицида', 'мг/л', [0, 1, 2, 3, 4, 5, 6], 'выживаемость личинок комаров', '%', 'decline', 'eco', (4, 96), 0),
    ('глубина', 'м', [0, 5, 10, 20, 30, 40, 50], 'интенсивность фотосинтеза водорослей', 'усл. ед.', 'decline', 'eco', (3, 100), 0),
    ('возраст', 'лет', [20, 30, 40, 50, 60, 70, 80], 'верхняя граница слышимых частот', 'кГц', 'decline', 'human', (8, 19), 0),
    ('время задержки дыхания', 'с', [0, 10, 20, 30, 40, 50, 60], 'насыщение крови кислородом', '%', 'decline', 'human', (88, 98), 0),
    ('время после посева', 'ч', [0, 2, 4, 6, 8, 10, 12], 'число бактерий в колонии', 'тыс.', 'grow', 'micro', (1, 900), 0),
]


def graph_series(rng, shape, n, lo=5, hi=90, dec=0):
    """Ряд заданной формы в реалистичном диапазоне [lo, hi]; монотонные участки строгие после округления."""
    step = Fraction(1, 10 ** dec)
    grid = [Fraction(lo) + i * step for i in range(int((Fraction(str(hi)) - Fraction(str(lo))) / step) + 1)]
    rnd = lambda v: round(float(v), dec) if dec else int(v)
    if shape == 'grow':
        v = [rng.randint(2, 9)]
        for _ in range(n - 1):
            v.append(v[-1] * 2 if rng.random() < 0.75 else v[-1] * 2 + rng.randint(1, 5))
        return v
    if shape == 'bell':
        peak = rng.randrange(2, n - 2)
        top = grid[-1] - rng.randint(0, max(1, len(grid) // 12)) * step
        below = [g for g in grid if g < top]
        up = sorted(rng.sample(below, peak))
        down = sorted(rng.sample(below, n - peak - 1), reverse=True)
        return [rnd(x) for x in up + [top] + down]
    if shape == 'sat':
        k = rng.randrange(3, n - 1)                    # плато с точки k
        up = sorted(rng.sample(grid[:-1], k))
        top = rng.choice([g for g in grid if g > up[-1]])
        return [rnd(x) for x in up + [top] * (n - k)]
    k = rng.choice([n, n, n - 1, n - 2])               # decline: иногда плато в конце
    down = sorted(rng.sample(grid[1:], k), reverse=True)
    return [rnd(x) for x in down + [down[-1]] * (n - k)]


def graph_statements(xs, ys, fx, fy, xu, yu=''):
    """(текст, верно по данным?) — утверждения в духе КИМ, проверяемые по точкам графика."""
    n = len(xs)
    X = lambda i: f'{fmt(Fraction(str(xs[i])))}{" " + xu if xu else ""}'
    V = lambda v: f'{fmt(Fraction(str(v)))}{" " + yu if yu and len(yu) < 12 else ""}'
    Y = cap(fy)
    MX, MN = short_adj(fy, 'максимальный'), short_adj(fy, 'минимальный')
    imax = max(range(n), key=lambda i: ys[i])
    imin = min(range(n), key=lambda i: ys[i])
    out = []
    if ys.count(ys[imax]) == 1:
        out.append((f'{Y} {MX} при значении фактора {X(imax)}', True))
    else:                                              # плато: «максимальна в точке начала плато» — неоднозначно, берём ложную формулировку
        out.append((f'{Y} {MX} только при значении фактора {X(n - 1)}', False))
    if ys.count(ys[imin]) == 1:
        out.append((f'{Y} {MN} при значении фактора {X(imin)}', True))
    for alt in (imax - 1, imax + 1, imax + 2):
        if 0 <= alt < n and ys[alt] < ys[imax]:
            out.append((f'{Y} {MX} при значении фактора {X(alt)}', False))
            break
    inc = all(p < q for p, q in zip(ys, ys[1:]))
    dec_ = all(p > q for p, q in zip(ys, ys[1:]))
    out.append((f'{Y} возрастает на всём изученном интервале', inc))
    out.append((f'{Y} снижается на всём изученном интервале', dec_))
    flat = [i for i in range(n - 1) if ys[i] == ys[i + 1]]
    if flat:
        a = flat[0]
        out.append((f'{Y} не изменяется при значениях фактора от {X(a)} до {X(n - 1)}', all(ys[i] == ys[a] for i in range(a, n))))
        out.append((f'{Y} перестаёт изменяться начиная со значения фактора {X(a)}', True))
        if a > 1:
            out.append((f'{Y} не изменяется при значениях фактора от {X(a - 1)} до {X(n - 1)}', False))
    else:
        a = rng_mid = n // 2
        out.append((f'{Y} не изменяется при значениях фактора от {X(a)} до {X(n - 1)}', False))
    for a in range(0, n - 2, 2):
        seg = ys[a:a + 3]
        if all(p < q for p, q in zip(seg, seg[1:])):
            out.append((f'при увеличении фактора от {X(a)} до {X(a + 2)} {fy} возрастает', True))
            out.append((f'при увеличении фактора от {X(a)} до {X(a + 2)} {fy} снижается', False))
        elif all(p > q for p, q in zip(seg, seg[1:])):
            out.append((f'при увеличении фактора от {X(a)} до {X(a + 2)} {fy} снижается', True))
            out.append((f'при увеличении фактора от {X(a)} до {X(a + 2)} {fy} возрастает', False))
    i = n // 2
    out.append((f'при значении фактора {X(i)} {fy} составляет {V(ys[i])}', True))
    j = (i + 1) % n
    if ys[j] != ys[i]:
        out.append((f'при значении фактора {X(i)} {fy} составляет {V(ys[j])}', False))
    return [(cap(t), ok) for t, ok in out]


def gen_b_graph(rng):
    fx, xu, xs, fy, yu, shape, cat, (lo, hi), dec = rng.choice(GRAPH_CTX)
    ys = graph_series(rng, shape, len(xs), lo, hi, dec)
    sts = graph_statements(xs, ys, fx, fy, xu, yu)
    seen, uniq = set(), []
    for t, ok in sts:
        if t not in seen:
            seen.add(t)
            uniq.append((t, ok))
    good = [t for t, ok in uniq if ok]
    bad = [t for t, ok in uniq if not ok]
    k = rng.choice([2, 2, 3])
    if len(good) < k or len(bad) < 5 - k:
        return gen_b_graph(rng)
    topic_of = lambda t: re.sub(r'(возрастает|снижается|(максимальн|минимальн)\w+( только)? при значении фактора [\d,]+|составляет .*)', '', t)
    for _ in range(60):                # без пар-антонимов об одном интервале: они подсказывают ответ
        items = rng.sample(good, k) + rng.sample(bad, 5 - k)
        if len({topic_of(t) for t in items}) == 5:
            break
    rng.shuffle(items)
    gi = [i for i, t in enumerate(items) if t in good]
    pts = '; '.join(f'({fmt(Fraction(str(x)))}; {fmt(Fraction(str(y)))})' for x, y in zip(xs, ys))
    axes = f'по оси абсцисс — {fx}{" (" + xu + ")" if xu else ""}, по оси ординат — {fy} ({yu})'
    if k == 2:
        q = (f'Изучите график зависимости: {axes}. Точки графика: {pts}. Какие два из приведённых ниже описаний '
             'верно характеризуют данную зависимость? Запишите в ответе цифры, под которыми они указаны.')
    else:
        q = (f'Проанализируйте график: {axes}. Точки графика: {pts}. Выберите все утверждения, которые можно '
             'сформулировать на основании анализа представленных данных. Запишите в ответе цифры, под которыми они указаны.')
    c = many_card('bio-ege-21', q, items, gi, 'По точкам графика: ' + '; '.join(items[i] for i in gi) + '.',
                  {'xs': xs, 'ys': ys, 'fx': fx, 'fy': fy, 'xu': xu, 'yu': yu, 'items': items, 'nk': k, 'shape': shape, 'cat': cat})
    return c


def check_b_graph(c):
    truth = dict(graph_statements(c['xs'], c['ys'], c['fx'], c['fy'], c['xu'], c.get('yu', '')))
    return [str(i + 1) for i, s in enumerate(c['items']) if truth[s]]


# плоидность клеток растений (ЕГЭ 3, 27): кратность набора по стадиям жизненного цикла
PLOIDY = {
    'мха кукушкина льна': {'спора': 1, 'клетка листа (гаметофит)': 1, 'клетка коробочки на ножке (спорофит)': 2,
                           'яйцеклетка': 1, 'зигота': 2, 'клетка ризоида': 1},
    'папоротника щитовника': {'спора': 1, 'клетка заростка': 1, 'клетка листа (вайи)': 2, 'сперматозоид': 1,
                              'зигота': 2, 'клетка корневища': 2},
    'сосны обыкновенной': {'клетка хвои': 2, 'пыльцевое зерно (мужской гаметофит)': 1, 'спермий': 1,
                           'клетка эндосперма семени': 1, 'клетка зародыша семени': 2, 'яйцеклетка': 1},
    'цветкового растения': {'клетка листа': 2, 'спермий': 1, 'яйцеклетка': 1, 'клетка эндосперма семени': 3,
                            'клетка зародыша семени': 2, 'центральная клетка зародышевого мешка': 2,
                            'клетка кожуры семени': 2, 'микроспора': 1},
    'зелёной водоросли улотрикса': {'клетка нити': 1, 'зигота': 2, 'гамета': 1, 'зооспора': 1},
}
PLANT_2N = [12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 36, 40, 42, 48]


def gen_b_ploidy(rng):
    sp = rng.choice(list(PLOIDY))
    cell = rng.choice(list(PLOIDY[sp]))
    k = PLOIDY[sp][cell]
    shown_cell = rng.choice([c for c in PLOIDY[sp] if PLOIDY[sp][c] != k] or [cell])
    n = rng.choice(PLANT_2N) // 2
    given = n * PLOIDY[sp][shown_cell]
    ans = n * k
    q = (f'У {sp} {shown_cell} содержит {agree(given, "хромосома")}. Какое число хромосом содержит {cell}? '
         'В ответе запишите только число.')
    e = f'{cap(shown_cell)} — {PLOIDY[sp][shown_cell]}n = {given}, n = {n}; {cell} — {k}n = {ans}.'
    return card('num', 'bio-ege-3', q, str(ans), e, {'sp': sp, 'cell': cell, 'shown': shown_cell, 'given': given})


def check_b_ploidy(c):
    P = PLOIDY[c['sp']]
    n = Fraction(c['given'], P[c['shown']])
    return str(int(n * P[c['cell']]))


# энергетический обмен (ЕГЭ 3): число АТФ и молекул по этапам (школьная схема: гликолиз 2, кислородный 36)
def gen_b_atp(rng):
    g = rng.randint(2, 30)
    mode = rng.choice(['full', 'glyc', 'o2', 'pyr', 'co2', 'back'])
    if mode == 'full':
        q, ans, e = f'Сколько молекул АТФ образуется при полном окислении {g} молекул глюкозы?', 38 * g, f'38 × {g}'
    elif mode == 'glyc':
        q, ans, e = f'Сколько молекул АТФ образуется при гликолизе {g} молекул глюкозы?', 2 * g, f'2 × {g}'
    elif mode == 'o2':
        q, ans, e = f'Сколько молекул АТФ образуется на кислородном этапе при окислении {g} молекул глюкозы?', 36 * g, f'36 × {g}'
    elif mode == 'pyr':
        q, ans, e = f'Сколько молекул пировиноградной кислоты образуется при гликолизе {g} молекул глюкозы?', 2 * g, f'2 × {g}'
    elif mode == 'co2':
        q, ans, e = f'Сколько молекул углекислого газа выделится при полном окислении {g} молекул глюкозы?', 6 * g, f'6 × {g}'
    else:
        q, ans, e = f'При гликолизе в клетке образовалось {2 * g} молекул АТФ. Сколько молекул глюкозы подверглось гликолизу?', g, f'{2 * g} : 2'
    q += ' В ответе запишите только число.'
    return card('num', 'bio-ege-3', q, str(ans), f'{e} = {ans} (школьная схема: гликолиз 2 АТФ, кислородный этап 36 АТФ на глюкозу).',
                {'g': g, 'mode': mode})


def check_b_atp(c):
    per = {'full': (2 + 36), 'glyc': 2, 'o2': 36, 'pyr': 2, 'co2': 6}
    return str(c['g']) if c['mode'] == 'back' else str(per[c['mode']] * c['g'])


# энергозатраты (ОГЭ 26): свои условные нормы расхода, даются в условии
ACTIVITY = {'бег трусцой': 9, 'езда на велосипеде': 7, 'плавание': 8, 'катание на лыжах': 10, 'игра в футбол': 9,
            'ходьба быстрым шагом': 5, 'игра в волейбол': 5, 'катание на коньках': 7, 'танцы': 6, 'прыжки со скакалкой': 11}


def gen_b_energy(rng):
    act = rng.sample(list(ACTIVITY), 2)
    mins = [rng.choice([15, 20, 25, 30, 40, 45, 60, 90]) for _ in act]
    use = sum(ACTIVITY[a] * m for a, m in zip(act, mins))
    dishes = rng.sample(list(DISHES), 3)
    eat = sum(DISHES[d] for d in dishes)
    mode = rng.choice(['spent', 'balance'])
    rates = '; '.join(f'{a} — {ACTIVITY[a]} ккал/мин' for a in act)
    plan = ' и '.join(f'{a} {m} мин' for a, m in zip(act, mins))
    if mode == 'spent':
        q = f'Подросток занимался: {plan}. Расход энергии: {rates}. Сколько килокалорий он израсходовал? Запишите число.'
        ans, e = use, ' + '.join(f'{ACTIVITY[a]} × {m}' for a, m in zip(act, mins)) + f' = {use} ккал.'
    else:
        menu = '; '.join(f'{d} — {DISHES[d]} ккал' for d in dishes)
        q = (f'Подросток занимался: {plan} (расход: {rates}), затем съел: {menu}. На сколько килокалорий энергия обеда '
             'отличается от затрат на тренировку? Запишите модуль разности числом.')
        ans, e = abs(eat - use), f'Затраты {use} ккал, обед {eat} ккал, разница {abs(eat - use)} ккал.'
    return card('num', 'bio-oge-26', q, str(ans), e, {'act': act, 'mins': mins, 'dishes': dishes, 'mode': mode})


def check_b_energy(c):
    use = 0
    for a, m in zip(c['act'], c['mins']):
        use += ACTIVITY[a] * m
    if c['mode'] == 'spent':
        return str(use)
    return str(abs(sum(DISHES[d] for d in c['dishes']) - use))


# мутация (ЕГЭ 27): замена нуклеотида в матричной цепи → аминокислота до/после
def gen_b_mutation(rng):
    coding = rand_coding(rng, rng.randint(4, 6))
    tmpl = ''.join(DNA_C[b] for b in coding)             # матричная цепь 3'→5' (комплементарна кодирующей)
    codons = [coding[i:i + 3] for i in range(0, len(coding), 3)]
    ci = rng.randrange(len(codons))
    pos = ci * 3 + rng.randrange(3)
    for _ in range(20):
        nb = rng.choice([b for b in 'АТГЦ' if b != tmpl[pos]])
        mt = tmpl[:pos] + nb + tmpl[pos + 1:]
        new_coding = ''.join(DNA_C[b] for b in mt)
        aa_old = CODE[''.join(RNA_FROM_DNA[DNA_C[b]] for b in codons[ci]).replace('Т', 'У')]
        new_codon = new_coding[ci * 3:ci * 3 + 3]
        aa_new = CODE[new_codon.replace('Т', 'У')]
        if aa_new != 'стоп':
            break
    else:
        return gen_b_mutation(rng)
    q = (f'Фрагмент матричной (транскрибируемой) цепи ДНК 3ʹ→5ʹ: {tmpl}. В результате мутации {pos + 1}-й нуклеотид '
         f'заменился на {nb}. Какая аминокислота будет в белке на месте {ci + 1}-й? Используйте таблицу генетического кода.')
    all_aa = sorted({v for v in CODE.values() if v not in ('стоп', aa_new)})
    o, a = one(rng, aa_new, rng.sample(all_aa, 3) if aa_old == aa_new else [aa_old] + rng.sample([x for x in all_aa if x != aa_old], 2))
    e = f'Новый кодон иРНК: {new_codon.replace("Т", "У")} → {aa_new} (было {aa_old}).'
    return card('one', 'bio-ege-27', q, a, e, {'tmpl': tmpl, 'pos': pos, 'nb': nb, 'ci': ci, 'opts': [x['t'] for x in o]}, o=o)


def check_b_mutation(c):
    t = c['tmpl'][:c['pos']] + c['nb'] + c['tmpl'][c['pos'] + 1:]
    rna = ''.join(RNA_FROM_DNA[b] for b in t)             # иРНК 5'→3' комплементарна матрице 3'→5'
    aa = CODE[rna[c['ci'] * 3:c['ci'] * 3 + 3]]
    return '123456'[c['opts'].index(aa)]


# таблица с вычислениями (ОГЭ 25, ЕГЭ 23): свои условные данные
TABLE_CTX = [
    ('Частота пульса школьников (уд./мин) до и после 20 приседаний', ['до нагрузки', 'после нагрузки'], (60, 130)),
    ('Масса проростков фасоли (г) при разном поливе', ['обильный полив', 'умеренный полив'], (5, 40)),
    ('Число колоний бактерий на чашках Петри', ['без антибиотика', 'с антибиотиком'], (3, 90)),
    ('Время реакции (мс) на световой и звуковой сигнал', ['свет', 'звук'], (140, 320)),
    ('Урожай картофеля (кг с делянки)', ['с удобрением', 'без удобрения'], (8, 60)),
]


def gen_b_table_q(rng):
    title, cols, (lo, hi) = rng.choice(TABLE_CTX)
    n = rng.choice([4, 5])
    rows = [[rng.randint(lo, hi) for _ in cols] for _ in range(n)]
    names = [f'проба {i + 1}' for i in range(n)]
    mode = rng.choice(['diffmax', 'mean', 'range'])
    col = rng.randrange(len(cols))
    tab = '; '.join(f'{nm}: ' + ', '.join(f'{c} — {v}' for c, v in zip(cols, r)) for nm, r in zip(names, rows))
    if mode == 'diffmax':
        d = [abs(r[0] - r[1]) for r in rows]
        if d.count(max(d)) > 1:
            return gen_b_table_q(rng)
        ans = str(d.index(max(d)) + 1)
        q = f'{title}. {tab}. В какой пробе разница между столбцами наибольшая? Запишите номер пробы.'
    elif mode == 'mean':
        s = sum(r[col] for r in rows)
        ans = fmt(Fraction(s, n), 1)
        q = f'{title}. {tab}. Найдите среднее значение в столбце «{cols[col]}» (округлите до десятых).'
    else:
        v = [r[col] for r in rows]
        ans = str(max(v) - min(v))
        q = f'{title}. {tab}. Найдите размах (разность наибольшего и наименьшего значений) в столбце «{cols[col]}».'
    return card('num', 'bio-oge-25', q, ans, 'Расчёт по таблице.', {'rows': rows, 'mode': mode, 'col': col})


def check_b_table_q(c):
    R = c['rows']
    if c['mode'] == 'diffmax':
        d = [max(r) - min(r) for r in R]
        return str(d.index(max(d)) + 1)
    v = [r[c['col']] for r in R]
    if c['mode'] == 'mean':
        return fmt(half_up(Fraction(sum(v), len(v)), 1), 1)
    return str(max(v) - min(v))

# ---- новые параметрические генераторы по прототипам географии

def ru_subject_names():
    return sorted(FACTS['geo'].get('ru_subjects', {}) or ['Регион А', 'Регион Б', 'Регион В', 'Регион Г', 'Регион Д'])


INDEX_Q = {  # критерий → (текст, функция по ряду индексов)
    'grow_each': ('объём производства ежегодно увеличивался', lambda r: all(x > 100 for x in r)),
    'fall_each': ('объём производства ежегодно сокращался', lambda r: all(x < 100 for x in r)),
    'fall_last': ('в последнем году объём производства сократился', lambda r: r[-1] < 100),
    'grow_first': ('в первом году объём производства вырос', lambda r: r[0] > 100),
}


def gen_g_index_table(rng):
    """ЕГЭ гео 10: таблица 4 регионов за 3 года — индексы производства (% к предыдущему году) или абсолютные значения;
    вопрос КИМ: в каких регионах показатель ежегодно увеличивался (сокращался). Данные условные, масштаб реалистичный."""
    kind = rng.choice(['ind', 'agr', 'abs'])
    grow = rng.random() < 0.6
    regs = rng.sample(ru_subject_names(), 4)
    y0 = rng.choice([2019, 2020, 2021, 2022])
    years = (y0, y0 + 1, y0 + 2)
    for _ in range(300):
        if kind == 'abs':
            base = rng.randint(300, 4000)
            rows = []
            for _r in regs:
                v, row = base * rng.uniform(0.5, 1.5), []
                for _y in years:
                    v *= 1 + rng.choice([-1, 1]) * rng.uniform(0.004, 0.04)
                    row.append(round(v, 1))
                rows.append(row)
            ok = lambda r: all(q > p for p, q in zip(r, r[1:])) if grow else all(q < p for p, q in zip(r, r[1:]))
        else:
            rows = [[round(rng.choice([rng.uniform(88, 99.9), rng.uniform(100.1, 114)]), 1) for _y in years] for _r in regs]
            ok = lambda r: min(r) > 100 if grow else max(r) < 100
        good = [i for i, r in enumerate(rows) if ok(r)]
        # ловушки: для индексов — ряд, растущий, но ниже 100 (или падающий, но выше 100); ряд с одним провалом
        if kind != 'abs':
            trap = any((all(q > p for p, q in zip(r, r[1:])) and max(r) < 100) if grow else (all(q < p for p, q in zip(r, r[1:])) and min(r) > 100) for r in rows)
        else:
            trap = any(r[-1] > r[0] and not ok(r) for r in rows) if grow else any(r[-1] < r[0] and not ok(r) for r in rows)
        if 1 <= len(good) <= 3 and trap:
            break
    else:
        return gen_g_index_table(rng)
    what = {'ind': 'Индекс промышленного производства (в % к предыдущему году)',
            'agr': 'Индекс производства продукции сельского хозяйства (в % к предыдущему году)',
            'abs': rng.choice(['Численность населения (тыс. чел.)', 'Валовой сбор зерна (тыс. т)', 'Производство молока (тыс. т)'])}[kind]
    tab = '; '.join(f'{i + 1}) {g}: ' + ', '.join(f'{y} г. — {fmt(Fraction(str(v)))}' for y, v in zip(years, r))
                    for i, (g, r) in enumerate(zip(regs, rows)))
    verb = 'увеличивался' if grow else 'сокращался'
    obj = 'объём производства' if kind != 'abs' else 'показатель'
    q = (f'Проанализируйте данные таблицы. {what}: {tab}. В каких из приведённых регионов {obj} ежегодно {verb} '
         f'в период с {years[0]} по {years[-1]} г.? Запишите цифры, под которыми указаны эти регионы.')
    e = ('Индекс больше 100 % — рост к предыдущему году, меньше 100 % — сокращение (даже если индекс растёт).' if kind != 'abs'
         else 'Нужен рост (снижение) в каждом году, а не только от первого года к последнему.')
    return many_card('geo-ege-10', q, regs, good, e, {'rows': rows, 'kind': kind, 'grow': grow})


def check_g_index_table(c):
    out = []
    for i, r in enumerate(c['rows']):
        if c['kind'] == 'abs':
            ok = all((q > p) if c['grow'] else (q < p) for p, q in zip(r, r[1:]))
        else:
            ok = all((v > 100) if c['grow'] else (v < 100) for v in r)
        if ok:
            out.append(str(i + 1))
    return out


def wbv(iso, key):
    v = FACTS['geo']['countries'][iso]['wb'].get(key)
    return None if v is None else v[0]


def gen_g_pair(rng):
    """ЕГЭ гео 24–25: пара стран по данным World Bank — ВВП на душу или роль сельского хозяйства (расчёт/сравнение)."""
    C = FACTS['geo']['countries']
    mode = rng.choice(['gdp_pc', 'agr'])
    pool = [i for i in C if all(wbv(i, k) is not None for k in ('gdp', 'pop', 'agr_gdp', 'agr_emp')) and wbv(i, 'pop') > 5e6]
    for _ in range(100):
        a, b = rng.sample(pool, 2)
        if mode == 'gdp_pc':
            va = wbv(a, 'gdp') / wbv(a, 'pop')
            vb = wbv(b, 'gdp') / wbv(b, 'pop')
            if max(va, vb) / min(va, vb) < 1.5:
                continue
            ga, pa = round(wbv(a, 'gdp') / 1e9), round(wbv(a, 'pop') / 1e6, 1)
            gb, pb = round(wbv(b, 'gdp') / 1e9), round(wbv(b, 'pop') / 1e6, 1)
            if not ga or not gb:
                continue
            q = (f'ВВП {C[a]["name"]} — {sp(ga)} млрд долл., население — {fmt(Fraction(str(pa)))} млн чел.; '
                 f'ВВП {C[b]["name"]} — {sp(gb)} млрд долл., население — {fmt(Fraction(str(pb)))} млн чел. '
                 f'В какой из стран больше ВВП на душу населения?')
            win = a if Fraction(ga) / Fraction(str(pa)) > Fraction(gb) / Fraction(str(pb)) else b
            e = (f'ВВП на душу: {C[a]["name"]} ≈ {round(ga * 1000 / pa)} долл., {C[b]["name"]} ≈ {round(gb * 1000 / pb)} долл. '
                 f'(World Bank, {C[a]["wb"]["gdp"][1]}).')
        else:
            ra, rb = wbv(a, 'agr_gdp'), wbv(b, 'agr_gdp')
            ea, eb = wbv(a, 'agr_emp'), wbv(b, 'agr_emp')
            if not ((ra > rb * 1.5 and ea > eb * 1.5) or (rb > ra * 1.5 and eb > ea * 1.5)):
                continue
            q = (f'Доля сельского хозяйства в ВВП: {C[a]["name"]} — {round(ra)} %, {C[b]["name"]} — {round(rb)} %; '
                 f'доля занятых в сельском хозяйстве: {C[a]["name"]} — {round(ea)} %, {C[b]["name"]} — {round(eb)} %. '
                 'В какой из стран сельское хозяйство играет бо́льшую роль в экономике?')
            win = a if ra > rb else b
            e = f'Оба показателя выше у страны {C[win]["name"]} (World Bank, {C[a]["wb"]["agr_gdp"][1]}).'
        o, ans = one(rng, C[win]['name'], [C[b if win == a else a]['name']], n=2)
        return card('one', 'geo-ege-24', q, ans, e, {'a': a, 'b': b, 'mode': mode, 'opts': [x['t'] for x in o],
                                                   'num': [ga, pa, gb, pb] if mode == 'gdp_pc' else [ra, rb, ea, eb]}, o=o)
    return gen_g_pair(rng)


def check_g_pair(c):
    C = FACTS['geo']['countries']
    if c['mode'] == 'gdp_pc':
        ga, pa, gb, pb = (Fraction(str(x)) for x in c['num'])
        win = c['a'] if ga * pb > gb * pa else c['b']
    else:
        win = c['a'] if c['num'][0] > c['num'][1] and c['num'][2] > c['num'][3] else c['b']
    return '123456'[c['opts'].index(C[win]['name'])]


DENS_SCALE = [(0, 10), (11, 50), (51, 100), (101, 200), (201, None)]


def dens_label(lo, hi):
    return f'более {lo - 1}' if hi is None else f'{lo}–{hi}'


def gen_g_density_class(rng):
    """ЕГЭ гео 20: страна → интервал средней плотности населения (World Bank)."""
    C = FACTS['geo']['countries']
    pool = [i for i in C if wbv(i, 'density') is not None and wbv(i, 'pop') > 3e6]
    for _ in range(100):
        iso = rng.choice(pool)
        d = wbv(iso, 'density')
        r = round(d)
        # не берём страны у границы интервала: округление не должно менять ответ
        if any(abs(d - b) < 2 for b in (10.5, 50.5, 100.5, 200.5)):
            continue
        k = next(i for i, (lo, hi) in enumerate(DENS_SCALE) if hi is None or r <= hi)
        labels = [dens_label(lo, hi) for lo, hi in DENS_SCALE]
        o = [{'id': '12345'[i], 't': t} for i, t in enumerate(labels)]
        q = f'Определите, к какому интервалу средней плотности населения (чел./км²) относится страна {C[iso]["name"]}.'
        e = f'{C[iso]["name"]}: ≈ {r} чел./км² (World Bank, {C[iso]["wb"]["density"][1]}).'
        return card('one', 'geo-ege-20', q, '12345'[k], e, {'iso': iso}, o=o)


def check_g_density_class(c):
    d = wbv(c['iso'], 'density')
    for i, (lo, hi) in enumerate(DENS_SCALE):
        if hi is None or d < hi + 0.5:
            return '12345'[i]


def gen_g_sunrise(rng):
    """ОГЭ гео 17: где раньше взойдёт Солнце по московскому времени (равноденствие: решает долгота)."""
    cs = [c for c in CITIES if CITIES[c][3] is not None]
    for _ in range(100):
        pick = rng.sample(cs, 4)
        lons = sorted(CITIES[c][2] for c in pick)
        if min(b - a for a, b in zip(lons, lons[1:])) >= 4:
            break
    day = rng.choice(['21 марта', '23 сентября'])
    first = max(pick, key=lambda c: CITIES[c][2])
    o, a = one(rng, first, [c for c in pick if c != first])
    q = f'Дата — {day}. Часы во всех городах выставлены по Москве. В каком городе восход наступит раньше?'
    e = f'В дни равноденствия восход раньше там, где восточнее: {first} ({fmt(CITIES[first][2])}° в. д.).'
    return card('one', 'geo-oge-17', q, a, e, {'pick': pick, 'opts': [x['t'] for x in o]}, o=o)


def check_g_sunrise(c):
    # восход по всемирному времени в равноденствие: 6 ч − λ/15 (без учёта рефракции) — меньше у восточного
    t = {x: 6 - CITIES[x][2] / 15 for x in c['opts']}
    return '123456'[c['opts'].index(min(t, key=t.get))]


ROCKS_SED = ['песок', 'глина', 'известняк', 'песчаник', 'мергель', 'каменная соль', 'гравий', 'суглинок', 'доломит', 'мел']


def gen_g_strata(rng):
    """ОГЭ гео 8: слои осадочных пород при ненарушенном залегании — от древнего к молодому (снизу вверх)."""
    k = rng.choice([3, 4])
    layers = rng.sample(ROCKS_SED, k)                    # сверху вниз
    shown = layers[:]
    rng.shuffle(shown)
    old_first = rng.random() < 0.5
    order_names = layers[::-1] if old_first else layers
    order = [shown.index(x) for x in order_names]
    q = (f'Обрыв на берегу реки: сверху вниз залегают слои — {", ".join(layers)} (залегание ненарушенное). '
         f'Расположите породы в порядке {"от самой древней к самой молодой" if old_first else "от самой молодой к самой древней"}')
    return seq_card('geo-oge-8', q, shown, order, 'Ниже залегающие слои образовались раньше.',
                    {'layers': layers, 'shown': shown, 'old': old_first, 'k': k})


def check_g_strata(c):
    age = {x: i for i, x in enumerate(c['layers'])}      # больше индекс (ниже) — древнее
    idx = sorted(range(len(c['shown'])), key=lambda j: age[c['shown'][j]], reverse=c['old'])
    return ''.join(str(j + 1) for j in idx)


SHARE_CTX = [
    ('Земельный фонд района (тыс. га)', ['сельскохозяйственные угодья', 'леса', 'застроенные земли', 'водные объекты', 'прочие']),
    ('Производство электроэнергии в регионе (млн кВт·ч)', ['ТЭС', 'ГЭС', 'АЭС', 'ВЭС и СЭС']),
    ('Население района (тыс. чел.)', ['городское', 'сельское']),
    ('Посевные площади хозяйства (га)', ['зерновые', 'технические', 'кормовые', 'картофель и овощи']),
]


def gen_g_share(rng):
    """ОГЭ гео 13: доля части в целом, %, округлить до целого (условные данные)."""
    title, parts = rng.choice(SHARE_CTX)
    vals = [rng.randint(5, 400) for _ in parts]
    i = rng.randrange(len(parts))
    tot = sum(vals)
    x = Fraction(vals[i] * 100, tot)
    if abs(x - int(x) - Fraction(1, 2)) < Fraction(1, 50):
        return gen_g_share(rng)
    ans = fmt(half_up(x, 0))
    q = (f'{title} (условные данные): ' + '; '.join(f'{p} — {v}' for p, v in zip(parts, vals)) +
         f'. Какова доля категории «{parts[i]}» в общем итоге (%)? Ответ округлите до целого числа.')
    return card('num', 'geo-oge-13', q, ans, f'{vals[i]} : {tot} × 100 % ≈ {ans} %.', {'vals': vals, 'i': i})


def check_g_share(c):
    v = c['vals']
    return str(round(Decimal(v[c['i']] * 100) / Decimal(sum(v))))


def gen_g_chart(rng):
    """ОГЭ гео 23: ряд по годам (условные данные) — год максимума/минимума или изменение за период."""
    y0 = rng.choice(range(2012, 2019))
    n = rng.choice([5, 6, 7])
    years = list(range(y0, y0 + n))
    what = rng.choice(['число прибывших в регион, тыс. чел.', 'рождаемость, ‰', 'производство зерна, млн т',
                       'объём грузоперевозок, млн т', 'численность населения города, тыс. чел.'])
    vals = rng.sample(range(10, 99), n)
    mode = rng.choice(['max', 'min', 'delta'])
    if mode == 'delta':
        a, b = sorted(rng.sample(range(n), 2))
        ans = str(vals[b] - vals[a])
        q = f'Показатель «{what}» по годам: ' + ', '.join(f'{y} — {v}' for y, v in zip(years, vals)) + \
            f'. На сколько изменился показатель с {years[a]} по {years[b]} г.? Уменьшение запишите со знаком «минус».'
        chk = {'years': years, 'vals': vals, 'mode': mode, 'a': a, 'b': b}
    else:
        f = max if mode == 'max' else min
        ans = str(years[vals.index(f(vals))])
        q = f'Показатель «{what}» по годам: ' + ', '.join(f'{y} — {v}' for y, v in zip(years, vals)) + \
            f'. В каком году показатель был {"наибольшим" if mode == "max" else "наименьшим"}?'
        chk = {'years': years, 'vals': vals, 'mode': mode}
    return card('num', 'geo-oge-23', q, ans, 'Чтение ряда по годам (условные данные).', chk)


def check_g_chart(c):
    y, v = c['years'], c['vals']
    if c['mode'] == 'delta':
        return str(v[c['b']] - v[c['a']])
    best = sorted(zip(v, y), reverse=c['mode'] == 'max')[0]
    return str(best[1])


def stations_full():
    """Станции с полными помесячными нормами; пограничные по поясу/типу (note с «или») и с расхождениями (check) не берём."""
    return [s for s in FACTS['geo'].get('stations', []) if s.get('t') and s.get('p') and len(s['t']) == 12
            and len(s['p']) == 12 and None not in s['t'] + s['p'] and not s.get('check') and 'или' not in s.get('note', '')]


def gen_g_climtype(rng):
    """ЕГЭ гео 27 / ОГЭ 18: по помесячным t и осадкам определить климатический пояс (по Алисову), 1 из 4."""
    S = stations_full()
    belts = sorted({s['belt'] for s in S if s.get('belt')})
    if len(belts) < 4:
        raise Skip('stations')
    s = rng.choice([x for x in S if x.get('belt')])
    wrong = rng.sample([t for t in belts if t != s['belt']], 3)
    o, a = one(rng, s['belt'], wrong)
    q = ('Климатические данные пункта (без названия). Средняя температура по месяцам (°C, янв.–дек.): '
         + ', '.join(fmt(Fraction(str(x))) for x in s['t']) + '. Осадки (мм): ' + ', '.join(str(round(x)) for x in s['p']) +
         f'. Широта пункта {abs(round(s["lat"]))}° {"с. ш." if s["lat"] >= 0 else "ю. ш."}. В каком климатическом поясе он находится?')
    return card('one', 'geo-ege-27', q, a, f'Это {s["name"]} ({s["country"]}): {s["belt"]} пояс, {s.get("type", "")} климат.',
                {'name': s['name'], 'opts': [x['t'] for x in o]}, o=o)


def check_g_climtype(c):
    s = next(x for x in stations_full() if x['name'] == c['name'])
    return '123456'[c['opts'].index(s['belt'])]


def gen_g_climtable(rng):
    """ОГЭ гео 16: таблица 3–4 метеостанций; какой вывод следует из данных (монотонность по широте/долготе)."""
    S = [s for s in stations_full() if s.get('country') == 'Россия']
    if len(S) < 6:
        raise Skip('stations')
    for _ in range(200):
        pick = rng.sample(S, 3)
        axis = rng.choice(['lat', 'lon'])
        if min(abs(a[axis] - b[axis]) for a, b in itertools.combinations(pick, 2)) < 3:
            continue
        pick.sort(key=lambda s: s[axis])
        feats = {'t_jan': 'средняя температура января', 't_jul': 'средняя температура июля', 'p_year': 'годовое количество осадков'}
        concl = []
        for f, name in feats.items():
            v = [geo_value('stations', s, f)[0] for s in pick]
            up = all(a < b for a, b in zip(v, v[1:]))
            dn = all(a > b for a, b in zip(v, v[1:]))
            dir_ = {'lat': ('с юга на север', 'с севера на юг'), 'lon': ('с запада на восток', 'с востока на запад')}[axis]
            concl.append((f'{name} повышается при движении {dir_[0]}', up))
            concl.append((f'{name} повышается при движении {dir_[1]}', dn))
        good = [t for t, ok in concl if ok]
        bad = [t for t, ok in concl if not ok]
        if len(good) != 1 and not (len(good) >= 1 and rng.random() < 0.3):
            continue
        g = rng.choice(good)
        o, a = one(rng, g, rng.sample([b for b in bad if b not in good], 3))
        rows = '; '.join(f'{s["name"]} ({round(s["lat"])}° с. ш., {round(s["lon"])}° в. д.): январь {fmt(Fraction(str(s["t"][0])))} °C, '
                         f'июль {fmt(Fraction(str(s["t"][6])))} °C, осадки {round(sum(s["p"]))} мм' for s in pick)
        q = f'Климатические показатели пунктов: {rows}. Какой вывод следует из этих данных?'
        return card('one', 'geo-oge-16', q, a, 'Проверяем каждый вывод по всем пунктам таблицы.',
                    {'names': [s['name'] for s in pick], 'axis': axis, 'opts': [x['t'] for x in o]}, o=o)
    raise Skip('climtable')


def check_g_climtable(c):
    by = {s['name']: s for s in stations_full()}
    pick = sorted((by[n] for n in c['names']), key=lambda s: s[c['axis']])
    feats = {'средняя температура января': 't_jan', 'средняя температура июля': 't_jul', 'годовое количество осадков': 'p_year'}
    fwd = {'lat': 'с юга на север', 'lon': 'с запада на восток'}[c['axis']]
    ok = []
    for i, t in enumerate(c['opts']):
        name, _, rest = t.partition(' повышается при движении ')
        v = [geo_value('stations', s, feats[name])[0] for s in pick]
        if rest != fwd:
            v = v[::-1]
        if all(a < b for a, b in zip(v, v[1:])):
            ok.append(i)
    return '123456'[ok[0]] if len(ok) == 1 else None




def gen_g_demo2(rng):
    """ЕГЭ гео 15–16: добыча по запасам, обеспеченность пашней на душу, изменение численности, миграция по потокам."""
    mode = rng.choice(['production', 'percap', 'total', 'flows'])
    Y = rng.choice([2022, 2023, 2024])
    if mode == 'production':
        res_name = rng.choice(list(RESOURCES))
        ru, pu, T = RESOURCES[res_name]
        cn = rng.choice(list(T))
        R = jitter(rng, T[cn][0], 8, 1)
        years = int(half_up(R * 1000 / T[cn][1], 0))
        ans = fmt(half_up(R * 1000 / years, 0))
        q = (f'Учащиеся нашли данные о разведанных запасах {res_name} в {inflect(cn, "loct") if inflect(cn, "loct") != cn else "стране " + cn}: '
             f'{fmt(R)} {ru}; ресурсообеспеченность {of_country(cn)} {RES_ABLT[res_name]} — {years} {years_word(years)}. '
             f'Определите годовую добычу {res_name} ({pu}). Полученный результат округлите до целого числа.')
        e = f'{fmt(R)} {ru} = {fmt(R * 1000)} {pu}; {fmt(R * 1000)} : {years} ≈ {ans} {pu}.'
        chk = {'mode': mode, 'R': str(R), 'years': years}
    elif mode == 'percap':
        cn = rng.choice(list(ARABLE))
        pop, ar = jitter(rng, ARABLE[cn][0], 3, 1), jitter(rng, ARABLE[cn][1], 5, 1)
        ans = fmt(half_up(ar / pop, 2), 2)
        q = (f'Площадь пашни {of_country(cn)} в {Y} г. составляла {fmt(ar)} млн га, численность населения — {fmt(pop)} млн человек. '
             'Определите обеспеченность страны пашней (га на человека). Полученный результат округлите до сотых.')
        e = f'{fmt(ar)} : {fmt(pop)} ≈ {ans} га/чел.'
        chk = {'mode': mode, 'ar': str(ar), 'pop': str(pop)}
    elif mode == 'total':
        name, p, nats, migs = demo_rows(rng, 2)
        q = (f'Численность населения субъекта РФ «{name}» на 1 января: {Y} г. — {sp(p[0])} чел.; {Y + 1} г. — {sp(p[1])} чел.; '
             f'{Y + 2} г. — {sp(p[2])} чел. Используя данные таблицы, определите, на сколько человек изменилась численность '
             f'населения за {Y + 1} г. Если численность уменьшилась, ответ запишите со знаком «минус».')
        ans = str(p[2] - p[1])
        e = f'За {Y + 1} г. — разность численности на 1 января {Y + 2} и {Y + 1} гг.: {sp(p[2])} − {sp(p[1])} = {ans}.'
        chk = {'mode': mode, 'p': p}
    else:
        name, v = subj(rng, True)
        k = v['pop'] / 1_000_000                          # масштаб потоков — от численности субъекта
        inner = half_up(Fraction(str(round(rng.uniform(4, 20) * k, 1))), 1)
        reg_in, reg_out = [half_up(Fraction(str(round(rng.uniform(5, 25) * k, 1))), 1) for _ in range(2)]
        int_in, int_out = [half_up(x / rng.randint(3, 10), 1) for x in (reg_in, reg_out)]
        q = (f'Миграция населения субъекта РФ «{name}» в {Y} г. (тыс. чел.): внутрирегиональная — прибыло {fmt(inner)}, выбыло {fmt(inner)}; '
             f'межрегиональная — прибыло {fmt(reg_in)}, выбыло {fmt(reg_out)}; международная — прибыло {fmt(int_in)}, выбыло {fmt(int_out)}. '
             'Используя эти данные, определите величину миграционного прироста (убыли) населения субъекта в этом году '
             '(тыс. чел.). Убыль запишите со знаком «минус».')
        ans = fmt(reg_in + int_in - reg_out - int_out, 1)
        e = (f'Внутрирегиональная миграция не меняет численность субъекта. ({fmt(reg_in)} + {fmt(int_in)}) − ({fmt(reg_out)} + {fmt(int_out)}) = {ans}.')
        chk = {'mode': mode, 'ins': [str(inner), str(reg_in), str(int_in)], 'outs': [str(inner), str(reg_out), str(int_out)]}
    return card('num', 'geo-ege-16' if mode in ('total', 'flows') else 'geo-ege-15', q, ans, e, chk)


def check_g_demo2(c):
    m = c['mode']
    F = Fraction
    if m == 'production':
        return fmt(half_up(F(c['R']) * 1000 / c['years'], 0))
    if m == 'percap':
        return fmt(half_up(F(c['ar']) / F(c['pop']), 2), 2)
    if m == 'total':
        return str(c['p'][2] - c['p'][1])
    return fmt(sum(F(x) for x in c['ins']) - sum(F(x) for x in c['outs']), 1)


def gen_g_demo4(rng):
    """ОГЭ гео 23: таблица 4 субъектов (численность на 1 января, естественный и миграционный прирост) → один регион по условию."""
    Y = rng.choice([2022, 2023, 2024])
    crit = rng.choice(['birth', 'outflow', 'grew', 'fell_inflow'])
    for _ in range(200):
        rows = [demo_rows(rng, 1) for _ in range(4)]
        if len({r[0] for r in rows}) < 4:
            continue
        test = {'birth': lambda r: r[2][0] > 0, 'outflow': lambda r: r[3][0] < 0,
                'grew': lambda r: r[2][0] + r[3][0] > 0,
                'fell_inflow': lambda r: r[2][0] + r[3][0] < 0 and r[3][0] > 0}[crit]
        good = [i for i, r in enumerate(rows) if test(r)]
        if len(good) == 1:
            break
    else:
        return gen_g_demo4(rng)
    text = {'birth': 'рождаемость превышала смертность', 'outflow': 'наблюдался миграционный отток населения',
            'grew': 'численность населения увеличилась', 'fell_inflow': 'численность населения сократилась, несмотря на миграционный приток'}[crit]
    tab = '; '.join(f'{i + 1}) {r[0]}: численность на 1 января {Y} г. — {sp(r[1][0])} чел., естественный прирост — {r[2][0]} чел., '
                    f'миграционный прирост — {r[3][0]} чел.' for i, r in enumerate(rows))
    q = (f'Проанализируйте данные таблицы о населении субъектов РФ за {Y} г.: {tab}. В каком из субъектов в {Y} г. {text}? '
         'Запишите в ответ цифру, под которой указан этот субъект.')
    names = [r[0] for r in rows]
    c = card('one', 'geo-oge-23', q, str(good[0] + 1), 'Естественный прирост > 0 — рождаемость выше смертности; общий = естественный + миграционный.',
             {'rows': [[r[2][0], r[3][0]] for r in rows], 'crit': crit}, o=[{'id': str(i + 1), 't': n} for i, n in enumerate(names)])
    return c


def check_g_demo4(c):
    t = {'birth': lambda n, m: n > 0, 'outflow': lambda n, m: m < 0, 'grew': lambda n, m: n + m > 0,
         'fell_inflow': lambda n, m: n + m < 0 and m > 0}[c['crit']]
    hits = [str(i + 1) for i, (n, m) in enumerate(c['rows']) if t(n, m)]
    return hits[0] if len(hits) == 1 else None


SCALES = {
    'density': ([(0, 10), (11, 50), (51, 100), (101, 200), (201, None)], 'средней плотности населения (чел./км²)'),
    'urban': ([(0, 20), (21, 40), (41, 60), (61, 80), (81, None)], 'доли городского населения (%)'),
}


def gen_d_interval(rng, args, topic='dict'):
    """ЕГЭ гео 20: три страны ↔ интервалы легенды картограммы (плотность или доля горожан, World Bank)."""
    (tab, field), kw = parse_args(args)
    scale, label = SCALES[field]
    C = FACTS['geo']['countries']
    pool = [i for i in C if wbv(i, field) is not None and wbv(i, 'pop') > 3e6]
    bounds = [hi + 0.5 for lo, hi in scale if hi is not None]

    def cls(v):
        return next(i for i, b in enumerate(bounds + [float('inf')]) if v < b)
    ok = [i for i in pool if not any(abs(wbv(i, field) - b) < max(1.5, b * 0.05) for b in bounds)]   # не у границы
    for _ in range(100):
        pick = rng.sample(ok, 3)
        ks = [cls(wbv(i, field)) for i in pick]
        if len(set(ks)) < 3:                              # в КИМ цифры в ответе не повторяются
            continue
        labels = [f'более {lo - 1}' if hi is None else f'{lo}–{hi}' for lo, hi in scale]
        q = (f'Установите соответствие между страной и значением {label}, которое ей соответствует на картограмме. '
             'Для каждой страны выберите номер интервала.')
        e = '; '.join(f'{C[i]["name"]} — {fmt(Fraction(str(round(wbv(i, field), 1))))}' for i in pick) + \
            f' (World Bank, {C[pick[0]]["wb"][field][1]}).'
        return match_card(topic, q, [C[i]['name'] for i in pick], labels, ks, e, {'eng': 'd_interval', 'field': field, 'isos': pick})
    raise Skip(field)


def check_d_interval(c):
    scale, _ = SCALES[c['field']]
    out = ''
    for iso in c['isos']:
        v = wbv(iso, c['field'])
        out += str(next(i for i, (lo, hi) in enumerate(scale) if hi is None or v < hi + 0.5) + 1)
    return out


def gen_d_struct(rng, args, topic='dict'):
    """ЕГЭ гео 7: страна ↔ структура ВВП или занятости по секторам (World Bank)."""
    (tab, kind), kw = parse_args(args)
    keys = {'gdp': ('agr_gdp', 'ind_gdp', 'srv_gdp'), 'emp': ('agr_emp', 'ind_emp', 'srv_emp')}[kind]
    C = FACTS['geo']['countries']
    pool = [i for i in C if all(wbv(i, k) is not None for k in keys) and wbv(i, 'pop') > 5e6]
    for _ in range(200):
        pick = rng.sample(pool, 3)
        agr = sorted(wbv(i, keys[0]) for i in pick)
        if min(b - a for a, b in zip(agr, agr[1:])) < 8:
            continue
        right = sorted(pick, key=lambda i: wbv(i, keys[0]))
        labels = [f'сельское хозяйство {round(wbv(i, keys[0]))} %, промышленность {round(wbv(i, keys[1]))} %, '
                  f'сфера услуг {round(wbv(i, keys[2]))} %' for i in right]
        left = rng.sample(pick, int(kw.get('left', 3)))
        ans = [right.index(i) for i in left]
        what = 'ВВП' if kind == 'gdp' else 'занятых'
        q = f'Соотнесите страны со структурой {what} по секторам экономики (данные World Bank): для каждой буквы — номер.'
        e = '; '.join(f'{C[i]["name"]}: {labels[right.index(i)]}' for i in left) + '.'
        return match_card(topic, q, [C[i]['name'] for i in left], labels, ans, e,
                          {'eng': 'd_struct', 'keys': keys, 'left': left, 'right': right})
    raise Skip(kind)


def check_d_struct(c):
    # страна с большей долей сельского хозяйства стоит в правом столбце ниже: сравниваем ранги заново
    ranks = sorted(c['right'], key=lambda i: wbv(i, c['keys'][0]))
    return ''.join(str(ranks.index(i) + 1) for i in c['left'])




def translate_rna(rna):
    out = []
    for i in range(0, len(rna) - 2, 3):
        aa = CODE[rna[i:i + 3]]
        if aa == 'стоп':
            break
        out.append(aa)
    return out


def gen_b_orf(rng):
    """ЕГЭ 27: иРНК с «лидером» — синтез начинается с первого АУГ; найти белок."""
    for _ in range(200):
        lead = ''.join(rng.choice('АУГЦ') for _ in range(rng.randint(3, 8)))
        if 'АУГ' in lead + 'АУ' or lead.endswith('А') or lead.endswith('АУ'):
            continue
        body = [c for c in (rng.choice(list(CODE)) for _ in range(rng.randint(4, 6))) if CODE[c] != 'стоп']
        stop = rng.choice([c for c in CODE if CODE[c] == 'стоп'])
        rna = lead + 'АУГ' + ''.join(body) + stop + ''.join(rng.choice('АУГЦ') for _ in range(rng.randint(2, 5)))
        if rna.find('АУГ') != len(lead):
            continue
        prot = translate_rna(rna[len(lead):])
        from_start = translate_rna(rna[:len(rna) - len(rna) % 3])
        shifted = translate_rna(rna[len(lead) + 1:])
        opts = ['-'.join(prot), '-'.join(from_start), '-'.join(shifted) or '—', '-'.join(prot[1:]) or '—']
        if len(set(opts)) < 4 or not prot:
            continue
        o, a = one(rng, opts[0], opts[1:])
        q = (f'Фрагмент иРНК 5ʹ→3ʹ: {rna}. Синтез белка начинается с первого кодона АУГ и идёт до стоп-кодона. '
             'Какая последовательность аминокислот закодирована? Используйте таблицу генетического кода.')
        return card('one', 'bio-ege-27', q, a, f'Первый АУГ — с {len(lead) + 1}-го нуклеотида: {opts[0]}.',
                    {'rna': rna, 'opts': [x['t'] for x in o]}, o=o)
    return gen_b_orf(rng)


def check_b_orf(c):
    rna = c['rna']
    i = rna.index('АУГ')
    prot = []
    while i + 3 <= len(rna) and CODE[rna[i:i + 3]] != 'стоп':
        prot.append(CODE[rna[i:i + 3]])
        i += 3
    return '123456'[c['opts'].index('-'.join(prot))]


def gen_b_nondisj(rng):
    """ЕГЭ 28, 3: нерасхождение одной пары хромосом в мейозе — число хромосом в гаметах и зиготе."""
    org = rng.choice(list(KARYO))
    n2 = KARYO[org]
    n = n2 // 2
    mode = rng.choice(['gamete_plus', 'gamete_minus', 'zygote_plus', 'zygote_minus'])
    what = {'gamete_plus': ('в гамете, получившей лишнюю хромосому', n + 1),
            'gamete_minus': ('в гамете, которой не досталось хромосомы этой пары', n - 1),
            'zygote_plus': ('в зиготе от слияния такой гаметы (с лишней хромосомой) с нормальной гаметой', n2 + 1),
            'zygote_minus': ('в зиготе от слияния гаметы без хромосомы этой пары с нормальной гаметой', n2 - 1)}[mode]
    q = (f'В соматических клетках {org} содержится {agree(n2, "хромосома")}. В мейозе I одна пара гомологичных хромосом не разошлась. '
         f'Сколько хромосом {what[0]}? В ответе запишите только число.')
    return card('num', 'bio-ege-28', q, str(what[1]), f'n = {n}; ответ {what[1]}.', {'n2': n2, 'mode': mode})


def check_b_nondisj(c):
    n = c['n2'] // 2
    g = n + (1 if 'plus' in c['mode'] else -1)
    return str(g + n if c['mode'].startswith('zygote') else g)


def gen_b_phylo(rng):
    """ЕГЭ 27: «молекулярные часы» — время расхождения двух видов по числу различий T = D / (2r)."""
    r = rng.choice([Fraction(1, 2), Fraction(1), Fraction(2), Fraction(3, 2), Fraction(5, 2)])
    T = rng.randint(2, 60)
    D = 2 * r * T
    if D.denominator != 1:
        return gen_b_phylo(rng)
    q = (f'Два вида имеют общего предка. В исследованном участке ДНК между ними {agree(int(D), "различие")} (замены нуклеотидов). '
         f'Скорость накопления замен в каждой линии — {agree(int(r), "замена") if r.denominator == 1 else fmt(r) + " замены"} за миллион лет. Сколько миллионов лет назад '
         'разошлись линии этих видов? Ответ запишите числом.')
    return card('num', 'bio-ege-27', q, str(T), f'Замены копятся в обеих линиях: T = D : (2r) = {int(D)} : {fmt(2 * r)} = {T}.',
                {'D': int(D), 'r': str(r)})


def check_b_phylo(c):
    return fmt(Fraction(c['D']) / (2 * Fraction(c['r'])))




def gen_b_foodweb2(rng):
    """ОГЭ 21: рост численности X → как изменятся конкурент X (общий корм) и организм, не связанный с X напрямую."""
    name = rng.choice(list(WEBS))
    web = WEBS[name]
    eaters = {x: [y for y, food in web.items() if x in food] for x in web}
    mode = rng.choice(['competitor', 'unrelated'])
    links = '; '.join(f'{x} питается: {", ".join(f)}' for x, f in web.items() if f)
    cons = [x for x in web if web[x]]
    rng.shuffle(cons)
    for x in cons:
        food = web[x]
        if mode == 'competitor':
            # конкурент: ест тот же корм, сам не является ни пищей, ни врагом X
            comp = [y for y in web if y != x and set(web[y]) & set(food) and y not in food and x not in web[y]]
            if not comp:
                continue
            B = rng.choice(comp)
            A = rng.choice(food)
            ans = '22'
            why = f'{x} сильнее выедает {A} (уменьшится); у {B} меньше общего корма (уменьшится).'
        else:
            near = set(food) | set(eaters[x]) | {x}
            far = [y for y in web if y not in near and not (set(web[y]) & set(food)) and not (set(eaters[y]) & set(eaters[x]))]
            if not far:
                continue
            B = rng.choice(far)
            A = rng.choice(food)
            ans = '23'
            why = f'{A} — пища {x} (уменьшится); {B} с {x} напрямую не связан (не изменится).'
        swap = rng.random() < 0.5
        P, Q = (B, A) if swap else (A, B)
        if swap:
            ans = ans[::-1]
        q = (f'Экосистема «{name}». Связи: {links}. Несколько лет росла численность организма «{x}». Как изменится '
             f'численность: А) {P}; Б) {Q}? 1 — увеличится, 2 — уменьшится, 3 — не изменится (учитывайте только прямые связи). '
             'Ответ — две цифры.')
        return card('num', 'bio-oge-21', q, ans, why, {'web': name, 'mode': mode, 'x': x, 'A': P, 'B': Q})
    return gen_b_foodweb2(rng)


def check_b_foodweb2(c):
    web = WEBS[c['web']]
    x = c['x']

    def code(y):
        if y in web[x]:
            return '2'                                    # пищу выедают
        if x in web[y]:
            return '1'                                    # у хищника больше корма
        if set(web[y]) & set(web[x]):
            return '2'                                    # конкурент за общий корм
        return '3'
    return code(c['A']) + code(c['B'])


def gen_g_strata2(rng):
    """ОГЭ гео 8 (нарушенное залегание): магматическое тело прорывает слои — оно моложе прорванных слоёв."""
    k = 2                                                # 2 слоя + магматическое тело = 3 элемента, как в КИМ
    layers = rng.sample(ROCKS_SED, k)                    # сверху вниз
    cut = rng.randint(1, k)                               # сколько нижних слоёв прорвала интрузия
    intr = rng.choice(['гранит', 'диорит', 'габбро'])
    cut_layers = layers[-cut:]
    # интрузия моложе прорванных слоёв и древнее не прорванных (лежащих выше)
    ages = {x: i for i, x in enumerate(layers)}           # больше индекс — древнее
    ages[intr] = k - cut - 0.5
    items = layers + [intr]
    shown = items[:]
    rng.shuffle(shown)
    old_first = rng.random() < 0.5
    order = sorted(range(len(shown)), key=lambda j: ages[shown[j]], reverse=old_first)
    top_uncut = layers[:k - cut]
    gen_ = {'гранит': 'гранита', 'диорит': 'диорита', 'габбро': 'габбро'}[intr]
    q = (f'Разрез: сверху вниз залегают {", ".join(layers)}. Тело {gen_} прорывает '
         f'{"все слои" if cut == k else "слои: " + ", ".join(cut_layers)}'
         f'{"" if cut == k else "; выше лежащие слои (" + ", ".join(top_uncut) + ") не нарушены"}. '
         f'Расположите породы {"от самой древней к самой молодой" if old_first else "от самой молодой к самой древней"}')
    return seq_card('geo-oge-8', q, shown, order, 'Прорывающее тело моложе слоёв, которые оно прорывает.',
                    {'layers': layers, 'intr': intr, 'cut': cut, 'shown': shown, 'old': old_first})


def check_g_strata2(c):
    k = len(c['layers'])
    age = {x: i for i, x in enumerate(c['layers'])}
    age[c['intr']] = (k - c['cut'] - 1 + k - c['cut']) / 2     # между последним непрорванным и первым прорванным
    idx = sorted(range(len(c['shown'])), key=lambda j: age[c['shown'][j]], reverse=c['old'])
    return ''.join(str(j + 1) for j in idx)




ORDERS = ['продуцент', 'консумент I порядка', 'консумент II порядка', 'консумент III порядка', 'консумент IV порядка']


def web_levels(web):
    """Все порядки каждого организма по всем путям от продуцентов."""
    memo = {}

    def lv(x, stack=()):
        if x in memo:
            return memo[x]
        if not web[x]:
            memo[x] = {0}
        else:
            memo[x] = {l + 1 for f in web[x] if f not in stack for l in lv(f, stack + (x,))}
        return memo[x]
    return {x: lv(x) for x in web}


def foodweb_facts(web, x):
    """(утверждение, верно?) об организме x по схеме пищевой сети."""
    eaters = {a: [b for b, food in web.items() if a in food] for a in web}
    L = web_levels(web)[x]
    out = []
    for i, name in enumerate(ORDERS[:4]):
        out.append((f'является {name.replace("продуцент", "продуцентом").replace("консумент", "консументом")}', i in L))
    for f in web:
        if f == x:
            continue
        out.append((f'питается организмом «{f}»', f in web[x]))
        out.append((f'служит пищей для организма «{f}»', f in eaters[x]))
    out.append(('входит в пищевую цепь из 4 звеньев', any(x in ch for ch in web_chains(web, 4))))
    return out


def gen_b_foodweb3(rng):
    """ОГЭ био 19: выбрать 3 из 6 характеристик организма, отмеченного на схеме пищевой сети."""
    name = rng.choice(list(WEBS))
    web = WEBS[name]
    x = rng.choice([o for o in web if web[o]])
    facts = foodweb_facts(web, x)
    good = [t for t, ok in facts if ok]
    bad = [t for t, ok in facts if not ok]
    if len(good) < 3 or len(bad) < 3:
        return gen_b_foodweb3(rng)
    items = rng.sample(good, 3) + rng.sample(bad, 3)
    rng.shuffle(items)
    links = '; '.join(f'{o} → {", ".join(f)}' for o, f in web.items() if f)
    q = (f'Рассмотрите схему пищевой сети экосистемы «{name}» (стрелка: кто → кем питается): {links}. '
         f'Выберите три утверждения, верно характеризующие организм «{x}» в этой сети. Запишите цифры, под которыми они указаны.')
    gi = [i for i, t in enumerate(items) if t in good]
    return many_card('bio-oge-19', q, items, gi, 'Верно: ' + '; '.join(items[i] for i in gi) + '.', {'web': name, 'x': x, 'items': items})


def check_b_foodweb3(c):
    web = WEBS[c['web']]
    truth = dict(foodweb_facts(web, c['x']))
    return [str(i + 1) for i, t in enumerate(c['items']) if truth[t]]


EXTREME = {  # таблица:поле → (вопрос о максимуме, о минимуме)
    'obj:река:length_km': ('Какая из перечисленных рек имеет наибольшую длину?', 'Какая из перечисленных рек имеет наименьшую длину?'),
    'obj:вершина:elev_m': ('Какая из перечисленных вершин самая высокая?', 'Какая из перечисленных вершин самая низкая?'),
    'obj:озеро:area_km2': ('Какое из перечисленных озёр имеет наибольшую площадь?', 'Какое из перечисленных озёр имеет наименьшую площадь?'),
    'countries:area': ('Какая из перечисленных стран имеет наибольшую площадь территории?', 'Какая из перечисленных стран имеет наименьшую площадь территории?'),
    'countries:pop': ('В какой из перечисленных стран численность населения наибольшая?', 'В какой из перечисленных стран численность населения наименьшая?'),
}


def gen_d_extreme(rng, args, topic='dict'):
    """ОГЭ гео 1: один объект из четырёх с наибольшим/наименьшим значением (длина, высота, площадь)."""
    (tab, field), kw = parse_args(args)
    rows = geo_filter(tab, geo_rows(tab), kw)
    vals = {k: geo_value(tab, r, field) for k, r in rows.items()}
    vals = {k: v[0] for k, v in vals.items() if v and v[0]}
    gap = float(kw.get('gap', 1.1))
    for _ in range(100):
        pick = rng.sample(list(vals), 4)
        top = rng.random() < 0.7
        s = sorted(pick, key=vals.get, reverse=top)
        a, b = vals[s[0]], vals[s[1]]
        if max(a, b) < min(a, b) * gap:
            continue
        o, ans = one(rng, s[0], s[1:])
        qmax, qmin = EXTREME[f'{tab}:{field}']
        e = '; '.join(f'{x} — {sp(round(vals[x]))}' for x in pick) + '.'
        return card('one', topic, qmax if top else qmin, ans, e, {'eng': 'd_extreme', 'tab': tab, 'field': field, 'top': top,
                    'opts': [z['t'] for z in o]}, o=o)
    raise Skip(tab)


def check_d_extreme(c):
    rows = geo_rows(c['tab'])
    v = [geo_value(c['tab'], rows[x], c['field'])[0] for x in c['opts']]
    best = (max if c['top'] else min)(range(len(v)), key=lambda i: v[i])
    return '123456'[best]


def daylen_hours(lat, doy):
    import math
    decl = -23.44 * math.cos(math.radians(360 / 365 * (doy + 10)))
    x = -math.tan(math.radians(lat)) * math.tan(math.radians(decl))
    return 2 * math.degrees(math.acos(max(-1, min(1, x)))) / 15


def gen_g_daylen1(rng):
    """ОГЭ гео 17: в каком из четырёх городов 22 июня / 22 декабря день самый длинный (короткий)."""
    day, doy = rng.choice([('22 июня', 173), ('22 декабря', 356)])
    for _ in range(100):
        cs = rng.sample(list(CITIES), 4)
        lats = sorted(CITIES[c][1] for c in cs)
        if min(b - a for a, b in zip(lats, lats[1:])) >= 2:
            break
    longest = rng.random() < 0.5
    north = max(cs, key=lambda c: CITIES[c][1])
    south = min(cs, key=lambda c: CITIES[c][1])
    right = (north if day == '22 июня' else south) if longest else (south if day == '22 июня' else north)
    o, a = one(rng, right, [c for c in cs if c != right])
    q = f'Где из перечисленных городов {day} день длится {"дольше" if longest else "меньше"} всего (от восхода до заката Солнца)?'
    return card('one', 'geo-oge-17', q, a, f'{day}: чем {"севернее" if (day == "22 июня") == longest else "южнее"}, тем {"длиннее" if longest else "короче"} день.',
                {'cs': cs, 'doy': doy, 'longest': longest, 'opts': [z['t'] for z in o]}, o=o)


def check_g_daylen1(c):
    L = [daylen_hours(CITIES[x][1], c['doy']) for x in c['opts']]
    i = (max if c['longest'] else min)(range(4), key=lambda j: L[j])
    return '123456'[i]


def gen_g_chart1(rng):
    """ОГЭ гео 23: по ряду значений (график/таблица) выбрать год с наибольшим/наименьшим значением — 1 из 4."""
    c = gen_g_chart(rng)
    if c['chk']['mode'] == 'delta':
        return gen_g_chart1(rng)
    years = c['chk']['years']
    right = c['a']
    wrong = rng.sample([str(y) for y in years if str(y) != right], 3)
    o, a = one(rng, right, wrong)
    q = c['q'].replace('В каком году', 'Выберите год, когда').rstrip('?') + '.'
    return card('one', 'geo-oge-23', q, a, c['e'], dict(c['chk'], opts=[z['t'] for z in o]), o=o)


def check_g_chart1(c):
    best = check_g_chart(c)
    return '123456'[c['opts'].index(best)]


def gen_g_sun1(rng):
    """ОГЭ гео 17: в каком из четырёх городов 22 июня / 22 декабря полуденное Солнце выше (ниже) всего."""
    day, decl = rng.choice([('22 июня', 23.5), ('22 декабря', -23.5), ('21 марта', 0)])
    for _ in range(100):
        cs = rng.sample(list(CITIES), 4)
        lats = sorted(CITIES[c][1] for c in cs)
        if min(b - a for a, b in zip(lats, lats[1:])) >= 2:
            break
    high = rng.random() < 0.6
    h = {c: 90 - abs(CITIES[c][1] - decl) for c in cs}
    right = (max if high else min)(cs, key=h.get)
    o, a = one(rng, right, [c for c in cs if c != right])
    q = f'В каком из перечисленных городов {day} Солнце в полдень поднимается над горизонтом {"выше" if high else "ниже"}, чем в остальных?'
    return card('one', 'geo-oge-17', q, a, 'h = 90° − |φ − δ|: ' + ', '.join(f'{c} {fmt(Fraction(str(round(h[c], 1))))}°' for c in cs) + '.',
                {'cs': cs, 'decl': decl, 'high': high, 'opts': [z['t'] for z in o]}, o=o)


def check_g_sun1(c):
    import math
    z = [abs(math.radians(CITIES[x][1] - c['decl'])) for x in c['opts']]     # зенитное расстояние
    i = (min if c['high'] else max)(range(4), key=lambda j: z[j])
    return '123456'[i]


# ================================================================ реестр и самопроверка

GENS = {k[4:]: v for k, v in globals().items() if k.startswith('gen_') and not k.startswith('gen_d_')}
CHECKS = {k[6:]: v for k, v in globals().items() if k.startswith('check_') and not k.startswith('check_d_')}

INFO = {  # тип → (экзамен/задание, что проверяет)
    'b_chromo': 'ЕГЭ био 3, 27 · хромосомный набор и число ДНК в фазах митоза/мейоза',
    'b_chargaff': 'ЕГЭ био 3 · правило Чаргаффа',
    'b_coding': 'ЕГЭ био 3 · нуклеотиды/триплеты/тРНК по числу аминокислот',
    'b_food': 'ЕГЭ био 3, ОГЭ био 19–21 · правило 10 %',
    'b_mono': 'ЕГЭ био 4, ОГЭ 26 · моногибридное скрещивание (полное и неполное доминирование)',
    'b_dihybrid': 'ЕГЭ био 4 · дигибридное скрещивание, типы гамет',
    'b_blood': 'ЕГЭ био 4, 28 · группы крови AB0',
    'b_xlinked': 'ЕГЭ био 4, 28 · наследование, сцепленное с X-хромосомой',
    'b_linkage': 'ЕГЭ био 4, 28 · сцепленное наследование и кроссинговер',
    'b_hardy': 'ЕГЭ био 27 · закон Харди — Вайнберга',
    'b_transcr': 'ЕГЭ био 27 · транскрипция (иРНК по ДНК)',
    'b_transl': 'ЕГЭ био 27 · трансляция по таблице генетического кода',
    'b_anticodon': 'ЕГЭ био 27 · антикодон тРНК',
    'b_taxa': 'ЕГЭ био 12, ОГЭ био 3 · последовательность систематических групп',
    'b_foodweb': 'ОГЭ био 19–21 · пищевые сети: цепь, трофический уровень, изменение численности',
    'b_menu': 'ОГЭ био 26 · энергетическая ценность рациона',
    'g_time': 'ЕГЭ гео 14 · местное время в часовых зонах России',
    'g_newyear': 'ОГЭ гео 26 · порядок встречи Нового года',
    'g_sollon': 'ЕГЭ гео 28 · долгота по солнечному времени',
    'g_meridian': 'ЕГЭ гео 28 · расстояние по меридиану',
    'g_scale': 'ОГЭ гео 9 · масштаб, расстояние по карте',
    'g_azimuth': 'ОГЭ гео 10 · азимут и стороны горизонта',
    'g_altitude': 'ОГЭ гео 13 · температура и давление с высотой',
    'g_humidity': 'ЕГЭ гео 2 · относительная и абсолютная влажность',
    'g_demo': 'ЕГЭ гео 15–16, ОГЭ гео 24 · плотность, прирост, миграции, ресурсообеспеченность',
    'g_sun': 'ЕГЭ гео 27 · высота полуденного Солнца (солнечная радиация)',
    'g_daylen': 'ЕГЭ гео 3, ОГЭ гео 17 · продолжительность дня по широте и дате',
    'g_climate': 'ОГЭ гео 18, ЕГЭ гео 27 (подготовка) · климатограмма: амплитуда, сумма осадков',
    'g_lonorder': 'ЕГЭ гео 4 · горные системы с запада на восток',
    'b_graph': 'ЕГЭ био 21, ОГЭ 4 · таблица опыта: утверждения, проверяемые по данным',
    'b_ploidy': 'ЕГЭ био 3, 27 · число хромосом в клетках растений разных стадий цикла',
    'b_atp': 'ЕГЭ био 3 · энергетический обмен: АТФ, ПВК, CO₂ по числу молекул глюкозы',
    'b_energy': 'ОГЭ био 26 · энергозатраты на тренировку и калорийность обеда',
    'b_mutation': 'ЕГЭ био 27 · замена нуклеотида в матричной цепи → аминокислота',
    'b_table_q': 'ОГЭ био 25 · вычисления по таблице результатов',
    'g_index_table': 'ЕГЭ гео 10 · индексы производства: выбрать регионы по динамике',
    'g_pair': 'ЕГЭ гео 24–25 · пара стран: ВВП на душу, роль сельского хозяйства (World Bank)',
    'g_density_class': 'ЕГЭ гео 20 · страна → интервал плотности населения (World Bank)',
    'g_sunrise': 'ОГЭ гео 17 · восход по московскому времени в равноденствие',
    'g_strata': 'ОГЭ гео 8 · возраст слоёв осадочных пород',
    'g_share': 'ОГЭ гео 13 · доля части в целом, %',
    'g_chart': 'ОГЭ гео 23 · ряд по годам: год максимума/минимума, изменение',
    'g_climtype': 'ЕГЭ гео 27, ОГЭ 18 · климатический пояс по помесячным данным',
    'g_climtable': 'ОГЭ гео 16 · таблица метеостанций: верный вывод',
    'b_orf': 'ЕГЭ био 27 · рамка считывания: белок с первого АУГ',
    'b_nondisj': 'ЕГЭ био 28, 3 · нерасхождение хромосом: число хромосом в гамете/зиготе',
    'b_phylo': 'ЕГЭ био 27 · молекулярные часы: время расхождения видов',
    'b_foodweb2': 'ОГЭ био 21 · пищевая сеть: конкурент и несвязанный организм',
    'g_strata2': 'ОГЭ гео 8 · разрез с магматическим телом (нарушенное залегание)',
    'b_foodweb3': 'ОГЭ био 19 · три характеристики организма по схеме пищевой сети',
    'g_daylen1': 'ОГЭ гео 17 · где 22 июня/22 декабря день самый длинный (1 из 4)',
    'g_chart1': 'ОГЭ гео 23 · год максимума/минимума по ряду (1 из 4)',
    'g_sun1': 'ОГЭ гео 17 · где полуденное Солнце выше/ниже (1 из 4)',
    'g_demo2': 'ЕГЭ гео 15–16 · добыча по запасам, обеспеченность на душу, общий прирост, миграционные потоки',
    'g_demo4': 'ОГЭ гео 23 · таблица демографии 4 субъектов, выбор субъекта по условию',
}


def run_check(c, typ):
    res = CHECKS[typ](c['chk'])
    if isinstance(res, bool):
        return res
    return res == c['a']


def selfcheck(n, seed=2026, probe=3000):
    rows = []
    for typ in GENS:
        cards = unique_cards(typ, n, seed)
        bad = [c for c in cards if not run_check(c, typ)]
        inval = [(c, validate(c)) for c in cards if validate(c)]
        keys = Counter(c['q'] + json.dumps(c.get('o'), ensure_ascii=False) for c in cards)
        dup = sum(v - 1 for v in keys.values()) + sum(v - 1 for v in Counter(c['id'] for c in cards).values())
        cores = len({c['core'] for c in cards})
        rng = random.Random(f'probe-{typ}')
        probe_cards = []
        for _ in range(probe):
            try:
                probe_cards.append(GENS[typ](rng))
            except Skip:
                pass
        cap = len({c['q'] + json.dumps(c.get('o'), ensure_ascii=False) for c in probe_cards})
        capc = len({c['core'] for c in probe_cards})
        rows.append((typ, len(cards), len(bad), len(inval), dup, cores, cap, capc))
        for c in bad[:2]:
            print('  НЕСОВПАДЕНИЕ', typ, c['q'][:120], '| a =', c['a'], '| check =', CHECKS[typ](c['chk']), file=sys.stderr)
        for c, e in inval[:2]:
            print('  НЕВАЛИДНО', typ, e, file=sys.stderr)
    return rows


def unique_cards(typ, n, seed=2026):
    """n различных карточек типа (для выгрузки): генерируем, пока не наберём или не упрёмся."""
    rng = random.Random(f'{seed}-{typ}')
    out, seen, tries = [], set(), 0
    while len(out) < n and tries < n * 20:
        tries += 1
        try:
            c = GENS[typ](rng)
        except Skip:                      # нет данных (например, таблицы станций) — тип пропускаем
            continue
        key = c['q'] + json.dumps(c.get('o'), ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        c['id'] = f'gen-{typ}-{len(out) + 1:04d}'
        out.append(c)
    return out


FOLD_ORDER = ['байкальская складчатость', 'каледонская складчатость', 'герцинская складчатость',
              'мезозойская складчатость', 'кайнозойская (альпийская) складчатость']


def gen_d_tectseq(rng, args, topic='dict'):
    """ЕГЭ гео 13 (тектоника): три структуры земной коры — от более древней складчатости к более молодой."""
    C = FACTS['geo']['classes']['tectonic_age']['items']
    by = {}
    for s_, t in C.items():
        if t in FOLD_ORDER:
            by.setdefault(t, []).append(s_)
    eps = rng.sample(sorted(by), 3)
    pick = [rng.choice(by[e]) for e in eps]
    old_first = rng.random() < 0.6
    order = sorted(range(3), key=lambda i: FOLD_ORDER.index(C[pick[i]]), reverse=not old_first)
    q = (f'Расположите горные сооружения в порядке {"от более древних" if old_first else "от более молодых"} по времени '
         f'складчатости {"к более молодым" if old_first else "к более древним"}')
    return seq_card(topic, q, pick, order, '; '.join(f'{x} — {C[x]}' for x in pick) + '.', {'eng': 'd_tectseq', 'pick': pick, 'old': old_first})


def check_d_tectseq(c):
    C = FACTS['geo']['classes']['tectonic_age']['items']
    return ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: FOLD_ORDER.index(C[c['pick'][i]]), reverse=not c['old']))


def gen_d_regword(rng, args, topic='dict'):
    """ОГЭ гео 2: вписать название — единственное государство-сосед или море субъекта РФ (ответ словом)."""
    (tab, field), kw = parse_args(args)
    R = {k: v for k, v in FACTS['geo'][tab].items() if not v.get('new') and len(v.get(field) or []) == 1}
    x = rng.choice(list(R))
    v = R[x][field][0]
    q = {'borders': f'Субъект Российской Федерации «{x}» граничит только с одним иностранным государством. Назовите это государство.',
         'seas': f'Субъект Российской Федерации «{x}» имеет выход только к одному морю. Назовите это море.'}[field]
    c = card('word', topic, q + ' Ответ запишите словом.', v, f'{x}: {v}.', {'eng': 'd_regword', 'tab': tab, 'field': field, 'x': x})
    return c


def check_d_regword(c):
    return FACTS['geo'][c['tab']][c['x']][c['field']][0]


# ================================================================ прототипы: генератор по спецификации и самопроверка

def gen_d_text17(rng, args, topic='dict'):
    """ЕГЭ 17: текст из 6 предложений, выбрать три о заданном понятии (критерий вида, форма отбора и т. п.).
    Спрашиваем исходное понятие текста или другое, если к нему тоже относятся ровно три предложения."""
    (ref,), kw = parse_args(args)
    T = FACTS[ref.split('/')[0]]['texts17']
    t = rng.choice([x for x in T if not kw.get('topic') or x['topic'] in kw['topic'].split('+')])
    by = Counter(z['c'] for z in t['sentences'])
    alt = [c for c, n in by.items() if n == 3 and c != t['target']]
    target, ask = t['target'], t['ask']
    if alt and t['topic'] == 'species_criteria' and rng.random() < 0.4:
        target = rng.choice(alt)
        ask = re.sub(r'описан \w+ критерий', f'описан {target} критерий', ask)
    good = [i for i, z in enumerate(t['sentences']) if z['c'] == target]
    if len(good) != 3:
        raise Skip(t['title'])
    sents = [re.sub(r'^\(\d+\)\s*', '', z['t']) for z in t['sentences']]
    q = f'{ask} {t["title"]}.'
    return many_card(topic, q, sents, good, f'{cap(target)}: ' + ', '.join(str(i + 1) for i in good) + '.',
                     {'eng': 'd_text17', 'ref': ref, 'title': t['title'], 'target': target})


def check_d_text17(c):
    T = FACTS[c['ref'].split('/')[0]]['texts17']
    t = next(x for x in T if x['title'] == c['title'])
    return [str(i + 1) for i, z in enumerate(t['sentences']) if z['c'] == c['target']]


ASPECT_ORDER = ['строение', 'среда', 'питание', 'размножение', 'значение']


def gen_d_profile(rng, args, topic='dict'):
    """ОГЭ 7: «Известно, что X — [2 признака]. Выберите три утверждения, относящиеся к описанию данных признаков».
    Все шесть утверждений верны; три — о названных признаках, три — о других сторонах жизни организма."""
    (ref,), kw = parse_args(args)
    P = FACTS[ref.split('/')[0]]['organism_profiles']
    group = kw.get('group')
    names = [n for n, v in P.items() if not group or v['group'] in group.split('+')]
    for _ in range(50):
        x = rng.choice(names)
        v = P[x]
        by = {}
        for f in v['facts']:
            by.setdefault(f['aspect'], []).append(f['t'])
        asp = [a for a in by if a in v['about']]
        if len(asp) < 3:
            continue
        pick = rng.sample(asp, 2)
        yes = [t for a in pick for t in by[a]]
        no = [t for a in by if a not in pick for t in by[a]]
        if len(yes) < 3 or len(no) < 3:
            continue
        good = rng.sample(yes, 3)
        items = good + rng.sample(no, 3)
        rng.shuffle(items)
        gi = [i for i, t in enumerate(items) if t in good]
        about = ', '.join(v['about'][a] for a in sorted(pick, key=ASPECT_ORDER.index))
        q = (f'Известно, что {x} — {about}. Используя эти сведения, выберите из приведённого ниже списка три утверждения, '
             'относящиеся к описанию данных признаков этого организма. Запишите в таблицу цифры, соответствующие выбранным ответам.')
        return many_card(topic, q, items, gi, 'О названных признаках: ' + ' '.join(items[i] for i in gi),
                         {'eng': 'd_profile', 'ref': ref, 'x': x, 'pick': pick, 'items': items})
    raise Skip(ref)


def check_d_profile(c):
    v = FACTS[c['ref'].split('/')[0]]['organism_profiles'][c['x']]
    asp = {f['t']: f['aspect'] for f in v['facts']}
    return [str(i + 1) for i, t in enumerate(c['items']) if asp.get(t) in c['pick']]


ENGINES = {k[4:]: (v, globals()['check_' + k[4:]]) for k, v in list(globals().items())
           if k.startswith('gen_d_') and 'check_' + k[4:] in globals()}


def make_gen(spec):
    """Спецификация из поля gen → (gen(rng) → карточка, check(карточка) → bool).

    'd_match:bio/organelles,g=energy' — словарный движок и аргументы;
    'g_demo@mode=migr' — параметрический генератор с фильтром по полю chk (повторяем, пока не совпадёт);
    'A|B' — случайно один из вариантов (прототип покрывают несколько генераторов).
    """
    parts = spec.split('|')
    if len(parts) > 1:
        subs = [make_gen(p) for p in parts]

        def g(rng):
            i = rng.randrange(len(subs))
            c = subs[i][0](rng)
            c['_sub'] = i
            return c
        return g, lambda c: subs[c['_sub']][1](c)
    if '#' in spec:                                   # модификатор формата ответа как в КИМ
        base, _, mod = spec.partition('#')
        g0, c0 = make_gen(base)
        if mod == 'word':
            def g(rng):
                return to_word(g0(rng))
            return g, lambda c: agree_word(c, c0)
        raise ValueError(mod)
    if spec.startswith('d_'):
        name, _, a = spec.partition(':')
        gen, chk = ENGINES[name]
        args = [x for x in a.split(',') if x]
        return (lambda rng: gen(rng, args)), (lambda c: same_answer(chk(c['chk']), c))
    name, _, filt = spec.partition('@')
    want = dict(kv.split('=', 1) for kv in filt.split('&') if kv)

    def g(rng):
        for _ in range(300):
            c = GENS[name](rng)
            if all(str(c['chk'].get(k)) == v for k, v in want.items()):
                return c
        raise Skip(spec)
    return g, lambda c: same_answer(CHECKS[name](c['chk']), c)


def to_word(c):
    """Карточка 1 из 4 → ввод слова (ответ-слово, как в бланке КИМ); варианты остаются в chk для проверки."""
    if c['k'] != 'one':
        return c
    right = next(x['t'] for x in c['o'] if x['id'] == c['a'])
    w = dict(c, k='word', a=right)
    if c['chk'].get('answers'):
        w['alt'] = [x for x in c['chk']['answers'] if x != right]
    w['_one'] = {'o': c['o'], 'a': c['a']}
    w.pop('o')
    w['q'] = re.sub(r'\s*Выберите[^.?]*[.?]?$', '', w['q']).rstrip() + ' Ответ запишите словом (словосочетанием).'
    return w


def agree_word(c, check_one):
    if c['k'] != 'word':
        return check_one(c)
    one_card = dict(c, k='one', o=c['_one']['o'], a=c['_one']['a'])
    return check_one(one_card)


def same_answer(res, c):
    if isinstance(res, bool):
        return res
    if c['k'] == 'match':
        return res == c['x']
    return res == c['a']


def card_key(c):
    return c['q'] + json.dumps(c.get('o'), ensure_ascii=False, sort_keys=True)


def card_text(c):
    o = c.get('o')
    if isinstance(o, dict):
        o = o['left'] + o['right']
    return c['q'] + ' ' + ' '.join(x['t'] for x in (o or []))


def validate(c):
    errs = []
    k = c['k']
    if k == 'num':
        try:
            float(c['a'].replace(',', '.'))
        except ValueError:
            errs.append('ответ не число: ' + c['a'])
    elif k == 'one':
        ids = [x['id'] for x in c['o']]
        texts = [x['t'] for x in c['o']]
        if len(set(texts)) != len(texts):
            errs.append('повторяются варианты')
        if c['a'] not in ids:
            errs.append('ответ не среди вариантов')
        if len(texts) < 2:
            errs.append('мало вариантов')
    elif k == 'many':
        texts = [x['t'] for x in c['o']]
        if len(set(texts)) != len(texts):
            errs.append('повторяются варианты')
        if not c['a'] or not set(c['a']) <= {x['id'] for x in c['o']} or len(c['a']) == len(texts):
            errs.append('неверный набор ответов')
    elif k == 'match':
        L, R = c['o']['left'], c['o']['right']
        if len({x['t'] for x in L}) != len(L) or len({x['t'] for x in R}) != len(R):
            errs.append('повторяются позиции')
        if set(c['a']) != {x['id'] for x in L} or not set(c['a'].values()) <= {x['id'] for x in R}:
            errs.append('ответ не по позициям')
    elif k == 'word':
        if not c['a'] or len(c['a']) > 80:
            errs.append('ответ-слово пустой или слишком длинный')
    elif k == 'flip':
        if not c['a']:
            errs.append('пустой ответ')
    if not c['q'] or not c['e']:
        errs.append('пустой вопрос/пояснение')
    return errs


WORD = re.compile(r'[a-zа-яё0-9]+')


def shingles(text, k=5):
    w = WORD.findall(text.lower().replace('ё', 'е'))
    return {' '.join(w[i:i + k]) for i in range(len(w) - k + 1)}


def fipi_shingles(folder):
    """Шинглы локальных текстов ФИПИ (в репозиторий не кладём: © Рособрнадзор)."""
    S = set()
    for f in sorted(Path(folder).glob('*.txt')):
        S |= shingles(f.read_text('utf-8', errors='ignore'))
    return S


# Стандартные формулы КИМ о форме записи ответа (одинаковы в тысячах заданий; их требует критерий «стиль КИМ»).
# Сходство с ФИПИ меряем по содержанию задания, без этих формул; список — закрытый, в отчёте приведён.
KIM_FORMS = [
    r'запишите в таблицу (выбранные цифры|получившуюся последовательность цифр|соответствующую последовательность цифр|цифры, соответствующие выбранным ответам)( под соответствующими буквами| для каждой величины)?\.?',
    r'к каждой позиции, данной в первом столбце, подберите соответствующую позицию из второго столбца\.?',
    r'для каждой величины определите соответствующий характер её изменения\.?', r'цифры в ответе могут повторяться\.?',
    r'запишите цифры, под которыми они указаны\.?', r'запишите в ответе цифры, под которыми они указаны\.?',
    r'в ответе запишите только число\.?', r'ответ запишите в виде числа\.?', r'полученный результат округлите до [а-яё ]+\.?',
    r'верны ли следующие суждения о', r'верно только а', r'верно только б', r'верны оба суждения', r'оба суждения неверны',
    r'увеличится', r'уменьшится', r'не изменится', r'измерение проводите между центрами условных знаков\.?',
    r'установите последовательность', r'установите соответствие между', r'выберите три верных ответа из шести',
    r'прочитайте текст\.', r'выберите три предложения, в которых', r'(и )?запишите в таблицу цифры, под которыми они указаны\.?',
]
_FORMS_RE = re.compile('|'.join(KIM_FORMS), re.I)


def similarity(c, S):
    sh = shingles(_FORMS_RE.sub(' ', card_text(c)))
    return len(sh & S) / len(sh) if sh else 0.0


def load_protos(subject):
    p = ROOT / 'data' / 'source' / f'{subject}-prototypes.json'
    return p, json.loads(p.read_text('utf-8'))


def run_proto(p, probe, seed=2026, fipi=None):
    """Генерирует до probe попыток: ёмкость (различных карточек), ошибки проверки и сходство с ФИПИ."""
    gen, chk = make_gen(p['gen'])
    rng = random.Random(f'{seed}-{p["id"]}')
    seen, cards, skips, errors = set(), [], 0, []
    for _ in range(probe):
        try:
            c = gen(rng)
        except Skip:
            skips += 1
            continue
        except KeyError as e:                     # нет таблицы/поля — прототип не собирается
            errors.append(str(e))
            continue
        key = card_key(c)
        if key in seen:
            continue
        seen.add(key)
        c['t'] = p['id']
        cards.append(c)
    bad = [c for c in cards if not chk(c)]
    inval = [c for c in cards if validate(c)]
    sim = max((similarity(c, fipi) for c in cards), default=0.0) if fipi else None
    return {'cards': cards, 'bad': bad, 'inval': inval, 'skips': skips, 'sim': sim, 'errors': sorted(set(errors))}


def example_of(c):
    ex = {'k': c['k'], 'q': c['q'], 'a': c['a']}
    if 'o' in c:
        ex['o'] = c['o']
    if 'x' in c:
        ex['x'] = c['x']
    ex['e'] = c['e']
    return ex


# ---------------------------------------------------------------- сверка с форматом КИМ 2027 (data/research/kim-format-2027.json)

KIM = {(k['exam'], k['subj'], k['n']): k for k in
       json.loads((ROOT / 'data' / 'research' / 'kim-format-2027.json').read_text('utf-8'))} if (ROOT / 'data' / 'research' / 'kim-format-2027.json').exists() else {}


def card_shape(c):
    """Формат ответа карточки в терминах КИМ и число элементов."""
    k = c['k']
    if k == 'match':
        return 'digits_match', {'left': len(c['o']['left']), 'right': len(c['o']['right']),
                                'repeat': len(set(c['a'].values())) < len(c['a'])}
    if k == 'many':
        return 'digits_set', {'options': len(c['o']), 'correct': len(c['a'])}
    if k == 'one':
        return 'digits_set', {'options': len(c['o']), 'correct': 1}
    if k == 'word':
        return 'word', {}
    if k in ('num', 'flip'):
        if k == 'num' and ('под соответствующими буквами' in c['q'] or 'в порядке букв' in c['q']):
            return 'digits_match', {'left': len(c['a'])}
        if k == 'num' and ('последовательность цифр' in c['q'] or 'цифры подряд' in c['q']) and re.fullmatch(r'\d+', c['a']):
            return 'digits_seq', {'seq_len': len(c['a'])}
        if k == 'flip' and re.fullmatch(r'[А-ЯЁ]+', c['a']):
            return 'digits_seq', {'seq_len': len(c['a']), 'symbols': 'letters'}
        if k == 'num' and re.fullmatch(r'[1-3]{2,3}', c['a']) and '1 — увеличится' in c['q']:
            return 'digits_match', {'left': len(c['a']), 'right': 3}
        return 'number', {}
    return k, {}


def in_range(v, want):
    if want is None or want == 'any':
        return True
    if isinstance(want, list):
        return want[0] <= v <= want[-1]
    return v == want


def kim_auto(p, cards):
    """Формат и устройство аналогов против эталона КИМ: (format_ok, structure_ok, заметки)."""
    kim = KIM.get((p['exam'], 'bio' if p['id'].startswith('bio') else 'geo', p['n']))
    if not kim or not cards:
        return None
    want = kim['answer'] if isinstance(kim['answer'], list) else [kim['answer']]
    st = kim.get('structure', {})
    fmt_bad, st_bad = set(), set()
    for c in cards:
        a, sh = card_shape(c)
        if want == ['open']:
            fmt_bad.add(f'в КИМ развёрнутый ответ, у нас {a} (шаг задания)')
            continue
        if a not in want:
            fmt_bad.add(f'ответ {a}, в КИМ {"/".join(want)}')
            continue
        for key in ('left', 'right', 'options', 'correct', 'seq_len'):
            if key in sh and key in st and not in_range(sh[key], st[key]):
                st_bad.add(f'{key}: {sh[key]} вместо {st[key]}')
        if 'repeat' in sh and st.get('repeat_digits') is False and sh['repeat']:
            st_bad.add('цифры повторяются, в КИМ — нет')
    return {'format': 'fail' if fmt_bad else 'pass', 'structure': 'fail' if st_bad or fmt_bad else 'pass',
            'notes': sorted(fmt_bad | st_bad)}


def kim_meta(p):
    kim = KIM.get((p['exam'], 'bio' if p['id'].startswith('bio') else 'geo', p['n']))
    if not kim:
        return {}
    return {k: kim.get(k) for k in ('level', 'points', 'time_min', 'answer', 'structure', 'scoring', 'codifier')}


def proto_check(subjects, probe, fipi_dir, write, only=None):
    fipi = fipi_shingles(fipi_dir) if fipi_dir else None
    rows, fail = [], 0
    for subject in subjects:
        path, data = load_protos(subject)
        for p in data['prototypes']:
            if only and not p['id'].startswith(only):
                continue
            g = p['gen']
            if isinstance(g, dict):              # llm / bank — генератора нет, ёмкость оценена в записи
                p.setdefault('fidelity', {})['kim'] = kim_meta(p)
                rows.append((p['id'], g['kind'], None))
                continue
            r = run_proto(p, probe, fipi=fipi)
            n = len(r['cards'])
            fid = p.setdefault('fidelity', {})
            fid['kim'] = kim_meta(p)
            fid['auto'] = kim_auto(p, r['cards'][:300])
            p['capacity'] = n if n < probe * 0.95 else f'≥{n}'
            if r['cards']:
                p['example'] = example_of(r['cards'][0])
            ok = n > 0 and not r['bad'] and not r['inval'] and not r['errors'] and (r['sim'] is None or r['sim'] < 0.3)
            fail += not ok
            rows.append((p['id'], 'gen', r))
            for c in r['bad'][:1]:
                print('  НЕСОВПАДЕНИЕ', p['id'], c['q'][:150], '| a =', c.get('x', c['a']), file=sys.stderr)
            for c in r['inval'][:1]:
                print('  НЕВАЛИДНО', p['id'], validate(c), file=sys.stderr)
            if r['errors']:
                print('  НЕТ ДАННЫХ', p['id'], '; '.join(r['errors'][:3]), file=sys.stderr)
            if n == 0:
                print('  НЕТ КАРТОЧЕК', p['id'], p['gen'], file=sys.stderr)
        if write:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return rows, fail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=200)
    ap.add_argument('--sample', nargs=2, metavar=('TYPE', 'COUNT'))
    ap.add_argument('--dump')
    ap.add_argument('--protos', nargs='*', metavar='SUBJ',
                    help='самопроверка по прототипам data/source/<bio|geo>-prototypes.json')
    ap.add_argument('--probe', type=int, default=1000, help='попыток генерации на прототип')
    ap.add_argument('--fipi', help='папка с локальными текстами ФИПИ (*.txt) для проверки сходства')
    ap.add_argument('--only', help='только прототипы с этим префиксом id')
    ap.add_argument('--write', action='store_true', help='записать capacity и example в JSON прототипов')
    args = ap.parse_args()
    if args.protos is not None:
        subjects = args.protos or ['bio', 'geo']
        rows, fail = proto_check(subjects, args.probe, args.fipi, args.write, args.only)
        print('| Прототип | Карточек (из %d попыток) | Не сошлось | Невалидно | Сходство с ФИПИ |' % args.probe)
        print('|---|---|---|---|---|')
        for pid, kind, r in rows:
            if r is None:
                print(f'| {pid} | {kind} | — | — | — |')
                continue
            sim = '—' if r['sim'] is None else f'{r["sim"]:.0%}'
            print(f'| {pid} | {len(r["cards"])} | {len(r["bad"])} | {len(r["inval"])} | {sim} |')
        gen = [r for _, k, r in rows if r is not None]
        print(f'\nПрототипов: {len(rows)}, с генератором: {len(gen)}, карточек: {sum(len(r["cards"]) for r in gen)}, '
              f'с ошибками: {fail}.')
        sys.exit(1 if fail else 0)
    if args.sample:
        typ, k = args.sample[0], int(args.sample[1])
        for c in unique_cards(typ, k):
            c.pop('core')
            print(json.dumps(c, ensure_ascii=False, indent=1))
        return
    if args.dump:
        allc = []
        for typ in GENS:
            for c in unique_cards(typ, args.n):
                c.pop('core')
                c.pop('chk')
                allc.append(c)
        with open(args.dump, 'w', encoding='utf-8') as f:
            json.dump(allc, f, ensure_ascii=False, indent=0)
        print(f'{len(allc)} карточек → {args.dump}')
        return
    rows = selfcheck(args.n)
    print('| Тип | Что тренирует | Уникальных карточек | Ответ не сошёлся | Невалидных | Дубликатов | Различных по сути | Ёмкость из 3000 попыток: тексты / по сути |')
    print('|---|---|---|---|---|---|---|---|')
    fail = 0
    for typ, n, bad, inval, dup, cores, cap, capc in rows:
        print(f'| `{typ}` | {INFO.get(typ, "")} | {n} | {bad} | {inval} | {dup} | {cores} | {cap} / {capc} |')
        fail += bad + inval + dup
    tot = sum(r[1] for r in rows)
    short = [r[0] for r in rows if r[1] < args.n]
    print(f'\nИтого типов: {len(rows)}, карточек: {tot}, ошибок (ответ, структура, дубликаты): {fail}.'
          + (f' Меньше {args.n} разных карточек (ёмкость исчерпана или нет данных): {", ".join(short)}.' if short else ''))
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
