"""Прототипы по химии: строение атома, Периодический закон, химическая связь, степень окисления.

ЕГЭ (КИМ 2027): задания 1–4 (1 — строение электронных оболочек, 2 — закономерности ПСХЭ, последовательность;
3 — степень окисления/валентность/ЭО, 4 — вид связи и тип кристаллической решётки).
ОГЭ 2027: задания 1–6 (1 — элемент/простое/сложное вещество, 2 — модель атома «X, Y», 3 — ряд из трёх элементов,
4 — соответствие «формула — степень окисления» (2 балла), 5 — вид связи, 6 — характеристика элементов).

Справочные данные (элементы 1–36 + Rb, Sr, Ag, I, Cs, Ba, Pb; вещества с видом связи и решёткой) — в этом модуле.
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
Rb 37 рубидий рубидия 5 1 A [Kr]5s1 0.82 1 т m
Sr 38 стронций стронция 5 2 A [Kr]5s2 0.95 2 т m
Ag 47 серебро серебра 5 1 B [Kr]4d10_5s1 1.93 1 т m
I 53 иод иода 5 7 A [Kr]4d10_5s2_5p5 2.66 -1,1,3,5,7 т n
Cs 55 цезий цезия 6 1 A [Xe]6s1 0.79 1 т m
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
_DAT = dict(Li='литию', Be='бериллию', B='бору', C='углероду', N='азоту', O='кислороду', F='фтору', Na='натрию',
            Mg='магнию', Al='алюминию', Si='кремнию', P='фосфору', S='сере', Cl='хлору', K='калию', Ca='кальцию')
for _s, _d in _DAT.items():
    E[_s]['dat'] = _d
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
                    style=style or 'инструкции КИМ 2027 дословно («Из указанных в ряду химических элементов выберите два '
                                   'элемента, …», «Определите, …», «Из предложенного перечня выберите два вещества, …», '
                                   '«Запишите номера выбранных элементов/ответов»); условие (что спрашивают) — своими '
                                   'словами; ряд из пяти элементов (в карточке свой, в КИМ общий для 1–3) или перечень '
                                   'пяти веществ; справочные данные — ПСХЭ',
                    level='Б', time_min=2.5, scale=scale, trap=trap, kes=kes,
                    score='1 балл, ответ засчитывается только при полном совпадении')
    lv = {4: 'П'}.get(n, 'Б')
    return dict(answer_format=fmt_ or 'две цифры — номера выбранных ответов, порядок не важен',
                style=style or 'инструкции КИМ ОГЭ 2027 дословно («Выберите два высказывания…», «Из предложенного перечня '
                               'выберите два вещества…», «Запишите номера выбранных ответов»); условие и варианты — '
                               'свои; справочные данные — ПСХЭ',
                level=lv, time_min=7 if n == 4 else 3, scale=scale, trap=trap, kes=kes,
                score='2 балла; 1 балл при одной ошибке в позиции' if n == 4 else '1 балл, полное совпадение')


MAIN = [s for s, e in E.items() if e['sub'] == 'A' and e['kind'] != 'g' and s not in ('Pb',)]
DBLK = ['Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn']
DCOMMON = ['Cr', 'Mn', 'Fe', 'Cu', 'Zn']
# ================================================================= ЕГЭ 1. Строение электронных оболочек атомов
K1 = ['1.1']
TIME_E1 = ('ряд из пяти элементов (главные подгруппы периодов 1–5, d-элементы 4-го периода), как в заданиях 1–3 банка '
           'и демоверсии 2027')
TAILS = ['Запишите номера выбранных элементов.', 'Запишите в поле ответа номера выбранных элементов.']
GS = 'в невозбуждённом состоянии'


def kim_row(q):
    """Инструкция — как в КИМ 2027 («Из указанных в ряду химических элементов выберите два элемента, …»,
    «Определите, … каких двух из указанных в ряду элементов …»); условие (что именно спрашивают) — своё."""
    q = re.sub(r'^Укажите два элемента ряда, ', 'Из указанных в ряду химических элементов выберите два элемента, ', q)
    if q.endswith('?'):
        q = q[:-1] + '.'
        q = q.replace('каких двух элементов ряда', 'каких двух из указанных в ряду элементов')
        q = q.replace('Какие два элемента ряда', 'какие два из указанных в ряду элементов')
        q = 'Определите, ' + q[0].lower() + q[1:]
    return q


def row_card(pid, rng, items, pred, q, e_lines, p):
    ans = ids_of(items, pred)
    if len(ans) != 2:
        raise Retry
    e = '; '.join(e_lines) + f'. Условию отвечают элементы {items[int(ans[0]) - 1]} и {items[int(ans[1]) - 1]}; ' \
                             f'ответ {"".join(ans)}.'
    return pcard(pid, kim_row(q) + ' ' + rng.choice(TAILS), ans, e, k='many', o=opts(items), p=dict(p, row=items))


def pick_pair(rng, pool, f):
    """Ряд: ровно два элемента с одинаковым значением f, у остальных трёх значения разные и другие."""
    by = {}
    for s in pool:
        by.setdefault(f(s), []).append(s)
    vs = [v for v, xs in by.items() if len(xs) >= 2]
    if not vs:
        raise Retry
    v = rng.choice(vs)
    others = [w for w in by if w != v]
    if len(others) < 3:
        raise Retry
    items = rng.sample(by[v], 2) + [rng.choice(by[w]) for w in rng.sample(others, 3)]
    rng.shuffle(items)
    return items, v


def pair_pred(items, f):
    vals = [f(s) for s in items]
    return lambda s: vals.count(f(s)) == 2


def sub_unpaired(cells, l=None, outer=False):
    n0 = outer_n(cells)
    return sum(min(c, 2 * (2 * ll + 1) - c) for (n, ll), c in cells.items()
               if (l is None or ll == l) and (not outer or n == n0))


def r_unp(Z, l=None, outer=False):
    """Второй путь: электроны раскладываются по орбиталям подуровня по одному (правило Хунда)."""
    occ, _ = aufbau(Z)
    n0 = r_period(Z)
    tot = 0
    for (n, ll), c in occ.items():
        if (l is not None and ll != l) or (outer and n != n0):
            continue
        boxes = [0] * (2 * ll + 1)
        for i in range(c):
            boxes[i % len(boxes)] += 1
        tot += boxes.count(1)
    return tot


UNP_MODES = ['count', 'count', 'zero', 'same', 'outer1', 's', 'p1', 'donly', 'dsame']


def _solve_unpaired(p):
    m, row = p['mode'], p['row']
    zs = {s: z_of(s) for s in row}
    if m == 'count':
        f = lambda s: r_unp(zs[s]) == p['v']
    elif m == 'zero':
        f = lambda s: r_unp(zs[s]) == 0
    elif m == 'same':
        vals = [r_unp(zs[s]) for s in row]
        f = lambda s: vals.count(r_unp(zs[s])) == 2
    elif m == 'outer1':
        f = lambda s: r_unp(zs[s], outer=True) == 1
    elif m == 's':
        f = lambda s: r_unp(zs[s], l=0) > 0
    elif m == 'p1':
        f = lambda s: r_unp(zs[s], l=1) == 1
    elif m == 'donly':
        f = lambda s: r_unp(zs[s]) > 0 and r_unp(zs[s], l=2) == r_unp(zs[s])
    else:
        vals = [r_unp(zs[s], l=2) for s in row]
        f = lambda s: vals.count(r_unp(zs[s], l=2)) == 2
    return ids_of(row, f)


@proto('ch-ege-01-unpaired', 'ЕГЭ', 1, 'Неспаренные электроны атома в основном состоянии',
       invariant='записать электронную конфигурацию (валентные подуровни) и разместить электроны по орбиталям '
                 'по правилу Хунда; сосчитать неспаренные (всего, на внешнем уровне, на s-, p- или d-подуровне)',
       varies='ряд из пяти элементов; что спрашивают: число неспаренных (0–3), «одинаковое число», один неспаренный '
              'на внешнем уровне, неспаренный s-электрон, один неспаренный p-электрон, неспаренные только на d, '
              'одинаковое число неспаренных d-электронов',
       answer_rule='выбрать два элемента, удовлетворяющих условию; у Cr и Cu учесть «провал» (4s¹)',
       mistakes=['спаривают p-электроны до заполнения всех орбиталей (у N считают один неспаренный)',
                 'у Cr и Cu забывают «провал» электрона', 'путают число неспаренных с числом внешних электронов',
                 'у Fe, Mn ищут неспаренные на внешнем 4s-подуровне'],
       solve=_solve_unpaired, kes=K1,
       fidelity=fid(1, 'ЕГЭ', trap='правило Хунда (N, P — 3; O, S — 2); d-элементы: неспаренные только на 3d у Mn, Fe; '
                                    'у Cr, Cu — неспаренный 4s-электрон', scale=TIME_E1, kes=['1.1']))
def g_unpaired(rng):
    pid = 'ch-ege-01-unpaired'
    mode = rng.choice(UNP_MODES)
    cf = {s: cfg_cells(s) for s in E}
    u = lambda s: sub_unpaired(cf[s])
    if mode in ('count', 'zero'):
        pool = MAIN + (DCOMMON if rng.random() < 0.4 else [])
        v = 0 if mode == 'zero' else rng.choice([1, 2, 3])
        pred = lambda s: u(s) == v
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        if v == 0:
            q = rng.choice([f'Укажите два элемента ряда, атомы которых {GS} не имеют ни одного неспаренного электрона.',
                            f'У атомов каких двух элементов ряда {GS} все электроны спарены?'])
        else:
            w = {1: 'один неспаренный электрон', 2: 'два неспаренных электрона', 3: 'три неспаренных электрона'}[v]
            q = rng.choice([f'Укажите два элемента ряда, атомы которых {GS} имеют ровно {w}.',
                            f'У атомов каких двух элементов ряда {GS} число неспаренных электронов равно {v}?'])
        lines = [f'{s} ({val_text(s)}) — {u(s)}' for s in items]
        head = 'Неспаренные электроны: '
    elif mode == 'same':
        pool = MAIN + (DCOMMON if rng.random() < 0.4 else [])
        items, v = pick_pair(rng, pool, u)
        pred = pair_pred(items, u)
        q = rng.choice([f'Укажите два элемента ряда, у атомов которых {GS} равное число неспаренных электронов.',
                        f'Атомы каких двух элементов ряда {GS} имеют одно и то же число неспаренных электронов?'])
        lines = [f'{s} ({val_text(s)}) — {u(s)}' for s in items]
        head = 'Неспаренные электроны: '
    elif mode == 'outer1':
        pool = MAIN + DCOMMON
        f = lambda s: sub_unpaired(cf[s], outer=True)
        pred = lambda s: f(s) == 1
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        q = rng.choice([f'Укажите два элемента ряда, у атомов которых {GS} на внешнем уровне находится ровно один '
                        f'неспаренный электрон.',
                        f'У атомов каких двух элементов ряда {GS} внешний энергетический уровень содержит единственный '
                        f'неспаренный электрон?'])
        lines = [f'{s} ({val_text(s)}) — {f(s)}' for s in items]
        head = 'Неспаренные электроны внешнего уровня: '
    elif mode == 's':
        pool = MAIN + DCOMMON
        f = lambda s: sub_unpaired(cf[s], l=0)
        pred = lambda s: f(s) > 0
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        q = f'Укажите два элемента ряда, у атомов которых {GS} есть неспаренный электрон на s-подуровне.'
        lines = [f'{s} ({val_text(s)})' for s in items]
        head = 'Валентные подуровни: '
    elif mode == 'p1':
        pool = MAIN
        f = lambda s: sub_unpaired(cf[s], l=1)
        pred = lambda s: f(s) == 1
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        q = f'Укажите два элемента ряда, у атомов которых {GS} на p-подуровне находится ровно один неспаренный электрон.'
        lines = [f'{s} ({val_text(s)}) — {f(s)}' for s in items]
        head = 'Неспаренные p-электроны: '
    elif mode == 'donly':
        pool = [s for s in MAIN if u(s) > 0] + DBLK
        pred = lambda s: u(s) > 0 and sub_unpaired(cf[s], l=2) == u(s)
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        q = f'Укажите два элемента ряда, у атомов которых {GS} все неспаренные электроны расположены на d-подуровне.'
        lines = [f'{s} ({val_text(s)})' for s in items]
        head = 'Валентные подуровни: '
    else:
        f = lambda s: sub_unpaired(cf[s], l=2)
        items, v = pick_pair(rng, DBLK, f)
        pred = pair_pred(items, f)
        q = f'Укажите два элемента ряда, атомы которых {GS} имеют равное число неспаренных электронов на d-подуровне.'
        lines = [f'{s} ({val_text(s)}) — {f(s)}' for s in items]
        head = 'Неспаренные d-электроны: '
    p = {'mode': mode}
    if mode == 'count':
        p['v'] = v
    return row_card(pid, rng, items, pred, q, [head + lines[0]] + lines[1:], p)


def valence_e(s):
    """Валентные электроны: s/p-элементы — внешний слой, d-элементы — (n−1)d + ns (только до d⁵)."""
    cells = cfg_cells(s)
    n = outer_n(cells)
    if E[s]['sub'] == 'B':
        return cells.get((n, 0), 0) + cells.get((n - 1, 2), 0)
    return outer_count(cells)


OUT_MODES = ['count', 'same', 'same', 'formula', 'valence', 'valsame', 'sonly']
DVAL = ['Sc', 'Ti', 'V', 'Cr', 'Mn']


def _solve_outer(p):
    m, row = p['mode'], p['row']
    zs = {s: z_of(s) for s in row}

    def val(Z):
        occ, _ = aufbau(Z)
        n = r_period(Z)
        return occ.get((n, 0), 0) + occ.get((n - 1, 2), 0) if r_block(Z) == 'd' else r_outer(Z)
    if m == 'count':
        f = lambda s: r_outer(zs[s]) == p['v']
    elif m == 'same':
        vals = [r_outer(zs[s]) for s in row]
        f = lambda s: vals.count(r_outer(zs[s])) == 2
    elif m == 'formula':
        f = lambda s: r_block(zs[s]) != 'd' and r_outer(zs[s]) == p['v']
    elif m == 'valence':
        f = lambda s: val(zs[s]) == p['v']
    elif m == 'valsame':
        vals = [val(zs[s]) for s in row]
        f = lambda s: vals.count(val(zs[s])) == 2
    else:
        f = lambda s: r_block(zs[s]) == 's'
    return ids_of(row, f)


@proto('ch-ege-01-outer', 'ЕГЭ', 1, 'Электроны внешнего уровня и валентные электроны',
       invariant='по положению в ПСХЭ определить число электронов внешнего уровня (формулу внешнего уровня) или число '
                 'валентных электронов',
       varies='ряд; что спрашивают: заданное число внешних электронов, «одинаковое число» (пара), формула внешнего '
              'уровня ns¹ / ns² / ns²np⁴…, число валентных электронов (в т. ч. у d-элементов), все валентные '
              'электроны на s-подуровне',
       answer_rule='у элементов главных подгрупп внешних (валентных) электронов = номер группы; у d-элементов внешний '
                   'уровень — ns (1 у Cr и Cu, 2 у остальных), валентные — (n−1)d + ns',
       mistakes=['у d-элементов считают внешними и d-электроны', 'путают номер периода и число внешних электронов',
                 'считают Zn s-элементом', 'не учитывают «провал» электрона у Cr, Cu'],
       solve=_solve_outer, kes=K1,
       fidelity=fid(1, 'ЕГЭ', trap='у Fe, Mn, Zn на внешнем уровне 2 электрона (как у Mg), у Cr и Cu — 1 (как у Na); '
                                    'у Cr 6 валентных электронов, как у S', scale=TIME_E1, kes=['1.1']))
def g_outer(rng):
    pid = 'ch-ege-01-outer'
    oc = lambda s: outer_count(cfg_cells(s))
    mode = rng.choice(OUT_MODES)
    p = {'mode': mode}
    if mode == 'count':
        pool = MAIN + (DCOMMON if rng.random() < 0.5 else [])
        v = rng.randint(1, 7)
        pred = lambda s: oc(s) == v
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        q = (f'Укажите два элемента ряда, у атомов которых {GS} на внешнем энергетическом уровне находится '
             f'{v} {plural(v, "электрон", "электрона", "электронов")}.')
        p['v'] = v
        f = oc
    elif mode == 'same':
        pool = MAIN + (DCOMMON if rng.random() < 0.5 else [])
        items, v = pick_pair(rng, pool, oc)
        pred = pair_pred(items, oc)
        q = rng.choice([f'Укажите два элемента ряда, атомы которых {GS} имеют равное число электронов на внешнем '
                        f'энергетическом уровне.',
                        f'Атомы каких двух элементов ряда {GS} имеют сходное строение внешнего энергетического '
                        f'уровня (одинаковое число внешних электронов)?'])
        f = oc
    elif mode == 'formula':
        v = rng.randint(1, 7)
        pred = lambda s: oc(s) == v
        items = pick_row(rng, [s for s in MAIN if pred(s)], [s for s in MAIN if not pred(s)])
        a, b = min(v, 2), max(v - 2, 0)
        fm = f'ns{str(a).translate(SUP)}' + (f'np{str(b).translate(SUP)}' if b else '')
        q = rng.choice([f'Укажите два элемента ряда, для атомов которых {GS} внешний электронный уровень описывается '
                        f'формулой {fm}.',
                        f'Электронная формула внешнего уровня атомов каких двух элементов ряда {GS} имеет вид {fm}?'])
        p['v'] = v
        f = oc
    elif mode == 'valence':
        pool = MAIN + DVAL
        v = rng.choice([3, 4, 5, 6, 7])
        pred = lambda s: valence_e(s) == v
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        q = (f'Укажите два элемента ряда, атомы которых {GS} имеют {v} '
             f'{plural(v, "валентный электрон", "валентных электрона", "валентных электронов")}.')
        p['v'] = v
        f = valence_e
    elif mode == 'valsame':
        pool = MAIN + DVAL
        items, v = pick_pair(rng, pool, valence_e)
        pred = pair_pred(items, valence_e)
        q = f'Укажите два элемента ряда, у атомов которых {GS} одинаковое число валентных электронов.'
        f = valence_e
    else:
        pool = MAIN + ['Sc', 'Ti', 'V', 'Mn', 'Fe', 'Co', 'Ni']
        pred = lambda s: block_of(s) == 's'
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        q = f'Укажите два элемента ряда, у атомов которых {GS} все валентные электроны находятся на s-подуровне.'
        f = valence_e
    lines = [f'{s}: {val_text(s)} — {f(s)}' for s in items]
    return row_card(pid, rng, items, pred, q, ['Внешние (валентные) электроны: ' + lines[0]] + lines[1:], p)


def block_of(s):
    e = E[s]
    if e['sub'] == 'B':
        return 'd'
    return 's' if e['group'] <= 2 and s != 'He' else 'p'


NOBLE = {'He': 2, 'Ne': 10, 'Ar': 18, 'Kr': 36}
ION_POOL = ['Li', 'Na', 'K', 'Be', 'Mg', 'Ca', 'Sr', 'Ba', 'Al', 'N', 'O', 'F', 'P', 'S', 'Cl', 'Se', 'Br', 'I', 'As']


def ion_q(s):
    e = E[s]
    return e['group'] if e['kind'] == 'm' else e['group'] - 8


def ion_str(s, q=None):
    q = ion_q(s) if q is None else q
    mag = '' if abs(q) == 1 else str(abs(q))
    return s + (mag + ('+' if q > 0 else '-')).translate(SUP)


def _solve_ion(p):
    zn = {'Ne': 10, 'Ar': 18, 'Kr': 36}[p['gas']]
    sign = p['sign']

    def ok(s):
        q = r_ion_charge(z_of(s))
        if q is None or (sign > 0 and q < 0) or (sign < 0 and q > 0):
            return False
        return z_of(s) - q == zn
    return ids_of(p['row'], ok)


@proto('ch-ege-01-ion', 'ЕГЭ', 1, 'Катионы/анионы с электронной конфигурацией благородного газа',
       invariant='построить простой ион элемента (металл отдаёт внешние электроны, неметалл достраивает октет) и '
                 'сравнить его конфигурацию с конфигурацией благородного газа',
       varies='ряд; благородный газ (Ne, Ar, Kr); какие ионы (катионы, анионы, любые); как задана конфигурация '
              '(название газа, полная формула, формула внешнего уровня)',
       answer_rule='число электронов иона Z − q совпадает с Z благородного газа; учитывать знак иона',
       mistakes=['берут атом, а не ион', 'выбирают неметалл, когда спрашивают о катионах',
                 'соседние по Z элементы дают ионы разных газов'],
       solve=_solve_ion, kes=K1,
       fidelity=fid(1, 'ЕГЭ', trap='изоэлектронные частицы: S²⁻, Cl⁻, K⁺, Ca²⁺ — как у Ar; в ряду есть анион того же '
                                    'газа, когда спрашивают о катионах', scale=TIME_E1, kes=['1.1']))
def g_ion(rng):
    pid = 'ch-ege-01-ion'
    sign = rng.choice([1, -1, 0])
    gases = {1: ['Ne', 'Ar'], -1: ['Ne', 'Ar', 'Kr'], 0: ['Ne', 'Ar', 'Kr']}[sign]
    gas = rng.choice(gases)
    zn = NOBLE[gas]
    pred = lambda s: E[s]['Z'] - ion_q(s) == zn and (sign == 0 or sign * ion_q(s) > 0)
    no = [s for s in ION_POOL if not pred(s)] + (['Fe', 'Cu', 'Zn'] if rng.random() < 0.3 else [])
    items = pick_row(rng, [s for s in ION_POOL if pred(s)], no)
    who = {1: 'катионы', -1: 'анионы', 0: 'простые ионы'}[sign]
    full = cfg_text(_core_cells(gas))
    outer = ''.join(x for x in re.findall(r'\d[spd][⁰¹²³⁴⁵⁶⁷⁸⁹]+', full)[-2:])
    form = rng.randrange(3)
    if form == 0:
        cond = f'имеют такую же электронную конфигурацию, как атом {E[gas]["gen"]}'
    elif form == 1:
        cond = f'имеют электронную конфигурацию {full}'
    else:
        cond = f'имеют конфигурацию внешнего энергетического уровня {outer}'
    q = rng.choice([f'Укажите два элемента ряда, {who} которых {cond}.',
                    f'Для каких двух элементов ряда {who}, образуемые в соединениях, {cond}?'])
    lines = []
    for s in items:
        if s in ION_POOL and sign < 0 and ion_q(s) > 0:
            lines.append(f'{s} — металл, анионов не образует')
        elif s in ION_POOL and sign > 0 and ion_q(s) < 0:
            lines.append(f'{s} — неметалл, простых катионов не образует')
        elif s in ION_POOL:
            lines.append(f'{ion_str(s)} — {E[s]["Z"] - ion_q(s)} e')
        else:
            lines.append(f'{s} — d-элемент, его ионы не имеют конфигурации благородного газа')
    return row_card(pid, rng, items, pred, q, [f'У атома {gas} {zn} электронов; ' + lines[0]] + lines[1:],
                    {'gas': gas, 'sign': sign})


REF_PARTICLES = [('Na', 1), ('Mg', 2), ('Al', 3), ('K', 1), ('Ca', 2), ('F', -1), ('O', -2), ('Cl', -1), ('S', -2),
                 ('N', -3), ('Li', 1), ('Fe', 2), ('Fe', 3), ('Mn', 2), ('Cu', 1), ('Zn', 2), ('Cr', 3), ('Ne', 0),
                 ('Ar', 0), ('Na', 0), ('Mg', 0), ('K', 0), ('Ca', 0), ('P', 0), ('Cl', 0), ('Be', 0), ('Cr', 0),
                 ('Cu', 0), ('Br', -1), ('Se', -2)]
SUB_GEN = {'s': 's-электронов', 'p': 'p-электронов', 'd': 'd-электронов'}


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
    """Частица словами, как в КИМ: «атом неона», «катион натрия», «катион железа(III)», «анион серы»."""
    if q == 0:
        return f'атом {E[sym]["gen"]}'
    if q > 0:
        pos = [x for x in E[sym]['ox'] if x > 0]
        return f'катион {E[sym]["gen"]}' + (f'({ROMAN[q]})' if len(pos) > 1 else '')
    return f'анион {E[sym]["gen"]}'


def _solve_sublevel(p):
    sub, row, m = p['sub'], p['row'], p['mode']
    if m == 'ref':
        ref = r_counts(z_of(p['ref'][0]), p['ref'][1])[sub]
        return ids_of(row, lambda s: r_counts(z_of(s))[sub] == ref)
    if m == 'ionref':
        ref = r_counts(z_of(p['ref'][0]), p['ref'][1])[sub]
        return ids_of(row, lambda s: r_ion_charge(z_of(s)) is not None and
                      r_counts(z_of(s), r_ion_charge(z_of(s)))[sub] == ref)
    if m == 'exact':
        return ids_of(row, lambda s: r_counts(z_of(s))[sub] == p['v'])
    vals = [r_counts(z_of(s))[sub] for s in row]
    return ids_of(row, lambda s: vals.count(r_counts(z_of(s))[sub]) == 2)


@proto('ch-ege-01-sublevel', 'ЕГЭ', 1, 'Число s-, p- или d-электронов атома/иона',
       invariant='записать полную электронную конфигурацию и сосчитать все электроны одного типа подуровня '
                 '(s, p или d) у атома или иона',
       varies='ряд; тип подуровня; условие: как у частицы-эталона (атом, катион, анион), «одинаковое число» (пара), '
              'заданное число d-электронов (5, 10), ионы элементов ряда против атома-эталона',
       answer_rule='совпадает суммарное число электронов на всех подуровнях данного типа',
       mistakes=['считают только внешний подуровень, а не все s (p, d)', 'забывают снять/добавить электроны у иона',
                 'у Cr, Cu не учитывают провал (s-электронов на один меньше)'],
       solve=_solve_sublevel, kes=K1,
       fidelity=fid(1, 'ЕГЭ', trap='как в демоверсии 2027: число s-электронов как у катиона натрия; Cr и Mn — по пять '
                                    'd-электронов', scale=TIME_E1, kes=['1.1']))
def g_sublevel(rng):
    pid = 'ch-ege-01-sublevel'
    mode = rng.choice(['ref', 'ref', 'ionref', 'exact', 'same'])
    sub = rng.choice(['s', 's', 'p', 'p', 'd'])
    pool = MAIN + DBLK
    p = {'mode': mode, 'sub': sub}
    if mode in ('ref', 'ionref'):
        refs = [r for r in REF_PARTICLES if counts(*r)[sub] > 0]
        ref = rng.choice(refs)
        v = counts(*ref)[sub]
        pn = particle_name(*ref)
        if mode == 'ref':
            pool = [s for s in pool if not (s == ref[0] and ref[1] == 0)]
            f = lambda s: counts(s)[sub]
            q = f'Укажите два элемента ряда, атомы которых {GS} содержат такое же общее число {SUB_GEN[sub]}, как и {pn}.'
        else:
            pool = [s for s in ION_POOL if s != ref[0]]
            f = lambda s: counts(s, ion_q(s))[sub]
            q = f'Укажите два элемента ряда, простые ионы которых содержат столько же {SUB_GEN[sub]}, сколько и {pn}.'
        pred = lambda s: f(s) == v
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        p['ref'] = list(ref)
        head = f'{pn[0].upper() + pn[1:]}: {v}; '
    elif mode == 'exact':
        sub = 'd'
        p['sub'] = 'd'
        v = rng.choice([5, 10])
        f = lambda s: counts(s)['d']
        pred = lambda s: f(s) == v
        pool = DBLK + [s for s in MAIN if E[s]['period'] >= 4 or rng.random() < 0.3]
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        q = rng.choice([f'Укажите два элемента ряда, атомы которых {GS} содержат ровно {v} d-электронов.',
                        f'В атомах каких двух элементов ряда {GS} общее число d-электронов равно {v}?'])
        p['v'] = v
        head = ''
    else:
        f = lambda s: counts(s)[sub]
        items, v = pick_pair(rng, [s for s in pool if f(s) > 0], f)
        pred = pair_pred(items, f)
        q = f'Укажите два элемента ряда, в атомах которых {GS} одинаковое общее число {SUB_GEN[sub]}.'
        head = ''
    if mode == 'ionref':
        lines = [f'{ion_str(s)} — {f(s)}' for s in items]
    else:
        lines = [f'{s} — {f(s)}' for s in items]
    return row_card(pid, rng, items, pred, q, [head + f'{sub}-электронов: ' + lines[0]] + lines[1:], p)


EXC = {2: 'ns¹np¹', 3: 'ns¹np²', 4: 'ns¹np³'}


def _solve_excited(p):
    if p['mode'] == 'formula':
        return ids_of(p['row'], lambda s: r_block(z_of(s)) != 'd' and r_outer(z_of(s)) == p['g'])
    # число неспаренных в возбуждённом состоянии: один s-электрон переходит на свободную p-орбиталь того же уровня
    def exc(Z):
        occ, _ = aufbau(Z)
        n = r_period(Z)
        s_, p_ = occ.get((n, 0), 0), occ.get((n, 1), 0)
        if s_ == 2 and p_ < 3 and Z > 2:
            return 2 + p_
        return None
    return ids_of(p['row'], lambda s: exc(z_of(s)) == p['v'])


@proto('ch-ege-01-excited', 'ЕГЭ', 1, 'Возбуждённое состояние атома',
       invariant='при возбуждении один электрон ns-подуровня переходит на свободную np-орбиталь того же уровня',
       varies='ряд; вопрос: формула внешнего уровня в возбуждённом состоянии (ns¹np¹, ns¹np², ns¹np³) или число '
              'неспаренных электронов в возбуждённом состоянии (2, 3, 4)',
       answer_rule='ns¹np^(k−1) и k неспаренных электронов — у элементов II–IV групп главных подгрупп',
       mistakes=['путают основное и возбуждённое состояния', 'считают, что у N, O, F число неспаренных при '
                 'возбуждении растёт', 'берут элементы соседней группы'],
       solve=_solve_excited, kes=K1,
       fidelity=fid(1, 'ЕГЭ', trap='в основном состоянии у C и Si два неспаренных, в возбуждённом — четыре',
                    scale=TIME_E1, kes=['1.1']))
def g_excited(rng):
    pid = 'ch-ege-01-excited'
    g = rng.choice([2, 3, 4])
    pool = [s for s in MAIN if s not in ('H',)]
    if rng.random() < 0.5:
        pool = [s for s in pool if E[s]['group'] in (1, 2, 3, 4) or s in ('P', 'As')]
        pred = lambda s: E[s]['group'] == g
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        q = rng.choice([f'Укажите два элемента ряда, атомы которых в возбуждённом состоянии имеют {g} '
                        f'{plural(g, "неспаренный электрон", "неспаренных электрона", "неспаренных электронов")}.',
                        f'У атомов каких двух элементов ряда при переходе в возбуждённое состояние число неспаренных '
                        f'электронов становится равным {g}?'])
        lines = [f'{s}: {val_text(s)}' for s in items]
        return row_card(pid, rng, items, pred, q, [f'Распаривание ns²: {g} неспаренных у элементов группы {ROMAN[g]}A; '
                                                   + lines[0]] + lines[1:], {'mode': 'unp', 'v': g})
    pred = lambda s: E[s]['group'] == g
    items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
    q = rng.choice([f'Укажите два элемента ряда, для атомов которых в возбуждённом состоянии внешний уровень '
                    f'описывается формулой {EXC[g]}.',
                    f'Для атомов каких двух элементов ряда возбуждённому состоянию соответствует конфигурация внешнего '
                    f'уровня {EXC[g]}?'])
    lines = [f'{s}: {val_text(s)}' for s in items]
    return row_card(pid, rng, items, pred, q, [f'{EXC[g]} получается из ns²np{str(g - 2).translate(SUP) if g > 2 else "⁰"} '
                                               f'(группа {ROMAN[g]}A); ' + lines[0]] + lines[1:], {'mode': 'formula', 'g': g})


# ================================================================= ЕГЭ 2. Закономерности изменения свойств (последовательность)
K2 = ['1.2']
LINES_P = {2: ['Li', 'Be', 'B', 'C', 'N', 'O', 'F'], 3: ['Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl'],
           4: ['K', 'Ca', 'Ga', 'Ge', 'As', 'Se', 'Br']}
LINES_G = {1: ['Li', 'Na', 'K'], 2: ['Be', 'Mg', 'Ca', 'Sr', 'Ba'], 3: ['B', 'Al', 'Ga'], 4: ['C', 'Si', 'Ge'],
           5: ['N', 'P', 'As'], 6: ['O', 'S', 'Se'], 7: ['F', 'Cl', 'Br', 'I']}
HYDR = {'C', 'Si', 'N', 'O', 'F', 'P', 'S', 'Cl', 'As', 'Se', 'Br', 'I'}
POOL2 = [s for s in MAIN if s not in ('H', 'Ge')] + ['Sc', 'Ti', 'V', 'Cr', 'Mn', 'Zn']
# отбор трёх элементов: подпись в условии и признак (путь генератора — по таблице)
SEL = {
    'period': ('три элемента одного периода', None),
    'group': ('три элемента одной группы (главной подгруппы)', None),
    'p': ('три p-элемента', lambda s: E[s]['sub'] == 'A' and E[s]['group'] >= 3),
    's': ('три s-элемента', lambda s: E[s]['sub'] == 'A' and E[s]['group'] <= 2),
    'd': ('три d-элемента', lambda s: E[s]['sub'] == 'B'),
    'metal': ('три элемента-металла', lambda s: E[s]['kind'] == 'm'),
    'nonmetal': ('три элемента-неметалла', lambda s: E[s]['kind'] == 'n'),
    'small': ('три элемента малых периодов', lambda s: E[s]['period'] <= 3),
    'hydride': ('три элемента, для которых известны летучие водородные соединения', lambda s: s in HYDR),
}
# свойство: (фразы «в порядке … <фраза>» для возрастания/убывания, знак вдоль периода, вдоль группы (None — число),
#            допустимые способы отбора, фильтр элементов)
PROPS2 = {
    'radius': (('возрастания', 'уменьшения'), 'атомного радиуса', -1, 1,
               ['period', 'group', 'p', 's', 'metal', 'nonmetal', 'small'], lambda s: E[s]['sub'] == 'A'),
    'en': (('возрастания', 'уменьшения'), 'электроотрицательности', 1, -1,
           ['period', 'group', 'p', 'nonmetal', 'small', 'hydride'], lambda s: E[s]['sub'] == 'A' and s not in ('Ga', 'Ge')),
    'reduc_m': (('усиления', 'ослабления'), 'восстановительных свойств образуемых ими простых веществ', -1, 1,
                ['period', 'group', 's', 'metal'], lambda s: E[s]['kind'] == 'm' and E[s]['sub'] == 'A'),
    'reduc_n': (('усиления', 'ослабления'), 'восстановительных свойств соответствующих им простых веществ', -1, 1,
                ['nonmetal', 'p', 'group'], lambda s: E[s]['kind'] == 'n' and s not in ('H', 'B')),
    'oxid': (('усиления', 'ослабления'), 'окислительной способности образуемых ими простых веществ', 1, -1,
             ['nonmetal', 'p', 'period', 'group'], lambda s: E[s]['kind'] == 'n' and s not in ('H', 'B')),
    'acid_ox': (('усиления', 'ослабления'), 'кислотных свойств образуемых ими высших оксидов', 1, -1,
                ['period', 'nonmetal', 'p', 'group'],
                lambda s: E[s]['sub'] == 'A' and s not in ('O', 'F', 'H', 'Br', 'I')),
    'base': (('усиления', 'ослабления'), 'осно́вных свойств образуемых ими гидроксидов', -1, 1,
             ['period', 'group', 's', 'metal'], lambda s: E[s]['kind'] == 'm' and E[s]['sub'] == 'A'),
    'hyd_acid': (('усиления', 'ослабления'), 'кислотных свойств образуемых ими летучих водородных соединений', 1, 1,
                 ['hydride', 'period', 'group', 'nonmetal'], lambda s: s in HYDR and s not in ('C', 'Si')),
    'hyd_val': (('возрастания', 'уменьшения'), 'валентности в летучих водородных соединениях', None, None,
                ['hydride', 'p', 'nonmetal', 'period'], lambda s: s in HYDR),
    'hiox': (('возрастания', 'уменьшения'), 'степени окисления в высших оксидах', None, None,
             ['d', 'metal', 'period', 'p', 'small'],
             lambda s: s not in ('O', 'F', 'H', 'Fe', 'Co', 'Ni', 'Cu', 'Br', 'I')),
}
PHR2 = {'radius': ('радиус их атомов', 'увеличивался', 'уменьшался'),
        'en': ('электроотрицательность элементов', 'возрастала', 'снижалась'),
        'oxid': ('окислительная активность соответствующих простых веществ', 'возрастала', 'снижалась'),
        'reduc_m': ('восстановительная активность соответствующих металлов', 'возрастала', 'снижалась'),
        'reduc_n': ('восстановительная активность соответствующих простых веществ', 'возрастала', 'снижалась'),
        'acid_ox': ('кислотный характер их высших оксидов', 'усиливался', 'ослабевал'),
        'base': ('осно́вный характер их гидроксидов', 'усиливался', 'ослабевал'),
        'hyd_acid': ('кислотность их летучих водородных соединений', 'росла', 'снижалась'),
        'hyd_val': ('валентность элемента в летучем водородном соединении', 'росла', 'снижалась'),
        'hiox': ('максимальная степень окисления элемента в оксидах', 'росла', 'снижалась')}
GROUP_OK = {'acid_ox': {1, 2, 3, 4, 5, 7}, 'base': {1, 2}, 'hyd_acid': {6, 7}, 'reduc_n': {6, 7}, 'oxid': {5, 6, 7},
            'reduc_m': {1, 2}}


def num_val(prop, s):
    return 8 - E[s]['group'] if prop == 'hyd_val' else ox_max(s)


def chain_order(els, key_cmp):
    """Единственный порядок по возрастанию; None, если правило не определяет его однозначно."""
    good = []
    for perm in itertools.permutations(els):
        if all((c := key_cmp(perm[i], perm[j])) is None or c < 0
               for i in range(len(perm)) for j in range(i + 1, len(perm))):
            good.append(perm)
    return list(good[0]) if len(good) == 1 else None


def rule_cmp(dp, dg, per, grp):
    def cmp(a, b):
        if per(a) == per(b):
            return None if grp(a) == grp(b) else (dp if grp(a) > grp(b) else -dp)
        if grp(a) == grp(b):
            return dg if per(a) > per(b) else -dg
        return None
    return cmp


def _solve_seq(p):
    """Второй путь: отбор и порядок по электронной конфигурации (Z → период, группа, семейство, металличность)."""
    row, sel, prop = p['row'], p['sel'], p['prop']
    zs = {s: z_of(s) for s in row}
    per = lambda s: r_period(zs[s])
    grp = lambda s: r_valence(zs[s])
    blk = lambda s: r_block(zs[s])
    if sel in ('period', 'group'):
        key = per if sel == 'period' else (lambda s: (grp(s), blk(s) == 'd'))
        cnt = {}
        for s in row:
            cnt.setdefault(key(s), []).append(s)
        trip = [v for v in cnt.values() if len(v) == 3][0]
    else:
        test = {'p': lambda s: blk(s) == 'p', 's': lambda s: blk(s) == 's', 'd': lambda s: blk(s) == 'd',
                'metal': lambda s: r_metal(zs[s]), 'nonmetal': lambda s: not r_metal(zs[s]),
                'small': lambda s: per(s) <= 3,
                'hydride': lambda s: not r_metal(zs[s]) and r_outer(zs[s]) >= 4}[sel]
        trip = [s for s in row if test(s)]
    assert len(trip) == 3
    rules = {'radius': (-1, 1), 'en': (1, -1), 'reduc_m': (-1, 1), 'reduc_n': (-1, 1), 'oxid': (1, -1),
             'acid_ox': (1, -1), 'base': (-1, 1), 'hyd_acid': (1, 1)}
    if prop in rules:
        order = chain_order(trip, rule_cmp(*rules[prop], per, grp))
    else:
        val = (lambda s: 8 - r_outer(zs[s])) if prop == 'hyd_val' else (lambda s: r_higher_ox(zs[s]))
        order = sorted(trip, key=val)
    if not p['asc']:
        order = order[::-1]
    return ''.join(str(row.index(s) + 1) for s in order)


def seq_card(pid, rng, props):
    prop = rng.choice(props)
    (up, down), word, dp, dg, sels, flt = PROPS2[prop]
    sel = rng.choice(sels)
    per = lambda s: E[s]['period']
    grp = lambda s: E[s]['group']
    pool = POOL2
    if sel in ('period', 'group'):
        attr = 'period' if sel == 'period' else 'group'
        lines = {}
        for s in pool:
            if E[s]['sub'] == 'A' and flt(s):
                lines.setdefault(E[s][attr], []).append(s)
        if sel == 'group' and prop in GROUP_OK:
            lines = {k: v for k, v in lines.items() if k in GROUP_OK[prop]}
        lines = {k: v for k, v in lines.items() if len(v) >= 3}
        if not lines:
            raise Retry
        k = rng.choice(list(lines))
        triple = rng.sample(lines[k], 3)
        if sel == 'period':
            others = [s for s in pool if E[s]['period'] != k]
        else:
            others = [s for s in pool if not (E[s]['group'] == k and E[s]['sub'] == 'A')]
        two = rng.sample(others, 2)
    else:
        test = SEL[sel][1]
        yes = [s for s in pool if test(s) and flt(s)]
        no = [s for s in pool if not test(s) and not (sel == 'hydride' and s == 'B')]
        if len(yes) < 3:
            raise Retry
        triple = rng.sample(yes, 3)
        two = rng.sample(no, 2)
    if prop == 'acid_ox' and all(E[x]['kind'] == 'm' for x in triple):
        raise Retry   # для металлов спрашиваем об осно́вном характере (прототип base)
    if prop == 'radius' and {'Al', 'Ga'} <= set(triple):
        raise Retry   # по школьному правилу Al < Ga, а реальный радиус Ga меньше (d-сжатие)
    if dp is None:
        vals = [num_val(prop, s) for s in triple]
        if len(set(vals)) < 3:
            raise Retry
        order = sorted(triple, key=lambda s: num_val(prop, s))
    else:
        order = chain_order(triple, rule_cmp(dp, dg, per, grp))
        if order is None:
            raise Retry
    items = triple + two
    rng.shuffle(items)
    asc = rng.random() < 0.5
    seq = order if asc else order[::-1]
    ans = ''.join(str(items.index(s) + 1) for s in seq)
    how = up if asc else down
    noun, vu, vd = PHR2[prop]
    q = (f'Из указанных в ряду химических элементов выберите {SEL[sel][0]}. Расположите выбранные элементы так, '
         f'чтобы {noun} {vu if asc else vd}. ' + rng.choice(['Запишите номера выбранных элементов в нужной '
                                                             'последовательности.',
                                                             'Запишите в поле ответа номера выбранных элементов в '
                                                             'нужной последовательности.']))
    desc = ', '.join(f'{s} ({E[s]["period"]}-й период, {ROMAN[E[s]["group"]]}{E[s]["sub"]})' for s in triple)
    if dp is None:
        rule = '; '.join(f'{s}: {num_val(prop, s)}' for s in triple)
    else:
        rule = ('в периоде слева направо ' + ('растёт' if dp > 0 else 'уменьшается') + ', в группе сверху вниз ' +
                ('растёт' if dg > 0 else 'уменьшается'))
    e = f'Отбор: {desc}. {word[0].upper() + word[1:]}: {rule}. Порядок {how}: {" → ".join(seq)}; ответ {ans}.'
    return pcard(pid, q, ans, e, k='num', o=opts(items), p={'row': items, 'prop': prop, 'sel': sel, 'asc': asc},
                 wrong=[ans[::-1], ans[1] + ans[0] + ans[2], ans[0] + ans[2] + ans[1]])


FID2 = dict(fmt_='три цифры — номера элементов в нужной последовательности (порядок важен), как в КИМ 2027')
SC2 = ('ряд из пяти элементов; отбор по признаку (один период/группа, p-, s-, d-элементы, металлы, неметаллы, '
       'малые периоды, летучие водородные соединения), как в банке')


def _p2(pid, title, props, invariant, answer_rule, mistakes, trap):
    def gen(rng):
        return seq_card(pid, rng, props)
    gen.__name__ = 'g_' + pid.replace('-', '_')
    proto(pid, 'ЕГЭ', 2, title, invariant=invariant,
          varies='ряд из пяти элементов, признак отбора трёх элементов, свойство, возрастание/убывание',
          answer_rule=answer_rule, mistakes=mistakes, solve=_solve_seq, kes=K2,
          fidelity=fid(2, 'ЕГЭ', trap=trap, scale=SC2, kes=['1.2'], **FID2))(gen)


_p2('ch-ege-02-radius', 'Отбор трёх элементов и порядок изменения атомного радиуса', ['radius'],
    'отобрать три элемента по признаку и упорядочить по радиусу атома (правила периода и группы, при необходимости — '
    'через общий элемент)',
    'в периоде слева направо радиус уменьшается, в группе сверху вниз — увеличивается',
    ['считают, что в периоде радиус растёт с зарядом ядра', 'путают направление («уменьшения»)',
     'отбирают не те три элемента'],
    'направление в периоде и группе противоположно; отбор p-/s-элементов или металлов вместо «одного периода»')
_p2('ch-ege-02-en', 'Порядок изменения электроотрицательности и окислительных свойств', ['en', 'oxid'],
    'отобрать три элемента и упорядочить по ЭО атомов (окислительной способности простых веществ)',
    'в периоде слева направо ЭО и окислительные свойства растут, в группе сверху вниз — уменьшаются',
    ['путают направление в группе', 'считают кислород электроотрицательнее фтора'],
    'направления в периоде и группе противоположны')
_p2('ch-ege-02-reduc', 'Порядок изменения восстановительных (металлических) свойств простых веществ',
    ['reduc_m', 'reduc_n'],
    'отобрать три металла (неметалла) и упорядочить по восстановительным свойствам простых веществ',
    'восстановительные свойства усиливаются справа налево в периоде и сверху вниз в группе',
    ['путают усиление и ослабление', 'в периоде ставят металл с большим зарядом ядра активнее'],
    'у неметаллов восстановительные свойства растут вниз по группе (I₂ > Br₂ > Cl₂)')
_p2('ch-ege-02-acidbase', 'Порядок изменения кислотно-основных свойств высших оксидов и гидроксидов',
    ['acid_ox', 'base'],
    'отобрать три элемента и упорядочить по кислотным свойствам высших оксидов (основным свойствам гидроксидов)',
    'в периоде слева направо кислотные свойства высших оксидов/гидроксидов усиливаются, основные ослабевают; в группе '
    'сверху вниз — наоборот',
    ['переносят рост кислотности водородных соединений в группе на оксиды', 'путают оксиды и гидроксиды'],
    'кислотность высших оксидов в группе падает, а водородных соединений — растёт')
_p2('ch-ege-02-hydrides', 'Летучие водородные соединения: кислотные свойства и валентность', ['hyd_acid', 'hyd_val'],
    'отобрать три элемента, образующих летучие водородные соединения, и упорядочить по кислотным свойствам этих '
    'соединений или по валентности элемента в них',
    'кислотные свойства растут и слева направо, и сверху вниз; валентность в летучем водородном соединении = 8 − N',
    ['переносят закономерность ЭО на кислотность (HF считают самой сильной)', 'валентность = N вместо 8 − N'],
    'HF — самая слабая из галогеноводородных кислот; CH₄ — валентность IV, NH₃ — III')
_p2('ch-ege-02-hiox', 'Порядок изменения степени окисления (валентности) в высших оксидах', ['hiox'],
    'отобрать три элемента (в т. ч. d-элементы) и упорядочить по степени окисления в высших оксидах',
    'степень окисления в высшем оксиде = номер группы (Sc +3, Ti +4, V +5, Cr +6, Mn +7, Zn +2)',
    ['для d-элементов берут число внешних электронов', 'путают направление'],
    'd-элементы: Mn (+7) выше Cr (+6), хотя оба имеют d⁵')


# ================================================================= ЕГЭ 3. Степень окисления, валентность
K3 = ['1.3']
OXIDE_T = {1: 'Э₂O', 2: 'ЭO', 3: 'Э₂O₃', 4: 'ЭO₂', 5: 'Э₂O₅', 6: 'ЭO₃', 7: 'Э₂O₇'}
HYD_T = {4: 'ЭH₄', 5: 'ЭH₃', 6: 'H₂Э', 7: 'HЭ'}
POOL3 = [s for s in MAIN if s not in ('Ge', 'B')] + ['Cr', 'Mn', 'Zn', 'V', 'Ti', 'Sc']


def _ox_line(s):
    ox = E[s]['ox']
    return f'{s}: ' + (', '.join(signed(x) for x in ox) if ox else '0')


def r_hi(Z):
    """Высшая степень окисления (второй путь): номер группы; у O — +2 (OF₂), у F — 0."""
    return {8: 2, 9: 0}.get(Z, r_higher_ox(Z))


def _solve_maxox(p):
    if p['mode'] == 'same':
        vals = [r_hi(z_of(s)) for s in p['row']]
        return ids_of(p['row'], lambda s: vals.count(r_hi(z_of(s))) == 2)
    return ids_of(p['row'], lambda s: r_hi(z_of(s)) == p['v'])


@proto('ch-ege-03-maxox', 'ЕГЭ', 3, 'Степень окисления в высших оксидах (гидроксидах)',
       invariant='высшая степень окисления элемента (в высшем оксиде и гидроксиде) равна номеру группы',
       varies='ряд (главные и побочные подгруппы: Cr, Mn, V, Ti, Sc, Zn), значение +1…+7 или «одинаковая» (пара), '
              'формулировка (в высших оксидах / в высших гидроксидах)',
       answer_rule='выбрать два элемента с нужным номером группы (для пары — два элемента одной группы, в т. ч. A и B)',
       mistakes=['для d-элементов берут число внешних электронов (Mn → +2)', 'путают высшую и низшую степени '
                 'окисления'],
       solve=_solve_maxox, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='элементы побочных подгрупп: Cr +6 как у S, Mn +7 как у Cl', scale=TIME_E1,
                    kes=['1.3']))
def g_maxox(rng):
    pid = 'ch-ege-03-maxox'
    pool = [s for s in POOL3 if s not in ('O', 'F', 'H', 'Br', 'I')]   # у Br, I высшие оксиды не получены
    if rng.random() < 0.35:
        items, v = pick_pair(rng, pool, ox_max)
        pred = pair_pred(items, ox_max)
        q = rng.choice(['Укажите два элемента ряда, которые в высших оксидах имеют одну и ту же степень окисления.',
                        'Для каких двух элементов ряда степени окисления в высших оксидах совпадают?'])
        p = {'mode': 'same'}
    else:
        v = rng.randint(1, 7)
        pred = lambda s: ox_max(s) == v
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        q = rng.choice([f'Укажите два элемента ряда, у которых в высшем оксиде степень окисления элемента равна '
                        f'{signed(v)}.',
                        f'Укажите два элемента ряда, у которых в высшем гидроксиде степень окисления элемента равна '
                        f'{signed(v)}.',
                        f'Укажите два элемента ряда, для которых максимальное значение степени окисления равно '
                        f'{signed(v)}.'])
        p = {'mode': 'v', 'v': v}
    lines = [f'{s} — {signed(ox_max(s))}' for s in items]
    return row_card(pid, rng, items, pred, q, ['Высшие степени окисления: ' + lines[0]] + lines[1:], p)


def _solve_minox(p):
    lo = lambda s: r_lower_ox(z_of(s))
    if p['mode'] == 'same':
        # все пары с совпадающей низшей степенью окисления (у металлов — 0); верная пара должна быть единственной
        vals = [lo(s) for s in p['row']]
        return ids_of(p['row'], lambda s: vals.count(lo(s)) >= 2)
    return ids_of(p['row'], lambda s: lo(s) == -p['v'])


@proto('ch-ege-03-minox', 'ЕГЭ', 3, 'Низшая (отрицательная) степень окисления',
       invariant='низшая степень окисления неметалла = номер группы − 8; металлы отрицательных степеней не имеют',
       varies='ряд, значение низшей степени окисления (−1…−4), формулировки: «низшая равна», «в соединениях с '
              'металлами (литием) одинаковая» (пара)',
       answer_rule='VII → −1, VI → −2, V → −3, IV → −4; водород −1 (гидриды)',
       mistakes=['приписывают металлам отрицательную степень окисления', 'путают −(8 − N) и −N'],
       solve=_solve_minox, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='водород: −1 в гидридах — как у галогенов', scale=TIME_E1, kes=['1.3']))
def g_minox(rng):
    pid = 'ch-ege-03-minox'
    pool = [s for s in MAIN if s not in ('B', 'Ge')] + ['Cr', 'Fe', 'Zn', 'Cu']
    if rng.random() < 0.35:
        nm = [s for s in pool if ox_min(s) < 0]
        met = [s for s in pool if ox_min(s) >= 0]
        by = {}
        for s in nm:
            by.setdefault(ox_min(s), []).append(s)
        v = rng.choice([k for k, xs in by.items() if len(xs) >= 2])
        rest_vals = [k for k in by if k != v]
        if len(rest_vals) < 2:
            raise Retry
        k_nm = rng.randint(2, min(3, len(rest_vals)))   # металлов в ряду не больше одного: их низшая с.о. 0
        items = rng.sample(by[v], 2) + [rng.choice(by[w]) for w in rng.sample(rest_vals, k_nm)] + \
            rng.sample(met, 3 - k_nm)
        rng.shuffle(items)
        vals = [ox_min(s) for s in items]
        pred = lambda s: ox_min(s) < 0 and vals.count(ox_min(s)) == 2
        q = rng.choice(['Укажите два элемента ряда, которые в соединениях с литием проявляют одну и ту же степень '
                        'окисления.',
                        'Для каких двух элементов ряда низшие степени окисления совпадают?'])
        p = {'mode': 'same'}
    else:
        v = rng.randint(1, 4)
        pred = lambda s: ox_min(s) == -v
        items = pick_row(rng, [s for s in pool if pred(s)], [s for s in pool if not pred(s)])
        q = rng.choice([f'Укажите два элемента ряда, низшая степень окисления которых составляет {signed(-v)}.',
                        f'Для каких двух элементов ряда наименьшая возможная степень окисления равна {signed(-v)}?'])
        p = {'mode': 'v', 'v': v}
    lines = [f'{s} — {signed(min(ox_min(s), 0))}' for s in items]
    return row_card(pid, rng, items, pred, q, ['Низшие степени окисления (у металлов 0): ' + lines[0]] + lines[1:], p)


def _solve_sign(p):
    def kind(s):
        Z = z_of(s)
        lo, hi = r_lower_ox(Z), r_hi(Z)
        return lo, hi
    m = p['mode']
    if m == 'both':
        return ids_of(p['row'], lambda s: kind(s)[0] < 0 < kind(s)[1])
    if m == 'neg':
        return ids_of(p['row'], lambda s: kind(s)[0] < 0)
    return ids_of(p['row'], lambda s: kind(s)[0] == 0)


@proto('ch-ege-03-sign', 'ЕГЭ', 3, 'Знак степени окисления: положительная и/или отрицательная',
       invariant='металлы в соединениях имеют только положительные степени окисления; неметаллы (кроме фтора) — и '
                 'положительные, и отрицательные; фтор — только −1',
       varies='ряд; вопрос: «и положительную, и отрицательную», «может быть отрицательной», «не проявляют '
              'отрицательной»',
       answer_rule='выбрать два неметалла (кроме F — для «обеих») или два металла (для «не проявляют отрицательной»)',
       mistakes=['выбирают фтор в вопросе про обе степени', 'не считают кислород (+2 в OF₂)',
                 'выбирают металл с переменной степенью окисления'],
       solve=_solve_sign, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='как в демоверсии 2027: O (+2 в OF₂) и Si (−4 в силицидах); F только −1',
                    scale=TIME_E1, kes=['1.3']))
def g_sign(rng):
    pid = 'ch-ege-03-sign'
    pool = [s for s in MAIN if s not in ('B', 'Ge', 'Ga')] + (['Cr', 'Mn', 'Fe', 'Cu', 'Zn'] if rng.random() < .4 else [])
    mode = rng.choice(['both', 'both', 'neg', 'pos'])
    if mode == 'both':
        pred = lambda s: E[s]['kind'] == 'n' and min(E[s]['ox']) < 0 < max(E[s]['ox'])
        q = rng.choice(['Укажите два элемента ряда, которые в различных соединениях проявляют как положительные, так '
                        'и отрицательные степени окисления.',
                        'Какие два элемента ряда способны иметь в соединениях и положительную, и отрицательную '
                        'степень окисления?'])
    elif mode == 'neg':
        pred = lambda s: E[s]['kind'] == 'n'
        q = rng.choice(['Укажите два элемента ряда, у которых в соединениях возможна отрицательная степень окисления.',
                        'Какие два элемента ряда в некоторых своих соединениях имеют отрицательную степень окисления?'])
    else:
        pred = lambda s: E[s]['kind'] == 'm'
        q = rng.choice(['Укажите два элемента ряда, которые ни в одном соединении не имеют отрицательной степени '
                        'окисления.',
                        'Какие два элемента ряда во всех своих соединениях имеют только положительные степени '
                        'окисления?'])
    yes = [s for s in pool if pred(s)]
    no = [s for s in pool if not pred(s)]
    if mode == 'both' and rng.random() < 0.5:
        no += ['F', 'F']
    items = pick_row(rng, yes, no)
    return row_card(pid, rng, items, pred, q, ['Степени окисления в соединениях: ' + _ox_line(items[0])]
                    + [_ox_line(s) for s in items[1:]], {'mode': mode})


def diff_of(s):
    ox = list(E[s]['ox']) + [0]
    hi = max(ox) if s not in ('F',) else 0
    return hi - min(ox)


DIFF_POOL = [s for s in MAIN if s not in ('B', 'Ge', 'Ga')] + ['Cr', 'Mn', 'Zn', 'Ti', 'V', 'Sc']


def _solve_diff(p):
    d = lambda s: r_hi(z_of(s)) - min(r_lower_ox(z_of(s)), 0)
    if p['mode'] == 'same':
        vals = [d(s) for s in p['row']]
        return ids_of(p['row'], lambda s: vals.count(d(s)) == 2)
    return ids_of(p['row'], lambda s: d(s) == p['v'])


@proto('ch-ege-03-diff', 'ЕГЭ', 3, 'Разность высшей и низшей степеней окисления',
       invariant='найти высшую (номер группы; у O +2, у F 0) и низшую (N − 8 у неметаллов, 0 у металлов) степени '
                 'окисления и их разность',
       varies='ряд из металлов и неметаллов; «одинаковая разность» (пара) или «разность равна k»',
       answer_rule='неметаллы IV–VII групп: разность 8; O: 4; F: 1; H: 2; металлы: равна высшей степени окисления',
       mistakes=['для металлов берут отрицательную низшую степень', 'для кислорода и фтора берут номер группы',
                 'складывают вместо вычитания'],
       solve=_solve_diff, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='у всех неметаллов IV–VII групп разность одинакова (8); у металлов низшая = 0',
                    scale=TIME_E1, kes=['1.3']))
def g_diff(rng):
    pid = 'ch-ege-03-diff'
    if rng.random() < 0.65:
        items, v = pick_pair(rng, DIFF_POOL, diff_of)
        pred = pair_pred(items, diff_of)
        q = rng.choice(['Укажите два элемента ряда, у которых разность между высшей и низшей степенями окисления '
                        'одинакова.',
                        'Для каких двух элементов ряда разность значений высшей и низшей степеней окисления '
                        'совпадает?'])
        p = {'mode': 'same'}
    else:
        v = rng.choice([1, 2, 3, 4])
        pred = lambda s: diff_of(s) == v
        items = pick_row(rng, [s for s in DIFF_POOL if pred(s)], [s for s in DIFF_POOL if not pred(s)])
        q = f'Укажите два элемента ряда, у каждого из которых высшая степень окисления больше низшей на {v}.'
        p = {'mode': 'v', 'v': v}
    lines = [f'{s}: {signed(max(list(E[s]["ox"]) + [0]) if s != "F" else 0)} и {signed(min(list(E[s]["ox"]) + [0]))} '
             f'(разность {diff_of(s)})' for s in items]
    return row_card(pid, rng, items, pred, q, ['Высшая и низшая степени окисления — ' + lines[0]] + lines[1:], p)


# «может проявлять степень окисления v»: элементы, для которых значение бесспорно есть / бесспорно нет (школьный курс)
OXVAL = {
    4: ('C Si S Se Mn Pb Ti N', 'Li Na K Mg Ca Ba Al Zn F B Ga H Cu Ag'),
    3: ('N P As Al B Cr Fe Ga Sc Co', 'Li Na K Mg Ca Ba Zn F O Si H Cu Ag'),
    6: ('S Se Cr Mn', 'N P C Si Al Mg Na K Ca Zn Cu F O B H As Ti V'),
    2: ('Mg Ca Ba Be Zn Fe Cu Mn Cr C N Pb Co Ni Sr O', 'Li Na K Al F H B'),
    5: ('N P As Cl Br I V', 'C Si S O F H Li Na K Mg Ca Al Zn Fe Cu B Ba'),
    1: ('H Li Na K Cu Ag N Cl Br I', 'Mg Ca Ba Al Zn F Fe Si'),
    -1: ('H F Cl Br I O', 'Li Na K Mg Ca Al Zn Fe Cu Cr Mn B Si'),
    -2: ('O S Se', 'Li Na K Mg Ca Al Zn Fe Cu F H Cl Br I B'),
    -3: ('N P As', 'F Cl Br I O S H Li Na K Mg Ca Al Zn Fe Cu Se'),
    -4: ('C Si', 'N P S Cl O F H Li Na K Mg Ca Al Zn Fe Cu As Se Br I'),
}


def _solve_oxval(p):
    v = p['v']
    return ids_of(p['row'], lambda s: v in E[s]['ox'])


@proto('ch-ege-03-oxval', 'ЕГЭ', 3, 'Может проявлять в соединениях заданную степень окисления',
       invariant='знать типичные степени окисления элементов (по группе, металл/неметалл, переменная валентность '
                 'd-элементов)',
       varies='ряд; значение степени окисления (−4…+6)',
       answer_rule='выбрать два элемента, для которых это значение типично (C, Si, S, N, Mn… для +4 и т. д.)',
       mistakes=['считают, что степень окисления бывает только высшей и низшей', 'приписывают металлам IA/IIA '
                 'переменную степень окисления'],
       solve=_solve_oxval, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='промежуточные степени окисления: N +2, +4; S +4; Mn +4; C +2',
                    scale=TIME_E1, kes=['1.3']))
def g_oxval(rng):
    pid = 'ch-ege-03-oxval'
    v = rng.choice(list(OXVAL))
    yes, no = (x.split() for x in OXVAL[v])
    items = pick_row(rng, yes, no)
    q = rng.choice([f'Укажите два элемента ряда, для которых в соединениях известна степень окисления {signed(v)}.',
                    f'Для каких двух элементов ряда в соединениях возможна степень окисления {signed(v)}?'])
    return row_card(pid, rng, items, lambda s: s in yes, q, ['Типичные степени окисления: ' + _ox_line(items[0])]
                    + [_ox_line(s) for s in items[1:]], {'v': v})


# кислородсодержащие анионы: элемент → [(формула аниона, заряд, степень окисления)]
ANIONS = {
    'S': [('SO3', 2), ('SO4', 2)], 'Se': [('SeO3', 2), ('SeO4', 2)], 'Cr': [('CrO4', 2), ('CrO2', 1)],
    'Mn': [('MnO4', 2), ('MnO4', 1)], 'C': [('CO3', 2)], 'Si': [('SiO3', 2)], 'N': [('NO3', 1), ('NO2', 1)],
    'P': [('PO4', 3)], 'Cl': [('ClO', 1), ('ClO2', 1), ('ClO3', 1), ('ClO4', 1)], 'Br': [('BrO', 1), ('BrO3', 1)],
    'I': [('IO3', 1), ('IO4', 1)], 'Al': [('AlO2', 1)], 'Zn': [('ZnO2', 2)], 'B': [('BO2', 1)],
    'As': [('AsO4', 3)], 'Fe': [('FeO4', 2)],
}
AN_POOL = list(ANIONS) + ['Na', 'K', 'Mg', 'Ca', 'F']


def an_ox(f, q):
    comp = parse_formula(f)
    el = [x for x in comp if x != 'O'][0]
    return el, (2 * comp['O'] - q) // comp[el]


def an_states(s, form=None):
    """Степени окисления s в его кислородсодержащих анионах (form: 2 — только ЭOₓ²⁻, 1 — ЭOₓ⁻)."""
    return {an_ox(f, q)[1] for f, q in ANIONS.get(s, []) if form is None or q == form}


def an_view(f, q):
    return pretty(f) + ((str(q) if q > 1 else '') + '−').translate(SUP)


def _solve_anion(p):
    def states(s):
        # второй путь: заряд аниона = 2·nO − n·x … пересчитываем по каждой формуле из электронейтральности
        out = set()
        for f, q in ANIONS.get(s, []):
            comp = parse_formula(f)
            if p['form'] and q != p['form']:
                continue
            out.add(Fr(-q + 2 * comp['O'], comp[s]))
        return out
    if p['mode'] == 'same':
        row = p['row']
        return sorted(str(i + 1) for i, s in enumerate(row)
                      if any(states(s) & states(t) for t in row if t != s))
    return ids_of(p['row'], lambda s: p['v'] in states(s))


@proto('ch-ege-03-anion', 'ЕГЭ', 3, 'Степень окисления элемента в кислородсодержащих анионах',
       invariant='степень окисления элемента в анионе ЭOₓ^(n−) из электронейтральности (O −2, сумма = заряд иона)',
       varies='ряд (неметаллы, амфотерные и переходные металлы); вопрос: «одинаковая степень окисления в анионах '
              'ЭOₓ²⁻ (ЭOₓ⁻)», «в анионах могут иметь +5»',
       answer_rule='перебрать известные анионы элементов ряда (SO₄²⁻, CrO₄²⁻, MnO₄⁻, NO₃⁻, ClO₃⁻…) и сравнить '
                   'степени окисления',
       mistakes=['не учитывают заряд аниона', 'путают MnO₄⁻ (+7) и MnO₄²⁻ (+6)', 'забывают анионы переходных металлов'],
       solve=_solve_anion, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='S и Cr (SO₄²⁻, CrO₄²⁻: +6), C и Si (+4); N, P, Cl — +5', scale=TIME_E1,
                    kes=['1.3']))
def g_anion(rng):
    pid = 'ch-ege-03-anion'
    if rng.random() < 0.6:
        form = rng.choice([2, 2, 1, None])
        for _ in range(60):
            items = rng.sample(AN_POOL, 5)
            st = {s: an_states(s, form) for s in items}
            pairs = [(a, b) for a, b in itertools.combinations(items, 2) if st[a] & st[b]]
            if len(pairs) == 1:
                break
        else:
            raise Retry
        a, b = pairs[0]
        pred = lambda s: s in (a, b)
        where = {2: 'в анионах с общей формулой ЭOₓ²⁻', 1: 'в анионах с общей формулой ЭOₓ⁻',
                 None: 'в составе кислородсодержащих анионов'}[form]
        q = rng.choice([f'Укажите два элемента ряда, для которых {where} возможна одна и та же степень окисления.',
                        f'Для каких двух элементов ряда {where} возможно совпадение степеней окисления?'])
        p = {'mode': 'same', 'form': form}
    else:
        v = rng.choice([5, 6, 4, 7, 3])
        pred = lambda s: v in an_states(s)
        items = pick_row(rng, [s for s in AN_POOL if pred(s)], [s for s in AN_POOL if not pred(s)])
        q = f'Укажите два элемента ряда, для которых в составе их кислородсодержащих анионов возможна степень ' \
            f'окисления {signed(v)}.'
        p = {'mode': 'v', 'v': v, 'form': None}
    lines = [f'{s}: ' + (', '.join(f'{an_view(f, qq)} ({signed(an_ox(f, qq)[1])})' for f, qq in ANIONS[s]
                                   if p['form'] is None or qq == p['form']) or 'нет') if s in ANIONS
             else f'{s}: анионов не образует' for s in items]
    return row_card(pid, rng, items, pred, q, ['Анионы: ' + lines[0]] + lines[1:], p)


VAL1_YES = 'H F Cl Br I Li Na K Cu Ag'.split()
VAL1_NO = 'Mg Ca Ba Al C Si O Zn B Be'.split()
NOTGROUP_YES = ['N', 'O', 'F']
NOTGROUP_NO = 'Li Na K Mg Ca Al C Si P S Cl Br I'.split()
SAMEVAL_YES = ['C', 'Si']
SAMEVAL_NO = 'N P S Cl O F Br I As Se'.split()


def _solve_valence(p):
    def maxval(Z):
        # максимальная валентность: у элементов 2-го периода не больше 4 (нет d-орбиталей), F — 1, O — 2
        if Z == 9:
            return 1
        if Z == 8:
            return 2
        if r_period(Z) == 2 and not r_metal(Z):
            return min(r_outer(Z), 4)
        return r_valence(Z)
    m = p['mode']
    if m == 'one':
        return ids_of(p['row'], lambda s: r_valence(z_of(s)) == 1 or (not r_metal(z_of(s)) and r_outer(z_of(s)) == 7)
                      or z_of(s) == 1)
    if m == 'notgroup':
        return ids_of(p['row'], lambda s: maxval(z_of(s)) != r_valence(z_of(s)))
    return ids_of(p['row'], lambda s: not r_metal(z_of(s)) and r_valence(z_of(s)) == 8 - r_valence(z_of(s)))


@proto('ch-ege-03-valence', 'ЕГЭ', 3, 'Валентность элементов в соединениях',
       invariant='валентность — число связей атома; высшая = номер группы (кроме N, O, F), в водородном соединении — '
                 '8 − N',
       varies='ряд; вопрос: «могут проявлять валентность I», «не проявляют валентности, равной номеру группы», '
              '«валентность в высшем оксиде и летучем водородном соединении одинакова»',
       answer_rule='валентность I: H, галогены, щелочные металлы, Cu, Ag; ≠ номеру группы: N (IV), O (II), F (I); '
                   'одинаковая в оксиде и водородном соединении: IVA (C, Si)',
       mistakes=['азоту приписывают валентность V', 'путают валентность и степень окисления'],
       solve=_solve_valence, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='N: высшая валентность IV при степени окисления +5', scale=TIME_E1, kes=['1.3']))
def g_valence3(rng):
    pid = 'ch-ege-03-valence'
    mode = rng.choice(['one', 'notgroup', 'same'])
    if mode == 'one':
        yes, no = VAL1_YES, VAL1_NO
        q = rng.choice(['Укажите два элемента ряда, для которых в соединениях характерна валентность I.',
                        'Какие два элемента ряда образуют соединения, в которых их валентность равна I?'])
    elif mode == 'notgroup':
        yes, no = NOTGROUP_YES, NOTGROUP_NO
        q = rng.choice(['Укажите два элемента ряда, высшая валентность которых не совпадает с номером группы.',
                        'Для каких двух элементов ряда высшая валентность меньше номера группы?'])
    else:
        yes, no = SAMEVAL_YES, SAMEVAL_NO
        q = ('Укажите два элемента ряда, у каждого из которых валентность в высшем оксиде такая же, как в летучем '
             'водородном соединении.')
    items = pick_row(rng, yes, no)
    lines = [f'{s} — группа {ROMAN[E[s]["group"]]}' for s in items]
    return row_card(pid, rng, items, lambda s: s in yes, q, ['Положение: ' + lines[0]] + lines[1:], {'mode': mode})


CONST_YES = ['Li', 'Na', 'K', 'Be', 'Mg', 'Ca', 'Sr', 'Ba', 'Al', 'Zn']
CONST_NO = ['Cr', 'Mn', 'Fe', 'Cu', 'Pb', 'N', 'S', 'Cl', 'P', 'C', 'Br', 'I', 'Se']


def _solve_const(p):
    def const(s):
        Z = z_of(s)
        if not r_metal(Z):
            return False
        if r_block(Z) == 'd':
            occ, _ = aufbau(Z)
            return occ.get((r_period(Z) - 1, 2), 0) == 10 and r_outer(Z) == 2
        return r_outer(Z) <= 3
    want = p['mode'] == 'const'
    return ids_of(p['row'], lambda s: const(s) == want)


@proto('ch-ege-03-const', 'ЕГЭ', 3, 'Постоянная или переменная степень окисления',
       invariant='металлы IA, IIA групп, алюминий и цинк проявляют в соединениях одну степень окисления; неметаллы и '
                 'большинство d-металлов — переменную',
       varies='ряд; вопрос о постоянной или о переменной степени окисления',
       answer_rule='постоянная: IA, IIA, Al, Zn; переменная: неметаллы, Cr, Mn, Fe, Cu, Pb',
       mistakes=['относят к постоянным Fe или Cr', 'считают Zn элементом с переменной степенью окисления'],
       solve=_solve_const, kes=K3,
       fidelity=fid(3, 'ЕГЭ', trap='Zn — d-элемент, но степень окисления постоянная (+2); Cu, Fe, Cr — переменная',
                    scale=TIME_E1, kes=['1.3']))
def g_const(rng):
    pid = 'ch-ege-03-const'
    mode = rng.choice(['const', 'const', 'var'])
    yes, no = (CONST_YES, CONST_NO) if mode == 'const' else (CONST_NO, CONST_YES)
    items = pick_row(rng, yes, no)
    if mode == 'const':
        q = rng.choice(['Укажите два элемента ряда, которые во всех соединениях имеют одну и ту же степень окисления.',
                        'Какие два элемента ряда проявляют в соединениях единственную (постоянную) степень '
                        'окисления?'])
    else:
        q = rng.choice(['Укажите два элемента ряда, для которых характерны несколько различных степеней окисления.',
                        'Какие два элемента ряда проявляют в соединениях переменную степень окисления?'])
    return row_card(pid, rng, items, lambda s: s in yes, q,
                    ['Степени окисления: ' + _ox_line(items[0])] + [_ox_line(s) for s in items[1:]], {'mode': mode})


# ================================================================= вещества: вид связи, решётка, водородные связи
# (формула, название, связи: i — ионная, p — ковалентная полярная, n — ковалентная неполярная, m — металлическая,
#  d — есть связь по донорно-акцепторному механизму; решётка: ion/mol/atom/met; hb — водородные связи между молекулами;
#  lvl: o — годится для ОГЭ (неорганика 8–9 кл.), e — только ЕГЭ)
_SUBS = """
Na|натрий|m|met||o
K|калий|m|met||o
Li|литий|m|met||o
Mg|магний|m|met||o
Ca|кальций|m|met||o
Ba|барий|m|met||o
Al|алюминий|m|met||o
Fe|железо|m|met||o
Cu|медь|m|met||o
Zn|цинк|m|met||o
Ag|серебро|m|met||o
Cr|хром|m|met||e
H2|водород|n|mol||o
O2|кислород|n|mol||o
N2|азот|n|mol||o
Cl2|хлор|n|mol||o
F2|фтор|n|mol||o
Br2|бром|n|mol||o
I2|иод|n|mol||o
O3|озон|n|mol||o
S8|сера (ромбическая)|n|mol||o
P4|белый фосфор|n|mol||o
C|алмаз|n|atom||o
C|графит|n|atom||e
Si|кремний|n|atom||o
B|бор|n|atom||e
SiO2|оксид кремния(IV)|p|atom||o
SiC|карбид кремния|p|atom||e
HCl|хлороводород|p|mol||o
HBr|бромоводород|p|mol||o
HI|иодоводород|p|mol||o
HF|фтороводород|p|mol|hb|o
H2O|вода|p|mol|hb|o
NH3|аммиак|p|mol|hb|o
H2S|сероводород|p|mol||o
PH3|фосфин|p|mol||o
CH4|метан|p|mol||o
CO2|оксид углерода(IV)|p|mol||o
SO2|оксид серы(IV)|p|mol||o
SO3|оксид серы(VI)|p|mol||o
P2O5|оксид фосфора(V)|p|mol||o
CCl4|тетрахлорметан|p|mol||e
NO|оксид азота(II)|p|mol||o
CO|оксид углерода(II)|pd|mol||o
H2SO4|серная кислота|p|mol|hb|o
HNO3|азотная кислота|p|mol|hb|o
H3PO4|ортофосфорная кислота|p|mol|hb|e
H2O2|пероксид водорода|pn|mol|hb|e
CH3OH|метанол|p|mol|hb|e
C2H5OH|этанол|pn|mol|hb|e
CH3COOH|уксусная кислота|pn|mol|hb|e
HCOOH|муравьиная кислота|p|mol|hb|e
C2H6|этан|pn|mol||e
C2H4|этилен|pn|mol||e
C2H2|ацетилен|pn|mol||e
C6H6|бензол|pn|mol||e
CH3OCH3|диметиловый эфир|p|mol||e
CH2O|формальдегид|p|mol||e
CH3CHO|уксусный альдегид|pn|mol||e
CH3NH2|метиламин|p|mol|hb|e
C6H5OH|фенол|pn|mol|hb|e
NaCl|хлорид натрия|i|ion||o
KCl|хлорид калия|i|ion||o
KBr|бромид калия|i|ion||o
NaI|иодид натрия|i|ion||o
CaCl2|хлорид кальция|i|ion||o
MgCl2|хлорид магния|i|ion||o
BaCl2|хлорид бария|i|ion||o
NaF|фторид натрия|i|ion||o
CaF2|фторид кальция|i|ion||o
Na2O|оксид натрия|i|ion||o
K2O|оксид калия|i|ion||o
Li2O|оксид лития|i|ion||o
CaO|оксид кальция|i|ion||o
MgO|оксид магния|i|ion||o
BaO|оксид бария|i|ion||o
Na2S|сульфид натрия|i|ion||o
K2S|сульфид калия|i|ion||o
NaH|гидрид натрия|i|ion||e
CaH2|гидрид кальция|i|ion||e
Li3N|нитрид лития|i|ion||o
Mg3N2|нитрид магния|i|ion||o
Na3N|нитрид натрия|i|ion||o
CaC2|карбид кальция|in|ion||e
Na2O2|пероксид натрия|in|ion||e
BaO2|пероксид бария|in|ion||e
NaOH|гидроксид натрия|ip|ion||o
KOH|гидроксид калия|ip|ion||o
Ca(OH)2|гидроксид кальция|ip|ion||o
Ba(OH)2|гидроксид бария|ip|ion||o
LiOH|гидроксид лития|ip|ion||o
Na2SO4|сульфат натрия|ip|ion||o
K2SO4|сульфат калия|ip|ion||o
K2CO3|карбонат калия|ip|ion||o
Na2CO3|карбонат натрия|ip|ion||o
CaCO3|карбонат кальция|ip|ion||o
NaNO3|нитрат натрия|ip|ion||o
KNO3|нитрат калия|ip|ion||o
K3PO4|фосфат калия|ip|ion||o
Na3PO4|фосфат натрия|ip|ion||o
Na2SiO3|силикат натрия|ip|ion||o
KMnO4|перманганат калия|ip|ion||e
NaHCO3|гидрокарбонат натрия|ip|ion||o
KHSO4|гидросульфат калия|ip|ion||e
KClO3|хлорат калия|ip|ion||e
NH4Cl|хлорид аммония|ipd|ion||o
NH4Br|бромид аммония|ipd|ion||o
NH4NO3|нитрат аммония|ipd|ion||o
(NH4)2SO4|сульфат аммония|ipd|ion||o
(NH4)2CO3|карбонат аммония|ipd|ion||e
CH3COONa|ацетат натрия|ipn|ion||e
C2H5ONa|этилат натрия|ipn|ion||e
CH3ONa|метилат натрия|ip|ion||e
HCOONa|формиат натрия|ip|ion||e
C6H5ONa|фенолят натрия|ipn|ion||e
CH3COOK|ацетат калия|ipn|ion||e
CH3NH3Cl|хлорид метиламмония|ipd|ion||e
CH3NH3Br|бромид метиламмония|ipd|ion||e
Cu(NH3)4SO4|сульфат тетраамминмеди(II)|ipd|ion||e
KAl(OH)4|тетрагидроксоалюминат калия|ipd|ion||e
SCl2|хлорид серы(II)|p|mol||e
CH2Cl2|дихлорметан|p|mol||e
CH3Cl|хлорметан|p|mol||e
PCl3|хлорид фосфора(III)|p|mol||e
SF6|фторид серы(VI)|p|mol||e
SiH4|силан|p|mol||e
C3H5(OH)3|глицерин|pn|mol|hb|e
C2H4(OH)2|этиленгликоль|pn|mol|hb|e
HCOOCH3|метилформиат|p|mol||e
CH3COOCH3|метилацетат|pn|mol||e
CH3COCH3|ацетон|pn|mol||e
C6H5CH3|толуол|pn|mol||e
C4H6|бутадиен-1,3|pn|mol||e
C2H5OC2H5|диэтиловый эфир|pn|mol||e
NH4F|фторид аммония|ipd|ion||e
NH4HCO3|гидрокарбонат аммония|ipd|ion||e
CH3COONH4|ацетат аммония|ipnd|ion||e
NaNO2|нитрит натрия|ip|ion||o
Li3PO4|фосфат лития|ip|ion||o
MgSO4|сульфат магния|ip|ion||o
CaSiO3|силикат кальция|ip|ion||e
Na2C2|ацетиленид натрия|in|ion||e
Cs|цезий|m|met||e
RbCl|хлорид рубидия|i|ion||e
"""
SUBS = []
for _ln in _SUBS.strip().splitlines():
    _f, _nm, _b, _lat, _hb, _lv = _ln.split('|')
    SUBS.append(dict(f=_f, name=_nm, bonds=set(_b), lat=_lat, hb=_hb == 'hb', lvl=_lv, key=_f + ':' + _nm))
SUBK = {s['key']: s for s in SUBS}
# формулы с неоднозначной школьной трактовкой донорно-акцепторной связи (N→O, O₃) — в прототип «д/а» не берём
DA_AMBIG = {'HNO3', 'NaNO3', 'KNO3', 'O3', 'NO', 'SO3', 'P2O5', 'H3PO4', 'H2SO4', 'Na2SO4', 'K2SO4', 'KHSO4',
            'K3PO4', 'Na3PO4', 'KMnO4', 'KClO3'}


def sub_view(s, names):
    """Как вещество показано в перечне: по названию (ЕГЭ, как в демоверсии) или по формуле."""
    if names:
        return s['name']
    f = {'Cu(NH3)4SO4': '[Cu(NH₃)₄]SO₄', 'KAl(OH)4': 'K[Al(OH)₄]'}.get(s['f']) or pretty(s['f'])
    if s['f'] in ('C', 'S8', 'P4', 'B', 'Si'):
        return f'{f} ({s["name"]})' if s['f'] in ('C', 'P4') else f
    return f


def _metal_el(el):
    return r_metal(z_of(el))


ETHERS = {'CH3OCH3', 'HCOOCH3'}   # два атома C, но связи C–C нет


def solve_bonds(f):
    """Второй путь: вид связи по составу формулы."""
    comp = parse_formula(f)
    mets = [el for el in comp if _metal_el(el)]
    if len(mets) == len(comp):
        return {'m'}
    ammon = 'NH4' in f or 'CH3NH3' in f
    ionic = bool(mets) or ammon
    b = set()
    nm = {el: n for el, n in comp.items() if not _metal_el(el)}
    if ionic:
        b.add('i')
        if sum(nm.values()) >= 2 and len(nm) >= 2:
            b.add('p')
        if len(mets) >= 2 and 'O' in nm:
            b.add('p')    # оксоанион переходного металла (MnO₄⁻, CrO₄²⁻): связи M–O ковалентные полярные
        elif len(nm) == 1:
            el, n = next(iter(nm.items()))
            charge = sum(r_outer(z_of(m)) * comp[m] for m in mets)
            if n >= 2 and Fr(-charge, n) != r_lower_ox(z_of(el)):
                b.add('n')    # пероксид O₂²⁻, карбид C₂²⁻
        if comp.get('C', 0) >= 2:
            b.add('n')
    else:
        if len(comp) == 1:
            b.add('n')
        else:
            b.add('p')
            if comp.get('C', 0) >= 2 and f not in ETHERS:
                b.add('n')
            if set(comp) == {'H', 'O'} and comp['O'] >= 2:
                b.add('n')
    if ammon or f == 'CO' or '(NH3)' in f or 'Al(OH)4' in f:
        b.add('d')    # NH₄⁺, RNH₃⁺, CO; комплексы [Cu(NH₃)₄]²⁺, [Al(OH)₄]⁻
    return b


def solve_lattice(f):
    comp = parse_formula(f)
    b = solve_bonds(f)
    if b == {'m'}:
        return 'met'
    if 'i' in b:
        return 'ion'
    if set(comp) <= {'B', 'C', 'Si'} and len(comp) == 1 or ('Si' in comp and 'H' not in comp):
        return 'atom'
    return 'mol'


def solve_hb(f):
    return solve_lattice(f) == 'mol' and ('OH' in f or 'NH' in f or f in ('H2O', 'HF', 'H2O2', 'H2SO4', 'HNO3', 'H3PO4'))


BOND_TXT = {'i': 'ионная', 'p': 'ковалентная полярная', 'n': 'ковалентная неполярная', 'm': 'металлическая'}
LAT_TXT = {'ion': 'ионная', 'mol': 'молекулярная', 'atom': 'атомная', 'met': 'металлическая'}


def sub_desc(s):
    b = ', '.join(BOND_TXT[x] for x in 'ipnm' if x in s['bonds'])
    return f'{pretty(s["f"])} — {b}'


def kim_list(q):
    """Инструкция — как в КИМ («Из предложенного перечня выберите два вещества, …»); условие — своё."""
    subs = [(r'^Укажите два (вещества|соединения|свойства) из перечня, ', r'Из предложенного перечня выберите два \1, '),
            (r'^Укажите два вещества, ', 'Из предложенного перечня выберите два вещества, '),
            (r'^Укажите два вещества ', 'Из предложенного перечня выберите два вещества '),
            (r'^Отметьте два вещества( перечня)?, ', 'Из предложенного перечня выберите два вещества, '),
            (r'^Среди перечисленных веществ отметьте два вещества ', 'Из предложенного перечня выберите два вещества '),
            (r'^В каких двух (веществах|соединениях) из (приведённого )?перечня (есть|имеется) (.*)\?$',
             r'Из предложенного перечня выберите два вещества, в которых имеется \4.'),
            (r'^Для каких двух веществ из перечня (.*)\?$', r'Из предложенного перечня выберите два вещества, для '
                                                             r'которых \1.'),
            (r'^Какие два (вещества из перечня|из перечисленных веществ) (.*)\?$',
             r'Из предложенного перечня выберите два вещества, которые \2.'),
            (r'^Какие два из перечисленных свойств (.*)\?$', r'Из предложенного перечня выберите два свойства, которые '
                                                              r'\1.')]
    for a, b in subs:
        q = re.sub(a, b, q)
    return q


def list_card(pid, rng, pool, pred, q, p_extra, explain=sub_desc, names=None, k=2, tail=None):
    yes = [s for s in pool if pred(s)]
    no = [s for s in pool if not pred(s)]
    if len(yes) < k or len(no) < 5 - k:
        raise Retry
    items = rng.sample(yes, k) + rng.sample(no, 5 - k)
    if len({s['f'] for s in items}) < 5:
        raise Retry
    rng.shuffle(items)
    names = (rng.random() < 0.5) if names is None else names
    view = [sub_view(s, names) for s in items]
    ans = ids_of(items, pred)
    if sum('NH4' in items[int(i) - 1]['f'] or 'CH3NH3' in items[int(i) - 1]['f'] for i in ans) > 1:
        raise Retry   # две соли аммония в ответе — тривиальная пара
    tail = tail or rng.choice(['Запишите номера выбранных ответов.', 'Запишите в поле ответа номера выбранных веществ.'])
    q = kim_list(q)
    e = '; '.join(explain(s) for s in items) + f'. Ответ: {"".join(ans)}.'
    return pcard(pid, q + ' ' + tail, ans, e, k='many', o=opts(view), p=dict(p_extra, subs=[s['f'] for s in items]))


def pool_for(level):
    return [s for s in SUBS if level == 'e' or s['lvl'] == 'o']


def _solve_bond(p):
    return ids_of(p['subs'], lambda f: p['b'] in solve_bonds(f))


K4 = ['1.4']
SC4 = 'пять веществ: простые вещества, бинарные соединения, соли, кислоты, основания, несложная органика (как в банке и демо)'


def bond_q(rng, b, exam):
    t = {'i': 'ионная', 'p': 'ковалентная полярная', 'n': 'ковалентная неполярная', 'm': 'металлическая'}[b]
    ins = {'i': 'ионной', 'p': 'ковалентной полярной', 'n': 'ковалентной неполярной', 'm': 'металлической'}[b]
    if exam == 'ЕГЭ':
        return rng.choice([f'Укажите два вещества из перечня, в которых имеется {t} химическая связь.',
                           f'В каких двух веществах из приведённого перечня есть {t} связь?',
                           f'Отметьте два вещества перечня, в состав которых входят атомы (ионы), соединённые {ins} '
                           f'связью.'])
    acc = {'i': 'ионную', 'p': 'ковалентную полярную', 'n': 'ковалентную неполярную', 'm': 'металлическую'}[b]
    if b == 'm':
        return f'Из предложенного перечня выберите два вещества с {ins} связью.'
    return rng.choice([f'Из предложенного перечня выберите два вещества с {ins} связью.',
                       f'Из предложенного перечня выберите два вещества, содержащие {acc} химическую связь.'])


def _bond_gen(pid, exam, letters):
    def gen(rng):
        b = rng.choice(letters)
        pool = pool_for('e' if exam == 'ЕГЭ' else 'o')
        c = list_card(pid, rng, pool, lambda s: b in s['bonds'], bond_q(rng, b, exam), {'b': b},
                      names=None if exam == 'ЕГЭ' else False)
        if exam == 'ОГЭ' and b == 'p':
            # как в банке ОГЭ: среди ответов хотя бы одно молекулярное вещество, соль/щёлочь — не больше одной
            ans_f = [c['gen']['p']['subs'][int(i) - 1] for i in c['a']]
            if sum(solve_lattice(f) == 'ion' for f in ans_f) > 1:
                raise Retry
        return c
    return gen


for _pid, _title, _lt, _trap in [
        ('ch-ege-04-ionic', 'Вещества с ионной связью', 'i',
         'соли аммония и аминов — ионные, хотя металла нет; AlCl₃, BeCl₂ в задания не берём'),
        ('ch-ege-04-polar', 'Вещества с ковалентной полярной связью', 'p',
         'полярные связи есть и внутри сложных ионов (соли кислородсодержащих кислот, щёлочи, алкоголяты)'),
        ('ch-ege-04-nonpolar', 'Вещества с ковалентной неполярной связью', 'n',
         'неполярная связь в пероксидах (O–O), карбиде кальция и ацетиленидах (C≡C), органике (C–C)')]:
    proto(_pid, 'ЕГЭ', 4, _title,
          invariant='по составу вещества (металл/неметалл, сложные ионы, одинаковые атомы) определить виды связи',
          varies='перечень из пяти веществ (названия или формулы: неорганические и органические), вид связи',
          answer_rule='ионная — металл + неметалл или катион аммония (алкиламмония); ковалентная неполярная — связь '
                      'одинаковых атомов неметалла; полярная — разных неметаллов',
          mistakes=['не видят ковалентных связей внутри сложного иона', 'не считают соли аммония ионными',
                    'пропускают связь O–O в пероксидах и C–C в органике'],
          solve=_solve_bond, kes=K4,
          fidelity=fid(4, 'ЕГЭ', trap=_trap, scale=SC4, kes=['1.4']))(_bond_gen(_pid, 'ЕГЭ', [_lt]))

MIX_ALT = {'ic': 'ионная связь и ковалентные связи', 'in': 'ионная связь и связь между одинаковыми атомами',
           'pn': 'связи между разными и между одинаковыми атомами неметаллов'}
MIX = {'ic': (lambda b: 'i' in b and bool(b & {'p', 'n'}), 'и ионная, и ковалентная связь'),
       'in': (lambda b: 'i' in b and 'n' in b, 'одновременно ионная и ковалентная неполярная связь'),
       'pn': (lambda b: 'p' in b and 'n' in b, 'одновременно ковалентная полярная и ковалентная неполярная связь')}


def _solve_mixed(p):
    t = {'ic': lambda b: 'i' in b and bool(b & {'p', 'n'}), 'in': lambda b: {'i', 'n'} <= b,
         'pn': lambda b: {'p', 'n'} <= b}[p.get('mode', 'ic')]
    return ids_of(p['subs'], lambda f: t(solve_bonds(f)))


def _mixed_gen(pid, exam):
    def gen(rng):
        pool = pool_for('e' if exam == 'ЕГЭ' else 'o')
        mode = rng.choice(['ic', 'ic', 'in', 'pn']) if exam == 'ЕГЭ' else 'ic'
        test, words = MIX[mode]
        pred = lambda s: test(s['bonds'])
        q = rng.choice([f'Укажите два вещества из перечня, в каждом из которых имеется {words}.',
                        f'Укажите два вещества из перечня, в каждом из которых одновременно встречаются '
                        f'{MIX_ALT[mode]}.'])
        return list_card(pid, rng, pool, pred, q, {'mode': mode}, names=None if exam == 'ЕГЭ' else False)
    return gen


proto('ch-ege-04-mixed', 'ЕГЭ', 4, 'Вещества с двумя видами связи одновременно',
      invariant='ионная связь между ионами + ковалентная внутри сложного иона; полярная + неполярная — в молекулах с '
                'цепочками одинаковых атомов',
      varies='сочетание (ионная + ковалентная, ионная + ковалентная неполярная, полярная + неполярная), перечень',
      answer_rule='выбрать два вещества, где есть оба вида связи (сложный ион; O–O, C–C вместе с полярными связями)',
      mistakes=['выбирают бинарные соли (NaCl)', 'выбирают кислоты (только ковалентные связи)',
                'не замечают C–C в этаноле, уксусной кислоте'],
      solve=_solve_mixed, kes=K4,
      fidelity=fid(4, 'ЕГЭ', trap='H₂SO₄ — только ковалентные связи, Na₂SO₄ — ионная и ковалентная; Na₂O₂ — ионная и '
                                  'неполярная', scale=SC4, kes=['1.4']))(_mixed_gen('ch-ege-04-mixed', 'ЕГЭ'))


def _solve_lat(p):
    L = p['L']
    if L == 'nonmol':
        return ids_of(p['subs'], lambda f: solve_lattice(f) != 'mol')
    return ids_of(p['subs'], lambda f: solve_lattice(f) == L)


@proto('ch-ege-04-lattice', 'ЕГЭ', 4, 'Тип кристаллической решётки (молекулярное/немолекулярное строение)',
       invariant='по виду связи и составу определить тип кристаллической решётки в твёрдом состоянии',
       varies='перечень, тип решётки (ионная, молекулярная, атомная) или «немолекулярное строение»',
       answer_rule='ионные соединения — ионная; металлы — металлическая; алмаз, графит, кремний, бор, SiO₂, SiC — '
                   'атомная; остальные ковалентные — молекулярная',
       mistakes=['CO₂ и SiO₂ относят к одному типу решётки', 'считают атомной решётку белого фосфора или иода'],
       solve=_solve_lat, kes=K4,
       fidelity=fid(4, 'ЕГЭ', trap='SiO₂ — атомная, CO₂ — молекулярная; соли аммония — ионная', scale=SC4, kes=['1.4']))
def g_lattice(rng):
    L = rng.choice(['ion', 'mol', 'atom', 'atom', 'nonmol'])
    pool = pool_for('e')
    pred = (lambda s: s['lat'] != 'mol') if L == 'nonmol' else (lambda s: s['lat'] == L)
    if L == 'nonmol':
        q = rng.choice(['Укажите два вещества из перечня, имеющие немолекулярное строение.',
                        'Какие два вещества из перечня в твёрдом состоянии построены не из молекул?'])
    else:
        q = rng.choice([f'Укажите два вещества из перечня, для которых в твёрдом состоянии характерна {LAT_TXT[L]} '
                        f'кристаллическая решётка.',
                        f'Какие два вещества из перечня образуют кристаллы с {LAT_TXT[L][:-2]}ой решёткой?'])
    return list_card('ch-ege-04-lattice', rng, pool, pred, q, {'L': L},
                     explain=lambda s: f'{pretty(s["f"])} — {LAT_TXT[s["lat"]]}')


def _solve_hb(p):
    return ids_of(p['subs'], solve_hb)


@proto('ch-ege-04-hbond', 'ЕГЭ', 4, 'Водородные связи между молекулами',
       invariant='водородная связь возникает между молекулами, где атом H связан с N, O или F',
       varies='перечень молекулярных (и немолекулярных) веществ: спирты, кислоты, амины, вода, аммиак, HF против '
              'эфиров, альдегидов, кетонов, углеводородов, H₂S, HCl',
       answer_rule='выбрать два вещества с группами O–H, N–H или H–F',
       mistakes=['выбирают H₂S и HCl (H связан не с N/O/F)', 'выбирают альдегиды и эфиры (O есть, но H не при O)',
                 'выбирают ионные вещества'],
       solve=_solve_hb, kes=K4,
       fidelity=fid(4, 'ЕГЭ', trap='эфиры, ацетон, формальдегид содержат кислород, но водородных связей между '
                                    'молекулами не образуют', scale=SC4, kes=['1.4']))
def g_hbond(rng):
    pool = [s for s in pool_for('e') if s['lat'] == 'mol' or rng.random() < 0.15]
    q = rng.choice(['Укажите два вещества из перечня, молекулы которых связаны друг с другом водородными связями.',
                    'Для каких двух веществ из перечня характерна водородная связь между молекулами?'])
    return list_card('ch-ege-04-hbond', rng, pool, lambda s: s['hb'], q, {},
                     explain=lambda s: f'{pretty(s["f"])} — {"есть" if s["hb"] else "нет"}')


def _solve_da(p):
    return ids_of(p['subs'], lambda f: 'd' in solve_bonds(f))


@proto('ch-ege-04-da', 'ЕГЭ', 4, 'Связь по донорно-акцепторному механизму',
       invariant='донорно-акцепторная связь: неподелённая пара N (O, C) + свободная орбиталь H⁺ (катион аммония, '
                 'алкиламмония) или C≡O в угарном газе',
       varies='перечень: соли аммония и аминов, CO против обычных ионных и ковалентных веществ',
       answer_rule='выбрать два вещества с катионом NH₄⁺ (RNH₃⁺) или молекулой CO',
       mistakes=['выбирают аммиак (в молекуле NH₃ связи обменные)', 'выбирают любые соли'],
       solve=_solve_da, kes=K4,
       fidelity=fid(4, 'ЕГЭ', trap='NH₃ — нет, NH₄Cl — есть', scale=SC4, kes=['1.4']))
def g_da(rng):
    pool = [s for s in pool_for('e') if s['f'] not in DA_AMBIG]
    q = rng.choice(['Укажите два соединения из перечня, содержащие ковалентную связь, возникшую по '
                    'донорно-акцепторному механизму.',
                    'В каких двух соединениях из перечня есть связь, образованная по донорно-акцепторному механизму?'])
    return list_card('ch-ege-04-da', rng, pool, lambda s: 'd' in s['bonds'], q, {},
                     explain=lambda s: f'{pretty(s["f"])} — {"есть" if "d" in s["bonds"] else "нет"}')


COMBOS = [('p', 'ion'), ('p', 'atom'), ('n', 'atom'), ('n', 'mol'), ('p', 'mol'), ('n', 'ion'), ('p', 'nonmol'),
          ('n', 'nonmol'), ('c', 'nonmol'), ('-n', 'nonmol'), ('pn', 'mol')]
BOND_GEN = {'p': 'ковалентная полярная связь', 'n': 'ковалентная неполярная связь', 'c': 'ковалентная связь',
            '-n': None, 'pn': 'и полярная, и неполярная ковалентные связи'}


def _has(b, bonds):
    if b == 'c':
        return bool(bonds & {'p', 'n'})
    if b == '-n':
        return 'n' not in bonds
    if b == 'pn':
        return {'p', 'n'} <= bonds
    return b in bonds


def _lat_ok(L, lat):
    return lat != 'mol' if L == 'nonmol' else lat == L


def _solve_combo(p):
    return ids_of(p['subs'], lambda f: _has(p['b'], solve_bonds(f)) and _lat_ok(p['L'], solve_lattice(f)))


@proto('ch-ege-04-combo', 'ЕГЭ', 4, 'Вид связи и тип решётки (строение) одновременно',
       invariant='проверить у каждого вещества два признака: наличие (отсутствие) связи данного вида и тип '
                 'кристаллической решётки / молекулярное или немолекулярное строение',
       varies='сочетание (ковалентная полярная + ионная решётка, неполярная + атомная, ковалентная + немолекулярное '
              'строение и т. д.), перечень',
       answer_rule='выбрать вещества, удовлетворяющие обоим признакам; вещества с одним признаком — ловушки',
       mistakes=['проверяют только один признак', 'забывают о ковалентных связях внутри сложных ионов'],
       solve=_solve_combo, kes=K4,
       fidelity=fid(4, 'ЕГЭ', trap='как в демоверсии 2027: ковалентная полярная связь + ионная решётка (алкоголяты, '
                                    'щёлочи), рядом — хлорид магния и аммиак', scale=SC4, kes=['1.4']))
def g_combo(rng):
    b, L = rng.choice(COMBOS)
    pool = pool_for('e')
    pred = lambda s: _has(b, s['bonds']) and _lat_ok(L, s['lat'])
    part = [s for s in pool if not pred(s) and (_has(b, s['bonds']) or _lat_ok(L, s['lat']))]
    rest = [s for s in pool if not pred(s) and s not in part]
    yes = [s for s in pool if pred(s)]
    if len(yes) < 2 or len(part) < 2:
        raise Retry
    k_rest = 1 if rest else 0
    items = rng.sample(yes, 2) + rng.sample(part, 3 - k_rest) + rng.sample(rest, k_rest)
    if len({s['f'] for s in items}) < 5:
        raise Retry
    rng.shuffle(items)
    struct = {'ion': 'с ионной кристаллической решёткой', 'atom': 'с атомной кристаллической решёткой',
              'mol': 'молекулярного строения', 'nonmol': 'немолекулярного строения'}[L]
    if b == '-n':
        cond = 'в которых нет ковалентной неполярной связи'
    else:
        cond = f'в которых имеется {BOND_GEN[b]}'
    q = rng.choice([f'Укажите два вещества {struct}, {cond}.',
                    f'Среди перечисленных веществ отметьте два вещества {struct}, {cond}.'])
    names = rng.random() < 0.6
    ans = ids_of(items, pred)
    e = '; '.join(f'{pretty(s["f"])} — {", ".join(BOND_TXT[x] for x in "ipnm" if x in s["bonds"])}, решётка '
                  f'{LAT_TXT[s["lat"]]}' for s in items) + f'. Ответ: {"".join(ans)}.'
    return pcard('ch-ege-04-combo', kim_list(q) + ' ' + rng.choice(['Запишите номера выбранных ответов.',
                                                                    'Запишите в поле ответа номера выбранных '
                                                                    'веществ.']), ans, e, k='many',
                 o=opts([sub_view(s, names) for s in items]), p={'b': b, 'L': L, 'subs': [s['f'] for s in items]})


# свойства веществ с разными кристаллическими решётками: признак → чем обусловлен (частицы в узлах/связь)
LAT_PROPS = [
    ('высокая электропроводность в твёрдом состоянии', 'free_e'), ('пластичность (ковкость)', 'free_e'),
    ('металлический блеск', 'free_e'), ('высокая теплопроводность', 'free_e'),
    ('хрупкость кристаллов', 'ions'), ('растворы и расплавы проводят электрический ток', 'ions'),
    ('высокая температура плавления', 'strong'), ('нелетучесть', 'strong'),
    ('низкая температура плавления', 'weak'), ('летучесть', 'weak'), ('малая твёрдость', 'weak'),
    ('у многих веществ есть запах', 'weak'),
    ('отсутствие электропроводности в твёрдом состоянии', 'nocond'),
    ('очень высокая твёрдость', 'covnet'), ('нерастворимость в воде и других растворителях', 'covnet'),
]
# свойства, которые у части веществ данного типа всё же встречаются, — в дистракторы не берём
PROPS_AMBIG = {'met': {'растворы и расплавы проводят электрический ток', 'низкая температура плавления', 'малая твёрдость', 'очень высокая твёрдость',
                       'нерастворимость в воде и других растворителях', 'высокая температура плавления', 'нелетучесть',
                       'хрупкость кристаллов'},
               'ion': {'нерастворимость в воде и других растворителях', 'очень высокая твёрдость'},
               'mol': {'хрупкость кристаллов', 'нерастворимость в воде и других растворителях'},
               'atom': {'отсутствие электропроводности в твёрдом состоянии', 'металлический блеск', 'высокая электропроводность в твёрдом состоянии', 'хрупкость кристаллов',
                        'высокая теплопроводность'}}
LAT_ACC = {'ion': 'ионную', 'met': 'металлическую', 'mol': 'молекулярную', 'atom': 'атомную'}
LAT_FEAT = {'met': {'free_e'}, 'ion': {'ions', 'strong', 'nocond'}, 'mol': {'weak', 'nocond'}, 'atom': {'covnet', 'strong'}}


def _solve_props(p):
    # второй путь: что находится в узлах решётки и чем связаны частицы
    nodes = {'met': ('катионы металла и обобществлённые электроны', {'free_e'}),
             'ion': ('катионы и анионы, прочная ионная связь, свободных электронов нет', {'ions', 'strong', 'nocond'}),
             'mol': ('молекулы, слабое межмолекулярное взаимодействие, свободных электронов нет', {'weak', 'nocond'}),
             'atom': ('атомы, прочные ковалентные связи во всём кристалле', {'covnet', 'strong'})}[p['L']][1]
    return sorted(str(i + 1) for i, need in enumerate(p['needs']) if need in nodes)


@proto('ch-ege-04-props', 'ЕГЭ', 4, 'Свойства веществ с данным типом кристаллической решётки',
       invariant='по частицам в узлах решётки и силе связи между ними предсказать физические свойства вещества',
       varies='тип решётки (ионная, металлическая, молекулярная, атомная), набор из пяти свойств',
       answer_rule='металлическая — электро- и теплопроводность, пластичность, блеск; ионная — тугоплавкость, '
                   'хрупкость, проводимость растворов/расплавов; молекулярная — летучесть, легкоплавкость, малая '
                   'твёрдость; атомная — очень высокая твёрдость, тугоплавкость, нерастворимость',
       mistakes=['приписывают ионным кристаллам электропроводность в твёрдом состоянии', 'путают атомную и '
                 'молекулярную решётку'],
       solve=_solve_props, kind='dict', kes=K4,
       fidelity=fid(4, 'ЕГЭ', trap='высокая температура плавления — и у ионных, и у атомных кристаллов; '
                                    'электропроводность в твёрдом виде — только у металлов',
                    scale='пять свойств, тип решётки — как в банке (3 задания из 77)', kes=['1.4']))
def g_props(rng):
    L = rng.choice(['met', 'ion', 'mol', 'atom'])
    feat = LAT_FEAT[L]
    yes = [x for x in LAT_PROPS if x[1] in feat]
    ambig = PROPS_AMBIG[L]
    no = [x for x in LAT_PROPS if x[1] not in feat and x[0] not in ambig]
    items = rng.sample(yes, 2) + rng.sample(no, 3)
    if len({x[1] for x in items[2:]}) < 2:
        raise Retry
    rng.shuffle(items)
    q = (f'Из предложенного перечня выберите два свойства, типичные для веществ, кристаллы которых построены по типу '
         f'{LAT_TXT[L][:-2]}ой решётки.')
    ans = sorted(str(i + 1) for i, x in enumerate(items) if x[1] in feat)
    e = {'met': 'В узлах — катионы металла, между ними свободные электроны: отсюда электро- и теплопроводность, '
                'пластичность, блеск.',
         'ion': 'В узлах — ионы, связанные прочной ионной связью: кристаллы тугоплавки, нелетучи, хрупки; ток проводят '
                'растворы и расплавы.',
         'mol': 'В узлах — молекулы, связанные слабо: вещества летучи, легкоплавки, мягкие, часто имеют запах.',
         'atom': 'В узлах — атомы, связанные прочными ковалентными связями по всему кристаллу: очень твёрдые, '
                 'тугоплавкие, нерастворимые.'}[L] + f' Ответ: {"".join(ans)}.'
    return pcard('ch-ege-04-props', kim_list(q) + ' Запишите номера выбранных ответов.', ans, e, k='many',
                 o=opts([x[0] for x in items]), p={'L': L, 'needs': [x[1] for x in items]})


# ================================================================= ОГЭ 1. Химический элемент / простое вещество / сложное вещество
# Высказывания составлены самостоятельно (факты школьного курса). E — об элементе, S — о простом веществе.
FACTS = {
    'O': ('кислороде', [
        'Кислород входит в состав молекул воды и углекислого газа.',
        'Почти половину массы земной коры составляет кислород.',
        'В оксидах кислород проявляет степень окисления −2.',
        'Ядро атома кислорода содержит 8 протонов.'], [
        'Тлеющая лучинка, внесённая в сосуд с кислородом, ярко вспыхивает.',
        'Кислород плохо растворяется в воде.',
        'Кислород из баллонов подают больным при затруднённом дыхании.',
        'Кислород получают в лаборатории разложением перманганата калия.']),
    'N': ('азоте', [
        'Азот входит в состав белков и нуклеиновых кислот.',
        'В аммиаке азот имеет степень окисления −3.',
        'Недостаток азота в почве восполняют внесением селитры.',
        'На внешнем электронном слое атома азота находится пять электронов.'], [
        'Азот занимает около 78 % объёма воздуха.',
        'Жидкий азот кипит при температуре −196 °C.',
        'Азот при комнатной температуре реагирует с литием.',
        'Азотом заполняют упаковки с продуктами, чтобы замедлить их порчу.']),
    'H': ('водороде', [
        'Водород входит в состав всех кислот.',
        'В гидридах металлов водород имеет степень окисления −1.',
        'Водород — самый распространённый элемент во Вселенной.',
        'Массовая доля водорода в метане составляет 25 %.'], [
        'Водород — самый лёгкий газ.',
        'Смесь водорода с кислородом взрывается при поджигании.',
        'При нагревании водород восстанавливает медь из оксида меди(II).',
        'Водород рассматривают как экологически чистое топливо для автомобилей.']),
    'Cl': ('хлоре', [
        'Хлор входит в состав поваренной соли.',
        'В составе соляной кислоты хлор присутствует в желудочном соке.',
        'В хлорной кислоте хлор проявляет степень окисления +7.',
        'Атом хлора имеет семь электронов на внешнем слое.'], [
        'Хлор при обычных условиях — газ жёлто-зелёного цвета с удушливым запахом.',
        'Хлор вытесняет бром из раствора бромида калия.',
        'Хлором обеззараживают водопроводную воду.',
        'Раскалённая железная проволока сгорает в хлоре.']),
    'S': ('сере', [
        'Сера входит в состав некоторых аминокислот.',
        'В сероводороде сера проявляет степень окисления −2.',
        'Массовая доля серы в сульфиде железа(II) превышает 36 %.',
        'Атомы серы и кислорода имеют одинаковое число внешних электронов.'], [
        'Сера — твёрдое вещество жёлтого цвета, не смачиваемое водой.',
        'Сера горит синим пламенем.',
        'Сера реагирует с ртутью уже при комнатной температуре.',
        'Серу применяют для вулканизации каучука.']),
    'P': ('фосфоре', [
        'Фосфор входит в состав костной ткани в виде фосфата кальция.',
        'В ортофосфорной кислоте фосфор имеет степень окисления +5.',
        'Фосфор относится к элементам питания растений, его вносят с суперфосфатом.',
        'Ядро атома фосфора содержит 15 протонов.'], [
        'Белый фосфор светится в темноте.',
        'Красный фосфор входит в состав намазки спичечного коробка.',
        'При горении фосфора образуется густой белый дым.',
        'Белый фосфор хранят под слоем воды.']),
    'Si': ('кремнии', [
        'Кремний — второй по распространённости элемент земной коры.',
        'Кремний входит в состав песка и глины.',
        'В силикатах кремний проявляет степень окисления +4.',
        'Электроны в атоме кремния расположены на трёх электронных слоях.'], [
        'Кристаллический кремний — полупроводник, из него изготавливают солнечные батареи.',
        'Кремний растворяется в концентрированных растворах щелочей с выделением водорода.',
        'Кремний — твёрдое вещество серого цвета с металлическим блеском.',
        'Кремний получают восстановлением оксида кремния(IV) магнием.']),
    'Na': ('натрии', [
        'Натрий входит в состав поваренной соли и питьевой соды.',
        'Ионы натрия участвуют в передаче нервных импульсов.',
        'В соединениях натрий проявляет степень окисления +1.',
        'В ядре атома натрия содержится 11 протонов.'], [
        'Натрий хранят под слоем керосина.',
        'Натрий настолько мягкий, что режется ножом.',
        'Натрий бурно реагирует с водой с выделением водорода.',
        'Натрий плавится при температуре ниже 100 °C.']),
    'K': ('калии', [
        'Калий необходим растениям, его вносят в почву с калийными удобрениями.',
        'Калий входит в состав поташа.',
        'Ионы калия необходимы для работы сердечной мышцы.',
        'В соединениях калий имеет степень окисления +1.'], [
        'Калий — мягкий серебристый металл.',
        'Калий реагирует с водой ещё энергичнее, чем натрий.',
        'Калий хранят без доступа воздуха под слоем минерального масла.',
        'Калий плавится при температуре около 63 °C.']),
    'Mg': ('магнии', [
        'Магний входит в состав хлорофилла.',
        'Массовая доля магния в оксиде магния составляет 60 %.',
        'В соединениях магний проявляет степень окисления +2.',
        'Соли магния, растворённые в воде, обусловливают её жёсткость.'], [
        'Магний горит ослепительно белым пламенем.',
        'Из сплавов магния изготавливают лёгкие детали самолётов.',
        'Магний вытесняет медь из раствора сульфата меди(II).',
        'Магний медленно реагирует с горячей водой.']),
    'Ca': ('кальции', [
        'Кальций входит в состав костей и зубов.',
        'Кальций содержится в меле, мраморе и известняке.',
        'В соединениях кальций проявляет степень окисления +2.',
        'Массовая доля кальция в карбонате кальция равна 40 %.'], [
        'Кальций — серебристо-белый металл, который хранят без доступа воздуха.',
        'Кальций реагирует с водой с выделением водорода.',
        'При нагревании на воздухе кальций сгорает.',
        'Кальций применяют как восстановитель при получении некоторых редких металлов.']),
    'Al': ('алюминии', [
        'Алюминий — самый распространённый металл в земной коре.',
        'Алюминий входит в состав глины и корунда.',
        'В соединениях алюминий проявляет степень окисления +3.',
        'Массовая доля алюминия в оксиде алюминия составляет около 53 %.'], [
        'На воздухе алюминий покрывается тонкой прочной оксидной плёнкой.',
        'Из алюминия изготавливают фольгу и лёгкую посуду.',
        'Алюминий растворяется в растворах щелочей.',
        'Алюминий — лёгкий серебристый металл, хорошо проводящий электрический ток.']),
    'Fe': ('железе', [
        'Железо входит в состав гемоглобина крови.',
        'В оксидах железо проявляет степени окисления +2 и +3.',
        'Массовая доля железа в оксиде железа(III) составляет 70 %.',
        'Железо входит в состав минералов магнетита и гематита.'], [
        'Железо притягивается магнитом.',
        'Во влажном воздухе железо ржавеет.',
        'Железо сгорает в кислороде, разбрасывая искры.',
        'Железо вытесняет медь из раствора сульфата меди(II).']),
    'Cu': ('меди', [
        'Медь входит в состав медного купороса.',
        'В оксиде меди(II) медь проявляет степень окисления +2.',
        'Медь относится к микроэлементам, необходимым организму человека.',
        'Массовая доля меди в оксиде меди(II) равна 80 %.'], [
        'Медь — металл красноватого цвета, хорошо проводящий электрический ток.',
        'Медь не вытесняет водород из разбавленной серной кислоты.',
        'Медь растворяется в концентрированной азотной кислоте.',
        'Из меди изготавливают электрические провода.']),
    'Zn': ('цинке', [
        'Цинк необходим организму для работы многих ферментов.',
        'В соединениях цинк проявляет степень окисления +2.',
        'Цинк входит в состав минерала цинковой обманки.',
        'Массовая доля цинка в оксиде цинка составляет около 80 %.'], [
        'Цинк вытесняет водород из соляной кислоты.',
        'Цинком покрывают стальные листы для защиты от коррозии.',
        'Цинк реагирует с растворами щелочей.',
        'Цинк — голубовато-серебристый металл.']),
    'I': ('иоде', [
        'Иод необходим для нормальной работы щитовидной железы.',
        'Иод содержится в морских водорослях.',
        'Для профилактики нехватки иода в пищу добавляют иодированную соль.',
        'В иодиде калия иод имеет степень окисления −1.'], [
        'Иод образует тёмно-фиолетовые кристаллы с металлическим блеском.',
        'При нагревании иод переходит в пар, минуя жидкое состояние.',
        'Иод окрашивает крахмал в синий цвет.',
        'Спиртовым раствором иода обрабатывают края царапин.']),
}
K_OGE1 = ['1.1', '1.2']


def _solve_elem_simple(p):
    # код высказывания «элемент:категория:номер»; категория задана при составлении банка
    want = p['cat']
    return sorted(str(i + 1) for i, c in enumerate(p['codes']) if c.split(':')[1] == want)


@proto('ch-oge-01-element', 'ОГЭ', 1, 'Химический элемент или простое вещество',
       invariant='отличить высказывания о химическом элементе (состав, строение атома, степень окисления, '
                 'распространённость) от высказываний о простом веществе (физические свойства, реакции, применение)',
       varies='элемент (16 металлов и неметаллов), что спрашивают (элемент или простое вещество), набор высказываний',
       answer_rule='элемент — «входит в состав», «массовая доля», «степень окисления», «ядро атома»; простое '
                   'вещество — агрегатное состояние, цвет, реагирует, применяют',
       mistakes=['«входит в состав» принимают за простое вещество', 'распространённость в воздухе (азот, кислород) '
                 'относят к элементу, хотя речь о простом веществе'],
       solve=_solve_elem_simple, kind='dict', kes=K_OGE1,
       fidelity=fid(1, 'ОГЭ', trap='«азот составляет 78 % воздуха» — простое вещество; «кальций входит в состав костей» '
                                    '— элемент', scale='16 распространённых элементов школьного курса, 5 высказываний',
                    kes=['1.1', '1.2']))
def g_elem_simple(rng):
    el = rng.choice(list(FACTS))
    prep, fe, fs = FACTS[el]
    cat = rng.choice(['E', 'S'])
    good, bad = (fe, fs) if cat == 'E' else (fs, fe)
    gi = rng.sample(range(4), 2)
    bi = rng.sample(range(4), 3)
    items = [(good[i], f'{el}:{cat}:{i}') for i in gi] + [(bad[i], f'{el}:{"S" if cat == "E" else "E"}:{i}') for i in bi]
    rng.shuffle(items)
    what = 'химическом элементе' if cat == 'E' else 'простом веществе'
    q = rng.choice([f'Выберите два высказывания, в которых говорится о {prep} как о {what}.',
                    f'Выберите два утверждения, в которых говорится о {prep} как о {what}.'])
    codes = [c for _, c in items]
    ans = sorted(str(i + 1) for i, c in enumerate(codes) if c.split(':')[1] == cat)
    e = ('Об элементе говорят, когда речь о составе веществ, строении атома, степени окисления, массовой доле; '
         'о простом веществе — когда описаны его физические свойства, реакции, применение. Ответ: ' + ''.join(ans) + '.')
    return pcard('ch-oge-01-element', q + ' Запишите номера выбранных ответов.', ans, e, k='many',
                 o=opts([t for t, _ in items]), p={'cat': cat, 'codes': codes})


FACTS_NOM = {s: E[s]['nom'] for s in FACTS}

# предложения с выделенным (в кавычках-ёлочках) названием вещества; формула — для независимой проверки
SENT = [
    ('O2', 'При горении свечи расходуется «кислород» воздуха.'),
    ('O3', 'Слой «озона» в стратосфере задерживает жёсткое ультрафиолетовое излучение.'),
    ('N2', 'Жидкий «азот» применяют для быстрой заморозки продуктов.'),
    ('H2', 'Оболочки первых дирижаблей наполняли «водородом».'),
    ('He', 'Праздничные воздушные шары наполняют «гелием».'),
    ('Cl2', 'На водопроводных станциях воду обеззараживают «хлором».'),
    ('I2', 'Кристаллы «иода» при нагревании превращаются в фиолетовый пар.'),
    ('S', 'Порошком «серы» обрабатывают виноградники от грибковых болезней.'),
    ('C', 'Стержень простого карандаша изготавливают из «графита» с добавкой глины.'),
    ('C', 'Стеклорез снабжён маленьким кристаллом «алмаза».'),
    ('Fe', 'Гвоздь из «железа» во влажном воздухе покрывается ржавчиной.'),
    ('Cu', 'Обмотку электродвигателей делают из «меди».'),
    ('Al', 'Фольгу для запекания изготавливают из «алюминия».'),
    ('Ag', 'Столовые приборы из «серебра» со временем темнеют.'),
    ('Ne', 'Газоразрядные трубки, заполненные «неоном», светятся красным светом.'),
    ('Zn', 'Стальные вёдра покрывают тонким слоем «цинка».'),
    ('P', 'В намазку спичечного коробка добавляют «красный фосфор».'),
    ('Mg', 'Лента «магния» сгорает ослепительно ярким пламенем.'),
    ('Hg', 'В старых термометрах столбик «ртути» поднимался при нагревании.'),
    ('H2O', 'При электролизе «вода» разлагается на два газа.'),
    ('NH3', 'Нашатырный спирт — это водный раствор «аммиака».'),
    ('CH4', 'Основным компонентом природного газа является «метан».'),
    ('CO2', 'Газированные напитки насыщают «углекислым газом».'),
    ('NaCl', 'Для засолки огурцов используют «поваренную соль».'),
    ('NaHCO3', 'Тесто разрыхляют «питьевой содой».'),
    ('CaCO3', 'Школьный «мел» оставляет на доске белый след.'),
    ('C6H12O6', 'Раствор «глюкозы» вводят больным для поддержания сил.'),
    ('C2H5OH', 'Медицинским «этиловым спиртом» обрабатывают кожу перед уколом.'),
    ('C3H8O3', 'В увлажняющие кремы добавляют «глицерин».'),
    ('H2SO4', 'Автомобильные аккумуляторы заливают раствором «серной кислоты».'),
    ('H2S', 'Запах тухлых яиц обусловлен «сероводородом».'),
    ('CaO', 'При гашении «негашёной извести» выделяется много теплоты.'),
    ('H2O2', 'Раствором «пероксида водорода» обрабатывают ссадины.'),
    ('C12H22O11', 'Из сахарной свёклы получают «сахарозу».'),
    ('CO', 'При неполном сгорании топлива образуется ядовитый «угарный газ».'),
    ('CH3COOH', 'Для маринада используют разбавленный раствор «уксусной кислоты».'),
]


def _solve_simple_complex(p):
    want_simple = p['cat'] == 'simple'
    return sorted(str(i + 1) for i, f in enumerate(p['fs']) if (len(parse_formula(f)) == 1) == want_simple)


@proto('ch-oge-01-simple', 'ОГЭ', 1, 'Простое или сложное вещество в тексте',
       invariant='определить, из атомов скольких элементов состоит названное в предложении вещество',
       varies='пять предложений о применении/свойствах веществ, спрашивают простые или сложные вещества',
       answer_rule='простое — из атомов одного элемента (в т. ч. озон, графит, алмаз), сложное — из разных',
       mistakes=['считают озон или графит сложными веществами', 'считают простым веществом бытовое название '
                 '(«сода», «мел»)'],
       solve=_solve_simple_complex, kind='dict', kes=K_OGE1,
       fidelity=fid(1, 'ОГЭ', trap='аллотропные модификации (озон, алмаз, графит) — простые вещества',
                    scale='вещества повседневной жизни, 5 предложений, выделенное слово', kes=['1.1', '1.2']))
def g_simple_complex(rng):
    cat = rng.choice(['simple', 'complex'])
    is_simple = lambda f: len(parse_formula(f)) == 1
    yes = [s for s in SENT if is_simple(s[0]) == (cat == 'simple')]
    no = [s for s in SENT if is_simple(s[0]) != (cat == 'simple')]
    items = rng.sample(yes, 2) + rng.sample(no, 3)
    rng.shuffle(items)
    w = 'простое' if cat == 'simple' else 'сложное'
    q = f'Выберите два утверждения, в которых выделенное (взятое в кавычки) слово обозначает {w} вещество.'
    ans = ids_of([f for f, _ in items], lambda f: is_simple(f) == (cat == 'simple'))
    e = '; '.join(f'{t[t.index("«") + 1:t.index("»")]} — {pretty(f)}, {"простое" if is_simple(f) else "сложное"}'
                  for f, t in items) + f'. Ответ: {"".join(ans)}.'
    return pcard('ch-oge-01-simple', q + ' Запишите номера выбранных ответов.', ans, e, k='many',
                 o=opts([t for _, t in items]), p={'cat': cat, 'fs': [f for f, _ in items]})


# ================================================================= ОГЭ 2. Модель атома / ячейка ПСХЭ → «X Y»
K_OGE2 = ['2.1', '2.2']
OGE_EL = [s for s in E if E[s]['Z'] <= 20]
QTY = {'period': 'номер периода', 'group': 'номер группы', 'charge': 'заряд ядра',
       'electrons': 'общее число электронов', 'outer': 'число электронов на внешнем электронном слое',
       'neutrons': 'число нейтронов в ядре'}
QTY_X = {'period': '{v} — номер периода, где находится этот элемент',
         'group': '{v} — номер группы, к которой относится этот элемент',
         'charge': '{v} — заряд ядра его атома',
         'electrons': '{v} — общее число электронов в его атоме',
         'outer': '{v} — число электронов во внешнем слое его атома',
         'neutrons': '{v} — число нейтронов в ядре его атома'}


def _val(s, what, A=None):
    e = E[s]
    return {'period': e['period'], 'group': e['group'], 'charge': e['Z'], 'electrons': e['Z'],
            'outer': outer_count(cfg_cells(s)), 'neutrons': None if A is None else A - e['Z']}[what]


def _solve_model(p):
    if p['model'] == 'layers':
        Z = sum(p['layers'])
    elif p['model'] == 'nucleus':
        Z = p['protons']
    else:
        Z = p['Z']
    A = p.get('A')
    def v(w):
        return {'period': r_period(Z), 'group': r_valence(Z), 'charge': Z, 'electrons': Z, 'outer': r_outer(Z),
                'neutrons': None if A is None else A - Z}[w]
    return f'{v(p["x"])}{v(p["y"])}'


def model_card(pid, rng, model):
    s = rng.choice([x for x in OGE_EL if model == 'layers' or x != 'Cl'])
    e = E[s]
    cells = cfg_cells(s)
    layers = [sum(c for (n, l), c in cells.items() if n == k) for k in range(1, outer_n(cells) + 1)]
    A = int(AR[s]) if s in AR and s != 'Cl' else None
    opts_q = ['period', 'group', 'charge', 'outer']
    if model in ('nucleus', 'cell') and A:
        opts_q += ['neutrons', 'electrons']
    if model == 'layers':
        opts_q = ['period', 'group', 'charge']
    x, y = rng.sample(opts_q, 2)
    if model == 'nucleus' and 'charge' in (x, y):
        raise Retry
    if s in ('He', 'Ne', 'Ar') and 'group' in (x, y):
        raise Retry
    p = {'model': model, 'x': x, 'y': y}
    if model == 'layers':
        lay = ', '.join(str(v) for v in layers)
        intro = rng.choice([f'Модель атома химического элемента: вокруг ядра расположены электронные слои, на которых '
                            f'находится соответственно {lay} {plural(layers[-1], "электрон", "электрона", "электронов")} '
                            f'(от ядра к периферии).',
                            f'В модели атома некоторого химического элемента электроны распределены по электронным слоям '
                            f'так: {lay} (начиная от ядра).'])
        p['layers'] = layers
    elif model == 'nucleus':
        n = A - e['Z']
        intro = rng.choice([f'Модель ядра атома некоторого химического элемента: в ядре {e["Z"]} '
                            f'{plural(e["Z"], "протон", "протона", "протонов")} и {n} '
                            f'{plural(n, "нейтрон", "нейтрона", "нейтронов")}.',
                            f'Ядро атома химического элемента состоит из {e["Z"]} '
                            f'{plural(e["Z"], "протона", "протонов", "протонов")} и {n} '
                            f'{plural(n, "нейтрона", "нейтронов", "нейтронов")}.'])
        p['protons'] = e['Z']
        p['A'] = A
    else:
        intro = (f'Ячейка Периодической системы содержит сведения о химическом элементе: {e["Z"]} — порядковый номер, '
                 f'{s} — символ, {A if A else AR[s]} — относительная атомная масса (округлённая).')
        p['Z'] = e['Z']
        if A:
            p['A'] = A
    q = (f'{intro} Запишите в таблицу величины X и Y, где {QTY_X[x].format(v="X")}, {QTY_X[y].format(v="Y")}. '
         f'(Для записи ответа используйте арабские цифры.)')
    vx, vy = _val(s, x, A), _val(s, y, A)
    ans = f'{vx}{vy}'
    e_txt = (f'Это {e["nom"]} ({s}): Z = {e["Z"]}, период {e["period"]}, группа {ROMAN[e["group"]]}A, '
             f'на внешнем слое {outer_count(cells)} e' + (f', нейтронов {A - e["Z"]}' if A else '') +
             f'. X = {vx}, Y = {vy}; ответ {ans}.')
    wrong = [f'{vy}{vx}', f'{_val(s, "period", A)}{e["Z"]}' if ans != f'{e["period"]}{e["Z"]}' else f'{e["group"]}{e["Z"]}',
             f'{vx}{e["Z"] + 1}']
    return pcard(pid, q, ans, e_txt, k='num', p=p, wrong=wrong)


FID_OGE2 = dict(fmt_='две величины X и Y арабскими цифрами подряд (как в таблице ответа КИМ)',
                style='КИМ ОГЭ: «Запишите в таблицу … (X) … (Y) … (Для записи ответа используйте арабские цифры.)»; рисунок модели заменён словесным описанием с теми же числами')


@proto('ch-oge-02-layers', 'ОГЭ', 2, 'Модель атома (распределение электронов по слоям) → период/группа/заряд',
       invariant='по числу электронов на слоях найти Z (сумма), период (число слоёв), группу (электроны внешнего слоя)',
       varies='элемент Z ≤ 20, пара величин X и Y (период, группа, заряд ядра)',
       answer_rule='Z = сумма электронов; период = число слоёв; группа (A) = электроны внешнего слоя',
       mistakes=['записывают X и Y в обратном порядке', 'за номер группы берут число слоёв'],
       solve=_solve_model, kes=K_OGE2,
       fidelity=fid(2, 'ОГЭ', trap='порядок X и Y; период ↔ группа', scale='элементы первых трёх периодов, K, Ca',
                    kes=['2.1', '2.2'], **FID_OGE2))
def g_model_layers(rng):
    return model_card('ch-oge-02-layers', rng, 'layers')


@proto('ch-oge-02-nucleus', 'ОГЭ', 2, 'Модель ядра (протоны и нейтроны) → положение и строение атома',
       invariant='число протонов = Z; по Z найти период, группу, число внешних электронов; нейтроны даны отдельно',
       varies='элемент Z ≤ 20, пара величин (период, группа, внешние электроны, электроны, нейтроны)',
       answer_rule='Z = число протонов; электроны = Z; дальше — по ПСХЭ',
       mistakes=['за Z принимают число нейтронов или массовое число', 'путают X и Y'],
       solve=_solve_model, kes=K_OGE2,
       fidelity=fid(2, 'ОГЭ', trap='нейтроны не определяют положение элемента', scale='элементы Z ≤ 20',
                    kes=['2.1', '2.2'], **FID_OGE2))
def g_model_nucleus(rng):
    return model_card('ch-oge-02-nucleus', rng, 'nucleus')


@proto('ch-oge-02-cell', 'ОГЭ', 2, 'Ячейка ПСХЭ → заряд ядра, период, группа, нейтроны',
       invariant='по данным ячейки (порядковый номер, символ, Ar) найти заряд ядра, положение, число нейтронов',
       varies='элемент Z ≤ 20, пара величин X и Y',
       answer_rule='заряд ядра = порядковый номер; нейтроны = округлённая Ar − Z',
       mistakes=['нейтроны = Ar, а не Ar − Z', 'путают X и Y'],
       solve=_solve_model, kes=K_OGE2,
       fidelity=fid(2, 'ОГЭ', trap='Ar округляют до целого; нейтроны = A − Z', scale='элементы Z ≤ 20 (Cl не берём '
                                                                                     'из-за Ar = 35,5)',
                    kes=['2.1', '2.2'], **FID_OGE2))
def g_model_cell(rng):
    return model_card('ch-oge-02-cell', rng, 'cell')


# ================================================================= ОГЭ 3. Ряд из трёх элементов: последовательность
K_OGE3 = ['2.3']
OGE3_EL = [s for s in E if E[s]['Z'] <= 20 and E[s]['kind'] in ('m', 'n') and s != 'H']
# свойство: (фраза «в порядке …», знак вдоль периода слева направо, знак вдоль группы сверху вниз, фильтр)
PROPS3 = {
    'radius': (['увеличения радиуса атома', 'уменьшения радиуса атома', 'увеличения атомного радиуса',
                'уменьшения атомного радиуса'], -1, +1, None),
    'en': (['возрастания электроотрицательности', 'уменьшения электроотрицательности'], +1, -1, None),
    'nonmet': (['усиления неметаллических свойств образуемых ими простых веществ',
                'ослабления неметаллических свойств образуемых ими простых веществ'], +1, -1,
               lambda s: E[s]['kind'] == 'n'),
    'metal': (['усиления металлических свойств образуемых ими простых веществ',
               'ослабления металлических свойств образуемых ими простых веществ'], -1, +1, lambda s: E[s]['kind'] == 'm'),
    'reduc': (['увеличения восстановительных свойств образуемых ими простых веществ',
               'уменьшения восстановительных свойств образуемых ими простых веществ'], -1, +1,
              lambda s: E[s]['kind'] == 'm'),
    'oxid': (['усиления окислительных свойств образуемых ими простых веществ',
              'ослабления окислительных свойств образуемых ими простых веществ'], +1, -1, lambda s: E[s]['kind'] == 'n'),
    'acid': (['усиления кислотных свойств образуемых ими высших оксидов',
              'ослабления кислотных свойств образуемых ими высших оксидов'], +1, -1,
             lambda s: E[s]['kind'] == 'n' and s not in ('O', 'F')),
    'base': (['усиления основных свойств образуемых ими высших гидроксидов',
              'ослабления основных свойств образуемых ими высших гидроксидов'], -1, +1, lambda s: E[s]['kind'] == 'm'),
}


PHR3 = {'radius': ('радиус их атомов', 'увеличивался', 'уменьшался'),
        'en': ('электроотрицательность', 'возрастала', 'уменьшалась'),
        'nonmet': ('неметаллические свойства образуемых ими простых веществ', 'усиливались', 'ослабевали'),
        'metal': ('металлические свойства образуемых ими простых веществ', 'усиливались', 'ослабевали'),
        'reduc': ('восстановительная активность соответствующих металлов', 'возрастала', 'уменьшалась'),
        'oxid': ('окислительная способность соответствующих простых веществ', 'возрастала', 'уменьшалась'),
        'acid': ('кислотный характер их высших оксидов', 'усиливался', 'ослабевал'),
        'base': ('основный характер их высших гидроксидов', 'усиливался', 'ослабевал')}


def _cmp_rule(a, b, dp, dg, per, grp):
    """+1 если свойство у a больше, −1 — меньше, None — правилом не сравнить (разные период и группа)."""
    if per(a) == per(b):
        return (dp if grp(a) > grp(b) else -dp) if grp(a) != grp(b) else 0
    if grp(a) == grp(b):
        return dg if per(a) > per(b) else -dg
    return None


def _unique_order(els, cmp):
    """Единственный порядок по возрастанию свойства, совместимый со всеми сравнимыми парами (или None)."""
    good = []
    for perm in itertools.permutations(els):
        ok = True
        for i in range(3):
            for j in range(i + 1, 3):
                c = cmp(perm[i], perm[j])
                if c is None:
                    continue
                if c >= 0:
                    ok = False
        if ok:
            good.append(perm)
    return good[0] if len(good) == 1 else None


def _solve_order3(p):
    rules = {'radius': (-1, 1), 'en': (1, -1), 'nonmet': (1, -1), 'metal': (-1, 1), 'reduc': (-1, 1), 'oxid': (1, -1),
             'acid': (1, -1), 'base': (-1, 1)}
    dp, dg = rules[p['prop']]
    names = p['els']
    per = lambda s: r_period(z_of(s))
    grp = lambda s: r_valence(z_of(s))
    order = _unique_order(names, lambda a, b: _cmp_rule(a, b, dp, dg, per, grp))
    seq = list(order) if p['asc'] else list(order)[::-1]
    return ''.join(str(names.index(s) + 1) for s in seq)


def order3_card(pid, rng, props):
    prop = rng.choice(props)
    phrases, dp, dg, flt = PROPS3[prop]
    pool = [s for s in OGE3_EL if flt is None or flt(s)]
    per = lambda s: E[s]['period']
    grp = lambda s: E[s]['group']
    cmp = lambda a, b: _cmp_rule(a, b, dp, dg, per, grp)
    for _ in range(40):
        els = rng.sample(pool, 3)
        pairs = [cmp(a, b) for a, b in itertools.combinations(els, 2)]
        if pairs.count(None) > 1 or 0 in pairs:
            continue
        order = _unique_order(els, cmp)
        if order:
            break
    else:
        raise Retry
    idx = rng.randrange(len(phrases))
    phrase = phrases[idx]
    asc = phrase.split()[0] in ('увеличения', 'возрастания', 'усиления')
    seq = list(order) if asc else list(order)[::-1]
    ans = ''.join(str(els.index(s) + 1) for s in seq)
    noun, vu, vd = PHR3[prop]
    verb = vu if asc else vd
    q = (f'Расположите химические элементы так, чтобы {noun} {verb}. Запишите указанные номера элементов в '
         f'соответствующем порядке.')
    e = ('; '.join(f'{E[s]["nom"]} — {E[s]["period"]}-й период, {ROMAN[E[s]["group"]]}A' for s in els) +
         '. В периоде слева направо радиус и металлические свойства уменьшаются, ЭО и неметаллические свойства '
         f'растут; в группе сверху вниз — наоборот. Порядок: {" → ".join(E[s]["nom"] for s in seq)}; ответ {ans}.')
    return pcard(pid, q, ans, e, k='num', o=opts([E[s]['nom'] for s in els]),
                 p={'els': els, 'prop': prop, 'asc': asc}, wrong=[ans[::-1], ans[1] + ans[0] + ans[2], ans[0] + ans[2] + ans[1]])


FID_OGE3 = dict(fmt_='три цифры — номера элементов в нужном порядке',
                style='КИМ ОГЭ: «Расположите химические элементы … Запишите указанные номера элементов в соответствующем порядке»; свойство сформулировано своими словами')


@proto('ch-oge-03-radius', 'ОГЭ', 3, 'Три элемента: порядок изменения радиуса атома',
       invariant='по положению в ПСХЭ (период, группа) упорядочить три элемента по радиусу атома',
       varies='три элемента Z ≤ 20 (одного периода, одной группы или «уголком»), увеличение/уменьшение',
       answer_rule='в периоде слева направо радиус уменьшается, в группе сверху вниз увеличивается',
       mistakes=['путают направление в периоде', 'записывают порядок наоборот'],
       solve=_solve_order3, kes=K_OGE3,
       fidelity=fid(3, 'ОГЭ', trap='«уголок» (F, O, S): сравнение через общий элемент', scale='элементы 2–4 периодов '
                    '(Z ≤ 20)', kes=['2.3'], **FID_OGE3))
def g_o3_radius(rng):
    return order3_card('ch-oge-03-radius', rng, ['radius'])


@proto('ch-oge-03-en', 'ОГЭ', 3, 'Три элемента: электроотрицательность, неметаллические и окислительные свойства',
       invariant='упорядочить три элемента по ЭО (неметаллическим/окислительным свойствам простых веществ)',
       varies='три элемента, свойство, направление',
       answer_rule='в периоде слева направо растут, в группе сверху вниз ослабевают',
       mistakes=['путают направление в группе', 'путают «усиления» и «ослабления»'],
       solve=_solve_order3, kes=K_OGE3,
       fidelity=fid(3, 'ОГЭ', trap='направления в периоде и группе противоположны', scale='элементы Z ≤ 20',
                    kes=['2.3'], **FID_OGE3))
def g_o3_en(rng):
    return order3_card('ch-oge-03-en', rng, ['en', 'nonmet', 'oxid'])


@proto('ch-oge-03-metal', 'ОГЭ', 3, 'Три элемента: металлические и восстановительные свойства',
       invariant='упорядочить три металла (элемента) по металлическим/восстановительным свойствам простых веществ',
       varies='три элемента, свойство, направление',
       answer_rule='металлические и восстановительные свойства усиливаются сверху вниз и справа налево',
       mistakes=['считают бериллий активнее кальция', 'путают направление'],
       solve=_solve_order3, kes=K_OGE3,
       fidelity=fid(3, 'ОГЭ', trap='Be–Mg–Ca: восстановительные свойства растут вниз по группе', scale='элементы Z ≤ 20',
                    kes=['2.3'], **FID_OGE3))
def g_o3_metal(rng):
    return order3_card('ch-oge-03-metal', rng, ['metal', 'reduc'])


@proto('ch-oge-03-oxides', 'ОГЭ', 3, 'Три элемента: кислотные свойства высших оксидов / основные свойства гидроксидов',
       invariant='упорядочить элементы по кислотно-основным свойствам их высших оксидов (гидроксидов)',
       varies='три элемента (неметаллы — кислотные оксиды, металлы — основные гидроксиды), направление',
       answer_rule='кислотные свойства высших оксидов растут слева направо и ослабевают сверху вниз; основные — наоборот',
       mistakes=['переносят рост радиуса на кислотность', 'путают оксиды и водородные соединения'],
       solve=_solve_order3, kes=K_OGE3,
       fidelity=fid(3, 'ОГЭ', trap='в группе кислотные свойства высших оксидов ослабевают', scale='элементы Z ≤ 20',
                    kes=['2.3'], **FID_OGE3))
def g_o3_oxides(rng):
    return order3_card('ch-oge-03-oxides', rng, ['acid', 'base'])


# ================================================================= ОГЭ 4. Степень окисления / валентность (соответствие)
K_OGE4 = ['1.3']
# (формула, элемент, степень окисления) — данные генератора; solve считает заново из электронейтральности
OXD = """
N: NH3 -3; NH4Cl -3; NH4Br -3; (NH4)3PO4 -3; Li3N -3; Mg3N2 -3; Ca3N2 -3; N2O 1; NO 2; N2O3 3; HNO2 3; NaNO2 3; KNO2 3; NO2 4; N2O5 5; HNO3 5; KNO3 5; Ca(NO3)2 5; N2 0; (NH4)2SO4 -3; NH4NO2? ; N2H4 -2; NH2OH -1
S: H2S -2; Na2S -2; K2S -2; Al2S3 -2; SO2 4; Na2SO3 4; H2SO3 4; K2SO3 4; SO3 6; H2SO4 6; Na2SO4 6; CaSO4 6; SF6 6; S8 0; NaHSO3 4; KHSO4 6
Cl: HCl -1; NaCl -1; CaCl2 -1; Cl2 0; Cl2O 1; HClO 1; NaClO 1; HClO2 3; NaClO2 3; KClO3 5; HClO3 5; Cl2O7 7; HClO4 7; KClO4 7; ClO2 4
P: PH3 -3; PH4Cl -3; Ca3P2 -3; Na3P -3; Mg3P2 -3; PH4I -3; P2O3 3; H3PO3 3; PCl3 3; P2O5 5; H3PO4 5; Na3PO4 5; Ca3(PO4)2 5; PCl5 5; K2HPO4 5; (NH4)2HPO4 5; NaH2PO4 5; P4 0
C: CH4 -4; Al4C3 -4; Be2C -4; CaC2 -1; CO 2; CO2 4; H2CO3 4; Na2CO3 4; CaCO3 4; CCl4 4; NaHCO3 4; Ca(HCO3)2 4; (NH4)2CO3 4; HCOOH 2; CH3OH -2; CH2O 0; CS2? 
Mn: MnO 2; MnCl2 2; MnSO4 2; Mn(OH)2 2; Mn2O3 3; MnO2 4; K2MnO4 6; KMnO4 7; Mn2O7 7; NaMnO4 7
Cr: CrO 2; CrCl2 2; Cr2O3 3; Cr(OH)3 3; CrCl3 3; Cr2(SO4)3 3; NaCrO2 3; K3Cr(OH)6 3; CrO3 6; K2CrO4 6; K2Cr2O7 6; Na2CrO4 6
Fe: FeO 2; FeCl2 2; FeSO4 2; Fe(OH)2 2; Fe2O3 3; FeCl3 3; Fe(OH)3 3; Fe2(SO4)3 3; Fe(NO3)3 3; K2FeO4 6; Na2FeO4 6
Br: HBr -1; KBr -1; Br2 0; HBrO 1; NaBrO 1; NaBrO2 3; BrF3 3; KBrO3 5; HBrO3 5; HBrO4 7; KBrO4 7
I: HI -1; KI -1; I2 0; HIO 1; NaIO 1; ICl 1; HIO3 5; KIO3 5; IF5 5; HIO4 7; NaIO4 7; IF7 7
Si: Mg2Si -4; Ca2Si -4; SiO2 4; H2SiO3 4; Na2SiO3 4; SiCl4 4; SiF4 4; SiC 4; K2SiO3 4; Si 0
O: H2O -2; Na2O -2; H2O2 -1; Na2O2 -1; BaO2 -1; OF2 2; O2F2 1; O2 0; O3 0
H: H2O 1; HCl 1; H2S 1; HF 1; NaH -1; CaH2 -1; LiH -1; KH -1; H2 0
Cu: Cu2O 1; CuCl 1; Cu2S 1; CuO 2; CuSO4 2; Cu(OH)2 2; Cu(NO3)2 2; CuCl2 2
"""
OX_DATA = {}
for _ln in OXD.strip().splitlines():
    _el, _rest = _ln.split(':', 1)
    rows = []
    for _it in _rest.split(';'):
        _it = _it.strip()
        if not _it or _it.endswith('?'):
            continue
        _f, _v = _it.split()
        rows.append((_f, int(_v)))
    OX_DATA[_el] = rows
NONMET4 = ['N', 'S', 'Cl', 'P', 'C', 'Br', 'I', 'Si', 'O', 'H']
METAL4 = ['Mn', 'Cr', 'Fe', 'Cu']

GROUPS_OX = [('H2PO4', -1), ('HPO4', -2), ('HCO3', -1), ('HSO4', -1), ('HSO3', -1), ('NH4', 1), ('NO3', -1),
             ('NO2', -1), ('SO4', -2), ('SO3', -2), ('CO3', -2), ('PO4', -3), ('OH', -1)]
FIX1 = {'Li', 'Na', 'K'}
FIX2 = {'Be', 'Mg', 'Ca', 'Sr', 'Ba', 'Zn'}


def solve_ox(f, el):
    """Степень окисления el в f из электронейтральности; известные группы (NH₄⁺, SO₄²⁻, OH⁻…) снимаются целиком,
    если el в них не входит; остальным атомам — постоянные степени окисления."""
    rest, total = f, 0
    for g, q in GROUPS_OX:
        if el in parse_formula(g):
            continue
        for m in list(re.finditer(r'\(' + g + r'\)(\d*)', rest)):
            total += q * int(m.group(1) or 1)
        rest = re.sub(r'\(' + g + r'\)(\d*)', '', rest)
        if re.search(g + r'(?![a-z])', rest) and g != 'OH' or (g == 'OH' and rest.endswith('OH')):
            n = len(re.findall(g + r'(?![a-z])', rest)) if g != 'OH' else 1
            total += q * n
            rest = re.sub(g + r'(?![a-z])', '', rest, count=n) if g != 'OH' else rest[:-2]
    comp = parse_formula(rest) if rest else {}
    if el not in comp:
        raise ValueError(f'{f}: {el} потерян при разборе')
    others = [x for x in comp if x != el]
    metals_only = all(x in FIX1 | FIX2 | {'Al'} for x in others)
    for x in others:
        n = comp[x]
        if x in FIX1:
            v = 1
        elif x in FIX2:
            v = 2
        elif x == 'Al':
            v = 3
        elif x == 'F':
            v = -1
        elif x == 'O':
            v = -2
        elif x == 'H':
            v = -1 if metals_only and E[el]['kind'] == 'm' else 1
        elif x in ('Cl', 'Br', 'I'):
            v = -1
        elif x == 'S':
            v = -2
        elif x == 'N':
            v = -3
        elif x == 'C':
            v = -4
        else:
            raise ValueError(f'{f}: нет правила для {x}')
        total += v * n
    return Fr(-total, comp[el])


def ox_view(v):
    return '0' if v == 0 else (f'+{v}' if v > 0 else f'−{-v}')


def _solve_ox_match(p):
    right = {r['id']: r['v'] for r in p['right']}
    out = {}
    for L, f in zip('АБВГ', p['fs']):
        v = solve_ox(f, p['el'])
        out[L] = next(k for k, x in right.items() if Fr(x) == v)
    return out


def ox_match_card(pid, rng, elems, names=False):
    onium = 'N' in elems and rng.random() < 0.3     # как в демо 2027: соль аммония/фосфония (PH₄I, NH₄Cl)
    el = rng.choice(['N', 'P']) if onium else rng.choice(elems)
    rows = OX_DATA[el]
    vals = sorted({v for _, v in rows})
    if len(vals) < 3:
        raise Retry
    picked = rng.sample(rows, 3)
    if onium and not any(('NH4' in f or 'PH4' in f) for f, _ in picked):
        raise Retry
    need = sorted({v for _, v in picked})
    skel = lambda f: tuple(sorted((k, n) for k, n in parse_formula(f).items()
                                  if k not in ('Li', 'Na', 'K', 'Mg', 'Ca', 'Ba', 'Al')))
    if len(need) < 2 or len({skel(f) for f, _ in picked}) < 3:
        raise Retry   # почти одинаковые вещества (K₂SiO₃ и Na₂SiO₃) или одно значение во всех позициях
    extra = [v for v in vals if v not in need]
    rng.shuffle(extra)
    right_vals = need + extra[:4 - len(need)]
    if len(right_vals) < 4:
        cand = [v for v in ((1, 2, 3, 4, 5, 6, 7) if E[el]['kind'] == 'm' else (-4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7))
                if v not in right_vals]
        right_vals += rng.sample(cand, 4 - len(right_vals))
    rng.shuffle(right_vals)
    right = [ox_view(v) for v in right_vals]
    left = [pretty(f) for f, _ in picked]
    o = match_opts(left, right, rids='1234')
    ans = {L: str(right_vals.index(v) + 1) for L, (_, v) in zip('АБВ', picked)}
    gen = E[el]['gen']
    q = rng.choice([f'Установите соответствие между соединением и значением степени окисления атомов {gen} в нём: к '
                    f'каждой позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой.',
                    f'Установите соответствие между химической формулой и тем, какую степень окисления имеет '
                    f'{E[el]["nom"]} в этом соединении: к каждой позиции, обозначенной буквой, подберите '
                    f'соответствующую позицию, обозначенную цифрой.'])
    e = '; '.join(f'{pretty(f)}: {el} {ox_view(v)}' for f, v in picked) + \
        '. Сумма степеней окисления в соединении равна нулю. Ответ: ' + ''.join(ans[L] for L in 'АБВ') + '.'
    return pcard(pid, q + ' Запишите в таблицу выбранные цифры под соответствующими буквами.', ans, e, k='match', o=o,
                 p={'el': el, 'fs': [f for f, _ in picked], 'right': [{'id': str(i + 1), 'v': v} for i, v in
                                                                      enumerate(right_vals)]})


FID_OGE4 = dict(fmt_='три цифры под буквами А, Б, В (соответствие; цифры могут повторяться)',
                style='КИМ ОГЭ 2027: «Установите соответствие …: к каждой позиции, обозначенной буквой, подберите …», «Запишите в таблицу выбранные цифры под соответствующими буквами»; предмет соответствия сформулирован своими словами')


@proto('ch-oge-04-ox-nonmetal', 'ОГЭ', 4, 'Степень окисления неметалла в веществах (соответствие)',
       invariant='степень окисления элемента в формуле из электронейтральности (H +1, O −2, металлы IA/IIA/Al — '
                 'постоянные), в т. ч. в солях аммония, гидридах, пероксидах',
       varies='элемент-неметалл (N, S, Cl, P, C, Br, I, Si, O, H), три формулы, четыре значения',
       answer_rule='сумма степеней окисления = 0; для каждой формулы найти значение и номер в правом столбце',
       mistakes=['в солях аммония считают азот +3 или +5', 'в фосфидах/карбидах ставят положительную степень',
                 'в пероксидах берут кислород −2', 'в гидридах металлов водород +1'],
       solve=_solve_ox_match, kes=K_OGE4,
       fidelity=fid(4, 'ОГЭ', trap='PH₄I, (NH₄)₂HPO₄, Al₄C₃, Ca₃P₂ — как в банке и демо', scale='3 формулы, 4 степени '
                    'окисления, неорганика 8–9 кл.', kes=['1.3'], **FID_OGE4))
def g_ox_nonmetal(rng):
    return ox_match_card('ch-oge-04-ox-nonmetal', rng, NONMET4)


@proto('ch-oge-04-ox-metal', 'ОГЭ', 4, 'Степень окисления переходного металла (Mn, Cr, Fe, Cu) в веществах',
       invariant='степень окисления металла из электронейтральности формулы (оксиды, гидроксиды, соли, оксоанионы)',
       varies='металл (Mn, Cr, Fe, Cu), три формулы (MnO₂, KMnO₄, K₂Cr₂O₇, Fe₂(SO₄)₃…), четыре значения',
       answer_rule='сумма степеней окисления = 0; в оксоанионах металл положительный (+6, +7)',
       mistakes=['в перманганате/дихромате ставят +2/+3', 'не учитывают индекс металла (Cr₂O₇²⁻)'],
       solve=_solve_ox_match, kes=K_OGE4,
       fidelity=fid(4, 'ОГЭ', trap='KMnO₄ (+7) и K₂MnO₄ (+6); K₂Cr₂O₇ (+6) — два атома хрома', scale='3 формулы, '
                    '4 степени окисления', kes=['1.3'], **FID_OGE4))
def g_ox_metal(rng):
    return ox_match_card('ch-oge-04-ox-metal', rng, METAL4)


VAL_DATA = """
S: H2S 2; SO2 4; SO3 6; Na2S 2; CS2 2; SF6 6; Al2S3 2
P: PH3 3; P2O3 3; P2O5 5; PCl3 3; PCl5 5; Ca3P2 3
C: CH4 4; CO2 4; CCl4 4; Al4C3 4; SiC 4
Cl: HCl 1; Cl2O 1; Cl2O7 7; ClO2 4; Cl2O3 3
N: NH3 3; Li3N 3; Mg3N2 3; NCl3 3
Mn: MnO 2; MnO2 4; Mn2O7 7; Mn2O3 3; MnCl2 2
Cr: CrO 2; Cr2O3 3; CrO3 6; CrCl3 3
Fe: FeO 2; Fe2O3 3; FeCl3 3; FeCl2 2; FeS 2
Si: SiO2 4; SiH4 4; SiCl4 4; Mg2Si 4
Cu: Cu2O 1; CuO 2; CuCl2 2; CuCl 1; Cu2S 1
"""
VAL = {}
for _ln in VAL_DATA.strip().splitlines():
    _el, _rest = _ln.split(':', 1)
    VAL[_el] = [(x.split()[0], int(x.split()[1])) for x in _rest.split(';') if x.strip()]
PARTNER_VAL = {'O': 2, 'H': 1, 'Cl': 1, 'F': 1, 'S': 2, 'N': 3, 'P': 3, 'C': 4, 'Na': 1, 'Li': 1, 'Mg': 2, 'Ca': 2,
               'Al': 3, 'Si': 4}


def _solve_val(p):
    right = {r['id']: r['v'] for r in p['right']}
    out = {}
    for L, f in zip('АБВ', p['fs']):
        comp = parse_formula(f)
        other = [x for x in comp if x != p['el']][0]
        v = Fr(PARTNER_VAL[other] * comp[other], comp[p['el']])
        out[L] = next(k for k, x in right.items() if x == v)
    return out


@proto('ch-oge-04-valence', 'ОГЭ', 4, 'Валентность элемента в бинарных соединениях (соответствие)',
       invariant='валентность элемента по формуле бинарного соединения: произведение валентности на индекс '
                 'одинаково у обоих элементов',
       varies='элемент (S, P, C, Cl, N, Mn, Cr, Fe, Si, Cu), три бинарных соединения (оксиды, хлориды, гидриды, '
              'сульфиды, нитриды, фосфиды, карбиды), четыре значения валентности',
       answer_rule='валентность = (валентность партнёра × его индекс) / индекс элемента',
       mistakes=['путают валентность и степень окисления (пишут знак)', 'не учитывают индексы'],
       solve=_solve_val, kes=K_OGE4,
       fidelity=fid(4, 'ОГЭ', trap='Mn₂O₇ — VII, Cl₂O — I; валентность без знака', scale='3 бинарных соединения, '
                    'римские цифры', kes=['1.3'], **FID_OGE4))
def g_valence(rng):
    el = rng.choice(list(VAL))
    rows = VAL[el]
    picked = rng.sample(rows, 3)
    need = sorted({v for _, v in picked})
    skel = lambda f: tuple(sorted((k, n) for k, n in parse_formula(f).items()
                                  if k not in ('Li', 'Na', 'K', 'Mg', 'Ca', 'Ba', 'Al')))
    if len(need) < 2 or len({skel(f) for f, _ in picked}) < 3:
        raise Retry   # почти одинаковые вещества (K₂SiO₃ и Na₂SiO₃) или одно значение во всех позициях
    pool = [v for v in range(1, 8) if v not in need]
    right_vals = need + rng.sample(pool, 4 - len(need))
    rng.shuffle(right_vals)
    o = match_opts([pretty(f) for f, _ in picked], [ROMAN[v] for v in right_vals], rids='1234')
    ans = {L: str(right_vals.index(v) + 1) for L, (_, v) in zip('АБВ', picked)}
    q = (f'Установите соответствие между соединением и валентностью атомов {E[el]["gen"]} в нём: к каждой '
         f'позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой. Запишите в таблицу '
         f'выбранные цифры под соответствующими буквами.')
    e = '; '.join(f'{pretty(f)}: {ROMAN[v]}' for f, v in picked) + '. Ответ: ' + ''.join(ans[L] for L in 'АБВ') + '.'
    return pcard('ch-oge-04-valence', q, ans, e, k='match', o=o,
                 p={'el': el, 'fs': [f for f, _ in picked], 'right': [{'id': str(i + 1), 'v': v} for i, v in
                                                                      enumerate(right_vals)]})


# ================================================================= ОГЭ 5. Вид химической связи
K_OGE5 = ['3.1']
SC5 = 'пять формул неорганических веществ 8–9 кл. (простые вещества, бинарные соединения, соли, кислоты, щёлочи)'
for _pid, _title, _lt, _trap in [
        ('ch-oge-05-bond', 'Вещества с заданным видом связи (ионная, ковалентная полярная/неполярная, металлическая)',
         'ipnm', 'S₈, P₄ — ковалентная неполярная; соли аммония — ионная; металлы — металлическая')]:
    proto(_pid, 'ОГЭ', 5, _title,
          invariant='по составу вещества определить вид химической связи',
          varies='вид связи, перечень из пяти формул',
          answer_rule='металл + неметалл (или NH₄⁺) — ионная; одинаковые атомы неметалла — ковалентная неполярная; '
                      'разные неметаллы — ковалентная полярная; металл — металлическая',
          mistakes=['считают связь в Na металлической и ионной одновременно', 'путают полярную и неполярную',
                    'не относят соли аммония к ионным'],
          solve=_solve_bond, kes=K_OGE5,
          fidelity=fid(5, 'ОГЭ', trap=_trap, scale=SC5, kes=['3.1']))(_bond_gen(_pid, 'ОГЭ', list(_lt)))

proto('ch-oge-05-mixed', 'ОГЭ', 5, 'Вещества, содержащие и ионную, и ковалентную связь',
      invariant='ионная связь между ионами и ковалентная внутри сложного иона',
      varies='перечень формул: соли кислородсодержащих кислот, щёлочи, соли аммония против бинарных солей и '
             'молекулярных веществ',
      answer_rule='выбрать вещества со сложным ионом (SO₄²⁻, NO₃⁻, OH⁻, NH₄⁺, CO₃²⁻, PO₄³⁻)',
      mistakes=['выбирают NaCl или кислоты'],
      solve=_solve_mixed, kes=K_OGE5,
      fidelity=fid(5, 'ОГЭ', trap='HNO₃ — только ковалентная, KNO₃ — ионная и ковалентная', scale=SC5, kes=['3.1']))(
    _mixed_gen('ch-oge-05-mixed', 'ОГЭ'))


# ================================================================= ОГЭ 6. Характеристика элементов (два утверждения)
K_OGE6 = ['2.2', '2.3']
OGE6_EL = [s for s in E if E[s]['Z'] <= 20 and E[s]['kind'] in ('m', 'n') and s != 'H']
STATE_TXT = {'г': 'газообразно', 'т': 'твёрдое', 'ж': 'жидкое'}
OX_CHAR = {'Li': 'осн', 'Na': 'осн', 'K': 'осн', 'Mg': 'осн', 'Ca': 'осн', 'Be': 'амф', 'Al': 'амф', 'B': 'кисл',
           'C': 'кисл', 'Si': 'кисл', 'N': 'кисл', 'P': 'кисл', 'S': 'кисл', 'Cl': 'кисл'}
CHAR_TXT = {'осн': 'основными', 'амф': 'амфотерными', 'кисл': 'кислотными'}


def stmt_text(tid, v):
    if tid == 'layers':
        return f'Атом элемента содержит {v} электронных слоя.'
    if tid == 'outer':
        return f'Внешний электронный слой атома содержит {v} {plural(v, "электрон", "электрона", "электронов")}.'
    if tid == 'lack':
        return f'Для завершения внешнего слоя атому недостаёт {v} {plural(v, "электрона", "электронов", "электронов")}.'
    if tid == 'metal':
        return 'Элемент относится к металлам.' if v else 'Элемент относится к неметаллам.'
    if tid == 'state':
        return ('Простое вещество, образованное элементом, при обычных условиях — '
                f'{"газ" if v == "г" else "твёрдое вещество"}.')
    if tid == 'hyd':
        return 'Элемент образует летучее соединение с водородом.'
    if tid == 'hydf':
        return f'Формула летучего водородного соединения элемента — {HYD_T[v]}.'
    if tid == 'hiox':
        return f'Высшая степень окисления элемента составляет {signed(v)}.'
    if tid == 'oxide':
        return f'Формула высшего оксида элемента — {OXIDE_T[v]}.'
    if tid == 'charge':
        return f'Ядро атома имеет заряд +{v}.'
    if tid == 'char':
        return f'Высший оксид элемента обладает {CHAR_TXT[v]} свойствами.'
    if tid == 'hival':
        return f'Высшая валентность элемента — {ROMAN[v]}.'
    raise KeyError(tid)


def stmt_true(tid, v, s):
    e = E[s]
    oc = outer_count(cfg_cells(s))
    if tid == 'layers':
        return e['period'] == v
    if tid == 'outer':
        return oc == v
    if tid == 'lack':
        return e['kind'] == 'n' and 8 - oc == v
    if tid == 'metal':
        return (e['kind'] == 'm') == bool(v)
    if tid == 'state':
        return e['state'] == v
    if tid == 'hyd':
        return e['kind'] == 'n' and e['group'] >= 4
    if tid == 'hydf':
        return e['kind'] == 'n' and e['group'] == v
    if tid in ('hiox', 'hival'):
        return s not in ('O', 'F') and ox_max(s) == v
    if tid == 'oxide':
        return s not in ('O', 'F') and ox_max(s) == v
    if tid == 'charge':
        return e['Z'] == v
    if tid == 'char':
        return OX_CHAR.get(s) == v
    raise KeyError(tid)


def r_stmt(tid, v, s):
    """Второй путь: истинность утверждения из Z (электронная конфигурация по правилу Клечковского)."""
    Z = z_of(s)
    per, out, met = r_period(Z), r_outer(Z), r_metal(Z)
    if tid == 'layers':
        return per == v
    if tid == 'outer':
        return out == v
    if tid == 'lack':
        return not met and 8 - out == v
    if tid == 'metal':
        return met == bool(v)
    if tid == 'state':
        return {'г': Z in (1, 2, 7, 8, 9, 10, 17, 18), 'т': Z not in (1, 2, 7, 8, 9, 10, 17, 18, 35)}[v]
    if tid == 'hyd':
        return not met and out >= 4
    if tid == 'hydf':
        return not met and out == v
    if tid in ('hiox', 'hival', 'oxide'):
        return r_higher_ox(Z) == v
    if tid == 'charge':
        return Z == v
    if tid == 'char':
        if not met:
            return v == 'кисл' and Z not in (8, 9)
        return v == ('амф' if out == per else 'осн')
    raise KeyError(tid)


def all_stmts(els):
    out = [('layers', k) for k in (2, 3, 4)] + [('outer', k) for k in range(1, 8)] + \
          [('lack', k) for k in (1, 2, 3, 4)] + [('metal', 1), ('metal', 0), ('state', 'г'), ('state', 'т'), ('hyd', 1)] + \
          [('hydf', g) for g in (4, 5, 6, 7)] + [('hiox', k) for k in range(1, 8)] + [('oxide', k) for k in range(1, 8)] + \
          [('charge', E[s]['Z']) for s in els] + [('char', c) for c in ('осн', 'амф', 'кисл')] + \
          [('hival', k) for k in range(1, 8)]
    return out


def _solve_pair(p):
    a, b = p['a'], p['b']
    res = []
    for i, (tid, v) in enumerate(p['st']):
        ta, tb = r_stmt(tid, v, a), r_stmt(tid, v, b)
        ok = (ta and tb) if p['mode'] == 'both' else (ta and not tb)
        if ok:
            res.append(str(i + 1))
    return res


def pair_card(pid, rng, mode):
    kind = rng.random()
    if kind < 0.5:
        g = rng.choice([1, 2, 3, 4, 5, 6, 7])
        cand = [s for s in OGE6_EL if E[s]['group'] == g]
    else:
        pr = rng.choice([2, 3])
        cand = [s for s in OGE6_EL if E[s]['period'] == pr]
    if len(cand) < 2:
        raise Retry
    a, b = rng.sample(cand, 2)
    sts = all_stmts([a, b])
    rng.shuffle(sts)
    good, near, far = [], [], []
    for tid, v in sts:
        ta, tb = stmt_true(tid, v, a), stmt_true(tid, v, b)
        ok = (ta and tb) if mode == 'both' else (ta and not tb)
        if ok:
            good.append((tid, v))
        elif ta or tb:
            near.append((tid, v))
        else:
            far.append((tid, v))
    # не больше одного утверждения одного типа среди верных и не повторять тип hiox/hival/oxide
    def distinct(xs, k):
        out, used = [], set()
        for tid, v in xs:
            key = 'ox' if tid in ('hiox', 'hival', 'oxide') else ('hyd' if tid in ('hyd', 'hydf') else tid)
            if key in used:
                continue
            used.add(key)
            out.append((tid, v))
            if len(out) == k:
                break
        return out, used
    g2, used = distinct(good, 2)
    if len(g2) < 2:
        raise Retry
    rest = [x for x in near if x not in g2]
    rest_far = [x for x in far]
    bad = []
    usedb = set(used)
    for tid, v in rest[:] + rest_far:
        key = 'ox' if tid in ('hiox', 'hival', 'oxide') else ('hyd' if tid in ('hyd', 'hydf') else tid)
        if key in usedb:
            continue
        if tid == 'charge' and rng.random() < 0.5:
            continue
        usedb.add(key)
        bad.append((tid, v))
        if len(bad) == 3:
            break
    if len(bad) < 3:
        raise Retry
    st = g2 + bad
    rng.shuffle(st)
    A, B = E[a], E[b]
    if mode == 'both':
        q = rng.choice([f'Какие два утверждения верны для характеристики как {A["gen"]}, так и {B["gen"]}?',
                        f'Из предложенного перечня выберите два утверждения, верные для характеристики как '
                        f'{A["gen"]}, так и {B["gen"]}.'])
    else:
        q = f'Какие два утверждения являются верными для характеристики {A["gen"]} и неверными для характеристики ' \
            f'{B["gen"]}?'
    fit = (lambda t, v: stmt_true(t, v, a) and stmt_true(t, v, b)) if mode == 'both' else \
        (lambda t, v: stmt_true(t, v, a) and not stmt_true(t, v, b))
    ans = sorted(str(i + 1) for i, (tid, v) in enumerate(st) if fit(tid, v))
    if len(ans) != 2:
        raise Retry
    e = (f'{A["nom"].capitalize()}: период {A["period"]}, группа {ROMAN[A["group"]]}A, внешних электронов '
         f'{outer_count(cfg_cells(a))}; {B["nom"]}: период {B["period"]}, группа {ROMAN[B["group"]]}A, внешних '
         f'электронов {outer_count(cfg_cells(b))}. Ответ: {"".join(ans)}.')
    return pcard(pid, q + ' Запишите номера выбранных ответов.', ans, e, k='many', o=opts([stmt_text(*x) for x in st]),
                 p={'a': a, 'b': b, 'mode': mode, 'st': [list(x) for x in st]})


FID6 = dict(style='КИМ ОГЭ 2027, задание 6: «Какие два утверждения верны для характеристики как …, так и …?», «… являются верными для … и неверными для …?», «Выберите два верных продолжения для следующего утверждения»; утверждения свои')


@proto('ch-oge-06-both', 'ОГЭ', 6, 'Утверждения, верные для обоих элементов',
       invariant='по положению двух элементов в ПСХЭ проверить каждое утверждение (строение атома, металл/неметалл, '
                 'водородное соединение, высший оксид, агрегатное состояние простого вещества) для обоих',
       varies='пара элементов Z ≤ 20 (одна группа или один период), набор утверждений',
       answer_rule='выбрать два утверждения, истинные для обоих элементов',
       mistakes=['проверяют только один элемент', 'для кислорода и фтора берут высшую степень окисления по группе'],
       solve=_solve_pair, kes=K_OGE6,
       fidelity=fid(6, 'ОГЭ', trap='у элементов одной группы одинаково число внешних электронов, но разное число слоёв',
                    scale='элементы 2–3 периодов, K, Ca; пять утверждений', kes=['2.2', '2.3'], **FID6))
def g_pair_both(rng):
    return pair_card('ch-oge-06-both', rng, 'both')


@proto('ch-oge-06-anotb', 'ОГЭ', 6, 'Утверждения, верные для одного элемента и неверные для другого',
       invariant='проверить утверждения для двух элементов, выбрать верные для первого и неверные для второго',
       varies='пара элементов, набор утверждений',
       answer_rule='выбрать два утверждения: для A — истина, для B — ложь',
       mistakes=['выбирают утверждения, верные для обоих', 'путают, для какого элемента утверждение должно быть '
                 'верным'],
       solve=_solve_pair, kes=K_OGE6,
       fidelity=fid(6, 'ОГЭ', trap='как в демоверсии 2027: натрий против хлора (три слоя у обоих)', scale='элементы '
                    '2–3 периодов, K, Ca; пять утверждений', kes=['2.2', '2.3'], **FID6))
def g_pair_anotb(rng):
    return pair_card('ch-oge-06-anotb', rng, 'anotb')


# ---- ряд «X → Y → Z»: верные продолжения
TREND = {
    'radius': ('радиус атомов', 'увеличивается', 'уменьшается'),
    'en': ('электроотрицательность', 'возрастает', 'уменьшается'),
    'metal': ('металлические свойства соответствующих простых веществ', 'усиливаются', 'ослабевают'),
    'outer': ('число электронов на внешнем электронном слое атомов', 'увеличивается', 'уменьшается'),
    'layers': ('число электронных слоёв в атомах', 'увеличивается', 'уменьшается'),
    'charge': ('заряд ядер атомов', 'увеличивается', 'уменьшается'),
    'hiox': ('высшая степень окисления', 'возрастает', 'уменьшается'),
    'acid': ('кислотный характер высших оксидов', 'усиливается', 'ослабевает'),
}


def trend_dir(key, seq):
    """+1 растёт, −1 убывает, 0 не меняется (по таблице: период/группа)."""
    per = [E[s]['period'] for s in seq]
    grp = [E[s]['group'] for s in seq]
    along_period = len(set(per)) == 1
    step = (grp[1] - grp[0]) if along_period else (per[1] - per[0])
    sgn = 1 if step > 0 else -1
    d = {'radius': (-1, 1), 'en': (1, -1), 'metal': (-1, 1), 'outer': (1, 0), 'layers': (0, 1), 'charge': (1, 1),
         'hiox': (1, 0), 'acid': (1, -1)}[key]
    return sgn * (d[0] if along_period else d[1])


def _solve_row(p):
    seq = p['seq']
    zs = [z_of(s) for s in seq]
    def val(key, Z):
        per, gr = r_period(Z), r_valence(Z)
        return {'radius': per * 10 - gr, 'en': -per * 10 + gr, 'metal': per * 10 - gr, 'outer': r_outer(Z),
                'layers': per, 'charge': Z, 'hiox': r_higher_ox(Z), 'acid': -per * 10 + gr}[key]
    res = []
    for i, (key, word) in enumerate(p['st']):
        vs = [val(key, Z) for Z in zs]
        if all(x == vs[0] for x in vs):
            d = 0
        elif all(vs[j] < vs[j + 1] for j in range(2)):
            d = 1
        elif all(vs[j] > vs[j + 1] for j in range(2)):
            d = -1
        else:
            d = None
        if d == {'up': 1, 'down': -1, 'same': 0}[word]:
            res.append(str(i + 1))
    return res


@proto('ch-oge-06-row', 'ОГЭ', 6, 'Верные продолжения утверждения о ряде элементов X → Y → Z',
       invariant='определить направление изменения свойств в ряду элементов одного периода или одной группы',
       varies='ряд из трёх элементов (период или группа, по возрастанию или убыванию заряда ядра), набор продолжений',
       answer_rule='период слева направо: радиус и металличность ↓, ЭО, внешние электроны, высшая степень окисления, '
                   'кислотность оксидов ↑, слоёв — без изменений; группа вниз: радиус, металличность, число слоёв ↑, '
                   'ЭО и кислотность оксидов ↓, внешние электроны — без изменений',
       mistakes=['не замечают, что ряд записан в обратном порядке', 'путают «не изменяется» и «увеличивается» для '
                 'числа слоёв и внешних электронов'],
       solve=_solve_row, kes=K_OGE6,
       fidelity=fid(6, 'ОГЭ', trap='ряд справа налево (Cl → S → P) меняет все направления', scale='элементы Z ≤ 20, '
                    'три элемента подряд', kes=['2.2', '2.3'], **FID6))
def g_row(rng):
    if rng.random() < 0.5:
        line = rng.choice([LINES_P[2][:], LINES_P[3][:]])
        i = rng.randrange(len(line) - 2)
        seq = line[i:i + 3]
    else:
        g = rng.choice([1, 2, 3, 4, 5, 6, 7])
        line = [s for s in LINES_G[g] if E[s]['Z'] <= 20]
        if len(line) < 3:
            raise Retry
        seq = line[:3]
    if rng.random() < 0.35:
        seq = seq[::-1]
    keys = list(TREND)
    if any(s in ('O', 'F') for s in seq):
        keys = [k for k in keys if k not in ('hiox', 'acid')]
    if any(E[s]['kind'] == 'm' for s in seq) and any(E[s]['kind'] == 'n' for s in seq):
        pass
    cands = []
    for k in keys:
        d = trend_dir(k, seq)
        for w in ('up', 'down', 'same'):
            if w == 'same' and k not in ('outer', 'layers', 'hiox'):
                continue
            truth = {'up': 1, 'down': -1, 'same': 0}[w] == d
            cands.append((k, w, truth))
    rng.shuffle(cands)
    good, bad, used = [], [], set()
    for k, w, t in cands:
        if k in used:
            continue
        if t and len(good) < 2:
            good.append((k, w)); used.add(k)
        elif not t and len(bad) < 3:
            bad.append((k, w)); used.add(k)
    if len(good) < 2 or len(bad) < 3:
        raise Retry
    st = good + bad
    rng.shuffle(st)
    def txt(k, w):
        noun, up, down = TREND[k]
        verb = {'up': up, 'down': down, 'same': 'не изменяется' if not noun.endswith('ва') else 'не изменяются'}[w]
        if k == 'metal' and w == 'same':
            verb = 'не изменяются'
        return f'{verb} {noun}'
    q = (f'Выберите два верных продолжения для следующего утверждения. В ряду химических элементов '
         f'{" → ".join(seq)} …')
    ans = sorted(str(i + 1) for i, x in enumerate(st) if x in good)
    e = (f'{"-".join(seq)}: ' + ('один период' if len({E[s]["period"] for s in seq}) == 1 else 'одна группа') +
         '; ' + '; '.join(f'{TREND[k][0]} — {({1: TREND[k][1], -1: TREND[k][2], 0: "не изменяется"})[trend_dir(k, seq)]}'
                          for k, _ in st) + f'. Ответ: {"".join(ans)}.')
    return pcard('ch-oge-06-row', q + ' Запишите номера выбранных ответов.', ans, e, k='many',
                 o=opts([txt(*x) for x in st]), p={'seq': seq, 'st': [list(x) for x in st]})


# ---- «Среди элементов X, Y, Z …»
def _solve_among(p):
    els = p['els']
    zs = {s: z_of(s) for s in els}
    per = {x: r_period(zs[x]) for x in els}
    gr = {x: r_valence(zs[x]) for x in els}
    rad = {x: per[x] * 10 - gr[x] for x in els}
    en = {x: -rad[x] for x in els}
    hi = {x: r_higher_ox(zs[x]) for x in els}

    def uniq(d, s, best):   # строгий единственный экстремум; ничья — неверно
        return d[s] == best(d.values()) and list(d.values()).count(d[s]) == 1
    res = []
    for i, (tid, s) in enumerate(p['st']):
        if tid == 'sameox':
            ok = len(set(hi.values())) == 1
        elif tid == 'onlyox':
            v = hi[s]
            ok = list(hi.values()).count(v) == 1
        else:
            ok = {'maxr': lambda: uniq(rad, s, max), 'minr': lambda: uniq(rad, s, min),
                  'maxen': lambda: uniq(en, s, max), 'minen': lambda: uniq(en, s, min),
                  'onlymetal': lambda: r_metal(zs[s]) and sum(r_metal(zs[x]) for x in els) == 1,
                  'onlynonmetal': lambda: not r_metal(zs[s]) and sum(not r_metal(zs[x]) for x in els) == 1,
                  'maxox': lambda: uniq(hi, s, max)}[tid]()
        if ok:
            res.append(str(i + 1))
    return res


AMONG_TXT = {'maxr': 'наибольший радиус имеют атомы {g}', 'minr': 'наименьший радиус имеют атомы {g}',
             'maxen': 'наибольшую электроотрицательность имеет {n}', 'minen': 'наименьшую электроотрицательность имеет {n}',
             'onlymetal': 'простое вещество-металл образует только {n}',
             'onlynonmetal': 'простое вещество-неметалл образует только {n}',
             'maxox': 'наибольшую высшую степень окисления имеет {n}',
             'onlyox': 'высшую степень окисления {v} имеет только {n}',
             'sameox': 'все три элемента имеют одинаковую высшую степень окисления'}


@proto('ch-oge-06-among', 'ОГЭ', 6, 'Сравнение трёх элементов: «среди элементов X, Y, Z …»',
       invariant='сравнить три элемента одного периода (группы) по радиусу, ЭО, металличности, высшей степени окисления',
       varies='три элемента, набор утверждений «наибольший/наименьший …», «только … является металлом»',
       answer_rule='применить закономерности периода/группы к каждому утверждению',
       mistakes=['путают наибольший и наименьший радиус', 'считают, что металлом может быть только один элемент ряда'],
       solve=_solve_among, kes=K_OGE6,
       fidelity=fid(6, 'ОГЭ', trap='в периоде наибольший радиус — у левого элемента', scale='элементы Z ≤ 20',
                    kes=['2.2', '2.3'], **FID6))
def g_among(rng):
    if rng.random() < 0.6:
        line = rng.choice([LINES_P[2][:6], LINES_P[3]])
        els = sorted(rng.sample(line, 3), key=lambda s: E[s]['Z'])
        along = 'p'
    else:
        g = rng.choice([1, 2, 4, 5, 6, 7])
        els = [s for s in LINES_G[g] if E[s]['Z'] <= 20][:3]
        if len(els) < 3:
            raise Retry
        along = 'g'
    per = lambda s: E[s]['period']
    grp = lambda s: E[s]['group']
    rad = {s: (-grp(s) if along == 'p' else per(s)) for s in els}
    en = {s: -rad[s] for s in els}
    mets = [s for s in els if E[s]['kind'] == 'm']
    truth = {}
    hi = {s: ox_max(s) for s in els}
    no_ox = any(x in ('O', 'F') for x in els)

    def uniq(d, s, best):
        return d[s] == best(d.values()) and list(d.values()).count(d[s]) == 1
    for s in els:
        truth[('maxr', s)] = uniq(rad, s, max)
        truth[('minr', s)] = uniq(rad, s, min)
        truth[('maxen', s)] = uniq(en, s, max)
        truth[('minen', s)] = uniq(en, s, min)
        truth[('onlymetal', s)] = E[s]['kind'] == 'm' and len(mets) == 1
        truth[('onlynonmetal', s)] = E[s]['kind'] == 'n' and len(els) - len(mets) == 1
        if not no_ox:
            if len(set(hi.values())) > 1:
                truth[('maxox', s)] = uniq(hi, s, max)
            truth[('onlyox', s)] = list(hi.values()).count(hi[s]) == 1
    if not no_ox:
        truth[('sameox', '*')] = len(set(hi.values())) == 1
    keys = list(truth)
    rng.shuffle(keys)
    good = [k for k in keys if truth[k]]
    bad = [k for k in keys if not truth[k]]
    g2, b3, used = [], [], set()
    for k in good:
        if k[0] not in used and len(g2) < 2:
            g2.append(k); used.add(k[0])
    for k in bad:
        if k[0] not in used and len(b3) < 3:
            b3.append(k); used.add(k[0])
    if len(g2) < 2 or len(b3) < 3:
        raise Retry
    st = g2 + b3
    rng.shuffle(st)
    texts = [AMONG_TXT[t] if s == '*' else AMONG_TXT[t].format(g=E[s]['gen'], n=E[s]['nom'], v=signed(ox_max(s)))
             for t, s in st]
    q = (f'Выберите два верных продолжения для следующего утверждения. Среди химических элементов '
         f'{", ".join(els)} …')
    ans = sorted(str(i + 1) for i, k in enumerate(st) if truth[k])
    e = ('; '.join(f'{s}: {E[s]["period"]}-й период, {ROMAN[E[s]["group"]]}A' for s in els) +
         '. В периоде слева направо радиус уменьшается, ЭО растёт; в группе сверху вниз — наоборот. Ответ: ' +
         ''.join(ans) + '.')
    return pcard('ch-oge-06-among', q + ' Запишите номера выбранных ответов.', ans, e, k='many', o=opts(texts),
                 p={'els': els, 'st': [list(k) for k in st]})
