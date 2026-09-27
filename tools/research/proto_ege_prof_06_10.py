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


EQ_Q = ['Решите уравнение {} и запишите его корень.',
        'Уравнение {} имеет единственный корень. Найдите его.',
        'Найдите значение x, при котором {}.',
        'При каком значении x верно равенство {}?',
        'Найдите x, если {}.']


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
    return fr(v)


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
    return pcard(q, num(x), ex), one_root(sp.Integer(a) ** (k * X + c), R(F(a) ** m), num(x))


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
    if not nice(x, 1) or c == 0:
        return None
    e = lin_t(k, c)
    f = f'(1/{a})^{{{e}}} = {_pow_rhs(a, m)}'
    q = eq_q(r, f)
    ex = f'(1/{a})^{{{e}}} = {a}^{{−({e})}}, {_pow_rhs(a, m)} = {a}^{{{tnum(m)}}}; −({e}) = {tnum(m)}, x = {tnum(x)}.'
    return pcard(q, num(x), ex), one_root(sp.Rational(1, a) ** (k * X + c), R(F(a) ** m), num(x))


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
    if not nice(x, 1) or (c1 == 0 and c2 == 0):
        return None
    e1, e2 = lin_t(k1, c1), lin_t(k2, c2)
    f = f'{base(s)}^{{{e1}}} = {base(t)}^{{{e2}}}'
    q = eq_q(r, f)
    ex = f'Обе части — степени числа {d}: {d}^{{{tnum(s)}({e1})}} = {d}^{{{tnum(t)}({e2})}}; {tnum(s)}({e1}) = {tnum(t)}({e2}), x = {tnum(x)}.'
    return pcard(q, num(x), ex), one_root(R(F(d) ** s) ** (k1 * X + c1), R(F(d) ** t) ** (k2 * X + c2), num(x))


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
    if not nice(x, 1) or b == 0 or c == a:
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
    if not nice(x, 2) or b == 0:
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
    f = f'{logb("x" + (" + " if b > 0 else " − ") + str(abs(b))).replace("x + ", "₍ₓ₊").replace("x − ", "₍ₓ₋")}'
    # основание-выражение пишем как log_{x + b}: подстрочно не набрать — используем скобки
    f = f'log_(x {"+" if b > 0 else "−"} {abs(b)}) {c} = {n}'
    q = eq_q(r, f)
    if n == 2:
        q = q.rstrip('.?') + ('. Если уравнение имеет более одного корня, в ответе запишите больший из них.' if False else '')
        q = q + ('.' if not q.endswith(('.', '?')) else '')
    ex = (f'(x {"+" if b > 0 else "−"} {abs(b)})^{n} = {c}, основание положительно и не равно 1: '
          f'x {"+" if b > 0 else "−"} {abs(b)} = {base}, x = {tnum(x)}.')

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
    if not nice(x, 1) or b == 0:
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
    if not nice(x, 1) or b == 0:
        return None
    arg = lin_t(k, b)
    f = f'∛({arg}) = {tnum(c)}'
    q = eq_q(r, f)
    ex = f'Возводим в куб: {arg} = {tnum(c ** 3)}, x = {tnum(x)}.'
    return pcard(q, num(x), ex), one_root(sp.real_root(k * X + b, 3) if False else (k * X + b), sp.Integer(c) ** 3, num(x))


@proto('ep07-cube', 'ege-prof', 7, 'Уравнение (x + b)³ = c',
       invariant='(kx + b)³ = c, c — точный куб (может быть отрицательным); извлекаем кубический корень.',
       varies='b, c, коэффициент k',
       answer_rule='kx + b = ∛c',
       fipi=r'корень уравнения \( x [+−] \d+ \) 3 = ',
       mistakes=['при c < 0 считают, что корней нет', 'делят c на 3 вместо извлечения корня'],
       kim=kim(KIM7, kes=['2.1']))
def gen_ep07_cube(r):
    t = r.choice([-6, -5, -4, -3, -2, 2, 3, 4, 5, 6, 7])
    k = r.choice([1, 1, 1, 2, -1])
    b = r.choice([v for v in range(-12, 13) if v])
    x = F(t - b, k)
    if not nice(x, 1):
        return None
    f = f'({lin_t(k, b)})³ = {tnum(t ** 3)}'
    q = eq_q(r, f)
    ex = f'{tnum(t ** 3)} = ({tnum(t)})³, значит {lin_t(k, b)} = {tnum(t)}, x = {tnum(x)}.'
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
    if not nice(x, 2) or b == 0 or c == 0:
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
    q = f'Решите уравнение {fm(f)}. Если уравнение имеет более одного корня, в ответе запишите {word} из корней.'
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
    q = f'Решите уравнение {fm(f)}. Если уравнение имеет более одного корня, в ответе укажите меньший из них.'
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
    base = []
    for j in range(24):
        t = sp.pi * j / 12
        if sp.simplify((sp.cos(t) if fn == 'cos' else sp.sin(t)) - v) == 0:
            base.append(F(j, 12))
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
