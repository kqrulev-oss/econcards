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
    key = {central(f)}
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

def _evolved(r, x):
    """Выделяется ли газ x из раствора (галогеноводороды в водном растворе остаются растворёнными)."""
    if x not in I.GASES:
        return False
    if r.get('aq') and x in ('HCl', 'HBr', 'HI', 'HF'):
        return False
    return True


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
    elif tags & _IRREV_TAGS and not ('кислота+основание' in tags and not set(r['lhs']) & I.STRONG_ACIDS):
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


POOL17 = [r for r in RX if 'электролиз' not in r['type'] and describe(r)]
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
    many = 'все типы реакций' if k_yes > 2 or rng.random() < 0.5 else 'два типа реакций'
    if rng.random() < 0.55:
        q = (f'Из предложенного перечня выберите {many}, к которым можно отнести реакцию, протекающую в соответствии '
             f'с уравнением {eq_text(r["lhs"], r["rhs"])}. Запишите номера выбранных ответов.')
    else:
        q = (f'Из предложенного перечня выберите {many}, к которым можно отнести {d}. '
             f'Запишите номера выбранных ответов.')
    e = f'{eq_text(r["lhs"], r["rhs"])}: ' + ', '.join(t for t in pick if a[t]) + '.'
    word = rng.random() < 0.5
    lab = lambda t: (('реакция ' + t) if t in ('нейтрализации', 'ионного обмена', 'соединения', 'разложения',
                                              'замещения', 'обмена') else (t + ' реакция')) if word else t
    return card(pid, q, ans, e, k='many', o=opts([lab(t) for t in pick]),
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
    cand = [r for r in POOL17 if _pair_desc(r) and len(r['lhs']) <= 3 and not set(r['lhs']) & {'H2CO3', 'H2SO3'}]
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
        if not v or x[0] in ('H2CO3', 'H2SO3'):
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


# ================================================================= 19. ОВР: свойства элемента, окислитель/восстановитель

def _sgn(v):
    return f'+{v}' if v > 0 else ('0' if v == 0 else f'−{-v}')


def redox_roles(r):
    """{'ox': (el, from, to), 'red': (el, from, to)} или None, если картина не однозначна (несколько элементов)."""
    ch = ox_changes(r)
    if not ch:
        return None
    ups, downs = [], []
    for e, (L, Rr) in ch.items():
        if len(L) != 1:
            # сопропорционирование (NH4NO2 → N2): N и окислитель, и восстановитель — отдельный случай
            if len(L) == 2 and len(Rr) == 1:
                lo, hi = sorted(L)
                (p,) = Rr
                if lo < p < hi:
                    ups.append((e, lo, p))
                    downs.append((e, hi, p))
                    continue
            return None
        (a,) = L
        higher = [x for x in Rr if x > a]
        lower = [x for x in Rr if x < a]
        if len(higher) > 1 or len(lower) > 1:
            return None
        if higher:
            ups.append((e, a, higher[0]))
        if lower:
            downs.append((e, a, lower[0]))
    if len(ups) != 1 or len(downs) != 1:
        return None
    return {'red': ups[0], 'ox': downs[0]}


def agent_formula(r, role):
    """Формула вещества-окислителя/восстановителя среди реагентов (единственная), иначе None."""
    rr = redox_roles(r)
    if not rr:
        return None
    e, a, b = rr[role]
    cands = [f for f in dict.fromkeys(r['lhs']) if (ox_of(f) or {}).get(e) == a]
    return cands[0] if len(cands) == 1 else None


REDOX19 = [r for r in RX if redox_roles(r) and 'электролиз' not in r['type'] and len(r['lhs']) <= 3]


def _show19(r, mode):
    return eq_text(r['lhs'], r['rhs']).replace('→', '=') if mode == 'eq' else scheme_text(r['lhs'], r['rhs'])


def _solve_19change(p):
    ans = {}
    for i, rid in enumerate(p['rids']):
        r = RX_BY_ID[rid]
        # независимо: сравниваем ст. ок. по каждому элементу в реагентах и продуктах
        L, Rr = {}, {}
        for side, d in ((r['lhs'], L), (r['rhs'], Rr)):
            for f in side:
                for e, v in (ox_of(f) or {}).items():
                    d.setdefault(e, set()).add(v)
        found = None
        for e in L:
            for a in L[e]:
                for b in Rr.get(e, ()):
                    if (p['role'] == 'red' and b > a or p['role'] == 'ox' and b < a) and b not in L[e]:
                        found = f'{_sgn(a)} → {_sgn(b)}'
        hits = [str(j + 1) for j, t in enumerate(p['opts']) if t == found]
        if len(hits) != 1:
            return {'err': rid}
        ans[LET[i]] = hits[0]
    return ans


_EL_RU = {'N': 'азота', 'S': 'серы', 'Cl': 'хлора', 'C': 'углерода', 'P': 'фосфора', 'Fe': 'железа', 'Cu': 'меди',
          'Mn': 'марганца', 'Cr': 'хрома', 'I': 'иода', 'Br': 'брома', 'H': 'водорода', 'O': 'кислорода',
          'Si': 'кремния', 'Zn': 'цинка', 'Al': 'алюминия', 'Mg': 'магния', 'Na': 'натрия', 'K': 'калия', 'Ca': 'кальция',
          'Ag': 'серебра', 'Pb': 'свинца', 'Hg': 'ртути', 'F': 'фтора', 'Ba': 'бария', 'Li': 'лития'}


def _pick19(rng, pred, k=3, theme=None):
    pool = [r for r in REDOX19 if pred(r)]
    if theme:
        pool = [r for r in pool if theme(r)]
    if len(pool) < k:
        raise Retry
    out, keys = [], set()
    for r in shuffled(rng, pool):
        key = frozenset(r['lhs'])
        if key in keys:
            continue
        keys.add(key)
        out.append(r)
        if len(out) == k:
            return out
    raise Retry


@proto('ch-ege-19-change', 'ЕГЭ', 19, 'Уравнение/схема ОВР ↔ изменение степени окисления восстановителя (окислителя)',
       invariant='расставить степени окисления, найти элемент, который их повышает (понижает), записать переход',
       varies='три ОВР неорганической химии, роль (восстановитель/окислитель), запись: схема или уравнение',
       answer_rule='каждой реакции — переход степени окисления элемента-восстановителя (окислителя)',
       mistakes=['путают окислитель и восстановитель', 'пишут изменение для «зрителя» (NO₃⁻ в нитрате)',
                 'ошибаются со степенью окисления в пероксидах и сложных анионах'],
       solve=_solve_19change, kind='dict', kes=['1.12'],
       fidelity=FID(19, trap='в перечне — обратные переходы (+4 → +2 вместо +2 → +4) и переходы другого элемента той же '
                             'реакции', scale='3 реакции × 4 перехода — как демоверсия 2027 (Cu₂O, Cu, CuO) и ~24 задания '
                             'банка', kes=['1.12'], fmt_='три цифры под буквами А–В'))
def g_19change(rng):
    pid = 'ch-ege-19-change'
    role = rng.choice(['red', 'red', 'ox'])
    el = rng.choice(['N', 'S', 'Cl', 'C', 'Fe', 'Cu', 'Mn', 'Cr', 'P', 'H', 'I', 'O', None, None])
    theme = (lambda r: any(el in els(f) for f in r['lhs'])) if el else None
    rs = _pick19(rng, lambda r: True, 3, theme)
    chg = []
    for r in rs:
        e, a, b = redox_roles(r)[role]
        chg.append(f'{_sgn(a)} → {_sgn(b)}')
    if len(set(chg)) < 2 and rng.random() < 0.8:
        raise Retry
    # дистракторы: обратные переходы и переходы «другой роли»
    dis = []
    for r in rs:
        rr = redox_roles(r)
        other = 'ox' if role == 'red' else 'red'
        e, a, b = rr[role]
        e2, a2, b2 = rr[other]
        dis += [f'{_sgn(b)} → {_sgn(a)}', f'{_sgn(a2)} → {_sgn(b2)}']
    opts_ = list(dict.fromkeys(chg))
    for d in shuffled(rng, dis):
        if len(opts_) >= 4:
            break
        if d not in opts_:
            opts_.append(d)
    if len(opts_) < 4:
        raise Retry
    rng.shuffle(opts_)
    ans = {LET[i]: str(opts_.index(c) + 1) for i, c in enumerate(chg)}
    mode = rng.choice(['eq', 'scheme'])
    who = 'восстановителя' if role == 'red' else 'окислителя'
    q = (f'Установите соответствие между {"уравнением" if mode == "eq" else "схемой"} реакции и изменением степени '
         f'окисления {who} в этой реакции: к каждой позиции, обозначенной буквой, подберите соответствующую позицию, '
         f'обозначенную цифрой. Запишите в таблицу выбранные цифры под соответствующими буквами.')
    e = '; '.join(f'{LET[i]}) {_EL_RU.get(redox_roles(r)[role][0], redox_roles(r)[role][0])}: {chg[i]}'
                  for i, r in enumerate(rs)) + '.'
    return card(pid, q, ans, e, k='match', o=match_opts([_show19(r, mode) for r in rs], opts_),
                p={'rids': [r['rid'] for r in rs], 'role': role, 'opts': opts_},
                eqs=[(r['lhs'], r['rhs'], *r['k']) for r in rs])


PROPS19 = ['только окислитель', 'только восстановитель', 'и окислитель, и восстановитель',
           'не проявляет окислительно-восстановительных свойств']


def _prop_el(r, el):
    L, Rr = set(), set()
    for f in r['lhs']:
        o = ox_of(f)
        if o is None:
            return None
        if el in o:
            L.add(o[el])
    for f in r['rhs']:
        o = ox_of(f)
        if o is None:
            return None
        if el in o:
            Rr.add(o[el])
    if not L:
        return None
    up = any(b > a for a in L for b in Rr if b not in L)
    down = any(b < a for a in L for b in Rr if b not in L)
    if up and down:
        return PROPS19[2]
    if up:
        return PROPS19[1]
    if down:
        return PROPS19[0]
    return PROPS19[3]


def _solve_19prop(p):
    ans = {}
    for i, rid in enumerate(p['rids']):
        pr = _prop_el(RX_BY_ID[rid], p['el'])
        hits = [str(j + 1) for j, t in enumerate(p['opts']) if t == pr]
        if len(hits) != 1:
            return {'err': rid}
        ans[LET[i]] = hits[0]
    return ans


@proto('ch-ege-19-property', 'ЕГЭ', 19, 'Уравнение/схема ↔ свойство элемента (окислитель, восстановитель, оба, не проявляет)',
       invariant='сравнить степени окисления выбранного элемента в реагентах и продуктах',
       varies='элемент (N, S, Cl, P, C, H, Fe, Cu, Mn, Cr, I, Br), три реакции с его участием, включая реакции без '
              'изменения его степени окисления и диспропорционирование',
       answer_rule='повышает степень окисления — восстановитель; понижает — окислитель; и то и другое — '
                   'диспропорционирование/сопропорционирование; не меняет — не проявляет',
       mistakes=['реакцию обмена с участием элемента считают ОВР', 'не замечают диспропорционирование (Cl₂ + KOH)',
                 'путают окислитель и восстановитель'],
       solve=_solve_19prop, kind='dict', kes=['1.12'],
       fidelity=FID(19, trap='одна из реакций — без изменения ст. ок. элемента, одна — диспропорционирование',
                    scale='3 реакции × 4 свойства — как демоверсия 2027 (свойство водорода) и ~25 заданий банка',
                    kes=['1.12'], fmt_='три цифры под буквами А–В'))
def g_19prop(rng):
    pid = 'ch-ege-19-property'
    el = rng.choice(['N', 'S', 'Cl', 'P', 'C', 'H', 'Fe', 'Cu', 'Mn', 'Cr', 'I', 'Br', 'O'])
    pool = [r for r in RX if any(el in els(f) for f in r['lhs']) and _prop_el(r, el) and len(r['lhs']) <= 3 and
            'электролиз' not in r['type'] and not (el in ('H', 'O') and _prop_el(r, el) == PROPS19[3] and
                                                     rng.random() < 0.3)]
    by = {}
    for r in pool:
        by.setdefault(_prop_el(r, el), []).append(r)
    kinds = [k for k in by if by[k]]
    if len(kinds) < 2:
        raise Retry
    chosen = rng.sample(kinds, min(3, len(kinds)))
    while len(chosen) < 3:
        chosen.append(rng.choice(kinds))
    rs = []
    for k in chosen:
        cand = [r for r in by[k] if r not in rs]
        if not cand:
            raise Retry
        rs.append(rng.choice(cand))
    rng.shuffle(rs)
    opts_ = PROPS19[:]
    ans = {LET[i]: str(opts_.index(_prop_el(r, el)) + 1) for i, r in enumerate(rs)}
    mode = rng.choice(['eq', 'scheme'])
    q = (f'Установите соответствие между {"уравнением" if mode == "eq" else "схемой"} реакции и свойством '
         f'{_EL_RU[el]}, которое этот элемент проявляет в этой реакции: к каждой позиции, обозначенной буквой, '
         f'подберите соответствующую позицию, обозначенную цифрой. Запишите в таблицу выбранные цифры под '
         f'соответствующими буквами.')
    e = '; '.join(f'{LET[i]}) {_prop_el(r, el)}' for i, r in enumerate(rs)) + '.'
    return card(pid, q, ans, e, k='match', o=match_opts([_show19(r, mode) for r in rs], opts_),
                p={'rids': [r['rid'] for r in rs], 'el': el, 'opts': opts_},
                eqs=[(r['lhs'], r['rhs'], *r['k']) for r in rs])


def _solve_19agent(p):
    ans = {}
    for i, rid in enumerate(p['rids']):
        r = RX_BY_ID[rid]
        # независимо: вещество реагентов, в котором элемент меняет степень окисления в нужную сторону
        found = []
        for f in dict.fromkeys(r['lhs']):
            of = ox_of(f) or {}
            for e, a in of.items():
                prod = {(ox_of(g) or {}).get(e) for g in r['rhs']} - {None}
                if p['role'] == 'red' and any(b > a for b in prod) or p['role'] == 'ox' and any(b < a for b in prod):
                    if not any((ox_of(g) or {}).get(e) == a for g in r['rhs']) or True:
                        found.append(f)
        found = list(dict.fromkeys(found))
        hits = [str(j + 1) for j, t in enumerate(p['opts']) if t in found]
        if len(hits) != 1:
            return {'err': rid}
        ans[LET[i]] = hits[0]
    return ans


@proto('ch-ege-19-agent', 'ЕГЭ', 19, 'Уравнение ОВР ↔ формула окислителя (восстановителя)',
       invariant='найти в реагентах вещество, содержащее элемент, который понижает (повышает) степень окисления',
       varies='три ОВР, роль, набор формул в правом столбце',
       answer_rule='каждой реакции — формула её окислителя (восстановителя)',
       mistakes=['называют восстановителем продукт', 'путают роли при участии азотсодержащих веществ'],
       solve=_solve_19agent, kind='dict', kes=['1.12'],
       fidelity=FID(19, trap='в правом столбце — вещества тех же реакций в другой роли',
                    scale='3 уравнения × 4 формулы — как задания банка «…и формулой восстановителя в этой реакции»',
                    kes=['1.12'], fmt_='три цифры под буквами А–В'))
def g_19agent(rng):
    pid = 'ch-ege-19-agent'
    role = rng.choice(['red', 'ox'])
    el = rng.choice(['N', 'S', 'Cl', 'C', 'H', 'Fe', 'Mn', 'Cr', 'I', None])
    theme = (lambda r: any(el in els(f) for f in r['lhs'])) if el else None
    rs = _pick19(rng, lambda r: agent_formula(r, role) and agent_formula(r, 'ox' if role == 'red' else 'red'), 3,
                 theme)
    ag = [agent_formula(r, role) for r in rs]
    if len(set(ag)) < 3:
        raise Retry
    other = [agent_formula(r, 'ox' if role == 'red' else 'red') for r in rs]
    opts_ = list(ag)
    for o in shuffled(rng, other):
        if o not in opts_:
            opts_.append(o)
            break
    if len(opts_) < 4:
        raise Retry
    # ни одна из «чужих» формул не должна быть агентом другой реакции той же роли
    for i, r in enumerate(rs):
        roles_here = [f for f in opts_ if f in r['lhs'] and f == agent_formula(r, role)]
        if len(roles_here) != 1:
            raise Retry
        for f in opts_:
            if f != ag[i] and f in r['lhs']:
                of = ox_of(f) or {}
                e, a, b = redox_roles(r)[role]
                if of.get(e) == a:
                    raise Retry
    rng.shuffle(opts_)
    ans = {LET[i]: str(opts_.index(a) + 1) for i, a in enumerate(ag)}
    who = 'восстановителя' if role == 'red' else 'окислителя'
    q = (f'Установите соответствие между уравнением реакции и формулой {who} в этой реакции: к каждой позиции, '
         f'обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой. Запишите в таблицу выбранные '
         f'цифры под соответствующими буквами.')
    e = '; '.join(f'{LET[i]}) {who[:-1] + "ь"} — {F(a)}' for i, a in enumerate(ag)) + '.'
    return card(pid, q, ans, e, k='match', o=match_opts([_show19(r, 'eq') for r in rs], [F(x) for x in opts_]),
                p={'rids': [r['rid'] for r in rs], 'role': role, 'opts': opts_},
                eqs=[(r['lhs'], r['rhs'], *r['k']) for r in rs])


IONS19 = [  # (запись, элемент, ст. ок.)
    ('S²⁻', 'S', -2), ('HS⁻', 'S', -2), ('SO₃²⁻', 'S', 4), ('HSO₃⁻', 'S', 4), ('SO₄²⁻', 'S', 6), ('NO₃⁻', 'N', 5),
    ('NO₂⁻', 'N', 3), ('NH₄⁺', 'N', -3), ('Cl⁻', 'Cl', -1), ('ClO⁻', 'Cl', 1), ('ClO₃⁻', 'Cl', 5),
    ('ClO₄⁻', 'Cl', 7), ('Br⁻', 'Br', -1), ('I⁻', 'I', -1), ('MnO₄⁻', 'Mn', 7), ('MnO₄²⁻', 'Mn', 6),
    ('Mn²⁺', 'Mn', 2), ('Cr₂O₇²⁻', 'Cr', 6), ('CrO₄²⁻', 'Cr', 6), ('Fe²⁺', 'Fe', 2), ('Cu²⁺', 'Cu', 2),
    ('Ag⁺', 'Ag', 1), ('H⁻', 'H', -1), ('H⁺', 'H', 1), ('Sn²⁺', 'Sn', 2), ('Cu⁺', 'Cu', 1), ('BrO₃⁻', 'Br', 5),
    ('IO₃⁻', 'I', 5), ('S₂O₃²⁻', 'S', 2), ('Hg²⁺', 'Hg', 2),
]
_OX_RANGE = {'S': (-2, 6), 'N': (-3, 5), 'Cl': (-1, 7), 'Br': (-1, 7), 'I': (-1, 7), 'Mn': (0, 7), 'Cr': (0, 6),
             'Fe': (0, 3), 'Cu': (0, 2), 'Ag': (0, 1), 'H': (-1, 1), 'Sn': (0, 4), 'Hg': (0, 2), 'Zn': (0, 2),
             'Al': (0, 3)}


def _ion_prop(el, v):
    lo, hi = _OX_RANGE[el]
    if lo < v < hi:
        return PROPS19[2]
    return PROPS19[0] if v == hi else PROPS19[1]


def _solve_19ion(p):
    table = {t: (e, v) for t, e, v in IONS19}
    ans = {}
    for i, t in enumerate(p['ions']):
        e, v = table[t]
        # другим путём: сравнение с высшей/низшей степенью окисления по группе ПСХЭ
        hi = {'S': 6, 'N': 5, 'Cl': 7, 'Br': 7, 'I': 7, 'Mn': 7, 'Cr': 6, 'Fe': 3, 'Cu': 2, 'Ag': 1, 'H': 1, 'Sn': 4,
              'Hg': 2, 'Zn': 2, 'Al': 3}[e]
        lo = {'S': -2, 'N': -3, 'Cl': -1, 'Br': -1, 'I': -1, 'H': -1}.get(e, 0)
        pr = 'только окислитель' if v >= hi else ('только восстановитель' if v <= lo else
                                                  'и окислитель, и восстановитель')
        hits = [str(j + 1) for j, t2 in enumerate(p['opts']) if t2 == pr]
        ans[LET[i]] = hits[0]
    return ans


@proto('ch-ege-19-ion', 'ЕГЭ', 19, 'Формула иона ↔ окислительно-восстановительные свойства, которые он может проявлять',
       invariant='сравнить степень окисления элемента в ионе с его высшей и низшей степенями окисления',
       varies='ионы серы, азота, галогенов, марганца, хрома, металлов',
       answer_rule='высшая ст. ок. — только окислитель; низшая — только восстановитель; промежуточная — оба',
       mistakes=['SO₃²⁻ и NO₂⁻ считают только восстановителями', 'NH₄⁺ считают окислителем',
                 'MnO₄²⁻ считают только окислителем'],
       solve=_solve_19ion, kind='dict', kes=['1.12'],
       fidelity=FID(19, trap='промежуточные степени окисления (SO₃²⁻, NO₂⁻, ClO⁻, MnO₄²⁻, Fe²⁺)',
                    scale='3–4 иона × 3 свойства — как задания банка «…формулой иона и '
                          'окислительно-восстановительными свойствами, которые он способен проявлять»', kes=['1.12'],
                    fmt_='цифры под буквами А–Г'))
def g_19ion(rng):
    pid = 'ch-ege-19-ion'
    k = rng.choice([3, 4])
    ions = rng.sample(IONS19, k)
    props = [_ion_prop(e, v) for _, e, v in ions]
    if len(set(props)) < 2:
        raise Retry
    opts_ = PROPS19[:3]
    ans = {LET[i]: str(opts_.index(pr) + 1) for i, pr in enumerate(props)}
    q = (rng.choice(['Установите соответствие между частицей и окислительно-восстановительной способностью, которую она '
                     'может проявлять в реакциях', 'Установите соответствие между ионом и его ролью в '
                     'окислительно-восстановительных реакциях']) +
         ': к каждой позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой. '
         'Запишите в таблицу выбранные цифры под соответствующими буквами.')
    e = '; '.join(f'{t}: {_EL_RU.get(el, el)} {_sgn(v)} — {pr}' for (t, el, v), pr in zip(ions, props)) + '.'
    return card(pid, q, ans, e, k='match', o=match_opts([t for t, _, _ in ions], opts_),
                p={'ions': [t for t, _, _ in ions], 'opts': opts_})


# ================================================================= 20. Электролиз

EL_TABLE = {(x['f'], x['medium']): x for x in I.ELECTROLYSIS}


def _el_rule(f, melt=False):
    """Независимое правило (для solve): продукты на инертных электродах."""
    s = SUBS[f]
    comp = parse_formula(f)
    if f in ('NaOH', 'KOH', 'LiOH', 'RbOH'):
        m, an = f[:-2], 'OH'
    elif s['cls'] == 'кислота':
        m, an = 'H', {'HCl': 'Cl', 'HBr': 'Br', 'HI': 'I', 'H2SO4': 'SO4', 'HNO3': 'NO3'}[f]
    elif f == 'Al2O3':
        return ['Al'], ['O2']
    else:
        io = s.get('ion')
        if io:
            m, an = CAT[io['cat']][3], io['an']
        else:
            m = [e for e in comp if e in METALS][0]
            an = 'Cl' if 'Cl' in comp else 'SO4'
    halo = {'Cl': 'Cl2', 'Br': 'Br2', 'I': 'I2', 'F': 'F2'}
    if melt:
        return [m], ([halo[an]] if an in halo else ['O2', 'H2O'])
    order = I.ACTIVITY
    if m == 'H':
        cat = ['H2']
    elif m in order and order.index(m) > order.index('H2'):
        cat = [m]
    elif m in order and order.index(m) > order.index('Al'):
        cat = [m, 'H2']
    else:
        cat = ['H2']
    if an in ('Cl', 'Br', 'I'):
        anode = [halo[an]]
    elif an == 'S':
        anode = ['S']
    elif an == 'CH3COO':
        anode = ['C2H6', 'CO2']
    else:
        anode = ['O2']
    return cat, anode


_CLS_WORD = {'H2': 'водород', 'O2': 'кислород', 'Cl2': 'галоген', 'Br2': 'галоген', 'I2': 'галоген', 'F2': 'галоген',
             'S': 'сера'}


def el_class(cat, anode):
    c = ['металл' if x not in ('H2',) else 'водород' for x in cat]
    if cat == ['H2']:
        c = ['водород']
    elif len(cat) == 2:
        c = ['металл', 'водород']
    a = [_CLS_WORD.get(x, x) for x in anode]
    words = c + a
    return words[0] + ' и ' + words[1] if len(words) == 2 else ', '.join(words[:-1]) + ' и ' + words[-1]


def _solve_20cls(p):
    ans = {}
    for i, f in enumerate(p['items']):
        cat, an = _el_rule(f)
        pr = el_class(cat, an)
        hits = [str(j + 1) for j, t in enumerate(p['opts']) if t == pr]
        if len(hits) != 1:
            return {'err': f}
        ans[LET[i]] = hits[0]
    return ans


SOL20 = [x['f'] for x in I.ELECTROLYSIS if x['medium'] == 'раствор' and x['anode'] != ['C2H6', 'CO2']]


@proto('ch-ege-20-classes', 'ЕГЭ', 20, 'Соль (название/формула) ↔ продукты электролиза водного раствора (металл/водород, '
                                       'кислород/галоген)',
       invariant='катод: до Al — водород, после H — металл, между ними — металл и водород; анод: бескислородный '
                 'анион (кроме F⁻) — его простое вещество, кислородсодержащий и F⁻ — кислород',
       varies='соли, щёлочи и кислоты разных металлов и анионов; число позиций 3–4',
       answer_rule='каждому веществу — пара (тройка) продуктов на инертных электродах',
       mistakes=['для солей Al, Mg пишут металл', 'для фторидов пишут фтор', 'для нитратов пишут NO₂',
                 'для металлов средней активности забывают водород'],
       solve=_solve_20cls, kind='dict', kes=['1.13'],
       fidelity=FID(20, trap='соли Al/Mg/щелочных металлов (водород), фториды и нитраты (кислород), соли Fe, Zn, Pb '
                             '(металл, водород и кислород)', scale='3–4 соли × 4–6 вариантов продуктов — как '
                             'демоверсия 2027 (нитрат ртути(II), нитрат рубидия, хлорид алюминия) и 82 задания банка',
                    kes=['1.13'], fmt_='цифры под буквами'))
def g_20cls(rng):
    pid = 'ch-ege-20-classes'
    k = rng.choice([3, 3, 4])
    items = rng.sample(SOL20, k)
    prods = [el_class(*_el_rule(f)) for f in items]
    base = ['металл и кислород', 'металл и галоген', 'водород и галоген', 'водород и кислород']
    extra = ['металл, водород и кислород', 'металл, водород и галоген', 'водород и сера']
    opts_ = list(base)
    for x in prods:
        if x not in opts_:
            opts_.append(x)
    for x in shuffled(rng, extra):
        if len(opts_) >= (4 if k == 3 else 6):
            break
        if x not in opts_:
            opts_.append(x)
    if len(set(prods)) < 2:
        raise Retry
    ans = {LET[i]: str(opts_.index(x) + 1) for i, x in enumerate(prods)}
    by_name = rng.random() < 0.5
    q = (f'Установите соответствие между {"солью" if by_name else "формулой вещества"} и продуктами электролиза '
         f'водного раствора {"этой соли" if by_name else "этого вещества"}, которые выделяются на инертных '
         f'электродах: к каждой позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой. '
         f'Запишите в таблицу выбранные цифры под соответствующими буквами.')
    left = [ru(f) if by_name else F(f) for f in items]
    e = '; '.join(f'{F(f)}: катод — {", ".join(F(x) for x in EL_TABLE[(f, "раствор")]["cathode"])}, анод — '
                  f'{", ".join(F(x) for x in EL_TABLE[(f, "раствор")]["anode"])}' for f in items) + '.'
    return card(pid, q, ans, e, k='match', o=match_opts(left, opts_), p={'items': items, 'opts': opts_})


def _prod_txt(cat, anode):
    return ', '.join(F(x) for x in cat + anode)


def _solve_20f(p):
    ans = {}
    for i, f in enumerate(p['items']):
        pr = _prod_txt(*_el_rule(f))
        hits = [str(j + 1) for j, t in enumerate(p['opts']) if t == pr]
        if len(hits) != 1:
            return {'err': f}
        ans[LET[i]] = hits[0]
    return ans


@proto('ch-ege-20-formulas', 'ЕГЭ', 20, 'Формула вещества ↔ конкретные продукты электролиза раствора',
       invariant='те же правила катода и анода, продукты — конкретные вещества',
       varies='соли, щёлочи, кислоты; дистракторы — NO₂, SO₂, металл вместо водорода и т. п.',
       answer_rule='каждой формуле — набор веществ, выделяющихся на катоде и аноде',
       mistakes=['для нитратов пишут NO₂, для сульфатов SO₂', 'для солей активных металлов пишут металл'],
       solve=_solve_20f, kind='dict', kes=['1.13'],
       fidelity=FID(20, trap='«продукты разложения аниона» (NO₂, SO₂) вместо кислорода; металл вместо водорода',
                    scale='3–4 формулы × 4–6 вариантов — как задания банка «ВЕЩЕСТВО — ПРОДУКТЫ ЭЛЕКТРОЛИЗА: '
                          'H₂, O₂ / Hg, O₂ / Hg, NO₂…»', kes=['1.13'], fmt_='цифры под буквами'))
def g_20f(rng):
    pid = 'ch-ege-20-formulas'
    k = rng.choice([3, 4])
    items = rng.sample(SOL20, k)
    true = [_prod_txt(*_el_rule(f)) for f in items]
    if len(set(true)) < k:
        raise Retry
    dis = []
    for f in items:
        cat, an = _el_rule(f)
        io = SUBS[f].get('ion') or {}
        m = CAT[io['cat']][3] if io.get('cat') in CAT else None
        if an == ['O2'] and io.get('an') == 'NO3':
            dis.append(_prod_txt(cat, ['NO2']))
        if an == ['O2'] and io.get('an') == 'SO4':
            dis.append(_prod_txt(cat, ['SO2']))
        if cat == ['H2'] and m and m not in ('N',):
            dis.append(_prod_txt([m], an))
        if cat != ['H2']:
            dis.append(_prod_txt(['H2'], an))
    opts_ = list(dict.fromkeys(true))
    for d in shuffled(rng, dis):
        if len(opts_) >= k + 1 + (1 if k == 4 else 0):
            break
        if d not in opts_:
            opts_.append(d)
    if len(opts_) < k + 1:
        raise Retry
    rng.shuffle(opts_)
    ans = {LET[i]: str(opts_.index(t) + 1) for i, t in enumerate(true)}
    q = (rng.choice(['Установите соответствие между формулой соли и веществами, выделяющимися на инертных электродах '
                     'при электролизе её водного раствора', 'Установите соответствие между формулой электролита и '
                     'продуктами, которые получаются на катоде и аноде (электроды инертные) при электролизе его '
                     'водного раствора']) +
         ': к каждой позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой. '
         'Запишите в таблицу выбранные цифры под соответствующими буквами.')
    e = '; '.join(f'{F(f)} → {t}' for f, t in zip(items, true)) + '.'
    return card(pid, q, ans, e, k='match', o=match_opts([F(f) for f in items], opts_), p={'items': items, 'opts': opts_})


METHODS20 = []   # (текст способа, electrolyte, medium)
for _x in I.ELECTROLYSIS:
    if _x['medium'] == 'раствор' and _x['anode'] != ['C2H6', 'CO2'] and SUBS[_x['f']]['cls'] == 'соль':
        METHODS20.append((f'водного раствора {F(_x["f"])}', _x['f'], 'раствор'))
    elif _x['medium'] == 'расплав':
        METHODS20.append((f'расплава {F(_x["f"])}', _x['f'], 'расплав'))
METHODS20.append(('раствора Al₂O₃ в расплавленном криолите', 'Al2O3', 'расплав'))
TARGETS20 = ['Na', 'K', 'Li', 'Ca', 'Mg', 'Ba', 'Al', 'F2', 'Cl2', 'Br2', 'I2', 'H2', 'O2', 'Cu', 'Ag', 'Hg']


def _method_products(f, medium):
    cat, an = _el_rule(f, melt=(medium == 'расплав'))
    return set(cat) | set(an)


def _solve_20m(p):
    ans = {}
    for i, t in enumerate(p['targets']):
        hits = [str(j + 1) for j, (txt, f, med) in enumerate(p['methods']) if t in _method_products(f, med)]
        if len(hits) != 1:
            return {'err': t}
        ans[LET[i]] = hits[0]
    return ans


@proto('ch-ege-20-obtain', 'ЕГЭ', 20, 'Вещество ↔ возможный способ его получения электролизом',
       invariant='понять, какие продукты дают электролиз расплава и раствора; активные металлы и фтор — только из '
                 'расплавов, алюминий — из раствора Al₂O₃ в криолите',
       varies='металлы, галогены, водород, кислород; способы — расплавы и растворы разных солей',
       answer_rule='каждому веществу — способ, при котором оно выделяется на электроде',
       mistakes=['активный металл получают электролизом водного раствора', 'фтор — из раствора фторида',
                 'алюминий — из водного раствора AlCl₃'],
       solve=_solve_20m, kind='dict', kes=['1.13'],
       fidelity=FID(20, trap='водные растворы солей активных металлов и фторидов дают водород и кислород',
                    scale='3–4 вещества × 4–5 способов — как демоверсия 2027 (алюминий, фтор, калий) и задания банка '
                          '«…и возможным способом его получения путём электролиза»', kes=['1.13'],
                    fmt_='цифры под буквами'))
def g_20m(rng):
    pid = 'ch-ege-20-obtain'
    k = rng.choice([3, 4])
    for _ in range(40):
        targets = rng.sample(TARGETS20, k)
        methods = []
        ok = True
        for t in targets:
            cands = [m for m in METHODS20 if t in _method_products(m[1], m[2])]
            if not cands:
                ok = False
                break
            methods.append(rng.choice(cands))
        if not ok:
            continue
        # дистракторы: «ловушки» — водные растворы солей тех же металлов/галогенов
        traps = [m for m in METHODS20 if m not in methods and any(
            (t in els(m[1]) or t[:-1] in els(m[1])) for t in targets)]
        others = [m for m in METHODS20 if m not in methods and m not in traps]
        n_opts = k + 1
        pool = shuffled(rng, traps)[:2] + shuffled(rng, others)
        for m in pool:
            if len(methods) >= n_opts:
                break
            if m not in methods:
                methods.append(m)
        rng.shuffle(methods)
        ans = {}
        for i, t in enumerate(targets):
            hits = [str(j + 1) for j, m in enumerate(methods) if t in _method_products(m[1], m[2])]
            if len(hits) != 1:
                ok = False
                break
            ans[LET[i]] = hits[0]
        if ok and len({m[0] for m in methods}) == len(methods):
            break
    else:
        raise Retry
    names = {'Na': 'натрий', 'K': 'калий', 'Li': 'литий', 'Ca': 'кальций', 'Mg': 'магний', 'Ba': 'барий',
             'Al': 'алюминий', 'F2': 'фтор', 'Cl2': 'хлор', 'Br2': 'бром', 'I2': 'иод', 'H2': 'водород',
             'O2': 'кислород', 'Cu': 'медь', 'Ag': 'серебро', 'Hg': 'ртуть'}
    q = (rng.choice(['Установите соответствие между простым веществом и электролизом, с помощью которого это вещество '
                     'можно получить', 'Установите соответствие между названием простого вещества и электролитом, '
                     'при электролизе которого на инертном электроде выделяется это вещество']) +
         ': к каждой позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой. '
         'Запишите в таблицу выбранные цифры под соответствующими буквами.')
    e = '; '.join(f'{names[t]} — электролиз {methods[int(ans[LET[i]]) - 1][0]}' for i, t in enumerate(targets)) + '.'
    return card(pid, q, ans, e, k='match', o=match_opts([names[t] for t in targets], [m[0] for m in methods]),
                p={'targets': targets, 'methods': [list(m) for m in methods]})


def _solve_20el(p):
    ans = {}
    for i, f in enumerate(p['items']):
        cat, an = _el_rule(f)
        pr = (cat if p['el'] == 'катод' else an)
        pr = pr[0] if len(pr) == 1 else None
        hits = [str(j + 1) for j, t in enumerate(p['opts']) if pr and t == pr]
        if len(hits) != 1:
            return {'err': f}
        ans[LET[i]] = hits[0]
    return ans


@proto('ch-ege-20-electrode', 'ЕГЭ', 20, 'Формула соли ↔ продукт на инертном аноде (катоде) при электролизе раствора',
       invariant='правило анода (или катода) для водного раствора',
       varies='электрод, 4 соли, 5–6 вариантов продукта',
       answer_rule='каждой соли — вещество, выделяющееся на указанном электроде',
       mistakes=['на аноде при электролизе фторида пишут F₂', 'на катоде при электролизе соли Mg пишут Mg'],
       solve=_solve_20el, kind='dict', kes=['1.13'],
       fidelity=FID(20, trap='фториды, нитраты, сульфаты (кислород на аноде), соли активных металлов (водород)',
                    scale='4 соли × 5–6 продуктов — задания банка прежних лет «…продуктом, образующимся на инертном '
                          'аноде»', kes=['1.13'], fmt_='четыре цифры под буквами А–Г'))
def g_20el(rng):
    pid = 'ch-ege-20-electrode'
    el = rng.choice(['анод', 'катод'])
    pool = [f for f in SOL20 if len(_el_rule(f)[0 if el == 'катод' else 1]) == 1]
    items = rng.sample(pool, 4)
    prods = [_el_rule(f)[0 if el == 'катод' else 1][0] for f in items]
    if len(set(prods)) < 2:
        raise Retry
    extra = ['H2', 'O2', 'Cl2', 'S', 'SO2', 'NO2', 'F2', 'Br2', 'Na', 'Cu'] if el == 'анод' else \
        ['H2', 'Cu', 'Ag', 'Hg', 'Na', 'K', 'Mg', 'Al', 'Ca', 'Ba']
    opts_ = list(dict.fromkeys(prods))
    for x in shuffled(rng, extra):
        if len(opts_) >= 5:
            break
        if x not in opts_:
            opts_.append(x)
    rng.shuffle(opts_)
    ans = {LET[i]: str(opts_.index(p) + 1) for i, p in enumerate(prods)}
    word = 'аноде' if el == 'анод' else 'катоде'
    q = (f'Установите соответствие между формулой соли и продуктом, образующимся на инертном {word} при электролизе '
         f'её водного раствора: к каждой позиции, обозначенной буквой, подберите соответствующую позицию, '
         f'обозначенную цифрой. Запишите в таблицу выбранные цифры под соответствующими буквами.')
    e = '; '.join(f'{F(f)} — {F(p)}' for f, p in zip(items, prods)) + '.'
    return card(pid, q, ans, e, k='match', o=match_opts([F(f) for f in items], [F(x) for x in opts_]),
                p={'items': items, 'opts': opts_, 'el': el})


# ================================================================= ионные уравнения

def _ion_label(formula, charge):
    q = abs(charge)
    sign = '+' if charge > 0 else '−'
    sup = (str(q) if q > 1 else '').translate(SUP) + ('⁺' if charge > 0 else '⁻')
    return pretty(formula) + sup


STRONG_DISS = {'HCl': [('H', 1, 1), ('Cl', -1, 1)], 'HBr': [('H', 1, 1), ('Br', -1, 1)],
               'HI': [('H', 1, 1), ('I', -1, 1)], 'HNO3': [('H', 1, 1), ('NO3', -1, 1)],
               'H2SO4': [('H', 1, 2), ('SO4', -2, 1)], 'HClO4': [('H', 1, 1), ('ClO4', -1, 1)],
               'NaOH': [('Na', 1, 1), ('OH', -1, 1)], 'KOH': [('K', 1, 1), ('OH', -1, 1)],
               'LiOH': [('Li', 1, 1), ('OH', -1, 1)], 'Ba(OH)2': [('Ba', 2, 1), ('OH', -1, 2)],
               'Ca(OH)2': [('Ca', 2, 1), ('OH', -1, 2)], 'Sr(OH)2': [('Sr', 2, 1), ('OH', -1, 2)],
               'RbOH': [('Rb', 1, 1), ('OH', -1, 1)], 'CsOH': [('Cs', 1, 1), ('OH', -1, 1)]}


def dissociate(f, form=None):
    """Ионы сильного электролита в растворе: [(формула, заряд, число)] или None (записывается молекулой)."""
    if form == 'конц.' or form == 'тв.':
        return None
    if f in STRONG_DISS:
        return STRONG_DISS[f]
    s = SUBS.get(f, {})
    io = s.get('ion')
    if not io or s.get('sol') != 'р' or s.get('cls') != 'соль':
        return None
    if io.get('cplx'):
        if f.startswith('('):   # [Cu(NH3)4]SO4 — не используем
            return None
        m = re.match(r'([A-Z][a-z]?)(\d*)\((.+)\)(\d*)$', f)
        if not m:
            return None
        cat, nc, an, na = m.group(1), int(m.group(2) or 1), m.group(3), int(m.group(4) or 1)
        cq = {'Na': 1, 'K': 1, 'Ba': 2, 'Li': 1}[cat]
        aq = -(cq * nc) // na
        return [(cat, cq, nc), ('[' + an + ']', aq, na)]
    ck, ak = io['cat'], io['an']
    cf, cq = I.CAT[ck][0], I.CAT[ck][1]
    af, aq = I.AN[ak][0], I.AN[ak][1]
    nc, na = io['n']
    if ak == 'HSO4':
        return [(cf, cq, nc), ('H', 1, na), ('SO4', -2, na)]
    return [(cf, cq, nc), (af, -aq, na)]


def ionic(r):
    """(полное, сокращённое) ионные уравнения: списки [(вид, коэф.)], вид = ('ion', формула, заряд) | ('mol', f)."""
    if not r.get('aq'):
        return None
    kl, kr = r['k']
    sides = []
    for fs, ks in ((r['lhs'], kl), (r['rhs'], kr)):
        c = Counter()
        for f, k in zip(fs, ks):
            d = dissociate(f, FORM_OF(r, f))
            if d is None:
                c[('mol', f, 0)] += k
            else:
                for fo, q, n in d:
                    c[('ion', fo, q)] += k * n
        sides.append(c)
    full = [dict(sides[0]), dict(sides[1])]
    L, Rr = Counter(sides[0]), Counter(sides[1])
    for key in list(L):
        if key in Rr:
            m = min(L[key], Rr[key])
            L[key] -= m
            Rr[key] -= m
    L = +L
    Rr = +Rr
    if not L or not Rr:
        return None
    g = 0
    for v in list(L.values()) + list(Rr.values()):
        g = math.gcd(g, v)
    net = [{k: v // g for k, v in L.items()}, {k: v // g for k, v in Rr.items()}]
    # проверка: атомы и заряд
    for eqn in (full, net):
        ch = [sum(k[2] * v for k, v in side.items()) for side in eqn]
        if ch[0] != ch[1]:
            return None
        at = []
        for side in eqn:
            c = Counter()
            for (kind, fo, q), v in side.items():
                for e, n in parse_formula(fo.strip('[]')).items():
                    c[e] += n * v
            at.append(c)
        if at[0] != at[1]:
            return None
    return full, net


def ion_text(side_pair):
    def t(side):
        out = []
        for (kind, fo, q), v in side.items():
            name = _ion_label(fo, q) if kind == 'ion' else F(fo)
            out.append((str(v) if v > 1 else '') + name)
        return ' + '.join(out)
    return t(side_pair[0]) + ' = ' + t(side_pair[1])


def net_key(r):
    x = ionic(r)
    if not x:
        return None
    net = x[1]
    return (frozenset(net[0].items()), frozenset(net[1].items()))


# ================================================================= наблюдения (6, 24)

_GEN_COLOR = {'белый': 'белого', 'чёрный': 'чёрного', 'голубой': 'голубого', 'бурый': 'бурого', 'жёлтый': 'жёлтого',
              'светло-жёлтый': 'светло-жёлтого', 'серо-зелёный': 'серо-зелёного', 'синий': 'синего',
              'кирпично-красный': 'кирпично-красного', 'зелёный': 'зелёного', 'тёмно-бурый': 'бурого',
              'красный': 'красного', 'телесный': 'телесного', 'желтовато-белый': 'белого', 'бледно-розовый': 'розового'}
_GAS_DESC = {'NO2': 'выделение бурого газа', 'H2S': 'выделение газа с запахом тухлых яиц',
             'SO2': 'выделение газа с резким запахом', 'NH3': 'выделение газа с резким запахом',
             'Cl2': 'выделение жёлто-зелёного газа', 'HCl': 'выделение газа с резким запахом'}


_CLASSIC_PREC = {'AgCl', 'AgBr', 'AgI', 'Ag3PO4', 'BaSO4', 'BaCO3', 'CaCO3', 'CuS', 'PbS', 'FeS', 'ZnS', 'Ag2S',
                 'Cu(OH)2', 'Fe(OH)3', 'Fe(OH)2', 'Al(OH)3', 'Zn(OH)2', 'Mg(OH)2', 'Cr(OH)3', 'H2SiO3', 'Ca3(PO4)2',
                 'BaSO3', 'PbI2', 'BaCrO4', '(CuOH)2CO3', 'KFe(Fe(CN)6)', 'S', 'CaSO3', 'Ag2O', 'PbSO4',
                 'Ba3(PO4)2', 'CaF2', 'Mn(OH)2', 'Ag2CO3', 'SrSO4', 'PbCrO4', 'Ag2CrO4', 'CuI', 'HgS', 'MgCO3',
                 'Mg3(PO4)2', 'FeCO3', 'PbCO3', 'ZnCO3', 'AlPO4', 'FePO4', 'Cu3(PO4)2', 'Zn3(PO4)2', 'CaSiO3',
                 'BaSiO3', 'MnS'}


def _prec_color(f):
    if f not in _CLASSIC_PREC:
        return None
    c = (SUBS[f].get('color') or 'белый').split(' (')[0].split(',')[0]
    if f == 'MnS':
        return 'телесного'
    return _GEN_COLOR.get(c)


def _obs_one(r, a, b):
    lhs = set(r['lhs'])
    prec = [x for x in r['rhs'] if x not in lhs and x != 'H2O' and SUBS.get(x, {}).get('sol') == 'н'
            and SUBS[x]['cls'] != 'простое вещество' or x == 'S' and x not in lhs]
    metal_dep = [x for x in r['rhs'] if x not in lhs and SUBS.get(x, {}).get('cls') == 'простое вещество' and
                 SUBS[x].get('sub') == 'металл']
    gases = [x for x in r['rhs'] if x not in lhs and _evolved(r, x)]
    solid_in = [x for x in (a, b) if x != 'H2O' and (SUBS[x].get('sol') == 'н' or SUBS[x]['cls'] == 'простое вещество'
                                                     and SUBS[x].get('sub') == 'металл') and x not in r['rhs']]
    sign = r.get('sign', '')
    out = []
    if any(SUBS.get(x, {}).get('sol') == 'м' for x in r['rhs'] if x not in lhs):
        return None
    if prec:
        cols = {_prec_color(x) for x in prec}
        if None in cols or len(cols) > 1:
            return None
        out.append(f'образование {cols.pop()} осадка')
    if metal_dep:
        return None
    if gases:
        g = gases[0]
        if len(gases) > 1:
            return None
        out.append(_GAS_DESC.get(g, 'выделение газа без цвета и запаха' if g not in ('NH3', 'H2S', 'SO2', 'NO2')
                   else 'выделение газа'))
    if solid_in:
        if not out or gases and not prec:
            out.insert(0, 'растворение осадка' if SUBS[solid_in[0]]['cls'] != 'простое вещество'
                       else 'растворение металла')
        else:
            return None
    if not out:
        if is_redox(r) and not sign:
            return None
        if 'обесцвеч' in sign:
            return 'обесцвечивание раствора'
        for key in ('становится', 'окраск', 'окраш', 'буреет', 'желтеет', 'синего раствора'):
            if key in sign:
                return sign.split(',')[0].split(' (')[0]
        return 'видимые признаки реакции отсутствуют'
    return ' и '.join(out) if len(out) <= 2 else None


def obs(a, la, b, lb):
    """Наблюдение при сливании (добавлении) b к a в растворе: строка-признак или None (неясно)."""
    v = reacts(a, la, b, lb)
    if v is False:
        return 'видимые признаки реакции отсутствуют'
    if v is not True:
        return None
    rs = [r for r in pos_rx(a, la, b, lb) if r.get('aq') and 'сплавл' not in r.get('cond', '')]
    if not rs:
        return None
    plain = [r for r in rs if not r.get('cond', '') or r.get('cond') in ('t', 'р-р')]
    if len(plain) == 1 and len(rs) > 1 and not any('избыток' in r.get('cond', '') for r in rs):
        rs = plain
    conds = {r.get('cond', '') for r in rs}
    if len(rs) == 2 and any('избыток' in c for c in conds) and any('недостаток' in c for c in conds):
        lack = next(r for r in rs if 'недостаток' in r.get('cond', ''))
        exc = next(r for r in rs if 'избыток' in r.get('cond', ''))
        o1 = _obs_one(lack, a, b)
        if o1 and o1.startswith('образование') and not any(SUBS.get(x, {}).get('sol') == 'н'
                                                             for x in exc['rhs'] if x not in exc['lhs']):
            return o1.replace(' осадка', ' осадка, растворяющегося в избытке реагента')
        return None
    if len(rs) != 1:
        return None
    return _obs_one(rs[0], a, b)


# ================================================================= 24. Качественные реакции (неорганика)

_OBS = {}


def obs_c(a, la, b, lb):
    k = (a, la, b, lb)
    if k not in _OBS:
        _OBS[k] = obs(a, la, b, lb)
    return _OBS[k]


U24 = [x for x in I.U if x in SUBS and x not in ('Au', 'Pt', 'Hg', 'N2', 'NO', 'N2O', 'CO', 'H2', 'O2', 'Si', 'C',
                                                   'P', 'S', 'SiO2', 'MnO2')]


def _lab24(f):
    return {'HNO3': 'разб.', 'H2SO4': 'разб.'}.get(f, '')


SIGN_PAIRS = []
for _k, _rs in PAIR.items():
    _k = list(_k)
    if len(_k) != 2 or not all(x in U24 for x in _k):
        continue
    _a, _b = _k
    _o = obs_c(_a, _lab24(_a), _b, _lab24(_b))
    if _o and _o != 'видимые признаки реакции отсутствуют' or _o and 'нейтрализации' in _rs[0]['type']:
        SIGN_PAIRS.append((_a, _b, _o))


def _pair_txt(a, b):
    def one(x):
        lab = _lab24(x)
        if not lab and SUBS[x].get('sol') == 'р' and SUBS[x]['cls'] in ('соль', 'основание', 'кислота') and \
                x not in ('HCl', 'HBr', 'HI'):
            lab = 'р-р'
        return FL(x, lab)
    return f'{one(a)} и {one(b)}'


def _solve_24s(p):
    ans = {}
    for i, (a, b) in enumerate(p['pairs']):
        # независимо: по продуктам реакции из базы (перебор всех реакций пары)
        o = obs(a, _lab24(a), b, _lab24(b))
        hits = [str(j + 1) for j, t in enumerate(p['opts']) if t == o]
        if len(hits) != 1:
            return {'err': a + b}
        ans[LET[i]] = hits[0]
    return ans


@proto('ch-ege-24-signs', 'ЕГЭ', 24, 'Реагирующие вещества ↔ признак реакции (неорганика)',
       invariant='по продуктам реакции определить видимый признак: осадок (его цвет), газ (цвет/запах), растворение '
                 'осадка, изменение окраски или отсутствие видимых признаков',
       varies='пары неорганических веществ: соли, кислоты, щёлочи, амфотерные гидроксиды, металлы',
       answer_rule='каждой паре — признак протекающей реакции',
       mistakes=['реакцию нейтрализации сопровождают «выделением газа»', 'забывают цвет осадка (Cu(OH)₂ — голубой, '
                 'Fe(OH)₃ — бурый, AgI — жёлтый)', 'амфотерный гидроксид в избытке щёлочи растворяется'],
       solve=_solve_24s, kind='dict', kes=['2.5'],
       fidelity=FID(24, trap='похожие признаки (белый/жёлтый осадок, газ без запаха/с запахом), реакции без видимых '
                             'признаков', scale='4 пары × 5 признаков — как задания банка «Установите соответствие между '
                             'реагирующими веществами и признаком протекающей между ними реакции» (неорганическая '
                             'часть)', kes=['2.5'], fmt_='четыре цифры под буквами А–Г'))
def g_24s(rng):
    pid = 'ch-ege-24-signs'
    for _ in range(30):
        picks = rng.sample(SIGN_PAIRS, 4)
        if len({o for _, _, o in picks}) >= 3 and len({frozenset((a, b)) for a, b, _ in picks}) == 4:
            break
    else:
        raise Retry
    opts_ = list(dict.fromkeys(o for _, _, o in picks))
    others = list(dict.fromkeys(o for _, _, o in SIGN_PAIRS if o not in opts_))
    rng.shuffle(others)
    while len(opts_) < 5 and others:
        opts_.append(others.pop())
    rng.shuffle(opts_)
    pairs = [(a, b) if rng.random() < 0.5 else (b, a) for a, b, _ in picks]
    ans = {LET[i]: str(opts_.index(o) + 1) for i, (_, _, o) in enumerate(picks)}
    q = ('Установите соответствие между реагирующими веществами и признаком протекающей между ними реакции: к каждой '
         'позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой. Запишите в таблицу '
         'выбранные цифры под соответствующими буквами.')
    ex = []
    for a, b in pairs:
        r = pos_rx(a, _lab24(a), b, _lab24(b))
        r = [x for x in r if x.get('aq')]
        plain = [x for x in r if not x.get('cond')] or r
        ex.append(eq_text(plain[0]['lhs'], plain[0]['rhs']))
    e = '; '.join(f'{LET[i]}) {ex[i]} — {picks[i][2]}' for i in range(4)) + '.'
    return card(pid, q, ans, e, k='match', o=match_opts([_pair_txt(a, b) for a, b in pairs], opts_),
                p={'pairs': [list(x) for x in pairs], 'opts': opts_})


R24 = ['KOH', 'NaOH', 'Ba(OH)2', 'AgNO3', 'BaCl2', 'Ba(NO3)2', 'HCl', 'H2SO4', 'HNO3', 'Na2CO3', 'K2CO3', 'NH3·H2O',
       'CuSO4', 'FeCl3', 'Na2S', 'KI', 'Cl2', 'Zn', 'Cu', 'KNO3', 'NaCl', 'Na2SO4', 'CH3COONa', 'KCl', 'Na3PO4', 'CO2',
       'Fe', 'Mg', 'Al', 'NaNO3', 'K3PO4', 'Pb(NO3)2', 'AlCl3', 'MgCl2']
S24 = [x for x in U24 if SUBS[x]['cls'] in ('соль', 'кислота', 'основание') and SUBS[x].get('sol') == 'р'
       or x in ('Zn', 'Fe', 'Cu', 'Mg', 'Al', 'Ag')]


def _dist(a, b, r):
    oa, ob = obs_c(a, _lab24(a), r, _lab24(r)), obs_c(b, _lab24(b), r, _lab24(r))
    if oa is None or ob is None:
        return None
    return oa != ob


def _share(a, b):
    ia, ib = SUBS[a].get('ion') or {}, SUBS[b].get('ion') or {}
    if ia and ib and (ia.get('cat') == ib.get('cat') or ia.get('an') == ib.get('an')):
        return True
    return SUBS[a]['cls'] == SUBS[b]['cls']


def _solve_24d(p):
    ans = {}
    for i, (a, b) in enumerate(p['pairs']):
        hits = []
        for j, r in enumerate(p['reag']):
            oa, ob = obs(a, _lab24(a), r, _lab24(r)), obs(b, _lab24(b), r, _lab24(r))
            if oa is not None and ob is not None and oa != ob:
                hits.append(str(j + 1))
        if len(hits) != 1:
            return {'err': a + b}
        ans[LET[i]] = hits[0]
    return ans


@proto('ch-ege-24-distinguish', 'ЕГЭ', 24, 'Два вещества ↔ реактив, с помощью которого их можно различить (неорганика)',
       invariant='для каждой пары найти реактив, дающий с веществами разные видимые признаки (осадок, газ, '
                 'растворение, окраска)', varies='пары солей с общим катионом/анионом, кислоты, щёлочи, металлы; пять '
                 'реактивов', answer_rule='каждой паре — реактив, который с одним веществом даёт признак, а с другим — '
                                          'другой признак или не реагирует',
       mistakes=['выбирают реактив, реагирующий с обоими веществами одинаково', 'не учитывают амфотерность '
                 '(ZnCl₂/MgCl₂ и избыток щёлочи)', 'путают качественные реакции на анионы'],
       solve=_solve_24d, kind='dict', kes=['2.5'],
       fidelity=FID(24, trap='«ложный» реактив реагирует с обоими веществами одинаково или не реагирует ни с одним',
                    scale='4 пары × 5 реактивов — как демоверсия 2027 (Zn и Fe, BaCl₂ и Ba(NO₃)₂, K₂SO₄ и MgSO₄, '
                          'HBr и HNO₃)', kes=['2.5'], fmt_='четыре цифры под буквами А–Г'))
def g_24d(rng):
    pid = 'ch-ege-24-distinguish'
    for _ in range(25):
        reag = rng.sample(R24, 5)
        cands = []
        for _ in range(60):
            a, b = rng.sample(S24, 2)
            if not _share(a, b) or a in reag or b in reag:
                continue
            d = [_dist(a, b, r) for r in reag]
            if None in d or sum(d) != 1:
                continue
            cands.append((a, b, d.index(True)))
        uniq = {}
        for a, b, j in cands:
            uniq.setdefault(frozenset((a, b)), (a, b, j))
        cands = list(uniq.values())
        if len(cands) >= 4 and len({j for _, _, j in cands}) >= 3:
            break
    else:
        raise Retry
    rng.shuffle(cands)
    chosen = []
    for c in cands:
        if len(chosen) < 4 and (sum(1 for x in chosen if x[2] == c[2]) < 2):
            chosen.append(c)
    if len(chosen) < 4:
        raise Retry
    ans = {LET[i]: str(j + 1) for i, (_, _, j) in enumerate(chosen)}
    q = ('Установите соответствие между двумя веществами и реактивом, с помощью которого можно различить эти '
         'вещества: к каждой позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой. '
         'Запишите в таблицу выбранные цифры под соответствующими буквами.')
    lab = lambda x: FL(x, _lab24(x) or ('р-р' if SUBS[x].get('sol') == 'р' and SUBS[x]['cls'] != 'простое вещество'
                                        else ''))
    ex = []
    for a, b, j in chosen:
        r = reag[j]
        ex.append(f'{F(a)} с {F(r)}: {obs_c(a, _lab24(a), r, _lab24(r))}; {F(b)}: {obs_c(b, _lab24(b), r, _lab24(r))}')
    e = '; '.join(f'{LET[i]}) {x}' for i, x in enumerate(ex)) + '.'
    return card(pid, q, ans, e, k='match', o=match_opts([f'{lab(a)} и {lab(b)}' for a, b, _ in chosen],
                                                        [lab(r) for r in reag]),
                p={'pairs': [[a, b] for a, b, _ in chosen], 'reag': reag})


# ================================================================= 6. «Две пробирки»: признаки реакций

def cat6(a, la, b, lb):
    v = reacts(a, la, b, lb)
    if v is False:
        return 'нет реакции'
    if v is not True:
        return None
    o = obs_c(a, la, b, lb)
    if o is None:
        return None
    if o.startswith('растворение'):
        return 'растворение и газ' if 'газа' in o else 'растворение'
    if o.startswith('образование') and 'газа' in o:
        return 'осадок и газ'
    if o.startswith('образование'):
        return 'осадок'
    if o.startswith('выделение'):
        return 'газ'
    if o.startswith('видимые'):
        return 'без видимых признаков'
    return 'окраска'


_OUT6 = {'осадок': ['выпал осадок', 'наблюдали образование осадка'],
         'газ': ['выделился газ', 'наблюдали выделение газа'],
         'растворение': ['наблюдали растворение осадка'],
         'без видимых признаков': ['протекала реакция, которая не сопровождалась видимыми признаками'],
         'осадок и газ': ['выпал осадок и выделился газ']}
S6 = [x for x in U24 if SUBS[x].get('sol') == 'р' and SUBS[x]['cls'] in ('соль', 'кислота', 'основание')]
P6 = [x for x in U24 if SUBS[x]['cls'] in ('соль', 'кислота', 'основание', 'оксид', 'амфотерный гидроксид')
      and x != 'H2O']
PREC6 = ['Zn(OH)2', 'Al(OH)3', 'Cu(OH)2', 'Fe(OH)3', 'Mg(OH)2', 'CaCO3', 'BaCO3', 'Cr(OH)3', 'Fe(OH)2']


def _solve_6k(p):
    S = p['S']
    ans = {}
    for letter, want in (('X', p['c1']), ('Y', p['c2'])):
        hits = [str(j + 1) for j, o in enumerate(p['opts']) if cat6(S, _lab24(S), o, _lab24(o)) == want]
        if len(hits) != 1:
            return {'err': letter}
        ans[letter] = hits[0]
    return ans


@proto('ch-ege-06-two-tubes', 'ЕГЭ', 6, 'Две пробирки с раствором (осадком) вещества: какие X и Y дали указанные признаки',
       invariant='для каждого вещества перечня предсказать результат реакции с исходным веществом (осадок, газ, '
                 'растворение осадка, реакция без видимых признаков, нет реакции)',
       varies='исходное вещество (соль, кислота, щёлочь, осадок гидроксида/карбоната), пять реагентов, пара признаков',
       answer_rule='X — единственное вещество перечня, дающее первый признак; Y — второй',
       mistakes=['считают, что любая реакция обмена даёт осадок', 'не учитывают растворимость продуктов по таблице',
                 'амфотерный гидроксид растворяется и в кислоте, и в щёлочи'],
       solve=lambda p: _solve_6k_roles(p), kind='dict', kes=['2.2', '2.3', '1.9'],
       fidelity=FID(6, trap='в перечне есть вещества, реагирующие без видимых признаков или дающие другой признак',
                    scale='исходное вещество + 5 реагентов, две буквы — как демоверсия 2027 (сульфид натрия: осадок/газ) '
                          'и ~74 задания банка (КЭС 1.9, 2.2, 2.3)', kes=['2.2', '2.3', '1.9'],
                    fmt_='две цифры под буквами X, Y',
                    style='«Даны две пробирки с раствором… В одну из них добавили раствор вещества X, а в другую – '
                          'раствор вещества Y… Из предложенного перечня выберите вещества X и Y…»'))
def g_6k(rng):
    pid = 'ch-ege-06-two-tubes'
    prec = rng.random() < 0.25
    S = rng.choice(PREC6 if prec else S6)
    table = {}
    for o in P6:
        if o == S:
            continue
        c = cat6(S, _lab24(S), o, _lab24(o))
        if c:
            table[o] = c
    by = {}
    for o, c in table.items():
        by.setdefault(c, []).append(o)
    wanted = [c for c in by if c in _OUT6 and c != 'нет реакции']
    if len(wanted) < 2 and not (prec and len(by.get('растворение', [])) >= 2):
        raise Retry
    if prec and len(by.get('растворение', [])) >= 2 and rng.random() < 0.6:
        c1 = c2 = 'растворение'
        X, Y = rng.sample(by['растворение'], 2)
        # X — кислота, Y — щёлочь/иной сильный электролит
        if SUBS[X]['cls'] != 'кислота':
            X, Y = Y, X
        if SUBS[X]['cls'] != 'кислота' or SUBS[Y]['cls'] == 'кислота':
            raise Retry
        others = [o for o, c in table.items() if c != 'растворение' and o not in (X, Y)]
        if len(others) < 3:
            raise Retry
        items = shuffled(rng, [X, Y] + rng.sample(others, 3))
        ans = {'X': str(items.index(X) + 1), 'Y': str(items.index(Y) + 1)}
        q = (f'Даны две пробирки с осадком {gen(S)}. В одну из них добавили раствор кислоты X, а в другую – раствор '
             f'вещества Y, не являющегося кислотой. В результате в каждой из пробирок наблюдали растворение осадка. '
             f'Из предложенного перечня выберите вещества X и Y, которые могут вступать в описанные реакции. '
             f'Запишите в таблицу номера выбранных веществ под соответствующими буквами.')
        p = {'S': S, 'c1': 'растворение', 'c2': 'растворение', 'opts': items, 'roles': True}
    else:
        if len(wanted) < 2:
            raise Retry
        c1, c2 = rng.sample(wanted, 2)
        X, Y = rng.choice(by[c1]), rng.choice(by[c2])
        others = [o for o, c in table.items() if c not in (c1, c2)]
        if len(others) < 3:
            raise Retry
        items = shuffled(rng, [X, Y] + rng.sample(others, 3))
        ans = {'X': str(items.index(X) + 1), 'Y': str(items.index(Y) + 1)}
        what = 'осадком' if prec else 'раствором'
        q = (f'Даны две пробирки с {what} {gen(S)}. В одну из них добавили раствор вещества X, а в другую – '
             f'раствор вещества Y. В результате в пробирке с веществом X {rng.choice(_OUT6[c1])}, а в пробирке с '
             f'веществом Y {rng.choice(_OUT6[c2])}. Из предложенного перечня выберите вещества X и Y, которые могут '
             f'вступать в описанные реакции. Запишите в таблицу номера выбранных веществ под соответствующими буквами.')
        p = {'S': S, 'c1': c1, 'c2': c2, 'opts': items}
    by_name = rng.random() < 0.6
    txt = [ru(x) if by_name else F(x) for x in items]
    rx = lambda o: [r for r in pos_rx(S, _lab24(S), o, _lab24(o)) if r.get('aq')][0]
    e = f'X: {eq_text(rx(X)["lhs"], rx(X)["rhs"])}; Y: {eq_text(rx(Y)["lhs"], rx(Y)["rhs"])}.'
    return card(pid, q, ans, e, k='match', o=match_opts(['X', 'Y'], txt, lids='XY'), p=p)


def _solve_6k_roles(p):
    if p.get('roles'):
        S = p['S']
        xs = [str(j + 1) for j, o in enumerate(p['opts']) if SUBS[o]['cls'] == 'кислота' and
              cat6(S, _lab24(S), o, _lab24(o)) == 'растворение']
        ys = [str(j + 1) for j, o in enumerate(p['opts']) if SUBS[o]['cls'] != 'кислота' and
              cat6(S, _lab24(S), o, _lab24(o)) == 'растворение']
        if len(xs) != 1 or len(ys) != 1:
            return {'err': 1}
        return {'X': xs[0], 'Y': ys[0]}
    return _solve_6k(p)


def _solve_6u(p):
    R1 = p['R1']
    good = []
    for x in p['opts']:
        if cat6(x, _lab24(x), R1, _lab24(R1)) != p['c1']:
            continue
        for y in p['opts']:
            if y != x and cat6(x, _lab24(x), y, _lab24(y)) == p['c2']:
                good.append((x, y))
    if len(good) != 1:
        return {'err': len(good)}
    x, y = good[0]
    return {'X': str(p['opts'].index(x) + 1), 'Y': str(p['opts'].index(y) + 1)}


@proto('ch-ege-06-unknown', 'ЕГЭ', 6, 'Две пробирки с раствором неизвестного вещества X: реакция с известным реагентом и с Y',
       invariant='подобрать вещество X по признаку реакции с названным реагентом и вещество Y по второму признаку',
       varies='известный реагент (хлорид бария, гидроксид калия, соляная кислота, нитрат серебра…), пара признаков',
       answer_rule='единственная пара (X, Y) из перечня, для которой выполняются оба описанных наблюдения',
       mistakes=['проверяют только одну пробирку', 'не учитывают, что X должен реагировать и с реагентом, и с Y'],
       solve=_solve_6u, kind='dict', kes=['2.2', '2.3', '1.9'],
       fidelity=FID(6, trap='несколько веществ дают первый признак, но только одно из них реагирует со вторым '
                             'нужным образом', scale='как задания банка «Даны две пробирки с раствором вещества X. В одну '
                             'из них добавили раствор хлорида бария…»', kes=['2.2', '2.3', '1.9'],
                    fmt_='две цифры под буквами X, Y'))
def g_6u(rng):
    pid = 'ch-ege-06-unknown'
    R1 = rng.choice(['BaCl2', 'KOH', 'NaOH', 'HCl', 'AgNO3', 'H2SO4', 'Ba(OH)2', 'Na2CO3', 'NH3·H2O', 'K3PO4'])
    for _ in range(30):
        items = rng.sample([x for x in S6 if x != R1], 5)
        c1s = {x: cat6(x, _lab24(x), R1, _lab24(R1)) for x in items}
        if None in c1s.values():
            continue
        cands = [x for x in items if c1s[x] in ('осадок', 'газ')]
        if not cands:
            continue
        X = rng.choice(cands)
        c1 = c1s[X]
        pairs = {}
        ok = True
        for x in items:
            if c1s[x] != c1:
                continue
            for y in items:
                if y == x:
                    continue
                c = cat6(x, _lab24(x), y, _lab24(y))
                if c is None:
                    ok = False
                pairs[(x, y)] = c
        if not ok:
            continue
        c2s = [c for (x, y), c in pairs.items() if x == X and c in ('осадок', 'газ', 'без видимых признаков')]
        if not c2s:
            continue
        c2 = rng.choice(c2s)
        good = [k for k, c in pairs.items() if c == c2]
        if len(good) == 1:
            X, Y = good[0]
            break
    else:
        raise Retry
    ans = {'X': str(items.index(X) + 1), 'Y': str(items.index(Y) + 1)}
    q = (f'Даны две пробирки с раствором вещества X. В одну из них добавили раствор {gen(R1)}, при этом '
         f'{rng.choice(_OUT6[c1])}. В другую пробирку добавили раствор вещества Y, при этом '
         f'{rng.choice(_OUT6[c2])}. Из предложенного перечня выберите вещества X и Y, которые могут вступать в '
         f'описанные реакции. Запишите в таблицу номера выбранных веществ под соответствующими буквами.')
    q = q.replace('при этом протекала', 'при этом протекала')
    by_name = rng.random() < 0.6
    txt = [ru(x) if by_name else F(x) for x in items]
    rx = lambda a, b: [r for r in pos_rx(a, _lab24(a), b, _lab24(b)) if r.get('aq')][0]
    e = f'{eq_text(rx(X, R1)["lhs"], rx(X, R1)["rhs"])}; {eq_text(rx(X, Y)["lhs"], rx(X, Y)["rhs"])}.'
    return card(pid, q, ans, e, k='match', o=match_opts(['X', 'Y'], txt, lids='XY'),
                p={'R1': R1, 'c1': c1, 'c2': c2, 'opts': items})


_ROLE6 = {'соль': 'соли', 'кислота': 'кислоты', 'основание': 'основания'}


def _role6(f):
    c = SUBS[f]['cls']
    if f in I.ALKALIS:
        return 'щёлочи'
    return _ROLE6.get(c)


def _solve_6i(p):
    target = (frozenset(tuple(x) for x in p['net'][0]), frozenset(tuple(x) for x in p['net'][1]))
    good = []
    for x in p['opts']:
        for y in p['opts']:
            if x == y or _role6(x) != p['rx'] or _role6(y) != p['ry']:
                continue
            for r in pos_rx(x, _lab24(x), y, _lab24(y)):
                nk = net_key(r)
                if nk and (frozenset((k, v) for k, v in nk[0]), frozenset((k, v) for k, v in nk[1])) == target:
                    good.append((x, y))
    good = list(dict.fromkeys(good))
    if len(good) != 1:
        return {'err': len(good)}
    x, y = good[0]
    return {'X': str(p['opts'].index(x) + 1), 'Y': str(p['opts'].index(y) + 1)}


IONIC6 = [r for r in RX if r.get('aq') and not is_redox(r) and net_key(r) and len(set(r['lhs']) - {'H2O'}) == 2]


@proto('ch-ege-06-ionic', 'ЕГЭ', 6, 'Вещества X и Y по сокращённому ионному уравнению их реакции',
       invariant='по сокращённому ионному уравнению восстановить сильные электролиты, дающие эти ионы, и проверить, '
                 'что остальные ионы — «зрители»',
       varies='ионное уравнение (осадок, газ, вода, кислая соль, комплекс), классы X и Y, пять веществ',
       answer_rule='X и Y — растворимые сильные электролиты, при сливании которых остаётся именно это уравнение',
       mistakes=['берут нерастворимое вещество или слабый электролит как источник иона',
                 'не учитывают второй осадок (Ba(OH)₂ + CuSO₄)', 'путают роли X (соль) и Y (кислота)'],
       solve=_solve_6i, kind='dict', kes=['1.9', '2.2', '2.3'],
       fidelity=FID(6, trap='вещество, дающее нужный ион, но образующее второй осадок/газ или являющееся слабым '
                             'электролитом', scale='как задания банка «…произошла реакция, которую описывает сокращённое '
                             'ионное уравнение H₂PO₄⁻ + 2OH⁻ = PO₄³⁻ + 2H₂O…»', kes=['1.9', '2.2', '2.3'],
                    fmt_='две цифры под буквами X, Y'))
def g_6i(rng):
    pid = 'ch-ege-06-ionic'
    r = rng.choice(IONIC6)
    L = [x for x in dict.fromkeys(r['lhs']) if x != 'H2O']
    X, Y = L if rng.random() < 0.5 else L[::-1]
    rx_, ry_ = _role6(X), _role6(Y)
    if not rx_ or not ry_ or rx_ == ry_ or FORM_OF(r, X) == 'конц.' or FORM_OF(r, Y) == 'конц.':
        raise Retry
    if len(pos_rx(X, _lab24(X), Y, _lab24(Y))) != 1:
        raise Retry
    nk = net_key(r)
    pool = [x for x in S6 + ['H3PO4', 'CH3COOH', 'H2S', 'NH3·H2O', 'CaCO3', 'Cu(OH)2', 'Fe(OH)3', 'BaSO4']
            if x in SUBS and x not in (X, Y)]
    same_role = [x for x in pool if _role6(x) in (rx_, ry_)]
    for _ in range(40):
        dis = rng.sample(same_role, 3)
        items = shuffled(rng, [X, Y] + dis)
        good, bad = [], False
        for x in items:
            for y in items:
                if x == y or _role6(x) != rx_ or _role6(y) != ry_:
                    continue
                v = reacts(x, _lab24(x), y, _lab24(y))
                if v is None:
                    bad = True
                for rr in pos_rx(x, _lab24(x), y, _lab24(y)):
                    if net_key(rr) == nk:
                        good.append((x, y))
        if not bad and list(dict.fromkeys(good)) == [(X, Y)]:
            break
    else:
        raise Retry
    full, net = ionic(r)
    ans = {'X': str(items.index(X) + 1), 'Y': str(items.index(Y) + 1)}
    q = (f'В пробирку с раствором {rx_} X добавили раствор {ry_} Y. В результате произошла реакция, которую описывает '
         f'сокращённое ионное уравнение {ion_text(net)}. Из предложенного перечня выберите вещества X и Y, которые '
         f'могут вступать в описанную реакцию. Запишите в таблицу номера выбранных веществ под соответствующими '
         f'буквами.')
    by_name = rng.random() < 0.6
    txt = [ru(x) if by_name else F(x) for x in items]
    e = f'{eq_text(r["lhs"], r["rhs"])}; полное ионное: {ion_text(full)}.'
    netj = [[list(k) + [v] for k, v in side.items()] for side in net]
    return card(pid, q, ans, e, k='match', o=match_opts(['X', 'Y'], txt, lids='XY'),
                p={'net': [[[tuple(k), v] for k, v in side.items()] for side in net], 'rx': rx_, 'ry': ry_,
                   'opts': items}, eqs=[(r['lhs'], r['rhs'], *r['k'])])


# ================================================================= 30. Реакции ионного обмена (из перечня)

EXCH30 = [r for r in RX if r.get('aq') and not is_redox(r) and len(set(r['lhs']) - {'H2O'}) == 2 and net_key(r)
          and not any(FORM_OF(r, x) == 'конц.' for x in r['lhs']) and 'совместный гидролиз' not in r.get('tags', [])]


def cond30(r):
    """Набор признаков реакции ионного обмена: осадок, газ, слабый электролит без газа и осадка."""
    lhs = set(r['lhs'])
    prod = [x for x in r['rhs'] if x not in lhs]
    prec = any(SUBS.get(x, {}).get('sol') == 'н' for x in prod)
    gas = any(_evolved(r, x) for x in prod)
    weak = any(x == 'H2O' or x in ('CH3COOH', 'HNO2', 'HF', 'NH3·H2O', 'H3PO4', 'H2S') for x in r['rhs'] if x not in lhs)
    acid_salt = any(SUBS.get(x, {}).get('sub') == 'кислая соль' for x in r['rhs'] if x not in lhs)
    out = set()
    if prec:
        out.add('осадок')
    if gas:
        out.add('газ')
    if (weak or acid_salt) and not prec and not gas:
        out.add('слабый')
    return out


_C30 = {'осадок': 'образованием осадка', 'газ': 'выделением газа',
        'слабый': 'образованием слабого электролита, а выделения газа и образования осадка не происходит'}
POOL30 = [x for x in S6 + ['NH3·H2O', 'CH3COOH', 'H3PO4', 'H2S', 'NaHCO3', 'KHSO4', 'NaH2PO4', 'Na2HPO4',
                           'KHCO3', 'NaHSO4', 'CaCO3', 'Cu(OH)2', 'Fe(OH)3', 'Mg(OH)2', 'Al(OH)3', 'Zn(OH)2']
          if x in SUBS]
POOL30 = list(dict.fromkeys(POOL30))


def _pairs30(items):
    res = {}
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            v = reacts(a, _lab24(a), b, _lab24(b))
            rs = [r for r in pos_rx(a, _lab24(a), b, _lab24(b)) if r in EXCH30]
            res[(a, b)] = (v, rs)
    return res


def _solve_30c(p):
    items = p['items']
    want = p['cond']
    good = set()
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            for r in RX:
                if set(r['lhs']) - {'H2O'} == {a, b} and r in EXCH30 and want in cond30(r):
                    good.add((a, b))
    if len(good) != 1:
        return ['err']
    a, b = good.pop()
    return sorted([str(items.index(a) + 1), str(items.index(b) + 1)])


LIST_HEAD = 'Для выполнения задания используйте следующий перечень веществ: {}. Допустимо использование водных ' \
            'растворов веществ.'


@proto('ch-ege-30-choose', 'ЕГЭ', 30, 'Перечень из шести веществ: выбрать пару для реакции ионного обмена с заданным признаком',
       invariant='перебрать пары веществ перечня, оставить реакции ионного обмена и выбрать ту, что даёт требуемый '
                 'признак (осадок, газ, слабый электролит без газа и осадка)',
       varies='перечень из шести веществ (соли, кислоты, щёлочи, кислые соли), требуемый признак',
       answer_rule='два номера веществ, реакция ионного обмена между которыми соответствует условию; в КИМ далее '
                   'записывают молекулярное, полное и сокращённое ионные уравнения',
       mistakes=['выбирают пару, где идёт ОВР, а не обмен', 'выбирают пару без признаков реакции обмена',
                 'не замечают, что вместе с водой выделяется газ'],
       solve=_solve_30c, kind='dict', kes=['1.9'],
       fidelity=FID(30, trap='в перечне несколько возможных реакций обмена, но условию отвечает одна',
                    scale='шесть веществ, как в демоверсии 2027 (нитрит калия, сульфит калия, дихромат калия, серная '
                          'кислота, иодид калия, гидросульфат аммония) и 69 заданиях банка',
                    kes=['1.9'], fmt_='в КИМ — развёрнутый ответ; в тренажёре — два номера веществ',
                    style='«Из предложенного перечня выберите два вещества, реакция ионного обмена между которыми…»'))
def g_30c(rng):
    pid = 'ch-ege-30-choose'
    r = rng.choice(EXCH30)
    a, b = [x for x in dict.fromkeys(r['lhs']) if x != 'H2O']
    cs = cond30(r)
    if not cs or a not in POOL30 and b not in POOL30:
        raise Retry
    want = rng.choice(sorted(cs))
    for _ in range(40):
        others = rng.sample([x for x in POOL30 if x not in (a, b)], 4)
        items = shuffled(rng, [a, b] + others)
        pr = _pairs30(items)
        if any(v is None for v, _ in pr.values()):
            continue
        good = [k for k, (v, rs) in pr.items() if any(want in cond30(x) for x in rs)]
        n_exch = sum(1 for v, rs in pr.values() if rs)
        if good == [(x, y) for x, y in pr if {x, y} == {a, b}] and n_exch >= 2:
            break
    else:
        raise Retry
    ans = sorted([str(items.index(a) + 1), str(items.index(b) + 1)])
    names = [ru(x) for x in items]
    q = (LIST_HEAD.format(', '.join(names)) + f' Из предложенного перечня выберите два вещества, реакция ионного '
         f'обмена между которыми протекает с {_C30[want]}. Запишите номера выбранных веществ.')
    full, net = ionic(r)
    e = (f'{eq_text(r["lhs"], r["rhs"])}; полное ионное: {ion_text(full)}; сокращённое: {ion_text(net)}.')
    return card(pid, q, ans, e, k='many', o=opts(names, ids='123456'), p={'items': items, 'cond': want},
                eqs=[(r['lhs'], r['rhs'], *r['k'])])


def _net_variants(r, rng):
    """Неверные «сокращённые» уравнения: ионы вместо осадка/слабого электролита, не та стехиометрия."""
    full, net = ionic(r)
    L, Rr = dict(net[0]), dict(net[1])
    out = []
    # 1) молекула реагента записана ионами (если это нерастворимое/слабое вещество)
    for (kind, fo, q), v in list(L.items()):
        if kind == 'mol' and fo in SUBS:
            d = STRONG_DISS.get(fo)
            io = SUBS[fo].get('ion')
            if io and not io.get('cplx'):
                cf, cq = I.CAT[io['cat']][0], I.CAT[io['cat']][1]
                af, aq = I.AN[io['an']][0], I.AN[io['an']][1]
                nc, na = io['n']
                L2 = {k: x for k, x in L.items() if k != (kind, fo, q)}
                L2[('ion', cf, cq)] = L2.get(('ion', cf, cq), 0) + nc * v
                L2[('ion', af, -aq)] = L2.get(('ion', af, -aq), 0) + na * v
                out.append((L2, Rr))
    # 2) неверный коэффициент у первого иона
    for key in list(L)[:2]:
        if L[key] == 1:
            L2 = dict(L)
            L2[key] = 2
            out.append((L2, Rr))
        else:
            L2 = dict(L)
            L2[key] = 1
            out.append((L2, Rr))
    # 3) продукт-осадок записан ионами (реакция «не идёт»)
    for (kind, fo, q), v in list(Rr.items()):
        if kind == 'mol' and fo not in ('H2O',) and fo in SUBS and SUBS[fo].get('sol') == 'н':
            out.append((L, {('mol', 'H2O', 0): 1} if False else {k: x for k, x in Rr.items() if k != (kind, fo, q)}
                        | {('ion', fo, 0): v}))
    # 4) газ + вода записаны кислотой
    if ('mol', 'CO2', 0) in Rr and ('mol', 'H2O', 0) in Rr:
        R2 = {k: x for k, x in Rr.items() if k not in (('mol', 'CO2', 0), ('mol', 'H2O', 0))}
        R2[('mol', 'H2CO3', 0)] = Rr[('mol', 'CO2', 0)]
        out.append((L, R2))
    if ('mol', 'SO2', 0) in Rr and ('mol', 'H2O', 0) in Rr:
        R2 = {k: x for k, x in Rr.items() if k not in (('mol', 'SO2', 0), ('mol', 'H2O', 0))}
        R2[('mol', 'H2SO3', 0)] = Rr[('mol', 'SO2', 0)]
        out.append((L, R2))
    rng.shuffle(out)
    return [x for x in out if all(k[2] != 0 or k[0] == 'mol' for side in x for k in side)]


def _solve_30n(p):
    r = RX_BY_ID[p['rid']]
    x = ionic(r)
    t = ion_text(x[1])
    hits = [str(i + 1) for i, o in enumerate(p['opts']) if o == t]
    return hits[0] if len(hits) == 1 else 'err'


@proto('ch-ege-30-net-ionic', 'ЕГЭ', 30, 'Сокращённое ионное уравнение реакции ионного обмена между растворами двух веществ',
       invariant='записать сильные растворимые электролиты ионами, осадки, газы, слабые электролиты — молекулами, '
                 'сократить ионы-«зрители» и общий множитель',
       varies='пары веществ (соли, кислоты, щёлочи, кислые соли, нерастворимые основания и карбонаты)',
       answer_rule='одно верное сокращённое ионное уравнение из четырёх',
       mistakes=['CaCO₃, Cu(OH)₂, CH₃COOH записывают ионами', 'не сокращают коэффициенты',
                 'пишут H₂CO₃ вместо CO₂ + H₂O', 'HSO₄⁻ оставляют целым'],
       solve=_solve_30n, kind='dict', kes=['1.9'],
       fidelity=FID(30, trap='дистракторы — типичные ошибки записи ионного уравнения', scale='реакции ионного обмена '
                              'того же набора веществ, что в заданиях 30 банка', kes=['1.9'],
                    fmt_='в КИМ — часть развёрнутого ответа; в тренажёре — выбор одного уравнения из четырёх',
                    score='в КИМ 2 балла за задание 30; здесь — проверяемый шаг, 1 балл'))
def g_30n(rng):
    pid = 'ch-ege-30-net-ionic'
    r = rng.choice(EXCH30)
    full, net = ionic(r)
    true = ion_text(net)
    wrong = []
    for L2, R2 in _net_variants(r, rng):
        t = ion_text((L2, R2))
        if t != true and t not in wrong:
            wrong.append(t)
    if len(wrong) < 2:
        raise Retry
    # добавим чужое уравнение с общим ионом
    other = [x for x in EXCH30 if x is not r and set(x['lhs']) & set(r['lhs'])]
    for x in shuffled(rng, other):
        t = ion_text(ionic(x)[1])
        if t != true and t not in wrong:
            wrong.append(t)
            break
    items = shuffled(rng, [true] + wrong[:3])
    a, b = [x for x in dict.fromkeys(r['lhs']) if x != 'H2O']
    cnd = r.get('cond', '')
    cnd_t = f' ({cnd})' if cnd and ('избыт' in cnd or 'недостат' in cnd) else ''
    q = (f'Выберите сокращённое ионное уравнение реакции ионного обмена между {ins(a).replace("ом ", "ом ")} и '
         f'{ins(b)}{cnd_t}.').replace('между ', 'между ')
    q = f'Какое сокращённое ионное уравнение соответствует реакции между растворами веществ {F(a)} и {F(b)}{cnd_t}?'
    e = f'{eq_text(r["lhs"], r["rhs"])}; полное ионное: {ion_text(full)}; сокращённое: {true}.'
    return card(pid, q, str(items.index(true) + 1), e, k='one', o=opts(items), p={'rid': r['rid'], 'opts': items},
                eqs=[(r['lhs'], r['rhs'], *r['k'])])


def _solve_30s(p):
    x = ionic(RX_BY_ID[p['rid']])
    return str(sum(x[1][0].values()) + sum(x[1][1].values()))


@proto('ch-ege-30-sum', 'ЕГЭ', 30, 'Сумма коэффициентов в сокращённом ионном уравнении',
       invariant='составить полное и сокращённое ионные уравнения и сложить коэффициенты сокращённого',
       varies='пары веществ, реакции ионного обмена с осадком, газом, водой, кислыми солями',
       answer_rule='сумма всех коэффициентов сокращённого ионного уравнения (коэффициент 1 тоже учитывается)',
       mistakes=['суммируют коэффициенты полного или молекулярного уравнения', 'забывают коэффициенты 1',
                 'не сокращают общий множитель'],
       solve=_solve_30s, kind='dict', kes=['1.9'],
       fidelity=FID(30, trap='молекулярное и полное ионное уравнения дают другие суммы', scale='реакции ионного обмена '
                              'заданий 30 банка', kes=['1.9'], fmt_='целое число',
                    score='в КИМ 2 балла за задание 30; здесь — проверяемый шаг, 1 балл'))
def g_30s(rng):
    pid = 'ch-ege-30-sum'
    r = rng.choice(EXCH30)
    full, net = ionic(r)
    s_net = sum(net[0].values()) + sum(net[1].values())
    s_full = sum(full[0].values()) + sum(full[1].values())
    s_mol = sum(r['k'][0]) + sum(r['k'][1])
    if s_full == s_net:
        raise Retry
    a, b = [x for x in dict.fromkeys(r['lhs']) if x != 'H2O']
    cnd = r.get('cond', '')
    cnd_t = f' ({cnd})' if cnd and ('избыт' in cnd or 'недостат' in cnd) else ''
    q = (f'Составьте молекулярное, полное и сокращённое ионные уравнения реакции между растворами {gen(a)} и '
         f'{gen(b)}{cnd_t}. В ответ запишите сумму коэффициентов в сокращённом ионном уравнении.')
    q = q.replace('растворами ', 'растворами ')
    e = f'{eq_text(r["lhs"], r["rhs"])}; сокращённое: {ion_text(net)} — сумма {s_net}.'
    return card(pid, q, str(s_net), e, k='num', p={'rid': r['rid']}, wrong=[str(s_full), str(s_mol), str(s_net + 1)],
                eqs=[(r['lhs'], r['rhs'], *r['k'])])


# ================================================================= 29. ОВР из перечня

OX29 = ['KMnO4', 'K2Cr2O7', 'K2CrO4', 'H2O2', 'Cl2', 'Br2', 'FeCl3', 'Fe2(SO4)3', 'MnO2', 'NaClO', 'KClO3', 'PbO2',
        'KNO2', 'NaNO2', 'HNO3', 'CuSO4', 'Na2Cr2O7', 'I2']
RED29 = ['KI', 'NaI', 'K2SO3', 'Na2SO3', 'KNO2', 'NaNO2', 'FeSO4', 'FeCl2', 'H2S', 'K2S', 'Na2S', 'KBr', 'NaBr',
         'SO2', 'NH3', 'MnSO4', 'Cr2(SO4)3', 'CrCl3', 'HCl', 'HBr', 'HI', 'PH3', 'Na3(Cr(OH)6)', 'K3(Cr(OH)6)',
         'Cr(OH)3', 'NH4Cl', 'Fe(OH)2', 'H2O2']
MED29 = ['H2SO4', 'KOH', 'NaOH', 'HCl', 'H2O']
SPECT29 = ['K2SO4', 'Na2SO4', 'Na3PO4', 'K3PO4', 'MgSO4', 'ZnSO4', 'Al2(SO4)3', 'Na2CO3', 'K2CO3', 'CaCO3',
           'BaSO4', 'Na2SiO3', 'KNO3', 'NH4NO3', 'NaHCO3', 'CuO', 'SiO2', 'ZnO', 'MgO']
_BAD29 = [{'K2S', 'K2SO3'}, {'Na2S', 'Na2SO3'}, {'FeSO4', 'KNO2'}, {'FeSO4', 'NaNO2'}, {'FeCl2', 'KNO2'},
          {'FeCl2', 'NaNO2'}, {'H2S', 'K2SO3'}, {'H2S', 'Na2SO3'}, {'K2S', 'SO2'}, {'Na2S', 'SO2'}]
REDOX29 = [r for r in RX if is_redox(r) and agent_formula(r, 'ox') and agent_formula(r, 'red') and
           set(r['lhs']) <= set(OX29 + RED29 + MED29) and 'электролиз' not in r['type'] and
           not any(FORM_OF(r, x) == 'конц.' for x in r['lhs'])]


def _salts(fs):
    return [x for x in fs if SUBS.get(x, {}).get('cls') == 'соль']


def cond29(r):
    """Признаки ОВР (для условия задания 29)."""
    prod = [x for x in dict.fromkeys(r['rhs']) if x != 'H2O']
    lhs = set(r['lhs'])
    out = set()
    simple = [x for x in prod if SUBS[x]['cls'] == 'простое вещество']
    salts = [x for x in prod if SUBS[x]['cls'] == 'соль']
    if simple and len(salts) == 2:
        out.add('простое вещество и две соли')
    if len(salts) == 3:
        out.add('три соли')
    if any(SUBS[x]['cls'] == 'кислота' and x not in lhs for x in prod):
        out.add('кислота')
    gas = any(_evolved(r, x) for x in prod)
    if gas:
        out.add('газ')
    if any(SUBS[x].get('sol') == 'н' for x in prod) and not gas:
        out.add('осадок без газа')
    if simple and not gas:
        out.add('простое вещество без газа')
    if 'обесцвеч' in r.get('sign', ''):
        out.add('обесцвечивание')
    rr = redox_roles(r)
    if rr:
        e, a, b = rr['red']
        red = agent_formula(r, 'red')
        n = parse_formula(red).get(e, 0) * (b - a)
        out.add(f'электроны:{n}')
    return out


_C29 = {'простое вещество и две соли': 'с образованием простого вещества и раствора двух солей',
        'три соли': 'с образованием трёх солей', 'кислота': 'с образованием кислоты',
        'газ': 'с выделением газа', 'осадок без газа': 'с образованием осадка, выделения газа при этом не происходит',
        'простое вещество без газа': 'с образованием простого вещества, выделения газа при этом не происходит',
        'обесцвечивание': 'с обесцвечиванием раствора'}


def _c29_text(c):
    if c.startswith('электроны:'):
        n = int(c.split(':')[1])
        return f'так, что 1 моль восстановителя отдаёт {n} моль электронов'
    return _C29[c]


def _redox_in(items):
    s = set(items) | {'H2O'}
    return [r for r in REDOX29 if set(r['lhs']) <= s]


def _solve_29c(p):
    items = p['items']
    pairs = set()
    for r in RX:
        if not set(r['lhs']) <= set(items) | {'H2O'} or 'электролиз' in r['type']:
            continue
        if any(FORM_OF(r, x) == 'конц.' for x in r['lhs']):
            continue
        rr = redox_roles(r)
        if not rr or p['cond'] not in cond29(r):
            continue
        o, rd = agent_formula(r, 'ox'), agent_formula(r, 'red')
        if o in items and rd in items:
            pairs.add((o, rd))
    if len(pairs) != 1:
        return {'err': len(pairs)}
    o, rd = pairs.pop()
    return {'А': str(items.index(o) + 1), 'Б': str(items.index(rd) + 1)}


@proto('ch-ege-29-choose', 'ЕГЭ', 29, 'Перечень из шести веществ: выбрать окислитель и восстановитель для ОВР с заданным признаком',
       invariant='найти в перечне окислители и восстановители, представить продукты их ОВР в возможной среде и выбрать '
                 'пару, для которой выполняется условие',
       varies='перечень (окислитель, 2–3 восстановителя, среда, «нейтральные» вещества), условие (простое вещество и '
              'две соли, кислота, газ, осадок, число электронов)',
       answer_rule='под А — номер окислителя, под Б — номер восстановителя; в КИМ далее — уравнение и электронный '
                   'баланс',
       mistakes=['выбирают пару, которая не даёт требуемого продукта', 'путают окислитель и восстановитель',
                 'не учитывают среду (MnSO₄ / MnO₂ / K₂MnO₄)'],
       solve=_solve_29c, kind='dict', kes=['1.12'],
       fidelity=FID(29, trap='в перечне несколько восстановителей, но условию отвечает только одна пара',
                    scale='шесть веществ и условие — как демоверсия 2027 (нитрит калия, сульфит калия, дихромат калия, '
                          'серная кислота, иодид калия, гидросульфат аммония) и 82 задания банка', kes=['1.12'],
                    fmt_='в КИМ — развёрнутый ответ (2 балла); в тренажёре — два номера (окислитель, восстановитель)',
                    style='«Из предложенного перечня выберите вещество-окислитель и вещество-восстановитель, реакция '
                          'между которыми в соответствующей среде протекает…»'))
def g_29c(rng):
    pid = 'ch-ege-29-choose'
    r = rng.choice(REDOX29)
    o, rd = agent_formula(r, 'ox'), agent_formula(r, 'red')
    if o == rd:
        raise Retry
    med = [x for x in dict.fromkeys(r['lhs']) if x not in (o, rd, 'H2O')]
    conds = [c for c in cond29(r) if c in _C29 or c.startswith('электроны:')]
    if not conds:
        raise Retry
    for _ in range(40):
        extra_red = rng.sample([x for x in RED29 if x not in (o, rd) + tuple(med)], rng.choice([1, 2]))
        extra_ox = rng.sample([x for x in OX29 if x not in (o, rd) + tuple(med) + tuple(extra_red)],
                              rng.choice([0, 0, 1]))
        base = [o, rd] + med + extra_red + extra_ox
        if len(set(base)) != len(base) or len(base) > 6:
            continue
        items = base + rng.sample([x for x in SPECT29 if x not in base], 6 - len(base))
        if any(b <= set(items) for b in _BAD29):
            continue
        # все пары «окислитель — восстановитель» перечня должны быть известны базе
        oxs = [x for x in items if x in OX29]
        reds = [x for x in items if x in RED29]
        rx_in = _redox_in(items)
        known = {(agent_formula(x, 'ox'), agent_formula(x, 'red')) for x in rx_in}
        if any((a, b) not in known and a != b for a in oxs for b in reds):
            continue
        rng.shuffle(conds)
        for c in conds:
            pairs = {(agent_formula(x, 'ox'), agent_formula(x, 'red')) for x in rx_in if c in cond29(x)}
            if pairs == {(o, rd)}:
                break
        else:
            continue
        break
    else:
        raise Retry
    rng.shuffle(items)
    ans = {'А': str(items.index(o) + 1), 'Б': str(items.index(rd) + 1)}
    names = [ru(x) for x in items]
    q = (LIST_HEAD.format(', '.join(names)) + ' Из предложенного перечня выберите вещество-окислитель и '
         f'вещество-восстановитель, реакция между которыми в соответствующей среде протекает {_c29_text(c)}. В '
         'качестве среды для протекания реакции можно использовать ещё одно из веществ, приведённых в перечне, или '
         'воду. Под буквой А запишите номер окислителя, под буквой Б — номер восстановителя.')
    e = f'{eq_text(r["lhs"], r["rhs"])}; окислитель — {F(o)}, восстановитель — {F(rd)}.'
    return card(pid, q, ans, e, k='match', o=match_opts(['окислитель', 'восстановитель'], names, rids='123456'),
                p={'items': items, 'cond': c}, eqs=[(r['lhs'], r['rhs'], *r['k'])])


REDOX_ALL = [r for r in RX if redox_roles(r) and agent_formula(r, 'ox') and agent_formula(r, 'red') and
             'электролиз' not in r['type'] and 4 <= len(r['lhs']) + len(r['rhs']) <= 8]


def _solve_29k(p):
    r = RX_BY_ID[p['rid']]
    kl, kr = balance(r['lhs'], r['rhs'])
    if p['ask'] == 'sum':
        return str(sum(kl) + sum(kr))
    f = p['f']
    return str(kl[r['lhs'].index(f)])


@proto('ch-ege-29-coefficients', 'ЕГЭ', 29, 'Схема ОВР: расставить коэффициенты методом электронного баланса',
       invariant='составить электронный баланс (число отданных = числу принятых электронов), перенести множители в '
                 'уравнение, уравнять остальные атомы',
       varies='ОВР с перманганатом, дихроматом, кислотами-окислителями, галогенами, пероксидом водорода; что спросить '
              '(коэффициент окислителя, восстановителя, сумма)',
       answer_rule='коэффициент перед формулой окислителя (восстановителя) или сумма всех коэффициентов',
       mistakes=['не учитывают индекс (Cr₂, Cl₂) при подсчёте электронов', 'забывают, что часть кислоты идёт на '
                 'солеобразование', 'сумму считают без коэффициентов 1'],
       solve=_solve_29k, kind='dict', kes=['1.12'],
       fidelity=FID(29, trap='часть окислителя/кислоты — среда (HCl в KMnO₄ + HCl, HNO₃ с металлами)',
                    scale='схемы ОВР из заданий 29 банка и демоверсии', kes=['1.12'], fmt_='целое число',
                    score='в КИМ 2 балла за задание 29; здесь — проверяемый шаг, 1 балл'))
def g_29k(rng):
    pid = 'ch-ege-29-coefficients'
    r = rng.choice(REDOX_ALL)
    kl, kr = r['k']
    o, rd = agent_formula(r, 'ox'), agent_formula(r, 'red')
    ask = rng.choice(['ox', 'red', 'sum']) if o != rd else 'sum'
    if ask == 'sum':
        a = str(sum(kl) + sum(kr))
        wrong = [str(sum(kl)), str(sum(kl) + sum(kr) - 1), str(sum(x for x in kl + kr if x > 1))]
        tail = 'В ответ запишите сумму коэффициентов в уравнении.'
        f = None
    else:
        f = o if ask == 'ox' else rd
        a = str(kl[r['lhs'].index(f)])
        other = rd if ask == 'ox' else o
        wrong = [str(kl[r['lhs'].index(other)]), str(sum(kl) + sum(kr)), str(int(a) * 2)]
        tail = f'В ответ запишите коэффициент перед формулой {"окислителя" if ask == "ox" else "восстановителя"}.'
    if all(k == 1 for k in kl + kr):
        raise Retry
    q = (f'Используя метод электронного баланса, расставьте коэффициенты в уравнении реакции, схема которой '
         f'{scheme_text(r["lhs"], r["rhs"])}. Определите окислитель и восстановитель. {tail}')
    rr = redox_roles(r)
    e = (f'{eq_text(r["lhs"], r["rhs"])}. Окислитель — {F(o)} ({_EL_RU.get(rr["ox"][0], rr["ox"][0])} '
         f'{_sgn(rr["ox"][1])} → {_sgn(rr["ox"][2])}), восстановитель — {F(rd)} '
         f'({_EL_RU.get(rr["red"][0], rr["red"][0])} {_sgn(rr["red"][1])} → {_sgn(rr["red"][2])}).')
    return card(pid, q, a, e, k='num', p={'rid': r['rid'], 'ask': ask, 'f': f}, wrong=wrong,
                eqs=[(r['lhs'], r['rhs'], *r['k'])])


def _solve_29e(p):
    r = RX_BY_ID[p['rid']]
    role = p['role']
    f = p['f']
    # независимо: сумма изменений ст. ок. по всем атомам, меняющим ст. ок. в формуле агента
    of = ox_of(f)
    tot = 0
    for e, a in of.items():
        prod = {(ox_of(g) or {}).get(e) for g in r['rhs']} - {None, a}
        if not prod:
            continue
        b = max(prod) if role == 'red' else min(prod)
        if (role == 'red' and b > a) or (role == 'ox' and b < a):
            tot += abs(b - a) * parse_formula(f)[e]
    return str(tot)


@proto('ch-ege-29-electrons', 'ЕГЭ', 29, 'Число электронов, которое отдаёт (принимает) 1 формульная единица восстановителя '
                                         '(окислителя)',
       invariant='определить изменение степени окисления и умножить на число атомов элемента в формуле',
       varies='ОВР из базы, роль вещества',
       answer_rule='n(e⁻) = |Δст. ок.| × число атомов элемента в формуле (для K₂Cr₂O₇ → Cr³⁺: 6)',
       mistakes=['не умножают на индекс (Cr₂O₇²⁻, Cl₂)', 'берут изменение не того элемента'],
       solve=_solve_29e, kind='dict', kes=['1.12'],
       fidelity=FID(29, trap='индексы в формулах окислителя/восстановителя (K₂Cr₂O₇, Cl₂, FeS₂)', scale='реакции '
                              'заданий 29 банка («1 моль восстановителя отдаёт 10 моль электронов»)', kes=['1.12'],
                    fmt_='целое число', score='в КИМ — часть задания 29; здесь — проверяемый шаг, 1 балл'))
def g_29e(rng):
    pid = 'ch-ege-29-electrons'
    r = rng.choice(REDOX_ALL)
    role = rng.choice(['ox', 'red'])
    f = agent_formula(r, role)
    rr = redox_roles(r)
    e_, a, b = rr[role]
    n = abs(b - a) * parse_formula(f)[e_]
    if len([x for x in (ox_of(f) or {}) if x != e_ and any((ox_of(g) or {}).get(x) not in (None, (ox_of(f) or {})[x])
                                                          for g in r['rhs'])]):
        raise Retry
    word = 'отдаёт' if role == 'red' else 'принимает'
    q = (f'Для реакции, протекающей по схеме {scheme_text(r["lhs"], r["rhs"])}, определите, сколько моль электронов '
         f'{word} 1 моль {"восстановителя" if role == "red" else "окислителя"}. В ответ запишите число.')
    e = f'{F(f)}: {_EL_RU.get(e_, e_)} {_sgn(a)} → {_sgn(b)}, атомов в формуле {parse_formula(f)[e_]}, n(e⁻) = {n}.'
    return card(pid, q, str(n), e, k='num', p={'rid': r['rid'], 'role': role, 'f': f},
                wrong=[str(abs(b - a)), str(n * 2), str(abs(b) if b else abs(a))], eqs=[(r['lhs'], r['rhs'], *r['k'])])


# ================================================================= 31. «Мысленный эксперимент» (цепочка из 4 реакций)

def _prep_name(f, form=''):
    """Предложный падеж: «в соляной кислоте», «в растворе гидроксида натрия», «в воде»."""
    if f == 'H2O':
        return 'в воде'
    n = ru(f)
    adj = {'конц.': 'концентрированной ', 'разб.': 'разбавленной '}.get(form, '')
    if n.endswith('кислота'):
        w = n.split(' ')
        w = [x[:-2] + 'ой' if x.endswith('ая') else x for x in w]
        w[-1] = 'кислоте'
        return 'в ' + adj + ' '.join(w)
    return 'в растворе ' + gen(f)


GAS_NOM = {'CO2': 'углекислый газ', 'SO2': 'сернистый газ', 'Cl2': 'хлор', 'H2S': 'сероводород', 'NH3': 'аммиак',
           'O2': 'кислород', 'H2': 'водород', 'CO': 'угарный газ', 'NO2': 'оксид азота(IV)', 'HCl': 'хлороводород'}


def _carrier(r, prev=None):
    """(вещество, вид) — что переходит в следующую реакцию; None, если выбрать однозначно нельзя."""
    lhs = set(r['lhs'])
    prod = [x for x in dict.fromkeys(r['rhs']) if x != 'H2O' and x not in lhs]
    aq = r.get('aq')
    prec = [x for x in prod if SUBS[x].get('sol') == 'н' and SUBS[x]['cls'] != 'простое вещество' and aq]
    gas = [x for x in prod if _evolved(r, x)]
    simple = [x for x in prod if SUBS[x]['cls'] == 'простое вещество' and x not in I.GASES]
    out = []
    if len(prec) == 1:
        out.append((prec[0], 'осадок'))
    if len(gas) == 1:
        out.append((gas[0], 'газ'))
    if len(simple) == 1:
        out.append((simple[0], 'простое'))
    if aq and not prec:
        salts = [x for x in prod if SUBS[x]['cls'] == 'соль' and SUBS[x].get('sol') == 'р']
        if len(salts) == 1:
            out.append((salts[0], 'раствор'))
    if not aq:
        solids = [x for x in prod if x not in I.GASES and SUBS[x].get('state') in ('тв', None) and
                  SUBS[x]['cls'] != 'простое вещество']
        if len(solids) == 1:
            out.append((solids[0], 'твёрдое'))
    return out


_SUBJ = {'осадок': ['Образовавшийся осадок', 'Выпавший осадок отделили и'],
         'газ': ['Выделившийся газ'], 'раствор': ['Полученный раствор'],
         'твёрдое': ['Твёрдый продукт реакции', 'Полученное твёрдое вещество'],
         'простое': ['Образовавшееся простое вещество']}


def _acc_name(f):
    n = ru(f)
    w = n.split(' ')
    if n.endswith('кислота'):
        w = [x[:-2] + 'ую' if x.endswith('ая') else x for x in w]
        w[-1] = 'кислоту'
    elif n in ('вода',):
        return 'воду'
    return ' '.join(w)


_GAS_R = {'CO2', 'SO2', 'Cl2', 'H2S', 'NH3', 'O2', 'H2', 'CO', 'NO2'}


def _step_text(r, subj_f, kind, rng, first=False):
    """Фраза для одной стадии. subj_f — «носитель» (вещество, над которым действуют)."""
    others = [x for x in dict.fromkeys(r['lhs']) if x != subj_f and x != 'H2O']
    cond = r.get('cond', '')
    heat = ' при нагревании' if cond.startswith('t') or ', t' in cond else ''
    if not r.get('aq') and not (cond.startswith('t') or ', t' in cond or 'сплавл' in cond or 'горение' in cond or
                                'обжиг' in cond or 'O2' in r['lhs'] or len(r['lhs']) == 1):
        return None
    if first:
        name = ru(subj_f)
        subj = name[0].upper() + name[1:]
    else:
        subj = rng.choice(_SUBJ[kind])
    if len(r['lhs']) == 1 or not others:
        if r['lhs'] == [subj_f] and 't' in cond:
            verb = rng.choice(['прокалили', 'нагрели'])
            return f'{subj} {verb}.'
        if others == [] and 'H2O' in r['lhs']:
            return f'{subj} {"обработали водой" if first else "поместили в воду"}.'
        return None
    if len(others) != 1:
        return None
    R = others[0]
    fr = FORM_OF(r, R) or ''
    exc = 'избыток ' in cond and R in cond or ('избыток кислоты' in cond and SUBS[R]['cls'] == 'кислота') or \
        ('избыток щёлочи' in cond and R in I.ALKALIS)
    if 'недостаток' in cond:
        return None
    if 'сплавл' in cond:
        return f'{subj} сплавили с {ins(R)}.'
    if R == 'O2':
        return f'{subj} {"подвергли обжигу" if "обжиг" in cond else "сожгли в кислороде"}.'
    is_metal = SUBS[R]['cls'] == 'простое вещество' and SUBS[R].get('sub') == 'металл'
    if kind == 'газ' and not first:
        if SUBS[R].get('sol') == 'р' or SUBS[R]['cls'] in ('кислота', 'основание'):
            return f'{subj} пропустили через {"избыток раствора" if exc else "раствор"} {gen(R)}.'
        if 't' in cond:
            return f'{subj} пропустили над нагретым {ins(R)}.'
        return None
    if R in _GAS_R:
        if r.get('aq'):
            where = f'раствор {gen(subj_f)}' if first else ('полученный раствор' if kind == 'раствор' else None)
            if where is None:
                return None
            return f'Через {where} пропустили {"избыток " + gen(R) if exc else GAS_NOM[R]}.'
        if 't' in cond:
            return f'{subj} нагрели в атмосфере {gen(R)}.'
        return None
    solid_subj = SUBS[subj_f].get('sol') == 'н' or SUBS[subj_f]['cls'] == 'простое вещество' or kind in (
        'осадок', 'твёрдое', 'простое')
    if solid_subj:
        if is_metal:
            return None
        if SUBS[R]['cls'] == 'кислота':
            if rng.random() < 0.5:
                return f'{subj} растворили {_prep_name(R, fr)}{heat}.'
            return f'{subj} обработали {"избытком " if exc else ""}{_ADJ.get(fr, "")}{ins(R)}{heat}.'
        if R in I.ALKALIS or SUBS[R].get('sol') == 'р':
            return f'{subj} обработали {"избытком раствора" if exc else "раствором"} {gen(R)}{heat}.'
        if 't' in cond:
            return f'{subj} нагрели с {ins(R)}.'
        return None
    # раствор + металл / кислота / раствор
    target = f'раствор {gen(subj_f)}' if first else 'полученный раствор'
    if is_metal:
        return f'В {target} поместили {ru(R)}{heat}.'
    if SUBS[R]['cls'] == 'кислота':
        adj = {'конц.': 'концентрированную ', 'разб.': 'разбавленную '}.get(fr, '')
        return f'К {"раствору " + gen(subj_f) if first else "полученному раствору"} прилили ' \
               f'{"избыток " if exc else ""}{adj}{_acc_name(R) if not exc else gen(R)}{heat}.'
    if first:
        return f'К раствору {gen(subj_f)} прилили {"избыток раствора" if exc else "раствор"} {gen(R)}{heat}.'
    return f'К полученному раствору добавили {"избыток раствора" if exc else "раствор"} {gen(R)}{heat}.'


def _unique_step(r, carrier, R):
    """Реакция однозначно задаётся парой «носитель + реагент» (с учётом формы и описанного избытка)."""
    rs = pos_rx(carrier, '', R, FORM_OF(r, R) or '') if R else [x for x in SINGLE.get(carrier, [])
                                                                 if 't' in x.get('cond', '')]
    rs = [x for x in rs if 'электролиз' not in x['type']]
    if len(rs) == 1:
        return True
    return len([x for x in rs if 'избыток' in x.get('cond', '') == ('избыток' in r.get('cond', ''))]) == 1 and \
        'избыток' in r.get('cond', '')


CHAIN_RX = [r for r in RX if 'электролиз' not in r['type'] and len(set(r['lhs']) - {'H2O'}) <= 2 and
            'качественная' not in r.get('tags', [])]
BY_LHS31 = {}
for _r in CHAIN_RX:
    for _x in set(_r['lhs']):
        BY_LHS31.setdefault(_x, []).append(_r)


def build_chain(rng, n=4):
    starts = [r for r in CHAIN_RX if r['lhs'][0] != 'H2O']
    r1 = rng.choice(starts)
    subj = [x for x in dict.fromkeys(r1['lhs']) if x != 'H2O' and x not in I.GASES]
    if not subj:
        return None
    A = rng.choice(subj)
    if SUBS[A]['cls'] in ('кислота',) and len(subj) > 1:
        A = [x for x in subj if x != A][0]
    others = [x for x in subj if x != A]
    if others and not _unique_step(r1, A, others[0]) or not others and not _unique_step(r1, A, None):
        return None
    steps = []
    t = _step_text(r1, A, None, rng, first=True)
    if not t:
        return None
    car = _carrier(r1)
    if not car:
        return None
    c, kind = rng.choice(car)
    steps.append((r1, A, c, kind, t))
    used = {A, c}
    for _ in range(n - 1):
        prevR = set(steps[-1][0]['lhs']) - {steps[-1][1]}
        cand = [r for r in BY_LHS31.get(c, []) if r is not steps[-1][0] and not (set(r['lhs']) - {c}) & prevR - {'H2O'}]
        rng.shuffle(cand)
        ok = False
        for r in cand:
            oth = [x for x in dict.fromkeys(r['lhs']) if x not in (c, 'H2O')]
            if len(oth) > 1 or not _unique_step(r, c, oth[0] if oth else None):
                continue
            if kind == 'газ' and r.get('aq') is None and not oth:
                continue
            t = _step_text(r, c, kind, rng)
            if not t:
                continue
            car = [x for x in _carrier(r) if x[0] not in used]
            if not car:
                continue
            c2, kind2 = rng.choice(car)
            steps.append((r, c, c2, kind2, t))
            used.add(c2)
            c, kind = c2, kind2
            ok = True
            break
        if not ok:
            return None
    return steps


def _solve_31(p):
    rs = [RX_BY_ID[x] for x in p['rids']]
    k = p['k']
    if p['ask'] == 'sum':
        kl, kr = balance(rs[k]['lhs'], rs[k]['rhs'])
        return str(sum(kl) + sum(kr))
    # вещество-носитель после реакции k: продукт реакции k, который является реагентом реакции k+1 (или названный вид)
    prod = set(rs[k]['rhs'])
    nxt = set(rs[k + 1]['lhs']) if k + 1 < len(rs) else set()
    cands = [x for x in p['opts'] if x in prod and (not nxt or x in nxt)]
    if len(cands) != 1:
        return 'err'
    return str(p['opts'].index(cands[0]) + 1)


_ORD = ['первой', 'второй', 'третьей', 'четвёртой']
_ORD_ACC = ['первую', 'вторую', 'третью', 'четвёртую']
_KIND_Q = {'осадок': 'выпавший в осадок', 'газ': 'выделившийся газ', 'раствор': 'соль, оставшуюся в растворе',
           'твёрдое': 'твёрдый продукт', 'простое': 'образовавшееся простое вещество'}


@proto('ch-ege-31-chain', 'ЕГЭ', 31, 'Мысленный эксперимент: описание четырёх последовательных реакций → вещества и уравнения',
       invariant='по описанию (реагенты, условия, признаки) восстановить вещества на каждой стадии и записать '
                 'уравнения; в тренажёре — проверяемый шаг: вещество одной из стадий или сумма коэффициентов',
       varies='цепочки из базы реакций: растворение в кислотах/щелочах, осаждение, прокаливание, ОВР, пропускание газов',
       answer_rule='формула вещества, образовавшегося на указанной стадии (один из четырёх вариантов), или сумма '
                   'коэффициентов в уравнении указанной реакции',
       mistakes=['теряют «носитель» цепочки (берут побочный продукт)', 'не учитывают избыток реагента',
                 'в ОВР неверно определяют продукты восстановления/окисления'],
       solve=_solve_31, kind='dict', kes=['2.2', '2.3', '2.4'],
       fidelity=FID(31, trap='вещества-дистракторы — соединения того же элемента в другой степени окисления или '
                             'другие соли', scale='четыре стадии, стиль описания как в демоверсии 2027 («Алюминат калия '
                             'растворили в … Выделившийся газ разделили на две части…») и 90 заданиях банка',
                    kes=['2.2', '2.3', '2.4'], fmt_='в КИМ — четыре уравнения (4 балла); в тренажёре — номер варианта '
                                                     'или целое число'))
def g_31(rng):
    pid = 'ch-ege-31-chain'
    steps = None
    for _ in range(30):
        steps = build_chain(rng)
        if steps:
            break
    if not steps:
        raise Retry
    text = ' '.join(s[4] for s in steps) + ' Напишите молекулярные уравнения четырёх описанных реакций.'
    ask = rng.choice(['subst', 'subst', 'sum'])
    rids = [s[0]['rid'] for s in steps]
    if ask == 'sum':
        k = rng.randrange(4)
        r = steps[k][0]
        kl, kr = r['k']
        a = str(sum(kl) + sum(kr))
        if all(x == 1 for x in kl + kr):
            raise Retry
        q = text + f' В ответ запишите сумму коэффициентов в уравнении {_ORD[k]} реакции.'
        e = ' '.join(f'{i + 1}) {eq_text(s[0]["lhs"], s[0]["rhs"])}' for i, s in enumerate(steps))
        return card(pid, q, a, e, k='num', p={'rids': rids, 'k': k, 'ask': 'sum'},
                    wrong=[str(sum(kl)), str(sum(kl) + sum(kr) + 1), str(len(kl) + len(kr))],
                    eqs=[(s[0]['lhs'], s[0]['rhs'], *s[0]['k']) for s in steps])
    k = rng.randrange(3)
    r, _, c, kind, _ = steps[k]
    rel = [x for x in _related(c, rng, 30) if x not in r['rhs'] and x not in steps[k + 1][0]['lhs']]
    if len(rel) < 3:
        raise Retry
    items = shuffled(rng, [c] + rel[:3])
    pre = 'во' if k == 1 else 'в'
    qq = {'осадок': f'Какое вещество выпало в осадок {pre} {_ORD[k]} реакции?',
          'газ': f'Какой газ выделился {pre} {_ORD[k]} реакции?',
          'раствор': f'Какая соль, образовавшаяся {pre} {_ORD[k]} реакции, вступила затем в {_ORD_ACC[k + 1]} '
                     f'реакцию?',
          'твёрдое': f'Какое твёрдое вещество образовалось {pre} {_ORD[k]} реакции?',
          'простое': f'Какое простое вещество образовалось {pre} {_ORD[k]} реакции?'}[kind]
    q = text + ' ' + qq
    e = ' '.join(f'{i + 1}) {eq_text(s[0]["lhs"], s[0]["rhs"])}' for i, s in enumerate(steps))
    return card(pid, q, str(items.index(c) + 1), e, k='one', o=opts([F(x) for x in items]),
                p={'rids': rids, 'k': k, 'ask': 'subst', 'opts': items},
                eqs=[(s[0]['lhs'], s[0]['rhs'], *s[0]['k']) for s in steps])


# ================================================================= рецепты полного развёрнутого ответа (29–31)

recipe('ch-ege-29-full', 'ЕГЭ', 29, 'Полный ответ 29: уравнение ОВР по перечню и электронный баланс',
       invariant='выбрать окислитель и восстановитель из перечня, записать уравнение, составить электронный баланс, '
                 'указать окислитель и восстановитель',
       varies='перечень из шести веществ и условие — как в ch-ege-29-choose',
       answer_rule='2 балла: верное уравнение с коэффициентами (1) + электронный баланс с указанием окислителя и '
                   'восстановителя (1)',
       mistakes=['реакция не удовлетворяет условию', 'не та среда — не те продукты восстановления Mn/Cr',
                 'коэффициенты не согласованы с балансом'],
       kind='llm',
       how='условие берётся из генератора ch-ege-29-choose (перечень, условие, эталонная реакция из chemdb). ИИ получает '
           'условие и ответ ученика (текст), извлекает из него уравнение и полуреакции',
       check='уравнение ученика разбирается parse_formula; вещества — из перечня (+H₂O), продукты совпадают с одной из '
             'реакций chemdb для этой пары с тем же признаком (cond29); коэффициенты — пропорциональны balance(); '
             'число электронов в балансе = Δст. ок. × индекс (как в ch-ege-29-electrons)',
       capacity=2000, example={
           'q': 'Перечень: дихромат калия, иодид калия, серная кислота, сульфат натрия, карбонат калия, нитрат аммония. '
                'Выберите окислитель и восстановитель, реакция между которыми в кислой среде даёт простое вещество и '
                'раствор двух солей… запишите уравнение и электронный баланс.',
           'a': 'K₂Cr₂O₇ + 6KI + 7H₂SO₄ = Cr₂(SO₄)₃ + 3I₂ + 4K₂SO₄ + 7H₂O; 2Cr⁺⁶ + 6e = 2Cr⁺³ | 1; 2I⁻ − 2e = I₂ | 3; '
                'K₂Cr₂O₇ (Cr⁺⁶) — окислитель, KI (I⁻) — восстановитель',
           'e': 'иод — простое вещество, соли — Cr₂(SO₄)₃ и K₂SO₄'},
       why='развёрнутый ответ оценивается по критериям (уравнение + баланс); автоматически проверяется через шаги '
           'ch-ege-29-choose / -coefficients / -electrons и сверку с chemdb',
       kes=['1.12'],
       fidelity=FID(29, trap='как в КИМ: одна пара из перечня отвечает условию', scale='перечень из шести веществ',
                    kes=['1.12'], fmt_='развёрнутый ответ', score='2 балла (уравнение — 1, баланс — 1)'))

recipe('ch-ege-30-full', 'ЕГЭ', 30, 'Полный ответ 30: молекулярное, полное и сокращённое ионные уравнения',
       invariant='выбрать пару для реакции ионного обмена по условию и записать три уравнения',
       varies='перечень и условие — как в ch-ege-30-choose',
       answer_rule='2 балла: молекулярное уравнение (1) + полное и сокращённое ионные (1)',
       mistakes=['слабые электролиты и осадки записаны ионами', 'не сокращены «зрители»', 'выбрана ОВР, а не обмен'],
       kind='llm',
       how='условие — из ch-ege-30-choose; ИИ извлекает из ответа ученика три уравнения',
       check='молекулярное — есть в chemdb (EXCH30) для выбранной пары, коэффициенты ∝ balance(); ионные — сравниваются '
             'с ionic(r) (полное и сокращённое), проверка атомов и заряда',
       capacity=1500, example={
           'q': 'Перечень: нитрит калия, сульфит калия, дихромат калия, серная кислота, иодид калия, гидросульфат '
                'аммония. Выберите два вещества, реакция ионного обмена между которыми даёт слабый электролит без газа…',
           'a': '2KNO₂ + H₂SO₄ = K₂SO₄ + 2HNO₂; 2K⁺ + 2NO₂⁻ + 2H⁺ + SO₄²⁻ = 2K⁺ + SO₄²⁻ + 2HNO₂; NO₂⁻ + H⁺ = HNO₂',
           'e': 'азотистая кислота — слабый электролит'},
       why='развёрнутый ответ; автоматическая проверка — через ch-ege-30-choose / -net-ionic / -sum и ionic()',
       kes=['1.9'],
       fidelity=FID(30, trap='как в КИМ', scale='перечень из шести веществ', kes=['1.9'], fmt_='развёрнутый ответ',
                    score='2 балла'))

recipe('ch-ege-31-full', 'ЕГЭ', 31, 'Полный ответ 31: четыре уравнения реакций по описанию эксперимента',
       invariant='по описанию восстановить четыре реакции и записать уравнения с коэффициентами',
       varies='цепочки build_chain() из chemdb (4 стадии), стиль описания КИМ',
       answer_rule='4 балла — по 1 за каждое верное уравнение',
       mistakes=['потерян носитель цепочки', 'не учтён избыток', 'неверные продукты ОВР'],
       kind='llm',
       how='генератор ch-ege-31-chain строит описание и эталонные уравнения (RX chemdb); ИИ извлекает из ответа '
           'ученика четыре уравнения',
       check='каждое уравнение ученика: те же реагенты и продукты, что эталонная реакция стадии (порядок не важен), '
             'коэффициенты ∝ balance(); допускается другой верный продукт только если он есть в chemdb для тех же '
             'реагентов и условий',
       capacity=3000, example={
           'q': 'К раствору хлорида меди(II) прилили раствор гидроксида кальция. Выпавший осадок отделили и обработали '
                'азотной кислотой. К полученному раствору добавили раствор сульфида аммония. Выпавший осадок отделили '
                'и растворили в концентрированной азотной кислоте при нагревании. Напишите уравнения четырёх реакций.',
           'a': 'CuCl₂ + Ca(OH)₂ = Cu(OH)₂ + CaCl₂; Cu(OH)₂ + 2HNO₃ = Cu(NO₃)₂ + 2H₂O; '
                'Cu(NO₃)₂ + (NH₄)₂S = CuS + 2NH₄NO₃; CuS + 8HNO₃ = CuSO₄ + 8NO₂ + 4H₂O',
           'e': 'носитель — соединения меди; последняя стадия — ОВР (S⁻² → S⁺⁶)'},
       why='развёрнутый ответ на 4 балла; автоматически проверяются шаги ch-ege-31-chain',
       kes=['2.2', '2.3', '2.4'],
       fidelity=FID(31, trap='как в КИМ', scale='четыре стадии', kes=['2.2', '2.3', '2.4'], fmt_='развёрнутый ответ',
                    score='4 балла'))

recipe('ch-ege-24-organic', 'ЕГЭ', 24, 'Качественные реакции органических веществ: признак / реактив для различения',
       invariant='по функциональным группам определить признак реакции (Cu(OH)₂, [Ag(NH₃)₂]OH, бромная вода, KMnO₄, '
                 'FeCl₃) или реактив, различающий два органических вещества',
       varies='пары органических веществ (спирты, многоатомные спирты, фенол, альдегиды, кислоты, алкены, алкины, '
              'арены), реактивы',
       answer_rule='каждой паре — признак (или реактив, дающий разные признаки)',
       mistakes=['глицерин и этанол различают бромной водой', 'бензол обесцвечивает KMnO₄'],
       kind='dict',
       how='таблица качественных реакций — chemdb_org.FACTS (qual=True, поле sign) и REACTIONS с sign; генерация по '
           'схеме ch-ege-24-signs / ch-ege-24-distinguish этого модуля, но по органической базе',
       check='признак пары = sign факта/реакции chemdb_org для (вещество, реактив); различение — признаки разные, для '
             'остальных реактивов одинаковые или реакции нет (NOT_REACT)',
       capacity=300, example={
           'q': 'Установите соответствие между двумя веществами и реактивом, с помощью которого их можно различить: '
                'А) этанол и глицерин; Б) пропен и пропан; В) фенол (р-р) и этанол; Г) этаналь и этанол. '
                '1) Cu(OH)₂  2) Br₂ (водн.)  3) FeCl₃  4) [Ag(NH₃)₂]OH  5) Na₂SO₄',
           'a': 'А1 Б2 В3 Г4', 'e': 'глицерин — ярко-синий раствор с Cu(OH)₂; пропен обесцвечивает бромную воду; '
                                     'фенол — фиолетовое окрашивание с FeCl₃; этаналь — «серебряное зеркало»'},
       why='органическая часть задания 24 опирается на базу chemdb_org (участок «органика»); генератор по образцу '
           'неорганического стоит собрать исполнителю органики',
       kes=['3.19', '2.5'],
       fidelity=FID(24, trap='как в неорганической части', scale='демоверсия 2027, вариант «ИЛИ» (C₂H₂ и '
                              '[Ag(NH₃)₂]OH, C₂H₂ и Br₂ (р-р)…)', kes=['3.19', '2.5'], fmt_='четыре цифры под буквами'))

recipe('ch-ege-17-organic', 'ЕГЭ', 17, 'Классификация органических реакций (присоединение, замещение, изомеризация…)',
       invariant='отнести органическую реакцию к типам: присоединения, замещения, отщепления, изомеризации, '
                 'гидрирования, гидратации, этерификации, полимеризации; каталитическая, обратимая, экзо/эндо',
       varies='органические реакции из базы chemdb_org',
       answer_rule='номера всех типов, к которым относится реакция (или пара «реакция — пара типов»)',
       mistakes=['гидрирование не считают присоединением', 'этерификацию считают необратимой'],
       kind='dict',
       how='типы реакций берутся из REACTIONS chemdb_org (поле type); форма карточки — как ch-ege-17-types / -match',
       check='тип совпадает с полем type реакции chemdb_org; тепловой эффект/обратимость — только если заданы явно',
       capacity=200, example={
           'q': 'Из предложенного перечня выберите все типы реакций, к которым можно отнести получение метилпропана из '
                'н-бутана: 1) каталитическая 2) изомеризации 3) присоединения 4) гидрирования 5) дегидрирования',
           'a': '12', 'e': 'изомеризация бутана идёт на катализаторе AlCl₃'},
       why='органическая часть задания 17 — база chemdb_org (участок «органика»)',
       kes=['1.5'],
       fidelity=FID(17, trap='как в неорганической части', scale='задания банка КЭС 1.5 с органическими реакциями',
                    kes=['1.5'], fmt_='номера выбранных ответов'))
