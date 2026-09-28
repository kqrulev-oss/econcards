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
from functools import lru_cache

from pc_core import (AR, Retry, balance, eq_str, fmt, match_opts, molar, opts, pcard, pretty, proto, recipe)
from pc_core import parse_formula as _parse_formula


@lru_cache(maxsize=None)
def _pf(f):
    return tuple(_parse_formula(f).items())


def parse_formula(f):
    """parse_formula с кэшем (возвращает новый словарь)."""
    return dict(_pf(f))

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


@lru_cache(maxsize=None)
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
    return cond_ru(clean_cond(c))


_KEEP = ('конц.', 'разб.', 'р-р', 'ж.', 'акт.', 'газ', 'красный')


def clean_cond(c):
    """Условия реакции без вложенных пояснений в скобках: 'Ni (Pt), t, p' → 'Ni, t, p'."""
    c = c.replace('Pd (Pb2+)', 'Pd/Pb2+').replace('P (красный)', 'Pкр.')
    c = re.sub(r'\s+\(([^()]*)\)', lambda m: f' ({m.group(1)})' if m.group(1) in _KEEP else '', c)
    c = re.sub(r'избыток [A-Za-zА-Яа-я0-9]+', 'изб.', c)
    c = re.sub(r'1 моль [A-Za-z0-9]+', '1 моль', c)
    c = re.sub(r'^t \(([^)]*)\)$', r'\1, t', c)
    return c.strip(' ,')


def eqv(f):
    s = SUB.get(f)
    if s and s.get('org') and s['hom'] in ('моносахариды', 'дисахариды'):
        return pretty(''.join(x + (str(n) if n > 1 else '') for x, n in sorted(parse_formula(f).items(),
                                                                                key=lambda t: 'CHON'.find(t[0]))))
    if s and s.get('org'):
        v = s.get('view') or pretty(f)
        if '(цикл)' in v:
            return pretty(hill(parse_formula(f))) + f' ({s["name"]})'
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


def canon(r):
    """Химическая «суть» реагента и условий: одинаковый ключ — одинаковое действие на вещество.
    Детали записи (Ni/Pt, «t°, p», избыток, катализатор гидратации) не различаются; различаются: вид реагента (rk),
    среда окисления KMnO₄, спиртовой/водный раствор (в rk), Pd (частичное гидрирование), холод (реакция Вагнера),
    t > / < 140 °C (в rk), свет/катализатор (в rk)."""
    c = r.get('cond', '')
    flags = []
    if 'Pd' in c:
        flags.append('Pd')
    if 'KMnO4' in r['lhs'] and ('0' in c and '°C' in c):
        flags.append('cold')
    rk = r.get('rk', '') or ('therm:' + clean_cond(c))
    rk = {'NaOHtp': 'NaOH', 'KOHtp': 'KOH'}.get(rk, rk)  # «t°, p» — тот же водный раствор щёлочи
    return (rk, r.get('medium', ''), ','.join(flags))


def canon_prods(sub, key):
    return {r['rhs'][0] for r in RX if r['lhs'][0] == sub and canon(r) == key}


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
    a = parse_formula(f)
    if sum(bool(x) for x in (a.get('O'), a.get('N'), a.get('Cl', 0) + a.get('Br', 0) + a.get('I', 0) + a.get('F', 0))) > 1:
        return None  # вещество подходит сразу к двум группам (хлоруксусная кислота, нитробензол)
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


@lru_cache(maxsize=None)
def _info(f):
    return D.smiles_info(SMI[f])


def info(f):
    return _info(f)


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


def _diene_kind(f):
    """Тип диена: кумулированный / сопряжённый / изолированный (по расстоянию между двойными связями)."""
    atoms, bonds = D.smiles_info(SMI[f])['graph']
    dbl = [(i, j) for i, j, o in bonds if o == 2]
    if len(dbl) != 2:
        return None
    (a1, b1), (a2, b2) = dbl
    if {a1, b1} & {a2, b2}:
        return 'cum'
    single = {frozenset((i, j)) for i, j, o in bonds if o == 1}
    return 'conj' if any(frozenset((x, y)) in single for x in (a1, b1) for y in (a2, b2)) else 'isol'


def homologs(a, b):
    """Гомологи: один класс (ряд), сходное строение, брутто различаются на k·CH₂ (k ≥ 1)."""
    if SUB[a]['hom'] != SUB[b]['hom'] or not cls_fine(a):
        return False
    if SUB[a]['hom'] == 'алкадиены' and _diene_kind(a) != _diene_kind(b):
        return False
    if cls_fine(a) in ('амины', 'одноатомные спирты') and _n_degree(a) != _n_degree(b):
        return False
    x, y = parse_formula(a), parse_formula(b)
    dc = y['C'] - x['C']
    if dc == 0:
        return False
    return all(y.get(e, 0) - x.get(e, 0) == {'C': dc, 'H': 2 * dc}.get(e, 0) for e in set(x) | set(y))


def _hom_loose(a, b):
    """Грубая проверка «похожи на гомологи»: один ряд и разница состава кратна CH₂ (без учёта степени замещения)."""
    if SUB[a]['hom'] != SUB[b]['hom']:
        return False
    x, y = parse_formula(a), parse_formula(b)
    dc = y['C'] - x['C']
    return dc != 0 and all(y.get(e, 0) - x.get(e, 0) == {'C': dc, 'H': 2 * dc}.get(e, 0) for e in set(x) | set(y))


def _solve_homologs(p):
    def hom_s(a, b):
        if SUB[a]['hom'] != SUB[b]['hom']:
            return False
        if cls_fine(a) in ('амины', 'одноатомные спирты') and _n_degree(a) != _n_degree(b):
            return False
        if SUB[a]['hom'] == 'алкадиены' and _diene_kind(a) != _diene_kind(b):
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
        # не больше двух веществ одного гомологического ряда: пара-гомологов ровно одна
        hc = Counter(SUB[f]['hom'] for f in items)
        if hc[SUB[good[0]]['hom']] != 2 or any(v > 2 for v in hc.values()):
            continue
        if sum(1 for i, a in enumerate(items) for b in items[i + 1:] if _hom_loose(a, b)) != 1:
            continue
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


def _n_degree(f):
    """Степень замещения: для амина — число атомов C при N; для спирта — число атомов C при атоме C, несущем OH
    (метанол считается первичным). По графу SMILES."""
    atoms, bonds = D.smiles_info(SMI[f])['graph']
    adj = defaultdict(list)
    for i, j, o in bonds:
        adj[i].append(j)
        adj[j].append(i)
    if any(a[0] == 'N' for a in atoms):
        n = next(i for i, a in enumerate(atoms) if a[0] == 'N')
        return sum(atoms[j][0] == 'C' for j in adj[n])
    o = next(i for i, a in enumerate(atoms) if a[0] == 'O' and len(adj[i]) == 1)
    c = adj[o][0]
    return max(1, sum(atoms[j][0] == 'C' for j in adj[c]))


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


SYN_GROUPS = [{'Na', 'K'}, {'NaOH', 'KOH'}, {'NaHCO3', 'Na2CO3', 'KHCO3', 'K2CO3'}, {'HCl', 'HBr'},
              {'KOHalc', 'NaOHalc'}, {'CH3OH', 'C2H5OH'}]


def syn_ok(rks):
    """В одном перечне нет однотипных реагентов (Na и K, NaOH и KOH …) и не больше одного «инертного»."""
    if any(len(g & set(rks)) > 1 for g in SYN_GROUPS):
        return False
    return sum(r in INERT for r in rks) <= 1


def _pick_rks(rng, subs, pool, lo=2, hi=3, want=True, n=5):
    ok = [rk for rk in pool if all(known(f, rk) is not None for f in subs)]
    if len(ok) < n:
        raise Retry
    for _ in range(60):
        rks = rng.sample(ok, n)
        if not syn_ok(rks):
            continue
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
    k = rng.randint(2, 3)
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
          'многоатомные спирты': 'двухатомный спирт', 'карбоновые кислоты': 'карбоновую кислоту'}


def acc(name):
    """Винительный падеж названия (дают … «пропановую кислоту», «ацетон», «глюкозу»)."""
    out = []
    for w in name.split(' '):
        m = re.match(r'^(.*?)(-[\d,]+)?$', w)
        b, t = m.group(1), m.group(2) or ''
        if b.endswith('ая'):
            b = b[:-2] + 'ую'
        elif b.endswith('а') and not b.endswith('ва'):
            b = b[:-1] + 'у'
        elif b.endswith('ва'):
            b = b[:-1] + 'у'
        out.append(b + t)
    return ' '.join(out)


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
    # вещество, которое реагирует, но продукт этой реакции в базе не записан, в вариантах не используем
    cand = [f for f in cand if known(f, rk) is False or prods[f]]
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
        target_txt = acc(nm(tf)) if tf != 'CO2' else 'углекислый газ'
    if len(good_set) < 2:
        raise Retry
    k = rng.randint(2, min(3, len(good_set)))
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
    good_r = pick_distinct(rng, by_p[tp], min(len(by_p[tp]), rng.randint(2, 3)), key=rkey)
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
    k = rng.randint(2, 3)
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
    if not syn_ok(rks):
        raise Retry
    rng.shuffle(rks)
    names = [_rk_text(rng, rk) for rk in rks]
    N = {f: nm(f, rng)}
    if want:
        q = q_many('два', 'вещества', rng.choice([f'с которыми {N[f]} вступает в реакцию при подходящих условиях',
                                              f'которые при подходящих условиях реагируют с веществом «{N[f]}»']))
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
    kind = rng.choice(['N', 'N', 'N', 'C', 'mix', 'mix'])  # азотные пары чаще отбраковываются — берём их чаще
    if kind == 'mix':  # вещества разных групп: аминокислота/амин против углевода/жира
        a, b = rng.choice(N_POOL), rng.choice(C_POOL)
        if rng.random() < 0.5:
            a, b = b, a
    else:
        a, b = rng.sample(N_POOL if kind == 'N' else C_POOL, 2)
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
    if 'O2' in fit and len(fit) > 2 and rng.random() < 0.7:
        fit = [x for x in fit if x != 'O2']
    rks = rng.sample(fit, 2) + rng.sample(rest_real, 3 - k_in) + rng.sample([r for r in rest if r in INERT], k_in)
    if not syn_ok(rks):
        raise Retry
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
        med = 'в кислой среде'
    g_ = gen(nm(sub, rng))
    if rng.random() < 0.5 or g_.startswith('вещества «'):
        what = f'которые образуются при гидролизе соединения {vw(sub)} {med}'
    else:
        what = f'которые образуются при гидролизе {g_} {med}'
    q = q_many('два', 'вещества', what)
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


_CANON_PRODS = defaultdict(set)
for _r in RX:
    _CANON_PRODS[(_r['lhs'][0], canon(_r))].add(_r['rhs'][0])


def _mixed(r):
    return ('реакция Вюрца' in r['type'] and len(r['lhs']) == 3) or 'крекинга' in r['type']


def _ok_rx(r):
    return (r['rhs'][0] in SUB and SUB[r['rhs'][0]].get('org') and 'горения' not in r['type'] and not _mixed(r)
            and len(SCHEME[rkey(r)]) == 1 and len(_CANON_PRODS[(r['lhs'][0], canon(r))]) == 1
            and r['lhs'][0] in SUB and SUB[r['lhs'][0]].get('org')
            and parse_formula(r['rhs'][0]).get('C', 0) <= 10 and r['rhs'][0] not in _POOL10_SKIP
            and SUB[r['rhs'][0]]['hom'] not in ('жиры',) and SUB[r['lhs'][0]]['hom'] not in ('жиры',))


POOL14 = [r for r in RX if _ok_rx(r) and SUB[r['lhs'][0]]['cls'] in HC_CLS]
# спирт + NH₃ (Al₂O₃) — промышленный способ, в заданиях банка 15 не встречается
POOL15 = [r for r in RX if _ok_rx(r) and SUB[r['lhs'][0]]['cls'] in O_CLS
          and not ('NH3' in r['lhs'] and 'Al2O3' in r.get('cond', ''))]
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
    key = (tuple(r['lhs']), r.get('cond', ''), r.get('medium', ''), r.get('rk', ''))
    if key not in _SIGL:
        _SIGL[key] = _sig_label(r)
    return _SIGL[key]


_SIGL = {}


def _sig_label(r):
    rg = reagent_label(r)
    c = scheme_cond(r)
    if not rg:
        return c
    if not c:
        return rg
    if c.startswith(rg):
        return c
    c = ', '.join(x for x in c.split(', ') if x and x not in rg)
    if not c:
        return rg
    return rg + (f', {c}' if '(' in c else f' ({c})')


def _canon_db(r):
    """canon() для строки базы (независимо от кэшей генератора)."""
    return list(canon(r))


def _solve_reagent(p):
    out = {}
    for i, (sub, prod) in enumerate(p['left']):
        ox = _ox_equiv(sub, prod)
        good = [n for n, keys in enumerate(p['right'])
                if any(r['lhs'][0] == sub and r['rhs'][0] == prod and _canon_db(r) in keys for r in D.REACTIONS)
                or any(tuple(k) in ox for k in keys)]
        out[LET[i]] = str(good[0] + 1)
    return out


_BY_LABEL = None


def label_canons():
    global _BY_LABEL
    if _BY_LABEL is None:
        _BY_LABEL = defaultdict(set)
        for r in RX:
            _BY_LABEL[sig_label(r)].add(canon(r))
    return _BY_LABEL


def _distinct_labels(labels):
    """Метки с разной химической сутью (не допускаем «H₂ (Ni, t°)» и «H₂ (Ni, t°, p)» в одном списке)."""
    by = label_canons()
    out, seen = [], set()
    for L in labels:
        ks = frozenset(by[L])
        if ks & seen:
            continue
        seen |= ks
        out.append(L)
    return out


_ALC = ('предельные одноатомные спирты', 'циклические спирты', 'ароматические спирты', 'непредельные спирты')
_KET = ('кетоны', 'циклические кетоны', 'ароматические кетоны')
_ALD = ('предельные альдегиды', 'ароматические альдегиды', 'непредельные альдегиды')
_ACID = ('предельные одноосновные карбоновые кислоты', 'ароматические карбоновые кислоты',
         'непредельные карбоновые кислоты')
_OX_KET = {('CuO', '', ''), ('KMnO4', 'кисл.', ''), ('KMnO4', 'нейтр.', ''), ('K2Cr2O7', '', ''), ('O2cat', '', '')}
_OX_ALD = {('CuO', '', ''), ('K2Cr2O7', '', ''), ('O2cat', '', '')}
_STRONG_ACIDS = {('HCl', '', ''), ('HBr', '', ''), ('H2SO4', '', ''), ('H2SO4t', '', ''), ('HNO3', '', '')}
_OX_ACID = {('KMnO4', 'кисл.', ''), ('K2Cr2O7', '', ''), ('O2cat', '', '')}


def _ox_equiv(sub, prod):
    """Окислители, каждый из которых по школьному курсу тоже осуществляет превращение sub → prod,
    даже если в базе записана реакция только с одним из них (вторичный спирт → кетон и т. п.)."""
    hs, hp = SUB[sub].get('hom'), SUB[prod].get('hom')
    if hs in _ALC and hp in _KET:
        return _OX_KET
    if hs in _ALC and hp in _ALD:
        return _OX_ALD
    if hs in _ALD and hp in _ACID:
        return _OX_ACID
    # соль → кислота (фенол, спирт): подходит любая сильная кислота, в т. ч. H₂SO₄ (конц.)
    if (SUB[sub].get('cls'), SUB[prod].get('cls')) in (('фенолят', 'фенол'), ('соль карбоновой кислоты', 'карбоновая кислота'),
                                                        ('алкоголят', 'спирт')):
        return _STRONG_ACIDS
    return set()


def _fits(sub, prod, L):
    ks = label_canons()[L]
    return (any(r['lhs'][0] == sub and r['rhs'][0] == prod and canon(r) in ks for r in RX)
            or bool(set(ks) & _ox_equiv(sub, prod)))


def _gen_reagent(pid, rng, pool):
    by_label = label_canons()
    rs = pick_distinct(rng, pool, 4, key=lambda r: (r['lhs'][0], r['rhs'][0]))
    labels = _distinct_labels(dict.fromkeys(sig_label(r) for r in rs))
    others = sorted({sig_label(r) for r in pool} - set(labels))
    rng.shuffle(others)
    right = _distinct_labels(labels + others)[:6]
    if len(right) < 6 or not set(sig_label(r) for r in rs) <= set(right):
        raise Retry
    rng.shuffle(right)
    # однозначность: для каждой строки подходит ровно один реагент из шести
    for r in rs:
        if sum(_fits(r['lhs'][0], r['rhs'][0], L) for L in right) != 1:
            raise Retry
    lt = [f'{eqv(r["lhs"][0])} —X→ {eqv(r["rhs"][0])}' for r in rs]
    q = mq('схемой превращения и реагентом X, который участвует в этом превращении', 'СХЕМА ПРЕВРАЩЕНИЯ', 'РЕАГЕНТ X')
    ans = [right.index(sig_label(r)) for r in rs]
    return match_card(pid, rng, q, lt, right, ans, '; '.join(rx_eq(r) for r in rs) + '.',
                      {'left': [[r['lhs'][0], r['rhs'][0]] for r in rs],
                       'right': [sorted(list(x) for x in by_label[L]) for L in right]},
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
    for i, (key, prod) in enumerate(p['left']):
        good = [n for n, f in enumerate(p['right'])
                if any(r['lhs'][0] == f and r['rhs'][0] == prod and _canon_db(r) == key for r in D.REACTIONS)]
        out[LET[i]] = str(good[0] + 1)
    return out


def _makes(f, prod, key):
    return any(x['lhs'][0] == f and x['rhs'][0] == prod and canon(x) == key for x in RX)


def _gen_subst_x(pid, rng, pool):
    rs = pick_distinct(rng, pool, 4, key=lambda r: (canon(r), r['rhs'][0]))
    subs = list(dict.fromkeys(r['lhs'][0] for r in rs))
    conf = set()
    for f in subs:
        conf.update(g for g in ORG if (brutto(g) == brutto(f) or SUB[g]['hom'] == SUB[f]['hom']
                                       or parse_formula(g).get('C') == parse_formula(f).get('C'))
                    and g != f and SUB[g]['cls'] in O_CLS | {'углеводород'} and g not in _POOL10_SKIP)
    conf -= set(subs)
    # отвлекающие не должны давать ни один из продуктов строк тем же реагентом
    conf = [g for g in sorted(conf) if not any(_makes(g, r['rhs'][0], canon(r)) for r in rs)]
    need = 6 - len(subs)
    if need < 0 or len(conf) < need:
        raise Retry
    right = subs + rng.sample(conf, need)
    rng.shuffle(right)
    for r in rs:  # ровно один подходящий кандидат
        if sum(_makes(f, r['rhs'][0], canon(r)) for f in right) != 1:
            raise Retry
    rt = [nm(f, rng) for f in right]
    if len(set(rt)) < 6:
        raise Retry
    lt = [f'X + {sig_label(r)} → {nm(r["rhs"][0])}' if sig_label(r) and reagent_label(r) else
          f'X —({scheme_cond(r)})→ {nm(r["rhs"][0])}' for r in rs]
    q = mq('схемой реакции и веществом X, принимающим в ней участие', 'СХЕМА РЕАКЦИИ', 'ВЕЩЕСТВО X')
    ans = [right.index(r['lhs'][0]) for r in rs]
    return match_card(pid, rng, q, lt, rt, ans, '; '.join(rx_eq(r) for r in rs) + '.',
                      {'left': [[list(canon(r)), r['rhs'][0]] for r in rs], 'right': right}, eqs=[eqt(r) for r in rs])


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
    rs = [r for r in RX if r['lhs'][0] == f and _ok_rx(r) and not ('NH3' in r['lhs'] and 'Al2O3' in r.get('cond', ''))]
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


def edge_db(a, b, keys=None):
    """Есть ли в базе одностадийное превращение a → b (при необходимости — реагентом с данной химической сутью)."""
    for r in D.REACTIONS:
        if r['lhs'][0] == a and r['rhs'][0] == b and (keys is None or _canon_db(r) in keys):
            return True
    if keys is not None and a in SUB and b in SUB and any(tuple(k) in _ox_equiv(a, b) for k in keys):
        return True
    return False


def keys_of(label):
    return sorted(list(k) for k in label_canons()[label])


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
        good = [n for n, keys in enumerate(p['right']) if edge_db(x, y, keys)]
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
    rng.shuffle(pool)
    right = _distinct_labels([l1, l2] + pool)[:5]
    if len(right) < 5 or l1 not in right or l2 not in right:
        raise Retry
    rng.shuffle(right)
    for x, y in ((a, b), (b, c)):
        if sum(_fits(x, y, L) for L in right) != 1:
            raise Retry
    disp = lambda f: eqv(f) if rng.random() < 0.6 else nm(f)
    q = (f'Задана схема превращений веществ: {disp(a)} —X→ {disp(b)} —Y→ {disp(c)}.\n'
         'Определите, какие из указанных веществ являются веществами X и Y.\n'
         'Запишите в таблицу номера выбранных веществ под соответствующими буквами.')
    e = f'{rx_eq(r1)}; {rx_eq(r2)}.'
    return match_card('ch-ege-16-reagents', rng, q, ['вещество X', 'вещество Y'], right,
                      [right.index(l1), right.index(l2)], e, {'chain': [a, b, c], 'right': [keys_of(L) for L in right]},
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
    good_x = [n for n, f in enumerate(p['right']) if edge_db(f, b, p['k1'])]
    good_y = [n for n, f in enumerate(p['right']) if edge_db(b, f, p['k2'])]
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
    k1, k2 = keys_of(l1), keys_of(l2)
    if len(canon_prods(b, canon(r2))) != 1:
        raise Retry
    cand = {r['lhs'][0] for r in EDGE_RX if sig_label(r) == l1} | {r['rhs'][0] for r in EDGE_RX if sig_label(r) == l2}
    cand |= {g for g in ORG if brutto(g) in (brutto(x), brutto(y)) and g not in _POOL10_SKIP}
    cand -= {x, b, y}
    bad = [f for f in cand if not edge_db(f, b, k1) and not edge_db(b, f, k2) and f in SUB and SUB[f].get('org')]
    if len(bad) < 3:
        raise Retry
    right = [x, y] + rng.sample(sorted(bad), 3)
    rng.shuffle(right)
    if sum(edge_db(f, b, k1) for f in right) != 1 or sum(edge_db(b, f, k2) for f in right) != 1:
        raise Retry
    names = [nm(f, rng) for f in right]
    if len(set(names)) < 5 or not l1 or not l2:
        raise Retry
    q = (f'Задана схема превращений веществ: X —({l1})→ {nm(b)} —({l2})→ Y.\n'
         'Определите, какие из указанных веществ являются веществами X и Y.\n'
         'Запишите в таблицу номера выбранных веществ под соответствующими буквами.')
    return match_card('ch-ege-16-start-end', rng, q, ['вещество X', 'вещество Y'], names, [right.index(x),
                                                                                           right.index(y)],
                      f'{rx_eq(r1)}; {rx_eq(r2)}.', {'b': b, 'k1': k1, 'k2': k2, 'right': right},
                      eqs=[eqt(r1), eqt(r2)], lids=XY)


def _solve16_fwd(p):
    cur = p['a']
    got = []
    for keys in p['keys']:
        nxt = {r['rhs'][0] for r in D.REACTIONS if r['lhs'][0] == cur and _canon_db(r) in keys}
        cur = sorted(nxt)[0]
        got.append(cur)
    return {'X': str(p['right'].index(got[0]) + 1), 'Y': str(p['right'].index(got[1]) + 1)}


@proto('ch-ege-16-forward', 'ЕГЭ', 16, 'Схема A →(реагент)→ X →(реагент)→ Y: продукты двух последовательных стадий',
       invariant='по исходному веществу и реагентам (с условиями) на стрелках определить продукты обеих стадий',
       varies='цепочки из двух стадий по базе, реагенты и условия, пять кандидатов (изомеры и продукты «соседних» '
              'условий)',
       answer_rule='провести первую реакцию, затем вторую с её продуктом',
       mistakes=['H₂SO₄ (конц.) при t > 140 °C даёт алкен, при t < 140 °C — простой эфир',
                 'гидратация по правилу Марковникова', 'продукт первой стадии спутан с изомером'],
       solve=_solve16_fwd, kind='dict', kes=KES16,
       fidelity=fid(TWO16, 'П', 3, 'банк №16: CH₃CH₂CH₂OH —(H₂SO₄, t°)→ X —(H₂O, H⁺)→ Y; CH₃COONa —(NaOH)→ X —(HNO₃)→ Y',
                    'изомерные продукты (пропанол-1/-2, 1-/2-бромпропан)', KES16, SC1))
def g16_forward(rng):
    r1, r2 = _walk(rng, 2)
    a, x, y = r1['lhs'][0], r1['rhs'][0], r2['rhs'][0]
    l1, l2 = sig_label(r1), sig_label(r2)
    if not l1 or not l2:
        raise Retry
    for r, L in ((r1, l1), (r2, l2)):
        ks = label_canons()[L]
        if len({z['rhs'][0] for z in RX if z['lhs'][0] == r['lhs'][0] and canon(z) in ks}) != 1:
            raise Retry
    conf = {g for g in ORG if (brutto(g) in (brutto(x), brutto(y)) or SUB[g]['hom'] in (SUB[x]['hom'], SUB[y]['hom']))
            and g not in (a, x, y) and g not in _POOL10_SKIP and parse_formula(g).get('C', 0) <= 10}
    conf |= {r['rhs'][0] for r in OUT.get(a, []) + OUT.get(x, [])} - {a, x, y}
    if len(conf) < 3:
        raise Retry
    right = [x, y] + rng.sample(sorted(conf), 3)
    rng.shuffle(right)
    names = [nm(f, rng) for f in right]
    if len(set(names)) < 5:
        raise Retry
    q = (f'Задана схема превращений веществ: {nm(a)} —({l1})→ X —({l2})→ Y.\n'
         'Определите, какие из указанных веществ являются веществами X и Y.\n'
         'Запишите в таблицу номера выбранных веществ под соответствующими буквами.')
    return match_card('ch-ege-16-forward', rng, q, ['вещество X', 'вещество Y'], names, [right.index(x), right.index(y)],
                      f'{rx_eq(r1)}; {rx_eq(r2)}.', {'a': a, 'keys': [keys_of(l1), keys_of(l2)], 'right': right},
                      eqs=[eqt(r1), eqt(r2)], lids=XY)


# -------- 32: цепочка из пяти превращений (проверяемый шаг: вещества X₁–X₄)
KES32 = ['3.20', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13', '3.14', '3.15', '3.16']
XL = ['X₁', 'X₂', 'X₃', 'реагент на стадии 3']
THEMES32 = {
    'hc': ('углеводороды и галогенпроизводные', lambda f: SUB[f]['cls'] in HC_CLS),
    'o': ('кислородсодержащие соединения', lambda f: SUB[f]['cls'] in O_CLS | HC_CLS),
    'ar': ('производные бензола', lambda f: 'C6H' in f or 'c1ccccc1' in SMI.get(f, '')),
    'n': ('азотсодержащие соединения', lambda f: True),
}
OXID = ('KMnO4', 'K2Cr2O7')


def _acid_base(r):
    return 'нейтрализации' in r['type'] or ('обмена' in r['type'] and 'гидролиза' not in r['type'])


def _chain32(p):
    """Прогон цепочки заново по химической сути реагентов (из базы, без кэшей генератора)."""
    cur = p['start']
    got = []
    for keys in p['keys']:
        nxt = {r['rhs'][0] for r in D.REACTIONS if r['lhs'][0] == cur and _canon_db(r) in keys}
        cur = sorted(nxt)[0]
        got.append(cur)
    return got


def _solve32(p):
    got = _chain32(p)
    x1, x2, s3, x3 = got[0], got[1], got[2], got[3]
    out = {}
    for lid, f in zip(['X₁', 'X₂', 'X₃'], (x1, x2, x3)):
        out[lid] = str(p['right'].index(['f', f]) + 1)
    good = [n for n, o in enumerate(p['right']) if o[0] == 'r' and edge_db(x2, s3, o[1])]
    out['R₃'] = str(good[0] + 1)
    return out


def _solve32_steps(p):
    got = [p['start']] + _chain32(p)
    out = []
    for i in p['ox']:
        r = next(r for r in D.REACTIONS if r['lhs'][0] == got[i] and r['rhs'][0] == got[i + 1]
                 and _canon_db(r) in p['keys'][i])
        kl, kr = balance(r['lhs'], r['rhs'])
        out.append(str(sum(kl) + sum(kr)))
    return out


def _reach_n():
    """Вещества, из которых за ≤ 3 стадии можно получить азотсодержащее (обратный поиск в ширину)."""
    back = defaultdict(set)
    for r in EDGE_RX:
        back[r['rhs'][0]].add(r['lhs'][0])
    front = {f for f in OUT if any('N' in parse_formula(r['rhs'][0]) for r in OUT[f])}
    seen = set(front)
    for _ in range(4):
        front = {x for f in front for x in back[f]} - seen
        seen |= front
    return sorted(seen)


REACH_N = _reach_n()
_BACK = defaultdict(list)
for _r in EDGE_RX:
    _BACK[_r['rhs'][0]].append(_r)
# для азотной темы добавлены стадии с солями аминов (амин + HCl → соль, соль + NaOH → амин, алкилирование)
EDGE_N = EDGE_RX + [r for r in RX if _ok_rx(r) and SUB[r['rhs'][0]]['cls'] == 'соль амина'
                    and SUB[r['lhs'][0]]['cls'] != 'соль амина' and r['rhs'][0] != r['lhs'][0]]
OUT_N, _BACK_N = defaultdict(list), defaultdict(list)
for _r in EDGE_N:
    OUT_N[_r['lhs'][0]].append(_r)
    _BACK_N[_r['rhs'][0]].append(_r)
N_EDGES = [r for r in EDGE_N if 'N' in parse_formula(r['rhs'][0]) and 'N' not in parse_formula(r['lhs'][0])]
_N_GROUPS = defaultdict(list)  # «азотные» стадии по классу продукта — чтобы тема не сводилась к одной цепочке
for _r in N_EDGES:
    _N_GROUPS[SUB[_r['rhs'][0]]['hom']].append(_r)


def _walk_n(rng, n, allow):
    """Цепочка, в которой азот появляется на 2–3-й стадии: от «азотной» стадии назад и вперёд."""
    for _ in range(300):
        mid = rng.choice(_N_GROUPS[rng.choice(sorted(_N_GROUPS))])
        if not allow(mid):
            continue
        k = rng.choice([0, 1, 1, 2])  # сколько стадий до неё
        path, seen, ok_ = [mid], {mid['lhs'][0], mid['rhs'][0]}, True
        cur = mid['lhs'][0]
        for _ in range(k):
            opts_ = [r for r in _BACK_N.get(cur, []) if r['lhs'][0] not in seen and allow(r)]
            if not opts_:
                ok_ = False
                break
            r = rng.choice(opts_)
            path.insert(0, r)
            seen.add(r['lhs'][0])
            cur = r['lhs'][0]
        cur = mid['rhs'][0]
        while ok_ and len(path) < n:
            opts_ = [r for r in OUT_N.get(cur, []) if r['rhs'][0] not in seen and allow(r)]
            if not opts_:
                ok_ = False
                break
            r = rng.choice(opts_)
            path.append(r)
            seen.add(r['rhs'][0])
            cur = r['rhs'][0]
        if ok_ and len(path) == n:
            return path
    raise Retry


def _gen32(pid, rng, theme):
    name, ok = THEMES32[theme]
    allow = lambda r: ok(r['rhs'][0]) and ok(r['lhs'][0]) and 'Ag2O' not in r['lhs'] \
        and not ('NH3' in r['lhs'] and 'Al2O3' in r.get('cond', ''))
    path = _walk_n(rng, 5, allow) if theme == 'n' else _walk(rng, 5, allow=allow)
    chain = [path[0]['lhs'][0]] + [r['rhs'][0] for r in path]
    if theme == 'n' and sum('N' in parse_formula(f) for f in chain[:5]) < 2:
        raise Retry
    if theme == 'o' and sum(SUB[f]['cls'] in O_CLS for f in chain) < 3:
        raise Retry
    if theme == 'ar' and not all(ok(f) for f in chain):
        raise Retry
    if sum(_acid_base(r) for r in path) > (2 if theme == 'n' else 1):
        raise Retry  # не более одной кислотно-основной стадии (соль ↔ кислота)
    labels = [sig_label(r) for r in path]
    if not all(labels):
        raise Retry
    for r in path:  # каждая стадия однозначна по химической сути реагента
        if len(canon_prods(r['lhs'][0], canon(r))) != 1:
            raise Retry
    x1, x2, s3, x3 = chain[1], chain[2], chain[3], chain[4]
    # реагент третьей стадии (X₂ → вещество 3) и отвлекающий реагент, который этого превращения не даёт
    l3 = labels[2]
    other = [L for L in {sig_label(r) for r in OUT.get(x2, []) + OUT.get(s3, []) + rng.sample(EDGE_RX, 12)}
             if L and L != l3 and not _fits(x2, s3, L) and not ('NH₃' in L and 'Al₂O₃' in L)]
    other = _distinct_labels([l3] + sorted(other))[1:]
    if not other:
        raise Retry
    l_bad = rng.choice(other)
    conf = set()
    for f in (x1, x2, x3):
        conf.update(g for g in ORG if (brutto(g) == brutto(f) or SUB[g]['hom'] == SUB[f]['hom']) and g not in chain
                    and g not in _POOL10_SKIP and parse_formula(g).get('C', 0) <= 10)
    if not conf:
        raise Retry
    right = [['f', x1], ['f', x2], ['f', x3], ['r', keys_of(l3)], ['f', rng.choice(sorted(conf))],
             ['r', keys_of(l_bad)]]
    rtext = {id(right[3]): l3, id(right[5]): l_bad}
    rng.shuffle(right)
    rt = [vw(o[1]) if o[0] == 'f' else rtext[id(o)] for o in right]
    if len(set(rt)) < 6:
        raise Retry
    s3_txt = nm(s3) if rng.random() < 0.5 else eqv(s3)
    arrows = (f'{eqv(chain[0])} —({labels[0]})→ X₁ —({labels[1]})→ X₂ → {s3_txt} —({labels[3]})→ X₃ → '
              f'{eqv(chain[5])}')
    q = ('Напишите уравнения реакций, с помощью которых можно осуществить следующие превращения:\n'
         f'{arrows}\n'
         'При написании уравнений реакций указывайте преимущественно образующиеся продукты, используйте структурные '
         'формулы органических веществ.\n'
         'Проверка в тренажёре: установите структурные формулы веществ X₁, X₂, X₃ и реагент, необходимый для стадии 3 '
         '(X₂ → ' + nm(s3) + ').')
    ox = [i for i, r in enumerate(path) if any(o in r['lhs'] for o in OXID)]
    steps = [(f'сумма коэффициентов в уравнении стадии {i + 1}', str(sum(path[i]['k'][0]) + sum(path[i]['k'][1])))
             for i in ox]
    e = ' '.join(f'{i + 1}) {rx_eq(r)}' + (f' ({scheme_cond(r)})' if scheme_cond(r) else '') + ';'
                 for i, r in enumerate(path))
    ans = [right.index(['f', x1]), right.index(['f', x2]), right.index(['f', x3]),
           next(n for n, o in enumerate(right) if o[0] == 'r' and rtext[id(o)] == l3)]
    o = match_opts(XL, rt, lids=['X₁', 'X₂', 'X₃', 'R₃'])
    a_ = {o['left'][i]['id']: str(ans[i] + 1) for i in range(4)}
    p = {'start': chain[0], 'keys': [keys_of(L) for L in labels], 'right': right, 'ox': ox}
    return pcard(pid, q, a_, e, k='match', o=o, p=p, eqs=[eqt(r) for r in path], steps=steps or None)


FID32 = dict(answer_format='в КИМ — развёрнутый ответ (5 уравнений, по 1 баллу за уравнение); в тренажёре — соответствие '
                          '(четыре цифры): структуры X₁–X₃ и реагент стадии 3; для ОВР с KMnO₄/K₂Cr₂O₇ — шаг «сумма '
                          'коэффициентов»',
             style='«Напишите уравнения реакций, с помощью которых можно осуществить следующие превращения…» — как в КИМ; '
                   'как в банке, две стрелки без реагентов и одно промежуточное вещество названо',
             level='В', time_min=10, scale='цепочки из 5 стадий школьной органики (демо 2027 №32; банк 4B8E47, 323E4B, '
                                           '5427F2): реагенты с условиями на трёх стрелках, одна кислотно-основная стадия '
                                           'максимум',
             trap='условия определяют продукт (водн./спирт. щёлочь, t < / > 140 °C, среда окисления KMnO₄); реагент '
                  'стадии без подписи нужно подобрать самому',
             kes=KES32, score='в КИМ 5 баллов (по 1 за уравнение: продукты, структурные формулы, коэффициенты). Тренажёр '
                              'покрывает: продукты трёх стадий (X₁–X₃), выбор реагента для стадии без подписи, коэффициенты '
                              'в уравнениях ОВР (шаг «сумма коэффициентов», проверка balance()); не покрыто — запись '
                              'уравнений целиком (рецепт ch-ege-32-full-answer)')


@proto('ch-ege-32-chain-hydrocarbons', 'ЕГЭ', 32, 'Цепочка превращений: углеводороды и галогенпроизводные',
       invariant='пять последовательных стадий; вещество каждой стадии определяется реагентом и условиями',
       varies='цепочки по базе (алканы, алкены, алкины, арены, галогенпроизводные), зашифрованные вещества X₁–X₄',
       answer_rule='идти по цепочке слева направо, записывая продукт каждой стадии; все уравнения уравнены',
       mistakes=['дегидрогалогенирование по Зайцеву', 'Вюрц удваивает радикал', 'гидрирование на Pd — до алкена'],
       solve=_solve32, kind='dict', kes=KES32, fidelity=FID32,
       solve_steps=_solve32_steps)
def g32_hc(rng):
    return _gen32('ch-ege-32-chain-hydrocarbons', rng, 'hc')


@proto('ch-ege-32-chain-oxygen', 'ЕГЭ', 32, 'Цепочка превращений: кислородсодержащие соединения',
       invariant='пять стадий с участием спиртов, альдегидов, кислот, эфиров, солей',
       varies='цепочки по базе, зашифрованные вещества X₁–X₄',
       answer_rule='окисление/восстановление, этерификация/гидролиз, декарбоксилирование — по реагентам на стрелках',
       mistakes=['в щелочной среде кислота существует в виде соли', 'CuO окисляет спирт до альдегида'],
       solve=_solve32, kind='dict', kes=KES32, fidelity=FID32,
       solve_steps=_solve32_steps)
def g32_o(rng):
    return _gen32('ch-ege-32-chain-oxygen', rng, 'o')


@proto('ch-ege-32-chain-aromatic', 'ЕГЭ', 32, 'Цепочка превращений: производные бензола',
       invariant='пять стадий с участием аренов, галогенаренов, фенола, бензойной кислоты, анилина',
       varies='цепочки по базе, зашифрованные вещества X₁–X₄',
       answer_rule='учитывать место атаки (кольцо/цепь) и среду окисления гомологов бензола',
       mistakes=['свет — замещение в боковой цепи, FeCl₃ — в кольце', 'в нейтральной среде KMnO₄ даёт бензоат калия'],
       solve=_solve32, kind='dict', kes=KES32, fidelity=FID32,
       solve_steps=_solve32_steps)
def g32_ar(rng):
    return _gen32('ch-ege-32-chain-aromatic', rng, 'ar')


@proto('ch-ege-32-chain-nitrogen', 'ЕГЭ', 32, 'Цепочка превращений с азотсодержащими веществами',
       invariant='пять стадий, среди продуктов — амины, соли аминов, аминокислоты, нитросоединения',
       varies='цепочки по базе, зашифрованные вещества X₁–X₄',
       answer_rule='амин + кислота → соль, соль амина + щёлочь → амин; галогенкислота + NH₃ → аминокислота',
       mistakes=['в кислой среде восстановление нитробензола даёт соль фениламмония', 'аминокислота с HCl — соль'],
       solve=_solve32, kind='dict', kes=KES32, fidelity=FID32,
       solve_steps=_solve32_steps)
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
       capacity=2000, example={'q': 'Напишите уравнения реакций, с помощью которых можно осуществить следующие '
                                    'превращения: бромэтан —(KOH, спирт., t°)→ X₁ → этанол —(CuO, t°)→ X₂ → X₃ '
                                    '—(C₂H₅OH, H₂SO₄ (конц.), t°)→ этилацетат. При написании уравнений реакций '
                                    'используйте структурные формулы органических веществ.',
                               'a': '1) CH₃–CH₂Br + KOH (спирт.) → CH₂=CH₂ + KBr + H₂O; 2) CH₂=CH₂ + H₂O —(H⁺, t°)→ '
                                    'CH₃–CH₂–OH; 3) CH₃–CH₂–OH + CuO —(t°)→ CH₃–CHO + Cu + H₂O; '
                                    '4) 5CH₃–CHO + 2KMnO₄ + 3H₂SO₄ → 5CH₃–COOH + 2MnSO₄ + K₂SO₄ + 3H₂O; '
                                    '5) CH₃–COOH + CH₃–CH₂–OH ⇄ CH₃–COO–CH₂–CH₃ + H₂O (H₂SO₄ конц., t°)',
                               'e': 'Стадии 2 и 4 даны без реагентов — их нужно подобрать (гидратация этилена; '
                                    'окисление альдегида, например KMnO₄ в кислой среде). 5 баллов — по 1 за верное '
                                    'уравнение со структурными формулами и коэффициентами.'},
       why='развёрнутый ответ (запись уравнений) автоматически проверяется только через эталон и ИИ', kes=KES32,
       fidelity=dict(FID32, answer_format='развёрнутый ответ: 5 уравнений реакций, как в КИМ 2027'))


# ================================================================= задание 25: химия и жизнь, промышленность, полимеры

KES25 = ['3.18', '4.1', '4.2', '4.3', '4.4']
MATCH25 = 'три позиции (А–В), четыре варианта (1–4); ответ — три цифры, цифры могут повторяться'
FID25 = lambda scale, trap: fid(MATCH25, 'Б', 3, scale, trap, KES25, SC1)
POLY = {p['name']: p for p in D.POLYMERS}
POLY_TRIV = {p['name']: (p.get('trivial') or [None])[0] for p in D.POLYMERS}


def _unit(p):
    return '(' + _sub_idx(p['unit'].replace('-', '–')) + ')ₙ'


def _sub_idx(v):
    return re.sub(r'(?<=[A-Za-z)])(\d+)', lambda m: m.group(1).translate(str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')), v)


POLY_M = [p for p in D.POLYMERS if p['how'] == 'полимеризация']


def _solve_poly(p):
    out = {}
    for i, x in enumerate(p['left']):
        if p['mode'] == 'mon→poly':
            j = [n for n, pn in enumerate(p['right']) if x in POLY[pn]['mon']]
        elif p['mode'] == 'poly→mon':
            j = [n for n, f in enumerate(p['right']) if f in POLY[x]['mon']]
        else:  # звено → название
            j = [n for n, pn in enumerate(p['right']) if pn == x]
        out[LET[i]] = str(j[0] + 1)
    return out


@proto('ch-ege-25-monomer-polymer', 'ЕГЭ', 25, 'Мономер → полимер (и обратно)',
       invariant='связь мономера и полимера: полимеризация по двойной связи, поликонденсация бифункциональных мономеров',
       varies='направление (мономер → полимер / полимер → мономер), 15 полимеров (пластмассы, каучуки, волокна)',
       answer_rule='по названию (формуле) мономера найти полимер и наоборот',
       mistakes=['изопрен → натуральный (изопреновый) каучук, дивинил → бутадиеновый', 'ПВХ — из хлорэтена (винилхлорида)',
                 'капрон получают поликонденсацией ε-аминокапроновой кислоты'],
       solve=_solve_poly, kind='dict', kes=KES25,
       fidelity=FID25('банк №25: «мономер — полимер» (пропен, бутадиен-1,3, изопрен, хлорэтен, стирол)',
                      'мономеры каучуков и виниловых полимеров'))
def g25_mon_poly(rng):
    ps = rng.sample(D.POLYMERS, 4)
    mode = rng.choice(['mon→poly', 'poly→mon'])
    use = [p for p in ps[:3]]
    if mode == 'mon→poly':
        use = [p for p in use if len(p['mon']) == 1 and p['name'] not in ('крахмал', 'целлюлоза')]
        if len(use) < 3:
            raise Retry
        left = [p['mon'][0] for p in use]
        right = [p['name'] for p in ps]
        if len({m for p in ps for m in p['mon']} & set(left)) != 3 or any(
                sum(m in POLY[r]['mon'] for r in right) != 1 for m in left):
            raise Retry
        lt = [nm(f, rng) if rng.random() < 0.6 else vw(f) for f in left]
        rt = [POLY_TRIV[n] if POLY_TRIV[n] and rng.random() < 0.3 else n for n in right]
        q = mq('мономером и полимером, который получают из этого мономера', 'МОНОМЕР', 'ПОЛИМЕР')
        ans = [right.index(p['name']) for p in use]
        p_ = {'mode': mode, 'left': left, 'right': right}
    else:
        use = [p for p in use if p['name'] not in ('крахмал', 'целлюлоза')]
        if len(use) < 3:
            raise Retry
        left = [p['name'] for p in use]
        mons = []
        for p in use:
            mons.append(rng.choice(p['mon']))
        extra = [m for p in D.POLYMERS for m in p['mon'] if m not in mons and not any(m in POLY[x]['mon'] for x in left)]
        if not extra:
            raise Retry
        right = list(dict.fromkeys(mons)) + rng.sample(sorted(set(extra)), 4 - len(set(mons)))
        rng.shuffle(right)
        if any(sum(f in POLY[x]['mon'] for f in right) != 1 for x in left):
            raise Retry
        lt = [POLY_TRIV[n] if POLY_TRIV[n] and rng.random() < 0.3 else n for n in left]
        rt = [nm(f, rng) for f in right]
        q = mq('названием полимера и веществом, которое служит мономером для его получения', 'ПОЛИМЕР', 'МОНОМЕР')
        ans = [right.index(m) for m in mons]
        p_ = {'mode': mode, 'left': left, 'right': right}
    if len(set(rt)) < 4:
        raise Retry
    e = '; '.join(f'{p["name"]}: {" + ".join(nm(m) for m in p["mon"])} → {_unit(p)} ({p["how"]})' for p in use)
    return match_card('ch-ege-25-monomer-polymer', rng, q, lt, rt, ans, e + '.', p_)


@proto('ch-ege-25-unit-polymer', 'ЕГЭ', 25, 'Структурное звено → название полимера',
       invariant='по структурному звену узнать полимер (заместитель у звена = заместитель в мономере)',
       varies='звенья 15 полимеров, названия (систематические/тривиальные)',
       answer_rule='восстановить мономер по звену и назвать полимер',
       mistakes=['–CH₂–CH(CH₃)– — полипропилен, а не полиэтилен', '–CH₂–C(CH₃)=CH–CH₂– — натуральный каучук',
                 '–NH–(CH₂)₅–CO– — капрон'],
       solve=_solve_poly, kind='dict', kes=KES25,
       fidelity=FID25('демо 2027 №25 (вариант): –CH₂–CH(CH₃)–, –NH–(CH₂)₅–CO–, –CH₂–C(CH₃)=CH–CH₂–',
                      'похожие звенья (полиэтилен/полипропилен, дивиниловый/изопреновый каучук)'))
def g25_unit(rng):
    ps = rng.sample([p for p in D.POLYMERS if p['name'] not in ('крахмал', 'целлюлоза', 'бутадиен-стирольный каучук')], 4)
    use = ps[:3]
    lt = [_unit(p) for p in use]
    right = [p['name'] for p in ps]
    rng.shuffle(right)
    rt = [POLY_TRIV[n] if POLY_TRIV[n] and rng.random() < 0.3 else n for n in right]
    q = mq('формулой элементарного звена макромолекулы и названием соответствующего полимера', 'СТРУКТУРНОЕ ЗВЕНО',
           'НАЗВАНИЕ ПОЛИМЕРА')
    e = '; '.join(f'{_unit(p)} — {p["name"]} (мономер: {", ".join(nm(m) for m in p["mon"])})' for p in use)
    return match_card('ch-ege-25-unit-polymer', rng, q, lt, rt, [right.index(p['name']) for p in use], e + '.',
                      {'mode': 'unit', 'left': [p['name'] for p in use], 'right': right})


FIBER_T = {**D.FIBERS, 'ацетатный шёлк': 'искусственное', 'асбест': 'минеральное', 'хлопок': 'природное (растительное)'}
HMC_T = {'крахмал': 'природный', 'целлюлоза': 'природный', 'белок': 'природный', 'натуральный каучук': 'природный',
         'полиэтилен': 'синтетический', 'поливинилхлорид': 'синтетический', 'капрон': 'синтетический',
         'полистирол': 'синтетический', 'лавсан': 'синтетический', 'бутадиеновый каучук': 'синтетический',
         'ацетатное волокно': 'искусственный', 'вискоза': 'искусственный', 'ацетатный шёлк': 'искусственный',
         'нитроцеллюлоза': 'искусственный'}


def _solve_ftype(p):
    table = FIBER_T if p['kind'] == 'fiber' else HMC_T
    norm = lambda t: t.split(' (')[0]
    return {LET[i]: str([n for n, t in enumerate(p['right']) if norm(t) == norm(table[x])][0] + 1)
            for i, x in enumerate(p['left'])}


@proto('ch-ege-25-fiber-type', 'ЕГЭ', 25, 'Волокно / высокомолекулярное соединение → тип (природное, искусственное, '
                                          'синтетическое)',
       invariant='природные — из природы без химической переработки; искусственные — химическая переработка природных '
                 'полимеров; синтетические — из низкомолекулярных веществ',
       varies='волокна и ВМС (хлопок, шерсть, шёлк, вискоза, ацетатное волокно, капрон, лавсан, нитрон, крахмал, ПВХ …)',
       answer_rule='определить происхождение полимера',
       mistakes=['вискоза и ацетатное волокно — искусственные, а не синтетические', 'натуральный каучук — природный'],
       solve=_solve_ftype, kind='dict', kes=KES25,
       fidelity=FID25('банк №25: «название волокна — тип волокна» (капрон, нейлон, вискоза, хлопок)',
                      'искусственные против синтетических'))
def g25_ftype(rng):
    kind = rng.choice(['fiber', 'hmc'])
    table = FIBER_T if kind == 'fiber' else HMC_T
    norm = lambda t: t.split(' (')[0]
    types = sorted({norm(t) for t in table.values()})
    left = rng.sample(sorted(table), 3)
    need = {norm(table[x]) for x in left}
    if kind == 'fiber':
        right = sorted({'природное', 'искусственное', 'синтетическое', 'минеральное'})
    else:
        right = ['природный', 'искусственный', 'синтетический', 'неорганический']
    rng.shuffle(right)
    head = ('волокном и группой волокон, к которой оно относится по происхождению' if kind == 'fiber' else
            'высокомолекулярным веществом и группой, к которой оно относится по способу получения')
    q = mq(head, 'НАЗВАНИЕ', 'ТИП')
    ans = [[n for n, t in enumerate(right) if t == norm(table[x])][0] for x in left]
    e = '; '.join(f'{x} — {table[x]}' for x in left)
    return match_card('ch-ege-25-fiber-type', rng, q, left, right, ans, e + '.', {'kind': kind, 'left': left,
                                                                                    'right': right})


APPL = {  # вещество → области применения
    'метан': {'в качестве топлива', 'получение водорода', 'производство метанола', 'получение ацетилена'}, 'пропан': {'в качестве топлива'},
    'бутан': {'в качестве топлива'}, 'ацетилен': {'газовая сварка и резка металлов', 'получение полимеров'},
    'этилен': {'получение полимеров', 'производство этанола'}, 'пропен': {'получение полимеров'},
    'стирол': {'получение полимеров'}, 'бутадиен-1,3': {'производство каучука', 'получение полимеров'}, 'изопрен': {'производство каучука', 'получение полимеров'},
    'хлоропрен': {'производство каучука', 'получение полимеров'}, 'ацетон': {'в качестве растворителя'},
    'этилацетат': {'в качестве растворителя'}, 'толуол': {'в качестве растворителя', 'производство взрывчатых веществ'},
    'бензол': {'в качестве растворителя', 'производство красителей и лекарств'}, 'тетрахлорметан': {'в качестве растворителя'},
    'уксусная кислота': {'консервирование пищевых продуктов', 'в качестве пищевой добавки'},
    'бензоат натрия': {'консервирование пищевых продуктов', 'в качестве пищевой добавки'},
    'лимонная кислота': {'в качестве пищевой добавки', 'консервирование пищевых продуктов'}, 'хлорид натрия': {'в качестве пищевой добавки', 'консервирование пищевых продуктов', 'получение хлора и щелочей'},
    'пероксид водорода': {'в качестве антисептика', 'в качестве отбеливателя', 'обеззараживание воды', 'в косметике'},
    'иод (спиртовой раствор)': {'в качестве антисептика'}, 'анилин': {'производство красителей и лекарств'},
    'глицерин': {'производство взрывчатых веществ', 'в косметике', 'в качестве пищевой добавки'}, 'нитрат аммония': {'в качестве удобрения'},
    'мочевина': {'в качестве удобрения'}, 'суперфосфат': {'в качестве удобрения'}, 'хлорид калия': {'в качестве удобрения'},
    'хлор': {'обеззараживание воды', 'в качестве отбеливателя', 'производство поливинилхлорида'}, 'озон': {'обеззараживание воды', 'в качестве отбеливателя'}, 'аммиак': {'производство удобрений', 'производство азотной кислоты'},
    'оксид ванадия(V)': {'в качестве катализатора'}, 'кумол': {'получение фенола и ацетона'},
    'оксид углерода(II)': {'производство метанола', 'в качестве топлива'}, 'медь': {'изготовление электропроводов'},
    'алюминий': {'изготовление электропроводов', 'производство лёгких сплавов'}, 'аргон': {'создание инертной атмосферы'},
    'активированный уголь': {'в качестве адсорбента'}, 'карбонат натрия': {'изготовление стекла', 'производство мыла и моющих средств'},
    'сульфат бария': {'рентгеноконтрастное вещество в медицине'}, 'этиленгликоль': {'в качестве антифриза', 'получение полимеров'},
    'глицин': {'в качестве лекарственного препарата'}, 'ацетилсалициловая кислота': {'в качестве лекарственного препарата'},
    'сера': {'вулканизация каучука'}, 'формальдегид': {'получение фенолформальдегидных смол', 'получение полимеров', 'в качестве антисептика'},
    'полиэтилен': {'изготовление упаковочной плёнки'}, 'тринитротолуол': {'производство взрывчатых веществ'},
    'этанол': {'в качестве растворителя', 'в качестве антисептика', 'в косметике', 'в качестве топлива'}, 'капрон': {'изготовление текстильных волокон'},
    'хлорат калия': {'производство спичек'}, 'магний': {'производство лёгких сплавов'},
}


def _solve_appl(p):
    if p['dir'] == 's→a':
        return {LET[i]: str([n for n, a in enumerate(p['right']) if a in APPL[x]][0] + 1) for i, x in enumerate(p['left'])}
    return {LET[i]: str([n for n, s_ in enumerate(p['right']) if a in APPL[s_]][0] + 1) for i, a in enumerate(p['left'])}


@proto('ch-ege-25-application', 'ЕГЭ', 25, 'Вещество ↔ область применения',
       invariant='важнейшие применения органических и неорганических веществ (топливо, растворители, мономеры, '
                 'лекарства, удобрения, водоочистка, катализаторы)',
       varies='направление, ≈ 50 веществ и 30 областей; каждой позиции подходит ровно один вариант',
       answer_rule='вспомнить основное применение вещества',
       mistakes=['ацетилен — газовая сварка, а не топливо для автомобилей', 'кумол — сырьё для фенола и ацетона',
                 'пероксид водорода — антисептик и отбеливатель'],
       solve=_solve_appl, kind='dict', kes=KES25,
       fidelity=FID25('банк и демо 2027 №25: «область применения — вещество» (антисептик, пищевая добавка, растворитель)',
                      'вещества с несколькими применениями — однозначность обеспечена подбором вариантов'))
def g25_appl(rng):
    dir_ = rng.choice(['s→a', 'a→s'])
    for _ in range(50):
        subs = rng.sample(sorted(APPL), 4)
        if dir_ == 's→a':
            left = subs[:3]
            apps = [rng.choice(sorted(APPL[s_])) for s_ in left]
            others = sorted(set().union(*APPL.values()) - set().union(*(APPL[s_] for s_ in left)))
            right = list(dict.fromkeys(apps)) + rng.sample(others, 4 - len(set(apps)))
            if all(sum(a in APPL[s_] for a in right) == 1 for s_ in left):
                break
        else:
            apps = []
            for s_ in subs[:3]:
                apps.append(rng.choice(sorted(APPL[s_])))
            if len(set(apps)) < 3:
                continue
            left = apps
            right = subs
            if all(sum(a in APPL[s_] for s_ in right) == 1 for a in left):
                break
    else:
        raise Retry
    rng.shuffle(right)
    if dir_ == 's→a':
        q = mq('названием вещества и тем, где оно преимущественно используется', 'ВЕЩЕСТВО', 'ОБЛАСТЬ ПРИМЕНЕНИЯ')
        ans = [[n for n, a in enumerate(right) if a in APPL[s_]][0] for s_ in left]
        e = '; '.join(f'{s_} — {", ".join(sorted(APPL[s_]))}' for s_ in left)
    else:
        q = mq('назначением и веществом, которое для этого преимущественно используют', 'ОБЛАСТЬ ПРИМЕНЕНИЯ', 'ВЕЩЕСТВО')
        ans = [[n for n, s_ in enumerate(right) if a in APPL[s_]][0] for a in left]
        e = '; '.join(f'{a} — {right[j]}' for a, j in zip(left, ans))
    return match_card('ch-ege-25-application', rng, q, left, right, ans, e + '.', {'dir': dir_, 'left': left,
                                                                                    'right': right})


APPARATUS = {
    'перегонка нефти': 'ректификационная колонна', 'получение мазута': 'ректификационная колонна',
    'разделение нефти на фракции': 'ректификационная колонна', 'синтез аммиака': 'колонна синтеза',
    'синтез метанола': 'колонна синтеза', 'окисление сернистого газа': 'контактный аппарат',
    'поглощение оксида серы(VI)': 'поглотительная башня', 'обжиг пирита': 'печь для обжига',
    'выплавка чугуна': 'доменная печь', 'получение алюминия': 'электролизёр', 'получение натрия': 'электролизёр',
    'получение гидроксида натрия': 'электролизёр', 'получение хлора': 'электролизёр',
    'получение гидроксида калия': 'электролизёр', 'коксование каменного угля': 'коксовая печь',
    'выплавка стали из чугуна': 'кислородный конвертер', 'осушка сернистого газа': 'сушильная башня',
}


def _solve_app(p):
    if p['dir'] == 'p→a':
        return {LET[i]: str(p['right'].index(APPARATUS[x]) + 1) for i, x in enumerate(p['left'])}
    return {LET[i]: str([n for n, pr in enumerate(p['right']) if APPARATUS[pr] == a][0] + 1)
            for i, a in enumerate(p['left'])}


@proto('ch-ege-25-industry', 'ЕГЭ', 25, 'Промышленный процесс ↔ аппарат химического производства',
       invariant='аппараты производств: ректификационная колонна, колонна синтеза, контактный аппарат, поглотительная '
                 'башня, доменная печь, электролизёр …',
       varies='направление, процессы производства аммиака, серной кислоты, метанола, металлов, щелочей, нефтепереработки',
       answer_rule='связать процесс с аппаратом',
       mistakes=['натрий, алюминий и щёлочи получают электролизом', 'SO₂ окисляется в контактном аппарате, SO₃ '
                                                                   'поглощается в башне'],
       solve=_solve_app, kind='dict', kes=KES25,
       fidelity=FID25('демо 2027 №25: «процесс — аппарат» (мазут, KOH, алюминий)', 'один аппарат для разных процессов'))
def g25_industry(rng):
    dir_ = rng.choice(['p→a', 'a→p'])
    apps = sorted(set(APPARATUS.values()))
    if dir_ == 'p→a':
        left = rng.sample(sorted(APPARATUS), 3)
        need = list(dict.fromkeys(APPARATUS[x] for x in left))
        right = need + rng.sample([a for a in apps if a not in need], 4 - len(need))
        rng.shuffle(right)
        q = mq('технологической стадией и установкой, в которой её проводят на производстве', 'ПРОЦЕСС', 'АППАРАТ')
        ans = [right.index(APPARATUS[x]) for x in left]
        e = '; '.join(f'{x} — {APPARATUS[x]}' for x in left)
    else:
        left = rng.sample(apps, 3)
        procs = [rng.choice([p_ for p_, a in APPARATUS.items() if a == x]) for x in left]
        other = [p_ for p_, a in APPARATUS.items() if a not in left]
        right = procs + rng.sample(other, 1)
        rng.shuffle(right)
        q = mq('промышленной установкой и технологической стадией, которую в ней проводят', 'АППАРАТ', 'ПРОЦЕСС')
        ans = [right.index(pr) for pr in procs]
        e = '; '.join(f'{a} — {pr}' for a, pr in zip(left, procs))
    return match_card('ch-ege-25-industry', rng, q, left, right, ans, e + '.', {'dir': dir_, 'left': left,
                                                                                 'right': right})


PROCESS = {
    'керосин': 'перегонка нефти', 'мазут': 'перегонка нефти', 'бензин прямой перегонки': 'перегонка нефти',
    'резина': 'вулканизация', 'полиэтилен': 'полимеризация', 'полипропилен': 'полимеризация',
    'хлоропреновый каучук': 'полимеризация', 'бутадиеновый каучук': 'полимеризация', 'тефлон': 'полимеризация',
    'капрон': 'поликонденсация', 'лавсан': 'поликонденсация', 'фенолформальдегидная смола': 'поликонденсация',
    'кокс': 'коксование', 'бензин с высоким октановым числом (из тяжёлых фракций)': 'крекинг',
    'целлюлоза → глюкоза': 'гидролиз', 'белок → аминокислоты': 'гидролиз', 'сахароза → глюкоза и фруктоза': 'гидролиз',
    'этилен → этанол': 'гидратация', 'ацетилен → этаналь': 'гидратация', 'ацетилен → бензол': 'тримеризация',
    'аминокислоты → полипептид': 'поликонденсация', 'бутадиен-1,3 → каучук': 'полимеризация',
    'глюкоза → этанол': 'брожение', 'жир → мыло': 'омыление', 'растительное масло → твёрдый жир': 'гидрирование',
    'пропен → полипропилен': 'полимеризация', 'этилен → этан': 'гидрирование',
}


def _solve_proc(p):
    return {LET[i]: str(p['right'].index(PROCESS[x]) + 1) for i, x in enumerate(p['left'])}


@proto('ch-ege-25-process', 'ЕГЭ', 25, 'Продукт или превращение → химический процесс',
       invariant='способы получения продуктов (перегонка, крекинг, коксование, вулканизация) и типы превращений '
                 '(полимеризация, поликонденсация, гидролиз, гидратация, брожение)',
       varies='продукты нефтепереработки и полимеры, схемы превращений природных веществ',
       answer_rule='определить процесс, лежащий в основе получения/превращения',
       mistakes=['резину получают вулканизацией каучука', 'полипептиды образуются поликонденсацией',
                 'керосин — продукт перегонки нефти, а не крекинга'],
       solve=_solve_proc, kind='dict', kes=KES25,
       fidelity=FID25('банк №25: «продукт — способ получения» (керосин, хлоропреновый каучук, резина); «схема превращения '
                      '— название процесса»', 'полимеризация / поликонденсация'))
def g25_process(rng):
    left = rng.sample(sorted(PROCESS), 3)
    need = list(dict.fromkeys(PROCESS[x] for x in left))
    other = sorted(set(PROCESS.values()) - set(need))
    right = need + rng.sample(other, 4 - len(need))
    rng.shuffle(right)
    head = rng.choice(['продуктом (превращением) и процессом, лежащим в основе его получения',
                       'схемой превращения (продуктом) и названием химического процесса, на котором оно основано'])
    q = mq(head, 'ПРОДУКТ / ПРЕВРАЩЕНИЕ', 'ПРОЦЕСС')
    return match_card('ch-ege-25-process', rng, q, left, right, [right.index(PROCESS[x]) for x in left],
                      '; '.join(f'{x} — {PROCESS[x]}' for x in left) + '.', {'left': left, 'right': right})


SAFETY = {
    'разбавление концентрированной серной кислоты': 'кислоту приливать в воду тонкой струёй при перемешивании',
    'нагревание пробирки с жидкостью': 'держать пробирку под углом, отверстием от себя и соседей',
    'определение запаха вещества': 'направлять пары к себе движением ладони',
    'работа с летучими и ядовитыми веществами': 'работать в вытяжном шкафу',
    'попадание щёлочи на кожу': 'промыть водой, затем слабым раствором уксусной (борной) кислоты',
    'попадание кислоты на кожу': 'промыть водой, затем раствором питьевой соды',
    'возгорание бензина (ЛВЖ)': 'засыпать песком или накрыть плотной тканью, не заливать водой',
    'хранение щелочных металлов': 'под слоем керосина',
    'хранение белого фосфора': 'под слоем воды',
}


def _solve_safety(p):
    return {LET[i]: str(p['right'].index(SAFETY[x]) + 1) for i, x in enumerate(p['left'])}


@proto('ch-ege-25-safety', 'ЕГЭ', 25, 'Правила безопасной работы с веществами',
       invariant='правила техники безопасности в лаборатории и быту (едкие, горючие, ядовитые вещества)',
       varies='ситуация и правильное действие (9 ситуаций)',
       answer_rule='выбрать безопасный приём для каждой ситуации',
       mistakes=['воду в кислоту не приливают', 'горящий бензин водой не тушат'],
       solve=_solve_safety, kind='dict', kes=['4.1'],
       fidelity=FID25('кодификатор 4.1 «правила безопасной работы с едкими, горючими и токсичными веществами»; в открытом '
                      'банке почти нет — формат №25', 'опасные «интуитивные» действия среди вариантов'))
def g25_safety(rng):
    left = rng.sample(sorted(SAFETY), 3)
    right = [SAFETY[x] for x in left] + [SAFETY[rng.choice([k for k in SAFETY if k not in left])]]
    rng.shuffle(right)
    q = mq('ситуацией при работе с веществами и правильным действием', 'СИТУАЦИЯ', 'ДЕЙСТВИЕ')
    return match_card('ch-ege-25-safety', rng, q, left, right, [right.index(SAFETY[x]) for x in left],
                      '; '.join(f'{x}: {SAFETY[x]}' for x in left) + '.', {'left': left, 'right': right})




# ================================================================= задание 33: установление формулы органического вещества
#
# Вещества задания 33 — из курируемой таблицы T33: у каждого признаки (текст условия), которые ОДНОЗНАЧНО задают
# строение, «признаки для проверки» feats (проверяются по SMILES и базе независимо от текста) и реакция для пункта 3,
# согласованная с признаками. При загрузке модуля проверяется: среди всех веществ базы с той же молекулярной формулой
# признакам удовлетворяет только само вещество.

KES33 = ['5.8', '5.1', '5.4', '3.20']
FID33 = lambda scale, trap, score='3 балла (формула, структура, уравнение); тренажёр проверяет формулу и шаги расчёта': dict(
    answer_format='в КИМ — развёрнутый ответ (3 балла); в тренажёре — молекулярная формула (выбор из четырёх) и шаги '
                  'расчёта n(Э) (как элементы критерия «вычисления»)',
    style='текст задачи и пункты «1) проведите необходимые вычисления… 2) составьте структурную формулу… 3) напишите '
          'уравнение…» — как в КИМ; Ar — целые (Cl = 35,5), Vm = 22,4 л/моль',
    level='В', time_min=12, scale=scale, trap=trap, kes=KES33, score=score)
TAIL33 = ('На основании данных условия задания:\n1) проведите необходимые вычисления (указывайте единицы измерения искомых '
          'физических величин) и установите молекулярную формулу вещества А;\n2) составьте структурную формулу вещества А, '
          'которая однозначно отражает порядок связи атомов в его молекуле;\n3) {eq_task} (используйте структурные формулы '
          'органических веществ).')
TRAINER33 = '\nВ тренажёре: выберите молекулярную формулу вещества А.'
NICE_N = [Fr(x, 1000) for x in (10, 15, 20, 25, 30, 40, 50, 60, 75, 80, 100, 120, 125, 150, 200, 250, 300)]
HAL = ('Cl', 'Br', 'I', 'F')
MET1, MET2 = ('Na', 'K', 'Li'), ('Ca', 'Ba', 'Mg', 'Cu')


def hill(cnt):
    cnt = {e: n for e, n in dict(cnt).items() if n}
    order = ([e for e in ('C', 'H') if e in cnt] if 'C' in cnt else []) + \
        sorted(e for e in cnt if e not in ('C', 'H') or 'C' not in cnt)
    return ''.join(e + (str(cnt[e]) if cnt[e] > 1 else '') for e in order)


def dec(x, nd=3):
    """Число для условия: не более nd знаков после запятой, иначе Retry."""
    x = Fr(x)
    if (x * 10 ** nd).denominator != 1:
        raise Retry
    return fmt(x)


def valid_formula(c):
    """Формула возможна: степень ненасыщенности целая и неотрицательная (одновалентные — H, Hal, Na/K; двухвалентные
    металлы — как два одновалентных)."""
    mono = c.get('H', 0) + sum(c.get(e, 0) for e in HAL + MET1) + 2 * sum(c.get(e, 0) for e in MET2)
    dou2 = 2 * c.get('C', 0) + 2 + c.get('N', 0) - mono
    return dou2 >= 0 and dou2 % 2 == 0 and all(v > 0 for v in c.values())


def _formula_opts(rng, true_cnt):
    """Правильная формула + правдоподобные ошибки (все формулы химически возможны): простейшая формула, удвоенная,
    гомологи ±CH₂, ±O, на 2 атома H меньше/больше."""
    import math
    t = dict(true_cnt)
    g = 0
    for v in t.values():
        g = math.gcd(g, v)
    cands = []
    if g > 1:
        cands.append({e: n // g for e, n in t.items()})
    cands.append({e: n * 2 for e, n in t.items()})
    for dc in (-1, 1):
        h = dict(t)
        h['C'] = h.get('C', 0) + dc
        h['H'] = h.get('H', 0) + 2 * dc
        cands.append(h)
    for do in (-1, 1):
        if t.get('O', 0) + do >= 0:
            h = dict(t)
            h['O'] = t.get('O', 0) + do
            cands.append({e: v for e, v in h.items() if v})
    for dh in (-2, 2):
        h = dict(t)
        h['H'] = t.get('H', 0) + dh
        cands.append(h)
    right = hill(t)
    # соль амина R–NH₃⁺Hal⁻: проверяем формулу «амин + HHal» — отнимаем одну молекулу галогеноводорода
    xh = next((e for e in HAL if t.get(e)), None) if t.get('N') and not valid_formula(t) else None

    def ok_f(c):
        if xh is None:
            return valid_formula(c)
        if c.get(xh, 0) < 1 or c.get('H', 0) < 1:
            return False
        d = dict(c)
        d[xh] -= 1
        d['H'] -= 1
        return valid_formula({e: v for e, v in d.items() if v})
    if xh is not None and not ok_f(t):
        raise Retry
    out, seen = [], {right}
    for c in cands:
        s_ = hill(c)
        if s_ not in seen and ok_f(c) and c.get('C', 0) >= 1:
            seen.add(s_)
            out.append(s_)
    if len(out) < 3:
        raise Retry
    opts_ = sorted([right] + rng.sample(sorted(out), 3), key=lambda x: (parse_formula(x).get('C', 0), x))
    return opts_, [pretty(x) for x in opts_]


def _ratio_to_formula(moles, anchor=None):
    """Моли элементов → формула (независимый пересчёт). anchor=(элемент, число атомов) — масштаб по свойствам."""
    mn = min(v for v in moles.values() if v > 0)
    rel = {e: Fr(v) / Fr(mn) for e, v in moles.items() if v > 0}
    for k in range(1, 25):
        c = {e: float(v * k) for e, v in rel.items()}
        if all(abs(x - round(x)) < 0.06 for x in c.values()):
            emp = {e: int(round(x)) for e, x in c.items()}
            break
    else:
        return None
    k = 1
    if anchor:
        e, n = anchor
        if emp.get(e, 0) == 0 or n % emp[e]:
            return None
        k = n // emp[e]
    return hill({e: n * k for e, n in emp.items()})


# -------- признаки строения (по SMILES и базе — независимо от текста условия)
def _graph(f):
    atoms, bonds = D.smiles_info(SMI[f])['graph']
    adj = defaultdict(list)
    for i, j, o in bonds:
        adj[i].append(j)
        adj[j].append(i)
    return atoms, adj


def _cb(atoms, adj, a, frm):
    return atoms[a][0] + '(' + ','.join(sorted(_cb(atoms, adj, b, a) for b in adj[a] if b != frm)) + ')'


def f_branched(f):
    atoms, adj = _graph(f)
    return any(atoms[i][0] == 'C' and not atoms[i][1] and sum(atoms[j][0] == 'C' for j in adj[i]) >= 3
               for i in range(len(atoms)))


def f_center(f):
    """Функциональный центр: атом C кетонной группы или атом N амина."""
    atoms, adj = _graph(f)
    if cls_fine(f) == 'амины':
        return next(i for i, a in enumerate(atoms) if a[0] == 'N')
    for i, a in enumerate(atoms):
        if a[0] == 'C' and sum(atoms[j][0] == 'C' for j in adj[i]) == 2 and any(atoms[j][0] == 'O' for j in adj[i]):
            return i
    return None


def f_sym(f):
    atoms, adj = _graph(f)
    c = f_center(f)
    br = [_cb(atoms, adj, b, c) for b in adj[c] if atoms[b][0] == 'C']
    return len(br) >= 2 and len(set(br)) == 1


def f_alpha(f):
    atoms, adj = _graph(f)
    n = next(i for i, a in enumerate(atoms) if a[0] == 'N')
    cc = [j for j in adj[n] if atoms[j][0] == 'C']
    return any(any(atoms[k][0] == 'C' and sum(atoms[x][0] == 'O' for x in adj[k]) == 2 for k in adj[c]) for c in cc)


def f_n_on_secondary(f):
    atoms, adj = _graph(f)
    n = next(i for i, a in enumerate(atoms) if a[0] == 'N')
    return any(sum(atoms[k][0] == 'C' for k in adj[c]) >= 2 for c in adj[n] if atoms[c][0] == 'C')


def _hyd_products(f):
    return {x for r in D.REACTIONS if r['lhs'][0] == f and 'NaOH' in r['lhs'] and 'гидролиза' in r['type']
            for x in r['rhs']}


def _cuo_class(f):
    ps = [r['rhs'][0] for r in D.REACTIONS if r['lhs'][0] == f and 'CuO' in r['lhs']]
    return cls_fine(ps[0]) if ps else None


def _alc_part_kind(f):
    alc = [x for x in _hyd_products(f) if x in SUB and SUB[x]['cls'] == 'спирт']
    if not alc:
        return None
    k = _cuo_class(alc[0])
    return {'альдегиды': 'первичный', 'кетоны': 'вторичный'}.get(k, 'третичный')


def _made(f, reagent, hom=None, sub=None, rk=None):
    return any(r['rhs'][0] == f and r['lhs'][1:] == [reagent] and (hom is None or SUB[r['lhs'][0]].get('hom') == hom)
               and (sub is None or r['lhs'][0] == sub) and (rk is None or r.get('rk') == rk) for r in D.REACTIONS)


def feat_ok(f, feats):
    """Удовлетворяет ли вещество f признакам (каждый признак вычисляется по строению/базе)."""
    if f not in SMI:
        return False
    for k, v in feats.items():
        if k == 'cls' and cls_fine(f) != v:
            return False
        if k == 'branched' and f_branched(f) != v:
            return False
        if k == 'sym' and (f_center(f) is None or f_sym(f) != v):
            return False
        if k == 'deg' and (cls_fine(f) != 'амины' or _n_degree(f) != v):
            return False
        if k == 'alpha' and f_alpha(f) != v:
            return False
        if k == 'nsec' and f_n_on_secondary(f) != v:
            return False
        if k == 'cuo' and _cuo_class(f) != v:
            return False
        if k == 'salt' and v not in _hyd_products(f):
            return False
        if k == 'alcohol' and v not in _hyd_products(f):
            return False
        if k == 'alc_kind' and _alc_part_kind(f) != v:
            return False
        if k == 'acid_branched':
            acid = [x for x in _hyd_products(f) if x in SUB and SUB[x]['cls'] == 'соль карбоновой кислоты']
            if not acid or f_branched(acid[0]) != v:
                return False
        if k == 'made' and not _made(f, *v):
            return False
        if k == 'twosalts' and sum(1 for x in _hyd_products(f) if x in SUB and SUB[x]['cls'] in
                                   ('соль карбоновой кислоты', 'фенолят')) != 2:
            return False
    return True


def T(f, clue, eq, task, feats, anchor=None):
    return dict(f=f, clue=clue, eq=eq, task=task, feats=feats, anchor=anchor)


def _use(f, reagent):
    return next(r for r in RX if r['lhs'][0] == f and r['lhs'][1:] == [reagent] and 'горения' not in r['type'])


def _prod(f, reagent, sub=None, rk=None):
    return next(r for r in RX if r['rhs'][0] == f and r['lhs'][1:] == [reagent] and (sub is None or r['lhs'][0] == sub)
                and (rk is None or r.get('rk') == rk))


EST = 'при нагревании с раствором гидроксида натрия вещество А образует '
TK_NAOH = 'напишите уравнение реакции вещества А с раствором гидроксида натрия'
TK_CUO = 'напишите уравнение реакции окисления вещества А оксидом меди(II)'
TK_AG = 'напишите уравнение реакции вещества А с аммиачным раствором оксида серебра'
TK_H2 = 'напишите уравнение реакции каталитического гидрирования вещества А'
TK_NAHCO3 = 'напишите уравнение реакции вещества А с раствором гидрокарбоната натрия'
TK_HCL = 'напишите уравнение реакции вещества А с хлороводородом'
TK_NA = 'напишите уравнение реакции вещества А с натрием'
TK_MAKE = 'напишите уравнение реакции получения вещества А, указанной в условии'
ES_, AL_, AD_, KE_, AC_, AM_, AA_ = ('сложные эфиры', 'одноатомные спирты', 'альдегиды', 'кетоны', 'карбоновые кислоты',
                                     'амины', 'аминокислоты')
T_CHON = [
    T('CH3COOC2H5', EST + 'ацетат натрия и спирт', ('NaOH',), TK_NAOH, dict(cls=ES_, salt='CH3COONa'), ('O', 2)),
    T('HCOOC2H5', EST + 'формиат натрия и спирт', ('NaOH',), TK_NAOH, dict(cls=ES_, salt='HCOONa'), ('O', 2)),
    T('CH3COOCH3', EST + 'ацетат натрия и спирт', ('NaOH',), TK_NAOH, dict(cls=ES_, salt='CH3COONa'), ('O', 2)),
    T('CH3CH2COOCH3', EST + 'метанол и соль карбоновой кислоты', ('NaOH',), TK_NAOH, dict(cls=ES_, alcohol='CH3OH'),
      ('O', 2)),
    T('CH3COOCH2CH2CH3', EST + 'ацетат натрия и первичный спирт', ('NaOH',), TK_NAOH,
      dict(cls=ES_, salt='CH3COONa', alc_kind='первичный'), ('O', 2)),
    T('CH3COOCH(CH3)2', EST + 'ацетат натрия и вторичный спирт', ('NaOH',), TK_NAOH,
      dict(cls=ES_, salt='CH3COONa', alc_kind='вторичный'), ('O', 2)),
    T('HCOOCH2CH2CH3', EST + 'формиат натрия и первичный спирт', ('NaOH',), TK_NAOH,
      dict(cls=ES_, salt='HCOONa', alc_kind='первичный'), ('O', 2)),
    T('CH3CH2COOC2H5', EST + 'этанол и соль карбоновой кислоты', ('NaOH',), TK_NAOH, dict(cls=ES_, alcohol='C2H5OH'),
      ('O', 2)),
    T('CH3(CH2)2COOC2H5', EST + 'этанол и соль карбоновой кислоты с неразветвлённым углеродным скелетом', ('NaOH',),
      TK_NAOH, dict(cls=ES_, alcohol='C2H5OH', acid_branched=False), ('O', 2)),
    T('C6H5COOCH3', EST + 'метанол и соль ароматической карбоновой кислоты', ('NaOH',), TK_NAOH,
      dict(cls=ES_, alcohol='CH3OH'), ('O', 2)),
    T('CH3COOC6H5', 'при нагревании с избытком раствора гидроксида натрия вещество А образует две соли, одна из которых '
                    '— ацетат натрия', ('NaOH',), TK_NAOH, dict(cls=ES_, twosalts=True, salt='CH3COONa'), ('O', 2)),
    T('CH3CH2CH2OH', 'вещество А реагирует с натрием, а при окислении оксидом меди(II) образует альдегид', ('CuO',),
      TK_CUO, dict(cls=AL_, cuo=AD_), ('O', 1)),
    T('CH3CH(OH)CH3', 'вещество А реагирует с натрием, а при окислении оксидом меди(II) образует кетон', ('CuO',),
      TK_CUO, dict(cls=AL_, cuo=KE_), ('O', 1)),
    T('CH3(CH2)3OH', 'вещество А имеет неразветвлённый углеродный скелет, реагирует с натрием, а при окислении оксидом '
                     'меди(II) образует альдегид', ('CuO',), TK_CUO, dict(cls=AL_, cuo=AD_, branched=False), ('O', 1)),
    T('(CH3)2CHCH2OH', 'вещество А имеет разветвлённый углеродный скелет, реагирует с натрием, а при окислении оксидом '
                       'меди(II) образует альдегид', ('CuO',), TK_CUO, dict(cls=AL_, cuo=AD_, branched=True), ('O', 1)),
    T('CH3CH(OH)CH2CH3', 'вещество А реагирует с натрием, а при окислении оксидом меди(II) образует кетон', ('CuO',),
      TK_CUO, dict(cls=AL_, cuo=KE_), ('O', 1)),
    T('(CH3)3COH', 'вещество А реагирует с хлороводородом, но не окисляется оксидом меди(II)', ('HCl',),
      TK_HCL, dict(cls=AL_, cuo=None), ('O', 1)),
    T('CH3(CH2)4OH', 'вещество А имеет неразветвлённый углеродный скелет, реагирует с натрием, а при окислении оксидом '
                     'меди(II) образует альдегид', ('CuO',), TK_CUO, dict(cls=AL_, cuo=AD_, branched=False), ('O', 1)),
    T('C2H5OH', 'вещество А реагирует с натрием с выделением водорода', ('Na',), TK_NA, dict(cls=AL_), ('O', 1)),
    T('CH3CHO', 'при нагревании с аммиачным раствором оксида серебра вещество А образует серебряный налёт', ('Ag(NH3)2OH',),
      TK_AG, dict(cls=AD_), ('O', 1)),
    T('CH3CH2CHO', 'при нагревании с аммиачным раствором оксида серебра вещество А образует серебряный налёт',
      ('Ag(NH3)2OH',), TK_AG, dict(cls=AD_), ('O', 1)),
    T('CH3(CH2)2CHO', 'вещество А имеет неразветвлённый углеродный скелет и вступает в реакцию «серебряного зеркала»',
      ('Ag2O',), TK_AG, dict(cls=AD_, branched=False), ('O', 1)),
    T('(CH3)2CHCHO', 'вещество А имеет разветвлённый углеродный скелет и вступает в реакцию «серебряного зеркала»',
      ('Ag2O',), TK_AG, dict(cls=AD_, branched=True), ('O', 1)),
    T('CH3(CH2)3CHO', 'вещество А имеет неразветвлённый углеродный скелет и вступает в реакцию «серебряного зеркала»',
      ('Ag2O',), TK_AG, dict(cls=AD_, branched=False), ('O', 1)),
    T('CH3COCH3', 'вещество А не вступает в реакцию «серебряного зеркала», а при каталитическом гидрировании образует '
                  'вторичный спирт', ('H2',), TK_H2, dict(cls=KE_), ('O', 1)),
    T('CH3COCH2CH3', 'вещество А не вступает в реакцию «серебряного зеркала», а при каталитическом гидрировании образует '
                     'вторичный спирт', ('H2',), TK_H2, dict(cls=KE_), ('O', 1)),
    T('CH3CH2COCH2CH3', 'вещество А не вступает в реакцию «серебряного зеркала», при гидрировании образует вторичный '
                        'спирт; молекула вещества А симметрична', ('H2',), TK_H2, dict(cls=KE_, sym=True), ('O', 1)),
    T('CH3CO(CH2)2CH3', 'вещество А не вступает в реакцию «серебряного зеркала», при гидрировании образует вторичный '
                        'спирт; углеродный скелет неразветвлённый, молекула несимметрична', ('H2',), TK_H2,
      dict(cls=KE_, sym=False, branched=False), ('O', 1)),
    T('CH3COCH(CH3)2', 'вещество А не вступает в реакцию «серебряного зеркала», при гидрировании образует вторичный '
                       'спирт; углеродный скелет разветвлённый', ('H2',), TK_H2, dict(cls=KE_, branched=True), ('O', 1)),
    T('CH3COOH', 'вещество А реагирует с гидрокарбонатом натрия с выделением газа', ('NaHCO3',), TK_NAHCO3,
      dict(cls=AC_), ('O', 2)),
    T('CH3CH2COOH', 'вещество А реагирует с гидрокарбонатом натрия с выделением газа', ('NaHCO3',), TK_NAHCO3,
      dict(cls=AC_), ('O', 2)),
    T('CH3(CH2)2COOH', 'вещество А реагирует с гидрокарбонатом натрия с выделением газа и имеет неразветвлённый '
                       'углеродный скелет', ('NaHCO3',), TK_NAHCO3, dict(cls=AC_, branched=False), ('O', 2)),
    T('(CH3)2CHCOOH', 'вещество А реагирует с гидрокарбонатом натрия с выделением газа и имеет разветвлённый углеродный '
                      'скелет', ('NaHCO3',), TK_NAHCO3, dict(cls=AC_, branched=True), ('O', 2)),
    T('C2H5NH2', 'в молекуле вещества А атом азота связан только с одним атомом углерода', ('HCl',), TK_HCL, dict(cls=AM_, deg=1), ('N', 1)),
    T('(CH3)2NH', 'в молекуле вещества А атом азота связан с двумя атомами углерода', ('HCl',), TK_HCL, dict(cls=AM_, deg=2), ('N', 1)),
    T('CH3CH2CH2NH2', 'в молекуле вещества А атом азота связан только с одним атомом углерода, а этот атом углерода связан только с одним атомом углерода', ('HCl',), TK_HCL,
      dict(cls=AM_, deg=1, nsec=False), ('N', 1)),
    T('(CH3)2CHNH2', 'в молекуле вещества А атом азота связан только с одним атомом углерода, а этот атом углерода связан ещё с двумя атомами углерода',
      ('HCl',), TK_HCL, dict(cls=AM_, deg=1, nsec=True), ('N', 1)),
    T('CH3NHC2H5', 'в молекуле вещества А атом азота связан с двумя атомами углерода', ('HCl',), TK_HCL, dict(cls=AM_, deg=2), ('N', 1)),
    T('(CH3)3N', 'в молекуле вещества А атом азота связан с тремя атомами углерода', ('HCl',), TK_HCL, dict(cls=AM_, deg=3), ('N', 1)),
    T('(C2H5)2NH', 'вещество А — вторичный амин, оба радикала которого одинаковы', ('HCl',), TK_HCL,
      dict(cls=AM_, deg=2, sym=True), ('N', 1)),
    T('(C2H5)3N', 'вещество А — третичный амин, все три радикала которого одинаковы', ('HCl',), TK_HCL,
      dict(cls=AM_, deg=3, sym=True), ('N', 1)),
    T('H2NCH2COOH', 'вещество А проявляет амфотерные свойства: образует соли и с кислотами, и со щелочами', ('NaOH',),
      TK_NAOH, dict(cls=AA_), ('N', 1)),
    T('CH3CH(NH2)COOH', 'вещество А — амфотерное соединение, в молекуле которого аминогруппа находится в α-положении к '
                        'карбоксильной группе', ('NaOH',), TK_NAOH, dict(cls=AA_, alpha=True), ('N', 1)),
    T('H2NCH2CH2COOH', 'вещество А — амфотерное соединение, в молекуле которого аминогруппа и карбоксильная группа '
                       'находятся на концах неразветвлённой цепи', ('NaOH',), TK_NAOH, dict(cls=AA_, alpha=False),
      ('N', 1)),
]
AD2_ = 'присоединении брома к алкену'
T_HAL = [
    T('CH2BrCH2Br', 'вещество А образуется при ' + AD2_, ('make', 'Br2'), TK_MAKE, dict(made=('Br2', 'алкены')), ('Br', 2)),
    T('CH2BrCHBrCH3', 'вещество А образуется при ' + AD2_, ('make', 'Br2'), TK_MAKE, dict(made=('Br2', 'алкены')),
      ('Br', 2)),
    T('CH3CHBrCHBrCH3', 'вещество А образуется при ' + AD2_ + ', для которого характерна цис-транс-изомерия',
      ('make', 'Br2'), TK_MAKE, dict(made=('Br2', 'алкены', 'CH3CHCHCH3')), ('Br', 2)),
    T('CH2BrCHBrCH2CH3', 'вещество А образуется при ' + AD2_ + ' с неразветвлённым скелетом и концевой двойной связью',
      ('make', 'Br2'), TK_MAKE, dict(made=('Br2', 'алкены', 'CH2CHCH2CH3')), ('Br', 2)),
    T('(CH3)2CBrCH2Br', 'вещество А образуется при ' + AD2_ + ' с разветвлённым углеродным скелетом', ('make', 'Br2'),
      TK_MAKE, dict(made=('Br2', 'алкены', 'CH2C(CH3)2')), ('Br', 2)),
    T('CH2ClCH2Cl', 'вещество А образуется при присоединении хлора к алкену', ('make', 'Cl2'), TK_MAKE,
      dict(made=('Cl2', 'алкены')), ('Cl', 2)),
    T('CH2ClCHClCH3', 'вещество А образуется при присоединении хлора к алкену', ('make', 'Cl2'), TK_MAKE,
      dict(made=('Cl2', 'алкены')), ('Cl', 2)),
    T('CH3CHBr2', 'вещество А образуется при присоединении избытка бромоводорода к алкину', ('make', 'HBr'), TK_MAKE,
      dict(made=('HBr', 'алкины')), ('Br', 2)),
    T('CH3CBr2CH3', 'вещество А образуется при присоединении избытка бромоводорода к алкину', ('make', 'HBr'), TK_MAKE,
      dict(made=('HBr', 'алкины')), ('Br', 2)),
    T('C2H5Cl', 'вещество А образуется при присоединении хлороводорода к алкену', ('make', 'HCl'), TK_MAKE,
      dict(made=('HCl', 'алкены')), ('Cl', 1)),
    T('C2H5Br', 'вещество А образуется при присоединении бромоводорода к алкену', ('make', 'HBr'), TK_MAKE,
      dict(made=('HBr', 'алкены')), ('Br', 1)),
    T('CH3CHClCH3', 'вещество А образуется при присоединении хлороводорода к алкену', ('make', 'HCl'), TK_MAKE,
      dict(made=('HCl', 'алкены')), ('Cl', 1)),
    T('CH3CHBrCH3', 'вещество А образуется при присоединении бромоводорода к алкену', ('make', 'HBr'), TK_MAKE,
      dict(made=('HBr', 'алкены')), ('Br', 1)),
    T('CH3CHBrCH2CH3', 'вещество А образуется при присоединении бромоводорода к алкену с неразветвлённым углеродным '
                       'скелетом', ('make', 'HBr'), TK_MAKE, dict(made=('HBr', 'алкены'), branched=False), ('Br', 1)),
    T('(CH3)3CBr', 'вещество А образуется при присоединении бромоводорода к алкену с разветвлённым углеродным скелетом',
      ('make', 'HBr'), TK_MAKE, dict(made=('HBr', 'алкены'), branched=True), ('Br', 1)),
    T('CH3Cl', 'вещество А образуется при хлорировании метана на свету', ('make', 'Cl2'), TK_MAKE,
      dict(made=('Cl2', None, 'CH4')), ('Cl', 1)),
    T('C6H5Br', 'вещество А образуется при бромировании бензола в присутствии бромида железа(III)', ('make', 'Br2'),
      TK_MAKE, dict(made=('Br2', None, 'C6H6')), ('Br', 1)),
    T('C6H5CH2Cl', 'вещество А образуется при хлорировании толуола на свету', ('make', 'Cl2'), TK_MAKE,
      dict(made=('Cl2', None, 'C6H5CH3', 'Cl2hv')), ('Cl', 1)),
    T('CH3NH3Cl', 'вещество А образуется при взаимодействии амина с хлороводородом', ('make', 'HCl'), TK_MAKE,
      dict(made=('HCl', 'предельные амины')), ('N', 1)),
    T('C2H5NH3Cl', 'вещество А образуется при взаимодействии первичного амина с хлороводородом', ('make', 'HCl'), TK_MAKE,
      dict(made=('HCl', None, 'C2H5NH2')), ('N', 1)),
    T('(CH3)2NH2Cl', 'вещество А образуется при взаимодействии вторичного амина с хлороводородом', ('make', 'HCl'),
      TK_MAKE, dict(made=('HCl', None, '(CH3)2NH')), ('N', 1)),
    T('C2H5NH3Br', 'вещество А образуется при взаимодействии первичного амина с бромоводородом', ('make', 'HBr'),
      TK_MAKE, dict(made=('HBr', None, 'C2H5NH2')), ('N', 1)),
    T('(C2H5)2NH2Cl', 'вещество А образуется при взаимодействии хлороводорода со вторичным амином, радикалы которого '
                      'одинаковы', ('make', 'HCl'), TK_MAKE, dict(made=('HCl', None, '(C2H5)2NH')), ('N', 1)),
    T('CH3CH2CH2NH3Cl', 'вещество А образуется при взаимодействии хлороводорода с первичным амином, аминогруппа в '
                        'котором связана с крайним атомом углерода', ('make', 'HCl'), TK_MAKE,
      dict(made=('HCl', None, 'CH3CH2CH2NH2')), ('N', 1)),
    T('(CH3)2CHNH3Cl', 'вещество А образуется при взаимодействии хлороводорода с первичным амином, аминогруппа в '
                       'котором связана со вторичным атомом углерода', ('make', 'HCl'), TK_MAKE,
      dict(made=('HCl', None, '(CH3)2CHNH2')), ('N', 1)),
    T('CH3NH2C2H5Cl', 'вещество А образуется при взаимодействии хлороводорода со вторичным амином, радикалы которого '
                      'различны', ('make', 'HCl'), TK_MAKE, dict(made=('HCl', None, 'CH3NHC2H5')), ('N', 1)),
    T('(CH3)3NHCl', 'вещество А образуется при взаимодействии хлороводорода с третичным амином', ('make', 'HCl'),
      TK_MAKE, dict(made=('HCl', None, '(CH3)3N')), ('N', 1)),
    T('C6H5NH3Cl', 'вещество А образуется при взаимодействии хлороводорода с ароматическим амином', ('make', 'HCl'),
      TK_MAKE, dict(made=('HCl', None, 'C6H5NH2')), ('N', 1)),
]
AC_MAKE = 'вещество А образуется при действии раствора гидроксида {m} на карбоновую кислоту'
T_SALT = [
    T('CH3COONa', AC_MAKE.format(m='натрия'), ('make', 'NaOH'), TK_MAKE, dict(made=('NaOH', None)), ('Na', 1)),
    T('HCOONa', AC_MAKE.format(m='натрия'), ('make', 'NaOH'), TK_MAKE, dict(made=('NaOH', None)), ('Na', 1)),
    T('CH3CH2COONa', AC_MAKE.format(m='натрия'), ('make', 'NaOH'), TK_MAKE, dict(made=('NaOH', None)), ('Na', 1)),
    T('CH3(CH2)2COONa', AC_MAKE.format(m='натрия') + ' с неразветвлённым углеродным скелетом', ('make', 'NaOH'),
      TK_MAKE, dict(made=('NaOH', None), branched=False), ('Na', 1)),
    T('(CH3)2CHCOONa', AC_MAKE.format(m='натрия') + ' с разветвлённым углеродным скелетом', ('make', 'NaOH'), TK_MAKE,
      dict(made=('NaOH', None), branched=True), ('Na', 1)),
    T('C6H5COONa', AC_MAKE.format(m='натрия') + ' ароматического ряда', ('make', 'NaOH'), TK_MAKE,
      dict(made=('NaOH', None)), ('Na', 1)),
    T('CH3COOK', AC_MAKE.format(m='калия'), ('make', 'KOH'), TK_MAKE, dict(made=('KOH', None)), ('K', 1)),
    T('HCOOK', AC_MAKE.format(m='калия'), ('make', 'KOH'), TK_MAKE, dict(made=('KOH', None)), ('K', 1)),
    T('CH3CH2COOK', AC_MAKE.format(m='калия'), ('make', 'KOH'), TK_MAKE, dict(made=('KOH', None)), ('K', 1)),
    T('C6H5COOK', AC_MAKE.format(m='калия') + ' ароматического ряда', ('make', 'KOH'), TK_MAKE,
      dict(made=('KOH', None)), ('K', 1)),
    T('C6H5ONa', 'вещество А образуется при действии гидроксида натрия на вещество, которое даёт фиолетовое окрашивание с '
                 'хлоридом железа(III)', ('make', 'NaOH'), TK_MAKE, dict(made=('NaOH', None, 'C6H5OH')), ('Na', 1)),
    T('C6H5OK', 'вещество А образуется при действии гидроксида калия на вещество, которое даёт фиолетовое окрашивание с '
                'хлоридом железа(III)', ('make', 'KOH'), TK_MAKE, dict(made=('KOH', None, 'C6H5OH')), ('K', 1)),
    T('C2H5ONa', 'вещество А образуется при взаимодействии одноатомного спирта с натрием', ('make', 'Na'), TK_MAKE,
      dict(made=('Na', None)), ('Na', 1)),
    T('CH3ONa', 'вещество А образуется при взаимодействии одноатомного спирта с натрием', ('make', 'Na'), TK_MAKE,
      dict(made=('Na', None)), ('Na', 1)),
    T('CH3CH2CH2ONa', 'вещество А образуется при взаимодействии натрия с первичным одноатомным спиртом', ('make', 'Na'),
      TK_MAKE, dict(made=('Na', None, 'CH3CH2CH2OH')), ('Na', 1)),
    T('H2NCH2COONa', 'вещество А образуется при действии раствора гидроксида натрия на аминокислоту', ('make', 'NaOH'),
      TK_MAKE, dict(made=('NaOH', 'аминокислоты')), ('Na', 1)),
    T('(CH3COO)2Ca', 'вещество А образуется при действии гидроксида кальция на карбоновую кислоту', ('make', 'Ca(OH)2'),
      TK_MAKE, dict(made=('Ca(OH)2', None)), ('Ca', 1)),
]


def _t_reaction(t):
    eq = t['eq']
    if eq[0] == 'make':
        subs = t['feats'].get('made', (None, None, None))
        sub = subs[2] if len(subs) > 2 else None
        return _prod(t['f'], eq[1], sub, subs[3] if len(subs) > 3 else None)
    return _use(t['f'], eq[0])


def _check_targets(ts):
    """Отбрасывает цели, чьи признаки не выделяют вещество однозначно среди изомеров базы (и сообщает об этом)."""
    ok = []
    for t in ts:
        same = [g for g in ORG if brutto(g) == brutto(t['f']) and g in SMI]
        fit = [g for g in same if feat_ok(g, t['feats'])]
        try:
            _t_reaction(t)
        except StopIteration:
            continue
        if fit == [t['f']]:
            ok.append(t)
    return ok


T_CHON = _check_targets(T_CHON)
T_HAL = _check_targets(T_HAL)
T_SALT = _check_targets(T_SALT)
T_ALL = {t['f']: t for t in T_CHON + T_HAL + T_SALT}


def _fresh(rng, key, items):
    """Выбор цели 33 без повторов подряд в пределах одного генератора случайных чисел (выборка из 5 аналогов не
    должна содержать одно вещество с удвоенными числами); после исчерпания список начинается заново."""
    used = rng.__dict__.setdefault('_fresh33', {}).setdefault(key, set())
    rest = [t for t in items if t['f'] not in used]
    if not rest:
        used.clear()
        rest = list(items)
    t = rng.choice(rest)
    used.add(t['f'])
    return t


def _known(rng):
    return rng.choice(['Известно, что', 'Дополнительно установлено, что', 'Опытным путём установлено, что'])


def _vary(rng, clue):
    return clue.replace('вещество А', rng.choice(['вещество А', 'это вещество']), 1)


def _explain(f, t, nums):
    r = _t_reaction(t)
    return nums + f' → {pretty(hill(parse_formula(f)))}. Строение: {vw(f)} ({nm(f)}). Уравнение: {rx_eq(r)}.'


def _pick_struct(formula, feats):
    """Независимо: вещество базы с данной формулой, удовлетворяющее признакам."""
    c = [g for g in ORG if g in SMI and hill(parse_formula(g)) == formula and feat_ok(g, feats)]
    return c[0] if len(c) == 1 else None


# -------- 33.1: по продуктам сгорания (CHO/CHON)
def _comb_moles(p):
    nC = Fr(p['V_CO2']) / Fr(224, 10) if p.get('V_CO2') else Fr(p['m_CO2']) / 44
    nH = Fr(p['m_H2O']) / 18 * 2
    nN = Fr(p.get('V_N2') or 0) / Fr(224, 10) * 2
    mO = Fr(p['m']) - 12 * nC - nH - 14 * nN
    return {'C': nC, 'H': nH, 'N': nN, 'O': mO / 16}


def _solve_comb(p):
    moles = {e: v for e, v in _comb_moles(p).items() if v > 0}
    return str(p['opts'].index(_ratio_to_formula(moles, anchor=tuple(p['anchor']))) + 1)


def _steps_comb(p):
    m = _comb_moles(p)
    return [fmt(m[e]) for e in ('C', 'H', 'O', 'N') if m[e] > 0]


def _comb_data(rng, f, n):
    a = parse_formula(f)
    m = n * molar(f)
    use_mass = rng.random() < 0.35
    V = n * a['C'] * Fr(224, 10)
    mH = n * a['H'] * 9
    p = {'m': str(m), 'm_H2O': str(mH)}
    if use_mass:
        co2 = f'{dec(n * a["C"] * 44)} г углекислого газа'
        p['m_CO2'] = str(n * a['C'] * 44)
    else:
        co2 = f'{dec(V)} л (н.у.) ' + rng.choice(['углекислого газа', 'оксида углерода(IV)'])
        p['V_CO2'] = str(V)
    items = [co2, f'{dec(mH)} г воды']
    if a.get('N'):
        VN = n * a['N'] * Fr(112, 10)
        items.append(f'{dec(VN)} л (н.у.) азота')
        p['V_N2'] = str(VN)
    rng.shuffle(items)
    lst = ', '.join(items[:-1]) + ' и ' + items[-1]
    tpl = rng.randrange(3)
    head = [f'Для анализа сожгли {dec(m)} г органического вещества А в избытке кислорода; образовалось {lst}.',
            f'Навеску органического вещества А массой {dec(m)} г полностью сожгли, продукты сгорания — {lst}.',
            f'Полное сжигание {dec(m)} г органического вещества А дало {lst}.'][tpl]
    return head, p, m


def _comb_steps_lbl(a):
    return [f'n({e}), моль' for e in ('C', 'H', 'O', 'N') if a.get(e)]


@proto('ch-ege-33-combustion', 'ЕГЭ', 33, 'Формула вещества по продуктам сгорания (CO₂, H₂O, N₂) и признакам строения',
       invariant='n(C) = n(CO₂), n(H) = 2n(H₂O), n(N) = 2n(N₂), m(O) — по разности; простейшая формула → молекулярная по '
                 'числу атомов O/N в функциональной группе; строение — по признакам (класс, разветвлённость, продукт '
                 'окисления или гидролиза)',
       varies='≈ 45 веществ (эфиры, спирты, альдегиды, кетоны, кислоты, амины, аминокислоты), масса пробы, способ задания '
              'CO₂',
       answer_rule='вычислить n(C), n(H), n(O) [n(N)] и их отношение, привести к формуле с нужным числом функциональных '
                   'групп; признаки однозначно задают структуру',
       mistakes=['забыт кислород (по разности масс)', 'n(H) = n(H₂O) вместо 2n(H₂O)',
                 'простейшая формула принята за молекулярную (сложный эфир C₂H₄O → C₄H₈O₂)'],
       solve=_solve_comb, solve_steps=_steps_comb, kind='param', kes=KES33,
       fidelity=FID33('банк №33 (5.8): «При сжигании образца массой 8,76 г получено 8,064 л CO₂ и 5,4 г воды… подвергается '
                      'гидролизу…» (BA45FC, 752570, A4B57C) — масса пробы 1–45 г, объёмы с тремя знаками',
                      'кислород по разности; простейшая ≠ молекулярная; признаки выбирают один изомер'))
def g33_comb(rng):
    t = _fresh(rng, 'chon', T_CHON)
    f = t['f']
    a = parse_formula(f)
    head, p, m = _comb_data(rng, f, rng.choice(NICE_N))
    p['anchor'] = list(t['anchor'])
    q = head + f' {_known(rng)} {_vary(rng, t["clue"])}.\n' + TAIL33.format(eq_task=t['task']) + TRAINER33
    opts_raw, opts_txt = _formula_opts(rng, a)
    p['opts'] = opts_raw
    mo = _comb_moles(p)
    nums = '; '.join(f'n({e}) = {fmt(mo[e])} моль' for e in ('C', 'H', 'O', 'N') if mo[e] > 0) + \
        '; отношение ' + ' : '.join(f'{e}' for e in ('C', 'H', 'O', 'N') if a.get(e)) + ' = ' + \
        ' : '.join(str(a[e]) for e in ('C', 'H', 'O', 'N') if a.get(e))
    return pcard('ch-ege-33-combustion', q, str(opts_raw.index(hill(a)) + 1), _explain(f, t, nums), k='one',
                 o=opts(opts_txt), p=p, eq=eqt(_t_reaction(t)), steps=list(zip(_comb_steps_lbl(a), _steps_comb(p))))


def _solve_struct(p):
    moles = {e: v for e, v in _comb_moles(p).items() if v > 0}
    formula = _ratio_to_formula(moles, anchor=tuple(p['anchor']))
    g = _pick_struct(formula, p['feats'])
    return str(p['opts'].index(g) + 1)


@proto('ch-ege-33-structure', 'ЕГЭ', 33, 'Структурная формула вещества по продуктам сгорания и признакам',
       invariant='после расчёта формулы выбрать единственную структуру, отвечающую всем признакам условия',
       varies='вещества с несколькими изомерами (эфиры, спирты, альдегиды, кетоны, кислоты, амины); в вариантах — '
              'изомеры и гомологи',
       answer_rule='формула из расчёта, затем отбор изомеров по классу, разветвлённости, продукту окисления/гидролиза',
       mistakes=['выбран изомер другого класса (кислота вместо эфира)', 'не учтено «неразветвлённый скелет»',
                 'первичный спирт спутан со вторичным'],
       solve=_solve_struct, kind='param', kes=KES33,
       fidelity=FID33('банк №33: пункт 2 — «составьте структурную формулу вещества А, которая однозначно отражает порядок '
                      'связи атомов»; признаки как в BA45FC, 752570', 'изомеры одной формулы среди вариантов',
                      score='второй элемент критериев (структура) — выбор из четырёх структур'))
def g33_struct(rng):
    t = _fresh(rng, 'chon', T_CHON)
    f = t['f']
    iso = [g for g in ORG if g in SMI and brutto(g) == brutto(f) and g != f and g not in _POOL10_SKIP]
    near = [g for g in ORG if g in SMI and SUB[g]['hom'] == SUB[f]['hom'] and g != f and g not in iso]
    if len(iso) + len(near) < 3:
        raise Retry
    dis = rng.sample(iso, min(3, len(iso)))
    dis += rng.sample(near, 3 - len(dis))
    items = [f] + dis
    rng.shuffle(items)
    rt = [vw(g) for g in items]
    if len(set(rt)) < 4:
        raise Retry
    head, p, m = _comb_data(rng, f, rng.choice(NICE_N))
    p.update(anchor=list(t['anchor']), feats=t['feats'], opts=items)
    q = (head + f' {_known(rng)} {_vary(rng, t["clue"])}.\n' + 'Установите молекулярную формулу вещества А и выберите '
         'его структурную формулу, которая однозначно отражает порядок связи атомов в молекуле.')
    mo = _comb_moles(p)
    nums = '; '.join(f'n({e}) = {fmt(mo[e])} моль' for e in ('C', 'H', 'O', 'N') if mo[e] > 0)
    return pcard('ch-ege-33-structure', q, str(items.index(f) + 1), _explain(f, t, nums), k='one', o=opts(rt), p=p,
                 eq=eqt(_t_reaction(t)))


# -------- 33.2: по массовым долям элементов
EL_GEN = {'C': 'углерода', 'H': 'водорода', 'O': 'кислорода', 'N': 'азота', 'Na': 'натрия', 'K': 'калия',
          'Ca': 'кальция', 'Cl': 'хлора', 'Br': 'брома', 'Ba': 'бария'}
MF_T = [t for t in T_CHON + T_HAL + T_SALT if len(parse_formula(t['f'])) >= 3]


def _mf_moles(p):
    moles = {e: Fr(v) / AR[e] for e, v in p['w'].items()}
    if p.get('rest'):
        moles[p['rest']] = (100 - sum(Fr(v) for v in p['w'].values())) / AR[p['rest']]
    return moles


def _solve_mf(p):
    return str(p['opts'].index(_ratio_to_formula(_mf_moles(p), anchor=tuple(p['anchor']))) + 1)


def _steps_mf(p):
    mo = _mf_moles(p)
    return [fmt(mo[e], 3) for e in p['order']]


@proto('ch-ege-33-mass-fractions', 'ЕГЭ', 33, 'Формула вещества по массовым долям элементов и признакам',
       invariant='n(Э) в 100 г = ω(Э)/Ar(Э) → простейшее отношение → молекулярная формула по числу атомов металла, азота, '
                 'галогена или кислорода, следующему из признаков; способ получения, указанный в условии, — в пункте 3',
       varies='вещества: соли карбоновых кислот, феноляты, алкоголяты, соли аминов, галогенпроизводные, эфиры, '
              'аминокислоты; какие доли даны (все или «остальное — водород»)',
       answer_rule='разделить массовые доли на Ar, привести к целым, масштабировать по «якорному» элементу',
       mistakes=['округление отношения до целых слишком рано', 'не учтён элемент «остальное»', 'Ar(Cl) = 35,5'],
       solve=_solve_mf, solve_steps=_steps_mf, kind='param', kes=KES33,
       fidelity=FID33('банк №33: «Соль органической кислоты содержит 5,05% H, 42,42% C…», «вещество содержит 12,79% N, '
                      '10,95% H и 32,42% Cl» — массовые доли с двумя знаками', 'водород «остальное», масштабирование'))
def g33_mf(rng):
    t = _fresh(rng, 'mf', MF_T)
    f = t['f']
    a = parse_formula(f)
    M = molar(f)
    w = {e: round(Fr(AR[e] * n * 100) / M, 2) for e, n in a.items()}
    rest = rng.choice([None, 'H']) if 'H' in a else None
    shown = {e: v for e, v in w.items() if e != rest}
    order = [e for e in ('C', 'H', 'N', 'O', 'Cl', 'Br', 'Na', 'K', 'Ca', 'Ba') if e in a]
    ws = ', '.join(f'{fmt(shown[e])} % {EL_GEN[e]}' for e in order if e in shown)
    head = rng.choice(['Органическое вещество А содержит по массе', 'Массовые доли элементов в органическом веществе А:'])
    task = t['task'] if t['eq'][0] != 'make' else TK_MAKE
    q = (f'{head} {ws}' + (', остальное — водород.' if rest else '.') + f' {_known(rng)} {_vary(rng, t["clue"])}.\n'
         + TAIL33.format(eq_task=task) + TRAINER33)
    opts_raw, opts_txt = _formula_opts(rng, a)
    p = {'w': {e: str(v) for e, v in shown.items()}, 'rest': rest, 'anchor': list(t['anchor']), 'opts': opts_raw,
         'order': order}
    mo = _mf_moles(p)
    nums = 'В 100 г: ' + '; '.join(f'n({e}) = {fmt(mo[e], 3)} моль' for e in order) + \
        (f' (водород — по разности: {fmt(100 - sum(shown.values()))} %)' if rest else '') + \
        f'; с учётом числа атомов {t["anchor"][0]} = {t["anchor"][1]}'
    return pcard('ch-ege-33-mass-fractions', q, str(opts_raw.index(hill(a)) + 1), _explain(f, t, nums), k='one',
                 o=opts(opts_txt), p=p, eq=eqt(_t_reaction(t)),
                 steps=[(f'n({e}) в 100 г вещества, моль', v) for e, v in zip(order, _steps_mf(p))])


# -------- 33.3: соль карбоновой кислоты → карбонильное соединение
SALT_R = {'H': ('формиат', 'HCHO', 'метаналь', None), 'CH3': ('ацетат', 'CH3COCH3', 'пропанон', None),
          'C2H5': ('пропионат', '(C2H5)2CO', 'пентанон-3', None),
          'CH3CH2CH2': ('бутират', '(CH3CH2CH2)2CO', 'гептанон-4', False),
          '(CH3)2CH': ('изобутират', '((CH3)2CH)2CO', '2,4-диметилпентанон-3', True),
          'CH3(CH2)3': ('валерат', '(CH3(CH2)3)2CO', 'нонанон-5', False)}


def _salt_moles(p):
    mo = {e: Fr(v) / AR[e] for e, v in p['w'].items()}
    if p.get('rest'):
        mo[p['rest']] = (100 - sum(Fr(v) for v in p['w'].values())) / AR[p['rest']]
    return mo


def _solve_salt(p):
    return str(p['opts'].index(_ratio_to_formula(_salt_moles(p), anchor=(p['metal'], 1))) + 1)


def _steps_salt(p):
    mo = _salt_moles(p)
    return [fmt(mo[e], 3) for e in p['order']]


@proto('ch-ege-33-salt-carbonyl', 'ЕГЭ', 33, 'Соль карбоновой кислоты (Ca, Ba) → при нагревании карбонильное соединение',
       invariant='по массовым долям найти соль (RCOO)₂M; при её нагревании образуются карбонат металла и кетон R₂CO '
                 '(из формиата — метаналь)',
       varies='радикал (H, CH₃, C₂H₅, н-C₃H₇, изо-C₃H₇ — с признаком разветвлённости), металл (Ca, Ba)',
       answer_rule='n(Э) = ω/Ar, приведение к одному атому металла; кетон — из двух радикалов соли',
       mistakes=['формула соли записана как RCOOM (забыт второй остаток)', 'продукт пиролиза — альдегид вместо кетона'],
       solve=_solve_salt, solve_steps=_steps_salt, kind='param', kes=KES33,
       fidelity=FID33('банк №33: «Соль органической кислоты содержит 28,48% C, 3,39% H, 21,69% O и 46,44% Ba… при '
                      'нагревании образуется карбонильное соединение» (1D0BD8, A22451); Ar(Ba) = 137, как принято в '
                      'расчётах КИМ (целые Ar)', 'двухвалентный металл — два кислотных остатка'))
def g33_salt(rng):
    R = rng.choice(list(SALT_R))
    metal = rng.choice(['Ca', 'Ba'])
    salt = f'({R}COO)2{metal}'
    a = parse_formula(salt)
    M = molar(salt)
    w = {e: round(Fr(AR[e] * n * 100) / M, 2) for e, n in a.items()}
    order = ['C', 'H', 'O', metal]
    rest = rng.choice([None, 'H', 'O', 'C'])
    ws = ', '.join(f'{fmt(w[e])} % {EL_GEN[e]}' for e in order if e != rest) + \
        (f', остальное — {({"H": "водород", "O": "кислород", "C": "углерод"})[rest]}' if rest else '')
    acid, ket, ketn, br = SALT_R[R]
    extra = '' if br is None else (' Кислотный остаток имеет ' + ('разветвлённый' if br else 'неразветвлённый') +
                                   ' углеродный скелет.')
    q = (f'Соль органической кислоты А содержит по массе {ws}. Известно, что при нагревании вещества А образуется '
         f'карбонильное соединение.{extra}\n'
         + TAIL33.format(eq_task='напишите уравнение реакции разложения вещества А при нагревании') + TRAINER33)
    opts_raw, opts_txt = _formula_opts(rng, a)
    eq = balance([salt], [ket, metal + 'CO3'])
    p = {'w': {k: str(v) for k, v in w.items() if k != rest}, 'rest': rest, 'metal': metal, 'opts': opts_raw,
         'order': order}
    mo = _salt_moles(p)
    e = ('В 100 г: ' + '; '.join(f'n({x}) = {fmt(mo[x], 3)} моль' for x in order)
         + f'; на один атом {metal} — {pretty(hill(a))}, т. е. {pretty(salt)} ({acid} '
         f'{"кальция" if metal == "Ca" else "бария"}). При нагревании: '
         + pretty(eq_str([salt], [ket, metal + 'CO3'], *eq)) + f' ({ketn}).')
    return pcard('ch-ege-33-salt-carbonyl', q, str(opts_raw.index(hill(a)) + 1), e, k='one', o=opts(opts_txt), p=p,
                 eq=([salt], [ket, metal + 'CO3'], eq[0], eq[1]),
                 steps=[(f'n({x}) в 100 г вещества, моль', v) for x, v in zip(order, _steps_salt(p))])


# -------- 33.4: сгорание соли (карбонат в продуктах)
CARB_T = [t for t in T_SALT if set(parse_formula(t['f'])) & {'Na', 'K'}]


def _carb_moles(p):
    M_ = p['metal']
    n_m = 2 * Fr(p['m_carb']) / (2 * AR[M_] + 60)
    nC = Fr(p['V_CO2']) / Fr(224, 10) + n_m / 2
    nH = 2 * Fr(p['m_H2O']) / 18
    nN = 2 * Fr(p.get('V_N2') or 0) / Fr(224, 10)
    mO = Fr(p['m']) - 12 * nC - nH - 14 * nN - AR[M_] * n_m
    return {'C': nC, 'H': nH, 'N': nN, 'O': mO / 16, M_: n_m}


def _solve_carb(p):
    moles = {e: v for e, v in _carb_moles(p).items() if v > 0}
    return str(p['opts'].index(_ratio_to_formula(moles, anchor=(p['metal'], 1))) + 1)


def _steps_carb(p):
    mo = _carb_moles(p)
    return [fmt(mo[e]) for e in ('C', 'H', p['metal'])]


@proto('ch-ege-33-combustion-carbonate', 'ЕГЭ', 33, 'Формула соли (фенолята, алкоголята) по продуктам сгорания с карбонатом',
       invariant='при сгорании натриевой (калиевой) соли металл уходит в карбонат: n(C) = n(CO₂) + n(M₂CO₃), '
                 'n(M) = 2n(M₂CO₃); способ получения из условия — в пункте 3',
       varies='вещество (соли карбоновых кислот, феноляты, алкоголяты, соль аминокислоты), масса пробы',
       answer_rule='учесть углерод карбоната, кислород — по разности масс, привести к одному атому металла',
       mistakes=['забыт углерод в карбонате натрия', 'кислород по разности без учёта массы натрия'],
       solve=_solve_carb, solve_steps=_steps_carb, kind='param', kes=KES33,
       fidelity=FID33('банк №33: «При сгорании 10,8 г вещества А получили 7,84 л CO₂, 5,3 г карбоната натрия и 4,5 г воды» '
                      '(616D73, 8F0DB2, 03cFF6)', 'углерод карбоната'))
def g33_carb(rng):
    t = _fresh(rng, 'carb', CARB_T)
    f = t['f']
    a = parse_formula(f)
    M_ = 'Na' if 'Na' in a else 'K'
    n = rng.choice(NICE_N)
    m = n * molar(f)
    n_carb = n * a[M_] / 2
    m_carb = n_carb * (2 * AR[M_] + 60)
    V = (n * a['C'] - n_carb) * Fr(224, 10)
    mH = n * a['H'] * 9
    if V <= 0:
        raise Retry
    carb = 'карбоната натрия' if M_ == 'Na' else 'карбоната калия'
    txt = rng.choice([f'Навеску органического вещества А массой {dec(m)} г сожгли; образовалось {dec(m_carb)} г {carb}, '
                      f'{dec(V)} л (н.у.) углекислого газа',
                      f'При полном сгорании {dec(m)} г органического вещества А выделилось {dec(V)} л (н.у.) '
                      f'оксида углерода(IV) и образовалось {dec(m_carb)} г {carb}'])
    p = {'m': str(m), 'V_CO2': str(V), 'm_carb': str(m_carb), 'm_H2O': str(mH), 'metal': M_}
    if a.get('N'):
        VN = n * a['N'] * Fr(112, 10)
        txt += f', {dec(VN)} л (н.у.) азота'
        p['V_N2'] = str(VN)
    txt += f' и {dec(mH)} г воды.'
    q = txt + f' {_known(rng)} {_vary(rng, t["clue"])}.\n' + TAIL33.format(eq_task=TK_MAKE) + TRAINER33
    opts_raw, opts_txt = _formula_opts(rng, a)
    p['opts'] = opts_raw
    mo = _carb_moles(p)
    nums = (f'n({M_}₂CO₃) = {fmt(n_carb)} моль → n({M_}) = {fmt(mo[M_])} моль; n(C) = n(CO₂) + n({M_}₂CO₃) = '
            f'{fmt(mo["C"])} моль; n(H) = {fmt(mo["H"])} моль; кислород — по разности масс')
    return pcard('ch-ege-33-combustion-carbonate', q, str(opts_raw.index(hill(a)) + 1), _explain(f, t, nums), k='one',
                 o=opts(opts_txt), p=p, eq=eqt(_t_reaction(t)),
                 steps=list(zip(['n(C), моль', 'n(H), моль', f'n({M_}), моль'], _steps_carb(p))))


# -------- 33.5: сгорание галогенпроизводного / соли амина (HCl, HBr в продуктах)
def _hal_moles(p):
    X = p['X']
    nC = Fr(p['V_CO2']) / Fr(224, 10)
    nX = Fr(p['m_HX']) / (AR[X] + 1) if p.get('m_HX') else Fr(p['V_HX']) / Fr(224, 10)
    nH = 2 * Fr(p['m_H2O']) / 18 + nX
    nN = 2 * Fr(p.get('V_N2') or 0) / Fr(224, 10)
    mO = Fr(p['m']) - 12 * nC - nH - 14 * nN - AR[X] * nX
    return {'C': nC, 'H': nH, 'N': nN, X: nX, 'O': mO / 16}


def _solve_hal(p):
    moles = {e: v for e, v in _hal_moles(p).items() if v > Fr(1, 10 ** 6)}
    return str(p['opts'].index(_ratio_to_formula(moles, anchor=tuple(p['anchor']))) + 1)


def _steps_hal(p):
    mo = _hal_moles(p)
    return [fmt(mo[e]) for e in ('C', 'H', p['X']) + (('N',) if p.get('V_N2') else ())]


@proto('ch-ege-33-combustion-halogen', 'ЕГЭ', 33, 'Формула галогенпроизводного (соли амина) по продуктам сгорания с HCl/HBr',
       invariant='галоген уходит в HX: n(X) = n(HX), водород — в воде и в HX; n(H) = 2n(H₂O) + n(HX); число атомов '
                 'галогена и строение — из способа получения, указанного в условии',
       varies='вещество (продукты присоединения Br₂/Cl₂/HX, хлорирования метана и толуола, бромирования бензола, соли '
              'аминов), масса пробы, HX — объёмом или массой',
       answer_rule='учесть водород в галогеноводороде; способ получения из условия — в пункте 3',
       mistakes=['водород HCl не учтён', 'Ar(Cl) = 35,5', 'число атомов галогена не согласовано с реакцией получения'],
       solve=_solve_hal, solve_steps=_steps_hal, kind='param', kes=KES33,
       fidelity=FID33('банк №33: «При сгорании 13,95 г вещества А получили 5,6 л CO₂ и 6,72 л HCl», «…2,43 г HBr, 90 мг '
                      'воды и 112 мл азота» (29982D, B357BB, 5DB015)', 'водород галогеноводорода'))
def g33_hal(rng):
    # соли аминов и галогенпроизводные — примерно поровну
    amine = rng.random() < 0.45
    grp = [t for t in T_HAL if ('N' in parse_formula(t['f'])) == amine]
    t = _fresh(rng, 'hal', grp)
    f = t['f']
    a = parse_formula(f)
    X = 'Cl' if 'Cl' in a else 'Br'
    n = rng.choice(NICE_N)
    m = n * molar(f)
    nX = n * a[X]
    nH2O = (n * a['H'] - nX) / 2
    if nH2O <= 0:
        raise Retry
    V = n * a['C'] * Fr(224, 10)
    hx = 'хлороводорода' if X == 'Cl' else 'бромоводорода'
    txt = rng.choice([f'Навеску органического вещества А массой {dec(m)} г сожгли; образовалось {dec(V)} л (н.у.) '
                      f'оксида углерода(IV), ',
                      f'Полное сжигание {dec(m)} г органического вещества А дало {dec(V)} л (н.у.) углекислого газа, '])
    p = {'m': str(m), 'V_CO2': str(V), 'm_H2O': str(nH2O * 18), 'X': X, 'anchor': list(t['anchor'])}
    if rng.random() < 0.5:
        txt += f'{dec(nX * Fr(224, 10))} л (н.у.) {hx}'
        p['V_HX'] = str(nX * Fr(224, 10))
    else:
        txt += f'{dec(nX * (AR[X] + 1))} г {hx}'
        p['m_HX'] = str(nX * (AR[X] + 1))
    if a.get('N'):
        VN = n * a['N'] * Fr(112, 10)
        txt += f', {dec(VN)} л (н.у.) азота'
        p['V_N2'] = str(VN)
    txt += f' и {dec(nH2O * 18)} г воды.'
    q = txt + f' {_known(rng)} {_vary(rng, t["clue"])}.\n' + TAIL33.format(eq_task=TK_MAKE) + TRAINER33
    opts_raw, opts_txt = _formula_opts(rng, a)
    p['opts'] = opts_raw
    mo = _hal_moles(p)
    nums = (f'n(C) = {fmt(mo["C"])} моль; n({X}) = n(H{X}) = {fmt(mo[X])} моль; n(H) = 2n(H₂O) + n(H{X}) = '
            f'{fmt(mo["H"])} моль' + (f'; n(N) = {fmt(mo["N"])} моль' if a.get('N') else ''))
    return pcard('ch-ege-33-combustion-halogen', q, str(opts_raw.index(hill(a)) + 1), _explain(f, t, nums), k='one',
                 o=opts(opts_txt), p=p, eq=eqt(_t_reaction(t)),
                 steps=list(zip(['n(C), моль', 'n(H), моль', f'n({X}), моль', 'n(N), моль'], _steps_hal(p))))


# -------- 33.6: многошаговая — сгорание порции + реакция такой же порции
RX33 = {  # класс цели → (реагент в тексте, что измерено, реагент в уравнении, n(A) по измеренному)
    AL_: ('с избытком натрия', 'водорода', 'Na', lambda x: 2 * x / Fr(224, 10), 'V'),
    AC_: ('с избытком раствора гидрокарбоната натрия', 'углекислого газа', 'NaHCO3', lambda x: x / Fr(224, 10), 'V'),
    AD_: ('с избытком аммиачного раствора оксида серебра', 'серебра', 'Ag2O', lambda x: x / 216, 'm'),
    AM_: ('с хлороводородом', 'хлороводорода', 'HCl', lambda x: x / Fr(73, 2), 'm'),
}
def _rx(f, reagent):
    return next((r for r in RX if r['lhs'][0] == f and reagent in r['lhs'][1:] and 'горения' not in r['type']), None)


BR_T = [t for t in T_CHON if t['feats'].get('cls') in RX33 and _rx(t['f'], RX33[t['feats']['cls']][2]) is not None]


def _br_vals(p):
    nC = Fr(p['V_CO2']) / Fr(224, 10)
    nH = 2 * Fr(p['m_H2O']) / 18
    nA = RX33[p['cls']][3](Fr(p['x']))
    M = Fr(p['m']) / nA
    return nC, nH, nA, M


_BR_STRIP = [  # признаки, которые повторяют реакцию из условия, убираются — остаются только признаки строения
    ('вещество А реагирует с натрием, а при окислении оксидом меди(II) образует', 'при окислении оксидом меди(II) вещество А образует'),
    ('вещество А реагирует с натрием с выделением водорода', ''),
    ('при нагревании с аммиачным раствором оксида серебра вещество А образует серебряный налёт', ''),
    (' и вступает в реакцию «серебряного зеркала»', ''),
    ('вещество А реагирует с гидрокарбонатом натрия с выделением газа и имеет', 'вещество А имеет'),
    ('вещество А реагирует с гидрокарбонатом натрия с выделением газа', ''),
]


def _br_clue(clue):
    for a, b in _BR_STRIP:
        clue = clue.replace(a, b)
    return clue.strip()


def _solve_br(p):
    nC, nH, nA, M = _br_vals(p)
    c, h = nC / nA, nH / nA
    nN = 1 if p['cls'] == AM_ else 0
    o = (M - 12 * c - h - 14 * nN) / 16
    f = hill({'C': int(c), 'H': int(h), 'O': int(o), 'N': nN})
    return str(p['opts'].index(f) + 1)


def _steps_br(p):
    nC, nH, nA, M = _br_vals(p)
    return [fmt(nC), fmt(nH), fmt(nA), fmt(M)]


@proto('ch-ege-33-by-reaction', 'ЕГЭ', 33, 'Формула по двум опытам: сгорание порции и реакция такой же порции',
       invariant='из сгорания — n(C), n(H); из реакции той же порции (Na, NaHCO₃, Ag₂O/NH₃, HCl) — n(А) и M(А); '
                 'число атомов C, H — делением на n(А), O — по молярной массе; строение — по признакам',
       varies='класс (спирт, кислота, альдегид, амин) и вещество с однозначными признаками, масса порции',
       answer_rule='n(A) по уравнению реакции → C = n(C)/n(A), H = n(H)/n(A) → O из M(A)',
       mistakes=['для спирта n(H₂) = n(спирта)/2', 'для альдегида n(Ag) = 2n(альдегида)', 'M(A) найдена без учёта '
                                                                                          'стехиометрии'],
       solve=_solve_br, solve_steps=_steps_br, kind='param', kes=KES33,
       fidelity=FID33('банк №33 (5.8): формула по сгоранию + дополнительные данные о реакции (соотношение, объём газа), '
                      'признаки строения', 'стехиометрия реакции (H₂ : спирт = 1 : 2, Ag : альдегид = 2 : 1)'))
def g33_react(rng):
    t = _fresh(rng, 'br', BR_T)
    f = t['f']
    cls = t['feats']['cls']
    a = parse_formula(f)
    rtxt, ptxt, reag, _, kind = RX33[cls]
    r = _rx(f, reag)
    n = rng.choice(NICE_N)
    m = n * molar(f)
    V = n * a['C'] * Fr(224, 10)
    mH = n * a['H'] * 9
    x = {AL_: n / 2 * Fr(224, 10), AC_: n * Fr(224, 10), AD_: n * 216, AM_: n * Fr(73, 2)}[cls]
    meas = f'{dec(x)} л (н.у.) {ptxt}' if kind == 'V' else f'{dec(x)} г {ptxt}'
    verb = 'выделилось' if cls in (AL_, AC_, AD_) else 'прореагировало'
    q = (f'Порцию органического вещества А массой {dec(m)} г сожгли и получили {dec(V)} л (н.у.) углекислого газа и '
         f'{dec(mH)} г воды. При взаимодействии такой же порции вещества А {rtxt} {verb} {meas}.'
         + (f' Известно, что {_vary(rng, _br_clue(t["clue"]))}.' if _br_clue(t['clue']) else '') + '\n'
         + TAIL33.format(eq_task='напишите уравнение реакции вещества А ' + {AL_: 'с натрием', AC_: 'с гидрокарбонатом '
                         'натрия', AD_: 'с аммиачным раствором оксида серебра', AM_: 'с хлороводородом'}[cls])
         + TRAINER33)
    opts_raw, opts_txt = _formula_opts(rng, a)
    p = {'cls': cls, 'm': str(m), 'x': str(x), 'V_CO2': str(V), 'm_H2O': str(mH), 'opts': opts_raw}
    nC, nH, nA, M = _br_vals(p)
    e = (f'n(C) = {fmt(nC)} моль, n(H) = {fmt(nH)} моль; по уравнению {rx_eq(r)} n(А) = {fmt(nA)} моль; '
         f'M(А) = {dec(m)} / {fmt(nA)} = {fmt(M)} г/моль; C : H = {fmt(nC / nA)} : {fmt(nH / nA)} на молекулу → '
         f'{pretty(hill(a))}. Строение: {vw(f)} ({nm(f)}).')
    return pcard('ch-ege-33-by-reaction', q, str(opts_raw.index(hill(a)) + 1), e, k='one', o=opts(opts_txt), p=p,
                 eq=eqt(r), steps=list(zip(['n(C), моль', 'n(H), моль', 'n(А), моль', 'M(А), г/моль'], _steps_br(p))))


recipe('ch-ege-33-full-answer', 'ЕГЭ', 33, 'Установление формулы — полный развёрнутый ответ (формула, структура, уравнение)',
       invariant='три элемента ответа: вычисления и молекулярная формула; структурная формула, однозначно следующая из '
                 'признаков; уравнение реакции из условия со структурными формулами',
       varies='условие — из генераторов ch-ege-33-* (числа, признаки и реакция согласованы с базой)',
       answer_rule='по 1 баллу за каждый элемент (критерии ФИПИ)',
       mistakes=['структура не соответствует признакам (первичный/вторичный спирт, разветвлённость)',
                 'уравнение без коэффициентов'],
       kind='llm', how='условие и эталон берутся из ch-ege-33-* (формула пересчитывается solve(), шаги — solve_steps(), '
                       'структура — единственное вещество базы, удовлетворяющее признакам, уравнение — из базы); ИИ '
                       'проверяет развёрнутый ответ ученика по трём критериям',
       check='эталонная формула и шаги расчёта пересчитаны независимо; структура и уравнение — из базы; оценивание ИИ по '
             'критериям',
       capacity=3000, example={'q': 'При сгорании 4,4 г органического вещества А получили 4,48 л (н.у.) углекислого газа и '
                                    '3,6 г воды. Известно, что при нагревании с раствором гидроксида натрия вещество А '
                                    'образует формиат натрия и вторичный спирт. На основании данных условия задания: '
                                    '1) проведите необходимые вычисления…; 2) составьте структурную формулу…; 3) напишите '
                                    'уравнение реакции вещества А с раствором гидроксида натрия.',
                               'a': '1) n(C) = 0,2 моль, n(H) = 0,4 моль, m(O) = 4,4 − 2,4 − 0,4 = 1,6 г, n(O) = 0,1 моль; '
                                    'C : H : O = 2 : 4 : 1, сложный эфир содержит 2 атома O → C₄H₈O₂; '
                                    '2) H–COO–CH(CH₃)₂ (изопропилформиат); '
                                    '3) H–COO–CH(CH₃)₂ + NaOH → H–COONa + CH₃–CH(OH)–CH₃',
                               'e': 'Простейшая формула C₂H₄O; сложноэфирная группа содержит два атома кислорода — '
                                    'молекулярная формула C₄H₈O₂ (M = 88 г/моль, n(А) = 0,05 моль). Формиат натрия + '
                                    'вторичный спирт C₃ — изопропиловый эфир муравьиной кислоты.'},
       why='структурная формула и уравнение — развёрнутый ответ; автоматически проверяются формула, шаги и выбор структуры',
       kes=KES33, fidelity=FID33('как у ch-ege-33-*', 'структура должна однозначно следовать из признаков'))


# ================================================================= задание 17 (органическая часть): классификация реакций
KES17 = ['1.5', '1.6']
# типы: код → как в перечне КИМ
T17 = {'зам': 'замещения', 'прис': 'присоединения', 'отщ': 'отщепления', 'изом': 'изомеризации', 'обм': 'обмена',
       'разл': 'разложения', 'гидрир': 'гидрирования', 'гидрат': 'гидратации', 'гидрол': 'гидролиза',
       'дегидрир': 'дегидрирования', 'дегидрат': 'дегидратации', 'этериф': 'этерификации', 'нейтр': 'нейтрализации',
       'галоген': 'галогенирования', 'гидрогал': 'гидрогалогенирования', 'дегидрогал': 'дегидрогалогенирования',
       'окисл': 'окисления', 'овр': 'окислительно-восстановительная', 'кат': 'каталитическая',
       'некат': 'некаталитическая', 'обр': 'обратимая', 'необр': 'необратимая', 'гомо': 'гомогенная',
       'гетеро': 'гетерогенная', 'экзо': 'экзотермическая', 'эндо': 'эндотермическая'}
# «выберите две реакции, которые …»
Q17 = {'прис': 'которые являются реакциями присоединения', 'зам': 'которые являются реакциями замещения',
       'отщ': 'которые являются реакциями отщепления', 'обм': 'которые являются реакциями обмена',
       'овр': 'которые являются окислительно-восстановительными', 'неовр': 'которые не являются окислительно-'
       'восстановительными', 'кат': 'которые являются каталитическими', 'гетеро': 'которые являются гетерогенными',
       'гомо': 'которые являются гомогенными', 'экзо': 'которые являются экзотермическими',
       'эндо': 'которые являются эндотермическими', 'обр': 'которые являются обратимыми',
       'необр': 'которые являются необратимыми'}
_PROC = ('гидрир', 'гидрат', 'гидрол', 'дегидрир', 'дегидрат', 'этериф', 'нейтр', 'галоген', 'гидрогал', 'дегидрогал')
# вид реакции → (типы «да», типы «нет», типы «спорно» — не спрашиваются); ОВР — отдельно, пересчётом степеней окисления
_K17 = {
    'HYD': ({'прис', 'гидрир', 'экзо'}, {'зам', 'отщ', 'изом', 'обм', 'разл', 'окисл'}, set()),
    'HALADD': ({'прис', 'галоген', 'экзо'}, {'зам', 'отщ', 'изом', 'обм', 'разл', 'обр'}, {'окисл'}),
    'HX': ({'прис', 'гидрогал', 'экзо'}, {'зам', 'отщ', 'изом', 'обм', 'разл', 'окисл'}, set()),
    'HYDRAT': ({'прис', 'гидрат', 'экзо'}, {'зам', 'отщ', 'изом', 'обм', 'разл', 'окисл', 'гидрол'}, {'обр'}),
    'HALSUB': ({'зам', 'галоген', 'экзо'}, {'прис', 'отщ', 'изом', 'обм', 'разл', 'обр'}, {'окисл'}),
    'DEHYD': ({'отщ', 'дегидрир', 'эндо'}, {'зам', 'прис', 'изом', 'обм', 'окисл'}, {'разл', 'обр'}),
    'DEHYDRAT': ({'отщ', 'дегидрат', 'эндо'}, {'зам', 'прис', 'изом', 'обм', 'окисл'}, {'разл', 'обр'}),
    'DEHX': ({'отщ', 'дегидрогал'}, {'зам', 'прис', 'изом', 'обм', 'окисл', 'обр'}, {'разл'}),
    'DEHAL': ({'отщ'}, {'зам', 'прис', 'изом', 'обм', 'обр'}, {'разл', 'окисл'}),
    'ISO': ({'изом'}, {'зам', 'прис', 'отщ', 'обм', 'разл', 'окисл'}, {'обр'}),
    'ESTER': ({'этериф', 'обр'}, {'прис', 'отщ', 'изом', 'разл', 'окисл', 'нейтр'}, {'зам', 'обм'}),
    'EHYD_A': ({'гидрол', 'обр'}, {'прис', 'отщ', 'изом', 'разл', 'окисл', 'гидрат'}, {'зам', 'обм'}),
    'EHYD_B': ({'гидрол'}, {'прис', 'отщ', 'изом', 'разл', 'окисл', 'гидрат', 'обр'}, {'зам', 'обм', 'нейтр'}),
    'NEUT': ({'обм', 'нейтр', 'экзо'}, {'зам', 'прис', 'отщ', 'изом', 'разл', 'окисл', 'обр'}, set()),
    'BICARB': ({'обм'}, {'зам', 'прис', 'отщ', 'изом', 'разл', 'окисл', 'обр'}, {'нейтр'}),
    'NA': ({'зам', 'экзо'}, {'прис', 'отщ', 'изом', 'обм', 'разл', 'обр'}, {'окисл'}),
    'COMB': ({'окисл', 'экзо'}, {'зам', 'прис', 'отщ', 'изом', 'обм', 'разл', 'обр'}, set()),
    'OX': ({'окисл'}, {'прис', 'отщ', 'изом', 'разл', 'обр'}, {'зам', 'обм'}),
    'DECOMP': ({'разл', 'эндо'}, {'зам', 'прис', 'изом', 'обм'}, {'отщ', 'дегидрир', 'окисл', 'обр'}),
}
_OVR17 = {'HYD': True, 'HALADD': True, 'HX': False, 'HYDRAT': False, 'HALSUB': True, 'DEHYD': True,
          'DEHYDRAT': False, 'DEHX': False, 'DEHAL': True, 'ISO': False, 'ESTER': False, 'EHYD_A': False,
          'EHYD_B': False, 'NEUT': False, 'BICARB': False, 'NA': True, 'COMB': True, 'OX': True, 'DECOMP': True}
_GAS17 = {'CH4', 'C2H6', 'C3H8', 'CH3CH2CH2CH3', 'CH3CH(CH3)CH3', 'C2H4', 'CH2CHCH3', 'CH2CHCH2CH3', 'CH3CHCHCH3',
          'CH2C(CH3)2', 'C2H2', 'CHCCH3', 'CH2CHCHCH2', 'H2', 'O2', 'Cl2', 'HCl', 'HBr', 'CH3Cl', 'HCHO'}
_SOLID17 = {'Na', 'K', 'Zn', 'Mg', 'CuO', 'Cu(OH)2'}
_SOLID_CAT = ('Ni', 'Pt', 'Pd', 'Al2O3', 'Cr2O3', 'ZnO', 'C (акт')
_CAT_MARK = ('кат', 'Ni', 'Pt', 'Pd', 'Hg', 'H+', 'AlCl3', 'FeBr3', 'FeCl3', 'Al2O3', 'Cr2O3', 'ZnO', 'H3PO4',
             'фермент', 'дрожж', 'C (акт')
_INSTR = {'H2': 'водородом', 'Cl2': 'хлором', 'Br2': 'бромом', 'HCl': 'хлороводородом', 'HBr': 'бромоводородом',
          'H2O': 'водой', 'Na': 'натрием', 'K': 'калием', 'NaOH': 'раствором гидроксида натрия',
          'KOH': 'раствором гидроксида калия', 'O2': 'кислородом', 'CuO': 'оксидом меди(II)',
          'Cu(OH)2': 'гидроксидом меди(II)', 'Ag2O': 'аммиачным раствором оксида серебра',
          'Ag(NH3)2OH': 'аммиачным раствором оксида серебра', 'NaHCO3': 'гидрокарбонатом натрия',
          'KHCO3': 'гидрокарбонатом калия', 'Zn': 'цинком', 'Mg': 'магнием'}


def _light(c):
    return any(x in c for x in ('hν', 'hv', 'свет'))


def _kind17(r):
    t, l, c = r['type'], r['lhs'], r.get('cond', '') or ''
    s = l[0]
    if s not in SUB or not SUB[s].get('org') or any(x not in SUB for x in l + r['rhs']):
        return None
    cls = SUB[s]['cls']
    two = l[1] if len(l) > 1 else None
    if len(l) > 2 and not (len(l) == 3 and l[2] == 'H2O' and two == 'Br2'):
        return None
    if 'горения' in t:
        return 'COMB' if two == 'O2' and len(r['rhs']) == 2 else None
    if 'гидрирования' in t and two == 'H2':
        return 'HYD'
    if 'гидрогалогенирования' in t:
        return 'HX'
    if 'галогенирования' in t and two in ('Br2', 'Cl2'):
        if 'присоединения' in t:
            return 'HALADD'
        if 'замещения' in t:
            return 'HALSUB'
    if 'гидратации' in t and two == 'H2O':
        return 'HYDRAT'
    if t == ['изомеризации']:
        return 'ISO'
    if 'дегидрирования' in t and two is None and len(r['rhs']) == 2 and 'разложения' not in t and \
            SUB[s]['hom'] == 'алканы' and SUB[r['rhs'][0]]['hom'] in ('алкены', 'алкадиены'):
        return 'DEHYD'
    if 'дегидратации' in t and two is None and SUB[r['rhs'][0]]['cls'] == 'углеводород' and len(r['rhs']) == 2:
        return 'DEHYDRAT'
    if 'дегидрогалогенирования' in t and two in ('KOH', 'NaOH'):
        return 'DEHX'
    if 'дегалогенирования' in t and two in ('Zn', 'Mg') and SUB[r['rhs'][0]]['hom'] in ('алкены', 'алкины'):
        return 'DEHAL'
    if 'этерификации' in t and two in SUB and SUB[two]['cls'] == 'карбоновая кислота' and cls == 'спирт':
        return 'ESTER'
    if 'этерификации' in t and cls == 'карбоновая кислота' and two in SUB and SUB[two]['cls'] == 'спирт':
        return 'ESTER'
    if 'гидролиза' in t and cls == 'сложный эфир' and SUB[s]['hom'] == 'сложные эфиры':
        if two == 'H2O' and 'H+' in c:
            return 'EHYD_A'
        if two in ('NaOH', 'KOH'):
            return 'EHYD_B'
    if 'нейтрализации' in t and two in ('NaOH', 'KOH') and cls == 'карбоновая кислота':
        return 'NEUT'
    if two in ('NaHCO3', 'KHCO3') and cls == 'карбоновая кислота':
        return 'BICARB'
    if two in ('Na', 'K') and cls in ('спирт', 'карбоновая кислота') and 'замещения' in t:
        return 'NA'
    if two in ('Ag2O', 'Ag(NH3)2OH', 'Cu(OH)2') and cls == 'альдегид' and 'окисления' in t:
        return 'OX'
    if two == 'CuO' and cls == 'спирт' and 'окисления' in t:
        return 'OX'
    if s == 'CH4' and 'разложения' in t and two is None:
        return 'DECOMP'
    return None


_FIX_OX = {'H': 1, 'O': -2, 'F': -1, 'Cl': -1, 'Br': -1, 'I': -1, 'Na': 1, 'K': 1, 'Li': 1, 'Ca': 2, 'Mg': 2,
           'Ba': 2, 'Zn': 2, 'Al': 3}


def _ox_tot(f):
    """Суммарные степени окисления элементов в частице (средние для углерода, как в школьном курсе)."""
    a = parse_formula(f)
    if len(a) == 1:
        return {e: 0 for e in a}
    out = {e: _FIX_OX[e] * n for e, n in a.items() if e in _FIX_OX}
    var = [e for e in a if e not in _FIX_OX]
    if 'N' in var and 'C' in var:
        hom = SUB.get(f, {}).get('hom', '')
        out['N'] = a['N'] * (3 if hom.startswith('нитро') else 5 if 'азотной' in hom or 'целлюлозы' in hom else -3)
        var.remove('N')
    if not var:
        return out if sum(out.values()) == 0 else None
    if len(var) != 1:
        return None
    out[var[0]] = -sum(out.values())
    return out


def ovr_calc(r):
    """ОВР ли реакция: меняется ли сумма степеней окисления какого-либо элемента (по уравнению с коэффициентами)."""
    try:
        kl, kr = r.get('k') or balance(r['lhs'], r['rhs'])
    except Exception:
        return None
    tot = defaultdict(int)
    for side, fs, ks in ((1, r['lhs'], kl), (-1, r['rhs'], kr)):
        for f, k in zip(fs, ks):
            o = _ox_tot(f)
            if o is None:
                return None
            for e, v in o.items():
                tot[e] += side * k * v
    return any(v != 0 for v in tot.values())


def cls17(r):
    """Признаки реакции: код → True/False; спорные признаки отсутствуют."""
    k = _kind17(r)
    if k is None:
        return None
    yes, no, dis = _K17[k]
    out = {x: True for x in yes}
    out.update({x: False for x in no})
    for x in _PROC:  # названия процессов: только «свой» процесс
        if x not in yes and x not in dis:
            out.setdefault(x, False)
    for x in ('зам', 'прис', 'отщ', 'изом', 'обм', 'разл', 'окисл'):
        if x not in yes and x not in dis:
            out.setdefault(x, False)
    o = ovr_calc(r)
    if o is None or o != _OVR17[k]:
        return None  # школьная классификация не подтверждена пересчётом — реакцию не используем
    out['овр'] = o
    c = r.get('cond', '') or ''
    lhs = r['lhs']
    if any(m in c for m in _CAT_MARK):
        out['кат'] = True
    elif 'H2SO4' in c and 'H2SO4' not in lhs:
        pass  # конц. H₂SO₄ — катализатор или водоотнимающее средство: спорно
    elif k in ('NA', 'NEUT', 'BICARB', 'HALADD', 'HALSUB', 'COMB', 'DEHX', 'DEHAL', 'OX', 'EHYD_B', 'HX', 'DECOMP'):
        out['кат'] = False
    if 'кат' in out:
        out['некат'] = not out['кат']
    if 'обр' in yes:
        out['необр'] = False
    elif 'обр' in no:
        out['необр'] = True
    if 'экзо' in yes:
        out['эндо'] = False
    elif 'эндо' in yes:
        out['экзо'] = False
    # фазы — по реагентам (как в банке); реакции на твёрдом катализаторе в вопросы о фазах не берём
    solid = any(x in _SOLID17 for x in lhs)
    if any(m in c for m in _SOLID_CAT):
        pass
    elif solid:
        out['гетеро'], out['гомо'] = True, False
    elif all(x in _GAS17 for x in lhs) and (_light(c) or k == 'COMB') and not any(m in c for m in _SOLID_CAT):
        out['гетеро'], out['гомо'] = False, True
    elif k == 'ESTER':
        out['гетеро'], out['гомо'] = False, True
    if k == 'HALSUB' and not _light(c):
        out.pop('экзо', None)  # ароматическое замещение: тепловой эффект в курсе не обсуждается
        out.pop('эндо', None)
    return out


def _acid_instr(name):
    m = re.match(r'^(\S+)ая кислота$', name)
    return f'{m.group(1)}ой кислотой' if m else None


def desc17(r, rng, style):
    """Словесное описание реакции, как в перечнях КИМ. style: 'inter' — «взаимодействие A с B», 'proc' — название
    процесса («гидрирование …»)."""
    k = _kind17(r)
    s, l, c = r['lhs'][0], r['lhs'], r.get('cond', '') or ''
    g = gen(nm(s, rng))
    two = l[1] if len(l) > 1 else None
    light = ' на свету' if _light(c) else ''
    if k == 'HALSUB' and not light:
        cat = 'бромида железа(III)' if 'FeBr3' in c else 'хлорида железа(III)' if 'FeCl3' in c else \
            'хлорида алюминия' if 'AlCl3' in c else None
        light = f' в присутствии {cat}' if cat else ''
        if not cat and 'водн' not in c and 'бромная' not in c:
            return None
    proc = {'HYD': f'гидрирование {g}', 'HX': ('гидробромирование ' if two == 'HBr' else 'гидрохлорирование ') + g,
            'HYDRAT': f'гидратация {g}', 'DEHYD': f'дегидрирование {g}', 'DEHYDRAT': f'внутримолекулярная '
            f'дегидратация {g}', 'ISO': f'изомеризация {g}', 'COMB': f'горение {g}',
            'EHYD_A': f'кислотный гидролиз {g}', 'EHYD_B': f'щелочной гидролиз {g}',
            'HALSUB': ('бромирование ' if two == 'Br2' else 'хлорирование ') + g + light,
            'DECOMP': 'разложение метана до простых веществ' if r['rhs'][0] == 'C' else 'разложение метана при 1500 °C'}
    if k == 'DECOMP':
        return proc[k]
    if k == 'HALSUB' and ('водн' in c or 'бромная' in c):
        return f'взаимодействие {g} с бромной водой'
    if k == 'ESTER':
        acid, alc = (two, s) if SUB[s]['cls'] == 'спирт' else (s, two)
        ai = _acid_instr(SUB[acid]['name'])
        return f'взаимодействие {gen(nm(alc, rng))} с {ai}' if ai else None
    if k == 'DEHX':
        return f'взаимодействие {g} со спиртовым раствором {"гидроксида калия" if two == "KOH" else "гидроксида натрия"}'
    if k in ('ISO', 'DEHYD', 'DEHYDRAT') and style == 'inter':
        return f'получение {gen(nm(r["rhs"][0], rng))} из {g}'
    if (style == 'proc' or k == 'COMB') and k in proc:
        return proc[k]
    if k == 'EHYD_A':
        return f'взаимодействие {g} с водой в кислой среде'
    if two == 'Br2' and ('водн' in c or 'бромная' in c or 'H2O' in l):
        return f'взаимодействие {g} с бромной водой'
    if two in _INSTR:
        return f'взаимодействие {g} с {_INSTR[two]}{light}'
    return proc.get(k)


def _rx_key(r):
    return [list(r['lhs']), list(r['rhs']), r.get('cond', '') or '']


def _rx_by_key(key):
    lhs, rhs, cond = key
    return next(r for r in RX if r['lhs'] == lhs and r['rhs'] == rhs and (r.get('cond', '') or '') == cond)


RX17 = []
_seen17 = set()
for _r in RX:
    _c = cls17(_r)
    if _c and (parse_formula(_r['lhs'][0]).get('C', 0) <= 6 or _r['lhs'][0] == 'C6H5CH3') \
            and all('(' not in SUB[x]['name'] for x in _r['lhs'] if SUB[x].get('org')) \
            and SUB[_r['lhs'][0]]['hom'] not in ('жиры', 'полисахариды', 'двухосновные карбоновые кислоты'):
        _d = desc17(_r, None, 'inter')
        if _d and _d not in _seen17:
            _seen17.add(_d)
            RX17.append(_r)
FID17 = lambda scale, trap, fmt_: fid(fmt_, 'Б', 2, scale, trap, KES17, SC1)
MANY17 = 'пять вариантов, ответ — все верные цифры (две–три), порядок не важен'


def _solve17_types(p):
    c = cls17(_rx_by_key(p['rx']))
    return [str(i + 1) for i, x in enumerate(p['opts']) if c[x]]


def _by_kind(rng, rs, n):
    """n реакций разных видов (сначала вид, потом реакция — чтобы гидрирование и горение не вытесняли остальное)."""
    g = defaultdict(list)
    for r in rs:
        g[_kind17(r)].append(r)
    if len(g) < n:
        raise Retry
    return [rng.choice(g[k]) for k in rng.sample(sorted(g), n)]


def _gen17_types(pid, rng, n_true):
    r = _by_kind(rng, RX17, 1)[0]
    c = cls17(r)
    kinds = [x for x in c if x in T17]
    yes = [x for x in kinds if c[x]]
    no = [x for x in kinds if not c[x]]
    k_yes = n_true if n_true else rng.choice([2, 2, 3])
    if len(yes) < k_yes or len(no) < 5 - k_yes:
        raise Retry
    # отвлекающие — сначала «соседние» типы (как в банке: гидратации ↔ гидролиза, замещения ↔ присоединения)
    pick = rng.sample(yes, k_yes) + rng.sample(no, 5 - k_yes)
    if len({T17[x] for x in pick}) < 5:
        raise Retry
    if ('кат' in pick and 'некат' in pick) or ('экзо' in pick and 'эндо' in pick) or \
            ('обр' in pick and 'необр' in pick) or ('гомо' in pick and 'гетеро' in pick):
        raise Retry  # взаимоисключающие пары в одном перечне банк не даёт
    rng.shuffle(pick)
    d = desc17(r, rng, 'inter')
    # формулировка банка («к которым можно отнести …») встречается в нём менее 40 раз и не считается типовой —
    # используем близкие по смыслу, чтобы не совпадать с конкретными заданиями
    tail = rng.choice([f'к которым относится {d}', f'которые характеризуют {d}' if not d.startswith('получение')
                       else f'к которым относится {d}'])
    if n_true:
        q = q_many('два', 'типа реакций', tail)
    else:
        q = q_many('все', 'типы реакций', tail)
    good = [i for i, x in enumerate(pick) if c[x]]
    e = (f'{rx_eq(r)}. ' + '; '.join(f'{T17[x]} — {"да" if c[x] else "нет"}' for x in pick) + '.')
    return many_card(pid, q, [T17[x] for x in pick], good, e, {'rx': _rx_key(r), 'opts': pick}, eqs=[eqt(r)])


@proto('ch-ege-17-org-types-all', 'ЕГЭ', 17, 'Органическая реакция → все типы, к которым её можно отнести',
       invariant='одна реакция органического вещества; классифицировать по механизму (замещение, присоединение, '
                 'отщепление, изомеризация, обмен), по названию процесса, по ОВР, катализатору, обратимости, фазам, '
                 'тепловому эффекту',
       varies='реакция из базы (гидрирование, галогенирование, гидратация, дегидратация, этерификация, гидролиз эфиров, '
              'реакции с натрием, горение …), пять типов в перечне',
       answer_rule='записать уравнение, определить тип по составу реагентов и продуктов; ОВР — по изменению степеней '
                   'окисления',
       mistakes=['гидратация спутана с гидролизом', 'реакция спирта с натрием — замещение и ОВР, а не обмен',
                 'гидрирование на никеле — гетерогенная каталитическая реакция'],
       solve=_solve17_types, kind='dict', kes=KES17,
       fidelity=FID17('банк №17: «выберите все типы реакций, к которым можно отнести взаимодействие этилена с водородом '
                      '(ацетилена с водой, пропана с хлором на свету)»', 'ОВР и гомо/гетерогенность вместе с '
                      'механизмом', MANY17))
def g17_types_all(rng):
    return _gen17_types('ch-ege-17-org-types-all', rng, 0)


@proto('ch-ege-17-org-types-two', 'ЕГЭ', 17, 'Органическая реакция → два типа, к которым её можно отнести',
       invariant='одна реакция органического вещества; ровно два верных типа из пяти',
       varies='реакция из базы, пять типов (механизм, название процесса, обратимость, катализ, тепловой эффект)',
       answer_rule='определить механизм и частный тип процесса',
       mistakes=['этерификация — обратимая реакция, а не нейтрализация', 'дегидрирование — эндотермическая реакция'],
       solve=_solve17_types, kind='dict', kes=KES17,
       fidelity=FID17('банк №17: «выберите два типа реакций, к которым можно отнести взаимодействие этанола с '
                      'пропионовой кислотой (бензола с водородом, получение метилпропана из н-бутана)»',
                      'соседние названия процессов (гидрирования/гидратации/гидролиза)', MANY2))
def g17_types_two(rng):
    return _gen17_types('ch-ege-17-org-types-two', rng, 2)


def _solve17_rx(p):
    out = []
    for i, key in enumerate(p['rxs']):
        c = cls17(_rx_by_key(key))
        v = (not c['овр']) if p['feat'] == 'неовр' else c[p['feat']]
        if v:
            out.append(str(i + 1))
    return out


@proto('ch-ege-17-org-two-reactions', 'ЕГЭ', 17, 'Пять органических реакций → две, обладающие признаком',
       invariant='по словесному описанию реакции определить её тип (механизм, ОВР, катализ, фазы, тепловой эффект, '
                 'обратимость)',
       varies='признак (присоединение, замещение, отщепление, обмен, ОВР / не ОВР, каталитические, гетерогенные, '
              'гомогенные, экзо-/эндотермические, обратимые); пять реакций из базы',
       answer_rule='для каждой реакции записать схему и определить признак',
       mistakes=['хлорирование метана — замещение, а не присоединение', 'гидратация пропина — не ОВР',
                 'нейтрализация — не гетерогенная, если кислота и щёлочь в растворе'],
       solve=_solve17_rx, kind='dict', kes=KES17,
       fidelity=FID17('банк №17: «выберите две реакции, которые являются реакциями присоединения» (окисление метанола, '
                      'гидрирование ацетальдегида, гидратация пропина …), «две гетерогенные», «две эндотермические»',
                      'реакции одного вещества с разными реагентами', MANY2))
def g17_two_rx(rng):
    feat = rng.choice(sorted(Q17))
    key = 'овр' if feat == 'неовр' else feat

    def val(c):
        if key not in c:
            return None
        return (not c[key]) if feat == 'неовр' else c[key]
    cand = [(r, cls17(r)) for r in RX17]
    cand = [(r, c) for r, c in cand if val(c) is not None]
    yes = [r for r, c in cand if val(c)]
    no = [r for r, c in cand if not val(c)]
    if len(yes) < 2 or len(no) < 3:
        raise Retry
    rs = _by_kind(rng, yes, 2) + _by_kind(rng, no, 3)
    style = rng.choice(['proc', 'inter', 'mix'])
    texts = [desc17(r, rng, style if style != 'mix' else rng.choice(['proc', 'inter'])) for r in rs]
    if None in texts or len(set(texts)) < 5 or len({r['lhs'][0] for r in rs}) < 4:
        raise Retry
    order = list(range(5))
    rng.shuffle(order)
    rs, texts = [rs[i] for i in order], [texts[i] for i in order]
    q = q_many('две', 'реакции', Q17[feat])
    good = [i for i, r in enumerate(rs) if val(cls17(r))]
    e = '; '.join(f'{t} ({rx_eq(r)}) — {"да" if val(cls17(r)) else "нет"}' for t, r in zip(texts, rs)) + '.'
    return many_card('ch-ege-17-org-two-reactions', q, texts, good, e,
                     {'feat': feat, 'rxs': [_rx_key(r) for r in rs]}, eqs=[eqt(r) for r in rs])


# ================================================================= задание 24 (органическая часть): качественные реакции
KES24 = ['2.5', '3.19']
# признаки (коды → текст для столбца «признак реакции»)
SIGN24 = {'dec': 'обесцвечивание раствора', 'decw': 'обесцвечивание раствора и образование белого осадка',
          'mir': 'образование «серебряного зеркала»', 'agp': 'образование серовато-белого осадка',
          'red': 'образование кирпично-красного осадка',
          'blue': 'растворение осадка и образование ярко-синего раствора', 'viol': 'появление фиолетовой окраски',
          'gas': 'выделение газа', 'none': 'видимые признаки реакции отсутствуют', 'iod': 'появление синей окраски',
          'bluea': 'растворение осадка', 'decg': 'обесцвечивание раствора и выделение газа'}
# реактивы (коды → подписи, как в банке)
REAG24 = {'Br2': ['Br₂ (водн.)', 'бромная вода'], 'KMnO4': ['KMnO₄ (H⁺)'],
          'Ag': ['[Ag(NH₃)₂]OH', 'Ag₂O (NH₃ р-р)'], 'Cu': ['Cu(OH)₂'], 'Cut': ['Cu(OH)₂ (t°)'],
          'Fe': ['FeCl₃', 'FeCl₃ (р-р)'], 'HCO3': ['NaHCO₃', 'KHCO₃'], 'Na': ['Na', 'K'], 'NaOH': ['NaOH', 'KOH'],
          'I2': ['I₂ (р-р)'], 'HCl': ['HCl (р-р)'], 'Cu0': ['Cu'], 'AcK': ['CH₃COOK'], 'KCl': ['KCl']}
_INERT24 = ('HCl', 'Cu0', 'AcK', 'KCl')  # реактивы, не дающие видимых признаков с веществами перечня
_N = None  # «неизвестно / спорно» — такое сочетание в задание не попадает
# признаки по гомологическому ряду: Br2, KMnO4, Ag, Cu, Cut, Fe, HCO3, Na, NaOH, I2
_R24 = ('Br2', 'KMnO4', 'Ag', 'Cu', 'Cut', 'Fe', 'HCO3', 'Na', 'NaOH', 'I2')
_HOM24 = {
    'алканы': ('none', 'none', 'none', 'none', 'none', 'none', 'none', 'none', 'none', 'none'),
    'циклоалканы': ('none', 'none', 'none', 'none', 'none', 'none', 'none', 'none', 'none', 'none'),
    'алкены': ('dec', 'dec', 'none', 'none', 'none', 'none', 'none', 'none', 'none', _N),
    'циклоалкены': ('dec', 'dec', 'none', 'none', 'none', 'none', 'none', 'none', 'none', _N),
    'алкадиены': ('dec', 'dec', 'none', 'none', 'none', 'none', 'none', 'none', 'none', _N),
    'предельные одноатомные спирты': ('none', 'dec', 'none', 'none', _N, 'none', 'none', 'gas', 'none', _N),
    'многоатомные спирты': ('none', 'dec', 'none', 'blue', _N, 'none', 'none', 'gas', 'none', _N),
    'предельные альдегиды': ('dec', 'dec', 'mir', 'none', 'red', 'none', 'none', _N, _N, _N),
    'кетоны': ('none', 'none', 'none', 'none', 'none', 'none', 'none', _N, _N, _N),
    'предельные одноосновные карбоновые кислоты': ('none', 'none', 'none', 'bluea', _N, _N, 'gas', 'gas', 'none', _N),
    'сложные эфиры': ('none', 'none', 'none', 'none', 'none', 'none', 'none', _N, _N, _N),
    'простые эфиры': ('none', _N, 'none', 'none', 'none', 'none', 'none', 'none', 'none', _N),
}
_SUB24 = {  # отдельные вещества (переопределяют ряд); подпись в перечне
    'C6H6': (('none', 'none', 'none', 'none', 'none', 'none', 'none', 'none', 'none', _N), None),
    'C6H5CH3': (('none', 'dec', 'none', 'none', 'none', 'none', 'none', 'none', 'none', _N), None),
    'C6H5CHCH2': (('dec', 'dec', 'none', 'none', 'none', 'none', 'none', 'none', 'none', _N), None),
    'C2H2': (('dec', 'dec', 'agp', 'none', _N, 'none', 'none', _N, 'none', _N), None),
    'CHCCH3': (('dec', 'dec', 'agp', 'none', _N, 'none', 'none', _N, 'none', _N), None),
    'CHCCH2CH3': (('dec', 'dec', 'agp', 'none', _N, 'none', 'none', _N, 'none', _N), None),
    'CH3CCCH3': (('dec', 'dec', 'none', 'none', _N, 'none', 'none', _N, 'none', _N), None),
    'C6H5OH': (('decw', 'dec', _N, 'none', _N, 'viol', 'none', _N, 'none', _N), 'фенол (р-р)'),
    'C6H5NH2': (('decw', _N, _N, _N, _N, _N, 'none', _N, 'none', _N), None),
    'HCHO': (('dec', 'dec', 'mir', 'none', 'red', 'none', 'none', _N, _N, _N), 'формальдегид (р-р)'),
    'HCOOH': (('dec', 'dec', 'mir', 'bluea', 'red', _N, 'gas', 'gas', 'none', _N), None),
    'CH2CHCOOH': (('dec', 'dec', _N, 'bluea', _N, _N, 'gas', 'gas', 'none', _N), None),
    'C6H5COOH': (('none', 'none', 'none', _N, _N, _N, 'gas', _N, _N, _N), None),
    'HCOOCH3': ((_N, _N, 'mir', 'none', _N, 'none', 'none', _N, _N, _N), None),
    'HCOOC2H5': ((_N, _N, 'mir', 'none', _N, 'none', 'none', _N, _N, _N), None),
    'C6H12O6': (('dec', 'dec', 'mir', 'blue', 'red', 'none', 'none', _N, 'none', 'none'), 'глюкоза (р-р)'),
    'HOCH2(CHOH)3COCH2OH': (('none', _N, _N, 'blue', _N, 'none', 'none', _N, _N, 'none'), 'фруктоза (р-р)'),
    'C12H22O11': (('none', _N, 'none', 'blue', _N, 'none', 'none', _N, 'none', 'none'), 'сахароза (р-р)'),
    'C6H10O5': (('none', _N, 'none', 'none', _N, 'none', 'none', _N, 'none', 'iod'), 'крахмал'),
}
_POOL24_F = ['CH3(CH2)4CH3', 'CH3(CH2)3CH3', '(CH2)6', 'C6H6', 'C6H5CH3', 'C6H5CHCH2', 'C2H4', 'CH2CHCH3',
             'CH2CHCH2CH3', 'CH3CHCHCH3', 'CH3CHCHCH2CH3', 'C6H10', 'CH2CHCHCH2', 'CH2C(CH3)CHCH2', 'C2H2', 'CHCCH3',
             'CHCCH2CH3', 'CH3CCCH3', 'CH3OH', 'C2H5OH', 'CH3CH2CH2OH', 'CH3CH(OH)CH3', 'CH3(CH2)3OH',
             'C2H4(OH)2', 'C3H5(OH)3', 'CH3CH(OH)CH(OH)CH3', 'C6H5OH', 'C6H5NH2', 'HCHO', 'CH3CHO', 'CH3CH2CHO',
             'CH3(CH2)2CHO', 'CH3COCH3', 'CH3COCH2CH3', 'HCOOH', 'CH3COOH', 'CH3CH2COOH', 'CH2CHCOOH', 'C6H5COOH',
             'CH3COOC2H5', 'CH3COOCH3', 'HCOOCH3', 'HCOOC2H5', 'C2H5OC2H5', 'C6H12O6', 'HOCH2(CHOH)3COCH2OH',
             'C12H22O11', 'C6H10O5']
_GAS24 = {'C2H4', 'CH2CHCH3', 'CH2CHCH2CH3', 'CH3CHCHCH3', 'C2H2', 'CHCCH3', 'CHCCH2CH3', 'CH2CHCHCH2', 'HCHO'}


def sign24(f, rk):
    """Признак реакции вещества f с реактивом rk (код из SIGN24) или None (спорно / не используется)."""
    if rk in _INERT24:
        return None if (rk == 'HCl' and f == 'C6H5NH2') else 'none'
    row = _SUB24[f][0] if f in _SUB24 else _HOM24.get(SUB[f]['hom'])
    if row is None:
        return None
    v = row[_R24.index(rk)]
    if v and f in _GAS24 and rk == 'Na':
        return None
    if v and v != 'none' and rk in _RX24:
        rs = [r for r in RX if r['lhs'][0] == f and any(x in r['lhs'][1:] for x in _RX24[rk])
              and (rk != 'KMnO4' or 'H2SO4' in r['lhs'])]
        if rk == 'KMnO4' and not rs:
            return None  # подкисленный KMnO₄: без реакции в базе не знаем, выделяется ли CO₂
        if any('CO2' in r['rhs'] for r in rs):  # признак «газ» вместе с основным
            return 'decg' if v == 'dec' else None
    return v


_RX24 = {'KMnO4': ('KMnO4',), 'Br2': ('Br2',), 'Ag': ('Ag2O', 'Ag(NH3)2OH'), 'Cut': ('Cu(OH)2',)}


def _coarse24(v):
    return {'bluea': 'blue', 'decg': 'dec'}.get(v, v)


def label24(f, rng):
    lab = _SUB24.get(f, (None, None))[1]
    return lab or nm(f, rng)


POOL24 = [f for f in _POOL24_F if f in SUB]


def _check24():
    """Сверка таблицы с базой реакций: где таблица говорит «реагирует с признаком», в базе должна быть реакция с этим
    реактивом (для Br₂, Ag, Cu(OH)₂ (t°), NaHCO₃, Na)."""
    need = {'Br2': ('Br2',), 'Ag': ('Ag2O', 'Ag(NH3)2OH'), 'Cut': ('Cu(OH)2',), 'HCO3': ('NaHCO3', 'KHCO3'),
            'Na': ('Na', 'K')}
    bad = []
    for f in POOL24:
        for rk, xs in need.items():
            v = sign24(f, rk)
            if v and v != 'none' and not any(r['lhs'][0] == f and any(x in r['lhs'][1:] for x in xs) for r in RX):
                bad.append((f, rk))
    return bad


_BAD24 = set(_check24())


def distinguish24(a, b, rk):
    """Реактив различает вещества: оба признака известны и различны."""
    if (a, rk) in _BAD24 or (b, rk) in _BAD24:
        return None
    x, y = sign24(a, rk), sign24(b, rk)
    if x is None or y is None:
        return None
    return _coarse24(x) != _coarse24(y)


def _solve24_pairs(p):
    out = {}
    for i, (a, b) in enumerate(p['left']):
        good = [n for n, rk in enumerate(p['right']) if distinguish24(a, b, rk)]
        out[LET[i]] = str(good[0] + 1)
    return out


FID24 = lambda scale, trap: fid(MATCH45, 'П', 4, scale, trap, KES24, SC2)
MATCH45 = 'четыре позиции (А–Г), пять вариантов (1–5); ответ — четыре цифры, цифры могут повторяться'


@proto('ch-ege-24-org-pair-reagent', 'ЕГЭ', 24, 'Два органических вещества → реактив, с помощью которого их можно '
                                               'различить',
       invariant='реактив различает вещества, если с одним из них даёт видимый признак, а с другим — другой признак '
                 'или никакого',
       varies='четыре пары (углеводороды, спирты, фенол, альдегиды, кетоны, кислоты, эфиры, углеводы), пять реактивов '
              '(бромная вода, KMnO₄, аммиачный раствор Ag₂O, Cu(OH)₂, FeCl₃, NaHCO₃, Na, соли-«пустышки»)',
       answer_rule='для каждой пары перебрать реактивы: подходит тот, что даёт с веществами разные признаки',
       mistakes=['алкен и альдегид оба обесцвечивают бромную воду', 'кислота и многоатомный спирт оба растворяют '
                                                                   'Cu(OH)₂', 'бензол и гексан KMnO₄ не различает'],
       solve=_solve24_pairs, kind='dict', kes=KES24,
       fidelity=FID24('банк №24: «соответствие между двумя веществами и реактивом, с помощью которого можно различить '
                      'эти вещества» (пропаналь и метилбензол, фенол и гексан, этанол и глицерин …)',
                      'реактив, дающий одинаковый признак с обоими веществами'))
def g24_pairs(rng):
    reags = [r for r in REAG24 if r not in _INERT24]
    n_real = rng.choice([3, 4, 4, 5])
    right = rng.sample(reags, n_real) + rng.sample(list(_INERT24), 5 - n_real)
    rng.shuffle(right)
    # кандидаты: пары, для которых все пять реактивов определены и различает ровно один
    cand = defaultdict(list)
    for x in range(len(POOL24)):
        for y in range(x + 1, len(POOL24)):
            a, b = POOL24[x], POOL24[y]
            ds = [distinguish24(a, b, rk) for rk in right]
            if None in ds or sum(ds) != 1:
                continue
            cand[right[ds.index(True)]].append((a, b))
    keys = sorted(cand)
    if len(keys) < 3:
        raise Retry
    pairs, used = [], set()
    ks = rng.sample(keys, min(4, len(keys)))
    while len(ks) < 4:
        ks.append(rng.choice(keys))
    for k in ks:
        opts_ = [pr for pr in cand[k] if not set(pr) & used]
        if not opts_:
            raise Retry
        pr = rng.choice(opts_)
        if rng.random() < 0.5:
            pr = pr[::-1]
        pairs.append(pr)
        used |= set(pr)
    rng.shuffle(pairs)
    lt = [f'{label24(a, rng)} и {label24(b, rng)}' for a, b in pairs]
    rt = [rng.choice(REAG24[rk]) for rk in right]
    if len(set(rt)) < 5 or len(set(lt)) < 4:
        raise Retry
    head = rng.choice(['двумя веществами и реактивом, с помощью которого можно различить эти вещества',
                       'двумя веществами и реагентом, с помощью которого можно различить эти вещества'])
    q = mq(head, 'ВЕЩЕСТВА', 'РЕАКТИВ')
    ans = [next(n for n, rk in enumerate(right) if distinguish24(a, b, rk)) for a, b in pairs]
    e = '; '.join(f'{lt[i]}: {rt[ans[i]]} — {SIGN24[sign24(a, right[ans[i]])]} / {SIGN24[sign24(b, right[ans[i]])]}'
                  for i, (a, b) in enumerate(pairs)) + '.'
    return match_card('ch-ege-24-org-pair-reagent', rng, q, lt, rt, ans, e,
                      {'left': [list(x) for x in pairs], 'right': right})


def _solve24_sign(p):
    out = {}
    for i, (f, rk) in enumerate(p['left']):
        v = sign24(f, rk)
        out[LET[i]] = str(p['right'].index(v) + 1)
    return out


@proto('ch-ege-24-org-sign', 'ЕГЭ', 24, 'Органическое вещество + реактив → признак реакции',
       invariant='качественные реакции: обесцвечивание бромной воды и KMnO₄, «серебряное зеркало», кирпично-красный '
                 'Cu₂O, ярко-синий раствор с Cu(OH)₂, фиолетовая окраска с FeCl₃, газ с Na и NaHCO₃',
       varies='четыре пары «вещество — реактив», пять признаков (в т. ч. «признаки отсутствуют»)',
       answer_rule='определить, идёт ли реакция и что наблюдается',
       mistakes=['фенол с бромной водой — не только обесцвечивание, но и белый осадок',
                 'альдегид с Cu(OH)₂ без нагревания признаков не даёт', 'бензол не обесцвечивает KMnO₄'],
       solve=_solve24_sign, kind='dict', kes=KES24,
       fidelity=FID24('банк №24: «соответствие между реагирующими веществами и признаком протекающей между ними '
                      'реакции» (фенол и FeCl₃, пентен-2 и Br₂ (водн.), этаналь и Cu(OH)₂ (t°) …)',
                      'признаки-«соседи»: обесцвечивание / обесцвечивание и осадок; растворение осадка'))
def g24_sign(rng):
    rows = []
    reags = [r for r in REAG24 if r not in _INERT24]
    for _ in range(80):
        f = rng.choice(POOL24)
        rk = rng.choice(reags)
        v = sign24(f, rk)
        if v is None or v == 'bluea' or (f, rk) in _BAD24 or any(x[0] == f for x in rows):
            continue
        if v == 'none' and sum(sign24(x[0], x[1]) == 'none' for x in rows) >= 1:
            continue  # «признаков нет» — не больше одной позиции, как в банке
        if sum(sign24(x[0], x[1]) == v for x in rows) >= 2:
            continue  # один признак — не больше чем у двух позиций
        rows.append((f, rk))
        if len(rows) == 4:
            break
    else:
        raise Retry
    need = list(dict.fromkeys(sign24(f, rk) for f, rk in rows))
    others = [s_ for s_ in SIGN24 if s_ not in need and s_ != 'bluea']
    rng.shuffle(others)
    right = need + others[:5 - len(need)]
    if len(right) != 5:
        raise Retry
    # составной признак не должен «покрываться» простым из того же столбца
    if ('decw' in need and 'dec' in right) or ('decg' in need and ('dec' in right or 'gas' in right)):
        raise Retry
    rng.shuffle(right)
    lt = [f'{label24(f, rng)} и {rng.choice(REAG24[rk])}' for f, rk in rows]
    rt = [SIGN24[s_] for s_ in right]
    q = mq(rng.choice(['реагирующими веществами и признаком протекающей между ними реакции',
                       'реагирующими веществами и признаком реакции, протекающей между ними']),
           'РЕАГИРУЮЩИЕ ВЕЩЕСТВА', 'ПРИЗНАК РЕАКЦИИ')
    ans = [right.index(sign24(f, rk)) for f, rk in rows]
    e = '; '.join(f'{lt[i]} — {rt[ans[i]]}' for i in range(4)) + '.'
    return match_card('ch-ege-24-org-sign', rng, q, lt, rt, ans, e, {'left': [list(x) for x in rows], 'right': right})
