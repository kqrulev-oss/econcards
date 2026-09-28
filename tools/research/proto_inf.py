#!/usr/bin/env python3
"""Каталог прототипов по информатике (ЕГЭ 1–27 в нумерации проекта КИМ 2027, ОГЭ 1–16) и привязка генераторов.

Запуск через gen_inf.py:
  python3 tools/research/gen_inf.py --protos [--n 50] [--cap 300] [--proto inf-ege-05]   # самопроверка
  python3 tools/research/gen_inf.py --protos --export        # записать data/source/inf-prototypes.json
  python3 tools/research/gen_inf.py --protos --samples 3 --seed 7 --out FILE   # случайные аналоги для экспертизы

Прототип — запись с метаданными (что неизменно, что меняется, правило ответа, типичные ошибки, паспорт КИМ)
и привязкой к генератору: gen(rng) -> (card, params) из gen_inf.py или отсюда, filt(params) выбирает подвид,
check(params, card) — независимая проверка ответа (второй способ или перебор). Для программ (ЕГЭ 12, 13, 16, 25;
ОГЭ 6, 16) вторая проверка — выполнение эталонной программы на Python (exec).

Тексты ФИПИ и коммерческих банков не используются: только структура экзамена (номер, уровень, балл, тема
кодификатора) и собственные условия. Нумерация ЕГЭ — проект 2027: 10 — маска подсети (в 2026 — № 13),
13 — анализ алгоритма, 23 — графы; поле n2026 хранит номер 2026 года, где он отличается.
"""
import fnmatch
import hashlib
import itertools
import json
import os
import random
import re
from collections import Counter
from fractions import Fraction

import gen_inf as G

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROTOS = []
_IDS = set()
ID_RE = re.compile(r'^inf-(ege|oge)-\d{2}-[a-z0-9-]+$')

LEVEL_EGE = {**{i: 'Б' for i in range(1, 12)}, **{i: 'П' for i in range(12, 23)}, **{i: 'В' for i in range(23, 28)}}
SCORE_EGE = {**{i: 1 for i in range(1, 26)}, 26: 2, 27: 2}
SCORE_OGE = {**{i: 1 for i in range(1, 13)}, 13: 2, 14: 3, 15: 2, 16: 2}


def _passport(exam, n, answer, kes):
    if exam == 'ЕГЭ':
        lvl, sc = LEVEL_EGE[n], SCORE_EGE[n]
        soft = 'специализированное ПО' if n in (3, 9, 16, 17, 18, 22, 24, 25, 26, 27) else 'без ПО'
        form = 'КЕГЭ: ответ вводится в поле компьютерной формы'
    else:
        lvl = 'Б' if n <= 12 else ('П' if n in (13, 14, 15) else 'В')
        sc = SCORE_OGE[n]
        soft = 'компьютер' if n >= 11 else 'без ПО'
        form = 'бланк ответов № 1' if n <= 12 else 'файл-ответ, проверяет эксперт'
    part = '2 балла: полное совпадение; 1 балл — верно одно из двух чисел' if (exam, n) in {('ЕГЭ', 26), ('ЕГЭ', 27)} else None
    return {'level': lvl, 'score': sc, 'answer': answer, 'form': form, 'software': soft, 'kes': kes, 'partial': part}


def P(pid, exam, n, title, *, gen, check, filt=None, kind='param', kes, answer, invariant, varies, answer_rule,
      mistakes, n2026=None, mini=None, pc=False):
    if not ID_RE.match(pid) or pid in _IDS:
        raise ValueError(f'плохой или повторный id прототипа {pid!r}')
    if int(pid.split('-')[2]) != n or ('-ege-' in pid) != (exam == 'ЕГЭ'):
        raise ValueError(f'{pid}: id не совпадает с экзаменом/номером')
    _IDS.add(pid)
    PROTOS.append({'id': pid, 'exam': exam, 'n': n, 'n2026': n2026, 'title': title, 'kind': kind,
                   'invariant': invariant, 'varies': varies, 'answer_rule': answer_rule, 'mistakes': list(mistakes),
                   'passport': _passport(exam, n, answer, kes), 'mini': mini, 'pc': pc,
                   'gen': gen, 'filt': filt, 'check': check, 'gen_name': gen.__module__ + '.' + gen.__name__})


def R(pid, exam, n, title, *, kind, kes, answer, invariant, varies, answer_rule, mistakes, how, check_rule,
      example, capacity, why, n2026=None):
    if not ID_RE.match(pid) or pid in _IDS:
        raise ValueError(f'плохой или повторный id прототипа {pid!r}')
    _IDS.add(pid)
    PROTOS.append({'id': pid, 'exam': exam, 'n': n, 'n2026': n2026, 'title': title, 'kind': kind,
                   'invariant': invariant, 'varies': varies, 'answer_rule': answer_rule, 'mistakes': list(mistakes),
                   'passport': _passport(exam, n, answer, kes), 'gen': None, 'filt': None, 'check': None,
                   'recipe': {'how': how, 'check': check_rule, 'why_not_param': why}, 'example': example,
                   'capacity': capacity})


def both(*checks):
    return lambda p, c: all(ch(p, c) for ch in checks)


def by(key, *values):
    return lambda p: p.get(key) in values


def run_py(code, inputs=()):
    """Выполняет эталонную программу на Python с заданными вводами; возвращает напечатанные строки."""
    it = iter([str(x) for x in inputs])
    out = []
    env = {'input': lambda *_: next(it), 'print': lambda *a, **k: out.append(' '.join(str(x) for x in a))}
    exec(code, env)  # noqa: S102 — своя эталонная программа, не пользовательский ввод
    return out


def retag(c, t, k=None):
    """Карточка старого генератора под id прототипа (нумерация 2027)."""
    c = dict(c)
    c['t'] = t
    if k:
        c['k'] = k
    c['id'] = t + '-' + hashlib.sha1((c['q'] + '|' + json.dumps(c['a'], ensure_ascii=False)).encode()).hexdigest()[:10]
    return c


# ================================================================ новые генераторы: ЕГЭ

# ---- ЕГЭ 2: фрагмент таблицы истинности → порядок переменных


def gen_ege2_frag(rng):
    vars_ = ['x', 'y', 'z', 'w']
    for _ in range(5000):
        e = G.rand_expr(rng, vars_, 3)
        if G.used_vars(e) != set(vars_) or _degenerate(e):
            continue
        rows = [r for r in itertools.product([0, 1], repeat=4)]
        target = rng.choice([0, 1])
        good = [r for r in rows if bool(G.ev(e, dict(zip(vars_, map(bool, r))))) == bool(target)]
        if not 3 <= len(good) <= 6:
            continue
        perm = list(vars_)
        rng.shuffle(perm)  # perm[j] — переменная в j-м столбце
        idx = [vars_.index(v) for v in perm]
        chosen = list(good)
        rng.shuffle(chosen)
        table = [[r[i] for i in idx] for r in chosen]
        if len(_solve_frag(e, table, target)) != 1:
            continue
        ans = ''.join(perm)
        tbl = '; '.join(' '.join(str(v) for v in row) + f' → {target}' for row in table)
        q = (f'Логическая функция F задаётся выражением {G.show(e)}. Дан фрагмент таблицы истинности функции F, '
             f'содержащий все наборы аргументов, при которых F {"истинна" if target else "ложна"}. Столбцы '
             f'обозначены ?1 ?2 ?3 ?4, строки: {tbl}. Определите, какому столбцу таблицы соответствует каждая из '
             f'переменных x, y, z, w. В ответе напишите буквы x, y, z, w в том порядке, в котором идут '
             f'соответствующие им столбцы (без разделителей).')
        ex = ('Перебираем 24 расстановки переменных по столбцам; подходит только одна. Полезно сначала найти '
              'наборы, где значение выражения определяется одной операцией (импликация ложна при 1 → 0).')
        return G.card('inf-ege-02', 'text', q, ans, ex), {'e': e, 'table': table, 'target': target}
    raise RuntimeError('ege2: не удалось подобрать выражение')


def _degenerate(e):
    """Подвыражение вида (x ∨ x) или ¬¬x выглядит ненатурально — такие выражения не берём."""
    if e[0] == 'var':
        return False
    if e[0] == 'not':
        return e[1][0] == 'not' or _degenerate(e[1])
    return e[1] == e[2] or _degenerate(e[1]) or _degenerate(e[2])


def _solve_frag(e, table, target):
    vars_ = ['x', 'y', 'z', 'w']
    sols = []
    for perm in itertools.permutations(vars_):
        ok = all(bool(G.ev(e, dict(zip(perm, map(bool, row))))) == bool(target) for row in table)
        if ok:
            sols.append(''.join(perm))
    return sols


def check_ege2_frag(p, c):
    # второй способ: по каждой строке отдельно строим множество допустимых перестановок и пересекаем
    vars_ = ['x', 'y', 'z', 'w']
    live = None
    for row in p['table']:
        s = {perm for perm in itertools.permutations(vars_)
             if bool(G.ev(p['e'], dict(zip(perm, map(bool, row))))) == bool(p['target'])}
        live = s if live is None else live & s
    return len(live) == 1 and ''.join(next(iter(live))) == c['a']


# ---- ЕГЭ 7: объём растрового изображения (число, а не выбор)


def gen_ege7_img(rng):
    w, h = rng.choice([(640, 480), (800, 600), (1024, 768), (1280, 1024), (320, 240), (1600, 1200), (2048, 1536)])
    i = rng.choice([1, 2, 4, 8, 12, 16, 24, 32])
    if (w * h * i) % (8 * 1024) != 0:
        return gen_ege7_img(rng)
    kb = w * h * i // (8 * 1024)
    if rng.random() < 0.5:
        q = (f'Для хранения растрового изображения размером {w}×{h} пикселей отвели {kb} Кбайт памяти, сжатие '
             f'не используется, все пиксели кодируются одинаковым числом бит. Сколько бит отведено на каждый пиксель?')
        ans, kind = i, 'bits'
        ex = f'{kb}·8·1024 / ({w}·{h}) = {i} бит.'
    else:
        q = (f'Растровое изображение размером {w}×{h} пикселей сохраняется без сжатия, на каждый пиксель отводится '
             f'{i} бит. Сколько Кбайт занимает изображение?')
        ans, kind = kb, 'kb'
        ex = f'{w}·{h}·{i} бит / 8 / 1024 = {kb} Кбайт.'
    return G.card('inf-ege-07', 'num', q, str(ans), ex), {'w': w, 'h': h, 'i': i, 'kb': kb, 'kind': kind}


def check_ege7_img(p, c):
    bits = p['w'] * p['h'] * p['i']
    if p['kind'] == 'bits':
        return str(int(p['kb']) * 8192 // (p['w'] * p['h'])) == c['a']
    return str(bits // 8192) == c['a'] and bits % 8192 == 0


# ---- ЕГЭ 13 (2027): анализ алгоритма


def _digits_prog(base, cond, op_a, op_b):
    return (f'x = int(input())\na = 0\nb = 1\nwhile x > 0:\n    d = x % {base}\n    if d % 2 == {cond}:\n'
            f'        a = a {op_a} d\n    else:\n        b = b {op_b} d\n    x = x // {base}\nprint(a)\nprint(b)')


def gen_ege13_digits(rng):
    base = rng.choice([10, 10, 8])
    cond = rng.choice([0, 1])
    op_a, op_b = rng.choice([('+', '*'), ('+', '+')])
    code = _digits_prog(base, cond, op_a, op_b)
    lo, hi = 1, 9999 if base == 10 else 4095
    res = {}
    for x in range(lo, hi + 1):
        a, b = map(int, run_py(code, [x]))
        res.setdefault((a, b), []).append(x)
    pairs = [k for k, v in res.items() if 2 <= len(v) <= 40 and k[1] > 1]
    if not pairs:
        return gen_ege13_digits(rng)
    a, b = rng.choice(pairs)
    ask = rng.choice(['max', 'min'])
    xs = res[(a, b)]
    ans = max(xs) if ask == 'max' else min(xs)
    q = (f'Ниже записана программа. Получив на вход натуральное число x, она печатает два числа: a и b.\n{code}\n'
         f'Укажите {"наибольшее" if ask == "max" else "наименьшее"} число x, при вводе которого программа напечатает '
         f'сначала {a}, а потом {b}.')
    ex = (f'Цикл перебирает цифры x в {base}-ичной записи: {"чётные" if cond == 0 else "нечётные"} цифры идут в a, '
          f'остальные — в b. Подбираем набор цифр с нужными a и b, затем расставляем их по убыванию (для наибольшего) '
          f'или по возрастанию без ведущего нуля.')
    return G.card('inf-ege-13', 'num', q, str(ans), ex), {'code': code, 'a': a, 'b': b, 'ask': ask, 'lo': lo, 'hi': hi}


def check_ege13_digits(p, c):
    # второй способ: без exec — разбор цифр вручную по тексту программы
    m = re.search(r'x % (\d+)', p['code'])
    base = int(m.group(1))
    cond = int(re.search(r'd % 2 == (\d)', p['code']).group(1))
    op_a = re.search(r'a = a (.) d', p['code']).group(1)
    op_b = re.search(r'b = b (.) d', p['code']).group(1)
    best = None
    for x in range(p['lo'], p['hi'] + 1):
        a, b, y = 0, 1, x
        while y > 0:
            d = y % base
            if d % 2 == cond:
                a = a + d if op_a == '+' else a * d
            else:
                b = b + d if op_b == '+' else b * d
            y //= base
        if (a, b) == (p['a'], p['b']):
            best = x if best is None or (x > best if p['ask'] == 'max' else x < best) else best
    return str(best) == c['a']


def gen_ege13_loop(rng):
    step = rng.randint(3, 25)
    lim = rng.randint(100, 900)
    mode = rng.choice(['mul', 'add'])
    k = rng.randint(2, 5)
    code = (f's = int(input())\nn = 1\nwhile s < {lim}:\n    s = s + {step}\n    n = n {"*" if mode == "mul" else "+"} {k}\nprint(n)')
    outs = {}
    for s in range(1, lim + 1):
        outs.setdefault(int(run_py(code, [s])[0]), []).append(s)
    cand = [v for v, xs in outs.items() if len(xs) >= 2 and 1 < v < 10 ** 12]
    if not cand:
        return gen_ege13_loop(rng)
    v = rng.choice(cand)
    ask = rng.choice(['max', 'min'])
    ans = max(outs[v]) if ask == 'max' else min(outs[v])
    q = (f'Ниже записана программа. Получив на вход число s, она печатает число n.\n{code}\n'
         f'Укажите {"наибольшее" if ask == "max" else "наименьшее"} число s, при вводе которого программа напечатает {v}.')
    ex = (f'Из n = {v} находим число итераций цикла; s должно за столько шагов по {step} впервые стать не меньше {lim}: '
          f'это отрезок значений s, из него берём {"наибольшее" if ask == "max" else "наименьшее"}.')
    return G.card('inf-ege-13', 'num', q, str(ans), ex), {'step': step, 'lim': lim, 'mode': mode, 'k': k, 'v': v, 'ask': ask}


def check_ege13_loop(p, c):
    # второй способ: формула числа итераций вместо моделирования
    xs = []
    for s in range(1, p['lim'] + 1):
        it = max(0, -(-(p['lim'] - s) // p['step']))
        n = p['k'] ** it if p['mode'] == 'mul' else 1 + p['k'] * it
        if n == p['v']:
            xs.append(s)
    return bool(xs) and str(max(xs) if p['ask'] == 'max' else min(xs)) == c['a']


# ---- ЕГЭ 15: делимость (ДЕЛ)


def gen_ege15_del(rng):
    pairs = [(6, 10), (12, 18), (15, 21), (14, 21), (20, 30), (24, 36), (18, 30), (10, 25), (12, 20), (28, 42)]
    p_, q_ = rng.choice(pairs)
    if rng.random() < 0.5:
        p_, q_ = q_, p_
    shape = rng.choice(['min', 'max'])
    if shape == 'min':
        f = f'ДЕЛ(x, A) → (¬ДЕЛ(x, {p_}) ∨ ДЕЛ(x, {q_}))'
        ans = _del_min(p_, q_)
        q = (f'Обозначим через ДЕЛ(n, m) утверждение «натуральное число n делится без остатка на натуральное число m». '
             f'Для какого наименьшего натурального числа A формула {f} тождественно истинна (то есть принимает '
             f'значение 1 при любом натуральном значении переменной x)?')
        ex = (f'Формула ложна, если x кратно A и {p_}, но не кратно {q_}. Значит, каждое общее кратное A и {p_} должно '
              f'делиться на {q_}: A должно содержать недостающие простые множители {q_}. Перебор A с проверкой x до НОК.')
    else:
        f = f'(ДЕЛ(x, {p_}) ∧ ДЕЛ(x, {q_})) → ДЕЛ(x, A)'
        ans = _lcm(p_, q_)
        q = (f'Обозначим через ДЕЛ(n, m) утверждение «натуральное число n делится без остатка на натуральное число m». '
             f'Для какого наибольшего натурального числа A формула {f} тождественно истинна (то есть принимает '
             f'значение 1 при любом натуральном значении переменной x)?')
        ex = f'x кратно и {p_}, и {q_} ⇔ x кратно НОК({p_}, {q_}) = {ans}; A должно делить НОК, наибольшее A = НОК.'
    return G.card('inf-ege-15', 'num', q, str(ans), ex), {'p': p_, 'q': q_, 'shape': shape}


def _lcm(a, b):
    from math import gcd
    return a * b // gcd(a, b)


def _del_min(p_, q_):
    for A in range(1, 10000):
        L = _lcm(A, p_)
        if L % q_ == 0:
            return A
    return None


def check_ege15_del(p, c):
    # второй способ: прямой перебор x ≤ 5000 для каждого кандидата A
    N = 5000
    if p['shape'] == 'min':
        for A in range(1, 2000):
            if all((x % A != 0) or (x % p['p'] != 0) or (x % p['q'] == 0) for x in range(1, N + 1)):
                return str(A) == c['a']
        return False
    best = None
    for A in range(1, 2000):
        if all(not (x % p['p'] == 0 and x % p['q'] == 0) or x % A == 0 for x in range(1, N + 1)):
            best = A
    return str(best) == c['a']


# ---- ЕГЭ 23 (2027): графы


def _dag(rng, n):
    V = list('АБВГДЕЖЗИКЛМ')[:n]
    edges = set()
    for i in range(n - 1):
        edges.add((V[i], V[rng.randint(i + 1, min(n - 1, i + 2))]))
        for _ in range(rng.randint(1, 2)):
            j = rng.randint(i + 1, min(n - 1, i + 4))
            edges.add((V[i], V[j]))
    return V, sorted(edges)


def _paths(V, edges, avoid=None):
    f = {V[0]: 1}
    for v in V[1:]:
        f[v] = 0 if v == avoid else sum(f[u] for u, w in edges if w == v)
    return f[V[-1]]


def gen_ege23_paths(rng):
    n = rng.randint(9, 12)
    V, edges = _dag(rng, n)
    mode = rng.choice(['via', 'avoid', 'via_avoid'])
    mid = rng.sample(V[1:-1], 2)
    via, avoid = (mid[0], None) if mode == 'via' else ((None, mid[0]) if mode == 'avoid' else (mid[0], mid[1]))
    if via:
        ans = _paths(V[:V.index(via) + 1], [e for e in edges if e[1] in V[:V.index(via) + 1]], avoid) * \
            _paths(V[V.index(via):], [e for e in edges if e[0] in V[V.index(via):]], avoid)
    else:
        ans = _paths(V, edges, avoid)
    if not 3 <= ans <= 400:
        return gen_ege23_paths(rng)
    tail = {'via': f', проходящих через город {via}', 'avoid': f', не проходящих через город {avoid}',
            'via_avoid': f', проходящих через город {via} и не проходящих через город {avoid}'}[mode]
    q = (f'Схема дорог, связывающих города {", ".join(V)}, задана списком дорог с односторонним движением '
         f'(стрелка — разрешённое направление): {"; ".join(f"{u}→{w}" for u, w in edges)}. Сколько существует различных '
         f'путей из города {V[0]} в город {V[-1]}{tail}?')
    ex = ('Считаем число путей в каждую вершину как сумму по входящим дорогам (динамика по топологическому порядку). '
          'Запрещённый город получает 0; для «через» перемножаем число путей до него и от него.')
    return G.card('inf-ege-23', 'num', q, str(ans), ex), {'V': V, 'edges': edges, 'via': via, 'avoid': avoid}


def check_ege23_paths(p, c):
    # второй способ: явный DFS-перебор всех путей
    adj = {}
    for u, w in p['edges']:
        adj.setdefault(u, []).append(w)
    cnt = 0
    stack = [(p['V'][0], (p['V'][0],))]
    while stack:
        v, path = stack.pop()
        if v == p['V'][-1]:
            if (p['via'] is None or p['via'] in path) and (p['avoid'] is None or p['avoid'] not in path):
                cnt += 1
            continue
        for w in adj.get(v, []):
            stack.append((w, path + (w,)))
    return str(cnt) == c['a']


def gen_ege23_short(rng):
    n = rng.randint(6, 8)
    V = list('ABCDEFGH')[:n]
    W = {}
    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or rng.random() < 0.35:
                W[(V[i], V[j])] = rng.randint(2, 15)
    src, dst = V[0], V[-1]
    d = _dijkstra(V, W, src)
    if d[dst] is None:
        return gen_ege23_short(rng)
    # прямой путь не должен быть кратчайшим, иначе задача тривиальна
    if (src, dst) in W and W[(src, dst)] <= d[dst]:
        return gen_ege23_short(rng)
    cells = '; '.join(f'{a}–{b}: {w}' for (a, b), w in sorted(W.items()))
    q = (f'Между населёнными пунктами {", ".join(V)} построены дороги, протяжённость которых (в км) приведена в '
         f'таблице (пустая клетка — дороги нет): {cells}. Определите длину кратчайшего пути между пунктами {src} и {dst}. '
         f'Передвигаться можно только по дорогам, протяжённость которых указана в таблице.')
    ex = 'Алгоритм Дейкстры или перебор путей по таблице: помечаем вершины наименьшими найденными расстояниями.'
    return G.card('inf-ege-23', 'num', q, str(d[dst]), ex), {'V': V, 'W': [[a, b, w] for (a, b), w in W.items()]}


def _dijkstra(V, W, src):
    adj = {v: [] for v in V}
    for (a, b), w in W.items():
        adj[a].append((b, w))
        adj[b].append((a, w))
    dist = {v: None for v in V}
    dist[src] = 0
    done = set()
    while True:
        cand = [(d, v) for v, d in dist.items() if d is not None and v not in done]
        if not cand:
            return dist
        d, v = min(cand)
        done.add(v)
        for w, c in adj[v]:
            if dist[w] is None or d + c < dist[w]:
                dist[w] = d + c


def check_ege23_short(p, c):
    # второй способ: Флойд–Уоршелл
    V = p['V']
    INF = 10 ** 9
    D = {(a, b): (0 if a == b else INF) for a in V for b in V}
    for a, b, w in p['W']:
        D[(a, b)] = D[(b, a)] = min(D[(a, b)], w)
    for k in V:
        for i in V:
            for j in V:
                if D[(i, k)] + D[(k, j)] < D[(i, j)]:
                    D[(i, j)] = D[(i, k)] + D[(k, j)]
    return str(D[(V[0], V[-1])]) == c['a']


# ================================================================ exec-проверки программ (ЕГЭ 12, 16, 25; ОГЭ 6)


def exec_ege12(p, c):
    rules = p['rules']
    cond = ' or '.join(f"'{a}' in s" for a, _ in rules)
    body = '\n'.join(('    if' if i == 0 else '    elif') + f" '{a}' in s:\n        s = s.replace('{a}', '{b}', 1)"
                     for i, (a, b) in enumerate(rules))
    code = f"s = '{p['start']}'\nwhile {cond}:\n{body}\nprint(sum(int(ch) for ch in s))"
    return run_py(code) == [c['a']]


def exec_ege16(p, c):
    t, c0, a, b, d, form, N = (p[k] for k in ('t', 'c0', 'a', 'b', 'd', 'form', 'N'))
    rule = {'lin': f'return {a} * F(n - 1) + {b} * n',
            'parity': f'return F(n - 1) + {b} * n if n % 2 == 0 else {a} * F(n - 2) + {d}',
            'two': f'return {c0 + d} if n == {t + 1} else F(n - 1) + F(n - 2) + {d}'}[form]
    code = (f'from functools import lru_cache\n@lru_cache(None)\ndef F(n):\n    if n <= {t}:\n        return {c0}\n'
            f'    {rule}\nprint(F({N}))')
    return run_py(code) == [c['a']]


def exec_ege25(p, c):
    if p['kind'] == 'mask':
        code = (f"from fnmatch import fnmatch\nf = [x for x in range({p['d']}, 10**6 + 1, {p['d']}) if fnmatch(str(x), '{p['mask']}')]\n"
                f"print({{'count': len(f), 'min': min(f), 'max': max(f)}}['{p['ask']}'])")
    else:
        code = (f"f = []\nfor x in range({p['a']}, {p['b']} + 1):\n    ds = set()\n    t = 2\n    while t * t <= x:\n"
                f"        if x % t == 0:\n            ds.add(t); ds.add(x // t)\n        t += 1\n    if len(ds) == {p['k']}:\n"
                f"        f.append(x)\nprint(len(f) if '{p['ask']}' == 'count' else f[-1])")
    return run_py(code) == [c['a']]


def exec_oge6(p, c):
    yes = sum(1 for s, t in p['pairs'] if run_py(p['code'], [s, t]) == ['YES'])
    return str(yes) == c['a']


# ================================================================ новые генераторы: ОГЭ

# ---- ОГЭ 12: файлы по маске (мини-версия каталога в условии)

NAMES12 = ['доклад', 'реферат', 'задача', 'карта', 'сказка', 'план', 'отчёт', 'таблица', 'рисунок', 'схема', 'урок', 'тест']
EXT12 = ['txt', 'doc', 'docx', 'odt', 'pdf', 'jpg', 'png', 'ods', 'xls']


def gen_oge12(rng):
    files = set()
    while len(files) < rng.randint(12, 16):
        files.add(f'{rng.choice(NAMES12)}{rng.choice(["", "", str(rng.randint(1, 9))])}.{rng.choice(EXT12)}')
    files = sorted(files)
    core = rng.choice(NAMES12)
    mask = rng.choice([f'*{core[:3]}*.*', f'*.{rng.choice(["doc*", "txt", "?d?", "od?", "*x"])}',
                       f'{core[:2]}*.d*', f'*{core[-2:]}*.{rng.choice(["txt", "pdf", "od?"])}', f'*?.{rng.choice(EXT12)}'])
    hit = [f for f in files if fnmatch.fnmatchcase(f, mask)]
    if not 1 <= len(hit) <= len(files) - 2:
        return gen_oge12(rng)
    q = (f'В каталоге «Документы» находятся файлы: {", ".join(files)}. Сколько из них соответствует маске {mask}? '
         f'В маске «*» — любая последовательность символов (возможно, пустая), «?» — ровно один символ.')
    ex = f'Проверяем каждое имя по маске: подходят {", ".join(hit)}.'
    return G.card('inf-oge-12', 'num', q, str(len(hit)), ex), {'files': files, 'mask': mask}


def check_oge12(p, c):
    rx = re.compile('^' + ''.join('.*' if ch == '*' else '.' if ch == '?' else re.escape(ch) for ch in p['mask']) + '$')
    return str(sum(1 for f in p['files'] if rx.match(f))) == c['a']


# ---- ОГЭ 14: электронная таблица (мини-версия: 8–10 строк в условии)

SURN = ['Аверин', 'Белова', 'Ветров', 'Гусева', 'Дёмин', 'Ежова', 'Жуков', 'Зотова', 'Ильин', 'Крылова', 'Лунин', 'Мухина']
SUBJ = ['математика', 'физика', 'информатика', 'биология']


def gen_oge14(rng):
    rows = []
    names = rng.sample(SURN, rng.randint(8, 10))
    for nm in names:
        rows.append((nm, rng.choice(SUBJ), rng.randint(15, 100), rng.randint(1, 3)))
    ask = rng.choice(['count', 'avg'])
    subj = rng.choice(SUBJ)
    sel = [r for r in rows if r[1] == subj]
    if ask == 'count':
        thr = rng.choice([50, 60, 70, 75, 80])
        ans = sum(1 for r in rows if r[2] > thr and r[1] == subj)
        if not sel or ans == 0:
            return gen_oge14(rng)
        what = f'Сколько учеников, выбравших предмет «{subj}», набрали больше {thr} баллов?'
        ex = f'В электронной таблице: =СЧЁТЕСЛИМН(B:B; "{subj}"; C:C; ">{thr}") или отбор строк вручную.'
    else:
        if len(sel) < 2:
            return gen_oge14(rng)
        avg = Fraction(sum(r[2] for r in sel), len(sel))
        if (avg * 100).denominator != 1:
            return gen_oge14(rng)
        ans = f'{float(avg):.2f}'.rstrip('0').rstrip('.').replace('.', ',')
        what = f'Каков средний балл учеников, выбравших предмет «{subj}»? Ответ запишите с точностью не менее двух знаков после запятой.'
        ex = f'=СРЗНАЧЕСЛИ(B:B; "{subj}"; C:C): сумма баллов {sum(r[2] for r in sel)} делится на {len(sel)}.'
    tbl = '; '.join(f'{nm} — {sb} — {sc} — школа {sch}' for nm, sb, sc, sch in rows)
    q = (f'В электронную таблицу занесли результаты олимпиады: столбцы A — фамилия, B — предмет, C — баллы, '
         f'D — номер школы. Строки: {tbl}. {what}')
    return G.card('inf-oge-14', 'num', q, str(ans), ex), {'rows': rows, 'ask': ask, 'subj': subj,
                                                       'thr': thr if ask == 'count' else None}


def check_oge14(p, c):
    sel = [r for r in p['rows'] if r[1] == p['subj']]
    if p['ask'] == 'count':
        return str(len([r for r in sel if r[2] > p['thr']])) == c['a']
    total = 0
    for r in sel:
        total += r[2]
    got = round(total / len(sel) + 1e-9, 2)
    return abs(got - float(c['a'].replace(',', '.'))) < 1e-9


# ---- ОГЭ 16: программа на универсальном языке (мини-версия: данные в условии)

COND16 = [('кратны 3', 'x % 3 == 0', lambda x: x % 3 == 0),
          ('чётны и больше 20', 'x % 2 == 0 and x > 20', lambda x: x % 2 == 0 and x > 20),
          ('оканчиваются на 5', 'x % 10 == 5', lambda x: x % 10 == 5),
          ('двузначны и нечётны', '10 <= x <= 99 and x % 2 == 1', lambda x: 10 <= x <= 99 and x % 2 == 1),
          ('кратны 4, но не кратны 8', 'x % 4 == 0 and x % 8 != 0', lambda x: x % 4 == 0 and x % 8 != 0)]


def gen_oge16(rng):
    n = rng.randint(8, 12)
    xs = [rng.randint(1, 120) for _ in range(n)]
    name, pycond, fn = rng.choice(COND16)
    agg = rng.choice(['count', 'sum'])
    hit = [x for x in xs if fn(x)]
    if not hit:
        return gen_oge16(rng)
    ans = len(hit) if agg == 'count' else sum(hit)
    body = 's = s + 1' if agg == 'count' else 's = s + x'
    code = f'n = int(input())\ns = 0\nfor i in range(n):\n    x = int(input())\n    if {pycond}:\n        {body}\nprint(s)'
    q = (f'Напишите программу, которая в последовательности натуральных чисел определяет '
         f'{"количество чисел, которые" if agg == "count" else "сумму чисел, которые"} {name}. Программа получает на вход '
         f'количество чисел, затем сами числа. Проверьте программу на данных: n = {n}, числа: {" ".join(map(str, xs))}. '
         f'Какое число она должна напечатать?')
    ex = f'Один цикл со счётчиком/суммой и условием «{pycond}». Подходят: {" ".join(map(str, hit))}.'
    return G.card('inf-oge-16', 'num', q, str(ans), ex), {'xs': xs, 'code': code, 'agg': agg}


def check_oge16(p, c):
    return run_py(p['code'], [len(p['xs'])] + p['xs']) == [c['a']]


def gen_oge16_trace(rng):
    a, b = rng.randint(1, 9), rng.randint(2, 6)
    n = rng.randint(4, 8)
    op = rng.choice(['s = s + i * %d' % b, 's = s * 2 + %d' % b, 's = s + %d - i' % b])
    code = f's = {a}\nfor i in range(1, {n + 1}):\n    {op}\nprint(s)'
    out = run_py(code)
    q = f'Определите, что напечатает программа:\n{code}'
    ex = f'Выполняем цикл по шагам i = 1..{n}, следя за s.'
    return G.card('inf-oge-16', 'num', q, out[0], ex), {'a': a, 'b': b, 'n': n, 'op': op}


def check_oge16_trace(p, c):
    s = p['a']
    for i in range(1, p['n'] + 1):
        if p['op'].startswith('s = s + i'):
            s = s + i * p['b']
        elif p['op'].startswith('s = s * 2'):
            s = s * 2 + p['b']
        else:
            s = s + p['b'] - i
    return str(s) == c['a']


# ================================================================ КАТАЛОГ

def _ege(n, slug, title, **kw):
    P(f'inf-ege-{n:02d}-{slug}', 'ЕГЭ', n, title, **kw)


def _oge(n, slug, title, **kw):
    P(f'inf-oge-{n:02d}-{slug}', 'ОГЭ', n, title, **kw)


def wrap(gen, t, k=None, accept=None):
    """Карточка старого генератора под id прототипа; accept(card) отбрасывает карточки не в форме КИМ."""
    def g(rng):
        while True:
            c, p = gen(rng)
            if accept is None or accept(c):
                return retag(c, t, k), p
    g.__name__ = gen.__name__
    g.__module__ = gen.__module__
    return g


# ---------------- ЕГЭ
_ege(1, 'graph-table', 'Граф и весовая таблица: длина дороги между двумя пунктами',
     gen=wrap(G.gen_ege1, 'inf-ege-01'), check=G.check_ege1, kes='Информационные модели: графы, таблицы', answer='число',
     invariant='схема дорог задана списком рёбер, таблица — с перепутанными номерами пунктов; найти вес ребра между двумя названными вершинами',
     varies='число вершин (6–7), набор рёбер, веса, какая пара вершин спрашивается',
     answer_rule='сопоставление вершин по степеням и соседству даёт единственный вес; целое число',
     mistakes=['перепутать степени вершин, когда две вершины одинаковой степени', 'взять вес соседнего ребра'])
_ege(2, 'truth-fragment', 'Фрагмент таблицы истинности: какой столбец какой переменной',
     gen=gen_ege2_frag, check=check_ege2_frag, kes='Таблицы истинности, логические выражения', answer='последовательность букв',
     invariant='выражение от x, y, z, w; фрагмент из 3 строк со всеми наборами одного значения F; определить порядок переменных',
     varies='выражение (∧, ∨, →, ≡, ¬ глубины до 3), значение F в фрагменте (0 или 1), перестановка столбцов',
     answer_rule='строка из четырёх букв в порядке столбцов; единственная перестановка, согласованная со всеми строками',
     mistakes=['проверить только одну строку', 'перепутать порядок: буквы записываются по столбцам, а не по алфавиту'])
for slug, ask, title in [('district', 'district', 'Мини-БД: сумма продаж по району'), ('dept', 'dept', 'Мини-БД: количество по отделу'),
                         ('balance', 'balance', 'Мини-БД: остаток товара за период')]:
    _ege(3, slug, title, gen=wrap(G.gen_ege3, 'inf-ege-03', accept=lambda c: not c['a'].startswith('-')),
         check=G.check_ege3, filt=by('ask', ask),
         kes='Реляционные базы данных: связь таблиц', answer='число', mini='4 магазина, 4 товара, 12–16 операций вместо файла .ods',
         invariant='три связанные таблицы (магазины, товары, движение); вопрос по связи через ID и артикул',
         varies='названия, районы, отделы, числа операций, даты', answer_rule='SQL-запрос по трём таблицам; целое число',
         mistakes=['не связать таблицы по ключу', 'учесть поступление как продажу'])
_ege(4, 'fano-min', 'Условие Фано: наименьшая длина кодового слова',
     gen=wrap(G.gen_ege4, 'inf-ege-04'), check=G.check_ege4, filt=by('k', 1), kes='Кодирование: неравномерные коды, условие Фано', answer='число',
     invariant='известны коды нескольких букв, код удовлетворяет условию Фано; найти наименьшую длину кода ещё одной буквы',
     varies='алфавит 6–10 букв, известные коды, свободные ветви дерева', answer_rule='кратчайшая свободная ветвь двоичного дерева; целое число',
     mistakes=['выбрать код, являющийся началом известного', 'забыть обратное условие Фано, если оно требуется'])
_ege(4, 'fano-sum', 'Условие Фано: наименьшая суммарная длина кодов двух букв',
     gen=wrap(G.gen_ege4, 'inf-ege-04'), check=G.check_ege4, filt=by('k', 2), kes='Кодирование: неравномерные коды, условие Фано', answer='число',
     invariant='то же, но нужно дописать две буквы с наименьшей суммой длин', varies='алфавит, известные коды',
     answer_rule='две свободные ветви, вместе не нарушающие Фано; сумма длин', mistakes=['взять две ветви, одна из которых — начало другой'])
for mode, slug, title in [('minN', 'min-n', 'Алгоритм над двоичной записью: наименьшее N по условию на R'),
                          ('minR', 'min-r', 'Алгоритм над двоичной записью: наименьшее R, большее порога'),
                          ('maxN', 'max-n', 'Алгоритм над двоичной записью: наибольшее N по условию на R')]:
    _ege(5, slug, title, gen=wrap(G.gen_ege5, 'inf-ege-05'), check=G.check_ege5, filt=by('mode', mode),
         kes='Двоичная система счисления, алгоритмы обработки чисел', answer='число',
         invariant='автомат строит R из двоичной записи N по правилу; вопрос про N или R с ограничением',
         varies='правило (дописать биты, чётность, инвертировать), порог', answer_rule='перебор N программой или разбор двоичной записи; целое',
         mistakes=['дописать биты слева вместо справа', 'перепутать «больше» и «не меньше»'])
_ege(6, 'turtle-inter', 'Черепаха: целые точки внутри пересечения двух прямоугольников',
     gen=wrap(G.gen_ege6, 'inf-ege-06'), check=G.check_ege6, filt=by('ask', 'inter'), kes='Исполнитель Черепаха, алгоритмы', answer='число',
     invariant='два прямоугольника из команд Повтори/Вперёд/Направо; вопрос про внутренние точки пересечения без границы',
     varies='размеры, сдвиг второго прямоугольника', answer_rule='(w − 1)(h − 1) для пересечения; целое', mistakes=['учесть точки на границе', 'ошибиться со сдвигом при поднятом хвосте'])
_ege(6, 'turtle-union', 'Черепаха: целые точки в объединении фигур с границей',
     gen=wrap(G.gen_ege6, 'inf-ege-06'), check=G.check_ege6, filt=by('ask', 'union'), kes='Исполнитель Черепаха, алгоритмы', answer='число',
     invariant='те же фигуры; вопрос про объединение с точками на линиях', varies='размеры и сдвиг',
     answer_rule='включения-исключения по замкнутым прямоугольникам; целое', mistakes=['дважды посчитать пересечение'])
_ege(7, 'image-volume', 'Растровое изображение: объём или глубина цвета',
     gen=gen_ege7_img, check=check_ege7_img, kes='Кодирование графической информации', answer='число',
     invariant='размер в пикселях, глубина цвета или объём; найти недостающее', varies='разрешение, глубина', answer_rule='w·h·i / 8 / 1024; целое',
     mistakes=['делить на 1000 вместо 1024', 'бит и байт'])
_ege(7, 'image-colors', 'Растровое изображение: наибольшее число цветов при ограничении памяти',
     gen=wrap(G.gen_ege7, 'inf-ege-07'), check=G.check_ege7, filt=by('kind', 'img_colors'), kes='Кодирование графической информации', answer='число',
     invariant='размер и лимит памяти; найти максимальную палитру 2^i', varies='разрешение, лимит', answer_rule='i = ⌊лимит / (w·h)⌋, 2^i',
     mistakes=['округлить биты вверх', 'ответить числом бит вместо числа цветов'])
_ege(7, 'sound', 'Звук: объём записи или время/частота/глубина',
     gen=wrap(G.gen_ege7, 'inf-ege-07'), check=G.check_ege7, filt=by('kind', 'sound'), kes='Кодирование звуковой информации', answer='число',
     invariant='частота дискретизации, глубина, каналы, время; одна величина неизвестна', varies='числа, каналы', answer_rule='f·i·k·t / 8 / 1024²',
     mistakes=['забыть число каналов', 'Мбайт как 10⁶'])
for kind, slug, title in [('exact', 'count-cond', 'Слова из букв: количество по условию на позиции'),
                          ('no_adj_vowels', 'no-adj-vowels', 'Слова: гласные не стоят рядом'),
                          ('distinct_first', 'distinct-first', 'Слова с заданной первой буквой и без повторов'),
                          ('perm_no_adj', 'perm-no-adj', 'Перестановки букв: две буквы не рядом')]:
    _ege(8, slug, title, gen=wrap(G.gen_ege8, 'inf-ege-08'), check=G.check_ege8, filt=by('kind', kind),
         kes='Комбинаторика: подсчёт слов и кодов', answer='число',
         invariant='алфавит из букв слова, длина слова, комбинаторное ограничение', varies='набор букв, длина, ограничение',
         answer_rule='правило произведения или перебор itertools; целое', mistakes=['не учесть запрет повторов', 'считать ограничение только для одной позиции'])
_ege(9, 'rows-conditions', 'Электронная таблица: строки, удовлетворяющие двум условиям',
     gen=wrap(G.gen_ege9, 'inf-ege-09'), check=G.check_ege9, kes='Электронные таблицы: обработка числовых данных', answer='число',
     mini='8–10 строк по 5 чисел вместо файла .ods',
     invariant='строки чисел, два условия (повторы/различие/треугольник × сумма/среднее/max+min); сколько строк подходят',
     varies='числа, пара условий', answer_rule='перебор строк; целое', mistakes=['«ровно один повтор» принять за «есть повтор»', 'среднее вместо суммы'])
for kind, slug, title in [('net_byte', 'net-address', 'Маска подсети: байт адреса сети'),
                          ('mask_byte', 'mask-byte', 'Маска подсети: байт маски по адресу узла и сети'),
                          ('count_addr', 'count-addr', 'Маска подсети: число адресов с условием на биты'),
                          ('max_ones', 'max-ones', 'Маска подсети: наибольшее число единиц в маске по двум адресам одной сети')]:
    _ege(10, slug, title, gen=wrap(G.gen_ege13, 'inf-ege-10'), check=G.check_ege13, filt=by('kind', kind), n2026=13,
         kes='Адресация в сети: IP-адрес, маска подсети', answer='число',
         invariant='IP-адреса, маска (или число единиц); вопрос про сеть, маску или подсчёт адресов', varies='адреса, длина префикса, байт',
         answer_rule='поразрядная конъюнкция адреса и маски; целое', mistakes=['маска с нулями между единицами', 'считать адреса без учёта адреса сети и широковещательного'])
_ege(11, 'total-volume', 'Информационный объём: память под N записей (идентификаторов, паролей)',
     gen=wrap(G.gen_ege11, 'inf-ege-11'), check=G.check_ege11, filt=by('ask', 'bytes_total', 'kb_total'),
     kes='Измерение информации, алфавитный подход', answer='число',
     invariant='алфавит мощности M, длина L символов, целое число байт на запись, N записей; найти общий объём',
     varies='алфавит, длина, N, единицы (байт/Кбайт)', answer_rule='⌈L·⌈log₂M⌉ / 8⌉·N (+ доп. байты); целое',
     mistakes=['не округлять биты до байт вверх', 'log₂ округлить вниз'])
_ege(11, 'per-record', 'Информационный объём: байт на одну запись или доп. сведения',
     gen=wrap(G.gen_ege11, 'inf-ege-11'), check=G.check_ege11, filt=by('ask', 'bytes_one'),
     kes='Измерение информации, алфавитный подход', answer='число',
     invariant='известен общий объём и число записей; найти байты на запись или на дополнительные сведения',
     varies='алфавит, длина, объём', answer_rule='объём / N − байты на символы', mistakes=['перевести Кбайт как 1000 байт'])
_ege(12, 'editor-digit-sum', 'Исполнитель Редактор: сумма цифр строки-результата',
     gen=wrap(G.gen_ege12, 'inf-ege-12'), check=both(G.check_ege12, exec_ege12), kes='Исполнители, циклы, обработка строк', answer='число',
     invariant='программа ПОКА/ЕСЛИ с 2–3 заменами; на входе длинная строка из одной цифры (или 0+единицы+двойки); найти сумму цифр результата',
     varies='набор правил (6 наборов), длина строки', answer_rule='моделирование программой (str.replace, регулярные выражения, exec эталона); целое',
     mistakes=['заменить не первое слева вхождение', 'остановиться раньше, чем перестанут выполняться условия'])
_ege(13, 'digits-ab', 'Анализ алгоритма: наибольшее/наименьшее x, при котором печатаются a и b',
     gen=gen_ege13_digits, check=check_ege13_digits, kes='Анализ алгоритмов, циклы, целочисленная арифметика', answer='число',
     invariant='программа перебирает цифры x (в 10- или 8-ичной записи), чётные и нечётные цифры идут в a и b; найти крайний x по выводу',
     varies='основание, условие чётности, операции (сложение/умножение), пара (a, b), «наибольшее»/«наименьшее»',
     answer_rule='перебор x программой (exec листинга) или подбор набора цифр; целое', mistakes=['ведущие нули', 'перепутать, куда идут чётные цифры'])
_ege(13, 'loop-count', 'Анализ алгоритма: s по выведенному n (цикл «пока»)',
     gen=gen_ege13_loop, check=check_ege13_loop, kes='Анализ алгоритмов, циклы', answer='число',
     invariant='цикл while s < L с шагом по s и умножением/сложением n; по напечатанному n найти крайнее s',
     varies='шаг, порог, множитель, «наибольшее»/«наименьшее»', answer_rule='число итераций из n, затем границы s; целое',
     mistakes=['ошибка на единицу в числе итераций', 'граница s < L против s ≤ L'])
_ege(13, 'exec-programs', 'Анализ алгоритма: число программ исполнителя через/минуя заданные числа',
     gen=wrap(G.gen_ege23, 'inf-ege-13'), check=G.check_ege23, n2026=23, kes='Анализ алгоритмов, динамическое программирование', answer='число',
     invariant='две команды (прибавить/умножить); сколько программ переводят A в B с обязательным C и запретным D',
     varies='команды, A, B, C, D', answer_rule='динамика f(y) += f(x) с обнулением запретного; целое',
     mistakes=['не обнулить запретное число', 'забыть перемножить A→C и C→B'])
_ege(14, 'count-digit', 'Системы счисления: сколько цифр d в записи суммы степеней',
     gen=wrap(G.gen_ege14, 'inf-ege-14', accept=lambda c: c['a'] != '0'), check=G.check_ege14, filt=by('kind', 'count_digit'), kes='Позиционные системы счисления', answer='число',
     invariant='выражение из степеней основания с вычитанием; посчитать цифры d в записи по основанию b',
     varies='основание (4, 8, 16 и др.), показатели, вычитаемое', answer_rule='перевод программой или разбор «единица и нули минус число»; целое',
     mistakes=['не учесть заём при вычитании', 'перепутать 16^k и 4^(2k)'])
_ege(14, 'unknown-digit', 'Системы счисления: найти неизвестную цифру по делимости',
     gen=wrap(G.gen_ege14, 'inf-ege-14'), check=G.check_ege14, filt=by('kind', 'unknown_digit'), kes='Позиционные системы счисления', answer='число',
     invariant='запись с одной неизвестной цифрой в системе с основанием b; условие делимости; найти цифру или значение',
     varies='основание, цифры, делитель', answer_rule='перебор цифры 0..b−1; целое', mistakes=['цифра ≥ основания', 'взять не наименьший вариант'])
_ege(15, 'bitwise', 'Законы логики: поразрядная конъюнкция, наименьшее A',
     gen=wrap(G.gen_ege15, 'inf-ege-15'), check=G.check_ege15, filt=by('kind', 'bits'), kes='Законы математической логики', answer='число',
     invariant='формула с x & a = 0 и x & A; найти наименьшее A, при котором формула тождественно истинна',
     varies='числа a, b, структура формулы', answer_rule='перебор A с проверкой x до 2^k; целое', mistakes=['A как объединение вместо нужных битов'])
_ege(15, 'segments', 'Законы логики: отрезки P, Q, наименьшая длина A',
     gen=wrap(G.gen_ege15, 'inf-ege-15'), check=G.check_ege15, filt=by('kind', 'segments'), kes='Законы математической логики', answer='число',
     invariant='формула (x ∈ P) → ((x ∈ Q) ∨ (x ∈ A)) тождественно истинна; найти наименьшую длину A',
     varies='границы P и Q', answer_rule='A ⊇ P \\ Q, длина покрытия; число', mistakes=['длина одной части P \\ Q вместо всего покрытия'])
_ege(15, 'del', 'Законы логики: делимость ДЕЛ(x, A), наименьшее/наибольшее A',
     gen=gen_ege15_del, check=check_ege15_del, kes='Законы математической логики', answer='число',
     invariant='формула с ДЕЛ(x, A), ДЕЛ(x, p), ДЕЛ(x, q); найти наименьшее (или наибольшее) A',
     varies='пара p, q, форма формулы', answer_rule='перебор A с проверкой x; для «наибольшего» — НОК; целое',
     mistakes=['ответ НОД вместо НОК', 'проверить x только до 100'])
_ege(16, 'recurrent-value', 'Рекуррентная функция: значение F(N)',
     gen=wrap(G.gen_ege16, 'inf-ege-16'), check=both(G.check_ege16, exec_ege16), kes='Рекурсивные алгоритмы', answer='число',
     invariant='F задана базой и 1–2 рекуррентными правилами (линейное, по чётности, два предыдущих); найти F(N)',
     varies='коэффициенты, форма правила, N (15–30)', answer_rule='вычисление снизу вверх или lru_cache (exec эталона); целое',
     mistakes=['перепутать правила для чётного и нечётного n', 'ошибка в базе'])
_ege(17, 'pairs-div', 'Последовательность: пары соседних с условием делимости — количество и максимум суммы',
     gen=wrap(G.gen_ege17, 'inf-ege-17'), check=G.check_ege17, filt=by('mode', 'div'), kes='Обработка числовых последовательностей', answer='два числа через пробел',
     mini='12–16 чисел в условии вместо файла .txt',
     invariant='целые числа, пара — соседние элементы, условие на делимость; ответ — количество и наибольшая сумма',
     varies='числа, делитель, вид условия', answer_rule='один проход по парам; «count max»', mistakes=['остаток отрицательных чисел', 'пары не соседних'])
_ege(17, 'pairs-last', 'Последовательность: пары соседних с условием на последнюю цифру',
     gen=wrap(G.gen_ege17, 'inf-ege-17'), check=G.check_ege17, filt=by('mode', 'last'), kes='Обработка числовых последовательностей', answer='два числа через пробел',
     mini='12–16 чисел в условии вместо файла .txt',
     invariant='то же, условие на последнюю цифру', varies='числа, цифра', answer_rule='один проход; «count max»', mistakes=['последняя цифра отрицательного числа'])
_ege(18, 'robot-coins', 'Робот на поле: максимальная и минимальная сумма монет',
     gen=wrap(G.gen_ege18, 'inf-ege-18'), check=G.check_ege18, kes='Динамическое программирование в электронных таблицах', answer='два числа через пробел',
     mini='поле 3×3–3×5 в условии вместо .ods 20×20',
     invariant='движение вправо/вниз из левого верхнего в правый нижний угол; найти max и min суммы',
     varies='размер, числа в клетках', answer_rule='динамика по клеткам; «max min»', mistakes=['перепутать порядок max/min', 'не учесть начальную клетку'])
_ege(19, 'game-vanya-first', 'Игра с кучей камней: Ваня выигрывает первым ходом после неудачного хода Пети',
     gen=wrap(G.gen_ege19, 'inf-ege-19'), check=G.check_ege19, filt=by('task', 19), kes='Теория игр: дерево игры', answer='число',
     invariant='одна куча, 3 хода (+a, +b, ×m), порог; найти минимальное S с описанным сценарием', varies='ходы, порог',
     answer_rule='перебор S с анализом позиций; целое', mistakes=['S, при котором Петя выигрывает сам первым ходом'])
_ege(20, 'game-petya-second', 'Игра: Петя не может выиграть первым ходом, но выигрывает вторым',
     gen=wrap(G.gen_ege19, 'inf-ege-20'), check=G.check_ege19, filt=by('task', 20), kes='Теория игр: дерево игры', answer='два числа',
     invariant='те же правила; два значения S с выигрышной стратегией Пети за 2 хода', varies='ходы, порог',
     answer_rule='позиции P2 без P1; два числа по возрастанию', mistakes=['включить позиции, где Петя выигрывает первым ходом'])
_ege(21, 'game-vanya-second', 'Игра: Ваня выигрывает первым или вторым ходом при любой игре Пети',
     gen=wrap(G.gen_ege19, 'inf-ege-21'), check=G.check_ege19, filt=by('task', 21), kes='Теория игр: дерево игры', answer='число',
     invariant='те же правила; минимальное S, где у Вани стратегия за ≤ 2 хода, но не за 1', varies='ходы, порог',
     answer_rule='позиции V2 без V1; целое', mistakes=['взять позицию V1'])
_ege(22, 'processes-total', 'Параллельные процессы: минимальное время завершения всех',
     gen=wrap(G.gen_ege22, 'inf-ege-22'), check=G.check_ege22, filt=by('ask', 'total'), kes='Многопроцессорные системы, зависимости процессов', answer='число',
     mini='5–9 процессов в условии вместо .ods на 50+',
     invariant='таблица процессов с длительностью и зависимостями; время завершения всех', varies='число процессов, времена, зависимости',
     answer_rule='критический путь; целое', mistakes=['сложить все длительности', 'начать процесс до завершения всех предшественников'])
_ege(22, 'processes-one', 'Параллельные процессы: момент завершения конкретного процесса',
     gen=wrap(G.gen_ege22, 'inf-ege-22'), check=G.check_ege22, filt=by('ask', 'one'), kes='Многопроцессорные системы, зависимости процессов', answer='число',
     mini='5–9 процессов в условии', invariant='то же; вопрос про один процесс', varies='таблица', answer_rule='наибольший путь до процесса плюс его длительность',
     mistakes=['учесть зависимости не полностью'])
_ege(23, 'paths-via', 'Граф дорог: число путей с обязательными и запретными городами',
     gen=gen_ege23_paths, check=check_ege23_paths, kes='Графы: пути в ориентированном графе', answer='число',
     invariant='ориентированный граф без циклов, 9–12 городов; число путей из первого в последний через/минуя названные города',
     varies='рёбра, названные города, вид условия', answer_rule='динамика по вершинам; целое', mistakes=['не обнулить запретный город', 'посчитать пути через город дважды'])
_ege(23, 'shortest-path', 'Граф дорог: длина кратчайшего пути по таблице',
     gen=gen_ege23_short, check=check_ege23_short, kes='Графы: кратчайшие пути, весовая таблица', answer='число',
     invariant='таблица длин дорог между 6–8 пунктами; кратчайший путь между двумя', varies='пункты, длины',
     answer_rule='Дейкстра / Флойд; целое', mistakes=['взять прямую дорогу как кратчайшую', 'пропустить путь через 3+ пункта'])
for mode, slug, title in [('run', 'longest-run', 'Строка: длина наибольшей серии одинаковых символов'),
                          ('noadj', 'no-adjacent', 'Строка: наибольшая подстрока без соседних одинаковых'),
                          ('without', 'without-char', 'Строка: наибольшая подстрока без заданного символа'),
                          ('pairs', 'pair-chain', 'Строка: наибольшая цепочка из заданных пар')]:
    _ege(24, slug, title, gen=wrap(G.gen_ege24, 'inf-ege-24'), check=G.check_ege24, filt=by('mode', mode),
         kes='Обработка символьных строк', answer='число', mini='строка 28–40 символов в условии вместо файла на 10⁶',
         invariant='строка из 3–4 латинских букв; вопрос про длину подстроки с условием', varies='алфавит, строка, условие',
         answer_rule='перебор всех подстрок; целое', mistakes=['длина серии на 1 меньше/больше', 'считать подпоследовательность вместо подстроки'])
_ege(25, 'mask-count', 'Маска числа и делимость: количество чисел',
     gen=wrap(G.gen_ege25, 'inf-ege-25'), check=both(G.check_ege25, exec_ege25), filt=lambda p: p['kind'] == 'mask' and p['ask'] == 'count',
     kes='Обработка целочисленной информации: маски, делители', answer='число', pc=True,
     invariant='маска с «?» и «*», делитель d, числа ≤ 10⁶; сколько чисел подходят', varies='маска, d',
     answer_rule='перебор кратных d с fnmatch (exec эталона); целое', mistakes=['число с ведущим нулём', '«*» как ровно одна цифра'])
_ege(25, 'mask-extreme', 'Маска числа и делимость: наименьшее или наибольшее число',
     gen=wrap(G.gen_ege25, 'inf-ege-25'), check=both(G.check_ege25, exec_ege25), filt=lambda p: p['kind'] == 'mask' and p['ask'] != 'count',
     kes='Обработка целочисленной информации: маски, делители', answer='число',
     invariant='то же, найти крайнее число', varies='маска, d', answer_rule='перебор, min/max; целое', mistakes=['перебрать не все длины'])
_ege(25, 'divisors', 'Числа на отрезке с ровно k делителями (кроме 1 и самого числа)',
     gen=wrap(G.gen_ege25, 'inf-ege-25'), check=both(G.check_ege25, exec_ege25), filt=by('kind', 'div'),
     kes='Обработка целочисленной информации: делители', answer='число', pc=True,
     invariant='отрезок [a; b], ровно k нетривиальных делителей; количество или наибольшее', varies='отрезок, k',
     answer_rule='τ(x) − 2 = k через разложение (exec эталона); целое', mistakes=['корень квадрата посчитать дважды', 'учесть 1 и само число'])
_ege(26, 'disk-files', 'Жадный алгоритм: сколько файлов поместится и наибольший из них',
     gen=wrap(G.gen_ege26, 'inf-ege-26'), check=G.check_ege26, kes='Сортировка, жадные алгоритмы', answer='два числа через пробел',
     mini='8–12 файлов в условии вместо .txt на 10 000',
     invariant='объём диска и размеры файлов; максимум файлов и максимальный размер файла при этом максимуме', varies='размеры, объём',
     answer_rule='сортировка + замена самого большого взятого; перебор подмножеств для проверки', mistakes=['взять наибольший файл вообще, а не при максимальном количестве'])
_ege(27, 'clusters-center', 'Кластеризация точек: центр самого большого кластера',
     gen=wrap(G.gen_ege27, 'inf-ege-27'), check=G.check_ege27, kes='Анализ данных: кластеризация', answer='два числа через пробел',
     mini='15–25 точек, 2–3 кластера в условии вместо файла на тысячи строк',
     invariant='точки на плоскости, кластеры по расстоянию; центр — точка с минимальной суммой расстояний', varies='точки, число кластеров',
     answer_rule='DSU/пороговая связность и перебор центров; координаты через пробел', mistakes=['центр как среднее координат, а не точка кластера'])

# ---------------- ОГЭ
_oge(1, 'removed-word', 'Объём текста: какое слово удалили',
     gen=wrap(G.gen_oge1, 'inf-oge-01'), check=G.check_oge1, kes='Измерение информации: кодировки текста', answer='слово',
     invariant='список слов в кодировке с фиксированной глубиной; объём уменьшился на N байт — найти удалённое слово',
     varies='категория слов, кодировка (8/16 бит), список', answer_rule='длина слова из разности байт; единственное слово такой длины',
     mistakes=['забыть запятую и пробел', 'бит и байт'])
_oge(2, 'decode', 'Декодирование сообщения по таблице кодов',
     gen=wrap(G.gen_oge2, 'inf-oge-02', accept=lambda c: len(set(c['a'])) >= 2), check=G.check_oge2, kes='Кодирование и декодирование информации', answer='слово (последовательность букв)',
     invariant='таблица кодов букв, закодированная строка, единственная расшифровка', varies='коды, буквы, длина сообщения',
     answer_rule='однозначное декодирование (проверка перебором разбиений)', mistakes=['неоднозначное разбиение на коды'])
for kind, slug, title in [('min_notlt_odd', 'min-not-lt-odd', 'Истинность высказывания: наименьшее число (НЕ, нечётное)'),
                          ('max_lt_notodd', 'max-lt-not-odd', 'Истинность высказывания: наибольшее число (НЕ нечётное)'),
                          ('min_and_div', 'min-and-div', 'Истинность высказывания: наименьшее число (И, делимость)')]:
    _oge(3, slug, title, gen=wrap(G.gen_oge3, 'inf-oge-03'), check=G.check_oge3, filt=by('kind', kind),
         kes='Логические значения, операции, высказывания', answer='число',
         invariant='составное высказывание из НЕ/И/ИЛИ над сравнениями и чётностью; найти крайнее натуральное число, для которого оно истинно',
         varies='границы, чётность, делитель', answer_rule='перебор чисел; целое', mistakes=['НЕ (x < a) как x < a', 'ИЛИ как И'])
_oge(4, 'shortest-table', 'Кратчайший путь по таблице длин дорог',
     gen=wrap(G.gen_oge4, 'inf-oge-04'), check=G.check_oge4, kes='Графы, таблицы: кратчайший путь', answer='число',
     invariant='таблица дорог между 5–6 пунктами; кратчайший путь между двумя', varies='пункты, длины, ограничение «через»',
     answer_rule='перебор путей / Дейкстра; целое', mistakes=['взять прямую дорогу', 'пропустить путь через два пункта'])
_oge(5, 'executor-two-cmds', 'Исполнитель с двумя командами: неизвестное в команде',
     gen=wrap(G.gen_oge5, 'inf-oge-05'), check=G.check_oge5, kes='Алгоритмы для исполнителя', answer='число',
     invariant='две команды (прибавь/умножь с неизвестным b), программа из цифр, начальное и конечное число; найти b',
     varies='команды, программа, числа', answer_rule='обратный ход или перебор b; целое', mistakes=['применить команды в обратном порядке'])
_oge(6, 'program-yes', 'Программа с ветвлением: сколько запусков дали YES',
     gen=wrap(G.gen_oge6, 'inf-oge-06'), check=both(G.check_oge6, exec_oge6), kes='Программирование: ветвление, логические выражения', answer='число',
     invariant='листинг с if (or/and) над двумя вводами; 9 пар; сколько раз печатается YES', varies='границы, or/and, знаки, пары',
     answer_rule='проверка условия на каждой паре (exec эталона); целое', mistakes=['or как and', 'строгое и нестрогое неравенство'])
_oge(7, 'url', 'Адрес файла в интернете: собрать из фрагментов',
     gen=wrap(G.gen_oge7, 'inf-oge-07'), check=G.check_oge7, kes='Интернет: адрес ресурса', answer='последовательность букв',
     invariant='фрагменты адреса (протокол, ://, сервер, /, файл) с буквами; записать буквы в порядке адреса', varies='имена, расширения, порядок букв',
     answer_rule='протокол → :// → сервер → / → файл', mistakes=['перепутать «/» и «://»', 'сервер после файла'])
_oge(8, 'search-euler', 'Запросы к поисковой системе: число страниц по И/ИЛИ',
     gen=wrap(G.gen_oge8, 'inf-oge-8'), check=G.check_oge8, kes='Поиск информации: логические запросы', answer='число',
     invariant='известны три количества из четырёх (A, B, A|B, A&B); найти четвёртое', varies='слова, числа, что спрашивается',
     answer_rule='|A ∪ B| = |A| + |B| − |A ∩ B|; целое', mistakes=['сложить без вычитания пересечения'])
_oge(9, 'paths-count', 'Число путей в ориентированном графе',
     gen=wrap(G.gen_oge9, 'inf-oge-09'), check=G.check_oge9, kes='Графы: число путей', answer='число',
     invariant='граф без циклов на 7–10 вершинах; число путей из первой в последнюю (иногда через вершину)', varies='рёбра, ограничение',
     answer_rule='динамика по вершинам; целое', mistakes=['потерять входящее ребро', 'путь через вершину — не перемножить'])
_oge(10, 'compare-bases', 'Числа в разных системах: наибольшее/наименьшее',
     gen=wrap(G.gen_oge10, 'inf-oge-10'), check=G.check_oge10, kes='Системы счисления', answer='число',
     invariant='три числа в системах 2, 8, 16; найти крайнее и записать в десятичной', varies='числа, основания, max/min',
     answer_rule='перевод всех в десятичную; целое', mistakes=['сравнивать по числу цифр', 'записать ответ не в десятичной'])
R('inf-oge-11-file-search', 'ОГЭ', 11, 'Поиск информации в файлах каталога', kind='llm', kes='Поиск информации в файловой системе', answer='слово или число',
  invariant='каталог текстовых файлов; найти файл/фрагмент по признаку и переписать слово или число из него', varies='каталог, вопрос',
  answer_rule='точное слово/число из текста', mistakes=['взять фрагмент из соседнего файла'],
  how='ИИ пишет 8–12 коротких «файлов» (по 2–3 предложения на школьную тему) и вопрос, ответ на который есть ровно в одном файле',
  check_rule='скрипт: ответ встречается ровно в одном файле как подстрока; второй проход вслепую подтверждает единственность',
  example={'q': 'В каталоге 10 текстов о планетах. В каком году, по тексту файла о Марсе, был запущен первый марсоход? Ответ — число.', 'a': '1997', 'e': 'Ищем файл по названию/ключу, выписываем число.'},
  capacity='по цене генерации', why='нужен набор файлов; на телефоне заменяется чтением 8–12 коротких текстов')
_oge(12, 'mask-count', 'Файлы по маске: сколько имён подходит',
     gen=gen_oge12, check=check_oge12, kes='Файловая система: маски имён файлов', answer='число', mini='12–16 имён файлов в условии вместо каталога',
     invariant='список имён файлов и маска с «*» и «?»; сколько подходят', varies='имена, расширения, маска',
     answer_rule='fnmatch / регулярное выражение; целое', mistakes=['«?» как любая строка', 'точка в маске не учтена'])
R('inf-oge-13-doc', 'ОГЭ', 13, 'Презентация или текстовый документ по образцу', kind='llm', kes='Создание документов и презентаций', answer='файл-ответ',
  invariant='13.1 — презентация из 3 слайдов на тему с материалами; 13.2 — текст с заданными параметрами форматирования и таблицей',
  varies='тема, параметры', answer_rule='критерии эксперта (структура, шрифты, поля, таблица)', mistakes=['лишние слайды', 'не те поля/шрифт'],
  how='ИИ пишет тему и набор критериев в стиле КИМ; ученик выполняет на компьютере', check_rule='самооценка по рубрике (flip)',
  example={'q': 'Создайте презентацию из трёх слайдов о Байкале по материалам папки. Первый слайд — титульный с названием и автором…', 'a': 'рубрика', 'e': 'Проверяется экспертом по критериям.'},
  capacity='по цене генерации', why='ответ — файл, автоматическая проверка невозможна')
_oge(14, 'table-count', 'Электронная таблица: сколько записей по двум условиям',
     gen=gen_oge14, check=check_oge14, filt=by('ask', 'count'), kes='Электронные таблицы: обработка данных', answer='число', mini='8–10 строк в условии вместо .ods на сотни',
     invariant='таблица (фамилия, предмет, баллы, школа); сколько строк по предмету с баллом выше порога', varies='строки, предмет, порог',
     answer_rule='СЧЁТЕСЛИМН или отбор вручную; целое', mistakes=['«больше» как «не меньше»'])
_oge(14, 'table-avg', 'Электронная таблица: средний балл по условию',
     gen=gen_oge14, check=check_oge14, filt=by('ask', 'avg'), kes='Электронные таблицы: обработка данных', answer='число (до двух знаков)', mini='8–10 строк в условии',
     invariant='та же таблица; среднее по предмету', varies='строки, предмет', answer_rule='СРЗНАЧЕСЛИ; десятичная дробь с двумя знаками',
     mistakes=['среднее по всем строкам', 'округление до целого'])
R('inf-oge-15-robot', 'ОГЭ', 15, 'Алгоритм для исполнителя Робот', kind='llm', kes='Алгоритмы для исполнителя Робот', answer='файл-ответ (программа)',
  invariant='поле с стенами заданной конфигурации; закрасить клетки по правилу при неизвестных длинах стен', varies='конфигурация стен, правило закраски',
  answer_rule='программа проверяется на нескольких полях (рубрика)', mistakes=['программа для одной длины стены', 'Робот разбивается о стену'],
  how='ИИ описывает поле словами и правило; ученик пишет программу; в тренажёре — шаг «какая команда следующая» (one)',
  check_rule='рубрика; для шаговых карточек — моделирование Робота скриптом', example={'q': 'Робот стоит у левого конца горизонтальной стены неизвестной длины. Закрасьте все клетки над стеной…', 'a': 'рубрика', 'e': 'нц пока снизу стена: закрасить; вправо кц'},
  capacity='десятки конфигураций', why='нужен рисунок поля и проверка программы на нескольких полях')
_oge(16, 'sequence-program', 'Программа для последовательности: количество или сумма по условию',
     gen=gen_oge16, check=check_oge16, kes='Программирование: циклы, ввод последовательности', answer='число', mini='8–12 чисел в условии; ответ — что напечатает верная программа',
     invariant='нужно написать программу с циклом и условием; проверка — вывод на заданных данных', varies='условие, агрегат (количество/сумма), числа',
     answer_rule='exec эталонной программы; целое', mistakes=['условие «и» вместо «или»', 'считать сумму вместо количества'])
_oge(16, 'trace-loop', 'Программа с циклом for: что будет напечатано',
     gen=gen_oge16_trace, check=check_oge16_trace, kes='Программирование: циклы', answer='число',
     invariant='короткий листинг с for и одной операцией над s; найти вывод', varies='начальное s, операция, число итераций',
     answer_rule='пошаговое выполнение / exec; целое', mistakes=['range(1, n+1) как n+1 итераций', 'перепутать порядок операций'])


# ================================================================ самопроверка, экспорт, выборки


def sample_cards(proto, rng, n, cap, max_calls=None):
    """До n разных карточек прототипа и оценка ёмкости (разных условий на cap подходящих попыток)."""
    gen, filt, chk = proto['gen'], proto['filt'], proto['check']
    seen, cards, bad = set(), [], 0
    calls, matched = 0, 0
    max_calls = max_calls or cap * 30
    while matched < cap and calls < max_calls:
        calls += 1
        c, p = gen(rng)
        if filt and not filt(p):
            continue
        matched += 1
        if c['q'] in seen:
            continue
        seen.add(c['q'])
        if len(cards) < n:
            ok = c['a'] not in ('', None) and chk(p, c)
            if not ok:
                bad += 1
                c = dict(c, _bad=True)
            cards.append(c)
    return cards, bad, len(seen), matched


def selftest(n=50, cap=300, seed=2026, only=None):
    rows, all_cards = [], []
    for pr in PROTOS:
        if only and not pr['id'].startswith(only):
            continue
        if pr['gen'] is None:
            rows.append({'id': pr['id'], 'kind': pr['kind'], 'cards': 0, 'bad': 0, 'capacity': None, 'kinds': {}})
            continue
        rng = random.Random(seed + hash(pr['id']) % 1000)
        cards, bad, distinct, matched = sample_cards(pr, rng, n, cap)
        rows.append({'id': pr['id'], 'kind': pr['kind'], 'cards': len(cards), 'bad': bad,
                     'capacity': distinct, 'cap_hit': distinct >= cap, 'matched': matched,
                     'kinds': dict(Counter(c['k'] for c in cards))})
        for c in cards:
            all_cards.append(dict(c, proto=pr['id']))
    ids = Counter(c['id'] for c in all_cards)
    qs = Counter(c['q'] for c in all_cards)
    dup = sum(v - 1 for v in ids.values() if v > 1) + sum(v - 1 for v in qs.values() if v > 1)
    return rows, all_cards, dup


def load_fidelity():
    path = os.path.join(ROOT, 'data', 'research', 'inf-fidelity.json')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return {v['id']: v for v in json.load(f)['verdicts']}


def export(rows, cards, path=None):
    fid = load_fidelity()
    by_id = {}
    for c in cards:
        by_id.setdefault(c['proto'], c)
    row = {r['id']: r for r in rows}
    out = []
    for pr in PROTOS:
        r = row.get(pr['id'], {})
        ex = pr.get('example')
        if pr['gen'] is not None and pr['id'] in by_id:
            c = by_id[pr['id']]
            ex = {'k': c['k'], 'q': c['q'], 'a': c['a'], 'e': c['e']}
        cap = pr.get('capacity') if pr['gen'] is None else r.get('capacity')
        v = fid.get(pr['id'], {})
        out.append({
            'id': pr['id'], 'exam': pr['exam'], 'n': pr['n'], 'n2026': pr['n2026'], 'title': pr['title'],
            'kes': pr['passport']['kes'], 'invariant': pr['invariant'], 'varies': pr['varies'],
            'answer_rule': pr['answer_rule'], 'mistakes': pr['mistakes'],
            'gen': ({'kind': pr['kind'], 'fn': pr['gen_name'], 'mini': pr.get('mini'), 'pc': pr.get('pc', False)}
                    if pr['gen'] is not None else {'kind': pr['kind'], **pr['recipe']}),
            'passport': pr['passport'],
            'capacity': cap, 'capacity_note': ('300+ (упёрлось в предел попыток)' if r.get('cap_hit') else
                                              ('оценка' if pr['gen'] is None else 'разных условий на 300 попыток')),
            'selfcheck': ({'cards': r.get('cards'), 'mismatched': r.get('bad')} if pr['gen'] is not None else None),
            'fidelity': {'status': v.get('status', 'unchecked'), 'checked': v.get('checked', 0),
                         'notes': v.get('notes', ''), 'fixed': v.get('fixed', '')},
            'example': ex,
        })
    meta = {
        'about': 'Каталог прототипов заданий ЕГЭ по информатике (нумерация проекта КИМ 2027: 10 — маска подсети, 13 — анализ '
                 'алгоритма, 23 — графы; n2026 — номер 2026 года, где отличается) и ОГЭ (1–16). На прототип: что неизменно, '
                 'что меняется, правило ответа, типичные ошибки, паспорт КИМ, генератор или рецепт, наш пример. Тексты ФИПИ '
                 'и коммерческих банков не включены; примеры составлены генератором. Поле kes — тема кодификатора словами, '
                 'числовые коды не воспроизводятся.',
        'built_by': 'python3 tools/research/gen_inf.py --protos --export',
        'counts': {'total': len(out),
                   'ЕГЭ': sum(1 for p in out if p['exam'] == 'ЕГЭ'), 'ОГЭ': sum(1 for p in out if p['exam'] == 'ОГЭ'),
                   'kinds': dict(Counter(p['gen']['kind'] for p in out)),
                   'fidelity': dict(Counter(p['fidelity']['status'] for p in out))},
        'selfcheck': {'cards_per_proto': max((r.get('cards') or 0) for r in rows) if rows else 0,
                      'mismatched': sum(r.get('bad') or 0 for r in rows)},
    }
    path = path or os.path.join(ROOT, 'data', 'source', 'inf-prototypes.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'meta': meta, 'prototypes': out}, f, ensure_ascii=False, indent=1)
    return path, out


def apply_fidelity(path=None):
    """Переписать поле fidelity в готовом каталоге из data/research/inf-fidelity.json (без пересчёта карточек)."""
    from collections import Counter as _C
    path = path or os.path.join(ROOT, 'data', 'source', 'inf-prototypes.json')
    fid = load_fidelity()
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    for pr in data['prototypes']:
        v = fid.get(pr['id'], {})
        pr['fidelity'] = {'status': v.get('status', 'unchecked'), 'checked': v.get('checked', 0),
                          'notes': v.get('notes', ''), 'fixed': v.get('fixed', '')}
    data['meta']['counts']['fidelity'] = dict(_C(p['fidelity']['status'] for p in data['prototypes']))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return data['meta']['counts']['fidelity']


def samples(k, seed, path):
    """k случайных аналогов на прототип — для экзаменационной проверки."""
    rng = random.Random(seed)
    out = []
    for pr in PROTOS:
        if pr['gen'] is None:
            continue
        cards, _, _, _ = sample_cards(pr, rng, 30, 30)
        for c in rng.sample(cards, min(k, len(cards))):
            out.append({'proto': pr['id'], 'k': c['k'], 'q': c['q'], 'a': c['a']})
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    return len(out)


def print_table(rows, dup):
    print(f'{"прототип":34} {"вид":6} {"карт.":>5} {"несошл.":>7} {"ёмкость":>8}  типы')
    for r in rows:
        cap = '—' if r['capacity'] is None else (f'{r["capacity"]}+' if r.get('cap_hit') else str(r['capacity']))
        print(f'{r["id"]:34} {r["kind"]:6} {r["cards"]:5} {r["bad"]:7} {cap:>8}  {r["kinds"]}')
    gens = [r for r in rows if r['capacity'] is not None]
    print(f'Итого: {len(rows)} прототипов ({len(gens)} с генератором), карточек {sum(r["cards"] for r in rows)}, '
          f'несошедшихся {sum(r["bad"] for r in rows)}, дублей между прототипами {dup}, '
          f'ёмкость (нижняя оценка) {sum(r["capacity"] for r in gens)}, упёрлось в предел: {sum(1 for r in gens if r.get("cap_hit"))}')
