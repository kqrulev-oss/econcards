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
from functools import reduce

from mathlib import (F, R, X, SUB, finite, ftxt, nice, num, par, pcard, pick, plural, poly, proto, proto_llm,
                     same, signed, sp, svg_geom, tnum, _svg, BLUE, RED, INK, GRID)

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

K14 = dict(level='П', points=2, minutes=10, kes=['2.3'], kt=['КТ 3'],
           answer='развёрнутый (в карточке — число из пункта б: количество, сумма или крайний корень)',
           scoring=CRIT14)
K15 = dict(level='П', points=3, minutes=20, kes=['7.2', '7.3'], kt=['КТ 9', 'КТ 10', 'КТ 11'],
           answer='развёрнутый (в карточке — число из пункта б)', scoring=CRIT_AB3)
K16 = dict(level='П', points=2, minutes=10, kes=['2.7'], kt=['КТ 3'],
           answer='развёрнутый (в карточке — число: сумма или количество целых решений, крайнее целое решение)',
           scoring=CRIT16)
K18 = dict(level='П', points=3, minutes=35, kes=['7.1'], kt=['КТ 9', 'КТ 11'],
           answer='развёрнутый (в карточке — число из пункта б)', scoring=CRIT_AB3)
K19 = dict(level='В', points=4, minutes=35, kes=['2.10'], kt=['КТ 3', 'КТ 5'],
           answer='развёрнутый (в карточке — число: количество или сумма целых a из ответа, граничное значение)',
           scoring=CRIT19)
K20 = dict(level='В', points=4, minutes=40, kes=['1.1'], kt=['КТ 1', 'КТ 2', 'КТ 13'],
           answer='развёрнутый (в карточке — число из пункта в)', scoring=CRIT20)


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
        return None

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
                e = e / self.power()
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
            return sp.sqrt(self.atom())
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
            if not ch.isalpha():
                raise ValueError(f'аргумент функции в {self.s!r} @ {j}')
            self.i += 1
            arg = k * self.env[ch]
            if self.s.startswith('/', self.i) and self.s[self.i + 1:self.i + 2].isdigit():
                self.i += 1
                arg = arg / self.number()
        fn = {'sin': sp.sin, 'cos': sp.cos, 'tg': sp.tan, 'ctg': sp.cot, 'ln': sp.log}.get(f)
        v = sp.log(arg, base) if f == 'log' else fn(arg)
        return v ** pw


A_ = sp.Symbol('a', real=True)
Y_ = sp.Symbol('y', real=True)


def parse_f(s, env=None):
    """Текст формулы → sympy (выражение или (знак, левая, правая))."""
    return _P(s, env or {'x': X, 'a': A_, 'y': Y_}).parse()


def eq_expr(s):
    """Уравнение «L = R» → L − R."""
    op, a, b = parse_f(s)
    assert op == '=', s
    return a - b


# ================================================================ численный поиск корней (для проверок №14)


def num_roots(f, lo, hi, n=6000):
    """Все корни выражения f(x) на [lo; hi] (включая касания), численно по сетке + уточнение.
    Точки, где f не определена (комплексное значение, деление на 0), пропускаются."""
    g = sp.lambdify(X, f, modules=['mpmath'])
    import mpmath as mp
    mp.mp.dps = 30

    def val(x):
        try:
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

    xs = [lo + (hi - lo) * i / n for i in range(n + 1)]
    vs = [val(x) for x in xs]
    cand = []
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
        if v0 is not None and abs(v0) < mp.mpf(10) ** -12 and lo - 1e-9 <= x0 <= hi + 1e-9:
            if all(abs(x0 - q) > 1e-7 for q in roots):
                roots.append(x0)
    return sorted(float(x) for x in roots)


# ================================================================ №14: общие части


# значения синуса/косинуса стандартных углов и «посторонние» значения (|t| > 1)
T_OK = [QS(0), QS(F(1, 2)), QS(-F(1, 2)), QS(1), QS(-1), QS(F(1, 2), 2), QS(-F(1, 2), 2),
        QS(F(1, 2), 3), QS(-F(1, 2), 3)]
T_BAD = [QS(2), QS(-2), QS(F(3, 2)), QS(-F(3, 2)), QS(3), QS(-3), QS(1, 2), QS(-1, 2), QS(1, 3), QS(-1, 3),
         QS(F(5, 2)), QS(-F(5, 2)), QS(4), QS(-4)]

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
            return (pick(r, 'В ответ запишите количество корней, найденных в пункте б.',
                         'В ответ запишите, сколько корней найдено в пункте б.',
                         'Для самопроверки введите число корней из пункта б.'), F(len(rts)))
        exact = all(e is not None for e, _ in rts)
        if not exact:
            continue
        if k == 'sum':
            s = sum(e for e, _ in rts)
            if s != 0 and nice(s, 2):
                return (pick(r, 'В ответ запишите сумму корней из пункта б, делённую на π.',
                             'Для самопроверки введите сумму корней, найденных в пункте б, делённую на π.'), s)
        if k in ('max', 'min'):
            e = max(e for e, _ in rts) if k == 'max' else min(e for e, _ in rts)
            deg = e * 180
            if deg.denominator == 1:
                w = 'наибольший' if k == 'max' else 'наименьший'
                return (pick(r, f'В ответ запишите {w} из корней пункта б в градусах.',
                             f'Для самопроверки введите {w} корень из пункта б, выраженный в градусах.'), deg)
    return None


def check14(eq_text, lo, hi, ask, ans):
    """Независимая проверка: разбираем уравнение из текста и ищем корни численно."""
    f = eq_expr(eq_text)
    rts = num_roots(f, float(lo) * math.pi, float(hi) * math.pi)
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


PART_A = ['а) Решите уравнение {f}.', 'а) Решите уравнение {f}.', 'а) Найдите все решения уравнения {f}.']
PART_B = ['б) Найдите все его корни, принадлежащие промежутку {s}.',
          'б) Укажите корни, лежащие на отрезке {s}.',
          'б) Отберите корни уравнения, принадлежащие отрезку {s}.',
          'б) Найдите корни этого уравнения из отрезка {s}.',
          'б) Какие из корней уравнения лежат на отрезке {s}?']


def q14(r, eq, s, ask):
    return (pick(r, *PART_A).format(f=fm(eq)) + '\n' + pick(r, *PART_B).format(s=fm(s)) + '\n' + ask)


def roots_text(rts):
    out = []
    for e, v in rts:
        out.append(pis(e) if e is not None else f'≈{v * math.pi:.3f}'.replace('.', ','))
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
    left, right = [], []
    for t in terms:
        if left and r.random() < 0.3:
            right.append((-qs(t[0]), t[1]))
        else:
            left.append(t)
    return f'{join_terms(left)} = {join_terms(right)}'
