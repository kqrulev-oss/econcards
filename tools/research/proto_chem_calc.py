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
    # точность должна соответствовать величине ответа: округление не искажает ответ больше чем на 5 %
    x = Fr(x)
    if x and abs(Fr(out.replace(',', '.')) - x) / abs(x) > Fr(1, 20):
        raise Retry
    return out


# Растворимость при ~20 °C (г на 100 г воды; справочник Лидина/CRC) → предельная массовая доля насыщенного раствора, %.
# Концентрации в условиях не должны превышать 90 % от неё (запас). Кислоты, смешивающиеся с водой, не ограничены.
SOLUB20 = {
    'NaNO3': 88, 'Mg(NO3)2': 70, 'KNO3': Fr(316, 10), 'Ba(NO3)2': Fr(91, 10), 'CuCl2': 73, 'KCl': 34, 'NaCl': 36,
    'CaCl2': Fr(745, 10), 'K2SO4': Fr(111, 10), 'Na2SO4': Fr(195, 10), 'CuSO4': Fr(207, 10), 'ZnSO4': 54, 'MgSO4': 35,
    'Na2CO3': Fr(215, 10), 'K2CO3': 111, 'NH4NO3': 192, 'AgNO3': 216, 'ZnCl2': 395, 'NH4Cl': Fr(372, 10),
    'Al2(SO4)3': Fr(364, 10), 'Zn(NO3)2': 118, 'CH3COONa': Fr(464, 10), 'NaOH': 109, 'KOH': 112, 'C6H12O6': 91,
    'C12H22O11': 204, 'Cu(NO3)2': 125, 'BaCl2': Fr(358, 10), 'FeCl3': 92, 'MgCl2': Fr(546, 10), 'Fe2(SO4)3': 80,
    'Na2S': Fr(186, 10), 'Na2SO3': 26, 'Na3PO4': Fr(121, 10), 'K3PO4': 90, 'Pb(NO3)2': Fr(545, 10), 'KI': 144,
    'Na2SiO3': 22, 'Ba(OH)2': Fr(39, 10), 'Ca(NO3)2': 121, 'FeSO4': Fr(265, 10), 'Ca(OH)2': Fr(17, 100),
    'KMnO4': Fr(64, 10), 'Fe(NO3)3': 82, 'AlCl3': 45, 'HCl': 72, 'KHCO3': Fr(332, 10),
    'NaHCO3': Fr(96, 10), 'NaF': 4, 'FeCl2': 64, 'H2SiO3': 0,
}


def wmax(f):
    """Предельная массовая доля (%) с запасом 10 %; None — ограничения нет (кислоты, смешивающиеся с водой)."""
    S = SOLUB20.get(f)
    if S is None:
        return None
    return Fr(S) / (100 + Fr(S)) * 100 * Fr(9, 10)


def w_ok(f, *ws):
    lim = wmax(f)
    return lim is None or all(Fr(w) <= lim for w in ws)


def rs(x, dec):
    """Независимое округление для solve(): Decimal, половина вверх."""
    x = Fr(x)
    d = (Decimal(x.numerator) / Decimal(x.denominator)).quantize(Decimal(1).scaleb(-dec), rounding=ROUND_HALF_UP)
    s = format(d, 'f')
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s.replace('.', ',')


def sfmt(x, dec):
    """Промежуточный шаг решения: округление с отбраковкой значений у границы округления."""
    guard(x, dec, Fr(1, 100))
    return fmt(Fr(x), dec)


def pcard_s(pid, q, a, e, *, steps, **kw):
    """Карточка развёрнутого задания: шаги решения (частичный балл) и их перечень в пояснении."""
    e = e + ' Элементы решения: ' + '; '.join(f'{lbl} = {v}' for lbl, v in steps) + '.'
    return pcard(pid, q, a, e, steps=steps, **kw)


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
        v = fmt(x, dec)
        if v != '0':
            out.append(v)
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
    if w >= 70 or not w_ok(f, w1, w):
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
    e = (f'm({name}) = ' + (f'{ru(m1)}·{fmt(w1, 2)}/100' if mode != 'masses' else f'{fmt(s1, 2)}') +
         (f' + {ru(add)}' if add else '') + f' = {fmt(s1 + add, 2)} г; '
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
    if not w_ok(f, *ws):
        raise Retry
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
    if not w_ok(f, w1, w2):
        raise Retry
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
        q = rng.choice([f'Рассчитайте массу {name}, которую нужно растворить в {m} г воды, чтобы массовая доля {name} в '
                        f'образовавшемся растворе составила {w2} %.',
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
    if not w_ok(f, w2):
        raise Retry
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
    if not w_ok(f, c):
        raise Retry
    m1 = Fr(rng.choice(range(50, 401, 5)))
    dec = rng.choice([0, 1])
    x = m1 * (w1 - w) / (w - w2)
    if x <= 0 or x > 3000:
        raise Retry
    ans = rnd(x, dec)
    q = rng.choice([f'Имеются два раствора {name}: {m1} г с массовой долей {w1} % и раствор с массовой долей {w2} %. '
                    f'Какую массу второго раствора нужно смешать с первым, чтобы массовая доля {name} в смеси составила '
                    f'{w} %?',
                    f'Для получения {w} %-ного раствора {name} к {m1} г {w1} %-ного раствора этого же вещества прибавили '
                    f'его раствор с массовой долей {w2} %. Рассчитайте массу прибавленного раствора.'])
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
        if x < 2:
            raise Retry
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


# приближённая зависимость плотности раствора от массовой доли (20 °C): ρ ≈ 1 + k·ω, ω в % (по справочным таблицам)
RHO_K = {'NaOH': Fr(11, 1000), 'KOH': Fr(92, 10000), 'NaCl': Fr(72, 10000), 'KCl': Fr(64, 10000), 'H2SO4': Fr(70, 10000),
         'HNO3': Fr(57, 10000), 'HCl': Fr(49, 10000), 'Na2CO3': Fr(104, 10000), 'CuSO4': Fr(107, 10000),
         'KNO3': Fr(65, 10000), 'Na2SO4': Fr(93, 10000), 'CaCl2': Fr(86, 10000), 'BaCl2': Fr(94, 10000),
         'NH4NO3': Fr(41, 10000), 'C6H12O6': Fr(39, 10000), 'AgNO3': Fr(93, 10000), 'K2CO3': Fr(92, 10000),
         'MgSO4': Fr(105, 10000), 'ZnCl2': Fr(95, 10000), 'KMnO4': Fr(70, 10000)}


def rho_of(f, w):
    """Реалистичная плотность раствора (г/мл), округлённая до сотых."""
    return Fr(round((1 + RHO_K[f] * Fr(w)) * 100), 100)


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
                        f'Какую массу {name} нужно взять, чтобы приготовить {V} мл раствора, молярная концентрация '
                        f'которого равна {ru(c)} моль/л?'])
        wrong = W([c * V * Mf, c * Mf, c * V / 1000], dec)
        p = dict(f=f, mode=mode, c=str(c), V=str(V), dec=dec)
        e = f'n = c·V = {ru(c)}·{ru(V / 1000)} = {ru(c * V / 1000)} моль; m = n·M'
    elif mode == 'c_from_w':
        w = rng.choice([2, 4, 5, 8, 10, 12, 15, 20, 25, 30])
        if not w_ok(f, w):
            raise Retry
        rho = rho_of(f, w)
        x = w * rho * 10 / Mf
        q = (f'Раствор {name} с массовой долей растворённого вещества {w} % имеет плотность {ru(rho)} г/мл. '
             f'Рассчитайте молярную концентрацию {name} в нём (моль/л).')
        wrong = W([w * 10 / Mf, w * rho / Mf, w * rho * 1000 / Mf], dec)
        p = dict(f=f, mode=mode, w=w, rho=str(rho), dec=dec)
        e = f'В 1 л: m(р-ра) = 1000·{ru(rho)} г, m(в-ва) = {ru(1000 * rho * w / 100)} г; c = m/M'
    else:
        c = Fr(rng.choice([10, 20, 25, 50, 75, 100, 125, 150, 200, 250, 300]), 100)
        w_est = c * Mf / 10                      # ω при ρ ≈ 1, затем уточняем плотность
        rho = rho_of(f, c * Mf / 10 / (1 + RHO_K[f] * w_est))
        x = c * Mf / rho / 10
        if not w_ok(f, x):
            raise Retry
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
    bys = [b for b in by_set if b != 'V' or (st == G and f != 'H2O')]
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
    txt = _thermo_q_text(rng, r, f, by, val)
    q = f'{txt}{chr(10) if txt.endswith("кДж") else " "}{tail(dec)}'
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
    by = rng.choice(['V', 'V', 'm', 'n']) if st == G and f != 'H2O' else rng.choice(['m', 'm', 'n'])
    n = Fr(rng.choice(range(1, 81)), rng.choice([10, 20, 4]))
    Q = abs(r['q']) * n / k
    if not nice(Q, 1) or Q < 2:
        raise Retry
    val = n * {'V': VM, 'm': M(f), 'n': 1}[by]
    dec = rng.choice([0, 1, 2]) if by != 'm' else rng.choice([0, 1])
    ans = rnd(val, dec)
    eq, eqt = therm_eq(r)
    past = 'выделилось' if r['q'] > 0 else 'поглотилось'
    if f in r['lhs']:
        role = 'вступившей в реакцию' if gnd(f) == 'f' else 'вступившего в реакцию'
        what = {'V': f'объём (н.у.) {gen(f)}, {role}', 'm': f'массу {gen(f)}, {role}',
                'n': f'количество вещества {gen(f)} (моль), {role}'}[by]
    else:
        role = pp_sh('образовавш', gnd(f))
        what = {'V': f'объём (н.у.) {role} {gen(f)}', 'm': f'массу {role} {gen(f)}',
                'n': f'количество вещества {role} {gen(f)} (моль)'}[by]
    q = rng.choice([f'Реакция протекает по термохимическому уравнению\n{eq}\nРассчитайте {what}, если в ходе процесса '
                    f'{past} {ru(Q)} кДж теплоты.',
                    f'Определите {what}, если известно, что тепловой эффект процесса составил {ru(Q)} кДж '
                    f'({"теплота выделялась" if r["q"] > 0 else "теплота поглощалась"}). Термохимическое уравнение '
                    f'реакции:\n{eq}'])
    q += ('\n' if q.endswith('кДж') else ' ') + tail(dec)
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
    by = 'V' if st == G and f != 'H2O' and rng.random() < 0.5 else 'm'
    n = Fr(rng.choice(range(1, 41)), rng.choice([10, 20, 40]))
    val = n * (VM if by == 'V' else M(f))
    if not nice(val, 2):
        raise Retry
    Qexp = abs(r['q']) * n / k
    if not nice(Qexp, 2) or Qexp < 1:
        raise Retry
    ans = fmt(Fr(abs(r['q'])), 0)
    kl, kr = balance(lhs, rhs)
    scheme = therm_eq(r)[0].rsplit(' + ' if r['q'] > 0 else ' − ', 1)[0] + (' + Q' if r['q'] > 0 else ' − Q')
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
    subj = what if all(x in ('O2', 'H2', 'Cl2') for x in r['lhs']) or g == main[0] else f'{what} {gen(main[0])}'
    pickq = rng.choice if main[0] not in (f, g) else (lambda xs: xs[0])
    q = pickq([f'В процессе {subj} {given}. Рассчитайте объём {fl} {gen(f)} (л).',
                    f'Какой объём {gen(f)} (л) {"расходуется" if f in r["lhs"] else "образуется"} в процессе {subj}, '
                    f'если {given_p}?'])
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
    raw, rg, rawg = c['raw']
    tpl = rng.randrange(3)
    if tpl == 0:
        q = f'Образец {rawg} массой {ru(m)} г, содержащий {imp} % {c["imp"]}, {c["act"]}. Рассчитайте {_want(f, fby)}.'
    elif tpl == 1:
        q = f'{cap(raw)} массой {ru(m)} г {"содержат" if rg == "pl" else "содержит"} {100 - imp} % {gen(g)} по массе; остальное — примеси, не участвующие ' \
            f'в реакции. Образец {c["act"]}. Определите {_want(f, fby)}.'
    else:
        q = f'В заводской лаборатории образец {rawg} массой {ru(m)} г {c["act"]}. Массовая доля {c["imp"]} в образце — ' \
            f'{imp} %. Найдите {_want(f, fby)}.'
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
    r = pick(rng, D.YIELD + [x for x in D.STOICH if x['calc']['g'] in ('Zn', 'Al', 'CaC2')
                             and 'постоянной массы' not in x['calc']['act'] and 'длительн' not in x['calc']['act']])
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
        s = f'{cap(NOM[g])} массой {ru(val)} г {c["act"]}; выделено {got} {gen(f)}.'
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
    raw, rg, rawg = c['raw']
    if mode == 'raw':
        x = pure * 100 / (100 - imp)
        q = f'Образец {rawg}, содержащий {imp} % {c["imp"]}, {c["act"]} и получили {got}. Рассчитайте массу образца.'
        wrong = W([pure, pure * (100 - imp) / 100, pure * (100 + imp) / 100], dec)
        p = dict(lhs=r['lhs'], rhs=r['rhs'], g=g, f=f, pv=str(pv), fby=fby, imp=imp, mode=mode, dec=dec)
    else:
        m = pure * 100 / (100 - imp)
        m = Fr(math.ceil(m * 10), 10) if not nice(m, 2) else m
        x = (m - pure) / m * 100
        if x <= 0:
            raise Retry
        q = f'Образец {rawg} массой {ru(m)} г {c["act"]} и получили {got}. Определите массовую долю (%) примесей в образце.'
        wrong = W([pure / m * 100, (m - pure) / pure * 100, x / 2], dec)
        p = dict(lhs=r['lhs'], rhs=r['rhs'], g=g, f=f, pv=str(pv), fby=fby, m=str(m), mode=mode, dec=dec)
    ans = rnd(x, dec)
    q += ' ' + tail(dec)
    eqs, eq = eqp(r['lhs'], r['rhs'])
    e = f'{eqs}; n({pretty(f)}) = {ru(nf)} моль ⇒ n({pretty(g)}) = {fmt(nf * k[g] / k[f], 4)} моль, m(чист.) = ' \
        f'{fmt(pure, 2)} г ⇒ {ans}.'
    return pcard('ch-ege-28-raw', q, ans, e, p=p, wrong=wrong, eq=eq)


def _solve_28_rev(p):
    k = coef(p['lhs'], p['rhs'])
    nf = Fr(p['pv']) / _unit_i(p['f'], p['fby'])
    ng = nf * 100 / Fr(p['eta']) * k[p['g']] / k[p['f']]
    return rs(ng * _unit_i(p['g'], p['gby']), p['dec'])


@proto('ch-ege-28-reverse', 'ЕГЭ', 28, 'Масса (объём) исходного вещества по количеству продукта и выходу',
       invariant='n(продукта, практ.) → n(продукта, теор.) = n(практ.)·100/η → по коэффициентам n(исходного) → m или V',
       varies='реакция (промышленные синтезы, брожение, этерификация, нитрование, восстановление металлов, окисление '
              'сероводорода), полученное количество продукта, выход, что найти (масса или объём исходного вещества)',
       answer_rule='масса (г) или объём (л, н.у.) исходного вещества с указанной точностью',
       mistakes=['умножили на выход вместо деления', 'не учли коэффициенты', 'нашли теоретическое количество продукта'],
       solve=_solve_28_rev, kes=['5.5'],
       fidelity=fid('число, г или л', 'как задание банка «Вычислите массу этилового спирта, из которого с выходом 75 % '
                    'получили 33,6 л (н.у.) бутадиена-1,3» — формулировка своя. Задания банка с КЭС 5.1 (простой расчёт '
                    'по уравнению без примесей и выхода) по плану 2027 не относятся к № 28 (5.4/5.5), поэтому отдельного '
                    'прототипа для них нет', 'Б', 4, 'продукт 1–100 г (л), выход 40–95 %',
                    'обратный ход: делить на выход, а не умножать', ['5.5'], '1 балл'))
def g28_reverse(rng):
    r = pick(rng, D.YIELD)
    c = r['calc']
    g, f = c['g'], c['f']
    k = coef(r['lhs'], r['rhs'])
    fby = 'V' if is_gas(f) and rng.random() < 0.7 else 'm'
    gby = 'V' if is_gas(g) and rng.random() < 0.7 else 'm'
    nf = Fr(rng.choice(range(1, 61)), rng.choice([10, 20, 40]))
    pv = nf * _unit(f, fby)
    if not nice(pv, 2):
        raise Retry
    eta = Fr(rng.choice([50, 60, 62.5, 64, 70, 75, 80, 85, 90, 92, 95, 96])).limit_denominator(10)
    x = nf * 100 / eta * k[g] / k[f] * _unit(g, gby)
    dec = rng.choice([0, 1, 2]) if gby == 'V' else rng.choice([0, 1])
    ans = rnd(x, dec)
    got = f'{ru(pv)} л (н.у.)' if fby == 'V' else f'{ru(pv)} г'
    act = c['act'].format(g=gen(g))
    want = f'объём (н.у.) {gen(g)}' if gby == 'V' else f'массу {gen(g)}'
    taken = 'взятой' if gnd(g) == 'f' else 'взятого'
    q = rng.choice([f'При {act} получили {got} {gen(f)}; выход продукта составил {ru(eta)} % от теоретически возможного. '
                    f'Рассчитайте {want}, {taken} для реакции.',
                    f'Рассчитайте {want}, необходим{"ую" if gby == "m" else "ый"} для получения {got} {gen(f)}, если '
                    f'практический выход продукта при {act} равен {ru(eta)} %.'])
    q += ' ' + tail(dec)
    eqs, eq = eqp(r['lhs'], r['rhs'])
    e = f'{eqs}; n({pretty(f)}, практ.) = {ru(nf)} моль; теоретически {fmt(nf * 100 / eta, 4)} моль; ' \
        f'n({pretty(g)}) = {fmt(nf * 100 / eta * k[g] / k[f], 4)} моль ⇒ {ans}.'
    unit = _unit(g, gby)
    wrong = W([nf * eta / 100 * k[g] / k[f] * unit, nf * k[g] / k[f] * unit, nf * 100 / eta * unit if k[g] != k[f] else x * 2], dec)
    return pcard('ch-ege-28-reverse', q, ans, e, p=dict(lhs=r['lhs'], rhs=r['rhs'], g=g, f=f, pv=str(pv), fby=fby, gby=gby,
                                                        eta=str(eta), dec=dec), wrong=wrong, eq=eq)


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
            elif ph == 'тв' and f not in ('Cu', 'Ag', 'Fe', 'Zn'):
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
    ch = _pick5(rng, items, lambda x: x[1] == sign, 2, 4)
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
    side = lambda ss, ks, sts: ' + '.join((str(k) if k > 1 else '') + disp(s) + PH[t] for s, k, t in zip(ss, ks, sts))
    return side(lhs, kl, st[:len(lhs)]) + ' = ' + side(rhs, kr, st[len(lhs):]), (lhs, rhs, kl, kr)


def disp(f):
    """Формула для показа: комплексы — с квадратными скобками (Na₂[Zn(OH)₄])."""
    return {'Na2(Zn(OH)4)': 'Na₂[Zn(OH)₄]'}.get(f, pretty(f))


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
            txt = ' и '.join(f'{disp(f)} {PH[ph]}' for f, ph, _ in R['r'])
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
ALC18 = [('воды', 6, 'H₂O'), ('метанола', 5, 'CH₃OH'), ('этанола', 4, 'C₂H₅OH'), ('пропанола-1', 3, 'пропанол-1'),
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
                    if (ac != ref[1] and ac[1] == ref[1][1]) or (m != ref[0] and m[2] == ref[0][2]):
                        continue            # разные вещества одного «ранга» — сравнить нельзя
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
        n_solid = sum(1 for x in pick4 if x[0] == 'c' and phase_of[x[1][0]] == 'тв')
        if what == 'hetero' and (n_solid > 2 or (n_solid == 0 and rng.random() < 0.7)):
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


# ======================================================================= ЕГЭ 34. Комбинированные расчётные задачи
# Ответ — число (итог решения, обычно массовая доля в %, до десятых). В КИМ № 34 оценивается ход решения (4 балла);
# в тренажёре проверяем итоговое число, уравнения и шаги — в объяснении.

KIM34 = ('В ответе запишите уравнения реакций, которые указаны в условии задачи, и приведите все необходимые вычисления '
         '(указывайте единицы измерения и обозначения искомых физических величин). В тренажёре введите итоговое число. ')


def _gw(f):
    return D.GEN.get(f, (pretty(f), 'm'))[0]


def _sol_mass(n, f, w):
    """Масса раствора, содержащего n моль вещества f при массовой доле w (%)."""
    return n * M(f) * 100 / Fr(w)


def _nice_sol(rng, n, f, ws=(5, 8, 10, 12, 15, 16, 20, 24, 25, 30, 40)):
    """Подобрать массовую долю так, чтобы масса раствора была «круглой» (≤ 1 знака после запятой)."""
    cand = [w for w in ws if nice(_sol_mass(n, f, w), 1) and _sol_mass(n, f, w) <= 800 and w_ok(f, w)]
    if not cand:
        raise Retry
    w = pick(rng, cand)
    return w, _sol_mass(n, f, w)


EL34 = {  # соль: (реакция электролиза раствора, металл/основание, газ на аноде, газ на катоде)
    'CuSO4': (['CuSO4', 'H2O'], ['Cu', 'O2', 'H2SO4'], 'O2', None),
    'Cu(NO3)2': (['Cu(NO3)2', 'H2O'], ['Cu', 'O2', 'HNO3'], 'O2', None),
    'AgNO3': (['AgNO3', 'H2O'], ['Ag', 'O2', 'HNO3'], 'O2', None),
    'NaCl': (['NaCl', 'H2O'], ['NaOH', 'H2', 'Cl2'], 'Cl2', 'H2'),
    'KCl': (['KCl', 'H2O'], ['KOH', 'H2', 'Cl2'], 'Cl2', 'H2'),
    'CuCl2': (['CuCl2'], ['Cu', 'Cl2'], 'Cl2', None),
}
LEAVE = {'Cu', 'Ag', 'O2', 'H2', 'Cl2'}  # уходят из раствора при электролизе


def _el_state(salt, n0, x):
    """Состав раствора после электролиза x моль соли: {вещество: моль}, потеря массы раствора."""
    lhs, rhs, _, _ = EL34[salt]
    k = coef(lhs, rhs)
    comp = {salt: n0 - x}
    loss = Fr(0)
    for f in rhs:
        amt = x * Fr(k[f], k[salt])
        if f in LEAVE:
            loss += amt * M(f)
        else:
            comp[f] = comp.get(f, 0) + amt
    return comp, loss


def _el_calc(p):
    """Независимый пересчёт по данным условия через число электронов и ионный баланс раствора.
    Возвращает шаги: n(разложившейся соли), m(р-ра после электролиза), n(реагента, вступившего в реакцию)
    [, m(конечного р-ра)], ответ."""
    salt = p['salt']
    m0, w0 = Fr(p['m0']), Fr(p['w0'])
    n0 = m0 * w0 / 100 / Mi(salt)
    ez = {'CuSO4': 2, 'Cu(NO3)2': 2, 'CuCl2': 2, 'AgNO3': 1, 'NaCl': 1, 'KCl': 1}[salt]   # e⁻ на формульную единицу
    cat = {'CuSO4': Mi('Cu') / 2, 'Cu(NO3)2': Mi('Cu') / 2, 'CuCl2': Mi('Cu') / 2, 'AgNO3': Mi('Ag'),
           'NaCl': Mi('H'), 'KCl': Mi('H')}[salt]                                      # масса на 1 моль e⁻ на катоде
    an = Mi('O') / 2 if salt in ('CuSO4', 'Cu(NO3)2', 'AgNO3') else Mi('Cl')            # … на аноде
    kind, val = p['stop']
    val = Fr(val)
    if kind == 'an':
        e = val / VM * (4 if salt in ('CuSO4', 'Cu(NO3)2', 'AgNO3') else 2)
    elif kind == 'cat':
        e = val / VM * 2
    else:
        e = val / (cat + an)
    x = e / ez
    m_after = m0 - e * (cat + an)
    H = e if salt in ('CuSO4', 'Cu(NO3)2', 'AgNO3') else 0
    OH = e if salt in ('NaCl', 'KCl') else 0
    metal_ion = (n0 - x) if salt in ('CuSO4', 'Cu(NO3)2', 'CuCl2', 'AgNO3') else 0
    r = p['reag']
    if p['mode'] == 'portion':
        f = Fr(p['mp']) / m_after
        need = {'NaOH': H * f + 2 * metal_ion * f, 'NaCl': metal_ion * f, 'CuSO4': OH * f / 2}[r]
        return [(x, 3), (m_after, 2), (need, 3), (need * Mi(r) * 100 / Fr(p['wr']), 1)]
    mr = Fr(p['mr'])
    nr = mr * Fr(p['wr']) / 100 / Mi(r)
    if r == 'NaOH':
        used = H + 2 * metal_ion
        left, lost = {'NaOH': nr - used}, metal_ion * Mi('Cu(OH)2')
    elif r == 'Na2CO3':
        used = nr
        lost = nr * Mi('CO2')
        left = {'H2SO4': (H - 2 * nr) / 2, 'HNO3': H - 2 * nr, salt: metal_ion}
    elif r == 'NaCl':
        used = metal_ion
        left, lost = {'NaCl': nr - metal_ion, 'HNO3': H}, metal_ion * Mi('AgCl')
    else:
        used = nr
        left, lost = {'NaOH' if salt == 'NaCl' else 'KOH': OH - 2 * nr, salt: n0 - x}, nr * Mi('Cu(OH)2')
    total = m_after + mr - lost
    t = p['target']
    return [(x, 3), (m_after, 2), (used, 3), (total, 2), (left[t] * Mi(t) / total * 100, 1)]


def _steps(calc):
    return lambda p: [rs(v, d) for v, d in calc(p)]


def _last(calc):
    return lambda p: rs(*calc(p)[-1])


_solve_34_el = _last(_el_calc)


@proto('ch-ege-34-electro', 'ЕГЭ', 34, 'Электролиз раствора соли, затем реакция с другим раствором',
       invariant='по объёму газа или уменьшению массы находят количество разложившейся соли; масса раствора после '
                 'электролиза = исходная − (металл/H₂ на катоде + газ на аноде); затем реакция с добавленным раствором, '
                 'масса конечного раствора за вычетом осадка/газа',
       varies='соль (CuSO₄, Cu(NO₃)₂, AgNO₃, NaCl, KCl, CuCl₂), способ остановки (газ на аноде/катоде, убыль массы), '
              'второй реагент (NaOH, Na₂CO₃, NaCl, CuSO₄), что найти (доля вещества или масса раствора для порции)',
       answer_rule='массовая доля (%) или масса раствора (г), округление до десятых',
       mistakes=['не вычли из массы раствора выделившиеся на электродах вещества', 'не учли, что щёлочь сначала '
                 'нейтрализует кислоту', 'не вычли массу осадка или газа'],
       solve=_solve_34_el, kes=['1.13', '5.4', '5.6', '5.7'],
       fidelity=fid('в КИМ — развёрнутое решение (4 балла); в тренажёре — итоговое число с точностью до десятых',
                    'как задания банка № 34 «Для проведения электролиза (на инертных электродах) взяли …» — '
                    'формулировка своя, те же шаги', 'В', 22, 'массы растворов 100–700 г, доли 10–40 %, газы 1–7 л — как в банке',
                    'масса раствора после электролиза; порядок реакций (кислота раньше соли)', ['1.13', '5.4', '5.6', '5.7'],
                    '4 балла в КИМ (за шаги), в тренажёре — число'))
def g34_electro(rng):
    salt = pick(rng, list(EL34))
    lhs, rhs, an, cat = EL34[salt]
    k = coef(lhs, rhs)
    n0 = Fr(rng.choice(range(4, 21)), 20)          # 0,2–1 моль
    x = n0 * Fr(rng.choice([1, 2, 3, 4]), 5)
    w0, m0 = _nice_sol(rng, n0, salt, (10, 12, 15, 16, 20, 25, 30, 40))
    comp, loss = _el_state(salt, n0, x)
    m_after = m0 - loss
    v_an, v_cat = x * Fr(k[an], k[salt]) * VM, (x * Fr(k[cat], k[salt]) * VM if cat else None)
    stops = [('an', f'на аноде выделилось {ru(v_an)} л (н.у.) газа', v_an)]
    if cat:
        stops.append(('cat', f'на катоде собрали {ru(v_cat)} л (н.у.) газа', v_cat))
    if nice(loss, 2):
        stops.append(('mass', f'масса раствора уменьшилась на {ru(loss)} г', loss))
    stop = pick(rng, stops)
    if not nice(x * Fr(k[an], k[salt]) * VM, 3):
        raise Retry
    name = _gw(salt)
    metal_ion = n0 - x if salt in ('CuSO4', 'Cu(NO3)2', 'CuCl2', 'AgNO3') else 0
    H = x * (2 if salt in ('CuSO4', 'Cu(NO3)2') else 1) if salt in ('CuSO4', 'Cu(NO3)2', 'AgNO3') else 0
    OH = x if salt in ('NaCl', 'KCl') else 0
    mode = 'final' if rng.random() < 0.8 else 'portion'
    if salt in ('CuSO4', 'Cu(NO3)2', 'CuCl2'):
        reag = 'NaOH' if salt == 'CuCl2' or rng.random() < 0.6 else 'Na2CO3'
    elif salt == 'AgNO3':
        reag = 'NaCl'
    else:
        reag = 'CuSO4'
    if mode == 'portion' and reag == 'Na2CO3':
        reag = 'NaOH'
    if mode == 'portion':
        frac = Fr(1, rng.choice([2, 4, 5, 10]))
        mp = m_after * frac
        if not nice(mp, 2):
            raise Retry
        need = {'NaOH': H * frac + 2 * metal_ion * frac, 'NaCl': metal_ion * frac, 'CuSO4': OH * frac / 2}[reag]
        wr = pick(rng, [w for w in (5, 8, 10, 15, 20, 25) if w_ok(reag, w)])
        ans_v = need * M(reag) * 100 / wr
        ans = rnd(ans_v, 1)
        purpose = {'NaOH': 'полного осаждения ионов меди', 'NaCl': 'полного осаждения ионов серебра',
                   'CuSO4': 'полного связывания щёлочи в осадок'}[reag]
        q = (f'Раствор {name} массой {ru(m0)} г с массовой долей соли {w0} % подвергли электролизу с инертными '
             f'электродами. Когда {stop[1]}, ток отключили. Из полученного раствора взяли порцию массой {ru(mp)} г. '
             f'Рассчитайте массу {wr} %-ного раствора {_gw(reag)}, которая потребуется для {purpose} в этой порции. '
             f'' + KIM34 + '(Запишите число с точностью до десятых.)')
        p = dict(salt=salt, m0=str(m0), w0=w0, stop=[stop[0], str(stop[2])], reag=reag, mode='portion', mp=str(mp),
                 wr=wr, target='')
        steps = [('n(разложившейся соли), моль', sfmt(x, 3)), ('m(раствора после электролиза), г', sfmt(m_after, 2)),
                 (f'n({pretty(reag)}), необходимое для порции, моль', sfmt(need, 3)), (f'm(раствора {pretty(reag)}), г', ans)]
        e = f'Разложилось {fmt(x, 3)} моль соли; масса раствора после электролиза {fmt(m_after, 2)} г; в порции ' \
            f'{fmt(frac, 3)} часть веществ; n({pretty(reag)}) = {fmt(need, 4)} моль ⇒ m(р-ра) ≈ {ans} г.'
        wrong = W([need * M(reag), ans_v * 2 if reag == 'CuSO4' else ans_v / 2, need * M(reag) * 100 / wr / frac], 1)
    else:
        if reag == 'NaOH':
            used = H + (2 if salt != 'AgNO3' else 1) * metal_ion
            nr = used + Fr(rng.choice(range(1, 11)), 20)
        elif reag == 'Na2CO3':
            nr = H / 2 * Fr(rng.choice([1, 2, 3, 4]), 5)
        elif reag == 'NaCl':
            nr = metal_ion + Fr(rng.choice(range(1, 11)), 20)
        else:
            nr = OH / 2 * Fr(rng.choice([1, 2, 3, 4]), 5)
        if nr <= 0:
            raise Retry
        wr, mr = _nice_sol(rng, nr, reag)
        if reag == 'NaOH':
            targets = ['NaOH']
        elif reag == 'Na2CO3':
            targets = [salt, 'H2SO4' if salt == 'CuSO4' else 'HNO3']
        elif reag == 'NaCl':
            targets = ['NaCl', 'HNO3']
        else:
            targets = ['NaOH' if salt == 'NaCl' else 'KOH', salt]
        target = pick(rng, targets)
        p = dict(salt=salt, n0=str(n0), x=str(x), m0=str(m0), w0=w0, stop=[stop[0], str(stop[2])], reag=reag,
                 nr=str(nr), mr=str(mr), wr=wr, mode='final', target=target)
        exact = Fr(_ans_exact_el(p))
        if exact <= 0:
            raise Retry
        ans = rnd(exact, 1)
        used = {'NaOH': H + 2 * metal_ion, 'Na2CO3': nr, 'NaCl': metal_ion, 'CuSO4': nr}[reag]
        lost = {'NaOH': metal_ion * M('Cu(OH)2'), 'Na2CO3': nr * M('CO2'), 'NaCl': metal_ion * M('AgCl'),
                'CuSO4': nr * M('Cu(OH)2')}[reag]
        steps = [('n(разложившейся соли), моль', sfmt(x, 3)), ('m(раствора после электролиза), г', sfmt(m_after, 2)),
                 (f'n({pretty(reag)}), вступившего в реакцию, моль', sfmt(used, 3)),
                 ('m(конечного раствора), г', sfmt(m_after + mr - lost, 2)), (f'ω({pretty(target)}), %', ans)]
        q = (f'Раствор {name} массой {ru(m0)} г с массовой долей соли {w0} % подвергли электролизу с инертными '
             f'электродами. Когда {stop[1]}, ток отключили. К оставшемуся раствору прилили {ru(mr)} г {wr} %-ного '
             f'раствора {_gw(reag)}. Рассчитайте массовую долю {_gw(target)} в образовавшемся растворе. '
             f'' + KIM34 + '(Запишите число с точностью до десятых.)')
        e = f'Разложилось {fmt(x, 3)} моль {pretty(salt)}; масса раствора после электролиза {fmt(m_after, 2)} г; ' \
            f'взято {fmt(nr, 3)} моль {pretty(reag)}, в реакцию вступило {fmt(used, 3)} моль; из раствора уходит ' \
            f'{fmt(lost, 2)} г осадка/газа, масса конечного раствора {fmt(m_after + mr - lost, 2)} г ⇒ ω ≈ {ans} %.'
        wrong = W([exact * m_after / m0, exact * (m_after + mr) / (m0 + mr), exact * 2], 1)
    eqs = [eqp(lhs, rhs)[1]]
    return pcard_s('ch-ege-34-electro', q, ans, e, p=p, wrong=wrong, eqs=eqs, steps=steps)


def _ans_exact_el(p):
    """Точное значение ответа (для отбраковки у границы округления) — через тот же баланс, без округления."""
    salt, n0, x = p['salt'], Fr(p['n0']), Fr(p['x'])
    comp, loss = _el_state(salt, n0, x)
    m_after = Fr(p['m0']) - loss
    reag, nr, mr = p['reag'], Fr(p['nr']), Fr(p['mr'])
    H = comp.get('H2SO4', 0) * 2 + comp.get('HNO3', 0)
    metal_ion = comp[salt] if salt in ('CuSO4', 'Cu(NO3)2', 'CuCl2', 'AgNO3') else 0
    if reag == 'NaOH':
        used = H + (2 if salt != 'AgNO3' else 1) * metal_ion
        left, lost = {'NaOH': nr - used}, metal_ion * M('Cu(OH)2')
    elif reag == 'Na2CO3':
        left = {salt: metal_ion, 'H2SO4': comp.get('H2SO4', 0) - nr, 'HNO3': comp.get('HNO3', 0) - 2 * nr}
        lost = nr * M('CO2')
    elif reag == 'NaCl':
        left, lost = {'NaCl': nr - metal_ion, 'HNO3': comp.get('HNO3', 0)}, metal_ion * M('AgCl')
    else:
        base = 'NaOH' if salt == 'NaCl' else 'KOH'
        left, lost = {base: comp[base] - 2 * nr, salt: comp[salt]}, nr * M('Cu(OH)2')
    t = p['target']
    return left[t] * M(t) / (m_after + mr - lost) * 100


DEC34 = {  # соль: (твёрдый продукт, газы [(ф, моль на моль соли)], реагент для остатка, растворяется ли весь остаток)
    'CaCO3': ('CaO', [('CO2', 1)], 'HCl'), 'MgCO3': ('MgO', [('CO2', 1)], 'HCl'), 'BaCO3': ('BaO', [('CO2', 1)], 'HCl'),
    'KClO3': ('KCl', [('O2', Fr(3, 2))], 'AgNO3'), 'AgNO3': ('Ag', [('NO2', 1), ('O2', Fr(1, 2))], 'HCl'),
    'Cu(NO3)2': ('CuO', [('NO2', 2), ('O2', Fr(1, 2))], 'NaOH'), 'Mg(NO3)2': ('MgO', [('NO2', 2), ('O2', Fr(1, 2))], 'NaOH'),
    'NaHCO3': ('Na2CO3', [('CO2', Fr(1, 2)), ('H2O', Fr(1, 2))], 'HCl'),
}


def _dec_result(salt, x, r, reag, nr, water, mres):
    """Масса и состав конечного раствора после обработки остатка (x — разложилось, r — осталось соли)."""
    solid, gases, _ = DEC34[salt]
    s_k = Fr(parse_formula(salt).get({'CaCO3': 'Ca', 'MgCO3': 'Mg', 'BaCO3': 'Ba', 'KClO3': 'K', 'AgNO3': 'Ag',
                                      'Cu(NO3)2': 'Cu', 'Mg(NO3)2': 'Mg', 'NaHCO3': 'Na'}[salt], 1),
             parse_formula(solid).get({'CaCO3': 'Ca', 'MgCO3': 'Mg', 'BaCO3': 'Ba', 'KClO3': 'K', 'AgNO3': 'Ag',
                                       'Cu(NO3)2': 'Cu', 'Mg(NO3)2': 'Mg', 'NaHCO3': 'Na'}[salt], 1))
    n_solid = x * s_k
    mr_sol = Fr(0)
    left, gone = {}, Fr(0)
    if salt in ('CaCO3', 'MgCO3', 'BaCO3'):
        cl = {'CaCO3': 'CaCl2', 'MgCO3': 'MgCl2', 'BaCO3': 'BaCl2'}[salt]
        need = 2 * (n_solid + r)
        left = {'HCl': nr - need, cl: n_solid + r}
        gone = r * M('CO2')
        m_in = mres
    elif salt == 'NaHCO3':
        need = 2 * n_solid + r
        left = {'HCl': nr - need, 'NaCl': 2 * n_solid + r}
        gone = (n_solid + r) * M('CO2')
        m_in = mres
    elif salt == 'KClO3':
        left = {'AgNO3': nr - n_solid, 'KNO3': n_solid, 'KClO3': r}
        gone = n_solid * M('AgCl')
        m_in = mres
    elif salt == 'AgNO3':
        left = {'HCl': nr - r, 'HNO3': r}
        gone = r * M('AgCl')
        m_in = r * M('AgNO3') + water          # серебро не растворяется
    else:
        hyd = {'Cu(NO3)2': 'Cu(OH)2', 'Mg(NO3)2': 'Mg(OH)2'}[salt]
        left = {'NaOH': nr - 2 * r, 'NaNO3': 2 * r}
        gone = r * M(hyd)
        m_in = r * M(salt) + water             # оксид металла в раствор не переходит
    return left, m_in - gone


def _dec_calc(p):
    """Пересчёт от данных условия: n(газа) → x; масса остатка → r; далее баланс раствора."""
    salt = p['salt']
    solid, gases, reag = DEC34[salt]
    per = sum(Fr(g[1]) for g in gases if g[0] != 'H2O')
    mres = Fr(p['mres'])
    if salt == 'NaHCO3':
        x = (Fr(p['m0']) - mres) / (Mi('CO2') / 2 + Mi('H2O') / 2)
    else:
        x = Fr(p['V']) / VM / per
    solid_per = Fr(1, 2) if salt == 'NaHCO3' else 1
    r = (mres - x * solid_per * Mi(solid)) / Mi(salt)
    nr = Fr(p['mr']) * Fr(p['wr']) / 100 / Mi(reag)
    left, msol = _dec_result(salt, x, r, reag, nr, Fr(p['water']), mres)
    total = msol + Fr(p['mr']) + Fr(p['water']) * (0 if salt in ('AgNO3', 'Cu(NO3)2', 'Mg(NO3)2') else 1)
    t = p['target']
    return [(x, 3), (r, 3), (nr - left[reag], 3), (total, 2), (left[t] * Mi(t) / total * 100, 1)]


_solve_34_dec = _last(_dec_calc)


@proto('ch-ege-34-decomp', 'ЕГЭ', 34, 'Частичное термическое разложение соли, затем реакция остатка с раствором',
       invariant='по объёму газов (или убыли массы) находят разложившуюся часть, по массе остатка — неразложившуюся; '
                 'остаток реагирует с раствором; масса конечного раствора = остаток (растворимая часть) + вода + раствор '
                 '− осадок − газ',
       varies='соль (CaCO₃, MgCO₃, BaCO₃, NaHCO₃, KClO₃, AgNO₃, Cu(NO₃)₂, Mg(NO₃)₂), реагент (HCl, AgNO₃, NaOH), '
              'что найти (доля кислоты/щёлочи/соли)',
       answer_rule='массовая доля вещества в конечном растворе, %, до десятых',
       mistakes=['считают, что разложилась вся соль', 'не учитывают газ из неразложившегося карбоната',
                 'включают нерастворимый оксид/металл в массу раствора'],
       solve=_solve_34_dec, kes=['5.4', '5.6', '5.7'],
       fidelity=fid('в КИМ — развёрнутое решение; в тренажёре — число, % до десятых', 'как задания банка № 34 «При '
                    'нагревании образца … часть вещества разложилась …» — формулировка своя', 'В', 22,
                    'газ 1–10 л, остаток 10–100 г, растворы 50–400 г', 'смесь в остатке; нерастворимые компоненты',
                    ['5.4', '5.6', '5.7'], '4 балла в КИМ'))
def g34_decomp(rng):
    salt = pick(rng, list(DEC34))
    solid, gases, reag = DEC34[salt]
    x = Fr(rng.choice(range(2, 21)), 20)
    r = Fr(rng.choice(range(1, 17)), 20)
    solid_per = Fr(1, 2) if salt == 'NaHCO3' else 1
    mres = x * solid_per * M(solid) + r * M(salt)
    if not nice(mres, 2):
        raise Retry
    per = sum(Fr(g[1]) for g in gases if g[0] != 'H2O')
    V = x * per * VM
    m0 = (x + r) * M(salt)
    water = Fr(rng.choice([0, 50, 100, 150, 200])) if salt in ('AgNO3', 'Cu(NO3)2', 'Mg(NO3)2') else Fr(0)
    if salt in ('AgNO3', 'Cu(NO3)2', 'Mg(NO3)2') and water == 0:
        water = Fr(100)
    n_solid = x * solid_per
    need = {'HCl': (2 * (n_solid + r) if salt != 'NaHCO3' else 2 * n_solid + r) if salt != 'AgNO3' else r,
            'AgNO3': n_solid, 'NaOH': 2 * r}[reag]
    nr = need + Fr(rng.choice(range(1, 13)), 20)
    wr, mr = _nice_sol(rng, nr, reag)
    if salt == 'KClO3' and r * M('KClO3') > mr * (100 - wr) / 100 * Fr(6, 100):
        raise Retry             # остаток KClO₃ должен полностью раствориться (растворимость ≈ 7 г на 100 г воды)
    prod_cl = {'CaCO3': 'CaCl2', 'MgCO3': 'MgCl2', 'BaCO3': 'BaCl2', 'NaHCO3': 'NaCl', 'AgNO3': 'HNO3'}.get(salt)
    targets = {'HCl': ['HCl', prod_cl], 'AgNO3': ['AgNO3', 'KNO3'], 'NaOH': ['NaOH', 'NaNO3']}[reag]
    target = pick(rng, targets)
    p = dict(salt=salt, V=str(V), mres=str(mres), m0=str(m0), mr=str(mr), wr=wr, water=str(water), target=target)
    left, msol = _dec_result(salt, x, r, reag, nr, water, mres)
    total = msol + mr + (0 if salt in ('AgNO3', 'Cu(NO3)2', 'Mg(NO3)2') else water)
    exact = left[target] * M(target) / total * 100
    if exact <= 0:
        raise Retry
    ans = rnd(exact, 1)
    sname = _gw(salt)
    if salt == 'NaHCO3':
        s1 = f'Образец гидрокарбоната натрия массой {ru(m0)} г нагревали, пока его масса не уменьшилась до {ru(mres)} г.'
    else:
        gas_w = 'смеси газов' if len(gases) > 1 else 'газа'
        cat = ''     # без катализатора: иначе он остался бы в твёрдом остатке
        s1 = \
            f'Порцию {sname} нагревали{cat}; разложилась только часть соли. Собрали {ru(V)} л (н.у.) {gas_w}, а твёрдый ' \
            f'остаток имел массу {ru(mres)} г.'
    wtxt = f', прилили к нему {ru(water)} мл воды' if salt in ('AgNO3', 'Cu(NO3)2', 'Mg(NO3)2') else ''
    s2 = f'Остаток перенесли в колбу{wtxt} и добавили {ru(mr)} г раствора {_gw(reag)} с массовой долей {wr} %.'
    q = f'{s1} {s2} Рассчитайте массовую долю {_gw(target)} в образовавшемся растворе. ' + KIM34 + \
        '(Запишите число с точностью до десятых.)'
    e = f'Разложилось {fmt(x, 3)} моль {pretty(salt)}, осталось {fmt(r, 3)} моль; из {fmt(nr, 3)} моль взятого ' \
        f'{pretty(reag)} в реакцию вступило {fmt(need, 3)} моль; масса конечного раствора {fmt(total, 2)} г ⇒ ω ≈ {ans} %.'
    steps = [('n(разложившейся соли), моль', sfmt(x, 3)), ('n(неразложившейся соли), моль', sfmt(r, 3)),
             (f'n({pretty(reag)}), вступившего в реакцию, моль', sfmt(need, 3)), ('m(конечного раствора), г', sfmt(total, 2)),
             (f'ω({pretty(target)}), %', ans)]
    wrong = W([exact * total / (total + (r * M("CO2") if salt in ("CaCO3", "MgCO3", "BaCO3") else 20)),
               left[target] * M(target) / (mres + mr + water) * 100, exact * 2], 1)
    eqs = [eqp([salt], [solid] + [g for g, _ in gases])[1]]
    return pcard_s('ch-ege-34-decomp', q, ans, e, p=p, wrong=wrong, eqs=eqs, steps=steps)


ATOM34 = [  # (X, Y, кислота, соль, элементы отношения)
    ('Zn', 'ZnCO3', 'H2SO4', 'ZnSO4', ('Zn', 'O')), ('Mg', 'MgCO3', 'HCl', 'MgCl2', ('Mg', 'O')),
    ('Ca', 'CaCO3', 'HCl', 'CaCl2', ('Ca', 'O')), ('MgO', 'MgCO3', 'HCl', 'MgCl2', ('O', 'Mg')),
    ('Na2CO3', 'NaHCO3', 'HCl', 'NaCl', ('Na', 'C')), ('Al', 'Al2O3', 'HCl', 'AlCl3', ('Al', 'O')),
    ('Fe', 'FeO', 'H2SO4', 'FeSO4', ('Fe', 'O')), ('K2CO3', 'KHCO3', 'HNO3', 'KNO3', ('K', 'C')),
    ('CaO', 'CaCO3', 'HNO3', 'Ca(NO3)2', ('O', 'Ca')), ('Zn', 'ZnO', 'HCl', 'ZnCl2', ('Zn', 'O')),
]
ATOM_G = {'Zn': 'цинка', 'O': 'кислорода', 'Mg': 'магния', 'Ca': 'кальция', 'C': 'углерода', 'Na': 'натрия',
          'Al': 'алюминия', 'Fe': 'железа', 'K': 'калия', 'H': 'водорода'}
NAME34 = {'Zn': 'цинк', 'ZnCO3': 'карбонат цинка', 'Mg': 'магний', 'MgCO3': 'карбонат магния', 'Ca': 'кальций',
          'CaCO3': 'карбонат кальция', 'MgO': 'оксид магния', 'Na2CO3': 'карбонат натрия', 'NaHCO3': 'гидрокарбонат натрия',
          'Al': 'алюминий', 'Al2O3': 'оксид алюминия', 'Fe': 'железо', 'FeO': 'оксид железа(II)', 'K2CO3': 'карбонат калия',
          'KHCO3': 'гидрокарбонат калия', 'CaO': 'оксид кальция', 'ZnO': 'оксид цинка'}


def _acid_rx(s, acid, salt):
    """Уравнение взаимодействия компонента смеси с кислотой (продукты подбираем по составу)."""
    el = parse_formula(s)
    prods = [salt]
    if 'C' in el:
        prods.append('CO2')
    if 'O' in el or 'H' in el:
        prods.append('H2O')
    if 'O' not in el:
        prods.append('H2')
    if s in ('Na2CO3', 'K2CO3', 'NaHCO3', 'KHCO3', 'ZnCO3', 'MgCO3', 'CaCO3', 'MgO', 'CaO', 'ZnO', 'Al2O3', 'FeO'):
        prods = [p_ for p_ in prods if p_ != 'H2']
    return [s, acid], prods


def _atoms_calc(p):
    X, Y, acid, salt = p['X'], p['Y'], p['acid'], p['salt']
    e1, e2 = p['els']
    a1, a2 = Fr(p['ratio'][0]), Fr(p['ratio'][1])
    cx, cy = parse_formula(X), parse_formula(Y)
    # a·(cx[e1]·a2 − cx[e2]·a1) = b·(cy[e2]·a1 − cy[e1]·a2); m = a·M(X) + b·M(Y)
    kx = cx.get(e1, 0) * a2 - cx.get(e2, 0) * a1
    ky = cy.get(e2, 0) * a1 - cy.get(e1, 0) * a2
    t = Fr(ky, kx) if kx else None            # a = t·b
    m = Fr(p['m'])
    b = m / (t * Mi(X) + Mi(Y))
    a = t * b
    # газы и соль по уравнениям
    gas_m, salt_n, acid_used = Fr(0), Fr(0), Fr(0)
    for s, n in ((X, a), (Y, b)):
        lhs, rhs = _acid_rx(s, acid, salt)
        k = coef(lhs, rhs)
        for g in ('H2', 'CO2'):
            if g in rhs:
                gas_m += n * Fr(k[g], k[s]) * Mi(g)
        salt_n += n * Fr(k[salt], k[s])
        acid_used += n * Fr(k[acid], k[s])
    total = m + Fr(p['ms']) - gas_m
    if p['target'] == 'salt':
        w = salt_n * Mi(salt) / total * 100
    else:
        w = (Fr(p['ms']) * Fr(p['ws']) / 100 - acid_used * Mi(acid)) / total * 100
    return [(a, 3), (b, 3), (gas_m, 2), (total, 2), (w, 1)]


_solve_34_atoms = _last(_atoms_calc)


@proto('ch-ege-34-atoms', 'ЕГЭ', 34, 'Смесь веществ с заданным соотношением числа атомов, растворение в кислоте',
       invariant='из отношения числа атомов двух элементов и массы смеси составляют систему и находят количества '
                 'компонентов; затем реакции с кислотой, масса раствора за вычетом газов',
       varies='смесь (Zn + ZnCO₃, Mg + MgCO₃, MgO + MgCO₃, Na₂CO₃ + NaHCO₃, Al + Al₂O₃, Fe + FeO …), отношение атомов, '
              'кислота, что найти (доля соли или оставшейся кислоты)',
       answer_rule='массовая доля, %, до десятых',
       mistakes=['атомное отношение перепутали с мольным отношением веществ', 'не вычли массу выделившихся газов',
                 'забыли, что кислота была в избытке'],
       solve=_solve_34_atoms, kes=['5.4', '5.6', '5.7'],
       fidelity=fid('в КИМ — развёрнутое решение; в тренажёре — число, %', 'как задания банка № 34 «Смесь …, в которой '
                    'соотношение числа атомов … равно …, растворили в …» — формулировка своя', 'В', 22,
                    'массы смесей 5–80 г, растворы кислот 100–800 г', 'система уравнений по атомам', ['5.4', '5.6', '5.7'],
                    '4 балла в КИМ'))
def g34_atoms(rng):
    X, Y, acid, salt, (e1, e2) = pick(rng, ATOM34)
    a = Fr(rng.choice(range(1, 13)), 20)
    b = Fr(rng.choice(range(1, 13)), 20)
    cx, cy = parse_formula(X), parse_formula(Y)
    n1 = a * cx.get(e1, 0) + b * cy.get(e1, 0)
    n2 = a * cx.get(e2, 0) + b * cy.get(e2, 0)
    ratio = n1 / n2
    if ratio.numerator > 20 or ratio.denominator > 20 or ratio == 1:
        raise Retry
    m = a * M(X) + b * M(Y)
    if not nice(m, 2):
        raise Retry
    need = Fr(0)
    gas_m, salt_n = Fr(0), Fr(0)
    eqs = []
    for s, n in ((X, a), (Y, b)):
        lhs, rhs = _acid_rx(s, acid, salt)
        k = coef(lhs, rhs)
        eqs.append(eqp(lhs, rhs)[1])
        need += n * Fr(k[acid], k[s])
        salt_n += n * Fr(k[salt], k[s])
        for g in ('H2', 'CO2'):
            if g in rhs:
                gas_m += n * Fr(k[g], k[s]) * M(g)
    nacid = need + Fr(rng.choice(range(1, 21)), 20)
    ws, ms = _nice_sol(rng, nacid, acid, (5, 8, 10, 12, 15, 20, 25))
    target = rng.choice(['salt', 'salt', 'acid'])
    total = m + ms - gas_m
    exact = (salt_n * M(salt) if target == 'salt' else (nacid - need) * M(acid)) / total * 100
    ans = rnd(exact, 1)
    rt = f'{ratio.numerator} : {ratio.denominator}'
    q = (f'Имеется смесь веществ {pretty(X)} и {pretty(Y)} ({NAME34[X]} и {NAME34[Y]}) массой {ru(m)} г, в которой '
         f'число атомов {ATOM_G[e1]} относится к числу атомов {ATOM_G[e2]} как {rt}. Смесь полностью растворили в '
         f'{ru(ms)} г {ws} %-ного раствора {_gw(acid)}. Рассчитайте массовую долю '
         f'{_gw(salt) if target == "salt" else _gw(acid)} в образовавшемся растворе. ' + KIM34 + '(Запишите число с точностью до десятых.)')
    e = f'Пусть n({pretty(X)}) = a, n({pretty(Y)}) = b: отношение атомов даёт a : b = {fmt(a / b, 3)}, масса смеси — ' \
        f'a = {fmt(a, 3)}, b = {fmt(b, 3)} моль. Масса раствора = {ru(m)} + {ru(ms)} − m(газов) = {fmt(total, 2)} г ⇒ ω ≈ {ans} %.'
    wrong = W([exact * total / (m + ms), exact * total / ms, exact / 2], 1)
    p = dict(X=X, Y=Y, acid=acid, salt=salt, els=[e1, e2], ratio=[ratio.numerator, ratio.denominator], m=str(m),
             ms=str(ms), ws=ws, target=target)
    steps = [(f'n({pretty(X)}), моль', sfmt(a, 3)), (f'n({pretty(Y)}), моль', sfmt(b, 3)),
             ('m(выделившихся газов), г', sfmt(gas_m, 2)), ('m(конечного раствора), г', sfmt(total, 2)),
             (f'ω({pretty(salt) if target == "salt" else pretty(acid)}), %', ans)]
    return pcard_s('ch-ege-34-atoms', q, ans, e, p=p, wrong=wrong, eqs=eqs, steps=steps)


HYD34_METALS = [('Fe', 'железных опилок', 'FeSO4'), ('Zn', 'цинковой пыли', 'ZnSO4'), ('Mg', 'магниевой стружки', 'MgSO4')]


def _hyd_calc(p):
    n0 = Fr(p['mh']) / Mi('CuSO4·5H2O')
    S0 = n0 * Mi('CuSO4') * 100 / Fr(p['w1'])
    met, msalt = p['metal'], p['msalt']
    nM = Fr(p['mM']) / Mi(met)
    nA = Fr(p['mA']) * Fr(p['wA']) / 100 / Mi('H2SO4')
    rest = nM - n0
    react = min(rest, nA)
    total = S0 + (n0 + react) * Mi(met) - n0 * Mi('Cu') + Fr(p['mA']) - react * Mi('H2')
    w = ((n0 + react) * Mi(msalt) if p['target'] == 'salt' else (nA - react) * Mi('H2SO4')) / total * 100
    return [(n0, 3), (S0, 2), (react, 3), (total, 2), (w, 1)]


_solve_34_hyd = _last(_hyd_calc)


@proto('ch-ege-34-hydrate', 'ЕГЭ', 34, 'Раствор кристаллогидрата, вытеснение металла, затем кислота',
       invariant='n(соли) = n(кристаллогидрата); масса раствора по заданной доле; металл вытесняет медь (избыток металла '
                 'затем растворяется в кислоте); масса раствора: + растворившийся металл − медь − водород + раствор кислоты',
       varies='металл (Fe, Zn, Mg), массы купороса и металла, доля исходного раствора, раствор серной кислоты (избыток или '
              'недостаток), что найти (доля соли или кислоты)',
       answer_rule='массовая доля, %, до десятых',
       mistakes=['массу кристаллогидрата приняли за массу соли', 'не учли, что медь выпадает из раствора',
                 'не прибавили массу растворившегося металла'],
       solve=_solve_34_hyd, kes=['1.11', '5.4', '5.6', '5.7'],
       fidelity=fid('в КИМ — развёрнутое решение; в тренажёре — число, %', 'как задание банка № 34 «Медный купорос '
                    'массой … растворили в воде и получили раствор с массовой долей соли …» — формулировка своя', 'В', 22,
                    'купорос 10–60 г, металл 3–20 г, кислота 50–300 г', 'медь не входит в раствор; избыток металла',
                    ['1.11', '5.4', '5.6', '5.7'], '4 балла в КИМ'))
def g34_hydrate(rng):
    met, mtxt, msalt = pick(rng, HYD34_METALS)
    n0 = Fr(rng.choice(range(2, 13)), 40)             # 0,05–0,3 моль
    mh = n0 * M('CuSO4·5H2O')
    w1 = pick(rng, [5, 8, 10, 12, 16, 20])
    S0 = n0 * M('CuSO4') * 100 / w1
    if S0 <= mh or not nice(S0, 2):
        raise Retry
    nM = n0 + Fr(rng.choice(range(1, 9)), 40)
    mM = nM * M(met)
    if not nice(mM, 2):
        raise Retry
    rest = nM - n0
    nA = rest * Fr(rng.choice([1, 2, 3, 4, 6, 8]), 4)
    wA, mA = _nice_sol(rng, nA, 'H2SO4', (Fr(49, 10), Fr(98, 10), 10, Fr(147, 10), Fr(196, 10), 20, Fr(245, 10)))
    if mA < 40:
        raise Retry
    target = 'salt' if nA <= rest or rng.random() < 0.6 else 'acid'
    p = dict(mh=str(mh), w1=w1, metal=met, msalt=msalt, mM=str(mM), mA=str(mA), wA=str(wA), target=target)
    react = min(rest, nA)
    total = S0 + (n0 + react) * M(met) - n0 * M('Cu') + mA - react * M('H2')
    exact = ((n0 + react) * M(msalt) if target == 'salt' else (nA - react) * M('H2SO4')) / total * 100
    ans = rnd(exact, 1)
    q = (f'Медный купорос (CuSO₄·5H₂O) массой {ru(mh)} г растворили в воде и получили раствор, массовая доля сульфата '
         f'меди(II) в котором равна {w1} %. В раствор внесли {ru(mM)} г {mtxt}; после окончания реакции к смеси прилили '
         f'{ru(mA)} г раствора серной кислоты с массовой долей {ru(wA)} %. Рассчитайте массовую долю '
         f'{_gw(msalt) if target == "salt" else "серной кислоты"} в конечном растворе. ' + KIM34 + '(Запишите число с точностью до десятых.)')
    e = f'n(CuSO₄) = {fmt(n0, 3)} моль; m(р-ра) = {fmt(S0, 2)} г; {pretty(met)} ({fmt(nM, 3)} моль) вытесняет медь, ' \
        f'остаётся {fmt(rest, 3)} моль металла; с кислотой ({fmt(nA, 3)} моль) реагирует {fmt(react, 3)} моль; ' \
        f'масса конечного раствора {fmt(total, 2)} г ⇒ ω ≈ {ans} %.'
    steps = [('n(CuSO₄), моль', sfmt(n0, 3)), ('m(исходного раствора CuSO₄), г', sfmt(S0, 2)),
             (f'n({pretty(met)}), растворившегося в кислоте, моль', sfmt(react, 3)),
             ('m(конечного раствора), г', sfmt(total, 2)),
             (f'ω({pretty(msalt) if target == "salt" else "H₂SO₄"}), %', ans)]
    wrong = W([exact * total / (total + n0 * M('Cu')), (n0 + react) * M(msalt) / (mh + mA + mM) * 100 if target == 'salt'
               else exact * 2, exact / 2], 1)
    eqs = [eqp([met, 'CuSO4'], [msalt, 'Cu'])[1], eqp([met, 'H2SO4'], [msalt, 'H2'])[1]]
    return pcard_s('ch-ege-34-hydrate', q, ans, e, p=p, wrong=wrong, eqs=eqs, steps=steps)


SOLUB34 = {  # соль: (растворимости, г на 100 г воды, при разных температурах; реакции с реагентом: (реагент, продукт в р-ре, осадок/газ))
    'Na2CO3': ([Fr(218, 10), Fr(307, 10), Fr(397, 10)], [('HCl', 'NaCl', 'CO2'), ('CaCl2', 'NaCl', 'CaCO3')]),
    'CuSO4': ([Fr(207, 10), Fr(25), Fr(285, 10)], [('NaOH', 'Na2SO4', 'Cu(OH)2')]),
    'BaCl2': ([Fr(358, 10), Fr(381, 10), Fr(408, 10)], [('Na2SO4', 'NaCl', 'BaSO4')]),
    'MgSO4': ([Fr(351, 10), Fr(389, 10), Fr(445, 10)], [('KOH', 'K2SO4', 'Mg(OH)2')]),
    'AgNO3': ([Fr(216), Fr(256), Fr(300)], [('NaCl', 'NaNO3', 'AgCl')]),
    'K2CO3': ([Fr(111), Fr(114), Fr(117)], [('HNO3', 'KNO3', 'CO2')]),
}


def _solub_rx(p):
    lhs = [p['salt'], p['reag']]
    rhs = [p['prod'], p['out']] + (['H2O'] if p['out'] == 'CO2' else [])
    return coef(lhs, rhs)


def _solub_calc(p):
    """По первой порции: осадок/газ → n соли → ω(насыщ.); масса всего раствора = W/(1 − ω); вторая порция → реакция."""
    k = _solub_rx(p)
    salt, out = p['salt'], p['out']
    n1 = Fr(p['pv1']) / (VM if out == 'CO2' else Mi(out)) * Fr(k[salt], k[out])
    wsat = n1 * Mi(salt) / Fr(p['m1'])
    sat = Fr(p['W']) / (1 - wsat)
    mp = sat - Fr(p['m1'])
    ns = mp * wsat / Mi(salt)
    out_m = ns * Fr(k[out], k[salt]) * Mi(out)
    total = mp + Fr(p['mr']) - out_m
    nr = Fr(p['mr']) * Fr(p['wr']) / 100 / Mi(p['reag'])
    if p['target'] == 'prod':
        w = ns * Fr(k[p['prod']], k[salt]) * Mi(p['prod']) / total * 100
    else:
        w = (nr - ns * Fr(k[p['reag']], k[salt])) * Mi(p['reag']) / total * 100
    return [(wsat * 100, 2), (mp, 2), (ns, 3), (total, 2), (w, 1)]


_solve_34_solub = _last(_solub_calc)


@proto('ch-ege-34-solub', 'ЕГЭ', 34, 'Насыщенный раствор (растворимость), порция раствора и реакция',
       invariant='по первой порции насыщенного раствора (осадок/газ) находят массовую долю соли в насыщенном растворе; '
                 'масса всего раствора = m(воды)/(1 − ω); вторая порция реагирует с раствором реагента, масса раствора '
                 'без осадка/газа',
       varies='соль (растворимость при разных температурах), масса воды, масса первой порции и её продукт, реагент, что найти',
       answer_rule='массовая доля, %, до десятых',
       mistakes=['приняли растворимость за массовую долю', 'не вычли осадок или газ', 'посчитали всю соль, а не порцию'],
       solve=_solve_34_solub, kes=['1.11', '5.6', '5.7'],
       fidelity=fid('в КИМ — развёрнутое решение; в тренажёре — число, %', 'как задания банка № 34 «Растворимость … при '
                    'некоторой температуре составляет … г на 100 г воды …» — формулировка своя', 'В', 22,
                    'растворимости справочные (20–40 °C), вода 100–400 г', 'растворимость ≠ массовая доля',
                    ['1.11', '5.6', '5.7'], '4 балла в КИМ'))
def g34_solub(rng):
    salt = pick(rng, list(SOLUB34))
    Ss, rx = SOLUB34[salt]
    S = pick(rng, Ss)
    reag, prod, out = pick(rng, rx)
    Wt = Fr(rng.choice(range(100, 401, 50)))
    sat = Wt * (100 + S) / 100
    wsat = S / (100 + S)
    k = coef([salt, reag], [prod, out] + (['H2O'] if out == 'CO2' else []))
    m1 = Fr(rng.choice(range(20, int(sat * Fr(2, 3)), 5)))
    n1 = m1 * wsat / M(salt)
    pv1 = n1 * Fr(k[out], k[salt]) * (VM if out == 'CO2' else M(out))
    pv1 = Fr(round(pv1 * (1000 if out == 'CO2' else 100)), 1000 if out == 'CO2' else 100)
    mp = sat - m1
    ns = mp * wsat / M(salt)
    need = ns * Fr(k[reag], k[salt])
    wr = pick(rng, [w for w in (5, 8, 10, 12, 15, 20, 25) if w_ok(reag, w)])
    mr = Fr(math.ceil(need * Fr(rng.choice([11, 12, 13, 15, 16, 18, 20]), 10) * M(reag) * 100 / wr))
    nr = mr * wr / 100 / M(reag)
    target = rng.choice(['prod', 'prod', 'reag'])
    out_m = ns * Fr(k[out], k[salt]) * M(out)
    total = mp + mr - out_m
    exact = (ns * Fr(k[prod], k[salt]) * M(prod) if target == 'prod' else (nr - need) * M(reag)) / total * 100
    ans = rnd(exact, 1)
    p = dict(salt=salt, reag=reag, prod=prod, out=out, W=str(Wt), m1=str(m1), pv1=str(pv1), mr=str(mr), wr=wr,
             target=target)
    steps = [('ω(соли) в насыщенном растворе, %', sfmt(wsat * 100, 2)), ('m(второй части раствора), г', sfmt(mp, 2)),
             (f'n({pretty(salt)}) во второй части, моль', sfmt(ns, 3)), ('m(конечного раствора), г', sfmt(total, 2)),
             (f'ω({pretty(prod) if target == "prod" else pretty(reag)}), %', ans)]
    if [v for _, v in steps] != [rs(v, d) for v, d in _solub_calc(p)]:
        raise Retry                 # данные первой порции округлены — шаги должны сходиться с пересчётом по условию
    got = f'выделилось {ru(pv1)} л (н.у.) газа' if out == 'CO2' else f'выпало {ru(pv1)} г осадка'
    q = (f'При некоторой температуре приготовили насыщенный раствор {_gw(salt)}, растворив соль в {ru(Wt)} г воды. '
         f'Раствор разделили на две части. К первой части массой {ru(m1)} г прилили избыток раствора {_gw(reag)}; при этом '
         f'{got}. Вторую часть смешали с {ru(mr)} г {wr} %-ного раствора {_gw(reag)}. Рассчитайте массовую долю '
         f'{_gw(prod) if target == "prod" else _gw(reag)} в образовавшемся растворе. ' + KIM34 +
         '(Запишите число с точностью до десятых.)')
    e = f'По первой части: n({pretty(salt)}) = {fmt(n1, 4)} моль, ω(насыщ.) = {fmt(wsat * 100, 2)} %; масса всего раствора ' \
        f'= {ru(Wt)}/(1 − ω) = {fmt(sat, 2)} г, вторая часть {fmt(mp, 2)} г; реакция с {pretty(reag)}, из раствора уходит ' \
        f'{pretty(out)} ({fmt(out_m, 2)} г) ⇒ ω ≈ {ans} %.'
    wrong = W([exact * total / (mp + mr), exact * (sat / mp), exact * 2], 1)
    return pcard_s('ch-ege-34-solub', q, ans, e, p=p, wrong=wrong, eq=eqp([salt, reag], [prod, out] + (['H2O'] if out == 'CO2' else []))[1],
                   steps=steps)


def _oleum_inv(p):
    m = Fr(p['m'])
    wd = Fr(p['wel']) / 100
    if p['el'] == 'O':      # 98a + 80b = m; 64a + 48b = ω·m
        det = Fr(98 * 48 - 80 * 64)
        a = (m * 48 - 80 * wd * m) / det
        b = (98 * wd * m - 64 * m) / det
    else:                   # 32a + 32b = ω·m
        tot = wd * m / 32
        a = (m - 80 * tot) / (98 - 80)
        b = tot - a
    nac = a + b
    salt = p['reag']
    nr = Fr(p['V']) * Fr(p['c']) / 1000
    left = (nr - nac) * Mi(salt)
    rest = m + Fr(p['V']) * Fr(p['rho']) - nac * Mi('BaSO4')
    F = left / (Fr(p['wf']) / 100)
    return [(nac, 3), (nac * Mi('BaSO4'), 2), (F, 1), (F - rest, 0)]


def _oleum_calc(p):
    if p['mode'] == 'inverse':
        return _oleum_inv(p)
    m, pr = Fr(p['m']), Fr(p['p'])
    n = m * (100 - pr) / 100 / Mi('H2SO4') + m * pr / 100 / Mi('SO3')
    W = Fr(p['W'])
    if p['mode'] == 'acid':
        return [(n, 3), (m + W, 2), (n * Mi('H2SO4') / (m + W) * 100, 1)]
    nr = Fr(p['mr']) * Fr(p['wr']) / 100 / Mi(p['reag'])
    if p['reag'] == 'KOH':
        total = m + W + Fr(p['mr'])
        val = n * Mi('K2SO4') if p['target'] == 'K2SO4' else (nr - 2 * n) * Mi('KOH')
        return [(n, 3), (2 * n, 3), (total, 2), (val / total * 100, 1)]
    total = m + W + Fr(p['mr']) - n * Mi('BaSO4')
    val = 2 * n * Mi('HCl') if p['target'] == 'HCl' else (nr - n) * Mi('BaCl2')
    return [(n, 3), (n * Mi('BaSO4'), 2), (total, 2), (val / total * 100, 1)]


_solve_34_oleum = _last(_oleum_calc)


@proto('ch-ege-34-oleum', 'ЕГЭ', 34, 'Олеум: растворение в воде и дальнейшая реакция',
       invariant='олеум = H₂SO₄ + SO₃; SO₃ + H₂O = H₂SO₄; n(H₂SO₄) общее; масса раствора = олеум + вода (+ раствор '
                 'реагента − осадок)',
       varies='масса олеума и доля свободного SO₃ (или доля атомов O/S), масса воды, второй раствор (KOH, BaCl₂, '
              'Ba(NO₃)₂), что найти: долю вещества или — как в демоверсии 2027 — объём воды по конечной доле соли',
       answer_rule='массовая доля, % (до десятых) или объём воды, мл (до целых)',
       mistakes=['не учли серную кислоту из SO₃', 'посчитали массу SO₃ как массу H₂SO₄', 'не вычли осадок BaSO₄'],
       solve=_solve_34_oleum, kes=['5.4', '5.6', '5.7'],
       fidelity=fid('в КИМ — развёрнутое решение; в тренажёре — число, %', 'как задание демоверсии 2027 № 34 (олеум + '
                    'раствор хлорида бария) — прямая задача, формулировка своя', 'В', 22, 'олеум 5–60 г, SO₃ 10–40 %, '
                    'растворы 100–500 г', 'SO₃ даёт дополнительную H₂SO₄', ['5.4', '5.6', '5.7'], '4 балла в КИМ'))
def g34_oleum(rng):
    pr = pick(rng, [10, 16, 20, 25, 30, 32, 40])
    m = Fr(rng.choice(range(5, 61)))
    n = m * (100 - pr) / 100 / M('H2SO4') + m * pr / 100 / M('SO3')
    Wt = Fr(rng.choice(range(50, 401, 10)))
    mode = rng.choice(['KOH', 'BaCl2', 'BaCl2', 'inverse', 'inverse'])
    if mode == 'inverse':      # как демоверсия 2027: по составу олеума и конечной доле соли найти объём воды
        a_, b_ = Fr(rng.randint(1, 10), 100), Fr(rng.randint(2, 20), 100)
        m = 98 * a_ + 80 * b_
        el = rng.choice(['O', 'S'])
        wel_exact = (16 * (4 * a_ + 3 * b_) if el == 'O' else 32 * (a_ + b_)) / m * 100
        wel = Fr(round(wel_exact * 100), 100)
        salt = rng.choice(['BaCl2', 'Ba(NO3)2'])
        c = Fr(rng.choice([15, 20, 24, 25, 28, 30, 35, 36, 40, 45]), 100)
        V = Fr(rng.choice([200, 250, 300, 350, 400, 600, 700, 750, 800]))
        w_s = c * M(salt) / 10                                  # ≈ массовая доля соли, %
        if not w_ok(salt, w_s):
            raise Retry
        rho = Fr(round((1 + Fr(9, 1000) * w_s) * 100), 100)     # реалистичная плотность раствора
        nac = a_ + b_
        if V * c / 1000 <= nac * Fr(11, 10):
            raise Retry
        Wt = Fr(rng.choice(range(50, 301, 10)))
        left = (V * c / 1000 - nac) * M(salt)
        F = m + Wt + V * rho - nac * M('BaSO4')
        wf = Fr(round(left / F * 10000), 100)
        if wf <= 0:
            raise Retry
        p = dict(mode='inverse', m=str(m), el=el, wel=str(wel), reag=salt, V=str(V), c=str(c), rho=str(rho), wf=str(wf))
        val = _oleum_inv(p)[-1][0]
        guard(val, 0, Fr(1, 5))
        if abs(val - Wt) > 1 or val <= 0:
            raise Retry
        ans = fmt(val, 0)
        F_ex = m + Wt + V * rho - nac * M('BaSO4')
        steps = [('n(H₂SO₄) после растворения олеума, моль', sfmt(nac, 3)), ('m(BaSO₄), г', sfmt(nac * M('BaSO4'), 2)),
                 ('m(конечного раствора), г', sfmt(F_ex, 1)), ('V(воды), мл', ans)]
        if [v for _, v in steps] != [rs(v, d) for v, d in _oleum_inv(p)]:
            raise Retry             # данные условия округлены — шаги должны совпадать с пересчётом по условию
        elw = 'атомов кислорода' if el == 'O' else 'атомов серы'
        q = (f'Олеум массой {ru(m)} г, в котором на долю {elw} приходится {ru(wel)} % массы, растворили в воде. Весь '
             f'полученный раствор прибавили к {ru(V)} мл раствора {_gw(salt)} с молярной концентрацией {ru(c)} моль/л '
             f'(плотность {ru(rho)} г/мл). После отделения осадка массовая доля {_gw(salt)} в растворе составила {ru(wf)} %. '
             f'Рассчитайте объём воды (мл), который использовали для растворения олеума. ' + KIM34 +
             '(Запишите число с точностью до целых.)')
        e = (f'По составу олеума: n(H₂SO₄) = {fmt(a_, 2)} моль, n(SO₃) = {fmt(b_, 2)} моль, всего H₂SO₄ после растворения '
             f'{fmt(nac, 2)} моль; осадок BaSO₄ {fmt(nac * M("BaSO4"), 2)} г; остаток соли {fmt(left, 2)} г; из доли соли '
             f'находим массу раствора и массу воды ≈ {ans} г (мл).')
        wrong = W([val + nac * M('BaSO4'), val - m, val + V * rho / 10], 0)
        eqs = [eqp(['SO3', 'H2O'], ['H2SO4'])[1], eqp(['H2SO4', salt], ['BaSO4', 'HCl' if salt == 'BaCl2' else 'HNO3'])[1]]
        return pcard_s('ch-ege-34-oleum', q, ans, e, p=p, wrong=wrong, eqs=eqs, steps=steps)
    if mode == 'acid':
        exact = n * M('H2SO4') / (m + Wt) * 100
        p = dict(m=str(m), p=pr, W=str(Wt), mode='acid')
        q = (f'Олеум массой {ru(m)} г, массовая доля оксида серы(VI) в котором равна {pr} %, растворили в {ru(Wt)} г воды. '
             f'Рассчитайте массовую долю серной кислоты в полученном растворе. ' + KIM34 + '(Запишите число с точностью до десятых.)')
        eqs = [eqp(['SO3', 'H2O'], ['H2SO4'])[1]]
        wrong = W([m * (100 - pr) / 100 / (m + Wt) * 100, n * M('H2SO4') / Wt * 100, m / (m + Wt) * 100], 1)
        mid = [('n(H₂SO₄) после растворения, моль', sfmt(n, 3)), ('m(раствора), г', sfmt(m + Wt, 2))]
    else:
        reag = 'KOH' if mode == 'KOH' else 'BaCl2'
        need = 2 * n if reag == 'KOH' else n
        nr = need * Fr(rng.choice([11, 12, 13, 15, 16, 18, 20]), 10)
        wr = pick(rng, [w for w in (5, 8, 10, 12, 15, 20) if w_ok(reag, w)])
        mr = Fr(math.ceil(nr * M(reag) * 100 / wr))
        nr = mr * wr / 100 / M(reag)
        target = pick(rng, ['K2SO4', 'KOH'] if reag == 'KOH' else ['HCl', 'BaCl2'])
        if reag == 'KOH':
            total = m + Wt + mr
            val = n * M('K2SO4') if target == 'K2SO4' else (nr - 2 * n) * M('KOH')
            mid = [('n(H₂SO₄) после растворения, моль', sfmt(n, 3)), ('n(KOH), вступившего в реакцию, моль', sfmt(2 * n, 3)),
                   ('m(конечного раствора), г', sfmt(total, 2))]
            eqs = [eqp(['SO3', 'H2O'], ['H2SO4'])[1], eqp(['H2SO4', 'KOH'], ['K2SO4', 'H2O'])[1]]
        else:
            total = m + Wt + mr - n * M('BaSO4')
            val = 2 * n * M('HCl') if target == 'HCl' else (nr - n) * M('BaCl2')
            mid = [('n(H₂SO₄) после растворения, моль', sfmt(n, 3)), ('m(BaSO₄), г', sfmt(n * M('BaSO4'), 2)),
                   ('m(конечного раствора), г', sfmt(total, 2))]
            eqs = [eqp(['SO3', 'H2O'], ['H2SO4'])[1], eqp(['H2SO4', 'BaCl2'], ['BaSO4', 'HCl'])[1]]
        exact = val / total * 100
        p = dict(m=str(m), p=pr, W=str(Wt), mode='react', reag=reag, mr=str(mr), wr=wr, target=target)
        tname = {'K2SO4': 'сульфата калия', 'KOH': 'гидроксида калия', 'HCl': 'хлороводорода', 'BaCl2': 'хлорида бария'}[target]
        q = (f'Порцию олеума массой {ru(m)} г (массовая доля свободного оксида серы(VI) {pr} %) растворили в {ru(Wt)} мл '
             f'воды. Полученный раствор прилили к {ru(mr)} г {wr} %-ного раствора {_gw(reag)}. Рассчитайте массовую '
             f'долю {tname} в образовавшемся растворе. ' + KIM34 + '(Запишите число с точностью до десятых.)')
        wrong = W([val / (m + Wt + mr) * 100 if reag == 'BaCl2' else exact * 2,
                   exact * (m + Wt + mr) / (Wt + mr), exact / 2], 1)
    if exact <= 0:
        raise Retry
    ans = rnd(exact, 1)
    e = f'n(H₂SO₄) = {ru(m)}·{100 - pr}/100/98 + {ru(m)}·{pr}/100/80 = {fmt(n, 4)} моль (SO₃ + H₂O = H₂SO₄) ⇒ ω ≈ {ans} %.'
    steps = mid + [('ω, %', ans)]
    return pcard_s('ch-ege-34-oleum', q, ans, e, p=p, wrong=wrong, eqs=eqs, steps=steps)


# ======================================================================= ОГЭ 18. Массовая доля элемента

OGE18 = {  # сюжет → [(формула, в чём (предл. п.), вводная фраза, элементы)]
    'salt': [
        ('NH4NO3', 'нитрате аммония', 'Нитрат аммония (аммиачная селитра) — одно из самых распространённых азотных удобрений.', ['N']),
        ('KNO3', 'нитрате калия', 'Калийная селитра — удобрение, в котором есть сразу два элемента питания растений.', ['K', 'N']),
        ('Ca(NO3)2', 'нитрате кальция', 'Кальциевую селитру вносят под овощные культуры весной.', ['N', 'Ca']),
        ('NaNO3', 'нитрате натрия', 'Натриевая (чилийская) селитра — природное азотное удобрение.', ['N', 'Na']),
        ('(NH4)2SO4', 'сульфате аммония', 'Сульфат аммония применяют как азотно-серное удобрение.', ['N', 'S']),
        ('CO(NH2)2', 'карбамиде (мочевине)', 'Карбамид — самое концентрированное твёрдое азотное удобрение.', ['N']),
        ('NH4H2PO4', 'дигидрофосфате аммония', 'Аммофос — сложное азотно-фосфорное удобрение.', ['N', 'P']),
        ('(NH4)2HPO4', 'гидрофосфате аммония', 'Диаммофос используют для подкормки ягодных культур.', ['N', 'P']),
        ('Ca(H2PO4)2', 'дигидрофосфате кальция', 'Двойной суперфосфат — фосфорное удобрение.', ['P', 'Ca']),
        ('CaHPO4', 'гидрофосфате кальция', 'Преципитат — фосфорное удобрение и кормовая добавка.', ['P', 'Ca']),
        ('KCl', 'хлориде калия', 'Хлорид калия — основное калийное удобрение.', ['K']),
        ('K2SO4', 'сульфате калия', 'Сульфат калия вносят под культуры, чувствительные к хлору.', ['K', 'S']),
        ('K2CO3', 'карбонате калия', 'Поташ (карбонат калия) содержится в древесной золе.', ['K']),
        ('KH2PO4', 'дигидрофосфате калия', 'Монофосфат калия — водорастворимое удобрение для теплиц.', ['K', 'P']),
        ('NaHCO3', 'гидрокарбонате натрия', 'Питьевую соду используют в кулинарии.', ['Na', 'C']),
        ('KMnO4', 'перманганате калия', 'Раствор перманганата калия применяют для дезинфекции.', ['K', 'Mn', 'O']),
        ('NaF', 'фториде натрия', 'Фторид натрия добавляют в зубные пасты.', ['F']),
        ('Na2PO3F', 'монофторофосфате натрия', 'Монофторофосфат натрия — фторсодержащий компонент зубных паст.', ['F', 'P']),
        ('KIO3', 'иодате калия', 'Иодат калия добавляют в поваренную соль для профилактики дефицита иода.', ['I']),
        ('CaCO3', 'карбонате кальция', 'Карбонат кальция входит в состав препаратов кальция.', ['Ca']),
        ('Na3PO4', 'фосфате натрия', 'Фосфат натрия используют как пищевую добавку.', ['P', 'Na']),
        ('NaNO2', 'нитрите натрия', 'Нитрит натрия — пищевая добавка в мясных продуктах.', ['N']),
        ('ZnSO4', 'сульфате цинка', 'Сульфат цинка входит в состав микроудобрений.', ['Zn']),
        ('CuSO4', 'сульфате меди(II)', 'Сульфат меди(II) применяют для обработки растений.', ['Cu']),
        ('H3BO3', 'борной кислоте', 'Борная кислота — антисептик и микроудобрение.', ['B']),
        ('AlPO4', 'фосфате алюминия', 'Фосфат алюминия — действующее вещество некоторых антацидов.', ['Al', 'P']),
        ('Mg(OH)2', 'гидроксиде магния', 'Гидроксид магния применяют при повышенной кислотности желудка.', ['Mg']),
        ('K2HPO4', 'гидрофосфате калия', 'Гидрофосфат калия — компонент жидких комплексных удобрений.', ['K', 'P']),
        ('Mg(NO3)2', 'нитрате магния', 'Нитрат магния используют для подкормки томатов.', ['Mg', 'N']),
        ('MgSO4', 'сульфате магния', 'Сульфат магния — магниевое удобрение.', ['Mg', 'S']),
        ('Na2SiO3', 'силикате натрия', 'Силикат натрия (жидкое стекло) применяют как клей и пропитку.', ['Si', 'Na']),
        ('Na2B4O7', 'тетраборате натрия', 'Тетраборат натрия используют при пайке металлов.', ['B']),
        ('NaClO', 'гипохлорите натрия', 'Гипохлорит натрия — действующее вещество отбеливателей.', ['Cl', 'Na']),
        ('Ca(ClO)2', 'гипохлорите кальция', 'Гипохлорит кальция применяют для дезинфекции воды в бассейнах.', ['Cl', 'Ca']),
        ('NH4Cl', 'хлориде аммония', 'Хлорид аммония (нашатырь) используют при пайке.', ['N', 'Cl']),
        ('CaSO4', 'сульфате кальция', 'Безводный сульфат кальция — осушитель в лабораториях.', ['Ca', 'S']),
        ('BaSO4', 'сульфате бария', 'Сульфат бария используют как рентгеноконтрастное вещество.', ['Ba']),
        ('AgNO3', 'нитрате серебра', 'Нитрат серебра (ляпис) — прижигающее средство.', ['Ag']),
    ],
    'hydrate': [
        ('FeSO4·7H2O', 'гептагидрате сульфата железа(II)', 'Гептагидрат сульфата железа(II) входит в препараты железа.', ['Fe']),
        ('FeCl2·4H2O', 'тетрагидрате хлорида железа(II)', 'Тетрагидрат хлорида железа(II) используют в лекарствах.', ['Fe']),
        ('CuSO4·5H2O', 'медном купоросе (CuSO₄·5H₂O)', 'Медный купорос применяют в садоводстве.', ['Cu', 'S']),
        ('ZnSO4·7H2O', 'гептагидрате сульфата цинка', 'Гептагидрат сульфата цинка — источник цинка в витаминах.', ['Zn']),
        ('MgSO4·7H2O', 'гептагидрате сульфата магния', 'Английскую (горькую) соль применяют в медицине.', ['Mg']),
        ('Na2B4O7·10H2O', 'декагидрате тетрабората натрия (буре)', 'Буру используют в средствах от насекомых.', ['B', 'Na']),
        ('CaSO4·2H2O', 'дигидрате сульфата кальция (гипсе)', 'Гипс применяют в строительстве и медицине.', ['Ca', 'S']),
        ('Na2CO3·10H2O', 'кристаллической соде (Na₂CO₃·10H₂O)', 'Кристаллическую соду используют как моющее средство.', ['Na']),
        ('KAl(SO4)2·12H2O', 'алюмокалиевых квасцах', 'Алюмокалиевые квасцы применяют как кровоостанавливающее средство.', ['Al', 'K']),
        ('CaCl2·6H2O', 'гексагидрате хлорида кальция', 'Хлорид кальция используют для приготовления растворов для инъекций.', ['Ca']),
        ('NiSO4·7H2O', 'гептагидрате сульфата никеля(II)', 'Сульфат никеля применяют в гальванических ваннах для никелирования.', ['Ni']),
        ('CoCl2·6H2O', 'гексагидрате хлорида кобальта(II)', 'Хлорид кобальта служит индикатором влажности в силикагеле.', ['Co']),
        ('Al2(SO4)3·18H2O', 'октадекагидрате сульфата алюминия', 'Сульфат алюминия используют для очистки питьевой воды.', ['Al', 'S']),
        ('Na2S2O3·5H2O', 'пентагидрате тиосульфата натрия', 'Тиосульфат натрия применяют как противоядие и в фотографии.', ['S', 'Na']),
        ('MnSO4·5H2O', 'пентагидрате сульфата марганца(II)', 'Сульфат марганца входит в состав микроудобрений.', ['Mn']),
        ('CaHPO4·2H2O', 'дигидрате гидрофосфата кальция', 'Дигидрат гидрофосфата кальция — кормовая добавка для скота.', ['Ca', 'P']),
        ('FeCl3·6H2O', 'гексагидрате хлорида железа(III)', 'Хлорид железа(III) используют для травления печатных плат.', ['Fe', 'Cl']),
        ('CuCl2·2H2O', 'дигидрате хлорида меди(II)', 'Хлорид меди(II) применяют как катализатор и протраву.', ['Cu', 'Cl']),
        ('Na3PO4·12H2O', 'додекагидрате фосфата натрия', 'Фосфат натрия входит в состав средств для смягчения воды.', ['P', 'Na']),
        ('(NH4)2Fe(SO4)2·6H2O', 'соли Мора ((NH₄)₂Fe(SO₄)₂·6H₂O)', 'Соль Мора используют в аналитической химии.', ['Fe', 'N']),
        ('Mg(NO3)2·6H2O', 'гексагидрате нитрата магния', 'Нитрат магния — водорастворимое магниевое удобрение.', ['Mg', 'N']),
        ('Ca(NO3)2·4H2O', 'тетрагидрате нитрата кальция', 'Тетрагидрат нитрата кальция — удобрение для гидропоники.', ['Ca', 'N']),
        ('BaCl2·2H2O', 'дигидрате хлорида бария', 'Дигидрат хлорида бария — лабораторный реактив на сульфат-ионы.', ['Ba', 'Cl']),
    ],
    'mineral': [
        ('CuFeS2', 'халькопирите (CuFeS₂)', 'Халькопирит — важнейший минерал медных руд.', ['Cu', 'Fe', 'S']),
        ('Cu2S', 'халькозине (Cu₂S)', 'Халькозин — медная руда.', ['Cu']),
        ('Cu2O', 'куприте (Cu₂O)', 'Куприт — красный минерал меди.', ['Cu']),
        ('Cu2(OH)2CO3', 'малахите (Cu₂(OH)₂CO₃)', 'Малахит — поделочный камень и медная руда.', ['Cu']),
        ('FeS2', 'пирите (FeS₂)', 'Пирит служит сырьём для получения серной кислоты.', ['Fe', 'S']),
        ('Fe3O4', 'магнетите (Fe₃O₄)', 'Магнетит — богатая железная руда.', ['Fe']),
        ('Fe2O3', 'гематите (Fe₂O₃)', 'Гематит (красный железняк) — железная руда.', ['Fe']),
        ('ZnS', 'сфалерите (ZnS)', 'Сфалерит (цинковая обманка) — главная руда цинка.', ['Zn', 'S']),
        ('PbS', 'галените (PbS)', 'Галенит — основной минерал свинца.', ['Pb']),
        ('CaCO3·MgCO3', 'доломите (CaCO₃·MgCO₃)', 'Доломитовую муку вносят для раскисления почв.', ['Ca', 'Mg']),
        ('CaF2', 'флюорите (CaF₂)', 'Флюорит используют в металлургии как флюс.', ['F', 'Ca']),
        ('Ca5(PO4)3F', 'фторапатите (Ca₅(PO₄)₃F)', 'Фторапатит — сырьё для производства фосфорных удобрений.', ['P', 'F']),
        ('Na3AlF6', 'криолите (Na₃AlF₆)', 'Криолит применяют при получении алюминия.', ['Al', 'F']),
        ('KCl·MgCl2·6H2O', 'карналлите (KCl·MgCl₂·6H₂O)', 'Карналлит — сырьё для получения магния и калийных удобрений.', ['K', 'Mg']),
        ('MnO2', 'пиролюзите (MnO₂)', 'Пиролюзит — основная марганцевая руда.', ['Mn']),
        ('Na2O·CaO·6SiO2', 'стекле состава Na₂O·CaO·6SiO₂', 'Обычное оконное стекло имеет состав Na₂O·CaO·6SiO₂.', ['Na', 'Ca', 'Si']),
        ('K2O·CaO·6SiO2', 'стекле состава K₂O·CaO·6SiO₂', 'Тугоплавкое химическое стекло имеет состав K₂O·CaO·6SiO₂.', ['K', 'Si']),
        ('K2O·PbO·6SiO2', 'стекле состава K₂O·PbO·6SiO₂', 'Хрусталь содержит оксид свинца: его состав K₂O·PbO·6SiO₂.', ['Pb', 'K', 'Si']),
        ('Al2O3·2SiO2·2H2O', 'каолините (Al₂O₃·2SiO₂·2H₂O)', 'Каолинит — основной минерал белой глины для фарфора.', ['Al', 'Si']),
        ('K2O·Al2O3·6SiO2', 'ортоклазе (K₂O·Al₂O₃·6SiO₂)', 'Ортоклаз (полевой шпат) входит в состав гранита.', ['K', 'Al', 'Si']),
        ('Cu3(CO3)2(OH)2', 'азурите (Cu₃(CO₃)₂(OH)₂)', 'Азурит — синий минерал меди.', ['Cu']),
        ('FeCO3', 'сидерите (FeCO₃)', 'Сидерит (шпатовый железняк) — железная руда.', ['Fe']),
        ('ZnCO3', 'смитсоните (ZnCO₃)', 'Смитсонит — руда цинка.', ['Zn']),
        ('MgCO3', 'магнезите (MgCO₃)', 'Магнезит используют для производства огнеупоров.', ['Mg']),
        ('CaSO4·2H2O', 'гипсе (CaSO₄·2H₂O)', 'Природный гипс — сырьё для строительных материалов.', ['Ca', 'S']),
        ('Cr2O3·FeO', 'хромите (FeO·Cr₂O₃)', 'Хромит — единственная промышленная руда хрома.', ['Cr', 'Fe']),
        ('Na2B4O7·10H2O', 'буре (Na₂B₄O₇·10H₂O)', 'Природная бура — сырьё для получения соединений бора.', ['B']),
    ],
}
EL_G = {'Ni': 'никеля', 'Co': 'кобальта', 'Ba': 'бария', 'Ag': 'серебра', 'Cr': 'хрома', 'N': 'азота', 'K': 'калия', 'Ca': 'кальция', 'Na': 'натрия', 'S': 'серы', 'P': 'фосфора', 'C': 'углерода',
        'Mn': 'марганца', 'O': 'кислорода', 'F': 'фтора', 'I': 'иода', 'Zn': 'цинка', 'Cu': 'меди', 'B': 'бора',
        'Al': 'алюминия', 'Mg': 'магния', 'Fe': 'железа', 'Pb': 'свинца', 'Si': 'кремния', 'H': 'водорода', 'Cl': 'хлора'}


def _w_el(f, el):
    return Fr(AR[el] * parse_formula(f)[el]) / M(f) * 100


def _solve_oge18(p):
    comp = parse_formula(p['f'])
    return rs(Fr(AR[p['el']]) * comp[p['el']] * 100 / Mi(p['f']), p['dec'])


def _g_oge18(rng, pid, key):
    f, prep, intro, els = pick(rng, OGE18[key])
    el = pick(rng, els)
    dec = rng.choice([0, 0, 1, 1, 2])
    w = _w_el(f, el)
    ans = rnd(w, dec)
    fp = '' if pretty(f) in prep else f' ({pretty(f)})'
    ask = pick(rng, [f'Вычислите массовую долю {EL_G[el]} (в процентах) в {prep}{fp}.',
                     f'Определите, какую долю (в процентах) от массы вещества {pretty(f)} составляет масса {EL_G[el]}.',
                     f'Какова массовая доля элемента {EL_G[el]} в этом веществе ({pretty(f)})? Ответ выразите в процентах.'])
    q = f'{intro} {ask} Запишите число с точностью до {PREC[dec]}.'
    e = f'M({pretty(f)}) = {ru(M(f))} г/моль; ω({el}) = {parse_formula(f)[el]}·{ru(AR[el])}/{ru(M(f))}·100 % ≈ {ans} %.'
    wrong = W([Fr(AR[el]) / M(f) * 100, Fr(parse_formula(f)[el], sum(parse_formula(f).values())) * 100, 100 - w], dec)
    return pcard(pid, q, ans, e, p=dict(f=f, el=el, dec=dec), wrong=wrong)


@proto('ch-oge-18-salt', 'ОГЭ', 18, 'Массовая доля элемента в удобрении, соли или пищевой добавке',
       invariant='ω(Э) = n·Ar(Э)/Mr(вещества)·100 %',
       varies='вещество (селитры, фосфаты, калийные соли, соли для медицины и быта), элемент, точность',
       answer_rule='ω в %, с точностью до целых/десятых/сотых',
       mistakes=['не умножили Ar на индекс', 'взяли долю по числу атомов', 'ошиблись в Mr'],
       solve=_solve_oge18, kes=['1.4', '7.1'],
       fidelity=fid('число, %, точность как указано', 'как зад. 18 демоверсии ОГЭ 2027: вводная фраза о веществе и '
                    '«Вычислите в процентах массовую долю … Запишите число с точностью до …»', 'Б', 5,
                    'вещества банка: нитраты, фосфаты, сульфаты, KMnO₄, фториды', 'индекс элемента', ['1.4', '7.1'],
                    '1 балл'))
def goge18_salt(rng):
    return _g_oge18(rng, 'ch-oge-18-salt', 'salt')


@proto('ch-oge-18-hydrate', 'ОГЭ', 18, 'Массовая доля элемента в кристаллогидрате (лекарство, бытовое средство)',
       invariant='Mr кристаллогидрата включает кристаллизационную воду; ω(Э) = n·Ar/Mr·100 %',
       varies='кристаллогидрат (купоросы, бура, гипс, квасцы, препараты железа), элемент, точность',
       answer_rule='ω в %',
       mistakes=['не учли воду в молярной массе', 'умножили Mr воды не на число молекул'],
       solve=_solve_oge18, kes=['1.4', '7.1'],
       fidelity=fid('число, %', 'как демоверсия ОГЭ 2027 (FeSO₄·7H₂O в препарате железа)', 'Б', 5,
                    'кристаллогидраты банка (FeSO₄·7H₂O, FeCl₂·4H₂O, бура)', 'вода в составе кристаллогидрата',
                    ['1.4', '7.1'], '1 балл'))
def goge18_hydrate(rng):
    return _g_oge18(rng, 'ch-oge-18-hydrate', 'hydrate')


@proto('ch-oge-18-mineral', 'ОГЭ', 18, 'Массовая доля элемента в минерале или стекле',
       invariant='Mr считают по формуле минерала (стекла, записанного через оксиды); ω(Э) = n·Ar/Mr·100 %',
       varies='минерал (халькопирит, малахит, доломит, фторапатит, карналлит …) или стекло, элемент, точность',
       answer_rule='ω в %',
       mistakes=['для стекла не сложили массы всех оксидов', 'не учли число атомов элемента в формуле'],
       solve=_solve_oge18, kes=['1.4', '7.1'],
       fidelity=fid('число, %', 'как в банке ОГЭ (стекло «указанного состава», халькопирит)', 'Б', 5,
                    'минералы и стёкла банка', 'формула через оксиды', ['1.4', '7.1'], '1 балл'))
def goge18_mineral(rng):
    return _g_oge18(rng, 'ch-oge-18-mineral', 'mineral')


# ======================================================================= ОГЭ 19. Практический расчёт по тексту

def _w_round(f, el, dec):
    return Fr(fmt(_w_el(f, el), dec).replace(',', '.'))


def _w_round_i(f, el, dec):
    return Fr(rs(Fr(AR[el]) * parse_formula(f)[el] * 100 / Mi(f), dec).replace(',', '.'))


DOSE19 = [  # (формула, название (род. п.), что (им. п.), элемент, масса вещества в единице, мг, единица, приёмов в сутки)
    ('FeSO4·7H2O', 'гептагидрата сульфата железа(II)', 'капсула', 'Fe', [150, 200, 250, 300], 'капсуле'),
    ('FeCl2·4H2O', 'тетрагидрата хлорида железа(II)', 'капсула', 'Fe', [100, 150, 200, 250], 'капсуле'),
    ('ZnSO4·7H2O', 'гептагидрата сульфата цинка', 'таблетка', 'Zn', [20, 30, 40, 50, 60], 'таблетке'),
    ('CaCO3', 'карбоната кальция', 'таблетка', 'Ca', [250, 400, 500, 600, 750, 1000], 'таблетке'),
    ('MgSO4·7H2O', 'гептагидрата сульфата магния', 'таблетка', 'Mg', [100, 150, 200, 250], 'таблетке'),
    ('KI', 'иодида калия', 'таблетка', 'I', [Fr(1, 10), Fr(13, 100), Fr(2, 10), Fr(26, 100)], 'таблетке'),
    ('NaF', 'фторида натрия', 'таблетка', 'F', [Fr(11, 10), Fr(22, 10), Fr(5, 2)], 'таблетке'),
    ('CaHPO4', 'гидрофосфата кальция', 'таблетка', 'Ca', [100, 150, 200, 250, 300], 'таблетке'),
    ('CuSO4', 'сульфата меди(II)', 'таблетка', 'Cu', [2, 3, 4, 5], 'таблетке'),
]
AGRO19 = [  # (формула, название удобрения (вин. п.), элемент)
    ('NH4NO3', 'аммиачную селитру (NH₄NO₃)', 'N'), ('KNO3', 'калийную селитру (KNO₃)', 'K'),
    ('Ca(NO3)2', 'кальциевую селитру (Ca(NO₃)₂)', 'N'), ('K2SO4', 'сульфат калия (K₂SO₄)', 'K'),
    ('KCl', 'хлорид калия (KCl)', 'K'), ('Ca(H2PO4)2', 'двойной суперфосфат (Ca(H₂PO₄)₂)', 'P'),
    ('(NH4)2HPO4', 'диаммофос ((NH₄)₂HPO₄)', 'N'), ('CO(NH2)2', 'карбамид (CO(NH₂)₂)', 'N'),
    ('K2CO3', 'поташ (K₂CO₃)', 'K'), ('CaCO3·MgCO3', 'доломитовую муку (CaCO₃·MgCO₃)', 'Mg'),
]
NORM19 = {'Fe': [10, 12, 14, 15, 18, 20], 'Zn': [8, 10, 12, 15], 'Ca': [200, 250, 300, 400, 500, 600],
          'Mg': [100, 150, 200, 250, 300], 'I': [Fr(1, 10), Fr(15, 100), Fr(2, 10)], 'F': [1, Fr(3, 2), 2],
          'Cu': [1, Fr(3, 2), 2]}
RAW19 = [  # (формула, название (род. п.), элемент, единица)
    ('CuFeS2', 'халькопирита', 'Cu', 'кг'), ('Fe3O4', 'магнетита', 'Fe', 'т'), ('Fe2O3', 'гематита', 'Fe', 'т'),
    ('ZnS', 'сфалерита', 'Zn', 'кг'), ('PbS', 'галенита', 'Pb', 'кг'), ('Cu2S', 'халькозина', 'Cu', 'кг'),
    ('Na2O·CaO·6SiO2', 'стекла состава Na₂O·CaO·6SiO₂', 'Si', 'кг'), ('K2O·PbO·6SiO2', 'хрусталя состава K₂O·PbO·6SiO₂', 'Pb', 'кг'),
    ('Na3AlF6', 'криолита', 'Al', 'кг'), ('Cu2(OH)2CO3', 'малахита', 'Cu', 'кг'),
]


def _solve_oge19(p):
    w = _w_round_i(p['f'], p['el'], p['d18'])
    t = p['type']
    if t == 'dose':
        x = Fr(p['m']) * Fr(p['k']) * Fr(p['days']) * w / 100
    elif t == 'dose_inv':
        x = Fr(p['norm']) / Fr(p['k']) / (w / 100)
    elif t == 'agro':
        x = Fr(p['norm']) * Fr(p['S']) / (w / 100) / Fr(p['div'])
    elif t == 'raw':
        x = Fr(p['mel']) / (w / 100)
    elif t == 'raw_el':
        x = Fr(p['mraw']) * w / 100
    else:
        x = Fr(p['m']) / Fr(p['V']) * Fr(p['V1']) * w / 100
    return rs(x, p['dec'])


def _intro18(f, el, d18):
    return f'Массовую долю {EL_G[el]} в {pretty(f)} предварительно вычислите в процентах с точностью до {PREC[d18]} и ' \
           f'используйте полученное значение в расчёте.'


@proto('ch-oge-19-dose', 'ОГЭ', 19, 'Масса элемента, получаемого с лекарственным препаратом (и обратная задача)',
       invariant='m(Э) = m(вещества)·ω(Э); ω берут из задания 18 с указанной там точностью',
       varies='препарат (соли железа, цинка, кальция, магния, иода, фтора), масса вещества в таблетке, число таблеток, '
              'срок; обратная задача — масса вещества в таблетке по суточной норме элемента',
       answer_rule='масса в мг (г) с точностью, указанной в условии',
       mistakes=['использовали массу таблетки вместо массы действующего вещества', 'не учли число приёмов/дней',
                 'взяли точное значение ω вместо округлённого в задании 18'],
       solve=_solve_oge19, kes=['1.4', '7.1', '6.2'],
       fidelity=fid('число, мг или г, точность как указано', 'как зад. 19 демоверсии ОГЭ 2027 (капсула с FeSO₄·7H₂O, '
                    'масса железа в сутки) — связка с № 18 указана в условии', 'Б', 5, 'массы 0,1–1000 мг, 1–3 приёма, '
                    'до 30 дней', 'округлённая ω из № 18', ['1.4', '7.1', '6.2'], '1 балл'))
def goge19_dose(rng):
    f, gname, unit, el, masses, unit_p = pick(rng, DOSE19)
    d18 = rng.choice([0, 1])
    w = _w_round(f, el, d18)
    dec = rng.choice([0, 1, 2])
    if rng.random() < 0.65:
        m = Fr(pick(rng, masses))
        k = rng.choice([1, 2, 3])
        days = rng.choice([1, 1, 7, 10, 14, 30])
        x = m * k * days * w / 100
        period = {1: 'в сутки', 7: 'за неделю', 14: 'за две недели'}.get(days, f'за {days} дней')
        q = (f'В каждой {unit_p} препарата содержится {ru(m)} мг {gname}; остальное — вещества, не содержащие {EL_G[el]}. '
             f'Препарат принимают по {("одной таблетке" if unit == "таблетка" else "одной капсуле") if k == 1 else str(k) + (" таблетки" if unit == "таблетка" else " капсулы")} '
             f'в сутки. Какую массу {EL_G[el]} (в миллиграммах) получает человек {period}? {_intro18(f, el, d18)} '
             f'Запишите число с точностью до {PREC[dec]}.')
        p = dict(type='dose', f=f, el=el, d18=d18, m=str(m), k=k, days=days, dec=dec)
        e = f'ω({el}) ≈ {fmt(w, d18)} %; m({el}) = {ru(m)}·{k}·{days}·{fmt(w, d18)}/100 ≈ {rnd(x, dec)} мг.'
        wrong = W([m * k * days, m * w / 100, x * 100 / w if w else None], dec)
    else:
        norm = Fr(pick(rng, NORM19[el]))
        k = rng.choice([1, 2, 3])
        x = norm / k / (w / 100)
        q = (f'Для восполнения дефицита {EL_G[el]} врач рекомендовал получать с препаратом {ru(norm)} мг {EL_G[el]} в сутки. '
             f'Действующее вещество препарата — {pretty(f)}; принимать его нужно по {k} {"таблетке" if k == 1 else "таблетки"} '
             f'в сутки. Вычислите массу {gname} (в миллиграммах), которую должна содержать одна таблетка. '
             f'{_intro18(f, el, d18)} Запишите число с точностью до {PREC[dec]}.').replace('по 1 таблетке', 'по одной таблетке')
        p = dict(type='dose_inv', f=f, el=el, d18=d18, norm=str(norm), k=k, dec=dec)
        e = f'ω({el}) ≈ {fmt(w, d18)} %; на одну таблетку {ru(norm)}/{k} мг {el}; m(в-ва) = m({el})/ω ≈ {rnd(x, dec)} мг.'
        wrong = W([norm / (w / 100), norm / k * w / 100, norm / k], dec)
    ans = rnd(x, dec)
    return pcard('ch-oge-19-dose', q, ans, e, p=p, wrong=wrong)


@proto('ch-oge-19-agro', 'ОГЭ', 19, 'Масса удобрения для участка по норме внесения элемента (и корма для животных)',
       invariant='m(удобрения) = норма(Э)·S/ω(Э); ω из задания 18 с указанной точностью',
       varies='удобрение (селитры, фосфаты, калийные соли, карбамид, доломит), норма на 1 или 10 м², площадь, единицы',
       answer_rule='масса в г или кг с точностью, указанной в условии',
       mistakes=['умножили на ω вместо деления', 'не перевели г в кг', 'норма на 10 м² принята как на 1 м²'],
       solve=_solve_oge19, kes=['1.4', '7.1', '6.2'],
       fidelity=fid('число, г или кг', 'как в банке ОГЭ: «… из расчёта … г калия на 10 м². Вычислите, сколько граммов … '
                    'надо внести на участок …» — формулировка своя', 'Б', 5, 'нормы 2–50 г/м², площади 10–400 м²',
                    'деление на ω; единицы', ['1.4', '7.1', '6.2'], '1 балл'))
def goge19_agro(rng):
    f, gname, el = pick(rng, AGRO19)
    d18 = rng.choice([0, 1])
    w = _w_round(f, el, d18)
    div = rng.choice([1, 1, 10])
    norm = Fr(rng.choice([2, 3, 4, 5, 6, 8, 10, 12, 15, 20]) * div)       # как в банке: до 20 г на 1 м² (200 г на 10 м²)
    S = Fr(rng.choice([10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 120, 150, 200, 250, 300, 400]))
    x = norm * S / (w / 100) / div
    kg = x >= 1000
    dec = (rng.choice([0, 1]) if x >= 100 else 1) if not kg else 1
    if kg:
        x = x / 1000
    ans = rnd(x, dec)
    q = (f'Под плодовые деревья вносят {gname} из расчёта {ru(norm)} г {EL_G[el]} на '
         f'{"1 м²" if div == 1 else "10 м²"} площади. Какую массу удобрения (в {"килограммах" if kg else "граммах"}) нужно внести на участок площадью '
         f'{ru(S)} м²? {_intro18(f, el, d18)} Запишите число с точностью до {PREC[dec]}.')
    if f == 'CaCO3·MgCO3':
        q = q.replace('Под плодовые деревья вносят', 'Для раскисления почвы и восполнения магния вносят')
    if rng.random() < 0.3:
        q = q.replace('Под плодовые деревья', 'Под картофель').replace('площади', 'поля')
    p = dict(type='agro', f=f, el=el, d18=d18, norm=str(norm * (Fr(1, 1000) if kg else 1)), S=str(S), div=div, dec=dec)
    e = f'ω({el}) ≈ {fmt(w, d18)} %; m({el}) = {ru(norm)}·{ru(S)}/{div} г; m(удобрения) = m({el})/ω ≈ {ans} {"кг" if kg else "г"}.'
    wrong = W([x * (w / 100) ** 2, x * div if div > 1 else x * 10, norm * S * (w / 100) / div / (1000 if kg else 1)], dec)
    return pcard('ch-oge-19-agro', q, ans, e, p=p, wrong=wrong)


@proto('ch-oge-19-raw', 'ОГЭ', 19, 'Масса минерала (стекла) по массе элемента и обратно',
       invariant='m(минерала) = m(Э)/ω(Э); m(Э) = m(минерала)·ω(Э); ω из задания 18',
       varies='руда или стекло, элемент, масса, прямая или обратная задача, единицы (кг, т)',
       answer_rule='масса с точностью, указанной в условии',
       mistakes=['умножили вместо деления', 'использовали неокруглённую ω'],
       solve=_solve_oge19, kes=['1.4', '7.1', '6.2'],
       fidelity=fid('число, кг или т', 'как в банке ОГЭ: «Вычислите массу стекла, если в нём содержится 15,3 кг свинца»; '
                    '«… массу халькопирита для получения 40 кг меди»', 'Б', 5, 'массы 1–500 кг (т)', 'деление на ω',
                    ['1.4', '7.1', '6.2'], '1 балл'))
def goge19_raw(rng):
    f, gname, el, unit = pick(rng, RAW19)
    d18 = rng.choice([0, 1])
    w = _w_round(f, el, d18)
    dec = rng.choice([0, 1])
    if rng.random() < 0.6:
        mel = Fr(rng.choice(list(range(5, 501, 5)) + [Fr(k, 10) for k in range(15, 200, 7)]))
        x = mel / (w / 100)
        q = (f'Какая масса {gname} (в {"тоннах" if unit == "т" else "килограммах"}) содержит {ru(mel)} {unit} {EL_G[el]}? '
             f'{_intro18(f, el, d18)} Запишите число с точностью до {PREC[dec]}.')
        p = dict(type='raw', f=f, el=el, d18=d18, mel=str(mel), dec=dec)
        wrong = W([mel * w / 100, mel / w, mel * 100 / (100 - w)], dec)
    else:
        mraw = Fr(rng.choice(list(range(10, 1001, 10))))
        x = mraw * w / 100
        q = (f'Сколько {"тонн" if unit == "т" else "килограммов"} {EL_G[el]} содержится в {ru(mraw)} {unit} {gname}? '
             f'{_intro18(f, el, d18)} Запишите число с точностью до {PREC[dec]}.')
        p = dict(type='raw_el', f=f, el=el, d18=d18, mraw=str(mraw), dec=dec)
        wrong = W([mraw / (w / 100), mraw * (100 - w) / 100, mraw * w], dec)
    ans = rnd(x, dec)
    e = f'ω({el}) ≈ {fmt(w, d18)} % ⇒ {ans} {unit}.'
    return pcard('ch-oge-19-raw', q, ans, e, p=p, wrong=wrong)


SOL19 = [  # (формула, название (род. п.), элемент, сюжет)
    ('KMnO4', 'перманганата калия', 'Mn', 'Для подкормки растений'), ('KMnO4', 'перманганата калия', 'K', 'Для дезинфекции семян'),
    ('CuSO4', 'сульфата меди(II)', 'Cu', 'Для опрыскивания винограда'), ('ZnSO4', 'сульфата цинка', 'Zn', 'Для некорневой подкормки'),
    ('H3BO3', 'борной кислоты', 'B', 'Для опрыскивания цветущих томатов'), ('Ca(NO3)2', 'нитрата кальция', 'Ca', 'Для полива рассады'),
    ('MgSO4', 'сульфата магния', 'Mg', 'Для подкормки картофеля'), ('KNO3', 'нитрата калия', 'K', 'Для подкормки огурцов'),
]


@proto('ch-oge-19-sol', 'ОГЭ', 19, 'Масса элемента в заданном объёме рабочего раствора',
       invariant='концентрация вещества в растворе (г/л) × объём × ω(Э); ω из задания 18',
       varies='вещество (перманганат калия, купорос, борная кислота, соли кальция, магния), сюжет, объёмы',
       answer_rule='масса в г (мг) с точностью, указанной в условии',
       mistakes=['не пересчитали на нужный объём', 'забыли умножить на ω(Э)'],
       solve=_solve_oge19, kes=['1.4', '7.1', '6.2'],
       fidelity=fid('число, г', 'как в банке ОГЭ: «Для подкормки растений 2 г перманганата калия растворяют в 10 л воды. '
                    'Вычислите массу марганца в 1 л раствора» — формулировка своя', 'Б', 5, 'навески 0,5–50 г, объёмы 1–20 л',
                    'пропорция по объёму', ['1.4', '7.1', '6.2'], '1 балл'))
def goge19_sol(rng):
    f, gname, el, story = pick(rng, SOL19)
    d18 = rng.choice([0, 1])
    w = _w_round(f, el, d18)
    m = Fr(rng.choice([Fr(1, 2), 1, 2, 3, 5, 10, 15, 20, 25, 50]))
    V = Fr(rng.choice([1, 2, 5, 8, 10, 12, 20]))
    V1 = Fr(rng.choice([Fr(1, 2), 1, 2, 3, 5]))
    if V1 >= V:
        raise Retry
    x = m / V * V1 * w / 100
    if x < Fr(1, 10):
        raise Retry
    dec = 2 if x < 1 else rng.choice([1, 2])
    ans = rnd(x, dec)
    q = (f'{story} {ru(m)} г {gname} растворяют в {ru(V)} л воды (объём раствора считать равным объёму воды). Какая масса '
         f'{EL_G[el]} (в граммах) содержится в {ru(V1)} л такого раствора? {_intro18(f, el, d18)} Запишите число с точностью '
         f'до {PREC[dec]}.')
    p = dict(type='sol', f=f, el=el, d18=d18, m=str(m), V=str(V), V1=str(V1), dec=dec)
    e = f'В {ru(V1)} л — {ru(m)}·{ru(V1)}/{ru(V)} г {pretty(f)}; ω({el}) ≈ {fmt(w, d18)} % ⇒ {ans} г.'
    wrong = W([m * w / 100, m / V * V1, m * V1 * w / 100], dec)
    return pcard('ch-oge-19-sol', q, ans, e, p=p, wrong=wrong)


# ======================================================================= ОГЭ 22. Расчёт по уравнению с раствором

def _oge22_amounts(rng, f, ws=(2, 4, 5, 6, 8, 10, 12, 15, 16, 20, 25)):
    """n вещества в растворе и «круглые» масса раствора и доля (как в банке ОГЭ)."""
    for _ in range(40):
        n = Fr(rng.choice(range(1, 61)), rng.choice([100, 50, 20]))
        w = pick(rng, ws)
        if not w_ok(f, w):
            w = pick(rng, [x for x in (Fr(1, 2), 1, 2, 3) if w_ok(f, x)] or [Fr(1, 10)])
        m = n * M(f) * 100 / w
        if nice(m, 1) and 10 <= m <= 600:
            return n, w, m
    raise Retry


def _oge22_calc(p):
    """Шаги как в критериях ОГЭ № 22 (после уравнения): масса/количество вещества → количество по уравнению → ответ."""
    k = coef(p['lhs'], p['rhs'])
    t = p['type']
    if t in ('precip', 'gas'):
        ms = Fr(p['m']) * Fr(p['w']) / 100
        n = ms / Mi(p['sol'])
        x = n * Fr(k[p['f']], k[p['sol']])
        return [(ms, 2), (n, 3), (x, 3), (x * (VM if t == 'gas' else Mi(p['f'])), 2)]
    if t in ('omega', 'msol'):
        nf = Fr(p['pv']) / (VM if p['fby'] == 'V' else Mi(p['f']))
        ns = nf * Fr(k[p['sol']], k[p['f']])
        ms = ns * Mi(p['sol'])
        last = ms / Fr(p['m']) * 100 if t == 'omega' else ms * 100 / Fr(p['w'])
        return [(nf, 3), (ns, 3), (ms, 2), (last, 2)]
    ms = Fr(p['m']) * Fr(p['w']) / 100
    n = ms / Mi(p['sol'])
    nr = n * Fr(k[p['r']], k[p['sol']])
    return [(ms, 2), (n, 3), (nr, 3), (nr * (VM if p['rby'] == 'V' else Mi(p['r'])), 2)]


_solve_oge22 = _last(_oge22_calc)


KIM22 = ('В ответе запишите уравнение реакции, о которой идёт речь в условии задачи, и приведите все необходимые '
         'вычисления (указывайте единицы измерения искомых физических величин).')


def _ans22(x):
    if not nice(x, 2) or x <= 0:
        raise Retry
    return fmt(x)


@proto('ch-oge-22-precip', 'ОГЭ', 22, 'Масса осадка при действии избытка реагента на раствор с заданной долей',
       invariant='m(в-ва) = m(р-ра)·ω; n = m/M; n(осадка) по уравнению; m(осадка) = n·M',
       varies='реакция осаждения (гидроксиды, сульфат бария, хлорид серебра, карбонаты, фосфаты, сульфид меди), масса и '
              'доля раствора',
       answer_rule='масса осадка, г (точное значение)',
       mistakes=['массу раствора подставили как массу вещества', 'не учли коэффициенты', 'M осадка вместо M вещества'],
       solve=_solve_oge22, kes=['7.1', '7.2'],
       fidelity=fid('в ОГЭ — развёрнутый ответ (3 балла: уравнение, n, масса); в тренажёре — число, г', 'как зад. 22 '
                    'демоверсии ОГЭ 2027 (300 г 8 %-ного CuSO₄ + избыток NaOH) — формулировка своя', 'В', 10,
                    'массы растворов 10–800 г, доли 2–25 % — как в банке', 'масса вещества в растворе',
                    ['7.1', '7.2'], '3 балла в КИМ'))
def goge22_precip(rng):
    r = pick(rng, [x for x in D.SOLUTION if x['calc']['kind'] == 'precip'])
    c = r['calc']
    k = coef(r['lhs'], r['rhs'])
    n, w, m = _oge22_amounts(rng, c['sol'])
    x = n * Fr(k[c['f']], k[c['sol']]) * M(c['f'])
    ans = _ans22(x)
    q = rng.choice([f'К раствору {gen(c["sol"])} массой {ru(m)} г (массовая доля растворённого вещества — {w} %) прилили '
                    f'избыток раствора {gen(c["ex"])}. Найдите массу выпавшего осадка.',
                    f'В {ru(m)} г {w} %-ного раствора {gen(c["sol"])} понемногу добавляли раствор {gen(c["ex"])}, пока '
                    f'осадок не перестал образовываться. Какова масса полученного осадка?'])
    q += ' ' + KIM22 + ' В тренажёре введите массу осадка в граммах.'
    eqs, eq = eqp(r['lhs'], r['rhs'])
    e = f'{eqs}; m({pretty(c["sol"])}) = {ru(m)}·{w}/100 = {ru(m * w / 100)} г; n = {ru(n)} моль; ' \
        f'n({pretty(c["f"])}) = {ru(n * Fr(k[c["f"]], k[c["sol"]]))} моль; m = {ans} г.'
    wrong = W([m / M(c['sol']) * Fr(k[c['f']], k[c['sol']]) * M(c['f']), n * M(c['f']), m * w / 100], 2)
    nf_ = n * Fr(k[c['f']], k[c['sol']])
    steps = [(f'm({pretty(c["sol"])}) в растворе, г', sfmt(m * w / 100, 2)), (f'n({pretty(c["sol"])}), моль', sfmt(n, 3)),
             (f'n({pretty(c["f"])}), моль', sfmt(nf_, 3)), (f'm({pretty(c["f"])}), г', ans)]
    return pcard_s('ch-oge-22-precip', q, ans, e, p=dict(type='precip', lhs=r['lhs'], rhs=r['rhs'], sol=c['sol'], f=c['f'],
                                                       m=str(m), w=w), wrong=wrong, eq=eq, steps=steps)


@proto('ch-oge-22-gas', 'ОГЭ', 22, 'Объём газа при реакции раствора с заданной долей',
       invariant='m(в-ва) = m(р-ра)·ω; n(газа) по уравнению; V = n·22,4',
       varies='реакция с выделением газа (карбонаты + кислота, металл + кислота, сульфид/сульфит + кислота, соль аммония '
              '+ щёлочь), масса и доля раствора',
       answer_rule='объём газа (н.у.), л',
       mistakes=['не учли коэффициенты', 'объём через молярную массу'],
       solve=_solve_oge22, kes=['7.1', '7.2'],
       fidelity=fid('в ОГЭ — развёрнутый ответ; в тренажёре — число, л', 'КИМ-стиль «…поместили избыток цинка. '
                    'Вычислите объём выделившегося газа (н.у.)» — формулировка своя', 'В', 10, 'как в банке (73 г 5 %-ной '
                    'HCl)', 'коэффициенты', ['7.1', '7.2'], '3 балла в КИМ'))
def goge22_gas(rng):
    r = pick(rng, [x for x in D.SOLUTION if x['calc']['kind'] == 'gas'])
    c = r['calc']
    k = coef(r['lhs'], r['rhs'])
    n, w, m = _oge22_amounts(rng, c['sol'])
    x = n * Fr(k[c['f']], k[c['sol']]) * VM
    ans = _ans22(x)
    ex = c['ex']
    ex_txt = f'избыток {gen(ex)}' if ex in ('Zn', 'Mg', 'CaCO3', 'FeS') else f'избыток раствора {gen(ex)}'
    sol_name = 'соляной кислоты' if c['sol'] == 'HCl' else gen(c['sol'])
    ex_i = ex_txt.replace('избыток', 'избытком')
    q = rng.choice([f'Порцию раствора {sol_name} массой {ru(m)} г, в которой массовая доля растворённого вещества равна {w} %, '
                    f'обработали {ex_i}. Найдите объём газа (н.у.), который при этом выделился.',
                    f'На {ru(m)} г {w} %-ного раствора {sol_name} подействовали {ex_i}. Какой объём (н.у.) газа выделился?'])
    if c['sol'] == 'NH4Cl':
        q = q.replace('обработали', 'при нагревании обработали').replace('подействовали', 'при нагревании подействовали')
    q += ' ' + KIM22 + ' В тренажёре введите объём в литрах.'
    eqs, eq = eqp(r['lhs'], r['rhs'])
    e = f'{eqs}; m({pretty(c["sol"])}) = {ru(m * w / 100)} г; n = {ru(n)} моль; n(газа) = {ru(n * Fr(k[c["f"]], k[c["sol"]]))} моль; ' \
        f'V = {ans} л.'
    wrong = W([n * VM, m / M(c['sol']) * Fr(k[c['f']], k[c['sol']]) * VM, n * Fr(k[c['f']], k[c['sol']]) * M(c['f'])], 2)
    nf_ = n * Fr(k[c['f']], k[c['sol']])
    steps = [(f'm({pretty(c["sol"])}) в растворе, г', sfmt(m * w / 100, 2)), (f'n({pretty(c["sol"])}), моль', sfmt(n, 3)),
             (f'n({pretty(c["f"])}), моль', sfmt(nf_, 3)), (f'V({pretty(c["f"])}), л', ans)]
    return pcard_s('ch-oge-22-gas', q, ans, e, p=dict(type='gas', lhs=r['lhs'], rhs=r['rhs'], sol=c['sol'], f=c['f'], m=str(m),
                                                    w=w), wrong=wrong, eq=eq, steps=steps)


@proto('ch-oge-22-omega', 'ОГЭ', 22, 'Массовая доля вещества в исходном растворе по массе осадка или объёму газа',
       invariant='n(продукта) → по уравнению n(вещества в растворе) → m → ω = m/m(р-ра)·100 %',
       varies='реакция, продукт — осадок (масса) или газ (объём), масса раствора',
       answer_rule='ω, % (точное значение)',
       mistakes=['поделили массу осадка на массу раствора', 'не учли коэффициенты'],
       solve=_solve_oge22, kes=['7.1', '7.2'],
       fidelity=fid('в ОГЭ — развёрнутый ответ; в тренажёре — число, %', 'как в банке ОГЭ: «170 г раствора нитрата серебра '
                    'смешали с избытком хлорида натрия. Выпал осадок массой 8,61 г. Вычислите массовую долю соли…»', 'В', 10,
                    'как в банке', 'обратный ход по уравнению', ['7.1', '7.2'], '3 балла в КИМ'))
def goge22_omega(rng):
    r = pick(rng, [x for x in D.SOLUTION if x['calc']['kind'] in ('precip', 'gas')])
    c = r['calc']
    k = coef(r['lhs'], r['rhs'])
    n, w, m = _oge22_amounts(rng, c['sol'])
    nf = n * Fr(k[c['f']], k[c['sol']])
    fby = 'V' if c['kind'] == 'gas' else 'm'
    pv = nf * (VM if fby == 'V' else M(c['f']))
    if not nice(pv, 3):
        raise Retry
    ans = _ans22(Fr(w))
    sol_name = 'соляной кислоты' if c['sol'] == 'HCl' else gen(c['sol'])
    got = f'выделилось {ru(pv)} л (н.у.) газа' if fby == 'V' else f'образовалось {ru(pv)} г осадка'
    ex = c['ex']
    ex_txt = f'избытком {gen(ex)}' if ex in ('Zn', 'Mg', 'CaCO3', 'FeS') else f'избытком раствора {gen(ex)}'
    q = f'Порцию раствора {sol_name} массой {ru(m)} г обработали {ex_txt}; при этом {got}. Рассчитайте массовую долю ' \
        f'{"хлороводорода" if c["sol"] == "HCl" else gen(c["sol"])} в исходном растворе. ' + KIM22 + ' В тренажёре введите ' \
        f'массовую долю в процентах.'
    eqs, eq = eqp(r['lhs'], r['rhs'])
    e = f'{eqs}; n(продукта) = {ru(nf)} моль ⇒ n({pretty(c["sol"])}) = {ru(n)} моль, m = {ru(n * M(c["sol"]))} г; ω = {ans} %.'
    wrong = W([pv / m * 100, nf * M(c['sol']) / m * 100 if k[c['f']] != k[c['sol']] else Fr(w) * 2, n * M(c['sol'])], 2)
    steps = [(f'n({pretty(c["f"])}), моль', sfmt(nf, 3)), (f'n({pretty(c["sol"])}), моль', sfmt(n, 3)),
             (f'm({pretty(c["sol"])}), г', sfmt(n * M(c['sol']), 2)), (f'ω({pretty(c["sol"])}), %', ans)]
    return pcard_s('ch-oge-22-omega', q, ans, e, p=dict(type='omega', lhs=r['lhs'], rhs=r['rhs'], sol=c['sol'], f=c['f'],
                                                      m=str(m), pv=str(pv), fby=fby), wrong=wrong, eq=eq, steps=steps)


@proto('ch-oge-22-msol', 'ОГЭ', 22, 'Масса раствора заданной концентрации, необходимая для реакции',
       invariant='по продукту (или второму реагенту) находят n вещества в растворе; m(р-ра) = n·M/ω',
       varies='реакция, известное количество продукта, доля раствора',
       answer_rule='масса раствора, г (точное значение)',
       mistakes=['нашли массу вещества, а не раствора', 'умножили на ω вместо деления'],
       solve=_solve_oge22, kes=['7.1', '7.2'],
       fidelity=fid('в ОГЭ — развёрнутый ответ; в тренажёре — число, г', 'как в банке ОГЭ: «… выпал осадок массой 2,87 г. '
                    'Вычислите массу исходного раствора нитрата серебра с массовой долей соли 17 %»', 'В', 10, 'как в банке',
                    'масса раствора = m(в-ва)/ω', ['7.1', '7.2'], '3 балла в КИМ'))
def goge22_msol(rng):
    r = pick(rng, [x for x in D.SOLUTION if x['calc']['kind'] in ('precip', 'gas')])
    c = r['calc']
    k = coef(r['lhs'], r['rhs'])
    n, w, m = _oge22_amounts(rng, c['sol'])
    nf = n * Fr(k[c['f']], k[c['sol']])
    fby = 'V' if c['kind'] == 'gas' else 'm'
    pv = nf * (VM if fby == 'V' else M(c['f']))
    if not nice(pv, 3):
        raise Retry
    ans = _ans22(m)
    sol_name = 'соляной кислоты' if c['sol'] == 'HCl' else gen(c['sol'])
    got = f'выделилось {ru(pv)} л (н.у.) газа' if fby == 'V' else f'выпал осадок массой {ru(pv)} г'
    exr = f'избытком {gen(c["ex"])}' if c['ex'] in ('Zn', 'Mg', 'CaCO3', 'FeS') else f'избытком раствора {gen(c["ex"])}'
    q = f'Некоторую массу раствора {sol_name} обработали {exr}; {got}. Известно, что массовая доля растворённого ' \
        f'вещества в этом растворе была равна {w} %. Найдите массу взятого раствора. ' + KIM22 + \
        ' В тренажёре введите массу раствора в граммах.'
    eqs, eq = eqp(r['lhs'], r['rhs'])
    e = f'{eqs}; n({pretty(c["sol"])}) = {ru(n)} моль, m = {ru(n * M(c["sol"]))} г; m(р-ра) = m/{w}·100 = {ans} г.'
    wrong = W([n * M(c['sol']), n * M(c['sol']) * w / 100, pv * 100 / w], 2)
    steps = [(f'n({pretty(c["f"])}), моль', sfmt(nf, 3)), (f'n({pretty(c["sol"])}), моль', sfmt(n, 3)),
             (f'm({pretty(c["sol"])}), г', sfmt(n * M(c['sol']), 2)), ('m(раствора), г', ans)]
    return pcard_s('ch-oge-22-msol', q, ans, e, p=dict(type='msol', lhs=r['lhs'], rhs=r['rhs'], sol=c['sol'], f=c['f'],
                                                     w=w, pv=str(pv), fby=fby), wrong=wrong, eq=eq, steps=steps)


@proto('ch-oge-22-reagent', 'ОГЭ', 22, 'Масса (объём) второго реагента или соли для реакции с раствором',
       invariant='m(в-ва в растворе) = m(р-ра)·ω → n → по уравнению n второго реагента (продукта) → m или V',
       varies='реакция (оксид/гидроксид + кислота, аммиак + кислота, металл + соль, CO₂/SO₂ + щёлочь, H₂S + CuSO₄), '
              'масса и доля раствора',
       answer_rule='масса (г) или объём (л) — точное значение',
       mistakes=['не учли коэффициенты', 'взяли массу раствора как массу вещества'],
       solve=_solve_oge22, kes=['7.1', '7.2'],
       fidelity=fid('в ОГЭ — развёрнутый ответ; в тренажёре — число', 'как в банке ОГЭ: «Вычислите массу оксида меди(II), '
                    'который может прореагировать с 73 г 20 %-ного раствора соляной кислоты»', 'В', 10, 'как в банке',
                    'коэффициенты', ['7.1', '7.2'], '3 балла в КИМ'))
def goge22_reagent(rng):
    r = pick(rng, [x for x in D.REAGENT if not x['calc'].get('made')])
    c = r['calc']
    k = coef(r['lhs'], r['rhs'])
    n, w, m = _oge22_amounts(rng, c['sol'])
    nr = n * Fr(k[c['r']], k[c['sol']])
    rby = c['by']
    x = nr * (VM if rby == 'V' else M(c['r']))
    ans = _ans22(x)
    sol_name = {'HCl': 'соляной кислоты'}.get(c['sol'], gen(c['sol']))
    want = f'объём (н.у.) {gen(c["r"])}' if rby == 'V' else f'массу {gen(c["r"])}'
    rel, need_w = ('который', 'необходимый') if rby == 'V' else ('которая', 'необходимую')
    q = rng.choice([f'Вычислите {want}, {rel} может полностью прореагировать с {ru(m)} г раствора {sol_name} с массовой '
                    f'долей растворённого вещества {w} %.',
                    f'Имеется {ru(m)} г {w} %-ного раствора {sol_name}. Определите {want}, {need_w} для полного '
                    f'взаимодействия с этим раствором.'])
    q += ' ' + KIM22 + ' В тренажёре введите ' + ('объём в литрах.' if rby == 'V' else 'массу в граммах.')
    eqs, eq = eqp(r['lhs'], r['rhs'])
    e = f'{eqs}; m({pretty(c["sol"])}) = {ru(m * w / 100)} г, n = {ru(n)} моль; n({pretty(c["r"])}) = {ru(nr)} моль ⇒ {ans}.'
    wrong = W([n * (VM if rby == 'V' else M(c['r'])), m / M(c['sol']) * Fr(k[c['r']], k[c['sol']]) * (VM if rby == 'V' else M(c['r'])),
               nr * (M(c['r']) if rby == 'V' else VM)], 2)
    steps = [(f'm({pretty(c["sol"])}) в растворе, г', sfmt(m * w / 100, 2)), (f'n({pretty(c["sol"])}), моль', sfmt(n, 3)),
             (f'n({pretty(c["r"])}), моль', sfmt(nr, 3)), (f'{"V" if rby == "V" else "m"}({pretty(c["r"])}), '
                                                         f'{"л" if rby == "V" else "г"}', ans)]
    return pcard_s('ch-oge-22-reagent', q, ans, e, p=dict(type='reag', lhs=r['lhs'], rhs=r['rhs'], sol=c['sol'], r=c['r'],
                                                        rby=rby, m=str(m), w=w), wrong=wrong, eq=eq, steps=steps)


# ======================================================================= шаги развёрнутых решений (частичный балл)
# Шаги карточки (pcard steps=) пересчитываются независимо (solve_steps) по данным условия. Как шаги ложатся на критерии:

import pc_core as _pc  # noqa: E402

SCORE34 = ('4 балла, как в критериях ФИПИ № 34: 1) уравнения реакций (проверяет эксперт/самопроверка по эталону в '
           'пояснении); 2) количества исходных веществ — шаги 1–2 (разложившаяся/неразложившаяся часть, n компонентов '
           'смеси, n соли, n H₂SO₄ из олеума); 3) количества прореагировавших веществ и масса конечного раствора — '
           'шаги 3–4 (избыток/недостаток, вычет осадка, газа, металла); 4) искомая величина — последний шаг. '
           'Каждый верный элемент — 1 балл; итоговое число проверяется отдельно.')
SCORE22 = ('3 балла, как в критериях ОГЭ № 22: 1) уравнение реакции (эталон в пояснении); 2) масса и количество вещества '
           'в растворе (или по продукту) — шаги 1–2; 3) количество по уравнению и искомая величина — шаги 3–4. '
           'Частичный балл — по числу верных элементов.')
for _pid, _calc in [('ch-ege-34-electro', _el_calc), ('ch-ege-34-decomp', _dec_calc), ('ch-ege-34-atoms', _atoms_calc),
                    ('ch-ege-34-hydrate', _hyd_calc), ('ch-ege-34-solub', _solub_calc), ('ch-ege-34-oleum', _oleum_calc)]:
    _pc.PROTOS[_pid]['solve_steps'] = _steps(_calc)
    _pc.PROTOS[_pid]['fidelity']['score'] = SCORE34
    _pc.PROTOS[_pid]['fidelity']['answer_format'] = ('многошаговая карточка: промежуточные величины (n, массы растворов) '
                                                     'и итоговое число, % до десятых (объём воды — до целых)')
for _pid in ('ch-oge-22-precip', 'ch-oge-22-gas', 'ch-oge-22-omega', 'ch-oge-22-msol', 'ch-oge-22-reagent'):
    _pc.PROTOS[_pid]['solve_steps'] = _steps(_oge22_calc)
    _pc.PROTOS[_pid]['fidelity']['score'] = SCORE22
    _pc.PROTOS[_pid]['fidelity']['answer_format'] = ('многошаговая карточка: m и n вещества, n по уравнению, итоговое '
                                                     'число (точное значение)')
