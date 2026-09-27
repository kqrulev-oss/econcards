"""Прототипы ЕГЭ-химии (КИМ 2027), неорганика: задания 5, 6, 7, 8, 9, 17, 19, 20, 24, 29, 30, 31.

Все генераторы строятся по базе веществ и реакций (chemdb.load(): chemdb_inorg.py и др.). Карточка хранит в
gen.p только «сырые» параметры (формулы, условия, порядок вариантов); solve() пересчитывает ответ заново ДРУГИМ путём:
перебором реакций базы (а не через индекс генератора), по правилам классификации, по степеням окисления, по ряду
активности и таблице растворимости.

Номера заданий — по обобщённому плану КИМ ЕГЭ 2027 (спецификация, приложение):
  5 — классификация/номенклатура неорганических веществ (2.1);
  6 — «две пробирки», признаки и сокращённые ионные уравнения (2.2, 2.3, 1.9);
  7 — вещество ↔ реагенты (2.2, 2.3);  8 — исходные вещества ↔ продукты (2.2, 2.3);
  9 — схема превращений X, Y (2.4);  17 — классификация реакций (1.5);  19 — ОВР (1.12);
  20 — электролиз (1.13);  24 — качественные реакции (2.5; неорганическая часть);
  29 — ОВР из перечня (1.12), 30 — реакции ионного обмена из перечня (1.9), 31 — «мысленный эксперимент» (2.2–2.4):
  для заданий с развёрнутым ответом — проверяемые шаги (выбор пары, коэффициенты, ионное уравнение, вещества цепочки).
"""
import math
import re
from collections import Counter
from fractions import Fraction as Fr

import chemdb
import chemdb_inorg as I
from pc_core import Retry, balance, match_opts, opts, parse_formula, pcard, pretty, proto, recipe

DB = chemdb.load()
# вещества — общая база, но поля этого участка (класс, ионы, ст. ок.) берём из chemdb_inorg (первоисточник для неорганики)
SUBS = dict(DB['substances'])
for _s in I.SUBSTANCES:
    SUBS[_s['f']] = dict(SUBS.get(_s['f'], {}), **_s, _mod='chemdb_inorg.py')
# реакции — из chemdb_inorg (в общей базе дубли из других модулей могли «забрать» ключ)
RX = []
for _i, _r in enumerate(I.REACTIONS):
    _kl, _kr = balance(_r['lhs'], _r['rhs'])
    RX.append(dict(_r, k=[_kl, _kr], rid=f'inorg-{_i:04d}'))
RX_BY_ID = {r['rid']: r for r in RX}
LET = 'АБВГДЕ'
SUP = str.maketrans('0123456789+-', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻')


# ================================================================= отображение

MYVIEW = {x['f']: x.get('view') for x in I.SUBSTANCES}


def F(f):
    """Формула для показа: view (скобки комплекса) + нижние индексы."""
    v = MYVIEW[f] if f in MYVIEW else SUBS.get(f, {}).get('view')
    return pretty(v or f)


def FL(f, form=''):
    """Формула с пометкой формы: HNO₃ (конц.)."""
    return F(f) + (f' ({form})' if form else '')


def eq_text(lhs, rhs, kl=None, kr=None, arrow='→'):
    if kl is None:
        kl, kr = balance(lhs, rhs)
    side = lambda ss, ks: ' + '.join((str(k) if k > 1 else '') + F(s) for s, k in zip(ss, ks))
    return f'{side(lhs, kl)} {arrow} {side(rhs, kr)}'


def scheme_text(lhs, rhs):
    return ' + '.join(F(s) for s in lhs) + ' → ' + ' + '.join(F(s) for s in rhs)


RU = {  # названия в тексте (именительный падеж)
    'HCl': 'соляная кислота', 'HBr': 'бромоводородная кислота', 'HI': 'иодоводородная кислота',
    'HF': 'фтороводородная кислота', 'H2S': 'сероводород', 'NH3·H2O': 'гидрат аммиака', 'NH3': 'аммиак',
    'H2O': 'вода', 'H2O2': 'пероксид водорода', 'C': 'углерод', 'P': 'фосфор', 'Na(Al(OH)4)': 'тетрагидроксоалюминат натрия',
    'H3PO4': 'фосфорная кислота', 'CH3COOH': 'уксусная кислота', 'H2SiO3': 'кремниевая кислота',
}


def ru(f):
    return RU.get(f) or SUBS[f]['name']


_GEN_WORD = {'натрий': 'натрия', 'калий': 'калия', 'литий': 'лития', 'магний': 'магния', 'кальций': 'кальция',
             'алюминий': 'алюминия', 'барий': 'бария', 'стронций': 'стронция', 'кремний': 'кремния', 'медь': 'меди',
             'ртуть': 'ртути', 'свинец': 'свинца', 'марганец': 'марганца', 'никель': 'никеля', 'железо': 'железа',
             'серебро': 'серебра', 'золото': 'золота', 'олово': 'олова', 'вода': 'воды', 'сера': 'серы',
             'цинк': 'цинка', 'хром': 'хрома', 'бериллий': 'бериллия', 'рубидий': 'рубидия', 'цезий': 'цезия'}
_INS_WORD = {'натрий': 'натрием', 'калий': 'калием', 'литий': 'литием', 'магний': 'магнием', 'кальций': 'кальцием',
             'алюминий': 'алюминием', 'барий': 'барием', 'стронций': 'стронцием', 'кремний': 'кремнием',
             'медь': 'медью', 'ртуть': 'ртутью', 'свинец': 'свинцом', 'марганец': 'марганцем', 'никель': 'никелем',
             'железо': 'железом', 'серебро': 'серебром', 'золото': 'золотом', 'олово': 'оловом', 'вода': 'водой',
             'сера': 'серой', 'цинк': 'цинком', 'хром': 'хромом', 'бериллий': 'бериллием'}


def _decl_word(w, case):
    table = _GEN_WORD if case == 'g' else _INS_WORD
    if w in table:
        return table[w]
    if w.endswith('ая'):
        return w[:-2] + ('ой' if case == 'g' else 'ой')
    if w.endswith('кислота'):
        return w[:-1] + ('ы' if case == 'g' else 'ой')
    if w.endswith('й'):
        return w[:-1] + ('я' if case == 'g' else 'ем')
    if w[-1] in 'бвгджзклмнпрстфхцчшщ':
        return w + ('а' if case == 'g' else 'ом')
    return w


def decl(name, case):
    """Родительный ('g') / творительный ('i') падеж названия вещества: «сульфид натрия» → «сульфида натрия»."""
    words = name.split(' ')
    if len(words) >= 2 and words[1].startswith('кислот'):
        return _decl_word(words[0], case) + ' ' + _decl_word(words[1], case) + (' ' + ' '.join(words[2:]) if words[2:]
                                                                                   else '')
    words[0] = _decl_word(words[0], case)
    return ' '.join(words)


def gen(f):
    return decl(ru(f), 'g')


def ins(f):
    return decl(ru(f), 'i')


# ================================================================= знание о взаимодействии пар

FORM_OF = lambda r, f: (r.get('form') or {}).get(f)


def _pair_rx(a, b):
    """Реакции, в которых реагенты — ровно a и b (и, возможно, вода)."""
    out = []
    for r in RX:
        L = set(r['lhs'])
        if a in L and b in L and a != b and L - {a, b} <= {'H2O'}:
            out.append(r)
        elif a == b and False:
            pass
    return out


PAIR = {}
for _r in RX:
    _L = [x for x in dict.fromkeys(_r['lhs'])]
    _base = [x for x in _L if x != 'H2O']
    if len(_base) == 2:
        PAIR.setdefault(frozenset(_base), []).append(_r)
    elif len(_base) == 1 and 'H2O' in _L:
        PAIR.setdefault(frozenset([_base[0], 'H2O']), []).append(_r)
    elif len(_L) == 2 and 'H2O' in _L:
        PAIR.setdefault(frozenset(_L), []).append(_r)
SINGLE = {}
for _r in RX:
    if len(_r['lhs']) == 1:
        SINGLE.setdefault(_r['lhs'][0], []).append(_r)

NR = {}
for _a, _fa, _b, _fb, _why in I.NO_REACTION:
    NR.setdefault(frozenset([_a, _b]), []).append((_a, _fa, _b, _fb, _why))


def _form_ok(label, rform, cond):
    if not label:
        return True
    if label == 'конц.':
        return rform == 'конц.'
    if label in ('разб.', 'р-р'):
        return rform in (None, 'разб.', 'р-р') and 'сплавл' not in cond and 'конц' not in cond
    if label == 'тв.':
        return rform in (None, 'тв.')
    return True


def _nr_ok(label, nform):
    if not nform:
        return True
    if label == nform:
        return True
    if label in ('', 'р-р', 'разб.') and nform in ('р-р', 'разб.'):
        return True
    return False


def pos_rx(a, la, b, lb):
    return [r for r in PAIR.get(frozenset([a, b]), [])
            if _form_ok(la, FORM_OF(r, a), r.get('cond', '')) and _form_ok(lb, FORM_OF(r, b), r.get('cond', ''))]


def reacts(a, la='', b=None, lb=''):
    """True — реагирует (есть в базе), False — заведомо нет (NO_REACTION), None — неизвестно или спорно."""
    pos = pos_rx(a, la, b, lb)
    neg = []
    for x, fx, y, fy, why in NR.get(frozenset([a, b]), []):
        lx, ly = (la, lb) if x == a else (lb, la)
        if _nr_ok(lx, fx) and _nr_ok(ly, fy):
            neg.append(why)
    if pos and not neg:
        return True
    if neg and not pos:
        return False
    return None


# ================================================================= классификация веществ (для 5)

STRICT = {
    'основного оксида': lambda s: s['cls'] == 'оксид' and s.get('acid_base') == 'основный' and s['f'] not in ('Cu2O',),
    'кислотного оксида': lambda s: s.get('acid_base') == 'кислотный' and s['f'] not in ('NO2', 'Cl2O', 'P2O3', 'B2O3'),
    'амфотерного оксида': lambda s: s['f'] in ('Al2O3', 'ZnO', 'BeO', 'Cr2O3', 'Fe2O3'),
    'несолеобразующего оксида': lambda s: s['f'] in ('CO', 'NO', 'N2O'),
    'щёлочи': lambda s: s.get('sub') == 'щёлочь' and s['f'] not in ('Ca(OH)2', 'Sr(OH)2'),
    'нерастворимого основания': lambda s: s.get('sub') == 'нерастворимое основание',
    'амфотерного гидроксида': lambda s: s['f'] in ('Al(OH)3', 'Zn(OH)2', 'Be(OH)2', 'Cr(OH)3'),
    'сильной кислоты': lambda s: s['f'] in ('HCl', 'HBr', 'HI', 'HNO3', 'H2SO4', 'HClO4'),
    'слабой кислоты': lambda s: s['f'] in ('HF', 'H2S', 'H2CO3', 'H2SiO3', 'HNO2', 'CH3COOH', 'HClO'),
    'одноосновной кислоты': lambda s: s['f'] in ('HCl', 'HBr', 'HI', 'HNO3', 'HNO2', 'HF', 'HClO4', 'HClO3', 'HClO',
                                                 'CH3COOH', 'HMnO4'),
    'двухосновной кислоты': lambda s: s['f'] in ('H2SO4', 'H2SO3', 'H2S', 'H2CO3', 'H2SiO3', 'H2CrO4'),
    'бескислородной кислоты': lambda s: s['f'] in ('HCl', 'HBr', 'HI', 'HF', 'H2S'),
    'средней соли': lambda s: s.get('sub') == 'средняя соль' and s['cls'] == 'соль' and 'ion' in s,
    'кислой соли': lambda s: s.get('sub') == 'кислая соль',
    'основной соли': lambda s: s.get('sub') == 'основная соль',
    'комплексной соли': lambda s: s.get('sub') == 'комплексная соль' and s['f'] not in ('KFe(Fe(CN)6)',),
    'двойной соли': lambda s: s.get('sub') == 'двойная соль',
    'простого вещества-металла': lambda s: s['cls'] == 'простое вещество' and s.get('sub') == 'металл',
    'простого вещества-неметалла': lambda s: s['cls'] == 'простое вещество' and s.get('sub') == 'неметалл' and
                                             s['f'] not in ('He', 'Ne', 'Ar'),
}
# «широкие» признаки: вещество-дистрактор не должно подпадать под выбранную категорию даже в широком смысле
LOOSE = {
    'основного оксида': lambda s: s['cls'] == 'оксид' and s.get('acid_base') == 'основный',
    'кислотного оксида': lambda s: s['cls'] == 'оксид' and s.get('acid_base') in ('кислотный',) or s['f'] in ('NO2',),
    'амфотерного оксида': lambda s: s.get('acid_base') == 'амфотерный' or s['f'] in ('Fe3O4',),
    'несолеобразующего оксида': lambda s: s.get('acid_base') == 'несолеобразующий' or s['f'] in ('NO2', 'H2O'),
    'щёлочи': lambda s: s.get('sub') == 'щёлочь' or s['f'] == 'NH3·H2O',
    'нерастворимого основания': lambda s: s['cls'] in ('основание', 'амфотерный гидроксид') and s.get('sol') == 'н',
    'амфотерного гидроксида': lambda s: s['cls'] == 'амфотерный гидроксид',
    'сильной кислоты': lambda s: s['cls'] == 'кислота' and s.get('strength') in ('сильная', 'средней силы'),
    'слабой кислоты': lambda s: s['cls'] == 'кислота' and s.get('strength') in ('слабая', 'средней силы'),
    'одноосновной кислоты': lambda s: s['cls'] == 'кислота',
    'двухосновной кислоты': lambda s: s['cls'] == 'кислота',
    'бескислородной кислоты': lambda s: s['cls'] == 'кислота' or s['f'] in ('NH3', 'PH3', 'SiH4', 'CH4'),
    'средней соли': lambda s: s['cls'] == 'соль' or s.get('cls') == 'бинарное' and 'сульфид' in s.get('sub', ''),
    'кислой соли': lambda s: s.get('sub') == 'кислая соль',
    'основной соли': lambda s: s.get('sub') == 'основная соль',
    'комплексной соли': lambda s: s.get('sub') == 'комплексная соль' or s['f'] in ('Na3AlF6',),
    'двойной соли': lambda s: s.get('sub') in ('двойная соль', 'смешанная соль'),
    'простого вещества-металла': lambda s: s['cls'] == 'простое вещество',
    'простого вещества-неметалла': lambda s: s['cls'] == 'простое вещество',
}
# у простых веществ «металл/неметалл» в КИМ называют просто «простого вещества», если второй тип не выбран
CAT_GROUP = {'основного оксида': 'ox', 'кислотного оксида': 'ox', 'амфотерного оксида': 'ox',
             'несолеобразующего оксида': 'ox', 'щёлочи': 'b', 'нерастворимого основания': 'b',
             'амфотерного гидроксида': 'b', 'сильной кислоты': 'a', 'слабой кислоты': 'a', 'одноосновной кислоты': 'a',
             'двухосновной кислоты': 'a', 'бескислородной кислоты': 'a', 'средней соли': 's', 'кислой соли': 's',
             'основной соли': 's', 'комплексной соли': 's', 'двойной соли': 's', 'простого вещества-металла': 'e',
             'простого вещества-неметалла': 'e'}
TRIV5 = {'негашёная известь': 'CaO', 'гашёная известь': 'Ca(OH)2', 'едкий натр': 'NaOH', 'едкое кали': 'KOH',
         'питьевая сода': 'NaHCO3', 'кальцинированная сода': 'Na2CO3', 'поваренная соль': 'NaCl',
         'углекислый газ': 'CO2', 'угарный газ': 'CO', 'веселящий газ': 'N2O', 'сернистый газ': 'SO2', 'кварц': 'SiO2',
         'корунд': 'Al2O3', 'гематит': 'Fe2O3', 'пирит': 'FeS2', 'гипс': 'CaSO4·2H2O', 'медный купорос': 'CuSO4·5H2O',
         'малахит': '(CuOH)2CO3', 'мел': 'CaCO3', 'мрамор': 'CaCO3', 'поташ': 'K2CO3', 'аммиачная селитра': 'NH4NO3',
         'калийная селитра': 'KNO3', 'нашатырь': 'NH4Cl', 'бертолетова соль': 'KClO3', 'жжёная магнезия': 'MgO',
         'плавиковая кислота': 'HF', 'алмаз': 'C', 'графит': 'C', 'озон': 'O3', 'красный фосфор': 'P',
         'хлорная известь': 'CaOCl2', 'флюорит': 'CaF2', 'жёлтая кровяная соль': 'K4(Fe(CN)6)',
         'магнетит': 'Fe3O4', 'глауберова соль': 'Na2SO4·10H2O', 'ляпис': 'AgNO3', 'киноварь': 'HgS',
         'сильвин': 'KCl', 'марганцовка': 'KMnO4'}
POOL5 = [f for f, s in SUBS.items() if s.get('_mod') == 'chemdb_inorg.py' and f not in ('KO2', 'OF2', 'SiO', 'NaNH2')
         and not f.startswith(('Rb', 'Cs')) and 'Hg' not in f and 'Sr' not in f]


def _kim_ox_name(f):
    return ru(f)


# ================================================================= fidelity-заготовки

def FID(n, *, trap, scale, kes, fmt_=None, style=None, level=None, time_min=None, score=None):
    lv = level or {5: 'Б', 6: 'П', 7: 'П', 8: 'П', 9: 'П', 17: 'Б', 19: 'Б', 20: 'Б', 24: 'П', 29: 'В', 30: 'В',
                   31: 'В'}[n]
    tm = time_min or {5: 2.5, 6: 6, 7: 6, 8: 6, 9: 2.5, 17: 2.5, 19: 2.5, 20: 2.5, 24: 6, 29: 12, 30: 11, 31: 12}[n]
    sc = score or {5: '1 балл, полное совпадение', 9: '1 балл, полное совпадение', 17: '1 балл, полное совпадение',
                   19: '1 балл, полное совпадение', 20: '1 балл, полное совпадение',
                   29: 'в КИМ 2 балла за развёрнутый ответ; в тренажёре — проверяемый шаг, 1 балл',
                   30: 'в КИМ 2 балла за развёрнутый ответ; в тренажёре — проверяемый шаг, 1 балл',
                   31: 'в КИМ 4 балла (по 1 за уравнение); в тренажёре — проверяемый шаг, 1 балл'}.get(
        n, '2 балла; 1 балл при одной ошибке')
    return dict(answer_format=fmt_ or 'последовательность цифр по буквам (соответствие), цифры могут повторяться',
                style=style or 'формулировка КИМ 2027 «Установите соответствие между…», без разговорных вставок',
                level=lv, time_min=tm, scale=scale, trap=trap, kes=kes, score=sc)


# ---- страховка от близких пересказов банка: если локальная выгрузка ФИПИ доступна (FIPI_DIR), карточка со сходством
# ≥ 0,28 отбрасывается (Retry) — аналог обязан отличаться веществами и сочетаниями, а не только числами.
_SIM = None


def _sim():
    global _SIM
    if _SIM is None:
        import glob
        import json
        import os
        from pc_core import Similarity
        texts = []
        d = os.environ.get('FIPI_DIR', '')
        for path in sorted(glob.glob(os.path.join(d, '*-chem*.jsonl'))) if d else []:
            for line in open(path, encoding='utf-8'):
                t = json.loads(line).get('text', '')
                if t:
                    texts.append(t)
        _SIM = Similarity(texts) if texts else False
    return _SIM


def card(pid, q, a, e, **kw):
    c = pcard(pid, q, a, e, **kw)
    sim = _sim()
    if sim:
        from pc_core import card_text
        if sim.score(card_text(c))[0] >= 0.28:
            raise Retry
    return c


def shuffled(rng, xs):
    xs = list(xs)
    rng.shuffle(xs)
    return xs


# ================================================================= 5. Классификация и номенклатура

STRICT['основания'] = lambda s: s['cls'] == 'основание' and s['f'] != 'NH3·H2O'
LOOSE['основания'] = lambda s: s['cls'] in ('основание', 'амфотерный гидроксид')
CAT_GROUP['основания'] = 'b'
STRICT['простого вещества'] = lambda s: s['cls'] == 'простое вещество' and s['f'] not in ('He', 'Ne', 'Ar')
LOOSE['простого вещества'] = lambda s: s['cls'] == 'простое вещество'
CAT_GROUP['простого вещества'] = 'e'
STRICT['кислоты'] = lambda s: s['cls'] == 'кислота' and s['f'] not in ('H3PO3', 'HIO3')
LOOSE['кислоты'] = lambda s: s['cls'] == 'кислота' or s.get('sub') == 'кислая соль'
CAT_GROUP['кислоты'] = 'a'
TRIV_OF = {}
for _n, _f in TRIV5.items():
    TRIV_OF.setdefault(_f, []).append(_n)


def _classify5(f):
    """Независимая классификация по формуле (для solve): множество категорий в узком смысле."""
    comp = parse_formula(f.split('·')[0])
    els = set(comp)
    metals = {'Li', 'Na', 'K', 'Rb', 'Cs', 'Be', 'Mg', 'Ca', 'Sr', 'Ba', 'Al', 'Zn', 'Fe', 'Cr', 'Mn', 'Cu', 'Ag', 'Hg',
              'Pb', 'Sn', 'Ni', 'Au', 'Pt'}
    out = set()
    if len(els) == 1 and '·' not in f:
        out.add('простого вещества')
        out.add('простого вещества-металла' if els & metals else 'простого вещества-неметалла')
        return out
    if f in ('Na2O2', 'BaO2', 'H2O2', 'KO2', 'Fe3O4', 'H2O'):
        return out
    if len(els) == 2 and 'O' in els and '·' not in f:
        x = (els - {'O'}).pop()
        ox = Fr(2 * comp['O'], comp[x])
        if f in ('CO', 'NO', 'N2O'):
            out.add('несолеобразующего оксида')
        elif x in metals:
            if x in ('Al', 'Zn', 'Be') or (x in ('Cr', 'Fe') and ox == 3):
                out.add('амфотерного оксида')
            elif ox <= 2 and x not in ('Pb', 'Sn') and f != 'Cu2O':
                out.add('основного оксида')
            elif ox >= 5:
                out.add('кислотного оксида')
        elif f not in ('NO2', 'Cl2O', 'P2O3', 'B2O3'):
            out.add('кислотного оксида')
        return out
    m = re.fullmatch(r'([A-Z][a-z]?)(\(OH\)(\d)|OH)', f)
    if m:
        x = m.group(1)
        if x in ('Al', 'Zn', 'Be') or (x == 'Cr' and m.group(3) == '3'):
            out.add('амфотерного гидроксида')
        elif x == 'Fe' and m.group(3) == '3':
            pass
        else:
            out.add('основания')
            if x in ('Li', 'Na', 'K', 'Rb', 'Cs', 'Ba'):
                out.add('щёлочи')
            elif x not in ('Ca', 'Sr'):
                out.add('нерастворимого основания')
        return out
    if f in I.STRONG_ACIDS | I.WEAK_ACIDS | {'H2CrO4', 'H2Cr2O7', 'HClO3', 'HMnO4'}:
        out.add('кислоты')
        if f in ('HCl', 'HBr', 'HI', 'HNO3', 'H2SO4', 'HClO4'):
            out.add('сильной кислоты')
        if f in ('HF', 'H2S', 'H2CO3', 'H2SiO3', 'HNO2', 'CH3COOH', 'HClO'):
            out.add('слабой кислоты')
        if 'O' not in els:
            out.add('бескислородной кислоты')
        nh = {'HCl': 1, 'HBr': 1, 'HI': 1, 'HNO3': 1, 'HNO2': 1, 'HF': 1, 'HClO4': 1, 'HClO3': 1, 'HClO': 1,
              'CH3COOH': 1, 'HMnO4': 1, 'H2SO4': 2, 'H2SO3': 2, 'H2S': 2, 'H2CO3': 2, 'H2SiO3': 2, 'H2CrO4': 2}.get(f)
        if nh == 1:
            out.add('одноосновной кислоты')
        if nh == 2:
            out.add('двухосновной кислоты')
        return out
    view = SUBS[f].get('view', f)
    if '[' in view:
        out.add('комплексной соли')
        return out
    if f in ('KAl(SO4)2', 'KCr(SO4)2', '(NH4)2Fe(SO4)2'):
        out.add('двойной соли')
        return out
    if re.search(r'OH', f) and not f.startswith('(CH3') and els & metals:
        out.add('основной соли')
        return out
    if re.search(r'(HCO3|HSO4|HSO3|H2PO4|HPO4|HS)(\)|\d|$)', f) and (els & metals or 'N' in els):
        out.add('кислой соли')
        return out
    if SUBS[f]['cls'] == 'соль' and '·' not in f and f not in ('CaOCl2', 'Na3AlF6', 'KSCN', 'NH4SCN', 'Fe(SCN)3'):
        out.add('средней соли')
    return out


def _cell_text(rng, f, allow_triv=True):
    r = rng.random()
    if allow_triv and f in TRIV_OF and r < 0.3:
        return rng.choice(TRIV_OF[f])
    if r < 0.62:
        return F(f)
    return SUBS[f]['name'] if f not in RU else RU[f]


def _solve_5cells(p):
    ans = {}
    for i, cat in enumerate(p['cats']):
        hits = [str(j + 1) for j, f in enumerate(p['cells']) if cat in _classify5(f)]
        if len(hits) != 1:
            return {'err': cat}
        ans[LET[i]] = hits[0]
    return ans


def _pick_cats(rng, k, pool=None):
    names = pool or [c for c in STRICT if c not in ('простого вещества-металла', 'простого вещества-неметалла')]
    for _ in range(50):
        cats = rng.sample(names, k)
        if len({CAT_GROUP[c] for c in cats}) == k:
            return cats
    raise Retry


@proto('ch-ege-05-cells', 'ЕГЭ', 5, 'Девять ячеек: формулы и названия → три класса/группы веществ',
       invariant='определить класс/группу каждого вещества (оксиды по кислотно-основным свойствам, основания, '
                 'кислоты по силе и основности, соли средние/кислые/основные/комплексные, простые вещества) и найти по '
                 'одному представителю трёх заданных групп',
       varies='три группы из 20, набор из девяти веществ (формулы, систематические и тривиальные названия)',
       answer_rule='под буквами А, Б, В — номера ячеек с представителями названных групп',
       mistakes=['амфотерный гидроксид Zn(OH)₂, Al(OH)₃ принимают за основание', 'NO₂ считают несолеобразующим',
                 'кислую соль (NaHCO₃) принимают за кислоту', 'не узнают вещество по тривиальному названию',
                 'оксид металла в высшей степени окисления (CrO₃, Mn₂O₇) считают основным'],
       solve=_solve_5cells, kind='dict', kes=['2.1'],
       fidelity=FID(5, trap='амфотерные гидроксиды/оксиды среди «оснований», пероксиды и несолеобразующие оксиды, '
                            'кислые и основные соли, тривиальные названия (питьевая сода, гашёная известь, кварц, пирит)',
                    scale='девять ячеек, 3 буквы, смесь формул и названий — как в демоверсии 2027 и 44 заданиях банка',
                    kes=['2.1'], fmt_='три цифры — номера ячеек под буквами А, Б, В',
                    style='«Среди предложенных формул/названий… выберите…» (перефразировано), 9 пронумерованных ячеек'))
def g_5cells(rng):
    pid = 'ch-ege-05-cells'
    cats = _pick_cats(rng, 3)
    chosen, cells = [], []
    for c in cats:
        cand = [f for f in POOL5 if STRICT[c](SUBS[f]) and c in _classify5(f)
                and not any(LOOSE[c2](SUBS[f]) for c2 in cats if c2 != c)]
        if not cand:
            raise Retry
        chosen.append(rng.choice(cand))
    groups = {CAT_GROUP[c] for c in cats}
    near = [f for f in POOL5 if not any(LOOSE[c](SUBS[f]) for c in cats) and not any(c in _classify5(f) for c in cats)
            and f not in chosen]
    tempting = [f for f in near if any(CAT_GROUP.get(c2) in groups for c2 in _classify5(f))]
    others = [f for f in near if f not in tempting]
    dis = rng.sample(tempting, min(len(tempting), 4))
    rest = [f for f in others if f not in dis]
    dis += rng.sample(rest, 6 - len(dis))
    items = chosen + dis
    if len(set(items)) != 9:
        raise Retry
    rng.shuffle(items)
    texts = [_cell_text(rng, f) for f in items]
    if len(set(texts)) != 9:
        raise Retry
    ans = {LET[i]: str(items.index(chosen[i]) + 1) for i in range(3)}
    head = ('Среди предложенных формул/названий веществ, расположенных в пронумерованных ячейках, выберите '
            'формулы/названия:')
    q = head + ' ' + '; '.join(f'{LET[i]}) {c}' for i, c in enumerate(cats)) + '.' + \
        ' Запишите в таблицу номера ячеек, в которых расположены выбранные вещества, под соответствующими буквами.'
    e = '; '.join(f'{LET[i]}) {cats[i]} — ячейка {ans[LET[i]]}: {F(chosen[i])} ({SUBS[chosen[i]]["name"]})'
                  for i in range(3)) + '.'
    return card(pid, q, ans, e, k='match', o=match_opts(cats, texts, rids='123456789'), p={'cats': cats, 'cells': items})


def _solve_5match(p):
    ans = {}
    for i, f in enumerate(p['items']):
        cl = _classify5(f)
        hits = [str(j + 1) for j, g in enumerate(p['groups']) if GROUP_NAMES[g] in cl or g in cl]
        if len(hits) != 1:
            return {'err': f}
        ans[LET[i]] = hits[0]
    return ans


GROUP_NAMES = {'основные оксиды': 'основного оксида', 'кислотные оксиды': 'кислотного оксида',
               'амфотерные оксиды': 'амфотерного оксида', 'несолеобразующие оксиды': 'несолеобразующего оксида',
               'щёлочи': 'щёлочи', 'нерастворимые основания': 'нерастворимого основания',
               'амфотерные гидроксиды': 'амфотерного гидроксида', 'кислоты': 'кислоты', 'средние соли': 'средней соли',
               'кислые соли': 'кислой соли', 'основные соли': 'основной соли', 'комплексные соли': 'комплексной соли',
               'сильные кислоты': 'сильной кислоты', 'слабые кислоты': 'слабой кислоты',
               'бескислородные кислоты': 'бескислородной кислоты', 'двухосновные кислоты': 'двухосновной кислоты',
               'одноосновные кислоты': 'одноосновной кислоты'}


@proto('ch-ege-05-match', 'ЕГЭ', 5, 'Формула/название вещества → класс (группа) веществ',
       invariant='по формуле или названию отнести вещество к классу/группе неорганических веществ',
       varies='три вещества (формула или название) и четыре группы: оксиды по свойствам, основания, кислоты, соли',
       answer_rule='каждому веществу — номер группы, к которой оно принадлежит',
       mistakes=['ZnO, Al₂O₃ относят к основным оксидам', 'кислую соль относят к кислотам', 'Mn₂O₇, CrO₃ считают основными'],
       solve=_solve_5match, kind='dict', kes=['2.1'],
       fidelity=FID(5, trap='та же, что у 9-ячеечной формы: амфотерность, кислые/основные соли, несолеобразующие оксиды',
                    scale='3 вещества × 4 группы — как в 75 заданиях банка старой формы (КЭС 2.1, соответствие)',
                    kes=['2.1'], fmt_='три цифры под буквами А, Б, В',
                    style='«Установите соответствие между формулой (названием) вещества и классом/группой…»'))
def g_5match(rng):
    pid = 'ch-ege-05-match'
    gnames = list(GROUP_NAMES)
    for _ in range(40):
        groups = rng.sample(gnames, 4)
        cats = [GROUP_NAMES[g] for g in groups]
        if len({CAT_GROUP[c] for c in cats}) >= 2:
            break
    items = []
    for _ in range(3):
        g = rng.choice(groups)
        c = GROUP_NAMES[g]
        cand = [f for f in POOL5 if STRICT[c](SUBS[f]) and _classify5(f) & set(cats) == {c} and f not in items
                and not any(LOOSE[c2](SUBS[f]) for c2 in cats if c2 != c)]
        if not cand:
            raise Retry
        items.append(rng.choice(cand))
    ans = {LET[i]: str(groups.index(next(g for g in groups if GROUP_NAMES[g] in _classify5(f))) + 1)
           for i, f in enumerate(items)}
    by_name = rng.random() < 0.4
    left = [ru(f) if by_name else F(f) for f in items]
    q = (f'Установите соответствие между {"названием" if by_name else "формулой"} вещества и классом/группой, '
         f'к которому(-ой) это вещество принадлежит: к каждой позиции, обозначенной буквой, подберите '
         f'соответствующую позицию, обозначенную цифрой. Запишите в таблицу выбранные цифры под соответствующими '
         f'буквами.')
    e = '; '.join(f'{F(f)} ({SUBS[f]["name"]}) — {groups[int(ans[LET[i]]) - 1]}' for i, f in enumerate(items)) + '.'
    return card(pid, q, ans, e, k='match', o=match_opts(left, groups), p={'items': items, 'groups': groups})


# ================================================================= 7. Вещество ↔ реагенты

ACID_LABELS = {'HNO3': ['конц.', 'разб.'], 'H2SO4': ['конц.', 'разб.']}
PARTNERS = {}
for _k in list(PAIR) + list(NR):
    _k = list(_k)
    if len(_k) == 2:
        PARTNERS.setdefault(_k[0], set()).add(_k[1])
        PARTNERS.setdefault(_k[1], set()).add(_k[0])
_KNOW = {}


def csplit(c):
    f, _, lab = c.partition('|')
    return f, lab


def rc(c, x):
    f, lab = csplit(c)
    return reacts(f, lab, x[0], x[1])


def CF(c):
    return FL(*csplit(c))


def know(c):
    """{(partner, label): True/False} — только определённые ответы. c — 'формула' или 'формула|форма'."""
    if c in _KNOW:
        return _KNOW[c]
    out = {}
    f0, lab0 = csplit(c)
    for p in PARTNERS.get(f0, ()):
        if p not in SUBS:
            continue
        for lab in ACID_LABELS.get(p, ['']):
            v = reacts(f0, lab0, p, lab)
            if v is not None:
                out[(p, lab)] = v
    _KNOW[c] = out
    return out


def _center_ok(c):
    k = know(c)
    return sum(v for v in k.values()) >= 5 and sum(not v for v in k.values()) >= 5


CENTERS7 = [c for c in SUBS if SUBS[c].get('_mod') == 'chemdb_inorg.py' and c not in ('H2O', 'HNO3', 'H2SO4')
            and _center_ok(c)] + [c for c in ('HNO3|конц.', 'HNO3|разб.', 'H2SO4|конц.', 'H2SO4|разб.')
                                  if _center_ok(c)]


def _rlabel(p, lab):
    return FL(p, lab)


def _set_ok(c, S):
    """True — вещество реагирует со всеми реагентами набора, False — хотя бы с одним заведомо нет, None — неясно."""
    vals = [rc(c, (p, lab)) for p, lab in S]
    if all(v is True for v in vals):
        return True
    if any(v is False for v in vals):
        return False
    return None


def _solve_7(p):
    ans = {}
    for i, c0 in enumerate(p['centers']):
        c, clab = csplit(c0)
        hits = []
        for j, S in enumerate(p['sets']):
            vals = []
            for pf, lab in S:
                pos = [r for r in RX if c in r['lhs'] and pf in r['lhs'] and set(r['lhs']) - {c, pf} <= {'H2O'}
                       and _form_ok(lab, FORM_OF(r, pf), r.get('cond', ''))
                       and _form_ok(clab, FORM_OF(r, c), r.get('cond', ''))]
                vals.append(bool(pos))
            if all(vals):
                hits.append(str(j + 1))
        if len(hits) != 1:
            return {'err': c}
        ans[LET[i]] = hits[0]
    return ans


def _grow_centers(rng, k=4, tries=12):
    """Подбор центров с большим общим «известным» набором реагентов (жадно, со случайностью)."""
    c1 = rng.choice(CENTERS7)
    centers = [c1]
    known = {x for x in know(c1) if x[0] != c1}
    while len(centers) < k:
        best, best_n = None, -1
        for c in rng.sample(CENTERS7, min(tries, len(CENTERS7))):
            if csplit(c)[0] in {csplit(x)[0] for x in centers} or \
                    any(SUBS[csplit(c)[0]]['cls'] == SUBS[csplit(x)[0]]['cls'] for x in centers) and rng.random() < 0.7:
                continue
            kc = know(c)
            n = sum(1 for x in known if x in kc and x[0] != csplit(c)[0])
            n += rng.random()
            if n > best_n:
                best, best_n = c, n
        if best is None:
            raise Retry
        centers.append(best)
        known = {x for x in known if x in know(best) and x[0] not in {csplit(y)[0] for y in centers}}
    return centers


@proto('ch-ege-07-reagents', 'ЕГЭ', 7, 'Вещество ↔ набор из трёх реагентов, с каждым из которых оно взаимодействует',
       invariant='для каждого вещества проверить взаимодействие с каждым реагентом набора по свойствам классов '
                 '(ряд активности, амфотерность, ОВР, условия обмена)',
       varies='четыре вещества (простые, оксиды, основания, кислоты, соли), пять наборов по три реагента',
       answer_rule='подходит набор, с каждым реагентом которого вещество реагирует; остальные наборы содержат хотя бы '
                   'один реагент, с которым реакции нет',
       mistakes=['медь с разбавленными кислотами-неокислителями', 'основный оксид со щёлочью',
                 'амфотерность Al₂O₃, ZnO, Zn(OH)₂ не учитывают', 'соль со щёлочью без образования осадка/газа',
                 'металл вытесняет более активный металл из соли'],
       solve=_solve_7, kind='dict', kes=['2.2', '2.3'],
       fidelity=FID(7, trap='в «ложном» наборе ровно один-два реагента не реагируют: Cu + HCl, CuO + NaOH, '
                            'NaCl + KNO₃, SiO₂ + HCl, Fe + ZnCl₂; конц. и разб. HNO₃/H₂SO₄ различаются',
                    scale='4 вещества × 5 наборов по 3 реагента — как в демоверсии 2027 (P, H₂, Al₂(SO₄)₃, HNO₃) и 93 '
                          'заданиях банка',
                    kes=['2.2', '2.3'], fmt_='четыре цифры под буквами А–Г'))
def g_7(rng):
    pid = 'ch-ege-07-reagents'
    centers = _grow_centers(rng)
    table = {}
    for x in {x for c in centers for x in know(c)}:
        if x[0] in {csplit(y)[0] for y in centers}:
            continue
        vals = [rc(c, x) for c in centers]
        if None not in vals:
            table[x] = vals
    R = list(table)
    if len(R) < 10:
        raise Retry
    sets = []
    for i, c in enumerate(centers):
        pos = [x for x in R if table[x][i]]
        for _ in range(60):
            if len(pos) < 3:
                raise Retry
            S = rng.sample(pos, 3)
            if len({x[0] for x in S}) < 3:
                continue
            if all(any(not table[x][j] for x in S) for j in range(4) if j != i):
                sets.append(S)
                break
        else:
            raise Retry
    for _ in range(80):
        S = rng.sample(R, 3)
        if len({x[0] for x in S}) == 3 and all(any(not table[x][j] for x in S) for j in range(4)):
            sets.append(S)
            break
    else:
        raise Retry
    if len({frozenset(S) for S in sets}) < 5:
        raise Retry
    order = shuffled(rng, range(5))
    sets = [sets[i] for i in order]
    ans = {}
    for i, c in enumerate(centers):
        hits = []
        for j, S in enumerate(sets):
            v = _set_ok(c, S)
            if v is None:
                raise Retry
            if v:
                hits.append(str(j + 1))
        if len(hits) != 1:
            raise Retry
        ans[LET[i]] = hits[0]
    left = [CF(c) + (' (р-р)' if '|' not in c and SUBS[c].get('sol') == 'р' and
                     SUBS[c]['cls'] in ('соль', 'основание') and rng.random() < 0.3 else '') for c in centers]
    right = [', '.join(_rlabel(p, lab) for p, lab in S) for S in sets]
    q = (rng.choice(['Установите соответствие между веществом и реагентами, с каждым из которых это вещество может '
                     'взаимодействовать', 'Установите соответствие между формулой вещества и реагентами, с каждым '
                     'из которых это вещество может взаимодействовать']) +
         ': к каждой позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой. '
         'Запишите в таблицу выбранные цифры под соответствующими буквами.')
    ex = []
    for i, c in enumerate(centers):
        S = sets[int(ans[LET[i]]) - 1]
        ex.append(f'{CF(c)} реагирует с {", ".join(_rlabel(p, lab) for p, lab in S)}')
    e = '; '.join(ex) + '. В остальных наборах есть реагент, с которым вещество не взаимодействует.'
    return card(pid, q, ans, e, k='match', o=match_opts(left, right),
                 p={'centers': centers, 'sets': [[list(x) for x in S] for S in sets]})


def _solve_7two(p):
    c, clab = csplit(p['center'])
    out = []
    for i, (pf, lab) in enumerate(p['opts']):
        pos = [r for r in RX if c in r['lhs'] and pf in r['lhs'] and set(r['lhs']) - {c, pf} <= {'H2O'}
               and _form_ok(lab, FORM_OF(r, pf), r.get('cond', '')) and _form_ok(clab, FORM_OF(r, c), r.get('cond', ''))]
        if pos:
            out.append(str(i + 1))
    return out


@proto('ch-ege-07-choose-two', 'ЕГЭ', 7, 'Из пяти веществ выбрать два, с каждым из которых реагирует данное вещество',
       invariant='проверить взаимодействие вещества с каждым из пяти реагентов по свойствам классов',
       varies='вещество (металл, неметалл, оксид, основание, кислота, соль), пять реагентов',
       answer_rule='два номера реагентов, с которыми реакция идёт',
       mistakes=['не учитывают ряд активности', 'путают амфотерные и основные оксиды', 'пассивацию не учитывают'],
       solve=_solve_7two, kind='dict', kes=['2.2', '2.3'],
       fidelity=FID(7, trap='тот же навык, что в задании 7; ловушки — Cu/HCl, Fe/ZnCl₂, CuO/NaOH, SiO₂/HCl',
                    scale='вещество + 5 реагентов — как 51 задание банка формы «выбор ответов» (КЭС 2.2, 2.3)',
                    kes=['2.2', '2.3'], fmt_='две цифры (порядок не важен)',
                    style='«Из предложенного перечня выберите два вещества, с каждым из которых взаимодействует…»',
                    level='Б', time_min=3, score='1 балл, полное совпадение'))
def g_7two(rng):
    pid = 'ch-ege-07-choose-two'
    c = rng.choice(CENTERS7)
    k = know(c)
    pos = [x for x, v in k.items() if v]
    neg = [x for x, v in k.items() if not v]
    if len(pos) < 2 or len(neg) < 3:
        raise Retry
    right = rng.sample(pos, 2)
    wrong = []
    for x in shuffled(rng, neg):
        if x[0] not in {y[0] for y in right + wrong}:
            wrong.append(x)
        if len(wrong) == 3:
            break
    if len(wrong) < 3:
        raise Retry
    items = shuffled(rng, right + wrong)
    by_name = rng.random() < 0.9
    rr = rng.random() < 0.6
    lab_of = lambda x: x[1] or ('р-р' if rr and SUBS[x[0]].get('sol') == 'р' and
                                SUBS[x[0]]['cls'] in ('соль', 'основание') and reacts(csplit(c)[0], csplit(c)[1], x[0], 'р-р')
                                == reacts(csplit(c)[0], csplit(c)[1], x[0], x[1]) else '')
    txt = lambda x: (ru(x[0]) + (f' ({lab_of(x)})' if lab_of(x) else '')) if by_name else FL(x[0], lab_of(x))
    ans = [str(i + 1) for i, x in enumerate(items) if x in right]
    f0, lab0 = csplit(c)
    cname = ru(f0) + (f' ({lab0})' if lab0 else '')
    q = rng.choice([f'Из предложенного перечня выберите два вещества, с каждым из которых взаимодействует {cname}.',
                    f'Из предложенного перечня веществ выберите два вещества, с которыми реагирует {cname}.',
                    f'Из предложенного перечня выберите два вещества, которые вступают в реакцию с {ins(f0)}'
                    f'{" (" + lab0 + ")" if lab0 else ""}.']) + \
        ' Запишите номера выбранных ответов.'
    e = f'{CF(c)} реагирует с ' + ' и '.join(ins(x[0]) + (f' ({x[1]})' if x[1] else '') for x in right) + \
        '; с остальными веществами перечня реакция не идёт.'
    return card(pid, q, ans, e, k='many', o=opts([txt(x) for x in items]),
                 p={'center': c, 'opts': [list(x) for x in items]})


# ================================================================= 8. Исходные вещества ↔ продукты

_ALK_SET = {'NaOH', 'KOH', 'LiOH', 'Ba(OH)2', 'Ca(OH)2'}
_ACID_SET = {'HCl', 'HBr', 'HI', 'HNO3', 'H2SO4', 'H3PO4', 'CH3COOH', 'HF', 'H2S'}


def _cond_marks(r):
    """Условия реакции → (пометки у веществ {f: 'изб.'}, общие условия [..]) или None, если условие не передаётся."""
    lhs = [x for x in r['lhs'] if x != 'H2O']
    marks, extra = {}, []
    cond = r.get('cond', '')
    for tok in [t.strip() for t in re.split(r',\s*', cond) if t.strip()]:
        t0 = tok.split(' (')[0]
        if tok in ('конц.', 'разб.', 'оч. разб.', 'р-р'):
            continue
        if t0 in ('t', 't°') or tok.startswith('t (') or tok in ('t (кипячение)', 't (прокаливание)', 'нагревание'):
            extra.append('t°')
        elif tok == 'сплавление':
            extra.append('при сплавлении')
        elif tok == 'хол.':
            extra.append('на холоду')
        elif tok.startswith('кат.'):
            extra.append(pretty(tok))
        elif tok.startswith(('избыток ', 'недостаток ')):
            what = tok.split(' ', 1)[1]
            tgt = None
            if what == 'щёлочи':
                tgt = next((x for x in lhs if x in _ALK_SET), None)
            elif what == 'кислоты':
                tgt = next((x for x in lhs if x in _ACID_SET), None)
            elif what in lhs:
                tgt = what
            elif what == 'NH3':
                tgt = next((x for x in lhs if x.startswith('NH3')), None)
            elif what in ('сульфида',):
                tgt = next((x for x in lhs if x.endswith('S') or x.endswith('S2')), None)
            if tgt is None:
                return None
            if tok.startswith('недостаток'):
                others = [x for x in lhs if x != tgt]
                if len(others) != 1:
                    return None
                tgt = others[0]
            marks[tgt] = 'изб.'
        elif tok in ('избыток', 'электрический ток', 'свет (hν)', 'свет'):
            return None
        else:
            return None
    return marks, extra


def disp_lhs(r):
    """Как в КИМ: «Cu и HNO₃ (конц.)», «Cl₂ и KOH (t°)», «NaHCO₃ →t°»; None — если условие не передать."""
    cm = _cond_marks(r)
    if cm is None:
        return None
    marks, extra = cm
    lhs = [x for x in dict.fromkeys(r['lhs'])]
    base = [x for x in lhs if x != 'H2O']
    if len(base) >= 3:
        return None
    show = base if (len(base) == 2 or 'H2O' not in lhs) else base + ['H2O']
    parts = []
    for x in show:
        lab = []
        fm = FORM_OF(r, x)
        if fm in ('конц.', 'разб.', 'оч. разб.'):
            lab.append(fm)
        elif fm == 'р-р' and x in _ALK_SET:
            lab.append('р-р')
        if marks.get(x):
            lab.append(marks[x])
        parts.append(F(x) + (f' ({", ".join(lab)})' if lab else ''))
    if len(show) == 1:
        if not extra:
            return None
        return parts[0] + ' →' + ('t°' if extra == ['t°'] else ' (' + ', '.join(extra) + ')')
    ex = ['при нагревании' if x == 't°' else x for x in extra]
    if ex == ['при сплавлении'] or ex == ['при нагревании'] or ex == ['на холоду']:
        return ' и '.join(parts) + f' ({ex[0]})'
    return ' и '.join(parts) + (f' ({", ".join(ex)})' if ex else '')


def disp_prod(fs):
    fs = list(fs)
    txt = [F(x) for x in fs]
    return txt[0] if len(txt) == 1 else ', '.join(txt[:-1]) + ' и ' + txt[-1]


DISP8 = {}
for _r in RX:
    if 'электролиз' in _r['type'] or 'качественная' in _r.get('tags', []):
        continue
    _d = disp_lhs(_r)
    if _d:
        DISP8.setdefault(_d, []).append(_r)
USE8 = {d: rs[0] for d, rs in DISP8.items() if len({tuple(sorted(r['rhs'])) for r in rs}) == 1}

_SWAPS = [('NO2', 'NO'), ('NO', 'N2O'), ('N2O', 'N2'), ('SO2', 'H2S'), ('H2S', 'S'), ('SO2', 'S'), ('FeCl2', 'FeCl3'),
          ('FeSO4', 'Fe2(SO4)3'), ('Fe(NO3)2', 'Fe(NO3)3'), ('FeBr2', 'FeBr3'), ('NaAlO2', 'Na(Al(OH)4)'),
          ('KAlO2', 'K(Al(OH)4)'), ('Na2ZnO2', 'Na2(Zn(OH)4)'), ('K2ZnO2', 'K2(Zn(OH)4)'), ('KClO', 'KClO3'),
          ('NaClO', 'NaClO3'), ('CrCl3', 'CrCl2'), ('MnSO4', 'MnO2'), ('MnO2', 'K2MnO4'), ('NaHCO3', 'Na2CO3'),
          ('KHCO3', 'K2CO3'), ('NaHSO3', 'Na2SO3'), ('NaHSO4', 'Na2SO4'), ('FeO', 'Fe2O3'), ('Cu2O', 'CuO'),
          ('NaNO2', 'NaNO3'), ('KNO2', 'KNO3'), ('Cu(NO3)2', 'CuO'), ('Na2O', 'Na2O2'),
          ('Cr2(SO4)3', 'CrSO4'), ('K2CrO4', 'K2Cr2O7'), ('Na2CrO4', 'Na2Cr2O7'), ('NaI', 'NaIO3'), ('KI', 'KIO3'),
          ('NH4NO3', 'NO'), ('Fe(OH)2', 'Fe(OH)3'), ('CuCl', 'CuCl2'), ('NaH2PO4', 'Na2HPO4'), ('Na2HPO4', 'Na3PO4'),
          ('KH2PO4', 'K2HPO4'), ('K2HPO4', 'K3PO4'), ('Ca(HCO3)2', 'CaCO3'), ('HNO3', 'HNO2'), ('H2SO4', 'H2SO3'),
          ('CO', 'CO2'), ('P2O3', 'P2O5'), ('PCl3', 'PCl5'), ('NH3', 'N2'), ('Mn2O3', 'MnO2'), ('Ag', 'Ag2O'),
          ('Hg', 'HgO'), ('Fe3O4', 'Fe2O3'), ('Ca(NO2)2', 'CaO'), ('KNO2', 'K2O'), ('NaNO2', 'Na2O'),
          ('Ba(NO2)2', 'BaO'), ('Mg(NO2)2', 'MgO'), ('Li2O', 'LiNO2'), ('N2O', 'NH3'), ('K2S', 'K2SO3'),
          ('Na2S', 'Na2SO3'), ('BaSO3', 'BaSO4'), ('CaSO3', 'CaSO4'), ('Cl2', 'HCl'), ('Br2', 'HBr'), ('I2', 'HI'),
          ('KCl', 'KClO4'), ('CrCl3', 'K2CrO4')]
SWAP = {}
for _a, _b in _SWAPS:
    SWAP.setdefault(_a, []).append(_b)
    SWAP.setdefault(_b, []).append(_a)


def _mutations(prod, rng):
    out = []
    for i, x in enumerate(prod):
        for y in SWAP.get(x, []):
            if y in SUBS and y not in prod:
                out.append(prod[:i] + [y] + prod[i + 1:])
    if 'H2O' in prod and len(prod) > 2:
        out.append([x for x in prod if x != 'H2O'])
    rng.shuffle(out)
    return out


def _solve_8(p):
    ans = {}
    for i, (lhs, cond, form) in enumerate(p['items']):
        hits = []
        for r in RX:
            if sorted(r['lhs']) == sorted(lhs) and r.get('cond', '') == cond and (r.get('form') or {}) == form:
                for j, pr in enumerate(p['prods']):
                    if sorted(pr) == sorted(r['rhs']):
                        hits.append(str(j + 1))
        hits = sorted(set(hits))
        if len(hits) != 1:
            return {'err': i}
        ans[LET[i]] = hits[0]
    return ans


def _theme8(r, theme):
    tags = set(r.get('tags', [])) | set(r['type'])
    if theme == 'oxacid':
        return bool(tags & {'кислота-окислитель', 'металл+кислота-окислитель', 'неметалл+кислота-окислитель',
                            'металл+кислота', 'конц. кислота+соль'}) or \
            any(FORM_OF(r, x) == 'конц.' for x in r['lhs'])
    if theme == 'amph':
        return any('амфотер' in t or t in ('комплекс+кислота', 'комплекс+кислотный оксид', 'алюминат+кислота',
                                           'цинкат+кислота', 'разложение комплекса', 'щёлочь+соль') for t in tags) \
            and any(e in ''.join(r['lhs']) for e in ('Al', 'Zn', 'Cr', 'Be'))
    if theme == 'decomp':
        return len(r['lhs']) == 1
    return True


_ELEMENTS8 = ['Na', 'K', 'Ca', 'Ba', 'Mg', 'Al', 'Zn', 'Fe', 'Cu', 'Cr', 'Mn', 'Ag', 'N', 'P', 'S', 'Cl', 'Br', 'I', 'C',
              'Si']


def _has_el(f, el):
    try:
        return el in parse_formula(f)
    except ValueError:
        return False


def gen8(rng, pid, theme):
    pool = [d for d, r in USE8.items() if _theme8(r, theme)]
    if theme == 'elem':
        el = rng.choice(_ELEMENTS8)
        pool = [d for d in pool if any(_has_el(x, el) for x in USE8[d]['lhs'] if x != 'H2O')]
    if len(pool) < 6:
        raise Retry
    # 4 реакции; с вероятностью берём «пары» с одинаковыми реагентами и разными условиями
    items = []
    by_lhs = {}
    for d in pool:
        by_lhs.setdefault(frozenset(USE8[d]['lhs']) - {'H2O'}, []).append(d)
    twins = [v for v in by_lhs.values() if len(v) >= 2]
    if twins and rng.random() < 0.6:
        items += rng.sample(rng.choice(twins), 2)
    for d in shuffled(rng, pool):
        if len(items) == 4:
            break
        if d not in items and all(sorted(USE8[d]['rhs']) != sorted(USE8[x]['rhs']) for x in items):
            items.append(d)
    if len(items) < 4:
        raise Retry
    rng.shuffle(items)
    prods = [list(USE8[d]['rhs']) for d in items]
    if len({tuple(sorted(x)) for x in prods}) < 4:
        raise Retry
    # два дистрактора
    pool_mut = []
    for pr in prods:
        pool_mut += _mutations(pr, rng)
    for d in by_lhs.get(frozenset(USE8[items[0]]['lhs']) - {'H2O'}, []):
        if d not in items:
            pool_mut.append(list(USE8[d]['rhs']))
    dis = []
    true_sets = {tuple(sorted(x)) for x in prods}
    for m in shuffled(rng, pool_mut):
        key = tuple(sorted(m))
        if key in true_sets or key in {tuple(sorted(x)) for x in dis}:
            continue
        dis.append(m)
        if len(dis) == 2:
            break
    if len(dis) < 2:
        raise Retry
    right = shuffled(rng, prods + dis)
    ans = {LET[i]: str(next(j for j, x in enumerate(right) if sorted(x) == sorted(prods[i])) + 1) for i in range(4)}
    left = items
    q = rng.choice(['Установите соответствие между исходными веществами, вступающими в реакцию, и продуктами этой '
                    'реакции', 'Установите соответствие между исходными веществами и продуктом(-ами), который(-ые) '
                    'образуется(-ются) при взаимодействии этих веществ', 'Установите соответствие между реагирующими '
                    'веществами и продуктами, которые образуются при взаимодействии этих веществ'])
    if theme == 'decomp':
        q = 'Установите соответствие между исходным веществом, вступающим в реакцию, и продуктами, которые ' \
            'образуются при нагревании этого вещества'
    q += (': к каждой позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой. '
          'Запишите в таблицу выбранные цифры под соответствующими буквами.')
    e = '; '.join(f'{LET[i]}) {eq_text(USE8[d]["lhs"], USE8[d]["rhs"])}' for i, d in enumerate(items)) + '.'
    eqs = []
    for d in items:
        r = USE8[d]
        kl, kr = r['k']
        eqs.append((r['lhs'], r['rhs'], kl, kr))
    return card(pid, q, ans, e, k='match', o=match_opts(left, [disp_prod(x) for x in right], rids='123456'),
                p={'items': [[USE8[d]['lhs'], USE8[d].get('cond', ''), USE8[d].get('form') or {}] for d in items],
                   'prods': right}, eqs=eqs)


_TRAP8 = 'условия (конц./разб., t°, избыток) меняют продукты; дистракторы — «соседние» продукты: NO₂/NO, SO₂/H₂S, ' \
         'Fe²⁺/Fe³⁺, Na[Al(OH)₄]/NaAlO₂, KClO/KClO₃, кислая/средняя соль'
_SCALE8 = '4 пары реагентов × 6 наборов продуктов (два лишних) — как в демоверсии 2027 (Cl₂ и KOH, K₂O и HCl, ' \
          'HCl и MnO₂, Cl₂O и KOH) и ~69 заданиях банка этой формы'


@proto('ch-ege-08-oxacids', 'ЕГЭ', 8, 'Реагенты → продукты: кислоты-окислители (HNO₃, H₂SO₄ конц.) и кислоты-неокислители',
       invariant='определить продукты реакции металла/неметалла/соединения с кислотой с учётом её концентрации',
       varies='металлы разной активности, неметаллы, оксиды и соли-восстановители; конц./разб. HNO₃, H₂SO₄',
       answer_rule='каждой паре реагентов — набор продуктов; учитываются концентрация, t°, пассивация',
       mistakes=['медь с разб. HNO₃ даёт NO₂', 'металл с HNO₃ даёт H₂', 'железо окисляется до +2 конц. кислотой',
                 'активный металл с конц. H₂SO₄ даёт SO₂ вместо H₂S/S'],
       solve=_solve_8, kind='dict', kes=['2.2', '2.3'],
       fidelity=FID(8, trap=_TRAP8, scale=_SCALE8, kes=['2.2', '2.3'], fmt_='четыре цифры под буквами А–Г'))
def g_8oxacid(rng):
    return gen8(rng, 'ch-ege-08-oxacids', 'oxacid')


@proto('ch-ege-08-amphoteric', 'ЕГЭ', 8, 'Реагенты → продукты: соединения Al, Zn, Cr(III), Be (раствор/сплавление, избыток)',
       invariant='амфотерные оксиды/гидроксиды/металлы со щелочами (в растворе — гидроксокомплекс, при сплавлении — '
                 'метасоль), разрушение комплексов кислотами и CO₂ в зависимости от избытка',
       varies='элемент (Al, Zn, Cr, Be), вид реагента, условия (р-р/сплавление, избыток/недостаток)',
       answer_rule='каждой паре реагентов — набор продуктов с учётом условий',
       mistakes=['в растворе пишут NaAlO₂ вместо Na[Al(OH)₄]', 'при сплавлении пишут комплекс',
                 'не учитывают избыток щёлочи/кислоты'],
       solve=_solve_8, kind='dict', kes=['2.2', '2.3'],
       fidelity=FID(8, trap=_TRAP8, scale=_SCALE8, kes=['2.2', '2.3'], fmt_='четыре цифры под буквами А–Г'))
def g_8amph(rng):
    return gen8(rng, 'ch-ege-08-amphoteric', 'amph')


@proto('ch-ege-08-element', 'ЕГЭ', 8, 'Реагенты → продукты: соединения одного элемента (разные классы и условия)',
       invariant='по классам реагентов и условиям определить продукты: обмен, ОВР, диспропорционирование, '
                 'кислые/средние соли',
       varies='элемент-«тема» (Na, Fe, Cu, S, N, P, Cl и др.), четыре реакции его соединений',
       answer_rule='каждой паре реагентов — набор продуктов',
       mistakes=['хлор с горячей щёлочью даёт гипохлорит', 'кислые соли при избытке щёлочи',
                 'Fe(III) с иодидами без ОВР'],
       solve=_solve_8, kind='dict', kes=['2.2', '2.3'],
       fidelity=FID(8, trap=_TRAP8, scale=_SCALE8, kes=['2.2', '2.3'], fmt_='четыре цифры под буквами А–Г'))
def g_8elem(rng):
    return gen8(rng, 'ch-ege-08-element', 'elem')


@proto('ch-ege-08-decomposition', 'ЕГЭ', 8, 'Вещество → продукты его разложения при нагревании',
       invariant='правила термического разложения нитратов (по ряду активности), карбонатов, гидрокарбонатов, '
                 'солей аммония, гидроксидов, перманганата, хлората',
       varies='соли и гидроксиды разных металлов, соли аммония',
       answer_rule='каждому веществу — набор продуктов разложения',
       mistakes=['нитрат активного металла разлагают до оксида', 'Fe(NO₃)₂ разлагают до FeO',
                 'NH₄NO₃ разлагают до NH₃ и HNO₃', 'NaHCO₃ разлагают до Na₂O'],
       solve=_solve_8, kind='dict', kes=['2.2', '2.3'],
       fidelity=FID(8, trap='нитраты: до Mg — нитрит + O₂, Mg–Cu — оксид + NO₂ + O₂, после Cu — металл; соли аммония; '
                            'Fe(II) окисляется до Fe₂O₃', scale='4 вещества × 6 наборов продуктов — как задания банка '
                            '«…продуктами, которые образуются при нагревании этого вещества»', kes=['2.2', '2.3'],
                    fmt_='четыре цифры под буквами А–Г'))
def g_8dec(rng):
    return gen8(rng, 'ch-ege-08-decomposition', 'decomp')


# ================================================================= 9. Схема превращений X → Y

def els(f):
    try:
        return set(parse_formula(f))
    except ValueError:
        return set()


def central(f):
    """«Сквозной» элемент цепочки: металл соли/оксида/гидроксида; для солей Na, K, NH₄ — элемент аниона."""
    s = SUBS.get(f, {})
    io = s.get('ion')
    e = [x for x in parse_formula(f.split('·')[0]) if x not in ('H', 'O')]
    if io and not io.get('cplx'):
        ck, an = io['cat'], io['an']
        if ck in ('Na', 'K', 'Li', 'NH4', 'Rb', 'Cs') and an not in ('Cl', 'Br', 'I', 'F', 'NO3', 'CH3COO'):
            an_f = I.AN[an][0]
            return [x for x in parse_formula(an_f) if x not in ('H', 'O')][0]
        return CAT[ck][3] if ck in CAT and ck != 'NH4' else 'N'
    if io and io.get('cplx'):
        m = re.match(r'[A-Z][a-z]?', io['an']).group()
        return m
    if not e:
        return 'O'
    metals = [x for x in e if x in METALS]
    return metals[0] if metals else e[0]


METALS = {'Li', 'Na', 'K', 'Rb', 'Cs', 'Be', 'Mg', 'Ca', 'Sr', 'Ba', 'Al', 'Zn', 'Fe', 'Cr', 'Mn', 'Cu', 'Ag', 'Hg',
          'Pb', 'Sn', 'Ni', 'Au', 'Pt'}
CAT = I.CAT


def carriers(r, src):
    """Продукты реакции, содержащие «сквозной» элемент исходного вещества."""
    key = central(src)
    return [x for x in dict.fromkeys(r['rhs']) if x != 'H2O' and key in els(x) and x in SUBS]


def two_reagents(r):
    base = [x for x in dict.fromkeys(r['lhs']) if x != 'H2O']
    return base if len(base) == 2 else None


REAG9 = [('HCl', ''), ('H2SO4', 'разб.'), ('H2SO4', 'конц.'), ('HNO3', 'разб.'), ('HNO3', 'конц.'), ('NaOH', ''),
         ('KOH', ''), ('Ca(OH)2', ''), ('Ba(OH)2', ''), ('NH3·H2O', ''), ('H2O', ''), ('O2', ''), ('H2', ''),
         ('Cl2', ''), ('Br2', ''), ('CO2', ''), ('SO2', ''), ('CO', ''), ('C', ''), ('Fe', ''), ('Zn', ''), ('Cu', ''),
         ('Mg', ''), ('Al', ''), ('AgNO3', ''), ('BaCl2', ''), ('Na2CO3', ''), ('K2CO3', ''), ('Na2S', ''), ('KI', ''),
         ('KMnO4', ''), ('K2Cr2O7', ''), ('H2O2', ''), ('Na2SO4', ''), ('NaCl', ''), ('KNO3', ''), ('H2S', ''),
         ('Na3PO4', ''), ('K3PO4', ''), ('HBr', ''), ('HI', ''), ('NaNO3', ''), ('CuO', ''), ('KCl', ''),
         ('Na2SO3', ''), ('NH4Cl', ''), ('FeCl3', ''), ('CuSO4', ''), ('Pb(NO3)2', ''), ('H3PO4', ''), ('LiOH', '')]


def step_can(S, o, lo, T):
    """Может ли S + o (форма lo) дать T: True/False/None (неизвестно)."""
    pos = pos_rx(S, '', o, lo)
    if any(T in r['rhs'] for r in pos):
        return True
    if pos:
        return False
    if reacts(S, '', o, lo) is False:
        return False
    need = els(T) - {'H', 'O'}
    if not need <= (els(S) | els(o)):
        return False
    return None


def _solve_9r(p):
    A, B, C = p['chain']
    ans = {}
    for letter, (S, T) in (('X', (A, B)), ('Y', (B, C))):
        hits = []
        for j, (o, lo) in enumerate(p['opts']):
            ok = any(T in r['rhs'] for r in RX if S in r['lhs'] and o in r['lhs'] and
                     set(r['lhs']) - {S, o} <= {'H2O'} and _form_ok(lo, FORM_OF(r, o), r.get('cond', '')))
            if ok:
                hits.append(str(j + 1))
        if len(hits) != 1:
            return {'err': letter}
        ans[letter] = hits[0]
    return ans


_SCHEME_HEAD = ['Задана схема превращений веществ:', 'В заданной схеме превращений']


def _arrow(lbl):
    return f' →({lbl}) '


@proto('ch-ege-09-reagents', 'ЕГЭ', 9, 'Схема A →X B →Y C: подобрать реагенты X и Y',
       invariant='по генетической связи классов подобрать реагенты для двух последовательных превращений',
       varies='цепочки из базы реакций: металлы, оксиды, гидроксиды, соли; реагенты — кислоты, щёлочи, соли, '
              'окислители/восстановители',
       answer_rule='X — реагент, переводящий A в B; Y — реагент, переводящий B в C; остальные реагенты перечня '
                   'дают другой продукт или не реагируют',
       mistakes=['берут реагент, который реагирует, но даёт другой продукт (Fe + Cl₂ → FeCl₃, а не FeCl₂)',
                 'не учитывают концентрацию кислоты', 'амфотерные гидроксиды растворяются в избытке щёлочи'],
       solve=_solve_9r, kind='dict', kes=['2.4'],
       fidelity=FID(9, trap='реагент-«ловушка» тоже реагирует с исходным веществом, но даёт другой продукт; '
                            'степень окисления продукта (Fe²⁺/Fe³⁺), кислая/средняя соль',
                    scale='цепочка из двух стрелок и пять реагентов — как 78 заданий банка (КЭС 2.4) и демоверсия 2027',
                    kes=['2.4'], fmt_='две цифры под буквами X, Y', style='«Задана схема превращений веществ: … '
                    'Определите, какие из указанных веществ являются веществами X и Y.»'))
def g_9r(rng):
    pid = 'ch-ege-09-reagents'
    for _ in range(40):
        r1 = rng.choice(RX)
        tr = two_reagents(r1)
        if not tr or 'электролиз' in r1['type'] or r1.get('cond', '').startswith('электролиз'):
            continue
        A, X = tr if rng.random() < 0.5 else tr[::-1]
        if SUBS[A]['cls'] == 'простое вещество' and A in ('O2', 'H2', 'N2') or A == 'H2O':
            continue
        cb = carriers(r1, A)
        if not cb:
            continue
        B = rng.choice(cb)
        r2s = [r for r in RX if B in r['lhs'] and two_reagents(r) and 'электролиз' not in r['type']]
        if not r2s:
            continue
        r2 = rng.choice(r2s)
        Y = next(x for x in two_reagents(r2) if x != B)
        cc = [x for x in carriers(r2, B) if x not in (A, B)]
        if not cc or Y == X:
            continue
        C = rng.choice(cc)
        break
    else:
        raise Retry
    lx = FORM_OF(r1, X) if FORM_OF(r1, X) in ('конц.', 'разб.') else ''
    ly = FORM_OF(r2, Y) if FORM_OF(r2, Y) in ('конц.', 'разб.') else ''
    if X in ('HNO3', 'H2SO4') and not lx or Y in ('HNO3', 'H2SO4') and not ly:
        raise Retry
    if step_can(A, X, lx, B) is not True or step_can(B, Y, ly, C) is not True:
        raise Retry
    dis = []
    for o in shuffled(rng, REAG9):
        if o[0] in (X, Y, A, B, C) or o in dis:
            continue
        if step_can(A, o[0], o[1], B) is False and step_can(B, o[0], o[1], C) is False:
            dis.append(o)
        if len(dis) == 3:
            break
    if len(dis) < 3:
        raise Retry
    items = shuffled(rng, [(X, lx), (Y, ly)] + dis)
    # X не должен давать C из B, а Y — B из A (иначе двусмысленно)
    if step_can(A, Y, ly, B) is not False or step_can(B, X, lx, C) is not False:
        raise Retry
    ans = {'X': str(items.index((X, lx)) + 1), 'Y': str(items.index((Y, ly)) + 1)}
    scheme = F(A) + _arrow('X') + F(B) + _arrow('Y') + F(C)
    q = (f'Задана схема превращений веществ: {scheme}. Определите, какие из указанных веществ являются веществами '
         f'X и Y. Запишите в таблицу номера выбранных веществ под соответствующими буквами.')
    by_name = rng.random() < 0.35
    txt = lambda o: (ru(o[0]) + (f' ({o[1]})' if o[1] else '')) if by_name else FL(*o)
    e = f'X: {eq_text(r1["lhs"], r1["rhs"])}; Y: {eq_text(r2["lhs"], r2["rhs"])}.'
    return card(pid, q, ans, e, k='match', o=match_opts(['X', 'Y'], [txt(o) for o in items], lids='XY'),
                p={'chain': [A, B, C], 'opts': [list(o) for o in items]},
                eqs=[(r1['lhs'], r1['rhs'], *r1['k']), (r2['lhs'], r2['rhs'], *r2['k'])])


def _union_products(S, o, lo):
    if o == 't':
        return {x for r in SINGLE.get(S, []) for x in r['rhs']}
    return {x for r in pos_rx(S, '', o, lo) for x in r['rhs']}


def _solve_9s(p):
    A, (R1, l1), (R2, l2) = p['A'], p['r1'], p['r2']
    opts_ = p['opts']
    u1 = set()
    for r in RX:
        if R1 == 't':
            if r['lhs'] == [A]:
                u1 |= set(r['rhs'])
        elif A in r['lhs'] and R1 in r['lhs'] and set(r['lhs']) - {A, R1} <= {'H2O'} and \
                _form_ok(l1, FORM_OF(r, R1), r.get('cond', '')):
            u1 |= set(r['rhs'])
    xs = [o for o in opts_ if o in u1]
    if len(xs) != 1:
        return {'err': 'X'}
    X = xs[0]
    u2 = set()
    for r in RX:
        if R2 == 't':
            if r['lhs'] == [X]:
                u2 |= set(r['rhs'])
        elif X in r['lhs'] and R2 in r['lhs'] and set(r['lhs']) - {X, R2} <= {'H2O'} and \
                _form_ok(l2, FORM_OF(r, R2), r.get('cond', '')):
            u2 |= set(r['rhs'])
    ys = [o for o in opts_ if o in u2 and o != X]
    if len(ys) != 1:
        return {'err': 'Y'}
    return {'X': str(opts_.index(X) + 1), 'Y': str(opts_.index(ys[0]) + 1)}


def _pick_step(rng, S, exclude=()):
    """Случайная реакция S (+ один реагент или нагревание) → carrier. Возвращает (reagent, label, product, r)."""
    rs = [r for r in RX if S in r['lhs'] and (two_reagents(r) or r['lhs'] == [S]) and 'электролиз' not in r['type']]
    rng.shuffle(rs)
    for r in rs:
        if r['lhs'] == [S]:
            if 't' not in r.get('cond', ''):
                continue
            R, lab = 't', ''
        else:
            R = next(x for x in two_reagents(r) if x != S)
            lab = FORM_OF(r, R) if FORM_OF(r, R) in ('конц.', 'разб.') else ''
            if R in ('HNO3', 'H2SO4') and not lab:
                continue
        cc = [x for x in carriers(r, S) if x not in exclude]
        if cc:
            return R, lab, rng.choice(cc), r
    return None


def _related(f, rng, k=12):
    key = els(f) - {'H', 'O'}
    pool = [x for x, s in SUBS.items() if s.get('_mod') == 'chemdb_inorg.py' and els(x) & key and x != f
            and '·' not in x and 'Hg' not in x and not x.startswith(('Rb', 'Cs', 'Sr'))]
    rng.shuffle(pool)
    return pool[:k]


def _lab9(R, lab):
    if R == 't':
        return 't°'
    return FL(R, lab)


@proto('ch-ege-09-substances', 'ЕГЭ', 9, 'Схема A →(реагент) X →(реагент) Y: определить вещества X и Y',
       invariant='по известным реагентам и условиям определить продукты двух последовательных превращений',
       varies='исходное вещество, реагенты/условия над стрелками (t°, кислоты, щёлочи, окислители)',
       answer_rule='X — продукт первого превращения, Y — продукт второго (из вещества X)',
       mistakes=['не учитывают степень окисления продукта', 'кислая/средняя соль', 'амфотерность при избытке'],
       solve=_solve_9s, kind='dict', kes=['2.4'],
       fidelity=FID(9, trap='в перечне — соединения того же элемента в других степенях окисления и другие соли',
                    scale='схема из двух стрелок с реагентами над ними, пять веществ — как задания банка вида '
                          '«Fe →Cl₂ X →Y FeS», «H₂O₂ →MnO₂ X →Y K₂SO₄»', kes=['2.4'],
                    fmt_='две цифры под буквами X, Y'))
def g_9s(rng):
    pid = 'ch-ege-09-substances'
    A = rng.choice([x for x in SUBS if SUBS[x].get('_mod') == 'chemdb_inorg.py' and x in PARTNERS and
                    SUBS[x]['cls'] != 'бинарное' and x not in ('H2O', 'O2', 'H2')])
    s1 = _pick_step(rng, A)
    if not s1:
        raise Retry
    R1, l1, X, r1 = s1
    s2 = _pick_step(rng, X, exclude=(A,))
    if not s2:
        raise Retry
    R2, l2, Y, r2 = s2
    if Y == X:
        raise Retry
    u1, u2 = _union_products(A, R1, l1), _union_products(X, R2, l2)
    if Y in u1:
        raise Retry
    dis = [f for f in _related(X, rng, 20) + _related(Y, rng, 20)
           if f not in u1 and f not in u2 and f not in (A, X, Y)]
    dis = list(dict.fromkeys(dis))[:3]
    if len(dis) < 3:
        raise Retry
    items = shuffled(rng, [X, Y] + dis)
    ans = {'X': str(items.index(X) + 1), 'Y': str(items.index(Y) + 1)}
    scheme = F(A) + _arrow(_lab9(R1, l1)) + 'X' + _arrow(_lab9(R2, l2)) + 'Y'
    q = (f'Задана схема превращений веществ: {scheme}. Определите, какие из указанных веществ являются веществами '
         f'X и Y. Запишите в таблицу номера выбранных веществ под соответствующими буквами.')
    e = f'{eq_text(r1["lhs"], r1["rhs"])}; {eq_text(r2["lhs"], r2["rhs"])}.'
    return card(pid, q, ans, e, k='match', o=match_opts(['X', 'Y'], [F(x) for x in items], lids='XY'),
                p={'A': A, 'r1': [R1, l1], 'r2': [R2, l2], 'opts': items},
                eqs=[(r1['lhs'], r1['rhs'], *r1['k']), (r2['lhs'], r2['rhs'], *r2['k'])])


def _solve_9m(p):
    A, (R1, l1), C = p['A'], p['r1'], p['C']
    opts_ = [tuple(o) for o in p['opts']]
    u1 = set()
    for r in RX:
        if R1 == 't':
            if r['lhs'] == [A]:
                u1 |= set(r['rhs'])
        elif A in r['lhs'] and R1 in r['lhs'] and set(r['lhs']) - {A, R1} <= {'H2O'} and \
                _form_ok(l1, FORM_OF(r, R1), r.get('cond', '')):
            u1 |= set(r['rhs'])
    xs = [o for o in opts_ if o[0] in u1 and not o[1]]
    if len(xs) != 1:
        return {'err': 'X'}
    X = xs[0][0]
    ys = []
    for j, (o, lo) in enumerate(opts_):
        if any(C in r['rhs'] for r in RX if X in r['lhs'] and o in r['lhs'] and set(r['lhs']) - {X, o} <= {'H2O'}
               and _form_ok(lo, FORM_OF(r, o), r.get('cond', ''))):
            ys.append(str(j + 1))
    if len(ys) != 1:
        return {'err': 'Y'}
    return {'X': str(opts_.index(xs[0]) + 1), 'Y': ys[0]}


@proto('ch-ege-09-mixed', 'ЕГЭ', 9, 'Схема A →(реагент) X →Y C: вещество X и реагент Y',
       invariant='определить продукт первого превращения и подобрать реагент для второго',
       varies='исходное и конечное вещества, реагент/условие первой стрелки',
       answer_rule='X — продукт A с указанным реагентом; Y — реагент, переводящий X в C',
       mistakes=['путают продукты разложения (CuO/Cu₂O)', 'берут реагент, не дающий C'],
       solve=_solve_9m, kind='dict', kes=['2.4'],
       fidelity=FID(9, trap='вещество X узнают по реагенту первой стрелки; реагент Y проверяют по продукту C',
                    scale='схема «Cu(OH)₂ →t° X →Y Cu» — как задания банка, где X — вещество, Y — реагент',
                    kes=['2.4'], fmt_='две цифры под буквами X, Y'))
def g_9m(rng):
    pid = 'ch-ege-09-mixed'
    A = rng.choice([x for x in SUBS if SUBS[x].get('_mod') == 'chemdb_inorg.py' and x in PARTNERS and
                    SUBS[x]['cls'] not in ('бинарное',) and x not in ('H2O', 'O2', 'H2')])
    s1 = _pick_step(rng, A)
    if not s1:
        raise Retry
    R1, l1, X, r1 = s1
    r2s = [r for r in RX if X in r['lhs'] and two_reagents(r) and 'электролиз' not in r['type']]
    if not r2s:
        raise Retry
    r2 = rng.choice(r2s)
    Y = next(x for x in two_reagents(r2) if x != X)
    ly = FORM_OF(r2, Y) if FORM_OF(r2, Y) in ('конц.', 'разб.') else ''
    if Y in ('HNO3', 'H2SO4') and not ly:
        raise Retry
    cc = [x for x in carriers(r2, X) if x not in (A, X)]
    if not cc:
        raise Retry
    C = rng.choice(cc)
    u1 = _union_products(A, R1, l1)
    if C in u1 or Y in u1 or step_can(X, Y, ly, C) is not True:
        raise Retry
    dis_s = [f for f in _related(X, rng, 20) if f not in u1 and f not in (A, C, Y)]
    dis_r = [o for o in shuffled(rng, REAG9) if o[0] not in (X, Y, A, C) and o[0] not in u1 and
             step_can(X, o[0], o[1], C) is False]
    if not dis_s or not dis_r:
        raise Retry
    n_s = rng.choice([1, 2])
    dis = [(f, '') for f in dis_s[:n_s]] + dis_r[:3 - n_s]
    if len(dis) < 3:
        raise Retry
    # вещества-дистракторы не должны сами давать C с каким-либо реагентом перечня как «X»
    items = shuffled(rng, [(X, ''), (Y, ly)] + dis)
    if len({o[0] for o in items}) < 5:
        raise Retry
    for o in items:
        if o[0] in u1 and o[0] != X:
            raise Retry
        if o != (Y, ly) and step_can(X, o[0], o[1], C) is not False:
            raise Retry
    ans = {'X': str(items.index((X, '')) + 1), 'Y': str(items.index((Y, ly)) + 1)}
    scheme = F(A) + _arrow(_lab9(R1, l1)) + 'X' + _arrow('Y') + F(C)
    q = (f'Задана схема превращений веществ: {scheme}. Определите, какие из указанных веществ являются веществами '
         f'X и Y. Запишите в таблицу номера выбранных веществ под соответствующими буквами.')
    e = f'{eq_text(r1["lhs"], r1["rhs"])}; {eq_text(r2["lhs"], r2["rhs"])}.'
    return card(pid, q, ans, e, k='match', o=match_opts(['X', 'Y'], [FL(*o) for o in items], lids='XY'),
                p={'A': A, 'r1': [R1, l1], 'C': C, 'opts': [list(o) for o in items]},
                eqs=[(r1['lhs'], r1['rhs'], *r1['k']), (r2['lhs'], r2['rhs'], *r2['k'])])


# ================================================================= степени окисления и типы реакций

def ox_of(f):
    """Степени окисления элементов вещества: {el: int}; None, если у какого-то элемента их несколько/дробная."""
    o = SUBS.get(f, {}).get('ox')
    if not o:
        return None
    out = {}
    for e, v in o.items():
        if isinstance(v, list):
            if len(set(v)) != 1:
                return None
            v = v[0]
        if isinstance(v, Fr) and v.denominator != 1:
            return None
        out[e] = int(v)
    return out


def ox_changes(r):
    """{элемент: (множество ст. ок. в реагентах, множество в продуктах)} для элементов, где они различаются;
    None — если есть вещество со «смешанной» степенью окисления."""
    L, Rr = {}, {}
    for side, d in ((r['lhs'], L), (r['rhs'], Rr)):
        for f in side:
            o = ox_of(f)
            if o is None:
                return None
            for e, v in o.items():
                d.setdefault(e, set()).add(v)
    return {e: (L.get(e, set()), Rr.get(e, set())) for e in set(L) | set(Rr) if L.get(e) != Rr.get(e)}


def is_redox(r):
    ch = ox_changes(r)
    if ch is None:
        return 'ОВР' in r['type']
    return bool(ch)


_SIMPLE = lambda f: SUBS.get(f, {}).get('cls') == 'простое вещество'


def rtype(r):
    L = [x for x in r['lhs']]
    Rr = [x for x in r['rhs']]
    if len(L) >= 2 and len(Rr) == 1:
        return 'соединения'
    if len(L) == 1 and len(Rr) >= 2:
        return 'разложения'
    if len(L) == 2 and len(Rr) == 2 and sum(map(_SIMPLE, L)) == 1 and sum(map(_SIMPLE, Rr)) == 1:
        return 'замещения'
    if len(L) == 2 and not any(map(_SIMPLE, L + Rr)) and not is_redox(r):
        return 'обмена'
    return None


# ================================================================= 17. Классификация реакций

_IRREV_TAGS = {'горение', 'металл+кислота', 'металл+вода', 'соль+соль', 'щёлочь+соль', 'кислота+карбонат',
               'кислота+сульфид', 'кислота+основание', 'гидролиз бинарного соединения', 'металл+кислота-окислитель',
               'металл+соль', 'кислота+соль (осадок)', 'кислота+силикат', 'кислота+сульфит', 'щёлочь+соль аммония',
               'аммиачная вода+соль', 'основный оксид+кислота', 'амфотерный оксид+кислота', 'галоген+галогенид',
               'металл+галоген', 'металл+кислород', 'разложение нитрата', 'разложение соли'}


def _phase(r):
    if r.get('phase'):
        return r['phase']
    L = [x for x in dict.fromkeys(r['lhs']) if x != 'H2O']
    if not L:
        return None
    st = lambda x: SUBS.get(x, {}).get('state')
    if r.get('aq'):
        ok = lambda x: SUBS[x].get('sol') == 'р' or x in I.ALKALIS or SUBS[x]['cls'] == 'кислота' and x != 'H2SiO3'
        if all(ok(x) for x in L):
            return 'гомо'
        if any(st(x) == 'тв' and not ok(x) for x in L):
            return 'гетеро'
        return None
    if len(L) >= 2 or 'H2O' in r['lhs']:
        states = {st(x) for x in r['lhs']}
        if states == {'г'}:
            return 'гомо'
        if 'тв' in states and len(states) > 1 or states == {'тв'} and len(L) >= 2:
            return 'гетеро'
    return None


def attrs(r):
    T = rtype(r)
    tags = set(r.get('tags', []))
    a = {t: (T == t) for t in ('соединения', 'разложения', 'замещения', 'обмена')}
    if 'совместный гидролиз' in tags or T is None and len(r['lhs']) >= 3:
        a['обмена'] = None
    red = is_redox(r)
    a['окислительно-восстановительная'] = red
    ph = _phase(r)
    a['гомогенная'] = None if ph is None else ph == 'гомо'
    a['гетерогенная'] = None if ph is None else ph == 'гетеро'
    heat = r.get('heat')
    if heat is None and 'нейтрализации' in r['type']:
        heat = 'экзо'
    if heat is None and tags & {'горение'}:
        heat = 'экзо'
    a['экзотермическая'] = None if heat is None else heat == 'экзо'
    a['эндотермическая'] = None if heat is None else heat == 'эндо'
    if r.get('rev'):
        rv = True
    elif tags & _IRREV_TAGS:
        rv = False
    else:
        rv = None
    a['обратимая'] = rv
    a['необратимая'] = None if rv is None else not rv
    cat = bool(r.get('cat')) or 'кат' in r.get('cond', '')
    a['каталитическая'] = cat
    a['некаталитическая'] = not cat
    a['нейтрализации'] = 'нейтрализации' in r['type']
    a['ионного обмена'] = (T == 'обмена' and bool(r.get('aq'))) if T == 'обмена' and r.get('aq') is not None \
        else (False if T != 'обмена' and a['обмена'] is not None else None)
    a['без изменения степеней окисления'] = not red
    return a


_ADJ = {'конц.': 'концентрированной ', 'разб.': 'разбавленной ', 'оч. разб.': 'очень разбавленной '}


def _ins_form(x, form):
    return (_ADJ.get(form, '') if x in ('HNO3', 'H2SO4', 'HCl') else '') + ins(x)


def describe(r):
    """«взаимодействие оксида натрия с водой», «разложение нитрата меди(II)»."""
    L = [x for x in dict.fromkeys(r['lhs']) if x != 'H2O']
    if 'H2O' in r['lhs'] and len(L) == 1:
        L = L + ['H2O']
    if len(L) == 1:
        s = 'разложение ' + gen(L[0])
        if 't' in r.get('cond', ''):
            s += ' при нагревании'
        return s
    if len(L) != 2:
        return None
    a, b = L
    order = ['простое вещество', 'оксид', 'основание', 'амфотерный гидроксид', 'соль', 'бинарное', 'кислота']
    if b != 'H2O' and SUBS[a]['cls'] in order and SUBS[b]['cls'] in order and \
            order.index(SUBS[a]['cls']) > order.index(SUBS[b]['cls']):
        a, b = b, a
    if 'горение' in r.get('tags', []) and b == 'O2':
        return 'горение ' + gen(a) + ' в кислороде'
    return f'взаимодействие {gen(a)} с {_ins_form(b, FORM_OF(r, b) or "")}'


POOL17 = [r for r in RX if describe(r) and 'электролиз' not in r['type'] and
          len({describe(x) for x in RX if describe(x) == describe(r)}) >= 1]
_DESC_COUNT = Counter(describe(r) for r in POOL17)
POOL17 = [r for r in POOL17 if _DESC_COUNT[describe(r)] == 1]   # описание однозначно задаёт реакцию
ATTR_NAMES = ['соединения', 'разложения', 'замещения', 'обмена', 'окислительно-восстановительная', 'гомогенная',
              'гетерогенная', 'экзотермическая', 'эндотермическая', 'обратимая', 'необратимая', 'каталитическая',
              'нейтрализации', 'ионного обмена']
RX17 = {r['rid']: r for r in POOL17}


def _solve_17match(p):
    ans = {}
    for i, rid in enumerate(p['rids']):
        a = attrs(RX_BY_ID[rid])
        hits = [str(j + 1) for j, (t1, t2) in enumerate(p['opts']) if a.get(t1) and a.get(t2)]
        if len(hits) != 1:
            return {'err': rid}
        ans[LET[i]] = hits[0]
    return ans


_SECOND = ['окислительно-восстановительная', 'гомогенная', 'гетерогенная', 'экзотермическая', 'эндотермическая',
           'обратимая', 'необратимая', 'каталитическая', 'без изменения степеней окисления']


@proto('ch-ege-17-match', 'ЕГЭ', 17, 'Реакция (словесное описание) ↔ пара классификационных признаков',
       invariant='определить тип реакции по числу/составу реагентов и продуктов и второй признак: ОВР, фазовый '
                 'состав, тепловой эффект, обратимость, участие катализатора',
       varies='три реакции неорганической химии (соединения, разложения, замещения, обмена), наборы признаков',
       answer_rule='каждой реакции — вариант, оба признака которого ей присущи (варианты могут повторяться)',
       mistakes=['Na₂O + H₂O считают гомогенной', 'гидролиз Al₂S₃ относят к соединению',
                 'реакцию металла с солью называют обменом', 'горение считают эндотермическим'],
       solve=_solve_17match, kind='dict', kes=['1.5'],
       fidelity=FID(17, trap='оба признака должны выполняться; «соединения, гомогенная» vs «соединения, '
                             'экзотермическая» для Na₂O + H₂O', scale='3 реакции × 4 пары признаков — как демоверсия '
                             '2027 (оксид натрия с водой, гидролиз сульфида алюминия, хлор с порошком железа)',
                    kes=['1.5'], fmt_='три цифры под буквами А–В, цифры могут повторяться'))
def g_17match(rng):
    pid = 'ch-ege-17-match'
    rs = []
    for r in shuffled(rng, POOL17):
        a = attrs(r)
        T = rtype(r)
        if not T or a.get(T) is not True:
            continue
        good2 = [x for x in _SECOND if a.get(x) is True]
        if not good2 or any(rtype(x) == T and x is not r for x in rs) and rng.random() < 0.6:
            continue
        rs.append(r)
        if len(rs) == 3:
            break
    if len(rs) < 3:
        raise Retry
    opts_ = []
    for r in rs:
        a = attrs(r)
        good2 = [x for x in _SECOND if a.get(x) is True]
        opts_.append((rtype(r), rng.choice(good2)))
    types = ['соединения', 'разложения', 'замещения', 'обмена']
    for _ in range(30):
        if len(set(opts_)) >= 4:
            break
        opts_.append((rng.choice(types), rng.choice(_SECOND)))
    opts_ = list(dict.fromkeys(opts_))[:4]
    if len(opts_) < 4:
        raise Retry
    rng.shuffle(opts_)
    ans = {}
    for i, r in enumerate(rs):
        a = attrs(r)
        hits = []
        for j, (t1, t2) in enumerate(opts_):
            v1, v2 = a.get(t1), a.get(t2)
            if v1 is None or (v1 and v2 is None):
                raise Retry
            if v1 and v2:
                hits.append(str(j + 1))
        if len(hits) != 1:
            raise Retry
        ans[LET[i]] = hits[0]
    left = [describe(r) for r in rs]
    right = [f'{t1}, {t2}' for t1, t2 in opts_]
    q = ('Установите соответствие между химической реакцией и типами реакции, к которым она относится: к каждой '
         'позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой. Запишите в таблицу '
         'выбранные цифры под соответствующими буквами.')
    e = '; '.join(f'{LET[i]}) {eq_text(r["lhs"], r["rhs"])} — {right[int(ans[LET[i]]) - 1]}' for i, r in enumerate(rs))
    return card(pid, q, ans, e + '.', k='match', o=match_opts(left, right),
                p={'rids': [r['rid'] for r in rs], 'opts': [list(x) for x in opts_]},
                eqs=[(r['lhs'], r['rhs'], *r['k']) for r in rs])


def _solve_17types(p):
    a = attrs(RX_BY_ID[p['rid']])
    return [str(i + 1) for i, t in enumerate(p['types']) if a.get(t)]


@proto('ch-ege-17-types', 'ЕГЭ', 17, 'Выбрать все типы, к которым относится данная реакция',
       invariant='классифицировать одну реакцию сразу по нескольким признакам',
       varies='реакция (словесно), пять признаков из списка: тип, ОВР, фазы, тепловой эффект, обратимость, '
              'катализ, нейтрализация, ионный обмен',
       answer_rule='номера всех признаков, которые выполняются для этой реакции',
       mistakes=['реакцию металла с кислотой называют обменом', 'не замечают изменения степеней окисления',
                 'гетерогенность при участии твёрдого вещества'],
       solve=_solve_17types, kind='dict', kes=['1.5'],
       fidelity=FID(17, trap='набор признаков, где верны 2–3; «лишний» признак близок по смыслу (обмена/замещения, '
                             'гомогенная/гетерогенная)', scale='одна реакция и пять признаков — как задания банка '
                             '«Из предложенного перечня выберите все типы реакций, к которым можно отнести…» '
                             '(КЭС 1.5, 55 заданий)', kes=['1.5'], fmt_='номера выбранных признаков (все верные)',
                    style='«Из предложенного перечня выберите все типы реакций, к которым можно отнести '
                          'взаимодействие…»'))
def g_17types(rng):
    pid = 'ch-ege-17-types'
    r = rng.choice(POOL17)
    a = attrs(r)
    known = [t for t in ATTR_NAMES if a.get(t) is not None]
    yes = [t for t in known if a[t]]
    no = [t for t in known if not a[t]]
    if len(yes) < 2 or len(no) < 2:
        raise Retry
    k_yes = rng.choice([2, 2, 3]) if len(yes) >= 3 else 2
    pick = rng.sample(yes, k_yes) + rng.sample(no, 5 - k_yes)
    if len(set(pick)) < 5:
        raise Retry
    rng.shuffle(pick)
    ans = [str(i + 1) for i, t in enumerate(pick) if a[t]]
    d = describe(r)
    q = (f'Из предложенного перечня выберите все типы реакций, к которым можно отнести {d}. '
         f'Запишите номера выбранных ответов.')
    e = f'{eq_text(r["lhs"], r["rhs"])}: ' + ', '.join(t for t in pick if a[t]) + '.'
    return card(pid, q, ans, e, k='many', o=opts([t if t in ('нейтрализации', 'ионного обмена', 'соединения',
                                                              'разложения', 'замещения', 'обмена') and False else t
                                                  for t in pick]),
                p={'rid': r['rid'], 'types': pick}, eqs=[(r['lhs'], r['rhs'], *r['k'])])


def _pair_desc(r):
    L = [x for x in dict.fromkeys(r['lhs']) if x != 'H2O']
    if 'H2O' in r['lhs'] and len(L) == 1:
        L.append('H2O')
    if len(L) != 2:
        return None
    return ' и '.join(ru(x) + (f' ({FORM_OF(r, x)})' if FORM_OF(r, x) in ('конц.', 'разб.') else '') for x in L)


def _pair_rxs(rid):
    r = RX_BY_ID[rid]
    L = frozenset(x for x in r['lhs'] if x != 'H2O') | ({'H2O'} if len(set(r['lhs']) - {'H2O'}) == 1 else set())
    same = [x for x in RX if (frozenset(y for y in x['lhs'] if y != 'H2O') |
                               ({'H2O'} if len(set(x['lhs']) - {'H2O'}) == 1 else set())) == L
            and all((FORM_OF(x, f) or '') == (FORM_OF(r, f) or '') for f in L if f in ('HNO3', 'H2SO4'))]
    return same


def _solve_17pairs(p):
    out = []
    for i, rid in enumerate(p['rids']):
        vals = {attrs(x).get(p['type']) for x in _pair_rxs(rid)}
        if vals == {True}:
            out.append(str(i + 1))
    return out


@proto('ch-ege-17-pairs', 'ЕГЭ', 17, 'Выбрать все пары веществ, реакция между которыми относится к заданному типу',
       invariant='для каждой пары веществ представить продукты и определить тип реакции',
       varies='тип (соединения, замещения, обмена, ОВР, нейтрализации), пять пар веществ',
       answer_rule='номера всех пар, взаимодействие которых относится к названному типу',
       mistakes=['FeCl₂ + Cl₂ относят к замещению', 'KI + Cl₂ — к соединению', 'NH₃ + HCl — к обмену'],
       solve=_solve_17pairs, kind='dict', kes=['1.5'],
       fidelity=FID(17, trap='пары с похожим составом, но разным типом (Na + H₂O / Na₂O + H₂O; FeCl₂ + Cl₂ / KI + Cl₂)',
                    scale='пять пар веществ — как задания банка «Из предложенного перечня выберите все пары '
                          'веществ, взаимодействие между которыми является реакцией соединения»', kes=['1.5'],
                    fmt_='номера всех верных пар'))
def g_17pairs(rng):
    pid = 'ch-ege-17-pairs'
    T = rng.choice(['соединения', 'замещения', 'обмена', 'окислительно-восстановительная', 'нейтрализации'])
    cand = [r for r in POOL17 if _pair_desc(r) and len(r['lhs']) <= 3]
    yes, no = [], []
    for r in shuffled(rng, cand):
        vals = {attrs(x).get(T) for x in _pair_rxs(r['rid'])}
        if vals == {True} and len(yes) < 3:
            yes.append(r)
        elif vals == {False} and len(no) < 4:
            no.append(r)
        if len(yes) == 3 and len(no) == 4:
            break
    k = rng.choice([2, 3]) if len(yes) >= 3 else 2
    if len(yes) < k or len(no) < 5 - k:
        raise Retry
    items = shuffled(rng, yes[:k] + no[:5 - k])
    descs = [_pair_desc(r) for r in items]
    if len(set(descs)) < 5:
        raise Retry
    ans = [str(i + 1) for i, r in enumerate(items) if r in yes]
    phr = {'соединения': 'реакцией соединения', 'замещения': 'реакцией замещения', 'обмена': 'реакцией обмена',
           'окислительно-восстановительная': 'окислительно-восстановительной реакцией',
           'нейтрализации': 'реакцией нейтрализации'}[T]
    q = (f'Из предложенного перечня выберите все пары веществ, взаимодействие между которыми является {phr}. '
         f'Запишите номера выбранных ответов.')
    e = '; '.join(eq_text(r['lhs'], r['rhs']) for r in items if r in yes) + f' — {phr}.'
    return card(pid, q, ans, e, k='many', o=opts(descs), p={'rids': [r['rid'] for r in items], 'type': T},
                eqs=[(r['lhs'], r['rhs'], *r['k']) for r in items])


def _solve_17dec(p):
    out = []
    for i, f in enumerate(p['items']):
        rs = [r for r in RX if r['lhs'] == [f] and 't' in r.get('cond', '')]
        vals = {is_redox(r) for r in rs}
        if vals == {True}:
            out.append(str(i + 1))
    return out


DEC17 = {}
for _r in RX:
    if len(_r['lhs']) == 1 and 't' in _r.get('cond', '') and 'электролиз' not in _r['type']:
        DEC17.setdefault(_r['lhs'][0], []).append(_r)


@proto('ch-ege-17-decomposition', 'ЕГЭ', 17, 'Разложение каких веществ является ОВР (или не является)',
       invariant='представить продукты термического разложения и проверить изменение степеней окисления',
       varies='пять веществ: нитраты, карбонаты, гидрокарбонаты, соли аммония, гидроксиды, KMnO₄, KClO₃',
       answer_rule='номера веществ, разложение которых — ОВР (или, в обратной формулировке, — не ОВР)',
       mistakes=['разложение нитратов и NH₄NO₂ не считают ОВР', 'разложение NH₄Cl считают ОВР',
                 'разложение Fe(OH)₃ считают ОВР'],
       solve=lambda p: _solve_17dec_any(p), kind='dict', kes=['1.5'],
       fidelity=FID(17, trap='нитраты, NH₄NO₃/NH₄NO₂, (NH₄)₂Cr₂O₇, KMnO₄, KClO₃ — ОВР; карбонаты, гидроксиды, '
                             'NH₄Cl, (NH₄)₂CO₃ — нет', scale='пять веществ — как задания банка «выберите два вещества, '
                             'разложение которых является окислительно-восстановительной реакцией»', kes=['1.5'],
                    fmt_='номера выбранных веществ'))
def g_17dec(rng):
    pid = 'ch-ege-17-decomposition'
    red = [f for f, rs in DEC17.items() if {is_redox(r) for r in rs} == {True}]
    non = [f for f, rs in DEC17.items() if {is_redox(r) for r in rs} == {False}]
    want = rng.random() < 0.75
    good, bad = (red, non) if want else (non, red)
    k = 2
    items = shuffled(rng, rng.sample(good, k) + rng.sample(bad, 5 - k))
    ans = [str(i + 1) for i, f in enumerate(items) if f in good]
    by_name = rng.random() < 0.6
    txt = [ru(f) if by_name else F(f) for f in items]
    q = (f'Из предложенного перечня выберите два вещества, реакция разложения которых '
         f'{"" if want else "не "}является окислительно-восстановительной. Запишите номера выбранных ответов.')
    e = '; '.join(eq_text(DEC17[f][0]['lhs'], DEC17[f][0]['rhs']) for f in items if f in good) + '.'
    p = {'items': items}
    if not want:
        p['neg'] = True
    return card(pid, q, ans, e, k='many', o=opts(txt), p=p,
                eqs=[(DEC17[f][0]['lhs'], DEC17[f][0]['rhs'], *DEC17[f][0]['k']) for f in items])


def _solve_17dec_any(p):
    out = _solve_17dec(p)
    if p.get('neg'):
        out = []
        for i, f in enumerate(p['items']):
            rs = [r for r in RX if r['lhs'] == [f] and 't' in r.get('cond', '')]
            if {is_redox(r) for r in rs} == {False}:
                out.append(str(i + 1))
    return out


PROTOS_FIX = {'ch-ege-17-decomposition': _solve_17dec_any}


def _solve_17reag(p):
    out = []
    for i, (f, lab) in enumerate(p['items']):
        rs = pos_rx(p['R'], p['RL'], f, lab)
        vals = {attrs(r).get(p['type']) for r in rs}
        if vals == {True}:
            out.append(str(i + 1))
    return out


@proto('ch-ege-17-reagent', 'ЕГЭ', 17, 'Выбрать все вещества, реакция которых с данным реагентом — нейтрализация/ОВР/обмен',
       invariant='для каждого вещества представить реакцию с общим реагентом и определить её тип',
       varies='реагент (щёлочь, кислота, окислитель), тип (нейтрализация, ОВР, соединения, обмена), пять веществ',
       answer_rule='номера всех веществ, реакция которых с реагентом относится к названному типу',
       mistakes=['кислотный оксид + щёлочь называют нейтрализацией', 'NO₂ + NaOH не считают ОВР',
                 'реакцию соли аммония со щёлочью считают нейтрализацией'],
       solve=_solve_17reag, kind='dict', kes=['1.5'],
       fidelity=FID(17, trap='нейтрализация — только кислота + основание; с NO₂, Cl₂, S щёлочь реагирует как ОВР',
                    scale='реагент + пять веществ — как задания банка «выберите все вещества, взаимодействие которых '
                          'с гидроксидом натрия является реакцией нейтрализации»', kes=['1.5'],
                    fmt_='номера всех верных веществ'))
def g_17reag(rng):
    pid = 'ch-ege-17-reagent'
    R, RL = rng.choice([('NaOH', ''), ('KOH', ''), ('Ba(OH)2', ''), ('HNO3', 'конц.'), ('HCl', ''), ('H2SO4', 'разб.'),
                        ('Ca(OH)2', ''), ('HNO3', 'разб.'), ('H2SO4', 'конц.')])
    T = rng.choice(['нейтрализации', 'окислительно-восстановительная', 'обмена', 'соединения'])
    yes, no = [], []
    for x, v in shuffled(rng, list(know(R + ('|' + RL if RL else '')).items())):
        if not v:
            continue
        rs = pos_rx(R, RL, x[0], x[1])
        vals = {attrs(r).get(T) for r in rs}
        if vals == {True}:
            yes.append(x)
        elif vals == {False}:
            no.append(x)
    if len(yes) < 2 or len(no) < 3:
        raise Retry
    k = rng.choice([2, 2, 3]) if len(yes) >= 3 else 2
    items = shuffled(rng, rng.sample(yes, k) + rng.sample(no, 5 - k))
    if len({x[0] for x in items}) < 5:
        raise Retry
    ans = [str(i + 1) for i, x in enumerate(items) if x in yes]
    phr = {'нейтрализации': 'реакцией нейтрализации', 'окислительно-восстановительная':
           'окислительно-восстановительной реакцией', 'обмена': 'реакцией обмена', 'соединения': 'реакцией соединения'}[T]
    rname = (_ADJ.get(RL, '') + ins(R)) if RL else ins(R)
    rname = rname.replace('ой кислотой', 'ой кислотой')
    q = (f'Из предложенного перечня выберите все вещества, взаимодействие которых с {rname} является {phr}. '
         f'Запишите номера выбранных ответов.')
    txt = [ru(x[0]) + (f' ({x[1]})' if x[1] else '') for x in items]
    ex = [eq_text(pos_rx(R, RL, x[0], x[1])[0]['lhs'], pos_rx(R, RL, x[0], x[1])[0]['rhs']) for x in items if x in yes]
    e = '; '.join(ex) + f' — {phr}.'
    return card(pid, q, ans, e, k='many', o=opts(txt),
                p={'R': R, 'RL': RL, 'type': T, 'items': [list(x) for x in items]})
