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
from itertools import combinations, product

from mathlib import (R, SUB, TRIPLES, _svg, BLUE, RED, INK, GRID, finite, nice, num, par, pcard, pick, plural, proto, raz,
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
        if na < 1e-9 or nb < 1e-9:
            continue
        ua, ub = (ua[0] / na, ua[1] / na), (ub[0] / nb, ub[1] / nb)
        n1, n2, n3 = next(aux), next(aux), next(aux)
        pts[n1] = (V[0] + ua[0] * s, V[1] + ua[1] * s)
        pts[n2] = (V[0] + (ua[0] + ub[0]) * s, V[1] + (ua[1] + ub[1]) * s)
        pts[n3] = (V[0] + ub[0] * s, V[1] + ub[1] * s)
        extra += [n1 + n2, n2 + n3]
    circles = [((float(c[0]), float(c[1])), float(rr)) for c, rr in circles]
    return svg_geom(pts, polys, list(segs) + extra, circles, labels=show, marks=marks, width=width)


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
    AC, BC = sd(t, A, C), sd(t, B, C)
    D = 'D' if 'D' not in t else 'K'
    angC = f'{A}{C}{B}'
    ang3 = {A: f'{C}{A}{B}', B: f'{A}{B}{C}'}
    if mode == 'ext_base':
        g = r.randrange(10, 172, 2)
        ans = 90 + g // 2
        V = r.choice([A, B])
        q = pick(r, f'Треугольник {t} равнобедренный, {AC} = {BC}, угол при вершине {C} равен {g}°. '
                    f'Найдите внешний угол этого треугольника при вершине {V}. {DEG}',
                 f'У треугольника {t} стороны {AC} и {BC} равны, а ∠{C} = {g}°. Точка {D} лежит на продолжении '
                 f'стороны {sd(t, A, B)} за точку {V}. Найдите угол {C}{V}{D}. {DEG}')
        e = f'∠{V} = (180° − {g}°) : 2 = {(180 - g) // 2}°, внешний угол равен 180° − {(180 - g) // 2}° = {ans}°.'
        gamma = g
    elif mode == 'apex_from_ext':
        ex = r.randint(92, 178)
        ans = 2 * ex - 180
        V = r.choice([A, B])
        q = pick(r, f'Треугольник {t} равнобедренный с основанием {sd(t, A, B)}. Угол, смежный с углом {V} этого '
                    f'треугольника, равен {ex}°. Найдите угол {angC}. {DEG}',
                 f'Боковые стороны {AC} и {BC} треугольника {t} равны. Точка {D} лежит на продолжении основания '
                 f'{sd(t, A, B)} за точку {V}, ∠{C}{V}{D} = {ex}°. Найдите угол {angC}. {DEG}')
        e = f'∠{V} = 180° − {ex}° = {180 - ex}°, ∠{C} = 180° − 2 · {180 - ex}° = {ans}°.'
        gamma = ans
    elif mode == 'base_from_ext_apex':
        ex = r.randrange(10, 178, 2)
        ans = ex // 2
        V = r.choice([A, B])
        q = pick(r, f'Треугольник {t} равнобедренный с основанием {sd(t, A, B)}. Внешний угол треугольника при его '
                    f'вершине {C} равен {ex}°. Найдите угол {ang3[V]}. {DEG}',
                 f'Боковые стороны {AC} и {BC} треугольника {t} равны. Угол, смежный с углом {C}, равен {ex}°. '
                 f'Найдите угол {ang3[V]}. {DEG}')
        e = f'Внешний угол при {C} равен сумме углов {A} и {B}, а они равны: {ex}° : 2 = {ans}°.'
        gamma = 180 - ex
    elif mode == 'ext_apex_from_base':
        al = r.randint(5, 88)
        ans = 2 * al
        V = r.choice([A, B])
        q = pick(r, f'Треугольник {t} равнобедренный с основанием {sd(t, A, B)}, ∠{V} = {al}°. Найдите внешний угол '
                    f'треугольника при его вершине {C}. {DEG}',
                 f'Боковые стороны {AC} и {BC} треугольника {t} равны, угол {V} равен {al}°. Найдите угол, смежный '
                 f'с углом {C}. {DEG}')
        e = f'Внешний угол при {C} равен {al}° + {al}° = {ans}°.'
        gamma = 180 - 2 * al
    else:
        al = r.randint(5, 88)
        ans = 180 - 2 * al
        V = r.choice([A, B])
        q = pick(r, f'Боковые стороны {AC} и {BC} треугольника {t} равны, ∠{ang3[V]} = {al}°. Найдите угол {angC}. {DEG}',
                 f'В равнобедренном треугольнике {t} с основанием {sd(t, A, B)} угол при основании равен {al}°. '
                 f'Найдите угол {angC}, лежащий против основания. {DEG}')
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
    a3 = {v: ''.join(w for w in t if w != v)[0] + v + ''.join(w for w in t if w != v)[1] for v in t}
    if mode == 'ext_from_two':
        ans = a + b
        q = pick(r, f'Два угла треугольника {t} известны: ∠{X_} = {a}°, ∠{Y_} = {b}°. Найдите внешний угол '
                    f'треугольника при третьей вершине. {DEG}',
                 f'В треугольнике {t} ∠{a3[X_]} = {a}°, ∠{a3[Y_]} = {b}°. Найдите угол, смежный с углом {a3[Z_]}. {DEG}')
        e = f'Внешний угол при {Z_} равен ∠{X_} + ∠{Y_} = {ans}°.'
    elif mode == 'angle_from_ext':
        ex = a + b
        ans = b
        q = pick(r, f'Угол, смежный с углом {a3[Z_]} треугольника {t}, равен {ex}°, а ∠{a3[X_]} = {a}°. Найдите угол {a3[Y_]}. {DEG}',
                 f'Известно, что ∠{a3[X_]} = {a}°, а внешний угол треугольника {t} при вершине {Z_} равен {ex}°. '
                 f'Найдите величину угла {a3[Y_]}. {DEG}')
        e = f'∠{Y_} = {ex}° − {a}° = {ans}°.'
    else:
        ans = 180 - a - b
        q = pick(r, f'В треугольнике {t} ∠{a3[X_]} = {a}°, ∠{a3[Y_]} = {b}°. Найдите угол {a3[Z_]}. {DEG}',
                 f'Два угла треугольника {t} равны {a}° и {b}°. Найдите третий угол этого треугольника. {DEG}')
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
    side = sd(t, A, C) if half[0] == C else sd(t, A, B)
    given = c if mode != 'ADC_fromB' else b
    G = C if mode != 'ADC_fromB' else B
    intro = pick(r, f'В треугольнике {t} проведена биссектриса {A}{D}. Известно, что ∠{G} = {given}°, ∠{half} = {x}°.',
                 f'Отрезок {A}{D} — биссектриса треугольника {t}, ∠{half} = {x}°, ∠{G} = {given}°.',
                 f'Биссектриса {A}{D} треугольника {t} образует со стороной {side} угол {x}°, а угол {G} равен {given}°.')
    if mode == 'B':
        ans = b
        q = f'{intro} Найдите угол {B}. {DEG}'
        e = f'∠{A} = 2 · {x}° = {2 * x}°, ∠{B} = 180° − {c}° − {2 * x}° = {ans}°.'
    elif mode == 'ADB':
        ans = c + x
        q = f'{intro} Найдите угол {A}{D}{B}. {DEG}'
        e = f'∠{A}{D}{B} — внешний угол треугольника {A}{D}{C}: {c}° + {x}° = {ans}°.'
    elif mode == 'ADC':
        ans = 180 - c - x
        q = f'{intro} Найдите угол {A}{D}{C}. {DEG}'
        e = f'В треугольнике {A}{D}{C}: 180° − {c}° − {x}° = {ans}°.'
    else:
        ans = b + x
        q = f'{intro} Найдите угол {A}{D}{C}. {DEG}'
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


@proto('ep01-area-heights', 'ege-prof', 1, 'Две стороны и высоты: площадь треугольника или параллелограмма двумя способами',
       invariant='Площадь равна произведению стороны на проведённую к ней высоту (для треугольника — половине), '
                 'поэтому высоты обратно пропорциональны сторонам.',
       varies='Треугольник или параллелограмм, длины сторон, какая высота дана, к какой стороне ищем высоту, буквы.',
       answer_rule='h₁ · a₁ = h₂ · a₂, отсюда искомая высота = (сторона · данная высота) : другая сторона.',
       fipi=r'(стороны треугольника|стороны параллелограмма) равны[^.]*\. высота',
       mistakes=['думают, что к большей стороне проведена большая высота', 'путают, к какой стороне дана высота'],
       maxdec=1, svg=True, kim=kim(1, KIM_LEN))
def gen_ep01_area_heights(r):
    kind = r.choice(['tri', 'par'])
    s1 = r.randint(6, 40)
    s2 = r.randint(s1 + 1, min(2 * s1, 48))
    to_small = r.random() < 0.5          # True: дана высота к большей стороне, ищем к меньшей
    if to_small:
        h_given = r.randint(2, s1 - 1)
        ans = F(s2 * h_given, s1)
    else:
        h_given = r.randint(2, min(s2 - 1, 40))
        if h_given >= s2:
            return None
        ans = F(s1 * h_given, s2)
    if not nice(ans, 1) or ans < 1:
        return None
    sin_t = (h_given / s1) if to_small else (h_given / s2)
    if not 0.3 <= sin_t <= 0.95:
        return None
    if kind == 'tri':
        t = r.choice(('ABC', 'ABC', 'KLM', 'PQR', 'DEF'))
        A, B, C = t
        AB, BC = sd(t, A, B), sd(t, B, C)
        Hs = ('H', 'K') if 'K' not in t else ('H', 'T')
        # AB = s1 (меньшая), BC = s2 (большая); высота к BC из A, к AB из C
        if to_small:
            q = pick(r, f'Стороны {AB} и {BC} треугольника {t} равны {s1} и {s2} соответственно. Высота {A}{Hs[0]}, проведённая '
                        f'к стороне {BC}, равна {h_given}. Найдите высоту {C}{Hs[1]}, проведённую к стороне {AB}.',
                     f'Длины двух сторон треугольника равны {s1} и {s2}, а высота, проведённая к большей из них, равна '
                     f'{h_given}. Найдите высоту, проведённую к меньшей из этих двух сторон.')
        else:
            q = pick(r, f'Стороны {AB} и {BC} треугольника {t} равны {s1} и {s2} соответственно. Высота {C}{Hs[1]}, проведённая '
                        f'к стороне {AB}, равна {h_given}. Найдите высоту {A}{Hs[0]}, проведённую к стороне {BC}.',
                     f'Длины двух сторон треугольника равны {s1} и {s2}, а высота, проведённая к меньшей из них, равна '
                     f'{h_given}. Найдите высоту, проведённую к большей из этих двух сторон.')
        e = f'2S = {s2} · h₁ = {s1} · h₂, искомая высота равна {tnum(ans)}.'
        th = math.asin(min(0.94, max(0.5, sin_t)))
        Bp, Cp = (0.0, 0.0), (float(s2), 0.0)
        Ap = (s1 * math.cos(th), s1 * math.sin(th))
        P = {A: Ap, B: Bp, C: Cp, Hs[0]: foot(Ap, Bp, Cp), Hs[1]: foot(Cp, Bp, Ap)}
        segs = [A + Hs[0], C + Hs[1], B + Hs[1], C + Hs[0]]      # с продолжениями сторон, если основание высоты вне стороны
        svg = fig(P, polys=[t], segs=segs, right=[(C if dist(P[Hs[0]], P[C]) > 1e-6 else B, Hs[0], A), (B, Hs[1], C)])
    else:
        t = r.choice(('ABCD', 'ABCD', 'KLMN', 'PQRS'))
        A, B, C, D = t
        AB, AD = sd(t, A, B), sd(t, A, D)
        if to_small:
            q = pick(r, f'В параллелограмме {t} стороны {AB} и {AD} равны {s1} и {s2}. Высота, проведённая к стороне {AD}, '
                        f'равна {h_given}. Найдите высоту параллелограмма, проведённую к стороне {AB}.',
                     f'Длины сторон параллелограмма равны {s1} и {s2}, а высота, проведённая к большей стороне, равна '
                     f'{h_given}. Найдите высоту, проведённую к меньшей стороне.')
        else:
            q = pick(r, f'В параллелограмме {t} стороны {AB} и {AD} равны {s1} и {s2}. Высота, проведённая к стороне {AB}, '
                        f'равна {h_given}. Найдите высоту параллелограмма, проведённую к стороне {AD}.',
                     f'Длины сторон параллелограмма равны {s1} и {s2}, а высота, проведённая к меньшей стороне, равна '
                     f'{h_given}. Найдите высоту, проведённую к большей стороне.')
        e = f'S = {s2} · h₁ = {s1} · h₂, искомая высота равна {tnum(ans)}.'
        th = math.asin(min(0.94, max(0.5, sin_t)))
        Ap, Dp = (0.0, 0.0), (float(s2), 0.0)
        Bp = (s1 * math.cos(th), s1 * math.sin(th))
        Cp = (Bp[0] + s2, Bp[1])
        P = {A: Ap, B: Bp, C: Cp, D: Dp, 'H': foot(Bp, Ap, Dp)}
        svg = fig(P, polys=[t], segs=[B + 'H'], right=[(D, 'H', B)])

    def chk():
        th_ = math.asin(sin_t)
        O, Pp = (0.0, 0.0), (float(s2), 0.0)
        Q = (s1 * math.cos(th_), s1 * math.sin(th_))
        h_to_s2 = dist(Q, foot(Q, O, Pp))       # высота к большей стороне
        h_to_s1 = dist(Pp, foot(Pp, O, Q))      # высота к меньшей стороне
        if to_small:
            return ok(h_to_s2, str(h_given)) and ok(h_to_s1, num(ans))
        return ok(h_to_s1, str(h_given)) and ok(h_to_s2, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


# середина стороны параллелограмма ABCD: фигура → доля площади
PAR_MID = {
    'AD': {'ABE': F(1, 4), 'CDE': F(1, 4), 'BCE': F(1, 2), 'BCDE': F(3, 4), 'ABCE': F(3, 4)},
    'BC': {'ABE': F(1, 4), 'CDE': F(1, 4), 'ADE': F(1, 2), 'ABED': F(3, 4), 'AECD': F(3, 4)},
}


@proto('ep01-par-area', 'ege-prof', 1, 'Параллелограмм и середина стороны: площади частей',
       invariant='Треугольник с вершиной в середине стороны и основанием на противоположной стороне занимает половину '
                 'площади параллелограмма; треугольник у вершины — четверть; трапеция — три четверти.',
       varies='Буквы, на какой стороне середина, какая часть (треугольник или трапеция), прямая или обратная постановка.',
       answer_rule='S(угл. треугольника) = S/4, S(треугольника на всю сторону) = S/2, S(трапеции) = 3S/4.',
       fipi=r'параллелограмма A B C D равна.*середина стороны',
       mistakes=['считают трапецию половиной параллелограмма', 'путают, какой треугольник отрезан'],
       svg=True, kim=kim(1, KIM_LEN + ' Как в КИМ: «Площадь параллелограмма … Точка E — середина стороны … Найдите площадь трапеции …».'))
def gen_ep01_par_area(r):
    t = r.choice(QUAD)
    E = 'E' if 'E' not in t else 'T'
    side = r.choice(['AD', 'AD', 'BC'])
    shape = r.choice(list(PAR_MID[side]))
    part = PAR_MID[side][shape]
    L = dict(zip('ABCD', t))
    L['E'] = E
    nm = ''.join(L[c] for c in shape)
    what = ('трапеции' if len(shape) == 4 else 'треугольника') + ' ' + nm
    sname = L[side[0]] + L[side[1]]
    reverse = r.random() < 0.35
    if not reverse:
        S = r.randrange(8, 161, 4)
        ans = S * part
        q = pick(r, f'Точка {E} — середина стороны {sname} параллелограмма {t}, площадь которого равна {S}. Найдите площадь {what}.',
                 f'Площадь параллелограмма {t} равна {S}. На стороне {sname} отмечена её середина {E}. Найдите площадь {what}.',
                 f'В параллелограмме {t} площадью {S} точка {E} делит сторону {sname} пополам. Найдите площадь {what}.')
        e = f'S({nm}) = {part.numerator}/{part.denominator} · {S} = {tnum(ans)}.'
    else:
        ans_S = r.randrange(8, 161, 4)
        given = ans_S * part
        ans = F(ans_S)
        q = pick(r, f'Точка {E} — середина стороны {sname} параллелограмма {t}. Площадь {what} равна {tnum(given)}. '
                    f'Найдите площадь параллелограмма {t}.',
                 f'В параллелограмме {t} точка {E} делит сторону {sname} пополам, площадь {what} равна {tnum(given)}. '
                 f'Найдите площадь параллелограмма.')
        e = f'S({nm}) составляет {part.numerator}/{part.denominator} площади параллелограмма: S = {tnum(ans)}.'
    if not nice(ans, 1):
        return None
    k = r.choice([0.5, 0.8, 1.1])
    base = {'A': (0.0, 0.0), 'D': (4.0, 0.0), 'B': (k, 2.2), 'C': (4.0 + k, 2.2)}
    base['E'] = lerp(base[side[0]], base[side[1]], 0.5)
    P = {L[c]: base[c] for c in 'ABCDE'}
    svg = fig(P, polys=[t, nm])

    def chk():
        # произвольный косой параллелограмм, площадь — по формуле шнурования
        Ab, Db, Bb = (0.0, 0.0), (7.0, 0.0), (2.3, 3.1)
        pts = {'A': Ab, 'B': Bb, 'C': (Bb[0] + 7.0, Bb[1]), 'D': Db}
        pts['E'] = lerp(pts[side[0]], pts[side[1]], 0.5)
        ratio = area([pts[c] for c in shape]) / area([pts[c] for c in 'ABCD'])
        if reverse:
            return ok(float(given) / ratio, num(ans))
        return ok(S * ratio, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-par-angles', 'ege-prof', 1, 'Углы параллелограмма и трапеции',
       invariant='Противоположные углы параллелограмма равны, а углы, прилежащие к одной стороне (к боковой стороне '
                 'трапеции), в сумме дают 180°.',
       varies='Параллелограмм или трапеция (в том числе равнобедренная), что дано: сумма двух углов, разность, один угол.',
       answer_rule='Сумма двух углов параллелограмма s ≠ 180° → это равные углы по s/2, остальные 180° − s/2; '
                   'разность d → углы 90° ± d/2; в трапеции угол при боковой стороне 180° − α.',
       fipi=r'^(?!.*Докажите).*(сумма двух углов параллелограмма|углов параллелограмма|трапеци\w*[^.]*угол [A-Z] равен)',
       mistakes=['складывают соседние углы как противоположные', 'в равнобедренной трапеции путают, какие углы равны'],
       svg=True, kim=kim(1, KIM_DEG))
def gen_ep01_par_angles(r):
    t = r.choice(QUAD)
    A, B, C, D = t
    mode = r.choice(['par_sum', 'par_diff', 'trap_leg', 'trap_iso'])
    if mode == 'par_sum':
        s = r.randrange(20, 340, 2)
        if s == 180:
            return None
        big = r.random() < 0.5
        each = s // 2
        ans = 180 - each
        q = pick(r, f'Сумма двух углов параллелограмма равна {s}°. Найдите один из двух оставшихся углов. {DEG}',
                 f'В параллелограмме {t} сумма углов {A} и {C} равна {s}°. Найдите угол {B}. {DEG}',
                 f'Два угла параллелограмма {t} в сумме составляют {s}°. Найдите величину каждого из двух других углов. {DEG}')
        e = f'Два угла с суммой {s}° ≠ 180° — противоположные, каждый {each}°; остальные по 180° − {each}° = {ans}°.'
        theta = each
    elif mode == 'par_diff':
        d = r.randrange(4, 170, 2)
        big = r.random() < 0.6
        ans = 90 + d // 2 if big else 90 - d // 2
        which = 'больший' if big else 'меньший'
        q = pick(r, f'Один из углов параллелограмма на {d}° больше другого. Найдите {which} угол параллелограмма. {DEG}',
                 f'Разность двух углов параллелограмма {t} равна {d}°. Найдите {which} из углов параллелограмма. {DEG}')
        e = f'Неравные углы параллелограмма в сумме 180°: x + (x + {d}°) = 180°, углы {90 - d // 2}° и {90 + d // 2}°.'
        theta = 90 - d // 2
    elif mode == 'trap_leg':
        al = r.randint(20, 160)
        if al == 90:
            return None
        ans = 180 - al
        q = pick(r, f'У трапеции {t} стороны {sd(t, A, D)} и {sd(t, B, C)} параллельны, а угол {A} равен {al}°. Найдите угол {B}. {DEG}',
                 f'Основания трапеции {t} — {sd(t, A, D)} и {sd(t, B, C)}, ∠{B}{A}{D} = {al}°. Найдите угол {A}{B}{C}. {DEG}')
        e = f'Углы при боковой стороне {sd(t, A, B)} в сумме 180°: 180° − {al}° = {ans}°.'
        theta = al
    else:
        al = r.randint(20, 88)
        ask = r.choice([B, C, D])
        a4 = {B: f'{A}{B}{C}', C: f'{B}{C}{D}', D: f'{A}{D}{C}'}
        ans = al if ask == D else 180 - al
        q = pick(r, f'Трапеция {t} с основаниями {sd(t, A, D)} и {sd(t, B, C)} равнобедренная, ∠{B}{A}{D} = {al}°. '
                    f'Найдите угол {a4[ask]}. {DEG}',
                 f'Трапеция {t} равнобедренная, {sd(t, A, D)} и {sd(t, B, C)} — её основания, ∠{B}{A}{D} = {al}°. Найдите угол {a4[ask]}. {DEG}')
        e = f'В равнобедренной трапеции углы при основании равны, а углы при боковой стороне в сумме 180°: {ans}°.'
        theta = al
    th = math.radians(min(150, max(30, theta)))
    if mode in ('par_sum', 'par_diff'):
        base = [(0, 0), (1.3 * math.cos(th), 1.3 * math.sin(th)), (1.3 * math.cos(th) + 3, 1.3 * math.sin(th)), (3, 0)]
    elif mode == 'trap_leg':
        h = 1.3
        x1 = h / math.tan(th)
        base = [(0, 0), (x1, h), (x1 + 1.4 + (0 if x1 > 0 else 0), h), (3.4, 0)]
    else:
        h = 1.3
        x1 = h / math.tan(th)
        base = [(0, 0), (x1, h), (4 - x1, h), (4, 0)]
    P = {n: p for n, p in zip(t, base)}
    svg = fig(P, polys=[t])

    def chk():
        if mode == 'par_sum':
            # перебираем острый угол параллелограмма, углы — по координатам
            found = set()
            for th_ in range(1, 180):
                a = math.radians(th_)
                pts = [(0, 0), (math.cos(a), math.sin(a)), (math.cos(a) + 2, math.sin(a)), (2, 0)]
                angs = [vang(pts[i - 1], pts[i], pts[(i + 1) % 4]) for i in range(4)]
                for i, j in combinations(range(4), 2):
                    if abs(angs[i] + angs[j] - s) < 1e-6:
                        rest = [angs[k] for k in range(4) if k not in (i, j)]
                        found.update(round(x, 6) for x in rest)
            return found == {float(ans)}
        if mode == 'par_diff':
            for th_ in range(1, 180):
                a = math.radians(th_)
                pts = [(0, 0), (math.cos(a), math.sin(a)), (math.cos(a) + 2, math.sin(a)), (2, 0)]
                angs = sorted(vang(pts[i - 1], pts[i], pts[(i + 1) % 4]) for i in range(4))
                if abs(angs[-1] - angs[0] - d) < 1e-6:
                    return ok(angs[-1] if big else angs[0], num(ans))
            return False
        a = math.radians(al)
        pts = {A: (0.0, 0.0), D: (5.0, 0.0), B: (math.cos(a), math.sin(a))}
        pts[C] = (5.0 - math.cos(a), math.sin(a)) if mode == 'trap_iso' else (math.cos(a) + 1.7, math.sin(a))
        angs = {A: vang(pts[B], pts[A], pts[D]), B: vang(pts[A], pts[B], pts[C]), C: vang(pts[B], pts[C], pts[D]),
                D: vang(pts[C], pts[D], pts[A])}
        return ok(angs[B if mode == 'trap_leg' else ask], num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


RHOMB = [(3, 4), (4, 3), (5, 12), (12, 5), (8, 15), (15, 8), (6, 8), (8, 6), (9, 12), (12, 9), (7, 24), (24, 7),
         (20, 21), (21, 20), (10, 24), (24, 10), (12, 16), (16, 12), (15, 20), (20, 15)]


@proto('ep01-rhombus', 'ege-prof', 1, 'Ромб: диагонали, сторона и площадь',
       invariant='Диагонали ромба перпендикулярны и делятся точкой пересечения пополам; площадь ромба равна половине '
                 'произведения диагоналей, сторона — гипотенуза треугольника с катетами-полудиагоналями.',
       varies='Что дано (две диагонали; сторона и диагональ; площадь и диагональ) и что ищем, буквы.',
       answer_rule='S = d₁d₂/2; a² = (d₁/2)² + (d₂/2)².',
       fipi=r'диагонали ромба|ромба равн',
       mistakes=['берут целые диагонали вместо половин в теореме Пифагора', 'забывают разделить произведение диагоналей на 2'],
       svg=True, kim=kim(1, KIM_LEN))
def gen_ep01_rhombus(r):
    t = r.choice(QUAD)
    A, B, C, D = t
    O = 'O'
    p, q_ = r.choice(RHOMB)
    k = r.choice([1, 1, 2, 3])
    p, q_ = p * k, q_ * k
    d1, d2 = 2 * p, 2 * q_                     # AC = d1, BD = d2
    a = isqrt_exact(p * p + q_ * q_)
    if a is None or d1 > 60 or d2 > 60:
        return None
    AC, BD = f'{A}{C}', f'{B}{D}'
    mode = r.choice(['side', 'area', 'diag_from_side', 'diag_from_area'])
    if mode == 'side':
        ans = a
        q = pick(r, f'Ромб {t} имеет диагонали длиной {d1} и {d2}. Найдите длину его стороны.',
                 f'В ромбе {t} диагональ {AC} равна {d1}, а диагональ {BD} равна {d2}. Найдите длину стороны {sd(t, A, B)}.')
        e = f'Половины диагоналей {p} и {q_}, сторона √({p}² + {q_}²) = {a}.'
    elif mode == 'area':
        ans = d1 * d2 // 2
        q = pick(r, f'Ромб {t} имеет диагонали длиной {d1} и {d2}. Найдите его площадь.',
                 f'В ромбе {t} диагонали {AC} и {BD} равны соответственно {d1} и {d2}. Найдите площадь ромба {t}.')
        e = f'S = {d1} · {d2} : 2 = {ans}.'
    elif mode == 'diag_from_side':
        ans = d2
        q = pick(r, f'В ромбе {t} сторона {sd(t, A, B)} = {a}, диагональ {AC} = {d1}. Найдите длину диагонали {BD}.',
                 f'Ромб {t} со стороной {a} имеет диагональ {AC} длиной {d1}. Найдите длину диагонали {BD}.')
        e = f'{O}{B} = √({a}² − {p}²) = {q_}, {BD} = {d2}.'
    else:
        S = d1 * d2 // 2
        ans = d2
        q = pick(r, f'В ромбе {t} площадью {S} диагональ {AC} имеет длину {d1}. Найдите длину диагонали {BD}.',
                 f'Ромб {t} имеет площадь {S}, его диагональ {AC} равна {d1}. Найдите длину диагонали {BD}.')
        e = f'{BD} = 2 · {S} : {d1} = {d2}.'
    P = {A: (-p, 0), B: (0, q_), C: (p, 0), D: (0, -q_), O: (0, 0)}
    svg = fig(P, polys=[t], segs=[A + C, B + D], hide=[O] if mode in ('area',) else [])

    def chk():
        pts = {A: (-p, 0.0), B: (0.0, q_), C: (p, 0.0), D: (0.0, -q_)}
        side = dist(pts[A], pts[B])
        if not all(ok(dist(pts[t[i]], pts[t[(i + 1) % 4]]), str(a)) for i in range(4)):
            return False
        val = {'side': side, 'area': area([pts[c] for c in t]), 'diag_from_side': dist(pts[B], pts[D]),
               'diag_from_area': dist(pts[B], pts[D])}[mode]
        return ok(val, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-midline-area', 'ege-prof', 1, 'Треугольник, отсечённый средней линией (прямой, параллельной стороне): площади',
       invariant='Прямая, параллельная стороне, отсекает подобный треугольник; площади относятся как квадрат '
                 'коэффициента подобия (для средней линии — 1 : 4).',
       varies='Средняя линия или отрезок, делящий стороны в заданном отношении; ищем площадь треугольника, трапеции или '
              'исходного треугольника; буквы.',
       answer_rule='S(малого) = k²·S, S(трапеции) = (1 − k²)·S; для средней линии k = 1/2.',
       fipi=r'средняя линия, параллельная стороне',
       mistakes=['считают, что площадь уменьшается вдвое, а не вчетверо', 'забывают вычесть малый треугольник для трапеции'],
       svg=True, kim=kim(1, KIM_LEN + ' Как в КИМ: «DE — средняя линия, параллельная стороне AB. Найдите площадь трапеции ABED».'))
def gen_ep01_midline_area(r):
    t = r.choice(('ABC', 'ABC', 'KLM', 'PQR'))
    A, B, C = t
    M, N = r.choice([('D', 'E'), ('M', 'N'), ('P', 'Q'), ('E', 'F')])
    if M in t or N in t:
        return None
    ratio = r.choice([None, None, None, (1, 2), (2, 1), (1, 3), (3, 1), (2, 3), (3, 2), (1, 4), (3, 7)])
    k = F(1, 2) if ratio is None else F(ratio[0], ratio[0] + ratio[1])
    small = k * k
    target = r.choice(['tri', 'trap'])
    part = small if target == 'tri' else 1 - small
    trap = f'{A}{B}{N}{M}'
    what = f'треугольника {C}{M}{N}' if target == 'tri' else f'трапеции {trap}'
    if ratio is None:
        intro = pick(r, f'Точки {M} и {N} — середины сторон {sd(t, A, C)} и {sd(t, B, C)} треугольника {t}',
                     f'В треугольнике {t} отрезок {M}{N} соединяет середины сторон {sd(t, A, C)} и {sd(t, B, C)}')
    else:
        intro = pick(r, f'На сторонах {sd(t, A, C)} и {sd(t, B, C)} треугольника {t} отмечены точки {M} и {N} так, что '
                        f'{M}{N} ∥ {sd(t, A, B)} и {C}{M} : {M}{A} = {ratio[0]} : {ratio[1]}',
                     f'Прямая, параллельная стороне {sd(t, A, B)} треугольника {t}, пересекает стороны {sd(t, A, C)} и '
                     f'{sd(t, B, C)} в точках {M} и {N}, причём {C}{M} : {M}{A} = {ratio[0]} : {ratio[1]}')
    reverse = r.random() < 0.35
    if not reverse:
        S = r.randint(4, 200)
        ans = S * part
        if not nice(ans, 1) or ans.denominator > 2:
            return None
        q = pick(r, f'{intro}. Треугольник {t} имеет площадь {S}. Найдите площадь {what}.',
                 f'{intro}, а площадь треугольника {t} равна {S}. Чему равна площадь {what}?')
        e = f'Коэффициент подобия {tnum(k) if finite(k) else f"{k.numerator}/{k.denominator}"}, S({C}{M}{N}) = {small.numerator}/{small.denominator} · S; ответ {tnum(ans)}.'
    else:
        given = r.randint(2, 120)
        ans = given / part
        if not nice(ans, 1) or ans.denominator > 2 or ans > 1000:
            return None
        q = pick(r, f'{intro}. Площадь {what} равна {given}. Найдите площадь треугольника {t}.',
                 f'{intro}, а площадь {what} составляет {given}. Найдите площадь всего треугольника {t}.')
        e = f'Площадь {what} составляет {part.numerator}/{part.denominator} площади треугольника: {tnum(ans)}.'
    kk = float(k)
    P = {A: (0, 0), B: (4, 0), C: (1.4, 3)}
    P[M] = lerp(P[C], P[A], kk)
    P[N] = lerp(P[C], P[B], kk)
    svg = fig(P, polys=[t], segs=[M + N])

    def chk():
        Ap, Bp, Cp = (0.0, 0.0), (5.0, 0.0), (1.7, 2.9)
        Mp = lerp(Cp, Ap, float(k))
        Np = cross_lines(Mp, (Mp[0] + 1, Mp[1]), Bp, Cp)      # прямая через M параллельно AB
        whole = area([Ap, Bp, Cp])
        piece = area([Cp, Mp, Np]) if target == 'tri' else area([Ap, Bp, Np, Mp])
        if reverse:
            return ok(given * whole / piece, num(ans))
        return ok(S * piece / whole, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-trap-midline', 'ege-prof', 1, 'Средняя линия трапеции и отрезки, на которые её делит диагональ',
       invariant='Средняя линия трапеции равна полусумме оснований; диагональ делит её на две средние линии '
                 'треугольников, равные половинам оснований.',
       varies='Что дано (основания, средняя линия и основание, отрезки средней линии) и что ищем, буквы.',
       answer_rule='m = (a + b)/2; отрезки средней линии a/2 и b/2; основание = 2m − другое основание.',
       fipi=r'(средн\w* лини\w*[^.]*трапеци|трапеци[^.]*средн\w* лини)',
       mistakes=['берут полусумму там, где нужна половина одного основания', 'путают больший и меньший отрезки'],
       maxdec=1, svg=True, kim=kim(1, KIM_LEN + ' Как в демоверсии: «Основания трапеции равны … Найдите больший из отрезков …».'))
def gen_ep01_trap_midline(r):
    t = r.choice(QUAD)
    A, B, C, D = t
    a = r.randint(2, 40)
    b = r.randint(a + 1, 60)
    mode = r.choice(['seg', 'seg', 'mid', 'base', 'base_from_segs'])
    if mode == 'seg':
        big = r.random() < 0.6
        ans = F(b, 2) if big else F(a, 2)
        which = 'больший' if big else 'меньший'
        q = pick(r, f'Основания трапеции равны {a} и {b}. Одна из диагоналей трапеции разбивает её среднюю линию на два '
                    f'отрезка. Найдите {which} из них.',
                 f'В трапеции {t} основания {sd(t, B, C)} и {sd(t, A, D)} равны {a} и {b}. Диагональ {A}{C} пересекает среднюю '
                 f'линию трапеции. Найдите {which} из получившихся отрезков средней линии.')
        e = f'Отрезки средней линии — средние линии треугольников, они равны {tnum(F(a, 2))} и {tnum(F(b, 2))}.'
    elif mode == 'mid':
        ans = F(a + b, 2)
        q = pick(r, f'Основания трапеции {t} равны {a} и {b}. Найдите среднюю линию трапеции.',
                 f'В трапеции {t} основание {sd(t, B, C)} равно {a}, основание {sd(t, A, D)} равно {b}. Найдите длину средней линии этой трапеции.')
        e = f'm = ({a} + {b}) : 2 = {tnum(ans)}.'
    elif mode == 'base':
        m = F(a + b, 2)
        if m.denominator != 1:
            return None
        big = r.random() < 0.5
        ans = F(b if big else a)
        known = a if big else b
        q = pick(r, f'Средняя линия трапеции равна {m}, а одно из её оснований равно {known}. Найдите другое основание трапеции.',
                 f'В трапеции {t} средняя линия равна {m}, основание {sd(t, B, C) if big else sd(t, A, D)} равно {known}. '
                 f'Найдите основание {sd(t, A, D) if big else sd(t, B, C)}.')
        e = f'Другое основание: 2 · {m} − {known} = {ans}.'
    else:
        x, y = F(a, 2), F(b, 2)
        big = r.random() < 0.5
        ans = F(b if big else a)
        which = 'большее' if big else 'меньшее'
        q = pick(r, f'Диагональ трапеции делит её среднюю линию на отрезки {tnum(x)} и {tnum(y)}. Найдите {which} из оснований трапеции.',
                 f'Средняя линия трапеции {t} пересекается с диагональю {A}{C}, которая разбивает её на два отрезка: '
                 f'{tnum(x)} и {tnum(y)}. Найдите длину {"большего" if big else "меньшего"} основания трапеции.')
        e = f'Каждый отрезок — половина основания: {which} основание равно {ans}.'
    if not nice(ans, 1):
        return None
    sc = 4.0 / b
    P = {A: (0, 0), D: (b * sc, 0), B: (0.9, 1.8), C: (0.9 + a * sc, 1.8)}
    Mn, Nn = 'M', 'N'
    if Mn in t or Nn in t:
        Mn, Nn = 'E', 'F'
    P[Mn] = lerp(P[A], P[B], 0.5)
    P[Nn] = lerp(P[D], P[C], 0.5)
    segs = [Mn + Nn] + ([A + C] if mode in ('seg', 'base_from_segs') else [])
    svg = fig(P, polys=[t], segs=segs, hide=[Mn, Nn])

    def chk():
        Ap, Dp, Bp = (0.0, 0.0), (float(b), 0.0), (1.3, 2.1)
        Cp = (1.3 + a, 2.1)
        Mp, Np = lerp(Ap, Bp, 0.5), lerp(Dp, Cp, 0.5)
        K = cross_lines(Mp, Np, Ap, Cp)
        segs_ = sorted([dist(Mp, K), dist(K, Np)])
        if mode == 'seg':
            return ok(segs_[1] if big else segs_[0], num(ans))
        if mode == 'mid':
            return ok(dist(Mp, Np), num(ans))
        if mode == 'base':
            return ok(dist(Mp, Np), str(m)) and ok(dist(Bp, Cp) if not big else dist(Ap, Dp), num(ans)) or \
                ok(dist(Mp, Np), str(m)) and ok(dist(Ap, Dp) if big else dist(Bp, Cp), num(ans))
        return ok(2 * (segs_[1] if big else segs_[0]), num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


ISO_TRAP = [(3, 4, 5), (4, 3, 5), (5, 12, 13), (12, 5, 13), (8, 15, 17), (15, 8, 17), (6, 8, 10), (8, 6, 10), (7, 24, 25),
            (9, 12, 15), (12, 9, 15), (20, 21, 29), (21, 20, 29)]


@proto('ep01-trap-iso', 'ege-prof', 1, 'Равнобедренная трапеция: высота, боковая сторона, площадь',
       invariant='Высота из вершины меньшего основания отсекает прямоугольный треугольник с катетом (b − a)/2; '
                 'дальше теорема Пифагора (или угол 45°) и площадь трапеции (a + b)/2 · h.',
       varies='Основания, боковая сторона или высота, острый угол 45°, что ищем (высота, боковая сторона, площадь), буквы.',
       answer_rule='(b − a)/2 и h — катеты, боковая сторона — гипотенуза; S = (a + b)/2 · h; при угле 45° h = (b − a)/2.',
       fipi=r'Основания равнобедренной трапеции|В равнобедренной трапеции[^.]*основания[^.]*равны[^.]*\. Найдите (высоту|площадь|боковую)',
       mistakes=['берут разность оснований вместо её половины', 'находят среднюю линию вместо площади'],
       svg=True, kim=kim(1, KIM_LEN))
def gen_ep01_trap_iso(r):
    t = r.choice(QUAD)
    A, B, C, D = t
    mode = r.choice(['h', 'area', 'leg', 'area45'])
    if mode == 'area45':
        a = r.randint(2, 30)
        x = r.randint(1, 15)
        b = a + 2 * x
        h = x
        ans = F(a + b, 2) * h
        q = pick(r, f'В равнобедренной трапеции острый угол равен 45°, а основания имеют длины {a} и {b}. Найдите площадь этой трапеции.',
                 f'В равнобедренной трапеции {t} основания {sd(t, B, C)} = {a} и {sd(t, A, D)} = {b}, угол {A} равен 45°. '
                 f'Найдите площадь трапеции.')
        e = f'h = ({b} − {a}) : 2 = {h}; S = ({a} + {b}) : 2 · {h} = {tnum(ans)}.'
        leg2 = 2 * x * x
    else:
        px, hy, c = r.choice(ISO_TRAP)
        k = r.choice([1, 1, 2, 3])
        px, hy, c = px * k, hy * k, c * k
        a = r.randint(2, 30)
        b = a + 2 * px
        h = hy
        leg2 = c * c
        if b > 80:
            return None
        if mode == 'h':
            ans = F(h)
            q = pick(r, f'В равнобедренной трапеции боковая сторона имеет длину {c}, а основания — {a} и {b}. Найдите высоту этой трапеции.',
                     f'В равнобедренной трапеции {t} основания {sd(t, B, C)} и {sd(t, A, D)} равны {a} и {b}, а боковая '
                     f'сторона {sd(t, A, B)} равна {c}. Найдите высоту трапеции.')
            e = f'Проекция боковой стороны ({b} − {a}) : 2 = {px}; h = √({c}² − {px}²) = {h}.'
        elif mode == 'area':
            ans = F(a + b, 2) * h
            q = pick(r, f'В равнобедренной трапеции боковая сторона имеет длину {c}, а основания — {a} и {b}. Найдите площадь этой трапеции.',
                     f'В равнобедренной трапеции {t} с основаниями {sd(t, B, C)} = {a} и {sd(t, A, D)} = {b} боковая '
                     f'сторона равна {c}. Найдите площадь трапеции.')
            e = f'h = √({c}² − {px}²) = {h}; S = ({a} + {b}) : 2 · {h} = {tnum(ans)}.'
        else:
            ans = F(c)
            q = pick(r, f'В равнобедренной трапеции высота имеет длину {h}, а основания — {a} и {b}. Найдите длину боковой стороны.',
                     f'В равнобедренной трапеции {t} основания {sd(t, B, C)} и {sd(t, A, D)} равны {a} и {b}, высота равна '
                     f'{h}. Найдите длину боковой стороны.')
            e = f'Боковая сторона √({px}² + {h}²) = {c}.'
    if not nice(ans, 1):
        return None
    sc = 4.0 / b
    hh = min(2.4, max(0.8, h * sc))
    P = {A: (0, 0), D: (4, 0), B: ((b - a) / 2 * sc, hh), C: (4 - (b - a) / 2 * sc, hh), 'H': ((b - a) / 2 * sc, 0)}
    svg = fig(P, polys=[t], segs=[B + 'H'], right=[(A, 'H', B)], hide=['H'])

    def chk():
        # строим трапецию: A(0; 0), D(b; 0), B и C симметричны на высоте, найденной из боковой стороны
        hh_ = math.sqrt(leg2 - ((b - a) / 2) ** 2)
        Ap, Dp, Bp, Cp = (0.0, 0.0), (float(b), 0.0), ((b - a) / 2, hh_), ((b + a) / 2, hh_)
        if abs(dist(Ap, Bp) - dist(Cp, Dp)) > 1e-9 or abs(dist(Bp, Cp) - a) > 1e-9:
            return False
        if mode == 'area45' and not ok(vang(Bp, Ap, Dp), '45'):
            return False
        val = {'h': hh_, 'area': area([Ap, Bp, Cp, Dp]), 'leg': dist(Ap, Bp), 'area45': area([Ap, Bp, Cp, Dp])}[mode]
        return ok(val, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


# ---------------------------------------------------------------- окружность

CIRC4 = ('ABCD', 'ABCD', 'ABCD', 'KLMN', 'MNPK', 'PQRS')


def circle_fig(pts, polys=(), segs=(), extra_circles=(), hide=(), right=()):
    """Чертёж с окружностью радиуса 1 и центром (0, 0)."""
    return fig(pts, polys=polys, segs=segs, circles=[((0, 0), 1)] + list(extra_circles), hide=hide, right=right)


@proto('ep01-diam-angles', 'ege-prof', 1, 'Два диаметра окружности: вписанный и центральный углы',
       invariant='Треугольник, образованный радиусами и хордой, равнобедренный; вертикальные центральные углы равны; '
                 'центральный угол вдвое больше вписанного, опирающегося на ту же дугу.',
       varies='Буквы, что дано (вписанный угол ACB или центральный AOD), что ищем (AOD, AOB, ACB).',
       answer_rule='AOD = BOC = 180° − 2·ACB; AOB = 2·ACB; ACB = (180° − AOD)/2.',
       fipi=r'диаметры окружности',
       mistakes=['считают AOD = 2·ACB (путают дуги)', 'забывают про равнобедренный треугольник BOC'],
       svg=True, kim=kim(1, KIM_DEG + ' Как в КИМ: «Отрезки AC и BD — диаметры окружности с центром O».'))
def gen_ep01_diam_angles(r):
    t = r.choice(CIRC4)
    A, B, C, D = t
    O = 'O'
    mode = r.choice(['AOD', 'AOD', 'ACB', 'AOB'])
    if mode == 'ACB':
        th = r.randrange(4, 176, 2)
        al = (180 - th) // 2
        ans = al
        q = pick(r, f'В окружности с центром {O} проведены диаметры {A}{C} и {B}{D}. Центральный угол {A}{O}{D} равен {th}°. '
                    f'Найдите вписанный угол {A}{C}{B}. {DEG}',
                 f'{A}{C} и {B}{D} — два диаметра окружности, {O} — её центр, ∠{A}{O}{D} = {th}°. Найдите угол {A}{C}{B}. {DEG}')
        e = f'∠{B}{O}{C} = ∠{A}{O}{D} = {th}°, треугольник {B}{O}{C} равнобедренный: ∠{A}{C}{B} = (180° − {th}°) : 2 = {ans}°.'
    else:
        al = r.randint(3, 87)
        ans = 180 - 2 * al if mode == 'AOD' else 2 * al
        ask = f'{A}{O}{D}' if mode == 'AOD' else f'{A}{O}{B}'
        q = pick(r, f'В окружности с центром {O} проведены диаметры {A}{C} и {B}{D}. Вписанный угол {A}{C}{B} равен {al}°. '
                    f'Найдите центральный угол {ask}. {DEG}',
                 f'{A}{C} и {B}{D} — два диаметра окружности, {O} — её центр. Известно, что ∠{A}{C}{B} = {al}°. Найдите ∠{ask}. {DEG}',
                 f'Диаметры {A}{C} и {B}{D} окружности пересекаются в её центре {O}, угол {A}{C}{B} равен {al}°. Найдите угол {ask}. {DEG}')
        e = (f'∠{A}{O}{B} = 2 · {al}° = {2 * al}°' + (f', ∠{A}{O}{D} = 180° − {2 * al}° = {ans}°.' if mode == 'AOD' else '.'))
    aob = 2 * al
    ang0 = r.uniform(100, 140)
    Pa = onc(ang0)
    Pb = onc(ang0 - max(24, min(150, aob)))
    P = {A: Pa, B: Pb, C: (-Pa[0], -Pa[1]), D: (-Pb[0], -Pb[1]), O: (0, 0)}
    svg = circle_fig(P, segs=[A + C, B + D, C + B, A + B] if mode == 'AOB' else [A + C, B + D, C + B])

    def chk():
        a0 = 117.0
        Pa_, Pb_ = onc(a0), onc(a0 - 2 * al)
        Pc_, Pd_ = (-Pa_[0], -Pa_[1]), (-Pb_[0], -Pb_[1])
        O_ = (0.0, 0.0)
        vals = {'ACB': vang(Pa_, Pc_, Pb_), 'AOD': vang(Pa_, O_, Pd_), 'AOB': vang(Pa_, O_, Pb_)}
        if mode == 'ACB':
            return ok(vang(Pa_, O_, Pd_), str(th)) and ok(vals['ACB'], num(ans))
        return ok(vals['ACB'], str(al)) and ok(vals[mode], num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-central-diff', 'ege-prof', 1, 'Центральный и вписанный углы на одну дугу: разность или сумма',
       invariant='Центральный угол вдвое больше вписанного, опирающегося на ту же дугу; дальше линейное уравнение.',
       varies='Дана разность или сумма углов; ищем центральный или вписанный угол.',
       answer_rule='Разность d: вписанный d, центральный 2d; сумма s: вписанный s/3, центральный 2s/3.',
       fipi=r'центральн\w* уг\w*[^.]*на \d+ ?° больше',
       mistakes=['считают разность равной центральному углу', 'делят сумму пополам'],
       svg=True, kim=kim(1, KIM_DEG + ' Как в КИМ: «Центральный угол на … больше острого вписанного угла, опирающегося на ту же дугу».'))
def gen_ep01_central_diff(r):
    mode = r.choice(['diff', 'diff', 'sum'])
    want = r.choice(['central', 'inscribed'])
    A, B, C, O = r.choice([('A', 'B', 'C', 'O'), ('M', 'N', 'K', 'O'), ('P', 'Q', 'S', 'O')])
    if mode == 'diff':
        d = r.randint(5, 89)
        ins = d
        wtxt = 'центральный угол' if want == 'central' else 'вписанный угол'
        q = pick(r, f'Острый вписанный угол {A}{C}{B} и центральный угол {A}{O}{B} опираются на одну и ту же дугу {A}{B}. '
                    f'Центральный угол больше вписанного на {d}°. Найдите {wtxt}. {DEG}',
                 f'Вписанный угол окружности острый и на {d}° меньше центрального угла, опирающегося на ту же дугу. '
                 f'Найдите {wtxt}. {DEG}',
                 f'Разность центрального угла {A}{O}{B} и опирающегося на ту же дугу острого вписанного угла {A}{C}{B} '
                 f'равна {d}°. Найдите угол {A + O + B if want == "central" else A + C + B}. {DEG}')
        e = f'Центральный угол 2x, вписанный x: 2x − x = {d}°, x = {d}°' + (f', центральный угол {2 * d}°.' if want == 'central' else '.')
    else:
        s_ = r.randrange(9, 267, 3)
        ins = s_ // 3
        wtxt = 'центральный угол' if want == 'central' else 'вписанный угол'
        q = pick(r, f'Сумма центрального угла {A}{O}{B} и острого вписанного угла {A}{C}{B}, опирающихся на одну дугу, '
                    f'равна {s_}°. Найдите {wtxt}. {DEG}',
                 f'Центральный и острый вписанный углы опираются на одну и ту же дугу окружности, а вместе составляют {s_}°. '
                 f'Найдите {wtxt}. {DEG}')
        e = f'Вписанный угол x, центральный 2x: 2x + x = {s_}°, x = {ins}°' + (f', центральный угол {2 * ins}°.' if want == 'central' else '.')
    ans = 2 * ins if want == 'central' else ins
    a0 = r.uniform(-60, -30)
    Pa, Pb = onc(a0), onc(a0 - max(30, min(160, 2 * ins)))
    mid = (a0 - min(160, 2 * ins) / 2) + 180
    P = {A: Pa, B: Pb, C: onc(mid + r.uniform(-25, 25)), O: (0, 0)}
    svg = circle_fig(P, segs=[A + O, O + B, A + C, C + B])

    def chk():
        cen = 2 * ins if want == 'inscribed' else ans
        Pa_, Pb_ = onc(10.0), onc(10.0 + cen)
        Pc_ = onc(10.0 + cen / 2 + 180 + 17)            # точка на большей дуге
        ins_ = vang(Pa_, Pc_, Pb_)
        cen_ = vang(Pa_, (0.0, 0.0), Pb_)
        cond = abs(cen_ - ins_ - d) < 1e-6 if mode == 'diff' else abs(cen_ + ins_ - s_) < 1e-6
        return cond and ins_ < 90 and ok(cen_ if want == 'central' else ins_, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-inscribed-arc', 'ege-prof', 1, 'Вписанный угол и дуга (центральный угол)',
       invariant='Вписанный угол равен половине дуги, на которую он опирается; если вершина лежит на меньшей дуге, '
                 'угол опирается на большую дугу 360° − x.',
       varies='Дуга в градусах или в долях окружности, положение вершины (на большей или меньшей дуге), хорда, '
              'равная радиусу; прямая и обратная задачи.',
       answer_rule='∠ACB = x/2 (C на большей дуге) или 180° − x/2 (C на меньшей дуге); центральный угол = 2·вписанный.',
       fipi=r'дуг\w*[^.]*не содержащ|стягивает дугу|равна радиусу окружности|составляет \d+ ?/ ?\d+ окружности',
       mistakes=['не учитывают, на какую дугу опирается угол', 'путают градусную меру дуги и вписанного угла'],
       svg=True, kim=kim(1, KIM_DEG))
def gen_ep01_inscribed_arc(r):
    A, B, C, O = r.choice([('A', 'B', 'C', 'O'), ('K', 'M', 'N', 'O'), ('P', 'Q', 'R', 'O'), ('D', 'E', 'F', 'O')])
    mode = r.choice(['arc_big', 'arc_small', 'part', 'central', 'radius_chord'])
    if mode == 'arc_big':
        x = r.randrange(10, 350, 2)
        if x == 180:
            return None
        ans = x // 2
        q = pick(r, f'Точки {A}, {B} и {C} лежат на окружности. Дуга {A}{B}, не содержащая точку {C}, равна {x}°. '
                    f'Найдите угол {A}{C}{B}. {DEG}',
                 f'На окружности отмечены точки {A}, {B}, {C}. Градусная мера дуги {A}{B}, не содержащей точки {C}, равна {x}°. '
                 f'Найдите вписанный угол {A}{C}{B}. {DEG}')
        e = f'Вписанный угол равен половине дуги, на которую опирается: {x}° : 2 = {ans}°.'
        arc = x
    elif mode == 'arc_small':
        x = r.randrange(10, 178, 2)
        ans = 180 - x // 2
        q = pick(r, f'Точки {A}, {B}, {C} лежат на окружности, причём точка {C} лежит на меньшей дуге {A}{B}, равной {x}°. '
                    f'Найдите угол {A}{C}{B}. {DEG}',
                 f'Хорда {A}{B} стягивает дугу в {x}°. Точка {C} взята на этой дуге. Найдите угол {A}{C}{B}. {DEG}')
        e = f'Угол {A}{C}{B} опирается на дугу 360° − {x}° = {360 - x}°, он равен {ans}°.'
        arc = 360 - x
    elif mode == 'part':
        num_, den = r.choice([(1, 3), (1, 4), (1, 5), (1, 6), (1, 8), (1, 9), (1, 10), (1, 12), (1, 15), (1, 18), (1, 20),
                              (1, 24), (1, 36), (2, 5), (3, 8), (5, 12), (2, 9), (3, 10), (5, 18), (7, 20), (4, 15),
                              (7, 36), (7, 18), (4, 9), (5, 24), (7, 24), (11, 36)])
        x = 360 * num_ // den
        ans = x // 2 if 360 * num_ % den == 0 and x % 2 == 0 else None
        if ans is None:
            return None
        q = pick(r, f'Хорда {A}{B} делит окружность на две дуги, меньшая из которых составляет {num_}/{den} окружности. '
                    f'Точка {C} лежит на большей дуге. Найдите угол {A}{C}{B}. {DEG}',
                 f'Точки {A} и {B} делят окружность на две дуги, одна из которых равна {num_}/{den} окружности. Найдите '
                 f'вписанный угол, опирающийся на эту дугу. {DEG}')
        e = f'Дуга равна {num_}/{den} · 360° = {x}°, вписанный угол {ans}°.'
        arc = x
    elif mode == 'central':
        ins = r.randint(5, 89)
        want_c = r.random() < 0.5
        if want_c:
            ans = 2 * ins
            q = pick(r, f'Вписанный угол {A}{C}{B} окружности с центром {O} равен {ins}°. Найдите центральный угол {A}{O}{B}, '
                        f'опирающийся на ту же дугу. {DEG}',
                     f'Острый вписанный угол {A}{C}{B} равен {ins}°. Найдите угол {A}{O}{B}, где {O} — центр окружности. {DEG}')
        else:
            ans = ins
            q = pick(r, f'Центральный угол {A}{O}{B} окружности равен {2 * ins}°. Найдите вписанный угол {A}{C}{B}, '
                        f'опирающийся на ту же дугу {A}{B}. {DEG}',
                     f'Точка {C} лежит на большей дуге {A}{B} окружности с центром {O}, ∠{A}{O}{B} = {2 * ins}°. '
                     f'Найдите угол {A}{C}{B}. {DEG}')
        e = 'Центральный угол вдвое больше вписанного, опирающегося на ту же дугу.'
        arc = 2 * ins
    else:
        big = r.random() < 0.6
        ans = 30 if big else 150
        where = 'большей' if big else 'меньшей'
        q = pick(r, f'Хорда {A}{B} окружности равна её радиусу. Точка {C} лежит на {where} дуге {A}{B}. Найдите угол {A}{C}{B}. {DEG}',
                 f'Длина хорды {A}{B} равна радиусу окружности, точка {C} окружности лежит на {where} из дуг {A}{B}. '
                 f'Найдите вписанный угол {A}{C}{B}. {DEG}')
        e = f'Треугольник {A}{O}{B} равносторонний, дуга {A}{B} равна 60°; ∠{A}{C}{B} = {ans}°.'
        arc = 60 if big else 300
    Pa, Pb = onc(-90 - arc / 2), onc(-90 + arc / 2)
    Pc = onc(90 + r.uniform(-20, 20))
    P = {A: Pa, B: Pb, C: Pc, O: (0, 0)}
    segs = [A + C, C + B] + ([A + O, O + B] if mode in ('central', 'radius_chord') else []) + \
        ([A + B] if mode in ('radius_chord', 'part', 'arc_small') else [])
    svg = circle_fig(P, segs=segs, hide=[O] if mode in ('arc_big', 'part', 'arc_small') else [])

    def chk():
        # дуга AB, не содержащая C, равна arc; C — середина другой дуги
        Pa_, Pb_ = onc(0.0), onc(float(arc))
        Pc_ = onc(arc + (360 - arc) / 2)
        val = vang(Pa_, Pc_, Pb_)
        if mode == 'central' and want_c:
            return ok(vang(Pa_, (0.0, 0.0), Pb_) if arc <= 180 else 360 - vang(Pa_, (0.0, 0.0), Pb_), num(ans)) and ok(val, str(ins))
        if mode == 'radius_chord':
            return ok(dist(Pa_, Pb_), '1') and ok(val, num(ans))
        return ok(val, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-cyclic-quad', 'ege-prof', 1, 'Вписанный четырёхугольник: углы, опирающиеся на одну дугу',
       invariant='Вписанные углы, опирающиеся на одну дугу, равны (∠CBD = ∠CAD), поэтому ∠ABC = ∠ABD + ∠DBC.',
       varies='Буквы, какие два угла из ABC, ABD, CAD даны и какой ищем.',
       answer_rule='∠ABD = ∠ABC − ∠CAD; ∠ABC = ∠ABD + ∠CAD; ∠CAD = ∠ABC − ∠ABD.',
       fipi=r'Четырёхугольник[^.]*вписан в окружность\. Угол',
       mistakes=['складывают вместо вычитания', 'используют свойство противоположных углов вместо равенства вписанных'],
       svg=True, kim=kim(1, KIM_DEG + ' Как в КИМ: «Четырёхугольник ABCD вписан в окружность. Угол ABC равен …».'))
def gen_ep01_cyclic_quad(r):
    t = r.choice(CIRC4)
    A, B, C, D = t
    a3, a4 = r.randrange(20, 200, 2), r.randrange(20, 200, 2)   # дуги CD и DA (не содержащие B)
    a1 = r.randrange(20, 200, 2)
    a2 = 360 - a1 - a3 - a4
    if a2 < 20:
        return None
    abc, cad, abd = (a3 + a4) // 2, a3 // 2, a4 // 2
    if abc >= 180:
        return None
    mode = r.choice(['ABD', 'ABC', 'CAD'])
    given = {'ABD': (('ABC', abc), ('CAD', cad)), 'ABC': (('ABD', abd), ('CAD', cad)), 'CAD': (('ABC', abc), ('ABD', abd))}[mode]
    L = dict(zip('ABCD', t))
    nm = lambda s_: ''.join(L[c] for c in s_)
    ans = {'ABD': abd, 'ABC': abc, 'CAD': cad}[mode]
    g1, g2 = given
    q = pick(r, f'Около четырёхугольника {t} описана окружность, ∠{nm(g1[0])} = {g1[1]}°, ∠{nm(g2[0])} = {g2[1]}°. '
                f'Найдите величину угла {nm(mode)}. {DEG}',
             f'Вершины четырёхугольника {t} лежат на одной окружности. Известно, что ∠{nm(g1[0])} = {g1[1]}°, '
             f'∠{nm(g2[0])} = {g2[1]}°. Найдите градусную меру угла {nm(mode)}. {DEG}',
             f'В окружность вписан четырёхугольник {t}, у которого ∠{nm(g2[0])} = {g2[1]}°, ∠{nm(g1[0])} = {g1[1]}°. '
             f'Найдите величину угла {nm(mode)}. {DEG}')
    e = f'∠{nm("CBD")} = ∠{nm("CAD")} (опираются на дугу {nm("CD")}), ∠{nm("ABC")} = ∠{nm("ABD")} + ∠{nm("CBD")}; ответ {ans}°.'
    s0 = r.uniform(0, 360)
    arcs = [max(35, min(150, v)) for v in (a1, a2, a3, a4)]
    tot = sum(arcs)
    arcs = [v * 360 / tot for v in arcs]
    pos = [s0, s0 + arcs[0], s0 + arcs[0] + arcs[1], s0 + arcs[0] + arcs[1] + arcs[2]]
    P = {n: onc(-p_) for n, p_ in zip(t, pos)}
    svg = circle_fig(P, polys=[t], segs=[A + C, B + D])

    def chk():
        pos_ = [0.0, a1, a1 + a2, a1 + a2 + a3]
        Pp = {c: onc(v) for c, v in zip('ABCD', pos_)}
        ang = lambda s_: vang(Pp[s_[0]], Pp[s_[1]], Pp[s_[2]])
        return (ok(ang(g1[0]), str(g1[1])) and ok(ang(g2[0]), str(g2[1])) and ok(ang(mode), num(ans)))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-cyclic-opp', 'ege-prof', 1, 'Вписанный четырёхугольник: противоположные углы',
       invariant='Сумма противоположных углов вписанного четырёхугольника равна 180°.',
       varies='Даны два соседних угла (ищем больший или меньший из оставшихся) или один угол (ищем противоположный), буквы.',
       answer_rule='Оставшиеся углы 180° − α и 180° − β; противоположный угол 180° − α.',
       fipi=r'угла вписанного в окружность четырёхугольника',
       mistakes=['считают данные углы противоположными', 'выбирают меньший угол вместо большего'],
       svg=True, kim=kim(1, KIM_DEG + ' Как в КИМ: «Два угла вписанного в окружность четырёхугольника равны … и …».'))
def gen_ep01_cyclic_opp(r):
    t = r.choice(CIRC4)
    A, B, C, D = t
    mode = r.choice(['two', 'two', 'one'])
    if mode == 'two':
        x, y = r.randint(40, 140), r.randint(40, 140)
        if x == y or x + y == 180:
            return None
        big = r.random() < 0.6
        ans = 180 - min(x, y) if big else 180 - max(x, y)
        which = 'больший' if big else 'меньший'
        q = pick(r, f'Около четырёхугольника описана окружность. Два его угла, прилежащие к одной стороне, равны {x}° и {y}°. '
                    f'Найдите {which} из двух других углов. {DEG}',
                 f'В четырёхугольнике {t}, вписанном в окружность, ∠{A} = {x}°, ∠{B} = {y}°. Найдите {which} из углов {C} и {D}. {DEG}',
                 f'Вершины четырёхугольника {t} лежат на окружности, углы при вершинах {A} и {B} равны {x}° и {y}°. '
                 f'Найдите {which} из оставшихся углов этого четырёхугольника. {DEG}')
        e = f'Противоположные углы в сумме 180°: 180° − {x}° = {180 - x}°, 180° − {y}° = {180 - y}°; {which} — {ans}°.'
        angA, angB = x, y
    else:
        x = r.randint(25, 155)
        if x == 90:
            return None
        ans = 180 - x
        q = pick(r, f'В окружность вписан четырёхугольник {t}, ∠{A}{B}{C} = {x}°. Найдите величину угла {A}{D}{C}. {DEG}',
                 f'Около четырёхугольника {t} описана окружность, ∠{B}{C}{D} = {x}°. Найдите градусную меру угла {B}{A}{D}. {DEG}')
        e = f'Сумма противоположных углов равна 180°: 180° − {x}° = {ans}°.'
        angA, angB = 180 - x, x   # для чертежа
    # дуги: A = (a2 + a3)/2, B = (a3 + a4)/2
    a3 = min(2 * angA, 2 * angB) / 2
    a2, a4 = 2 * angA - a3, 2 * angB - a3
    a1 = 360 - a2 - a3 - a4
    if min(a1, a2, a3, a4) <= 0:
        return None
    pos = [0, a1, a1 + a2, a1 + a2 + a3]
    rot = r.uniform(0, 360)
    P = {n: onc(-(p_ + rot)) for n, p_ in zip(t, pos)}
    svg = circle_fig(P, polys=[t])

    def chk():
        pts = {c: onc(v) for c, v in zip('ABCD', pos)}
        angs = {c: vang(pts['ABCD'[i - 1]], pts[c], pts['ABCD'[(i + 1) % 4]]) for i, c in enumerate('ABCD')}
        if mode == 'two':
            rest = [angs['C'], angs['D']]
            return ok(angs['A'], str(x)) and ok(angs['B'], str(y)) and ok(max(rest) if big else min(rest), num(ans))
        return ok(angs['B'], str(x)) and ok(angs['D'], num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-tangent-arc', 'ege-prof', 1, 'Касательная и секущая через центр: угол и дуга',
       invariant='Радиус, проведённый в точку касания, перпендикулярен касательной; центральный угол AOB равен дуге AB; '
                 'в прямоугольном треугольнике ACO угол ACO = 90° − ∠AOC.',
       varies='Буквы, что дано (дуга или угол) и что ищем.',
       answer_rule='∠ACO = 90° − (дуга AB); дуга AB = 90° − ∠ACO.',
       fipi=r'касается окружности с центром',
       mistakes=['берут половину дуги, как для вписанного угла', 'забывают про прямой угол между радиусом и касательной'],
       svg=True, kim=kim(1, KIM_DEG + ' Чертёж обязателен («см. рисунок»), как в КИМ.'))
def gen_ep01_tangent_arc(r):
    A, B, C, O = r.choice([('A', 'B', 'C', 'O'), ('K', 'M', 'P', 'O'), ('M', 'N', 'S', 'O'), ('E', 'F', 'T', 'O')])
    mode = r.choice(['angle', 'arc'])
    if mode == 'angle':
        phi = r.randint(8, 82)
        ans = 90 - phi
        q = pick(r, f'Прямая {C}{A} касается окружности с центром {O} в точке {A}, отрезок {C}{O} пересекает окружность в '
                    f'точке {B} (см. рисунок). Меньшая дуга {A}{B} равна {phi}°. Найдите угол {A}{C}{O}. {DEG}',
                 f'Из точки {C} проведена касательная {C}{A} к окружности с центром {O} ({A} — точка касания). Отрезок {C}{O} '
                 f'пересекает окружность в точке {B}, дуга {A}{B}, лежащая внутри угла {A}{C}{O}, равна {phi}°. '
                 f'Найдите угол {A}{C}{O}. {DEG}')
        e = f'∠{A}{O}{C} = {phi}°, ∠{O}{A}{C} = 90°, ∠{A}{C}{O} = 90° − {phi}° = {ans}°.'
    else:
        ang = r.randint(8, 82)
        phi = 90 - ang
        ans = phi
        q = pick(r, f'Прямая {C}{A} касается окружности с центром {O} в точке {A}, отрезок {C}{O} пересекает окружность в '
                    f'точке {B} (см. рисунок). Угол {A}{C}{O} равен {ang}°. Найдите градусную меру меньшей дуги {A}{B}. {DEG}',
                 f'Сторона {C}{A} угла {A}{C}{O} касается окружности с центром {O}, а отрезок {C}{O} пересекает эту окружность '
                 f'в точке {B}. Известно, что ∠{A}{C}{O} = {ang}°. Найдите величину дуги {A}{B}, заключённой внутри угла. {DEG}')
        e = f'∠{A}{O}{C} = 90° − {ang}° = {ans}°, дуга {A}{B} равна центральному углу: {ans}°.'
    pd = max(25, min(65, phi))
    Pa = onc(pd)
    Cx = 1 / math.cos(math.radians(pd))
    P = {A: Pa, B: (1, 0), C: (Cx, 0), O: (0, 0)}
    svg = circle_fig(P, segs=[C + A, C + O, O + A], right=[(O, A, C)])

    def chk():
        O_ = (0.0, 0.0)
        if mode == 'angle':
            Pa_ = onc(phi)
            Cp = (1 / math.cos(math.radians(phi)), 0.0)
            return ok(vang(Pa_, O_, (1.0, 0.0)), str(phi)) and ok(vang(Pa_, Cp, O_), num(ans))
        # находим дугу перебором положения точки касания с шагом 1°
        for d in range(1, 90):
            Pa_ = onc(d)
            Cp = (1 / math.cos(math.radians(d)), 0.0)
            if abs(vang(Pa_, Cp, O_) - ang) < 1e-6:
                return ok(vang(Pa_, O_, (1.0, 0.0)), num(ans))
        return False
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-tangents-two', 'ege-prof', 1, 'Две касательные из одной точки',
       invariant='Радиусы в точки касания перпендикулярны касательным, поэтому в четырёхугольнике PAOB ∠APB + ∠AOB = 180°; '
                 'отрезки касательных равны, треугольник APB равнобедренный.',
       varies='Что дано (угол между касательными или центральный угол) и что ищем (центральный угол, угол между '
              'касательными, угол между касательной и хордой, угол OAB).',
       answer_rule='∠AOB = 180° − ∠APB; ∠PAB = 90° − ∠APB/2; ∠OAB = ∠APB/2.',
       fipi=r'касательн\w*[^.]*из (одной )?точки|проведены касательные',
       mistakes=['считают ∠AOB = 2∠APB', 'забывают, что отрезки касательных равны'],
       svg=True, kim=kim(1, KIM_DEG))
def gen_ep01_tangents_two(r):
    A, B, Pn, O = r.choice([('A', 'B', 'C', 'O'), ('A', 'B', 'P', 'O'), ('K', 'M', 'T', 'O'), ('E', 'F', 'S', 'O')])
    mode = r.choice(['AOB', 'APB', 'PAB', 'OAB'])
    if mode == 'APB':
        cen = r.randint(20, 170)
        beta = 180 - cen
        ans = beta
        q = pick(r, f'Из точки {Pn} к окружности с центром {O} проведены две касательные, {A} и {B} — точки касания. '
                    f'Угол {A}{O}{B} равен {cen}°. Найдите угол {A}{Pn}{B}. {DEG}',
                 f'Прямые {Pn}{A} и {Pn}{B} касаются окружности с центром {O} в точках {A} и {B}, ∠{A}{O}{B} = {cen}°. '
                 f'Найдите угол между касательными. {DEG}')
        e = f'В четырёхугольнике {Pn}{A}{O}{B} два прямых угла: ∠{A}{Pn}{B} = 180° − {cen}° = {ans}°.'
    else:
        beta = r.randrange(10, 170, 2)
        ans = {'AOB': 180 - beta, 'PAB': 90 - beta // 2, 'OAB': beta // 2}[mode]
        ask = {'AOB': f'{A}{O}{B}', 'PAB': f'{Pn}{A}{B}', 'OAB': f'{O}{A}{B}'}[mode]
        q = pick(r, f'Из точки {Pn} к окружности с центром {O} проведены две касательные, {A} и {B} — точки касания. '
                    f'Угол {A}{Pn}{B} равен {beta}°. Найдите угол {ask}. {DEG}',
                 f'Прямые {Pn}{A} и {Pn}{B} касаются окружности с центром {O} в точках {A} и {B}, угол между '
                 f'касательными равен {beta}°. Найдите угол {ask}. {DEG}')
        e = {'AOB': f'∠{A}{O}{B} = 180° − {beta}° = {ans}°.',
             'PAB': f'{Pn}{A} = {Pn}{B}, ∠{Pn}{A}{B} = (180° − {beta}°) : 2 = {ans}°.',
             'OAB': f'∠{O}{A}{B} = 90° − ∠{Pn}{A}{B} = {beta}° : 2 = {ans}°.'}[mode]
    cd = max(40, min(140, 180 - beta))
    Pa, Pb = onc(cd / 2), onc(-cd / 2)
    P = {A: Pa, B: Pb, Pn: (1 / math.cos(math.radians(cd / 2)), 0), O: (0, 0)}
    segs = [Pn + A, Pn + B, O + A, O + B] + ([A + B] if mode in ('PAB', 'OAB') else [])
    svg = circle_fig(P, segs=segs)

    def chk():
        # по углу между касательными строим точку P на оси, точки касания — через прямоугольный треугольник OAP
        bb = beta
        dP = 1 / math.sin(math.radians(bb / 2))
        Pp, O_ = (dP, 0.0), (0.0, 0.0)
        tA = math.degrees(math.acos(1 / dP))
        Pa_, Pb_ = onc(tA), onc(-tA)
        if abs(vang(O_, Pa_, Pp) - 90) > 1e-6:
            return False
        vals = {'AOB': vang(Pa_, O_, Pb_), 'APB': vang(Pa_, Pp, Pb_), 'PAB': vang(Pp, Pa_, Pb_), 'OAB': vang(O_, Pa_, Pb_)}
        if mode == 'APB':
            return ok(vals['AOB'], str(cen)) and ok(vals['APB'], num(ans))
        return ok(vals['APB'], str(beta)) and ok(vals[mode], num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-tangent-quad', 'ege-prof', 1, 'Описанный четырёхугольник: суммы противоположных сторон',
       invariant='В четырёхугольнике, описанном около окружности, суммы противоположных сторон равны '
                 '(отрезки касательных из одной вершины равны).',
       varies='Что дано: периметр и сторона, две противоположные стороны, три стороны; буквы.',
       answer_rule='AB + CD = BC + AD = P/2; четвёртая сторона AD = AB + CD − BC.',
       fipi=r'^(?!.*Докажите).*(четырёхугольник[^.]*вписана окружность|вписана окружность[^.]*четырёхугольник)',
       mistakes=['берут периметр вместо полупериметра', 'складывают соседние стороны вместо противоположных'],
       svg=True, kim=kim(1, KIM_LEN + ' Как в КИМ: «В четырёхугольник ABCD вписана окружность, AB = …, CD = …. Найдите периметр».'))
def gen_ep01_tangent_quad(r):
    t = r.choice(CIRC4)
    A, B, C, D = t
    tl = [r.randint(1, 12) for _ in range(4)]        # отрезки касательных из A, B, C, D
    ab, bc, cd, da = tl[0] + tl[1], tl[1] + tl[2], tl[2] + tl[3], tl[3] + tl[0]
    P_ = ab + bc + cd + da
    AB, BC, CD, DA = sd(t, A, B), sd(t, B, C), sd(t, C, D), sd(t, A, D)
    mode = r.choice(['CD_from_P', 'P_from_two', 'fourth'])
    if mode == 'CD_from_P':
        ans = cd
        q = pick(r, f'Четырёхугольник {t} описан около окружности, его периметр равен {P_}, а сторона {AB} равна {ab}. '
                    f'Найдите сторону {CD}.',
                 f'В четырёхугольник {t} можно вписать окружность. Периметр {t} равен {P_}, {AB} = {ab}. Найдите длину стороны {CD}.')
        e = f'{AB} + {CD} = {P_} : 2 = {P_ // 2}, {CD} = {P_ // 2} − {ab} = {ans}.'
    elif mode == 'P_from_two':
        ans = P_
        q = pick(r, f'Четырёхугольник {t} описан около окружности, {AB} = {ab}, {CD} = {cd}. Найдите периметр {t}.',
                 f'В четырёхугольник {t} можно вписать окружность. Известно, что {AB} = {ab} и {CD} = {cd}. Найдите периметр четырёхугольника.')
        e = f'{BC} + {DA} = {AB} + {CD} = {ab + cd}, периметр {2 * (ab + cd)}.'
    else:
        ans = da
        q = pick(r, f'Четырёхугольник {t} описан около окружности, {AB} = {ab}, {BC} = {bc}, {CD} = {cd}. Найдите {DA}.',
                 f'В четырёхугольник {t} можно вписать окружность. Три его стороны: {AB} = {ab}, {BC} = {bc}, {CD} = {cd}. '
                 f'Найдите длину четвёртой стороны.')
        e = f'{DA} = {AB} + {CD} − {BC} = {ab} + {cd} − {bc} = {ans}.'
    # чертёж: четырёхугольник, описанный около единичной окружности (касание под углами)
    ang = [0, 95, 185, 270]
    ang = [a_ + r.uniform(-15, 15) for a_ in ang]
    tang = []
    for i in range(4):
        a1, a2 = math.radians(ang[i]), math.radians(ang[(i + 1) % 4] + (360 if i == 3 else 0))
        mid = (a1 + a2) / 2
        dd = 1 / math.cos((a2 - a1) / 2)
        tang.append((dd * math.cos(mid), dd * math.sin(mid)))
    P = {n: p_ for n, p_ in zip(t, tang)}
    svg = circle_fig(P, polys=[t])

    def chk():
        # сторону ищем как сумму отрезков касательных (а не по формуле суммы противоположных сторон)
        if mode == 'fourth':
            for x in range(1, 13):          # отрезок касательной из вершины B
                ta, tc = ab - x, bc - x
                td = cd - tc
                if ta > 0 and tc > 0 and td > 0:
                    return ok(td + ta, num(ans))
            return False
        if mode == 'P_from_two':
            return ok(sum(2 * v for v in tl), num(ans))
        half = P_ / 2
        return ok(half - ab, num(ans)) and ok(tl[2] + tl[3], num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-circum-sine', 'ege-prof', 1, 'Радиус описанной окружности по теореме синусов',
       invariant='По теореме синусов сторона, делённая на синус противолежащего угла, равна 2R.',
       varies='Угол (30°, 45°, 60°, 90°, 120°, 135°, 150°), сторона (с корнем там, где нужно), прямая или обратная задача, буквы.',
       answer_rule='R = a / (2 sin α); a = 2R sin α.',
       fipi=r'радиус описанной около',
       mistakes=['забывают двойку в формуле 2R', 'путают синус тупого угла', 'берут прилежащую сторону вместо противолежащей'],
       svg=True, kim=kim(1, KIM_LEN + ' Как в КИМ: «В треугольнике ABC сторона AB равна …, угол C равен … Найдите радиус описанной окружности».'))
def gen_ep01_circum_sine(r):
    t = r.choice(TRI)
    A, B, C = t
    al = r.choice([30, 45, 60, 90, 120, 135, 150, 30, 150])
    reverse = r.random() < 0.3
    k = r.randint(1, 30)
    if not reverse:
        if al in (30, 150):
            side, ans, s2 = str(k), F(k), k * k
        elif al == 90:
            side, ans, s2 = str(k), F(k, 2), k * k
        elif al in (45, 135):
            side, ans, s2 = f'{k}√2', F(k), 2 * k * k
        else:
            side, ans, s2 = f'{k}√3', F(k), 3 * k * k
        if k == 1:
            side = side.replace('1√', '√')
        q = pick(r, f'В треугольнике {t} известны сторона {sd(t, A, B)} = {side} и угол {A}{C}{B} = {al}°. Найдите радиус '
                    f'окружности, описанной около треугольника {t}.',
                 f'Сторона {sd(t, A, B)} треугольника {t} равна {side}, а противолежащий ей угол {C} равен {al}°. Найдите радиус '
                 f'описанной около треугольника окружности.',
                 f'Около треугольника {t} описана окружность. Известно, что {sd(t, A, B)} = {side}, ∠{A}{C}{B} = {al}°. '
                 f'Найдите радиус этой окружности.')
        e = f'2R = {sd(t, A, B)} : sin {al}°, R = {tnum(ans)}.'
        R2 = F(s2) / (4 * F({30: 1, 150: 1, 90: 4, 45: 2, 135: 2, 60: 3, 120: 3}[al], 4))
    else:
        if al in (30, 150):
            rtxt, ans = str(k), F(k)
        elif al == 90:
            rtxt, ans = str(k), F(2 * k)
        elif al in (45, 135):
            rtxt, ans = f'{k}√2', F(2 * k)
        else:
            rtxt, ans = f'{k}√3', F(3 * k)
        if k == 1:
            rtxt = rtxt.replace('1√', '√')
        R2 = {30: F(k * k), 150: F(k * k), 90: F(k * k), 45: F(2 * k * k), 135: F(2 * k * k), 60: F(3 * k * k), 120: F(3 * k * k)}[al]
        q = pick(r, f'Радиус окружности, описанной около треугольника {t}, равен {rtxt}, угол {C} равен {al}°. Найдите сторону {sd(t, A, B)}.',
                 f'Около треугольника {t} описана окружность радиуса {rtxt}. Угол {A}{C}{B} равен {al}°. Найдите длину стороны {sd(t, A, B)}.')
        e = f'{sd(t, A, B)} = 2R · sin {al}° = {tnum(ans)}.'
    # чертёж: точки на окружности, AB — хорда, C — на дуге, где угол равен al
    cen = 2 * al if al <= 90 else 360 - 2 * al
    Pa, Pb = onc(-90 - cen / 2), onc(-90 + cen / 2)
    Pc = onc(90 + r.uniform(-25, 25)) if al <= 90 else onc(-90 + r.uniform(-cen / 4, cen / 4))
    P = {A: Pa, B: Pb, C: Pc, 'O': (0, 0)}
    svg = circle_fig(P, polys=[t], hide=['O'])

    def chk():
        Rr = math.sqrt(float(R2))
        cen_ = 2 * al if al <= 90 else 360 - 2 * al
        Pa_, Pb_ = onc(-cen_ / 2, Rr), onc(cen_ / 2, Rr)
        Pc_ = onc(180, Rr) if al <= 90 else onc(0, Rr)
        if not ok(vang(Pa_, Pc_, Pb_), str(al)):
            return False
        return ok(Rr, num(ans)) if not reverse else ok(dist(Pa_, Pb_), num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-circle-right', 'ege-prof', 1, 'Прямоугольный треугольник: радиусы описанной и вписанной окружностей',
       invariant='Центр описанной окружности прямоугольного треугольника — середина гипотенузы (R = c/2); '
                 'радиус вписанной окружности r = (a + b − c)/2.',
       varies='Что дано (катеты, катет и гипотенуза, R и катет), что ищем (R, r, катет), буквы.',
       answer_rule='R = c/2; r = (a + b − c)/2; катет = √((2R)² − b²).',
       fipi=r'прямоугольн\w* треугольник\w*[^.]*(описанн|вписанн)\w* окружност',
       mistakes=['считают R равным половине катета', 'путают формулы вписанной и описанной окружностей'],
       svg=True, kim=kim(1, KIM_LEN))
def gen_ep01_circle_right(r):
    t = r.choice(TRI_NOAUX)
    A, B, C = t      # прямой угол C
    p, q_, h = r.choice(TRIPLES[:9])
    k = r.choice([1, 1, 2, 3, 4])
    a, b, c = p * k, q_ * k, h * k
    if c > 130:
        return None
    if r.random() < 0.5:
        a, b = b, a
    BC, AC, AB = sd(t, B, C), sd(t, A, C), sd(t, A, B)
    mode = r.choice(['R_legs', 'r_legs', 'leg_from_R', 'r_hyp'])
    if mode == 'R_legs':
        ans = F(c, 2)
        q = pick(r, f'Прямоугольный треугольник {t} имеет катеты {a} и {b}. Найдите радиус описанной около него окружности.',
                 f'В треугольнике {t} угол {C} прямой, {BC} = {a}, {AC} = {b}. Найдите радиус описанной около него окружности.')
        e = f'{AB} = √({a}² + {b}²) = {c}, R = {AB} : 2 = {tnum(ans)}.'
    elif mode == 'r_legs':
        ans = F(a + b - c, 2)
        q = pick(r, f'Прямоугольный треугольник {t} имеет катеты {a} и {b}. Найдите радиус вписанной в него окружности.',
                 f'В треугольнике {t} угол {C} прямой, {BC} = {a}, {AC} = {b}. Найдите радиус вписанной в него окружности.')
        e = f'{AB} = {c}, r = ({a} + {b} − {c}) : 2 = {tnum(ans)}.'
    elif mode == 'leg_from_R':
        Rv = F(c, 2)
        ans = F(a)
        q = pick(r, f'Радиус окружности, описанной около прямоугольного треугольника {t} с прямым углом {C}, равен {tnum(Rv)}, '
                    f'катет {AC} равен {b}. Найдите катет {BC}.',
                 f'В треугольнике {t} угол {C} прямой, {AC} = {b}, а радиус описанной окружности равен {tnum(Rv)}. Найдите {BC}.')
        e = f'{AB} = 2R = {c}, {BC} = √({c}² − {b}²) = {a}.'
    else:
        ans = F(a + b - c, 2)
        q = pick(r, f'В прямоугольном треугольнике {t} гипотенуза {AB} равна {c}, катет {AC} равен {b}. Найдите радиус '
                    f'вписанной окружности.',
                 f'В треугольнике {t} угол {C} прямой, {AB} = {c}, {AC} = {b}. Найдите радиус окружности, вписанной в треугольник {t}.')
        e = f'{BC} = √({c}² − {b}²) = {a}, r = ({a} + {b} − {c}) : 2 = {tnum(ans)}.'
    Pc, Pb, Pa = (0, 0), (0, a), (b, 0)
    if mode in ('R_legs', 'leg_from_R'):
        circ = [((b / 2, a / 2), c / 2)]
    else:
        rr = (a + b - c) / 2
        circ = [((rr, rr), rr)]
    P = {A: Pa, B: Pb, C: Pc}
    svg = fig(P, polys=[t], circles=circ, right=[(A, C, B)])

    def chk():
        Cp, Bp, Ap = (0.0, 0.0), (0.0, float(a)), (float(b), 0.0)
        if mode in ('R_legs', 'leg_from_R'):
            # центр описанной окружности — пересечение серединных перпендикуляров
            m1, m2 = lerp(Cp, Bp, 0.5), lerp(Cp, Ap, 0.5)
            O_ = cross_lines(m1, (m1[0] + 1, m1[1]), m2, (m2[0], m2[1] + 1))
            Rr = dist(O_, Ap)
            if mode == 'R_legs':
                return ok(Rr, num(ans))
            return ok(Rr, num(F(c, 2))) and ok(dist(Cp, Bp), num(ans))
        per = dist(Ap, Bp) + dist(Bp, Cp) + dist(Cp, Ap)
        return ok(2 * area([Ap, Bp, Cp]) / per, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep01-circle-regular', 'ege-prof', 1, 'Правильные многоугольники: радиусы вписанной и описанной окружностей',
       invariant='Для правильного треугольника R = 2h/3, r = h/3, R = a/√3; для квадрата r = a/2, R = a/√2; '
                 'для правильного шестиугольника R = a, r = a√3/2.',
       varies='Многоугольник (треугольник, квадрат, шестиугольник), что дано (сторона с корнем, высота, радиус), что ищем.',
       answer_rule='Соотношения между стороной, высотой и радиусами для правильных многоугольников.',
       fipi=r'^(?!.*Докажите).*(правильн\w* (треугольник|шестиугольник)\w*|около квадрата|в квадрат)[^.]*окружност',
       mistakes=['путают радиусы вписанной и описанной окружностей', 'в правильном треугольнике берут R = h/2'],
       svg=True, kim=kim(1, KIM_LEN))
def gen_ep01_circle_regular(r):
    k = r.randint(1, 20)
    mode = r.choice(['tri_R', 'tri_r', 'tri_h', 'tri_rR', 'sq_r', 'sq_R', 'sq_side', 'hex_R', 'hex_r'])
    rt = lambda kk, s_: (f'{kk}√{s_}' if kk != 1 else f'√{s_}')
    if mode == 'tri_R':
        n_, side2, want = 3, 3 * k * k, 'R'
        ans = F(k)
        q = pick(r, f'Правильный треугольник имеет сторону {rt(k, 3)}. Найдите радиус описанной около него окружности.',
                 f'Около правильного треугольника со стороной {rt(k, 3)} описана окружность. Найдите её радиус.')
        e = f'R = a/√3 = {k}.'
    elif mode == 'tri_r':
        n_, side2, want = 3, 3 * k * k, 'r'
        ans = F(k, 2)
        q = pick(r, f'Правильный треугольник имеет сторону {rt(k, 3)}. Найдите радиус вписанной в него окружности.',
                 f'В правильный треугольник со стороной {rt(k, 3)} вписана окружность. Найдите её радиус.')
        e = f'r = a/(2√3) = {tnum(ans)}.'
    elif mode == 'tri_h':
        h = 3 * k
        n_, side2 = 3, F(4 * h * h, 3)
        want = r.choice(['R', 'r'])
        ans = F(2 * h, 3) if want == 'R' else F(h, 3)
        nm = 'описанной около него' if want == 'R' else 'вписанной в него'
        q = pick(r, f'Правильный треугольник имеет высоту {h}. Найдите радиус {nm} окружности.',
                 f'В правильном треугольнике высота равна {h}. Найдите радиус {"описанной" if want == "R" else "вписанной"} окружности.')
        e = f'Центр делит высоту в отношении 2 : 1: {"R = 2h/3" if want == "R" else "r = h/3"} = {tnum(ans)}.'
    elif mode == 'tri_rR':
        n_ = 3
        if r.random() < 0.5:
            Rv = r.randint(2, 60)
            side2, want, ans = 3 * Rv * Rv, 'r', F(Rv, 2)
            q = pick(r, f'Радиус окружности, описанной около правильного треугольника, равен {Rv}. Найдите радиус вписанной в него окружности.',
                     f'Около правильного треугольника описана окружность радиуса {Rv}. Найдите радиус вписанной в него окружности.')
            e = f'r = R/2 = {tnum(ans)}.'
        else:
            rv = r.randint(1, 40)
            side2, want, ans = 12 * rv * rv, 'R', F(2 * rv)
            q = pick(r, f'Радиус окружности, вписанной в правильный треугольник, равен {rv}. Найдите радиус описанной около него окружности.',
                     f'В правильный треугольник вписана окружность радиуса {rv}. Найдите радиус описанной около него окружности.')
            e = f'R = 2r = {tnum(ans)}.'
    elif mode == 'sq_r':
        n_, side2, want = 4, 4 * k * k, 'r'
        a = 2 * k if r.random() < 0.5 else r.randint(1, 60)
        side2 = a * a
        ans = F(a, 2)
        q = pick(r, f'Найдите радиус окружности, вписанной в квадрат со стороной {a}.',
                 f'В квадрат со стороной {a} вписана окружность. Найдите её радиус.')
        e = f'r = a/2 = {tnum(ans)}.'
    elif mode == 'sq_R':
        n_, side2, want = 4, 2 * k * k, 'R'
        ans = F(k)
        q = pick(r, f'Найдите радиус окружности, описанной около квадрата со стороной {rt(k, 2)}.',
                 f'Около квадрата со стороной {rt(k, 2)} описана окружность. Найдите её радиус.')
        e = f'Диагональ квадрата {2 * k}, R = {k}.'
    elif mode == 'sq_side':
        n_, want = 4, 'a'
        side2 = 4 * k * k
        ans = F(2 * k)
        q = pick(r, f'Квадрат вписан в окружность радиуса {rt(k, 2)}. Найдите сторону квадрата.',
                 f'Около квадрата описана окружность радиуса {rt(k, 2)}. Найдите сторону этого квадрата.')
        e = f'Диагональ квадрата 2R = {rt(2 * k, 2)}, сторона {2 * k}.'
    elif mode == 'hex_R':
        n_, want = 6, 'R'
        a = r.randint(2, 60)
        side2, ans = a * a, F(a)
        q = pick(r, f'Правильный шестиугольник имеет сторону {a}. Найдите радиус описанной около него окружности.',
                 f'Около правильного шестиугольника со стороной {a} описана окружность. Найдите её радиус.')
        e = f'Шестиугольник состоит из шести правильных треугольников: R = a = {a}.'
    else:
        n_, want = 6, 'r'
        side2, ans = 3 * k * k, F(3 * k, 2)
        q = pick(r, f'Правильный шестиугольник имеет сторону {rt(k, 3)}. Найдите радиус вписанной в него окружности.',
                 f'В правильный шестиугольник со стороной {rt(k, 3)} вписана окружность. Найдите её радиус.')
        e = f'r — высота правильного треугольника со стороной a: a√3/2 = {tnum(ans)}.'
    if not nice(ans, 1):
        return None
    rot = {3: 90, 4: 45, 6: 0}[n_]
    names = {3: 'ABC', 4: 'ABCD', 6: 'ABCDEF'}[n_]
    P = {nm_: onc(rot + 360 * i / n_) for i, nm_ in enumerate(names)}
    P['O'] = (0, 0)
    rin = math.cos(math.pi / n_)
    circ = [((0, 0), 1)] if want in ('R', 'a') else [((0, 0), rin)]
    svg = fig(P, polys=[names], circles=circ, hide=list(names) + ['O'])

    def chk():
        a_ = math.sqrt(float(side2))
        # вершины правильного n-угольника со стороной a_: радиус подбираем по расстоянию между соседними вершинами
        Rr = 1.0
        pts = [onc(360 * i / n_, Rr) for i in range(n_)]
        s_ = dist(pts[0], pts[1])
        pts = [(x * a_ / s_, y * a_ / s_) for x, y in pts]
        O_ = (0.0, 0.0)
        Rv_ = dist(O_, pts[0])
        rv_ = dist(O_, lerp(pts[0], pts[1], 0.5))
        if mode == 'tri_h':
            hh = dist(pts[0], lerp(pts[1], pts[2], 0.5))
            if not ok(hh, str(h)):
                return False
        val = {'R': Rv_, 'r': rv_, 'a': a_}[want]
        return ok(val, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


# ================================================================ №2. Векторы

VA, VB = 'a⃗', 'b⃗'


def vt(v):
    """Координаты вектора в условии: (3; −4)."""
    return f'({tnum(v[0])}; {tnum(v[1])})'


def comb_txt(k, m, u=VA, w=VB):
    """k·a + m·b → '3a⃗ − 2b⃗' (без единиц)."""
    def term(c, v, first):
        if c == 0:
            return ''
        s_ = '' if abs(c) == 1 else str(abs(c))
        if first:
            return ('−' if c < 0 else '') + s_ + v
        return (' − ' if c < 0 else ' + ') + s_ + v
    out = term(k, u, True)
    return out + term(m, w, not out)


def svg_vecs(vecs, x0, x1, y0, y1, cell=24):
    """Векторы на клетчатой координатной плоскости. vecs — [((sx, sy), (dx, dy), 'a')], всё в клетках;
    окно [x0; x1] × [y0; y1] (целые), ось абсцисс и ординат проходит через 0."""
    w, h = (x1 - x0) * cell + 24, (y1 - y0) * cell + 24
    X_ = lambda x: 12 + (x - x0) * cell
    Y_ = lambda y: 12 + (y1 - y) * cell
    out = '<defs><marker id="va" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">' \
          f'<path d="M0 0L10 5L0 10z" fill="{BLUE}"/></marker></defs>'
    out += f'<g stroke="{GRID}" stroke-width="1">'
    out += ''.join(f'<line x1="{X_(i)}" y1="{Y_(y0)}" x2="{X_(i)}" y2="{Y_(y1)}"/>' for i in range(x0, x1 + 1))
    out += ''.join(f'<line x1="{X_(x0)}" y1="{Y_(j)}" x2="{X_(x1)}" y2="{Y_(j)}"/>' for j in range(y0, y1 + 1))
    out += '</g>'
    if y0 <= 0 <= y1:
        out += f'<line x1="{X_(x0)}" y1="{Y_(0)}" x2="{X_(x1) + 8}" y2="{Y_(0)}" stroke="{INK}" stroke-width="1.3" marker-end="url(#a)"/>'
        out += f'<text x="{X_(x1) - 2}" y="{Y_(0) + 16}" font-style="italic">x</text>'
    if x0 <= 0 <= x1:
        out += f'<line x1="{X_(0)}" y1="{Y_(y0)}" x2="{X_(0)}" y2="{Y_(y1) - 8}" stroke="{INK}" stroke-width="1.3" marker-end="url(#a)"/>'
        out += f'<text x="{X_(0) - 14}" y="{Y_(y1) + 4}" font-style="italic">y</text>'
    out += (f'<text x="{X_(0) - 11}" y="{Y_(0) + 14}">0</text><text x="{X_(1) - 3}" y="{Y_(0) + 14}">1</text>'
            f'<text x="{X_(0) - 11}" y="{Y_(1) + 4}">1</text>')
    for (sx, sy), (dx, dy), name in vecs:
        ax, ay, bx, by = X_(sx), Y_(sy), X_(sx + dx), Y_(sy + dy)
        out += f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{BLUE}" stroke-width="2.4" marker-end="url(#va)"/>'
        ln = math.hypot(bx - ax, by - ay)
        nx, ny = -(by - ay) / ln, (bx - ax) / ln
        mx, my = (ax + bx) / 2 + nx * 13, (ay + by) / 2 + ny * 13
        out += (f'<text x="{mx - 4:.1f}" y="{my + 5:.1f}" font-size="15" font-style="italic" fill="{BLUE}">{name}</text>'
                f'<line x1="{mx - 4:.1f}" y1="{my - 8:.1f}" x2="{mx + 6:.1f}" y2="{my - 8:.1f}" stroke="{BLUE}" stroke-width="1"/>'
                f'<path d="M{mx + 6:.1f} {my - 8:.1f}l-3 -2v4z" fill="{BLUE}"/>')
    return _svg(w, h, out)


def grid_pair(r, lim=6):
    """Два неколлинеарных вектора с целыми координатами и их начала в окне, куда помещаются стрелки."""
    for _ in range(50):
        a = (r.randint(-lim, lim), r.randint(-lim, lim))
        b = (r.randint(-lim, lim), r.randint(-lim, lim))
        if a == (0, 0) or b == (0, 0) or a[0] * b[1] - a[1] * b[0] == 0:
            continue
        if abs(a[0]) + abs(a[1]) < 3 or abs(b[0]) + abs(b[1]) < 3:
            continue
        return a, b
    return None


def grid_layout(r, a, b):
    """Размещение двух векторов в окне с осями: возвращает (vecs, x0, x1, y0, y1)."""
    x0, y0 = -1, -1
    wa, ha = abs(a[0]), abs(a[1])
    wb, hb = abs(b[0]), abs(b[1])
    sa = (r.randint(1, 2) + (wa if a[0] < 0 else 0), r.randint(1, 2) + (ha if a[1] < 0 else 0))
    sb = (sa[0] + max(wa, 1) * (1 if a[0] >= 0 else 0) + r.randint(1, 2) + (wb if b[0] < 0 else 0),
          r.randint(1, 3) + (hb if b[1] < 0 else 0))
    pts = [sa, (sa[0] + a[0], sa[1] + a[1]), sb, (sb[0] + b[0], sb[1] + b[1])]
    x1 = max(p[0] for p in pts) + 1
    y1 = max(p[1] for p in pts) + 1
    return [(sa, a, 'a'), (sb, b, 'b')], x0, x1, y0, y1


@proto('ep02-dot', 'ege-prof', 2, 'Скалярное произведение векторов по координатам',
       invariant='Скалярное произведение равно сумме произведений соответствующих координат.',
       varies='Координаты векторов (в том числе отрицательные), форма записи инструкции.',
       answer_rule='a⃗ · b⃗ = x₁x₂ + y₁y₂.',
       fipi=r'Даны векторы[^.]*\. Найдите скалярное произведение a → ⋅ b →',
       mistakes=['перемножают x₁ на y₂', 'теряют знак при отрицательных координатах'],
       kim=kim(2, 'Как в КИМ: «Даны векторы a⃗(…) и b⃗(…). Найдите скалярное произведение a⃗ · b⃗.»; ответ — целое число.'))
def gen_ep02_dot(r):
    a = (r.randint(-15, 15), r.randint(-15, 15))
    b = (r.randint(-15, 15), r.randint(-30, 30))
    if 0 in a and 0 in b or a == (0, 0) or b == (0, 0):
        return None
    ans = a[0] * b[0] + a[1] * b[1]
    q = pick(r, f'Даны векторы {VA}{vt(a)}, {VB}{vt(b)}. Вычислите {VA} · {VB}.',
             f'Вычислите скалярное произведение векторов {VA}{vt(a)}, {VB}{vt(b)}.',
             f'Найдите скалярное произведение векторов {VA} и {VB}, если {VA}{vt(a)}, {VB}{vt(b)}.',
             f'Векторы заданы координатами: {VA}{vt(a)}, {VB}{vt(b)}. Найдите {VA} · {VB}.')
    e = f'{VA} · {VB} = {par(a[0])} · {par(b[0])} + {par(a[1])} · {par(b[1])} = {tnum(ans)}.'

    def chk():
        # через длины и угол между векторами
        la, lb = math.hypot(*a), math.hypot(*b)
        ang = math.atan2(b[1], b[0]) - math.atan2(a[1], a[0])
        return ok(la * lb * math.cos(ang), num(ans), 1e-6)
    return pcard(q, num(ans), e=e), chk


LEN_VECS = [(p * k * sx, q * k * sy) for p, q, h in [(3, 4, 5), (4, 3, 5), (5, 12, 13), (12, 5, 13), (8, 15, 17), (15, 8, 17),
                                                      (7, 24, 25), (24, 7, 25), (20, 21, 29), (21, 20, 29)]
            for k in (1, 2, 3) for sx in (1, -1) for sy in (1, -1)] + [(n, 0) for n in range(2, 40)] + [(0, n) for n in range(2, 40)]


@proto('ep02-len-comb', 'ege-prof', 2, 'Длина линейной комбинации векторов по координатам',
       invariant='Находим координаты вектора ka⃗ + mb⃗ покоординатно, затем длину по формуле √(x² + y²).',
       varies='Координаты a⃗ и b⃗, коэффициенты k и m (в том числе отрицательные), формулировка.',
       answer_rule='|ka⃗ + mb⃗| = √((kx₁ + mx₂)² + (ky₁ + my₂)²).',
       fipi=r'Даны векторы[^.]*\. Найдите длину вектора',
       mistakes=['складывают длины векторов вместо координат', 'забывают умножить обе координаты на коэффициент'],
       kim=kim(2, 'Как в КИМ: «Даны векторы … Найдите длину вектора 7a⃗ + b⃗.»; координаты подобраны так, что длина — целое число.'))
def gen_ep02_len_comb(r):
    k = r.choice([1, 1, 2, 3, 4, 5, 6, 7, 8, -1, -2, -3])
    m = r.choice([1, 1, 2, 3, 4, 5, -1, -2, -3, -4, -24, 7, 14])
    if k == m == 1 and r.random() < 0.5:
        return None
    b = (r.randint(-6, 6), r.randint(-7, 7))
    if b == (0, 0):
        return None
    w = r.choice(LEN_VECS)
    ax, ay = w[0] - m * b[0], w[1] - m * b[1]
    if ax % k or ay % k:
        return None
    a = (ax // k, ay // k)
    if a == (0, 0) or max(abs(a[0]), abs(a[1])) > 40:
        return None
    ans = math.isqrt(w[0] ** 2 + w[1] ** 2)
    ct = comb_txt(k, m)
    q = pick(r, f'Даны векторы {VA}{vt(a)}, {VB}{vt(b)}. Найдите |{ct}|.',
             f'Вычислите длину вектора {ct}, где {VA}{vt(a)}, {VB}{vt(b)}.',
             f'Векторы {VA} и {VB} имеют координаты {vt(a)} и {vt(b)} соответственно. Найдите |{ct}|.',
             f'Известны координаты векторов: {VA}{vt(a)}, {VB}{vt(b)}. Найдите модуль вектора {ct}.')
    e = f'{ct} = {vt(w)}, длина √({par(w[0])}² + {par(w[1])}²) = {ans}.'

    def chk():
        v = k * sp.Matrix(a) + m * sp.Matrix(b)
        return same(num(ans), v.norm())
    return pcard(q, num(ans), e=e), chk


@proto('ep02-dot-comb', 'ege-prof', 2, 'Скалярное произведение двух линейных комбинаций векторов',
       invariant='Находим координаты обеих комбинаций, затем их скалярное произведение (или раскрываем скобки).',
       varies='Координаты a⃗, b⃗ и коэффициенты комбинаций.',
       answer_rule='(pa⃗ + qb⃗) · (ra⃗ + sb⃗) — по координатам комбинаций.',
       fipi=r'скалярное произведение векторов a → [+−-]',
       mistakes=['перемножают только a⃗ · b⃗', 'ошибаются в знаке при вычитании векторов'],
       kim=kim(2, 'Как в КИМ: «Даны векторы … Найдите скалярное произведение векторов a⃗ + b⃗ и 7a⃗ − b⃗.»'))
def gen_ep02_dot_comb(r):
    a = (r.randint(-6, 6), r.randint(-6, 6))
    b = (r.randint(-6, 6), r.randint(-6, 6))
    if a == (0, 0) or b == (0, 0) or a == b:
        return None
    p, q_ = r.choice([1, 1, 2, 3]), r.choice([1, -1, 2, -2, 3])
    s1, s2 = r.choice([1, 2, 3, 5, 7]), r.choice([1, -1, 2, -2, -3])
    if (p, q_) == (s1, s2) or (p, q_, s1, s2) == (1, 1, 7, -1):
        return None
    u = (p * a[0] + q_ * b[0], p * a[1] + q_ * b[1])
    v = (s1 * a[0] + s2 * b[0], s1 * a[1] + s2 * b[1])
    ans = u[0] * v[0] + u[1] * v[1]
    if ans == 0 or abs(ans) > 1000:
        return None
    c1, c2 = comb_txt(p, q_), comb_txt(s1, s2)
    q = pick(r, f'Даны векторы {VA}{vt(a)}, {VB}{vt(b)}. Вычислите скалярное произведение ({c1}) · ({c2}).',
             f'Векторы {c1} и {c2} построены по векторам {VA}{vt(a)}, {VB}{vt(b)}. Найдите их скалярное произведение.',
             f'Векторы {VA} и {VB} имеют координаты {vt(a)} и {vt(b)}. Вычислите ({c1}) · ({c2}).')
    e = f'{c1} = {vt(u)}, {c2} = {vt(v)}; произведение {tnum(ans)}.'

    def chk():
        # раскрываем скобки: p·s1·a² + (p·s2 + q·s1)·(a·b) + q·s2·b²
        A_, B_ = sp.Matrix(a), sp.Matrix(b)
        val = p * s1 * A_.dot(A_) + (p * s2 + q_ * s1) * A_.dot(B_) + q_ * s2 * B_.dot(B_)
        return same(num(ans), val)
    return pcard(q, num(ans), e=e), chk


@proto('ep02-dot-angle', 'ege-prof', 2, 'Скалярное произведение через длины и угол между векторами',
       invariant='a⃗ · b⃗ = |a⃗| · |b⃗| · cos φ; по любым трём величинам находим четвёртую.',
       varies='Длины векторов (с корнями при 45° и 30°), угол (0°, 30°, 45°, 60°, 90°, 120°, 135°, 150°, 180°), что ищем: '
              'произведение, угол или длину.',
       answer_rule='a⃗ · b⃗ = |a⃗||b⃗|cos φ; cos φ = a⃗ · b⃗ / (|a⃗||b⃗|).',
       fipi=r'Длины векторов[^.]*угол между ними',
       mistakes=['берут синус вместо косинуса', 'теряют минус при тупом угле'],
       kim=kim(2, 'Как в КИМ: «Длины векторов … равны …, а угол между ними равен …°»; ответ — целое число или конечная дробь.'))
def gen_ep02_dot_angle(r):
    ang = r.choice([60, 60, 120, 120, 45, 135, 30, 150])
    m, n = r.randint(1, 12), r.randint(1, 12)
    cosv = {0: F(1), 60: F(1, 2), 90: F(0), 120: F(-1, 2), 180: F(-1)}.get(ang)
    if ang in (45, 135):
        la_txt, la2 = (f'{m}√2' if m > 1 else '√2'), 2 * m * m
        dot = F(m * n) * (1 if ang == 45 else -1)
    elif ang in (30, 150):
        la_txt, la2 = (f'{m}√3' if m > 1 else '√3'), 3 * m * m
        dot = F(3 * m * n, 2) * (1 if ang == 30 else -1)
    else:
        la_txt, la2 = str(m), m * m
        dot = m * n * cosv
    mode = r.choice(['dot', 'dot', 'angle', 'len'])
    if mode == 'dot':
        ans = dot
        q = pick(r, f'Векторы {VA} и {VB} имеют длины {la_txt} и {n} и образуют угол {ang}°. Найдите {VA} · {VB}.',
                 f'Известно, что |{VA}| = {la_txt}, |{VB}| = {n}, угол между векторами {VA} и {VB} равен {ang}°. Найдите скалярное произведение {VA} · {VB}.',
                 f'Угол между векторами {VA} и {VB} равен {ang}°, |{VA}| = {la_txt}, |{VB}| = {n}. Вычислите скалярное произведение этих векторов.')
        e = f'{VA} · {VB} = {la_txt} · {n} · cos {ang}° = {tnum(ans)}.'
    elif mode == 'angle':
        ans = F(ang)
        q = pick(r, f'Известно, что |{VA}| = {la_txt}, |{VB}| = {n}, {VA} · {VB} = {tnum(dot)}. Найдите угол между векторами {VA} и {VB}. {DEG}',
                 f'Векторы {VA} и {VB} имеют длины {la_txt} и {n}, а их скалярное произведение равно {tnum(dot)}. Найдите угол между этими векторами. {DEG}')
        e = f'cos φ = {tnum(dot)} : ({la_txt} · {n}), φ = {ang}°.'
    else:
        ans = F(n)
        q = pick(r, f'Известно, что |{VA}| = {la_txt}, {VA} · {VB} = {tnum(dot)}, угол между векторами {VA} и {VB} равен {ang}°. Найдите |{VB}|.',
                 f'Скалярное произведение векторов {VA} и {VB} равно {tnum(dot)}, угол между ними {ang}°, а длина {VA} равна {la_txt}. Найдите длину вектора {VB}.')
        e = f'|{VB}| = {tnum(dot)} : ({la_txt} · cos {ang}°) = {n}.'
    if not nice(ans, 2):
        return None

    def chk():
        # строим векторы: a⃗ по оси абсцисс, b⃗ под углом ang
        A_ = (math.sqrt(la2), 0.0)
        B_ = (n * math.cos(math.radians(ang)), n * math.sin(math.radians(ang)))
        d = A_[0] * B_[0] + A_[1] * B_[1]
        if mode == 'dot':
            return ok(d, num(ans))
        if mode == 'angle':
            return ok(d, num(dot)) and ok(vang(A_, (0, 0), B_), num(ans))
        return ok(d, num(dot)) and ok(math.hypot(*B_), num(ans))
    return pcard(q, num(ans), e=e), chk


def _norm_cases():
    """Согласованные данные для ep02-norm: пары векторов с целыми длинами (x, y ≤ 20),
    для которых длина нужной комбинации тоже целая. Ключ — то, что видит ученик."""
    vecs = [(x, y) for x in range(-20, 21) for y in range(-20, 21)
            if (x, y) != (0, 0) and isqrt_exact(x * x + y * y) and x * x + y * y <= 400]
    lens, dots = {}, {}
    for a in vecs:
        for b in vecs:
            la, lb = isqrt_exact(a[0] ** 2 + a[1] ** 2), isqrt_exact(b[0] ** 2 + b[1] ** 2)
            d = a[0] * b[0] + a[1] * b[1]
            if abs(d) == la * lb:
                continue
            for p, q_ in ((1, 1), (1, -1), (2, 1), (1, -2), (2, -1), (3, 1), (1, 2), (3, -1)):
                w = (p * a[0] + q_ * b[0], p * a[1] + q_ * b[1])
                L = isqrt_exact(w[0] ** 2 + w[1] ** 2)
                if L:
                    lens.setdefault((la, lb, d, p, q_), (a, b, L))
            for sg in (1, -1):
                w = (a[0] + sg * b[0], a[1] + sg * b[1])
                L = isqrt_exact(w[0] ** 2 + w[1] ** 2)
                if L:
                    dots.setdefault((la, lb, sg, L), (a, b, d))
    return sorted(lens.items()), sorted(dots.items())


NORM_LEN, NORM_DOT = _norm_cases()


@proto('ep02-norm', 'ege-prof', 2, 'Длина суммы (разности) векторов по длинам и скалярному произведению',
       invariant='Квадрат длины вектора равен его скалярному квадрату: |pa⃗ + qb⃗|² = p²|a⃗|² + 2pq(a⃗ · b⃗) + q²|b⃗|².',
       varies='Длины, скалярное произведение, коэффициенты комбинации; обратная задача — найти a⃗ · b⃗ по длине суммы.',
       answer_rule='|pa⃗ + qb⃗| = √(p²|a⃗|² + 2pq a⃗·b⃗ + q²|b⃗|²); a⃗·b⃗ = (|a⃗ + b⃗|² − |a⃗|² − |b⃗|²)/2.',
       fipi=r'\|\s*a\s*→?\s*\|\s*=',
       mistakes=['считают |a⃗ + b⃗| = |a⃗| + |b⃗|', 'забывают удвоенное скалярное произведение'],
       kim=kim(2, 'Инструкция «Найдите длину вектора …», данные — длины и скалярное произведение; ответ — целое число.'))
def gen_ep02_norm(r):
    # согласованные данные подобраны заранее по целочисленным векторам
    if r.random() < 0.65:
        (la, lb, d, p, q_), (a, b, ans) = r.choice(NORM_LEN)
        mode = 'len'
        ct = comb_txt(p, q_)
        L2 = ans * ans
        q = pick(r, f'Известно, что |{VA}| = {la}, |{VB}| = {lb}, {VA} · {VB} = {tnum(d)}. Найдите длину вектора {ct}.',
                 f'Векторы {VA} и {VB} таковы, что |{VA}| = {la}, |{VB}| = {lb}, а их скалярное произведение равно {tnum(d)}. Найдите |{ct}|.')
        e = f'|{ct}|² = {p * p}·{la}² {"+" if 2 * p * q_ * d >= 0 else "−"} {abs(2 * p * q_ * d)} + {q_ * q_}·{lb}² = {L2}, ответ {ans}.'
    else:
        (la, lb, sg, s_), (a, b, d) = r.choice(NORM_DOT)
        mode = 'dot'
        sign = sg == 1
        ans = d
        ct = f'{VA} + {VB}' if sign else f'{VA} − {VB}'
        q = pick(r, f'Известно, что |{VA}| = {la}, |{VB}| = {lb}, |{ct}| = {s_}. Найдите скалярное произведение {VA} · {VB}.',
                 f'Длины векторов {VA}, {VB} и {ct} равны {la}, {lb} и {s_} соответственно. Найдите {VA} · {VB}.')
        e = f'|{ct}|² = |{VA}|² {"+" if sign else "−"} 2{VA}·{VB} + |{VB}|², отсюда {VA} · {VB} = {tnum(d)}.'

    def chk():
        A_, B_ = sp.Matrix(a), sp.Matrix(b)
        if mode == 'len':
            return (same(str(la), A_.norm()) and same(str(lb), B_.norm()) and same(str(d), A_.dot(B_))
                    and same(num(ans), (p * A_ + q_ * B_).norm()))
        return same(num(ans), A_.dot(B_)) and same(str(s_), (A_ + B_ if sign else A_ - B_).norm())
    return pcard(q, num(ans), e=e), chk


UNIT_LEN = [v for v in LEN_VECS if max(abs(v[0]), abs(v[1])) <= 25] + [(1, 0), (0, 1), (-1, 0), (0, -1), (2, 0), (0, 2), (0, -4), (4, 0)]


@proto('ep02-cos', 'ege-prof', 2, 'Косинус угла (угол) между векторами по координатам',
       invariant='cos φ = (a⃗ · b⃗) / (|a⃗| · |b⃗|); скалярное произведение и длины — по координатам.',
       varies='Координаты векторов, спрашиваем косинус или градусную меру угла (45°, 90°, 135°).',
       answer_rule='cos φ = (x₁x₂ + y₁y₂) / (√(x₁² + y₁²) · √(x₂² + y₂²)).',
       fipi=r'косинус угла между векторами|угол между векторами a',
       mistakes=['забывают разделить на произведение длин', 'путают знак косинуса для тупого угла'],
       maxdec=4, kim=kim(2, 'Инструкции «Найдите косинус угла между векторами …», «Найдите угол между векторами … Ответ дайте в градусах.»'))
def gen_ep02_cos(r):
    if r.random() < 0.65:
        a, b = r.choice(UNIT_LEN), r.choice(UNIT_LEN)
        la, lb = math.isqrt(a[0] ** 2 + a[1] ** 2), math.isqrt(b[0] ** 2 + b[1] ** 2)
        ans = F(a[0] * b[0] + a[1] * b[1], la * lb)
        if ans in (0, 1, -1) or not nice(ans, 4):
            return None
        q = pick(r, f'Даны векторы {VA}{vt(a)}, {VB}{vt(b)}. Найдите косинус угла между ними.',
                 f'Найдите косинус угла между векторами {VA}{vt(a)}, {VB}{vt(b)}.',
                 f'Векторы {VA} и {VB} имеют координаты {vt(a)} и {vt(b)}. Найдите косинус угла между векторами {VA} и {VB}.')
        e = f'cos φ = {tnum(a[0] * b[0] + a[1] * b[1])} : ({la} · {lb}) = {tnum(ans)}.'
        deg = False
    else:
        a = (r.randint(-7, 7), r.randint(-7, 7))
        b = (r.randint(-7, 7), r.randint(-7, 7))
        if a == (0, 0) or b == (0, 0):
            return None
        d = a[0] * b[0] + a[1] * b[1]
        n2 = (a[0] ** 2 + a[1] ** 2) * (b[0] ** 2 + b[1] ** 2)
        c2 = F(d * d, n2)
        if c2 == F(1, 2):
            ans = F(45 if d > 0 else 135)
        elif d == 0:
            ans = F(90)
        else:
            return None
        q = pick(r, f'Даны векторы {VA}{vt(a)}, {VB}{vt(b)}. Найдите градусную меру угла между ними.',
                 f'Найдите угол между векторами {VA}{vt(a)}, {VB}{vt(b)}. {DEG}')
        e = f'a⃗ · b⃗ = {tnum(d)}, cos φ = {tnum(d)} / √{n2}, φ = {ans}°.'
        deg = True

    def chk():
        ang = abs(math.degrees(math.atan2(b[1], b[0]) - math.atan2(a[1], a[0])))
        ang = 360 - ang if ang > 180 else ang
        return ok(ang if deg else math.cos(math.radians(ang)), num(ans))
    return pcard(q, num(ans), e=e), chk


@proto('ep02-param', 'ege-prof', 2, 'Перпендикулярность и коллинеарность векторов: найти координату',
       invariant='Перпендикулярные векторы: скалярное произведение равно нулю; коллинеарные: координаты пропорциональны.',
       varies='Условие (перпендикулярны или коллинеарны), в каком месте неизвестная координата, числа.',
       answer_rule='x₁x₂ + y₁y₂ = 0 или x₁y₂ − x₂y₁ = 0 — линейное уравнение относительно неизвестной.',
       fipi=r'при каком значении[^.]*вектор',
       mistakes=['путают условия перпендикулярности и коллинеарности', 'ошибаются в знаке при решении уравнения'],
       maxdec=2, kim=kim(2, 'Инструкция «При каком значении x векторы … перпендикулярны (коллинеарны)?»; ответ — число.'))
def gen_ep02_param(r):
    p, q_, s_ = r.choice([i for i in range(-9, 10) if i]), r.choice([i for i in range(-9, 10) if i]), r.randint(-9, 9)
    kind = r.choice(['perp', 'perp', 'coll'])
    pos = r.choice([0, 1])            # неизвестная — абсцисса или ордината вектора a⃗
    if kind == 'perp':
        # a⃗ = (x; p) или (p; x), b⃗ = (q; s)
        if pos == 0:
            ans = F(-p * s_, q_)
        else:
            if s_ == 0:
                return None
            ans = F(-p * q_, s_)
    else:
        if pos == 0:
            if s_ == 0:
                return None
            ans = F(p * q_, s_)       # a⃗(x; p) ∥ b⃗(q; s): x·s = p·q
        else:
            ans = F(p * s_, q_)       # a⃗(p; x) ∥ b⃗(q; s): p·s = x·q
    if not nice(ans, 2) or ans == 0:
        return None
    at = f'(x; {tnum(p)})' if pos == 0 else f'({tnum(p)}; x)'
    bt = vt((q_, s_))
    cond = 'перпендикулярны' if kind == 'perp' else 'коллинеарны'
    q = pick(r, f'При каком значении x векторы {VA}{at}, {VB}{bt} {cond}?',
             f'Векторы {VA}{at}, {VB}{bt} {cond}. Найдите x.',
             f'Найдите значение x, при котором векторы {VA}{at}, {VB}{bt} {cond}.')
    e = ('Скалярное произведение равно нулю' if kind == 'perp' else 'Координаты пропорциональны') + f': x = {tnum(ans)}.'

    def chk():
        x = sp.Symbol('x')
        A_ = sp.Matrix([x, p]) if pos == 0 else sp.Matrix([p, x])
        B_ = sp.Matrix([q_, s_])
        eq = A_.dot(B_) if kind == 'perp' else A_[0] * B_[1] - A_[1] * B_[0]
        sol = sp.solve(sp.Eq(eq, 0), x)
        return len(sol) == 1 and same(num(ans), sol[0])
    return pcard(q, num(ans), e=e), chk


@proto('ep02-coord', 'ege-prof', 2, 'Координата линейной комбинации векторов',
       invariant='При сложении векторов и умножении на число координаты складываются и умножаются на то же число.',
       varies='Координаты a⃗ и b⃗, коэффициенты, спрашиваем абсциссу или ординату.',
       answer_rule='Абсцисса ka⃗ + mb⃗ равна kx₁ + mx₂, ордината — ky₁ + my₂.',
       fipi=r'(абсциссу|ординату) вектора',
       mistakes=['путают абсциссу и ординату', 'теряют знак коэффициента'],
       kim=kim(2, 'Инструкция «Найдите абсциссу (ординату) вектора …»; ответ — целое число.'))
def gen_ep02_coord(r):
    a = (r.randint(-12, 12), r.randint(-12, 12))
    b = (r.randint(-12, 12), r.randint(-12, 12))
    if a == (0, 0) or b == (0, 0):
        return None
    k, m = r.choice([2, 3, 4, 5, -2, -3, 1, -1]), r.choice([2, 3, -2, -3, -4, 1, -1, 5])
    if abs(k) == abs(m) == 1:
        return None
    c = r.choice([0, 1])
    ans = k * a[c] + m * b[c]
    ct = comb_txt(k, m)
    nm = 'абсциссу' if c == 0 else 'ординату'
    q = pick(r, f'Даны векторы {VA}{vt(a)}, {VB}{vt(b)}. Найдите {nm} вектора {ct}.',
             f'Найдите {nm} вектора {ct}, если {VA}{vt(a)}, {VB}{vt(b)}.',
             f'Векторы {VA} и {VB} имеют координаты {vt(a)} и {vt(b)}. Найдите {nm} вектора {ct}.')
    e = f'{tnum(k)} · {"(" + tnum(a[c]) + ")" if a[c] < 0 else a[c]} {"+" if m > 0 else "−"} {abs(m)} · {"(" + tnum(b[c]) + ")" if b[c] < 0 else b[c]} = {tnum(ans)}.'

    def chk():
        # координата как проекция на ось: скалярное произведение с ортом
        e_ = sp.Matrix([1, 0]) if c == 0 else sp.Matrix([0, 1])
        v = k * sp.Matrix(a) + m * sp.Matrix(b)
        return same(num(ans), v.dot(e_))
    return pcard(q, num(ans), e=e), chk


@proto('ep02-grid-dot', 'ege-prof', 2, 'Векторы на клетчатой плоскости: скалярное произведение',
       invariant='Координаты векторов считываем по клеткам (конец минус начало), затем скалярное произведение по координатам.',
       varies='Направление и длина векторов на рисунке, их расположение.',
       answer_rule='Координаты по рисунку → x₁x₂ + y₁y₂.',
       fipi=r'На координатной плоскости изображены векторы[^.]*\. Найдите скалярное',
       mistakes=['берут координаты начала или конца вместо разности', 'путают направление вектора'],
       svg=True, kim=kim(2, 'Как в КИМ: векторы с целыми координатами на клетчатой координатной плоскости, «Найдите скалярное произведение a⃗ · b⃗.»'))
def gen_ep02_grid_dot(r):
    pr = grid_pair(r)
    if not pr:
        return None
    a, b = pr
    ans = a[0] * b[0] + a[1] * b[1]
    if ans == 0 and r.random() < 0.7:
        return None
    q = pick(r, f'На клетчатой координатной плоскости построены векторы {VA} и {VB}, их координаты — целые числа (см. рисунок). '
                f'Найдите скалярное произведение {VA} · {VB}.',
             f'По рисунку определите координаты векторов {VA} и {VB} (они целые) и найдите их скалярное произведение.',
             f'Векторы {VA} и {VB} с целыми координатами показаны на клетчатой плоскости. Вычислите {VA} · {VB}.')
    e = f'{VA}{vt(a)}, {VB}{vt(b)}; {VA} · {VB} = {tnum(ans)}.'
    vecs, x0, x1, y0, y1 = grid_layout(r, a, b)
    svg = svg_vecs(vecs, x0, x1, y0, y1)

    def chk():
        # считываем координаты по концам стрелок, как ученик
        (sa, da, _), (sb, db, _) = vecs
        A_ = sp.Matrix([sa[0] + da[0] - sa[0], sa[1] + da[1] - sa[1]])
        B_ = sp.Matrix([sb[0] + db[0] - sb[0], sb[1] + db[1] - sb[1]])
        la, lb = math.hypot(*A_), math.hypot(*B_)
        ang = math.atan2(B_[1], B_[0]) - math.atan2(A_[1], A_[0])
        return ok(la * lb * math.cos(ang), num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep02-grid-len', 'ege-prof', 2, 'Векторы на клетчатой плоскости: длина суммы (комбинации)',
       invariant='Координаты векторов считываем по клеткам, находим координаты комбинации и её длину.',
       varies='Векторы на рисунке, комбинация (a⃗ + b⃗, a⃗ − b⃗, a⃗ + kb⃗, ka⃗ − b⃗).',
       answer_rule='Координаты по рисунку → координаты комбинации → √(x² + y²).',
       fipi=r'На координатной плоскости изображены векторы[^.]*\. Найдите длину',
       mistakes=['складывают длины, а не векторы', 'ошибаются при счёте клеток'],
       svg=True, kim=kim(2, 'Как в КИМ: векторы с целыми координатами на клетчатой плоскости, «Найдите длину вектора a⃗ + 4b⃗.»'))
def gen_ep02_grid_len(r):
    pr = grid_pair(r)
    if not pr:
        return None
    a, b = pr
    k, m = r.choice([(1, 1), (1, 1), (1, -1), (1, 2), (1, 3), (1, 4), (2, 1), (1, -2), (2, -1), (3, 1)])
    w = (k * a[0] + m * b[0], k * a[1] + m * b[1])
    ans = isqrt_exact(w[0] ** 2 + w[1] ** 2)
    if not ans or ans < 2:
        return None
    ct = comb_txt(k, m)
    q = pick(r, f'На клетчатой координатной плоскости построены векторы {VA} и {VB}, их координаты — целые числа (см. рисунок). '
                f'Найдите длину вектора {ct}.',
             f'По рисунку определите координаты векторов {VA} и {VB} (они целые) и найдите длину вектора {ct}.',
             f'Векторы {VA} и {VB} с целыми координатами показаны на клетчатой плоскости. Найдите |{ct}|.')
    e = f'{VA}{vt(a)}, {VB}{vt(b)}; {ct} = {vt(w)}, длина {ans}.'
    vecs, x0, x1, y0, y1 = grid_layout(r, a, b)
    svg = svg_vecs(vecs, x0, x1, y0, y1)

    def chk():
        (sa, da, _), (sb, db, _) = vecs
        v = k * sp.Matrix(da) + m * sp.Matrix(db)
        return same(num(ans), v.norm())
    return pcard(q, num(ans), e=e, svg=svg), chk


# ================================================================ №3. Стереометрия: рисунки

CAB = (0.36, 0.36)          # косоугольная (кабинетная) проекция: x + 0.36y, z + 0.36y
VIEW_CAB = (-0.36, 1.0, -0.36)
TOP = 0.34                  # вид «спереди-сверху» для тел вращения: x, z + 0.34y
VIEW_TOP = (0.0, 1.0, -0.34)


def p_cab(p):
    return (p[0] + CAB[0] * p[1], p[2] + CAB[1] * p[1])


def p_top(p):
    return (p[0], p[2] + TOP * p[1])


def _v(a, b):
    return (b[0] - a[0], b[1] - a[1], b[2] - a[2])


def _cr(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def _dt(u, v):
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]


def hull_faces(V):
    """Грани выпуклого многогранника по вершинам V = {имя: (x, y, z)} (перебор плоскостей).
    Возвращает [(список имён по кругу, внешняя нормаль)]."""
    names = list(V)
    cen = tuple(sum(V[n][i] for n in names) / len(names) for i in range(3))
    faces, seen = [], set()
    for a, b, c in combinations(names, 3):
        n = _cr(_v(V[a], V[b]), _v(V[a], V[c]))
        ln = math.sqrt(_dt(n, n))
        if ln < 1e-9:
            continue
        n = (n[0] / ln, n[1] / ln, n[2] / ln)
        d = [_dt(n, _v(V[a], V[x])) for x in names]
        if all(v <= 1e-9 for v in d) or all(v >= -1e-9 for v in d):
            on = frozenset(x for x, v in zip(names, d) if abs(v) < 1e-9)
            if on in seen:
                continue
            seen.add(on)
            if _dt(n, _v(cen, V[a])) < 0:
                n = (-n[0], -n[1], -n[2])
            fc = tuple(sum(V[x][i] for x in on) / len(on) for i in range(3))
            u = _v(fc, V[next(iter(on))])
            w = _cr(n, u)
            order = sorted(on, key=lambda x: math.atan2(_dt(_v(fc, V[x]), w), _dt(_v(fc, V[x]), u)))
            faces.append((order, n))
    return faces


def poly_items(V, view, proj, inner=None, extra=(), label=True, hide_labels=(), fill_inner=True, dots=()):
    """Рисунок многогранника V (внешнее тело) и вписанного в него многогранника inner (список вершин V
    или словарь новых точек): видимые рёбра сплошные, невидимые — штрихом.
    extra — отрезки [(p, q)] (имена), рисуются синим."""
    faces = hull_faces(V)
    vis = [f for f, n in faces if _dt(n, view) < -1e-9]
    allp = dict(V)
    if isinstance(inner, dict):
        allp.update(inner)
        inner_names = list(inner)
    else:
        inner_names = list(inner or [])

    def on_face(p, f):
        a, b, c = (V[f[0]], V[f[1]], V[f[2]])
        n = _cr(_v(a, b), _v(a, c))
        return abs(_dt(n, _v(a, p))) < 1e-6 * (1 + math.sqrt(_dt(n, n)))

    def visible(p, q):
        return any(on_face(p, f) and on_face(q, f) for f in vis)

    items = []
    edges = set()
    for f, n in faces:
        for i in range(len(f)):
            e = frozenset((f[i], f[(i + 1) % len(f)]))
            edges.add(e)
    for e in edges:
        a, b = tuple(e)
        items.append(('L', proj(V[a]), proj(V[b]), 's' if visible(V[a], V[b]) else 'd'))
    if len(inner_names) >= 4:
        sub = {n: allp[n] for n in inner_names}
        ifaces = hull_faces(sub)
        if fill_inner:
            for f, n in ifaces:
                items.insert(0, ('F', [proj(sub[x]) for x in f]))
        iedges = set()
        for f, n in ifaces:
            for i in range(len(f)):
                iedges.add(frozenset((f[i], f[(i + 1) % len(f)])))
        for e in iedges:
            a, b = tuple(e)
            items.append(('L', proj(sub[a]), proj(sub[b]), 'b' if visible(sub[a], sub[b]) else 'bd'))
    for a, b in extra:
        items.append(('L', proj(allp[a]), proj(allp[b]), 'b' if visible(allp[a], allp[b]) else 'bd'))
    for n in dots:
        items.append(('D', proj(allp[n])))
    if label:
        pts2 = [proj(p) for p in V.values()]
        cx = sum(p[0] for p in pts2) / len(pts2)
        cy = sum(p[1] for p in pts2) / len(pts2)
        for n, p in allp.items():
            if n in hide_labels:
                continue
            x, y = proj(p)
            items.append(('T', (x, y), n.translate(SUB) if len(n) > 1 else n, x - cx, y - cy))
    return items


def ell_items(c, rx, ry, st='s', back='d'):
    """Горизонтальная окружность в виде эллипса: передняя половина — st, задняя — back (None — не рисовать)."""
    out = [('E', c, rx, ry, st, 'front')]
    if back:
        out.append(('E', c, rx, ry, back, 'back'))
    return out


def cyl_items(r, h, x=0.0, z=0.0, st='s', back='d'):
    ry = r * TOP
    return (ell_items((x, z), r, ry, st, back) + [('E', (x, z + h), r, ry, st, 'front'), ('E', (x, z + h), r, ry, st, 'back'),
                                                  ('L', (x - r, z), (x - r, z + h), st), ('L', (x + r, z), (x + r, z + h), st)])


def cone_items(r, h, x=0.0, z=0.0, st='s', back='d', apex_up=True):
    ry = r * TOP
    if apex_up:
        return ell_items((x, z), r, ry, st, back) + [('L', (x - r, z), (x, z + h), st), ('L', (x + r, z), (x, z + h), st)]
    # вершиной вниз: основание сверху видно целиком
    return [('E', (x, z + h), r, ry, st, 'front'), ('E', (x, z + h), r, ry, st, 'back'),
            ('L', (x - r, z + h), (x, z), st), ('L', (x + r, z + h), (x, z), st)]


def sphere_items(R, x=0.0, z=0.0, st='s', back='d'):
    return [('C', (x, z), R, st)] + ell_items((x, z), R, R * TOP, st, back)


STY = {'s': f'stroke="{INK}" stroke-width="1.7"', 'd': f'stroke="{INK}" stroke-width="1.1" stroke-dasharray="5 4"',
       'b': f'stroke="{BLUE}" stroke-width="2.1"', 'bd': f'stroke="{BLUE}" stroke-width="1.4" stroke-dasharray="5 4"',
       'r': f'stroke="{RED}" stroke-width="2"'}


def render(items, width=250, pad=22):
    """Плоские примитивы (y вверх) → SVG. L — отрезок, E — половина/целый эллипс, C — окружность,
    F — заливка многоугольника, W — заливка жидкости, T — подпись, D — точка."""
    xs, ys = [], []
    for it in items:
        k = it[0]
        if k == 'L':
            xs += [it[1][0], it[2][0]]
            ys += [it[1][1], it[2][1]]
        elif k == 'E':
            xs += [it[1][0] - it[2], it[1][0] + it[2]]
            ys += [it[1][1] - it[3], it[1][1] + it[3]]
        elif k == 'C':
            xs += [it[1][0] - it[2], it[1][0] + it[2]]
            ys += [it[1][1] - it[2], it[1][1] + it[2]]
        elif k in ('F', 'W'):
            xs += [p[0] for p in it[1]]
            ys += [p[1] for p in it[1]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    span = max(x1 - x0, (y1 - y0) * 0.9, 1e-9)
    k = (width - 2 * pad) / span
    w = (x1 - x0) * k + 2 * pad
    h = (y1 - y0) * k + 2 * pad
    sx = lambda x: pad + (x - x0) * k
    sy = lambda y: pad + (y1 - y) * k
    out = ''
    for it in items:
        kd = it[0]
        if kd == 'F':
            out += f'<polygon points="{" ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in it[1])}" fill="{BLUE}" fill-opacity="0.13" stroke="none"/>'
        elif kd == 'W':
            out += f'<path d="{it[2](sx, sy, k)}" fill="{BLUE}" fill-opacity="0.22" stroke="none"/>'
    for it in items:
        kd = it[0]
        if kd == 'L':
            out += f'<line x1="{sx(it[1][0]):.1f}" y1="{sy(it[1][1]):.1f}" x2="{sx(it[2][0]):.1f}" y2="{sy(it[2][1]):.1f}" {STY[it[3]]}/>'
        elif kd == 'E':
            (cx, cy), rx, ry, st, part = it[1], it[2], it[3], it[4], it[5]
            X0, X1, Y = sx(cx - rx), sx(cx + rx), sy(cy)
            RX, RY = rx * k, max(ry * k, 0.5)
            if part == 'full':
                out += f'<ellipse cx="{sx(cx):.1f}" cy="{Y:.1f}" rx="{RX:.1f}" ry="{RY:.1f}" fill="none" {STY[st]}/>'
            else:
                sweep = 0 if part == 'front' else 1
                out += f'<path d="M{X0:.1f} {Y:.1f}A{RX:.1f} {RY:.1f} 0 0 {sweep} {X1:.1f} {Y:.1f}" fill="none" {STY[st]}/>'
        elif kd == 'C':
            out += f'<circle cx="{sx(it[1][0]):.1f}" cy="{sy(it[1][1]):.1f}" r="{it[2] * k:.1f}" fill="none" {STY[it[3]]}/>'
        elif kd == 'D':
            out += f'<circle cx="{sx(it[1][0]):.1f}" cy="{sy(it[1][1]):.1f}" r="2.3" fill="{INK}"/>'
    for it in items:
        if it[0] == 'T':
            (x, y), t, dx, dy = it[1], it[2], it[3], it[4]
            d = math.hypot(dx, dy) or 1
            tx, ty = sx(x) + dx / d * 11 - 4 * len(t), sy(y) - dy / d * 11 + 5
            out += f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="13" font-style="italic">{t}</text>'
        elif it[0] == 'S':    # свободная подпись (размер)
            (x, y), t = it[1], it[2]
            out += f'<text x="{sx(x):.1f}" y="{sy(y):.1f}" font-size="12" text-anchor="middle">{t}</text>'
    return _svg(w, h, out)


def box_V(a, b, c):
    """Прямоугольный параллелепипед ABCDA1B1C1D1: AB вдоль x, AD вдоль y (вглубь), AA1 вверх."""
    V = {'A': (0, 0, 0), 'B': (a, 0, 0), 'C': (a, b, 0), 'D': (0, b, 0)}
    V.update({n + '1': (x, y, z + c) for n, (x, y, z) in list(V.items())})
    return V


def prism_V(s=3.0, h=3.2):
    """Правильная треугольная призма ABCA1B1C1: B — передняя вершина основания, AC — задняя сторона."""
    V = {'A': (0, 0, 0), 'B': (s / 2, -s * math.sqrt(3) / 2 * 0.8, 0), 'C': (s, 0, 0)}
    V.update({n + '1': (x, y, z + h) for n, (x, y, z) in list(V.items())})
    return V


def draw_dims(a, b, c):
    """Пропорции для рисунка: не даём телу стать слишком плоским или длинным."""
    m = max(a, b, c)
    return tuple(max(0.45, v / m) * 3 for v in (a, b, c))


def hull_volume(V):
    """Точный объём выпуклого многогранника (вершины — Fraction/int): сумма тетраэдров из внутренней точки."""
    names = list(V)
    fl = {n: tuple(float(c) for c in V[n]) for n in names}
    cen = tuple(sum(F(V[n][i]) for n in names) / len(names) for i in range(3))
    vol = F(0)
    for f, _ in hull_faces(fl):
        for i in range(1, len(f) - 1):
            pts = [V[f[0]], V[f[i]], V[f[i + 1]]]
            m = sp.Matrix([[F(p[j]) - cen[j] for j in range(3)] for p in pts])
            vol += abs(F(str(m.det()))) / 6
    return vol


def sub1(s_):
    """'A1' → 'A₁' в тексте условия."""
    return s_.translate(SUB)


BOXN = 'ABCDA₁B₁C₁D₁'


# ================================================================ №3. Стереометрия


@proto('ep03-box-pyr', 'ege-prof', 3, 'Пирамида с вершинами в вершинах прямоугольного параллелепипеда',
       invariant='Многогранник — пирамида: основание лежит в грани параллелепипеда, высота равна ребру; V = S·h/3.',
       varies='Измерения параллелепипеда, какие вершины взяты (треугольная пирамида — объём abc/6, четырёхугольная — abc/3), '
              'какие рёбра названы.',
       answer_rule='Треугольная пирамида: V = (ab/2)·c/3 = abc/6; четырёхугольная: V = ab·c/3.',
       fipi=r'точки A , B , C , (B 1|D , [ABCD] 1) \.|вершины A , B , C , D , [AB] 1 прямоугольного',
       mistakes=['забывают множитель 1/3', 'берут площадь всей грани вместо треугольника'],
       svg=True, kim=kim(3, 'Как в КИМ: «В прямоугольном параллелепипеде ABCDA₁B₁C₁D₁ известно, что AB = …, BC = …, AA₁ = …. '
                            'Найдите объём многогранника, вершинами которого являются точки …»; ответ — целое число.'))
def gen_ep03_box_pyr(r):
    a, b, c = r.randint(2, 12), r.randint(2, 12), r.randint(2, 12)
    kind = r.choice(['tri', 'tri', 'quad'])
    bottom, top = ['A', 'B', 'C', 'D'], ['A1', 'B1', 'C1', 'D1']
    flip = r.random() < 0.25
    if flip:
        bottom, top = top, bottom
    if kind == 'tri':
        base = r.sample(bottom, 3)
        base.sort(key=lambda x: 'ABCD'.index(x[0]))
        apex = r.choice(top)
        verts = base + [apex]
        ans = F(a * b * c, 6)
    else:
        verts = sorted(bottom, key=lambda x: 'ABCD'.index(x[0])) + [r.choice(top)]
        ans = F(a * b * c, 3)
    if ans.denominator != 1 or ans > 600:
        return None
    e2 = r.choice(['BC', 'AD'])
    e3 = r.choice(['AA1', 'BB1', 'CC1', 'DD1'])
    vt_ = ', '.join(sub1(v) for v in verts)
    E = f'AB = {a}, {e2} = {b}, {sub1(e3)} = {c}'
    q = pick(r, f'Длины рёбер прямоугольного параллелепипеда {BOXN}: {E}. Найдите объём многогранника с вершинами {vt_}.',
             f'Рёбра AB, {e2} и {sub1(e3)} прямоугольного параллелепипеда {BOXN} равны {a}, {b} и {c} соответственно. '
             f'Найдите объём многогранника, вершины которого — точки {vt_}.',
             f'Точки {vt_} — вершины прямоугольного параллелепипеда {BOXN}, в котором {E}. Найдите объём многогранника '
             f'с вершинами в этих точках.')
    e = (f'Это треугольная пирамида: V = 1/3 · ({a} · {b} : 2) · {c} = {tnum(ans)}.' if kind == 'tri' else
         f'Это четырёхугольная пирамида: V = 1/3 · {a} · {b} · {c} = {tnum(ans)}.')
    V = box_V(*draw_dims(a, b, c))
    svg = render(poly_items(V, VIEW_CAB, p_cab, inner=verts))

    def chk():
        Vx = box_V(a, b, c)
        return ok(hull_volume({n: Vx[n] for n in verts}), num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


PRISM6 = [['A', 'B', 'C', 'A1', 'B1', 'C1'], ['A', 'C', 'D', 'A1', 'C1', 'D1'], ['A', 'B', 'D', 'A1', 'B1', 'D1'],
          ['B', 'C', 'D', 'B1', 'C1', 'D1'], ['A', 'B', 'C', 'D', 'A1', 'B1'], ['A', 'B', 'C', 'D', 'C1', 'D1'],
          ['A', 'B', 'C', 'D', 'B1', 'C1'], ['A', 'B', 'C', 'D', 'A1', 'D1'], ['A1', 'B1', 'C1', 'D1', 'A', 'B'],
          ['A1', 'B1', 'C1', 'D1', 'C', 'D']]


@proto('ep03-box-prism', 'ege-prof', 3, 'Треугольная призма с вершинами в вершинах прямоугольного параллелепипеда',
       invariant='Многогранник — прямая треугольная призма, отсекаемая от параллелепипеда диагональной плоскостью; '
                 'её объём — половина объёма параллелепипеда.',
       varies='Измерения параллелепипеда и набор из шести вершин (разные диагональные сечения), названия рёбер.',
       answer_rule='V = abc/2.',
       fipi=r'параллелепипед[^.]*\. Найдите объём многогранника[^.]*точки A , B , C , (A 1 , B 1 , C 1|D , A 1 , B 1)',
       mistakes=['считают объём как у пирамиды (делят на 3 или 6)', 'не узнают призму в «лежачем» положении'],
       svg=True, kim=kim(3, 'Как в КИМ: «Найдите объём многогранника, вершинами которого являются точки A, B, C, A₁, B₁, C₁»; ответ — целое или «,5».'))
def gen_ep03_box_prism(r):
    a, b, c = r.randint(2, 14), r.randint(2, 14), r.randint(2, 14)
    verts = r.choice(PRISM6)
    ans = F(a * b * c, 2)
    if ans > 1500:
        return None
    e2 = r.choice(['BC', 'AD'])
    e3 = r.choice(['AA1', 'BB1', 'CC1', 'DD1'])
    vt_ = ', '.join(sub1(v) for v in verts)
    E = f'AB = {a}, {e2} = {b}, {sub1(e3)} = {c}'
    q = pick(r, f'Длины рёбер прямоугольного параллелепипеда {BOXN}: {E}. Найдите объём многогранника с вершинами {vt_}.',
             f'Рёбра AB, {e2} и {sub1(e3)} прямоугольного параллелепипеда {BOXN} равны {a}, {b} и {c} соответственно. '
             f'Найдите объём многогранника, вершины которого — точки {vt_}.',
             f'Точки {vt_} — вершины прямоугольного параллелепипеда {BOXN}, в котором {E}. Найдите объём многогранника '
             f'с вершинами в этих точках.')
    e = f'Многогранник — треугольная призма, половина параллелепипеда: V = {a} · {b} · {c} : 2 = {tnum(ans)}.'
    V = box_V(*draw_dims(a, b, c))
    svg = render(poly_items(V, VIEW_CAB, p_cab, inner=verts))

    def chk():
        Vx = box_V(a, b, c)
        return ok(hull_volume({n: Vx[n] for n in verts}), num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep03-prism-part', 'ege-prof', 3, 'Часть правильной треугольной призмы: пирамида с вершинами в вершинах призмы',
       invariant='Пирамида с основанием — основанием призмы и вершиной на другом основании занимает треть призмы; '
                 'оставшиеся пять вершин дают четырёхугольную пирамиду объёмом 2/3 призмы.',
       varies='Площадь основания, боковое ребро, набор вершин (четыре или пять).',
       answer_rule='V(призмы) = S·h; треугольная пирамида S·h/3; пятивершинник 2S·h/3.',
       fipi=r'правильн\w* треугольн\w* призм[^.]*площадь основания',
       mistakes=['забывают множитель 1/3', 'для пяти вершин берут половину призмы'],
       svg=True, kim=kim(3, 'Как в КИМ: «…вершинами которого являются вершины A, B, C, C₁ правильной треугольной призмы…, '
                            'площадь основания которой равна …, а боковое ребро равно …»'))
def gen_ep03_prism_part(r):
    S, h = r.randint(2, 24), r.randint(2, 15)
    kind = r.choice(['four', 'four', 'five'])
    bottom, top = ['A', 'B', 'C'], ['A1', 'B1', 'C1']
    if r.random() < 0.3:
        bottom, top = top, bottom
    if kind == 'four':
        verts = bottom + [r.choice(top)]
        ans = F(S * h, 3)
    else:
        drop = r.choice(top)
        verts = bottom + [x for x in top if x != drop]
        ans = F(2 * S * h, 3)
    if ans.denominator != 1:
        return None
    verts.sort(key=lambda x: (len(x), x))
    vt_ = ', '.join(sub1(v) for v in verts)
    PR = 'ABCA₁B₁C₁'
    q = pick(r, f'Площадь основания правильной треугольной призмы {PR} равна {S}, боковое ребро равно {h}. Найдите объём '
                f'многогранника с вершинами в точках {vt_}.',
             f'В правильной треугольной призме {PR} боковое ребро равно {h}, а площадь основания равна {S}. '
             f'Найдите объём многогранника, вершины которого — точки {vt_}.',
             f'Точки {vt_} — вершины правильной треугольной призмы {PR}, у которой площадь основания {S}, а боковое ребро {h}. '
             f'Найдите объём многогранника с вершинами в этих точках.')
    e = (f'Треугольная пирамида: V = 1/3 · {S} · {h} = {tnum(ans)}.' if kind == 'four' else
         f'Призма без треугольной пирамиды: {S} · {h} − {S} · {h} : 3 = {tnum(ans)}.')
    V = prism_V()
    svg = render(poly_items(V, VIEW_CAB, p_cab, inner=verts))

    def chk():
        side = math.sqrt(4 * S / math.sqrt(3))
        Vx = {'A': (0.0, 0.0, 0.0), 'B': (side, 0.0, 0.0), 'C': (side / 2, side * math.sqrt(3) / 2, 0.0)}
        Vx.update({n + '1': (x, y, float(h)) for n, (x, y, _) in list(Vx.items())})
        sub = {n: Vx[n] for n in verts}
        # объём через разбиение на тетраэдры из первой вершины (плавающая точка)
        cen = tuple(sum(p[i] for p in sub.values()) / len(sub) for i in range(3))
        vol = 0.0
        for f, _ in hull_faces(sub):
            for i in range(1, len(f) - 1):
                u, v, w = (_v(cen, sub[f[0]]), _v(cen, sub[f[i]]), _v(cen, sub[f[i + 1]]))
                vol += abs(_dt(u, _cr(v, w))) / 6
        return ok(vol, num(ans), 1e-6)
    return pcard(q, num(ans), e=e, svg=svg), chk


def mid_prism_items(extra_mid=True):
    V = {'A': (0, 0, 0), 'B': (1.6, -1.9, 0), 'C': (3.4, 0, 0)}
    V.update({n + '1': (x, y, z + 3.0) for n, (x, y, z) in list(V.items())})
    M = lerp(V['A'][:2], V['B'][:2], 0.5)
    N = lerp(V['C'][:2], V['B'][:2], 0.5)
    inner = {'B': V['B'], 'B1': V['B1'], 'M': (M[0], M[1], 0), 'N': (N[0], N[1], 0), 'M1': (M[0], M[1], 3.0),
             'N1': (N[0], N[1], 3.0)}
    return render(poly_items(V, VIEW_CAB, p_cab, inner=inner, label=False))


@proto('ep03-mid-vol', 'ege-prof', 3, 'Плоскость через среднюю линию основания призмы: объём отсечённой призмы',
       invariant='Отсечённая призма имеет ту же высоту, а её основание — треугольник, отсечённый средней линией '
                 '(площадь в 4 раза меньше), поэтому объём в 4 раза меньше.',
       varies='Прямая или обратная задача, число, призма произвольная или правильная, формулировка.',
       answer_rule='V(отсечённой) = V/4; V = 4·V(отсечённой).',
       fipi=r'^(?!.*боковой поверхности)(?=.*средн\w* лини\w* основания)(?=.*объём)',
       mistakes=['делят объём пополам (как длину)', 'путают с отношением боковых поверхностей'],
       svg=True, kim=kim(3, 'Как в КИМ: «Через среднюю линию основания треугольной призмы … проведена плоскость, параллельная боковому ребру».'))
def gen_ep03_mid_vol(r):
    reverse = r.random() < 0.45
    reg = r.random() < 0.3
    pr = 'правильной треугольной призмы' if reg else 'треугольной призмы'
    if not reverse:
        V_ = r.randrange(8, 400, 4)
        ans = F(V_, 4)
        q = pick(r, f'Объём {pr} равен {V_}. Плоскость, параллельная боковому ребру, проходит через среднюю линию основания '
                    f'и отсекает от призмы меньшую треугольную призму. Найдите её объём.',
                 f'Треугольная призма{" правильная и" if reg else ""} имеет объём {V_}. Через среднюю линию её основания '
                 f'провели плоскость параллельно боковому ребру. Найдите объём треугольной призмы, которую отсекает эта плоскость.')
        e = f'Площадь основания отсечённой призмы в 4 раза меньше, высота та же: {V_} : 4 = {tnum(ans)}.'
    else:
        v = r.randint(2, 150)
        ans = F(4 * v)
        q = pick(r, f'Плоскость, параллельная боковому ребру {pr}, проходит через среднюю линию основания и отсекает '
                    f'треугольную призму объёмом {v}. Найдите объём исходной призмы.',
                 f'От треугольной призмы плоскостью, проходящей через среднюю линию основания параллельно боковому ребру, '
                 f'отсекли призму объёмом {v}. Найдите объём исходной призмы.')
        e = f'Объём отсечённой призмы — четверть исходного: 4 · {v} = {tnum(ans)}.'
    if not nice(ans, 2):
        return None
    svg = mid_prism_items()

    def chk():
        A_, B_, C_ = (0, 0, 0), (F(7), F(2), 0), (F(3), F(5), 0)
        hgt = F(3)
        M_ = tuple((A_[i] + B_[i]) / 2 for i in range(2)) + (0,)
        N_ = tuple((C_[i] + B_[i]) / 2 for i in range(2)) + (0,)
        up = lambda p: (p[0], p[1], hgt)
        big = hull_volume({'A': A_, 'B': B_, 'C': C_, 'A1': up(A_), 'B1': up(B_), 'C1': up(C_)})
        small = hull_volume({'B': B_, 'M': M_, 'N': N_, 'B1': up(B_), 'M1': up(M_), 'N1': up(N_)})
        k = big / small
        return ok(V_ / k if not reverse else v * k, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep03-mid-side', 'ege-prof', 3, 'Плоскость через среднюю линию основания призмы: боковая поверхность',
       invariant='Периметр основания отсечённой призмы равен половине периметра исходного основания (средняя линия — '
                 'половина третьей стороны), высота та же, поэтому боковая поверхность вдвое меньше.',
       varies='Прямая или обратная задача, число, формулировка.',
       answer_rule='S(бок. отсечённой) = S/2; S = 2·S(бок. отсечённой).',
       fipi=r'средн\w* лини\w* основания.*боковой поверхности|боковой поверхности.*средн\w* лини\w* основания',
       mistakes=['делят на 4, как для объёма', 'учитывают площадь сечения как боковую грань исходной призмы'],
       svg=True, kim=kim(3, 'Как в КИМ: «Площадь боковой поверхности треугольной призмы равна … Через среднюю линию основания …»'))
def gen_ep03_mid_side(r):
    reverse = r.random() < 0.45
    if not reverse:
        S = r.randrange(6, 300, 2)
        ans = F(S, 2)
        q = pick(r, f'Боковая поверхность треугольной призмы имеет площадь {S}. Через среднюю линию основания провели '
                    f'плоскость, параллельную боковому ребру. Найдите площадь боковой поверхности отсечённой ею треугольной призмы.',
                 f'Плоскость, параллельная боковому ребру треугольной призмы, содержит среднюю линию её основания. '
                 f'Исходная призма имеет боковую поверхность площадью {S}. Найдите площадь боковой поверхности меньшей призмы, '
                 f'которую отсекает эта плоскость.')
        e = f'Периметр основания отсечённой призмы вдвое меньше, высота та же: {S} : 2 = {tnum(ans)}.'
    else:
        s_ = r.randint(3, 150)
        ans = F(2 * s_)
        q = pick(r, f'Плоскость, проходящая через среднюю линию основания треугольной призмы параллельно боковому ребру, '
                    f'отсекает призму с площадью боковой поверхности {s_}. Найдите площадь боковой поверхности исходной призмы.',
                 f'Через среднюю линию основания треугольной призмы параллельно боковому ребру проведена плоскость. '
                 f'У отсечённой призмы боковая поверхность имеет площадь {s_}. Найдите площадь боковой поверхности исходной призмы.')
        e = f'Боковая поверхность отсечённой призмы вдвое меньше: 2 · {s_} = {tnum(ans)}.'
    svg = mid_prism_items()

    def chk():
        A_, B_, C_ = (0.0, 0.0), (7.0, 2.0), (3.0, 5.0)
        M_, N_ = lerp(A_, B_, 0.5), lerp(C_, B_, 0.5)
        per_big = dist(A_, B_) + dist(B_, C_) + dist(C_, A_)
        per_small = dist(B_, M_) + dist(M_, N_) + dist(N_, B_)
        k = per_big / per_small            # высота общая, отношение боковых поверхностей = отношение периметров
        return ok(S / k if not reverse else s_ * k, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep03-cube-cut', 'ege-prof', 3, 'Призма, отсекаемая от куба (параллелепипеда) плоскостью через середины рёбер',
       invariant='Отсечённая призма имеет ту же высоту, а её основание — прямоугольный треугольник с катетами-половинами '
                 'рёбер, т. е. 1/8 площади грани; объём — 1/8 объёма.',
       varies='Куб или прямоугольный параллелепипед, прямая или обратная задача.',
       answer_rule='V(призмы) = V/8; V = 8·V(призмы).',
       fipi=r'отсекаемой от куба',
       mistakes=['берут половину или четверть вместо восьмой части', 'считают основание треугольником с катетами-рёбрами'],
       svg=True, kim=kim(3, 'Как в КИМ: «…плоскостью, проходящей через середины двух рёбер, выходящих из одной вершины, и параллельной третьему ребру…»'))
def gen_ep03_cube_cut(r):
    reverse = r.random() < 0.4
    body = r.choice(['куба', 'куба', 'прямоугольного параллелепипеда'])
    if not reverse:
        V_ = r.randrange(16, 1000, 8)
        ans = F(V_, 8)
        q = pick(r, f'Объём {body} равен {V_}. Плоскость проходит через середины двух рёбер, выходящих из одной вершины, '
                    f'параллельно третьему ребру, выходящему из той же вершины. Найдите объём треугольной призмы, которую она отсекает.',
                 f'От {body} объёмом {V_} плоскостью отсекли треугольную призму: плоскость проходит через середины двух рёбер '
                 f'с общей вершиной и параллельна третьему ребру с той же вершиной. Найдите объём этой призмы.')
        e = f'Основание призмы — 1/8 грани, высота — ребро: {V_} : 8 = {tnum(ans)}.'
    else:
        v = r.randint(2, 120)
        ans = F(8 * v)
        q = pick(r, f'Плоскость проходит через середины двух рёбер {body}, выходящих из одной вершины, параллельно третьему '
                    f'ребру, выходящему из этой вершины, и отсекает треугольную призму объёмом {v}. Найдите объём {body}.',
                 f'Треугольная призма объёмом {v} отсечена от {body} плоскостью, проходящей через середины двух рёбер с общей '
                 f'вершиной параллельно третьему ребру с той же вершиной. Найдите объём {body}.')
        e = f'Призма составляет 1/8 объёма: 8 · {v} = {tnum(ans)}.'
    dims = (3, 3, 3) if body == 'куба' else (3.6, 2.4, 2.6)
    V = box_V(*dims)
    a, b, c = dims
    inner = {'B': V['B'], 'B1': V['B1'], 'P': (a / 2, 0, 0), 'Q': (a, b / 2, 0), 'P1': (a / 2, 0, c), 'Q1': (a, b / 2, c)}
    svg = render(poly_items(V, VIEW_CAB, p_cab, inner=inner, label=False))

    def chk():
        a_, b_, c_ = F(5), F(3), F(4)
        Vx = box_V(a_, b_, c_)
        whole = hull_volume(Vx)
        piece = hull_volume({'B': Vx['B'], 'P': (a_ / 2, 0, 0), 'Q': (a_, b_ / 2, 0), 'B1': Vx['B1'], 'P1': (a_ / 2, 0, c_),
                             'Q1': (a_, b_ / 2, c_)})
        k = whole / piece
        return ok(V_ / k if not reverse else v * k, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


def fig_cyl_cone(k=1):
    hc = 1.9 / k                                      # высота конуса (при k > 1 она в k раз меньше высоты цилиндра)
    return render(cyl_items(1.0, 1.9) + [('L', (-1.0, 0), (0, hc), 'b'), ('L', (1.0, 0), (0, hc), 'b')])


@proto('ep03-cyl-cone', 'ege-prof', 3, 'Цилиндр и конус с общим основанием и общей высотой: объёмы',
       invariant='Объём конуса равен трети объёма цилиндра с тем же основанием и той же высотой.',
       varies='Что дано (объём цилиндра или конуса), число, формулировка; вариант с высотой цилиндра в k раз больше.',
       answer_rule='V(конуса) = V(цилиндра)/3; при h(цил) = k·h(кон): V(конуса) = V(цил)/(3k).',
       fipi=r'Цилиндр и конус имеют общие основание и высоту\. Объём',
       mistakes=['делят на 2 вместо 3', 'умножают вместо деления'],
       svg=True, kim=kim(3, 'Как в КИМ: «Цилиндр и конус имеют общие основание и высоту. Объём конуса равен … Найдите объём цилиндра.»'))
def gen_ep03_cyl_cone(r):
    mode = r.choice(['cone', 'cyl', 'cone', 'cyl', 'k'])
    if mode == 'cone':
        Vc = r.randrange(3, 450, 3)
        ans = F(Vc, 3)
        q = pick(r, f'Конус и цилиндр имеют одно и то же основание и одинаковую высоту. Найдите объём конуса, если объём цилиндра равен {Vc}.',
                 f'Основание конуса совпадает с нижним основанием цилиндра, а вершина конуса лежит в центре верхнего основания '
                 f'цилиндра. Объём цилиндра равен {Vc}. Найдите объём конуса.')
        e = f'V(конуса) = V(цилиндра) : 3 = {tnum(ans)}.'
    elif mode == 'cyl':
        Vk = r.randint(2, 200)
        ans = F(3 * Vk)
        q = pick(r, f'Конус и цилиндр имеют одно и то же основание и одинаковую высоту. Найдите объём цилиндра, если объём конуса равен {Vk}.',
                 f'Основание конуса совпадает с нижним основанием цилиндра, а вершина конуса лежит в центре верхнего основания '
                 f'цилиндра. Объём конуса равен {Vk}. Найдите объём цилиндра.')
        e = f'V(цилиндра) = 3 · {Vk} = {tnum(ans)}.'
    else:
        k = r.choice([2, 3, 4])
        Vc = r.randrange(3 * k, 300, 3 * k)
        ans = F(Vc, 3 * k)
        q = pick(r, f'Конус и цилиндр имеют общее основание, а высота цилиндра {raz(k)} больше высоты конуса. '
                    f'Объём цилиндра равен {Vc}. Найдите объём конуса.',
                 f'Радиусы оснований цилиндра и конуса равны, высота конуса {raz(k)} меньше высоты цилиндра, а объём цилиндра равен {Vc}. '
                 f'Найдите объём конуса.')
        e = f'V(конуса) = V(цилиндра) : (3 · {k}) = {tnum(ans)}.'
    svg = fig_cyl_cone(k if mode == 'k' else 1)

    def chk():
        z, rr, H = sp.symbols('z r H', positive=True)
        kk = k if mode == 'k' else 1
        hc = H / kk                                   # высота конуса
        v_cone = sp.integrate(sp.pi * (rr * (1 - z / hc)) ** 2, (z, 0, hc))
        v_cyl = sp.integrate(sp.pi * rr ** 2, (z, 0, H))
        ratio = sp.simplify(v_cyl / v_cone)
        return same(num(ans), R(Vc) / ratio if mode != 'cyl' else R(Vk) * ratio)
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep03-cyl-cone-side', 'ege-prof', 3, 'Цилиндр и конус с общим основанием, высота равна радиусу: боковые поверхности',
       invariant='При h = r образующая конуса равна r√2; S(бок. цилиндра) = 2πr², S(бок. конуса) = πr²√2, '
                 'их отношение равно √2.',
       varies='Что дано (боковая поверхность цилиндра или конуса), число перед √2.',
       answer_rule='S(конуса) = S(цилиндра)/√2; S(цилиндра) = S(конуса)·√2.',
       fipi=r'Высота цилиндра равна радиусу основания\. Площадь боковой поверхности',
       mistakes=['считают образующую конуса равной радиусу', 'берут отношение 2 вместо √2'],
       svg=True, kim=kim(3, 'Как в КИМ: «Цилиндр и конус имеют общие основание и высоту. Высота цилиндра равна радиусу основания. '
                            'Площадь боковой поверхности цилиндра равна 3√2…»'))
def gen_ep03_cyl_cone_side(r):
    k = r.randint(2, 40)
    given_cyl = r.random() < 0.5
    if given_cyl:
        ans = F(k)
        g = f'{k}√2'
        q = pick(r, f'У цилиндра и конуса общее основание и общая высота, причём высота равна радиусу основания. Боковая '
                    f'поверхность цилиндра имеет площадь {g}. Найдите площадь боковой поверхности конуса.',
                 f'Конус вписан в цилиндр так, что их основания совпадают, а высота цилиндра совпадает с радиусом основания. '
                 f'Боковая поверхность цилиндра имеет площадь {g}. Вычислите площадь боковой поверхности конуса.')
        e = f'S(цил) = 2πr², S(кон) = πr · r√2; S(кон) = {g} : √2 = {k}.'
    else:
        ans = F(2 * k)
        g = f'{k}√2'
        q = pick(r, f'У цилиндра и конуса общее основание и общая высота, причём высота равна радиусу основания. Боковая '
                    f'поверхность конуса имеет площадь {g}. Найдите площадь боковой поверхности цилиндра.',
                 f'Конус вписан в цилиндр так, что их основания совпадают, а высота цилиндра совпадает с радиусом основания. '
                 f'Боковая поверхность конуса имеет площадь {g}. Вычислите площадь боковой поверхности цилиндра.')
        e = f'S(цил) = S(кон) · √2 = {g} · √2 = {2 * k}.'
    svg = render(cyl_items(1.0, 1.0) + [('L', (-1.0, 0), (0, 1.0), 'b'), ('L', (1.0, 0), (0, 1.0), 'b')], width=250)

    def chk():
        rr = sp.Symbol('r', positive=True)
        s_cyl, s_cone = 2 * sp.pi * rr * rr, sp.pi * rr * sp.sqrt(rr ** 2 + rr ** 2)
        given = k * sp.sqrt(2)
        rv = sp.solve(sp.Eq(s_cyl if given_cyl else s_cone, given), rr)[0]
        return same(num(ans), (s_cone if given_cyl else s_cyl).subs(rr, rv))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep03-ball-cyl', 'ege-prof', 3, 'Шар, вписанный в цилиндр: объём и площадь поверхности',
       invariant='У цилиндра, описанного около шара, высота равна диаметру; V(шара) = 2/3 V(цилиндра), '
                 'S(шара) = 2/3 S(полной поверхности цилиндра).',
       varies='Объём или площадь поверхности, что дано (шар или цилиндр), формулировка («вписан», «описан около»).',
       answer_rule='V(шара) = 2V(цил)/3; V(цил) = 3V(шара)/2; S(шара) = 2S(цил)/3.',
       fipi=r'(Шар[^.]*вписан в цилиндр|Цилиндр[^.]*описан около шара)',
       mistakes=['забывают, что высота цилиндра равна диаметру', 'для поверхности берут только боковую поверхность цилиндра'],
       svg=True, kim=kim(3, 'Как в КИМ: «Цилиндр, объём которого равен …, описан около шара. Найдите объём шара.»'))
def gen_ep03_ball_cyl(r):
    what = r.choice(['V', 'V', 'S'])
    given_ball = r.random() < 0.5
    x = r.randint(2, 150)
    if given_ball:
        if x % 2:
            return None
        ans = F(3 * x, 2)
    else:
        if x % 3:
            return None
        ans = F(2 * x, 3)
    if what == 'V':
        if given_ball:
            q = pick(r, f'Шар с объёмом {x} помещён в цилиндр так, что касается обоих его оснований и боковой поверхности. Найдите объём цилиндра.',
                     f'Около шара, объём которого равен {x}, описан цилиндр. Найдите объём этого цилиндра.')
        else:
            q = pick(r, f'Объём цилиндра равен {x}. В этот цилиндр вписан шар. Вычислите объём шара.',
                     f'Шар касается обоих оснований и боковой поверхности цилиндра, объём которого равен {x}. Найдите объём шара.')
        e = 'V(шара) = 4/3 πR³, V(цилиндра) = πR² · 2R = 2πR³; отношение 2 : 3.'
    else:
        if given_ball:
            q = pick(r, f'Шар касается обоих оснований и боковой поверхности цилиндра, а площадь поверхности шара равна {x}. Вычислите площадь полной поверхности цилиндра.',
                     f'Около шара с площадью поверхности {x} описан цилиндр. Найдите площадь полной поверхности цилиндра.')
        else:
            q = pick(r, f'Полная поверхность цилиндра, описанного около шара, имеет площадь {x}. Вычислите площадь поверхности шара.',
                     f'Шар касается обоих оснований и боковой поверхности цилиндра. Полная поверхность цилиндра имеет площадь {x}. '
                     f'Найдите площадь поверхности шара.')
        e = 'S(шара) = 4πR², S(цилиндра) = 2πR² + 2πR · 2R = 6πR²; отношение 2 : 3.'
    svg = render(cyl_items(1.0, 2.0) + sphere_items(1.0, z=1.0, st='b', back='bd'))

    def chk():
        Rr = sp.Symbol('R', positive=True)
        if what == 'V':
            ball, cyl = sp.Rational(4, 3) * sp.pi * Rr ** 3, sp.pi * Rr ** 2 * (2 * Rr)
        else:
            ball, cyl = 4 * sp.pi * Rr ** 2, 2 * sp.pi * Rr ** 2 + 2 * sp.pi * Rr * (2 * Rr)
        rv = sp.solve(sp.Eq(ball if given_ball else cyl, x), Rr)[0]
        return same(num(ans), (cyl if given_ball else ball).subs(Rr, rv))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep03-cone-ball', 'ege-prof', 3, 'Конус, вписанный в шар (радиус основания равен радиусу шара): объёмы',
       invariant='Основание конуса — большой круг шара, высота конуса равна радиусу: V(конуса) = πR³/3 = V(шара)/4.',
       varies='Что дано (объём шара или конуса), число, формулировка.',
       answer_rule='V(конуса) = V(шара)/4; V(шара) = 4V(конуса).',
       fipi=r'Конус вписан в шар',
       mistakes=['считают высоту конуса равной диаметру', 'берут отношение 1/3 по аналогии с цилиндром'],
       svg=True, kim=kim(3, 'Как в КИМ: «Конус вписан в шар. Радиус основания конуса равен радиусу шара. Объём шара равен …»'))
def gen_ep03_cone_ball(r):
    given_ball = r.random() < 0.5
    if given_ball:
        x = r.randrange(4, 400, 4)
        ans = F(x, 4)
        q = pick(r, f'Вершина конуса и окружность его основания лежат на сфере, ограничивающей шар объёмом {x}, причём '
                    f'плоскость основания конуса проходит через центр шара. Найдите объём конуса.',
                 f'В шар объёмом {x} вписан конус, радиус основания которого совпадает с радиусом шара. Вычислите объём конуса.')
    else:
        x = r.randint(2, 150)
        ans = F(4 * x)
        q = pick(r, f'Вершина конуса и окружность его основания лежат на сфере, ограничивающей шар, причём плоскость основания '
                    f'конуса проходит через центр шара. Объём конуса равен {x}. Найдите объём шара.',
                 f'Конус с объёмом {x} вписан в шар так, что радиус его основания совпадает с радиусом шара. Вычислите объём шара.')
    e = 'Высота конуса равна R: V(конуса) = πR³/3, V(шара) = 4πR³/3 — в 4 раза больше.'
    svg = render(sphere_items(1.0) + cone_items(1.0, 1.0, st='b', back='bd'))

    def chk():
        Rr, z = sp.symbols('R z', positive=True)
        # объёмы тел вращения интегрированием площадей сечений
        v_ball = sp.integrate(sp.pi * (Rr ** 2 - z ** 2), (z, -Rr, Rr))
        v_cone = sp.integrate(sp.pi * (Rr - z) ** 2, (z, 0, Rr))
        ratio = sp.simplify(v_ball / v_cone)
        return same(num(ans), R(x) / ratio if given_ball else R(x) * ratio)
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep03-sphere-cone', 'ege-prof', 3, 'Сфера, описанная около конуса с центром в центре основания: образующая и радиус',
       invariant='Центр сферы в центре основания, поэтому высота и радиус основания конуса равны радиусу сферы; '
                 'образующая — гипотенуза равнобедренного прямоугольного треугольника: l = R√2.',
       varies='Что дано (радиус сферы или образующая, с корнем из 2), число.',
       answer_rule='l = R√2; R = l/√2.',
       fipi=r'Около конуса описана сфера',
       mistakes=['считают образующую равной радиусу', 'умножают на √2 вместо деления'],
       svg=True, kim=kim(3, 'Как в КИМ: «Около конуса описана сфера (сфера содержит окружность основания конуса и его вершину). '
                            'Центр сферы находится в центре основания конуса.»'))
def gen_ep03_sphere_cone(r):
    k = r.randint(2, 99)
    given_R = r.random() < 0.5
    if given_R:
        ans = F(2 * k)
        q = pick(r, f'Вершина конуса и окружность его основания лежат на сфере радиуса {k}√2, центр которой совпадает с центром '
                    f'основания конуса. Найдите образующую конуса.',
                 f'Сфера радиуса {k}√2 проходит через вершину конуса и через окружность его основания, а её центр — центр основания '
                 f'конуса. Найдите длину образующей конуса.')
        e = f'h = r = R, l = R√2 = {k}√2 · √2 = {2 * k}.'
    else:
        ans = F(k)
        q = pick(r, f'Вершина конуса и окружность его основания лежат на сфере, центр которой совпадает с центром основания '
                    f'конуса. Длина образующей конуса {k}√2. Вычислите радиус сферы.',
                 f'Сфера проходит через вершину конуса и через окружность его основания, а её центр — центр основания конуса. '
                 f'Длина образующей конуса равна {k}√2. Найдите радиус сферы.')
        e = f'l = R√2, R = {k}√2 : √2 = {k}.'
    svg = render(sphere_items(1.0) + cone_items(1.0, 1.0, st='b', back='bd') + [('L', (0, 0), (1.0, 0), 'r')])

    def chk():
        Rr = sp.Symbol('R', positive=True)
        l_expr = sp.sqrt(Rr ** 2 + Rr ** 2)            # катеты: радиус основания и высота
        if given_R:
            return same(num(ans), l_expr.subs(Rr, k * sp.sqrt(2)))
        return same(num(ans), sp.solve(sp.Eq(l_expr, k * sp.sqrt(2)), Rr)[0])
    return pcard(q, num(ans), e=e, svg=svg), chk


def fig_cyl_in_box():
    th = math.radians(22)
    V = {}
    for i, nm in enumerate('ABCD'):
        a_ = th + math.radians(225 + 90 * i)
        x, y = math.sqrt(2) * math.cos(a_), math.sqrt(2) * math.sin(a_)
        V[nm] = (x, y, 0.0)
        V[nm + '1'] = (x, y, 1.8)
    items = poly_items(V, VIEW_TOP, p_top, label=False)
    items += [('E', (0, 1.8), 1.0, TOP, 'b', 'front'), ('E', (0, 1.8), 1.0, TOP, 'b', 'back'),
              ('E', (0, 0), 1.0, TOP, 'bd', 'front'), ('E', (0, 0), 1.0, TOP, 'bd', 'back'),
              ('L', (-1.0, 0), (-1.0, 1.8), 'bd'), ('L', (1.0, 0), (1.0, 1.8), 'bd')]
    return render(items)


@proto('ep03-cyl-box', 'ege-prof', 3, 'Цилиндр, вписанный в прямоугольный параллелепипед',
       invariant='Основание параллелепипеда — квадрат со стороной 2r (окружность вписана в квадрат), высота общая.',
       varies='Радиус и высота цилиндра, что ищем (объём или площадь поверхности параллелепипеда).',
       answer_rule='V = (2r)²·h; S = 2·(2r)² + 4·2r·h.',
       fipi=r'Цилиндр вписан в прямоугольный параллелепипед',
       mistakes=['берут сторону квадрата равной радиусу', 'забывают про две грани-основания'],
       svg=True, kim=kim(3, 'Как в КИМ: «Цилиндр вписан в прямоугольный параллелепипед. Радиус основания и высота цилиндра равны …»'))
def gen_ep03_cyl_box(r):
    rr, h = r.randint(1, 10), r.randint(1, 15)
    what = r.choice(['V', 'V', 'S'])
    same_ = r.random() < 0.3
    if same_:
        h = rr
    ans = F(4 * rr * rr * h) if what == 'V' else F(8 * rr * rr + 8 * rr * h)
    dat = (f'радиус основания {rr} и такую же высоту' if same_ else f'радиус основания {rr} и высоту {h}')
    wt = 'объём' if what == 'V' else 'площадь поверхности'
    q = pick(r, f'Цилиндр имеет {dat}. Он вписан в прямоугольный параллелепипед. Найдите {wt} параллелепипеда.',
             f'Около цилиндра, имеющего {dat}, описан прямоугольный параллелепипед. Вычислите {wt} этого параллелепипеда.',
             f'Основания цилиндра вписаны в основания прямоугольного параллелепипеда, а боковая поверхность цилиндра касается '
             f'боковых граней. Цилиндр имеет {dat}. Найдите {wt} параллелепипеда.')
    e = (f'Основание — квадрат со стороной {2 * rr}: V = {2 * rr}² · {h} = {tnum(ans)}.' if what == 'V' else
         f'S = 2 · {2 * rr}² + 4 · {2 * rr} · {h} = {tnum(ans)}.')
    svg = fig_cyl_in_box()

    def chk():
        # квадрат, описанный около окружности радиуса rr: вершины (±rr; ±rr)
        Vx = box_V(2 * rr, 2 * rr, h)
        if what == 'V':
            return ok(hull_volume(Vx), num(ans))
        faces = hull_faces({n: tuple(float(c) for c in p) for n, p in Vx.items()})
        tot = 0.0
        for f, n in faces:
            pts = [Vx[x] for x in f]
            # площадь грани: половина модуля суммы векторных произведений
            sx_ = [0.0, 0.0, 0.0]
            for i in range(len(pts)):
                c_ = _cr(pts[i], pts[(i + 1) % len(pts)])
                sx_ = [sx_[j] + c_[j] for j in range(3)]
            tot += math.sqrt(_dt(sx_, sx_)) / 2
        return ok(tot, num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep03-scale', 'ege-prof', 3, 'Цилиндр или конус: изменение радиуса и высоты, отношение объёмов',
       invariant='Объём цилиндра (конуса) пропорционален квадрату радиуса и первой степени высоты: V ∝ r²h.',
       varies='Тело (цилиндр, конус, кружки, банки), во сколько раз меняются радиус (диаметр, «шире») и высота, '
              'что ищем (новый объём, во сколько раз изменится объём, отношение объёмов).',
       answer_rule='V₂ = V₁ · (r₂/r₁)² · (h₂/h₁).',
       fipi=r'Дано два цилиндра|Во сколько раз (увеличится|уменьшится) объём конуса|цилиндрическая кружка',
       mistakes=['не возводят отношение радиусов в квадрат', 'путают «в k раз меньше» с «на k меньше»'],
       svg=True, kim=kim(3, 'Как в КИМ: «Дано два цилиндра… У второго высота в 3 раза меньше, а радиус в 2 раза больше…», '
                            '«Во сколько раз увеличится объём конуса…»'))
def gen_ep03_scale(r):
    mode = r.choice(['two_cyl', 'two_cyl', 'cone_times', 'mugs'])
    if mode == 'two_cyl':
        body = r.choice(['цилиндра', 'конуса'])
        V1 = r.randint(2, 120)
        kh = r.choice([1, 2, 3, 4, 5])
        kr = r.choice([1, 2, 3, 4])
        h_up = r.random() < 0.3
        r_up = r.random() < 0.7
        if kh == 1 and kr == 1:
            return None
        fac = (F(kr) ** 2 if r_up else F(1, kr * kr)) * (F(kh) if h_up else F(1, kh))
        ans = V1 * fac
        if not nice(ans, 2) or ans == V1:
            return None
        nm = 'цилиндр' if body == 'цилиндра' else 'конус'
        ht = '' if kh == 1 else f'{"выше" if h_up else "ниже"} первого {raz(kh)}'
        rt_ = '' if kr == 1 else f'радиус его основания {raz(kr)} {"больше" if r_up else "меньше"}'
        parts = f'{ht}, а {rt_}' if ht and rt_ else (ht if ht else f'имеет ту же высоту, но {rt_}')
        q = pick(r, f'Первый {nm} имеет объём {V1}. Второй {nm} {parts}. Найдите объём второго {nm}а.',
                 f'Имеются два {nm}а, объём первого равен {V1}. Второй {parts}. Вычислите объём второго {nm}а.')
        e = f'V ∝ r²h: V₂ = {V1} · {tnum(fac) if finite(fac) else f"{fac.numerator}/{fac.denominator}"} = {tnum(ans)}.'
        ratio_check = (F(kr) if r_up else F(1, kr), F(kh) if h_up else F(1, kh), V1)
        svg = render((cyl_items(0.8, 1.6) + cyl_items(1.2, 0.9, x=2.6)) if nm == 'цилиндр'
                     else (cone_items(0.8, 1.6) + cone_items(1.2, 0.9, x=2.6)))
    elif mode == 'cone_times':
        k = r.randint(2, 15)
        which = r.choice(['h_down', 'r_up', 'r_down', 'h_up'])
        body = r.choice(['конуса', 'цилиндра'])
        ans = F(k * k) if which in ('r_up', 'r_down') else F(k)
        verb = 'увеличится' if which in ('r_up', 'h_up') else 'уменьшится'
        if which in ('r_up', 'r_down'):
            ch = f'радиус его основания {"увеличить" if which == "r_up" else "уменьшить"} {raz(k)}, а высоту оставить прежней'
        else:
            ch = f'его высоту {"увеличить" if which == "h_up" else "уменьшить"} {raz(k)}, а радиус основания не менять'
        past = {'r_up': f'Радиус основания {body} увеличили {raz(k)}, не меняя высоты.',
                'r_down': f'Радиус основания {body} уменьшили {raz(k)}, не меняя высоты.',
                'h_up': f'Высоту {body} увеличили {raz(k)}, не меняя радиуса основания.',
                'h_down': f'Высоту {body} уменьшили {raz(k)}, не меняя радиуса основания.'}[which]
        vpast = 'увеличился' if verb == 'увеличится' else 'уменьшился'
        q = pick(r, f'{past} Во сколько раз {vpast} объём {body}?',
                 f'Как изменится объём {body}, если {ch}? В ответе укажите, во сколько раз {verb} объём.')
        e = f'V ∝ r²h, объём {verb} в {ans} раз.'
        f_r = F(k) if which == 'r_up' else (F(1, k) if which == 'r_down' else F(1))
        f_h = F(k) if which == 'h_up' else (F(1, k) if which == 'h_down' else F(1))
        ratio_check = (f_r, f_h, None)
        svg = render(cone_items(1.0, 1.7) if body == 'конуса' else cyl_items(1.0, 1.6))
    else:
        kh = r.choice([F(2), F(3), F(3, 2), F(4)])
        kw = r.choice([F(3, 2), F(2), F(5, 2), F(3), F(5, 4)])
        ans = kw * kw / kh
        if not nice(ans, 2) or ans == 1:
            return None
        pl, gen_, gpl = r.choice([('банки', 'банки', 'банок'), ('кастрюли', 'кастрюли', 'кастрюль'), ('кружки', 'кружки', 'кружек'),
                                  ('ёмкости', 'ёмкости', 'ёмкостей'), ('вазы', 'вазы', 'ваз')])
        kh_t = {F(2): 'вдвое', F(3): 'втрое', F(3, 2): 'в полтора раза', F(4): 'в 4 раза'}[kh]
        kw_t = {F(3, 2): 'в полтора раза', F(2): 'вдвое', F(5, 2): 'в 2,5 раза', F(3): 'втрое', F(5, 4): 'в 1,25 раза'}[kw]
        q = pick(r, f'Имеются две {pl} цилиндрической формы. Высота первой {kh_t} больше высоты второй, а диаметр дна второй '
                    f'{kw_t} больше диаметра дна первой. Найдите отношение объёма второй {gen_} к объёму первой.',
                 f'У первой из двух цилиндрических {gpl} высота {kh_t} больше, чем у второй, но вторая {kw_t} шире первой. '
                 f'Найдите отношение объёма второй {gen_} к объёму первой.')
        e = f'V₂ : V₁ = ({tnum(kw)})² : {tnum(kh)} = {tnum(ans)}.'
        ratio_check = (kw, 1 / kh, None)
        svg = render(cyl_items(0.6, 2.0) + cyl_items(0.6 * float(kw), 2.0 / float(kh), x=0.8 + 0.6 * float(kw) + 0.5))

    def chk():
        rr, hh = sp.symbols('r h', positive=True)
        fr_, fh_, v1 = ratio_check
        vol = lambda a_, b_: sp.pi * a_ ** 2 * b_ / (3 if (mode != 'mugs' and 'кон' in q[:60]) else 1)
        ratio = sp.simplify(vol(R(fr_) * rr, R(fh_) * hh) / vol(rr, hh))
        if mode == 'two_cyl':
            return same(num(ans), R(v1) * ratio)
        if mode == 'cone_times':
            return same(num(ans), ratio if ratio >= 1 else 1 / ratio)
        return same(num(ans), ratio)
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep03-similar', 'ege-prof', 3, 'Подобные тела: как меняются площадь поверхности и объём',
       invariant='При увеличении линейных размеров в k раз площади поверхности увеличиваются в k², а объёмы — в k³ раз.',
       varies='Тело (куб, шар, правильный тетраэдр, прямоугольный параллелепипед), k, что дано и что ищем '
              '(поверхность по объёму и наоборот, новое значение или «во сколько раз»).',
       answer_rule='S₂/S₁ = k², V₂/V₁ = k³; по отношению объёмов k = ∛(V₂/V₁).',
       fipi=r'Во сколько раз увеличится (площадь поверхности|объём) (куба|шара|тетраэдра)',
       mistakes=['считают, что поверхность меняется в k раз', 'путают k² и k³'],
       svg=True, kim=kim(3, 'Формулировки «Во сколько раз увеличится …, если …» и «… в 8 раз больше …»; ответ — целое число.'))
def gen_ep03_similar(r):
    body = r.choice([('куба', 'ребро', 'рёбра'), ('шара', 'радиус', 'радиусы'), ('правильного тетраэдра', 'ребро', 'рёбра'),
                     ('сферы', 'радиус', 'радиусы')])
    mode = r.choice(['times', 'times', 'from_ratio', 'value'])
    k = r.randint(2, 6)
    if mode == 'times':
        what = r.choice(['площадь поверхности', 'объём']) if body[0] != 'сферы' else 'площадь'
        ans = F(k * k) if what.startswith('площадь') else F(k ** 3)
        q = pick(r, f'Во сколько раз увеличится {what} {body[0]}, если {body[1]} увеличить {raz(k)}?',
                 f'{body[1].capitalize()} {body[0]} увеличили {raz(k)}. Во сколько раз увеличилась {what}?' if what != 'объём' else
                 f'{body[1].capitalize()} {body[0]} увеличили {raz(k)}. Во сколько раз увеличился его объём?')
        e = f'{"Площади" if what != "объём" else "Объёмы"} подобных тел относятся как k{"²" if what != "объём" else "³"}: {tnum(ans)}.'
        kk, kind = k, ('S' if what != 'объём' else 'V')
    elif mode == 'from_ratio':
        if body[0] == 'сферы':
            return None
        ans = F(k * k)
        q = pick(r, f'Объём одного {body[0]} {raz(k ** 3)} больше объёма другого. Во сколько раз площадь поверхности первого {body[0]} '
                    f'больше площади поверхности второго?',
                 f'Даны два {"шара" if body[0] == "шара" else ("куба" if body[0] == "куба" else "правильных тетраэдра")}, объём первого {raz(k ** 3)} больше объёма второго. '
                 f'Во сколько раз площадь поверхности первого больше площади поверхности второго?')
        e = f'k³ = {k ** 3}, k = {k}, площади относятся как k² = {k * k}.'
        kk, kind = k, 'from'
    else:
        if body[0] == 'сферы':
            return None
        what = r.choice(['площадь поверхности', 'объём'])
        v1 = r.randint(2, 60)
        ans = F(v1 * (k * k if what == 'площадь поверхности' else k ** 3))
        if ans > 3000:
            return None
        q = pick(r, f'{what.capitalize()} {body[0]} равна {v1}. Найдите {what} {body[0]}, у которого {body[1]} {raz(k)} больше.'
                 if what != 'объём' else f'Объём {body[0]} равен {v1}. Найдите объём {body[0]}, у которого {body[1]} {raz(k)} больше.',
                 f'{body[1].capitalize()} {body[0]} увеличили {raz(k)}. До увеличения {what} была равна {v1}. Найдите новую {what}.'
                 if what != 'объём' else f'{body[1].capitalize()} {body[0]} увеличили {raz(k)}. До увеличения объём был равен {v1}. Найдите новый объём.')
        e = f'Множитель {k}{"²" if what != "объём" else "³"}: {tnum(ans)}.'
        kk, kind = k, ('S' if what != 'объём' else 'V')
    svg = render(sphere_items(1.0) if body[0] in ('шара', 'сферы') else
                 poly_items(box_V(2, 2, 2), VIEW_CAB, p_cab, label=False) if body[0] == 'куба' else
                 poly_items({'A': (0, 0, 0), 'B': (2.4, -0.8, 0), 'C': (3.0, 1.2, 0), 'D': (1.8, 0.1, 2.2)}, VIEW_CAB, p_cab, label=False))

    def chk():
        # считаем по формулам тела при ребре (радиусе) 1 и kk
        a_ = sp.Symbol('a', positive=True)
        S_ = {'куба': 6 * a_ ** 2, 'шара': 4 * sp.pi * a_ ** 2, 'сферы': 4 * sp.pi * a_ ** 2,
              'правильного тетраэдра': sp.sqrt(3) * a_ ** 2}[body[0]]
        V_ = {'куба': a_ ** 3, 'шара': sp.Rational(4, 3) * sp.pi * a_ ** 3, 'сферы': sp.Rational(4, 3) * sp.pi * a_ ** 3,
              'правильного тетраэдра': a_ ** 3 * sp.sqrt(2) / 12}[body[0]]
        if kind == 'from':
            kv = sp.solve(sp.Eq(V_.subs(a_, a_) / V_.subs(a_, 1), kk ** 3), a_)[0]
            return same(num(ans), sp.simplify(S_.subs(a_, kv) / S_.subs(a_, 1)))
        f_ = S_ if kind == 'S' else V_
        ratio = sp.simplify(f_.subs(a_, kk) / f_.subs(a_, 1))
        return same(num(ans), ratio if mode == 'times' else v1 * ratio)
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep03-ball-section', 'ege-prof', 3, 'Сечение шара через центр и площадь сферы',
       invariant='Сечение через центр — большой круг площади πR²; площадь сферы 4πR², т. е. в 4 раза больше.',
       varies='Что дано (площадь сечения или площадь поверхности), число, формулировка.',
       answer_rule='S(сферы) = 4·S(сечения); S(сечения) = S(сферы)/4.',
       fipi=r'сечения шара плоскостью, проходящей через центр',
       mistakes=['берут отношение 2 или 3', 'путают площадь сечения с площадью полусферы'],
       svg=True, kim=kim(3, 'Как в КИМ: «Площадь сечения шара плоскостью, проходящей через центр шара, равна … Найдите площадь поверхности шара.»'))
def gen_ep03_ball_section(r):
    given_sec = r.random() < 0.6
    if given_sec:
        x = r.randint(2, 250)
        ans = F(4 * x)
        q = pick(r, f'Плоскость проходит через центр шара, и площадь получившегося сечения равна {x}. Найдите площадь поверхности шара.',
                 f'Большой круг шара (сечение плоскостью через центр) имеет площадь {x}. Вычислите площадь поверхности шара.')
        e = f'S(сечения) = πR², S(сферы) = 4πR² = 4 · {x} = {tnum(ans)}.'
    else:
        x = r.randrange(4, 1000, 4)
        ans = F(x, 4)
        q = pick(r, f'Шар имеет поверхность площадью {x}. Его рассекли плоскостью через центр. Найдите площадь сечения.',
                 f'Сфера имеет площадь {x}. Её пересекли плоскостью, проходящей через центр. Найдите площадь получившегося круга.')
        e = f'Площадь большого круга в 4 раза меньше площади сферы: {tnum(ans)}.'
    svg = render([('W', [(-1, -TOP), (1, TOP)], lambda sx, sy, k: f'M{sx(-1):.1f} {sy(0):.1f}A{k:.1f} {k * TOP:.1f} 0 1 0 {sx(1):.1f} {sy(0):.1f}A{k:.1f} {k * TOP:.1f} 0 1 0 {sx(-1):.1f} {sy(0):.1f}z')]
                 + sphere_items(1.0))

    def chk():
        Rr, t = sp.symbols('R t', positive=True)
        sec = sp.integrate(2 * sp.pi * t, (t, 0, Rr))                     # площадь круга по кольцам
        sph = sp.integrate(2 * sp.pi * Rr ** 2 * sp.sin(t), (t, 0, sp.pi))  # площадь сферы по поясам
        ratio = sp.simplify(sph / sec)
        return same(num(ans), R(x) * ratio if given_sec else R(x) / ratio)
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep03-cone-level', 'ege-prof', 3, 'Конический сосуд и сечение конуса, параллельное основанию: объёмы',
       invariant='Жидкость (отсечённый конус) подобна всему конусу; объёмы относятся как куб коэффициента подобия.',
       varies='Уровень (1/2, 1/3, 1/4, 2/3 высоты), что дано и что ищем (сколько долить, объём сосуда, объём отсечённого конуса).',
       answer_rule='V(жидкости) = V(сосуда)·k³; долить V(сосуда) − V(жидкости).',
       fipi=r'сосуде, имеющем форму конуса|Через середину высоты конуса',
       mistakes=['берут отношение объёмов равным отношению высот', 'возводят в квадрат вместо куба'],
       svg=True, kim=kim(3, 'Как в демоверсии: «В сосуде, имеющем форму конуса, уровень жидкости достигает 1/3 высоты. Объём жидкости … '
                            'Сколько миллилитров нужно долить…»; единицы — мл.'))
def gen_ep03_cone_level(r):
    kfr = r.choice([F(1, 2), F(1, 3), F(1, 4), F(2, 3), F(1, 5), F(3, 4)])
    mode = r.choice(['add', 'add', 'full', 'cut'])
    cube = kfr ** 3
    lvl = f'{kfr.numerator}/{kfr.denominator}' if kfr.numerator != 1 or kfr.denominator > 2 else 'половины'
    lvl_txt = f'{kfr.numerator}/{kfr.denominator} высоты' if lvl != 'половины' else 'половины высоты'
    vessel = r.choice(['сосуд', 'бокал', 'воронку с закрытым носиком', 'мерный стакан'])
    if mode in ('add', 'full'):
        v = r.randint(1, 40) * cube.numerator
        full = v / cube
        ans = full - v if mode == 'add' else full
        cap = {'сосуд': 5000, 'бокал': 400, 'воронку с закрытым носиком': 2000, 'мерный стакан': 1000}[vessel]
        if not nice(ans, 1) or full > cap:
            return None
        head = {'сосуд': f'Сосуд в форме конуса стоит вершиной вниз. В него налили {v} мл жидкости, и её уровень достиг {lvl_txt}.',
                'бокал': f'В бокал в форме конуса налили {v} мл вина, и оно заполнило бокал до {lvl_txt}.',
                'воронку с закрытым носиком': f'Коническую воронку с заткнутым носиком поставили вершиной вниз и налили в неё '
                                              f'{v} мл масла; уровень масла достиг {lvl_txt}.',
                'мерный стакан': f'В мерный стакан в форме перевёрнутого конуса налили {v} мл воды, и вода поднялась до {lvl_txt}.'}[vessel]
        liq = {'сосуд': 'жидкости', 'бокал': 'вина', 'воронку с закрытым носиком': 'масла', 'мерный стакан': 'воды'}[vessel]
        acc, nom = {'сосуд': ('сосуд', 'сосуда'), 'бокал': ('бокал', 'бокала'), 'воронку с закрытым носиком': ('воронку', 'воронки'),
                    'мерный стакан': ('стакан', 'стакана')}[vessel]
        if mode == 'add':
            q = f'{head} Сколько миллилитров {liq} нужно долить, чтобы {acc} стал{"а" if acc == "воронку" else ""} полным?'
            q = q.replace('чтобы воронку стала полным', 'чтобы воронка стала полной')
        else:
            q = f'{head} Найдите вместимость {nom}. Ответ дайте в миллилитрах.'
        e = f'Жидкость — подобный конус с коэффициентом {kfr.numerator}/{kfr.denominator}: весь сосуд {tnum(full)} мл' + \
            (f', долить {tnum(full)} − {v} = {tnum(ans)} мл.' if mode == 'add' else '.')
    else:
        Vb = r.randint(1, 30) * cube.denominator
        ans = Vb * cube
        where = {F(1, 2): 'через середину высоты', F(1, 3): 'через точку, делящую высоту в отношении 1 : 2, считая от вершины',
                 F(1, 4): 'через точку, делящую высоту в отношении 1 : 3, считая от вершины',
                 F(2, 3): 'через точку, делящую высоту в отношении 2 : 1, считая от вершины',
                 F(1, 5): 'через точку, делящую высоту в отношении 1 : 4, считая от вершины',
                 F(3, 4): 'через точку, делящую высоту в отношении 3 : 1, считая от вершины'}[kfr]
        q = pick(r, f'Конус объёмом {Vb} пересекли плоскостью, параллельной основанию и проходящей {where}. Найдите объём '
                    f'отсечённого конуса с той же вершиной.',
                 f'Плоскость, параллельная основанию конуса, проходит {where}. Объём конуса равен {Vb}. Найдите объём меньшего конуса, '
                 f'отсечённого этой плоскостью.')
        e = f'Отсечённый конус подобен данному с коэффициентом {kfr.numerator}/{kfr.denominator}: {Vb} · {cube.numerator}/{cube.denominator} = {tnum(ans)}.'
    if not nice(ans, 1):
        return None
    kk = float(kfr)
    if mode == 'cut':
        svg = render(cone_items(1.0, 2.0) + [('E', (0, 2.0 * (1 - kk)), kk, kk * TOP, 'b', 'front'),
                                              ('E', (0, 2.0 * (1 - kk)), kk, kk * TOP, 'bd', 'back')])
    else:
        H = 2.2
        lv = H * kk

        def liquid(sx, sy, k_):
            return (f'M{sx(0):.1f} {sy(0):.1f}L{sx(-kk):.1f} {sy(lv):.1f}A{kk * k_:.1f} {kk * TOP * k_:.1f} 0 0 0 '
                    f'{sx(kk):.1f} {sy(lv):.1f}z')
        svg = render([('W', [(-kk, lv), (kk, lv), (0, 0)], liquid)] + cone_items(1.0, H, apex_up=False) +
                     [('E', (0, lv), kk, kk * TOP, 'b', 'front'), ('E', (0, lv), kk, kk * TOP, 'b', 'back')])

    def chk():
        z, H_, r_ = sp.symbols('z H r', positive=True)
        cone_v = lambda top: sp.integrate(sp.pi * (r_ * z / H_) ** 2, (z, 0, top))   # от вершины до уровня top
        ratio = sp.simplify(cone_v(R(kfr) * H_) / cone_v(H_))
        if mode == 'cut':
            return same(num(ans), R(Vb) * ratio)
        full_ = R(v) / ratio
        return same(num(ans), full_ - v if mode == 'add' else full_)
    return pcard(q, num(ans), e=e, svg=svg), chk


def fig_two_cyl(k, h1, h2):
    """Два цилиндрических сосуда с жидкостью: радиусы 1 и k (для рисунка k ограничен)."""
    kk = max(0.5, min(2.2, k))
    H = 2.2
    l1, l2 = min(H * 0.92, h1), min(H * 0.92, h2)
    x2 = 1 + 0.8 + kk
    items = []
    for x, rr, lv in ((0.0, 1.0, l1), (x2, kk, l2)):
        def liq(sx, sy, k_, x=x, rr=rr, lv=lv):
            return (f'M{sx(x - rr):.1f} {sy(0):.1f}A{rr * k_:.1f} {rr * TOP * k_:.1f} 0 0 0 {sx(x + rr):.1f} {sy(0):.1f}'
                    f'L{sx(x + rr):.1f} {sy(lv):.1f}A{rr * k_:.1f} {rr * TOP * k_:.1f} 0 0 1 {sx(x - rr):.1f} {sy(lv):.1f}z')
        items.append(('W', [(x - rr, 0), (x + rr, lv)], liq))
        items += cyl_items(rr, H, x=x) + [('E', (x, lv), rr, rr * TOP, 'b', 'front'), ('E', (x, lv), rr, rr * TOP, 'b', 'back')]
    return render(items, width=280)


@proto('ep03-cyl-pour', 'ege-prof', 3, 'Переливание жидкости в цилиндрический сосуд другого диаметра',
       invariant='Объём жидкости не меняется, площадь дна пропорциональна квадрату диаметра, поэтому высота уровня '
                 'меняется обратно пропорционально квадрату отношения диаметров.',
       varies='Во сколько раз второй сосуд шире или уже, уровень, единицы (см), сюжет (вода, сок, масло, раствор).',
       answer_rule='h₂ = h₁ / k², если диаметр второго сосуда в k раз больше; h₂ = h₁·k², если в k раз меньше.',
       fipi=r'цилиндрическ\w* сосуд\w*[^.]*уровень жидкости',
       mistakes=['делят на k, а не на k²', 'путают, в какую сторону меняется уровень'],
       svg=True, kim=kim(3, 'Сюжет с цилиндрическими сосудами, «Ответ дайте в сантиметрах.»; ответ — целое число или десятичная дробь.'))
def gen_ep03_cyl_pour(r):
    k = r.choice([2, 2, 3, 4, 5])
    wider = r.random() < 0.7
    liq = r.choice(['воды', 'сока', 'масла', 'раствора', 'молока', 'сиропа'])
    if wider:
        h2 = r.randint(1, 12)
        h1 = h2 * k * k
        if h1 > 60:
            return None
        ans = F(h2)
        rel = f'диаметр которого {raz(k)} больше диаметра первого'
    else:
        h1 = r.randint(1, 8)
        ans = F(h1 * k * k)
        if ans > 60:
            return None
        rel = f'диаметр которого {raz(k)} меньше диаметра первого'
    q = pick(r, f'В цилиндрический сосуд налили {liq} до высоты {h1} см. Всю жидкость перелили во второй цилиндрический сосуд, '
                f'{rel}. На какой высоте окажется уровень жидкости во втором сосуде? Ответ дайте в сантиметрах.',
             f'Уровень {liq} в цилиндрическом сосуде равен {h1} см. Жидкость полностью перелили в другой цилиндрический сосуд, '
             f'{rel}. Найдите высоту уровня жидкости во втором сосуде. Ответ дайте в сантиметрах.')
    e = (f'Площадь дна {"больше" if wider else "меньше"} {raz(k * k)}, уровень {"ниже" if wider else "выше"} {raz(k * k)}: '
         f'{tnum(ans)} см.')
    svg = fig_two_cyl(k if wider else 1 / k, 2.0, 2.0 * (1 / (k * k) if wider else 1))

    def chk():
        hh = sp.Symbol('h', positive=True)
        d1 = 1
        d2 = k if wider else sp.Rational(1, k)
        sol = sp.solve(sp.Eq(sp.pi * (d1 / 2) ** 2 * h1, sp.pi * (d2 / 2) ** 2 * hh), hh)
        return same(num(ans), sol[0])
    return pcard(q, num(ans), e=e, svg=svg), chk


@proto('ep03-cyl-immerse', 'ege-prof', 3, 'Погружение детали в цилиндрический сосуд: объём по подъёму уровня',
       invariant='Объём жидкости в цилиндре пропорционален высоте уровня; объём детали равен объёму «добавленного» слоя.',
       varies='Объём жидкости и её уровень, подъём уровня, сюжет (деталь, камень, шарик, гирька), единицы (см³, мл).',
       answer_rule='V(детали) = V(жидкости) · Δh / h.',
       fipi=r'погрузили деталь|уровень жидкости поднялся',
       mistakes=['берут отношение новой высоты к старой', 'делят объём на подъём уровня'],
       svg=True, kim=kim(3, 'Сюжет «налили … см³ воды, уровень … см; после погружения детали уровень поднялся на … см»; ответ в см³.'))
def gen_ep03_cyl_immerse(r):
    h = r.randint(8, 30)
    dh = r.randint(1, h // 2)
    V = r.randrange(200, 5001, 10)
    ans = F(V * dh, h)
    if ans.denominator != 1 or ans > 5000:
        return None
    thing = r.choice(['деталь', 'металлическую деталь', 'камень', 'стеклянный шарик', 'гирю', 'фарфоровую фигурку'])
    unit = r.choice(['см³', 'мл'])
    ut = 'кубических сантиметрах' if unit == 'см³' else 'миллилитрах'
    q = pick(r, f'В цилиндрический сосуд налили {V} {unit} воды, уровень воды при этом равен {h} см. В воду полностью погрузили '
                f'{thing}, и уровень поднялся на {dh} см. Найдите объём погружённого тела. Ответ дайте в {ut}.',
             f'В цилиндрический сосуд налили {V} {unit} воды. Уровень воды оказался равным {h} см. После того как в воду '
             f'полностью погрузили {thing}, уровень воды поднялся на {dh} см. Чему равен объём погружённого тела? Ответ дайте в {ut}.')
    e = f'Слой высотой 1 см имеет объём {V} : {h}; тело вытеснило {V} · {dh} : {h} = {tnum(ans)} {unit}.'
    svg = fig_two_cyl(1.0, 1.6, 1.6 * (h + dh) / h)

    def chk():
        S = sp.Symbol('S', positive=True)              # площадь дна
        s_ = sp.solve(sp.Eq(S * h, V), S)[0]
        return same(num(ans), s_ * (h + dh) - V)
    return pcard(q, num(ans), e=e, svg=svg), chk


QUADS = [(1, 2, 2, 3), (2, 3, 6, 7), (1, 4, 8, 9), (4, 4, 7, 9), (2, 6, 9, 11), (6, 6, 7, 11), (2, 10, 11, 15),
         (3, 4, 12, 13), (2, 5, 14, 15), (1, 12, 12, 17), (8, 9, 12, 17), (6, 10, 15, 19), (4, 5, 20, 21), (12, 15, 16, 25),
         (2, 4, 4, 6), (4, 8, 8, 12), (3, 6, 6, 9), (4, 6, 12, 14), (6, 9, 18, 21), (2, 3, 6, 7)]


@proto('ep03-box-diag', 'ege-prof', 3, 'Диагональ прямоугольного параллелепипеда и куба',
       invariant='Квадрат диагонали прямоугольного параллелепипеда равен сумме квадратов трёх его измерений; у куба d = a√3.',
       varies='Три ребра, ребро по диагонали и двум другим рёбрам, куб (ребро или объём по диагонали).',
       answer_rule='d² = a² + b² + c²; a = d/√3 для куба.',
       fipi=r'диагональ (прямоугольного параллелепипеда|куба)',
       mistakes=['берут сумму рёбер вместо суммы квадратов', 'путают диагональ грани и диагональ параллелепипеда'],
       svg=True, kim=kim(3, KIM_LEN))
def gen_ep03_box_diag(r):
    mode = r.choice(['diag', 'diag', 'edge', 'cube_edge', 'cube_vol'])
    if mode in ('diag', 'edge'):
        a, b, c, d = r.choice(QUADS)
        k = r.choice([1, 1, 2, 3])
        a, b, c, d = a * k, b * k, c * k, d * k
        ed = [a, b, c]
        r.shuffle(ed)
        if mode == 'diag':
            ans = F(d)
            q = pick(r, f'Три ребра прямоугольного параллелепипеда, выходящие из одной вершины, равны {ed[0]}, {ed[1]} и {ed[2]}. '
                        f'Найдите длину его диагонали.',
                     f'В прямоугольном параллелепипеде {BOXN} известно, что AB = {ed[0]}, AD = {ed[1]}, {sub1("AA1")} = {ed[2]}. '
                     f'Найдите длину диагонали {sub1("AC1")}.')
            e = f'd = √({ed[0]}² + {ed[1]}² + {ed[2]}²) = {d}.'
        else:
            ans = F(ed[2])
            q = pick(r, f'Диагональ прямоугольного параллелепипеда равна {d}, а два его ребра, выходящие из одной вершины, равны '
                        f'{ed[0]} и {ed[1]}. Найдите третье ребро, выходящее из этой вершины.',
                     f'В прямоугольном параллелепипеде {BOXN} диагональ {sub1("BD1")} = {d}, AB = {ed[0]}, AD = {ed[1]}. Найдите длину ребра {sub1("AA1")}.')
            e = f'{sub1("AA1")} = √({d}² − {ed[0]}² − {ed[1]}²) = {ed[2]}.'
        dims = draw_dims(ed[0], ed[1], ed[2])
        dd, known = (a * a + b * b + c * c, ed)
    else:
        k = r.randint(1, 15)
        dtxt = f'{k}√3' if k > 1 else '√3'
        if mode == 'cube_edge':
            ans = F(k)
            q = pick(r, f'Диагональ куба равна {dtxt}. Найдите ребро куба.', f'Найдите длину ребра куба, диагональ которого равна {dtxt}.')
            e = f'd = a√3, a = {k}.'
        else:
            ans = F(k ** 3)
            q = pick(r, f'Диагональ куба равна {dtxt}. Найдите объём куба.', f'Найдите объём куба, диагональ которого равна {dtxt}.')
            e = f'a = {k}, V = {k}³ = {k ** 3}.'
        dims = (2.4, 2.4, 2.4)
        dd, known = 3 * k * k, None
    V = box_V(*dims)
    diag = ('A', 'C1') if mode != 'edge' else ('B', 'D1')
    svg = render(poly_items(V, VIEW_CAB, p_cab, extra=[diag], label=(mode in ('diag', 'edge')), dots=[]))

    def chk():
        if known is None:
            a_ = sp.Symbol('a', positive=True)
            av = sp.solve(sp.Eq(sp.sqrt(3 * a_ ** 2), sp.sqrt(dd)), a_)[0]
            return same(num(ans), av if mode == 'cube_edge' else av ** 3)
        Vx = box_V(known[0], known[1], known[2])
        dvec = _v(Vx['A'], Vx['C1'])
        dl = math.sqrt(_dt(dvec, dvec))
        if mode == 'diag':
            return ok(dl, num(ans))
        return ok(math.sqrt(dl ** 2 - known[0] ** 2 - known[1] ** 2), num(ans))
    return pcard(q, num(ans), e=e, svg=svg), chk


# ================================================================ №4. Простая вероятность

PROB = 'Найдите вероятность того, что'
KIM4 = 'Сюжетная задача в одну-две фразы, инструкция «Найдите вероятность того, что …»; ответ — конечная десятичная дробь.'


def pnice(p, dec=4):
    return nice(p, dec) and 0 < p < 1


SHARE_CTX = [
    # (текст с {n} и {m}, событие «да», событие «нет»)
    ('В базе интеллектуальной викторины {n} {qw}, {m} из них посвящены космосу. Ведущий выбирает вопрос наугад.',
     'выбранный вопрос будет о космосе', 'выбранный вопрос будет не о космосе', ('вопрос', 'вопроса', 'вопросов')),
    ('В плейлисте {n} {qw}, {m} из них исполняются на английском языке. Плеер включает случайную композицию.',
     'зазвучит композиция на английском языке', 'зазвучит композиция не на английском языке', ('композиция', 'композиции', 'композиций')),
    ('Учитель подготовил {n} {qw} для проектов, {m} из них связаны с экологией. Ученик вытягивает тему наугад.',
     'ему достанется тема, связанная с экологией', 'ему достанется тема, не связанная с экологией', ('тему', 'темы', 'тем')),
    ('В коробке {n} одинаковых на вид {qw}, в {m} из них спрятан приз. Покупатель берёт одно яйцо наугад.',
     'в выбранном яйце окажется приз', 'в выбранном яйце приза не окажется', ('шоколадное яйцо', 'шоколадных яйца', 'шоколадных яиц')),
    ('На складе {n} {qw}, у {m} из них повреждена упаковка. Для отправки заказа кладовщик берёт один чайник наугад.',
     'у выбранного чайника повреждена упаковка', 'упаковка выбранного чайника окажется целой', ('электрический чайник', 'электрических чайника', 'электрических чайников')),
    ('По данным магазина, в среднем из каждых {n} {qw} {m} возвращают из-за брака. Покупатель выбирает один фонарик.',
     'выбранный фонарик окажется с браком', 'выбранный фонарик окажется исправным', ('проданного фонарика', 'проданных фонариков', 'проданных фонариков')),
    ('В среднем из каждых {n} {qw} типографии {m} печатаются со смазанной обложкой. Читатель покупает одну книгу этого тиража.',
     'у купленной книги будет смазанная обложка', 'обложка купленной книги окажется без дефекта', ('книги', 'книг', 'книг')),
    ('В электронном сборнике {n} {qw}, {m} из них на построение графиков. Программа выдаёт ученику одно упражнение случайным образом.',
     'выпадет упражнение на построение графика', 'выпадет упражнение не на построение графика', ('упражнение', 'упражнения', 'упражнений')),
]


@proto('ep04-share', 'ege-prof', 4, 'Классическая вероятность: доля объектов с признаком (или без него)',
       invariant='Все исходы равновозможны: вероятность равна отношению числа благоприятных объектов к общему числу; '
                 'для «не …» берём дополнение.',
       varies='Сюжет (викторина, плейлист, темы проектов, склад, брак в среднем), числа, спрашиваем событие или противоположное.',
       answer_rule='P = m/n или P = (n − m)/n.',
       fipi=r'(сборнике билетов|В среднем из|Фабрика выпускает)',
       mistakes=['забывают перейти к противоположному событию', 'делят на число «плохих», а не на общее число'],
       maxdec=4, kim=kim(4, KIM4 + ' Числа масштаба банка (десятки — тысячи объектов).'))
def gen_ep04_share(r):
    i = r.randrange(len(SHARE_CTX))
    ctx, yes, no, forms = SHARE_CTX[i]
    hi = [500, 300, 60, 200, 500, 5000, 5000, 300][i]
    n = r.choice([r.randint(12, 100), r.randint(12, 100), r.choice([120, 150, 200, 250, 400, 500, 1000, 2000, 2500, 3000, 5000])])
    if n > hi:
        return None
    m = r.randint(1, n - 1)
    neg = r.random() < 0.55
    p = F(n - m, n) if neg else F(m, n)
    if not pnice(p, 4) or not nice(p, 3) and n < 1000:
        return None
    if ('в среднем' in ctx.lower() or 'повреждена' in ctx) and m > n // 5:
        return None
    qw = plural(n, *forms) if 'каждых' not in ctx else (forms[0] if n % 10 == 1 and n % 100 != 11 else forms[2])
    q = ctx.format(n=n, m=m, qw=qw) + f' {PROB} {no if neg else yes}.'
    e = f'P = {"(" + str(n) + " − " + str(m) + ")" if neg else m} / {n} = {tnum(p)}.'

    def chk():
        outs = [1] * m + [0] * (n - m)           # 1 — объект с признаком
        fav = sum(1 for o in outs if (o == 0 if neg else o == 1))
        return same(num(p), sp.Rational(fav, len(outs)))
    return pcard(q, num(p), e=e), chk


@proto('ep04-ratio-sum', 'ege-prof', 4, '«На каждые a исправных приходится b неисправных»',
       invariant='Общее число объектов в группе равно a + b; вероятность — отношение нужных к a + b (а не к a).',
       varies='Сюжет, числа a и b (a + b подобрано так, что ответ — конечная десятичная дробь), спрашиваем исправный '
              'или неисправный.',
       answer_rule='P(исправный) = a/(a + b); P(неисправный) = b/(a + b).',
       fipi=r'на каждые \d+[^.]*приходится',
       mistakes=['делят на a вместо a + b', 'находят вероятность не того события (исправный/неисправный)'],
       maxdec=3, kim=kim(4, KIM4 + ' Ответ — точная конечная десятичная дробь без округления: в КИМ 2027 ответ — целое '
                                  'число или конечная десятичная дробь, в действующем банке №4 инструкции «округлите» нет.'))
def gen_ep04_ratio_sum(r):
    items = [(('качественный рюкзак', 'качественных рюкзака', 'качественных рюкзаков'),
              ('рюкзак со скрытым дефектом', 'рюкзака со скрытым дефектом', 'рюкзаков со скрытым дефектом'),
              'купленный рюкзак окажется качественным', 'купленный рюкзак окажется с дефектом'),
             (('исправный пульт', 'исправных пульта', 'исправных пультов'), ('неисправный', 'неисправных', 'неисправных'),
              'случайно выбранный пульт окажется исправным', 'случайно выбранный пульт окажется неисправным'),
             (('годную деталь', 'годные детали', 'годных деталей'), ('бракованная', 'бракованные', 'бракованных'),
              'взятая наугад деталь окажется годной', 'взятая наугад деталь окажется бракованной'),
             (('целый ёлочный шар', 'целых ёлочных шара', 'целых ёлочных шаров'), ('треснувший', 'треснувших', 'треснувших'),
              'вынутый наугад шар окажется целым', 'вынутый наугад шар окажется треснувшим'),
             (('банку без вмятин', 'банки без вмятин', 'банок без вмятин'), ('банка с вмятиной', 'банки с вмятинами', 'банок с вмятинами'),
              'выбранная наугад банка окажется без вмятин', 'выбранная наугад банка окажется с вмятиной')]
    gf, bf, e_good, e_bad = r.choice(items)
    tot = r.choice([20, 25, 40, 50, 50, 80, 100, 100, 100, 125, 200, 200, 250, 400, 500, 1000])
    b = r.randint(1, max(1, tot // 10))
    a = tot - b
    if a % 10 == 1 and a % 100 != 11:              # «на каждые 91 исправный пульт» — неудачное согласование
        return None
    good, bad = plural(a, *gf), plural(b, *bf)
    ask_good = r.random() < 0.6
    ans = F(a if ask_good else b, a + b)
    if not nice(ans, 3):
        return None
    who = r.choice(['На фабрике', 'В среднем на производстве', 'По статистике магазина'])
    q = f'{who} на каждые {a} {good} приходится {b} {bad}. {PROB} {e_good if ask_good else e_bad}.'
    e = f'P = {a if ask_good else b} / ({a} + {b}) = {a if ask_good else b}/{a + b} = {tnum(ans)}.'

    def chk():
        exact = sp.Rational(a if ask_good else b, a + b)
        return same(num(ans), exact)
    return pcard(q, num(ans), e=e), chk


ORDER_CTX = [
    ('На фестивале выступают {N} хоров: {groups}. Порядок выступлений определяется жребием.', 'хор', 'хора', 'хоров',
     'из', 'город', ['Самары', 'Казани', 'Перми', 'Уфы', 'Твери', 'Омска']),
    ('В конкурсе юных пианистов участвуют {N} музыкантов: {groups}. Порядок выступлений определяется жеребьёвкой.', 'музыкант', 'музыканта',
     'музыкантов', 'из', 'школа', ['школы № 1', 'школы № 3', 'школы № 5', 'школы № 8', 'гимназии', 'лицея']),
    ('На соревнованиях по фигурному катанию выступают {N} спортсменок: {groups}. Порядок выступлений определяется жребием.', 'спортсменка',
     'спортсменки', 'спортсменок', 'из', 'клуб', ['«Звезды»', '«Олимпа»', '«Вьюги»', '«Грации»', '«Метели»']),
    ('На школьной научной конференции {N} докладов: {groups}. Порядок докладов определяется жеребьёвкой.', 'доклад', 'доклада', 'докладов',
     'от', 'класс', ['9 «А»', '10 «Б»', '11 «А»', '10 «В»', '8 «Г»']),
    ('На защиту проектов записались {N} команд: {groups}. Очерёдность выступлений определяется жребием.', 'команда', 'команды', 'команд',
     'из', 'город', ['Тулы', 'Рязани', 'Калуги', 'Орла', 'Брянска']),
]

ORD = {1: 'первым', 2: 'вторым', 3: 'третьим', 4: 'четвёртым', 5: 'пятым', 6: 'шестым', 7: 'седьмым', 8: 'восьмым',
       9: 'девятым', 10: 'десятым', 11: 'одиннадцатым', 12: 'двенадцатым', 13: 'тринадцатым', 15: 'пятнадцатым', 20: 'двадцатым'}
ORD_F = {k: v[:-2] + 'ой' if v.endswith('ым') else v for k, v in ORD.items()}
ORD_F[3] = 'третьей'


@proto('ep04-order', 'ege-prof', 4, 'Порядок выступлений по жребию: k-й участник из данной группы',
       invariant='При случайном порядке на любом месте с равной вероятностью может оказаться любой участник, '
                 'поэтому номер места не важен: P = (число участников группы) / (общее число).',
       varies='Сюжет (фестиваль, конкурс, соревнования, конференция), число групп, номер места, группа '
              '(иногда её численность нужно найти как «остальные»).',
       answer_rule='P = n_X / N (n_X = N − сумма остальных, если группа названа «остальные»).',
       fipi=r'^(?!.*Конкурс исполнителей).*Порядок\s*(выступлений|докладов|,\s*в котором)[^.]*(жреби|жеребьёвк)',
       mistakes=['думают, что номер места влияет на вероятность', 'забывают найти численность группы «остальные»'],
       maxdec=4, kim=kim(4, KIM4 + ' Как в КИМ: «Порядок выступлений определяется жребием. Найдите вероятность того, что …-м …»'))
def gen_ep04_order(r):
    ctx, one, few, many, prep, _, names = r.choice(ORDER_CTX)
    g = r.randint(2, 4)
    nm = r.sample(names, g)
    cnt = [r.randint(2, 20) for _ in range(g)]
    N = sum(cnt)
    if plural(N, 'a', 'b', 'c') != 'c':          # «выступают 22 хоров» — только числа с формой «многих»
        return None
    idx = r.randrange(g)
    p = F(cnt[idx], N)
    if not nice(p, 3):
        return None
    rest = g >= 3 and r.random() < 0.4
    parts = []
    for i in range(g):
        if rest and i == g - 1:
            parts.append(f'остальные — {prep} {nm[i]}')
        else:
            parts.append(f'{cnt[i]} {prep} {nm[i]}')
    groups = ', '.join(parts)
    pos = r.choice([1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 20])
    if pos > N:
        return None
    fem = one in ('спортсменка', 'команда')
    ordw = (ORD_F if fem else ORD)[pos]
    who = f'{one} {prep} {nm[idx]}'
    head = ctx.format(N=N, groups=groups)
    verb = 'прозвучит' if one == 'доклад' else 'выступит'
    q = head + f' {PROB} {ordw} по счёту {verb} {who}.'
    e = (f'Из «остальных»: {N} − {N - cnt[-1]} = {cnt[-1]}. ' if rest else '') + f'P = {cnt[idx]} / {N} = {tnum(p)}.'

    def chk():
        # перебор: доля перестановок, где на месте pos стоит участник группы idx, = доля участников группы
        people = [i for i in range(g) for _ in range(cnt[i])]
        fav = sum(1 for x in people if x == idx)        # кто может стоять на месте pos
        return same(num(p), sp.Rational(fav, len(people))) and pos <= len(people)
    return pcard(q, num(p), e=e), chk


@proto('ep04-groups', 'ege-prof', 4, 'Распределение по дням (аудиториям): вероятность попасть в данную группу',
       invariant='Сначала находим, сколько мест в нужной группе (день, аудитория), затем делим на общее число участников.',
       varies='Сюжет (конкурс по дням, экзамен по дням, запасная аудитория, запасной корпус), числа, номер дня.',
       answer_rule='P = (размер нужной группы) / N; размер = (N − первые группы) / (число оставшихся групп).',
       fipi=r'(запасную аудиторию|Конкурс исполнителей проводится)',
       mistakes=['делят на число дней, а не на число выступлений', 'не вычитают первый день'],
       maxdec=4, kim=kim(4, KIM4 + ' Как в КИМ: «В первый день запланировано …, остальные распределены поровну…».'))
def gen_ep04_groups(r):
    mode = r.choice(['days', 'days', 'reserve'])
    if mode == 'days':
        d = r.randint(3, 5)
        first = r.randrange(4, 40, 2)
        each = r.randint(3, 20)
        N = first + each * (d - 1)
        day = r.randint(2, d)
        p = F(each, N)
        if not nice(p, 3):
            return None
        dn = {2: 'второй', 3: 'третий', 4: 'четвёртый', 5: 'пятый'}[day] if day < d or r.random() < 0.5 else 'последний'
        dn = ('во ' if dn == 'второй' else 'в ') + dn
        ctx = r.choice([
            (f'Конкурс чтецов проходит {d} {plural(d, "день", "дня", "дней")}. В программе {N} выступлений: {first} — в первый день, '
             f'остальные поровну делятся между другими днями. Очерёдность решает жребий. '
             f'{PROB} ученица Н. выступит {dn} день конкурса.'),
            (f'Экзамен по вождению принимают {d} {plural(d, "день", "дня", "дней")}. На него записались {N} человек: {first} из них '
             f'сдают в первый день, остальные распределены поровну по оставшимся дням. Очерёдность определяется жребием. '
             f'{PROB} курсант С. будет сдавать экзамен {dn} день.'),
            (f'Фестиваль уличных театров длится {d} {plural(d, "день", "дня", "дней")}. Запланировано {N} спектаклей: {first} — в первый '
             f'день, остальные поровну в остальные дни. Порядок показа определяется жребием. {PROB} спектакль театра «Балаган» '
             f'покажут {dn} день.'),
            (f'Турнир по шахматам среди школ проходит {d} {plural(d, "день", "дня", "дней")}. Всего {N} {plural(N, "партия", "партии", "партий")}, в первый день {"играют" if first % 10 != 1 or first % 100 == 11 else "играется"} {first}, '
             f'остальные партии поровну распределены по другим дням. Расписание составляется жребием. {PROB} партия команды школы № 7 '
             f'будет сыграна {dn} день.')])
        q = ctx
        e = f'В каждый из остальных дней ({N} − {first}) : {d - 1} = {each}; P = {each} / {N} = {tnum(p)}.'
        sizes = [first] + [each] * (d - 1)
        target = day - 1 if dn != 'последний' else d - 1
    else:
        k = r.randint(2, 4)
        m = r.randint(10, 120)
        extra = r.randint(3, m - 1)
        N = k * m + extra
        p = F(extra, N)
        if not nice(p, 3):
            return None
        q = r.choice([
            (f'На олимпиаде по физике {N} участников разместили в {k + 1} аудиториях. В каждую из первых {k} посадили по {m} человек, '
             f'остальных — в резервную аудиторию на другом этаже. {PROB} случайно выбранный участник писал олимпиаду в резервной аудитории.'),
            (f'На сборы приехали {N} спортсменов. В {k} корпусах поселили по {m} человек, остальных — в запасном корпусе. '
             f'{PROB} случайно выбранный спортсмен живёт в запасном корпусе.'),
            (f'На экскурсию едут {N} школьников. В {k} больших автобуса сели по {m} человек, остальные поехали в микроавтобусе. '
             f'{PROB} случайно выбранный школьник едет в микроавтобусе.' if 2 <= k <= 4 else ''),
            (f'Для конференции подготовили {k + 1} зала. В {k} {plural(k, "зал", "зала", "залов")} поместилось по {m} слушателей, '
             f'остальных направили в дополнительный зал с трансляцией. {PROB} случайно выбранный слушатель окажется в дополнительном зале.')])
        if not q:
            return None
        e = f'В резерве {N} − {k} · {m} = {extra}; P = {extra} / {N} = {tnum(p)}.'
        sizes = [m] * k + [extra]
        target = k

    def chk():
        slots = [i for i, s_ in enumerate(sizes) for _ in range(s_)]
        return len(slots) == N and same(num(p), sp.Rational(slots.count(target), len(slots)))
    return pcard(q, num(p), e=e), chk


@proto('ep04-select-k', 'ege-prof', 4, 'Выбор k человек из n: вероятность, что данный человек попадёт в число выбранных',
       invariant='Каждый из n человек равновозможно попадает в выбранную группу из k; P = k/n.',
       varies='Сюжет (дежурные, первый рейс, победители розыгрыша, кабина канатной дороги), числа n и k.',
       answer_rule='P = k / n.',
       fipi=r'(Их вертолётом доставляют|С помощью жребия они выбирают)',
       mistakes=['считают вероятность равной 1/n', 'делят n на k'],
       maxdec=4, kim=kim(4, KIM4 + ' Как в КИМ: «Порядок, в котором …, случаен. Найдите вероятность того, что … полетит первым рейсом».'))
def gen_ep04_select_k(r):
    k = r.randint(2, 15)
    n = k * r.randint(2, 20)
    if r.random() < 0.4:
        n = r.randint(k + 2, 80)
    p = F(k, n)
    if not nice(p, 3) or n > 300:
        return None
    q = r.choice([
        f'В классе {n} учеников. С помощью жребия выбирают {k} дежурных на школьный вечер. {PROB} ученица Ольга окажется среди дежурных.',
        f'Группу из {n} туристов переправляют на остров на лодке, которая берёт по {k} {plural(k, "человеку", "человека", "человек")} '
        f'за рейс. Туристы садятся в лодку в случайном порядке. {PROB} турист Р. окажется в лодке первого рейса.',
        f'В розыгрыше участвуют {n} покупателей, призы получат {k} из них, выбранные случайно. {PROB} покупатель Д. получит приз.',
        f'Кабина канатной дороги вмещает {k} человек. Группа из {n} лыжников поднимается в гору, порядок посадки случаен. '
        f'{PROB} лыжница М. поедет в первой кабине.',
        f'На районную олимпиаду школа отправляет {k} из {n} желающих, выбранных жребием. {PROB} Антон, который тоже хочет поехать, '
        f'попадёт в число участников.'])
    e = f'P = {k} / {n} = {tnum(p)}.'

    def chk():
        # доля k-элементных подмножеств, содержащих данного человека: C(n−1, k−1)/C(n, k)
        return same(num(p), sp.binomial(n - 1, k - 1) / sp.binomial(n, k))
    return pcard(q, num(p), e=e), chk


def coin_event(r, n):
    """Случайное событие для n бросков: (текст, предикат по кортежу 0/1, где 1 — «успех»)."""
    kinds = [('ровно один раз', lambda s: sum(s) == 1), ('ни разу', lambda s: sum(s) == 0), ('все {n} раза', lambda s: sum(s) == n),
             ('хотя бы один раз', lambda s: sum(s) >= 1), ('не более одного раза', lambda s: sum(s) <= 1),
             ('ровно два раза', lambda s: sum(s) == 2), ('не менее двух раз', lambda s: sum(s) >= 2)]
    if n == 2:
        kinds = [k_ for k_ in kinds if k_[0] not in ('ровно два раза', 'не менее двух раз')] + [('оба раза', lambda s: sum(s) == 2)]
        kinds = [k_ for k_ in kinds if not k_[0].startswith('все')]
    t, f_ = r.choice(kinds)
    return t.format(n=n), f_


@proto('ep04-coin', 'ege-prof', 4, 'Монета (жребий «орёл/решка») при нескольких бросках',
       invariant='Все 2ⁿ последовательностей исходов равновозможны; считаем подходящие последовательности перебором.',
       varies='Число бросков (2–4), событие (ровно k раз, ни разу, хотя бы раз, не более одного, конкретная очерёдность), '
              'сюжет (монета, жребий перед партией или матчем).',
       answer_rule='P = (число подходящих последовательностей) / 2ⁿ.',
       fipi=r'(симметричную монету бросают|бросает монетку|тянут жребий)',
       mistakes=['считают исходы «0, 1, 2 орла» равновозможными', 'для «хотя бы раз» забывают про дополнение'],
       maxdec=4, kim=kim(4, KIM4))
def gen_ep04_coin(r):
    n = r.choice([2, 3, 3, 4])
    mode = r.choice(['count', 'count', 'seq'])
    if mode == 'count':
        ev, pred = coin_event(r, n)
        side = r.choice(['орёл', 'решка'])
        neg = ev == 'ни разу'
        ctxs = [f'Правильную монету подбрасывают {n} {plural(n, "раз", "раза", "раз")} подряд. {PROB} {side} {"ни разу не окажется сверху" if neg else "окажется сверху " + ev}.',
                f'Перед каждой партией в шахматы судья бросает монету, чтобы определить, кто из соперников будет играть белыми. '
                f'Андрей играет {n} {plural(n, "партию", "партии", "партий")} с разными соперниками. {PROB} Андрей {"не " if neg else ""}будет играть белыми {ev}.',
                f'Перед началом волейбольного матча капитаны бросают монету, чтобы выбрать, кто подаёт первым. Команда «Прибой» '
                f'проводит {n} {plural(n, "матч", "матча", "матчей")}. {PROB} «Прибой» {"не " if neg else ""}будет подавать первым {ev}.']
        q = r.choice(ctxs)
        if not q:
            return None
    else:
        pos = r.randint(1, n)
        ordw = {1: 'первую', 2: 'вторую', 3: 'третью', 4: 'четвёртую'}[pos]
        names = r.sample(['«Ладья»', '«Пешка»', '«Гамбит»', '«Эндшпиль»', '«Цейтнот»', '«Дебют»'], n + 1)
        q = (f'Шахматная команда {names[0]} по очереди встречается с командами {", ".join(names[1:-1])} и {names[-1]}. Перед каждой '
             f'встречей жребием определяют, кто играет белыми на первой доске. {PROB} {names[0]} будет играть белыми только '
             f'{ordw} встречу.')
        pred = lambda s, pos=pos: s[pos - 1] == 1 and sum(s) == 1
    fav = [s for s in product((0, 1), repeat=n) if pred(s)]
    p = F(len(fav), 2 ** n)
    if p in (0, 1):
        return None
    e = f'Всего {2 ** n} равновозможных {plural(2 ** n, "исход", "исхода", "исходов")}, подходящих {len(fav)}: P = {tnum(p)}.'

    def chk():
        # моделируем бросками: 1 — нужная сторона; вероятность каждого исхода (1/2)^n
        tot = sum(sp.Rational(1, 2) ** n for s in product((0, 1), repeat=n) if pred(s))
        return same(num(p), tot)
    return pcard(q, num(p), e=e), chk


DICE_ONE = [('выпадет чётное число очков', lambda a: a % 2 == 0), ('выпадет нечётное число очков', lambda a: a % 2 == 1),
            ('выпадет больше 3 очков', lambda a: a > 3), ('выпадет меньше 4 очков', lambda a: a < 4),
            ('выпадет не больше 3 очков', lambda a: a <= 3), ('выпадет не меньше 4 очков', lambda a: a >= 4)]
DICE_TWO = [('сумма очков окажется чётной', lambda a, b: (a + b) % 2 == 0),
            ('сумма очков окажется нечётной', lambda a, b: (a + b) % 2 == 1),
            ('произведение выпавших очков окажется чётным', lambda a, b: a * b % 2 == 0),
            ('произведение выпавших очков окажется нечётным', lambda a, b: a * b % 2 == 1),
            ('оба раза выпадет чётное число очков', lambda a, b: a % 2 == 0 and b % 2 == 0),
            ('оба раза выпадет нечётное число очков', lambda a, b: a % 2 == 1 and b % 2 == 1),
            ('чётное число очков выпадет хотя бы при одном броске', lambda a, b: a % 2 == 0 or b % 2 == 0),
            ('оба раза выпадет больше 3 очков', lambda a, b: a > 3 and b > 3),
            ('оба раза выпадет меньше 4 очков', lambda a, b: a < 4 and b < 4),
            ('больше 3 очков выпадет хотя бы при одном броске', lambda a, b: a > 3 or b > 3),
            ('сумма выпавших очков будет делиться на 4', lambda a, b: (a + b) % 4 == 0),
            ('сумма выпавших очков не будет делиться на 4', lambda a, b: (a + b) % 4 != 0),
            ('в первый раз выпадет чётное число очков, а во второй — нечётное', lambda a, b: a % 2 == 0 and b % 2 == 1),
            ('в первый раз выпадет больше 3 очков, а во второй — меньше 4', lambda a, b: a > 3 and b < 4)]
DICE_HEAD = ['Игральную кость бросают дважды.', 'В случайном эксперименте игральную кость бросают два раза.',
             'Игральный кубик бросают два раза подряд.', 'Симметричную игральную кость бросили дважды.']


@proto('ep04-dice', 'ege-prof', 4, 'Игральная кость: вероятность события при одном или двух бросках',
       invariant='Выписываем все равновозможные исходы (6 или 36 упорядоченных пар) и считаем подходящие.',
       varies='Один или два броска, событие (чётность суммы или произведения, больше/меньше, делимость суммы, '
              'условие на каждый бросок), формулировка броска.',
       answer_rule='P = (число подходящих исходов) / 36 (или / 6); ответ — конечная десятичная дробь.',
       fipi=r'игральн\w* кост\w*[^.]*(бросают|бросили)[^.]*\. Найдите вероятность того',
       mistakes=['считают исходы (2; 5) и (5; 2) одним', 'считают исходы «сумма чётная/нечётная» по суммам 2…12, а не по парам'],
       maxdec=2, kim=kim(4, KIM4 + ' Ответ — точная конечная десятичная дробь без округления (КИМ 2027: ответ — целое число '
                                  'или конечная десятичная дробь; в действующем банке №4 инструкции «округлите» нет).'))
def gen_ep04_dice(r):
    if r.random() < 0.15:
        ev, cond = r.choice(DICE_ONE)
        fav = [a for a in range(1, 7) if cond(a)]
        tot = 6
        text = r.choice(['Игральную кость бросают один раз.', 'Симметричную игральную кость бросают один раз.'])
        pred2 = None
    else:
        ev, pred2 = r.choice(DICE_TWO)
        fav = [(a, b) for a in range(1, 7) for b in range(1, 7) if pred2(a, b)]
        tot = 36
        text = r.choice(DICE_HEAD)
    p = F(len(fav), tot)
    if p in (0, 1) or not nice(p, 2):
        return None
    q = f'{text} {PROB} {ev}.'
    e = f'Равновозможных исходов {tot}, подходящих {len(fav)}: P = {len(fav)}/{tot} = {tnum(p)}.'

    def chk():
        if pred2 is None:
            exact = sp.Rational(sum(1 for a in range(1, 7) if cond(a)), 6)
        else:
            exact = sum(sp.Rational(1, 36) for a in range(1, 7) for b in range(1, 7) if pred2(a, b))
        return same(num(p), exact)
    return pcard(q, num(p), e=e), chk


COMP_CTX = [
    ('Вероятность того, что новый электрический чайник прослужит больше двух лет, равна {p}.', 'он прослужит не больше двух лет'),
    ('Вероятность того, что пассажир электрички опоздает к её отправлению, равна {p}.', 'пассажир успеет к отправлению'),
    ('Вероятность того, что в случайно выбранный день в городе пойдёт снег, равна {p}.', 'в этот день снега не будет'),
    ('Вероятность того, что случайно выбранная батарейка разрядится раньше гарантийного срока, равна {p}.', 'батарейка проработает весь гарантийный срок'),
    ('Вероятность того, что при наборе текста секретарь допустит хотя бы одну опечатку на странице, равна {p}.', 'на странице не будет ни одной опечатки'),
    ('Вероятность того, что утренний автобус придёт на остановку по расписанию, равна {p}.', 'автобус не придёт по расписанию'),
]


@proto('ep04-complement', 'ege-prof', 4, 'Противоположное событие',
       invariant='Вероятности события и противоположного ему события в сумме равны 1.',
       varies='Сюжет, данная вероятность, формулировка противоположного события.',
       answer_rule='P(не A) = 1 − P(A).',
       fipi=r'температура тела здорового человека окажется ниже',
       mistakes=['не распознают противоположное событие', 'вычитают из 100 вместо 1'],
       maxdec=4, kim=kim(4, KIM4))
def gen_ep04_complement(r):
    i = r.randrange(len(COMP_CTX))
    ctx, ev = COMP_CTX[i]
    lo, hi = [(80, 97), (2, 20), (10, 60), (1, 10), (5, 40), (70, 98)][i]
    p = F(r.randint(lo, hi), 100) if r.random() < 0.8 else F(r.randint(lo * 10, hi * 10), 1000)
    if p in (F(1, 2),):
        return None
    ans = 1 - p
    q = ctx.format(p=tnum(p)) + f' {PROB} {ev}.'
    e = f'P = 1 − {tnum(p)} = {tnum(ans)}.'
    return pcard(q, num(ans), e=e), (lambda: same(num(ans), sp.Integer(1) - R(p)))


RANGE_CTX = [
    ('В кафе ведут учёт посетителей. Вероятность того, что за обеденный час придёт меньше {a} посетителей, равна {pa}. '
     'Вероятность того, что придёт меньше {b} посетителей, равна {pb}.', 'число посетителей за обеденный час будет от {b} до {a1} включительно'),
    ('Вероятность того, что в течение смены в диспетчерскую поступит меньше {a} вызовов, равна {pa}. Вероятность того, что вызовов '
     'будет меньше {b}, равна {pb}.', 'за смену поступит от {b} до {a1} вызовов включительно'),
    ('Вероятность того, что на контрольной ученик К. верно решит больше {b1} заданий, равна {pb_}. Вероятность того, что он верно '
     'решит больше {a1} заданий, равна {pa_}.', 'К. верно решит от {b} до {a1} заданий включительно'),
    ('Вероятность того, что в случайно выбранный день в интернет-магазине оформят меньше {a} заказов, равна {pa}. Вероятность '
     'того, что заказов будет меньше {b}, равна {pb}.', 'в этот день оформят от {b} до {a1} заказов включительно'),
    ('Вероятность того, что за игру хоккейная команда забьёт больше {b1} шайб, равна {pb_}. Вероятность того, что она забьёт больше '
     '{a1} шайб, равна {pa_}.', 'команда забьёт от {b} до {a1} шайб включительно'),
]


@proto('ep04-range', 'ege-prof', 4, 'Вероятность попадания в промежуток как разность вероятностей',
       invariant='Событие «меньше a» — объединение несовместных событий «меньше b» и «от b до a − 1»; искомая '
                 'вероятность — разность данных.',
       varies='Сюжет (посетители, вызовы, решённые задачи, заказы, голы), границы, формулировки «меньше» или «больше».',
       answer_rule='P(b ≤ X ≤ a − 1) = P(X < a) − P(X < b) = P(X > b − 1) − P(X > a − 1).',
       fipi=r'(окажется меньше \d+ пассажиров|верно решит больше)',
       mistakes=['складывают вероятности', 'путают, какие границы включены'],
       maxdec=4, kim=kim(4, KIM4 + ' Как в КИМ: «… меньше 20 …, равна 0,94 … меньше 15 … Найдите вероятность того, что … от 15 до 19 включительно».'))
def gen_ep04_range(r):
    i = r.randrange(len(RANGE_CTX))
    ctx, ev = RANGE_CTX[i]
    (b0, b1), (g0, g1) = [((5, 25), (3, 12)), ((5, 30), (3, 12)), ((2, 8), (2, 4)), ((10, 60), (5, 20)), ((2, 4), (2, 3))][i]
    b = r.randint(b0, b1)
    a = b + r.randint(g0, g1)
    pa = F(r.randint(50, 99), 100)
    pb = F(r.randint(5, 95), 100)
    if pb >= pa:
        return None
    ans = pa - pb
    if 'больше' in ctx:
        # P(X > b − 1) = 1 − P(X < b) = 1 − pb; P(X > a − 1) = 1 − pa
        q = ctx.format(b1=b - 1, a1=a - 1, pb_=tnum(1 - pb), pa_=tnum(1 - pa)) + f' {PROB} {ev.format(b=b, a1=a - 1)}.'
        e = f'P = P(X > {b - 1}) − P(X > {a - 1}) = {tnum(1 - pb)} − {tnum(1 - pa)} = {tnum(ans)}.'
    else:
        q = ctx.format(a=a, b=b, pa=tnum(pa), pb=tnum(pb)) + f' {PROB} {ev.format(b=b, a1=a - 1)}.'
        e = f'P = {tnum(pa)} − {tnum(pb)} = {tnum(ans)}.'

    def chk():
        # строим распределение: масса pb до b, масса pa − pb на [b, a−1], остаток — от a и выше
        dist_ = {b - 1: R(pb), b: R(pa - pb), a: 1 - R(pa)}
        P_between = sum(v for x, v in dist_.items() if b <= x <= a - 1)
        return same(num(ans), P_between)
    return pcard(q, num(ans), e=e), chk


DISJ_CTX = [
    ('На викторине участнику достаётся один случайный вопрос. Вероятность того, что это вопрос о животных, равна {p1}, а о растениях — {p2}. '
     'Вопросов сразу о животных и о растениях нет.', 'вопрос будет о животных или о растениях'),
    ('На остановке останавливаются автобусы нескольких маршрутов. Вероятность того, что первым подойдёт автобус 12-го маршрута, равна {p1}, '
     '27-го маршрута — {p2}.', 'первым подойдёт автобус одного из этих двух маршрутов'),
    ('В лотерее вероятность выиграть кружку равна {p1}, а вероятность выиграть футболку — {p2}. На один билет можно выиграть не больше '
     'одного приза.', 'на купленный билет выпадет кружка или футболка'),
    ('Школьник вытягивает на зачёте один билет. Вероятность того, что в нём окажется задача на проценты, равна {p1}, на движение — {p2}. '
     'Билетов, где есть задачи обоих типов, нет.', 'в билете окажется задача на проценты или на движение'),
    ('В магазине случайному покупателю достаётся одна скидочная карта. Вероятность получить серебряную карту равна {p1}, золотую — {p2}.',
     'покупатель получит серебряную или золотую карту'),
]


@proto('ep04-disjoint', 'ege-prof', 4, 'Сумма вероятностей несовместных событий',
       invariant='Для несовместных событий вероятность «или A, или B» равна сумме вероятностей.',
       varies='Сюжет, вероятности (десятичные), формулировка несовместности.',
       answer_rule='P(A или B) = P(A) + P(B).',
       fipi=r'Вопросов, которые одновременно относятся к этим двум темам, нет',
       mistakes=['перемножают вероятности', 'вычитают произведение, как для совместных событий'],
       maxdec=4, kim=kim(4, KIM4 + ' Как в открытом варианте: две темы вопросов, «одновременно … нет».'))
def gen_ep04_disjoint(r):
    ctx, ev = r.choice(DISJ_CTX)
    p1 = F(r.randint(2, 60), 100)
    p2 = F(r.randint(2, 40), 100)
    ans = p1 + p2
    if ans >= 1:
        return None
    q = ctx.format(p1=tnum(p1), p2=tnum(p2)) + f' {PROB} {ev}.'
    e = f'События несовместны: {tnum(p1)} + {tnum(p2)} = {tnum(ans)}.'

    def chk():
        # модель: 100 равновозможных исходов, первые — событие A, следующие — B
        omega = ['A'] * int(p1 * 100) + ['B'] * int(p2 * 100)
        omega += ['-'] * (100 - len(omega))
        return same(num(ans), sp.Rational(sum(1 for w in omega if w in 'AB'), 100))
    return pcard(q, num(ans), e=e), chk


BOYS = ['Артём', 'Никита', 'Илья', 'Егор', 'Максим', 'Кирилл', 'Тимур', 'Роман', 'Глеб', 'Лев', 'Марк', 'Фёдор']
GIRLS = ['Алина', 'Вера', 'Дарья', 'Ева', 'Зоя', 'Катя', 'Лиза', 'Мила', 'Полина', 'Соня', 'Ульяна', 'Яна']


@proto('ep04-names', 'ege-prof', 4, 'Жребий среди перечисленных людей: вероятность выбора мальчика (девочки)',
       invariant='Каждый из перечисленных выбирается с равной вероятностью; считаем нужных по списку.',
       varies='Список имён (4–8 человек), что определяется жребием, спрашиваем мальчика или девочку.',
       answer_rule='P = (число мальчиков или девочек в списке) / (число человек).',
       fipi=r'бросили жребий',
       mistakes=['ошибаются при подсчёте по списку', 'делят на число мальчиков вместо общего числа'],
       maxdec=4, kim=kim(4, KIM4))
def gen_ep04_names(r):
    nb, ng = r.randint(1, 5), r.randint(1, 5)
    names = r.sample(BOYS, nb) + r.sample(GIRLS, ng)
    r.shuffle(names)
    boy = r.random() < 0.5
    p = F(nb if boy else ng, nb + ng)
    if not nice(p, 3):
        return None
    lst = ', '.join(names[:-1]) + ' и ' + names[-1]
    what = r.choice(['кто первым будет отвечать у доски', 'кому идти за мячом', 'кто будет капитаном команды',
                     'кто начнёт игру', 'кто поливает цветы в классе на этой неделе'])
    q = f'{lst} бросили жребий — {what}. {PROB} это будет {"мальчик" if boy else "девочка"}.'
    e = f'{"Мальчиков" if boy else "Девочек"} {nb if boy else ng} из {nb + ng}: P = {tnum(p)}.'

    def chk():
        cnt = sum(1 for x in names if (x in BOYS) == boy)
        return same(num(p), sp.Rational(cnt, len(names)))
    return pcard(q, num(p), e=e), chk


# ================================================================ №5. Вероятности сложных событий

KIM5 = ('Сюжетная задача повышенного уровня, «Найдите вероятность того, что …»; ответ — точная конечная десятичная дробь '
        '(до 4 знаков), без округления, как в КИМ.')


def prob_all(p_list):
    """Перебор исходов серии независимых испытаний: {кортеж 0/1: вероятность} (Fraction)."""
    out = {}
    for s_ in product((0, 1), repeat=len(p_list)):
        v = F(1)
        for x, p in zip(s_, p_list):
            v *= p if x else 1 - p
        out[s_] = v
    return out


SEQ_CTX = [
    ('Биатлонист на огневом рубеже стреляет по {n} мишеням, по одному разу в каждую. Вероятность поразить мишень при одном выстреле '
     'равна {p}.', 'биатлонист поразит {first} и промахнётся по {last}', 'мишень', 'мишени', 'мишеням'),
    ('Баскетболист выполняет {n} штрафных броска. Вероятность попадания при каждом броске равна {p}.',
     'баскетболист попадёт {first} и промахнётся {last}', 'бросок', 'броска', 'броски'),
    ('Лучник делает {n} выстрела по мишени. Вероятность попадания в «десятку» при каждом выстреле равна {p}.',
     'лучник попадёт в «десятку» {first} и не попадёт {last}', 'выстрел', 'выстрела', 'выстрелы'),
    ('Теннисист выполняет {n} первые подачи. Вероятность того, что подача окажется удачной, равна {p} для каждой подачи.',
     'удачными окажутся {first}, а {last} — неудачными', 'подача', 'подачи', 'подачи'),
    ('Вратарь отражает серию из {n} пенальти. Вероятность отбить каждый удар равна {p}.',
     'вратарь отобьёт {first} и пропустит {last}', 'удар', 'удара', 'удары'),
]


@proto('ep05-seq', 'ege-prof', 5, 'Серия независимых испытаний: заданная последовательность успехов и неудач',
       invariant='Исходы испытаний независимы, поэтому вероятность конкретной последовательности равна произведению '
                 'вероятностей: p для каждого успеха и 1 − p для каждой неудачи.',
       varies='Сюжет (биатлон, штрафные, лук, подачи, пенальти), число испытаний (3–4), p, сколько первых успешны.',
       answer_rule='P = p^k · (1 − p)^(n − k).',
       fipi=r'стреляет по одному разу (в|по) кажд\w+ из',
       mistakes=['умножают на число сочетаний (это не «ровно k», а заданный порядок)', 'забывают про вероятность промаха 1 − p'],
       maxdec=4, kim=kim(5, KIM5))
def gen_ep05_seq(r):
    i = r.randrange(len(SEQ_CTX))
    ctx, ev, _, _, _ = SEQ_CTX[i]
    lo, hi = [(2, 9), (4, 9), (2, 7), (4, 8), (1, 4)][i]       # правдоподобные вероятности для сюжета
    n = r.choice([3, 4, 4])
    k = r.randint(1, n - 1)
    p = F(r.randint(lo, hi), 10)
    ans = p ** k * (1 - p) ** (n - k)
    if not pnice(ans, 4):
        return None
    if 'пенальти' in ctx:
        first = {1: 'первый удар', 2: 'два первых удара', 3: 'три первых удара'}[k]
        last = {1: 'последний', 2: 'два последних', 3: 'три последних'}[n - k]
    elif 'подач' in ctx:
        first = {1: 'первая подача', 2: 'две первые подачи', 3: 'три первые подачи'}[k]
        last = {1: 'последняя', 2: 'две последние', 3: 'три последние'}[n - k]
        ev = 'удачными окажутся {first}, а {last} — неудачными' if k > 1 else 'удачной окажется {first}, а {last} — неудачными' \
            if n - k > 1 else 'удачной окажется {first}, а {last} — неудачной'
        if k > 1 and n - k == 1:
            ev = 'удачными окажутся {first}, а {last} — неудачной'
    elif 'Биатлонист' in ctx:
        first = {1: 'первую мишень', 2: 'две первые мишени', 3: 'три первые мишени'}[k]
        last = {1: 'последней', 2: 'двум последним', 3: 'трём последним'}[n - k]
    else:
        first = {1: 'первым', 2: 'двумя первыми', 3: 'тремя первыми'}[k]
        first += ' ' + ('броском' if 'Баскет' in ctx and k == 1 else 'бросками' if 'Баскет' in ctx else 'выстрелом' if k == 1 else 'выстрелами')
        last = {1: 'последним', 2: 'двумя последними', 3: 'тремя последними'}[n - k]
        first = 'при ' + first.replace('первым ', 'первом ').replace('двумя первыми ', 'двух первых ').replace('тремя первыми ', 'трёх первых ') \
            .replace('броском', 'броске').replace('бросками', 'бросках').replace('выстрелом', 'выстреле').replace('выстрелами', 'выстрелах')
        last = 'при ' + {1: 'последнем', 2: 'двух последних', 3: 'трёх последних'}[n - k]
    nn = {3: 'три', 4: 'четыре'}[n]
    head = ctx.format(n=n if 'мишеням' not in ctx else {3: 'трём', 4: 'четырём'}[n], p=tnum(p))
    head = head.replace(f'выполняет {n} штрафных броска', f'выполняет {nn} штрафных броска') \
        .replace(f'делает {n} выстрела', f'делает {nn} выстрела').replace(f'выполняет {n} первые подачи', f'выполняет {nn} подачи') \
        .replace(f'серию из {n} пенальти', f'серию из {"трёх" if n == 3 else "четырёх"} пенальти')
    q = head + f' {PROB} {ev.format(first=first, last=last)}.'
    e = f'Испытания независимы: P = {tnum(p)}^{k} · {tnum(1 - p)}^{n - k} = {tnum(ans)}.'

    def chk():
        outs = prob_all([p] * n)
        target = tuple([1] * k + [0] * (n - k))
        return same(num(ans), R(outs[target]))
    return pcard(q, num(ans), e=e), chk


ATL_CTX = [
    ('Помещение освещают {n} {lamp}. Каждая из них может перегореть в течение года с вероятностью {p} независимо от других.',
     'к концу года будет гореть хотя бы одна лампа', 'к концу года перегорят все лампы',
     ('лампы', 'лампы', 'ламп')),
    ('В серверной работают {n} {lamp}, каждый может отказать в течение суток с вероятностью {p} независимо от остальных.',
     'в течение суток хотя бы один сервер будет работать', 'в течение суток откажут все серверы', ('сервер', 'сервера', 'серверов')),
    ('В магазине {n} {lamp}. Каждый из них занят с клиентом с вероятностью {p}, независимо от других.',
     'в случайный момент хотя бы один продавец свободен', 'в случайный момент все продавцы заняты', ('продавец', 'продавца', 'продавцов')),
    ('Для полива теплицы установлены {n} {lamp}. Вероятность того, что насос выйдет из строя в течение сезона, равна {p}; насосы '
     'ломаются независимо.', 'в течение сезона хотя бы один насос останется исправным', 'в течение сезона все насосы выйдут из строя',
     ('насоса', 'насоса', 'насосов')),
    ('Сигнализацию обеспечивают {n} {lamp}. Каждый датчик в момент проникновения может не сработать с вероятностью {p} независимо '
     'от остальных.', 'хотя бы один датчик сработает', 'не сработает ни один датчик', ('датчика', 'датчика', 'датчиков')),
]


@proto('ep05-atleast', 'ege-prof', 5, 'Хотя бы один из независимых элементов исправен (все откажут)',
       invariant='Событие «хотя бы один работает» противоположно событию «все отказали», вероятность которого — '
                 'произведение вероятностей отказа.',
       varies='Сюжет (лампы, серверы, продавцы, насосы, датчики), число элементов (2–4), вероятность отказа, '
              'спрашиваем «хотя бы один» или «все».',
       answer_rule='P(все откажут) = pⁿ; P(хотя бы один работает) = 1 − pⁿ.',
       fipi=r'освещается (тремя лампами|фонарём)|хотя бы одна лампа',
       mistakes=['считают 1 − p вместо 1 − pⁿ', 'складывают вероятности вместо перемножения'],
       maxdec=4, kim=kim(5, KIM5 + ' Как в КИМ: «Помещение освещается тремя лампами… Найдите вероятность того, что … хотя бы одна лампа не перегорит».'))
def gen_ep05_atleast(r):
    i = r.randrange(len(ATL_CTX))
    ctx, ev_one, ev_all, forms = ATL_CTX[i]
    lo, hi = [(2, 9), (1, 3), (3, 8), (1, 4), (1, 3)][i]          # правдоподобные вероятности отказа
    n = r.choice([2, 3, 3, 4])
    p = F(r.randint(lo, hi), 10)
    ask_all = r.random() < 0.3
    ans = p ** n if ask_all else 1 - p ** n
    if not pnice(ans, 4):
        return None
    num_w = {2: 'две', 3: 'три', 4: 'четыре'}[n] if forms[0] == 'лампы' else {2: 'два', 3: 'три', 4: 'четыре'}[n]
    q = ctx.format(n=num_w, lamp=plural(n, *forms) if forms[0] != 'лампы' else 'лампы', p=tnum(p)) + \
        f' {PROB} {ev_all if ask_all else ev_one}.'
    e = (f'P = {tnum(p)}^{n} = {tnum(ans)}.' if ask_all else f'P = 1 − {tnum(p)}^{n} = {tnum(ans)}.')

    def chk():
        outs = prob_all([1 - p] * n)          # 1 — элемент работает
        tot = sum(v for s_, v in outs.items() if (sum(s_) == 0 if ask_all else sum(s_) >= 1))
        return same(num(ans), R(tot))
    return pcard(q, num(ans), e=e), chk


TOTAL_CTX = [
    ('Автомат фасует чай в пакетики. Вероятность того, что пакетик заполнен неправильно, равна {d}. Каждый пакетик проверяет весовой '
     'контроль. Неправильно заполненный пакетик отбраковывается с вероятностью {s}, а правильно заполненный — по ошибке с вероятностью {f}.',
     'случайно выбранный пакетик будет отбракован'),
    ('Для выявления вируса проводят экспресс-тест. Вероятность того, что случайно выбранный человек заражён, равна {d}. Если человек '
     'заражён, тест положителен с вероятностью {s}; если здоров — ошибочно положителен с вероятностью {f}.',
     'тест случайно выбранного человека окажется положительным'),
    ('На почте сканер проверяет посылки. Вероятность того, что в посылке запрещённый предмет, равна {d}. Сканер подаёт сигнал на такую '
     'посылку с вероятностью {s}, а на посылку без запрещённых предметов — с вероятностью {f}.',
     'сканер подаст сигнал на случайно выбранную посылку'),
    ('Датчик на конвейере проверяет бутылки. Вероятность того, что бутылка с трещиной, равна {d}. Датчик снимает бутылку с трещиной '
     'с вероятностью {s}, а целую бутылку снимает по ошибке с вероятностью {f}.', 'случайно выбранная бутылка будет снята с конвейера'),
]
TOTAL_MIX = [
    ('Первый завод выпускает {w}% всех электрических чайников магазина, второй — остальные. Среди чайников первого завода {d1}% '
     'неисправны, второго — {d2}%.', 'купленный в магазине чайник окажется неисправным'),
    ('В теплице {w}% рассады выращено из семян фирмы «Агро», остальное — фирмы «Сад». Всхожесть семян «Агро» равна {d1}%, '
     'а семян «Сад» — {d2}%.', 'случайно выбранное семя из этих партий взойдёт'),
    ('Утром {w}% учеников приезжают в школу на автобусе, остальные приходят пешком. Опаздывает {d1}% приезжающих на автобусе '
     'и {d2}% пешеходов.', 'случайно выбранный ученик опоздает'),
]


@proto('ep05-total', 'ege-prof', 5, 'Формула полной вероятности',
       invariant='Разбиваем исходы по гипотезам (брак/не брак, первый/второй поставщик), вероятность события — сумма '
                 'произведений вероятности гипотезы на условную вероятность события.',
       varies='Сюжет (контроль качества, тест, сканер, два поставщика, два способа), числа (доли в процентах или вероятности).',
       answer_rule='P(A) = P(H₁)·P(A|H₁) + P(H₂)·P(A|H₂).',
       fipi=r'(система забракует|фабрики выпускают|Первая фабрика)',
       mistakes=['учитывают только одну гипотезу', 'складывают условные вероятности без весов'],
       maxdec=4, kim=kim(5, KIM5 + ' Как в демоверсии 2027 (батарейки и контроль качества), но свой сюжет.'))
def gen_ep05_total(r):
    if r.random() < 0.6:
        ctx, ev = r.choice(TOTAL_CTX)
        d = F(r.randint(1, 20), 100)
        s_ = F(r.randint(85, 99), 100)
        f_ = F(r.randint(1, 9), 100)
        ans = d * s_ + (1 - d) * f_
        q = ctx.format(d=tnum(d), s=tnum(s_), f=tnum(f_)) + f' {PROB} {ev}.'
        e = f'P = {tnum(d)} · {tnum(s_)} + {tnum(1 - d)} · {tnum(f_)} = {tnum(ans)}.'
        w1, a1, a2 = d, s_, f_
    else:
        ctx, ev = r.choice(TOTAL_MIX)
        w = r.randrange(10, 91, 5)
        if 'Всхожесть' in ctx:
            d1, d2 = r.randint(70, 98), r.randint(70, 98)
        else:
            d1, d2 = r.randint(1, 12), r.randint(1, 12)
        if d1 == d2:
            return None
        w1, a1, a2 = F(w, 100), F(d1, 100), F(d2, 100)
        ans = w1 * a1 + (1 - w1) * a2
        q = ctx.format(w=w, d1=d1, d2=d2) + f' {PROB} {ev}.'
        e = f'P = {tnum(w1)} · {tnum(a1)} + {tnum(1 - w1)} · {tnum(a2)} = {tnum(ans)}.'
    if not pnice(ans, 4):
        return None

    def chk():
        # дерево исходов: (гипотеза, событие) → вероятность ветки
        tree = {(1, 1): w1 * a1, (1, 0): w1 * (1 - a1), (0, 1): (1 - w1) * a2, (0, 0): (1 - w1) * (1 - a2)}
        return sum(tree.values()) == 1 and same(num(ans), R(sum(v for (h, a_), v in tree.items() if a_)))
    return pcard(q, num(ans), e=e), chk


BAYES = [(F(d, 100), F(s_, 100), F(f_, 100)) for d in range(1, 51) for s_ in range(75, 100) for f_ in range(1, 26)
         if finite(F(d * s_, d * s_ + (100 - d) * f_)) and nice(F(d * s_, d * s_ + (100 - d) * f_), 4)]


@proto('ep05-bayes', 'ege-prof', 5, 'Условная вероятность гипотезы после проверки (формула Байеса)',
       invariant='Вероятность гипотезы при условии, что событие произошло, равна доле «ветки» гипотезы среди всех ветвей, '
                 'где событие произошло.',
       varies='Сюжет (контроль качества, тест, сканер, две фабрики), числа.',
       answer_rule='P(H|A) = P(H)·P(A|H) / P(A), P(A) — по формуле полной вероятности.',
       fipi=r'забракован[^.]*\. Найдите вероятность того, что (она|он) действительно',
       mistakes=['путают P(H|A) и P(A|H)', 'забывают делить на P(A)'],
       maxdec=4, kim=kim(5, KIM5))
def gen_ep05_bayes(r):
    d, s_, f_ = r.choice(BAYES)
    pa = d * s_ + (1 - d) * f_
    ans = d * s_ / pa
    ctx = r.choice([
        (f'Вероятность того, что изготовленная на станке втулка имеет брак, равна {tnum(d)}. Контроль бракует втулку с браком с '
         f'вероятностью {tnum(s_)}, а исправную — с вероятностью {tnum(f_)}. Случайно выбранная втулка была забракована. '
         f'{PROB} она действительно имеет брак.'),
        (f'Вероятность того, что пациент болен, равна {tnum(d)}. Анализ даёт положительный результат у больного с вероятностью '
         f'{tnum(s_)}, а у здорового — с вероятностью {tnum(f_)}. Анализ случайно выбранного пациента оказался положительным. '
         f'{PROB} пациент действительно болен.'),
        (f'Вероятность того, что письмо является рекламной рассылкой, равна {tnum(d)}. Фильтр отправляет в «Спам» рекламное письмо '
         f'с вероятностью {tnum(s_)}, а обычное — с вероятностью {tnum(f_)}. Случайное письмо оказалось в «Спаме». '
         f'{PROB} это рекламная рассылка.'),
        (f'Вероятность того, что в партии фруктов есть гнилые, равна {tnum(d)}. Проверяющий обнаруживает гнилые фрукты с вероятностью '
         f'{tnum(s_)}, а в хорошей партии по ошибке находит «гниль» с вероятностью {tnum(f_)}. Партию забраковали. '
         f'{PROB} в ней действительно были гнилые фрукты.')])
    q = ctx
    e = f'P(A) = {tnum(d)}·{tnum(s_)} + {tnum(1 - d)}·{tnum(f_)} = {tnum(pa)}; P = {tnum(d * s_)} : {tnum(pa)} = {tnum(ans)}.'

    def chk():
        # 10000 «равновозможных» объектов в пропорциях (точно, через Fraction)
        Nn = 10 ** 6
        bad = d * Nn
        bad_rej, good_rej = bad * s_, (Nn - bad) * f_
        return same(num(ans), R(bad_rej / (bad_rej + good_rej)))
    return pcard(q, num(ans), e=e), chk


INT_CTX = [
    ('Масса пачки масла после фасовки случайна: с вероятностью {p1} она меньше {hi} г и с вероятностью {p2} больше {lo} г.',
     'масса пачки больше {lo} г, но меньше {hi} г', (175, 185), (178, 182)),
    ('Диаметр изготовленного подшипника случаен: с вероятностью {p1} он меньше {hi} мм, а с вероятностью {p2} — больше {lo} мм.',
     'диаметр случайно выбранного подшипника больше {lo} мм, но меньше {hi} мм', (60, 70), (63, 67)),
    ('Курьер доставляет пиццу быстрее чем за {hi} минут с вероятностью {p1}, а дольше {lo} минут доставка длится с вероятностью {p2}.',
     'доставка займёт больше {lo}, но меньше {hi} минут', (15, 60), (20, 45)),
    ('Автомат разливает сок: с вероятностью {p1} в пакете оказывается меньше {hi} мл сока, а с вероятностью {p2} — больше {lo} мл.',
     'в случайном пакете окажется больше {lo} мл, но меньше {hi} мл сока', (960, 1040), (985, 1015)),
    ('Температура в холодильной камере в случайный момент ниже {hi} °C с вероятностью {p1} и выше {lo} °C с вероятностью {p2}.',
     'температура в камере выше {lo} °C, но ниже {hi} °C', (1, 8), (2, 6)),
]


@proto('ep05-interval', 'ege-prof', 5, 'Вероятность попадания в интервал по двум «односторонним» вероятностям',
       invariant='События «меньше верхней границы» и «больше нижней» в сумме покрывают всё и перекрываются как раз на '
                 'интервале: P(A ∩ B) = P(A) + P(B) − 1.',
       varies='Сюжет (масса пачки, диаметр, время доставки, объём сока, температура), границы и вероятности.',
       answer_rule='P(lo < X < hi) = P(X < hi) + P(X > lo) − 1.',
       fipi=r'(контрольное взвешивание|масса буханки)',
       mistakes=['перемножают вероятности', 'вычитают одну из другой'],
       maxdec=4, kim=kim(5, KIM5 + ' Как в КИМ: «…меньше 810 г, равна 0,96… больше 790 г, равна 0,82…»'))
def gen_ep05_interval(r):
    ctx, ev, (a, b), (c, d_) = r.choice(INT_CTX)
    lo = r.randint(a, c)
    hi = r.randint(d_, b)
    if hi <= lo:
        return None
    p1, p2 = F(r.randint(80, 99), 100), F(r.randint(70, 98), 100)
    ans = p1 + p2 - 1
    if ans <= 0:
        return None
    q = ctx.format(lo=lo, hi=hi, p1=tnum(p1), p2=tnum(p2)) + f' {PROB} {ev.format(lo=lo, hi=hi)}.'
    e = f'P = {tnum(p1)} + {tnum(p2)} − 1 = {tnum(ans)}.'

    def chk():
        # три области: X ≤ lo (масса 1 − p2), lo < X < hi (?), X ≥ hi (масса 1 − p1)
        mid = 1 - (1 - R(p2)) - (1 - R(p1))
        return same(num(ans), mid)
    return pcard(q, num(ans), e=e), chk


UNION_CTX = [
    ('В торговом центре два одинаковых банкомата. Вероятность того, что к концу дня в первом банкомате закончатся наличные, равна {p}. '
     'Такая же вероятность для второго. Вероятность того, что наличные закончатся в обоих банкоматах, равна {q}.',
     'к концу дня наличные останутся в обоих банкоматах', 'к концу дня наличные закончатся хотя бы в одном банкомате',
     'к концу дня наличные закончатся ровно в одном банкомате'),
    ('В офисе два принтера. Вероятность того, что за день в первом закончится бумага, равна {p}, во втором — тоже {p}. Вероятность того, '
     'что бумага закончится в обоих, равна {q}.', 'к концу дня бумага останется в обоих принтерах',
     'бумага закончится хотя бы в одном принтере', 'бумага закончится ровно в одном принтере'),
    ('В фойе стоят два кулера с водой. Вероятность того, что к вечеру опустеет первый кулер, равна {p}, второй — тоже {p}. Вероятность '
     'того, что опустеют оба, равна {q}.', 'к вечеру вода останется в обоих кулерах', 'к вечеру опустеет хотя бы один кулер',
     'к вечеру опустеет ровно один кулер'),
    ('На кассах самообслуживания магазина два одинаковых терминала. Вероятность того, что за день выйдет из строя первый, равна {p}, '
     'второй — тоже {p}. Вероятность того, что сломаются оба, равна {q}.', 'за день оба терминала останутся исправными',
     'за день сломается хотя бы один терминал', 'за день сломается ровно один терминал'),
]


@proto('ep05-union', 'ege-prof', 5, 'Два зависимых события с известной вероятностью совмещения',
       invariant='Вероятность объединения по формуле P(A ∪ B) = P(A) + P(B) − P(AB); «ни одно» — дополнение объединения.',
       varies='Сюжет (банкоматы, принтеры, кулеры, терминалы), p и P(AB), вопрос (ни в одном, хотя бы в одном, ровно в одном).',
       answer_rule='P(ни одно) = 1 − 2p + q; P(хотя бы одно) = 2p − q; P(ровно одно) = 2p − 2q.',
       fipi=r'два одинаковых автомата',
       mistakes=['считают события независимыми и перемножают', 'забывают вычесть вероятность совмещения'],
       maxdec=4, kim=kim(5, KIM5 + ' Как в КИМ: «…кофе закончится в двух автоматах, равна 0,18. Найдите вероятность того, что … останется в двух автоматах».'))
def gen_ep05_union(r):
    ctx, e_none, e_any, e_one = r.choice(UNION_CTX)
    p = F(r.randint(5, 40), 100)
    q_ = F(r.randint(1, 30), 100)
    if q_ >= p or 2 * p - q_ >= 1:
        return None
    ask = r.choice(['none', 'none', 'any', 'one'])
    ans = {'none': 1 - 2 * p + q_, 'any': 2 * p - q_, 'one': 2 * p - 2 * q_}[ask]
    if not pnice(ans, 4):
        return None
    q = ctx.format(p=tnum(p), q=tnum(q_)) + f' {PROB} {dict(none=e_none, any=e_any, one=e_one)[ask]}.'
    e = {'none': f'P(хотя бы одно) = 2 · {tnum(p)} − {tnum(q_)} = {tnum(2 * p - q_)}; P = 1 − {tnum(2 * p - q_)} = {tnum(ans)}.',
         'any': f'P = {tnum(p)} + {tnum(p)} − {tnum(q_)} = {tnum(ans)}.',
         'one': f'P = 2 · ({tnum(p)} − {tnum(q_)}) = {tnum(ans)}.'}[ask]

    def chk():
        # четыре клетки таблицы: оба, только первый, только второй, ни один
        cells = {(1, 1): R(q_), (1, 0): R(p - q_), (0, 1): R(p - q_), (0, 0): 1 - R(2 * p - q_)}
        if any(v < 0 for v in cells.values()):
            return False
        pred = {'none': lambda a, b: a + b == 0, 'any': lambda a, b: a + b >= 1, 'one': lambda a, b: a + b == 1}[ask]
        return same(num(ans), sum(v for (a, b), v in cells.items() if pred(a, b)))
    return pcard(q, num(ans), e=e), chk


DRAW_CTX = [
    ('В лотерейном барабане {items}. Ведущий наугад достаёт два шара.', 'шар', 'шара', 'шаров',
     [('белых', 'белый'), ('жёлтых', 'жёлтый'), ('оранжевых', 'оранжевый'), ('голубых', 'голубой')]),
    ('В ящике комода лежат {items} (все носки разные). Не глядя, достают два носка.', 'носок', 'носка', 'носков',
     [('серых', 'серый'), ('чёрных', 'чёрный'), ('полосатых', 'полосатый'), ('белых', 'белый')]),
    ('В коробке {items}. Случайным образом берут две конфеты.', 'конфета', 'конфеты', 'конфет',
     [('с орехом', 'с орехом'), ('с карамелью', 'с карамелью'), ('с вишней', 'с вишней'), ('с нугой', 'с нугой')]),
    ('В стакане стоят {items}. Наугад вынимают две ручки.', 'ручка', 'ручки', 'ручек',
     [('синих', 'синяя'), ('чёрных', 'чёрная'), ('зелёных', 'зелёная'), ('красных', 'красная')]),
]


@proto('ep05-two-draw', 'ege-prof', 5, 'Выбор двух предметов без возвращения: один одного цвета и один другого (или оба одного)',
       invariant='Считаем число подходящих пар и делим на число всех пар C(N, 2) (или перемножаем вероятности по шагам с учётом '
                 'двух порядков).',
       varies='Сюжет (шары, носки, конфеты, ручки), количества трёх видов, событие (по одному двух видов, оба одного вида).',
       answer_rule='P(один X и один Y) = x·y / C(N, 2); P(оба X) = C(x, 2) / C(N, 2).',
       fipi=r'Случайным образом выбирают два',
       mistakes=['забывают второй порядок (множитель 2)', 'выбирают с возвращением'],
       maxdec=4, kim=kim(5, KIM5 + ' Как в открытом варианте 2026: три вида предметов, выбирают два.'))
def gen_ep05_two_draw(r):
    ctx, one, few, many, kinds = r.choice(DRAW_CTX)
    ks = r.sample(kinds, 3)
    cnt = [r.randint(2, 14) for _ in range(3)]
    N = sum(cnt)
    ask = r.choice(['pair', 'pair', 'same'])
    if ask == 'pair':
        ans = F(cnt[0] * cnt[1], N * (N - 1) // 2)
    else:
        ans = F(cnt[0] * (cnt[0] - 1) // 2, N * (N - 1) // 2)
    if not pnice(ans, 4):
        return None
    fem = one in ('конфета', 'ручка')
    items = ', '.join(f'{c} {k[0]}' for c, k in zip(cnt[:-1], ks[:-1])) + f' и {cnt[-1]} {ks[-1][0]} {plural(cnt[-1], one, few, many)}'
    if one == 'конфета':
        items = ', '.join(f'{c} {plural(c, one, few, many)} {k[0]}' for c, k in zip(cnt, ks))
        items = items.rsplit(', ', 1)[0] + ' и ' + items.rsplit(', ', 1)[1]
    head = ctx.format(items=items)
    if ask == 'pair':
        if one == 'конфета':
            ev = f'окажется одна конфета {ks[0][1]} и одна {ks[1][1]}'
        else:
            ev = (f'окажутся {"одна" if fem else "один"} {ks[0][1]} и {"одна" if fem else "один"} {ks[1][1]} {one}')
    else:
        if one == 'конфета':
            ev = f'обе конфеты будут {ks[0][1]}'
        else:
            adj = ks[0][0][:-2] + ('ыми' if ks[0][0].endswith('ых') else 'ими')      # «серых» → «серыми»
            ev = f'{"обе вынутые" if fem else "оба вынутых"} {few} будут {adj}'
    q = f'{head} {PROB} {ev}.'
    e = (f'Всего пар C({N}, 2) = {N * (N - 1) // 2}, подходящих ' +
         (f'{cnt[0]} · {cnt[1]} = {cnt[0] * cnt[1]}' if ask == 'pair' else f'C({cnt[0]}, 2) = {cnt[0] * (cnt[0] - 1) // 2}') +
         f'; P = {tnum(ans)}.')

    def chk():
        bag = [i for i in range(3) for _ in range(cnt[i])]
        pairs = list(combinations(range(N), 2))
        if ask == 'pair':
            fav = sum(1 for a, b in pairs if {bag[a], bag[b]} == {0, 1})
        else:
            fav = sum(1 for a, b in pairs if bag[a] == bag[b] == 0)
        return same(num(ans), sp.Rational(fav, len(pairs)))
    return pcard(q, num(ans), e=e), chk


@proto('ep05-cond-dice', 'ege-prof', 5, 'Условная вероятность на двух бросках кости',
       invariant='Условие сужает пространство исходов: перечисляем исходы, удовлетворяющие условию, и среди них — '
                 'благоприятные.',
       varies='Условие (какое-то число не выпало ни разу; сумма равна s; хотя бы раз выпало …), событие (сумма, '
              'чётность, хотя бы одно число), формулировка.',
       answer_rule='P(A | B) = |A ∩ B| / |B| (исходы — упорядоченные пары).',
       fipi=r'Известно, что[^.]*не выпало ни разу',
       mistakes=['делят на 36, а не на число исходов, удовлетворяющих условию', 'считают (a; b) и (b; a) одним исходом'],
       maxdec=4, kim=kim(5, KIM5 + ' Как в КИМ: «Игральную кость бросили два раза. Известно, что … Найдите при этом условии вероятность события «…»».'))
def gen_ep05_cond_dice(r):
    kind = r.choice(['no_k', 'no_k', 'sum', 'has'])
    NUMW = {1: 'одно очко', 2: 'два очка', 3: 'три очка', 4: 'четыре очка', 5: 'пять очков', 6: 'шесть очков'}
    if kind == 'no_k':
        k = r.randint(1, 6)
        cond_t = f'ни при одном из бросков не выпало {NUMW[k]}'
        cond = lambda a, b: a != k and b != k
    elif kind == 'sum':
        s0 = r.randint(3, 11)
        cond_t = f'в сумме выпало {s0} {plural(s0, "очко", "очка", "очков")}'
        cond = lambda a, b: a + b == s0
    else:
        k = r.randint(1, 6)
        cond_t = f'хотя бы один раз выпало {NUMW[k]}'
        cond = lambda a, b: k in (a, b)
    evs = [('сумма выпавших очков равна {t}', lambda a, b, t: a + b == t, True), ('сумма выпавших очков больше {t}', lambda a, b, t: a + b > t, True),
           ('хотя бы раз выпало {t} {o}', lambda a, b, t: t in (a, b), False),
           ('оба раза выпало чётное число очков', lambda a, b, t: a % 2 == 0 and b % 2 == 0, None),
           ('в первый раз выпало меньше {t} {og}', lambda a, b, t: a < t, False)]
    et, pred, is_sum = r.choice(evs)
    t = r.randint(4, 10) if is_sum else r.randint(1, 6) if is_sum is False else 0
    B = [(a, b) for a in range(1, 7) for b in range(1, 7) if cond(a, b)]
    Afav = [x for x in B if pred(x[0], x[1], t)]
    if not Afav or len(Afav) == len(B):
        return None
    ans = F(len(Afav), len(B))
    if not pnice(ans, 4):
        return None
    evt = et.format(t=t, o=plural(t, 'очко', 'очка', 'очков'), og='очка' if t == 1 else 'очков')
    q = pick(r, f'Кубик бросили два раза, и оказалось, что {cond_t}. Найдите при этом условии вероятность события «{evt}».',
             f'Игральный кубик подбросили дважды. Стало известно, что {cond_t}. Найдите при этом условии вероятность события «{evt}».')
    e = f'Исходов, где {cond_t}: {len(B)}; из них подходящих {len(Afav)}: P = {len(Afav)}/{len(B)} = {tnum(ans)}.'

    def chk():
        pa_b = sum(sp.Rational(1, 36) for a in range(1, 7) for b in range(1, 7) if cond(a, b) and pred(a, b, t))
        pb = sum(sp.Rational(1, 36) for a in range(1, 7) for b in range(1, 7) if cond(a, b))
        return same(num(ans), pa_b / pb)
    return pcard(q, num(ans), e=e), chk


@proto('ep05-until', 'ege-prof', 5, 'Испытания до первого успеха: сколько попыток нужно',
       invariant='Вероятность хотя бы одного успеха за n попыток равна 1 − (1 − p)ⁿ; ищем наименьшее n, при котором она '
                 'не меньше заданной.',
       varies='Сюжет (стрелок, рыбак, звонки клиентам, подключение к сети), p, порог.',
       answer_rule='Наименьшее n с 1 − (1 − p)ⁿ ≥ P₀.',
       fipi=r'стреляет по мишени до тех пор',
       mistakes=['берут n, при котором вероятность меньше порога', 'считают вероятность успеха за n попыток равной n·p'],
       maxdec=0, kim=kim(5, 'Как в КИМ: «…Какое наименьшее количество патронов нужно дать стрелку, чтобы он поразил цель с вероятностью '
                            'не меньше 0,7?»; ответ — натуральное число.'))
def gen_ep05_until(r):
    p = F(r.choice([3, 4, 5, 5, 6, 7, 8]), 10)
    P0 = F(r.randint(60, 99), 100) if r.random() < 0.7 else F(r.randint(990, 999), 1000)
    n, cur = 0, F(0)
    while cur < P0:
        n += 1
        cur = 1 - (1 - p) ** n
    if n < 2 or n > 12:
        return None
    # порог не должен совпадать с достигнутым значением «впритык» на предыдущем шаге
    ctx = r.choice([
        (f'Стрелок в тире стреляет по мишени, пока не поразит её. Вероятность попадания при каждом выстреле равна {tnum(p)}. '
         f'Какое наименьшее число патронов нужно выдать стрелку, чтобы он поразил мишень с вероятностью не меньше {tnum(P0)}?'),
        (f'Менеджер обзванивает клиентов, пока кто-нибудь не согласится на встречу. Каждый клиент независимо соглашается с '
         f'вероятностью {tnum(p)}. Какое наименьшее число клиентов нужно внести в список, чтобы менеджер договорился о встрече '
         f'с вероятностью не меньше {tnum(P0)}?'),
        (f'Программа пытается подключиться к серверу, пока подключение не удастся. Каждая попытка успешна с вероятностью {tnum(p)} '
         f'независимо от других. Какое наименьшее число попыток нужно разрешить программе, чтобы подключение состоялось с '
         f'вероятностью не меньше {tnum(P0)}?'),
        (f'Баскетболист бросает мяч в корзину, пока не попадёт. Вероятность попадания при каждом броске равна {tnum(p)}. Какое '
         f'наименьшее число бросков нужно ему разрешить, чтобы он попал с вероятностью не меньше {tnum(P0)}?')])
    q = ctx
    e = f'1 − {tnum(1 - p)}ⁿ ≥ {tnum(P0)}: при n = {n - 1} {tnum(1 - (1 - p) ** (n - 1))} < {tnum(P0)}, при n = {n} — уже не меньше.'

    def chk():
        # моделирование по шагам: вероятность ещё не попасть после k попыток
        miss, k = sp.Integer(1), 0
        while 1 - miss < R(P0):
            miss *= 1 - R(p)
            k += 1
        return k == n
    return pcard(q, num(n), e=e), chk


@proto('ep05-bernoulli', 'ege-prof', 5, 'Ровно k успехов в n независимых испытаниях (схема Бернулли)',
       invariant='Число последовательностей с k успехами равно C(n, k), каждая имеет вероятность p^k(1 − p)^(n − k).',
       varies='Сюжет (монета, стрелок, угадывание ответов теста, всхожесть семян), n (3–5), k, p.',
       answer_rule='P = C(n, k) · p^k · (1 − p)^(n − k).',
       fipi=r'ровно (два|три|\d+) раза?[^.]*(из|при)',
       mistakes=['забывают множитель C(n, k)', 'путают число успехов и неудач'],
       maxdec=4, kim=kim(5, KIM5))
def gen_ep05_bernoulli(r):
    kind = r.choice(['coin', 'shot', 'guess', 'seed'])
    if kind == 'coin':
        n = r.randint(3, 5)
        p = F(1, 2)
    elif kind == 'guess':
        n = r.randint(3, 4)
        p = r.choice([F(1, 2), F(1, 4), F(1, 5)])
    else:
        n = r.randint(3, 4)
        p = F(r.randint(1, 9), 10)
    k = r.randint(1, n - 1)
    ans = sp.binomial(n, k) * p ** k * (1 - p) ** (n - k)
    ans = F(int(sp.binomial(n, k))) * p ** k * (1 - p) ** (n - k)
    if not pnice(ans, 4):
        return None
    kw = {1: 'ровно один раз', 2: 'ровно два раза', 3: 'ровно три раза', 4: 'ровно четыре раза'}[k]
    if kind == 'coin':
        q = f'Монету подбрасывают {n} {plural(n, "раз", "раза", "раз")}. {PROB} орёл окажется сверху {kw}.'
    elif kind == 'shot':
        q = (f'Стрелок в тире стреляет по мишени {n} {plural(n, "раз", "раза", "раз")}; каждый выстрел независимо от других '
             f'попадает в цель с вероятностью {tnum(p)}. {PROB} мишень будет поражена {kw}.')
    elif kind == 'guess':
        opts_n = p.denominator
        q = (f'В тесте {n} {plural(n, "вопрос", "вопроса", "вопросов")}, к каждому дано {opts_n} варианта ответа, из которых верен '
             f'только один' if opts_n < 5 else f'В тесте {n} {plural(n, "вопрос", "вопроса", "вопросов")}, к каждому дано {opts_n} '
             f'вариантов ответа, из которых верен только один') + \
            f'. Ученик отвечает наугад. {PROB} он угадает {"ровно один ответ" if k == 1 else f"ровно {k} ответа"}.'
    else:
        q = (f'Посеяли {n} {plural(n, "семечко", "семечка", "семечек")} огурца. Каждое всходит с вероятностью {tnum(p)} независимо '
             f'от других. {PROB} взойдут ровно {k} из {n}.' if k > 1 else
             f'Посеяли {n} {plural(n, "семечко", "семечка", "семечек")} огурца. Каждое всходит с вероятностью {tnum(p)} независимо '
             f'от других. {PROB} взойдёт ровно одно из них.')
    e = f'P = C({n}, {k}) · {tnum(p)}^{k} · {tnum(1 - p)}^{n - k} = {tnum(ans)}.'

    def chk():
        outs = prob_all([p] * n)
        return same(num(ans), R(sum(v for s_, v in outs.items() if sum(s_) == k)))
    return pcard(q, num(ans), e=e), chk


SAME_GROUP = [(g, s_) for g in range(2, 10) for s_ in range(3, 51) if finite(F(s_ - 1, g * s_ - 1)) and g * s_ <= 100]
GNUM = {2: 'две', 3: 'три', 4: 'четыре', 5: 'пять', 6: 'шесть', 7: 'семь', 8: 'восемь', 9: 'девять'}
GNUM_D = {2: 'двум', 3: 'трём', 4: 'четырём', 5: 'пяти', 6: 'шести', 7: 'семи', 8: 'восьми', 9: 'девяти'}
GNUM_M = {2: 'два', 3: 'три', 4: 'четыре', 5: 'пять', 6: 'шесть', 7: 'семь', 8: 'восемь', 9: 'девять'}


@proto('ep05-same-group', 'ege-prof', 5, 'Случайное деление на группы: два данных человека в одной группе',
       invariant='Фиксируем место первого; для второго остаётся N − 1 равновозможных мест, из них s − 1 — в той же группе.',
       varies='Сюжет (близнецы и подгруппы класса, друзья и отряды лагеря, турнир, лодки, команды), N и размер группы s, '
              'вопрос «в одной» или «в разных».',
       answer_rule='P = (s − 1) / (N − 1); в разных — 1 − (s − 1)/(N − 1).',
       fipi=r'(близнец|случайным образом делят)',
       mistakes=['делят s на N', 'не учитывают, что одно место уже занято первым человеком'],
       maxdec=4, kim=kim(5, KIM5))
def gen_ep05_same_group(r):
    g, s_ = r.choice(SAME_GROUP)
    N = g * s_
    ans = F(s_ - 1, N - 1)
    if not pnice(ans, 4):
        return None
    diff = r.random() < 0.35
    if diff:
        ans = 1 - ans
    few = g <= 4
    sub = f'{GNUM[g]} {"равные подгруппы" if few else "равных подгрупп"}'
    grp = f'{GNUM[g]} {"равные группы" if few else "равных групп"}'
    otr = f'{GNUM_M[g]} {"отряда" if few else "отрядов"}'
    boats = f'{GNUM[g]} {"одинаковые лодки" if few else "одинаковых лодок"}'
    teams = f'{GNUM[g]} {"команды" if few else "команд"}'
    one = N % 10 == 1 and N % 100 != 11
    pc = f'{s_} {plural(s_, "человеку", "человека", "человек")}'
    ctx = r.choice([
        (f'В параллели {N} {plural(N, "ученик", "ученика", "учеников")}, среди них двое близнецов — Лёша и Миша. Всех случайным образом делят на {sub} для занятий '
         f'английским. {PROB} близнецы окажутся {"в разных подгруппах" if diff else "в одной подгруппе"}.' if 18 <= N <= 60 and g <= 3 else ''),
        (f'В лагере {N} {plural(N, "ребёнок", "ребёнка", "детей")}, среди них подруги Оля и Света. Детей случайно распределяют на {otr} по {pc}. '
         f'{PROB} подруги попадут {"в разные отряды" if diff else "в один отряд"}.' if s_ >= 7 else ''),
        (f'В турнире по настольному теннису {"участвует" if one else "участвуют"} {N} {plural(N, "спортсмен", "спортсмена", "спортсменов")}, в том числе братья Ивановы. Жеребьёвкой их делят на {grp}. '
         f'{PROB} братья окажутся {"в разных группах" if diff else "в одной группе"}.'),
        (f'Группу из {N} {plural(N, "туриста", "туристов", "туристов")} случайным образом рассаживают в {boats} по {pc}. '
         f'{PROB} туристы А. и Б. поплывут {"в разных лодках" if diff else "в одной лодке"}.' if s_ <= 7 else ''),
        (f'На квест {"пришёл" if one else "пришли"} {N} {plural(N, "школьник", "школьника", "школьников")}, среди них Катя и Маша. Всех случайно разбивают на {teams} по {pc}. '
         f'{PROB} Катя и Маша окажутся {"в разных командах" if diff else "в одной команде"}.' if s_ <= 13 else ''),
        (f'На экзамен {"пришёл" if one else "пришли"} {N} {plural(N, "студент", "студента", "студентов")}, среди них друзья Петров и Сидоров. Их случайным образом '
         f'распределяют по {GNUM_D[g]} аудиториям, в каждую по {pc}. {PROB} друзья окажутся '
         f'{"в разных аудиториях" if diff else "в одной аудитории"}.'),
        (f'На сборы {"приехал" if one else "приехали"} {N} {plural(N, "пловец", "пловца", "пловцов")}, в том числе братья Кравец. Тренеры случайно делят всех на '
         f'{grp} для тренировок. {PROB} братья попадут {"в разные группы" if diff else "в одну группу"}.')])
    if not ctx:
        return None
    q = ctx
    e = f'Для второго человека {N - 1} {plural(N - 1, "место", "места", "мест")}, в той же группе {s_ - 1}: P = {s_ - 1}/{N - 1}' + \
        (f', в разных: 1 − это = {tnum(ans)}.' if diff else f' = {tnum(ans)}.')

    def chk():
        # перебор: первый на месте 0 (группы по порядку мест), второй — на любом другом из N − 1 мест
        grp_of = lambda i: i // s_
        same_cnt = sum(1 for j in range(1, N) if grp_of(j) == grp_of(0))
        v = sp.Rational(same_cnt, N - 1)
        return same(num(ans), 1 - v if diff else v)
    return pcard(q, num(ans), e=e), chk


INDEP_CTX = [
    ('Два стрелка одновременно стреляют по мишени. Первый попадает с вероятностью {p1}, второй — с вероятностью {p2}.',
     {'both': 'в мишени будут два попадания', 'one': 'в мишень попадёт ровно один стрелок', 'any': 'мишень будет поражена хотя бы одним стрелком',
      'none': 'оба стрелка промахнутся'}),
    ('Студент сдаёт два экзамена. Вероятность сдать первый равна {p1}, второй — {p2}; результаты экзаменов независимы.',
     {'both': 'студент сдаст оба экзамена', 'one': 'студент сдаст ровно один экзамен', 'any': 'студент сдаст хотя бы один экзамен',
      'none': 'студент не сдаст ни одного экзамена'}),
    ('На маршруте работают два автобуса. Вероятность того, что первый опоздает, равна {p1}, второй — {p2}, опоздания независимы.',
     {'both': 'опоздают оба автобуса', 'one': 'опоздает ровно один автобус', 'any': 'опоздает хотя бы один автобус',
      'none': 'ни один автобус не опоздает'}),
    ('В квартире стоят два независимых датчика дыма. Первый срабатывает при задымлении с вероятностью {p1}, второй — {p2}.',
     {'both': 'при задымлении сработают оба датчика', 'one': 'при задымлении сработает ровно один датчик',
      'any': 'при задымлении сработает хотя бы один датчик', 'none': 'при задымлении не сработает ни один датчик'}),
]


@proto('ep05-indep-two', 'ege-prof', 5, 'Два независимых события с разными вероятностями',
       invariant='Вероятность совместного наступления независимых событий — произведение; «ровно одно» — сумма двух '
                 'несовместных вариантов, «хотя бы одно» — через дополнение.',
       varies='Сюжет (стрелки, экзамены, автобусы, датчики), вероятности, вопрос (оба, ровно одно, хотя бы одно, ни одного).',
       answer_rule='P(оба) = p₁p₂; P(ровно одно) = p₁(1 − p₂) + (1 − p₁)p₂; P(хотя бы одно) = 1 − (1 − p₁)(1 − p₂).',
       fipi=r'Два стрелка|независим\w*[^.]*двух',
       mistakes=['складывают вероятности для «хотя бы одно»', 'для «ровно одно» берут только один вариант'],
       maxdec=4, kim=kim(5, KIM5))
def gen_ep05_indep_two(r):
    ctx, evs = r.choice(INDEP_CTX)
    p1, p2 = F(r.randint(1, 19), 20), F(r.randint(1, 19), 20)
    if p1 == p2:
        return None
    ask = r.choice(['both', 'one', 'any', 'none'])
    ans = {'both': p1 * p2, 'one': p1 * (1 - p2) + (1 - p1) * p2, 'any': 1 - (1 - p1) * (1 - p2), 'none': (1 - p1) * (1 - p2)}[ask]
    if not pnice(ans, 4):
        return None
    q = ctx.format(p1=tnum(p1), p2=tnum(p2)) + f' {PROB} {evs[ask]}.'
    e = {'both': f'P = {tnum(p1)} · {tnum(p2)} = {tnum(ans)}.',
         'one': f'P = {tnum(p1)} · {tnum(1 - p2)} + {tnum(1 - p1)} · {tnum(p2)} = {tnum(ans)}.',
         'any': f'P = 1 − {tnum(1 - p1)} · {tnum(1 - p2)} = {tnum(ans)}.',
         'none': f'P = {tnum(1 - p1)} · {tnum(1 - p2)} = {tnum(ans)}.'}[ask]

    def chk():
        outs = prob_all([p1, p2])
        pred = {'both': lambda s_: sum(s_) == 2, 'one': lambda s_: sum(s_) == 1, 'any': lambda s_: sum(s_) >= 1,
                'none': lambda s_: sum(s_) == 0}[ask]
        return same(num(ans), R(sum(v for s_, v in outs.items() if pred(s_))))
    return pcard(q, num(ans), e=e), chk


# КЭС для №3 точнее общего паспорта: многогранники — 7.3, тела вращения — 7.4
_KES3 = {'7.3': ('ep03-box-pyr', 'ep03-box-prism', 'ep03-prism-part', 'ep03-mid-vol', 'ep03-mid-side', 'ep03-cube-cut',
                 'ep03-box-diag'),
         '7.4': ('ep03-cyl-cone', 'ep03-cyl-cone-side', 'ep03-ball-cyl', 'ep03-cone-ball', 'ep03-sphere-cone', 'ep03-scale',
                 'ep03-ball-section', 'ep03-cone-level', 'ep03-cyl-pour', 'ep03-cyl-immerse')}
for _k, _ids in _KES3.items():
    for _pid in _ids:
        PROTO_KIM = __import__('mathlib').PROTO[_pid]['kim']
        PROTO_KIM['kes'] = [_k]
