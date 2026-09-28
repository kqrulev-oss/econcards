"""Общие помощники генераторов по математике (исследование, в сайт не входит).

Здесь форматирование чисел, реестры генераторов (GEN — старые генераторы по заданиям,
PROTO — генераторы по прототипам) и простые SVG-рисунки. Используют gen_math.py
и модули прототипов proto_*.py.
"""
import json
import math
import random
import sys
from collections import Counter
from fractions import Fraction as F

import sympy as sp

X = sp.Symbol('x', real=True)

# ---------------------------------------------------------------- форматирование


def finite(x):
    """True, если дробь записывается конечной десятичной."""
    d = F(x).denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    return d == 1


def decimals(x):
    """Сколько знаков после запятой у конечной десятичной дроби."""
    x = F(x)
    n = 0
    while x.denominator != 1:
        x *= 10
        n += 1
    return n


def num(x):
    """Число для ответа: '12', '-3,5' (минус ASCII — так его разбирает sameNumber в lib.js)."""
    x = F(x)
    if x.denominator == 1:
        return str(x.numerator)
    assert finite(x), x
    n = decimals(x)
    s = f'{abs(x.numerator) * 10**n // x.denominator:0{n + 1}d}'
    s = s[:-n] + ',' + s[-n:]
    return ('-' if x < 0 else '') + s


def tnum(x):
    """Число в условии: с типографским минусом."""
    return num(x).replace('-', '−')


def ftxt(x):
    """Число в условии; бесконечную дробь пишем как (p/q)."""
    x = F(x)
    if finite(x):
        return tnum(x)
    return f'{"−" if x < 0 else ""}({abs(x.numerator)}/{x.denominator})'


def par(x):
    """Отрицательное число в скобках: для записи произведений в разборе."""
    return f'({tnum(x)})' if F(x) < 0 else tnum(x)


def signed(c, first=False):
    """Коэффициент со знаком для записи многочлена: ' + 3', ' − 5'."""
    c = F(c)
    if first:
        return ftxt(c)
    return f' − {ftxt(-c)}' if c < 0 else f' + {ftxt(c)}'


def poly(coefs, var='x'):
    """[a, b, c] → 'ax² + bx + c' без нулевых членов и единиц."""
    sup = {1: '', 2: '²', 3: '³', 4: '⁴'}
    deg = len(coefs) - 1
    out = ''
    for i, c in enumerate(coefs):
        p = deg - i
        if c == 0:
            continue
        body = var + sup.get(p, f'^{p}') if p else ''
        if p and abs(c) == 1:
            coef = '' if c > 0 else '−'
            term = coef + body
            if out:
                term = (' + ' if c > 0 else ' − ') + body
        else:
            term = (ftxt(c) if not out else signed(c)) + body
        out += term
    return out or '0'


def lin(a, b, var='x'):
    """a·x + b в виде текста."""
    return poly([a, b], var)


def nice(x, maxdec=2, lim=10000):
    x = F(x)
    return finite(x) and decimals(x) <= maxdec and abs(x) <= lim


SUB = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')


def card(gid, q, a, e='', k='num', **kw):
    c = {'id': '', 't': GEN[gid]['t'], 'p': GEN[gid]['p'], 'k': k, 'q': q, 'a': a}
    if e:
        c['e'] = e
    c.update(kw)
    return c


def same(a, b):
    """Сравнение как sameNumber в lib.js: запятая и точка равноправны."""
    try:
        return abs(float(str(a).replace(',', '.')) - float(sp.N(b))) < 1e-9
    except (TypeError, ValueError):
        return False


GEN = {}


def gen(gid, exam, n, title, t, p=None, gen_type='param', maxdec=2, lim=10000):
    def deco(fn):
        GEN[gid] = dict(fn=fn, exam=exam, n=n, title=title, t=t, p=p or f'g-{gid}', gen=gen_type, maxdec=maxdec, lim=lim)
        return fn
    return deco


TRIPLES = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (9, 40, 41), (12, 35, 37), (11, 60, 61),
           (28, 45, 53), (33, 56, 65), (16, 63, 65), (48, 55, 73), (13, 84, 85), (36, 77, 85), (39, 80, 89), (65, 72, 97)]



# ================================================================ прототипы
#
# Прототип — разновидность задания КИМ: неизменная схема решения, меняются числа,
# сюжет, слова. Каждый прототип регистрируется одним из двух способов:
#
#   @proto(...)       — параметрический генератор gen(r) → (card, check) или None;
#   proto_llm(...)    — рецепт для ИИ, когда генератор невозможен (доказательство,
#                       сложный сюжет): числа задаёт и проверяет код, текст пишет ИИ.
#
# card строится через pcard(q, a, e=..., k='num', svg=..., o=...).
# check() пересчитывает ответ НЕЗАВИСИМО (sympy / Fraction / перебор) → True/False.
# fipi — регулярное выражение (без учёта регистра) для текстов открытого банка ФИПИ:
# по нему самопроверка считает, сколько заданий банка покрывает прототип. Сами тексты
# банка в репозиторий не кладутся.

PROTO = {}
EXAMS = {'ege-prof': 'ЕГЭ профиль (КИМ 2027)', 'ege-base': 'ЕГЭ база', 'oge': 'ОГЭ'}


def proto(pid, exam, n, title, invariant, varies, answer_rule, fipi=None, mistakes=(), maxdec=2, lim=10000,
          svg=False, card_kind='num', note='', kim=None):
    """Регистрирует параметрический генератор прототипа.

    kim — паспорт задания по КИМ (для проверки «экзаменационности»):
      {'level': 'Б'|'П'|'В', 'points': 1, 'minutes': 3, 'kes': ['7.1'], 'kt': ['КТ 9'],
       'answer': 'число' | 'цифра варианта' | 'цифры' | 'соответствие' | 'развёрнутый',
       'style': 'чем формулировка совпадает с КИМ: «Ответ дайте в …», округление, единицы'}"""
    assert exam in EXAMS, exam
    assert pid not in PROTO, f'повтор id прототипа: {pid}'

    def deco(fn):
        PROTO[pid] = dict(id=pid, exam=exam, n=n, title=title, invariant=invariant, varies=varies,
                          answer_rule=answer_rule, fipi=fipi, mistakes=list(mistakes), maxdec=maxdec, lim=lim,
                          svg=svg, card_kind=card_kind, note=note, kim=kim or {}, fn=fn, gen=fn.__name__, kind='param')
        return fn
    return deco


def proto_llm(pid, exam, n, title, invariant, varies, answer_rule, recipe, example, capacity, fipi=None,
              mistakes=(), svg=False, note='', kim=None):
    """Рецепт llm: recipe = {'prompt': что пишет ИИ, 'code': что задаёт код, 'check': как проверяется};
    example = {'q': наш пример, 'a': ответ, 'chk': lambda: True/False — пересчёт ответа примера};
    capacity — оценка числа разных аналогов (int) и откуда она (строка в recipe['capacity'])."""
    assert exam in EXAMS, exam
    assert pid not in PROTO, f'повтор id прототипа: {pid}'
    assert {'prompt', 'code', 'check'} <= set(recipe), pid
    PROTO[pid] = dict(id=pid, exam=exam, n=n, title=title, invariant=invariant, varies=varies, answer_rule=answer_rule,
                      fipi=fipi, mistakes=list(mistakes), svg=svg, note=note, recipe=recipe, example=example,
                      capacity=capacity, kim=kim or {}, kind='llm')


def pcard(q, a, e='', k='num', **kw):
    """Карточка прототипа; id, t (тема) и p проставляет самопроверка."""
    c = {'id': '', 't': '', 'p': '', 'k': k, 'q': q, 'a': a}
    if e:
        c['e'] = e
    c.update(kw)
    return c


def R(x):
    """Fraction → sympy.Rational (для проверок)."""
    x = F(x)
    return sp.Rational(x.numerator, x.denominator)


def pick(r, *variants):
    """Случайный вариант формулировки: pick(r, 'Найдите', 'Вычислите')."""
    return r.choice(variants)


def plural(n, one, few, many):
    """Согласование с числом: plural(5, 'рубль', 'рубля', 'рублей')."""
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def raz(k):
    """«в 3 раза», «в 5 раз»."""
    return f'в {k} {plural(k, "раз", "раза", "раз")}'


# ================================================================ SVG
# Стиль как у графиков задания 8 в tools/build_packs.py: белый фон, серая клетка,
# синяя линия #2F6BFF, акцент #E4572E, шрифт Arial 12.

INK, BLUE, RED, GRID = '#15181E', '#2F6BFF', '#E4572E', '#E3E6EC'


def _svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" font-family="Arial" font-size="12" fill="{INK}">'
            '<defs><marker id="a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">'
            '<path d="M0 0L10 5L0 10z"/></marker></defs>'
            f'<rect width="{w:.0f}" height="{h:.0f}" fill="#fff"/>{body}</svg>')


def svg_plot(fns, x0, x1, y0, y1, extra=None, width=360, axes=True, points=()):
    """График одной или нескольких функций на клетчатой сетке (единица = клетка).
    fns — функция или список функций (float → float, может бросать ValueError/ZeroDivisionError);
    points — [(x, y)] выделенные точки; extra(sx, sy) → строка SVG поверх."""
    if callable(fns):
        fns = [fns]
    u = (width - 40) / (x1 - x0)
    w, h = width, (y1 - y0) * u + 30
    sx = lambda x: 20 + (x - x0) * u
    sy = lambda y: 15 + (y1 - y) * u
    grid = ''.join(f'<line x1="{sx(i):.1f}" y1="{sy(y0):.1f}" x2="{sx(i):.1f}" y2="{sy(y1):.1f}"/>' for i in range(math.ceil(x0), math.floor(x1) + 1))
    grid += ''.join(f'<line x1="{sx(x0):.1f}" y1="{sy(j):.1f}" x2="{sx(x1):.1f}" y2="{sy(j):.1f}"/>' for j in range(math.ceil(y0), math.floor(y1) + 1))
    lines = ''
    for k, fn in enumerate(fns):
        segs, pts = [], []
        for i in range(601):
            x = x0 + (x1 - x0) * i / 600
            try:
                y = fn(x)
            except (ZeroDivisionError, ValueError, OverflowError):
                y = None
            if y is not None and y0 - 3 <= y <= y1 + 3:
                pts.append(f'{sx(x):.1f},{sy(y):.1f}')
            elif pts:
                segs.append(pts)
                pts = []
        if pts:
            segs.append(pts)
        col = BLUE if k == 0 else RED
        lines += ''.join(f'<polyline fill="none" stroke="{col}" stroke-width="2.4" points="{" ".join(s)}"/>' for s in segs if len(s) > 1)
    ax = ''
    if axes:
        ax = (f'<line x1="{sx(x0):.1f}" y1="{sy(0):.1f}" x2="{sx(x1):.1f}" y2="{sy(0):.1f}" stroke="{INK}" stroke-width="1.4" marker-end="url(#a)"/>'
              f'<line x1="{sx(0):.1f}" y1="{sy(y0):.1f}" x2="{sx(0):.1f}" y2="{sy(y1):.1f}" stroke="{INK}" stroke-width="1.4" marker-end="url(#a)"/>'
              f'<text x="{sx(x1) - 10:.1f}" y="{sy(0) - 6:.1f}">x</text><text x="{sx(0) + 6:.1f}" y="{sy(y1) + 10:.1f}">y</text>'
              f'<text x="{sx(1) - 3:.1f}" y="{sy(0) + 14:.1f}">1</text><text x="{sx(0) - 12:.1f}" y="{sy(1) + 4:.1f}">1</text>'
              f'<text x="{sx(0) - 12:.1f}" y="{sy(0) + 14:.1f}">0</text>')
    dots = ''.join(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="3.5" fill="{INK}"/>' for x, y in points)
    body = (f'<g stroke="{GRID}" stroke-width="1">{grid}</g>{ax}'
            f'<clipPath id="c"><rect x="{sx(x0):.1f}" y="{sy(y1):.1f}" width="{sx(x1) - sx(x0):.1f}" height="{sy(y0) - sy(y1):.1f}"/></clipPath>'
            f'<g clip-path="url(#c)">{lines}{dots}{extra(sx, sy) if extra else ""}</g>')
    return _svg(w, h, body)


def svg_cells(shapes, cols, rows, cell=24, labels=(), segs=(), dots=()):
    """Фигуры на клетчатой бумаге. shapes — список многоугольников [(x, y), …] в клетках
    (y вверх); segs — отрезки [((x1, y1), (x2, y2))]; dots — точки; labels — [(x, y, 'A')]."""
    w, h = cols * cell + 20, rows * cell + 20
    sx = lambda x: 10 + x * cell
    sy = lambda y: 10 + (rows - y) * cell
    grid = ''.join(f'<line x1="{sx(i)}" y1="{sy(0)}" x2="{sx(i)}" y2="{sy(rows)}"/>' for i in range(cols + 1))
    grid += ''.join(f'<line x1="{sx(0)}" y1="{sy(j)}" x2="{sx(cols)}" y2="{sy(j)}"/>' for j in range(rows + 1))
    poly_ = ''.join(f'<polygon points="{" ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in p)}" fill="{BLUE}" fill-opacity="0.12" stroke="{BLUE}" stroke-width="2.2"/>' for p in shapes)
    sg = ''.join(f'<line x1="{sx(a[0]):.1f}" y1="{sy(a[1]):.1f}" x2="{sx(b[0]):.1f}" y2="{sy(b[1]):.1f}" stroke="{RED}" stroke-width="2.2"/>' for a, b in segs)
    dt = ''.join(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="3.5" fill="{INK}"/>' for x, y in dots)
    lb = ''.join(f'<text x="{sx(x) + 4:.1f}" y="{sy(y) - 4:.1f}" font-size="13" font-style="italic">{t}</text>' for x, y, t in labels)
    return _svg(w, h, f'<g stroke="{GRID}" stroke-width="1">{grid}</g>{poly_}{sg}{dt}{lb}')


def svg_geom(points, polys=(), segs=(), circles=(), labels=None, marks=(), width=300, pad=24):
    """Чертёж планиметрии. points — {'A': (x, y), …} в любых единицах (y вверх);
    polys — ['ABC', …] многоугольники по именам; segs — ['AD', …] отрезки;
    circles — [((cx, cy), r)]; marks — [('B', 'A', 'C')] дуга угла BAC; подписи — имена точек."""
    xs = [p[0] for p in points.values()] + [c[0][0] - c[1] for c in circles] + [c[0][0] + c[1] for c in circles]
    ys = [p[1] for p in points.values()] + [c[0][1] - c[1] for c in circles] + [c[0][1] + c[1] for c in circles]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    k = (width - 2 * pad) / max(x1 - x0, y1 - y0, 1e-9)
    w, h = width, (y1 - y0) * k + 2 * pad
    w = (x1 - x0) * k + 2 * pad
    sx = lambda x: pad + (x - x0) * k
    sy = lambda y: pad + (y1 - y) * k
    P = {n: (sx(x), sy(y)) for n, (x, y) in points.items()}
    out = ''
    for c, rr in circles:
        out += f'<circle cx="{sx(c[0]):.1f}" cy="{sy(c[1]):.1f}" r="{rr * k:.1f}" fill="none" stroke="{INK}" stroke-width="1.6"/>'
    for pg in polys:
        out += f'<polygon points="{" ".join(f"{P[n][0]:.1f},{P[n][1]:.1f}" for n in pg)}" fill="none" stroke="{INK}" stroke-width="1.8"/>'
    for s in segs:
        a, b = P[s[0]], P[s[1]]
        out += f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{INK}" stroke-width="1.6"/>'
    for b_, a_, c_ in marks:
        A, B, C = P[a_], P[b_], P[c_]
        rr = 16
        u = [(B[0] - A[0]), (B[1] - A[1])]
        v = [(C[0] - A[0]), (C[1] - A[1])]
        nu, nv = math.hypot(*u) or 1, math.hypot(*v) or 1
        p1 = (A[0] + u[0] / nu * rr, A[1] + u[1] / nu * rr)
        p2 = (A[0] + v[0] / nv * rr, A[1] + v[1] / nv * rr)
        sweep = 1 if u[0] * v[1] - u[1] * v[0] > 0 else 0
        out += f'<path d="M{p1[0]:.1f} {p1[1]:.1f} A{rr} {rr} 0 0 {sweep} {p2[0]:.1f} {p2[1]:.1f}" fill="none" stroke="{RED}" stroke-width="1.6"/>'
    cx = sum(p[0] for p in P.values()) / max(1, len(P))
    cy = sum(p[1] for p in P.values()) / max(1, len(P))
    for n, (x, y) in P.items():
        if labels is not None and n not in labels:
            continue
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1
        tx, ty = x + dx / d * 12 - 4, y + dy / d * 12 + 4
        out += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="{INK}"/><text x="{tx:.1f}" y="{ty:.1f}" font-size="13" font-style="italic">{n}</text>'
    return _svg(w, h, out)


def svg_bars(values, labels, title='', width=360, height=220, line=False):
    """Столбчатая диаграмма (или ломаная при line=True) с сеткой по оси y."""
    vmax = max(values)
    vmin = min(0, min(values))
    step = next(s for s in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000, 10000) if (vmax - vmin) / s <= 10)
    top = math.ceil(vmax / step) * step
    bot = math.floor(vmin / step) * step
    L, B, T = 44, 28, 18 if not title else 30
    ph = height - B - T
    pw = width - L - 10
    sy = lambda v: T + (top - v) / (top - bot) * ph
    bw = pw / len(values)
    out = f'<text x="{width / 2:.0f}" y="16" text-anchor="middle">{title}</text>' if title else ''
    v = bot
    while v <= top:
        out += f'<line x1="{L}" y1="{sy(v):.1f}" x2="{width - 10}" y2="{sy(v):.1f}" stroke="{GRID}"/><text x="{L - 6}" y="{sy(v) + 4:.1f}" text-anchor="end">{tnum(v)}</text>'
        v += step
    pts = []
    for i, (val, lab) in enumerate(zip(values, labels)):
        x = L + i * bw
        if line:
            pts.append(f'{x + bw / 2:.1f},{sy(val):.1f}')
            out += f'<circle cx="{x + bw / 2:.1f}" cy="{sy(val):.1f}" r="3" fill="{BLUE}"/>'
        else:
            y0_, y1_ = sorted((sy(0), sy(val)))
            out += f'<rect x="{x + bw * 0.18:.1f}" y="{y0_:.1f}" width="{bw * 0.64:.1f}" height="{y1_ - y0_:.1f}" fill="{BLUE}"/>'
        out += f'<text x="{x + bw / 2:.1f}" y="{height - 10}" text-anchor="middle" font-size="11">{lab}</text>'
    if line:
        out += f'<polyline fill="none" stroke="{BLUE}" stroke-width="2.2" points="{" ".join(pts)}"/>'
    out += f'<line x1="{L}" y1="{sy(0):.1f}" x2="{width - 10}" y2="{sy(0):.1f}" stroke="{INK}"/>'
    return _svg(width, height, out)
