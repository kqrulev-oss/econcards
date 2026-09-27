"""Прототипы ЕГЭ профиль (КИМ 2027), часть 2: №14, 15, 16, 18, 19, 20.

№14 — уравнение (а — решить, б — отбор корней): тригонометрические (квадратные относительно sin/cos,
вынесение множителя, формулы сложения, однородные, группировка), показательные и логарифмические
с тригонометрией, показательные и логарифмические с отбором на отрезке с иррациональными концами.
№15 — стереометрия: расстояния, углы, сечения, объёмы, отношения; тела вращения.
№16 — неравенства: показательные, логарифмические, с переменным основанием, рациональные, с корнями.
№18 — планиметрия: доказательство + вычисление.
№19 — задача с параметром.
№20 — числа и их свойства (а, б, в).

Задание с развёрнутым ответом в карточке — полное условие как в КИМ (а, б …) и строка
«В ответ запишите …» с числовым итогом пункта б (в). Доказательная часть (а) проверяется
экспертом, в карточку она входит текстом; для номеров, где числовой итог не генерируется,
есть рецепты proto_llm.

Формулы в условиях помечены ⟦ ⟧ (степени ^{…} показываются надстрочно, см. lib.js).
Проверки: текст формулы из карточки разбирается заново (parse_f) и решается другим путём —
численный поиск корней, перебор целых точек, sympy, координаты.
Тексты ФИПИ сюда не попадают: регулярки fipi служат только для подсчёта покрытия банка.
"""
import itertools
import math

from mathlib import (F, R, X, finite, ftxt, nice, num, pcard, pick, plural, poly, proto, proto_llm, same, signed, sp,
                     svg_geom, tnum)

# ================================================================ паспорта КИМ

CRIT14 = ('2 — обоснованно получены верные ответы в обоих пунктах; 1 — обоснованно получен верный ответ '
          'в пункте а ИЛИ вычислительная ошибка при верной последовательности шагов обоих пунктов; 0 — иначе')
CRIT16 = ('2 — обоснованно получен верный ответ; 1 — ответ отличается от верного исключением/включением '
          'граничной точки ИЛИ вычислительная ошибка при верной последовательности всех шагов; 0 — иначе')
CRIT_AB3 = ('3 — доказан пункт а и обоснованно получен верный ответ в б; 2 — обоснованный ответ в б ИЛИ доказан а, '
            'но в б арифметическая ошибка; 1 — доказан а ИЛИ арифметическая ошибка в обоснованном б ИЛИ верный '
            'ответ в б с опорой на недоказанный а; 0 — иначе')
CRIT19 = ('4 — обоснованно получен правильный ответ; 3 — верный ответ, отличающийся исключением/включением '
          'граничных точек; 2 — верно найдена часть множества (один из промежутков) ИЛИ вычислительная ошибка '
          'при верных шагах; 1 — задача верно сведена к исследованию (аналитически или графически); 0 — иначе')
CRIT20 = ('4 — верные обоснованные ответы в а, б и в; 3 — обоснован в и один из а, б; 2 — обоснованы а и б '
          'ИЛИ обоснован в; 1 — обоснован а или б; 0 — иначе')

NUM_LINE = ('. Отличие карточки от КИМ: условие — как в КИМ, добавлена строка «В ответ запишите …» с числом '
            'для автопроверки ({}). Число проверяет только верность итогового ответа; баллы по критериям '
            'выставляются за полное решение, а верное число — необходимое, но не достаточное условие высшего балла')

K14 = dict(level='П', points=2, minutes=10, kes=['2.3'], kt=['КТ 3'],
           answer='развёрнутый (в карточке — число из пункта б: количество, сумма или крайний корень)',
           scoring=CRIT14 + NUM_LINE.format('количество, сумма или крайний из корней пункта б'),
           format='как в КИМ: «а) Решите уравнение …» + «б) Найдите все корни этого уравнения, принадлежащие отрезку […]» '
                  '+ строка «В ответ запишите …»')
K15 = dict(level='П', points=3, minutes=20, kes=['7.2', '7.3'], kt=['КТ 9', 'КТ 10', 'КТ 11'],
           answer='развёрнутый (в карточке — число из пункта б)',
           scoring=CRIT_AB3 + NUM_LINE.format('искомая величина пункта б (или её квадрат, тригонометрическая функция угла)'),
           format='описание многогранника с числами + «а) Докажите, что …» + «б) Найдите …» + строка ответа; чертёж')
K16 = dict(level='П', points=2, minutes=10, kes=['2.7'], kt=['КТ 3'],
           answer='развёрнутый (в карточке — число: сумма или количество целых решений, крайнее целое решение)',
           scoring=CRIT16 + NUM_LINE.format('сумма/количество целых решений или крайнее целое решение'),
           format='«Решите неравенство …» (как в КИМ) + строка «В ответ запишите …»')
K18 = dict(level='П', points=3, minutes=35, kes=['7.1'], kt=['КТ 9', 'КТ 11'],
           answer='развёрнутый (в карточке — число из пункта б)',
           scoring=CRIT_AB3 + NUM_LINE.format('искомая величина пункта б'),
           format='данные фигуры + «а) Докажите, что …» + «б) Найдите …» + строка ответа; чертёж')
K19 = dict(level='В', points=4, minutes=35, kes=['2.10'], kt=['КТ 3', 'КТ 5'],
           answer='развёрнутый (в карточке — число: количество или сумма целых a из ответа, граничное значение)',
           scoring=CRIT19 + NUM_LINE.format('количество или сумма целых a из ответа, граничное значение a'),
           format='как в КИМ: «Найдите все значения a, при каждом из которых уравнение (система) … имеет …» '
                  '+ строка «В ответ запишите …»')
K20 = dict(level='В', points=4, minutes=40, kes=['1.1'], kt=['КТ 1', 'КТ 2', 'КТ 13'],
           answer='развёрнутый (в карточке — число из пункта в)',
           scoring=CRIT20 + NUM_LINE.format('ответ пункта в'),
           format='сюжет + «а) Может ли …» + «б) Может ли …» + «в) Найдите наибольшее/наименьшее …» + строка ответа')


def kim(base, style, **kw):
    d = dict(base)
    d['style'] = style
    d.update(kw)
    return d


# ================================================================ текст формул


def fm(s):
    """Формула в условии: ⟦…⟧."""
    return f'⟦{s}⟧'


def fr(x):
    """Число дробью: 7/2, −3/4; целое — числом."""
    x = F(x)
    if x.denominator == 1:
        return tnum(x)
    return f'{"−" if x < 0 else ""}{abs(x.numerator)}/{x.denominator}'


def pis(k):
    """k·π текстом (k — дробь): π, −π, 3π, 5π/2, −π/6, 0."""
    k = F(k)
    if k == 0:
        return '0'
    s = '−' if k < 0 else ''
    p, q = abs(k.numerator), k.denominator
    body = ('' if p == 1 else str(p)) + 'π'
    return s + body + (f'/{q}' if q != 1 else '')


def seg_pi(a, b):
    return f'[{pis(a)}; {pis(b)}]'


def logb(b):
    """log с основанием нижним индексом: log₃, log₀,₅, logₓ₊₁."""
    t = str(b).replace('-', '−')
    tr = str.maketrans('0123456789x+−', '₀₁₂₃₄₅₆₇₈₉ₓ₊₋')
    return 'log' + t.replace(' ', '').translate(tr)


class QS:
    """Число r·√m (m свободно от квадратов) — коэффициенты и значения sin/cos стандартных углов."""
    __slots__ = ('r', 'm')

    def __init__(self, r, m=1):
        r = F(r)
        if r == 0:
            m = 1
        self.r, self.m = r, m

    def __add__(self, o):
        o = qs(o)
        if self.r == 0:
            return o
        if o.r == 0:
            return self
        if self.m != o.m:
            return None
        return QS(self.r + o.r, self.m)

    def __neg__(self):
        return QS(-self.r, self.m)

    def __sub__(self, o):
        return self + (-qs(o))

    def __mul__(self, o):
        o = qs(o)
        if self.m == o.m:
            return QS(self.r * o.r * self.m, 1)
        if self.m == 1 or o.m == 1:
            return QS(self.r * o.r, self.m * o.m)
        k, m = sqfree(self.m * o.m)
        return QS(self.r * o.r * k, m)

    def __eq__(self, o):
        o = qs(o)
        return self.r == o.r and (self.m == o.m or self.r == 0)

    def __hash__(self):
        return hash((self.r, self.m if self.r else 1))

    def f(self):
        return float(self.r) * math.sqrt(self.m)

    def sq(self):
        return self.r * self.r * self.m

    def is_zero(self):
        return self.r == 0

    def text(self):
        """Текст числа: 3, −1/2, √3, 2√2, −√3/2, 3√2/2."""
        r, m = self.r, self.m
        if m == 1:
            return fr(r)
        s = '−' if r < 0 else ''
        p, q = abs(r.numerator), r.denominator
        body = ('' if p == 1 else str(p)) + f'√{m}'
        return s + body + (f'/{q}' if q != 1 else '')

    def sym(self):
        return R(self.r) * sp.sqrt(self.m)


def qs(x):
    return x if isinstance(x, QS) else QS(x)


def cterm(c, body, first=False):
    """Слагаемое c·body со знаком: '2cos 2x', ' − √2 sin x', ' + 3' (body='' — число)."""
    c = qs(c)
    if c.is_zero():
        return ''
    neg = c.r < 0
    a = QS(abs(c.r), c.m)
    if not body:
        t = a.text()
    elif a == QS(1):
        t = body
    elif a.r.denominator != 1:
        t = (f'({a.text()})' if a.m != 1 else a.text()) + '·' + body
    elif a.m != 1:
        t = a.text() + ' ' + body
    elif body[0].isdigit():
        t = a.text() + '·' + body
    else:
        t = a.text() + body
    if first:
        return ('−' if neg else '') + t
    return (' − ' if neg else ' + ') + t


def join_terms(terms):
    """[(coef, body), …] → 'a + b − c'; пусто → '0'."""
    out = ''
    for c, b in terms:
        s = cterm(c, b, first=not out)
        out += s
    return out or '0'


# ================================================================ разбор формул (для проверок)

_SUBS = str.maketrans('₀₁₂₃₄₅₆₇₈₉ₓ₊₋₍₎', '0123456789x+-()')


class _P:
    """Разбор формулы из карточки в sympy: ровно тот текст, что видит ученик."""

    FUN = ('sin', 'cos', 'tg', 'ctg', 'ln', 'log')

    def __init__(self, s, env):
        s = s.replace('⟦', '').replace('⟧', '').replace('−', '-').replace('⋅', '·')
        self.s, self.i, self.env = s, 0, env
        self.conds = []           # условия области определения, собранные при разборе (до упрощений sympy)

    def cond(self, e, kind):
        if getattr(e, 'free_symbols', None):
            self.conds.append((e, kind))

    def peek(self):
        while self.i < len(self.s) and self.s[self.i] == ' ':
            self.i += 1
        return self.s[self.i] if self.i < len(self.s) else ''

    def eat(self, ch):
        if self.peek() == ch:
            self.i += 1
            return True
        return False

    def expect(self, ch):
        if not self.eat(ch):
            raise ValueError(f'ожидалось {ch!r} в позиции {self.i}: {self.s!r}')

    def parse(self):
        e = self.relation()
        if self.peek():
            raise ValueError(f'лишний хвост {self.s[self.i:]!r} в {self.s!r}')
        return e

    def relation(self):
        a = self.expr()
        for op in ('≥', '≤', '>', '<', '='):
            if self.eat(op):
                b = self.expr()
                return (op, a, b)
        return a

    def expr(self):
        if self.eat('-'):
            e = -self.term()
        else:
            self.eat('+')
            e = self.term()
        while True:
            if self.eat('+'):
                e = e + self.term()
            elif self.eat('-'):
                e = e - self.term()
            else:
                return e

    def term(self):
        e = self.power()
        while True:
            c = self.peek()
            if c == '·' or c == '*':
                self.i += 1
                e = e * self.power()
            elif c == '/':
                self.i += 1
                d = self.power()
                self.cond(d, 'nz')
                e = e / d
            elif c and (c.isdigit() or c.isalpha() or c in '(√π'):
                e = e * self.power()
            else:
                return e

    def power(self):
        e = self.atom()
        while True:
            c = self.peek()
            if c == '^':
                self.i += 1
                self.expect('{')
                p = self.expr()
                self.expect('}')
                e = e ** p
            elif c and c in '²³⁴':
                self.i += 1
                e = e ** {'²': 2, '³': 3, '⁴': 4}[c]
            else:
                return e

    def number(self):
        j = self.i
        while self.i < len(self.s) and (self.s[self.i].isdigit() or
                                        (self.s[self.i] == ',' and self.i + 1 < len(self.s) and self.s[self.i + 1].isdigit())):
            self.i += 1
        return sp.Rational(self.s[j:self.i].replace(',', '.'))

    def atom(self):
        c = self.peek()
        if c.isdigit():
            return self.number()
        if c == '(':
            self.i += 1
            e = self.expr()
            self.expect(')')
            return e
        if c == '|':
            self.i += 1
            e = self.expr()
            self.expect('|')
            return sp.Abs(e)
        if c == '[':
            self.i += 1
            e = self.expr()
            self.expect(']')
            return e
        if c == '√':
            self.i += 1
            a = self.atom()
            self.cond(a, 'nonneg')
            return sp.sqrt(a)
        if c == 'π':
            self.i += 1
            return sp.pi
        for f in self.FUN:
            if self.s.startswith(f, self.i) and not (f == 'tg' and self.s.startswith('ctg', self.i - 1)):
                if f == 'ln' and self.s.startswith('log', self.i):
                    continue
                self.i += len(f)
                return self.func(f)
        if c.isalpha():
            self.i += 1
            if c in self.env:
                return self.env[c]
            raise ValueError(f'неизвестная буква {c!r} в {self.s!r}')
        raise ValueError(f'не разобрано {self.s[self.i:]!r} в {self.s!r}')

    def func(self, f):
        base = None
        if f == 'log':
            j = self.i
            while self.i < len(self.s) and (self.s[self.i] in '₀₁₂₃₄₅₆₇₈₉ₓ₊₋₍₎' or
                                            (self.s[self.i] == ',' and self.s[self.i + 1] in '₀₁₂₃₄₅₆₇₈₉')):
                self.i += 1
            bt = self.s[j:self.i].translate(_SUBS)
            base = _P(bt, self.env).parse() if bt else sp.Integer(10)
            self.cond(base, 'pos')
            self.cond(base - 1, 'nz')
        pw = 1
        if self.peek() and self.peek() in '²³':
            pw = {'²': 2, '³': 3}[self.s[self.i]]
            self.i += 1
        if self.peek() == '(':
            self.i += 1
            arg = self.expr()
            self.expect(')')
        else:
            # простой аргумент без скобок: x, 2x, 3x, x/2
            j = self.i
            k = sp.Integer(1)
            if self.peek().isdigit():
                k = self.number()
            ch = self.peek()
            if not ch.isalpha() and j != self.i:
                return (sp.log(k, base) if f == 'log' else {'sin': sp.sin, 'cos': sp.cos, 'tg': sp.tan,
                                                            'ctg': sp.cot, 'ln': sp.log}[f](k)) ** pw
            if not ch.isalpha():
                raise ValueError(f'аргумент функции в {self.s!r} @ {j}')
            self.i += 1
            arg = k * self.env[ch]
            if self.s.startswith('/', self.i) and self.s[self.i + 1:self.i + 2].isdigit():
                self.i += 1
                arg = arg / self.number()
        fn = {'sin': sp.sin, 'cos': sp.cos, 'tg': sp.tan, 'ctg': sp.cot, 'ln': sp.log}.get(f)
        if f in ('log', 'ln'):
            self.cond(arg, 'pos')
        if f == 'tg':
            self.cond(sp.cos(arg), 'nz')
        if f == 'ctg':
            self.cond(sp.sin(arg), 'nz')
        v = sp.log(arg, base) if f == 'log' else fn(arg)
        return v ** pw


A_ = sp.Symbol('a', real=True)
Y_ = sp.Symbol('y', real=True)


def parse_f(s, env=None):
    """Текст формулы → sympy (выражение или (знак, левая, правая))."""
    return _P(s, env or {'x': X, 'a': A_, 'y': Y_}).parse()


def parse_fd(s, env=None):
    """То же + условия области определения, собранные при разборе: (результат, [(выражение, вид)])."""
    p = _P(s, env or {'x': X, 'a': A_, 'y': Y_})
    res = p.parse()
    return res, p.conds


def eq_expr(s):
    """Уравнение «L = R» → (L − R, условия ОДЗ)."""
    (op, a, b), conds = parse_fd(s)
    assert op == '=', s
    return a - b, conds


# ================================================================ численный поиск корней (для проверок №14)


def domain_parts(f):
    """Условия области определения выражения: [(выражение, вид)], вид: 'pos' (> 0), 'nonneg' (≥ 0), 'nz' (≠ 0)."""
    conds = []
    for a in sp.preorder_traversal(f):
        if isinstance(a, sp.log) and a.args[0].free_symbols:
            conds.append((a.args[0], 'pos'))
        elif isinstance(a, sp.Pow) and a.base.free_symbols:
            ex = a.exp
            if ex.is_Rational and ex.q % 2 == 0:
                conds.append((a.base, 'nonneg' if ex > 0 else 'pos'))
            elif ex.is_Rational and ex < 0:
                conds.append((a.base, 'nz'))
            elif not ex.is_Rational:
                conds.append((a.base, 'pos'))
        elif isinstance(a, (sp.tan, sp.cot)):
            conds.append((sp.cos(a.args[0]) if isinstance(a, sp.tan) else sp.sin(a.args[0]), 'nz'))
    return conds


def make_eval(f, var=None, conds=()):
    """Функция x → значение f (mpmath) или None вне области определения (условия — из разбора и из f)."""
    import mpmath as mp
    mp.mp.dps = 30
    var = var or X
    g = sp.lambdify(var, f, modules=['mpmath'])
    conds = [(sp.lambdify(var, e, modules=['mpmath']), k) for e, k in list(conds) + domain_parts(f)]

    def bad_kinds(x):
        """Виды нарушенных условий области определения в точке x."""
        out = set()
        for c, k in conds:
            try:
                v = c(mp.mpf(x))
            except (ZeroDivisionError, ValueError, TypeError, OverflowError):
                out.add(k)
                continue
            if isinstance(v, mp.mpc):
                v = v.real if abs(v.imag) <= 1e-25 else None
            if v is None or k == 'pos' and not v > 0 or k == 'nonneg' and not v >= 0 or k == 'nz' and abs(v) < 1e-25:
                out.add(k)
        return out

    def val(x):
        try:
            for c, k in conds:
                v = c(mp.mpf(x))
                if isinstance(v, mp.mpc):
                    if abs(v.imag) > 1e-25:
                        return None
                    v = v.real
                if k == 'pos' and not v > 0 or k == 'nonneg' and not v >= 0 or k == 'nz' and abs(v) < 1e-25:
                    return None
            v = g(mp.mpf(x))
        except (ZeroDivisionError, ValueError, TypeError, OverflowError):
            return None
        if isinstance(v, mp.mpc):
            if abs(v.imag) > 1e-20:
                return None
            v = v.real
        try:
            v = mp.mpf(v)
        except TypeError:
            return None
        if not mp.isfinite(v):
            return None
        return v
    val.bad = bad_kinds
    return val


def num_roots(f, lo, hi, n=6000, conds=()):
    """Все корни выражения f(x) на [lo; hi] (включая касания и корни на границе области определения),
    численно по сетке + уточнение. Точки вне области определения пропускаются."""
    import mpmath as mp
    val = make_eval(f, conds=conds)

    d = (hi - lo) / n
    xs = [lo - 3 * d + d * i for i in range(n + 7)]
    n = len(xs) - 1
    vs = [val(x) for x in xs]
    cand = []
    for i in range(n):
        if (vs[i] is None) != (vs[i + 1] is None):
            a, b = mp.mpf(xs[i]), mp.mpf(xs[i + 1])
            da = vs[i] is not None
            for _ in range(95):
                m = (a + b) / 2
                if (val(m) is not None) == da:
                    a = m
                else:
                    b = m
            x0 = a if da else b
            v0 = val(x0)
            # на границе ОДЗ корень возможен, только если граница задана нестрогим условием (корень чётной степени)
            # и если в самой граничной точке не обращается в нуль знаменатель (условие «≠ 0»)
            nz0 = any(k_ == 'nz' and abs(complex(sp.N(ex.subs(X, x0)))) < 1e-6 for ex, k_ in conds)
            if v0 is not None and abs(v0) < 1e-9 and val.bad(b if da else a) <= {'nonneg'} and not nz0:
                cand.append((x0, x0))
    for i in range(n + 1):
        v = vs[i]
        if v is None:
            continue
        if abs(v) < 1e-18:
            cand.append((xs[i], xs[i]))
            continue
        if i < n and vs[i + 1] is not None and v * vs[i + 1] < 0:
            cand.append(('b', xs[i], xs[i + 1]))
        l_ = vs[i - 1] if i > 0 else None
        r_ = vs[i + 1] if i < n else None
        if (l_ is None or abs(v) <= abs(l_)) and (r_ is None or abs(v) <= abs(r_)):
            cand.append(('m', xs[max(i - 1, 0)], xs[min(i + 1, n)]))
    roots = []
    for c in cand:
        if len(c) == 2:
            x0 = mp.mpf(c[0])
        elif c[0] == 'b':
            a, b = mp.mpf(c[1]), mp.mpf(c[2])
            fa = val(a)
            for _ in range(200):
                m = (a + b) / 2
                fm_ = val(m)
                if fm_ is None:
                    break
                if fm_ == 0:
                    a = b = m
                    break
                if (fm_ > 0) == (fa > 0):
                    a, fa = m, fm_
                else:
                    b = m
            x0 = (a + b) / 2
        else:
            a, b = mp.mpf(c[1]), mp.mpf(c[2])
            gr = (mp.sqrt(5) - 1) / 2
            for _ in range(160):
                c1, c2 = b - gr * (b - a), a + gr * (b - a)
                v1, v2 = val(c1), val(c2)
                if v1 is None or v2 is None:
                    break
                if abs(v1) < abs(v2):
                    b = c2
                else:
                    a = c1
            x0 = (a + b) / 2
        v0 = val(x0)
        tol = mp.mpf(10) ** -9 if len(c) == 2 else mp.mpf(10) ** -12
        if v0 is not None and len(c) == 3:
            dlt = mp.mpf(10) ** -12
            near = [val.bad(x0 - dlt) if val(x0 - dlt) is None else set(), val.bad(x0 + dlt) if val(x0 + dlt) is None else set()]
            if any(k_ - {'nonneg'} for k_ in near):
                v0 = None
        if v0 is not None and any(k_ == 'nz' and abs(complex(sp.N(ex.subs(X, x0)))) < 1e-6 for ex, k_ in conds):
            v0 = None                   # предел в точке, где знаменатель обращается в нуль, — не корень
        if v0 is not None and abs(v0) < tol and lo - 1e-9 <= x0 <= hi + 1e-9:
            if all(abs(x0 - q) > 1e-7 for q in roots):
                roots.append(x0)
    return sorted(float(x) for x in roots)


# ================================================================ №14: общие части


# значения синуса/косинуса стандартных углов и «посторонние» значения (|t| > 1)
T_OK = [QS(0), QS(F(1, 2)), QS(-F(1, 2)), QS(1), QS(-1), QS(F(1, 2), 2), QS(-F(1, 2), 2),
        QS(F(1, 2), 3), QS(-F(1, 2), 3)]
T_BAD = [QS(2), QS(-2), QS(F(3, 2)), QS(-F(3, 2)), QS(3), QS(-3), QS(1, 2), QS(-1, 2), QS(1, 3), QS(-1, 3),
         QS(4), QS(-4)]


def small(terms, lim=12):
    return all(abs(qs(c).r) * (1 if qs(c).m == 1 else 1) <= lim for c, _ in terms)

ASIN = {QS(0): F(0), QS(F(1, 2)): F(1, 6), QS(1): F(1, 2), QS(F(1, 2), 2): F(1, 4), QS(F(1, 2), 3): F(1, 3)}
ATAN = {QS(0): F(0), QS(1): F(1, 4), QS(1, 3): F(1, 3), QS(F(1, 3), 3): F(1, 6)}


def series(kind, v):
    """Серии корней kind(x) = v: список (начало, период) в долях π (дроби) или None, если значение
    нестандартное (тогда float-серии: ('f', начало, период))."""
    if kind in ('sin', 'cos'):
        if abs(v.f()) > 1 + 1e-12:
            return []
        av = QS(abs(v.r), v.m)
        if av in ASIN:
            a = ASIN[av] * (1 if v.r >= 0 else -1)
            if kind == 'sin':
                if abs(a) == F(1, 2):
                    return [(a, F(2))]
                if a == 0:
                    return [(F(0), F(1))]
                return [(a, F(2)), (1 - a, F(2))]
            c = F(1, 2) - a            # arccos v = π/2 − arcsin v
            if c == 0 or c == 1:
                return [(c, F(2))]
            if c == F(1, 2):
                return [(c, F(1))]
            return [(c, F(2)), (-c, F(2))]
        a = math.asin(v.f()) / math.pi
        if kind == 'sin':
            return [('f', a, 2), ('f', 1 - a, 2)]
        c = 0.5 - a
        return [('f', c, 2), ('f', -c, 2)]
    if kind == 'tg':
        av = QS(abs(v.r), v.m)
        if av in ATAN:
            return [(ATAN[av] * (1 if v.r >= 0 else -1), F(1))]
        return [('f', math.atan(v.f()) / math.pi, 1)]
    raise ValueError(kind)


def roots_on(sers, lo, hi):
    """Корни всех серий на отрезке [lo; hi] (в долях π): список (дробь или None, float) без повторов."""
    out = {}
    for s in sers:
        if s[0] == 'f':
            a, p = s[1], s[2]
            k0 = math.floor((float(lo) - a) / p) - 1
            for k in range(k0, k0 + int(float(hi - lo) / p) + 4):
                x = a + p * k
                if float(lo) - 1e-12 <= x <= float(hi) + 1e-12:
                    out[round(x, 9)] = (None, x)
        else:
            a, p = s
            k0 = math.floor((lo - a) / p) - 1
            for k in range(k0, k0 + int((hi - lo) / p) + 4):
                x = a + p * k
                if lo <= x <= hi:
                    out[round(float(x), 9)] = (x, float(x))
    return [out[k] for k in sorted(out)]


ASK14 = ['count', 'count', 'sum', 'max', 'min']


def ask14(r, rts, kinds=ASK14):
    """Числовой итог пункта б: (текст инструкции, ответ, пояснение) или None."""
    if not rts:
        return None
    kinds = list(kinds)
    r.shuffle(kinds)
    for k in kinds:
        if k == 'count':
            return 'В ответ запишите количество корней, найденных в пункте б.', F(len(rts))
        exact = all(e is not None for e, _ in rts)
        if not exact:
            continue
        if k == 'sum':
            s = sum(e for e, _ in rts)
            if s != 0 and nice(s, 2):
                return 'В ответ запишите сумму корней, найденных в пункте б, делённую на π.', s
        if k in ('max', 'min'):
            e = max(e for e, _ in rts) if k == 'max' else min(e for e, _ in rts)
            deg = e * 180
            if deg.denominator == 1 and abs(deg) <= 540:
                w = 'наибольший' if k == 'max' else 'наименьший'
                return f'В ответ запишите {w} из корней, найденных в пункте б, в градусах.', deg
    return None


def check14(eq_text, lo, hi, ask, ans):
    """Независимая проверка: разбираем уравнение из текста и ищем корни численно."""
    f, conds = eq_expr(eq_text)
    rts = num_roots(f, float(lo) * math.pi, float(hi) * math.pi, n=3000, conds=conds)
    return check_ask(rts, ask, ans, unit=math.pi)


def check_ask(rts, ask, ans, unit=1.0):
    if 'количество' in ask or 'сколько' in ask or 'число корней' in ask:
        return len(rts) == int(ans)
    if 'сумму' in ask:
        return abs(sum(rts) / unit - float(ans)) < 1e-6
    if 'градусах' in ask:
        e = max(rts) if 'наибольший' in ask else min(rts)
        return abs(e / math.pi * 180 - float(ans)) < 1e-6
    if 'произведение' in ask:
        return abs(math.prod(rts) - float(ans)) < 1e-6
    if 'наибольший' in ask:
        return abs(max(rts) - float(ans)) < 1e-7
    if 'наименьший' in ask:
        return abs(min(rts) - float(ans)) < 1e-7
    raise ValueError(ask)


def segment14(r, lens=(F(3, 2), F(3, 2), F(1), F(2))):
    L = r.choice(lens)
    a = F(r.randint(-12, 12), 2)
    return a, a + L


PART_B = ['б) Найдите все корни этого уравнения, принадлежащие отрезку {s}.',
          'б) Найдите все корни этого уравнения, принадлежащие отрезку {s}.',
          'б) Укажите корни этого уравнения, принадлежащие отрезку {s}.']


def q14(r, eq, s, ask):
    """Условие как в КИМ: «а) Решите уравнение …», «б) Найдите все корни этого уравнения, принадлежащие
    отрезку […]»; строка «В ответ запишите …» — числовой итог пункта б для автопроверки."""
    head = 'а) Решите уравнение {f}.'.format(f=fm(eq))
    return head + '\n' + pick(r, *PART_B).format(s=fm(s)) + '\n' + ask


def roots_text(rts):
    out = []
    for e, v in rts:
        out.append(pis(e) if e is not None else f'≈{v * math.pi:.3f}'.replace('.', ',').replace('-', '−'))
    return '; '.join(out)


# формы записи ±sin x и ±cos x через формулы приведения: (текст, знак)
RED_S = [('sin x', 1), ('sin x', 1), ('sin(π − x)', 1), ('cos(π/2 − x)', 1), ('cos(x − π/2)', 1),
         ('sin(x + π)', -1), ('sin(−x)', -1), ('cos(π/2 + x)', -1), ('sin(2π − x)', -1),
         ('cos(3π/2 + x)', 1), ('cos(3π/2 − x)', -1), ('sin(x − π)', -1), ('sin(3π + x)', -1)]
RED_C = [('cos x', 1), ('cos x', 1), ('cos(−x)', 1), ('sin(π/2 + x)', 1), ('sin(π/2 − x)', 1),
         ('cos(π − x)', -1), ('cos(x + π)', -1), ('sin(3π/2 − x)', -1), ('sin(3π/2 + x)', -1),
         ('sin(x − π/2)', -1), ('cos(2π − x)', 1), ('cos(x − 3π)', -1)]
# квадратичная часть: форма = a·t² + b, где t — sin x (для 's') или cos x (для 'c')
SQ_S = [('sin²x', 1, 0), ('cos 2x', -2, 1), ('cos²x', -1, 1), ('sin²(π − x)', 1, 0), ('cos²(π/2 + x)', 1, 0)]
SQ_C = [('cos²x', 1, 0), ('cos 2x', 2, -1), ('sin²x', -1, 1), ('sin²(π/2 + x)', 1, 0), ('cos²(π − x)', 1, 0),
        ('sin²(3π/2 − x)', 1, 0)]


def red(r, base):
    return r.choice(RED_S if base == 's' else RED_C)


def pick_pair(r, pool1, pool2):
    """Два значения t1, t2 с «совместимыми» иррациональностями: сумма и произведение — вида r√m."""
    for _ in range(20):
        t1, t2 = r.choice(pool1), r.choice(pool2)
        if t1 == t2:
            continue
        s = t1 + t2
        p = t1 * t2
        if s is not None and p is not None and p.m == 1:
            return t1, t2, s, p
    return None


def shuffle_sides(r, terms):
    """Часть слагаемых переносим вправо с противоположным знаком → текст «L = R»."""
    terms = [t for t in terms if not qs(t[0]).is_zero()]
    if qs(terms[0][0]).r < 0 and r.random() < 0.85:
        terms = [(-qs(c), b) for c, b in terms]
    left, right = [], []
    for t in terms:
        if left and r.random() < 0.3:
            right.append((-qs(t[0]), t[1]))
        else:
            left.append(t)
    return f'{join_terms(left)} = {join_terms(right)}'


# ================================================================ №14: тригонометрические уравнения

FUN = {'s': 'sin', 'c': 'cos'}


def gen_quad_terms(r, base, t1, t2, s, p):
    """Слагаемые A·F2 + B·L + C для λ(t − t1)(t − t2), t = sin x или cos x. None — если не вышло."""
    form, a, b = r.choice(SQ_S if base == 's' else SQ_C)
    den = math.lcm(s.r.denominator, p.r.denominator)
    lam = den * abs(a) * r.choice([1, 1, 1, 2])
    if r.random() < 0.3:
        lam = -lam
    A = F(lam, a)
    if A.denominator != 1:
        return None
    Bt = -(s * QS(lam))
    rt, sg = red(r, base)
    B = Bt * QS(sg)
    C = QS(p.r * lam - A * b)
    return [(QS(A), form), (B, rt), (C, '')], (lam, -(s * QS(lam)), QS(p.r * lam))


@proto('ep14-trig-quad', 'ege-prof', 14, 'Уравнение, квадратное относительно sin x или cos x',
       invariant='Формулами приведения и cos 2x = 1 − 2sin²x (2cos²x − 1), sin²x + cos²x = 1 уравнение сводится '
                 'к квадратному относительно t = sin x (cos x); корни с |t| > 1 отбрасываются, затем отбор на отрезке.',
       varies='Функция (sin или cos), корни квадратного трёхчлена (стандартные значения и посторонние), '
              'запись через формулы приведения, отрезок отбора, что вписать в ответ.',
       answer_rule='Серии x = ±arccos t + 2πk или x = (−1)ⁿ arcsin t + πn; отбор на отрезке; итог — число корней, '
                   'их сумма (в долях π) или крайний корень в градусах.',
       fipi=r'Решите уравнение (?!.*(log|⋅|tg))(?=.*(cos 2 x|sin 2 [\s​]*[x(]|cos 2 [\s​]*\(|√\( \d+ \) (sin|cos) x = √))(?=.*отрезку)',
       mistakes=['не отбрасывают корень квадратного уравнения с |t| > 1', 'ошибаются в знаке формулы приведения',
                 'теряют корень на границе отрезка', 'путают серии для sin x = a и cos x = a'],
       kim=kim(K14, 'Как в КИМ: «а) Решите уравнение … б) Найдите все корни этого уравнения, принадлежащие отрезку […]», '
                    'формулы приведения и двойного угла в записи; итог пункта б — число.', kes=['2.3', '1.5']))
def gen_ep14_trig_quad(r):
    base = r.choice('sc')
    if r.random() < 0.3:
        return trig_quad_mixed(r, base)
    pr = pick_pair(r, T_OK, T_OK + T_BAD)
    if not pr:
        return None
    t1, t2, s, p = pr
    if s.is_zero() or p.is_zero() and r.random() < 0.5:
        return None
    res = gen_quad_terms(r, base, t1, t2, s, p)
    if not res:
        return None
    terms, (l2, l1, l0) = res
    if not small(terms):
        return None
    eq = shuffle_sides(r, terms)
    lo, hi = segment14(r)
    kind = FUN[base]
    rts = roots_on(series(kind, t1) + series(kind, t2), lo, hi)
    a = ask14(r, rts)
    if not a:
        return None
    ask, ans = a
    tt = 'sin x' if base == 's' else 'cos x'
    good = [t for t in (t1, t2) if abs(t.f()) <= 1]
    bad = [t for t in (t1, t2) if abs(t.f()) > 1]
    e = (f'Пусть t = {tt}: {join_terms([(l2, "t²"), (l1, "t"), (l0, "")])} = 0, t = {t1.text()} или t = {t2.text()}. '
         + (f'Значение {bad[0].text()} не подходит (|t| > 1). ' if bad else '')
         + '; '.join(f'{tt} = {t.text()}' for t in good) + f'. На отрезке: {roots_text(rts)}.')
    return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)


def trig_quad_mixed(r, base):
    """λ(t − t₁)(t − t₂) = 0 с корнями разных иррациональностей: линейный член записан двумя слагаемыми
    (например, 4sin²x + 2√2 sin x − √6 − 2√3 sin x = 0)."""
    irr = [v for v in T_OK if v.m != 1] + [QS(1, 2), QS(-1, 2), QS(1, 3), QS(-1, 3)]
    t1 = r.choice([v for v in T_OK if not v.is_zero()])
    t2 = r.choice([v for v in irr if v.m != t1.m and v != t1])
    lam = 4 if (t1.r.denominator == 2 or t2.r.denominator == 2) else r.choice([1, 2])
    if t1.r.denominator == 2 and t2.r.denominator == 2:
        lam = 4
    form, a, b = r.choice(SQ_S if base == 's' else SQ_C)
    A = F(lam, a)
    if A.denominator != 1:
        lam *= abs(a)
        A = F(lam, a)
    c1, c2 = -(t1 * QS(lam)), -(t2 * QS(lam))
    C = (t1 * t2) * QS(lam)
    C = C - QS(A * b) if (C.m == 1 or A * b == 0) else None
    if C is None:
        # константы разных видов: пишем двумя слагаемыми
        C1, C2 = (t1 * t2) * QS(lam), QS(-A * b)
        consts = [(C1, ''), (C2, '')]
    else:
        consts = [(C, '')]
    rt1, sg1 = red(r, base)
    rt2, sg2 = red(r, base)
    terms = [(QS(A), form), (c1 * QS(sg1), rt1), (c2 * QS(sg2), rt2)] + consts
    if not small(terms, 16):
        return None
    eq = shuffle_sides(r, terms)
    lo, hi = segment14(r)
    kind = FUN[base]
    rts = roots_on(series(kind, t1) + series(kind, t2), lo, hi)
    a_ = ask14(r, rts)
    if not a_:
        return None
    ask, ans = a_
    tt = f'{kind} x'
    e = (f'Относительно t = {tt} уравнение квадратное: {lam}(t − ({t1.text()}))(t − ({t2.text()})) = 0; '
         + '; '.join(f'{tt} = {t.text()}' for t in (t1, t2) if abs(t.f()) <= 1) + f'. На отрезке: {roots_text(rts)}.')
    return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)


BETA = [QS(1), QS(-1), QS(1, 2), QS(-1, 2), QS(1, 3), QS(-1, 3), QS(2), QS(-2), QS(3), QS(-3)]
TAUS = [QS(1), QS(-1), QS(1, 3), QS(-1, 3), QS(F(1, 3), 3), QS(-F(1, 3), 3)]


@proto('ep14-trig-factor', 'ege-prof', 14, 'Тригонометрическое уравнение: вынесение общего множителя',
       invariant='После sin 2x = 2sin x cos x и формул приведения в уравнении есть общий множитель sin x или cos x; '
                 'произведение равно нулю — совокупность двух простейших уравнений.',
       varies='Какой множитель выносится, вторая скобка (sin x = a, cos x = a или tg x = a), коэффициенты, отрезок.',
       answer_rule='Объединяем серии множителей (ни одна не теряется при делении), отбираем корни на отрезке.',
       fipi=r'Решите уравнение (?!.*(log|⋅))(?=.*sin 2 x)(?=.*(sin|cos) (\( |x ))',
       mistakes=['делят на sin x (cos x) и теряют серию', 'ошибка в формуле приведения',
                 'путают sin 2x и 2sin x'],
       kim=kim(K14, 'Как в КИМ: sin 2x и формулы приведения в записи; пункт б — отбор на отрезке.', kes=['2.3', '1.5']))
def gen_ep14_trig_factor(r):
    F1 = r.choice('sc')           # выносимый множитель
    G = 'c' if F1 == 's' else 's'
    k = r.choice([1, 1, 2, 3])
    u_ = r.random()
    if u_ < 0.2:
        # 2m·F − m·k·sin 2x = 2m·F³  ⇒ 2m·F·G·(G − k·F) = 0 (для F = cos: sin x = 0, cos x = 0, tg x = k)
        # 2m·F − m·k·sin 2x = 2m·F³  ⇒  2m·sin x·cos x·(G − k) = 0, G — другая функция
        kk = r.choice([QS(1, 3), QS(F(1, 2), 3), QS(F(1, 2), 2), QS(F(1, 2)), QS(-F(1, 2)), QS(1, 2), QS(2)])
        mm = r.choice([1, 2, 3])
        if (kk * QS(mm)).r.denominator != 1:
            mm *= 2
        fn1 = FUN[F1]
        terms = [(QS(2 * mm), f'{fn1} x'), (-(kk * QS(mm)), 'sin 2x'), (QS(-2 * mm), f'{fn1}³x')]
        sers = series('sin', QS(0)) + series('cos', QS(0)) + series(FUN[G], kk)
        how = (f'2{fn1} x(1 − {fn1}²x) = 2{fn1} x·{FUN[G]}²x, поэтому 2sin x·cos x·({FUN[G]} x − {kk.text()}) = 0: '
               f'sin x = 0, cos x = 0' + (f' или {FUN[G]} x = {kk.text()}' if abs(kk.f()) <= 1 else f' ({FUN[G]} x = {kk.text()} — нет решений)'))
        r.shuffle(terms)
        eq = shuffle_sides(r, terms)
        lo, hi = segment14(r)
        rts = roots_on(sers, lo, hi)
        a_ = ask14(r, rts)
        if not a_:
            return None
        ask, ans = a_
        e = f'{how}. На отрезке: {roots_text(rts)}.'
        return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)
    if u_ < 0.6:
        # k·sin 2x + β·F1' = 0  ⇒ F1·(2k·G + β) = 0
        beta = r.choice(BETA) * QS(k)
        rt, sg = red(r, F1)
        terms = [(QS(k), 'sin 2x'), (beta * QS(sg), rt)]
        gval = QS(-beta.r / (2 * k), beta.m)
        sers = series(FUN[F1], QS(0)) + series(FUN[G], gval)
        how = f'{FUN[F1]} x·(2{FUN[G]} x {"+" if beta.r > 0 else "−"} {QS(abs(beta.r) / k, beta.m).text()}) = 0'
    else:
        # a·F1² + b·sin 2x = 0  ⇒ F1·(a·F1 + 2b·G) = 0 ⇒ tg x = …
        tau = r.choice(TAUS + [QS(2), QS(-2), QS(F(1, 2)), QS(3)])
        # F1 = cos: a·c + 2b·s = 0 ⇒ tg = −a/(2b); F1 = sin: a·s + 2b·c = 0 ⇒ tg = −2b/a
        b = QS(r.choice([1, 1, 2, -1]))
        if F1 == 'c':
            a = -(tau * b * QS(2))
        else:
            if tau.m != 1 and False:
                return None
            inv = QS(1 / tau.r / tau.m, tau.m) if tau.m != 1 else QS(1 / tau.r)
            a = -(b * QS(2) * inv)
        if a is None or a.r.denominator != 1 and a.m == 1 and False:
            return None
        forms = [f for f in (SQ_C if F1 == 'c' else SQ_S) if f[2] == 0]
        form = r.choice(forms)[0]
        terms = [(a, form), (b, 'sin 2x')]
        if a.r.denominator != 1:
            terms = [(a * QS(a.r.denominator), form), (b * QS(a.r.denominator), 'sin 2x')]
        sers = series(FUN[F1], QS(0)) + series('tg', tau)
        how = f'{FUN[F1]} x = 0 или tg x = {tau.text()}'
    r.shuffle(terms)
    eq = shuffle_sides(r, terms)
    lo, hi = segment14(r)
    rts = roots_on(sers, lo, hi)
    a_ = ask14(r, rts)
    if not a_:
        return None
    ask, ans = a_
    e = f'Выносим общий множитель: {how}. На отрезке: {roots_text(rts)}.'
    return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)


# разложения k·sin(x ± φ), k·cos(x ± φ): (текст, коэф. при sin x, коэф. при cos x)
EXPAND = [('2sin(x + π/6)', QS(1, 3), QS(1)), ('2sin(x − π/6)', QS(1, 3), QS(-1)),
          ('2sin(x + π/3)', QS(1), QS(1, 3)), ('2sin(x − π/3)', QS(1), QS(-1, 3)),
          ('2cos(x + π/3)', QS(-1, 3), QS(1)), ('2cos(x − π/3)', QS(1, 3), QS(1)),
          ('2cos(x + π/6)', QS(-1), QS(1, 3)), ('2cos(x − π/6)', QS(1), QS(1, 3)),
          ('√2 sin(x + π/4)', QS(1), QS(1)), ('√2 sin(x − π/4)', QS(1), QS(-1)),
          ('√2 cos(x + π/4)', QS(-1), QS(1)), ('√2 cos(x − π/4)', QS(1), QS(1)),
          ('2sin(π/6 − x)', QS(-1, 3), QS(1)), ('2cos(π/3 − x)', QS(1, 3), QS(1)),
          ('4cos(x + π/4)', QS(-2, 2), QS(2, 2)), ('4sin(x − π/4)', QS(2, 2), QS(-2, 2))]


@proto('ep14-trig-homog1', 'ege-prof', 14, 'Формула синуса (косинуса) суммы: однородное уравнение первой степени',
       invariant='После раскрытия sin(x ± φ) или cos(x ± φ) и приведения подобных уравнение имеет вид '
                 'a·sin x + b·cos x = 0; деление на cos x ≠ 0 даёт tg x = −b/a.',
       varies='Угол φ (π/6, π/3, π/4), множитель, второе слагаемое (запись через формулы приведения), отрезок.',
       answer_rule='x = arctg(τ) + πk; отбор на отрезке.',
       fipi=r'Решите уравнение \d* ?(sin|cos) \( x [+−] π \d \) [+−] \d*\s?√?\(? ?\d? ?\)? ?(sin|cos) \([^)]*\) = 0',
       mistakes=['неверные знаки в формуле sin(α ± β)', 'делят на cos x, не проверив, что cos x ≠ 0',
                 'для tg берут период 2π'],
       kim=kim(K14, 'Как в КИМ: «2sin(x + π/6) − 2√3 sin(π − x) = 0»-подобная запись; отбор на отрезке.',
               kes=['2.3', '1.5']))
def gen_ep14_trig_homog1(r):
    txt, al, be = r.choice(EXPAND)
    Fb = r.choice('sc')
    tau = r.choice(TAUS)
    # txt = al·s + be·c; + B·Fb = 0
    if Fb == 's':
        # (al + B)s + be·c = 0 → tg = −be/(al + B) → al + B = −be/τ
        inv = QS(1 / (tau.r * tau.m), tau.m)
        need = be * inv
        B = (-need) - al if need is not None else None
    else:
        # al·s + (be + B)c = 0 → tg = −(be + B)/al → B = −τ·al − be
        m_ = tau * al
        B = (-m_) - be if m_ is not None else None
    if B is None or B.is_zero() or B.r.denominator != 1 or abs(B.r) > 8:
        return None
    rt, sg = red(r, Fb)
    terms = [(QS(1), txt), (B * QS(sg), rt)]
    eq = shuffle_sides(r, terms)
    lo, hi = segment14(r)
    rts = roots_on(series('tg', tau), lo, hi)
    a_ = ask14(r, rts)
    if not a_:
        return None
    ask, ans = a_
    e = f'Раскрываем {txt} и приводим подобные: получаем tg x = {tau.text()}, x = {pis(ATAN[QS(abs(tau.r), tau.m)] * (1 if tau.r > 0 else -1))} + πk. На отрезке: {roots_text(rts)}.'
    return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)


@proto('ep14-trig-expand', 'ege-prof', 14, 'Формула суммы + сокращение: квадратное уравнение относительно sin или cos',
       invariant='Раскрываем sin(x ± φ) или cos(x ± φ): одно из слагаемых сокращается с правой частью, '
                 'остаётся квадратное уравнение относительно sin x или cos x (через cos 2x или sin²x).',
       varies='Угол φ, функция, корни трёхчлена (включая посторонние |t| > 1), запись через формулы приведения, отрезок.',
       answer_rule='Сокращаем, решаем квадратное относительно t, отбрасываем |t| > 1, отбираем корни на отрезке.',
       fipi=r'Решите уравнение (?=.*(sin|cos) \( (2 )?x [+−] π \d \))(?=.*(cos 2 x|sin 2 x|sin 2 ​\(|cos 2 ​\())',
       mistakes=['не замечают сокращения и получают неоднородное уравнение', 'ошибка в знаке формулы суммы',
                 'не отбрасывают постороннее значение t'],
       kim=kim(K14, 'Как в КИМ: «2sin(x + π/3) + cos 2x = √3cos x + 1»; пункт б — отбор на отрезке.', kes=['2.3', '1.5']))
def gen_ep14_trig_expand(r):
    txt, al, be = r.choice(EXPAND)
    base = r.choice('sc')
    pr = pick_pair(r, T_OK, T_OK + T_BAD)
    if not pr:
        return None
    t1, t2, s, p = pr
    res = gen_quad_terms(r, base, t1, t2, s, p)
    if not res:
        return None
    terms, (l2, l1, l0) = res
    k = QS(1)
    own, other = (al, be) if base == 's' else (be, al)
    # линейный член: нужно l1 = own + B_explicit
    Bx = l1 - own
    if Bx is None or other.is_zero():
        return None
    rt, sg = red(r, base)
    ot, osg = red(r, 'c' if base == 's' else 's')
    lin_terms = [] if Bx.is_zero() else [(Bx * QS(sg), rt)]
    left = [(k, txt), terms[0]] + lin_terms
    right = [(other * QS(osg), ot)]
    C = terms[2][0]
    if r.random() < 0.5:
        right.append((-C, ''))
    else:
        left.append((C, ''))
    r.shuffle(left)
    eq = f'{join_terms(left)} = {join_terms(right)}'
    lo, hi = segment14(r)
    kind = FUN[base]
    rts = roots_on(series(kind, t1) + series(kind, t2), lo, hi)
    a_ = ask14(r, rts)
    if not a_:
        return None
    ask, ans = a_
    tt = FUN[base] + ' x'
    e = (f'После раскрытия {txt} слагаемые с {FUN["c" if base == "s" else "s"]} x сокращаются: '
         f'{join_terms([(l2, "t²"), (l1, "t"), (l0, "")])} = 0, t = {tt}; t = {t1.text()} или {t2.text()}. '
         f'На отрезке: {roots_text(rts)}.')
    return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)


TG_OK = [QS(0), QS(1), QS(-1), QS(1, 3), QS(-1, 3), QS(F(1, 3), 3), QS(-F(1, 3), 3)]


@proto('ep14-trig-tanquad', 'ege-prof', 14, 'Квадратное уравнение относительно tg x (в том числе однородное 2-й степени)',
       invariant='Уравнение a·tg²x + b·tg x + c = 0 или однородное a·sin²x + b·sin x cos x + c·cos²x = 0 '
                 '(делим на cos²x ≠ 0) — квадратное относительно tg x.',
       varies='Корни (стандартные значения tg, иногда нестандартное — через arctg), форма записи, отрезок.',
       answer_rule='tg x = τ₁ или τ₂, x = arctg τ + πk; отбор на отрезке.',
       fipi=r'Решите уравнение (?=.*tg)|Решите уравнение (?=.*sin 2 ​?x ?[+−].*sin x cos x)',
       mistakes=['теряют корни при делении', 'период tg x берут 2π', 'путают arctg √3 и arctg(1/√3)'],
       kim=kim(K14, 'Как в КИМ: «√3tg²x − 4tg x + √3 = 0»; отбор корней на отрезке.', kes=['2.3']))
def gen_ep14_trig_tanquad(r):
    pr = pick_pair(r, TG_OK, TG_OK + [QS(2), QS(-2), QS(3), QS(F(1, 2))])
    if not pr:
        return None
    t1, t2, s, p = pr
    den = math.lcm(s.r.denominator, p.r.denominator)
    lam = den * r.choice([1, 1, 2])
    if lam * p.r == 0 and r.random() < 0.6:
        return None
    a2, a1, a0 = QS(lam), -(s * QS(lam)), QS(lam * p.r)
    if a1.is_zero():
        return None
    if a1.m != 1 and a1.r.denominator == 1 and a0.r.denominator == 1 and r.random() < 0.3:
        pass
    homog = r.random() < 0.45 and not a0.is_zero()
    if homog and a0.r == a2.r and a0.m == a2.m:
        homog = False                   # a(sin²x + cos²x) схлопывается в число — в банке так не пишут
    if homog:
        # a2 sin² + a1 sin cos + a0 cos² = 0; иногда sin x cos x пишем как (1/2)sin 2x
        if r.random() < 0.5 and (a1.r / 2).denominator == 1:
            terms = [(a2, 'sin²x'), (QS(a1.r / 2, a1.m), 'sin 2x'), (a0, 'cos²x')]
        else:
            terms = [(a2, 'sin²x'), (a1, 'sin x cos x'), (a0, 'cos²x')]
        if r.random() < 0.4 and a0.m == 1:
            # a0·cos²x = a0 − a0·sin²x → переносим константу
            terms = [(a2 - a0, 'sin²x')] + terms[1:2] + [(a0, '')]
            if terms[0][0] is None or terms[0][0].is_zero():
                return None
    else:
        terms = [(a2, 'tg²x'), (a1, 'tg x'), (a0, '')]
    eq = shuffle_sides(r, terms)
    lo, hi = segment14(r, (F(1), F(3, 2), F(3, 2), F(2)))
    rts = roots_on(series('tg', t1) + series('tg', t2), lo, hi)
    a_ = ask14(r, rts)
    if not a_:
        return None
    ask, ans = a_
    e = (('Делим на cos²x ≠ 0 (при cos x = 0 равенство неверно): ' if homog else '')
         + f'{join_terms([(a2, "t²"), (a1, "t"), (a0, "")])} = 0 при t = tg x; tg x = {t1.text()} или tg x = {t2.text()}. '
         f'На отрезке: {roots_text(rts)}.')
    return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)


@proto('ep14-trig-cubic', 'ege-prof', 14, 'Тригонометрическое уравнение третьей степени: группировка',
       invariant='Уравнение a·t³ + b·t² + c·t + d = 0 (t = cos x или sin x) раскладывается группировкой '
                 '(at + b)(t² + m) = 0; вторая скобка корней не даёт (или даёт |t| > 1).',
       varies='Функция, корень линейной скобки (стандартные значения), число m, отрезок.',
       answer_rule='t = −b/a, затем серии и отбор на отрезке.',
       fipi=r'(cos|sin) 3 [\s​]*x',
       mistakes=['делят на t² + m, не объяснив, что оно положительно', 'ошибка при группировке',
                 'путают cos³x и cos 3x'],
       kim=kim(K14, 'Как в КИМ: «2cos³x − cos²x + 2cos x − 1 = 0»; отбор корней на отрезке.', kes=['2.3', '2.1']))
def gen_ep14_trig_cubic(r):
    base = r.choice('sc')
    t0 = r.choice([v for v in T_OK if not v.is_zero() and v.m != 2])
    # (a t + b)(t² + m): a·t0 + b = 0, t0 = −b/a
    if t0.m == 1:
        a = t0.r.denominator
        b = QS(-t0.r * a)
        a = QS(a)
    else:
        a = QS(2)
        b = QS(-t0.r * 2, t0.m)
    m = r.choice([1, 1, 2, 3, 4, F(1, 4) * 0 + 5])
    fn = FUN[base]
    terms = [(a, f'{fn}³x'), (b, f'{fn}²x'), (a * QS(m), f'{fn} x'), (b * QS(m), '')]
    eq = shuffle_sides(r, terms)
    lo, hi = segment14(r)
    rts = roots_on(series(fn, t0), lo, hi)
    a_ = ask14(r, rts)
    if not a_:
        return None
    ask, ans = a_
    e = (f'Группировка: ({join_terms([(a, "t"), (b, "")])})(t² + {m}) = 0, t = {fn} x; t² + {m} > 0, '
         f'значит {fn} x = {t0.text()}. На отрезке: {roots_text(rts)}.')
    return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)


# ================================================================ №14: показательные и логарифмические с тригонометрией

NEG_S = ['sin(x + π)', 'sin(−x)', 'sin(x − π)', 'sin(π + x)']
NEG_C = ['cos(π − x)', 'cos(x + π)', 'cos(x − π)', 'cos(3π − x)']


def ypow(B, v):
    """B^v для v ∈ {0, ±1/2, ±1, ±3/2, ±2}: дробь или None (если иррационально)."""
    v = F(v)
    if v.denominator == 1:
        return F(B) ** int(v)
    c = math.isqrt(B)
    if c * c != B:
        return None
    return F(c) ** int(v * 2)


def check14g(eq_text, lo, hi, ask, ans, unit=math.pi):
    f, conds = eq_expr(eq_text)
    rts = num_roots(f, float(lo) * unit, float(hi) * unit, conds=conds)
    return check_ask(rts, ask, ans, unit=unit)


@proto('ep14-exptrig-quad', 'ege-prof', 14, 'Показательное уравнение с тригонометрией в показателе: замена y = a^{sin x}',
       invariant='Замена y = a^{sin x} (a^{cos x}) даёт y + 1/y = c или квадратное уравнение; y > 0, затем '
                 'простейшее тригонометрическое уравнение и отбор корней.',
       varies='Основание (в том числе записанное квадратом: 81 = 9²), функция sin/cos, корни (одно из значений y '
              'может быть посторонним: y ≤ 0 или |sin x| > 1), отрезок.',
       answer_rule='y₁, y₂ → sin x (cos x) = log_a y; отбор на отрезке.',
       fipi=r'Решите уравнение (?=.*\d+ (sin|cos) (x|\())(?=.*\d+ ⋅ \d+ (sin|cos)|.*\d+ (sin|cos) x ​? \+ \d+ (sin|cos) \()|\d+ ⋅ \d+ sin 2 x − \d+ ⋅ \d+ cos 2 x',
       mistakes=['не учитывают y > 0', 'забывают, что a^{sin(x + π)} = a^{−sin x}', 'ошибка в показателе при 81 = 9²'],
       kim=kim(K14, 'Как в КИМ: «16^{sin x} + 16^{sin(x + π)} = 17/4», «9·81^{cos x} − 28·9^{cos x} + 3 = 0»; '
                    'отбор корней на отрезке.', kes=['2.4', '2.3']))
def gen_ep14_exptrig_quad(r):
    fn = r.choice(['sin', 'cos'])
    g = f'{fn} x'
    if r.random() < 0.2:
        # A·(b²)^{sin²x} − B·b^{cos 2x} = C: y = b^{2sin²x}, b^{cos 2x} = b/y ⇒ A·y² − C·y − B·b = 0
        b = r.choice([4, 4, 9, 2, 3])
        opts = [(F(1, 4), F(2) if b == 4 else F(3) if b == 9 else None), (F(1, 2), F(b)),
                (F(3, 4), F(8) if b == 4 else F(27) if b == 9 else None), (F(1), F(b * b))]
        v, y1 = r.choice([o for o in opts if o[1] is not None])
        A, Bc = r.randint(1, 8), r.randint(1, 8)
        C = A * y1 - F(Bc * b) / y1
        if C.denominator != 1 or C == 0:
            mul = C.denominator
            A, Bc, C = A * mul, Bc * mul, C * mul
            if A > 40:
                return None
        C = int(C)
        lhs = (f'{A}·' if A != 1 else '') + f'{b * b}^{{sin²x}}' + ' − ' + (f'{Bc}·' if Bc != 1 else '') + f'{b}^{{cos 2x}}'
        eq = f'{lhs} = {tnum(C)}'
        sv = {F(1, 4): QS(F(1, 2)), F(1, 2): QS(F(1, 2), 2), F(3, 4): QS(F(1, 2), 3), F(1): QS(1)}[v]
        sers = series('sin', sv) + series('sin', -sv)
        lo, hi = segment14(r)
        rts = roots_on(sers, lo, hi)
        a_ = ask14(r, rts)
        if not a_:
            return None
        ask, ans = a_
        e = (f'y = {b}^{{2sin²x}} > 0, {b}^{{cos 2x}} = {b}/y: {A}y² − {C}y − {Bc * b} = 0, y = {fr(y1)} (второй корень '
             f'отрицателен); sin²x = {fr(v)}. На отрезке: {roots_text(rts)}.').replace('− −', '+ ')
        return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)
    if r.random() < 0.45:
        v = r.choice([F(1, 2), F(1, 2), F(1)])
        B = r.choice([4, 9, 16, 25, 36, 49]) if v == F(1, 2) else r.randint(2, 9)
        y = ypow(B, v)
        rhs = y + 1 / y
        neg = r.choice(NEG_S if fn == 'sin' else NEG_C)
        other = pick(r, f'{B}^{{{neg}}}', f'{B}^{{−{g}}}', f'(1/{B})^{{{g}}}')
        mul = rhs.denominator if r.random() < 0.5 else 1
        lhs = f'{B}^{{{g}}} + {other}' if mul == 1 else f'{mul}·{B}^{{{g}}} + {mul}·{other}'
        eq = f'{lhs} = {fr(rhs * mul)}'
        vals = [v, -v]
        e = f'y = {B}^{{{g}}} > 0: y + 1/y = {fr(rhs)}, y = {fr(y)} или y = {fr(1 / y)}; {g} = ±{fr(v)}.'
    else:
        B = r.choice([2, 3, 5, 4, 9, 16])
        vs = [F(0), F(1, 2), F(-1, 2), F(1), F(-1)]
        v1 = r.choice([w for w in vs if ypow(B, w) is not None])
        bad = r.random() < 0.6
        if bad:
            opts = [w for w in (F(2), F(-2), F(3, 2), F(-3, 2)) if ypow(B, w) is not None and w != v1]
            if not opts or r.random() < 0.35:
                y2 = F(-r.randint(1, 5))          # отрицательный корень — посторонний
                v2 = None
            else:
                v2 = r.choice(opts)
                y2 = ypow(B, v2)
        else:
            v2 = r.choice([w for w in vs if ypow(B, w) is not None and w != v1])
            y2 = ypow(B, v2)
        y1 = ypow(B, v1)
        if y1 == y2:
            return None
        q = y1.denominator * y2.denominator
        c2, c1, c0 = q, -(y1 + y2) * q, y1 * y2 * q
        g_ = math.gcd(math.gcd(int(c2), int(c1)), int(c0))
        c2, c1, c0 = c2 // g_, c1 / g_, c0 / g_
        if max(abs(c1), abs(c0), c2) > 120 or c1 == 0 or c0 == 0:
            return None
        big = B * B
        t2 = f'{big}^{{{g}}}' if big <= 400 else f'{B}^{{2{g}}}'
        terms = [(QS(c2), t2), (QS(c1), f'{B}^{{{g}}}'), (QS(c0), '')]
        eq = shuffle_sides(r, terms)
        vals = [v1] + ([v2] if v2 is not None else [])
        e = (f'y = {B}^{{{g}}} > 0: {join_terms([(c2, "y²"), (c1, "y"), (c0, "")])} = 0, y = {fr(y1)} или y = {fr(y2)}. '
             + (f'y = {fr(y2)} < 0 не подходит. ' if y2 < 0 else '') + f'{g} = ' + ' или '.join(fr(w) for w in vals) + '.')
    sers = []
    for w in vals:
        if abs(w) <= 1:
            sers += series(fn, QS(w))
    lo, hi = segment14(r)
    rts = roots_on(sers, lo, hi)
    a_ = ask14(r, rts)
    if not a_:
        return None
    ask, ans = a_
    e += f' На отрезке: {roots_text(rts)}.'
    return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)


def base_txt(p, e):
    v = F(p) ** e
    return str(v) if v.denominator == 1 else f'(1/{v.denominator})'


@proto('ep14-exptrig-equal', 'ege-prof', 14, 'Показательное уравнение: степени одного основания, тригонометрия в показателях',
       invariant='Обе части — степени одного числа; приравниваем показатели и получаем однородное уравнение '
                 '(tg x = c) или уравнение с общим множителем (sin 2x = 2 sin x cos x).',
       varies='Основание и его степени (49 и 1/7, 4 и 8 …), тригонометрические выражения в показателях '
              '(формулы приведения, sin 2x), отрезок.',
       answer_rule='e₁·f₁(x) = e₂·f₂(x), решаем тригонометрическое уравнение, отбор на отрезке.',
       fipi=r'Решите уравнение \(? ?\d+ \d* ?\)? ?(sin|cos) \([^)]*\) ​? = \d+ .*(sin|cos)|Решите уравнение \d+ sin x = \( 1 \d+ \)',
       mistakes=['не меняют знак показателя при основании 1/a', 'ошибка при приведении к одному основанию',
                 'делят на sin x и теряют серию'],
       kim=kim(K14, 'Как в КИМ: «(1/49)^{sin(x + π)} = 7^{2√3 sin(π/2 − x)}»; отбор корней на отрезке.', kes=['2.4', '2.3']))
def gen_ep14_exptrig_equal(r):
    p = r.choice([2, 3, 5, 7])
    e1, e2 = r.sample([1, 2, -1, -2, 3, -3] if p <= 3 else [1, 2, -1, -2], 2)
    F1 = r.choice('sc')
    t1, s1 = red(r, F1)
    k1 = QS(r.choice([1, 1, 2]))
    if r.random() < 0.5:
        tau = r.choice(TAUS)
        G = 'c' if F1 == 's' else 's'
        t2, s2 = red(r, G)
        # e1·k1·s1·F1 = e2·k2·s2·G; F1 = s: tg = e2k2s2/(e1k1s1) = τ; F1 = c: ctg = … → tg = e1k1s1/(e2k2s2)
        if F1 == 's':
            k2 = tau * QS(F(e1 * s1, e2 * s2)) * k1
        else:
            inv = QS(1 / (tau.r * tau.m), tau.m)
            k2 = inv * QS(F(e1 * s1, e2 * s2)) * k1
        if k2 is None or k2.r.denominator != 1 or abs(k2.r) > 6:
            return None
        ex1 = cterm(k1 * QS(1), t1, True)
        ex2 = cterm(k2, t2, True)
        sers = series('tg', tau)
        how = f'tg x = {tau.text()}'
    else:
        # e1·k1·s1·F1 = e2·k2·sin 2x = 2e2k2·F1·G ⇒ F1 = 0 или G = e1k1s1/(2e2k2)
        G = 'c' if F1 == 's' else 's'
        gv = r.choice([v for v in T_OK + T_BAD if not v.is_zero()])
        inv = QS(1 / (gv.r * gv.m), gv.m)
        k2 = inv * QS(F(e1 * s1, 2 * e2)) * k1
        if k2 is None or k2.r.denominator != 1 or abs(k2.r) > 6:
            return None
        ex1 = cterm(k1, t1, True)
        ex2 = cterm(k2, 'sin 2x', True)
        sers = series(FUN[F1], QS(0)) + series(FUN[G], gv)
        how = f'{FUN[F1]} x = 0 или {FUN[G]} x = {gv.text()}'
    eq = f'{base_txt(p, e1)}^{{{ex1}}} = {base_txt(p, e2)}^{{{ex2}}}'
    if r.random() < 0.5:
        eq = f'{base_txt(p, e2)}^{{{ex2}}} = {base_txt(p, e1)}^{{{ex1}}}'
    lo, hi = segment14(r)
    rts = roots_on(sers, lo, hi)
    a_ = ask14(r, rts)
    if not a_:
        return None
    ask, ans = a_
    e = f'Приводим к основанию {p} и приравниваем показатели: {how}. На отрезке: {roots_text(rts)}.'
    return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)


def u_ok(u, sg, x, strict):
    v = sg * (math.sin(x * math.pi) if u == 's' else math.cos(x * math.pi))
    return v > 1e-9 if strict else v > -1e-9


@proto('ep14-trig-domain', 'ege-prof', 14, 'Уравнение с корнем или знаменателем: учёт области определения',
       invariant='Произведение (частное) равно нулю: множитель-многочлен от sin x (cos x) равен нулю при условии, '
                 'что подкоренное выражение неотрицательно (в знаменателе — положительно); корни, где оно нарушено, '
                 'отбрасываются.',
       varies='Квадратный трёхчлен от sin x или cos x, выражение под корнем (±sin x, ±cos x), произведение или дробь, отрезок.',
       answer_rule='Корни множителя с учётом ограничения + (для произведения) нули подкоренного выражения; отбор на отрезке.',
       fipi=r'Решите уравнение .*√\( \d* ?(sin|cos|−)',
       mistakes=['не проверяют знак подкоренного выражения', 'в произведении теряют нули корня',
                 'в дроби оставляют нули знаменателя'],
       kim=kim(K14, 'Как в КИМ: уравнение с √(…) или знаменателем, где ОДЗ отсекает часть серии; отбор корней.',
               kes=['2.3', '2.2']))
def gen_ep14_trig_domain(r):
    base = r.choice('sc')
    pr = pick_pair(r, [v for v in T_OK if not v.is_zero()], T_OK + T_BAD)
    if not pr:
        return None
    t1, t2, s, p = pr
    den = math.lcm(s.r.denominator, p.r.denominator)
    fn = FUN[base]
    q_terms = [(QS(den), f'{fn}²x'), (-(s * QS(den)), f'{fn} x'), (QS(p.r * den), '')]
    if not small(q_terms):
        return None
    u = r.choice('sc')
    sg = r.choice([1, -1])
    utxt = ('−' if sg < 0 else '') + FUN[u] + ' x'
    frac = r.random() < 0.4
    if frac:
        eq = f'({join_terms(q_terms)})/√({utxt}) = 0'
    else:
        eq = pick(r, f'({join_terms(q_terms)})·√({utxt}) = 0', f'√({utxt})·({join_terms(q_terms)}) = 0')
    sers = []
    for t in (t1, t2):
        sers += series(fn, t)
    cand = roots_on(sers + ([] if frac else series(FUN[u], QS(0))), F(-40), F(40))
    lo, hi = segment14(r)
    rts = [(e_, v_) for e_, v_ in roots_on(sers, lo, hi) if u_ok(u, sg, v_, frac)]
    if not frac:
        rts += roots_on(series(FUN[u], QS(0)), lo, hi)
        d = {}
        for e_, v_ in rts:
            d[round(v_, 9)] = (e_, v_)
        rts = [d[k] for k in sorted(d)]
    del cand
    a_ = ask14(r, rts)
    if not a_:
        return None
    ask, ans = a_
    cond = f'{utxt} {">" if frac else "≥"} 0'
    e = (f'Условие {cond}. {fn} x = {t1.text()} или {fn} x = {t2.text()}'
         + ('' if frac else f', а также {FUN[u]} x = 0') + f'; оставляем корни, где {cond}. На отрезке: {roots_text(rts)}.')
    return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)


@proto('ep14-log-trig', 'ege-prof', 14, 'Логарифмическое уравнение с тригонометрией: равенство аргументов и ОДЗ',
       invariant='log_a(f) = log_a(g) ⇔ f = g при g > 0; f − g — квадратный трёхчлен относительно sin x (cos x); '
                 'корни, при которых аргумент не положителен, отбрасываются.',
       varies='Основание логарифма, аргументы (формулы приведения, cos 2x), знак правого аргумента, отрезок.',
       answer_rule='Решаем f = g, отбираем значения с g > 0, серии и отбор на отрезке.',
       fipi=r'Решите уравнение log \d+ \d* ?\(? ?(sin|cos|\d+ (sin|cos))',
       mistakes=['не проверяют положительность аргумента', 'ошибка в формуле двойного угла', 'теряют знак при переносе'],
       kim=kim(K14, 'Как в КИМ: логарифмическое уравнение с тригонометрическими аргументами, ОДЗ отсекает серию; '
                    'отбор корней на отрезке.', kes=['2.4', '2.3']))
def gen_ep14_log_trig(r):
    base = r.choice('sc')
    pr = pick_pair(r, [v for v in T_OK if not v.is_zero()], [v for v in T_OK if not v.is_zero()] + T_BAD)
    if not pr:
        return None
    t1, t2, s, p = pr
    res = gen_quad_terms(r, base, t1, t2, s, p)
    if not res:
        return None
    terms, (l2, l1, l0) = res
    D = r.choice([QS(1), QS(-1), QS(2), QS(-2), QS(1, 2), QS(1, 3)])
    # аргумент слева = λ(t−t1)(t−t2) + D·t
    B, rt = terms[1]
    sgn = next(sg for tx, sg in (RED_S if base == 's' else RED_C) if tx == rt)
    Bt = B * QS(sgn) + D            # коэффициент при t
    if Bt is None:
        return None
    left = [terms[0], (Bt * QS(sgn), rt), terms[2]] if not Bt.is_zero() else [terms[0], terms[2]]
    if not small(left):
        return None
    r.shuffle(left)
    fn = FUN[base]
    b = r.choice([2, 3, 5, 7, '0,5'])
    Lt = join_terms(left)
    Rt = join_terms([(D, f'{fn} x')])
    eq = f'{logb(b)}({Lt}) = {logb(b)}({Rt})'
    lo, hi = segment14(r)
    good = [t for t in (t1, t2) if abs(t.f()) <= 1 and (D.f() * t.f()) > 0]
    sers = []
    for t in good:
        sers += series(fn, t)
    rts = roots_on(sers, lo, hi)
    a_ = ask14(r, rts)
    if not a_:
        return None
    ask, ans = a_
    e = (f'Аргументы равны: {join_terms([(l2, "t²"), (l1, "t"), (l0, "")])} = 0, t = {fn} x; t = {t1.text()} или {t2.text()}. '
         f'Нужно {Rt} > 0: остаётся ' + (', '.join(f'{fn} x = {t.text()}' for t in good) or 'ничего')
         + f'. На отрезке: {roots_text(rts)}.')
    return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)


# ---------------------------------------------------------------- показательные с иррациональными концами отрезка


def end_cands(B):
    """Кандидаты в концы отрезка: (текст, значение)."""
    out = []
    for c in range(2, 10):
        for d in range(2, 60):
            v = math.log(d) / math.log(c)
            if abs(v - round(v)) > 1e-9 and abs(2 * v - round(2 * v)) > 1e-6:
                out.append((f'{logb(c)} {d}', v))
    for n in range(2, 30):
        if math.isqrt(n) ** 2 != n:
            out.append((f'√{n}', math.sqrt(n)))
    return out


ENDS = end_cands(2)


@proto('ep14-exp-roots', 'ege-prof', 14, 'Показательное уравнение: замена t = a^x, отбор корней на отрезке с логарифмами и корнями',
       invariant='Замена t = a^x > 0 сводит уравнение к квадратному (или биквадратному после умножения на a^x); '
                 'корни сравниваются с концами отрезка вида log_c d и √n.',
       varies='Основание, запись степеней (8^x = 2^{3x}, 2^{x+2} = 4·2^x, 2^{5−x}), корни, концы отрезка.',
       answer_rule='x = log_a t для каждого положительного t; сравниваем с концами отрезка (оценки логарифмов и корней).',
       fipi=r'Решите уравнение \d+ x − \d+ ⋅ \d+ x \+ \d+ \+ \d+ \d+ − x',
       mistakes=['не умножают на a^x и теряют корни', 'неверно сравнивают log_c d с корнем',
                 'не отбрасывают отрицательное t'],
       kim=kim(K14, 'Как в КИМ: «8^x − 3·2^{x+2} + 2^{5−x} = 0; корни на [log₄5; √3]»; итог пункта б — число.',
               kes=['2.4', '1.4']))
def gen_ep14_exp_roots(r):
    B = r.choice([2, 2, 3, 3, 5])
    if r.random() < 0.55:
        e1, e2 = sorted(r.sample(range(0, 7 if B == 2 else 5), 2))
        sm = B ** e1 + B ** e2
        k = 0
        while sm % B == 0 and k < 3:
            sm //= B
            k += 1
        P = sm
        m = e1 + e2
        B3 = B ** 3
        t1 = f'{B3}^{{x}}' if r.random() < 0.45 else f'{B}^{{3x}}'
        t2 = (f'{P}·' if P != 1 else '') + (f'{B}^{{x + {k}}}' if k else f'{B}^{{x}}')
        t3 = f'{B}^{{{m} − x}}' if m else f'{B}^{{−x}}'
        eq = pick(r, f'{t1} + {t3} = {t2}', f'{t3} + {t1} = {t2}', f'{t3} + {t1} − {t2} = 0', f'{t1} − {t2} + {t3} = 0')
        xs = [F(e1, 2), F(e2, 2)]
        e = (f'Умножим на t = {B}^{{x}} > 0: t⁴ − {sm * B ** k}t² + {B ** m} = 0, t² = {B ** e1} или {B ** e2}; '
             f'x = {fr(xs[0])} или x = {fr(xs[1])}.')
    else:
        e1, e2 = r.sample(range(-2, 5), 2)
        y1, y2 = F(B) ** e1, F(B) ** e2
        neg = r.random() < 0.3
        if neg:
            y2 = F(-r.randint(1, 6))
        q = y1.denominator * y2.denominator
        c2, c1, c0 = q, -(y1 + y2) * q, y1 * y2 * q
        if c1 == 0 or max(abs(c1), abs(c0)) > 400:
            return None
        k = 0
        c1b = c1
        while c1b % B == 0 and k < 2 and c1b != 0:
            c1b //= B
            k += 1
        t1 = f'{B * B}^{{x}}' if r.random() < 0.6 else f'{B}^{{2x}}'
        t2 = (f'{abs(c1b)}·' if abs(c1b) != 1 else '') + (f'{B}^{{x + {k}}}' if k else f'{B}^{{x}}')
        eq = shuffle_sides(r, [(QS(c2), t1), (QS(-1 if c1 < 0 else 1), t2), (QS(c0), '')])
        xs = [F(e1)] + ([] if neg else [F(e2)])
        e = (f't = {B}^{{x}} > 0: {join_terms([(c2, "t²"), (c1, "t"), (c0, "")])} = 0, t = {fr(y1)} или t = {fr(y2)}'
             + (' (не подходит)' if neg else '') + '; x = ' + ' или '.join(fr(v) for v in xs) + '.')
    # концы отрезка: хотя бы один корень внутри
    xs_f = sorted(float(v) for v in xs)
    lo_c = [c for c in ENDS if xs_f[0] - 1.6 < c[1] < xs_f[-1] + 1.6 and all(abs(c[1] - v) > 0.02 for v in xs_f)]
    lo_c += [(fr(F(v).limit_denominator(2) if False else v), float(v)) for v in (F(k_, 2) for k_ in range(-6, 14))
             if xs_f[0] - 1.6 < v < xs_f[-1] + 1.6]
    if len(lo_c) < 4:
        return None
    for _ in range(80):
        a, b = sorted(r.sample(lo_c, 2), key=lambda c: c[1])
        inside = [v for v in xs if a[1] - 1e-12 <= float(v) <= b[1] + 1e-12]
        mixed = a[0].startswith('log') and b[0].startswith('log') and a[0].split()[0] != b[0].split()[0]
        if inside and b[1] - a[1] < 2.5 and (a[0][0] in 'l√' or b[0][0] in 'l√') and not mixed:
            break                       # как в банке: логарифмы на концах — с одним основанием
    else:
        return None
    a_txt = a[0].replace('-', '−')
    b_txt = b[0].replace('-', '−')
    if r.random() < 0.5:
        ask, ans = 'В ответ запишите количество корней, найденных в пункте б.', F(len(inside))
    else:
        ask, ans = 'В ответ запишите сумму корней, найденных в пункте б.', sum(inside)
    seg = f'[{a_txt}; {b_txt}]'
    e += f' На отрезке {seg}: ' + ('; '.join(fr(v) for v in inside)) + '.'
    q = q14(r, eq, seg, ask)

    def chk():
        lo_v = float(parse_f(a_txt))
        hi_v = float(parse_f(b_txt))
        return check14g(eq, lo_v, hi_v, ask, ans, unit=1.0)
    return pcard(q, num(ans), e), chk


# ================================================================ №16: неравенства

W16 = 30          # окно перебора целых x в генераторе
WCHK = 40         # окно перебора в проверке


def int_set(sat, w=W16):
    return [k for k in range(-w, w + 1) if sat(k)]


def ask16(r, sat, seg=10):
    """Числовой итог: (инструкция, ответ) по множеству целых решений; None — если не подходит."""
    S = int_set(sat)
    bounded_lo = -W16 not in S and -W16 + 1 not in S
    bounded_hi = W16 not in S and W16 - 1 not in S
    opts = []
    if S and bounded_lo and bounded_hi and len(S) <= 25:
        opts += ['sum', 'count']
    if S and bounded_lo and len(S) >= 1:
        opts.append('min')
    if S and bounded_hi:
        opts.append('max')
    inseg = [k for k in S if -seg <= k <= seg]
    if 0 < len(inseg) < 2 * seg + 1 and not (bounded_lo and bounded_hi):
        opts += ['cseg', 'cseg']
    if not opts:
        return None
    k = r.choice(opts)
    if k == 'sum' and sum(S) == 0 and r.random() < 0.7:
        k = 'count'
    if k == 'sum':
        return 'В ответ запишите сумму целых решений неравенства.', sum(S), S
    if k == 'count':
        return 'В ответ запишите количество целых решений неравенства.', len(S), S
    if k == 'min':
        return 'В ответ запишите наименьшее целое решение неравенства.', min(S), S
    if k == 'max':
        return 'В ответ запишите наибольшее целое решение неравенства.', max(S), S
    return (f'В ответ запишите число целых x из отрезка [−{seg}; {seg}], удовлетворяющих неравенству.',
            len(inseg), inseg)


def check16(text, ask, ans):
    """Независимая проверка: разбираем неравенство из текста и перебираем целые x (mpmath, 60 знаков)."""
    import mpmath as mp
    (op, a, b), conds = parse_fd(text)
    val = make_eval(a - b, conds=conds)
    mp.mp.dps = 60
    S = []
    val2 = None
    for k in range(-WCHK, WCHK + 1):
        v = val(k)
        if v is None:
            continue
        z = v == 0
        if not z and abs(v) < mp.mpf(10) ** -30:
            # ноль или просто очень малое число? Точный ноль при удвоенной точности уменьшается вместе с ней
            mp.mp.dps = 140
            val2 = val2 or make_eval(a - b, conds=conds)
            mp.mp.dps = 140
            v2 = val2(k)
            mp.mp.dps = 60
            z = v2 == 0 or abs(v2) < mp.mpf(10) ** -100 and abs(v2) < abs(v) * mp.mpf(10) ** -40
            if not z:
                v = v2
        ok = {'≥': v > 0 or z, '≤': v < 0 or z, '>': v > 0 and not z, '<': v < 0 and not z}[op]
        if ok:
            S.append(k)
    mp.mp.dps = 30
    if '[−' in ask:
        seg = int(ask.split('[−')[1].split(';')[0])
        return len([k for k in S if -seg <= k <= seg]) == ans
    if 'сумм' in ask:
        return -WCHK not in S and WCHK not in S and sum(S) == ans
    if 'число' in ask or 'количество' in ask:
        return -WCHK not in S and WCHK not in S and len(S) == ans
    if 'наименьшее' in ask:
        return -WCHK not in S and S and min(S) == ans
    if 'наибольшее' in ask:
        return WCHK not in S and S and max(S) == ans
    raise ValueError(ask)


INEQ_Q = ['Решите неравенство {f}.']
REL_FLIP = {'≥': '≤', '≤': '≥', '>': '<', '<': '>'}


def card16(r, text, sat, e):
    a_ = ask16(r, sat)
    if not a_:
        return None
    ask, ans, S = a_
    if abs(ans) > 10000:
        return None
    q = pick(r, *INEQ_Q).format(f=fm(text)) + '\n' + ask
    shown = S if len(S) <= 12 else S[:5] + ['…'] + S[-3:]
    e = e + (f' Целые решения: {"; ".join(tnum(k) if k != "…" else k for k in shown)}.' if S else '')
    return pcard(q, num(ans), e), lambda: check16(text, ask, ans)


def ineq_sides(r, terms, rel, p_move=0.3):
    """Σ terms rel 0 → «L rel R» (часть слагаемых перенесена вправо; знак неравенства сохраняется)."""
    terms = [t for t in terms if not qs(t[0]).is_zero()]
    left, right = [], []
    for t in terms:
        if left and r.random() < p_move:
            right.append((-qs(t[0]), t[1]))
        else:
            left.append(t)
    return f'{join_terms(left)} {rel} {join_terms(right)}'


def rel_ok(v, rel):
    """v — знак/значение выражения (Fraction), rel — знак неравенства «выражение rel 0»."""
    return {'≥': v >= 0, '≤': v <= 0, '>': v > 0, '<': v < 0}[rel]


def prod_sign(t, num_roots_, den_roots_, lead=1):
    """Значение (с точностью до положительного множителя) ∏(t − a)^m / ∏(t − b)^m; None — если знаменатель 0."""
    v = F(lead)
    for a, m in den_roots_:
        d = t - a
        if d == 0:
            return None
        v /= d ** m
    for a, m in num_roots_:
        v *= (t - a) ** m
    return v


def poly_from_roots(roots, lead=1):
    """Коэффициенты (старший первый) многочлена lead·∏(t − a)^m."""
    c = [F(lead)]
    for a, m in roots:
        for _ in range(m):
            c = [x - a * y for x, y in zip(c + [F(0)], [F(0)] + c)]
    return c


def xm(a, var='x'):
    """x − a текстом: «x − 3», «x + 2», «x»."""
    a = F(a)
    if a == 0:
        return var
    return f'{var} {"−" if a > 0 else "+"} {fr(abs(a))}'


def pw(B, e):
    """B^{e}: текст степени для множителя (e — целое)."""
    return f'{B}^{{{e}}}'


def expt(B, k, var='x'):
    """B^{x + k} текстом."""
    if k == 0:
        return f'{B}^{{{var}}}'
    return f'{B}^{{{var} {"+" if k > 0 else "−"} {abs(k)}}}'


@proto('ep16-exp-quad', 'ege-prof', 16, 'Показательное неравенство, квадратное относительно t = a^x',
       invariant='Замена t = a^x > 0: t² − pt + q ∨ 0 (в том числе после умножения t + q/t − p ∨ 0 на t > 0); '
                 'промежуток для t переводится в промежуток для x.',
       varies='Основание, корни (степени основания, одна может быть неположительной), форма записи '
              '(a^{2x}, a^{x+k}, a^{k−x}), знак неравенства.',
       answer_rule='t₁ ≤ t ≤ t₂ ⇒ log_a t₁ ≤ x ≤ log_a t₂ (или вне); итог — сумма/количество/крайнее целое решение.',
       fipi=r'Решите неравенство \d+ x \+ \d+ \d+ x − \d+|Решите неравенство \d+ x − \d+ ⋅ \d+ x',
       mistakes=['забывают, что t > 0', 'при a < 1 не меняют знак', 'ошибка при записи a^{x+k} = a^k·a^x'],
       kim=kim(K16, 'Как в КИМ: «Решите неравенство 3^x + 243/3^x − 84 ≤ 0» и т. п.', kes=['2.7', '2.5']))
def gen_ep16_exp_quad(r):
    B = r.choice([2, 3, 5, 2, 3, 7])
    e1, e2 = sorted(r.sample(range(-1, 6 if B == 2 else 4), 2))
    y1, y2 = F(B) ** e1, F(B) ** e2
    neg = r.random() < 0.25
    if neg:
        y1 = F(-r.randint(1, 8))
    rel = r.choice(['≥', '≤', '≥', '≤', '>', '<'])
    sm, pr_ = y1 + y2, y1 * y2
    den = math.lcm(sm.denominator, pr_.denominator)
    if den > 9 or abs(sm * den) > 400 or abs(pr_ * den) > 900 or sm == 0:
        return None
    if r.random() < 0.45 and not neg and den == 1:
        # t + B^{m}/t ∨ S  →  B^{x} + B^{m − x} ∨ S
        m = e1 + e2
        if m > 0:
            tt = pick(r, f'{B}^{{x}} + {B}^{{{m} − x}}', f'{B}^{{{m} − x}} + {B}^{{x}}')
        elif m == 0:
            tt = f'{B}^{{x}} + {B}^{{−x}}'
        else:
            tt = f'{B}^{{x}} + {B}^{{−x − {-m}}}'
        text = f'{tt} {rel} {int(sm)}'
    else:
        c2, c1, c0 = den, int(-sm * den), int(pr_ * den)
        k = 0
        c1b = c1
        while c1b % B == 0 and k < 2:
            c1b //= B
            k += 1
        t2 = pick(r, f'{B * B}^{{x}}', f'{B}^{{2x}}') if B * B < 100 else f'{B}^{{2x}}'
        text = ineq_sides(r, [(QS(c2), t2), (QS(c1b), expt(B, k)), (QS(c0), '')], rel)

    def sat(x):
        t = F(B) ** x
        return rel_ok((t - y1) * (t - y2), rel)
    e = (f't = {B}^{{x}} > 0: (t − {fr(y1)})(t − {fr(y2)}) {rel} 0' if not neg else
         f't = {B}^{{x}} > 0: (t + {fr(-y1)})(t − {fr(y2)}) {rel} 0, первый множитель положителен') + '.'
    return card16(r, text, sat, e)


@proto('ep16-exp-frac', 'ege-prof', 16, 'Показательное неравенство с дробями: замена t = a^x, метод интервалов',
       invariant='Замена t = a^x > 0 приводит к дробно-рациональному неравенству относительно t; '
                 'метод интервалов с учётом t > 0 и нулей знаменателя.',
       varies='Основание, числители и сдвиги в знаменателях, знак неравенства, одна дробь или две.',
       answer_rule='Сводим к одной дроби, метод интервалов по t, переход к x через логарифм.',
       fipi=r'Решите неравенство (?!.*log)(?!.*x 2)(?=.*\d+ x)',
       mistakes=['умножают на знаменатель без учёта знака', 'включают нули знаменателя', 'забывают t > 0'],
       kim=kim(K16, 'Как в КИМ: «4/(3^x − 27) ≥ 1/(3^x − 9)», «1/(3^x + 21) + 1/(3^x − 27) ≥ 0».', kes=['2.7', '2.5']))
def gen_ep16_exp_frac(r):
    B = r.choice([2, 3, 5, 2, 3, 4])
    rel = r.choice(['≥', '≤', '>', '<'])
    pool = [B ** k for k in range(0, 5) if B ** k <= 130] + [-B ** k for k in range(0, 3)] + [r.randint(5, 40)]
    t_ = expt(B, 0)
    if r.random() < 0.5:
        c1, c2 = r.sample(pool, 2)
        p, q = r.sample(range(1, 12), 2)
        a1, a0 = p - q, -p * c2 + q * c1
        if a1 == 0:
            return None
        text = f'{p}/({t_} {"−" if c1 > 0 else "+"} {abs(c1)}) {rel} {q}/({t_} {"−" if c2 > 0 else "+"} {abs(c2)})'
        if r.random() < 0.4:
            text = f'{q}/({t_} {"−" if c2 > 0 else "+"} {abs(c2)}) {REL_FLIP[rel]} {p}/({t_} {"−" if c1 > 0 else "+"} {abs(c1)})'

        def sat(x):
            t = F(B) ** x
            if t == c1 or t == c2:
                return False
            return rel_ok(F(p) / (t - c1) - F(q) / (t - c2), rel)
        e = f't = {B}^{{x}} > 0: ({join_terms([(a1, "t"), (a0, "")])})/(({xm(c1, "t")})({xm(c2, "t")})) {rel} 0.'
    else:
        c1 = r.choice([c for c in pool if c > 0])
        c2 = r.choice([B ** k for k in range(1, 5) if B ** k <= 130])
        m1, m2 = r.choice([(1, 1), (2, 1), (1, 2), (1, 3), (3, 1), (2, 3), (3, 2), (1, 4)])
        text = f'{m1}/({t_} + {c1}) + {m2}/({t_} − {c2}) {rel} 0'
        if r.random() < 0.5:
            text = f'{m2}/({t_} − {c2}) + {m1}/({t_} + {c1}) {rel} 0'

        def sat(x):
            t = F(B) ** x
            if t == c2:
                return False
            return rel_ok(F(m1) / (t + c1) + F(m2) / (t - c2), rel)
        e = f't = {B}^{{x}} > 0: ({join_terms([(m1 + m2, "t"), (m2 * c1 - m1 * c2, "")])})/(({xm(-c1, "t")})({xm(c2, "t")})) {rel} 0.'
    return card16(r, text, sat, e)


@proto('ep16-exp-poly', 'ege-prof', 16, 'Показательное неравенство третьей степени относительно t = a^x (кратный корень)',
       invariant='После замены t = a^x — многочлен третьей степени, раскладывается на множители (часто с кратным корнем); '
                 'метод интервалов с учётом кратности и t > 0.',
       varies='Основание, корни многочлена (степени основания), кратность, запись степеней (a^{3x}, 4^{x+1}, a^{x+2}).',
       answer_rule='Знаки по интервалам t; в точке кратного корня знак не меняется — изолированная точка решения.',
       fipi=r'Решите неравенство \d+ \d+ x − \d+ ⋅ \d+ x \+ \d+ \+ \d+ ⋅ \d+ x|Решите неравенство \d+ x − \d+ ⋅ \d+ x \+ \d+ \+ \d+ ⋅ \d+ x \+ \d+',
       mistakes=['теряют изолированную точку кратного корня', 'меняют знак в кратном корне', 'ошибка в разложении'],
       kim=kim(K16, 'Как в КИМ: «2^{3x} − 2·4^{x+1} + 5·2^{x+2} − 16 ≥ 0».', kes=['2.7', '2.5']))
def gen_ep16_exp_poly(r):
    B = r.choice([2, 3, 2, 3, 5])
    cand = [F(B) ** k for k in range(-1, 4) if F(B) ** k <= 64]
    dbl = r.random() < 0.7
    if dbl:
        a, b = r.sample(cand, 2)
        roots = [(a, 2), (b, 1)]
    else:
        roots = [(v, 1) for v in r.sample(cand, 3)]
    c = poly_from_roots(roots)
    den = math.lcm(*[x.denominator for x in c])
    c = [int(x * den) for x in c]
    if max(abs(x) for x in c) > 700:
        return None
    rel = r.choice(['≥', '≤', '>', '<'])
    terms = []
    for pwr, co in zip((3, 2, 1, 0), c):
        if co == 0:
            continue
        if pwr == 0:
            terms.append((QS(co), ''))
            continue
        base = B ** pwr
        if pwr == 1:
            k = 0
            cc = co
            while cc % B == 0 and k < 2 and r.random() < 0.7:
                cc //= B
                k += 1
            terms.append((QS(cc), expt(B, k)))
        elif pwr == 3:
            terms.append((QS(co), f'{base}^{{x}}' if base <= 125 and r.random() < 0.75 else f'{B}^{{3x}}'))
        else:
            terms.append((QS(co), pick(r, f'{base}^{{x}}', f'{B}^{{2x}}')))
    text = ineq_sides(r, terms, rel, 0.25)

    def sat(x):
        t = F(B) ** x
        return rel_ok(prod_sign(t, roots, []), rel)
    e = f't = {B}^{{x}} > 0: ' + '·'.join(f'({xm(a, "t")})' + ('²' if m == 2 else '') for a, m in roots) + f' {rel} 0.'
    return card16(r, text, sat, e)


@proto('ep16-exp-grouping', 'ege-prof', 16, 'Неравенство: группировка показательного числителя и метод рационализации',
       invariant='Числитель (ab)^x − … раскладывается группировкой в (a^x − a^p)(b^x − b^q); знак a^x − a^p совпадает '
                 'со знаком x − p; неравенство сводится к рациональному.',
       varies='Основания a, b, показатели p, q, знаменатель (квадратный трёхчлен с целыми корнями), знак.',
       answer_rule='Метод интервалов для (x − p)(x − q)/((x − r₁)(x − r₂)) с учётом знака старшего коэффициента.',
       fipi=r'Решите неравенство (?!.*log)(?=.*\d+ x ?[−+])(?=.*x 2)',
       mistakes=['не видят группировки', 'забывают про знак старшего коэффициента знаменателя', 'включают нули знаменателя'],
       kim=kim(K16, 'Как в КИМ: «(10^x − 25·2^x − 2·5^x + 50)/(5x − x² − 4) ≥ 0».', kes=['2.7', '2.5']))
def gen_ep16_exp_grouping(r):
    a, b = r.sample([2, 3, 5, 7], 2)
    p, q = r.choice([0, 1, 2, 3]), r.choice([0, 1, 2])
    if p == 0 and q == 0 or a ** p * b ** q > 400:
        return None
    ap, bq = a ** p, b ** q
    r1, r2 = r.sample(range(-4, 8), 2)
    sgn = r.choice([1, -1])
    c2, c1, c0 = sgn, -sgn * (r1 + r2), sgn * r1 * r2
    rel = r.choice(['≥', '≤', '>', '<'])
    parts = [(QS(1), f'{a * b}^{{x}}'), (QS(-bq), f'{a}^{{x}}'), (QS(-ap), f'{b}^{{x}}'), (QS(ap * bq), '')]
    first = parts[0]
    rest = parts[1:]
    r.shuffle(rest)
    numt = join_terms([first] + rest)
    dt = [(QS(c2), 'x²'), (QS(c1), 'x'), (QS(c0), '')]
    r.shuffle(dt)
    dent = join_terms(dt)
    text = f'({numt})/({dent}) {rel} 0'

    def sat(x):
        d = sgn * (x - r1) * (x - r2)
        if d == 0:
            return False
        return rel_ok(F((x - p) * (x - q)) / d, rel)
    e = (f'Числитель = ({a}^{{x}} − {ap})({b}^{{x}} − {bq}), знак как у ({xm(p)})({xm(q)}); '
         f'знаменатель {"" if sgn > 0 else "−"}({xm(r1)})({xm(r2)}).')
    return card16(r, text, sat, e)


@proto('ep16-exp-square', 'ege-prof', 16, 'Неравенство с полным квадратом показательного выражения в знаменателе',
       invariant='Знаменатель — полный квадрат (a^{x²} − a^c)², он положителен везде, кроме нулей; числитель '
                 'раскладывается группировкой с кратным корнем.',
       varies='Основание, c (нули знаменателя x = ±√c), числитель (x − p)(x − q)², знак неравенства.',
       answer_rule='Знак дроби = знак числителя, исключаем нули знаменателя; кратный корень — изолированная точка.',
       fipi=r'Решите неравенство \d* ?x \d+ [+−] \d* ?x \d+ [+−] \d* ?x [+−] \d+ \d+ x \d+ [+−] \d+ ⋅ \d+ x \d+ \+ \d+',
       mistakes=['забывают исключить нули знаменателя', 'теряют изолированную точку кратного корня',
                 'делят на квадрат, не проверив, что он ≠ 0'],
       kim=kim(K16, 'Как в КИМ: «(x³ + x² − x − 1)/(4^{x²} − 8·2^{x²} + 16) ≥ 0».', kes=['2.7', '2.5']))
def gen_ep16_exp_square(r):
    B = r.choice([2, 3])
    c = r.choice([1, 2, 4, 1, 2])
    p, q = r.sample(range(-3, 4), 2)
    # числитель (x − p)(x − q)²
    cf = poly_from_roots([(F(p), 1), (F(q), 2)])
    cf = [int(x) for x in cf]
    rel = r.choice(['≥', '≤'])
    K = B ** c
    if K > 20:                     # масштаб банка: 4^{x²} − 8·2^{x²} + 16
        return None
    dent = f'{B * B}^{{x²}} − {2 * K}·{B}^{{x²}} + {K * K}'
    numt = poly(cf)
    text = f'({numt})/({dent}) {rel} 0'

    def sat(x):
        if x * x == c:
            return False
        return rel_ok(F((x - p) * (x - q) ** 2), rel)
    rc = str(math.isqrt(c)) if math.isqrt(c) ** 2 == c else f'√{c}'
    e = f'Знаменатель ({B}^{{x²}} − {K})² > 0 при x ≠ ±{rc}; числитель ({xm(p)})({xm(q)})².'
    return card16(r, text, sat, e)


@proto('ep16-log-square', 'ege-prof', 16, 'Логарифмическое неравенство, квадратное относительно log',
       invariant='Замена t = log_a(u(x)), где u = c − x² или x² − c: квадратное неравенство для t, затем '
                 'u ≤ a^{t₁} или u ≥ a^{t₂} вместе с u > 0.',
       varies='Основание, выражение u(x), корни t₁, t₂, знак неравенства.',
       answer_rule='Промежутки для u → промежутки для x (с учётом ОДЗ u > 0).',
       fipi=r'Решите неравенство .*log \d+,?\d* 2 \( ',
       mistakes=['забывают ОДЗ u > 0', 'неверно переходят от log к аргументу при a < 1', 'теряют симметричный промежуток'],
       kim=kim(K16, 'Как в КИМ: «log₂²(25 − x²) − 7log₂(25 − x²) + 12 ≥ 0».', kes=['2.7']))
def gen_ep16_log_square(r):
    b = r.choice([2, 3, 2, 5])
    t1, t2 = sorted(r.sample(range(0, 5 if b == 2 else 3), 2))
    kind = r.choice(['c−x²', 'x²−c'])
    C = r.choice([9, 16, 25, 36, 49, 64, 81, 10, 17, 26, 30, 40, 50])
    if kind == 'c−x²':
        if b ** t2 >= C and r.random() < 0.7:
            return None
        u = f'{C} − x²'
    else:
        u = f'x² − {C}'
    rel = r.choice(['≥', '≤'])
    s1, p1 = t1 + t2, t1 * t2
    text = f'{logb(b)}²({u}){cterm(-s1, f"{logb(b)}({u})")}{cterm(p1, "") if p1 else ""} {rel} 0'

    def sat(x):
        uv = C - x * x if kind == 'c−x²' else x * x - C
        if uv <= 0:
            return False
        lo_, hi_ = F(b) ** t1, F(b) ** t2
        v = (uv - lo_) * (uv - hi_)          # тот же знак, что (t − t1)(t − t2), т. к. log монотонен
        return rel_ok(F(v), rel)
    e = (f't = {logb(b)}({u}): (t − {t1})(t − {t2}) {rel} 0, т. е. ' +
         (f'{u} ≤ {b ** t1} или {u} ≥ {b ** t2}' if rel == '≥' else f'{b ** t1} ≤ {u} ≤ {b ** t2}') + f', причём {u} > 0.')
    return card16(r, text, sat, e)


@proto('ep16-log-frac', 'ege-prof', 16, 'Логарифмическое неравенство, дробно-рациональное относительно t = log_a x',
       invariant='Логарифмы произведений и степеней выражаются через t = log_a x (log_a(a^k x) = t + k, '
                 'log_a x^m = m·t); получаем рациональное неравенство по t, метод интервалов, возврат к x > 0.',
       varies='Основание, корни числителя и знаменателя (целые t), запись множителей через логарифмы, знак.',
       answer_rule='Промежутки для t переводим в x = a^t (a > 1 — сохраняем порядок), ОДЗ x > 0.',
       fipi=r'Решите неравенство .*(log \d+ 2 x|log \d+ x [+−] \d+ \+ log|\d+ log \d+ x − \d+|log \d+ x log \d+)|\d+ log \d+ x [−+] log \d+',
       mistakes=['забывают ОДЗ x > 0', 'сокращают на выражение с переменной', 'включают нули знаменателя'],
       kim=kim(K16, 'Как в КИМ: дробь с log₃(81x), log₃x − 4 и т. п.; метод интервалов.', kes=['2.7', '2.5']))
def gen_ep16_log_frac(r):
    b = r.choice([2, 3, 2])
    k = r.choice([2, 3])          # число различных критических точек в t
    ts = r.sample(range(-2, 5 if b == 2 else 4), k + 1)
    nums = ts[:k] if k == 2 else ts[:2]
    dens = [ts[-1]]
    rel = r.choice(['≥', '≤', '>', '<'])

    def factor(c):
        # t − c разными записями
        if c == 0:
            return pick(r, f'{logb(b)}(x)', f'{logb(b)}(x)')
        v = F(b) ** (-c)
        opts = [f'({logb(b)}(x) {"−" if c > 0 else "+"} {abs(c)})']
        if v.denominator == 1:
            opts.append(f'{logb(b)}({v}x)')
        else:
            opts.append(f'{logb(b)}(x/{v.denominator})')
        return r.choice(opts)
    numt = '·'.join(factor(c) for c in nums)
    dent = factor(dens[0])
    if dent.startswith('(') and dent.endswith(')'):
        dent = dent[1:-1]
    text = f'{numt}/({dent}) {rel} 0' if r.random() < 0.5 else f'({numt})/({dent}) {rel} 0'
    text = text.replace('((', '(').replace('))/', ')/') if text.count('(') != text.count(')') else text

    def sat(x):
        if x <= 0:
            return False
        # t = log_b x; знак (t − c) совпадает со знаком x − b^c
        v = F(1)
        for c in nums:
            v *= (x - F(b) ** c)
        d = x - F(b) ** dens[0]
        if d == 0:
            return False
        return rel_ok(v / d, rel)
    e = (f't = {logb(b)} x: ' + '·'.join(f'({xm(c, "t")})' for c in nums) + f'/({xm(dens[0], "t")}) {rel} 0; '
         f'знак t − c совпадает со знаком x − {b}^c; x > 0.')
    return card16(r, text, sat, e)


@proto('ep16-log-sum', 'ege-prof', 16, 'Сумма логарифмов с одним основанием: ОДЗ и переход к аргументам',
       invariant='log_a f + log_a g ∨ log_a h (или разность) — по свойствам логарифма f·g ∨ h (f ∨ g·h) с учётом '
                 'ОДЗ f, g, h > 0 и направления монотонности (a > 1 или 0 < a < 1).',
       varies='Основание (в том числе 0 < a < 1), линейные выражения под логарифмами, сумма или разность, знак.',
       answer_rule='Система: ОДЗ + рациональное неравенство для аргументов; метод интервалов.',
       fipi=r'Решите неравенство log \d+,?\d* \( [^)]*\)+ [+−] log|≥ log \d+ \( [^)]*\) \+ log|log \d+ \( \( .*\) \) (≥|≤) log|log \d+,?\d* \( x 3|log \d+ \( \( x',
       mistakes=['забывают ОДЗ одного из логарифмов', 'при основании < 1 не меняют знак',
                 'переходят к аргументам до приведения к одному логарифму'],
       kim=kim(K16, 'Как в КИМ: «log₅(3x + 1) + log₅(…) ≥ log₅(…)».', kes=['2.7']))
def gen_ep16_log_sum(r):
    b = r.choice([2, 3, 5, 7, '0,5'])
    inc = b != '0,5'

    def lin_(quad=False):
        if quad:
            return (1, r.choice([0, 0, 1, -1, 2]), r.randint(1, 9))
        return (0, r.choice([1, 1, 2, 3, 4, 5, -1, -2, -3]), r.randint(-12, 12))
    qi = r.choice([None, None, 0, 1, 2])
    f, g, h = [lin_(qi == i) for i in range(3)]
    rel = r.choice(['≥', '≤'])
    mode = r.choice(['sum', 'diff'])
    lt = lambda km: poly(list(km)) if km[0] else poly([km[1], km[2]])
    if mode == 'sum':
        text = f'{logb(b)}({lt(f)}) + {logb(b)}({lt(g)}) {rel} {logb(b)}({lt(h)})'
    else:
        text = f'{logb(b)}({lt(f)}) − {logb(b)}({lt(g)}) {rel} {logb(b)}({lt(h)})'

    def sat(x):
        fv, gv, hv = [u[0] * x * x + u[1] * x + u[2] for u in (f, g, h)]
        if fv <= 0 or gv <= 0 or hv <= 0:
            return False
        lhs, rhs = (fv * gv, hv) if mode == 'sum' else (fv, gv * hv)
        d = lhs - rhs
        return rel_ok(F(d if inc else -d), rel)
    if not any(sat(x) for x in range(-W16, W16)):
        return None
    e = (f'ОДЗ: {lt(f)} > 0, {lt(g)} > 0, {lt(h)} > 0. ' +
         (f'({lt(f)})({lt(g)}) {rel if inc else REL_FLIP[rel]} {lt(h)}' if mode == 'sum'
          else f'{lt(f)} {rel if inc else REL_FLIP[rel]} ({lt(g)})({lt(h)})') + '.')
    return card16(r, text, sat, e)


@proto('ep16-log-varbase', 'ege-prof', 16, 'Логарифмическое неравенство с переменным основанием',
       invariant='log_{g(x)} h(x) ∨ c ⇔ (с учётом g > 0, g ≠ 1, h > 0) (g − 1)(h − g^c) ∨ 0 — метод рационализации.',
       varies='Основание g(x) (x + k, kx), аргумент h(x) (линейный или квадратный), число c (0, 1, 2), знак.',
       answer_rule='ОДЗ + знак произведения (g − 1)(h − g^c); метод интервалов.',
       fipi=r'Решите неравенство .*log \(|Решите неравенство .*log x',
       mistakes=['рассматривают только случай g > 1', 'забывают g ≠ 1', 'теряют ОДЗ h > 0'],
       kim=kim(K16, 'Как в КИМ: логарифм с основанием, зависящим от x; метод рационализации.', kes=['2.7']))
def gen_ep16_log_varbase(r):
    gk, gm = r.choice([(1, r.randint(-4, 5)), (2, r.randint(-3, 3)), (1, r.randint(1, 6))])
    c = r.choice([1, 1, 2, 0])
    if r.random() < 0.12:
        hk, hm = r.choice([1, 2, 3, 4, 5, -1, -2]), r.randint(-12, 12)
        hq = 0
    else:
        hq, hk, hm = r.choice([1, 1, 2, -1]), r.randint(-7, 7), r.randint(-9, 12)
    c = r.choice([1, 2, 1, 2, 0])
    rel = r.choice(['≥', '≤', '>', '<'])
    gt = poly([gk, gm])
    ht = poly([hq, hk, hm]) if hq else poly([hk, hm])
    base_ = gt.replace(' ', '')
    text = f'{logb(base_)}({ht}) {rel} {c}'

    def sat(x):
        g = gk * x + gm
        h = hq * x * x + hk * x + hm
        if g <= 0 or g == 1 or h <= 0:
            return False
        return rel_ok(F((g - 1) * (h - g ** c)), rel)
    if 'x' not in ht or len(int_set(sat)) < 1:
        return None
    gc = '1' if c == 0 else f'({gt})' + ('' if c == 1 else f'^{{{c}}}')
    e = f'ОДЗ: {gt} > 0, {gt} ≠ 1, {ht} > 0. Рационализация: ({gt} − 1)({ht} − {gc}) {rel} 0.'
    return card16(r, text, sat, e)


@proto('ep16-log-product', 'ege-prof', 16, 'Произведение (частное) многочлена и логарифма: метод рационализации',
       invariant='Знак log_a(u) при a > 1 совпадает со знаком u − 1 (на ОДЗ u > 0); неравенство сводится '
                 'к рациональному, метод интервалов.',
       varies='Многочлен с целыми корнями, аргумент логарифма (линейный или вида c·a^x), произведение или частное, знак.',
       answer_rule='Заменяем log_a u на (u − 1), решаем методом интервалов с учётом ОДЗ.',
       fipi=r'Решите неравенство .*(\) ⋅ log \d+ \(|x 2 [+−] \d* ?x [+−] \d+ log|log \d+ \( \d+ x \) ⋅ log)',
       mistakes=['забывают ОДЗ логарифма', 'считают логарифм всегда положительным', 'теряют корень многочлена'],
       kim=kim(K16, 'Как в КИМ: «(x² + 4x − 5)·log₃(0,2·5^x) ≥ 0».', kes=['2.7', '2.5']))
def gen_ep16_log_product(r):
    p, q = r.sample(range(-5, 6), 2)
    cf = poly_from_roots([(F(p), 1), (F(q), 1)])
    b = r.choice([2, 3, 5, '0,5'])
    inc = b != '0,5'
    rel = r.choice(['≥', '≤', '>', '<'])
    if r.random() < 0.5:
        k, m = r.choice([1, 2, 3, -1]), r.randint(-6, 8)
        ut = poly([k, m])
        uf = lambda x: F(k * x + m)
    else:
        B = r.choice([2, 3, 5])
        s = r.randint(-2, 3)
        v = F(B) ** (-s)
        ut = f'{fr(v).replace("/", "/") if v.denominator == 1 else ftxt(v) if finite(v) else fr(v)}·{B}^{{x}}'
        if v.denominator != 1 and not finite(v):
            ut = f'{B}^{{x}}/{v.denominator}'
        if v == 1:
            ut = f'{B}^{{x}}'
        uf = lambda x: v * F(B) ** x
    frac = r.random() < 0.35
    pt = poly([int(x) for x in cf])
    text = f'({pt})/{logb(b)}({ut}) {rel} 0' if frac else f'({pt})·{logb(b)}({ut}) {rel} 0'

    def sat(x):
        u = uf(x)
        if u <= 0:
            return False
        lg = (u - 1) if inc else (1 - u)
        if frac and lg == 0:
            return False
        P = F((x - p) * (x - q))
        return rel_ok(P / lg if frac else P * lg, rel)
    e = f'ОДЗ: {ut} > 0. Знак {logb(b)}({ut}) совпадает со знаком {"" if inc else "−"}({ut} − 1); многочлен = ({xm(p)})({xm(q)}).'
    return card16(r, text, sat, e)


@proto('ep16-radical', 'ege-prof', 16, 'Неравенство с квадратным корнем в произведении или частном',
       invariant='√f(x)·g(x) ∨ 0: ОДЗ f ≥ 0; нули f входят в решение нестрогого неравенства, в остальных точках '
                 'знак определяется g(x). В частном g/√f — f > 0.',
       varies='Подкоренное выражение (линейное или квадратное), множитель g (квадратный трёхчлен), произведение/частное, знак.',
       answer_rule='Объединяем нули корня (для ≥, ≤ в произведении) и решения g ∨ 0 на ОДЗ.',
       fipi=r'Решите неравенство .*√\( ?\d* ?x|Решите неравенство .*√ ?\(',
       mistakes=['теряют нули подкоренного выражения', 'забывают ОДЗ', 'делят на корень, не исключив нули'],
       kim=kim(K16, 'Как в КИМ: неравенство с корнем, где решающую роль играет ОДЗ.', kes=['2.6', '2.5']))
def gen_ep16_radical(r):
    if r.random() < 0.5:
        fk, fm_ = r.choice([1, -1, 2, -2]), r.randint(-6, 8)
        ft = poly([fk, fm_])
        ff = lambda x: fk * x + fm_
    else:
        a1, a2 = sorted(r.sample(range(-6, 7), 2))
        sg = r.choice([1, -1])
        cf = poly_from_roots([(F(a1), 1), (F(a2), 1)], sg)
        ft = poly([int(x) for x in cf])
        ff = lambda x: sg * (x - a1) * (x - a2)
    p, q = r.sample(range(-6, 7), 2)
    cg = poly_from_roots([(F(p), 1), (F(q), 1)])
    gt = poly([int(x) for x in cg])
    rel = r.choice(['≥', '≤', '>', '<'])
    frac = r.random() < 0.3
    text = f'({gt})/√({ft}) {rel} 0' if frac else pick(r, f'({gt})·√({ft}) {rel} 0', f'√({ft})·({gt}) {rel} 0')

    def sat(x):
        fv = ff(x)
        if fv < 0 or frac and fv == 0:
            return False
        if fv == 0:
            return rel in ('≥', '≤')
        return rel_ok(F((x - p) * (x - q)), rel)
    e = (f'ОДЗ: {ft} {">" if frac else "≥"} 0. ' + ('' if frac else f'Нули {ft} — решения нестрогого неравенства; ')
         + f'{"в" if not frac else "На ОДЗ"} остальных точках знак как у ({gt}).').replace('На ОДЗ остальных', 'На ОДЗ')
    return card16(r, text, sat, e)


@proto('ep16-rational', 'ege-prof', 16, 'Дробно-рациональное неравенство: приведение к общему знаменателю',
       invariant='Переносим всё в одну часть, приводим к общему знаменателю, раскладываем числитель; '
                 'метод интервалов с исключением нулей знаменателя.',
       varies='Дроби вида A/(x − a) + B/(x − b) и правая часть, знак неравенства.',
       answer_rule='Метод интервалов для P(x)/((x − a)(x − b)) ∨ 0.',
       fipi=r'Решите неравенство \d+ x [+−] \d+ \+ \d+ x [+−] \d+ ≥|Решите неравенство x \d+ [+−] .* x [+−] \d+ ≤',
       mistakes=['умножают на знаменатель без учёта знака', 'включают нули знаменателя', 'ошибка в общем знаменателе'],
       kim=kim(K16, 'Как в КИМ: рациональное неравенство, метод интервалов.', kes=['2.5']))
def gen_ep16_rational(r):
    a, b = r.sample(range(-9, 10), 2)
    A, B_ = r.choice([1, 2, 3, -1, 4, 5, 6, 7, -3]), r.choice([1, 2, 3, -2, 5, -4, 6])
    C = r.choice([0, 1, 1, 2, -1, 3, -2])
    if abs(A) == abs(B_) or abs(a) == abs(b) or abs(C) in (abs(A), abs(B_)):
        return None
    rel = r.choice(['≥', '≤', '>', '<'])

    def fr_(k, a_):
        return f'{k}/(x {"−" if a_ > 0 else "+"} {abs(a_)})' if a_ else f'{k}/x'
    lhs = fr_(A, a) + (f' + {fr_(B_, b)}' if B_ > 0 else f' − {fr_(-B_, b)}')
    if r.random() < 0.5:
        lhs = fr_(B_, b) + (f' + {fr_(A, a)}' if A > 0 else f' − {fr_(-A, a)}')
    text = f'{lhs} {rel} {tnum(C)}'

    def sat(x):
        if x == a or x == b:
            return False
        return rel_ok(F(A, x - a) + F(B_, x - b) - C, rel)
    S = int_set(sat)
    if not S:
        return None
    e = f'Переносим всё влево и приводим к знаменателю ({xm(a)})({xm(b)}); метод интервалов, x ≠ {tnum(a)}, x ≠ {tnum(b)}.'
    return card16(r, text, sat, e)


# ================================================================ №19: параметр — точная арифметика в Q(√D)


def sqfree(n):
    """n = k²·m → (k, m), m свободно от квадратов (n > 0 — целое)."""
    k, m, d = 1, n, 2
    while d * d <= m:
        while m % (d * d) == 0:
            m //= d * d
            k *= d
        d += 1
    return k, m


class QD:
    """Число p + q·√D (D > 1 свободно от квадратов) или рациональное (q = 0)."""
    __slots__ = ('p', 'q', 'D')

    def __init__(self, p, q=0, D=1):
        self.p, self.q, self.D = F(p), F(q), D
        if self.q == 0 or D == 1:
            self.p += self.q if D == 1 else 0
            self.q, self.D = F(0), 1

    @staticmethod
    def of(x):
        return x if isinstance(x, QD) else QD(x)

    def _d(self, o):
        if self.D == 1:
            return o.D
        if o.D == 1 or o.D == self.D:
            return self.D
        raise ValueError('разные иррациональности')

    def __add__(self, o):
        o = QD.of(o)
        return QD(self.p + o.p, self.q + o.q, self._d(o))
    __radd__ = __add__

    def __neg__(self):
        return QD(-self.p, -self.q, self.D)

    def __sub__(self, o):
        return self + (-QD.of(o))

    def __rsub__(self, o):
        return QD.of(o) - self

    def __mul__(self, o):
        o = QD.of(o)
        D = self._d(o)
        return QD(self.p * o.p + self.q * o.q * D, self.p * o.q + self.q * o.p, D)
    __rmul__ = __mul__

    def sign(self):
        p, q = self.p, self.q
        if q == 0:
            return (p > 0) - (p < 0)
        if p >= 0 and q > 0:
            return 1
        if p <= 0 and q < 0:
            return -1
        # разные знаки
        return (1 if p > 0 else -1) if p * p > q * q * self.D else (1 if q > 0 else -1)

    def key(self):
        return (self.p, self.q, self.D)

    def f(self):
        return float(self.p) + float(self.q) * math.sqrt(self.D)


def qroots(a, b, c):
    """Действительные корни a·x² + b·x + c = 0 (рациональные коэффициенты) — список QD без повторов.
    a = 0 — линейное; тождество 0 = 0 → None (бесконечно много)."""
    a, b, c = F(a), F(b), F(c)
    if a == 0:
        if b == 0:
            return None if c == 0 else []
        return [QD(-c / b)]
    d = b * b - 4 * a * c
    if d < 0:
        return []
    if d == 0:
        return [QD(-b / (2 * a))]
    num_, den_ = d.numerator, d.denominator
    k, m = sqfree(num_ * den_)
    # √d = k·√m / den
    if m == 1:
        s = F(k, den_)
        return [QD((-b - s) / (2 * a)), QD((-b + s) / (2 * a))]
    q = F(k, den_) / (2 * a)
    return [QD(-b / (2 * a), -q, m), QD(-b / (2 * a), q, m)]


def uniq(pts):
    d = {}
    for p in pts:
        d[p.key() if isinstance(p, QD) else tuple(x.key() for x in p)] = p
    return list(d.values())


W19 = 20


def ask19(r, sat, w=W19, seg=10):
    """Итог для параметра: (инструкция, ответ, множество целых a) или None."""
    S = [a for a in range(-w, w + 1) if sat(a)]
    blo = -w not in S and -w + 1 not in S
    bhi = w not in S and w - 1 not in S
    opts = []
    if S and blo and bhi and len(S) <= 40:
        opts += ['count', 'sum']
    ins = [a for a in S if -seg <= a <= seg]
    if 0 < len(ins) < 2 * seg + 1 and not (blo and bhi):
        opts += ['cseg']
    if S and blo and not bhi:
        opts.append('min')
    if S and bhi and not blo:
        opts.append('max')
    if not opts:
        return None
    k = r.choice(opts)
    if k == 'count':
        return 'В ответ запишите количество целых значений a, удовлетворяющих условию.', len(S), S
    if k == 'sum':
        return 'В ответ запишите сумму всех целых значений a, удовлетворяющих условию.', sum(S), S
    if k == 'min':
        return 'В ответ запишите наименьшее целое значение a, удовлетворяющее условию.', min(S), S
    if k == 'max':
        return 'В ответ запишите наибольшее целое значение a, удовлетворяющее условию.', max(S), S
    return (f'В ответ запишите количество целых значений a из отрезка [−{seg}; {seg}], удовлетворяющих условию.',
            len(ins), ins)


def check19(ask, ans, sat_chk, w=W19):
    S = [a for a in range(-w, w + 1) if sat_chk(a)]
    if 'сумму' in ask:
        return -w not in S and w not in S and sum(S) == ans
    if 'отрезка' in ask:
        seg = int(ask.split('[−')[1].split(';')[0])
        return len([a for a in S if -seg <= a <= seg]) == ans
    if 'количество' in ask or 'сколько' in ask:
        return -w not in S and w not in S and len(S) == ans
    if 'наименьшее' in ask:
        return -w not in S and S and min(S) == ans
    if 'наибольшее' in ask:
        return w not in S and S and max(S) == ans
    raise ValueError(ask)


P19 = ['Найдите все значения a, при каждом из которых {obj} {cond}.']
CNT_EQ = {1: 'имеет единственное решение', 2: 'имеет ровно два различных корня', 3: 'имеет ровно три различных корня',
          4: 'имеет ровно четыре различных корня'}
CNT_SYS = {1: 'имеет единственное решение', 2: 'имеет ровно два различных решения', 3: 'имеет ровно три различных решения',
           4: 'имеет ровно четыре различных решения'}


def card19(r, obj, cond, sat, sat_chk, e):
    a_ = ask19(r, sat)
    if not a_:
        return None
    ask, ans, S = a_
    q = pick(r, *P19).format(obj=obj, cond=cond) + '\n' + ask
    shown = S if len(S) <= 14 else S[:6] + ['…'] + S[-3:]
    e = e + f' Целые a из ответа: {"; ".join(tnum(k) if k != "…" else k for k in shown)}.'
    return pcard(q, num(ans), e), lambda: check19(ask, ans, sat_chk)


def rad_txt(R2):
    return str(math.isqrt(R2)) if math.isqrt(R2) ** 2 == R2 else f'√{R2}'


def real_roots_of(expr, var):
    """Различные действительные корни многочлена (sympy, точно)."""
    P = sp.Poly(sp.expand(expr), var)
    if P.is_zero:
        return None
    if P.degree() <= 0:
        return []
    return sp.Poly(P.sqf_part(), var).real_roots()


def nonneg(v):
    """v ≥ 0 для точного алгебраического числа (sympy)."""
    v = sp.nsimplify(v) if not v.is_Number else v
    s = sp.sign(sp.simplify(v))
    return s != -1


@proto('ep19-sqrt-eq', 'ege-prof', 19, 'Уравнение с корнем: возведение в квадрат и отбор по знаку правой части',
       invariant='√(x⁴ − b²x² + c²a²) = x² + bx − ca ⇔ правая часть ≥ 0 и после возведения в квадрат '
                 '2x(x + b)(bx − ca) = 0; корни 0, −b, ca/b проверяются условием x² + bx − ca ≥ 0 и на совпадение.',
       varies='Числа b, c, знаки при bx и ca, требуемое число корней (1, 2, 3).',
       answer_rule='Для каждого корня — условие на a (линейное/квадратное неравенство), учёт совпадений корней; '
                   'итог — количество или сумма целых a из ответа.',
       fipi=r'уравнение √\( x 4 − \d+ x 2 \+ \d+ a 2 \) = x 2',
       mistakes=['забывают условие правая часть ≥ 0', 'не учитывают совпадение корней', 'теряют корень x = 0'],
       kim=kim(K19, 'Как в КИМ: «Найдите все значения a, при каждом из которых уравнение … имеет ровно три решения»; '
                    'итог — число по найденному множеству.', kes=['2.10', '2.2']))
def gen_ep19_sqrt_eq(r):
    b = r.choice([1, 2, 3, 4])
    c = r.choice([1, 2, 3, 4, 5])
    sb = r.choice([1, -1])
    sc_ = r.choice([1, -1])
    B, Cc = sb * b, sc_ * c
    # правая часть x² + Bx − Cc·a; подкоренное x⁴ − B²x² + Cc²a²
    k = r.choice([3, 3, 2, 1])
    rhs = f'x² {"+" if B > 0 else "−"} {"" if b == 1 else b}x {"−" if Cc > 0 else "+"} {"" if c == 1 else c}a'
    lhs = f'√(x⁴ − {b * b if b > 1 else ""}x² + {c * c if c > 1 else ""}a²)'.replace('− x²', '− x²')
    obj = f'уравнение {fm(lhs + " = " + rhs)}'
    cond = {3: 'имеет ровно три различных решения', 2: 'имеет ровно два различных решения',
            1: 'имеет единственное решение'}[k]

    def cnt(a):
        roots = {F(0), F(-B), F(Cc * a, B)}
        ok = [x for x in roots if x * x + B * x - Cc * a >= 0]
        return len(ok)

    def cnt_chk(a):
        e_ = parse_f(lhs + ' = ' + rhs, {'x': X, 'a': sp.Integer(a)})
        L, Rr = e_[1], e_[2]
        rr = real_roots_of(L.args[0] - Rr ** 2 if isinstance(L, sp.Pow) else (L ** 2 - Rr ** 2), X)
        return len([x for x in rr if (Rr.subs(X, x)) >= 0])
    e = (f'Возводим в квадрат при условии {rhs} ≥ 0: 2x(x {"+" if B > 0 else "−"} {b})({b}x {"−" if Cc > 0 else "+"} {c}a) = 0; '
         f'корни 0, {tnum(-B)}, {ca_txt(F(Cc, B))} проверяем условием и на совпадение.').replace('(1x', '(x')
    return card19(r, obj, cond, lambda a: cnt(a) == k, lambda a: cnt_chk(a) == k, e)


def lin_ax(k, c, var='a'):
    """k·a + c текстом (k, c — числа)."""
    return join_terms([(QS(k), var), (QS(c), '')])


def sys_txt(*eqs):
    return fm('{' + '; '.join(eqs) + '}')


def sympy_points(eqs, a, filt=None):
    """Точки (x, y) системы полиномиальных уравнений при данном a (sympy.solve), только действительные.
    None — бесконечно много решений."""
    sol = sp.solve([e.subs(A_, a) for e in eqs], [X, Y_], dict=True)
    pts = set()
    for s_ in sol:
        if X not in s_ or Y_ not in s_:
            return None
        xv, yv = sp.nsimplify(s_[X]), sp.nsimplify(s_[Y_])
        if not (xv.is_real and yv.is_real):
            if abs(sp.im(sp.N(xv, 40))) > 1e-30 or abs(sp.im(sp.N(yv, 40))) > 1e-30:
                continue
            xv, yv = sp.re(xv), sp.re(yv)
        if filt and not filt(xv, yv):
            continue
        pts.add((sp.N(xv, 30), sp.N(yv, 30)))
    # склеиваем численно совпадающие
    out = []
    for p in pts:
        if all(abs(p[0] - q[0]) > 1e-20 or abs(p[1] - q[1]) > 1e-20 for q in out):
            out.append(p)
    return out


def ge0(v):
    return bool(sp.N(v, 40) > -1e-30)


def ca_txt(c, var='a'):
    """c·a текстом: «a», «−a», «5a», «2a/3», «−2a/3»."""
    c = F(c)
    s = '−' if c < 0 else ''
    p, q = abs(c.numerator), c.denominator
    return s + ('' if p == 1 else str(p)) + var + (f'/{q}' if q != 1 else '')


def pair_points(eqs, a):
    """Точки системы, где одно уравнение распадается на линейные множители (sympy: factor + real_roots)."""
    ex = [e.subs(A_, a) for e in eqs]
    lin_i = None
    for i, e in enumerate(ex):
        fl = sp.factor_list(sp.expand(e), X, Y_)[1]
        if all(sp.Poly(f_, X, Y_).total_degree() == 1 for f_, _ in fl):
            lin_i = i
            break
    if lin_i is None:
        raise ValueError('нет линейного разложения')
    other = ex[1 - lin_i]
    pts = []
    for f_, _ in sp.factor_list(sp.expand(ex[lin_i]), X, Y_)[1]:
        if f_.has(Y_):
            ysol = sp.solve(f_, Y_)[0]
            rr = real_roots_of(other.subs(Y_, ysol), X)
            if rr is None:
                return None
            pts += [(sp.N(x, 30), sp.N(ysol.subs(X, x), 30)) for x in rr]
        else:
            xsol = sp.solve(f_, X)[0]
            rr = real_roots_of(other.subs(X, xsol), Y_)
            if rr is None:
                return None
            pts += [(sp.N(xsol, 30), sp.N(y, 30)) for y in rr]
    out = []
    for p_ in pts:
        if all(abs(p_[0] - q[0]) > 1e-20 or abs(p_[1] - q[1]) > 1e-20 for q in out):
            out.append(p_)
    return out


@proto('ep19-sqrt-system', 'ege-prof', 19, 'Система: произведение с корнем равно нулю и прямая с параметром',
       invariant='(F(x, y))·√(L(x, y)) = 0 ⇔ L = 0 или (F = 0 и L ≥ 0); вторая строка — прямая, зависящая от a. '
                 'Число решений — число точек пересечения прямой с частью кривой F = 0 в полуплоскости L ≥ 0 и с '
                 'прямой L = 0 (с учётом совпадений).',
       varies='Кривая F (парабола, окружность, гипербола), полуплоскость L, семейство прямых (сдвиг или пучок), '
              'требуемое число решений.',
       answer_rule='Граничные положения: касание, прохождение через точки пересечения F = 0 и L = 0, параллельность; '
                   'итог — количество/сумма целых a из ответа.',
       fipi=r'система уравнений \{ \( [^{]*\) ⋅? ?√\( [^)]*\) = 0',
       mistakes=['забывают решения при L = 0', 'не отбрасывают точки кривой с L < 0', 'не учитывают совпадение точек'],
       kim=kim(K19, 'Как в КИМ: «Найдите все значения a, при каждом из которых система … имеет ровно два различных '
                    'решения»; итог — число по множеству a.', kes=['2.10', '2.9']))
def gen_ep19_sqrt_system(r):
    kind = r.choice(['P', 'C', 'H'])
    if kind == 'P':
        p, q = r.randint(-6, 6), r.randint(-6, 6)
        Ftxt = join_terms([(QS(1), 'x²'), (QS(p), 'x'), (QS(-1), 'y'), (QS(q), '')])
        quad = lambda A1, A0: (1, p - A1, q - A0)          # x² + (p − A1)x + (q − A0)
    elif kind == 'C':
        d, e_ = r.choice([-4, -2, 2, 4, 6, -6]), r.choice([0, 0, 2, -2, 4])
        Ftxt = join_terms([(QS(1), 'x²'), (QS(1), 'y²'), (QS(d), 'x'), (QS(e_), 'y')])
        quad = lambda A1, A0: (1 + A1 * A1, 2 * A1 * A0 + d + e_ * A1, A0 * A0 + e_ * A0)
    else:
        u, v = r.randint(-4, 4), r.choice([-12, -8, -6, 6, 8, 12, 4, -4])
        Ftxt = join_terms([(QS(1), 'xy'), (QS(u), 'x'), (QS(v), '')])
        quad = lambda A1, A0: (A1, A0 + u, v)
    al, be, ga = r.choice([(1, -1, r.randint(-5, 6)), (2, 1, r.randint(-6, 8)), (-1, -1, r.randint(-2, 6)),
                           (1, 1, r.randint(-4, 6)), (0, 1, r.randint(-4, 4))])
    Ltxt = join_terms([(QS(al), 'x'), (QS(be), 'y'), (QS(ga), '')])
    lk = r.choice(['shift', 'shift', 'pencil'])
    if lk == 'shift':
        k0 = r.choice([1, 2, 3, -1, -2, -3])
        line = f'y = {join_terms([(QS(k0), "x"), (QS(1), "a")])}'
        A = lambda a: (F(k0), F(a))
    else:
        c0 = r.randint(-12, 6)
        x0 = r.choice([0, 0, 2, -2, 1])
        line = f'y = a{"x" if x0 == 0 else "(" + xm(x0) + ")"}{signed(c0) if c0 else ""}'
        A = lambda a: (F(a), F(-a * x0 + c0))
    k = r.choice([2, 2, 2, 3, 1])

    def cnt(a):
        A1, A0 = A(a)
        xs = []
        qa, qb, qc = quad(A1, A0)
        rts = qroots(qa, qb, qc)
        if rts is None:
            return -1
        for x in rts:
            y = A1 * x + A0
            if (al * x + be * y + ga).sign() >= 0:
                xs.append(x)
        # L = 0 на прямой: (al + be·A1)x + be·A0 + ga = 0
        c1, c0_ = al + be * A1, be * A0 + ga
        if c1 == 0:
            if c0_ == 0:
                return -1
        else:
            xs.append(QD(-c0_ / c1))
        return len(uniq(xs))
    eqs = [f'({Ftxt})·√({Ltxt}) = 0', line]

    def cnt_chk(a):
        (op1, l1, r1_), _ = parse_fd(eqs[0])
        (op2, l2, r2_), _ = parse_fd(eqs[1])
        Fx = sp.expand(l1 / sp.sqrt(parse_f(Ltxt)))
        Lx = parse_f(Ltxt)
        line_e = l2 - r2_
        p1 = sympy_points([Fx, line_e], a, lambda x, y: ge0(Lx.subs({X: x, Y_: y})))
        p2 = sympy_points([Lx, line_e], a)
        if p1 is None or p2 is None:
            return -1
        pts = p1[:]
        for p in p2:
            if all(abs(p[0] - q[0]) > 1e-20 or abs(p[1] - q[1]) > 1e-20 for q in pts):
                pts.append(p)
        return len(pts)
    obj = f'система уравнений {sys_txt(*eqs)}'
    e = (f'Первое уравнение: {Ltxt} = 0 или ({Ftxt} = 0 и {Ltxt} ≥ 0). Считаем точки пересечения прямой '
         f'{line} с этим множеством при каждом a.')
    return card19(r, obj, CNT_SYS[k], lambda a: cnt(a) == k, lambda a: cnt_chk(a) == k, e)


@proto('ep19-circle-lines', 'ege-prof', 19, 'Окружность и пара прямых: ровно четыре (два, три) решения',
       invariant='Одно уравнение задаёт пару прямых (y² = x² или произведение двух линейных множителей), другое — '
                 'окружность; число решений — число общих точек с учётом точки пересечения прямых.',
       varies='Движется окружность (центр зависит от a) или прямые; радиус, коэффициенты, требуемое число решений.',
       answer_rule='Расстояние от центра до каждой прямой сравниваем с радиусом; отдельно — случаи прохождения '
                   'через точку пересечения прямых и совпадения прямых.',
       fipi=r'y 2 = x 2|x 2 \+ y 2 = \d+ .*имеет ровно четыре|\( x \+ a y − \d+ \) \( x \+ a y|x y \+ 1 = x \+ y|x 2 \+ y = x y \+ x',
       mistakes=['забывают про общую точку двух прямых', 'путают касание и пересечение', 'не рассматривают совпадение прямых'],
       kim=kim(K19, 'Как в КИМ: система «окружность + пара прямых», «имеет ровно четыре различных решения».',
               kes=['2.10', '7.5']))
def gen_ep19_circle_lines(r):
    k = r.choice([4, 4, 2, 3])
    if r.random() < 0.55:
        # окружность (x − (αa + β))² + (y − (γa + δ))² = R², прямые y = ±x
        al, be = r.choice([(1, 0), (2, 1), (1, 1), (2, 0), (1, -1)])
        ga, de = r.choice([(1, 0), (0, 1), (1, 1), (0, 2), (1, -2), (0, 0)])
        R2 = r.choice([2, 4, 8, 9, 18, 25, 1, 5])
        u = lambda a: al * a + be
        v = lambda a: ga * a + de
        # развёрнутая запись по a: x² + y² − 2u x − 2v y + u² + v² − R² = 0
        # u² + v² − R² = (α² + γ²)a² + 2(αβ + γδ)a + β² + δ² − R²
        c2, c1, c0 = al * al + ga * ga, 2 * (al * be + ga * de), be * be + de * de - R2
        def lin_term(k_, c_, v):
            # −2(k_·a + c_)·v
            if k_ == 0 and c_ == 0:
                return ''
            if c_ == 0:
                return cterm(QS(-2 * k_), f'a{v}')
            if k_ == 0:
                return cterm(QS(-2 * c_), v)
            g = math.gcd(k_, c_)
            if k_ < 0:
                g = -g
            return cterm(QS(-2 * g), f'({lin_ax(k_ // g, c_ // g)}){v}')
        circ = 'x² + y²' + lin_term(al, be, 'x') + lin_term(ga, de, 'y') + \
            (' + ' + join_terms([(QS(c2), 'a²'), (QS(c1), 'a'), (QS(c0), '')]) if (c2 or c1 or c0) else '') + ' = 0'
        circ = circ.replace('+ −', '− ')
        pair = pick(r, 'y² = x²', '|y| = |x|', 'x² − y² = 0')
        eqs = [circ, pair]

        def cnt(a):
            U, V = F(u(a)), F(v(a))
            pts = []
            for s_ in (1, -1):
                # (x − U)² + (s x − V)² = R²
                for x in qroots(2, -2 * U - 2 * s_ * V, U * U + V * V - R2):
                    pts.append((x, x * s_))
            return len(uniq(pts))
        e = f'Пара прямых y = x и y = −x; окружность с центром ({lin_ax(al, be)}; {lin_ax(ga, de)}) и радиусом {rad_txt(R2)}.'
    else:
        # окружность x² + y² = R², прямые (a·x + y − p)(a·x + y − q·a) = 0 или (x + a·y − p)(x + a·y − q)
        R2 = r.choice([4, 9, 16, 25, 8, 10, 5])
        p = r.choice([2, 3, 4, 5, 6, -3, -4])
        qk = r.choice([1, 2, -1, 3])
        pair = f'(ax + y {"−" if p > 0 else "+"} {abs(p)})(ax + y {"−" if qk > 0 else "+"} {"" if abs(qk) == 1 else abs(qk)}a) = 0'
        circ = f'x² + y² = {R2}'
        eqs = [pair, circ]

        def cnt(a):
            pts = []
            for c in (F(p), F(qk * a)):
                # y = c − a x:  x² + (c − a x)² = R²
                for x in qroots(1 + a * a, -2 * a * c, c * c - R2):
                    pts.append((x, c - a * x))
            return len(uniq(pts))
        e = f'Две параллельные прямые y = {tnum(p)} − ax и y = {"" if abs(qk) == 1 else abs(qk)}a − ax (совпадают, если a = {fr(F(p, qk))}); окружность радиуса {rad_txt(R2)}.'.replace('y = −a', 'y = −a')

    def cnt_chk(a):
        ex = []
        for t in eqs:
            op, l, rr = parse_f(t)
            ex.append(l - rr)
        ex = [Y_ ** 2 - X ** 2 if z.has(sp.Abs) else z for z in ex]
        pts = pair_points(ex, a)
        return -1 if pts is None else len(pts)
    obj = f'система уравнений {sys_txt(*eqs)}'
    return card19(r, obj, CNT_SYS[k], lambda a: cnt(a) == k, lambda a: cnt_chk(a) == k, e)


@proto('ep19-abs-quad', 'ege-prof', 19, 'Модуль квадратного выражения с параметром: число корней',
       invariant='|G(x, a)| = H(x, a) (или G = |H|) раскладывается на два квадратных уравнения с условием знака; '
                 'в плоскости (x; a) это части окружностей/парабол и прямые.',
       varies='Коэффициенты G и H, форма (модуль слева или справа), требуемое число корней.',
       answer_rule='Для каждого a — корни двух квадратных уравнений, удовлетворяющие условию знака, без повторов.',
       fipi=r'уравнение \|? ?x 2 \+ a 2 [−+] \d* ?x [−+] \d* ?a \|? = \|? ?\d* ?x|a 2 [+−] a x − 2 x 2 .*\| x \||x 2 \+ a 2 [+−] x [+−] \d+ a = \|',
       mistakes=['забывают условие H ≥ 0', 'считают совпавшие корни дважды', 'теряют случай касания'],
       kim=kim(K19, 'Как в КИМ: «|x² + a² − 6x + 4a| = 2x − 2a имеет четыре различных корня».', kes=['2.10']))
def gen_ep19_abs_quad(r):
    p, q = r.choice([-6, -4, -2, 2, 4, 6, -1, 1, -3, 3]), r.choice([-7, -6, -4, -2, 2, 4, 6, 7, -3, 3])
    rx, sa = r.choice([1, 2, 3, 7, -2, -7]), r.choice([1, 2, -1, -2, -3, 3])
    form = r.choice(['absG', 'absH'])
    if form == 'absH' and rx < 0:
        rx, sa = -rx, -sa               # |−7x + 2a| пишем как |7x − 2a|
    G = f'x² + a² {signed(p)[1:]}x {signed(q)[1:]}a'.replace('  ', ' ')
    G = join_terms([(QS(1), 'x²'), (QS(1), 'a²'), (QS(p), 'x'), (QS(q), 'a')])
    H = join_terms([(QS(rx), 'x'), (QS(sa), 'a')])
    k = r.choice([2, 2, 4, 3, 1])
    cond = {1: 'имеет единственный корень', 2: 'имеет ровно два различных корня', 3: 'имеет ровно три различных корня',
            4: 'имеет четыре различных корня'}[k]
    if form == 'absG':
        eq = f'|{G}| = {H}'
    else:
        eq = f'{G} = |{H}|'

    def cnt(a):
        xs = []
        for s_ in (1, -1):
            # G = s·H  ⇔ x² + (p − s·rx)x + a² + qa − s·sa·a = 0
            for x in qroots(1, p - s_ * rx, a * a + q * a - s_ * sa * a):
                Hv = x * rx + sa * a
                if form == 'absG':
                    ok = Hv.sign() >= 0
                else:
                    ok = (Hv.sign() >= 0) if s_ == 1 else (Hv.sign() <= 0)
                if ok:
                    xs.append(x)
        return len(uniq(xs))

    def cnt_chk(a):
        (op, l, rr) = parse_f(eq, {'x': X, 'a': sp.Integer(a)})
        Gs = l.args[0] if isinstance(l, sp.Abs) else l
        Hs = rr.args[0] if isinstance(rr, sp.Abs) else rr
        roots = real_roots_of(Gs ** 2 - Hs ** 2, X)
        cnt_ = 0
        for x in roots:
            if form == 'absG':
                cnt_ += ge0(Hs.subs(X, x))
            else:
                cnt_ += ge0(Gs.subs(X, x))
        return cnt_
    obj = f'уравнение {fm(eq)}'
    e = (f'Раскрываем модуль: {G} = ±({H})' + (f' при {H} ≥ 0' if form == 'absG' else f' при {G} ≥ 0')
         + '; при каждом a считаем различные корни двух квадратных уравнений с этим условием.')
    return card19(r, obj, cond, lambda a: cnt(a) == k, lambda a: cnt_chk(a) == k, e)


@proto('ep19-exp-abs', 'ege-prof', 19, 'Показательное уравнение с параметром и модулем: разложение на множители',
       invariant='После группировки (t − (a + c₁))(t − (k|a| + c₂)) = 0, t = b^x > 0; единственное решение — '
                 'когда ровно одно значение t положительно или значения совпадают.',
       varies='Основание, линейное выражение от a, коэффициенты при |a|, требуемое число решений.',
       answer_rule='Условия на a: знак (a + c₁), совпадение a + c₁ = k|a| + c₂; итог — число/сумма целых a.',
       fipi=r'уравнение \d+ x [−+] \( a [+−] \d+ \) \d+ x = \( \d+ \+ \d+ \| a \| \)',
       mistakes=['забывают, что t > 0', 'не учитывают совпадение корней', 'ошибка при раскрытии модуля'],
       kim=kim(K19, 'Как в КИМ: «25^x − (a + 6)·5^x = (5 + 3|a|)·5^x − (a + 6)(3|a| + 5) имеет единственное решение».',
               kes=['2.10', '2.4']))
def gen_ep19_exp_abs(r):
    B = r.choice([2, 3, 5, 7])
    m, c1 = r.choice([1, 1, 2]), r.choice([c for c in range(-8, 9) if c])
    kk, c2 = r.choice([2, 3, 4]), r.randint(1, 7)
    k = r.choice([1, 1, 2])
    t1 = lin_ax(m, c1)
    t2 = f'{c2} + {kk}|a|'
    eq = pick(r, f'{B * B}^{{x}} + ({t1})({t2}) = ({t1})·{B}^{{x}} + ({t2})·{B}^{{x}}',
              f'{B * B}^{{x}} − ({t2})·{B}^{{x}} = ({t1})·{B}^{{x}} − ({t2})({t1})')
    cond = 'имеет единственное решение' if k == 1 else 'имеет ровно два различных решения'

    def cnt(a):
        v1, v2 = m * a + c1, kk * abs(a) + c2
        return len({v for v in (v1, v2) if v > 0})

    def cnt_chk(a):
        f, conds = eq_expr(eq.replace('|a|', '·|a|'))     # разборщик не знает неявного умножения перед |…|
        f = f.subs(A_, a)
        return len(num_roots(f, -2, 8, n=1500))
    obj = f'уравнение {fm(eq)}'
    e = (f'Переносим всё влево и группируем: ({B}^{{x}} − ({t1}))({B}^{{x}} − ({t2})) = 0; {t2} > 0 всегда, '
         f'второй корень даёт решение при {t1} > 0 и не совпадает с первым.')
    return card19(r, obj, cond, lambda a: cnt(a) == k, lambda a: cnt_chk(a) == k, e)


@proto('ep19-log-segment', 'ege-prof', 19, 'Уравнение f(x)·ln g = f(x)·ln h: ровно один корень на отрезке',
       invariant='Произведение: f(x) = 0 (при положительных g и h) или g = h (при g > 0 и допустимом f); '
                 'требуется ровно один корень на отрезке — условия на a линейны.',
       varies='Множитель f (линейный или корень), линейные аргументы логарифмов с параметром, отрезок.',
       answer_rule='Корень множителя входит при g(x₀) > 0, h(x₀) > 0; корень g = h — если лежит на отрезке и в ОДЗ; '
                   'учёт совпадения; итог — число/сумма целых a.',
       fipi=r'ln \( [^)]*\) (= \(|⋅ √)|⋅ ln \(|√\( x 2 − a 2 \) = √|√\( \d x − \d \) ⋅ ln',
       mistakes=['не проверяют положительность аргументов в корне множителя', 'забывают про совпадение корней',
                 'не учитывают ОДЗ корня'],
       kim=kim(K19, 'Как в КИМ: «(5x − 2)·ln(x + a) = (5x − 2)·ln(2x − a) имеет ровно один корень на отрезке [0; 1]».',
               kes=['2.10', '2.4']))
def gen_ep19_log_segment(r):
    L = r.choice([1, 2, 3, 4])
    m, n = r.choice([(2, 1), (5, 2), (3, 1), (4, 1), (1, 1), (3, 2), (2, 3), (4, 3)])
    x0 = F(n, m)
    if not 0 < x0 < L:
        return None
    sq = r.random() < 0.45
    p1, p2 = r.sample([1, 2, 3, 4, 5, 6, 7, 8, 10], 2)
    q1, q2 = r.choice([(1, -1), (-1, 1), (2, -1), (-1, 2), (-2, 1), (1, 2), (2, 1)])
    r1, r2 = r.randint(-3, 3), r.randint(-3, 3)
    ft = f'√({xm(F(n), f"{m}x" if m > 1 else "x")})' if sq else f'({xm(F(n), f"{m}x" if m > 1 else "x")})'
    g1 = join_terms([(QS(p1), 'x'), (QS(q1), 'a'), (QS(r1), '')])
    g2 = join_terms([(QS(p2), 'x'), (QS(q2), 'a'), (QS(r2), '')])
    eq = pick(r, f'ln({g1})·{ft} = ln({g2})·{ft}', f'{ft}·ln({g1}) − {ft}·ln({g2}) = 0')

    def cnt(a):
        roots = set()
        if p1 * x0 + q1 * a + r1 > 0 and p2 * x0 + q2 * a + r2 > 0:
            roots.add(x0)
        xs = F((q2 - q1) * a + r2 - r1, p1 - p2)
        if 0 <= xs <= L and p1 * xs + q1 * a + r1 > 0 and (not sq or m * xs - n >= 0):
            roots.add(xs)
        return len(roots)

    def cnt_chk(a):
        f, conds = eq_expr(eq)
        f = f.subs(A_, a)
        conds = [(c.subs(A_, a), k_) for c, k_ in conds]
        return len(num_roots(f, 0, L, n=3000, conds=conds))
    obj = f'уравнение {fm(eq)}'
    cond = pick(r, f'имеет единственный корень, принадлежащий отрезку [0; {L}]', f'имеет на промежутке [0; {L}] единственный корень')
    e = (f'Корни: x = {fr(x0)} (если оба аргумента логарифмов в этой точке положительны) и корень уравнения '
         f'{g1} = {g2}, если он лежит на [0; {L}] и в области определения; совпадение учитываем один раз.')
    return card19(r, obj, cond, lambda a: cnt(a) == 1, lambda a: cnt_chk(a) == 1, e)


@proto('ep19-quad-subst', 'ege-prof', 19, 'Замена t = x + m/x: квадратное уравнение с параметром',
       invariant='Замена t = x + m/x (|t| ≥ 2√m): уравнение раскладывается (t + s)(a(t − s) + b) = 0; '
                 'каждое t с |t| > 2√m даёт два корня x, с |t| = 2√m — один.',
       varies='Число m, s, b, требуемое число корней.',
       answer_rule='t = −s всегда даёт два корня; второе значение t = s − b/a не должно давать новых корней '
                   '(|t| < 2√m) или должно совпасть с первым; итог — число/сумма целых a.',
       fipi=r'уравнение a \( x \+ \d+ x \) 2 \+ \d+ \( x \+ \d+ x \)',
       mistakes=['забывают ограничение |t| ≥ 2√m', 'не рассматривают a = 0', 'не учитывают совпадение t'],
       kim=kim(K19, 'Как в КИМ: «a(x + 4/x)² + 2(x + 4/x) − 25a + 10 = 0 имеет ровно два различных корня».',
               kes=['2.10', '2.1']))
def gen_ep19_quad_subst(r):
    m = r.choice([1, 4, 9, 16])
    rt = 2 * math.isqrt(m)
    s = r.choice([v for v in range(rt + 1, rt + 5)])
    b = r.choice([1, 2, 3, 4, 5, 6, -2, -3])
    tt = f'x + {m}/x' if m != 1 else 'x + 1/x'
    # a(t² − s²) + b(t + s) = 0 → a·t² + b·t − s²a + bs = 0
    eq = f'a({tt})² + {b}({tt}) − {s * s}a + {b * s} = 0' if b > 0 else f'a({tt})² − {-b}({tt}) − {s * s}a − {-b * s} = 0'
    eq = eq.replace('1(', '(')
    k = 2

    def cnt(a):
        ts = {F(-s)}
        if a != 0:
            ts.add(F(s) - F(b, a))
        n_ = 0
        for t in ts:
            d = t * t - 4 * m
            n_ += 2 if d > 0 else 1 if d == 0 else 0
        return n_

    def cnt_chk(a):
        f, _ = eq_expr(eq)
        num_ = sp.numer(sp.together(f.subs(A_, a)))
        roots = real_roots_of(num_, X)
        return -1 if roots is None else len([x for x in roots if x != 0])
    obj = f'уравнение {fm(eq)}'
    e = (f't = {tt}, |t| ≥ {rt}: (t + {s})(a(t − {s}) {"+" if b > 0 else "−"} {abs(b)}) = 0. t = −{s} даёт два корня; '
         f't = {s} {"−" if b > 0 else "+"} {abs(b)}/a не должно давать новых корней (или должно совпасть с −{s}).')
    return card19(r, obj, CNT_EQ[k], lambda a: cnt(a) == k, lambda a: cnt_chk(a) == k, e)


def ivl_nonempty(lows, highs):
    """Пересечение промежутков: lows/highs — списки (QD, закрыт?); True, если непусто."""
    lo = max(lows, key=lambda t: (t[0].f(), not t[1]))
    hi = min(highs, key=lambda t: (t[0].f(), t[1]))
    # точное сравнение
    d = (hi[0] - lo[0]).sign()
    if d > 0:
        return True
    if d == 0:
        return lo[1] and hi[1]
    return False


@proto('ep19-ineq-segment', 'ege-prof', 19, 'Система неравенств с параметром: есть решение на отрезке',
       invariant='Каждое неравенство при фиксированном a задаёт промежуток по x (линейное — луч, квадратичное вида '
                 'x² − px + a² < q — интервал между корнями); нужно, чтобы пересечение с отрезком было непусто. '
                 'Удобно в плоскости (x; a): полосы, прямые и круг.',
       varies='Линейные ограничения, квадратичное неравенство (круг в плоскости (x; a)), отрезок.',
       answer_rule='Для каждого a — сравнение концов промежутков; итог — число/сумма целых a.',
       fipi=r'система неравенств .*имеет хотя бы одно решение на отрезке',
       mistakes=['путают строгие и нестрогие неравенства на концах', 'забывают про ограничение отрезком',
                 'неверно находят проекцию круга'],
       kim=kim(K19, 'Как в КИМ: «система неравенств {…} имеет хотя бы одно решение на отрезке [4; 5]».', kes=['2.10', '2.9']))
def gen_ep19_ineq_segment(r):
    u = r.randint(-2, 5)
    v = u + r.choice([1, 1, 2])
    p, q = r.choice([4, 6, 8, 2, 10]), r.choice([0, 0, 1, 4, 5, 9])
    # x² − p x + a² < q   ⇔  (x − p/2)² + a² < q + p²/4
    k1, c1 = r.choice([2, 1, 3, -1, -2]), r.randint(-4, 6)
    s1 = r.choice(['≤', '≥'])
    k3, c3 = r.choice([1, 2, -1]), r.randint(2, 12)
    quad = f'{p}x > x² + a²{" − " + str(q) if q else ""}'
    lin1 = f'{ca_txt(k1)}{signed(c1) if c1 else ""} {s1} x'
    lin3 = f'x {"+" if k3 > 0 else "−"} {ca_txt(abs(k3))} ≤ {c3}'
    ineqs = [lin1, quad, lin3]
    r.shuffle(ineqs)

    def ok(a):
        lows = [(QD(u), True)]
        highs = [(QD(v), True)]
        b1 = F(k1 * a + c1)
        (lows if s1 == '≤' else highs).append((QD(b1), True))
        # x + k3·a ≤ c3 → x ≤ c3 − k3 a
        highs.append((QD(c3 - k3 * a), True))
        rts = qroots(1, -p, a * a - q)
        if not rts or len(rts) < 2:
            return False
        lows.append((rts[0], False))
        highs.append((rts[1], False))
        return ivl_nonempty(lows, highs)

    def ok_chk(a):
        xs = sp.Interval(u, v)
        for t in ineqs:
            op, l, rr = parse_f(t, {'x': X, 'a': sp.Integer(a)})
            rel = {'≤': sp.Le, '≥': sp.Ge, '<': sp.Lt, '>': sp.Gt}[op](l, rr)
            xs = xs.intersect(sp.solveset(rel, X, sp.S.Reals))
        return xs is not sp.S.EmptySet and not xs.is_empty
    obj = f'система неравенств {sys_txt(*ineqs)}'
    cond = f'имеет хотя бы одно решение на отрезке [{u}; {v}]'.replace('[-', '[−').replace('; -', '; −')
    e = (f'Неравенство {quad} — внутренность круга (x − {fr(F(p, 2))})² + a² < {fr(q + F(p * p, 4))} в плоскости (x; a); '
         f'остальные — полуплоскости. Для каждого a пересекаем промежутки по x с отрезком [{tnum(u)}; {tnum(v)}].')
    return card19(r, obj, cond, ok, ok_chk, e)


@proto('ep19-frac-roots', 'ege-prof', 19, 'Дробно-рациональное уравнение с параметром: совпадение корней и выколотые точки',
       invariant='Корни числителя (линейные по a) проверяются на совпадение между собой и с нулями знаменателя; '
                 'число корней меняется лишь при конечном наборе значений a.',
       varies='Коэффициенты числителя (k²x² − a² или (x − a)(x − c)) и знаменателя, требуемое число корней.',
       answer_rule='Находим все a, где корень числителя совпал с другим корнем или обнулил знаменатель; '
                   'итог — сумма (или количество) таких a.',
       fipi=r'уравнение \d* ?x 2 − a 2 x 2 \+ \d+ x \+ \d+ − a 2 = 0|уравнение .* x 2 − a 2 .*= 0 имеет ровно два',
       mistakes=['забывают совпадение корней числителя', 'не исключают нули знаменателя', 'теряют a = 0'],
       kim=kim(K19, 'Как в КИМ: «(9x² − a²)/(x² + 8x + 16 − a²) = 0 имеет ровно два различных корня».', kes=['2.10', '2.1']))
def gen_ep19_frac_roots(r):
    k = r.choice([1, 2, 3, 4, 5])
    pp = r.choice([1, 2, 3, 4, 5, -2, -3, -1])
    sym = r.random() < 0.35
    c0 = r.choice([v for v in range(-6, 7) if v != 0])
    if sym:
        # числитель k²x² − a² = (kx − a)(kx + a)
        if k == 1:
            return None
        numt = f'{k * k}x² − a²'
        nroots = lambda a: {a / k, -a / k}
    else:
        # числитель (kx − a)(x − c0) = kx² − (k·c0 + a)x + c0·a
        numt = (join_terms([(QS(k), 'x²')]) + f' − ({join_terms([(QS(1), "a"), (QS(k * c0), "")])})x'
                + ' ' + cterm(QS(c0), 'a').strip())
        numt = numt.replace('+ −', '− ')
        nroots = lambda a: {a / k, F(c0)}
    dent = join_terms([(QS(1), 'x²'), (QS(2 * pp), 'x'), (QS(pp * pp), '')]) + ' − a²'
    eq = f'({numt})/({dent}) = 0'
    want = r.choice([1, 1, 0]) if sym else r.choice([1, 1, 1, 0])
    # кандидаты: совпадение корней числителя и попадание их в нули знаменателя x = −pp ± a
    cands = {F(0)} if sym else {F(k * c0)}
    for s2 in (1, -1):
        for s1 in ((1, -1) if sym else (1,)):
            cf = F(s1, k) - s2
            if cf != 0:
                cands.add(F(-pp) / cf)
        if not sym:
            cands.add(F(c0 + pp) * s2)

    def cnt(a):
        a = F(a)
        return len([x for x in nroots(a) if (x + pp) ** 2 - a * a != 0])
    good = sorted(a for a in cands if cnt(a) == want)
    if not good or cnt(F(1, 7)) == want:
        return None
    if r.random() < 0.5:
        ans = sum(good)
        ask = 'В ответ запишите сумму всех найденных значений a.'
    else:
        ans = F(len(good))
        ask = 'В ответ запишите количество найденных значений a.'
    if not nice(ans, 2):
        return None
    cond = 'имеет ровно один корень' if want == 1 else 'не имеет корней'
    q = pick(r, *P19).format(obj=f'уравнение {fm(eq)}', cond=cond) + '\n' + ask
    e = ((f'Корни числителя x = ±a/{k} (различны при a ≠ 0)' if sym else f'Корни числителя x = {ca_txt(F(1, k), "a")} и x = {c0}')
         + f', нули знаменателя x = {tnum(-pp)} ± a. '
         + 'Число корней меняется при a = ' + '; '.join(fr(c) for c in sorted(cands)) + '. Подходят: '
         + '; '.join(fr(c) for c in good) + '.')

    def chk():
        f, _ = eq_expr(eq)
        nm, dn = sp.fraction(sp.together(f))
        rts = sp.solve(nm, X)                      # корни числителя как функции a
        cand2 = set()
        for i, r1 in enumerate(rts):
            for r2 in rts[i + 1:]:
                cand2 |= set(sp.solve(sp.Eq(r1, r2), A_))
            cand2 |= set(sp.solve(dn.subs(X, r1), A_))
        found = []
        for c in cand2:
            xs = {sp.simplify(rt.subs(A_, c)) for rt in rts}
            n_ = len([x for x in xs if sp.simplify(dn.subs({X: x, A_: c})) != 0])
            if n_ == want:
                found.append(c)
        # в общем положении корней не want
        gen_ok = all(len({rt.subs(A_, t) for rt in rts if dn.subs({X: rt.subs(A_, t), A_: t}) != 0}) != want
                     for t in (sp.Rational(1, 7), sp.Rational(-13, 11), sp.Rational(29, 3)))
        val = sum(found) if 'сумм' in ask else len(found)
        return gen_ok and same(num(ans), val)
    return pcard(q, num(ans), e), chk


@proto('ep19-line-abs', 'ege-prof', 19, 'Прямая и график с модулем: число решений системы',
       invariant='Второе уравнение задаёт график с модулем (|y| = |g(x)| или c|y| = g(x)): объединение двух парабол '
                 '(частей парабол); прямая из первого уравнения сдвигается параметром; считаем общие точки.',
       varies='Квадратичная функция g, вид модуля, наклон прямой, требуемое число решений.',
       answer_rule='Граничные положения: касание, прохождение через точки излома/пересечения парабол; '
                   'итог — число/сумма целых a.',
       fipi=r'\| y \| = \| x 2|\d+ \| y \| [−+] x 2|y = \| x − a \| − \d+|x \| y \| \+ x|\( x \+ 1 \) ⋅ \| x \+ 1 \|',
       mistakes=['теряют часть графика', 'не проверяют касание', 'путают |y| = g и y = |g|'],
       kim=kim(K19, 'Как в КИМ: «{x + y = a; |y| = |x² − 2x|} имеет ровно два различных решения».', kes=['2.10', '3.1']))
def gen_ep19_line_abs(r):
    p = r.choice([2, 4, 6, -2, -4, 3])
    kslope = r.choice([1, -1, 2, -2, 3, 4, -3])
    form = r.choice(['absabs', 'cabs'])
    c = r.choice([1, 2])
    g = join_terms([(QS(1), 'x²'), (QS(-p), 'x')])            # x² − p x
    if form == 'absabs':
        curve = f'|y| = |{g}|'
    else:
        g = join_terms([(QS(-1), 'x²'), (QS(p), 'x')])        # −x² + p x ≥ 0
        curve = f'{c}|y| = {g}' if c > 1 else f'|y| = {g}'
    line = pick(r, f'y = {join_terms([(QS(kslope), "x"), (QS(1), "a")])}',
                f'{join_terms([(QS(kslope), "x"), (QS(-1), "y"), (QS(1), "a")])} = 0')
    k = r.choice([2, 2, 3, 4, 1])

    def cnt(a):
        xs = []
        if form == 'absabs':
            for s_ in (1, -1):
                # kx + a = s(x² − p x)  ⇔  s x² − (s p + k)x − a = 0
                rts = qroots(s_, -(s_ * p + kslope), -a)
                xs += rts
        else:
            for s_ in (1, -1):
                # c·s·(kx + a) = −x² + p x, при −x² + p x ≥ 0
                rts = qroots(1, c * s_ * kslope - p, c * s_ * a)
                xs += [x for x in rts if (-(x * x) + p * x).sign() >= 0]
        return len(uniq(xs))

    def cnt_chk(a):
        (_, l1, r1_), (_, l2, r2_) = parse_f(curve.replace('2|y|', '2·|y|')), parse_f(line)
        le = sp.solve(l2 - r2_, Y_)[0].subs(A_, a)
        e_ = (l1 - r1_).subs(Y_, le)
        # убираем модули: рассматриваем все комбинации знаков и отбираем точки, где исходное равенство верно
        absx = sorted(e_.atoms(sp.Abs), key=str)
        pts = set()
        for signs in itertools.product((1, -1), repeat=len(absx)):
            ee = e_
            for ab, sg in zip(absx, signs):
                ee = ee.subs(ab, sg * ab.args[0])
            rr = real_roots_of(ee, X)
            if rr is None:
                return -1
            for x in rr:
                if abs(sp.N(e_.subs(X, x), 40)) < 1e-30:
                    pts.add(sp.N(x, 30))
        out = []
        for x in pts:
            if all(abs(x - y) > 1e-20 for y in out):
                out.append(x)
        return len(out)
    obj = f'система уравнений {sys_txt(line, curve)}'
    e = ('График второго уравнения — ' + ('объединение парабол y = ±(' + g + ')' if form == 'absabs'
                                          else f'части парабол y = ±({g}){"/" + str(c) if c > 1 else ""} при {g} ≥ 0')
         + f'; прямая с угловым коэффициентом {tnum(kslope)} сдвигается параметром a. Считаем общие точки.')
    return card19(r, obj, CNT_SYS[k], lambda a: cnt(a) == k, lambda a: cnt_chk(a) == k, e)


@proto('ep19-uv-zero', 'ege-prof', 19, 'Уравнение (u + v)² = (u − v)²: сведение к u·v = 0 и корни на отрезке',
       invariant='(u + v)² = (u − v)² ⇔ 4uv = 0: линейный множитель u = 0 или логарифм v = 0 (аргумент равен 1) '
                 'при условии, что логарифм определён; требуется единственный корень на отрезке.',
       varies='Линейное выражение u, аргумент логарифма (x + ma + t), отрезок.',
       answer_rule='Корень u = 0 годится, если в нём аргумент логарифма положителен и он на отрезке; корень v = 0 — '
                   'если на отрезке; совпадение учитываем; итог — число/сумма целых a.',
       fipi=r'\( \d* ?x \+ ln \(|\( \d* ?x [+−] a [+−] \d [+−] tg x \) 2',
       mistakes=['раскрывают квадраты и теряют область определения логарифма', 'забывают про совпадение корней',
                 'не проверяют принадлежность отрезку'],
       kim=kim(K19, 'Как в КИМ: «(x + ln(x + a))² = (x − ln(x + a))² имеет единственное решение на отрезке [0; 1]».',
               kes=['2.10', '2.4']))
def gen_ep19_uv_zero(r):
    L = r.choice([1, 2, 3])
    p = r.choice([1, 2, 3])
    q, rr = r.choice([1, 2, -1]), r.randint(-2, 2)
    mm, t = r.choice([1, 2, -1, 3]), r.randint(-2, 2)
    u = join_terms([(QS(p), 'x'), (QS(q), 'a'), (QS(rr), '')])
    arg = join_terms([(QS(1), 'x'), (QS(mm), 'a'), (QS(t), '')])
    v = f'ln({arg})'
    eq = pick(r, f'({u} + {v})² = ({u} − {v})²', f'({v} + {u})² = ({u} − {v})²')

    def cnt(a):
        roots = set()
        x1 = F(-(q * a + rr), p)
        if 0 <= x1 <= L and x1 + mm * a + t > 0:
            roots.add(x1)
        x2 = F(1 - mm * a - t)
        if 0 <= x2 <= L:
            roots.add(x2)
        return len(roots)

    def cnt_chk(a):
        f, conds = eq_expr(eq)
        f = f.subs(A_, a)
        conds = [(c.subs(A_, a), k_) for c, k_ in conds]
        return len(num_roots(f, 0, L, n=2000, conds=conds))
    obj = f'уравнение {fm(eq)}'
    cond = f'имеет единственное решение на отрезке [0; {L}]'
    e = (f'(u + v)² − (u − v)² = 4uv: {u} = 0 или {arg} = 1, причём {arg} > 0. Корень x = {fr(F(-rr, p)) if q == 0 else "…"} '
         f'первого множителя берём при положительном аргументе логарифма; совпадения учитываем один раз.').replace(' x = … ', ' ')
    return card19(r, obj, cond, lambda a: cnt(a) == 1, lambda a: cnt_chk(a) == 1, e)


@proto('ep19-quad-in-a', 'ege-prof', 19, 'Уравнение, квадратное относительно параметра: разложение и график в плоскости (x; a)',
       invariant='Уравнение квадратное относительно a, его дискриминант — полный квадрат; раскладывается на '
                 '(a − f(x))(a − g(x)) = 0: парабола и прямая в плоскости (x; a); число корней — число точек '
                 'пересечения горизонтали с их объединением.',
       varies='Парабола a = x² + px (или −x² + px), прямая a = kx + c, требуемое число корней.',
       answer_rule='Граничные a: вершина параболы, точки пересечения параболы и прямой; итог — число/сумма целых a.',
       fipi=r'уравнение \( x (−|\+) \d \) a 2|уравнение \( x 2 − x \) a 2|уравнение a x 4|x 2 − x a 2|a x \+ 1 x|\( x \+ 1 \) a 2',
       mistakes=['не замечают разложения', 'считают дважды общую точку параболы и прямой', 'теряют вершину параболы'],
       kim=kim(K19, 'Как в КИМ: «(x² − x)a² − (x⁴ − x³ − x + 1)a − x³ + x² = 0 имеет ровно два различных корня».',
               kes=['2.10', '2.1']))
def gen_ep19_quad_in_a(r):
    sg = r.choice([1, -1])
    p = r.randint(-5, 5)
    k, c = r.choice([1, -1, 2, -2, 3]), r.randint(-6, 6)
    # (a − sg(x² + p x))(a − (kx + c)) = 0
    f1 = [sg, sg * p, 0]
    f2 = [0, k, c]
    # a² − (f1 + f2)a + f1·f2 = 0
    s_ = [f1[i] + f2[i] for i in range(3)]
    pr = [0] * 5
    for i in range(3):
        for j in range(3):
            pr[i + j] += f1[i] * f2[j]
    lead = next(v for v in s_ if v)
    mid = f'+ ({poly([-v for v in s_])})a' if lead < 0 else f'− ({poly(s_)})a'
    pt = poly(pr[1:] if pr[0] == 0 else pr)
    eq = f'a² {mid} + {pt} = 0'
    if pt.startswith('−'):
        eq = f'a² {mid} − {pt[1:]} = 0'
    k_ = r.choice([2, 2, 3, 1])

    def cnt(a):
        xs = qroots(sg, sg * p, -a) + [QD(F(a - c, k))]
        return len(uniq(xs))

    def cnt_chk(a):
        f, _ = eq_expr(eq)
        rr = real_roots_of(f.subs(A_, a), X)
        return -1 if rr is None else len(rr)
    obj = f'уравнение {fm(eq)}'
    e = (f'Дискриминант по a — полный квадрат: (a − ({poly(f1)}))(a − ({poly(f2)})) = 0. В плоскости (x; a) — '
         f'парабола и прямая; считаем точки пересечения с горизонталью a = const.')
    return card19(r, obj, CNT_EQ[k_], lambda a: cnt(a) == k_, lambda a: cnt_chk(a) == k_, e)


# ================================================================ №20: числа и их свойства

ASK20 = ['В ответ запишите ответ на вопрос пункта в.']


def q20(r, head, a, b, c):
    return f'{head}\nа) {a}\nб) {b}\nв) {c}\n' + pick(r, *ASK20)


def subset_sums(items):
    """Все суммы подмножеств мультимножества [(номинал, количество)] — битовая маска (int)."""
    m = 1
    for v, cnt in items:
        for _ in range(cnt):
            m |= m << v
    return m


COIN_CTX = [
    dict(head='В кошельке лежат монеты двух видов: {n1} достоинством {v1} {u1} и {n2} достоинством {v2} {u2}.',
         one='монета', few='монеты', many='монет',
         U=('рубль', 'рубля', 'рублей'), make='заплатить этими монетами без сдачи ровно {s} {us}', add='монет по 1 рублю',
         need='чтобы без сдачи можно было набрать любую целую сумму от 1 до {t} рублей включительно'),
    dict(head='В наборе {n1} {w1} массой по {v1} {u1} и {n2} {w2} массой по {v2} {u2}.', one='гиря', few='гири', many='гирь',
         U=('кг', 'кг', 'кг'), make='уравновесить на чашечных весах груз массой {s} {us} (гири кладут на одну чашу)',
         add='гирь массой 1 кг', need='чтобы на одну чашу весов можно было положить гири общей массой, равной '
                                      'любому целому числу килограммов от 1 до {t}'),
    dict(head='У филателиста {n1} {w1} номиналом {v1} {u1} и {n2} {w2} номиналом {v2} {u2}.', one='марка',
         few='марки', many='марок', U=('рубль', 'рубля', 'рублей'), make='наклеить на конверт марки общим номиналом ровно {s} {us}',
         add='марок номиналом 1 рубль', need='чтобы можно было составить из марок любую целую сумму от 1 до {t} рублей'),
    dict(head='На складе {n1} {w1} по {v1} {u1} и {n2} {w2} по {v2} {u2}, все канистры полные.', one='канистра',
         few='канистры', many='канистр', U=('литр', 'литра', 'литров'), make='отгрузить ровно {s} {us}, не открывая канистр',
         add='полных канистр по 1 литру', need='чтобы, не открывая канистр, можно было отгрузить любое целое '
                                               'количество литров от 1 до {t}'),
]


@proto('ep20-coins', 'ege-prof', 20, 'Два номинала в ограниченном количестве: какие суммы набираются, сколько добавить единиц',
       invariant='Набираемые суммы — xa + yb при 0 ≤ x ≤ m, 0 ≤ y ≤ n; наименьшее число добавочных единиц равно '
                 'наибольшему «разрыву» между соседними набираемыми суммами (с учётом нуля) на нужном промежутке.',
       varies='Номиналы и количества, сюжет (монеты, гири, марки, канистры), проверяемые суммы, верхняя граница.',
       answer_rule='в) k = max(v − наибольшая набираемая сумма ≤ v) по всем v от 1 до T.',
       fipi=r'монет по \d+ рубл|камн(ей|я), каждый массой',
       mistakes=['не учитывают ограниченность количества монет', 'проверяют только суммы вблизи T',
                 'путают «разрыв» и число недостижимых сумм'],
       kim=kim(K20, 'Как в КИМ: пункты а, б — «Можно ли…», в — наименьшее количество; итог пункта в — число.'))
def gen_ep20_coins(r):
    v1, v2 = sorted(r.sample([2, 3, 5, 7, 10, 4], 2))
    if math.gcd(v1, v2) != 1:
        return None
    n1, n2 = r.randint(6, 25), r.randint(8, 35)
    tot = n1 * v1 + n2 * v2
    ctx = r.choice(COIN_CTX)
    A = subset_sums([(v1, n1), (v2, n2)])
    T = tot - r.randint(0, 10) if r.random() < 0.6 else tot + r.randint(1, 10)
    if T <= 20:
        return None
    # наименьшее k: наибольший разрыв
    prev, k = 0, 0
    for v in range(1, T + 1):
        if A >> v & 1:
            prev = v
        k = max(k, v - prev)
    s_yes = r.choice([s for s in range(tot // 3, tot) if A >> s & 1])
    no = [s for s in range(tot // 3, tot) if not A >> s & 1]
    if not no:
        return None
    s_no = r.choice(no)
    sa, sb = r.sample([s_yes, s_no], 2)
    w = lambda n: plural(n, ctx['one'], ctx['few'], ctx['many'])
    uu = lambda v: plural(v, *ctx['U'])
    head = ctx['head'].format(n1=n1, w1=w(n1), v1=v1, n2=n2, w2=w(n2), v2=v2, u1=uu(v1), u2=uu(v2))
    q = q20(r, head, f'Можно ли {ctx["make"].format(s=sa, us=uu(sa))}?', f'Можно ли {ctx["make"].format(s=sb, us=uu(sb))}?',
            f'Сколько {ctx["add"]} как минимум нужно добавить, {ctx["need"].format(t=T)}?')
    e = (f'а) {"да" if A >> sa & 1 else "нет"}; б) {"да" if A >> sb & 1 else "нет"}. в) Наибольший промежуток между '
         f'соседними набираемыми суммами (от 0 до {T}) равен {k}, поэтому нужно {k} (меньше — не хватит, '
         f'столько — хватит).')

    def chk():
        # перебор: сколько единиц k' нужно, прямое построение множества сумм
        for kk in range(0, T + 1):
            S = set()
            for x in range(n1 + 1):
                for y in range(n2 + 1):
                    s0 = x * v1 + y * v2
                    for z in range(kk + 1):
                        S.add(s0 + z)
            if all(v in S for v in range(1, T + 1)):
                return kk == k
        return False
    return pcard(q, num(k), e), chk


STONE_CTX = [
    ('На погрузочной площадке лежат {a} {wa} массой по {ma} т и {b} {wb} массой по {mb} т.', ('бетонный блок', 'бетонных блока', 'бетонных блоков'),
     'Все блоки распределяют между двумя грузовиками.', 'грузах двух машин'),
    ('В трюме {a} {wa} по {ma} ц и {b} {wb} по {mb} ц.', ('мешок', 'мешка', 'мешков'),
     'Все мешки делят между двумя баржами.', 'грузах двух барж'),
    ('В мастерской {a} {wa} длиной по {ma} дм и {b} {wb} длиной по {mb} дм.', ('брусок', 'бруска', 'брусков'),
     'Все бруски раскладывают на две стопки, а бруски в каждой стопке укладывают в один ряд вплотную.', 'длинах двух рядов'),
    ('На складе {a} {wa} массой по {ma} кг и {b} {wb} массой по {mb} кг.', ('ящик', 'ящика', 'ящиков'),
     'Все ящики грузят на две тележки.', 'грузах двух тележек'),
]


@proto('ep20-stones', 'ege-prof', 20, 'Разбиение на две группы с наименьшей разностью сумм',
       invariant='Разность сумм групп равна T − 2S, где S — сумма одной группы; S пробегает суммы xa + yb '
                 '(0 ≤ x ≤ m, 0 ≤ y ≤ n); чётность и делимость ограничивают возможные разности.',
       varies='Массы и количества предметов, сюжет, проверяемые разности.',
       answer_rule='в) min |T − 2S| > 0 по всем набираемым S (оценка по чётности/делимости + пример).',
       fipi=r'разложить все эти камни на две группы',
       mistakes=['забывают о чётности суммы', 'ищут только равное разбиение', 'не приводят пример к оценке'],
       kim=kim(K20, 'Как в КИМ: а — «можно ли, чтобы разность составила …», б — «можно ли поровну», в — наименьшая '
                    'положительная разность; итог — число.'))
def gen_ep20_stones(r):
    ma, mb = sorted(r.sample([3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 15, 17, 22], 2))
    a, b = r.randint(3, 12), r.randint(3, 12)
    T = a * ma + b * mb
    A = subset_sums([(ma, a), (mb, b)])
    diffs = sorted({abs(T - 2 * s) for s in range(T + 1) if A >> s & 1})
    pos = [d for d in diffs if d > 0]
    if not pos:
        return None
    best = pos[0]
    head, words, split, what = r.choice(STONE_CTX)
    head = head.format(a=a, wa=plural(a, *words), ma=ma, b=b, wb=plural(b, *words), mb=mb)
    unit = head.split('по ')[1].split()[1].rstrip('.,')
    dq = r.choice([d for d in range(1, T // 3) if d % 2 == T % 2] or [2])
    q = q20(r, head + ' ' + split, f'Может ли разность в {what} составить {dq} {unit}?',
            f'Может ли разность в {what} быть равна нулю?',
            f'Какое наименьшее положительное значение может принимать разность в {what}? Ответ дайте в {unit_in(unit)}.')
    e = (f'а) {"да" if dq in diffs else "нет"}; б) {"да" if 0 in diffs else "нет"}. в) Разность равна T − 2S, T = {T}; '
         f'наименьшее положительное значение {best}.')

    def chk():
        m = min(abs(T - 2 * (x * ma + y * mb)) or 10 ** 9 for x in range(a + 1) for y in range(b + 1))
        return m == best
    return pcard(q, num(best), e), chk


def unit_in(u):
    return {'т': 'тоннах', 'ц': 'центнерах', 'дм': 'дециметрах', 'кг': 'килограммах'}.get(u, u)


BOX_CTX = [
    ('Есть три коробки: в первой {x} {w}, во второй — {y}, третья пуста. За один ход из любых двух коробок берут по '
     'одному шарику и кладут в оставшуюся коробку.', ('шарик', 'шарика', 'шариков'), 'шариков', 'коробке', 'шарики'),
    ('На столе три кучки фишек: в первой {x} {w}, во второй — {y}, в третьей фишек нет. За один ход из каких-то двух '
     'кучек снимают по одной фишке и кладут обе фишки в третью кучку.', ('фишка', 'фишки', 'фишек'), 'фишек', 'кучке', 'фишки'),
    ('В трёх вазах лежат яблоки: в первой {x} {w}, во второй — {y}, третья ваза пуста. За один ход из двух ваз берут '
     'по одному яблоку и перекладывают их в третью вазу.', ('яблоко', 'яблока', 'яблок'), 'яблок', 'вазе', 'яблоки'),
    ('На трёх полках стоят книги: на первой {x} {w}, на второй — {y}, третья пустая. За один ход с каких-то двух полок '
     'снимают по одной книге и ставят обе книги на третью полку.', ('книга', 'книги', 'книг'), 'книг', 'полке', 'книги'),
]


@proto('ep20-boxes', 'ege-prof', 20, 'Перекладывание из двух коробок в третью: инвариант по модулю 3',
       invariant='При ходе каждая разность количеств меняется на 0 или ±3, поэтому остатки разностей по модулю 3 '
                 'сохраняются; сумма постоянна. Это даёт оценку, пример строится явно.',
       varies='Начальные количества, сюжет (коробки, кучки, вазы, полки), проверяемые позиции.',
       answer_rule='в) Максимум в третьей коробке при заданном числе в первой: учитываем инвариант (x − y) mod 3 '
                   'и сумму; достижимость — пример.',
       fipi=r'За один ход берут по одному камню из любых (двух|трёх) коробок',
       mistakes=['не замечают инварианта по модулю 3', 'не приводят пример достижимости', 'забывают, что сумма постоянна'],
       kim=kim(K20, 'Как в КИМ: а — «могло ли оказаться …», б — «мог ли …», в — наибольшее количество; итог — число.'))
def gen_ep20_boxes(r):
    x0, y0 = r.randint(20, 70), r.randint(20, 70)
    if x0 == y0:
        return None
    T = x0 + y0
    head, words, gen_, loc, nom = r.choice(BOX_CTX)
    head = head.format(x=x0, w=plural(x0, *words), y=y0)
    x1 = r.randint(0, 4)
    d0 = (x0 - y0) % 3
    # максимум z при x = x1: y = T − x1 − z ≥ 0, (x1 − y) ≡ d0 (mod 3) → минимальное y
    y = next(yy for yy in range(0, 3) if (x1 - yy) % 3 == d0)
    zmax = T - x1 - y
    # пункт а: произвольная позиция с той же суммой
    xa, ya = r.randint(0, T // 2), r.randint(0, T // 2)
    za = T - xa - ya
    v1, v2 = ('на', 'на') if loc == 'полке' else ('в', 'во')
    q = q20(r, head,
            f'Может ли через несколько ходов оказаться {v1} первой {loc} {xa}, {v2} второй — {ya}, а {v1} третьей — '
            f'{za} {plural(za, *words)}?',
            f'Могут ли через несколько ходов все {nom} оказаться {v1} третьей {loc}?',
            f'Через несколько ходов число {gen_} {v1} первой {loc} стало равно {x1}. '
            f'Какое наибольшее число {gen_} могло при этом оказаться {v1} третьей {loc}?')
    e = (f'Разности количеств меняются на 0 или ±3 — остатки по модулю 3 сохраняются, сумма {T} постоянна. '
         f'в) При {x1} в первой: во второй не меньше {y} (по модулю 3), значит в третьей не больше {zmax}; '
         f'пример строится последовательными ходами.')

    def chk():
        # поиск в ширину по состояниям (x, y)
        from collections import deque
        seen = {(x0, y0)}
        dq = deque([(x0, y0)])
        best = -1
        while dq:
            x, y_ = dq.popleft()
            z = T - x - y_
            if x == x1:
                best = max(best, z)
            for nx, ny, nz in ((x - 1, y_ - 1, z + 2), (x - 1, y_ + 2, z - 1), (x + 2, y_ - 1, z - 1)):
                if min(nx, ny, nz) >= 0 and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    dq.append((nx, ny))
        return best == zmax
    return pcard(q, num(zmax), e), chk


PROD_CTX = ['На доске записаны несколько различных натуральных чисел. Произведение любых двух из них больше {L} и меньше {U}.',
            'Вася выбрал несколько различных натуральных чисел так, что произведение любых двух выбранных чисел '
            'больше {L}, но меньше {U}.',
            'Набор состоит из различных натуральных чисел, причём для любых двух чисел набора их произведение '
            'строго больше {L} и строго меньше {U}.']


@proto('ep20-products', 'ege-prof', 20, 'Произведение любых двух чисел в заданных границах: сколько чисел и какая сумма',
       invariant='Наименьшее произведение даёт пара двух наименьших чисел, наибольшее — пара двух наибольших; '
                 'оценка через a₁a₂ > L и a_{n−1}a_n < U, пример — подбор.',
       varies='Границы L и U, количество чисел в пунктах, ищется наибольшая или наименьшая сумма.',
       answer_rule='в) Перебор четвёрок a < b < c < d с ab > L и cd < U; экстремальная сумма.',
       fipi=r'произведение любых двух из которых больше \d+ и меньше \d+',
       mistakes=['проверяют не все пары', 'не доказывают оценку', 'забывают про различность чисел'],
       kim=kim(K20, 'Как в КИМ: а, б — «может ли быть 5 (6) чисел», в — наибольшая/наименьшая сумма четырёх чисел.'))
def gen_ep20_products(r):
    L = r.randint(20, 70)
    U = L + r.randint(30, 90)
    mode = r.choice(['max', 'min'])
    best = None
    # перебор: a < b < c < d, ab > L, cd < U; максимум размера набора — отдельно
    top = U // 2 + 1
    for a in range(2, top):
        for b in range(a + 1, top):
            if a * b <= L:
                continue
            for c in range(b + 1, top):
                if b * c >= U:
                    break
                for d in range(c + 1, top):
                    if c * d >= U:
                        break
                    s = a + b + c + d
                    if best is None or (s > best if mode == 'max' else s < best):
                        best = s
    if best is None:
        return None

    def maxsize():
        # наибольшее количество чисел: жадно ищем самую длинную цепочку a1 < … < an, a1a2 > L, a_{n−1}a_n < U
        bestn = 0
        for a in range(1, top):
            for b in range(a + 1, top):
                if a * b <= L or a * b >= U:
                    continue
                seq = [a, b]
                c = b + 1
                while seq[-2] * c < U if len(seq) >= 2 else False:
                    if seq[-1] * c < U:
                        seq.append(c)
                    c += 1
                    if c > top:
                        break
                bestn = max(bestn, len(seq))
        return bestn
    q = q20(r, pick(r, *PROD_CTX).format(L=L, U=U), 'Может ли чисел быть пять?', 'Может ли чисел быть шесть?',
            f'Какое {"наибольшее" if mode == "max" else "наименьшее"} значение может принимать сумма этих чисел, если их четыре?')
    e = (f'в) Для четырёх чисел a < b < c < d достаточно ab > {L} и cd < {U}; перебор даёт '
         f'{"наибольшую" if mode == "max" else "наименьшую"} сумму {best}.')

    def chk():
        vals = []
        for comb in itertools.combinations(range(2, top), 4):
            if all(L < x * y < U for x, y in itertools.combinations(comb, 2)):
                vals.append(sum(comb))
        return bool(vals) and (max(vals) if mode == 'max' else min(vals)) == best
    return pcard(q, num(best), e), chk


CONS_CTX = ['На доске записано несколько подряд идущих натуральных чисел. Ровно {m} из них {vd} на {p}.',
            'Зрители заняли в длинном ряду кинозала несколько мест, номера которых идут подряд без пропусков; '
            'ровно {m} из этих номеров {vd2} на {p}.',
            'Кладовщик выдал несколько жетонов, номера которых — подряд идущие натуральные числа. Среди номеров выданных '
            'жетонов ровно {m} {vd2} на {p}.',
            'Билеты в кассе пронумерованы подряд идущими натуральными числами. Продали несколько билетов с подряд '
            'идущими номерами, среди которых ровно {m} номеров делятся на {p}.']


@proto('ep20-consecutive', 'ege-prof', 20, 'Подряд идущие числа: количество кратных двум разным числам',
       invariant='Среди L подряд идущих чисел кратных p не меньше ⌊L/p⌋ и не больше ⌈L/p⌉; «ровно m кратных p» '
                 'ограничивает длину: L ≤ (m + 1)p − 1; для k нужно mk + 1 ≤ L при подходящем расположении.',
       varies='Число m, делитель p, сюжет (числа на доске, страницы, билеты).',
       answer_rule='в) Наибольшее k, для которого возможно больше m кратных k: оценка по длине + согласование '
                   'остатков (пример).',
       fipi=r'последовательных натуральных чисел, среди которых|На доске записано k последовательных натуральных чисел',
       mistakes=['не учитывают взаимное расположение кратных p и k', 'путают «не больше» и «ровно»',
                 'не приводят пример'],
       kim=kim(K20, 'Как в КИМ: а, б — «могло ли…», в — наибольшее возможное k; итог — число.'))
def gen_ep20_consecutive(r):
    m = r.randint(3, 7)
    p = r.choice([10, 12, 15, 18, 20, 24, 25, 30])

    def possible(k):
        # есть ли блок, в котором ровно m кратных p и не меньше m + 1 кратных k
        g = math.gcd(k, p)
        for rr in range(0, p, g):
            # m + 1 кратных k: t, t + k, …, t + mk, t ≡ rr (mod p); минимальный блок [t, t + mk]
            t = rr if rr else p
            cnt = (t + m * k) // p - (t - 1) // p
            if cnt <= m:
                return True
        return False
    kmax = next(k for k in range((m + 1) * p, 0, -1) if possible(k) and k != p)
    ctx = r.choice(CONS_CTX)
    head = ctx.format(m=m, p=p, vd='делятся' if m > 1 else 'делится', vd2='делятся' if m > 1 else 'делится')
    k1 = r.choice([p + 1, p + 2, p - 1, 2 * p // 3])
    q = q20(r, head, f'Может ли среди них оказаться больше {m} чисел, делящихся на {k1}?',
            f'Может ли среди них оказаться меньше {m} чисел, делящихся на {max(2, p // 2 + 1)}?',
            f'Найдите наибольшее натуральное k, при котором среди этих чисел может оказаться больше {m} чисел, делящихся на k.')
    e = (f'в) Блок с ровно {m} кратными {p} содержит не больше {(m + 1) * p - 1} чисел; чтобы кратных k было хотя бы '
         f'{m + 1}, нужно {m}k + 1 ≤ длины и подходящее расположение остатков; наибольшее k = {kmax}.')

    def chk():
        for k in range((m + 1) * p, 0, -1):
            lcm = k * p // math.gcd(k, p)
            for s in range(1, lcm + 1):
                # наибольшая длина блока, начинающегося с s, с ровно m кратными p
                first = -(-s // p) * p
                end = first + m * p - 1            # до (m + 1)-го кратного p, не включая
                if end < s:
                    continue
                cp = end // p - (s - 1) // p
                if cp != m:
                    continue
                ck = end // k - (s - 1) // k
                if ck > m:
                    return k == kmax
        return False
    return pcard(q, num(kmax), e), chk


CIRC_CTX = ['По кругу в некотором порядке записаны числа {nums}. Для каждой пары соседних чисел вычислили модуль их '
            'разности, а затем все полученные модули сложили.',
            'За круглым столом рассаживают {n} гостей, на карточках которых написаны числа {nums} (у каждого своё). '
            'Для каждой пары соседей находят модуль разности их чисел и складывают все эти модули.',
            'На окружности отмечены {n} точек, в них в некотором порядке расставлены числа {nums}. Для каждой дуги '
            'между соседними точками записали модуль разности чисел на её концах и нашли сумму записанных модулей.']


@proto('ep20-circle-diffs', 'ege-prof', 20, 'Числа по кругу: сумма модулей разностей соседей',
       invariant='Сумма модулей разностей по кругу чётна (равна сумме разностей со знаками плюс удвоенные '
                 'отрицательные); наибольшее значение — чередование «больших» и «малых»: 2·(сумма больших − сумма малых).',
       varies='Набор чисел (6–9 различных), проверяемые значения суммы, сюжет.',
       answer_rule='в) Оценка: каждое число входит в сумму дважды со знаком; максимум при чередовании; пример.',
       fipi=r'По окружности в некотором порядке расставлены натуральные числа',
       mistakes=['не замечают чётности суммы', 'дают пример без оценки', 'ошибаются в расстановке для нечётного n'],
       kim=kim(K20, 'Как в КИМ: а — «приведите пример …», б — «может ли сумма быть равна …», в — наибольшее значение.'))
def gen_ep20_circle_diffs(r):
    n = r.randint(6, 9)
    nums = sorted(r.sample(range(1, 31), n))
    # максимум: перебор всех перестановок (n ≤ 9) — в генераторе формула, в проверке перебор
    h = n // 2
    if n % 2 == 0:
        best = 2 * (sum(nums[h:]) - sum(nums[:h]))
    else:
        best = 2 * (sum(nums[h + 1:]) - sum(nums[:h]))
    vals_a = best - 2 * r.randint(1, 5)
    odd = best - 2 * r.randint(1, 5) + 1
    txt = ', '.join(str(v) for v in nums[:-1]) + ' и ' + str(nums[-1])
    q = q20(r, pick(r, *CIRC_CTX).format(nums=txt, n=n),
            f'Может ли полученная сумма быть равна {vals_a}?', f'Может ли полученная сумма быть равна {odd}?',
            'Какое наибольшее значение может принимать полученная сумма?')
    e = (f'б) Нет: сумма модулей имеет ту же чётность, что сумма разностей со знаками (0), значит, чётна. '
         f'в) Каждое число входит в сумму дважды (с плюсом или минусом); наибольшее значение {best} — при чередовании больших и малых чисел.')

    def chk():
        first, rest = nums[0], nums[1:]
        m = 0
        for perm in itertools.permutations(rest):
            seq = (first,) + perm
            s = sum(abs(seq[i] - seq[i - 1]) for i in range(n))
            if s > m:
                m = s
        return m == best
    return pcard(q, num(best), e), chk


@proto('ep20-ones', 'ege-prof', 20, 'Единицы со знаками «+»: какие суммы получаются',
       invariant='Сумма складывается из блоков 1, 11, 111, 1111 …; если блоков вида 11…1 из k единиц x_k, то '
                 'n = Σ k·x_k, S = Σ R_k·x_k; перебор числа длинных блоков.',
       varies='Сумма S, количество единиц n в пунктах а и б.',
       answer_rule='в) Для скольких n можно получить S: перебираем количества блоков 1111, 111, 11, остаток — единицы.',
       fipi=r'единиц подряд\. Между некоторыми из них расставляют знаки',
       mistakes=['забывают блоки из трёх и более единиц', 'считают одно и то же n дважды', 'не проверяют остаток'],
       kim=kim(K20, 'Как в КИМ: а, б — «можно ли получить сумму … при n = …», в — «для скольких n …»; итог — число.'))
def gen_ep20_ones(r):
    S = r.randint(100, 400)
    ns = set()
    for d in range(0, S // 1111 + 1):
        for c in range(0, (S - 1111 * d) // 111 + 1):
            for b in range(0, (S - 1111 * d - 111 * c) // 11 + 1):
                a = S - 1111 * d - 111 * c - 11 * b
                ns.add(a + 2 * b + 3 * c + 4 * d)
    ans = len(ns)
    n_yes = r.choice(sorted(ns))
    n_no = r.choice([v for v in range(min(ns), max(ns)) if v not in ns] or [max(ns) + 1])
    na, nb = r.sample([n_yes, n_no], 2)
    head = pick(r, 'На доске написано n единиц подряд. Между некоторыми соседними единицами ставят знаки «+» и находят '
                   'значение получившегося выражения (например, из 1111111 можно получить 11 + 111 + 1 + 1 = 124).',
                'Выписано подряд n цифр 1. Между некоторыми из них вставляют плюсы и вычисляют сумму получившихся '
                'чисел (например, 11111 → 11 + 1 + 11 = 23).',
                'Полоску бумаги, на которой подряд напечатаны n единиц, разрезают между некоторыми цифрами; каждый '
                'кусок читают как число и все полученные числа складывают (например, 111111 → 11 + 1 + 111 = 123).',
                'Калькулятор умеет набирать только цифру 1 и знак «+». Мальчик нажал клавишу «1» ровно n раз, а между '
                'некоторыми нажатиями нажимал «+» (например, 11 + 1 + 111 при n = 6), после чего вычислил результат.')
    q = q20(r, head, f'Можно ли получить сумму {S} при n = {na}?', f'Можно ли получить сумму {S} при n = {nb}?',
            f'Для скольких значений n можно получить сумму {S}?')
    e = f'в) S = x₁ + 11x₂ + 111x₃ + …, n = x₁ + 2x₂ + 3x₃ + …; перебор x₂, x₃ даёт {ans} различных n.'

    def chk():
        # динамика: какие суммы достижимы ровно из n единиц
        reach = [set() for _ in range(S + 1)]
        reach[0].add(0)
        blocks = [(1, 1), (2, 11), (3, 111), (4, 1111)]
        for nn in range(1, S + 1):
            cur = set()
            for k, v in blocks:
                if k <= nn:
                    for s0 in reach[nn - k]:
                        if s0 + v <= S:
                            cur.add(s0 + v)
            reach[nn] = cur
        return sum(1 for nn in range(1, S + 1) if S in reach[nn]) == ans
    return pcard(q, num(ans), e), chk


def digs(N):
    return [int(c) for c in str(N)]


OPS = [
    ('из него вычитают сумму его цифр, а результат делят на 3', lambda N: (N - sum(digs(N))) // 3, lambda a, b, c: (a, b)),
    ('из него вычитают сумму его цифр, а результат делят на 9', lambda N: (N - sum(digs(N))) // 9, lambda a, b, c: (a, b)),
    ('из него вычитают число, записанное теми же цифрами в обратном порядке', lambda N: N - int(str(N)[::-1]),
     lambda a, b, c: (a - c,)),
    ('к нему прибавляют число, записанное теми же цифрами в обратном порядке (если последняя цифра 0, '
     'обращённое число двузначное или однозначное)', lambda N: N + int(str(N)[::-1]), lambda a, b, c: (a + c, b)),
]


@proto('ep20-digit-op', 'ege-prof', 20, 'Операция над цифрами трёхзначного числа: сколько различных результатов',
       invariant='Результат операции выражается через цифры (например, (N − S(N))/3 = 33a + 3b); различные '
                 'результаты ⇔ различные наборы «существенных» цифр; считаем их на заданном промежутке.',
       varies='Операция (вычесть сумму цифр и поделить, вычесть/прибавить обращённое), промежуток исходных чисел.',
       answer_rule='в) Количество различных значений выражения от цифр при N из промежутка.',
       fipi=r'С трёхзначным числом производят следующую операцию',
       mistakes=['считают одинаковые результаты разными', 'не учитывают границы промежутка', 'ошибка в записи через цифры'],
       kim=kim(K20, 'Как в КИМ: а, б — «могло ли получиться …», в — «сколько различных чисел может получиться»; итог — число.'))
def gen_ep20_digit_op(r):
    txt, op, key = r.choice(OPS)
    lo = r.randint(100, 400)
    hi = r.randint(lo + 150, 999)
    keys = set()
    for N in range(lo, hi + 1):
        a, b, c = digs(N)
        keys.add(key(a, b, c))
    ans = len(keys)
    res_all = sorted({op(N) for N in range(100, 1000)})
    ra = r.choice(res_all)
    cand_no = [v for v in range(min(res_all), max(res_all)) if v not in set(res_all)]
    rb = r.choice(cand_no) if cand_no else ra + 1
    head = pick(r, f'С трёхзначным числом проделывают следующее: {txt}.',
                f'Программа получает на вход трёхзначное число и выполняет такие действия: {txt}.',
                f'Каждому трёхзначному числу сопоставляют результат следующей операции: {txt}.',
                f'Петя задумывает трёхзначное число, и с ним поступают так: {txt}.')
    q = q20(r, head, f'Может ли в результате получиться {tnum(ra)}?', f'Может ли в результате получиться {tnum(rb)}?',
            f'Сколько различных чисел может получиться, если исходное число — любое из чисел от {lo} до {hi} включительно?')
    e = f'в) Результат зависит только от комбинации цифр {("a, b" if len(key(1, 2, 3)) == 2 else "a − c")}; различных значений {ans}.'

    def chk():
        return len({op(N) for N in range(lo, hi + 1)}) == ans
    return pcard(q, num(ans), e), chk


@proto('ep20-containers', 'ege-prof', 20, 'Две массы и доля по количеству: доля по массе',
       invariant='Если доля «особых» предметов по количеству p, то доля по массе максимальна, когда все особые — '
                 'тяжёлые, а остальные — лёгкие (и минимальна наоборот): p·M/(p·M + (1 − p)·m).',
       varies='Массы (m, M), доля по количеству, спрашивается наибольшая или наименьшая доля массы, сюжет.',
       answer_rule='в) Крайний случай распределения тяжёлых и лёгких + проверка, что он допустим.',
       fipi=r'масса каждого из которых равна \d+ тонн или \d+ тонн',
       mistakes=['берут долю по количеству за долю по массе', 'не проверяют крайний случай', 'ошибка в процентах'],
       kim=kim(K20, 'Как в КИМ: а, б — «может ли масса … составить … %», в — наибольшая доля; итог — число (в процентах).'))
def gen_ep20_containers(r):
    m1, m2 = r.choice([(10, 40), (20, 60), (15, 45), (10, 30), (5, 20), (12, 48), (25, 100), (20, 80), (10, 90)])
    p = F(r.choice([10, 20, 25, 40, 50, 60, 75, 80]), 100)
    mode = r.choice(['max', 'min'])
    if mode == 'max':
        share = p * m2 / (p * m2 + (1 - p) * m1)
    else:
        share = p * m1 / (p * m1 + (1 - p) * m2)
    pct = share * 100
    if not nice(pct, 2):
        return None
    ctx = r.choice([('В порту стоят только полностью загруженные контейнеры массой {m1} т или {m2} т. В части контейнеров '
                     'находится кофе, и таких контейнеров {p} % от общего числа.', 'контейнеров с кофе', 'всех контейнеров'),
                    ('На складе хранятся только ящики массой {m1} кг или {m2} кг. В части ящиков — фарфор; ящики с '
                     'фарфором составляют {p} % от общего числа ящиков.', 'ящиков с фарфором', 'всех ящиков'),
                    ('На станции стоят только вагоны массой {m1} т или {m2} т. Часть вагонов гружена углём, и таких '
                     'вагонов {p} % от общего числа.', 'вагонов с углём', 'всех вагонов'),
                    ('В библиотеку привезли пачки книг только двух видов: массой {m1} кг и массой {m2} кг. Пачки с '
                     'учебниками составляют {p} % от общего числа пачек.', 'пачек с учебниками', 'всех пачек')])
    head = ctx[0].format(m1=m1, m2=m2, p=tnum(p * 100))
    qa = tnum(r.choice([5, 15, 30, 45, 55, 70, 85]))
    q = q20(r, head, f'Может ли масса {ctx[1]} составить {qa} % от массы {ctx[2]}?',
            f'Может ли масса {ctx[1]} составить ровно {tnum(p * 100)} % от массы {ctx[2]}?',
            f'Какую {"наибольшую" if mode == "max" else "наименьшую"} долю (в процентах) может составлять масса {ctx[1]} от массы {ctx[2]}?')
    e = (f'в) Доля по массе {"наибольшая" if mode == "max" else "наименьшая"}, когда все особые — '
         f'{"тяжёлые" if mode == "max" else "лёгкие"}, а остальные — {"лёгкие" if mode == "max" else "тяжёлые"}: {tnum(pct)} %.')

    def chk():
        best = None
        for N in range(1, 101):
            k = p * N
            if k.denominator != 1:
                continue
            k = int(k)
            for h1 in range(k + 1):               # тяжёлых среди особых
                for h2 in range(N - k + 1):       # тяжёлых среди остальных
                    ms = h1 * m2 + (k - h1) * m1
                    mt = ms + h2 * m2 + (N - k - h2) * m1
                    v = F(ms, mt)
                    if best is None or (v > best if mode == 'max' else v < best):
                        best = v
        return best * 100 == pct
    return pcard(q, num(pct), e), chk


@proto('ep20-digits-sum', 'ege-prof', 20, 'Различные числа из двух цифр: наименьшее количество слагаемых',
       invariant='Числа записываются только цифрами d₁, d₂; чтобы слагаемых было меньше, берём наибольшие '
                 'подходящие числа; оценка — по остаткам (последняя цифра суммы) и по величине.',
       varies='Пара цифр, сумма, количество слагаемых в пунктах.',
       answer_rule='в) Наименьшее число различных слагаемых с суммой S (перебор/оценка по последней цифре).',
       fipi=r'в записи которых могут быть только цифры',
       mistakes=['используют одно число дважды', 'не учитывают последнюю цифру суммы', 'не доказывают минимальность'],
       kim=kim(K20, 'Как в КИМ: а, б — «может ли сумма быть равна …», в — наименьшее количество чисел; итог — число.'))
def gen_ep20_digits_sum(r):
    d1, d2 = sorted(r.sample([1, 2, 3, 4, 5, 6, 7, 8, 9], 2))
    nums = sorted(int(''.join(t)) for L in range(1, 5) for t in itertools.product(str(d1) + str(d2), repeat=L))
    S = r.randint(200, 3000)
    # минимум количества различных слагаемых: динамика «рюкзак 0/1 по количеству»
    INF = 10 ** 9
    best = [INF] * (S + 1)
    best[0] = 0
    for v in nums:
        if v > S:
            break
        for s in range(S, v - 1, -1):
            if best[s - v] + 1 < best[s]:
                best[s] = best[s - v] + 1
    if best[S] >= INF or best[S] <= 2:
        return None
    ans = best[S]
    sa, sb = r.randint(50, 300), r.randint(50, 300)
    head = pick(r, f'Петя записал в тетрадь несколько попарно различных натуральных чисел, используя лишь цифры {d1} и {d2} '
                   f'(число может состоять и из одной повторяющейся цифры).',
                f'Из карточек с цифрами {d1} и {d2} (карточек каждого вида сколько угодно) сложили несколько попарно '
                f'различных натуральных чисел.',
                f'На табло исправны только сегменты, позволяющие показывать цифры {d1} и {d2}. На нём по очереди показали '
                f'несколько попарно различных натуральных чисел (в записи каждого — только эти цифры).',
                f'Шифровальщик составляет коды — натуральные числа, записанные только цифрами {d1} и {d2} (можно одной '
                f'из них). Он составил несколько попарно различных кодов.')
    q = q20(r, head, f'Может ли сумма этих чисел быть равной {sa}?', f'Может ли сумма этих чисел быть равной {sb}?',
            f'Сумма этих чисел равна {S}. Найдите наименьшее возможное количество чисел.')
    e = f'в) Наименьшее количество различных слагаемых с суммой {S} равно {ans} (оценка по величине и последней цифре + пример).'

    def chk():
        # по количеству: множества сумм из k различных чисел (битовые маски)
        lay = [1] + [0] * 40
        for v in nums:
            if v > S:
                continue
            for k in range(39, -1, -1):
                if lay[k]:
                    lay[k + 1] |= (lay[k] << v) & ((1 << (S + 1)) - 1)
        for k in range(41):
            if lay[k] >> S & 1:
                return k == ans
        return False
    return pcard(q, num(ans), e), chk


@proto('ep20-pair-moves', 'ege-prof', 20, 'Ходы с парой чисел: инвариант по модулю 3 и монотонная сумма',
       invariant='Ход (a; b) → (a + 2; b − 1) или (a − 1; b + 2) увеличивает сумму на 1, разность меняется на ±3; '
                 'значит, число ходов = прирост суммы, а остаток a − b по модулю 3 сохраняется.',
       varies='Начальная пара, верхняя граница M, проверяемые пары.',
       answer_rule='в) Наибольшее число ходов при a, b ≤ M: 2M − (a₀ + b₀), уменьшенное с учётом (a − b) mod 3; пример.',
       fipi=r'за один ход (можно )?получ(ить|ают) пару|получается пара',
       mistakes=['не замечают, что сумма растёт на 1', 'не учитывают инвариант разности', 'не проверяют положительность'],
       kim=kim(K20, 'Как в КИМ: а — «можно ли за … ходов …», б — «за какое число ходов …», в — наибольшее число ходов.'))
def gen_ep20_pair_moves(r):
    a0, b0 = r.randint(2, 15), r.randint(2, 15)
    M = r.randint(40, 120)
    d0 = (a0 - b0) % 3
    # финальная пара с наибольшей суммой при a, b ≤ M и (a − b) ≡ d0
    # (M; M) недостижима: у неё нет предшественника с числами ≤ M
    best_sum = max(a + b for a in range(M - 2, M + 1) for b in range(M - 2, M + 1) if (a - b) % 3 == d0 and (a, b) != (M, M))
    ans = best_sum - a0 - b0
    S = a0 + b0 + r.randint(20, 150)
    k_a = r.randint(10, 60)
    head = pick(r, f'Робот хранит пару натуральных чисел (a; b). За один шаг он заменяет её на (a + 2; b − 1) или на '
                   f'(a − 1; b + 2), причём оба числа после замены должны остаться натуральными. В начале у робота пара '
                   f'({a0}; {b0}).',
                f'В двух кучках лежат фишки: в первой {a0}, во второй {b0}. За один шаг из одной кучки убирают одну фишку, '
                f'а в другую добавляют две; ни одна кучка не должна оставаться пустой. Состояние записывают парой '
                f'(a; b) — числа фишек в кучках.',
                f'На двух счётчиках горят числа {a0} и {b0}. За один шаг показание одного счётчика увеличивают на 2, а другого '
                f'уменьшают на 1; оба показания всегда должны оставаться натуральными. Пару показаний записывают как (a; b).')
    q = q20(r, head,
            f'Можно ли за {k_a} {plural(k_a, "шаг", "шага", "шагов")} получить пару, одно из чисел которой равно '
            f'{a0 + 2 * k_a - r.randint(0, 3)}?',
            f'Через сколько шагов сумма чисел пары станет равной {S}?',
            f'Какое наибольшее число шагов можно сделать, если после каждого шага ни одно из чисел пары не должно '
            f'превышать {M}?')
    e = (f'Сумма растёт на 1 за ход, разность меняется на ±3. в) Наибольшая сумма пары с числами ≤ {M} и нужным '
         f'остатком разности — {best_sum}, значит, ходов не больше {ans}; пример строится чередованием ходов.')

    def chk():
        # динамика по состояниям в порядке возрастания суммы: наибольшая длина пути
        from functools import lru_cache
        import sys
        sys.setrecursionlimit(10000)

        @lru_cache(maxsize=None)
        def longest(a, b):
            best_ = 0
            for na, nb in ((a + 2, b - 1), (a - 1, b + 2)):
                if na >= 1 and nb >= 1 and na <= M and nb <= M:
                    best_ = max(best_, 1 + longest(na, nb))
            return best_
        return longest(a0, b0) == ans
    return pcard(q, num(ans), e), chk


END_CTX = [(2, 6), (1, 5), (3, 7), (4, 8), (2, 8)]


@proto('ep20-endings', 'ege-prof', 20, 'Различные числа с заданными последними цифрами и данной суммой',
       invariant='Последняя цифра суммы определяется количеством чисел каждого вида; наименьшая возможная сумма '
                 'k различных чисел, оканчивающихся на d, равна dk + 10·k(k − 1)/2; большие суммы получаются '
                 'увеличением чисел на 10.',
       varies='Пара последних цифр, количество чисел, сумма.',
       answer_rule='в) Наименьшее k: сравнение по модулю 10 и оценка суммы снизу; пример.',
       fipi=r'оканчивается (или )?на цифру|либо чётное, либо его десятичная запись|различных натуральных чисел, сумма которых равна',
       mistakes=['не учитывают различность чисел при оценке суммы', 'неверно считают последнюю цифру', 'нет примера'],
       kim=kim(K20, 'Как в КИМ: а — «может ли быть поровну …», б — «может ли ровно одно …», в — наименьшее количество.'))
def gen_ep20_endings(r):
    d1, d2 = r.choice(END_CTX)
    n = r.randint(10, 18)
    mins = lambda k, d: d * k + 5 * k * (k - 1)
    base = mins(n, d1)
    S = base + r.randint(0, 60) * 2 + (0 if r.random() < 0.5 else 0)

    def feas(k):
        # k чисел на d2, n − k чисел на d1
        return (S - (n - k) * d1 - k * d2) % 10 == 0 and S >= mins(n - k, d1) + mins(k, d2)
    ks = [k for k in range(0, n + 1) if feas(k)]
    if not ks or ks[0] == 0:
        return None
    ans = ks[0]
    head = pick(r, f'Учитель выписал {n} попарно различных натуральных чисел; последняя цифра каждого из них — {d1} или {d2}, '
                   f'а сумма всех выписанных чисел равна {S}.',
                f'Имеется набор из {n} попарно различных натуральных чисел с суммой {S}; каждое число набора имеет '
                f'последнюю цифру {d1} либо {d2}.',
                f'В лотерее разыграли {n} билетов с попарно различными номерами; номер каждого билета оканчивается '
                f'на {d1} или на {d2}, а сумма всех номеров равна {S}.',
                f'Кладовщик промаркировал {n} ящиков попарно различными натуральными числами, каждое из которых '
                f'заканчивается цифрой {d1} или {d2}; сумма всех маркировок оказалась равной {S}.')
    q = q20(r, head, f'Могло ли чисел с последней цифрой {d1} оказаться столько же, сколько чисел с последней цифрой {d2}?',
            f'Могло ли среди них оказаться ровно одно число с последней цифрой {d2}?',
            f'Найдите наименьшее возможное количество чисел с последней цифрой {d2}.')
    e = f'в) Нужны совпадение последней цифры суммы и оценка снизу суммы различных чисел; наименьшее количество — {ans}.'

    def chk():
        # динамика по наборам: маски сумм для (количество на d1, количество на d2)
        A = [v for v in range(d1, S + 1, 10)]
        Bn = [v for v in range(d2, S + 1, 10)]
        full = (1 << (S + 1)) - 1
        # суммы j различных чисел из списка
        def layers(lst):
            lay = [1] + [0] * n
            for v in lst:
                for j in range(n - 1, -1, -1):
                    if lay[j]:
                        lay[j + 1] |= (lay[j] << v) & full
            return lay
        LA, LB = layers(A), layers(Bn)
        for k in range(0, n + 1):
            la, lb = LA[n - k], LB[k]
            # есть ли s: s ∈ la, S − s ∈ lb
            s = la
            while s:
                low = s & -s
                pos = low.bit_length() - 1
                if lb >> (S - pos) & 1:
                    return k == ans
                s ^= low
        return False
    return pcard(q, num(ans), e), chk


# ================================================================ №15: стереометрия — координаты

def v_sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def v_add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def v_mul(a, k):
    return tuple(x * k for x in a)


def v_dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def v_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def v_len(a, sq=math.sqrt):
    return sq(v_dot(a, a))


def lerp(a, b, t):
    """Точка на отрезке AB: A + t(B − A)."""
    return tuple(x + (y - x) * t for x, y in zip(a, b))


SUBI = {'1': '₁'}


def lab(n):
    """Имя точки в тексте: A1 → A₁."""
    return n.replace('1', '₁')


class Solid:
    """Многогранник: вершины (имя → координаты), рёбра, грани (для сечений и чертежа)."""

    def __init__(self, pts, edges, faces, kind):
        self.pts, self.edges, self.faces, self.kind = pts, edges, faces, kind


def mk_box(a, b, c, sq, Q):
    P = {'A': (Q(0), Q(0), Q(0)), 'B': (Q(a), Q(0), Q(0)), 'C': (Q(a), Q(b), Q(0)), 'D': (Q(0), Q(b), Q(0))}
    for n in 'ABCD':
        x, y, _ = P[n]
        P[n + '1'] = (x, y, Q(c))
    E = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')] + [(n + '1', m + '1') for n, m in [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]] \
        + [(n, n + '1') for n in 'ABCD']
    Fc = ['ABCD', ['A1', 'B1', 'C1', 'D1'], ['A', 'B', 'B1', 'A1'], ['B', 'C', 'C1', 'B1'], ['C', 'D', 'D1', 'C1'], ['D', 'A', 'A1', 'D1']]
    return Solid(P, E, Fc, 'box')


def mk_prism3(a, h, sq, Q):
    s3 = sq(3)
    P = {'A': (Q(0), Q(0), Q(0)), 'B': (Q(a), Q(0), Q(0)), 'C': (Q(a) / 2, Q(a) * s3 / 2, Q(0))}
    for n in 'ABC':
        x, y, _ = P[n]
        P[n + '1'] = (x, y, Q(h))
    E = [('A', 'B'), ('B', 'C'), ('C', 'A'), ('A1', 'B1'), ('B1', 'C1'), ('C1', 'A1')] + [(n, n + '1') for n in 'ABC']
    Fc = ['ABC', ['A1', 'B1', 'C1'], ['A', 'B', 'B1', 'A1'], ['B', 'C', 'C1', 'B1'], ['C', 'A', 'A1', 'C1']]
    return Solid(P, E, Fc, 'prism3')


def mk_pyr4(a, h, sq, Q):
    """Правильная четырёхугольная пирамида SABCD: сторона a, высота h (центр основания в начале координат)."""
    t = Q(a) / 2
    P = {'A': (-t, -t, Q(0)), 'B': (t, -t, Q(0)), 'C': (t, t, Q(0)), 'D': (-t, t, Q(0)), 'S': (Q(0), Q(0), h)}
    E = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')] + [('S', n) for n in 'ABCD']
    Fc = ['ABCD', 'SAB', 'SBC', 'SCD', 'SDA']
    return Solid(P, E, Fc, 'pyr4')


def mk_pyr3(a, h, sq, Q):
    """Правильная треугольная пирамида SABC: сторона a, высота h."""
    s3 = sq(3)
    A = (Q(0), Q(0), Q(0))
    B = (Q(a), Q(0), Q(0))
    C = (Q(a) / 2, Q(a) * s3 / 2, Q(0))
    O = (Q(a) / 2, Q(a) * s3 / 6, Q(0))
    P = {'A': A, 'B': B, 'C': C, 'S': (O[0], O[1], h)}
    E = [('A', 'B'), ('B', 'C'), ('C', 'A'), ('S', 'A'), ('S', 'B'), ('S', 'C')]
    return Solid(P, E, ['ABC', 'SAB', 'SBC', 'SCA'], 'pyr3')


def mk_tri_rect(p, q, r_, sq, Q):
    """Тетраэдр DABC: DA, DB, DC попарно перпендикулярны."""
    P = {'D': (Q(0), Q(0), Q(0)), 'A': (Q(p), Q(0), Q(0)), 'B': (Q(0), Q(q), Q(0)), 'C': (Q(0), Q(0), Q(r_))}
    E = [('D', 'A'), ('D', 'B'), ('D', 'C'), ('A', 'B'), ('B', 'C'), ('C', 'A')]
    return Solid(P, E, ['ABC', 'DAB', 'DBC', 'DCA'], 'trirect')


def mk_pyr6(a, h, sq, Q):
    s3 = sq(3)
    P = {}
    names = 'ABCDEF'
    coords = [(Q(a), Q(0)), (Q(a) / 2, Q(a) * s3 / 2), (-Q(a) / 2, Q(a) * s3 / 2), (-Q(a), Q(0)),
              (-Q(a) / 2, -Q(a) * s3 / 2), (Q(a) / 2, -Q(a) * s3 / 2)]
    for n, (x, y) in zip(names, coords):
        P[n] = (x, y, Q(0))
    P['S'] = (Q(0), Q(0), h)
    E = [(names[i], names[(i + 1) % 6]) for i in range(6)] + [('S', n) for n in names]
    Fc = [names] + ['S' + names[i] + names[(i + 1) % 6] for i in range(6)]
    return Solid(P, E, Fc, 'pyr6')


def fnice(x, maxdec=2, lim=10000):
    """Число float — «хорошее» (конечная десятичная ≤ maxdec знаков)? → Fraction или None."""
    if abs(x) > lim:
        return None
    y = x * 10 ** maxdec
    if abs(y - round(y)) < 1e-7:
        return F(round(y), 10 ** maxdec)
    return None


def pick_repr(r, val, kind='len'):
    """Выбор числового итога: сама величина или её квадрат (если величина иррациональна).
    Для углов val = (sin, cos, tan) → тангенс, косинус, синус, градусы."""
    if kind == 'len':
        v = fnice(val)
        if v is not None:
            return v, ''
        v2 = fnice(val * val)
        if v2 is not None:
            return v2, 'sq'
        return None
    s, c, t = val
    deg = math.degrees(math.atan2(s, c))
    opts = []
    if abs(deg - round(deg)) < 1e-7 and round(deg) in (30, 45, 60, 90) and r.random() < 0.5:
        return F(round(deg)), 'deg'
    for name, x in (('tg', t), ('cos', c), ('sin', s)):
        if x is None:
            continue
        v = fnice(x)
        if v is not None and v != 0:
            opts.append((v, name))
        v2 = fnice(x * x)
        if v2 is not None and v2 != 0:
            opts.append((v2, name + '2'))
    if not opts:
        return None
    exact = [o for o in opts if not o[1].endswith('2')]
    return r.choice(exact) if exact and r.random() < 0.8 else r.choice(opts)


ASK15 = {'': 'В ответ запишите найденное значение.',
         'sq': 'В ответ запишите квадрат найденной величины.',
         'deg': 'В ответ запишите величину угла в градусах.',
         'tg': 'В ответ запишите тангенс найденного угла.', 'cos': 'В ответ запишите косинус найденного угла.',
         'sin': 'В ответ запишите синус найденного угла.', 'tg2': 'В ответ запишите квадрат тангенса найденного угла.',
         'cos2': 'В ответ запишите квадрат косинуса найденного угла.', 'sin2': 'В ответ запишите квадрат синуса найденного угла.'}


def ang_value(kind, s, c):
    """Значение угла в выбранном виде из синуса и косинуса (sympy или float)."""
    t = s / c if c != 0 else None
    return {'deg': None, 'tg': t, 'cos': c, 'sin': s, 'tg2': t * t if t is not None else None,
            'cos2': c * c, 'sin2': s * s}[kind]


def proj_svg(solid, show, extra_pts=None, segs=()):
    """Чертёж многогранника в косоугольной проекции (все рёбра + доп. отрезки)."""
    P = dict(solid.pts)
    if extra_pts:
        P.update(extra_pts)
    k = 0.42
    pts2 = {}
    for n, (x, y, z) in P.items():
        x, y, z = float(x), float(y), float(z)
        pts2[lab(n)] = (x + k * y, z + k * y * 0.8)
    sg = [lab(a) + '|' + lab(b) for a, b in solid.edges] + [lab(a) + '|' + lab(b) for a, b in segs]
    # svg_geom принимает отрезки как строки из двух имён; имена с индексом длиннее одного символа —
    # поэтому переименовываем точки в одиночные символы и возвращаем подписи через labels
    names = list(pts2)
    single = {n: chr(0xE000 + i) for i, n in enumerate(names)}
    pts_s = {single[n]: pts2[n] for n in names}
    segs_s = [single[a] + single[b] for a, b in (s_.split('|') for s_ in sg)]
    svg = svg_geom(pts_s, segs=segs_s, labels=[single[n] for n in names if n in show or n.rstrip('₁') in show], width=300)
    for n in names:
        svg = svg.replace(f'font-style="italic">{single[n]}</text>', f'font-style="italic">{n}</text>')
    return svg


# ---------------------------------------------------------------- №15: сценарии (конфигурации с верным пунктом а)

def ratio_txt(p, q):
    return f'{p} : {q}'


def sc_pyr4_m(r):
    a = r.choice([2, 4, 6, 8, 10, 12])
    l = r.randint(a // 2 + 1, a + 6)
    h2 = F(l * l) - F(a * a, 2)
    if h2 <= 0:
        return None
    p, q = r.choice([(1, 1), (1, 1), (1, 2), (2, 1), (1, 3), (3, 1)])
    mdesc = 'Точка M — середина ребра SC.' if p == q else f'Точка M лежит на ребре SC, причём SM : MC = {ratio_txt(p, q)}.'

    def build(sq, Q):
        S_ = mk_pyr4(a, sq(Q(h2.numerator) / Q(h2.denominator)), sq, Q)
        M = lerp(S_.pts['S'], S_.pts['C'], Q(p) / (p + q))
        return S_, {'M': M}
    text = pick(r, f'Дана правильная четырёхугольная пирамида SABCD, у которой AB = {a}, SA = {l}.',
                f'В правильной четырёхугольной пирамиде SABCD ребро основания AB равно {a}, боковое ребро SA равно {l}.',
                f'Сторона основания правильной четырёхугольной пирамиды SABCD равна {a}, её боковые рёбра равны {l}.') + ' ' + mdesc
    a_st = 'Докажите, что плоскость BDM перпендикулярна плоскости SAC.'

    def a_chk(P):
        n1 = v_cross(v_sub(P['D'], P['B']), v_sub(P['M'], P['B']))
        n2 = v_cross(v_sub(P['A'], P['S']), v_sub(P['C'], P['S']))
        return sp.simplify(v_dot(n1, n2)) == 0
    Q_ = [('dpp', 'A', 'BDM'), ('dpp', 'C', 'BDM'), ('dpp', 'S', 'BDM'), ('app', 'BDM', 'ABC'), ('alp', 'AM', 'ABC'),
          ('sec', 'BDM'), ('vol', 'MBCD'), ('dpl', 'M', 'BD'), ('all', 'AM', 'BD'), ('dll', 'BD', 'SC')]
    return dict(build=build, text=text, a=a_st, a_chk=a_chk, queries=Q_, name='пирамиды', show='SABCDM')


def sc_pyr4_mk(r):
    a = r.choice([2, 4, 6, 8, 12, 16])
    l = r.randint(a // 2 + 1, a + 6)
    h2 = F(l * l) - F(a * a, 2)
    if h2 <= 0:
        return None

    def build(sq, Q):
        S_ = mk_pyr4(a, sq(Q(h2.numerator) / Q(h2.denominator)), sq, Q)
        M = lerp(S_.pts['A'], S_.pts['B'], Q(1) / 2)
        K = lerp(S_.pts['S'], S_.pts['D'], Q(1) / 2)
        return S_, {'M': M, 'K': K}
    text = pick(r, f'В правильной четырёхугольной пирамиде SABCD сторона основания AB = {a}, боковое ребро SA = {l}. '
                   f'Точки M и K — середины рёбер AB и SD соответственно.',
                f'Дана правильная четырёхугольная пирамида SABCD с основанием ABCD; AB = {a}, SA = {l}. M — середина AB, '
                f'K — середина SD.')
    a_st = 'Докажите, что прямая MK параллельна плоскости SBC.'

    def a_chk(P):
        n = v_cross(v_sub(P['B'], P['S']), v_sub(P['C'], P['S']))
        return sp.simplify(v_dot(n, v_sub(P['K'], P['M']))) == 0
    Q_ = [('alp', 'MK', 'ABC'), ('dpl', 'K', 'AB'), ('all', 'MK', 'SA'), ('dpp', 'M', 'SBC'), ('sec', 'MKC'),
          ('seg', 'MK')]
    return dict(build=build, text=text, a=a_st, a_chk=a_chk, queries=Q_, name='пирамиды', show='SABCDMK')


def sc_pyr3(r):
    a = r.choice([3, 6, 9, 12, 2, 4])
    l = r.randint(a // 2 + 1, a + 6)
    h2 = F(l * l) - F(a * a, 3)
    if h2 <= 0:
        return None
    p, q = r.choice([(1, 1), (1, 2), (2, 1), (1, 1)])

    def build(sq, Q):
        S_ = mk_pyr3(a, sq(Q(h2.numerator) / Q(h2.denominator)), sq, Q)
        M = lerp(S_.pts['A'], S_.pts['B'], Q(1) / 2)
        K = lerp(S_.pts['S'], S_.pts['C'], Q(p) / (p + q))
        return S_, {'M': M, 'K': K}
    kd = 'K — середина ребра SC' if p == q else f'точка K на ребре SC делит его в отношении SK : KC = {ratio_txt(p, q)}'
    text = pick(r, f'В правильной треугольной пирамиде SABC сторона основания равна {a}, а боковое ребро — {l}. '
                   f'Точка M — середина ребра AB, {kd}.',
                f'Дана правильная треугольная пирамида SABC: AB = {a}, SA = {l}. M — середина AB, {kd}.')
    a_st = 'Докажите, что прямые SC и AB перпендикулярны.'

    def a_chk(P):
        return sp.simplify(v_dot(v_sub(P['C'], P['S']), v_sub(P['B'], P['A']))) == 0
    Q_ = [('dll', 'SC', 'AB'), ('alp', 'SC', 'ABC'), ('app', 'SAB', 'ABC'), ('dpp', 'C', 'SAB'), ('sec', 'ABK'),
          ('alp', 'MK', 'ABC'), ('dpp', 'A', 'SBC'), ('vol', 'KABC')]
    return dict(build=build, text=text, a=a_st, a_chk=a_chk, queries=Q_, name='пирамиды', show='SABCMK')


def sc_prism3(r):
    a = r.choice([2, 4, 6, 8, 12])
    h = r.choice([1, 2, 3, 4, 5, 6, 8])

    def build(sq, Q):
        S_ = mk_prism3(a, h, sq, Q)
        M = lerp(S_.pts['A1'], S_.pts['B1'], Q(1) / 2)
        return S_, {'M': M}
    text = pick(r, f'В правильной треугольной призме ABCA₁B₁C₁ сторона основания AB = {a}, а боковое ребро AA₁ = {h}. '
                   f'Точка M — середина ребра A₁B₁.',
                f'Дана правильная треугольная призма ABCA₁B₁C₁, у которой AB = {a}, AA₁ = {h}; M — середина A₁B₁.')
    a_st = 'Докажите, что прямые CM и AB перпендикулярны.'

    def a_chk(P):
        return sp.simplify(v_dot(v_sub(P['M'], P['C']), v_sub(P['B'], P['A']))) == 0
    Q_ = [('dpp', 'B', 'ACM'), ('app', 'ABC1', 'ABC'), ('alp', 'CM', 'ABB1'), ('sec', 'ABC1'), ('dll', 'AB', 'CM'),
          ('all', 'AM', 'BC1'), ('dpl', 'C', 'AM'), ('vol', 'MABC')]
    return dict(build=build, text=text, a=a_st, a_chk=a_chk, queries=Q_, name='призмы', show=['A', 'B', 'C', 'A1', 'B1', 'C1', 'M'])


def sc_tet(r):
    a = r.choice([2, 3, 4, 6, 8, 12])

    def build(sq, Q):
        s3, s6 = sq(3), sq(6)
        P = {'A': (Q(0), Q(0), Q(0)), 'B': (Q(a), Q(0), Q(0)), 'C': (Q(a) / 2, Q(a) * s3 / 2, Q(0)),
             'D': (Q(a) / 2, Q(a) * s3 / 6, Q(a) * s6 / 3)}
        S_ = Solid(P, [('A', 'B'), ('B', 'C'), ('C', 'A'), ('D', 'A'), ('D', 'B'), ('D', 'C')],
                   ['ABC', 'DAB', 'DBC', 'DCA'], 'tet')
        return S_, {'M': lerp(P['A'], P['B'], Q(1) / 2), 'N': lerp(P['C'], P['D'], Q(1) / 2)}
    text = pick(r, f'Ребро правильного тетраэдра ABCD равно {a}. Точки M и N — середины рёбер AB и CD соответственно.',
                f'Дан правильный тетраэдр ABCD с ребром {a}; M — середина AB, N — середина CD.')
    a_st = 'Докажите, что отрезок MN — общий перпендикуляр прямых AB и CD.'

    def a_chk(P):
        u = v_sub(P['N'], P['M'])
        return sp.simplify(v_dot(u, v_sub(P['B'], P['A']))) == 0 and sp.simplify(v_dot(u, v_sub(P['D'], P['C']))) == 0
    Q_ = [('seg', 'MN'), ('alp', 'CM', 'ABD'), ('dpp', 'D', 'ABC'), ('app', 'DAB', 'ABC'), ('sec', 'CDM'),
          ('all', 'CM', 'AD'), ('dpl', 'D', 'CM')]
    return dict(build=build, text=text, a=a_st, a_chk=a_chk, queries=Q_, name='тетраэдра', show='ABCDMN')


def sc_trirect(r):
    p, q, r_ = r.choice([2, 3, 4, 6, 8, 12]), r.choice([3, 4, 6, 8, 12]), r.choice([3, 4, 6, 8, 12, 5])
    eq_ = r.random() < 0.35
    if eq_:
        q = r_ = p
    mm, nn = r.choice([(1, 1), (1, 2), (2, 1), (1, 3)])

    def build(sq, Q):
        S_ = mk_tri_rect(p, q, r_, sq, Q)
        return S_, {'M': lerp(S_.pts['D'], S_.pts['A'], Q(mm) / (mm + nn))}
    md = 'M — середина ребра DA' if mm == nn else f'точка M делит ребро DA в отношении DM : MA = {ratio_txt(mm, nn)}'
    text = pick(r, f'В треугольной пирамиде DABC рёбра DA, DB и DC попарно перпендикулярны, DA = {p}, DB = {q}, DC = {r_}; {md}.',
                (f'Рёбра DA, DB, DC пирамиды DABC попарно перпендикулярны и равны {p}; {md}.' if eq_ else
                 f'Рёбра DA, DB, DC пирамиды DABC попарно перпендикулярны и равны {p}, {q} и {r_} соответственно; {md}.'))
    a_st = 'Докажите, что прямые DA и BC перпендикулярны.'

    def a_chk(P):
        return sp.simplify(v_dot(v_sub(P['A'], P['D']), v_sub(P['C'], P['B']))) == 0
    Q_ = [('dpp', 'D', 'ABC'), ('dpp', 'D', 'MBC'), ('app', 'MBC', 'DBC'), ('sec', 'MBC'), ('dll', 'DA', 'BC'),
          ('alp', 'AB', 'DBC'), ('app', 'ABC', 'DBC')]
    return dict(build=build, text=text, a=a_st, a_chk=a_chk, queries=Q_, name='пирамиды', show='DABCM')


def sc_cube(r):
    a = r.choice([2, 3, 4, 6, 8, 12])
    mode = r.choice(['diag', 'mid'])

    def build(sq, Q):
        S_ = mk_box(a, a, a, sq, Q)
        P = S_.pts
        return S_, {'M': lerp(P['A'], P['B'], Q(1) / 2), 'N': lerp(P['A'], P['D'], Q(1) / 2)}
    if mode == 'diag':
        text = pick(r, f'Дан куб ABCDA₁B₁C₁D₁ с ребром {a}.', f'Ребро куба ABCDA₁B₁C₁D₁ равно {a}.')
        a_st = 'Докажите, что прямая AC₁ перпендикулярна плоскости A₁BD.'

        def a_chk(P):
            u = v_sub(P['C1'], P['A'])
            return all(sp.simplify(v_dot(u, v_sub(P[x], P['B']))) == 0 for x in ('A1', 'D'))
        Q_ = [('dpp', 'A', 'A1BD'), ('dpp', 'C1', 'A1BD'), ('sec', 'A1BD'), ('alp', 'AC1', 'ABC'), ('dll', 'AC1', 'BD'),
              ('all', 'A1B', 'AD1'), ('dpl', 'A', 'BD1')]
    else:
        text = pick(r, f'Дан куб ABCDA₁B₁C₁D₁ с ребром {a}; M и N — середины рёбер AB и AD.',
                    f'Ребро куба ABCDA₁B₁C₁D₁ равно {a}. Точки M и N — середины рёбер AB и AD соответственно.')
        a_st = 'Докажите, что прямые B₁N и CM перпендикулярны.'

        def a_chk(P):
            return sp.simplify(v_dot(v_sub(P['N'], P['B1']), v_sub(P['M'], P['C']))) == 0
        Q_ = [('dpp', 'C', 'MNC1'), ('sec', 'MNC1'), ('app', 'MNC1', 'ABC'), ('dpp', 'A', 'MNC1'), ('alp', 'B1N', 'ABC'),
              ('dpl', 'C', 'B1N')]
    return dict(build=build, text=text, a=a_st, a_chk=a_chk, queries=Q_, name='куба',
                show=['A', 'B', 'C', 'D', 'A1', 'B1', 'C1', 'D1'] + (['M', 'N'] if mode == 'mid' else []))


def sc_box(r):
    a, b, c = r.sample([2, 3, 4, 5, 6, 8, 9, 12, 15, 16], 3)

    def build(sq, Q):
        S_ = mk_box(a, b, c, sq, Q)
        return S_, {'K': lerp(S_.pts['C'], S_.pts['C1'], Q(1) / 2)}
    text = pick(r, f'В прямоугольном параллелепипеде ABCDA₁B₁C₁D₁ известно, что AB = {a}, AD = {b}, AA₁ = {c}.',
                f'Рёбра прямоугольного параллелепипеда ABCDA₁B₁C₁D₁ таковы: AB = {a}, BC = {b}, AA₁ = {c}.')
    a_st = 'Докажите, что плоскости ABC₁ и BCC₁ перпендикулярны.'

    def a_chk(P):
        n1 = v_cross(v_sub(P['B'], P['A']), v_sub(P['C1'], P['A']))
        n2 = v_cross(v_sub(P['C'], P['B']), v_sub(P['C1'], P['B']))
        return sp.simplify(v_dot(n1, n2)) == 0
    Q_ = [('app', 'ABC1', 'ABC'), ('dpp', 'C', 'ABC1'), ('sec', 'ABC1'), ('alp', 'AC1', 'BCC1'), ('dpp', 'B', 'ACC1'),
          ('all', 'AC1', 'BD'), ('dll', 'AA1', 'BD')]
    return dict(build=build, text=text, a=a_st, a_chk=a_chk, queries=Q_, name='параллелепипеда',
                show=['A', 'B', 'C', 'D', 'A1', 'B1', 'C1', 'D1'])


def sc_pyr6(r):
    a = r.choice([2, 4, 6, 8, 12])
    l = r.randint(a + 1, 2 * a + 6)

    def build(sq, Q):
        S_ = mk_pyr6(a, sq(Q(l * l - a * a)), sq, Q)
        P = S_.pts
        return S_, {'M': lerp(P['S'], P['B'], Q(1) / 2), 'K': lerp(P['S'], P['E'], Q(1) / 2)}
    text = pick(r, f'Основание пирамиды SABCDEF — правильный шестиугольник со стороной {a}, все боковые рёбра пирамиды '
                   f'равны {l}. На рёбрах SB и SE взяты их середины M и K.',
                f'У правильной шестиугольной пирамиды SABCDEF ребро основания равно {a}, а боковое — {l}; '
                f'точка M — середина SB, точка K — середина SE.')
    a_st = 'Докажите, что прямая MK параллельна прямой CD.'

    def a_chk(P):
        c = v_cross(v_sub(P['D'], P['C']), v_sub(P['K'], P['M']))
        return all(sp.simplify(x) == 0 for x in c)
    Q_ = [('vol', 'MBCD'), ('app', 'SCD', 'ABC'), ('dpp', 'A', 'SBC'), ('alp', 'SB', 'ABC'), ('seg', 'MK'),
          ('sec', 'MKC'), ('dpp', 'S', 'MKC')]
    return dict(build=build, text=text, a=a_st, a_chk=a_chk, queries=Q_, name='пирамиды', show='SABCDEFMK')


SCEN15 = [sc_pyr4_m, sc_pyr4_mk, sc_pyr3, sc_prism3, sc_tet, sc_trirect, sc_cube, sc_box, sc_pyr6]


def plane_pts(sp_str):
    """'BDM' → ['B', 'D', 'M']; 'ABC1' → ['A', 'B', 'C1']; 'A1BD' → ['A1', 'B', 'D']."""
    out = []
    for ch in sp_str:
        if ch == '1':
            out[-1] += '1'
        else:
            out.append(ch)
    return out


def section(P, solid, pl, eps=1e-9, exact=False):
    """Точки сечения многогранника плоскостью (три точки pl): пересечения с рёбрами, без повторов."""
    A, B, C = (P[n] for n in pl)
    n = v_cross(v_sub(B, A), v_sub(C, A))
    d = v_dot(n, A)
    pts = []
    for u, w in solid.edges:
        U, Wp = P[u], P[w]
        fu, fw = v_dot(n, U) - d, v_dot(n, Wp) - d
        if exact:
            fu, fw = sp.simplify(fu), sp.simplify(fw)
            su, sw = sp.sign(sp.N(fu, 30)) if fu != 0 else 0, sp.sign(sp.N(fw, 30)) if fw != 0 else 0
        else:
            su = 0 if abs(fu) < eps else (1 if fu > 0 else -1)
            sw = 0 if abs(fw) < eps else (1 if fw > 0 else -1)
        if su == 0:
            pts.append(U)
        if sw == 0:
            pts.append(Wp)
        if su * sw < 0:
            t = fu / (fu - fw)
            pts.append(lerp(U, Wp, t))
    uniq_ = []
    for p in pts:
        if all(sum(abs(float(x) - float(y)) for x, y in zip(p, q)) > 1e-7 for q in uniq_):
            uniq_.append(p)
    return uniq_, n


def poly_area(pts, n, sq=math.sqrt):
    """Площадь выпуклого многоугольника в пространстве: упорядочиваем по углу и складываем векторные произведения."""
    cx = [sum(float(p[i]) for p in pts) / len(pts) for i in range(3)]
    nf = [float(x) for x in n]
    ref = [float(x) - c for x, c in zip(pts[0], cx)]
    ax2 = v_cross(nf, ref)

    def ang(p):
        v = [float(x) - c for x, c in zip(p, cx)]
        return math.atan2(v_dot(v, ax2), v_dot(v, ref))
    ordered = sorted(pts, key=ang)
    tot = (0, 0, 0)
    for i in range(len(ordered)):
        tot = v_add(tot, v_cross(ordered[i], ordered[(i + 1) % len(ordered)]))
    return v_len(tot, sq) / 2


def names_of(s_):
    return plane_pts(s_)


def q_text(kind, a1, a2, sc):
    L = lambda s_: ''.join(lab(x) for x in names_of(s_))
    if kind == 'dpp':
        return f'Найдите расстояние от точки {lab(a1)} до плоскости {L(a2)}.'
    if kind == 'dpl':
        return f'Найдите расстояние от точки {lab(a1)} до прямой {L(a2)}.'
    if kind == 'dll':
        return f'Найдите расстояние между прямыми {L(a1)} и {L(a2)}.'
    if kind == 'seg':
        return f'Найдите длину отрезка {L(a1)}.'
    if kind == 'alp':
        return f'Найдите угол между прямой {L(a1)} и плоскостью {L(a2)}.'
    if kind == 'app':
        return f'Найдите угол между плоскостями {L(a1)} и {L(a2)}.'
    if kind == 'all':
        return f'Найдите угол между прямыми {L(a1)} и {L(a2)}.'
    if kind == 'sec':
        return f'Найдите площадь сечения {sc["name"]} плоскостью {L(a1)}.'
    if kind == 'vol':
        return f'Найдите объём пирамиды {L(a1)}.'
    raise ValueError(kind)


def q_float(kind, P, S_, a1, a2):
    """Значение (float) или (sin, cos, tan) для углов — генератор."""
    g = lambda n: P[n]
    if kind == 'dpp':
        Y, Z, W = (g(n) for n in names_of(a2))
        n = v_cross(v_sub(Z, Y), v_sub(W, Y))
        return abs(v_dot(n, v_sub(g(a1), Y))) / v_len(n)
    if kind == 'dpl':
        Y, Z = (g(n) for n in names_of(a2))
        return v_len(v_cross(v_sub(g(a1), Y), v_sub(Z, Y))) / v_len(v_sub(Z, Y))
    if kind == 'dll':
        A, B = (g(n) for n in names_of(a1))
        C, D = (g(n) for n in names_of(a2))
        w = v_cross(v_sub(B, A), v_sub(D, C))
        if v_len(w) < 1e-12:
            return None
        return abs(v_dot(v_sub(C, A), w)) / v_len(w)
    if kind == 'seg':
        A, B = (g(n) for n in names_of(a1))
        return v_len(v_sub(B, A))
    if kind in ('alp', 'app', 'all'):
        if kind == 'alp':
            A, B = (g(n) for n in names_of(a1))
            u = v_sub(B, A)
            X_, Y__, Z_ = (g(n) for n in names_of(a2))
            n = v_cross(v_sub(Y__, X_), v_sub(Z_, X_))
            s = abs(v_dot(u, n)) / (v_len(u) * v_len(n))
            c = math.sqrt(max(0.0, 1 - s * s))
        else:
            if kind == 'app':
                p1 = [g(n) for n in names_of(a1)]
                p2 = [g(n) for n in names_of(a2)]
                u = v_cross(v_sub(p1[1], p1[0]), v_sub(p1[2], p1[0]))
                v = v_cross(v_sub(p2[1], p2[0]), v_sub(p2[2], p2[0]))
            else:
                A, B = (g(n) for n in names_of(a1))
                C, D = (g(n) for n in names_of(a2))
                u, v = v_sub(B, A), v_sub(D, C)
            c = abs(v_dot(u, v)) / (v_len(u) * v_len(v))
            s = math.sqrt(max(0.0, 1 - c * c))
        return (s, c, s / c if c > 1e-12 else None)
    if kind == 'sec':
        pts, n = section(P, S_, names_of(a1))
        if len(pts) < 3:
            return None
        return poly_area(pts, n)
    if kind == 'vol':
        X_, Y__, Z_, W = (g(n) for n in names_of(a1))
        return abs(v_dot(v_sub(Y__, X_), v_cross(v_sub(Z_, X_), v_sub(W, X_)))) / 6
    raise ValueError(kind)


def q_exact(kind, P, S_, a1, a2):
    """Точное значение (sympy) другим способом — для проверки. Для углов → (sin, cos)."""
    g = lambda n: P[n]
    sq = sp.sqrt

    def tri_area(A, B, C):
        return sq(v_dot(v_cross(v_sub(B, A), v_sub(C, A)), v_cross(v_sub(B, A), v_sub(C, A)))) / 2

    def dist_pp(X_, pl):
        Y, Z, W = pl
        V = abs(v_dot(v_sub(Y, X_), v_cross(v_sub(Z, X_), v_sub(W, X_)))) / 6
        return 3 * V / tri_area(Y, Z, W)

    def signed_pp(X_, pl):
        Y, Z, W = pl
        V = v_dot(v_sub(Y, X_), v_cross(v_sub(Z, X_), v_sub(W, X_))) / 6
        return 3 * V / tri_area(Y, Z, W)
    if kind == 'dpp':
        return dist_pp(g(a1), [g(n) for n in names_of(a2)])
    if kind == 'dpl':
        Y, Z = (g(n) for n in names_of(a2))
        u = v_sub(Z, Y)
        t = v_dot(v_sub(g(a1), Y), u) / v_dot(u, u)
        Fp = v_add(Y, v_mul(u, t))
        return sq(v_dot(v_sub(g(a1), Fp), v_sub(g(a1), Fp)))
    if kind == 'dll':
        A, B = (g(n) for n in names_of(a1))
        C, D = (g(n) for n in names_of(a2))
        s_, t_ = sp.symbols('s t')
        Pp = v_add(A, v_mul(v_sub(B, A), s_))
        Qp = v_add(C, v_mul(v_sub(D, C), t_))
        w = v_sub(Pp, Qp)
        sol = sp.solve([v_dot(w, v_sub(B, A)), v_dot(w, v_sub(D, C))], [s_, t_], dict=True)[0]
        ww = [sp.simplify(x.subs(sol)) for x in w]
        return sq(v_dot(ww, ww))
    if kind == 'seg':
        A, B = (g(n) for n in names_of(a1))
        return sq(sum((x - y) ** 2 for x, y in zip(A, B)))
    if kind == 'alp':
        A, B = (g(n) for n in names_of(a1))
        pl = [g(n) for n in names_of(a2)]
        s = abs(signed_pp(A, pl) - signed_pp(B, pl)) / sq(v_dot(v_sub(B, A), v_sub(B, A)))
        return s, sq(1 - s * s)
    if kind == 'app':
        def normal(pts):
            a, b, c = sp.symbols('na nb nc')
            eqs = [a * (p[0] - pts[0][0]) + b * (p[1] - pts[0][1]) + c * (p[2] - pts[0][2]) for p in pts[1:]]
            for fix in ((a, 1), (b, 1), (c, 1)):
                sol = sp.solve(eqs + [fix[0] - fix[1]], [a, b, c], dict=True)
                if sol:
                    return [sol[0][a], sol[0][b], sol[0][c]]
            raise ValueError
        u = normal([g(n) for n in names_of(a1)])
        v = normal([g(n) for n in names_of(a2)])
        c = abs(v_dot(u, v)) / (sq(v_dot(u, u)) * sq(v_dot(v, v)))
        return sq(1 - c * c), c
    if kind == 'all':
        A, B = (g(n) for n in names_of(a1))
        C, D = (g(n) for n in names_of(a2))
        u, v = v_sub(B, A), v_sub(D, C)
        lu, lv, lw = v_dot(u, u), v_dot(v, v), v_dot(v_sub(u, v), v_sub(u, v))
        c = abs((lu + lv - lw) / (2 * sq(lu) * sq(lv)))
        return sq(1 - c * c), c
    if kind == 'sec':
        pts, n = section(P, S_, names_of(a1), exact=True)
        # площадь веером треугольников от первой точки (после упорядочения по углу)
        cx = [sum(float(sp.N(p[i])) for p in pts) / len(pts) for i in range(3)]
        nf = [float(sp.N(x)) for x in n]
        ref = [float(sp.N(x)) - c for x, c in zip(pts[0], cx)]
        ax2 = v_cross(nf, ref)
        ordered = sorted(pts, key=lambda p: math.atan2(v_dot([float(sp.N(x)) - c for x, c in zip(p, cx)], ax2),
                                                        v_dot([float(sp.N(x)) - c for x, c in zip(p, cx)], ref)))
        return sum(tri_area(ordered[0], ordered[i], ordered[i + 1]) for i in range(1, len(ordered) - 1))
    if kind == 'vol':
        X_, Y__, Z_, W = (g(n) for n in names_of(a1))
        return tri_area(Y__, Z_, W) * dist_pp(X_, [Y__, Z_, W]) / 3
    raise ValueError(kind)


ANGLE_K = ('alp', 'app', 'all')


def gen15(r, kinds):
    """Общий генератор №15: сценарий с верным пунктом а + вопрос б из заданных видов."""
    sc = r.choice(SCEN15)(r)
    if not sc:
        return None
    opts = [qq for qq in sc['queries'] if qq[0] in kinds]
    if not opts:
        return None
    kind, a1, *rest = r.choice(opts)
    a2 = rest[0] if rest else None
    S_, extra = sc['build'](math.sqrt, float)
    P = dict(S_.pts)
    P.update(extra)
    val = q_float(kind, P, S_, a1, a2)
    if val is None:
        return None
    if kind in ANGLE_K and abs(val[1]) < 1e-9:
        return None                     # прямой угол следует из пункта а сразу — в банке так не спрашивают
    rep = pick_repr(r, val, 'ang' if kind in ANGLE_K else 'len')
    if not rep:
        return None
    ans, how = rep
    if how in ('sq', 'tg2', 'cos2', 'sin2') and r.random() < 0.5:
        return None                     # чаще берём конфигурации с «хорошим» ответом, как в банке
    if how == 'sq' and ans > 1000:
        return None
    q = f'{sc["text"]}\nа) {sc["a"]}\nб) {q_text(kind, a1, a2, sc)}\n{ASK15[how]}'
    segs = []
    for nm in (a1, a2):
        if not nm:
            continue
        pts_ = names_of(nm)
        if len(pts_) >= 2 and kind != 'dpp' or nm == a2 and kind == 'dpp':
            segs += [(pts_[i], pts_[(i + 1) % len(pts_)]) for i in range(len(pts_) if len(pts_) > 2 else 1)]
    svg = proj_svg(S_, [lab(n) for n in (list(sc['show']) if not isinstance(sc['show'], list) else sc['show'])],
                   extra_pts=extra, segs=segs)
    e = f'б) Метод координат (или построение): искомая величина {"" if how in ("", "deg") else "(" + ASK15[how].split("запишите ")[1].rstrip(".") + ") "}равна {tnum(ans)}.'

    def chk():
        Se, ex = sc['build'](sp.sqrt, sp.Integer)
        Pe = dict(Se.pts)
        Pe.update(ex)
        if not sc['a_chk'](Pe):
            return False
        v = q_exact(kind, Pe, Se, a1, a2)
        if kind in ANGLE_K:
            s_, c_ = v
            if how == 'deg':
                return abs(math.degrees(math.atan2(float(sp.N(s_)), float(sp.N(c_)))) - float(ans)) < 1e-7
            return same(num(ans), ang_value(how, s_, c_))
        return same(num(ans), v * v if how == 'sq' else v)
    return pcard(q, num(ans), e, svg=svg), chk


KES15 = ['7.2', '7.3']
M15 = ['ошибка в координатах точек правильной пирамиды/призмы', 'путают расстояние до плоскости и до прямой',
       'находят не тот угол (например, с ребром вместо проекции)']


def reg15(pid, title, kinds, inv, ans_rule, fipi, extra_m=()):
    def fn(r):
        return gen15(r, kinds)
    fn.__name__ = 'gen_' + pid.replace('-', '_')
    proto(pid, 'ege-prof', 15, title, invariant=inv,
          varies='Многогранник (куб, параллелепипед, правильные призма и пирамиды, тетраэдр, прямоугольный тетраэдр), '
                 'размеры, положение точек на рёбрах, какая величина спрашивается; сюжет пункта а соответствует фигуре.',
          answer_rule=ans_rule, fipi=fipi, mistakes=list(extra_m) + M15, svg=True,
          kim=kim(K15, 'Как в КИМ: описание многогранника с числами, «а) Докажите, что …», «б) Найдите …»; '
                       'итог пункта б — число (при иррациональном ответе — квадрат величины или тригонометрическая функция угла).'))(fn)
    return fn


reg15('ep15-dist-plane', 'Расстояние от точки до плоскости', ('dpp',),
      'Расстояние от точки до плоскости: через объём тетраэдра (d = 3V/S), через перпендикуляр к плоскости или координатами.',
      'd = |n·(X − A)|/|n| или 3V/S; итог — d (или d²).', r'Найдите расстояние от (точки|вершины) .{1,12} до плоскости')
reg15('ep15-dist-line', 'Расстояние от точки до прямой и между скрещивающимися прямыми', ('dpl', 'dll', 'seg'),
      'Расстояние до прямой — высота треугольника; между скрещивающимися прямыми — общий перпендикуляр или '
      'расстояние от прямой до параллельной ей плоскости.',
      'd = |AX × AB|/|AB| или |(C − A)·(u × v)|/|u × v|; итог — d (или d²).',
      r'Найдите расстояние (от (точки|вершины) .{1,12} до прямой|между прямыми)|Найдите длину отрезка')
reg15('ep15-angle-lp', 'Угол между прямой и плоскостью', ('alp',),
      'Угол между прямой и её проекцией на плоскость: sin φ = расстояние от точки прямой до плоскости / длина отрезка.',
      'sin φ = |u·n|/(|u||n|); итог — тригонометрическая функция угла или градусы.', r'угол между прямой .{1,12} и плоскостью')
reg15('ep15-angle-pp', 'Угол между плоскостями', ('app',),
      'Двугранный угол: линейный угол (перпендикуляры к линии пересечения) или угол между нормалями.',
      'cos φ = |n₁·n₂|/(|n₁||n₂|); итог — тригонометрическая функция угла или градусы.',
      r'Найдите (косинус |тангенс )?угл[а-я]* между плоскост|угол между плоскостями')
reg15('ep15-angle-ll', 'Угол между скрещивающимися прямыми', ('all',),
      'Параллельный перенос одной прямой до пересечения с другой, теорема косинусов (или векторы направлений).',
      'cos φ = |u·v|/(|u||v|); итог — тригонометрическая функция угла или градусы.', r'угол между прямыми')
reg15('ep15-section', 'Площадь сечения многогранника плоскостью', ('sec',),
      'Строим сечение по трём точкам (следы на гранях, параллельность), определяем вид многоугольника и находим площадь.',
      'Площадь многоугольника сечения (по сторонам и высотам или через проекцию S = S_пр / cos φ).',
      r'площадь сечения')
reg15('ep15-volume', 'Объём пирамиды с вершинами в точках многогранника', ('vol',),
      'V = S·h/3: основание и высота выбираются удобно (часто высота — половина высоты пирамиды для середины ребра).',
      'V = |det|/6 или S·h/3; итог — объём (или его квадрат).', r'Найдите объём|отношение объёмов|объёмы которых')


@proto('ep15-cylinder', 'ege-prof', 15, 'Цилиндр: точки на окружностях оснований, отрезок через ось',
       invariant='Если отрезок AC₁ пересекает ось, то A и проекция C точки C₁ диаметрально противоположны; вписанный '
                 'угол ABC прямой, BB₁ ⟂ основанию, поэтому угол ABC₁ прямой; диаметр² = AB² + BC², BC = B₁C₁.',
       varies='Длины AB, BB₁, B₁C₁ (тройки чисел), спрашиваемая величина: объём, площадь боковой поверхности, '
              'расстояние от B до AC₁, угол между BB₁ и AC₁.',
       answer_rule='R = √(AB² + B₁C₁²)/2, H = BB₁; V = πR²H, S = 2πRH (в ответ — V/π или S/π); d = AB·BC₁/AC₁.',
       fipi=r'В цилиндре образующая перпендикулярна плоскости основания|отношение их объёмов',
       mistakes=['берут AB за диаметр', 'забывают деление на π в ответе', 'путают BC₁ и B₁C₁'],
       svg=True,
       kim=kim(K15, 'Как в КИМ: «В цилиндре образующая перпендикулярна плоскости основания… а) Докажите, что угол ABC₁ '
                    'прямой. б) Найдите …»; итог — число (для объёма и площади — делённое на π).', kes=['7.4', '7.2']))
def gen_ep15_cylinder(r):
    trip = [(3, 4, 5), (6, 8, 10), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (12, 16, 20), (9, 12, 15)]
    ab, bc, dia = r.choice(trip)
    if r.random() < 0.5:
        ab, bc = bc, ab
    H = r.choice([2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 20, 24])
    ask = r.choice(['V', 'S', 'd', 'tg'])
    R_ = F(dia, 2)
    if ask == 'V':
        val = R_ * R_ * H
        qtxt, ins = 'Найдите объём цилиндра.', 'В ответ запишите объём, делённый на π.'
    elif ask == 'S':
        val = 2 * R_ * H
        qtxt, ins = 'Найдите площадь боковой поверхности цилиндра.', 'В ответ запишите площадь, делённую на π.'
    elif ask == 'd':
        bc1 = math.sqrt(bc * bc + H * H)
        v = ab * bc1 / math.sqrt(ab * ab + bc1 * bc1)
        val = fnice(v)
        how = ''
        if val is None:
            val = fnice(v * v)
            how = 'sq'
        if val is None:
            return None
        qtxt = 'Найдите расстояние от точки B до прямой AC₁.'
        ins = ASK15[how]
    else:
        val = F(dia, H)
        if not nice(val, 2):
            return None
        qtxt, ins = 'Найдите угол между прямыми BB₁ и AC₁.', 'В ответ запишите тангенс найденного угла.'
    if not nice(val, 2):
        return None
    head = pick(r, 'Образующая цилиндра перпендикулярна плоскости его основания. На окружности нижнего основания отмечены '
                   'точки A и B, на окружности верхнего — точки B₁ и C₁, причём BB₁ — образующая, а отрезок AC₁ '
                   'пересекает ось цилиндра.',
                'Точки A и B лежат на окружности одного основания прямого кругового цилиндра, точки B₁ и C₁ — на окружности '
                'другого основания; BB₁ — образующая цилиндра, отрезок AC₁ проходит через точку на оси цилиндра.')
    head += f' Известно, что AB = {ab}, BB₁ = {H}, B₁C₁ = {bc}.'
    q = f'{head}\nа) Докажите, что угол ABC₁ прямой.\nб) {qtxt}\n{ins}'
    # чертёж: окружности-эллипсы заменяем многоугольниками
    k = 0.35
    pts = {}
    ang_a = math.pi * 0.9
    Ax, Ay = R_ * math.cos(ang_a), R_ * math.sin(ang_a)
    Cx, Cy = -Ax, -Ay
    # B на окружности с AB = ab: угол между A и B
    th = 2 * math.asin(ab / float(dia))
    Bx, By = float(R_) * math.cos(ang_a + th), float(R_) * math.sin(ang_a + th)
    pr = lambda x, y, z: (float(x), float(y) * k + float(z))
    pts['A'], pts['B'], pts['C'] = pr(Ax, Ay, 0), pr(Bx, By, 0), pr(Cx, Cy, 0)
    pts['B₁'], pts['C₁'] = pr(Bx, By, H * 0.6), pr(Cx, Cy, H * 0.6)
    ring = [pr(float(R_) * math.cos(2 * math.pi * i / 24), float(R_) * math.sin(2 * math.pi * i / 24), 0) for i in range(24)]
    ring2 = [(x, y + H * 0.6) for x, y in ring]
    for i, p_ in enumerate(ring + ring2):
        pts[chr(0xE100 + i)] = p_
    segs = [chr(0xE100 + i) + chr(0xE100 + (i + 1) % 24) for i in range(24)] + \
           [chr(0xE100 + 24 + i) + chr(0xE100 + 24 + (i + 1) % 24) for i in range(24)]
    segs += ['AB', 'BB₁'.replace('B₁', chr(0xE200)), ]
    pts[chr(0xE200)] = pts.pop('B₁')
    pts[chr(0xE201)] = pts.pop('C₁')
    segs = segs[:-1] + ['B' + chr(0xE200), chr(0xE200) + chr(0xE201), 'A' + chr(0xE201)]
    svg = svg_geom(pts, segs=segs, labels=['A', 'B', chr(0xE200), chr(0xE201)], width=260)
    svg = svg.replace(f'>{chr(0xE200)}<', '>B₁<').replace(f'>{chr(0xE201)}<', '>C₁<')
    e = (f'∠ABC = 90° (опирается на диаметр AC), BB₁ ⟂ BC… AC = √({ab}² + {bc}²) = {dia}, R = {fr(R_)}, H = {H}; '
         f'ответ {tnum(val)}.')

    def chk():
        # координаты: A и C диаметрально противоположны; B на окружности; проверяем через векторы
        Rr = R_
        Ap = sp.Matrix([-Rr, 0, 0])
        Cp = sp.Matrix([Rr, 0, 0])
        # B: |AB| = ab, на окружности x² + y² = R²
        bx = sp.Rational(ab * ab, 2 * 1) / (2 * Rr) - Rr   # из |B − A|² = ab²: 2R(bx + R) = ab²
        bx = sp.Rational(ab * ab) / (2 * R(Rr)) - R(Rr)
        by = sp.sqrt(R(Rr) ** 2 - bx ** 2)
        Bp = sp.Matrix([bx, by, 0])
        B1 = Bp + sp.Matrix([0, 0, H])
        C1 = Cp + sp.Matrix([0, 0, H])
        if sp.simplify((B1 - C1).norm() - bc) != 0:
            return False
        if sp.simplify((Ap - Bp).dot(C1 - Bp)) != 0:       # пункт а
            return False
        if ask == 'V':
            return same(num(val), (Cp - Ap).norm() ** 2 / 4 * H)
        if ask == 'S':
            return same(num(val), (Cp - Ap).norm() * H)
        if ask == 'd':
            u = C1 - Ap
            t = (Bp - Ap).dot(u) / u.dot(u)
            dd = (Bp - (Ap + t * u)).norm()
            return same(num(val), dd * dd if 'квадрат' in ins else dd)
        u, v = B1 - Bp, C1 - Ap
        c = u.dot(v) / (u.norm() * v.norm())
        return same(num(val), sp.sqrt(1 - c * c) / c)
    return pcard(q, num(val), e, svg=svg), chk


@proto('ep15-inverse', 'ege-prof', 15, 'Обратная задача: высота (ребро) по заданному углу',
       invariant='Угол между прямой (плоскостью) и основанием выражается через высоту и проекцию; по известному углу '
                 '(30°, 45°, 60°) и стороне основания находим высоту пирамиды или призмы.',
       varies='Многогранник и отрезок (середины рёбер), сторона основания, угол.',
       answer_rule='tg φ = (часть высоты)/(длина проекции) ⇒ h; итог — h (или h²).',
       fipi=r'Найдите (высоту|объём) (пирамиды|призмы),? если .*угол между',
       mistakes=['берут не ту проекцию', 'путают tg и sin', 'для середины бокового ребра берут всю высоту'],
       svg=True,
       kim=kim(K15, 'Как в КИМ: «б) Найдите высоту пирамиды, если AB = 12, а угол между прямой MK и плоскостью основания '
                    'равен 30°»; итог — число.'))
def gen_ep15_inverse(r):
    a = r.choice([2, 3, 4, 6, 8, 9, 12, 16, 18, 24])
    phi = r.choice([30, 45, 60])
    t = {30: 1 / math.sqrt(3), 45: 1.0, 60: math.sqrt(3)}[phi]
    s2, s3 = math.sqrt(2), math.sqrt(3)
    # (вид, проекция, множитель высоты, конструктор, пункт а, что за угол, текст фигуры, площадь основания)
    cfgs = [
        ('mk', a * math.sqrt(10) / 4, 2, 'pyr4', 'Докажите, что прямая MK параллельна плоскости SBC.',
         ('alp', 'MK', 'ABC'), 'прямой MK и плоскостью основания',
         'В правильной четырёхугольной пирамиде SABCD точки M и K — середины рёбер AB и SD соответственно.', a * a),
        ('edge4', a / s2, 1, 'pyr4', 'Докажите, что прямая BD перпендикулярна плоскости SAC.', ('alp', 'SB', 'ABC'),
         'боковым ребром и плоскостью основания', 'Дана правильная четырёхугольная пирамида SABCD с основанием ABCD.', a * a),
        ('face4', a / 2, 1, 'pyr4', 'Докажите, что плоскости SAC и SBD перпендикулярны.', ('app', 'SBC', 'ABC'),
         'боковой гранью и плоскостью основания', 'Дана правильная четырёхугольная пирамида SABCD с основанием ABCD.', a * a),
        ('edge3', a / s3, 1, 'pyr3', 'Докажите, что прямые SA и BC перпендикулярны.', ('alp', 'SA', 'ABC'),
         'боковым ребром и плоскостью основания', 'Дана правильная треугольная пирамида SABC с основанием ABC.', a * a * s3 / 4),
        ('face3', a / (2 * s3), 1, 'pyr3', 'Докажите, что прямые SA и BC перпендикулярны.', ('app', 'SBC', 'ABC'),
         'боковой гранью и плоскостью основания', 'Дана правильная треугольная пирамида SABC с основанием ABC.', a * a * s3 / 4),
        ('prism', a * s3 / 2, 1, 'prism3', 'Докажите, что сечение призмы плоскостью ABC₁ — равнобедренный треугольник.',
         ('app', 'ABC1', 'ABC'), 'плоскостью ABC₁ и плоскостью основания',
         'Дана правильная треугольная призма ABCA₁B₁C₁.', a * a * s3 / 4),
        ('edge6', a, 1, 'pyr6', 'Докажите, что прямые SA и SD образуют с основанием равные углы.', ('alp', 'SA', 'ABC'),
         'боковым ребром и плоскостью основания', 'Дана правильная шестиугольная пирамида SABCDEF с основанием ABCDEF.',
         3 * s3 * a * a / 2),
    ]
    kind, proj, mult, body, stmt, qa, what, pre, Sb = r.choice(cfgs)
    h = mult * t * proj
    ask = r.choice(['h', 'h', 'V']) if body != 'prism3' else 'h'
    fig = 'призмы' if body == 'prism3' else 'пирамиды'
    val = h if ask == 'h' else Sb * h / 3
    rep = pick_repr(r, val, 'len')
    if not rep:
        return None
    ans, how = rep
    if how == 'sq' and ans > 3000:
        return None
    base_side = 'AB'
    qd = (f'Найдите {"высоту" if ask == "h" else "объём"} {fig}, если {base_side} = {a}, а угол между {what} равен {phi}°.')
    q = f'{pre}\nа) {stmt}\nб) {qd}\n{ASK15[how]}'

    def build(hh, sq, Q):
        if body == 'pyr4':
            S_ = mk_pyr4(a, hh, sq, Q)
        elif body == 'pyr3':
            S_ = mk_pyr3(a, hh, sq, Q)
        elif body == 'pyr6':
            S_ = mk_pyr6(a, hh, sq, Q)
        else:
            S_ = mk_prism3(a, hh, sq, Q)
        P = dict(S_.pts)
        if body == 'pyr4':
            P['M'] = lerp(P['A'], P['B'], Q(1) / 2)
            P['K'] = lerp(P['S'], P['D'], Q(1) / 2)
        return S_, P
    S_, Pf = build(h, math.sqrt, float)
    extra = {k_: v_ for k_, v_ in Pf.items() if k_ in ('M', 'K')} if kind == 'mk' else {}
    show = [n for n in Pf if len(n) == 1 or n.endswith('1')]
    svg = proj_svg(S_, [lab(n) for n in show], extra_pts=extra, segs=[('M', 'K')] if kind == 'mk' else [])
    e = f'tg {phi}° выражаем через высоту и проекцию; получаем {"h" if ask == "h" else "V"} = {("√" if how == "sq" else "") + tnum(ans)}.'

    def chk():
        if ask == 'h':
            hh = sp.sqrt(R(ans)) if how == 'sq' else R(ans)
        else:
            Vv = sp.sqrt(R(ans)) if how == 'sq' else R(ans)
            Sbe = {'pyr4': sp.Integer(a * a), 'pyr3': sp.sqrt(3) * a * a / 4, 'pyr6': 3 * sp.sqrt(3) * a * a / 2}[body]
            hh = 3 * Vv / Sbe
        Se, Pe = build(hh, sp.sqrt, sp.sympify)
        s_, c_ = q_exact(qa[0], Pe, Se, qa[1], qa[2])
        return abs(float(sp.N(s_ / c_)) - math.tan(math.radians(phi))) < 1e-9
    return pcard(q, num(ans), e, svg=svg), chk


# ================================================================ №18: планиметрия

ASK18 = {'': 'В ответ запишите найденное значение.', 'sq': 'В ответ запишите квадрат найденной величины.'}


def rep18(v):
    """float → (ответ, вид) или None."""
    x = fnice(v)
    if x is not None and x > 0:
        return x, ''
    x = fnice(v * v)
    if x is not None and x > 0 and x <= 2000:
        return x, 'sq'
    return None


def sqrt_txt(n):
    """√n в упрощённом виде: 12 → 2√3, 16 → 4, 7 → √7 (n — целое)."""
    k, m = sqfree(int(n))
    if m == 1:
        return str(k)
    return (str(k) if k > 1 else '') + f'√{m}'


def fig18(points, polys=(), segs=(), circles=()):
    return svg_geom({k: (float(x), float(y)) for k, (x, y) in points.items()}, polys=polys, segs=segs,
                    circles=[((float(c[0]), float(c[1])), float(rr)) for c, rr in circles], width=280)


def dist2(P, Q):
    return (P[0] - Q[0]) ** 2 + (P[1] - Q[1]) ** 2


TRIPLES_ALL = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (9, 40, 41), (12, 35, 37)]


@proto('ep18-trap-perp', 'ege-prof', 18, 'Трапеция с перпендикулярными диагоналями: высота по диагоналям и сумме оснований',
       invariant='Параллельный перенос диагонали на вектор основания даёт треугольник со сторонами d₁, d₂ и a + b; '
                 'если d₁² + d₂² = (a + b)², он прямоугольный (диагонали перпендикулярны), а высота трапеции — '
                 'высота этого треугольника: h = d₁d₂/(a + b).',
       varies='Пифагоровы тройки и их кратные, спрашиваемая величина (высота, площадь, средняя линия × высота).',
       answer_rule='h = d₁·d₂/(a + b); S = d₁·d₂/2.',
       fipi=r'Сумма оснований трапеции равна|трапеции A B C D с основаниями B C и A D перпендикулярны',
       mistakes=['считают перпендикулярность очевидной без переноса диагонали', 'путают высоту с диагональю',
                 'делят произведение диагоналей не на ту сумму'],
       svg=True,
       kim=kim(K18, 'Как в КИМ: «а) Докажите, что диагонали трапеции перпендикулярны. б) Найдите высоту трапеции»; итог — число.'))
def gen_ep18_trap_perp(r):
    t = r.choice(TRIPLES_ALL[:5])
    k = F(r.choice([1, 1, 2, 3, 4, 5])) / r.choice([1, 1, 2])
    d1, d2, s = t[0] * k, t[1] * k, t[2] * k
    if s > 60:                          # масштаб банка: диагонали и основания — десятки, не сотни
        return None
    if r.random() < 0.5:
        d1, d2 = d2, d1
    if not all(nice(v, 1) for v in (d1, d2, s)):
        return None
    h = d1 * d2 / s
    ask = r.choice(['h', 'h', 'S'])
    val = h if ask == 'h' else d1 * d2 / 2
    if not nice(val, 2):
        return None
    head = pick(r, f'Диагонали трапеции равны {tnum(d1)} и {tnum(d2)}, а сумма её оснований равна {tnum(s)}.',
                f'Диагонали трапеции равны {tnum(d1)} и {tnum(d2)}, а сумма длин её оснований равна {tnum(s)}.')
    q = (f'{head}\nа) Докажите, что диагонали этой трапеции перпендикулярны.\n'
         f'б) Найдите {"высоту" if ask == "h" else "площадь"} трапеции.\n{ASK18[""]}')
    # чертёж: A(0,0), D' (s, 0), C (d1²/s, h); верхнее основание b = s/3
    b = s / 3
    C = (d1 * d1 / s, h)
    B = (C[0] - b, h)
    D = (s - b, F(0))
    pts = {'A': (0, 0), 'B': B, 'C': C, 'D': D}
    svg = fig18(pts, polys=['ABCD'], segs=['AC', 'BD'])
    e = f'Сдвинем диагональ BD на вектор BC: треугольник со сторонами {tnum(d1)}, {tnum(d2)}, {tnum(s)} прямоугольный; h = {tnum(d1)}·{tnum(d2)}/{tnum(s)}.'

    def chk():
        A_ = sp.Matrix([0, 0])
        Cc = sp.Matrix([R(d1) ** 2 / R(s), sp.Symbol('y', positive=True)])
        y = sp.solve(sp.Eq(Cc.dot(Cc), R(d1) ** 2), sp.Symbol('y', positive=True))[0]
        Cc = sp.Matrix([R(d1) ** 2 / R(s), y])
        bb = R(s) / 3
        Bb = Cc - sp.Matrix([bb, 0])
        Dd = sp.Matrix([R(s) - bb, 0])
        ok = sp.simplify((Dd - Bb).norm() - R(d2)) == 0 and sp.simplify((Cc - A_).dot(Dd - Bb)) == 0
        area = (Dd[0] + bb) * y / 2
        return ok and same(num(val), y if ask == 'h' else area)
    return pcard(q, num(val), e, svg=svg), chk


@proto('ep18-angle-circle', 'ege-prof', 18, 'Окружность, вписанная в угол, и диаметр через точку касания',
       invariant='Касательные NA = NB, NO ⟂ AB; вписанный угол BAC опирается на диаметр, поэтому AC ⟂ AB и AC ∥ NO; '
                 'из подобия (или OB² = OM·ON) NO = R²/OM, где OM = AC/2.',
       varies='Длины AC и AB (тройки), спрашиваемая величина: NO, расстояние от N до AB, NA.',
       answer_rule='BC = √(AB² + AC²), R = BC/2, OM = AC/2, NO = R²/OM, NM = NO − OM, NA = √(NO² − R²).',
       fipi=r'касается сторон угла с вершиной',
       mistakes=['путают OM и AC', 'берут AB за диаметр', 'ошибка в подобии треугольников'],
       svg=True,
       kim=kim(K18, 'Как в КИМ: окружность, вписанная в угол, диаметр BC; «а) Докажите, что AC ∥ биссектрисе угла … '
                    'б) Найдите NO»; итог — число.'))
def gen_ep18_angle_circle(r):
    t = r.choice(TRIPLES_ALL)
    k = r.choice([1, 2, 3, 4])
    ac, ab, bc = t[0] * k, t[1] * k, t[2] * k
    if r.random() < 0.5:
        ac, ab = ab, ac
    Rr = F(bc, 2)
    om = F(ac, 2)
    no = Rr * Rr / om
    ask = r.choice(['NO', 'NM', 'NA'])
    if ask == 'NO':
        val = no
    elif ask == 'NM':
        val = no - om
    else:
        val2 = no * no - Rr * Rr
        v = math.sqrt(val2)
        rr_ = rep18(v)
        if not rr_:
            return None
        val = rr_[0] if not rr_[1] else None
        if val is None:
            return None
    if not nice(val, 2):
        return None
    head = pick(r, f'Окружность с центром O вписана в угол с вершиной N и касается его сторон в точках A и B. '
                   f'Отрезок BC — диаметр окружности, AC = {ac}, AB = {ab}.',
                f'Стороны угла с вершиной N касаются окружности с центром O в точках A и B; BC — диаметр этой '
                f'окружности. Известно, что AB = {ab}, AC = {ac}.')
    qd = {'NO': 'Найдите длину отрезка NO.', 'NM': 'Найдите расстояние от точки N до прямой AB.',
          'NA': 'Найдите длину отрезка NA.'}[ask]
    q = f'{head}\nа) Докажите, что прямая AC параллельна прямой NO.\nб) {qd}\n{ASK18[""]}'
    # координаты: O(0,0), B(0, −R), C(0, R); A на окружности с |AB| = ab
    Rf = float(Rr)
    ya = ab * ab / (2 * Rf) - Rf           # |A − B|² = 2R² + 2R·yA
    xa = math.sqrt(Rf * Rf - ya * ya)
    # касательные в A и B пересекаются в N
    # касательная в B: y = −R; в A: xa·x + ya·y = R²
    xn = (Rf * Rf + ya * Rf) / xa
    pts = {'O': (0, 0), 'B': (0, -Rf), 'C': (0, Rf), 'A': (xa, ya), 'N': (xn, -Rf)}
    svg = fig18(pts, segs=['NA', 'NB', 'BC', 'AC', 'AB', 'NO'], circles=[((0, 0), Rf)])
    e = f'BC = √({ab}² + {ac}²) = {bc}, OM = AC/2 = {fr(om)}, NO = R²/OM = {fr(no)}.'

    def chk():
        Rs = R(Rr)
        ya_ = sp.Rational(ab * ab) / (2 * Rs) - Rs
        xa_ = sp.sqrt(Rs ** 2 - ya_ ** 2)
        A_ = sp.Matrix([xa_, ya_])
        Cc = sp.Matrix([0, Rs])
        if sp.simplify((A_ - Cc).norm() - ac) != 0:
            return False
        xn_ = (Rs ** 2 + ya_ * Rs) / xa_
        N_ = sp.Matrix([xn_, -Rs])
        if sp.simplify((N_ - A_).dot(A_)) != 0:          # NA — касательная
            return False
        # пункт а: AC ∥ NO
        if sp.simplify((A_ - Cc)[0] * N_[1] - (A_ - Cc)[1] * N_[0]) != 0:
            return False
        if ask == 'NO':
            return same(num(val), N_.norm())
        if ask == 'NA':
            return same(num(val), (N_ - A_).norm())
        Bm = sp.Matrix([0, -Rs])
        u = A_ - Bm
        d = abs(u[0] * (N_ - Bm)[1] - u[1] * (N_ - Bm)[0]) / u.norm()
        return same(num(val), d)
    return pcard(q, num(val), e, svg=svg), chk


ANG = {15: (sp.sqrt(6) - sp.sqrt(2)) / 4, 30: sp.Rational(1, 2), 45: sp.sqrt(2) / 2, 60: sp.sqrt(3) / 2,
       75: (sp.sqrt(6) + sp.sqrt(2)) / 4, 90: sp.Integer(1), 105: (sp.sqrt(6) + sp.sqrt(2)) / 4,
       120: sp.sqrt(3) / 2, 135: sp.sqrt(2) / 2, 150: sp.Rational(1, 2)}


def tri_by_angles(a_len, A, B, C, exact=False):
    """Треугольник по стороне BC = a и углам (градусы): B(0,0), C(a,0), A сверху."""
    if exact:
        s = lambda d: sp.sin(sp.pi * d / 180)
        c_ = lambda d: sp.cos(sp.pi * d / 180)
    else:
        s = lambda d: math.sin(math.radians(d))
        c_ = lambda d: math.cos(math.radians(d))
    c_len = a_len * s(C) / s(A)             # AB
    Bp = (0, 0)
    Cp = (a_len, 0)
    Ap = (c_len * c_(B), c_len * s(B))
    return Ap, Bp, Cp


@proto('ep18-ninepoint', 'ege-prof', 18, 'Середины сторон и основание высоты лежат на одной окружности',
       invariant='C₁B₁ ∥ BC, а A₁B₁ = C₁H (медиана прямоугольного треугольника AHB), поэтому A₁B₁C₁H — '
                 'равнобокая трапеция и вписана в окружность; A₁H = |BH − BA₁| = |AB·cos B − BC/2|.',
       varies='Углы треугольника (стандартные), длина BC, какой отрезок спрашивается.',
       answer_rule='По теореме синусов AB = BC·sin C/sin A; BH = AB·cos B; A₁H = |BH − BC/2|.',
       fipi=r'середины сторон B C , A C и A B соответственно, A H — высота',
       mistakes=['берут неверный знак при BH − BA₁', 'путают стороны в теореме синусов', 'не учитывают тупой угол'],
       svg=True,
       kim=kim(K18, 'Как в КИМ: «а) Докажите, что точки A₁, B₁, C₁ и H лежат на одной окружности. б) Найдите A₁H»; итог — число.'))
def gen_ep18_ninepoint(r):
    A = r.choice([30, 45, 60, 120, 135, 90])
    Cc = r.choice([15, 30, 45, 60, 75])
    B = 180 - A - Cc
    if B <= 0 or B == Cc or B == 90 or B not in ANG and B not in (165,):
        return None
    k = r.randint(1, 12)
    m = r.choice([1, 2, 3, 6])
    a_len = k * math.sqrt(m)
    Ap, Bp, Cp = tri_by_angles(a_len, A, B, Cc)
    val = abs(Ap[0] - a_len / 2)
    rr_ = rep18(val)
    if not rr_:
        return None
    ans, how = rr_
    bc_txt = f'{k if k > 1 or m == 1 else ""}{"√" + str(m) if m > 1 else ""}'
    head = pick(r, f'В треугольнике ABC угол BAC равен {A}°, угол ACB равен {Cc}°; A₁, B₁, C₁ — середины сторон BC, CA, AB, '
                   f'а AH — высота треугольника.',
                f'Дан треугольник ABC, в котором ∠A = {A}°, ∠C = {Cc}°. Точки A₁, B₁ и C₁ — середины его сторон BC, AC '
                f'и AB, точка H — основание высоты, проведённой из вершины A.')
    q = (f'{head}\nа) Докажите, что точки A₁, B₁, C₁ и H лежат на одной окружности.\n'
         f'б) Найдите длину отрезка A₁H, если BC = {bc_txt}.\n{ASK18[how]}')
    pts = {'A': Ap, 'B': Bp, 'C': Cp, 'H': (Ap[0], 0), 'M': (a_len / 2, 0)}
    svg = fig18(pts, polys=['ABC'], segs=['AH'])
    svg = svg.replace('>M<', '>A₁<')
    e = f'AB = BC·sin C / sin A, BH = AB·cos B, A₁H = |BH − BC/2| = {("√" if how else "") + tnum(ans)}.'

    def chk():
        a_ = k * sp.sqrt(m)
        Ae, Be, Ce = tri_by_angles(a_, A, B, Cc, exact=True)
        H = (Ae[0], 0)
        A1 = (a_ / 2, 0)
        B1 = ((Ae[0] + Ce[0]) / 2, Ae[1] / 2)
        C1 = (Ae[0] / 2, Ae[1] / 2)
        # пункт а: вписанность через равенство A₁B₁ = C₁H и C₁B₁ ∥ A₁H
        if sp.simplify(dist2(A1, B1) - dist2(C1, H)) != 0:
            return False
        v = sp.sqrt(dist2(A1, H))
        return same(num(ans), v * v if how else v)
    return pcard(q, num(ans), e, svg=svg), chk


@proto('ep18-chords', 'ege-prof', 18, 'Вписанный четырёхугольник с тремя равными сторонами',
       invariant='Равные хорды стягивают равные дуги: ∠CAD = ∠ACB (опираются на равные дуги), значит BC ∥ AD; '
                 'центральный угол θ: sin(θ/2) = c/(2R), AD = 2R·|sin(3θ/2)| = |3c − c³/R²|.',
       varies='Радиус R и длина равных хорд c.',
       answer_rule='AD = |3c − c³/R²| (формула тройного угла).',
       fipi=r'вписан в окружность радиуса R = \d+ \. Известно, что A B = B C = C D',
       mistakes=['считают AD = 3c', 'неверно применяют формулу тройного угла', 'забывают модуль (дуга больше 180°)'],
       svg=True,
       kim=kim(K18, 'Как в КИМ: «Четырёхугольник ABCD вписан в окружность радиуса R, AB = BC = CD = … а) Докажите, что BC ∥ AD. '
                    'б) Найдите AD»; итог — число.'))
def gen_ep18_chords(r):
    Rr = r.randint(2, 20)
    c = r.randint(1, 2 * Rr - 1)
    if F(c, 2 * Rr) >= F(866, 1000):
        return None
    ad = abs(3 * c - F(c ** 3, Rr * Rr))
    if not nice(ad, 2) or ad == 0:
        return None
    head = pick(r, f'Около четырёхугольника ABCD описана окружность радиуса {Rr}, причём AB = BC = CD = {c}.',
                f'Четырёхугольник ABCD вписан в окружность, радиус которой равен {Rr}; его стороны AB, BC и CD равны {c}.')
    q = f'{head}\nа) Докажите, что прямые BC и AD параллельны.\nб) Найдите длину стороны AD.\n{ASK18[""]}'
    th = 2 * math.asin(c / (2 * Rr))
    pts = {n: (Rr * math.cos(i * th - 1.5 * th + math.pi / 2), Rr * math.sin(i * th - 1.5 * th + math.pi / 2))
           for i, n in enumerate('ABCD')}
    pts['O'] = (0, 0)
    svg = fig18(pts, polys=['ABCD'], circles=[((0, 0), Rr)])
    e = f'sin(θ/2) = {c}/{2 * Rr}, AD = 2R|sin(3θ/2)| = |3·{c} − {c}³/{Rr}²| = {tnum(ad)}.'

    def chk():
        cth = 1 - sp.Rational(c * c, 2 * Rr * Rr)          # cos θ
        sth = sp.sqrt(1 - cth ** 2)
        P = [sp.Matrix([Rr, 0])]
        rot = sp.Matrix([[cth, -sth], [sth, cth]])
        for _ in range(3):
            P.append(rot * P[-1])
        if any(sp.simplify((P[i + 1] - P[i]).norm() - c) != 0 for i in range(3)):
            return False
        # пункт а: BC ∥ AD
        u, v = P[2] - P[1], P[3] - P[0]
        if sp.simplify(u[0] * v[1] - u[1] * v[0]) != 0:
            return False
        return same(num(ad), (P[3] - P[0]).norm())
    return pcard(q, num(ad), e, svg=svg), chk


@proto('ep18-trap-isosc', 'ege-prof', 18, 'Трапеция, которую диагональ делит на два равнобедренных треугольника',
       invariant='AB = BD = BC; ∠BCA = ∠BAC и ∠BCA = ∠CAD (накрест лежащие) ⇒ AC — биссектриса; в координатах '
                 'CD² = 4BD² − AC² (параллелограмм, достроенный по диагоналям, или теорема косинусов).',
       varies='Длины диагоналей (пифагоровы тройки AC, CD, 2BD), спрашиваемая сторона.',
       answer_rule='CD = √(4BD² − AC²).',
       fipi=r'разбивает её на два равнобедренных треугольника',
       mistakes=['путают основания равнобедренных треугольников', 'ошибка в теореме косинусов', 'берут 2BD за AC'],
       svg=True,
       kim=kim(K18, 'Как в КИМ: «а) Докажите, что луч AC — биссектриса угла BAD. б) Найдите CD, если AC = … и BD = …».'))
def gen_ep18_trap_isosc(r):
    t = r.choice(TRIPLES_ALL + [(11, 60, 61), (28, 45, 53), (33, 56, 65), (16, 63, 65), (48, 55, 73)])
    k = F(r.choice([1, 1, 2, 3, 4, 5, 6])) / r.choice([1, 2, 5])
    ac, cd, dd = t[1] * k, t[0] * k, t[2] * k        # AC — больший катет (нужно AC > √2·BD)
    bd = dd / 2
    if not (ac * ac > 2 * bd * bd and ac < 2 * bd):
        ac, cd = cd, ac
        if not (ac * ac > 2 * bd * bd and ac < 2 * bd):
            return None
    if not all(nice(v, 1) for v in (ac, bd, cd)) or ac > 100:
        return None
    head = pick(r, f'В трапеции ABCD с основаниями AD и BC диагональ BD делит трапецию на два равнобедренных треугольника: '
                   f'ABD с основанием AD и BCD с основанием CD. Диагонали равны AC = {tnum(ac)} и BD = {tnum(bd)}.',
                f'Трапеция ABCD (AD ∥ BC) такова, что AB = BD и BC = BD. Её диагонали AC и BD равны {tnum(ac)} и {tnum(bd)}.')
    q = f'{head}\nа) Докажите, что AC — биссектриса угла BAD.\nб) Найдите боковую сторону CD.\n{ASK18[""]}'
    d = float(bd)
    p_ = (float(ac) ** 2 - 2 * d * d) / (2 * d)
    hh = math.sqrt(d * d - p_ * p_)
    pts = {'A': (-p_, 0), 'D': (p_, 0), 'B': (0, hh), 'C': (d, hh)}
    svg = fig18(pts, polys=['ABCD'], segs=['AC', 'BD'])
    e = f'CD² = 4BD² − AC² = {tnum(4 * bd * bd)} − {tnum(ac * ac)}, CD = {tnum(cd)}.'

    def chk():
        d_ = R(bd)
        p2 = (R(ac) ** 2 - 2 * d_ ** 2) / (2 * d_)
        h_ = sp.sqrt(d_ ** 2 - p2 ** 2)
        A_, D_, B_, C_ = sp.Matrix([-p2, 0]), sp.Matrix([p2, 0]), sp.Matrix([0, h_]), sp.Matrix([d_, h_])
        ok = sp.simplify((A_ - B_).norm() - d_) == 0 and sp.simplify((C_ - B_).norm() - d_) == 0
        ok = ok and sp.simplify((C_ - A_).norm() - R(ac)) == 0
        # биссектриса: углы CAB и CAD равны (сравниваем косинусы)
        u, v, w = B_ - A_, C_ - A_, D_ - A_
        ok = ok and sp.simplify(u.dot(v) / u.norm() - w.dot(v) / w.norm()) == 0
        return ok and same(num(cd), (D_ - C_).norm())
    return pcard(q, num(cd), e, svg=svg), chk


@proto('ep18-orthic', 'ege-prof', 18, 'Отрезок, соединяющий основания высот: подобие и расстояние от центра описанной окружности',
       invariant='Треугольник AB₁C₁ подобен ABC с коэффициентом |cos A| (B₁, C₁ — основания высот); '
                 'B₁C₁ = BC·|cos A|, расстояние от центра описанной окружности до BC равно R·|cos A| = B₁C₁/(2 sin A).',
       varies='Угол A (30°, 45°, 60°), длина B₁C₁ (с корнем, согласованным с углом), остальные углы, спрашиваемая величина.',
       answer_rule='BC = B₁C₁/cos A, R = BC/(2 sin A), d = R·cos A.',
       fipi=r'Высоты B B 1 и C C 1 остроугольного треугольника|высоты A A 1 , B B 1 и C C 1',
       mistakes=['берут коэффициент подобия sin A вместо cos A', 'путают R и расстояние до стороны', 'ошибка с корнями'],
       svg=True,
       kim=kim(K18, 'Как в КИМ: «а) Докажите, что треугольник AB₁C₁ подобен треугольнику ABC. б) Найдите расстояние от '
                    'центра описанной окружности до стороны BC, если B₁C₁ = … и ∠BAC = …».'))
def gen_ep18_orthic(r):
    A = r.choice([30, 45, 60])
    B = r.choice([b for b in (45, 60, 75) if 0 < 180 - A - b < 90])
    Cc = 180 - A - B
    k = r.randint(1, 15)
    m = {30: 1, 45: 2, 60: 3}[A]
    b1c1 = k * math.sqrt(m) if r.random() < 0.7 else k
    txt = f'{k if k > 1 or b1c1 == k else ""}{"√" + str(m) if m > 1 and b1c1 != k else ""}' if not (b1c1 == k) else str(k)
    ask = r.choice(['d', 'R', 'BC'])
    cosA = math.cos(math.radians(A))
    sinA = math.sin(math.radians(A))
    BC = b1c1 / cosA
    Rr = BC / (2 * sinA)
    val = {'d': Rr * cosA, 'R': Rr, 'BC': BC}[ask]
    rr_ = rep18(val)
    if not rr_:
        return None
    ans, how = rr_
    head = pick(r, f'В остроугольном треугольнике ABC проведены высоты BB₁ и CC₁; угол BAC равен {A}°, а B₁C₁ = {txt}.',
                f'Дан остроугольный треугольник ABC с углом {A}° при вершине A. Его высоты BB₁ и CC₁ проведены к сторонам '
                f'AC и AB, причём B₁C₁ = {txt}.')
    qd = {'d': 'Найдите расстояние от центра окружности, описанной около треугольника ABC, до прямой BC.',
          'R': 'Найдите радиус окружности, описанной около треугольника ABC.', 'BC': 'Найдите длину стороны BC.'}[ask]
    q = f'{head}\nа) Докажите, что треугольник AB₁C₁ подобен треугольнику ABC.\nб) {qd}\n{ASK18[how]}'
    Ap, Bp, Cp = tri_by_angles(BC, A, B, Cc)
    svg = fig18({'A': Ap, 'B': Bp, 'C': Cp}, polys=['ABC'])
    e = f'Коэффициент подобия |cos A|: BC = B₁C₁/cos {A}°, R = BC/(2 sin {A}°), d = R·cos {A}° = B₁C₁/(2 sin {A}°).'

    def chk():
        # строим треугольник с найденной BC и заданными углами, находим B₁, C₁ и проверяем B₁C₁
        cA = ANG[90 - A] if False else sp.cos(sp.pi * A / 180)
        target = k * sp.sqrt(m) if b1c1 != k else sp.Integer(k)
        a_ = target / cA
        Ae, Be, Ce = tri_by_angles(a_, A, B, Cc, exact=True)
        Ae, Be, Ce = [sp.Matrix(p) for p in (Ae, Be, Ce)]

        def foot(Pt, U, V):
            u = V - U
            t = (Pt - U).dot(u) / u.dot(u)
            return U + t * u
        B1 = foot(Be, Ae, Ce)
        C1 = foot(Ce, Ae, Be)
        if abs(sp.N((B1 - C1).norm() - target, 30)) > 1e-20:
            return False
        # центр описанной окружности: пересечение серединных перпендикуляров
        ox = a_ / 2
        oy = sp.Symbol('oy')
        oy = sp.solve(sp.Eq((ox - Ae[0]) ** 2 + (oy - Ae[1]) ** 2, ox ** 2 + oy ** 2), oy)[0]
        v = {'d': abs(oy), 'R': sp.sqrt(ox ** 2 + oy ** 2), 'BC': a_}[ask]
        return same(num(ans), v * v if how else v)
    return pcard(q, num(ans), e, svg=svg), chk


@proto('ep18-aho', 'ege-prof', 18, 'Ортоцентр и центр описанной окружности при угле 60° или 120°',
       invariant='AH = 2R|cos A|; при A = 60° или 120° получаем AH = R = AO; угол HAO равен |B − C|; '
                 'S(AHO) = R²·sin|B − C|/2, R = BC/(2 sin A).',
       varies='Угол A (60° или 120°), углы B и C, длина BC (целая или k√3), спрашиваемая величина.',
       answer_rule='R = BC/√3, S = R²·sin|B − C|/2 (или HO² = 2R²(1 − cos|B − C|)).',
       fipi=r'содержащие высоты',
       mistakes=['берут AH = 2R', 'неверно находят угол HAO', 'путают R и BC'],
       svg=True,
       kim=kim(K18, 'Как в КИМ: «а) Докажите, что AH = AO. б) Найдите площадь треугольника AHO, если BC = …, ∠ABC = …».'))
def gen_ep18_aho(r):
    A, B = r.choice([(120, 15), (120, 45), (60, 45), (60, 75), (60, 15), (60, 105)])
    Cc = 180 - A - B
    if r.random() < 0.5:
        k = r.randint(1, 14)
        bct, bc = f'{k}√3' if k > 1 else '√3', k * math.sqrt(3)
    else:
        k = r.choice([3, 6, 9, 12, 15, 18, 21, 24, 2, 4])
        bct, bc = str(k), float(k)
    Rr = bc / math.sqrt(3)
    d = abs(B - Cc)
    ask = r.choice(['S', 'S', 'HO'])
    if ask == 'S':
        val = Rr * Rr * math.sin(math.radians(d)) / 2
    else:
        val = math.sqrt(2 * Rr * Rr * (1 - math.cos(math.radians(d))))
    rr_ = rep18(val)
    if not rr_:
        return None
    ans, how = rr_
    head = pick(r, f'В треугольнике ABC угол A равен {A}°, угол ABC равен {B}°, BC = {bct}. Прямые, на которых лежат '
                   f'высоты треугольника, пересекаются в точке H, O — центр описанной около треугольника окружности.',
                f'Дан треугольник ABC: ∠A = {A}°, ∠B = {B}°, BC = {bct}. Точка H — ортоцентр треугольника (точка '
                f'пересечения прямых, содержащих высоты), точка O — центр его описанной окружности.')
    qd = 'Найдите площадь треугольника AHO.' if ask == 'S' else 'Найдите длину отрезка HO.'
    q = f'{head}\nа) Докажите, что AH = AO.\nб) {qd}\n{ASK18[how]}'
    Ap, Bp, Cp = tri_by_angles(bc, A, B, Cc)
    svg = fig18({'A': Ap, 'B': Bp, 'C': Cp}, polys=['ABC'])
    e = f'AH = 2R|cos A| = R = AO, ∠HAO = |B − C| = {d}°, R = BC/√3.'

    def chk():
        a_ = k * sp.sqrt(3) if '√' in bct else sp.Integer(k)
        Ae, Be, Ce = [sp.Matrix(p) for p in tri_by_angles(a_, A, B, Cc, exact=True)]
        # ортоцентр: H = A + B + C − 2O для центра O описанной окружности
        ox = a_ / 2
        oy = sp.Symbol('oy')
        oy = sp.solve(sp.Eq((ox - Ae[0]) ** 2 + (oy - Ae[1]) ** 2, ox ** 2 + oy ** 2), oy)[0]
        O = sp.Matrix([ox, oy])
        H = Ae + Be + Ce - 2 * O
        # проверка: H на высоте из A (x = A_x) и AH = AO
        if abs(sp.N(H[0] - Ae[0], 30)) > 1e-20 or abs(sp.N((H - Ae).norm() - (O - Ae).norm(), 30)) > 1e-20:
            return False
        if ask == 'S':
            u, v = H - Ae, O - Ae
            v_ = abs(u[0] * v[1] - u[1] * v[0]) / 2
        else:
            v_ = (H - O).norm()
        return same(num(ans), v_ * v_ if how else v_)
    return pcard(q, num(ans), e, svg=svg), chk


@proto('ep18-tangent-seg', 'ege-prof', 18, 'Отрезок, отсекающий подобный треугольник и касающийся вписанной окружности',
       invariant='MN ∥ AC отсекает треугольник MBN, подобный ABC с коэффициентом t; четырёхугольник AMNC описан около '
                 'окружности: AM + NC = MN + AC ⇒ (1 − t)(AB + BC) = (1 + t)AC.',
       varies='Коэффициент t (середины сторон или деление в отношении), периметр, прямой угол, спрашиваемая величина.',
       answer_rule='AB + BC = k·AC, k = (1 + t)/(1 − t); с прямым углом C: BC = AC(k² − 1)/(2k); P = (k + 1)AC.',
       fipi=r'касается отрезка M N|касается окружности, вписанной в треугольник|касается окружности, вписанной',
       mistakes=['путают стороны в свойстве описанного четырёхугольника', 'неверный коэффициент подобия',
                 'забывают, что MN = t·AC'],
       svg=True,
       kim=kim(K18, 'Как в КИМ: «а) Докажите, что AB + BC = 3AC. б) Найдите площадь треугольника ABC, если … ∠ACB = 90°».'))
def gen_ep18_tangent_seg(r):
    t = r.choice([F(1, 2), F(1, 2), F(3, 5), F(1, 3), F(2, 3), F(3, 4)])
    k = (1 + t) / (1 - t)
    if k.denominator != 1 and r.random() < 0.3:
        return None
    b = F(r.randint(2, 30))
    a = b * (k * k - 1) / (2 * k)              # BC (катет), C — прямой угол
    c = k * b - a                              # AB (гипотенуза)
    if not (a > 0 and c > a and c > b):
        return None
    P = a + b + c
    ask = r.choice(['S', 'r', 'P'])
    val = {'S': a * b / 2, 'r': (a + b - c) / 2, 'P': P}[ask]
    if not nice(val, 2) or not nice(P, 2):
        return None
    if t == F(1, 2):
        pre = 'Точки M и N — середины сторон AB и BC треугольника ABC.'
    else:
        u = t / (1 - t)          # BM : MA = t : (1 − t)
        pre = (f'На сторонах AB и BC треугольника ABC взяты точки M и N так, что BM : MA = BN : NC = '
               f'{u.numerator} : {u.denominator}.')
    given = {'S': f'периметр треугольника равен {tnum(P)}', 'r': f'периметр треугольника равен {tnum(P)}',
             'P': f'AC = {tnum(b)}'}[ask]
    qd = {'S': 'Найдите площадь треугольника ABC', 'r': 'Найдите радиус вписанной окружности треугольника ABC',
          'P': 'Найдите периметр треугольника ABC'}[ask]
    kt = tnum(k) if k.denominator == 1 else fr(k)
    q = (f'{pre} Отрезок MN касается окружности, вписанной в треугольник ABC.\n'
         f'а) Докажите, что AB + BC = {kt}·AC.\nб) {qd}, если угол ACB прямой, а {given}.\n{ASK18[""]}').replace(
        '= 1·AC', '= AC')
    pts = {'C': (0, 0), 'A': (b, 0), 'B': (0, a)}
    pts['M'] = lerp(pts['B'], pts['A'], t)
    pts['N'] = lerp(pts['B'], pts['C'], t)
    rr = (a + b - c) / 2
    svg = fig18(pts, polys=['ABC'], segs=['MN'], circles=[((rr, rr), rr)])
    e = f'AMNC описан: AM + NC = MN + AC ⇒ AB + BC = {kt}·AC; с ∠C = 90°: AC = {fr(b)}, BC = {fr(a)}, AB = {fr(c)}.'

    def chk():
        # восстанавливаем треугольник только по данным условия: ∠C = 90°, AB + BC = k·AC, периметр/AC
        x, y = sp.symbols('x y', positive=True)    # x = AC, y = BC
        hyp = sp.sqrt(x ** 2 + y ** 2)
        eqs = [sp.Eq(hyp + y, R(k) * x)]
        eqs.append(sp.Eq(x + y + hyp, R(P)) if ask != 'P' else sp.Eq(x, R(b)))
        sol = sp.solve(eqs, [x, y], dict=True)
        if len(sol) != 1:
            return False
        X_, Y_v = sol[0][x], sol[0][y]
        Cp, Ap, Bp = sp.Matrix([0, 0]), sp.Matrix([X_, 0]), sp.Matrix([0, Y_v])
        M = Bp + R(t) * (Ap - Bp)
        N = Bp + R(t) * (Cp - Bp)
        rin = (X_ + Y_v - sp.sqrt(X_ ** 2 + Y_v ** 2)) / 2
        I = sp.Matrix([rin, rin])
        u = N - M
        dist = abs(u[0] * (I - M)[1] - u[1] * (I - M)[0]) / u.norm()
        if sp.simplify(dist - rin) != 0:
            return False
        v = {'S': X_ * Y_v / 2, 'r': rin, 'P': X_ + Y_v + sp.sqrt(X_ ** 2 + Y_v ** 2)}[ask]
        return same(num(val), v)
    return pcard(q, num(val), e, svg=svg), chk


@proto('ep18-rhombus', 'ege-prof', 18, 'Ромб и прямая, перпендикулярная стороне: косинус угла и длины',
       invariant='В координатах с центром ромба в начале: M на AC, N на BD, условие MN ⟂ BC даёт отношение диагоналей; '
                 'отсюда cos∠BAD = (u² − v²)/(u² + v²) и связь MN со стороной.',
       varies='Отношения AM : MC и BN : ND, длина MN, спрашиваемая величина (сторона, площадь).',
       answer_rule='Полудиагонали u, v: x_M·u + y_N·v = 0 (скалярное произведение); сторона² = u² + v²; S = 2uv.',
       fipi=r'перпендикулярная стороне B C ромба',
       mistakes=['неверные координаты точек деления', 'путают диагонали', 'ошибка в знаке при скалярном произведении'],
       svg=True,
       kim=kim(K18, 'Как в КИМ: «а) Докажите, что cos∠BAD = 1/5. б) Найдите площадь ромба (сторону), если MN = …».'))
def gen_ep18_rhombus(r):
    m1, m2 = r.choice([(1, 2), (1, 3), (2, 3), (1, 4), (3, 5), (2, 5)])
    n1, n2 = r.choice([(1, 3), (1, 2), (1, 4), (2, 3), (1, 5), (3, 5)])
    if r.random() < 0.5:
        m1, m2 = m1, m2
    # A(−u,0), C(u,0), B(0,v), D(0,−v); M = A + (AM/AC)(C − A): x_M = u(m1 − m2)/(m1 + m2)
    alpha = F(m1 - m2, m1 + m2)        # x_M = α·u
    beta = F(n2 - n1, n1 + n2)         # y_N = β·v (N от B к D)
    # MN ⟂ BC: BC = (u, −v); MN = (−αu, βv); (−αu)·u + (βv)(−v) = 0 → −α u² − β v² = 0 → v²/u² = −α/β
    rho2 = -alpha / beta
    if rho2 <= 0 or rho2 == 1:
        return None
    cosA = (1 - rho2) / (1 + rho2)
    ask = r.choice(['side', 'S'])
    # MN² = α²u² + β²v² = u²(α² + β²ρ²)
    gam = alpha * alpha + beta * beta * rho2
    side = r.randint(2, 20)
    u2 = F(side * side) / (1 + rho2)
    mn2 = u2 * gam
    if ask == 'side':
        val, how = F(side), ''
    else:
        S2 = 4 * u2 * u2 * rho2            # S² = 4u²v²
        s = fnice(math.sqrt(float(S2)))
        if s is not None and s ** 2 == S2:
            val, how = s, ''
        elif nice(S2, 2) and S2 <= 5000:
            val, how = S2, 'sq'
        else:
            return None
    # MN как текст: √(mn2)
    if mn2.denominator != 1:
        return None
    mn_t = sqrt_txt(mn2)
    ct = fr(cosA) if cosA.denominator != 1 else tnum(cosA)
    head = pick(r, f'Прямая, перпендикулярная стороне BC ромба ABCD, пересекает диагональ AC в точке M, а диагональ BD — '
                   f'в точке N, причём AM : MC = {m1} : {m2}, BN : ND = {n1} : {n2}.',
                f'В ромбе ABCD через точку M диагонали AC и точку N диагонали BD провели прямую MN, перпендикулярную '
                f'стороне BC. Известно, что AM : MC = {m1} : {m2} и BN : ND = {n1} : {n2}.')
    qd = f'Найдите {"сторону ромба" if ask == "side" else "площадь ромба"}, если MN = {mn_t}.'
    q = f'{head}\nа) Докажите, что cos∠BAD = {ct}.\nб) {qd}\n{ASK18[how]}'
    uf = math.sqrt(float(u2))
    vf = uf * math.sqrt(float(rho2))
    pts = {'A': (-uf, 0), 'B': (0, vf), 'C': (uf, 0), 'D': (0, -vf), 'M': (float(alpha) * uf, 0), 'N': (0, float(beta) * vf)}
    svg = fig18(pts, polys=['ABCD'], segs=['AC', 'BD', 'MN'])
    e = f'v²/u² = {fr(rho2)}, cos∠BAD = (u² − v²)/(u² + v²) = {ct}; MN² = {fr(gam)}·u².'

    def chk():
        uu, vv = sp.symbols('uu vv', positive=True)
        A_, B_, C_, D_ = sp.Matrix([-uu, 0]), sp.Matrix([0, vv]), sp.Matrix([uu, 0]), sp.Matrix([0, -vv])
        M = A_ + sp.Rational(m1, m1 + m2) * (C_ - A_)
        N = B_ + sp.Rational(n1, n1 + n2) * (D_ - B_)
        sol = sp.solve([sp.Eq((N - M).dot(C_ - B_), 0), sp.Eq((N - M).dot(N - M), R(mn2))], [uu, vv], dict=True)
        sol = [s_ for s_ in sol if s_[uu].is_positive and s_[vv].is_positive]
        if len(sol) != 1:
            return False
        U, V = sol[0][uu], sol[0][vv]
        AB, AD = B_ - A_, D_ - A_
        cos_ = (AB.dot(AD) / (AB.norm() * AD.norm())).subs({uu: U, vv: V})
        if sp.simplify(cos_ - R(cosA)) != 0:
            return False
        v = sp.sqrt(U ** 2 + V ** 2) if ask == 'side' else 2 * U * V
        return same(num(val), v * v if how else v)
    return pcard(q, num(val), e, svg=svg), chk


@proto('ep18-iso-trap', 'ege-prof', 18, 'Равнобедренная трапеция с кратными основаниями: высота делит основание, расстояния',
       invariant='В равнобедренной трапеции высота CH делит AD на AH = (AD + BC)/2 и HD = (AD − BC)/2; '
                 'при AD = k·BC отношение (k + 1) : (k − 1); далее координаты или теорема Пифагора.',
       varies='Кратность k, основания, диагональ (через корень) или боковая сторона, точка (середина BD, середина OD).',
       answer_rule='Высота из AC² = AH² + h², затем расстояние от C до середины отрезка по координатам.',
       fipi=r'равнобедренной трапеции A B C D основание A D в (два|три) раза',
       mistakes=['путают AH и HD', 'неверно находят точку пересечения диагоналей', 'ошибка в координатах середины'],
       svg=True,
       kim=kim(K18, 'Как в КИМ: «а) Докажите, что высота CH делит AD на отрезки в отношении 2 : 1. б) Найдите расстояние от C '
                    'до середины BD, если AD = …, AC = …».'))
def gen_ep18_iso_trap(r):
    k = r.choice([2, 3, 4, 5])
    b = r.randint(2, 12)
    a = k * b
    h = r.randint(2, 16)
    target = r.choice(['BD', 'OD'])
    A, D = (F(0), F(0)), (F(a), F(0))
    B, C = (F(a - b, 2), F(h)), (F(a + b, 2), F(h))
    if target == 'BD':
        Pm = ((B[0] + D[0]) / 2, (B[1] + D[1]) / 2)
        tname = 'середины диагонали BD'
    else:
        # O — пересечение диагоналей: делит BD в отношении BC : AD = 1 : k
        O = (B[0] + (D[0] - B[0]) / (k + 1), B[1] + (D[1] - B[1]) / (k + 1))
        Pm = ((O[0] + D[0]) / 2, (O[1] + D[1]) / 2)
        tname = 'середины отрезка OD, где O — точка пересечения диагоналей'
    d2 = dist2(C, Pm)
    rr_ = rep18(math.sqrt(float(d2)))
    if not rr_:
        return None
    ans, how = rr_
    ac2 = dist2(A, C)
    if ac2.denominator != 1:
        return None
    head = pick(r, f'Дана равнобедренная трапеция ABCD, у которой большее основание AD в {k} {plural(k, "раз", "раза", "раз")} '
                   f'длиннее меньшего основания BC.',
                f'Основание AD равнобедренной трапеции ABCD в {k} {plural(k, "раз", "раза", "раз")} больше её основания BC.')
    g_ = math.gcd(k + 1, k - 1)
    q = (f'{head}\nа) Докажите, что высота CH делит основание AD на отрезки, длины которых относятся как {(k + 1) // g_} : {(k - 1) // g_}.\n'
         f'б) Найдите расстояние от вершины C до {tname}, если AD = {a}, AC = {sqrt_txt(ac2)}.\n{ASK18[how]}').replace(
        'как 2 : 1', 'как 2 : 1')
    pts = {'A': A, 'B': B, 'C': C, 'D': D, 'H': (C[0], F(0))}
    svg = fig18(pts, polys=['ABCD'], segs=['AC', 'BD', 'CH'])
    e = f'AH = {tnum(F(a + b, 2))}, HD = {tnum(F(a - b, 2))}; высота h = {h}; искомое расстояние = {("√" if how else "") + tnum(ans)}.'

    def chk():
        bb, hh = sp.symbols('bb hh', positive=True)
        Ae, De = sp.Matrix([0, 0]), sp.Matrix([a, 0])
        Be, Ce = sp.Matrix([(a - bb) / 2, hh]), sp.Matrix([(a + bb) / 2, hh])
        sol = sp.solve([sp.Eq(k * bb, a), sp.Eq((Ce - Ae).dot(Ce - Ae), R(ac2))], [bb, hh], dict=True)
        if len(sol) != 1:
            return False
        s_ = sol[0]
        Be, Ce = Be.subs(s_), Ce.subs(s_)
        if target == 'BD':
            Pp = (Be + De) / 2
        else:
            # пересечение диагоналей AC и BD
            t1, t2 = sp.symbols('t1 t2')
            ss = sp.solve(list(Ae + t1 * (Ce - Ae) - (Be + t2 * (De - Be))), [t1, t2], dict=True)[0]
            Oe = Ae + ss[t1] * (Ce - Ae)
            Pp = (Oe + De) / 2
        v = (Ce - Pp).norm()
        # пункт а
        H_ = sp.Matrix([Ce[0], 0])
        if sp.simplify(H_[0] * (k - 1) - (De[0] - H_[0]) * (k + 1)) != 0:
            return False
        return same(num(ans), v * v if how else v)
    return pcard(q, num(ans), e, svg=svg), chk


@proto('ep18-similar-circle', 'ege-prof', 18, 'Окружность через две вершины треугольника: подобие и отношение площадей',
       invariant='B, C, B₁, C₁ на одной окружности ⇒ ∠AB₁C₁ = ∠ABC, треугольники AB₁C₁ и ABC подобны; отношение '
                 'площадей = k², откуда BC = B₁C₁/k.',
       varies='Угол A (для чертежа и контекста), B₁C₁, во сколько раз площадь четырёхугольника больше площади треугольника.',
       answer_rule='S(ABC) = (n + 1)·S(AB₁C₁) ⇒ k = 1/√(n + 1), BC = B₁C₁·√(n + 1).',
       fipi=r'Окружность проходит через вершины [ВB] и [СC] треугольника',
       mistakes=['берут отношение площадей n вместо n + 1', 'коэффициент подобия равен отношению площадей',
                 'путают соответственные стороны'],
       svg=True,
       kim=kim(K18, 'Как в КИМ: «а) Докажите, что треугольник AB₁C₁ подобен треугольнику ABC. б) Найдите BC, если …».'))
def gen_ep18_similar_circle(r):
    n = r.choice([3, 8, 15, 24, 3, 8])
    A = r.choice([30, 45, 60, 75, 120, 135])
    b1c1 = r.randint(2, 15)
    kk = math.isqrt(n + 1)
    bc = b1c1 * kk
    head = pick(r, f'Окружность проходит через вершины B и C треугольника ABC и вторично пересекает стороны AB и AC в точках '
                   f'C₁ и B₁ соответственно. Угол BAC равен {A}°, B₁C₁ = {b1c1}.',
                f'Через вершины B и C треугольника ABC (∠A = {A}°) проведена окружность, которая пересекает отрезки AB и AC '
                f'в точках C₁ и B₁; известно, что B₁C₁ = {b1c1}.')
    q = (f'{head}\nа) Докажите, что треугольники AB₁C₁ и ABC подобны.\n'
         f'б) Найдите BC, если площадь четырёхугольника BCB₁C₁ в {n} {plural(n, "раз", "раза", "раз")} больше площади '
         f'треугольника AB₁C₁.\n{ASK18[""]}')
    # чертёж: A(0,0), AB вдоль оси, AC под углом A
    ab = 3.0
    ac = 2.2
    Ap = (0, 0)
    Bp = (ab, 0)
    Cp = (ac * math.cos(math.radians(A)), ac * math.sin(math.radians(A)))
    k = 1 / kk
    C1 = (ac * k, 0)
    B1 = (ab * k * math.cos(math.radians(A)), ab * k * math.sin(math.radians(A)))
    svg = fig18({'A': Ap, 'B': Bp, 'C': Cp, 'C₁': C1, 'B₁': B1}, polys=['ABC'], segs=[])
    e = f'Подобие с коэффициентом k: S(ABC) = {n + 1}·S(AB₁C₁) ⇒ k = 1/{kk}, BC = {b1c1}·{kk} = {bc}.'

    def chk():
        # треугольник с углом A и произвольными AB, AC; ищем k по условию площадей и проверяем вписанность
        ABv, ACv = sp.Integer(5), sp.Integer(3)
        cA = sp.cos(sp.pi * A / 180)
        sA = sp.sin(sp.pi * A / 180)
        Ae, Be, Ce = sp.Matrix([0, 0]), sp.Matrix([ABv, 0]), sp.Matrix([ACv * cA, ACv * sA])
        kv = sp.Symbol('kv', positive=True)
        C1e = sp.Matrix([ACv * kv, 0])                  # AC₁ = k·AC
        B1e = sp.Matrix([ABv * kv * cA, ABv * kv * sA])  # AB₁ = k·AB
        area = lambda P, Q, W: abs((Q - P)[0] * (W - P)[1] - (Q - P)[1] * (W - P)[0]) / 2
        sol = sp.solve(sp.Eq(area(Ae, Be, Ce), (n + 1) * area(Ae, B1e, C1e)), kv)
        if len(sol) != 1:
            return False
        kv_ = sol[0]
        # вписанность B, C, B₁, C₁: степень точки A: AB·AC₁ = AC·AB₁
        if sp.simplify(ABv * ACv * kv_ - ACv * ABv * kv_) != 0:
            return False
        ratio = (Be - Ce).norm() / (B1e - C1e).subs(kv, kv_).norm()
        return same(num(bc), b1c1 * ratio)
    return pcard(q, num(bc), e, svg=svg), chk


# ================================================================ рецепты для ИИ (доказательная часть и сложные сюжеты)


def _chk_ep15_proof():
    # пирамида SABC: S(0,0,6), A(0,0,0)… — проверяем отношение объёмов частей, на которые плоскость MNK делит пирамиду
    S, A, B, C = (sp.Integer(0), 0, 6), (0, 0, 0), (6, 0, 0), (0, 6, 0)
    M = lerp(S, A, sp.Rational(1, 2))
    N = lerp(S, B, sp.Rational(1, 2))
    K = lerp(S, C, sp.Rational(1, 3))
    vol = lambda P, Q, W, Z: abs(v_dot(v_sub(Q, P), v_cross(v_sub(W, P), v_sub(Z, P)))) / 6
    small = vol(S, M, N, K)
    big = vol(S, A, B, C) - small
    return small / vol(S, A, B, C) == sp.Rational(1, 12) and big / small == 11


proto_llm('ep15-proof', 'ege-prof', 15, 'Доказательство в стереометрии + вычисление (сечения, отношения, объёмы частей)',
          invariant='Пункт а — доказательство взаимного расположения (параллельность, перпендикулярность, положение точки '
                    'сечения); пункт б — вычисление с опорой на а: отношение отрезков, объёмов частей, площадь сечения.',
          varies='Многогранник (произвольная треугольная или четырёхугольная пирамида, призма с трапецией/параллелограммом в '
                 'основании, тетраэдр с квадратом в сечении), отношения на рёбрах, спрашиваемая величина.',
          answer_rule='Числовой итог пункта б пересчитывается кодом по координатам вершин (объёмы — через определитель).',
          recipe={'prompt': 'Составь условие №15 КИМ ЕГЭ профиль: описание многогранника с числами и точками на рёбрах; '
                            '«а) Докажите, что …» (утверждение, которое код проверил на координатах), «б) Найдите …» '
                            '(отношение объёмов, площадь сечения, отношение отрезков). Слова и сюжет — свои, не из банка ФИПИ.',
                  'code': 'Код задаёт координаты вершин, точки на рёбрах (отношения), строит сечение (пересечения с рёбрами), '
                          'проверяет утверждение пункта а (скалярные/векторные произведения = 0) и считает ответ б точно.',
                  'check': 'Ответ пересчитывается независимо: объём части — как V(пирамиды) − V(отсечённой), площадь — '
                           'через проекцию; сравнение точное (sympy).',
                  'capacity': 'виды многогранников (≈6) × положения точек (≈10) × отношения (≈10) × вопросы (3) ≈ 1800'},
          example={'q': 'В треугольной пирамиде SABC точки M и N — середины рёбер SA и SB, а точка K лежит на ребре SC, '
                        'причём SK : KC = 1 : 2.\nа) Докажите, что прямая MN параллельна плоскости ABC.\n'
                        'б) Плоскость MNK делит пирамиду на два многогранника. Найдите отношение объёма большего из них к '
                        'объёму меньшего.\nВ ответ запишите найденное отношение.',
                   'a': '11', 'chk': _chk_ep15_proof},
          capacity=1800, fipi=r'(?=.*Докажите)(?=.*(пирамид|призм|куб|тетраэдр|параллелепипед))',
          mistakes=['считают отношение объёмов равным отношению отрезков', 'неверно строят сечение',
                    'доказательство подменяют ссылкой на рисунок'],
          kim=kim(K15, 'Как в КИМ: «а) Докажите … б) Найдите отношение объёмов/площадь сечения»; итог — число.'))


def _chk_ep18_circles():
    # две окружности касаются внешним образом, радиусы 4 и 9: длина общей внешней касательной = 2√(4·9) = 12
    r1, r2 = 4, 9
    d = r1 + r2
    return sp.sqrt(d ** 2 - (r2 - r1) ** 2) == 12


proto_llm('ep18-circles', 'ege-prof', 18, 'Касающиеся окружности, общие касательные, вписанные углы (доказательство + вычисление)',
          invariant='Пункт а — доказательство (параллельность, равенство углов через касательные и гомотетию касающихся '
                    'окружностей); пункт б — вычисление по радиусам: длина касательной 2√(r₁r₂), расстояния, хорды.',
          varies='Внешнее или внутреннее касание, радиусы, вписанный прямоугольный треугольник, спрашиваемая величина.',
          answer_rule='Числовой итог пересчитывается кодом по координатам центров и точек касания.',
          recipe={'prompt': 'Составь условие №18 КИМ ЕГЭ профиль про две касающиеся окружности (или окружность, касающуюся '
                            'сторон угла): «а) Докажите, что …», «б) Найдите …». Своими словами, не пересказывая банк.',
                  'code': 'Код задаёт радиусы и положение точек (углы), вычисляет координаты всех точек и ответ.',
                  'check': 'Независимый пересчёт: теорема Пифагора для касательной / координаты точек пересечения (sympy).',
                  'capacity': 'радиусы (≈40 пар) × конфигурации (≈5) × вопросы (≈3) ≈ 600'},
          example={'q': 'Две окружности радиусов 4 и 9 касаются внешним образом в точке K. Прямая касается окружностей в '
                        'точках A и B (A — на меньшей).\nа) Докажите, что угол AKB прямой.\nб) Найдите длину отрезка AB.\n'
                        'В ответ запишите найденное значение.', 'a': '12', 'chk': _chk_ep18_circles},
          capacity=600, fipi=r'Две окружности|касаются внутренним образом|касаются внешним образом',
          mistakes=['путают внешнее и внутреннее касание', 'длину касательной считают как r₁ + r₂',
                    'не обосновывают коллинеарность центров и точки касания'],
          kim=kim(K18, 'Как в КИМ: две касающиеся окружности, пункт а — доказательство, б — длина/площадь.'))


proto_llm('ep18-misc', 'ege-prof', 18, 'Параллелограмм, трапеция, биссектрисы и вписанные окружности (доказательство + вычисление)',
          invariant='Пункт а — доказательство свойства конфигурации (биссектриса, равенство отрезков, вписанность); '
                    'пункт б — вычисление через теоремы косинусов/синусов, площадь и полупериметр (r = S/p), подобие.',
          varies='Фигура (параллелограмм с точкой на стороне, трапеция с биссектрисами, треугольник с высотами/медианами), '
                 'данные длины и углы, спрашиваемая величина.',
          answer_rule='Код строит фигуру в координатах по данным условия и вычисляет ответ; иррациональный ответ — '
                      'в карточке как квадрат величины.',
          recipe={'prompt': 'Составь условие №18: фигура с числовыми данными; «а) Докажите, что …» (свойство, которое код '
                            'проверил численно), «б) Найдите …». Формулировки свои, стиль КИМ.',
                  'code': 'Код задаёт стороны/углы, строит координаты, проверяет утверждение а и считает ответ б точно (sympy).',
                  'check': 'Второй способ: теорема косинусов / формула Герона вместо координат.',
                  'capacity': 'конфигурации (≈15) × наборы чисел (≈40) ≈ 600'},
          example={'q': 'На стороне BC параллелограмма ABCD, у которого AB = 5, AD = 10 и ∠BAD = 60°, выбрана точка M так, '
                        'что AM = MC.\nа) Докажите, что центр окружности, вписанной в треугольник AMD, лежит на диагонали AC.\n'
                        'б) Найдите длину отрезка AM.\nВ ответ запишите найденное значение.',
                   'a': '7', 'chk': lambda: _ep18_misc_val() == 7},
          capacity=600, fipi=r'(?=.*Докажите)(?=.*(треугольник|трапец|параллелограмм|ромб|квадрат|окружност|четырёхугольник|пятиугольник|прямоугольник))(?!.*(пирамид|призм|куб|цилиндр|конус|тетраэдр|параллелепипед))',
          mistakes=['неверно применяют свойство биссектрисы', 'ошибка в теореме косинусов', 'путают r = S/p и R = abc/4S'],
          kim=kim(K18, 'Как в КИМ: пункт а — доказательство, б — вычисление; итог — число.'))


def _ep18_misc_val():
    A_ = sp.Matrix([0, 0])
    B_ = sp.Matrix([sp.Rational(5, 2), 5 * sp.sqrt(3) / 2])
    D_ = sp.Matrix([10, 0])
    C_ = B_ + D_
    x = sp.Symbol('x', real=True)
    P = sp.Matrix([x, B_[1]])
    xm = sp.solve(sp.Eq((P - A_).dot(P - A_), (C_ - P).dot(C_ - P)), x)[0]
    M = sp.Matrix([xm, B_[1]])
    # пункт а: биссектриса угла MAD — прямая AC (углы CAM и CAD равны)
    u, v, w = M - A_, C_ - A_, D_ - A_
    if sp.simplify(u.dot(v) / u.norm() - w.dot(v) / w.norm()) != 0:
        return None
    return sp.simplify((M - A_).norm())


def _chk_ep20_avg():
    # 11 различных натуральных; среднее пяти наименьших = 6, пяти наибольших = 20; наибольшая сумма всех чисел.
    # Перебор среднего (шестого) числа m: слева 5 различных чисел < m с суммой 30, справа 5 различных > m с суммой 100.
    best = None
    for m in range(1, 101):
        left = any(sum(c) == 30 for c in itertools.combinations(range(1, m), 5))
        right = any(sum(c) == 100 for c in itertools.combinations(range(m + 1, 101), 5)) if left else False
        if left and right:
            best = 130 + m
    return best == 147


proto_llm('ep20-averages', 'ege-prof', 20, 'Средние арифметические частей набора различных чисел',
          invariant='Суммы «наименьших» и «наибольших» частей перекрываются; общая сумма = S₁ + S₂ − (общие члены); '
                    'оценка крайних значений через различность чисел (минимальные суммы подряд идущих) + пример.',
          varies='Количество чисел, размеры частей, средние, спрашиваемая величина (наибольшее среднее, наименьшее число, S − B).',
          answer_rule='Код перебирает наборы и находит экстремум; пример строится явно.',
          recipe={'prompt': 'Составь условие №20 (а, б, в) о наборе различных натуральных чисел со средними частей; '
                            'в пункте в — экстремальная величина. Сюжет и слова свои.',
                  'code': 'Код задаёт размеры и средние, перебором находит экстремум и пример набора.',
                  'check': 'Перебор всех подходящих наборов (itertools) другим способом.',
                  'capacity': 'n (8–12) × размеры частей × средние (≈20) ≈ 400'},
          example={'q': 'Ученик выписал 11 попарно различных натуральных чисел. Оказалось, что среднее арифметическое пяти '
                        'самых маленьких из них равно 6, а пяти самых больших — 20.\nа) Может ли самое маленькое из чисел '
                        'равняться 5?\nб) Может ли сумма всех выписанных чисел равняться 140?\n'
                        'в) Какое наибольшее значение может принимать сумма всех выписанных чисел?\n'
                        'В ответ запишите ответ на вопрос пункта в.', 'a': '147', 'chk': _chk_ep20_avg},
          capacity=400, fipi=r'Среднее арифметическое (шести|пяти|четырёх) наименьших|Средняя масса фруктов',
          mistakes=['забывают, что части перекрываются', 'не учитывают различность чисел', 'нет примера к оценке'],
          kim=kim(K20, 'Как в КИМ: а, б — «может ли…», в — наибольшее/наименьшее значение; итог — число.'))


def _chk_ep20_school():
    # две секции (в каждой не меньше двух человек), средний балл первой 20; после перехода одного спортсмена средние
    # обеих секций выросли на 10 %. Наибольшее возможное число спортсменов во второй секции — перебором.
    best = None
    for n1 in range(2, 40):
        s1 = 20 * n1
        for x in range(1, s1):                    # балл перешедшего
            if F(s1 - x, n1 - 1) != 22:
                continue
            for m2 in range(1, 60):               # исходный средний балл второй секции (целый)
                for n2 in range(2, 400):
                    if F(m2 * n2 + x, n2 + 1) == F(m2 * 11, 10):
                        best = n2 if best is None else max(best, n2)
    return best == 169


proto_llm('ep20-transfer', 'ege-prof', 20, 'Переход элемента между группами и изменение средних',
          invariant='Средний балл группы = сумма / количество; переход одного элемента меняет обе суммы и количества; '
                    'условия на изменение средних (в разы, на проценты) дают диофантовы уравнения.',
          varies='Количество групп и участников, изменение средних (в k раз, на p %), сюжет (школы, бригады, команды).',
          answer_rule='Код решает диофантовы условия перебором и находит экстремальное значение.',
          recipe={'prompt': 'Составь условие №20 о переходе участника из одной группы в другую с изменением средних; '
                            'а, б — «мог ли…», в — наименьшее/наибольшее значение. Сюжет свой.',
                  'code': 'Код перебирает размеры групп и баллы, проверяет условия, находит экстремум.',
                  'check': 'Перебор другим порядком (по баллу перешедшего).',
                  'capacity': 'сюжеты (≈6) × изменения (≈10) × данные (≈10) ≈ 600'},
          example={'q': 'Спортсмены двух секций сдавали норматив, каждый получил натуральное число баллов; в каждой секции '
                        'средний балл был целым, в первой — 20. Один спортсмен перешёл из первой секции во вторую, и средние '
                        'баллы обеих секций выросли на 10 %. Изначально в каждой секции было не меньше двух спортсменов.\n'
                        'а) Мог ли перешедший получить 10 баллов?\n'
                        'б) Мог ли средний балл второй секции изначально быть равен 30?\n'
                        'в) Какое наибольшее число спортсменов могло быть во второй секции до перехода?\n'
                        'В ответ запишите ответ на вопрос пункта в.', 'a': '169', 'chk': _chk_ep20_school},
          capacity=600, fipi=r'учащиеся писали тест',
          mistakes=['путают «на 10 %» и «в 1,1 раза» при пересчёте', 'забывают про целочисленность средних',
                    'нет примера'],
          kim=kim(K20, 'Как в КИМ: а, б — «мог ли…», в — экстремум; итог — число.'))


def _chk_ep20_cards():
    # синие: различные числа, кратные 5; красные: различные чётные; все числа > −60.
    # наибольшее красное = 2·(число синих), наибольшее синее = число красных. Наибольшее общее число карточек.
    best = 0
    for b in range(1, 80):
        for rr in range(1, 200):
            if rr % 5:
                continue                         # наибольшее синее число = rr кратно 5
            # синих b различных кратных 5 чисел > −60 и ≤ rr: их не больше (rr − (−55))/5 + 1
            if b > (rr + 55) // 5 + 1:
                continue
            # красных rr различных чётных > −60 и ≤ 2b: не больше (2b + 58)/2 + 1
            if rr > (2 * b + 58) // 2 + 1:
                continue
            best = max(best, b + rr)
    return best == 72


proto_llm('ep20-cards', 'ege-prof', 20, 'Карточки двух цветов: ограничения на наибольшие числа и количество',
          invariant='Числа одного цвета различны и лежат в арифметической прогрессии (кратные k, чётные), ограничены '
                    'снизу; наибольшее число одного цвета связано с количеством карточек другого цвета — получаем '
                    'систему неравенств на количества.',
          varies='Кратности (3, 5, чётные), нижняя граница, связи «наибольшее = 2·количество», сюжет.',
          answer_rule='Оценка: количество чисел кратности k на отрезке ≤ длина/k + 1; из системы неравенств — максимум; пример.',
          recipe={'prompt': 'Составь условие №20 про карточки двух цветов (как в демоверсии), но со своими числами и '
                            'связями; в — наибольшее количество карточек.',
                  'code': 'Код перебирает количества синих и красных, проверяет достижимость, находит максимум и пример.',
                  'check': 'Прямой перебор наборов для небольших параметров.',
                  'capacity': 'кратности (≈6) × границы (≈10) × связи (≈4) ≈ 240'},
          example={'q': 'На столе лежат синие и красные карточки (есть хотя бы по одной каждого цвета), на каждой написано '
                        'целое число, большее −60. Числа на синих карточках различны и делятся на 5, на красных — различны и '
                        'чётны. Наибольшее число на красной карточке вдвое больше числа синих карточек, а наибольшее число на '
                        'синей карточке равно числу красных карточек.\nа) Может ли на столе лежать 8 карточек?\n'
                        'б) Может ли красных карточек быть на 40 больше, чем синих?\n'
                        'в) Какое наибольшее количество карточек может лежать на столе?\n'
                        'В ответ запишите ответ на вопрос пункта в.', 'a': '72', 'chk': _chk_ep20_cards},
          capacity=240, fipi=r'часть из которых синего цвета|либо зелёного, либо красного цвета',
          mistakes=['не учитывают отрицательные числа в диапазоне', 'путают число карточек и наибольшее число',
                    'нет примера'],
          kim=kim(K20, 'Как в КИМ (демоверсия 2027): а, б — «может ли…», в — наибольшее количество.'))


def _chk_ep20_proof():
    # приписывание цифр 1 и 8 к числам трёх групп: сумма выросла в 11 раз — наибольшее количество чисел (перебор малых)
    best = 0
    # 10x + 1 для первой группы, 10x + 8 для второй: 10(S1 + S2) + n1 + 8n2 + S3 = 11(S1 + S2 + S3) ⇒
    # n1 + 8n2 = S1 + S2 + 10·S3; при различных натуральных числах S ≥ 1 + 2 + … — перебор
    for n1 in range(1, 12):
        for n2 in range(1, 12):
            for n3 in range(1, 12):
                n = n1 + n2 + n3
                # наименьшая возможная S1 + S2 + 10·S3 при различных числах: малые числа — в третью группу
                nums = list(range(1, n + 1))
                s3 = sum(nums[:n3])
                s12 = sum(nums[n3:])
                if s12 + 10 * s3 <= n1 + 8 * n2:
                    best = max(best, n)
    return best == 10


proto_llm('ep20-digits-append', 'ege-prof', 20, 'Приписывание цифр к числам: оценка + пример',
          invariant='Приписывание цифры d справа превращает x в 10x + d; условие на рост суммы даёт линейное уравнение; '
                    'оценка через наименьшую сумму различных чисел, пример — подбор.',
          varies='Приписываемые цифры, число групп, во сколько раз выросла сумма, спрашиваемая величина.',
          answer_rule='Сравниваем n₁d₁ + n₂d₂ с минимально возможной суммой; максимум n — оценка + пример (перебор).',
          recipe={'prompt': 'Составь условие №20 о приписывании цифр к числам нескольких групп; в — наибольшее количество '
                            'чисел или наибольший коэффициент роста. Сюжет свой.',
                  'code': 'Код перебирает размеры групп и наборы малых чисел, находит экстремум и пример.',
                  'check': 'Прямой перебор наборов чисел для найденного n и n + 1.',
                  'capacity': 'цифры (≈20 пар) × коэффициенты (≈8) ≈ 160'},
          example={'q': 'На доске написали несколько различных натуральных чисел и разбили их на три непустые группы. К каждому '
                        'числу первой группы приписали справа цифру 1, к каждому числу второй — цифру 8, числа третьей '
                        'группы не изменяли.\nа) Могла ли сумма всех чисел увеличиться в 5 раз?\n'
                        'б) Могла ли сумма увеличиться в 19 раз?\n'
                        'в) Сумма всех чисел увеличилась в 11 раз. Какое наибольшее количество чисел могло быть на доске?\n'
                        'В ответ запишите ответ на вопрос пункта в.', 'a': '10', 'chk': _chk_ep20_proof},
          capacity=160, fipi=r'приписали справа цифру',
          mistakes=['не учитывают различность чисел', 'нет примера', 'ошибка в уравнении для суммы'],
          kim=kim(K20, 'Как в КИМ: а, б — «могла ли…», в — наибольшее количество; итог — число.'))


def _chk_ep19_abs_sum():
    # (|x − a − 1| + |x − a + 1|)² − 5(|x − a − 1| + |x − a + 1|) + 6 − ... : число целых a
    # t = |x − a − 1| + |x − a + 1| ≥ 2; t² + a t + a² − 16 = 0: ровно два корня ⇔ ровно один корень t > 2
    cnt = 0
    for a in range(-10, 11):
        ts = [t for t in sp.solve(sp.Symbol('t') ** 2 + a * sp.Symbol('t') + a * a - 16, sp.Symbol('t')) if t.is_real]
        good = [t for t in set(ts) if t > 2]
        eq2 = [t for t in set(ts) if t == 2]
        roots = 2 * len(good) + (1000 if eq2 else 0)    # t = 2 — целый отрезок корней
        if roots == 2:
            cnt += 1
    return cnt == 7


proto_llm('ep19-abs-sum', 'ege-prof', 19, 'Замена t = |x − p| + |x − q|: квадратное уравнение относительно t',
          invariant='Функция t(x) = |x − p| + |x − q| ≥ |p − q|, значение |p − q| принимается на целом отрезке, каждое '
                    'большее значение — ровно в двух точках; число корней исходного уравнения определяется корнями '
                    'квадратного уравнения по t и их положением относительно |p − q|.',
          varies='Сдвиги p, q (зависят от a), квадратное уравнение по t, требуемое число корней.',
          answer_rule='Для каждого a: корни t > |p − q| дают по два x, t = |p − q| — бесконечно много; итог — число целых a.',
          recipe={'prompt': 'Составь условие №19 с заменой t = |x − p(a)| + |x − q(a)| и квадратным уравнением по t; '
                            'вопрос о числе корней. Формулировка КИМ, числа свои.',
                  'code': 'Код для каждого целого a решает квадратное по t и считает корни x.',
                  'check': 'Численный поиск корней исходного уравнения по x для каждого a.',
                  'capacity': 'сдвиги (≈20) × уравнения по t (≈20) × условия (3) ≈ 1200'},
          example={'q': 'Найдите все значения a, при каждом из которых уравнение '
                        '⟦(|x − a − 1| + |x − a + 1|)² + a(|x − a − 1| + |x − a + 1|) + a² − 16 = 0⟧ '
                        'имеет ровно два различных корня.\n'
                        'В ответ запишите количество целых значений a, удовлетворяющих условию.', 'a': '7',
                   'chk': _chk_ep19_abs_sum},
          capacity=1200, fipi=r'\( \| x − a (−|\+) \d \| \+ \| x|\( \| x − a 2 \| \+ \| x \+ 1 \| \)|\( \d* ?x [+−] \d* ?\| x [+−] a|\( \d x \+ \| x − a \|',
          mistakes=['забывают, что t ≥ |p − q|', 'при t = |p − q| считают один корень вместо отрезка',
                    'не учитывают совпадение корней t'],
          kim=kim(K19, 'Как в КИМ: «(|x − a − 1| + |x − a + 1|)² + a(…) + a² − 16 = 0 имеет ровно два различных корня».'))


def _chk_ep19_graph():
    # |x| + |y| = a, y = √(x + 4): ровно два решения при a ∈ (2; 4) и a = 17/4 (касание левой ветви)
    def cnt(a):
        pts = set()
        x = sp.Symbol('x', real=True)
        for sx in (1, -1):
            sol = sp.solve(sp.Eq(sx * x + sp.sqrt(x + 4), a), x)
            for s_ in sol:
                if s_.is_real and s_ >= -4 and (sx * s_ >= 0):
                    pts.add(sp.nsimplify(s_))
        return len(pts)
    return (cnt(3) == 2 and cnt(sp.Rational(17, 4)) == 2 and cnt(sp.Rational(41, 10)) == 3
            and all(cnt(sp.Rational(v, 100)) == 1 for v in (426, 450, 500, 700)))


proto_llm('ep19-graph', 'ege-prof', 19, 'Системы с модулями и корнями: графический метод (квадраты, полупараболы, степени)',
          invariant='Каждое уравнение — известная линия (квадрат |x| + |y| = a, полупарабола y = √(x + c), окружности, '
                    'x⁴ − y⁴ через замену u = x², v = y²); число решений — число общих точек, граничные случаи — касание и '
                    'прохождение через особые точки.',
          varies='Вид линий, параметр (размер, сдвиг), требуемое число решений.',
          answer_rule='Код считает число решений при каждом значении a (точно) и находит множество ответа.',
          recipe={'prompt': 'Составь условие №19 с системой из «графических» уравнений (модули, корни, чётные степени); '
                            'вопрос о числе решений. Числа свои, формулировка КИМ.',
                  'code': 'Для каждого a код решает систему по случаям знаков и считает решения.',
                  'check': 'sympy.solve системы при каждом целом a; сравнение множеств.',
                  'capacity': 'пары линий (≈10) × параметры (≈20) × условия (3) ≈ 600'},
          example={'q': 'Найдите все положительные значения a, при каждом из которых система ⟦{|x| + |y| = a; y = √(x + 4)}⟧ '
                        'имеет ровно два различных решения.\nВ ответ запишите наибольшее значение a из найденного множества.',
                   'a': '4,25', 'chk': _chk_ep19_graph},
          capacity=600, fipi=r'\| x \| \+ \| y \| = a|x 4 − y 4 =|x 4 \+ y 2 = a 2',
          mistakes=['теряют вершины квадрата', 'не проверяют касание', 'путают число решений и число точек пересечения'],
          kim=kim(K19, 'Как в КИМ: система с |x| + |y| = a и корнем / чётными степенями; число решений.'))


# ---------------------------------------------------------------- №14: дополнительные разновидности


@proto('ep14-trig-group', 'ege-prof', 14, 'Группировка с sin 2x: (2sin x + p)(cos x + q) = 0',
       invariant='sin 2x = 2sin x cos x; четыре слагаемых группируются попарно, получается произведение двух '
                 'скобок с простейшими тригонометрическими уравнениями.',
       varies='Корни скобок (стандартные значения, одна скобка может не давать решений), формулы приведения, отрезок.',
       answer_rule='sin x = −p/2 или cos x = −q (с проверкой |…| ≤ 1); отбор корней на отрезке.',
       fipi=r'sin 2 x [+−] \d* ?(sin|cos) \( − x \) [+−] \d* ?(sin|cos) \( − x \)',
       mistakes=['не видят группировки', 'теряют одну из скобок', 'ошибка в знаке sin(−x)'],
       kim=kim(K14, 'Как в КИМ: «sin 2x + 2sin(−x) + cos(−x) − 1 = 0»; отбор корней на отрезке.', kes=['2.3']))
def gen_ep14_trig_group(r):
    first = r.choice('sc')            # (2·first + p)(other + q)
    other = 'c' if first == 's' else 's'
    vals_first = [QS(1), QS(-1), QS(1, 2), QS(-1, 2), QS(1, 3), QS(-1, 3), QS(2), QS(-2), QS(3)]
    p = r.choice(vals_first)           # first = −p/2
    q = r.choice([QS(1), QS(-1), QS(F(1, 2)), QS(-F(1, 2)), QS(2), QS(-2), QS(F(1, 2), 2), QS(-F(1, 2), 3)])
    # 2·first·other + 2q·first + p·other + pq
    c_first, c_other, c0 = q * QS(2), p, p * q
    if c_first is None or c0 is None:
        return None
    rf, sf = red(r, first)
    ro, so = red(r, other)
    terms = [(QS(1), 'sin 2x'), (c_first * QS(sf), rf), (c_other * QS(so), ro), (c0, '')]
    eq = shuffle_sides(r, terms)
    lo, hi = segment14(r)
    v1 = QS(-p.r / 2, p.m)
    v2 = -q
    sers = series(FUN[first], v1) + series(FUN[other], v2)
    rts = roots_on(sers, lo, hi)
    a_ = ask14(r, rts)
    if not a_:
        return None
    ask, ans = a_
    e = (f'sin 2x = 2sin x cos x; группируем: (2{FUN[first]} x {"+" if p.r > 0 else "−"} {QS(abs(p.r), p.m).text()})'
         f'({FUN[other]} x {"+" if q.r > 0 else "−"} {QS(abs(q.r), q.m).text()}) = 0. На отрезке: {roots_text(rts)}.')
    return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)


@proto('ep14-trig-expand-lin', 'ege-prof', 14, 'Формула суммы: после сокращения — простейшее уравнение',
       invariant='Раскрываем k·sin(x ± φ) или k·cos(x ± φ); слагаемое с одной из функций сокращается с другим членом '
                 'уравнения, остаётся простейшее уравнение sin x = a или cos x = a.',
       varies='Угол φ, множитель, какая функция сокращается, значение a, отрезок.',
       answer_rule='Серии простейшего уравнения, отбор на отрезке.',
       fipi=r'Решите уравнение \d* ?(cos|sin) \( x [+−] π \d \) [+−] \d* ?√\( \d \) (cos|sin) \([^)]*\) = (√\( \d \)|\d)',
       mistakes=['ошибка в формуле суммы', 'не замечают сокращения', 'путают серии sin x = a и cos x = a'],
       kim=kim(K14, 'Как в КИМ: «4cos(x + π/4) + 2√2 cos(π − x) = 2»; отбор корней на отрезке.', kes=['2.3', '1.5']))
def gen_ep14_trig_expand_lin(r):
    txt, al, be = r.choice(EXPAND)
    keep = r.choice('sc')              # остающаяся функция
    own, other = (al, be) if keep == 's' else (be, al)
    if own.is_zero() or other.is_zero():
        return None
    t = r.choice([v for v in T_OK if not v.is_zero()])
    C = own * t
    if C is None:
        return None
    ro, so = red(r, 'c' if keep == 's' else 's')
    left = [(QS(1), txt), (-(other) * QS(so), ro)]
    eq = f'{join_terms(left)} = {join_terms([(C, "")])}'
    lo, hi = segment14(r)
    rts = roots_on(series(FUN[keep], t), lo, hi)
    a_ = ask14(r, rts)
    if not a_:
        return None
    ask, ans = a_
    e = f'Раскрываем {txt}: слагаемые с {FUN["c" if keep == "s" else "s"]} x сокращаются, {FUN[keep]} x = {t.text()}. На отрезке: {roots_text(rts)}.'
    return pcard(q14(r, eq, seg_pi(lo, hi), ask), num(ans), e), lambda: check14(eq, lo, hi, ask, ans)


@proto('ep16-log-identity', 'ege-prof', 16, 'Основное логарифмическое тождество в неравенстве: a^{log_a f(x)} = f(x) при f(x) > 0',
       invariant='a^{log_a f(x)} = f(x) только на ОДЗ f(x) > 0; после замены — рациональное неравенство, решения которого '
                 'пересекаем с ОДЗ.',
       varies='Основание, выражение f (линейное или квадратное), второе слагаемое (многочлен), знак.',
       answer_rule='Решаем f(x) + g(x) ∨ 0 и пересекаем с f(x) > 0.',
       fipi=r'Решите неравенство \d log \d+ (\(|\d)',
       mistakes=['забывают ОДЗ f(x) > 0', 'заменяют a^{log_a f} на f без условия', 'ошибка при решении квадратного'],
       kim=kim(K16, 'Как в КИМ: «3^{log₃(4 − x²)} + x⁴ − 10 ≥ 0» — ловушка ОДЗ.', kes=['2.7', '2.5']))
def gen_ep16_log_identity(r):
    b = r.choice([2, 3, 5, 7])
    kind = r.choice(['lin', 'quad'])
    if kind == 'lin':
        k, m = r.choice([1, 2, 3, 5, -1, -2, -5]), r.randint(-12, 25)
        f = lambda x: k * x + m
        ft = poly([k, m])
        c1, c0 = r.choice([2, 3, 4, 5, -2, -3]), r.randint(-40, 40)
        g = lambda x: c1 * x + c0
        gt = join_terms([(QS(c1), 'x'), (QS(c0), '')])
    else:
        C = r.choice([4, 9, 16, 25, 5, 10, 20])
        f = lambda x: C - x * x
        ft = f'{C} − x²'
        c2, c0 = r.choice([1, 1, 2]), r.randint(-40, 10)
        g = lambda x: c2 * x ** 4 + c0
        gt = join_terms([(QS(c2), 'x⁴'), (QS(c0), '')])
    rel = r.choice(['≥', '≤', '>', '<'])
    text = f'{b}^{{{logb(b)}({ft})}} ' + (f'− {gt[1:]}' if gt.startswith('−') else f'+ {gt}') + f' {rel} 0'

    def sat(x):
        fv = f(x)
        if fv <= 0:
            return False
        return rel_ok(F(fv + g(x)), rel)
    e = f'ОДЗ: {ft} > 0; на ней {b}^{{{logb(b)}({ft})}} = {ft}, остаётся {ft} + ({gt}) {rel} 0.'
    return card16(r, text, sat, e)


def _chk_ep19_sym():
    # 2^{|x|+1} + 3|x| = y + x² + a, x² + y² = 1: единственное решение ⇒ x = 0 (чётность) ⇒ y = ±1;
    # a = 2 − y ∈ {1, 3}; проверка кандидатов: при a = 1 решение одно, при a = 3 — три (лишний кандидат)

    def count(a):
        # y = 2^{|x|+1} + 3|x| − x² − a, подставляем в x² + y² = 1 и ищем корни по x ∈ [−1; 1]
        f = sp.Abs(X)
        expr = X ** 2 + (2 ** (f + 1) + 3 * f - X ** 2 - a) ** 2 - 1
        return len(num_roots(expr, -1, 1, n=4000))
    return count(1) == 1 and count(3) == 3 and count(2) == 2


proto_llm('ep19-symmetry', 'ege-prof', 19, 'Метод симметрии: единственное решение ⇒ x = 0 (чётность по x)',
          invariant='Если (x; y) — решение, то и (−x; y) — решение (функции от |x| и x²); единственное решение возможно '
                    'лишь при x = 0; находим кандидаты a и проверяем каждый — лишние отбрасываются.',
          varies='Функции от |x| (показательные, модули), вторая линия (окружность, парабола), сюжет условия.',
          answer_rule='Кандидаты a из подстановки x = 0; проверка числа решений при каждом кандидате; итог — сумма/число a.',
          recipe={'prompt': 'Составь условие №19 на метод симметрии: система (или уравнение) с |x| и x², требование '
                            'единственного решения. Формулировка КИМ, числа свои.',
                  'code': 'Код находит кандидатов при x = 0 и для каждого кандидата считает решения численно.',
                  'check': 'Численный поиск корней по x (с учётом касаний) при каждом кандидате.',
                  'capacity': 'функции (≈8) × вторые линии (≈4) × числа (≈10) ≈ 320'},
          example={'q': 'Найдите все значения a, при каждом из которых система ⟦{2^{|x| + 1} + 3|x| = y + x² + a; x² + y² = 1}⟧ '
                        'имеет единственное решение.\nВ ответ запишите найденное значение a.',
                   'a': '1', 'chk': _chk_ep19_sym},
          capacity=320, fipi=r"\d+ \| x \| \+ \d+ \+ \d+ ⋅ \| x \||x ​? 4 \+ \( a − \d \) 2 = \| x",
          mistakes=['не проверяют кандидатов (лишний корень)', 'забывают про симметрию по x', 'путают |x| и x'],
          kim=kim(K19, 'Как в КИМ: система с |x|, «имеет единственное решение»; итог — значение a.'))


def _chk_ep20_circle_sums():
    # по кругу N различных натуральных чисел ≤ 100; сумма любых трёх подряд делится на 3, любых двух подряд — нечётна.
    # Тогда остатки по модулю 6 периодичны с периодом… Находим наибольшее N перебором по остаткам.
    # Из «двух подряд нечётно» — чётность чередуется, N чётно; из «трёх подряд делится на 3» — остатки mod 3
    # повторяются с периодом 3, N кратно 3. Итого N кратно 6, а остатки по модулю 6 повторяются с периодом 6.
    best = 0
    for pattern in itertools.product(range(6), repeat=6):
        ok = all((pattern[i] + pattern[(i + 1) % 6]) % 2 == 1 for i in range(6)) and \
            all((pattern[i] + pattern[(i + 1) % 6] + pattern[(i + 2) % 6]) % 3 == 0 for i in range(6))
        if not ok:
            continue
        cnt = collections_counter(pattern)
        # каждый остаток r встречается cnt[r] раз на период; чисел с остатком r среди 1..100 — avail[r]
        avail = {r_: len([v for v in range(1, 101) if v % 6 == r_]) for r_ in range(6)}
        k = min(avail[r_] // c for r_, c in cnt.items())
        best = max(best, 6 * k)
    return best == 96


def collections_counter(seq):
    d = {}
    for x in seq:
        d[x] = d.get(x, 0) + 1
    return d


proto_llm('ep20-circle-sums', 'ege-prof', 20, 'Числа по кругу: делимость сумм подряд идущих',
          invariant='Если сумма любых k подряд идущих чисел делится на m, то остатки чисел по модулю m повторяются с '
                    'периодом k (соседние суммы отличаются на a_{i+k} − a_i); вместе с условием на чётность получаем '
                    'периодичность остатков и оценку N по количеству чисел с нужными остатками.',
          varies='Длины блоков (2, 3, 4), модули, верхняя граница чисел, спрашиваемая величина (наибольшее N).',
          answer_rule='Перебор периодических наборов остатков; N = период × min(доступно/нужно); пример.',
          recipe={'prompt': 'Составь условие №20 о числах по кругу с условиями делимости сумм подряд идущих; а, б — '
                            '«может ли N равняться …», в — наибольшее N. Числа и условия свои.',
                  'code': 'Код перебирает периодические шаблоны остатков и считает наибольшее N и пример расстановки.',
                  'check': 'Проверка найденной расстановки (все суммы) и невозможности для N + период.',
                  'capacity': 'пары условий (≈10) × границы (≈20) ≈ 200'},
          example={'q': 'Вокруг клумбы по кругу посадили N кустов роз и у каждого поставили табличку с номером — '
                        'натуральным числом не больше 100, все номера разные. Сумма номеров любых трёх кустов, растущих '
                        'подряд, делится на 3, а сумма номеров любых двух соседних кустов нечётна.\nа) Может ли N быть равным 30?\n'
                        'б) Может ли N быть равным 40?\nв) Найдите наибольшее возможное N.\n'
                        'В ответ запишите ответ на вопрос пункта в.', 'a': '96', 'chk': _chk_ep20_circle_sums},
          capacity=200, fipi=r'По кругу расставлено N различных натуральных чисел',
          mistakes=['не замечают периодичности остатков', 'забывают, что N кратно периоду', 'нет примера'],
          kim=kim(K20, 'Как в КИМ: а, б — «может ли N быть равным …», в — наибольшее N.'))


def _chk_ep20_misc():
    # трёхзначное n, не оканчивающееся нулём, n = k·S(n); наибольшее k — перебором по n
    ks = set()
    for n in range(100, 1000):
        if n % 10:
            s_ = sum(map(int, str(n)))
            if n % s_ == 0:
                ks.add(n // s_)
    # второй способ: перебор по k и сумме цифр
    ks2 = {k for k in range(1, 1000) for s_ in range(1, 28)
           if 100 <= k * s_ <= 999 and (k * s_) % 10 and sum(map(int, str(k * s_))) == s_}
    return ks == ks2 and max(ks) == 89 and 12 in ks and 20 not in ks


proto_llm('ep20-misc', 'ege-prof', 20, 'Числа и их свойства: оценка + пример (прочие сюжеты)',
          invariant='Пункты а и б — проверка возможности (пример или противоречие по делимости/остаткам/оценке), '
                    'пункт в — экстремальное значение: доказательство оценки и пример, на котором она достигается.',
          varies='Сюжеты: цифры и десятичная запись, доли и проценты в классе, прогрессии (фотографии по дням), '
                 'разрезание, операции над дробями и парами, письма и количества, тройки чисел с условием.',
          answer_rule='Код находит ответ пункта в перебором (конечная область) и строит пример; ИИ пишет условие.',
          recipe={'prompt': 'Составь условие №20 (а, б, в) на свойства натуральных чисел в стиле КИМ: сюжет свой, '
                            'в пункте в — наибольшее/наименьшее значение. Не пересказывай задания банка.',
                  'code': 'Код задаёт параметры, перебором находит ответ пункта в и пример (и ответы а, б).',
                  'check': 'Независимый перебор другим порядком (например, по парам множителей вместо чисел).',
                  'capacity': 'сюжеты (≈15) × параметры (≈20) ≈ 300'},
          example={'q': 'Для натурального числа n обозначим через S(n) сумму его цифр. Рассматриваются трёхзначные числа, '
                        'последняя цифра которых отлична от нуля.\nа) Существует ли такое n, что n = 12·S(n)?\n'
                        'б) Существует ли такое n, что n = 20·S(n)?\nв) Найдите наибольшее натуральное k, для которого '
                        'найдётся такое n с n = k·S(n).\nВ ответ запишите ответ на вопрос пункта в.', 'a': '89',
                   'chk': _chk_ep20_misc},
          capacity=300,
          fipi=r'(?=.*а\) )(?=.*в\) )(?=.*(натуральн|цифр|чисел|число|количеств))(?!.*(треугольник|пирамид|кредит|вклад|значения a|уравнени))',
          mistakes=['приводят пример без оценки', 'оценка без примера', 'перебор без обоснования полноты'],
          kim=kim(K20, 'Как в КИМ: три пункта, в — экстремум; итог — число.'))
