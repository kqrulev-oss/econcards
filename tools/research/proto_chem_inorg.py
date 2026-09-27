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
    return pcard(pid, q, ans, e, k='match', o=match_opts(cats, texts, rids='123456789'), p={'cats': cats, 'cells': items})


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
    return pcard(pid, q, ans, e, k='match', o=match_opts(left, groups), p={'items': items, 'groups': groups})


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
    return pcard(pid, q, ans, e, k='match', o=match_opts(left, right),
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
    by_name = rng.random() < 0.5
    txt = lambda x: (ru(x[0]) + (f' ({x[1]})' if x[1] else '')) if by_name else _rlabel(*x)
    ans = [str(i + 1) for i, x in enumerate(items) if x in right]
    f0, lab0 = csplit(c)
    cname = ru(f0) + (f' ({lab0})' if lab0 else '')
    q = rng.choice([f'Из предложенного перечня выберите два вещества, с каждым из которых взаимодействует {cname}.',
                    f'Из предложенного перечня веществ выберите два вещества, с которыми реагирует {cname}.']) + \
        ' Запишите номера выбранных ответов.'
    e = f'{CF(c)} реагирует с ' + ' и '.join(ins(x[0]) + (f' ({x[1]})' if x[1] else '') for x in right) + \
        '; с остальными веществами перечня реакция не идёт.'
    return pcard(pid, q, ans, e, k='many', o=opts([txt(x) for x in items]),
                 p={'center': c, 'opts': [list(x) for x in items]})
