"""Прототипы ЕГЭ профиль (КИМ 2027), задания 1–5.

№1 — планиметрия (КЭС 7.1): треугольники, четырёхугольники, окружность, площади.
№2 — векторы на плоскости (КЭС 7.5): координаты, длина, скалярное произведение, угол.
№3 — стереометрия (КЭС 7.3, 7.4): многогранники из параллелепипеда и призмы, тела вращения.
№4 — простая вероятность (КЭС 6.2, базовый уровень).
№5 — вероятность сложных событий (КЭС 6.2, повышенный уровень).

Формулировки и сюжеты свои; стиль инструкций как в КИМ («Ответ дайте в градусах.»,
«Найдите вероятность того, что …»). Регулярки fipi служат только для подсчёта покрытия
открытого банка при самопроверке, тексты банка сюда не попадают.
Чертежи: svg_geom (планиметрия), своя клетка со стрелками (векторы), своя косоугольная
проекция (многогранники и тела вращения).
"""
import math
from fractions import Fraction as F
from itertools import combinations, permutations, product

from mathlib import (R, SUB, TRIPLES, _svg, BLUE, RED, INK, GRID, finite, nice, num, pcard, pick, plural, proto,
                     same, sp, svg_geom, tnum)

# ================================================================ паспорта КИМ

_KIM = {
    1: dict(level='Б', points=1, minutes=3, kes=['7.1'], kt=['КТ 9', 'КТ 10', 'КТ 11'], answer='число'),
    2: dict(level='Б', points=1, minutes=3, kes=['7.5'], kt=['КТ 12'], answer='число'),
    3: dict(level='Б', points=1, minutes=3, kes=['7.3', '7.4'], kt=['КТ 9', 'КТ 10', 'КТ 11'], answer='число'),
    4: dict(level='Б', points=1, minutes=2, kes=['6.2'], kt=['КТ 8'], answer='число'),
    5: dict(level='П', points=1, minutes=7, kes=['6.2'], kt=['КТ 8'], answer='число'),
}


def kim(n, style, kes=None):
    d = dict(_KIM[n])
    d['style'] = style
    if kes:
        d['kes'] = list(kes)
    return d


DEG = 'Ответ дайте в градусах.'
KIM_DEG = 'Краткое условие с чертежом, буквенные обозначения, «Ответ дайте в градусах.»; ответ — целое число градусов.'
KIM_LEN = 'Краткое условие с чертежом, буквенные обозначения, «Найдите …»; ответ — целое число или конечная десятичная дробь.'

# ================================================================ общие помощники


def fa(s):
    """Строка ответа → float."""
    return float(str(s).replace(',', '.'))


def ok(x, a, eps=1e-6):
    """Число x (float/sympy) совпадает с ответом a (строка из num)."""
    return abs(float(x) - fa(a)) < eps


def dist(A, B):
    return math.hypot(A[0] - B[0], A[1] - B[1])


def vang(A, O, B):
    """Угол AOB в градусах по координатам."""
    u = (A[0] - O[0], A[1] - O[1])
    v = (B[0] - O[0], B[1] - O[1])
    c = (u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def onc(d, rad=1.0, c=(0.0, 0.0)):
    """Точка окружности под углом d градусов."""
    t = math.radians(d)
    return (c[0] + rad * math.cos(t), c[1] + rad * math.sin(t))


def area(pts):
    """Площадь многоугольника (формула шнурования)."""
    s = 0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def foot(P, A, B):
    """Основание перпендикуляра из P на прямую AB."""
    ax, ay = B[0] - A[0], B[1] - A[1]
    t = ((P[0] - A[0]) * ax + (P[1] - A[1]) * ay) / (ax * ax + ay * ay)
    return (A[0] + t * ax, A[1] + t * ay)


def lerp(A, B, t):
    return (A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t)


def cross_lines(A, B, C, D):
    """Точка пересечения прямых AB и CD."""
    x1, y1, x2, y2, x3, y3, x4, y4 = *A, *B, *C, *D
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / den
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / den
    return (px, py)


def tri_by_angles(a, b, base=1.0):
    """Треугольник XYZ с углами a при X и b при Y (градусы), XY на оси абсцисс."""
    X = (0.0, 0.0)
    Y = (base, 0.0)
    c = 180 - a - b
    xz = base * math.sin(math.radians(b)) / math.sin(math.radians(c))
    Z = (xz * math.cos(math.radians(a)), xz * math.sin(math.radians(a)))
    return X, Y, Z


def isqrt_exact(n):
    k = math.isqrt(n)
    return k if k * k == n else None


def root(n):
    """√n в условии: целое, если n — точный квадрат."""
    k = isqrt_exact(n)
    return str(k) if k is not None else f'√{n}'


def fig(pts, polys=(), segs=(), circles=(), marks=(), right=(), hide=(), width=260):
    """svg_geom + значки прямого угла (right=[('A', 'C', 'B')] — прямой угол ACB); hide — точки без подписи."""
    pts = {k: (float(x), float(y)) for k, (x, y) in pts.items()}
    xs = [p[0] for p in pts.values()]
    ys = [p[1] for p in pts.values()]
    span = max(max(xs) - min(xs), max(ys) - min(ys), *[2 * c[1] for c in circles] or [0])
    s = span * 0.055
    show = [k for k in pts if k not in hide]
    extra = []
    aux = iter('123456789')
    for a, v, b in right:
        V = pts[v]
        ua = (pts[a][0] - V[0], pts[a][1] - V[1])
        ub = (pts[b][0] - V[0], pts[b][1] - V[1])
        na, nb = math.hypot(*ua), math.hypot(*ub)
        ua, ub = (ua[0] / na, ua[1] / na), (ub[0] / nb, ub[1] / nb)
        n1, n2, n3 = next(aux), next(aux), next(aux)
        pts[n1] = (V[0] + ua[0] * s, V[1] + ua[1] * s)
        pts[n2] = (V[0] + (ua[0] + ub[0]) * s, V[1] + (ua[1] + ub[1]) * s)
        pts[n3] = (V[0] + ub[0] * s, V[1] + ub[1] * s)
        extra += [n1 + n2, n2 + n3]
    circles = [((float(c[0]), float(c[1])), float(rr)) for c, rr in circles]
    return svg_geom(pts, polys, list(segs) + extra, circles, labels=show, marks=marks, width=width)


def sides(t):
    """Имена сторон треугольника t='ABC': {'AB', 'BC', 'AC'} в порядке букв t."""
    return {frozenset(p): (p[0] + p[1] if t.index(p[0]) < t.index(p[1]) else p[1] + p[0]) for p in combinations(t, 2)}


def sd(t, a, b):
    """Сторона ab треугольника/многоугольника t в «правильном» порядке букв."""
    return a + b if t.index(a) < t.index(b) else b + a


DECS = [F(k, 10) for k in range(1, 10)] + [F(1, 4), F(3, 4), F(1, 20) * 3, F(1, 20) * 7, F(1, 20) * 9, F(1, 20) * 11,
                                          F(1, 20) * 13, F(1, 20) * 17, F(1, 25) * 6, F(1, 25) * 7, F(1, 25) * 24,
                                          F(1, 8) * 3, F(5, 8), F(7, 8)]

TRI = ('ABC', 'ABC', 'ABC', 'ABC', 'KLM', 'MNK', 'PQR', 'DEF', 'SKT')
TRI_NOAUX = ('ABC', 'ABC', 'ABC', 'KLN', 'PQR', 'EFG', 'STU')   # без H, M, D, O
QUAD = ('ABCD', 'ABCD', 'ABCD', 'KLMN', 'MNPQ', 'PQRS')


# ================================================================ №1. Планиметрия

@proto('ep01-right-ratio', 'ege-prof', 1, 'Прямоугольный треугольник: синус, косинус или тангенс по двум сторонам',
       invariant='Недостающую сторону прямоугольного треугольника находим по теореме Пифагора, затем берём '
                 'отношение сторон по определению синуса, косинуса или тангенса острого угла.',
       varies='Буквы вершин, какая сторона дана (часто катет в виде корня), какая функция и какого угла спрашивается.',
       answer_rule='sin = противолежащий катет / гипотенуза, cos = прилежащий / гипотенуза, tg = противолежащий / прилежащий.',
       fipi=r'угол C равен 90 ?°.*Найдите (sin|cos|tg)',
       mistakes=['путают противолежащий и прилежащий катет', 'делят на катет вместо гипотенузы',
                 'забывают извлечь корень из разности квадратов'],
       maxdec=2, svg=True,
       kim=kim(1, 'Как в КИМ: «В треугольнике ABC угол C равен 90°, AB = …, BC = √… . Найдите cos A.»; '
                  'катет задан корнем, ответ — конечная десятичная дробь.'))
def gen_ep01_right_ratio(r):
    t = r.choice(TRI)
    Z = t[2]
    W, V = (t[0], t[1]) if r.random() < 0.5 else (t[1], t[0])
    hyp, adj, opp = sd(t, t[0], t[1]), sd(t, W, Z), sd(t, V, Z)
    fn = r.choice(['sin', 'cos', 'sin', 'cos', 'tg'])
    if fn in ('sin', 'cos'):
        c = r.choice([2, 4, 5, 5, 8, 10, 10, 10, 20, 20, 25, 40, 50])
        m = r.randint(1, c - 1)
        ans = F(m, c)
        if not nice(ans, 2) or not F(1, 10) <= ans <= F(19, 20):
            return None
        s = c * c - m * m
        if isqrt_exact(s) is not None and r.random() < 0.8:
            return None
        hyp2 = c * c
        if fn == 'sin':       # sin W = opp/hyp; дан прилежащий катет
            known, known2 = adj, s
            lens = dict(opp=m * m, adj=s)
        else:                 # cos W = adj/hyp; дан противолежащий катет
            known, known2 = opp, s
            lens = dict(opp=s, adj=m * m)
        htxt = str(c)
    else:
        p, q = r.randint(1, 15), r.randint(1, 15)
        ans = F(p, q)
        if p == q or not nice(ans, 2):
            return None
        hyp2 = p * p + q * q
        htxt = root(hyp2)
        if r.random() < 0.5:
            known, known2 = adj, q * q
        else:
            known, known2 = opp, p * p
        lens = dict(opp=p * p, adj=q * q)
    ktxt = root(known2)
    ask = f'{fn} {W}'
    q = pick(r,
             f'В треугольнике {t} угол {Z} прямой, {known} = {ktxt}, {hyp} = {htxt}. Найдите {ask}.',
             f'Дан треугольник {t}, в котором ∠{Z} = 90°, {known} = {ktxt}, {hyp} = {htxt}. Найдите {ask}.',
             f'В прямоугольном треугольнике {t} с прямым углом {Z} гипотенуза {hyp} равна {htxt}, катет {known} равен {ktxt}. Найдите {ask}.',
             f'Угол {Z} треугольника {t} прямой. Известно, что {hyp} = {htxt} и {known} = {ktxt}. Найдите {ask}.')
    miss = adj if known == opp else opp
    e = (f'{miss} = √({hyp}² − {known}²) = {root(hyp2 - known2)}; '
         f'{ask} = {tnum(ans)}.')
    adj_l, opp_l = math.sqrt(lens['adj']), math.sqrt(lens['opp'])
    sgn = r.choice([1, -1])
    pts = {Z: (0, 0), W: (sgn * adj_l, 0), V: (0, opp_l)}
    svg = fig(pts, polys=[t], right=[(W, Z, V)])

    def chk():
        other = sp.sqrt(R(hyp2) - R(known2))          # недостающий катет
        a_len = other if known == opp else sp.sqrt(known2)
        o_len = other if known == adj else sp.sqrt(known2)
        Wp, Zp, Vp = (float(a_len), 0.0), (0.0, 0.0), (0.0, float(o_len))
        ang = math.radians(vang(Vp, Wp, Zp))
        val = {'sin': math.sin, 'cos': math.cos, 'tg': math.tan}[fn](ang)
        return ok(val, num(ans)) and ok(dist(Wp, Vp) ** 2, str(hyp2), 1e-6)
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-right-side', 'ege-prof', 1, 'Прямоугольный треугольник: сторона по синусу, косинусу или тангенсу',
       invariant='Из определения синуса, косинуса или тангенса острого угла выражаем нужную сторону через известную.',
       varies='Буквы, функция и её значение (десятичная дробь), какая сторона известна и какую ищем.',
       answer_rule='Катет = гипотенуза · sin (cos); гипотенуза = катет : sin (cos); катет = другой катет · tg.',
       fipi=r'угол C равен 90 ?°.*(sin|cos|tg) ?[AB] ?=',
       mistakes=['умножают вместо деления (и наоборот)', 'берут прилежащий катет вместо противолежащего'],
       maxdec=1, svg=True,
       kim=kim(1, 'Как в КИМ: прямоугольный треугольник с буквами, значение sin/cos/tg дано десятичной дробью, «Найдите AC.»'))
def gen_ep01_right_side(r):
    t = r.choice(TRI)
    Z = t[2]
    W, V = (t[0], t[1]) if r.random() < 0.5 else (t[1], t[0])
    hyp, adj, opp = sd(t, t[0], t[1]), sd(t, W, Z), sd(t, V, Z)
    fn = r.choice(['sin', 'cos', 'tg'])
    if fn == 'tg':
        val = r.choice(DECS + [F(3, 2), F(2), F(5, 2), F(3), F(4), F(5, 4), F(12, 5), F(4, 3)])
        if val.denominator == 3:
            return None
        known, want = (adj, opp) if r.random() < 0.5 else (opp, adj)
    else:
        val = r.choice(DECS)
        pair = {'sin': (hyp, opp), 'cos': (hyp, adj)}[fn]
        known, want = pair if r.random() < 0.55 else pair[::-1]
    L = r.randint(2, 60)
    if fn == 'sin':
        ans = L * val if known == hyp else F(L) / val
    elif fn == 'cos':
        ans = L * val if known == hyp else F(L) / val
    else:
        ans = L * val if known == adj else F(L) / val
    if not nice(ans, 1) or ans > 200 or ans == L:
        return None
    q = pick(r,
             f'В треугольнике {t} угол {Z} прямой, {fn} {W} = {tnum(val)}, {known} = {L}. Найдите {want}.',
             f'Дан треугольник {t} с прямым углом {Z}; {known} = {L}, {fn} {W} = {tnum(val)}. Найдите {want}.',
             f'В прямоугольном треугольнике {t} с прямым углом {Z} известно, что {known} = {L} и {fn} {W} = {tnum(val)}. Найдите {want}.',
             f'Угол {Z} треугольника {t} равен 90°. Известно, что {fn} {W} = {tnum(val)}, а {known} = {L}. Найдите {want}.')
    rel = {'sin': f'sin {W} = {opp} / {hyp}', 'cos': f'cos {W} = {adj} / {hyp}', 'tg': f'tg {W} = {opp} / {adj}'}[fn]
    e = f'{rel}, отсюда {want} = {tnum(ans)}.'
    th = {'sin': math.asin, 'cos': math.acos, 'tg': math.atan}[fn](float(val))
    sgn = r.choice([1, -1])
    pts = {Z: (0, 0), W: (sgn * math.cos(th), 0), V: (0, math.sin(th))}
    svg = fig(pts, polys=[t], right=[(W, Z, V)])

    def chk():
        # единичная гипотенуза с углом θ при W, затем масштаб по известной стороне
        th_ = {'sin': math.asin, 'cos': math.acos, 'tg': math.atan}[fn](float(val))
        Wp, Zp, Vp = (0.0, 0.0), (math.cos(th_), 0.0), (math.cos(th_), math.sin(th_))
        L_ = {hyp: dist(Wp, Vp), adj: dist(Wp, Zp), opp: dist(Zp, Vp)}
        k = L / L_[known]
        return ok(k * L_[want], num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


CEV = {'h': ('высота', 'высотой', 'H'), 'm': ('медиана', 'медианой', 'M'), 'b': ('биссектриса', 'биссектрисой', 'D')}


@proto('ep01-right-cevian', 'ege-prof', 1, 'Угол между высотой, медианой и биссектрисой из вершины прямого угла',
       invariant='Углы высоты, медианы и биссектрисы с катетом выражаются через острый угол: медиана равна половине '
                 'гипотенузы (равнобедренный треугольник), биссектриса делит прямой угол пополам, высота даёт угол 90° − β.',
       varies='Острый угол, какая пара отрезков (высота и медиана, высота и биссектриса, биссектриса и медиана), '
              'прямая или обратная постановка (по углу между отрезками найти острый угол).',
       answer_rule='Высота и медиана: |90° − 2β|; биссектриса с высотой или медианой: |45° − β|.',
       fipi=r'между (высотой|биссектрисой)[^.]*(медианой|биссектрисой)',
       mistakes=['не замечают, что медиана к гипотенузе равна её половине', 'берут угол с другим катетом'],
       svg=True, kim=kim(1, KIM_DEG + ' Отрезки проведены «из вершины прямого угла», как в КИМ.'))
def gen_ep01_right_cevian(r):
    t = r.choice(TRI_NOAUX)
    X_, Y_, Z = t
    pair = r.choice([('h', 'm'), ('h', 'm'), ('h', 'b'), ('b', 'm')])
    n1, n2 = CEV[pair[0]], CEV[pair[1]]
    s1, s2 = Z + n1[2], Z + n2[2]
    mode = r.choice(['direct', 'direct', 'reverse'])
    if mode == 'direct':
        beta = r.randint(8, 82)
        if beta == 45:
            return None
        ans = abs(90 - 2 * beta) if pair == ('h', 'm') else abs(45 - beta)
        q = pick(r,
                 f'В прямоугольном треугольнике {t} с прямым углом {Z} угол {Y_} равен {beta}°. Из вершины {Z} проведены '
                 f'{n1[0]} {s1} и {n2[0]} {s2}. Найдите угол между ними. {DEG}',
                 f'Угол {Y_} прямоугольного треугольника {t} (∠{Z} = 90°) равен {beta}°. Отрезки {s1} и {s2} — '
                 f'{n1[0]} и {n2[0]} этого треугольника. Найдите угол {n1[2]}{Z}{n2[2]}. {DEG}',
                 f'В треугольнике {t} угол {Z} прямой, угол {Y_} равен {beta}°, {s1} — {n1[0]}, {s2} — {n2[0]}. '
                 f'Найдите угол {n1[2]}{Z}{n2[2]}. {DEG}')
        e = ('Медиана к гипотенузе равна её половине, поэтому ∠' + f'{s2[1]}{Z}{Y_} = {beta}°; '
             if 'm' in pair else '') + f'искомый угол равен {ans}°.'
    else:
        big = r.random() < 0.6
        if pair == ('h', 'm'):
            phi = r.randrange(4, 82, 2)
            ans = 45 + phi // 2 if big else 45 - phi // 2
        else:
            phi = r.randint(3, 42)
            ans = 45 + phi if big else 45 - phi
        which = 'больший' if big else 'меньший'
        q = pick(r,
                 f'В прямоугольном треугольнике {t} из вершины прямого угла {Z} проведены {n1[0]} {s1} и {n2[0]} {s2}. '
                 f'Угол между ними равен {phi}°. Найдите {which} острый угол треугольника {t}. {DEG}',
                 f'{n1[0].capitalize()} {s1} и {n2[0]} {s2} прямоугольного треугольника {t} выходят из вершины '
                 f'прямого угла {Z} и образуют угол {phi}°. Найдите {which} из острых углов этого треугольника. {DEG}')
        e = f'Если β — острый угол, то угол между отрезками равен {"|90° − 2β|" if pair == ("h", "m") else "|45° − β|"}; β = {ans}°.'
        beta = ans if r.random() < 0.5 else 90 - ans
    b_ = math.radians(min(65, max(25, beta)))   # чертёж схематичный, без вырожденных углов
    P = {Z: (0.0, 0.0), Y_: (0.0, 1.0), X_: (math.tan(b_), 0.0)}
    H = foot(P[Z], P[X_], P[Y_])
    M = lerp(P[X_], P[Y_], 0.5)
    D = cross_lines(P[Z], (1.0, 1.0), P[X_], P[Y_])
    aux = {'H': H, 'M': M, 'D': D}
    P[n1[2]], P[n2[2]] = aux[n1[2]], aux[n2[2]]
    svg = fig(P, polys=[t], segs=[s1, s2], right=[(X_, Z, Y_)])

    def chk():
        def build(bdeg):
            bb = math.radians(bdeg)
            Zp, Yp, Xp = (0.0, 0.0), (0.0, 1.0), (math.tan(bb), 0.0)
            pts = {'H': foot(Zp, Xp, Yp), 'M': lerp(Xp, Yp, 0.5), 'D': cross_lines(Zp, (1.0, 1.0), Xp, Yp)}
            return vang(pts[n1[2]], Zp, pts[n2[2]]), vang(Zp, Yp, Xp), vang(Zp, Xp, Yp)
        if mode == 'direct':
            return ok(build(beta)[0], num(ans))
        # обратная задача: при найденном остром угле угол между отрезками равен данному
        between, angY, angX = build(ans)
        return ok(between, str(phi)) and ((ans >= 45) == big or ans == 45)
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-iso-ext', 'ege-prof', 1, 'Равнобедренный треугольник: углы и внешний угол',
       invariant='Углы при основании равнобедренного треугольника равны; внешний угол равен 180° минус смежный '
                 'внутренний (или сумме двух внутренних, не смежных с ним).',
       varies='Буквы, что дано (угол при вершине, угол при основании, внешний угол при основании или при вершине) '
              'и что ищем, запись равенства сторон.',
       answer_rule='Угол при основании (180° − γ)/2; внешний при основании 90° + γ/2; внешний при вершине 2α.',
       fipi=r'стороны A C и B C равны',
       mistakes=['принимают внешний угол за внутренний', 'путают вершину и основание равнобедренного треугольника'],
       svg=True, kim=kim(1, KIM_DEG + ' Равенство сторон записано словами, внешний угол — «угол CBD внешний» или «внешний угол при вершине».'))
def gen_ep01_iso_ext(r):
    t = r.choice(TRI_NOAUX)
    A, B, C = t          # AC = BC, вершина C, основание AB
    mode = r.choice(['ext_base', 'apex_from_ext', 'base_from_ext_apex', 'ext_apex_from_base', 'apex_from_base'])
    eq = pick(r, f'стороны {sd(t, A, C)} и {sd(t, B, C)} равны', f'{sd(t, A, C)} = {sd(t, B, C)}')
    D = 'D' if 'D' not in t else 'K'
    if mode == 'ext_base':
        g = r.randrange(10, 172, 2)
        ans = 90 + g // 2
        V = r.choice([A, B])
        if r.random() < 0.5:
            q = f'В треугольнике {t} {eq}, угол {C} равен {g}°. Найдите внешний угол при вершине {V}. {DEG}'
        else:
            q = f'В треугольнике {t} {eq}, угол {C} равен {g}°, угол {C}{V}{D} — внешний. Найдите угол {C}{V}{D}. {DEG}'
        e = f'∠{V} = (180° − {g}°) : 2 = {(180 - g) // 2}°, внешний угол равен 180° − {(180 - g) // 2}° = {ans}°.'
        gamma = g
    elif mode == 'apex_from_ext':
        ex = r.randint(92, 178)
        ans = 2 * ex - 180
        V = r.choice([A, B])
        q = pick(r, f'В треугольнике {t} {eq}. Внешний угол при вершине {V} равен {ex}°. Найдите угол {C}. {DEG}',
                 f'Треугольник {t} равнобедренный с основанием {sd(t, A, B)}. Внешний угол при вершине {V} равен {ex}°. Найдите угол {C}. {DEG}')
        e = f'∠{V} = 180° − {ex}° = {180 - ex}°, ∠{C} = 180° − 2 · {180 - ex}° = {ans}°.'
        gamma = ans
    elif mode == 'base_from_ext_apex':
        ex = r.randrange(10, 178, 2)
        ans = ex // 2
        V = r.choice([A, B])
        q = pick(r, f'В треугольнике {t} {eq}. Внешний угол при вершине {C} равен {ex}°. Найдите угол {V}. {DEG}',
                 f'Треугольник {t} равнобедренный с основанием {sd(t, A, B)}. Внешний угол при вершине {C} равен {ex}°. Найдите угол {V}. {DEG}')
        e = f'Внешний угол при {C} равен сумме углов {A} и {B}, а они равны: {ex}° : 2 = {ans}°.'
        gamma = 180 - ex
    elif mode == 'ext_apex_from_base':
        al = r.randint(5, 88)
        ans = 2 * al
        V = r.choice([A, B])
        q = pick(r, f'В треугольнике {t} {eq}, угол {V} равен {al}°. Найдите внешний угол при вершине {C}. {DEG}',
                 f'Треугольник {t} равнобедренный с основанием {sd(t, A, B)}, угол {V} равен {al}°. Найдите внешний угол при вершине {C}. {DEG}')
        e = f'Внешний угол при {C} равен {al}° + {al}° = {ans}°.'
        gamma = 180 - 2 * al
    else:
        al = r.randint(5, 88)
        ans = 180 - 2 * al
        V = r.choice([A, B])
        q = pick(r, f'В треугольнике {t} {eq}, угол {V} равен {al}°. Найдите угол {C}. {DEG}',
                 f'В равнобедренном треугольнике {t} с основанием {sd(t, A, B)} угол {V} равен {al}°. Найдите угол {C}. {DEG}')
        e = f'∠{A} = ∠{B} = {al}°, ∠{C} = 180° − 2 · {al}° = {ans}°.'
        gamma = ans
    gd = min(150, max(30, gamma))
    h = 1 / math.tan(math.radians(gd / 2))
    P = {A: (-1, 0), B: (1, 0), C: (0, h)}
    segs = []
    if mode in ('ext_base', 'apex_from_ext'):
        P[D] = (-1.7, 0) if V == A else (1.7, 0)
        segs = [V + D]
    elif mode in ('base_from_ext_apex', 'ext_apex_from_base'):
        P[D] = (0.55, h + 0.55 * h)                 # продолжение стороны AC за точку C
        segs = [C + D]
    svg = fig(P, polys=[t], segs=segs, hide=[D] if 'ext' not in mode else [])

    def chk():
        gg = gamma
        hh = 1 / math.tan(math.radians(gg / 2))
        Ap, Bp, Cp = (-1.0, 0.0), (1.0, 0.0), (0.0, hh)
        if abs(dist(Ap, Cp) - dist(Bp, Cp)) > 1e-9:
            return False
        Vp = Ap if V == A else Bp
        base_ang = vang(Cp, Vp, Bp if V == A else Ap)
        ext_base = 180 - base_ang
        apex = vang(Ap, Cp, Bp)
        ext_apex = 180 - apex
        if mode == 'ext_base':
            return ok(apex, str(g)) and ok(ext_base, num(ans))
        if mode == 'apex_from_ext':
            return ok(ext_base, str(ex)) and ok(apex, num(ans))
        if mode == 'base_from_ext_apex':
            return ok(ext_apex, str(ex)) and ok(base_ang, num(ans))
        if mode == 'ext_apex_from_base':
            return ok(base_ang, str(al)) and ok(ext_apex, num(ans))
        return ok(base_ang, str(al)) and ok(apex, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-iso-trig', 'ege-prof', 1, 'Равнобедренный треугольник: стороны через косинус, синус или тангенс угла при основании',
       invariant='Высота к основанию равнобедренного треугольника делит его на два равных прямоугольных треугольника; '
                 'в одном из них применяем определение cos, sin или tg угла при основании.',
       varies='Буквы, функция и её значение, какие стороны даны и что ищем (боковая сторона, основание, высота).',
       answer_rule='AC = (AB/2) : cos A; AB = 2·AC·cos A; CH = AC·sin A; CH = (AB/2)·tg A.',
       fipi=r'A C = B C.*(cos|sin|tg) A',
       mistakes=['берут всё основание вместо его половины', 'забывают удвоить половину основания'],
       maxdec=1, svg=True, kim=kim(1, KIM_LEN + ' Значение функции угла — десятичная дробь.'))
def gen_ep01_iso_trig(r):
    t = r.choice(TRI_NOAUX)
    A, B, C = t
    H = 'H'
    base, lat = sd(t, A, B), sd(t, A, C)
    V = r.choice([A, B])
    mode = r.choice(['lat_from_base', 'base_from_lat', 'h_from_lat', 'h_from_base'])
    eq = pick(r, f'{sd(t, A, C)} = {sd(t, B, C)}', f'стороны {sd(t, A, C)} и {sd(t, B, C)} равны')
    if mode in ('lat_from_base', 'base_from_lat'):
        fn, val = 'cos', r.choice(DECS)
    elif mode == 'h_from_lat':
        fn, val = 'sin', r.choice(DECS)
    else:
        fn, val = 'tg', r.choice(DECS + [F(3, 2), F(2), F(5, 2), F(3), F(4), F(5, 4), F(12, 5)])
    L = r.randint(2, 60)
    if mode == 'lat_from_base':
        ans, given, want = F(L, 2) / val, base, lat
    elif mode == 'base_from_lat':
        ans, given, want = 2 * L * val, lat, base
    elif mode == 'h_from_lat':
        ans, given, want = L * val, lat, f'{C}{H}'
    else:
        ans, given, want = F(L, 2) * val, base, f'{C}{H}'
    if not nice(ans, 1) or ans > 300 or ans < 1:
        return None
    hnote = f', {C}{H} — высота' if want == f'{C}{H}' else ''
    q = pick(r,
             f'В треугольнике {t} {eq}, {given} = {L}, {fn} {V} = {tnum(val)}{hnote}. Найдите {want}.',
             f'В равнобедренном треугольнике {t} с основанием {base} известно, что {given} = {L} и {fn} {V} = {tnum(val)}{hnote}. Найдите {want}.',
             f'Треугольник {t} равнобедренный, {eq}. Известно, что {fn} {V} = {tnum(val)}, {given} = {L}{hnote}. Найдите {want}.')
    e = {'lat_from_base': f'{A}{H} = {base} : 2 = {tnum(F(L, 2))}, {lat} = {A}{H} : cos {V} = {tnum(ans)}.',
         'base_from_lat': f'{A}{H} = {lat} · cos {V} = {tnum(L * val)}, {base} = 2 · {A}{H} = {tnum(ans)}.',
         'h_from_lat': f'{C}{H} = {lat} · sin {V} = {tnum(ans)}.',
         'h_from_base': f'{C}{H} = ({base} : 2) · tg {V} = {tnum(ans)}.'}[mode]
    th = {'sin': math.asin, 'cos': math.acos, 'tg': math.atan}[fn](float(val))
    thd = min(math.radians(70), max(math.radians(25), th))
    P = {A: (-1, 0), B: (1, 0), C: (0, math.tan(thd)), H: (0, 0)}
    segs = [C + H] if want == f'{C}{H}' else []
    svg = fig(P, polys=[t], segs=segs, right=[(B, H, C)] if segs else [], hide=[] if segs else [H])

    def chk():
        th_ = {'sin': math.asin, 'cos': math.acos, 'tg': math.atan}[fn](float(val))
        Ap, Bp, Cp = (-1.0, 0.0), (1.0, 0.0), (0.0, math.tan(th_))
        Hp = foot(Cp, Ap, Bp)
        L_ = {base: dist(Ap, Bp), lat: dist(Ap, Cp), f'{C}{H}': dist(Cp, Hp)}
        return ok(L / L_[given] * L_[want], num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-tri-ext', 'ege-prof', 1, 'Треугольник: сумма углов и внешний угол',
       invariant='Сумма углов треугольника 180°; внешний угол равен сумме двух внутренних, не смежных с ним.',
       varies='Буквы, какие углы даны (два внутренних, внутренний и внешний), какой угол ищем.',
       answer_rule='Внешний при C = A + B; B = (внешний при C) − A; B = 180° − A − C.',
       fipi=r'треугольнике A B C угол A равен.*угол B равен|внешний угол при вершине C',
       mistakes=['считают внешний угол равным 180° минус сумма', 'путают смежный и несмежный углы'],
       svg=True, kim=kim(1, KIM_DEG))
def gen_ep01_tri_ext(r):
    t = r.choice(TRI)
    idx = [0, 1, 2]
    r.shuffle(idx)
    X_, Y_, Z_ = (t[i] for i in idx)   # ищем угол/внешний при Z_
    mode = r.choice(['ext_from_two', 'ext_from_two', 'angle_from_ext', 'third'])
    a, b = r.randint(12, 110), r.randint(12, 110)
    if a + b > 168:
        return None
    ang = {X_: a, Y_: b, Z_: 180 - a - b}
    if mode == 'ext_from_two':
        ans = a + b
        q = pick(r, f'В треугольнике {t} угол {X_} равен {a}°, угол {Y_} равен {b}°. Найдите внешний угол при вершине {Z_}. {DEG}',
                 f'В треугольнике {t} известны углы: ∠{X_} = {a}°, ∠{Y_} = {b}°. Найдите внешний угол треугольника при вершине {Z_}. {DEG}')
        e = f'Внешний угол при {Z_} равен ∠{X_} + ∠{Y_} = {ans}°.'
    elif mode == 'angle_from_ext':
        ex = a + b
        ans = b
        q = pick(r, f'Внешний угол треугольника {t} при вершине {Z_} равен {ex}°, угол {X_} равен {a}°. Найдите угол {Y_}. {DEG}',
                 f'В треугольнике {t} угол {X_} равен {a}°, а внешний угол при вершине {Z_} равен {ex}°. Найдите угол {Y_}. {DEG}')
        e = f'∠{Y_} = {ex}° − {a}° = {ans}°.'
    else:
        ans = 180 - a - b
        q = pick(r, f'В треугольнике {t} угол {X_} равен {a}°, угол {Y_} равен {b}°. Найдите угол {Z_}. {DEG}',
                 f'Два угла треугольника {t} равны: ∠{X_} = {a}°, ∠{Y_} = {b}°. Найдите третий угол. {DEG}')
        e = f'∠{Z_} = 180° − {a}° − {b}° = {ans}°.'
    pa, pb, pc = tri_by_angles(ang[t[0]], ang[t[1]])
    P = {t[0]: pa, t[1]: pb, t[2]: pc}
    segs, hide = [], []
    if mode != 'third':
        others = [c for c in t if c != Z_]
        Dn = 'D' if 'D' not in t else 'K'
        far = P[others[0]]
        P[Dn] = lerp(far, P[Z_], 1.45)
        segs, hide = [Z_ + Dn], [Dn]
    svg = fig(P, polys=[t], segs=segs, hide=hide)

    def chk():
        Xp, Yp, Zp = tri_by_angles(a, b, 3.0)
        ext = 180 - vang(Xp, Zp, Yp)
        if mode == 'ext_from_two':
            return ok(ext, num(ans))
        if mode == 'angle_from_ext':
            return ok(vang(Xp, Yp, Zp), num(ans)) and ok(ext, str(a + b))
        return ok(vang(Xp, Zp, Yp), num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-bisector', 'ege-prof', 1, 'Треугольник с биссектрисой: углы',
       invariant='Биссектриса делит угол пополам; дальше — сумма углов треугольника и внешний угол треугольника ABD или ADC.',
       varies='Какой угол дан (C или B) и какая половина угла A (CAD или BAD), что ищем (угол B, ADB, ADC).',
       answer_rule='B = 180° − C − 2x; ADB = C + x; ADC = 180° − C − x = B + x.',
       fipi=r'A D — биссектриса',
       mistakes=['забывают удвоить половину угла A', 'находят ADC вместо ADB'],
       svg=True, kim=kim(1, KIM_DEG + ' «AD — биссектриса, угол CAD равен …», как в демоверсии.'))
def gen_ep01_bisector(r):
    t = r.choice(('ABC', 'ABC', 'ABC', 'KLM', 'PQR', 'MNP', 'EFK'))
    A, B, C = t
    D = 'D' if 'D' not in t else 'T'
    x = r.randint(10, 50)
    c = r.randint(20, 120)
    b = 180 - 2 * x - c
    if b < 15:
        return None
    half = r.choice([f'{C}{A}{D}', f'{B}{A}{D}'])
    mode = r.choice(['B', 'ADB', 'ADC', 'ADC_fromB'])
    bis = f'{A}{D} — биссектриса'
    if mode == 'B':
        ans = b
        q = pick(r, f'В треугольнике {t} угол {C} равен {c}°, {bis}, угол {half} равен {x}°. Найдите угол {B}. {DEG}',
                 f'В треугольнике {t} проведена биссектриса {A}{D}. Известно, что ∠{C} = {c}°, ∠{half} = {x}°. Найдите угол {B}. {DEG}')
        e = f'∠{A} = 2 · {x}° = {2 * x}°, ∠{B} = 180° − {c}° − {2 * x}° = {ans}°.'
    elif mode == 'ADB':
        ans = c + x
        q = pick(r, f'В треугольнике {t} угол {C} равен {c}°, {bis}, угол {half} равен {x}°. Найдите угол {A}{D}{B}. {DEG}',
                 f'Биссектриса {A}{D} треугольника {t} образует со стороной {sd(t, A, C) if half[0] == C else sd(t, A, B)} угол {x}°. Угол {C} равен {c}°. Найдите угол {A}{D}{B}. {DEG}')
        e = f'∠{A}{D}{B} — внешний угол треугольника {A}{D}{C}: {c}° + {x}° = {ans}°.'
    elif mode == 'ADC':
        ans = 180 - c - x
        q = pick(r, f'В треугольнике {t} угол {C} равен {c}°, {bis}, угол {half} равен {x}°. Найдите угол {A}{D}{C}. {DEG}',
                 f'В треугольнике {t} проведена биссектриса {A}{D}. Известно, что ∠{C} = {c}°, ∠{half} = {x}°. Найдите угол {A}{D}{C}. {DEG}')
        e = f'В треугольнике {A}{D}{C}: 180° − {c}° − {x}° = {ans}°.'
    else:
        ans = b + x
        q = pick(r, f'В треугольнике {t} угол {B} равен {b}°, {bis}, угол {half} равен {x}°. Найдите угол {A}{D}{C}. {DEG}',
                 f'В треугольнике {t} проведена биссектриса {A}{D}. Известно, что ∠{B} = {b}°, ∠{half} = {x}°. Найдите угол {A}{D}{C}. {DEG}')
        e = f'∠{A}{D}{C} — внешний угол треугольника {A}{B}{D}: {b}° + {x}° = {ans}°.'
    pa, pb, pc = tri_by_angles(2 * x, b)
    ratio = dist(pa, pb) / (dist(pa, pb) + dist(pa, pc))
    P = {A: pa, B: pb, C: pc, D: lerp(pb, pc, ratio)}
    svg = fig(P, polys=[t], segs=[A + D])

    def chk():
        # строим треугольник по углам A = 2x и C, точку D ищем как пересечение луча-биссектрисы с BC
        Ap = (0.0, 0.0)
        Bp = (1.0, 0.0)
        Cp = tri_by_angles(2 * x, 180 - 2 * x - c)[2]
        Dp = cross_lines(Ap, onc(x), Bp, Cp)
        vals = {'B': vang(Ap, Bp, Cp), 'ADB': vang(Ap, Dp, Bp), 'ADC': vang(Ap, Dp, Cp), 'ADC_fromB': vang(Ap, Dp, Cp)}
        return ok(vang(Ap, Cp, Bp), str(c)) and ok(vals[mode], num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk
