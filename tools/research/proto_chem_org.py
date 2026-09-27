"""ЕГЭ-химия (КИМ 2027), органика: прототипы заданий 10–16, 25, 32, 33.

Данные — tools/research/chemdb_org.py (вещества со SMILES, реакции, факты без уравнений, «не реагирует», полимеры).
Генераторы строят условие по базе; solve(p) пересчитывает ответ другим путём: по SMILES (брутто-формула, σ/π-связи,
гибридизация), заново ищет реакции по реагентам, пересчитывает формулу по числам условия.
Формат и стиль — по демоверсии 2027 и открытому банку (сверка — в отчёте исполнителя).
"""
import re
from collections import Counter, defaultdict
from fractions import Fraction as Fr

import chemdb_org as D
from pc_core import (AR, Retry, balance, eq_str, fmt, match_opts, molar, opts, parse_formula, pcard, pretty, proto,
                     recipe)

# ================================================================= данные и отображение

SUB = {s['f']: s for s in D.SUBSTANCES}
ORG = [f for f, s in SUB.items() if s.get('org')]
RX = []
for _r in D.REACTIONS:
    _kl, _kr = balance(_r['lhs'], _r['rhs'])
    RX.append(dict(_r, k=(_kl, _kr)))
FACTS = D.FACTS
SMI = D.SMILES
LET = 'АБВГД'


def brutto(f):
    return tuple(sorted(parse_formula(f).items()))


def smi_brutto(f):
    """Брутто-формула по SMILES (независимый путь)."""
    return tuple(sorted(D.smiles_info(SMI[f])['atoms'].items()))


def nm(f, rng=None, triv=0.4):
    s = SUB[f]
    if rng is not None and s.get('trivial') and rng.random() < triv:
        return s['trivial'][0]
    return s['name']


def vw(f):
    return SUB[f].get('view') or pretty(f)


def pf(f):
    return pretty(f)


_COND = [(r'\bt\b', 't°'), (r'\bhv\b', 'hν'), (r'Hg2\+', 'Hg²⁺'), (r'Pb2\+', 'Pb²⁺'), (r'Mn2\+', 'Mn²⁺'),
         (r'\bH\+', 'H⁺'), (r'\bOH-', 'OH⁻'), (r'Cr2O3', 'Cr₂O₃'), (r'Al2O3', 'Al₂O₃'), (r'H3PO4', 'H₃PO₄'),
         (r'H2SO4', 'H₂SO₄'), (r'FeBr3', 'FeBr₃'), (r'FeCl3', 'FeCl₃'), (r'AlCl3', 'AlCl₃'), (r'HgCl2', 'HgCl₂'),
         (r'PdCl2', 'PdCl₂'), (r'CuCl2', 'CuCl₂'), (r'NH4Cl', 'NH₄Cl'), (r'NH3', 'NH₃'), (r'ZnO', 'ZnO'),
         (r'Zn\(CH3COO\)2', 'Zn(CH₃COO)₂'), (r'HNO3', 'HNO₃'), (r'KOH', 'KOH'), (r'H2', 'H₂')]


def cond_ru(c):
    for a, b in _COND:
        c = re.sub(a, b, c)
    return c


def rx_scheme(r, sub_disp=None, show_rhs=False, names=False, rng=None):
    """Схема реакции для условия: «A + реагент (условия) →». sub_disp — как показать субстрат."""
    a = sub_disp or (nm(r['lhs'][0], rng) if names else eqv(r['lhs'][0]))
    rg = reagent_label(r, names=names)
    left = a + (f' + {rg}' if rg else '')
    c = scheme_cond(r)
    arrow = f' —({c})→' if c else ' →'
    return left + arrow


def reagent_label(r, names=False):
    """Реагент(ы) схемы: всё, кроме субстрата, в записи ЕГЭ (KMnO₄ + H₂SO₄, [Ag(NH₃)₂]OH …)."""
    rest = [x for x in r['lhs'][1:] if x != 'H2O' or r.get('rk') == 'H2O' or len(r['lhs']) == 2]
    if 'KMnO4' in r['lhs']:
        return {'кисл.': 'KMnO₄ + H₂SO₄', 'щел.': 'KMnO₄ + KOH'}.get(r.get('medium'), 'KMnO₄ + H₂O')
    if 'K2Cr2O7' in r['lhs']:
        return 'K₂Cr₂O₇ + H₂SO₄'
    out = []
    for x in rest:
        if x == 'Ag(NH3)2OH':
            out.append('[Ag(NH₃)₂]OH')
        elif x == 'Cu(NH3)2Cl':
            out.append('[Cu(NH₃)₂]Cl')
        elif names and x in SUB and SUB[x].get('org'):
            out.append(nm(x))
        else:
            out.append(eqv(x))
    return ' + '.join(out)


def scheme_cond(r):
    c = r.get('cond', '')
    if 'KMnO4' in r['lhs'] and r.get('medium') == 'нейтр.' and '0' in c:
        c = '0 °C'
    elif 'KMnO4' in r['lhs']:
        c = 't' if r.get('medium') != 'кисл.' and 't' in c else ''
    c = c.replace('бромная вода', 'водн. р-р').replace('водн. р-р, t', 'водн., t').replace('спирт. р-р, t', 'спирт., t')
    return cond_ru(c)


def eqv(f):
    s = SUB.get(f)
    if s and s.get('org') and s['hom'] in ('моносахариды', 'дисахариды'):
        return pretty(''.join(x + (str(n) if n > 1 else '') for x, n in sorted(parse_formula(f).items(),
                                                                                key=lambda t: 'CHON'.find(t[0]))))
    if s and s.get('org'):
        v = s.get('view') or pretty(f)
        if '(цикл)' in v or '(1,' in v or '(орто' in v or '(пара' in v or '(мета' in v:
            return s['name']
        return v
    if f == 'Ag(NH3)2OH':
        return '[Ag(NH₃)₂]OH'
    if f == 'Cu(NH3)2Cl':
        return '[Cu(NH₃)₂]Cl'
    return pretty(f)


POLY_UNIT = {'C6H10O5': '(C₆H₁₀O₅)ₙ', 'C6H7O2(OH)3': '[C₆H₇O₂(OH)₃]ₙ', 'C6H7O2(ONO2)3': '[C₆H₇O₂(ONO₂)₃]ₙ',
             'C6H7O2(OCOCH3)3': '[C₆H₇O₂(OCOCH₃)₃]ₙ'}


def rx_eq(r):
    kl, kr = r['k']
    poly = any(x in POLY_UNIT for x in r['lhs'] + r['rhs'])

    def term(x, k):
        if poly and x in POLY_UNIT:
            return (f'{k}' if k > 1 else '') + POLY_UNIT[x]
        if poly:
            return (f'{k}n' if k > 1 else 'n') + eqv(x)
        return (f'{k}' if k > 1 else '') + eqv(x)
    side = lambda ss, ks: ' + '.join(term(x, k) for x, k in zip(ss, ks))
    return f"{side(r['lhs'], kl)} → {side(r['rhs'], kr)}"


def eqt(r):
    return (list(r['lhs']), list(r['rhs']), list(r['k'][0]), list(r['k'][1]))


def rkey(r):
    """Ключ «схемы»: реагенты + условия (однозначно определяют продукт в базе)."""
    return (tuple(r['lhs']), r.get('cond', ''), r.get('medium', ''))


def by_scheme():
    d = defaultdict(set)
    for r in RX:
        d[rkey(r)].add(r['rhs'][0])
    return d


SCHEME = by_scheme()


def pick_distinct(rng, items, n, key=lambda x: x):
    items = list(items)
    rng.shuffle(items)
    out, seen = [], set()
    for x in items:
        k = key(x)
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
        if len(out) == n:
            return out
    raise Retry


def match_card(pid, rng, q, left, right, ans_idx, e, p, eqs=None, lids=None):
    """left — тексты; right — тексты; ans_idx[i] — индекс правильного right для left[i]."""
    o = match_opts(left, right, lids=lids or LET)
    a = {o['left'][i]['id']: str(ans_idx[i] + 1) for i in range(len(left))}
    return pcard(pid, q, a, e, k='match', o=o, p=p, eqs=eqs)


def many_card(pid, q, items, good, e, p, eqs=None):
    o = opts(items)
    a = [str(i + 1) for i in sorted(good)]
    return pcard(pid, q, a, e, k='many', o=o, p=p, eqs=eqs)


def fid(fmt_, level, time_min, scale, trap, kes, score, style=None):
    return dict(answer_format=fmt_, style=style or 'формулировка в стиле КИМ 2027: «Установите соответствие…», '
                                                   '«Из предложенного перечня выберите…»; вещества — названия и формулы '
                                                   'школьной органики, как в открытом банке',
                level=level, time_min=time_min, scale=scale, trap=trap, kes=kes, score=score)


KIM_TAIL = ': к каждой позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой.'
KIM_TABLE = 'Запишите в таблицу выбранные цифры под соответствующими буквами.'


def mq(between, lh, rh):
    """Формулировка задания на соответствие, как в КИМ."""
    return f'Установите соответствие между {between}{KIM_TAIL}\n{KIM_TABLE}'


def q_many(n, obj, what):
    """«Из предложенного перечня выберите два вещества, …» (как в КИМ)."""
    return f'Из предложенного перечня выберите {n} {obj}, {what}.\nЗапишите номера выбранных ответов.'


MATCH3 = 'три позиции (А–В), четыре варианта (1–4); ответ — три цифры, цифры могут повторяться'
MATCH4 = 'четыре позиции (А–Г), шесть вариантов (1–6); ответ — четыре цифры, цифры могут повторяться'
SC1 = '1 балл (полное совпадение)'
SC2 = '2 балла; 1 балл при одной ошибке в позиции'

# ================================================================= задание 10: классификация и номенклатура

FINE = {  # гомологический ряд → класс (детальный уровень, как во 2-м столбце заданий)
    'алканы': 'алканы', 'циклоалканы': 'циклоалканы', 'алкены': 'алкены', 'алкадиены': 'алкадиены', 'алкины': 'алкины',
    'арены': 'арены', 'арены (с непредельной боковой цепью)': 'арены',
    'предельные одноатомные спирты': 'одноатомные спирты', 'циклические спирты': 'одноатомные спирты',
    'ароматические спирты': 'одноатомные спирты', 'многоатомные спирты': 'многоатомные спирты', 'фенолы': 'фенолы',
    'простые эфиры': 'простые эфиры', 'предельные альдегиды': 'альдегиды', 'ароматические альдегиды': 'альдегиды',
    'непредельные альдегиды': 'альдегиды', 'кетоны': 'кетоны', 'циклические кетоны': 'кетоны',
    'ароматические кетоны': 'кетоны', 'предельные одноосновные карбоновые кислоты': 'карбоновые кислоты',
    'высшие карбоновые кислоты': 'карбоновые кислоты', 'непредельные карбоновые кислоты': 'карбоновые кислоты',
    'ароматические карбоновые кислоты': 'карбоновые кислоты', 'двухосновные карбоновые кислоты': 'карбоновые кислоты',
    'сложные эфиры': 'сложные эфиры', 'предельные амины': 'амины', 'ароматические амины': 'амины', 'диамины': 'амины',
    'аминокислоты': 'аминокислоты', 'дипептиды': 'пептиды', 'моносахариды': 'углеводы', 'дисахариды': 'углеводы',
    'полисахариды': 'углеводы', 'нитроалканы': 'нитросоединения', 'нитроарены': 'нитросоединения',
    'галогеналканы': 'галогенпроизводные', 'галогенарены': 'галогенпроизводные',
}
SUGAR = {'моносахариды': 'моносахариды', 'дисахариды': 'дисахариды', 'полисахариды': 'полисахариды'}
COARSE = {  # укрупнённо (как «углеводороды / кислородсодержащие / азотсодержащие»)
    'углеводород': 'углеводороды', 'спирт': 'кислородсодержащие соединения', 'фенол': 'кислородсодержащие соединения',
    'альдегид': 'кислородсодержащие соединения', 'кетон': 'кислородсодержащие соединения',
    'карбоновая кислота': 'кислородсодержащие соединения', 'сложный эфир': 'кислородсодержащие соединения',
    'простой эфир': 'кислородсодержащие соединения', 'углевод': 'кислородсодержащие соединения',
    'амин': 'азотсодержащие соединения', 'аминокислота': 'азотсодержащие соединения',
    'нитросоединение': 'азотсодержащие соединения', 'пептид': 'азотсодержащие соединения',
    'галогенпроизводное': 'галогенсодержащие соединения',
}
_POOL10_SKIP = {'C6H5CH(OH)CH3', 'C6H5CH(OH)CH2OH', 'C6H10(OH)2', 'C6H5CHClCH3', 'CH2BrCBr(CH3)CHBrCH2Br',
                'C17H33Br2COOH', 'CH3CH(NH3Cl)COOH', 'C6H6Cl6'}


def cls_fine(f):
    s = SUB[f]
    if not s.get('org'):
        return None
    if 'N' in parse_formula(f) and s['cls'] == 'сложный эфир':
        return None
    return FINE.get(s['hom'])


def cls_sugar(f):
    return SUGAR.get(SUB[f]['hom'])


def cls_coarse(f):
    s = SUB[f]
    if s['hom'] in ('жиры',) or s['cls'] not in COARSE:
        return None
    if s['cls'] == 'сложный эфир' and 'N' in parse_formula(f):
        return None
    return COARSE[s['cls']]


LEVELS = {'fine': cls_fine, 'sugar': cls_sugar, 'coarse': cls_coarse}


def pool10(level):
    fn = LEVELS[level]
    return [f for f in ORG if f not in _POOL10_SKIP and fn(f) and SUB[f]['cls'] not in ('соль амина', 'алкоголят')]


def _solve_cls(p):
    """Пересчёт: класс каждого вещества заново по полю hom/cls и тексту варианта."""
    fn = LEVELS[p['level']]
    return {LET[i]: str(p['right'].index(fn(f)) + 1) for i, f in enumerate(p['left'])}


def _gen_cls(pid, rng, show):
    level = rng.choice(['fine'] * 6 + ['sugar', 'coarse'])
    fn = LEVELS[level]
    pool = pool10(level)
    labels = sorted({fn(f) for f in pool})
    if len(labels) < 4:
        raise Retry
    right = rng.sample(labels, 4)
    cand = [f for f in pool if fn(f) in right]
    left = pick_distinct(rng, cand, 3, key=lambda f: f)
    if len({fn(f) for f in left}) < 2:
        raise Retry
    if show == 'name':
        ltxt = [nm(f, rng) for f in left]
        q = mq('названием органического вещества и классом (группой) соединений, к которому это вещество относится',
               'НАЗВАНИЕ ВЕЩЕСТВА', 'КЛАСС/ГРУППА ОРГАНИЧЕСКИХ СОЕДИНЕНИЙ')
    else:
        ltxt = [vw(f) for f in left]
        q = mq('формулой органического вещества и классом (группой) соединений, к которому это вещество относится',
               'ФОРМУЛА ВЕЩЕСТВА', 'КЛАСС/ГРУППА ОРГАНИЧЕСКИХ СОЕДИНЕНИЙ')
    ans = [right.index(fn(f)) for f in left]
    e = '; '.join(f'{t} — {fn(f)}' + (f' ({vw(f)})' if show == 'name' else f' ({nm(f)})') for t, f in zip(ltxt, left))
    return match_card(pid, rng, q, ltxt, right, ans, e + '.', {'level': level, 'left': left, 'right': right})


KES10 = ['3.3']


@proto('ch-ege-10-name-class', 'ЕГЭ', 10, 'Название вещества → класс (группа) органических соединений',
       invariant='по названию (систематическому или тривиальному) определить класс/группу соединения',
       varies='вещества (алканы … углеводы, амины, пептиды), уровень классификации (класс / моно-ди-поли / '
              'укрупнённые группы), набор классов во 2-м столбце',
       answer_rule='каждому веществу — его класс; цифры могут повторяться', mistakes=[
           'стирол отнесён к алкенам, а не к аренам', 'глицерин — к одноатомным спиртам', 'фенол — к спиртам',
           'тривиальное название не узнано (изопрен, толуол, кумол)'],
       solve=_solve_cls, kind='dict', kes=KES10,
       fidelity=fid(MATCH3, 'Б', 3, 'вещества из банка №10: изооктан, изопрен, стирол, дезоксирибоза, глицилаланин',
                    'тривиальные названия, пограничные классы (стирол, глицерин, фенол)', KES10, SC1))
def g10_name_class(rng):
    return _gen_cls('ch-ege-10-name-class', rng, 'name')


@proto('ch-ege-10-formula-class', 'ЕГЭ', 10, 'Формула вещества → класс (группа) органических соединений',
       invariant='по структурной (полуструктурной) формуле распознать функциональную группу и класс',
       varies='вещества, уровень классификации, набор классов',
       answer_rule='каждой формуле — класс по функциональной группе', mistakes=[
           'HCOOCH₃ принят за кислоту (это сложный эфир)', 'простой эфир спутан со сложным',
           'альдегид спутан с кетоном'],
       solve=_solve_cls, kind='dict', kes=KES10,
       fidelity=fid(MATCH3, 'Б', 3, 'формулы вида HCOOCH₃, CH₃OC₃H₇, C₃H₇COOH, CH₃CH(CH₃)CHO как в банке',
                    'сложный/простой эфир, альдегид/кетон, фенол/спирт', KES10, SC1))
def g10_formula_class(rng):
    return _gen_cls('ch-ege-10-formula-class', rng, 'formula')


# -------- общие формулы гомологических рядов
GEN_CLASSES = {  # класс → множество hom, чьи представители дают одну общую формулу
    'алканы': ['алканы'], 'алкены': ['алкены'], 'циклоалканы': ['циклоалканы'], 'алкины': ['алкины'],
    'алкадиены': ['алкадиены'], 'гомологи бензола': ['арены'], 'предельные одноатомные спирты':
        ['предельные одноатомные спирты'], 'простые эфиры': ['простые эфиры'],
    'предельные альдегиды': ['предельные альдегиды'], 'кетоны': ['кетоны'],
    'предельные одноосновные карбоновые кислоты': ['предельные одноосновные карбоновые кислоты'],
    'сложные эфиры': ['сложные эфиры'], 'фенолы': ['фенолы'], 'предельные амины': ['предельные амины'],
    'предельные двухатомные спирты': ['многоатомные спирты'],
}
GEN_SKIP = {'C6H5CH(OH)CH2OH', 'C3H5(OH)3', 'C6H10(OH)2', 'C6H8(OH)6', 'C6H2Br3OH', 'C6H2(NO2)3OH', 'C6H4(OH)2',
            'CH2CHCOOCH3', 'CH2C(CH3)COOCH3', 'CH3COOCHCH2', 'CH3COOC6H5', 'C6H5COOCH3', 'C6H5CH2CH2CH3x'}


def genf_of(f):
    """Общая формула по брутто-формуле: CnH2n+k[Oa][Nb]."""
    a = parse_formula(f)
    if set(a) - {'C', 'H', 'O', 'N'}:
        return None
    k = a['H'] - 2 * a['C']
    s = 'CₙH₂ₙ' + ('' if k == 0 else (f'+{k}' if k > 0 else f'−{-k}'))
    if a.get('O'):
        s += 'O' + ('' if a['O'] == 1 else str(a['O']).translate(str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')))
    if a.get('N'):
        s += 'N' + ('' if a['N'] == 1 else str(a['N']).translate(str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')))
    return s


def members(cls):
    homs = GEN_CLASSES[cls]
    out = [f for f in ORG if SUB[f]['hom'] in homs and f not in GEN_SKIP]
    if cls == 'предельные двухатомные спирты':
        out = [f for f in out if parse_formula(f).get('O') == 2]
    if cls == 'гомологи бензола':
        out = [f for f in out if f != 'C10H8']
    if cls == 'сложные эфиры':
        out = [f for f in out if 'N' not in parse_formula(f) and genf_of(f) == 'CₙH₂ₙO₂']
    if cls == 'фенолы':
        out = [f for f in out if parse_formula(f).get('O') == 1]
    if cls == 'кетоны':
        out = [f for f in out if SUB[f]['hom'] == 'кетоны']
    return out


def class_genf(cls):
    fs = {genf_of(f) for f in members(cls)}
    return fs.pop() if len(fs) == 1 else None


def _solve_genf_cls(p):
    # по SMILES членов каждого класса во 2-м столбце — их общая формула
    def gf_smiles(cls):
        vals = set()
        for f in members(cls):
            a = dict(smi_brutto(f)) if f in SMI else parse_formula(f)
            k = a['H'] - 2 * a['C']
            vals.add((k, a.get('O', 0), a.get('N', 0)))
        return vals.pop()
    out = {}
    for i, g in enumerate(p['left_k']):
        j = [n for n, c in enumerate(p['right']) if gf_smiles(c) == tuple(g)]
        out[LET[i]] = str(j[0] + 1)
    return out


def _kon(s):
    a = s.replace('CₙH₂ₙ', '')
    m = re.match(r'([+−]\d+)?(O[₀-₉]*)?(N[₀-₉]*)?$', a)
    k = int(m.group(1).replace('−', '-')) if m.group(1) else 0
    sub = lambda t: int(t[1:].translate(str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')) or 1) if t else 0
    return (k, sub(m.group(2)), sub(m.group(3)))


@proto('ch-ege-10-genf-class', 'ЕГЭ', 10, 'Общая формула → класс (гомологический ряд)',
       invariant='сопоставить общую формулу CₙH₂ₙ₊ₖOₐNᵦ с классом соединений',
       varies='три общие формулы из 13 рядов, четыре класса во 2-м столбце (один лишний, без двусмысленных пар)',
       answer_rule='подставить представителя класса и сверить число атомов H относительно 2n',
       mistakes=['алкены и циклоалканы (CₙH₂ₙ) — межклассовые изомеры, нужно смотреть, какой из них в списке',
                 'для аренов взято CₙH₂ₙ₋₂', 'амины — CₙH₂ₙ₊₁N вместо CₙH₂ₙ₊₃N'],
       solve=_solve_genf_cls, kind='dict', kes=KES10,
       fidelity=fid(MATCH3, 'Б', 3, 'общие формулы CₙH₂ₙ₋₆O, CₙH₂ₙ₊₂O₂, CₙH₂ₙ₋₂, CₙH₂ₙ₊₃N — как в банке',
                    'одна общая формула у двух классов (межклассовая изомерия)', KES10, SC1))
def g10_genf_class(rng):
    classes = [c for c in GEN_CLASSES if class_genf(c)]
    right = rng.sample(classes, 4)
    gfs = [class_genf(c) for c in right]
    if len(set(gfs)) < 4:
        raise Retry  # в правом столбце не должно быть двух классов с одной общей формулой
    idx = rng.sample(range(4), 3)
    left = [gfs[i] for i in idx]
    q = mq('общей формулой и классом (гомологическим рядом) органических соединений, которому она отвечает', 'ОБЩАЯ ФОРМУЛА',
           'КЛАСС/ГРУППА ОРГАНИЧЕСКИХ СОЕДИНЕНИЙ')
    ex = {c: rng.choice(members(c)) for c in right}
    e = '; '.join(f'{gfs[i]} — {right[i]} (например, {nm(ex[right[i]])}, {pretty(_bru_str(ex[right[i]]))})' for i in idx)
    return match_card('ch-ege-10-genf-class', rng, q, left, right, idx, e + '.',
                      {'left_k': [list(_kon(g)) for g in left], 'right': right})


def _bru_str(f):
    a = parse_formula(f)
    order = ['C', 'H'] + sorted(x for x in a if x not in 'CH')
    return ''.join(x + (str(a[x]) if a[x] > 1 else '') for x in order if x in a)


def _solve_genf_sub(p):
    def gk(f):
        a = dict(smi_brutto(f))
        return (a['H'] - 2 * a['C'], a.get('O', 0), a.get('N', 0))
    out = {}
    if p['dir'] == 'gf→sub':
        for i, g in enumerate(p['left_k']):
            j = [n for n, f in enumerate(p['right']) if gk(f) == tuple(g)]
            out[LET[i]] = str(j[0] + 1)
    else:
        for i, f in enumerate(p['left']):
            j = [n for n, g in enumerate(p['right_k']) if gk(f) == tuple(g)]
            out[LET[i]] = str(j[0] + 1)
    return out


GF_OK = {'CₙH₂ₙ+2', 'CₙH₂ₙ', 'CₙH₂ₙ−2', 'CₙH₂ₙ−6', 'CₙH₂ₙ−8', 'CₙH₂ₙ+2O', 'CₙH₂ₙO', 'CₙH₂ₙO₂', 'CₙH₂ₙ−6O',
         'CₙH₂ₙ+2O₂', 'CₙH₂ₙ+2O₃', 'CₙH₂ₙ+3N', 'CₙH₂ₙ−5N', 'CₙH₂ₙ+1NO₂', 'CₙH₂ₙ−8O', 'CₙH₂ₙ−8O₂', 'CₙH₂ₙ−2O₄'}
GF_POOL = [f for f in ORG if f in SMI and genf_of(f) in GF_OK and f not in _POOL10_SKIP
           and SUB[f]['cls'] not in ('соль карбоновой кислоты', 'алкоголят', 'соль амина', 'фенолят', 'ацетиленид')
           and SUB[f]['hom'] not in ('жиры', 'моносахариды', 'дисахариды', 'полисахариды')
           and len(parse_formula(f)) <= 4 and parse_formula(f).get('C', 0) <= 10]


@proto('ch-ege-10-genf-substance', 'ЕГЭ', 10, 'Общая формула ряда ↔ вещество этого ряда',
       invariant='найти вещество, чья молекулярная формула подходит под общую формулу (или наоборот)',
       varies='направление (формула → вещество / вещество → формула), вещества любых классов, общие формулы',
       answer_rule='записать молекулярную формулу вещества, выразить число H через n и сверить',
       mistakes=['стирол (CₙH₂ₙ₋₈) спутан с толуолом (CₙH₂ₙ₋₆)', 'циклоалкан отнесён к CₙH₂ₙ₊₂',
                 'в аминокислоте не учтён атом азота'],
       solve=_solve_genf_sub, kind='dict', kes=KES10,
       fidelity=fid(MATCH3, 'Б', 3, 'пары вида CₙH₂ₙ₋₈ — стирол, CₙH₂ₙ₋₆ — толуол, CₙH₂ₙ₋₅N — анилин (банк, демо 2027)',
                    'межклассовые изомеры и близкие ряды (−6/−8, +2/+3)', KES10, SC1))
def g10_genf_sub(rng):
    by = defaultdict(list)
    for f in GF_POOL:
        by[genf_of(f)].append(f)
    gfs = [g for g in by if len(g) < 18]
    four = rng.sample(gfs, 4)
    subs = [rng.choice(by[g]) for g in four]
    idx = rng.sample(range(4), 3)
    if rng.random() < 0.6:
        left = [four[i] for i in idx]
        right = [nm(f, rng) for f in subs]
        q = mq('общей формулой гомологического ряда и веществом, которое входит в этот ряд', 'ОБЩАЯ ФОРМУЛА',
               'НАЗВАНИЕ ВЕЩЕСТВА')
        p = {'dir': 'gf→sub', 'left_k': [list(_kon(g)) for g in left], 'right': subs}
        ans = idx
        e = '; '.join(f'{four[i]} — {nm(subs[i])} ({pretty(_bru_str(subs[i]))})' for i in idx)
    else:
        left_f = [subs[i] for i in idx]
        left = [nm(f, rng) for f in left_f]
        right = four
        q = mq('органическим соединением и общей формулой того гомологического ряда, в который оно входит',
               'НАЗВАНИЕ ВЕЩЕСТВА', 'ОБЩАЯ ФОРМУЛА')
        p = {'dir': 'sub→gf', 'left': left_f, 'right_k': [list(_kon(g)) for g in right]}
        ans = idx
        e = '; '.join(f'{nm(subs[i])} — {pretty(_bru_str(subs[i]))} → {four[i]}' for i in idx)
    return match_card('ch-ege-10-genf-substance', rng, q, left, right, ans, e + '.', p)


def _solve_name_formula(p):
    out = {}
    for i, f in enumerate(p['left']):
        out[LET[i]] = str(p['right'].index(f) + 1)
    return out


NF_POOL = [f for f in ORG if f not in _POOL10_SKIP and SUB[f]['cls'] not in ('ацетиленид',) and SUB[f].get('view')]


@proto('ch-ege-10-name-formula', 'ЕГЭ', 10, 'Название вещества ↔ формула',
       invariant='по систематическому или тривиальному названию выбрать формулу (или наоборот)',
       varies='направление, вещества (близкие по составу: изомеры, гомологи, соседи по классу)',
       answer_rule='разобрать название (корень — число C, суффикс — класс, приставки — заместители)',
       mistakes=['ацетальдегид спутан с ацетоном', 'пропанол-1 и пропанол-2 перепутаны', 'кумол спутан с пропилбензолом'],
       solve=_solve_name_formula, kind='dict', kes=KES10,
       fidelity=fid(MATCH3, 'Б', 3, 'тройки вида ацетальдегид/ацетон/формальдегид; глицин/нитробензол/изопропиламин',
                    'в вариантах — изомеры и гомологи правильных веществ', KES10, SC1))
def g10_name_formula(rng):
    f0 = rng.choice(NF_POOL)
    hom = SUB[f0]['hom']
    near = [f for f in NF_POOL if SUB[f]['hom'] == hom or brutto(f) == brutto(f0)]
    if len(near) < 4:
        near += rng.sample(NF_POOL, 6)
    four = pick_distinct(rng, near, 4, key=lambda f: f)
    idx = rng.sample(range(4), 3)
    left_f = [four[i] for i in idx]
    if rng.random() < 0.5:
        left = [nm(f, rng) for f in left_f]
        right = [vw(f) for f in four]
        q = mq('названием органического вещества и его формулой', 'НАЗВАНИЕ ВЕЩЕСТВА', 'ФОРМУЛА ВЕЩЕСТВА')
    else:
        left = [vw(f) for f in left_f]
        right = [nm(f, rng) for f in four]
        q = mq('формулой органического вещества и его названием', 'ФОРМУЛА ВЕЩЕСТВА', 'НАЗВАНИЕ ВЕЩЕСТВА')
    if len(set(right)) < 4 or len(set(left)) < 3:
        raise Retry
    e = '; '.join(f'{nm(f)} — {vw(f)}' for f in left_f)
    return match_card('ch-ege-10-name-formula', rng, q, left, right, idx, e + '.', {'left': left_f, 'right': four})


def _solve_brutto_class(p):
    def gk_cls(cls):
        return {tuple(sorted(parse_formula(f).items())) for f in members(cls)}
    out = {}
    for i, b in enumerate(p['left_b']):
        a = dict(b)
        kk = (a['H'] - 2 * a['C'], a.get('O', 0), a.get('N', 0))
        j = []
        for n, c in enumerate(p['right']):
            vals = set()
            for f in members(c):
                x = parse_formula(f)
                vals.add((x['H'] - 2 * x['C'], x.get('O', 0), x.get('N', 0)))
            if kk in vals:
                j.append(n)
        out[LET[i]] = str(j[0] + 1)
    return out


@proto('ch-ege-10-brutto-class', 'ЕГЭ', 10, 'Молекулярная формула (брутто) → класс соединений',
       invariant='по молекулярной формуле CₓHᵧOz определить возможный класс (через общую формулу рядов)',
       varies='число атомов углерода (2–8), класс; во 2-м столбце нет двух классов с одинаковой общей формулой',
       answer_rule='вычислить k = H − 2C и число O/N, сравнить с общими формулами классов из списка',
       mistakes=['C₄H₈O₂ — не только кислота, но и сложный эфир: смотреть, какой класс есть в списке',
                 'CₙH₂ₙO отнесён к спиртам'],
       solve=_solve_brutto_class, kind='dict', kes=KES10,
       fidelity=fid(MATCH3, 'Б', 3, 'брутто-формулы C₄H₈O₂, C₆H₁₂O₆, C₄H₁₀O₃ и т. п. (банк)',
                    'межклассовые изомеры с одинаковой общей формулой', KES10, SC1))
def g10_brutto_class(rng):
    classes = [c for c in GEN_CLASSES if class_genf(c)]
    right = rng.sample(classes, 4)
    if len({class_genf(c) for c in right}) < 4:
        raise Retry
    idx = rng.sample(range(4), 3)
    left_b, left = [], []
    for i in idx:
        m = members(right[i])
        g = _kon(class_genf(right[i]))
        mn = min(parse_formula(f)['C'] for f in m)
        n = rng.randint(max(mn, 2), max(mn, 2) + 5)
        b = {'C': n, 'H': 2 * n + g[0]}
        if g[1]:
            b['O'] = g[1]
        if g[2]:
            b['N'] = g[2]
        left_b.append(sorted(b.items()))
        left.append(pretty(''.join(x + (str(b[x]) if b[x] > 1 else '') for x in ['C', 'H', 'O', 'N'] if x in b)))
    if len(set(left)) < 3:
        raise Retry
    q = mq('молекулярной формулой органического вещества и классом соединений, к которому это вещество может '
       'относиться', 'МОЛЕКУЛЯРНАЯ ФОРМУЛА', 'КЛАСС/ГРУППА СОЕДИНЕНИЙ')
    e = '; '.join(f'{left[j]} отвечает общей формуле {class_genf(right[i])} — {right[i]}' for j, i in enumerate(idx))
    return match_card('ch-ege-10-brutto-class', rng, q, left, right, idx, e + '.', {'left_b': left_b, 'right': right})


# ================================================================= задание 11: строение, изомерия, гомологи

KES11 = ['3.1', '3.2']
MANY2 = 'пять вариантов, ответ — две цифры (порядок не важен)'
SC11 = '1 балл (полное совпадение)'
MOL = [f for f in ORG if f in SMI and '[' not in SMI[f] and 'N(=O)=O' not in SMI[f] and 'O=N' not in SMI[f]
       and SUB[f]['hom'] not in ('жиры',) and parse_formula(f).get('C', 0) <= 10 and f not in _POOL10_SKIP]


def info(f):
    return D.smiles_info(SMI[f])


def _q_two(rng, what):
    return q_many('два', 'вещества', what)


# -------- изомеры
def _solve_isomers(p):
    bs = [smi_brutto(f) for f in p['items']]
    if p['mode'] == 'of':
        t = smi_brutto(p['target'])
        return [str(i + 1) for i, b in enumerate(bs) if b == t]
    if p['mode'] == 'interclass':
        good = [i for i in range(5) for j in range(5) if i != j and bs[i] == bs[j]
                and cls_fine(p['items'][i]) != cls_fine(p['items'][j])]
        return [str(i + 1) for i in sorted(set(good))]
    good = [i for i in range(5) for j in range(5) if i != j and bs[i] == bs[j]]
    return [str(i + 1) for i in sorted(set(good))]


ISO_POOL = [f for f in MOL if cls_fine(f) and SUB[f]['cls'] not in ('галогенпроизводное',)]


def _iso_groups():
    g = defaultdict(list)
    for f in ISO_POOL:
        g[brutto(f)].append(f)
    return {k: v for k, v in g.items() if len(v) >= 2}


ISO = _iso_groups()


@proto('ch-ege-11-isomers', 'ЕГЭ', 11, 'Изомеры: пара изомеров, изомеры данного вещества, межклассовые',
       invariant='изомеры — одинаковая молекулярная формула, разное строение; сравнить брутто-формулы',
       varies='режим (пара / изомеры вещества X / межклассовые), вещества 3–8 атомов C разных классов',
       answer_rule='записать молекулярные формулы всех веществ и найти совпадающие (для межклассовых — ещё и разные классы)',
       mistakes=['гомологи приняты за изомеры', 'цис- и транс-формы одного вещества — не межклассовые изомеры',
                 'не учтено, что циклоалканы изомерны алкенам, а сложные эфиры — кислотам'],
       solve=_solve_isomers, kind='dict', kes=KES11,
       fidelity=fid(MANY2, 'Б', 3, 'изомеры этилформиата, пропанола-1, бутаналя; изопрен/циклопентен (демо 2027)',
                    'гомологи и вещества того же класса среди вариантов', KES11, SC11))
def g11_isomers(rng):
    mode = rng.choice(['pair', 'of', 'interclass'])
    keys = list(ISO)
    b = rng.choice(keys)
    grp = ISO[b]
    if mode == 'of':
        if len(grp) < 3:
            raise Retry
        target, a1, a2 = rng.sample(grp, 3)
        good = [a1, a2]
    elif mode == 'interclass':
        pairs = [(x, y) for x in grp for y in grp if x < y and cls_fine(x) != cls_fine(y)]
        if not pairs:
            raise Retry
        good = list(rng.choice(pairs))
        target = None
    else:
        good = rng.sample(grp, 2)
        target = None
    others = [f for f in ISO_POOL if brutto(f) != b]
    # отвлекающие: те же классы / близкий состав, но без второй пары изомеров
    near = [f for f in others if cls_fine(f) in {cls_fine(g) for g in good} or
            abs(parse_formula(f)['C'] - parse_formula(good[0])['C']) <= 1]
    for _ in range(30):
        dis = rng.sample(near if len(near) >= 3 else others, 3)
        if len({brutto(x) for x in dis}) == 3:
            break
    else:
        raise Retry
    if mode == 'interclass' and rng.random() < 0.5:
        # ловушка: изомер того же класса вместо одного отвлекающего — нельзя (даст вторую пару); берём гомолог
        pass
    items = good + dis
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    N = dict(zip(items, names))
    if len(set(names)) < 5:
        raise Retry
    if mode == 'pair':
        what = rng.choice(['которые изомерны друг другу', 'которые имеют одинаковый состав, но разное строение'])
    elif mode == 'of':
        what = rng.choice([f'которые изомерны веществу «{nm(target)}»', f'каждое из которых — изомер {gen(nm(target))}'])
    else:
        what = rng.choice(['которые принадлежат к разным классам, но изомерны друг другу',
                           'которые образуют пару межклассовых изомеров'])
    q = _q_two(rng, what)
    gi = [items.index(g) for g in good]
    e = ('Изомеры имеют одинаковую молекулярную формулу: ' + ', '.join(f'{N.get(f, nm(f))} — {pretty(_bru_str(f))}' for f in items)
         + (f'; у вещества «{nm(target)}» — {pretty(_bru_str(target))}' if target else '') + '.')
    if mode == 'interclass':
        e += f' Классы: {cls_fine(good[0])} и {cls_fine(good[1])}.'
    return many_card('ch-ege-11-isomers', q, names, gi, e, {'mode': mode, 'items': items, 'target': target})


def homologs(a, b):
    """Гомологи: один класс (ряд), брутто различаются на k·CH₂ (k ≥ 1)."""
    if SUB[a]['hom'] != SUB[b]['hom'] or not cls_fine(a):
        return False
    x, y = parse_formula(a), parse_formula(b)
    dc = y['C'] - x['C']
    if dc == 0:
        return False
    return all(y.get(e, 0) - x.get(e, 0) == {'C': dc, 'H': 2 * dc}.get(e, 0) for e in set(x) | set(y))


def _solve_homologs(p):
    def hom_s(a, b):
        if SUB[a]['hom'] != SUB[b]['hom']:
            return False
        x, y = dict(smi_brutto(a)), dict(smi_brutto(b))
        dc = y['C'] - x['C']
        return dc != 0 and all(y.get(e, 0) - x.get(e, 0) == {'C': dc, 'H': 2 * dc}.get(e, 0) for e in set(x) | set(y))
    it = p['items']
    if p['target']:
        return [str(i + 1) for i, f in enumerate(it) if hom_s(p['target'], f)]
    return [str(i + 1) for i in range(5) if any(hom_s(it[i], it[j]) for j in range(5) if j != i)]


HOM_POOL = [f for f in MOL if cls_fine(f) and SUB[f]['hom'] in
            ('алканы', 'циклоалканы', 'алкены', 'алкины', 'алкадиены', 'арены', 'предельные одноатомные спирты',
             'предельные альдегиды', 'кетоны', 'предельные одноосновные карбоновые кислоты', 'сложные эфиры',
             'предельные амины', 'простые эфиры', 'аминокислоты', 'многоатомные спирты', 'фенолы')]


@proto('ch-ege-11-homologs', 'ЕГЭ', 11, 'Гомологи: пара гомологов, гомологи данного вещества',
       invariant='гомологи — один класс (одна функциональная группа, тот же тип связей), разница на CH₂',
       varies='класс, вещества; режим (пара / гомологи вещества X); в отвлекающих — изомеры и соседние классы',
       answer_rule='проверить класс и разницу состава на (CH₂)ₙ',
       mistakes=['изомер принят за гомолог', 'метилацетат и метилформиат — гомологи, а кислота и эфир — нет',
                 'бензол и стирол не гомологи'],
       solve=_solve_homologs, kind='dict', kes=KES11,
       fidelity=fid(MANY2, 'Б', 3, 'гомологи уксусной кислоты, н-гексана, бензола (банк №11)',
                    'изомеры и вещества соседних классов в отвлекающих', KES11, SC11))
def g11_homologs(rng):
    f0 = rng.choice(HOM_POOL)
    hs = [f for f in HOM_POOL if homologs(f0, f)]
    target = f0 if rng.random() < 0.5 else None
    if target:
        if len(hs) < 2:
            raise Retry
        good = rng.sample(hs, 2)
        if homologs(good[0], good[1]) is False and False:
            pass
    else:
        if not hs:
            raise Retry
        good = [f0, rng.choice(hs)]
    rest = [f for f in HOM_POOL if f not in good and f != target]
    # ловушки: изомеры и близкие вещества, но без лишних гомологов
    near = [f for f in rest if brutto(f) in {brutto(g) for g in good} or
            abs(parse_formula(f)['C'] - parse_formula(good[0])['C']) <= 1]
    for _ in range(40):
        dis = rng.sample(near if len(near) >= 3 else rest, 3)
        items = good + dis
        if target:
            if sum(homologs(target, f) for f in items) == 2 and target not in items:
                break
        elif sum(any(homologs(a, b) for b in items if b != a) for a in items) == 2:
            break
    else:
        raise Retry
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    N = dict(zip(items, names))
    if len(set(names)) < 5:
        raise Retry
    what = (rng.choice([f'которые гомологичны веществу «{nm(target)}»', f'каждое из которых — гомолог '
                                                                        f'{gen(nm(target))}']) if target else
            rng.choice(['которые гомологичны друг другу', 'которые входят в один и тот же гомологический ряд',
                        'которые образуют пару гомологов']))
    q = _q_two(rng, what)
    e = ('Гомологи принадлежат к одному классу и отличаются на группу CH₂: '
         + ', '.join(f'{N.get(f, nm(f))} ({pretty(_bru_str(f))})' for f in good) + (f'; исходное — {nm(target)} '
                                                                            f'({pretty(_bru_str(target))})' if target else '')
         + '.')
    return many_card('ch-ege-11-homologs', q, names, [items.index(g) for g in good], e,
                     {'items': items, 'target': target})


# -------- гибридизация, σ/π
HYB_Q = {
    'all_sp3': ('у которых каждый атом углерода sp³-гибридизован', lambda h, c: h['sp3'] == c),
    'all_sp2': ('у которых каждый атом углерода sp²-гибридизован', lambda h, c: h['sp2'] == c),
    'one_sp2': ('у которых ровно один атом углерода sp²-гибридизован', lambda h, c: h['sp2'] == 1),
    'one_sp3': ('у которых ровно один атом углерода sp³-гибридизован', lambda h, c: h['sp3'] == 1),
    'sp2_sp3': ('у которых есть и sp²-, и sp³-гибридизованные атомы углерода',
                lambda h, c: h['sp2'] > 0 and h['sp3'] > 0),
    'has_sp': ('у которых есть хотя бы один sp-гибридизованный атом углерода', lambda h, c: h['sp'] > 0),
    'no_sp2': ('у которых нет ни одного sp²-гибридизованного атома углерода', lambda h, c: h['sp2'] == 0),
}
HYB_POOL = [f for f in MOL if parse_formula(f)['C'] <= 8 and SUB[f]['hom'] not in ('дипептиды',)]


def _solve_hyb(p):
    pred = HYB_Q[p['mode']][1]
    out = []
    for i, f in enumerate(p['items']):
        x = D.smiles_info(SMI[f])
        c = x['atoms']['C']
        if pred(x['hyb'], c):
            out.append(str(i + 1))
    return out


@proto('ch-ege-11-hybrid', 'ЕГЭ', 11, 'Гибридизация атомов углерода (sp³, sp², sp)',
       invariant='тип гибридизации C: четыре σ-связи — sp³, двойная связь (или ароматическое кольцо) — sp², '
                 'тройная или две двойные — sp',
       varies='условие (все sp³ / все sp² / один sp² / и sp², и sp³ / есть sp / нет sp²), вещества разных классов',
       answer_rule='для каждого атома C определить кратность связей; ровно два вещества удовлетворяют условию',
       mistakes=['атом C карбоксильной/карбонильной группы считают sp³', 'в толуоле не все C — sp²',
                 'в аллене центральный атом — sp'],
       solve=_solve_hyb, kind='dict', kes=KES11,
       fidelity=fid(MANY2, 'Б', 3, 'формулировки «все атомы углерода в sp²», «только один атом в sp³» (банк №11)',
                    'C=O и ароматическое кольцо как источник sp²; метильная группа в аренах', KES11, SC11))
def g11_hybrid(rng):
    mode = rng.choice(list(HYB_Q))
    text, pred = HYB_Q[mode]
    ok = [f for f in HYB_POOL if pred(info(f)['hyb'], info(f)['atoms']['C'])]
    bad = [f for f in HYB_POOL if f not in ok]
    if len(ok) < 2:
        raise Retry
    good = rng.sample(ok, 2)
    dis = rng.sample(bad, 3)
    items = good + dis
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    N = dict(zip(items, names))
    if len(set(names)) < 5:
        raise Retry
    q = _q_two(rng, text)

    def d(f):
        h = info(f)['hyb']
        return f'{N.get(f, nm(f))} ({vw(f)}): ' + ', '.join(f'{k} — {h[k]}' for k in ('sp3', 'sp2', 'sp') if h[k]).replace(
            'sp3', 'sp³').replace('sp2', 'sp²')
    e = 'Число атомов C по типу гибридизации. ' + '; '.join(d(f) for f in items) + '.'
    return many_card('ch-ege-11-hybrid', q, names, [items.index(g) for g in good], e, {'mode': mode, 'items': items})


SIGPI_Q = {
    'only_sigma': ('молекулы которых не содержат ни одной π-связи', lambda x, n: x['pi'] == 0),
    'pi1': ('молекула каждого из которых содержит ровно одну π-связь', lambda x, n: x['pi'] == 1),
    'pi2': ('молекула каждого из которых содержит ровно две π-связи', lambda x, n: x['pi'] == 2),
    'pi3': ('молекула каждого из которых содержит ровно три π-связи', lambda x, n: x['pi'] == 3),
    'sigma_n': ('молекула каждого из которых содержит ровно {n} σ-связей', lambda x, n: x['sigma'] == n),
}
SIG_POOL = [f for f in MOL if parse_formula(f)['C'] <= 6 and SUB[f]['hom'] not in ('дипептиды', 'аминокислоты')
            and f not in ('C10H8',)]


def _solve_sigpi(p):
    pred = SIGPI_Q[p['mode']][1]
    return [str(i + 1) for i, f in enumerate(p['items']) if pred(D.smiles_info(SMI[f]), p.get('n'))]


def gen(name):
    """Родительный падеж названия вещества (для «изомерами этилформиата», «гомологами бензола»)."""
    words = name.split(' ')
    out = []
    for k, w in enumerate(words):
        m = re.match(r'^(.*?)(-[\d,]+)?$', w)
        base, tail = m.group(1), m.group(2) or ''
        if base.endswith('ая'):
            out.append(base[:-2] + 'ой' + tail)
            continue
        if re.search(r'(ый|ий|ой)$', base) and k < len(words) - 1:
            out.append(base[:-2] + 'ого' + tail)
            continue
        if base.endswith('а'):
            base = base[:-1] + 'ы'
        elif base.endswith('аль'):
            base = base[:-1] + 'я'
        elif re.search(r'[бвгджзклмнпрстфхцчшщ]$', base):
            base = base + 'а'
        else:
            return f'вещества «{name}»'
        return ' '.join(out + [base + tail] + words[k + 1:])
    return f'вещества «{name}»'


def _sig_word(n):
    return 'σ-связи' if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else 'σ-связей'


@proto('ch-ege-11-sigma-pi', 'ЕГЭ', 11, 'Число σ- и π-связей в молекуле',
       invariant='одинарная связь — σ; двойная — σ + π; тройная — σ + 2π; ароматическое кольцо — 3π; связи C–H — σ',
       varies='условие (только σ / одна, две, три π-связи / ровно N σ-связей), вещества',
       answer_rule='нарисовать структурную формулу, посчитать связи с учётом C–H и O–H',
       mistakes=['не посчитаны σ-связи C–H', 'в тройной связи засчитана одна π-связь', 'в бензоле «забыты» π-связи'],
       solve=_solve_sigpi, kind='dict', kes=KES11,
       fidelity=fid(MANY2, 'Б', 3, '«только три σ-связи» (ацетилен, формальдегид), «две π-связи» — банк №11',
                    'связи C–H тоже σ; кратные связи C=O', KES11, SC11))
def g11_sigma_pi(rng):
    mode = rng.choice(list(SIGPI_Q))
    n = None
    if mode == 'sigma_n':
        vals = Counter(info(f)['sigma'] for f in SIG_POOL)
        n = rng.choice([v for v, c in vals.items() if c >= 2 and v <= 14])
    text, pred = SIGPI_Q[mode]
    ok = [f for f in SIG_POOL if pred(info(f), n)]
    bad = [f for f in SIG_POOL if f not in ok]
    good = rng.sample(ok, 2)
    dis = rng.sample(bad, 3)
    items = good + dis
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    N = dict(zip(items, names))
    if len(set(names)) < 5:
        raise Retry
    t = text.format(n=n).replace('σ-связей', _sig_word(n) if n else 'σ-связей')
    q = _q_two(rng, t)
    e = 'Подсчёт связей: ' + '; '.join(f'{N.get(f, nm(f))} ({vw(f)}) — σ: {info(f)["sigma"]}, π: {fmt(info(f)["pi"])}'
                                      for f in items) + '.'
    return many_card('ch-ege-11-sigma-pi', q, names, [items.index(g) for g in good], e,
                     {'mode': mode, 'items': items, 'n': n})


# -------- цис-транс-изомерия
def _branch(adj, a, frm):
    """Каноническая строка ветви молекулы от атома a (пришли из frm) — для сравнения заместителей."""
    ch = sorted(_branch(adj, b, a) for b in adj[a] if b != frm)
    return 'X(' + ','.join(ch) + ')'


def cis_trans(f):
    """Есть ли у ациклического вещества C=C с двумя разными заместителями на каждом атоме (по SMILES)."""
    smi = SMI[f]
    if any(ch.isdigit() for ch in smi) or '#' in smi:
        return False
    # разбор SMILES на граф тяжёлых атомов
    tok = re.findall(r'\[[^\]]+\]|Br|Cl|[BCNOSPFI]|[=#\(\)]', smi)
    atoms, bonds, stack, prev, order = [], [], [], None, 1
    for t in tok:
        if t == '(':
            stack.append(prev)
        elif t == ')':
            prev = stack.pop()
        elif t in '=#':
            order = 2 if t == '=' else 3
        else:
            atoms.append(t)
            i = len(atoms) - 1
            if prev is not None:
                bonds.append((prev, i, order))
            prev, order = i, 1
    adj = defaultdict(list)
    for a, b, o in bonds:
        adj[a].append(b)
        adj[b].append(a)

    def label(a, frm):
        return atoms[a] + _branch_l(a, frm)

    def _branch_l(a, frm):
        return '(' + ','.join(sorted(atoms[b] + _branch_l(b, a) for b in adj[a] if b != frm)) + ')'
    for a, b, o in bonds:
        if o != 2 or atoms[a] != 'C' or atoms[b] != 'C':
            continue
        ok = True
        for x, y in ((a, b), (b, a)):
            subs = [label(z, x) for z in adj[x] if z != y]
            # второй заместитель — атом H (если у атома одна тяжёлая связь, кроме двойной)
            if len(subs) == 0:
                ok = False
            elif len(subs) == 1:
                pass  # заместитель и H — разные
            elif subs[0] == subs[1]:
                ok = False
            if any(o2 == 2 for p_, q_, o2 in bonds if (p_ == x or q_ == x) and {p_, q_} != {a, b}):
                ok = False  # кумулированная система
        if ok:
            return True
    return False


CT_POOL = [f for f in MOL if SUB[f]['hom'] in ('алкены', 'алкадиены', 'галогеналкены', 'непредельные карбоновые кислоты',
                                               'алкины', 'алканы', 'непредельные спирты', 'непредельные альдегиды')
           and parse_formula(f)['C'] <= 7]
CT_KNOWN = {'CH3CHCHCH3': True, 'CH2CHCH2CH3': False, '(CH3)2CCHCH3': False, 'CH3CHCHCH2CH3': True, 'C2H4': False,
            'CH2CHCH3': False, 'CHBrCHBr': True, 'CH2BrCHCHCH2Br': True, 'CH2CHCHCHCH3': True, 'CH2C(CH3)2': False,
            'CH3CCCH3': False, 'CH2CHCOOH': False}


def _solve_ct(p):
    return [str(i + 1) for i, f in enumerate(p['items']) if cis_trans(f)]


@proto('ch-ege-11-cis-trans', 'ЕГЭ', 11, 'Цис-транс-изомерия (геометрическая)',
       invariant='цис-транс-изомерия возможна, если при каждом атоме C двойной связи два разных заместителя',
       varies='алкены, диены, галогеналкены, отвлекающие — алкены с двумя одинаковыми заместителями, алкины, алканы',
       answer_rule='проверить оба атома C=C: у каждого заместители должны различаться',
       mistakes=['бутен-1 отнесён к цис-транс-изомерам (у C1 два атома H)', '2-метилбутен-2: у C2 две метильные группы',
                 'для алкинов цис-транс-изомерии нет'],
       solve=_solve_ct, kind='dict', kes=KES11,
       fidelity=fid(MANY2, 'Б', 3, 'бутен-2, 4-метилпентен-2 против бутена-1, 2-метилбутена-2, бутина-2 (банк №11)',
                    'одинаковые заместители у одного атома C=C', KES11, SC11))
def g11_cis_trans(rng):
    ok = [f for f in CT_POOL if cis_trans(f)]
    bad = [f for f in CT_POOL if not cis_trans(f)]
    good = rng.sample(ok, 2)
    dis = rng.sample(bad, 3)
    items = good + dis
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    N = dict(zip(items, names))
    what = rng.choice(['которые способны существовать в виде цис- и транс-форм',
                       'у которых возможна геометрическая (цис-транс-) изомерия'])
    q = _q_two(rng, what)
    e = ('Цис-транс-изомерия возможна, если у каждого атома C двойной связи разные заместители: '
         + ', '.join(f'{N.get(f, nm(f))} ({vw(f)})' for f in good) + '. У остальных ('
         + ', '.join(N.get(f, nm(f)) for f in dis) + ') это условие не выполняется или нет связи C=C.')
    return many_card('ch-ege-11-cis-trans', q, names, [items.index(g) for g in good], e, {'items': items})


# -------- функциональные группы, ориентанты, «нет изомеров»
FG = {
    'carbonyl': ('в состав молекул которых входит карбонильная группа', ['альдегиды', 'кетоны'],
                 ['одноатомные спирты', 'многоатомные спирты', 'простые эфиры', 'алкены', 'алканы', 'арены', 'фенолы',
                  'амины']),
    'hydroxyl': ('в состав молекул которых входит одна или несколько групп –OH', ['одноатомные спирты', 'многоатомные спирты', 'фенолы'],
                 ['альдегиды', 'кетоны', 'простые эфиры', 'алкены', 'арены', 'амины', 'алканы']),
    'amino': ('в состав молекул которых входит аминогруппа', ['амины', 'аминокислоты'],
              ['нитросоединения', 'одноатомные спирты', 'альдегиды', 'карбоновые кислоты', 'алкены']),
    'carboxyl': ('в состав молекул которых входит карбоксильная группа', ['карбоновые кислоты', 'аминокислоты'],
                 ['альдегиды', 'кетоны', 'сложные эфиры', 'одноатомные спирты', 'простые эфиры', 'фенолы']),
}


def _fg_has(f, mode):
    s = SMI[f]
    if mode == 'carbonyl':
        return bool(re.search(r'C=O|C\(=O\)|O=C', s)) and not re.search(r'C\(=O\)O|OC=O|O=CO|C\(=O\)\[|O=C\(O', s)
    if mode == 'hydroxyl':
        return bool(re.search(r'(^|[C\)c1-9])O($|[\)])|^O[Cc]|\(O\)', s)) and 'C(=O)O' not in s and 'OC=O' not in s
    if mode == 'amino':
        return 'N' in s and 'N(=O)' not in s and 'O=N' not in s
    if mode == 'carboxyl':
        return bool(re.search(r'C\(=O\)O$|^OC\(=O\)|^OC=O$|C\(=O\)O\)|OC\(=O\)c', s)) and '[' not in s
    return False


FG_POOL = [f for f in MOL if cls_fine(f) and parse_formula(f)['C'] <= 7]


def _solve_fg(p):
    return [str(i + 1) for i, f in enumerate(p['items']) if cls_fine(f) in FG[p['mode']][1]]


@proto('ch-ege-11-func-groups', 'ЕГЭ', 11, 'Функциональные группы (карбонильная, гидроксильная, амино-, карбоксильная)',
       invariant='распознать функциональную группу по названию/классу вещества',
       varies='группа, вещества; отвлекающие — классы без этой группы (простые эфиры, нитросоединения и т. п.)',
       answer_rule='выписать функциональные группы всех пяти веществ',
       mistakes=['простой эфир принят за спирт', 'нитрогруппа принята за аминогруппу', 'кетон считают без C=O'],
       solve=_solve_fg, kind='dict', kes=KES11,
       fidelity=fid(MANY2, 'Б', 3, '«содержат карбонильную группу», «гидроксильные группы» (банк №11)',
                    'кислоты и сложные эфиры в «карбонильную» не включаем, чтобы ответ был однозначным', KES11, SC11))
def g11_func_groups(rng):
    mode = rng.choice(list(FG))
    text, pos, neg = FG[mode]
    ok = [f for f in FG_POOL if cls_fine(f) in pos]
    bad = [f for f in FG_POOL if cls_fine(f) in neg]
    good = rng.sample(ok, 2)
    dis = rng.sample(bad, 3)
    items = good + dis
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    N = dict(zip(items, names))
    if len(set(names)) < 5:
        raise Retry
    q = _q_two(rng, text)
    e = '; '.join(f'{N.get(f, nm(f))} ({vw(f)}) — {cls_fine(f)}' for f in items) + '.'
    return many_card('ch-ege-11-func-groups', q, names, [items.index(g) for g in good], e, {'mode': mode, 'items': items})


ORIENT = {  # заместитель в бензольном кольце → род ориентанта
    'C6H5CH3': 1, 'C6H5OH': 1, 'C6H5NH2': 1, 'C6H5Cl': 1, 'C6H5Br': 1, 'C6H5C2H5': 1, 'C6H5CH(CH3)2': 1,
    'C6H5NO2': 2, 'C6H5COOH': 2, 'C6H5CHO': 2, 'C6H5COCH3': 2, 'C6H5COOCH3': 2,
}


def _solve_orient(p):
    # мета-ориентант — заместитель с кратной связью у атома, соединённого с кольцом (по SMILES: C(=O) или N(=O))
    def meta(f):
        s = SMI[f]
        return bool(re.search(r'O=C\(|O=N|C\(=O\)c|^O=Cc|N\(=O\)=O', s)) or s.startswith('O=C')
    want = 2 if p['kind'] == 2 else 1
    return [str(i + 1) for i, f in enumerate(p['items']) if (meta(f) and want == 2) or (not meta(f) and want == 1)]


@proto('ch-ege-11-orientation', 'ЕГЭ', 11, 'Ориентанты I и II рода в бензольном кольце',
       invariant='заместители без кратных связей у первого атома (–CH₃, –OH, –NH₂, галогены) — орто-/пара-ориентанты; '
                 '–NO₂, –COOH, –CHO, –COR — мета-ориентанты',
       varies='вопрос (мета- / орто-, пара-), производные бензола',
       answer_rule='определить заместитель и его род; ровно два вещества подходят',
       mistakes=['галогены отнесены к мета-ориентантам', 'альдегидная группа принята за ориентант I рода'],
       solve=_solve_orient, kind='dict', kes=KES11,
       fidelity=fid(MANY2, 'Б', 3, 'кодификатор 3.2 «ориентационные эффекты заместителей»; производные бензола из банка',
                    'галогены — дезактивирующие, но орто-/пара-ориентанты', KES11, SC11))
def g11_orientation(rng):
    kind = rng.choice([1, 2])
    ok = [f for f, v in ORIENT.items() if v == kind]
    bad = [f for f, v in ORIENT.items() if v != kind]
    good = rng.sample(ok, 2)
    dis = rng.sample(bad, 3)
    items = good + dis
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    N = dict(zip(items, names))
    what = ('в молекулах которых заместитель является ориентантом II рода (мета-ориентантом)' if kind == 2
            else 'в молекулах которых заместитель является ориентантом I рода (орто-, пара-ориентантом)')
    q = _q_two(rng, what)
    e = ('Ориентанты I рода (орто-, пара-): –CH₃, –C₂H₅, –OH, –NH₂, –Cl, –Br; II рода (мета-): –NO₂, –COOH, –CHO, '
         '–COCH₃, –COOCH₃. Здесь: ' + ', '.join(f'{N.get(f, nm(f))} — {"мета" if ORIENT[f] == 2 else "орто-, пара"}' for f in items)
         + '.')
    return many_card('ch-ege-11-orientation', q, names, [items.index(g) for g in good], e, {'kind': kind, 'items': items})


NO_ISO = ['CH4', 'C2H6', 'C3H8', 'C2H4', 'C2H2', 'CH3OH', 'HCHO', 'CH3Cl', 'CH2Cl2', 'CHCl3', 'CCl4', 'C2H5Cl',
          'C2H5Br', 'CH3NH2', 'CH3Br', 'HCOOH']
HAS_ISO = ['CH3CH2CH2CH3', 'CH2CHCH3', 'C2H5OH', 'CH3COOH', 'CH3COCH3', 'CH3CH2CH2OH', 'CH3OCH3',
           'CH2CHCH2CH3', 'CHCCH3', 'C2H5NH2', 'CH3CH2CHO', 'CH3CH2COOH', 'CH3CHClCH3', 'CH2ClCH2Cl']


def _solve_noiso(p):
    # вещество не имеет изомеров, если в базе нет другого вещества того же состава и оно из «коротких» (≤ 1 варианта
    # строения для данного брутто): проверяем по списку проверенных фактов и по совпадению брутто в базе
    out = []
    for i, f in enumerate(p['items']):
        same = [g for g in ORG if g != f and brutto(g) == brutto(f) and SUB[g]['cls'] != 'соль амина']
        if f in NO_ISO and not same:
            out.append(str(i + 1))
    return out


@proto('ch-ege-11-no-isomers', 'ЕГЭ', 11, 'Вещества, не имеющие изомеров',
       invariant='изомеров нет, если для данной молекулярной формулы возможна только одна структура',
       varies='вещества C1–C3 (метан, этан, пропан, этен, этин, метанол, метаналь, галогенметаны …) и отвлекающие',
       answer_rule='попробовать построить другую структуру того же состава (цепь, положение группы, другой класс)',
       mistakes=['у пропена есть изомер — циклопропан', 'у этанола есть изомер — диметиловый эфир',
                 'у уксусной кислоты — метилформиат'],
       solve=_solve_noiso, kind='dict', kes=KES11,
       fidelity=fid(MANY2, 'Б', 3, '«не имеют изомеров»: пропен, н-бутан, ацетилен, пропаналь, формальдегид (банк)',
                    'межклассовые изомеры у простых веществ (пропен — циклопропан, этанол — диметиловый эфир)', KES11,
                    SC11))
def g11_no_isomers(rng):
    good = rng.sample(NO_ISO, 2)
    dis = rng.sample(HAS_ISO, 3)
    items = good + dis
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    N = dict(zip(items, names))
    q = _q_two(rng, 'для которых нельзя составить ни одного изомера')

    def iso(f):
        g = sorted((x for x in ORG if x != f and brutto(x) == brutto(f)), key=lambda x: len(nm(x)))
        return nm(g[0]) if g else None
    e = ('Изомеров нет у: ' + ', '.join(N.get(f, nm(f)) for f in good) + '. Изомеры есть у: '
         + ', '.join(f'{N.get(f, nm(f))} (например, {iso(f)})' for f in dis) + '.')
    return many_card('ch-ege-11-no-isomers', q, names, [items.index(g) for g in good], e, {'items': items})


# ================================================================= задания 12, 13: свойства («выберите все / два»)

POS = D.positives()
NEG = set(D.NOT_REACT)
RKN = {  # ключ реагента → как он назван в перечне
    'O2': ['кислород'], 'H2': ['водород (кат.)', 'водород'], 'Br2aq': ['бромная вода', 'бром (водн.)'],
    'HCl': ['хлороводород'], 'HBr': ['бромоводород'], 'KMnO4': ['перманганат калия (р-р)',
                                                                                 'раствор перманганата калия'],
    'Na': ['натрий', 'металлический натрий'], 'K': ['калий'], 'NaOH': ['гидроксид натрия (р-р)',
                                                                      'раствор гидроксида натрия'],
    'KOH': ['гидроксид калия (р-р)'], 'NaHCO3': ['гидрокарбонат натрия', 'питьевая сода (NaHCO₃)'],
    'Cu(OH)2': ['гидроксид меди(II)', 'свежеосаждённый Cu(OH)₂'],
    'AgNH3': ['аммиачный раствор оксида серебра', 'аммиачный раствор Ag₂O'], 'HNO3': ['азотная кислота'],
    'H2O': ['вода'], 'CuO': ['оксид меди(II)'], 'C2H5OH': ['этанол'], 'CH3OH': ['метанол'],
    'NaCl': ['хлорид натрия'], 'Na2SO4': ['сульфат натрия'], 'KNO3': ['нитрат калия'], 'CH4': ['метан'],
    'Cu': ['медь'], 'N2': ['азот'], 'KCl': ['хлорид калия'], 'Ag': ['серебро'], 'I2': ['иод (р-р)'],
    'H2SO4': ['серная кислота'], 'CH3Cl': ['хлорметан'], 'C2H5Cl': ['хлорэтан'], 'Mg': ['магний'],
}


def known(f, rk):
    if (f, rk) in POS:
        return True
    if (f, rk) in NEG:
        return False
    return None


def react_db(f, rk):
    """Независимый пересчёт: есть ли в базе реакция/факт субстрата f с реагентом rk (перебор заново)."""
    for r in D.REACTIONS:
        if r['lhs'][0] == f and r.get('rk') == rk:
            return True
    for r in D.FACTS:
        if r['lhs'][0] == f and r.get('rk') == rk and not r.get('neg'):
            return True
    return False


def _rk_text(rng, rk):
    return rng.choice(RKN[rk])


POOL12 = [f for f in ORG if SUB[f]['cls'] in ('углеводород', 'спирт', 'фенол', 'альдегид', 'кетон', 'карбоновая кислота',
                                              'сложный эфир', 'простой эфир') and SUB[f]['hom'] != 'жиры'
          and parse_formula(f)['C'] <= 8 and f not in _POOL10_SKIP]
RK12 = ['O2', 'H2', 'Br2aq', 'HCl', 'HBr', 'KMnO4', 'Na', 'NaOH', 'NaHCO3', 'Cu(OH)2', 'AgNH3', 'HNO3', 'H2O', 'CuO', 'K',
        'KOH']
KES12 = ['3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13']
ALL12 = 'пять вариантов, ответ — все верные (от двух до четырёх цифр), порядок не важен'


def _q_all(rng, what):
    return q_many('все', 'вещества', what)


def _solve_rk_common(p):
    out = []
    for i, rk in enumerate(p['rks']):
        if all(react_db(f, rk) for f in p['subs']):
            out.append(str(i + 1))
    return out


def _solve_rk_not(p):
    return [str(i + 1) for i, rk in enumerate(p['rks']) if not react_db(p['subs'][0], rk)]


def _pick_rks(rng, subs, pool, lo=2, hi=4, want=True, n=5):
    ok = [rk for rk in pool if all(known(f, rk) is not None for f in subs)]
    if len(ok) < n:
        raise Retry
    for _ in range(30):
        rks = rng.sample(ok, n)
        good = [i for i, rk in enumerate(rks) if all(known(f, rk) for f in subs) == want] if want else \
            [i for i, rk in enumerate(rks) if known(subs[0], rk) is False]
        if lo <= len(good) <= hi:
            return rks, good
    raise Retry


def _rk_expl(subs, rks, N):
    parts = []
    for rk in rks:
        seg = []
        for f in subs:
            r = next((x for x in RX if x['lhs'][0] == f and x.get('rk') == rk), None)
            if r:
                seg.append(f'{N.get(f, nm(f))}: {rx_eq(r)}')
            elif known(f, rk):
                fa = next((x for x in FACTS if x['lhs'][0] == f and x.get('rk') == rk), None)
                seg.append(f'{N.get(f, nm(f))}: реагирует' + (f' ({fa["sign"]})' if fa and fa.get('sign') else ''))
            else:
                seg.append(f'{N.get(f, nm(f))}: не реагирует')
        parts.append(f'{RKN[rk][0]} — ' + '; '.join(seg))
    return '. '.join(parts) + '.'


@proto('ch-ege-12-common-reagent', 'ЕГЭ', 12, 'Реагенты, с которыми реагируют оба вещества (углеводороды, O-содержащие)',
       invariant='для каждого реагента решить, реагирует ли с ним каждое из двух веществ; выбрать общие',
       varies='пара веществ разных классов (алкан/алкен/арен/спирт/фенол/альдегид/кислота/эфир), пять реагентов',
       answer_rule='реагент подходит, только если реагирует и первое, и второе вещество',
       mistakes=['алканы не обесцвечивают бромную воду и KMnO₄', 'фенол не реагирует с NaHCO₃',
                 'спирты не реагируют с раствором щёлочи', 'забыто горение (кислород — общий реагент)'],
       solve=_solve_rk_common, kind='dict', kes=KES12,
       fidelity=fid(ALL12, 'П', 3, 'пары пропан/глицерин (демо 2027), этан/этиленгликоль, фенол/стеариновая кислота',
                    'реагент подходит только одному из веществ', KES12, SC1))
def g12_common(rng):
    a, b = rng.sample(POOL12, 2)
    if cls_fine(a) == cls_fine(b):
        raise Retry
    rks, good = _pick_rks(rng, [a, b], RK12)
    names = [_rk_text(rng, rk) for rk in rks]
    N = {a: nm(a, rng), b: nm(b, rng)}
    q = q_many('все', 'вещества', f'с каждым из которых реагирует и {N[a]}, и {N[b]}')
    e = _rk_expl([a, b], rks, N)
    return many_card('ch-ege-12-common-reagent', q, names, good, e, {'subs': [a, b], 'rks': rks})


@proto('ch-ege-12-reacts-with', 'ЕГЭ', 12, 'С какими реагентами реагирует данное вещество (углеводороды, O-содержащие)',
       invariant='химические свойства одного вещества по его классу и строению',
       varies='вещество (≈ 150 из базы), пять реагентов; вариант «реагирует» и «не реагирует»',
       answer_rule='выбрать все реагенты, с которыми вещество реагирует (или все, с которыми не реагирует)',
       mistakes=['кетоны не дают «серебряного зеркала»', 'третичный спирт не окисляется CuO',
                 'муравьиная кислота восстанавливает Ag₂O (NH₃) и Cu(OH)₂'],
       solve=lambda p: _solve_rk_common(p) if p['want'] else _solve_rk_not(p), kind='dict', kes=KES12,
       fidelity=fid(ALL12, 'П', 3, '«все вещества, с которыми реагирует толуол / метан», «с которыми не реагирует '
                                   'фенол» (банк №12)', 'реагенты, характерные для соседнего класса', KES12, SC1))
def g12_reacts(rng):
    f = rng.choice(POOL12)
    want = rng.random() < 0.7
    rks, good = _pick_rks(rng, [f], RK12, want=want)
    names = [_rk_text(rng, rk) for rk in rks]
    N = {f: nm(f, rng)}
    if want:
        q = q_many('все', 'вещества', f'с которыми вступает в реакцию {N[f]}')
    else:
        q = q_many('все', 'вещества', f'с которыми не вступает в реакцию {N[f]}')
    return many_card('ch-ege-12-reacts-with', q, names, good, _rk_expl([f], rks, N), {'subs': [f], 'rks': rks,
                                                                                         'want': want})


def _solve_subs_rk(p):
    return [str(i + 1) for i, f in enumerate(p['items']) if react_db(f, p['rk'])]


@proto('ch-ege-12-substances-for-reagent', 'ЕГЭ', 12, 'Какие вещества реагируют с данным реагентом',
       invariant='для одного реагента (Na, NaOH, Br₂ (водн.), KMnO₄, Ag₂O/NH₃, Cu(OH)₂, H₂ …) отобрать реагирующие вещества',
       varies='реагент, пять веществ разных классов',
       answer_rule='выбрать все вещества, которые реагируют с этим реагентом',
       mistakes=['бензол не обесцвечивает бромную воду', 'с натрием реагируют спирты, фенол и кислоты, но не эфиры',
                 'с аммиачным раствором Ag₂O реагируют альдегиды, HCOOH и алкины с концевой тройной связью'],
       solve=_solve_subs_rk, kind='dict', kes=KES12,
       fidelity=fid(ALL12, 'П', 3, '«все вещества, которые реагируют с аммиачным раствором оксида серебра / с натрием / '
                                   'с гидроксидом меди(II)» (банк №12)', 'соседние классы с похожими формулами',
                    KES12, SC1))
def g12_subs_for_rk(rng):
    rk = rng.choice(['Br2aq', 'KMnO4', 'Na', 'NaOH', 'NaHCO3', 'Cu(OH)2', 'AgNH3', 'H2', 'HBr', 'H2O', 'CuO'])
    cand = [f for f in POOL12 if known(f, rk) is not None]
    pos = [f for f in cand if known(f, rk)]
    neg = [f for f in cand if not known(f, rk)]
    k = rng.randint(2, 4)
    if len(pos) < k or len(neg) < 5 - k:
        raise Retry
    items = rng.sample(pos, k) + rng.sample(neg, 5 - k)
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    if len(set(names)) < 5:
        raise Retry
    N = dict(zip(items, names))
    r_txt = _rk_text(rng, rk)
    q = q_many('все', 'вещества', f'способные реагировать с реагентом «{r_txt}»')
    good = [i for i, f in enumerate(items) if known(f, rk)]
    e = _rk_expl(items, [rk], N)
    return many_card('ch-ege-12-substances-for-reagent', q, names, good, e, {'items': items, 'rk': rk})


PROD_Q = [  # (ключ реагента, фильтр реакции, описание процесса, признак продукта → текст)
    ('H2O', lambda r: 'гидратации' in r['type'], 'которые в результате гидратации дают'),
    ('H2', lambda r: 'гидрирования' in r['type'], 'которые в результате каталитического гидрирования дают'),
    ('KMnO4', lambda r: r.get('medium') == 'кисл.', 'которые в результате окисления подкисленным раствором KMnO₄ дают'),
    ('KMnO4', lambda r: r.get('medium') == 'нейтр.' and '0' in r.get('cond', ''),
     'которые в результате окисления водным раствором KMnO₄ на холоду дают'),
    ('HBr', lambda r: True, 'которые в результате реакции с бромоводородом дают'),
    ('CuO', lambda r: True, 'которые в результате окисления оксидом меди(II) дают'),
]
PCLASS = {'альдегиды': 'альдегид', 'кетоны': 'кетон', 'одноатомные спирты': 'одноатомный спирт',
          'многоатомные спирты': 'двухатомный спирт', 'карбоновые кислоты': 'карбоновая кислота'}


def _prods(f, rk, flt):
    out = set()
    for r in RX:
        if r['lhs'][0] == f and r.get('rk') == rk and flt(r):
            out.add(r['rhs'][0])
    for r in FACTS:
        if r['lhs'][0] == f and r.get('rk') == rk and flt(r) and r['prod'] and r['prod'][0] in SUB:
            out.update(x for x in r['prod'] if x in SUB and SUB[x].get('org') or x == 'CO2')
    return out


def _solve_prod(p):
    rk, fi = p['rk'], p['fi']
    flt = PROD_Q[fi][1]
    out = []
    for i, f in enumerate(p['items']):
        ps = set()
        for r in D.REACTIONS:
            if r['lhs'][0] == f and r.get('rk') == rk and flt(r):
                ps.add(r['rhs'][0])
        for r in D.FACTS:
            if r['lhs'][0] == f and r.get('rk') == rk and flt(r):
                ps.update(r['prod'])
        if p['target_f'] and p['target_f'] in ps:
            out.append(str(i + 1))
        elif p['target_c'] and any(x in SUB and PCLASS.get(cls_fine(x)) == p['target_c'] for x in ps):
            out.append(str(i + 1))
    return out


@proto('ch-ege-12-product-of-reaction', 'ЕГЭ', 12, 'Вещества, дающие заданный продукт в указанной реакции',
       invariant='мысленно провести реакцию (гидратация, гидрирование, окисление KMnO₄/CuO, + HBr) и сравнить продукт',
       varies='реакция, требуемый продукт (конкретное вещество или класс: кетон, альдегид, спирт, кислота, CO₂), вещества',
       answer_rule='выбрать все вещества, у которых главный продукт совпадает с заданным (правило Марковникова, '
                   'реакция Кучерова, жёсткое окисление по месту кратной связи)',
       mistakes=['гидратация пропина даёт ацетон, а не пропаналь', 'при окислении бутена-1 KMnO₄ (H⁺) '
                                                                  'образуется пропионовая кислота и CO₂',
                 'вторичный спирт окисляется CuO до кетона'],
       solve=_solve_prod, kind='dict', kes=KES12,
       fidelity=fid(ALL12, 'П', 3, '«при гидратации которых образуется кетон», «при окислении KMnO₄ в кислой среде '
                                   'образуется уксусная кислота» (банк №12)', 'изомерные продукты (Марковников, Кучеров)',
                    KES12, SC1))
def g12_product(rng):
    fi = rng.randrange(len(PROD_Q))
    rk, flt, text = PROD_Q[fi]
    cand = [f for f in POOL12 if known(f, rk) is not None]
    prods = {f: _prods(f, rk, flt) for f in cand}
    # цель: либо конкретный продукт, либо класс продукта
    by_c = defaultdict(set)
    by_f = defaultdict(set)
    for f, ps in prods.items():
        for x in ps:
            by_f[x].add(f)
            if x in SUB and PCLASS.get(cls_fine(x)):
                by_c[PCLASS[cls_fine(x)]].add(f)
    use_class = rng.random() < 0.4 and by_c
    if use_class:
        tc = rng.choice(sorted(by_c))
        tf = None
        good_set = by_c[tc]
        target_txt = tc
    else:
        opts_ = [x for x, v in by_f.items() if len(v) >= 2]
        if not opts_:
            raise Retry
        tf = rng.choice(opts_)
        tc = None
        good_set = by_f[tf]
        target_txt = nm(tf) if tf != 'CO2' else 'углекислый газ'
    if len(good_set) < 2:
        raise Retry
    k = rng.randint(2, min(4, len(good_set)))
    bad = [f for f in cand if f not in good_set and f not in ('CO2',)]
    if len(bad) < 5 - k:
        raise Retry
    # отвлекающие — те, что реагируют, но дают другое, и нереагирующие
    items = rng.sample(sorted(good_set), k) + rng.sample(bad, 5 - k)
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    if len(set(names)) < 5:
        raise Retry
    N = dict(zip(items, names))
    q = _q_all(rng, f'{text} {target_txt}')
    good = [items.index(f) for f in items if f in good_set]
    seg = []
    for f in items:
        ps = prods.get(f, set())
        seg.append(f'{N[f]} → ' + (', '.join(nm(x) if x in SUB and x != 'CO2' else 'CO₂' for x in sorted(ps))
                                    if ps else 'не реагирует'))
    return many_card('ch-ege-12-product-of-reaction', q, names, good, '; '.join(seg) + '.',
                     {'items': items, 'rk': rk, 'fi': fi, 'target_f': tf, 'target_c': tc})


SCH_POOL12 = [r for r in RX if r['lhs'][0] in POOL12 and r['rhs'][0] in POOL12 and 'горения' not in r['type'] and len(SCHEME[rkey(r)]) == 1
              and parse_formula(r['rhs'][0]).get('C', 0) <= 8 and SUB[r['rhs'][0]]['cls'] not in ('соль амина',)]


def _solve_schemes(p):
    out = []
    for i, (lhs, cond, med) in enumerate(p['keys']):
        prods = {r['rhs'][0] for r in D.REACTIONS if r['lhs'] == list(lhs) and r.get('cond', '') == cond
                 and r.get('medium', '') == med}
        if p['target'] in prods:
            out.append(str(i + 1))
    return out


@proto('ch-ege-12-schemes-to-product', 'ЕГЭ', 12, 'Схемы реакций, в которых образуется заданное вещество',
       invariant='по схеме (реагенты + условия) определить главный органический продукт и сравнить с заданным',
       varies='заданный продукт (этилен, этанол, пропан, толуол, уксусная кислота, ацетальдегид …), пять схем',
       answer_rule='выбрать все схемы, главный продукт которых — заданное вещество',
       mistakes=['спиртовой и водный раствор щёлочи дают разные продукты', 'гидратация алкина — карбонильное соединение',
                 'реакция Вюрца удваивает углеродный скелет'],
       solve=_solve_schemes, kind='dict', kes=KES12,
       fidelity=fid(ALL12, 'П', 3, '«все реакции, в результате которых образуется этилен / толуол / пропан» (банк №12)',
                    'схемы с тем же субстратом, но другими условиями', KES12, SC1))
def g12_schemes(rng):
    by_p = defaultdict(list)
    for r in SCH_POOL12:
        by_p[r['rhs'][0]].append(r)
    targets = [p for p, v in by_p.items() if len({rkey(r) for r in v}) >= 2]
    tp = rng.choice(targets)
    good_r = pick_distinct(rng, by_p[tp], min(len(by_p[tp]), rng.randint(2, 4)), key=rkey)
    if len(good_r) < 2:
        raise Retry
    subs = {r['lhs'][0] for r in good_r}
    near = [r for r in SCH_POOL12 if r['rhs'][0] != tp and (r['lhs'][0] in subs or
                                                             SUB[r['rhs'][0]]['hom'] == SUB[tp]['hom'])]
    far = [r for r in SCH_POOL12 if r['rhs'][0] != tp]
    bad = pick_distinct(rng, near + rng.sample(far, 10), 5 - len(good_r), key=rkey)
    rs = good_r + bad
    rng.shuffle(rs)
    items = [rx_scheme(r) for r in rs]
    if len(set(items)) < 5:
        raise Retry
    q = q_many('все', 'схемы реакций', f'в результате которых образуется {nm(tp)}')
    good = [i for i, r in enumerate(rs) if r['rhs'][0] == tp]
    e = '; '.join(rx_eq(r) for r in rs) + '.'
    return many_card('ch-ege-12-schemes-to-product', q, items, good, e,
                     {'keys': [list(rkey(r)) for r in rs], 'target': tp}, eqs=[eqt(r) for r in rs])


TYPE_Q = {
    'гидратации': ('способны к реакции гидратации', 'H2O', lambda r: 'гидратации' in r['type']),
    'гидрирования': ('способны к реакции гидрирования', 'H2', lambda r: 'гидрирования' in r['type']),
    'присоединения': ('способны к реакциям присоединения', None, lambda r: 'присоединения' in r['type']),
    'полимеризации': ('способны к реакции полимеризации', None, None),
    'этерификации': ('способны к реакции этерификации', None, lambda r: 'этерификации' in r['type']),
}
_NO_ADD = set(D._ALKANES + D._CYCLO_BIG + D._MONO_ALC + D._SAT_ACIDS + D._ETHERS + ['C2H4(OH)2', 'C3H5(OH)3'])
_NO_POLY = set(D._ALKANES + D._CYCLO_BIG + D._MONO_ALC + D._SAT_ACIDS + D._ETHERS + D._KETONES + D._ARENES_SAT)
_NO_EST = set(D._ALKANES + D._ARENES_SAT + D._ALKENES + D._ETHERS + D._KETONES + D._ALDEH + D._SAT_ESTERS)
MONOMERS = {m for pl in D.POLYMERS if pl['how'] == 'полимеризация' for m in pl['mon']}


def type_known(f, t):
    q, rk, flt = TYPE_Q[t]
    if t == 'полимеризации':
        return True if f in MONOMERS else (False if f in _NO_POLY else None)
    pos = any(r['lhs'][0] == f and flt(r) for r in RX) or (t == 'этерификации' and any(
        r['lhs'][1:2] == [f] and flt(r) for r in RX))
    if pos:
        return True
    if t == 'присоединения' and f in _NO_ADD:
        return False
    if t == 'этерификации' and f in _NO_EST:
        return False
    if rk and (f, rk) in NEG:
        return False
    return None


def _solve_type(p):
    t = p['t']
    out = []
    for i, f in enumerate(p['items']):
        if t == 'полимеризации':
            ok = any(f in pl['mon'] and pl['how'] == 'полимеризация' for pl in D.POLYMERS)
        else:
            word = t
            ok = any(word in r['type'] and (r['lhs'][0] == f or (t == 'этерификации' and f in r['lhs']))
                     for r in D.REACTIONS)
        if ok:
            out.append(str(i + 1))
    return out


@proto('ch-ege-12-reaction-type', 'ЕГЭ', 12, 'Вещества, вступающие в реакцию данного типа',
       invariant='тип реакции (гидратация, гидрирование, присоединение, полимеризация, этерификация) определяется '
                 'наличием кратной связи / функциональной группы',
       varies='тип реакции, пять веществ (углеводороды, спирты, кислоты, альдегиды, эфиры)',
       answer_rule='выбрать все вещества, для которых такая реакция возможна',
       mistakes=['бензол гидрируется, но не гидратируется', 'полимеризуются только вещества с кратной связью',
                 'в этерификацию вступают спирты и кислоты, а не альдегиды'],
       solve=_solve_type, kind='dict', kes=KES12,
       fidelity=fid(ALL12, 'П', 3, '«вступают в реакцию полимеризации / гидратации / присоединения» (банк №12)',
                    'углеводороды с похожими названиями из разных рядов', KES12, SC1))
def g12_type(rng):
    t = rng.choice(list(TYPE_Q))
    cand = [f for f in POOL12 if type_known(f, t) is not None]
    pos = [f for f in cand if type_known(f, t)]
    neg = [f for f in cand if type_known(f, t) is False]
    k = rng.randint(2, 4)
    if len(pos) < k or len(neg) < 5 - k:
        raise Retry
    items = rng.sample(pos, k) + rng.sample(neg, 5 - k)
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    if len(set(names)) < 5:
        raise Retry
    q = _q_all(rng, 'которые ' + TYPE_Q[t][0])
    good = [i for i, f in enumerate(items) if type_known(f, t)]
    N = dict(zip(items, names))
    seg = []
    for f in items:
        if type_known(f, t):
            r = next((r for r in RX if (r['lhs'][0] == f or f in r['lhs']) and TYPE_Q[t][2] and TYPE_Q[t][2](r)), None)
            seg.append(f'{N[f]} — да' + (f': {rx_eq(r)}' if r else ' (мономер)'))
        else:
            seg.append(f'{N[f]} — нет')
    return many_card('ch-ege-12-reaction-type', q, names, good, '; '.join(seg) + '.', {'items': items, 't': t})


KES13 = ['3.14', '3.15', '3.16', '3.17']
TWO13 = 'пять вариантов, ответ — две цифры (порядок не важен)'
N_POOL = ['CH3NH2', '(CH3)2NH', '(CH3)3N', 'C2H5NH2', '(C2H5)2NH', '(C2H5)3N', 'CH3CH2CH2NH2', '(CH3)2CHNH2',
          'CH3NHC2H5', 'C6H5NH2', 'C6H5NHCH3', 'H2NCH2COOH', 'CH3CH(NH2)COOH']
C_POOL = ['C6H12O6', 'HOCH2(CHOH)3COCH2OH', 'C12H22O11', '(C6H11O5)2O', 'C6H10O5', 'C6H7O2(OH)3',
          '(C17H35COO)3C3H5', '(C15H31COO)3C3H5', '(C17H33COO)3C3H5', '(C17H31COO)3C3H5']
INERT = {'NaCl', 'Na2SO4', 'KNO3', 'CH4', 'Cu', 'N2', 'KCl', 'Ag'}
RK13 = ['HCl', 'H2SO4', 'HNO3', 'NaOH', 'KOH', 'NaHCO3', 'O2', 'Br2aq', 'H2O', 'CH3OH', 'Na', 'AgNH3', 'Cu(OH)2', 'H2',
        'I2', 'CH3Cl', 'NaCl', 'Na2SO4', 'KNO3', 'CH4', 'Cu', 'N2', 'KCl', 'Ag']


def _gen_two_rk(pid, rng, pool):
    f = rng.choice(pool)
    want = rng.random() < 0.75
    ok = [rk for rk in RK13 if known(f, rk) is not None]
    pos = [rk for rk in ok if known(f, rk)]
    neg = [rk for rk in ok if known(f, rk) is False]
    g, b = (pos, neg) if want else (neg, pos)
    b_real = [x for x in b if x not in INERT]
    b_inert = [x for x in b if x in INERT]
    if len(g) < 2 or len(b) < 3:
        raise Retry
    if len(b_real) >= 3 and rng.random() < 0.6:
        bb = rng.sample(b_real, 3)
    else:
        k = min(2, len(b_real))
        if len(b_inert) < 3 - k:
            raise Retry
        bb = rng.sample(b_real, k) + rng.sample(b_inert, 3 - k)
    rks = rng.sample(g, 2) + bb
    rng.shuffle(rks)
    names = [_rk_text(rng, rk) for rk in rks]
    N = {f: nm(f, rng)}
    if want:
        q = q_many('два', 'вещества', f'с которыми взаимодействует {N[f]}')
    else:
        q = q_many('два', 'вещества', f'с которыми не взаимодействует {N[f]}')
    good = [i for i, rk in enumerate(rks) if known(f, rk) == want]
    return many_card(pid, q, names, good, _rk_expl([f], rks, N), {'subs': [f], 'rks': rks, 'want': want})


def _solve_two_rk(p):
    f = p['subs'][0]
    return [str(i + 1) for i, rk in enumerate(p['rks']) if react_db(f, rk) == p['want']]


@proto('ch-ege-13-n-compound-reagents', 'ЕГЭ', 13, 'Свойства аминов и аминокислот: с чем реагирует (не реагирует)',
       invariant='амины — основания (реагируют с кислотами, алкилируются), анилин — ещё и с бромной водой; '
                 'аминокислоты амфотерны (кислоты, щёлочи, спирты)',
       varies='амин / аминокислота (13 веществ), пять реагентов; вопрос «реагирует» / «не реагирует»',
       answer_rule='выбрать два реагента по кислотно-основным свойствам и особенностям строения',
       mistakes=['амины не реагируют со щелочами', 'анилин — слабое основание, но с HCl реагирует',
                 'глицин реагирует и с HCl, и с NaOH'],
       solve=_solve_two_rk, kind='dict', kes=KES13,
       fidelity=fid(TWO13, 'Б', 3, '«с которыми реагирует метиламин / анилин / аминоуксусная кислота» (банк №13)',
                    'реагенты для соседнего класса (щёлочь для амина, соль для аминокислоты)', KES13, SC1))
def g13_n_rk(rng):
    return _gen_two_rk('ch-ege-13-n-compound-reagents', rng, N_POOL)


@proto('ch-ege-13-carb-fat-reagents', 'ЕГЭ', 13, 'Свойства углеводов и жиров: с чем реагирует (не реагирует)',
       invariant='глюкоза — альдегидоспирт; фруктоза, сахароза — без альдегидной группы; ди- и полисахариды, жиры '
                 'гидролизуются; ненасыщенные жиры присоединяют H₂ и Br₂',
       varies='углевод или жир, пять реагентов (Ag₂O/NH₃, Cu(OH)₂, H₂, Br₂ (водн.), H₂O, I₂, NaOH …)',
       answer_rule='выбрать два реагента, с которыми вещество реагирует (не реагирует)',
       mistakes=['сахароза не даёт «серебряного зеркала»', 'крахмал не реагирует с Cu(OH)₂ и Ag₂O',
                 'тристеарат глицерина не присоединяет водород'],
       solve=_solve_two_rk, kind='dict', kes=KES13,
       fidelity=fid(TWO13, 'Б', 3, '«с которыми реагирует глюкоза, но не сахароза», триолеат против тристеарата '
                                   '(банк №13)', 'восстанавливающие и невосстанавливающие углеводы', KES13, SC1))
def g13_c_rk(rng):
    return _gen_two_rk('ch-ege-13-carb-fat-reagents', rng, C_POOL)


def _solve_pair13(p):
    a, b = p['subs']
    out = []
    for i, rk in enumerate(p['rks']):
        x, y = react_db(a, rk), react_db(b, rk)
        if (p['mode'] == 'both' and x and y) or (p['mode'] == 'only' and x and not y):
            out.append(str(i + 1))
    return out


@proto('ch-ege-13-compare-two', 'ЕГЭ', 13, 'Сравнение двух веществ: реагируют оба / реагирует первое, но не второе',
       invariant='сопоставить свойства двух азотсодержащих веществ или углеводов (жиров) по одному набору реагентов',
       varies='пара веществ (глицин/этиламин, анилин/метиламин, глюкоза/сахароза, триолеин/тристеарин …), режим',
       answer_rule='для каждого реагента оценить обе реакции; выбрать два реагента по условию',
       mistakes=['глицин, в отличие от этиламина, реагирует со щелочами и спиртами', 'анилин, в отличие от метиламина, '
                                                                                 'обесцвечивает бромную воду',
                 'глюкоза, в отличие от сахарозы, даёт «серебряное зеркало»'],
       solve=_solve_pair13, kind='dict', kes=KES13,
       fidelity=fid(TWO13, 'Б', 3, '«с которыми взаимодействует глицин, но не взаимодействует фениламин», «и глюкоза, '
                                   'и фруктоза» (банк №13)', 'общие и различающие реагенты', KES13, SC1))
def g13_compare(rng):
    pool = rng.choice([N_POOL, C_POOL])
    a, b = rng.sample(pool, 2)
    mode = rng.choice(['both', 'only'])
    ok = [rk for rk in RK13 if known(a, rk) is not None and known(b, rk) is not None]
    fit = [rk for rk in ok if (known(a, rk) and known(b, rk)) if mode == 'both'] if mode == 'both' else \
        [rk for rk in ok if known(a, rk) and not known(b, rk)]
    rest = [rk for rk in ok if rk not in fit]
    rest_real = [rk for rk in rest if rk not in INERT]
    if len(fit) < 2 or len(rest) < 3:
        raise Retry
    k_in = max(0, 3 - len(rest_real))
    if k_in > 1:
        raise Retry
    rks = rng.sample(fit, 2) + rng.sample(rest_real, 3 - k_in) + rng.sample([r for r in rest if r in INERT], k_in)
    rng.shuffle(rks)
    names = [_rk_text(rng, rk) for rk in rks]
    N = {a: nm(a, rng), b: nm(b, rng)}
    if mode == 'both':
        q = q_many('два', 'вещества', f'с каждым из которых взаимодействуют и {N[a]}, и {N[b]}')
    else:
        q = q_many('два', 'вещества', f'с которыми взаимодействует {N[a]}, но не взаимодействует {N[b]}')
    good = [i for i, rk in enumerate(rks) if rk in fit]
    return many_card('ch-ege-13-compare-two', q, names, good, _rk_expl([a, b], rks, N),
                     {'subs': [a, b], 'rks': rks, 'mode': mode})


STRONGER = ['CH3NH2', '(CH3)2NH', '(CH3)3N', 'C2H5NH2', '(C2H5)2NH', '(C2H5)3N', 'CH3CH2CH2NH2', '(CH3)2CHNH2',
            'CH3NHC2H5']
WEAKER = ['C6H5NH2', 'C6H5NHCH3', 'CH3C6H4NH2', '(C6H5)2NH', '(C6H5)3N']


def _aryl_on_n(f):
    """Число ароматических атомов углерода, связанных с атомом N (по графу SMILES): 0 — алифатический амин."""
    atoms, bonds = D.smiles_info(SMI[f])['graph']
    n = 0
    for i, j, o in bonds:
        for x, y in ((i, j), (j, i)):
            if atoms[x][0] == 'N' and atoms[y][1]:
                n += 1
    return n


def _solve_basic(p):
    out = []
    for i, f in enumerate(p['items']):
        ar = _aryl_on_n(f)
        if p['mode'] == 'stronger_nh3' and ar == 0:
            out.append(str(i + 1))
        elif p['mode'] == 'weaker_nh3' and ar > 0:
            out.append(str(i + 1))
        elif p['mode'] == 'weaker_aniline' and ar >= 2:
            out.append(str(i + 1))
    return out


@proto('ch-ege-13-basicity', 'ЕГЭ', 13, 'Сравнение основных свойств аминов и аммиака',
       invariant='алкильные группы усиливают основность (сильнее NH₃), фенильные — ослабляют (слабее NH₃, '
                 'дифениламин слабее анилина)',
       varies='режим (сильнее аммиака / слабее аммиака / слабее анилина), амины',
       answer_rule='определить, какие радикалы при атоме азота: алкилы или арилы, и сколько арилов',
       mistakes=['анилин считают сильнее аммиака', 'триметиламин ошибочно отнесён к слабым основаниям'],
       solve=_solve_basic, kind='dict', kes=KES13,
       fidelity=fid(TWO13, 'Б', 3, '«более сильные основания, чем аммиак», «основные свойства слабее, чем у анилина» '
                                   '(банк №13)', 'ароматические и алифатические амины рядом', KES13, SC1))
def g13_basic(rng):
    mode = rng.choice(['stronger_nh3', 'weaker_nh3', 'weaker_aniline'])
    if mode == 'stronger_nh3':
        good = rng.sample(STRONGER, 2)
        bad = rng.sample(WEAKER, 3)
        what = 'основность которых выше, чем у аммиака'
    elif mode == 'weaker_nh3':
        good = rng.sample(WEAKER, 2)
        bad = rng.sample(STRONGER, 3)
        what = 'основность которых ниже, чем у аммиака'
    else:
        good = ['(C6H5)2NH', '(C6H5)3N']
        bad = rng.sample(STRONGER, 2) + rng.sample(['C6H5NHCH3', 'CH3C6H4NH2'], 1)
        what = 'основность которых ниже, чем у анилина'
    items = good + bad
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    q = q_many('два', 'вещества', what)
    e = ('Алкильные радикалы увеличивают электронную плотность на атоме азота — основность выше, чем у NH₃; бензольное '
         'кольцо её оттягивает — основность ниже; два-три фенила ослабляют сильнее, чем один. '
         + '; '.join(f'{n} — {"ароматический" if _aryl_on_n(f) else "алифатический"}' for f, n in zip(items, names)) + '.')
    return many_card('ch-ege-13-basicity', q, names, [items.index(g) for g in good], e, {'mode': mode, 'items': items})


HYD_POS = ['C12H22O11', '(C6H11O5)2O', 'C6H10O5', 'C6H7O2(OH)3', '(C17H35COO)3C3H5', '(C15H31COO)3C3H5',
           '(C17H33COO)3C3H5', 'H2NCH2CONHCH2COOH', 'H2NCH2CONHCH(CH3)COOH', 'CH3CH(NH2)CONHCH2COOH', 'CH3COOC2H5',
           'HCOOCH3', 'CH3COOCH3', 'H2NCH2COOCH3']
HYD_NEG = ['C6H12O6', 'HOCH2(CHOH)3COCH2OH', 'C5H10O5', 'C3H5(OH)3', 'H2NCH2COOH', 'CH3CH(NH2)COOH', 'CH3NH2',
           'C6H5NH2', 'C2H5OH', 'C17H35COOH', 'C6H8(OH)6']


def _hydrolyzes(f):
    for r in D.REACTIONS:
        if r['lhs'][0] == f and 'гидролиза' in r['type'] and SUB[f].get('org') and f not in ('C2H5ONa',):
            return True
    return any(r['lhs'][0] == f and 'гидролиза' in r['type'] for r in D.FACTS)


def _solve_hyd(p):
    return [str(i + 1) for i, f in enumerate(p['items']) if _hydrolyzes(f) == p['want']]


@proto('ch-ege-13-hydrolysis', 'ЕГЭ', 13, 'Какие вещества подвергаются (не подвергаются) гидролизу',
       invariant='гидролизуются ди- и полисахариды, жиры и сложные эфиры, пептиды (белки); моносахариды, спирты, '
                 'амины, аминокислоты — нет',
       varies='режим (подвергаются / не подвергаются), пять веществ из углеводов, жиров, пептидов, эфиров',
       answer_rule='найти связи, которые разрываются водой: гликозидная, сложноэфирная, пептидная',
       mistakes=['глюкоза и фруктоза не гидролизуются', 'аминокислота не гидролизуется, в отличие от дипептида'],
       solve=_solve_hyd, kind='dict', kes=KES13,
       fidelity=fid(TWO13, 'Б', 3, '«два вещества, которые подвергаются гидролизу / не подвергаются» (банк №13)',
                    'моносахариды рядом с дисахаридами, аминокислота рядом с пептидом', KES13, SC1))
def g13_hydrolysis(rng):
    want = rng.random() < 0.65
    g, b = (HYD_POS, HYD_NEG) if want else (HYD_NEG, HYD_POS)
    good = rng.sample(g, 2)
    items = good + rng.sample(b, 3)
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    if len(set(names)) < 5:
        raise Retry
    what = 'которые подвергаются гидролизу' if want else 'которые не подвергаются гидролизу'
    q = q_many('два', 'вещества', what)
    e = '; '.join(f'{n} — {"гидролизуется" if f in HYD_POS else "не гидролизуется"}' for f, n in zip(items, names)) + '.'
    return many_card('ch-ege-13-hydrolysis', q, names, [items.index(x) for x in good], e, {'items': items, 'want': want})


TYPES13 = {  # вещество → {тип реакции: вступает?}
    'C6H7O2(OH)3': {'этерификации': 1, 'гидролиза': 1, 'горения': 1, 'полимеризации': 0, 'нейтрализации': 0,
                    'гидратации': 0, 'гидрирования': 0, '«серебряного зеркала»': 0},
    'C6H10O5': {'гидролиза': 1, 'горения': 1, 'полимеризации': 0, 'нейтрализации': 0, 'гидратации': 0,
                '«серебряного зеркала»': 0, 'гидрирования': 0},
    'C12H22O11': {'гидролиза': 1, 'горения': 1, '«серебряного зеркала»': 0, 'гидрирования': 0, 'полимеризации': 0,
                  'нейтрализации': 0, 'брожения': 0},
    'C6H12O6': {'брожения': 1, 'гидрирования': 1, '«серебряного зеркала»': 1, 'горения': 1, 'гидролиза': 0,
                'полимеризации': 0, 'нейтрализации': 0, 'гидратации': 0},
    '(C17H33COO)3C3H5': {'гидролиза': 1, 'гидрирования': 1, 'омыления': 1, 'нейтрализации': 0, 'полимеризации': 0,
                         '«серебряного зеркала»': 0, 'этерификации': 0},
    '(C17H35COO)3C3H5': {'гидролиза': 1, 'омыления': 1, 'гидрирования': 0, 'нейтрализации': 0, 'полимеризации': 0,
                         '«серебряного зеркала»': 0, 'гидратации': 0},
    'H2NCH2COOH': {'нейтрализации': 1, 'этерификации': 1, 'поликонденсации': 1, 'горения': 1, 'гидролиза': 0,
                   'гидратации': 0, 'полимеризации': 0, '«серебряного зеркала»': 0},
    '(C6H11O5)2O': {'гидролиза': 1, '«серебряного зеркала»': 1, 'горения': 1, 'полимеризации': 0, 'нейтрализации': 0,
                    'гидратации': 0},
}
TYPE_WORD = {'«серебряного зеркала»': 'реакция «серебряного зеркала»', 'брожения': 'брожение',
             'омыления': 'омыление (щелочной гидролиз)'}


def _types_db(f):
    """Типы реакций вещества по базе: поле type реакций и фактов, где оно — субстрат."""
    out = set()
    for r in list(D.REACTIONS) + list(D.FACTS):
        if r['lhs'][0] == f or (f in r['lhs'] and 'этерификации' in r['type']):
            out.update(r['type'])
            if 'серебряное зеркало' in r.get('sign', ''):
                out.add('«серебряного зеркала»')
            if any('брожение' in t for t in r['type']):
                out.add('брожения')
    return out


def _solve_types13(p):
    have = _types_db(p['f'])
    return [str(i + 1) for i, t in enumerate(p['types']) if t in have]


@proto('ch-ege-13-reaction-types', 'ЕГЭ', 13, 'Типы реакций, в которые вступает углевод, жир или аминокислота',
       invariant='связать строение (многоатомный спирт, альдегидная группа, сложноэфирная/гликозидная связь, C=C) '
                 'с типами реакций',
       varies='вещество (целлюлоза, крахмал, сахароза, глюкоза, мальтоза, жиры, глицин), пять типов реакций',
       answer_rule='выбрать два типа реакций, возможных для вещества',
       mistakes=['целлюлоза вступает в этерификацию (нитраты, ацетаты), но не в полимеризацию',
                 'сахароза не даёт «серебряного зеркала»', 'насыщенный жир не гидрируется'],
       solve=_solve_types13, kind='dict', kes=KES13,
       fidelity=fid(TWO13, 'Б', 3, 'демо 2027 (целлюлоза: этерификация, гидролиз); «в отличие от тристеарата вступает '
                                   'триолеат» (банк)', 'типы реакций соседних классов', KES13, SC1))
def g13_types(rng):
    f = rng.choice(list(TYPES13))
    t = TYPES13[f]
    pos = [k for k, v in t.items() if v and k in _types_db(f)]
    neg = [k for k, v in t.items() if not v and k not in _types_db(f)]
    if len(pos) < 2 or len(neg) < 3:
        raise Retry
    types = rng.sample(pos, 2) + rng.sample(neg, 3)
    rng.shuffle(types)
    items = ['реакция ' + x if x not in TYPE_WORD else TYPE_WORD[x] for x in types]
    n = nm(f, rng)
    q = q_many('две', 'реакции', f'в которые вступает {n}')
    have = _types_db(f)
    e = f'{n}: ' + '; '.join(f'{it} — {"да" if ty in have else "нет"}' for it, ty in zip(items, types)) + '.'
    return many_card('ch-ege-13-reaction-types', q, items, [types.index(x) for x in types if x in have], e,
                     {'f': f, 'types': types})


HP_R = [r for r in RX if r['lhs'][0] in ('(C17H35COO)3C3H5', '(C15H31COO)3C3H5', '(C17H33COO)3C3H5',
                                         '(C17H31COO)3C3H5', 'H2NCH2COOCH3', 'H2NCH2CONHCH2COOH',
                                         'H2NCH2CONHCH(CH3)COOH', 'CH3CH(NH2)CONHCH2COOH', 'CH3CH(NH2)CONHCH(CH3)COOH')
        and 'гидролиза' in r['type']]
HP_ORG = ['C17H35COOH', 'C15H31COOH', 'C17H33COOH', 'C17H35COONa', 'C17H35COOK', 'C15H31COONa', 'C17H33COONa',
          'C3H5(OH)3', 'C2H4(OH)2', 'H2NCH2COOH', 'CH3CH(NH2)COOH', 'H2NCH2COONa', 'CH3CH(NH2)COONa', 'ClH3NCH2COOH',
          'CH3OH', 'C2H5OH', 'CH3COONa', 'C6H12O6', 'CH3CH(NH3Cl)COOH', 'H2NCH2COOK', 'C17H33COOK', 'C15H31COOK']


def _solve_hp(p):
    lhs = list(p['lhs'])
    prods = set()
    for r in D.REACTIONS:
        if r['lhs'] == lhs and r.get('cond', '') == p['cond']:
            prods.update(x for x in r['rhs'] if x in SUB and SUB[x].get('org'))
    return [str(i + 1) for i, f in enumerate(p['items']) if f in prods]


@proto('ch-ege-13-hydrolysis-products', 'ЕГЭ', 13, 'Продукты гидролиза жира, эфира аминокислоты, дипептида',
       invariant='при гидролизе рвётся сложноэфирная или пептидная связь; в щёлочи кислота даёт соль, в кислоте '
                 'аминогруппа — соль аммония',
       varies='вещество (4 жира, эфир глицина, 4 дипептида), среда (вода/кислота, NaOH, KOH, HCl)',
       answer_rule='записать продукты с учётом среды и выбрать два органических продукта из пяти',
       mistakes=['в щелочной среде вместо соли записана кислота', 'при гидролизе жира забыт глицерин',
                 'в кислой среде аминокислота образует соль (хлорид)'],
       solve=_solve_hp, kind='dict', kes=KES13,
       fidelity=fid(TWO13, 'Б', 3, '«образуются при щелочном гидролизе жира», «при гидролизе этилового эфира '
                                   '2-аминопропановой кислоты в присутствии HCl» (банк №13)',
                    'кислота вместо соли и наоборот', KES13, SC1))
def g13_hp(rng):
    r = rng.choice(HP_R)
    prods = [x for x in r['rhs'] if x in SUB and SUB[x].get('org')]
    if len(prods) != 2:
        raise Retry
    bad = [x for x in HP_ORG if x not in prods]
    # ловушки: та же кислота в другой форме, другие жирные кислоты
    items = prods + rng.sample(bad, 3)
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    if len(set(names)) < 5:
        raise Retry
    sub = r['lhs'][0]
    med = {'NaOH': 'в присутствии гидроксида натрия', 'KOH': 'в присутствии гидроксида калия',
           'HCl': 'в присутствии соляной кислоты'}.get(r['lhs'][1] if len(r['lhs']) > 1 else '', 'в кислой среде')
    if r['lhs'][1:2] == ['H2O'] and 'OH-' in r.get('cond', ''):
        med = 'водой при нагревании (катализатор — кислота)'
    shown = vw(sub) if rng.random() < 0.5 else nm(sub, rng)
    q = q_many('два', 'вещества', f'которые образуются при гидролизе вещества {shown} {med}')
    return many_card('ch-ege-13-hydrolysis-products', q, names, [items.index(x) for x in prods], rx_eq(r) + '.',
                     {'lhs': r['lhs'], 'cond': r.get('cond', ''), 'items': items}, eqs=[eqt(r)])


AM_TARGETS = ['CH3NH2', 'C2H5NH2', 'C6H5NH2', '(CH3)2NH', 'C6H5NH3Cl', '(CH3)2NH2Cl', 'CH3NH3Cl', 'H2NCH2COOH',
              'CH3CH(NH2)COOH', 'C2H5NH3Cl']
AM_R = [r for r in RX if any(x in SUB and 'N' in parse_formula(x) for x in r['rhs']) and 'горения' not in r['type']
        and len(SCHEME[rkey(r)]) == 1]


def _solve_amine_syn(p):
    out = []
    for i, (lhs, cond, med) in enumerate(p['keys']):
        if any(r['lhs'] == list(lhs) and r.get('cond', '') == cond and p['target'] in r['rhs'] for r in D.REACTIONS):
            out.append(str(i + 1))
    return out


@proto('ch-ege-13-n-synthesis', 'ЕГЭ', 13, 'Схемы реакций получения амина (аминокислоты, соли амина)',
       invariant='амины получают восстановлением нитросоединений, алкилированием аммиака, из солей аммония щёлочью; '
                 'аминокислоты — из галогенкарбоновых кислот и аммиака, гидролизом пептидов',
       varies='целевое вещество, пять схем (две верные)',
       answer_rule='мысленно провести каждую реакцию и найти две, дающие целевое вещество',
       mistakes=['при действии HCl на амин образуется соль, а не амин', 'реакция Зинина даёт анилин (в кислоте — '
                                                                        'его соль)'],
       solve=_solve_amine_syn, kind='dict', kes=KES13,
       fidelity=fid(TWO13, 'Б', 3, '«схемы двух реакций, в результате которых образуется метиламин / анилин» (банк)',
                    'схема с тем же субстратом, дающая соль вместо амина', KES13, SC1))
def g13_n_syn(rng):
    tp = rng.choice(AM_TARGETS)
    good_r = [r for r in AM_R if tp in r['rhs']]
    if len({rkey(r) for r in good_r}) < 2:
        raise Retry
    good = pick_distinct(rng, good_r, 2, key=rkey)
    bad_pool = [r for r in AM_R if tp not in r['rhs'] and rkey(r) not in {rkey(g) for g in good}]
    bad = pick_distinct(rng, bad_pool, 3, key=rkey)
    rs = good + bad
    rng.shuffle(rs)
    items = [rx_scheme(r) for r in rs]
    if len(set(items)) < 5:
        raise Retry
    q = q_many('две', 'схемы реакций', f'в результате которых образуется {nm(tp)}')
    return many_card('ch-ege-13-n-synthesis', q, items, [rs.index(g) for g in good], '; '.join(rx_eq(r) for r in rs) + '.',
                     {'keys': [list(rkey(r)) for r in rs], 'target': tp}, eqs=[eqt(r) for r in rs])


AMPH = ['H2NCH2COOH', 'CH3CH(NH2)COOH', 'H2NCH2CH2COOH', 'H2N(CH2)5COOH', 'C6H5CH2CH(NH2)COOH']
NOT_AMPH = ['CH3NH2', 'C6H5NH2', 'CH3COOH', 'C6H5OH', 'C2H5OH', 'CH3COOC2H5', '(CH3)2NH', 'CH3CH2COOH', 'HCOOH',
            'C3H5(OH)3']


def _solve_amph(p):
    # амфотерность: в молекуле есть и основная аминогруппа (не нитро, не амид), и карбоксильная группа
    def amph(f):
        s = SMI[f]
        return 'N' in s and 'N(=O)' not in s and bool(re.search(r'C\(=O\)O$|C\(=O\)O\)', s))
    return [str(i + 1) for i, f in enumerate(p['items']) if amph(f)]


@proto('ch-ege-13-amphoteric', 'ЕГЭ', 13, 'Амфотерные органические вещества (аминокислоты)',
       invariant='амфотерность — у веществ с кислотной (–COOH) и основной (–NH₂) группами',
       varies='аминокислоты (глицин, аланин, β-аланин, ε-аминокапроновая, фенилаланин) и отвлекающие',
       answer_rule='выбрать вещества, реагирующие и с кислотами, и со щелочами за счёт двух групп',
       mistakes=['фенол — только слабая кислота', 'амины — только основания'],
       solve=_solve_amph, kind='dict', kes=KES13,
       fidelity=fid(TWO13, 'Б', 3, '«два вещества, которые проявляют амфотерные свойства» (банк №13)',
                    'кислоты и амины в отвлекающих', KES13, SC1))
def g13_amph(rng):
    good = rng.sample(AMPH, 2)
    items = good + rng.sample(NOT_AMPH, 3)
    rng.shuffle(items)
    names = [nm(f, rng) for f in items]
    q = q_many('два', 'вещества', 'которые проявляют амфотерные свойства')
    e = 'Амфотерны аминокислоты: ' + ', '.join(f'{nm(f)} ({vw(f)})' for f in good) + '.'
    return many_card('ch-ege-13-amphoteric', q, names, [items.index(g) for g in good], e, {'items': items})


STATEMENTS = {
    'белки': ([
        'подвергаются гидролизу с образованием α-аминокислот', 'необратимо денатурируют при нагревании',
        'дают фиолетовое окрашивание с Cu(OH)₂ в щелочной среде', 'дают жёлтое окрашивание с концентрированной HNO₃',
        'содержат пептидные связи –CO–NH–', 'являются природными высокомолекулярными соединениями',
        'образуются при поликонденсации α-аминокислот'], [
        'образуются при полимеризации аминокислот', 'дают реакцию «серебряного зеркала»', 'не подвергаются гидролизу',
        'построены из остатков глюкозы', 'окрашиваются иодом в синий цвет', 'при денатурации распадаются на аминокислоты',
        'являются синтетическими полимерами']),
    'сахароза': ([
        'при гидролизе образует глюкозу и фруктозу', 'растворяет гидроксид меди(II) с образованием синего раствора',
        'является дисахаридом', 'имеет молекулярную формулу C₁₂H₂₂O₁₁', 'хорошо растворима в воде'], [
        'даёт реакцию «серебряного зеркала»', 'является моносахаридом', 'восстанавливает гидроксид меди(II) до Cu₂O',
        'не подвергается гидролизу', 'является полимером', 'окрашивается иодом в синий цвет']),
    'глюкоза': ([
        'даёт реакцию «серебряного зеркала»', 'при восстановлении образует шестиатомный спирт сорбит',
        'подвергается спиртовому брожению', 'является альдегидоспиртом', 'образуется при гидролизе крахмала'], [
        'подвергается гидролизу', 'является дисахаридом', 'не реагирует с гидроксидом меди(II)',
        'является кетоспиртом', 'окрашивается иодом в синий цвет', 'является полимером']),
    'крахмал': ([
        'является природным полимером', 'при полном гидролизе даёт глюкозу', 'окрашивается иодом в синий цвет',
        'построен из остатков α-глюкозы', 'образуется в растениях при фотосинтезе'], [
        'даёт реакцию «серебряного зеркала»', 'построен из остатков β-глюкозы', 'хорошо растворим в холодной воде',
        'является дисахаридом', 'не подвергается гидролизу']),
    'целлюлоза': ([
        'является природным полимером', 'построена из остатков β-глюкозы', 'при гидролизе образует глюкозу',
        'образует сложные эфиры с азотной и уксусной кислотами', 'служит сырьём для искусственных волокон'], [
        'окрашивается иодом в синий цвет', 'хорошо растворима в воде', 'даёт реакцию «серебряного зеркала»',
        'построена из остатков α-глюкозы', 'является синтетическим полимером']),
    'жиры': ([
        'являются сложными эфирами глицерина и высших карбоновых кислот', 'подвергаются щелочному гидролизу (омылению)',
        'жидкие растительные масла содержат остатки непредельных кислот', 'нерастворимы в воде',
        'при гидролизе образуют глицерин'], [
        'являются полимерами', 'хорошо растворимы в воде', 'при гидрировании жидкие масла превращаются в жидкие же '
                                                          'углеводороды', 'содержат пептидные связи',
        'дают реакцию «серебряного зеркала»']),
}
STMT_TRUE = {(k, t) for k, (tr, fa) in STATEMENTS.items() for t in tr}


def _solve_stmt(p):
    return [str(i + 1) for i, t in enumerate(p['items']) if (p['subj'], t) in STMT_TRUE]


@proto('ch-ege-13-statements', 'ЕГЭ', 13, 'Верные характеристики белков, углеводов, жиров',
       invariant='знание строения и свойств биологически важных веществ (белки, глюкоза, сахароза, крахмал, целлюлоза, '
                 'жиры)',
       varies='вещество, набор из двух верных и трёх неверных характеристик',
       answer_rule='выбрать две характеристики, справедливые для вещества',
       mistakes=['белки образуются поликонденсацией, а не полимеризацией', 'крахмал — α-, целлюлоза — β-глюкоза',
                 'сахароза не восстанавливает Cu(OH)₂'],
       solve=_solve_stmt, kind='dict', kes=KES13,
       fidelity=fid(TWO13, 'Б', 3, '«две характеристики, которые справедливы для сахарозы» (банк №13); белки — '
                                   'кодификатор 3.17', 'характеристики соседнего вещества (крахмал ↔ целлюлоза)',
                    KES13, SC1))
def g13_stmt(rng):
    subj = rng.choice(list(STATEMENTS))
    tr, fa = STATEMENTS[subj]
    good = rng.sample(tr, 2)
    items = good + rng.sample(fa, 3)
    rng.shuffle(items)
    q = q_many('два', 'утверждения', f'которые справедливы для веществ «{subj}»' if subj in ('белки', 'жиры') else
               f'которые справедливы для вещества «{subj}»')
    e = f'Верно: {good[0]}; {good[1]}. Остальные утверждения неверны.'
    return many_card('ch-ege-13-statements', q, items, [items.index(g) for g in good], e, {'subj': subj, 'items': items})


# ================================================================= задания 14, 15: соответствие «схема — продукт/реагент»

KES14 = ['3.4', '3.5', '3.6', '3.7', '3.8', '3.9']
KES15 = ['3.10', '3.11', '3.12', '3.13', '3.14', '3.15']
HC_CLS = {'углеводород', 'галогенпроизводное'}
O_CLS = {'спирт', 'фенол', 'альдегид', 'кетон', 'карбоновая кислота', 'сложный эфир', 'простой эфир',
         'соль карбоновой кислоты', 'алкоголят', 'фенолят'}


def _ok_rx(r):
    return (r['rhs'][0] in SUB and SUB[r['rhs'][0]].get('org') and 'горения' not in r['type']
            and len(SCHEME[rkey(r)]) == 1 and r['lhs'][0] in SUB and SUB[r['lhs'][0]].get('org')
            and parse_formula(r['rhs'][0]).get('C', 0) <= 10 and r['rhs'][0] not in _POOL10_SKIP
            and SUB[r['rhs'][0]]['hom'] not in ('жиры',) and SUB[r['lhs'][0]]['hom'] not in ('жиры',))


POOL14 = [r for r in RX if _ok_rx(r) and SUB[r['lhs'][0]]['cls'] in HC_CLS]
POOL15 = [r for r in RX if _ok_rx(r) and SUB[r['lhs'][0]]['cls'] in O_CLS]
AREN14 = [r for r in POOL14 if 'C6H' in r['lhs'][0] or r['lhs'][0] in ('C6H6', 'C10H8')]


def _prod_disp(f, how):
    return vw(f) if how == 'view' else nm(f)


def _solve_scheme_prod(p):
    out = {}
    for i, (lhs, cond, med) in enumerate(p['keys']):
        prods = {r['rhs'][0] for r in D.REACTIONS if r['lhs'] == list(lhs) and r.get('cond', '') == cond
                 and r.get('medium', '') == med}
        j = [n for n, f in enumerate(p['right']) if f in prods]
        out[LET[i]] = str(j[0] + 1)
    return out


def _gen_scheme_prod(pid, rng, pool):
    rs = pick_distinct(rng, pool, 4, key=rkey)
    subs = {r['lhs'][0] for r in rs}
    prods = [r['rhs'][0] for r in rs]
    uniq = list(dict.fromkeys(prods))
    # отвлекающие продукты: изомеры правильных, продукты тех же субстратов с другими реагентами
    conf = set()
    for f in uniq:
        conf.update(g for g in ORG if brutto(g) == brutto(f) and g != f and g not in _POOL10_SKIP)
    conf.update(r['rhs'][0] for r in pool if r['lhs'][0] in subs)
    conf -= set(uniq)
    conf = [c for c in conf if SUB[c].get('org') and SUB[c]['cls'] not in ('соль амина',)]
    need = 6 - len(uniq)
    if len(conf) < need:
        conf += [r['rhs'][0] for r in rng.sample(pool, 12) if r['rhs'][0] not in uniq]
        conf = list(dict.fromkeys(conf))
    if len(conf) < need:
        raise Retry
    right = uniq + rng.sample(sorted(conf), need)
    rng.shuffle(right)
    how = rng.choice(['name', 'name', 'view'])
    rt = [_prod_disp(f, how) for f in right]
    lt = [rx_scheme(r, names=(how == 'view' and rng.random() < 0.5) is False and rng.random() < 0.3, rng=rng)
          for r in rs]
    if len(set(rt)) < 6 or len(set(lt)) < 4:
        raise Retry
    q = mq('схемой реакции и органическим веществом, которое преимущественно образуется в этой реакции',
           'СХЕМА РЕАКЦИИ', 'ПРОДУКТ РЕАКЦИИ')
    ans = [right.index(r['rhs'][0]) for r in rs]
    e = '; '.join(rx_eq(r) for r in rs) + '.'
    return match_card(pid, rng, q, lt, rt, ans, e, {'keys': [list(rkey(r)) for r in rs], 'right': right},
                      eqs=[eqt(r) for r in rs])


@proto('ch-ege-14-scheme-product', 'ЕГЭ', 14, 'Схема реакции углеводорода (галогенпроизводного) → главный продукт',
       invariant='по реагентам и условиям определить главный органический продукт (Марковников, Зайцев, Кучеров, '
                 'Вюрц, водный/спиртовой раствор щёлочи, окисление KMnO₄)',
       varies='четыре схемы из ≈ 300 реакций алканов, циклоалканов, алкенов, диенов, алкинов, аренов, галогенпроизводных; '
              'продукты — названиями или формулами; в вариантах изомеры правильных продуктов',
       answer_rule='для каждой схемы записать продукт и найти его среди шести вариантов',
       mistakes=['водный раствор щёлочи — спирт, спиртовой — алкен', 'HBr присоединяется по Марковникову',
                 'малые циклы раскрываются при гидрировании'],
       solve=_solve_scheme_prod, kind='dict', kes=KES14,
       fidelity=fid(MATCH4, 'П', 6, 'схемы из банка №14: CH₂=CH₂ + H₂O (H₃PO₄), HC≡CH + H₂O (Hg²⁺), дигалогеналканы + Zn/KOH',
                    'изомерные продукты (1-/2-бромпропан, пропаналь/ацетон)', KES14, SC2))
def g14_scheme(rng):
    return _gen_scheme_prod('ch-ege-14-scheme-product', rng, POOL14)


@proto('ch-ege-14-arenes', 'ЕГЭ', 14, 'Реакции аренов и их производных → продукт',
       invariant='замещение в кольце (катализатор) и в боковой цепи (свет), окисление гомологов бензола KMnO₄ '
                 'в разных средах, алкилирование, гидрирование',
       varies='арен (бензол, толуол, этилбензол, ксилолы, стирол, кумол, хлорбензол, нитробензол, бензойная кислота), '
              'реагент и условия',
       answer_rule='определить место атаки (кольцо / боковая цепь) и среду окисления',
       mistakes=['на свету хлорируется боковая цепь, с FeCl₃ — кольцо', 'в нейтральной/щелочной среде KMnO₄ даёт соль '
                                                                         '(бензоат калия)',
                 'нитрогруппа и карбоксил — мета-ориентанты'],
       solve=_solve_scheme_prod, kind='dict', kes=KES14,
       fidelity=fid(MATCH4, 'П', 6, 'демо 2027 №14: C₆H₅Cl + KOH, стирол / кумол / толуол + KMnO₄ в разных средах',
                    'кислота/соль в зависимости от среды, кольцо/боковая цепь', KES14, SC2))
def g14_arenes(rng):
    return _gen_scheme_prod('ch-ege-14-arenes', rng, AREN14)


FIXED14 = [  # (описание процесса, ключ реагента, фильтр)
    ('основным органическим продуктом его гидратации', 'H2O', lambda r: 'гидратации' in r['type']),
    ('веществом, которое получается при исчерпывающем гидрировании исходного', 'H2', lambda r: 'гидрирования' in r['type'] and
     ('избыток' in r['cond'] or 'Pd' not in r['cond'])),
    ('основным продуктом его реакции с избытком HBr', 'HBr',
     lambda r: 'пероксиды' not in r['cond'] and '1 моль' not in r['cond']),
    ('основным продуктом его реакции с избытком бромной воды', 'Br2aq', lambda r: '1 моль' not in r['cond']),
    ('органическим продуктом, который получается при его окислении раствором KMnO₄ в присутствии H₂SO₄', 'KMnO4',
     lambda r: r.get('medium') == 'кисл.'),
]


def _fixed_prod(f, fi):
    rk, flt = FIXED14[fi][1], FIXED14[fi][2]
    ps = {r['rhs'][0] for r in RX if r['lhs'][0] == f and r.get('rk') == rk and flt(r)}
    fa = [x for x in FACTS if x['lhs'][0] == f and x.get('rk') == rk and flt(x) and x['prod'][0] in SUB]
    for x in fa:
        ps.add(x['prod'][0])
    return ps


def _solve_fixed(p):
    fi = p['fi']
    rk, flt = FIXED14[fi][1], FIXED14[fi][2]
    out = {}
    for i, f in enumerate(p['left']):
        ps = {r['rhs'][0] for r in D.REACTIONS if r['lhs'][0] == f and r.get('rk') == rk and flt(r)}
        ps |= {x['prod'][0] for x in D.FACTS if x['lhs'][0] == f and x.get('rk') == rk and flt(x)}
        j = [n for n, g in enumerate(p['right']) if g in ps]
        out[LET[i]] = str(j[0] + 1)
    return out


@proto('ch-ege-14-fixed-process', 'ЕГЭ', 14, 'Вещество → продукт одного и того же процесса (гидратация, гидрирование, '
                                             '+HBr, +Br₂, KMnO₄/H⁺)',
       invariant='один тип превращения для четырёх разных углеводородов; продукт зависит от строения',
       varies='процесс, четыре углеводорода (алкены, алкины, диены, циклоалканы, арены)',
       answer_rule='для каждого вещества провести процесс (правило Марковникова, реакция Кучерова, разрыв C=C при '
                   'окислении) и найти продукт',
       mistakes=['гидратация пропина даёт ацетон', 'при окислении бутена-1 получается пропановая кислота (и CO₂)',
                 'циклопропан при гидрировании даёт пропан'],
       solve=_solve_fixed, kind='dict', kes=KES14,
       fidelity=fid(MATCH4, 'П', 6, '«исходный углеводород — продукт гидратации / полного гидрирования / окисления '
                                   'KMnO₄ в кислой среде» (банк №14)', 'изомерные углеводороды с разными продуктами',
                    KES14, SC2))
def g14_fixed(rng):
    fi = rng.randrange(len(FIXED14))
    cand = [f for f in ORG if SUB[f]['cls'] == 'углеводород' and len(_fixed_prod(f, fi)) == 1]
    left = rng.sample(cand, 4)
    prods = [next(iter(_fixed_prod(f, fi))) for f in left]
    uniq = list(dict.fromkeys(prods))
    conf = set()
    for f in uniq:
        conf.update(g for g in ORG if (brutto(g) == brutto(f) or SUB[g]['hom'] == SUB[f].get('hom')) and g != f
                    and g not in _POOL10_SKIP and parse_formula(g).get('C', 0) <= 8)
    conf -= set(uniq)
    if len(conf) < 6 - len(uniq):
        raise Retry
    right = uniq + rng.sample(sorted(conf), 6 - len(uniq))
    rng.shuffle(right)
    rt = [nm(f) if f != 'CO2' else 'углекислый газ' for f in right]
    lt = [nm(f, rng) for f in left]
    if len(set(rt)) < 6 or len(set(lt)) < 4:
        raise Retry
    q = mq(f'углеводородом и {FIXED14[fi][0]}', 'ИСХОДНОЕ ВЕЩЕСТВО', 'ПРОДУКТ РЕАКЦИИ')
    ans = [right.index(p) for p in prods]
    ex = []
    for f, pr in zip(left, prods):
        r = next((r for r in RX if r['lhs'][0] == f and r['rhs'][0] == pr and r.get('rk') == FIXED14[fi][1]), None)
        ex.append(rx_eq(r) if r else f'{nm(f)} → {nm(pr)} (+ другие продукты окисления)')
    eqs = [eqt(r) for r in RX for f, pr in zip(left, prods)
           if r['lhs'][0] == f and r['rhs'][0] == pr and r.get('rk') == FIXED14[fi][1]]
    return match_card('ch-ege-14-fixed-process', rng, q, lt, rt, ans, '; '.join(ex) + '.',
                      {'fi': fi, 'left': left, 'right': right}, eqs=eqs or None)


def sig(r):
    """Сигнатура реагента: всё, кроме субстрата, + условия + среда."""
    return (tuple(r['lhs'][1:]), r.get('cond', ''), r.get('medium', ''))


def sig_label(r):
    rg = reagent_label(r)
    c = scheme_cond(r)
    if not rg:
        return c
    return rg + (f' ({c})' if c else '')


def _solve_reagent(p):
    out = {}
    for i, (sub, prod) in enumerate(p['left']):
        good = []
        for n, group in enumerate(p['right']):
            for sg in group:
                lhs = [sub] + list(sg[0])
                if any(r['lhs'] == lhs and r.get('cond', '') == sg[1] and r.get('medium', '') == sg[2]
                       and r['rhs'][0] == prod for r in D.REACTIONS):
                    good.append(n)
                    break
        out[LET[i]] = str(good[0] + 1)
    return out


def _gen_reagent(pid, rng, pool):
    by_label = defaultdict(set)
    for r in RX:
        by_label[sig_label(r)].add(sig(r))
    rs = pick_distinct(rng, pool, 4, key=lambda r: (r['lhs'][0], r['rhs'][0]))
    labels = list(dict.fromkeys(sig_label(r) for r in rs))
    others = sorted({sig_label(r) for r in pool} - set(labels))
    rng.shuffle(others)
    right = labels + others[:6 - len(labels)]
    if len(right) < 6:
        raise Retry
    rng.shuffle(right)
    # однозначность: для каждой строки подходит ровно один реагент из шести (по базе)
    for r in rs:
        n = sum(any(x['lhs'][0] == r['lhs'][0] and x['rhs'][0] == r['rhs'][0] and sig_label(x) == L for x in RX)
                for L in right)
        if n != 1:
            raise Retry
    lt = [f'{eqv(r["lhs"][0])} —X→ {eqv(r["rhs"][0])}' for r in rs]
    q = mq('схемой превращения и реагентом X, который участвует в этом превращении', 'СХЕМА ПРЕВРАЩЕНИЯ', 'РЕАГЕНТ X')
    ans = [right.index(sig_label(r)) for r in rs]
    return match_card(pid, rng, q, lt, right, ans, '; '.join(rx_eq(r) for r in rs) + '.',
                      {'left': [[r['lhs'][0], r['rhs'][0]] for r in rs],
                       'right': [sorted([list(x) for x in by_label[L]]) for L in right]},
                      eqs=[eqt(r) for r in rs])


R14 = [r for r in POOL14 if len(r['lhs']) >= 2 and r['lhs'][1] in SUB and not SUB[r['lhs'][1]].get('org')]
R15 = [r for r in POOL15 if len(r['lhs']) >= 2 and r['lhs'][1] in SUB and not SUB[r['lhs'][1]].get('org')]


@proto('ch-ege-14-reagent-x', 'ЕГЭ', 14, 'Превращение углеводорода (галогенпроизводного) → реагент X',
       invariant='по исходному веществу и продукту подобрать реагент и условия',
       varies='четыре превращения, шесть реагентов с условиями (H₂/Ni, HBr, Br₂, H₂O/Hg²⁺, KOH спирт./водн., Zn, Na …)',
       answer_rule='сравнить состав исходного вещества и продукта: что присоединилось / отщепилось / заместилось',
       mistakes=['спиртовой и водный растворы щёлочи перепутаны', 'для 1,2-дибромида Zn даёт алкен, KOH (спирт.) — алкин'],
       solve=_solve_reagent, kind='dict', kes=KES14,
       fidelity=fid(MATCH4, 'П', 6, '«схема реакции — реагент X» для пропина/бутина-2 (банк №14)',
                    'реагенты, дающие соседние продукты (HBr ↔ Br₂, H₂ ↔ H₂O)', KES14, SC2))
def g14_reagent(rng):
    return _gen_reagent('ch-ege-14-reagent-x', rng, R14)


def _solve_synth(p):
    out = {}
    for i, f in enumerate(p['left']):
        good = []
        for n, (lhs, cond, med) in enumerate(p['right']):
            if any(r['lhs'] == list(lhs) and r.get('cond', '') == cond and r.get('medium', '') == med
                   and r['rhs'][0] == f for r in D.REACTIONS):
                good.append(n)
        out[LET[i]] = str(good[0] + 1)
    return out


def _gen_synth(pid, rng, pool):
    by = defaultdict(list)
    for r in pool:
        by[r['rhs'][0]].append(r)
    targets = rng.sample(sorted(by), 4)
    right_r = []
    for t in targets:
        right_r.append(rng.choice(by[t]))
    rest = [r for r in pool if r['rhs'][0] not in targets]
    right_r += rng.sample(rest, 2)
    keys = [rkey(r) for r in right_r]
    if len(set(keys)) < 6:
        raise Retry
    rng.shuffle(right_r)
    rt = [rx_scheme(r) for r in right_r]
    if len(set(rt)) < 6:
        raise Retry
    for t in targets:
        if sum(r['rhs'][0] == t for r in right_r) != 1:
            raise Retry
    lt = [nm(f, rng) for f in targets]
    q = mq('веществом и схемой реакции, в результате которой может быть получено это вещество', 'ВЕЩЕСТВО',
           'СХЕМА РЕАКЦИИ')
    ans = [next(i for i, r in enumerate(right_r) if r['rhs'][0] == t) for t in targets]
    e = '; '.join(rx_eq(right_r[i]) for i in ans) + '.'
    return match_card(pid, rng, q, lt, rt, ans, e, {'left': targets, 'right': [list(rkey(r)) for r in right_r]},
                      eqs=[eqt(right_r[i]) for i in ans])


SYN14 = [r for r in RX if _ok_rx(r) and SUB[r['rhs'][0]]['cls'] == 'углеводород'] + \
        [r for r in RX if r['lhs'][0] in ('Al4C3', 'CaC2') and r['rhs'][0] in SUB and SUB[r['rhs'][0]].get('org')]
SYN15 = [r for r in RX if _ok_rx(r) and SUB[r['rhs'][0]]['cls'] in O_CLS - {'алкоголят', 'фенолят'}]


@proto('ch-ege-14-synthesis', 'ЕГЭ', 14, 'Углеводород → схема реакции, которой его можно получить',
       invariant='способы получения углеводородов: Вюрц, Дюма, дегидрирование, дегидрогалогенирование, '
                 'дегалогенирование, гидрирование, карбиды, крекинг',
       varies='четыре углеводорода, шесть схем (две — лишние)',
       answer_rule='для каждой схемы записать продукт и сопоставить с веществами',
       mistakes=['CH₃COONa + NaOH (сплавление) даёт метан, а не этан', 'гидролиз карбида кальция — ацетилен, '
                                                                     'карбида алюминия — метан'],
       solve=_solve_synth, kind='dict', kes=KES14,
       fidelity=fid(MATCH4, 'П', 6, '«углеводород — возможный способ получения» (метан, этан, этин, этилен; банк №14)',
                    'схемы, дающие гомолог или изомер', KES14, SC2))
def g14_synth(rng):
    return _gen_synth('ch-ege-14-synthesis', rng, SYN14)


@proto('ch-ege-15-scheme-product', 'ЕГЭ', 15, 'Схема реакции кислородсодержащего вещества → главный продукт',
       invariant='свойства спиртов, фенола, альдегидов, кетонов, кислот, эфиров, солей: окисление, восстановление, '
                 'дегидратация, этерификация, гидролиз, декарбоксилирование',
       varies='четыре схемы из ≈ 300 реакций O-содержащих веществ; продукты — названиями или формулами',
       answer_rule='определить тип реакции по реагенту и условиям и записать продукт',
       mistakes=['вторичный спирт окисляется до кетона', 'при t < 140 °C спирт даёт простой эфир, при t > 140 °C — алкен',
                 'щелочной гидролиз эфира даёт соль, а не кислоту'],
       solve=_solve_scheme_prod, kind='dict', kes=KES15,
       fidelity=fid(MATCH4, 'П', 6, 'схемы из банка №15: CH₃COOH + NaHCO₃, C₆H₅COONa + NaOH (t), HOCH₂CH₂OH + Cu(OH)₂',
                    'соль/кислота, альдегид/кетон, эфир/алкен в зависимости от условий', KES15, SC2))
def g15_scheme(rng):
    return _gen_scheme_prod('ch-ege-15-scheme-product', rng, POOL15)


def _solve_subst_x(p):
    out = {}
    for i, (sg, prod) in enumerate(p['left']):
        good = []
        for n, f in enumerate(p['right']):
            lhs = [f] + list(sg[0])
            if any(r['lhs'] == lhs and r.get('cond', '') == sg[1] and r.get('medium', '') == sg[2]
                   and r['rhs'][0] == prod for r in D.REACTIONS):
                good.append(n)
        out[LET[i]] = str(good[0] + 1)
    return out


def _gen_subst_x(pid, rng, pool):
    rs = pick_distinct(rng, pool, 4, key=lambda r: (sig(r), r['rhs'][0]))
    subs = list(dict.fromkeys(r['lhs'][0] for r in rs))
    conf = set()
    for f in subs:
        conf.update(g for g in ORG if (brutto(g) == brutto(f) or SUB[g]['hom'] == SUB[f]['hom']
                                       or parse_formula(g).get('C') == parse_formula(f).get('C'))
                    and g != f and SUB[g]['cls'] in O_CLS | {'углеводород'} and g not in _POOL10_SKIP)
    conf -= set(subs)
    need = 6 - len(subs)
    if need < 0 or len(conf) < need:
        raise Retry
    right = subs + rng.sample(sorted(conf), need)
    rng.shuffle(right)
    for r in rs:  # ровно один подходящий субстрат (по базе) и ни один отвлекающий не даёт тот же продукт
        n = sum(any(x['lhs'] == [f] + r['lhs'][1:] and x.get('cond', '') == r.get('cond', '') and
                    x.get('medium', '') == r.get('medium', '') and x['rhs'][0] == r['rhs'][0] for x in RX)
                for f in right)
        if n != 1:
            raise Retry
    rt = [nm(f, rng) for f in right]
    if len(set(rt)) < 6:
        raise Retry
    lt = [f'X + {sig_label(r)} → {nm(r["rhs"][0])}' if sig_label(r) and reagent_label(r) else
          f'X —({scheme_cond(r)})→ {nm(r["rhs"][0])}' for r in rs]
    q = mq('схемой реакции и веществом X, принимающим в ней участие', 'СХЕМА РЕАКЦИИ', 'ВЕЩЕСТВО X')
    ans = [right.index(r['lhs'][0]) for r in rs]
    return match_card(pid, rng, q, lt, rt, ans, '; '.join(rx_eq(r) for r in rs) + '.',
                      {'left': [[list(sig(r)), r['rhs'][0]] for r in rs], 'right': right}, eqs=[eqt(r) for r in rs])


@proto('ch-ege-15-substance-x', 'ЕГЭ', 15, 'Схема «X + реагент → продукт»: найти исходное вещество X',
       invariant='восстановить исходное вещество по реагенту, условиям и продукту (обратный ход рассуждения)',
       varies='четыре схемы, шесть кандидатов X (изомеры и гомологи правильных)',
       answer_rule='понять тип реакции и «отмотать» её назад',
       mistakes=['ацетон получают окислением пропанола-2, а не пропанола-1', 'гидратация пропина, а не пропаналя, '
                                                                             'даёт ацетон'],
       solve=_solve_subst_x, kind='dict', kes=KES15,
       fidelity=fid(MATCH4, 'П', 6, 'демо 2027 №15: X + Cu(OH)₂ → уксусная кислота, X + H₂SO₄ → диэтиловый эфир, '
                                   'X + KMnO₄/H⁺ → ацетон', 'изомеры-кандидаты (пропанол-1/-2, пропаналь/пропин)',
                    KES15, SC2))
def g15_subst(rng):
    return _gen_subst_x('ch-ege-15-substance-x', rng, [r for r in POOL15 + [x for x in RX if _ok_rx(x) and
                                                                           SUB[x['rhs'][0]]['cls'] in O_CLS]
                                                       if len(SCHEME[rkey(r)]) == 1])


@proto('ch-ege-15-reagent-x', 'ЕГЭ', 15, 'Превращение O-содержащего вещества → реагент X',
       invariant='по исходному веществу и продукту подобрать реагент/условия (CuO, KMnO₄, H₂SO₄ конц., HBr, NaOH, Na, '
                 'H₂ …)',
       varies='четыре превращения спиртов, альдегидов, кислот, эфиров, солей; шесть реагентов',
       answer_rule='сравнить исходное вещество и продукт: окисление, восстановление, замещение, гидролиз',
       mistakes=['CuO окисляет первичный спирт до альдегида, KMnO₄ (H⁺) — до кислоты', 'натрий и NaOH дают разные '
                                                                                        'продукты со спиртом'],
       solve=_solve_reagent, kind='dict', kes=KES15,
       fidelity=fid(MATCH4, 'П', 6, '«схема — вещество X (реагент)»: CH₃CHO → CH₃CH₂OH, CH₃OH → HCHO (банк №15)',
                    'реагенты с похожим действием', KES15, SC2))
def g15_reagent(rng):
    return _gen_reagent('ch-ege-15-reagent-x', rng, R15)


@proto('ch-ege-15-synthesis', 'ЕГЭ', 15, 'Кислородсодержащее вещество → схема его получения',
       invariant='важнейшие способы получения спиртов, альдегидов, кетонов, кислот, эфиров',
       varies='четыре вещества, шесть схем',
       answer_rule='для каждой схемы записать продукт и сопоставить',
       mistakes=['гидратация алкена даёт спирт, алкина — альдегид/кетон', 'окисление вторичного спирта — кетон'],
       solve=_solve_synth, kind='dict', kes=KES15,
       fidelity=fid(MATCH4, 'П', 6, '«вещество — способ получения» (этанол, этаналь, уксусная кислота, этиленгликоль; '
                                   'банк №15)', 'схемы, дающие изомер или гомолог', KES15, SC2))
def g15_synth(rng):
    return _gen_synth('ch-ege-15-synthesis', rng, SYN15)


EST_H = [r for r in RX if r['lhs'][0] in SUB and SUB[r['lhs'][0]]['cls'] == 'сложный эфир'
         and 'гидролиза' in r['type'] and 'N' not in parse_formula(r['lhs'][0])
         and SUB[r['lhs'][0]]['hom'] == 'сложные эфиры']


def _pair_txt(fs):
    order = {'соль карбоновой кислоты': 0, 'карбоновая кислота': 0, 'фенолят': 2, 'фенол': 2, 'спирт': 1, 'альдегид': 1}
    return ' и '.join(nm(f) for f in sorted(fs, key=lambda f: (order.get(SUB[f]['cls'], 3), f)))


def _solve_ester(p):
    out = {}
    for i, (lhs, cond) in enumerate(p['left']):
        prods = None
        for r in D.REACTIONS:
            if r['lhs'] == list(lhs) and r.get('cond', '') == cond:
                prods = sorted(x for x in r['rhs'] if x in SUB and SUB[x].get('org'))
        out[LET[i]] = str(p['right'].index(prods) + 1)
    return out


@proto('ch-ege-15-ester-hydrolysis', 'ЕГЭ', 15, 'Гидролиз сложного эфира в кислой и щелочной среде → продукты',
       invariant='кислотный гидролиз: кислота + спирт; щелочной: соль + спирт (фенол → фенолят, виниловый спирт → '
                 'альдегид)',
       varies='эфир (формиаты, ацетаты, пропионаты, бензоаты, фенилацетат, винилацетат), среда',
       answer_rule='разорвать связь C(O)–O, в щёлочи записать соль кислоты',
       mistakes=['в щелочной среде записана кислота', 'гидролиз винилацетата даёт ацетальдегид, а не виниловый спирт',
                 'кислотная и спиртовая части эфира перепутаны'],
       solve=_solve_ester, kind='dict', kes=KES15,
       fidelity=fid(MATCH4, 'П', 6, '«схема гидролиза сложного эфира — продукты» (HCOOC₂H₅, C₃H₆O₂ + H₂O/NaOH; банк №15)',
                    'пары продуктов со «зеркальными» частями (метилацетат/этилформиат)', KES15, SC2))
def g15_ester(rng):
    rs = pick_distinct(rng, EST_H, 4, key=lambda r: tuple(sorted(r['rhs'])))
    pairs = [sorted(x for x in r['rhs'] if x in SUB and SUB[x].get('org')) for r in rs]
    uniq = [list(x) for x in dict.fromkeys(tuple(x) for x in pairs)]
    conf = []
    for r in EST_H:
        pr = sorted(x for x in r['rhs'] if x in SUB and SUB[x].get('org'))
        if pr not in uniq and pr not in conf:
            conf.append(pr)
    # ловушка: «зеркальная» пара — кислота вместо соли
    need = 6 - len(uniq)
    if len(conf) < need:
        raise Retry
    right = uniq + rng.sample(conf, need)
    rng.shuffle(right)
    rt = [_pair_txt(x) for x in right]
    lt = [rx_scheme(r) for r in rs]
    if len(set(rt)) < 6 or len(set(lt)) < 4:
        raise Retry
    q = mq('схемой реакции гидролиза сложного эфира и продуктами, которые преимущественно образуются в этой реакции',
           'СХЕМА РЕАКЦИИ', 'ПРОДУКТЫ РЕАКЦИИ')
    ans = [right.index(x) for x in pairs]
    return match_card('ch-ege-15-ester-hydrolysis', rng, q, lt, rt, ans, '; '.join(rx_eq(r) for r in rs) + '.',
                      {'left': [[r['lhs'], r.get('cond', '')] for r in rs], 'right': right}, eqs=[eqt(r) for r in rs])


FIX15 = ['CH3CH(OH)CH3', 'C2H5OH', 'CH3OH', 'CH3CH2CH2OH', 'CH3COOH', 'HCOOH', 'C6H5OH', 'CH3CHO', 'CH3COCH3',
         'CH3CH2COOH', 'C2H4(OH)2', 'C3H5(OH)3', 'HCHO']


def _solve_fix15(p):
    out = {}
    for i, sg in enumerate(p['left']):
        lhs = [p['f']] + list(sg[0])
        prods = {r['rhs'][0] for r in D.REACTIONS if r['lhs'] == lhs and r.get('cond', '') == sg[1]
                 and r.get('medium', '') == sg[2]}
        out[LET[i]] = str([n for n, g in enumerate(p['right']) if g in prods][0] + 1)
    return out


@proto('ch-ege-15-one-substance', 'ЕГЭ', 15, 'Одно вещество с разными реагентами → продукты',
       invariant='одно кислородсодержащее вещество реагирует с четырьмя разными реагентами — продукты различаются',
       varies='вещество (пропанол-2, этанол, уксусная кислота, фенол, ацетальдегид …), четыре реагента с условиями',
       answer_rule='для каждого реагента определить тип реакции и продукт',
       mistakes=['с HCl спирт даёт хлоралкан, с Na — алкоголят', 'с Cu(OH)₂ при нагревании альдегид окисляется до '
                                                                 'кислоты'],
       solve=_solve_fix15, kind='dict', kes=KES15,
       fidelity=fid(MATCH4, 'П', 6, '«вещество — продукт реакции данного вещества с пропанолом-2» (банк №15)',
                    'продукты одного субстрата в разных условиях', KES15, SC2))
def g15_one(rng):
    f = rng.choice(FIX15)
    rs = [r for r in RX if r['lhs'][0] == f and _ok_rx(r)]
    if len({sig(r) for r in rs}) < 4:
        raise Retry
    rs = pick_distinct(rng, rs, 4, key=sig)
    prods = list(dict.fromkeys(r['rhs'][0] for r in rs))
    conf = [g for g in ORG if g not in prods and (SUB[g]['hom'] in {SUB[x]['hom'] for x in prods} or
                                                  brutto(g) in {brutto(x) for x in prods}) and g not in _POOL10_SKIP
            and parse_formula(g).get('C', 0) <= 8]
    if len(conf) < 6 - len(prods):
        raise Retry
    right = prods + rng.sample(conf, 6 - len(prods))
    rng.shuffle(right)
    rt = [nm(g) for g in right]
    if len(set(rt)) < 6:
        raise Retry
    lt = [sig_label(r) for r in rs]
    n = nm(f, rng)
    q = mq(f'реагентом и органическим продуктом, который преимущественно образуется при взаимодействии этого '
           f'реагента с веществом «{n}»', 'РЕАГЕНТ', 'ПРОДУКТ РЕАКЦИИ')
    ans = [right.index(r['rhs'][0]) for r in rs]
    return match_card('ch-ege-15-one-substance', rng, q, lt, rt, ans, '; '.join(rx_eq(r) for r in rs) + '.',
                      {'f': f, 'left': [list(sig(r)) for r in rs], 'right': right}, eqs=[eqt(r) for r in rs])


# ================================================================= задания 16 и 32: генетическая связь (граф превращений)

KES16 = ['3.20']
EDGE_RX = [r for r in RX if _ok_rx(r) and SUB[r['lhs'][0]]['cls'] not in ('ацетиленид',)
           and SUB[r['rhs'][0]]['cls'] not in ('ацетиленид', 'соль амина') and SUB[r['lhs'][0]]['hom'] != 'дипептиды'
           and SUB[r['rhs'][0]]['hom'] != 'дипептиды' and r['rhs'][0] != r['lhs'][0]]
OUT = defaultdict(list)
for _r in EDGE_RX:
    OUT[_r['lhs'][0]].append(_r)


def edge_db(a, b, label=None):
    """Есть ли в базе одностадийное превращение a → b (при необходимости — с данной подписью реагента)."""
    for r in D.REACTIONS:
        if r['lhs'][0] == a and r['rhs'][0] == b and (label is None or sig_label(dict(r, k=None)) == label):
            return True
    return False


def _walk(rng, n, start=None, allow=None):
    """Случайная цепочка из n превращений без повторов веществ."""
    for _ in range(60):
        a = start or rng.choice(sorted(OUT))
        path, seen = [], {a}
        cur = a
        for _ in range(n):
            opts_ = [r for r in OUT.get(cur, []) if r['rhs'][0] not in seen and (allow is None or allow(r))]
            if not opts_:
                break
            r = rng.choice(opts_)
            path.append(r)
            cur = r['rhs'][0]
            seen.add(cur)
        if len(path) == n:
            return path
    raise Retry


XY = ['X', 'Y']
TWO16 = 'пять вариантов, ответ — две цифры: номер вещества X и номер вещества Y (порядок важен)'


def _solve16_rg(p):
    a, b, c = p['chain']
    out = {}
    for key, (x, y) in zip(XY, ((a, b), (b, c))):
        good = [n for n, L in enumerate(p['right']) if edge_db(x, y, L)]
        out[key] = str(good[0] + 1)
    return out


@proto('ch-ege-16-reagents', 'ЕГЭ', 16, 'Схема A →X→ B →Y→ C: определить реагенты X и Y',
       invariant='по исходному веществу и продукту каждой стадии подобрать реагент (генетическая связь классов)',
       varies='цепочки из двух стадий по базе (≈ 800 превращений), пять реагентов (три лишних — реагенты соседних '
              'превращений)',
       answer_rule='для каждой стадии найти единственный реагент, дающий нужный продукт',
       mistakes=['CuO окисляет спирт до альдегида, а KMnO₄ (H⁺) — до кислоты', 'водный и спиртовой раствор щёлочи',
                 'Ag₂O (NH₃) и Cu(OH)₂ окисляют альдегид, но не спирт'],
       solve=_solve16_rg, kind='dict', kes=KES16,
       fidelity=fid(TWO16, 'П', 3, 'демо 2027 №16: C₂H₄ →X→ C₂H₅OH →Y→ CH₃CHO (H₂O/H⁺, CuO); банк: CH₂Br–CH₂Br → C₂H₂ → '
                                   'CH₃CHO', 'реагенты с похожим действием на соседнюю стадию', KES16, SC1))
def g16_reagents(rng):
    r1, r2 = _walk(rng, 2)
    a, b, c = r1['lhs'][0], r1['rhs'][0], r2['rhs'][0]
    l1, l2 = sig_label(r1), sig_label(r2)
    if l1 == l2 or a == c:
        raise Retry
    pool = sorted({sig_label(r) for r in OUT.get(a, []) + OUT.get(b, []) + rng.sample(EDGE_RX, 20)} - {l1, l2})
    if len(pool) < 3:
        raise Retry
    right = [l1, l2] + rng.sample(pool, 3)
    rng.shuffle(right)
    for x, y in ((a, b), (b, c)):
        if sum(any(r['lhs'][0] == x and r['rhs'][0] == y and sig_label(r) == L for r in RX) for L in right) != 1:
            raise Retry
    disp = lambda f: eqv(f) if rng.random() < 0.6 else nm(f)
    q = (f'Задана схема превращений веществ: {disp(a)} —X→ {disp(b)} —Y→ {disp(c)}.\n'
         'Определите, какие из указанных веществ являются веществами X и Y.\n'
         'Запишите в таблицу номера выбранных веществ под соответствующими буквами.')
    e = f'{rx_eq(r1)}; {rx_eq(r2)}.'
    return match_card('ch-ege-16-reagents', rng, q, ['вещество X', 'вещество Y'], right,
                      [right.index(l1), right.index(l2)], e, {'chain': [a, b, c], 'right': right},
                      eqs=[eqt(r1), eqt(r2)], lids=XY)


def _solve16_mid(p):
    chain = p['chain']
    out = {}
    for key, (x, y) in zip(XY, ((chain[0], chain[2]), (chain[2], chain[4]))):
        good = [n for n, f in enumerate(p['right']) if edge_db(x, f) and edge_db(f, y)]
        out[key] = str(good[0] + 1)
    return out


@proto('ch-ege-16-intermediates', 'ЕГЭ', 16, 'Схема A → X → B → Y → C: определить промежуточные вещества',
       invariant='найти вещество, которое можно получить из предыдущего и превратить в следующее за одну стадию',
       varies='цепочки из четырёх стадий по базе, пять веществ (три лишних — получаются только из одного соседа)',
       answer_rule='проверить для кандидата обе стадии: «из предыдущего» и «в следующее»',
       mistakes=['выбрано вещество, которое получается из A, но не превращается в B', 'пропущено изменение углеродного '
                                                                                   'скелета (Вюрц, декарбоксилирование)'],
       solve=_solve16_mid, kind='dict', kes=KES16,
       fidelity=fid(TWO16, 'П', 3, 'банк №16: CH₄ → X → CH₃CHO → Y → CH₃COOCH₃; бромэтан → X → этаналь → Y → метилацетат',
                    'кандидаты, связанные только с одним из соседей', KES16, SC1))
def g16_mid(rng):
    path = _walk(rng, 4)
    chain = [path[0]['lhs'][0]] + [r['rhs'][0] for r in path]
    x, y = chain[1], chain[3]
    cand = set()
    for f in (chain[0], chain[2]):
        cand.update(r['rhs'][0] for r in OUT.get(f, []))
    cand.update(r['lhs'][0] for r in EDGE_RX if r['rhs'][0] in (chain[2], chain[4]))
    cand -= set(chain)
    bad = [f for f in cand if not ((edge_db(chain[0], f) and edge_db(f, chain[2])) or
                                   (edge_db(chain[2], f) and edge_db(f, chain[4])))]
    if len(bad) < 3:
        raise Retry
    right = [x, y] + rng.sample(sorted(bad), 3)
    rng.shuffle(right)
    for s_, t_ in ((chain[0], chain[2]), (chain[2], chain[4])):
        if sum(edge_db(s_, f) and edge_db(f, t_) for f in right) != 1:
            raise Retry
    names = [nm(f, rng) for f in right]
    if len(set(names)) < 5:
        raise Retry
    q = (f'Задана схема превращений веществ: {nm(chain[0])} → X → {nm(chain[2])} → Y → {nm(chain[4])}.\n'
         'Определите, какие из указанных веществ являются веществами X и Y.\n'
         'Запишите в таблицу номера выбранных веществ под соответствующими буквами.')
    e = '; '.join(rx_eq(r) for r in path) + '.'
    return match_card('ch-ege-16-intermediates', rng, q, ['вещество X', 'вещество Y'], names,
                      [right.index(x), right.index(y)], e, {'chain': chain, 'right': right},
                      eqs=[eqt(r) for r in path], lids=XY)


def _solve16_ends(p):
    b = p['b']
    out = {}
    good_x = [n for n, f in enumerate(p['right']) if edge_db(f, b, p['l1'])]
    good_y = [n for n, f in enumerate(p['right']) if edge_db(b, f, p['l2'])]
    out['X'] = str(good_x[0] + 1)
    out['Y'] = str(good_y[0] + 1)
    return out


@proto('ch-ege-16-start-end', 'ЕГЭ', 16, 'Схема X →(реагент)→ B →(реагент)→ Y: исходное вещество и продукт',
       invariant='по реагентам на стрелках восстановить исходное вещество и продукт второй стадии',
       varies='цепочки из двух стадий, реагенты с условиями на стрелках, пять кандидатов',
       answer_rule='X — вещество, которое данным реагентом превращается в B; Y — продукт реакции B со вторым реагентом',
       mistakes=['перепутаны прямое и обратное направление стадии', 'не учтены условия (t, катализатор, среда)'],
       solve=_solve16_ends, kind='dict', kes=KES16,
       fidelity=fid(TWO16, 'П', 3, 'банк №16: X →(Cl₂)→ … →(водн. NaOH)→ Y; X →(Zn)→ этилен →(KMnO₄, H₂O)→ Y',
                    'кандидаты, реагирующие с тем же реагентом, но с другим продуктом', KES16, SC1))
def g16_ends(rng):
    r1, r2 = _walk(rng, 2)
    x, b, y = r1['lhs'][0], r1['rhs'][0], r2['rhs'][0]
    l1, l2 = sig_label(r1), sig_label(r2)
    cand = {r['lhs'][0] for r in EDGE_RX if sig_label(r) == l1} | {r['rhs'][0] for r in EDGE_RX if sig_label(r) == l2}
    cand |= {g for g in ORG if brutto(g) in (brutto(x), brutto(y)) and g not in _POOL10_SKIP}
    cand -= {x, b, y}
    bad = [f for f in cand if not edge_db(f, b, l1) and not edge_db(b, f, l2) and f in SUB and SUB[f].get('org')]
    if len(bad) < 3:
        raise Retry
    right = [x, y] + rng.sample(sorted(bad), 3)
    rng.shuffle(right)
    if sum(edge_db(f, b, l1) for f in right) != 1 or sum(edge_db(b, f, l2) for f in right) != 1:
        raise Retry
    names = [nm(f, rng) for f in right]
    if len(set(names)) < 5 or not l1 or not l2:
        raise Retry
    q = (f'Задана схема превращений веществ: X —({l1})→ {nm(b)} —({l2})→ Y.\n'
         'Определите, какие из указанных веществ являются веществами X и Y.\n'
         'Запишите в таблицу номера выбранных веществ под соответствующими буквами.')
    return match_card('ch-ege-16-start-end', rng, q, ['вещество X', 'вещество Y'], names, [right.index(x),
                                                                                           right.index(y)],
                      f'{rx_eq(r1)}; {rx_eq(r2)}.', {'b': b, 'l1': l1, 'l2': l2, 'right': right},
                      eqs=[eqt(r1), eqt(r2)], lids=XY)


# -------- 32: цепочка из пяти превращений (проверяемый шаг: вещества X₁–X₄)
KES32 = ['3.20', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13', '3.14', '3.15', '3.16']
XL = ['X₁', 'X₂', 'X₃', 'X₄']
THEMES32 = {
    'hc': ('углеводороды и галогенпроизводные', lambda f: SUB[f]['cls'] in HC_CLS),
    'o': ('кислородсодержащие соединения', lambda f: SUB[f]['cls'] in O_CLS | HC_CLS),
    'ar': ('производные бензола', lambda f: 'C6H' in f or 'c1ccccc1' in SMI.get(f, '')),
    'n': ('азотсодержащие соединения', lambda f: True),
}


def _solve32(p):
    """Прогон цепочки заново: из известного начала по подписям реагентов (однозначный продукт каждой стадии)."""
    cur = p['start']
    got = []
    for L in p['labels']:
        nxt = {r['rhs'][0] for r in D.REACTIONS if r['lhs'][0] == cur and sig_label(dict(r, k=None)) == L}
        cur = sorted(nxt)[0]
        got.append(cur)
    out = {}
    for i in range(4):
        out[XL[i]] = str(p['right'].index(got[i]) + 1)
    return out


def _gen32(pid, rng, theme):
    name, ok = THEMES32[theme]
    path = _walk(rng, 5, allow=lambda r: ok(r['rhs'][0]) and ok(r['lhs'][0]))
    chain = [path[0]['lhs'][0]] + [r['rhs'][0] for r in path]
    if theme == 'n' and not any('N' in parse_formula(f) for f in chain):
        raise Retry
    if theme == 'o' and sum(SUB[f]['cls'] in O_CLS for f in chain) < 3:
        raise Retry
    if theme == 'ar' and not all(ok(f) for f in chain):
        raise Retry
    labels = [sig_label(r) for r in path]
    # каждая стадия должна давать единственный продукт при данной подписи реагента
    for r, L in zip(path, labels):
        if len({x['rhs'][0] for x in RX if x['lhs'][0] == r['lhs'][0] and sig_label(x) == L}) != 1 or not L:
            raise Retry
    xs = chain[1:5]
    conf = set()
    for f in xs:
        conf.update(g for g in ORG if (brutto(g) == brutto(f) or SUB[g]['hom'] == SUB[f]['hom']) and g not in chain
                    and g not in _POOL10_SKIP and parse_formula(g).get('C', 0) <= 10)
    if len(conf) < 2:
        raise Retry
    right = xs + rng.sample(sorted(conf), 2)
    rng.shuffle(right)
    rt = [vw(f) for f in right]
    if len(set(rt)) < 6:
        raise Retry
    arrows = ''.join(f' —({L})→ ' + (XL[i] if i < 4 else eqv(chain[5])) for i, L in enumerate(labels))
    q = ('Напишите уравнения реакций, с помощью которых можно осуществить следующие превращения:\n'
         f'{eqv(chain[0])}{arrows}\n'
         'При написании уравнений реакций указывайте преимущественно образующиеся продукты, используйте структурные '
         'формулы органических веществ.\n'
         'Проверка в тренажёре: установите, какие вещества зашифрованы как X₁–X₄ (выберите их структурные формулы).')
    e = ' '.join(f'{i + 1}) {rx_eq(r)} ({cond_ru(r.get("cond", "")) or "без особых условий"});'
                 for i, r in enumerate(path))
    return match_card(pid, rng, q, XL, rt, [right.index(f) for f in xs], e,
                      {'start': chain[0], 'labels': labels, 'right': right}, eqs=[eqt(r) for r in path], lids=XL)


FID32 = dict(answer_format='в КИМ — развёрнутый ответ (5 уравнений, до 5 баллов: по 1 баллу за уравнение); в тренажёре '
                          'проверяется ключевой шаг — вещества X₁–X₄ (соответствие, четыре цифры)',
             style='«Напишите уравнения реакций, с помощью которых можно осуществить следующие превращения…» — как в КИМ',
             level='В', time_min=10, scale='цепочки из 5 стадий школьной органики с реагентами и условиями над стрелками, '
                                           'как в банке №32 (демо 2027: C₃H₄ → … → [Ag(NH₃)₂]OH → … CH₃Cl)',
             trap='условия определяют продукт (водн./спирт. щёлочь, t < / > 140 °C, среда окисления KMnO₄)',
             kes=KES32, score='5 баллов (по 1 за каждое верное уравнение)')


@proto('ch-ege-32-chain-hydrocarbons', 'ЕГЭ', 32, 'Цепочка превращений: углеводороды и галогенпроизводные',
       invariant='пять последовательных стадий; вещество каждой стадии определяется реагентом и условиями',
       varies='цепочки по базе (алканы, алкены, алкины, арены, галогенпроизводные), зашифрованные вещества X₁–X₄',
       answer_rule='идти по цепочке слева направо, записывая продукт каждой стадии; все уравнения уравнены',
       mistakes=['дегидрогалогенирование по Зайцеву', 'Вюрц удваивает радикал', 'гидрирование на Pd — до алкена'],
       solve=_solve32, kind='dict', kes=KES32, fidelity=FID32)
def g32_hc(rng):
    return _gen32('ch-ege-32-chain-hydrocarbons', rng, 'hc')


@proto('ch-ege-32-chain-oxygen', 'ЕГЭ', 32, 'Цепочка превращений: кислородсодержащие соединения',
       invariant='пять стадий с участием спиртов, альдегидов, кислот, эфиров, солей',
       varies='цепочки по базе, зашифрованные вещества X₁–X₄',
       answer_rule='окисление/восстановление, этерификация/гидролиз, декарбоксилирование — по реагентам на стрелках',
       mistakes=['в щелочной среде кислота существует в виде соли', 'CuO окисляет спирт до альдегида'],
       solve=_solve32, kind='dict', kes=KES32, fidelity=FID32)
def g32_o(rng):
    return _gen32('ch-ege-32-chain-oxygen', rng, 'o')


@proto('ch-ege-32-chain-aromatic', 'ЕГЭ', 32, 'Цепочка превращений: производные бензола',
       invariant='пять стадий с участием аренов, галогенаренов, фенола, бензойной кислоты, анилина',
       varies='цепочки по базе, зашифрованные вещества X₁–X₄',
       answer_rule='учитывать место атаки (кольцо/цепь) и среду окисления гомологов бензола',
       mistakes=['свет — замещение в боковой цепи, FeCl₃ — в кольце', 'в нейтральной среде KMnO₄ даёт бензоат калия'],
       solve=_solve32, kind='dict', kes=KES32, fidelity=FID32)
def g32_ar(rng):
    return _gen32('ch-ege-32-chain-aromatic', rng, 'ar')


@proto('ch-ege-32-chain-nitrogen', 'ЕГЭ', 32, 'Цепочка превращений с азотсодержащими веществами',
       invariant='пять стадий, среди продуктов — амины, соли аминов, аминокислоты, нитросоединения',
       varies='цепочки по базе, зашифрованные вещества X₁–X₄',
       answer_rule='амин + кислота → соль, соль амина + щёлочь → амин; галогенкислота + NH₃ → аминокислота',
       mistakes=['в кислой среде восстановление нитробензола даёт соль фениламмония', 'аминокислота с HCl — соль'],
       solve=_solve32, kind='dict', kes=KES32, fidelity=FID32)
def g32_n(rng):
    return _gen32('ch-ege-32-chain-nitrogen', rng, 'n')


recipe('ch-ege-32-full-answer', 'ЕГЭ', 32, 'Цепочка превращений — полный развёрнутый ответ (5 уравнений)',
       invariant='записать пять уравнений со структурными формулами и условиями; ионы/комплексы ([Ag(NH₃)₂]OH) и ОВР '
                 'с KMnO₄/K₂Cr₂O₇ — с коэффициентами',
       varies='цепочка (из генераторов ch-ege-32-chain-*), часть веществ дана формулами, часть — зашифрована',
       answer_rule='каждое уравнение — 1 балл: верные продукты, условия, коэффициенты',
       mistakes=['не уравнены ОВР с перманганатом', 'вместо структурных формул — молекулярные'],
       kind='llm', how='берём цепочку из ch-ege-32-chain-* (5 реакций базы с уравнениями); ИИ формулирует условие в стиле '
                       'КИМ (часть веществ открыта, часть — X₁…X₄) и эталон с уравнениями из базы',
       check='эталонные уравнения — из базы (коэффициенты проверены balance); ответ ученика сверяется поэлементно ИИ '
             'по критериям ФИПИ (1 балл за уравнение)',
       capacity=2000, example={'q': 'Напишите уравнения реакций, с помощью которых можно осуществить превращения: '
                                    'бромэтан —(KOH, спирт., t°)→ X₁ —(H₂O, H⁺)→ X₂ —(CuO, t°)→ X₃ —(Ag₂O, NH₃)→ X₄ '
                                    '—(C₂H₅OH, H₂SO₄)→ этилацетат',
                               'a': '1) C₂H₅Br + KOH → C₂H₄ + KBr + H₂O; 2) C₂H₄ + H₂O → C₂H₅OH; 3) C₂H₅OH + CuO → '
                                    'CH₃CHO + Cu + H₂O; 4) CH₃CHO + Ag₂O → CH₃COOH + 2Ag; 5) CH₃COOH + C₂H₅OH ⇄ '
                                    'CH₃COOC₂H₅ + H₂O',
                               'e': 'Каждая стадия определяется реагентом и условиями; 5 баллов за 5 верных уравнений.'},
       why='развёрнутый ответ (запись уравнений) автоматически проверяется только через эталон и ИИ', kes=KES32,
       fidelity=dict(FID32, answer_format='развёрнутый ответ: 5 уравнений реакций, как в КИМ 2027'))
