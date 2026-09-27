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


SUPS = '⁰¹²³⁴⁵⁶⁷⁸⁹'
SUP = str.maketrans('0123456789-−', SUPS + '⁻⁻')
UNSUP = {c: str(i) for i, c in enumerate(SUPS)} | {'⁻': '-'}


def sup(n):
    """Показатель степени верхним индексом: sup(-3) → '⁻³'."""
    return str(n).translate(SUP)


def parse(txt):
    """Выражение из текста условия → sympy (независимая проверка: считаем то, что видит ученик).
    Понимает −, ·, :, десятичную запятую, √(…) и √n, ², ³, ^{k}, смешанные числа «2 3/4»."""
    s = txt.replace('⟦', '').replace('⟧', '').replace('−', '-').replace('·', '*').replace(':', '/')
    s = re.sub(r'(\d),(\d)', r'\1.\2', s)
    s = re.sub(r'(?<![\d.])(\d+) (\d+)/(\d+)', r'(\1+\2/\3)', s)
    s = re.sub(r'(?<![\d./])(\d+)/(\d+)(?![\d.])', r'(\1/\2)', s)
    s = re.sub('[' + SUPS + '⁻]+', lambda m: '**(' + ''.join(UNSUP[c] for c in m.group(0)) + ')', s)
    s = re.sub(r'\^\{([^}]*)\}', r'**(\1)', s)
    s = re.sub(r'\^\(([^)]*)\)', r'**(\1)', s)
    s = re.sub(r'\^(-?\d+)', r'**(\1)', s)
    s = re.sub(r'√(\d+(?:\.\d+)?)', r'§(\1)', s)
    s = s.replace('√', '§')
    s = re.sub(r'([a-z])\s*(?=[a-z(§])', r'\1*', s)
    s = re.sub(r'(\d|\))\s*(?=[a-z(§])', r'\1*', s)
    s = s.replace('§', 'sqrt')
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


ASK = ('Найдите значение числового выражения', 'Вычислите значение числового выражения')
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
        out += f'<text x="4" y="{y + 4}" font-size="13">{nm})</text>' if nm else ''
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
       invariant='Одно действие: сложение или вычитание двух обыкновенных дробей с разными знаменателями (делители 100), ответ — десятичная дробь.',
       varies='Знаменатели (2, 4, 5, 10, 20, 25, 50), числители, знак действия; ответ может быть отрицательным.',
       answer_rule='Приводим к общему знаменателю, складываем/вычитаем, переводим в десятичную.',
       fipi=r'значение выражения\s+\d+\s+\d+\s*[+−-]\s*\d+\s+\d+\s*\.',
       mistakes=['складывают числители и знаменатели', 'ошибка в знаке, когда вычитаемое больше'], kim=K6)
def gen_og06_frac_addsub(r):
    d1 = r.choice([2, 4, 5, 8, 10, 20, 25])
    d2 = r.choice([x for x in (4, 5, 10, 20, 25, 40, 50) if x != d1])
    n1 = r.randint(2, 2 * d1 - 1)
    n2 = r.randint(1, 2 * d2 - 1)
    a, b = F(n1, d1), F(n2, d2)
    if a.denominator != d1 or b.denominator != d2:
        return None
    op = r.choice('+−')
    val = a + b if op == '+' else a - b
    if not nice(val, 3) or val == 0:
        return None
    if r.random() < 0.5:
        a, b = b, a
        val = a + b if op == '+' else a - b
    ex = f'{fr(a)} {op} {fr(b)}'
    return _expr_card(r, ex, val, f'Общий знаменатель {max(a.denominator, b.denominator) if max(a.denominator, b.denominator) % min(a.denominator, b.denominator) == 0 else a.denominator * b.denominator // math.gcd(a.denominator, b.denominator)}: {ex} = {fr(val)} = {tnum(val)}.')


@proto('og06-frac-muldiv', 'oge', 6, 'Произведение или частное обыкновенных дробей',
       invariant='Одно действие: умножение или деление двух обыкновенных дробей (правильных или неправильных).',
       varies='Числители и знаменатели (до 25), знак действия.',
       answer_rule='Умножаем числители и знаменатели (при делении — на перевёрнутую дробь), сокращаем, переводим в десятичную.',
       fipi=r'значение выражения\s+\d+\s+\d+\s*[·⋅:]\s*\d+\s+\d+\s*\.',
       mistakes=['при делении не переворачивают делитель', 'делят числитель на числитель и знаменатель на знаменатель с ошибкой'], kim=K6)
def gen_og06_frac_muldiv(r):
    a = F(r.randint(1, 24), r.randint(2, 16))
    b = F(r.randint(1, 24), r.randint(2, 16))
    if a.denominator == 1 or b.denominator == 1 or a.numerator > 25 or b.numerator > 40:
        return None
    op = r.choice(['·', ':'])
    val = a * b if op == '·' else a / b
    if not nice(val, 2) or val.denominator == 1 and r.random() < 0.6:
        return None
    ex = f'{fr(a)} {op} {fr(b)}'
    return _expr_card(r, ex, val, f'{ex} = {fr(val)} = {tnum(val)}.')


@proto('og06-dec-addsub', 'oge', 6, 'Сумма или разность десятичных дробей',
       invariant='Одно действие с десятичными дробями (десятые): a ± b, ответ может быть отрицательным.',
       varies='Числа (одна-две цифры до запятой), знак действия.',
       answer_rule='Записываем разряд под разрядом; если вычитаемое больше, результат отрицательный.',
       fipi=r'значение выражения\s+\d+,\d\s*[+−-]\s*\d+,\d\s*\.',
       mistakes=['ошибка в знаке при a < b', 'сдвиг разрядов'], kim=K6)
def gen_og06_dec_addsub(r):
    a = F(r.randint(11, 199), 10)
    b = F(r.randint(11, 199), 10)
    if a.denominator == 1 or b.denominator == 1 or a < 10 and b < 10:
        return None
    op = r.choice('+−')
    val = a + b if op == '+' else a - b
    if val == 0:
        return None
    ex = f'{tnum(a)} {op} {tnum(b)}'
    return _expr_card(r, ex, val, f'{ex} = {tnum(val)}.')


@proto('og06-dec-mul', 'oge', 6, 'Произведение десятичных дробей',
       invariant='Умножение двух десятичных дробей (десятые, сотые) «в столбик».',
       varies='Множители (в т. ч. меньше 1 или больше 10).',
       answer_rule='Перемножаем как натуральные числа и отделяем столько знаков, сколько их у множителей вместе.',
       fipi=r'значение выражения\s+\d+,\d\s*[·⋅]\s*\d+,\d\s*\.',
       mistakes=['отделяют неверное число знаков после запятой'], kim=K6)
def gen_og06_dec_mul(r):
    a = F(r.randint(2, 9), 10) if r.random() < 0.35 else F(r.randint(101, 250), 10)
    b = F(r.randint(11, 99), 10)
    if a.denominator == 1 or b.denominator == 1:
        return None
    if r.random() < 0.5:
        a, b = b, a
    val = a * b
    ex = f'{tnum(a)} · {tnum(b)}'
    return _expr_card(r, ex, val, f'{ex} = {tnum(val)}.')


@proto('og06-dec-div', 'oge', 6, 'Частное десятичных дробей (запись дробью)',
       invariant='Десятичная дробь делится на десятичную, частное записано дробной чертой; ответ — целое или десятичное.',
       varies='Делимое и делитель (десятые), ответ (целый или с одним знаком).',
       answer_rule='Переносим запятую в делителе и делимом на одинаковое число знаков и делим.',
       fipi=r'значение выражения\s+\d+,\d\s+\d+,\d\s*\.',
       mistakes=['переносят запятую только в делителе'], kim=K6)
def gen_og06_dec_div(r):
    b = F(r.randint(2, 99), 10)
    val = F(r.randint(2, 40)) if r.random() < 0.7 else F(r.randint(11, 99), 10)
    a = b * val
    if b.denominator == 1 or not nice(a, 2) or a.denominator == 1 or a > 150:
        return None
    ex = f'{tnum(a)} : {tnum(b)}'
    q = f'{pick(r, *ASK)} ⟦{tnum(a)} / {tnum(b)}⟧.'
    return pcard(q, num(val), e=f'{tnum(a)} : {tnum(b)} = {tnum(a * 10 ** 2)} : {tnum(b * 10 ** 2)} = {tnum(val)}.'), lambda: same(num(val), parse(ex))


@proto('og06-frac-reciprocal', 'oge', 6, 'Единица, делённая на сумму дробей',
       invariant='Выражение вида 1 / (1/a ± 1/b): многоэтажная дробь, знаменатели с общим множителем.',
       varies='Знаменатели a, b, знак.',
       answer_rule='Считаем знаменатель как сумму дробей (общий знаменатель — НОК), затем делим 1 на неё.',
       fipi=r'значение выражения\s+1\s+1\s+\d+\s*[+−-]\s*1\s+\d+',
       mistakes=['считают 1/(1/a+1/b) = a + b', 'ошибка в общем знаменателе'], kim=K6)
def gen_og06_frac_reciprocal(r):
    g = r.randint(7, 16)
    p, q_ = r.sample(range(2, 10), 2)
    a, b = g * p, g * q_
    op = r.choice('+−') if a < b else '+'
    den = F(1, a) + F(1, b) if op == '+' else F(1, a) - F(1, b)
    if den <= 0 or a > 120 or b > 120:
        return None
    val = 1 / den
    if not nice(val, 2):
        return None
    ex = f'1 : (1/{a} {op} 1/{b})'
    q = f'{pick(r, *ASK)} ⟦1 / (1/{a} {op} 1/{b})⟧.'
    return pcard(q, num(val), e=f'1/{a} {op} 1/{b} = {fr(den)}; 1 : {fr(den)} = {tnum(val)}.'), lambda: same(num(val), parse(ex))


# ================================================================ №7 — числа на координатной прямой

K7 = K(minutes=2, kes=['1.4', '6.1'], kt=[3], answer='цифра варианта',
       style='Выбор одного из вариантов «1) … 4)», в ответ — номер (как в КИМ ОГЭ №7)')
TAIL7 = ('В ответе укажите номер правильного варианта.', 'Запишите в ответ номер выбранного варианта.', '')
SUB = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')


def ufr(p, q):
    """Дробь одним знаком: ⁵⁵⁄₁₉ (числитель верхним, знаменатель нижним индексом)."""
    s = '−' if p * q < 0 else ''
    return s + str(abs(p)).translate(SUP) + '⁄' + str(abs(q)).translate(SUB)


def _q7(r, q):
    t = pick(r, *TAIL7)
    return f'{q} {t}'.strip()


def _int_line(lo, hi, pts):
    return svg_numline(lo - 0.6, hi + 0.6, ticks=range(lo, hi + 1), labels=[(i, tnum(i)) for i in range(lo, hi + 1)], points=pts)


def _roots_pool(lo, hi):
    """Натуральные n, для которых lo < √n < hi и √n не целое."""
    return [nn for nn in range(max(2, lo * lo + 1), hi * hi) if math.isqrt(nn) ** 2 != nn]


@proto('og07-point-which', 'oge', 7, 'Какое из чисел отмечено точкой',
       invariant='На прямой отмечена точка; среди четырёх чисел (дроби с общим знаменателем или корни) выбрать то, которое ей соответствует.',
       varies='Вид чисел (p/q или √n), знаменатель, положение точки, шкала (целые деления или деления 0,1).',
       answer_rule='Оцениваем каждое число (делением или через квадраты) и сравниваем с положением точки.',
       fipi=r'Одно из чисел.{0,80}отмечено на (координатной|числовой)?\s*прямой',
       mistakes=['путают числитель и знаменатель при оценке', '√n оценивают как n/2'],
       svg=True, card_kind='one', kim=K7)
def gen_og07_point_which(r):
    kind = r.choice(['frac', 'frac', 'sqrt', 'tenth'])
    letter = r.choice('AMKPBC')
    if kind == 'tenth':  # отрезок [n; n+1] с делениями 0,1
        n = r.choice([0, 0, 1, 2])
        d = r.choice([3, 6, 7, 9, 11, 12, 13, 14, 17, 18, 19, 21])
        inside = [m for m in range(n * d + 1, (n + 1) * d) if math.gcd(m, d) == 1 and 0.03 < (F(m, d) * 10) % 1 < 0.97]
        if len(inside) < 2:
            return None
        m = r.choice(inside)
        others = [x for x in range(max(1, (n - 1) * d), (n + 2) * d) if math.gcd(x, d) == 1 and abs(F(x - m, d)) >= F(15, 100)]
        if len(others) < 3:
            return None
        vals = sorted([m] + r.sample(others, 3))
        t = F(m, d)
        ticks = [n + F(i, 10) for i in range(11)]
        svg = svg_numline(n - F(1, 20), n + 1 + F(1, 20), ticks=ticks, labels=[(v, tnum(v)) for v in ticks[::2]], points=[(t, letter)])
        items = [ufr(v, d) for v in vals]
        vv = [sp.Rational(v, d) for v in vals]
        e = f'{ufr(m, d)} ≈ {approx(t)} — между {tnum(n + F(int((t - n) * 10), 10))} и {tnum(n + F(int((t - n) * 10) + 1, 10))}, там и стоит точка {letter}.'
    elif kind == 'frac':
        d = r.choice([7, 9, 11, 13, 17, 19, 21, 23, 29])
        k = r.randint(1, 9)
        good = [m for m in range(k * d + 1, (k + 1) * d) if math.gcd(m, d) == 1 and 0.2 < float(F(m, d) - k) < 0.8]
        if not good:
            return None
        m = r.choice(good)
        t = F(m, d)
        others = [x for x in range((k - 1) * d, (k + 3) * d) if math.gcd(x, d) == 1 and abs(F(x - m, d)) > F(1, 2) and x > 0]
        if len(others) < 3:
            return None
        vals = sorted([m] + r.sample(others, 3))
        lo, hi = max(0, math.floor(F(vals[0], d))), math.ceil(F(vals[-1], d))
        svg = _int_line(lo, hi, [(t, letter)])
        items = [ufr(v, d) for v in vals]
        vv = [sp.Rational(v, d) for v in vals]
        e = f'{ufr(m, d)} = {k} {ufr(m - k * d, d)} ≈ {approx(t)} — это точка {letter}.'
    else:
        k = r.randint(2, 11)
        pool = _roots_pool(k, k + 1)
        nn = r.choice([x for x in pool if 0.2 < math.sqrt(x) - k < 0.8] or pool)
        t = F(round(math.sqrt(nn) * 1000), 1000)
        others = [x for x in range(max(2, (k - 1) ** 2), (k + 2) ** 2 + 1) if math.isqrt(x) ** 2 != x and abs(math.sqrt(x) - math.sqrt(nn)) > 0.45]
        if len(others) < 3:
            return None
        vals = sorted([nn] + r.sample(others, 3))
        lo, hi = math.floor(math.sqrt(vals[0])), math.ceil(math.sqrt(vals[-1]))
        svg = _int_line(lo, hi, [(t, letter)])
        items = [f'√{v}' for v in vals]
        vv = [sp.sqrt(v) for v in vals]
        m = nn
        e = f'{k}² = {k * k} < {nn} < {(k + 1) ** 2} = {k + 1}², √{nn} ≈ {approx(t)} — это точка {letter}.'
    right = vals.index(m)
    o, a = fixed_opts(items, right)
    q = _q7(r, pick(r, f'Какое из чисел, приведённых в вариантах ответа, изображено на координатной прямой точкой {letter}?',
                    f'На рисунке точкой {letter} показано одно из чисел, записанных в вариантах ответа. Какое именно?',
                    f'Определите, какому из предложенных чисел соответствует точка {letter} на координатной прямой.'))
    pos = R(t)
    return pcard(q, a, e=e, k='one', o=o, svg=svg), lambda: min(range(4), key=lambda i: abs(sp.N(vv[i] - pos))) == right and \
        abs(sp.N(vv[right] - pos)) < 0.01


@proto('og07-point-number', 'oge', 7, 'Какая из точек соответствует данному числу',
       invariant='На прямой с подписанными целыми отмечены точки A, B, C, D; одна изображает число √n (или p/q); найти её.',
       varies='Число (корень, неправильная дробь, со знаком минус), положение точек, подписанные целые.',
       answer_rule='Оцениваем число между соседними целыми и по положению внутри промежутка выбираем точку.',
       fipi=r'Одна из них соответствует числу',
       mistakes=['не различают левую и правую половину промежутка', 'путают √n и n/2'],
       svg=True, card_kind='one', kim=K7)
def gen_og07_point_number(r):
    kind = r.choice(['sqrt', 'sqrt', 'frac', 'negsqrt'])
    k = r.randint(2, 11) if kind != 'frac' else r.randint(1, 9)
    if kind == 'frac':
        d = r.choice([3, 6, 7, 9, 11, 12, 13, 17, 19])
        m = r.randint(k * d + 1, (k + 1) * d - 1)
        if math.gcd(m, d) != 1:
            return None
        v = F(m, d)
        txt, val = ufr(m, d), R(v)
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
    pts = sorted([v] + r.sample(same_seg, 1) + r.sample(other, 2))
    if min(b - a for a, b in zip(pts, pts[1:])) < F(3, 10):
        return None
    names = 'ABCD'
    right = pts.index(v)
    svg = _int_line(lo, hi, [(p, names[i]) for i, p in enumerate(pts)])
    o, a = fixed_opts([f'точка {c}' for c in names], right)
    q = _q7(r, pick(r, f'Какая из отмеченных на рисунке точек A, B, C, D изображает число {txt}?',
                    f'Число {txt} изображено на координатной прямой одной из точек A, B, C, D. Укажите эту точку.',
                    f'Где на координатной прямой находится число {txt}? Выберите нужную точку из A, B, C, D.'))
    e = f'{txt} ≈ {approx(v)}: между {tnum(base)} и {tnum(base + 1)}, {"ближе к " + tnum(base + 1) if fracp > 0.5 else "ближе к " + tnum(base)} — это точка {names[right]}.'
    pos = [R(p) for p in pts]
    return pcard(q, a, e=e, k='one', o=o, svg=svg), lambda: min(range(4), key=lambda i: abs(sp.N(pos[i] - val))) == right


@proto('og07-decimals-points', 'oge', 7, 'Точки и десятичные дроби: какой точке соответствует число',
       invariant='Точки A, B, C, D на прямой соответствуют четырём близким десятичным числам (в разном порядке); по порядку чисел найти точку для заданного числа.',
       varies='Числа (сотые и тысячные, отрицательные), порядок точек на рисунке, спрашиваемое число.',
       answer_rule='Упорядочиваем числа по возрастанию: самое левое число — самая левая точка и т. д.',
       fipi=r'соответствуют числам',
       mistakes=['считают 0,098 больше 0,11 из-за «большего числа цифр»', 'путают порядок отрицательных'],
       svg=True, card_kind='one', kim=K7)
def gen_og07_decimals_points(r):
    base = F(r.choice([1, 1, 1, 2, 3, 5, 7]), r.choice([10, 100]))
    nums = set()
    while len(nums) < 4:
        x = base + F(r.randint(-12, 12), r.choice([100, 1000])) * base * 5
        x = F(round(x * 1000), 1000)
        if x != 0:
            nums.add(x)
    nums = sorted(nums)
    if min(b - a for a, b in zip(nums, nums[1:])) < F(1, 1000):
        return None
    listed = nums[:]
    r.shuffle(listed)
    names = 'ABCD'
    xs = [F(i * 3 + r.randint(0, 1), 1) for i in range(4)]  # позиции точек слева направо
    target = r.choice(listed)
    right = nums.index(target)
    svg = svg_numline(-1, 12, ticks=(), labels=(), points=[(xs[i], names[i]) for i in range(4)])
    o, a = fixed_opts([f'точка {c}' for c in names], right)
    lst = '; '.join(tnum(x) for x in listed)
    q = _q7(r, pick(r, f'Точки A, B, C и D, изображённые на координатной прямой, соответствуют числам {lst} (в каком-то порядке). Какая точка соответствует числу {tnum(target)}?',
                    f'Числа {lst} изображены на координатной прямой точками A, B, C и D, но порядок неизвестен. Какой точкой изображено число {tnum(target)}?'))
    e = f'По возрастанию: {" < ".join(tnum(x) for x in nums)}. Число {tnum(target)} — {right + 1}-е слева, это точка {names[right]}.'
    return pcard(q, a, e=e, k='one', o=o, svg=svg), lambda: sorted(listed, key=lambda z: R(z)).index(target) == right


@proto('og07-sqrt-estimate', 'oge', 7, 'Оценка квадратного корня между целыми числами',
       invariant='Сравнение √n с целыми через квадраты: между какими числами лежит √n, или какой корень лежит на данном промежутке.',
       varies='Подкоренное число, направление вопроса, ловушки (√k и √(k+1) рядом с промежутком [k; k+1]).',
       answer_rule='k² < n < (k+1)² ⇔ k < √n < k+1.',
       fipi=r'(Между какими числами заключено|принадлежит промежутку).{0,40}√|√.{0,60}принадлежит промежутку',
       mistakes=['принимают √k за число из [k; k+1]', 'делят подкоренное число на 2'],
       card_kind='one', kim=K7)
def gen_og07_sqrt_estimate(r):
    if r.random() < 0.5:
        nn = r.randint(8, 250)
        if math.isqrt(nn) ** 2 == nn:
            return None
        k = math.isqrt(nn)
        wrong = [s for s in (k - 2, k - 1, k + 1, k + 2) if s > 0]
        items_v = sorted([k] + r.sample(wrong, 3))
        items = [f'{s} и {s + 1}' for s in items_v]
        o, a = fixed_opts(items, items_v.index(k))
        q = _q7(r, pick(r, f'Укажите два соседних целых числа, между которыми расположено число √{nn}.',
                        f'Число √{nn} лежит между двумя последовательными натуральными числами. Какими?'))
        e = f'{k}² = {k * k} < {nn} < {(k + 1) ** 2} = {k + 1}², значит {k} < √{nn} < {k + 1}.'
        return pcard(q, a, e=e, k='one', o=o), lambda: sp.floor(sp.sqrt(nn)) == items_v[int(a) - 1]
    k = r.randint(3, 12)
    nn = r.choice(_roots_pool(k, k + 1))
    traps = [k, k + 1] if r.random() < 0.6 else []
    bad = [x for x in range((k - 1) ** 2 + 1, (k + 2) ** 2) if math.isqrt(x) ** 2 != x and not k * k < x < (k + 1) ** 2]
    ws = traps + r.sample(bad, 3 - len(traps))
    vals = sorted(set([nn] + ws))
    if len(vals) < 4:
        return None
    items = [f'√{x}' for x in vals]
    o, a = fixed_opts(items, vals.index(nn))
    q = _q7(r, pick(r, f'Какое из чисел лежит на отрезке [{k}; {k + 1}]?',
                    f'Укажите число, которое больше {k}, но меньше {k + 1}.',
                    f'Какое из данных чисел находится между {k} и {k + 1}?'))
    e = f'{k} = √{k * k}, {k + 1} = √{(k + 1) ** 2}; между ними только √{nn}.'
    return pcard(q, a, e=e, k='one', o=o), lambda: sum(bool(k < sp.sqrt(x) < k + 1) for x in vals) == 1 and bool(k < sp.sqrt(vals[int(a) - 1]) < k + 1)


@proto('og07-frac-interval', 'oge', 7, 'Обыкновенная дробь и промежутки',
       invariant='Сравнение обыкновенной дроби с десятичными или целыми границами: какому промежутку принадлежит дробь, какая дробь лежит на [k; k+1], между какими целыми дробь.',
       varies='Дробь, шаг промежутков (0,1 или 1), направление вопроса.',
       answer_rule='Делим числитель на знаменатель (или выделяем целую часть) и находим промежуток.',
       fipi=r'(Какому из данных промежутков принадлежит|принадлежит отрезку|Между какими целыми числами заключено)',
       mistakes=['округляют дробь не в ту сторону', 'неверно выделяют целую часть'], card_kind='one', kim=K7)
def gen_og07_frac_interval(r):
    kind = r.randrange(3)
    d = r.choice([3, 6, 7, 9, 11, 12, 13, 14, 17, 19, 21, 23])
    if kind == 0:
        m = r.randint(1, d - 1)
        v = F(m, d)
        if math.gcd(m, d) != 1 or (v * 10) % 1 == 0:
            return None
        k = int(v * 10)
        starts = [s for s in range(max(0, k - 3), min(10, k + 4)) if s != k]
        if len(starts) < 3:
            return None
        starts = sorted(r.sample(starts, 3) + [k])
        items = [f'[{tnum(F(s, 10))}; {tnum(F(s + 1, 10))}]' for s in starts]
        o, a = fixed_opts(items, starts.index(k))
        q = _q7(r, pick(r, f'Какой из промежутков содержит число {ufr(m, d)}?', f'Укажите промежуток, в котором лежит число {ufr(m, d)}.'))
        e = f'{ufr(m, d)} = {m} : {d} ≈ {approx(v, 3)}.'
        return pcard(q, a, e=e, k='one', o=o), lambda: F(starts[int(a) - 1], 10) <= v <= F(starts[int(a) - 1] + 1, 10)
    if kind == 1:
        k = r.randint(1, 8)
        good = [m for m in range(k * d + 1, (k + 1) * d) if math.gcd(m, d) == 1]
        bad = [m for m in range((k - 1) * d + 1, (k + 2) * d) if math.gcd(m, d) == 1 and not k * d < m < (k + 1) * d]
        if not good or len(bad) < 3:
            return None
        m = r.choice(good)
        vals = sorted([m] + r.sample(bad, 3))
        o, a = fixed_opts([ufr(x, d) for x in vals], vals.index(m))
        q = _q7(r, pick(r, f'Какое из чисел лежит на отрезке [{k}; {k + 1}]?', f'Укажите число, заключённое между {k} и {k + 1}.'))
        e = f'{k} = {ufr(k * d, d)}, {k + 1} = {ufr((k + 1) * d, d)}; подходит {ufr(m, d)}.'
        return pcard(q, a, e=e, k='one', o=o), lambda: sum(bool(k <= sp.Rational(x, d) <= k + 1) for x in vals) == 1 and \
            bool(k <= sp.Rational(vals[int(a) - 1], d) <= k + 1)
    m = r.randint(2 * d + 1, 12 * d)
    if math.gcd(m, d) != 1:
        return None
    k = m // d
    wrong = [s for s in (k - 2, k - 1, k + 1, k + 2) if s > 0]
    items_v = sorted([k] + r.sample(wrong, 3))
    o, a = fixed_opts([f'{s} и {s + 1}' for s in items_v], items_v.index(k))
    q = _q7(r, pick(r, f'Между какими соседними целыми числами находится число {ufr(m, d)}?', f'Число {ufr(m, d)} заключено между двумя последовательными целыми числами. Какими?'))
    e = f'{ufr(m, d)} = {k} {ufr(m - k * d, d)}, значит {k} < {ufr(m, d)} < {k + 1}.'
    return pcard(q, a, e=e, k='one', o=o), lambda: sp.floor(sp.Rational(m, d)) == items_v[int(a) - 1]


@proto('og07-between-fracs', 'oge', 7, 'Какое число заключено между двумя дробями',
       invariant='Даны две близкие обыкновенные дроби; из четырёх десятичных чисел выбрать то, что лежит между ними.',
       varies='Дроби (близкие, с разными знаменателями), набор десятичных вариантов.',
       answer_rule='Переводим дроби в десятичные с точностью до сотых/тысячных и сравниваем.',
       fipi=r'заключено между числами',
       mistakes=['сравнивают только числители', 'грубое округление'], card_kind='one', kim=K7)
def gen_og07_between_fracs(r):
    step = r.choice([F(1, 10), F(1, 10), F(1, 100)])
    target = F(r.randint(2, 18), 10) if step == F(1, 10) else F(r.randint(20, 98), 100)
    for _ in range(40):
        d1, d2 = r.sample([7, 9, 11, 13, 14, 17, 19, 21, 23, 27, 29, 31], 2)
        p1 = math.floor(target * d1)
        p2 = math.ceil(target * d2)
        a_, b_ = F(p1, d1), F(p2, d2)
        if a_ < target < b_ and b_ - a_ < step and math.gcd(p1, d1) == 1 and math.gcd(p2, d2) == 1:
            break
    else:
        return None
    opts_v = sorted([target] + r.sample([target - 3 * step, target - 2 * step, target - step, target + step, target + 2 * step, target + 3 * step], 3))
    if len(opts_v) < 4 or any(a_ < x < b_ for x in opts_v if x != target) or opts_v[0] <= 0:
        return None
    o, a = fixed_opts([tnum(x) for x in opts_v], opts_v.index(target))
    q = _q7(r, pick(r, f'Какое из чисел больше {ufr(p1, d1)}, но меньше {ufr(p2, d2)}?', f'Какое из следующих чисел лежит между {ufr(p1, d1)} и {ufr(p2, d2)}?'))
    e = f'{ufr(p1, d1)} ≈ {approx(a_, 3)}, {ufr(p2, d2)} ≈ {approx(b_, 3)}; между ними {tnum(target)}.'
    return pcard(q, a, e=e, k='one', o=o), lambda: bool(sp.Rational(p1, d1) < R(target) < sp.Rational(p2, d2)) and \
        sum(bool(sp.Rational(p1, d1) < R(x) < sp.Rational(p2, d2)) for x in opts_v) == 1


def _stmt_pool(a_name, c_vals):
    """Утверждения про одно число: (текст, f(a) > 0 ⇔ верно)."""
    out = []
    for c in c_vals:
        if c == 0:
            out += [(f'{a_name} > 0', lambda a: a), (f'{a_name} < 0', lambda a: -a)]
            continue
        out += [(f'{a_name} − {par(c)} > 0' if c >= 0 else f'{a_name} + {tnum(-c)} > 0', lambda a, c=c: a - c),
                (f'{a_name} − {par(c)} < 0' if c >= 0 else f'{a_name} + {tnum(-c)} < 0', lambda a, c=c: c - a),
                (f'{tnum(c)} − {a_name} > 0', lambda a, c=c: c - a),
                (f'{tnum(c)} − {a_name} < 0', lambda a, c=c: a - c)]
    return out


@proto('og07-point-statement', 'oge', 7, 'Число отмечено на прямой: какое неравенство верно',
       invariant='Точка a между соседними целыми на рисунке; из четырёх неравенств вида a − c > 0, c − a < 0 выбрать верное (неверное).',
       varies='Буква, положение точки (в т. ч. отрицательные), числа в неравенствах, вопрос «верно»/«неверно».',
       answer_rule='По рисунку k < a < k+1; определяем знак каждой разности.',
       fipi=r'отмечено число.{0,40}(утверждений|неравенств).{0,40}верн',
       mistakes=['путают знак разности c − a', 'ошибаются с отрицательными числами'], svg=True, card_kind='one', kim=K7)
def gen_og07_point_statement(r):
    v = r.choice(['t', 'c', 'k', 'p'])
    k = r.randint(-7, 6)
    aval = k + F(r.randint(2, 8), 10)
    pool = _stmt_pool(v, [k, k + 1, k - 1, k + 2])
    want_true = r.random() < 0.75
    good = [s for s in pool if (s[1](aval) > 0) == want_true]
    bad = [s for s in pool if (s[1](aval) > 0) != want_true]
    if not good or len(bad) < 3:
        return None
    ch = r.sample(good, 1) + r.sample(bad, 3)
    if len({c[0] for c in ch}) < 4:
        return None
    o, a = opts(r, [c[0] for c in ch], 0)
    svg = _int_line(k - 1, k + 2, [(aval, v)])
    word = 'верно' if want_true else 'неверно'
    q = _q7(r, pick(r, f'На рисунке изображена координатная прямая, на которой отмечено число {v}. Какое из приведённых ниже неравенств для этого числа {word}?',
                    f'Положение числа {v} показано точкой на координатной прямой. Выберите среди предложенных неравенств то, которое {word}.',
                    f'Пользуясь рисунком, где отмечено число {v}, определите, какое из следующих неравенств {word}.'))
    e = f'По рисунку {tnum(k)} < {v} < {tnum(k + 1)}. Проверяем знаки разностей: {word} «{ch[0][0]}».'
    rel = parse(ch[0][0].replace(' > ', '>').replace(' < ', '<'))
    S = sp.Symbol(v)
    A = sp.Symbol('A', real=True)

    def chk():
        sol = sp.solve_univariate_inequality(rel.subs(S, A), A, relational=False)
        inside = sp.Interval.open(k, k + 1).is_subset(sol)
        outside = sp.Interval.open(k, k + 1).intersect(sol) == sp.EmptySet
        return inside if want_true else outside
    return pcard(q, a, e=e, k='one', o=o, svg=svg), chk


def _corners(ia, ib):
    return [(x, y) for x in ia for y in ib]


@proto('og07-two-points', 'oge', 7, 'Два числа на прямой: знак суммы, разности, произведения',
       invariant='На прямой отмечены два числа; по их положению выбрать верное (неверное) утверждение о сумме, разности, произведении, квадратах, обратных.',
       varies='Буквы, положение точек (разные знаки, одна сторона), набор утверждений, вопрос верно/неверно.',
       answer_rule='По рисунку знаем промежутки для обоих чисел; оцениваем знак выражения на всём прямоугольнике значений.',
       fipi=r'отмечены числа\s+[a-zxy]?\s*и\s+[a-zxy]?\s*\.\s*Какое из',
       mistakes=['считают, что a − b > 0, если a левее', 'не учитывают знак при сравнении обратных'],
       svg=True, card_kind='one', kim=K7)
def gen_og07_two_points(r):
    na, nb = r.choice([('a', 'b'), ('x', 'y'), ('m', 'n'), ('p', 'q'), ('c', 'd')])
    ka, kb = r.sample(range(-4, 4), 2)
    ia, ib = (ka, ka + 1), (kb, kb + 1)
    av, bv = ka + F(r.randint(2, 8), 10), kb + F(r.randint(2, 8), 10)
    lo, hi = min(ka, kb) - 1, max(ka, kb) + 2
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
        vals = [f(F(x), F(y)) for x, y in _corners(ia, ib) if (x != 0 and y != 0) or '1/' not in t]
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
    q = _q7(r, pick(r, f'Числа {na} и {nb} изображены точками на координатной прямой (см. рисунок). Выберите утверждение, которое {word}.',
                    f'По расположению чисел {na} и {nb} на координатной прямой определите, какое из утверждений {word}.',
                    f'На рисунке показано, где на координатной прямой находятся числа {na} и {nb}. Какое из следующих соотношений {word}?'))
    e = f'По рисунку {tnum(ka)} < {na} < {tnum(ka + 1)}, {tnum(kb)} < {nb} < {tnum(kb + 1)}; {word}: «{ch[0][0]}».'
    f0 = ch[0][2]

    def chk():  # сетка внутренних точек обоих промежутков
        grid = [F(i, 20) for i in range(1, 20)]
        res = {f0(ka + s, kb + t) > 0 for s in grid for t in grid if ka + s != 0 and kb + t != 0}
        return res == {want_true}
    return pcard(q, a, e=e, k='one', o=o, svg=svg), chk


@proto('og07-three-diff', 'oge', 7, 'Три числа на прямой: знак разности',
       invariant='На прямой отмечены три числа; из трёх разностей выбрать отрицательную (положительную).',
       varies='Буквы, взаимное расположение, спрашиваемый знак.',
       answer_rule='Разность u − v отрицательна, если u левее v.',
       fipi=r'Какая из разностей',
       mistakes=['путают уменьшаемое и вычитаемое'], svg=True, card_kind='one', kim=K7)
def gen_og07_three_diff(r):
    names = r.choice([('p', 'q', 'r'), ('x', 'y', 'z'), ('a', 'b', 'c'), ('k', 'm', 'n'), ('s', 't', 'u')])
    pos = sorted(r.sample(range(-6, 7), 3))
    order = list(names)
    r.shuffle(order)
    val = {order[i]: F(pos[i]) + F(r.randint(2, 8), 10) for i in range(3)}
    want_neg = r.random() < 0.5
    pairs = [(x, y) for x in names for y in names if x != y]
    good = [(x, y) for x, y in pairs if (val[x] - val[y] < 0) == want_neg]
    bad = [(x, y) for x, y in pairs if (val[x] - val[y] < 0) != want_neg]
    g = r.choice(good)
    bs = [b for b in bad if b != (g[1], g[0])]
    if len(bs) < 2:
        return None
    ch = [g] + r.sample(bs, 2)
    if len({frozenset(c) for c in ch}) < 3:
        return None
    o, a = opts(r, [f'{x} − {y}' for x, y in ch], 0)
    lo, hi = pos[0] - 1, pos[-1] + 2
    svg = svg_numline(lo, hi, ticks=[pos[0] - 1 + i for i in range(hi - lo + 1)], labels=[(0, '0')] if lo < 0 < hi else [],
                      points=[(val[n], n) for n in names])
    word = 'отрицательна' if want_neg else 'положительна'
    q = _q7(r, pick(r, f'Числа {", ".join(names[:2])} и {names[2]} отмечены на координатной прямой. Выберите разность, которая {word}.',
                    f'На рисунке изображены числа {names[0]}, {names[1]} и {names[2]}. Определите, какая из приведённых разностей {word}.'))
    x, y = g
    e = f'На рисунке {x} {"левее" if want_neg else "правее"} {y}, поэтому {x} − {y} {"< 0" if want_neg else "> 0"}.'
    return pcard(q, a, e=e, k='one', o=o, svg=svg), lambda: sum(bool((R(val[p]) - R(val[s]) < 0) == want_neg) for p, s in ch) == 1 and \
        bool((R(val[x]) - R(val[y]) < 0) == want_neg)


# ================================================================ №8 — степени, корни, преобразования

K8 = K(minutes=3, kes=['2.2', '2.5', '1.4'], kt=[4], style='«Найдите значение выражения …» с формулой; ответ — число')
K8a = K(minutes=4, kes=['2.1', '2.3', '2.4'], kt=[4], style='«Найдите значение выражения … при a = …»: сначала упростить, затем подставить')


def _pw(b, e):
    b = f'({tnum(b)})' if F(b) < 0 else (f'({fr(b)})' if F(b).denominator > 1 else tnum(b))
    return f'{b}{sup(e)}'


def _f8(r, ex, val, e):
    q = f'{pick(r, *ASK)} ⟦{ex}⟧.'
    return pcard(q, num(val), e=e), lambda: same(num(val), parse(ex))


@proto('og08-pow-base', 'oge', 8, 'Степени с одинаковым числовым основанием',
       invariant='Числовое выражение из степеней одного основания (целые показатели, в т. ч. отрицательные): умножение, деление, степень степени.',
       varies='Основание (в т. ч. дробь 1/2, 1/3), показатели, запись (частное через «:» или дробью).',
       answer_rule='Складываем/вычитаем/умножаем показатели, затем вычисляем одну небольшую степень.',
       fipi=r'значение выражения\s+\(?\s*(\d+)\s*[−-]?\s*\d+\s*\)?\s*[−-]?\s*\d*\s*[·⋅]?\s*\(?\s*\1\s+[−-]?\s*\d+',
       mistakes=['перемножают показатели вместо сложения', 'ошибка со знаком отрицательного показателя'], maxdec=4, kim=K8)
def gen_og08_pow_base(r):
    b = r.choice([2, 2, 3, 3, 5, 6, 7, 9, 10, F(1, 2), F(1, 3)])
    target = r.choice([-3, -2, -1, 1, 2, 3, 4]) if b in (2, 3) else r.choice([-2, -1, 1, 2])
    if isinstance(b, F) and target < 0:
        target = -target
    kind = r.randrange(3)
    if kind == 0:
        m = r.choice([x for x in range(-13, 20) if x not in (0, 1, -1)])
        n = r.choice([x for x in range(-13, 20) if x not in (0, 1, -1)])
        k = m + n - target
        if k in (0, 1, -1) or abs(k) > 25:
            return None
        ex = pick(r, f'{_pw(b, m)} · {_pw(b, n)} : {_pw(b, k)}', f'({_pw(b, m)} · {_pw(b, n)}) / {_pw(b, k)}')
        e = f'Показатель: {tnum(m)} + {par(n)} − {par(k)} = {tnum(target)}.'
    elif kind == 1:
        m, n = r.choice([-9, -7, -5, -4, -3, 3, 4, 5, 7, 9]), r.choice([-3, -2, 2, 3, 4])
        k = target - m * n
        if k in (0, 1, -1) or abs(k) > 30:
            return None
        ex = f'({_pw(b, m)}){sup(n)} · {_pw(b, k)}'
        e = f'Показатель: {tnum(m)}·{par(n)} + {par(k)} = {tnum(target)}.'
    else:
        m, n = r.choice([-9, -7, -5, -4, -3, 3, 4, 5, 7, 9]), r.choice([-3, -2, 2, 3, 4])
        k = m * n - target
        if k in (0, 1, -1) or abs(k) > 30:
            return None
        ex = pick(r, f'({_pw(b, m)}){sup(n)} : {_pw(b, k)}', f'({_pw(b, m)}){sup(n)} / {_pw(b, k)}')
        e = f'Показатель: {tnum(m)}·{par(n)} − {par(k)} = {tnum(target)}.'
    val = F(b) ** target
    if not nice(val, 4):
        return None
    return _f8(r, ex, val, e + f' {_pw(b, target)} = {tnum(val)}.')


@proto('og08-pow-var', 'oge', 8, 'Степени с буквой: упростить и подставить',
       invariant='Выражение с буквой из степеней одного основания; упростить по свойствам степени и подставить значение.',
       varies='Буква, показатели (в т. ч. отрицательные), вид (произведение, частное, степень степени), значение переменной.',
       answer_rule='Приводим к виду aᵏ и подставляем число.',
       fipi=r'при\s+[a-zх]\s*=\s*[−-]?\s*\d+\s*\.?\s*$',
       mistakes=['подставляют до упрощения и ошибаются в вычислениях', 'путают степень степени и произведение'], maxdec=4, kim=K8)
def gen_og08_pow_var(r):
    v = r.choice(['b', 'x', 'c', 'y', 'm', 'p', 'a'])
    target = r.choice([-2, -1, 2, 3, 1, 4])
    m, n = r.choice([-9, -7, -6, -5, -4, -3, 3, 4, 5, 6, 7, 8, 9, 11, 13]), r.choice([-3, -2, 2, 3, 4, 7, 12, 17])
    kind = r.randrange(3)
    if kind == 0:
        k = m + n - target
        if k in (0, 1) or abs(k) > 30:
            return None
        ex = pick(r, f'{v}{sup(m)} · {v}{sup(n)} : {v}{sup(k)}', f'({v}{sup(m)} · {v}{sup(n)}) / {v}{sup(k)}')
    elif kind == 1:
        n = r.choice([-4, -3, -2, 2, 3, 4])
        k = target - m * n
        if k in (0, 1) or abs(k) > 30:
            return None
        ex = pick(r, f'({v}{sup(m)}){sup(n)} · {v}{sup(k)}', f'{v}{sup(k)} · ({v}{sup(m)}){sup(n)}')
    else:
        n = r.choice([-4, -3, -2, 2, 3, 4])
        k = m * n - target
        if k in (0, 1) or abs(k) > 30:
            return None
        ex = pick(r, f'({v}{sup(m)}){sup(n)} : {v}{sup(k)}', f'({v}{sup(m)}){sup(n)} / {v}{sup(k)}')
    val_x = r.choice([2, 3, 4, 5, 6, 7, 10, -2, -3, F(1, 2), F(1, 3), F(1, 5)])
    val = F(val_x) ** target
    if not nice(val, 3) or abs(val) > 1000:
        return None
    q = f'{pick(r, "Найдите значение выражения", "Вычислите значение выражения", "Упростите выражение и найдите его значение:")} {ex} при {v} = {fr(val_x)}.'
    e = f'Упрощаем: {v}{sup(target) if target != 1 else ""}; при {v} = {fr(val_x)} получаем {tnum(val)}.'
    sym = sp.Symbol(v)
    return pcard(q, num(val), e=e), lambda: same(num(val), parse(ex).subs(sym, R(val_x)))


@proto('og08-pow-mixed', 'oge', 8, 'Степени с разными основаниями',
       invariant='Произведение степеней разных оснований и степень их произведения: (ab)ⁿ = aⁿbⁿ; сокращаем одинаковые степени.',
       varies='Основания (в т. ч. 10 = 2·5, 30 = 3·10), показатели, место составного основания.',
       answer_rule='Раскладываем составное основание на множители и сокращаем.',
       fipi=r'значение выражения\s+\(?\s*\d+\s*[·⋅]?\s*\d*\s*\)?\s*\d+\s*[·⋅]?\s*\d+\s+\d+\s*[·⋅]\s*\d+\s+\d+\s+\d+',
       mistakes=['перемножают основания и складывают показатели одновременно'], maxdec=4, kim=K8)
def gen_og08_pow_mixed(r):
    a, b = r.choice([(2, 3), (2, 5), (3, 5), (2, 7), (3, 7), (4, 5), (3, 10), (6, 11), (5, 7), (2, 9), (4, 7)])
    if r.random() < 0.5:
        a, b = b, a
    ab = a * b
    n = r.randint(4, 14)
    kind = r.randrange(3)
    if kind == 0:
        p, q_ = n + r.choice([0, 1, 2]), n + r.choice([0, 1, 2])
        if p == q_ == n:
            return None
        val = F(a) ** (p - n) * F(b) ** (q_ - n)
        ex = pick(r, f'({_pw(a, p)} · {_pw(b, q_)}) / {_pw(ab, n)}', f'{_pw(a, p)} · {_pw(b, q_)} : {_pw(ab, n)}')
    elif kind == 1:
        p = n - r.choice([1, 2])
        val = F(ab) ** n / (F(a) ** p * F(b) ** n)
        ex = f'{_pw(ab, n)} / ({_pw(a, p)} · {_pw(b, n)})'
    else:
        c = r.choice([1, 2])
        val = F(ab) ** n / (F(a) ** (n - c) * F(b) ** (n - 1))
        ex = f'({a} · {b}){sup(n)} / ({_pw(a, n - c)} · {_pw(b, n - 1)})'
    if not nice(val, 4) or abs(val) > 5000 or val == 1:
        return None
    return _f8(r, ex, val, f'{ab}{sup(n)} = {a}{sup(n)}·{b}{sup(n)}; после сокращения {tnum(val)}.')


@proto('og08-pow-two-vars', 'oge', 8, 'Степени двух букв: упростить и подставить (в т. ч. корень)',
       invariant='aᵖ·(bᵠ)ʳ/(ab)ˢ: после упрощения остаётся произведение небольших степеней; подставляем значения (b может быть корнем).',
       varies='Показатели, значения букв (целые, √2, √3).',
       answer_rule='Собираем показатели при a и при b, затем подставляем; (√k)² = k.',
       fipi=r'\(\s*[a-z]\s*[·⋅]\s*[a-z]\s*\).{0,40}при\s+[a-z]\s*=.{0,20}и\s+[a-z]\s*=',
       mistakes=['забывают возвести в степень второй множитель', 'ошибка с (√2)⁴'], kim=K8)
def gen_og08_pow_two_vars(r):
    va, vb = r.choice([('a', 'b'), ('x', 'y'), ('m', 'n'), ('p', 'q')])
    s_ = r.randint(9, 25)
    ea, eb = r.choice([1, 2, 3, 4]), r.choice([0, 2, 4])
    q_ = r.choice([2, 3, 4, 5])
    if (s_ + eb) % q_:
        return None
    rr = (s_ + eb) // q_
    p = s_ + ea
    A = r.choice([2, 3, 5, -2])
    B = r.choice([2, 3, 5])
    if eb == 0:
        return None
    val = F(A) ** ea * F(B) ** (eb // 2)
    ex = f'{va}{sup(p)} · ({vb}{sup(q_)}){sup(rr)} / ({va}{vb}){sup(s_)}'
    if abs(val) > 2000:
        return None
    q = f'{pick(r, "Найдите значение выражения", "Вычислите значение выражения")} {ex} при {va} = {tnum(A)} и {vb} = √{B}.'
    e = f'Упрощаем: {va}{sup(ea) if ea > 1 else ""}·{vb}{sup(eb)}; подставляем: {tnum(val)}.'
    S = {sp.Symbol(va): A, sp.Symbol(vb): sp.sqrt(B)}
    return pcard(q, num(val), e=e), lambda: same(num(val), sp.simplify(parse(ex).subs(S)))


def _sq_free():
    return [2, 3, 5, 6, 7, 10, 11, 13, 14, 15, 17, 19]


@proto('og08-sqrt-prod', 'oge', 8, 'Произведение и частное корней',
       invariant='√a·√b, √a·√b/√c, √(a·b)·√c, c√a·d√b·√e: под общим корнем получается точный квадрат.',
       varies='Подкоренные числа, коэффициенты, число множителей, частное или произведение.',
       answer_rule='√a·√b = √(ab), √a/√b = √(a/b); раскладываем на множители и извлекаем корень.',
       fipi=r'√\s*\(\s*\d+\s*(?:[·⋅]\s*\d+\s*)?\)\s*[·⋅]\s*√|\d+\s*√\s*\(\s*\d+\s*\)\s*[·⋅]\s*\d+\s*√',
       mistakes=['складывают подкоренные числа', 'забывают коэффициенты перед корнями'], kim=K8)
def gen_og08_sqrt_prod(r):
    kind = r.randrange(3)
    s = r.choice(_sq_free())
    if kind == 0:  # √a·√b/√c
        p, q_, t = r.sample([2, 3, 5, 7, 11, 13, 17], 3)
        a, b, c = p * q_, q_ * t * r.choice([1, 4]), p * t
        rad = F(a * b, c)
        if rad.denominator != 1 or math.isqrt(int(rad)) ** 2 != rad or a > 300 or b > 300:
            return None
        val = math.isqrt(int(rad))
        ex = pick(r, f'√{a} · √{b} / √{c}', f'(√{a} · √{b}) / √{c}')
        e = f'√({a}·{b}/{c}) = √{int(rad)} = {val}.'
    elif kind == 1:  # √(a·b)·√c
        a, b = r.sample([2, 3, 5, 6, 7, 10, 11, 13, 14, 15, 17, 18, 19, 21, 22, 26], 2)
        prod = a * b
        core = 1
        for pr in (2, 3, 5, 7, 11, 13, 17, 19):
            while prod % (pr * pr) == 0:
                prod //= pr * pr
        c = prod * r.choice([1, 4, 9])
        val = math.isqrt(a * b * c)
        if val * val != a * b * c or c > 400:
            return None
        ex = f'√({a} · {b}) · √{c}'
        e = f'√({a}·{b}·{c}) = √{a * b * c} = {val}.'
    else:  # c√a·d√b·√e
        c1, c2 = r.randint(2, 9), r.randint(2, 9)
        a, b = r.sample([2, 3, 5, 7, 11, 13, 17], 2)
        e_ = a * b * r.choice([1, 4])
        val = c1 * c2 * math.isqrt(a * b * e_)
        if math.isqrt(a * b * e_) ** 2 != a * b * e_:
            return None
        ex = f'{c1}√{a} · {c2}√{b} · √{e_}'
        e = f'{c1}·{c2}·√({a}·{b}·{e_}) = {c1 * c2}·{math.isqrt(a * b * e_)} = {val}.'
    return _f8(r, ex, val, e)


@proto('og08-sqrt-powers', 'oge', 8, 'Корень из произведения степеней',
       invariant='√(pᵐ·qⁿ) или √(pᵐ) с чётными показателями: корень делит показатель пополам.',
       varies='Основания, чётные показатели, число множителей.',
       answer_rule='√(p²ᵏ) = pᵏ; корень из произведения — произведение корней.',
       fipi=r'√\s*\(\s*\d+\s+\d+\s*(?:[·⋅]\s*\d+\s+\d+\s*)?\)\s*\.',
       mistakes=['извлекают корень только из одного множителя', 'делят основание, а не показатель'], kim=K8)
def gen_og08_sqrt_powers(r):
    if r.random() < 0.7:
        p, q_ = r.sample([2, 3, 5, 7, 11], 2)
        m, n = r.choice([2, 4, 6, 8]), r.choice([2, 4, 6])
        val = p ** (m // 2) * q_ ** (n // 2)
        if val > 3000:
            return None
        ex = f'√({p}{sup(m)} · {q_}{sup(n)})'
        e = f'√({p}{sup(m)}·{q_}{sup(n)}) = {p}{sup(m // 2)}·{q_}{sup(n // 2)} = {val}.'
    else:
        p, m = r.choice([2, 3, 5, 7, 11, 13]), r.choice([4, 6, 8, 10])
        val = p ** (m // 2)
        if val > 3000:
            return None
        ex = f'√({p}{sup(m)})'
        e = f'√({p}{sup(m)}) = {p}{sup(m // 2)} = {val}.'
    return _f8(r, ex, val, e.replace('¹', ''))


@proto('og08-sqrt-square', 'oge', 8, 'Квадрат выражения с корнем в дроби',
       invariant='(c√b)²/k или k/(c√b)²: возведение в квадрат произведения числа и корня.',
       varies='Коэффициент, подкоренное число, делимое/делитель.',
       answer_rule='(c√b)² = c²·b, затем деление.',
       fipi=r'\(\s*\d+\s*√\s*\(\s*\d+\s*\)\s*\)\s*2',
       mistakes=['возводят в квадрат только корень', 'пишут (c√b)² = c·b'], kim=K8)
def gen_og08_sqrt_square(r):
    c, b = r.randint(2, 9), r.choice(_sq_free())
    k = r.choice([2, 3, 4, 5, 6, 8, 10, 12, 15, 18, 20, 24, 30, 36, 40, 45, 48, 60, 72, 90, 96, 120])
    sq = c * c * b
    if r.random() < 0.5:
        val = F(sq, k)
        ex = f'({c}√{b})² / {k}'
    else:
        val = F(k, sq)
        ex = f'{k} / ({c}√{b})²'
    if not nice(val, 2):
        return None
    return _f8(r, ex, val, f'({c}√{b})² = {c * c}·{b} = {sq}; итог {tnum(val)}.')


@proto('og08-sqrt-conj', 'oge', 8, 'Произведение сопряжённых выражений с корнями',
       invariant='(√a − b)(√a + b) или (√a − √b)(√a + √b): формула разности квадратов.',
       varies='Числа под корнями, свободный член, порядок множителей, коэффициент при корне.',
       answer_rule='(x − y)(x + y) = x² − y².',
       fipi=r'\(\s*\d*\s*√\s*\(\s*\d+\s*\)\s*[−-]\s*\d*\s*√?\s*\(?\s*\d+\s*\)?\s*\)\s*\(',
       mistakes=['забывают возвести в квадрат число без корня', 'пишут a − b вместо a − b²'], kim=K8)
def gen_og08_sqrt_conj(r):
    a = r.choice([x for x in range(20, 99) if math.isqrt(x) ** 2 != x])
    k = r.choice([1, 1, 1, 2, 3])
    X_ = f'{k if k > 1 else ""}√{a}'
    if r.random() < 0.5:
        b = r.randint(1, 12)
        val = k * k * a - b * b
        Y_ = f'{b}'
    else:
        b = r.choice([x for x in range(20, 99) if math.isqrt(x) ** 2 != x and x != a])
        val = k * k * a - b
        Y_ = f'√{b}'
    if r.random() < 0.4:
        X_, Y_, val = Y_, X_, -val
    ex = f'({X_} − {Y_})({X_} + {Y_})' if r.random() < 0.5 else f'({X_} + {Y_})({X_} − {Y_})'
    return _f8(r, ex, val, f'Разность квадратов: ({X_})² − ({Y_})² = {tnum(val)}.')


@proto('og08-sqrt-binom', 'oge', 8, 'Квадрат суммы (разности) с корнем',
       invariant='(√a ± b)² ∓ 2b√a: удвоенное произведение взаимно уничтожается.',
       varies='Числа, знак, форма выражения.',
       answer_rule='Раскрываем квадрат: a ± 2b√a + b², удвоенное произведение сокращается; ответ a + b².',
       fipi=r'\(\s*√\s*\(\s*\d+\s*\)\s*[+−-]\s*\d+\s*\)\s*2\s*[+−-]\s*\d+\s*√',
       mistakes=['забывают удвоенное произведение', '(√a − b)² считают как a − b²'], kim=K8)
def gen_og08_sqrt_binom(r):
    a = r.choice([x for x in range(2, 60) if math.isqrt(x) ** 2 != x])
    b = r.randint(1, 9)
    sgn = r.choice('+−')
    val = a + b * b
    ex = f'(√{a} {sgn} {b})² {"−" if sgn == "+" else "+"} {2 * b}√{a}'
    return _f8(r, ex, val, f'(√{a} {sgn} {b})² = {a} {sgn} {2 * b}√{a} + {b * b}; остаётся {a} + {b * b} = {val}.')


@proto('og08-sqrt-distrib', 'oge', 8, 'Скобка с корнями, умноженная на корень',
       invariant='(√a ± √b)·√b, где a·b — точный квадрат: раскрываем скобку.',
       varies='Подкоренные числа (a = k²b), знак.',
       answer_rule='√a·√b = √(ab) = k·b, √b·√b = b; складываем или вычитаем.',
       fipi=r'\(\s*√\s*\(\s*\d+\s*\)\s*[+−-]\s*√\s*\(\s*\d+\s*\)\s*\)\s*[·⋅]\s*√',
       mistakes=['умножают только первое слагаемое', '√b·√b = √b'], kim=K8)
def gen_og08_sqrt_distrib(r):
    b = r.choice(_sq_free())
    k = r.randint(2, 7)
    a = k * k * b
    if a > 400:
        return None
    sgn = r.choice('+−')
    val = k * b + b if sgn == '+' else k * b - b
    ex = f'(√{a} {sgn} √{b}) · √{b}'
    return _f8(r, ex, val, f'√{a}·√{b} = √{a * b} = {k * b}, √{b}·√{b} = {b}; итог {val}.')


@proto('og08-sqrt-recip', 'oge', 8, 'Сумма обратных к сопряжённым',
       invariant='1/(a + √b) + 1/(a − √b) (или c/…): общий знаменатель — разность квадратов.',
       varies='a, b, числитель c.',
       answer_rule='Общий знаменатель a² − b; числитель 2ac.',
       fipi=r'значение выражения\s+\d+\s+\d+\s*\+\s*√\s*\(\s*\d+\s*\)\s*\+\s*\d+\s+\d+\s*[−-]\s*√',
       mistakes=['складывают знаменатели', 'ошибка в знаке a² − b'], kim=K8)
def gen_og08_sqrt_recip(r):
    a = r.randint(3, 9)
    b = r.choice([x for x in range(6, a * a + 30) if math.isqrt(x) ** 2 != x and x != a * a])
    c = r.choice([2, 3, 4, 5, 6, 1]) if a > 4 else r.choice([2, 3, 4, 5, 6])
    D = a * a - b
    val = F(2 * a * c, D)
    if not nice(val, 2) or abs(D) > 40:
        return None
    ex = f'{c}/({a} + √{b}) + {c}/({a} − √{b})'
    return _f8(r, ex, val, f'Общий знаменатель ({a} + √{b})({a} − √{b}) = {a * a} − {b} = {tnum(D)}; числитель {2 * a * c}; итого {tnum(val)}.')


@proto('og08-sqrt-poly', 'oge', 8, 'Корень из полного квадрата при заданных значениях',
       invariant='√(a² ± 2kab + k²b²) = |a ± kb|: свернуть по формуле квадрата суммы/разности и подставить (значения — дроби, смешанные числа).',
       varies='Коэффициент k, знак, буквы, значения (подобраны так, что a ± kb — «круглое» число).',
       answer_rule='Сворачиваем подкоренное выражение в квадрат, извлекаем корень с модулем, подставляем.',
       fipi=r'√\s*\(\s*\d*\s*[a-z]\s*2\s*[+−-]\s*\d+\s*[a-z]\s*[a-z]\s*\+\s*\d*\s*[a-z]\s*2\s*\)',
       mistakes=['забывают модуль (ответ отрицательный)', 'подставляют без свёртки и ошибаются в дробях'], kim=K8a)
def gen_og08_sqrt_poly(r):
    va, vb = r.choice([('a', 'b'), ('x', 'y'), ('m', 'n'), ('p', 'q'), ('c', 'd')])
    k = r.choice([2, 3, 4, 5])
    first_k = r.random() < 0.35
    sg = r.choice([1, -1])
    target = r.randint(1, 12) * r.choice([1, 1, -1])
    d = r.choice([3, 5, 7, 9, 11, 13])
    bv = F(r.randint(1, 3 * d), d)
    if bv.denominator == 1:
        return None
    if first_k:  # √(k²a² ± 2kab + b²) = |ka ± b|
        av = (target - sg * bv) / k
        inner = f'{k * k}{va}² {"+" if sg > 0 else "−"} {2 * k}{va}{vb} + {vb}²'
        form = f'|{k}{va} {"+" if sg > 0 else "−"} {vb}|'
    else:  # √(a² ± 2kab + k²b²) = |a ± kb|
        av = target - sg * k * bv
        inner = f'{va}² {"+" if sg > 0 else "−"} {2 * k}{va}{vb} + {k * k}{vb}²'
        form = f'|{va} {"+" if sg > 0 else "−"} {k}{vb}|'
    if av == 0 or av.denominator > 60:
        return None
    val = abs(target)
    show = lambda x: mixed(x) if x > 1 and x.denominator > 1 and r.random() < 0.6 else fr(x)
    ex = f'√({inner})'
    q = f'{pick(r, "Найдите значение выражения", "Вычислите значение выражения")} {ex} при {va} = {show(av)} и {vb} = {show(bv)}.'
    e = f'√({inner}) = {form}; подставляем: |{tnum(target)}| = {val}.'
    S = {sp.Symbol(va): R(av), sp.Symbol(vb): R(bv)}
    return pcard(q, num(val), e=e), lambda: same(num(val), parse(ex).subs(S))


@proto('og08-sqrt-mono', 'oge', 8, 'Корень из одночлена при заданных значениях',
       invariant='√(c·xᵐ·yⁿ) или √(aᵖ·(−a)ᵍ) с чётными показателями: вынести из-под корня и подставить.',
       varies='Коэффициент (точный квадрат, в т. ч. дробь 1/16), показатели, значения переменных.',
       answer_rule='√(x²ᵏ) = |xᵏ|; подставляем значения (удобнее после упрощения).',
       fipi=r'√\s*\(\s*\d*\s*\d*\s*[⋅·]?\s*\(?\s*[−-]?\s*[a-z]\s*\)?\s*\d+\s*[·⋅]?\s*\(?\s*[−-]?\s*[a-z]\s*\)?\s*\d+\s*\)\s*при',
       mistakes=['делят на 2 основание вместо показателя', 'теряют модуль'], kim=K8a)
def gen_og08_sqrt_mono(r):
    if r.random() < 0.6:
        vx, vy = r.choice([('m', 'n'), ('p', 'q'), ('c', 'd'), ('u', 'v')])
        c = r.choice([F(9), F(25), F(36), F(49), F(1, 9), F(1, 25), F(1, 36), F(4, 9), F(9, 4)])
        m, n = r.choice([2, 4, 6]), r.choice([2, 4, 6])
        X0, Y0 = r.randint(2, 7), r.randint(2, 7)
        val = math.isqrt(c.numerator) * F(1, math.isqrt(c.denominator)) * X0 ** (m // 2) * Y0 ** (n // 2)
        if not nice(val, 2) or val > 3000:
            return None
        cs = fr(c) if c.denominator == 1 else f'{fr(c)} ·'
        ex = f'√({cs}{vx}{sup(m)}{vy}{sup(n)})' if c.denominator == 1 else f'√({fr(c)} · {vx}{sup(m)}{vy}{sup(n)})'
        q = f'{pick(r, "Найдите значение выражения", "Вычислите значение выражения")} {ex} при {vx} = {X0} и {vy} = {Y0}.'
        S = {sp.Symbol(vx): X0, sp.Symbol(vy): Y0}
        e = f'√({fr(c)}·{vx}{sup(m)}{vy}{sup(n)}) = {fr(F(math.isqrt(c.numerator), math.isqrt(c.denominator)))}·{vx}{sup(m // 2)}·{vy}{sup(n // 2)} = {tnum(val)}.'.replace('¹', '')
    else:
        v = r.choice(['a', 'b', 'x', 'c'])
        p_, q2 = r.choice([2, 4, 6, 8, 10]), r.choice([2, 4, 6])
        A = r.choice([2, 3, -2, -3, 5])
        val = abs(A) ** ((p_ + q2) // 2)
        if val > 5000:
            return None
        ex = pick(r, f'√({v}{sup(p_)} · (−{v}){sup(q2)})', f'√((−{v}){sup(q2)} · {v}{sup(p_)})')
        q = f'{pick(r, "Найдите значение выражения", "Вычислите значение выражения")} {ex} при {v} = {tnum(A)}.'
        S = {sp.Symbol(v): A}
        e = f'(−{v}){sup(q2)} = {v}{sup(q2)}, поэтому корень равен |{v}{sup((p_ + q2) // 2)}| = {val}.'
    return pcard(q, num(val), e=e), lambda: same(num(val), sp.simplify(parse(ex).subs(S)))


# ================================================================ №9 — уравнения

K9 = K(minutes=3, kes=['3.1'], kt=[5], style='«Решите уравнение …» / «Найдите корень уравнения …»; при двух корнях — «в ответ запишите больший/меньший из корней»')
ASK9 = ('Решите уравнение', 'Найдите корень уравнения', 'Решите уравнение')
TWO = ('Если корней несколько, запишите в ответ {w} из них.',
       'Когда корней больше одного, в ответ нужно записать {w} из них.',
       'При наличии нескольких корней укажите в ответе {w}.')
ONE = ('Решите уравнение {eq}. В ответ запишите найденный корень.',
       'Найдите корень уравнения {eq} и запишите его в ответ.',
       'При каком значении x верно равенство {eq}?',
       'Найдите значение x, при котором выполняется равенство {eq}.')


def _roots_card(r, eq_txt, roots, e, lhs, rhs):
    roots = sorted(set(roots))
    if not any(nice(x, 2) for x in roots):
        return None
    if len(roots) > 1:
        which = r.choice([w for w, x in (('min', roots[0]), ('max', roots[-1])) if nice(x, 2)])
        ans = roots[0] if which == 'min' else roots[-1]
        q = f'{pick(r, "Решите уравнение", "Найдите корни уравнения")} ⟦{eq_txt}⟧. ' + pick(r, *TWO).format(w='меньший' if which == 'min' else 'больший')
    else:
        which, ans = None, roots[0]
        q = pick(r, *ONE).format(eq=f'⟦{eq_txt}⟧')

    def chk():
        sol = sorted(s_ for s_ in sp.solve(sp.Eq(parse(lhs), parse(rhs)), sp.Symbol('x')) if s_.is_real)
        if len(sol) != len(roots):
            return False
        want = sol[0] if which != 'max' else sol[-1]
        return same(num(ans), want)
    return pcard(q, num(ans), e=e), chk


@proto('og09-lin', 'oge', 9, 'Линейное уравнение',
       invariant='ax + b = cx + d: переносим члены с x в одну сторону, числа — в другую.',
       varies='Коэффициенты (в т. ч. отрицательные), расположение x, формулировка инструкции.',
       answer_rule='x = (d − b)/(a − c); ответ — целое или конечная десятичная дробь.',
       fipi=r'Найдите корень уравнения\s+[−-]?\s*\d*\s*x\s*[+−-]\s*\d+\s*=\s*[−-]?\s*\d*\s*x',
       mistakes=['не меняют знак при переносе', 'делят не на тот коэффициент'], kim=K9)
def gen_og09_lin(r):
    a, c = r.randint(-12, 12), r.randint(-12, 12)
    b, d = r.randint(-30, 30), r.randint(-30, 30)
    if a == c or a == 0 or b == 0:
        return None
    x0 = F(d - b, a - c)
    if not nice(x0, 2):
        return None
    lhs, rhs = lin(a, b), lin(c, d) if c else tnum(d)
    return _roots_card(r, f'{lhs} = {rhs}', [x0], (f'{lin(a - c, 0)} = {tnum(d - b)}, ' if a - c != 1 else '') + f'x = {tnum(x0)}.', lhs, rhs)


@proto('og09-lin-brackets', 'oge', 9, 'Линейное уравнение со скобками',
       invariant='a(x − b) − c(x + d) = e или a(x + b) = c(x + d) + e: раскрываем скобки, получаем линейное уравнение.',
       varies='Коэффициенты перед скобками, числа внутри, знак между скобками.',
       answer_rule='Раскрываем скобки (с учётом минуса), приводим подобные и решаем.',
       fipi=r'\d\s*\(\s*x\s*[+−-]\s*\d+\s*\)\s*[+−-=]\s*\d*\s*\(?\s*x?',
       mistakes=['минус перед скобкой меняет знак только первого слагаемого', 'не умножают второе слагаемое в скобке'], kim=K9)
def gen_og09_lin_brackets(r):
    a, c = r.randint(3, 12), r.randint(3, 9)
    b, d = r.randint(1, 12) * r.choice([1, -1]), r.randint(1, 12) * r.choice([1, -1])
    sg = r.choice([1, -1])
    e_ = r.randint(-20, 20)
    ins = lambda k: f'x {"+" if k > 0 else "−"} {abs(k)}'
    kind = r.randrange(3)
    if kind == 0:
        lhs, rhs = f'{a}({ins(b)})', tnum(e_)
        A, B = a, a * b - e_
    elif kind == 1:
        lhs = f'{a}({ins(b)}) {"+" if sg > 0 else "−"} {c}({ins(d)})'
        rhs = tnum(e_)
        A, B = a + sg * c, a * b + sg * c * d - e_
    else:
        lhs = f'{a}({ins(b)})'
        rhs = f'{c}({ins(d)})' + (signed(e_) if e_ else '')
        A, B = a - c, a * b - c * d - e_
    if A == 0:
        return None
    x0 = F(-B, A)
    if not nice(x0, 2):
        return None
    return _roots_card(r, f'{lhs} = {rhs}', [x0], f'Раскрываем скобки: {lin(A, B)} = 0, x = {tnum(x0)}.', lhs, rhs)


@proto('og09-quad', 'oge', 9, 'Полное квадратное уравнение',
       invariant='ax² + bx + c = 0 с двумя корнями (рациональными); в ответ — больший или меньший корень.',
       varies='Корни (целые и дробные), старший коэффициент, «больший/меньший».',
       answer_rule='Дискриминант или теорема Виета; выбираем нужный корень.',
       fipi=r'x\s*2\s*[+−-]\s*\d*\s*x\s*[+−-]\s*\d+\s*=\s*0',
       mistakes=['ошибка в знаке −b', 'делят только на a, а не на 2a', 'записывают не тот корень'], kim=K9)
def gen_og09_quad(r):
    a = r.choice([1, 1, 1, 2, 3, 4, 5, 6])
    p1 = F(r.randint(-12, 12), r.choice([1, 1, a]) if a > 1 else 1)
    p2 = F(r.randint(-12, 12))
    if p1 == p2 or p1 == 0 and p2 == 0:
        return None
    co = [a, -a * (p1 + p2), a * p1 * p2]
    if any(F(k).denominator != 1 for k in co) or co[1] == 0 or co[2] == 0:
        return None
    if a > 1 and math.gcd(math.gcd(int(co[0]), int(co[1])), int(co[2])) != 1:
        return None
    txt = f'{poly(co)} = 0'
    D = co[1] ** 2 - 4 * co[0] * co[2]
    return _roots_card(r, txt, [p1, p2], f'D = {tnum(D)}, корни {fr(min(p1, p2))} и {fr(max(p1, p2))}.', poly(co), '0')


@proto('og09-quad-incomplete', 'oge', 9, 'Неполное квадратное уравнение',
       invariant='ax² + bx = 0 (вынести x) или ax² − c = 0 (корни ±√(c/a)).',
       varies='Коэффициенты, вид (без свободного члена / без x), «больший/меньший».',
       answer_rule='Выносим x за скобку или выражаем x²; второй корень не теряем.',
       fipi=r'x\s*2\s*[+−-]\s*\d+\s*x\s*=\s*0|\d*\s*x\s*2\s*[+−-]\s*\d+\s*=\s*0|x\s*2\s*=\s*\d*\s*x\s*\.',
       mistakes=['делят на x и теряют корень 0', 'берут только положительный корень'], kim=K9)
def gen_og09_quad_incomplete(r):
    a = r.choice([1, 2, 3, 4, 5, 6, 7, 8, 9])
    if r.random() < 0.5:
        root = F(r.randint(1, 30), r.choice([1, 1, 2, 4, 5]) if a > 1 else 1) * r.choice([1, -1])
        b = -a * root
        if F(b).denominator != 1:
            return None
        if r.random() < 0.5:
            txt, lhs, rhs = f'{poly([a, b, 0])} = 0', poly([a, b, 0]), '0'
        else:
            txt, lhs, rhs = f'{poly([a, 0, 0])} = {lin(-b, 0)}', poly([a, 0, 0]), lin(-b, 0)
        return _roots_card(r, txt, [F(0), root], f'x({lin(a, b)}) = 0: x = 0 или x = {tnum(root)}.', lhs, rhs)
    root = F(r.randint(1, 12), r.choice([1, 1, 2, 5, 10]))
    c = a * root * root
    if c.denominator != 1:
        return None
    txt, lhs, rhs = (f'{poly([a, 0, -c])} = 0', poly([a, 0, -c]), '0') if r.random() < 0.6 else (f'{poly([a, 0, 0])} = {tnum(c)}', poly([a, 0, 0]), tnum(c))
    return _roots_card(r, txt, [root, -root], f'x² = {tnum(c / a)}, x = ±{tnum(root)}.', lhs, rhs)


# ================================================================ №10 — вероятность

K10 = K(minutes=3, kes=['8.2'], kt=[15], style='«Найдите вероятность того, что …»; ответ — десятичная дробь (при необходимости «Результат округлите до сотых»)')


def _pnoun(n, forms):
    return f'{n} {plural(n, *forms)}'


def _round2(x):
    """Округление до сотых (половина — вверх), как требует КИМ."""
    return F(math.floor(F(x) * 100 + F(1, 2)), 100)


# сюжеты «две категории»: предмет, род («он/она/оно»), место, действие, категории
# (род. мн. — «синих среди них», им. мн. — «остальные — синие», твор. ед. — «окажется синим»)
TWO_CAT = [
    dict(where='В коробке лежат', noun=('ёлочная игрушка', 'ёлочные игрушки', 'ёлочных игрушек'), act='Малыш, не глядя, достаёт одну игрушку.',
         obj='вынутая игрушка', cats=[('стеклянных', 'стеклянные', 'стеклянной'), ('пластиковых', 'пластиковые', 'пластиковой')]),
    dict(where='На полке стоят', noun=('книга', 'книги', 'книг'), act='Читатель берёт с полки одну книгу наугад.',
         obj='взятая книга', cats=[('детективов', 'детективы', 'детективом'), ('фантастических романов', 'фантастические романы', 'фантастическим романом')]),
    dict(where='На парковке у офиса стоят', noun=('электросамокат', 'электросамоката', 'электросамокатов'), act='Приложение выдаёт курьеру случайный самокат.',
         obj='выданный самокат', cats=[('синих', 'синие', 'синим'), ('чёрных', 'чёрные', 'чёрным')]),
    dict(where='В корзине лежат', noun=('яблоко', 'яблока', 'яблок'), act='Повар наугад берёт одно яблоко.',
         obj='взятое яблоко', cats=[('красных', 'красные', 'красным'), ('зелёных', 'зелёные', 'зелёным')]),
    dict(where='В наборе', noun=('фломастер', 'фломастера', 'фломастеров'), act='Художница вынимает из набора один фломастер наугад.',
         obj='вынутый фломастер', cats=[('тёмных оттенков', 'тёмных оттенков', 'тёмного оттенка'), ('светлых оттенков', 'светлых оттенков', 'светлого оттенка')]),
    dict(where='На противне остывают', noun=('булочка', 'булочки', 'булочек'), act='Мама берёт одну булочку наугад.',
         obj='взятая булочка', cats=[('с маком', 'с маком', 'с маком'), ('с корицей', 'с корицей', 'с корицей')], prep=True),
    dict(where='Для викторины подготовлены', noun=('карточка с вопросом', 'карточки с вопросами', 'карточек с вопросами'), act='Ведущий вытягивает одну карточку наугад.',
         obj='вопрос на вытянутой карточке', cats=[('по истории', 'по истории', 'по истории'), ('по географии', 'по географии', 'по географии')], prep=True, verb='будет'),
    dict(where='В пункте проката есть', noun=('велосипед', 'велосипеда', 'велосипедов'), act='Посетителю выдают случайный свободный велосипед; сейчас свободны все.',
         obj='выданный велосипед', cats=[('горных', 'горные', 'горным'), ('городских', 'городские', 'городским')]),
    dict(where='В вазе стоят', noun=('тюльпан', 'тюльпана', 'тюльпанов'), act='Девочка вынимает из вазы один цветок наугад.',
         obj='вынутый тюльпан', cats=[('жёлтых', 'жёлтые', 'жёлтым'), ('белых', 'белые', 'белым')]),
    dict(where='В плейлисте', noun=('песня', 'песни', 'песен'), act='Плеер включён в режиме случайного выбора.',
         obj='первая прозвучавшая песня', cats=[('на русском языке', 'на русском языке', 'на русском языке'), ('на английском языке', 'на английском языке', 'на английском языке')], prep=True, verb='будет'),
    dict(where='В холодильнике магазина стоят', noun=('бутылка сока', 'бутылки сока', 'бутылок сока'), act='Покупатель берёт одну бутылку, не глядя.',
         obj='взятая бутылка', cats=[('с яблочным соком', 'с яблочным соком', 'с яблочным соком'), ('с томатным соком', 'с томатным соком', 'с томатным соком')], prep=True),
    dict(where='В ящике лежат', noun=('мяч', 'мяча', 'мячей'), act='Тренер достаёт из ящика один мяч наугад.',
         obj='вынутый мяч', cats=[('волейбольных', 'волейбольные', 'волейбольным'), ('баскетбольных', 'баскетбольные', 'баскетбольным')]),
]


def _two_cat_text(r, c, N, k, ask):
    A, B = c['cats'] if r.random() < 0.5 else c['cats'][::-1]
    head = f'{c["where"]} {_pnoun(N, c["noun"])}.'
    if c.get('prep'):
        mid = f'Из них {k} — {A[1]}, остальные — {B[1]}.'
    else:
        mid = f'{A[0].capitalize()} среди них — {k}, остальные — {B[1]}.'
    tgt = A if ask == 'A' else B
    verb = c.get('verb', 'окажется')
    return f'{head} {mid} {c["act"]} Найдите вероятность того, что {c["obj"]} {verb} {tgt[2]}.'


TICKETS = [
    ('К зачёту по физике подготовлено {N} {n1}, {name} не успел разобрать {k} из них.', ('вопрос', 'вопроса', 'вопросов'),
     'Найдите вероятность того, что {name2} достанется разобранный вопрос.'),
    ('На олимпиаде по информатике случайным образом выдаётся одна из {N} {n1}; {name} умеет решать все, кроме {k}.', ('задача', 'задачи', 'задач'),
     'Найдите вероятность того, что {name2} попадётся задача, которую он умеет решать.'),
    ('Для устного экзамена по истории составлено {N} {n1}. {name} плохо знает материал {k} из них.', ('карточка', 'карточки', 'карточек'),
     'Какова вероятность того, что {name2} выпадет карточка с хорошо знакомым материалом?'),
]
BOYS = [('Тимур', 'Тимуру'), ('Глеб', 'Глебу'), ('Арсений', 'Арсению'), ('Родион', 'Родиону'), ('Ярослав', 'Ярославу'), ('Мирон', 'Мирону')]
GIFTS = [
    ('Для {N} {n1} летнего лагеря купили {N} настольных игр: {k} — стратегии, остальные — головоломки. Игры раздают случайным образом, одну каждому; среди участников есть {name}.',
     ('участник', 'участников', 'участников'), 'Найдите вероятность того, что {name2} достанется {what}.', ('стратегия', 'головоломка')),
    ('Школа подготовила {N} подарочных наборов для {N} {n1}: в {k} наборах — книги, в остальных — конструкторы. Наборы распределяются случайно; среди победителей есть {name}.',
     ('победитель олимпиады', 'победителей олимпиады', 'победителей олимпиады'), 'Найдите вероятность того, что {name2} достанется набор, в котором {what}.', ('книга', 'конструктор')),
]
THREE = [
    ('На стоянке каршеринга свободно {N} автомобилей: {a} белых, {b} серых и {c} красных. Приложение назначает клиенту случайный свободный автомобиль.',
     'Найдите вероятность того, что клиенту достанется {w} автомобиль.', ('белый', 'серый', 'красный')),
    ('В вольере приюта {N} щенков: {a} рыжих, {b} чёрных и {c} пятнистых. Волонтёр наугад берёт одного щенка на прогулку.',
     'Найдите вероятность того, что на прогулку пойдёт {w} щенок.', ('рыжий', 'чёрный', 'пятнистый')),
    ('В сувенирной лавке на полке стоят {N} кружек: {a} синих, {b} зелёных и {c} белых. Покупатель, не выбирая, берёт одну.',
     'Найдите вероятность того, что взятая кружка окажется {w}.', ('синей', 'зелёной', 'белой')),
]


@proto('og10-classic', 'oge', 10, 'Классическая вероятность: доля благоприятных исходов',
       invariant='N равновозможных исходов, из них k благоприятных (одна из групп, «невыученные билеты», случайная раздача подарков); P = k/N.',
       varies='Сюжет (игрушки, книги, самокаты, вопросы к зачёту, подарки, три группы…), N, k, спрашиваемая группа.',
       answer_rule='P = число благоприятных / общее число; если спрашивают про «остальных» — сначала вычитаем.',
       fipi=r'(не выучил|остальные с|свободно \d+ машин|распределяются случайным|лежат \d+.{0,40}маркер|Найдите вероятность того, что .{0,60}(окажется|будет чашка))',
       mistakes=['делят k на N − k', 'находят вероятность не той группы'], maxdec=4, kim=K10)
def gen_og10_classic(r):
    kind = r.choice(['two', 'two', 'tickets', 'gifts', 'three'])
    N = r.choice([10, 12, 15, 16, 20, 20, 24, 25, 25, 30, 40, 50, 60, 75, 80])
    if kind == 'two':
        c = r.choice(TWO_CAT)
        k = r.randint(1, N - 1)
        ask = r.choice('AB')
        fav = k if ask == 'A' else N - k
        q = _two_cat_text(r, c, N, k, ask)
    elif kind == 'tickets':
        head, nn, tail = r.choice(TICKETS)
        name, name2 = r.choice(BOYS)
        k = r.randint(1, N // 3)
        fav = N - k
        q = head.format(N=N, n1=plural(N, *nn), name=name, k=k) + ' ' + tail.format(name2=name2)
    elif kind == 'gifts':
        head, nn, tail, whats = r.choice(GIFTS)
        if N > 30:
            return None
        name, name2 = r.choice(BOYS)
        k = r.randint(1, N - 1)
        j = r.randrange(2)
        fav = k if j == 0 else N - k
        q = head.format(N=N, n1=plural(N, *nn), k=k, name=name) + ' ' + tail.format(name2=name2, what=whats[j])
    else:
        head, tail, ws = r.choice(THREE)
        a_, b_ = r.randint(1, N // 2), r.randint(1, N // 2)
        c_ = N - a_ - b_
        if c_ < 1:
            return None
        j = r.randrange(3)
        fav = (a_, b_, c_)[j]
        k = fav
        q = head.format(N=N, a=a_, b=b_, c=c_) + ' ' + tail.format(w=ws[j])
    p = F(fav, N)
    if not nice(p, 3):
        return None
    e = f'Всего равновозможных исходов {N}, благоприятных {fav}: P = {fav}/{N} = {tnum(p)}.'
    return pcard(q, num(p), e=e), lambda: same(num(p), sp.Rational(sum(1 for i in range(N) if i < fav), N))


MULTI = [
    dict(where='В ящике лежат', noun=('теннисный мяч', 'теннисных мяча', 'теннисных мячей'), obj='вынутый наугад мяч', g='m',
         cats=[('белых', 'белым'), ('оранжевых', 'оранжевым'), ('жёлтых', 'жёлтым'), ('зелёных', 'зелёным'), ('розовых', 'розовым')], rest=('зелёные и розовые', 3, 4)),
    dict(where='В пачке', noun=('чайный пакетик', 'чайных пакетика', 'чайных пакетиков'), obj='вынутый наугад пакетик', g='m',
         cats=[('с чёрным чаем', 'с чёрным чаем'), ('с зелёным чаем', 'с зелёным чаем'), ('с травяным сбором', 'с травяным сбором'), ('с мятой', 'с мятой'), ('с чабрецом', 'с чабрецом')], rest=('с мятой и с чабрецом', 3, 4), prep=True),
    dict(where='В гардеробной театра висят', noun=('костюм', 'костюма', 'костюмов'), obj='выбранный наугад костюм', g='m',
         cats=[('красных', 'красным'), ('синих', 'синим'), ('золотистых', 'золотистым'), ('белых', 'белым'), ('чёрных', 'чёрным')], rest=('белые и чёрные', 3, 4)),
    dict(where='В коробке с конфетами', noun=('конфета', 'конфеты', 'конфет'), obj='взятая наугад конфета', g='f',
         cats=[('с орехом', 'с орехом'), ('с карамелью', 'с карамелью'), ('с кокосом', 'с кокосом'), ('с вишней', 'с вишней'), ('с апельсином', 'с апельсином')], rest=('с вишней и с апельсином', 3, 4), prep=True),
    dict(where='В таксопарке', noun=('автомобиль', 'автомобиля', 'автомобилей'), obj='автомобиль, случайно назначенный на заказ,', g='m',
         cats=[('жёлтых', 'жёлтым'), ('белых', 'белым'), ('синих', 'синим'), ('зелёных', 'зелёным'), ('оранжевых', 'оранжевым')], rest=('зелёные и оранжевые', 3, 4)),
    dict(where='В корзине для рукоделия', noun=('моток пряжи', 'мотка пряжи', 'мотков пряжи'), obj='вынутый наугад моток', g='m',
         cats=[('серых', 'серым'), ('бежевых', 'бежевым'), ('голубых', 'голубым'), ('сиреневых', 'сиреневым'), ('мятных', 'мятным')], rest=('сиреневые и мятные', 3, 4)),
]


@proto('og10-union', 'oge', 10, 'Вероятность: несколько групп, «остальные поровну», событие «или»',
       invariant='Предметы нескольких видов; оставшиеся делятся поровну между двумя видами; найти вероятность события «вид A или вид B».',
       varies='Сюжет, количества, какие два вида объединяются.',
       answer_rule='Находим количество «остальных», делим пополам; складываем благоприятные и делим на общее число.',
       fipi=r'(поровну|остальные).{0,150}(или)',
       mistakes=['забывают поделить остаток поровну', 'считают вероятность одного вида'], maxdec=4, kim=K10)
def gen_og10_union(r):
    c = r.choice(MULTI)
    N = r.choice([40, 50, 60, 80, 100, 120, 150, 200, 250])
    a = [r.randint(N // 12, N // 4) for _ in range(3)]
    rest = N - sum(a)
    if rest <= 0 or rest % 2:
        return None
    each = rest // 2
    i = r.randrange(3)
    j = r.choice([3, 4])
    fav = a[i] + each
    p = F(fav, N)
    if not nice(p, 3):
        return None
    cats = c['cats']
    lst = ', '.join(f'{cats[t][0]} — {a[t]}' for t in range(3))
    q = (f'{c["where"]} {_pnoun(N, c["noun"])}: {lst}, остальные — {c["rest"][0]}, причём их поровну. '
         f'Найдите вероятность того, что {c["obj"]} {"окажется" if not c.get("prep") else "будет"} {cats[i][1]} или {cats[j][1]}.')
    e = f'{c["rest"][0].capitalize()}: ({N} − {sum(a)}) : 2 = {each} каждого вида. Благоприятных {a[i]} + {each} = {fav}; P = {fav}/{N} = {tnum(p)}.'
    pool = [0] * a[0] + [1] * a[1] + [2] * a[2] + [3] * each + [4] * each
    return pcard(q, num(p), e=e), lambda: len(pool) == N and same(num(p), sp.Rational(sum(1 for x in pool if x in (i, j)), N))


DEFECT = [
    (('электрический чайник', 'электрических чайника', 'электрических чайников'), 'купленный в магазине чайник', ('исправен', 'неисправен')),
    (('беспроводные наушники', 'пары беспроводных наушников', 'пар беспроводных наушников'), 'купленная пара наушников', ('исправна', 'неисправна')),
    (('зарядное устройство', 'зарядных устройства', 'зарядных устройств'), 'купленное зарядное устройство', ('исправно', 'неисправно')),
    (('настольная лампа', 'настольные лампы', 'настольных ламп'), 'случайно выбранная в магазине лампа', ('исправна', 'неисправна')),
    (('фен', 'фена', 'фенов'), 'случайно выбранный в магазине фен', ('исправен', 'неисправен')),
    (('калькулятор', 'калькулятора', 'калькуляторов'), 'случайно выбранный калькулятор', ('исправен', 'неисправен')),
    (('флеш-накопитель', 'флеш-накопителя', 'флеш-накопителей'), 'купленный флеш-накопитель', ('исправен', 'неисправен')),
    (('электронный термометр', 'электронных термометра', 'электронных термометров'), 'купленный термометр', ('исправен', 'неисправен')),
]


@proto('og10-defect', 'oge', 10, 'Вероятность исправного изделия (брак из общего числа)',
       invariant='Из N изделий в среднем k с дефектом; найти вероятность, что случайное изделие исправно (или неисправно).',
       varies='Изделие, N, k, спрашиваемое событие.',
       answer_rule='P(исправно) = (N − k)/N.',
       fipi=r'(неисправн|бракован|подтекают|с дефект).{0,160}Найдите вероятность',
       mistakes=['дают вероятность брака вместо исправности'], maxdec=4, kim=K10)
def gen_og10_defect(r):
    noun, obj, adj = r.choice(DEFECT)
    N = r.choice([200, 250, 400, 500, 800, 1000, 1200, 1500, 2000])
    k = r.randint(2, N // 20)
    good = r.random() < 0.75
    fav = N - k if good else k
    p = F(fav, N)
    if not nice(p, 4):
        return None
    verb = plural(k, 'оказывается', 'оказываются', 'оказываются')
    q = pick(r, f'В среднем из {_pnoun(N, noun)}, поступивших в продажу, {k} {verb} с дефектом. Найдите вероятность того, что {obj} {adj[0] if good else adj[1]}.',
             f'Проверка показала, что из каждых {N} выпущенных {noun[2]} в среднем {k} {verb} с дефектом. Найдите вероятность того, что {obj} {adj[0] if good else adj[1]}.')
    e = f'Исправных {N} − {k} = {N - k}. P = {fav}/{N} = {tnum(p)}.'
    return pcard(q, num(p), e=e), lambda: same(num(p), 1 - sp.Rational(k, N) if good else sp.Rational(k, N))


COMPL = [
    ('новый маркер пишет бледно или не пишет вовсе', 'маркер пишет хорошо', 'Покупатель берёт один маркер'),
    ('купленная батарейка разряжена', 'батарейка заряжена', 'Покупатель берёт одну батарейку с витрины'),
    ('случайно выбранная пачка печенья весит меньше указанного на упаковке', 'пачка весит не меньше указанного', 'Контролёр выбирает одну пачку'),
    ('новый зонт сломается в первый же сезон', 'зонт прослужит сезон без поломок', 'Покупатель выбирает один зонт'),
    ('лампочка в новой гирлянде не горит', 'лампочка горит', 'Мастер проверяет одну случайную лампочку'),
    ('автобус приедет на остановку с опозданием', 'автобус приедет вовремя', 'Пассажир ждёт ближайший автобус'),
]


@proto('og10-complement', 'oge', 10, 'Вероятность противоположного события',
       invariant='Дана вероятность события; найти вероятность противоположного: 1 − p.',
       varies='Сюжет, значение p (сотые).',
       answer_rule='P(не A) = 1 − P(A).',
       fipi=r'равна\s+0,\d+.{0,160}Найдите вероятность',
       mistakes=['повторяют данное p', 'вычитают из 100'], maxdec=4, kim=K10)
def gen_og10_complement(r):
    ev, op, act = r.choice(COMPL)
    p = F(r.randint(2, 40), 100) if r.random() < 0.7 else F(r.randint(2, 40), 1000) * r.choice([1, 2])
    if not nice(p, 3):
        return None
    ans = 1 - p
    q = f'Вероятность того, что {ev}, равна {tnum(p)}. {act}. Найдите вероятность того, что {op}.'
    return pcard(q, num(ans), e=f'Противоположное событие: 1 − {tnum(p)} = {tnum(ans)}.'), lambda: same(num(ans), 1 - R(p))


@proto('og10-dice', 'oge', 10, 'Игральный кубик: один или два броска',
       invariant='Равновозможные исходы броска кубика (6 или 36); событие про сумму, чётность, сравнение.',
       varies='Число бросков, событие (сумма из набора, «больше», «оба раза»), округление.',
       answer_rule='Перечисляем благоприятные исходы и делим на 6 или 36; при необходимости округляем до сотых.',
       fipi=r'(кубик|игральн).{0,120}(сумма|очк)',
       mistakes=['считают исходы (2;3) и (3;2) одним', 'делят на 12 вместо 36'], maxdec=4, kim=K10)
def gen_og10_dice(r):
    two = r.random() < 0.75
    if two:
        kind = r.randrange(4)
        outs = [(a, b) for a in range(1, 7) for b in range(1, 7)]
        if kind == 0:
            S = sorted(r.sample(range(2, 13), r.choice([1, 2, 3])))
            ev = lambda a, b: a + b in S
            txt = f'в сумме выпадет {S[0]} {plural(S[0], "очко", "очка", "очков")}' if len(S) == 1 else 'в сумме выпадет ' + ', '.join(map(str, S[:-1])) + f' или {S[-1]} {plural(S[-1], "очко", "очка", "очков")}'
        elif kind == 1:
            t = r.randint(4, 10)
            sgn = r.choice(['больше', 'меньше'])
            ev = (lambda a, b: a + b > t) if sgn == 'больше' else (lambda a, b: a + b < t)
            txt = f'сумма очков за два броска окажется {sgn} {t}'
        elif kind == 2:
            t = r.randint(2, 5)
            ev = lambda a, b: a > t and b > t
            txt = f'в каждом из двух бросков выпадет больше {t} {plural(t, "очка", "очков", "очков")}'
        else:
            ev = lambda a, b: a == b
            txt = 'в обоих бросках выпадет одно и то же число очков'
        fav = sum(1 for a, b in outs if ev(a, b))
        exact = F(fav, 36)
        pre = pick(r, 'Игральный кубик с шестью гранями бросают два раза.', 'Правильный игральный кубик подбрасывают дважды.', 'Игрок дважды бросает симметричный шестигранный кубик.')
    else:
        outs = list(range(1, 7))
        kind = r.randrange(3)
        if kind == 0:
            t = r.randint(1, 5)
            ev, txt = (lambda a: a > t), f'выпадет число очков, большее {t}'
        elif kind == 1:
            ev, txt = (lambda a: a % 2 == 0), 'выпадет чётное число очков'
        else:
            t = r.randint(2, 6)
            ev, txt = (lambda a: a < t), f'выпадет меньше {t} {plural(t, "очка", "очков", "очков")}'
        fav = sum(1 for a in outs if ev(a))
        exact = F(fav, 6)
        pre = pick(r, 'Правильный игральный кубик бросают один раз.', 'Игрок один раз подбрасывает симметричный игральный кубик.')
    if fav == 0 or exact == 1:
        return None
    rnd = not finite(exact)
    ans = _round2(exact) if rnd else exact
    q = f'{pre} Найдите вероятность того, что {txt}.' + (' Результат округлите до сотых.' if rnd else '')
    e = f'Благоприятных исходов {fav} из {36 if two else 6}: P = {fav}/{36 if two else 6}' + (f' ≈ {tnum(ans)}.' if rnd else f' = {tnum(ans)}.')

    def chk():
        fav2 = sum(1 for o in outs if (ev(*o) if two else ev(o)))
        v = sp.Rational(fav2, len(outs))
        return same(num(ans), sp.Rational(round(v * 100), 100) if rnd else v)
    return pcard(q, num(ans), e=e), chk


ORDER = [
    ('В конкурсе юных пианистов участвуют', ('исполнитель', 'исполнителя', 'исполнителей'),
     ['из музыкальной школы № 1', 'из музыкальной школы № 2', 'из музыкальной школы № 3'], 'выступает', 'Порядок выступлений определяется жеребьёвкой.', 'исполнитель', 'm'),
    ('В финал олимпиады по робототехнике вышли', ('команда', 'команды', 'команд'), ['из Самары', 'из Казани', 'из Перми'], 'защищает проект',
     'Очерёдность защиты определяется случайным образом.', 'команда', 'f'),
    ('На турнир по прыжкам на батуте заявлены', ('гимнаст', 'гимнаста', 'гимнастов'), ['из клуба «Взлёт»', 'из клуба «Пружина»', 'из клуба «Олимп»'],
     'выполняет прыжок', 'Порядок выступлений определяют жребием.', 'гимнаст', 'm'),
    ('На фестиваль уличных театров приехали', ('труппа', 'труппы', 'трупп'), ['с Урала', 'из Сибири', 'из Поволжья'], 'показывает спектакль',
     'Порядок показов определяется жеребьёвкой.', 'труппа', 'f'),
    ('В конкурсе чтецов участвуют', ('школьник', 'школьника', 'школьников'), ['из 7 «А»', 'из 8 «Б»', 'из 9 «В»'], 'читает стихи',
     'Очерёдность выступлений определяют жребием.', 'школьник', 'm'),
    ('В соревнованиях по скалолазанию участвуют', ('спортсмен', 'спортсмена', 'спортсменов'), ['из Красноярска', 'из Екатеринбурга', 'из Тюмени'],
     'проходит трассу', 'Стартовый порядок определяется жеребьёвкой.', 'спортсмен', 'm'),
]


@proto('og10-order', 'oge', 10, 'Жеребьёвка: кто выступает первым (последним)',
       invariant='Участники из нескольких групп, порядок случайный; вероятность, что на конкретном месте участник из группы X = доля группы.',
       varies='Сюжет, количества по группам, место (первым, последним, пятым…).',
       answer_rule='P = (число участников группы) / (общее число), от номера места не зависит.',
       fipi=r'(жеребь|жреби|случайн).{0,200}(первым|последним|первой|последней)',
       mistakes=['думают, что вероятность зависит от номера места', 'делят на число групп'], maxdec=4, kim=K10)
def gen_og10_order(r):
    head, noun, groups, act, rule, who, g_ = r.choice(ORDER)
    cnt = [r.randint(2, 12) for _ in range(3)]
    N = sum(cnt)
    g = r.randrange(3)
    p = F(cnt[g], N)
    if not nice(p, 3):
        return None
    place = r.choice(['первым', 'последним', 'третьим', 'пятым', 'вторым'])
    if g_ == 'f':
        place = place[:-2] + 'ой'
    lst = ', '.join(f'{cnt[i]} — {groups[i]}' for i in range(3))
    q = f'{head} {_pnoun(N, noun)}: {lst}. {rule} Найдите вероятность того, что {place} {act} {who} {groups[g]}.'
    e = f'На любом месте с равной вероятностью может оказаться любой из {N}; P = {cnt[g]}/{N} = {tnum(p)}.'

    def chk():  # доля участников группы среди всех
        pool = [i for i in range(3) for _ in range(cnt[i])]
        return same(num(p), sp.Rational(sum(1 for x in pool if x == g), len(pool)))
    return pcard(q, num(p), e=e), chk



def svg_euler(counts, labels=('A', 'B'), width=320, height=190, seed=0):
    """Диаграмма Эйлера: прямоугольник Ω, два пересекающихся круга; counts = (только A, A∩B, только B, вне)."""
    import random as _r
    rr = _r.Random(seed)
    cx1, cx2, cy, R_ = 125, 195, 95, 62
    out = f'<rect x="8" y="8" width="{width - 16}" height="{height - 16}" fill="none" stroke="{INK}" stroke-width="1.4"/>'
    out += f'<circle cx="{cx1}" cy="{cy}" r="{R_}" fill="{BLUE}" fill-opacity="0.10" stroke="{BLUE}" stroke-width="2"/>'
    out += f'<circle cx="{cx2}" cy="{cy}" r="{R_}" fill="{RED}" fill-opacity="0.08" stroke="{RED}" stroke-width="2"/>'
    out += f'<text x="{cx1 - R_ + 4}" y="{cy - R_ + 14}" font-size="15" font-style="italic">{labels[0]}</text>'
    out += f'<text x="{cx2 + R_ - 14}" y="{cy - R_ + 14}" font-size="15" font-style="italic">{labels[1]}</text>'
    inA = lambda x, y: (x - cx1) ** 2 + (y - cy) ** 2 < (R_ - 7) ** 2
    inB = lambda x, y: (x - cx2) ** 2 + (y - cy) ** 2 < (R_ - 7) ** 2
    nearA = lambda x, y: abs(math.hypot(x - cx1, y - cy) - R_) < 13
    nearB = lambda x, y: abs(math.hypot(x - cx2, y - cy) - R_) < 13
    zones = [lambda x, y: inA(x, y) and not inB(x, y) and not nearB(x, y), lambda x, y: inA(x, y) and inB(x, y),
             lambda x, y: inB(x, y) and not inA(x, y) and not nearA(x, y),
             lambda x, y: not inA(x, y) and not inB(x, y) and not nearA(x, y) and not nearB(x, y)]
    pts = []
    for z, n in zip(zones, counts):
        placed = 0
        tries = 0
        while placed < n and tries < 20000:
            tries += 1
            x, y = rr.uniform(18, width - 18), rr.uniform(18, height - 18)
            if z(x, y) and all(math.hypot(x - a, y - b) > 13 for a, b in pts):
                pts.append((x, y))
                placed += 1
        if placed < n:
            return None
    out += ''.join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{INK}"/>' for x, y in pts)
    return _svg(width, height, out)


EVENTS = {
    'AB': ('A ∩ B', lambda a, b: a and b, 'одновременно и A, и B'),
    'A|B': ('A ∪ B', lambda a, b: a or b, 'A или B (хотя бы одно из них)'),
    'A': ('A', lambda a, b: a, 'A'),
    'B': ('B', lambda a, b: b, 'B'),
    'notA': ('Ā (не A)', lambda a, b: not a, 'противоположного событию A'),
    'A-B': ('A, но не B', lambda a, b: a and not b, 'A и при этом не наступает B'),
    'none': ('ни A, ни B', lambda a, b: not a and not b, 'не наступает ни A, ни B'),
}


@proto('og10-euler', 'oge', 10, 'Вероятность по диаграмме Эйлера',
       invariant='Диаграмма Эйлера двух событий, точки — равновозможные элементарные исходы; найти вероятность пересечения, объединения, дополнения или разности.',
       varies='Число точек в каждой области, спрашиваемое событие.',
       answer_rule='Считаем точки, благоприятствующие событию, и делим на общее число точек.',
       fipi=r'диаграмма Эйлера',
       mistakes=['для A ∪ B дважды считают точки пересечения', 'забывают точки вне кругов в общем числе'],
       maxdec=4, svg=True, kim=K10)
def gen_og10_euler(r):
    N = r.choice([10, 20, 20, 25, 16, 8, 12])
    cnt = [r.randint(1, N // 2) for _ in range(3)]
    rest = N - sum(cnt)
    if rest < 1 or rest > 10 or max(cnt) > 9:
        return None
    key = r.choice(list(EVENTS))
    name, f, words = EVENTS[key]
    region = [(True, False), (True, True), (False, True), (False, False)]
    counts = cnt + [rest]
    fav = sum(n for (a_, b_), n in zip(region, counts) if f(a_, b_))
    p = F(fav, N)
    if not nice(p, 3) or fav == 0:
        return None
    svg = svg_euler(counts, seed=r.randint(0, 10 ** 6))
    if not svg:
        return None
    q = pick(r, f'В случайном эксперименте все элементарные исходы равновозможны; они показаны точками на диаграмме Эйлера, круги изображают события A и B. Найдите вероятность события {name}.',
             f'На диаграмме Эйлера изображены события A и B некоторого случайного опыта, а точками — все его равновозможные элементарные исходы. Найдите вероятность того, что наступит событие: {words}.')
    e = f'Всего точек {N}; событию благоприятствуют {fav}. P = {fav}/{N} = {tnum(p)}.'
    pts = [reg for reg, n in zip(region, counts) for _ in range(n)]
    return pcard(q, num(p), e=e, svg=svg), lambda: same(num(p), sp.Rational(sum(1 for a_, b_ in pts if f(a_, b_)), len(pts)))


def svg_tree(p1, p2s, mark, width=340, height=210):
    """Дерево опыта: корень S → A (p1), B (1 − p1); от A и B — по два исхода с вероятностями p2s[i].
    mark — множество индексов выделенных листьев (0..3)."""
    root = (30, height / 2)
    mids = [(140, 55), (140, height - 55)]
    leaves = [(290, 22), (290, 88), (290, height - 88), (290, height - 22)]
    probs1 = [p1, 1 - p1]
    out = ''
    for i, m in enumerate(mids):
        hot = bool({2 * i, 2 * i + 1} & set(mark))
        out += f'<line x1="{root[0]}" y1="{root[1]}" x2="{m[0]}" y2="{m[1]}" stroke="{RED if hot else INK}" stroke-width="{2.6 if hot else 1.6}"/>'
        lx, ly = (root[0] + m[0]) / 2, (root[1] + m[1]) / 2
        out += f'<text x="{lx - 10:.0f}" y="{ly + (-6 if i == 0 else 16):.0f}" font-size="13">{tnum(probs1[i])}</text>'
        for j in range(2):
            lf = leaves[2 * i + j]
            pp = p2s[i] if j == 0 else 1 - p2s[i]
            col = RED if 2 * i + j in mark else INK
            out += f'<line x1="{m[0]}" y1="{m[1]}" x2="{lf[0]}" y2="{lf[1]}" stroke="{col}" stroke-width="{2.6 if col == RED else 1.6}"/>'
            out += f'<text x="{(m[0] + lf[0]) / 2 - 12:.0f}" y="{(m[1] + lf[1]) / 2 + (-6 if j == 0 else 15):.0f}" font-size="13">{tnum(pp)}</text>'
            out += f'<circle cx="{lf[0]}" cy="{lf[1]}" r="{6 if col == RED else 4}" fill="{col}"/>'
            out += f'<text x="{lf[0] + 10}" y="{lf[1] + 4}" font-size="13" font-style="italic">{["C", "D", "E", "F"][2 * i + j]}</text>'
        out += f'<circle cx="{m[0]}" cy="{m[1]}" r="4" fill="{INK}"/><text x="{m[0] - 4}" y="{m[1] - 9}" font-size="13" font-style="italic">{"AB"[i]}</text>'
    out += f'<circle cx="{root[0]}" cy="{root[1]}" r="4.5" fill="{INK}"/><text x="{root[0] - 4}" y="{root[1] - 10}" font-size="13" font-style="italic">S</text>'
    return _svg(width, height, out)


@proto('og10-tree', 'oge', 10, 'Вероятность по дереву случайного опыта',
       invariant='Дерево опыта с вероятностями на рёбрах; событию благоприятствуют выделенные листья. Вероятность — сумма произведений вероятностей вдоль путей.',
       varies='Вероятности на рёбрах (десятые), набор выделенных исходов (один или два пути).',
       answer_rule='Перемножаем вероятности вдоль каждого пути к выделенному исходу и складываем.',
       fipi=r'дерево случайного опыта',
       mistakes=['складывают вероятности вдоль пути вместо умножения', 'не учитывают второй путь'],
       maxdec=4, svg=True, kim=K10)
def gen_og10_tree(r):
    p1 = F(r.randint(1, 9), 10)
    p2s = [F(r.randint(1, 9), 10), F(r.randint(1, 9), 10)]
    mark = set(r.sample(range(4), r.choice([1, 2, 2])))
    probs = [p1 * p2s[0], p1 * (1 - p2s[0]), (1 - p1) * p2s[1], (1 - p1) * (1 - p2s[1])]
    p = sum(probs[i] for i in mark)
    names = ['C', 'D', 'E', 'F']
    ev = ' или '.join(names[i] for i in sorted(mark))
    q = pick(r, f'На рисунке показано дерево случайного опыта с вероятностями на рёбрах. Выделенные исходы благоприятствуют событию T. Найдите вероятность события T.',
             f'Случайный опыт изображён деревом; около рёбер указаны вероятности переходов. Найдите вероятность того, что опыт закончится исходом {ev}.')
    e = ' + '.join(f'{tnum([p1, p1, 1 - p1, 1 - p1][i])}·{tnum([p2s[0], 1 - p2s[0], p2s[1], 1 - p2s[1]][i])}' for i in sorted(mark)) + f' = {tnum(p)}.'
    svg = svg_tree(p1, p2s, mark)

    def chk():  # моделирование по шагам: перебор путей с точными вероятностями
        tot = sp.Integer(0)
        for i, (a1, a2) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
            w1 = R(p1) if a1 == 0 else 1 - R(p1)
            w2 = R(p2s[a1]) if a2 == 0 else 1 - R(p2s[a1])
            if i in mark:
                tot += w1 * w2
        return same(num(p), tot)
    return pcard(q, num(p), e=e, svg=svg), chk


@proto('og10-coin-count', 'oge', 10, 'Монету бросили n раз, известно число орлов: вероятность решки на данном броске',
       invariant='Известно, что при n бросках орёл выпал k раз; все расположения орлов равновозможны; P(решка на m-м броске) = (n − k)/n.',
       varies='n, k, номер броска, спрашиваемая сторона.',
       answer_rule='Выпавшие решки равномерно «распределены» по номерам бросков: P = (n − k)/n.',
       fipi=r'Монету бросили \d+ раз',
       mistakes=['отвечают 0,5, игнорируя условие', 'делят k на n − k'], maxdec=4, kim=K10)
def gen_og10_coin_count(r):
    n = r.choice([4, 5, 8, 10, 16, 20, 25, 40, 50])
    k = r.randint(1, n - 1)
    m = r.randint(1, n)
    side = r.choice(['орёл', 'решка'])
    fav = k if side == 'орёл' else n - k
    p = F(fav, n)
    if not nice(p, 3):
        return None
    ordw = ['первый', 'второй', 'третий', 'четвёртый', 'пятый', 'шестой', 'седьмой', 'восьмой', 'девятый', 'десятый']
    mw = ordw[m - 1] if m <= 10 else f'{m}-й'
    si = 'орлом' if side == 'орёл' else 'решкой'
    q = pick(r, f'Монету подбросили {n} {plural(n, "раз", "раза", "раз")}; орёл при этом выпал {k} {plural(k, "раз", "раза", "раз")}. Какова вероятность того, что {mw} бросок закончился {si}?',
             f'Известно, что в серии из {n} подбрасываний монеты орёл выпал ровно {k} {plural(k, "раз", "раза", "раз")}. Найдите вероятность того, что {mw} по порядку бросок дал {"орла" if side == "орёл" else "решку"}.')
    e = f'Все расположения {k} орлов среди {n} бросков равновозможны, поэтому P = {fav}/{n} = {tnum(p)}.'
    comb = math.comb
    return pcard(q, num(p), e=e), lambda: same(num(p), sp.Rational(comb(n - 1, k - 1) if side == 'орёл' else comb(n - 1, k), comb(n, k)))


@proto('og10-second-draw', 'oge', 10, 'Второй предмет того же цвета (без возвращения)',
       invariant='Из a + b предметов достают два; первый оказался цвета X; вероятность, что второй тоже X = (x − 1)/(a + b − 1).',
       varies='Сюжет, числа a и b, цвет первого.',
       answer_rule='После первого извлечения осталось a + b − 1 предмет, из них x − 1 нужного цвета.',
       fipi=r'первый карандаш оказался|Известно, что первый',
       mistakes=['не уменьшают общее число', 'дают x/(a + b)'], maxdec=4, kim=K10)
def gen_og10_second_draw(r):
    things = [('В пенале лежат', 'ручек', [('синих', 'синей'), ('красных', 'красной')], ('Первая', 'оказалась', 'вторая')),
              ('В мешочке лежат', 'шашек', [('белых', 'белой'), ('чёрных', 'чёрной')], ('Первая', 'оказалась', 'вторая')),
              ('В коробке лежат', 'карандашей', [('простых', 'простым'), ('цветных', 'цветным')], ('Первый', 'оказался', 'второй')),
              ('В вазочке лежат', 'леденцов', [('мятных', 'мятным'), ('лимонных', 'лимонным')], ('Первый', 'оказался', 'второй')),
              ('В ящике стола лежат', 'батареек', [('новых', 'новой'), ('севших', 'севшей')], ('Первая', 'оказалась', 'вторая'))]
    head, noun, cols, (w1, verb, w2) = r.choice(things)
    a_, b_ = r.randint(5, 30), r.randint(5, 30)
    if plural(a_, 1, 2, 3) != 3 or plural(b_, 1, 2, 3) != 3:
        return None
    j = r.randrange(2)
    x = (a_, b_)[j]
    p = F(x - 1, a_ + b_ - 1)
    if not nice(p, 3):
        return None
    q = (f'{head} {a_} {cols[0][0]} и {b_} {cols[1][0]} {noun}. Не глядя, из него вынимают один предмет за другим — всего два. '
         f'{w1} {verb} {cols[j][1]}. Найдите вероятность того, что {w2} тоже {verb.replace("оказалась", "окажется").replace("оказался", "окажется")} {cols[j][1]}.')
    e = f'Осталось {a_ + b_ - 1}, из них нужных {x - 1}: P = {x - 1}/{a_ + b_ - 1} = {tnum(p)}.'
    pool = [0] * a_ + [1] * b_

    def chk():  # перебор упорядоченных пар
        pairs = [(pool[i], pool[k]) for i in range(len(pool)) for k in range(len(pool)) if i != k and pool[i] == j]
        return same(num(p), sp.Rational(sum(1 for u, w in pairs if w == j), len(pairs)))
    return pcard(q, num(p), e=e), chk


@proto('og10-formula', 'oge', 10, 'Вероятность по числу исходов (формулировка через элементарные события)',
       invariant='Известно число n равновозможных элементарных исходов и число k благоприятствующих событию A; P(A) = k/n (или P(Ā) = 1 − k/n).',
       varies='n, k, спрашиваемое событие (A или противоположное).',
       answer_rule='P(A) = k/n; P(Ā) = (n − k)/n.',
       fipi=r'равновозможных элементарных событий, из которых',
       mistakes=['делят n на k', 'для противоположного события не вычитают из 1'], maxdec=4, kim=K10)
def gen_og10_formula(r):
    n = r.choice([8, 10, 16, 20, 25, 40, 50, 80, 100, 125, 200])
    k = r.randint(1, n - 1)
    comp = r.random() < 0.35
    p = F(n - k if comp else k, n)
    if not nice(p, 3):
        return None
    ev = 'события, противоположного событию A' if comp else 'события A'
    q = pick(r, f'Некоторый опыт имеет {n} равновозможных элементарных исходов, и {k} из них благоприятствуют событию A. Найдите вероятность {ev}.',
             f'В случайном эксперименте всего {n} равновозможных исходов; событию A благоприятствует {k} из них. Чему равна вероятность {ev}?')
    e = f'P = {(n - k) if comp else k}/{n} = {tnum(p)}.'
    return pcard(q, num(p), e=e), lambda: same(num(p), (1 - sp.Rational(k, n)) if comp else sp.Rational(k, n))


# ================================================================ №11 — графики функций: соответствие

K11 = K(minutes=3, kes=['5.1', '6.2'], kt=[6], answer='соответствие',
        style='Установление соответствия А–В ↔ 1–3, ответ — последовательность цифр под буквами (как в КИМ ОГЭ №11)')
TAIL11 = ('Под каждой буквой запишите номер соответствующего графика.', 'Для каждой буквы выберите номер.', '')


def _match(r, left_txt, right_txt, perm, e):
    """left_txt[i] соответствует right_txt[perm[i]]; right — номера 1..n."""
    left = [{'id': LET[i], 't': t} for i, t in enumerate(left_txt)]
    right = [{'id': str(j + 1), 't': t} for j, t in enumerate(right_txt)]
    a = {LET[i]: str(perm[i] + 1) for i in range(len(left_txt))}
    return left, right, a


def _lin_f(k, b):
    return lambda x: float(k) * x + float(b)


def _lin_txt(k, b):
    k = F(k)
    kt = '' if k == 1 else ('−' if k == -1 else (ufr(k.numerator, k.denominator) if k.denominator > 1 else tnum(k)))
    s_ = f'y = {kt}x'
    if b:
        s_ += signed(b)
    return s_


@proto('og11-lin-signs', 'oge', 11, 'Прямые y = kx + b: знаки k и b',
       invariant='Три прямые на отдельных рисунках; сопоставить каждой паре знаков k и b её график.',
       varies='Наклон и точка пересечения с осью y каждой прямой, какие три комбинации знаков выбраны, порядок.',
       answer_rule='k > 0 — прямая возрастает, k < 0 — убывает; b — ордината точки пересечения с осью y.',
       fipi=r'графики функций вида y = k x \+ b',
       mistakes=['путают знак k с направлением «вверх/вниз» при чтении справа налево', 'путают b с нулём функции'],
       svg=True, card_kind='match', kim=K11)
def gen_og11_lin_signs(r):
    combos = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    three = r.sample(combos, 3)
    fns, lines = [], []
    for sk, sb in three:
        k = sk * r.choice([F(1, 2), F(1), F(2), F(3), F(1, 3), F(3, 2)])
        b = sb * r.randint(1, 3)
        fns.append((k, b))
    perm = list(range(3))
    r.shuffle(perm)  # график номер perm[i] — это комбинация i
    graphs = [None] * 3
    for i, j in enumerate(perm):
        graphs[j] = fns[i]
    svg = svg_panels([_lin_f(k, b) for k, b in graphs], ['1', '2', '3'])
    sg = lambda v: '> 0' if v > 0 else '< 0'
    left_txt = [f'k {sg(sk)}, b {sg(sb)}' for sk, sb in three]
    left, right, a = _match(r, left_txt, ['график 1', 'график 2', 'график 3'], perm, '')
    q = pick(r, 'На рисунках построены графики трёх функций вида y = kx + b. Сопоставьте знаки коэффициентов k и b с номерами графиков.',
             'Каждый из трёх рисунков — график линейной функции y = kx + b. Для каждой пары знаков коэффициентов укажите номер подходящего графика.') + ' ' + pick(r, *TAIL11)
    e = 'Возрастающая прямая — k > 0, убывающая — k < 0; b — точка пересечения с осью y. ' + '; '.join(f'{LET[i]} → {perm[i] + 1}' for i in range(3)) + '.'

    def chk():
        for i, (sk, sb) in enumerate(three):
            k, b = graphs[int(a[LET[i]]) - 1]
            X_ = sp.Symbol('X')
            f = R(k) * X_ + b
            if sp.sign(sp.diff(f, X_)) != sk or sp.sign(f.subs(X_, 0)) != sb:
                return False
        return True
    return pcard(q.strip(), a, e=e, k='match', o={'left': left, 'right': right}, svg=svg), chk


@proto('og11-parab-signs', 'oge', 11, 'Параболы y = ax² + bx + c: знаки a и c',
       invariant='Три параболы; сопоставить парам знаков a и c графики.',
       varies='Вершины и раскрытие парабол, выбранные комбинации знаков, порядок.',
       answer_rule='a > 0 — ветви вверх; c = y(0) — точка пересечения с осью y.',
       fipi=r'графики функций вида y = a x 2 \+ b x \+ c',
       mistakes=['путают c с вершиной параболы', 'определяют знак a по положению вершины'],
       svg=True, card_kind='match', kim=K11)
def gen_og11_parab_signs(r):
    combos = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    three = r.sample(combos, 3)
    ps = []
    for sa, sc in three:
        for _ in range(50):
            a_ = sa * r.choice([F(1, 2), F(1), F(1), F(2)])
            h = r.randint(-2, 2)
            v = r.randint(-3, 3)
            c = a_ * h * h + v
            if c != 0 and (c > 0) == (sc > 0) and abs(c) <= 3.6 and c.denominator == 1:
                ps.append((a_, h, v))
                break
        else:
            return None
    perm = list(range(3))
    r.shuffle(perm)
    graphs = [None] * 3
    for i, j in enumerate(perm):
        graphs[j] = ps[i]
    svg = svg_panels([(lambda x, a_=a_, h=h, v=v: float(a_) * (x - h) ** 2 + float(v)) for a_, h, v in graphs], ['1', '2', '3'])
    sg = lambda t: '> 0' if t > 0 else '< 0'
    left_txt = [f'a {sg(sa)}, c {sg(sc)}' for sa, sc in three]
    left, right, a = _match(r, left_txt, ['график 1', 'график 2', 'график 3'], perm, '')
    q = pick(r, 'На рисунках изображены графики трёх функций вида y = ax² + bx + c. Сопоставьте знаки коэффициентов a и c с номерами графиков.',
             'Три параболы — графики функций y = ax² + bx + c. Для каждой пары знаков коэффициентов a и c найдите подходящий график.') + ' ' + pick(r, *TAIL11)
    e = 'Ветви вверх — a > 0, вниз — a < 0; c — ордината точки пересечения с осью y. ' + '; '.join(f'{LET[i]} → {perm[i] + 1}' for i in range(3)) + '.'

    def chk():
        X_ = sp.Symbol('X')
        for i, (sa, sc) in enumerate(three):
            a_, h, v = graphs[int(a[LET[i]]) - 1]
            f = R(a_) * (X_ - h) ** 2 + v
            if sp.sign(sp.Poly(f, X_).LC()) != sa or sp.sign(f.subs(X_, 0)) != sc:
                return False
        return True
    return pcard(q.strip(), a, e=e, k='match', o={'left': left, 'right': right}, svg=svg), chk


@proto('og11-lin-formulas', 'oge', 11, 'Три прямые и их формулы',
       invariant='Графики трёх линейных функций с похожими формулами (одинаковый |k|, разные знаки k и b); сопоставить графики формулам.',
       varies='|k| (целое или дробь), |b|, какие три формулы из четырёх, порядок.',
       answer_rule='По наклону определяем знак k, по пересечению с осью y — b.',
       fipi=r'между графиками функций и формулами, которые их задают.{0,60}y = [−-]?\s*\d*\s*x\s*[+−-]\s*\d',
       mistakes=['путают знак углового коэффициента', 'смотрят на пересечение с осью x вместо y'],
       svg=True, card_kind='match', kim=K11)
def gen_og11_lin_formulas(r):
    k0 = r.choice([F(1), F(2), F(3), F(1, 2), F(1, 3), F(3, 2)])
    b0 = r.randint(1, 3)
    combos = [(k0, b0), (k0, -b0), (-k0, b0), (-k0, -b0)]
    if r.random() < 0.3:
        combos = [(k0, b0), (-k0, b0), (k0 * 2 if k0 < 2 else k0 / 2, b0), (k0, -b0)]
    three = r.sample(combos, 3)
    perm = list(range(3))
    r.shuffle(perm)  # график (буква) i ↔ формула perm[i]
    formulas = [None] * 3
    for i, j in enumerate(perm):
        formulas[j] = three[i]
    svg = svg_panels([_lin_f(k, b) for k, b in three], ['А', 'Б', 'В'])
    left_txt = ['график А', 'график Б', 'график В']
    right_txt = [_lin_txt(k, b) for k, b in formulas]
    left, right, a = _match(r, left_txt, right_txt, perm, '')
    q = pick(r, 'Сопоставьте каждому из графиков А–В формулу, которой он задаётся.',
             'На рисунке изображены графики А, Б, В трёх линейных функций. Для каждого графика выберите номер его формулы.')
    e = '; '.join(f'{LET[i]}: {_lin_txt(*three[i])}' for i in range(3)) + '.'

    def chk():
        X_ = sp.Symbol('X')
        for i in range(3):
            k, b = formulas[int(a[LET[i]]) - 1]
            if (R(k), b) != (R(three[i][0]), three[i][1]):
                return False
            # точки графика с целыми координатами лежат на прямой из формулы
            if sp.simplify(R(k) * X_ + b - (R(three[i][0]) * X_ + three[i][1])) != 0:
                return False
        return True
    return pcard(q, a, e=e, k='match', o={'left': left, 'right': right_txt and right}, svg=svg), chk


def _kinds(r):
    """Случайные формулы трёх видов: (текст, функция, вид)."""
    k = r.choice([F(1, 2), F(1, 3), F(2), F(-1, 2), F(-2), F(3), F(-3), F(1, 4)])
    b = r.randint(-3, 3)
    lin_ = (_lin_txt(k, b), _lin_f(k, b), 'прямая')
    a_ = r.choice([F(1), F(-1), F(2), F(-2), F(1, 2), F(-1, 2)])
    h, v = r.randint(-2, 2), r.randint(-2, 2)
    co = [a_, -2 * a_ * h, a_ * h * h + v]
    par_ = (f'y = {poly(co)}', lambda x, a_=a_, h=h, v=v: float(a_) * (x - h) ** 2 + float(v), 'парабола')
    kk = r.choice([1, -1, 2, -2, 3, -3, 4, -4])
    hyp = (f'y = {tnum(kk)}/x' if kk > 0 else f'y = −{-kk}/x', lambda x, kk=kk: kk / x, 'гипербола')
    return [lin_, par_, hyp]


@proto('og11-mixed', 'oge', 11, 'Прямая, парабола, гипербола: формулы и графики',
       invariant='Три функции разных видов (линейная, квадратичная, обратная пропорциональность); сопоставить формулы и графики.',
       varies='Коэффициенты, направление соответствия (формулы → графики или графики → формулы), порядок.',
       answer_rule='Вид графика определяется видом формулы: kx + b — прямая, ax² + … — парабола, k/x — гипербола.',
       fipi=r'(между функциями и их графиками|между графиками функций и формулами).{0,80}(x 2|1 x)',
       mistakes=['путают гиперболу и параболу при «перевёрнутых» ветвях'],
       svg=True, card_kind='match', kim=K11)
def gen_og11_mixed(r):
    items = _kinds(r)
    r.shuffle(items)
    perm = list(range(3))
    r.shuffle(perm)
    if r.random() < 0.5:  # формулы А–В → графики 1–3
        graphs = [None] * 3
        for i, j in enumerate(perm):
            graphs[j] = items[i]
        svg = svg_panels([g[1] for g in graphs], ['1', '2', '3'])
        left_txt = [it[0] for it in items]
        right_txt = ['график 1', 'график 2', 'график 3']
        q = pick(r, 'Для каждой из функций А–В укажите номер её графика.', 'Сопоставьте функции, заданные формулами, с их графиками на рисунках 1–3.')
        want = [graphs[perm[i]] for i in range(3)]
        got = lambda a: [graphs[int(a[LET[i]]) - 1] for i in range(3)]
    else:  # графики А–В → формулы 1–3
        formulas = [None] * 3
        for i, j in enumerate(perm):
            formulas[j] = items[i]
        svg = svg_panels([it[1] for it in items], ['А', 'Б', 'В'])
        left_txt = ['график А', 'график Б', 'график В']
        right_txt = [f[0] for f in formulas]
        q = pick(r, 'Каждому графику А–В поставьте в соответствие формулу, которой задана функция.', 'Определите, какой формулой задаётся каждый из графиков А, Б, В.')
        want = items
        got = lambda a: [formulas[int(a[LET[i]]) - 1] for i in range(3)]
    left, right, a = _match(r, left_txt, right_txt, perm, '')
    e = '; '.join(f'{it[0]} — {it[2]}' for it in items) + '.'

    def chk():
        g = got(a)
        return all(g[i][0] == want[i][0] for i in range(3)) and len({x[2] for x in g}) == 3
    return pcard(q, a, e=e, k='match', o={'left': left, 'right': right}, svg=svg), chk


# ================================================================ №12 — расчёты по формулам

K12 = K(minutes=3, kes=['2.1', '2.2'], kt=[4], style='Формула из физики/жизни с пояснением величин; «… найдите …»; «Ответ дайте в …»')
FIND = ('По этой формуле найдите', 'С помощью этой формулы найдите', 'Воспользуйтесь этой формулой и найдите')


def _f12(r, head, ask, ans, e, chk, unit=''):
    q = f'{head} {pick(r, *FIND)} {ask}' + (f' Ответ выразите {unit}.' if unit and r.random() < 0.5 else (f' Ответ дайте {unit}.' if unit else ''))
    return pcard(q, num(ans), e=e), chk


@proto('og12-linear-calc', 'oge', 12, 'Подстановка в линейную формулу',
       invariant='Формула вида y = a + b·x или y = k(x + c) из жизни; подставить значение и вычислить.',
       varies='Сюжет (прокат, каршеринг, фотопечать, размер обуви, «термометр-сверчок»), коэффициенты, значение переменной.',
       answer_rule='Подставляем число в формулу, соблюдая порядок действий.',
       fipi=r'(стоимость|переводить|перевести).{0,120}по формуле.{0,200}(рассчитайте|Скольким градусам)',
       mistakes=['прибавляют раньше, чем умножают', 'забывают вычесть в скобках'], lim=100000, kim=K12)
def gen_og12_linear_calc(r):
    kind = r.randrange(5)
    if kind == 0:
        a, b, t = r.choice([300, 350, 400, 450, 500]), r.choice([90, 110, 120, 130, 150, 180]), r.randint(2, 12)
        ans = a + b * t
        head = (f'Стоимость проката электросамоката (в рублях) в одном из городских сервисов считается по формуле C = {a} + {b}t, '
                f'где t — время поездки в часах.')
        ask, unit = f'стоимость поездки длительностью {t} {plural(t, "час", "часа", "часов")}.', 'в рублях'
        chk = lambda: same(num(ans), sp.Rational(a) + b * t)
        e = f'C = {a} + {b}·{t} = {ans}.'
    elif kind == 1:
        a, b, n = r.choice([100, 120, 150, 200]), r.choice([12, 14, 15, 18, 22, 25]), r.randint(10, 120)
        ans = a + b * n
        head = f'Фотоателье рассчитывает стоимость печати снимков (в рублях) по формуле C = {a} + {b}n, где n — число отпечатков в заказе.'
        ask, unit = f'стоимость заказа из {n} {plural(n, "снимка", "снимков", "снимков")}.', 'в рублях'
        chk = lambda: same(num(ans), sp.Rational(a) + b * n)
        e = f'C = {a} + {b}·{n} = {ans}.'
    elif kind == 2:
        N = r.randint(33, 46)
        L = F(2 * N, 3) - F(3, 2)
        if not nice(L, 1):
            return None
        ans = N
        head = 'Европейский размер обуви N приближённо связан с длиной стопы L (в сантиметрах) формулой N = 1,5(L + 1,5).'
        ask, unit = f'размер обуви, если длина стопы равна {tnum(L)} см.', ''
        chk = lambda: same(num(ans), sp.Rational(3, 2) * (R(L) + sp.Rational(3, 2)))
        e = f'N = 1,5·({tnum(L)} + 1,5) = {ans}.'
    elif kind == 3:
        t = r.randint(12, 30)
        N = 7 * (t - 10) + 40
        ans = t
        head = ('Существует формула, по которой температуру воздуха (в °C) можно оценить по пению сверчка: t = 10 + (N − 40)/7, '
                'где N — число стрекотаний за минуту.')
        ask, unit = f'температуру воздуха, если сверчок стрекочет {N} {plural(N, "раз", "раза", "раз")} в минуту.', 'в градусах Цельсия'
        chk = lambda: same(num(ans), 10 + sp.Rational(N - 40, 7))
        e = f't = 10 + ({N} − 40)/7 = {ans}.'
    else:
        a, b, t = r.choice([500, 600, 700, 800]), r.choice([150, 200, 250, 300]), r.randint(2, 9)
        ans = a + b * (t - 1)
        head = (f'Стоимость аренды прогулочной лодки (в рублях) вычисляется по формуле C = {a} + {b}(t − 1), где t — длительность аренды в часах (t ≥ 1).')
        ask, unit = f'стоимость аренды на {t} {plural(t, "час", "часа", "часов")}.', 'в рублях'
        chk = lambda: same(num(ans), sp.Rational(a) + b * (t - 1))
        e = f'C = {a} + {b}·({t} − 1) = {ans}.'
    return _f12(r, head, ask, ans, e, chk, unit)


@proto('og12-product-calc', 'oge', 12, 'Вычисление по формуле-произведению',
       invariant='Физическая формула-произведение (p = ρgh, Q = cmΔt, F = mg, A = Fs); подставить данные и вычислить.',
       varies='Формула и сюжет, значения величин (десятичные).',
       answer_rule='Перемножаем значения, аккуратно с десятичными дробями.',
       fipi=r'Сила Архимеда|вычисляется по формуле F = ρ g V',
       mistakes=['ошибка в порядке десятичных знаков'], lim=10 ** 7, kim=K12)
def gen_og12_product_calc(r):
    kind = r.randrange(4)
    if kind == 0:
        h = F(r.randint(1, 60), r.choice([1, 2, 10]))
        ans = 1000 * F(98, 10) * h
        head = ('Давление столба жидкости на дно сосуда (в паскалях) вычисляется по формуле p = ρgh, где ρ = 1000 кг/м³ — плотность воды, '
                'g = 9,8 м/с² — ускорение свободного падения, h — высота столба воды в метрах.')
        ask, unit = f'давление воды на дно бассейна, если глубина воды {tnum(h)} м.', 'в паскалях'
        chk = lambda: same(num(ans), 1000 * sp.Rational(49, 5) * R(h))
        e = f'p = 1000·9,8·{tnum(h)} = {tnum(ans)}.'
    elif kind == 1:
        m = F(r.randint(1, 30), r.choice([1, 2, 10]))
        dt = r.randint(5, 80)
        ans = 4200 * m * dt
        head = ('Количество теплоты (в джоулях), нужное для нагревания воды, вычисляется по формуле Q = cmΔt, где c = 4200 Дж/(кг·°C) — удельная '
                'теплоёмкость воды, m — масса воды в килограммах, Δt — изменение температуры в градусах Цельсия.')
        ask, unit = f'количество теплоты, необходимое, чтобы нагреть {tnum(m)} кг воды на {dt} °C.', 'в джоулях'
        chk = lambda: same(num(ans), 4200 * R(m) * dt)
        e = f'Q = 4200·{tnum(m)}·{dt} = {tnum(ans)}.'
    elif kind == 2:
        m = F(r.randint(2, 400), r.choice([1, 10]))
        ans = m * F(98, 10)
        head = 'Сила тяжести (в ньютонах), действующая на тело, вычисляется по формуле F = mg, где m — масса тела в килограммах, g = 9,8 м/с².'
        ask, unit = f'силу тяжести, действующую на груз массой {tnum(m)} кг.', 'в ньютонах'
        chk = lambda: same(num(ans), R(m) * sp.Rational(49, 5))
        e = f'F = {tnum(m)}·9,8 = {tnum(ans)}.'
    else:
        Fv = r.randint(20, 600)
        sd = F(r.randint(5, 250), r.choice([1, 10]))
        ans = Fv * sd
        head = 'Механическая работа (в джоулях) при перемещении тела вычисляется по формуле A = Fs, где F — сила в ньютонах, s — путь в метрах.'
        ask, unit = f'работу, которую совершает сила {Fv} Н на пути {tnum(sd)} м.', 'в джоулях'
        chk = lambda: same(num(ans), Fv * R(sd))
        e = f'A = {Fv}·{tnum(sd)} = {tnum(ans)}.'
    if not nice(ans, 2):
        return None
    return _f12(r, head, ask, ans, e, chk, unit)


@proto('og12-solve-factor', 'oge', 12, 'Найти множитель из формулы (переменная в первой степени)',
       invariant='Формула-произведение (с квадратом другой величины): выразить неизвестный множитель и вычислить.',
       varies='Формула (Q = I²Rt, p = ρgh, Q = cmΔt, F = kx, P = U²/R, E = kx²/2), искомая величина, значения.',
       answer_rule='Делим известное значение на произведение остальных множителей.',
       fipi=r'(Мощность постоянного тока|Центростремительное ускорение|потенциальная энергия).{0,300}(найдите сопротивление|найдите радиус|Найдите массу)',
       mistakes=['забывают возвести в квадрат другую величину', 'умножают вместо деления'], lim=10 ** 6, kim=K12)
def gen_og12_solve_factor(r):
    kind = r.randrange(6)
    if kind == 0:
        I, Rr, t = r.randint(2, 9), r.randint(2, 40), r.choice([5, 10, 20, 30, 60, 120])
        Q = I * I * Rr * t
        head = ('Количество теплоты (в джоулях), выделяемое проводником с током, вычисляется по формуле Q = I²Rt, где I — сила тока (в амперах), '
                'R — сопротивление (в омах), t — время (в секундах).')
        ask, ans, unit = f'сопротивление проводника, если за {t} с выделилось {Q} Дж теплоты при силе тока {I} А.', Rr, 'в омах'
        chk = lambda: same(num(ans), sp.solve(sp.Eq(I ** 2 * sp.Symbol('R') * t, Q), sp.Symbol('R'))[0])
        e = f'R = Q/(I²t) = {Q}/({I * I}·{t}) = {ans}.'
    elif kind == 1:
        h = F(r.randint(1, 40), r.choice([1, 2, 10]))
        p_ = 9800 * h
        if not nice(p_, 0):
            return None
        head = ('Давление жидкости на глубине (в паскалях) вычисляется по формуле p = ρgh, где ρ = 1000 кг/м³ — плотность воды, g = 9,8 м/с², h — глубина в метрах.')
        ask, ans, unit = f'глубину, на которой давление воды равно {tnum(p_)} Па.', h, 'в метрах'
        chk = lambda: same(num(ans), sp.solve(sp.Eq(1000 * sp.Rational(49, 5) * sp.Symbol('h'), R(p_)), sp.Symbol('h'))[0])
        e = f'h = p/(ρg) = {tnum(p_)}/9800 = {tnum(ans)}.'
    elif kind == 2:
        m = F(r.randint(1, 40), r.choice([1, 2, 10]))
        dt = r.randint(5, 80)
        Q = 4200 * m * dt
        if Q.denominator != 1:
            return None
        head = ('Количество теплоты (в джоулях), полученное водой при нагревании, находят по формуле Q = cmΔt, где c = 4200 Дж/(кг·°C), m — масса воды (в кг), '
                'Δt — изменение температуры (в °C).')
        if r.random() < 0.5:
            ask, ans, unit = f'массу воды, если при нагревании на {dt} °C она получила {tnum(Q)} Дж.', m, 'в килограммах'
            e = f'm = Q/(cΔt) = {tnum(Q)}/(4200·{dt}) = {tnum(m)}.'
        else:
            ask, ans, unit = f'на сколько градусов нагрелась вода массой {tnum(m)} кг, получив {tnum(Q)} Дж.', F(dt), 'в градусах Цельсия'
            e = f'Δt = Q/(cm) = {tnum(Q)}/(4200·{tnum(m)}) = {dt}.'
        chk = lambda: same(num(ans), R(Q) / (4200 * (R(m) if ans == dt else dt)))
    elif kind == 3:
        Rr = r.choice([2, 4, 5, 8, 10, 12, 16, 20, 25, 40, 50])
        U = r.randint(2, 30) * math.isqrt(Rr) if math.isqrt(Rr) ** 2 == Rr else r.choice([4, 10, 20, 12]) * r.randint(1, 5)
        Pw = F(U * U, Rr)
        if not nice(Pw, 2):
            return None
        head = 'Мощность (в ваттах) электроприбора можно найти по формуле P = U²/R, где U — напряжение (в вольтах), R — сопротивление (в омах).'
        ask, ans, unit = f'сопротивление прибора, если при напряжении {U} В его мощность равна {tnum(Pw)} Вт.', Rr, 'в омах'
        chk = lambda: same(num(ans), sp.solve(sp.Eq(U ** 2 / sp.Symbol('R'), R(Pw)), sp.Symbol('R'))[0])
        e = f'R = U²/P = {U * U}/{tnum(Pw)} = {ans}.'
    elif kind == 4:
        k = r.choice([20, 40, 50, 80, 100, 120, 150, 200, 250, 400, 500])
        x = F(r.randint(1, 30), 100)
        E = k * x * x / 2
        if not nice(E, 4):
            return None
        head = 'Потенциальная энергия (в джоулях) растянутой пружины вычисляется по формуле E = kx²/2, где k — жёсткость пружины (в Н/м), x — удлинение (в метрах).'
        ask, ans, unit = f'жёсткость пружины, если при удлинении {tnum(x)} м её энергия равна {tnum(E)} Дж.', k, 'в ньютонах на метр'
        chk = lambda: same(num(ans), sp.solve(sp.Eq(sp.Symbol('k') * R(x) ** 2 / 2, R(E)), sp.Symbol('k'))[0])
        e = f'k = 2E/x² = 2·{tnum(E)}/{tnum(x * x)} = {k}.'
    else:
        m = F(r.randint(2, 60), r.choice([1, 10]))
        v = r.randint(2, 20)
        rr = r.choice([1, 2, 4, 5, 8, 10, 20, 25, 40, 50])
        Fc = m * v * v / rr
        if not nice(Fc, 2):
            return None
        head = ('Сила (в ньютонах), удерживающая тело на окружности, вычисляется по формуле F = mv²/r, где m — масса (в кг), v — скорость (в м/с), r — радиус окружности (в метрах).')
        ask, ans, unit = f'массу тела, если при скорости {v} м/с на окружности радиусом {rr} м на него действует сила {tnum(Fc)} Н.', m, 'в килограммах'
        chk = lambda: same(num(ans), sp.solve(sp.Eq(sp.Symbol('m') * v ** 2 / rr, R(Fc)), sp.Symbol('m'))[0])
        e = f'm = Fr/v² = {tnum(Fc)}·{rr}/{v * v} = {tnum(m)}.'
    if not nice(ans, 2):
        return None
    return _f12(r, head, ask, ans, e, chk, unit)


@proto('og12-solve-square', 'oge', 12, 'Найти величину, стоящую в квадрате',
       invariant='В формуле искомая величина стоит в квадрате (Q = I²Rt, E = kx²/2, P = U²/R, F = mv²/r); выразить квадрат и извлечь корень.',
       varies='Формула и сюжет, значения (ответ — целое или десятичное).',
       answer_rule='Выражаем квадрат искомой величины, извлекаем арифметический корень.',
       fipi=r'(Кинетическая энергия|кинетической энергией).{0,300}скорость',
       mistakes=['забывают извлечь корень', 'делят на 2 вместо умножения'], kim=K12)
def gen_og12_solve_square(r):
    kind = r.randrange(4)
    if kind == 0:
        I, Rr, t = F(r.randint(1, 20), r.choice([1, 2])), r.randint(2, 50), r.choice([2, 5, 10, 20, 60])
        Q = I * I * Rr * t
        if not nice(Q, 1):
            return None
        head = ('Количество теплоты (в джоулях), выделяемое в проводнике с током, находят по формуле Q = I²Rt, где I — сила тока (в амперах), R — сопротивление (в омах), t — время (в секундах).')
        ask, ans, unit = f'силу тока, если за {t} с в проводнике сопротивлением {Rr} Ом выделилось {tnum(Q)} Дж.', I, 'в амперах'
        e = f'I² = Q/(Rt) = {tnum(Q)}/({Rr}·{t}) = {tnum(I * I)}, I = {tnum(I)}.'
        chk = lambda: same(num(ans), [s_ for s_ in sp.solve(sp.Eq(sp.Symbol('I') ** 2 * Rr * t, R(Q)), sp.Symbol('I')) if s_ > 0][0])
    elif kind == 1:
        k = r.choice([50, 100, 200, 250, 400, 500, 800, 1000])
        x = F(r.randint(1, 40), 100)
        E = k * x * x / 2
        if not nice(E, 3):
            return None
        head = 'Энергия (в джоулях) сжатой пружины вычисляется по формуле E = kx²/2, где k — жёсткость пружины (в Н/м), x — сжатие (в метрах).'
        ask, ans, unit = f'сжатие пружины жёсткостью {k} Н/м, если её энергия равна {tnum(E)} Дж.', x, 'в метрах'
        e = f'x² = 2E/k = {tnum(2 * E / k)}, x = {tnum(x)}.'
        chk = lambda: same(num(ans), [s_ for s_ in sp.solve(sp.Eq(k * sp.Symbol('x') ** 2 / 2, R(E)), sp.Symbol('x')) if s_ > 0][0])
    elif kind == 2:
        U = r.choice([6, 9, 12, 20, 24, 36, 110, 127, 220, 40, 60])
        Rr = r.choice([2, 4, 5, 8, 10, 20, 40, 50, 100])
        Pw = F(U * U, Rr)
        if not nice(Pw, 2):
            return None
        head = 'Мощность (в ваттах) электрической цепи вычисляется по формуле P = U²/R, где U — напряжение (в вольтах), R — сопротивление (в омах).'
        ask, ans, unit = f'напряжение, если мощность равна {tnum(Pw)} Вт, а сопротивление {Rr} Ом.', U, 'в вольтах'
        e = f'U² = PR = {tnum(Pw)}·{Rr} = {U * U}, U = {U}.'
        chk = lambda: same(num(ans), [s_ for s_ in sp.solve(sp.Eq(sp.Symbol('U') ** 2 / Rr, R(Pw)), sp.Symbol('U')) if s_ > 0][0])
    else:
        m = r.choice([1, 2, 4, 5, 10, 20, 50, 60, 80, 100])
        v = r.randint(2, 25)
        rr = r.choice([1, 2, 4, 5, 10, 20, 25, 50])
        Fc = F(m * v * v, rr)
        if not nice(Fc, 2):
            return None
        head = ('Центростремительная сила (в ньютонах) вычисляется по формуле F = mv²/r, где m — масса (в кг), v — скорость (в м/с), r — радиус (в метрах).')
        ask, ans, unit = f'скорость тела массой {m} кг, движущегося по окружности радиусом {rr} м, если на него действует сила {tnum(Fc)} Н.', v, 'в метрах в секунду'
        e = f'v² = Fr/m = {v * v}, v = {v}.'
        chk = lambda: same(num(ans), [s_ for s_ in sp.solve(sp.Eq(m * sp.Symbol('v') ** 2 / rr, R(Fc)), sp.Symbol('v')) if s_ > 0][0])
    return _f12(r, head, ask, ans, e, chk, unit)


@proto('og12-sine', 'oge', 12, 'Геометрическая формула с синусом',
       invariant='Формула площади/радиуса с синусом угла (S = ½ab·sin γ, S = ab·sin α, R = a/(2 sin α)); синус дан дробью; найти длину.',
       varies='Формула, известные величины, значение синуса.',
       answer_rule='Выражаем искомую длину и подставляем; синус — обыкновенная дробь.',
       fipi=r'sin\s*α.{0,200}найдите длину диагонали',
       mistakes=['забывают коэффициент ½ или 2', 'умножают на синус вместо деления'], kim=K12)
def gen_og12_sine(r):
    kind = r.randrange(3)
    sn = F(r.randint(1, 6), r.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 11]))
    if sn >= 1 or sn.denominator == 1:
        return None
    st = ufr(sn.numerator, sn.denominator)
    if kind == 0:
        a, b = r.randint(2, 30), r.randint(2, 30)
        S = F(a * b, 2) * sn
        if not nice(S, 2):
            return None
        head = 'Площадь треугольника можно найти по формуле S = ½ab·sin γ, где a и b — две стороны треугольника, γ — угол между ними.'
        ask, ans = f'сторону a, если b = {b}, sin γ = {st}, а S = {tnum(S)}.', a
        e = f'a = 2S/(b·sin γ) = {tnum(2 * S)}/({b}·{st}) = {a}.'
        chk = lambda: same(num(ans), sp.solve(sp.Eq(sp.Symbol('a') * b * R(sn) / 2, R(S)), sp.Symbol('a'))[0])
    elif kind == 1:
        a, b = r.randint(2, 30), r.randint(2, 30)
        S = a * b * sn
        if not nice(S, 2):
            return None
        head = 'Площадь параллелограмма вычисляется по формуле S = ab·sin α, где a и b — стороны параллелограмма, α — угол между ними.'
        ask, ans = f'сторону b, если a = {a}, sin α = {st}, S = {tnum(S)}.', b
        e = f'b = S/(a·sin α) = {tnum(S)}/({a}·{st}) = {b}.'
        chk = lambda: same(num(ans), sp.solve(sp.Eq(a * sp.Symbol('b') * R(sn), R(S)), sp.Symbol('b'))[0])
    else:
        Rr = F(r.randint(2, 40), r.choice([1, 2]))
        a = 2 * Rr * sn
        if not nice(a, 2):
            return None
        head = 'Если в треугольнике известны сторона a и противолежащий ей угол α, то описанную около него окружность задаёт радиус R = a/(2 sin α) (следствие теоремы синусов).'
        if r.random() < 0.5:
            ask, ans = f'сторону a, если R = {tnum(Rr)}, sin α = {st}.', a
            e = f'a = 2R·sin α = 2·{tnum(Rr)}·{st} = {tnum(a)}.'
        else:
            ask, ans = f'радиус R, если a = {tnum(a)}, sin α = {st}.', Rr
            e = f'R = {tnum(a)}/(2·{st}) = {tnum(Rr)}.'
        chk = lambda: same(num(ans), R(a) / (2 * R(sn)) if ans == Rr else 2 * R(Rr) * R(sn))
    return _f12(r, head, ask, ans, e, chk)


# ================================================================ №13 — неравенства: выбор ответа

K13 = K(minutes=3, kes=['3.2', '6.1'], kt=[5], answer='цифра варианта',
        style='«Укажите решение неравенства (системы)…» с вариантами-промежутками или рисунками 1)–4); в ответ — номер (КИМ ОГЭ №13)')
FLIP = {'<': '>', '>': '<', '≤': '≥', '≥': '≤'}
REL = {'<': sp.Lt, '>': sp.Gt, '≤': sp.Le, '≥': sp.Ge}
ASK13 = ('Укажите решение неравенства {x}.', 'Какое из множеств является решением неравенства {x}?', 'Выберите множество решений неравенства {x}.')
ASK13S = ('Укажите решение системы неравенств {x}.', 'Какое из множеств является решением системы {x}?', 'Выберите множество решений системы неравенств {x}.')
REALS = ((None, None, False, False),)
PIC13 = ' Каждый из вариантов ответа 1–4 показан на своей координатной прямой.'

# Множество на прямой — кортеж интервалов (a, b, a_closed, b_closed); a/b = None — бесконечность.


def ray(rel, c):
    """Решение x rel c."""
    c = F(c)
    return {'<': ((None, c, False, False),), '≤': ((None, c, False, True),),
            '>': ((c, None, False, False),), '≥': ((c, None, True, False),)}[rel]


def lin_sol(k, m, rel):
    """k·x rel m."""
    return ray(rel if k > 0 else FLIP[rel], F(m) / k)


def quad_sol(a, r1, r2, rel):
    """a(x − r1)(x − r2) rel 0, r1 < r2."""
    if a < 0:
        rel = FLIP[rel]
    cl = rel in '≤≥'
    if rel in '<≤':
        return ((F(r1), F(r2), cl, cl),)
    return ((None, F(r1), False, cl), (F(r2), None, cl, False))


def s_and(S, T):
    out = []
    for a1, b1, ca1, cb1 in S:
        for a2, b2, ca2, cb2 in T:
            if a1 is None or (a2 is not None and a2 > a1):
                a, ca = a2, ca2
            elif a2 is None or a1 > a2:
                a, ca = a1, ca1
            else:
                a, ca = a1, ca1 and ca2
            if b1 is None or (b2 is not None and b2 < b1):
                b, cb = b2, cb2
            elif b2 is None or b1 < b2:
                b, cb = b1, cb1
            else:
                b, cb = b1, cb1 and cb2
            if a is not None and b is not None and (a > b or a == b and not (ca and cb)):
                continue
            out.append((a, b, ca, cb))
    return tuple(out)


def s_not(S):
    """Дополнение до прямой."""
    out = []
    prev, pc = None, False
    for a, b, ca, cb in S:
        if a is not None:
            out.append((prev, a, pc, not ca))
        prev, pc = b, (not cb) if b is not None else False
        if b is None:
            prev = 'end'
    if prev != 'end':
        out.append((prev, None, pc, False))
    return tuple(i for i in out if not (i[0] is not None and i[1] is not None and i[0] == i[1] and not (i[2] and i[3])))


def s_flip(S):
    return tuple((a, b, (not ca) if a is not None else False, (not cb) if b is not None else False) for a, b, ca, cb in S)


def s_or(S, T):
    return s_not(s_and(s_not(S), s_not(T)))


def s_sympy(S):
    x = sp.Union(*[sp.Interval(-sp.oo if a is None else R(a), sp.oo if b is None else R(b), not ca, not cb) for a, b, ca, cb in S])
    return x if S else sp.EmptySet


def _nb(v):
    """Граница промежутка: конечная десятичная — десятичной, иначе дробью."""
    return tnum(v) if finite(v) else fr(v)


def s_txt(S):
    if not S:
        return 'решений нет'
    out = []
    for a, b, ca, cb in S:
        if a is not None and a == b:
            out.append('{' + _nb(a) + '}')
            continue
        L = '(−∞' if a is None else ('[' if ca else '(') + _nb(a)
        Rt = '+∞)' if b is None else _nb(b) + (']' if cb else ')')
        out.append(f'{L}; {Rt}')
    return ' ∪ '.join(out)


def s_rows(sets, lo, hi, names=None):
    rows = []
    for n, S in enumerate(sets, 1):
        ivs, marks, ends = [], {}, {}
        for a, b, ca, cb in S:
            ivs.append((None if a is None else float(a), None if b is None else float(b), ca, cb))
            for v in (a, b):
                if v is not None:
                    marks[float(v)] = _nb(v)
        rows.append((names[n - 1] if names else str(n), ivs, sorted(marks.items()), lo, hi))
    return rows


def s_span(sets):
    pts = [v for S in sets for a, b, _, _ in S for v in (a, b) if v is not None]
    if not pts:
        return -5, 5
    lo, hi = float(min(pts)), float(max(pts))
    pad = max(1.5, (hi - lo) * 0.35)
    return lo - pad, hi + pad


def _sym_solve(lhs, rel, rhs):
    x = sp.Symbol('x', real=True)
    X_ = sp.Symbol('x')
    return sp.solve_univariate_inequality(REL[rel](parse(lhs).subs(X_, x), parse(rhs).subs(X_, x)), x, relational=False)


def _ineq_card(r, q, sol, wrong, pictures, e, sym_sol):
    cands = []
    for w in wrong:
        if w != sol and w not in cands:
            cands.append(w)
    if len(cands) < 3:
        return None
    sets = [sol] + r.sample(cands, 3)
    order = list(range(4))
    r.shuffle(order)
    sets = [sets[i] for i in order]
    right = order.index(0)
    extra = {}
    if pictures:
        lo, hi = s_span(sets)
        extra['svg'] = svg_rays(s_rows(sets, lo, hi))
        o = [{'id': str(i + 1), 't': f'рисунок {i + 1}'} for i in range(4)]
    else:
        o = [{'id': str(i + 1), 't': s_txt(S)} for i, S in enumerate(sets)]
        if len({x['t'] for x in o}) < 4:
            return None

    def chk():
        got = sym_sol()
        return sum(1 for S in sets if s_sympy(S) == got) == 1 and s_sympy(sets[right]) == got
    return pcard(q, str(right + 1), e=e, k='one', o=o, **extra), chk


@proto('og13-lin', 'oge', 13, 'Линейное неравенство: выбор решения',
       invariant='a + bx ≷ cx + d: перенос слагаемых, деление на коэффициент (со сменой знака при отрицательном).',
       varies='Коэффициенты, знак неравенства (строгий/нестрогий), форма вариантов (промежутки или рисунки).',
       answer_rule='Приводим к виду kx ≷ m, делим на k (при k < 0 знак меняется), выбираем промежуток.',
       fipi=r'Укажите решение неравенства\s+[−-]?\s*\d+\s*[−-]\s*\d*\s*x\s*[<>≤≥]',
       mistakes=['не меняют знак при делении на отрицательное число', 'путают строгий и нестрогий знак (скобка/точка)'],
       card_kind='one', kim=K13)
def gen_og13_lin(r):
    a, b = r.choice([x for x in range(-9, 10) if x]), r.choice([x for x in range(-9, 10) if x])
    c, d = r.choice([x for x in range(-9, 10) if x]), r.randint(-9, 9)
    if b == c:
        return None
    rel = r.choice(list(FLIP))
    lhs = f'{tnum(a)}{signed(b)}x'.replace(' 1x', ' x')
    rhs = lin(c, d).replace('−1x', '−x') if lin(c, d) != '0' else '0'
    k, m = b - c, d - a
    bound = F(m, k)
    if not nice(bound, 2):
        return None
    sol = lin_sol(k, m, rel)
    wrong = [s_not(sol), s_flip(sol), s_flip(s_not(sol)), ray(FLIP[rel] if k < 0 else rel, -bound) if bound else ray(rel, 1)]
    wrong += [lin_sol(-k, m, rel)] if k != 0 else []
    pictures = r.random() < 0.5
    q = (pick(r, *ASK13[1:]) if pictures else pick(r, *ASK13)).format(x=f'{lhs} {rel} {rhs}') + (PIC13 if pictures else '')
    e = f'{lin(k, 0)} {rel} {tnum(m)}; ' + (f'делим на {tnum(k)} и меняем знак: ' if k < 0 else f'делим на {tnum(k)}: ') + f'x {FLIP[rel] if k < 0 else rel} {fr(bound)}.'
    return _ineq_card(r, q, sol, wrong, pictures, e, lambda: _sym_solve(lhs, rel, rhs))


@proto('og13-system', 'oge', 13, 'Система линейных неравенств: выбор решения',
       invariant='Система двух линейных неравенств; решение — пересечение лучей (отрезок, луч или пустое множество).',
       varies='Коэффициенты, знаки, десятичные границы, форма вариантов (рисунки или промежутки).',
       answer_rule='Решаем каждое неравенство, пересекаем решения на прямой.',
       fipi=r'Укажите решение системы неравенств',
       mistakes=['берут объединение вместо пересечения', 'не меняют знак при делении на отрицательное'],
       card_kind='one', kim=K13)
def gen_og13_system(r):
    parts, sets = [], []
    for _ in range(2):
        k = r.choice([1, 1, 1, 2, 3, 4, 5, -1, -2, -3, -4, -5])
        bound = F(r.randint(-12, 12)) if r.random() < 0.6 else F(r.randint(-99, 99), 10)
        m = k * bound
        rel = r.choice(list(FLIP))
        c = F(r.randint(-9, 9)) if r.random() < 0.7 else F(r.randint(-49, 49), 10)
        if not nice(m + c, 1) or abs(m + c) > 40:
            return None
        if c and r.random() < 0.4:
            lhs = f'{tnum(c)}{signed(k)}x'.replace(' 1x', ' x')
        else:
            lhs = (lin(k, c) if c else lin(k, 0)).replace('−1x', '−x')
        rhs = tnum(m + c)
        parts.append((lhs, rel, rhs))
        sets.append(lin_sol(k, m, rel))
    sol = s_and(*sets)
    if any(a is not None and a == b for a, b, _, _ in sol):
        return None
    wrong = [s_or(*sets), sets[0], sets[1], s_flip(sol) if sol else REALS, s_not(sol) if sol else ((F(-1), F(1), True, True),)]
    if len(sol) == 1 and sol[0][0] is not None and sol[0][1] is not None:
        a_, b_, ca, cb = sol[0]
        wrong += [((None, a_, False, not ca), (b_, None, not cb, False))]
    pictures = r.random() < 0.6
    txt = f'{{ {parts[0][0]} {parts[0][1]} {parts[0][2]};  {parts[1][0]} {parts[1][1]} {parts[1][2]} }}'
    q = (pick(r, *ASK13S[1:]) if pictures else pick(r, *ASK13S)).format(x=txt) + (PIC13 if pictures else '')
    e = f'Первое: x ∈ {s_txt(sets[0])}; второе: x ∈ {s_txt(sets[1])}; общая часть: {s_txt(sol)}.'
    return _ineq_card(r, q, sol, wrong, pictures, e, lambda: _sym_solve(*parts[0]).intersect(_sym_solve(*parts[1])))


@proto('og13-quad', 'oge', 13, 'Квадратное неравенство: выбор решения',
       invariant='x² − a² ≷ 0, p²x² ≷ q², kx − x² ≷ 0: корни и знаки параболы; решение — отрезок/интервал или объединение лучей.',
       varies='Вид неравенства, числа, знак, форма вариантов (промежутки или рисунки).',
       answer_rule='Находим корни, учитываем направление ветвей, выбираем нужные промежутки.',
       fipi=r'Укажите решение неравенства\s+(\d+\s*x\s*[−-]\s*x\s*2|\d*\s*x\s*2\s*[−-<>≤≥])',
       mistakes=['берут промежуток между корнями вместо внешних лучей', 'для kx − x² забывают, что ветви вниз'],
       card_kind='one', kim=K13)
def gen_og13_quad(r):
    kind = r.randrange(3)
    rel = r.choice(list(FLIP))
    if kind == 0:
        a = r.randint(2, 15)
        lhs, rhs = f'x² − {a * a}', '0'
        if r.random() < 0.4:
            lhs, rhs = 'x²', str(a * a)
        sol = quad_sol(1, -a, a, rel)
    elif kind == 1:
        p, q_ = r.randint(2, 13), r.randint(2, 13)
        if math.gcd(p, q_) != 1:
            return None
        lhs, rhs = f'{p * p}x²', f'{q_ * q_}'
        sol = quad_sol(1, -F(q_, p), F(q_, p), rel)
    else:
        k = r.randint(2, 12)
        if r.random() < 0.6:
            lhs, rhs = f'{k}x − x²', '0'
            sol = quad_sol(-1, 0, k, rel)
        else:
            lhs, rhs = f'x² − {k}x', '0'
            sol = quad_sol(1, 0, k, rel)
    wrong = [s_not(sol), s_flip(sol), s_flip(s_not(sol))]
    if len(sol) == 2:
        wrong += [(sol[1],), (sol[0],)]
    else:
        a_, b_, ca, cb = sol[0]
        wrong += [((None, b_, False, cb),), ((a_, None, ca, False),)]
    pictures = r.random() < 0.5
    q = (pick(r, *ASK13[1:]) if pictures else pick(r, *ASK13)).format(x=f'{lhs} {rel} {rhs}') + (PIC13 if pictures else '')
    e = f'Корни и направление ветвей параболы дают: x ∈ {s_txt(sol)}.'
    return _ineq_card(r, q, sol, wrong, pictures, e, lambda: _sym_solve(lhs, rel, rhs))


@proto('og13-which', 'oge', 13, 'Какое неравенство изображено на рисунке',
       invariant='По рисунку множества решений выбрать неравенство из четырёх (квадратные или линейные) с похожими числами.',
       varies='Число на рисунке, вид неравенств (x² − ax, x² − a², линейные), знаки.',
       answer_rule='Решаем каждое неравенство (или проверяем точки) и сравниваем с рисунком.',
       fipi=r'Укажите неравенство, решение которого изображено на рисунке',
       mistakes=['путают x² − a² и x² − ax', 'путают знак неравенства и «внутренность/внешность»'],
       svg=True, card_kind='one', kim=K13)
def gen_og13_which(r):
    a = r.randint(2, 12)
    pool = []
    if r.random() < 0.7:
        for rel in FLIP:
            pool += [(f'x² − {a}x', rel, quad_sol(1, 0, a, rel)), (f'x² − {a * a}', rel, quad_sol(1, -a, a, rel))]
    else:
        k = r.choice([1, 2, 3, 4, 5])
        for rel in FLIP:
            pool += [(lin(k, -k * a), rel, lin_sol(k, k * a, rel)), (lin(k, k * a), rel, lin_sol(k, -k * a, rel))]
    four = r.sample(pool, 4)
    if len({f[2] for f in four}) < 4:
        return None
    right = r.randrange(4)
    S = four[right][2]
    lo, hi = s_span([S])
    lo, hi = min(lo, -1.5), max(hi, 1.5)
    rows = s_rows([S], lo, hi, names=[''])
    marks = rows[0][2]
    if not any(abs(m[0]) < 1e-9 for m in marks):
        marks = sorted(marks + [(0.0, '0')])
    svg = svg_rays([('', rows[0][1], marks, lo, hi)])
    o = [{'id': str(i + 1), 't': f'{l_} {rel} 0'} for i, (l_, rel, _) in enumerate(four)]
    q = pick(r, 'Укажите неравенство, множество решений которого показано на рисунке.', 'На рисунке изображено множество решений одного из неравенств. Какого?',
             'Какое из неравенств имеет решение, изображённое на координатной прямой?')
    e = f'На рисунке: {s_txt(S)}. Это решение неравенства {four[right][0]} {four[right][1]} 0.'
    sS = s_sympy(S)
    return pcard(q, str(right + 1), e=e, k='one', o=o, svg=svg), lambda: sum(1 for l_, rel, _ in four if _sym_solve(l_, rel, '0') == sS) == 1 and \
        _sym_solve(four[right][0], four[right][1], '0') == sS


# ================================================================ №1–5 — практико-ориентированные блоки
#
# Каждый сюжет — генератор данных «блока»; прототип = позиция блока (№1…№5) внутри сюжета.
# Карточка несёт короткое общее вводное (своё) и один вопрос; рисунок — план или таблица.


def KP(n, kes, kt, minutes=4, answer='число', style=''):
    return {'level': 'Б', 'points': 1, 'minutes': minutes, 'kes': kes, 'kt': [f'КТ {k}' for k in kt], 'answer': answer,
            'style': style or 'Общий текст-сюжет к заданиям 1–5, вопрос позиции №' + str(n) + '; «Ответ дайте в …», округление как в КИМ'}


def svg_table(rows, colw=None, width=None, head=1):
    """Таблица-картинка: rows — списки строк; первые head строк — заголовок."""
    ncol = max(len(rw) for rw in rows)
    colw = colw or [max(40, 8 * max(len(str(rw[i])) if i < len(rw) else 0 for rw in rows) + 16) for i in range(ncol)]
    W = sum(colw) + 2
    rh = 24
    H = rh * len(rows) + 2
    out = ''
    for j, rw in enumerate(rows):
        y = 1 + j * rh
        if j < head:
            out += f'<rect x="1" y="{y}" width="{W - 2}" height="{rh}" fill="#EEF2FA"/>'
        x = 1
        for i in range(ncol):
            t = rw[i] if i < len(rw) else ''
            out += f'<rect x="{x}" y="{y}" width="{colw[i]}" height="{rh}" fill="none" stroke="{GRID}" stroke-width="1"/>'
            fw = ' font-weight="bold"' if j < head else ''
            out += f'<text x="{x + colw[i] / 2:.0f}" y="{y + 16}" text-anchor="middle" font-size="12"{fw}>{t}</text>'
            x += colw[i]
    return _svg(W, H, out)


def _pct_round1(x):
    """Округление процента до десятых (половина — вверх)."""
    return F(math.floor(F(x) * 10 + F(1, 2)), 10)


# ---------------------------------------------------------------- сюжет «маркировка шин»

VEH = [
    dict(name='скутер', who='Завод выпускает скутеры одной модели', W=[90, 100, 110, 120, 130], P=[70, 80, 90], D=[10, 12, 13], unit='скутер'),
    dict(name='мотоцикл', who='Мотозавод выпускает мотоциклы одной модели', W=[110, 120, 130, 140, 150, 160], P=[60, 70, 80], D=[17, 18, 19], unit='мотоцикл'),
    dict(name='кроссовер', who='Автозавод собирает кроссоверы одной модели', W=[205, 215, 225, 235, 245], P=[50, 55, 60, 65], D=[16, 17, 18], unit='кроссовер'),
    dict(name='микроавтобус', who='Предприятие выпускает микроавтобусы одной модели', W=[185, 195, 205, 215], P=[65, 70, 75], D=[14, 15, 16], unit='микроавтобус'),
    dict(name='электромобиль', who='Компания производит городские электромобили одной модели', W=[165, 175, 185, 195], P=[55, 60, 65, 70], D=[13, 14, 15], unit='электромобиль'),
]
INTRO_T = ('Размер шины записывают кодом вида {ex}. Первое число — ширина шины B в миллиметрах. Второе число показывает, сколько процентов ширины '
           'составляет высота боковины H. Число после R — диаметр диска d в дюймах, 1 дюйм = 25,4 мм. Диаметр колеса D складывается из диаметра диска и двух высот боковины.')


def _tyre(W, P, d):
    return f'{W}/{P} R{d}'


def _tyre_block(r):
    v = r.choice(VEH)
    Ws = sorted(r.sample(v['W'], 3))
    Ds = v['D']
    table = {}
    for W in Ws:
        for d in Ds:
            if r.random() < 0.65:
                table[(W, d)] = sorted(r.sample(v['P'], r.choice([1, 1, 2])), reverse=True)
    if not all(any((W, d) in table for W in Ws) for d in Ds):
        return None
    base = r.choice(sorted(table))
    W0, d0 = base
    P0 = table[base][0]
    ex = _tyre(r.choice(v['W']), r.choice(v['P']), r.choice(Ds))
    intro = INTRO_T.format(ex=ex) + f' {v["who"]} и ставит на них шины {_tyre(W0, P0, d0)}.'
    return dict(v=v, Ws=Ws, Ds=Ds, table=table, W0=W0, P0=P0, d0=d0, intro=intro)


def _tyre_svg(b):
    rows = [['Ширина, мм'] + [f'd = {d}″' for d in b['Ds']]]
    for W in b['Ws']:
        rows.append([str(W)] + ['; '.join(_tyre(W, P, d).split(' ')[0] for P in b['table'][(W, d)]) if (W, d) in b['table'] else '—' for d in b['Ds']])
    return svg_table(rows)


KT1 = KP(1, ['8.1', '1.2'], [8, 14], 3, style='Чтение таблицы допустимых размеров; «Ответ дайте в миллиметрах»')


@proto('og01-tyre-table', 'oge', 1, 'Шины: чтение таблицы разрешённых размеров',
       invariant='Таблица «ширина × диаметр диска» с допустимыми маркировками; найти наибольшую/наименьшую ширину для данного диска или наибольший/наименьший диск для данной ширины.',
       varies='Транспорт, набор ширин и дисков, заполнение таблицы, спрашиваемый экстремум.',
       answer_rule='Смотрим нужный столбец (строку) таблицы и выбираем экстремальное значение среди непустых клеток.',
       fipi=r'Шины какой (наибольшей|наименьшей) ширины',
       mistakes=['читают не тот столбец', 'берут значение из клетки с прочерком'], svg=True, kim=KT1)
def gen_og01_tyre_table(r):
    b = _tyre_block(r)
    if not b:
        return None
    if r.random() < 0.6:
        d = r.choice(b['Ds'])
        ws = [W for W in b['Ws'] if (W, d) in b['table']]
        if len(ws) < 2:
            return None
        mx = r.random() < 0.5
        ans = max(ws) if mx else min(ws)
        ask = (f'Шины какой {"наибольшей" if mx else "наименьшей"} ширины разрешено ставить на {b["v"]["unit"]}, если диаметр диска равен {d} дюймам? '
               'Ответ дайте в миллиметрах.')
        chk = lambda: ans == (max if mx else min)(W for (W, dd) in b['table'] if dd == d)
    else:
        W = r.choice(b['Ws'])
        ds = [d for d in b['Ds'] if (W, d) in b['table']]
        if len(ds) < 2:
            return None
        mx = r.random() < 0.5
        ans = max(ds) if mx else min(ds)
        ask = f'Какой {"наибольший" if mx else "наименьший"} диаметр диска (в дюймах) допускается для шин шириной {W} мм?'
        chk = lambda: ans == (max if mx else min)(dd for (WW, dd) in b['table'] if WW == W)
    q = b['intro'] + ' В таблице указано, какие ещё размеры шин допускает производитель.\n' + ask
    return pcard(q, num(ans), e=f'По таблице: {ans}.', svg=_tyre_svg(b)), chk


def _H(W, P):
    return F(W * P, 100)


def _D(W, P, d):
    return F(254, 10) * d + 2 * _H(W, P)


def _parse_tyre(t):
    W, P, d = map(int, re.match(r'(\d+)/(\d+) R(\d+)', t).groups())
    return sp.Rational(W * P, 100), sp.Rational(254, 10) * d + sp.Rational(2 * W * P, 100)


@proto('og02-tyre-sidewall', 'oge', 2, 'Шины: высота боковины по маркировке',
       invariant='По коду B/H Rd найти высоту боковины: процент от ширины.',
       varies='Транспорт, маркировка (ширина, процент).',
       answer_rule='H = B · (процент)/100.',
       fipi=r'высота боковины шины',
       mistakes=['берут процент как миллиметры', 'путают ширину и диаметр'], kim=KP(2, ['1.2', '3.3'], [8], 2))
def gen_og02_tyre_sidewall(r):
    b = _tyre_block(r)
    if not b:
        return None
    W, P = r.choice(b['v']['W']), r.choice(b['v']['P'])
    d = r.choice(b['Ds'])
    t = _tyre(W, P, d)
    H = _H(W, P)
    q = b['intro'] + '\n' + pick(r, f'Сколько миллиметров составляет высота боковины шины с маркировкой {t}?',
                                 f'Найдите высоту боковины шины {t}. Ответ дайте в миллиметрах.')
    return pcard(q, num(H), e=f'H = {W}·{P}/100 = {tnum(H)} мм.'), lambda: same(num(H), _parse_tyre(t)[0])


@proto('og03-tyre-diameter', 'oge', 3, 'Шины: диаметр колеса',
       invariant='Диаметр колеса = диаметр диска (дюймы → мм) + 2 высоты боковины.',
       varies='Транспорт, заводская маркировка.',
       answer_rule='D = 25,4·d + 2·B·(процент)/100.',
       fipi=r'Найдите диаметр колеса',
       mistakes=['прибавляют одну высоту боковины', 'забывают перевести дюймы'], kim=KP(3, ['1.2', '3.3'], [8], 3))
def gen_og03_tyre_diameter(r):
    b = _tyre_block(r)
    if not b:
        return None
    t = _tyre(b['W0'], b['P0'], b['d0'])
    D = _D(b['W0'], b['P0'], b['d0'])
    q = b['intro'] + '\n' + pick(r, f'Найдите диаметр колеса {b["v"]["unit"] if b["v"]["unit"] != "скутер" else "скутера"}, сходящего с конвейера. Ответ дайте в миллиметрах.',
                                 'Каков диаметр заводского колеса (в миллиметрах)?')
    q = q.replace('колеса скутер,', 'колеса скутера,').replace('колеса мотоцикл,', 'колеса мотоцикла,').replace('колеса кроссовер,', 'колеса кроссовера,') \
        .replace('колеса микроавтобус,', 'колеса микроавтобуса,').replace('колеса электромобиль,', 'колеса электромобиля,')
    return pcard(q, num(D), e=f'D = 25,4·{b["d0"]} + 2·{tnum(_H(b["W0"], b["P0"]))} = {tnum(D)} мм.'), lambda: same(num(D), _parse_tyre(t)[1])


@proto('og04-tyre-diff', 'oge', 4, 'Шины: на сколько изменится диаметр (радиус) колеса',
       invariant='Сравнение двух колёс с разными шинами: разность диаметров или радиусов в миллиметрах.',
       varies='Транспорт, две маркировки из таблицы, диаметр или радиус, «больше/меньше».',
       answer_rule='Считаем D (или R = D/2) для обеих шин и вычитаем.',
       fipi=r'(увеличится|уменьшится) диаметр колеса|радиус колеса с шиной',
       mistakes=['сравнивают только высоты боковин при разных дисках', 'путают радиус и диаметр'], kim=KP(4, ['1.2', '3.3'], [8], 4))
def gen_og04_tyre_diff(r):
    b = _tyre_block(r)
    if not b:
        return None
    opts_ = [(W, P, d) for (W, d), Ps in b['table'].items() for P in Ps if (W, P, d) != (b['W0'], b['P0'], b['d0'])]
    if not opts_:
        return None
    W, P, d = r.choice(opts_)
    t0, t1 = _tyre(b['W0'], b['P0'], b['d0']), _tyre(W, P, d)
    D0, D1 = _D(b['W0'], b['P0'], b['d0']), _D(W, P, d)
    if D0 == D1:
        return None
    rad = r.random() < 0.4
    diff = abs(D1 - D0) / (2 if rad else 1)
    if not nice(diff, 2):
        return None
    word = 'увеличится' if D1 > D0 else 'уменьшится'
    q = b['intro'] + ' Производитель разрешает ставить и другие шины, указанные в таблице.\n'
    if rad:
        q += f'На сколько миллиметров радиус колеса с шиной {t1} {"больше" if D1 > D0 else "меньше"}, чем радиус заводского колеса?'
    else:
        q += f'На сколько миллиметров {word} диаметр колеса, если заменить заводские шины шинами {t1}?'
    e = f'D₀ = {tnum(D0)} мм, D₁ = {tnum(D1)} мм; разность {"радиусов" if rad else "диаметров"}: {tnum(diff)} мм.'
    return pcard(q, num(diff), e=e, svg=_tyre_svg(b)), lambda: same(num(diff), abs(_parse_tyre(t1)[1] - _parse_tyre(t0)[1]) / (2 if rad else 1))


@proto('og05-tyre-percent', 'oge', 5, 'Шины: на сколько процентов изменится пробег за оборот',
       invariant='Путь за один оборот пропорционален диаметру колеса; процент изменения = (D₁/D₀ − 1)·100, округлить до десятых.',
       varies='Транспорт, новая маркировка, «увеличится/уменьшится».',
       answer_rule='Находим оба диаметра, делим, переводим в проценты и округляем до десятых.',
       fipi=r'На сколько процентов (увеличится|уменьшится) пробег',
       mistakes=['делят на новый диаметр вместо старого', 'округляют раньше времени'], maxdec=1, kim=KP(5, ['1.2', '1.5', '3.3'], [8], 5))
def gen_og05_tyre_percent(r):
    b = _tyre_block(r)
    if not b:
        return None
    opts_ = [(W, P, d) for (W, d), Ps in b['table'].items() for P in Ps if (W, P, d) != (b['W0'], b['P0'], b['d0'])]
    if not opts_:
        return None
    W, P, d = r.choice(opts_)
    t0, t1 = _tyre(b['W0'], b['P0'], b['d0']), _tyre(W, P, d)
    D0, D1 = _D(b['W0'], b['P0'], b['d0']), _D(W, P, d)
    if D0 == D1:
        return None
    pct = abs(D1 / D0 - 1) * 100
    ans = _pct_round1(pct)
    if abs(pct * 10 - int(pct * 10) - F(1, 2)) < F(1, 1000) or ans == 0:
        return None
    word = 'увеличится' if D1 > D0 else 'уменьшится'
    q = (b['intro'] + ' Производитель разрешает ставить и другие шины, указанные в таблице.\n'
         f'На сколько процентов {word} расстояние, которое {b["v"]["unit"]} проезжает за один оборот колеса, если заводские шины заменить шинами {t1}? Результат округлите до десятых.')
    e = f'D₀ = {tnum(D0)} мм, D₁ = {tnum(D1)} мм; ({tnum(D1)}/{tnum(D0)} − 1)·100% ≈ {tnum(ans)}%.'
    return pcard(q, num(ans), e=e, svg=_tyre_svg(b)), lambda: same(num(ans), sp.Rational(round(abs(_parse_tyre(t1)[1] / _parse_tyre(t0)[1] - 1) * 1000), 10))


# ---------------------------------------------------------------- сюжет «форматы бумаги серий B и C»

PAPER = {
    'B': [(1000, 1414), (707, 1000), (500, 707), (353, 500), (250, 353), (176, 250), (125, 176), (88, 125)],
    'C': [(917, 1297), (648, 917), (458, 648), (324, 458), (229, 324), (162, 229), (114, 162), (81, 114)],
}
PAPER['RA'] = [(860, 1220), (610, 860), (430, 610), (305, 430), (215, 305)]
PAPER['SRA'] = [(900, 1280), (640, 900), (450, 640), (320, 450), (225, 320)]
PAPER_USE = {'B': 'плакатов, книг и паспортов', 'C': 'конвертов и папок', 'RA': 'печати в типографиях (с запасом под обрезку)',
             'SRA': 'печати «в край» с большим запасом под обрезку'}
SERIES = ['B', 'C', 'RA', 'SRA']


def _paper_intro(ser):
    s0 = PAPER[ser][0]
    return (f'Кроме привычной серии A, стандарт ISO 216 описывает форматы бумаги серии {ser} — их используют для {PAPER_USE[ser]}. '
            f'Самый большой лист {ser}0 имеет размеры {s0[0]} × {s0[1]} мм. Если лист любого формата разрезать пополам поперёк большей стороны, '
            f'получатся два листа следующего формата: из {ser}0 — два {ser}1, из {ser}1 — два {ser}2 и так далее. '
            + ('Отношение большей стороны к меньшей у всех листов серии одинаковое.' if ser in 'BC' else 'Стандарт ISO 217 задаёт такие листы для типографий.'))


@proto('og01-paper-match', 'oge', 1, 'Форматы бумаги: соответствие форматов и размеров листов',
       invariant='Даны размеры четырёх листов (номера 1–4) и четыре формата серии; каждый следующий формат вдвое меньше; установить соответствие.',
       varies='Серия (B или C), набор форматов, порядок листов.',
       answer_rule='Чем больше номер формата, тем меньше лист; каждый следующий получается делением большей стороны пополам.',
       fipi=r'В таблице даны размеры .{0,60}листов, имеющих форматы',
       mistakes=['путают порядок: считают, что больший номер — больший лист'], card_kind='match',
       kim=KP(1, ['1.2', '8.1'], [8, 14], 3, answer='соответствие'))
def gen_og01_paper_match(r):
    ser = r.choice(SERIES)
    fm = sorted(r.sample(range(0, len(PAPER[ser])), 4))
    order = fm[:]
    r.shuffle(order)
    right_txt = [f'лист {i + 1}: {PAPER[ser][k][1]} × {PAPER[ser][k][0]} мм' for i, k in enumerate(order)]
    left = [{'id': LET[j], 't': f'формат {ser}{k}'} for j, k in enumerate(fm)]
    right = [{'id': str(i + 1), 't': t} for i, t in enumerate(right_txt)]
    a = {LET[j]: str(order.index(k) + 1) for j, k in enumerate(fm)}
    q = _paper_intro(ser) + '\nСопоставьте форматы листов с номерами листов, размеры которых указаны (длина × ширина). Для каждого формата выберите номер листа.'
    e = '; '.join(f'{ser}{k} — {PAPER[ser][k][1]} × {PAPER[ser][k][0]}' for k in fm) + '.'

    def chk():  # площадь каждого следующего формата примерно вдвое меньше: упорядочиваем листы по площади
        by_area = sorted(range(4), key=lambda i: -PAPER[ser][order[i]][0] * PAPER[ser][order[i]][1])
        return all(a[LET[j]] == str(by_area[j] + 1) for j in range(4))
    return pcard(q, a, e=e, k='match', o={'left': left, 'right': right}), chk


@proto('og02-paper-count', 'oge', 2, 'Форматы бумаги: сколько листов получится',
       invariant='Из листа формата n получается 2^(m − n) листов формата m.',
       varies='Серия, два формата.',
       answer_rule='Каждый шаг формата делит лист пополам: 2 в степени разности номеров.',
       fipi=r'Сколько листов формата .{1,4} получится из одного листа',
       mistakes=['считают разность номеров вместо степени двойки'], kim=KP(2, ['1.1', '3.3'], [8], 2))
def gen_og02_paper_count(r):
    ser = r.choice(SERIES)
    L = len(PAPER[ser]) - 1
    n = r.randint(0, L - 1)
    m = r.randint(n + 1, min(L, n + 5))
    ans = 2 ** (m - n)
    q = _paper_intro(ser) + '\n' + pick(r, f'Сколько листов формата {ser}{m} можно нарезать из одного листа формата {ser}{n}?',
                                        f'Типография режет листы {ser}{n} на листы {ser}{m} без обрезков. Сколько листов {ser}{m} выйдет из одного листа {ser}{n}?')
    return pcard(q, num(ans), e=f'Каждый шаг делит лист пополам: 2^{m - n} = {ans}.'), lambda: ans * PAPER[ser][m][0] * PAPER[ser][m][1] / (PAPER[ser][n][0] * PAPER[ser][n][1]) > 0.9 and ans == sp.Integer(2) ** (m - n)


@proto('og03-paper-area', 'oge', 3, 'Форматы бумаги: площадь или сторона листа',
       invariant='По размерам из таблицы (или по делению пополам) найти площадь листа в см² либо длину стороны, округлённую до десятков миллиметров.',
       varies='Серия, формат, спрашиваемая величина.',
       answer_rule='Площадь = длина × ширина (мм² → см² делением на 100); сторона следующего формата — половина большей стороны предыдущего.',
       fipi=r'Найдите площадь листа формата|Найдите (ширину|длину) листа бумаги формата',
       mistakes=['переводят мм² в см² делением на 10', 'берут не ту сторону'], maxdec=2, lim=100000,
       kim=KP(3, ['7.5', '1.5'], [8, 11], 3))
def gen_og03_paper_area(r):
    ser = r.choice(SERIES)
    k = r.randint(1, len(PAPER[ser]) - 1)
    w, h = PAPER[ser][k]
    if r.random() < 0.6:
        ans = F(w * h, 100)
        tab = '; '.join(f'{ser}{i}: {PAPER[ser][i][1]} × {PAPER[ser][i][0]}' for i in range(max(0, k - r.randint(1, 2)), min(len(PAPER[ser]), k + r.randint(1, 2))))
        q = _paper_intro(ser) + f' Размеры некоторых листов (мм): {tab}.\n' + pick(r, f'Найдите площадь листа формата {ser}{k}. Ответ дайте в квадратных сантиметрах.',
                                                                                  f'Какую площадь (в квадратных сантиметрах) имеет лист формата {ser}{k}?')
        e = f'{h}·{w} = {w * h} мм² = {tnum(ans)} см².'
        chk = lambda: same(num(ans), sp.Rational(w * h, 100))
    else:
        ans = F(round(F(PAPER[ser][k - 1][1], 2) / 10) * 10) if False else None
        big = PAPER[ser][k - 1]
        side = F(big[1], 2)  # меньшая сторона нового листа — половина большей стороны предыдущего
        ans = F(math.floor(side / 10 + F(1, 2)) * 10)
        if abs(side % 10 - 5) < 1:
            return None
        q = (_paper_intro(ser) + f' Размеры листа {ser}{k - 1}: {big[1]} × {big[0]} мм.\n'
             f'Найдите длину меньшей стороны листа формата {ser}{k}. Ответ дайте в миллиметрах и округлите до ближайшего числа, кратного 10.')
        e = f'Меньшая сторона {ser}{k} — половина большей стороны {ser}{k - 1}: {big[1]} : 2 = {tnum(side)} мм ≈ {tnum(ans)} мм.'
        chk = lambda: same(num(ans), sp.Integer(round(sp.Rational(big[1], 2) / 10)) * 10)
    return pcard(q, num(ans), e=e), chk


@proto('og04-paper-ratio', 'oge', 4, 'Форматы бумаги: отношение сторон',
       invariant='Отношение большей стороны к меньшей (или меньшей к большей) у листа серии; округлить до десятых.',
       varies='Серия, формат, направление отношения.',
       answer_rule='Делим стороны из таблицы; для любых форматов серии ≈ 1,4 (или ≈ 0,7).',
       fipi=r'Найдите отношение длины (большей|меньшей) стороны листа',
       mistakes=['делят меньшую на большую, когда спрашивают наоборот'], maxdec=1, kim=KP(4, ['1.5', '1.2'], [8], 2))
def gen_og04_paper_ratio(r):
    ser = r.choice(SERIES)
    k = r.randint(0, len(PAPER[ser]) - 1)
    w, h = PAPER[ser][k]
    big = r.random() < 0.5
    val = F(h, w) if big else F(w, h)
    ans = F(math.floor(val * 10 + F(1, 2)), 10)
    q = _paper_intro(ser) + f' Лист формата {ser}{k} имеет размеры {h} × {w} мм.\n' + pick(
        r, f'Найдите отношение {"большей" if big else "меньшей"} стороны листа формата {ser}{k} к {"меньшей" if big else "большей"}. Ответ округлите до десятых.',
        f'Во сколько раз {"большая" if big else "меньшая"} сторона листа {ser}{k} {"больше меньшей" if big else "меньше большей"}? Ответ округлите до десятых.' if big else
        f'Какую часть большей стороны листа {ser}{k} составляет его меньшая сторона? Ответ округлите до десятых.')
    return pcard(q, num(ans), e=f'{h if big else w} : {w if big else h} ≈ {approx(val, 3)} ≈ {tnum(ans)}.'), lambda: same(num(ans), sp.Rational(round(sp.Rational(h, w) * 10 if big else sp.Rational(w, h) * 10), 10))


@proto('og04-paper-mass', 'oge', 4, 'Форматы бумаги: масса пачки',
       invariant='Масса пачки = число листов × площадь листа (м²) × плотность бумаги (г/м²).',
       varies='Серия, формат, число листов, плотность.',
       answer_rule='Площадь листа в м² (мм² : 1 000 000), умножаем на плотность и число листов.',
       fipi=r'упаковали в пачки по \d+ листов',
       mistakes=['ошибка при переводе мм² в м²'], maxdec=2, lim=100000, kim=KP(4, ['1.2', '7.5'], [8, 11], 4))
def gen_og04_paper_mass(r):
    ser = r.choice(SERIES)
    k = r.randint(0, len(PAPER[ser]) - 1)
    w, h = PAPER[ser][k]
    n = r.choice([50, 100, 200, 250, 400, 500])
    g = r.choice([60, 80, 90, 100, 120, 160, 200])
    ans = F(w * h, 10 ** 6) * g * n
    if not nice(ans, 2):
        return None
    q = _paper_intro(ser) + f' Лист формата {ser}{k} имеет размеры {h} × {w} мм.\n' + pick(
        r, f'Листы формата {ser}{k} упакованы в пачки по {n} штук. Сколько граммов весит пачка, если квадратный метр такой бумаги весит {g} г?',
        f'Найдите массу пачки из {n} листов формата {ser}{k}, если плотность бумаги {g} г/м². Ответ дайте в граммах.')
    e = f'Площадь листа {h}·{w} мм² = {tnum(F(w * h, 10 ** 6))} м²; масса {tnum(F(w * h, 10 ** 6))}·{g}·{n} = {tnum(ans)} г.'
    return pcard(q, num(ans), e=e), lambda: same(num(ans), sp.Rational(w * h, 10 ** 6) * g * n)


@proto('og05-paper-font', 'oge', 5, 'Форматы бумаги: масштаб шрифта при смене формата',
       invariant='При переходе к соседнему формату все размеры меняются в одно и то же число раз (отношение сторон); размер шрифта масштабируется так же и округляется до целого.',
       varies='Серия, пара форматов (соседние или через один), исходный кегль.',
       answer_rule='Новый кегль = старый × (сторона нового листа / сторона старого), округлить до целого.',
       fipi=r'Какой высоты нужен шрифт',
       mistakes=['увеличивают кегль вдвое при соседнем формате', 'делят вместо умножения'],
       kim=KP(5, ['1.5', '3.3', '7.5'], [8, 10], 5))
def gen_og05_paper_font(r):
    ser = r.choice(SERIES)
    k = r.randint(1, len(PAPER[ser]) - 1)
    step = r.choice([1, 1, 2]) if k >= 2 else 1
    src, dst = (k, k - step) if r.random() < 0.6 else (k - step, k)
    f0 = r.randint(8, 30)
    ratio = F(PAPER[ser][dst][1], PAPER[ser][src][1])
    val = f0 * ratio
    if abs(val - math.floor(val) - F(1, 2)) < F(1, 20):
        return None
    ans = math.floor(val + F(1, 2))
    q = (_paper_intro(ser) + f' Размеры листов (мм): {ser}{src} — {PAPER[ser][src][1]} × {PAPER[ser][src][0]}, {ser}{dst} — {PAPER[ser][dst][1]} × {PAPER[ser][dst][0]}. '
         'Высоту шрифта измеряют в пунктах.\n'
         f'Текст напечатан на листе {ser}{src} шрифтом высотой {f0} пунктов. Каким должен быть шрифт (в пунктах), чтобы тот же текст разместился на листе {ser}{dst} '
         'точно так же, то есть все размеры изменились в одно и то же число раз? Размер шрифта округлите до целого.')
    e = f'Коэффициент подобия {PAPER[ser][dst][1]}/{PAPER[ser][src][1]}; {f0}·{approx(ratio, 3)} ≈ {approx(val, 2)} ≈ {ans}.'
    return pcard(q, num(ans), e=e), lambda: ans == round(sp.Rational(f0 * PAPER[ser][dst][1], PAPER[ser][src][1]))
