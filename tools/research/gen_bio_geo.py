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
import sys
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP, getcontext
from fractions import Fraction
from math import gcd
from functools import reduce

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
    ids = 'абвгде'
    o = [{'id': ids[i], 't': t} for i, t in enumerate(opts)]
    return o, ids[opts.index(correct)]


def card(kind, topic, q, a, e, chk, o=None, core=None):
    c = {'k': kind, 't': topic, 'q': q, 'a': a, 'e': e, 'src': 'gen:' + kind, 'chk': chk}
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
    q = (f'В соматических клетках {org} {n2} хромосом(ы). Сколько {what} содержится {ph}? '
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
    mode = rng.choice(['mrna', 'dna2', 'dna1', 'trna', 'triplets', 'back', 'len'])
    if mode == 'back':
        q = (f'Фрагмент иРНК (без стоп-кодона) содержит {3 * n} нуклеотидов. Сколько аминокислот '
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
        q = (f'Белок состоит из {n} аминокислот. Сколько {what}? Стоп-кодон и некодирующие '
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
    if mode == 'need':
        top = rng.choice([1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50])
        ans = top * 10 ** (L - 1)
        q = (f'Пищевая цепь: {" → ".join(ch)}. На основании правила 10 % рассчитайте массу (кг) '
             f'организмов первого звена ({ch[0]}), необходимую для существования {ch[-1]} массой {top} кг. '
             'В ответе запишите только число.')
        e = f'Звеньев {L}, переходов {L - 1}: {top} × 10^{L - 1} = {ans} кг.'
        chk = {'L': L, 'mode': mode, 'x': top}
    elif mode == 'energy':
        k = rng.randint(2, L)
        e1 = rng.choice([10, 20, 50, 100, 200, 500]) * 10 ** rng.randint(2, 5)
        ans = Fraction(e1, 10 ** (k - 1))
        q = (f'Пищевая цепь: {" → ".join(ch)}. Продуценты накопили {e1} кДж энергии. '
             f'Сколько энергии (кДж) перейдёт к организмам {k}-го трофического уровня ({ch[k - 1]}) '
             'по правилу 10 %? В ответе запишите только число.')
        e = f'С каждого уровня на следующий переходит 10 %: {e1} / 10^{k - 1} = {fmt(ans)} кДж.'
        ans = fmt(ans)
        chk = {'L': L, 'mode': mode, 'x': e1, 'k': k}
    else:
        m1 = rng.choice([100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000])
        ans = Fraction(m1, 10 ** (L - 1))
        q = (f'Пищевая цепь: {" → ".join(ch)}. Биомасса первого звена ({ch[0]}) — {m1} кг. '
             f'Какая масса (кг) последнего звена ({ch[-1]}) может прокормиться по правилу 10 %? '
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
    inc = rng.random() < 0.3
    p1, p2 = rng.choice([('Aa', 'Aa'), ('Aa', 'aa'), ('AA', 'aa'), ('AA', 'Aa'), ('Aa', 'Aa'), ('Aa', 'aa')])
    g = cross1(p1, p2)
    if inc:
        org, ph_aa, ph_Aa, ph_a = rng.choice(INCOMPLETE)
        desc = {'AA': ph_aa, 'Aa': ph_Aa, 'aa': ph_a}
        intro = f'У растений/животных ({org}) при неполном доминировании AA — {ph_aa}, Aa — {ph_Aa}, aa — {ph_a}.'
        phen = {desc[k]: v for k, v in g.items() if v}
    else:
        org, dom, rec = rng.choice(TRAITS)
        desc = {'AA': dom, 'Aa': dom, 'aa': rec}
        intro = f'У организма ({org}) признак «{dom}» доминирует над «{rec}».'
        phen = Counter()
        for k, v in g.items():
            if v:
                phen[desc[k]] += v
    word = lambda gt: {'AA': 'гомозиготную доминантную', 'Aa': 'гетерозиготную', 'aa': 'гомозиготную рецессивную'}[gt]
    word2 = lambda gt: {'AA': 'гомозиготной доминантной', 'Aa': 'гетерозиготной', 'aa': 'гомозиготной рецессивной'}[gt]
    parents = f'Скрестили {word(p1)} особь ({p1}) с {word2(p2)} ({p2}).'
    mode = rng.choice(['phen', 'gen', 'prob', 'nphen'])
    if mode in ('phen', 'gen') and sum(1 for v in g.values() if v) == 1:
        mode = 'prob'                      # потомство однородно — «соотношение» бессмысленно
    if mode == 'phen':
        r = ratio([int(v * 4) for v in phen.values()])
        q = f'{intro} {parents} Определите соотношение фенотипов потомков. Ответ запишите в виде последовательности цифр в порядке их убывания.'
        a = seq(r)
    elif mode == 'gen':
        r = ratio([int(v * 4) for v in g.values() if v])
        q = f'{intro} {parents} Определите соотношение генотипов потомков. Ответ запишите в виде последовательности цифр в порядке их убывания.'
        a = seq(r)
    elif mode == 'prob':
        gt = rng.choice(GENO1)
        q = f'{intro} {parents} Какова вероятность (%) появления {GNAME[gt]} потомков? В ответе запишите только число.'
        a = fmt(g[gt] * 100)
    else:
        q = f'{intro} {parents} Сколько фенотипических классов получится в потомстве? В ответе запишите только число.'
        a = str(len(phen))
    tab = ', '.join(f'{k} — {fmt(v * 100)} %' for k, v in g.items() if v)
    e = f'Генотипы потомков: {tab}.'
    chk = {'p1': p1, 'p2': p2, 'inc': inc, 'mode': mode, 'gt': gt if mode == 'prob' else None}
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
    mode = rng.choice(['phen', 'prob', 'gam', 'nphen'])
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
        if p1.count('a') + p1.count('b') + p2.count('a') + p2.count('b') and ('Aa' in p1 + p2 or 'Bb' in p1 + p2):
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
        target = rng.choice(list(phen))
        name = {'A_B_': 'с обоими доминантными признаками', 'A_bb': 'с доминантным первым и рецессивным вторым признаком',
                'aaB_': 'с рецессивным первым и доминантным вторым признаком', 'aabb': 'с обоими рецессивными признаками'}[target]
        q = q0 + f' Какова вероятность (%) появления потомков {name}? Ответ округлите до сотых.'
        a = fmt(phen[target] * 100, 2)
        mode = 'prob:' + target
    e = 'Фенотипы: ' + ', '.join(f'{k} — {fmt(v * 100, 2)} %' for k, v in phen.items()) + '. Признаки наследуются независимо, вероятности перемножаются.'
    return card('num', 'bio-ege-4', q, a, e, {'p1': p1, 'p2': p2, 'mode': mode})


def check_b_dihybrid(c):
    if c['mode'] == 'gam':
        return str(len(set(gametes(c['gt']))))
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
    return fmt(Fraction(ph[c['mode'].split(':')[1]] * 100, tot), 2)


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
    mode = rng.choice(['p', 'p', 'n', 'rh'])
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
    dist = rng.randint(1, 49)
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
        q = (f'При анализирующем скрещивании дигетерозиготы {geno} с ab//ab получено потомство: '
             + ', '.join(f'{g} — {n}' for g, n in zip(cls, counts))
             + '. Определите расстояние между генами A и B (сМ). В ответе запишите только число.')
        e = f'Кроссоверных потомков {rec // 2} + {rec // 2} = {rec} из {total}: {rec} / {total} × 100 = {dist} сМ.'
        return card('num', 'bio-ege-4', q, str(dist), e, {'mode': 'rev', 'cls': cls, 'counts': counts, 'cis': cis})
    cls = rng.choice(['AaBb', 'aabb', 'Aabb', 'aaBb'])
    val = Fraction(100 - dist, 2) if cls in parental else Fraction(dist, 2)
    q = (f'Гены A и B сцеплены, расстояние между ними {dist} морганид (сМ). Дигетерозиготную особь {geno} '
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
    row = rng.choice(TAXA)
    ranks = RANKS_A if row[0] == 'Животные' else RANKS_P
    avail = [i for i, x in enumerate(row) if x]
    k = rng.choice([5, 5, 6])
    pick = sorted(rng.sample(avail, min(k, len(avail))))
    items = [(i, f'{ranks[i]} {row[i]}' if rng.random() < 0.5 else row[i]) for i in pick]
    shown = items[:]
    rng.shuffle(shown)
    top_down = rng.random() < 0.5
    order = sorted(shown, key=lambda x: x[0], reverse=not top_down)
    ans = ''.join(str(shown.index(x) + 1) for x in order)
    lst = '; '.join(f'{j + 1}) {t}' for j, (_, t) in enumerate(shown))
    q = (f'Установите последовательность систематических групп, начиная с {"самого крупного" if top_down else "самого мелкого"} '
         f'таксона: {lst}. Запишите последовательность цифр.')
    e = 'Порядок рангов: ' + ' → '.join(ranks[i] for i in pick) + '.'
    return card('num', 'bio-ege-12', q, ans, e,
                {'row': row[-1], 'shown': [i for i, _ in shown], 'top_down': top_down})


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


def gen_g_time(rng):
    a, b = rng.sample(list(CITIES), 2)
    h = rng.randint(0, 23)
    ua, ub = CITIES[a][3], CITIES[b][3]
    if ua == ub:
        return gen_g_time(rng)
    ans = (h + ub - ua) % 24
    q = (f'Трансляция началась в {h} ч по местному времени города {a}. Который час (ч) по местному '
         f'времени был в этот момент в городе {b}? Используйте часовые зоны России. Ответ запишите в виде числа.')
    e = (f'{a}: UTC+{ua} (МСК{ua - 3:+d}), {b}: UTC+{ub} (МСК{ub - 3:+d}). Разница {ub - ua:+d} ч: '
         f'{h} {"+" if ub >= ua else "−"} {abs(ub - ua)} = {ans} ч.')
    return card('num', 'geo-ege-14', q, str(ans), e, {'a': a, 'b': b, 'h': h})


def check_g_time(c):
    ua, ub = CITIES[c['a']][3], CITIES[c['b']][3]
    t = dt.datetime(2026, 5, 12, c['h'], 0, tzinfo=dt.timezone(dt.timedelta(hours=ua)))
    return str(t.astimezone(dt.timezone(dt.timedelta(hours=ub))).hour)


def gen_g_newyear(rng):
    while True:
        cs = rng.sample(list(CITIES), 3)
        if len({CITIES[c][3] for c in cs}) == 3:
            break
    regs = [CITIES[c][0] for c in cs]
    order = sorted(range(3), key=lambda i: -CITIES[cs[i]][3])
    ans = ''.join(str(i + 1) for i in order)
    q = ('Расположите регионы России в той последовательности, в которой их жители встречают Новый год: '
         + '; '.join(f'{i + 1}) {r}' for i, r in enumerate(regs)) + '. Запишите последовательность цифр.')
    e = 'Раньше встречают там, где больше смещение от UTC: ' + ', '.join(f'{r} — МСК{CITIES[c][3] - 3:+d}' for r, c in zip(regs, cs)) + '.'
    return card('num', 'geo-oge-26', q, ans, e, {'cs': cs})


def check_g_newyear(c):
    moments = []
    for i, city in enumerate(c['cs']):
        tz = dt.timezone(dt.timedelta(hours=CITIES[city][3]))
        moments.append((dt.datetime(2027, 1, 1, tzinfo=tz).astimezone(dt.timezone.utc), i))
    return ''.join(str(i + 1) for _, i in sorted(moments))


def gen_g_sollon(rng):
    gh, gm = rng.randint(0, 23), rng.choice([0, 20, 40])
    lon = rng.randint(1, 179)
    east = rng.random() < 0.5
    minutes = lon * 4
    t0 = gh * 60 + gm
    tl = (t0 + minutes) % 1440 if east else (t0 - minutes) % 1440
    fh = lambda m: f'{m // 60} ч {m % 60:02d} мин'
    q = (f'Определите географическую долготу пункта, если в {fh(t0)} по солнечному времени гринвичского меридиана '
         f'местное солнечное время в нём {fh(tl)}. Пункт находится ближе к гринвичскому меридиану, чем к 180-му.')
    ok = f'{lon}° {"в.д." if east else "з.д."}'
    wrong = [f'{lon}° {"з.д." if east else "в.д."}', f'{(lon + 1) if lon < 179 else lon - 2}° {"в.д." if east else "з.д."}',
             f'{min(179, round(lon * 1.5)) if lon * 1.5 != lon else lon + 3}° {"в.д." if east else "з.д."}',
             f'{max(1, lon - 5)}° {"з.д." if east else "в.д."}']
    o, a = one(rng, ok, wrong)
    e = f'1 ч = 15°, 4 мин = 1°. Разница {fh(minutes)} = {lon}°. Местное время {"больше" if east else "меньше"} гринвичского — {"восточное" if east else "западное"} полушарие.'
    return card('one', 'geo-ege-28', q, a, e, {'t0': t0, 'tl': tl, 'ok': ok}, o=o)


def check_g_sollon(c):
    d = (c['tl'] - c['t0']) % 1440
    if d > 720:
        d -= 1440
    lon = abs(d) / 4
    return f'{int(lon)}° {"в.д." if d > 0 else "з.д."}' == c['ok']


def gen_g_meridian(rng):
    lon = rng.randint(1, 179)
    hemi = rng.choice(['в.д.', 'з.д.'])
    p1 = rng.randint(0, 80)
    p2 = rng.randint(0, 80)
    s1, s2 = rng.choice(['с.ш.', 'ю.ш.']), rng.choice(['с.ш.', 'ю.ш.'])
    lat1 = p1 if s1 == 'с.ш.' else -p1
    lat2 = p2 if s2 == 'с.ш.' else -p2
    if lat1 == lat2:
        return gen_g_meridian(rng)
    ans = abs(lat1 - lat2) * 111
    q = (f'Определите расстояние (км) по меридиану между точками {p1}° {s1} {lon}° {hemi} и {p2}° {s2} {lon}° {hemi}. '
         'Длину дуги 1° меридиана примите равной 111 км. Ответ запишите в виде числа.')
    e = (f'Разность широт: {"|" + str(p1) + " − " + str(p2) + "|" if s1 == s2 else str(p1) + " + " + str(p2)} = '
         f'{abs(lat1 - lat2)}°; {abs(lat1 - lat2)} × 111 = {ans} км. Точки в разных полушариях — широты складываются.')
    return card('num', 'geo-ege-28', q, str(ans), e, {'lat1': lat1, 'lat2': lat2},
                core={'d': abs(lat1 - lat2), 'same': s1 == s2})


def check_g_meridian(c):
    # длина дуги как доля окружности 360° × 111 км на градус
    arc_deg = abs(c['lat1'] - c['lat2'])
    return str(round(arc_deg / 360 * 360 * 111))


def gen_g_scale(rng):
    scale = rng.choice([1000, 2000, 5000, 10000, 25000, 50000, 100000, 200000, 500000, 1000000, 2500000, 5000000])
    mode = rng.choice(['dist', 'named', 'map'])
    if mode == 'dist':
        mm = rng.randint(5, 250)
        m = Fraction(mm, 1000) * scale
        unit = 'м' if m < 10000 else 'км'
        val = m if unit == 'м' else m / 1000
        ans = fmt(Fraction(fmt(val / 10, 0)) * 10 if unit == 'м' and m >= 100 else val, 1)
        q = (f'Расстояние на карте масштаба 1:{sp(scale)} между двумя пунктами {fmt(Fraction(mm, 10))} см. '
             f'Определите расстояние на местности ({unit}).'
             + (' Результат округлите до десятков метров.' if unit == 'м' and m >= 100 else ''))
        e = f'В 1 см {fmt(Fraction(scale, 100))} м: {fmt(Fraction(mm, 10))} × {fmt(Fraction(scale, 100))} = {fmt(m)} м.'
        chk = {'mode': mode, 'scale': scale, 'mm': mm}
    elif mode == 'named':
        q = f'Численный масштаб карты 1:{sp(scale)}. Сколько метров на местности соответствует 1 см на карте?'
        ans = fmt(Fraction(scale, 100))
        e = f'1:{sp(scale)} — в 1 см {sp(scale)} см = {ans} м.'
        chk = {'mode': mode, 'scale': scale}
    else:
        km = rng.choice([0.5, 1, 1.5, 2, 3, 4, 5, 8, 10, 12, 20, 25, 40, 50, 100, 150, 200])
        cm = Fraction(str(km)) * 100000 / scale
        if cm < Fraction(1, 2) or cm > 40 or (cm * 10).denominator != 1:
            return gen_g_scale(rng)
        ans = fmt(cm)
        q = f'Расстояние на местности {fmt(km)} км. Каким будет расстояние (см) на карте масштаба 1:{sp(scale)}?'
        e = f'{fmt(km)} км = {fmt(Fraction(str(km)) * 100000)} см; {fmt(Fraction(str(km)) * 100000)} : {scale} = {ans} см.'
        chk = {'mode': mode, 'scale': scale, 'km': km}
    return card('num', 'geo-oge-9', q, ans, e, chk)


def check_g_scale(c):
    s = c['scale']
    if c['mode'] == 'named':
        return fmt(Fraction(s, 100))
    if c['mode'] == 'map':
        return fmt(Fraction(str(c['km'])) * 100000 / s)
    m = Fraction(c['mm'], 1000) * s
    if m < 10000:
        return fmt(half_up(m, -1)) if m >= 100 else fmt(m, 1)
    return fmt(m / 1000, 1)


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
    mode = rng.choice(['temp', 'temp_up', 'press', 'height'])
    if mode == 'temp':
        h = rng.choice(range(500, 8001, 250))
        t0 = rng.randint(-10, 35)
        ans = fmt(t0 - Fraction(6, 1000) * h, 1)
        q = (f'Температура воздуха у подножия горы (уровень моря) {t0} °С. Определите температуру (°С) на вершине высотой {h} м, '
             'если она понижается на 0,6 °С на каждые 100 м. Ответ запишите в виде числа.')
        e = f'{h} / 100 × 0,6 = {fmt(Fraction(6, 1000) * h)} °С; {t0} − {fmt(Fraction(6, 1000) * h)} = {ans} °С.'
        chk = {'mode': mode, 'h': h, 't0': t0}
    elif mode == 'temp_up':
        h = rng.choice(range(500, 6001, 500))
        t1 = rng.randint(-30, 10)
        ans = fmt(t1 + Fraction(6, 1000) * h, 1)
        q = (f'На вершине горы высотой {h} м температура {t1} °С. Какая температура (°С) в это время у подножия (уровень моря), '
             'если на каждые 100 м она меняется на 0,6 °С? Ответ запишите в виде числа.')
        e = f'{t1} + {h} / 100 × 0,6 = {ans} °С.'
        chk = {'mode': mode, 'h': h, 't1': t1}
    elif mode == 'press':
        h = rng.choice(range(100, 3001, 100))
        p0 = rng.choice([750, 755, 760, 765, 770])
        ans = str(p0 - h // 10)
        q = (f'У подножия холма давление {p0} мм рт. ст. Каким будет давление на высоте {h} м над подножием, '
             'если оно понижается на 1 мм рт. ст. на каждые 10 м подъёма? Ответ запишите в виде числа.')
        e = f'{h} / 10 = {h // 10} мм; {p0} − {h // 10} = {ans}.'
        chk = {'mode': mode, 'h': h, 'p0': p0}
    else:
        p0 = rng.choice([750, 755, 760, 765])
        dp = rng.randint(5, 150)
        ans = str(dp * 10)
        q = (f'У подножия горы давление {p0} мм рт. ст., на вершине {p0 - dp} мм рт. ст. Определите относительную высоту горы (м), '
             'если давление падает на 1 мм рт. ст. на каждые 10 м. Ответ запишите в виде числа.')
        e = f'{p0} − {p0 - dp} = {dp} мм; {dp} × 10 = {ans} м.'
        chk = {'mode': mode, 'p0': p0, 'dp': dp}
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
    return str(c['dp'] * 10)


# максимальное содержание водяного пара (г/м³) при температуре — школьная справочная таблица
SAT = {-20: 1, -10: 2, 0: 5, 10: 9, 20: 17, 30: 30}


def gen_g_humidity(rng):
    mode = rng.choice(['rh', 'order', 'abs', 'order_a', 'press'])
    if mode == 'rh':
        t = rng.choice(list(SAT))
        a = rng.randint(1, SAT[t])
        ans = fmt(Fraction(100 * a, SAT[t]), 0)
        q = (f'При температуре {t} °С в 1 м³ воздуха может содержаться не более {SAT[t]} г водяного пара. '
             f'Фактически содержится {a} г. Определите относительную влажность (%). Ответ округлите до целого.')
        e = f'{a} / {SAT[t]} × 100 % = {ans} %.'
        return card('num', 'geo-ege-2', q, ans, e, {'mode': mode, 't': t, 'a': a})
    if mode == 'abs':
        t = rng.choice(list(SAT))
        rh = rng.choice([10, 20, 25, 40, 50, 60, 75, 80, 100])
        if SAT[t] * rh % 100:
            return gen_g_humidity(rng)
        ans = str(SAT[t] * rh // 100)
        q = (f'При температуре {t} °С насыщенный воздух содержит {SAT[t]} г/м³ водяного пара. Сколько граммов пара '
             f'содержится в 1 м³ воздуха при относительной влажности {rh} %? Ответ запишите в виде числа.')
        return card('num', 'geo-ege-2', q, ans, f'{SAT[t]} × {rh} / 100 = {ans} г.', {'mode': mode, 't': t, 'rh': rh})
    if mode == 'order_a':
        t = rng.choice([t for t in SAT if SAT[t] >= 5])
        aa = rng.sample(range(1, SAT[t] + 1), 3)
        q = (f'В пунктах 1, 2 и 3 температура воздуха одинакова ({t:+d} °С), содержание водяного пара: '
             + '; '.join(f'{i + 1}) {x} г/м³' for i, x in enumerate(aa))
             + '. Расположите пункты в порядке понижения относительной влажности. Запишите последовательность цифр.')
        ans = ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: -aa[i]))
        return card('num', 'geo-ege-2', q, ans, 'При одной температуре относительная влажность пропорциональна содержанию пара.',
                    {'mode': mode, 't': t, 'aa': aa})
    if mode == 'press':
        ps = rng.sample(range(560, 771), 3)
        up = rng.random() < 0.5
        q = ('На метеостанциях 1, 2 и 3 на склоне горы одновременно измерили давление: '
             + '; '.join(f'{i + 1}) {p} мм рт. ст.' for i, p in enumerate(ps))
             + f'. Расположите метеостанции в порядке {"увеличения" if up else "уменьшения"} их высоты. Запишите последовательность цифр.')
        ans = ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: -ps[i] if up else ps[i]))
        return card('num', 'geo-ege-2', q, ans, 'С высотой давление понижается: выше станция — ниже давление.',
                    {'mode': mode, 'ps': ps, 'up': up})
    # order: одинаковое содержание пара — чем теплее, тем ниже относительная влажность
    a = rng.choice([1, 2, 5, 9])
    ts = rng.sample([t for t in SAT if SAT[t] >= a], 3)
    q = ('В пунктах 1, 2 и 3 одновременно измерили содержание водяного пара и температуру: '
         + '; '.join(f'{i + 1}) {a} г/м³, {t:+d} °С' for i, t in enumerate(ts))
         + '. Расположите пункты в порядке повышения относительной влажности. Запишите последовательность цифр.')
    order = sorted(range(3), key=lambda i: -ts[i])
    ans = ''.join(str(i + 1) for i in order)
    e = 'При одинаковом содержании пара относительная влажность выше там, где холоднее (меньше насыщение).'
    return card('num', 'geo-ege-2', q, ans, e, {'mode': mode, 'a': a, 'ts': ts})


def check_g_humidity(c):
    m = c['mode']
    if m == 'rh':
        return fmt(half_up(Fraction(100 * c['a'], SAT[c['t']]), 0))
    if m == 'abs':
        return str(round(SAT[c['t']] * c['rh'] / 100))
    if m == 'order_a':
        return ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: Fraction(c['aa'][i], SAT[c['t']]), reverse=True))
    if m == 'press':
        import math
        h = [18400 * math.log10(760 / p) for p in c['ps']]   # барометрическая ступень: высота монотонно растёт при падении P
        return ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: h[i], reverse=not c['up']))
    rh = [c['a'] / SAT[t] for t in c['ts']]
    return ''.join(str(i + 1) for i in sorted(range(3), key=lambda i: rh[i]))


REGIONS_AREA = None  # площади регионов здесь не используются — задачи на плотность с условными числами


def gen_g_demo(rng):
    mode = rng.choice(['density', 'natural', 'migr', 'urban', 'supply', 'reserves', 'birth'])
    if mode == 'density':
        pop = rng.randint(100, 9000) * 1000
        area = rng.randint(5, 900) * 1000
        ans = fmt(Fraction(pop, area), 1)
        q = (f'Численность населения региона {sp(pop)} человек, площадь {sp(area)} км². Определите среднюю плотность '
             'населения (чел./км²). Ответ округлите до десятых.')
        e = f'{pop} / {area} = {ans} чел./км².'
        chk = {'mode': mode, 'pop': pop, 'area': area}
    elif mode == 'natural':
        pop = rng.randint(200, 5000) * 1000
        b = rng.randint(5, 20) * pop // 1000 + rng.randint(-200, 200)
        d = rng.randint(8, 18) * pop // 1000 + rng.randint(-200, 200)
        ans = fmt(Fraction((b - d) * 1000, pop), 1)
        q = (f'В регионе с численностью населения {sp(pop)} человек за год родилось {sp(b)} и умерло {sp(d)} человек. '
             'Определите естественный прирост (‰). Ответ округлите до десятых.')
        e = f'({b} − {d}) / {pop} × 1000 = {ans} ‰.'
        chk = {'mode': mode, 'pop': pop, 'b': b, 'd': d}
    elif mode == 'migr':
        p1 = rng.randint(200, 5000) * 1000 + rng.randint(0, 999)
        nat = rng.randint(-15000, 8000)
        mig = rng.randint(-12000, 12000)
        p2 = p1 + nat + mig
        ans = str(mig)
        q = (f'Численность населения региона на 1 января 2025 г. — {sp(p1)} человек, на 1 января 2026 г. — {sp(p2)}. '
             f'Естественный прирост за 2025 г. составил {sp(nat)} человек. Определите миграционный прирост (человек). '
             'Ответ запишите в виде числа.')
        e = f'Общий прирост {p2 - p1}; миграционный = общий − естественный = {p2 - p1} − ({nat}) = {mig}.'
        chk = {'mode': mode, 'p1': p1, 'p2': p2, 'nat': nat}
    elif mode == 'urban':
        tot = rng.randint(300, 9000) * 1000
        urb = rng.randint(20, 95) * tot // 100 + rng.randint(-500, 500)
        ans = fmt(Fraction(urb * 100, tot), 1)
        q = (f'В регионе проживает {sp(tot)} человек, из них в городах — {sp(urb)}. Определите долю городского населения (%). '
             'Ответ округлите до десятых.')
        e = f'{urb} / {tot} × 100 = {ans} %.'
        chk = {'mode': mode, 'tot': tot, 'urb': urb}
    elif mode == 'supply':
        prod = rng.randint(50, 5000)
        years = rng.randint(10, 300)
        res = prod * years
        ans = str(years)
        q = (f'Разведанные запасы ресурса в стране — {sp(res)} млн т, годовая добыча — {sp(prod)} млн т. '
             'Определите ресурсообеспеченность (лет). Ответ запишите в виде числа.')
        e = f'{res} / {prod} = {years} лет.'
        chk = {'mode': mode, 'res': res, 'prod': prod}
    elif mode == 'reserves':
        prod = rng.randint(50, 5000)
        years = rng.randint(10, 300)
        ans = str(prod * years)
        q = (f'Годовая добыча ресурса — {sp(prod)} млн т, ресурсообеспеченность — {years} лет. Определите величину '
             'разведанных запасов (млн т). Ответ запишите в виде числа.')
        e = f'{prod} × {years} = {ans} млн т.'
        chk = {'mode': mode, 'prod': prod, 'years': years}
    else:
        pop = rng.randint(200, 9000) * 1000
        rate = Fraction(rng.randint(50, 250), 10)
        b = int(rate * pop / 1000)
        ans = fmt(Fraction(b * 1000, pop), 1)
        q = (f'В стране с населением {sp(pop)} человек за год родилось {sp(b)} детей. Определите коэффициент рождаемости (‰). '
             'Ответ округлите до десятых.')
        e = f'{b} / {pop} × 1000 = {ans} ‰.'
        chk = {'mode': mode, 'pop': pop, 'b': b}
    return card('num', 'geo-ege-16', q, ans, e, chk)


def check_g_demo(c):
    m = c['mode']
    F = Fraction
    if m == 'density':
        return fmt(F(c['pop'], c['area']), 1)
    if m == 'natural':
        return fmt(F((c['b'] - c['d']) * 1000, c['pop']), 1)
    if m == 'migr':
        return str((c['p2'] - c['p1']) - c['nat'])
    if m == 'urban':
        return fmt(F(c['urb'] * 100, c['tot']), 1)
    if m == 'supply':
        return fmt(F(c['res'], c['prod']))
    if m == 'reserves':
        return str(c['prod'] * c['years'])
    return fmt(F(c['b'] * 1000, c['pop']), 1)


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
    q = (f'Расположите города в порядке {"увеличения" if asc else "уменьшения"} продолжительности светового дня {day}: '
         + '; '.join(f'{i + 1}) {c}' for i, c in enumerate(cs)) + '. Запишите последовательность цифр.')
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
         + '; '.join(f'{i + 1}) {x}' for i, x in enumerate(pick)) + '. Запишите последовательность цифр.')
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


# ================================================================ реестр и самопроверка

GENS = {k[4:]: v for k, v in globals().items() if k.startswith('gen_')}
CHECKS = {k[6:]: v for k, v in globals().items() if k.startswith('check_')}

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
}


def validate(c):
    errs = []
    if c['k'] == 'num':
        s = c['a'].replace(',', '.')
        try:
            float(s)
        except ValueError:
            errs.append('ответ не число: ' + c['a'])
    elif c['k'] == 'one':
        ids = [x['id'] for x in c['o']]
        texts = [x['t'] for x in c['o']]
        if len(set(texts)) != len(texts):
            errs.append('повторяются варианты')
        if c['a'] not in ids:
            errs.append('ответ не среди вариантов')
        if len(texts) < 3:
            errs.append('мало вариантов')
    if not c['q'] or not c['e']:
        errs.append('пустой вопрос/пояснение')
    return errs


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
        probe_cards = [GENS[typ](rng) for _ in range(probe)]
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
        c = GENS[typ](rng)
        key = c['q'] + json.dumps(c.get('o'), ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        c['id'] = f'gen-{typ}-{len(out) + 1:04d}'
        out.append(c)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=200)
    ap.add_argument('--sample', nargs=2, metavar=('TYPE', 'COUNT'))
    ap.add_argument('--dump')
    args = ap.parse_args()
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
        fail += bad + inval + dup + (n < args.n)
    tot = sum(r[1] for r in rows)
    print(f'\nИтого типов: {len(rows)}, карточек: {tot}, ошибок (ответ, структура, дубликаты, недобор): {fail}.')
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
