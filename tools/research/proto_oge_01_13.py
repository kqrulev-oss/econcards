"""Прототипы ОГЭ по математике, задания 1–13 (часть 1).

№1–5 — практико-ориентированный блок с общим сюжетом. В экзамене пять вопросов идут
к одному тексту; у нас каждая позиция блока — отдельный прототип: карточка несёт краткое
общее вводное (свой сюжет, свои числа) и один вопрос. Сюжеты придуманы заново по той же
математической схеме, что и в открытом банке (маркировка изделий, план участка/квартиры
на клетчатой бумаге, форматы листов, тарифы и т. п.).
№6–13 — вычисления, числовая прямая, степени и корни, уравнения, вероятность, графики,
расчёт по формуле, неравенства.

Тексты ФИПИ сюда не попадают: формулировки свои, регулярки fipi служат только для подсчёта
покрытия банка при самопроверке.
"""
import math
import re

from mathlib import (F, R, X, _svg, BLUE, RED, INK, GRID, finite, ftxt, nice, num, par, pcard, pick, plural,
                     poly, proto, proto_llm, raz, same, signed, sp, svg_cells, svg_plot, tnum, lin)

# ================================================================ общие помощники


def approx(x, nd=2):
    """Приближённое значение с десятичной запятой: 0,56."""
    return f'{float(x):.{nd}f}'.replace('.', ',').replace('-', '−')


def fr(x):
    """Обыкновенная дробь в условии: 7/12, −3/4, целое — числом."""
    x = F(x)
    if x.denominator == 1:
        return tnum(x)
    return f'{"−" if x < 0 else ""}{abs(x.numerator)}/{x.denominator}'


def mixed(x):
    """Смешанное число: 2 3/4 (x > 0)."""
    x = F(x)
    w = x.numerator // x.denominator
    rest = x - w
    if w == 0:
        return fr(x)
    if rest == 0:
        return str(w)
    return f'{w} {rest.numerator}/{rest.denominator}'


def parse(txt):
    """Выражение из текста условия → sympy (независимая проверка: считаем то, что видит ученик).
    Понимает −, ·, :, десятичную запятую, √(…) и √n, ², ³, ^{k}, смешанные числа «2 3/4»."""
    s = txt.replace('⟦', '').replace('⟧', '').replace('−', '-').replace('·', '*').replace(':', '/')
    s = re.sub(r'(\d),(\d)', r'\1.\2', s)
    s = re.sub(r'(?<![\d.])(\d+) (\d+)/(\d+)', r'(\1+\2/\3)', s)
    s = re.sub(r'(?<![\d./])(\d+)/(\d+)(?![\d.])', r'(\1/\2)', s)
    s = s.replace('²', '**2').replace('³', '**3')
    s = re.sub(r'\^\{([^}]*)\}', r'**(\1)', s)
    s = re.sub(r'\^\(([^)]*)\)', r'**(\1)', s)
    s = re.sub(r'\^(-?\d+)', r'**(\1)', s)
    s = re.sub(r'√(\d+(?:\.\d+)?)', r'sqrt(\1)', s)
    s = s.replace('√', 'sqrt')
    s = re.sub(r'(\d|\))\s*(sqrt|\()', r'\1*\2', s)
    s = re.sub(r'(\d|\))\s*([a-z])(?!qrt)', r'\1*\2', s)
    return sp.sympify(s, rational=True)


def opts(r, items, right=0):
    """Варианты ответа k='one': items — тексты, right — индекс верного. → (o, a)."""
    order = list(range(len(items)))
    r.shuffle(order)
    o = [{'id': str(i + 1), 't': items[j]} for i, j in enumerate(order)]
    return o, str(order.index(right) + 1)


def fixed_opts(items, right):
    o = [{'id': str(i + 1), 't': t} for i, t in enumerate(items)]
    return o, str(right + 1)


ASK = ('Найдите значение выражения', 'Вычислите', 'Найдите значение выражения', 'Вычислите значение выражения')
LET = 'АБВГ'


def K(level='Б', minutes=2, kes=(), kt=(), answer='число', style=''):
    return {'level': level, 'points': 1, 'minutes': minutes, 'kes': list(kes), 'kt': [f'КТ {k}' for k in kt],
            'answer': answer, 'style': style}


# ================================================================ SVG: числовая прямая, панели графиков


def svg_numline(lo, hi, ticks=(), labels=(), points=(), width=360, height=56, step_label=None):
    """Координатная прямая. ticks — значения штрихов, labels — [(value, 'текст')] под прямой,
    points — [(value, 'A')] точки с подписью над прямой."""
    L, Rr = 16, width - 16
    sx = lambda v: L + (float(v) - lo) / (hi - lo) * (Rr - L)
    y = height - 26
    out = f'<line x1="{L - 8}" y1="{y}" x2="{Rr + 10}" y2="{y}" stroke="{INK}" stroke-width="1.4" marker-end="url(#a)"/>'
    for t in ticks:
        out += f'<line x1="{sx(t):.1f}" y1="{y - 5}" x2="{sx(t):.1f}" y2="{y + 5}" stroke="{INK}" stroke-width="1.2"/>'
    for v, t in labels:
        out += f'<text x="{sx(v):.1f}" y="{y + 19}" text-anchor="middle">{t}</text>'
    for v, t in points:
        out += (f'<circle cx="{sx(v):.1f}" cy="{y}" r="3.6" fill="{RED}"/>'
                f'<text x="{sx(v):.1f}" y="{y - 10}" text-anchor="middle" font-size="13" font-style="italic">{t}</text>')
    return _svg(width, height, out)


def svg_rays(rows, width=340):
    """Несколько координатных прямых с заштрихованными промежутками (варианты №13).
    rows — [(номер, [(a, b, a_closed, b_closed)], [(value, 'подпись')], lo, hi)]; a/b = None — бесконечность."""
    h_row = 52
    H = h_row * len(rows) + 6
    out = ''
    for k, (nm, ivs, marks, lo, hi) in enumerate(rows):
        y = 30 + k * h_row
        L, Rr = 34, width - 14
        sx = lambda v: L + (float(v) - lo) / (hi - lo) * (Rr - L)
        out += f'<text x="4" y="{y + 4}" font-size="13">{nm})</text>'
        for a, b, ca, cb in ivs:
            xa = L - 4 if a is None else sx(a)
            xb = Rr + 2 if b is None else sx(b)
            # штриховка над прямой
            out += f'<rect x="{xa:.1f}" y="{y - 12}" width="{xb - xa:.1f}" height="12" fill="{BLUE}" fill-opacity="0.18"/>'
            hx = xa - (xa - L) % 8
            while hx < xb:
                x1, x2 = max(hx, xa), min(hx + 8, xb)
                out += f'<line x1="{x1:.1f}" y1="{y}" x2="{x2:.1f}" y2="{y - 12 * (x2 - x1) / 8:.1f}" stroke="{BLUE}" stroke-width="1"/>'
                hx += 8
        out += f'<line x1="{L - 6}" y1="{y}" x2="{Rr + 8}" y2="{y}" stroke="{INK}" stroke-width="1.4" marker-end="url(#a)"/>'
        ends = {}
        for a, b, ca, cb in ivs:
            if a is not None:
                ends[a] = ca
            if b is not None:
                ends[b] = cb
        for v, t in marks:
            out += f'<text x="{sx(v):.1f}" y="{y + 18}" text-anchor="middle">{t}</text>'
            if v in ends:
                fill = INK if ends[v] else '#fff'
                out += f'<circle cx="{sx(v):.1f}" cy="{y}" r="4" fill="{fill}" stroke="{INK}" stroke-width="1.5"/>'
            else:
                out += f'<line x1="{sx(v):.1f}" y1="{y - 4}" x2="{sx(v):.1f}" y2="{y + 4}" stroke="{INK}"/>'
    return _svg(width, H, out)


def svg_panels(fns, names, span=4, unit=18, gap=14):
    """Несколько графиков рядом (для соответствия №11): каждая панель — клетка [−span; span]²,
    отмечены 0 и 1 на осях. fns — список функций float → float."""
    side = 2 * span * unit
    W = len(fns) * (side + gap) + gap
    H = side + 34
    out = ''
    for k, (fn, nm) in enumerate(zip(fns, names)):
        ox, oy = gap + k * (side + gap), 26
        sx = lambda x: ox + (x + span) * unit
        sy = lambda y: oy + (span - y) * unit
        out += f'<text x="{ox}" y="16" font-size="13">{nm})</text>'
        g = ''.join(f'<line x1="{sx(i)}" y1="{sy(-span)}" x2="{sx(i)}" y2="{sy(span)}"/>' for i in range(-span, span + 1))
        g += ''.join(f'<line x1="{sx(-span)}" y1="{sy(j)}" x2="{sx(span)}" y2="{sy(j)}"/>' for j in range(-span, span + 1))
        out += f'<g stroke="{GRID}" stroke-width="1">{g}</g>'
        out += (f'<line x1="{sx(-span)}" y1="{sy(0)}" x2="{sx(span)}" y2="{sy(0)}" stroke="{INK}" stroke-width="1.2" marker-end="url(#a)"/>'
                f'<line x1="{sx(0)}" y1="{sy(-span)}" x2="{sx(0)}" y2="{sy(span)}" stroke="{INK}" stroke-width="1.2" marker-end="url(#a)"/>'
                f'<text x="{sx(span) - 9}" y="{sy(0) - 5}" font-size="11">x</text><text x="{sx(0) + 5}" y="{sy(span) + 10}" font-size="11">y</text>'
                f'<text x="{sx(1) - 3}" y="{sy(0) + 13}" font-size="11">1</text><text x="{sx(0) - 10}" y="{sy(1) + 4}" font-size="11">1</text>'
                f'<text x="{sx(0) - 10}" y="{sy(0) + 13}" font-size="11">0</text>')
        segs, pts = [], []
        for i in range(401):
            x = -span + 2 * span * i / 400
            try:
                y = fn(x)
            except (ZeroDivisionError, ValueError, OverflowError):
                y = None
            if y is not None and -span - 0.6 <= y <= span + 0.6:
                pts.append(f'{sx(x):.1f},{sy(y):.1f}')
            elif pts:
                segs.append(pts)
                pts = []
        if pts:
            segs.append(pts)
        out += f'<clipPath id="p{k}"><rect x="{sx(-span)}" y="{sy(span)}" width="{side}" height="{side}"/></clipPath>'
        out += f'<g clip-path="url(#p{k})">' + ''.join(
            f'<polyline fill="none" stroke="{BLUE}" stroke-width="2.2" points="{" ".join(s)}"/>' for s in segs if len(s) > 1) + '</g>'
    return _svg(W, H, out)


# ================================================================ №6 — действия с дробями

K6 = K(minutes=2, kes=['1.2', '1.3'], kt=[3], style='«Найдите значение выражения …», ответ — число (обыкновенную дробь переводят в десятичную)')
DEN = [2, 4, 5, 8, 10, 20, 25, 3, 6, 9, 12, 15, 7, 14, 16, 40]


def _expr_card(r, ex, val, e):
    q = f'{pick(r, *ASK)} {ex}.'
    return pcard(q, num(val), e=e), lambda: same(num(val), parse(ex))


def _fr(r, dens=DEN, lo=1, hi=None):
    d = r.choice(dens)
    n = r.randint(lo, hi or 2 * d - 1)
    x = F(n, d)
    if x.denominator == 1 or x.denominator != d:
        return None
    return x


@proto('og06-frac-addsub', 'oge', 6, 'Сумма или разность обыкновенных дробей',
       invariant='Одно действие: сложение или вычитание двух обыкновенных дробей с разными знаменателями, ответ — десятичная дробь.',
       varies='Знаменатели, числители, знак действия, порядок слагаемых.',
       answer_rule='Приводим к общему знаменателю, складываем/вычитаем, переводим в десятичную.',
       fipi=r'значение выражения\s+-?\s*\d+\s+\d+\s*[+−-]\s*\d+\s+\d+\s*\.?\s*Ответ',
       mistakes=['складывают числители и знаменатели', 'ошибка при переводе в десятичную'], kim=K6)
def gen_og06_frac_addsub(r):
    a, b = _fr(r), _fr(r)
    if not a or not b or a.denominator == b.denominator:
        return None
    op = r.choice('+−')
    val = a + b if op == '+' else a - b
    if not nice(val, 2) or val == 0:
        return None
    ex = f'{fr(a)} {op} {fr(b)}'
    return _expr_card(r, ex, val, f'Общий знаменатель {(a + b).denominator if op == "+" else (a - b).denominator}: {ex} = {fr(val)} = {tnum(val)}.')


@proto('og06-frac-brackets', 'oge', 6, 'Скобка с дробями, умноженная (делённая) на число',
       invariant='Сумма или разность двух дробей в скобках умножается на целое число или делится на дробь.',
       varies='Дроби, множитель/делитель, знак в скобках, порядок записи (множитель слева или справа).',
       answer_rule='Сначала действие в скобках, затем умножение (деление); результат в десятичной записи.',
       fipi=r'\(\s*\d+\s+\d+\s*[+−-]\s*\d+\s+\d+\s*\)\s*[·⋅:]|[·⋅:]\s*\(\s*\d+\s+\d+\s*[+−-]',
       mistakes=['умножают только одно слагаемое', 'делят вместо умножения на обратную'], kim=K6)
def gen_og06_frac_brackets(r):
    a, b = _fr(r), _fr(r)
    if not a or not b or a.denominator == b.denominator:
        return None
    op = r.choice('+−')
    s = a + b if op == '+' else a - b
    if r.random() < 0.6:
        m = r.randint(2, 60)
        val = s * m
        ex = f'({fr(a)} {op} {fr(b)}) · {m}' if r.random() < 0.5 else f'{m} · ({fr(a)} {op} {fr(b)})'
    else:
        m = _fr(r, [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 25])
        if not m:
            return None
        val = s / m
        ex = f'({fr(a)} {op} {fr(b)}) : {fr(m)}'
    if not nice(val, 2) or val == 0 or abs(val) > 200 or s.denominator == 1:
        return None
    return _expr_card(r, ex, val, f'В скобках {fr(s)}; дальше {ex.split(")")[-1].strip() or "умножение"} → {tnum(val)}.')


@proto('og06-frac-muldiv', 'oge', 6, 'Произведение или частное дробей',
       invariant='Умножение/деление обыкновенных дробей или смешанных чисел (одно-два действия без сложения).',
       varies='Дроби (в т. ч. смешанные числа), порядок действий, знак действия.',
       answer_rule='Смешанные числа → неправильные дроби, сокращаем, делим как умножение на обратную.',
       fipi=r'\d+\s+\d+\s*[·⋅:]\s*\d+\s+\d+\s*\.?\s*Ответ',
       mistakes=['при делении не переворачивают делитель', 'ошибка при переводе смешанного числа'], kim=K6)
def gen_og06_frac_muldiv(r):
    a = F(r.randint(1, 40), r.randint(2, 16))
    b = F(r.randint(1, 40), r.randint(2, 16))
    if a.denominator == 1 or b.denominator == 1:
        return None
    op = r.choice(['·', ':'])
    val = a * b if op == '·' else a / b
    if not nice(val, 2) or val.denominator == 1 and r.random() < 0.5:
        return None
    w = mixed if r.random() < 0.5 else fr
    ex = f'{w(a)} {op} {w(b)}'
    return _expr_card(r, ex, val, f'{fr(a)} {op} {fr(b)} = {fr(val)} = {tnum(val)}.')


@proto('og06-frac-reciprocal', 'oge', 6, 'Единица, делённая на сумму дробей',
       invariant='Выражение вида 1 / (1/a ± 1/b) или c / (1/a + 1/b): многоэтажная дробь.',
       varies='Знаменатели a, b (с общим множителем), числитель, знак.',
       answer_rule='Считаем знаменатель как сумму дробей, затем делим на неё.',
       fipi=r'1\s+1\s+1\s+\d+\s+\d+\s*[+−-]|значение выражения\s+1\s+1\s+\d+',
       mistakes=['считают 1/(1/a+1/b) = a + b', 'ошибка в общем знаменателе'], kim=K6)
def gen_og06_frac_reciprocal(r):
    g = r.randint(2, 15)
    p, q_ = r.sample(range(1, 10), 2)
    a, b = g * p, g * q_
    op = r.choice('+−') if a > b else '+'
    c = r.choice([1, 1, 1, 2, 3])
    den = F(1, a) + F(1, b) if op == '+' else F(1, a) - F(1, b)
    if den <= 0 or a > 120 or b > 120:
        return None
    val = c / den
    if not nice(val, 2):
        return None
    ex = f'{c} : (1/{a} {op} 1/{b})'
    q = f'{pick(r, *ASK)} ⟦{c} / (1/{a} {op} 1/{b})⟧.'
    return pcard(q, num(val), e=f'1/{a} {op} 1/{b} = {fr(den)}; {c} : {fr(den)} = {tnum(val)}.'), lambda: same(num(val), parse(ex))


@proto('og06-frac-complex', 'oge', 6, 'Дробь, делённая на сумму дробей',
       invariant='Частное: обыкновенная (или десятичная) дробь делится на сумму/разность двух дробей, или сумма — на дробь.',
       varies='Все дроби, место суммы (в числителе или знаменателе).',
       answer_rule='Считаем сумму, затем делим; ответ — десятичная дробь.',
       fipi=r'\d+\s+\d+\s+\d+\s+\d+\s*[+−-]\s*\d+\s+\d+\s*\.?\s*Ответ',
       mistakes=['делят почленно', 'путают числитель и знаменатель'], kim=K6)
def gen_og06_frac_complex(r):
    b = F(r.randint(1, 8), r.randint(2, 9))
    c = F(r.randint(1, 8), r.randint(2, 9))
    if b.denominator == 1 or c.denominator == 1 or b.denominator == c.denominator or b == c:
        return None
    op = r.choice('+−')
    s = b + c if op == '+' else b - c
    if s <= 0 or s.denominator > 40:
        return None
    val = F(r.choice([1, 2, 3, 4, 5, 6, 8, 12, 15, 25]), r.choice([1, 2, 4, 5, 10]))
    top = r.random() < 0.5
    a = val * s if top else s / val
    if a.denominator == 1 or a.numerator > 60 or a.denominator > 60:
        return None
    if top:
        ex, q_ex = f'{fr(a)} : ({fr(b)} {op} {fr(c)})', f'⟦({fr(a)}) / ({fr(b)} {op} {fr(c)})⟧'
    else:
        ex, q_ex = f'({fr(b)} {op} {fr(c)}) : {fr(a)}', f'⟦({fr(b)} {op} {fr(c)}) / ({fr(a)})⟧'
    q = f'{pick(r, *ASK)} {q_ex}.'
    return pcard(q, num(val), e=f'{fr(b)} {op} {fr(c)} = {fr(s)}; дальше деление: {tnum(val)}.'), lambda: same(num(val), parse(ex))


@proto('og06-mixed', 'oge', 6, 'Действия со смешанными числами',
       invariant='Сумма/разность смешанных чисел, затем умножение или деление на число.',
       varies='Смешанные числа, множитель, знаки.',
       answer_rule='Переводим в неправильные дроби (или складываем целые и дробные части), затем умножаем.',
       fipi=r'\(\s*\d+\s+\d+\s+\d+\s*[+−-]\s*\d+\s+\d+\s+\d+\s*\)',
       mistakes=['теряют целую часть при вычитании с «занимом»'], kim=K6)
def gen_og06_mixed(r):
    a = r.randint(1, 6) + F(r.randint(1, 9), r.choice([2, 3, 4, 5, 6, 8, 10]))
    b = r.randint(1, 4) + F(r.randint(1, 9), r.choice([2, 3, 4, 5, 6, 8, 10]))
    if a.denominator == 1 or b.denominator == 1 or a.denominator == b.denominator or a - int(a) == 0 or b - int(b) == 0:
        return None
    op = r.choice('+−')
    s = a + b if op == '+' else a - b
    m = r.choice([2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 24, 30])
    if s <= 0:
        return None
    if r.random() < 0.5:
        val, ex = s * m, f'({mixed(a)} {op} {mixed(b)}) · {m}'
    else:
        val, ex = s / m, f'({mixed(a)} {op} {mixed(b)}) : {m}'
    if not nice(val, 2) or a.numerator // a.denominator == 0:
        return None
    return _expr_card(r, ex, val, f'{mixed(a)} {op} {mixed(b)} = {fr(s)}; {ex.split(")")[-1].strip()} → {tnum(val)}.')


@proto('og06-dec-two', 'oge', 6, 'Десятичные дроби: два действия',
       invariant='Выражение с десятичными дробями: (a ± b)·c, a·b ± c или a − b·c; порядок действий.',
       varies='Числа (десятые/сотые, разные знаки), схема выражения.',
       answer_rule='Соблюдаем порядок действий: сначала скобки и умножение, потом сложение.',
       fipi=r'\d,\d+\s*[·⋅]\s*\(?\s*[−-]?\s*\d+,\d|\(\s*\d+,\d+\s*[+−-]\s*\d+,\d+\s*\)\s*[·⋅]',
       mistakes=['выполняют действия слева направо без приоритета', 'ошибка в знаке при умножении отрицательных'], kim=K6)
def gen_og06_dec_two(r):
    d = lambda lo, hi: F(r.randint(lo, hi), 10) * r.choice([1, 1, -1])
    a, b, c = d(3, 99), d(3, 99), d(2, 60)
    if a.denominator == 1 or b.denominator == 1 or c.denominator == 1:
        return None
    kind = r.randrange(3)
    if kind == 0:
        b = abs(b)
        op = r.choice('+−')
        val = (a + b if op == '+' else a - b) * c
        ex = f'({tnum(a)} {op} {tnum(b)}) · {par(c)}'
    elif kind == 1:
        op = r.choice('+−')
        c = abs(c)
        val = a * b + c if op == '+' else a * b - c
        ex = f'{tnum(a)} · {par(b)} {op} {tnum(c)}'
    else:
        b, c = abs(b), abs(c)
        val = a - b * c
        ex = f'{tnum(a)} − {tnum(b)} · {tnum(c)}'
    if not nice(val, 2) or val == 0:
        return None
    return _expr_card(r, ex, val, f'Порядок действий: {ex} = {tnum(val)}.')


@proto('og06-dec-frac', 'oge', 6, 'Дробь с десятичными числами',
       invariant='Частное: в числителе и/или знаменателе произведение или сумма десятичных дробей.',
       varies='Числа, место произведения/суммы.',
       answer_rule='Считаем числитель и знаменатель отдельно и делим (удобно сократить на общие множители).',
       fipi=r'значение выражения\s+\d+,\d+\s+\d+,\d+\s*[·⋅+−-]\s*\d+,\d+|\d+,\d+\s*[·⋅]\s*\d+,\d+\s+\d+,\d+',
       mistakes=['делят только на один множитель знаменателя', 'ошибка с запятой при делении'], kim=K6)
def gen_og06_dec_frac(r):
    b, c = F(r.randint(2, 60), 10), F(r.randint(2, 40), 10)
    if b.denominator == 1 or c.denominator == 1:
        return None
    val = F(r.randint(1, 40), r.choice([1, 2, 4, 5, 10]))
    kind = r.randrange(3)
    if kind == 0:
        a = val * b * c
        if not nice(a, 2) or a.denominator == 1 or a > 100:
            return None
        ex, q_ex = f'{tnum(a)} : ({tnum(b)} · {tnum(c)})', f'⟦{tnum(a)} / ({tnum(b)} · {tnum(c)})⟧'
    elif kind == 1:
        a = val * c / b
        if not nice(a, 1) or a > 100:
            return None
        ex, q_ex = f'({tnum(a)} · {tnum(b)}) : {tnum(c)}', f'⟦({tnum(a)} · {tnum(b)}) / {tnum(c)}⟧'
    else:
        s = val * c
        a = F(r.randint(1, int(s * 10) + 1), 10) if s > F(1, 5) else None
        if not a or a >= s or not nice(s - a, 1) or s > 30:
            return None
        b = s - a
        ex, q_ex = f'({tnum(a)} + {tnum(b)}) : {tnum(c)}', f'⟦({tnum(a)} + {tnum(b)}) / {tnum(c)}⟧'
    if not nice(val, 2):
        return None
    q = f'{pick(r, *ASK)} {q_ex}.'
    return pcard(q, num(val), e=f'{ex} = {tnum(val)}.'), lambda: same(num(val), parse(ex))


@proto('og06-pow-neg', 'oge', 6, 'Выражение со степенями отрицательного числа',
       invariant='Многочлен от числа (−10), (−1) или десятичного числа: a·(−10)³ + b·(−10)² + c; знаки степеней.',
       varies='Коэффициенты (десятичные), основание, показатели.',
       answer_rule='Возводим в степень с учётом знака (чётная — плюс), умножаем, складываем.',
       fipi=r'\(\s*[−-]\s*10\s*\)|\(\s*[−-]\s*1\s*\)\s*\d',
       mistakes=['(−10)² считают отрицательным', 'путают (−10)³ и −10³'], kim=K6)
def gen_og06_pow_neg(r):
    base = r.choice([-10, -10, -10, -1, F(-1, 2), F(-1, 10)])
    k = r.choice([2, 3, 4]) if base == -10 else r.choice([2, 3, 4, 5])
    c1 = F(r.randint(1, 99), r.choice([10, 100] if base == -10 else [1])) * r.choice([1, -1])
    c2 = F(r.randint(1, 9), r.choice([1, 1, 10])) * r.choice([1, -1])
    c3 = r.randint(-99, 99) if r.random() < 0.8 else 0
    kk = [k, k - 1] if r.random() < 0.6 else [k]
    P = lambda e: F(base) ** e
    val = c1 * P(kk[0]) + (c2 * P(kk[1]) if len(kk) > 1 else 0) + c3
    if not nice(val, 2) or abs(val) > 9999:
        return None
    B = f'({tnum(base) if F(base).denominator == 1 else fr(base)})'
    pw = lambda e: B if e == 1 else f'{B}^{{{e}}}'
    ex = f'{tnum(c1)} · {pw(kk[0])}'
    if len(kk) > 1:
        ex += f'{signed(c2)} · {pw(kk[1])}'
    if c3:
        ex += signed(c3)
    q = f'{pick(r, *ASK)} ⟦{ex}⟧.'
    e = '; '.join(f'{B}^{e_} = {ftxt(P(e_))}' for e_ in kk if e_ > 1) + f'; итого {tnum(val)}.'
    return pcard(q, num(val), e=e), lambda: same(num(val), parse(ex))


@proto('og06-frac-dec-mix', 'oge', 6, 'Обыкновенная и десятичная дробь в одном выражении',
       invariant='В выражении есть и обыкновенная, и десятичная дробь (сумма, произведение); удобно перейти к одному виду.',
       varies='Дроби, десятичные числа, действия.',
       answer_rule='Переводим обыкновенную дробь в десятичную (или наоборот) и считаем.',
       fipi=r'\d+\s+\d+\s*[+−-·⋅:]\s*\d+,\d+|\d+,\d+\s*[+−-·⋅:]\s*\d+\s+\d+\s*\.?\s*Ответ',
       mistakes=['неверный перевод 3/8 в десятичную'], kim=K6)
def gen_og06_frac_dec_mix(r):
    a = _fr(r, [2, 4, 5, 8, 20, 25, 3, 6, 7, 9, 12, 15])
    b = F(r.randint(1, 99), r.choice([10, 100])) * r.choice([1, 1, -1])
    c = r.choice([2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 40])
    if not a or b.denominator == 1:
        return None
    kind = r.randrange(3)
    if kind == 0:
        val, ex = (a + b) * c, f'({fr(a)} {signed(b).strip()}) · {c}'
    elif kind == 1:
        val, ex = a * c + b, f'{fr(a)} · {c} {signed(b).strip()}'
    else:
        val, ex = a * b, f'{fr(a)} · {par(b)}'
    if not nice(val, 2) or val == 0:
        return None
    return _expr_card(r, ex, val, f'{fr(a)} = {tnum(a) if finite(a) else fr(a)}; {ex} = {tnum(val)}.')


# ================================================================ №7 — числа на координатной прямой

K7 = K(minutes=2, kes=['1.4', '6.1'], kt=[3], answer='цифра варианта',
       style='Выбор одного из четырёх вариантов «1) … 4)», в ответ — номер (как в КИМ ОГЭ №7)')
TAIL7 = ('В ответе укажите номер правильного варианта.', 'Запишите в ответ номер выбранного варианта.', '')


def _q7(r, q):
    t = pick(r, *TAIL7)
    return f'{q} {t}'.strip()


def _int_line(lo, hi, pts):
    return svg_numline(lo - 0.6, hi + 0.6, ticks=range(lo, hi + 1), labels=[(i, tnum(i)) for i in range(lo, hi + 1)], points=pts)


@proto('og07-point-frac', 'oge', 7, 'Какое число отмечено точкой (дроби на отрезке с делениями 0,1)',
       invariant='На прямой отрезок с делениями по 0,1 и точка; среди четырёх дробей с одним знаменателем выбрать ту, что отмечена.',
       varies='Знаменатель, числители, положение отрезка на прямой, буква точки.',
       answer_rule='Переводим дроби в десятичные (прикидка до десятых) и сравниваем с положением точки.',
       fipi=r'отмечено на (координатной|числовой) прямой точкой|Одно из чисел .{0,60}отмечено',
       mistakes=['путают числитель и знаменатель при оценке', 'не учитывают целую часть неправильной дроби'],
       svg=True, card_kind='one', kim=K7)
def gen_og07_point_frac(r):
    n = r.choice([0, 0, 1, 2, 3])
    d = r.choice([3, 6, 7, 9, 11, 12, 13, 14, 15, 17, 18, 19, 21, 22, 23])
    inside = [m for m in range(n * d + 1, (n + 1) * d) if math.gcd(m, d) == 1]
    ok = [m for m in inside if 0.025 < (F(m, d) * 10) % 1 < 0.975]
    if len(ok) < 2:
        return None
    m = r.choice(ok)
    t = F(m, d)
    near = [x for x in inside if x != m and abs(F(x, d) - t) >= F(12, 100) and math.gcd(x, d) == 1]
    far = [x for x in range(max(1, (n - 1) * d), (n + 2) * d) if (x < n * d or x > (n + 1) * d) and math.gcd(x, d) == 1]
    if not near or len(far) < 2:
        return None
    dis = r.sample(near, 1) + r.sample(far, 2) if r.random() < 0.5 or len(near) < 2 else r.sample(near, 2) + r.sample(far, 1)
    vals = sorted([m] + dis)
    items = [f'{v}/{d}' for v in vals]
    o, a = fixed_opts(items, vals.index(m))
    letter = r.choice('ABCKMP')
    ticks = [n + F(i, 10) for i in range(11)]
    svg = svg_numline(n - F(1, 20), n + 1 + F(1, 20), ticks=ticks, labels=[(v, tnum(v)) for v in ticks[::2]] if n else [(v, tnum(v)) for v in ticks[::2]],
                      points=[(t, letter)])
    q = _q7(r, pick(r, f'Одно из чисел {", ".join(items[:-1])} и {items[-1]} отмечено на координатной прямой точкой {letter}. Какое это число?',
                    f'Точкой {letter} на координатной прямой отмечено одно из чисел: {"; ".join(items)}. Определите, какое именно.',
                    f'На координатной прямой точкой {letter} отмечено одно из четырёх чисел, записанных ниже. Какое?'))
    e = f'{m}/{d} ≈ {approx(t)} — лежит между {tnum(n + F(int(float(t - n) * 10), 10))} и {tnum(n + F(int(float(t - n) * 10) + 1, 10))}, как точка {letter}.'
    return pcard(q, a, e=e, k='one', o=o, svg=svg), lambda: abs(sp.Rational(m, d) - R(t)) == 0 and all(
        abs(sp.Rational(v, d) - R(t)) >= sp.Rational(1, 10) for v in dis)


def _roots_pool(lo, hi):
    """Числа вида √n, лежащие в (lo, hi), без целых."""
    return [nn for nn in range(max(2, lo * lo + 1), hi * hi) if int(math.isqrt(nn)) ** 2 != nn]


@proto('og07-point-number', 'oge', 7, 'Какая из точек соответствует данному числу (корень или дробь)',
       invariant='На прямой с подписанными целыми точками A, B, C, D; одна соответствует числу √n (или дроби p/q); найти какая.',
       varies='Число (корень, неправильная дробь, со знаком минус), положение точек, подписанные целые.',
       answer_rule='Оцениваем число между соседними целыми (через квадраты) и выбираем ближайшую точку по положению в промежутке.',
       fipi=r'Одна из них соответствует числу|соответствует числу',
       mistakes=['не различают положение в левой и правой половине промежутка', 'путают √n и n/2'],
       svg=True, card_kind='one', kim=K7)
def gen_og07_point_number(r):
    kind = r.choice(['sqrt', 'sqrt', 'frac', 'negsqrt'])
    k = r.randint(2, 11) if kind != 'frac' else r.randint(1, 9)
    if kind == 'frac':
        d = r.choice([3, 6, 7, 9, 11, 12, 13])
        m = r.randint(k * d + 1, (k + 1) * d - 1)
        if math.gcd(m, d) != 1:
            return None
        v = F(m, d)
        txt, val = f'{m}/{d}', R(v)
    else:
        nn = r.choice(_roots_pool(k, k + 1))
        v = F(round(math.sqrt(nn) * 10000), 10000)
        txt, val = f'√{nn}', sp.sqrt(nn)
        if kind == 'negsqrt':
            v, txt, val = -v, f'−√{nn}', -sp.sqrt(nn)
    base = math.floor(v)
    fracp = float(v - base)
    if not 0.12 < fracp < 0.88 or abs(fracp - 0.5) < 0.12:
        return None
    lo, hi = base - 1, base + 2
    cand = [F(x, 10) + lo for x in range(3, 30)]
    cand = [c for c in cand if abs(float(c - v)) > 0.35 and abs(float(c) - round(float(c))) > 0.12]
    same_seg = [c for c in cand if base < c < base + 1]
    other = [c for c in cand if not base < c < base + 1]
    if not same_seg or len(other) < 2:
        return None
    ds = r.sample(same_seg, 1) + r.sample(other, 2)
    pts = sorted([v] + ds)
    if min(b - a for a, b in zip(pts, pts[1:])) < F(3, 10):
        return None
    names = 'ABCD'
    right = pts.index(v)
    svg = _int_line(lo, hi, [(p, names[i]) for i, p in enumerate(pts)])
    o, a = fixed_opts([f'точка {c}' for c in names], right)
    q = _q7(r, pick(r, f'На координатной прямой отмечены точки A, B, C и D. Одна из них изображает число {txt}. Какая?',
                    f'Числу {txt} на координатной прямой соответствует одна из отмеченных точек A, B, C, D. Укажите её.',
                    f'Какая из точек A, B, C, D, отмеченных на координатной прямой, соответствует числу {txt}?'))
    e = f'{txt} ≈ {approx(v)}: между {base} и {base + 1}, {"ближе к " + str(base + 1) if fracp > 0.5 else "ближе к " + str(base)} — это точка {names[right]}.'
    pos = [R(p) for p in pts]
    return pcard(q, a, e=e, k='one', o=o, svg=svg), lambda: min(range(4), key=lambda i: abs(sp.N(pos[i] - val))) == right


@proto('og07-sqrt-estimate', 'oge', 7, 'Оценка квадратного корня между целыми числами',
       invariant='Сравнение √n (или a√b) с целыми числами через квадраты: между какими целыми лежит число, или какое число лежит на промежутке.',
       varies='Подкоренное число, вид вопроса (промежуток для числа / число для промежутка), множитель перед корнем.',
       answer_rule='Сравниваем квадраты: k² < n < (k+1)² ⇒ k < √n < k+1; a√b = √(a²b).',
       fipi=r'(между какими|заключено|принадлежит (отрезку|промежутку)).{0,80}√|√.{0,60}(заключено|принадлежит)',
       mistakes=['делят подкоренное число на 2 вместо извлечения корня', 'забывают внести множитель под корень'],
       card_kind='one', kim=K7)
def gen_og07_sqrt_estimate(r):
    if r.random() < 0.5:
        coef = r.choice([1, 1, 1, 2, 3])
        if coef == 1:
            nn = r.randint(8, 200)
            txt, val = f'√{nn}', sp.sqrt(nn)
        else:
            b = r.choice([2, 3, 5, 6, 7, 10, 11])
            nn = coef * coef * b
            txt, val = f'{coef}√{b}', coef * sp.sqrt(b)
        if math.isqrt(nn) ** 2 == nn:
            return None
        k = math.isqrt(nn)
        starts = sorted({k, k - 1, k + 1, k - 2, k + 2} - {0})
        wrong = [s for s in starts if s != k]
        r.shuffle(wrong)
        items_v = sorted([k] + wrong[:3])
        items = [f'{s} и {s + 1}' for s in items_v]
        o, a = fixed_opts(items, items_v.index(k))
        q = _q7(r, pick(r, f'Между какими двумя последовательными целыми числами заключено число {txt}?',
                        f'Число {txt} лежит между двумя соседними натуральными числами. Какими?',
                        f'Укажите два соседних целых числа, между которыми находится число {txt}.'))
        e = (f'{txt} = √{nn}; ' if coef > 1 else '') + f'{k}² = {k * k} < {nn} < {(k + 1) ** 2} = {k + 1}², значит {k} < {txt} < {k + 1}.'
        return pcard(q, a, e=e, k='one', o=o), lambda: sp.floor(val) == items_v[int(a) - 1]
    k = r.randint(3, 12)
    good = _roots_pool(k, k + 1)
    nn = r.choice(good)
    bad = [x for x in range((k - 1) ** 2 + 1, (k + 2) ** 2) if math.isqrt(x) ** 2 != x and not k * k < x < (k + 1) ** 2]
    ws = r.sample(bad, 3)
    vals = sorted([nn] + ws)
    items = [f'√{x}' for x in vals]
    o, a = fixed_opts(items, vals.index(nn))
    q = _q7(r, pick(r, f'Какое из чисел принадлежит промежутку [{k}; {k + 1}]?',
                    f'Какое из данных чисел заключено между числами {k} и {k + 1}?',
                    f'Укажите число, которое больше {k}, но меньше {k + 1}.'))
    e = f'{k}² = {k * k}, {k + 1}² = {(k + 1) ** 2}; между ними только {nn}.'
    return pcard(q, a, e=e, k='one', o=o), lambda: bool(k < sp.sqrt(vals[int(a) - 1]) < k + 1) and sum(bool(k < sp.sqrt(x) < k + 1) for x in vals) == 1


@proto('og07-frac-interval', 'oge', 7, 'Какому промежутку принадлежит дробь',
       invariant='Обыкновенная дробь сравнивается с десятичными границами промежутков (или выбирается дробь из промежутка).',
       varies='Дробь, шаг промежутков (0,1 или 1), направление вопроса.',
       answer_rule='Делим числитель на знаменатель до нужного знака и находим промежуток.',
       fipi=r'(какому из|каком из).{0,30}промежутк|принадлежит (промежутку|отрезку).{0,40}\d+\s+\d+',
       mistakes=['округляют дробь не в ту сторону', 'путают границы промежутка'], card_kind='one', kim=K7)
def gen_og07_frac_interval(r):
    d = r.choice([3, 6, 7, 9, 11, 12, 13, 14, 17, 19, 21, 23, 27])
    if r.random() < 0.5:
        m = r.randint(1, d - 1)
        v = F(m, d)
        if math.gcd(m, d) != 1:
            return None
        k = int(v * 10)
        if (v * 10) % 1 == 0:
            return None
        starts = [s for s in range(max(0, k - 2), min(10, k + 3)) if s < 10]
        if len(starts) < 4:
            return None
        starts = sorted(r.sample([s for s in starts if s != k], 3) + [k])
        items = [f'[{tnum(F(s, 10))}; {tnum(F(s + 1, 10))}]' for s in starts]
        o, a = fixed_opts(items, starts.index(k))
        txt = f'{m}/{d}'
        q = _q7(r, pick(r, f'Какому из промежутков принадлежит число {txt}?',
                        f'Укажите промежуток, которому принадлежит число {txt}.'))
        e = f'{txt} = {m} : {d} ≈ {approx(v, 3)}.'
        return pcard(q, a, e=e, k='one', o=o), lambda: F(starts[int(a) - 1], 10) <= v <= F(starts[int(a) - 1] + 1, 10)
    k = r.randint(1, 6)
    good = [m for m in range(k * d + 1, (k + 1) * d) if math.gcd(m, d) == 1]
    bad = [m for m in range((k - 1) * d + 1, (k + 2) * d) if math.gcd(m, d) == 1 and not k * d < m < (k + 1) * d]
    if not good or len(bad) < 3:
        return None
    m = r.choice(good)
    ws = r.sample(bad, 3)
    vals = sorted([m] + ws)
    items = [f'{x}/{d}' for x in vals]
    o, a = fixed_opts(items, vals.index(m))
    q = _q7(r, pick(r, f'Какое из чисел принадлежит отрезку [{k}; {k + 1}]?', f'Какое из следующих чисел заключено между {k} и {k + 1}?'))
    e = f'{k} = {k * d}/{d}, {k + 1} = {(k + 1) * d}/{d}; подходит {m}/{d}.'
    return pcard(q, a, e=e, k='one', o=o), lambda: bool(k <= sp.Rational(vals[int(a) - 1], d) <= k + 1) and sum(
        bool(k <= sp.Rational(x, d) <= k + 1) for x in vals) == 1


def _stmt_pool(a_name, c_vals):
    """Утверждения про одно число: (текст, функция знака f(a) > 0 ⇔ верно)."""
    out = []
    for c in c_vals:
        out += [(f'{a_name} − {par(c)} > 0' if c >= 0 else f'{a_name} + {tnum(-c)} > 0', lambda a, c=c: a - c),
                (f'{a_name} − {par(c)} < 0' if c >= 0 else f'{a_name} + {tnum(-c)} < 0', lambda a, c=c: c - a),
                (f'{tnum(c)} − {a_name} > 0', lambda a, c=c: c - a),
                (f'{tnum(c)} − {a_name} < 0', lambda a, c=c: a - c)]
    return out


@proto('og07-point-statement', 'oge', 7, 'Число отмечено на прямой: какое утверждение верно',
       invariant='Точка a между соседними целыми на рисунке; из четырёх неравенств вида a − c > 0, c − a < 0 выбрать верное (неверное).',
       varies='Положение точки (в т. ч. отрицательные), числа в неравенствах, вопрос «верно»/«неверно».',
       answer_rule='По рисунку k < a < k+1; определяем знак каждой разности.',
       fipi=r'(отмечено|отмечены) числ.{0,120}(верн|неверн)',
       mistakes=['путают знак разности c − a', 'ошибаются с отрицательными числами'], svg=True, card_kind='one', kim=K7)
def gen_og07_point_statement(r):
    k = r.randint(-7, 6)
    aval = k + F(r.randint(2, 8), 10)
    pool = _stmt_pool('a', [k, k + 1, k - 1, k + 2])
    want_true = r.random() < 0.75
    good = [s for s in pool if (s[1](aval) > 0) == want_true]
    bad = [s for s in pool if (s[1](aval) > 0) != want_true]
    if not good or len(bad) < 3:
        return None
    ch = r.sample(good, 1) + r.sample(bad, 3)
    if len({c[0] for c in ch}) < 4:
        return None
    o, a = opts(r, [c[0] for c in ch], 0)
    svg = _int_line(k - 1, k + 2, [(aval, 'a')])
    word = 'верно' if want_true else 'неверно'
    q = _q7(r, pick(r, f'На координатной прямой отмечено число a. Какое из утверждений относительно этого числа {word}?',
                    f'Число a отмечено на координатной прямой. Какое из приведённых неравенств {word}?',
                    f'По рисунку определите, какое из утверждений о числе a {word}.'))
    e = f'По рисунку {tnum(k)} < a < {tnum(k + 1)}. Проверяем знаки разностей: {word} «{ch[0][0]}».'
    txt = ch[0][0]
    A = sp.Symbol('a', real=True)
    rel = parse(txt.replace(' > ', '>').replace(' < ', '<').replace('a', 'a'))

    def chk():
        # все точки промежутка (k; k+1) дают одинаковую истинность
        sol = sp.solve_univariate_inequality(rel.subs(sp.Symbol('a'), A), A, relational=False)
        inside = sp.Interval.open(k, k + 1).is_subset(sol)
        outside = sp.Interval.open(k, k + 1).intersect(sol) == sp.EmptySet
        return inside if want_true else outside
    return pcard(q, a, e=e, k='one', o=o, svg=svg), chk


def _corners(ia, ib):
    return [(x, y) for x in ia for y in ib]


@proto('og07-two-points', 'oge', 7, 'Два числа на прямой: знак суммы, разности, произведения',
       invariant='На прямой отмечены числа a и b (или x и y); по их положению выбрать верное (неверное) утверждение о сумме, разности, произведении, обратных.',
       varies='Положение точек (разные знаки, одна сторона), набор утверждений, вопрос верно/неверно.',
       answer_rule='По рисунку знаем промежутки для a и b; оцениваем знак выражения на всём прямоугольнике значений.',
       fipi=r'отмечены числа\s+[a-zxy]\s+и\s+[a-zxy]|числа\s+[a-z]\s+и\s+[a-z].{0,60}(верн|неверн)',
       mistakes=['считают, что a − b > 0, если a левее', 'не учитывают знак при сравнении обратных'],
       svg=True, card_kind='one', kim=K7)
def gen_og07_two_points(r):
    na, nb = r.choice([('a', 'b'), ('x', 'y'), ('m', 'n'), ('p', 'q')])
    ka, kb = r.sample(range(-4, 4), 2)
    ia, ib = (ka, ka + 1), (kb, kb + 1)
    av, bv = ka + F(r.randint(2, 8), 10), kb + F(r.randint(2, 8), 10)
    lo, hi = min(ka, kb) - 1, max(ka, kb) + 2
    if hi - lo > 8 or 0 in (ka, kb) and False:
        return None
    S = [(f'{na} + {nb} > 0', lambda a, b: a + b), (f'{na} + {nb} < 0', lambda a, b: -(a + b)),
         (f'{na}{nb} > 0', lambda a, b: a * b), (f'{na}{nb} < 0', lambda a, b: -a * b),
         (f'{na} − {nb} > 0', lambda a, b: a - b), (f'{na} − {nb} < 0', lambda a, b: b - a),
         (f'{nb} − {na} > 0', lambda a, b: b - a),
         (f'{na}² > {nb}²', lambda a, b: a * a - b * b), (f'{na}² < {nb}²', lambda a, b: b * b - a * a)]
    if 0 not in ia and 0 not in ib and ka != -1 and kb != -1:
        S += [(f'1/{na} > 1/{nb}', lambda a, b: F(1) / a - F(1) / b), (f'1/{na} < 1/{nb}', lambda a, b: F(1) / b - F(1) / a)]
    want_true = r.random() < 0.7
    cls = []
    for t, f in S:
        vals = [f(F(x), F(y)) for x, y in _corners(ia, ib) if x != 0 and y != 0 or '1/' not in t]
        if all(v > 0 for v in vals):
            cls.append((t, True, f))
        elif all(v < 0 for v in vals):
            cls.append((t, False, f))
    good = [c for c in cls if c[1] == want_true]
    bad = [c for c in cls if c[1] != want_true]
    if not good or len(bad) < 3:
        return None
    ch = r.sample(good, 1) + r.sample(bad, 3)
    o, a = opts(r, [c[0] for c in ch], 0)
    svg = _int_line(lo, hi, [(av, na), (bv, nb)])
    word = 'верно' if want_true else 'неверно'
    q = _q7(r, pick(r, f'На координатной прямой отмечены числа {na} и {nb}. Какое из следующих утверждений {word}?',
                    f'Числа {na} и {nb} отмечены на координатной прямой. Какое из неравенств {word}?',
                    f'По расположению чисел {na} и {nb} на координатной прямой выберите утверждение, которое {word}.'))
    e = f'По рисунку {tnum(ka)} < {na} < {tnum(ka + 1)}, {tnum(kb)} < {nb} < {tnum(kb + 1)}; {word}: «{ch[0][0]}».'
    f0 = ch[0][2]

    def chk():  # проверяем на сетке внутренних точек обоих промежутков
        grid = [F(i, 20) for i in range(1, 20)]
        res = {f0(ka + s, kb + t) > 0 for s in grid for t in grid if ka + s != 0 and kb + t != 0}
        return res == {want_true}
    return pcard(q, a, e=e, k='one', o=o, svg=svg), chk


@proto('og07-point-compare', 'oge', 7, 'Число на прямой: наибольшее (наименьшее) из выражений',
       invariant='Отмечено число a (например, между 0 и 1 или −1 и 0); выбрать наибольшее/наименьшее из a, a², 1/a, −a, a − 1 и т. п.',
       varies='Промежуток для a, набор выражений, вопрос (наибольшее/наименьшее/отрицательное).',
       answer_rule='Берём любое удобное число из промежутка (например, a = 0,5) и сравниваем; проверяем, что вывод не зависит от выбора.',
       fipi=r'(наибольш|наименьш).{0,60}(1\s*/?\s*a|a\s*2|a\s*−\s*1)|отмечено число\s+a.{0,80}(наибольш|наименьш)',
       mistakes=['считают, что квадрат всегда больше числа', 'забывают про знак'], svg=True, card_kind='one', kim=K7)
def gen_og07_point_compare(r):
    k = r.choice([0, -1, 1, -2, 2, 0, -1])
    a0 = k + F(r.randint(2, 8), 10)
    ex = [('a', lambda a: a), ('a²', lambda a: a * a), ('a³', lambda a: a ** 3), ('1/a', lambda a: 1 / a),
          ('−a', lambda a: -a), ('a − 1', lambda a: a - 1), ('a + 1', lambda a: a + 1), ('1 − a', lambda a: 1 - a),
          ('−1/a', lambda a: -1 / a), ('2a', lambda a: 2 * a)]
    four = r.sample(ex, 4)
    mode = r.choice(['max', 'min'])
    grid = [k + F(i, 40) for i in range(1, 40)]
    best = set()
    for x in grid:
        vs = [f(x) for _, f in four]
        tgt = max(vs) if mode == 'max' else min(vs)
        if vs.count(tgt) > 1:
            return None
        best.add(vs.index(tgt))
    if len(best) != 1:
        return None
    right = best.pop()
    o, a = fixed_opts([t for t, _ in four], right)
    svg = _int_line(k - 1, k + 2, [(a0, 'a')])
    word = 'наибольшее' if mode == 'max' else 'наименьшее'
    q = _q7(r, pick(r, f'На координатной прямой отмечено число a. Какое из чисел {word}?',
                    f'Число a отмечено на координатной прямой. Какое из приведённых ниже чисел {word}?',
                    f'По рисунку определите, какое из следующих чисел {word}.'))
    e = f'Возьмём, например, a = {tnum(a0)}: ' + ', '.join(f'{t} = {ftxt(f(a0))}' for t, f in four) + f'. {word.capitalize()} — {four[right][0]}.'
    A = sp.Symbol('a')
    exprs = [parse(t.replace('a', '(a)')) for t, _ in four]

    def chk():
        import random as _r
        rr = _r.Random(7)
        for _ in range(40):
            x = sp.Rational(rr.randint(1, 999), 1000) + k
            vs = [ex_.subs(sp.Symbol('a'), x) for ex_ in exprs]
            tgt = max(vs) if mode == 'max' else min(vs)
            if vs.index(tgt) != right:
                return False
        return True
    return pcard(q, a, e=e, k='one', o=o, svg=svg), chk
