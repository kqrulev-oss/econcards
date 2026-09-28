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

from mathlib import (F, R, _svg, BLUE, RED, INK, GRID, finite, nice, num, par, pcard, pick, plural,
                     poly, proto, same, signed, sp, tnum, lin)

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
    """Показатель степени верхним индексом: sup(-3) → '⁻³' (только для разборов)."""
    return str(n).translate(SUP)


def xp(n):
    """Показатель степени в условии: разметка сайта ^{…} внутри ⟦ ⟧ → <sup>; xp(-3) → '^{−3}'."""
    return '^{' + tnum(n) + '}'


def parse(txt):
    """Выражение из текста условия → sympy (независимая проверка: считаем то, что видит ученик).
    Понимает −, ·, :, десятичную запятую, √(…) и √n, ², ³, ^{k}, смешанные числа «2 3/4»."""
    s = txt.replace('⟦', '').replace('⟧', '').replace('−', '-').replace('·', '*').replace(':', '/')
    s = re.sub(r'(\d),(\d)', r'\1.\2', s)
    s = re.sub(r'(?<![\d.])(\d+) (\d+)/(\d+)', r'(\1+\2/\3)', s)
    s = re.sub(r'(?<![\d./])(\d+)/(\d+)(?![\d.])', r'(\1/\2)', s)
    s = re.sub('([' + SUPS + ']+)⁄([₀₁₂₃₄₅₆₇₈₉]+)', lambda m: '(' + ''.join(UNSUP[c] for c in m.group(1)) + '/' + ''.join(str('₀₁₂₃₄₅₆₇₈₉'.index(c)) for c in m.group(2)) + ')', s)
    s = re.sub('[' + SUPS + '⁻]+', lambda m: '**(' + ''.join(UNSUP[c] for c in m.group(0)) + ')', s)
    s = re.sub(r'\^\{([^}]*)\}', r'**(\1)', s)
    s = re.sub(r'\^\(([^)]*)\)', r'**(\1)', s)
    s = re.sub(r'\^(-?\d+)', r'**(\1)', s)
    s = re.sub(r'√(\d+(?:\.\d+)?)', r'§(\1)', s)
    s = re.sub(r'√([a-z])', r'§(\1)', s)
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


ASK = ('Найдите значение выражения',)  # инструкция КИМ ОГЭ №6, №8
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
    q = f'{pick(r, *ASK)} ⟦{ex}⟧.'
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
    if not nice(val, 2) or val == 0:
        return None
    if r.random() < 0.5:
        a, b = b, a
        val = a + b if op == '+' else a - b
    ex = f'{fr(a)} {op} {fr(b)}'
    return _expr_card(r, ex, val, f'Общий знаменатель {max(a.denominator, b.denominator) if max(a.denominator, b.denominator) % min(a.denominator, b.denominator) == 0 else a.denominator * b.denominator // math.gcd(a.denominator, b.denominator)}: {ex} = {fr(val)} = {tnum(val)}.')


@proto('og06-frac-muldiv', 'oge', 6, 'Произведение или частное обыкновенных дробей',
       invariant='Одно действие: умножение или деление двух обыкновенных дробей (правильных или неправильных).',
       varies='Числители (до 20) и знаменатели (до 12), знак действия; без тривиального ответа 1.',
       answer_rule='Умножаем числители и знаменатели (при делении — на перевёрнутую дробь), сокращаем, переводим в десятичную.',
       fipi=r'значение выражения\s+\d+\s+\d+\s*[·⋅:]\s*\d+\s+\d+\s*\.',
       mistakes=['при делении не переворачивают делитель', 'делят числитель на числитель и знаменатель на знаменатель с ошибкой'], kim=K6)
def gen_og06_frac_muldiv(r):
    # масштаб банка: 7/6 · 9/5, 4/5 : 2/7, 15/4 · 6/5 — числители до 20, знаменатели до 12
    a = F(r.randint(1, 20), r.randint(2, 12))
    b = F(r.randint(1, 20), r.randint(2, 12))
    if a.denominator == 1 or b.denominator == 1:
        return None
    op = r.choice(['·', ':'])
    val = a * b if op == '·' else a / b
    if not nice(val, 2) or val == 1 or a * b == 1 or a == b or val.denominator == 1 and r.random() < 0.6:
        return None
    ex = f'{fr(a)} {op} {fr(b)}'
    return _expr_card(r, ex, val, f'{ex} = {fr(val)} = {tnum(val)}.')


@proto('og06-dec-addsub', 'oge', 6, 'Сумма или разность десятичных дробей',
       invariant='Одно действие с десятичными дробями (десятые): a ± b, ответ может быть отрицательным.',
       varies='Числа (одна цифра до запятой и одна после, как в банке), знак действия.',
       answer_rule='Записываем разряд под разрядом; если вычитаемое больше, результат отрицательный.',
       fipi=r'значение выражения\s+\d+,\d\s*[+−-]\s*\d+,\d\s*\.',
       mistakes=['ошибка в знаке при a < b', 'сдвиг разрядов'], kim=K6)
def gen_og06_dec_addsub(r):
    # масштаб банка: 8,4 + 3,7; 4,9 − 9,4 — одна цифра до запятой, одна после
    a = F(r.randint(11, 99), 10)
    b = F(r.randint(11, 99), 10)
    if a.denominator == 1 or b.denominator == 1:
        return None
    op = r.choice('+−')
    val = a + b if op == '+' else a - b
    if val == 0:
        return None
    ex = f'{tnum(a)} {op} {tnum(b)}'
    return _expr_card(r, ex, val, f'{ex} = {tnum(val)}.')


@proto('og06-dec-mul', 'oge', 6, 'Произведение десятичных дробей',
       invariant='Умножение двух десятичных дробей (десятые, сотые) «в столбик».',
       varies='Множители — десятичные дроби вида 8,9 и 4,3 (одна цифра до и после запятой).',
       answer_rule='Перемножаем как натуральные числа и отделяем столько знаков, сколько их у множителей вместе.',
       fipi=r'значение выражения\s+\d+,\d\s*[·⋅]\s*\d+,\d\s*\.',
       mistakes=['отделяют неверное число знаков после запятой'], kim=K6)
def gen_og06_dec_mul(r):
    # масштаб банка: 8,9 · 4,3; 6,7 · 5,5
    a = F(r.randint(11, 99), 10)
    b = F(r.randint(11, 99), 10)
    if a.denominator == 1 or b.denominator == 1:
        return None
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
    # масштаб банка: 9,6 / 1,6; 8,2 / 4,1 — десятые, частное целое или с одним знаком
    b = F(r.randint(11, 99), 10)
    val = F(r.randint(2, 9)) if r.random() < 0.75 else F(r.randint(11, 49), 10)
    a = b * val
    if b.denominator == 1 or not nice(a, 1) or a.denominator == 1 or a >= 100:
        return None
    ex = f'{tnum(a)} : {tnum(b)}'
    q = f'{pick(r, *ASK)} ⟦{tnum(a)} / {tnum(b)}⟧.'
    return pcard(q, num(val), e=f'{tnum(a)} : {tnum(b)} = {tnum(a * 10)} : {tnum(b * 10)} = {tnum(val)}.'), lambda: same(num(val), parse(ex))


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
       style='Вопрос КИМ ОГЭ №7 («Какая из точек … соответствует числу …?», «Между какими соседними целыми числами '
             'заключено число …?», «Какое из чисел принадлежит отрезку …?», «Какая из разностей … отрицательна?»), '
             'варианты 1)–4), в ответ — номер; дроби записаны как 55/19')
TAIL7 = ('',)  # варианты — кнопки 1)–4), отдельная приписка «укажите номер» не нужна
SUB = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')


def ufr(p, q):
    """Обыкновенная дробь в условии и вариантах: 55/19 (крупно и читаемо на телефоне; индексные
    глифы ⁵⁵⁄₁₉ мельчат и берутся из запасного шрифта)."""
    s = '−' if p * q < 0 else ''
    return f'{s}{abs(p)}/{abs(q)}'


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
    q = _q7(r, pick(r, f'Какое из чисел, приведённых ниже, отмечено на координатной прямой точкой {letter}?',
                    f'Какое из данных чисел изображено на координатной прямой точкой {letter}?'))
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
    q = _q7(r, pick(r, f'Какая из точек A, B, C, D, отмеченных на координатной прямой, соответствует числу {txt}?',
                    f'Какая из отмеченных на координатной прямой точек A, B, C, D изображает число {txt}?'))
    e = f'{txt} ≈ {approx(v)}: между {tnum(base)} и {tnum(base + 1)}, {"ближе к " + tnum(base + 1) if fracp > 0.5 else "ближе к " + tnum(base)} — это точка {names[right]}.'
    pos = [R(p) for p in pts]
    return pcard(q, a, e=e, k='one', o=o, svg=svg), lambda: min(range(4), key=lambda i: abs(sp.N(pos[i] - val))) == right


@proto('og07-decimals-points', 'oge', 7, 'Точки и десятичные дроби: какой точке соответствует число',
       invariant='Точки A, B, C, D на прямой соответствуют четырём близким десятичным числам (в разном порядке); по порядку чисел найти точку для заданного числа.',
       varies='Две цифры и четыре записи из них (0,xy; 0,0xy; 0,x0y; 0,yx …), знаки, спрашиваемое число.',
       answer_rule='Упорядочиваем числа по возрастанию: самое левое число — самая левая точка и т. д.',
       fipi=r'соответствуют числам',
       mistakes=['считают 0,098 больше 0,11 из-за «большего числа цифр»', 'путают порядок отрицательных'],
       svg=True, card_kind='one', kim=K7)
def gen_og07_decimals_points(r):
    # как в банке: четыре числа из одних и тех же цифр с разным положением нуля и знаком
    # (0,098; −0,02; 0,09; 0,11 или −0,205; −0,052; 0,02; 0,008) — ловушка «длинное число больше»
    d1, d2 = r.sample(range(1, 10), 2)
    forms = [f'{d1}{d2}', f'0{d1}{d2}', f'{d1}0{d2}', f'{d2}{d1}', f'0{d2}{d1}', f'{d2}0{d1}', f'{d1}', f'0{d1}', f'00{d1}{d2}']
    picked = r.sample(forms, 4)
    neg = r.choice([0, 0, 1, 1, 2])
    signs = [-1] * neg + [1] * (4 - neg)
    r.shuffle(signs)
    nums_ = [sg * F(int(t), 10 ** len(t)) for sg, t in zip(signs, picked)]
    if len(set(nums_)) < 4:
        return None
    listed = nums_[:]
    nums = sorted(nums_)
    if min(b - a for a, b in zip(nums, nums[1:])) <= 0:
        return None
    names = 'ABCD'
    xs = [F(i * 3 + r.randint(0, 1), 1) for i in range(4)]  # позиции точек слева направо
    target = r.choice(listed)
    right = nums.index(target)
    svg = svg_numline(-1, 12, ticks=(), labels=(), points=[(xs[i], names[i]) for i in range(4)])
    o, a = fixed_opts([f'точка {c}' for c in names], right)
    lst = '; '.join(tnum(x) for x in listed)
    q = _q7(r, f'Точки A, B, C и D на координатной прямой соответствуют числам {lst}. Какая из точек соответствует числу {tnum(target)}?')
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
        q = _q7(r, f'Между какими соседними целыми числами заключено число √{nn}?')
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
    q = _q7(r, pick(r, f'Какое из чисел принадлежит отрезку [{k}; {k + 1}]?', f'Какое из чисел принадлежит промежутку [{k}; {k + 1}]?'))
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
        d = r.choice([6, 12, 14, 15, 17, 19, 21, 23])  # в банке здесь 7, 9, 11, 13 — берём другие знаменатели
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
        q = _q7(r, f'Какому из данных промежутков принадлежит число {ufr(m, d)}?')
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
        q = _q7(r, f'Какое из чисел принадлежит отрезку [{k}; {k + 1}]?')
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
    q = _q7(r, f'Между какими соседними целыми числами заключено число {ufr(m, d)}?')
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
    q = _q7(r, f'Какое из чисел заключено между {ufr(p1, d1)} и {ufr(p2, d2)}?')
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
    q = _q7(r, f'Число {v} отмечено на координатной прямой. Какое из приведённых неравенств для него {word}?')
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
    q = _q7(r, f'Числа {na} и {nb} отмечены на координатной прямой. Какое из приведённых утверждений {word}?')
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
    q = _q7(r, f'Числа {names[0]}, {names[1]} и {names[2]} отмечены на координатной прямой. Какая из приведённых разностей {word}?')
    x, y = g
    e = f'На рисунке {x} {"левее" if want_neg else "правее"} {y}, поэтому {x} − {y} {"< 0" if want_neg else "> 0"}.'
    return pcard(q, a, e=e, k='one', o=o, svg=svg), lambda: sum(bool((R(val[p]) - R(val[s]) < 0) == want_neg) for p, s in ch) == 1 and \
        bool((R(val[x]) - R(val[y]) < 0) == want_neg)


# ================================================================ №8 — степени, корни, преобразования

K8 = K(minutes=3, kes=['2.2', '2.5', '1.4'], kt=[4], style='«Найдите значение выражения …» (инструкция КИМ), степени — верхним индексом через разметку ^{…}; ответ — число')
K8a = K(minutes=4, kes=['2.1', '2.3', '2.5'], kt=[4], style='«Найдите значение выражения … при a = …»: сначала упростить, затем подставить')


def _pw(b, e):
    b = f'({tnum(b)})' if F(b) < 0 else (f'({fr(b)})' if F(b).denominator > 1 else tnum(b))
    return f'{b}{sup(e)}'


def caret(s):
    """Показатели-индексы → разметка ^{…} (внутри ⟦ ⟧ сайт рисует настоящий верхний индекс
    основным шрифтом формулы; глифы ⁴–⁹ в Nunito отсутствуют и берутся из запасного шрифта)."""
    return re.sub('[' + SUPS + '⁻]+', lambda m: '^{' + ''.join(UNSUP[c] for c in m.group(0)).replace('-', '−') + '}', s)


def _f8(r, ex, val, e):
    q = f'{pick(r, *ASK)} ⟦{caret(ex)}⟧.'
    return pcard(q, num(val), e=e), lambda: same(num(val), parse(ex))


@proto('og08-pow-base', 'oge', 8, 'Степени с одинаковым числовым основанием',
       invariant='Числовое выражение из степеней одного основания (целые показатели, в т. ч. отрицательные): умножение, деление, степень степени.',
       varies='Основание (в т. ч. дробь 1/2, 1/3), показатели (в основном двузначные, как 2^{−11} и 2^{26} в банке), запись частного через «:» или дробью.',
       answer_rule='Складываем/вычитаем/умножаем показатели, затем вычисляем одну небольшую степень.',
       fipi=r'значение выражения\s+\(?\s*(\d+)\s*[−-]?\s*\d+\s*\)?\s*[−-]?\s*\d*\s*[·⋅]?\s*\(?\s*\1\s+[−-]?\s*\d+|значение выражения\s+\d\s+\d+\s+\d+\s*\.$',
       mistakes=['перемножают показатели вместо сложения', 'ошибка со знаком отрицательного показателя'], maxdec=4, kim=K8)
def gen_og08_pow_base(r):
    b = r.choice([2, 2, 3, 3, 5, 6, 7, 9, 10, F(1, 2), F(1, 3)])
    target = r.choice([-3, -2, -1, 1, 2, 3, 4]) if b in (2, 3) else r.choice([-2, -1, 1, 2])
    if isinstance(b, F) and target < 0:
        target = -target
    kind = r.randrange(4)
    if kind == 0:
        m = r.choice([x for x in range(-19, 20) if abs(x) > 7])
        n = r.choice([x for x in range(-19, 20) if abs(x) > 7])
        k = m + n - target
        if k in (0, 1, -1) or abs(k) > 30 or m + n == 0:
            return None
        ex = pick(r, f'{_pw(b, m)} · {_pw(b, n)} : {_pw(b, k)}', f'({_pw(b, m)} · {_pw(b, n)}) / {_pw(b, k)}')
        e = f'Показатель: {tnum(m)} + {par(n)} − {par(k)} = {tnum(target)}.'
    elif kind == 1:
        m, n = r.choice([-15, -14, -13, -12, 12, 13, 14, 15]), r.choice([-3, -2, 2, 3])
        k = target - m * n
        if k in (0, 1, -1) or abs(k) > 48:
            return None
        ex = f'({_pw(b, m)}){sup(n)} · {_pw(b, k)}'
        e = f'Показатель: {tnum(m)}·{par(n)} + {par(k)} = {tnum(target)}.'
    elif kind == 2:
        m, n = r.choice([-15, -14, -13, -12, 12, 13, 14, 15]), r.choice([-3, -2, 2, 3])
        k = m * n - target
        if k in (0, 1, -1) or abs(k) > 48:
            return None
        ex = pick(r, f'({_pw(b, m)}){sup(n)} : {_pw(b, k)}', f'({_pw(b, m)}){sup(n)} / {_pw(b, k)}')
        e = f'Показатель: {tnum(m)}·{par(n)} − {par(k)} = {tnum(target)}.'
    else:  # степень, делённая на число — тоже степень того же основания
        if not isinstance(b, int) or b == 10:
            return None
        k = r.randint(2, 5)
        m = target + k
        N = b ** k
        if N > 1000 or m < 3:
            return None
        ex = pick(r, f'{_pw(b, m)} / {N}', f'{_pw(b, m)} : {N}')
        e = f'{N} = {_pw(b, k)}; показатель {m} − {k} = {tnum(target)}.'
    val = F(b) ** target
    if not nice(val, 4):
        return None
    return _f8(r, ex, val, e + f' {_pw(b, target)} = {tnum(val)}.')


@proto('og08-pow-var', 'oge', 8, 'Степени с буквой: упростить и подставить',
       invariant='Выражение с буквой из степеней одного основания; упростить по свойствам степени и подставить значение.',
       varies='Буква, показатели (в т. ч. отрицательные), вид (произведение, частное, степень степени), значение переменной (натуральное 2–7, как в банке).',
       answer_rule='Приводим к виду aᵏ и подставляем число.',
       fipi=r'при\s+[a-zх]\s*=\s*[−-]?\s*\d+\s*\.?\s*$',
       mistakes=['подставляют до упрощения и ошибаются в вычислениях', 'путают степень степени и произведение'], maxdec=4, kim=K8)
def gen_og08_pow_var(r):
    v = r.choice(['b', 'c', 'x', 'y', 'm', 'p'])  # в банке почти всегда a — берём другие буквы
    target = r.choice([2, 2, 3, 3, 4, 1])
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
    val_x = r.choice([2, 3, 4, 5, 6, 7])  # масштаб банка: при a = 2 … 7, ответ — небольшая степень
    val = F(val_x) ** target
    if not nice(val, 3) or abs(val) > 1000:
        return None
    q = f'{pick(r, *ASK)} ⟦{caret(ex)}⟧ при {v} = {fr(val_x)}.'
    e = f'Упрощаем: {v}{sup(target) if target != 1 else ""}; при {v} = {fr(val_x)} получаем {tnum(val)}.'
    sym = sp.Symbol(v)
    return pcard(q, num(val), e=e), lambda: same(num(val), parse(ex).subs(sym, R(val_x)))


@proto('og08-pow-mixed', 'oge', 8, 'Степени с разными основаниями',
       invariant='Произведение степеней разных оснований и степень их произведения: (ab)ⁿ = aⁿbⁿ; сокращаем одинаковые степени.',
       varies='Основания (18 = 2·9, 33 = 3·11, 36 = 4·9 …), показатели, место составного основания.',
       answer_rule='Раскладываем составное основание на множители и сокращаем.',
       fipi=r'значение выражения\s+(\(\s*\d+\s*⋅\s*\d+\s*\)\s*\d+\s+\d+\s+\d+\s*⋅\s*\d+\s+\d+|\d+\s+\d+\s*⋅\s*\d+\s+\d+\s+\d+\s+\d+|\d+\s+\d+\s+\d+\s+\d+\s*⋅\s*\d+\s+\d+)\s*\.',
       mistakes=['перемножают основания и складывают показатели одновременно'], maxdec=4, kim=K8)
def gen_og08_pow_mixed(r):
    # пары оснований того же масштаба, что в банке (6, 15, 21, 30, 44 …), но не совпадающие с ним
    a, b = r.choice([(2, 9), (3, 11), (2, 13), (4, 9), (5, 11), (7, 8), (3, 13), (6, 7), (8, 9), (7, 11)])
    if r.random() < 0.5:
        a, b = b, a
    ab = a * b
    n = r.randint(7, 14)
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
       varies='Показатели, значения букв (a — натуральное, b = √n; как в банке, b часто сокращается полностью).',
       answer_rule='Собираем показатели при a и при b, затем подставляем; (√k)² = k.',
       fipi=r'\(\s*[a-z]\s*[·⋅]\s*[a-z]\s*\).{0,40}при\s+[a-z]\s*=.{0,20}и\s+[a-z]\s*=',
       mistakes=['забывают возвести в степень второй множитель', 'ошибка с (√2)⁴'], kim=K8)
def gen_og08_pow_two_vars(r):
    va, vb = r.choice([('x', 'y'), ('m', 'n'), ('p', 'q'), ('c', 'd')])
    s_ = r.randint(9, 25)
    ea, eb = r.choice([1, 2, 2, 3]), r.choice([0, 0, 2])  # как в банке: b = √n часто сокращается полностью
    q_ = r.choice([2, 3, 4, 5])
    if (s_ + eb) % q_:
        return None
    rr = (s_ + eb) // q_
    p = s_ + ea
    A = r.choice([2, 3, 4, 5, 6, 7])
    B = r.choice([2, 3, 5, 6, 7])
    val = F(A) ** ea * F(B) ** (eb // 2)
    ex = f'{va}{sup(p)} · ({vb}{sup(q_)}){sup(rr)} / ({va}{vb}){sup(s_)}'
    if abs(val) > 1000:
        return None
    q = f'{pick(r, *ASK)} ⟦{caret(ex)}⟧ при {va} = {tnum(A)} и {vb} = √{B}.'
    e = (f'Упрощаем: {va}{sup(ea) if ea > 1 else ""}' + (f'·{vb}{sup(eb)}' if eb else '') + f'; подставляем: {tnum(val)}.')
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
        c1, c2 = r.randint(2, 7), r.randint(2, 7)
        a, b = r.sample([2, 3, 5, 7, 11, 13, 17], 2)
        e_ = a * b * r.choice([4, 9])
        val = c1 * c2 * math.isqrt(a * b * e_)
        if math.isqrt(a * b * e_) ** 2 != a * b * e_:
            return None
        ex = f'{c1}√{a} · {c2}√{b} · √{e_}'
        e = f'{c1}·{c2}·√({a}·{b}·{e_}) = {c1 * c2}·{math.isqrt(a * b * e_)} = {val}.'
        if val > 1500:
            return None
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
        if val > 1000:
            return None
        ex = f'√({p}{sup(m)} · {q_}{sup(n)})'
        e = f'√({p}{sup(m)}·{q_}{sup(n)}) = {p}{sup(m // 2)}·{q_}{sup(n // 2)} = {val}.'
    else:
        p, m = r.choice([2, 3, 5, 7, 11, 13]), r.choice([4, 6, 8, 10])
        val = p ** (m // 2)
        if val > 1000:
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
    if k * k * a > 300:
        return None
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
    b = r.randint(2, 9)
    sgn = r.choice('+−')
    if r.random() < 0.5:  # (b ± √a)² ∓ 2b√a
        a = r.choice([x for x in range(2, 60) if math.isqrt(x) ** 2 != x])
        ex = f'({b} {sgn} √{a})² {"−" if sgn == "+" else "+"} {2 * b}√{a}'
    else:  # (√a ± b)² ∓ 2b√a
        a = r.choice([x for x in range(20, 60) if math.isqrt(x) ** 2 != x])
        ex = f'(√{a} {sgn} {b})² {"−" if sgn == "+" else "+"} {2 * b}√{a}'
    val = a + b * b
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
    a = r.randint(4, 9)
    b = r.choice([x for x in range(11, a * a + 30) if math.isqrt(x) ** 2 != x and x != a * a])
    c = r.choice([x for x in (2, 3, 4, 5, 6) if x != a])
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
    va, vb = r.choice([('x', 'y'), ('m', 'n'), ('p', 'q'), ('c', 'd')])
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
    show = lambda x: (('−' if x < 0 else '') + mixed(abs(x))) if abs(x) > 1 and x.denominator > 1 else fr(x)
    ex = f'√({inner})'
    q = f'{pick(r, *ASK)} ⟦{caret(ex)}⟧ при {va} = {show(av)} и {vb} = {show(bv)}.'
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
        if not nice(val, 2) or val > 500:
            return None
        cs = fr(c) if c.denominator == 1 else f'{fr(c)} ·'
        ex = f'√({cs}{vx}{sup(m)}{vy}{sup(n)})' if c.denominator == 1 else f'√({fr(c)} · {vx}{sup(m)}{vy}{sup(n)})'
        q = f'{pick(r, *ASK)} ⟦{caret(ex)}⟧ при {vx} = {X0} и {vy} = {Y0}.'
        S = {sp.Symbol(vx): X0, sp.Symbol(vy): Y0}
        e = f'√({fr(c)}·{vx}{sup(m)}{vy}{sup(n)}) = {fr(F(math.isqrt(c.numerator), math.isqrt(c.denominator)))}·{vx}{sup(m // 2)}·{vy}{sup(n // 2)} = {tnum(val)}.'.replace('¹', '')
    else:
        v = r.choice(['b', 'c', 'm', 'p', 'y'])
        p_, q2 = r.choice([2, 4, 6, 8, 10]), r.choice([2, 4, 6])
        if p_ + q2 < 8:
            return None
        A = r.choice([2, 3, -2, -3, 5])
        val = abs(A) ** ((p_ + q2) // 2)
        if val > 5000:
            return None
        ex = pick(r, f'√({v}{sup(p_)} · (−{v}){sup(q2)})', f'√((−{v}){sup(q2)} · {v}{sup(p_)})')
        q = f'{pick(r, *ASK)} ⟦{caret(ex)}⟧ при {v} = {tnum(A)}.'
        S = {sp.Symbol(v): A}
        e = f'(−{v}){sup(q2)} = {v}{sup(q2)}, поэтому корень равен |{v}{sup((p_ + q2) // 2)}| = {val}.'
    return pcard(q, num(val), e=e), lambda: same(num(val), sp.simplify(parse(ex).subs(S)))


# ================================================================ №9 — уравнения

K9 = K(minutes=3, kes=['3.1'], kt=[5], style='Инструкции КИМ: «Найдите корень уравнения …» (линейное); «Решите уравнение … Если уравнение '
       'имеет более одного корня, в ответе запишите меньший (больший) из корней» (квадратное)')
TWO = 'Если уравнение имеет более одного корня, в ответе запишите {w} из корней.'


def _roots_card(r, eq_txt, roots, e, lhs, rhs):
    roots = sorted(set(roots))
    if not any(nice(x, 2) for x in roots):
        return None
    if len(roots) > 1:
        which = r.choice([w for w, x in (('min', roots[0]), ('max', roots[-1])) if nice(x, 2)])
        ans = roots[0] if which == 'min' else roots[-1]
        q = f'Решите уравнение ⟦{eq_txt}⟧. ' + TWO.format(w='меньший' if which == 'min' else 'больший')
    else:
        which, ans = None, roots[0]
        q = pick(r, f'Найдите корень уравнения ⟦{eq_txt}⟧.', f'Решите уравнение ⟦{eq_txt}⟧.')

    def chk():
        sol = sorted(s_ for s_ in sp.solve(sp.Eq(parse(lhs), parse(rhs)), sp.Symbol('x')) if s_.is_real)
        if len(sol) != len(roots):
            return False
        want = sol[0] if which != 'max' else sol[-1]
        return same(num(ans), want)
    return pcard(q, num(ans), e=e), chk


@proto('og09-lin', 'oge', 9, 'Линейное уравнение',
       invariant='ax + b = cx + d: переносим члены с x в одну сторону, числа — в другую.',
       varies='Коэффициенты (до 12, в т. ч. отрицательные), свободные числа (одно из них двузначное, до 20), расположение x.',
       answer_rule='x = (d − b)/(a − c); ответ — целое или конечная десятичная дробь.',
       fipi=r'Найдите корень уравнения\s+(?![^=]*x\s+2\b)[^()]*x[^()]*=[^()]*\.\s*$',
       mistakes=['не меняют знак при переносе', 'делят не на тот коэффициент'], kim=K9)
def gen_og09_lin(r):
    # банк: −5 + 2x = −2x − 3, 8 + 7x = 9x + 4, −4x − 9 = 6x. Однозначные числа банк покрывает почти
    # целиком, поэтому одно из свободных чисел берём двузначным (до 20) — уровень тот же, но это не копия
    a, c = r.randint(-12, 12), r.randint(-12, 12)
    b, d = r.randint(-20, 20), r.randint(-20, 20)
    if a == c or a == 0 or max(abs(b), abs(d)) < 11 or abs(a) < 2 or c in (1, -1):
        return None
    form = r.randrange(3)
    if form == 1:
        d = 0  # «−4x − 9 = 6x»
        if abs(b) < 11:
            return None
    x0 = F(d - b, a - c)
    if not nice(x0, 2) or (b == 0 and d == 0):
        return None
    side = lambda k, m: (f'{tnum(m)}{signed(k)}x'.replace(' 1x', ' x') if m and form == 0 else (lin(k, m) if m else lin(k, 0))).replace('−1x', '−x')
    lhs = side(a, b) if b else lin(a, 0)
    rhs = side(c, d) if c else tnum(d)
    return _roots_card(r, f'{lhs} = {rhs}', [x0], (f'{lin(a - c, 0)} = {tnum(d - b)}, ' if a - c != 1 else '') + f'x = {tnum(x0)}.', lhs, rhs)


@proto('og09-lin-brackets', 'oge', 9, 'Линейное уравнение со скобками',
       invariant='k(x ± b) = e (как в банке: 4(x − 6) = 5): раскрываем скобку или делим обе части на k.',
       varies='Множитель перед скобкой (2–10), число в скобке, правая часть; корень — целый или десятичная дробь.',
       answer_rule='Раскрываем скобки (с учётом минуса), приводим подобные и решаем.',
       fipi=r'\d\s*\(\s*x\s*[+−-]\s*\d+\s*\)\s*[+−=-]\s*\d*\s*\(?\s*x?|^Решите уравнение\s*$',
       mistakes=['не умножают второе слагаемое в скобке', 'ошибаются со знаком при переносе'], kim=K9)
def gen_og09_lin_brackets(r):
    # масштаб банка: 4(x − 6) = 5, 10(x + 2) = −7, 4(x + 10) = −1
    a, c = r.randint(2, 10), r.randint(2, 9)
    b, d = r.randint(1, 10) * r.choice([1, -1]), r.randint(1, 10) * r.choice([1, -1])
    sg = r.choice([1, -1])
    e_ = r.randint(-10, 10)
    ins = lambda k: f'x {"+" if k > 0 else "−"} {abs(k)}'
    kind = 0  # в банке только одна скобка: 4(x − 6) = 5; две скобки — уже уровень выше
    if kind == 0:
        e_ = r.choice([1, -1]) * r.randint(11, 40)  # короткие записи вида 2(x + 1) = 6 встречаются в банках дословно
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
    if not nice(x0, 2) or abs(x0) > 30:
        return None
    return _roots_card(r, f'{lhs} = {rhs}', [x0], f'Раскрываем скобки: {lin(A, B)} = 0, x = {tnum(x0)}.', lhs, rhs)


@proto('og09-quad', 'oge', 9, 'Полное квадратное уравнение',
       invariant='ax² + bx + c = 0 с двумя корнями (рациональными); в ответ — больший или меньший корень.',
       varies='Приведённое уравнение с целыми корнями или неприведённое (a = 2, 3, коэффициенты до 25) с дробным корнем; «больший/меньший».',
       answer_rule='Дискриминант или теорема Виета; выбираем нужный корень.',
       fipi=r'x\s*2\s*[+−-]\s*\d*\s*x\s*[+−-]\s*\d+\s*=\s*0',
       mistakes=['ошибка в знаке −b', 'делят только на a, а не на 2a', 'записывают не тот корень'], kim=K9)
def gen_og09_quad(r):
    # в банке: x² + 4x − 12 = 0, x² − 11x + 30 = 0, 2x² − 3x + 1 = 0 — приведённые с целыми корнями
    # и неприведённые с дробным корнем
    a = r.choice([1, 1, 1, 2, 2, 3])
    if a == 1:  # приведённые с небольшими корнями банк перебирает почти все — берём один корень двузначным
        p1, p2 = F(r.choice([x for x in range(-15, 16) if abs(x) > 10])), F(r.randint(-9, 9))
        if p2 == 0:
            return None
    else:  # 2x² − 3x + 1 = 0: небольшие коэффициенты, один корень дробный
        p1, p2 = F(r.choice([x for x in range(-7, 8) if x % a]), a), F(r.randint(-6, 6))
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
    # масштаб банка: 9x² = 54x, x² = 5x, x² − 49 = 0, x² − 144 = 0 — целые корни
    a = r.choice([1, 2, 3, 4, 5, 6, 7, 8, 9])
    if r.random() < 0.5:
        root = F(r.randint(1, 10)) * r.choice([1, -1])
        b = -a * root
        if F(b).denominator != 1:
            return None
        if r.random() < 0.5:
            txt, lhs, rhs = f'{poly([a, b, 0])} = 0', poly([a, b, 0]), '0'
        else:  # в банке ax² = bx только с положительным корнем — берём отрицательный
            if root > 0:
                root, b = -root, -b
            txt, lhs, rhs = f'{poly([a, 0, 0])} = {lin(-b, 0)}', poly([a, 0, 0]), lin(-b, 0)
        return _roots_card(r, txt, [F(0), root], f'x({lin(a, b)}) = 0: x = 0 или x = {tnum(root)}.', lhs, rhs)
    a = r.choice([1, 2, 2, 3, 4, 5])  # в банке x² − 16 = 0 … x² − 144 = 0 — чаще берём a > 1
    root = F(r.randint(13, 15)) if a == 1 else F(r.randint(2, 9))
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
     'Найдите вероятность того, что {name2} выпадет карточка с хорошо знакомым материалом.'),
]
BOYS = [('Тимур', 'Тимуру'), ('Глеб', 'Глебу'), ('Арсений', 'Арсению'), ('Родион', 'Родиону'), ('Ярослав', 'Ярославу'), ('Мирон', 'Мирону')]
GIFTS = [
    ('Для {N} {n1} летнего лагеря купили {N} настольных игр: {k} — стратегии, остальные — головоломки. Игры раздают случайным образом, одну каждому; среди участников есть {name}.',
     ('участник', 'участников', 'участников'), 'Найдите вероятность того, что {name2} достанется {what}.', ('стратегия', 'головоломка')),
    ('Школа подготовила {N} подарочных наборов для {N} {n1}: в {k} наборах — книги, в остальных — конструкторы. Наборы распределяются случайно; среди победителей есть {name}.',
     ('победитель олимпиады', 'победителей олимпиады', 'победителей олимпиады'), 'Найдите вероятность того, что {name2} достанется набор, в котором {what}.', ('книга', 'конструктор')),
]
THREE = [
    ('На стоянке каршеринга свободно {N} автомобилей: белых — {a}, серых — {b}, красных — {c}. Приложение назначает клиенту случайный свободный автомобиль.',
     'Найдите вероятность того, что клиенту достанется {w} автомобиль.', ('белый', 'серый', 'красный')),
    ('В вольере приюта {N} щенков: рыжих — {a}, чёрных — {b}, пятнистых — {c}. Волонтёр наугад берёт одного щенка на прогулку.',
     'Найдите вероятность того, что на прогулку пойдёт {w} щенок.', ('рыжий', 'чёрный', 'пятнистый')),
    ('В сувенирной лавке на полке стоят {N} кружек: синих — {a}, зелёных — {b}, белых — {c}. Покупатель, не выбирая, берёт одну.',
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
        k = r.randint(2, N - 2)
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
    if not nice(p, 3):
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


EVENTS = {  # как событие названо в вопросе «Найдите вероятность события …»
    'AB': ('A ∩ B', lambda a, b: a and b, ''),
    'A|B': ('A ∪ B', lambda a, b: a or b, ''),
    'A': ('A', lambda a, b: a, ''),
    'B': ('B', lambda a, b: b, ''),
    'notA': (', противоположного событию A', lambda a, b: not a, ''),
    'A-B': ('«наступило A, но не наступило B»', lambda a, b: a and not b, ''),
    'none': ('«не наступило ни A, ни B»', lambda a, b: not a and not b, ''),
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
    q = pick(r, f'В случайном эксперименте все элементарные исходы равновозможны; они показаны точками на диаграмме Эйлера, круги изображают события A и B. Найдите вероятность события{"" if name.startswith(",") else " "}{name}.',
             f'На диаграмме Эйлера изображены события A и B некоторого случайного опыта, а точками — все его равновозможные элементарные исходы. Найдите вероятность события{"" if name.startswith(",") else " "}{name}.')
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
    q = pick(r, f'Монету подбросили {n} {plural(n, "раз", "раза", "раз")}; орёл при этом выпал {k} {plural(k, "раз", "раза", "раз")}. Найдите вероятность того, что {mw} бросок закончился {si}.',
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
    vb = plural(k, 'благоприятствует', 'благоприятствуют', 'благоприятствуют')
    q = pick(r, f'Некоторый опыт имеет {n} равновозможных элементарных исходов, и {k} из них {vb} событию A. Найдите вероятность {ev}.',
             f'В случайном эксперименте всего {n} равновозможных исходов; событию A {vb} {k} из них. Найдите вероятность {ev}.')
    e = f'P = {(n - k) if comp else k}/{n} = {tnum(p)}.'
    return pcard(q, num(p), e=e), lambda: same(num(p), (1 - sp.Rational(k, n)) if comp else sp.Rational(k, n))


# ================================================================ №11 — графики функций: соответствие

K11 = K(minutes=3, kes=['5.1', '6.2'], kt=[6], answer='соответствие',
        style='«Установите соответствие между …» (инструкция КИМ ОГЭ №11), А–В ↔ 1–3, ответ — цифры под буквами; '
              'дробный коэффициент записан как x/2, 2x/3')
TAIL11 = ('',)


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
    if k == 0:
        return f'y = {tnum(b)}'
    if k.denominator > 1:  # y = x/2, y = −2x/3: без двусмысленного «1/2x»
        num_ = abs(k.numerator)
        s_ = f'y = {"−" if k < 0 else ""}{"" if num_ == 1 else num_}x/{k.denominator}'
        return s_ + (signed(b) if b else '')
    kt = '' if k == 1 else ('−' if k == -1 else tnum(k))
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
    fns = []
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
    q = 'Даны графики трёх функций вида y = kx + b. Установите соответствие между знаками коэффициентов k, b и номерами графиков.'
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
    q = 'Даны графики трёх функций вида y = ax² + bx + c. Установите соответствие между знаками коэффициентов a, c и номерами графиков.'
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
       fipi=r'ФОРМУЛЫ 1\) y = [−-]?\s*\d+\s+2\) y = x|(между графиками функций и формулами, которые их задают|между функциями и их графиками)\.?\s*(ФОРМУЛЫ|ФУНКЦИИ|ГРАФИКИ)?.{0,40}(y = [−-]?\s*\d*\s*\d*\s*x\s*([+−-]\s*\d+\s*)?(Б|В|2|3)\)).{0,60}y = [−-]?\s*\d*\s*\d*\s*x\s*([+−-]\s*\d+\s*)?(В|3)?\)?\s*y? ?=? ?[−-]?\s*\d*\s*\d*\s*x\s*([+−-]\s*\d+)?\s*(ГРАФИКИ|В таблице)',
       mistakes=['путают знак углового коэффициента', 'смотрят на пересечение с осью x вместо y'],
       svg=True, card_kind='match', kim=K11)
def gen_og11_lin_formulas(r):
    k0 = r.choice([F(1), F(2), F(3), F(1, 2), F(1, 3), F(3, 2), F(2, 3), F(1, 5), F(2, 5)])
    if r.random() < 0.2:  # y = c, y = x + c, y = cx
        c0 = r.choice([2, 3, 4, -2, -3, -4])
        combos = [(0, c0), (1, c0), (c0, 0), (-1, c0)]
    elif r.random() < 0.25:  # прямые пропорциональности: y = kx, y = −kx, y = x/k
        k1 = k0 if k0 >= 1 else 1 / k0
        if k1 == 1:
            return None
        combos = [(k1, 0), (-k1, 0), (1 / k1, 0), (-1 / k1, 0)]
    else:
        b0 = r.randint(1, 3)
        combos = [(k0, b0), (k0, -b0), (-k0, b0), (-k0, -b0)]
    three = r.sample(combos, 3)
    perm = list(range(3))
    r.shuffle(perm)
    to_graphs = r.random() < 0.5
    if to_graphs:  # формулы А–В → графики 1–3
        graphs = [None] * 3
        for i, j in enumerate(perm):
            graphs[j] = three[i]
        svg = svg_panels([_lin_f(k, b) for k, b in graphs], ['1', '2', '3'])
        left_txt = [_lin_txt(k, b) for k, b in three]
        right_txt = ['график 1', 'график 2', 'график 3']
        q = 'Установите соответствие между функциями, заданными формулами, и их графиками.'
        pairs = lambda a: [(left_txt[i], graphs[int(a[LET[i]]) - 1]) for i in range(3)]
    else:  # графики А–В → формулы 1–3
        formulas = [None] * 3
        for i, j in enumerate(perm):
            formulas[j] = three[i]
        svg = svg_panels([_lin_f(k, b) for k, b in three], ['А', 'Б', 'В'])
        left_txt = ['график А', 'график Б', 'график В']
        right_txt = [_lin_txt(k, b) for k, b in formulas]
        q = 'Установите соответствие между графиками и формулами функций.'
        pairs = lambda a: [(right_txt[int(a[LET[i]]) - 1], three[i]) for i in range(3)]
    left, right, a = _match(r, left_txt, right_txt, perm, '')
    e = '; '.join(f'{LET[i]} → {perm[i] + 1}' for i in range(3)) + '.'

    def chk():  # формула из текста должна проходить через две точки нарисованной прямой
        X_ = sp.Symbol('x')
        for txt, (k, b) in pairs(a):
            f = parse(txt.split('=')[1])
            for x0 in (0, 3):
                if sp.simplify(f.subs(X_, x0) - (R(k) * x0 + b)) != 0:
                    return False
        return True
    return pcard(q, a, e=e, k='match', o={'left': left, 'right': right}, svg=svg), chk


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
    if r.random() < 0.3:
        v2 = r.choice([0, 0, 1, -1, 2])
        sg = r.choice([1, 1, -1])
        hyp = (f'y = {"−" if sg < 0 else ""}√x' + (signed(v2) if v2 else ''), lambda x, v2=v2, sg=sg: sg * math.sqrt(x) + v2, 'ветвь параболы (корень)')
    return [lin_, par_, hyp]


@proto('og11-mixed', 'oge', 11, 'Прямая, парабола, гипербола: формулы и графики',
       invariant='Три функции разных видов (линейная, квадратичная, обратная пропорциональность); сопоставить формулы и графики.',
       varies='Коэффициенты, направление соответствия (формулы → графики или графики → формулы), порядок.',
       answer_rule='Вид графика определяется видом формулы: kx + b — прямая, ax² + … — парабола, k/x — гипербола.',
       fipi=r'(между функциями и их графиками|между графиками функций и формулами).{0,80}(x 2|1 x|√)',
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
        q = 'Установите соответствие между функциями, заданными формулами, и их графиками.'
        want = [graphs[perm[i]] for i in range(3)]
        got = lambda a: [graphs[int(a[LET[i]]) - 1] for i in range(3)]
    else:  # графики А–В → формулы 1–3
        formulas = [None] * 3
        for i, j in enumerate(perm):
            formulas[j] = items[i]
        svg = svg_panels([it[1] for it in items], ['А', 'Б', 'В'])
        left_txt = ['график А', 'график Б', 'график В']
        right_txt = [f[0] for f in formulas]
        q = 'Установите соответствие между графиками и формулами функций.'
        want = items
        got = lambda a: [formulas[int(a[LET[i]]) - 1] for i in range(3)]
    left, right, a = _match(r, left_txt, right_txt, perm, '')
    e = '; '.join(f'{it[0]} — {it[2]}' for it in items) + '.'

    def chk():  # формула из текста, выбранная для графика, совпадает с нарисованной функцией в нескольких точках
        g = got(a)
        X_ = sp.Symbol('x')
        for i in range(3):
            f = parse(g[i][0].split('=')[1])
            for x0 in (1, 2, 4):
                if abs(float(f.subs(X_, x0)) - want[i][1](x0)) > 1e-9:
                    return False
        return True
    return pcard(q, a, e=e, k='match', o={'left': left, 'right': right}, svg=svg), chk


# ================================================================ №12 — расчёты по формулам

K12 = K(minutes=3, kes=['2.1', '2.2'], kt=[4], style='Формула с пояснением величин; инструкции КИМ «Пользуясь этой формулой, найдите …», «Ответ дайте в …»')
FIND = ('Пользуясь этой формулой, найдите',)


def _f12(r, head, ask, ans, e, chk, unit=''):
    q = f'{head} {pick(r, *FIND)} {ask}' + (f' Ответ дайте {unit}.' if unit else '')
    return pcard(q, num(ans), e=e), chk


@proto('og12-linear-calc', 'oge', 12, 'Подстановка в линейную формулу',
       invariant='Формула вида y = a + b·x или y = k(x + c) из жизни; подставить значение и вычислить.',
       varies='Сюжет (прокат, каршеринг, фотопечать, размер обуви, «термометр-сверчок»), коэффициенты, значение переменной.',
       answer_rule='Подставляем число в формулу, соблюдая порядок действий.',
       fipi=r'(стоимость|переводить|перевести|Перевести).{0,120}(по формуле|формула|формулой).{0,250}(рассчитайте|Скольким градусам)',
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
        head = ('Количество теплоты Q (в джоулях), которое выделяет проводник с током, находят по закону Джоуля — Ленца: Q = I²Rt, где I — сила тока (в амперах), t — время (в секундах), R — сопротивление проводника (в омах).')
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
        head = 'Мощность P (в ваттах), которую потребляет электроприбор, находят по формуле P = U²/R, где R — сопротивление прибора (в омах), U — напряжение сети (в вольтах).'
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
        head = ('Количество теплоты Q (в джоулях), которое выделяет проводник с током, находят по закону Джоуля — Ленца: Q = I²Rt, где I — сила тока (в амперах), t — время (в секундах), R — сопротивление проводника (в омах).')
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
        head = 'Мощность P (в ваттах), которую потребляет электроприбор, находят по формуле P = U²/R, где R — сопротивление прибора (в омах), U — напряжение сети (в вольтах).'
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
        style='Инструкции КИМ ОГЭ №13: «Укажите решение неравенства …», «Укажите решение системы неравенств …», '
              '«Укажите неравенство, решение которого изображено на рисунке»; варианты 1)–4) — промежутки или рисунки, в ответ — номер')
FLIP = {'<': '>', '>': '<', '≤': '≥', '≥': '≤'}
REL = {'<': sp.Lt, '>': sp.Gt, '≤': sp.Le, '≥': sp.Ge}
ASK13 = ('Укажите решение неравенства {x}.',)
ASK13S = ('Укажите решение системы неравенств {x}.',)
REALS = ((None, None, False, False),)
PIC13 = ''  # варианты-рисунки подписаны 1)–4), как в КИМ

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
        ivs, marks = [], {}
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
       fipi=r'Укажите решение неравенства\s+[−-]?\s*\d+\s*[−-]\s*\d*\s*x\s*[<>≤≥]|Укажите решение неравенства\s*\.$',
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
    if not nice(bound, 2) or bound == 0:
        return None
    sol = lin_sol(k, m, rel)
    wrong = [s_not(sol), s_flip(sol), s_flip(s_not(sol)), ray(FLIP[rel] if k < 0 else rel, -bound) if bound else ray(rel, 1)]
    wrong += [lin_sol(-k, m, rel)] if k != 0 else []
    pictures = r.random() < 0.5
    q = pick(r, *ASK13).format(x=f'⟦{lhs} {rel} {rhs}⟧')
    e = f'{lin(k, 0)} {rel} {tnum(m)}' + ('' if k == 1 else ('; делим на ' + tnum(k) + (' и меняем знак' if k < 0 else '') + f': x {FLIP[rel] if k < 0 else rel} {_nb(bound)}')) + '.'
    return _ineq_card(r, q, sol, wrong, pictures, e, lambda: _sym_solve(lhs, rel, rhs))


@proto('og13-system', 'oge', 13, 'Система линейных неравенств: выбор решения',
       invariant='Система двух линейных неравенств; решение — пересечение лучей (отрезок, луч или пустое множество).',
       varies='Форма как в банке ({x + c ≷ r} с десятичными c или {−kt + kx ≷ 0; e − kx ≷ f}), знаки, форма вариантов (рисунки или промежутки).',
       answer_rule='Решаем каждое неравенство, пересекаем решения на прямой.',
       fipi=r'Укажите решение системы неравенств',
       mistakes=['берут объединение вместо пересечения', 'не меняют знак при делении на отрицательное'],
       card_kind='one', kim=K13)
def gen_og13_system(r):
    # две формы банка: {x + 3 ≥ −2; x + 1,1 ≥ 0} (коэффициент 1, десятичные) и {−35 + 5x < 0; 6 − 3x > −18}
    parts, sets = [], []
    form = r.choice('AB')
    for i in range(2):
        rel = r.choice(list(FLIP))
        if form == 'A':
            c = F(r.randint(-9, 9)) if r.random() < 0.5 else F(r.choice([x for x in range(-99, 100) if x % 10]), 10)
            rr = F(r.randint(-6, 6))
            if c == 0:
                return None
            lhs, rhs = lin(1, c), tnum(rr)
            k, m = 1, rr - c
        elif i == 0:  # −k·t + kx ≷ 0
            k, t = r.randint(2, 9), r.choice([x for x in range(-9, 10) if x])
            lhs, rhs = f'{tnum(-k * t)}{signed(k)}x', '0'
            m = F(k * t)
        else:  # e − kx ≷ f
            k, t = r.randint(2, 9), r.choice([x for x in range(-9, 10) if x])
            e0 = r.randint(1, 12)
            f0 = e0 - k * t
            lhs, rhs = f'{e0} − {k}x', tnum(f0)
            k, m = -k, F(f0 - e0)
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
    q = pick(r, *ASK13S).format(x=f'⟦{txt}⟧')
    e = f'Первое: x ∈ {s_txt(sets[0])}; второе: x ∈ {s_txt(sets[1])}; общая часть: {s_txt(sol)}.'
    return _ineq_card(r, q, sol, wrong, pictures, e, lambda: _sym_solve(*parts[0]).intersect(_sym_solve(*parts[1])))


@proto('og13-quad', 'oge', 13, 'Квадратное неравенство: выбор решения',
       invariant='x² − a² ≷ 0, p²x² ≷ q², kx − x² ≷ 0: корни и знаки параболы; решение — отрезок/интервал или объединение лучей.',
       varies='Вид неравенства, числа, знак, форма вариантов (промежутки или рисунки).',
       answer_rule='Находим корни, учитываем направление ветвей, выбираем нужные промежутки.',
       fipi=r'Укажите решение неравенства\s+(\d*\s*x\s*[−-]\s*x\s*2|\d*\s*x\s*2\s*[−<>≤≥-])',
       mistakes=['берут промежуток между корнями вместо внешних лучей', 'для kx − x² забывают, что ветви вниз'],
       card_kind='one', kim=K13)
def gen_og13_quad(r):
    kind = r.randrange(3)
    rel = r.choice(list(FLIP))
    if kind == 0:
        a = r.randint(9, 16)
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
        k = r.randint(7, 15)
        if r.random() < 0.6:
            lhs, rhs = f'{k if k > 1 else ""}x − x²', '0'
            sol = quad_sol(-1, 0, k, rel)
        else:
            lhs, rhs = f'x² − {k if k > 1 else ""}x', '0'
            sol = quad_sol(1, 0, k, rel)
    wrong = [s_not(sol), s_flip(sol), s_flip(s_not(sol))]
    if len(sol) == 2:
        wrong += [(sol[1],), (sol[0],)]
    else:
        a_, b_, ca, cb = sol[0]
        wrong += [((None, b_, False, cb),), ((a_, None, ca, False),)]
    pictures = r.random() < 0.5
    q = pick(r, *ASK13).format(x=f'⟦{lhs} {rel} {rhs}⟧')
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
    q = 'Укажите неравенство, множество решений которого изображено на рисунке.'
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


def money(n):
    """Число рублей в тексте: 9500, но 15 370 (пробел в числах от 10 000)."""
    n = int(n)
    return f'{n:,}'.replace(',', ' ') if abs(n) >= 10000 else str(n)


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
    iso = 'ISO 216' if ser in 'BC' else 'ISO 217'  # серии RA и SRA описаны в ISO 217
    return (f'Кроме привычной серии A, стандарт {iso} описывает форматы бумаги серии {ser} — их используют для {PAPER_USE[ser]}. '
            f'Самый большой лист {ser}0 имеет размеры {s0[0]} × {s0[1]} мм. Если лист любого формата разрезать пополам поперёк большей стороны, '
            f'получатся два листа следующего формата: из {ser}0 — два {ser}1, из {ser}1 — два {ser}2 и так далее.'
            + (' Отношение большей стороны к меньшей у всех листов серии одинаковое.' if ser in 'BC' else ''))


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
    q = _paper_intro(ser) + '\nДаны размеры четырёх листов (длина × ширина). Установите соответствие между форматами и номерами листов.'
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
         f'Текст напечатан на листе {ser}{src} шрифтом высотой {f0} {plural(f0, "пункт", "пункта", "пунктов")}. Каким должен быть шрифт (в пунктах), чтобы тот же текст разместился на листе {ser}{dst} '
         'точно так же, то есть все размеры изменились в одно и то же число раз? Размер шрифта округлите до целого.')
    e = f'Коэффициент подобия {PAPER[ser][dst][1]}/{PAPER[ser][src][1]}; {f0}·{approx(ratio, 3)} ≈ {approx(val, 2)} ≈ {ans}.'
    return pcard(q, num(ans), e=e), lambda: ans == round(sp.Rational(f0 * PAPER[ser][dst][1], PAPER[ser][src][1]))


# ---------------------------------------------------------------- план на клетчатой бумаге (территория, квартира)

def svg_plan(cols, rows, rects, cells=(), gate=None, cell=22, fills=None, extra=''):
    """План: rects — [(x, y, w, h, 'подпись')] в клетках (y вверх); cells — закрашенные клетки дорожек [(x, y)];
    gate — (x, y) клетка ворот на границе (рисуется стрелкой)."""
    W, H = cols * cell + 20, rows * cell + 20
    sx = lambda x: 10 + x * cell
    sy = lambda y: 10 + (rows - y) * cell
    g = ''.join(f'<line x1="{sx(i)}" y1="{sy(0)}" x2="{sx(i)}" y2="{sy(rows)}"/>' for i in range(cols + 1))
    g += ''.join(f'<line x1="{sx(0)}" y1="{sy(j)}" x2="{sx(cols)}" y2="{sy(j)}"/>' for j in range(rows + 1))
    out = f'<g stroke="{GRID}" stroke-width="1">{g}</g>'
    out += ''.join(f'<rect x="{sx(x)}" y="{sy(y + 1)}" width="{cell}" height="{cell}" fill="#C9CED8"/>' for x, y in cells)
    for i, (x, y, w, h, lab) in enumerate(rects):
        fill = (fills or {}).get(i, BLUE)
        out += (f'<rect x="{sx(x)}" y="{sy(y + h)}" width="{w * cell}" height="{h * cell}" fill="{fill}" fill-opacity="0.16" stroke="{fill}" stroke-width="2.2"/>'
                f'<text x="{sx(x + w / 2):.1f}" y="{sy(y + h / 2) + 6:.1f}" text-anchor="middle" font-size="17" font-weight="bold">{lab}</text>')
    out += f'<rect x="{sx(0)}" y="{sy(rows)}" width="{cols * cell}" height="{rows * cell}" fill="none" stroke="{INK}" stroke-width="2.4"/>'
    if gate:
        gx, gy = gate
        out += (f'<line x1="{sx(gx + 0.5)}" y1="{sy(gy) + 26}" x2="{sx(gx + 0.5)}" y2="{sy(gy) + 3}" stroke="{RED}" stroke-width="2.4" marker-end="url(#a)"/>')
    return _svg(W, H + (18 if gate else 0), out + extra)


def _dist_rect(a, b):
    """(dx, dy) — зазоры между прямоугольниками a=(x, y, w, h), b по осям (0, если проекции перекрываются)."""
    dx = max(0, b[0] - (a[0] + a[2]), a[0] - (b[0] + b[2]))
    dy = max(0, b[1] - (a[1] + a[3]), a[1] - (b[1] + b[3]))
    return dx, dy


YARDS = [
    dict(site='турбазы', obj=['главный корпус', 'столовая', 'баня', 'лодочный сарай'], tile='бетонной плиткой'),
    dict(site='школьного двора', obj=['школа', 'спортзал', 'теплица', 'мастерская'], tile='тротуарной плиткой'),
    dict(site='фермы', obj=['жилой дом', 'коровник', 'амбар', 'птичник'], tile='бетонной плиткой'),
    dict(site='детского лагеря', obj=['спальный корпус', 'столовая', 'медпункт', 'склад'], tile='резиновой плиткой'),
    dict(site='автосервиса', obj=['мастерская', 'офис', 'мойка', 'склад шин'], tile='тротуарной плиткой'),
]


def _yard_block(r):
    """Генерация плана территории: 4 строения, аллея, ворота внизу."""
    ctx = r.choice(YARDS)
    cols, rows = r.randint(18, 22), r.randint(13, 16)
    s = r.choice([1, 1, 2])  # сторона клетки, м
    ym = r.randint(5, rows - 7)  # ряд аллеи
    g = r.randint(7, cols - 8)  # колонка дорожки от ворот
    rects = []
    # два строения ниже аллеи (слева и справа от дорожки), два — выше
    specs = [(1, g - 1, 1, ym - 1), (g + 2, cols - 1, 1, ym - 1), (1, cols // 2 - 1, ym + 2, rows - 1), (cols // 2 + 1, cols - 1, ym + 2, rows - 1)]
    for x0, x1, y0, y1 in specs:
        if x1 - x0 < 3 or y1 - y0 < 2:
            return None
        w = r.randint(2, min(8, x1 - x0))
        h = r.randint(2, min(6, y1 - y0))
        x = r.randint(x0, x1 - w)
        y = r.randint(y0, y1 - h) if r.random() < 0.4 else (y1 - h if y0 == 1 else y0)
        rects.append((x, y, w, h))
    areas = [w * h for _, _, w, h in rects]
    if len(set(areas)) < 4:
        return None
    path = {(x, ym) for x in range(1, cols - 1)} | {(g, y) for y in range(0, ym)}
    names = ctx['obj'][:]
    r.shuffle(names)
    # правила описания: самое большое; ближе всех к воротам; из оставшихся двух — левее; последнее
    order = list(range(4))
    big = max(order, key=lambda i: areas[i])
    rest = [i for i in order if i != big]
    gd = lambda i: sum(_dist_rect(rects[i], (g, 0, 1, 1)))
    dists = sorted(gd(i) for i in rest)
    if dists[0] == dists[1]:
        return None
    near = min(rest, key=gd)
    rest2 = [i for i in rest if i != near]
    if rects[rest2[0]][0] == rects[rest2[1]][0]:
        return None
    left = min(rest2, key=lambda i: rects[i][0])
    last = [i for i in rest2 if i != left][0]
    assign = {big: names[0], near: names[1], left: names[2], last: names[3]}
    digits = list(range(1, 5))
    r.shuffle(digits)
    desc = (f'На клетчатом плане (сторона клетки {s} м) изображены строения {ctx["site"]}; въездные ворота отмечены стрелкой. Самое большое строение — {names[0]}. '
            f'Ближе всех к воротам находится {names[1]}. Из двух оставшихся строений левее на плане стоит {names[2]}, а правее — {names[3]}. '
            f'Дорожки, выложенные {ctx["tile"]}, закрашены серым.')
    return dict(ctx=ctx, cols=cols, rows=rows, s=s, rects=rects, areas=areas, path=path, gate=(g, 0), assign=assign,
                digits=digits, desc=desc, names=names)


def _yard_svg(b):
    rects = [(x, y, w, h, str(b['digits'][i])) for i, (x, y, w, h) in enumerate(b['rects'])]
    return svg_plan(b['cols'], b['rows'], rects, cells=sorted(b['path']), gate=b['gate'])


@proto('og01-yard-match', 'oge', 1, 'План территории: какие цифры соответствуют объектам',
       invariant='По словесному описанию (самое большое, ближе к воротам, левее/правее) определить, какой цифрой на плане обозначен каждый объект.',
       varies='Сюжет (турбаза, школьный двор, ферма, лагерь, автосервис), расположение и размеры строений, нумерация.',
       answer_rule='Последовательно применяем признаки описания к плану; каждому объекту — своя цифра.',
       fipi=r'Для объектов, указанных в таблице, определите, какими цифрами они обозначены на плане',
       mistakes=['путают «ближе к воротам» с «ближе к краю плана»', 'сравнивают площади на глаз'],
       svg=True, card_kind='match', kim=KP(1, ['7.1', '7.5'], [9, 10], 3, answer='соответствие'))
def gen_og01_yard_match(r):
    b = _yard_block(r)
    if not b:
        return None
    names = b['ctx']['obj']
    left = [{'id': LET[j], 't': nm} for j, nm in enumerate(names)]
    right = [{'id': str(d), 't': f'цифра {d} на плане'} for d in range(1, 5)]
    idx = {nm: i for i, nm in b['assign'].items()}
    a = {LET[j]: str(b['digits'][idx[nm]]) for j, nm in enumerate(names)}
    q = b['desc'] + '\nДля объектов, перечисленных ниже, определите, какими цифрами они обозначены на плане.'
    e = '; '.join(f'{nm} — {b["digits"][idx[nm]]}' for nm in names) + '.'

    def chk():  # заново применяем правила к геометрии
        rects, areas = b['rects'], b['areas']
        big = max(range(4), key=lambda i: areas[i])
        rest = [i for i in range(4) if i != big]
        g = b['gate'][0]
        near = min(rest, key=lambda i: math.hypot(*_dist_rect(rects[i], (g, 0, 1, 1))) * 0 + sum(_dist_rect(rects[i], (g, 0, 1, 1))))
        rest2 = [i for i in rest if i != near]
        lft = min(rest2, key=lambda i: rects[i][0])
        want = {b['names'][0]: big, b['names'][1]: near, b['names'][2]: lft, b['names'][3]: [i for i in rest2 if i != lft][0]}
        return all(a[LET[j]] == str(b['digits'][want[nm]]) for j, nm in enumerate(names))
    return pcard(q, a, e=e, k='match', o={'left': left, 'right': right}, svg=_yard_svg(b)), chk


@proto('og02-yard-tiles', 'oge', 2, 'План территории: сколько упаковок плитки для дорожек',
       invariant='Дорожки на плане — закрашенные клетки; площадь дорожек → число плиток → число упаковок (округление вверх).',
       varies='Сюжет, план, размер клетки и плитки, число плиток в упаковке.',
       answer_rule='Считаем клетки дорожек, переводим в плитки, делим на размер упаковки и округляем вверх.',
       fipi=r'(продаются|продаётся|продается) в упаковках.{0,120}дорожк',
       mistakes=['округляют вниз', 'не учитывают, что в клетке несколько плиток'], svg=True,
       kim=KP(2, ['1.2', '7.5', '3.3'], [8, 11], 4))
def gen_og02_yard_tiles(r):
    b = _yard_block(r)
    if not b:
        return None
    n_cells = len(b['path'])
    tile = r.choice([F(1, 2), F(1, 2), F(1)] if b['s'] == 1 else [F(1), F(1, 2)])
    per_cell = int((b['s'] / tile) ** 2)
    tiles = n_cells * per_cell
    pack = r.choice([4, 5, 6, 8, 10, 12, 15, 20, 25])
    if r.random() < 0.3:  # упаковка рассчитана на площадь
        sq = r.choice([F(2), F(5, 2), F(3), F(7, 2), F(4), F(5)])
        area = n_cells * b['s'] ** 2
        ans = math.ceil(area / sq)
        if (area / sq).denominator == 1:
            return None
        q = b['desc'] + f'\nПлитка продаётся упаковками, каждой из которых хватает на {tnum(sq)} м². Сколько упаковок понадобится, чтобы выложить все дорожки?'
        e = f'Площадь дорожек {n_cells}·{b["s"] ** 2} = {area} м²; {area} : {tnum(sq)} → {ans} (округляем вверх).'
        return pcard(q, num(ans), e=e, svg=_yard_svg(b)), lambda: ans == sp.ceiling(len(b['path']) * b['s'] ** 2 / R(sq))
    ans = -(-tiles // pack)
    if tiles % pack == 0:
        return None
    tsz = '1 × 1 м' if tile == 1 else '50 × 50 см'
    q = (b['desc'] + f'\nДорожки выкладывают квадратной плиткой {tsz}; плитка продаётся упаковками по {pack} {plural(pack, "штуке", "штуки", "штук")}. '
         'Сколько упаковок понадобится, чтобы выложить все дорожки?').replace('по 1 штуке', 'по 1 штуке')
    e = f'Клеток дорожек {n_cells}, в клетке {per_cell} {plural(per_cell, "плитка", "плитки", "плиток")}: {tiles} {plural(tiles, "плитка", "плитки", "плиток")}; {tiles} : {pack} → {ans} {plural(ans, "упаковка", "упаковки", "упаковок")} (с округлением вверх).'
    return pcard(q, num(ans), e=e, svg=_yard_svg(b)), lambda: ans == sp.ceiling(sp.Rational(len(b['path']) * int((b['s'] / tile) ** 2), pack))


@proto('og03-yard-area', 'oge', 3, 'План территории: площадь или периметр строения',
       invariant='Строение — прямоугольник из клеток; площадь (м²) или периметр (м) с учётом стороны клетки.',
       varies='Сюжет, план, объект, размер клетки, спрашиваемая величина.',
       answer_rule='Считаем клетки по сторонам и умножаем на сторону клетки (для площади — на её квадрат).',
       fipi=r'Найдите (площадь, которую занимает|периметр|площадь открытого грунта)',
       mistakes=['для площади умножают на сторону клетки, а не на её квадрат', 'путают площадь и периметр'], svg=True,
       kim=KP(3, ['7.5'], [11], 3))
def gen_og03_yard_area(r):
    b = _yard_block(r)
    if not b:
        return None
    i = r.randrange(4)
    x, y, w, h = b['rects'][i]
    nm = b['assign'][i]
    s = b['s']
    kind = r.random()
    if kind < 0.2:
        free = b['cols'] * b['rows'] - sum(b['areas']) - len(b['path'])
        ans = free * s * s
        q = b['desc'] + '\nНайдите площадь части территории, не занятой ни строениями, ни дорожками. Ответ дайте в квадратных метрах.'
        e = f'Всего {b["cols"] * b["rows"]} клеток, строения {sum(b["areas"])}, дорожки {len(b["path"])}; свободно {free} клеток = {ans} м².'
        chk = lambda: ans == (b['cols'] * b['rows'] - sum(w_ * h_ for _, _, w_, h_ in b['rects']) - len(b['path'])) * s ** 2
    elif kind < 0.7:
        ans = w * h * s * s
        q = b['desc'] + f'\nНайдите площадь, которую занимает {nm}. Ответ дайте в квадратных метрах.'
        e = f'{w}·{s} м × {h}·{s} м = {ans} м².'
        chk = lambda: ans == b['rects'][i][2] * b['rects'][i][3] * s ** 2
    else:
        ans = 2 * (w + h) * s
        q = b['desc'] + f'\nНайдите периметр строения «{nm}». Ответ дайте в метрах.'
        e = f'2·({w * s} + {h * s}) = {ans} м.'
        chk = lambda: ans == 2 * (b['rects'][i][2] + b['rects'][i][3]) * s
    return pcard(q, num(ans), e=e, svg=_yard_svg(b)), chk


@proto('og04-yard-distance', 'oge', 4, 'План территории: расстояние между строениями',
       invariant='Расстояние между ближайшими точками двух строений по прямой: по клеткам (если строения «друг напротив друга») или по теореме Пифагора.',
       varies='Сюжет, план, пара строений, сторона клетки.',
       answer_rule='Находим горизонтальный и вертикальный зазоры в клетках, переводим в метры, при необходимости — теорема Пифагора.',
       fipi=r'расстояние между двумя ближайшими точками по прямой',
       mistakes=['меряют между центрами строений', 'складывают катеты вместо теоремы Пифагора'], svg=True,
       kim=KP(4, ['7.5', '7.2'], [11], 4))
def gen_og04_yard_distance(r):
    b = _yard_block(r)
    if not b:
        return None
    pairs = []
    for i in range(4):
        for j in range(i + 1, 4):
            dx, dy = _dist_rect(b['rects'][i], b['rects'][j])
            d2 = dx * dx + dy * dy
            if d2 and math.isqrt(d2) ** 2 == d2:
                pairs.append((i, j, dx, dy))
    if not pairs:
        return None
    diag = [p for p in pairs if p[2] and p[3]]
    i, j, dx, dy = r.choice(diag) if diag and r.random() < 0.7 else r.choice(pairs)
    ans = math.isqrt(dx * dx + dy * dy) * b['s']
    q = b['desc'] + f'\nНайдите расстояние (в метрах) между строениями «{b["assign"][i]}» и «{b["assign"][j]}», то есть между их ближайшими точками по прямой.'
    e = f'Зазоры: {dx * b["s"]} м и {dy * b["s"]} м; расстояние √({(dx * b["s"]) ** 2} + {(dy * b["s"]) ** 2}) = {ans} м.' if dx and dy else f'Строения напротив друг друга: {ans} м.'

    def chk():  # перебор всех пар угловых точек/сторон по сетке 0,5 клетки
        A, B = b['rects'][i], b['rects'][j]
        ptsA = [(A[0] + u / 2, A[1] + v / 2) for u in range(2 * A[2] + 1) for v in range(2 * A[3] + 1)]
        ptsB = [(B[0] + u / 2, B[1] + v / 2) for u in range(2 * B[2] + 1) for v in range(2 * B[3] + 1)]
        m = min((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2 for pa in ptsA for pb in ptsB)
        return abs(math.sqrt(m) * b['s'] - ans) < 1e-9
    return pcard(q, num(ans), e=e, svg=_yard_svg(b)), chk


@proto('og04-yard-percent', 'oge', 4, 'План территории: проценты площадей',
       invariant='Сравнение площадей в процентах: на сколько процентов одно строение больше/меньше другого или какую долю территории занимают строения (округление до целых).',
       varies='Сюжет, план, пара строений или набор, вид вопроса.',
       answer_rule='Считаем площади в клетках; (S₁ − S₂)/S₂·100% или S/S_общ·100%.',
       fipi=r'На сколько процентов площадь|Сколько процентов (от )?площади',
       mistakes=['делят на площадь не того строения', 'забывают умножить на 100'], svg=True, maxdec=0,
       kim=KP(4, ['1.2', '7.5'], [8, 11], 4))
def gen_og04_yard_percent(r):
    b = _yard_block(r)
    if not b:
        return None
    A = b['areas']
    kind = r.randrange(3)
    if kind < 2:
        i, j = r.sample(range(4), 2)
        big = A[i] > A[j]
        val = F(abs(A[i] - A[j]) * 100, A[j])
        if not nice(val, 0):
            return None
        ans = val
        q = b['desc'] + f'\nНа сколько процентов площадь строения «{b["assign"][i]}» {"больше" if big else "меньше"} площади строения «{b["assign"][j]}»?'
        e = f'Площади в клетках: {A[i]} и {A[j]}; |{A[i]} − {A[j]}| : {A[j]} · 100% = {tnum(ans)}%.'
        chk = lambda: same(num(ans), sp.Abs(sp.Rational(A[i] - A[j], A[j])) * 100)
    else:
        tot = b['cols'] * b['rows']
        val = F(sum(A) * 100, tot)
        ans = F(math.floor(val + F(1, 2)))
        if abs(val - math.floor(val) - F(1, 2)) < F(1, 50):
            return None
        q = b['desc'] + f'\nСколько процентов площади всей территории занимают строения? Ответ округлите до целого.'
        e = f'Строения: {sum(A)} клеток из {tot}; {sum(A)}/{tot}·100% ≈ {tnum(ans)}%.'
        chk = lambda: ans == round(sp.Rational(sum(A) * 100, tot))
    return pcard(q, num(ans), e=e, svg=_yard_svg(b)), chk


PAYBACK = [
    ('Для обогрева мастерской выбирают между газовым и электрическим котлом.', ('газовый котёл', 'электрический котёл'),
     lambda r: (r.choice([F(16, 10), F(15, 10), F(12, 10), F(2)]), 'куб. м газа в час', r.choice([F(7), F(8), F(9), F(65, 10)]), 'руб. за куб. м',
                r.choice([F(5), F(6), F(8)]), 'кВт', r.choice([F(5), F(6), F(55, 10), F(7)]), 'руб. за кВт·ч')),
    ('Для освещения спортплощадки выбирают светодиодные или галогенные прожекторы.', ('светодиодные прожекторы', 'галогенные прожекторы'),
     lambda r: (r.choice([F(2), F(3), F(4)]), 'кВт', r.choice([F(6), F(7), F(8)]), 'руб. за кВт·ч', r.choice([F(8), F(10), F(12)]), 'кВт', None, None)),
    ('Для сушки урожая на ферме выбирают сушильную установку: газовую или электрическую.', ('газовая сушилка', 'электрическая сушилка'),
     lambda r: (r.choice([F(2), F(25, 10), F(3)]), 'куб. м газа в час', r.choice([F(7), F(8), F(9)]), 'руб. за куб. м',
                r.choice([F(10), F(12), F(15)]), 'кВт', r.choice([F(5), F(6), F(65, 10)]), 'руб. за кВт·ч')),
    ('Для полива огорода выбирают насос: электрический или бензиновый.', ('электрический насос', 'бензиновый насос'),
     lambda r: (r.choice([F(1), F(15, 10), F(2)]), 'кВт', r.choice([F(6), F(7), F(8)]), 'руб. за кВт·ч', r.choice([F(1), F(12, 10), F(15, 10)]), 'л бензина в час', r.choice([F(55), F(60), F(62)]), 'руб. за литр')),
]


@proto('og05-yard-payback', 'oge', 5, 'Выбор оборудования: через сколько часов окупится более дорогой вариант',
       invariant='Два варианта оборудования: дороже купить, но дешевле в работе; найти, через сколько часов работы экономия покроет разницу в цене.',
       varies='Сюжет (котлы, прожекторы, насосы), цены, мощности/расход, тарифы.',
       answer_rule='Часы = (разница начальных затрат) / (разница стоимости часа работы).',
       fipi=r'Через сколько часов непрерывной работы',
       mistakes=['сравнивают только цену покупки', 'путают кВт и кВт·ч в расчёте стоимости часа'], lim=10 ** 5,
       kim=KP(5, ['3.3', '1.2', '8.1'], [8, 14], 6))
def gen_og05_yard_payback(r):
    head, (n1, n2), gen = r.choice(PAYBACK)
    a1, u1, p1, v1, a2, u2, p2, v2 = gen(r)
    if p2 is None:
        p2, v2 = p1, v1
    c1, c2 = a1 * p1, a2 * p2  # стоимость часа
    if c1 >= c2:
        return None
    hours = r.randint(20, 400) * 5
    d = (c2 - c1) * hours
    if not nice(d, 0):
        return None
    base2 = r.randint(8, 40) * 1000
    inst2 = r.randint(3, 20) * 500
    base1 = base2 + r.randint(1, 8) * 1000
    inst1 = base2 + inst2 + int(d) - base1
    if inst1 <= 0 or inst1 > 60000:
        return None
    rows = [['', 'Цена, руб.', 'Установка, руб.', 'Расход', 'Цена ресурса'],
            [n1, money(base1), money(inst1), f'{tnum(a1)} {u1}', f'{tnum(p1)} {v1}'],
            [n2, money(base2), money(inst2), f'{tnum(a2)} {u2}', f'{tnum(p2)} {v2}']]
    q = (head + ' Цены, стоимость установки и расход ресурсов даны в таблице. Выбрали вариант «' + n1 + '». '
         f'Через сколько часов работы экономия на ресурсах покроет разницу в стоимости покупки и установки?')
    e = f'Разница затрат: {base1 + inst1 - base2 - inst2} руб.; час работы: {tnum(c1)} и {tnum(c2)} руб., экономия {tnum(c2 - c1)} руб./ч; {hours} ч.'
    svg = svg_table(rows, colw=[150, 80, 100, 130, 130])
    t = sp.Symbol('t')
    return pcard(q, num(hours), e=e, svg=svg), lambda: same(num(hours), sp.solve(sp.Eq(base1 + inst1 + R(c1) * t, base2 + inst2 + R(c2) * t), t)[0])


# ---------------------------------------------------------------- сюжет «план помещения»

FLATS = [
    dict(what='офиса небольшой фирмы', rooms=['переговорная', 'кабинет директора', 'кухня', 'архив'], hall='холл'),
    dict(what='первого этажа загородного дома', rooms=['гостиная', 'кухня', 'котельная', 'кладовая'], hall='прихожая'),
    dict(what='небольшого кафе', rooms=['зал для посетителей', 'кухня', 'склад', 'гардероб'], hall='коридор'),
    dict(what='сельской библиотеки', rooms=['читальный зал', 'абонемент', 'хранилище', 'кабинет'], hall='холл'),
    dict(what='детского клуба', rooms=['игровая', 'класс рисования', 'раздевалка', 'кладовая'], hall='коридор'),
]


def _flat_block(r):
    ctx = r.choice(FLATS)
    cols, rows = r.randint(14, 18), r.randint(9, 12)
    a = r.randint(5, cols - 6)          # ширина левой части
    hy = r.randint(3, rows - 4)         # граница по высоте слева
    c = r.randint(2, 3)                 # ширина коридора (справа от левой части)
    b = r.randint(3, rows - 3)          # граница справа
    rects = [(0, hy, a, rows - hy), (0, 0, a, hy), (a + c, b, cols - a - c, rows - b), (a + c, 0, cols - a - c, b), (a, 0, c, rows)]
    if min(w for _, _, w, _ in rects[:4]) < 3:
        return None
    areas = [w * h for _, _, w, h in rects]
    if len(set(areas[:4])) < 4 or max(areas[:4]) <= areas[4]:
        return None
    s = F(4, 10)
    names = ctx['rooms'][:]
    order = sorted(range(4), key=lambda i: -areas[i])
    assign = {order[0]: names[0], order[3]: names[3]}
    mid = order[1:3]
    left = min(mid, key=lambda i: (rects[i][0], -rects[i][1]))
    if rects[mid[0]][0] == rects[mid[1]][0]:
        return None
    assign[left] = names[1]
    assign[[i for i in mid if i != left][0]] = names[2]
    digits = list(range(1, 5))
    r.shuffle(digits)
    desc = (f'На рисунке — план {ctx["what"]} (сторона клетки {tnum(s)} м). Вдоль всего помещения тянется {ctx["hall"]} — серые клетки на плане. '
            f'Самое большое помещение — {names[0]}, самое маленькое — {names[3]}. Из двух оставшихся помещений левее на плане находится {names[1]}, '
            f'а {names[2]} — правее.')
    return dict(ctx=ctx, cols=cols, rows=rows, s=s, rects=rects, areas=areas, assign=assign, digits=digits, desc=desc, names=names)


def _flat_svg(b):
    rects = [(x, y, w, h, str(b['digits'][i])) for i, (x, y, w, h) in enumerate(b['rects'][:4])]
    x, y, w, h = b['rects'][4]
    cells = [(x + i, y + j) for i in range(w) for j in range(h)]
    return svg_plan(b['cols'], b['rows'], rects, cells=cells, cell=24)


@proto('og01-flat-match', 'oge', 1, 'План помещения: какими цифрами обозначены комнаты',
       invariant='По описанию (самое большое/маленькое, левее/правее) определить цифры помещений на плане.',
       varies='Сюжет (офис, дом, кафе, библиотека, клуб), разбиение плана, нумерация.',
       answer_rule='Считаем площади в клетках, сравниваем, применяем признаки расположения.',
       fipi=r'определите, какими цифрами (они )?обозначены на плане|Для (объектов|помещений), указанных в таблице',
       mistakes=['ошибаются в подсчёте клеток', 'путают лево и право на плане'], svg=True, card_kind='match',
       kim=KP(1, ['7.1', '7.5'], [9, 10], 3, answer='соответствие'))
def gen_og01_flat_match(r):
    b = _flat_block(r)
    if not b:
        return None
    names = b['ctx']['rooms']
    idx = {nm: i for i, nm in b['assign'].items()}
    left = [{'id': LET[j], 't': nm} for j, nm in enumerate(names)]
    right = [{'id': str(d), 't': f'цифра {d} на плане'} for d in range(1, 5)]
    a = {LET[j]: str(b['digits'][idx[nm]]) for j, nm in enumerate(names)}
    q = b['desc'] + '\nДля помещений, перечисленных ниже, определите, какими цифрами они обозначены на плане.'
    e = '; '.join(f'{nm} — {b["digits"][idx[nm]]} ({b["areas"][idx[nm]]} {plural(b["areas"][idx[nm]], "клетка", "клетки", "клеток")})' for nm in names) + '.'

    def chk():
        ar = b['areas'][:4]
        big, small = ar.index(max(ar)), ar.index(min(ar))
        mid = [i for i in range(4) if i not in (big, small)]
        lft = min(mid, key=lambda i: b['rects'][i][0])
        want = {names[0]: big, names[3]: small, names[1]: lft, names[2]: [i for i in mid if i != lft][0]}
        return all(a[LET[j]] == str(b['digits'][want[nm]]) for j, nm in enumerate(names))
    return pcard(q, a, e=e, k='match', o={'left': left, 'right': right}, svg=_flat_svg(b)), chk


FLOOR = [('плиткой 40 × 40 см', 1), ('плиткой 20 × 40 см', 2), ('плиткой 20 × 20 см', 4), ('паркетной доской 20 × 40 см', 2)]


@proto('og02-flat-floor', 'oge', 2, 'План помещения: упаковки плитки (паркета) для пола',
       invariant='Площадь пола помещения в клетках → число плиток/досок → число упаковок (округление вверх).',
       varies='Сюжет, помещение, размер плитки (1, 2 или 4 на клетку), размер упаковки.',
       answer_rule='Клетки × (плиток на клетку) = число плиток; делим на упаковку и округляем вверх.',
       fipi=r'(Плитка для пола|Паркетная доска) размером',
       mistakes=['округляют вниз', 'не учитывают, сколько плиток в одной клетке'], svg=True, kim=KP(2, ['1.2', '7.5', '3.3'], [8, 11], 4))
def gen_og02_flat_floor(r):
    b = _flat_block(r)
    if not b:
        return None
    i = r.randrange(4)
    nm = b['assign'][i]
    ft, per = r.choice(FLOOR)
    pack = r.choice([6, 8, 10, 12, 14, 16, 20, 24])
    n = b['areas'][i] * per
    if n % pack == 0:
        return None
    ans = -(-n // pack)
    forms = ('доска', 'доски', 'досок') if 'доск' in ft else ('плитка', 'плитки', 'плиток')
    q = (b['desc'] + f'\nПол в помещении «{nm}» покрывают {ft}; в упаковке {pack} {plural(pack, *forms)}. Сколько упаковок нужно купить, чтобы покрыть весь пол в этом помещении?')
    e = f'Клеток {b["areas"][i]}, на клетку {per}: {n} {plural(n, *forms)}; {n} : {pack} → {ans} {plural(ans, "упаковка", "упаковки", "упаковок")} (округляем вверх).'
    return pcard(q, num(ans), e=e, svg=_flat_svg(b)), lambda: ans == sp.ceiling(sp.Rational(b['rects'][i][2] * b['rects'][i][3] * per, pack))


@proto('og03-flat-area', 'oge', 3, 'План помещения: площадь комнаты',
       invariant='Площадь прямоугольного помещения по плану: число клеток × площадь клетки (0,4 × 0,4 м).',
       varies='Сюжет, помещение, разбиение.',
       answer_rule='S = (клеток по длине × 0,4) · (клеток по ширине × 0,4).',
       fipi=r'Найдите площадь (кухни|спальни|гостиной|санузла|кладовой|коридора|лоджии|большей лоджии|меньшей лоджии)',
       mistakes=['умножают число клеток на 0,4 вместо 0,16'], svg=True, kim=KP(3, ['7.5', '1.2'], [11], 3))
def gen_og03_flat_area(r):
    b = _flat_block(r)
    if not b:
        return None
    i = r.randrange(5)
    x, y, w, h = b['rects'][i]
    nm = b['assign'].get(i, b['ctx']['hall'])
    ans = w * b['s'] * h * b['s']
    q = b['desc'] + f'\nНайдите площадь помещения «{nm}». Ответ дайте в квадратных метрах.'
    e = f'{w}·0,4 = {tnum(w * b["s"])} м, {h}·0,4 = {tnum(h * b["s"])} м; S = {tnum(ans)} м².'
    return pcard(q, num(ans), e=e, svg=_flat_svg(b)), lambda: same(num(ans), R(b['s']) ** 2 * b['rects'][i][2] * b['rects'][i][3])


@proto('og04-flat-percent', 'oge', 4, 'План помещения: на сколько процентов одна комната больше другой',
       invariant='Сравнение площадей двух помещений в процентах.',
       varies='Сюжет, пара помещений, «больше/меньше».',
       answer_rule='(S₁ − S₂)/S₂ · 100%, где S₂ — площадь, с которой сравнивают.',
       fipi=r'На сколько процентов площадь (кухни|гостиной|спальни|санузла|коридора|лоджии)',
       mistakes=['делят на площадь не того помещения'], svg=True, maxdec=1, kim=KP(4, ['1.2', '7.5'], [8, 11], 4))
def gen_og04_flat_percent(r):
    b = _flat_block(r)
    if not b:
        return None
    i, j = r.sample(range(5), 2)
    A = b['areas']
    val = F(abs(A[i] - A[j]) * 100, A[j])
    if not nice(val, 1) or val == 0 or val > 200:
        return None
    nm = lambda k: b['assign'].get(k, b['ctx']['hall'])
    q = b['desc'] + f'\nНа сколько процентов площадь помещения «{nm(i)}» {"больше" if A[i] > A[j] else "меньше"} площади помещения «{nm(j)}»?'
    e = f'В клетках: {A[i]} и {A[j]}; {abs(A[i] - A[j])} : {A[j]} · 100% = {tnum(val)}%.'
    return pcard(q, num(val), e=e, svg=_flat_svg(b)), lambda: same(num(val), sp.Abs(sp.Rational(A[i], A[j]) - 1) * 100)


APPL = [
    dict(what='посудомоечную машину', par='вместимость (комплектов посуды)', u='комплектов', need=lambda r: r.choice([9, 10, 12, 13]), vals=[6, 8, 9, 10, 11, 12, 13, 14],
         types=('встраиваемая', 'отдельностоящая'), price=(22000, 48000)),
    dict(what='водонагреватель', par='объём бака (л)', u='л', need=lambda r: r.choice([50, 80, 100]), vals=[30, 50, 80, 100, 120],
         types=('вертикальный', 'горизонтальный'), price=(9000, 26000)),
    dict(what='холодильник', par='объём камер (л)', u='л', need=lambda r: r.choice([250, 300, 350]), vals=[200, 240, 280, 310, 350, 400],
         types=('с морозилкой снизу', 'с морозилкой сверху'), price=(24000, 62000)),
    dict(what='кондиционер', par='площадь охлаждения (м²)', u='м²', need=lambda r: r.choice([20, 25, 30]), vals=[15, 20, 25, 30, 35, 40],
         types=('инверторный', 'обычный'), price=(18000, 45000)),
]


@proto('og05-choice-table', 'oge', 5, 'Выбор самого дешёвого подходящего товара по таблице',
       invariant='Таблица моделей: параметр, тип, цена, стоимость подключения, доставка (% от цены или бесплатно); отобрать подходящие и найти наименьшую полную стоимость.',
       varies='Товар, требования (не меньше X, тип), числа в таблице.',
       answer_rule='Отсеиваем неподходящие модели, для остальных считаем цену + подключение + доставку, берём минимум.',
       fipi=r'Сколько рублей будет стоить наиболее дешёвый подходящий вариант',
       mistakes=['забывают доставку в процентах', 'выбирают модель, не подходящую по типу или параметру'], svg=True, lim=10 ** 6,
       kim=KP(5, ['1.2', '8.1', '3.3'], [8, 14], 6))
def gen_og05_choice_table(r):
    ap = r.choice(APPL)
    need = ap['need'](r)
    tp = r.choice(ap['types'])
    rows = [['Модель', ap['par'], 'Тип', 'Цена, руб.', 'Подключение, руб.', 'Доставка']]
    models = []
    labs = 'АБВГДЕЖЗ'[:r.randint(6, 8)]
    fit = set(r.sample(range(len(labs)), r.choice([2, 3])))
    trap = r.choice([k for k in range(len(labs)) if k not in fit])
    for k, lab in enumerate(labs):
        if k in fit:
            v, t = r.choice([x for x in ap['vals'] if x >= need]), tp
        else:
            v, t = r.choice(ap['vals']), r.choice(ap['types'])
        price = r.randint(ap['price'][0] // 100, ap['price'][1] // 100) * 100
        inst = r.choice([0, 1500, 2000, 2500, 3000, 3500, 4000])
        dl = r.choice([0, 0, 5, 10, 15])
        if k == trap:
            price, inst, dl = ap['price'][0] - 1000, 0, 0
            if v >= need and t == tp:
                t = [x for x in ap['types'] if x != tp][0]
        total = price + inst + F(price * dl, 100)
        models.append((lab, v, t, price, inst, dl, total))
        rows.append([lab, str(v), t, money(price), str(inst) if inst else 'бесплатно', f'{dl}%' if dl else 'бесплатно'])
    good = [m for m in models if m[1] >= need and m[2] == tp]
    if len(good) < 2:
        return None
    best = min(good, key=lambda m: m[6])
    others = sorted(m[6] for m in good)
    if others[0] == others[1] or not nice(best[6], 0, 10 ** 6):
        return None
    q = (f'Для помещения выбирают {ap["what"]}. Нужна модель типа «{tp}», у которой {ap["par"].split(" (")[0]} не меньше {need} {ap["u"]}. '
         'Характеристики моделей и условия подключения и доставки приведены в таблице (доставка — в процентах от цены или бесплатно). '
         'Сколько рублей будет стоить самый дешёвый подходящий вариант вместе с подключением и доставкой?')
    e = f'Подходят: {", ".join(m[0] for m in good)}; дешевле всех модель {best[0]}: {best[3]} + {best[4]} + {best[5]}% = {tnum(best[6])} руб.'
    svg = svg_table(rows, colw=[60, 150, 150, 90, 120, 80])
    return pcard(q, num(best[6]), e=e, svg=svg), lambda: same(num(best[6]), min(sp.Rational(m[3]) * (100 + m[5]) / 100 + m[4] for m in models if m[1] >= need and m[2] == tp))


PLANS = [
    dict(intro='Для дачного роутера выбирают тариф мобильного интернета. Ожидается, что за месяц уйдёт {u} ГБ трафика, и выбирают самый дешёвый вариант.',
         unit='ГБ', rows=lambda r: [('«Лайт»', r.choice([290, 350, 390]), r.choice([10, 15, 20]), r.choice([25, 30, 40])),
                                     ('«Стандарт»', r.choice([490, 550, 590]), r.choice([30, 35, 40]), r.choice([15, 18, 20])),
                                     ('«Максимум»', r.choice([790, 850, 900]), None, None)],
         u=lambda r: r.randint(12, 60)),
    dict(intro='Бассейн продаёт абонементы на месяц. Посетитель рассчитывает прийти {u} раз и выбирает самый дешёвый вариант.',
         unit='занятий', rows=lambda r: [('«Утро»', r.choice([1600, 1800, 2000]), r.choice([4, 5, 6]), r.choice([350, 400, 450])),
                                        ('«День»', r.choice([2900, 3200, 3500]), r.choice([8, 10]), r.choice([300, 320, 350])),
                                        ('«Безлимит»', r.choice([4500, 4800, 5200]), None, None)],
         u=lambda r: r.randint(5, 18)),
    dict(intro='Оператор связи предлагает три тарифа для звонков. Абонент рассчитывает говорить {u} минут в месяц и выбирает самый дешёвый вариант.',
         unit='мин', rows=lambda r: [('«Мини»', r.choice([150, 190, 250]), r.choice([100, 150]), r.choice([2, 3])),
                                     ('«Разговор»', r.choice([350, 390, 450]), r.choice([300, 400]), r.choice([1, 2])),
                                     ('«Безлимит»', r.choice([590, 650, 700]), None, None)],
         u=lambda r: r.randint(12, 60) * 10),
    dict(intro='Сервис облачного хранения предлагает три тарифа. Семья собирается хранить {u} ГБ фотографий и выбирает самый дешёвый вариант.',
         unit='ГБ', rows=lambda r: [('«Базовый»', r.choice([99, 149]), r.choice([50, 100]), r.choice([2, 3])),
                                     ('«Семейный»', r.choice([249, 299]), r.choice([200, 250]), r.choice([1, 2])),
                                     ('«Про»', r.choice([549, 599, 699]), None, None)],
         u=lambda r: r.randint(60, 400)),
]


@proto('og05-plan-tariff', 'oge', 5, 'Выбор самого дешёвого тарифа при заданном потреблении',
       invariant='Несколько тарифов: абонентская плата с включённым объёмом и доплата за каждую единицу сверх; безлимитный тариф. Найти плату по самому дешёвому тарифу.',
       varies='Сюжет (интернет, абонемент, облако), цены, включённые объёмы, ожидаемое потребление.',
       answer_rule='Для каждого тарифа: плата + (потребление − включённое)·цену единицы, если потребление больше включённого; берём минимум.',
       fipi=r'(предлагает три тарифных плана|тарифный план).{0,400}Сколько рублей',
       mistakes=['забывают доплату сверх пакета', 'выбирают тариф с наименьшей абонентской платой'], svg=True,
       kim=KP(5, ['1.2', '8.1', '3.3'], [8, 14], 5))
def gen_og05_plan_tariff(r):
    pl = r.choice(PLANS)
    u = pl['u'](r)
    rows = pl['rows'](r)
    costs = []
    trow = [['Тариф', 'Абонентская плата, руб.', f'Включено, {pl["unit"]}', f'Сверх пакета, руб. за 1 {pl["unit"].replace("занятий", "занятие").replace("мин", "минуту")}']]
    for name, fee, inc, extra in rows:
        c = fee if inc is None else fee + max(0, u - inc) * extra
        costs.append(c)
        trow.append([name, str(fee), 'без ограничений' if inc is None else str(inc), '—' if extra is None else str(extra)])
    if len(set(costs)) < 3 or costs.index(min(costs)) == 0 and u <= rows[0][2]:
        return None
    ans = min(costs)
    q = pl['intro'].format(u=u) + ' Условия приведены в таблице. Сколько рублей придётся заплатить за месяц, если потребление окажется ровно таким, как ожидалось?'
    e = '; '.join(f'{rows[i][0]}: {costs[i]} руб' for i in range(3)) + f'. Наименьшая плата — {ans} руб.'
    svg = svg_table(trow, colw=[100, 170, 130, 190])
    return pcard(q, num(ans), e=e, svg=svg), lambda: ans == min(fee + (sp.Max(0, u - inc) * extra if inc is not None else 0) for _, fee, inc, extra in rows)


# ---------------------------------------------------------------- сюжет «план местности: дороги»

TRIPS = [
    dict(who='Лена с мамой', how='едут на машине', places=[('Сосновка', 'Сосновки', 'Сосновку'), ('Каменка', 'Каменки', 'Каменку'),
                                                             ('Озёрное', 'Озёрного', 'Озёрное'), ('Ягодное', 'Ягодного', 'Ягодное')],
         road=(('шоссе', 'по шоссе'), ('грунтовая дорога', 'по грунтовой дороге')), v=[(60, 30), (70, 35), (80, 40), (90, 45), (60, 40)], car=True),
    dict(who='Артём с отцом', how='едут на велосипедах', places=[('лагерь', 'лагеря', 'лагерь'), ('родник', 'родника', 'родник'),
                                                                   ('мельница', 'мельницы', 'мельницу'), ('водопад', 'водопада', 'водопад')],
         road=(('велодорожка', 'по велодорожке'), ('лесная тропа', 'по лесной тропе')), v=[(15, 10), (18, 12), (20, 10), (16, 12)], car=False),
    dict(who='Денис с папой', how='едут на машине', places=[('Кленовка', 'Кленовки', 'Кленовку'), ('Луговое', 'Лугового', 'Луговое'),
                                                             ('Ручьи', 'Ручьёв', 'Ручьи'), ('Высокое', 'Высокого', 'Высокое')],
         road=(('трасса', 'по трассе'), ('лесная дорога', 'по лесной дороге')), v=[(60, 30), (90, 45), (80, 40), (75, 30)], car=True),
    dict(who='Соня с дедушкой', how='едут на машине', places=[('Липки', 'Липок', 'Липки'), ('Бор', 'Бора', 'Бор'),
                                                                ('Заречье', 'Заречья', 'Заречье'), ('Дальний', 'Дальнего', 'Дальний')],
         road=(('асфальтовая дорога', 'по асфальтовой дороге'), ('просёлочная дорога', 'по просёлочной дороге')), v=[(60, 30), (75, 25), (80, 40), (90, 30)], car=True),
    dict(who='Туристы', how='идут на лыжах', places=[('база отдыха', 'базы отдыха', 'базу отдыха'), ('смотровая площадка', 'смотровой площадки', 'смотровую площадку'),
                                                   ('охотничий домик', 'охотничьего домика', 'охотничий домик'), ('турбаза', 'турбазы', 'турбазу')],
         road=(('накатанная лыжня', 'по лыжне'), ('снежная целина', 'по целине')), v=[(12, 6), (10, 5), (12, 8), (9, 6)], car=False),
]
MAPGEO = [(12, 16, 7), (12, 16, 11), (12, 9, 4), (8, 15, 9), (15, 20, 12), (6, 8, 0), (9, 12, 0), (12, 5, 0)]


def _map_block(r):
    ctx = r.choice(TRIPS)
    b_, a_, p_ = r.choice(MAPGEO)
    if p_ == 0:
        p_ = r.randint(1, a_ - 1)
        tri = False
    else:
        tri = True
    s = r.choice([1, 1, 2]) if a_ <= 16 else 1
    x0, y0 = 1, 1
    cols, rows = x0 + a_ + 2, y0 + b_ + 2
    q_ = r.randint(1, b_ - 1)
    S, V, C, W, T = (x0, y0), (x0 + p_, y0), (x0 + a_, y0), (x0 + a_, y0 + q_), (x0 + a_, y0 + b_)
    pl = ctx['places']
    digits = list(range(1, 5))
    r.shuffle(digits)
    vh, vd = r.choice(ctx['v'])
    (hw, hw_by), (dr, dr_by) = ctx['road']
    desc = (f'{ctx["who"]} {ctx["how"]}: старт — {pl[0][0]}, финиш — {pl[3][0]}. Сторона клетки на плане — {s} км. '
            f'Основная дорога ({hw}, сплошная линия) идёт от старта на восток мимо пункта «{pl[1][0]}», затем поворачивает на север, '
            f'проходит мимо пункта «{pl[2][0]}» и приводит к финишу. Кроме того, есть {dr} (пунктир) — прямо от старта к финишу'
            + (f', а также от пункта «{pl[1][0]}» к финишу.' if tri else '.'))
    names = [p[0] for p in pl]
    return dict(ctx=ctx, S=S, V=V, C=C, W=W, T=T, a=a_, b=b_, p=p_, q=q_, s=s, tri=tri, cols=cols, rows=rows, names=names, pl=pl,
                digits=digits, desc=desc, vh=vh, vd=vd, hw_by=hw_by, dr_by=dr_by)


def _map_svg(b):
    cell = min(22, 420 // max(b['cols'], b['rows']))
    W, H = b['cols'] * cell + 20, b['rows'] * cell + 20
    sx = lambda x: 10 + x * cell
    sy = lambda y: 10 + (b['rows'] - y) * cell
    g = ''.join(f'<line x1="{sx(i)}" y1="{sy(0)}" x2="{sx(i)}" y2="{sy(b["rows"])}"/>' for i in range(b['cols'] + 1))
    g += ''.join(f'<line x1="{sx(0)}" y1="{sy(j)}" x2="{sx(b["cols"])}" y2="{sy(j)}"/>' for j in range(b['rows'] + 1))
    out = f'<g stroke="{GRID}" stroke-width="1">{g}</g>'
    S, V, C, W_, T = b['S'], b['V'], b['C'], b['W'], b['T']
    out += f'<polyline points="{sx(S[0])},{sy(S[1])} {sx(C[0])},{sy(C[1])} {sx(T[0])},{sy(T[1])}" fill="none" stroke="{INK}" stroke-width="3"/>'
    dashes = [(S, T)] + ([(V, T)] if b['tri'] else [])
    out += ''.join(f'<line x1="{sx(p[0])}" y1="{sy(p[1])}" x2="{sx(q[0])}" y2="{sy(q[1])}" stroke="#9A6B3C" stroke-width="2.4" stroke-dasharray="7 5"/>' for p, q in dashes)
    for i, P in enumerate([S, V, W_, T]):
        dx = -16 if i in (0,) else 8
        dy = 18 if i in (0, 1) else -6
        out += f'<circle cx="{sx(P[0])}" cy="{sy(P[1])}" r="5" fill="{RED}"/><text x="{sx(P[0]) + dx}" y="{sy(P[1]) + dy}" font-size="15" font-weight="bold">{b["digits"][i]}</text>'
    return _svg(W, H, out)


KMAP = dict(kes=['7.5', '3.3'], kt=[8, 11])


@proto('og01-map-match', 'oge', 1, 'План местности: какими цифрами обозначены пункты',
       invariant='По описанию маршрута (сначала на восток мимо одного пункта, после поворота — мимо другого) определить цифры пунктов на плане.',
       varies='Сюжет (машина, велосипеды, лыжи), форма маршрута, нумерация.',
       answer_rule='Прослеживаем дорогу на плане от начального пункта и сопоставляем описанию.',
       fipi=r'какими цифрами на плане обозначены (деревни|населённые пункты)',
       mistakes=['путают направления (восток/север)', 'путают пункты на двух участках дороги'], svg=True, card_kind='match',
       kim=KP(1, ['7.1', '6.2'], [9, 10], 3, answer='соответствие'))
def gen_og01_map_match(r):
    b = _map_block(r)
    left = [{'id': LET[j], 't': nm} for j, nm in enumerate(b['names'])]
    right = [{'id': str(d), 't': f'цифра {d} на плане'} for d in range(1, 5)]
    a = {LET[j]: str(b['digits'][j]) for j in range(4)}
    q = b['desc'] + '\nПользуясь описанием, определите, какими цифрами на плане обозначены пункты.'
    e = '; '.join(f'{nm} — {b["digits"][j]}' for j, nm in enumerate(b['names'])) + '.'
    pts = [b['S'], b['V'], b['W'], b['T']]

    def chk():  # начало — самая юго-западная точка; конец — самая северная; второй — на горизонтальном участке
        order = [min(range(4), key=lambda i: pts[i][0] + pts[i][1]), [i for i in range(4) if pts[i][1] == pts[0][1] and pts[i] != pts[0]][0],
                 [i for i in range(4) if pts[i][0] == pts[3][0] and pts[i] != pts[3]][0], max(range(4), key=lambda i: pts[i][1])]
        return all(a[LET[j]] == str(b['digits'][order[j]]) for j in range(4))
    return pcard(q, a, e=e, k='match', o={'left': left, 'right': right}, svg=_map_svg(b)), chk


@proto('og02-map-road', 'oge', 2, 'План местности: расстояние по дороге',
       invariant='Длина пути по дороге, идущей по линиям сетки: сумма горизонтальных и вертикальных участков × сторона клетки.',
       varies='Сюжет, план, начальный и конечный пункты.',
       answer_rule='Считаем клетки вдоль дороги и умножаем на сторону клетки.',
       fipi=r'Найдите расстояние от .{3,30} по шоссе|Сколько километров проедут',
       mistakes=['считают по прямой вместо дороги', 'забывают масштаб клетки'], svg=True, kim=KP(2, **KMAP, minutes=3))
def gen_og02_map_road(r):
    b = _map_block(r)
    P = {0: b['S'], 1: b['V'], 2: b['W'], 3: b['T']}
    along = lambda A, B: abs(A[0] - B[0]) + abs(A[1] - B[1])
    pairs = [(0, 3), (0, 2), (1, 3), (1, 2), (0, 1)]
    i, j = r.choice(pairs)
    via = lambda A, B: along(A, b['C']) + along(b['C'], B) if A[1] == b['S'][1] and B[0] == b['C'][0] else along(A, B)
    d = via(P[i], P[j]) * b['s']
    pl = b['pl']
    q = b['desc'] + f'\nСколько километров составляет путь {b["hw_by"]} от пункта «{pl[i][0]}» до пункта «{pl[j][0]}»?'
    e = f'По клеткам: {via(P[i], P[j])} кл. × {b["s"]} км = {d} км.'
    return pcard(q, num(d), e=e, svg=_map_svg(b)), lambda: d == (sp.Abs(P[i][0] - b['C'][0]) + sp.Abs(P[i][1] - b['C'][1]) + sp.Abs(P[j][0] - b['C'][0]) + sp.Abs(P[j][1] - b['C'][1])) * b['s'] \
        if (P[i][1] == b['S'][1] and P[j][0] == b['C'][0]) else d == (sp.Abs(P[i][0] - P[j][0]) + sp.Abs(P[i][1] - P[j][1])) * b['s']


@proto('og03-map-straight', 'oge', 3, 'План местности: расстояние по прямой',
       invariant='Расстояние по прямой между пунктами — гипотенуза прямоугольного треугольника с катетами по клеткам.',
       varies='Сюжет, план (пифагоровы тройки), пара пунктов, сторона клетки.',
       answer_rule='Катеты в клетках → теорема Пифагора → умножаем на сторону клетки.',
       fipi=r'по прямой\. Ответ дайте в километрах',
       mistakes=['складывают катеты', 'забывают масштаб'], svg=True, kim=KP(3, ['7.2', '7.5'], [11], 3))
def gen_og03_map_straight(r):
    b = _map_block(r)
    cand = [(0, 3)] + ([(1, 3)] if b['tri'] else [])
    i, j = r.choice(cand)
    P = {0: b['S'], 1: b['V'], 3: b['T']}
    dx, dy = abs(P[i][0] - P[j][0]), abs(P[i][1] - P[j][1])
    h = math.isqrt(dx * dx + dy * dy)
    if h * h != dx * dx + dy * dy:
        return None
    d = h * b['s']
    nm = b['names']
    q = b['desc'] + f'\nНайдите расстояние по прямой между пунктами «{nm[i]}» и «{nm[j]}». Ответ дайте в километрах.'
    e = f'Катеты: {dx * b["s"]} и {dy * b["s"]} км; √({(dx * b["s"]) ** 2} + {(dy * b["s"]) ** 2}) = {d} км.'
    return pcard(q, num(d), e=e, svg=_map_svg(b)), lambda: same(num(d), sp.sqrt((dx * b['s']) ** 2 + (dy * b['s']) ** 2))


@proto('og04-map-time', 'oge', 4, 'План местности: время в пути по маршруту',
       invariant='Маршрут состоит из участков с разной скоростью; время = сумма (длина участка / скорость), перевести в минуты.',
       varies='Сюжет, скорости по дороге и по бездорожью, выбранный маршрут.',
       answer_rule='Длины участков из плана (клетки, Пифагор), делим на соответствующие скорости, складываем, ×60.',
       fipi=r'Сколько минут затратят на дорогу',
       mistakes=['берут одну скорость для всего пути', 'забывают перевести часы в минуты'], svg=True, kim=KP(4, ['3.3', '7.5'], [8, 11], 5))
def gen_og04_map_time(r):
    b = _map_block(r)
    s, vh, vd = b['s'], b['vh'], b['vd']
    routes = [(f'всё время {b["hw_by"]}', [((b['a'] + b['b']) * s, vh)])]
    routes.append((f'напрямик {b["dr_by"]}', [(math.hypot(b['a'], b['b']) * s, vd)]))
    if b['tri']:
        routes.append((f'сначала {b["hw_by"]} до пункта «{b["names"][1]}», а затем {b["dr_by"]}',
                       [(b['p'] * s, vh), (math.hypot(b['a'] - b['p'], b['b']) * s, vd)]))
    name, legs = r.choice(routes)
    if any(abs(L - round(L)) > 1e-9 for L, _ in legs):
        return None
    legs = [(int(round(L)), v) for L, v in legs]
    t = sum(F(L, v) for L, v in legs) * 60
    if t.denominator != 1:
        return None
    q = (b['desc'] + f' {b["hw_by"].capitalize()} они движутся со скоростью {vh} км/ч, {b["dr_by"]} — {vd} км/ч.\n'
         f'Сколько минут займёт путь от старта до финиша, если двигаться {name}?')
    e = ' + '.join(f'{L}/{v}' for L, v in legs) + f' ч = {t} мин.'
    return pcard(q, num(t), e=e, svg=_map_svg(b)), lambda: same(num(t), sum(sp.Rational(L, v) for L, v in legs) * 60)


@proto('og05-map-fuel', 'oge', 5, 'План местности: расход топлива на бездорожье',
       invariant='Два маршрута требуют одинакового количества бензина; по известному расходу на шоссе найти расход на грунтовой дороге (л на 100 км).',
       varies='Сюжет (машина), план, расход на шоссе, пара маршрутов.',
       answer_rule='Приравниваем: расход₁·длина шоссе = расход₁·(шоссейная часть) + расход₂·(грунтовая часть); выражаем расход₂.',
       fipi=r'расходует .{0,20}литра бензина на 100 км',
       mistakes=['делят не на ту длину', 'забывают шоссейный участок второго маршрута'], svg=True, maxdec=2,
       kim=KP(5, ['3.3', '7.5'], [8, 11], 6))
def gen_og05_map_fuel(r):
    b = _map_block(r)
    if not b['ctx']['car']:
        return None
    s = b['s']
    c1 = F(r.randint(50, 90), 10)
    L1 = (b['a'] + b['b']) * s
    use_tri = b['tri'] and r.random() < 0.6
    if use_tri:
        hw = b['p'] * s
        dirt = math.isqrt((b['a'] - b['p']) ** 2 + b['b'] ** 2) * s
        second = f'до пункта «{b["names"][1]}» {b["hw_by"]}, а дальше {b["dr_by"]}'
    else:
        hw = 0
        dh = math.hypot(b['a'], b['b'])
        if abs(dh - round(dh)) > 1e-9:
            return None
        dirt = int(round(dh)) * s
        second = f'напрямик {b["dr_by"]}'
    c2 = c1 * (L1 - hw) / dirt
    if not nice(c2, 1):
        return None
    q = (b['desc'] + f'\n{b["hw_by"].capitalize()} машина расходует {tnum(c1)} л бензина на 100 км. Путь от старта до финиша {b["hw_by"]} и путь {second} '
         f'требуют одинакового количества бензина. Сколько литров бензина на 100 км машина расходует, когда едет {b["dr_by"]}?')
    e = (f'{tnum(c1)}·{L1} = {tnum(c1)}·{hw} + x·{dirt}' if hw else f'{tnum(c1)}·{L1} = x·{dirt}') + f' ⇒ x = {tnum(c2)}.'
    x = sp.Symbol('x')
    return pcard(q, num(c2), e=e, svg=_map_svg(b)), lambda: same(num(c2), sp.solve(sp.Eq(R(c1) * L1, R(c1) * hw + x * dirt), x)[0])


SHOPS = [
    [('молоко (1 л)', 60, 95, ('л', 'л', 'л'), 'молока'), ('хлеб (1 батон)', 35, 60, ('батон', 'батона', 'батонов'), 'хлеба'),
     ('сыр (1 кг)', 550, 800, ('кг', 'кг', 'кг'), 'сыра'), ('яблоки (1 кг)', 90, 160, ('кг', 'кг', 'кг'), 'яблок'),
     ('гречка (1 кг)', 70, 120, ('кг', 'кг', 'кг'), 'гречки')],
    [('вода (бутыль 5 л)', 90, 150, ('бутыль', 'бутыли', 'бутылей'), 'воды'), ('печенье (1 пачка)', 60, 110, ('пачка', 'пачки', 'пачек'), 'печенья'),
     ('чай (1 пачка)', 110, 200, ('пачка', 'пачки', 'пачек'), 'чая'), ('сахар (1 кг)', 60, 95, ('кг', 'кг', 'кг'), 'сахара'),
     ('мёд (1 банка)', 300, 480, ('банка', 'банки', 'банок'), 'мёда')],
]


@proto('og05-map-shop', 'oge', 5, 'Выбор магазина с самой дешёвой покупкой',
       invariant='Таблица цен в четырёх магазинах; стоимость набора (количества × цены) в каждом, выбрать наименьшую.',
       varies='Товары, цены, количества в наборе, названия пунктов.',
       answer_rule='Для каждого магазина считаем сумму количеств × цен, берём минимум.',
       fipi=r'В каком магазине такой набор продуктов будет стоить дешевле всего',
       mistakes=['сравнивают только одну позицию', 'забывают умножить на количество'], svg=True, lim=100000,
       kim=KP(5, ['1.3', '8.1'], [8, 14], 5))
def gen_og05_map_shop(r):
    b = _map_block(r)
    items = r.sample(r.choice(SHOPS), 4)
    prices = [[r.randint(it[1] // 5, it[2] // 5) * 5 for it in items] for _ in range(4)]
    qty = [r.randint(1, 4) for _ in range(3)] + [0]
    r.shuffle(qty)
    tot = [sum(p * k for p, k in zip(pr, qty)) for pr in prices]
    if sorted(tot)[0] == sorted(tot)[1]:
        return None
    ans = min(tot)
    rows = [['Товар'] + [f'п. {j + 1}' for j in range(4)]]
    for i, it in enumerate(items):
        rows.append([it[0]] + [str(prices[j][i]) for j in range(4)])
    parts = [f'{k} {plural(k, *items[i][3])} {items[i][4]}' for i, k in enumerate(qty) if k]
    buy = ', '.join(parts[:-1]) + ' и ' + parts[-1]
    q = (f'В каждом из четырёх пунктов маршрута ({", ".join("«" + n + "»" for n in b["names"])} — в таблице п. 1–4 в этом порядке) есть магазин. '
         f'Цены (в рублях) приведены в таблице. {b["ctx"]["who"]} хотят купить {buy}. В каком магазине такой набор обойдётся дешевле всего? '
         'В ответ запишите стоимость набора в этом магазине в рублях.')
    q = q.replace('Группа туристов хотят', 'Туристы хотят')
    e = '; '.join(f'п. {j + 1}: {tot[j]}' for j in range(4)) + f'. Дешевле всего — {ans} руб.'
    svg = svg_table(rows, colw=[170, 60, 60, 60, 60])
    return pcard(q, num(ans), e=e, svg=svg), lambda: ans == min(sum(sp.Integer(p) * k for p, k in zip(pr, qty)) for pr in prices)


# ---------------------------------------------------------------- сюжет «подписка с пакетом минут» (диаграмма по месяцам)

MONTHS = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']
MONTHS_P = ['январе', 'феврале', 'марте', 'апреле', 'мае', 'июне', 'июле', 'августе', 'сентябре', 'октябре', 'ноябре', 'декабре']
MONTHS_G = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
SUBS = [
    dict(who='Кирилл пользуется каршерингом по подписке', what='минут аренды', one='минута', fee=(990, 1490, 1990), inc=(200, 300, 400), extra=(8, 9, 10, 12), rng=(80, 600), step=10),
    dict(who='Марина ездит на прокатных электросамокатах по месячной подписке', what='минут поездок', one='минута', fee=(299, 399, 499), inc=(150, 200, 300), extra=(3, 4, 5), rng=(40, 420), step=10),
    dict(who='Олег берёт напрокат велосипеды городской сети по месячной подписке', what='минут проката', one='минута', fee=(349, 449, 549), inc=(200, 300, 400), extra=(2, 3, 4), rng=(60, 600), step=10),
    dict(who='Семья смотрит фильмы в онлайн-кинотеатре по подписке', what='часов просмотра', one='час', fee=(249, 299, 399), inc=(30, 40, 50), extra=(5, 6, 8), rng=(10, 90), step=1),
]


def svg_month_bars(vals, width=380, height=230, limit=None):
    """Столбчатая диаграмма по месяцам с подписями значений над столбцами; limit — горизонтальная линия пакета."""
    vmax = max(vals + ([limit] if limit else []))
    step = next(s_ for s_ in (5, 10, 20, 25, 50, 100, 200) if vmax / s_ <= 8)
    top = (vmax // step + 1) * step
    L, B, T = 40, 26, 14
    ph, pw = height - B - T, width - L - 8
    sy = lambda v: T + (top - v) / top * ph
    bw = pw / 12
    out = ''
    v = 0
    while v <= top:
        out += f'<line x1="{L}" y1="{sy(v):.1f}" x2="{width - 8}" y2="{sy(v):.1f}" stroke="{GRID}"/><text x="{L - 5}" y="{sy(v) + 4:.1f}" text-anchor="end" font-size="10">{v}</text>'
        v += step
    for i, val in enumerate(vals):
        x = L + i * bw
        out += f'<rect x="{x + bw * 0.15:.1f}" y="{sy(val):.1f}" width="{bw * 0.7:.1f}" height="{sy(0) - sy(val):.1f}" fill="{BLUE}"/>'
        out += f'<text x="{x + bw / 2:.1f}" y="{sy(val) - 3:.1f}" text-anchor="middle" font-size="9">{val}</text>'
        out += f'<text x="{x + bw / 2:.1f}" y="{height - 8}" text-anchor="middle" font-size="10">{i + 1}</text>'
    if limit:
        out += f'<line x1="{L}" y1="{sy(limit):.1f}" x2="{width - 8}" y2="{sy(limit):.1f}" stroke="{RED}" stroke-width="1.6" stroke-dasharray="6 4"/>'
    return _svg(width, height, out)


def _sub_block(r):
    c = r.choice(SUBS)
    fee, inc, ex = r.choice(c['fee']), r.choice(c['inc']), r.choice(c['extra'])
    lo, hi = c['rng']
    st = c['step']
    v = r.randint(lo, (lo + hi) // 2) // st * st
    vals = []
    for _ in range(12):
        vals.append(v)
        v = max(lo, min(hi, v + r.choice([-1, 1]) * r.randint(1, 6) * st * (1 if st > 1 else 2)))
    if not any(v > inc for v in vals) or all(v > inc for v in vals):
        return None
    intro = (f'{c["who"]}. Подписка стоит {fee} руб. в месяц и включает {inc} {c["what"]}; {"каждая минута" if c["one"] == "минута" else "каждый час"} сверх пакета оплачивается отдельно — {ex} руб. '
             f'На диаграмме показано, сколько {c["what"]} было израсходовано в каждом месяце прошлого года (номера месяцев под столбцами; пунктир — объём пакета).')
    return dict(c=c, fee=fee, inc=inc, ex=ex, vals=vals, intro=intro, svg=svg_month_bars(vals, limit=inc))


def _qty(c, n, gen=False):
    """«41 час просмотра», «45 минут аренды»; gen=True — родительный после «до»: «до 41 часа просмотра»."""
    rest = c['what'].split(' ', 1)[1]
    if c['one'] == 'минута':
        w = plural(n, 'минуты', 'минут', 'минут') if gen else plural(n, 'минута', 'минуты', 'минут')
    else:
        w = plural(n, 'часа', 'часов', 'часов') if gen else plural(n, 'час', 'часа', 'часов')
    return f'{n} {w} {rest}'


def _sub_cost(b, m):
    return b['fee'] + max(0, b['vals'][m] - b['inc']) * b['ex']


@proto('og01-sub-months', 'oge', 1, 'Диаграмма по месяцам: каким месяцам соответствуют значения',
       invariant='По столбчатой диаграмме найти номера месяцев, в которые израсходовано указанное количество.',
       varies='Сюжет (каршеринг, самокаты, онлайн-кинотеатр), значения по месяцам, выбранные значения.',
       answer_rule='Находим столбец с нужной высотой (подписью) и записываем номер месяца.',
       fipi=r'Определите, какие месяцы соответствуют указанному',
       mistakes=['путают номер месяца со значением'], svg=True, card_kind='match',
       kim=KP(1, ['8.1'], [14], 3, answer='соответствие'))
def gen_og01_sub_months(r):
    b = _sub_block(r)
    if not b:
        return None
    uniq = [m for m in range(12) if b['vals'].count(b['vals'][m]) == 1]
    if len(uniq) < 4:
        return None
    ms = r.sample(uniq, 4)
    left = [{'id': LET[j], 't': _qty(b['c'], b['vals'][m])} for j, m in enumerate(ms)]
    right = [{'id': str(i + 1), 't': MONTHS[i]} for i in range(12)]
    a = {LET[j]: str(m + 1) for j, m in enumerate(ms)}
    q = b['intro'] + f'\nОпределите, какие месяцы соответствуют указанному ниже количеству {b["c"]["what"]}.'
    e = '; '.join(f'{b["vals"][m]} — {MONTHS[m]}' for m in ms) + '.'
    return pcard(q, a, e=e, k='match', o={'left': left, 'right': right}, svg=b['svg']), lambda: all(b['vals'][int(a[LET[j]]) - 1] == b['vals'][m] and b['vals'].count(b['vals'][m]) == 1 for j, m in enumerate(ms))


@proto('og02-sub-cost', 'oge', 2, 'Подписка с пакетом: плата за месяц',
       invariant='Плата = абонентская плата + (расход − пакет) × цена единицы, если расход больше пакета.',
       varies='Сюжет, месяц, условия подписки.',
       answer_rule='Смотрим расход в месяце по диаграмме, сравниваем с пакетом и считаем доплату.',
       fipi=r'Сколько рублей потратил абонент на услуги связи',
       mistakes=['берут весь расход, а не превышение', 'забывают абонентскую плату'], svg=True, kim=KP(2, ['8.1', '1.2'], [8, 14], 3))
def gen_og02_sub_cost(r):
    b = _sub_block(r)
    if not b:
        return None
    over = [m for m in range(12) if b['vals'][m] > b['inc']]
    m = r.choice(over) if r.random() < 0.8 else r.randrange(12)
    ans = _sub_cost(b, m)
    q = b['intro'] + f'\nСколько рублей было заплачено за подписку и доплаты в {MONTHS_P[m]}?'
    e = f'Расход {b["vals"][m]}, пакет {b["inc"]}: ' + (f'{b["fee"]} + ({b["vals"][m]} − {b["inc"]})·{b["ex"]} = {ans} руб.' if b['vals'][m] > b['inc'] else f'доплаты нет, {ans} руб.')
    return pcard(q, num(ans), e=e, svg=b['svg']), lambda: ans == b['fee'] + sp.Max(0, b['vals'][m] - b['inc']) * b['ex']


@proto('og03-sub-count', 'oge', 3, 'Диаграмма: сколько месяцев выполнено условие',
       invariant='Подсчитать месяцы, в которые расход превысил пакет (не превысил, оказался в заданных границах).',
       varies='Сюжет, данные, условие.',
       answer_rule='Сравниваем каждый столбец с линией пакета (границей) и считаем подходящие.',
       fipi=r'Сколько месяцев в .{0,30}году (абонент|расходы)|Какое наименьшее количество минут|Какой наименьший трафик',
       mistakes=['считают «равно» как превышение'], svg=True, kim=KP(3, ['8.1'], [14], 3))
def gen_og03_sub_count(r):
    b = _sub_block(r)
    if not b:
        return None
    kind = r.randrange(5)
    if kind == 3:
        mx = r.random() < 0.5
        ans = max(b['vals']) if mx else min(b['vals'])
        q = b['intro'] + f'\nКакое {"наибольшее" if mx else "наименьшее"} количество {b["c"]["what"]} было израсходовано за месяц в прошлом году?'
        return pcard(q, num(ans), e=f'По диаграмме: {ans}.', svg=b['svg']), lambda: ans == (max if mx else min)(b['vals'])
    if kind == 4:
        ans = sum(v <= b['inc'] for v in b['vals'])
        q = b['intro'] + f'\nВ течение скольких месяцев прошлого года плата за месяц составила ровно {b["fee"]} руб.?'
        return pcard(q, num(ans), e=f'Ровно {b["fee"]} руб. — в месяцы без превышения пакета: {ans}.', svg=b['svg']), lambda: ans == len([m for m in range(12) if _sub_cost(b, m) == b['fee']])
    if kind == 0:
        ans = sum(v > b['inc'] for v in b['vals'])
        ask = f'В течение скольких месяцев израсходованный объём превысил пакет?'
        f = lambda v: v > b['inc']
    elif kind == 1:
        ans = sum(v <= b['inc'] for v in b['vals'])
        ask = f'Сколько месяцев в году обошлись без доплат (объём не превысил пакет)?'
        f = lambda v: v <= b['inc']
    else:
        lo_ = r.choice(sorted(b['vals'])[2:6])
        hi_ = r.choice(sorted(b['vals'])[6:10])
        ans = sum(lo_ <= v <= hi_ for v in b['vals'])
        ask = f'Сколько было месяцев, в которых израсходовано от {lo_} до {_qty(b["c"], hi_, gen=True)} включительно?'
        f = lambda v: lo_ <= v <= hi_
    q = b['intro'] + '\n' + ask
    return pcard(q, num(ans), e=f'Подходящих месяцев: {ans}.', svg=b['svg']), lambda: ans == len([v for v in b['vals'] if f(v)])


@proto('og04-sub-percent', 'oge', 4, 'Диаграмма: на сколько процентов изменился расход',
       invariant='Процент изменения расхода между двумя месяцами (или изменения цены подписки).',
       varies='Сюжет, пара месяцев, рост или снижение.',
       answer_rule='(новое − старое)/старое · 100%.',
       fipi=r'На сколько процентов (увеличился|уменьшился|выросла|повысилась)|Известно, что в .{0,15}году абонентская плата',
       mistakes=['делят на новое значение'], svg=True, maxdec=1, kim=KP(4, ['1.2', '8.1'], [8, 14], 4))
def gen_og04_sub_percent(r):
    b = _sub_block(r)
    if not b:
        return None
    if r.random() < 0.7:
        m = r.randrange(11)
        v0 = b['vals'][m]
        ok = [p_ for p_ in (5, 10, 15, 20, 25, 30, 40, 50, 60, 75) if (v0 * p_) % (100 * b['c']['step']) == 0]
        if not ok:
            return None
        p_ = r.choice(ok)
        v1 = v0 + r.choice([1, -1]) * v0 * p_ // 100
        if v1 <= 0:
            return None
        b['vals'][m + 1] = v1
        b['svg'] = svg_month_bars(b['vals'], limit=b['inc'])
        pct = F(abs(v1 - v0) * 100, v0)
        q = b['intro'] + f'\nНа сколько процентов {"увеличился" if v1 > v0 else "уменьшился"} расход в {MONTHS_P[m + 1]} по сравнению с {"январём" if m == 0 else MONTHS_P[m].replace("е", "ем", 0)}?'
        q = q.replace(f'по сравнению с {MONTHS_P[m]}', f'по сравнению с {["январём", "февралём", "мартом", "апрелем", "маем", "июнем", "июлем", "августом", "сентябрём", "октябрём", "ноябрём"][m]}')
        e = f'{v0} → {v1}: |{v1} − {v0}| : {v0} · 100% = {tnum(pct)}%.'
        chk = lambda: same(num(pct), sp.Abs(sp.Rational(v1, v0) - 1) * 100)
    elif r.random() < 0.5:
        p_ = r.choice([10, 20, 25, 30, 40, 50, 60, 75])
        up = r.random() < 0.6
        old = r.choice([200, 240, 280, 300, 320, 360, 400, 480, 500, 600, 800, 1000, 1200])
        new = F(old * (100 + p_ if up else 100 - p_), 100)
        if new.denominator != 1:
            return None
        pct = F(old)
        q = b['intro'] + f'\nИзвестно, что по сравнению с позапрошлым годом подписка {"подорожала" if up else "подешевела"} на {p_}% и стоила в прошлом году {new} руб. в месяц. Сколько рублей стоила подписка позапрошлым годом?'
        e = f'{new} : {tnum(F(100 + p_ if up else 100 - p_, 100))} = {old} руб.'
        chk = lambda: same(num(pct), R(new) / (1 + (1 if up else -1) * sp.Rational(p_, 100)))
        b['fee_note'] = True
    else:
        new = b['fee'] + r.choice([10, 20, 30, 40, 50, 60, 100, 150]) * (1 if b['fee'] > 300 else 1)
        pct = F((new - b['fee']) * 100, b['fee'])
        if not nice(pct, 1):
            return None
        q = b['intro'] + f'\nВ новом году подписка подорожала и стала стоить {new} руб. в месяц. На сколько процентов выросла её цена?'
        e = f'({new} − {b["fee"]}) : {b["fee"]} · 100% = {tnum(pct)}%.'
        chk = lambda: same(num(pct), (sp.Rational(new, b['fee']) - 1) * 100)
    return pcard(q, num(pct), e=e, svg=b['svg']), chk


@proto('og05-sub-switch', 'oge', 5, 'Подписка: выгоднее ли другой тариф за год',
       invariant='По расходу за 12 месяцев посчитать годовую плату по текущей и по новой подписке; найти экономию (или годовую плату по выгодному тарифу).',
       varies='Сюжет, условия новой подписки, данные диаграммы.',
       answer_rule='Для каждого месяца: плата + доплата за превышение; суммируем за год для обоих тарифов и сравниваем.',
       fipi=r'Перейдёт ли абонент на новый тариф',
       mistakes=['считают только абонентскую плату', 'забывают месяцы без превышения'], svg=True, lim=10 ** 6,
       kim=KP(5, ['3.3', '8.1', '1.2'], [8, 14], 7))
def gen_og05_sub_switch(r):
    b = _sub_block(r)
    if not b:
        return None
    fee2 = b['fee'] + r.choice([100, 200, 300, 500]) if b['fee'] > 400 else b['fee'] + r.choice([50, 100, 150])
    inc2 = b['inc'] + r.choice([50, 100, 150, 200]) * (1 if b['c']['step'] == 10 else 0) + (r.choice([10, 20, 30]) if b['c']['step'] == 1 else 0)
    ex2 = b['ex'] + r.choice([-1, 0, 1, 2])
    y1 = sum(_sub_cost(b, m) for m in range(12))
    y2 = sum(fee2 + max(0, v - inc2) * ex2 for v in b['vals'])
    if y1 == y2:
        return None
    ask_diff = r.random() < 0.5
    ans = abs(y1 - y2) if ask_diff else min(y1, y2)
    q = (b['intro'] + f'\nВ конце года предложили другую подписку: {fee2} руб. в месяц, в неё входит {inc2} {b["c"]["what"]}, {"каждая минута" if b["c"]["one"] == "минута" else "каждый час"} сверх пакета — {ex2} руб. '
         + ('На сколько рублей за прошлый год отличались бы расходы по новой подписке от фактических?' if ask_diff else
            'Посчитайте, сколько стоил бы прошлый год по каждой подписке, и запишите в ответ наименьшую из этих сумм (в рублях).'))
    e = f'Фактически за год: {y1} руб.; по новой подписке: {y2} руб.'
    return pcard(q, num(ans), e=e, svg=b['svg']), lambda: ans == (abs(y1 - y2) if ask_diff else min(y1, y2)) and y1 == sum(b['fee'] + sp.Max(0, v - b['inc']) * b['ex'] for v in b['vals'])


# ---------------------------------------------------------------- сюжет «выбор печи (камина) по объёму помещения»

STOVES = [
    dict(room='гостиной загородного дома', thing='камин', things='камины', obj='камина', inst_w='устройство дымохода', inst_e='подвод отдельной электролинии'),
    dict(room='столярной мастерской', thing='отопительную печь', things='печи', obj='печи', inst_w='монтаж дымохода', inst_e='прокладка силового кабеля'),
    dict(room='веранды на даче', thing='печь-камин', things='печи-камины', obj='печи-камина', inst_w='дымоход с защитным экраном', inst_e='установка силовой розетки'),
    dict(room='гаражной мастерской', thing='обогреватель', things='обогреватели', obj='обогревателя', inst_w='монтаж дымохода', inst_e='прокладка электропроводки'),
]


def _stove_block(r):
    c = r.choice(STOVES)
    L = F(r.randint(20, 60), 10)
    Wd = F(r.randint(20, 50), 10)
    Hh = F(r.choice([22, 24, 25, 26, 27, 28, 30]), 10)
    V = L * Wd * Hh
    if not nice(V, 3) or V > 80:
        return None
    rows = [['№', 'Тип', 'Объём помещения, м³', 'Масса, кг', 'Цена, руб.']]
    models = []
    masses = r.sample(range(30, 90), 4)
    lo_fit = max(4, int(V) - r.randint(2, 6))
    bands = [(lo_fit, int(V) + r.randint(2, 10)), (lo_fit + r.randint(0, 3), int(V) + r.randint(1, 8))]
    types = ['дровяной', 'электрический'] if r.random() < 0.5 else ['электрический', 'дровяной']
    for k in range(4):
        tp = types[k % 2]
        if k < 2:
            lo, hi = bands[k]
        else:
            lo, hi = (int(V) + r.randint(2, 8), int(V) + r.randint(12, 25)) if r.random() < 0.5 else (max(2, int(V) - r.randint(20, 30)), int(V) - r.randint(2, 6))
            if hi <= lo:
                return None
        price = r.randint(150, 600) * 100
        models.append(dict(n=k + 1, tp=tp, lo=lo, hi=hi, m=masses[k], price=price))
    r.shuffle(models)
    for i, m in enumerate(models):
        m['n'] = i + 1
        rows.append([str(i + 1), m['tp'], f'{m["lo"]}–{m["hi"]}', str(m['m']), money(m["price"])])
    fit = [m for m in models if m['lo'] <= V <= m['hi']]
    if sorted(m['tp'] for m in fit) != ['дровяной', 'электрический']:
        return None
    iw, ie = r.randint(10, 40) * 500, r.randint(4, 20) * 500
    intro = (f'Для {c["room"]} выбирают {c["thing"]}. Размеры помещения: длина {tnum(L)} м, ширина {tnum(Wd)} м, высота {tnum(Hh)} м. '
             f'Характеристики подходящих моделей приведены в таблице; модель годится, если объём помещения попадает в указанный диапазон. '
             f'Кроме цены самой модели, нужно оплатить установку: для дровяной — {c["inst_w"]} ({money(iw)} руб.), для электрической — {c["inst_e"]} ({money(ie)} руб.).')
    return dict(c=c, L=L, W=Wd, H=Hh, V=V, models=models, fit=fit, iw=iw, ie=ie, intro=intro, svg=svg_table(rows, colw=[30, 110, 150, 80, 90]))


@proto('og01-stove-match', 'oge', 1, 'Выбор печи: соответствие характеристик и номеров моделей',
       invariant='По таблице моделей сопоставить указанные массы (или цены) номерам моделей.',
       varies='Сюжет (камин, печь, обогреватель), таблица, спрашиваемая характеристика.',
       answer_rule='Находим в таблице строку с нужным значением и записываем номер модели.',
       fipi=r'Установите соответствие между (массами|стоимостями) и номерами печей',
       mistakes=['читают соседнюю строку'], svg=True, card_kind='match', kim=KP(1, ['8.1'], [14], 2, answer='соответствие'))
def gen_og01_stove_match(r):
    b = _stove_block(r)
    if not b:
        return None
    key = r.choice(['m', 'price'])
    ms = r.sample(b['models'], 3)
    lab = (lambda m: f'{m["m"]} кг') if key == 'm' else (lambda m: f'{money(m["price"])} руб.')
    left = [{'id': LET[j], 't': lab(m)} for j, m in enumerate(ms)]
    right = [{'id': str(i + 1), 't': f'модель № {i + 1}'} for i in range(4)]
    a = {LET[j]: str(m['n']) for j, m in enumerate(ms)}
    q = b['intro'] + f'\nУстановите соответствие между {"массами" if key == "m" else "ценами"} и номерами моделей.'
    e = '; '.join(f'{lab(m)} — № {m["n"]}' for m in ms) + '.'
    return pcard(q, a, e=e, k='match', o={'left': left, 'right': right}, svg=b['svg']), lambda: all(
        [mm for mm in b['models'] if mm[key] == m[key]][0]['n'] == int(a[LET[j]]) for j, m in enumerate(ms))


@proto('og02-stove-volume', 'oge', 2, 'Выбор печи: объём (площадь) помещения',
       invariant='Объём помещения — произведение длины, ширины и высоты (площадь пола — длины на ширину).',
       varies='Сюжет, размеры (десятые доли метра), спрашиваемая величина.',
       answer_rule='V = a·b·h, S = a·b.',
       fipi=r'Найдите (объём|площадь пола) парного отделения',
       mistakes=['забывают высоту', 'ошибаются в умножении десятичных'], svg=True, maxdec=3, kim=KP(2, ['7.5', '1.2'], [11], 3))
def gen_og02_stove_volume(r):
    b = _stove_block(r)
    if not b:
        return None
    if r.random() < 0.6:
        ans = b['V']
        q = b['intro'] + '\nНайдите объём помещения. Ответ дайте в кубических метрах.'
        e = f'{tnum(b["L"])}·{tnum(b["W"])}·{tnum(b["H"])} = {tnum(ans)} м³.'
        chk = lambda: same(num(ans), R(b['L']) * R(b['W']) * R(b['H']))
    else:
        ans = b['L'] * b['W']
        q = b['intro'] + '\nНайдите площадь пола помещения. Ответ дайте в квадратных метрах.'
        e = f'{tnum(b["L"])}·{tnum(b["W"])} = {tnum(ans)} м².'
        chk = lambda: same(num(ans), R(b['L']) * R(b['W']))
    return pcard(q, num(ans), e=e, svg=b['svg']), chk


@proto('og03-stove-cheaper', 'oge', 3, 'Выбор печи: на сколько дешевле подходящая модель с учётом установки',
       invariant='Отобрать модели, подходящие по объёму помещения; сравнить полную стоимость (цена + установка) дровяной и электрической.',
       varies='Сюжет, таблица моделей, стоимость установки.',
       answer_rule='Считаем объём, находим подходящие модели, к цене прибавляем установку, находим разность.',
       fipi=r'обойдётся (дешевле|дороже) .{0,40}(с учётом|без учёта) установки',
       mistakes=['не проверяют диапазон объёма', 'забывают стоимость установки'], svg=True, lim=10 ** 6,
       kim=KP(3, ['1.2', '3.3', '8.1'], [8, 14], 5))
def gen_og03_stove_cheaper(r):
    b = _stove_block(r)
    if not b:
        return None
    w = [m for m in b['fit'] if m['tp'] == 'дровяной'][0]
    el = [m for m in b['fit'] if m['tp'] == 'электрический'][0]
    noinst = r.random() < 0.3
    tw, te = w['price'] + (0 if noinst else b['iw']), el['price'] + (0 if noinst else b['ie'])
    if tw == te:
        return None
    ans = abs(tw - te)
    cheap = 'дровяная' if tw < te else 'электрическая'
    dear = 'электрическая' if cheap == 'дровяная' else 'дровяная'
    gen = {'дровяная': 'дровяной', 'электрическая': 'электрической'}
    if r.random() < 0.5:
        q = b['intro'] + f'\nНа сколько рублей подходящая по объёму {cheap} модель {"без учёта" if noinst else "вместе с"} установк{"и" if noinst else "ой"} обойдётся дешевле подходящей {gen[dear]}?'
    else:
        q = b['intro'] + f'\nНа сколько рублей подходящая по объёму {dear} модель {"без учёта" if noinst else "вместе с"} установк{"и" if noinst else "ой"} обойдётся дороже подходящей {gen[cheap]}?'
    e = (f'V = {tnum(b["V"])} м³; подходят дровяная № {w["n"]} и электрическая № {el["n"]}; ' +
         (f'цены {w["price"]} и {el["price"]}' if noinst else f'{w["price"]} + {b["iw"]} = {tw}, {el["price"]} + {b["ie"]} = {te}') + f'; разница {ans} руб.')
    def chk():  # заново отбираем модели по объёму (sympy) и сравниваем полные стоимости
        V = R(b['L']) * R(b['W']) * R(b['H'])
        tot = {m['tp']: m['price'] + (0 if noinst else (b['iw'] if m['tp'] == 'дровяной' else b['ie'])) for m in b['models'] if m['lo'] <= V <= m['hi']}
        return ans == abs(tot['дровяной'] - tot['электрический'])
    return pcard(q, num(ans), e=e, svg=b['svg']), chk


@proto('og04-stove-discount', 'oge', 4, 'Выбор печи: цена со скидкой',
       invariant='На модель (заданную массой или номером) сделали скидку p%; найти новую цену.',
       varies='Сюжет, модель, процент скидки.',
       answer_rule='Новая цена = цена · (100 − p)/100.',
       fipi=r'сделали скидку \d+%',
       mistakes=['вычитают p рублей вместо процентов', 'находят величину скидки, а не новую цену'], svg=True, lim=10 ** 6,
       kim=KP(4, ['1.2'], [8], 3))
def gen_og04_stove_discount(r):
    b = _stove_block(r)
    if not b:
        return None
    m = r.choice(b['models'])
    p_ = r.choice([5, 10, 12, 15, 20, 25, 30])
    ans = F(m['price'] * (100 - p_), 100)
    if not nice(ans, 2, 10 ** 6):
        return None
    q = b['intro'] + f'\nНа модель массой {m["m"]} кг сделали скидку {p_}%. Сколько рублей стала стоить эта модель?'
    e = f'Это модель № {m["n"]}: {m["price"]}·{100 - p_}/100 = {tnum(ans)} руб.'
    return pcard(q, num(ans), e=e, svg=b['svg']), lambda: same(num(ans), [mm for mm in b['models'] if mm['m'] == m['m']][0]['price'] * sp.Rational(100 - p_, 100))


ARCH = [(15, 20), (18, 24), (21, 28), (24, 32), (30, 40), (20, 21), (12, 35), (27, 36), (16, 30), (24, 45)]


def svg_arch(half, h, R_):
    """Портал: прямоугольник шириной 2·half и высотой h, сверху дуга окружности радиуса R_ с центром в середине низа."""
    k = 150 / R_
    cx, cy = 180, 30 + R_ * k
    xl, xr = cx - half * k, cx + half * k
    yt = cy - h * k
    out = (f'<path d="M{xl:.1f} {cy:.1f} L{xl:.1f} {yt:.1f} A{R_ * k:.1f} {R_ * k:.1f} 0 0 1 {xr:.1f} {yt:.1f} L{xr:.1f} {cy:.1f} Z" '
           f'fill="{BLUE}" fill-opacity="0.12" stroke="{INK}" stroke-width="2"/>')
    out += f'<line x1="{cx}" y1="{cy}" x2="{xr:.1f}" y2="{yt:.1f}" stroke="{RED}" stroke-width="1.6" stroke-dasharray="5 4"/>'
    out += f'<circle cx="{cx}" cy="{cy}" r="3" fill="{RED}"/><text x="{cx + (xr - cx) / 2 + 6:.1f}" y="{(cy + yt) / 2:.1f}" font-size="14" font-style="italic" fill="{RED}">R</text>'
    out += f'<text x="{cx}" y="{cy + 18:.1f}" text-anchor="middle" font-size="13">{2 * half}</text>'
    out += f'<text x="{xl - 8:.1f}" y="{(cy + yt) / 2 + 4:.1f}" text-anchor="end" font-size="13">{h}</text>'
    return _svg(360, cy + 30, out)


@proto('og05-stove-arch', 'oge', 5, 'Арка над проёмом: радиус дуги',
       invariant='Верх проёма — дуга окружности с центром в середине нижнего края; радиус — гипотенуза треугольника с катетами «половина ширины» и «высота боковой стенки».',
       varies='Сюжет (портал камина, дверца печи, экран обогревателя), размеры (пифагоровы тройки).',
       answer_rule='R = √((ширина/2)² + h²).',
       fipi=r'радиус закругления арки',
       mistakes=['берут всю ширину вместо половины', 'складывают катеты'], svg=True, kim=KP(5, ['7.2', '7.4', '7.5'], [11], 5))
def gen_og05_stove_arch(r):
    c = r.choice(STOVES)
    a_, h = r.choice(ARCH)
    if r.random() < 0.5:
        a_, h = h, a_
    R_ = math.isqrt(a_ * a_ + h * h)
    q = (f'Лицевую часть {c["obj"]} обрамляет металлический портал: снизу и по бокам он прямой, а сверху — дуга окружности, центр которой находится '
         f'в середине нижнего края портала (см. рисунок, размеры в сантиметрах). Ширина портала {2 * a_} см, высота его боковых сторон {h} см. '
         'Найдите радиус дуги R в сантиметрах.')
    e = f'R = √({a_}² + {h}²) = {R_} см.'
    return pcard(q, num(R_), e=e, svg=svg_arch(a_, h, R_)), lambda: same(num(R_), sp.sqrt(sp.Integer(2 * a_) ** 2 / 4 + h ** 2))
