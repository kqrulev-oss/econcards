"""Прототипы ЕГЭ профиль (КИМ 2027), задания 6–10.

6 — случайная величина (новое в 2027): распределение, матожидание, дисперсия,
    стандартное отклонение; биномиальное, геометрическое, равномерное,
    показательное и нормальное распределения.
7 — простейшие уравнения.
8 — вычисления и преобразования.
9 — производная и первообразная (в КИМ по графику) и наибольшее/наименьшее
    значение функции (по спецификации 2027 входит в требования задания 9).
10 — задачи с прикладным содержанием (формула из физики, экономики).

Тексты условий свои; формулировки инструкций — в духе КИМ. Формулы в условиях
помечены ⟦ ⟧ (степени ^{…} показываются надстрочно, см. lib.js).
"""
import math

from mathlib import (F, R, X, SUB, finite, ftxt, lin, nice, num, par, pcard, pick, plural, poly, proto, same, signed,
                     sp, svg_plot, tnum, _svg, BLUE, RED, INK, GRID)

# ================================================================ помощники


def fm(s):
    """Формула в условии: ⟦…⟧."""
    return f'⟦{s}⟧'


SUPD = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')


def root(n, s):
    """Корень n-й степени: √, ∛, ∜, ⁵√ …"""
    return {2: '√', 3: '∛', 4: '∜'}.get(n, str(n).translate(SUPD) + '√') + s


def logb(b):
    """log с основанием: log₃, log₀,₆."""
    return 'log' + (str(b) if not isinstance(b, str) else b).translate(SUB)


def lin_t(a, b, var='x'):
    """ax + b или b − x (если a < 0, пишем b впереди, как в КИМ: 15 − x)."""
    a, b = F(a), F(b)
    if a < 0 and b > 0:
        k = '' if a == -1 else ftxt(-a)
        return f'{ftxt(b)} − {k}{var}'
    return lin(a, b, var)


def ok_lin(a, b):
    """Естественная запись линейного выражения: при отрицательном k свободный член положителен (15 − x)."""
    return not (a < 0 and b <= 0)


def plin(a, b, var='x'):
    """(ax + b) в скобках, если это не просто x."""
    s = lin_t(a, b, var)
    return s if s == var else f'({s})'


def fr(x):
    """Дробь в условии: 1/81, −3/4, 2,5."""
    x = F(x)
    if finite(x):
        return tnum(x)
    return f'{"−" if x < 0 else ""}{abs(x.numerator)}/{x.denominator}'


def solve1(lhs, rhs, var=X, pick_=None, cond=None):
    """Корни уравнения по sympy (вещественные, при условии cond)."""
    sol = sp.solve(sp.Eq(lhs, rhs), var)
    sol = [s for s in sol if s.is_real]
    if cond:
        sol = [s for s in sol if cond(s)]
    return sol


def one_root(lhs, rhs, ans, cond=None):
    def chk():
        sol = solve1(lhs, rhs, cond=cond)
        return len(sol) == 1 and same(ans, sol[0])
    return chk


def exp_check(k1, c1, a, k2, c2, b, ans):
    """a^{k1 x + c1} = b^{k2 x + c2}: логарифмируем — получается линейное уравнение
    (k1 x + c1)·ln a − (k2 x + c2)·ln b = 0; решаем его в числах с плавающей точкой
    и дополнительно проверяем точной подстановкой ответа."""
    def chk():
        g = lambda x: (k1 * x + c1) * math.log(float(a)) - (k2 * x + c2) * math.log(float(b))
        x0 = -g(0) / (g(1) - g(0))
        xa = F(ans.replace(',', '.'))
        exact = sp.simplify(R(F(a)) ** R(k1 * xa + c1) - R(F(b)) ** R(k2 * xa + c2)) == 0
        return abs(x0 - float(xa)) < 1e-9 and exact
    return chk


EQ_Q = ['Решите уравнение {} и запишите его корень.',
        'Уравнение {} имеет единственный корень. Найдите его.',
        'Найдите значение x, при котором выполняется равенство {}.',
        'При каком значении x верно равенство {}?']


def eq_q(r, f):
    return r.choice(EQ_Q).format(fm(f))


KIM7 = dict(level='Б', points=1, minutes=2, kt=['КТ 3'], answer='число',
            style='инструкция «найдите корень / решите уравнение», ответ — целое число или конечная десятичная дробь')
KIM8 = dict(level='Б', points=1, minutes=3, kt=['КТ 2'], answer='число',
            style='«Найдите значение выражения …» / «Вычислите …», ответ — целое число или конечная десятичная дробь')
KIM9 = dict(level='Б', points=1, minutes=5, kt=['КТ 4'], answer='число')
KIM10 = dict(level='П', points=1, minutes=5, kt=['КТ 6'], answer='число',
             style='формула из физики/экономики дана в условии; «Ответ дайте в …» с единицами, как в КИМ')
KIM6 = dict(level='П', points=1, minutes=8, kes=['6.2'], kt=['КТ 8'], answer='число')


def kim(base, **kw):
    d = dict(base)
    d.update(kw)
    return d


# ================================================================ 7. Простейшие уравнения


def _pow_rhs(a, m):
    """a^m как число в условии: 81 или 1/81 (a может быть дробью 1/7)."""
    v = F(a) ** m
    if v.denominator != 1:
        return f'{v.numerator}/{v.denominator}'
    return tnum(v)


@proto('ep07-exp-base', 'ege-prof', 7, 'Показательное уравнение: правая часть — степень того же основания',
       invariant='a^{kx+b} = c, где c — степень числа a (в том числе с отрицательным показателем, записанная дробью 1/…); приравниваем показатели.',
       varies='основание 2–10, вид показателя (x − b, b − x, kx + b), знак показателя в правой части, формулировка инструкции',
       answer_rule='kx + b = m, где c = a^m; x = (m − b)/k',
       fipi=r'корень уравнения (\d{1,2}) (x [+−–] \d+|\d+ − x|− \d+ − x|\d x [+−] \d+) ​? ?= (1 )?\d+ ​? ?\.?$',
       mistakes=['1/81 принимают за 3^4 вместо 3^(−4)', 'ошибка в знаке при показателе b − x', 'делят c на a вместо представления степенью'],
       kim=kim(KIM7, kes=['2.4']))
def gen_ep07_exp_base(r):
    a = r.choice([2, 2, 3, 3, 4, 5, 6, 7, 8, 9, 10])
    ms = [m for m in range(-6, 7) if m and a ** abs(m) <= 1024]
    m = r.choice(ms)
    form = r.choice(['x-b', 'x+b', 'b-x', 'b-x', '-b-x', 'kx+b'])
    b = r.randint(1, 16)
    if form == 'x-b':
        k, c = 1, -b
    elif form == 'x+b':
        k, c = 1, b
    elif form == 'b-x':
        k, c = -1, b
    elif form == '-b-x':
        k, c = -1, -b
    else:
        k, c = r.choice([2, 3, -2]), r.randint(-9, 9)
    x = F(m - c, k)
    if not nice(x, 1) or x == 0:
        return None
    e = lin_t(k, c)
    f = f'{a}^{{{e}}} = {_pow_rhs(a, m)}'
    q = eq_q(r, f)
    ex = f'{_pow_rhs(a, m)} = {a}^{{{tnum(m)}}}, значит {e} = {tnum(m)}, x = {tnum(x)}.'
    return pcard(q, num(x), ex), exp_check(k, c, a, 0, 1, F(a) ** m, num(x))


@proto('ep07-exp-recip', 'ege-prof', 7, 'Показательное уравнение с основанием 1/a',
       invariant='(1/a)^{kx+b} = c, где c — степень a; переписываем (1/a)^t = a^{−t} и приравниваем показатели.',
       varies='основание 1/2 … 1/9, вид показателя, правая часть — целое или дробь 1/…',
       answer_rule='−(kx + b) = m, где c = a^m',
       fipi=r'корень уравнения (\( 1 \d \)|1 [2-9] (\d+ − x|x [+−] \d+)) ',
       mistakes=['забывают сменить знак показателя при переходе к основанию a', 'путают 1/a^m и a^m'],
       kim=kim(KIM7, kes=['2.4']))
def gen_ep07_exp_recip(r):
    a = r.choice([2, 3, 4, 5, 6, 7, 9])
    m = r.choice([m for m in range(-5, 6) if m and a ** abs(m) <= 1024])
    k = r.choice([1, 1, 1, -1, 2])
    c = r.randint(-12, 12)
    # (1/a)^{kx+c} = a^m  ⇔  −(kx + c) = m
    x = F(-m - c, k)
    if not nice(x, 1) or c == 0 or not ok_lin(k, c):
        return None
    e = lin_t(k, c)
    f = f'(1/{a})^{{{e}}} = {_pow_rhs(a, m)}'
    q = eq_q(r, f)
    ex = f'(1/{a})^{{{e}}} = {a}^{{−({e})}}, {_pow_rhs(a, m)} = {a}^{{{tnum(m)}}}; −({e}) = {tnum(m)}, x = {tnum(x)}.'
    return pcard(q, num(x), ex), exp_check(k, c, F(1, a), 0, 1, F(a) ** m, num(x))


@proto('ep07-exp-two', 'ege-prof', 7, 'Показательное уравнение: переменная в обеих частях, основания — степени одного числа',
       invariant='a^{p(x)} = b^{q(x)}, где a и b — степени одного числа (например, 3 и 9, 1/6 и 6); приводим к одному основанию и приравниваем показатели.',
       varies='общее основание, степени, линейные показатели в обеих частях',
       answer_rule='s·p(x) = t·q(x), где a = d^s, b = d^t — линейное уравнение',
       fipi=r'корень уравнения (\( 1 \d \) x [+−] \d+ = \d+ x|\d+ x [+−] \d+ = \d+ \d x)',
       mistakes=['приравнивают показатели, не приведя основания к одному', 'не умножают весь показатель на степень основания'],
       kim=kim(KIM7, kes=['2.4']))
def gen_ep07_exp_two(r):
    d = r.choice([2, 3, 5, 6, 7])
    s, t = r.choice([(1, 2), (2, 1), (1, 3), (3, 1), (2, 3), (-1, 1), (1, -1), (-1, 2), (2, -1), (3, 2)])
    if d ** max(abs(s), abs(t)) > 125:
        return None
    base = lambda u: f'(1/{d ** -u})' if u < 0 else str(d ** u)
    # s(k1 x + c1) = t(k2 x + c2)
    k1, k2 = r.choice([1, 1, 2, -1]), r.choice([1, 1, 2, 3])
    c1, c2 = r.randint(-9, 9), r.randint(-9, 9)
    den = s * k1 - t * k2
    if den == 0:
        return None
    x = F(t * c2 - s * c1, den)
    if not nice(x, 1) or (c1 == 0 and c2 == 0) or not ok_lin(k1, c1) or not ok_lin(k2, c2):
        return None
    e1, e2 = lin_t(k1, c1), lin_t(k2, c2)
    f = f'{base(s)}^{{{e1}}} = {base(t)}^{{{e2}}}'
    if r.random() < 0.5:
        f = f'{base(t)}^{{{e2}}} = {base(s)}^{{{e1}}}'
    q = eq_q(r, f)
    mul = lambda u, e: f'({e})' if u == 1 else f'−({e})' if u == -1 else f'{tnum(u)}({e})'
    ex = f'Обе части — степени числа {d}: {d}^{{{mul(s, e1)}}} = {d}^{{{mul(t, e2)}}}; {mul(s, e1)} = {mul(t, e2)}, x = {tnum(x)}.'
    return pcard(q, num(x), ex), exp_check(k1, c1, F(d) ** s, k2, c2, F(d) ** t, num(x))


@proto('ep07-log-log', 'ege-prof', 7, 'Логарифмическое уравнение log_a f(x) = log_a c',
       invariant='log_a(kx + b) = log_a c с одинаковыми основаниями; аргументы равны (c > 0, поэтому ОДЗ выполняется).',
       varies='основание, линейный аргумент (в том числе b − x), число c',
       answer_rule='kx + b = c',
       fipi=r'корень уравнения log \d+ \( [^)]*\) = log \d+ \d+',
       mistakes=['ошибка знака в аргументе вида b − x', 'приравнивают аргумент основанию'],
       kim=kim(KIM7, kes=['2.4']))
def gen_ep07_log_log(r):
    a = r.choice([2, 3, 4, 5, 6, 7, 8, 9, 11, 13])
    k = r.choice([1, 1, -1, -1, 2, 3, 5])
    b = r.randint(-30, 30)
    c = r.randint(2, 40)
    x = F(c - b, k)
    if not nice(x, 1) or b == 0 or c == a or not ok_lin(k, b):
        return None
    arg = lin_t(k, b)
    f = f'{logb(a)}({arg}) = {logb(a)}{c}'
    q = eq_q(r, f)
    ex = f'Основания равны, значит {arg} = {c} (при этом аргумент положителен), x = {tnum(x)}.'
    return pcard(q, num(x), ex), one_root(sp.log(k * X + b, a), sp.log(c, a), num(x), cond=lambda s: k * s + b > 0)


@proto('ep07-log-num', 'ege-prof', 7, 'Логарифмическое уравнение log_a f(x) = n',
       invariant='log_a(kx + b) = n; по определению логарифма kx + b = a^n.',
       varies='основание (в том числе дробное), показатель n (в том числе 0 и отрицательный), линейный аргумент',
       answer_rule='x = (a^n − b)/k',
       fipi=r'корень уравнения log \d+ \( [^)]*\) = \d+ ?\.?$',
       mistakes=['пишут kx + b = n·a вместо a^n', 'при n < 0 получают целое a^|n|'],
       kim=kim(KIM7, kes=['2.4']))
def gen_ep07_log_num(r):
    a = r.choice([2, 2, 3, 3, 4, 5, 6, 7, 8, 9, 10])
    n = r.choice([1, 2, 2, 3, 3, 4, -1, -2, 0])
    v = F(a) ** n
    if v > 1000:
        return None
    k = r.choice([1, 1, -1, 2, 3, 4, 5])
    b = r.randint(-40, 40)
    x = F(v - b, k)
    if not nice(x, 2) or b == 0 or not ok_lin(k, b) or abs(x) > 200:
        return None
    arg = lin_t(k, b)
    f = f'{logb(a)}({arg}) = {tnum(n)}'
    q = eq_q(r, f)
    ex = f'По определению логарифма {arg} = {a}^{{{tnum(n)}}} = {fr(v)}, x = {tnum(x)}.'
    return pcard(q, num(x), ex), one_root(sp.log(k * X + b, a), sp.Integer(n), num(x), cond=lambda s: k * s + b > 0)


@proto('ep07-log-base', 'ege-prof', 7, 'Логарифмическое уравнение с переменной в основании',
       invariant='log_{x + b} c = 2 (или 3); основание (x + b)^n = c, отбрасываем основание ≤ 0 и равное 1.',
       varies='сдвиг b, число c — точный квадрат или куб, показатель 2 или 3',
       answer_rule='x + b = ⁿ√c (для n = 2 берём положительный корень)',
       fipi=r'log x [+−] \d+ \d+ = \d',
       mistakes=['берут отрицательный корень для основания', 'забывают условие основание > 0'],
       kim=kim(KIM7, kes=['2.4']))
def gen_ep07_log_base(r):
    n = r.choice([2, 2, 2, 3])
    base = r.randint(2, 12 if n == 2 else 5)
    c = base ** n
    b = r.choice([v for v in range(-15, 16) if v])
    x = base - b
    sb = ('ₓ₊' if b > 0 else 'ₓ₋') + str(abs(b)).translate(SUB)
    f = f'log{sb} {c} = {n}'
    q = eq_q(r, f)
    xb = f'x {"+" if b > 0 else "−"} {abs(b)}'
    ex = f'({xb})^{{{n}}} = {c}, основание положительно и не равно 1: {xb} = {base}, x = {tnum(x)}.'

    def chk():
        y = sp.Symbol('y', real=True)
        sol = [s for s in sp.solve(sp.Eq(y ** n, c), y) if s.is_real and s > 0 and s != 1]
        return len(sol) == 1 and same(num(x), sol[0] - b)
    return pcard(q, num(x), ex), chk


@proto('ep07-sqrt', 'ege-prof', 7, 'Иррациональное уравнение √(kx + b) = c',
       invariant='√(kx + b) = c, c > 0; возводим обе части в квадрат.',
       varies='коэффициенты k (в том числе отрицательные: b − kx), b и число c',
       answer_rule='kx + b = c², x = (c² − b)/k',
       fipi=r'корень уравнения √\( [^)]*\) = \d+',
       mistakes=['не возводят c в квадрат', 'ошибка знака при kx с минусом'],
       kim=kim(KIM7, kes=['2.2']))
def gen_ep07_sqrt(r):
    c = r.randint(1, 12)
    k = r.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, -2, -3, -4, -5, -7, -9])
    b = r.randint(-60, 120)
    x = F(c * c - b, k)
    if not nice(x, 1) or b == 0 or not ok_lin(k, b):
        return None
    arg = lin_t(k, b)
    f = f'√({arg}) = {c}'
    q = eq_q(r, f)
    ex = f'Возводим в квадрат: {arg} = {c * c}, x = {tnum(x)}.'
    return pcard(q, num(x), ex), one_root(sp.sqrt(k * X + b), sp.Integer(c), num(x))


@proto('ep07-cbrt', 'ege-prof', 7, 'Уравнение с кубическим корнем ∛(kx + b) = c',
       invariant='∛(kx + b) = c; возводим в куб (c может быть отрицательным).',
       varies='k, b, c (в том числе отрицательное)',
       answer_rule='kx + b = c³',
       fipi=r'корень уравнения x [+−] \d+ 3 = −? ?\d+ ?\.?$',
       mistakes=['возводят в квадрат вместо куба', 'считают, что при c < 0 корней нет'],
       kim=kim(KIM7, kes=['2.2']))
def gen_ep07_cbrt(r):
    c = r.choice([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6])
    k = r.choice([1, 1, 1, 2, 3, -1, 4, 5])
    b = r.randint(-30, 30)
    x = F(c ** 3 - b, k)
    if not nice(x, 1) or b == 0 or not ok_lin(k, b):
        return None
    arg = lin_t(k, b)
    f = f'∛({arg}) = {tnum(c)}'
    q = eq_q(r, f)
    ex = f'Возводим в куб: {arg} = {tnum(c ** 3)}, x = {tnum(x)}.'
    # проверка подстановкой: вещественный кубический корень; функция монотонна — корень единственный
    return pcard(q, num(x), ex), lambda: sp.real_root(k * R(x) + b, 3) == c


@proto('ep07-cube', 'ege-prof', 7, 'Уравнение (x + b)³ = c',
       invariant='(kx + b)³ = c, c — точный куб (может быть отрицательным); извлекаем кубический корень.',
       varies='b, c, коэффициент k',
       answer_rule='kx + b = ∛c',
       fipi=r'корень уравнения \( x [+−] \d+ \) 3 = ',
       mistakes=['при c < 0 считают, что корней нет', 'делят c на 3 вместо извлечения корня'],
       kim=kim(KIM7, kes=['2.1']))
def gen_ep07_cube(r):
    t = r.choice([-6, -5, -4, -3, -2, 2, 3, 4, 5, 6, 7])
    k = r.choice([1, 1, 1, 2, 3])
    b = r.choice([v for v in range(-12, 13) if v])
    x = F(t - b, k)
    if not nice(x, 1):
        return None
    f = f'({lin_t(k, b)})³ = {tnum(t ** 3)}'
    q = eq_q(r, f)
    ex = f'{tnum(t ** 3)} = {par(t)}³, значит {lin_t(k, b)} = {tnum(t)}, x = {tnum(x)}.'
    return pcard(q, num(x), ex), one_root((k * X + b) ** 3, sp.Integer(t ** 3), num(x))


@proto('ep07-recip', 'ege-prof', 7, 'Дробно-рациональное уравнение m/(kx + b) = c',
       invariant='m/(kx + b) = c, знаменатель не равен нулю; kx + b = m/c.',
       varies='числитель m, линейный знаменатель, правая часть c (в том числе дробная или отрицательная)',
       answer_rule='x = (m/c − b)/k',
       fipi=r'корень уравнения 1 \d x [+−] \d+ = −? ?\d+ ?\.?$',
       mistakes=['умножают c на m вместо деления', 'переносят b без смены знака'],
       kim=kim(KIM7, kes=['2.1']))
def gen_ep07_recip(r):
    m = r.choice([1, 1, 1, 2, 3, 4, 5, 6, 8, 10, 12])
    c = F(r.choice([1, 2, 3, 4, 5, 6, 8, 10, -2, -4, -5]), r.choice([1, 1, 1, 2, 5]))
    k = r.choice([1, 2, 3, 4, 5, -1, -2])
    b = r.randint(-12, 12)
    x = (F(m) / c - b) / k
    if not nice(x, 2) or b == 0 or c == 0 or not ok_lin(k, b):
        return None
    f = f'{m}/({lin_t(k, b)}) = {tnum(c)}'
    q = eq_q(r, f)
    ex = f'{lin_t(k, b)} = {m} : {par(c)} = {tnum(F(m) / c)}, x = {tnum(x)}.'
    return pcard(q, num(x), ex), one_root(sp.Integer(m) / (k * X + b), R(c), num(x))


@proto('ep07-quad', 'ege-prof', 7, 'Квадратное уравнение: меньший или больший корень',
       invariant='ax² + bx + c = 0 (или в виде x² = px + q) с двумя корнями; в ответ — меньший или больший.',
       varies='корни (целые или десятичные), форма записи, какой корень записать',
       answer_rule='корни по формуле или теореме Виета, выбрать нужный',
       fipi=r'более одного корня',
       mistakes=['записывают не тот корень', 'ошибка в дискриминанте при переносе членов'],
       kim=kim(KIM7, kes=['2.1'], style='«Если уравнение имеет более одного корня, в ответе запишите меньший (больший) из них» — как в КИМ'))
def gen_ep07_quad(r):
    x1 = F(r.randint(-12, 12), r.choice([1, 1, 1, 2]))
    x2 = F(r.randint(-12, 12))
    a = r.choice([1, 1, 1, 2, -1])
    if x1 == x2:
        return None
    b, c = -a * (x1 + x2), a * x1 * x2
    if x1.denominator == 2:
        a, b, c = 2 * a, 2 * b, 2 * c
    if b.denominator != 1 or c.denominator != 1 or b == 0 and c == 0:
        return None
    small = r.random() < 0.5
    ans = min(x1, x2) if small else max(x1, x2)
    form = r.choice(['std', 'move'])
    if form == 'std' or b == 0:
        f = f'{poly([a, b, c])} = 0'
    else:
        f = f'{poly([a, 0, c])} = {poly([-b, 0])}'
    word = 'меньший' if small else 'больший'
    q = pick(r, f'Найдите {word} корень уравнения {fm(f)}.',
             f'Решите уравнение {fm(f)}. В ответ запишите {word} из его корней.',
             f'Уравнение {fm(f)} имеет два корня. Укажите {word} из них.')
    ex = f'Корни {tnum(min(x1, x2))} и {tnum(max(x1, x2))}; {word} — {tnum(ans)}.'

    def chk():
        sol = sorted(solve1(a * X ** 2 + b * X + c, 0))
        return len(sol) == 2 and same(num(ans), sol[0] if small else sol[1])
    return pcard(q, num(ans), ex), chk


@proto('ep07-sqrt-x', 'ege-prof', 7, 'Иррациональное уравнение √(px + q) = x (посторонний корень)',
       invariant='√(px + q) = x: после возведения в квадрат получаем квадратное уравнение, отрицательный корень посторонний.',
       varies='корни получающегося квадратного уравнения, вид правой части (x или x + d)',
       answer_rule='x² − px − q = 0, берём корень с x ≥ 0 (правая часть неотрицательна)',
       fipi=r'√\( [^)]*\) = x',
       mistakes=['записывают оба корня / посторонний отрицательный', 'забывают условие неотрицательности правой части'],
       kim=kim(KIM7, kes=['2.2']))
def gen_ep07_sqrt_x(r):
    good = r.randint(1, 12)
    bad = -r.randint(1, 12)
    d = r.choice([0, 0, 0, 1, 2, -1])
    # √(A x + B) = x + d, где (x + d)² = A x + B при x = good и x = bad;
    # у bad правая часть отрицательна
    if good + d <= 0 or bad + d >= 0:
        return None
    # (x + d)² − (A x + B) = (x − good)(x − bad) → A = good + bad + 2d, B = d² − good·bad
    A, B = good + bad + 2 * d, d * d - good * bad
    if A == 0:
        return None
    rhs = 'x' if d == 0 else lin(1, d)
    f = f'√({lin_t(A, B)}) = {rhs}'
    q = pick(r, f'Решите уравнение {fm(f)}. В ответ запишите меньший корень, если их больше одного.',
             f'Найдите все корни уравнения {fm(f)}. Если их несколько, укажите в ответе меньший.',
             f'Решите уравнение {fm(f)}. Запишите в ответ его корень (при нескольких корнях — меньший из них).')
    ex = f'Возводим в квадрат при условии {rhs} ≥ 0: получаем корни {tnum(good)} и {tnum(bad)}; x = {tnum(bad)} посторонний. Ответ: {good}.'
    return pcard(q, num(good), ex), one_root(sp.sqrt(A * X + B), X + d, num(good))


@proto('ep07-trig', 'ege-prof', 7, 'Тригонометрическое уравнение: наибольший отрицательный / наименьший положительный корень',
       invariant='sin или cos от π(x + b)/k равен табличному значению; записываем серии и отбираем нужный корень.',
       varies='функция, табличное значение, сдвиг b, делитель k, какой корень ищем',
       answer_rule='π(x + b)/k = ±arccos(v) + 2πn (или две серии для синуса), перебор n',
       fipi=r'(наибольший отрицательный|наименьший положительный) корень',
       mistakes=['теряют одну из серий', 'выбирают корень с неверным знаком'],
       kim=kim(KIM7, kes=['2.3'], style='как в КИМ прошлых лет: «В ответе напишите наибольший отрицательный корень»'))
def gen_ep07_trig(r):
    fn = r.choice(['cos', 'sin'])
    val = r.choice(['1/2', '−1/2', '√2/2', '√3/2', '0', '1', '−1'])
    k = r.choice([3, 4, 6, 8, 12])
    b = r.randint(-9, 9)
    want = r.choice(['neg', 'pos'])
    v = {'1/2': sp.Rational(1, 2), '−1/2': sp.Rational(-1, 2), '√2/2': sp.sqrt(2) / 2, '√3/2': sp.sqrt(3) / 2,
         '0': 0, '1': 1, '−1': -1}[val]
    # все корни на [−60; 60]: t = π(x + b)/k; углы t в [0; 2π) с f(t) = v
    fv = float(v)
    g = math.cos if fn == 'cos' else math.sin
    base = [F(j, 12) for j in range(24) if abs(g(math.pi * j / 12) - fv) < 1e-9]
    roots = sorted({F(k) * (t0 + 2 * n) - b for t0 in base for n in range(-40, 41)})
    cand = [x for x in roots if (x < 0 if want == 'neg' else x > 0)]
    ans = max(cand) if want == 'neg' else min(cand)
    if not nice(ans, 2):
        return None
    arg = f'π({lin(1, b)})/{k}' if b else f'πx/{k}'
    f = f'{fn}({arg}) = {val}'
    word = 'наибольший отрицательный' if want == 'neg' else 'наименьший положительный'
    q = f'Решите уравнение {fm(f)}. В ответе напишите {word} корень.'
    ex = f'Выписываем серии для {arg} и перебираем целые n: {word} корень равен {tnum(ans)}.'

    def chk():
        # численно: ищем корни на сетке шагом 1/24 около ответа и проверяем, что ближе к нулю нет
        f_ = (lambda x: math.cos(math.pi * (x + b) / k)) if fn == 'cos' else (lambda x: math.sin(math.pi * (x + b) / k))
        vv = float(v)
        a0 = float(ans)
        if abs(f_(a0) - vv) > 1e-9:
            return False
        step = F(1, 24)
        x = F(0)
        while abs(x) < abs(ans):
            if abs(f_(float(x)) - vv) < 1e-9 and x != 0:
                return False
            x = x - step if want == 'neg' else x + step
        return True
    return pcard(q, num(ans), ex), chk


# ================================================================ 8. Вычисления и преобразования

# «Найдите значение выражения …» дословно совпадает с банком ФИПИ, а короткие условия
# сверяются буквально — поэтому инструкции чуть длиннее и своими словами.
VAL_Q = ['Найдите значение числового выражения {}.', 'Вычислите значение числового выражения {}.',
         'Найдите, чему равно выражение {}.', 'Определите значение числового выражения {}.']


def val_q(r, f):
    return r.choice(VAL_Q).format(fm(f))


def spv(x):
    """Строка ответа → sympy.Rational (для сравнения с sympy-выражением)."""
    return R(F(x.replace(',', '.')))


def expr_check(expr, ans):
    """Независимый пересчёт: sympy упрощает выражение и сравнивает с ответом."""
    return lambda: sp.simplify(sp.nsimplify(expr) - spv(ans)) == 0 if False else sp.simplify(expr - spv(ans)) == 0


ROOT_IDX = [(m, n, k) for m in (2, 3, 4, 5, 6, 8, 10, 12) for n in (3, 4, 5, 6, 8, 10, 12, 15, 20, 24) for k in (4, 6, 8, 10, 12, 15, 20, 24, 30, 40, 60)
            if m < n and k not in (m, n) and F(1, m) + F(1, n) - F(1, k) in (F(1, 2), F(1, 3), F(1, 1))]


@proto('ep08-root-idx', 'ege-prof', 8, 'Корни разных степеней из одного числа',
       invariant='произведение и частное корней разной степени из одного числа a: складываем и вычитаем показатели 1/m + 1/n − 1/k.',
       varies='степени корней, число a (точный квадрат, куб или любое), запись корнями или дробными показателями',
       answer_rule='a^{1/m + 1/n − 1/k}; показатель равен 1/2, 1/3 или 1',
       fipi=r'значение выражения (\d+) (\d+) ⋅ \1 \d+ \1 \d+ \.',
       mistakes=['перемножают показатели вместо сложения', 'складывают корни как числа'],
       kim=kim(KIM8, kes=['1.3', '1.4']))
def gen_ep08_root_idx(r):
    m, n, k = r.choice(ROOT_IDX)
    e = F(1, m) + F(1, n) - F(1, k)
    t = r.randint(2, 15 if e == F(1, 2) else 6 if e == F(1, 3) else 20)
    a = t ** e.denominator if e != 1 else t
    if a > 999:
        return None
    if r.random() < 0.7:
        f = f'({root(m, str(a))} · {root(n, str(a))}) / {root(k, str(a))}'
    else:
        f = f'{a}^{{1/{m}}} · {a}^{{1/{n}}} : {a}^{{1/{k}}}'
    q = val_q(r, f)
    ex = f'{a}^{{1/{m} + 1/{n} − 1/{k}}} = {a}^{{{e.numerator}/{e.denominator}}} = {t}.' if e != 1 else f'{a}^{{1/{m} + 1/{n} − 1/{k}}} = {a}^{{1}} = {a}.'
    ans = t if e != 1 else a
    expr = sp.root(a, m) * sp.root(a, n) / sp.root(a, k)
    return pcard(q, num(ans), ex), expr_check(expr, num(ans))


def _npow(x, n):
    """Является ли x точной n-й степенью натурального числа."""
    t = round(x ** (1 / n))
    return any((t + d) ** n == x for d in (-1, 0, 1))


@proto('ep08-root-same', 'ege-prof', 8, 'Произведение и частное корней одной степени',
       invariant='ⁿ√A · ⁿ√B / ⁿ√C = ⁿ√(AB/C); числа подобраны так, что под общим корнем получается точная степень.',
       varies='степень корня (2, 3, 4), числа A, B, C',
       answer_rule='ⁿ√(AB/C)',
       fipi=r'значение выражения (\d+) (\d) ⋅ (\d+) \2 (\d+) \2 \.',
       mistakes=['извлекают корни по отдельности приближённо', 'перемножают подкоренные числа неверно'],
       kim=kim(KIM8, kes=['1.3']))
def gen_ep08_root_same(r):
    n = r.choice([2, 3, 3, 4])
    t = r.randint(2, 12 if n == 2 else 6 if n == 3 else 4)
    P = t ** n
    # A·B = P·C
    C = r.choice([2, 3, 5, 6, 7, 10, 12, 15, 20, 24, 40, 80])
    tot = P * C
    divs = [d for d in range(2, int(tot ** 0.5) + 1) if tot % d == 0]
    if not divs:
        return None
    A = r.choice(divs)
    B = tot // A
    if A == B or any(_npow(v, n) for v in (A, B, C)) or max(A, B, C) > 2000:
        return None
    op = r.random() < 0.7
    f = f'{root(n, str(A))} · {root(n, str(B))} / {root(n, str(C))}' if op else f'{root(n, str(A))} · {root(n, str(B))} : {root(n, str(C))}'
    q = val_q(r, f)
    ex = f'{root(n, f"({A}·{B}/{C})")} = {root(n, str(P))} = {t}.'
    expr = sp.root(A, n) * sp.root(B, n) / sp.root(C, n)
    return pcard(q, num(t), ex), expr_check(expr, num(t))


@proto('ep08-root-square', 'ege-prof', 8, 'Квадрат (куб) произведения числа на корень',
       invariant='(k·ⁿ√m)ⁿ / d = kⁿ·m / d: возводим в степень и множитель, и корень.',
       varies='множитель k, подкоренное число m, степень (2 или 3), делитель d',
       answer_rule='kⁿ·m / d',
       fipi=r'значение выражения \( \d+ √\( \d+ \) \) 2 \d+|значение выражения \d+ √\( \d+ \) 2 \d+',
       mistakes=['забывают возвести в степень множитель k', 'возводят в степень только множитель'],
       kim=kim(KIM8, kes=['1.3']))
def gen_ep08_root_square(r):
    n = r.choice([2, 2, 2, 3])
    k = r.randint(2, 9)
    m = r.choice([2, 3, 5, 6, 7, 10, 11, 13] if n == 2 else [2, 3, 4, 5, 6, 7, 9])
    top = k ** n * m
    d = r.choice([v for v in range(2, 101) if top % v == 0 or F(top, v).denominator in (2, 4, 5)])
    ans = F(top, d)
    if not nice(ans, 2) or d == top or ans < 1:
        return None
    f = f'({k}{root(n, str(m))})^{{{n}}} / {d}'
    q = val_q(r, f)
    ex = f'({k}{root(n, str(m))})^{{{n}}} = {k}^{{{n}}}·{m} = {top}; {top} : {d} = {tnum(ans)}.'
    expr = (k * sp.root(m, n)) ** n / d
    return pcard(q, num(ans), ex), expr_check(expr, num(ans))


@proto('ep08-root-distrib', 'ege-prof', 8, 'Раскрытие скобок с корнями: (√A ± √B)·√m',
       invariant='A = p²m, B = q²m; выносим множитель из-под корня: (p√m ± q√m)·√m = (p ± q)·m.',
       varies='p, q, m, знак, порядок множителей',
       answer_rule='(p ± q)·m',
       fipi=r'значение выражения \( √\( \d+ \) [−+] √\( \d+ \) \) ⋅ √',
       mistakes=['вычитают подкоренные выражения: √A − √B = √(A − B)', 'не выносят множитель из-под корня'],
       kim=kim(KIM8, kes=['1.3']))
def gen_ep08_root_distrib(r):
    m = r.choice([2, 3, 5, 6, 7, 10, 11])
    p, q_ = r.sample(range(1, 9), 2)
    sgn = r.choice([1, -1])
    A, B = p * p * m, q_ * q_ * m
    if A == m and B == m:
        return None
    ans = (p + sgn * q_) * m
    s = '+' if sgn > 0 else '−'
    f = pick(r, f'(√{A} {s} √{B}) · √{m}', f'√{m} · (√{A} {s} √{B})')
    q = val_q(r, f)
    rt = lambda v, c: f'√{v}' if c == 1 else f'√{v} = {c}√{m}'
    ex = f'{rt(A, p)}, {rt(B, q_)}; ({p} {s} {q_})·√{m}·√{m} = {tnum(p + sgn * q_)}·{m} = {tnum(ans)}.'
    expr = (sp.sqrt(A) + sgn * sp.sqrt(B)) * sp.sqrt(m)
    return pcard(q, num(ans), ex), expr_check(expr, num(ans))


def _prime_pow(p, s):
    return p ** s


@proto('ep08-pow-tower', 'ege-prof', 8, 'Степень степени: (a^m)^n : b^k',
       invariant='все основания — степени одного простого числа; (a^m)^n = a^{mn}, приводим к общему основанию и вычитаем показатели.',
       varies='простое основание, степени оснований, показатели',
       answer_rule='p^{s₁mn − s₂k}',
       fipi=r'значение выражения \( \d+ \d+ \) \d+ : (\( )?\d+ \d+',
       mistakes=['складывают показатели m + n вместо умножения', 'не приводят к общему основанию'],
       kim=kim(KIM8, kes=['1.4']))
def gen_ep08_pow_tower(r):
    p = r.choice([2, 2, 3, 5, 7])
    s1 = r.choice([1, 1, 2, 3, 4, 6] if p == 2 else [1, 1, 2])
    s2 = r.choice([1, 2, 3, 4] if p == 2 else [1, 2])
    res = r.choice([1, 2, 3, 4, -1, -2] if p <= 3 else [1, 2, -1])
    m, n = r.randint(2, 19), r.randint(2, 9)
    tot = s1 * m * n - res
    if tot % s2:
        return None
    k = tot // s2
    if k <= 1 or k > 200:
        return None
    ans = F(p) ** res
    if not nice(ans, 3):
        return None
    a, b = p ** s1, p ** s2
    two = r.random() < 0.3 and s2 > 1
    if two:
        # делитель в виде (b^u)^v
        u = next((d for d in range(2, 10) if k % d == 0), None)
        if not u:
            return None
        f = f'({a}^{{{m}}})^{{{n}}} : ({b}^{{{k // u}}})^{{{u}}}'
    else:
        f = f'({a}^{{{m}}})^{{{n}}} : {b}^{{{k}}}'
    q = val_q(r, f)
    ex = f'{p}^{{{s1 * m * n}}} : {p}^{{{s2 * k}}} = {p}^{{{tnum(res)}}} = {tnum(ans)}.'
    expr = (sp.Integer(a) ** m) ** n / sp.Integer(b) ** k
    return pcard(q, num(ans), ex), lambda: expr == R(ans)


def _dec(x):
    """Показатель в условии: 2,6 или 1/5."""
    x = F(x)
    return tnum(x) if finite(x) else f'{x.numerator}/{x.denominator}'


@proto('ep08-pow-frac', 'ege-prof', 8, 'Степени с дробными показателями и основаниями — степенями одного числа',
       invariant='a = p^s, b = p^t; a^u · b^v (или a^u : b^v) = p^{su ± tv}, где показатель — целое число.',
       varies='простое число p, основания (например, 9 и 81, 4 и 16, 5 и 25), десятичные или обыкновенные дробные показатели, умножение или деление',
       answer_rule='p в степени su ± tv',
       fipi=r'значение выражения \d+ \d+,\d+ (⋅ )?\d+ \d+,\d+ \.|значение выражения \d+ 1 \d+ ⋅ \d+ \d+ \d+ \.',
       mistakes=['перемножают основания 9·81 и складывают показатели', 'делят показатели вместо вычитания'],
       kim=kim(KIM8, kes=['1.4']))
def gen_ep08_pow_frac(r):
    p = r.choice([2, 3, 5, 7])
    opts = {2: [1, 2, 3, 4], 3: [1, 2, 4], 5: [1, 2], 7: [1, 2]}[p]
    s, t = r.choice(opts), r.choice(opts)
    if s == t:
        return None
    op = r.choice(['*', ':'])
    res = r.randint(1, 4 if p <= 3 else 2)
    frac = r.random() < 0.3
    if frac:
        den = r.choice([3, 4, 5, 6, 10])
        u = F(r.randint(1, 3 * den), den)
    else:
        u = F(r.randint(3, 99), r.choice([10, 100]))
    # s·u ± t·v = res
    v = (F(res) - s * u) / t if op == '*' else (s * u - res) / t
    if v == 0 or not (finite(v) or frac) or abs(v) > 10 or u.denominator == 1:
        return None
    if frac and v.denominator not in (1, u.denominator, 2, 3, 4, 5, 6, 10):
        return None
    a, b = p ** s, p ** t
    ans = F(p) ** res
    uv = lambda z: f'({_dec(z)})' if z < 0 else _dec(z)
    f = f'{a}^{{{_dec(u)}}} {"·" if op == "*" else ":"} {b}^{{{_dec(v)}}}'
    q = val_q(r, f)
    ex = f'{", ".join(f"{z} = {p}^{{{w}}}" for z, w in ((a, s), (b, t)) if w > 1)}; показатель {s}·{uv(u)} {"+" if op == "*" else "−"} {t}·{uv(v)} = {res}; ответ {p}^{{{res}}} = {tnum(ans)}.'
    expr = sp.Integer(a) ** R(u) * sp.Integer(b) ** (R(v) if op == '*' else -R(v))
    return pcard(q, num(ans), ex), lambda: sp.simplify(expr - R(ans)) == 0


@proto('ep08-pow-split', 'ege-prof', 8, 'Степень произведения: (ab)^u · a^v : b^w',
       invariant='раскладываем основание-произведение: (ab)^u = a^u·b^u, затем показатели при a и при b складываются в целые числа.',
       varies='основание-произведение (6, 10, 14, 15, 21, 35), десятичные показатели, порядок множителей',
       answer_rule='a^{u + v} · b^{u − w}',
       fipi=r'значение выражения \d{2} \d+,\d+ ⋅ \d+ − \d+,\d+ \d+ \d+,\d+',
       mistakes=['считают (ab)^u = a^u + b^u', 'ошибка знака при отрицательном показателе'],
       kim=kim(KIM8, kes=['1.4']))
def gen_ep08_pow_split(r):
    a, b = r.choice([(2, 3), (2, 5), (2, 7), (3, 5), (3, 7), (5, 7), (2, 11), (3, 2), (5, 2), (7, 2)])
    ea, eb = r.choice([0, 1, 2, 3]), r.choice([0, 1, 2])
    if ea + eb == 0:
        return None
    u = F(r.randint(11, 99), 10)
    if u.denominator == 1:
        return None
    v, w = ea - u, u - eb      # a^{u+v} = a^{ea}, b^{u−w} = b^{eb}
    ans = a ** ea * b ** eb
    if ans > 2000:
        return None
    sgn = lambda z: f'({tnum(z)})' if z < 0 else tnum(z)
    if r.random() < 0.5:
        f = f'{a * b}^{{{tnum(u)}}} · {a}^{{{tnum(v)}}} / {b}^{{{tnum(w)}}}'
    else:
        f = f'{a * b}^{{{tnum(u)}}} / ({b}^{{{tnum(w)}}} · {a}^{{{tnum(-v)}}})'
    q = val_q(r, f)
    ex = (f'{a * b}^{{{tnum(u)}}} = {a}^{{{tnum(u)}}}·{b}^{{{tnum(u)}}}; {a}^{{{tnum(u)} + {sgn(v)}}}·{b}^{{{tnum(u)} − {sgn(w)}}} '
          f'= {a}^{{{ea}}}·{b}^{{{eb}}} = {ans}.')
    expr = sp.Integer(a * b) ** R(u) * sp.Integer(a) ** R(v) / sp.Integer(b) ** R(w)
    return pcard(q, num(ans), ex), lambda: sp.simplify(expr - ans) == 0


@proto('ep08-pow-irr', 'ege-prof', 8, 'Степени с иррациональными показателями',
       invariant='основания — степени одного числа p; иррациональные части показателей (α√m) взаимно уничтожаются, остаётся p в целой степени.',
       varies='p и степень основания, корень √m в показателе, числовые сдвиги, умножение или деление',
       answer_rule='p^{s(α√m + β) + (γ − sα√m)} = p^{sβ + γ}',
       fipi=r'значение выражения \d+ \d √\( \d+ \) [+−] \d+ ⋅ \d+',
       mistakes=['пытаются вычислить √m приближённо', 'не умножают весь показатель на s при переходе к основанию p'],
       kim=kim(KIM8, kes=['1.4']))
def gen_ep08_pow_irr(r):
    p = r.choice([2, 3, 5, 7])
    s = r.choice([2, 3] if p <= 3 else [2])
    m = r.choice([2, 3, 5, 6, 7, 8, 10, 12])
    al = r.randint(1, 5)
    be = r.randint(-4, 5)
    res = r.randint(1, 4 if p <= 3 else 3)
    ga = res - s * be
    A = p ** s
    ans = p ** res
    if ans > 1000 or abs(ga) > 12:
        return None
    e1 = f'{al if al > 1 else ""}√{m}' + (f' + {be}' if be > 0 else f' − {-be}' if be < 0 else '')
    ir = s * al
    e2 = (f'{ga} − {ir}√{m}' if ga > 0 else f'−{ir}√{m}' if ga == 0 else f'{tnum(ga)} − {ir}√{m}')
    if r.random() < 0.5:
        f = f'{A}^{{{e1}}} · {p}^{{{e2}}}'
    else:
        # деление: p^{γ − ir√m} = 1 : p^{ir√m − γ}
        e3 = f'{ir}√{m}' + (f' − {ga}' if ga > 0 else f' + {-ga}' if ga < 0 else '')
        f = f'{A}^{{{e1}}} : {p}^{{{e3}}}'
    q = val_q(r, f)
    ex = f'{A} = {p}^{{{s}}}; показатель: {s}({e1}) + ({e2}) = {res}; ответ {p}^{{{res}}} = {ans}.'
    expr = sp.Integer(A) ** (al * sp.sqrt(m) + be) * sp.Integer(p) ** (ga - ir * sp.sqrt(m))
    return pcard(q, num(ans), ex), lambda: sp.simplify(sp.expand_power_base(sp.powsimp(expr, force=True), force=True) - ans) == 0 or abs(float(expr) - ans) < 1e-6


@proto('ep08-log-root', 'ege-prof', 8, 'Логарифм корня из основания',
       invariant='k·log_a ⁿ√a = k·(1/n): логарифм основания в дробной степени.',
       varies='основание a, степень корня n, множитель k; иногда корень из степени a^m',
       answer_rule='k·m/n',
       fipi=r'значение выражения \d+ log \d+ \d+ \d+ ?\.',
       mistakes=['пишут log_a ⁿ√a = n', 'путают множитель и степень корня'],
       kim=kim(KIM8, kes=['1.6']))
def gen_ep08_log_root(r):
    a = r.choice([2, 3, 5, 6, 7, 10, 11, 13, 17])
    n = r.choice([2, 3, 4, 5, 6, 7, 8])
    mm = r.choice([1, 1, 1, 2, 3])
    if F(mm, n).denominator == 1:
        return None
    k = r.randint(2, 40)
    ans = F(k * mm, n)
    if not nice(ans, 1):
        return None
    arg = root(n, str(a) if mm == 1 else f'{a}^{{{mm}}}')
    f = f'{k}{logb(a)} {arg}'
    q = val_q(r, f)
    ex = f'{logb(a)} {arg} = {mm}/{n}; {k}·{mm}/{n} = {tnum(ans)}.'
    expr = k * sp.log(sp.root(sp.Integer(a) ** mm, n), a)
    return pcard(q, num(ans), ex), expr_check(sp.simplify(expr), num(ans))


def _dec_log_base():
    return [(F(1, 2), '0,5'), (F(1, 5), '0,2'), (F(3, 5), '0,6'), (F(2, 5), '0,4'), (F(7, 10), '0,7'), (F(4, 5), '0,8')]


@proto('ep08-log-sum', 'ege-prof', 8, 'Сумма и разность логарифмов с одним основанием',
       invariant='log_a x ± log_a y = log_a(xy) или log_a(x/y), где xy (x/y) — целая степень a.',
       varies='основание (целое или десятичное 0,6 и т. п.), числа (в том числе десятичные 6,4), сумма или разность',
       answer_rule='показатель степени: xy = a^e или x/y = a^e',
       fipi=r'значение выражения log (\d+(,\d+)?) \d+(,\d+)? [−+] log \1 ​? ?\d+',
       mistakes=['вычитают аргументы: log(x) − log(y) = log(x − y)', 'для основания 0,6 теряют знак показателя'],
       kim=kim(KIM8, kes=['1.6']))
def gen_ep08_log_sum(r):
    dec = r.random() < 0.25
    if dec:
        a, at = r.choice(_dec_log_base())
        e = r.choice([-1, -2, -3, 1, 2])
    else:
        a = F(r.choice([2, 2, 3, 3, 4, 5, 6, 7]))
        at = str(a)
        e = r.choice([1, 2, 3, 4, 5, 6] if a == 2 else [1, 2, 3, 4] if a <= 5 else [1, 2, 3])
    tgt = a ** e
    op = r.choice(['+', '−'])
    if op == '+':
        # x·y = tgt; x = tgt/y, y — «неудобный» множитель
        y = F(r.choice([3, 5, 6, 7, 10, 12, 14, 15, 20, 25, 18, 50]), r.choice([1, 1, 1, 10, 2, 5]))
        x = tgt / y
    else:
        y = F(r.choice([2, 3, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 18, 20]), r.choice([1, 1, 1, 10]))
        x = tgt * y
    if not (finite(x) and finite(y)) or x <= 0 or y == a or x == a or F(x).denominator > 100 or x > 5000 or x == y:
        return None
    if F(x).denominator != 1 and F(y).denominator != 1:
        return None
    lg = logb(at)
    f = f'{lg}{tnum(x)} {op} {lg}{tnum(y)}'
    q = val_q(r, f)
    ex = f'{lg}({tnum(x)} {"·" if op == "+" else ":"} {tnum(y)}) = {lg}{fr(tgt)} = {tnum(e)}.'
    A = R(a)
    expr = sp.log(R(x), A) + (1 if op == '+' else -1) * sp.log(R(y), A)
    exact = lambda: (R(x) * R(y) if op == '+' else R(x) / R(y)) == A ** e
    return pcard(q, num(e), ex), lambda: abs(float(expr) - e) < 1e-9 and exact()


@proto('ep08-log-ratio', 'ege-prof', 8, 'Отношение логарифмов с одним основанием',
       invariant='log_c B^k / log_c B = k (формула перехода к новому основанию: это log_B B^k).',
       varies='основание c (не связано с числами), B и k, иногда дробный результат',
       answer_rule='k',
       fipi=r'значение выражения log (\d+) \d+ log \1 \d+ ?\.',
       mistakes=['сокращают логарифмы как дроби: log 32 / log 2 = 16', 'вычитают вместо деления'],
       kim=kim(KIM8, kes=['1.6']))
def gen_ep08_log_ratio(r):
    c = r.choice([2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 0.5])
    B = r.choice([2, 3, 5, 6, 7, 10, 11])
    k = r.choice([2, 3, 4, 5, 6])
    top = B ** k
    if top > 5000 or c == B:
        return None
    flip = r.random() < 0.2
    lc = logb('0,5' if c == 0.5 else c)
    if flip:
        f = f'{lc}{B} / {lc}{top}'
        ans = F(1, k)
        if not finite(ans):
            return None
    else:
        f = f'{lc}{top} / {lc}{B}'
        ans = F(k)
    q = val_q(r, f)
    ex = f'По формуле перехода это log{str(B).translate(SUB)}{top if not flip else B}{"" if not flip else ""} … = {tnum(ans)}: {top} = {B}^{{{k}}}.'
    ex = f'{top} = {B}^{{{k}}}, поэтому {lc}{top} = {k}·{lc}{B}; отношение равно {tnum(ans)}.'
    cc = sp.Rational(1, 2) if c == 0.5 else sp.Integer(c)
    expr = sp.log(top, cc) / sp.log(B, cc) if not flip else sp.log(B, cc) / sp.log(top, cc)
    return pcard(q, num(ans), ex), lambda: sp.simplify(expr - R(ans)) == 0


@proto('ep08-log-base-ratio', 'ege-prof', 8, 'Отношение логарифмов одного числа по разным основаниям',
       invariant='log_a c / log_{a^k} c = k: основание a^k выносим множителем 1/k.',
       varies='основание a и его степень a^k, число c, порядок дроби, добавочное слагаемое',
       answer_rule='k (или 1/k)',
       fipi=r'значение выражения log (\d+) \d+ log (\d+) \d+ ?\.$|log 9 28 log 9 7',
       mistakes=['считают, что отношение равно 1 (одно и то же число c)', 'путают k и 1/k'],
       kim=kim(KIM8, kes=['1.6']))
def gen_ep08_log_base_ratio(r):
    a = r.choice([2, 3, 5, 6, 7])
    k = r.choice([2, 3, 2, 4] if a <= 3 else [2, 2, 3])
    ak = a ** k
    c = r.choice([v for v in range(5, 60) if v not in (a, ak) and v % a])
    flip = r.random() < 0.3
    if flip:
        ans = F(1, k)
        if not finite(ans):
            return None
        f = f'{logb(ak)}{c} / {logb(a)}{c}'
    else:
        ans = F(k)
        f = f'{logb(a)}{c} / {logb(ak)}{c}'
    q = val_q(r, f)
    ex = f'{logb(ak)}{c} = (1/{k})·{logb(a)}{c}, поэтому отношение равно {tnum(ans)}.'
    expr = sp.log(c, a) / sp.log(c, ak) if not flip else sp.log(c, ak) / sp.log(c, a)
    return pcard(q, num(ans), ex), lambda: sp.simplify(sp.expand_log(expr, force=True) - R(ans)) == 0


@proto('ep08-log-power', 'ege-prof', 8, 'Основное логарифмическое тождество',
       invariant='a^{log_a b} = b; при основании степени a^k или сумме в показателе: (a^k)^{log_a b} = b^k, a^{m + log_a b} = a^m·b.',
       varies='основание, число b, вид выражения (степень основания, слагаемое в показателе, основание a², √a)',
       answer_rule='b, b^k, a^m·b или √b',
       fipi=r'\d+ log \d+ \d+ ?\.?$',
       mistakes=['ответ log_a b вместо b', 'для 36^{log_6 5} отвечают 5'],
       kim=kim(KIM8, kes=['1.6']))
def gen_ep08_log_power(r):
    a = r.choice([2, 3, 5, 6, 7])
    b = r.choice([v for v in range(2, 16) if v != a and v % a])
    kind = r.choice(['pow', 'sum', 'sqr', 'root'])
    if kind == 'pow':
        k = r.choice([2, 3])
        f = f'{a ** k}^{{{logb(a)}{b}}}'
        ans = b ** k
        ex = f'{a ** k}^{{{logb(a)}{b}}} = ({a}^{{{logb(a)}{b}}})^{{{k}}} = {b}^{{{k}}} = {ans}.'
        expr = sp.Integer(a ** k) ** sp.log(b, a)
    elif kind == 'sum':
        m = r.choice([1, 2, 3, -1])
        f = f'{a}^{{{m} + {logb(a)}{b}}}' if m > 0 else f'{a}^{{{logb(a)}{b} − {-m}}}'
        ans = F(a) ** m * b
        if not nice(ans, 2):
            return None
        ex = f'{a}^{{{tnum(m)}}}·{a}^{{{logb(a)}{b}}} = {fr(F(a) ** m)}·{b} = {tnum(ans)}.'
        expr = sp.Integer(a) ** (m + sp.log(b, a))
    elif kind == 'sqr':
        k = 2
        f = f'{a}^{{{k}{logb(a)}{b}}}'
        ans = b ** k
        ex = f'{a}^{{{k}{logb(a)}{b}}} = {a}^{{{logb(a)}{b ** k}}} = {ans}.'
        expr = sp.Integer(a) ** (k * sp.log(b, a))
    else:
        f = f'{a}^{{{logb(a * a)}{b * b}}}'
        ans = b
        ex = f'{logb(a * a)}{b * b} = {logb(a)}{b}, поэтому значение равно {b}.'
        expr = sp.Integer(a) ** sp.log(b * b, a * a)
    if not nice(ans, 2) or ans > 1000:
        return None
    q = val_q(r, f)
    return pcard(q, num(ans), ex), lambda: abs(float(expr) - float(ans)) < 1e-9 and sp.simplify(sp.expand_log(sp.log(expr), force=True) - sp.log(R(ans))) == 0


# ---------- тригонометрия


def deg(x):
    return f'{x}°'


@proto('ep08-trig-dbl', 'ege-prof', 8, 'Синус двойного угла в градусах: k·sin α·cos α / sin 2α',
       invariant='sin 2α = 2 sin α cos α, поэтому k·sin α·cos α / sin 2α = k/2.',
       varies='угол α (в градусах), множитель k, порядок множителей',
       answer_rule='k/2',
       fipi=r'значение выражения \d+ sin (\d+) ° ⋅ cos \1 ° sin \d+ °',
       mistakes=['забывают множитель 2 в формуле двойного угла', 'пытаются вычислить синусы приближённо'],
       kim=kim(KIM8, kes=['1.5', '1.8']))
def gen_ep08_trig_dbl(r):
    a = r.randint(8, 86)
    if a in (30, 45, 60):
        return None
    k = r.choice(range(2, 41))
    ans = F(k, 2)
    if r.random() < 0.8:
        f = pick(r, f'{k} sin {deg(a)} · cos {deg(a)} / sin {deg(2 * a)}', f'{k} cos {deg(a)} · sin {deg(a)} / sin {deg(2 * a)}')
    else:
        f = f'sin {deg(2 * a)} / ({k} sin {deg(a)} · cos {deg(a)})'
        ans = F(2, k)
        if not finite(ans):
            return None
    q = val_q(r, f)
    ex = f'sin {deg(2 * a)} = 2 sin {deg(a)} cos {deg(a)}; значение равно {tnum(ans)}.'
    A = sp.pi * a / 180
    expr = k * sp.sin(A) * sp.cos(A) / sp.sin(2 * A) if 'sin ' + deg(2 * a) + ' /' not in f else sp.sin(2 * A) / (k * sp.sin(A) * sp.cos(A))
    return pcard(q, num(ans), ex), lambda: abs(float(expr) - float(ans)) < 1e-12


@proto('ep08-trig-compl', 'ege-prof', 8, 'Двойной угол и формулы приведения: k·sin 2α / (sin α · sin(90° − α))',
       invariant='числитель — синус двойного угла (возможно, записанный через 180° − 2α), в знаменателе sin α и cos α, один из них записан через дополнительный угол.',
       varies='угол, множитель, запись: sin 164° / (sin 82° · sin 8°), sin 70° / (cos 35° · cos 55°) и т. п.',
       answer_rule='2k',
       fipi=r'значение выражения \d+ sin \d+ ° (sin|cos) \d+ ° ⋅ (sin|cos) \d+ °',
       mistakes=['не замечают, что sin(90° − α) = cos α', 'не видят в 180° − 2α двойной угол'],
       kim=kim(KIM8, kes=['1.5', '1.8']))
def gen_ep08_trig_compl(r):
    a = r.randint(5, 85)
    if a in (30, 45, 60, 90) or 2 * a == 90:
        return None
    k = r.randint(2, 30)
    ans = 2 * k
    b = 90 - a
    top = r.choice([2 * a, 180 - 2 * a]) if 2 * a < 180 else 2 * a
    den = r.choice(['sin_sin', 'cos_cos'])
    if den == 'sin_sin':   # sin α · sin(90° − α) = sin α · cos α
        d1, d2 = f'sin {deg(a)}', f'sin {deg(b)}'
    else:                  # cos α · cos(90° − α) = cos α · sin α
        d1, d2 = f'cos {deg(a)}', f'cos {deg(b)}'
    f = f'{k} sin {deg(top)} / ({d1} · {d2})'
    q = val_q(r, f)
    ex = (f'sin {deg(top)} = {"" if top == 2 * a else f"sin {deg(2 * a)} = "}2 sin {deg(a)} cos {deg(a)}, '
          f'{d2} = {"cos" if den == "sin_sin" else "sin"} {deg(a)}; значение равно 2·{k} = {ans}.')
    A = sp.pi * a / 180
    B = sp.pi * b / 180
    fn = sp.sin if den == 'sin_sin' else sp.cos
    expr = k * sp.sin(sp.pi * top / 180) / (fn(A) * fn(B))
    return pcard(q, num(ans), ex), lambda: abs(float(expr) - ans) < 1e-9


def _pi(p, q):
    """pπ/q в условии."""
    fr_ = F(p, q)
    n, d = fr_.numerator, fr_.denominator
    s = ('−' if n < 0 else '') + ('' if abs(n) == 1 else str(abs(n))) + 'π'
    return s if d == 1 else f'{s}/{d}'


@proto('ep08-trig-rad-sc', 'ege-prof', 8, 'k·sin t·cos t при t = pπ/8 или pπ/12',
       invariant='sin t cos t = ½ sin 2t, а 2t — табличный угол (кратный π/4 или π/6) с учётом формул приведения.',
       varies='t (в том числе больше 2π и с отрицательным синусом), коэффициент k (с множителем √2 при π/8)',
       answer_rule='k/2 · sin 2t',
       fipi=r'значение выражения (\d+ )?(√\( \d \) )?sin \d+ ?π \d+ ⋅ cos',
       mistakes=['ошибаются со знаком синуса после приведения', 'забывают множитель ½'],
       kim=kim(KIM8, kes=['1.5', '1.8']))
def gen_ep08_trig_rad_sc(r):
    den = r.choice([8, 12])
    p = r.choice([v for v in range(1, 3 * den) if F(v, den).denominator == den])
    k = r.choice([7, 9, 11, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24])
    t = sp.pi * p / den
    if den == 8:     # sin 2t = ±√2/2 → коэффициент k√2
        coef, cexpr = f'{"" if k == 1 else k}√2', k * sp.sqrt(2)
    else:            # sin 2t = ±1/2
        coef, cexpr = ('' if k == 1 else str(k)), sp.Integer(k)
    val = sp.nsimplify(cexpr * sp.sin(t) * sp.cos(t))
    ans = F(str(sp.Rational(val))) if val.is_rational else None
    if ans is None or not nice(ans, 2):
        return None
    f = f'{coef} sin {_pi(p, den)} · cos {_pi(p, den)}'.strip()
    q = val_q(r, f)
    ex = f'{coef} sin t cos t = {coef}/2 · sin 2t, 2t = {_pi(2 * p, den)}; значение {tnum(ans)}.'.replace(' /2', '1/2')
    return pcard(q, num(ans), ex), lambda: abs(float(cexpr * sp.sin(t) * sp.cos(t)) - float(ans)) < 1e-12


@proto('ep08-trig-rad-cos2', 'ege-prof', 8, 'Косинус двойного угла: k cos²t − k sin²t, 2k cos²t − k, k − 2k sin²t',
       invariant='выражение сворачивается в k·cos 2t, где 2t — табличный угол (кратный π/4 или π/6).',
       varies='вид выражения (три формы), t = pπ/8 или pπ/12, коэффициент с √2 или √3',
       answer_rule='k·cos 2t',
       fipi=r'значение выражения \d* ?√\( \d \) (cos|−)|значение выражения √\( 2 \) − 2 √',
       mistakes=['путают формулы cos 2t', 'ошибка знака после приведения'],
       kim=kim(KIM8, kes=['1.5', '1.8']))
def gen_ep08_trig_rad_cos2(r):
    den = r.choice([8, 12])
    p = r.choice([v for v in range(1, 3 * den) if F(v, den).denominator == den])
    k = r.choice([7, 9, 10, 11, 12, 13, 14, 15])
    t = sp.pi * p / den
    sq = 2 if den == 8 else 3
    ks = f'{"" if k == 1 else k}√{sq}'
    k2 = f'{2 * k}√{sq}'
    K = k * sp.sqrt(sq)
    form = r.choice(['diff', 'cos', 'sin'])
    T = _pi(p, den)
    if form == 'diff':
        f = f'{ks} cos² {T} − {ks} sin² {T}'
        expr = K * sp.cos(t) ** 2 - K * sp.sin(t) ** 2
    elif form == 'cos':
        f = f'{k2} cos² {T} − {ks}'
        expr = 2 * K * sp.cos(t) ** 2 - K
    else:
        f = f'{ks} − {k2} sin² {T}'
        expr = K - 2 * K * sp.sin(t) ** 2
    val = K * sp.cos(2 * t)
    val = sp.nsimplify(val)
    if not val.is_rational:
        return None
    ans = F(int(val.p), int(val.q))
    if not nice(ans, 2):
        return None
    q = val_q(r, f)
    ex = f'Выражение равно {ks}·cos {_pi(2 * p, den)} = {tnum(ans)}.'
    return pcard(q, num(ans), ex), lambda: abs(float(expr) - float(ans)) < 1e-12


@proto('ep08-trig-cos2a', 'ege-prof', 8, 'k·cos 2α по известному sin α или cos α',
       invariant='cos 2α = 1 − 2 sin²α = 2 cos²α − 1; знак sin α и cos α не важен.',
       varies='данное значение (sin или cos, десятичная дробь, в том числе отрицательная), множитель k',
       answer_rule='k(1 − 2 sin²α) или k(2 cos²α − 1)',
       fipi=r'значение выражения \d+ cos 2 α , если (sin|cos) α =',
       mistakes=['считают cos 2α = 2 cos α', 'путают формулы через синус и косинус'],
       kim=kim(KIM8, kes=['1.5', '1.8']))
def gen_ep08_trig_cos2a(r):
    v = F(r.choice([1, 2, 3, 4, 5, 6, 7, 8, 9]), 10) * r.choice([1, -1])
    given = r.choice(['sin', 'cos'])
    k = r.randint(7, 40)
    c2 = 1 - 2 * v * v if given == 'sin' else 2 * v * v - 1
    ans = k * c2
    if not nice(ans, 2) or ans == 0:
        return None
    f = f'{k} cos 2α'
    tpl = pick(r, 'Найдите значение выражения {f}, если {g} α = {v}.', 'Вычислите {f}, если известно, что {g} α = {v}.',
               'Известно, что {g} α = {v}. Найдите {f}.')
    q = tpl.format(f=fm(f), g=given, v=tnum(v))
    ex = (f'cos 2α = 1 − 2 sin²α = {tnum(c2)}' if given == 'sin' else f'cos 2α = 2 cos²α − 1 = {tnum(c2)}') + f'; {k}·{par(c2)} = {tnum(ans)}.'
    al = sp.asin(R(v)) if given == 'sin' else sp.acos(R(v))
    return pcard(q, num(ans), ex), lambda: abs(float(k * sp.cos(2 * al)) - float(ans)) < 1e-12


QUART = {1: '(0; π/2)', 2: '(π/2; π)', 3: '(π; 3π/2)', 4: '(3π/2; 2π)'}


@proto('ep08-trig-find', 'ege-prof', 8, 'Значение тригонометрической функции по другой и четверти',
       invariant='основное тригонометрическое тождество + знак по четверти; величины заданы через корни (5√26/26) или дробями.',
       varies='какая функция дана и какую найти (sin, cos, tg), четверть, множитель, вид записи',
       answer_rule='sin² + cos² = 1, tg = sin/cos, знак по четверти',
       fipi=r'(значение выражения )?tg α , если cos α|найдите \d* ?(sin|cos|tg) α , если',
       mistakes=['берут неверный знак для четверти', 'не избавляются от корней в знаменателе'],
       kim=kim(KIM8, kes=['1.5', '1.8']))
def gen_ep08_trig_find(r):
    quarter = r.randint(1, 4)
    sc, ss = {1: (1, 1), 2: (-1, 1), 3: (-1, -1), 4: (1, -1)}[quarter]
    mode = r.choice(['sqrt', 'triple'])
    if mode == 'sqrt':
        # cos α = p/√N, sin α = q/√N, N = p² + q², tg = q/p
        p_, q_ = r.randint(1, 7), r.randint(1, 7)
        N = p_ * p_ + q_ * q_
        if int(math.isqrt(N)) ** 2 == N or math.gcd(p_, q_) != 1:
            return None
        cosv, sinv = sc * sp.Integer(p_) / sp.sqrt(N), ss * sp.Integer(q_) / sp.sqrt(N)
        given = r.choice(['cos', 'sin'])
        gv = cosv if given == 'cos' else sinv
        num_ = (p_ if given == 'cos' else q_)
        g = f'{"−" if gv < 0 else ""}{num_ if num_ > 1 else ""}√{N}/{N}'
        want = 'tg'
        k = r.choice([1, 1, 2, 3, 4, 5, 10])
        val = k * sinv / cosv
    else:
        a_, b_, c_ = r.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29)])
        if r.random() < 0.5:
            a_, b_ = b_, a_
        cosv, sinv = sp.Rational(sc * a_, c_), sp.Rational(ss * b_, c_)
        given = r.choice(['cos', 'sin', 'tg'])
        want = r.choice([w for w in ('sin', 'cos', 'tg') if w != given])
        gv = {'cos': cosv, 'sin': sinv, 'tg': sinv / cosv}[given]
        g = fr(F(int(gv.p), int(gv.q)))
        k = r.choice([1, 2, 3, 5, c_, 2 * c_, a_ if want == 'tg' else c_])
        val = k * {'cos': cosv, 'sin': sinv, 'tg': sinv / cosv}[want]
    if not val.is_rational:
        return None
    ans = F(int(val.p), int(val.q))
    if not nice(ans, 2):
        return None
    ws = f'{"" if k == 1 else k}{want} α'
    q = pick(r, f'Найдите {fm(ws)}, если {fm(f"{given} α = {g}")} и {fm(f"α ∈ {QUART[quarter]}")}.',
             f'Известно, что {fm(f"{given} α = {g}")} и {fm(f"α ∈ {QUART[quarter]}")}. Найдите {fm(ws)}.',
             f'Вычислите {fm(ws)}, если {fm(f"{given} α = {g}")}, а угол α лежит в интервале {fm(QUART[quarter])}.')
    ex = f'По основному тождеству и знаку в {quarter}-й четверти: sin α = {sinv}, cos α = {cosv}; {ws} = {tnum(ans)}.'.replace('sqrt', '√')

    def chk():
        al = sp.atan2(sinv, cosv) % (2 * sp.pi)
        lo = (quarter - 1) * sp.pi / 2
        okq = bool(lo < al < lo + sp.pi / 2)
        fnv = {'sin': sp.sin, 'cos': sp.cos, 'tg': sp.tan}[want](al)
        gvv = {'sin': sp.sin, 'cos': sp.cos, 'tg': sp.tan}[given](al)
        return okq and abs(float(k * fnv) - float(ans)) < 1e-9 and abs(float(gvv) - float(gv)) < 1e-12
    return pcard(q, num(ans), ex), chk


H = F(1, 2)
TAB = {  # угол → значения (sin, cos, tg) в виде (c, m) = c·√m
    'π/6': ((H, 1), (H, 3), (F(1, 3), 3)),
    'π/4': ((H, 2), (H, 2), (F(1), 1)),
    'π/3': ((H, 3), (H, 1), (F(1), 3)),
    '2π/3': ((H, 3), (-H, 1), (F(-1), 3)),
    '3π/4': ((H, 2), (-H, 2), (F(-1), 1)),
    '5π/6': ((H, 1), (-H, 3), (F(-1, 3), 3)),
    '7π/6': ((-H, 1), (-H, 3), (F(1, 3), 3)),
    '5π/4': ((-H, 2), (-H, 2), (F(1), 1)),
    '4π/3': ((-H, 3), (-H, 1), (F(1), 3)),
    '5π/3': ((-H, 3), (H, 1), (F(-1), 3)),
    '7π/4': ((-H, 2), (H, 2), (F(-1), 1)),
    '11π/6': ((-H, 1), (H, 3), (F(-1, 3), 3)),
    '−π/3': ((-H, 3), (H, 1), (F(-1), 3)),
    '−π/4': ((-H, 2), (H, 2), (F(-1), 1)),
    '−π/6': ((-H, 1), (H, 3), (F(-1, 3), 3)),
}
TAB_F = ['sin', 'cos', 'tg']


def _tv(v):
    c, m = v
    if m == 1:
        return fr(c)
    return f'{"−" if c < 0 else ""}{"" if abs(c.numerator) == 1 else abs(c.numerator)}√{m}' + (f'/{c.denominator}' if c.denominator > 1 else '')


def _angle(s):
    s = s.replace('−', '-').replace('π', '*pi')
    s = s[1:] if s.startswith('*') else s.replace('-*', '-')
    return sp.sympify(s)


@proto('ep08-trig-table', 'ege-prof', 8, 'Произведение табличных значений тригонометрических функций',
       invariant='k·√m·f(α)·g(β), где f, g — sin, cos, tg табличных углов (в том числе после приведения); корни сокращаются.',
       varies='углы (π/6 … 11π/6, отрицательные), функции, множитель k√m',
       answer_rule='подставляем табличные значения',
       fipi=r'значение выражения \d+ √\( \d \) tg π \d sin',
       mistakes=['путают sin π/6 и cos π/6', 'теряют знак для углов вне первой четверти'],
       kim=kim(KIM8, kes=['1.5']))
def gen_ep08_trig_table(r):
    a1, a2 = r.sample(list(TAB), 2)
    f1, f2 = r.choice(TAB_F), r.choice(TAB_F)
    (c1, m1), (c2, m2) = TAB[a1][TAB_F.index(f1)], TAB[a2][TAB_F.index(f2)]
    # c1√m1·c2√m2 = c1c2·√(m1m2); домножаем на √m, чтобы корень ушёл
    mm = m1 * m2
    if mm in (1, 4, 9):
        m, rat = 1, c1 * c2 * math.isqrt(mm)
    elif mm in (2, 3):
        m, rat = mm, c1 * c2 * mm
    elif mm == 6:
        return None
    else:
        return None
    k = r.randint(1, 40)
    ans = rat * k
    if not nice(ans, 1) or ans == 0:
        return None
    coef = (str(k) if k > 1 else '') + (f'√{m}' if m > 1 else '')
    f = f'{coef} {f1}({a1}) · {f2}({a2})'.strip()
    q = val_q(r, f)
    ex = f'{f1}({a1}) = {_tv((c1, m1))}, {f2}({a2}) = {_tv((c2, m2))}; значение {tnum(ans)}.'
    fn = {'sin': math.sin, 'cos': math.cos, 'tg': math.tan}
    fa1, fa2 = float(_angle(a1)), float(_angle(a2))
    return pcard(q, num(ans), ex), lambda: abs(k * math.sqrt(m) * fn[f1](fa1) * fn[f2](fa2) - float(ans)) < 1e-9


@proto('ep08-alg-simplify', 'ege-prof', 8, 'Дробно-рациональное выражение: сначала упростить, потом подставить',
       invariant='после сокращения дроби (разность квадратов, общий множитель) переменная пропадает или остаётся простое выражение; подстановка «неудобного» числа не нужна.',
       varies='вид дроби (a² − b²)/(a − b), (x² − 9)/(x + 3) − x, (a − b)/(√a − √b) и т. п., подставляемые числа',
       answer_rule='упрощаем выражение до константы или простого вида, затем подставляем',
       fipi=r'значение выражения .* при [a-z] =',
       mistakes=['подставляют числа до упрощения и ошибаются в вычислениях', 'сокращают слагаемые, а не множители'],
       kim=kim(KIM8, kes=['1.8']))
def gen_ep08_alg_simplify(r):
    kind = r.choice(['sq', 'sq2', 'root', 'ab'])
    x = sp.Symbol('x')
    if kind == 'sq':
        c = r.randint(2, 15)
        x0 = F(r.randint(101, 999), 10)
        sgn = r.choice([1, -1])
        # (x² − c²)/(x ∓ c) − x = ±c
        f = f'({poly([1, 0, -c * c])})/({lin(1, -sgn * c)}) − x'
        ans = F(sgn * c)
        expr = (x ** 2 - c * c) / (x - sgn * c) - x
        sub = {x: R(x0)}
        v = f'x = {tnum(x0)}'
    elif kind == 'sq2':
        a_ = r.randint(2, 9)
        c = r.randint(1, 9)
        x0 = F(r.randint(11, 99), 10) * r.choice([1, -1])
        # (a²x² − c²)/(ax + c) − ax = −c
        f = f'({poly([a_ * a_, 0, -c * c])})/({lin(a_, c)}) − {a_}x'
        ans = F(-c)
        expr = (a_ * a_ * x ** 2 - c * c) / (a_ * x + c) - a_ * x
        sub = {x: R(x0)}
        v = f'x = {tnum(x0)}'
    elif kind == 'root':
        # (x − c)/(√x − √c) − √x = √c при x > 0; c — точный квадрат
        s_ = r.randint(2, 9)
        c = s_ * s_
        x0 = F(r.choice([2, 3, 5, 7, 11, 13, 17, 19, 23]))
        f = f'({lin(1, -c)})/(√x − {s_}) − √x'
        ans = F(s_)
        expr = (x - c) / (sp.sqrt(x) - s_) - sp.sqrt(x)
        sub = {x: R(x0)}
        v = f'x = {tnum(x0)}'
    else:
        # (a² − 4b²)/(a − 2b) − a при b = …; равно 2b
        k = r.randint(2, 6)
        b0 = F(r.randint(11, 99), 10)
        aa, bb = sp.symbols('a b')
        f = f'(a² − {k * k}b²)/(a − {k}b) − a'
        ans = k * b0
        expr = (aa ** 2 - k * k * bb ** 2) / (aa - k * bb) - aa
        a0 = F(r.randint(11, 99), 10)
        if a0 == k * b0:
            return None
        sub = {aa: R(a0), bb: R(b0)}
        v = f'a = {tnum(a0)}, b = {tnum(b0)}'
    if not nice(ans, 2):
        return None
    q = pick(r, f'Найдите значение выражения {fm(f)} при {fm(v)}.', f'Вычислите {fm(f)} при {fm(v)}.',
             f'Упростите выражение {fm(f)} и найдите его значение при {fm(v)}.')
    ex = f'После сокращения дроби выражение равно {tnum(ans) if kind != "ab" else f"{k}b"}; ответ {tnum(ans)}.'
    return pcard(q, num(ans), ex), lambda: sp.simplify(expr.subs(sub) - R(ans)) == 0


@proto('ep08-alg-ratio', 'ege-prof', 8, 'Значение дроби по известному отношению a/b',
       invariant='(pa + qb)/(ra + sb) при a/b = t: делим числитель и знаменатель на b.',
       varies='коэффициенты дроби, отношение t (целое, дробное, отрицательное), вид условия (a/b = t или a = tb)',
       answer_rule='(pt + q)/(rt + s)',
       fipi=r'если \\?\(? ?a b = |, если a b =',
       mistakes=['подставляют a = t, b = 1 без проверки… ошибка в знаменателе', 'путают a/b и b/a'],
       kim=kim(KIM8, kes=['1.8']))
def gen_ep08_alg_ratio(r):
    t = F(r.choice([2, 3, 4, 5, 6, -2, -3, 1, 7]), r.choice([1, 1, 1, 2, 3]))
    p_, q_, r_, s_ = [r.choice([v for v in range(-9, 10) if v]) for _ in range(4)]
    den = r_ * t + s_
    if den == 0 or t == 1:
        return None
    ans = (p_ * t + q_) / den
    if not nice(ans, 2) or ans == 0:
        return None
    f = f'({lin(p_, q_, "a").replace("x", "a")}{"" if False else ""})'
    num_s = poly([p_, 0], 'a') + signed(q_) + 'b'
    num_s = num_s.replace(' 1b', ' b')
    den_s = poly([r_, 0], 'a') + signed(s_) + 'b'
    den_s = den_s.replace(' 1b', ' b')
    f = f'({num_s})/({den_s})'
    cond = f'a/b = {fr(t)}' if r.random() < 0.7 else (f'a = {fr(t)}b' if t.denominator == 1 else f'{t.denominator}a = {t.numerator}b'.replace('-', '−'))
    q = pick(r, f'Найдите значение выражения {fm(f)}, если {fm(cond)}.', f'Известно, что {fm(cond)}. Вычислите {fm(f)}.')
    pf = lambda z: f'({fr(z)})' if z < 0 else fr(z)
    ex = f'Делим числитель и знаменатель на b: ({tnum(p_)}·{pf(t)} + {pf(q_)})/({tnum(r_)}·{pf(t)} + {pf(s_)}) = {tnum(ans)}.'
    a_, b_ = sp.symbols('a b', positive=True)
    expr = (p_ * a_ + q_ * b_) / (r_ * a_ + s_ * b_)
    return pcard(q, num(ans), ex), lambda: sp.simplify(expr.subs(a_, R(t) * b_) - R(ans)) == 0


# ================================================================ 9. Производная и первообразная
#
# Графики строятся гладким монотонным сплайном (PCHIP, как в tools/build_packs.py):
# между соседними опорными точками функция монотонна, поэтому нули производной и
# экстремумы стоят ровно в опорных точках — в узлах сетки. Проверка каждой карточки —
# численная, по нарисованной функции (смены знака на мелкой сетке, конечные разности,
# численное интегрирование), то есть независимо от того, как ответ получен при генерации.


def _spline(xs, ys):
    """Монотонная кубическая интерполяция Фрича — Карлсона: без выбросов между узлами."""
    n = len(xs) - 1
    h = [xs[i + 1] - xs[i] for i in range(n)]
    dl = [(ys[i + 1] - ys[i]) / h[i] for i in range(n)]
    m = [dl[0]] + [0.0] * (n - 1) + [dl[-1]]
    for i in range(1, n):
        if dl[i - 1] * dl[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / dl[i - 1] + w2 / dl[i])

    def f(x):
        if x < xs[0] - 1e-12 or x > xs[-1] + 1e-12:
            raise ValueError('вне области')
        j = 0
        while j < n - 1 and x > xs[j + 1]:
            j += 1
        t = (x - xs[j]) / h[j]
        h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[j] + h10 * h[j] * m[j] + h01 * ys[j + 1] + h11 * h[j] * m[j + 1]
    return f


def _dom(fn, a, b):
    """Функция, определённая только на (a; b) — для рисунка."""
    def g(x):
        if x <= a or x >= b:
            raise ValueError
        return fn(x)
    return g


def _label_spot(fn, a, b, X0, X1, y0, y1, u):
    """Место для подписи «y = f(x)» (левый нижний угол текста): угол рисунка, где график дальше всего."""
    wid = 72 / u          # ширина подписи в клетках
    best, spot = -1, (X1 - wid - 0.2, y1 - 0.9)
    for x_left in (X1 - wid - 0.2, X0 + 0.2, X0 + 0.2 + (X1 - X0 - wid) / 2):
        for yb in (y1 - 0.9, y0 + 0.4):
            gap = 99
            for i in range(21):
                x = x_left + wid * i / 20
                try:
                    y = fn(x) if a <= x <= b else None
                except (ValueError, ZeroDivisionError):
                    y = None
                if y is not None:
                    gap = min(gap, abs(y - (yb + 0.35)))
            if gap > best:
                best, spot = gap, (x_left, yb)
    return spot


def _fsvg(fn, a, b, y0, y1, name='y = f(x)', marks=(), ticks=(), dots=(), extra=None, open_ends=True):
    """Рисунок графика на клетке: область (a; b), подписи концов, отмеченные точки x₁…xₙ
    (marks — список (x, подпись)), подписи абсцисс ticks, точки dots, свой слой extra."""
    X0, X1 = min(a, 0) - 1, max(b, 0) + 1

    def ex(sx, sy):
        out = ''
        for x in (a, b):
            if open_ends:
                y = fn(x)
                out += f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="3.2" fill="#fff" stroke="{BLUE}" stroke-width="1.6"/>'
        for x, lab in marks:
            y = fn(x)
            out += (f'<line x1="{sx(x):.1f}" y1="{sy(0):.1f}" x2="{sx(x):.1f}" y2="{sy(y):.1f}" stroke="{INK}" stroke-dasharray="3 3" stroke-width="1"/>'
                    f'<circle cx="{sx(x):.1f}" cy="{sy(0):.1f}" r="2.4" fill="{INK}"/>'
                    f'<text x="{sx(x) - 6:.1f}" y="{sy(0) + (14 if y >= 0 else -6):.1f}" font-size="11" font-style="italic">{lab}</text>')
        for x in ticks:
            if x not in (0, 1):
                out += f'<text x="{sx(x) - 4:.1f}" y="{sy(0) + 14:.1f}" font-size="11">{tnum(x)}</text>'
        for x, y in dots:
            out += f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="3.2" fill="{INK}"/>'
        lx, ly = _label_spot(fn, a, b, X0, X1, y0, y1, (sx(X1) - sx(X0)) / (X1 - X0))
        out += f'<text x="{sx(lx):.1f}" y="{sy(ly):.1f}" font-size="12" font-style="italic">{name}</text>'
        if extra:
            out += extra(sx, sy)
        return out
    w = 360 if X1 - X0 > 12 else 300
    return svg_plot(_dom(fn, a - 1e-9, b + 1e-9) if not open_ends else _dom(fn, a, b), X0, X1, y0, y1, extra=ex, width=w)


def _dcurve(r, a, b, zeros, touches, sign):
    """Гладкий график f′ на [a; b]: простые нули zeros (смена знака), касания оси touches."""
    cuts = sorted(zeros + touches)
    bounds = [a] + cuts + [b]
    raw = lambda x: sign * math.prod(x - z for z in zeros) * math.prod((x - d) ** 2 for d in touches)
    xs, ys = [float(a)], [None]
    for i, (lo, hi) in enumerate(zip(bounds, bounds[1:])):
        sg = 1 if raw((lo + hi) / 2) > 0 else -1
        amp = r.uniform(1.3, 3.3) * (0.7 if (lo in touches or hi in touches) else 1)
        if i == 0:
            ys[0] = sg * r.uniform(0.8, 3.3)
        xs.append((lo + hi) / 2)
        ys.append(sg * amp)
        if hi in touches:
            xs += [hi - 0.45, hi, hi + 0.45]
            ys += [sg * 0.35, sg * 0.0, sg * 0.35]
        elif hi != b:
            xs.append(float(hi))
            ys.append(0.0)
        else:
            xs.append(float(b))
            ys.append(sg * r.uniform(0.8, 3.3))
    # касания: значение 0 в самой точке, но знак не меняется
    return _spline(xs, ys), xs, ys


def _zeros(r, a, b, cnt, gap=2):
    """cnt целых точек внутри (a; b) с шагом не меньше gap и отступом от концов."""
    for _ in range(50):
        z = sorted(r.sample(range(a + 1, b), cnt))
        if all(q - p >= gap for p, q in zip(z, z[1:])):
            return z
    return None


def sign_changes(fn, lo, hi, n=4000):
    """Численно: список (x, 'max'|'min') — точек смены знака fn на (lo; hi)."""
    out = []
    prev, px = None, None
    for i in range(1, n):
        x = lo + (hi - lo) * i / n
        v = fn(x)
        s_ = 1 if v > 1e-7 else -1 if v < -1e-7 else 0
        if s_ == 0:
            continue
        if prev is not None and s_ != prev:
            out.append(((px + x) / 2, 'max' if prev > 0 else 'min'))
        prev, px = s_, x
    return out


def _domain(r):
    a = -r.randint(3, 11)
    b = r.randint(3, 12)
    if b - a < 9 or b - a > 20:
        return None
    return a, b


EXT_W = {'max': ('максимума', 'точек максимума'), 'min': ('минимума', 'точек минимума'), 'ext': ('экстремума', 'точек экстремума')}
DG = 'y = f′(x)'


def _dgraph_setup(r, nmin=3, nmax=5):
    ab = _domain(r)
    if not ab:
        return None
    a, b = ab
    cnt = r.randint(nmin, nmax)
    zeros = _zeros(r, a, b, cnt)
    if not zeros:
        return None
    rest = [x for x in range(a + 2, b - 1) if all(abs(x - z) >= 2 for z in zeros)]
    touches = r.sample(rest, 1) if rest and r.random() < 0.35 else []
    sign = r.choice([1, -1])
    fn, xs, ys = _dcurve(r, a, b, zeros, touches, sign)
    return a, b, zeros, touches, sign, fn


def _kinds_at(zeros, touches, sign, b):
    """По нулям производной: тип каждой точки смены знака (комбинаторно, без сплайна)."""
    res = []
    for z in zeros:
        right = sign * math.prod((z + 0.01) - w for w in zeros)
        res.append((z, 'min' if right > 0 else 'max'))
    return res


def dq_intro(a, b, r=None):
    """Вступление к заданию по графику производной — своими словами (текст КИМ дословно не повторяем)."""
    iv = fm(f'({tnum(a)}; {tnum(b)})')
    v = [f'Функция {fm("f(x)")} определена на интервале {iv}. На рисунке изображён график её производной {fm("y = f′(x)")}.',
         f'На рисунке показан график производной {fm("y = f′(x)")} некоторой функции {fm("f(x)")}, заданной на интервале {iv}.',
         f'Функция {fm("f(x)")} задана на интервале {iv}, а график её производной {fm("y = f′(x)")} приведён на рисунке.']
    return (r.choice(v) if r else v[0])


@proto('ep09-dg-count', 'ege-prof', 9, 'График производной: число точек максимума (минимума, экстремума) на отрезке',
       invariant='по графику f′ считаем точки, где f′ меняет знак: с «+» на «−» — максимум, с «−» на «+» — минимум; касание оси без смены знака экстремумом не является.',
       varies='область определения, нули производной, отрезок или весь интервал, вид точек (максимум, минимум, экстремум)',
       answer_rule='число нулей f′ на отрезке со сменой знака нужного направления',
       fipi=r'производной функции .*Найдите количество точек (максимума|минимума|экстремума)',
       mistakes=['считают точки пересечения графика с осью, где знак не меняется (касание)', 'путают график f′ с графиком f и считают его вершины'],
       svg=True, kim=kim(KIM9, kes=['4.2'], style='как в КИМ: «На рисунке изображён график y = f′(x) — производной функции f(x), определённой на интервале (…). Найдите количество точек … принадлежащих отрезку […]»'))
def gen_ep09_dg_count(r):
    st = _dgraph_setup(r, 3, 6)
    if not st:
        return None
    a, b, zeros, touches, sign, fn = st
    kinds = _kinds_at(zeros, touches, sign, b)
    what = r.choice(['max', 'min', 'ext'])
    whole = r.random() < 0.3
    if whole:
        c, d = a, b
    else:
        c = r.randint(a + 1, b - 4)
        d = r.randint(c + 3, b - 1)
        if any(z in (c, d) for z in zeros + touches):
            return None
    ans = sum(1 for z, k in kinds if c < z < d and (what == 'ext' or k == what))
    svg = _fsvg(fn, a, b, -4, 4, name=DG, ticks=(a, b))
    where = 'на всём интервале' if whole else f'на отрезке {fm(f"[{tnum(c)}; {tnum(d)}]")}'
    q = dq_intro(a, b, r) + ' ' + pick(r, f'Сколько {EXT_W[what][1]} имеет функция {fm("f(x)")} {where}?',
                                       f'Определите, сколько у функции {fm("f(x)")} {EXT_W[what][1]} {where}.',
                                       f'Найдите число {EXT_W[what][1]} функции {fm("f(x)")}, лежащих {where}.'.replace('лежащих на всём интервале', 'на всём интервале'))
    ex = (f'Точки {EXT_W[what][0]} — нули производной, в которых она меняет знак'
          f'{" с «+» на «−»" if what == "max" else " с «−» на «+»" if what == "min" else ""}; '
          f'на {"интервале" if whole else "отрезке"} таких точек {ans}.')

    def chk():
        ch = sign_changes(fn, c + 1e-6, d - 1e-6)
        return ans == sum(1 for x, k in ch if what == 'ext' or k == what) and all(abs(x - round(x)) < 0.01 for x, _ in ch)
    return pcard(q, num(ans), ex, svg=svg), chk


@proto('ep09-dg-point', 'ege-prof', 9, 'График производной: точка максимума (минимума, экстремума)',
       invariant='по графику f′ находим единственную точку, где f′ меняет знак нужным образом (на всём интервале или на отрезке).',
       varies='область, нули производной, тип точки, отрезок',
       answer_rule='абсцисса нуля f′ со сменой знака «+ → −» (максимум) или «− → +» (минимум)',
       fipi=r'производной функции .*Найдите точку (максимума|минимума|экстремума)',
       mistakes=['ищут наибольшее значение f′ вместо нуля', 'путают максимум и минимум'],
       svg=True, kim=kim(KIM9, kes=['4.2']))
def gen_ep09_dg_point(r):
    st = _dgraph_setup(r, 1, 4)
    if not st:
        return None
    a, b, zeros, touches, sign, fn = st
    kinds = _kinds_at(zeros, touches, sign, b)
    what = r.choice(['max', 'min', 'ext'])
    if what == 'ext':
        c = r.randint(a + 1, b - 3)
        d = r.randint(c + 2, b - 1)
        inside = [z for z, k in kinds if c < z < d]
        if len(inside) != 1 or any(t in (c, d) for t in zeros + touches):
            return None
        ans = inside[0]
        seg = f'на отрезке {fm(f"[{tnum(c)}; {tnum(d)}]")}'
    else:
        cand = [z for z, k in kinds if k == what]
        if len(cand) != 1:
            return None
        ans = cand[0]
        c, d = a, b
        seg = ''
    svg = _fsvg(fn, a, b, -4, 4, name=DG, ticks=(a, b))
    if what == 'ext':
        q = dq_intro(a, b, r) + ' ' + pick(r, f'{seg[0].upper() + seg[1:]} функция {fm("f(x)")} имеет ровно одну точку экстремума. Найдите её.',
                                           f'Укажите абсциссу единственной точки экстремума функции {fm("f(x)")} {seg}.')
    else:
        q = dq_intro(a, b, r) + ' ' + pick(r, f'В какой точке функция {fm("f(x)")} имеет {EXT_W[what][0][:-1]}?',
                                           f'Укажите абсциссу точки {EXT_W[what][0]} функции {fm("f(x)")}.',
                                           f'Найдите, в какой точке функция {fm("f(x)")} достигает {EXT_W[what][0][:-1]}а.')
    ex = f'В точке {tnum(ans)} производная обращается в ноль и меняет знак — это точка {EXT_W[what][0] if what != "ext" else "экстремума"}.'

    def chk():
        ch = [(x, k) for x, k in sign_changes(fn, c + 1e-6, d - 1e-6) if what == 'ext' or k == what]
        return len(ch) == 1 and abs(ch[0][0] - ans) < 0.01
    return pcard(q, num(ans), ex, svg=svg), chk


@proto('ep09-dg-segmax', 'ege-prof', 9, 'График производной: в какой точке отрезка функция принимает наибольшее (наименьшее) значение',
       invariant='на отрезке f′ сохраняет знак или меняет его один раз в нужную сторону; по монотонности f выбираем конец отрезка или точку экстремума.',
       varies='область, отрезок, наибольшее или наименьшее, знак производной на отрезке',
       answer_rule='f′ > 0 — функция возрастает (наибольшее на правом конце), f′ < 0 — убывает; при смене знака + → − наибольшее в нуле f′',
       fipi=r'производной функции .*В какой точке отрезка',
       mistakes=['выбирают точку, где f′ наибольшая', 'путают возрастание f и положение графика f′ выше/ниже'],
       svg=True, kim=kim(KIM9, kes=['4.2']))
def gen_ep09_dg_segmax(r):
    st = _dgraph_setup(r, 2, 4)
    if not st:
        return None
    a, b, zeros, touches, sign, fn = st
    kinds = dict(_kinds_at(zeros, touches, sign, b))
    want = r.choice(['max', 'min'])
    c = r.randint(a + 1, b - 3)
    d = r.randint(c + 2, min(b - 1, c + 6))
    inside = [z for z in zeros if c <= z <= d]
    if any(t in (c, d) for t in zeros + touches):
        return None
    if not inside:
        pos = fn((c + d) / 2 + 0.01 * 0) > 0 if all(abs((c + d) / 2 - t) > 0.3 for t in touches) else fn(c + 0.3) > 0
        ans = (d if pos else c) if want == 'max' else (c if pos else d)
    elif len(inside) == 1 and kinds[inside[0]] == want:
        ans = inside[0]
    else:
        return None
    svg = _fsvg(fn, a, b, -4, 4, name=DG, ticks=(a, b))
    word = 'наибольшее' if want == 'max' else 'наименьшее'
    sg = fm(f'[{tnum(c)}; {tnum(d)}]')
    word_ = 'наибольшего' if want == 'max' else 'наименьшего'
    q = dq_intro(a, b, r) + ' ' + pick(r, f'При каком значении x из отрезка {sg} функция {fm("f(x)")} достигает {word_} значения?',
                                       f'Укажите точку отрезка {sg}, в которой значение функции {fm("f(x)")} {word[:-2]}ее.',
                                       f'Найдите ту точку отрезка {sg}, где функция {fm("f(x)")} принимает своё {word} на этом отрезке значение.')
    ex = f'На отрезке [{tnum(c)}; {tnum(d)}] по знаку f′ определяем монотонность f; {word} значение — в точке {tnum(ans)}.'

    def chk():
        # численно интегрируем f′ от c: F(x) = f(x) − f(c); ищем точку наибольшего/наименьшего значения
        n = 2000
        h = (d - c) / n
        acc, best, bx, vals = 0.0, 0.0, c, [(c, 0.0)]
        for i in range(1, n + 1):
            x = c + i * h
            acc += (fn(x - h) + fn(x)) * h / 2
            vals.append((x, acc))
        pick_ = max(vals, key=lambda t: t[1]) if want == 'max' else min(vals, key=lambda t: t[1])
        return abs(pick_[0] - ans) < 0.02
    return pcard(q, num(ans), ex, svg=svg), chk


SUBN = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
NUMW = {6: 'шесть', 7: 'семь', 8: 'восемь', 9: 'девять', 10: 'десять', 11: 'одиннадцать', 12: 'двенадцать'}


def _marks(r, a, b, avoid, cnt, gap=0.45):
    """cnt отмеченных абсцисс (кратных 0,5) внутри (a; b), далеко от точек avoid."""
    cand = [F(k, 2) for k in range(2 * a + 1, 2 * b) if all(abs(F(k, 2) - t) >= gap for t in avoid)]
    if len(cand) < cnt:
        return None
    for _ in range(40):
        xs = sorted(r.sample(cand, cnt))
        if all(q - p >= F(1, 1) for p, q in zip(xs, xs[1:])):
            return xs
    return None


@proto('ep09-dg-marked', 'ege-prof', 9, 'График производной с отмеченными точками: сколько точек на промежутках возрастания (убывания)',
       invariant='f возрастает там, где f′ > 0 (график f′ выше оси), убывает там, где f′ < 0; считаем отмеченные точки.',
       varies='график, число отмеченных точек (6–12), возрастание или убывание',
       answer_rule='число отмеченных точек, где f′ > 0 (или f′ < 0)',
       fipi=r'производной функции f ?\(? ?x ?\)? ?\. На оси абсцисс отмечено',
       mistakes=['смотрят, растёт ли сам график f′, а не его знак', 'считают точки, где f′ возрастает'],
       svg=True, kim=kim(KIM9, kes=['4.2']))
def gen_ep09_dg_marked(r):
    st = _dgraph_setup(r, 3, 5)
    if not st:
        return None
    a, b, zeros, touches, sign, fn = st
    cnt = r.randint(6, min(12, b - a - 1))
    xs = _marks(r, a, b, zeros + touches, cnt)
    if not xs:
        return None
    raw = lambda x: sign * math.prod(x - z for z in zeros) * math.prod((x - d) ** 2 for d in touches)
    want = r.choice(['inc', 'dec'])
    ans = sum(1 for x in xs if (raw(float(x)) > 0) == (want == 'inc'))
    names = [f'x{str(i + 1).translate(SUBN)}' for i in range(cnt)]
    svg = _fsvg(fn, a, b, -4, 4, name=DG, marks=[(float(x), nm) for x, nm in zip(xs, names)], open_ends=False)
    word = 'возрастания' if want == 'inc' else 'убывания'
    pts = ', '.join(names)
    verb = 'возрастает' if want == 'inc' else 'убывает'
    q = pick(r, f'На рисунке показан график производной {fm("y = f′(x)")} некоторой функции {fm("f(x)")}; на оси абсцисс отмечены точки {pts}. '
                f'Сколько из отмеченных точек лежит на промежутках, где функция {fm("f(x)")} {verb}?',
             f'Дан график производной {fm("y = f′(x)")} функции {fm("f(x)")} (см. рисунок), на оси абсцисс отмечены {cnt} {plural(cnt, "точка", "точки", "точек")}: {pts}. '
             f'В скольких из них функция {fm("f(x)")} {verb}?')
    ex = f'f {"возрастает" if want == "inc" else "убывает"} там, где f′ {">" if want == "inc" else "<"} 0; таких отмеченных точек {ans}.'
    return pcard(q, num(ans), ex, svg=svg), lambda: ans == sum(1 for x in xs if (fn(float(x)) > 0) == (want == 'inc'))


@proto('ep09-dg-longest', 'ege-prof', 9, 'График производной: длина наибольшего промежутка возрастания (убывания)',
       invariant='промежутки возрастания f — где f′ ≥ 0; касание оси без смены знака промежуток не разрывает; берём самый длинный.',
       varies='график f′, касания оси, возрастание или убывание',
       answer_rule='наибольшая длина промежутка между соседними сменами знака (или концами интервала)',
       fipi=r'длину наибольшего (из )?(промежутк|интервал)',
       mistakes=['разрывают промежуток в точке касания', 'путают возрастание f с возрастанием f′'],
       svg=True, kim=kim(KIM9, kes=['4.2'], style='классическая формулировка открытого банка прошлых лет: «Найдите длину наибольшего промежутка возрастания»'))
def gen_ep09_dg_longest(r):
    st = _dgraph_setup(r, 2, 4)
    if not st:
        return None
    a, b, zeros, touches, sign, fn = st
    want = r.choice(['inc', 'dec'])
    pts = [a] + zeros + [b]
    raw = lambda x: sign * math.prod(x - z for z in zeros)
    lens = [q_ - p_ for p_, q_ in zip(pts, pts[1:]) if (raw((p_ + q_) / 2) > 0) == (want == 'inc')]
    if not lens or lens.count(max(lens)) > 1 and False:
        return None
    ans = max(lens)
    svg = _fsvg(fn, a, b, -4, 4, name=DG, ticks=(a, b))
    word = 'возрастания' if want == 'inc' else 'убывания'
    q = dq_intro(a, b, r) + ' ' + pick(r, f'Найдите длину самого длинного промежутка {word} функции {fm("f(x)")}.',
                                       f'Функция {fm("f(x)")} {"возрастает" if want == "inc" else "убывает"} на нескольких промежутках. Какова длина наибольшего из них?')
    ex = f'f {"возрастает" if want == "inc" else "убывает"} на промежутках, где f′ {"≥" if want == "inc" else "≤"} 0; длины: {", ".join(map(str, lens))}; наибольшая {ans}.'

    def chk():
        ch = [x for x, _ in sign_changes(fn, a + 1e-6, b - 1e-6)]
        bb = [a] + ch + [b]
        ls = [q_ - p_ for p_, q_ in zip(bb, bb[1:]) if (fn((p_ + q_) / 2) > 0) == (want == 'inc')]
        return abs(max(ls) - ans) < 0.02
    return pcard(q, num(ans), ex, svg=svg), chk


@proto('ep09-dg-parallel', 'ege-prof', 9, 'График производной: число точек, где касательная параллельна прямой y = kx + m',
       invariant='касательная параллельна прямой y = kx + m там, где f′(x) = k: считаем пересечения графика f′ с горизонталью y = k.',
       varies='график f′, прямая (угловой коэффициент k — целое число, в том числе 0 и отрицательное)',
       answer_rule='число решений f′(x) = k на интервале',
       fipi=r'касательная к графику функции f ?\(? ?x ?\)? ?параллельна',
       mistakes=['считают точки пересечения графика f′ с самой прямой y = kx + m', 'ищут f′(x) = m вместо k'],
       svg=True, kim=kim(KIM9, kes=['4.1', '4.2']))
def gen_ep09_dg_parallel(r):
    ab = _domain(r)
    if not ab:
        return None
    a, b = ab
    # опорные точки: экстремумы графика f′ в полуцелых точках, значения далеко от k
    k = r.choice([-2, -1, 0, 1, 2])
    n = r.randint(4, 7)
    xs = sorted(r.sample([F(v, 2) for v in range(2 * a, 2 * b + 1)], n))
    if xs[0] != a:
        xs = [F(a)] + xs
    if xs[-1] != b:
        xs = xs + [F(b)]
    if any(q_ - p_ < 1 for p_, q_ in zip(xs, xs[1:])):
        return None
    ys, up = [], r.choice([True, False])
    for i in range(len(xs)):
        off = r.uniform(0.6, 2.6)
        ys.append(k + off if up else k - off)
        if r.random() < 0.8:
            up = not up
    if any(abs(y) > 3.8 for y in ys):
        return None
    fn = _spline([float(x) for x in xs], ys)
    ans = sum(1 for y1, y2 in zip(ys, ys[1:]) if (y1 - k) * (y2 - k) < 0)
    m = r.choice([v for v in range(-9, 10) if v])
    svg = _fsvg(fn, a, b, -4, 4, name=DG, ticks=(a, b))
    line = f'y = {lin(k, m)}' if k else f'y = {tnum(m)}'
    q = dq_intro(a, b, r) + ' ' + pick(r, f'В скольких точках касательная к графику функции {fm("f(x)")} параллельна прямой {fm(line)} или совпадает с ней?',
                                       f'Сколько существует точек графика функции {fm("f(x)")}, касательная в которых параллельна прямой {fm(line)} или совпадает с ней?')
    ex = f'Угловой коэффициент касательной равен f′(x₀), значит нужно f′(x) = {tnum(k)}; прямая y = {tnum(k)} пересекает график f′ в {ans} {plural(ans, "точке", "точках", "точках")}.'

    def chk():
        cnt, prev = 0, None
        for i in range(1, 4000):
            x = a + (b - a) * i / 4000
            s_ = fn(x) - k > 0
            if prev is not None and s_ != prev:
                cnt += 1
            prev = s_
        return cnt == ans
    return pcard(q, num(ans), ex, svg=svg), chk


# ---------- графики самой функции


def _fcurve(r, a, b, ext_xs):
    """График f на [a; b]: экстремумы ровно в ext_xs (целые), значения чередуются."""
    xs = [float(a)] + [float(x) for x in ext_xs] + [float(b)]
    up = r.choice([True, False])
    ys = []
    base = r.uniform(-1.0, 1.0)
    for i in range(len(xs)):
        ys.append(base + (r.uniform(1.0, 3.0) if up else -r.uniform(1.0, 3.0)))
        up = not up
    # концы — продолжение монотонности
    ys[0] = ys[1] + (r.uniform(0.8, 2.0) if ys[1] < ys[2] else -r.uniform(0.8, 2.0)) if len(xs) > 2 else ys[0]
    ys[-1] = ys[-2] + (r.uniform(0.8, 2.0) if ys[-2] < ys[-3] else -r.uniform(0.8, 2.0)) if len(xs) > 2 else ys[-1]
    if any(abs(y) > 4.5 for y in ys):
        return None
    return _spline(xs, ys), xs, ys


def _deriv(fn, x, h=1e-5):
    return (fn(x + h) - fn(x - h)) / (2 * h)


@proto('ep09-fg-sign', 'ege-prof', 9, 'График функции с отмеченными точками: где производная положительна (отрицательна)',
       invariant='f′ > 0 там, где функция возрастает, f′ < 0 — где убывает; считаем отмеченные точки на нужных участках.',
       varies='график f, число отмеченных точек (6–11), знак производной',
       answer_rule='число отмеченных точек на участках возрастания (или убывания)',
       fipi=r'изображён график функции y = f ?\(? ?x ?\)? ?\. На оси абсцисс отмечено',
       mistakes=['считают точки, где сама функция положительна', 'путают возрастание и убывание'],
       svg=True, kim=kim(KIM9, kes=['4.1', '4.2']))
def gen_ep09_fg_sign(r):
    ab = _domain(r)
    if not ab:
        return None
    a, b = ab
    ext = _zeros(r, a, b, r.randint(3, 5))
    if not ext:
        return None
    res = _fcurve(r, a, b, ext)
    if not res:
        return None
    fn, xs, ys = res
    cnt = r.randint(6, min(11, b - a - 1))
    mk = _marks(r, a, b, ext, cnt, gap=0.5)
    if not mk:
        return None
    want = r.choice(['pos', 'neg'])
    # знак производной на участке — по опорным значениям (сплайн монотонен между ними)
    seg_sign = lambda x: next((1 if ys[i + 1] > ys[i] else -1) for i in range(len(xs) - 1) if xs[i] <= x <= xs[i + 1])
    ans = sum(1 for x in mk if (seg_sign(float(x)) > 0) == (want == 'pos'))
    names = [f'x{str(i + 1).translate(SUBN)}' for i in range(cnt)]
    svg = _fsvg(fn, a, b, -5, 5, name='y = f(x)', marks=[(float(x), nm) for x, nm in zip(mk, names)], open_ends=False)
    word = 'положительна' if want == 'pos' else 'отрицательна'
    pts = ', '.join(names)
    sgn_ = '>' if want == 'pos' else '<'
    q = pick(r, f'На рисунке показан график функции {fm("y = f(x)")}, на оси Ox отмечены точки {pts}. '
                f'В скольких из этих точек производная {fm("f′(x)")} {word}?',
             f'Дан график функции {fm("y = f(x)")} (см. рисунок); на оси Ox отмечены точки {pts}. Сколько среди них точек, в которых {fm(f"f′(x) {sgn_} 0")}?',
             f'По графику функции {fm("y = f(x)")} определите, во скольких из отмеченных точек {pts} значение производной {word}.')
    ex = f'Производная {word} там, где функция {"возрастает" if want == "pos" else "убывает"}; таких отмеченных точек {ans}.'
    return pcard(q, num(ans), ex, svg=svg), lambda: ans == sum(1 for x in mk if (_deriv(fn, float(x)) > 0) == (want == 'pos'))


@proto('ep09-fg-which', 'ege-prof', 9, 'График функции: в какой из отмеченных точек производная наибольшая (наименьшая)',
       invariant='из четырёх отмеченных точек только в одной функция возрастает (убывает), в остальных убывает (возрастает) или стоит в вершине; знак производной решает.',
       varies='график, отмеченные абсциссы, наибольшее или наименьшее значение производной',
       answer_rule='для наибольшего f′ — точка на участке возрастания; для наименьшего — на участке убывания',
       fipi=r'В какой из этих точек значение производной',
       mistakes=['выбирают точку, где наибольшее значение самой функции', 'выбирают вершину'],
       svg=True, kim=kim(KIM9, kes=['4.1']))
def gen_ep09_fg_which(r):
    ab = _domain(r)
    if not ab:
        return None
    a, b = ab
    ext = _zeros(r, a, b, r.randint(3, 4), gap=3)
    if not ext:
        return None
    res = _fcurve(r, a, b, ext)
    if not res:
        return None
    fn, xs, ys = res
    want = r.choice(['max', 'min'])
    # участки монотонности между опорными точками; берём точки не ближе 1 к концам участка
    def piece(x):
        for i in range(len(xs) - 1):
            if xs[i] + 1 <= x <= xs[i + 1] - 1:
                return 1 if ys[i + 1] > ys[i] else -1
        return 0
    ints = [x for x in range(a + 1, b) if x != 0]
    need = 1 if want == 'max' else -1
    good = [x for x in ints if piece(x) == need]
    other = [x for x in ints if x in ext or piece(x) == -need]
    if not good or len(other) < 3:
        return None
    ans = r.choice(good)
    pts = sorted([ans] + r.sample(other, 3))
    svg = _fsvg(fn, a, b, -5, 5, name='y = f(x)', marks=[(float(x), tnum(x)) for x in pts], open_ends=False)
    word = 'наибольшее' if want == 'max' else 'наименьшее'
    ps = ', '.join(tnum(x) for x in pts[:-1]) + ' и ' + tnum(pts[-1])
    q = pick(r, f'На рисунке показан график функции {fm("y = f(x)")}; четыре точки на оси Ox имеют абсциссы {ps}. '
                f'Укажите ту из них, в которой производная {fm("f′(x)")} принимает {word} значение.',
             f'Дан график функции {fm("y = f(x)")} (см. рисунок). Среди четырёх точек оси Ox с абсциссами {ps} найдите ту, где значение {fm("f′(x)")} {word}. '
             f'В ответ запишите абсциссу этой точки.')
    ex = (f'Только в точке {tnum(ans)} функция {"возрастает (f′ > 0)" if want == "max" else "убывает (f′ < 0)"}; '
          f'в остальных f′ {"≤" if want == "max" else "≥"} 0.')

    def chk():
        ds = {x: _deriv(fn, float(x)) for x in pts}
        best = max(ds, key=ds.get) if want == 'max' else min(ds, key=ds.get)
        rest = [v for x, v in ds.items() if x != best]
        return best == ans and (ds[best] > 0.05 >= max(rest) if want == 'max' else ds[best] < -0.05 <= min(rest))
    return pcard(q, num(ans), ex, svg=svg), chk


@proto('ep09-fg-zeros', 'ege-prof', 9, 'Нули производной по графику функции (или нули f по графику первообразной)',
       invariant='f′(x) = 0 в точках экстремума гладкой функции (касательная горизонтальна); для графика первообразной F: f = F′, нули f — экстремумы F.',
       varies='график, отрезок, вопрос (сколько корней на отрезке / найдите корень / сколько точек с горизонтальной касательной), функция или первообразная',
       answer_rule='число (или абсцисса) вершин графика на отрезке',
       fipi=r'корней уравнения f ′ ?\(? ?x ?\)? ?= 0|корень уравнения f ′|одной из первообразных',
       mistakes=['считают нули самой функции (пересечения с осью Ox)', 'не учитывают границы отрезка'],
       svg=True, kim=kim(KIM9, kes=['4.1', '4.2', '4.3']))
def gen_ep09_fg_zeros(r):
    ab = _domain(r)
    if not ab:
        return None
    a, b = ab
    ext = _zeros(r, a, b, r.randint(2, 6))
    if not ext:
        return None
    res = _fcurve(r, a, b, ext)
    if not res:
        return None
    fn, xs, ys = res
    prim = r.random() < 0.35
    kind = r.choice(['count', 'count', 'one', 'horiz'])
    if kind == 'one':
        if len(ext) != 1 and not prim:
            c, d = None, None
            # «найдите корень» — только если экстремум единственный на отрезке
            c = r.randint(a, b - 2)
            d = r.randint(c + 2, b)
            inside = [e for e in ext if c < e < d]
            if len(inside) != 1 or c in ext or d in ext:
                return None
            ans = inside[0]
        else:
            if len(ext) != 1:
                return None
            c, d = a, b
            ans = ext[0]
    else:
        if r.random() < 0.3:
            c, d = a, b
        else:
            c = r.randint(a + 1, b - 3)
            d = r.randint(c + 2, b - 1)
        if c in ext or d in ext:
            return None
        ans = sum(1 for e in ext if c < e < d)
    seg = '' if (c, d) == (a, b) else f', принадлежащих отрезку {fm(f"[{tnum(c)}; {tnum(d)}]")}'
    seg1 = '' if (c, d) == (a, b) else f', принадлежащий отрезку {fm(f"[{tnum(c)}; {tnum(d)}]")}'
    iv = fm(f'({tnum(a)}; {tnum(b)})')
    intro = (pick(r, f'Функция {fm("F(x)")}, заданная на интервале {iv}, — первообразная некоторой функции {fm("f(x)")}; её график показан на рисунке.',
                  f'На рисунке показан график функции {fm("y = F(x)")}, заданной на интервале {iv}. Известно, что {fm("F(x)")} — одна из первообразных функции {fm("f(x)")}.')
             if prim else
             pick(r, f'На рисунке показан график функции {fm("y = f(x)")}, заданной на интервале {iv}.',
                  f'Функция {fm("y = f(x)")} определена на интервале {iv}; её график изображён на рисунке.'))
    eq = 'f(x) = 0' if prim else 'f′(x) = 0'
    where = f' на отрезке {fm(f"[{tnum(c)}; {tnum(d)}]")}' if (c, d) != (a, b) else ''
    if kind == 'one':
        q = f'{intro} ' + (f'Уравнение {fm(eq)} имеет{where} единственный корень. Найдите его.' if where else f'Уравнение {fm(eq)} имеет единственный корень. Найдите его.')
    elif kind == 'horiz' and not prim:
        q = f'{intro} В скольких точках{where} касательная к графику горизонтальна (параллельна оси абсцисс или совпадает с ней)?'
    else:
        q = f'{intro} ' + pick(r, f'Сколько корней имеет уравнение {fm(eq)}{where}?', f'Определите число решений уравнения {fm(eq)}{where}.')
    svg = _fsvg(fn, a, b, -5, 5, name='y = F(x)' if prim else 'y = f(x)', ticks=(a, b))
    ex = (f'{"f = F′, поэтому " if prim else ""}корни уравнения {eq} — абсциссы точек экстремума (вершин) графика'
          f'{"" if kind != "one" else ""}; ответ {tnum(ans)}.')

    def chk():
        d_ = lambda x: _deriv(fn, x)
        ch = sign_changes(d_, c + 1e-3, d - 1e-3, n=3000)
        return (len(ch) == 1 and abs(ch[0][0] - ans) < 0.02) if kind == 'one' else len(ch) == ans
    return pcard(q, num(ans), ex, svg=svg), chk


@proto('ep09-tangent', 'ege-prof', 9, 'Касательная к графику: значение производной в точке касания',
       invariant='f′(x₀) равно угловому коэффициенту касательной; его находим по двум узлам сетки на касательной: Δy/Δx.',
       varies='положение касательной и узлов, знак и величина наклона (целый или дробный), вид графика',
       answer_rule='k = (y₂ − y₁)/(x₂ − x₁)',
       fipi=r'касательная к нему в точке с абсциссой',
       mistakes=['берут Δx/Δy', 'теряют знак при убывающей касательной', 'считают клетки не от узлов'],
       svg=True, kim=kim(KIM9, kes=['4.1'], style='как в КИМ: график функции и касательная в точке x₀, «Найдите значение производной функции f(x) в точке x₀»; ответ может быть дробным (−0,2)'))
def gen_ep09_tangent(r):
    dx = r.choice([1, 2, 2, 3, 4, 4, 5, 6, 8])
    dy = r.choice([v for v in range(-6, 7) if v])
    k = F(dy, dx)
    if not nice(k, 2) or abs(k) > 4:
        return None
    x1 = r.randint(-6, 4)
    x2 = x1 + dx
    y1 = r.randint(-4, 5)
    y2 = y1 + dy
    if x2 > 8 or not -5 <= y2 <= 6:
        return None
    xt = r.choice([x1 + dx / 2, x1 + 0.5, x2 - 0.5, x1 - 1, x2 + 1]) if dx > 1 else r.choice([x1 - 1, x2 + 1, x1 + 0.5])
    xt = float(xt)
    line = lambda x: y1 + float(k) * (x - x1)
    c2 = r.choice([1, -1]) * r.uniform(0.12, 0.3)
    c3 = r.uniform(-0.03, 0.03)
    fn = lambda x: line(x) + c2 * (x - xt) ** 2 + c3 * (x - xt) ** 3
    X0, X1 = min(x1, xt, 0) - 3, max(x2, xt, 0) + 3
    ys = [y1, y2, line(xt), 0]
    Y0, Y1 = min(ys) - 2, max(ys) + 2
    if Y1 - Y0 < 7:
        Y1 = Y0 + 7
    yt = line(xt)
    if not (Y0 + 0.5 < yt < Y1 - 0.5):
        return None
    vis = sum(1 for i in range(41) if Y0 < fn(X0 + (X1 - X0) * i / 40) < Y1)
    if vis < 22:
        return None

    def extra(sx, sy):
        tl = f'<line x1="{sx(X0):.1f}" y1="{sy(line(X0)):.1f}" x2="{sx(X1):.1f}" y2="{sy(line(X1)):.1f}" stroke="{RED}" stroke-width="1.8"/>'
        dots = ''.join(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="3.6" fill="{INK}"/>' for x, y in ((x1, y1), (x2, y2)))
        guide = f'<line x1="{sx(xt):.1f}" y1="{sy(yt):.1f}" x2="{sx(xt):.1f}" y2="{sy(0):.1f}" stroke="{INK}" stroke-dasharray="3 3"/>'
        lab = f'<text x="{sx(xt) - 6:.1f}" y="{sy(0) + (14 if yt >= 0 else -6):.1f}" font-style="italic">x₀</text>'
        nm = f'<text x="{sx(X0) + 6:.1f}" y="{sy(Y1) + 14:.1f}" font-style="italic">y = f(x)</text>'
        return tl + guide + dots + lab + nm
    svg = svg_plot(fn, X0, X1, Y0, Y1, extra=extra, width=340)
    q = pick(r, f'К графику функции {fm("y = f(x)")} в точке с абсциссой {fm("x₀")} проведена касательная (см. рисунок). Найдите {fm("f′(x₀)")}.',
             f'На рисунке показаны график функции {fm("y = f(x)")} и прямая, касающаяся его в точке с абсциссой {fm("x₀")}. Чему равно значение производной {fm("f′(x₀)")}?',
             f'Прямая на рисунке касается графика функции {fm("y = f(x)")} в точке с абсциссой {fm("x₀")}. Найдите значение производной функции в этой точке.')
    ex = f'Касательная проходит через узлы ({tnum(x1)}; {tnum(y1)}) и ({tnum(x2)}; {tnum(y2)}): f′(x₀) = {tnum(dy)}/{dx} = {tnum(k)}.'
    return pcard(q, num(k), ex, svg=svg), lambda: abs(_deriv(fn, xt) - float(k)) < 1e-6 and abs(fn(xt) - yt) < 1e-9


@proto('ep09-prim-area', 'ege-prof', 9, 'Первообразная: F(d) − F(c) по графику f (площадь под ломаной)',
       invariant='F(d) − F(c) = ∫ f(x)dx от c до d — площадь под графиком f (ломаная по узлам сетки), считаем по трапециям и треугольникам.',
       varies='ломаная, отрезок интегрирования',
       answer_rule='сумма площадей трапеций под графиком',
       fipi=r'первообразн',
       mistakes=['вычисляют f(d) − f(c)', 'ошибаются в подсчёте клеток у наклонных участков'],
       svg=True, kim=kim(KIM9, kes=['4.3'], style='формулировка открытого банка прошлых лет: «На рисунке изображён график функции y = f(x). Пользуясь рисунком, вычислите F(d) − F(c), где F(x) — одна из первообразных функции f(x)»'))
def gen_ep09_prim_area(r):
    c = r.randint(-5, 3)
    d = c + r.randint(4, 9)
    n = r.randint(2, 4)
    inner = sorted(r.sample(range(c + 1, d), n - 1))
    xs = [c] + inner + [d]
    ys = [r.randint(0, 5) for _ in xs]
    if sum(ys) == 0 or all(y == ys[0] for y in ys):
        return None
    a, b = c - r.randint(1, 2), d + r.randint(1, 2)
    xs2 = [a] + xs + [b]
    ys2 = [r.randint(0, 5)] + ys + [r.randint(0, 5)]
    area = sum(F(ys2[i] + ys2[i + 1], 2) * (xs2[i + 1] - xs2[i]) for i in range(len(xs2) - 1) if c <= xs2[i] and xs2[i + 1] <= d)

    def fn(x):
        for i in range(len(xs2) - 1):
            if xs2[i] <= x <= xs2[i + 1]:
                t = (x - xs2[i]) / (xs2[i + 1] - xs2[i])
                return ys2[i] + t * (ys2[i + 1] - ys2[i])
        raise ValueError
    svg = _fsvg(fn, a, b, -1, 6, name='y = f(x)', ticks=(c, d), open_ends=False)
    q = pick(r, f'По графику функции {fm("y = f(x)")}, изображённому на рисунке, найдите {fm(f"F({tnum(d)}) − F({tnum(c)})")}, '
                f'где {fm("F(x)")} — какая-нибудь первообразная функции {fm("f(x)")}.',
             f'На рисунке показан график функции {fm("y = f(x)")}; {fm("F(x)")} — одна из её первообразных. '
             f'Вычислите разность {fm(f"F({tnum(d)}) − F({tnum(c)})")}.')
    ex = f'F({tnum(d)}) − F({tnum(c)}) равно площади под графиком f на отрезке [{tnum(c)}; {tnum(d)}]: {tnum(area)}.'

    def chk():
        N = 6000
        h = (d - c) / N
        return abs(sum((fn(c + i * h) + fn(c + (i + 1) * h)) * h / 2 for i in range(N)) - float(area)) < 1e-6
    return pcard(q, num(area), ex, svg=svg), chk


@proto('ep09-prim-formula', 'ege-prof', 9, 'Первообразная задана формулой: площадь закрашенной фигуры',
       invariant='площадь под графиком f (f ≥ 0) на [c; d] равна F(d) − F(c), где F — данная первообразная; границы читаются с рисунка.',
       varies='первообразная (многочлен третьей степени), границы фигуры',
       answer_rule='F(d) − F(c)',
       fipi=r'площадь закрашенной фигуры',
       mistakes=['считают F(c) − F(d)', 'подставляют границы в f, а не в F'],
       svg=True, kim=kim(KIM9, kes=['4.3']))
def gen_ep09_prim_formula(r):
    # f(x) = s(x − p)² + t ≥ 0 на [c; d]; F — первообразная с целыми коэффициентами при s = ±1, 3
    s = r.choice([1, 1, 3, -1])
    p = r.randint(-4, 2)
    t = r.randint(1, 5) if s > 0 else r.randint(5, 12)
    c = r.randint(p - 3, p)
    d = r.randint(c + 1, c + 4)
    f_ = lambda x: s * (x - p) ** 2 + t
    if min(f_(x / 10) for x in range(10 * c, 10 * d + 1)) < 0.5 or max(f_(c), f_(d), f_(p)) > 7:
        return None
    C0 = r.randint(-9, 9)
    # F(x) = s(x − p)³/3 + t x + C0 = раскрытый многочлен
    x = sp.Symbol('x')
    Fx = sp.expand(sp.Rational(s, 3) * (x - p) ** 3 + t * x + C0)
    coefs = [F(str(sp.Poly(Fx, x).coeff_monomial(x ** k))) for k in (3, 2, 1, 0)]
    if any(cf.denominator != 1 for cf in coefs[1:]) or coefs[0] not in (F(1, 3), F(1), F(-1, 3)):
        return None
    ans = F(str(Fx.subs(x, d) - Fx.subs(x, c)))
    if not nice(ans, 2):
        return None
    lead = {F(1, 3): 'x³/3', F(1): 'x³', F(-1, 3): '−x³/3'}[coefs[0]]
    Ftxt = lead + ''.join(signed(cf) + v for cf, v in zip(coefs[1:], ('x²', 'x', '')) if cf).replace(' + 1x', ' + x').replace(' − 1x', ' − x')
    fl = lambda xx: f_(xx)
    a, b = min(c - 2, p - 3), max(d + 2, p + 3)
    Y1 = min(8, math.ceil(max(f_(c), f_(d), t) + 1))

    def extra(sx, sy):
        pts = [f'{sx(c):.1f},{sy(0):.1f}'] + [f'{sx(c + (d - c) * i / 60):.1f},{sy(f_(c + (d - c) * i / 60)):.1f}' for i in range(61)] + [f'{sx(d):.1f},{sy(0):.1f}']
        return f'<polygon points="{" ".join(pts)}" fill="{BLUE}" fill-opacity="0.25" stroke="none"/>'
    svg = _fsvg(fl, a, b, -2, Y1, name='y = f(x)', ticks=(c, d), extra=extra, open_ends=False)
    q = (f'На рисунке изображён график некоторой функции {fm("y = f(x)")}. Функция {fm(f"F(x) = {Ftxt}")} — одна из первообразных '
         f'функции {fm("f(x)")}. Найдите площадь закрашенной фигуры.')
    ex = f'Фигура ограничена графиком f и осью Ox на отрезке [{tnum(c)}; {tnum(d)}]; S = F({tnum(d)}) − F({tnum(c)}) = {tnum(ans)}.'

    def chk():
        fx = sp.diff(Fx, x)
        okpos = all(fx.subs(x, sp.Rational(c * 20 + i * (d - c), 20)) > 0 for i in range(21))
        return okpos and sp.integrate(fx, (x, c, d)) == R(ans)
    return pcard(q, num(ans), ex, svg=svg), chk


# ---------- производная без рисунка: физический смысл, касательная


T = sp.Symbol('t', real=True)

MOTION = [
    ('Тело движется вдоль прямой, и его координата x (в метрах) меняется по закону {f}, где t — время в секундах от начала наблюдения.',
     'x(t)', 'скорость тела'),
    ('Вагонетка катится по прямолинейному рельсовому пути. Её расстояние от начала пути (в метрах) зависит от времени t (в секундах) так: {f}.',
     'x(t)', 'скорость вагонетки'),
    ('Квадрокоптер поднимается вертикально, и его высота над площадкой (в метрах) через t секунд после старта равна {f}.',
     'h(t)', 'вертикальная скорость квадрокоптера'),
    ('Поршень насоса движется вдоль оси цилиндра; его смещение (в сантиметрах) от крайнего положения через t секунд после включения описывается формулой {f}.',
     's(t)', 'скорость поршня'),
    ('Робот-пылесос едет по прямой линии вдоль стены. Его расстояние от зарядной станции (в метрах) через t секунд после начала движения равно {f}.',
     'x(t)', 'скорость робота'),
]


@proto('ep09-motion', 'ege-prof', 9, 'Физический смысл производной: скорость по закону движения',
       invariant='скорость — производная координаты по времени: v(t) = x′(t); находим v(t₀) или момент, когда v(t) = v₀.',
       varies='закон движения (многочлен до 3-й степени, иногда с дробными коэффициентами), сюжет (тело, вагонетка, квадрокоптер, поршень, робот), вопрос (скорость в момент или момент по скорости)',
       answer_rule='v(t₀) = x′(t₀) или положительный корень уравнения x′(t) = v₀',
       fipi=r'движется прямолинейно по закону',
       mistakes=['подставляют t₀ в сам закон x(t)', 'берут отрицательный корень для времени'],
       kim=kim(KIM9, kes=['4.1'], style='формулировка открытого банка прошлых лет «… по закону x(t) = …, где t — время в секундах. Найдите её скорость (в м/с) в момент времени t = … с»'))
def gen_ep09_motion(r):
    a3 = r.choice([F(1, 3), F(1, 3), F(1), F(-1, 3), F(1, 2), F(2)])
    a2 = F(r.randint(-8, 8), r.choice([1, 1, 2]))
    a1 = r.randint(-20, 30)
    a0 = r.randint(0, 40)
    story, sym, what = r.choice(MOTION)
    unit = 'см/с' if sym == 's(t)' else 'м/с'
    law = f'{sym} = {poly([a3, a2, a1, a0], "t")}'.replace('1/3t³', 't³/3').replace('−1/3t³', '−t³/3').replace('1/2t²', 't²/2')
    law = law.replace('(1/3)', '')
    xt = R(a3) * T ** 3 + R(a2) * T ** 2 + a1 * T + a0
    if r.random() < 0.55:
        t0 = r.randint(1, 10)
        v = 3 * a3 * t0 ** 2 + 2 * a2 * t0 + a1
        if not nice(v, 1) or v <= 0 or v > 300:
            return None
        q = story.format(f=fm(law)) + f' Найдите {what} (в {unit}) в момент времени {fm(f"t = {t0}")} с.'
        ex = f'v(t) = {sym[0]}′(t) = {poly([3 * a3, 2 * a2, a1], "t")}; v({t0}) = {tnum(v)} {unit}.'
        return pcard(q, num(v), ex), lambda: sp.diff(xt, T).subs(T, t0) == R(v)
    t1 = r.randint(1, 12)
    v0 = 3 * a3 * t1 ** 2 + 2 * a2 * t1 + a1
    # второй корень v(t) = v0 не должен быть положительным
    other = -2 * a2 / (3 * a3) - t1
    if other > 0 or not nice(v0, 1) or v0 <= 0 or v0 > 300:
        return None
    q = story.format(f=fm(law)) + f' В какой момент времени (в секундах) {what} была равна {tnum(v0)} {unit}?'
    ex = f'v(t) = {poly([3 * a3, 2 * a2, a1], "t")} = {tnum(v0)}; положительный корень t = {t1}.'

    def chk():
        sol = [s_ for s_ in sp.solve(sp.Eq(sp.diff(xt, T), R(v0)), T) if s_.is_real and s_ > 0]
        return len(sol) == 1 and sol[0] == t1
    return pcard(q, num(t1), ex), chk


@proto('ep09-parallel', 'ege-prof', 9, 'Касательная параллельна данной прямой: абсцисса точки касания',
       invariant='у параллельных прямых равные угловые коэффициенты: f′(x₀) = k.',
       varies='квадратичная функция, прямая y = kx + m (m не влияет), порядок слов в условии',
       answer_rule='решаем f′(x) = k',
       fipi=r'параллельна касательной к графику функции',
       mistakes=['приравнивают функцию к прямой', 'используют свободный член m'],
       kim=kim(KIM9, kes=['4.1']))
def gen_ep09_parallel(r):
    a = r.choice([1, 2, 3, -1, -2, F(1, 2), 4, 5])
    b = r.randint(-12, 12)
    c = r.randint(-15, 15)
    x0 = F(r.randint(-12, 12), r.choice([1, 1, 2]))
    k = 2 * a * x0 + b
    m = r.randint(-15, 15)
    if not nice(x0, 1) or k.denominator != 1 or k == 0 or m == c:
        return None
    fx, ln = f'y = {poly([a, b, c])}', f'y = {lin(k, m)}'
    q = pick(r, f'Прямая {fm(ln)} параллельна касательной к графику функции {fm(fx)}. Найдите абсциссу точки касания.',
             f'Касательная к графику функции {fm(fx)} параллельна прямой {fm(ln)}. Найдите абсциссу точки касания.',
             f'В некоторой точке графика функции {fm(fx)} провели касательную, параллельную прямой {fm(ln)}. Найдите абсциссу этой точки.')
    ex = f'y′ = {lin(2 * a, b)}; {lin(2 * a, b)} = {tnum(k)}, x₀ = {tnum(x0)}.'
    return pcard(q, num(x0), ex), one_root(sp.diff(R(a) * X ** 2 + b * X + c, X), sp.Integer(int(k)), num(x0))


@proto('ep09-tangent-line', 'ege-prof', 9, 'Прямая касается графика: абсцисса точки касания или параметр',
       invariant='в точке касания совпадают значения и производные: f(x₀) = kx₀ + m и f′(x₀) = k.',
       varies='функция (кубическая или квадратичная с параметром), прямая, вопрос (абсцисса точки касания или неизвестный коэффициент)',
       answer_rule='система f(x₀) = kx₀ + m, f′(x₀) = k; из корней f′(x) = k выбираем тот, где прямая действительно касается',
       fipi=r'является касательной к графику функции',
       mistakes=['берут любой корень уравнения f′(x) = k без проверки f(x₀) = kx₀ + m', 'забывают второе условие касания'],
       kim=kim(KIM9, kes=['4.1']))
def gen_ep09_tangent_line(r):
    if r.random() < 0.6:
        # y = x³ + px² + qx + s, касание в x0 (целом), угловой коэффициент k
        x0 = r.randint(-4, 4)
        p = r.randint(-6, 6)
        k = r.randint(-12, 12)
        q = k - 3 * x0 ** 2 - 2 * p * x0
        m = r.randint(-15, 15)
        s_ = k * x0 + m - (x0 ** 3 + p * x0 ** 2 + q * x0)
        # другой корень f′(x) = k: x1 = −2p/3 − x0 — там прямая не должна касаться
        fx = X ** 3 + p * X ** 2 + q * X + s_
        x1 = F(-2 * p, 3) - x0
        if x1 == x0 or abs(s_) > 60:
            return None
        if R(x1) ** 3 + p * R(x1) ** 2 + q * R(x1) + s_ == k * R(x1) + m:
            return None
        ln, fs = f'y = {lin(k, m)}' if k else f'y = {tnum(m)}', f'y = {poly([1, p, q, s_])}'
        qq = pick(r, f'Прямая {fm(ln)} является касательной к графику функции {fm(fs)}. Найдите абсциссу точки касания.',
                  f'Прямая {fm(ln)} касается графика функции {fm(fs)}. Найдите абсциссу точки касания.')
        ex = f'y′ = {poly([3, 2 * p, q])} = {tnum(k)} при x = {tnum(x0)} и x = {fr(x1)}; равенство значений выполняется только при x = {tnum(x0)}.'

        def chk():
            sol = sp.solve([sp.Eq(sp.diff(fx, X), k), sp.Eq(fx, k * X + m)], X, dict=True)
            xs = sorted({d[X] for d in sol})
            return xs == [x0]
        return pcard(qq, num(x0), ex), chk
    # y = x² + bx + c касается прямой y = kx + m: найти c
    x0 = r.randint(-6, 6)
    a = r.choice([1, 1, 2, -1, 3])
    b = r.randint(-9, 9)
    k = 2 * a * x0 + b
    m = r.randint(-12, 12)
    c = k * x0 + m - a * x0 ** 2 - b * x0
    if abs(c) > 50 or c == 0:
        return None
    ln = f'y = {lin(k, m)}' if k else f'y = {tnum(m)}'
    fs = f'y = {poly([a, b, 0])} + c'.replace(' + 0', '')
    qq = f'Прямая {fm(ln)} является касательной к графику функции {fm(fs)}. Найдите {fm("c")}.'
    ex = f'y′ = {lin(2 * a, b)} = {tnum(k)} при x₀ = {tnum(x0)}; из равенства значений в x₀ получаем c = {tnum(c)}.'
    cc = sp.Symbol('c')

    def chk2():
        # касание ⇔ дискриминант уравнения ax² + (b − k)x + c − m = 0 равен нулю
        sol = sp.solve(sp.Eq((b - k) ** 2 - 4 * a * (cc - m), 0), cc)
        return sol == [c]
    return pcard(qq, num(c), ex), chk2


# ---------- наибольшее и наименьшее значение, точки экстремума (бывшее задание 12)

NOTE_MM = ('в демоверсии 2027 задание 9 только по графику; по спецификации 2027 (требование 4, КЭС 4.2) '
           'поиск экстремумов и наибольшего/наименьшего значения входит в задание 9')

PT_Q = ['Найдите абсциссу точки {w} функции {f}.', 'В какой точке функция {f} имеет {m}?',
        'Найдите, в какой точке функция {f} достигает {m}а.']


def _fx(r, f):
    """Функцию называем то y = …, то f(x) = …, то g(x) = … (в КИМ — y = …)."""
    return f.replace('y = ', r.choice(['f(x) = ', 'g(x) = ', 'h(x) = ']), 1)


def pt_q(r, w, f):
    return r.choice(PT_Q).format(w=w, f=fm(_fx(r, f)), m=w[:-1])


def crit_check(expr, ans, kind, dom=None):
    """Независимо: sympy находит критические точки и определяет тип по смене знака производной."""
    def chk():
        d = sp.diff(expr, X)
        crit = [c for c in sp.solve(sp.Eq(d, 0), X) if c.is_real and (dom is None or dom(c))]
        good = []
        for c in crit:
            l, rr = d.subs(X, c - sp.Rational(1, 1000)), d.subs(X, c + sp.Rational(1, 1000))
            if (kind == 'max' and l > 0 > rr) or (kind == 'min' and l < 0 < rr):
                good.append(c)
        return len(good) == 1 and same(ans, good[0])
    return chk


@proto('ep09-ext-cubic', 'ege-prof', 9, 'Точка максимума (минимума) многочлена третьей степени',
       invariant='y′ — квадратный трёхчлен с двумя корнями; при положительном старшем коэффициенте максимум в меньшем корне, минимум в большем.',
       varies='коэффициенты (в том числе без x² или без x), корни производной (целый ответ, второй корень может быть дробным), форма записи (раскрытая или (x − a)²(x − b) + c)',
       answer_rule='корень y′ = 0, в котором знак меняется в нужную сторону',
       fipi=r'точку (максимума|минимума) функции y = \(? ?x 3 ',
       mistakes=['путают точку максимума и значение максимума', 'берут не тот корень производной'],
       note=NOTE_MM, kim=kim(KIM9, kes=['4.2'], style='как в КИМ 2026 (№12): «Найдите точку максимума функции y = …»'))
def gen_ep09_ext_cubic(r):
    want = r.choice(['max', 'min'])
    form = r.choice(['exp', 'exp', 'fact'])
    if form == 'fact':
        # y = (x − u)²(x − v) + s: y′ = (x − u)(3x − 2v − u), корни u и (u + 2v)/3
        u, v = r.randint(-9, 9), r.randint(-9, 9)
        w = F(u + 2 * v, 3)
        if u == v:
            return None
        lo, hi = min(F(u), w), max(F(u), w)
        ans = lo if want == 'max' else hi
        if ans.denominator != 1:
            return None
        s_ = r.randint(-15, 15)
        f = f'y = ({lin(1, -u)})²({lin(1, -v)})' + (f' {"+" if s_ > 0 else "−"} {abs(s_)}' if s_ else '')
        f = f.replace('(x)²', 'x²').replace('(x)', 'x')
        expr = (X - u) ** 2 * (X - v) + s_
    else:
        u = r.randint(-15, 15)
        w = F(r.randint(-45, 45), r.choice([1, 3]))
        if (3 * u + 3 * w) % 2 or u == w:
            return None
        # y′ = 3(x − u)(x − w) = 3x² − 3(u + w)x + 3uw → y = x³ − 1,5(u + w)x² + 3uw·x + s
        p, q = F(-3 * (u + w), 2), 3 * u * w
        if p.denominator != 1 or q.denominator != 1 or abs(q) > 400:
            return None
        lo, hi = min(F(u), w), max(F(u), w)
        ans = lo if want == 'max' else hi
        if ans.denominator != 1:
            return None
        s_ = r.randint(-25, 25)
        f = f'y = {poly([1, p, q, s_])}'
        expr = X ** 3 + R(p) * X ** 2 + R(q) * X + s_
    wd = 'максимума' if want == 'max' else 'минимума'
    q_ = pt_q(r, wd, f)
    ex = f'y′ = 0 при x = {fr(lo)} и x = {fr(hi)}; при переходе через x = {tnum(ans)} производная меняет знак с «{"+" if want == "max" else "−"}» на «{"−" if want == "max" else "+"}».'
    return pcard(q_, num(ans), ex), crit_check(expr, num(ans), want)


@proto('ep09-ext-sqrt', 'ege-prof', 9, 'Точка экстремума функции с x√x',
       invariant='y = a + bx − c·x√x: y′ = b − 1,5c√x = 0, откуда √x = 2b/(3c); область x ≥ 0.',
       varies='коэффициенты, знак (максимум или минимум), запись x√x или x^{3/2}',
       answer_rule='x = (2b/(3c))²',
       fipi=r'x √\( x \)|x 3 2',
       mistakes=['считают (x√x)′ = √x', 'забывают возвести в квадрат'],
       note=NOTE_MM, kim=kim(KIM9, kes=['4.2']))
def gen_ep09_ext_sqrt(r):
    s_ = r.randint(2, 15)          # √x₀
    c = r.choice([1, 1, 2, 4, 3])
    b = F(3 * c * s_, 2)
    if b.denominator != 1:
        return None
    a0 = r.randint(-20, 30)
    want = r.choice(['max', 'min'])
    t = r.choice(['x√x', 'x^{3/2}'])
    cx = ('' if c == 1 else str(c)) + t
    if want == 'max':
        f = pick(r, f'y = {a0} + {b}x − {cx}', f'y = {b}x − {cx} {"+" if a0 >= 0 else "−"} {abs(a0)}')
        expr = a0 + b * X - c * X * sp.sqrt(X)
    else:
        f = pick(r, f'y = {cx} − {b}x {"+" if a0 >= 0 else "−"} {abs(a0)}', f'y = {a0} − {b}x + {cx}')
        expr = a0 - b * X + c * X * sp.sqrt(X)
    ans = s_ * s_
    wd = 'максимума' if want == 'max' else 'минимума'
    q = pt_q(r, wd, f)
    ex = f'y′ = {"" if want == "min" else "−"}(1,5·{c}√x − {b}); y′ = 0 при √x = {s_}, x = {ans}.'.replace('1,5·1√x', '1,5√x')
    return pcard(q, num(ans), ex), crit_check(expr, num(ans), want, dom=lambda v: v > 0)


@proto('ep09-ext-ln', 'ege-prof', 9, 'Точка экстремума: линейная функция и логарифм',
       invariant='y = kx − m·ln(x + a) + c: y′ = k − m/(x + a) = 0 → x = m/k − a; учитываем область x > −a.',
       varies='коэффициенты k, m, сдвиг a, запись m·ln(x + a) или ln(x + a)^m, максимум или минимум',
       answer_rule='x = m/k − a',
       fipi=r'точку (максимума|минимума) функции y = .*ln',
       mistakes=['забывают производную сложной функции', 'получают точку вне области определения'],
       note=NOTE_MM, kim=kim(KIM9, kes=['4.2']))
def gen_ep09_ext_ln(r):
    k = r.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    m = r.choice([1, 1, 2, 3, 5, 6, 7, 9, 10, 11, 12])
    a = r.choice([v for v in range(-9, 10) if v])
    x0 = F(m, k) - a
    if not nice(x0, 2) or x0 == 0:
        return None
    c = r.randint(-20, 20)
    want = r.choice(['max', 'min'])
    arg = lin(1, a)
    lnm = pick(r, f'{"" if m == 1 else f"{m}"}ln({arg})', f'ln({arg})^{{{m}}}') if m > 1 else f'ln({arg})'
    lnm = lnm.replace(f'{m}ln', f'{m}·ln') if m > 1 else lnm
    kx = f'{"" if k == 1 else k}x'
    cs = f' {"+" if c > 0 else "−"} {abs(c)}' if c else ''
    if want == 'min':
        f = f'y = {kx} − {lnm}{cs}'
        expr = k * X - m * sp.log(X + a) + c
    else:
        f = pick(r, f'y = {lnm} − {kx}{cs}', f'y = {c} + {lnm} − {kx}')
        expr = m * sp.log(X + a) - k * X + c
    wd = 'максимума' if want == 'max' else 'минимума'
    q = pt_q(r, wd, f)
    ex = f'y′ = {"" if want == "max" else f"{k} − "}{m}/({arg}){"" if want == "min" else f" − {k}"} = 0 при x = {tnum(x0)} (x > {tnum(-a)}).'
    return pcard(q, num(x0), ex), crit_check(expr, num(x0), want, dom=lambda v: v + a > 0)


@proto('ep09-ext-lnquad', 'ege-prof', 9, 'Точка экстремума: квадратный трёхчлен плюс логарифм',
       invariant='y = (A/2)x² − Bx + C·ln x + D: y′ = (Ax² − Bx + C)/x; два положительных корня, максимум в меньшем, минимум в большем.',
       varies='корни числителя (целые или десятичные), коэффициенты, максимум или минимум',
       answer_rule='корни Ax² − Bx + C = 0 при x > 0, выбираем по смене знака',
       fipi=r'x 2 [−+] \d+ x [−+] \d+ ⋅? ?ln x',
       mistakes=['забывают область x > 0', 'путают, какой корень — максимум'],
       note=NOTE_MM, kim=kim(KIM9, kes=['4.2']))
def gen_ep09_ext_lnquad(r):
    u, v = sorted(r.sample(range(1, 16), 2))
    A = r.choice([1, 1, 2, 2, 4, 1])
    # A(x − u)(x − v) = Ax² − A(u + v)x + Auv; y = (A/2)x² − A(u+v)x + Auv·ln x + D
    B, C = A * (u + v), A * u * v
    D = r.randint(-99, 99)
    want = r.choice(['max', 'min'])
    ans = u if want == 'max' else v
    half = F(A, 2)
    f = f'y = {poly([half, -B, 0])} + {C}·ln x' + (f' {"+" if D > 0 else "−"} {abs(D)}' if D else '')
    f = f.replace(' + 0 +', ' +').replace('1/2x²', '0,5x²')
    expr = R(half) * X ** 2 - B * X + C * sp.log(X) + D
    wd = 'максимума' if want == 'max' else 'минимума'
    q = pt_q(r, wd, f)
    ex = f'y′ = ({poly([A, -B, C])})/x = {A if A > 1 else ""}(x − {u})(x − {v})/x; {wd[:-1]} в точке {ans}.'.replace('/x = (', '/x = (')
    return pcard(q, num(ans), ex), crit_check(expr, num(ans), want, dom=lambda z: z > 0)


@proto('ep09-ext-exp', 'ege-prof', 9, 'Точка экстремума: многочлен, умноженный на экспоненту',
       invariant='(P(x)·e^{±x + c})′ = e^{±x + c}(±P + P′); экспонента положительна, знак определяет многочлен.',
       varies='линейный или квадратный множитель, e^{x + c} или e^{c − x}, максимум или минимум',
       answer_rule='корень ±P(x) + P′(x) = 0 со сменой знака нужного вида',
       fipi=r'e \d* ?[−+]? ?x|e x [−+] \d+',
       mistakes=['дифференцируют только множитель', 'теряют минус у производной e^{−x}'],
       note=NOTE_MM, kim=kim(KIM9, kes=['4.2']))
def gen_ep09_ext_exp(r):
    kind = r.choice(['lin_minus', 'lin_plus', 'quad'])
    c = r.randint(-12, 12)
    ecs = lambda sgn: (f'e^{{{tnum(c)} − x}}' if sgn < 0 and c else 'e^{−x}' if sgn < 0 else f'e^{{x {"+" if c > 0 else "−"} {abs(c)}}}' if c else 'e^{x}')
    if kind == 'lin_minus':
        # (x + a)e^{c − x}: y′ = e^{c−x}(1 − x − a) → максимум x = 1 − a
        a = r.choice([v for v in range(-12, 13) if v])
        ans, want = 1 - a, 'max'
        f = f'y = ({lin(1, a)})·{ecs(-1)}'
        expr = (X + a) * sp.exp(c - X)
    elif kind == 'lin_plus':
        # (x + a)e^{x + c}: y′ = e(x + a + 1) → минимум x = −a − 1
        a = r.choice([v for v in range(-12, 13) if v])
        ans, want = -a - 1, 'min'
        f = f'y = ({lin(1, a)})·{ecs(1)}'
        expr = (X + a) * sp.exp(X + c)
    else:
        # (kx² + px + q)e^{x + c}: y′ = e(kx² + (p + 2k)x + p + q) = k·e(x − u)(x − v)
        k = r.choice([1, 1, 2, 3])
        u, v = sorted(r.sample(range(-9, 10), 2))
        p = -k * (u + v) - 2 * k
        q = k * u * v - p
        want = r.choice(['max', 'min'])
        ans = u if want == 'max' else v
        f = f'y = ({poly([k, p, q])})·{ecs(1)}'
        expr = (k * X ** 2 + p * X + q) * sp.exp(X + c)
    wd = 'максимума' if want == 'max' else 'минимума'
    q_ = pt_q(r, wd, f)
    ex = f'Производная равна экспоненте, умноженной на многочлен; он меняет знак в точке {tnum(ans)} — это точка {wd}.'
    return pcard(q_, num(ans), ex), crit_check(expr, num(ans), want)


@proto('ep09-ext-rational', 'ege-prof', 9, 'Точка экстремума функции вида x + a²/x',
       invariant='y = x + a²/x (или −(x² + a²)/x): y′ = 1 − a²/x² = 0 при x = ±a; тип точки — по смене знака, x ≠ 0.',
       varies='a, знак перед дробью, запись (сумма или одна дробь), максимум или минимум',
       answer_rule='x = a или x = −a по знакам производной',
       fipi=r'точку (максимума|минимума) функции y = −? ?x 2 [+−] \d+ x|\d+ x [+−] x',
       mistakes=['берут только положительный корень', 'не учитывают знак перед дробью'],
       note=NOTE_MM, kim=kim(KIM9, kes=['4.2']))
def gen_ep09_ext_rational(r):
    a = r.randint(2, 20)
    s_ = r.choice([1, -1])          # y = s(x + a²/x) + c
    c = r.randint(-15, 15)
    want = r.choice(['max', 'min'])
    # s = 1: минимум в a, максимум в −a; s = −1 наоборот
    ans = (a if want == 'min' else -a) if s_ > 0 else (-a if want == 'min' else a)
    cs = f' {"+" if c > 0 else "−"} {abs(c)}' if c else ''
    if s_ > 0:
        f = pick(r, f'y = x + {a * a}/x{cs}', f'y = ({poly([1, 0, a * a])})/x{cs}', f'y = {a * a}/x + x{cs}')
    else:
        f = pick(r, f'y = −({poly([1, 0, a * a])})/x{cs}', f'y = −x − {a * a}/x{cs}')
    expr = s_ * (X + sp.Integer(a * a) / X) + c
    wd = 'максимума' if want == 'max' else 'минимума'
    q = pt_q(r, wd, f)
    ex = f'y′ = {"" if s_ > 0 else "−"}(1 − {a * a}/x²) = 0 при x = ±{a}; по смене знака точка {wd} — {tnum(ans)}.'
    return pcard(q, num(ans), ex), crit_check(expr, num(ans), want)


SEG_Q = ['Какое {w} значение принимает функция {f} на отрезке {s}?', 'Найдите {w} значение, которое функция {f} принимает на отрезке {s}.',
         'Функция {f} рассматривается на отрезке {s}. Найдите её {w} значение.']


def seg_q(r, w, f, s):
    return r.choice(SEG_Q).format(w=w, f=fm(_fx(r, f)), s=fm(s))


def seg_check(expr, lo, hi, ans, want):
    """Независимо: значения на концах и в критических точках внутри отрезка (sympy) + сетка."""
    def chk():
        d = sp.diff(expr, X)
        cand = [lo, hi]
        try:
            cand += [c for c in sp.solve(sp.Eq(d, 0), X) if c.is_real and lo < c < hi]
        except NotImplementedError:
            pass
        vals = [float(expr.subs(X, c)) for c in cand]
        f_ = sp.lambdify(X, expr, 'math')
        grid = [f_(float(lo) + (float(hi) - float(lo)) * i / 400) for i in range(401)]
        v = max(vals) if want == 'max' else min(vals)
        g = max(grid) if want == 'max' else min(grid)
        a_ = float(F(ans.replace(',', '.')))
        return abs(v - a_) < 1e-9 and (g <= a_ + 1e-9 if want == 'max' else g >= a_ - 1e-9)
    return chk


@proto('ep09-seg-cubic', 'ege-prof', 9, 'Наибольшее (наименьшее) значение многочлена на отрезке',
       invariant='сравниваем значения на концах отрезка и в критических точках внутри него.',
       varies='многочлен 3-й степени, отрезок (содержит одну или обе критические точки), наибольшее или наименьшее',
       answer_rule='max/min из значений в концах и в критических точках отрезка',
       fipi=r'(наибольшее|наименьшее) значение функции y = x 3',
       mistakes=['берут критическую точку вне отрезка', 'отвечают точкой, а не значением'],
       note=NOTE_MM, kim=kim(KIM9, kes=['4.2']))
def gen_ep09_seg_cubic(r):
    u = r.randint(-6, 6)
    w = r.randint(-6, 6)
    if u == w or (u + w) % 2:
        return None
    p, q = F(-3 * (u + w), 2), 3 * u * w
    s_ = r.randint(-20, 20)
    f_ = lambda x: x ** 3 + p * x ** 2 + q * x + s_
    lo_c, hi_c = min(u, w), max(u, w)
    want = r.choice(['max', 'min'])
    if want == 'max':
        a = r.randint(lo_c - 4, lo_c - 1)
        b = r.randint(lo_c + 1, hi_c + 1)
    else:
        a = r.randint(lo_c - 1, hi_c - 1)
        b = r.randint(hi_c + 1, hi_c + 4)
    vals = [f_(x) for x in [a, b] + [c for c in (u, w) if a < c < b]]
    ans = max(vals) if want == 'max' else min(vals)
    # ответ должен достигаться в критической точке — «ловушка» задания
    crit_val = f_(lo_c) if want == 'max' else f_(hi_c)
    if ans != crit_val or vals.count(ans) > 1 or abs(ans) > 999:
        return None
    wd = 'наибольшее' if want == 'max' else 'наименьшее'
    q_ = seg_q(r, wd, f'y = {poly([1, p, q, s_])}', f'[{tnum(a)}; {tnum(b)}]')
    ex = f'y′ = 3(x − {u})(x − {w})'.replace('− -', '+ ') + f'; значения на концах и в критических точках: {", ".join(tnum(v) for v in vals)}; {wd} — {tnum(ans)}.'
    expr = X ** 3 + R(p) * X ** 2 + R(q) * X + s_
    return pcard(q_, num(ans), ex), seg_check(expr, a, b, num(ans), want)


def _pi_pt(k6):
    """k·π/6 в условии."""
    return _pi(k6, 6) if k6 else '0'


@proto('ep09-seg-trig', 'ege-prof', 9, 'Наибольшее (наименьшее) значение: тригонометрическая функция плюс линейная',
       invariant='y = A sin x + kx + C (или с cos): |A| меньше |k|, производная не меняет знак — функция монотонна; значение на нужном конце отрезка (π сокращается).',
       varies='sin или cos, коэффициенты (k = B/π или целое), отрезок с концами, кратными π/6, наибольшее или наименьшее',
       answer_rule='монотонна ⇒ значение на конце отрезка',
       fipi=r'значение функции y = \d+ (sin|cos) x',
       mistakes=['ищут корни y′ = 0, которых нет', 'подставляют не тот конец отрезка'],
       note=NOTE_MM, kim=kim(KIM9, kes=['4.2']))
def gen_ep09_seg_trig(r):
    fn = r.choice(['sin', 'cos'])
    A = r.choice([2, 3, 4, 5, 6, 8, 10, 12])
    # отрезок [kπ/6; 0] или [0; kπ/6]; значение на нужном конце должно быть рациональным
    k6 = r.choice([v for v in range(-12, 13) if v and abs(v) >= 2])
    a6, b6 = (k6, 0) if k6 < 0 else (0, k6)
    # y = A f(x) + (B/π)·x + C, B/π > A/π·… : |y′| ≥ B/π − A > 0 при B > πA
    B = r.choice([v for v in range(int(math.pi * A) + 1, int(math.pi * A) + 30) if v % 6 == 0])
    sgnB = r.choice([1, -1])
    Cc = r.randint(-20, 20)
    want = r.choice(['max', 'min'])
    fv = lambda k6: (sp.sin if fn == 'sin' else sp.cos)(sp.pi * k6 / 6)
    val = lambda k6: A * fv(k6) + sgnB * sp.Rational(B * k6, 6) + Cc
    # возрастает при sgnB > 0
    end = (b6 if want == 'max' else a6) if sgnB > 0 else (a6 if want == 'max' else b6)
    v = val(end)
    if not v.is_rational:
        return None
    ans = F(int(v.p), int(v.q))
    if not nice(ans, 1):
        return None
    Bs = f'{B}x/π'
    f = f'y = {A} {fn} x {"+" if sgnB > 0 else "−"} {Bs}' + (f' {"+" if Cc > 0 else "−"} {abs(Cc)}' if Cc else '')
    wd = 'наибольшее' if want == 'max' else 'наименьшее'
    q = seg_q(r, wd, f, f'[{_pi_pt(a6)}; {_pi_pt(b6)}]')
    ex = f'|{A}·{"cos" if fn == "sin" else "sin"} x| ≤ {A} < {B}/π, поэтому y′ {"> 0" if sgnB > 0 else "< 0"}: функция {"возрастает" if sgnB > 0 else "убывает"}; ответ y({_pi_pt(end)}) = {tnum(ans)}.'
    expr = A * (sp.sin(X) if fn == 'sin' else sp.cos(X)) + sgnB * B * X / sp.pi + Cc

    def chk():
        lo, hi = float(sp.pi * a6 / 6), float(sp.pi * b6 / 6)
        f_ = sp.lambdify(X, expr, 'math')
        grid = [f_(lo + (hi - lo) * i / 2000) for i in range(2001)]
        g = max(grid) if want == 'max' else min(grid)
        return abs(g - float(ans)) < 1e-9
    return pcard(q, num(ans), ex), chk


@proto('ep09-seg-ln', 'ege-prof', 9, 'Наибольшее (наименьшее) значение: логарифм и линейная функция на отрезке',
       invariant='y = m·ln(kx + a) − m(kx) + C или ln(kx) − kx + C: критическая точка там, где аргумент логарифма равен 1, и ln 1 = 0 даёт целый ответ.',
       varies='коэффициенты, запись ln(kx) или m·ln(x + a), отрезок с дробными концами, наибольшее или наименьшее',
       answer_rule='значение в критической точке (логарифм обращается в 0)',
       fipi=r'значение функции y = .*ln .* на отрезке',
       mistakes=['подставляют концы отрезка и получают логарифмы', 'ошибаются с производной ln(kx)'],
       note=NOTE_MM, kim=kim(KIM9, kes=['4.2']))
def gen_ep09_seg_ln(r):
    want = r.choice(['max', 'min'])
    Cc = r.randint(-20, 30)
    if r.random() < 0.5:
        # y = ±(ln(kx) − kx) + C; критическая x = 1/k, значение ±(−1) + C
        k = r.choice([2, 3, 4, 5, 6, 8, 10, 11, 12, 16, 20])
        mm = r.choice([1, 2, 3, 4, 5, 6])
        x0 = F(1, k)
        lo, hi = F(1, r.choice([2, 3, 4]) * k), F(r.choice([3, 5, 7]), 2 * k)
        s_ = 1 if want == 'max' else -1
        expr = s_ * mm * (sp.log(k * X) - k * X) + Cc
        ans = -s_ * mm + Cc
        cs = f' {"+" if Cc > 0 else "−"} {abs(Cc)}' if Cc else ''
        m_ = '' if mm == 1 else str(mm)
        f = f'y = {m_}ln({k}x) − {mm * k}x{cs}' if s_ > 0 else f'y = {mm * k}x − {m_}ln({k}x){cs}'
        fq = lambda z: f'{z.numerator}/{z.denominator}' if z.denominator > 1 else str(z)
        segs = f'[{fq(lo)}; {fq(hi)}]'
    else:
        # y = ±(m·ln(x + a) − m x) + C; критическая x = 1 − a
        m = r.randint(2, 12)
        a = r.randint(-9, 12)
        x0 = F(1 - a)
        lo = F(-2 * a + 1, 2) if r.random() < 0.5 else F(-a) + F(1, 2)
        hi = x0 + r.choice([F(1, 2), 1, F(3, 2), 2])
        s_ = 1 if want == 'max' else -1
        expr = s_ * (m * sp.log(X + a) - m * X) + Cc
        ans = s_ * (-m * x0) + Cc
        cs = f' {"+" if Cc > 0 else "−"} {abs(Cc)}' if Cc else ''
        arg = lin(1, a)
        lnm = pick(r, f'{m}ln({arg})', f'ln({arg})^{{{m}}}')
        f = f'y = {lnm} − {m}x{cs}' if s_ > 0 else f'y = {m}x − {lnm}{cs}'
        segs = f'[{tnum(lo)}; {tnum(hi)}]'
    if not (lo < x0 < hi) or not nice(ans, 2):
        return None
    wd = 'наибольшее' if want == 'max' else 'наименьшее'
    q = seg_q(r, wd, f, segs)
    ex = f'y′ = 0 при x = {fr(x0)} (там логарифм равен 0); это точка {"максимума" if want == "max" else "минимума"}, ответ {tnum(ans)}.'
    return pcard(q, num(ans), ex), seg_check(expr, R(lo), R(hi), num(ans), want)


@proto('ep09-seg-sqrt', 'ege-prof', 9, 'Наибольшее (наименьшее) значение функции с x√x на отрезке',
       invariant='y = a + bx − c·x√x: критическая точка √x = 2b/(3c) внутри отрезка, значение в ней — ответ.',
       varies='коэффициенты, отрезок, наибольшее или наименьшее',
       answer_rule='y(x₀), x₀ = (2b/(3c))²',
       fipi=r'значение функции .*x √\( x \).* на отрезке',
       mistakes=['берут значение на конце отрезка', 'ошибаются в (x√x)′'],
       note=NOTE_MM, kim=kim(KIM9, kes=['4.2']))
def gen_ep09_seg_sqrt(r):
    s_ = r.randint(2, 9)
    c = r.choice([1, 2, 4])
    b = F(3 * c * s_, 2)
    if b.denominator != 1:
        return None
    x0 = s_ * s_
    a0 = r.randint(-30, 30)
    want = r.choice(['max', 'min'])
    sg = 1 if want == 'max' else -1
    # max: y = a0 + b x − c x√x;  min: y = c x√x − b x + a0
    val = a0 + sg * (b * x0 - c * x0 * s_)
    lo = r.choice([0, 1, 4]) if x0 > 4 else r.choice([0, 1])
    hi = r.choice([x0 + v for v in (5, 11, 16, 20, 36)])
    if lo >= x0:
        return None
    cx = ('' if c == 1 else str(c)) + 'x√x'
    f = (f'y = {a0} + {b}x − {cx}' if want == 'max' else f'y = {cx} − {b}x {"+" if a0 >= 0 else "−"} {abs(a0)}')
    wd = 'наибольшее' if want == 'max' else 'наименьшее'
    q = seg_q(r, wd, f, f'[{lo}; {hi}]')
    ex = f'y′ = 0 при √x = {s_}, x = {x0}; y({x0}) = {tnum(val)} — {wd} значение.'
    expr = a0 + sg * (b * X - c * X * sp.sqrt(X))
    return pcard(q, num(val), ex), seg_check(expr, lo, hi, num(val), want)
