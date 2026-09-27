"""Общее ядро генераторов по физике и химии: форматирование ответов, карточки, химические формулы,
реестр прототипов и проверки (независимый пересчёт, баланс, дубли, сходство с текстами ФИПИ).

Модули прототипов — tools/research/proto_*.py. Каждый регистрирует прототипы через @proto(...) или recipe(...);
gen_phys_chem.py подхватывает их сам (править его не нужно).
"""
import hashlib
import json
import math
import re
from collections import Counter
from fractions import Fraction as Fr

G = 10

# ---------------------------------------------------------------- числа и карточки

def fmt(x, dec=None):
    """Число → строка как в бланке: запятая, без лишних нулей. dec — округлить (половина вверх)."""
    if isinstance(x, Fr):
        x = x.numerator / x.denominator
    if dec is not None:
        q = Fr(round(Fr(x) * 10 ** dec + Fr(1, 10 ** 9)) if x >= 0 else -round(-Fr(x) * 10 ** dec + Fr(1, 10 ** 9)), 10 ** dec)
        s = f'{float(q):.{dec}f}'
    else:
        s = f'{x:.6f}'
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    if s in ('-0', ''):
        s = '0'
    return s.replace('.', ',')


def exact(x, max_dec=2):
    """Ответ части 1 должен быть конечной дробью с ≤ max_dec знаками. Иначе None (перебрать параметры)."""
    x = Fr(x)
    y = x * 10 ** max_dec
    if y.denominator != 1:
        return None
    return fmt(x)


def num(s):
    return float(s.replace(',', '.'))


def ru(x):
    """Параметр в тексте условия: 2.5 → «2,5», −3 — типографский минус."""
    return fmt(Fr(x).limit_denominator(10 ** 6)).replace('-', '−')


def card(typ, exam, task, t, q, a, e, k='num', o=None, extra=None):
    key = q + json.dumps(o, ensure_ascii=False, sort_keys=True) if o is not None else q
    c = {'id': f'g-{typ}-' + hashlib.sha1(key.encode()).hexdigest()[:10], 't': t, 'k': k, 'q': q, 'a': a}
    if o is not None:
        c['o'] = o
    c['e'] = e
    c['gen'] = {'type': typ, 'exam': exam, 'task': task}
    if extra:
        c['gen'].update(extra)
    if k == 'num' and 'wrong' in c['gen']:
        c['gen']['wrong'] = distractors(a, c['gen']['wrong'])
    return c


def distractors(ans, wrong):
    """Неверные ответы: сначала типичные ошибки, затем запасные (×2, ÷2, ×10) — чтобы всегда было 3 варианта."""
    out = []
    for w in list(wrong) + [None]:
        if w and w != ans and w not in out and re.fullmatch(r'-?\d+(,\d+)?', w):
            out.append(w)
    x = num(ans)
    for f in (2, 0.5, 10, 0.1, 3):
        if len(out) >= 3:
            break
        w = fmt(Fr(x).limit_denominator(10 ** 6) * Fr(f).limit_denominator(10))
        if w != ans and w not in out and w != '0':
            out.append(w)
    return out[:4]


def choose(rng, *xs):
    return rng.choice(xs)


def with_options(c, rng, wrong):
    """Числовую карточку → вариант 'one' с дистракторами из типичных ошибок."""
    right = c['a']
    opts = [right] + [w for w in dict.fromkeys(wrong) if w and w != right]
    opts = opts[:4]
    if len(opts) < 3:
        return c
    rng.shuffle(opts)
    ids = 'абвг'
    c = dict(c, k='one', o=[{'id': ids[i], 't': v} for i, v in enumerate(opts)])
    c['a'] = ids[opts.index(right)]
    return c


class Retry(Exception):
    pass


# Ar как в КИМ: целые, кроме Cl = 35,5
AR = {'H': 1, 'He': 4, 'Li': 7, 'Be': 9, 'B': 11, 'C': 12, 'N': 14, 'O': 16, 'F': 19, 'Ne': 20, 'Na': 23, 'Mg': 24,
      'Al': 27, 'Si': 28, 'P': 31, 'S': 32, 'Cl': Fr(71, 2), 'Ar': 40, 'K': 39, 'Ca': 40, 'Cr': 52, 'Mn': 55, 'Fe': 56,
      'Co': 59, 'Ni': 59, 'Cu': 64, 'Zn': 65, 'Br': 80, 'Ag': 108, 'I': 127, 'Ba': 137, 'Pb': 207}


def parse_formula(f):
    """'Ca(OH)2' → {'Ca':1,'O':2,'H':2}; поддерживает скобки и гидраты через '·'."""
    total = Counter()
    for part in f.split('·'):
        mult = 1
        m = re.match(r'^(\d+)(.*)$', part)
        if m:
            mult, part = int(m.group(1)), m.group(2)
        stack = [Counter()]
        i = 0
        while i < len(part):
            ch = part[i]
            if ch == '(':
                stack.append(Counter())
                i += 1
            elif ch == ')':
                i += 1
                m = re.match(r'\d+', part[i:])
                n = int(m.group()) if m else 1
                i += len(m.group()) if m else 0
                top = stack.pop()
                for k, v in top.items():
                    stack[-1][k] += v * n
            else:
                m = re.match(r'([A-Z][a-z]?)(\d*)', part[i:])
                if not m:
                    raise ValueError(f'не разобрать {f!r} у {part[i:]!r}')
                stack[-1][m.group(1)] += int(m.group(2) or 1)
                i += len(m.group())
        for k, v in stack[0].items():
            total[k] += v * mult
    return dict(total)


def molar(f):
    return sum(AR[e] * n for e, n in parse_formula(f).items())


def balance(lhs, rhs):
    """Коэффициенты уравнения: наименьшие целые из ядра матрицы элементов (дроби, метод Гаусса)."""
    species = lhs + rhs
    elems = sorted({e for s in species for e in parse_formula(s)})
    M = [[Fr(parse_formula(s).get(e, 0) * (1 if j < len(lhs) else -1)) for j, s in enumerate(species)] for e in elems]
    n = len(species)
    rows, piv = [r[:] for r in M], []
    r = 0
    for c in range(n):
        p = next((i for i in range(r, len(rows)) if rows[i][c] != 0), None)
        if p is None:
            continue
        rows[r], rows[p] = rows[p], rows[r]
        rows[r] = [x / rows[r][c] for x in rows[r]]
        for i in range(len(rows)):
            if i != r and rows[i][c] != 0:
                f = rows[i][c]
                rows[i] = [a - f * b for a, b in zip(rows[i], rows[r])]
        piv.append(c)
        r += 1
    free = [c for c in range(n) if c not in piv]
    if len(free) != 1:
        raise ValueError(f'неоднозначный баланс {lhs} → {rhs}')
    x = [Fr(0)] * n
    x[free[0]] = Fr(1)
    for i, c in enumerate(piv):
        x[c] = -rows[i][free[0]]
    lcm = 1
    for v in x:
        lcm = lcm * v.denominator // math.gcd(lcm, v.denominator)
    k = [int(v * lcm) for v in x]
    g = 0
    for v in k:
        g = math.gcd(g, v)
    k = [v // g for v in k]
    if any(v <= 0 for v in k):
        raise ValueError(f'отрицательный коэффициент {lhs} → {rhs}: {k}')
    return k[:len(lhs)], k[len(lhs):]


def check_balance(lhs, rhs, kl, kr):
    left, right = Counter(), Counter()
    for s, k in zip(lhs, kl):
        for e, n in parse_formula(s).items():
            left[e] += n * k
    for s, k in zip(rhs, kr):
        for e, n in parse_formula(s).items():
            right[e] += n * k
    return left == right


def eq_str(lhs, rhs, kl, kr, arrow='→'):
    side = lambda ss, ks: ' + '.join((f'{k}' if k > 1 else '') + s for s, k in zip(ss, ks))
    return f'{side(lhs, kl)} {arrow} {side(rhs, kr)}'


def pretty(f):
    return re.sub(r'(?<=[A-Za-z)\]])(\d+)', lambda m: m.group(1).translate(str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')), f)


def sub(f):
    """Индексы в формуле: H2SO4 → H₂SO₄ (как pretty, но и для зарядов не трогает)."""
    return pretty(f)


# ================================================================= реестр прототипов
#
# Прототип — разновидность задания КИМ: неизменная схема решения + то, что можно менять.
# Запись в реестре = строка data/source/{phys,chem}-prototypes.json:
#   id, exam ('ЕГЭ'|'ОГЭ'), subj ('phys'|'chem'), n (номер задания КИМ 2027), title,
#   invariant (что неизменно), varies (что меняется), answer_rule (как считается ответ),
#   mistakes (типичные ошибки), gen (имя генератора или рецепт), capacity, example.
#
# Генератор: fn(rng) -> карточка, собранная через pcard(). В card['gen']['p'] лежат параметры,
# из которых solve(p) НЕЗАВИСИМО (другим кодом) пересчитывает ответ. Самопроверка сравнивает.

PROTOS = {}
ID_RE = re.compile(r'^(ph|ch)-(ege|oge)-\d{2}-[a-z0-9-]+$')


FIDELITY_KEYS = ('answer_format', 'style', 'level', 'time_min', 'scale', 'trap', 'kes', 'score')


def _meta(pid, exam, n, title, invariant, varies, answer_rule, mistakes, kind, kes, fidelity=None):
    if not ID_RE.match(pid):
        raise ValueError(f'плохой id прототипа {pid!r}: нужен вид ph-ege-01-slug')
    if pid in PROTOS:
        raise ValueError(f'повтор id прототипа {pid}')
    subj = 'phys' if pid.startswith('ph-') else 'chem'
    ex = 'ЕГЭ' if '-ege-' in pid else 'ОГЭ'
    if exam != ex or int(pid.split('-')[2]) != n:
        raise ValueError(f'{pid}: exam/n не совпадают с id')
    return {'id': pid, 'exam': exam, 'subj': subj, 'n': n, 'title': title, 'invariant': invariant, 'varies': varies,
            'answer_rule': answer_rule, 'mistakes': list(mistakes), 'kind': kind, 'kes': list(kes or []),
            'fidelity': _fid(pid, fidelity)}


def _fid(pid, f):
    """Соответствие КИМ (заполняет автор прототипа): answer_format — формат ответа как в КИМ 2027; style — формулировка
    и справочные данные; level — Б/П/В по спецификации; time_min — время на задание; scale — масштаб чисел/веществ как
    в банке; trap — какая «ловушка»/умение; kes — элементы кодификатора; score — баллы и частичный балл.
    Статус (pass/fail + причина) ставит экзаменационная проверка (fidelity_review.json)."""
    if f is None:
        return None
    extra = set(f) - set(FIDELITY_KEYS)
    if extra:
        raise ValueError(f'{pid}: неизвестные поля fidelity {sorted(extra)}')
    return dict(f)


def proto(pid, exam, n, title, *, invariant, varies, answer_rule, mistakes=(), solve=None, kind='param', kes=None,
          fidelity=None):
    """Декоратор генератора прототипа. kind: 'param' (формула) или 'dict' (по таблице веществ/фактов).
    solve(p) -> ответ в том же виде, что card['a'] (строка; для many — список id; для match — dict)."""
    def deco(fn):
        m = _meta(pid, exam, n, title, invariant, varies, answer_rule, mistakes, kind, kes, fidelity)
        if solve is None:
            raise ValueError(f'{pid}: нужен solve(p) для независимого пересчёта')
        m.update(fn=fn, solve=solve, gen=fn.__name__)
        PROTOS[pid] = m
        return fn
    return deco


def recipe(pid, exam, n, title, *, invariant, varies, answer_rule, mistakes=(), kind='llm', how, check, capacity, example,
           why=None, kes=None, fidelity=None):
    """Прототип без программного генератора: рецепт для ИИ ('llm') или справочника ('dict') + правило проверки.
    capacity — оценка числа разных аналогов; example — наш пример {q, a, e}; why — почему не param."""
    m = _meta(pid, exam, n, title, invariant, varies, answer_rule, mistakes, kind, kes, fidelity)
    m.update(fn=None, solve=None, gen={'kind': kind, 'recipe': how, 'check': check}, capacity=capacity,
             example=example, why=why)
    PROTOS[pid] = m
    return m


def pcard(pid, q, a, e, *, k='num', o=None, p=None, wrong=None, eq=None, eqs=None, nuc=None, extra=None):
    """Карточка прототипа. p — параметры для solve(); eq=(lhs, rhs, kl, kr) / eqs=[...] — уравнения для проверки баланса;
    nuc=(A,Z до, A,Z после) — ядерная реакция; wrong — типичные неверные ответы (для num)."""
    m = PROTOS[pid]
    key = q + (json.dumps(o, ensure_ascii=False, sort_keys=True) if o is not None else '')
    c = {'id': f'p-{pid}-' + hashlib.sha1(key.encode()).hexdigest()[:10],
         't': f"{'phys' if m['subj'] == 'phys' else 'chem'}-{'ege' if m['exam'] == 'ЕГЭ' else 'oge'}-{m['n']}",
         'k': k, 'q': q, 'a': a}
    if o is not None:
        c['o'] = o
    c['e'] = e
    g = {'proto': pid, 'p': p if p is not None else {}}
    if wrong is not None and k == 'num':
        g['wrong'] = distractors(a, [w for w in wrong if w is not None])
    if eq is not None:
        g['eqs'] = [list(eq)]
    if eqs:
        g.setdefault('eqs', []).extend([list(x) for x in eqs])
    if nuc is not None:
        g['nuc'] = list(nuc)
    if extra:
        g.update(extra)
    c['gen'] = g
    return c


def opts(items, ids='12345678'):
    """Список текстов → варианты [{id, t}] с цифрами как в бланке."""
    return [{'id': ids[i], 't': t} for i, t in enumerate(items)]


def match_opts(left, right, lids='АБВГД', rids='123456789'):
    return {'left': [{'id': lids[i], 't': t} for i, t in enumerate(left)],
            'right': [{'id': rids[i], 't': t} for i, t in enumerate(right)]}


def answer_str(c):
    """Ответ карточки как строка бланка: num/one — как есть; many — цифры по возрастанию; match — цифры по буквам."""
    a = c['a']
    if c['k'] == 'many':
        return ''.join(sorted(a))
    if c['k'] == 'match':
        return ''.join(a[x['id']] for x in c['o']['left'])
    return a


def same_answer(c, want):
    a = c['a']
    if c['k'] == 'many':
        return sorted(a) == sorted(want)
    if c['k'] == 'num' and isinstance(want, str):
        return a == want
    return a == want


# ================================================================= проверки карточек

def card_text(c):
    """Всё, что видит ученик: условие и варианты."""
    parts = [c['q']]
    o = c.get('o')
    if isinstance(o, list):
        parts += [x['t'] for x in o]
    elif isinstance(o, dict):
        parts += [x['t'] for x in o.get('left', [])] + [x['t'] for x in o.get('right', [])]
    return '\n'.join(parts)


def norm_key(c):
    """Ключ дубля: текст условия + варианты без пробельных различий."""
    return re.sub(r'\s+', ' ', card_text(c)).strip().lower()


def check_card(c, m):
    """Проверки одной карточки прототипа m. Возвращает список проблем."""
    errs = []
    for f in ('id', 't', 'k', 'q', 'a', 'e'):
        if f not in c or c[f] in (None, '', [], {}):
            errs.append(f'нет поля {f}')
    k = c.get('k')
    if k == 'num':
        if not re.fullmatch(r'-?\d+(,\d+)?', str(c['a'])):
            errs.append(f'ответ не число: {c["a"]!r}')
        elif len(c['a'].replace('-', '').replace(',', '')) > 9:
            errs.append(f'слишком длинный ответ {c["a"]}')
    elif k == 'one':
        ids = [o['id'] for o in c['o']]
        if c['a'] not in ids or len({o['t'] for o in c['o']}) != len(ids):
            errs.append('one: нет верного варианта или повторы')
    elif k == 'many':
        ids = [o['id'] for o in c['o']]
        if not c['a'] or not set(c['a']) <= set(ids) or len(set(c['a'])) != len(c['a']):
            errs.append('many: ответ не из вариантов')
        if len({o['t'] for o in c['o']}) != len(ids):
            errs.append('many: повторяющиеся варианты')
        if len(c['a']) == len(ids):
            errs.append('many: верны все варианты')
    elif k == 'match':
        L = [x['id'] for x in c['o']['left']]
        R = {x['id'] for x in c['o']['right']}
        if set(c['a']) != set(L) or not set(c['a'].values()) <= R:
            errs.append('match: соответствие не покрывает левый столбец')
    else:
        errs.append(f'неизвестный вид карточки {k}')
    g = c.get('gen', {})
    # независимый пересчёт
    try:
        want = m['solve'](g.get('p', {}))
        if not same_answer(c, want):
            errs.append(f'пересчёт: в карточке {c["a"]!r}, solve даёт {want!r}')
    except Exception as ex:  # noqa: BLE001
        errs.append(f'solve упал: {type(ex).__name__}: {ex}')
    for lhs, rhs, kl, kr in g.get('eqs', []):
        try:
            if not check_balance(lhs, rhs, kl, kr):
                errs.append(f'не уравнено: {eq_str(lhs, rhs, kl, kr)}')
            elif balance_ok_min(lhs, rhs, kl, kr) is False:
                errs.append(f'коэффициенты не наименьшие: {eq_str(lhs, rhs, kl, kr)}')
        except Exception as ex:  # noqa: BLE001
            errs.append(f'уравнение не разобрать: {lhs}→{rhs}: {ex}')
    if 'nuc' in g:
        (a0, z0), (a1, z1) = g['nuc'][0], g['nuc'][1]
        if (a0, z0) != (a1, z1):
            errs.append(f'ядерная реакция: A/Z не сохраняются {g["nuc"]}')
    if k == 'num' and 'wrong' in g and len([w for w in g['wrong'] if w != c['a']]) < 2:
        errs.append('мало дистракторов')
    if re.search(r'\b(None|nan|inf)\b|\{[a-z_]+\}', card_text(c) + c.get('e', '')):
        errs.append('в тексте осталась заготовка/None')
    return errs


def balance_ok_min(lhs, rhs, kl, kr):
    g = 0
    for v in list(kl) + list(kr):
        g = math.gcd(g, v)
    return g == 1


# ================================================================= сходство с текстами ФИПИ (шинглы по 5 слов)

WORD = re.compile(r'[a-zа-яё]+|\d+(?:[.,]\d+)?', re.I)


def words(t):
    t = t.lower().replace('ё', 'е')
    return ['#' if w[0].isdigit() else w for w in WORD.findall(t)]


def shingles(t, k=5):
    w = words(t)
    return {' '.join(w[i:i + k]) for i in range(len(w) - k + 1)}


class Similarity:
    """Индекс шинглов локальных текстов ФИПИ. score(text) = доля шинглов карточки, найденных в ОДНОМ тексте ФИПИ
    (максимум по текстам). Числа заменены на '#', чтобы «те же слова, другие числа» считались совпадением."""

    def __init__(self, texts, k=5):
        self.k = k
        self.index = {}
        self.n = 0
        for i, t in enumerate(texts):
            for s in shingles(t, k):
                self.index.setdefault(s, []).append(i)
            self.n += 1

    def score(self, text):
        sh = shingles(text, self.k)
        if not sh:
            return 0.0, None
        cnt = Counter()
        for s in sh:
            for i in self.index.get(s, ()):
                cnt[i] += 1
        if not cnt:
            return 0.0, None
        i, v = cnt.most_common(1)[0]
        return v / len(sh), i
