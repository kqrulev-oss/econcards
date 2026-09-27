#!/usr/bin/env python3
"""Прототип генераторов карточек по информатике (ЕГЭ и ОГЭ) — исследование, не часть сборки.

Запуск:
  python3 tools/research/gen_inf.py            # самопроверка: по 200 вариантов на тип
  python3 tools/research/gen_inf.py --show 2   # показать по 2 примера карточек каждого типа
  python3 tools/research/gen_inf.py --dump out.json  # все карточки в файл (не в packs/!)

Каждый генератор: gen_<тип>(rng) -> (card, params). card — карточка в формате
tools/build_packs.py: {id, t, k, q, a, e, o?}. Условия задач придуманы здесь,
тексты ФИПИ и коммерческих банков не используются.

Типы карточек:
  num  — число вводится с клавиатуры (есть в lib.js, sameNumber);
  one  — выбор варианта (есть);
  text — ПРЕДЛАГАЕМЫЙ тип: точная строка (слово, последовательность цифр/букв);
         сравнение без регистра и пробелов, как в бланке № 1. В lib.js его пока нет.

Каждый тип имеет независимую проверку check_<тип>(params, card): ответ считается
вторым способом (перебором / другой формулой) и сравнивается с card['a'].
"""
import argparse
import hashlib
import ipaddress
import itertools
import json
import math
import random
import re
import sys
from collections import Counter
from functools import lru_cache

# ---------------------------------------------------------------- общее


def card(t, k, q, a, e, o=None, src=None):
    c = {'id': '', 't': t, 'k': k, 'q': q, 'a': a, 'e': e}
    if o is not None:
        c['o'] = o
    c['src'] = src or 'Генератор «Между уроками» (собственные условия)'
    c['id'] = t + '-' + hashlib.sha1((q + '|' + json.dumps(a, ensure_ascii=False)).encode()).hexdigest()[:10]
    return c


def one_options(correct, wrong, rng):
    """Варианты для карточки one: верный + неверные (типичные ошибки), без повторов."""
    vals = [str(correct)]
    for w in wrong:
        if str(w) not in vals:
            vals.append(str(w))
    vals = vals[:4]
    rng.shuffle(vals)
    ids = 'абвг'
    o = [{'id': ids[i], 't': v} for i, v in enumerate(vals)]
    return o, ids[vals.index(str(correct))]


def to_base(n, b):
    digits = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if n == 0:
        return '0'
    s = ''
    while n:
        s = digits[n % b] + s
        n //= b
    return s


def bits_for(n):
    """Минимальное число бит, чтобы закодировать n разных значений."""
    return max(1, math.ceil(math.log2(n))) if n > 1 else 1


# ---------------------------------------------------------------- ЕГЭ 2: таблицы истинности

OPS = {'∧': lambda a, b: a and b, '∨': lambda a, b: a or b,
       '→': lambda a, b: (not a) or b, '≡': lambda a, b: a == b}


def rand_expr(rng, vars_, depth):
    if depth == 0 or rng.random() < 0.25:
        v = rng.choice(vars_)
        return ('not', ('var', v)) if rng.random() < 0.3 else ('var', v)
    op = rng.choice(list(OPS))
    e = (op, rand_expr(rng, vars_, depth - 1), rand_expr(rng, vars_, depth - 1))
    return ('not', e) if rng.random() < 0.15 else e


def ev(e, env):
    if e[0] == 'var':
        return env[e[1]]
    if e[0] == 'not':
        return not ev(e[1], env)
    return OPS[e[0]](ev(e[1], env), ev(e[2], env))


def show(e, top=True):
    if e[0] == 'var':
        return e[1]
    if e[0] == 'not':
        inner = show(e[1], False)
        return '¬' + (inner if e[1][0] in ('var', 'not') else inner)
    s = f'{show(e[1], False)} {e[0]} {show(e[2], False)}'
    return s if top else f'({s})'


def used_vars(e):
    if e[0] == 'var':
        return {e[1]}
    return set().union(*(used_vars(x) for x in e[1:]))


def gen_ege2(rng):
    vars_ = ['x', 'y', 'z', 'w']
    while True:
        e = rand_expr(rng, vars_, 3)
        if used_vars(e) == set(vars_):
            break
    rows = list(itertools.product([0, 1], repeat=4))
    ones = sum(1 for r in rows if ev(e, dict(zip(vars_, map(bool, r)))))
    want = rng.choice([1, 0])
    ans = ones if want else 16 - ones
    q = (f'Логическая функция F задана выражением F = {show(e)}. '
         f'Сколько строк таблицы истинности (из 16 наборов x, y, z, w) дают F = {want}?')
    ex = (f'Перебираем 16 наборов. F = 1 на {ones} наборах, F = 0 — на {16 - ones}. '
          'Удобно сначала найти, когда ложна импликация (1 → 0) или эквиваленция (разные значения).')
    return card('inf-ege-2', 'num', q, str(ans), ex), {'e': e, 'want': want}


def check_ege2(p, c):
    # второй способ: через побитовые операции над 16-битными масками столбцов
    masks = {}
    for i, v in enumerate('xyzw'):
        masks[v] = sum(1 << r for r in range(16) if (r >> (3 - i)) & 1)
    full = (1 << 16) - 1

    def m(e):
        if e[0] == 'var':
            return masks[e[1]]
        if e[0] == 'not':
            return full & ~m(e[1])
        a, b = m(e[1]), m(e[2])
        return {'∧': a & b, '∨': a | b, '→': (full & ~a) | b, '≡': full & ~(a ^ b)}[e[0]]
    ones = bin(m(p['e'])).count('1')
    return str(ones if p['want'] else 16 - ones) == c['a']


# ---------------------------------------------------------------- ЕГЭ 4: условие Фано


def random_prefix_code(rng, n):
    """Полный префиксный код из n слов: случайно делим листья двоичного дерева."""
    leaves = ['0', '1']
    while len(leaves) < n:
        leaf = rng.choice([l for l in leaves if len(l) < 5] or leaves)
        leaves.remove(leaf)
        leaves += [leaf + '0', leaf + '1']
    return leaves


def prefix_ok(a, b):
    return not a.startswith(b) and not b.startswith(a)


def min_total_len(given, k, maxlen=8):
    """Наименьшая суммарная длина k новых слов, совместимых по Фано с given (перебор)."""
    cands = [''.join(t) for L in range(1, maxlen + 1) for t in itertools.product('01', repeat=L)]
    cands = [s for s in cands if all(prefix_ok(s, g) for g in given)]
    best = None

    def rec(start, chosen, total):
        nonlocal best
        if best is not None and total >= best:
            return
        if len(chosen) == k:
            best = total
            return
        for i in range(start, len(cands)):
            s = cands[i]
            if best is not None and total + len(s) * (k - len(chosen)) >= best:
                break  # cands отсортированы по длине
            if all(prefix_ok(s, x) for x in chosen):
                rec(i + 1, chosen + [s], total + len(s))
    rec(0, [], 0)
    return best


def gen_ege4(rng):
    letters = 'АБВГДЕЖИКЛМН'
    n = rng.randint(5, 8)
    code = random_prefix_code(rng, n)
    rng.shuffle(code)
    k = rng.choice([1, 1, 2])
    drop = rng.randint(1, 2)  # освобождаем место в дереве: какие-то слова не используются
    given = code[:n - drop]
    names = rng.sample(letters, len(given) + k)
    known, unknown = names[:len(given)], names[len(given):]
    ans = min_total_len(given, k)
    parts = ', '.join(f'{a} — {c}' for a, c in zip(known, given))
    ask = (f'Укажите наименьшую возможную длину кодового слова для буквы {unknown[0]}.' if k == 1 else
           f'Укажите наименьшую возможную суммарную длину кодовых слов для букв {unknown[0]} и {unknown[1]}.')
    q = (f'По каналу связи передаются сообщения из букв {", ".join(sorted(names))}. Используется '
         f'неравномерный двоичный код, удовлетворяющий условию Фано (ни одно кодовое слово не является '
         f'началом другого). Известны коды: {parts}. {ask}')
    ex = ('Строим двоичное дерево известных кодов и ищем свободные ветви, которые не являются '
          'началом и продолжением занятых слов. Кратчайшая свободная ветвь даёт ответ.')
    return card('inf-ege-4', 'num', q, str(ans), ex), {'given': given, 'k': k}


def check_ege4(p, c):
    # второй способ: свободные узлы дерева — строки, не сравнимые ни с одним кодом; для k=2 берём
    # два непересекающихся (перебор пар из свободных до длины 7)
    free = [''.join(t) for L in range(1, 8) for t in itertools.product('01', repeat=L)
            if all(prefix_ok(''.join(t), g) for g in p['given'])]
    if p['k'] == 1:
        return str(min(len(s) for s in free)) == c['a']
    best = min(len(a) + len(b) for a, b in itertools.combinations(free, 2) if prefix_ok(a, b))
    return str(best) == c['a']


# ---------------------------------------------------------------- ЕГЭ 5: алгоритм над двоичной записью

RULES5 = [
    ('parity2', 'к двоичной записи дважды дописывается справа остаток от деления суммы её цифр на 2 '
                '(второй раз — уже для удлинённой записи)'),
    ('evenodd', 'если N чётное, в конец двоичной записи дописывается «10», иначе в начало дописывается «1», '
                'а в конец — «01»'),
    ('ones3', 'если количество единиц в двоичной записи делится на 3, в конец дописываются две её последние '
              'цифры, иначе дописывается остаток от деления количества единиц на 3 в двоичной записи'),
    ('dup', 'к двоичной записи справа дописываются две её первые (старшие) цифры'),
]


def apply5(rule, n):
    s = bin(n)[2:]
    if rule == 'parity2':
        for _ in range(2):
            s += str(s.count('1') % 2)
    elif rule == 'evenodd':
        s = s + '10' if n % 2 == 0 else '1' + s + '01'
    elif rule == 'ones3':
        k = s.count('1')
        s = s + s[-2:] if k % 3 == 0 else s + bin(k % 3)[2:]
    elif rule == 'dup':
        s = s + s[:2]
    return int(s, 2)


def gen_ege5(rng):
    rule, text = rng.choice(RULES5)
    mode = rng.choice(['minN', 'minR', 'maxN'])
    K = rng.randint(20, 400)
    rs = {n: apply5(rule, n) for n in range(1, 5000)}
    if mode == 'minN':
        ans = min(n for n, r in rs.items() if r > K)
        ask = f'Укажите минимальное число N, после обработки которого получается число R, большее {K}.'
    elif mode == 'minR':
        ans = min(r for r in rs.values() if r > K)
        ask = f'Укажите минимальное число R, большее {K}, которое может получиться в результате работы алгоритма.'
    else:
        ans = max(n for n, r in rs.items() if r < K * 4)
        ask = f'Укажите максимальное число N, после обработки которого получается число R, меньшее {K * 4}.'
    q = (f'Автомат получает на вход натуральное число N и строит R так: 1) строится двоичная запись N; '
         f'2) {text}; 3) результат переводится в десятичную систему. {ask}')
    ex = 'Удобно перебрать N программой: R растёт почти монотонно, но не строго — проверяйте соседние N.'
    return card('inf-ege-5', 'num', q, str(ans), ex), {'rule': rule, 'mode': mode, 'K': K}


def check_ege5(p, c):
    # второй способ: арифметика вместо строк
    def r(n):
        rule = p['rule']
        if rule == 'parity2':
            for _ in range(2):
                n = n * 2 + bin(n).count('1') % 2
            return n
        if rule == 'evenodd':
            L = n.bit_length()
            return n * 4 + 2 if n % 2 == 0 else ((1 << L) + n) * 4 + 1
        if rule == 'ones3':
            k = bin(n).count('1')
            if k % 3 == 0:
                return n * 4 + (n & 3)
            t = k % 3
            return (n << t.bit_length()) + t
        if rule == 'dup':
            L = n.bit_length()
            return n * 4 + (n >> (L - 2)) if L >= 2 else n * 2 + n  # у n = 1 «две первые» — одна цифра
    K = p['K']
    ns = range(1, 5000)
    if p['mode'] == 'minN':
        v = min(n for n in ns if r(n) > K)
    elif p['mode'] == 'minR':
        v = min(r(n) for n in ns if r(n) > K)
    else:
        v = max(n for n in ns if r(n) < K * 4)
    return str(v) == c['a']


# ---------------------------------------------------------------- ЕГЭ 7: объём изображения и звука


def gen_ege7(rng):
    kind = rng.choice(['img', 'img_colors', 'sound'])
    if kind == 'img':
        colors = rng.choice([2, 4, 8, 16, 32, 64, 128, 256, 1024, 65536])
        i = bits_for(colors)
        w, h = rng.choice([64, 128, 256, 512, 1024, 2048]), rng.choice([64, 128, 256, 512, 768, 1024])
        kb = w * h * i / 8 / 1024
        if kb != int(kb):
            return gen_ege7(rng)
        kb = int(kb)
        q = (f'Растровое изображение размером {w}×{h} пикселей сохранено без сжатия, палитра — {colors} цветов, '
             f'код каждого пикселя одинаковой минимальной длины. Сколько Кбайт занимает изображение?')
        ex = f'i = ⌈log₂{colors}⌉ = {i} бит. V = {w}·{h}·{i} бит = {w * h * i} бит = {kb} Кбайт (1 Кбайт = 1024 байта = 8192 бита).'
        wrong = [w * h * i // 1024, round(w * h * i / 8 / 1000), w * h * colors // 8 // 1024]
        o, a = one_options(kb, [x for x in wrong if x != kb] + [kb * 2, kb // 2], rng)
        return card('inf-ege-7', 'one', q, a, ex, o=o), {'kind': kind, 'w': w, 'h': h, 'colors': colors, 'ans': kb}
    if kind == 'img_colors':
        i = rng.randint(2, 16)
        w, h = rng.choice([128, 256, 512, 640, 1024]), rng.choice([128, 256, 480, 512, 1024])
        limit_kb = w * h * i / 8 / 1024
        if limit_kb != int(limit_kb):
            return gen_ege7(rng)
        limit_kb = int(limit_kb) + rng.randint(0, max(0, w * h // 8 // 1024 - 1))
        imax = limit_kb * 8192 // (w * h)
        ans = 2 ** imax
        q = (f'Для хранения растрового изображения {w}×{h} пикселей без сжатия отведено не более {limit_kb} Кбайт. '
             f'Код каждого пикселя одинаковой минимальной длины. Какое наибольшее число цветов можно использовать?')
        ex = f'На пиксель доступно ⌊{limit_kb}·8192 / ({w}·{h})⌋ = {imax} бит, значит цветов не больше 2^{imax} = {ans}.'
        return card('inf-ege-7', 'num', q, str(ans), ex), {'kind': kind, 'w': w, 'h': h, 'limit': limit_kb, 'ans': ans}
    ch = rng.choice([1, 2, 4])
    rate = rng.choice([8, 16, 32, 48, 64])  # кГц; для точного ответа берём степени двойки и 48
    bits = rng.choice([8, 16, 24, 32])
    sec = rng.choice([32, 64, 128, 256, 60, 120, 240])
    total = ch * rate * 1000 * bits * sec
    mb = total / 8 / 2 ** 20
    ans = int(mb + 0.5)
    if abs(mb - int(mb) - 0.5) < 0.1 or ans == 0:  # избегаем пограничных случаев вроде 62,5
        return gen_ege7(rng)
    q = (f'Производится {["", "одноканальная (моно)", "двухканальная (стерео)", "", "четырёхканальная (квадро)"][ch]} '
         f'звукозапись с частотой дискретизации {rate} кГц и разрешением {bits} бит, сжатие не используется. '
         f'Запись длится {sec} секунд. Каков размер файла в Мбайт? В ответе укажите ближайшее целое число.')
    ex = f'V = {ch}·{rate}000·{bits}·{sec} бит ≈ {mb:.2f} Мбайт (1 Мбайт = 2²⁰ байт). Ответ: {ans}.'
    return card('inf-ege-7', 'num', q, str(ans), ex), {'kind': kind, 'ch': ch, 'rate': rate, 'bits': bits, 'sec': sec}


def check_ege7(p, c):
    if p['kind'] == 'img':
        bits = (p['colors'] - 1).bit_length()
        v = p['w'] * p['h'] * bits // 8192
        return any(o['id'] == c['a'] and o['t'] == str(v) for o in c['o'])
    if p['kind'] == 'img_colors':
        # перебор числа цветов
        best = max(2 ** i for i in range(1, 25) if p['w'] * p['h'] * i <= p['limit'] * 8192)
        return str(best) == c['a']
    v = p['ch'] * p['rate'] * 1000 * p['bits'] * p['sec'] / 8 / 1024 / 1024
    return str(int(v + 0.5)) == c['a']


# ---------------------------------------------------------------- ЕГЭ 8: комбинаторика слов

WORDS8 = ['МАРС', 'КОРТ', 'ЛИМОН', 'ПОРТАЛ', 'ГРОЗА', 'СИНТЕЗ', 'ФОКУС', 'БАРЖА', 'ТОРНАДО', 'ВЕКТОР', 'ПИКСЕЛЬ']
VOWELS = set('АЕЁИОУЫЭЮЯ')


def count8(letters, n, cond):
    return sum(1 for w in itertools.product(letters, repeat=n) if cond(w))


def gen_ege8(rng):
    word = rng.choice(WORDS8)
    letters = sorted(set(word) - {'Ь'})
    kind = rng.choice(['exact', 'no_adj_vowels', 'distinct_first', 'perm_no_adj'])
    n = rng.randint(4, 6)
    x = rng.choice(letters)
    y = rng.choice([l for l in letters if l != x])
    if kind == 'exact':
        m = rng.randint(1, 2)
        cond = lambda w: w.count(x) == m and w[0] != y  # noqa: E731
        q = (f'Вася составляет {n}-буквенные слова из букв {", ".join(letters)}. Каждая буква может встречаться '
             f'любое число раз, но буква {x} — ровно {m} раз(а), и слово не может начинаться с буквы {y}. '
             f'Сколько различных слов может составить Вася?')
        p = {'kind': kind, 'letters': letters, 'n': n, 'x': x, 'y': y, 'm': m}
    elif kind == 'no_adj_vowels':
        cond = lambda w: not any(w[i] in VOWELS and w[i + 1] in VOWELS for i in range(n - 1))  # noqa: E731
        q = (f'Из букв {", ".join(letters)} составляются слова длины {n} (буквы могут повторяться). '
             f'Сколько существует слов, в которых нет двух гласных подряд?')
        p = {'kind': kind, 'letters': letters, 'n': n}
    elif kind == 'distinct_first':
        n = min(n, len(letters))
        cond = lambda w: len(set(w)) == n and w[0] == x  # noqa: E731
        q = (f'Сколько существует слов длины {n} из букв {", ".join(letters)}, в которых все буквы различны '
             f'и первая буква — {x}?')
        p = {'kind': kind, 'letters': letters, 'n': n, 'x': x}
    else:
        n = len(letters)
        if n > 7 or x == y:
            return gen_ege8(rng)
        cond = lambda w: len(set(w)) == n and all(not ({w[i], w[i + 1]} == {x, y}) for i in range(n - 1))  # noqa: E731
        q = (f'Сколько различных слов можно получить перестановкой букв {", ".join(letters)} (каждая буква '
             f'ровно один раз), если буквы {x} и {y} не должны стоять рядом?')
        p = {'kind': kind, 'letters': letters, 'n': n, 'x': x, 'y': y}
    ans = count8(letters, n, cond)
    ex = 'Считаем по правилу произведения или перебираем программой itertools.product / permutations.'
    return card('inf-ege-8', 'num', q, str(ans), ex), p


def check_ege8(p, c):
    L, n = len(p['letters']), p['n']
    if p['kind'] == 'exact':
        m = p['m']
        # формула: позиции x — C(n,m); остальные буквы — (L-1)^(n-m); вычитаем слова, начинающиеся с y
        total = math.comb(n, m) * (L - 1) ** (n - m)
        start_y = math.comb(n - 1, m) * (L - 1) ** (n - 1 - m) if n - 1 >= m else 0
        return str(total - start_y) == c['a']
    if p['kind'] == 'distinct_first':
        return str(math.perm(L - 1, n - 1)) == c['a']
    if p['kind'] == 'perm_no_adj':
        return str(math.factorial(n) - 2 * math.factorial(n - 1)) == c['a']
    # no_adj_vowels: динамика по последней букве
    v = sum(1 for l in p['letters'] if l in VOWELS)
    cns = L - v
    endv, endc = v, cns
    for _ in range(n - 1):
        endv, endc = endc * v, (endv + endc) * cns
    return str(endv + endc) == c['a']


# ---------------------------------------------------------------- ЕГЭ 11: объём сообщений (идентификаторы)


def gen_ege11(rng):
    alpha = rng.choice([10, 12, 26, 33, 36, 52, 62, 1000, 2000])
    length = rng.randint(6, 300) if alpha >= 1000 else rng.randint(5, 25)
    users = rng.choice([20, 50, 64, 100, 128, 256, 500, 1000, 1024, 2048, 4096])
    bits = bits_for(alpha)
    per = math.ceil(length * bits / 8)
    if alpha >= 1000:
        what = f'{alpha} различных символов (иероглифов)'
    else:
        what = f'{alpha} различных символов'
    ask = rng.choice(['bytes_total', 'kb_total', 'bytes_one'])
    if ask == 'bytes_one':
        ans = per
        tail = 'Сколько байт занимает один пароль?'
    elif ask == 'bytes_total':
        ans = per * users
        tail = f'Сколько байт нужно для хранения {users} паролей?'
    else:
        total = per * users
        ans = math.ceil(total / 1024)
        tail = f'Сколько Кбайт нужно для хранения {users} паролей? Ответ округлите вверх до целого.'
    q = (f'Пароль состоит из {length} символов, в нём используются только {what}. Каждый символ кодируется '
         f'одинаковым минимально возможным числом бит, а пароль целиком — минимально возможным целым числом байт. '
         f'{tail}')
    ex = (f'Символ: ⌈log₂{alpha}⌉ = {bits} бит. Пароль: {length}·{bits} = {length * bits} бит → {per} байт '
          '(округляем вверх до целого байта для КАЖДОГО пароля, а не для суммы).')
    return card('inf-ege-11', 'num', q, str(ans), ex), {'alpha': alpha, 'length': length, 'users': users, 'ask': ask}


def check_ege11(p, c):
    b = 1
    while 2 ** b < p['alpha']:
        b += 1
    per = -(-p['length'] * b // 8)
    v = {'bytes_one': per, 'bytes_total': per * p['users'], 'kb_total': -(-per * p['users'] // 1024)}[p['ask']]
    return str(v) == c['a']


# ---------------------------------------------------------------- ЕГЭ 12: исполнитель Редактор

RULES12 = [
    [('111', '2'), ('22', '1')],
    [('222', '1'), ('111', '2')],
    [('12', '2'), ('22', '1')],
    [('01', '30'), ('02', '101'), ('03', '202')],
    [('11', '2'), ('222', '1')],
    [('333', '1'), ('11', '3')],
]


def run12(s, rules, limit=100000):
    for _ in range(limit):
        for a, b in rules:
            if a in s:
                s = s.replace(a, b, 1)
                break
        else:
            return s
    return None


def gen_ege12(rng):
    rules = rng.choice(RULES12)
    if rules[0][0].startswith('0'):
        n1, n2 = rng.randint(3, 40), rng.randint(3, 40)
        start = '0' + '1' * n1 + '2' * n2
        desc = f'строка «0», за которой следуют {n1} единиц и {n2} двоек'
    else:
        d = rules[-1][0][0] if rng.random() < 0.3 else rules[0][0][0]
        n = rng.randint(20, 150)
        start = d * n
        desc = f'строка из {n} цифр «{d}»'
    res = run12(start, rules)
    if res is None or len(res) > 40:
        return gen_ege12(rng)
    ans = sum(int(ch) for ch in res)
    conds = ' ИЛИ '.join(f'нашлось({a})' for a, _ in rules)
    body = ' '.join(('ЕСЛИ' if i == 0 else 'ИНАЧЕ ЕСЛИ') + f' нашлось({a}) ТО заменить({a}, {b})'
                    for i, (a, b) in enumerate(rules))
    q = (f'Исполнитель Редактор выполняет программу: ПОКА {conds}: {body}. Команда заменить(v, w) заменяет '
         f'первое слева вхождение v на w. На вход подана {desc}. Найдите сумму цифр строки-результата.')
    ex = f'Моделируем программой или ищем цикл замен. Результат: {res}, сумма цифр {ans}.'
    return card('inf-ege-12', 'num', q, str(ans), ex), {'start': start, 'rules': rules}


def check_ege12(p, c):
    # второй способ: регулярные выражения вместо str.replace
    s = p['start']
    changed = True
    while changed:
        changed = False
        for a, b in p['rules']:
            m = re.search(re.escape(a), s)
            if m:
                s = s[:m.start()] + b + s[m.end():]
                changed = True
                break
    return str(sum(map(int, s))) == c['a']


# ---------------------------------------------------------------- ЕГЭ 13: IP-адреса и маски


def rand_ip(rng):
    return '.'.join(str(rng.randint(1, 254)) for _ in range(4))


def gen_ege13(rng):
    kind = rng.choice(['net_byte', 'max_ones', 'count_addr', 'mask_byte'])
    if kind == 'net_byte':
        ip = rand_ip(rng)
        pref = rng.randint(17, 30)
        net = ipaddress.ip_network(f'{ip}/{pref}', strict=False)
        byte = rng.choice([3, 4]) if pref > 24 else 3
        ans = int(str(net.network_address).split('.')[byte - 1])
        mask = str(net.netmask)
        q = (f'Узел с IP-адресом {ip} находится в сети с маской {mask}. Чему равен {["", "", "", "третий", "четвёртый"][byte]} '
             f'слева байт адреса этой сети?')
        ex = f'Адрес сети = IP поразрядно И маска: {net.network_address}.'
        return card('inf-ege-13', 'num', q, str(ans), ex), {'kind': kind, 'ip': ip, 'pref': pref, 'byte': byte}
    if kind == 'max_ones':
        a = rand_ip(rng)
        ai = int(ipaddress.IPv4Address(a))
        flip = rng.randint(3, 14)
        bi = ai ^ (1 << flip) ^ rng.randint(0, (1 << flip) - 1)
        b = str(ipaddress.IPv4Address(bi))
        best = None
        for pref in range(0, 31):
            na = ipaddress.ip_network(f'{a}/{pref}', strict=False)
            if ipaddress.IPv4Address(b) in na and a not in (str(na.network_address), str(na.broadcast_address)) \
                    and b not in (str(na.network_address), str(na.broadcast_address)):
                best = pref
        if best is None:
            return gen_ege13(rng)
        q = (f'Два узла с IP-адресами {a} и {b} находятся в одной сети. Какое наибольшее количество единиц '
             f'может быть в двоичной записи маски этой сети? Адреса узлов не совпадают с адресом сети и '
             f'широковещательным адресом.')
        ex = 'Маска — общая начальная часть двоичной записи двух адресов. Ищем первый различающийся бит.'
        return card('inf-ege-13', 'num', q, str(best), ex), {'kind': kind, 'a': a, 'b': b}
    if kind == 'count_addr':
        pref = rng.randint(20, 29)
        ip = rand_ip(rng)
        net = ipaddress.ip_network(f'{ip}/{pref}', strict=False)
        par = rng.choice(['even', 'mult3'])
        ok = [x for x in net if (bin(int(x)).count('1') % 2 == 0 if par == 'even' else bin(int(x)).count('1') % 3 == 0)]
        ans = len(ok)
        prop = 'чётно' if par == 'even' else 'кратно 3'
        q = (f'Сеть задана адресом {net.network_address} и маской {net.netmask}. Сколько в этой сети адресов '
             f'(включая адрес сети и широковещательный), у которых количество единиц в двоичной записи {prop}?')
        ex = 'Перебираем все адреса сети программой (ipaddress.ip_network) и считаем единицы.'
        return card('inf-ege-13', 'num', q, str(ans), ex), {'kind': kind, 'net': str(net), 'par': par}
    pref = rng.randint(9, 30)
    ip = rand_ip(rng)
    net = ipaddress.ip_network(f'{ip}/{pref}', strict=False)
    byte = (pref - 1) // 8 + 1
    ans = int(str(net.netmask).split('.')[byte - 1])
    nb = str(net.network_address).split('.')
    q = (f'Узел с IP-адресом {ip} находится в сети с адресом {net.network_address}. Известно, что маска '
         f'содержит ровно {pref} единиц. Чему равен {["", "первый", "второй", "третий", "четвёртый"][byte]} слева байт маски?')
    ex = f'{pref} единиц: полные байты 255, в {byte}-м байте {pref - 8 * (byte - 1)} единиц слева → {ans}.'
    return card('inf-ege-13', 'num', q, str(ans), ex), {'kind': kind, 'pref': pref, 'byte': byte}


def check_ege13(p, c):
    def ip2i(s):
        a = list(map(int, s.split('.')))
        return (a[0] << 24) | (a[1] << 16) | (a[2] << 8) | a[3]
    if p['kind'] == 'net_byte':
        m = (0xFFFFFFFF << (32 - p['pref'])) & 0xFFFFFFFF
        n = ip2i(p['ip']) & m
        return str((n >> (8 * (4 - p['byte']))) & 255) == c['a']
    if p['kind'] == 'max_ones':
        a, b = ip2i(p['a']), ip2i(p['b'])
        for pref in range(30, -1, -1):
            m = (0xFFFFFFFF << (32 - pref)) & 0xFFFFFFFF
            host = ~m & 0xFFFFFFFF
            if a & m == b & m and a & host not in (0, host) and b & host not in (0, host):
                return str(pref) == c['a']
        return False
    if p['kind'] == 'count_addr':
        net, pref = p['net'].split('/')
        base, size = ip2i(net), 1 << (32 - int(pref))
        f = (lambda k: k % 2 == 0) if p['par'] == 'even' else (lambda k: k % 3 == 0)
        return str(sum(1 for x in range(base, base + size) if f(bin(x).count('1')))) == c['a']
    k = p['pref'] - 8 * (p['byte'] - 1)  # 1..8 единиц в этом байте
    return str(256 - 2 ** (8 - k)) == c['a']


# ---------------------------------------------------------------- ЕГЭ 14: системы счисления


def gen_ege14(rng):
    kind = rng.choice(['count_digit', 'count_digit', 'unknown_digit'])
    if kind == 'count_digit':
        b = rng.choice([2, 3, 4, 5, 7, 8, 9, 16])
        terms = []
        val = 0
        for _ in range(rng.randint(2, 3)):
            base = rng.choice([b, b * b, b ** 3]) if b < 10 else rng.choice([2, 4, 16])
            e = rng.randint(10, 400)
            sign = rng.choice([1, 1, -1]) if terms else 1
            terms.append((sign, base, e))
            val += sign * base ** e
        sub = rng.randint(1, 300)
        val -= sub
        if val <= 0:
            return gen_ege14(rng)
        digit = rng.choice('0123456789ABCDEF'[:b][1:] if rng.random() < 0.7 else '0123456789ABCDEF'[:b])
        s = to_base(val, b)
        ans = s.count(digit)
        expr = ' '.join(('' if i == 0 else ('+ ' if sg > 0 else '− ')) + f'{bs}^{e}' for i, (sg, bs, e) in enumerate(terms))
        q = (f'Значение выражения {expr} − {sub} записали в системе счисления с основанием {b}. '
             f'Сколько цифр {digit} содержится в этой записи?')
        ex = 'Степени основания дают «1 и нули», вычитание небольшого числа превращает хвост в цифры (b−1). Проще проверить программой.'
        return card('inf-ege-14', 'num', q, str(ans), ex), {'kind': kind, 'val': val, 'b': b, 'digit': digit}
    p = rng.randint(9, 16)
    k = rng.randint(7, 50)
    d1, d2, d3, d4 = (rng.randint(0, p - 1) for _ in range(4))
    # M = d1 x d2 (основание p), N = x d3 d4 (основание p)
    found = None
    for x in range(1, p):
        m = d1 * p * p + x * p + d2
        n = x * p * p + d3 * p + d4
        if (m + n) % k == 0:
            found = (x, (m + n) // k)
            break
    if not found or d1 == 0:
        return gen_ege14(rng)
    D = '0123456789ABCDEF'
    q = (f'Числа M = {D[d1]}x{D[d2]} и N = x{D[d3]}{D[d4]} записаны в системе счисления с основанием {p} '
         f'(x — одна и та же неизвестная цифра этой системы). Найдите наименьшее x, при котором M + N делится на {k}. '
         f'В ответ запишите частное (M + N) / {k} в десятичной системе.')
    ex = f'Перебираем x от 0 до {p - 1}: x = {found[0]}, частное {found[1]}.'
    return card('inf-ege-14', 'num', q, str(found[1]), ex), {'kind': kind, 'p': p, 'k': k, 'd': (d1, d2, d3, d4)}


def check_ege14(p, c):
    if p['kind'] == 'count_digit':
        # второй способ: встроенная функция int с обратным переводом
        s = to_base(p['val'], p['b'])
        assert int(s, p['b']) == p['val']
        return str(s.count(p['digit'])) == c['a']
    D = '0123456789ABCDEF'
    d1, d2, d3, d4 = p['d']
    for x in range(1, p['p']):
        m = int(D[d1] + D[x] + D[d2], p['p'])
        n = int(D[x] + D[d3] + D[d4], p['p'])
        if (m + n) % p['k'] == 0:
            return str((m + n) // p['k']) == c['a']
    return False


# ---------------------------------------------------------------- ЕГЭ 15: логика (побитовое И, отрезки)


def gen_ege15(rng):
    kind = rng.choice(['bits', 'segments'])
    if kind == 'bits':
        a, b = rng.randint(1, 255), rng.randint(1, 255)
        target = a & ~b & 255
        if target == 0:
            return gen_ege15(rng)
        best = next(A for A in range(256) if all(
            not (x & a != 0) or not (x & b == 0) or (x & A != 0) for x in range(256)))
        q = (f'Обозначим x & y поразрядную конъюнкцию неотрицательных целых x и y. Для какого наименьшего '
             f'неотрицательного A формула (x & {a} ≠ 0) → ((x & {b} = 0) → (x & A ≠ 0)) тождественно истинна '
             f'(при любом неотрицательном x)?')
        ex = (f'Формула ложна, только когда x & {a} ≠ 0, x & {b} = 0 и x & A = 0. Опасные x содержат бит из {a}, '
              f'которого нет в {b}; A должно содержать все такие биты: {a} & ¬{b} = {best}.')
        return card('inf-ege-15', 'num', q, str(best), ex), {'kind': kind, 'a': a, 'b': b}
    p1 = rng.randint(5, 40)
    p2 = p1 + rng.randint(10, 50)
    q1 = rng.randint(p1 - 5, p2)
    q2 = q1 + rng.randint(3, 30)
    if q1 <= p1 and q2 >= p2:
        return gen_ege15(rng)
    pieces = []
    if p1 < q1:
        pieces.append((p1, min(p2, q1)))
    if p2 > q2:
        pieces.append((max(p1, q2), p2))
    ans = max(e for _, e in pieces) - min(s for s, _ in pieces)
    q = (f'На числовой прямой даны отрезки P = [{p1}; {p2}] и Q = [{q1}; {q2}]. Какова наименьшая возможная длина '
         f'отрезка A, при котором формула (x ∈ P) → ((x ∈ Q) ∨ (x ∈ A)) тождественно истинна (при любом x)?')
    ex = ('Формула ложна, когда x ∈ P и x ∉ Q и x ∉ A. Значит, A должен покрыть P \\ Q. Если разность — '
          f'два куска, A накрывает оба: длина {ans}.')
    return card('inf-ege-15', 'num', q, str(ans), ex), {'kind': kind, 'P': (p1, p2), 'Q': (q1, q2)}


def check_ege15(p, c):
    if p['kind'] == 'bits':
        return str(p['a'] & ~p['b'] & 255) == c['a']
    (p1, p2), (q1, q2) = p['P'], p['Q']
    xs = [i / 4 for i in range(int(p1 * 4) - 8, int(p2 * 4) + 9)]
    bad = [x for x in xs if p1 <= x <= p2 and not (q1 <= x <= q2)]
    # на сетке с шагом 1/4 открытые концы теряют ≤ 1/4 с каждой стороны
    L = max(bad) - min(bad)
    return abs(L - float(c['a'])) <= 0.5


# ---------------------------------------------------------------- ЕГЭ 16: рекурсия


def gen_ege16(rng):
    t = rng.randint(1, 4)
    c0 = rng.randint(1, 5)
    a = rng.randint(1, 3)
    b = rng.randint(1, 5)
    d = rng.randint(1, 4)
    form = rng.choice(['lin', 'parity', 'two'])
    N = rng.randint(15, 30)

    def f(n, memo={}):
        key = (n, t, c0, a, b, d, form)
        if key in memo:
            return memo[key]
        if n <= t:
            r = c0
        elif form == 'lin':
            r = a * f(n - 1) + b * n
        elif form == 'parity':
            r = f(n - 1) + b * n if n % 2 == 0 else f(n - 2) * a + d
        else:
            r = f(n - 1) + f(n - 2) + d if n > t + 1 else c0 + d
        memo[key] = r
        return r
    ans = f(N)
    if ans > 10 ** 12:
        return gen_ege16(rng)
    rule = {
        'lin': f'F(n) = {a}·F(n − 1) + {b}·n при n > {t}',
        'parity': f'F(n) = F(n − 1) + {b}·n при чётном n > {t}; F(n) = {a}·F(n − 2) + {d} при нечётном n > {t}',
        'two': f'F({t + 1}) = {c0 + d}; F(n) = F(n − 1) + F(n − 2) + {d} при n > {t + 1}',
    }[form]
    q = f'Функция F(n), n — натуральное, задана так: F(n) = {c0} при n ≤ {t}; {rule}. Чему равно F({N})?'
    ex = 'Считаем снизу вверх (циклом или с мемоизацией), чтобы не упереться в глубину рекурсии.'
    return card('inf-ege-16', 'num', q, str(ans), ex), {'t': t, 'c0': c0, 'a': a, 'b': b, 'd': d, 'form': form, 'N': N}


def check_ege16(p, c):
    t, c0, a, b, d, form, N = (p[k] for k in ('t', 'c0', 'a', 'b', 'd', 'form', 'N'))
    F = {}
    for n in range(1, N + 1):
        if n <= t:
            F[n] = c0
        elif form == 'lin':
            F[n] = a * F[n - 1] + b * n
        elif form == 'parity':
            F[n] = F[n - 1] + b * n if n % 2 == 0 else a * F[n - 2] + d
        else:
            F[n] = c0 + d if n == t + 1 else F[n - 1] + F[n - 2] + d
    return str(F[N]) == c['a']


# ---------------------------------------------------------------- ЕГЭ 19–21: теория игр (одна куча)


def game_levels(moves, W):
    """win_in(s, k): игрок, делающий ход из позиции s, может гарантированно выиграть не более чем за k своих ходов."""
    @lru_cache(None)
    def win_in(s, k):
        if k == 0:
            return False
        for m in moves:
            ns = m(s)
            if ns >= W:
                return True
            if k > 1 and all(m2(ns) < W and win_in(m2(ns), k - 1) for m2 in moves):
                return True
        return False
    return win_in


def stones(n):
    return f'{n} ' + ('камень' if n % 10 == 1 and n % 100 != 11 else
                      'камня' if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else 'камней')


def gen_ege19(rng):
    adds = sorted(rng.sample([1, 2, 3, 4, 5], 2))
    mul = rng.choice([2, 2, 3])
    W = rng.randint(30, 120)
    moves = [lambda s, x=adds[0]: s + x, lambda s, x=adds[1]: s + x, lambda s, m=mul: s * m]
    S = range(1, W)
    win_in = game_levels(moves, W)

    def v1(s):  # Ваня выигрывает первым ходом при любом ходе Пети
        return not win_in(s, 1) and all(m(s) < W and win_in(m(s), 1) for m in moves)

    def p2(s):
        return not win_in(s, 1) and win_in(s, 2)

    def v2(s):
        return not win_in(s, 1) and all(m(s) < W and win_in(m(s), 2) for m in moves) and not v1(s)

    task = rng.choice([19, 20, 21])
    rule = (f'В куче S камней. Игроки ходят по очереди, первый ход — Петя. За ход можно добавить в кучу '
            f'{stones(adds[0])} или {stones(adds[1])} или увеличить число камней в {mul} раза. Игра завершается, '
            f'когда в куче становится не менее {W} камней; победил тот, кто сделал последний ход. 1 ≤ S ≤ {W - 1}.')
    if task == 19:
        # Ваня выиграл первым ходом после неудачного хода Пети
        cand = [s for s in S if not win_in(s, 1) and any(m(s) < W and win_in(m(s), 1) for m in moves)]
        if not cand:
            return gen_ege19(rng)
        ans = str(min(cand))
        q = rule + (' Известно, что Ваня выиграл своим первым ходом после неудачного первого хода Пети. '
                    'Укажите минимальное S, при котором такая ситуация возможна.')
        k = 'num'
    elif task == 20:
        cand = [s for s in S if p2(s)]
        if len(cand) < 2:
            return gen_ege19(rng)
        cand = cand[:2]
        ans = ' '.join(map(str, cand))
        q = rule + (' Найдите два наименьших значения S, при которых у Пети есть выигрышная стратегия, причём '
                    'он не может выиграть за один ход, но может выиграть своим вторым ходом при любой игре Вани. '
                    'Запишите их в порядке возрастания через пробел.')
        k = 'text'
    else:
        cand = [s for s in S if v2(s)]
        if not cand:
            return gen_ege19(rng)
        ans = str(min(cand))
        q = rule + (' Найдите минимальное S, при котором у Вани есть стратегия, позволяющая выиграть первым '
                    'или вторым ходом при любой игре Пети, но нет стратегии, гарантирующей победу первым ходом.')
        k = 'num'
    ex = 'Строим позиции от конца: сначала те, где выигрывают за 1 ход, затем проигрышные, затем выигрыш за 2 хода.'
    return card(f'inf-ege-{task}', k, q, ans, ex), {'adds': adds, 'mul': mul, 'W': W, 'task': task}


def check_ege19(p, c):
    # второй способ: явное ретроградное присвоение уровней (без рекурсии с lru_cache)
    adds, mul, W = p['adds'], p['mul'], p['W']
    nxt = lambda s: [s + adds[0], s + adds[1], s * mul]  # noqa: E731
    level = {}  # s -> ('W', k) выигрыш ходящего за k ходов, ('L', k) проигрыш: соперник выигрывает за k
    for _ in range(8):
        for s in range(W - 1, 0, -1):
            outs = nxt(s)
            if any(o >= W for o in outs):
                level[s] = ('W', 1)
                continue
            ch = [level.get(o) for o in outs]
            ls = [x[1] for x in ch if x and x[0] == 'L']
            if ls:
                level[s] = ('W', min(ls) + 1)
            elif all(x and x[0] == 'W' for x in ch):
                level[s] = ('L', max(x[1] for x in ch))
    S = range(1, W)
    if p['task'] == 19:
        v = min(s for s in S if level.get(s) != ('W', 1) and any(o < W and level.get(o) == ('W', 1) for o in nxt(s)))
        return str(v) == c['a']
    if p['task'] == 20:
        v = [s for s in S if level.get(s) == ('W', 2)][:2]
        return ' '.join(map(str, v)) == c['a']
    v = min(s for s in S if level.get(s) == ('L', 2))
    return str(v) == c['a']


# ---------------------------------------------------------------- ЕГЭ 23 (2026): число программ исполнителя


def gen_ege23(rng):
    c1 = rng.choice([1, 1, 2])
    c2 = rng.choice([2, 3])
    ops = [('Прибавить ' + str(c1), lambda x: x + c1)]
    kind2 = rng.choice(['add', 'mul'])
    if kind2 == 'add':
        c2 = c1 + rng.randint(1, 2)
        ops.append(('Прибавить ' + str(c2), lambda x: x + c2))
    else:
        ops.append(('Умножить на ' + str(c2), lambda x: x * c2))
    A = rng.randint(1, 5)
    B = rng.randint(20, 60)
    C = rng.randint(A + 2, B - 3)
    D = rng.choice([None, rng.randint(A + 1, B - 1)])
    if D == C:
        D = None

    def count(a, b, avoid):
        f = {a: 1}
        for x in range(a, b):
            if x not in f or x == avoid:
                continue
            for _, op in ops:
                y = op(x)
                if y <= b:
                    f[y] = f.get(y, 0) + f[x]
        return f.get(b, 0) if b != avoid else 0
    ans = count(A, C, D) * count(C, B, D)
    if ans == 0 or ans > 10 ** 9:
        return gen_ege23(rng)
    names = '; '.join(f'{i + 1}. {n}' for i, (n, _) in enumerate(ops))
    extra = f' и не содержит числа {D}' if D else ''
    q = (f'Исполнитель преобразует число на экране. Команды: {names}. Сколько существует программ, которые '
         f'преобразуют число {A} в число {B}, если траектория вычислений содержит число {C}{extra}?')
    ex = 'Динамика: f(A) = 1, f(y) += f(x) по каждой команде; считаем A → C и C → B отдельно и перемножаем.'
    return card('inf-ege-23', 'num', q, str(ans), ex), {'c1': c1, 'c2': c2, 'kind2': kind2, 'A': A, 'B': B, 'C': C, 'D': D}


def check_ege23(p, c):
    ops = [lambda x: x + p['c1'], (lambda x: x + p['c2']) if p['kind2'] == 'add' else (lambda x: x * p['c2'])]

    @lru_cache(None)
    def ways(x, b):  # рекурсия сверху вниз
        if x == b:
            return 1
        if x > b or x == p['D']:
            return 0
        return sum(ways(op(x), b) for op in ops)
    return str(ways(p['A'], p['C']) * ways(p['C'], p['B'])) == c['a']


# ---------------------------------------------------------------- ОГЭ 1: объём текста

CATS = {
    'Звери': ['ёж', 'кот', 'лось', 'барсук', 'бобр', 'енот', 'хорёк', 'носорог', 'бурундук', 'медведь', 'дикобраз', 'горностай'],
    'Реки': ['Ока', 'Лена', 'Волга', 'Кама', 'Енисей', 'Амур', 'Обь', 'Печора', 'Северная Двина', 'Ангара', 'Иртыш'],
    'Инструменты': ['пила', 'молоток', 'рубанок', 'стамеска', 'отвёртка', 'напильник', 'шило', 'клещи', 'долото', 'уровень'],
    'Планеты': ['Марс', 'Венера', 'Земля', 'Юпитер', 'Сатурн', 'Уран', 'Нептун', 'Меркурий'],
}


def gen_oge1(rng):
    cat = rng.choice(list(CATS))
    pool = [w for w in CATS[cat] if ' ' not in w]
    words = rng.sample(pool, min(len(pool), rng.randint(6, 8)))
    lens = Counter(len(w) for w in words)
    cand = [w for w in words if lens[len(w)] == 1]
    if not cand:
        return gen_oge1(rng)
    removed = rng.choice(cand)
    bits = rng.choice([8, 16])
    enc = {8: 'КОИ-8 (8 бит)', 16: 'UTF-16 (16 бит)'}[bits]
    delta_chars = len(removed) + 2  # слово, запятая и пробел
    delta = delta_chars * bits // 8
    text = '«' + cat + ' — ' + ', '.join(words) + '.»'
    q = (f'В кодировке {enc} каждый символ кодируется {bits} битами. Ученик написал текст {text} '
         f'Затем он вычеркнул из списка одно слово, а также лишние запятую и пробел. Размер предложения '
         f'уменьшился на {delta} байт. Напишите вычеркнутое слово.')
    ex = f'{delta} байт = {delta * 8} бит = {delta_chars} символов; из них 2 — запятая и пробел, значит в слове {len(removed)} букв.'
    return card('inf-oge-1', 'text', q, removed, ex), {'words': words, 'bits': bits, 'delta': delta}


def check_oge1(p, c):
    L = p['delta'] * 8 // p['bits'] - 2
    m = [w for w in p['words'] if len(w) == L]
    return m == [c['a']]


# ---------------------------------------------------------------- ОГЭ 2: декодирование


def gen_oge2(rng):
    letters = rng.sample('АБВГДЕЖИКЛМНОПРСТ', rng.randint(4, 6))
    codes = random_prefix_code(rng, len(letters))
    table = dict(zip(letters, codes))
    msg = ''.join(rng.choice(letters) for _ in range(rng.randint(4, 7)))
    bits = ''.join(table[ch] for ch in msg)
    q = ('Разведчик передал сообщение, закодированное так: ' + ', '.join(f'{k} — {v}' for k, v in table.items()) +
         f'. Получена двоичная строка {bits}. Расшифруйте её и запишите буквы.')
    ex = 'Код префиксный (условие Фано): читаем слева направо, как только набралось кодовое слово — это буква.'
    return card('inf-oge-2', 'text', q, msg, ex), {'table': table, 'bits': bits}


def check_oge2(p, c):
    # второй способ: перебор всех разбиений (проверяет и однозначность)
    inv = {v: k for k, v in p['table'].items()}
    res = []

    def rec(i, acc):
        if len(res) > 1:
            return
        if i == len(p['bits']):
            res.append(acc)
            return
        for L in range(1, 7):
            if p['bits'][i:i + L] in inv:
                rec(i + L, acc + inv[p['bits'][i:i + L]])
    rec(0, '')
    return res == [c['a']]


# ---------------------------------------------------------------- ОГЭ 3: истинность высказывания


def gen_oge3(rng):
    a = rng.randint(5, 80)
    b = a + rng.randint(3, 30)
    kind = rng.choice(['min_notlt_odd', 'max_lt_notodd', 'min_and_div'])
    if kind == 'min_notlt_odd':
        ans = next(x for x in range(0, 1000) if not (x < a) and x % 2 == 1)
        q = f'Напишите наименьшее натуральное число x, для которого истинно высказывание: НЕ (x < {a}) И (x нечётное).'
    elif kind == 'max_lt_notodd':
        ans = max(x for x in range(0, 1000) if x < b and not (x % 2 == 1))
        q = f'Напишите наибольшее натуральное число x, для которого истинно высказывание: (x < {b}) И НЕ (x нечётное).'
    else:
        k = rng.choice([3, 4, 5, 7])
        ans = next(x for x in range(1, 1000) if x > a and x % k == 0)
        q = f'Напишите наименьшее натуральное число x, для которого истинно высказывание: НЕ (x ≤ {a}) И (x делится на {k}).'
    ex = 'Снимаем отрицание (НЕ (x < a) ⇔ x ≥ a) и ищем крайнее число, удовлетворяющее обоим условиям.'
    return card('inf-oge-3', 'num', q, str(ans), ex), {'kind': kind, 'a': a, 'b': b, 'q': q}


def check_oge3(p, c):
    a, b = p['a'], p['b']
    if p['kind'] == 'min_notlt_odd':
        v = a if a % 2 else a + 1
    elif p['kind'] == 'max_lt_notodd':
        v = b - 1 if (b - 1) % 2 == 0 else b - 2
    else:
        k = int(re.search(r'делится на (\d+)', p['q']).group(1))
        v = (a // k + 1) * k
    return str(v) == c['a']


# ---------------------------------------------------------------- ОГЭ 4: кратчайший путь по таблице


def gen_oge4(rng):
    names = 'ABCDEF'
    n = rng.randint(5, 6)
    V = names[:n]
    edges = {}
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < 0.55:
                edges[(V[i], V[j])] = rng.randint(1, 9)
    via = rng.choice([None, rng.choice(V[1:n - 1])])

    def dist(src):
        D = {v: math.inf for v in V}
        D[src] = 0
        todo = set(V)
        while todo:
            u = min(todo, key=lambda v: D[v])
            todo.remove(u)
            for (x, y), w in edges.items():
                for s, t in ((x, y), (y, x)):
                    if s == u and D[u] + w < D[t]:
                        D[t] = D[u] + w
        return D
    if via:
        ans = dist(V[0])[via] + dist(via)[V[-1]]
    else:
        ans = dist(V[0])[V[-1]]
    if ans == math.inf or (V[0], V[-1]) in edges:
        return gen_oge4(rng)
    tab = '; '.join(f'{x}–{y}: {w}' for (x, y), w in edges.items())
    extra = f', проходящего через пункт {via}' if via else ''
    q = (f'Между населёнными пунктами {", ".join(V)} построены дороги, их длины (в км): {tab}. Других дорог нет. '
         f'Определите длину кратчайшего пути между пунктами {V[0]} и {V[-1]}{extra}. Передвигаться можно только по указанным дорогам.')
    ex = 'Рисуем граф и идём от A, записывая у каждой вершины наименьшее найденное расстояние (алгоритм Дейкстры).'
    return card('inf-oge-4', 'num', q, str(ans), ex), {'V': V, 'edges': edges, 'via': via}


def check_oge4(p, c):
    V, E = p['V'], p['edges']
    D = {(a, b): (0 if a == b else math.inf) for a in V for b in V}
    for (x, y), w in E.items():
        D[x, y] = D[y, x] = min(D[x, y], w)
    for k in V:  # Флойд — Уоршелл
        for i in V:
            for j in V:
                if D[i, k] + D[k, j] < D[i, j]:
                    D[i, j] = D[i, k] + D[k, j]
    v = D[V[0], p['via']] + D[p['via'], V[-1]] if p['via'] else D[V[0], V[-1]]
    return str(v) == c['a']


# ---------------------------------------------------------------- ОГЭ 5: исполнитель с неизвестной командой


def gen_oge5(rng):
    add = rng.randint(1, 9)
    b = rng.randint(2, 9)
    start = rng.randint(1, 20)
    prog = ''.join(rng.choice('12') for _ in range(5))
    if '1' not in prog or '2' not in prog:
        return gen_oge5(rng)
    op_unknown = rng.choice(['mul', 'add'])

    def run(bb):
        x = start
        for ch in prog:
            if ch == '1':
                x = x + add if op_unknown == 'mul' else x + bb
            else:
                x = x * bb if op_unknown == 'mul' else x * add
        return x
    res = run(b)
    sols = [bb for bb in range(2, 50) if run(bb) == res]
    if sols != [b] or add in (0, 1) and op_unknown == 'add':
        return gen_oge5(rng)
    if op_unknown == 'mul':
        cmds = f'1. прибавь {add}; 2. умножь на b (b — неизвестное натуральное число ≥ 2)'
    else:
        cmds = f'1. прибавь b (b — неизвестное натуральное число ≥ 2); 2. умножь на {add}'
    q = f'У исполнителя две команды: {cmds}. Программа {prog} переводит число {start} в число {res}. Определите b.'
    ex = 'Подставляем b = 2, 3, … или составляем уравнение по программе.'
    return card('inf-oge-5', 'num', q, str(b), ex), {'add': add, 'start': start, 'prog': prog, 'op': op_unknown, 'res': res}


def check_oge5(p, c):
    # второй способ: символьно — результат линейный/полиномиальный по b, решаем перебором в обратную сторону
    for bb in range(2, 50):
        x = p['start']
        for ch in p['prog']:
            if p['op'] == 'mul':
                x = x + p['add'] if ch == '1' else x * bb
            else:
                x = x + bb if ch == '1' else x * p['add']
        if x == p['res']:
            return str(bb) == c['a']
    return False


# ---------------------------------------------------------------- ОГЭ 6: сколько раз программа напечатает YES


def gen_oge6(rng):
    A, B = rng.randint(2, 12), rng.randint(2, 12)
    op = rng.choice(['or', 'and'])
    cmp1, cmp2 = rng.choice(['>', '<']), rng.choice(['>', '<'])
    pairs = [(rng.randint(-5, 15), rng.randint(-5, 15)) for _ in range(9)]
    f = {'>': lambda u, v: u > v, '<': lambda u, v: u < v}
    ok = lambda s, t: (f[cmp1](s, A) or f[cmp2](t, B)) if op == 'or' else (f[cmp1](s, A) and f[cmp2](t, B))  # noqa: E731
    ans = sum(1 for s, t in pairs if ok(s, t))
    word = 'or' if op == 'or' else 'and'
    code = f"s = int(input())\nt = int(input())\nif s {cmp1} {A} {word} t {cmp2} {B}:\n    print('YES')\nelse:\n    print('NO')"
    q = ('Дана программа на Python:\n' + code + '\nБыло проведено 9 запусков с парами (s, t): ' +
         ', '.join(f'({s}, {t})' for s, t in pairs) + '. Сколько было запусков, при которых программа напечатала «YES»?')
    ex = f'Проверяем условие для каждой пары: {"хотя бы одно" if op == "or" else "оба"} сравнения должны быть истинны.'
    return card('inf-oge-6', 'num', q, str(ans), ex), {'code': code, 'pairs': pairs}


def check_oge6(p, c):
    # второй способ: реально выполняем код программы
    cnt = 0
    for s, t in p['pairs']:
        out = []
        it = iter([str(s), str(t)])
        exec(p['code'], {'input': lambda: next(it), 'print': out.append, 'int': int})
        cnt += out == ['YES']
    return str(cnt) == c['a']


# ---------------------------------------------------------------- ОГЭ 7: адрес файла в интернете


def gen_oge7(rng):
    proto = rng.choice(['http', 'https', 'ftp'])
    host = rng.choice(['shkola', 'lesson', 'kvant', 'nauka', 'robot', 'kniga']) + rng.choice(['.ru', '.org', '.net', '.info'])
    fname = rng.choice(['plan', 'test', 'map', 'news', 'otvet', 'draft']) + rng.choice(['.txt', '.doc', '.html', '.png', '.pdf'])
    parts = [proto, '://', host, '/', fname]
    # фрагменты: протокол, '://', имя сервера разбито на 2, '/', имя файла разбито на 2 — перемешиваем
    h1, h2 = host[:len(host) // 2], host[len(host) // 2:]
    f1, f2 = fname[:len(fname) // 2], fname[len(fname) // 2:]
    frags = [proto, '://', h1, h2, '/', f1, f2]
    order = list(range(len(frags)))
    rng.shuffle(order)
    labels = 'АБВГДЕЖ'
    shown = {labels[i]: frags[j] for i, j in enumerate(order)}
    ans = ''.join(next(l for l, v in shown.items() if v == fr) for fr in frags)
    q = (f'Доступ к файлу {fname}, находящемуся на сервере {host}, осуществляется по протоколу {proto}. '
         'Фрагменты адреса файла закодированы буквами: ' + '; '.join(f'{k}) {v}' for k, v in shown.items()) +
         '. Запишите последовательность букв, кодирующую адрес файла.')
    ex = 'Порядок: протокол, «://», имя сервера, «/», имя файла. ' + ''.join(parts)
    if len(set(frags)) != len(frags):
        return gen_oge7(rng)
    return card('inf-oge-7', 'text', q, ans, ex), {'shown': shown, 'url': ''.join(parts)}


def check_oge7(p, c):
    return ''.join(p['shown'][ch] for ch in c['a']) == p['url']


# ---------------------------------------------------------------- ОГЭ 10: сравнение чисел в разных системах


def gen_oge10(rng):
    nums = rng.sample(range(20, 255), 3)
    bases = [2, 8, 16]
    rng.shuffle(bases)
    shown = [(to_base(n, b), b) for n, b in zip(nums, bases)]
    mode = rng.choice(['max', 'min'])
    ans = max(nums) if mode == 'max' else min(nums)
    q = ('Среди приведённых ниже трёх чисел, записанных в различных системах счисления, найдите '
         f'{"максимальное" if mode == "max" else "минимальное"} и запишите его в десятичной системе счисления: ' +
         ', '.join(f'{s}₍{b}₎' for s, b in shown) + '. В ответе запишите только число.')
    ex = 'Переводим каждое число в десятичную систему: ' + ', '.join(f'{s}₍{b}₎ = {n}' for (s, b), n in zip(shown, nums))
    return card('inf-oge-10', 'num', q, str(ans), ex), {'shown': shown, 'mode': mode}


def check_oge10(p, c):
    vals = [int(s, b) for s, b in p['shown']]
    return str(max(vals) if p['mode'] == 'max' else min(vals)) == c['a']


# ---------------------------------------------------------------- 5–9 класс: перевод чисел, единицы информации


def gen_g8_base(rng):
    kind = rng.choice(['to10', 'to2', 'ones'])
    n = rng.randint(5, 1023)
    if kind == 'to10':
        b = rng.choice([2, 8, 16])
        q = f'Переведите число {to_base(n, b)}₍{b}₎ в десятичную систему счисления.'
        return card('inf-8-base', 'num', q, str(n), f'Раскладываем по степеням {b}.'), {'kind': kind, 's': to_base(n, b), 'b': b}
    if kind == 'to2':
        q = f'Переведите число {n} в двоичную систему счисления. В ответе запишите только цифры.'
        return card('inf-8-base', 'text', q, bin(n)[2:], 'Делим на 2 и выписываем остатки снизу вверх.'), {'kind': kind, 'n': n}
    q = f'Сколько единиц в двоичной записи числа {n}?'
    return card('inf-8-base', 'num', q, str(bin(n).count('1')), 'Раскладываем на сумму степеней двойки.'), {'kind': kind, 'n': n}


def check_g8_base(p, c):
    if p['kind'] == 'to10':
        return str(int(p['s'], p['b'])) == c['a']
    n = p['n']
    s = ''
    while n:
        s = str(n % 2) + s
        n //= 2
    return (s == c['a']) if p['kind'] == 'to2' else (str(s.count('1')) == c['a'])


def gen_g7_units(rng):
    units = [('бит', 1), ('байт', 8), ('Кбайт', 8 * 1024), ('Мбайт', 8 * 1024 ** 2)]
    i = rng.randint(1, 3)
    j = rng.randint(0, i - 1)
    x = rng.choice([1, 2, 3, 4, 5, 8, 16, 32, 64, 0.5, 0.25]) if i > 1 else rng.randint(2, 512)
    val = x * units[i][1] / units[j][1]
    if val != int(val) or x != int(x) and i < 2:
        return gen_g7_units(rng)
    xs = str(x).replace('.', ',')
    q = f'Сколько {units[j][0]} в {xs} {units[i][0]}?'
    wrong = [int(x * 1000 ** (i - j)) if j > 0 else int(x * 8 * 1000 ** (i - 1)), int(val // 8) or 1, int(val * 8)]
    o, a = one_options(int(val), [w for w in wrong if w != int(val)] + [int(val) + 24], rng)
    ex = '1 байт = 8 бит, 1 Кбайт = 1024 байта, 1 Мбайт = 1024 Кбайт.'
    return card('inf-7-units', 'one', q, a, ex, o=o), {'x': x, 'i': i, 'j': j}


def check_g7_units(p, c):
    f = [1, 8, 8192, 8388608]
    v = int(p['x'] * f[p['i']] // f[p['j']])
    return any(o['id'] == c['a'] and o['t'] == str(v) for o in c['o'])


# ---------------------------------------------------------------- ЕГЭ 18: Робот на клетчатом поле (мини-версия без файла)


def gen_ege18(rng):
    n, m = rng.randint(3, 5), rng.randint(3, 5)
    g = [[rng.randint(1, 99) for _ in range(m)] for _ in range(n)]
    best = {}
    for i in range(n):
        for j in range(m):
            prev = [best[x] for x in ((i - 1, j), (i, j - 1)) if x in best]
            mx = max(p[0] for p in prev) if prev else 0
            mn = min(p[1] for p in prev) if prev else 0
            best[i, j] = (mx + g[i][j], mn + g[i][j])
    mx, mn = best[n - 1, m - 1]
    rows = ' / '.join(' '.join(f'{v:2d}' for v in r) for r in g)
    q = (f'Робот стоит в левой верхней клетке поля {n}×{m} и за ход сдвигается на одну клетку вправо или вниз, '
         f'пока не придёт в правую нижнюю клетку. В каждой клетке лежит монета указанного достоинства; робот '
         f'собирает монеты во всех посещённых клетках, включая начальную и конечную. Поле по строкам: {rows}. '
         f'Найдите максимальную и минимальную возможные суммы. Запишите два числа через пробел: сначала максимум.')
    ex = 'Динамика: в каждой клетке лучшая сумма = значение клетки + лучшая из сумм сверху и слева (в таблице — формула =МАКС(...)+...).'
    return card('inf-ege-18', 'text', q, f'{mx} {mn}', ex), {'g': g}


def check_ege18(p, c):
    g = p['g']
    n, m = len(g), len(g[0])
    sums = []
    for path in itertools.combinations(range(n + m - 2), n - 1):  # на каких шагах идём вниз
        i = j = 0
        s = g[0][0]
        for step in range(n + m - 2):
            if step in path:
                i += 1
            else:
                j += 1
            s += g[i][j]
        sums.append(s)
    return f'{max(sums)} {min(sums)}' == c['a']


# ---------------------------------------------------------------- ЕГЭ 22: параллельные процессы (мини-версия)


def gen_ege22(rng):
    n = rng.randint(5, 9)
    procs = []
    for i in range(1, n + 1):
        deps = sorted(rng.sample(range(1, i), rng.randint(0, min(3, i - 1)))) if i > 1 else []
        procs.append((i, rng.randint(1, 15), deps))
    fin = {}
    for i, t, deps in procs:
        fin[i] = max((fin[d] for d in deps), default=0) + t
    ask = rng.choice(['total', 'one'])
    if ask == 'total':
        ans = max(fin.values())
        tail = 'Определите минимальное время (в мс), через которое завершится выполнение всех процессов.'
    else:
        target = rng.randint(2, n)
        ans = fin[target]
        tail = f'Определите минимальное время (в мс), через которое завершится процесс {target}.'
    rows = '; '.join(f'ID {i}: {t} мс, ' + ('зависит от ' + ', '.join(map(str, d)) if d else 'независимый') for i, t, d in procs)
    q = ('Процессы могут выполняться параллельно, число одновременно выполняемых процессов не ограничено. '
         'Процесс начинается сразу после завершения всех процессов, от которых он зависит. '
         f'Процессы: {rows}. {tail}')
    ex = 'Для каждого процесса: время окончания = время работы + максимум времён окончания его зависимостей.'
    return card('inf-ege-22', 'num', q, str(ans), ex), {'procs': procs, 'ask': ask, 'q': q}


def check_ege22(p, c):
    # второй способ: пошаговая «симуляция по миллисекундам»
    procs = {i: (t, d) for i, t, d in p['procs']}
    start, done, time = {}, {}, 0
    while len(done) < len(procs):
        for i, (t, d) in procs.items():
            if i not in start and all(x in done and done[x] <= time for x in d):
                start[i] = time
        for i in start:
            if i not in done and start[i] + procs[i][0] == time + 1:
                done[i] = time + 1
        time += 1
    if p['ask'] == 'total':
        return str(max(done.values())) == c['a']
    target = int(re.search(r'завершится процесс (\d+)', p['q']).group(1))
    return str(done[target]) == c['a']


# ---------------------------------------------------------------- ОГЭ 8: запросы к поисковому серверу


def gen_oge8(rng):
    a, b = rng.choice([('Кошки', 'Собаки'), ('Физика', 'Химия'), ('Лыжи', 'Коньки'), ('Пушкин', 'Лермонтов')])
    x, y, z = rng.randint(50, 900), rng.randint(50, 900), rng.randint(10, 500)  # только A, только B, оба
    ask = rng.choice(['and', 'or', 'a'])
    known = {'or': (f'{a} | {b}', x + y + z), 'and': (f'{a} & {b}', z), 'a': (a, x + z), 'b': (b, y + z)}
    show = [k for k in ('or', 'and', 'a', 'b') if k != ask][:3]
    if ask == 'a':
        show = ['or', 'and', 'b']
    tbl = '; '.join(f'«{known[k][0]}» — {known[k][1]} тыс.' for k in show)
    q = (f'В языке запросов «|» означает «ИЛИ», «&» — «И». Известно количество найденных страниц: {tbl}. '
         f'Какое количество страниц (в тысячах) будет найдено по запросу «{known[ask][0]}»?')
    ex = 'Формула включений-исключений: |A ИЛИ B| = |A| + |B| − |A И B|. Удобно нарисовать круги Эйлера.'
    return card('inf-oge-8', 'num', q, str(known[ask][1]), ex), {'x': x, 'y': y, 'z': z, 'ask': ask, 'show': show,
                                                                 'vals': {k: known[k][1] for k in show}}


def check_oge8(p, c):
    v = p['vals']
    ask = p['ask']
    if ask == 'and':
        r = v['a'] + v['b'] - v['or']
    elif ask == 'or':
        r = v['a'] + v['b'] - v['and']
    else:
        r = v['or'] - v['b'] + v['and']
    return str(r) == c['a']


# ---------------------------------------------------------------- ОГЭ 9 / ЕГЭ 23 (2027): число путей в графе


def gen_oge9(rng):
    V = list('АБВГДЕЖЗИК')[:rng.randint(7, 10)]
    V[-1] = 'К' if V[-1] != 'К' else V[-1]
    edges = set()
    for i in range(len(V) - 1):
        edges.add((V[i], V[rng.randint(i + 1, min(len(V) - 1, i + 3))]))
        for _ in range(rng.randint(0, 2)):
            j = rng.randint(i + 1, len(V) - 1)
            edges.add((V[i], V[j]))
    edges = sorted(edges)
    via = rng.choice([None, None, rng.choice(V[1:-1])])
    f = {V[0]: 1}
    for v in V[1:]:
        f[v] = sum(f[a] for a, b in edges if b == v)
    if via:
        g = {via: 1}
        for v in V[V.index(via) + 1:]:
            g[v] = sum(g.get(a, 0) for a, b in edges if b == v)
        ans = f[via] * g[V[-1]]
    else:
        ans = f[V[-1]]
    if ans == 0 or ans > 500:
        return gen_oge9(rng)
    extra = f', проходящих через город {via}' if via else ''
    q = ('Схема дорог между городами задана списком дорог с односторонним движением: ' +
         ', '.join(f'{a}→{b}' for a, b in edges) +
         f'. Сколько существует различных путей из города {V[0]} в город {V[-1]}{extra}?')
    ex = 'Идём по городам по порядку: число путей в город = сумма чисел путей в города, из которых в него ведут дороги.'
    return card('inf-oge-9', 'num', q, str(ans), ex), {'V': V, 'edges': edges, 'via': via}


def check_oge9(p, c):
    adj = {}
    for a, b in p['edges']:
        adj.setdefault(a, []).append(b)
    cnt = 0
    stack = [(p['V'][0], p['V'][0] == p['via'])]
    while stack:  # перебор всех путей
        v, seen = stack.pop()
        if v == p['V'][-1]:
            cnt += (seen or not p['via'])
            continue
        for w in adj.get(v, []):
            stack.append((w, seen or w == p['via']))
    return str(cnt) == c['a']


# ---------------------------------------------------------------- ЕГЭ 1: граф и весовая таблица


def gen_ege1(rng):
    n = rng.randint(6, 7)
    letters = 'АБВГДЕЖ'[:n]
    while True:
        edges = set()
        for i in range(1, n):  # связный граф: остов + случайные рёбра
            edges.add(frozenset((i, rng.randrange(i))))
        for _ in range(rng.randint(2, 4)):
            a, b = rng.sample(range(n), 2)
            edges.add(frozenset((a, b)))
        perm = list(range(n))
        rng.shuffle(perm)  # вершина графа v ↔ пункт таблицы perm[v]+1
        w = {e: rng.randint(5, 60) for e in edges}
        x, y = sorted(rng.choice(sorted(edges, key=sorted)))
        tbl = {frozenset((perm[a] + 1, perm[b] + 1)): w[frozenset((a, b))] for a, b in map(sorted, edges)}
        # все изоморфизмы граф → таблица: ответ должен совпадать во всех
        answers = set()
        for pm in itertools.permutations(range(1, n + 1)):
            if all(frozenset((pm[a], pm[b])) in tbl for a, b in map(sorted, edges)):
                answers.add(tbl[frozenset((pm[x], pm[y]))])
        if len(answers) == 1:
            break
    ans = answers.pop()
    adj = '; '.join(f'{letters[a]}–{letters[b]}' for a, b in sorted(map(sorted, edges)))
    rows = '; '.join(f'П{i}–П{j}: {v}' for (i, j), v in sorted((tuple(sorted(k)), v) for k, v in tbl.items()))
    q = (f'Схема дорог (граф) задана списком рёбер: {adj}. В таблице указаны длины дорог между пунктами '
         f'П1–П{n}, но номера пунктов в таблице не совпадают с буквами на схеме: {rows}. '
         f'Какова длина дороги из пункта {letters[x]} в пункт {letters[y]}?')
    ex = ('Сопоставляем вершины по числу дорог (степени) и по соседям: сначала вершины с уникальной степенью, '
          'затем их соседей. Длину берём из таблицы для найденной пары номеров.')
    return card('inf-ege-1', 'num', q, str(ans), ex), {'n': n, 'edges': [tuple(sorted(e)) for e in edges],
                                                        'tbl': {tuple(sorted(k)): v for k, v in tbl.items()},
                                                        'xy': (x, y)}


def check_ege1(p, c):
    # второй способ: поиск с возвратом по степеням вместо полного перебора перестановок
    n = p['n']
    g_adj = {v: set() for v in range(n)}
    for a, b in p['edges']:
        g_adj[a].add(b)
        g_adj[b].add(a)
    t_adj = {v: set() for v in range(1, n + 1)}
    for a, b in p['tbl']:
        t_adj[a].add(b)
        t_adj[b].add(a)
    res = set()

    def rec(v, m):
        if v == n:
            x, y = p['xy']
            a, b = sorted((m[x], m[y]))
            res.add(p['tbl'][a, b])
            return
        for u in t_adj:
            if u in m.values() or len(t_adj[u]) != len(g_adj[v]):
                continue
            if all((m[w] in t_adj[u]) == (w in g_adj[v]) for w in m):
                m[v] = u
                rec(v + 1, m)
                del m[v]
    rec(0, {})
    return len(res) == 1 and str(res.pop()) == c['a']


# ---------------------------------------------------------------- ЕГЭ 3: реляционная БД (мини-версия без файла)

SHOPS3 = {'М1': 'Заречный', 'М2': 'Центральный', 'М3': 'Заречный', 'М4': 'Северный', 'М5': 'Центральный'}
GOODS3 = {101: ('Кефир', 'Молочные'), 102: ('Сыр', 'Молочные'), 103: ('Батон', 'Хлеб'),
          104: ('Сушки', 'Хлеб'), 105: ('Яблоки', 'Фрукты'), 106: ('Груши', 'Фрукты')}


def gen_ege3(rng):
    shops = rng.sample(sorted(SHOPS3), 4)
    goods = rng.sample(sorted(GOODS3), 4)
    ops = []
    for i in range(rng.randint(12, 16)):
        ops.append((i + 1, rng.randint(1, 6), rng.choice(shops), rng.choice(goods),
                    rng.choice(['поступление', 'продажа']), rng.randint(1, 40)))
    ask = rng.choice(['district', 'dept', 'balance'])
    d1, d2 = sorted(rng.sample(range(1, 7), 2))
    if ask == 'district':
        dist = rng.choice(sorted({SHOPS3[s] for s in shops}))
        typ = rng.choice(['поступление', 'продажа'])
        good = rng.choice(goods)
        ans = sum(q for _, d, s, g, t, q in ops if SHOPS3[s] == dist and g == good and t == typ and d1 <= d <= d2)
        tail = (f'Сколько единиц товара «{GOODS3[good][0]}» пришлось на операции «{typ}» в магазинах района '
                f'{dist} с {d1} по {d2} июня включительно?')
        par = {'ask': ask, 'dist': dist, 'typ': typ, 'good': good}
    elif ask == 'dept':
        dept = rng.choice(sorted({GOODS3[g][1] for g in goods}))
        ans = sum(q for _, d, s, g, t, q in ops if GOODS3[g][1] == dept and t == 'продажа' and d1 <= d <= d2)
        tail = f'Сколько единиц товаров отдела «{dept}» продано во всех магазинах с {d1} по {d2} июня включительно?'
        par = {'ask': ask, 'dept': dept}
    else:
        shop = rng.choice(shops)
        ans = sum((q if t == 'поступление' else -q) for _, d, s, g, t, q in ops if s == shop and d1 <= d <= d2)
        tail = (f'На сколько единиц изменилось количество товаров в магазине {shop} с {d1} по {d2} июня включительно '
                '(поступления минус продажи; ответ может быть отрицательным)?')
        par = {'ask': ask, 'shop': shop}
    if ans == 0:
        return gen_ege3(rng)
    t1 = '; '.join(f'{s} — {SHOPS3[s]}' for s in shops)
    t2 = '; '.join(f'{g} — {GOODS3[g][0]} ({GOODS3[g][1]})' for g in goods)
    t3 = '; '.join(f'{i}) {d} июня, {s}, арт. {g}, {t}, {q} шт' for i, d, s, g, t, q in ops)
    q = (f'Мини-база данных сети магазинов. Магазины (ID — район): {t1}. Товары (артикул — название, отдел): {t2}. '
         f'Движение товаров: {t3}. {tail}')
    ex = ('Фильтруем таблицу «Движение» по датам и типу операции, по ID магазина подтягиваем район, по артикулу — '
          'товар и отдел (в ЭТ — ВПР/фильтр, затем СУММ).')
    par.update(ops=ops, d1=d1, d2=d2, shops=shops, goods=goods)
    return card('inf-ege-3', 'num', q, str(ans), ex), par


def check_ege3(p, c):
    # второй способ: настоящий SQL-запрос в sqlite3
    import sqlite3
    db = sqlite3.connect(':memory:')
    db.execute('create table shop(id text, dist text)')
    db.execute('create table good(id int, name text, dept text)')
    db.execute('create table op(id int, d int, shop text, good int, typ text, q int)')
    db.executemany('insert into shop values (?,?)', [(s, SHOPS3[s]) for s in p['shops']])
    db.executemany('insert into good values (?,?,?)', [(g, *GOODS3[g]) for g in p['goods']])
    db.executemany('insert into op values (?,?,?,?,?,?)', p['ops'])
    base = ('from op join shop on op.shop = shop.id join good on op.good = good.id '
            'where op.d between ? and ?')
    if p['ask'] == 'district':
        r = db.execute('select sum(q) ' + base + ' and shop.dist = ? and good.id = ? and typ = ?',
                       (p['d1'], p['d2'], p['dist'], p['good'], p['typ'])).fetchone()[0]
    elif p['ask'] == 'dept':
        r = db.execute('select sum(q) ' + base + " and good.dept = ? and typ = 'продажа'",
                       (p['d1'], p['d2'], p['dept'])).fetchone()[0]
    else:
        r = db.execute("select sum(case typ when 'поступление' then q else -q end) " + base + ' and op.shop = ?',
                       (p['d1'], p['d2'], p['shop'])).fetchone()[0]
    return str(r or 0) == c['a']


# ---------------------------------------------------------------- ЕГЭ 6: Черепаха, два прямоугольника


def gen_ege6(rng):
    a, b = rng.randint(4, 16), rng.randint(4, 16)
    e, f = rng.randint(4, 16), rng.randint(4, 16)
    cy, dx = rng.randint(1, a - 1), rng.randint(1, b - 1)  # второй прямоугольник начинается внутри первого
    cmds = (f'Повтори 2 [Вперёд {a} Направо 90 Вперёд {b} Направо 90] Поднять хвост Вперёд {cy} Направо 90 '
            f'Вперёд {dx} Налево 90 Опустить хвост Повтори 2 [Вперёд {e} Направо 90 Вперёд {f} Направо 90]')
    r1 = (0, b, 0, a)
    r2 = (dx, dx + f, cy, cy + e)
    ix = (max(r1[0], r2[0]), min(r1[1], r2[1]))
    iy = (max(r1[2], r2[2]), min(r1[3], r2[3]))
    ask = rng.choice(['inter', 'union'])
    if ask == 'inter':
        ans = max(0, ix[1] - ix[0] - 1) * max(0, iy[1] - iy[0] - 1)
        tail = ('Определите, сколько точек с целочисленными координатами находится внутри пересечения областей, '
                'ограниченных нарисованными линиями. Точки на линиях не учитывайте.')
    else:
        closed = lambda r: (r[1] - r[0] + 1) * (r[3] - r[2] + 1)  # noqa: E731
        both = max(0, ix[1] - ix[0] + 1) * max(0, iy[1] - iy[0] + 1)
        ans = closed(r1) + closed(r2) - both
        tail = ('Определите, сколько точек с целочисленными координатами находится внутри объединения областей, '
                'ограниченных нарисованными линиями, включая точки на линиях.')
    if ans == 0:
        return gen_ege6(rng)
    q = ('Черепаха стоит в начале координат и смотрит вдоль оси ординат (вверх); хвост опущен, при движении '
         f'остаётся след. Черепахе дан алгоритм: {cmds}. {tail}')
    ex = ('Рисуем: первая фигура — прямоугольник от (0; 0), вторая начинается в точке, куда черепаха пришла '
          'с поднятым хвостом. Внутренних целых точек в прямоугольнике w×h: (w − 1)(h − 1), с границей — (w + 1)(h + 1).')
    return card('inf-ege-6', 'num', q, str(ans), ex), {'cmds': cmds, 'ask': ask}


def check_ege6(p, c):
    # второй способ: исполняем команды черепахи и проверяем каждую точку по многоугольникам
    toks = re.findall(r'Повтори \d+ \[[^\]]*\]|Поднять хвост|Опустить хвост|Вперёд -?\d+|Направо \d+|Налево \d+',
                      p['cmds'])
    x = y = 0
    hx, hy = 0, 1
    pen, polys, cur = True, [], []

    def step(t):
        nonlocal x, y, hx, hy
        if t.startswith('Вперёд'):
            k = int(t.split()[1])
            x, y = x + hx * k, y + hy * k
            if pen:
                cur.append((x, y))
        elif t.startswith('Направо'):
            for _ in range(int(t.split()[1]) // 90):
                hx, hy = hy, -hx
        elif t.startswith('Налево'):
            for _ in range(int(t.split()[1]) // 90):
                hx, hy = -hy, hx
    for t in toks:
        if t.startswith('Повтори'):
            k = int(t.split()[1])
            cur = [(x, y)]
            for _ in range(k):
                for s in re.findall(r'(?:Вперёд|Направо|Налево) -?\d+', t):
                    step(s)
            polys.append(cur)
        elif t == 'Поднять хвост':
            pen = False
        elif t == 'Опустить хвост':
            pen = True
        else:
            step(t)

    def where(px, py, poly):  # 1 — внутри, 0 — на границе, -1 — снаружи
        for (x1, y1), (x2, y2) in zip(poly, poly[1:]):
            if min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2):
                return 0
        inside = False
        for (x1, y1), (x2, y2) in zip(poly, poly[1:]):
            if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
        return 1 if inside else -1
    xs = [q[0] for pl in polys for q in pl]
    ys = [q[1] for pl in polys for q in pl]
    cnt = 0
    for px in range(min(xs) - 1, max(xs) + 2):
        for py in range(min(ys) - 1, max(ys) + 2):
            w = [where(px, py, pl) for pl in polys]
            cnt += all(v == 1 for v in w) if p['ask'] == 'inter' else any(v >= 0 for v in w)
    return str(cnt) == c['a']


# ---------------------------------------------------------------- ЕГЭ 9: электронная таблица (мини-версия)

COND9 = {
    'pair': 'в строке ровно одно число повторяется дважды, остальные числа различны',
    'uniq': 'все числа строки различны',
    'tri': 'три наибольших числа строки (с учётом повторов) могут быть сторонами треугольника: '
           'наибольшее из них меньше суммы двух других',
}
COND9B = {
    'avg': 'среднее арифметическое повторяющихся чисел больше среднего арифметического неповторяющихся',
    'maxmin': 'удвоенная сумма наибольшего и наименьшего числа строки не больше суммы трёх остальных',
    'sum': 'сумма всех чисел строки чётна',
}


def row_ok9(r, c1, c2):
    cnt = Counter(r)
    if c1 == 'pair':
        a = sorted(cnt.values()) == [1] * (len(r) - 2) + [2]
    elif c1 == 'uniq':
        a = len(cnt) == len(r)
    else:
        s = sorted(r)
        a = s[-1] < s[-2] + s[-3]
    if c2 == 'avg':
        rep = [v for v in r if cnt[v] > 1]
        uni = [v for v in r if cnt[v] == 1]
        b = bool(rep) and bool(uni) and sum(rep) / len(rep) > sum(uni) / len(uni)
    elif c2 == 'maxmin':
        s = sorted(r)
        b = 2 * (s[0] + s[-1]) <= sum(s[1:-1])
    else:
        b = sum(r) % 2 == 0
    return a and b


def gen_ege9(rng):
    c1, c2 = rng.choice([('pair', 'avg'), ('uniq', 'maxmin'), ('uniq', 'sum'), ('tri', 'sum'), ('pair', 'sum')])
    rows = []
    for _ in range(rng.randint(8, 10)):
        r = [rng.randint(1, 30) for _ in range(5)]
        if c1 == 'pair' and rng.random() < 0.6:
            r[rng.randrange(5)] = r[rng.randrange(5)]
        rows.append(r)
    ans = sum(row_ok9(r, c1, c2) for r in rows)
    if ans == 0:
        return gen_ege9(rng)
    q = (f'В каждой строке электронной таблицы записаны пять натуральных чисел: ' +
         ' / '.join(' '.join(map(str, r)) for r in rows) +
         f'. Сколько строк удовлетворяют обоим условиям: 1) {COND9[c1]}; 2) {COND9B[c2]}?')
    ex = ('В ЭТ: СЧЁТЕСЛИ по строке — сколько раз встречается каждое число; затем СУММ/СРЗНАЧ по нужным клеткам '
          'и общая формула =ЕСЛИ(И(усл1; усл2); 1; 0), в конце — сумма столбца.')
    return card('inf-ege-9', 'num', q, str(ans), ex), {'rows': rows, 'c1': c1, 'c2': c2}


def check_ege9(p, c):
    # второй способ: попарные сравнения без Counter и без сортировки
    def ok(r):
        eq = [sum(1 for y in r if y == x) for x in r]
        if p['c1'] == 'pair':
            a = eq.count(2) == 2 and eq.count(1) == len(r) - 2
        elif p['c1'] == 'uniq':
            a = all(e == 1 for e in eq)
        else:
            import heapq
            t = heapq.nlargest(3, r)
            a = t[0] < t[1] + t[2]
        if p['c2'] == 'avg':
            rep = [x for x, e in zip(r, eq) if e > 1]
            uni = [x for x, e in zip(r, eq) if e == 1]
            b = rep and uni and sum(rep) * len(uni) > sum(uni) * len(rep)
        elif p['c2'] == 'maxmin':
            b = 2 * (max(r) + min(r)) <= sum(r) - max(r) - min(r)
        else:
            b = not sum(r) & 1
        return bool(a and b)
    return str(sum(ok(r) for r in p['rows'])) == c['a']


# ---------------------------------------------------------------- ЕГЭ 17: обработка последовательности (мини-версия)


def gen_ege17(rng):
    seq = [rng.randint(-99, 99) for _ in range(rng.randint(12, 16))]
    k = rng.choice([3, 4, 5, 7])
    last = rng.randint(1, 9)
    mode = rng.choice(['div', 'last'])
    ends = [x for x in seq if abs(x) % 10 == last]
    if mode == 'last' and not ends:
        return gen_ege17(rng)
    lim = max(ends) if mode == 'last' else None
    pairs = []
    for x, y in zip(seq, seq[1:]):
        if mode == 'div':
            good = (x % k == 0) != (y % k == 0)
        else:
            good = (abs(x) % 10 == last or abs(y) % 10 == last) and x + y > lim
        if good:
            pairs.append(x + y)
    if not pairs:
        return gen_ege17(rng)
    ans = f'{len(pairs)} {max(pairs)}'
    cond = (f'ровно одно из двух чисел делится на {k}' if mode == 'div' else
            f'хотя бы одно из чисел оканчивается на {last}, а сумма пары больше наибольшего из всех чисел '
            f'последовательности, оканчивающихся на {last}')
    q = (f'Дана последовательность целых чисел: {" ".join(map(str, seq))}. Парой называются два соседних элемента. '
         f'Найдите количество пар, в которых {cond}. В ответе запишите через пробел количество таких пар и '
         'наибольшую из сумм элементов таких пар.')
    ex = ('Один проход по парам (a[i], a[i+1]). У отрицательных чисел последнюю цифру берите через abs(x) % 10; '
          'в Python −7 % 3 = 2, а не −1, поэтому «делится» проверяется как x % k == 0.')
    return card('inf-ege-17', 'text', q, ans, ex), {'seq': seq, 'k': k, 'last': last, 'mode': mode}


def check_ege17(p, c):
    # второй способ: строковая проверка последней цифры и деление через divmod на модулях
    s = p['seq']
    endl = lambda x: str(x)[-1] == str(p['last'])  # noqa: E731
    divk = lambda x: divmod(abs(x), p['k'])[1] == 0  # noqa: E731
    lim = max((x for x in s if endl(x)), default=None)
    sums = []
    for i in range(len(s) - 1):
        a, b = s[i], s[i + 1]
        if p['mode'] == 'div':
            if divk(a) + divk(b) == 1:
                sums.append(a + b)
        elif (endl(a) or endl(b)) and a + b > lim:
            sums.append(a + b)
    return f'{len(sums)} {max(sums)}' == c['a']


# ---------------------------------------------------------------- ЕГЭ 24: обработка строки (мини-версия)


def gen_ege24(rng):
    alpha = rng.choice(['XYZ', 'ABC', 'KLMN', 'ACDO'])
    s = ''.join(rng.choice(alpha) for _ in range(rng.randint(28, 40)))
    mode = rng.choice(['run', 'noadj', 'without', 'pairs'])
    if mode == 'run':
        ch = rng.choice(alpha)
        ans = max((len(m) for m in re.findall(ch + '+', s)), default=0)
        ask = f'Определите максимальное количество идущих подряд символов {ch}.'
    elif mode == 'noadj':
        best = cur = 1
        for i in range(1, len(s)):
            cur = cur + 1 if s[i] != s[i - 1] else 1
            best = max(best, cur)
        ans, ch = best, None
        ask = 'Определите длину самой длинной подстроки, в которой никакие два соседних символа не совпадают.'
    elif mode == 'without':
        ch = rng.choice(alpha)
        ans = max(len(t) for t in s.split(ch))
        ask = f'Определите длину самой длинной подстроки, не содержащей символа {ch}.'
    else:
        ch = rng.choice(alpha) + rng.choice(alpha)
        best = cur = 0
        i = 0
        while i + 1 < len(s):  # подряд идущие пары ch: ch ch ch …
            if s[i:i + 2] == ch:
                cur += 1
                best = max(best, cur)
                i += 2
            else:
                cur = 0
                i += 1
        ans = best
        ask = (f'Определите наибольшее количество идущих подряд пар символов {ch} (пары не перекрываются: '
               f'например, в строке {ch * 3} три пары).')
    if ans < 2:
        return gen_ege24(rng)
    q = f'Дана строка из символов {", ".join(alpha)}: {s}. {ask}'
    ex = 'Один проход по строке со счётчиком текущей серии и максимумом; счётчик сбрасывается, когда серия рвётся.'
    return card('inf-ege-24', 'num', q, str(ans), ex), {'s': s, 'mode': mode, 'ch': ch}


def check_ege24(p, c):
    # второй способ: перебор всех подстрок (строка короткая)
    s, ch, m = p['s'], p['ch'], p['mode']
    n = len(s)
    best = 0
    for i in range(n):
        for j in range(i + 1, n + 1):
            t = s[i:j]
            if m == 'run' and set(t) == {ch}:
                best = max(best, len(t))
            elif m == 'noadj' and all(a != b for a, b in zip(t, t[1:])):
                best = max(best, len(t))
            elif m == 'without' and ch not in t:
                best = max(best, len(t))
            elif m == 'pairs' and len(t) % 2 == 0 and t == ch * (len(t) // 2):
                best = max(best, len(t) // 2)
    return str(best) == c['a']


# ---------------------------------------------------------------- ЕГЭ 25: маски и делители (мини-версия)


def mask_expand(mask, maxlen):
    """Все числа по маске: ? — ровно одна цифра, * — любая последовательность цифр (в т. ч. пустая)."""
    out = set()
    free = maxlen - len(mask.replace('*', '').replace('?', '')) - mask.count('?')
    stars = mask.count('*')
    for lens in itertools.product(range(free + 1), repeat=stars):
        if sum(lens) > free:
            continue
        slots = mask.count('?') + sum(lens)
        if slots > 5:
            continue
        for fill in itertools.product('0123456789', repeat=slots):
            it = iter(fill)
            s = ''
            li = iter(lens)
            for chh in mask:
                if chh == '?':
                    s += next(it)
                elif chh == '*':
                    s += ''.join(next(it) for _ in range(next(li)))
                else:
                    s += chh
            if s[0] != '0':
                out.add(int(s))
    return out


def gen_ege25(rng):
    kind = rng.choice(['mask', 'mask', 'div'])
    if kind == 'mask':
        d = rng.randint(3, 9)
        body = [str(rng.randint(1, 9))] + [str(rng.randint(0, 9)) for _ in range(rng.randint(1, 2))]
        mask = body[0] + ''.join(rng.choice(['?', '*', b]) for b in body[1:]) + rng.choice(['*', '?']) + str(rng.randint(0, 9))
        if '*' not in mask and '?' not in mask:
            return gen_ege25(rng)
        L = 6
        found = sorted(x for x in mask_expand(mask, L) if x % d == 0)
        if not 1 <= len(found) <= 400:
            return gen_ege25(rng)
        ask = rng.choice(['count', 'min', 'max'])
        ans = {'count': len(found), 'min': found[0], 'max': found[-1]}[ask]
        what = {'count': 'количество таких чисел', 'min': 'наименьшее такое число', 'max': 'наибольшее такое число'}[ask]
        q = (f'Маска числа — последовательность цифр, в которой «?» означает ровно одну цифру, а «*» — любую '
             f'последовательность цифр, в том числе пустую. Среди натуральных чисел, не превышающих 10⁶, найдите '
             f'соответствующие маске {mask} и делящиеся на {d}. Укажите {what}.')
        ex = ('Перебираем кратные d (range(d, 10**6+1, d)) и сверяем строку с маской: fnmatch или регулярное '
              'выражение, где ? → \\d, * → \\d*. Не забудьте: число не может начинаться с нуля.')
        return card('inf-ege-25', 'num', q, str(ans), ex), {'kind': kind, 'mask': mask, 'd': d, 'ask': ask}
    a = rng.randint(100, 2000)
    b = a + rng.randint(40, 200)
    k = rng.choice([2, 3])
    found = []
    for x in range(a, b + 1):
        ds = [t for t in range(2, int(x ** 0.5) + 1) if x % t == 0]
        ds = sorted(set(ds + [x // t for t in ds]))
        if len(ds) == k:
            found.append(x)
    if not found:
        return gen_ege25(rng)
    ask = rng.choice(['count', 'max'])
    ans = len(found) if ask == 'count' else found[-1]
    q = (f'Среди натуральных чисел от {a} до {b} включительно найдите числа, у которых ровно {k} различных '
         f'натуральных делителя, не считая единицы и самого числа. Укажите '
         f'{"их количество" if ask == "count" else "наибольшее такое число"}.')
    ex = ('Делители ищем до √x и добавляем парный x // t (у квадрата корень считаем один раз). Ровно 2 делителя — это '
          'p·q или p³, ровно 3 — это p⁴.')
    return card('inf-ege-25', 'num', q, str(ans), ex), {'kind': kind, 'a': a, 'b': b, 'k': k, 'ask': ask}


def check_ege25(p, c):
    if p['kind'] == 'mask':
        rx = re.compile('^' + p['mask'].replace('?', r'\d').replace('*', r'\d*') + '$')
        f = [x for x in range(p['d'], 10 ** 6 + 1, p['d']) if rx.match(str(x))]
        v = {'count': len(f), 'min': f[0] if f else None, 'max': f[-1] if f else None}[p['ask']]
        return str(v) == c['a']
    # второй способ: через разложение на простые — число делителей τ(x) − 2
    def tau(x):
        t, m, q = 1, x, 2
        while q * q <= m:
            e = 0
            while m % q == 0:
                m //= q
                e += 1
            t *= e + 1
            q += 1
        return t * (2 if m > 1 else 1)
    f = [x for x in range(p['a'], p['b'] + 1) if tau(x) - 2 == p['k']]
    return str(len(f) if p['ask'] == 'count' else f[-1]) == c['a']


# ---------------------------------------------------------------- ЕГЭ 26: жадный алгоритм (мини-версия)


def gen_ege26(rng):
    sizes = [rng.randint(5, 99) for _ in range(rng.randint(8, 12))]
    S = rng.randint(sum(sizes) // 4, sum(sizes) * 2 // 3)
    srt = sorted(sizes)
    cnt, tot = 0, 0
    for x in srt:
        if tot + x <= S:
            tot, cnt = tot + x, cnt + 1
        else:
            break
    # наибольший файл: заменяем последний взятый на самый большой, который ещё влезает
    base = tot - srt[cnt - 1]
    rest = srt[cnt - 1:]
    mx = max(x for x in rest if base + x <= S)
    if cnt in (0, len(sizes)):
        return gen_ege26(rng)
    q = (f'На диск объёмом {S} Мбайт нужно записать как можно больше файлов пользователей целиком. Размеры файлов '
         f'(Мбайт): {" ".join(map(str, sizes))}. Определите максимальное число файлов, которые можно записать, и '
         'максимальный размер файла, который может оказаться на диске при таком максимальном количестве. '
         'Запишите два числа через пробел.')
    ex = ('Жадно: сортируем по возрастанию и берём, пока влезают — это максимум штук. Затем выкидываем самый большой '
          'из взятых и ищем наибольший файл из оставшихся, который помещается в освободившееся место.')
    return card('inf-ege-26', 'text', q, f'{cnt} {mx}', ex), {'sizes': sizes, 'S': S}


def check_ege26(p, c):
    # второй способ: полный перебор подмножеств
    best = (0, 0)
    s = p['sizes']
    for mask in range(1 << len(s)):
        sub = [s[i] for i in range(len(s)) if mask >> i & 1]
        if sum(sub) <= p['S'] and sub:
            best = max(best, (len(sub), max(sub)))
    return f'{best[0]} {best[1]}' == c['a']


# ---------------------------------------------------------------- ЕГЭ 27: кластеры и центроид (мини-версия)


def gen_ege27(rng):
    k = rng.choice([2, 3])
    centers = []
    while len(centers) < k:
        cx, cy = rng.randint(0, 30), rng.randint(0, 30)
        if all(math.dist((cx, cy), q) > 12 for q in centers):
            centers.append((cx, cy))
    pts, lab = [], []
    sizes = rng.sample(range(4, 9), k)
    for ci, ((cx, cy), m) in enumerate(zip(centers, sizes)):
        while sum(1 for l in lab if l == ci) < m:
            x, y = round(cx + rng.uniform(-2, 2), 1), round(cy + rng.uniform(-2, 2), 1)
            if (x, y) not in pts:
                pts.append((x, y))
                lab.append(ci)
    order = list(range(len(pts)))
    rng.shuffle(order)
    pts, lab = [pts[i] for i in order], [lab[i] for i in order]
    # условие обещает: разные кластеры дальше 4, внутри — цепочки шагов ≤ 4; проверяем честно
    for i, j in itertools.combinations(range(len(pts)), 2):
        if lab[i] != lab[j] and math.dist(pts[i], pts[j]) <= 4:
            return gen_ege27(rng)
    for ci in range(k):
        mem = [q_ for q_, l in zip(pts, lab) if l == ci]
        reach, todo = {mem[0]}, [mem[0]]
        while todo:
            a = todo.pop()
            for b in mem:
                if b not in reach and math.dist(a, b) <= 4:
                    reach.add(b)
                    todo.append(b)
        if len(reach) != len(mem):
            return gen_ege27(rng)
    big = max(range(k), key=lambda ci: lab.count(ci))
    cl = [p_ for p_, l in zip(pts, lab) if l == big]
    sums = [(sum(math.dist(a, b) for b in cl), a) for a in cl]
    sums.sort()
    if len(sums) > 1 and abs(sums[0][0] - sums[1][0]) < 1e-6:
        return gen_ege27(rng)
    cen = sums[0][1]
    q = (f'На плоскости даны точки: ' + '; '.join(f'({x}; {y})' for x, y in pts) +
         f'. Точки образуют {k} кластера: расстояние между любыми точками разных кластеров больше 4, внутри кластера '
         'точки связаны цепочками шагов не длиннее 4. Центр кластера — его точка, у которой сумма расстояний до '
         'остальных точек кластера минимальна. Найдите центр самого многочисленного кластера. Запишите его '
         'координаты через пробел (с десятичной точкой, как в условии).')
    ex = ('Делим точки на кластеры (обход графа «расстояние ≤ 4»), в нужном кластере для каждой точки считаем сумму '
          'расстояний до остальных и берём минимум. В экзамене после этого ещё усредняют координаты центров и умножают на 10 000.')
    return card('inf-ege-27', 'text', q, f'{cen[0]} {cen[1]}', ex), {'pts': pts}


def check_ege27(p, c):
    # второй способ: кластеры восстанавливаем объединением множеств (DSU) по порогу 4, а не берём из генератора
    pts = p['pts']
    par = list(range(len(pts)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i, j in itertools.combinations(range(len(pts)), 2):
        if math.dist(pts[i], pts[j]) <= 4:
            par[f(i)] = f(j)
    groups = {}
    for i in range(len(pts)):
        groups.setdefault(f(i), []).append(pts[i])
    cl = max(groups.values(), key=len)
    if sorted(map(len, groups.values()))[-2:].count(len(cl)) > 1:
        return False
    cen = min(cl, key=lambda a: sum(math.hypot(a[0] - b[0], a[1] - b[1]) for b in cl))
    return f'{cen[0]} {cen[1]}' == c['a']


# ---------------------------------------------------------------- самопроверка

GENERATORS = {
    'ege2': (gen_ege2, check_ege2), 'ege4': (gen_ege4, check_ege4), 'ege5': (gen_ege5, check_ege5),
    'ege7': (gen_ege7, check_ege7), 'ege8': (gen_ege8, check_ege8), 'ege11': (gen_ege11, check_ege11),
    'ege12': (gen_ege12, check_ege12), 'ege13': (gen_ege13, check_ege13), 'ege14': (gen_ege14, check_ege14),
    'ege15': (gen_ege15, check_ege15), 'ege16': (gen_ege16, check_ege16), 'ege19-21': (gen_ege19, check_ege19),
    'ege18': (gen_ege18, check_ege18), 'ege22': (gen_ege22, check_ege22), 'ege23': (gen_ege23, check_ege23),
    'ege1': (gen_ege1, check_ege1), 'ege3': (gen_ege3, check_ege3), 'ege6': (gen_ege6, check_ege6),
    'ege9': (gen_ege9, check_ege9), 'ege17': (gen_ege17, check_ege17), 'ege24': (gen_ege24, check_ege24),
    'ege25': (gen_ege25, check_ege25), 'ege26': (gen_ege26, check_ege26), 'ege27': (gen_ege27, check_ege27),
    'oge1': (gen_oge1, check_oge1), 'oge2': (gen_oge2, check_oge2), 'oge3': (gen_oge3, check_oge3),
    'oge4': (gen_oge4, check_oge4), 'oge5': (gen_oge5, check_oge5), 'oge6': (gen_oge6, check_oge6),
    'oge7': (gen_oge7, check_oge7), 'oge8': (gen_oge8, check_oge8), 'oge9': (gen_oge9, check_oge9),
    'oge10': (gen_oge10, check_oge10),
    'g8-base': (gen_g8_base, check_g8_base), 'g7-units': (gen_g7_units, check_g7_units),
}


def selftest(n=200, seed=2026, max_tries=20):
    rng = random.Random(seed)
    report, allcards = [], []
    for name, (gen, chk) in GENERATORS.items():
        seen, cards, bad, tries = set(), [], 0, 0
        while len(cards) < n and tries < n * max_tries:
            tries += 1
            c, p = gen(rng)
            if c['q'] in seen:
                continue
            seen.add(c['q'])
            ok = c['a'] not in ('', None) and chk(p, c)
            if not ok:
                bad += 1
            cards.append(c)
        ids = Counter(c['id'] for c in cards)
        answers = Counter(json.dumps(c['a'], ensure_ascii=False) for c in cards)
        report.append({'type': name, 'cards': len(cards), 'tries': tries, 'dup_q': tries - len(cards),
                       'dup_id': sum(v - 1 for v in ids.values() if v > 1), 'check_failed': bad,
                       'distinct_answers': len(answers), 'kinds': dict(Counter(c['k'] for c in cards))})
        allcards += cards
    return report, allcards


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=200)
    ap.add_argument('--show', type=int, default=0)
    ap.add_argument('--dump')
    args = ap.parse_args()
    report, cards = selftest(args.n)
    print(f'{"тип":10} {"карт.":>5} {"попыт.":>6} {"повт.q":>6} {"повт.id":>7} {"ошибок":>6} {"разн.отв":>8}  типы')
    for r in report:
        print(f'{r["type"]:10} {r["cards"]:5} {r["tries"]:6} {r["dup_q"]:6} {r["dup_id"]:7} {r["check_failed"]:6} '
              f'{r["distinct_answers"]:8}  {r["kinds"]}')
    total = sum(r['cards'] for r in report)
    fails = sum(r['check_failed'] + r['dup_id'] for r in report) + sum(r['cards'] < args.n for r in report)
    print(f'Итого: {total} карточек, {len(report)} типов, проблем: {fails}')
    if args.show:
        by = {}
        for c in cards:
            by.setdefault(c['t'], []).append(c)
        for t, cs in by.items():
            for c in cs[:args.show]:
                print(json.dumps(c, ensure_ascii=False))
    if args.dump:
        with open(args.dump, 'w', encoding='utf-8') as f:
            json.dump(cards, f, ensure_ascii=False, indent=1)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
