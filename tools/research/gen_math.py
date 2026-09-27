#!/usr/bin/env python3
"""Прототипы генераторов карточек по математике (исследование, в сайт не входит).

Запуск:
  python3 tools/research/gen_math.py            # самопроверка: по 200 вариантов на генератор
  python3 tools/research/gen_math.py --n 50     # другое число вариантов
  python3 tools/research/gen_math.py --sample   # по 2 примера карточек на генератор (JSON)
  python3 tools/research/gen_math.py --json out.json  # все карточки в файл
  python3 tools/research/gen_math.py --export data/research/math.json  # отчёт в машинном виде

Каждый генератор — функция gen_*(rng) → (card, check) или None (вариант отсеян).
card — карточка в формате packs/ege-math.json: {id, t, p, k, q, a, e, o?}.
check — независимая проверка ответа: функция без аргументов, которая заново
считает ответ другим путём (sympy / Fraction / перебор) и возвращает True/False.

Самопроверка для каждого генератора:
  • ответ пересчитан проверкой check() — sympy или точная арифметика;
  • ответ «приятный»: целое или конечная десятичная дробь, не длиннее 2 знаков
    после запятой (у вероятностей и мат. ожидания — до 4), модуль ≤ 10 000;
  • нет повторов условий; «ёмкость» — сколько разных условий нашлось за 4000 попыток.

Нужен sympy: pip install sympy.
"""
import argparse
import json
import random
import sys
from collections import Counter

from mathlib import *  # noqa: F401,F403 — помощники и реестры
from mathlib import EXAMS, pcard, F, GEN, TRIPLES, X, card, finite, gen, nice, num, par, poly, same, signed, sp, tnum, ftxt, lin, SUB  # noqa: F401

# ================================================================ ЕГЭ профиль

# ---------- 1. Планиметрия


@gen('p1_angles', 'ege-prof', 1, 'Углы треугольника', 'm-task-1')
def gen_p1_angles(r):
    kind = r.choice(['sum', 'isosceles', 'exterior', 'bisector'])
    if kind == 'sum':
        a, c = r.randint(20, 100), r.randint(20, 100)
        b = 180 - a - c
        if b < 10:
            return None
        q = f'В треугольнике ABC угол A равен {a}°, угол C равен {c}°. Найдите угол B. Ответ дайте в градусах.'
        e = f'B = 180° − {a}° − {c}° = {b}°.'
        return card('p1_angles', q, num(b), e), lambda: sp.Eq(sp.Integer(180) - a - c, b)
    if kind == 'isosceles':
        top = r.randrange(20, 160, 2)
        base = (180 - top) // 2
        q = f'В равнобедренном треугольнике ABC с основанием AC угол B равен {top}°. Найдите угол A. Ответ дайте в градусах.'
        e = f'Углы при основании равны: A = (180° − {top}°) : 2 = {base}°.'
        return card('p1_angles', q, num(base), e), lambda: 2 * base + top == 180
    if kind == 'exterior':
        a, b = r.randint(15, 80), r.randint(15, 80)
        ext = a + b
        q = (f'В треугольнике ABC угол A равен {a}°, угол B равен {b}°. Найдите внешний угол при вершине C. '
             'Ответ дайте в градусах.')
        e = f'Внешний угол равен сумме двух внутренних, не смежных с ним: {a}° + {b}° = {ext}°.'
        return card('p1_angles', q, num(ext), e), lambda: 180 - (180 - a - b) == ext
    a, c = r.randrange(20, 120, 2), r.randrange(20, 120, 2)
    if a + c >= 170:
        return None
    # AD — биссектриса угла A, найти угол ADC
    adc = 180 - a // 2 - c
    q = (f'В треугольнике ABC угол A равен {a}°, угол C равен {c}°, AD — биссектриса. '
         'Найдите угол ADC. Ответ дайте в градусах.')
    e = f'∠DAC = {a}° : 2 = {a // 2}°; ∠ADC = 180° − {a // 2}° − {c}° = {adc}°.'
    return card('p1_angles', q, num(adc), e), lambda: adc == 180 - sp.Rational(a, 2) - c


@gen('p1_right', 'ege-prof', 1, 'Прямоугольный треугольник: Пифагор и синус', 'm-task-1')
def gen_p1_right(r):
    p, q_, h = r.choice(TRIPLES)
    if r.random() < 0.5:
        p, q_ = q_, p
    k = r.randint(1, max(1, 120 // h))
    a, b, c = p * k, q_ * k, h * k  # BC = a, AC = b, AB = c
    kind = r.choice(['hyp', 'leg', 'sin', 'cos', 'tg'])
    if kind == 'hyp':
        q = f'В треугольнике ABC угол C равен 90°, AC = {b}, BC = {a}. Найдите AB.'
        e = f'AB = √({b}² + {a}²) = √{b * b + a * a} = {c}.'
        return card('p1_right', q, num(c), e), lambda: sp.sqrt(a**2 + b**2) == c
    if kind == 'leg':
        q = f'В треугольнике ABC угол C равен 90°, AB = {c}, AC = {b}. Найдите BC.'
        e = f'BC = √({c}² − {b}²) = √{c * c - b * b} = {a}.'
        return card('p1_right', q, num(a), e), lambda: sp.sqrt(c**2 - b**2) == a
    ratio, given, want, wv = {'sin': (F(a, c), c, 'BC', a), 'cos': (F(b, c), c, 'AC', b), 'tg': (F(a, b), b, 'BC', a)}[kind]
    rt = tnum(ratio) if finite(ratio) else f'{ratio.numerator}/{ratio.denominator}'
    gname = 'AB' if kind in ('sin', 'cos') else 'AC'
    q = f'В треугольнике ABC угол C равен 90°, {gname} = {given}, {kind} A = {rt}. Найдите {want}.'
    e = f'{kind} A = {want} / {gname}, значит {want} = {given} · {rt} = {wv}.'
    return card('p1_right', q, num(wv), e), lambda: sp.Rational(ratio.numerator, ratio.denominator) * given == wv


@gen('p1_inscribed', 'ege-prof', 1, 'Вписанный и центральный угол', 'm-task-1')
def gen_p1_inscribed(r):
    if r.random() < 0.5:
        central = r.randrange(20, 340, 2)
        q = (f'Центральный угол AOB окружности равен {central}°. Найдите вписанный угол ACB, опирающийся на ту же дугу AB. '
             'Ответ дайте в градусах.')
        e = f'Вписанный угол равен половине дуги: {central}° : 2 = {central // 2}°.'
        return card('p1_inscribed', q, num(central // 2), e), lambda: sp.Rational(central, 2) == central // 2
    a = r.randint(10, 170)
    q = (f'Четырёхугольник ABCD вписан в окружность. Угол ABC равен {a}°. Найдите угол ADC. Ответ дайте в градусах.')
    e = f'Сумма противоположных углов вписанного четырёхугольника 180°: {180 - a}°.'
    return card('p1_inscribed', q, num(180 - a), e), lambda: a + (180 - a) == 180


@gen('p1_trapezoid', 'ege-prof', 1, 'Трапеция: площадь и средняя линия', 'm-task-1')
def gen_p1_trapezoid(r):
    a, b = r.randint(2, 30), r.randint(2, 30)
    if a == b:
        return None
    a, b = max(a, b), min(a, b)
    if r.random() < 0.5:
        h = r.randint(2, 20)
        s = F(a + b, 2) * h
        if not nice(s, 1):
            return None
        q = f'Основания трапеции равны {a} и {b}, высота равна {h}. Найдите площадь трапеции.'
        e = f'S = ({a} + {b}) / 2 · {h} = {tnum(s)}.'
        return card('p1_trapezoid', q, num(s), e), lambda: sp.Rational(a + b, 2) * h == sp.Rational(s.numerator, s.denominator)
    m = F(a + b, 2)
    q = f'Основания трапеции равны {a} и {b}. Найдите её среднюю линию.'
    e = f'Средняя линия — полусумма оснований: ({a} + {b}) / 2 = {tnum(m)}.'
    return card('p1_trapezoid', q, num(m), e), lambda: 2 * sp.Rational(m.numerator, m.denominator) == a + b


@gen('p1_tangent_quad', 'ege-prof', 1, 'Описанный четырёхугольник', 'm-task-1')
def gen_p1_tangent_quad(r):
    ab, bc, cd = r.randint(3, 40), r.randint(3, 40), r.randint(3, 40)
    ad = ab + cd - bc
    if ad < 3:
        return None
    q = f'Четырёхугольник ABCD описан около окружности, AB = {ab}, BC = {bc}, CD = {cd}. Найдите AD.'
    e = f'У описанного четырёхугольника AB + CD = BC + AD, поэтому AD = {ab} + {cd} − {bc} = {ad}.'
    return card('p1_tangent_quad', q, num(ad), e), lambda: ab + cd == bc + ad


# ---------- 2. Векторы


@gen('p2_vectors', 'ege-prof', 2, 'Векторы: координаты, длина, скалярное произведение', 'm-task-2')
def gen_p2_vectors(r):
    kind = r.choice(['dot', 'len', 'comb'])
    a = (r.randint(-9, 9), r.randint(-9, 9))
    b = (r.randint(-9, 9), r.randint(-9, 9))
    if a == (0, 0) or b == (0, 0) or a == b:
        return None
    va, vb = sp.Matrix(a), sp.Matrix(b)
    vec = lambda v: f'({tnum(v[0])}; {tnum(v[1])})'
    if kind == 'dot':
        d = a[0] * b[0] + a[1] * b[1]
        q = f'Даны векторы a⃗{vec(a)} и b⃗{vec(b)}. Найдите скалярное произведение a⃗ · b⃗.'
        e = f'a⃗ · b⃗ = {tnum(a[0])}·{tnum(b[0])} + {tnum(a[1])}·{tnum(b[1])} = {tnum(d)}.'
        return card('p2_vectors', q, num(d), e), lambda: va.dot(vb) == d
    if kind == 'len':
        p, q_, h = r.choice(TRIPLES[:4])
        k = r.randint(1, 3)
        s = (p * k * r.choice([1, -1]), q_ * k * r.choice([1, -1]))
        b = (s[0] - a[0], s[1] - a[1])
        if b == (0, 0):
            return None
        q = f'Даны векторы a⃗{vec(a)} и b⃗{vec(b)}. Найдите длину вектора a⃗ + b⃗.'
        e = f'a⃗ + b⃗ = {vec(s)}, |a⃗ + b⃗| = √({tnum(s[0])}² + {tnum(s[1])}²) = {h * k}.'
        return card('p2_vectors', q, num(h * k), e), lambda: (sp.Matrix(a) + sp.Matrix(b)).norm() == h * k
    m, n = r.choice([2, 3, 4, -2, -3]), r.choice([2, 3, -1, -2, -4])
    coord = r.choice([0, 1])
    v = m * a[coord] + n * b[coord]
    name = 'абсциссу' if coord == 0 else 'ординату'
    comb = f'{m}a⃗' + (f' + {n}b⃗' if n > 0 else f' − {-n}b⃗')
    comb = comb.replace('-', '−')
    q = f'Даны векторы a⃗{vec(a)} и b⃗{vec(b)}. Найдите {name} вектора {comb}.'
    e = f'{par(m)}·{par(a[coord])} + {par(n)}·{par(b[coord])} = {tnum(v)}.'
    return card('p2_vectors', q, num(v), e), lambda: (m * va + n * vb)[coord] == v


# ---------- 3. Стереометрия


@gen('p3_volume', 'ege-prof', 3, 'Объёмы: подобие, переливание, призма и цилиндр', 'm-task-3')
def gen_p3_volume(r):
    kind = r.choice(['pour', 'cone_cut', 'box', 'scale'])
    if kind == 'pour':
        k = r.choice([2, 3, 4, 5])
        h2 = r.randint(1, 12)
        h1 = h2 * k * k
        q = (f'В цилиндрическом сосуде уровень жидкости достигает {h1} см. На какой высоте будет уровень жидкости, '
             f'если её перелить во второй цилиндрический сосуд, диаметр которого в {k} {"раз" if k >= 5 else "раза"} больше диаметра первого? '
             'Ответ дайте в сантиметрах.')
        e = f'Объём тот же, площадь дна больше в {k}² = {k * k} раз, значит высота меньше в {k * k} раз: {h1} : {k * k} = {h2}.'
        return card('p3_volume', q, num(h2), e), lambda: sp.pi * 1**2 * h1 == sp.pi * k**2 * h2
    if kind == 'cone_cut':
        k = r.choice([2, 3, 4, 5])
        v_small = r.randint(1, 15)
        V = v_small * k**3
        q = (f'Объём конуса равен {V}. Через точку, делящую высоту конуса в отношении 1 : {k - 1}, считая от вершины, '
             'проведена плоскость, параллельная основанию. Найдите объём конуса, отсекаемого от данного конуса этой плоскостью.')
        e = f'Малый конус подобен большому с коэффициентом 1/{k}, объёмы относятся как 1 : {k}³: {V} : {k**3} = {v_small}.'
        return card('p3_volume', q, num(v_small), e), lambda: sp.Rational(V, k**3) == v_small
    if kind == 'box':
        a, b, c = r.randint(1, 12), r.randint(1, 12), r.randint(1, 12)
        s = 2 * (a * b + b * c + a * c)
        if r.random() < 0.5:
            q = f'Найдите объём прямоугольного параллелепипеда с рёбрами {a}, {b} и {c}.'
            return card('p3_volume', q, num(a * b * c), f'V = {a}·{b}·{c} = {a * b * c}.'), lambda: sp.prod([a, b, c]) == a * b * c
        q = f'Найдите площадь поверхности прямоугольного параллелепипеда с рёбрами {a}, {b} и {c}.'
        e = f'S = 2({a}·{b} + {b}·{c} + {a}·{c}) = {s}.'
        return card('p3_volume', q, num(s), e), lambda: 2 * sum(x * y for x, y in [(a, b), (b, c), (a, c)]) == s
    k = r.choice([2, 3, 4])
    body = r.choice([('куба', 'рёбра'), ('шара', 'радиус'), ('правильного тетраэдра', 'рёбра')])
    what = r.choice(['объём', 'площадь поверхности'])
    ans = k**3 if what == 'объём' else k**2
    q = f'Во сколько раз увеличится {what} {body[0]}, если {body[1]} увеличить в {k} раза?'
    e = f'При подобии с коэффициентом {k} площади растут в {k}², объёмы — в {k}³ раз: {ans}.'
    return card('p3_volume', q, num(ans), e), lambda: ans == (k**3 if what == 'объём' else k**2)


# ---------- 4. Простая вероятность

P4_CTX = [
    ('В сборнике билетов по биологии {n} билетов, в {m} из них встречается вопрос о грибах. '
     'На экзамене школьнику достаётся один случайно выбранный билет. Найдите вероятность того, что в этом билете будет вопрос о грибах.'),
    ('В фирме такси в наличии {n} легковых автомобилей: {m} из них жёлтые, остальные — другого цвета. '
     'По вызову выехала одна случайная машина. Найдите вероятность того, что к заказчику приедет жёлтое такси.'),
    ('На конференцию приехали {n} докладчиков, из них {m} — из Казани. Порядок докладов определяется жеребьёвкой. '
     'Найдите вероятность того, что первым будет выступать докладчик из Казани.'),
    ('В коробке {n} одинаковых на ощупь шаров, {m} из них красные. Наугад достают один шар. '
     'Найдите вероятность того, что он красный.'),
]


@gen('p4_classic', 'ege-prof', 4, 'Классическая вероятность', 'm-task-4', maxdec=4)
def gen_p4_classic(r):
    n = r.choice([4, 5, 8, 10, 16, 20, 25, 40, 50, 80, 100, 125, 200, 250, 400, 500, 1000])
    m = r.randint(1, n - 1)
    p = F(m, n)
    if not nice(p, 3):
        return None
    tpl = r.randrange(len(P4_CTX))
    other = r.random() < 0.3
    if other:
        p = 1 - p
        q = P4_CTX[tpl].format(n=n, m=m).replace('будет вопрос о грибах', 'не будет вопроса о грибах') \
            .replace('приедет жёлтое такси', 'приедет не жёлтое такси') \
            .replace('докладчик из Казани', 'докладчик не из Казани').replace('он красный', 'он не красный')
        e = f'P = ({n} − {m}) / {n} = {tnum(p)}.'
    else:
        q = P4_CTX[tpl].format(n=n, m=m)
        e = f'P = {m} / {n} = {tnum(p)}.'
    return card('p4_classic', q, num(p), e), lambda: sp.Rational(n - m if other else m, n) == sp.Rational(p.numerator, p.denominator)


# ---------- 5. Вероятность: сложение и умножение, полная вероятность


@gen('p5_prob', 'ege-prof', 5, 'Независимые события, противоположное событие, полная вероятность', 'm-task-5', maxdec=4)
def gen_p5_prob(r):
    kind = r.choice(['shooter', 'two', 'total'])
    if kind == 'shooter':
        p = F(r.choice([6, 7, 8, 9]), 10)
        n = r.randint(3, 5)
        k = r.randint(1, n - 1)
        ans = p**k * (1 - p)**(n - k)
        if not nice(ans, 4):
            return None
        q = (f'Биатлонист {n} раз стреляет по мишеням. Вероятность попадания при одном выстреле равна {tnum(p)}. '
             f'Найдите вероятность того, что биатлонист первые {k} раз попал в мишени, а последние {n - k} промахнулся. '
             'Результат округлите до сотых.')
        ans_r = F(round(ans * 100), 100) if ans * 100 % 1 != F(1, 2) else None
        if ans_r is None:
            return None
        e = f'P = {tnum(p)}^{k} · {tnum(1 - p)}^{n - k} = {tnum(ans)} ≈ {tnum(ans_r)}.'
        exact = sp.Rational(p.numerator, p.denominator)
        return card('p5_prob', q, num(ans_r), e), lambda: abs(exact**k * (1 - exact)**(n - k) - sp.Rational(ans_r.numerator, ans_r.denominator)) <= sp.Rational(1, 200)
    if kind == 'two':
        p = F(r.randint(1, 19), 20)
        q_ = F(r.randint(1, 19), 20)
        ask = r.choice(['оба', 'хотя бы один', 'ровно один'])
        ans = {'оба': p * q_, 'хотя бы один': 1 - (1 - p) * (1 - q_), 'ровно один': p * (1 - q_) + q_ * (1 - p)}[ask]
        if not nice(ans, 4):
            return None
        verb = {'оба': 'оба автомата исправны', 'хотя бы один': 'хотя бы один автомат исправен',
                'ровно один': 'исправен ровно один автомат'}[ask]
        q = (f'В торговом центре два одинаковых кофейных автомата. Вероятность того, что к концу дня первый автомат исправен, '
             f'равна {tnum(p)}, второй — {tnum(q_)}. Автоматы ломаются независимо. Найдите вероятность того, что к концу дня {verb}.')
        e = {'оба': f'P = {tnum(p)} · {tnum(q_)} = {tnum(ans)}.',
             'хотя бы один': f'P = 1 − (1 − {tnum(p)})(1 − {tnum(q_)}) = {tnum(ans)}.',
             'ровно один': f'P = {tnum(p)}·{tnum(1 - q_)} + {tnum(1 - p)}·{tnum(q_)} = {tnum(ans)}.'}[ask]

        def chk():
            a, b = sp.Rational(p.numerator, p.denominator), sp.Rational(q_.numerator, q_.denominator)
            # перебор четырёх исходов
            outs = {(1, 1): a * b, (1, 0): a * (1 - b), (0, 1): (1 - a) * b, (0, 0): (1 - a) * (1 - b)}
            cond = {'оба': lambda s: s == 2, 'хотя бы один': lambda s: s >= 1, 'ровно один': lambda s: s == 1}[ask]
            return sum(v for o, v in outs.items() if cond(sum(o))) == sp.Rational(ans.numerator, ans.denominator)
        return card('p5_prob', q, num(ans), e), chk
    s1 = r.randrange(10, 91, 10)
    d1, d2 = F(r.randint(1, 9), 100), F(r.randint(1, 9), 100)
    w1 = F(s1, 100)
    ans = w1 * d1 + (1 - w1) * d2
    if not nice(ans, 4):
        return None
    q = (f'Две фабрики выпускают одинаковые стёкла для фар. Первая фабрика выпускает {s1}% этих стёкол, вторая — {100 - s1}%. '
         f'Первая фабрика выпускает {tnum(d1 * 100)}% бракованных стёкол, а вторая — {tnum(d2 * 100)}%. '
         'Найдите вероятность того, что случайно купленное в магазине стекло окажется бракованным.')
    e = f'P = {tnum(w1)}·{tnum(d1)} + {tnum(1 - w1)}·{tnum(d2)} = {tnum(ans)}.'
    return card('p5_prob', q, num(ans), e), lambda: sp.Rational(s1, 100) * sp.Rational(d1.numerator, d1.denominator) + sp.Rational(100 - s1, 100) * sp.Rational(d2.numerator, d2.denominator) == sp.Rational(ans.numerator, ans.denominator)


# ---------- 6. Простейшие уравнения


def solve_check(expr_l, expr_r, ans, pick=None):
    """Проверка: sympy решает уравнение сам; pick — 'min'/'max', если корней несколько."""
    def chk():
        sol = [s for s in sp.solve(sp.Eq(expr_l, expr_r), X) if s.is_real]
        if not sol:
            return False
        v = min(sol) if pick == 'min' else max(sol) if pick == 'max' else (sol[0] if len(sol) == 1 else None)
        return v is not None and same(ans, v)
    return chk


@gen('p6_eq', 'ege-prof', 6, 'Простейшие уравнения: показательные, логарифмические, иррациональные, квадратные', 'm-task-6')
def gen_p6_eq(r):
    kind = r.choice(['exp', 'log', 'sqrt', 'quad', 'frac'])
    if kind == 'exp':
        base = r.choice([2, 3, 5, 7])
        a = r.choice([1, 2, 3, -1, -2])
        root = F(r.randint(-6, 8), r.choice([1, 1, 2]))
        b_ = r.randint(-5, 5)
        c = a * root + b_
        if c.denominator != 1 or not -4 <= c <= 6 or root == 0:
            return None
        rhs = F(base) ** int(c)
        rhs_s = tnum(rhs) if rhs.denominator == 1 else f'1/{rhs.denominator}'
        q = f'Решите уравнение {base}^({lin(a, b_)}) = {rhs_s}.'
        e = f'{rhs_s} = {base}^({tnum(c)}), значит {lin(a, b_)} = {tnum(c)}, x = {tnum(root)}.'
        return card('p6_eq', q, num(root), e), solve_check(sp.Integer(base) ** (a * X + b_), sp.Rational(rhs.numerator, rhs.denominator), num(root))
    if kind == 'log':
        base = r.choice([2, 3, 4, 5, 7])
        c = r.randint(0, 3 if base < 5 else 2)
        a = r.choice([1, 1, 2, 3, -1])
        b_ = r.randint(-9, 9)
        root = F(base**c - b_, a)
        if not nice(root, 1) or base**c - b_ == 0:
            return None
        q = f'Решите уравнение log{str(base).translate(SUB)}({lin(a, b_)}) = {c}.'
        e = f'{lin(a, b_)} = {base}^{c} = {base**c}, x = {tnum(root)}.'
        return card('p6_eq', q, num(root), e), solve_check(sp.log(a * X + b_, base), sp.Integer(c), num(root))
    if kind == 'sqrt':
        c = r.randint(1, 12)
        a = r.choice([1, 2, 3, 4, 5, -1, -2])
        b_ = r.randint(-20, 20)
        root = F(c * c - b_, a)
        if not nice(root, 1):
            return None
        q = f'Решите уравнение √({lin(a, b_)}) = {c}.'
        e = f'Обе части неотрицательны, возводим в квадрат: {lin(a, b_)} = {c * c}, x = {tnum(root)}.'
        return card('p6_eq', q, num(root), e), solve_check(sp.sqrt(a * X + b_), sp.Integer(c), num(root))
    if kind == 'quad':
        x1, x2 = r.randint(-12, 12), r.randint(-12, 12)
        if x1 == x2:
            return None
        pick = r.choice(['min', 'max'])
        v = min(x1, x2) if pick == 'min' else max(x1, x2)
        word = 'меньший' if pick == 'min' else 'больший'
        q = f'Решите уравнение {poly([1, -(x1 + x2), x1 * x2])} = 0. Если уравнение имеет более одного корня, в ответе запишите {word} из корней.'
        e = f'По теореме Виета корни {tnum(min(x1, x2))} и {tnum(max(x1, x2))}; {word} — {tnum(v)}.'
        return card('p6_eq', q, num(v), e), solve_check(X**2 - (x1 + x2) * X + x1 * x2, 0, num(v), pick)
    k = r.randint(2, 30)
    root = F(r.randint(-15, 15), r.choice([1, 2]))
    b_ = r.randint(-9, 9)
    rhs = F(k) / (root + b_) if root + b_ else None
    if rhs is None or not nice(rhs, 1) or rhs == 0:
        return None
    q = f'Решите уравнение {k} / ({lin(1, b_)}) = {tnum(rhs)}.'
    e = f'x + {b_} = {k} / {tnum(rhs)} = {tnum(root + b_)}, x = {tnum(root)}.'.replace('+ -', '− ')
    return card('p6_eq', q, num(root), e), solve_check(sp.Integer(k) / (X + b_), sp.Rational(rhs.numerator, rhs.denominator), num(root))


# ---------- 7. Вычисления и преобразования


@gen('p7_expr', 'ege-prof', 7, 'Значения выражений: степени, корни, логарифмы, тригонометрия', 'm-task-7')
def gen_p7_expr(r):
    kind = r.choice(['pow', 'root', 'log', 'trig'])
    if kind == 'pow':
        a = r.choice([2, 3, 5, 7, 10])
        m, n = r.randint(-5, 9), r.randint(-5, 9)
        k = m + n - r.randint(0, 3)
        val = F(a) ** (m + n - k)
        pw = lambda e_: f'{a}^{e_}' if e_ >= 0 else f'{a}^({tnum(e_)})'
        q = f'Найдите значение выражения {pw(m)} · {pw(n)} : {pw(k)}.'
        e = f'{a}^({m} + {n} − {k}) = {a}^{m + n - k} = {tnum(val)}.'.replace('+ -', '− ').replace('− -', '+ ')
        return card('p7_expr', q, num(val), e), lambda: sp.Integer(a)**m * sp.Integer(a)**n / sp.Integer(a)**k == val
    if kind == 'root':
        a = r.choice([2, 3, 5, 6, 7, 10, 11])
        # √(a·t²) · √(a·u²) / c
        t, u = r.randint(1, 5), r.randint(1, 5)
        c = r.choice([1, 2, 3, 4, 5, 6])
        val = F(a * t * u, c)
        if not nice(val, 1):
            return None
        q = f'Найдите значение выражения √{a * t * t} · √{a * u * u} / {c}.' if c > 1 else f'Найдите значение выражения √{a * t * t} · √{a * u * u}.'
        e = f'√({a * t * t}·{a * u * u}) = √{a * a * t * t * u * u} = {a * t * u}' + (f'; {a * t * u} / {c} = {tnum(val)}.' if c > 1 else '.')
        return card('p7_expr', q, num(val), e), lambda: sp.sqrt(a * t * t) * sp.sqrt(a * u * u) / c == sp.Rational(val.numerator, val.denominator)
    if kind == 'log':
        base = r.choice([2, 3, 5, 6])
        k = r.randint(1, 4)
        m = r.choice([d for d in range(2, 60) if (base**k) % d == 0 or True])
        n = F(base**k, m)
        if n.denominator != 1 or m in (1, base**k):
            return None
        c = r.choice([1, 2, 3])
        q = f'Найдите значение выражения {"" if c == 1 else c}log{str(base).translate(SUB)}{m} + {"" if c == 1 else c}log{str(base).translate(SUB)}{n.numerator}.'
        val = c * k
        e = f'{"" if c == 1 else f"{c}·"}log{str(base).translate(SUB)}({m}·{n.numerator}) = {"" if c == 1 else f"{c}·"}log{str(base).translate(SUB)}{base**k} = {val}.'
        return card('p7_expr', q, num(val), e), lambda: sp.simplify(c * sp.log(m, base) + c * sp.log(n.numerator, base) - val) == 0
    p, q_, h = r.choice(TRIPLES[:4])
    quarter = r.choice([1, 2, 3, 4])
    given, want = r.choice([('cos', 'sin'), ('sin', 'cos')])
    # cos α = ±p/h, sin α = ±q/h в нужной четверти
    sgn = {1: (1, 1), 2: (-1, 1), 3: (-1, -1), 4: (1, -1)}[quarter]
    cosv, sinv = F(sgn[0] * p, h), F(sgn[1] * q_, h)
    gv, wv = (cosv, sinv) if given == 'cos' else (sinv, cosv)
    rng = {1: '(0; π/2)', 2: '(π/2; π)', 3: '(π; 3π/2)', 4: '(3π/2; 2π)'}[quarter]
    val = h * wv
    gtxt = f'{"−" if gv < 0 else ""}{abs(gv.numerator)}/{gv.denominator}'
    q = f'Найдите {h}{want} α, если {given} α = {gtxt} и α ∈ {rng}.'
    e = f'{want} α = ±√(1 − {given}²α) = {tnum(wv.numerator)}/{wv.denominator} (знак — по четверти); {h}·{want} α = {tnum(val)}.'

    def chk():
        alpha = sp.atan2(sinv.numerator * cosv.denominator, cosv.numerator * sinv.denominator)
        lo = {1: 0, 2: sp.pi / 2, 3: sp.pi, 4: 3 * sp.pi / 2}[quarter]
        alpha = alpha % (2 * sp.pi)
        ok_q = lo < alpha < lo + sp.pi / 2
        fn = sp.sin if want == 'sin' else sp.cos
        return ok_q and sp.simplify(h * fn(alpha) - val) == 0
    return card('p7_expr', q, num(val), e), chk


# ---------- 8. Производная (без рисунка)


@gen('p8_deriv', 'ege-prof', 8, 'Производная: физический смысл, касательная параллельна прямой', 'm-task-8')
def gen_p8_deriv(r):
    t = sp.Symbol('t')
    if r.random() < 0.5:
        a, b, c, d = r.choice([F(1, 2), F(1, 3), 1, 2]), r.randint(-6, 6), r.randint(-9, 9), r.randint(-20, 20)
        # x(t) = a t³ + b t² + c t + d, найти скорость в момент t0
        t0 = r.randint(1, 8)
        a_ = sp.Rational(a.numerator, a.denominator)
        v = 3 * a * t0**2 + 2 * b * t0 + c
        if not nice(v) or abs(v) > 500:
            return None
        terms = poly([a, b, c, d], 't')
        q = (f'Материальная точка движется прямолинейно по закону x(t) = {terms}, где x — расстояние от точки отсчёта в метрах, '
             f't — время в секундах. Найдите её скорость (в м/с) в момент времени t = {t0} с.')
        e = f'v(t) = x′(t) = {poly([3 * a, 2 * b, c], "t")}; v({t0}) = {tnum(v)}.'
        return card('p8_deriv', q, num(v), e), lambda: sp.diff(a_ * t**3 + b * t**2 + c * t + d, t).subs(t, t0) == v
    a, b, c = r.choice([1, 2, 3, -1, -2]), r.randint(-9, 9), r.randint(-9, 9)
    x0 = F(r.randint(-8, 8), r.choice([1, 2]))
    k = 2 * a * x0 + b
    m = r.randint(-9, 9)
    if k.denominator != 1 or k == 0:
        return None
    q = (f'Прямая y = {lin(k, m)} параллельна касательной к графику функции y = {poly([a, b, c])}. '
         'Найдите абсциссу точки касания.')
    e = f'y′ = {lin(2 * a, b)} = {tnum(k)}, x₀ = {tnum(x0)}.'
    return card('p8_deriv', q, num(x0), e), solve_check(sp.diff(a * X**2 + b * X + c, X), sp.Integer(int(k)), num(x0))


# ---------- 9. Вычисления по формуле


@gen('p9_formula', 'ege-prof', 9, 'Задачи с прикладным содержанием (формула)', 'm-task-9')
def gen_p9_formula(r):
    if r.random() < 0.5:
        # h(t) = v0 t − 5 t²; сколько секунд мяч находится на высоте не менее H
        t1, t2 = sorted(r.sample([F(i, 10) for i in range(2, 41, 2)], 2))
        # h = 5(t − 0)(…): v0 t − 5 t² = H при t1, t2 → t1 + t2 = v0/5, t1 t2 = H/5
        v0, H = 5 * (t1 + t2), 5 * t1 * t2
        if not (nice(v0, 1) and nice(H, 2)):
            return None
        ans = t2 - t1
        q = (f'Мяч бросили вертикально вверх. Пока мяч не упал, высота, на которой он находится, описывается формулой '
             f'h(t) = {tnum(v0)}t − 5t², где h — высота в метрах, t — время в секундах. '
             f'Сколько секунд мяч находился на высоте не менее {tnum(H)} метров?')
        e = f'{tnum(v0)}t − 5t² ≥ {tnum(H)} ⇔ t ∈ [{tnum(t1)}; {tnum(t2)}], длина промежутка {tnum(ans)} с.'

        def chk():
            tt = sp.Symbol('t', real=True)
            sol = sp.solve(sp.Eq(sp.Rational(v0.numerator, v0.denominator) * tt - 5 * tt**2, sp.Rational(H.numerator, H.denominator)), tt)
            return len(sol) == 2 and same(num(ans), max(sol) - min(sol))
        return card('p9_formula', q, num(ans), e), chk
    # I = U / (R + r): при каком наименьшем R сила тока не превысит I_max
    U = r.randrange(10, 250, 10)
    rr = F(r.randint(1, 20), 2)
    Imax = F(r.randint(1, 40), 4)
    R = F(U) / Imax - rr
    if R <= 0 or not nice(R, 1) or not nice(Imax, 2):
        return None
    q = (f'Сила тока в цепи (в амперах) вычисляется по формуле I = ε / (R + r), где ε = {U} В — ЭДС источника, '
         f'r = {tnum(rr)} Ом — его внутреннее сопротивление, R — сопротивление цепи (в омах). При каком наименьшем R '
         f'сила тока будет не больше {tnum(Imax)} А? Ответ дайте в омах.')
    e = f'{U} / (R + {tnum(rr)}) ≤ {tnum(Imax)} ⇔ R ≥ {U} / {tnum(Imax)} − {tnum(rr)} = {tnum(R)}.'
    Rs = sp.Symbol('R', positive=True)
    return card('p9_formula', q, num(R), e), lambda: same(num(R), sp.solve(sp.Eq(U / (Rs + sp.Rational(rr.numerator, rr.denominator)), sp.Rational(Imax.numerator, Imax.denominator)), Rs)[0])


# ---------- 10. Текстовые задачи


@gen('p10_text', 'ege-prof', 10, 'Текстовые задачи: движение по реке, работа, смеси, проценты', 'm-task-10')
def gen_p10_text(r):
    kind = r.choice(['river', 'work', 'mix', 'percent'])
    v = sp.Symbol('v', positive=True)
    if kind == 'river':
        vb, u = r.randint(8, 30), r.randint(1, 5)
        if u >= vb:
            return None
        d = r.randint(20, 300)
        t_total = F(d, vb + u) + F(d, vb - u)
        stay = r.randint(0, 6)
        T = t_total + stay
        if T.denominator != 1 or T > 60:
            return None
        q = (f'Теплоход проходит по течению реки до пункта назначения {d} км и после стоянки возвращается в пункт отправления. '
             f'Найдите скорость теплохода в неподвижной воде, если скорость течения равна {u} км/ч, стоянка длится {stay} ч, '
             f'а в пункт отправления теплоход возвращается через {T} ч после отплытия. Ответ дайте в км/ч.')
        e = f'{d}/(v + {u}) + {d}/(v − {u}) + {stay} = {T} ⇒ v = {vb}.'

        def chk():
            sol = [s for s in sp.solve(sp.Eq(d / (v + u) + d / (v - u) + stay, T), v) if s.is_real and s > u]
            return len(sol) == 1 and sol[0] == vb
        return card('p10_text', q, num(vb), e), chk
    if kind == 'work':
        a, b = r.randint(2, 40), r.randint(2, 40)
        if a == b:
            return None
        tt = F(a * b, a + b)
        if not nice(tt, 1):
            return None
        if r.random() < 0.5:
            q = (f'Одна труба наполняет бассейн за {a} ч, а другая — за {b} ч. За сколько часов наполнят бассейн обе трубы, '
                 'работая одновременно?')
            e = f'Производительности 1/{a} и 1/{b}; вместе 1/{a} + 1/{b} = {a + b}/{a * b}, время {tnum(tt)} ч.'
            return card('p10_text', q, num(tt), e), lambda: same(num(tt), 1 / (sp.Rational(1, a) + sp.Rational(1, b)))
        q = (f'Двое рабочих, работая вместе, выполняют заказ за {tnum(tt)} ч. Первый рабочий, работая один, выполняет этот заказ '
             f'за {a} ч. За сколько часов выполнит этот заказ второй рабочий, работая один?')
        e = f'1/x = 1/{tnum(tt)} − 1/{a} ⇒ x = {b}.'

        def chk2():
            sol = sp.solve(sp.Eq(1 / v, 1 / sp.Rational(tt.numerator, tt.denominator) - sp.Rational(1, a)), v)
            return len(sol) == 1 and sol[0] == b
        return card('p10_text', q, num(b), e), chk2
    if kind == 'mix':
        m1, m2 = r.randint(1, 20), r.randint(1, 20)
        p1, p2 = r.randint(5, 60), r.randint(5, 60)
        if p1 == p2:
            return None
        c = F(m1 * p1 + m2 * p2, m1 + m2)
        if not nice(c, 1):
            return None
        q = (f'Смешали {m1} литров {p1}-процентного водного раствора некоторого вещества с {m2} литрами {p2}-процентного '
             'раствора этого же вещества. Сколько процентов составляет концентрация получившегося раствора?')
        e = f'Вещества {m1}·{p1}% + {m2}·{p2}% = {tnum(F(m1 * p1 + m2 * p2, 100))} л на {m1 + m2} л раствора: {tnum(c)}%.'
        return card('p10_text', q, num(c), e), lambda: same(num(c), sp.Rational(m1 * p1 + m2 * p2, m1 + m2))
    p0 = r.randrange(100, 5001, 50)
    up, down = r.choice([5, 10, 15, 20, 25, 30, 40, 50]), r.choice([5, 10, 15, 20, 25, 30, 40, 50])
    final = F(p0) * (100 + up) / 100 * (100 - down) / 100
    if not nice(final, 2):
        return None
    q = (f'Цена товара составляла {p0} рублей. Сначала её повысили на {up}%, а затем снизили на {down}%. '
         'Сколько рублей стал стоить товар?')
    e = f'{p0} · {tnum(F(100 + up, 100))} · {tnum(F(100 - down, 100))} = {tnum(final)}.'
    return card('p10_text', q, num(final), e), lambda: sp.Integer(p0) * sp.Rational(100 + up, 100) * sp.Rational(100 - down, 100) == sp.Rational(final.numerator, final.denominator)


# ---------- 11. Графики функций (текстовый вариант; для КИМ-формата нужен рисунок)


@gen('p11_graph', 'ege-prof', 11, 'Функция по точкам графика (текстовый вариант)', 'm-task-11')
def gen_p11_graph(r):
    if r.random() < 0.5:
        a, b, c = r.choice([1, -1, 2, -2, F(1, 2), F(-1, 2)]), r.randint(-6, 6), r.randint(-8, 8)
        f = lambda x: a * x * x + b * x + c
        xs = r.sample(range(-4, 5), 3)
        x0 = r.randint(5, 10) * r.choice([1, -1])
        val = f(x0)
        if not nice(val, 1) or any(F(f(x)).denominator != 1 for x in xs):
            return None
        pts = ', '.join(f'({tnum(x)}; {tnum(f(x))})' for x in xs)
        q = f'График функции f(x) = ax² + bx + c проходит через точки {pts}. Найдите f({tnum(x0)}).'
        e = f'Из системы a = {tnum(a)}, b = {tnum(b)}, c = {tnum(c)}; f({tnum(x0)}) = {tnum(val)}.'

        def chk():
            A, B, C = sp.symbols('A B C')
            s = sp.solve([sp.Eq(A * x**2 + B * x + C, sp.Rational(F(f(x)).numerator, F(f(x)).denominator)) for x in xs], [A, B, C])
            return same(num(val), s[A] * x0**2 + s[B] * x0 + s[C])
        return card('p11_graph', q, num(val), e), chk
    k = r.choice([1, 2, 3, 4, 6, 8, 12, -2, -4, -6])
    a = r.randint(-5, 5)
    x1 = r.choice([d for d in range(1, 13) if k % d == 0]) * r.choice([1, -1])
    y1 = F(k, x1) + a
    x0 = r.choice([2, 4, 5, 8, 10, 16, 20, 25])
    val = F(k, x0) + a
    if not nice(val, 2) or x0 == x1:
        return None
    q = (f'График функции f(x) = k/x + a проходит через точку ({tnum(x1)}; {tnum(y1)}), '
         f'а его горизонтальная асимптота — прямая y = {tnum(a)}. Найдите f({x0}).')
    e = f'a = {tnum(a)}; k = ({tnum(y1)} − {par(a)})·{par(x1)} = {tnum(k)}; f({x0}) = {tnum(val)}.'
    K = sp.Symbol('K')
    return card('p11_graph', q, num(val), e), lambda: same(num(val), sp.solve(sp.Eq(K / x1 + a, sp.Rational(y1.numerator, y1.denominator)), K)[0] / x0 + a)


# ---------- 12. Наибольшее и наименьшее значение


@gen('p12_extremum', 'ege-prof', 12, 'Экстремумы и наибольшее/наименьшее значение многочлена', 'm-task-12')
def gen_p12_extremum(r):
    # f'(x) = 3(x − p)(x − q) → f = x³ − 1.5(p+q)x² + 3pq x + c
    p, q_ = r.randint(-6, 6), r.randint(-6, 6)
    if p == q_ or (p + q_) % 2:
        return None
    lo, hi = min(p, q_), max(p, q_)
    c = r.randint(-20, 20)
    coefs = [1, F(-3 * (p + q_), 2), 3 * p * q_, c]
    f = lambda x: sum(F(k) * x**(3 - i) for i, k in enumerate(coefs))
    kind = r.choice(['max_pt', 'min_pt', 'min_seg', 'max_seg'])
    expr = sum(sp.Rational(F(k).numerator, F(k).denominator) * X**(3 - i) for i, k in enumerate(coefs))
    if kind in ('max_pt', 'min_pt'):
        ans = lo if kind == 'max_pt' else hi
        word = 'максимума' if kind == 'max_pt' else 'минимума'
        q = f'Найдите точку {word} функции y = {poly(coefs)}.'
        fac = lambda v: f'(x − {v})' if v > 0 else f'(x + {-v})' if v < 0 else 'x'
        e = f'y′ = {poly([3, -3 * (p + q_), 3 * p * q_])} = 3{fac(lo)}{fac(hi)}; производная меняет знак с «{"+" if word == "максимума" else "−"}» на «{"−" if word == "максимума" else "+"}» в точке {tnum(ans)}.'

        def chk():
            crit = sp.solve(sp.diff(expr, X), X)
            second = sp.diff(expr, X, 2)
            want = [x for x in crit if (second.subs(X, x) < 0 if kind == 'max_pt' else second.subs(X, x) > 0)]
            return len(want) == 1 and want[0] == ans
        return card('p12_extremum', q, num(ans), e), chk
    # отрезок, содержащий нужную критическую точку
    a = r.randint(lo - 4, lo) if kind == 'max_seg' else r.randint(lo, hi)
    b = r.randint(hi, hi + 4) if kind == 'min_seg' else r.randint(lo, hi)
    if a >= b:
        return None
    vals = {x: f(x) for x in {a, b, *[t for t in (lo, hi) if a <= t <= b]}}
    ans = max(vals.values()) if kind == 'max_seg' else min(vals.values())
    if not nice(ans) or abs(ans) > 999:
        return None
    word = 'наибольшее' if kind == 'max_seg' else 'наименьшее'
    q = f'Найдите {word} значение функции y = {poly(coefs)} на отрезке [{tnum(a)}; {tnum(b)}].'
    e = 'Сравниваем значения на концах и в критических точках внутри отрезка: ' + ', '.join(f'y({tnum(x)}) = {tnum(v)}' for x, v in sorted(vals.items())) + f'. Ответ: {tnum(ans)}.'

    def chk():
        cand = [a, b] + [x for x in sp.solve(sp.diff(expr, X), X) if a <= x <= b]
        vs = [expr.subs(X, x) for x in cand]
        return (max(vs) if kind == 'max_seg' else min(vs)) == sp.Rational(F(ans).numerator, F(ans).denominator)
    return card('p12_extremum', q, num(ans), e), chk


# ---------- 13 (пункт б). Отбор корней — числовая карточка «сколько корней на отрезке»

T_VALS = [F(-1), F(-1, 2), F(0), F(1, 2), F(1)]


@gen('p13_roots', 'ege-prof', 13, 'Отбор корней: сколько корней на отрезке (шаг задания 13)', 'm-task-13')
def gen_p13_roots(r):
    fn = r.choice(['sin', 'cos'])
    t1 = r.choice(T_VALS)
    t2 = r.choice([t for t in T_VALS + [F(2), F(-2), F(3, 2)] if t != t1])
    # 2(t − t1)(t − t2) = 2t² − 2(t1+t2)t + 2 t1 t2
    b, c = -2 * (t1 + t2), 2 * t1 * t2
    if b.denominator != 1 or c.denominator != 1:
        return None
    k1 = r.randint(-4, 3)
    k2 = k1 + r.choice([1, 2, 3]) * r.choice([1, 2])
    A, B = sp.pi * k1 / 2, sp.pi * k2 / 2

    def pi_txt(k):
        k = F(k, 2)
        if k == 0:
            return '0'
        s = '−' if k < 0 else ''
        k = abs(k)
        if k.denominator == 1:
            return s + ('π' if k == 1 else f'{k.numerator}π')
        return s + ('π' if k.numerator == 1 else f'{k.numerator}π') + f'/{k.denominator}'
    eq = f'2{fn}²x' + (f' {"+" if b > 0 else "−"} {abs(int(b)) if abs(b) != 1 else ""}{fn} x' if b else '') + (f' {"+" if c > 0 else "−"} {abs(int(c))}' if c else '') + ' = 0'
    # ответ: перебор решений fn x = t по периоду
    ans = 0
    for t in {t1, t2}:
        if abs(t) > 1:
            continue
        base = [math.asin(float(t)), math.pi - math.asin(float(t))] if fn == 'sin' else [math.acos(float(t)), -math.acos(float(t))]
        found = set()
        for x0 in base:
            for n in range(-10, 11):
                x = x0 + 2 * math.pi * n
                if k1 * math.pi / 2 - 1e-9 <= x <= k2 * math.pi / 2 + 1e-9:
                    found.add(round(x, 9))
        ans += len(found)
    q = f'Сколько корней уравнения {eq} принадлежит отрезку [{pi_txt(k1)}; {pi_txt(k2)}]?'
    e = (f'Замена t = {fn} x: {poly([2, b, c], "t")} = 0, t = {tnum(t1)} или t = {tnum(t2)}. '
         f'Значения вне [−1; 1] отбрасываем, остальные корни отбираем на отрезке по единичной окружности. Всего {ans}.').replace('+ -', '− ')

    def chk():
        f_ = sp.sin if fn == 'sin' else sp.cos
        ts = sp.solve(2 * X**2 + int(b) * X + int(c), X)
        roots = set()
        for tv in ts:
            s = sp.solveset(sp.Eq(f_(X), tv), X, sp.Interval(A, B))
            roots |= set(s)
        return len(roots) == ans
    return card('p13_roots', q, num(ans), e), chk


# ---------- 15. Неравенства — карточка с выбором ответа


@gen('p15_ineq', 'ege-prof', 15, 'Логарифмическое неравенство: выбор ответа (ОДЗ и знак)', 'm-task-15', gen_type='param')
def gen_p15_ineq(r):
    base = r.choice([2, 3, 5, F(1, 2), F(1, 3)])
    p = r.randint(-6, 6)
    c = r.randint(-1, 3)
    sign = r.choice(['≤', '≥'])
    bound = F(base) ** c + p
    grows = base > 1
    if not nice(bound, 2):
        return None
    # log_base(x − p) ≤ c; ОДЗ x > p
    if (sign == '≤') == grows:
        right = f'({tnum(p)}; {tnum(bound)}]'
        wrong_domain = f'(−∞; {tnum(bound)}]'
        wrong_sign = f'[{tnum(bound)}; +∞)'
    else:
        right = f'[{tnum(bound)}; +∞)'
        wrong_domain = f'({tnum(p)}; {tnum(bound)}]'
        wrong_sign = f'(−∞; {tnum(bound)}]'
    wrong_open = right.replace('[', '(').replace(']', ')')
    if not nice(bound, 2):
        return None
    opts = [right, wrong_domain, wrong_sign, wrong_open]
    if len(set(opts)) < 4:
        return None
    order = list(range(4))
    r.shuffle(order)
    ids = 'абвг'
    o = [{'id': ids[i], 't': opts[j]} for i, j in enumerate(order)]
    a = ids[order.index(0)]
    bs = tnum(base) if F(base).denominator == 1 else f'{F(base).numerator}/{F(base).denominator}'
    q = f'Выберите множество решений неравенства log{bs.translate(SUB).replace("/", "⁄")}({lin(1, -p)}) {sign} {c}.'
    e = (f'ОДЗ: x > {tnum(p)}. Основание {bs} {"больше" if grows else "меньше"} 1, поэтому знак '
         f'{"сохраняется" if grows else "меняется"}: x − {tnum(p)} {sign if grows else ("≥" if sign == "≤" else "≤")} {tnum(F(base) ** c)}. Ответ: {right}.').replace('− −', '+ ')

    def chk():
        bb = sp.Rational(F(base).numerator, F(base).denominator)
        rel = sp.Le if sign == '≤' else sp.Ge
        sol = sp.solve_univariate_inequality(rel(sp.log(X - p) / sp.log(bb), c), X, relational=False)
        lo_b = sp.Rational(bound.numerator, bound.denominator)
        want = sp.Interval.Lopen(p, lo_b) if right.startswith('(') and not right.endswith('+∞)') else sp.Interval(lo_b, sp.oo)
        return sol == want
    return card('p15_ineq', q, a, e, k='one', o=o), chk


# ---------- 16. Экономическая задача: кредиты


@gen('p16_credit', 'ege-prof', 16, 'Кредит: дифференцированные и аннуитетные платежи', 'm-task-16', lim=10**8)
def gen_p16_credit(r):
    if r.random() < 0.5:
        # долг уменьшается равными частями; выплата = часть долга + проценты на остаток
        n = r.choice([6, 8, 10, 12, 15, 18, 20, 24])
        rate = r.choice([1, 2, 3, 4, 5])
        S = r.choice([n * k * 1000 for k in (1, 2, 3, 5, 10, 25, 50, 100)])
        total = S + F(S * rate, 100) * F(n + 1, 2)
        if total.denominator != 1:
            return None
        q = (f'В июле планируется взять кредит в банке на сумму {S:,} рублей на {n} месяцев. Условия возврата: '.replace(',', ' ')
             + f'каждый месяц долг возрастает на {rate}% по сравнению с концом предыдущего месяца; после начисления процентов '
             'выплачивается часть долга так, чтобы долг уменьшался на одну и ту же величину каждый месяц. '
             'Сколько рублей составит общая сумма выплат?')
        e = (f'Долг каждый месяц уменьшается на S/{n}, проценты начисляются на S, (n−1)S/n, …, S/n. '
             f'Их сумма: {rate}% · S · (n + 1)/2 = {tnum(total - S)}; всего выплат {tnum(total)}.')

        def chk():
            debt, paid, part = sp.Integer(S), 0, sp.Rational(S, n)
            for _ in range(n):
                debt = debt * sp.Rational(100 + rate, 100)
                pay = debt - (debt / sp.Rational(100 + rate, 100) - part)
                paid += pay
                debt -= pay
            return debt == 0 and paid == int(total)
        return card('p16_credit', q, num(total), e), chk
    # m равных ежегодных платежей X (аннуитет): S·kᵐ = X(kᵐ⁻¹ + … + 1). Сначала выбираем X, потом S.
    m = r.choice([2, 2, 3])
    rate = r.choice([10, 20, 25, 50])
    k = F(100 + rate, 100)
    geo = sum(k**i for i in range(m))
    g = geo / k**m  # S = X·g = X·a/b; берём X = b·t, тогда S = a·t — круглая, если t кратно 1000/НОД(a, 1000)
    t_step = 1000 // math.gcd(g.numerator, 1000)
    t = t_step * r.randint(1, max(1, 5_000_000 // (g.denominator * t_step)))
    X_, S = g.denominator * t, F(g.numerator * t)
    if X_ < 50_000 or S > 20_000_000:
        return None
    ask = r.choice(['X', 'total'])
    words = {2: 'двумя', 3: 'тремя'}[m]
    q = (f'31 декабря взяли кредит {int(S):,} рублей на {m} года под {rate}% годовых. '.replace(',', ' ')
         + 'Каждый год 31 декабря банк начисляет проценты на оставшуюся сумму долга, затем заёмщик переводит в банк '
         f'одну и ту же сумму X рублей. Долг выплачивается {words} равными платежами. '
         + ('Найдите X.' if ask == 'X' else 'Сколько рублей составит общая сумма выплат?'))
    ans = X_ if ask == 'X' else m * X_
    e = f'S·{tnum(k)}^{m} = X·({" + ".join(f"{tnum(k)}^{i}" if i > 1 else (tnum(k) if i == 1 else "1") for i in range(m - 1, -1, -1))}) ⇒ X = {X_}' + ('.' if ask == 'X' else f'; всего {m}·X = {m * X_}.')
    xs = sp.Symbol('X', positive=True)
    kk = sp.Rational(k.numerator, k.denominator)

    def chk():  # моделируем по годам
        debt = sp.Integer(int(S)) * kk - xs
        for _ in range(m - 1):
            debt = debt * kk - xs
        x = sp.solve(sp.Eq(debt, 0), xs)[0]
        return (x if ask == 'X' else m * x) == ans
    return card('p16_credit', q, num(ans), e), chk


# ---------- ЕГЭ-2027, новое задание 6: случайная величина


@gen('p6_2027_rv', 'ege-prof-2027', 6, 'Случайная величина: матожидание, дисперсия (новое в 2027)', 'm27-task-6', maxdec=4)
def gen_p6_2027_rv(r):
    n = r.randint(3, 4)
    vals = sorted(r.sample(range(-5, 11), n))
    parts = [r.randint(1, 8) for _ in range(n)]
    tot = sum(parts)
    if tot not in (10, 20, 5, 4, 8, 25):
        return None
    ps = [F(pp, tot) for pp in parts]
    ask = r.choice(['E', 'D', 'miss', 'lottery'])
    if ask == 'lottery':
        # как в демоверсии 2027: матожидание выигрыша на один билет
        N = r.choice([1000, 2000, 5000, 10000])
        prizes = sorted(r.sample([50, 100, 200, 500, 1000, 2000, 5000, 10000, 50000], r.randint(2, 4)))
        counts = [r.choice([1, 2, 5, 10, 20, 50, 100, 200, 500]) for _ in prizes]
        counts.sort(reverse=True)
        if sum(counts) >= N:
            return None
        ans = F(sum(p * c for p, c in zip(prizes, counts)), N)
        if not nice(ans, 2):
            return None
        rows = '; '.join(f'{p} руб. — {c} бил.' for p, c in zip(prizes, counts))
        q = (f'В лотерее {N} билетов. Выигрыши: {rows}; остальные билеты без выигрыша. '
             'Найдите математическое ожидание выигрыша на один купленный билет (в рублях).')
        e = f'EX = ({" + ".join(f"{p}·{c}" for p, c in zip(prizes, counts))}) / {N} = {tnum(ans)}.'
        return card('p6_2027_rv', q, num(ans), e), lambda: sum(sp.Rational(c, N) * p for p, c in zip(prizes, counts)) == sp.Rational(ans.numerator, ans.denominator)
    E = sum(v * p for v, p in zip(vals, ps))
    D = sum((v - E) ** 2 * p for v, p in zip(vals, ps))
    table = 'Значение: ' + '; '.join(tnum(v) for v in vals) + '. Вероятность: '
    if ask == 'miss':
        j = r.randrange(n)
        table += '; '.join('?' if i == j else tnum(p) for i, p in enumerate(ps))
        q = f'Случайная величина X задана распределением. {table}. Найдите пропущенную вероятность.'
        ans = ps[j]
        e = f'Сумма вероятностей равна 1: 1 − ({" + ".join(tnum(p) for i, p in enumerate(ps) if i != j)}) = {tnum(ans)}.'
        return card('p6_2027_rv', q, num(ans), e), lambda: 1 - sum(sp.Rational(p.numerator, p.denominator) for i, p in enumerate(ps) if i != j) == sp.Rational(ans.numerator, ans.denominator)
    table += '; '.join(tnum(p) for p in ps)
    ans = E if ask == 'E' else D
    if not nice(ans, 2):
        return None
    what = 'математическое ожидание' if ask == 'E' else 'дисперсию'
    q = f'Случайная величина X задана распределением. {table}. Найдите {what} X.'
    e = (f'EX = Σ xᵢpᵢ = {tnum(E)}.' if ask == 'E' else f'EX = {tnum(E)}; DX = Σ (xᵢ − EX)²pᵢ = {tnum(D)}.')

    def chk():
        spv = [sp.Rational(p.numerator, p.denominator) for p in ps]
        e1 = sum(v * p for v, p in zip(vals, spv))
        e2 = sum(v * v * p for v, p in zip(vals, spv))
        # другая формула для дисперсии: E(X²) − (EX)²
        return (e1 if ask == 'E' else e2 - e1**2) == sp.Rational(ans.numerator, ans.denominator)
    return card('p6_2027_rv', q, num(ans), e), chk


# ---------- ЕГЭ-2027, новое задание 17: моделирование и оптимизация (здесь — числовой итог)


@gen('p17_2027_opt', 'ege-prof-2027', 17, 'Прикладная задача на наибольшее значение (итог задания 17)', 'm27-task-17', lim=10**6)
def gen_p17_2027_opt(r):
    kind = r.choice(['power', 'fence', 'price'])
    if kind == 'power':
        eps, rr = r.randrange(10, 241, 10), r.choice([F(1, 2), 1, 2, 4, 5, 8, 10])
        pmax = F(eps * eps) / (4 * rr)
        ask = r.choice(['P', 'R'])
        if not nice(pmax, 1):
            return None
        q = (f'Мощность, выделяемая на внешнем сопротивлении R, равна P = ε²R/(R + r)², где ε = {eps} В — ЭДС источника, '
             f'r = {tnum(rr)} Ом — его внутреннее сопротивление. ' + ('Найдите наибольшую мощность (в ваттах).' if ask == 'P' else 'При каком R (в омах) мощность наибольшая?'))
        ans = pmax if ask == 'P' else F(rr)
        e = f'P′(R) = ε²(r − R)/(R + r)³ = 0 при R = r = {tnum(rr)}; P(r) = ε²/(4r) = {tnum(pmax)}.'
        Rv = sp.Symbol('R', positive=True)
        rv = sp.Rational(F(rr).numerator, F(rr).denominator)

        def chk():
            Pexpr = eps**2 * Rv / (Rv + rv) ** 2
            crit = sp.solve(sp.diff(Pexpr, Rv), Rv)
            val = crit[0] if ask == 'R' else Pexpr.subs(Rv, crit[0])
            return len(crit) == 1 and same(num(ans), val)
        return card('p17_2027_opt', q, num(ans), e), chk
    if kind == 'fence':
        L = r.randrange(20, 401, 4)
        area = F(L * L, 8)
        q = (f'Прямоугольный участок одной стороной примыкает к стене дома, а три другие стороны огораживают забором длиной {L} м. '
             'Какую наибольшую площадь (в м²) можно огородить?')
        e = f'S(x) = x({L} − 2x), S′ = {L} − 4x = 0 при x = {tnum(F(L, 4))}; S = {tnum(area)}.'
        xv = sp.Symbol('x', positive=True)
        return card('p17_2027_opt', q, num(area), e), lambda: same(num(area), sp.maximum(xv * (L - 2 * xv), xv, sp.Interval(0, sp.Rational(L, 2))))
    a, b = r.randrange(100, 2001, 20), r.choice([1, 2, 4, 5, 10])
    cost = r.randrange(0, a // (2 * b), 5)
    # спрос q = a − b·p штук, себестоимость cost за штуку; прибыль (p − cost)(a − b p) → max при p = (a/b + cost)/2
    p_opt = (F(a, b) + cost) / 2
    if not nice(p_opt, 1) or p_opt <= cost:
        return None
    q = (f'Спрос на товар при цене p рублей составляет q = {a} − {b if b > 1 else ""}p штук в день, себестоимость одной штуки '
         f'{cost} рублей. При какой цене p (в рублях) дневная прибыль наибольшая?')
    e = f'П(p) = (p − {cost})({a} − {b}p), П′ = {a} − {2 * b}p + {b * cost} = 0 ⇒ p = {tnum(p_opt)}.'
    pv = sp.Symbol('p', positive=True)
    return card('p17_2027_opt', q, num(p_opt), e), lambda: same(num(p_opt), sp.solve(sp.diff((pv - cost) * (a - b * pv), pv), pv)[0])


# ================================================================ ОГЭ


@gen('o6_fractions', 'oge', 6, 'Действия с дробями', 'oge-task-6')
def gen_o6_fractions(r):
    kind = r.choice(['common', 'decimal'])
    if kind == 'common':
        a, b = F(r.randint(1, 9), r.choice([2, 4, 5, 8])), F(r.randint(1, 9), r.choice([2, 4, 5, 10]))
        m = r.choice([2, 4, 5, 8, 10, 12, 20])
        op = r.choice(['+', '−'])
        val = (a + b if op == '+' else a - b) * m
        if not nice(val, 2) or a.denominator == 1 or b.denominator == 1:
            return None
        fr = lambda z: f'{z.numerator}/{z.denominator}' if z.denominator > 1 else tnum(z)
        q = f'Найдите значение выражения ({fr(a)} {op} {fr(b)}) · {m}.'
        e = f'{fr(a)} {op} {fr(b)} = {fr(a + b if op == "+" else a - b)}; · {m} = {tnum(val)}.'
        return card('o6_fractions', q, num(val), e), lambda: (sp.Rational(a.numerator, a.denominator) + (1 if op == '+' else -1) * sp.Rational(b.numerator, b.denominator)) * m == sp.Rational(val.numerator, val.denominator)
    a, b, c = F(r.randint(1, 99), 10), F(r.randint(1, 99), 10), F(r.randint(1, 50), 10)
    val = (a - b) / c
    if not nice(val, 2) or a == b:
        return None
    q = f'Найдите значение выражения ({tnum(a)} − {tnum(b)}) / {tnum(c)}.'
    e = f'{tnum(a - b)} / {tnum(c)} = {tnum(val)}.'
    return card('o6_fractions', q, num(val), e), lambda: (sp.Rational(a.numerator, a.denominator) - sp.Rational(b.numerator, b.denominator)) / sp.Rational(c.numerator, c.denominator) == sp.Rational(val.numerator, val.denominator)


@gen('o9_eq', 'oge', 9, 'Линейные и квадратные уравнения', 'oge-task-9')
def gen_o9_eq(r):
    if r.random() < 0.5:
        a, b, c, d = r.randint(-9, 9), r.randint(-20, 20), r.randint(-9, 9), r.randint(-20, 20)
        if a == c:
            return None
        root = F(d - b, a - c)
        if not nice(root, 1):
            return None
        q = f'Найдите корень уравнения {lin(a, b)} = {lin(c, d)}.'
        e = f'{lin(a - c, 0)} = {tnum(d - b)}, x = {tnum(root)}.'
        return card('o9_eq', q, num(root), e), solve_check(a * X + b, c * X + d, num(root))
    x1, x2 = F(r.randint(-9, 9), r.choice([1, 1, 2])), F(r.randint(-9, 9))
    if x1 == x2:
        return None
    a = x1.denominator
    coefs = [a, -a * (x1 + x2), a * x1 * x2]
    if any(F(k).denominator != 1 for k in coefs):
        return None
    pick = r.choice(['min', 'max'])
    v = min(x1, x2) if pick == 'min' else max(x1, x2)
    word = 'меньший' if pick == 'min' else 'больший'
    q = f'Решите уравнение {poly(coefs)} = 0. Если уравнение имеет более одного корня, в ответ запишите {word} из корней.'
    e = f'D = {tnum(coefs[1] ** 2 - 4 * coefs[0] * coefs[2])}, корни {tnum(min(x1, x2))} и {tnum(max(x1, x2))}; ответ {tnum(v)}.'
    expr = sum(int(k) * X**(2 - i) for i, k in enumerate(coefs))
    return card('o9_eq', q, num(v), e), solve_check(expr, 0, num(v), pick)


@gen('o12_formula', 'oge', 12, 'Расчёт по формуле', 'oge-task-12')
def gen_o12_formula(r):
    kind = r.choice(['rhomb', 'celsius', 'energy', 'taxi'])
    if kind == 'rhomb':
        d1 = r.randint(2, 30)
        d2 = r.randint(2, 30)
        S = F(d1 * d2, 2)
        q = f'Площадь ромба можно вычислить по формуле S = d₁d₂/2, где d₁ и d₂ — диагонали. Найдите диагональ d₁, если d₂ = {d2}, а S = {tnum(S)}.'
        e = f'd₁ = 2S / d₂ = {tnum(2 * S)} / {d2} = {d1}.'
        s = sp.Symbol('s')
        return card('o12_formula', q, num(d1), e), lambda: sp.solve(sp.Eq(s * d2 / 2, sp.Rational(S.numerator, S.denominator)), s)[0] == d1
    if kind == 'celsius':
        c = r.randrange(-40, 101, 5)
        f = F(9, 5) * c + 32
        q = f'Перевести температуру из шкалы Цельсия в шкалу Фаренгейта позволяет формула t_F = 1,8t_C + 32. Сколько градусов по Фаренгейту соответствует {tnum(c)}° по Цельсию?'
        e = f'1,8·{tnum(c)} + 32 = {tnum(f)}.'
        return card('o12_formula', q, num(f), e), lambda: sp.Rational(18, 10) * c + 32 == sp.Rational(f.numerator, f.denominator)
    if kind == 'energy':
        m, v = r.randint(1, 20), r.randint(1, 12)
        E = F(m * v * v, 2)
        q = f'Кинетическая энергия тела вычисляется по формуле E = mv²/2. Найдите массу m (в кг), если v = {v} м/с, а E = {tnum(E)} Дж.'
        e = f'm = 2E / v² = {tnum(2 * E)} / {v * v} = {m}.'
        s = sp.Symbol('s')
        return card('o12_formula', q, num(m), e), lambda: sp.solve(sp.Eq(s * v**2 / 2, sp.Rational(E.numerator, E.denominator)), s)[0] == m
    base, per, t = r.randrange(100, 301, 10), r.randint(8, 25), r.randint(6, 40)
    cost = base + per * (t - 5)
    q = (f'Стоимость поездки на такси (в рублях) рассчитывается по формуле C = {base} + {per}(t − 5), где t — длительность поездки '
         f'в минутах (t > 5). Сколько рублей стоит {t}-минутная поездка?')
    return card('o12_formula', q, num(cost), f'C = {base} + {per}·{t - 5} = {cost}.'), lambda: base + per * (t - 5) == cost


@gen('o13_ineq', 'oge', 13, 'Линейные неравенства: выбор промежутка', 'oge-task-13')
def gen_o13_ineq(r):
    a, b, c = r.choice([2, 3, 4, 5, -2, -3, -4]), r.randint(-20, 20), r.randint(-20, 20)
    sign = r.choice(['<', '>', '≤', '≥'])
    bound = F(c - b, a)
    if not nice(bound, 1):
        return None
    flip = a < 0
    s = {'<': '>', '>': '<', '≤': '≥', '≥': '≤'}[sign] if flip else sign
    B = tnum(bound)
    iv = {'<': f'(−∞; {B})', '≤': f'(−∞; {B}]', '>': f'({B}; +∞)', '≥': f'[{B}; +∞)'}
    right = iv[s]
    wrong = iv[{'<': '>', '>': '<', '≤': '≥', '≥': '≤'}[s]]
    other = iv[{'<': '≤', '≤': '<', '>': '≥', '≥': '>'}[s]]
    wb = tnum(F(c + b, a)) if F(c + b, a) != bound and nice(F(c + b, a), 1) else tnum(-bound) if bound != 0 else '1'
    trap = iv[s].replace(B, wb)
    opts = [right, wrong, other, trap]
    if len(set(opts)) < 4:
        return None
    order = list(range(4))
    r.shuffle(order)
    o = [{'id': str(i + 1), 't': opts[j]} for i, j in enumerate(order)]
    q = f'Укажите решение неравенства {lin(a, b)} {sign} {tnum(c)}.'
    e = f'{lin(a, 0)} {sign} {tnum(c - b)}; делим на {tnum(a)}{" и меняем знак" if flip else ""}: x {s} {B}. Ответ: {right}.'

    def chk():
        rel = {'<': sp.Lt, '>': sp.Gt, '≤': sp.Le, '≥': sp.Ge}[sign]
        sol = sp.solve_univariate_inequality(rel(a * X + b, c), X, relational=False)
        bb = sp.Rational(bound.numerator, bound.denominator)
        want = {'<': sp.Interval.open(-sp.oo, bb), '≤': sp.Interval(-sp.oo, bb), '>': sp.Interval.open(bb, sp.oo), '≥': sp.Interval(bb, sp.oo)}[s]
        return sol == want
    return card('o13_ineq', q, str(order.index(0) + 1), e, k='one', o=o), chk


@gen('o14_progression', 'oge', 14, 'Прогрессии в текстовых задачах', 'oge-task-14')
def gen_o14_progression(r):
    if r.random() < 0.6:
        a1, d, n = r.randint(1, 30), r.randint(1, 12), r.randint(5, 20)
        ask = r.choice(['term', 'sum'])
        if ask == 'term':
            ans = a1 + (n - 1) * d
            q = (f'В амфитеатре {n + r.randint(0, 5)} рядов. В первом ряду {a1} мест, а в каждом следующем на {d} больше, чем в предыдущем. '
                 f'Сколько мест в {n}-м ряду?')
            e = f'aₙ = a₁ + (n − 1)d = {a1} + {n - 1}·{d} = {ans}.'
            return card('o14_progression', q, num(ans), e), lambda: sp.sequence(a1 + (sp.Symbol('k') - 1) * d, (sp.Symbol('k'), 1, n))[n - 1] == ans
        ans = n * (2 * a1 + (n - 1) * d) // 2
        q = (f'Спортсмен в первый день пробежал {a1} км, а в каждый следующий день пробегал на {d} км больше, чем в предыдущий. '
             f'Сколько километров он пробежал за {n} дней?')
        e = f'Sₙ = (2a₁ + (n − 1)d)·n/2 = (2·{a1} + {n - 1}·{d})·{n}/2 = {ans}.'
        return card('o14_progression', q, num(ans), e), lambda: sum(a1 + i * d for i in range(n)) == ans
    b1, qq, n = r.choice([1, 2, 3, 5, 10]), r.choice([2, 3]), r.randint(3, 8)
    ans = b1 * qq ** (n - 1)
    if ans > 10000:
        return None
    q = f'Колония бактерий каждый час увеличивается в {qq} раза. В начале наблюдения было {b1} тыс. бактерий. Сколько тысяч бактерий будет через {n - 1} ч?'
    e = f'bₙ = b₁qⁿ⁻¹ = {b1}·{qq}^{n - 1} = {ans}.'
    return card('o14_progression', q, num(ans), e), lambda: sp.Integer(b1) * sp.Integer(qq)**(n - 1) == ans


# ================================================================ ЕГЭ база


@gen('b1_ceil', 'ege-base', 1, 'Практическая арифметика с округлением', 'base-task-1')
def gen_b1_ceil(r):
    kind = r.choice(['bus', 'pack', 'promo'])
    if kind == 'bus':
        kids, adults, cap = r.randint(80, 600), r.randint(5, 40), r.choice([30, 36, 40, 45, 48, 50, 56])
        tot = kids + adults
        if tot % cap == 0:
            return None
        ans = -(-tot // cap)
        q = (f'Из лагеря в город нужно перевезти группу: детей — {kids}, воспитателей — {adults}. В автобус помещается '
             f'не более {cap} пассажиров. Какое наименьшее количество автобусов понадобится, чтобы перевезти всех за один раз?')
        e = f'{tot} : {cap} = {tnum(F(tot, cap)) if finite(F(tot, cap)) else f"{tot // cap} ост. {tot % cap}"}, округляем вверх: {ans}.'
        return card('b1_ceil', q, num(ans), e), lambda: sp.ceiling(sp.Rational(tot, cap)) == ans
    if kind == 'pack':
        per_week, weeks, pack = r.randrange(200, 2001, 50), r.randint(2, 12), r.choice([250, 500])
        tot = per_week * weeks
        if tot % pack == 0:
            return None
        ans = -(-tot // pack)
        q = (f'В пачке {pack} листов бумаги. За неделю в офисе расходуется {per_week} листов. '
             f'Какого наименьшего количества пачек хватит на {weeks} недель?')
        e = f'{per_week}·{weeks} = {tot} листов; {tot} : {pack} с округлением вверх = {ans}.'
        return card('b1_ceil', q, num(ans), e), lambda: sp.ceiling(sp.Rational(tot, pack)) == ans
    price, money = r.randint(15, 90), r.randrange(100, 1001, 10)
    pay_k, get_k = r.choice([(2, 3), (3, 4), (4, 5)])
    paid = money // price
    ans = paid // pay_k * get_k + paid % pay_k
    q = (f'Шоколадка стоит {price} рублей. По акции, заплатив за {pay_k} шоколадки, покупатель получает {get_k}. '
         f'Какое наибольшее число шоколадок можно получить на {money} рублей?')
    e = f'Можно оплатить {paid} шт.; каждые {pay_k} оплаченные дают {get_k}: {ans}.'

    def chk():  # перебор: сколько получится, если покупать по одной
        best = 0
        for k in range(money // price + 1):
            best = max(best, k // pay_k * get_k + k % pay_k)
        return best == ans
    return card('b1_ceil', q, num(ans), e), chk


@gen('b15_percent', 'ege-base', 15, 'Проценты и доли', 'base-task-15')
def gen_b15_percent(r):
    kind = r.choice(['discount', 'share', 'ratio', 'ndfl'])
    if kind == 'discount':
        p, d = r.randrange(100, 5001, 10), r.choice([5, 10, 15, 20, 25, 30, 40])
        ans = F(p * (100 - d), 100)
        if not nice(ans, 2):
            return None
        q = f'Футболка стоила {p} рублей. Во время распродажи её цена снизилась на {d}%. Сколько рублей стала стоить футболка?'
        return card('b15_percent', q, num(ans), f'{p}·(1 − {tnum(F(d, 100))}) = {tnum(ans)}.'), lambda: sp.Integer(p) * sp.Rational(100 - d, 100) == sp.Rational(ans.numerator, ans.denominator)
    if kind == 'share':
        tot = r.choice([20, 25, 40, 50, 80, 200, 400, 500])
        part = r.randint(1, tot - 1)
        ans = F(part * 100, tot)
        if not nice(ans, 1):
            return None
        q = f'В классе {tot} учеников, из них {part} занимаются в шахматном кружке. Сколько процентов учеников класса занимаются шахматами?'
        return card('b15_percent', q, num(ans), f'{part}/{tot}·100% = {tnum(ans)}%.'), lambda: sp.Rational(part * 100, tot) == sp.Rational(ans.numerator, ans.denominator)
    if kind == 'ratio':
        a, b = r.randint(1, 9), r.randint(1, 9)
        if math.gcd(a, b) != 1 or a == b:
            return None
        tot = (a + b) * r.randint(2, 30)
        big = tot * max(a, b) // (a + b)
        q = f'Отрезок длиной {tot} см разделили в отношении {a} : {b}. Найдите длину большей части в сантиметрах.'
        return card('b15_percent', q, num(big), f'{tot} : {a + b} · {max(a, b)} = {big}.'), lambda: sp.Rational(tot * max(a, b), a + b) == big
    net = r.randrange(8700, 87001, 870)
    gross = F(net * 100, 87)
    q = f'После удержания налога на доходы физических лиц (13%) Иван получил {net} рублей. Сколько рублей составляет его зарплата до вычета налога?'
    return card('b15_percent', q, num(gross), f'{net} : 0,87 = {tnum(gross)}.'), lambda: sp.Rational(gross.numerator, gross.denominator) * sp.Rational(87, 100) == net


@gen('b19_digits', 'ege-base', 19, 'Делимость и цифры (наименьшее/наибольшее — единственный ответ)', 'base-task-19', lim=10**5)
def gen_b19_digits(r):
    m = r.choice([3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 18, 20, 21, 22, 24, 25, 27, 33, 35, 36, 44, 45, 55, 75])
    conds = {
        'различные': ('все цифры различны', lambda s: len(set(s)) == len(s)),
        'чётные': ('все цифры чётные', lambda s: all(c in '02468' for c in s)),
        'нечётные': ('все цифры нечётные', lambda s: all(c in '13579' for c in s)),
        'без нулей': ('нет нулей', lambda s: '0' not in s),
        'возрастают': ('цифры идут строго по возрастанию', lambda s: all(x < y for x, y in zip(s, s[1:]))),
        'сумма': (None, None),
    }
    ck = r.choice(list(conds))
    if ck == 'сумма':
        sm = r.randint(5, 27)
        word, ok = f'сумма цифр равна {sm}', (lambda s, sm=sm: sum(map(int, s)) == sm)
    else:
        word, ok = conds[ck]
    ext = r.choice(['наименьшее', 'наибольшее'])
    n_dig = r.choice([3, 4, 5])
    rng = range(10 ** (n_dig - 1), 10 ** n_dig)
    good = [x for x in rng if x % m == 0 and ok(str(x))]
    if not good:
        return None
    ans = min(good) if ext == 'наименьшее' else max(good)
    nd = {3: 'трёх', 4: 'четырёх', 5: 'пяти'}[n_dig]
    q = f'Найдите {ext} {nd}значное число, которое делится на {m} и у которого {word}.'
    e = f'Перебираем кратные {m} {"с начала" if ext == "наименьшее" else "с конца"} диапазона, первое подходящее — {ans}.'

    def chk():  # другим путём: шагаем по кратным m
        start = -(-10 ** (n_dig - 1) // m) * m
        cands = list(range(start, 10 ** n_dig, m))
        seq = cands if ext == 'наименьшее' else cands[::-1]
        return next(x for x in seq if ok(str(x))) == ans
    return card('b19_digits', q, num(ans), e), chk


UNITS = {  # объект → (значение, варианты-ловушки того же рода); свои данные, без копирования банков
    'масса': [('масса слона', '5 т'), ('масса кошки', '4 кг'), ('масса яблока', '200 г'), ('масса снежинки', '3 мг'),
              ('масса легкового автомобиля', '1,5 т'), ('масса арбуза', '8 кг'), ('масса монеты', '5 г'), ('масса комара', '2 мг')],
    'длина': [('рост человека', '175 см'), ('длина реки Волги', '3530 км'), ('толщина листа бумаги', '0,1 мм'), ('длина комнаты', '5 м'),
              ('высота многоэтажного дома', '60 м'), ('расстояние Москва — Санкт-Петербург', '700 км'), ('длина муравья', '5 мм'), ('длина карандаша', '18 см')],
    'время': [('продолжительность урока', '45 минут'), ('время моргания глаза', '0,3 секунды'), ('длительность летних каникул', '3 месяца'),
              ('время полёта Москва — Владивосток', '9 часов'), ('время варки яйца всмятку', '3 минуты'), ('срок обучения в школе', '11 лет')],
}


@gen('b2_units', 'ege-base', 2, 'Единицы измерения: соответствие величин и значений', 'base-task-2', gen_type='dict')
def gen_b2_units(r):
    kind = r.choice(list(UNITS))
    items = r.sample(UNITS[kind], 4)
    right = items[:]
    r.shuffle(right)
    left = [{'id': 'АБВГ'[i], 't': it[0]} for i, it in enumerate(items)]
    rr = [{'id': str(i + 1), 't': it[1]} for i, it in enumerate(right)]
    a = {'АБВГ'[i]: str(right.index(it) + 1) for i, it in enumerate(items)}
    q = f'Установите соответствие между величинами и их возможными значениями ({kind}).'
    return card('b2_units', q, a, k='match', o={'left': left, 'right': rr}), lambda: all(rr[int(a[l['id']]) - 1]['t'] == dict(items)[l['t']] for l in left)


# ================================================================ 5–9 класс


@gen('s5_gcd', 'school', 6, 'НОД и НОК', 'school-6-divisibility')
def gen_s5_gcd(r):
    g = r.randint(2, 30)
    a, b = g * r.randint(2, 12), g * r.randint(2, 12)
    if a == b:
        return None
    if r.random() < 0.5:
        ans = math.gcd(a, b)
        return card('s5_gcd', f'Найдите наибольший общий делитель чисел {a} и {b}.', num(ans), f'НОД({a}, {b}) = {ans}.'), lambda: sp.gcd(a, b) == ans
    ans = a * b // math.gcd(a, b)
    if ans > 2000:
        return None
    return card('s5_gcd', f'Найдите наименьшее общее кратное чисел {a} и {b}.', num(ans), f'НОК = {a}·{b} / НОД = {ans}.'), lambda: sp.lcm(a, b) == ans


@gen('s6_percent', 'school', 6, 'Процент от числа и число по проценту', 'school-6-percent')
def gen_s6_percent(r):
    p = r.choice([1, 2, 5, 10, 12, 15, 20, 25, 30, 40, 50, 75, 120, 150])
    base = r.randrange(20, 2001, 20)
    part = F(base * p, 100)
    if not nice(part, 1):
        return None
    if r.random() < 0.5:
        return card('s6_percent', f'Найдите {p}% от числа {base}.', num(part), f'{base}·{p}/100 = {tnum(part)}.'), lambda: sp.Rational(base * p, 100) == sp.Rational(part.numerator, part.denominator)
    return card('s6_percent', f'{p}% числа равны {tnum(part)}. Найдите это число.', num(base), f'{tnum(part)} : {p} · 100 = {base}.'), lambda: sp.Rational(part.numerator, part.denominator) * 100 / p == base


@gen('s7_linear', 'school', 7, 'Линейные уравнения со скобками', 'school-7-linear')
def gen_s7_linear(r):
    a, b, c, d, k = r.randint(2, 9), r.randint(-9, 9), r.randint(1, 9), r.randint(-30, 30), r.randint(2, 5)
    # k(ax + b) − cx = d
    if k * a == c:
        return None
    root = F(d - k * b, k * a - c)
    if not nice(root, 1):
        return None
    q = f'Решите уравнение {k}({lin(a, b)}) − {lin(c, 0) if c >= 0 else "(" + lin(c, 0) + ")"} = {tnum(d)}.'
    e = f'{lin(k * a, k * b)} − {lin(c, 0)} = {tnum(d)} ⇒ {lin(k * a - c, 0)} = {tnum(d - k * b)} ⇒ x = {tnum(root)}.'.replace('− −', '+ ')
    return card('s7_linear', q, num(root), e), solve_check(k * (a * X + b) - c * X, d, num(root))


@gen('s8_vieta', 'school', 8, 'Квадратное уравнение: корни, теорема Виета', 'school-8-quadratic')
def gen_s8_vieta(r):
    x1, x2 = r.randint(-15, 15), r.randint(-15, 15)
    if x1 == x2:
        return None
    ask = r.choice(['sum', 'prod', 'sq'])
    coefs = [1, -(x1 + x2), x1 * x2]
    ans = {'sum': x1 + x2, 'prod': x1 * x2, 'sq': x1 * x1 + x2 * x2}[ask]
    what = {'sum': 'сумму корней', 'prod': 'произведение корней', 'sq': 'сумму квадратов корней'}[ask]
    q = f'Не решая уравнение {poly(coefs)} = 0, найдите {what}.'
    e = {'sum': f'x₁ + x₂ = −b = {ans}.', 'prod': f'x₁x₂ = c = {ans}.', 'sq': f'x₁² + x₂² = (x₁ + x₂)² − 2x₁x₂ = {par(x1 + x2)}² − 2·{par(x1 * x2)} = {tnum(ans)}.'}[ask]

    def chk():
        s = sp.solve(X**2 + coefs[1] * X + coefs[2], X)
        return {'sum': sum(s), 'prod': sp.prod(s), 'sq': sum(v**2 for v in s)}[ask] == ans
    return card('s8_vieta', q, num(ans), e), chk


@gen('s9_system', 'school', 9, 'Системы линейных уравнений', 'school-9-systems')
def gen_s9_system(r):
    x0, y0 = r.randint(-9, 9), r.randint(-9, 9)
    a1, b1, a2, b2 = [r.randint(-6, 6) for _ in range(4)]
    if a1 * b2 - a2 * b1 == 0 or 0 in (a1, b1, a2, b2):
        return None
    c1, c2 = a1 * x0 + b1 * y0, a2 * x0 + b2 * y0
    ask = r.choice(['x', 'y', 'x+y'])
    ans = {'x': x0, 'y': y0, 'x+y': x0 + y0}[ask]
    eq = lambda a, b, c: f'{poly([a, 0])}'.replace('x', 'x') + (f' + {poly([b, 0], "y")}' if b > 0 else f' − {poly([-b, 0], "y")}') + f' = {tnum(c)}'
    q = f'Решите систему {{ {eq(a1, b1, c1)}; {eq(a2, b2, c2)} }}. В ответ запишите {"x" if ask == "x" else "y" if ask == "y" else "x + y"}.'
    e = f'Решение: x = {tnum(x0)}, y = {tnum(y0)}.'
    Y = sp.Symbol('y')

    def chk():
        s = sp.solve([sp.Eq(a1 * X + b1 * Y, c1), sp.Eq(a2 * X + b2 * Y, c2)], [X, Y])
        return {'x': s[X], 'y': s[Y], 'x+y': s[X] + s[Y]}[ask] == ans
    return card('s9_system', q, num(ans), e), chk


# ================================================================ самопроверка


def answer_ok(c, maxdec, lim=10000):
    if c['k'] == 'num':
        try:
            v = F(c['a'].replace(',', '.'))
        except ValueError:
            return False
        return nice(v, maxdec, lim)
    if c['k'] == 'one':
        return c['a'] in [o['id'] for o in c['o']]
    if c['k'] == 'many':
        return bool(c['a']) and set(c['a']) <= {o['id'] for o in c['o']}
    if c['k'] == 'match':
        return set(c['a']) == {x['id'] for x in c['o']['left']}
    return True


def run(gid, n, seed=1, capacity_tries=4000):  # noqa: C901
    g = GEN[gid]
    r = random.Random(f'{seed}-{gid}')
    cards, seen, stats = [], set(), Counter()
    tries = 0
    while len(cards) < n and tries < n * 200:
        tries += 1
        res = g['fn'](r)
        if res is None:
            stats['отсеяно'] += 1
            continue
        c, chk = res
        key = c['q'] + json.dumps(c.get('o'), ensure_ascii=False)
        if key in seen:
            stats['повтор'] += 1
            continue
        if not answer_ok(c, g['maxdec'], g['lim']):
            stats['неприятный ответ'] += 1
            continue
        try:
            ok = bool(chk())
        except Exception as ex:  # noqa: BLE001 — любая ошибка проверки = провал
            ok = False
            stats[f'ошибка проверки: {type(ex).__name__}'] += 1
        if not ok:
            stats['ОТВЕТ НЕ СОШЁЛСЯ'] += 1
            print('  !!', gid, c['q'], c['a'], file=sys.stderr)
            continue
        seen.add(key)
        c['id'] = f'gen-{gid}-{len(cards) + 1}'
        cards.append(c)
    # ёмкость: сколько разных условий даёт генератор (нижняя оценка)
    r2 = random.Random(f'cap-{gid}')
    uniq = set()
    for _ in range(capacity_tries):
        res = g['fn'](r2)
        if res:
            uniq.add(res[0]['q'] + json.dumps(res[0].get('o'), ensure_ascii=False))
    answers = Counter(json.dumps(c['a'], ensure_ascii=False) for c in cards)
    return cards, dict(stats=stats, tries=tries, capacity=len(uniq), distinct_answers=len(answers),
                       top_answer_share=round(answers.most_common(1)[0][1] / max(1, len(cards)), 3) if cards else 0)


# ================================================================ экспорт data/research/math.json

MAP_2027 = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 7: 6, 8: 7, 9: 8, 10: 9, 11: 10, 12: 11, 14: 13, 15: 14, 16: 15, 18: 17, 19: 18, 20: 19}


def export(path):
    import copy
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import math_meta as M

    cache = {}

    def examples(gids, k=2):
        out = []
        for gid in gids:
            if gid not in cache:
                cache[gid] = run(gid, 6, capacity_tries=0)[0]  # тот же отбор и проверка, что в самопроверке
            for c in cache[gid][:max(1, k // len(gids))]:
                ex = {'q': c['q'], 'a': c['a']}
                if 'o' in c:
                    ex['o'] = c['o']
                out.append(ex)
        return out[:k]

    def task(d, exam_id):
        d = copy.deepcopy(d)
        gids = d.pop('gen_ids', [])
        t = {
            'n': d['n'], 'title': d['title'], 'checks': d.get('checks', d['title']), 'codifier': d.get('codifier', []),
            'answer': d.get('answer', 'number'), 'points': d.get('points', 1), 'part': d.get('part', 1),
            'cards': d.get('cards', ['num']), 'gen': d['gen'],
            'recipe': d.get('recipe') or (f'Генераторы {", ".join(gids)} в tools/research/gen_math.py' if gids else ''),
            'mistakes': d.get('mistakes', []), 'theory': d.get('theory', []), 'estimate': d['estimate'], 'priority': d['priority'],
            'examples': examples(gids) if gids else [],
        }
        if gids:
            t['gen_ids'] = gids
        for extra in ('n_2026', 'note'):
            if extra in d:
                t[extra] = d[extra]
        for h in M.HAND_EXAMPLES.get((exam_id, d.get('n_2026', d['n'])), []):
            assert eval(h['chk']), (exam_id, d['n'], h)  # noqa: S307 — выражения наши, из math_meta.py
            t['examples'].append({'q': h['q'], 'a': h['a']})
        assert t['examples'], f'нет примеров: {exam_id} №{d["n"]}'
        return t

    prof26 = [task(d, 'ege-prof-2026') for d in M.EGE_PROF]
    by_n = {d['n']: d for d in M.EGE_PROF}
    new27 = {d['n']: d for d in M.EGE_PROF_2027_NEW}
    points27 = {14: 2, 15: 3, 16: 2, 18: 3, 19: 4, 20: 4}
    prof27 = []
    for n in range(1, 21):
        if n in new27:
            d = dict(new27[n], note='новое задание 2027')
        else:
            d = dict(by_n[MAP_2027[n]], n=n, n_2026=MAP_2027[n])
            d['points'] = points27.get(n, 1)
        prof27.append(task(d, 'ege-prof-2026' if n not in new27 else 'ege-prof-2027'))
    data = [
        {'subject': 'Математика', 'exam': 'ЕГЭ профильный уровень 2026', 'id': 'ege-prof-2026', 'sources': M.SRC_EGE26,
         'summary': '19 заданий: часть 1 — 12 с кратким ответом (12 баллов), часть 2 — 7 с развёрнутым (20 баллов); максимум 32; 235 минут. '
                    'Изменений структуры против 2025 нет.', 'tasks': prof26, 'topics_5_9': []},
        {'subject': 'Математика', 'exam': 'ЕГЭ профильный уровень 2027 (проект ФИПИ)', 'id': 'ege-prof-2027', 'sources': M.SRC_EGE27,
         'summary': '20 заданий: часть 1 — 13 (13 баллов), часть 2 — 7 (20 баллов); максимум 33. Новые №6 (случайная величина), №13 (текстовая/финансовая, краткий ответ), '
                    '№17 (моделирование, 2 балла). Позиции «наибольшее/наименьшее значение» (№12 2026) и экономической задачи с развёрнутым ответом (№16 2026) в плане нет.',
         'tasks': prof27, 'topics_5_9': []},
        {'subject': 'Математика', 'exam': 'ЕГЭ базовый уровень 2026', 'id': 'ege-base-2026', 'sources': M.SRC_EGE26[:3],
         'summary': '21 задание с кратким ответом, по 1 баллу, максимум 21; 180 минут; только базовый уровень. Изменений против 2025 нет; проект 2027 — без изменений.',
         'tasks': [task(d, 'ege-base-2026') for d in M.EGE_BASE], 'topics_5_9': []},
        {'subject': 'Математика', 'exam': 'ОГЭ 2026', 'id': 'oge-2026', 'sources': M.SRC_OGE,
         'summary': '25 заданий: часть 1 — 19 с кратким ответом (по 1 баллу), часть 2 — 6 с развёрнутым (по 2 балла); максимум 31; 235 минут. '
                    'Изменений против 2025 нет; проект 2027 — без изменений структуры.', 'tasks': [task(d, 'oge-2026') for d in M.OGE], 'topics_5_9': []},
        {'subject': 'Математика', 'exam': '5–9 класс (ФРП «Математика», п. 146 ФОП ООО)', 'id': 'school-5-9', 'sources': M.SRC_SCHOOL, 'tasks': [],
         'topics_5_9': [{**{k: v for k, v in t.items() if k != 'gen_ids'}, **({'gen_ids': t['gen_ids'], 'examples': examples(t['gen_ids'], 1)} if t.get('gen_ids') else {})}
                        for t in M.TOPICS_5_9]},
    ]
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    n_tasks = sum(len(e['tasks']) for e in data)
    print(f'{path}: {len(data)} разделов, {n_tasks} заданий, {len(data[-1]["topics_5_9"])} тем 5–9')


# ================================================================ прототипы: самопроверка и экспорт
#
#   python3 tools/research/gen_math.py --protos [--exam oge] [--proto og09-quad] [--fipi DIR]
#   python3 tools/research/gen_math.py --export-protos data/source/math-prototypes.json --fipi DIR
#
# DIR — локальная выгрузка текстов ФИПИ (открытый банк, демоверсии, открытые варианты):
# файлы *.jsonl с полями {id, text} и *.txt. Она нужна только для сверки сходства
# и в репозиторий не кладётся (тексты ФИПИ — «© Рособрнадзор»).

import glob
import importlib
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SIM_LIMIT = 0.30      # предельное сходство с текстом ФИПИ (доля наших 5-словных шинглов)
CAP_TARGET = 50       # минимум разных аналогов на прототип
CAP_TRIES = 3000


def load_protos():
    import mathlib
    for path in sorted(glob.glob(os.path.join(HERE, 'proto_*.py'))):
        try:
            importlib.import_module(os.path.basename(path)[:-3])
        except Exception as ex:  # noqa: BLE001 — сломанный модуль не мешает проверять остальные
            print(f'  !! модуль {os.path.basename(path)} не загрузился: {type(ex).__name__}: {ex}', file=sys.stderr)
    return mathlib.PROTO


def tokens(text, mask=True):
    """Слова и числа в нижнем регистре. mask=True: числа заменены на «0» — сходство меряем
    по словам, а не по числам (так ловится «тот же текст с другими числами»)."""
    t = text.lower().replace('ё', 'е')
    t = re.sub(r'<[^>]+>', ' ', t)
    return ['0' if mask and w[0].isdigit() else w for w in re.findall(r'[а-яa-z]+|\d+(?:[.,]\d+)?', t)]


def shingles(text, k=5, mask=True):
    w = tokens(text, mask)
    return {' '.join(w[i:i + k]) for i in range(len(w) - k + 1)}


# Стандартные инструкции КИМ — общие математические обороты, а не авторский текст. Их вырезаем
# из нашего условия перед сверкой, чтобы формулировка могла быть «как в КИМ»: сравнивается
# только содержательная часть (сюжет, формула с числами).
STOCK = [r'найдите (?:корень|корни) уравнения', r'решите уравнение', r'решите неравенство', r'решите систему(?: уравнений| неравенств)?',
         r'найдите значение выражения', r'найдите значение', r'вычислите', r'упростите выражение',
         r'если уравнение имеет более одного корня,? в ответе (?:запишите|укажите) (?:меньший|больший) из (?:них|корней)',
         r'найдите точку (?:минимума|максимума) функции', r'найдите (?:наименьшее|наибольшее) значение функции',
         r'на отрезке', r'на промежутке', r'в ответе (?:запишите|укажите)[^.]*', r'ответ дайте в [^.]*',
         r'результат округлите до [^.]*', r'запишите номера выбранных утверждений[^.]*', r'без пробелов, запятых и других дополнительных символов',
         r'на рисунке изображ[её]н[аоы]? (?:график|графики)[^.]*', r'найдите', r'определите', r'укажите']
STOCK_RE = re.compile('|'.join(STOCK), re.I)


def strip_stock(text):
    return STOCK_RE.sub(' ', text.replace('ё', 'е').replace('Ё', 'Е'))


def wordy(text):
    """Сюжетное ли условие: 8 и больше русских слов. В коротких «формульных» условиях
    («Решите уравнение …») слов почти нет, и совпадение инструкции неизбежно — их сверяем
    без маскировки чисел, то есть ловим только буквальное совпадение с заданием ФИПИ."""
    return len(re.findall(r'[а-яё]{3,}', text.lower())) >= 8


class Fipi:
    """Индекс шинглов текстов ФИПИ; bank — тексты открытого банка по экзаменам."""

    def __init__(self, d):
        self.docs, self.bank = [], {}
        for path in sorted(glob.glob(os.path.join(d, '**', '*.jsonl'), recursive=True)):
            key = os.path.basename(path)[:-6]
            rows = [json.loads(line) for line in open(path, encoding='utf-8')]
            self.bank[key] = rows
            self.docs += [r['text'] for r in rows]
        for path in sorted(glob.glob(os.path.join(d, '**', '*.txt'), recursive=True)):
            # демоверсии и открытые варианты: режем на куски по «Ответ:», чтобы сравнивать по заданиям
            parts = re.split(r'Ответ:\s*_+', open(path, encoding='utf-8').read())
            self.docs += [p for p in parts if len(p) > 40]
        self.index = {True: {}, False: {}}
        for i, t in enumerate(self.docs):
            for mask in (True, False):
                for s in shingles(t, mask=mask):
                    self.index[mask].setdefault(s, set()).add(i)

    def sim(self, text):
        """Наибольшая доля шинглов нашего текста, найденных в одном тексте ФИПИ."""
        text = strip_stock(text)
        mask = wordy(text)
        sh = shingles(text, mask=mask)
        if not sh:
            return 0.0
        cnt = Counter()
        idx = self.index[mask]
        for s in sh:
            for i in idx.get(s, ()):
                cnt[i] += 1
        return max(cnt.values(), default=0) / len(sh)


BANK_OF = {'ege-prof': 'prof', 'ege-base': 'base', 'oge': 'oge'}


def card_text(c):
    """Условие вместе с вариантами ответа (one/many: o = [{id, t}], match: o = {left, right})."""
    o = c.get('o') or []
    if isinstance(o, dict):
        o = o.get('left', []) + o.get('right', [])
    return c['q'] + ' ' + ' '.join(str(x.get('t', '')) for x in o if isinstance(x, dict))


def run_proto(p, n, fipi=None, seed=1, cap_tries=None):
    """Самопроверка одного прототипа → (карточки, сводка)."""
    info = dict(id=p['id'], kind=p['kind'], fail=0, dup=0, drop=0, bad=0, cards=0, capacity=0, sim_max=None, sim_over=0)
    if p['kind'] == 'llm':
        ex = p['example']
        ok = bool(ex['chk']())
        info.update(fail=0 if ok else 1, cards=1, capacity=p['capacity'])
        if fipi:
            info['sim_max'] = round(fipi.sim(ex['q']), 3)
            info['sim_over'] = int(info['sim_max'] >= SIM_LIMIT)
        return [pcard(ex['q'], ex['a'])], info
    r = random.Random(f'{seed}-{p["id"]}')
    cards, seen = [], set()
    tries = 0
    while len(cards) < n and tries < n * 60:
        tries += 1
        res = p['fn'](r)
        if res is None:
            info['drop'] += 1
            continue
        c, chk = res
        key = c['q'] + json.dumps(c.get('o'), ensure_ascii=False) + c.get('svg', '')
        if key in seen:
            info['dup'] += 1
            continue
        if not answer_ok(c, p['maxdec'], p['lim']):
            info['bad'] += 1
            print('  ?? неприятный ответ', p['id'], c['q'][:90], c['a'], file=sys.stderr)
            continue
        try:
            ok = bool(chk())
        except Exception as ex:  # noqa: BLE001 — любая ошибка проверки = провал
            ok = False
            print('  !! ошибка проверки', p['id'], type(ex).__name__, ex, file=sys.stderr)
        if not ok:
            info['fail'] += 1
            print('  !! ответ не сошёлся', p['id'], c['q'][:120], c['a'], file=sys.stderr)
            continue
        if p['svg'] and not c.get('svg', '').startswith('<svg'):
            info['fail'] += 1
            print('  !! нет рисунка', p['id'], file=sys.stderr)
            continue
        seen.add(key)
        c['id'] = f'{p["id"]}-{len(cards) + 1}'
        c['t'] = f'{p["exam"]}-{p["n"]}'
        c['p'] = p['id']
        cards.append(c)
    r2 = random.Random(f'cap-{p["id"]}')
    uniq = set()
    for _ in range(CAP_TRIES if cap_tries is None else cap_tries):
        res = p['fn'](r2)
        if res:
            uniq.add(res[0]['q'] + json.dumps(res[0].get('o'), ensure_ascii=False) + res[0].get('svg', ''))
    info['capacity'] = len(uniq)
    info['cards'] = len(cards)
    info['answers'] = len({json.dumps(c['a'], ensure_ascii=False) for c in cards})
    if fipi and cards:
        sims = [fipi.sim(card_text(c)) for c in cards]
        info['sim_max'] = round(max(sims), 3)
        info['sim_over'] = sum(s >= SIM_LIMIT for s in sims)
        worst = max(range(len(cards)), key=lambda i: sims[i])
        if sims[worst] >= SIM_LIMIT:
            print(f'  ~~ сходство {sims[worst]:.2f}', p['id'], cards[worst]['q'][:120], file=sys.stderr)
    return cards, info


def fipi_coverage(protos, fipi):
    """Сколько заданий открытого банка узнаёт хотя бы один прототип (по регулярке fipi)."""
    out = {}
    for exam, key in BANK_OF.items():
        rows = fipi.bank.get(key, [])
        regs = [(p['id'], re.compile(p['fipi'], re.I)) for p in protos.values() if p['exam'] == exam and p.get('fipi')]
        hit, per = 0, Counter()
        unmatched = []
        for row in rows:
            ids = [pid for pid, rg in regs if rg.search(row['text'])]
            per.update(ids)
            if ids:
                hit += 1
            else:
                unmatched.append(row)
        out[exam] = dict(total=len(rows), matched=hit, per=per, unmatched=unmatched)
    return out


def protos_main(args):
    protos = load_protos()
    fipi = Fipi(args.fipi) if args.fipi else None
    sel = [p for p in protos.values() if (not args.exam or p['exam'] == args.exam) and (not args.proto or p['id'].startswith(args.proto))]
    sel.sort(key=lambda p: (list(EXAMS).index(p['exam']), p['n'], p['id']))
    print(f'{"прототип":<24}{"вид":<6}{"готово":>7}{"отсев":>6}{"повт.":>6}{"сбой":>5}{"ёмкость":>8}{"ответов":>8}{"сходство":>9}')
    allcards, infos = [], []
    for p in sel:
        cards, info = run_proto(p, args.n, fipi)
        infos.append(info)
        allcards += cards
        sim = '—' if info['sim_max'] is None else f'{info["sim_max"]:.2f}'
        print(f'{p["id"]:<24}{p["kind"]:<6}{info["cards"]:>7}{info["drop"]:>6}{info["dup"]:>6}{info["fail"]:>5}'
              f'{info["capacity"]:>8}{info.get("answers", "—"):>8}{sim:>9}')
        if args.sample:
            for c in cards[:2]:
                print('   ', json.dumps({k: v for k, v in c.items() if k != 'svg'}, ensure_ascii=False))
    # дубли между прототипами
    qs = Counter(c['q'] + json.dumps(c.get('o'), ensure_ascii=False) + c.get('svg', '') for c in allcards)
    cross = sum(v - 1 for v in qs.values() if v > 1)
    fails = sum(i['fail'] for i in infos)
    low = [i['id'] for i in infos if i['kind'] == 'param' and i['capacity'] < CAP_TARGET]
    over = [i['id'] for i in infos if i['sim_over']]
    print(f'\nПрототипов: {len(sel)} (param {sum(i["kind"] == "param" for i in infos)}, llm {sum(i["kind"] == "llm" for i in infos)}); '
          f'карточек: {len(allcards)}; несошедшихся ответов: {fails}; дублей между прототипами: {cross}')
    print(f'Ёмкость < {CAP_TARGET}: {len(low)} {low[:20]}')
    if fipi:
        sims = [i['sim_max'] for i in infos if i['sim_max'] is not None]
        print(f'Сходство с ФИПИ ≥ {SIM_LIMIT:.0%}: прототипов {len(over)} {over[:20]}; максимум по всем {max(sims, default=0):.2f}')
        cov = fipi_coverage({p['id']: p for p in sel}, fipi)
        for exam, c in cov.items():
            if c['total'] and (not args.exam or exam == args.exam):
                print(f'Банк ФИПИ, {EXAMS[exam]}: узнано прототипами {c["matched"]} из {c["total"]}')
                if args.unmatched:
                    for row in c['unmatched'][:args.unmatched]:
                        print('   ·', row['id'], row.get('kes', [''])[:1], row['text'][:160])
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as fh:
            json.dump(allcards, fh, ensure_ascii=False, indent=1)
    return 1 if fails or cross else 0


def export_protos(path, fipi_dir, n=30):
    protos = load_protos()
    fipi = Fipi(fipi_dir) if fipi_dir else None
    cov = fipi_coverage(protos, fipi) if fipi else {}
    fid_path = os.path.join(HERE, 'math_fidelity.json')
    fid = json.load(open(fid_path, encoding='utf-8')) if os.path.exists(fid_path) else {}
    out = []
    for p in sorted(protos.values(), key=lambda p: (list(EXAMS).index(p['exam']), p['n'], p['id'])):
        cards, info = run_proto(p, n, fipi)
        assert not info['fail'], p['id']
        ex = cards[0]
        rec = dict(id=p['id'], exam=p['exam'], n=p['n'], title=p['title'], invariant=p['invariant'], varies=p['varies'],
                   answer_rule=p['answer_rule'],
                   gen=p['gen'] if p['kind'] == 'param' else {'llm': p['recipe']},
                   capacity=info['capacity'], example={k: ex[k] for k in ('q', 'a', 'e', 'o', 'svg') if k in ex})
        if p['mistakes']:
            rec['mistakes'] = p['mistakes']
        if p['svg']:
            rec['figure'] = True
        if p.get('note'):
            rec['note'] = p['note']
        if p.get('kim'):
            rec['kim'] = p['kim']
        rec['fidelity'] = fid.get(p['id'], {'verdict': 'not_checked'})
        if fipi:
            rec['fipi_bank_matches'] = cov[p['exam']]['per'].get(p['id'], 0)
            rec['sim_fipi_max'] = info['sim_max']
        out.append(rec)
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    print(f'{path}: {len(out)} прототипов')


def review_dump(path, fipi_dir, k=5):
    """Материал для «экзаменационной проверки»: по k случайных аналогов на прототип (другое зерно,
    чем в самопроверке) + паспорт КИМ + до 3 заданий банка ФИПИ того же прототипа (только локально)."""
    protos = load_protos()
    fipi = Fipi(fipi_dir) if fipi_dir else None
    bank = {}
    if fipi:
        for exam, key in BANK_OF.items():
            bank[exam] = fipi.bank.get(key, [])
    with open(path, 'w', encoding='utf-8') as fh:
        for p in sorted(protos.values(), key=lambda p: (list(EXAMS).index(p['exam']), p['n'], p['id'])):
            cards, _ = run_proto(p, k, None, seed=7, cap_tries=0)
            rng = random.Random(p['id'])
            same_bank = [r_['text'] for r_ in bank.get(p['exam'], []) if p.get('fipi') and re.search(p['fipi'], r_['text'], re.I)]
            rec = {k_: p[k_] for k_ in ('id', 'exam', 'n', 'title', 'invariant', 'varies', 'answer_rule', 'kind', 'kim', 'mistakes')}
            rec['analogs'] = [{k_: c[k_] for k_ in ('q', 'a', 'e', 'o', 'k') if k_ in c} | ({'svg': True} if c.get('svg') else {}) for c in cards]
            rec['fipi_bank_sample'] = rng.sample(same_bank, min(3, len(same_bank)))
            if p['kind'] == 'llm':
                rec['recipe'] = p['recipe']
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(f'{path}: {len(protos)} прототипов')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=200)
    ap.add_argument('--sample', action='store_true')
    ap.add_argument('--json')
    ap.add_argument('--only')
    ap.add_argument('--export', help='собрать data/research/math.json')
    ap.add_argument('--protos', action='store_true', help='самопроверка прототипов (proto_*.py)')
    ap.add_argument('--exam', help='только этот экзамен: ege-prof, ege-base, oge')
    ap.add_argument('--proto', help='только прототипы с этим началом id')
    ap.add_argument('--fipi', help='папка с локальными текстами ФИПИ для сверки сходства')
    ap.add_argument('--unmatched', type=int, default=0, help='показать столько заданий банка без прототипа')
    ap.add_argument('--export-protos', help='собрать data/source/math-prototypes.json')
    ap.add_argument('--review-dump', help='материал для экзаменационной проверки (локально, не коммитить)')
    args = ap.parse_args()
    if args.review_dump:
        review_dump(args.review_dump, args.fipi)
        return 0
    if args.export_protos:
        export_protos(args.export_protos, args.fipi)
        return 0
    if args.protos:
        return protos_main(args)
    if args.export:
        export(args.export)
        return 0
    allc = []
    print(f'{"генератор":<18}{"экз.":<14}{"№":>3} {"готово":>7} {"попыток":>8} {"отсев":>6} {"повт.":>6} {"сбой":>5} {"ёмкость":>8} {"ответов":>8}')
    total_fail = 0
    for gid, g in GEN.items():
        if args.only and gid != args.only:
            continue
        cards, info = run(gid, args.n)
        st = info['stats']
        fail = st.get('ОТВЕТ НЕ СОШЁЛСЯ', 0) + sum(v for k, v in st.items() if k.startswith('ошибка'))
        total_fail += fail
        cap = f'{info["capacity"]}{"+" if info["capacity"] >= 3000 else ""}'
        print(f'{gid:<18}{g["exam"]:<14}{g["n"]:>3} {len(cards):>7} {info["tries"]:>8} {st.get("отсеяно", 0):>6} '
              f'{st.get("повтор", 0):>6} {fail:>5} {cap:>8} {info["distinct_answers"]:>8}')
        if args.sample:
            for c in cards[:2]:
                print('   ', json.dumps(c, ensure_ascii=False))
        allc += cards
    print(f'Итого карточек: {len(allc)}, несошедшихся ответов: {total_fail}')
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as fh:
            json.dump(allc, fh, ensure_ascii=False, indent=1)
    return 1 if total_fail else 0


if __name__ == '__main__':
    sys.exit(main())
