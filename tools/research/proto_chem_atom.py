"""Прототипы по химии: строение атома, Периодический закон, химическая связь, степень окисления.

ЕГЭ (КИМ 2027): задания 1–4 (1 — строение электронных оболочек, 2 — закономерности ПСХЭ, последовательность;
3 — степень окисления/валентность/ЭО, 4 — вид связи и тип кристаллической решётки).
ОГЭ 2027: задания 1–6 (1 — элемент/простое/сложное вещество, 2 — модель атома «X, Y», 3 — ряд из трёх элементов,
4 — соответствие «формула — степень окисления» (2 балла), 5 — вид связи, 6 — характеристика элементов).

Справочные данные (элементы 1–36 + Sr, Ag, I, Ba, Pb; вещества с видом связи и решёткой) — в этом модуле.
Генераторы берут готовые поля таблиц (конфигурация строкой, период, группа, степени окисления, связи);
solve() пересчитывает ответ ДРУГИМ путём: электронную конфигурацию — по правилу Клечковского (с «провалом»
электрона у Cr, Cu, Ag) из одного Z; положение в ПСХЭ, металличность, высшую/низшую степень окисления —
из этой конфигурации; вид связи — по составу формулы (металл/неметалл, группировки, степени окисления);
степень окисления — из электронейтральности.
"""
import itertools
import re
from fractions import Fraction as Fr

from pc_core import AR, Retry, match_opts, opts, parse_formula, pcard, pretty, proto

SUP = str.maketrans('0123456789+-', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻')

# ================================================================= таблица элементов
# символ Z именит. родит. период группа подгруппа конфигурация ЭО(Полинг) степени_окисления агрегатное_состояние вид
# вид: m — металл, n — неметалл, g — благородный газ, x — полуметалл (в заданиях не берём как «металл/неметалл»)
_EL = """
H 1 водород водорода 1 1 A 1s1 2.20 -1,1 г n
He 2 гелий гелия 1 8 A 1s2 - - г g
Li 3 литий лития 2 1 A [He]2s1 0.98 1 т m
Be 4 бериллий бериллия 2 2 A [He]2s2 1.57 2 т m
B 5 бор бора 2 3 A [He]2s2_2p1 2.04 -3,3 т n
C 6 углерод углерода 2 4 A [He]2s2_2p2 2.55 -4,2,4 т n
N 7 азот азота 2 5 A [He]2s2_2p3 3.04 -3,1,2,3,4,5 г n
O 8 кислород кислорода 2 6 A [He]2s2_2p4 3.44 -2,-1,1,2 г n
F 9 фтор фтора 2 7 A [He]2s2_2p5 3.98 -1 г n
Ne 10 неон неона 2 8 A [He]2s2_2p6 - - г g
Na 11 натрий натрия 3 1 A [Ne]3s1 0.93 1 т m
Mg 12 магний магния 3 2 A [Ne]3s2 1.31 2 т m
Al 13 алюминий алюминия 3 3 A [Ne]3s2_3p1 1.61 3 т m
Si 14 кремний кремния 3 4 A [Ne]3s2_3p2 1.90 -4,4 т n
P 15 фосфор фосфора 3 5 A [Ne]3s2_3p3 2.19 -3,3,5 т n
S 16 сера серы 3 6 A [Ne]3s2_3p4 2.58 -2,4,6 т n
Cl 17 хлор хлора 3 7 A [Ne]3s2_3p5 3.16 -1,1,3,5,7 г n
Ar 18 аргон аргона 3 8 A [Ne]3s2_3p6 - - г g
K 19 калий калия 4 1 A [Ar]4s1 0.82 1 т m
Ca 20 кальций кальция 4 2 A [Ar]4s2 1.00 2 т m
Sc 21 скандий скандия 4 3 B [Ar]3d1_4s2 1.36 3 т m
Ti 22 титан титана 4 4 B [Ar]3d2_4s2 1.54 2,3,4 т m
V 23 ванадий ванадия 4 5 B [Ar]3d3_4s2 1.63 2,3,4,5 т m
Cr 24 хром хрома 4 6 B [Ar]3d5_4s1 1.66 2,3,6 т m
Mn 25 марганец марганца 4 7 B [Ar]3d5_4s2 1.55 2,4,6,7 т m
Fe 26 железо железа 4 8 B [Ar]3d6_4s2 1.83 2,3,6 т m
Co 27 кобальт кобальта 4 8 B [Ar]3d7_4s2 1.88 2,3 т m
Ni 28 никель никеля 4 8 B [Ar]3d8_4s2 1.91 2,3 т m
Cu 29 медь меди 4 1 B [Ar]3d10_4s1 1.90 1,2 т m
Zn 30 цинк цинка 4 2 B [Ar]3d10_4s2 1.65 2 т m
Ga 31 галлий галлия 4 3 A [Ar]3d10_4s2_4p1 1.81 3 т m
Ge 32 германий германия 4 4 A [Ar]3d10_4s2_4p2 2.01 -4,2,4 т x
As 33 мышьяк мышьяка 4 5 A [Ar]3d10_4s2_4p3 2.18 -3,3,5 т n
Se 34 селен селена 4 6 A [Ar]3d10_4s2_4p4 2.55 -2,4,6 т n
Br 35 бром брома 4 7 A [Ar]3d10_4s2_4p5 2.96 -1,1,3,5,7 ж n
Kr 36 криптон криптона 4 8 A [Ar]3d10_4s2_4p6 3.00 2 г g
Sr 38 стронций стронция 5 2 A [Kr]5s2 0.95 2 т m
Ag 47 серебро серебра 5 1 B [Kr]4d10_5s1 1.93 1 т m
I 53 иод иода 5 7 A [Kr]4d10_5s2_5p5 2.66 -1,1,3,5,7 т n
Ba 56 барий бария 6 2 A [Xe]6s2 0.89 2 т m
Pb 82 свинец свинца 6 4 A [Xe]4f14_5d10_6s2_6p2 2.33 2,4 т m
"""
CORES = {'He': '1s2', 'Ne': '[He]2s2_2p6', 'Ar': '[Ne]3s2_3p6', 'Kr': '[Ar]3d10_4s2_4p6', 'Xe': '[Kr]4d10_5s2_5p6'}

E = {}
for _ln in _EL.strip().splitlines():
    _s, _z, _nom, _gen, _per, _gr, _sub, _cfg, _en, _ox, _st, _kind = _ln.split()
    E[_s] = dict(s=_s, Z=int(_z), nom=_nom, gen=_gen, period=int(_per), group=int(_gr), sub=_sub, cfg=_cfg,
                 en=None if _en == '-' else float(_en), ox=() if _ox == '-' else tuple(int(x) for x in _ox.split(',')),
                 state=_st, kind=_kind)
BY_Z = {v['Z']: k for k, v in E.items()}
ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII'}
LNAME = 'spdf'


def cfg_cells(sym):
    """Готовая строка конфигурации из таблицы → {(n, l): число электронов} (путь генератора)."""
    out = {}
    s = E[sym]['cfg'] if sym in E else CORES[sym]
    m = re.match(r'\[(\w+)\](.*)', s)
    if m:
        out.update(cfg_cells(m.group(1)) if m.group(1) in E else _core_cells(m.group(1)))
        s = m.group(2)
    for part in s.split('_'):
        if part:
            mm = re.fullmatch(r'(\d)([spdf])(\d+)', part)
            out[(int(mm.group(1)), LNAME.index(mm.group(2)))] = int(mm.group(3))
    return out


def _core_cells(core):
    out = {}
    s = CORES[core]
    m = re.match(r'\[(\w+)\](.*)', s)
    if m:
        out.update(_core_cells(m.group(1)))
        s = m.group(2)
    for part in s.split('_'):
        mm = re.fullmatch(r'(\d)([spdf])(\d+)', part)
        out[(int(mm.group(1)), LNAME.index(mm.group(2)))] = int(mm.group(3))
    return out


def cfg_text(cells):
    """{(n,l): c} → «1s²2s²2p⁶3s¹» в порядке n, l (как пишут в КИМ)."""
    return ''.join(f'{n}{LNAME[l]}{str(c).translate(SUP)}' for (n, l), c in sorted(cells.items()) if c)


def outer_n(cells):
    return max(n for (n, l), c in cells.items() if c)


def outer_count(cells):
    n = outer_n(cells)
    return sum(c for (nn, l), c in cells.items() if nn == n)


def unpaired_hund(cells):
    return sum(min(c, 2 * (2 * l + 1) - c) for (n, l), c in cells.items())


def ion_cells(cells, q):
    """Электроны иона: катион теряет с самого внешнего слоя (p, затем s; у d-элементов сначала ns), анион —
    достраивает последний незаполненный p-подуровень."""
    c = dict(cells)
    if q > 0:
        for _ in range(q):
            n = outer_n(c)
            key = max((k for k in c if k[0] == n and c[k]), key=lambda k: k[1])
            c[key] -= 1
            if not c[key]:
                del c[key]
            if not c:
                break
    else:
        n = outer_n(c)
        c[(n, 1)] = c.get((n, 1), 0) - q
    return c


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many


def signed(x):
    x = int(x)
    return f'+{x}' if x > 0 else ('0' if x == 0 else f'−{-x}')


def ox_max(sym):
    return max(E[sym]['ox']) if E[sym]['ox'] else 0


def ox_min(sym):
    return min(E[sym]['ox']) if E[sym]['ox'] else 0


def ids_of(items, pred):
    return sorted(str(i + 1) for i, x in enumerate(items) if pred(x))


def pick_row(rng, yes, no, k=2, n=5):
    yes, no = list(dict.fromkeys(yes)), list(dict.fromkeys(no))
    if len(yes) < k or len(no) < n - k:
        raise Retry
    items = rng.sample(yes, k) + rng.sample(no, n - k)
    rng.shuffle(items)
    return items


# ================================================================= второй путь (только для solve)
_MAD = sorted([(n, l) for n in range(1, 8) for l in range(0, min(n, 4))], key=lambda x: (x[0] + x[1], x[0]))
_DROP = {24, 29, 42, 47, 79}   # «провал» электрона: (n)s² (n−1)d⁴/d⁹ → s¹ d⁵/d¹⁰


def aufbau(Z):
    """Заполнение подуровней по правилу Клечковского (n + l, затем n) → {(n,l): c}, плюс порядок заполнения."""
    occ, left, order = {}, Z, []
    for n, l in _MAD:
        if left <= 0:
            break
        c = min(left, 2 * (2 * l + 1))
        occ[(n, l)] = c
        order.append((n, l))
        left -= c
    if Z in _DROP:
        s = max(k for k in occ if k[1] == 0)
        d = (s[0] - 1, 2)
        occ[s] -= 1
        occ[d] += 1
    return occ, order


def z_of(sym):
    return E[sym]['Z']


def r_period(Z):
    occ, _ = aufbau(Z)
    return max(n for (n, l), c in occ.items() if c)


def r_outer(Z):
    occ, _ = aufbau(Z)
    n = r_period(Z)
    return sum(c for (nn, l), c in occ.items() if nn == n)


def r_block(Z):
    """Семейство: подуровень, заполняемый последним по правилу Клечковского."""
    _, order = aufbau(Z)
    return LNAME[order[-1][1]]


def r_valence(Z):
    """Число валентных электронов (номер группы в короткой форме таблицы для A и B)."""
    occ, order = aufbau(Z)
    n = r_period(Z)
    if r_block(Z) == 'd':
        v = occ.get((n, 0), 0) + occ.get((n - 1, 2), 0)
        return v - 10 if v > 10 else min(v, 8)
    if Z == 2:
        return 8
    return r_outer(Z)


def r_noble(Z):
    return r_block(Z) == 'p' and r_outer(Z) == 8 or Z == 2


def r_metal(Z):
    """Металл, если внешних электронов не больше номера периода (кроме H и благородных газов); d-элементы — металлы."""
    if Z == 1 or r_noble(Z):
        return False
    if r_block(Z) == 'd':
        return True
    return r_outer(Z) <= r_period(Z)


def r_unpaired(Z):
    """Число неспаренных электронов: раскладываем электроны подуровня по орбиталям по правилу Хунда."""
    occ, _ = aufbau(Z)
    total = 0
    for (n, l), c in occ.items():
        boxes = [0] * (2 * l + 1)
        for i in range(c):
            boxes[i % len(boxes)] += 1
        total += sum(1 for b in boxes if b == 1)
    return total


def r_higher_ox(Z):
    """Высшая степень окисления = номер группы (валентные электроны); у Cu школьное +2, у O/F — не по группе."""
    if Z in (8, 9) or r_noble(Z):
        return None
    if Z == 29:
        return 2
    v = r_valence(Z)
    return v


def r_lower_ox(Z):
    """Низшая степень окисления неметалла = номер группы − 8; у металлов отрицательных нет."""
    if r_noble(Z):
        return None
    if Z == 1:
        return -1
    if r_metal(Z):
        return 0
    return r_outer(Z) - 8


def r_ion_charge(Z):
    """Заряд простого иона: металл главной подгруппы отдаёт внешние электроны, неметалл достраивает до октета."""
    if r_block(Z) == 'd' or Z == 1 or r_noble(Z):
        return None
    return r_outer(Z) if r_metal(Z) else r_outer(Z) - 8


def r_counts(Z, q=0):
    """Число s-, p-, d-электронов атома/иона (второй путь: снимаем с наибольшего n, у d-элементов сначала ns)."""
    occ, _ = aufbau(Z)
    occ = dict(occ)
    if q > 0:
        for _ in range(q):
            n = max(k[0] for k, c in occ.items() if c)
            ks = sorted((k for k, c in occ.items() if c and k[0] == n), key=lambda k: -k[1])
            occ[ks[0]] -= 1
    elif q < 0:
        n = max(k[0] for k, c in occ.items() if c)
        occ[(n, 1)] = occ.get((n, 1), 0) - q
    out = {'s': 0, 'p': 0, 'd': 0, 'f': 0}
    for (n, l), c in occ.items():
        out[LNAME[l]] += c
    return out


# ================================================================= общие части формулировок и fidelity
def val_text(sym):
    """Валентные подуровни: у s/p-элементов — внешний слой, у d-элементов — (n−1)d и ns."""
    cells = cfg_cells(sym)
    n = outer_n(cells)
    keep = {k: c for k, c in cells.items() if k[0] == n or (E[sym]['sub'] == 'B' and k == (n - 1, 2))}
    return ''.join(f'{nn}{LNAME[l]}{str(c).translate(SUP)}' for (nn, l), c in sorted(keep.items(), key=lambda kv: (kv[0][0], kv[0][1])))


def fid(n, exam, *, trap, scale, kes, fmt_=None, style=None):
    if exam == 'ЕГЭ':
        return dict(answer_format=fmt_ or 'две цифры — номера элементов/веществ, порядок не важен (как в КИМ 2027)',
                    style=style or 'условие КИМ: ряд из пяти элементов/перечень пяти веществ, «Определите…»/«Из числа '
                                   'указанных… выберите…»; справочные данные — ПСХЭ',
                    level='Б', time_min=2.5, scale=scale, trap=trap, kes=kes,
                    score='1 балл, ответ засчитывается только при полном совпадении')
    lv = {4: 'П'}.get(n, 'Б')
    return dict(answer_format=fmt_ or 'две цифры — номера выбранных ответов, порядок не важен',
                style=style or 'формулировка КИМ ОГЭ 2027: «Выберите два…», справочные данные — ПСХЭ',
                level=lv, time_min=7 if n == 4 else 3, scale=scale, trap=trap, kes=kes,
                score='2 балла; 1 балл при одной ошибке в позиции' if n == 4 else '1 балл, полное совпадение')


MAIN = [s for s, e in E.items() if e['sub'] == 'A' and e['kind'] != 'g' and s not in ('Pb',)]
DBLK = ['Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn']
DCOMMON = ['Cr', 'Mn', 'Fe', 'Cu', 'Zn']
ROW_TAIL = ['Запишите номера выбранных элементов.', 'Запишите в поле ответа номера выбранных элементов.',
            'В ответ запишите номера двух элементов.']


def row_card(pid, rng, items, pred, q, e_lines, p):
    ans = ids_of(items, pred)
    if len(ans) != 2:
        raise Retry
    e = '; '.join(e_lines) + f'. Условию отвечают элементы под номерами {", ".join(ans)}.'
    return pcard(pid, q + ' ' + rng.choice(ROW_TAIL), ans, e, k='many', o=opts(items), p=dict(p, row=items))


# ================================================================= ЕГЭ 1. Строение электронных оболочек атомов
K1 = ['1.1']
TIME_E1 = 'ряд из пяти элементов (главные подгруппы I–VII периодов 1–5, иногда Cr, Mn, Fe, Cu, Zn), как в банке'


def _solve_unpaired(p):
    v = p['v']
    return ids_of(p['row'], lambda s: r_unpaired(z_of(s)) == v)


@proto('ch-ege-01-unpaired', 'ЕГЭ', 1, 'Число неспаренных электронов в основном состоянии',
       invariant='по электронной конфигурации (правило Хунда) найти число неспаренных электронов у каждого атома ряда',
       varies='ряд из пяти элементов, требуемое число неспаренных электронов (0–3) или атом-эталон',
       answer_rule='выбрать два элемента, у атомов которых неспаренных электронов ровно столько, сколько требуется',
       mistakes=['спаривают p-электроны до заполнения всех орбиталей (у N считают 1)',
                 'у Cr и Cu забывают «провал» электрона', 'путают число неспаренных с числом внешних электронов'],
       solve=_solve_unpaired, kes=K1,
       fidelity=fid(1, 'ЕГЭ', trap='правило Хунда: N, P — 3 неспаренных; O, S — 2; d-элементы Cr (6), Mn (5)',
                    scale=TIME_E1, kes=['1.1']))
def g_unpaired(rng):
    pid = 'ch-ege-01-unpaired'
    pool = MAIN + (DCOMMON if rng.random() < 0.4 else [])
    v = rng.choice([0, 1, 2, 3, 3, 2])
    u = lambda s: unpaired_hund(cfg_cells(s))
    items = pick_row(rng, [s for s in pool if u(s) == v], [s for s in pool if u(s) != v])
    mode = rng.randrange(3)
    if mode == 0 and v:
        q = (f'Определите, у атомов каких двух из указанных в ряду элементов в основном состоянии '
             f'{v} {plural(v, "неспаренный электрон", "неспаренных электрона", "неспаренных электронов")}.')
    elif mode == 1 or not v:
        q = ('Определите, атомы каких двух из указанных в ряду элементов в основном состоянии не содержат неспаренных '
             'электронов.' if not v else
             f'Какие два из указанных в ряду элементов в основном состоянии атома имеют по '
             f'{v} {plural(v, "неспаренному электрону", "неспаренных электрона", "неспаренных электронов")}?')
    else:
        refs = [s for s in MAIN + DBLK if u(s) == v and s not in items]
        ref = rng.choice(refs)
        q = (f'Определите, атомы каких двух из указанных в ряду элементов в основном состоянии имеют столько же '
             f'неспаренных электронов, сколько атом {E[ref]["gen"]}.')
    lines = [f'{s} ({val_text(s)}) — {u(s)}' for s in items]
    return row_card(pid, rng, items, lambda s: u(s) == v, q, ['Неспаренные электроны: ' + lines[0]] + lines[1:], {'v': v})


def _solve_outer(p):
    mode = p['mode']
    if mode == 'lack':
        return ids_of(p['row'], lambda s: 8 - r_outer(z_of(s)) == p['v'])
    if mode == 'formula':
        return ids_of(p['row'], lambda s: r_block(z_of(s)) != 'd' and r_outer(z_of(s)) == p['v'])
    return ids_of(p['row'], lambda s: r_outer(z_of(s)) == p['v'])


@proto('ch-ege-01-outer', 'ЕГЭ', 1, 'Число электронов внешнего уровня / его формула',
       invariant='по положению в ПСХЭ (группа, подгруппа) определить число электронов на внешнем энергетическом уровне',
       varies='ряд; требуемое число внешних электронов, формула внешнего слоя ns^a np^b, «не хватает до завершения», '
              'атом-эталон',
       answer_rule='у элементов главных подгрупп внешних электронов = номер группы; у d-элементов внешний уровень — ns '
                   '(1 у Cr и Cu, 2 у остальных)',
       mistakes=['у d-элементов считают внешними и d-электроны', 'путают номер периода и число внешних электронов',
                 'не учитывают «провал» электрона у Cr, Cu'],
       solve=_solve_outer, kes=K1,
       fidelity=fid(1, 'ЕГЭ', trap='d-элементы: у Fe, Mn, Zn на внешнем уровне 2 электрона, у Cr и Cu — 1',
                    scale=TIME_E1, kes=['1.1']))
def g_outer(rng):
    pid = 'ch-ege-01-outer'
    oc = lambda s: outer_count(cfg_cells(s))
    mode = rng.choice(['count', 'count', 'formula', 'lack', 'ref'])
    if mode == 'formula':
        pool = MAIN
        v = rng.randint(1, 7)
        pred = lambda s: oc(s) == v
        a, b = min(v, 2), max(v - 2, 0)
        f = f'ns{str(a).translate(SUP)}' + (f'np{str(b).translate(SUP)}' if b else '')
        q = f'Определите, атомы каких двух из указанных в ряду элементов имеют электронную формулу внешнего уровня {f}.'
    elif mode == 'lack':
        pool = [s for s in MAIN if s != 'H']
        v = rng.randint(1, 4)
        pred = lambda s: 8 - oc(s) == v
        q = (f'Определите, атомам каких двух из указанных в ряду элементов до завершения внешнего энергетического '
             f'уровня недостаёт {v} {plural(v, "электрона", "электронов", "электронов")}.')
    else:
        pool = MAIN + (DCOMMON if rng.random() < 0.5 else [])
        v = rng.randint(1, 7) if rng.random() < 0.7 else rng.choice([1, 2])
        pred = lambda s: oc(s) == v
        if mode == 'count':
            q = (f'Определите, у атомов каких двух из указанных в ряду элементов на внешнем энергетическом уровне '
                 f'находится {v} {plural(v, "электрон", "электрона", "электронов")}.')
        else:
            refs = [s for s in MAIN if oc(s) == v]
            ref = rng.choice(refs)
            q = (f'Определите, атомы каких двух из указанных в ряду элементов имеют на внешнем энергетическом уровне '
                 f'столько же электронов, сколько атом {E[ref]["gen"]} в основном состоянии.')
            mode = 'count'
    items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
    lines = [f'{s}: {val_text(s)} — {oc(s)}' for s in items]
    return row_card(pid, rng, items, pred, q, ['Электроны внешнего уровня: ' + lines[0]] + lines[1:], {'mode': mode, 'v': v})


NOBLE = {'He': 2, 'Ne': 10, 'Ar': 18, 'Kr': 36}
ION_POOL = ['Li', 'Na', 'K', 'Be', 'Mg', 'Ca', 'Sr', 'Ba', 'Al', 'N', 'O', 'F', 'P', 'S', 'Cl', 'Se', 'Br', 'I']


def ion_q(s):
    e = E[s]
    return e['group'] if e['kind'] == 'm' else e['group'] - 8


def ion_str(s, q=None):
    q = ion_q(s) if q is None else q
    mag = '' if abs(q) == 1 else str(abs(q))
    return s + (mag + ('+' if q > 0 else '-')).translate(SUP)


def _solve_ion(p):
    zn = {'He': 2, 'Ne': 10, 'Ar': 18, 'Kr': 36}[p['gas']]
    return ids_of(p['row'], lambda s: r_ion_charge(z_of(s)) is not None and z_of(s) - r_ion_charge(z_of(s)) == zn)


@proto('ch-ege-01-ion', 'ЕГЭ', 1, 'Ион с электронной конфигурацией благородного газа',
       invariant='построить простой ион элемента (металл отдаёт внешние электроны, неметалл достраивает октет) и '
                 'сравнить его конфигурацию с конфигурацией благородного газа',
       varies='ряд, благородный газ (Ne, Ar, Kr), способ задать конфигурацию (название газа или электронная формула)',
       answer_rule='число электронов иона Z − q должно совпасть с Z благородного газа',
       mistakes=['путают заряд иона неметалла (берут +, а не −)', 'выбирают элемент, чей атом (а не ион) похож на газ',
                 'у ионов d-элементов ищут конфигурацию благородного газа'],
       solve=_solve_ion, kes=K1,
       fidelity=fid(1, 'ЕГЭ', trap='изоэлектронные частицы: S²⁻, Cl⁻, K⁺, Ca²⁺ — как у Ar; соседние по Z элементы '
                                    'дают ионы разных газов', scale=TIME_E1, kes=['1.1']))
def g_ion(rng):
    pid = 'ch-ege-01-ion'
    gas = rng.choice(['Ne', 'Ne', 'Ar', 'Ar', 'Kr'])
    zn = NOBLE[gas]
    pred = lambda s: s in ION_POOL and E[s]['Z'] - ion_q(s) == zn
    no = [s for s in ION_POOL if not pred(s)] + (['Fe', 'Cu', 'Zn'] if rng.random() < 0.3 else [])
    items = pick_row(rng, [s for s in ION_POOL if pred(s)], no)
    mode = rng.randrange(3)
    full = cfg_text(cfg_cells(gas) if gas in E else _core_cells(gas))
    if mode == 0:
        q = (f'Определите, какие два из указанных в ряду элементов образуют простые ионы с такой же электронной '
             f'конфигурацией, как у атома {E[gas]["gen"]}.')
    elif mode == 1:
        q = (f'Определите, атомы каких двух из указанных в ряду элементов, приняв или отдав электроны до завершения '
             f'внешнего уровня, образуют ионы с электронной формулой {full}.')
    else:
        q = (f'Определите, для каких двух из указанных в ряду элементов электронная конфигурация иона, характерного '
             f'для их соединений, совпадает с конфигурацией атома {E[gas]["gen"]} ({full}).')
    lines = []
    for s in items:
        if s in ION_POOL:
            lines.append(f'{ion_str(s)} — {E[s]["Z"] - ion_q(s)} электронов')
        else:
            lines.append(f'{s} — d-элемент, его ионы не имеют конфигурации благородного газа')
    return row_card(pid, rng, items, pred, q, [f'У {gas} {zn} электронов; ' + lines[0]] + lines[1:], {'gas': gas})


REF_PARTICLES = [('Na', 1), ('Mg', 2), ('Al', 3), ('K', 1), ('Ca', 2), ('F', -1), ('O', -2), ('Cl', -1), ('S', -2),
                 ('N', -3), ('Li', 1), ('Fe', 2), ('Fe', 3), ('Mn', 2), ('Cu', 1), ('Zn', 2), ('Cr', 3), ('Ne', 0),
                 ('Ar', 0), ('Na', 0), ('Mg', 0), ('K', 0), ('Ca', 0), ('P', 0), ('Cl', 0), ('Be', 0), ('Cr', 0),
                 ('Cu', 0), ('Br', -1), ('Se', -2)]
SUB_WORD = {'s': 's-электронов', 'p': 'p-электронов', 'd': 'd-электронов'}


def counts(sym, q=0):
    cells = cfg_cells(sym) if sym in E else _core_cells(sym)
    if q:
        cells = ion_cells(cells, q)
    out = {'s': 0, 'p': 0, 'd': 0}
    for (n, l), c in cells.items():
        if l < 3:
            out[LNAME[l]] += c
    return out


def particle_name(sym, q):
    if q == 0:
        return f'атом {E[sym]["gen"]}'
    kind = 'катион' if q > 0 else 'анион'
    return f'{kind} {ion_str(sym, q)}'


def _solve_sublevel(p):
    ref = r_counts(z_of(p['ref'][0]), p['ref'][1])[p['sub']]
    return ids_of(p['row'], lambda s: r_counts(z_of(s))[p['sub']] == ref)


@proto('ch-ege-01-sublevel', 'ЕГЭ', 1, 'Число s-, p- или d-электронов как у атома/иона-эталона',
       invariant='записать полную электронную конфигурацию атомов ряда и частицы-эталона, сосчитать электроны '
                 'одного типа подуровня',
       varies='ряд, тип подуровня (s, p, d), частица-эталон (атом, катион, анион)',
       answer_rule='совпадает суммарное число электронов на всех подуровнях данного типа',
       mistakes=['считают только внешний подуровень, а не все s (p, d) подуровни', 'забывают снять/добавить электроны '
                 'у иона', 'у Cr, Cu не учитывают провал (s-электронов на один меньше)'],
       solve=_solve_sublevel, kes=K1,
       fidelity=fid(1, 'ЕГЭ', trap='как в демоверсии 2027: число s-электронов как у катиона натрия; провал у Cr/Cu; '
                                    'у ионов d-элементов сначала уходят 4s-электроны', scale=TIME_E1, kes=['1.1']))
def g_sublevel(rng):
    pid = 'ch-ege-01-sublevel'
    sub = rng.choice(['s', 's', 'p', 'p', 'd'])
    refs = [r for r in REF_PARTICLES if counts(*r)[sub] > 0]
    ref = rng.choice(refs)
    v = counts(*ref)[sub]
    pool = [s for s in MAIN + DBLK if s != ref[0] or ref[1] != 0]
    pred = lambda s: counts(s)[sub] == v
    items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
    pn = particle_name(*ref)
    if rng.random() < 0.5:
        q = (f'Определите, атомы каких двух из указанных в ряду элементов в основном состоянии содержат такое же '
             f'общее число {SUB_WORD[sub]}, как и {pn}.')
    else:
        q = (f'Определите, в атомах каких двух из указанных в ряду элементов (основное состояние) суммарное число '
             f'{SUB_WORD[sub]} равно числу {SUB_WORD[sub]} частицы {pn.split(" ", 1)[1]}.')
    lines = [f'{s} — {counts(s)[sub]}' for s in items]
    return row_card(pid, rng, items, pred, q, [f'{pn[0].upper() + pn[1:]}: {v} {sub}-электронов; у атомов: ' + lines[0]]
                    + lines[1:], {'sub': sub, 'ref': list(ref)})


EXC = {2: 'ns¹np¹', 3: 'ns¹np²', 4: 'ns¹np³'}


def _solve_excited(p):
    if p['mode'] == 'formula':
        return ids_of(p['row'], lambda s: r_block(z_of(s)) != 'd' and r_outer(z_of(s)) == p['g'])
    # число неспаренных растёт при возбуждении: есть пара на внешнем уровне и свободная орбиталь того же уровня
    def can(s):
        Z = z_of(s)
        occ, _ = aufbau(Z)
        n = r_period(Z)
        paired = occ.get((n, 0), 0) == 2 or occ.get((n, 1), 0) > 3
        free = occ.get((n, 1), 0) < 3 if occ.get((n, 0), 0) == 2 and occ.get((n, 1), 0) < 3 else n >= 3
        return r_outer(Z) not in (1, 8) and paired and free
    return ids_of(p['row'], can)


def can_excite(s):
    """Возбуждение увеличивает число неспаренных: у групп II–IV — за счёт свободных p-орбиталей того же слоя;
    у V–VII — только при наличии d-подуровня на внешнем слое (с 3-го периода)."""
    g = E[s]['group']
    if g in (2, 3, 4):
        return True
    if g in (5, 6, 7):
        return E[s]['period'] >= 3
    return False


@proto('ch-ege-01-excited', 'ЕГЭ', 1, 'Возбуждённое состояние атома',
       invariant='распарить s-электроны внешнего уровня на свободные орбитали того же уровня (p, для периода ≥ 3 — d)',
       varies='ряд; вопрос: формула внешнего уровня в возбуждённом состоянии (ns¹np¹/ns¹np²/ns¹np³) или '
              '«может ли число неспаренных электронов увеличиться при возбуждении»',
       answer_rule='ns¹np^(k−1) в возбуждённом состоянии — у элементов группы k (II–IV); у N, O, F нет свободных орбиталей '
                   'на втором уровне, у щелочных металлов распаривать нечего',
       mistakes=['считают, что азот может стать пятивалентным за счёт возбуждения', 'путают основное и возбуждённое '
                 'состояния', 'забывают про d-орбитали у P, S, Cl'],
       solve=_solve_excited, kes=K1,
       fidelity=fid(1, 'ЕГЭ', trap='N, O, F не имеют возбуждённых состояний с большим числом неспаренных электронов; '
                                    'Be, B, C — имеют', scale=TIME_E1, kes=['1.1']))
def g_excited(rng):
    pid = 'ch-ege-01-excited'
    if rng.random() < 0.55:
        g = rng.choice([2, 3, 4])
        pool = [s for s in MAIN if s not in ('H',) and E[s]['kind'] != 'x' or s == 'Ge']
        pred = lambda s: E[s]['group'] == g and s != 'H'
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        q = rng.choice([f'Определите, атомы каких двух из указанных в ряду элементов в возбуждённом состоянии имеют '
                        f'электронную формулу внешнего энергетического уровня {EXC[g]}.',
                        f'Определите, для атомов каких двух из указанных в ряду элементов возбуждённому состоянию '
                        f'соответствует конфигурация внешнего уровня {EXC[g]}.'])
        lines = [f'{s}: {val_text(s)}' for s in items]
        return row_card(pid, rng, items, pred, q, [f'{EXC[g]} получается из ns²np^{g - 2} (группа {ROMAN[g]}); ' + lines[0]]
                        + lines[1:], {'mode': 'formula', 'g': g})
    pool = [s for s in MAIN if s != 'H']
    items = pick_row(rng, [s for s in pool if can_excite(s)], [s for s in pool if not can_excite(s)] + ['H'])
    q = rng.choice(['Определите, атомы каких двух из указанных в ряду элементов могут перейти в возбуждённое состояние '
                    'с увеличением числа неспаренных электронов.',
                    'Определите, у атомов каких двух из указанных в ряду элементов при переходе в возбуждённое состояние '
                    'возрастает число неспаренных электронов.'])
    lines = [f'{s} ({val_text(s)}) — {"да" if can_excite(s) else "нет"}' for s in items]
    return row_card(pid, rng, items, can_excite, q, ['Нужны спаренные электроны и свободные орбитали того же уровня: '
                                                     + lines[0]] + lines[1:], {'mode': 'unpair'})


def _solve_block(p):
    if p['mode'] == 'layers':
        return ids_of(p['row'], lambda s: r_period(z_of(s)) == p['v'])
    return ids_of(p['row'], lambda s: r_block(z_of(s)) == p['v'])


def block_of(s):
    e = E[s]
    if e['sub'] == 'B':
        return 'd'
    return 's' if e['group'] <= 2 and s != 'He' else 'p'


@proto('ch-ege-01-block', 'ЕГЭ', 1, 'Электронное семейство (s, p, d) и число энергетических уровней',
       invariant='определить, какой подуровень заполняется последним (семейство) или сколько энергетических уровней '
                 'занято электронами',
       varies='ряд, семейство (s-, p-, d-элементы) или число уровней (= номер периода)',
       answer_rule='s-элементы — IA, IIA (и H, He); p-элементы — IIIA–VIIIA; d-элементы — побочные подгруппы; '
                   'число уровней = номер периода',
       mistakes=['относят Zn, Cu к s-элементам (по внешним 4s)', 'относят Ga к d-элементам', 'путают номер группы и '
                 'число уровней'],
       solve=_solve_block, kes=K1,
       fidelity=fid(1, 'ЕГЭ', trap='Zn, Cu — d-элементы при внешнем 4s; He — s-элемент', scale=TIME_E1, kes=['1.1']))
def g_block(rng):
    pid = 'ch-ege-01-block'
    if rng.random() < 0.7:
        v = rng.choice(['s', 'p', 'd'])
        pool = MAIN + DBLK
        pred = lambda s: block_of(s) == v
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        q = rng.choice([f'Определите, какие два из указанных в ряду элементов относятся к {v}-элементам.',
                        f'Определите, в атомах каких двух из указанных в ряду элементов последним заполняется '
                        f'{v}-подуровень.'])
        lines = [f'{s} — {block_of(s)}' for s in items]
        return row_card(pid, rng, items, pred, q, ['Семейства: ' + lines[0]] + lines[1:], {'mode': 'block', 'v': v})
    v = rng.choice([2, 3, 4])
    pool = MAIN + DCOMMON
    pred = lambda s: E[s]['period'] == v
    items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
    q = (f'Определите, в атомах каких двух из указанных в ряду элементов электроны в основном состоянии занимают '
         f'{v} энергетических {plural(v, "уровень", "уровня", "уровней")}.')
    lines = [f'{s} — период {E[s]["period"]}' for s in items]
    return row_card(pid, rng, items, pred, q, ['Число уровней равно номеру периода: ' + lines[0]] + lines[1:],
                    {'mode': 'layers', 'v': v})


# ================================================================= ЕГЭ 2. Закономерности изменения свойств (последовательность)
LINES_P = {2: ['Li', 'Be', 'B', 'C', 'N', 'O', 'F'], 3: ['Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl'],
           4: ['K', 'Ca', 'Ga', 'Ge', 'As', 'Se', 'Br']}
LINES_G = {1: ['Li', 'Na', 'K'], 2: ['Be', 'Mg', 'Ca', 'Sr', 'Ba'], 3: ['B', 'Al', 'Ga'], 4: ['C', 'Si', 'Ge'],
           5: ['N', 'P', 'As'], 6: ['O', 'S', 'Se'], 7: ['F', 'Cl', 'Br', 'I']}
NO_OXIDE = {'O', 'F'}
HYDR = {'N', 'O', 'F', 'P', 'S', 'Cl', 'As', 'Se', 'Br', 'I'}
# свойство: (родительный падеж для «в порядке возрастания …», знак изменения вдоль периода (слева направо),
#            вдоль группы (сверху вниз), фильтр элементов, можно ли в группе, можно ли в периоде)
PROPS2 = {
    'radius': ('радиуса атома', -1, +1, None),
    'en': ('электроотрицательности', +1, -1, lambda s: s not in ('Ga', 'Ge')),
    'nonmet': ('неметаллических свойств', +1, -1, lambda s: s not in ('Ga', 'Ge')),
    'oxid': ('окислительных свойств соответствующих простых веществ', +1, -1, lambda s: E[s]['kind'] == 'n'),
    'metal': ('металлических свойств', -1, +1, None),
    'reduc': ('восстановительных свойств', -1, +1, lambda s: E[s]['kind'] == 'm'),
    'acid_ox': ('кислотных свойств высших оксидов', +1, -1, lambda s: s not in NO_OXIDE),
    'base_hyd': ('основных свойств высших гидроксидов', -1, +1, lambda s: s not in NO_OXIDE),
    'hyd_acid': ('кислотных свойств водородных соединений', +1, +1, lambda s: s in HYDR),
    'hyd_red': ('восстановительных свойств водородных соединений', -1, +1, lambda s: s in HYDR),
    'outer': ('числа электронов на внешнем энергетическом уровне', +1, 0, None),
    'hiox': ('высшей степени окисления', +1, 0, lambda s: s not in NO_OXIDE),
}
GROUP_OK = {'acid_ox': {1, 2, 3, 4, 5, 7}, 'base_hyd': {1, 2, 3}, 'hyd_acid': {6, 7}, 'hyd_red': {6, 7},
            'reduc': {1, 2}, 'oxid': {5, 6, 7}}


def _order_ids(items, triple, key, asc):
    seq = sorted(triple, key=key, reverse=not asc)
    return ''.join(str(items.index(s) + 1) for s in seq)


def _solve_seq(p):
    """Второй путь: период/группа — из электронной конфигурации (Z); направление — из своей таблицы правил."""
    rules = {'radius': (-1, 1), 'en': (1, -1), 'nonmet': (1, -1), 'oxid': (1, -1), 'metal': (-1, 1), 'reduc': (-1, 1),
             'acid_ox': (1, -1), 'base_hyd': (-1, 1), 'hyd_acid': (1, 1), 'hyd_red': (-1, 1), 'outer': (1, 0),
             'hiox': (1, 0)}
    row = p['row']
    zs = [z_of(s) for s in row]
    if p['along'] == 'period':
        groups = {}
        for i, Z in enumerate(zs):
            groups.setdefault(r_period(Z), []).append(i)
        trip = [g for g in groups.values() if len(g) == 3]
        pos = lambda i: r_valence(zs[i])
        d = rules[p['prop']][0]
    else:
        groups = {}
        for i, Z in enumerate(zs):
            if r_block(Z) != 'd':
                groups.setdefault(r_valence(Z), []).append(i)
        trip = [g for g in groups.values() if len(g) == 3]
        pos = lambda i: r_period(zs[i])
        d = rules[p['prop']][1]
    assert len(trip) == 1
    seq = sorted(trip[0], key=lambda i: d * pos(i), reverse=not p['asc'])
    return ''.join(str(i + 1) for i in seq)


def seq_card(pid, rng, props):
    prop = rng.choice(props)
    word, dp, dg, flt = PROPS2[prop]
    along = rng.choice(['period', 'group']) if dg else 'period'
    if along == 'group' and prop in GROUP_OK:
        lines = {g: v for g, v in LINES_G.items() if g in GROUP_OK[prop]}
    else:
        lines = LINES_G if along == 'group' else LINES_P
    cand = []
    for k, line in lines.items():
        good = [s for s in line if flt is None or flt(s)]
        if len(good) >= 3:
            cand.append((k, good))
    if not cand:
        raise Retry
    k, good = rng.choice(cand)
    triple = rng.sample(good, 3)
    attr = 'period' if along == 'period' else 'group'
    others = [s for s in MAIN if E[s][attr] != E[triple[0]][attr] and s not in triple and s != 'H']
    two = rng.sample(others, 2)
    if E[two[0]][attr] == E[two[1]][attr] and rng.random() < 0.5:
        raise Retry
    items = triple + two
    rng.shuffle(items)
    # в ряду ровно одна тройка с общим периодом/группой
    cnt = {}
    for s in items:
        cnt[E[s][attr]] = cnt.get(E[s][attr], 0) + 1
    if sorted(cnt.values(), reverse=True)[0] != 3 or list(cnt.values()).count(3) != 1:
        raise Retry
    asc = rng.random() < 0.5
    pos = (lambda s: E[s]['group']) if along == 'period' else (lambda s: E[s]['period'])
    d = dp if along == 'period' else dg
    ans = _order_ids(items, triple, lambda s: d * pos(s), asc)
    where = rng.choice(['в одном периоде', 'в одном периоде Периодической системы']) if along == 'period' else \
        rng.choice(['в одной группе (главной подгруппе)', 'в одной группе Периодической системы'])
    how = ('возрастания' if asc else 'уменьшения') if prop in ('radius', 'en', 'outer', 'hiox') else \
        ('усиления' if asc else 'ослабления')
    q = rng.choice([
        f'Из указанных в ряду химических элементов выберите три элемента, расположенных {where}. '
        f'Расположите выбранные элементы в порядке {how} {word}.',
        f'Выберите из числа указанных в ряду элементов три элемента, которые находятся {where}, и расположите '
        f'их в порядке {how} {word}.',
    ]) + ' ' + rng.choice(['Запишите номера выбранных элементов в нужной последовательности.',
                           'Запишите в поле ответа номера выбранных элементов в нужной последовательности.'])
    trip_sorted = sorted(triple, key=lambda s: pos(s))
    dir_word = {1: 'растёт', -1: 'уменьшается'}
    if along == 'period':
        rule = f'{"-".join(trip_sorted)} — {E[triple[0]]["period"]}-й период; слева направо {word} {dir_word[d]}'
    else:
        rule = f'{"-".join(trip_sorted)} — {ROMAN[E[triple[0]]["group"]]}A-группа; сверху вниз {word} {dir_word[d]}'
    e = f'{rule}. Порядок {how}: ' + ' → '.join(sorted(triple, key=lambda s: d * pos(s), reverse=not asc)) + f'. Ответ: {ans}.'
    rev = ans[::-1]
    return pcard(pid, q, ans, e, k='num', o=opts(items),
                 p={'row': items, 'prop': prop, 'along': along, 'asc': asc},
                 wrong=[rev, ans[1] + ans[0] + ans[2], ans[0] + ans[2] + ans[1]])


FID2 = dict(fmt_='три цифры — номера элементов в нужной последовательности (порядок важен), как в КИМ 2027')
K2 = ['1.2']


@proto('ch-ege-02-radius', 'ЕГЭ', 2, 'Три элемента периода/группы: порядок изменения радиуса атома',
       invariant='найти в ряду три элемента одного периода (группы) и упорядочить по радиусу атома',
       varies='ряд из пяти элементов, период или группа, возрастание или уменьшение',
       answer_rule='в периоде слева направо радиус уменьшается, в группе сверху вниз — увеличивается',
       mistakes=['считают, что в периоде радиус растёт с зарядом ядра', 'путают направление («уменьшения»)',
                 'берут тройку не из одного периода'],
       solve=_solve_seq, kes=K2,
       fidelity=fid(2, 'ЕГЭ', trap='направление изменения в периоде и группе противоположно; лишние два элемента из '
                                    'других периодов', scale=TIME_E1, kes=['1.2'], **FID2))
def g_seq_radius(rng):
    return seq_card('ch-ege-02-radius', rng, ['radius'])


@proto('ch-ege-02-en', 'ЕГЭ', 2, 'Порядок изменения ЭО, неметаллических и окислительных свойств',
       invariant='найти три элемента одного периода (группы) и упорядочить по электроотрицательности '
                 '(неметаллическим/окислительным свойствам)',
       varies='ряд, период/группа, свойство (ЭО, неметаллические, окислительные свойства), направление',
       answer_rule='в периоде слева направо ЭО и неметаллические свойства растут, в группе сверху вниз — ослабевают',
       mistakes=['путают направление в группе', 'считают кислород электроотрицательнее фтора'],
       solve=_solve_seq, kes=K2,
       fidelity=fid(2, 'ЕГЭ', trap='направления изменения в периоде и группе противоположны', scale=TIME_E1,
                    kes=['1.2'], **FID2))
def g_seq_en(rng):
    return seq_card('ch-ege-02-en', rng, ['en', 'nonmet', 'oxid'])


@proto('ch-ege-02-metal', 'ЕГЭ', 2, 'Порядок изменения металлических и восстановительных свойств',
       invariant='три элемента одного периода (группы) упорядочить по металлическим (восстановительным) свойствам',
       varies='ряд, период/группа, свойство, направление (усиление/ослабление)',
       answer_rule='металлические и восстановительные свойства усиливаются справа налево в периоде и сверху вниз в группе',
       mistakes=['путают усиление и ослабление', 'в периоде ставят металл с большим зарядом ядра активнее'],
       solve=_solve_seq, kes=K2,
       fidelity=fid(2, 'ЕГЭ', trap='направление в периоде обратно направлению в группе', scale=TIME_E1, kes=['1.2'],
                    **FID2))
def g_seq_metal(rng):
    return seq_card('ch-ege-02-metal', rng, ['metal', 'reduc'])


@proto('ch-ege-02-oxides', 'ЕГЭ', 2, 'Порядок изменения кислотно-основных свойств высших оксидов и гидроксидов',
       invariant='три элемента одного периода (группы) упорядочить по кислотным свойствам высших оксидов '
                 '(основным свойствам гидроксидов)',
       varies='ряд, период/группа, кислотные или основные свойства, направление',
       answer_rule='в периоде слева направо кислотные свойства высших оксидов/гидроксидов усиливаются, основные '
                   'ослабевают; в группе сверху вниз — наоборот',
       mistakes=['переносят рост кислотности водородных соединений в группе на оксиды', 'путают оксиды и гидроксиды'],
       solve=_solve_seq, kes=K2,
       fidelity=fid(2, 'ЕГЭ', trap='кислотность высших оксидов в группе падает, а водородных соединений — растёт',
                    scale=TIME_E1, kes=['1.2'], **FID2))
def g_seq_oxides(rng):
    return seq_card('ch-ege-02-oxides', rng, ['acid_ox', 'base_hyd'])


@proto('ch-ege-02-hydrides', 'ЕГЭ', 2, 'Порядок изменения свойств водородных соединений неметаллов',
       invariant='три неметалла одного периода (группы) упорядочить по кислотным (восстановительным) свойствам '
                 'их водородных соединений',
       varies='ряд, период/группа (VIA, VIIA), кислотные или восстановительные свойства, направление',
       answer_rule='кислотные свойства водородных соединений растут и слева направо, и сверху вниз; восстановительные '
                   'растут сверху вниз и справа налево',
       mistakes=['переносят закономерность ЭО на кислотность (HF считают самой сильной)', 'путают с оксидами'],
       solve=_solve_seq, kes=K2,
       fidelity=fid(2, 'ЕГЭ', trap='HF — самая слабая из галогеноводородных кислот', scale=TIME_E1, kes=['1.2'],
                    **FID2))
def g_seq_hydrides(rng):
    return seq_card('ch-ege-02-hydrides', rng, ['hyd_acid', 'hyd_red'])


@proto('ch-ege-02-count', 'ЕГЭ', 2, 'Порядок изменения числа внешних электронов / высшей степени окисления',
       invariant='три элемента одного периода упорядочить по числу электронов внешнего уровня или высшей степени окисления',
       varies='ряд, период, величина (внешние электроны, высшая степень окисления), направление',
       answer_rule='в периоде слева направо число внешних электронов и высшая степень окисления растут (равны номеру группы)',
       mistakes=['для кислорода и фтора берут высшую степень окисления по номеру группы', 'путают направление'],
       solve=_solve_seq, kes=K2,
       fidelity=fid(2, 'ЕГЭ', trap='номер группы = число внешних электронов = высшая степень окисления', scale=TIME_E1,
                    kes=['1.2'], **FID2))
def g_seq_count(rng):
    return seq_card('ch-ege-02-count', rng, ['outer', 'hiox'])


# ================================================================= ЕГЭ 3. Степень окисления, валентность, ЭО
K3 = ['1.3']
POOL3 = [s for s in MAIN if s not in ('O', 'F', 'Ge', 'B')] + ['Cr', 'Mn', 'Zn', 'V', 'Ti']
OXIDE_T = {1: 'Э₂O', 2: 'ЭO', 3: 'Э₂O₃', 4: 'ЭO₂', 5: 'Э₂O₅', 6: 'ЭO₃', 7: 'Э₂O₇'}
HYD_T = {4: 'ЭH₄', 5: 'ЭH₃', 6: 'H₂Э', 7: 'HЭ'}
NONMET3 = ['H', 'C', 'Si', 'N', 'P', 'As', 'O', 'S', 'Se', 'Cl', 'Br', 'I']


def _ox_line(s):
    ox = E[s]['ox']
    return f'{s}: ' + (', '.join(signed(x) for x in ox) if ox else '0')


def _solve_maxox(p):
    return ids_of(p['row'], lambda s: r_higher_ox(z_of(s)) == p['v'])


@proto('ch-ege-03-maxox', 'ЕГЭ', 3, 'Высшая степень окисления (+N)',
       invariant='высшая степень окисления элемента равна номеру группы (числу валентных электронов)',
       varies='ряд (главные и побочные подгруппы: Cr, Mn, V, Ti, Zn), значение высшей степени окисления, формулировка '
              '(высшая степень окисления / степень окисления в высшем оксиде)',
       answer_rule='выбрать два элемента, номер группы которых совпадает с требуемой степенью окисления',
       mistakes=['для d-элементов берут число внешних электронов (Mn → +2)', 'путают высшую и низшую степени окисления'],
       solve=_solve_maxox, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='элементы побочных подгрупп: Cr +6 как у S, Mn +7 как у Cl', scale=TIME_E1,
                    kes=['1.3']))
def g_maxox(rng):
    pid = 'ch-ege-03-maxox'
    v = rng.randint(1, 7)
    pred = lambda s: ox_max(s) == v
    items = pick_row(rng, [s for s in POOL3 if pred(s)], [s for s in POOL3 if not pred(s)])
    q = rng.choice([f'Определите, какие два из указанных в ряду элементов проявляют высшую степень окисления, равную {signed(v)}.',
                    f'Из числа указанных в ряду элементов выберите два элемента, которые в высших оксидах имеют '
                    f'степень окисления {signed(v)}.',
                    f'Определите, для каких двух из указанных в ряду элементов высшая степень окисления равна {signed(v)}.'])
    lines = [f'{s} — {signed(ox_max(s))}' for s in items]
    return row_card(pid, rng, items, pred, q, ['Высшие степени окисления: ' + lines[0]] + lines[1:], {'v': v})


def _solve_minox(p):
    return ids_of(p['row'], lambda s: r_lower_ox(z_of(s)) == -p['v'])


@proto('ch-ege-03-minox', 'ЕГЭ', 3, 'Низшая (отрицательная) степень окисления',
       invariant='низшая степень окисления неметалла = номер группы − 8; металлы отрицательных степеней не имеют',
       varies='ряд, значение низшей степени окисления (−1…−4), формулировка (низшая степень окисления / в соединениях '
              'с водородом или металлами)',
       answer_rule='выбрать два неметалла нужной группы (VII → −1, VI → −2, V → −3, IV → −4)',
       mistakes=['приписывают металлам отрицательную степень окисления', 'путают −(8 − N) и −N'],
       solve=_solve_minox, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='водород: низшая −1 (гидриды) — как у галогенов', scale=TIME_E1, kes=['1.3']))
def g_minox(rng):
    pid = 'ch-ege-03-minox'
    v = rng.randint(1, 4)
    pool = [s for s in MAIN if s not in ('B', 'Ge')] + ['Cr', 'Fe', 'Zn', 'Cu']
    pred = lambda s: ox_min(s) == -v
    items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
    q = rng.choice([f'Определите, какие два из указанных в ряду элементов имеют низшую степень окисления, равную {signed(-v)}.',
                    f'Из числа указанных в ряду элементов выберите два элемента, низшая степень окисления которых '
                    f'равна {signed(-v)}.'])
    lines = [f'{s} — {signed(min(ox_min(s), 0))}' for s in items]
    return row_card(pid, rng, items, pred, q, ['Низшие степени окисления (у металлов 0): ' + lines[0]] + lines[1:],
                    {'v': v})


def _solve_both(p):
    def ok(s):
        Z = z_of(s)
        lo, hi = r_lower_ox(Z), r_higher_ox(Z)
        if Z == 8:   # кислород: +2 во фториде кислорода OF2
            hi = 2
        return lo is not None and hi is not None and lo < 0 < hi
    return ids_of(p['row'], ok)


@proto('ch-ege-03-bothsign', 'ЕГЭ', 3, 'Может проявлять и положительную, и отрицательную степень окисления',
       invariant='неметаллы (кроме фтора) в соединениях с более электроотрицательными элементами имеют положительные, '
                 'с менее электроотрицательными — отрицательные степени окисления; металлы — только положительные',
       varies='ряд из металлов и неметаллов (в т. ч. H, O, F)',
       answer_rule='выбрать два неметалла, отличных от фтора (кислород: +2 в OF₂; водород: −1 в гидридах)',
       mistakes=['выбирают фтор', 'не считают кислород (OF₂)', 'выбирают металл с переменной степенью окисления'],
       solve=_solve_both, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='как в демоверсии 2027: O (+2 в OF₂) и Si (−4 в силицидах); F только −1',
                    scale=TIME_E1, kes=['1.3']))
def g_bothsign(rng):
    pid = 'ch-ege-03-bothsign'
    pool = [s for s in MAIN if s not in ('B', 'Ge', 'Ga')] + (['Cr', 'Mn', 'Fe', 'Cu', 'Zn'] if rng.random() < .4 else [])
    pred = lambda s: E[s]['kind'] == 'n' and min(E[s]['ox']) < 0 < max(E[s]['ox'])
    yes = [s for s in pool if pred(s)]
    no = [s for s in pool if not pred(s)]
    if rng.random() < 0.5:
        no += ['F', 'F']
    items = pick_row(rng, yes, no)
    q = rng.choice(['Из числа указанных в ряду элементов выберите два элемента, которые в соединениях могут иметь как '
                    'положительную, так и отрицательную степень окисления.',
                    'Определите, какие два из указанных в ряду элементов способны проявлять в соединениях и '
                    'положительные, и отрицательные степени окисления.'])
    return row_card(pid, rng, items, pred, q, ['Степени окисления в соединениях: ' + _ox_line(items[0])]
                    + [_ox_line(s) for s in items[1:]], {})


SUM_POOL = ['C', 'Si', 'N', 'P', 'As', 'S', 'Se', 'Cl', 'Br', 'I']


def _solve_sum(p):
    return ids_of(p['row'], lambda s: r_higher_ox(z_of(s)) + r_lower_ox(z_of(s)) == p['v'])


@proto('ch-ege-03-sum', 'ЕГЭ', 3, 'Сумма (разность) высшей и низшей степеней окисления',
       invariant='высшая степень окисления неметалла = N (группа), низшая = N − 8; сумма = 2N − 8',
       varies='ряд неметаллов IV–VII групп; сумма (0, +2, +4, +6) или разность «высшая − |низшая|»',
       answer_rule='выбрать два неметалла одной группы (сумма 0 → IV, +2 → V, +4 → VI, +6 → VII)',
       mistakes=['берут модуль низшей степени окисления и складывают', 'для кислорода/фтора считают по номеру группы'],
       solve=_solve_sum, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='сумма с учётом знака: у серы +6 + (−2) = +4', scale=TIME_E1, kes=['1.3']))
def g_sum(rng):
    pid = 'ch-ege-03-sum'
    g = rng.choice([4, 5, 6, 7])
    v = 2 * g - 8
    pred = lambda s: ox_max(s) + ox_min(s) == v
    items = pick_row(rng, [s for s in SUM_POOL if pred(s)], [s for s in SUM_POOL if not pred(s)])
    if rng.random() < 0.6:
        q = (f'Определите, для каких двух из указанных в ряду элементов сумма высшей и низшей степеней окисления '
             f'равна {signed(v) if v else "нулю"}.')
    else:
        q = (f'Из числа указанных в ряду элементов выберите два элемента, у которых высшая степень окисления '
             f'по абсолютной величине {"равна низшей" if v == 0 else f"на {v} больше абсолютной величины низшей"}.')
    lines = [f'{s}: {signed(ox_max(s))} и {signed(ox_min(s))}' for s in items]
    return row_card(pid, rng, items, pred, q, ['Высшая и низшая степени окисления — ' + lines[0]] + lines[1:], {'v': v})


def _solve_oxide(p):
    return ids_of(p['row'], lambda s: r_higher_ox(z_of(s)) == p['g'])


@proto('ch-ege-03-oxide', 'ЕГЭ', 3, 'Состав высшего оксида (валентность в высшем оксиде)',
       invariant='высшая валентность (степень окисления) = номер группы; состав высшего оксида из неё',
       varies='ряд, общая формула высшего оксида (Э₂O…Э₂O₇) или высшая валентность в оксиде',
       answer_rule='Э₂O — I, ЭO — II, Э₂O₃ — III, ЭO₂ — IV, Э₂O₅ — V, ЭO₃ — VI, Э₂O₇ — VII группа '
                   '(включая побочные подгруппы: CrO₃, Mn₂O₇)',
       mistakes=['путают ЭO₃ и Э₂O₃', 'для Cr, Mn берут низшие оксиды'],
       solve=_solve_oxide, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='d-элементы: Cr → CrO₃ (как S), Mn → Mn₂O₇ (как Cl)', scale=TIME_E1, kes=['1.3']))
def g_oxide(rng):
    pid = 'ch-ege-03-oxide'
    pool = [s for s in POOL3 if s != 'H']
    g = rng.randint(1, 7)
    pred = lambda s: ox_max(s) == g
    items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
    if rng.random() < 0.6:
        q = rng.choice([f'Определите, какие два из указанных в ряду элементов образуют высший оксид состава {OXIDE_T[g]}.',
                        f'Из числа указанных в ряду элементов выберите два элемента, высшие оксиды которых имеют общую '
                        f'формулу {OXIDE_T[g]}.'])
    else:
        q = f'Определите, какие два из указанных в ряду элементов в высших оксидах проявляют валентность {ROMAN[g]}.'
    lines = [f'{s} — {ROMAN[ox_max(s)]}, {OXIDE_T[ox_max(s)]}' for s in items]
    return row_card(pid, rng, items, pred, q, ['Высшая валентность и оксид: ' + lines[0]] + lines[1:], {'g': g})


def _solve_hydride(p):
    return ids_of(p['row'], lambda s: not r_metal(z_of(s)) and z_of(s) != 1 and r_outer(z_of(s)) == p['g'])


@proto('ch-ege-03-hydride', 'ЕГЭ', 3, 'Летучее водородное соединение (состав, валентность)',
       invariant='неметалл группы N образует летучее водородное соединение с валентностью 8 − N',
       varies='ряд, формула (ЭH₄, ЭH₃, H₂Э, HЭ) или валентность в водородном соединении',
       answer_rule='IV → ЭH₄, V → ЭH₃, VI → H₂Э, VII → HЭ; металлы летучих водородных соединений не образуют',
       mistakes=['путают формулу ЭH₃ и группу III', 'выбирают металлы (гидриды — нелетучие ионные вещества)'],
       solve=_solve_hydride, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='валентность в водородном соединении = 8 − N, а не N', scale=TIME_E1, kes=['1.3']))
def g_hydride(rng):
    pid = 'ch-ege-03-hydride'
    g = rng.choice([4, 5, 6, 7])
    pool = NONMET3[1:] + ['Na', 'Mg', 'Al', 'K', 'Ca', 'Li', 'Ba']
    pool = [s for s in pool if s != 'O' or g == 6]
    pred = lambda s: E[s]['kind'] == 'n' and E[s]['group'] == g
    items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
    if rng.random() < 0.6:
        q = rng.choice([f'Определите, какие два из указанных в ряду элементов образуют летучие водородные соединения '
                        f'состава {HYD_T[g]}.',
                        f'Из числа указанных в ряду элементов выберите два элемента, летучие водородные соединения '
                        f'которых имеют общую формулу {HYD_T[g]}.'])
    else:
        q = (f'Определите, какие два из указанных в ряду элементов проявляют в летучих водородных соединениях '
             f'валентность {ROMAN[8 - g]}.')
    lines = [f'{s} — {HYD_T[E[s]["group"]] if E[s]["kind"] == "n" and E[s]["group"] >= 4 else "нет летучего водородного соединения"}'
             for s in items]
    return row_card(pid, rng, items, pred, q, ['Водородные соединения: ' + lines[0]] + lines[1:], {'g': g})


CONST_YES = ['Li', 'Na', 'K', 'Be', 'Mg', 'Ca', 'Sr', 'Ba', 'Al', 'Zn']
CONST_NO = ['Cr', 'Mn', 'Fe', 'Cu', 'Pb', 'N', 'S', 'Cl', 'P', 'C', 'Br', 'I', 'Se']


def _solve_const(p):
    # постоянная: металл главной подгруппы I–III (одна возможная — все внешние электроны) или d¹⁰s² (Zn)
    def ok(s):
        Z = z_of(s)
        if not r_metal(Z):
            return False
        if r_block(Z) == 'd':
            occ, _ = aufbau(Z)
            return occ.get((r_period(Z) - 1, 2), 0) == 10 and r_outer(Z) == 2
        return r_outer(Z) <= 3
    return ids_of(p['row'], ok)


@proto('ch-ege-03-const', 'ЕГЭ', 3, 'Постоянная степень окисления в соединениях',
       invariant='металлы IA, IIA групп, алюминий и цинк проявляют в соединениях одну (постоянную) степень окисления; '
                 'неметаллы и большинство d-металлов — переменную',
       varies='ряд из металлов с постоянной и переменной степенью окисления и неметаллов',
       answer_rule='выбрать два элемента из IA/IIA, Al, Zn',
       mistakes=['относят к постоянным Fe или Cr', 'выбирают F, путая «постоянную» и «только отрицательную»'],
       solve=_solve_const, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='Zn — d-элемент, но степень окисления постоянная (+2); Cu, Fe, Cr — переменная',
                    scale=TIME_E1, kes=['1.3']))
def g_const(rng):
    pid = 'ch-ege-03-const'
    items = pick_row(rng, CONST_YES, CONST_NO)
    q = rng.choice(['Определите, какие два из указанных в ряду элементов проявляют в соединениях постоянную '
                    'положительную степень окисления.',
                    'Из числа указанных в ряду элементов выберите два элемента, которые во всех своих соединениях '
                    'имеют одну и ту же степень окисления.'])
    return row_card(pid, rng, items, lambda s: s in CONST_YES, q,
                    ['Степени окисления: ' + _ox_line(items[0])] + [_ox_line(s) for s in items[1:]], {})
