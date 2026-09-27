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
        elif a in ('each', 'diff', 'obj', 'prop', 'cls', 'rev', 'max', 'min', 'ru', 'world'):
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


def seq_card(topic, q, shown, order, e, chk):
    """shown — перемешанные тексты, order — индексы shown в верном порядке."""
    ans = ''.join(str(i + 1) for i in order)
    q = q + ': ' + '; '.join(f'{i + 1}) {t}' for i, t in enumerate(shown)) + '. Запишите последовательность цифр.'
    c = card('num', topic, q, ans, e, chk)
    c['x'] = ans
    return c


def cap(s):
    return s[:1].upper() + s[1:]


# ---------------------------------------------------------------- sets: объекты × свойства

def set_matrix(S):
    objs = S['objects']
    return objs, [(p['t'], set(p['yes'])) for p in S['props']]


def pool_of(S, kw):
    g = kw.get('g')
    if g:
        return list(S['groups'][g])
    return list(S['objects'])


def gen_d_match(rng, args, topic='dict'):
    """Соответствие «характеристика → объект» (ЕГЭ 6, 10, 14, 19; ОГЭ 11): 2–3 объекта, 5–6 характеристик."""
    (ref,), kw = parse_args(args)
    S = table(ref, 'sets')
    objs, props = set_matrix(S)
    pool = pool_of(S, kw)
    k = int(kw.get('k', rng.choice([2, 2, 3] if len(pool) >= 3 else [2])))
    n = int(kw.get('n', 6))
    for _ in range(60):
        chosen = rng.sample(pool, min(k, len(pool)))
        cand = [(t, [o for o in chosen if o in y]) for t, y in props]
        cand = [(t, hit[0]) for t, hit in cand if len(hit) == 1]
        by = {o: [t for t, h in cand if h == o] for o in chosen}
        if any(len(v) < 1 for v in by.values()) or len(cand) < n:
            continue
        pick = [rng.choice(by[o]) for o in chosen]                # каждому объекту — хотя бы одна
        rest = [t for t, _ in cand if t not in pick]
        pick += rng.sample(rest, n - len(pick))
        rng.shuffle(pick)
        right = sorted(chosen, key=lambda o: objs.index(o))
        who = {t: h for t, h in cand}
        ans = [right.index(who[t]) for t in pick]
        if len(set(ans)) < 2:
            continue
        q = (f'Установите соответствие между характеристиками и {S.get("q_obj", "объектами")}: к каждой позиции, '
             'данной в первом столбце, подберите соответствующую позицию из второго столбца.')
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


def gen_d_many(rng, args, topic='dict'):
    """3 верных из 6 (ЕГЭ 7, 11, 15, 18; ОГЭ 9, 17). Режим diff: признаки X, которых нет у Y."""
    (ref,), kw = parse_args(args)
    S = table(ref, 'sets')
    objs, props = set_matrix(S)
    pool = pool_of(S, kw)
    n_true = int(kw.get('t', 3))
    n_all = int(kw.get('n', 6))
    for _ in range(60):
        if kw.get('diff'):
            if len(pool) < 2:
                raise Skip(ref)
            x, y = rng.sample(pool, 2)
            good = [t for t, s in props if x in s and y not in s]
            bad = [t for t, s in props if y in s and x not in s] + [t for t, s in props if x in s and y in s]
            q = (f'Какие признаки отличают объект «{x}» от объекта «{y}»? Выберите {n_true} верных ответа '
                 f'из {n_all} и запишите цифры, под которыми они указаны.')
        else:
            x = rng.choice(pool)
            others = [o for o in pool if o != x]
            good = [t for t, s in props if x in s and not set(pool) <= s]
            bad = [t for t, s in props if x not in s and s & set(others)]
            y = None
            q = (f'{S["title"]}. Объект: {x}. Выберите {n_true} верные для него характеристики из {n_all} '
                 'и запишите цифры, под которыми они указаны.')
        if len(good) < n_true or len(bad) < n_all - n_true:
            continue
        items = rng.sample(good, n_true) + rng.sample(bad, n_all - n_true)
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
    """Один из четырёх: признак объекта или объект по признаку (ОГЭ 8, 14, 15; текстовая замена рисунков)."""
    (ref,), kw = parse_args(args)
    S = table(ref, 'sets')
    objs, props = set_matrix(S)
    pool = pool_of(S, kw)
    by_obj = kw.get('obj') or (not kw.get('prop') and rng.random() < 0.5)
    for _ in range(60):
        if by_obj:                                   # «Для какого объекта характерно …?»
            t, s = rng.choice(props)
            yes = [o for o in pool if o in s]
            no = [o for o in pool if o not in s]
            if len(yes) < 1 or len(no) < 3:
                continue
            x = rng.choice(yes)
            o, a = one(rng, x, rng.sample(no, 3))
            q = f'{S["title"]}. Для какого объекта характерно: {t}?'
            return card('one', topic, q, a, f'{cap(t)} — {x}.', {'eng': 'd_one', 'ref': ref, 'mode': 'obj', 't': t, 'opts': [z['t'] for z in o]}, o=o)
        x = rng.choice(pool)
        good = [t for t, s in props if x in s and not set(pool) <= s]
        bad = [t for t, s in props if x not in s and s & set(pool)]
        if not good or len(bad) < 3:
            continue
        t = rng.choice(good)
        o, a = one(rng, t, rng.sample(bad, 3))
        q = f'{S["title"]}. Какая характеристика относится к объекту «{x}»?'
        return card('one', topic, q, a, f'{cap(x)}: {t}.', {'eng': 'd_one', 'ref': ref, 'mode': 'prop', 'x': x, 'opts': [z['t'] for z in o]}, o=o)
    raise Skip(ref)


def check_d_one(c):
    S = table(c['ref'], 'sets')
    yes = {p['t']: set(p['yes']) for p in S['props']}
    if c['mode'] == 'obj':
        ok = [i for i, o in enumerate(c['opts']) if o in yes[c['t']]]
    else:
        ok = [i for i, t in enumerate(c['opts']) if c['x'] in yes[t]]
    return 'абвгде'[ok[0]] if len(ok) == 1 else None


JUDGE = ['верно только А', 'верно только Б', 'верны оба суждения', 'оба суждения неверны']


def gen_d_judge(rng, args, topic='dict'):
    """Верны ли суждения А и Б (ОГЭ 12). Истинность — по матрице набора."""
    (ref,), kw = parse_args(args)
    S = table(ref, 'sets')
    objs, props = set_matrix(S)
    pool = pool_of(S, kw)
    want = rng.choice([(1, 0), (0, 1), (1, 1), (0, 0)])
    sts = []
    for truth in want:
        for _ in range(60):
            x = rng.choice(pool)
            t, s = rng.choice(props)
            if (x in s) == bool(truth) and s & set(pool) and not set(pool) <= s:
                if (x, t) not in [(a, b) for a, b, _ in sts]:
                    sts.append((x, t, truth))
                    break
        else:
            raise Skip(ref)
    ans = {(1, 0): 0, (0, 1): 1, (1, 1): 2, (0, 0): 3}[want]
    o = [{'id': 'абвг'[i], 't': t} for i, t in enumerate(JUDGE)]
    q = (f'{S["title"]}. Верны ли суждения? А. {cap(sts[0][0])}: {sts[0][1]}. Б. {cap(sts[1][0])}: {sts[1][1]}.')
    e = f'А — {"верно" if sts[0][2] else "неверно"}, Б — {"верно" if sts[1][2] else "неверно"}.'
    return card('one', topic, q, 'абвг'[ans], e, {'eng': 'd_judge', 'ref': ref, 'st': [[x, t] for x, t, _ in sts]}, o=o)


def check_d_judge(c):
    S = table(c['ref'], 'sets')
    yes = {p['t']: set(p['yes']) for p in S['props']}
    A, B = (x in yes[t] for x, t in c['st'])
    return 'абвг'[{(True, False): 0, (False, True): 1, (True, True): 2, (False, False): 3}[(A, B)]]


def attr_pairs(S, attr):
    vals = S['attrs'][attr]
    return {o: v for o, v in vals.items() if list(vals.values()).count(v) == 1}


def gen_d_analogy(rng, args, topic='dict'):
    """Аналогия «объект — значение» (ЕГЭ 1, ОГЭ 8): по образцу найти пропуск. Для sets[attrs] и classes."""
    (ref,), kw = parse_args(args)
    if kw.get('cls'):
        C = table(ref, 'classes')
        items = C['items']
        x, y = rng.sample(list(items), 2)
        if items[x] == items[y] and rng.random() < 0.7:
            x, y = rng.sample(list(items), 2)
        vy = items[y]
        wrong = [c for c in C['classes'] if c != vy]
        if len(wrong) < 3:
            raise Skip(ref)
        o, a = one(rng, vy, rng.sample(wrong, 3))
        title = C['title']
        chk = {'eng': 'd_analogy', 'ref': ref, 'cls': True, 'y': y, 'opts': [z['t'] for z in o]}
        vx = items[x]
    else:
        S = table(ref, 'sets')
        attr = kw.get('a') or rng.choice(list(S['attrs']))
        pairs = attr_pairs(S, attr)
        if len(pairs) < 4:
            raise Skip(ref)
        x, y = rng.sample(list(pairs), 2)
        vx, vy = pairs[x], pairs[y]
        o, a = one(rng, vy, rng.sample([v for k, v in pairs.items() if k not in (x, y)], 3))
        title = f'{S["title"]} ({attr})'
        chk = {'eng': 'd_analogy', 'ref': ref, 'attr': attr, 'y': y, 'opts': [z['t'] for z in o]}
    q = f'{title}. Образец: «{x}» — «{vx}». Что нужно вписать на место пропуска: «{y}» — …?'
    return card('one', topic, q, a, f'{cap(y)} — {vy}.', chk, o=o)


def check_d_analogy(c):
    if c.get('cls'):
        v = table(c['ref'], 'classes')['items'][c['y']]
    else:
        v = table(c['ref'], 'sets')['attrs'][c['attr']][c['y']]
    ok = [i for i, t in enumerate(c['opts']) if t == v]
    return 'абвгде'[ok[0]] if len(ok) == 1 else None


def gen_d_table(rng, args, topic='dict'):
    """Таблица (ЕГЭ 20): 3 строки × 2 атрибута, 3 пропуска А–В, список из 6 элементов."""
    (ref,), kw = parse_args(args)
    S = table(ref, 'sets')
    attrs = [a for a in S.get('attrs', {}) if len(attr_pairs(S, a)) >= 4]
    if len(attrs) < 1:
        raise Skip(ref)
    cols = rng.sample(attrs, min(2, len(attrs)))
    rows = [o for o in S['objects'] if all(o in attr_pairs(S, a) for a in cols)]
    if len(rows) < 4:
        raise Skip(ref)
    rows = rng.sample(rows, 3)
    cells = [(r, a) for r in rows for a in cols]
    hide = rng.sample(cells, 3)
    hide.sort(key=lambda ra: cells.index(ra))
    true = [attr_pairs(S, a)[r] for r, a in hide]
    distr = [v for a in cols for o, v in attr_pairs(S, a).items() if v not in true and o not in rows]
    if len(distr) < 3:
        raise Skip(ref)
    items = true + rng.sample(sorted(set(distr)), 3)
    rng.shuffle(items)
    lines = []
    for r in rows:
        cellv = []
        for a in cols:
            if (r, a) in hide:
                cellv.append(f'({LET[hide.index((r, a))]})')
            else:
                cellv.append(attr_pairs(S, a)[r])
        lines.append(f'{r} | ' + ' | '.join(cellv))
    q = (f'{S["title"]}. Таблица «объект | {" | ".join(cols)}»: ' + '; '.join(lines) +
         '. Для каждой буквы выберите элемент из списка: ' + '; '.join(f'{i + 1}) {t}' for i, t in enumerate(items)) +
         '. Запишите цифры в порядке А, Б, В.')
    ans = ''.join(str(items.index(v) + 1) for v in true)
    c = card('num', topic, q, ans, '; '.join(f'{LET[i]} — {v}' for i, v in enumerate(true)) + '.',
             {'eng': 'd_table', 'ref': ref, 'hide': hide, 'items': items})
    c['x'] = ans
    return c


def check_d_table(c):
    S = table(c['ref'], 'sets')
    out = ''
    for r, a in c['hide']:
        v = S['attrs'][a][r]
        hits = [i for i, t in enumerate(c['items']) if t == v]
        if len(hits) != 1:
            return None
        out += str(hits[0] + 1)
    return out


# ---------------------------------------------------------------- seqs, classes, effects, texts

def gen_d_seq(rng, args, topic='dict'):
    """Последовательность (ЕГЭ 8, 16; ОГЭ 5): 5–6 шагов процесса, взятых в исходном порядке и перемешанных."""
    (ref,), kw = parse_args(args)
    Q = table(ref, 'seqs')
    steps = Q['steps']
    m = min(int(kw.get('m', rng.choice([5, 6]))), len(steps))
    if m < 4:
        raise Skip(ref)
    if rng.random() < 0.5 and len(steps) > m:                  # подряд идущие шаги
        s0 = rng.randrange(len(steps) - m + 1)
        idx = list(range(s0, s0 + m))
    else:
        idx = sorted(rng.sample(range(len(steps)), m))
    shown = idx[:]
    rng.shuffle(shown)
    order = sorted(range(m), key=lambda j: shown[j])
    e = 'Порядок: ' + ' → '.join(steps[i] for i in idx) + '.'
    return seq_card(topic, Q['q'], [steps[i] for i in shown], order, e, {'eng': 'd_seq', 'ref': ref, 'shown': [steps[i] for i in shown]})


def check_d_seq(c):
    steps = table(c['ref'], 'seqs')['steps']
    pos = [steps.index(t) for t in c['shown']]
    return ''.join(str(j + 1) for j in sorted(range(len(pos)), key=lambda j: pos[j]))


def gen_d_class(rng, args, topic='dict'):
    """Отнести элементы к классам (ОГЭ 2, 18; ЕГЭ 19): k классов, n элементов; each — по одному на класс."""
    (ref,), kw = parse_args(args)
    C = table(ref, 'classes')
    by = {}
    for it, cl in C['items'].items():
        by.setdefault(cl, []).append(it)
    classes = [c for c in C['classes'] if len(by.get(c, [])) >= 1]
    k = min(int(kw.get('k', rng.choice([2, 3]))), len(classes))
    n = int(kw.get('n', 6 if k <= 3 else k))
    if k < 2:
        raise Skip(ref)
    for _ in range(60):
        cls = rng.sample(classes, k)
        if kw.get('each'):
            items = [rng.choice(by[c]) for c in cls]
        else:
            pool = [it for c in cls for it in by[c]]
            if len(pool) < n:
                continue
            items = [rng.choice(by[c]) for c in cls]
            items += rng.sample([it for it in pool if it not in items], n - k)
        rng.shuffle(items)
        right = [c for c in C['classes'] if c in cls]
        ans = [right.index(C['items'][it]) for it in items]
        q = C.get('q', f'Установите соответствие: {C["title"]}') + ': к каждой позиции первого столбца подберите позицию из второго.'
        e = '; '.join(f'{it} — {C["items"][it]}' for it in items) + '.'
        return match_card(topic, q, items, right, ans, e, {'eng': 'd_class', 'ref': ref, 'items': items, 'right': right})
    raise Skip(ref)


def check_d_class(c):
    C = table(c['ref'], 'classes')
    return ''.join(str(c['right'].index(C['items'][it]) + 1) for it in c['items'])


CHANGE = ['увеличится', 'уменьшится', 'не изменится']


def gen_d_change(rng, args, topic='dict'):
    """Как изменится величина (ЕГЭ 2): ситуация, 2–3 величины, ответы 1/2/3, цифры могут повторяться."""
    (ref,), kw = parse_args(args)
    E = FACTS[ref.split('/')[0]]['effects']
    keys = [k for k in E if k.startswith(kw.get('p', ''))]
    name = rng.choice(keys)
    sit = E[name]
    vals = list(sit['values'])
    m = min(int(kw.get('m', rng.choice([2, 3]))), len(vals))
    pick = rng.sample(vals, m)
    ans = [CHANGE.index(sit['values'][v]) for v in pick]
    q = f'{sit["situation"]}. Как изменятся при этом величины? Для каждой величины определите характер её изменения'
    c = match_card(topic, q + '.', pick, CHANGE, ans, '; '.join(f'{v} — {sit["values"][v]}' for v in pick) + '.',
                   {'eng': 'd_change', 'ref': ref, 'sit': name, 'pick': pick})
    return c


def check_d_change(c):
    sit = FACTS[c['ref'].split('/')[0]]['effects'][c['sit']]
    return ''.join(str(CHANGE.index(sit['values'][v]) + 1) for v in c['pick'])


def gen_d_text(rng, args, topic='dict'):
    """Вставить термины в текст (ОГЭ 10, ЕГЭ гео 5): свой текст со слотами, список = ответы + шум."""
    (ref,), kw = parse_args(args)
    ns, key = ref.split('/', 1)
    T = [t for t in FACTS[ns][key] if not kw.get('topic') or t.get('topic') == kw['topic']]
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
    q = (f'Вставьте в текст пропущенные термины из списка: {text} Список: ' +
         '; '.join(f'{i + 1}) {x}' for i, x in enumerate(items)) + f'. Запишите цифры в порядке {", ".join(slots)}.')
    c = card('num', topic, q, ans, '; '.join(f'{s} — {t["slots"][s]}' for s in slots) + '.',
             {'eng': 'd_text', 'ref': ref, 'text': t['t'], 'items': items})
    c['x'] = ans
    return c


def check_d_text(c):
    ns, key = c['ref'].split('/', 1)
    t = next(x for x in FACTS[ns][key] if x['t'] == c['text'])
    return ''.join(str(c['items'].index(t['slots'][s]) + 1) for s in t['slots'])

# ---------------------------------------------------------------- география: таблицы с числами и тегами

def geo_rows(tab):
    """Строки таблицы geo-facts как {название: запись}; у стран — по школьному названию."""
    G = FACTS['geo']
    if tab == 'countries':
        return {r['name']: r for r in G['countries'].values()}
    if tab == 'stations':
        return {r['name']: r for r in G.get('stations', [])}
    if tab == 'capitals':
        return {r['name']: {'lat': v[0], 'lon': v[1]} for r in G['countries'].values()
                if len(r.get('capital_coords', {})) == 1 for v in r['capital_coords'].values()}
    return G[tab]


def geo_value(tab, row, field):
    """Значение показателя и год (или None). Производные поля считаются здесь же."""
    if tab == 'countries':
        wb = row['wb']
        if field == 'natinc':                        # естественный прирост, ‰
            if 'birth' in wb and 'death' in wb:
                return round(wb['birth'][0] - wb['death'][0], 1), wb['birth'][1]
            return None
        if field in wb:
            return wb[field][0], wb[field][1]
        return None
    if tab == 'stations':
        t, p = row.get('t'), row.get('p')
        if field == 't_jan' and t:
            return t[0], row.get('period')
        if field == 't_jul' and t:
            return t[6], row.get('period')
        if field == 'amp' and t:
            return round(max(t) - min(t), 1), row.get('period')
        if field == 'p_year' and p:
            return round(sum(p)), row.get('period')
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
    rel = field not in ('t_jan', 't_jul', 'natinc')
    gap = float(kw.get('gap', 1.3 if rel else 3))
    for _ in range(80):
        pick = rng.sample(list(vals), k)
        if not spaced([vals[p][0] for p in pick], gap, rel):
            continue
        asc = rng.random() < 0.5
        order = sorted(range(k), key=lambda i: vals[pick[i]][0], reverse=not asc)
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
        yes = [r for r in rows if has(rows[r])]
        no = [r for r in rows if not has(rows[r]) and not rows[r].get('new')]
        yes = [r for r in yes if not rows[r].get('new')]
        if len(yes) < k or len(no) < n - k:
            raise Skip(f'{tab}.{field}={tag}')
        items = rng.sample(yes, k) + rng.sample(no, n - k)
        rng.shuffle(items)
        good = [i for i, x in enumerate(items) if x in yes]
        phrase = TAG_Q.get((field, tag_v), f'есть признак «{tag}» ({field})')
        q = f'Выберите {k} {noun} из списка, в которых {phrase}. Запишите цифры, под которыми они указаны'
        e = 'Верно: ' + ', '.join(items[i] for i in good) + '.'
        return many_card(topic, q + '.', items, good, e, {'eng': 'd_pick', 'tab': tab, 'field': field, 'tag': tag_v, 'items': items})
    what, label, unit, srcname = ORDER_Q[(tab, field)]
    rows = geo_filter(tab, geo_rows(tab), kw)
    vals = {x: geo_value(tab, r, field) for x, r in rows.items()}
    vals = {x: v for x, v in vals.items() if v is not None and v[0] is not None}
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
        q = (f'Выберите {k} {noun} с {"наибольшей" if top else "наименьшей"} величиной показателя: {label}. '
             'Запишите цифры, под которыми они указаны.')
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
    e = f'{x}: центр {pts[x][0]}°, {pts[x][1]}°; ближе всех к точке ({lat}°, {lon}°).'
    return card('one', topic, q, a, e, {'eng': 'd_coords', 'tab': tab, 'pt': [lat, lon], 'opts': [z['t'] for z in o]}, o=o)


def check_d_coords(c):
    rows = geo_rows(c['tab'])
    def pt(k):
        r = rows[k]
        return (r['center_lat'], r['center_lon']) if c['tab'] == 'ru_subjects' else (r['lat'], r['lon'])
    d = [dist_km(tuple(c['pt']), pt(k)) for k in c['opts']]
    return 'абвгде'[d.index(min(d))]


def gen_d_statements(rng, args, topic='dict'):
    """Высказывания о процессе (ЕГЭ гео 12, ОГЭ 22): свой банк с тегами; k верных из n."""
    (ref, tag), kw = parse_args(args)
    ns, key = ref.split('/', 1)
    B = FACTS[ns][key]
    k, n = int(kw.get('k', rng.choice([2, 3])) ), int(kw.get('n', 5))
    near = [t for t in kw.get('near', '').split('+') if t in B] or [t for t in B if t != tag]
    good = rng.sample(B[tag]['items'], k)
    bad_pool = [s for t in near for s in B[t]['items']]
    bad = rng.sample(bad_pool, n - k)
    items = good + bad
    rng.shuffle(items)
    gi = [i for i, s in enumerate(items) if s in good]
    q = (f'Какие из высказываний относятся к явлению «{B[tag]["title"]}»? Запишите цифры, под которыми они указаны')
    return many_card(topic, q + '.', items, gi, 'Верно: ' + ' '.join(items[i] for i in gi),
                     {'eng': 'd_statements', 'ref': ref, 'tag': tag, 'items': items})


def check_d_statements(c):
    ns, key = c['ref'].split('/', 1)
    B = FACTS[ns][key]
    return [str(i + 1) for i, s in enumerate(c['items']) if s in B[c['tag']]['items']]



# ---- новые параметрические генераторы по прототипам (этап «прототипы → аналоги»)

# график/таблица опыта (ЕГЭ 21, ОГЭ 4): свои контексты; утверждения — только проверяемые по данным
GRAPH_CTX = [
    ('температура', '°C', [5, 10, 15, 20, 25, 30, 35, 40], 'скорость фотосинтеза элодеи', 'пузырьков O₂/мин', 'bell'),
    ('температура', '°C', [10, 20, 30, 35, 40, 50, 60], 'активность фермента амилазы', 'усл. ед.', 'bell'),
    ('освещённость', 'тыс. лк', [0, 5, 10, 15, 20, 25, 30], 'скорость фотосинтеза', 'мг CO₂/ч', 'sat'),
    ('концентрация CO₂', '%', [0.01, 0.02, 0.04, 0.06, 0.08, 0.1], 'интенсивность фотосинтеза', 'усл. ед.', 'sat'),
    ('концентрация субстрата', 'ммоль/л', [1, 2, 4, 6, 8, 10, 12], 'скорость ферментативной реакции', 'мкмоль/мин', 'sat'),
    ('время после посева', 'ч', [0, 2, 4, 6, 8, 10, 12], 'число бактерий в колонии', 'тыс.', 'grow'),
    ('концентрация соли', '%', [0, 0.5, 1, 1.5, 2, 3, 4], 'масса кусочков картофеля после опыта', 'г', 'decline'),
    ('pH среды', '', [2, 3, 4, 5, 6, 7, 8, 9], 'активность пепсина', 'усл. ед.', 'bell'),
    ('время бега', 'мин', [0, 5, 10, 15, 20, 25, 30], 'частота сердечных сокращений', 'уд./мин', 'sat'),
    ('возраст', 'лет', [10, 20, 30, 40, 50, 60, 70], 'жизненная ёмкость лёгких', 'л', 'bell'),
    ('доза удобрения', 'кг/га', [0, 20, 40, 60, 80, 100, 120], 'урожайность пшеницы', 'ц/га', 'bell'),
    ('температура воды', '°C', [0, 5, 10, 15, 20, 25, 30], 'содержание растворённого кислорода', 'мг/л', 'decline'),
    ('время после приёма пищи', 'ч', [0, 0.5, 1, 1.5, 2, 3, 4], 'концентрация глюкозы в крови', 'ммоль/л', 'bell'),
    ('концентрация пестицида', 'мг/л', [0, 1, 2, 3, 4, 5, 6], 'выживаемость личинок комаров', '%', 'decline'),
    ('глубина', 'м', [0, 5, 10, 20, 30, 40, 50], 'численность водорослей', 'тыс./л', 'decline'),
]


def graph_series(rng, shape, n):
    """Целые значения ряда заданной формы, без случайных совпадений соседей."""
    if shape == 'bell':
        peak = rng.randrange(2, n - 1)
        up = sorted(rng.sample(range(5, 90), peak))
        down = sorted(rng.sample(range(5, up[-1]), n - peak - 1), reverse=True)
        top = up[-1] + rng.randint(4, 15)
        return up + [top] + down
    if shape == 'sat':
        k = rng.randrange(3, n - 1)
        up = sorted(rng.sample(range(5, 90), k))
        return up + [up[-1]] * (n - k)
    if shape == 'grow':
        v = [rng.randint(2, 9)]
        for _ in range(n - 1):
            v.append(v[-1] * 2 if rng.random() < 0.75 else v[-1] * 2 + rng.randint(1, 5))
        return v
    return sorted(rng.sample(range(5, 99), n), reverse=True)     # decline


def graph_statements(xs, ys, fx, fy, xu):
    """(текст, верно по данным?) — только утверждения, которые можно проверить по таблице."""
    n = len(xs)
    X = lambda i: f'{fmt(Fraction(str(xs[i])))}{" " + xu if xu else ""}'
    fx = f'значении фактора «{fx}»'
    imax = max(range(n), key=lambda i: ys[i])
    imin = min(range(n), key=lambda i: ys[i])
    out = []                                  # при повторе максимума/минимума утверждение неоднозначно — не берём
    if ys.count(ys[imax]) == 1:
        out.append((f'наибольшее значение показателя «{fy}» отмечено при {fx} {X(imax)}', True))
    if ys.count(ys[imin]) == 1:
        out.append((f'наименьшее значение показателя «{fy}» отмечено при {fx} {X(imin)}', True))
    alt = (imax + 2) % n
    if ys[alt] != ys[imax]:
        out.append((f'наибольшее значение показателя «{fy}» отмечено при {fx} {X(alt)}', False))
    for a in range(n - 2):
        b = a + 2
        seg = ys[a:b + 1]
        if all(p < q for p, q in zip(seg, seg[1:])):
            out.append((f'в интервале от {X(a)} до {X(b)} показатель растёт', True))
            out.append((f'в интервале от {X(a)} до {X(b)} показатель снижается', False))
        elif all(p > q for p, q in zip(seg, seg[1:])):
            out.append((f'в интервале от {X(a)} до {X(b)} показатель снижается', True))
            out.append((f'в интервале от {X(a)} до {X(b)} показатель растёт', False))
        elif all(p == q for p, q in zip(seg, seg[1:])):
            out.append((f'в интервале от {X(a)} до {X(b)} показатель не меняется', True))
    out.append((f'показатель растёт на всём изученном интервале', all(p < q for p, q in zip(ys, ys[1:]))))
    out.append((f'показатель снижается на всём изученном интервале', all(p > q for p, q in zip(ys, ys[1:]))))
    i, j = sorted((0, n - 1))
    out.append((f'при {X(n - 1)} значение показателя больше, чем при {X(0)}', ys[-1] > ys[0]))
    out.append((f'при {X(0)} значение показателя больше, чем при {X(n - 1)}', ys[0] > ys[-1]))
    return out


def gen_b_graph(rng):
    fx, xu, xs, fy, yu, shape = rng.choice(GRAPH_CTX)
    ys = graph_series(rng, shape, len(xs))
    sts = graph_statements(xs, ys, fx, fy, xu)
    good = [s for s, ok in sts if ok]
    bad = [s for s, ok in sts if not ok]
    k = rng.choice([2, 2, 3])
    if len(good) < k or len(bad) < 5 - k:
        return gen_b_graph(rng)
    items = rng.sample(good, k) + rng.sample(bad, 5 - k)
    rng.shuffle(items)
    gi = [i for i, s in enumerate(items) if s in good]
    table_ = '; '.join(f'{fmt(Fraction(str(x)))} → {y}' for x, y in zip(xs, ys))
    q = (f'Исследователь изучал, как {fx} ({xu or "ед."}) влияет на показатель «{fy}» ({yu}). Результаты: {table_}. '
         f'Выберите утверждения, которые можно сформулировать на основании этих данных.')
    c = many_card('bio-ege-21', q, items, gi, 'По таблице: ' + '; '.join(items[i] for i in gi) + '.',
                  {'xs': xs, 'ys': ys, 'fx': fx, 'fy': fy, 'xu': xu, 'items': items})
    return c


def check_b_graph(c):
    truth = dict(graph_statements(c['xs'], c['ys'], c['fx'], c['fy'], c['xu']))
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
PLANT_2N = [8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 36, 40, 42, 48]


def gen_b_ploidy(rng):
    sp = rng.choice(list(PLOIDY))
    cell = rng.choice(list(PLOIDY[sp]))
    k = PLOIDY[sp][cell]
    shown_cell = rng.choice([c for c in PLOIDY[sp] if PLOIDY[sp][c] != k] or [cell])
    n = rng.choice(PLANT_2N) // 2
    given = n * PLOIDY[sp][shown_cell]
    ans = n * k
    q = (f'У {sp} {shown_cell} содержит {given} хромосом(ы). Сколько хромосом содержит {cell}? '
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
    return 'абвгде'[c['opts'].index(aa)]


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
    """ЕГЭ гео 10: индексы производства (% к предыдущему году), условные данные; выбрать регионы по критерию."""
    crit = rng.choice(list(INDEX_Q))
    text, f = INDEX_Q[crit]
    regs = rng.sample(ru_subject_names(), 4)
    years = rng.choice([(2021, 2022, 2023), (2022, 2023, 2024), (2019, 2020, 2021)])
    for _ in range(100):
        rows = [[rng.choice([rng.randint(88, 99), rng.randint(101, 114)]) + rng.choice([0, 0.5]) for _ in years] for _ in regs]
        good = [i for i, r in enumerate(rows) if f(r)]
        if 1 <= len(good) <= 2:
            break
    else:
        return gen_g_index_table(rng)
    branch = rng.choice(['промышленного производства', 'продукции сельского хозяйства'])
    tab = '; '.join(f'{i + 1}) {g}: ' + ', '.join(f'{y} — {fmt(Fraction(str(v)))}' for y, v in zip(years, r))
                    for i, (g, r) in enumerate(zip(regs, rows)))
    q = (f'Индексы {branch} (в % к предыдущему году; условные данные): {tab}. В каких регионах {text}? '
         'Запишите цифры, под которыми они указаны.')
    c = many_card('geo-ege-10', q, regs, good, 'Индекс больше 100 % — рост, меньше 100 % — сокращение.',
                  {'rows': rows, 'crit': crit})
    return c


def check_g_index_table(c):
    out = []
    for i, r in enumerate(c['rows']):
        ok = {'grow_each': min(r) > 100, 'fall_each': max(r) < 100, 'fall_last': r[-1] < 100, 'grow_first': r[0] > 100}[c['crit']]
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
    return 'абвгде'[c['opts'].index(C[win]['name'])]


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
        o = [{'id': 'абвгд'[i], 't': t} for i, t in enumerate(labels)]
        q = f'Определите, к какому интервалу средней плотности населения (чел./км²) относится страна {C[iso]["name"]}.'
        e = f'{C[iso]["name"]}: ≈ {r} чел./км² (World Bank, {C[iso]["wb"]["density"][1]}).'
        return card('one', 'geo-ege-20', q, 'абвгд'[k], e, {'iso': iso}, o=o)


def check_g_density_class(c):
    d = wbv(c['iso'], 'density')
    for i, (lo, hi) in enumerate(DENS_SCALE):
        if hi is None or d < hi + 0.5:
            return 'абвгд'[i]


def gen_g_sunrise(rng):
    """ОГЭ гео 17: где раньше взойдёт Солнце по московскому времени (равноденствие: решает долгота)."""
    cs = [c for c in CITIES if CITIES[c][3] is not None]
    for _ in range(100):
        pick = rng.sample(cs, 3)
        lons = sorted(CITIES[c][2] for c in pick)
        if min(b - a for a, b in zip(lons, lons[1:])) >= 4:
            break
    day = rng.choice(['21 марта', '23 сентября'])
    first = max(pick, key=lambda c: CITIES[c][2])
    o, a = one(rng, first, [c for c in pick if c != first], n=3)
    q = f'{day} в каком из городов Солнце раньше всего по московскому времени поднимется над горизонтом?'
    e = f'В дни равноденствия восход раньше там, где восточнее: {first} ({fmt(CITIES[first][2])}° в. д.).'
    return card('one', 'geo-oge-17', q, a, e, {'pick': pick, 'opts': [x['t'] for x in o]}, o=o)


def check_g_sunrise(c):
    # восход по всемирному времени в равноденствие: 6 ч − λ/15 (без учёта рефракции) — меньше у восточного
    t = {x: 6 - CITIES[x][2] / 15 for x in c['opts']}
    return 'абвгде'[c['opts'].index(min(t, key=t.get))]


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
                    {'layers': layers, 'shown': shown, 'old': old_first})


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
    return [s for s in FACTS['geo'].get('stations', []) if s.get('t') and s.get('p') and len(s['t']) == 12 and len(s['p']) == 12]


def gen_g_climtype(rng):
    """ЕГЭ гео 27 / ОГЭ 18: по помесячным t и осадкам определить тип климата (1 из 4)."""
    S = stations_full()
    types = sorted({s['type'] for s in S if s.get('type')})
    if len(types) < 4:
        raise Skip('stations')
    s = rng.choice([x for x in S if x.get('type')])
    wrong = rng.sample([t for t in types if t != s['type']], 3)
    o, a = one(rng, s['type'], wrong)
    q = ('Климатические данные пункта (без названия). Средняя температура по месяцам (°C, янв.–дек.): '
         + ', '.join(fmt(Fraction(str(x))) for x in s['t']) + '. Осадки (мм): ' + ', '.join(str(round(x)) for x in s['p']) +
         f'. Широта пункта {abs(round(s["lat"]))}° {"с. ш." if s["lat"] >= 0 else "ю. ш."}. Определите тип климата.')
    return card('one', 'geo-ege-27', q, a, f'Это {s["name"]} ({s["country"]}): {s["type"]}.', {'name': s['name'], 'opts': [x['t'] for x in o]}, o=o)


def check_g_climtype(c):
    s = next(x for x in stations_full() if x['name'] == c['name'])
    return 'абвгде'[c['opts'].index(s['type'])]


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
    return 'абвгде'[ok[0]] if len(ok) == 1 else None


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
    'g_climtype': 'ЕГЭ гео 27, ОГЭ 18 · тип климата по помесячным данным',
    'g_climtable': 'ОГЭ гео 16 · таблица метеостанций: верный вывод',
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


# ================================================================ прототипы: генератор по спецификации и самопроверка

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
    if spec.startswith('d_'):
        name, _, a = spec.partition(':')
        gen, chk = ENGINES[name]
        args = [x for x in a.split(',') if x]
        return (lambda rng: gen(rng, args)), (lambda c: agree(chk(c['chk']), c))
    name, _, filt = spec.partition('@')
    want = dict(kv.split('=', 1) for kv in filt.split('&') if kv)

    def g(rng):
        for _ in range(300):
            c = GENS[name](rng)
            if all(str(c['chk'].get(k)) == v for k, v in want.items()):
                return c
        raise Skip(spec)
    return g, lambda c: agree(CHECKS[name](c['chk']), c)


def agree(res, c):
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


def similarity(c, S):
    sh = shingles(card_text(c))
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
        key = card_key(c)
        if key in seen:
            continue
        seen.add(key)
        c['t'] = p['id']
        cards.append(c)
    bad = [c for c in cards if not chk(c)]
    inval = [c for c in cards if validate(c)]
    sim = max((similarity(c, fipi) for c in cards), default=0.0) if fipi else None
    return {'cards': cards, 'bad': bad, 'inval': inval, 'skips': skips, 'sim': sim}


def example_of(c):
    ex = {'k': c['k'], 'q': c['q'], 'a': c['a']}
    if 'o' in c:
        ex['o'] = c['o']
    if 'x' in c:
        ex['x'] = c['x']
    ex['e'] = c['e']
    return ex


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
                rows.append((p['id'], g['kind'], None))
                continue
            r = run_proto(p, probe, fipi=fipi)
            n = len(r['cards'])
            p['capacity'] = n if n < probe * 0.95 else f'≥{n}'
            if r['cards']:
                p['example'] = example_of(r['cards'][0])
            ok = n > 0 and not r['bad'] and not r['inval'] and (r['sim'] is None or r['sim'] < 0.3)
            fail += not ok
            rows.append((p['id'], 'gen', r))
            for c in r['bad'][:1]:
                print('  НЕСОВПАДЕНИЕ', p['id'], c['q'][:150], '| a =', c.get('x', c['a']), file=sys.stderr)
            for c in r['inval'][:1]:
                print('  НЕВАЛИДНО', p['id'], validate(c), file=sys.stderr)
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
        fail += bad + inval + dup + (n < args.n)
    tot = sum(r[1] for r in rows)
    print(f'\nИтого типов: {len(rows)}, карточек: {tot}, ошибок (ответ, структура, дубликаты, недобор): {fail}.')
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
