"""Прототипы «Химия: расчёты и физхимия».

ЕГЭ (КИМ 2027): 18 — скорость реакции; 21 — среда растворов (последовательность по pH; в банке также соответствия
«соль — среда / гидролиз»); 22 — смещение равновесия; 23 — равновесные концентрации; 26 — растворы (массовая доля,
молярная концентрация); 27 — тепловой эффект, объёмные отношения газов; 28 — примеси, выход, избыток, расчёт по
уравнению; 34 — комбинированная расчётная задача (числовой итог решения).
ОГЭ (КИМ 2027): 18 — массовая доля элемента; 19 — практический расчёт по тексту; 22 — расчёт по уравнению с раствором.

Реакции и названия веществ — chemdb_calc.py (уравнения уравнивает balance()). У каждого прототипа solve(p) пересчитывает
ответ из параметров карточки другим путём (через моли/массы элементов, Decimal-округление). Ar как в КИМ: целые, Cl = 35,5.
Формулировки — в стиле КИМ, но своими словами (сходство с текстами банка по 5-словным шинглам < 0,3).
"""
import math
import os
import sys
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from pc_core import (AR, Retry, balance, check_balance, eq_str, fmt, match_opts, molar, opts,  # noqa: E402
                     parse_formula, pcard, pretty, proto, ru)
import chemdb_calc as D  # noqa: E402

VM = Fr(224, 10)
G = D.G
PREC = ['целых', 'десятых', 'сотых']
NOM = {s['f']: s['name'] for s in D.SUBSTANCES}


# ---------------------------------------------------------------- общие помощники

def gen(f):
    return D.GEN[f][0]


def gnd(f):
    return D.GEN[f][1]


def pp_sh(stem, g):
    """Причастие в род. падеже: образовавш + егося/ейся/ихся."""
    return stem + {'f': 'ейся', 'pl': 'ихся'}.get(g, 'егося')


def pp_nn(stem, g):
    """Причастие на -нн- в род. падеже: полученн + ого/ой/ых."""
    return stem + {'f': 'ой', 'pl': 'ых'}.get(g, 'ого')


def cap(s):
    return s[0].upper() + s[1:]


def guard(x, dec, tol=Fr(1, 20)):
    """Отбраковать значения у границы округления (ответ не должен зависеть от округления промежуточных данных)."""
    y = Fr(x) * 10 ** dec
    fr = y - math.floor(y)
    if abs(fr - Fr(1, 2)) < tol:
        raise Retry


def rnd(x, dec):
    guard(x, dec)
    out = fmt(Fr(x), dec)
    if out in ('0', '-0'):
        raise Retry
    return out


def rs(x, dec):
    """Независимое округление для solve(): Decimal, половина вверх."""
    x = Fr(x)
    d = (Decimal(x.numerator) / Decimal(x.denominator)).quantize(Decimal(1).scaleb(-dec), rounding=ROUND_HALF_UP)
    s = format(d, 'f')
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s.replace('.', ',')


def nice(x, dec=2):
    """x — конечная дробь не длиннее dec знаков (для чисел в условии)."""
    return (Fr(x) * 10 ** dec).denominator == 1


def tail(dec):
    return f'(Запишите число с точностью до {PREC[dec]}.)'


MATCH_I = 'к каждой позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой.'
MATCH_T = 'Запишите в таблицу выбранные цифры под соответствующими буквами.'
MANY_T = 'Запишите номера выбранных ответов.'


def W(xs, dec):
    """Типичные неверные ответы, округлённые как ответ (пропуск нулевых/отрицательных)."""
    out = []
    for x in xs:
        if x is None:
            continue
        x = Fr(x)
        if x <= 0:
            continue
        out.append(fmt(x, dec))
    return out


def eqp(lhs, rhs, arrow='='):
    kl, kr = balance(lhs, rhs)
    return pretty(eq_str(lhs, rhs, kl, kr, arrow)), (lhs, rhs, kl, kr)


def coef(lhs, rhs):
    kl, kr = balance(lhs, rhs)
    return dict(zip(lhs + rhs, kl + kr))


def M(f):
    return molar(f)


def Mi(f):
    """Молярная масса другим кодом (для solve): сумма Ar по разбору формулы."""
    return sum(AR[e] * k for e, k in parse_formula(f).items())


def pick(rng, xs):
    return xs[rng.randrange(len(xs))]


def fid(answer_format, style, level, time_min, scale, trap, kes, score):
    return dict(answer_format=answer_format, style=style, level=level, time_min=time_min, scale=scale, trap=trap,
                kes=kes, score=score)


def is_gas(f):
    return f in ('H2', 'O2', 'N2', 'Cl2', 'CO2', 'CO', 'SO2', 'NH3', 'H2S', 'CH4', 'C2H2', 'C2H4', 'C2H6', 'C3H8', 'NO',
                 'NO2', 'HCl', 'C4H10', 'C4H6', 'C3H6')


# ======================================================================= ЕГЭ 26. Растворы

SOL26 = [  # (формула, род. падеж, слово для «массовая доля …»)
    ('NaNO3', 'нитрата натрия', 'соли'), ('Mg(NO3)2', 'нитрата магния', 'соли'), ('KNO3', 'нитрата калия', 'соли'),
    ('Ba(NO3)2', 'нитрата бария', 'соли'), ('CuCl2', 'хлорида меди(II)', 'соли'), ('KCl', 'хлорида калия', 'соли'),
    ('NaCl', 'хлорида натрия', 'соли'), ('CaCl2', 'хлорида кальция', 'соли'), ('K2SO4', 'сульфата калия', 'соли'),
    ('Na2SO4', 'сульфата натрия', 'соли'), ('CuSO4', 'сульфата меди(II)', 'соли'), ('ZnSO4', 'сульфата цинка', 'соли'),
    ('MgSO4', 'сульфата магния', 'соли'), ('Na2CO3', 'карбоната натрия', 'соли'), ('K2CO3', 'карбоната калия', 'соли'),
    ('NH4NO3', 'нитрата аммония', 'соли'), ('AgNO3', 'нитрата серебра', 'соли'), ('ZnCl2', 'хлорида цинка', 'соли'),
    ('NH4Cl', 'хлорида аммония', 'соли'), ('Al2(SO4)3', 'сульфата алюминия', 'соли'),
    ('Zn(NO3)2', 'нитрата цинка', 'соли'), ('CH3COONa', 'ацетата натрия', 'соли'),
    ('NaOH', 'гидроксида натрия', 'щёлочи'), ('KOH', 'гидроксида калия', 'щёлочи'),
    ('C6H12O6', 'глюкозы', 'глюкозы'), ('C12H22O11', 'сахарозы', 'сахарозы'),
    ('H2SO4', 'серной кислоты', 'кислоты'), ('HNO3', 'азотной кислоты', 'кислоты'),
    ('CH3COOH', 'уксусной кислоты', 'кислоты'), ('H3PO4', 'фосфорной кислоты', 'кислоты'),
]
W26 = [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15, 16, 18, 20, 22, 24, 25, 28, 30, 35, 40]


def _same(cw):
    return {'соли': 'той же соли', 'щёлочи': 'той же щёлочи', 'кислоты': 'той же кислоты'}.get(cw, 'того же вещества')


def _solve_26_add(p):
    m1, w1, a, wa, ev = (Fr(p[k]) for k in ('m1', 'w1', 'add', 'water', 'evap'))
    s = m1 * w1 / 100 + a
    return rs(s / (m1 + a + wa - ev) * 100, p['dec'])


@proto('ch-ege-26-add', 'ЕГЭ', 26, 'Массовая доля после добавления вещества, воды или упаривания',
       invariant='масса растворённого вещества = m·ω + добавленное; масса раствора = m + добавки − выпаренная вода; '
                 'ω = m(в-ва)/m(р-ра)·100 %',
       varies='вещество (соль, щёлочь, кислота, глюкоза), массы и доли, набор действий (добавили соль и/или воду, '
              'выпарили воду); исходный раствор задан долей или массами воды и соли',
       answer_rule='ω в % с точностью, указанной в условии (до целых/десятых)',
       mistakes=['добавленное вещество не учтено в массе раствора', 'выпаренную воду прибавили вместо вычитания',
                 'мл воды не приравнены к граммам'],
       solve=_solve_26_add, kes=['1.11', '5.7'],
       fidelity=fid('число, % с точностью до целых или десятых; единицы в бланк не пишутся',
                    'одно-два предложения с массами и долей, вопрос о массовой доле в полученном растворе, требование '
                    'точности в конце — как в зад. 26 демоверсии 2027', 'Б', 4,
                    'массы раствора 30–400 г, доли 2–40 %, добавки 2–60 г, вода 10–120 мл — как в банке (130 г, 10 %, '
                    '17 г соли, 17 мл воды)', 'учесть добавленное вещество и в числителе, и в знаменателе; мл воды = г',
                    ['1.11', '5.7'], '1 балл, ответ — число'))
def g26_add(rng):
    f, name, cw = pick(rng, SOL26)
    m1 = Fr(rng.choice(list(range(40, 401, 5))))
    w1 = Fr(rng.choice(W26[:-2]))
    s1 = m1 * w1 / 100
    mode = rng.choice(['salt', 'salt_water', 'salt_evap', 'water', 'evap', 'salt_water', 'salt_evap', 'masses'])
    add = water = evap = Fr(0)
    if cw == 'кислоты' and mode in ('salt', 'salt_water', 'salt_evap', 'masses'):
        raise Retry
    if mode == 'masses':   # раствор задан массами воды и вещества
        s1 = Fr(rng.choice(range(5, 61)))
        wat0 = Fr(rng.choice(range(40, 301, 5)))
        m1 = s1 + wat0
        w1 = s1 / m1 * 100
        water = Fr(rng.choice(range(10, 81)))
        if rng.random() < 0.6:
            add = Fr(rng.choice(range(3, 41)))
    if mode in ('salt', 'salt_water', 'salt_evap'):
        add = Fr(rng.choice(list(range(3, 61)) + [Fr(k, 10) for k in range(15, 60, 5)]))
    if mode in ('salt_water', 'water'):
        water = Fr(rng.choice(range(10, 121)))
    if mode in ('salt_evap', 'evap'):
        evap = Fr(rng.choice(range(10, 121)))
        if evap >= (m1 - s1) * Fr(3, 4):
            raise Retry
    dec = rng.choice([0, 0, 1])
    w = (s1 + add) / (m1 + add + water - evap) * 100
    if w >= 70:
        raise Retry
    ans = rnd(w, dec)
    same = _same(cw) if cw in ('соли', 'щёлочи') else name
    if mode == 'masses':
        s = f'Раствор приготовили из {ru(m1 - s1)} г воды и {ru(s1)} г {name}. Затем к нему прилили ещё {ru(water)} г воды' + \
            (f' и внесли {ru(add)} г {same}.' if add else '.')
    else:
        pre = rng.choice([f'Имеется {ru(m1)} г раствора {name}, массовая доля {cw} в котором равна {ru(w1)} %.',
                          f'Масса раствора {name} равна {ru(m1)} г, массовая доля растворённого вещества — {ru(w1)} %.',
                          f'В колбе находится {ru(m1)} г {ru(w1)} %-ного раствора {name}.'])
        acts = {'salt': [f'В нём растворили ещё {ru(add)} г {same}.',
                         f'Туда же внесли {ru(add)} г {same} и перемешивали до полного растворения.'],
                'water': [f'К нему прилили {ru(water)} мл воды.', f'Раствор разбавили, добавив {ru(water)} мл воды.'],
                'evap': [f'При нагревании из него испарилось {ru(evap)} г воды.', f'Раствор упарили, удалив {ru(evap)} мл воды.'],
                'salt_water': [f'В раствор внесли {ru(add)} г {same} и прилили {ru(water)} мл воды.',
                               f'К раствору прибавили {ru(water)} мл воды, а затем растворили в нём {ru(add)} г {same}.'],
                'salt_evap': [f'В нём растворили ещё {ru(add)} г {same}, после чего упарили {ru(evap)} мл воды.',
                              f'Из раствора выпарили {ru(evap)} г воды, а затем растворили в нём {ru(add)} г {same}.']}
        s = pre + ' ' + rng.choice(acts[mode])
    ask = rng.choice([f'Рассчитайте массовую долю {name} в образовавшемся растворе.',
                      f'Какой стала массовая доля {name} в растворе?',
                      f'Найдите массовую долю {"соли" if cw == "соли" else name} в конечном растворе.'])
    q = f'{s} {ask} {tail(dec)}'
    e = (f'm({name}) = {fmt(s1, 2)}' + (f' + {ru(add)}' if add else '') + f' = {fmt(s1 + add, 2)} г; '
         f'm(р-ра) = {ru(m1)}' + (f' + {ru(add)}' if add else '') + (f' + {ru(water)}' if water else '') +
         (f' − {ru(evap)}' if evap else '') + f' = {ru(m1 + add + water - evap)} г; ω = {fmt(s1 + add, 2)}/'
         f'{ru(m1 + add + water - evap)}·100 % ≈ {ans} %.')
    wrong = W([(s1 + add) / (m1 + water - evap) * 100, s1 / (m1 + add + water - evap) * 100,
               (s1 + add) / (m1 + add + water + evap) * 100 if evap else (s1 + add) / (m1 + add) * 100], dec)
    return pcard('ch-ege-26-add', q, ans, e, p=dict(m1=str(m1), w1=str(w1), add=str(add), water=str(water),
                                                    evap=str(evap), dec=dec), wrong=wrong)


def _solve_26_mix(p):
    ms, ws = [Fr(x) for x in p['m']], [Fr(x) for x in p['w']]
    tot = sum(a * b for a, b in zip(ms, ws)) / 100
    return rs(tot * 100 / (sum(ms) + Fr(p['water'])), p['dec'])


@proto('ch-ege-26-mix', 'ЕГЭ', 26, 'Массовая доля при смешивании растворов',
       invariant='массы растворённого вещества и массы растворов складываются; ω = Σm(в-ва)/Σm(р-ра)·100 %',
       varies='вещество, два-три раствора разной концентрации, иногда дополнительная вода; точность ответа',
       answer_rule='ω в % с точностью, указанной в условии',
       mistakes=['усреднили доли без учёта масс', 'сложили доли', 'забыли прибавить воду к массе раствора'],
       solve=_solve_26_mix, kes=['1.11', '5.7'],
       fidelity=fid('число, % с точностью до целых/десятых', 'КИМ-стиль: два раствора одной соли с массами и долями, '
                    'вопрос о доле в смеси', 'Б', 4, 'массы 20–400 г, доли 2–40 % (в банке 115 г 18 % + 65 г 20 %)',
                    'нельзя усреднять доли арифметически', ['1.11', '5.7'], '1 балл'))
def g26_mix(rng):
    f, name, cw = pick(rng, SOL26)
    k = rng.choice([2, 2, 2, 3])
    ws = rng.sample(W26, k)
    ms = [rng.choice(range(20, 401, 5)) for _ in range(k)]
    water = rng.choice([0, 0, 0] + list(range(20, 101, 10)))
    dec = rng.choice([0, 1, 1])
    tot = sum(Fr(a * b, 100) for a, b in zip(ms, ws))
    w = tot / (sum(ms) + water) * 100
    ans = rnd(w, dec)
    parts = [f'{m} г раствора с массовой долей {name} {x} %' if i == 0 else f'{m} г {x} %-ного раствора'
             for i, (m, x) in enumerate(zip(ms, ws))]
    lst = ', '.join(parts[:-1]) + ' и ' + parts[-1]
    q = rng.choice([f'В одном сосуде объединили {lst} того же вещества' + (f', а затем добавили {water} г воды.' if water else '.'),
                    f'Приготовлена смесь растворов {name}: ' + '; '.join(f'{m} г с массовой долей {x} %' for m, x in zip(ms, ws)) +
                    (f'. К смеси прилили {water} мл воды.' if water else '.')])
    q += ' ' + rng.choice([f'Рассчитайте массовую долю {name} в образовавшемся растворе.',
                           f'Определите, какой стала массовая доля {name} после смешивания.']) + ' ' + tail(dec)
    e = (f'm({name}) = ' + ' + '.join(f'{m}·{x}/100' for m, x in zip(ms, ws)) + f' = {ru(tot)} г; m(р-ра) = '
         + ' + '.join(str(m) for m in ms) + (f' + {water}' if water else '') + f' = {sum(ms) + water} г; ω ≈ {ans} %.')
    wrong = W([Fr(sum(ws), k), tot / sum(ms) * 100 if water else Fr(sum(ws)), tot / max(ms) * 100], dec)
    return pcard('ch-ege-26-mix', q, ans, e, p=dict(m=ms, w=ws, water=water, dec=dec), wrong=wrong)


def _solve_26_water(p):
    m, w1, w2 = Fr(p['m']), Fr(p['w1']), Fr(p['w2'])
    mode = p['mode']
    if mode == 'add':            # сколько воды добавить к m г
        x = m * w1 / w2 - m
    elif mode == 'evap':         # сколько воды выпарить из m г
        x = m - m * w1 / w2
    elif mode == 'take_add':     # масса исходного раствора, чтобы с m г воды получить w2
        x = m * w2 / (w1 - w2)
    elif mode == 'take_evap':    # масса исходного раствора, чтобы после выпаривания m г воды получить w2
        x = m * w2 / (w2 - w1)
    elif mode == 'take_salt':    # масса исходного раствора, чтобы после растворения m г соли получить w2
        x = m * (100 - w2) / (w2 - w1)
    else:                        # dissolve: масса вещества, которую растворить в m г воды для доли w2
        x = m * w2 / (100 - w2)
    return rs(x, p['dec'])


@proto('ch-ege-26-water', 'ЕГЭ', 26, 'Масса воды, вещества или исходного раствора для получения заданной доли',
       invariant='масса растворённого вещества при разбавлении и упаривании не меняется: m1·ω1 = m2·ω2; при добавлении '
                 'вещества — (m·ω1 + x)/(m + x) = ω2',
       varies='вещество; найти: массу добавляемой/выпариваемой воды, массу исходного раствора (для разбавления, '
              'упаривания, досыпания соли), массу вещества для растворения в воде',
       answer_rule='масса в г с точностью, указанной в условии',
       mistakes=['дали массу нового раствора вместо массы воды', 'перепутали ω1 и ω2', 'разность долей вместо пропорции'],
       solve=_solve_26_water, kes=['1.11', '5.7'],
       fidelity=fid('число, г с точностью до целых/десятых', 'КИМ-стиль обратной задачи «какую массу … нужно взять, '
                    'чтобы …» — формулировка своя', 'Б', 4, 'массы 5–600 г, доли 2–40 % (в банке 175 г, 30 % → 15 %; '
                    '10 г воды, 17 % → 7 %)', 'сохранение массы вещества; ответ — масса воды, а не нового раствора',
                    ['1.11', '5.7'], '1 балл'))
def g26_water(rng):
    f, name, cw = pick(rng, SOL26)
    mode = rng.choice(['add', 'evap', 'take_add', 'take_evap', 'take_salt', 'dissolve', 'add', 'take_add'])
    if cw == 'кислоты' and mode in ('take_salt', 'dissolve'):
        raise Retry
    dec = rng.choice([0, 1])
    lo, hi = sorted(rng.sample(W26, 2))
    w1, w2 = (hi, lo) if mode in ('add', 'take_add') else (lo, hi)
    m = Fr(rng.choice(range(20, 601, 5)))
    if mode in ('take_add', 'take_evap', 'take_salt'):
        m = Fr(rng.choice(range(5, 61)))
    if mode == 'add':
        x = m * w1 / w2 - m
        q = rng.choice([f'Раствор {name} массой {m} г содержит {w1} % растворённого вещества. Рассчитайте массу воды, '
                        f'которую следует прилить к нему, чтобы массовая доля {name} снизилась до {w2} %.',
                        f'Раствор {name} массой {m} г с массовой долей {w1} % нужно разбавить водой до массовой доли '
                        f'{w2} %. Определите массу воды, которая для этого потребуется.'])
        wrong = W([m * w1 / w2, m * Fr(w1 - w2, 100), m * w2 / w1], dec)
        e = f'm({name}) = {m}·{w1}/100 = {ru(m * w1 / 100)} г; m(нов. р-ра) = {fmt(m * w1 / w2, 2)} г; m(воды) = m(нов. р-ра) − {m}'
    elif mode == 'evap':
        x = m - m * w1 / w2
        q = rng.choice([f'Из {m} г раствора {name} (массовая доля {w1} %) удаляют воду выпариванием, пока массовая доля '
                        f'{name} не станет равной {w2} %. Рассчитайте массу удалённой воды.',
                        f'Раствор {name} массой {m} г с массовой долей {w1} % упарили до {w2} %-ного. Определите массу '
                        f'испарившейся воды.'])
        wrong = W([m * w1 / w2, m * Fr(w2 - w1, 100), m * w2 / w1 - m], dec)
        e = f'm({name}) = {ru(m * w1 / 100)} г; m(конечного р-ра) = {fmt(m * w1 / w2, 2)} г; m(воды) = {m} − m(конечного р-ра)'
    elif mode == 'take_add':
        x = m * w2 / (w1 - w2)
        q = rng.choice([f'Определите массу раствора {name} с массовой долей {w1} %, которую нужно смешать с {m} г воды, '
                        f'чтобы массовая доля {name} стала равной {w2} %.',
                        f'После разбавления некоторой порции {w1} %-ного раствора {name} водой массой {m} г получили раствор '
                        f'с массовой долей {w2} %. Найдите массу исходной порции раствора.'])
        wrong = W([m * w2 / w1, m * w1 / (w1 - w2), x + m], dec)
        e = f'x·{w1} = (x + {m})·{w2} ⇒ x = {m}·{w2}/({w1} − {w2})'
    elif mode == 'take_evap':
        x = m * w2 / (w2 - w1)
        q = rng.choice([f'Какова масса раствора {name} с массовой долей {w1} %, из которого после удаления {m} г воды '
                        f'получается раствор с массовой долей {w2} %?',
                        f'Порцию {w1} %-ного раствора {name} упарили, удалив {m} г воды, и получили {w2} %-ный раствор. '
                        f'Рассчитайте массу исходной порции.'])
        wrong = W([m * w1 / (w2 - w1), m * w2 / w1, x - m], dec)
        e = f'x·{w1} = (x − {m})·{w2} ⇒ x = {m}·{w2}/({w2} − {w1})'
    elif mode == 'take_salt':
        x = m * (100 - w2) / (w2 - w1)
        q = rng.choice([f'Какую массу раствора {name} с массовой долей {w1} % следует взять, чтобы после растворения в нём '
                        f'{m} г {_same(cw) if cw in ("соли", "щёлочи") else name} массовая доля стала равной {w2} %?',
                        f'В некоторой порции {w1} %-ного раствора {name} растворили {m} г {name} и получили раствор с '
                        f'массовой долей {w2} %. Найдите массу исходной порции раствора.'])
        wrong = W([m * w2 / (w2 - w1), m * (100 - w2) / w2, x + m], dec)
        e = f'(x·{w1}/100 + {m})/(x + {m}) = {w2}/100 ⇒ x = {m}·(100 − {w2})/({w2} − {w1})'
    else:
        m = Fr(rng.choice(range(50, 501, 10)))
        x = m * w2 / (100 - w2)
        q = rng.choice([f'Рассчитайте массу {name}, которую нужно растворить в {m} г воды, чтобы получить раствор с '
                        f'массовой долей {cw} {w2} %.',
                        f'В {m} мл воды растворяют {name}. Какая масса вещества потребуется, чтобы массовая доля {name} в '
                        f'растворе составила {w2} %?'])
        wrong = W([m * w2 / 100, m * w2 / (100 + w2), m * (100 - w2) / w2], dec)
        e = f'x/(x + {m}) = {w2}/100 ⇒ x = {m}·{w2}/(100 − {w2})'
    if x <= 0 or x > 5000:
        raise Retry
    ans = rnd(x, dec)
    q += ' ' + tail(dec)
    e += f' ≈ {ans} г.'
    return pcard('ch-ege-26-water', q, ans, e, p=dict(mode=mode, m=str(m), w1=w1, w2=w2, dec=dec), wrong=wrong)


def _solve_26_salt(p):
    m, w1, w2 = Fr(p['m']), Fr(p['w1']), Fr(p['w2'])
    return rs((m * w2 - m * w1) / (100 - w2), p['dec'])


@proto('ch-ege-26-salt', 'ЕГЭ', 26, 'Масса вещества, которую нужно дополнительно растворить для повышения доли',
       invariant='(m·ω1 + x)/(m + x) = ω2 ⇒ x = m(ω2 − ω1)/(100 − ω2)',
       varies='вещество (соль, щёлочь, глюкоза, сахароза), масса и доли, сюжет',
       answer_rule='масса вещества в г с указанной точностью',
       mistakes=['не учли, что добавленное вещество увеличивает массу раствора: x = m(ω2 − ω1)/100',
                 'поделили на ω2 вместо (100 − ω2)'],
       solve=_solve_26_salt, kes=['1.11', '5.7'],
       fidelity=fid('число, г с точностью до целых/десятых', 'КИМ-стиль «сколько граммов … растворить в … г раствора, '
                    'чтобы …» — своими словами', 'Б', 4, 'массы 50–500 г, доли 2–40 % (в банке 200 г 5 % → 10 %)',
                    'добавленное вещество увеличивает и массу раствора', ['1.11', '5.7'], '1 балл'))
def g26_salt(rng):
    sols = [x for x in SOL26 if x[2] in ('соли', 'щёлочи', 'глюкозы', 'сахарозы')]
    f, name, cw = pick(rng, sols)
    w1, w2 = sorted(rng.sample(W26[:-3], 2))
    m = Fr(rng.choice(range(50, 501, 5)))
    dec = rng.choice([0, 1])
    x = m * (w2 - w1) / (100 - w2)
    ans = rnd(x, dec)
    q = rng.choice([f'Раствор {name} массой {m} г имеет массовую долю растворённого вещества {w1} %. Определите массу '
                    f'{name}, которую необходимо дополнительно растворить в нём для повышения массовой доли до {w2} %.',
                    f'Массовую долю {name} в {m} г раствора нужно увеличить с {w1} % до {w2} %, растворив в нём ещё '
                    f'некоторое количество этого вещества. Рассчитайте массу добавляемого вещества.'])
    q += ' ' + tail(dec)
    e = f'({ru(m * w1 / 100)} + x)/({m} + x) = {w2}/100 ⇒ x = {m}·({w2} − {w1})/(100 − {w2}) ≈ {ans} г.'
    wrong = W([m * (w2 - w1) / 100, m * (w2 - w1) / w2, m * w2 / 100], dec)
    return pcard('ch-ege-26-salt', q, ans, e, p=dict(m=str(m), w1=w1, w2=w2, dec=dec), wrong=wrong)


def _solve_26_mixfind(p):
    m1, w1, w2, w = Fr(p['m1']), Fr(p['w1']), Fr(p['w2']), Fr(p['w'])
    return rs(m1 * (w1 - w) / (w - w2), p['dec'])


@proto('ch-ege-26-mixfind', 'ЕГЭ', 26, 'Масса второго раствора для получения смеси нужной концентрации',
       invariant='m1ω1 + xω2 = (m1 + x)ω ⇒ x = m1(ω1 − ω)/(ω − ω2)',
       varies='вещество, концентрации двух растворов и смеси, масса первого раствора',
       answer_rule='масса второго раствора в г с указанной точностью',
       mistakes=['неверный знак разностей («правило креста» наоборот)', 'нашли массу смеси, а не второго раствора'],
       solve=_solve_26_mixfind, kes=['1.11', '5.7'],
       fidelity=fid('число, г', 'КИМ-стиль «сколько граммов …%-ного раствора добавить к …, чтобы получить …» — своими '
                    'словами', 'Б', 4, 'массы 50–400 г, доли 2–40 % (в банке 200 г 6 % + x г 12 % → 10 %)',
                    'баланс масс вещества; искомое — второй раствор', ['1.11', '5.7'], '1 балл'))
def g26_mixfind(rng):
    f, name, cw = pick(rng, SOL26)
    a, b, c = sorted(rng.sample(W26, 3))
    w1, w2, w = (c, a, b) if rng.random() < 0.5 else (a, c, b)
    m1 = Fr(rng.choice(range(50, 401, 5)))
    dec = rng.choice([0, 1])
    x = m1 * (w1 - w) / (w - w2)
    if x <= 0 or x > 3000:
        raise Retry
    ans = rnd(x, dec)
    q = rng.choice([f'Имеются два раствора {name}: {m1} г с массовой долей {w1} % и раствор с массовой долей {w2} %. '
                    f'Какую массу второго раствора нужно смешать с первым, чтобы массовая доля {name} в смеси составила '
                    f'{w} %?',
                    f'Для получения {w} %-ного раствора {name} к {m1} г его {w1} %-ного раствора прибавили раствор того '
                    f'же вещества с массовой долей {w2} %. Рассчитайте массу прибавленного раствора.'])
    q += ' ' + tail(dec)
    e = f'{m1}·{w1} + x·{w2} = ({m1} + x)·{w} ⇒ x = {m1}·({w1} − {w})/({w} − {w2}) ≈ {ans} г.'
    wrong = W([m1 * (w - w2) / (w1 - w), x + m1, m1 * w / w2], dec)
    return pcard('ch-ege-26-mixfind', q, ans, e, p=dict(m1=str(m1), w1=w1, w2=w2, w=w, dec=dec), wrong=wrong)


HYDR = [  # (кристаллогидрат, безводная соль, название (вин. п.), название (род. п.), соль (род. п.))
    ('CuSO4·5H2O', 'CuSO4', 'медный купорос', 'медного купороса', 'сульфата меди(II)'),
    ('FeSO4·7H2O', 'FeSO4', 'железный купорос', 'железного купороса', 'сульфата железа(II)'),
    ('Na2CO3·10H2O', 'Na2CO3', 'кристаллическую соду', 'кристаллической соды', 'карбоната натрия'),
    ('Na2SO4·10H2O', 'Na2SO4', 'глауберову соль', 'глауберовой соли', 'сульфата натрия'),
    ('MgSO4·7H2O', 'MgSO4', 'горькую соль', 'горькой соли', 'сульфата магния'),
    ('ZnSO4·7H2O', 'ZnSO4', 'цинковый купорос', 'цинкового купороса', 'сульфата цинка'),
    ('BaCl2·2H2O', 'BaCl2', 'дигидрат хлорида бария', 'дигидрата хлорида бария', 'хлорида бария'),
    ('CaCl2·6H2O', 'CaCl2', 'гексагидрат хлорида кальция', 'гексагидрата хлорида кальция', 'хлорида кальция'),
]


def _solve_26_hydrate(p):
    Mh, Ma = Mi(p['hyd']), Mi(p['anh'])
    if p['mode'] == 'omega':
        return rs(Fr(p['mh']) * Ma / Mh / (Fr(p['mh']) + Fr(p['water'])) * 100, p['dec'])
    return rs(Fr(p['m']) * Fr(p['w']) / 100 * Mh / Ma, p['dec'])


@proto('ch-ege-26-hydrate', 'ЕГЭ', 26, 'Раствор из кристаллогидрата',
       invariant='m(безводной соли) = m(гидрата)·M(соли)/M(гидрата); вода гидрата переходит в раствор',
       varies='кристаллогидрат (купоросы, сода, глауберова соль …); найти ω раствора или массу гидрата для раствора',
       answer_rule='ω в % или масса в г с указанной точностью',
       mistakes=['массу гидрата приняли за массу безводной соли', 'не прибавили массу гидрата к массе раствора'],
       solve=_solve_26_hydrate, kes=['1.11', '5.7'],
       fidelity=fid('число, % или г', 'КИМ-стиль; в открытом банке № 26 кристаллогидратов почти нет — прототип по '
                    'кодификатору 1.11 (кристаллогидраты) и шагам задания 34', 'Б', 4, 'массы гидрата 5–100 г, воды '
                    '50–500 г', 'кристаллизационная вода входит в массу раствора, но не в массу вещества', ['1.11', '5.7'],
                    '1 балл'))
def g26_hydrate(rng):
    hyd, anh, acc, gname, aname = pick(rng, HYDR)
    Mh, Ma = M(hyd), M(anh)
    dec = rng.choice([0, 1])
    if rng.random() < 0.55:
        mh = Fr(rng.choice(range(5, 101)))
        water = Fr(rng.choice(range(50, 501, 5)))
        x = mh * Ma / Mh / (mh + water) * 100
        ans = rnd(x, dec)
        q = rng.choice([f'{cap(acc)} ({pretty(hyd)}) массой {mh} г растворили в {water} г воды. Рассчитайте массовую '
                        f'долю {aname} в образовавшемся растворе.',
                        f'Для приготовления раствора взяли {mh} г {gname} ({pretty(hyd)}) и {water} г воды. Какова '
                        f'массовая доля {aname} в растворе?'])
        p = dict(mode='omega', hyd=hyd, anh=anh, mh=str(mh), water=str(water), dec=dec)
        e = f'm({pretty(anh)}) = {mh}·{ru(Ma)}/{ru(Mh)} = {fmt(mh * Ma / Mh, 2)} г; m(р-ра) = {mh} + {water} = {mh + water} г; ω ≈ {ans} %.'
        wrong = W([mh / (mh + water) * 100, mh * Ma / Mh / water * 100, mh / water * 100], dec)
    else:
        m = Fr(rng.choice(range(50, 1001, 25)))
        w = rng.choice([2, 4, 5, 6, 8, 10, 12, 15, 16, 20])
        x = m * w / 100 * Mh / Ma
        ans = rnd(x, dec)
        q = rng.choice([f'Рассчитайте массу кристаллогидрата {pretty(hyd)}, необходимую для приготовления {m} г раствора, '
                        f'в котором массовая доля {aname} равна {w} %.',
                        f'Для опыта требуется {m} г {w} %-ного раствора {aname}. Какую массу {gname} ({pretty(hyd)}) '
                        f'нужно для этого растворить в воде?'])
        p = dict(mode='mass', hyd=hyd, anh=anh, m=str(m), w=w, dec=dec)
        e = f'm({pretty(anh)}) = {m}·{w}/100 = {ru(m * w / 100)} г; n = m/{ru(Ma)} = n(гидрата); m(гидрата) = n·{ru(Mh)} ≈ {ans} г.'
        wrong = W([m * w / 100, m * w / 100 * Ma / Mh, m * w / 100 * Mh / Ma * 100 / (100 - w)], dec)
    q += ' ' + tail(dec)
    return pcard('ch-ege-26-hydrate', q, ans, e, p=p, wrong=wrong)


MOLAR = ['NaOH', 'KOH', 'NaCl', 'KCl', 'H2SO4', 'HNO3', 'HCl', 'Na2CO3', 'CuSO4', 'KNO3', 'Na2SO4', 'CaCl2', 'BaCl2',
         'NH4NO3', 'C6H12O6', 'AgNO3', 'K2CO3', 'MgSO4', 'ZnCl2', 'KMnO4']


def _mname(f):
    return {'HCl': 'хлороводорода', 'NH4NO3': 'нитрата аммония'}.get(f) or gen(f)


def _solve_26_molar(p):
    f, mode = p['f'], p['mode']
    Mf = Mi(f)
    if mode == 'c':
        x = Fr(p['m']) / Mf / (Fr(p['V']) / 1000)
    elif mode == 'm':
        x = Fr(p['c']) * Fr(p['V']) / 1000 * Mf
    elif mode == 'c_from_w':
        x = Fr(p['w']) * Fr(p['rho']) * 10 / Mf
    else:
        x = Fr(p['c']) * Mf / Fr(p['rho']) / 10
    return rs(x, p['dec'])


@proto('ch-ege-26-molar', 'ЕГЭ', 26, 'Молярная концентрация раствора',
       invariant='c = n/V (моль/л); n = m/M; переход от ω к c: c = 1000·ρ·ω/M',
       varies='вещество, найти: c по массе и объёму, массу для раствора заданной c, c по ω и ρ или ω по c и ρ',
       answer_rule='число с указанной точностью (моль/л, г или %)',
       mistakes=['объём не переведён из мл в л', 'забыта плотность', 'масса вместо количества вещества'],
       solve=_solve_26_molar, kes=['1.11', '5.7'],
       fidelity=fid('число: моль/л, г или % с точностью до десятых/сотых', 'КИМ-стиль; определение молярной концентрации '
                    'как в справочной части демоверсии 2027 (зад. 21); в спецификации 2027 № 26 — «массовая доля и '
                    'молярная концентрация», в открытом банке таких кратких заданий пока нет', 'Б', 4,
                    'объёмы 50–2000 мл, c 0,05–3 моль/л, плотности 1,01–1,3 г/мл', 'мл → л; ω ↔ c через ρ',
                    ['1.11', '5.7'], '1 балл'))
def g26_molar(rng):
    f = pick(rng, MOLAR)
    name = _mname(f)
    Mf = M(f)
    mode = rng.choice(['c', 'm', 'c_from_w', 'w_from_c'])
    dec = rng.choice([1, 2])
    if mode == 'c':
        V = Fr(rng.choice([50, 100, 150, 200, 250, 300, 400, 500, 750, 1000, 1500, 2000]))
        m = Fr(rng.choice(range(1, 121))) if Mf > 50 else Fr(rng.choice(range(1, 61)))
        x = m / Mf / (V / 1000)
        q = rng.choice([f'В мерной колбе растворили {m} г {name} и довели объём раствора водой до {V} мл. Рассчитайте '
                        f'молярную концентрацию {name} (моль/л).',
                        f'В {V} мл раствора содержится {m} г {name}. Найдите молярную концентрацию раствора (моль/л).'])
        wrong = W([m / Mf / V, m / V * 1000, m / Mf], dec)
        p = dict(f=f, mode=mode, m=str(m), V=str(V), dec=dec)
        e = f'n = {m}/{ru(Mf)} моль; c = n/V = n/{ru(V / 1000)} л'
    elif mode == 'm':
        V = Fr(rng.choice([50, 100, 200, 250, 400, 500, 750, 1000, 2000]))
        c = Fr(rng.choice([5, 10, 15, 20, 25, 50, 75, 100, 150, 200, 250]), 100)
        x = c * V / 1000 * Mf
        q = rng.choice([f'Рассчитайте массу {name}, которая потребуется для приготовления {V} мл раствора с молярной '
                        f'концентрацией {ru(c)} моль/л.',
                        f'Нужно приготовить {V} мл раствора {name} с концентрацией {ru(c)} моль/л. Какую массу вещества '
                        f'следует взять?'])
        wrong = W([c * V * Mf, c * Mf, c * V / 1000], dec)
        p = dict(f=f, mode=mode, c=str(c), V=str(V), dec=dec)
        e = f'n = c·V = {ru(c)}·{ru(V / 1000)} = {ru(c * V / 1000)} моль; m = n·M'
    elif mode == 'c_from_w':
        w = rng.choice([2, 4, 5, 8, 10, 12, 15, 20, 25, 30])
        rho = Fr(rng.choice(range(101, 131)), 100)
        x = w * rho * 10 / Mf
        q = (f'Раствор {name} с массовой долей растворённого вещества {w} % имеет плотность {ru(rho)} г/мл. '
             f'Рассчитайте молярную концентрацию {name} в нём (моль/л).')
        wrong = W([w * 10 / Mf, w * rho / Mf, w * rho * 1000 / Mf], dec)
        p = dict(f=f, mode=mode, w=w, rho=str(rho), dec=dec)
        e = f'В 1 л: m(р-ра) = 1000·{ru(rho)} г, m(в-ва) = {ru(1000 * rho * w / 100)} г; c = m/M'
    else:
        c = Fr(rng.choice([10, 20, 25, 50, 75, 100, 125, 150, 200, 250, 300]), 100)
        rho = Fr(rng.choice(range(101, 131)), 100)
        x = c * Mf / rho / 10
        q = (f'Молярная концентрация {name} в растворе равна {ru(c)} моль/л, а его плотность — {ru(rho)} г/мл. '
             f'Найдите массовую долю {name} в этом растворе (%).')
        wrong = W([c * Mf / 10, c * Mf / rho, c * Mf / rho / 100], dec)
        p = dict(f=f, mode=mode, c=str(c), rho=str(rho), dec=dec)
        e = f'1 л раствора: m(р-ра) = {ru(1000 * rho)} г, m(в-ва) = {ru(c)}·{ru(Mf)} = {ru(c * Mf)} г; ω = m(в-ва)/m(р-ра)'
    if x < Fr(1, 100) or x > 10000:
        raise Retry
    ans = rnd(x, dec)
    q += ' ' + tail(dec)
    e += f' ≈ {ans}.'
    return pcard('ch-ege-26-molar', q, ans, e, p=p, wrong=wrong)


# ======================================================================= ЕГЭ 27. Тепловой эффект, объёмы газов

def therm_eq(r):
    """Термохимическое уравнение в записи КИМ: 2H₂(г) + O₂(г) = 2H₂O(ж) + 572 кДж."""
    lhs, rhs = r['lhs'], r['rhs']
    kl, kr = balance(lhs, rhs)
    st = r['st']
    side = lambda ss, ks, sts: ' + '.join((str(k) if k > 1 else '') + pretty(s) + f'({t})' for s, k, t in zip(ss, ks, sts))
    q = r['q']
    s = side(lhs, kl, st[:len(lhs)]) + ' = ' + side(rhs, kr, st[len(lhs):]) + (f' + {q} кДж' if q > 0 else f' − {-q} кДж')
    return s, (lhs, rhs, kl, kr)


def _solve_27_q(p):
    """Q = |Q°|·n(в-ва)/k(в-ва); n — из массы, объёма или моль; k — из заново уравненного уравнения."""
    k = coef(p['lhs'], p['rhs'])[p['f']]
    n = Fr(p['val']) / {'V': VM, 'm': Mi(p['f']), 'n': 1}[p['by']]
    return rs(abs(Fr(p['q'])) * n / k, p['dec'])


def _thermo_q_text(rng, r, f, by, val):
    eq, _ = therm_eq(r)
    q = r['q']
    amount = {'V': f'{ru(val)} л (н.у.) {gen(f)}', 'm': f'{ru(val)} г {gen(f)}', 'n': f'{ru(val)} моль {gen(f)}'}[by]
    in_lhs = f in r['lhs']
    fut = 'выделится' if q > 0 else 'поглотится'
    past = 'выделилось' if q > 0 else 'поглотилось'
    tpl = rng.randrange(3)
    if tpl == 0:
        act = ('израсходовали ' if in_lhs else 'получили ') + amount
        return (f'Процесс описывается термохимическим уравнением\n{eq}\nВ ходе процесса {act}. Рассчитайте, сколько '
                f'теплоты (кДж) при этом {past}.')
    if tpl == 1:
        if in_lhs and len(r['lhs']) == 1:
            what = f'разложении {amount}'
        elif in_lhs and 'горения' in r['type'] and f != 'O2':
            what = f'сгорании {amount}'
        elif in_lhs:
            what = f'вступлении в реакцию {amount}'
        else:
            what = f'образовании {amount}'
        return f'Термохимическое уравнение реакции:\n{eq}\nКакое количество теплоты (кДж) {fut} при {what}?'
    return (f'Определите количество теплоты, которое {fut}, если {"в реакцию вступит" if in_lhs else "будет получено"} '
            f'{amount}. Реакция протекает по термохимическому уравнению\n{eq}')


def _g27_q(rng, pid, by_set):
    r = pick(rng, D.THERMO)
    parts = list(zip(r['lhs'] + r['rhs'], r['st']))
    f, st = pick(rng, parts)
    if f == 'O2' and rng.random() < 0.6:
        raise Retry
    bys = [b for b in by_set if b != 'V' or st == G]
    if not bys:
        raise Retry
    by = pick(rng, bys)
    k = coef(r['lhs'], r['rhs'])[f]
    Mf = M(f)
    if by == 'V':
        n = Fr(rng.choice(range(1, 81)), 20)
        val = n * VM
    elif by == 'n':
        n = Fr(rng.choice(range(1, 81)), rng.choice([4, 8, 10, 20]))
        val = n
    else:
        val = rng.choice([Fr(rng.choice(range(1, 301))), Fr(rng.choice(range(5, 400)), 10)])
        if rng.random() < 0.4:   # «круглое» количество вещества, как в банке (8,8 г CO₂, 840 г CaO)
            nn = Fr(rng.choice(range(1, 81)), rng.choice([4, 5, 10, 20]))
            val = nn * Mf
            if not nice(val, 2):
                raise Retry
        n = val / Mf
    dec = rng.choice([0, 1])
    Q = abs(r['q']) * n / k
    if Q < 1 or Q > 30000:
        raise Retry
    ans = rnd(Q, dec)
    q = f'{_thermo_q_text(rng, r, f, by, val)} {tail(dec)}'
    _, eq = therm_eq(r)
    e = f'n({pretty(f)}) = {fmt(n, 4)} моль; на {k} моль по уравнению приходится {abs(r["q"])} кДж ⇒ ' \
        f'Q = {abs(r["q"])}·n/{k} ≈ {ans} кДж.'
    wrong = W([abs(r['q']) * n, abs(r['q']) * n * k if k > 1 else abs(r['q']) * n / 2,
               abs(r['q']) * val / k if by != 'n' else abs(r['q']) * n * Mf / k], dec)
    return pcard(pid, q, ans, e, p=dict(lhs=r['lhs'], rhs=r['rhs'], q=r['q'], f=f, by=by, val=str(val), dec=dec),
                 wrong=wrong, eq=eq)


@proto('ch-ege-27-mass', 'ЕГЭ', 27, 'Количество теплоты по массе или количеству вещества',
       invariant='Q = Q(уравн.)·n(в-ва)/k(в-ва), n = m/M',
       varies='реакция (горение топлива и металлов, разложение карбонатов, синтезы, гашение извести), вещество — '
              'реагент или продукт, выделение или поглощение теплоты, дана масса или количество вещества',
       answer_rule='Q в кДж с точностью, указанной в условии',
       mistakes=['не разделили на коэффициент вещества в уравнении', 'умножили на коэффициент', 'масса вместо моль'],
       solve=_solve_27_q, kes=['1.7', '5.2'],
       fidelity=fid('число, кДж с точностью до целых/десятых', 'термохимическое уравнение в записи КИМ с агрегатными '
                    'состояниями «(тв.)», «(г)», «(ж)» и «+ Q кДж»', 'Б', 3, 'массы 0,5–300 г, 0,05–20 моль, Q уравнения '
                    '65–5316 кДж (табличные)', 'коэффициент перед веществом ≠ 1', ['1.7', '5.2'], '1 балл'))
def g27_mass(rng):
    return _g27_q(rng, 'ch-ege-27-mass', ['m', 'm', 'n'])


@proto('ch-ege-27-vol', 'ЕГЭ', 27, 'Количество теплоты по объёму газа (н.у.)',
       invariant='n = V/22,4; Q = Q(уравн.)·n/k',
       varies='реакция, газ — реагент или продукт (CO₂, O₂, H₂, NH₃, CH₄ …), объём',
       answer_rule='Q в кДж с указанной точностью',
       mistakes=['не учли коэффициент газа', 'объём поделили на молярную массу'],
       solve=_solve_27_q, kes=['1.7', '5.2'],
       fidelity=fid('число, кДж', 'как зад. 27 демоверсии 2027 (теплота по объёму CO₂ при сгорании этанола) — своими '
                    'словами', 'Б', 3, 'объёмы 1,12–89,6 л (кратные 1,12, как 8,96 л в демо)',
                    'коэффициент газа (2CO₂ при сгорании этанола)', ['1.7', '5.2'], '1 балл'))
def g27_vol(rng):
    return _g27_q(rng, 'ch-ege-27-vol', ['V'])


def _solve_27_inv(p):
    k = coef(p['lhs'], p['rhs'])[p['f']]
    n = Fr(p['Q']) * k / abs(Fr(p['q']))
    return rs(n * {'V': VM, 'm': Mi(p['f']), 'n': 1}[p['by']], p['dec'])


@proto('ch-ege-27-inv', 'ЕГЭ', 27, 'Масса, объём или количество вещества по количеству теплоты',
       invariant='n(в-ва) = k·Q/Q(уравн.); m = n·M или V = n·22,4',
       varies='реакция, вещество, ответ в г, л (н.у.) или моль, теплота',
       answer_rule='масса (г), объём (л) или количество вещества (моль) с указанной точностью',
       mistakes=['не умножили на коэффициент', 'поделили теплоты наоборот', 'объём вместо массы'],
       solve=_solve_27_inv, kes=['1.7', '5.2'],
       fidelity=fid('число, г, л или моль', 'КИМ-стиль обратной задачи: «… выделилось … кДж теплоты. Вычислите массу …»',
                    'Б', 3, 'теплоты 5–6000 кДж (в банке 80,2; 1179,9; 5450 кДж)', 'пропорция через коэффициент',
                    ['1.7', '5.2'], '1 балл'))
def g27_inv(rng):
    r = pick(rng, D.THERMO)
    f, st = pick(rng, list(zip(r['lhs'] + r['rhs'], r['st'])))
    k = coef(r['lhs'], r['rhs'])[f]
    by = rng.choice(['V', 'V', 'm', 'n']) if st == G else rng.choice(['m', 'm', 'n'])
    n = Fr(rng.choice(range(1, 81)), rng.choice([10, 20, 4]))
    Q = abs(r['q']) * n / k
    if not nice(Q, 1) or Q < 2:
        raise Retry
    val = n * {'V': VM, 'm': M(f), 'n': 1}[by]
    dec = rng.choice([0, 1, 2]) if by != 'm' else rng.choice([0, 1])
    ans = rnd(val, dec)
    eq, eqt = therm_eq(r)
    past = 'выделилось' if r['q'] > 0 else 'поглотилось'
    role = ('вступившей в реакцию' if gnd(f) == 'f' else 'вступившего в реакцию') if f in r['lhs'] \
        else pp_sh('образовавш', gnd(f))
    what = {'V': f'объём (н.у.) {gen(f)}, {role}', 'm': f'массу {gen(f)}, {role}',
            'n': f'количество вещества {gen(f)} (моль), {role}'}[by]
    q = rng.choice([f'Реакция протекает по термохимическому уравнению\n{eq}\nВ результате {past} {ru(Q)} кДж теплоты. '
                    f'Рассчитайте {what}.',
                    f'Известно, что при протекании реакции\n{eq}\n{past} {ru(Q)} кДж теплоты. Определите {what}.'])
    q += ' ' + tail(dec)
    unit = {'V': VM, 'm': M(f), 'n': 1}[by]
    e = f'n({pretty(f)}) = {k}·{ru(Q)}/{abs(r["q"])} = {ru(n)} моль' + \
        {'V': '; V = n·22,4', 'm': f'; m = n·{ru(M(f))}', 'n': ''}[by] + f' ≈ {ans}.'
    wrong = W([Q / abs(r['q']) * unit, n * k * unit if k > 1 else n * 2 * unit, n / k * unit if k > 1 else n * unit / 2], dec)
    return pcard('ch-ege-27-inv', q, ans, e, p=dict(lhs=r['lhs'], rhs=r['rhs'], q=r['q'], f=f, by=by, Q=str(Q), dec=dec),
                 wrong=wrong, eq=eqt)


def _solve_27_qeq(p):
    k = coef(p['lhs'], p['rhs'])[p['f']]
    n = Fr(p['val']) / (VM if p['by'] == 'V' else Mi(p['f']))
    return rs(Fr(p['Qexp']) / n * k, 0)


@proto('ch-ege-27-qeq', 'ЕГЭ', 27, 'Тепловой эффект реакции по опытным данным',
       invariant='Q(уравн.) = Q(опыт)·k/n(в-ва)',
       varies='реакция, вещество, масса или объём, измеренная теплота',
       answer_rule='тепловой эффект в кДж (на уравнение с наименьшими целыми коэффициентами) до целых',
       mistakes=['забыли умножить на коэффициент вещества', 'отнесли теплоту к 1 г вместо 1 моль'],
       solve=_solve_27_qeq, kes=['1.7', '5.2'],
       fidelity=fid('число, кДж до целых', 'КИМ-стиль: «При … выделилось … кДж. Вычислите тепловой эффект реакции, '
                    'уравнение которой … + Q»', 'Б', 3, 'массы 0,5–100 г, теплоты 5–3000 кДж (в банке 6 г Mg → 150 кДж)',
                    'пересчёт на коэффициенты уравнения', ['1.7', '5.2'], '1 балл'))
def g27_qeq(rng):
    r = pick(rng, D.THERMO)
    lhs, rhs = r['lhs'], r['rhs']
    f, st = pick(rng, list(zip(lhs + rhs, r['st'])))
    if f == 'O2':
        raise Retry
    k = coef(lhs, rhs)[f]
    by = 'V' if st == G and rng.random() < 0.5 else 'm'
    n = Fr(rng.choice(range(1, 41)), rng.choice([10, 20, 40]))
    val = n * (VM if by == 'V' else M(f))
    if not nice(val, 2):
        raise Retry
    Qexp = abs(r['q']) * n / k
    if not nice(Qexp, 2) or Qexp < 1:
        raise Retry
    ans = fmt(Fr(abs(r['q'])), 0)
    kl, kr = balance(lhs, rhs)
    scheme = pretty(eq_str(lhs, rhs, kl, kr, '=')) + (' + Q' if r['q'] > 0 else ' − Q')
    amount = f'{ru(val)} л (н.у.) {gen(f)}' if by == 'V' else f'{ru(val)} г {gen(f)}'
    past = 'выделилось' if r['q'] > 0 else 'поглотилось'
    act = f'образовании {amount}' if f in rhs else (f'разложении {amount}' if len(lhs) == 1 else f'вступлении в реакцию {amount}')
    q = rng.choice([f'Опыт показал, что при {act} {past} {ru(Qexp)} кДж теплоты. Найдите значение Q (кДж) в '
                    f'термохимическом уравнении {scheme}.',
                    f'Для реакции {scheme} экспериментально установлено: при {act} {past} {ru(Qexp)} кДж. Рассчитайте '
                    f'тепловой эффект Q (кДж) в расчёте на записанные коэффициенты.'])
    q += ' ' + tail(0)
    e = f'n({pretty(f)}) = {ru(n)} моль; на {k} моль приходится {ru(Qexp)}·{k}/{ru(n)} = {ans} кДж.'
    wrong = W([Qexp / n, Qexp / n * k * 2 if k == 1 else Qexp / n, Qexp / val], 0)
    return pcard('ch-ege-27-qeq', q, ans, e, p=dict(lhs=lhs, rhs=rhs, f=f, by=by, val=str(val), Qexp=str(Qexp)),
                 wrong=wrong, eq=(lhs, rhs, kl, kr))


def _solve_27_gasvol(p):
    k = coef(p['lhs'], p['rhs'])
    return rs(Fr(p['V']) * k[p['f']] / k[p['g']], p['dec'])


GASCOND = ['Объёмы газов приведены к одинаковым условиям.', 'Температура и давление при измерении объёмов одинаковы.',
           'Все объёмы измерены при одних и тех же температуре и давлении.']


@proto('ch-ege-27-gasvol', 'ЕГЭ', 27, 'Объёмные отношения газов (закон объёмных отношений)',
       invariant='при одинаковых условиях V(газа1)/V(газа2) = k1/k2 (коэффициенты уравнения)',
       varies='реакция (гидрирование, горение углеводородов и сероводорода, окисление NO, NH₃, SO₂, синтез HCl), '
              'какой газ дан и какой найти',
       answer_rule='объём в л с указанной точностью',
       mistakes=['перевернули отношение коэффициентов', 'пересчитывали через 22,4 и ошиблись в округлении',
                 'посчитали объём воды как газа'],
       solve=_solve_27_gasvol, kes=['5.3'],
       fidelity=fid('число, л до целых/десятых', 'КИМ-стиль: объём одного газа по объёму другого при одинаковых условиях '
                    '— своими словами', 'Б', 2, 'объёмы 1,5–120 л (в банке 17 л бутадиена, 7 л пропана, 84 л O₂)',
                    'отношение коэффициентов, а не 22,4', ['5.3'], '1 балл'))
def g27_gasvol(rng):
    r = pick(rng, D.GASVOL)
    g, f = rng.sample(r['gas'], 2)
    k = coef(r['lhs'], r['rhs'])
    V = Fr(rng.choice(list(range(2, 121)) + [Fr(x, 10) for x in range(15, 100, 5)]))
    dec = rng.choice([0, 0, 1])
    x = V * k[f] / k[g]
    ans = rnd(x, dec)
    main = [s for s in r['lhs'] if s not in ('O2', 'H2', 'Cl2')] or [r['lhs'][0]]
    what = r['act']
    fl = 'израсходованного' if f in r['lhs'] else pp_sh('образовавш', gnd(f))
    given = f'{"израсходовали" if g in r["lhs"] else "получили"} {ru(V)} л {gen(g)}'
    given_p = f'{"израсходовано" if g in r["lhs"] else "получено"} {ru(V)} л {gen(g)}'
    q = rng.choice([f'В процессе {what} {gen(main[0])} {given}. Рассчитайте объём {fl} {gen(f)} (л).',
                    f'Какой объём {gen(f)} (л) {"расходуется" if f in r["lhs"] else "образуется"} в процессе {what} '
                    f'{gen(main[0])}, если {given_p}?'])
    q = q + ' ' + pick(rng, GASCOND) + ' ' + tail(dec)
    kl, kr = balance(r['lhs'], r['rhs'])
    e = f'{pretty(eq_str(r["lhs"], r["rhs"], kl, kr))}; V({pretty(f)}) = V({pretty(g)})·{k[f]}/{k[g]} = {ans} л.'
    wrong = W([V * k[g] / k[f], V, V * k[f] / k[g] * VM if k[f] != k[g] else V * 2], dec)
    return pcard('ch-ege-27-gasvol', q, ans, e, p=dict(lhs=r['lhs'], rhs=r['rhs'], g=g, f=f, V=str(V), dec=dec),
                 wrong=wrong, eq=(r['lhs'], r['rhs'], kl, kr))


# ======================================================================= ЕГЭ 28. Примеси, выход, избыток

def _unit(f, by):
    return {'V': VM, 'm': M(f), 'n': 1}[by]


def _unit_i(f, by):
    return {'V': VM, 'm': Mi(f), 'n': 1}[by]


def _solve_28(p):
    """m(чист.) = m·(100 − примеси)/100; n(прод) = n(исх)·k(прод)/k(исх)·η/100; ответ — m, V или n."""
    k = coef(p['lhs'], p['rhs'])
    g, f = p['g'], p['f']
    pure = Fr(p['m']) * (100 - Fr(p.get('imp', 0))) / 100
    ng = pure / _unit_i(g, p['gby'])
    nf = ng * k[f] / k[g] * Fr(p.get('eta', 100)) / 100
    return rs(nf * _unit_i(f, p['fby']), p['dec'])


def _want(f, fby):
    g = gnd(f)
    if fby == 'V':
        return f'объём (н.у.) {pp_sh("выделивш", g)} {gen(f)}'
    if fby == 'n':
        return f'количество вещества {pp_sh("образовавш", g)} {gen(f)} (моль)'
    return f'массу {pp_sh("образовавш", g)} {gen(f)}'


@proto('ch-ege-28-imp', 'ЕГЭ', 28, 'Расчёт по уравнению, если исходное вещество содержит примеси',
       invariant='m(чистого) = m(техн.)·(100 − ω(прим.))/100 → n → по коэффициентам n(продукта) → m или V',
       varies='сырьё (технический FeS, мрамор, известняк, селитры, карбиды, руды, пирит …), продукт — газ или твёрдое, '
              'доля примесей, точность',
       answer_rule='масса (г) или объём (л, н.у.) продукта с указанной точностью',
       mistakes=['не вычли примеси', 'использовали долю примесей вместо доли чистого вещества', 'не учли коэффициенты'],
       solve=_solve_28, kes=['5.4'],
       fidelity=fid('число, г или л с точностью до целых/десятых/сотых', 'как зад. 28 демоверсии 2027 (первый вариант: '
                    'технический FeS, 12 % примесей) — формулировка своя; уравнение в условии не дано', 'Б', 4,
                    'массы сырья 5–1000 г, примеси 2–30 %', 'масса чистого вещества = m·(1 − ω(прим.))', ['5.4'],
                    '1 балл'))
def g28_imp(rng):
    r = pick(rng, D.STOICH)
    c = r['calc']
    g, f = c['g'], c['f']
    k = coef(r['lhs'], r['rhs'])
    Mg = M(g)
    imp = rng.choice([2, 4, 5, 6, 8, 10, 12, 15, 16, 20, 24, 25, 30])
    m = Fr(rng.choice(list(range(5, 101)) + list(range(100, 1001, 25))))
    pure = m * (100 - imp) / 100
    nf = pure / Mg * k[f] / k[g]
    fby = 'V' if is_gas(f) else 'm'
    dec = rng.choice([0, 1, 2]) if fby == 'V' else rng.choice([0, 1])
    val = nf * _unit(f, fby)
    if val < Fr(1, 2):
        raise Retry
    ans = rnd(val, dec)
    raw = c['raw'][0]
    tpl = rng.randrange(3)
    if tpl == 0:
        q = f'Образец ({raw}) массой {ru(m)} г, содержащий {imp} % {c["imp"]}, {c["act"]}. Рассчитайте {_want(f, fby)}.'
    elif tpl == 1:
        q = f'Образец сырья ({raw}) массой {ru(m)} г содержит {100 - imp} % {gen(g)} по массе; остальное — примеси, ' \
            f'не участвующие в реакции. Образец {c["act"]}. Определите {_want(f, fby)}.'
    else:
        q = f'В заводской лаборатории {ru(m)} г сырья ({raw}) {c["act"]}. Содержание {c["imp"]} в сырье — {imp} % по ' \
            f'массе. Найдите {_want(f, fby)}.'
    q += ' ' + tail(dec)
    eqs, eq = eqp(r['lhs'], r['rhs'])
    unit = _unit(f, fby)
    e = f'{eqs}; m({pretty(g)}) = {ru(m)}·{100 - imp}/100 = {ru(pure)} г; n = m/{ru(Mg)}; ' \
        f'n({pretty(f)}) = n·{k[f]}/{k[g]}; ' + ('V = n·22,4' if fby == 'V' else f'm = n·{ru(M(f))}') + f' ≈ {ans}.'
    wrong = W([m / Mg * k[f] / k[g] * unit, m * imp / 100 / Mg * k[f] / k[g] * unit,
               pure / Mg * unit if k[f] != k[g] else pure / Mg * unit * 2], dec)
    return pcard('ch-ege-28-imp', q, ans, e, p=dict(lhs=r['lhs'], rhs=r['rhs'], g=g, f=f, m=str(m), imp=imp, gby='m',
                                                    fby=fby, dec=dec), wrong=wrong, eq=eq)


@proto('ch-ege-28-yield', 'ЕГЭ', 28, 'Масса (объём) продукта с учётом практического выхода',
       invariant='n(продукта, теор.) по уравнению; практическое = теоретическое·η/100',
       varies='реакция (промышленный синтез, брожение, этерификация, нитрование, восстановление металлов …), дано — '
              'масса или объём, выход, продукт — масса или объём',
       answer_rule='масса или объём продукта с указанной точностью',
       mistakes=['поделили на выход вместо умножения', 'не учли коэффициенты', 'объём вместо массы'],
       solve=_solve_28, kes=['5.5'],
       fidelity=fid('число, г или л', 'как зад. 28 демоверсии 2027 (второй вариант: сера из H₂S, выход 62,5 %) — '
                    'формулировка своя', 'Б', 4, 'массы 5–1000 г, объёмы 1–100 л, выход 40–95 %',
                    'практический = теоретический·η', ['5.5'], '1 балл'))
def g28_yield(rng):
    r = pick(rng, D.YIELD)
    c = r['calc']
    g, f = c['g'], c['f']
    k = coef(r['lhs'], r['rhs'])
    gby = 'V' if is_gas(g) and rng.random() < 0.8 else 'm'
    if gby == 'V':
        ng = Fr(rng.choice(range(1, 81)), rng.choice([4, 10, 20]))
        val = ng * VM
        if not nice(val, 2):
            raise Retry
    else:
        val = Fr(rng.choice(list(range(5, 201)) + list(range(200, 1001, 50))))
        ng = val / M(g)
    eta = Fr(rng.choice([40, 45, 50, 55, 60, 62.5, 65, 70, 75, 78, 80, 82, 85, 88, 90, 92, 95])).limit_denominator(10)
    fby = 'V' if is_gas(f) and rng.random() < 0.7 else 'm'
    dec = rng.choice([0, 1, 2]) if fby == 'V' else rng.choice([0, 1])
    x = ng * k[f] / k[g] * eta / 100 * _unit(f, fby)
    if x < Fr(1, 2):
        raise Retry
    ans = rnd(x, dec)
    amount = f'{ru(val)} л (н.у.) {gen(g)}' if gby == 'V' else f'{ru(val)} г {gen(g)}'
    act = c['act'].format(g=amount)
    want = f'объём (н.у.) {gen(f)}' if fby == 'V' else f'массу {gen(f)}'
    got = pp_nn('полученн', gnd(f))
    q = rng.choice([f'Практический выход {gen(f)} при {act} равен {ru(eta)} %. Рассчитайте {want}, {got} на практике.',
                    f'При {act} образовался продукт — {NOM[f]}; его выход составил {ru(eta)} % от теоретического. '
                    f'Определите {want}.',
                    f'Определите {want}, {got} при {act}, если потери продукта составили {ru(100 - eta)} %.'])
    q += ' ' + tail(dec)
    eqs, eq = eqp(r['lhs'], r['rhs'])
    unit = _unit(f, fby)
    e = f'{eqs}; n({pretty(g)}) = {fmt(ng, 4)} моль; n({pretty(f)}, теор.) = n·{k[f]}/{k[g]}; практически ·{ru(eta)}/100 ⇒ {ans}.'
    wrong = W([ng * k[f] / k[g] * unit, ng * k[f] / k[g] * unit * 100 / eta, ng * eta / 100 * unit if k[f] != k[g] else x * 2],
              dec)
    return pcard('ch-ege-28-yield', q, ans, e, p=dict(lhs=r['lhs'], rhs=r['rhs'], g=g, f=f, m=str(val), gby=gby, fby=fby,
                                                      eta=str(eta), dec=dec), wrong=wrong, eq=eq)


def _solve_28_eta(p):
    k = coef(p['lhs'], p['rhs'])
    ng = Fr(p['m']) / _unit_i(p['g'], p['gby'])
    theo = ng * k[p['f']] / k[p['g']] * _unit_i(p['f'], p['fby'])
    return rs(Fr(p['prac']) / theo * 100, p['dec'])


@proto('ch-ege-28-eta', 'ЕГЭ', 28, 'Выход продукта реакции от теоретически возможного',
       invariant='η = m(практ.)/m(теор.)·100 % (или по объёму, по количеству вещества)',
       varies='реакция, дано исходное вещество (масса или объём) и практически полученное количество продукта',
       answer_rule='выход в % с указанной точностью',
       mistakes=['перевернули отношение', 'не учли коэффициенты при расчёте теоретического количества'],
       solve=_solve_28_eta, kes=['5.5'],
       fidelity=fid('число, % до целых/десятых', 'КИМ-стиль: «При … получили … Определите выход продукта» — своими '
                    'словами', 'Б', 4, 'как в банке: 96 г Mg → 50,4 г Si; 61 г KClO₃ → 13,44 л O₂', 'теоретический расчёт '
                    'по уравнению', ['5.5'], '1 балл'))
def g28_eta(rng):
    r = pick(rng, D.YIELD + [x for x in D.STOICH if x['calc']['g'] in ('CaCO3', 'Zn', 'Al', 'CaC2', 'NaNO3', 'KMnO4')])
    c = r['calc']
    g, f = c['g'], c['f']
    k = coef(r['lhs'], r['rhs'])
    gby = 'V' if is_gas(g) and rng.random() < 0.7 else 'm'
    if gby == 'V':
        ng = Fr(rng.choice(range(1, 81)), rng.choice([4, 10, 20]))
        val = ng * VM
        if not nice(val, 2):
            raise Retry
    else:
        val = Fr(rng.choice(list(range(5, 201)) + list(range(200, 1001, 50))))
        ng = val / M(g)
    fby = 'V' if is_gas(f) and rng.random() < 0.6 else 'm'
    theo = ng * k[f] / k[g] * _unit(f, fby)
    eta = Fr(rng.choice(range(40, 97)))
    prac = Fr(round(theo * eta), 100)
    if prac <= 0:
        raise Retry
    dec = rng.choice([0, 1])
    x = prac / theo * 100
    ans = rnd(x, dec)
    amount = f'{ru(val)} л (н.у.) {gen(g)}' if gby == 'V' else f'{ru(val)} г {gen(g)}'
    got = f'{ru(prac)} л (н.у.)' if fby == 'V' else f'{ru(prac)} г'
    if '{g}' in c['act']:
        s = f'При {c["act"].format(g=amount)} удалось выделить {got} {gen(f)}.'
    elif gby == 'm':
        s = f'Навеску чистого вещества ({NOM[g]}) массой {ru(val)} г {c["act"]}; выделено {got} {gen(f)}.'
    else:
        s = f'Порцию {gen(g)} объёмом {ru(val)} л (н.у.) {c["act"]}; выделено {got} {gen(f)}.'
    q = s + ' ' + rng.choice([f'Рассчитайте выход {gen(f)} (%) по отношению к теоретическому.',
                              'Какую долю (%) от теоретически рассчитанного количества составляет полученный продукт?'])
    q += ' ' + tail(dec)
    eqs, eq = eqp(r['lhs'], r['rhs'])
    e = f'{eqs}; теоретически n({pretty(f)}) = {fmt(ng * k[f] / k[g], 4)} моль ⇒ {fmt(theo, 3)}; η = {ru(prac)}/{fmt(theo, 3)}·100 % ≈ {ans} %.'
    wrong = W([theo / prac * 100, prac / (ng * _unit(f, fby)) * 100 if k[f] != k[g] else x / 2, prac / val * 100], dec)
    return pcard('ch-ege-28-eta', q, ans, e, p=dict(lhs=r['lhs'], rhs=r['rhs'], g=g, f=f, m=str(val), gby=gby, fby=fby,
                                                    prac=str(prac), dec=dec), wrong=wrong, eq=eq)


def _solve_28_excess(p):
    k = coef(p['lhs'], p['rhs'])
    a, b = p['lhs'][0], p['lhs'][1]
    na = Fr(p['va']) / _unit_i(a, p['aby'])
    nb = Fr(p['vb']) / _unit_i(b, p['bby'])
    ext = min(na / k[a], nb / k[b])
    return rs(ext * k[p['f']] * _unit_i(p['f'], p['fby']), p['dec'])


@proto('ch-ege-28-excess', 'ЕГЭ', 28, 'Расчёт по уравнению, когда одно из веществ в избытке',
       invariant='сравнить n(A)/k(A) и n(B)/k(B); продукт считают по веществу в недостатке',
       varies='реакция (осаждение из растворов, нейтрализация, спекание металла с серой, смеси газов, металл + кислота), '
              'количества реагентов',
       answer_rule='масса (г) или объём (л) продукта с указанной точностью',
       mistakes=['расчёт по веществу в избытке', 'сравнили массы, а не количества вещества', 'не учли коэффициенты'],
       solve=_solve_28_excess, kes=['5.4'],
       fidelity=fid('число, г или л', 'КИМ-стиль: даны количества двух реагентов, найти продукт', 'Б', 4,
                    'массы 2–100 г, объёмы 1–50 л', 'определить недостаток по n/k', ['5.4'], '1 балл'))
def g28_excess(rng):
    r = pick(rng, D.EXCESS)
    c = r['calc']
    A0, B0 = r['lhs'][0], r['lhs'][1]
    f = c['f']
    k = coef(r['lhs'], r['rhs'])
    how = c['how']
    by = 'V' if how in ('gases', 'gases_m') else 'm'
    na = Fr(rng.choice(range(1, 41)), 20)
    ratio = Fr(rng.choice([3, 4, 5, 6, 7, 8, 12, 13, 14, 15, 16, 18, 20]), 10)
    nb = na / k[A0] * k[B0] * ratio
    if rng.random() < 0.5:
        na, nb = nb / k[B0] * k[A0], na / k[A0] * k[B0]
    va, vb = na * _unit(A0, by), nb * _unit(B0, by)
    if not nice(va, 2) or not nice(vb, 2):
        raise Retry
    fby = 'V' if how in ('gases', 'metal_acid') else 'm'
    ext = min(na / k[A0], nb / k[B0])
    x = ext * k[f] * _unit(f, fby)
    dec = rng.choice([0, 1, 2])
    ans = rnd(x, dec)
    A = lambda s, v: f'{ru(v)} л {gen(s)}' if by == 'V' else f'{ru(v)} г {gen(s)}'
    first, second = ((A0, va), (B0, vb)) if rng.random() < 0.5 else ((B0, vb), (A0, va))
    if how == 'solutions':
        tgt = 'выпавшего осадка' if c['what'] == 'осадка' else f'образовавшейся {c["what"]}'
        q = rng.choice([f'Раствор, в котором содержится {A(*first)}, слили с раствором, содержащим {A(*second)}. '
                        f'Найдите массу {tgt}.',
                        f'В лаборатории смешали два раствора: первый содержал {A(*first)}, второй — {A(*second)}. '
                        f'Рассчитайте массу {tgt}.'])
    elif how == 'solids':
        q = f'Порошки {A(*first)} и {A(*second)} тщательно перемешали и нагрели без доступа воздуха до окончания ' \
            f'реакции. Рассчитайте массу образовавшегося {c["what"]}.'
    elif how == 'gases':
        q = f'Газовую смесь, состоящую из {A(*first)} и {A(*second)} (н.у.), облучили светом до окончания реакции. ' \
            f'Найдите объём (н.у.) образовавшегося {c["what"]}.'
    elif how == 'gases_m':
        q = f'В эвдиометре взорвали смесь {A(*first)} и {A(*second)} (объёмы при н.у.). Какая масса воды образовалась?'
    else:
        metal = A0 if A0 != 'HCl' else B0
        vm = va if metal == A0 else vb
        vac = vb if metal == A0 else va
        q = f'Навеску {gen(metal)} массой {ru(vm)} г опустили в раствор, содержащий {ru(vac)} г хлороводорода. ' \
            f'Найдите объём (н.у.) выделившегося водорода.'
    q += ' ' + tail(dec)
    kl, kr = balance(r['lhs'], r['rhs'])
    lim = A0 if na / k[A0] < nb / k[B0] else B0
    exc = B0 if lim == A0 else A0
    n_exc = na if exc == A0 else nb
    e = f'{pretty(eq_str(r["lhs"], r["rhs"], kl, kr))}; n({pretty(A0)}) = {fmt(na, 4)} моль, n({pretty(B0)}) = {fmt(nb, 4)} моль; ' \
        f'в недостатке {pretty(lim)}; n({pretty(f)}) = {fmt(ext * k[f], 4)} моль ⇒ {ans}.'
    unit = _unit(f, fby)
    wrong = W([n_exc / k[exc] * k[f] * unit, (na + nb) / 2 * unit, ext * unit if k[f] != 1 else ext * 2 * unit], dec)
    return pcard('ch-ege-28-excess', q, ans, e, p=dict(lhs=r['lhs'], rhs=r['rhs'], f=f, va=str(va), vb=str(vb), aby=by,
                                                       bby=by, fby=fby, dec=dec), wrong=wrong, eq=(r['lhs'], r['rhs'], kl, kr))


def _solve_28_raw(p):
    k = coef(p['lhs'], p['rhs'])
    g, f = p['g'], p['f']
    nf = Fr(p['pv']) / _unit_i(f, p['fby'])
    pure = nf * k[g] / k[f] * Mi(g)
    if p['mode'] == 'raw':
        return rs(pure * 100 / (100 - Fr(p['imp'])), p['dec'])
    return rs((Fr(p['m']) - pure) / Fr(p['m']) * 100, p['dec'])


@proto('ch-ege-28-raw', 'ЕГЭ', 28, 'Масса сырья с примесями или доля примесей по количеству продукта',
       invariant='по продукту находят n и массу чистого вещества; m(сырья) = m(чист.)·100/(100 − ω(прим.)) или '
                 'ω(прим.) = (m(обр.) − m(чист.))/m(обр.)·100 %',
       varies='сырьё и реакция, что найти (масса сырья или доля примесей), продукт — газ или твёрдое',
       answer_rule='масса (г) или доля (%) с указанной точностью',
       mistakes=['умножили на (100 − ω) вместо деления', 'нашли долю чистого вещества вместо доли примесей'],
       solve=_solve_28_raw, kes=['5.4'],
       fidelity=fid('число, г или %', 'КИМ-стиль обратной задачи на примеси (в банке: 1 кг карбида → 280 л C₂H₂, '
                    'доля примесей)', 'Б', 4, 'как в банке', 'обратный ход через массу чистого вещества', ['5.4'],
                    '1 балл'))
def g28_raw(rng):
    r = pick(rng, D.STOICH)
    c = r['calc']
    g, f = c['g'], c['f']
    k = coef(r['lhs'], r['rhs'])
    fby = 'V' if is_gas(f) else 'm'
    nf = Fr(rng.choice(range(1, 101)), rng.choice([10, 20, 40]))
    pv = nf * _unit(f, fby)
    if not nice(pv, 2):
        raise Retry
    pure = nf * k[g] / k[f] * M(g)
    imp = rng.choice([4, 5, 6, 8, 10, 12, 15, 20, 25, 30])
    mode = rng.choice(['raw', 'imp'])
    dec = rng.choice([0, 1])
    got = f'{ru(pv)} л (н.у.) {gen(f)}' if fby == 'V' else f'{ru(pv)} г {gen(f)}'
    raw = c['raw'][0]
    if mode == 'raw':
        x = pure * 100 / (100 - imp)
        q = f'Сырьё ({raw}) содержит {imp} % {c["imp"]}. Некоторую массу сырья {c["act"]} и получили {got}. ' \
            f'Рассчитайте массу взятого сырья.'
        wrong = W([pure, pure * (100 - imp) / 100, pure * (100 + imp) / 100], dec)
        p = dict(lhs=r['lhs'], rhs=r['rhs'], g=g, f=f, pv=str(pv), fby=fby, imp=imp, mode=mode, dec=dec)
    else:
        m = pure * 100 / (100 - imp)
        m = Fr(math.ceil(m * 10), 10) if not nice(m, 2) else m
        x = (m - pure) / m * 100
        if x <= 0:
            raise Retry
        q = f'Сырьё ({raw}) массой {ru(m)} г {c["act"]} и получили {got}. Рассчитайте массовую долю примесей в сырье (%).'
        wrong = W([pure / m * 100, (m - pure) / pure * 100, x / 2], dec)
        p = dict(lhs=r['lhs'], rhs=r['rhs'], g=g, f=f, pv=str(pv), fby=fby, m=str(m), mode=mode, dec=dec)
    ans = rnd(x, dec)
    q += ' ' + tail(dec)
    eqs, eq = eqp(r['lhs'], r['rhs'])
    e = f'{eqs}; n({pretty(f)}) = {ru(nf)} моль ⇒ n({pretty(g)}) = {fmt(nf * k[g] / k[f], 4)} моль, m(чист.) = ' \
        f'{fmt(pure, 2)} г ⇒ {ans}.'
    return pcard('ch-ege-28-raw', q, ans, e, p=p, wrong=wrong, eq=eq)


def _solve_28_simple(p):
    k = coef(p['lhs'], p['rhs'])
    n = Fr(p['v']) / _unit_i(p['g'], p['gby'])
    return rs(n * k[p['f']] / k[p['g']] * _unit_i(p['f'], p['fby']), p['dec'])


SIMPLE28 = [  # (lhs, rhs, название процесса)
    (['Zn', 'H2SO4'], ['ZnSO4', 'H2'], 'растворение цинка в разбавленной серной кислоте'),
    (['Al', 'HCl'], ['AlCl3', 'H2'], 'растворение алюминия в соляной кислоте'),
    (['Mg', 'HCl'], ['MgCl2', 'H2'], 'растворение магния в соляной кислоте'),
    (['Fe', 'HCl'], ['FeCl2', 'H2'], 'растворение железа в соляной кислоте'),
    (['NaNO3'], ['NaNO2', 'O2'], 'термическое разложение нитрата натрия'),
    (['KNO3'], ['KNO2', 'O2'], 'термическое разложение нитрата калия'),
    (['KClO3'], ['KCl', 'O2'], 'каталитическое разложение хлората калия'),
    (['Cu(OH)2'], ['CuO', 'H2O'], 'прокаливание гидроксида меди(II)'),
    (['Fe(OH)3'], ['Fe2O3', 'H2O'], 'прокаливание гидроксида железа(III)'),
    (['CaCO3'], ['CaO', 'CO2'], 'обжиг карбоната кальция'),
    (['MgCO3'], ['MgO', 'CO2'], 'прокаливание карбоната магния'),
    (['CuO', 'H2'], ['Cu', 'H2O'], 'восстановление оксида меди(II) водородом'),
    (['Fe2O3', 'Al'], ['Al2O3', 'Fe'], 'алюмотермическое восстановление оксида железа(III)'),
    (['NaOH', 'H2SO4'], ['Na2SO4', 'H2O'], 'полная нейтрализация серной кислоты гидроксидом натрия'),
    (['Ca(OH)2', 'HNO3'], ['Ca(NO3)2', 'H2O'], 'нейтрализация азотной кислоты гидроксидом кальция'),
    (['Na2CO3', 'HCl'], ['NaCl', 'CO2', 'H2O'], 'взаимодействие карбоната натрия с соляной кислотой'),
    (['Na2SO3', 'H2SO4'], ['Na2SO4', 'SO2', 'H2O'], 'взаимодействие сульфита натрия с серной кислотой'),
    (['NH3', 'HCl'], ['NH4Cl'], 'поглощение аммиака соляной кислотой'),
    (['CaC2', 'H2O'], ['Ca(OH)2', 'C2H2'], 'гидролиз карбида кальция'),
    (['FeS', 'HCl'], ['FeCl2', 'H2S'], 'действие соляной кислоты на сульфид железа(II)'),
    (['H2S', 'O2'], ['SO2', 'H2O'], 'полное сгорание сероводорода'),
    (['NH3', 'O2'], ['N2', 'H2O'], 'сгорание аммиака в кислороде'),
    (['Cu(NO3)2'], ['CuO', 'NO2', 'O2'], 'термическое разложение нитрата меди(II)'),
]


@proto('ch-ege-28-simple', 'ЕГЭ', 28, 'Масса, объём или количество вещества по уравнению (без примесей и выхода)',
       invariant='n(дано) = m/M или V/22,4; n(искомое) = n·k(иск.)/k(дано); ответ m, V или n',
       varies='реакция (разложение, металл + кислота, нейтрализация, горение, восстановление), дано и искомое — любой '
              'участник (прямая и обратная задачи), в моль, г или л',
       answer_rule='масса (г), объём (л) или количество вещества (моль) с указанной точностью',
       mistakes=['не учли коэффициенты', 'объём газа через молярную массу', 'перевернули отношение коэффициентов'],
       solve=_solve_28_simple, kes=['5.1'],
       fidelity=fid('число, г, л или моль', 'задания банка с КЭС 5.1 (краткий ответ): «Определите объём водорода (н.у.), '
                    'который выделится при …» — относим к № 28 как базовый расчёт по уравнению; уравнение в условии '
                    'не дано', 'Б', 3, 'как в банке: 0,2–5 моль, 2–340 г', 'коэффициенты уравнения', ['5.1'], '1 балл'))
def g28_simple(rng):
    lhs, rhs, proc = pick(rng, SIMPLE28)
    k = coef(lhs, rhs)
    g, f = rng.sample([s for s in lhs + rhs if s != 'H2O'], 2)
    gby = rng.choice(['n', 'm', 'm'] + (['V'] if is_gas(g) else []))
    fby = rng.choice(['V', 'V', 'm'] if is_gas(f) else ['m', 'm', 'n'])
    n = Fr(rng.choice(range(1, 81)), rng.choice([4, 8, 10, 20]))
    v = n * _unit(g, gby)
    if not nice(v, 3):
        raise Retry
    x = n * k[f] / k[g] * _unit(f, fby)
    dec = rng.choice([0, 1, 2])
    ans = rnd(x, dec)
    given = {'n': f'{ru(v)} моль', 'm': f'{ru(v)} г', 'V': f'{ru(v)} л (н.у.)'}[gby]
    role_g = 'израсходовано' if g in lhs else 'получено'
    want = {'V': f'объём (н.у.) {gen(f)}', 'm': f'массу {gen(f)}', 'n': f'количество вещества {gen(f)} (моль)'}[fby]
    role_f = pp_sh('вступивш', gnd(f)) + ' в реакцию' if f in lhs else pp_sh('образовавш', gnd(f))
    q = rng.choice([f'Протекает {proc}. Известно, что {role_g} {given} {gen(g)}. Рассчитайте {want}, {role_f}.',
                    f'В ходе процесса «{proc}» {role_g} {given} {gen(g)}. Определите {want}.'])
    q += ' ' + tail(dec)
    eqs, eq = eqp(lhs, rhs)
    e = f'{eqs}; n({pretty(g)}) = {ru(n)} моль; n({pretty(f)}) = {ru(n)}·{k[f]}/{k[g]} = {fmt(n * k[f] / k[g], 4)} моль ⇒ {ans}.'
    unit = _unit(f, fby)
    wrong = W([n * unit, n * k[g] / k[f] * unit, n * k[f] / k[g] * (M(f) if fby == 'V' else VM)], dec)
    return pcard('ch-ege-28-simple', q, ans, e, p=dict(lhs=lhs, rhs=rhs, g=g, f=f, v=str(v), gby=gby, fby=fby, dec=dec),
                 wrong=wrong, eq=eq)


# ======================================================================= ЕГЭ 18. Скорость реакции

PH = {'г': '(г)', 'тв': '(тв.)', 'р-р': '(р-р)', 'ж': '(ж)'}


def _r18(d, r, p, cat=None, rev=False):
    """d — «реакции чего» (род. п.); r/p — [(формула, фаза, род. п. названия)]; cat — катализатор; rev — обратимая."""
    return dict(d=d, r=r, p=p, cat=cat, rev=rev)


R18 = [
    _r18('железа с раствором серной кислоты', [('Fe', 'тв', 'железа'), ('H2SO4', 'р-р', 'серной кислоты')],
         [('FeSO4', 'р-р', 'сульфата железа(II)'), ('H2', 'г', 'водорода')]),
    _r18('цинка с соляной кислотой', [('Zn', 'тв', 'цинка'), ('HCl', 'р-р', 'хлороводорода')],
         [('ZnCl2', 'р-р', 'хлорида цинка'), ('H2', 'г', 'водорода')]),
    _r18('магния с соляной кислотой', [('Mg', 'тв', 'магния'), ('HCl', 'р-р', 'хлороводорода')],
         [('MgCl2', 'р-р', 'хлорида магния'), ('H2', 'г', 'водорода')]),
    _r18('алюминия с раствором серной кислоты', [('Al', 'тв', 'алюминия'), ('H2SO4', 'р-р', 'серной кислоты')],
         [('Al2(SO4)3', 'р-р', 'сульфата алюминия'), ('H2', 'г', 'водорода')]),
    _r18('мрамора с соляной кислотой', [('CaCO3', 'тв', 'мрамора'), ('HCl', 'р-р', 'хлороводорода')],
         [('CaCl2', 'р-р', 'хлорида кальция'), ('CO2', 'г', 'углекислого газа'), ('H2O', 'ж', 'воды')]),
    _r18('оксида меди(II) с раствором серной кислоты', [('CuO', 'тв', 'оксида меди(II)'), ('H2SO4', 'р-р', 'серной кислоты')],
         [('CuSO4', 'р-р', 'сульфата меди(II)'), ('H2O', 'ж', 'воды')]),
    _r18('цинка с раствором сульфата меди(II)', [('Zn', 'тв', 'цинка'), ('CuSO4', 'р-р', 'сульфата меди(II)')],
         [('ZnSO4', 'р-р', 'сульфата цинка'), ('Cu', 'тв', 'меди')]),
    _r18('железа с раствором хлорида меди(II)', [('Fe', 'тв', 'железа'), ('CuCl2', 'р-р', 'хлорида меди(II)')],
         [('FeCl2', 'р-р', 'хлорида железа(II)'), ('Cu', 'тв', 'меди')]),
    _r18('синтеза аммиака из азота и водорода', [('N2', 'г', 'азота'), ('H2', 'г', 'водорода')],
         [('NH3', 'г', 'аммиака')], cat='губчатое железо', rev=True),
    _r18('окисления оксида серы(IV) кислородом', [('SO2', 'г', 'оксида серы(IV)'), ('O2', 'г', 'кислорода')],
         [('SO3', 'г', 'оксида серы(VI)')], cat='оксид ванадия(V)', rev=True),
    _r18('серы с водородом', [('S', 'тв', 'серы'), ('H2', 'г', 'водорода')], [('H2S', 'г', 'сероводорода')]),
    _r18('горения угля', [('C', 'тв', 'угля'), ('O2', 'г', 'кислорода')], [('CO2', 'г', 'углекислого газа')]),
    _r18('окисления угарного газа кислородом', [('CO', 'г', 'угарного газа'), ('O2', 'г', 'кислорода')],
         [('CO2', 'г', 'углекислого газа')]),
    _r18('окисления оксида азота(II) кислородом', [('NO', 'г', 'оксида азота(II)'), ('O2', 'г', 'кислорода')],
         [('NO2', 'г', 'оксида азота(IV)')]),
    _r18('разложения пероксида водорода', [('H2O2', 'р-р', 'пероксида водорода')],
         [('H2O', 'ж', 'воды'), ('O2', 'г', 'кислорода')], cat='оксид марганца(IV)'),
    _r18('разложения хлората калия', [('KClO3', 'тв', 'хлората калия')],
         [('KCl', 'тв', 'хлорида калия'), ('O2', 'г', 'кислорода')], cat='оксид марганца(IV)'),
    _r18('восстановления оксида меди(II) водородом', [('CuO', 'тв', 'оксида меди(II)'), ('H2', 'г', 'водорода')],
         [('Cu', 'тв', 'меди'), ('H2O', 'г', 'паров воды')]),
    _r18('гидрирования этилена', [('C2H4', 'г', 'этилена'), ('H2', 'г', 'водорода')], [('C2H6', 'г', 'этана')],
         cat='никель', rev=True),
    _r18('обжига сульфида цинка', [('ZnS', 'тв', 'сульфида цинка'), ('O2', 'г', 'кислорода')],
         [('ZnO', 'тв', 'оксида цинка'), ('SO2', 'г', 'оксида серы(IV)')]),
    _r18('получения метанола из угарного газа и водорода', [('CO', 'г', 'угарного газа'), ('H2', 'г', 'водорода')],
         [('CH3OH', 'г', 'метанола')], cat='оксиды цинка и хрома', rev=True),
    _r18('кальция с водой', [('Ca', 'тв', 'кальция'), ('H2O', 'ж', 'воды')],
         [('Ca(OH)2', 'р-р', 'гидроксида кальция'), ('H2', 'г', 'водорода')]),
    _r18('железа с хлором', [('Fe', 'тв', 'железа'), ('Cl2', 'г', 'хлора')], [('FeCl3', 'тв', 'хлорида железа(III)')]),
    _r18('цинка с серой', [('Zn', 'тв', 'цинка'), ('S', 'тв', 'серы')], [('ZnS', 'тв', 'сульфида цинка')]),
    _r18('растворов хлорида бария и сульфата натрия', [('BaCl2', 'р-р', 'хлорида бария'), ('Na2SO4', 'р-р', 'сульфата натрия')],
         [('BaSO4', 'тв', 'сульфата бария'), ('NaCl', 'р-р', 'хлорида натрия')]),
    _r18('оксида цинка с раствором гидроксида натрия', [('ZnO', 'тв', 'оксида цинка'), ('NaOH', 'р-р', 'гидроксида натрия'),
                                                           ('H2O', 'ж', 'воды')],
         [('Na2(Zn(OH)4)', 'р-р', 'тетрагидроксоцинката натрия')]),
]
SIMPLE_EL = {'Fe', 'Zn', 'Mg', 'Al', 'S', 'C', 'Cu', 'Ca', 'P'}


def _factors_dir(R):
    """(текст, эффект на скорость прямой реакции): +1 увеличивает, −1 уменьшает, 0 не влияет."""
    F = [('повышение температуры', 1), ('понижение температуры', -1)]
    gas_r = any(ph == 'г' for _, ph, _ in R['r'])
    F += [('повышение давления в системе', 1 if gas_r else 0), ('понижение давления в системе', -1 if gas_r else 0)]
    for f, ph, g in R['r']:
        if f == 'H2O':
            continue
        if ph in ('р-р', 'г'):
            F += [(f'увеличение концентрации {g}', 1), (f'уменьшение концентрации {g}', -1)]
        if ph == 'р-р' and f not in ('H2O2',):
            F += [(f'разбавление раствора {g} водой', -1)]
        if ph == 'тв':
            F += [(f'измельчение {g}', 1), (f'использование {g} в виде крупных кусков вместо порошка', -1)]
    if R['cat']:
        F += [(f'использование катализатора ({R["cat"]})', 1)]
    F += [('введение ингибитора', -1)]
    if not R['rev']:
        for f, ph, g in R['p']:
            if f == 'H2O':
                continue
            if ph == 'р-р':
                F += [(f'внесение в систему кристаллического {g}', 0)]
            elif ph == 'тв':
                F += [(f'добавление в систему {g}', 0)]
    if any(ph == 'р-р' for _, ph, _ in R['r']):
        F += [('добавление к раствору нескольких капель индикатора', 0)]
    return F


def _factors_aff(R):
    """(текст, влияет ли на скорость)."""
    gas_r = any(ph == 'г' for _, ph, _ in R['r'])
    F = [('изменение температуры', True), ('изменение давления в системе', gas_r)]
    for f, ph, g in R['r']:
        if f == 'H2O':
            continue
        if ph in ('р-р', 'г'):
            F += [(f'изменение концентрации {g}', True)]
        if ph == 'р-р':
            F += [(f'разбавление раствора {g} водой', True)]
        if ph == 'тв':
            F += [(f'степень измельчения {g}', True)]
    if R['cat']:
        F += [(f'присутствие катализатора ({R["cat"]})', True)]
    if not R['rev']:
        for f, ph, g in R['p']:
            if ph == 'р-р' and f != 'H2O':
                F += [(f'внесение в систему кристаллического {g}', False)]
            elif ph == 'тв':
                F += [(f'добавление в систему {g}', False)]
    if any(ph == 'р-р' for _, ph, _ in R['r']):
        F += [('добавление к раствору индикатора', False)]
    return F


def _pick5(rng, items, good, lo=1, hi=4):
    """5 вариантов из items [(текст, верно?)], верных от lo до hi; тексты не повторяются."""
    yes = [x for x in items if good(x)]
    no = [x for x in items if not good(x)]
    k = rng.randint(lo, hi)
    if len(yes) < k or len(no) < 5 - k:
        raise Retry
    ch = rng.sample(yes, k) + rng.sample(no, 5 - k)
    rng.shuffle(ch)
    if len({t for t, *_ in ch}) < 5:
        raise Retry
    return ch


def _solve_18_list(p):
    return [str(i + 1) for i, v in enumerate(p['truth']) if v]


def _how_many(k):
    return 'два' if k == 2 else 'все'


@proto('ch-ege-18-factor', 'ЕГЭ', 18, 'Внешние воздействия, увеличивающие (уменьшающие) скорость реакции',
       invariant='скорость растёт при нагревании, увеличении концентрации реагентов (раствор, газ), измельчении твёрдого '
                 'реагента, повышении давления при газообразном реагенте, катализаторе; продукты, индикатор, давление без '
                 'газообразных реагентов на скорость не влияют',
       varies='реакция (металл + кислота, мрамор + кислота, синтез аммиака, горение, окисление SO₂, разложение H₂O₂ …), '
              'увеличение или уменьшение скорости, «два» или «все» верных',
       answer_rule='номера всех верных воздействий (порядок не важен)',
       mistakes=['давление влияет и на реакции без газообразных реагентов', 'добавление продукта ускоряет реакцию',
                 'разбавление раствора не меняет скорость'],
       solve=_solve_18_list, kes=['1.6'],
       fidelity=fid('последовательность цифр (номера из 5), порядок не важен', 'КИМ: «Из предложенного перечня выберите '
                    'все (два) …, которые приводят к увеличению скорости …» + «Запишите номера выбранных ответов»', 'Б',
                    3, 'реакции и воздействия того же набора, что в банке (Fe + H₂SO₄, N₂ + H₂, CuO + HCl, S + H₂)',
                    'давление без газообразных реагентов; концентрация продукта; разбавление', ['1.6'],
                    '1 балл (в демо № 18 порядок записи не важен)'))
def g18_factor(rng):
    R = pick(rng, R18)
    up = rng.random() < 0.75
    items = _factors_dir(R)
    sign = 1 if up else -1
    ch = _pick5(rng, items, lambda x: x[1] == sign, 1, 4)
    k = sum(1 for _, v in ch if v == sign)
    noun = rng.choice(['внешних воздействия', 'фактора']) if k == 2 else rng.choice(['внешние воздействия', 'факторы'])
    q = rng.choice([f'Из предложенного перечня выберите {_how_many(k)} {noun}, которые {"ускоряют" if up else "замедляют"} '
                    f'реакцию {R["d"]}. {MANY_T}',
                    f'Из предложенного перечня выберите {_how_many(k)} {noun}, при которых реакция {R["d"]} протекает '
                    f'{"быстрее" if up else "медленнее"}. {MANY_T}'])
    o = opts([t for t, _ in ch])
    truth = [v == sign for _, v in ch]
    a = [str(i + 1) for i, v in enumerate(truth) if v]
    e = ('Скорость растёт при нагревании, увеличении концентрации реагентов, измельчении твёрдого вещества, катализаторе, '
         'а давление важно только при газообразных реагентах. ') + f'Верно: {", ".join(a)}.'
    return pcard('ch-ege-18-factor', q, a, e, k='many', o=o, p=dict(truth=truth))


@proto('ch-ege-18-affect', 'ЕГЭ', 18, 'Воздействия, которые влияют (не влияют) на скорость реакции',
       invariant='влияют: температура, концентрации реагентов, площадь поверхности твёрдого реагента, катализатор, '
                 'давление — только при газообразных реагентах; не влияют: индикатор, добавление твёрдого продукта',
       varies='реакция, вопрос «влияют» или «не влияют», набор воздействий',
       answer_rule='номера всех верных воздействий (порядок не важен)',
       mistakes=['давление влияет на реакции в растворе', 'добавление продукта меняет скорость'],
       solve=_solve_18_list, kes=['1.6'],
       fidelity=fid('последовательность цифр (номера из 5)', 'КИМ: «… выберите все внешние воздействия, которые влияют на '
                    'скорость реакции между …»', 'Б', 3, 'как в банке (CuSO₄ + Fe, HCl + Al)', 'давление; продукт',
                    ['1.6'], '1 балл'))
def g18_affect(rng):
    R = pick(rng, R18)
    items = _factors_aff(R)
    neg = rng.random() < 0.3
    ch = _pick5(rng, items, (lambda x: not x[1]) if neg else (lambda x: x[1]), 1, 4)
    truth = [(not v) if neg else v for _, v in ch]
    k = sum(truth)
    q = f'Из предложенного перечня выберите {_how_many(k)} {"внешних воздействия" if k == 2 else "внешние воздействия"}, ' \
        f'которые {"никак не сказываются" if neg else "сказываются"} на скорости реакции {R["d"]}. {MANY_T}'
    a = [str(i + 1) for i, v in enumerate(truth) if v]
    e = 'На скорость влияют температура, концентрации реагентов, измельчение твёрдого реагента, катализатор; давление — ' \
        f'только если среди реагентов есть газы. Ответ: {", ".join(a)}.'
    return pcard('ch-ege-18-affect', q, a, e, k='many', o=opts([t for t, _ in ch]), p=dict(truth=truth))


def _eq18(R):
    lhs = [f for f, _, _ in R['r']]
    rhs = [f for f, _, _ in R['p']]
    kl, kr = balance(lhs, rhs)
    st = [ph for _, ph, _ in R['r']] + [ph for _, ph, _ in R['p']]
    side = lambda ss, ks, sts: ' + '.join((str(k) if k > 1 else '') + pretty(s) + PH[t] for s, k, t in zip(ss, ks, sts))
    return side(lhs, kl, st[:len(lhs)]) + ' = ' + side(rhs, kr, st[len(lhs):]), (lhs, rhs, kl, kr)


@proto('ch-ege-18-eqlist', 'ЕГЭ', 18, 'Уравнения реакций, на скорость которых влияет данный фактор',
       invariant='давление — если есть газообразный реагент; концентрация кислоты — если кислота среди реагентов в растворе; '
                 'измельчение — если реагент твёрдое простое вещество',
       varies='фактор (повышение давления, концентрация кислоты, измельчение простого вещества), прямой или обратный '
              'вопрос («не влияет»), набор уравнений с агрегатными состояниями',
       answer_rule='номера всех подходящих уравнений (порядок не важен)',
       mistakes=['учитывают газообразный продукт вместо реагента', 'не различают твёрдое и растворённое вещество'],
       solve=_solve_18_list, kes=['1.6'],
       fidelity=fid('последовательность цифр', 'КИМ: «Из предложенного перечня выберите уравнения всех реакций, для '
                    'которых …» с уравнениями и агрегатными состояниями', 'Б', 3, 'уравнения банка того же типа',
                    'газообразный продукт ≠ газообразный реагент', ['1.6'], '1 балл'))
def g18_eqlist(rng):
    mode = rng.choice(['p', 'p', 'p_no', 'acid', 'grind'])
    tests = {
        'p': lambda R: any(ph == 'г' for _, ph, _ in R['r']),
        'p_no': lambda R: not any(ph == 'г' for _, ph, _ in R['r']),
        'acid': lambda R: any(ph == 'р-р' and f in ('HCl', 'H2SO4') for f, ph, _ in R['r']),
        'grind': lambda R: any(ph == 'тв' and f in SIMPLE_EL for f, ph, _ in R['r']),
    }
    items = [(R, tests[mode](R)) for R in R18 if R['d'] != 'разложения пероксида водорода']
    ch = _pick5(rng, [(_eq18(R)[0], v, R) for R, v in items], lambda x: x[1], 1, 4)
    truth = [v for _, v, _ in ch]
    k = sum(truth)
    ask = {'p': 'для которых повышение давления приводит к увеличению скорости',
           'p_no': 'скорость которых не зависит от давления',
           'acid': 'для которых увеличение концентрации кислоты приводит к увеличению скорости',
           'grind': 'на скорость которых влияет степень измельчения простого вещества'}[mode]
    q = f'Из предложенного перечня выберите {"два уравнения реакций" if k == 2 else "уравнения всех реакций"}, {ask}. {MANY_T}'
    a = [str(i + 1) for i, v in enumerate(truth) if v]
    e = {'p': 'Давление влияет, если среди реагентов есть газ.', 'p_no': 'Без газообразных реагентов давление не влияет.',
         'acid': 'Кислота должна быть реагентом в растворе.',
         'grind': 'Нужен твёрдый реагент — простое вещество.'}[mode] + f' Ответ: {", ".join(a)}.'
    eqs = [_eq18(R)[1] for _, _, R in ch]
    return pcard('ch-ege-18-eqlist', q, a, e, k='many', o=opts([t for t, _, _ in ch]), p=dict(truth=truth), eqs=eqs)


SUBST18 = {  # реагент (раствор) → [(вещество, газ?)] — все реагируют с ним при комнатной температуре
    'раствором гидроксида калия': [('оксид углерода(IV)', True), ('оксид серы(IV)', True), ('сероводород', True),
                                   ('оксид азота(IV)', True), ('хлор', True), ('хлороводород', True),
                                   ('оксид алюминия', False), ('оксид цинка', False), ('оксид фосфора(V)', False),
                                   ('алюминий', False), ('гидроксид цинка', False), ('хлорид аммония', False),
                                   ('сульфат меди(II)', False), ('хлорид железа(III)', False)],
    'соляной кислотой': [('аммиак', True), ('метиламин', True), ('диметиламин', True),
                         ('цинк', False), ('железо', False), ('карбонат кальция', False), ('оксид меди(II)', False),
                         ('гидроксид магния', False), ('нитрат серебра', False), ('карбонат калия', False),
                         ('оксид магния', False)],
    'бромной водой': [('этилен', True), ('ацетилен', True), ('пропен', True), ('оксид серы(IV)', True),
                      ('сероводород', True), ('фенол', False), ('анилин', False), ('иодид калия', False),
                      ('олеиновая кислота', False)],
    'водой': [('аммиак', True), ('хлор', True), ('оксид серы(IV)', True), ('оксид азота(IV)', True),
              ('натрий', False), ('кальций', False), ('оксид кальция', False), ('оксид фосфора(V)', False),
              ('карбид кальция', False), ('гидрид натрия', False)],
}


@proto('ch-ege-18-subst', 'ЕГЭ', 18, 'Вещества (пары реагентов), для которых скорость зависит от давления',
       invariant='давление влияет на скорость, только если хотя бы один реагент — газ',
       varies='реагент в растворе (щёлочь, кислота, бромная вода, вода) и набор веществ; либо набор пар реагентов с '
              'агрегатными состояниями',
       answer_rule='номера всех газообразных веществ (пар с газообразным реагентом), порядок не важен',
       mistakes=['считают, что давление влияет на реакции твёрдых и растворённых веществ',
                 'путают газообразный продукт с реагентом'],
       solve=_solve_18_list, kes=['1.6'],
       fidelity=fid('последовательность цифр', 'КИМ: «… выберите все вещества, на скорость взаимодействия которых с … при '
                    'комнатной температуре влияет изменение давления» / «… все реагенты, скорость реакции между которыми …»',
                    'Б', 3, 'вещества того же круга, что в банке (H₂S, CO₂, NO₂, Al₂O₃, P₂O₅)', 'агрегатное состояние '
                    'реагента', ['1.6'], '1 балл'))
def g18_subst(rng):
    if rng.random() < 0.55:
        reag = pick(rng, list(SUBST18))
        ch = _pick5(rng, SUBST18[reag], lambda x: x[1], 1, 4)
        truth = [v for _, v in ch]
        q = f'Из предложенного перечня выберите {"два вещества" if sum(truth) == 2 else "все вещества"}, для которых ' \
            f'скорость реакции с {reag} (при комнатной температуре) зависит от давления. {MANY_T}'
        o = opts([t for t, _ in ch])
        eqs = None
    else:
        pool = []
        for R in R18:
            if len(R['r']) != 2:
                continue
            txt = ' и '.join(f'{pretty(f)} {PH[ph]}' for f, ph, _ in R['r'])
            pool.append((txt, any(ph == 'г' for _, ph, _ in R['r']), R))
        ch = _pick5(rng, pool, lambda x: x[1], 1, 4)
        truth = [v for _, v, _ in ch]
        q = f'Из предложенного перечня выберите {"две пары" if sum(truth) == 2 else "все пары"} реагентов, для которых ' \
            f'увеличение давления ускоряет реакцию между ними. {MANY_T}'
        o = opts([t for t, _, _ in ch])
        eqs = [_eq18(R)[1] for _, _, R in ch]
    a = [str(i + 1) for i, v in enumerate(truth) if v]
    e = f'Давление влияет на скорость только при газообразном реагенте. Ответ: {", ".join(a)}.'
    return pcard('ch-ege-18-subst', q, a, e, k='many', o=o, p=dict(truth=truth), eqs=eqs)


METALS18 = [('Mg', 'магния', 3, 'магний'), ('Zn', 'цинка', 2, 'цинк'), ('Fe', 'железа', 1, 'железо')]
ACIDS18 = [('соляной кислотой', 2, 'HCl (р-р)'), ('раствором серной кислоты', 2, 'H₂SO₄ (разб. р-р)'),
           ('бромоводородной кислотой', 2, 'HBr (р-р)'), ('раствором уксусной кислоты', 1, 'CH₃COOH (р-р)'),
           ('раствором пропионовой кислоты', 1, 'C₂H₅COOH (р-р)')]
FORMS18 = [('порошка', 2, 'порошок'), ('гранул', 1, 'гранулы')]
FAST18 = ['NaOH (р-р) + CH₃COOH (р-р)', 'Ba(OH)₂ (р-р) + HNO₃ (р-р)', 'Na₂CO₃ (р-р) + HCl (р-р)',
          'KOH (р-р) + H₂SO₄ (р-р)']
ALC18 = [('воды', 5, 'H₂O'), ('метанола', 4, 'CH₃OH'), ('этанола', 3, 'C₂H₅OH'), ('пропанола-1', 2, 'пропанол-1'),
         ('бутанола-1', 2, 'бутанол-1'), ('пропанола-2', 1, 'пропанол-2')]
AMET18 = [('калия', 3, 'K'), ('натрия', 2, 'Na'), ('лития', 1, 'Li')]
PAIRS18 = [  # (два раствора, реагирующие между собой; твёрдые вещества, реагирующие с одним из растворов)
    (('AgNO3 (р-р)', 'HCl (р-р)'), ['FeO', 'BaCO3', 'Mg(OH)2', 'Zn (гранулы)', 'CuO']),
    (('Ca(OH)2 (р-р)', 'HCl (р-р)'), ['Fe (проволока)', 'Fe (порошок)', 'MgO', 'CaCO3', 'Al (гранулы)']),
    (('BaCl2 (р-р)', 'H2SO4 (р-р)'), ['Zn (гранулы)', 'CuO', 'MgCO3', 'Fe (порошок)', 'Al2O3']),
    (('NaOH (р-р)', 'HNO3 (р-р)'), ['ZnO', 'CaCO3', 'Cu (стружка)', 'Al(OH)3', 'MgO']),
    (('Na2CO3 (р-р)', 'HCl (р-р)'), ['Fe (порошок)', 'CuO', 'Zn (гранулы)', 'Mg (стружка)', 'Fe2O3']),
]


def _pf(s):
    parts = s.split(' ', 1)
    return pretty(parts[0]) + (' ' + parts[1] if len(parts) > 1 else '')


@proto('ch-ege-18-compare', 'ЕГЭ', 18, 'Сравнение скоростей реакций (быстрее/медленнее эталонной, наибольшая скорость)',
       invariant='при одинаковых температуре и концентрации скорость выше у более активного металла, более сильной '
                 'кислоты, более измельчённого вещества; реакции ионного обмена в растворах идут быстрее гетерогенных',
       varies='эталон (металл + кислота, щелочной металл + спирт), варианты с другим металлом/кислотой/формой вещества, '
              'вопрос «быстрее» или «медленнее»; либо выбрать пару веществ, реагирующих быстрее всего',
       answer_rule='номера всех подходящих реакций (веществ), порядок не важен',
       mistakes=['не учитывают силу кислоты', 'не учитывают активность металла', 'считают гетерогенную реакцию быстрее '
                 'реакции в растворе'],
       solve=_solve_18_list, kes=['1.6'],
       fidelity=fid('последовательность цифр', 'как зад. 18 демоверсии 2027: «… выберите все реакции, которые при '
                    'одинаковых температуре и концентрации кислот протекают с большей скоростью, чем …»', 'Б', 3,
                    'металлы Mg, Zn, Fe; кислоты HCl, H₂SO₄, уксусная; спирты — как в банке', 'одновременно учитывать '
                    'металл, кислоту и степень измельчения', ['1.6'], '1 балл'))
def g18_compare(rng):
    mode = rng.choice(['metal', 'metal', 'alc', 'fastest'])
    if mode == 'fastest':
        (s1, s2), solids = pick(rng, PAIRS18)
        items = [s1, s2] + rng.sample(solids, 3)
        rng.shuffle(items)
        truth = [x in (s1, s2) for x in items]
        q = f'Из предложенного перечня выберите два вещества, которые при одинаковых условиях реагируют друг с другом ' \
            f'быстрее всего. {MANY_T}'
        a = [str(i + 1) for i, v in enumerate(truth) if v]
        e = f'Быстрее всего идут реакции ионного обмена между растворами: {_pf(s1)} и {_pf(s2)}. Ответ: {", ".join(a)}.'
        return pcard('ch-ege-18-compare', q, a, e, k='many', o=opts([_pf(x) for x in items]), p=dict(truth=truth))
    faster = rng.random() < 0.65
    if mode == 'metal':
        forms = rng.random() < 0.4
        ref = (pick(rng, METALS18), pick(rng, ACIDS18), pick(rng, FORMS18) if forms else (None, 0))
        txt = lambda m, a, fm: (f'{fm[2]} {m[1]}' if fm[0] else m[3]) + ' + ' + a[2]
        cands = []
        for m in METALS18:
            for ac in ACIDS18:
                for fm in (FORMS18 if forms else [(None, 0)]):
                    if (m, ac, fm) == ref:
                        continue
                    d = [m[2] - ref[0][2], ac[1] - ref[1][1], fm[1] - ref[2][1]]
                    if all(x >= 0 for x in d) and any(x > 0 for x in d):
                        cands.append((txt(m, ac, fm), faster))
                    elif all(x <= 0 for x in d) and any(x < 0 for x in d):
                        cands.append((txt(m, ac, fm), not faster))
        cands += [(t, faster) for t in FAST18]
        ref_t = txt(*ref)
        cond = 'одинаковой температуре и равной концентрации кислот'
    else:
        ref = (pick(rng, AMET18), pick(rng, ALC18[1:]))
        txt = lambda m, al: f'{m[2]} + {al[2]}'
        cands = []
        for m in AMET18:
            for al in ALC18:
                if (m, al) == ref:
                    continue
                d = [m[1] - ref[0][1], al[1] - ref[1][1]]
                if all(x >= 0 for x in d) and any(x > 0 for x in d):
                    cands.append((txt(m, al), faster))
                elif all(x <= 0 for x in d) and any(x < 0 for x in d):
                    cands.append((txt(m, al), not faster))
        ref_t = txt(*ref)
        cond = 'одной и той же температуре'
    uniq = {}
    for t, v in cands:
        uniq.setdefault(t, v)
    ch = _pick5(rng, list(uniq.items()), lambda x: x[1], 1, 4)
    truth = [v for _, v in ch]
    q = f'Из предложенного перечня выберите все реакции, которые при {cond} идут {"быстрее" if faster else "медленнее"}, ' \
        f'чем реакция «{ref_t}». {MANY_T}'
    a = [str(i + 1) for i, v in enumerate(truth) if v]
    e = ('Сравниваем активность металла, силу кислоты (спирта) и степень измельчения; реакции между растворами '
         f'(ионный обмен) идут быстрее гетерогенных. Ответ: {", ".join(a)}.')
    return pcard('ch-ege-18-compare', q, a, e, k='many', o=opts([t for t, _ in ch]), p=dict(truth=truth))


# ======================================================================= ЕГЭ 21. Среда растворов, pH

PH21 = [  # (формула, название, категория, ориентировочный pH 0,1 М раствора)
    ('HCl', 'хлороводородная кислота', 'acid', 1.0), ('HBr', 'бромоводородная кислота', 'acid', 1.0),
    ('HI', 'иодоводородная кислота', 'acid', 1.0), ('HNO3', 'азотная кислота', 'acid', 1.0),
    ('HClO4', 'хлорная кислота', 'acid', 1.0), ('H2SO4', 'серная кислота', 'acid', 1.0),
    ('H3PO4', 'фосфорная кислота', 'acid', 1.6), ('HF', 'фтороводородная кислота', 'acid', 2.1),
    ('CH3COOH', 'уксусная кислота', 'acid', 2.9), ('H2S', 'сероводородная кислота', 'acid', 4.0),
    ('FeCl3', 'хлорид железа(III)', 'cat', 2.0), ('Fe(NO3)3', 'нитрат железа(III)', 'cat', 2.0),
    ('AlCl3', 'хлорид алюминия', 'cat', 3.0), ('Al(NO3)3', 'нитрат алюминия', 'cat', 3.0),
    ('Al2(SO4)3', 'сульфат алюминия', 'cat', 3.0), ('CrCl3', 'хлорид хрома(III)', 'cat', 3.0),
    ('CuSO4', 'сульфат меди(II)', 'cat', 4.2), ('CuCl2', 'хлорид меди(II)', 'cat', 4.2),
    ('Cu(NO3)2', 'нитрат меди(II)', 'cat', 4.2), ('FeSO4', 'сульфат железа(II)', 'cat', 4.5),
    ('FeCl2', 'хлорид железа(II)', 'cat', 4.5), ('Pb(NO3)2', 'нитрат свинца(II)', 'cat', 4.5),
    ('ZnSO4', 'сульфат цинка', 'cat', 5.0), ('ZnCl2', 'хлорид цинка', 'cat', 5.0), ('Zn(NO3)2', 'нитрат цинка', 'cat', 5.0),
    ('NH4Cl', 'хлорид аммония', 'cat', 5.1), ('NH4NO3', 'нитрат аммония', 'cat', 5.1),
    ('(NH4)2SO4', 'сульфат аммония', 'cat', 5.0), ('NH4ClO4', 'перхлорат аммония', 'cat', 5.1),
    ('MgCl2', 'хлорид магния', 'cat', 6.0), ('Mg(NO3)2', 'нитрат магния', 'cat', 6.0),
    ('NaCl', 'хлорид натрия', 'neu', 7.0), ('KNO3', 'нитрат калия', 'neu', 7.0), ('Na2SO4', 'сульфат натрия', 'neu', 7.0),
    ('KBr', 'бромид калия', 'neu', 7.0), ('BaCl2', 'хлорид бария', 'neu', 7.0), ('Ba(NO3)2', 'нитрат бария', 'neu', 7.0),
    ('CaCl2', 'хлорид кальция', 'neu', 7.0), ('KClO3', 'хлорат калия', 'neu', 7.0), ('NaClO4', 'перхлорат натрия', 'neu', 7.0),
    ('NaNO3', 'нитрат натрия', 'neu', 7.0), ('K2SO4', 'сульфат калия', 'neu', 7.0), ('LiNO3', 'нитрат лития', 'neu', 7.0),
    ('CsCl', 'хлорид цезия', 'neu', 7.0), ('SrCl2', 'хлорид стронция', 'neu', 7.0), ('KI', 'иодид калия', 'neu', 7.0),
    ('CaBr2', 'бромид кальция', 'neu', 7.0), ('Ca(NO3)2', 'нитрат кальция', 'neu', 7.0),
    ('NaHCO3', 'гидрокарбонат натрия', 'an', 8.3), ('KHCO3', 'гидрокарбонат калия', 'an', 8.3),
    ('NaF', 'фторид натрия', 'an', 8.1), ('KF', 'фторид калия', 'an', 8.1),
    ('NaNO2', 'нитрит натрия', 'an', 8.2), ('KNO2', 'нитрит калия', 'an', 8.2), ('LiNO2', 'нитрит лития', 'an', 8.2),
    ('CH3COONa', 'ацетат натрия', 'an', 8.9), ('CH3COOK', 'ацетат калия', 'an', 8.9),
    ('(CH3COO)2Ca', 'ацетат кальция', 'an', 8.9), ('HCOONa', 'формиат натрия', 'an', 8.4),
    ('Na2SO3', 'сульфит натрия', 'an', 10.1), ('K2SO3', 'сульфит калия', 'an', 10.1),
    ('Na2CO3', 'карбонат натрия', 'an', 11.6), ('K2CO3', 'карбонат калия', 'an', 11.6),
    ('Na3PO4', 'фосфат натрия', 'an', 12.6), ('K3PO4', 'фосфат калия', 'an', 12.6),
    ('Na2S', 'сульфид натрия', 'an', 12.9), ('K2S', 'сульфид калия', 'an', 12.9),
    ('NH3·H2O', 'гидрат аммиака', 'base', 11.1), ('NaOH', 'гидроксид натрия', 'base', 13.0),
    ('KOH', 'гидроксид калия', 'base', 13.0), ('LiOH', 'гидроксид лития', 'base', 13.0),
    ('CsOH', 'гидроксид цезия', 'base', 13.0), ('RbOH', 'гидроксид рубидия', 'base', 13.0),
    ('Ba(OH)2', 'гидроксид бария', 'base', 13.3), ('Sr(OH)2', 'гидроксид стронция', 'base', 13.3),
]
CATS21 = ['acid', 'cat', 'neu', 'an', 'base']
PH21_BY = {f: row for f, *row in PH21}


def _solve_21_order(p):
    """Порядок по ориентировочному pH, пересчитанному по таблице (независимо от порядка генерации)."""
    vals = [PH21_BY[f][2] for f in p['shown']]
    idx = sorted(range(len(vals)), key=lambda i: vals[i], reverse=not p['asc'])
    return ''.join(str(i + 1) for i in idx)


def _g21_order(rng, pid, names):
    for _ in range(50):
        cats = sorted(rng.sample(range(5), 4))
        subs = [pick(rng, [r for r in PH21 if r[2] == CATS21[c]]) for c in cats]
        if all(subs[i + 1][3] - subs[i][3] >= 1.0 for i in range(3)):
            break
    else:
        raise Retry
    shown = subs[:]
    rng.shuffle(shown)
    asc = rng.random() < 0.7
    order = subs if asc else subs[::-1]
    ans = ''.join(str(shown.index(s) + 1) for s in order)
    lst = '\n'.join(f'{i + 1}) {s[1] if names else pretty(s[0])}' for i, s in enumerate(shown))
    q = (f'Растворы перечисленных веществ имеют одинаковую молярную концентрацию.\n{lst}\n'
         f'Определите среду каждого раствора и расположите вещества так, чтобы pH {"увеличивался" if asc else "уменьшался"}. '
         f'В ответ запишите номера веществ в получившейся последовательности.')
    e = ('Сильная кислота < соль слабого основания и сильной кислоты (гидролиз по катиону) < соль сильного основания '
         'и сильной кислоты (pH ≈ 7) < соль слабой кислоты и сильного основания (гидролиз по аниону) < щёлочь. '
         f'Ответ: {ans}.')
    return pcard(pid, q, ans, e, p=dict(shown=[s[0] for s in shown], asc=asc))


@proto('ch-ege-21-order', 'ЕГЭ', 21, 'Порядок возрастания (убывания) pH растворов: формулы веществ',
       invariant='кислота < соль с гидролизом по катиону < соль, не подвергающаяся гидролизу < соль с гидролизом по '
                 'аниону < щёлочь (при одинаковой молярной концентрации)',
       varies='четыре вещества из пяти групп (кислоты, соли разных типов, основания), возрастание или убывание',
       answer_rule='последовательность из четырёх цифр',
       mistakes=['соль сильного основания и слабой кислоты считают кислой', 'аммонийные соли — нейтральными',
                 'порядок убывания записан как возрастания'],
       solve=_solve_21_order, kes=['1.10'],
       fidelity=fid('последовательность 4 цифр, порядок важен', 'как зад. 21 демоверсии 2027: перечень из 4 формул, '
                    '«Запишите номера веществ в порядке возрастания значения pH…»', 'Б', 3,
                    'вещества банка: HCl, HBr, H₂SO₄, (NH₄)₂SO₄, CuSO₄, FeCl₃, KBr, Ba(NO₃)₂, Na₃PO₄, K₂CO₃, KOH, LiOH',
                    'гидролиз по катиону/аниону', ['1.10'], '1 балл'))
def g21_order(rng):
    return _g21_order(rng, 'ch-ege-21-order', False)


@proto('ch-ege-21-names', 'ЕГЭ', 21, 'Порядок изменения pH растворов: вещества заданы названиями',
       invariant='то же правило, но вещество нужно сначала узнать по названию (перхлорат, гидрокарбонат, гидрат аммиака …)',
       varies='четыре названия веществ разных групп, возрастание или убывание',
       answer_rule='последовательность из четырёх цифр',
       mistakes=['не узнали соль по названию (перхлорат, хлорат — соли сильных кислот)', 'гидрат аммиака приняли за соль'],
       solve=_solve_21_order, kes=['1.10'],
       fidelity=fid('последовательность 4 цифр', 'как в банке: «1) перманганат натрия 2) иодид железа(II) …»', 'Б', 3,
                    'названия того же круга, что в банке', 'распознать класс по названию', ['1.10'], '1 балл'))
def g21_names(rng):
    return _g21_order(rng, 'ch-ege-21-names', True)


MED21 = {'acid': '1', 'cat': '1', 'neu': '2', 'an': '3'}
HYD21 = [('CH3COONH4', 'ацетат аммония', 'both'), ('(NH4)2CO3', 'карбонат аммония', 'both'),
         ('(NH4)2S', 'сульфид аммония', 'both'), ('(NH4)2SO3', 'сульфит аммония', 'both'), ('NH4F', 'фторид аммония', 'both')]


def _solve_21_match(p):
    return dict(p['ans'])


@proto('ch-ege-21-medium', 'ЕГЭ', 21, 'Соответствие «соль — среда раствора» / «соль — отношение к гидролизу»',
       invariant='тип гидролиза определяется силой основания и кислоты, образующих соль; по катиону — кислая среда, '
                 'по аниону — щелочная, не гидролизуется — нейтральная',
       varies='четыре соли (формулы или названия), вопрос о среде или о типе гидролиза',
       answer_rule='цифры под буквами А–Г',
       mistakes=['гидролиз по катиону и аниону путают с отсутствием гидролиза', 'соли аммония считают нейтральными'],
       solve=_solve_21_match, kes=['1.10'],
       fidelity=fid('4 цифры под буквами, цифры могут повторяться', 'как в открытом банке (КЭС 1.10, соответствие): '
                    '«Установите соответствие между формулой (названием) соли и средой её водного раствора»; в КИМ 2027 '
                    '№ 21 — последовательность, этот тип остаётся в банке и нужен для тренировки', 'Б', 3,
                    'соли банка', 'по катиону/аниону/обоим', ['1.10'], '1 балл'))
def g21_medium(rng):
    names = rng.random() < 0.5
    if rng.random() < 0.5:
        rows = rng.sample([r for r in PH21 if r[2] in ('cat', 'neu', 'an') and r[0] not in ('NH3·H2O',)], 4)
        left = [r[1] if names else pretty(r[0]) for r in rows]
        right = ['кислая', 'нейтральная', 'щелочная']
        ans = {'АБВГ'[i]: MED21[r[2]] for i, r in enumerate(rows)}
        q = f'Установите соответствие между {"названием" if names else "формулой"} соли и характером среды, которую имеет ' \
            f'её водный раствор: {MATCH_I} {MATCH_T}'
        e = 'Гидролиз по катиону — кислая среда, по аниону — щелочная, соль сильных основания и кислоты — нейтральная.'
    else:
        pool = [r for r in PH21 if r[2] in ('cat', 'neu', 'an')] + [(f, n, 'both', 7.0) for f, n, _ in HYD21]
        rows = rng.sample(pool, 4)
        if not any(r[2] == 'both' for r in rows) and rng.random() < 0.6:
            rows[rng.randrange(4)] = pick(rng, [(f, n, 'both', 7.0) for f, n, _ in HYD21])
            if len({r[0] for r in rows}) < 4:
                raise Retry
        left = [r[1] if names else pretty(r[0]) for r in rows]
        right = ['гидролиз идёт по катиону', 'гидролиз идёт по аниону', 'гидролиз идёт и по катиону, и по аниону',
                 'соль гидролизу не подвергается']
        code = {'cat': '1', 'an': '2', 'both': '3', 'neu': '4'}
        ans = {'АБВГ'[i]: code[r[2]] for i, r in enumerate(rows)}
        q = f'Установите соответствие между {"названием" if names else "формулой"} соли и тем, как эта соль ведёт себя при '\
            f'растворении в воде: {MATCH_I} {MATCH_T}'
        e = 'Слабое основание → гидролиз по катиону, слабая кислота → по аниону; оба слабых → по катиону и аниону.'
    e += ' Ответ: ' + ''.join(ans[x] for x in 'АБВГ') + '.'
    return pcard('ch-ege-21-medium', q, ans, e, k='match', o=match_opts(left, right), p=dict(ans=ans))


# ======================================================================= ЕГЭ 22. Смещение равновесия

SH = ['сместится в направлении прямой реакции', 'сместится в направлении обратной реакции',
      'положение равновесия практически не изменится']
NAME22 = {'N2': 'азота', 'H2': 'водорода', 'NH3': 'аммиака', 'SO2': 'оксида серы(IV)', 'O2': 'кислорода',
          'SO3': 'оксида серы(VI)', 'NO': 'оксида азота(II)', 'I2': 'паров иода', 'HI': 'иодоводорода',
          'CO': 'угарного газа', 'H2O': 'паров воды', 'CO2': 'углекислого газа', 'NO2': 'оксида азота(IV)',
          'N2O4': 'оксида азота(IV) (димера)', 'CH4': 'метана', 'PCl5': 'хлорида фосфора(V)', 'PCl3': 'хлорида фосфора(III)',
          'Cl2': 'хлора', 'COCl2': 'фосгена', 'CH3OH': 'паров метанола', 'HCl': 'хлороводорода', 'C2H4': 'этилена',
          'C2H6': 'этана', 'C2H5OH': 'паров этанола', 'Br2': 'паров брома', 'HBr': 'бромоводорода',
          'SO2Cl2': 'сульфурилхлорида', 'NOCl': 'нитрозилхлорида', 'H2S': 'сероводорода', 'C': 'угля',
          'CaCO3': 'карбоната кальция', 'CaO': 'оксида кальция', 'FeO': 'оксида железа(II)', 'Fe': 'железа',
          'Fe3O4': 'железной окалины', 'NH4Cl': 'хлорида аммония', 'S': 'серы', 'MgCO3': 'карбоната магния',
          'MgO': 'оксида магния'}

EQ22 = [  # (lhs [(ф, фаза)], rhs, знак Q: +1 экзо, −1 эндо)
    ([('N2', 'г'), ('H2', 'г')], [('NH3', 'г')], 1), ([('SO2', 'г'), ('O2', 'г')], [('SO3', 'г')], 1),
    ([('N2', 'г'), ('O2', 'г')], [('NO', 'г')], -1), ([('H2', 'г'), ('I2', 'г')], [('HI', 'г')], 1),
    ([('CO', 'г'), ('H2O', 'г')], [('CO2', 'г'), ('H2', 'г')], 1), ([('CO2', 'г'), ('H2', 'г')], [('CO', 'г'), ('H2O', 'г')], -1),
    ([('NO2', 'г')], [('N2O4', 'г')], 1), ([('N2O4', 'г')], [('NO2', 'г')], -1),
    ([('CH4', 'г'), ('H2O', 'г')], [('CO', 'г'), ('H2', 'г')], -1), ([('NO', 'г'), ('O2', 'г')], [('NO2', 'г')], 1),
    ([('PCl5', 'г')], [('PCl3', 'г'), ('Cl2', 'г')], -1), ([('CO', 'г'), ('Cl2', 'г')], [('COCl2', 'г')], 1),
    ([('COCl2', 'г')], [('CO', 'г'), ('Cl2', 'г')], -1), ([('CO', 'г'), ('H2', 'г')], [('CH3OH', 'г')], 1),
    ([('CH3OH', 'г')], [('CO', 'г'), ('H2', 'г')], -1), ([('HCl', 'г'), ('O2', 'г')], [('Cl2', 'г'), ('H2O', 'г')], 1),
    ([('C2H4', 'г'), ('H2', 'г')], [('C2H6', 'г')], 1), ([('C2H6', 'г')], [('C2H4', 'г'), ('H2', 'г')], -1),
    ([('C2H4', 'г'), ('H2O', 'г')], [('C2H5OH', 'г')], 1), ([('H2', 'г'), ('Br2', 'г')], [('HBr', 'г')], 1),
    ([('HI', 'г')], [('H2', 'г'), ('I2', 'г')], -1), ([('SO2', 'г'), ('Cl2', 'г')], [('SO2Cl2', 'г')], 1),
    ([('SO3', 'г')], [('SO2', 'г'), ('O2', 'г')], -1), ([('NO', 'г'), ('Cl2', 'г')], [('NOCl', 'г')], 1),
]
EQ22H = [  # гетерогенные
    ([('CaCO3', 'тв')], [('CaO', 'тв'), ('CO2', 'г')], -1), ([('C', 'тв'), ('CO2', 'г')], [('CO', 'г')], -1),
    ([('C', 'тв'), ('H2O', 'г')], [('CO', 'г'), ('H2', 'г')], -1), ([('C', 'тв'), ('H2', 'г')], [('CH4', 'г')], 1),
    ([('FeO', 'тв'), ('CO', 'г')], [('Fe', 'тв'), ('CO2', 'г')], 1),
    ([('Fe3O4', 'тв'), ('H2', 'г')], [('Fe', 'тв'), ('H2O', 'г')], -1),
    ([('NH4Cl', 'тв')], [('NH3', 'г'), ('HCl', 'г')], -1), ([('S', 'тв'), ('H2', 'г')], [('H2S', 'г')], 1),
    ([('MgCO3', 'тв')], [('MgO', 'тв'), ('CO2', 'г')], -1), ([('Fe', 'тв'), ('H2O', 'г')], [('Fe3O4', 'тв'), ('H2', 'г')], 1),
]
PHS = {'г': '(г)', 'тв': '(тв.)'}


def _eq22(lhs, rhs, qs):
    L, R = [f for f, _ in lhs], [f for f, _ in rhs]
    kl, kr = balance(L, R)
    side = lambda ss, ks: ' + '.join((str(k) if k > 1 else '') + pretty(f) + PHS[ph] for (f, ph), k in zip(ss, ks))
    s = side(lhs, kl) + ' ⇄ ' + side(rhs, kr) + (' + Q' if qs > 0 else ' − Q')
    dn = sum(k for (f, ph), k in zip(rhs, kr) if ph == 'г') - sum(k for (f, ph), k in zip(lhs, kl) if ph == 'г')
    return s, dn, (L, R, kl, kr)


def _shift(factor, qs, dn, side_of, phase_of):
    kind, arg = factor
    if kind == 'T':
        return '2' if (arg == 'up') == (qs > 0) else '1'
    if kind == 'p':
        if dn == 0:
            return '3'
        return '1' if (dn < 0) == (arg == 'up') else '2'
    if kind == 'cat':
        return '3'
    f, how = arg
    if phase_of[f] == 'тв':
        return '3'
    return '1' if (side_of[f] == 'L') == (how == 'add') else '2'


def _ftext(factor):
    kind, arg = factor
    if kind == 'T':
        return 'повышение температуры' if arg == 'up' else rng_free_choice('понижение температуры')
    if kind == 'p':
        return 'повышение давления' if arg == 'up' else 'понижение давления'
    if kind == 'cat':
        return 'добавление катализатора'
    f, how = arg
    nm = NAME22.get(f, pretty(f))
    if how in ('add', 'rem') and f in ('C', 'CaCO3', 'CaO', 'FeO', 'Fe', 'Fe3O4', 'NH4Cl', 'S', 'MgCO3', 'MgO'):
        return ('добавление ' if how == 'add' else 'удаление части ') + nm
    return ('увеличение концентрации ' if how == 'add' else 'уменьшение концентрации ') + nm


def rng_free_choice(s):
    return s


def _solve_22(p):
    side_of = {f: s for f, s in p['side'].items()}
    phase_of = dict(p['phase'])
    return {k: _shift(tuple(v) if v[0] != 'c' else ('c', tuple(v[1])), p['qs'], p['dn'], side_of, phase_of)
            for k, v in p['factors'].items()}


def _g22_sys(rng, pid, pool, what):
    lhs, rhs, qs = pick(rng, pool)
    eq, dn, eqt = _eq22(lhs, rhs, qs)
    side_of = {f: 'L' for f, _ in lhs}
    side_of.update({f: 'R' for f, _ in rhs})
    phase_of = {f: ph for f, ph in lhs + rhs}
    factors = [('T', 'up'), ('T', 'down'), ('p', 'up'), ('p', 'down'), ('cat', None)]
    for f, ph in lhs + rhs:
        factors += [('c', (f, 'add')), ('c', (f, 'rem'))]
    for _ in range(30):
        pick4 = rng.sample(factors, 4)
        kinds = [x[0] for x in pick4]
        if kinds.count('T') > 1 or kinds.count('p') > 1:
            continue
        if what == 'hetero' and not any(x[0] == 'c' and phase_of[x[1][0]] == 'тв' for x in pick4) and rng.random() < 0.7:
            continue
        ans = {'АБВГ'[i]: _shift(f, qs, dn, side_of, phase_of) for i, f in enumerate(pick4)}
        if len(set(ans.values())) >= 2:
            break
    else:
        raise Retry
    left = [_ftext(f) for f in pick4]
    q = f'В системе установилось равновесие\n{eq}\nУстановите соответствие между воздействием на эту систему и тем, как '\
        f'изменится положение равновесия: {MATCH_I} {MATCH_T}'
    e = (f'Принцип Ле Шателье: реакция {"экзо" if qs > 0 else "эндо"}термическая, изменение числа моль газов Δn = {dn:+d}; '
         'катализатор и твёрдые вещества равновесие не смещают. Ответ: ' + ''.join(ans[x] for x in 'АБВГ') + '.').replace('+0', '0')
    p = dict(qs=qs, dn=dn, side=side_of, phase=phase_of,
             factors={'АБВГ'[i]: [f[0], list(f[1]) if f[0] == 'c' else f[1]] for i, f in enumerate(pick4)})
    return pcard(pid, q, ans, e, k='match', o=match_opts(left, SH), p=p, eq=eqt)


@proto('ch-ege-22-gas', 'ЕГЭ', 22, 'Смещение равновесия в газовой системе при разных воздействиях',
       invariant='принцип Ле Шателье: нагревание — в сторону эндотермической реакции; давление — в сторону меньшего числа '
                 'моль газов (при Δn = 0 не смещается); добавление вещества — в сторону его расхода; катализатор не смещает',
       varies='равновесие (синтез аммиака, SO₃, NO, HI, метанола, конверсия CO, диссоциация N₂O₄, PCl₅ …), знак Q, '
              'четыре воздействия',
       answer_rule='цифры 1–3 под буквами А–Г',
       mistakes=['катализатор смещает равновесие', 'давление при Δn = 0 смещает', 'путают знак теплового эффекта'],
       solve=_solve_22, kes=['1.8'],
       fidelity=fid('4 цифры под буквами А–Г (1, 2, 3)', 'как зад. 22 демоверсии 2027 и банка: «Установите соответствие '
                    'между способом воздействия на равновесную систему … и смещением химического равновесия»', 'П', 5,
                    'равновесия банка (N₂ + H₂, CO + Cl₂, CH₄ + H₂O …)', 'катализатор; Δn = 0', ['1.8'],
                    '2 балла, 1 балл при одной ошибке'))
def g22_gas(rng):
    return _g22_sys(rng, 'ch-ege-22-gas', EQ22, 'gas')


@proto('ch-ege-22-hetero', 'ЕГЭ', 22, 'Смещение гетерогенного равновесия (с твёрдыми веществами)',
       invariant='твёрдые вещества не входят в выражение для смещения: их добавление/удаление не смещает равновесие; '
                 'давление учитывает только газы',
       varies='равновесие (разложение карбонатов, C + CO₂, C + H₂O, FeO + CO, NH₄Cl ⇄ NH₃ + HCl …), воздействия',
       answer_rule='цифры 1–3 под буквами А–Г',
       mistakes=['добавление твёрдого реагента смещает равновесие', 'в Δn включают твёрдые вещества'],
       solve=_solve_22, kes=['1.8'],
       fidelity=fid('4 цифры 1–3', 'КИМ-стиль (в банке: C(тв.) + 2H₂(г) ⇄ CH₄(г) + Q)', 'П', 5, 'как в банке',
                    'твёрдые вещества не смещают равновесие', ['1.8'], '2 балла, 1 балл при одной ошибке'))
def g22_hetero(rng):
    return _g22_sys(rng, 'ch-ege-22-hetero', EQ22H, 'hetero')


ION22 = [  # (запись, [(воздействие, ответ)], атомы/заряды не проверяются кодом — ионные записи сверены вручную)
    ('CH₃COOH(р-р) ⇄ CH₃COO⁻(р-р) + H⁺(р-р) − Q',
     [('добавление твёрдого ацетата натрия', '2'), ('добавление соляной кислоты', '2'), ('добавление твёрдой щёлочи', '1'),
      ('разбавление раствора водой', '1'), ('повышение температуры', '1'), ('понижение температуры', '2'),
      ('повышение давления', '3')]),
    ('HNO₂(р-р) ⇄ H⁺(р-р) + NO₂⁻(р-р) − Q',
     [('добавление твёрдого нитрита калия', '2'), ('добавление азотной кислоты', '2'), ('добавление твёрдой щёлочи', '1'),
      ('повышение температуры', '1'), ('понижение температуры', '2'), ('понижение давления', '3'),
      ('разбавление раствора водой', '1')]),
    ('CH₃NH₂(р-р) + H₂O(ж) ⇄ CH₃NH₃⁺(р-р) + OH⁻(р-р) − Q',
     [('добавление хлорида метиламмония', '2'), ('добавление соляной кислоты', '1'), ('добавление твёрдой щёлочи', '2'),
      ('повышение температуры', '1'), ('понижение температуры', '2'), ('понижение давления', '3')]),
    ('Zn²⁺(р-р) + 4OH⁻(р-р) ⇄ [Zn(OH)₄]²⁻(р-р) + Q',
     [('добавление твёрдого хлорида цинка', '1'), ('добавление твёрдой щёлочи', '1'), ('добавление хлорной кислоты', '2'),
      ('повышение давления', '3'), ('понижение температуры', '1'), ('повышение температуры', '2')]),
    ('Cr₂O₇²⁻(р-р) + H₂O(ж) ⇄ 2CrO₄²⁻(р-р) + 2H⁺(р-р)',
     [('добавление твёрдой щёлочи', '1'), ('добавление серной кислоты', '2'), ('добавление твёрдого хромата калия', '2'),
      ('добавление твёрдого дихромата калия', '1'), ('повышение давления', '3')]),
    ('Fe³⁺(р-р) + 3SCN⁻(р-р) ⇄ Fe(SCN)₃(р-р) + Q',
     [('добавление твёрдого роданида калия', '1'), ('добавление раствора хлорида железа(III)', '1'),
      ('добавление раствора гидроксида натрия', '2'), ('повышение давления', '3'), ('повышение температуры', '2'),
      ('понижение температуры', '1')]),
    ('Pb²⁺(р-р) + 2I⁻(р-р) ⇄ PbI₂(тв.) + Q',
     [('добавление твёрдого иодида калия', '1'), ('добавление раствора нитрата свинца(II)', '1'),
      ('добавление твёрдого иодида свинца(II)', '3'), ('повышение давления', '3'), ('повышение температуры', '2'),
      ('понижение температуры', '1')]),
    ('CO₃²⁻(р-р) + H₂O(ж) ⇄ HCO₃⁻(р-р) + OH⁻(р-р) − Q',
     [('добавление твёрдой щёлочи', '2'), ('добавление соляной кислоты', '1'), ('повышение температуры', '1'),
      ('добавление твёрдого карбоната натрия', '1'), ('понижение температуры', '2'), ('повышение давления', '3')]),
    ('NH₄⁺(р-р) + H₂O(ж) ⇄ NH₃·H₂O(р-р) + H⁺(р-р) − Q',
     [('добавление азотной кислоты', '2'), ('добавление твёрдой щёлочи', '1'), ('повышение температуры', '1'),
      ('добавление твёрдого хлорида аммония', '1'), ('понижение температуры', '2'), ('понижение давления', '3')]),
    ('Ag⁺(р-р) + Cl⁻(р-р) ⇄ AgCl(тв.) + Q',
     [('добавление твёрдого хлорида натрия', '1'), ('добавление раствора нитрата серебра', '1'),
      ('добавление раствора аммиака', '2'), ('повышение давления', '3'), ('понижение температуры', '1'),
      ('добавление твёрдого хлорида серебра', '3')]),
    ('HPO₄²⁻(р-р) ⇄ H⁺(р-р) + PO₄³⁻(р-р) − Q',
     [('добавление твёрдого фосфата калия', '2'), ('добавление соляной кислоты', '2'), ('добавление твёрдого гидроксида калия', '1'),
      ('повышение температуры', '1'), ('понижение температуры', '2'), ('повышение давления', '3')]),
    ('HCOOH(р-р) ⇄ HCOO⁻(р-р) + H⁺(р-р) − Q',
     [('добавление твёрдого формиата натрия', '2'), ('добавление азотной кислоты', '2'), ('добавление твёрдой щёлочи', '1'),
      ('повышение температуры', '1'), ('понижение давления', '3'), ('разбавление раствора водой', '1')]),
]


def _solve_22_ion(p):
    table = dict(ION22)
    tab = dict(table[p['eq']])
    return {k: tab[t] for k, t in p['factors'].items()}


@proto('ch-ege-22-ionic', 'ЕГЭ', 22, 'Смещение ионного равновесия в растворе',
       invariant='в растворе давление не смещает равновесие; добавление иона-участника смещает в сторону его расхода; '
                 'связывание иона (H⁺ щёлочью, OH⁻ кислотой, Ag⁺ аммиаком, Fe³⁺ щёлочью) — в сторону его образования; '
                 'разбавление смещает диссоциацию слабого электролита вправо',
       varies='равновесие (диссоциация слабых кислот и оснований, гидролиз, комплексообразование, осаждение, '
              'хромат-дихромат), четыре воздействия',
       answer_rule='цифры 1–3 под буквами А–Г',
       mistakes=['давление смещает равновесие в растворе', 'щёлочь «добавляет» OH⁻, но забывают, что она связывает H⁺',
                 'добавление твёрдого осадка смещает равновесие'],
       solve=_solve_22_ion, kes=['1.8'],
       fidelity=fid('4 цифры 1–3', 'как зад. 22 демоверсии 2027 (Zn²⁺ + 4OH⁻ ⇄ [Zn(OH)₄]²⁻ + Q)', 'П', 5,
                    'равновесия банка (HNO₂, HCOOH, CH₃NH₂, [Zn(OH)₄]²⁻, PbI₂, HPO₄²⁻)', 'связывание ионов; давление в '
                    'растворе', ['1.8'], '2 балла, 1 балл при одной ошибке'))
def g22_ionic(rng):
    eq, facts = pick(rng, ION22)
    if 'Q' not in eq:
        facts = [f for f in facts if 'температур' not in f[0]]
    for _ in range(20):
        ch = rng.sample(facts, 4)
        if sum('температур' in t for t, _ in ch) <= 1 and len({a for _, a in ch}) >= 2:
            break
    else:
        raise Retry
    ans = {'АБВГ'[i]: a for i, (t, a) in enumerate(ch)}
    q = f'В растворе установилось равновесие\n{eq}\nУстановите соответствие между воздействием на этот раствор и тем, '\
        f'куда сместится равновесие: {MATCH_I} {MATCH_T}'
    e = 'Равновесие смещается в сторону расходования добавленного иона и в сторону образования иона, который связывают; ' \
        'давление на равновесие в растворе практически не влияет. Ответ: ' + ''.join(ans[x] for x in 'АБВГ') + '.'
    return pcard('ch-ege-22-ionic', q, ans, e, k='match', o=match_opts([t for t, _ in ch], SH),
                 p=dict(eq=eq, factors={'АБВГ'[i]: t for i, (t, _) in enumerate(ch)}))


def _solve_22_list(p):
    out = {}
    for k, (qs, dn, side, phase) in p['rows'].items():
        out[k] = _shift(tuple(p['factor']) if p['factor'][0] != 'c' else ('c', tuple(p['factor'][1])), qs, dn, side, phase)
    return out


@proto('ch-ege-22-eqlist', 'ЕГЭ', 22, 'Направление смещения для нескольких равновесий при одном воздействии',
       invariant='для каждого уравнения отдельно: знак Q (температура), Δn газов (давление), сторона вещества (концентрация)',
       varies='воздействие (нагревание, охлаждение, повышение/понижение давления, увеличение концентрации водорода), '
              'четыре уравнения',
       answer_rule='цифры 1–3 под буквами А–Г',
       mistakes=['не учли твёрдые вещества при подсчёте Δn', 'водород в правой части — равновесие смещают вправо'],
       solve=_solve_22_list, kes=['1.8'],
       fidelity=fid('4 цифры 1–3', 'как в банке: «Установите соответствие между уравнением химической реакции и '
                    'направлением смещения химического равновесия при понижении давления в системе»', 'П', 5,
                    'уравнения банка', 'Δn = 0; сторона вещества', ['1.8'], '2 балла, 1 балл при одной ошибке'))
def g22_eqlist(rng):
    factor = pick(rng, [('T', 'up'), ('T', 'down'), ('p', 'up'), ('p', 'down'), ('c', ('H2', 'add'))])
    pool = EQ22 + EQ22H
    if factor[0] == 'c':
        pool = [x for x in pool if any(f == 'H2' for f, _ in x[0] + x[1])]
    rows, texts, eqs = {}, [], []
    ch = rng.sample(pool, 4)
    ans = {}
    for i, (lhs, rhs, qs) in enumerate(ch):
        eq, dn, eqt = _eq22(lhs, rhs, qs)
        side_of = {f: 'L' for f, _ in lhs}
        side_of.update({f: 'R' for f, _ in rhs})
        phase_of = {f: ph for f, ph in lhs + rhs}
        rows['АБВГ'[i]] = [qs, dn, side_of, phase_of]
        ans['АБВГ'[i]] = _shift(factor, qs, dn, side_of, phase_of)
        texts.append(eq)
        eqs.append(eqt)
    if len(set(ans.values())) < 2:
        raise Retry
    ftxt = {('T', 'up'): 'при повышении температуры', ('T', 'down'): 'при понижении температуры',
            ('p', 'up'): 'при повышении давления', ('p', 'down'): 'при понижении давления'}.get(factor, 'при увеличении '
                                                                                                    'концентрации водорода')
    q = f'Установите соответствие между обратимой реакцией и тем, куда сместится её равновесие {ftxt}: {MATCH_I} {MATCH_T}'
    e = 'Для каждого уравнения: знак Q, Δn газов, сторона, в которой находится вещество. Ответ: ' + \
        ''.join(ans[x] for x in 'АБВГ') + '.'
    fp = [factor[0], list(factor[1]) if factor[0] == 'c' else factor[1]]
    return pcard('ch-ege-22-eqlist', q, ans, e, k='match', o=match_opts(texts, SH), p=dict(rows=rows, factor=fp), eqs=eqs)


# ======================================================================= ЕГЭ 23. Равновесные концентрации

EQ23 = [  # (lhs, rhs) — формулы; все газы; коэффициенты — balance()
    (['CO2', 'H2'], ['CH4', 'H2O']), (['HCl', 'O2'], ['H2O', 'Cl2']), (['CO', 'H2'], ['CH4', 'H2O']),
    (['CO', 'H2'], ['CH3OCH3', 'H2O']), (['NO2'], ['NO', 'O2']), (['CH3OH', 'HCl'], ['CH3Cl', 'H2O']),
    (['NO2', 'Cl2'], ['NO2Cl']), (['H2', 'I2'], ['HI']), (['CO', 'Cl2'], ['COCl2']), (['SO2', 'O2'], ['SO3']),
    (['N2H4', 'H2'], ['NH3']), (['NO', 'O2'], ['NO2']), (['CH4', 'O2'], ['CO', 'H2']), (['BrCl'], ['Br2', 'Cl2']),
    (['NH3'], ['N2', 'H2']), (['Cl2', 'H2O'], ['HCl', 'O2']), (['C2H2', 'H2'], ['C2H6']), (['H2', 'Br2'], ['HBr']),
    (['NO', 'Cl2'], ['NOCl']), (['SO3'], ['SO2', 'O2']), (['C6H12'], ['C6H6', 'H2']), (['CO2'], ['CO', 'O2']),
    (['N2', 'O2'], ['NO']), (['CH4', 'H2O'], ['CO', 'H2']), (['N2O', 'H2'], ['NH3', 'H2O']), (['N2', 'H2'], ['NH3']),
    (['Br2', 'Cl2'], ['BrCl']), (['PCl5'], ['PCl3', 'Cl2']), (['C2H6'], ['C2H4', 'H2']), (['C2H4', 'H2O'], ['C2H5OH']),
    (['CO', 'H2'], ['CH3OH']), (['H2S'], ['H2', 'S2']), (['COCl2'], ['CO', 'Cl2']), (['HI'], ['H2', 'I2']),
]
LET23 = [(['A', 'B'], ['C'], [1, 2], [1]), (['A'], ['B', 'C'], [1], [1, 3]), (['A'], ['B', 'C'], [2], [1, 1]),
         (['A', 'B'], ['C'], [1, 1], [2]), (['A', 'B'], ['C'], [3, 1], [2]), (['A', 'B'], ['C', 'D'], [2, 1], [2, 1]),
         (['A', 'B'], ['C'], [2, 1], [2])]


def _fmt23(v, d):
    return f'{float(v):.{d}f}'.replace('.', ',')


def _solve_23(p):
    k = dict(zip(p['sp'], p['k']))
    known = {tuple(x[:2]): Fr(x[2]) for x in p['known']}
    # найти x (изменение на единицу коэффициента) по любому веществу, для которого известно достаточно
    x = None
    for (s, kind), v in known.items():
        if kind == 'eq' and s in p['prod']:
            x = v / k[s]
        if kind == 'eq' and (s, 'c0') in known:
            x = abs(known[(s, 'c0')] - v) / k[s]
        if x is not None:
            break
    out = {}
    for key, (s, kind) in zip(('X', 'Y'), p['ask']):
        if s in p['prod']:
            val = x * k[s] if kind == 'eq' else Fr(0)
        elif kind == 'eq':
            val = known[(s, 'c0')] - x * k[s]
        else:
            val = known[(s, 'eq')] + x * k[s]
        out[key] = str(p['opts'].index(str(val)) + 1)
    return out


def _g23(rng, pid, table, letters=False):
    if letters:
        lhs, rhs, kl, kr = pick(rng, LET23)
    else:
        lhs, rhs = pick(rng, EQ23)
        kl, kr = balance(lhs, rhs)
    sp = lhs + rhs
    k = dict(zip(sp, kl + kr))
    step = pick(rng, [Fr(1, 10), Fr(1, 10), Fr(1, 20), Fr(1, 50), Fr(2, 10)])
    x = step * rng.randint(1, 4)
    c0 = {s: k[s] * x + step * rng.randint(1, 8) for s in lhs}
    ceq = {s: c0[s] - k[s] * x for s in lhs}
    ceq.update({s: k[s] * x for s in rhs})
    # что показать: исходные концентрации части реагентов + равновесные двух веществ; спросить X, Y
    cells = [(s, 'c0') for s in lhs] + [(s, 'eq') for s in sp]
    for _ in range(60):
        ask = rng.sample(cells, 2)
        rest = [c for c in cells if c not in ask]
        known = rng.sample(rest, rng.randint(2, min(3, len(rest))))
        kn = set(known)
        # x определяется: равновесная концентрация продукта или (c0, eq) одного реагента
        ok_x = any(c[1] == 'eq' and c[0] in rhs for c in kn) or any((s, 'c0') in kn and (s, 'eq') in kn for s in lhs)
        ok_ask = all(a[0] in rhs or ((a[0], 'eq') in kn if a[1] == 'c0' else (a[0], 'c0') in kn) for a in ask)
        if ok_x and ok_ask:
            break
    else:
        raise Retry
    val = lambda c: c0[c[0]] if c[1] == 'c0' else ceq[c[0]]
    right = [val(a) for a in ask]
    if any(v <= 0 for v in right) or any(val(c) <= 0 for c in known):
        raise Retry
    # 6 вариантов: верные + типичные ошибки + соседние значения с тем же шагом
    pool = set(right)
    errs = [x, k[ask[0][0]] * x * 2, val(ask[0]) + step, val(ask[1]) - step, x * 3, val(ask[1]) + 2 * step,
            val(ask[0]) - 2 * step]
    for v in errs:
        if len(pool) >= 6:
            break
        if v > 0:
            pool.add(v)
    i = 1
    while len(pool) < 6:
        pool.add(step * i)
        i += 1
    pool = sorted(pool)[:6] if len(pool) > 6 else sorted(pool)
    if not all(v in pool for v in right):
        pool = sorted(set(right) | set(sorted(pool)[:6 - len(set(right))]))
    d = 2 if any(not nice(v, 1) for v in pool) else 1
    strs = [str(v) for v in pool]
    shown = lambda s: pretty(s)
    L = 'в реактор постоянного объёма'
    kind_w = {'c0': 'исходную', 'eq': 'равновесную'}
    ask_txt = f'{kind_w[ask[0][1]]} концентрацию {shown(ask[0][0])} (X) и {kind_w[ask[1][1]]} концентрацию {shown(ask[1][0])} (Y)'
    kstr = lambda kk: '' if kk == 1 else str(kk)
    eqs = ' + '.join(kstr(k[s]) + shown(s) + '(г)' for s in lhs) + ' ⇄ ' + ' + '.join(kstr(k[s]) + shown(s) + '(г)' for s in rhs)
    start = ' и '.join(shown(s) for s in lhs)
    if table:
        head = 'Вещество | ' + ' | '.join(shown(s) for s in sp)
        r0 = 'Исходная концентрация, моль/л | ' + ' | '.join(_fmt23(c0[s], d) if (s, 'c0') in known else '' for s in sp)
        r1 = 'Равновесная концентрация, моль/л | ' + ' | '.join(_fmt23(ceq[s], d) if (s, 'eq') in known else '' for s in sp)
        q = (f'В реакторе постоянного объёма смешали {start}. Между ними протекает обратимая реакция\n{eqs}\n'
             f'После установления равновесия известны данные, приведённые в таблице.\n{head}\n{r0}\n{r1}\n'
             f'Определите {ask_txt}.') if len(lhs) > 1 else (
             f'В реактор постоянного объёма ввели {start} и нагрели. Протекает обратимая реакция\n{eqs}\n'
             f'Воспользуйтесь данными таблицы.\n{head}\n{r0}\n{r1}\nОпределите {ask_txt}.')
    else:
        parts0 = [f'{shown(s)} — {_fmt23(c0[s], d)} моль/л' for s in lhs if (s, 'c0') in known]
        parts1 = [f'{shown(s)} — {_fmt23(ceq[s], d)} моль/л' for s in sp if (s, 'eq') in known]
        q = f'{"Смесь " + start if len(lhs) > 1 else cap(start)} поместили {L}' \
            + (f' (исходные концентрации: {"; ".join(parts0)})' if parts0 else '') + \
            f'. В системе протекает обратимая реакция\n{eqs}\nПосле установления равновесия концентрации составили: ' \
            f'{"; ".join(parts1)}. Определите {ask_txt}.'
    q += ' Выберите из списка номера правильных ответов. Запишите выбранные номера в таблицу под соответствующими буквами.'
    o = match_opts(['X', 'Y'], [f'{_fmt23(v, d)} моль/л' for v in pool], lids='XY')
    ans = {'X': str(pool.index(right[0]) + 1), 'Y': str(pool.index(right[1]) + 1)}
    e = (f'Изменения концентраций пропорциональны коэффициентам; на единицу коэффициента приходится '
         f'{_fmt23(x, d)} моль/л. X = {_fmt23(right[0], d)}, Y = {_fmt23(right[1], d)} моль/л. Ответ: {ans["X"]}{ans["Y"]}.')
    p = dict(sp=sp, k=[k[s] for s in sp], prod=rhs, ask=[list(a) for a in ask],
             known=[[c[0], c[1], str(val(c))] for c in known], opts=strs)
    eqt = None if letters else (lhs, rhs, kl, kr)
    return pcard(pid, q, ans, e, k='match', o=o, p=p, eq=eqt)


@proto('ch-ege-23-text', 'ЕГЭ', 23, 'Равновесные и исходные концентрации (данные в тексте)',
       invariant='изменения концентраций пропорциональны коэффициентам: реагенты убывают на k·x, продукты (исходно 0) '
                 'растут на k·x; c(равн.) = c(исх.) ∓ k·x',
       varies='обратимая газовая реакция (синтезы, разложения, конверсия), какие концентрации даны и какие найти, шаг '
              'значений',
       answer_rule='две цифры: номера значений X и Y из списка шести',
       mistakes=['не умножили изменение на коэффициент', 'прибавили вместо вычитания для реагента',
                 'исходную концентрацию продукта сочли ненулевой'],
       solve=_solve_23, kes=['1.8', '5.1'],
       fidelity=fid('2 цифры (X, Y) из списка 6 значений', 'как зад. 23 демоверсии 2027: «В реактор постоянного объёма '
                    'поместили … Определите исходную концентрацию … (X) и равновесную … (Y). Выберите из списка номера '
                    'правильных ответов» — формулировка своя', 'Б', 3, 'концентрации 0,02–3 моль/л, шаг 0,02–0,2 — как '
                    'в банке', 'коэффициенты; реагент/продукт', ['1.8', '5.1'], '2 балла, 1 балл при одной ошибке'))
def g23_text(rng):
    return _g23(rng, 'ch-ege-23-text', False)


@proto('ch-ege-23-table', 'ЕГЭ', 23, 'Равновесные и исходные концентрации (данные в таблице)',
       invariant='то же: изменение = k·x; из пары (исходная, равновесная) одного вещества или равновесной концентрации '
                 'продукта находят x',
       varies='реакция, заполненные ячейки таблицы, искомые X и Y',
       answer_rule='две цифры: номера значений X и Y',
       mistakes=['перепутали строки таблицы', 'не учли коэффициенты'],
       solve=_solve_23, kes=['1.8', '5.1'],
       fidelity=fid('2 цифры', 'как в банке: «Используя данные, приведённые в таблице, определите …»', 'Б', 3,
                    'как в банке', 'коэффициенты', ['1.8', '5.1'], '2 балла, 1 балл при одной ошибке'))
def g23_table(rng):
    return _g23(rng, 'ch-ege-23-table', True)


@proto('ch-ege-23-letters', 'ЕГЭ', 23, 'Равновесные концентрации в абстрактной реакции (A, B, C)',
       invariant='та же схема на буквенных веществах: изменения пропорциональны коэффициентам',
       varies='схема A + 2B ⇄ C, A ⇄ B + 3C и др., данные в таблице или тексте',
       answer_rule='две цифры: номера значений X и Y',
       mistakes=['не учли коэффициенты', 'сложили вместо вычитания'],
       solve=_solve_23, kes=['1.8', '5.1'],
       fidelity=fid('2 цифры', 'как в банке: «В реактор постоянного объёма поместили вещество А и вещество В …»', 'Б', 3,
                    'как в банке', 'коэффициенты', ['1.8', '5.1'], '2 балла, 1 балл при одной ошибке'))
def g23_letters(rng):
    return _g23(rng, 'ch-ege-23-letters', rng.random() < 0.6, letters=True)
