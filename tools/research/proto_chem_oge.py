"""Прототипы ОГЭ по химии 2027, задания 7–17, 20, 21, 23 (id ch-oge-NN-slug).

План КИМ ОГЭ 2027 (спецификация, обобщённый план; демоверсия 2027):
  7 — классификация неорганических веществ: выбрать вещества двух классов, порядок важен (Б, 1 б.);
  8 — свойства простых веществ и оксидов: какие два вещества реагируют / не реагируют с X (Б, 1 б.);
  9 — реагирующие вещества → продукты, соответствие 3→5 (П, 2 б.);
 10 — вещество → два реагента, с каждым из которых оно реагирует, соответствие 3→4 (П, 2 б.);
 11 — классификация реакций: две пары веществ / две схемы нужного типа (Б, 1 б.);
 12 — реагирующие вещества → признак реакции, соответствие 3→4 (П, 2 б.);
 13 — электролитическая диссоциация: ионы и их количество, электролиты (Б, 1 б.);
 14 — сокращённое ионное уравнение → два исходных вещества (Б, 1 б.);
 15 — схема процесса → окисление/восстановление (Б, 1 б.);
 16 — верные суждения о правилах работы в лаборатории, быту, о смесях (Б, 1 б.);
 17 — два вещества → реактив, которым их можно различить (П, 2 б.);
 20 — ОВР: электронный баланс, коэффициенты, окислитель и восстановитель (В, 3 б.);
 21 — цепочка превращений из трёх стадий (В, 3 б.);
 23 — реальный эксперимент: распознавание веществ в двух склянках (В, 5 б.).
Задания 20, 21, 23 — развёрнутые; в тренажёре они разложены на проверяемые шаги (роль веществ, коэффициенты,
выбор вещества X, реактива, признака), условие — как в КИМ.

Химия — из tools/research/chemdb_oge.py (вещества, реакции-факты, таблица растворимости, ряд активности).
Генератор выбирает вещества по правилам (классы, растворимость, ряд активности — функция R ниже), а solve()
независимо ищет реакции заново по реагентам в базе chemdb.load() (реакция есть — вещества реагируют).
Пары, где школьный ответ спорный, R помечает None — такие пары в карточки не попадают.
Тексты условий — свои (не пересказ банка ФИПИ), в стиле КИМ ОГЭ.
"""
import re
from collections import Counter
from fractions import Fraction as Fr

import chemdb
import chemdb_oge as D
from pc_core import proto, recipe, pcard, opts, match_opts, balance, check_balance, eq_str, pretty, parse_formula, Retry

LET = 'АБВГД'

# ================================================================= вещества

SUB = {}
for _row in D.SUBSTANCES:
    SUB.setdefault(_row['f'], _row)

SALT = {}      # формула соли → (катион, анион, растворимость)
for (_c, _a), _v in D.SOL.items():
    if _c != 'H' and _a != 'OH' and _v in ('р', 'м', 'н'):
        SALT[D._salt_formula(_c, _a)] = (_c, _a, _v)
CAT_OF_SALT = {f: v[0] for f, v in SALT.items()}

METALS = ['Li', 'Na', 'K', 'Mg', 'Ca', 'Ba', 'Al', 'Zn', 'Fe', 'Cu', 'Ag']
NONMET = ['H2', 'O2', 'Cl2', 'Br2', 'S', 'P', 'C', 'N2', 'Si']
OX_ACT = ['Li2O', 'Na2O', 'K2O', 'CaO', 'BaO']          # оксиды щелочных и щёлочноземельных металлов
OX_B = OX_ACT + ['MgO', 'CuO', 'FeO']
OX_AM = ['ZnO', 'Al2O3', 'Fe2O3']
OX_A = ['CO2', 'SO2', 'SO3', 'P2O5', 'SiO2', 'NO2']
OX_N = ['CO', 'NO']
ALK = {'LiOH': 'Li', 'NaOH': 'Na', 'KOH': 'K', 'Ca(OH)2': 'Ca', 'Ba(OH)2': 'Ba'}
BINS = {'Mg(OH)2': 'Mg', 'Cu(OH)2': 'Cu', 'Fe(OH)2': 'Fe2', 'Fe(OH)3': 'Fe3'}
BAMP = {'Zn(OH)2': 'Zn', 'Al(OH)3': 'Al'}
ACID = {'HCl': 'Cl', 'HBr': 'Br', 'HI': 'I', 'HNO3': 'NO3', 'H2SO4': 'SO4', 'H3PO4': 'PO4', 'H2S': 'S', 'H2SiO3': 'SiO3'}
STRONG = ['HCl', 'HBr', 'HI', 'HNO3', 'H2SO4']
ACT = {m: i for i, m in enumerate(D.ACTIVITY)}
MET_OF = {k: v[3] for k, v in D.CATIONS.items()}
REACTIVE_M = {'Li', 'Na', 'K', 'Ca', 'Ba'}


def kind(f):
    if f in METALS:
        return 'metal'
    if f in NONMET:
        return 'nonmetal'
    if f == 'H2O':
        return 'water'
    if f == 'NH3':
        return 'nh3'
    if f in OX_B:
        return 'oxb'
    if f in OX_AM:
        return 'oxam'
    if f in OX_A:
        return 'oxa'
    if f in OX_N:
        return 'oxn'
    if f in ACID:
        return 'acid'
    if f in ALK:
        return 'alk'
    if f in BINS:
        return 'bins'
    if f in BAMP:
        return 'bamp'
    if f in SALT:
        return 'salt'
    return None


def disp(f):
    """Формула для текста карточки: индексы, квадратные скобки комплексов."""
    return pretty(SUB.get(f, {}).get('view', f))


def name(f):
    return SUB[f]['name']


def cap(t):
    """Заглавная первая буква без порчи остального (иначе «железа(iii)»)."""
    return t[:1].upper() + t[1:]


NOUN_CASES = {  # именительный: (родительный, творительный)
    'литий': ('лития', 'литием'), 'натрий': ('натрия', 'натрием'), 'калий': ('калия', 'калием'),
    'магний': ('магния', 'магнием'), 'кальций': ('кальция', 'кальцием'), 'барий': ('бария', 'барием'),
    'алюминий': ('алюминия', 'алюминием'), 'цинк': ('цинка', 'цинком'), 'железо': ('железа', 'железом'),
    'медь': ('меди', 'медью'), 'серебро': ('серебра', 'серебром'), 'водород': ('водорода', 'водородом'),
    'кислород': ('кислорода', 'кислородом'), 'озон': ('озона', 'озоном'), 'хлор': ('хлора', 'хлором'),
    'бром': ('брома', 'бромом'), 'иод': ('иода', 'иодом'), 'сера': ('серы', 'серой'), 'фосфор': ('фосфора', 'фосфором'),
    'углерод': ('углерода', 'углеродом'), 'азот': ('азота', 'азотом'), 'кремний': ('кремния', 'кремнием'),
    'вода': ('воды', 'водой'), 'аммиак': ('аммиака', 'аммиаком'), 'кислота': ('кислоты', 'кислотой'),
    'известь': ('извести', 'известью'), 'газ': ('газа', 'газом'), 'сода': ('соды', 'содой'),
    'пероксид': ('пероксида', 'пероксидом'), 'надпероксид': ('надпероксида', 'надпероксидом'),
}


def _decl(phrase, case):
    """Склонение названия вещества: case 0 — родительный, 1 — творительный. Склоняются слова до первого
    слова в родительном падеже («оксид | меди(II)», «соляная кислота»)."""
    words = phrase.split(' ')
    out, done = [], False
    for w in words:
        if done:
            out.append(w)
            continue
        if w in NOUN_CASES:
            out.append(NOUN_CASES[w][case])
            done = w not in ('кислота',) and True
            if w == 'кислота':
                done = True
            continue
        if w.endswith('ая'):
            out.append(w[:-2] + 'ой')
            continue
        if w.endswith('ый') or w.endswith('ий') and w not in NOUN_CASES:
            out.append(w[:-2] + ('ого' if case == 0 else 'ым'))
            continue
        if re.search(r'(ид|ат|ит|ор|ан)$', w):    # оксид, хлорид, сульфат, нитрит, фосфор…
            out.append(w + ('а' if case == 0 else 'ом'))
            done = True
            continue
        out.append(w)
        done = True
    return ' '.join(out)


def gen(f):
    return _decl(name(f), 0)


def ins(f):
    """Творительный падеж названия: «с оксидом кальция», «с соляной кислотой», «с медью»."""
    return _decl(name(f), 1)


# ================================================================= правила реакционной способности (генератор)
# R(a, b): True — реагируют, False — не реагируют, None — в школьном курсе спорно (в карточки не берём).

def _act_lt(m1, m2):
    """m1 левее m2 в ряду напряжений (активнее)."""
    return ACT[m1] < ACT[m2]


def _r_metal(m, y):
    k = kind(y)
    if k == 'metal':
        return False
    if k == 'nonmetal':
        t = {'O2': m != 'Ag', 'Cl2': None if m == 'Ag' else True, 'Br2': None if m == 'Ag' else True,
             'S': None if m == 'Ag' else True}
        if y in t:
            return t[y]
        if y == 'N2':
            return True if m in ('Li', 'Mg', 'Ca') else (False if m in ('Zn', 'Fe', 'Cu', 'Ag') else None)
        if y == 'H2':
            return True if m in REACTIVE_M else (None if m == 'Mg' else False)
        if y == 'P':
            return True if m in ('Mg', 'Ca') else None
        if y == 'C':
            return True if m in ('Ca', 'Al') else (False if m in ('Cu', 'Ag', 'Zn') else None)
        if y == 'Si':
            return True if m == 'Mg' else (False if m in ('Cu', 'Ag', 'Zn') else None)
    if k == 'water':
        return True if m in REACTIVE_M | {'Mg'} else (None if m in ('Al', 'Fe', 'Zn') else False)
    if k == 'nh3':
        return None
    if k in ('oxb', 'oxam', 'oxa', 'oxn'):
        if m in REACTIVE_M:
            return None
        if m in ('Cu', 'Ag'):
            if y == 'CuO':
                return None
            return False if y in OX_B + OX_AM + ['CO', 'CO2', 'SiO2', 'P2O5', 'NO'] else None
        if m == 'Mg':
            if y in ('CuO', 'FeO', 'Fe2O3', 'CO2', 'SiO2'):
                return True
            return False if y in OX_ACT + ['MgO'] else None
        if m == 'Al':
            if y in ('CuO', 'FeO', 'Fe2O3'):
                return True
            return False if y in OX_ACT + ['MgO', 'Al2O3'] else None
        # Zn, Fe
        if y in OX_ACT + ['MgO', 'Al2O3'] or (m == 'Fe' and y == 'ZnO') or (m == 'Zn' and y == 'ZnO'):
            return False
        return None
    if k == 'acid':
        if y in ('HCl', 'HBr', 'HI', 'H2SO4'):
            return _act_lt(m, 'H')
        if y == 'H3PO4':
            return True if m in ('Li', 'Na', 'K', 'Mg', 'Ca', 'Zn') else (False if m in ('Cu', 'Ag') else None)
        if y == 'HNO3':
            return True
        if y == 'H2S':
            return None
        if y == 'H2SiO3':
            return False if m in ('Cu', 'Ag', 'Fe', 'Zn', 'Al', 'Mg') else None
    if k == 'alk':
        if m in REACTIVE_M:
            return None
        if m in ('Al', 'Zn'):
            return True if y in ('NaOH', 'KOH') else None
        return False
    if k in ('bins', 'bamp'):
        return None if m in REACTIVE_M else False
    if k == 'salt':
        if m in REACTIVE_M:
            return None
        c, a, sol = SALT[y]
        cm = MET_OF[c]
        if sol != 'р':
            if cm and not _act_lt(m, cm):
                return False
            return None
        if c == 'NH4':
            return None if m in ('Mg', 'Zn', 'Al') else False
        if c == 'Fe3' or (m == 'Mg' and c == 'Al'):
            return None
        if m in ('Al', 'Zn') and a in ('CO3', 'S', 'SO3', 'SiO3', 'PO4'):
            return None
        if cm == m == 'Cu':
            return None
        if cm in REACTIVE_M or cm == m:
            return False
        return _act_lt(m, cm)
    return None


def _r_nonmetal(n, y):
    k = kind(y)
    if k == 'nonmetal':
        pair = frozenset((n, y))
        if n == y:
            return False
        yes = [{'H2', 'O2'}, {'H2', 'Cl2'}, {'H2', 'Br2'}, {'H2', 'S'}, {'H2', 'N2'}, {'O2', 'S'}, {'O2', 'P'},
               {'O2', 'C'}, {'O2', 'Si'}, {'O2', 'N2'}, {'Cl2', 'P'}, {'Cl2', 'Si'}]
        no = [{'O2', 'Cl2'}, {'O2', 'Br2'}, {'Cl2', 'C'}, {'Cl2', 'N2'}, {'S', 'N2'}, {'P', 'N2'}, {'C', 'N2'},
              {'Br2', 'N2'}, {'Br2', 'C'}]
        if any(pair == frozenset(p) for p in yes):
            return True
        if any(pair == frozenset(p) for p in no):
            return False
        return None
    if k == 'water':
        return True if n == 'Cl2' else (None if n in ('Br2', 'C') else False)
    if k == 'nh3':
        return True if n == 'O2' else (False if n in ('H2', 'N2') else None)
    if k in ('oxb', 'oxam', 'oxa', 'oxn'):
        if y == 'ZnO' and n in ('H2', 'C'):
            return None
        if n == 'H2':
            if y in ('CuO', 'FeO', 'Fe2O3'):
                return True
            return False if y in OX_ACT + ['MgO', 'Al2O3', 'CO2', 'SiO2', 'P2O5', 'SO3'] else None
        if n == 'C':
            if y in ('CuO', 'FeO', 'Fe2O3', 'ZnO', 'CO2'):
                return True
            return False if y == 'CO' else None
        if n == 'O2':
            if y in ('CO', 'NO', 'SO2', 'FeO'):
                return True
            return False if y in ('CO2', 'SO3', 'P2O5', 'SiO2', 'MgO', 'CaO', 'CuO', 'ZnO', 'Al2O3', 'Fe2O3') else None
        if n in ('Cl2', 'Br2'):
            return False if y in ('MgO', 'CuO', 'ZnO', 'Al2O3', 'Fe2O3', 'CO2', 'SiO2', 'P2O5', 'SO3') else None
        if n == 'S':
            return False if y in ('CO2', 'SiO2', 'P2O5', 'Al2O3', 'MgO', 'ZnO') else None
        if n == 'P':
            return False if y in ('CO2', 'SiO2', 'MgO', 'Al2O3') else None
        if n == 'N2':
            return False
        if n == 'Si':
            return False if y in ('MgO', 'Al2O3') else None
    if k == 'acid':
        if n in ('S', 'P', 'C'):
            if y == 'HNO3':
                return True
            if y == 'H2S':
                return None if n == 'P' else False
            return False
        if n == 'Cl2':
            return y in ('HBr', 'HI', 'H2S')
        if n == 'Br2':
            return y in ('HI', 'H2S')
        if n == 'O2':
            return True if y == 'H2S' else (None if y == 'HI' else False)
        return False  # H2, N2, Si
    if k in ('alk', 'bins', 'bamp'):
        if n == 'Cl2':
            return True if y in ('NaOH', 'KOH', 'Ca(OH)2') else None
        if n == 'Br2':
            return None
        if n == 'Si':
            return True if y in ('NaOH', 'KOH') else (False if k != 'alk' else None)
        if n in ('S', 'P'):
            return None if k == 'alk' else False
        if n == 'O2' and y == 'Fe(OH)2':
            return True
        return False
    if k == 'salt':
        c, a, sol = SALT[y]
        if n == 'Cl2':
            if c == 'NH4':
                return None
            if sol != 'р':
                return None
            if a in ('Br', 'I'):
                return True if c not in ('Fe2', 'Fe3') else None
            if y == 'FeCl2':
                return True
            if c == 'Fe3':
                return None
            if a == 'S':
                return True if c in ('Na', 'K') else None
            if c == 'Fe2' or a in ('CO3', 'SO3', 'SiO3', 'PO4'):
                return None
            return False
        if n == 'Br2':
            if c == 'NH4' or sol != 'р':
                return None
            if a == 'I':
                return True if c != 'Fe2' else None
            if c == 'Fe2' or a in ('S', 'SO3', 'CO3', 'SiO3', 'PO4'):
                return None
            return False
        if n == 'O2':
            if a in ('S', 'SO3') or c == 'Fe2':
                return None
            return False
        if n in ('H2', 'N2'):
            return False
        if n == 'C':
            return None if a in ('SO4', 'CO3', 'NO3') else False
        if n == 'S':
            return None if a in ('S', 'SO3') else False
        if n == 'P':
            return None if a == 'NO3' else False
        if n == 'Si':
            return None if a == 'CO3' else False
    return None


def _r_oxide(x, y):
    kx, ky = kind(x), kind(y)
    if kx == 'oxb' and x in OX_ACT:
        bx = 'act'
    else:
        bx = {'MgO': 'mgo', 'CuO': 'heavy', 'FeO': 'heavy', 'ZnO': 'amph', 'Al2O3': 'amph', 'Fe2O3': 'fe2o3'}.get(x, kx)
    if ky == 'water':
        if x == 'CO':
            return None
        if bx == 'act':
            return True
        if bx == 'mgo':
            return None
        if kx == 'oxa':
            return x != 'SiO2'
        return False
    if ky == 'nh3':
        if x == 'CuO':
            return True
        return False if x in ('MgO', 'CaO', 'Al2O3', 'ZnO') else None
    if ky in ('oxb', 'oxam', 'oxa', 'oxn'):
        if x == y:
            return False
        s = {x, y}
        basic = lambda f: f in OX_ACT or f == 'MgO'
        if (basic(x) and kind(y) == 'oxa') or (basic(y) and kind(x) == 'oxa'):
            other = y if basic(x) else x
            return None if other == 'NO2' else True
        if s in ({'Na2O', 'Al2O3'}, {'K2O', 'Al2O3'}, {'CaO', 'Al2O3'}, {'Na2O', 'ZnO'}, {'K2O', 'ZnO'}):
            return True
        if (s & set(OX_ACT + ['MgO'])) and (s & {'ZnO', 'Al2O3', 'Fe2O3'}):
            return None
        if 'CO' in s:
            other = (s - {'CO'}).pop()
            if other == 'ZnO':
                return None
            if other in ('CuO', 'FeO', 'Fe2O3'):
                return True
            if other in OX_ACT + ['MgO', 'Al2O3', 'CO2', 'SiO2', 'P2O5', 'SO3']:
                return False
            return None
        if 'NO' in s:
            other = (s - {'NO'}).pop()
            return None if other in ('NO2', 'SO2', 'SO3') else False
        if kind(x) == 'oxa' and kind(y) == 'oxa':
            return None if 'NO2' in s or s == {'SiO2', 'P2O5'} or s == {'SO2', 'SO3'} else False
        if s & {'CuO', 'FeO'} and s & set(OX_A):
            return None
        if s <= set(OX_B + OX_AM):
            return None if s & {'Fe2O3'} and s & set(OX_ACT) else False
        if s & {'ZnO', 'Al2O3', 'Fe2O3'} and s & set(OX_A):
            return None
        return None
    if ky == 'acid':
        if kx == 'oxa':
            if x == 'SO2' and y == 'H2S':
                return True
            if (x, y) in (('SO2', 'HNO3'), ('SO3', 'H2SO4'), ('P2O5', 'HNO3'), ('P2O5', 'H2SO4')) or x == 'NO2':
                return None
            return False
        if kx == 'oxn':
            return None if (x, y) == ('NO', 'HNO3') else False
        # основные и амфотерные оксиды
        if y in STRONG:
            if y == 'HI' and x in ('CuO', 'Fe2O3'):
                return None
            return True
        if y == 'H3PO4':
            return True if bx in ('act', 'mgo') and x != 'Li2O' else None
        if y == 'H2S':
            return True if x in ('Li2O', 'Na2O', 'K2O') else None
        if y == 'H2SiO3':
            return False if bx in ('heavy', 'amph', 'fe2o3') else None
    if ky == 'alk':
        if kx == 'oxa':
            if x == 'SiO2':
                return True if y in ('NaOH', 'KOH') else None
            if x == 'NO2':
                return True if y in ('NaOH', 'KOH') else None
            if y == 'LiOH' and x == 'CO2':
                return None
            if y == 'Ca(OH)2' and x in ('SO2', 'SO3', 'P2O5'):
                return None
            return True
        if kx == 'oxn':
            return None if x == 'CO' else False
        if bx == 'amph':
            return True if y in ('NaOH', 'KOH') else None
        if bx == 'fe2o3':
            return None
        return False
    if ky in ('bins', 'bamp'):
        if kx == 'oxa':
            return None
        if kx == 'oxn':
            return False
        if bx == 'act' and ky == 'bamp':
            return None
        return False
    if ky == 'salt':
        c, a, sol = SALT[y]
        if kx == 'oxn':
            return False
        if kx == 'oxa':
            if x == 'CO2':
                if a == 'SiO3' and sol == 'р':
                    return True
                return False if a in ('Cl', 'Br', 'I', 'NO3', 'SO4') else None
            if x == 'SiO2':
                if a == 'CO3' and c in ('Na', 'K', 'Ca'):
                    return True
                return False if a in ('Cl', 'Br', 'NO3', 'SO4') else None
            if x in ('SO2', 'P2O5'):
                if c == 'Fe3':
                    return None
                return False if a in ('Cl', 'Br', 'NO3', 'SO4') and sol == 'р' else None
            return None
        if c in ('Li', 'Na', 'K') and a in ('Cl', 'Br', 'I', 'NO3', 'SO4'):
            return False
        return None
    return None


def _electrolyte_cat_an(f):
    k = kind(f)
    if k == 'acid':
        return 'H', ACID[f]
    if k == 'alk':
        return ALK[f], 'OH'
    if k in ('bins', 'bamp'):
        return {**BINS, **BAMP}[f], 'OH'
    if k == 'salt':
        return SALT[f][0], SALT[f][1]
    return None


def _sol2(c, a):
    if c == 'H':
        return {'SiO3': 'н'}.get(a, 'р')
    if a == 'OH':
        return D.SOL.get((c, 'OH'))
    return D.SOL.get((c, a), '?')


def _r_ionic(x, y):
    """Кислоты, основания, соли между собой (реакции обмена, нейтрализация, вытеснение слабой кислоты)."""
    kx, ky = kind(x), kind(y)
    if x == y:
        return False
    # кислота + кислота
    if kx == 'acid' and ky == 'acid':
        s = {x, y}
        if s == {'HNO3', 'H2S'}:
            return True
        if s & {'HNO3', 'H2SO4'} and s & {'HI', 'HBr', 'H2S'}:
            return None
        return False
    # основание + основание
    if kx in ('alk', 'bins', 'bamp') and ky in ('alk', 'bins', 'bamp'):
        s = {x, y}
        if s & set(ALK) and s & set(BAMP):
            a = (s & set(ALK)).pop()
            return True if a in ('NaOH', 'KOH') else None
        if s & set(ALK) and 'Fe(OH)3' in s:
            return None
        return False
    # кислота + основание
    if {kx, ky} & {'acid'} and {kx, ky} & {'alk', 'bins', 'bamp'}:
        acid, base = (x, y) if kx == 'acid' else (y, x)
        kb = kind(base)
        if acid in STRONG:
            if acid == 'HI' and base in ('Cu(OH)2', 'Fe(OH)3'):
                return None
            return True
        if acid == 'H3PO4':
            return True if kb == 'alk' else None
        if acid == 'H2S':
            return True if base in ('NaOH', 'KOH', 'LiOH') else None
        if acid == 'H2SiO3':
            return True if base in ('NaOH', 'KOH') else (False if kb != 'alk' else None)
    # кислота + соль
    if {kx, ky} == {'acid', 'salt'}:
        acid, salt = (x, y) if kx == 'acid' else (y, x)
        c, a, sol = SALT[salt]
        an = ACID[acid]
        if acid == 'H2SiO3':
            return False
        if acid == 'H2S':
            if c in ('Cu', 'Ag') and sol == 'р':
                return True if salt in ('CuSO4', 'CuCl2', 'Cu(NO3)2', 'AgNO3') else None
            if c == 'Fe3' or a in ('CO3', 'SO3', 'SiO3', 'PO4', 'S') or sol != 'р':
                return None
            return False
        if a == an:
            return None if acid in ('H2SO4', 'H3PO4') else False
        if acid == 'HNO3' and (a in ('S', 'SO3', 'I', 'Br') or c == 'Fe2'):
            return None
        if acid == 'HI' and c in ('Cu', 'Fe3'):
            return None
        if acid == 'H2SO4' and a in ('I', 'Br'):
            return None
        if sol != 'р':
            if a in ('CO3', 'SO3'):
                if acid == 'H3PO4' or c == 'Ag':
                    return None
                if acid == 'H2SO4' and c in ('Ca', 'Ba'):
                    return None
                return True if _sol2(c, an) == 'р' else None
            if a == 'S':
                if c in ('Cu', 'Ag'):
                    return False if acid != 'HNO3' else None
                return True if acid != 'H3PO4' else None
            if a in ('PO4', 'SiO3'):
                return None
            return False   # AgCl, BaSO4 … с кислотами не реагируют
        if acid == 'H3PO4':
            if a in ('CO3', 'SO3', 'S'):
                return True if _sol2(c, 'PO4') in ('р', 'н') else None
            return None if c in ('Ag', 'Ba', 'Ca', 'Fe3', 'Al') else False
        if a in ('CO3', 'SO3', 'S', 'SiO3'):
            return True if _sol2(c, an) != 'м' else None
        if a == 'PO4':
            return None
        ps = _sol2(c, an)
        if ps == 'н':
            return True
        if ps in ('м', '-', '?'):
            return None
        return False
    # основание + соль
    if {kx, ky} & {'salt'} and {kx, ky} & {'alk', 'bins', 'bamp'}:
        base, salt = (x, y) if ky == 'salt' else (y, x)
        c, a, sol = SALT[salt]
        kb = kind(base)
        if kb != 'alk':
            if c in ('Li', 'Na', 'K', 'Ba', 'Ca') and a in ('Cl', 'Br', 'I', 'NO3', 'SO4'):
                return False
            return None
        bc = ALK[base]
        if sol != 'р':
            return False if salt in ('BaSO4', 'CaCO3', 'BaCO3') else None
        if c == bc:
            return False
        if c == 'NH4':
            return True if _sol2(bc, a) in ('р', 'н') else None
        p_base, p_salt = _sol2(c, 'OH'), _sol2(bc, a)
        if p_base in ('-', '?', 'м') or p_salt in ('-', '?', 'м'):
            return None
        return p_base == 'н' or p_salt == 'н'
    # соль + соль
    if kx == 'salt' and ky == 'salt':
        c1, a1, s1 = SALT[x]
        c2, a2, s2 = SALT[y]
        if s1 != 'р' or s2 != 'р':
            return None
        if c1 == c2 or a1 == a2:
            return False
        if ({c1, c2} & {'Fe3'} and {a1, a2} & {'I', 'S', 'SO3'}) or {c1, c2} == {'Ag', 'Fe2'}:
            return None
        p1, p2 = _sol2(c1, a2), _sol2(c2, a1)
        if p1 in ('-', '?', 'м') or p2 in ('-', '?', 'м'):
            return None
        return 'н' in (p1, p2)
    return None


def _r_small(x, y):
    """Вода и аммиак с кислотами, основаниями, солями."""
    kx, ky = kind(x), kind(y)
    if kx == 'water':
        if ky == 'water':
            return False
        if ky == 'nh3':
            return True
        if ky in ('acid', 'alk', 'bins', 'bamp'):
            return False
        if ky == 'salt':
            c, a, sol = SALT[y]
            if sol != 'р':
                return False
            return False if c in ('Li', 'Na', 'K', 'Ba', 'Ca', 'Mg') and a in ('Cl', 'Br', 'I', 'NO3', 'SO4') else None
    if kx == 'nh3':
        if ky == 'acid':
            return True if y in ('HCl', 'HBr', 'HNO3', 'H2SO4', 'H3PO4') else None
        if ky in ('alk', 'bins'):
            return False
        return None
    return None


RANK = {'metal': 0, 'nonmetal': 1, 'water': 2, 'nh3': 3, 'oxb': 4, 'oxam': 4, 'oxa': 4, 'oxn': 4, 'acid': 5,
        'alk': 6, 'bins': 6, 'bamp': 6, 'salt': 7}


DISPUTED = {frozenset((x, y)) for x, y, _ in D.DISPUTED}


def R(a, b):
    """Реагируют ли a и b (правила школьного курса). None — спорно (в т. ч. исключения D.DISPUTED)."""
    if frozenset((a, b)) in DISPUTED:
        return None
    ka, kb = kind(a), kind(b)
    if ka is None or kb is None:
        return None
    if RANK[ka] > RANK[kb]:
        a, b, ka, kb = b, a, kb, ka
    if ka == 'metal':
        return _r_metal(a, b)
    if ka == 'nonmetal':
        return _r_nonmetal(a, b)
    if ka in ('water', 'nh3'):
        if kb in ('oxb', 'oxam', 'oxa', 'oxn'):
            return _r_oxide(b, a)
        return _r_small(a, b)
    if ka in ('oxb', 'oxam', 'oxa', 'oxn'):
        return _r_oxide(a, b)
    return _r_ionic(a, b)


# ================================================================= база: поиск реакции заново по реагентам (для solve)

_PAIR = None


def _db_pairs():
    global _PAIR
    if _PAIR is None:
        _PAIR = {}
        for r in chemdb.load()['reactions']:
            L = r['lhs']
            if len(L) == 1:
                _PAIR.setdefault((L[0],), []).append(r)
                continue
            for i, x in enumerate(L):
                for y in L[i + 1:]:
                    if x != y and set(L) - {x, y} <= {'H2O'}:
                        _PAIR.setdefault(frozenset((x, y)), []).append(r)
            if len(L) == 2 and L[0] == L[1]:
                pass
    return _PAIR


def db_reactions(a, b, conc=False):
    """Реакции a с b из объединённой базы. conc=False — серная кислота разбавленная (без «конц.»)."""
    rs = _db_pairs().get(frozenset((a, b)), [])
    out = []
    for r in rs:
        c = r.get('cond', '') or ''
        if 'электролиз' in c or 'электролиз' in ' '.join(r.get('type', [])):
            continue
        is_conc = 'конц' in c or (r.get('form') or {}).get('H2SO4', '').startswith('конц')
        if 'H2SO4' in (a, b) and is_conc != conc:
            continue
        out.append(r)
    return out


def db_react(a, b):
    return bool(db_reactions(a, b))


def agrees(a, b):
    """Отбор вариантов с учётом ВСЕЙ объединённой базы: правило R и chemdb.load() должны давать одно и то же.
    Новая реакция в чужом модуле, противоречащая правилу, выключает пару до разбора (затем — D.DISPUTED)."""
    r = R(a, b)
    return r is not None and r == db_react(a, b)


# ================================================================= общее для карточек

def F(answer_format, style, level, time_min, scale, trap, kes, score):
    """Поля соответствия КИМ ОГЭ 2027 (см. BRIEF: главный критерий приёмки)."""
    return dict(answer_format=answer_format, style=style, level=level, time_min=time_min, scale=scale, trap=trap,
                kes=kes, score=score)


SC1 = '1 балл за полное совпадение с эталоном'
SC1M = '1 балл за полное совпадение; порядок цифр не важен'
SC2 = '2 балла; 1 балл, если на любой одной позиции записан не тот символ'
SEQ2 = 'две цифры в заданном порядке (сначала номер вещества первого класса, затем второго)'
MANY2 = 'две цифры (номера выбранных вариантов), порядок не важен'
MATCH3 = 'три цифры по буквам А, Б, В (соответствие), цифры могут повторяться'


def numbered(items):
    return '\n'.join(f'{i + 1}) {t}' for i, t in enumerate(items))


def shuffled(rng, xs):
    xs = list(xs)
    rng.shuffle(xs)
    return xs


def ids_of(indices):
    return [str(i + 1) for i in sorted(indices)]


# ================================================================= 7. Классификация неорганических веществ

METALS_ALL = {'Li', 'Na', 'K', 'Rb', 'Cs', 'Be', 'Mg', 'Ca', 'Sr', 'Ba', 'Al', 'Zn', 'Fe', 'Cu', 'Ag', 'Mn', 'Cr', 'Ni',
              'Pb', 'Sn', 'Hg', 'Co'}


def classify(f):
    """Классы вещества по формуле (правила школьной номенклатуры) — независимая проверка задания 7."""
    if f in ('H2O', 'NH3', 'PH3', 'NCl3', 'CH4', 'H2O2', 'Na2O2', 'CaH2', 'NaH'):
        return {'другое'}
    el = parse_formula(f)
    els = set(el)
    if len(els) == 1:
        return {'простое вещество'}
    m = re.match(r'^([A-Z][a-z]?)\d*\(OH\)\d$|^([A-Z][a-z]?)OH$', f)
    if m:
        me = m.group(1) or m.group(2)
        if me in ('Li', 'Na', 'K', 'Rb', 'Cs', 'Ca', 'Sr', 'Ba'):
            return {'основание', 'щёлочь'}
        n_oh = int(re.search(r'\(OH\)(\d)$', f).group(1)) if '(OH)' in f else 1
        if me in ('Zn', 'Be', 'Al', 'Cr') or (me == 'Fe' and n_oh == 3):
            return {'амфотерный гидроксид'}
        return {'основание', 'нерастворимое основание'}
    if f.startswith('H') and not f.startswith('Hg') and not (els & METALS_ALL):
        return {'кислота', 'кислородсодержащая кислота' if 'O' in els else 'бескислородная кислота'}
    if els - {'O'} and len(els) == 2 and 'O' in els and f.endswith(('O', 'O2', 'O3', 'O5', 'O7')):
        e = (els - {'O'}).pop()
        ox = Fr(2 * el['O'], el[e])
        if e in METALS_ALL:
            if e in ('Zn', 'Be', 'Al', 'Pb', 'Sn') or (e == 'Cr' and ox == 3):
                return {'оксид', 'амфотерный оксид'}
            if ox >= 5:
                return {'оксид', 'кислотный оксид'}
            if ox <= 2:
                return {'оксид', 'основный оксид'}
            return {'оксид'}
        if (e, ox) in (('C', 2), ('N', 2), ('N', 1), ('Si', 2)):
            return {'оксид', 'несолеобразующий оксид'}
        return {'оксид', 'кислотный оксид'}
    if els & METALS_ALL or f.startswith('NH4') or f.startswith('(NH4)'):
        body = re.sub(r'^\(?NH4\)?\d*', '', f)
        body = re.sub(r'^\(?(' + '|'.join(sorted(METALS_ALL, key=len, reverse=True)) + r')\d*', '', body)
        if body.startswith('H') or body.startswith('(H'):
            return {'соль', 'кислая соль'}
        if 'OH' in body or (f.startswith('(') and 'OH)' in f):
            return {'соль', 'основная соль'}
        return {'соль', 'средняя соль'}
    return {'другое'}


# класс: (вин. падеж для «выберите …», род. падеж для «номер …», формулы)
CLS7 = {
    'кислотный оксид': ('кислотный оксид', 'кислотного оксида',
                        ['CO2', 'SO2', 'SO3', 'P2O5', 'P2O3', 'SiO2', 'N2O5', 'N2O3', 'Cl2O7', 'Mn2O7', 'CrO3']),
    'основный оксид': ('основный оксид', 'основного оксида',
                       ['Li2O', 'Na2O', 'K2O', 'MgO', 'CaO', 'BaO', 'FeO', 'CuO', 'MnO', 'SrO']),
    'амфотерный оксид': ('амфотерный оксид', 'амфотерного оксида', ['ZnO', 'Al2O3', 'BeO', 'Cr2O3']),
    'несолеобразующий оксид': ('несолеобразующий оксид', 'несолеобразующего оксида', ['CO', 'NO', 'N2O']),
    'кислота': ('кислоту', 'кислоты', ['HCl', 'HBr', 'HI', 'HF', 'H2S', 'HNO3', 'HNO2', 'H2SO4', 'H2SO3', 'H3PO4',
                                       'H2CO3', 'H2SiO3', 'HClO4']),
    'щёлочь': ('щёлочь', 'щёлочи', ['LiOH', 'NaOH', 'KOH', 'Ba(OH)2', 'Ca(OH)2', 'Sr(OH)2']),
    'нерастворимое основание': ('нерастворимое основание', 'нерастворимого основания',
                                ['Mg(OH)2', 'Cu(OH)2', 'Fe(OH)2', 'Mn(OH)2', 'Ni(OH)2']),
    'основание': ('основание', 'основания', ['LiOH', 'NaOH', 'KOH', 'Ba(OH)2', 'Ca(OH)2', 'Mg(OH)2', 'Cu(OH)2',
                                            'Fe(OH)2', 'Mn(OH)2']),
    'амфотерный гидроксид': ('амфотерный гидроксид', 'амфотерного гидроксида', ['Zn(OH)2', 'Al(OH)3', 'Be(OH)2', 'Cr(OH)3',
                                                                           'Fe(OH)3']),
    'соль': ('соль', 'соли', ['NaCl', 'K2SO4', 'CaCO3', 'MgSO4', 'Na3PO4', 'KNO3', 'BaCl2', 'CuSO4', 'Fe2(SO4)3',
                              'Al(NO3)3', 'ZnCl2', 'Na2SiO3', 'K2S', 'NH4Cl', 'AgNO3', 'Na2SO3', 'CaCl2', 'FeCl3',
                              'KMnO4', 'NaNO2', 'Li2SO4', '(NH4)2SO4', 'MgCO3', 'NaAlO2', 'K2CrO4', 'BaSO4']),
    'кислая соль': ('кислую соль', 'кислой соли', ['NaHCO3', 'KHCO3', 'Ca(HCO3)2', 'NaHSO4', 'KHSO4', 'NaH2PO4', 'K2HPO4']),
}
OTHER7 = ['NH3', 'PH3', 'NCl3', 'CH4']


def _cls_member(f, c):
    """Принадлежит ли f классу c по полю cls/sub базы (генератор)."""
    s = SUB.get(f, {})
    cls, sub = s.get('cls', ''), s.get('sub', '')
    if c.split()[-1] == 'оксид' and cls == 'оксид':
        return sub == c.split()[0].replace('основный', 'основный')
    if c == 'кислота':
        return cls == 'кислота'
    if c == 'щёлочь':
        return cls == 'основание' and sub == 'щёлочь'
    if c == 'нерастворимое основание':
        return cls == 'основание' and sub == 'нерастворимое'
    if c == 'основание':
        return cls == 'основание' and sub in ('щёлочь', 'нерастворимое')
    if c == 'амфотерный гидроксид':
        return cls == 'амфотерный гидроксид'
    if c == 'соль':
        return cls == 'соль'
    if c == 'кислая соль':
        return cls == 'соль' and sub == 'кислая'
    return False


ALL7 = sorted({f for v in CLS7.values() for f in v[2]} | set(OTHER7))
PAIRS7 = {
    'ox': [('кислотный оксид', 'основный оксид'), ('основный оксид', 'кислотный оксид'),
           ('амфотерный оксид', 'кислотный оксид'), ('кислотный оксид', 'амфотерный оксид'),
           ('основный оксид', 'амфотерный оксид'), ('амфотерный оксид', 'основный оксид'),
           ('несолеобразующий оксид', 'кислотный оксид'), ('кислотный оксид', 'несолеобразующий оксид'),
           ('несолеобразующий оксид', 'основный оксид'), ('основный оксид', 'несолеобразующий оксид'),
           ('амфотерный оксид', 'несолеобразующий оксид')],
    'hydr': [('основание', 'кислота'), ('кислота', 'основание'), ('щёлочь', 'кислота'), ('кислота', 'щёлочь'),
             ('щёлочь', 'амфотерный гидроксид'), ('амфотерный гидроксид', 'щёлочь'),
             ('кислота', 'амфотерный гидроксид'), ('амфотерный гидроксид', 'кислота'),
             ('нерастворимое основание', 'кислота'), ('нерастворимое основание', 'амфотерный гидроксид'),
             ('щёлочь', 'нерастворимое основание')],
    'mix': [('кислотный оксид', 'соль'), ('соль', 'кислотный оксид'), ('основный оксид', 'соль'),
            ('соль', 'щёлочь'), ('щёлочь', 'соль'), ('кислота', 'соль'), ('соль', 'кислота'),
            ('основный оксид', 'кислота'), ('кислота', 'кислотный оксид'), ('основание', 'кислотный оксид'),
            ('кислотный оксид', 'основание'), ('амфотерный оксид', 'соль'), ('соль', 'амфотерный гидроксид'),
            ('кислая соль', 'кислота'), ('щёлочь', 'кислая соль'), ('основный оксид', 'основание'),
            ('амфотерный оксид', 'кислота'), ('амфотерный гидроксид', 'соль'), ('несолеобразующий оксид', 'соль')],
}
ENDS7 = ['Запишите в поле ответа номера выбранных веществ: сначала номер {a}, затем — номер {b}.']
STEMS7 = ['Из предложенного перечня веществ выберите {a} и {b}.']


def _gen7(rng, fam):
    ca, cb = rng.choice(PAIRS7[fam])
    fa = rng.choice(CLS7[ca][2])
    fb = rng.choice(CLS7[cb][2])
    pool = [f for f in ALL7 if f not in (fa, fb) and not _cls_member(f, ca) and not _cls_member(f, cb)
            and not ({'основание', 'щёлочь', 'нерастворимое основание'} & {ca, cb} and SUB.get(f, {}).get('cls') == 'основание')
            and not ({'соль', 'кислая соль'} & {ca, cb} and SUB.get(f, {}).get('cls') == 'соль')]
    # отвлекающие — из других классов, по возможности похожие (оксиды к оксидам, гидроксиды к гидроксидам)
    near = [f for f in pool if (fam == 'ox' and SUB.get(f, {}).get('cls') == 'оксид') or
            (fam == 'hydr' and SUB.get(f, {}).get('cls') in ('основание', 'амфотерный гидроксид', 'кислота'))]
    k_near = min(len(near), rng.choice([1, 2, 2, 3]))
    dist = rng.sample(near, k_near) if k_near else []
    rest = [f for f in pool if f not in dist]
    dist += rng.sample(rest, 3 - len(dist))
    items = shuffled(rng, [fa, fb] + dist)
    ia, ib = items.index(fa) + 1, items.index(fb) + 1
    stem = rng.choice(STEMS7).format(a=CLS7[ca][0], b=CLS7[cb][0])
    end = rng.choice(ENDS7).format(a=CLS7[ca][1], b=CLS7[cb][1])
    q = f'{stem}\n{numbered([disp(f) for f in items])}\n{end}'
    ans = f'{ia}{ib}'
    e = (f'{disp(fa)} — {ca}, {disp(fb)} — {cb}. Остальные: ' +
         '; '.join(f'{disp(f)} — {_cls_word(f)}' for f in dist) + f'. Ответ: {ans}.')
    return pcard(PID7[fam], q, ans, e, k='num', p={'items': items, 'ca': ca, 'cb': cb},
                 wrong=[f'{ib}{ia}'] + [f'{ia}{j + 1}' for j in range(5) if j + 1 not in (ia, ib)][:2])


def _cls_word(f):
    s = SUB.get(f, {})
    cls, sub = s.get('cls', ''), s.get('sub', '')
    if cls == 'оксид':
        return f'{sub} оксид'.replace('основный', 'основный')
    if cls == 'основание':
        return 'щёлочь' if sub == 'щёлочь' else 'нерастворимое основание'
    if cls == 'соль':
        return 'кислая соль' if sub == 'кислая' else 'соль'
    if cls in ('кислота', 'амфотерный гидроксид'):
        return cls
    return 'не относится к этим классам'


def _solve7(p):
    items = p['items']
    ia = [i for i, f in enumerate(items) if p['ca'] in classify(f)]
    ib = [i for i, f in enumerate(items) if p['cb'] in classify(f)]
    if len(ia) != 1 or len(ib) != 1:
        return f'неоднозначно {ia} {ib}'
    return f'{ia[0] + 1}{ib[0] + 1}'


PID7 = {'ox': 'ch-oge-07-oxides', 'hydr': 'ch-oge-07-hydroxides', 'mix': 'ch-oge-07-mixed'}
_F7 = lambda scale: F(SEQ2, 'как в демоверсии 2027 №7: «Из предложенного перечня веществ выберите X и Y», пять формул, '
                             'ответ — номера в указанном порядке', 'Б', 3, scale,
                      'перепутать порядок записи; принять несолеобразующий оксид за кислотный, амфотерный — за основный, '
                      'кислую соль — за кислоту, нерастворимое основание — за щёлочь', ['4.1'], SC1)


@proto('ch-oge-07-oxides', 'ОГЭ', 7, 'Классификация: выбрать оксиды двух видов (кислотный, основный, амфотерный, несолеобразующий)',
       invariant='пять формул; выбрать оксиды двух заданных видов и записать номера в заданном порядке',
       varies='пара видов оксидов и их порядок, конкретные оксиды, отвлекающие вещества',
       answer_rule='вид оксида — по элементу и степени окисления: металл +1/+2 — основный (кроме Zn, Be), Zn, Al, Be, '
                   'Cr(+3) — амфотерный, неметалл — кислотный, CO, NO, N2O — несолеобразующие',
       mistakes=['CO и NO считают кислотными', 'ZnO и Al2O3 считают основными', 'записывают номера в обратном порядке'],
       solve=_solve7, kind='dict', kes=['4.1'],
       fidelity=_F7('оксиды из банка ФИПИ (задания 4.1): CO2, SO3, P2O5, SiO2, Na2O, BaO, FeO, ZnO, Al2O3, CO, NO'))
def g7_ox(rng):
    return _gen7(rng, 'ox')


@proto('ch-oge-07-hydroxides', 'ОГЭ', 7, 'Классификация: основание/щёлочь, амфотерный гидроксид, кислота',
       invariant='пять формул; выбрать вещества двух заданных классов гидроксидов/кислот, номера в заданном порядке',
       varies='пара классов (щёлочь, нерастворимое основание, амфотерный гидроксид, кислота), вещества, отвлекающие',
       answer_rule='щёлочи — растворимые гидроксиды Li, Na, K, Ca, Sr, Ba; Zn(OH)2, Al(OH)3, Be(OH)2, Cr(OH)3, Fe(OH)3 — '
                   'амфотерные (кодификатор 2027, 4.7); '
                   'кислота — водород + кислотный остаток',
       mistakes=['Cu(OH)2 или Mg(OH)2 считают щёлочью', 'Al(OH)3 считают основанием', 'H2O или NH3 принимают за кислоту/основание'],
       solve=_solve7, kind='dict', kes=['4.1'],
       fidelity=_F7('вещества банка: LiOH, NaOH, Ba(OH)2, Cu(OH)2, Fe(OH)2, Zn(OH)2, Al(OH)3, H2S, HNO3, H2SO4'))
def g7_hydr(rng):
    return _gen7(rng, 'hydr')


@proto('ch-oge-07-mixed', 'ОГЭ', 7, 'Классификация: вещества разных классов (оксид, основание, кислота, соль)',
       invariant='пять формул разных классов; выбрать два вещества заданных классов, номера в заданном порядке',
       varies='пара классов (оксид/основание/кислота/соль/кислая соль), вещества, отвлекающие',
       answer_rule='класс — по составу: оксид (Э + O), основание (металл + OH), кислота (H + кислотный остаток), '
                   'соль (металл/NH4 + кислотный остаток; с H в остатке — кислая)',
       mistakes=['NaHCO3 принимают за кислоту', 'NH4Cl не считают солью', 'путают порядок номеров'],
       solve=_solve7, kind='dict', kes=['4.1'],
       fidelity=_F7('вещества банка: K2CO3, NaAlO2, MgCO3, CaCl2, Cl2O7, Ca(OH)2, NH3, HClO4'))
def g7_mix(rng):
    return _gen7(rng, 'mix')


SAME7 = ['основный оксид', 'кислотный оксид', 'амфотерный оксид', 'несолеобразующий оксид', 'щёлочь',
         'нерастворимое основание', 'амфотерный гидроксид', 'кислая соль']
PLUR7 = {'основный оксид': 'два основных оксида', 'кислотный оксид': 'два кислотных оксида',
         'амфотерный оксид': 'два амфотерных оксида', 'несолеобразующий оксид': 'два несолеобразующих оксида',
         'щёлочь': 'две щёлочи', 'нерастворимое основание': 'два нерастворимых основания',
         'амфотерный гидроксид': 'два амфотерных гидроксида', 'кислая соль': 'две кислые соли'}


def _solve7same(p):
    return ids_of([i for i, f in enumerate(p['items']) if p['c'] in classify(f)])


@proto('ch-oge-07-same-class', 'ОГЭ', 7, 'Классификация: выбрать два вещества одного класса',
       invariant='пять формул; выбрать две формулы веществ одного заданного класса (порядок не важен)',
       varies='класс (виды оксидов, щёлочи, нерастворимые основания, амфотерные гидроксиды, кислые соли), вещества',
       answer_rule='признаки класса — как в ch-oge-07-oxides / -hydroxides / -mixed',
       mistakes=['амфотерный оксид считают основным', 'Ca(OH)2 не считают щёлочью', 'NO считают кислотным оксидом'],
       solve=_solve7same, kind='dict', kes=['4.1'],
       fidelity=F(MANY2, 'как в заданиях банка 4.1 «выберите два основных оксида / две щёлочи»', 'Б', 3,
                  'формулы из пулов задания 7 (как в банке)', 'соседние классы как отвлекающие', ['4.1'], SC1M))
def g7_same(rng):
    c = rng.choice(SAME7)
    two = rng.sample(CLS7[c][2], 2)
    pool = [f for f in ALL7 if not _cls_member(f, c) and f not in two]
    if c in ('щёлочь', 'нерастворимое основание'):
        pool = [f for f in pool if SUB.get(f, {}).get('cls') != 'основание' or f in CLS7[
            'щёлочь' if c == 'нерастворимое основание' else 'нерастворимое основание'][2]]
    near_cls = 'оксид' if 'оксид' in c else None
    near = [f for f in pool if near_cls and SUB.get(f, {}).get('cls') == near_cls] or \
           [f for f in pool if SUB.get(f, {}).get('cls') in ('основание', 'амфотерный гидроксид', 'соль')]
    dist = rng.sample(near, 2) + []
    dist += rng.sample([f for f in pool if f not in dist], 1)
    items = shuffled(rng, two + dist)
    o = opts([disp(f) for f in items])
    a = ids_of([items.index(f) for f in two])
    q = rng.choice(['Из предложенного перечня веществ выберите {x}.']
                   ).format(x=PLUR7[c]) + ' Запишите номера выбранных ответов.'
    e = f'{disp(two[0])} и {disp(two[1])} относятся к одному классу: {c}. ' + \
        '; '.join(f'{disp(f)} — {_cls_word(f)}' for f in dist) + f'. Ответ: {"".join(a)}.'
    return pcard('ch-oge-07-same-class', q, a, e, k='many', o=o, p={'items': items, 'c': c})


# ================================================================= 8. Какие два вещества реагируют (не реагируют) с X

INS_OK = {'Ca3(PO4)2', 'CaCO3', 'BaCO3', 'MgCO3', 'BaSO4', 'AgCl', 'AgBr', 'AgI', 'FeS', 'CuS', 'ZnS', 'BaSO3',
          'CaSO3', 'Mg3(PO4)2', 'Zn3(PO4)2', 'CaSiO3'}
COMMON_SALTS = sorted(f for f, (c, a, v) in SALT.items() if (v == 'р' and a not in ('SiO3',) or f in INS_OK)
                      and not (c in ('Fe2', 'Fe3') and a in ('SO3', 'CO3', 'S', 'PO4', 'SiO3'))) + ['Na2SiO3', 'K2SiO3']
REAGENTS = METALS + NONMET + ['H2O', 'NH3'] + OX_B + OX_AM + OX_A + OX_N + list(ACID) + list(ALK) + list(BINS) + \
    list(BAMP) + COMMON_SALTS
CONC_SENS = {'Cu', 'Ag', 'C', 'S', 'P', 'Fe', 'Al', 'Zn', 'Mg'}


def disp_r(f, x=None, names=False):
    """Реагент в списке: формула (или название); у серной кислоты при «чувствительных» X — пометка «разб.»."""
    t = name(f) if names else disp(f)
    if f == 'H2SO4' and x in CONC_SENS:
        t += ' (разб.)'
    return t


def _kind_group(f):
    k = kind(f)
    return {'oxb': 'ox', 'oxam': 'ox', 'oxa': 'ox', 'oxn': 'ox', 'bins': 'base', 'bamp': 'base', 'alk': 'base',
            'water': 'hyd', 'nh3': 'hyd'}.get(k, k)


def _pick_diverse(rng, cands, k, taken=(), maxper=2):
    """k веществ из cands, не больше maxper из одной группы (металлы, неметаллы, оксиды, кислоты, основания, соли);
    соли с одинаковым катионом не повторяются."""
    cnt = Counter(_kind_group(f) for f in taken)
    cats = {CAT_OF_SALT[f] for f in taken if f in CAT_OF_SALT}
    out = []
    for f in shuffled(rng, cands):
        g = _kind_group(f)
        if cnt[g] >= maxper or f in taken or f in out or CAT_OF_SALT.get(f, '-') in cats:
            continue
        out.append(f)
        cnt[g] += 1
        if f in CAT_OF_SALT:
            cats.add(CAT_OF_SALT[f])
        if len(out) == k:
            return out
    raise Retry


def _eq_of(a, b, conc=False):
    rs = db_reactions(a, b, conc)
    if not rs:
        return None
    r = rs[0]
    return (r['lhs'], r['rhs'], r['k'][0], r['k'][1])


def eq_text(eq):
    lhs, rhs, kl, kr = eq
    side = lambda ss, ks: ' + '.join((f'{k}' if k > 1 else '') + disp(s) for s, k in zip(ss, ks))
    return f'{side(lhs, kl)} = {side(rhs, kr)}'


METALS8 = ['Li', 'Na', 'K', 'Mg', 'Ca', 'Al', 'Fe']     # простые вещества-металлы плана №8 (КЭС 4.3)
NONMET8 = ['H2', 'O2', 'Cl2', 'S', 'P', 'C', 'N2', 'Si']  # простые вещества-неметаллы плана №8 (КЭС 4.2)
STEM8 = ['Какие два из перечисленных веществ вступают в реакцию с {i}?']
STEM8N = ['Какие два из перечисленных веществ не взаимодействуют с {i}?']


def _gen8(rng, pid, xs):
    x = rng.choice(xs)
    neg = rng.random() < 0.3
    cands = [y for y in REAGENTS if y != x and R(x, y) is not None and y not in REACTIVE_M and agrees(x, y)]
    yes = [y for y in cands if R(x, y)]
    no = [y for y in cands if R(x, y) is False]
    if len(yes) < 3 or len(no) < 3:
        raise Retry
    right = _pick_diverse(rng, yes if not neg else no, 2, maxper=1)
    other = _pick_diverse(rng, no if not neg else yes, 3, taken=right)
    items = shuffled(rng, right + other)
    names = rng.random() < 0.2
    o = opts([disp_r(f, x, names) for f in items])
    a = ids_of([items.index(f) for f in right])
    stem = rng.choice(STEM8N if neg else STEM8).format(n=name(x), i=ins(x))
    q = stem + ' Запишите номера выбранных ответов.'
    reacting = [f for f in items if R(x, f)]
    eqs = [e for e in (_eq_of(x, f) for f in reacting) if e]
    e = (f'{cap(name(x))} реагирует с ' + ', '.join(disp(f) for f in reacting) + ': ' +
         '; '.join(eq_text(eq) for eq in eqs) + '. С ' + ', '.join(disp(f) for f in items if f not in reacting) +
         ' не реагирует.' + f' Ответ: {"".join(a)}.')
    return pcard(pid, q, a, e, k='many', o=o, p={'x': x, 'items': items, 'neg': neg}, eqs=eqs)


def _solve8(p):
    x = p['x']
    return ids_of([i for i, f in enumerate(p['items']) if db_react(x, f) != p['neg']])


_F8 = lambda scale, trap: F(MANY2, 'как в демоверсии 2027 №8 и банке: «Какие два из перечисленных веществ (не) '
                                   'реагируют с X?», пять формул', 'Б', 3, scale, trap, ['4.2', '4.3', '4.5', '4.6'], SC1M)


@proto('ch-oge-08-metal', 'ОГЭ', 8, 'Химические свойства металла: с какими двумя веществами реагирует (не реагирует)',
       invariant='металл X и пять веществ разных классов; выбрать два, с которыми X реагирует (или не реагирует)',
       varies='металл из плана №8 (Li, Na, K, Mg, Ca, Al, Fe), набор веществ, вопрос «реагирует/не реагирует»',
       answer_rule='ряд напряжений: металл до H вытесняет водород из кислот-неокислителей, более активный металл вытесняет '
                   'менее активный из раствора соли; Al, Zn реагируют со щелочами; с HNO3 реагируют и металлы после H',
       mistakes=['медь «реагирует» с соляной кислотой', 'железо «вытесняет» цинк из соли', 'забывают реакцию Al со щёлочью'],
       solve=_solve8, kind='dict', kes=['4.3'],
       fidelity=_F8('металлы и реагенты банка: литий, магний, железо, алюминий с кислотами, солями, неметаллами',
                    'ряд напряжений, пассивные металлы, амфотерность Al/Zn'))
def g8_metal(rng):
    return _gen8(rng, 'ch-oge-08-metal', METALS8)


@proto('ch-oge-08-nonmetal', 'ОГЭ', 8, 'Химические свойства неметалла: с какими двумя веществами реагирует (не реагирует)',
       invariant='неметалл X и пять веществ; выбрать два, с которыми X реагирует (или не реагирует)',
       varies='неметалл из плана №8 (H2, O2, Cl2, S, P, C, N2, Si), набор веществ, вопрос «реагирует/не реагирует»',
       answer_rule='водород и углерод восстанавливают оксиды малоактивных металлов; галогены вытесняют менее активные '
                   'галогены из солей; S, P, C окисляются азотной кислотой; кислород не реагирует с высшими оксидами',
       mistakes=['кислород «реагирует» с CO2 или SO3', 'водород «восстанавливает» MgO', 'хлор «вытесняет» что-то из хлоридов'],
       solve=_solve8, kind='dict', kes=['4.2'],
       fidelity=_F8('неметаллы банка: хлор, сера, фосфор, азот, водород, кислород, уголь',
                    'высшие оксиды не горят; оксиды активных металлов не восстанавливаются водородом'))
def g8_nonmetal(rng):
    return _gen8(rng, 'ch-oge-08-nonmetal', NONMET8)


@proto('ch-oge-08-basic-oxide', 'ОГЭ', 8, 'Химические свойства оснóвного оксида',
       invariant='оснóвный оксид X и пять веществ; выбрать два, с которыми X реагирует (или не реагирует)',
       varies='оксид (Li2O, Na2O, K2O, CaO, BaO, MgO, CuO, FeO), набор веществ, вопрос',
       answer_rule='оснóвный оксид реагирует с кислотами и кислотными оксидами; оксиды щелочных и щёлочноземельных '
                   'металлов — с водой; CuO, FeO восстанавливаются H2, C, CO; со щелочами и оснóвными оксидами не реагирует',
       mistakes=['CuO «реагирует» с водой', 'оксид кальция «реагирует» со щёлочью', 'не замечают реакцию с кислотным оксидом'],
       solve=_solve8, kind='dict', kes=['4.6'],
       fidelity=_F8('оксиды банка: CaO, MgO, Na2O, K2O, Li2O, CuO, FeO', 'вода реагирует только с оксидами активных металлов'))
def g8_boxide(rng):
    return _gen8(rng, 'ch-oge-08-basic-oxide', OX_B)


@proto('ch-oge-08-acid-oxide', 'ОГЭ', 8, 'Химические свойства кислотного (несолеобразующего) оксида',
       invariant='кислотный или несолеобразующий оксид X и пять веществ; выбрать два, с которыми X реагирует (не реагирует)',
       varies='оксид (CO2, SO2, SO3, P2O5, SiO2, NO2, CO, NO), набор веществ, вопрос',
       answer_rule='кислотный оксид реагирует со щелочами, оснóвными оксидами, водой (кроме SiO2); SO2 и CO окисляются '
                   'кислородом; CO восстанавливает оксиды металлов; с кислотами и кислотными оксидами не реагирует',
       mistakes=['SiO2 «реагирует» с водой', 'CO2 «реагирует» с кислотой', 'CO считают кислотным оксидом'],
       solve=_solve8, kind='dict', kes=['4.5'],
       fidelity=_F8('оксиды банка: SO2, SO3, P2O5, CO2, SiO2, оксид азота(III)', 'SiO2 не реагирует с водой; CO — несолеобразующий'))
def g8_aoxide(rng):
    return _gen8(rng, 'ch-oge-08-acid-oxide', OX_A + OX_N)


@proto('ch-oge-08-amph-oxide', 'ОГЭ', 8, 'Химические свойства амфотерного оксида',
       invariant='амфотерный оксид X и пять веществ; выбрать два, с которыми X реагирует (не реагирует)',
       varies='оксид (ZnO, Al2O3, Fe2O3), набор веществ, вопрос',
       answer_rule='амфотерный оксид реагирует и с кислотами, и со щелочами; ZnO и Fe2O3 восстанавливаются H2, C, CO; '
                   'с водой не реагирует',
       mistakes=['Al2O3 «реагирует» с водой', 'забывают реакцию со щёлочью', 'Al2O3 «восстанавливают» водородом'],
       solve=_solve8, kind='dict', kes=['4.6'],
       fidelity=_F8('оксиды банка: ZnO, Al2O3, Fe2O3', 'амфотерность: реакция со щёлочью'))
def g8_amoxide(rng):
    return _gen8(rng, 'ch-oge-08-amph-oxide', OX_AM)


# ================================================================= 10. Вещество → два реагента

STEM10 = ['Установите соответствие между веществом и реагентами, с каждым из которых это вещество может вступать '
          'в реакцию: к каждой позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой.']
END_M = ' Запишите в таблицу выбранные цифры под соответствующими буквами.'


def _gen10(rng, pid, groups, names=False):
    subs = [rng.choice(g) for g in groups]
    if len(set(subs)) < 3:
        raise Retry
    cands = [y for y in REAGENTS if y not in subs and all(R(s, y) is not None and agrees(s, y) for s in subs)]
    T = [[y for y in cands if R(s, y)] for s in subs]
    pairs = []
    used = set()
    for i, s in enumerate(subs):
        ok = False
        for _ in range(40):
            if len(T[i]) < 2:
                raise Retry
            p = rng.sample(T[i], 2)
            if set(p) & used or _kind_group(p[0]) == _kind_group(p[1]) and rng.random() < 0.6:
                continue
            if any(j != i and all(R(subs[j], y) for y in p) for j in range(3)):
                continue
            pairs.append(p)
            used |= set(p)
            ok = True
            break
        if not ok:
            raise Retry
    for _ in range(60):
        p = rng.sample(cands, 2)
        if set(p) & used or any(all(R(s, y) for y in p) for s in subs):
            continue
        pairs.append(p)
        break
    else:
        raise Retry
    order = shuffled(rng, range(4))
    right = [pairs[k] for k in order]
    left_t = [name(s) if names else disp(s) for s in subs]
    right_t = [', '.join(disp_r(y, s) for y in p) for p in right]
    o = match_opts(left_t, right_t)
    a = {LET[i]: str(order.index(i) + 1) for i in range(3)}
    q = rng.choice(STEM10) + END_M
    eqs = [e for i, s in enumerate(subs) for e in (_eq_of(s, y) for y in pairs[i]) if e]
    e = ' '.join(f'{LET[i]}) {disp(s)} реагирует с {disp(pairs[i][0])} и {disp(pairs[i][1])}.' for i, s in enumerate(subs)) + \
        ' Уравнения: ' + '; '.join(eq_text(x) for x in eqs) + '. Ответ: ' + ''.join(a[x] for x in LET[:3]) + '.'
    return pcard(pid, q, a, e, k='match', o=o, p={'subs': subs, 'pairs': right}, eqs=eqs)


def _solve10(p):
    a = {}
    for i, s in enumerate(p['subs']):
        ok = [j for j, pr in enumerate(p['pairs']) if all(db_react(s, y) for y in pr)]
        if len(ok) != 1:
            return f'неоднозначно {s}: {ok}'
        a[LET[i]] = str(ok[0] + 1)
    return a


_F10 = lambda scale: F(MATCH3 + ' (3 вещества, 4 пары реагентов)', 'как в демоверсии 2027 №10: «вещество — реагенты, '
                       'с каждым из которых оно может вступать в реакцию»', 'П', 7, scale,
                       'в неверных парах один реагент подходит, второй — нет', ['4.2', '4.3', '4.4', '4.5', '4.6', '4.7',
                                                                            '4.8', '4.9'], SC2)
SIMPLE10 = [METALS, NONMET]
OXIDES10 = [OX_B, OX_AM, OX_A]
COMP10 = [list(ACID)[:6], list(ALK), COMMON_SALTS]


@proto('ch-oge-10-simple-oxide-salt', 'ОГЭ', 10, 'Вещество → реагенты: простое вещество, оксид, сложное вещество',
       invariant='три вещества (простое, оксид, кислота/основание/соль) и четыре пары реагентов; для каждого вещества '
                 'найти пару, с обоими реагентами которой оно реагирует',
       varies='вещества и пары реагентов (формулы)',
       answer_rule='проверить каждую пару: оба реагента должны реагировать с веществом (свойства классов, ряд напряжений, '
                   'условия реакций ионного обмена)',
       mistakes=['выбирают пару, где реагирует только один из реагентов', 'не учитывают амфотерность', 'путают ряд напряжений'],
       solve=_solve10, kind='dict', kes=['4.2', '4.3', '4.5', '4.6', '4.7', '4.8', '4.9'],
       fidelity=_F10('как в банке: А — простое вещество (H2, Cl2, C, Al), Б — оксид, В — соль/основание/кислота'))
def g10_mix(rng):
    groups = [rng.choice(SIMPLE10), rng.choice(OXIDES10), rng.choice(COMP10)]
    return _gen10(rng, 'ch-oge-10-simple-oxide-salt', groups)


@proto('ch-oge-10-names', 'ОГЭ', 10, 'Вещество (название) → реагенты (формулы)',
       invariant='три вещества даны названиями, пары реагентов — формулами; для каждого вещества найти пару реагентов',
       varies='вещества и пары реагентов',
       answer_rule='как в ch-oge-10-simple-oxide-salt',
       mistakes=['не узнают вещество по названию (угарный газ, негашёная известь)', 'выбирают пару с одним подходящим реагентом'],
       solve=_solve10, kind='dict', kes=['4.2', '4.3', '4.5', '4.6', '4.7', '4.8', '4.9'],
       fidelity=_F10('как в банке: «кислород, аммиак, сульфат меди(II)», «магний, оксид железа(II), гидроксид бария»'))
def g10_names(rng):
    groups = [rng.choice(SIMPLE10), rng.choice(OXIDES10), rng.choice(COMP10)]
    return _gen10(rng, 'ch-oge-10-names', groups, names=True)


@proto('ch-oge-10-compounds', 'ОГЭ', 10, 'Вещество → реагенты: оксиды, основания, кислоты, соли',
       invariant='три сложных вещества разных классов и четыре пары реагентов',
       varies='вещества (оксид, кислота, щёлочь, соль, амфотерный гидроксид) и пары реагентов',
       answer_rule='свойства классов: кислота — с металлами до H, оснóвными оксидами, основаниями, солями (осадок/газ); '
                   'щёлочь — с кислотами, кислотными оксидами, солями (осадок); соль — по условиям ионного обмена',
       mistakes=['забывают условие ионного обмена (осадок, газ, вода)', 'амфотерный гидроксид «не реагирует» со щёлочью'],
       solve=_solve10, kind='dict', kes=['4.5', '4.6', '4.7', '4.8', '4.9'],
       fidelity=_F10('как в банке: «гидроксид натрия, гидроксид цинка, соляная кислота»; «Fe2O3, H2SO4, CuSO4»'))
def g10_comp(rng):
    groups = rng.sample([OX_B + OX_AM, OX_A, list(ACID)[:6], list(ALK), list(BAMP) + list(BINS), COMMON_SALTS], 3)
    return _gen10(rng, 'ch-oge-10-compounds', groups)


# ================================================================= 9. Реагирующие вещества → продукты

def cond_tag(cond):
    c = cond or ''
    if 'сплав' in c:
        return 'сплавление'
    if 'конц' in c:
        return 'конц.'
    if 'разб' in c:
        return 'разб.'
    if any(w in c for w in ('изб', 'недост', ':', 'кипяч', 'влажн', 'обжиг', 'эл')):
        return 'особые'
    if 'хол' in c:
        return 'хол.'
    return ''


_MULTI = None


def cond_dependent(lhs):
    """Реагенты, для которых в базе есть разные наборы продуктов при разных условиях (Cl2 + KOH, C + O2 …)."""
    global _MULTI
    if _MULTI is None:
        acc = {}
        for r in chemdb.load()['reactions']:
            L = frozenset(x for x in r['lhs'] if x != 'H2O') if len(r['lhs']) == 3 else frozenset(r['lhs'])
            acc.setdefault(L, set()).add(frozenset(r['rhs']))
        _MULTI = {k for k, v in acc.items() if len(v) > 1}
    L = frozenset(x for x in lhs if x != 'H2O') if len(lhs) == 3 else frozenset(lhs)
    return L in _MULTI


def cond_words(cond):
    c = cond or ''
    w = []
    if 'хол' in c:
        w.append('на холоду')
    elif re.search(r'(^|[ ,(])t\b', c):
        w.append('t°')
    if 'горен' in c:
        w.append('горение')
    if 'кат' in c:
        w.append('кат.')
    if 'разряд' in c:
        w.append('электрический разряд')
    return ', '.join(w)


def _cond_ok9(r):
    """Если продукты зависят от условий, условие обязано быть в тексте карточки (конц./разб., t°, на холоду, сплавление)."""
    if not cond_dependent(r['lhs']):
        return True
    if frozenset(r['lhs']) in (frozenset({'Ba', 'O2'}), frozenset({'Mg', 'SiO2'}), frozenset({'C', 'CuO'})):
        return False          # продукты зависят от соотношения/условий, которые школьная запись не задаёт
    return bool(cond_tag(r.get('cond')) in ('конц.', 'разб.', 'сплавление') or cond_words(r.get('cond'))
                or set(r['lhs']) & AMPH9 or 'пар' in (r.get('cond') or ''))


def prod_text(ps):
    ts = [disp(x) for x in ps]
    return ts[0] if len(ts) == 1 else ', '.join(ts[:-1]) + ' и ' + ts[-1]


def _lhs_key(lhs, cond):
    L = [x for x in lhs if x != 'H2O'] if len(lhs) == 3 else list(lhs)
    return (frozenset(L), 'H2O' in lhs and len(lhs) == 2, cond_tag(cond))


_PROD = None


def _prod_index():
    """(реагенты без «лишней» воды, вода-реагент?, условие) → множество вариантов продуктов по всей базе."""
    global _PROD
    if _PROD is None:
        _PROD = {}
        for r in chemdb.load()['reactions']:
            if 'электролиз' in (r.get('cond') or '') or 'электролиз' in ' '.join(r.get('type', [])):
                continue
            key = _lhs_key(r['lhs'], r.get('cond'))
            _PROD.setdefault(key, set()).add(frozenset(r['rhs']))
    return _PROD


def products_db(lhs, cond):
    """solve: найти продукты заново по реагентам и условию; None — если в базе нет или неоднозначно."""
    v = _prod_index().get(_lhs_key(lhs, cond), set())
    return next(iter(v)) if len(v) == 1 else None


R9 = [r for r in D.REACTIONS if len(r['lhs']) <= 3 and cond_tag(r.get('cond')) != 'особые']
ALKALIS9 = {'NaOH', 'KOH'}
AMPH9 = {'Al', 'Zn', 'Al2O3', 'ZnO', 'Al(OH)3', 'Zn(OH)2'}


def _fam9(r):
    L, t = set(r['lhs']), r.get('type', [])
    if len(L) == 1:
        return 'decomp'
    if L & AMPH9 and L & ALKALIS9:
        return 'amph'
    if 'H2O' in L and len(r['lhs']) == 2:
        return 'water'
    if len(r['lhs']) == 3:
        return None
    ks = {kind(x) for x in L}
    if 'ОВР' in t or 'замещения' in t:
        return 'redox'
    if 'salt' in ks:
        return 'salts'
    if 'нейтрализации' in t or ks & {'oxb', 'oxam', 'oxa'}:
        return 'acidbase'
    return None


EXOTIC = {'FeSO3', 'FeSiO3', 'ZnSiO3', 'MgSiO3', 'BaSiO3', 'Fe3(PO4)2', 'FePO4', 'Cu3(PO4)2', 'AlPO4', 'Li2SO3',
          'FeI2', '(NH4)2SO3', 'Ag2SO3', 'Ag2CO3', 'Li2S', 'LiBr', 'LiI', 'Li2SiO3', 'Li2CO3', 'Li3PO4', 'MgSO3',
          'ZnCO3', 'FeCO3', 'Ag2SO4', 'BaSO3', 'CaSO3', 'FeBr2', 'FeBr3', 'CuBr2', 'AlBr3', 'AlI3', 'ZnI2', 'MgI2',
          'CaI2', 'BaI2', 'NH4I', 'NH4Br', 'CaBr2', 'BaBr2', 'ZnBr2', 'MgBr2', 'Zn3(PO4)2', 'Mg3(PO4)2', 'Ba3(PO4)2',
          '(NH4)2S', '(NH4)2SiO3', 'Fe(NO3)2', 'Ag2S'}


def _usable9(r):
    if any(x not in SUB for x in r['lhs'] + r['rhs']) or not _cond_ok9(r) or 'NH4NO3' in r['rhs']:
        return False
    if _fam9(r) in ('salts', 'acidbase', 'redox') and any(x in EXOTIC for x in r['lhs'] + r['rhs']):
        return False
    return products_db(r['lhs'], r.get('cond')) == frozenset(r['rhs'])


FAM9 = {}
for _r in R9:
    _f = _fam9(_r)
    if _f and _usable9(_r):
        FAM9.setdefault(_f, []).append(_r)
FAM9['amph'] = FAM9.get('amph', []) + [r for r in FAM9.get('acidbase', []) if set(r['lhs']) & AMPH9]


def lhs_text(r):
    L = [x for x in r['lhs'] if x != 'H2O'] if len(r['lhs']) == 3 else list(r['lhs'])
    tag = cond_tag(r.get('cond'))
    ts = []
    for x in L:
        t = disp(x)
        if tag in ('конц.', 'разб.') and x in ('HNO3', 'H2SO4', 'HCl'):
            t += f' ({tag})'
        if x in ALKALIS9 and set(L) & AMPH9:
            t += ' (тв.)' if tag == 'сплавление' else ' (р-р)'
        if x == 'H2O' and 'пар' in (r.get('cond') or ''):
            t += ' (пар)'
        if x == 'H2O' and 'горяч' in (r.get('cond') or ''):
            t += ' (при нагревании)'
        ts.append(t)
    if len(L) == 1:
        return f'{ts[0]} (при нагревании)'
    s = ' и '.join(ts)
    if tag == 'сплавление' and not set(L) & AMPH9:
        s += ' (сплавление)'
    if cond_dependent(r['lhs']) and tag not in ('сплавление',) and not set(L) & AMPH9:
        w = cond_words(r.get('cond'))
        if w and 'пар' not in (r.get('cond') or '') and 'горяч' not in (r.get('cond') or ''):
            s = s.replace(f' ({tag})', f' ({tag}, {w})', 1) if tag in ('конц.', 'разб.') and f' ({tag})' in s else s + f' ({w})'
    return s


SWAP_F = {'H2O': ['H2'], 'H2': ['H2O'], 'NO': ['NO2', 'N2'], 'NO2': ['NO', 'N2'], 'N2': ['NO', 'NH3'], 'SO2': ['SO3'],
          'SO3': ['SO2'], 'CO': ['CO2'], 'CO2': ['CO'], 'Cu': ['CuO'],
          'O2': ['O3', 'H2'], 'Fe3O4': ['Fe2O3', 'FeO'], 'NH4NO3': ['NH3', 'N2'], 'N2O': ['NO', 'N2'],
          'Na(Al(OH)4)': ['NaAlO2', 'Al(OH)3'], 'NaAlO2': ['Na(Al(OH)4)'], 'K(Al(OH)4)': ['KAlO2', 'Al(OH)3'],
          'KAlO2': ['K(Al(OH)4)'], 'Na2(Zn(OH)4)': ['Na2ZnO2', 'Zn(OH)2'], 'Na2ZnO2': ['Na2(Zn(OH)4)'],
          'K2(Zn(OH)4)': ['K2ZnO2', 'Zn(OH)2'], 'K2ZnO2': ['K2(Zn(OH)4)'], 'Fe2O3': ['FeO', 'Fe3O4'], 'FeO': ['Fe2O3'],
          'H2SO4': ['H2SO3'], 'H2SO3': ['H2SO4'], 'HNO3': ['HNO2'], 'H3PO4': ['HPO3'], 'NaNO2': ['NaNO3'],
          'KNO2': ['KNO3'], 'CaO': ['Ca(OH)2'], 'MgO': ['Mg(OH)2'], 'CuO': ['Cu2O', 'Cu(OH)2']}
AN_SWAP = {'SO4': 'SO3', 'SO3': 'SO4', 'NO3': 'NO2', 'Cl': 'ClO', 'S': 'SO3', 'CO3': 'SO3', 'PO4': 'SO4'}


def _mut_salt(f, rng):
    if f not in SALT:
        return None
    c, a, _ = SALT[f]
    opts_ = []
    if c == 'Fe2' and (('Fe3', a) in D.SOL):
        opts_.append(('Fe3', a))
    if c == 'Fe3' and (('Fe2', a) in D.SOL):
        opts_.append(('Fe2', a))
    if a in AN_SWAP and (c, AN_SWAP[a]) in D.SOL:
        opts_.append((c, AN_SWAP[a]))
    opts_ = [x for x in opts_ if D.SOL[x] in ('р', 'м', 'н')]
    if not opts_:
        return None
    return D._salt_formula(*rng.choice(opts_))


def mutate9(ps, rng):
    ps = list(ps)
    mode = rng.random()
    if mode < 0.2 and len(ps) >= 2 and 'H2O' in ps:
        return [x for x in ps if x != 'H2O']                      # «забыли» воду
    if mode < 0.35 and len(ps) >= 2:
        return ps[:-1] if rng.random() < 0.5 else ps[1:]
    if mode < 0.45 and 'H2' not in ps and 'H2O' not in ps:
        return ps + [rng.choice(['H2', 'H2O'])]
    i = rng.randrange(len(ps))
    f = ps[i]
    new = _mut_salt(f, rng)
    if new is None and f in SWAP_F:
        new = rng.choice(SWAP_F[f])
    if new is None or new not in SUB or new in ps:
        return None
    ps[i] = new
    return ps


def _elements(r):
    return {e for x in r['lhs'] for e in parse_formula(x)} - {'H', 'O'}


STEM9 = ['Установите соответствие между реагирующими веществами и продуктом(-ами) их взаимодействия: к каждой '
         'позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой.']


STEM9D = ['Установите соответствие между веществом и продуктами его разложения при нагревании: к каждой позиции, '
          'обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой.']


def _gen9(rng, pid, fam):
    pool = FAM9[fam]
    r0 = rng.choice(pool)
    el0 = _elements(r0)
    chosen = [r0]
    for _ in range(40):
        if len(chosen) == 3:
            break
        near = [r for r in pool if r not in chosen and _elements(r) & el0]
        r = rng.choice(near if near and rng.random() < 0.7 else pool)
        if any(_lhs_key(r['lhs'], r.get('cond')) == _lhs_key(c['lhs'], c.get('cond')) or
               frozenset(r['rhs']) == frozenset(c['rhs']) for c in chosen):
            continue
        chosen.append(r)
    if len(chosen) < 3:
        raise Retry
    rights = [list(r['rhs']) for r in chosen]
    dist = []
    for _ in range(60):
        if len(dist) == 2:
            break
        m = mutate9(rng.choice(rights), rng)
        if m and len(m) >= 1 and all(frozenset(m) != frozenset(x) for x in rights + dist):
            # отвлекающий вариант не должен оказаться верным для какой-либо левой позиции
            if all(products_db(c['lhs'], c.get('cond')) != frozenset(m) for c in chosen):
                dist.append(m)
    if len(dist) < 2:
        raise Retry
    right_sets = shuffled(rng, rights + dist)
    o = match_opts([lhs_text(r) for r in chosen], [prod_text(ps) for ps in right_sets])
    a = {LET[i]: str(right_sets.index(list(r['rhs'])) + 1) for i, r in enumerate(chosen)}
    q = (rng.choice(STEM9D) if fam == 'decomp' else rng.choice(STEM9)) + END_M
    eqs = [(r['lhs'], r['rhs'], *balance(r['lhs'], r['rhs'])) for r in chosen]
    e = ' '.join(f'{LET[i]}) {eq_text(eq)}.' for i, eq in enumerate(eqs)) + ' Ответ: ' + ''.join(a[x] for x in LET[:3]) + '.'
    return pcard(pid, q, a, e, k='match', o=o, eqs=eqs,
                 p={'left': [[r['lhs'], r.get('cond', '')] for r in chosen], 'right': right_sets})


def _solve9(p):
    a = {}
    for i, (lhs, cond) in enumerate(p['left']):
        ps = products_db(lhs, cond)
        hits = [j for j, s in enumerate(p['right']) if frozenset(s) == ps]
        if len(hits) != 1:
            return f'нет однозначного продукта для {lhs}'
        a[LET[i]] = str(hits[0] + 1)
    return a


_F9 = lambda scale, trap: F(MATCH3 + ' (3 пары реагентов, 5 вариантов продуктов)',
                           'как в демоверсии 2027 №9: «реагирующие вещества — продукт(ы) взаимодействия»', 'П', 7, scale,
                           trap, ['4.2', '4.3', '4.4', '4.5', '4.6', '4.7', '4.8', '4.9'], SC2)


@proto('ch-oge-09-water', 'ОГЭ', 9, 'Продукты реакций с водой: металлы, оснóвные и кислотные оксиды, хлор',
       invariant='три пары «вещество + вода»; для каждой выбрать продукты из пяти вариантов',
       varies='металлы (Li, Na, K, Ca, Ba, Mg), оксиды (Na2O, CaO, SO3, P2O5, N2O5 …), Cl2, NO2',
       answer_rule='активный металл + вода → щёлочь + H2; оснóвный оксид + вода → щёлочь; кислотный оксид + вода → кислота',
       mistakes=['металл + вода → «только щёлочь» (без H2)', 'оксид + вода → «щёлочь + H2»', 'SO2 + H2O → H2SO4'],
       solve=_solve9, kind='dict', kes=['4.3', '4.5', '4.6'],
       fidelity=_F9('как в банке: «Na2O и H2O», «Na и H2O», «CaO и H2O», «Ca и H2O»', 'H2 есть только у металла'))
def g9_water(rng):
    return _gen9(rng, 'ch-oge-09-water', 'water')


@proto('ch-oge-09-acid-base', 'ОГЭ', 9, 'Продукты реакций кислот, оснований и оксидов (соль + вода)',
       invariant='три пары (кислота + основание / оксид, щёлочь + кислотный оксид, оксид + оксид); выбрать продукты',
       varies='кислоты (HCl, H2SO4, HNO3, H3PO4 …), основания, оксиды',
       answer_rule='соль образована катионом основания (оксида) и анионом кислоты; SO2 даёт сульфит, SO3 — сульфат, '
                   'N2O5 — нитрат; с кислотами металлы не выделяют воду, а оксиды и основания — не выделяют H2',
       mistakes=['SO2 + KOH → K2SO4', 'оксид + кислота → соль + H2', 'валентность железа в соли'],
       solve=_solve9, kind='dict', kes=['4.5', '4.6', '4.7', '4.8'],
       fidelity=_F9('как в банке: «LiOH и SO3», «KOH и H2SO3», «P2O5 и NaOH»', 'сульфит/сульфат, H2/H2O'))
def g9_acidbase(rng):
    return _gen9(rng, 'ch-oge-09-acid-base', 'acidbase')


@proto('ch-oge-09-amphoteric', 'ОГЭ', 9, 'Продукты реакций амфотерных веществ (Al, Zn и их соединений) со щелочами и кислотами',
       invariant='три пары с Al/Zn или их оксидами и гидроксидами; раствор щёлочи или сплавление',
       varies='вещество (Al, Zn, Al2O3, ZnO, Al(OH)3, Zn(OH)2), щёлочь (NaOH, KOH), раствор/сплавление, кислота',
       answer_rule='в растворе щёлочи — гидроксокомплекс (Na[Al(OH)4], Na2[Zn(OH)4]), при сплавлении — метасоль '
                   '(NaAlO2, Na2ZnO2) и вода; металл дополнительно выделяет H2',
       mistakes=['в растворе пишут NaAlO2', 'при сплавлении пишут комплекс', 'забывают H2 у металла'],
       solve=_solve9, kind='dict', kes=['4.3', '4.6', '4.7'],
       fidelity=_F9('как в банке: «Al(OH)3 и KOH (р-р)», «Al2O3 и KOH (тв.)», «Al и KOH (р-р)»', 'раствор/сплавление'))
def g9_amph(rng):
    return _gen9(rng, 'ch-oge-09-amphoteric', 'amph')


@proto('ch-oge-09-redox', 'ОГЭ', 9, 'Продукты окислительно-восстановительных реакций (металлы, неметаллы, конц. кислоты)',
       invariant='три пары реагентов, реакции ОВР/замещения; выбрать продукты',
       varies='металлы с кислотами и солями, HNO3 и H2SO4 (конц./разб.), галогены, кислород, водород, углерод',
       answer_rule='металлы до H с HCl/H2SO4(разб.) → соль + H2; Cu с HNO3(конц.) → NO2, с HNO3(разб.) → NO, '
                   'с H2SO4(конц.) → SO2; Fe с Cl2 → FeCl3, с HCl → FeCl2; галоген вытесняет менее активный',
       mistakes=['Cu + HNO3 → H2', 'Fe + HCl → FeCl3', 'азотная кислота «выделяет водород»'],
       solve=_solve9, kind='dict', kes=['4.2', '4.3', '4.8'],
       fidelity=_F9('как в банке: «Cu + HNO3 (конц.)», «Fe и H2SO4 (разб.)», «Fe3O4 и H2», «H2S + O2»',
                    'NO/NO2, Fe2+/Fe3+'))
def g9_redox(rng):
    return _gen9(rng, 'ch-oge-09-redox', 'redox')


@proto('ch-oge-09-decomposition', 'ОГЭ', 9, 'Продукты термического разложения (гидроксиды, карбонаты, нитраты, соли аммония)',
       invariant='три вещества, разлагающиеся при нагревании; выбрать продукты',
       varies='гидроксиды (Cu, Fe, Al, Zn), карбонаты и гидрокарбонаты, нитраты, KMnO4, KClO3, соли аммония',
       answer_rule='нерастворимый гидроксид → оксид + вода; карбонат → оксид + CO2; гидрокарбонат → карбонат + CO2 + H2O; '
                   'нитраты: щелочных металлов → нитрит + O2, металлов Mg–Cu → оксид + NO2 + O2, Ag → Ag + NO2 + O2',
       mistakes=['NaHCO3 → Na2O', 'KNO3 → K2O', 'Fe(OH)3 → FeO'],
       solve=_solve9, kind='dict', kes=['4.7', '4.9'],
       fidelity=_F9('как в банке: «NaHCO3 →t», «Ca(HCO3)2 →t», «CaCO3 →t», «Fe(OH)3 →t»', 'продукты разложения нитратов'))
def g9_decomp(rng):
    return _gen9(rng, 'ch-oge-09-decomposition', 'decomp')


@proto('ch-oge-09-salts', 'ОГЭ', 9, 'Продукты реакций солей (с кислотами, щелочами, солями)',
       invariant='три пары с участием солей; выбрать продукты реакции ионного обмена',
       varies='соли (карбонаты, сульфиды, сульфиты, соли аммония, соли тяжёлых металлов), кислоты, щёлочи',
       answer_rule='обмен ионами; сульфит + кислота → SO2 + H2O; сульфид + кислота → H2S; соль аммония + щёлочь → NH3 + H2O',
       mistakes=['K2SO3 + HCl → SO3', 'NH4+ + OH− → N2', 'перепутали Fe(OH)2 и Fe(OH)3'],
       solve=_solve9, kind='dict', kes=['4.9'],
       fidelity=_F9('как в банке: «K2SO3 и HCl», «NaOH и (NH4)2SO4», «Fe2(SO4)3 и NaOH», «K2S + H2SO4»',
                    'SO2/SO3, NH3/N2, Fe(OH)2/Fe(OH)3'))
def g9_salts(rng):
    return _gen9(rng, 'ch-oge-09-salts', 'salts')


# ================================================================= степени окисления (для solve заданий 11, 15, 20)

OX_FIXED = {'F': -1, 'Li': 1, 'Na': 1, 'K': 1, 'Rb': 1, 'Cs': 1, 'Mg': 2, 'Ca': 2, 'Ba': 2, 'Sr': 2, 'Be': 2, 'Zn': 2,
            'Al': 3, 'Ag': 1}
OX_SPECIAL = {'H2O2': {'H': [1], 'O': [-1]}, 'Na2O2': {'Na': [1], 'O': [-1]}, 'KO2': {'K': [1], 'O': [Fr(-1, 2)]},
              'NH4NO3': {'N': [-3, 5], 'H': [1], 'O': [-2]}, 'NH4NO2': {'N': [-3, 3], 'H': [1], 'O': [-2]},
              'Fe3O4': {'Fe': [Fr(8, 3)], 'O': [-2]}, 'CaC2': {'Ca': [2], 'C': [-1]}, 'NH3·H2O': {'N': [-3], 'H': [1], 'O': [-2]}}
OX_GROUPS = [('Cr2O7', 'Cr', 6), ('CrO4', 'Cr', 6), ('SO4', 'S', 6), ('SO3', 'S', 4), ('NO3', 'N', 5), ('NO2', 'N', 3),
             ('PO4', 'P', 5), ('CO3', 'C', 4), ('SiO3', 'Si', 4), ('ClO4', 'Cl', 7), ('ClO3', 'Cl', 5), ('BrO3', 'Br', 5),
             ('IO3', 'I', 5), ('ClO', 'Cl', 1)]
BIN_NEG = {'Cl': -1, 'Br': -1, 'I': -1, 'S': -2, 'N': -3, 'P': -3, 'C': -4, 'Si': -4, 'H': -1}


def ox_states(f):
    """Степени окисления элементов в веществе: {элемент: [степени]} (независимый расчёт по правилам)."""
    if f in OX_SPECIAL:
        return OX_SPECIAL[f]
    comp = parse_formula(f)
    if len(comp) == 1:
        return {e: [0] for e in comp}
    known = {e: OX_FIXED[e] for e in comp if e in OX_FIXED}
    metals = set(comp) & METALS_ALL
    if 'O' in comp:
        known['O'] = -2
    if 'H' in comp:
        known['H'] = -1 if metals and set(comp) == metals | {'H'} else 1
    if f.startswith(('NH4', '(NH4)')) and 'N' not in known:
        known['N'] = -3
    unknown = [e for e in comp if e not in known]
    if len(unknown) == 2 and len(comp) == 2:
        neg = [e for e in unknown if e in BIN_NEG]
        if len(neg) == 2:       # например, NCl3, PCl5: более электроотрицательный — «отрицательный»
            order = ['Cl', 'N', 'Br', 'I', 'S', 'C', 'P', 'H', 'Si']
            neg = sorted(neg, key=order.index)[:1]
        if neg:
            known[neg[0]] = BIN_NEG[neg[0]]
    unknown = [e for e in comp if e not in known]
    if len(unknown) >= 2:
        for grp, el, st in OX_GROUPS:
            if grp in f and el in unknown:
                known[el] = st
                break
    unknown = [e for e in comp if e not in known]
    if len(unknown) > 1:
        raise ValueError(f'не определить степени окисления в {f}')
    if unknown:
        e = unknown[0]
        s = -sum(Fr(known[x]) * n for x, n in comp.items() if x != e)
        known[e] = s / comp[e]
    return {e: [known[e]] for e in comp}


def redox_changes(lhs, rhs):
    """Элементы, изменившие степень окисления: {элемент: (множество слева, множество справа)}."""
    L, Rr = {}, {}
    for side, d in ((lhs, L), (rhs, Rr)):
        for f in side:
            for e, sts in ox_states(f).items():
                d.setdefault(e, set()).update(sts)
    return {e: (L[e], Rr.get(e, set())) for e in L if L[e] != Rr.get(e, set())}


def rx_class(lhs, rhs):
    """Тип реакции по составу (независимо от поля type базы): разложения / соединения / замещения / обмена / другое."""
    simple = lambda f: len(parse_formula(f)) == 1
    if len(lhs) == 1:
        return 'разложения'
    if len(rhs) == 1:
        return 'соединения'
    if len(lhs) == 2 and len(rhs) == 2 and sum(map(simple, lhs)) == 1 and sum(map(simple, rhs)) == 1:
        return 'замещения'
    if not any(map(simple, lhs + rhs)) and not redox_changes(lhs, rhs):
        return 'обмена'
    return 'другое'


# ================================================================= 11. Классификация химических реакций

MAIN_T = ['соединения', 'разложения', 'замещения', 'обмена']
TYPE_GEN = {'соединения': 'соединения', 'разложения': 'разложения', 'замещения': 'замещения', 'обмена': 'обмена'}


def _main_type(r):
    ts = [t for t in r.get('type', []) if t in MAIN_T]
    return ts[0] if len(ts) == 1 else None


def _type_ok(r):
    """Тип в базе согласован с формальным признаком (строки без основного типа — только «другое»)."""
    return (_main_type(r) or 'другое') == rx_class(r['lhs'], r['rhs'])


def pair_name(r):
    L = [x for x in r['lhs'] if x != 'H2O'] if len(r['lhs']) == 3 else r['lhs']
    tag = cond_tag(r.get('cond'))
    ns = []
    for x in L:
        n = name(x)
        if x in ('H2SO4', 'HNO3') and tag == 'конц.':
            n = 'концентрированная ' + n
        elif x in ('H2SO4',) and tag == 'разб.':
            n = 'разбавленная ' + n
        ns.append(n)
    return ' и '.join(ns)


def pair_words(r):
    a, b = pair_name(r).split(' и ', 1)
    return f'взаимодействие {_decl(a, 0)} с {_decl(b, 1)}'


R11 = [r for r in D.REACTIONS if len(r['lhs']) == 2 and cond_tag(r.get('cond')) in ('', 'конц.', 'разб.')
       and all(x in SUB for x in r['lhs'] + r['rhs']) and not any(x in EXOTIC for x in r['lhs'] + r['rhs'])
       and products_db(r['lhs'], r.get('cond')) == frozenset(r['rhs']) and _type_ok(r)]
R11_EQ = [r for r in D.REACTIONS if len(r['lhs']) <= 2 and all(x in SUB for x in r['lhs'] + r['rhs'])
          and not any(x in EXOTIC for x in r['lhs'] + r['rhs']) and _type_ok(r)]


def _pick11(rng, pool, good, n_good, n_all=5):
    g = [r for r in pool if good(r)]
    b = [r for r in pool if not good(r)]
    if len(g) < n_good or len(b) < n_all - n_good:
        raise Retry
    out, seen = [], set()
    for src, k in ((g, n_good), (b, n_all - n_good)):
        cnt = 0
        for r in shuffled(rng, src):
            key = frozenset(x for x in r['lhs'] if x != 'H2O')
            if key in seen:
                continue
            seen.add(key)
            out.append((r, src is g))
            cnt += 1
            if cnt == k:
                break
        if cnt < k:
            raise Retry
    return out


STEM11P = ['Из предложенного перечня выберите две пары веществ, между которыми протекает реакция {t}.']
STEM11PN = ['Из предложенного перечня выберите две пары веществ, между которыми не протекает реакция {t}.']
STEM11W = ['Из предложенного перечня выберите две реакции, которые являются реакциями {t}.']
STEM11WN = ['Из предложенного перечня выберите две реакции, которые не являются реакциями {t}.']
END11 = ' Запишите номера выбранных ответов.'


def _gen11_pairs(rng):
    t = rng.choice(['соединения', 'замещения', 'обмена'])
    neg = rng.random() < 0.25
    pool = [r for r in R11 if _main_type(r) or 'ОВР' in r.get('type', [])]
    good = (lambda r: _main_type(r) == t) if not neg else (lambda r: _main_type(r) not in (t, None))
    if neg:
        pool = [r for r in pool if _main_type(r)]
    picked = _pick11(rng, pool, good, 2 if not neg else 2)
    if neg:   # в «не относится» верных — 2, остальные три — нужного типа
        picked = [(r, ok) for r, ok in picked]
    items = shuffled(rng, picked)
    words = rng.random() < 0.3
    texts = [pair_words(r) if words else pair_name(r) for r, _ in items]
    o = opts(texts)
    a = ids_of([i for i, (r, ok) in enumerate(items) if ok])
    stems = (STEM11WN if neg else STEM11W) if words else (STEM11PN if neg else STEM11P)
    q = rng.choice(stems).format(t=t) + END11
    eqs = [(r['lhs'], r['rhs'], *balance(r['lhs'], r['rhs'])) for r, _ in items]
    e = ' '.join(f'{i + 1}) {eq_text(eq)} — {_main_type(r) or "ОВР"}.' for i, ((r, _), eq) in enumerate(zip(items, eqs))) + \
        f' Ответ: {"".join(a)}.'
    return pcard('ch-oge-11-pairs-type', q, a, e, k='many', o=o, eqs=eqs,
                 p={'items': [[r['lhs'], r['rhs']] for r, _ in items], 't': t, 'neg': neg})


def _solve11_type(p):
    res = [rx_class(l, r) for l, r in p['items']]
    if p.get('neg'):
        return ids_of([i for i, c in enumerate(res) if c != p['t']])
    return ids_of([i for i, c in enumerate(res) if c == p['t']])


_F11 = lambda scale, trap: F(MANY2, 'как в демоверсии 2027 №11 и банке: «Из предложенного перечня выберите две пары '
                                    'веществ / два уравнения …», пять вариантов', 'Б', 5, scale, trap, ['5.1'], SC1M)


@proto('ch-oge-11-pairs-type', 'ОГЭ', 11, 'Тип реакции между парами веществ (соединения, замещения, обмена)',
       invariant='пять пар веществ (названия); выбрать две пары, реакция между которыми относится (не относится) '
                 'к заданному типу',
       varies='тип реакции, пары веществ, формулировка «пара веществ» / «взаимодействие … с …», отрицание',
       answer_rule='замещения — простое + сложное → простое + сложное; обмена — два сложных обмениваются составными '
                   'частями; соединения — из нескольких веществ одно',
       mistakes=['Fe2O3 + CO считают замещением', 'нейтрализацию не считают обменом', 'металл + кислота считают обменом'],
       solve=_solve11_type, kind='dict', kes=['5.1'],
       fidelity=_F11('как в банке: «оксид натрия и вода», «натрий и вода», «гидроксид калия и азотная кислота»',
                     'замещение/ОВР без простого реагента'))
def g11_pairs(rng):
    return _gen11_pairs(rng)


STEM11E = ['Из предложенного перечня выберите два уравнения, соответствующих реакциям {t}.',
           'Из предложенного перечня выберите схемы двух реакций, которые относятся к реакциям {t}.']


@proto('ch-oge-11-equations-type', 'ОГЭ', 11, 'Тип реакции по уравнению (соединения, разложения, замещения, обмена)',
       invariant='пять уравнений (схем) реакций; выбрать два, относящихся к заданному типу',
       varies='тип реакции, уравнения (с коэффициентами или схемы без них)',
       answer_rule='тип определяют по числу и составу реагентов и продуктов',
       mistakes=['разложение нитрата принимают за обмен', 'реакцию металла с солью — за обмен', 'AgNO3 + NaCl — за замещение'],
       solve=_solve11_type, kind='dict', kes=['5.1'],
       fidelity=_F11('как в банке: «Zn + Cu(NO3)2 →», «Mg(OH)2 + H2SO4 →», «BaCl2 + K2SO4 →», «Cu(NO3)2 →»',
                     'разложение нитратов/солей, замещение металла в соли'))
def g11_eq(rng):
    t = rng.choice(MAIN_T)
    pool = [r for r in R11_EQ if _main_type(r)]
    picked = _pick11(rng, pool, lambda r: _main_type(r) == t, 2)
    items = shuffled(rng, picked)
    coefs = rng.random() < 0.5
    eqs = [(r['lhs'], r['rhs'], *balance(r['lhs'], r['rhs'])) for r, _ in items]
    if coefs:
        texts = [eq_text(eq) for eq in eqs]
    else:
        texts = [' + '.join(disp(x) for x in r['lhs']) + ' → ' + ' + '.join(disp(x) for x in r['rhs']) for r, _ in items]
    o = opts(texts)
    a = ids_of([i for i, (r, ok) in enumerate(items) if ok])
    q = STEM11E[0 if coefs else 1].format(t=t) + ' Запишите номера выбранных ответов.'
    e = ' '.join(f'{i + 1}) {_main_type(r)}.' for i, (r, _) in enumerate(items)) + f' Ответ: {"".join(a)}.'
    return pcard('ch-oge-11-equations-type', q, a, e, k='many', o=o, eqs=eqs,
                 p={'items': [[r['lhs'], r['rhs']] for r, _ in items], 't': t, 'neg': False})


def _solve11_redox(p):
    out = []
    for i, (lhs, cond) in enumerate(p['left']):
        ps = products_db(lhs, cond)
        if ps is None:
            return 'реакция не найдена'
        if bool(redox_changes(list(lhs), list(ps))) != p['neg']:
            out.append(i)
    return ids_of(out)


@proto('ch-oge-11-redox-pairs', 'ОГЭ', 11, 'Пары веществ, между которыми протекает окислительно-восстановительная реакция',
       invariant='пять пар веществ (названия); выбрать две пары, реакция между которыми является (не является) ОВР',
       varies='пары веществ (металл + кислота, горение, вытеснение, нейтрализация, обмен, соединение оксидов), отрицание',
       answer_rule='ОВР — меняются степени окисления: все реакции с участием простых веществ, горение, вытеснение металлов '
                   'и галогенов; обмен и соединение оксидов/с водой — без изменения степеней окисления',
       mistakes=['реакцию оксида с водой считают ОВР', 'не замечают ОВР без простого вещества (CO + CuO, NH3 + O2)',
                 'аммиак + хлороводород считают ОВР'],
       solve=_solve11_redox, kind='dict', kes=['5.1', '5.3'],
       fidelity=_F11('как в демоверсии 2027: «оксид железа(III) и серная кислота», «угарный газ и кислород», '
                     '«алюминий и соляная кислота»', 'соединение без ОВР (NH3 + HCl, Na2O + H2O)'))
def g11_redox(rng):
    neg = rng.random() < 0.2
    pool = [r for r in R11 if _main_type(r) or 'ОВР' in r.get('type', [])]
    isredox = lambda r: 'ОВР' in r.get('type', [])
    picked = _pick11(rng, pool, (lambda r: not isredox(r)) if neg else isredox, 2)
    items = shuffled(rng, picked)
    o = opts([pair_name(r) for r, _ in items])
    a = ids_of([i for i, (r, ok) in enumerate(items) if ok])
    q = ('Из предложенного перечня выберите две пары веществ, между которыми не протекает окислительно-'
         'восстановительная реакция.' if neg else 'Из предложенного перечня выберите две пары веществ, между которыми '
         'протекает окислительно-восстановительная реакция.') + END11
    eqs = [(r['lhs'], r['rhs'], *balance(r['lhs'], r['rhs'])) for r, _ in items]
    e = ' '.join(f'{i + 1}) {eq_text(eq)} — {"ОВР" if isredox(r) else "без изменения степеней окисления"}.'
                 for i, ((r, _), eq) in enumerate(zip(items, eqs))) + f' Ответ: {"".join(a)}.'
    return pcard('ch-oge-11-redox-pairs', q, a, e, k='many', o=o, eqs=eqs,
                 p={'left': [[r['lhs'], r.get('cond', '')] for r, _ in items], 'neg': neg})


THERMO_T = dict(D.THERMO)


def _solve11_thermo(p):
    return ids_of([i for i, t in enumerate(p['items']) if THERMO_T.get(t) == p['want']])


@proto('ch-oge-11-thermal', 'ОГЭ', 11, 'Экзотермические и эндотермические реакции',
       invariant='пять описаний процессов; выбрать два экзотермических (эндотермических)',
       varies='процессы: горение, взаимодействие активных металлов с водой, нейтрализация — экзо; разложение карбонатов, '
              'гидроксидов, нитратов, перманганата, электролиз воды, N2 + O2, C + CO2 — эндо',
       answer_rule='горение, нейтрализация, соединение активных веществ — с выделением теплоты; разложение при нагревании, '
                   'электролиз, синтез NO — с поглощением',
       mistakes=['реакцию азота с кислородом считают экзотермической', 'разложение считают экзотермическим'],
       solve=_solve11_thermo, kind='dict', kes=['5.1', '5.2'],
       fidelity=_F11('как в банке: «разложение карбоната кальция», «горение серы», «взаимодействие азота и кислорода»',
                     'N2 + O2, C + CO2 — эндотермические'))
def g11_thermo(rng):
    want = rng.choice(['экзо', 'эндо'])
    good = [t for t, v in D.THERMO if v == want]
    bad = [t for t, v in D.THERMO if v != want]
    items = shuffled(rng, rng.sample(good, 2) + rng.sample(bad, 3))
    o = opts(items)
    a = ids_of([i for i, t in enumerate(items) if THERMO_T[t] == want])
    w = 'экзотермические' if want == 'экзо' else 'эндотермические'
    q = f'Из предложенного перечня выберите две {w} реакции. Запишите номера выбранных ответов.'
    e = '; '.join(f'{i + 1}) {("экзо" if THERMO_T[t] == "экзо" else "эндо")}термическая' for i, t in enumerate(items)) + \
        f'. Ответ: {"".join(a)}.'
    return pcard('ch-oge-11-thermal', q, a, e, k='many', o=o, p={'items': items, 'want': want})


# ================================================================= 12. Признаки реакций

SOL_EL = [f for f in STRONG] + ['NaOH', 'KOH', 'Ba(OH)2', 'Ca(OH)2'] + \
    [f for f in COMMON_SALTS if SALT[f][2] == 'р' and f not in EXOTIC]
INSOL12 = ['Mg(OH)2', 'Cu(OH)2', 'Fe(OH)2', 'Fe(OH)3', 'Zn(OH)2', 'Al(OH)3', 'CaCO3', 'BaCO3', 'MgCO3', 'BaSO4', 'AgCl',
           'FeS', 'ZnS', 'CuO', 'Fe2O3', 'MgO', 'ZnO', 'Al2O3', 'FeO']
METAL12 = ['Mg', 'Zn', 'Fe', 'Al', 'Cu', 'Ag']
GAS_OF = {'CO3': 'CO2', 'SO3': 'SO2', 'S': 'H2S'}


def _ions(f):
    k = kind(f)
    if k == 'acid':
        return ('H', ACID[f])
    if k == 'alk':
        return (ALK[f], 'OH')
    if k == 'salt' and SALT[f][2] == 'р':
        return SALT[f][:2]
    return None


def _prod_obs(c, a):
    """Что даёт пара ионов в растворе: '' — ничего видимого, 'осадок:F', 'газ:F', None — спорно."""
    if (c, a) == ('H', 'OH'):
        return ''
    if c == 'H':
        if a in GAS_OF:
            return 'газ:' + GAS_OF[a]
        if a == 'SiO3':
            return 'осадок:H2SiO3'
        return '' if a in ('Cl', 'Br', 'I', 'NO3', 'SO4') else None
    if (c, a) == ('NH4', 'OH'):
        return 'газ:NH3'
    s = D.SOL.get((c, a))
    if s == 'н':
        f = D._salt_formula(c, a) if a != 'OH' else [x for x, k in {**BINS, **BAMP}.items() if k == c][0]
        return 'осадок:' + f
    if s == 'р':
        return ''
    return None


def observe(a, b):
    """Признаки реакции по правилам (ионы, растворимость, ряд напряжений) — генератор задания 12, 17, 23."""
    ia, ib = _ions(a), _ions(b)
    if ia and ib:
        if ia[0] == ib[0] or ia[1] == ib[1]:
            return frozenset({'нет'})
        if 'HNO3' in (a, b) and {ia[1], ib[1]} & {'S', 'SO3', 'I', 'Br'} or {a, b} >= {'HNO3'} and {ia[0], ib[0]} & {'Fe2'}:
            return None
        tags = set()
        for c, an in ((ia[0], ib[1]), (ib[0], ia[1])):
            t = _prod_obs(c, an)
            if t is None:
                return None
            if t:
                tags.add(t)
        if {'Fe3', 'Ag'} & {ia[0], ib[0]} and {'I', 'S', 'SO3', 'Fe2'} & {ia[1], ib[1], ia[0], ib[0]}:
            return None
        return frozenset(tags or {'нет'})
    # нерастворимое вещество + кислота / щёлочь
    for x, y in ((a, b), (b, a)):
        if x in INSOL12 and y in STRONG:
            if y == 'HNO3' and x in ('FeS', 'ZnS', 'Fe(OH)2', 'FeO'):
                return None
            if x in ('BaSO4', 'AgCl'):
                return frozenset({'нет'})
            cat = {**BINS, **BAMP, **{'CuO': 'Cu', 'Fe2O3': 'Fe3', 'MgO': 'Mg', 'ZnO': 'Zn', 'Al2O3': 'Al', 'FeO': 'Fe2'}}.get(x)
            gas = None
            if x in SALT:
                cat, an, _ = SALT[x]
                gas = GAS_OF.get(an)
            if D.SOL.get((cat, ACID[y])) != 'р':
                return None
            tags = {'растворение'}
            if gas:
                tags.add('газ:' + gas)
            if cat in D.SOLN_COLOR:
                tags.add('раствор:' + D.SOLN_COLOR[cat])
            return frozenset(tags)
        if x in BAMP and y in ('NaOH', 'KOH'):
            return frozenset({'растворение'})
        if x in INSOL12 and y in ALK:
            if x in ('ZnO', 'Al2O3'):
                return frozenset({'растворение'}) if y in ('NaOH', 'KOH') else None
            if x in BAMP or x in ('Fe(OH)3', 'Fe2O3'):
                return None
            return frozenset({'нет'})
        if x in INSOL12 and y in SOL_EL:
            c, an = _ions(y)
            if c in ('Na', 'K') and an in ('Cl', 'NO3', 'SO4') and x not in ('FeS', 'ZnS'):
                return frozenset({'нет'})
            return None
    # металл + кислота / соль
    for x, y in ((a, b), (b, a)):
        if x in METAL12 and y in SOL_EL:
            if y in ('HCl', 'HBr', 'HI', 'H2SO4'):
                return frozenset({'газ:H2'}) if _act_lt(x, 'H') else frozenset({'нет'})
            if y == 'HNO3':
                return None
            if y in ALK:
                return frozenset({'газ:H2'}) if x in ('Al', 'Zn') and y in ('NaOH', 'KOH') else (None if x in ('Al', 'Zn') else frozenset({'нет'}))
            c, an = SALT[y][:2]
            cm = MET_OF.get(c)
            if c in ('Fe3', 'NH4') or an in ('CO3', 'S', 'SO3', 'SiO3', 'PO4'):
                return None
            if cm and _act_lt(x, cm) and cm not in REACTIVE_M:
                return frozenset({'налёт:' + cm}) if cm in ('Cu', 'Ag') else None
            return frozenset({'нет'})
    return None


_MYPAIR = {}
for _r in D.REACTIONS:
    _L = _r['lhs']
    for _i, _x in enumerate(_L):
        for _y in _L[_i + 1:]:
            if _x != _y and set(_L) - {_x, _y} <= {'H2O'}:
                _MYPAIR.setdefault(frozenset((_x, _y)), []).append(_r)


def obs_db(a, b, conc=False):
    """Признаки из базы участка (chemdb_oge): реакция найдена заново по реагентам, признак — поле sign в машинном виде
    ('осадок:F; газ:F; растворение; раствор:цвет; налёт:M'). Реакции нет — видимых признаков нет."""
    rs = [r for r in _MYPAIR.get(frozenset((a, b)), [])
          if ('конц' in (r.get('cond') or '')) == conc or 'H2SO4' not in (a, b) and 'HNO3' not in (a, b)]
    if 'HNO3' in (a, b) and not conc:
        rs = [r for r in rs if 'конц' not in (r.get('cond') or '')]
    if not rs:
        return frozenset({'нет'})
    tagsets = set()
    for r in rs:
        parts = [x.strip() for x in (r.get('sign') or '').split(';') if x.strip()]
        if parts and all(re.match(r'^(осадок:\S|газ:\S|растворение$|раствор:|налёт:|нет$)', x) for x in parts):
            tagsets.add(frozenset(parts))
    return next(iter(tagsets)) if len(tagsets) == 1 else None


ADJ = {'белый': 'белого', 'голубой': 'голубого', 'бурый': 'бурого', 'серо-зелёный': 'серо-зелёного', 'жёлтый': 'жёлтого',
       'чёрный': 'чёрного', 'светло-жёлтый': 'светло-жёлтого', 'белый творожистый': 'белого творожистого',
       'белый студенистый': 'белого студенистого', 'бесцветный студенистый': 'бесцветного студенистого'}
GAS_TEXT = {'CO2': 'выделение бесцветного газа без запаха', 'H2': 'выделение бесцветного газа без запаха',
            'SO2': 'выделение бесцветного газа с резким запахом', 'NH3': 'выделение бесцветного газа с резким запахом',
            'H2S': 'выделение газа с запахом тухлых яиц', 'NO2': 'выделение бурого газа'}
SOLN_GEN = {'голубой': 'голубого', 'жёлто-бурый': 'жёлтого', 'бледно-зелёный': 'бледно-зелёного'}


def sign_text(tags, level):
    """Словесный признак по машинным тегам; None — если для уровня формулировок пара не подходит."""
    if tags is None:
        return None
    t = set(tags)
    gas = [x[4:] for x in t if x.startswith('газ:')]
    pr = [x[7:] for x in t if x.startswith('осадок:')]
    sol = [x[8:] for x in t if x.startswith('раствор:')]
    dis = 'растворение' in t
    nal = [x[6:] for x in t if x.startswith('налёт:')]
    if t == {'нет'}:
        return 'видимые признаки реакции отсутствуют'
    if level == 'general':
        if dis and not gas and not pr:
            return 'растворение осадка'
        if gas and not pr and not dis:
            return 'выделение газа'
        if pr and not gas and not dis:
            return 'образование осадка'
        return None
    if level == 'color':
        if len(pr) == 1 and not gas and not dis and D.PRECIP_COLOR.get(pr[0]) in ADJ:
            return f'выпадение {ADJ[D.PRECIP_COLOR[pr[0]]]} осадка'
        if gas and not pr and not dis and gas[0] in ('CO2', 'H2'):
            return 'выделение бесцветного газа'
        return None
    if level == 'gas':
        if len(gas) == 1 and not pr and not dis:
            return GAS_TEXT.get(gas[0])
        if len(pr) == 1 and not gas and D.PRECIP_COLOR.get(pr[0]) in ('белый', 'белый творожистый'):
            return 'выпадение белого осадка'
        return None
    if level == 'solid':
        if nal:
            return {'Cu': 'выделение красного металла на поверхности', 'Ag': 'появление серого налёта металла'}[nal[0]]
        if dis and gas:
            return 'растворение твёрдого вещества с выделением газа'
        if dis and not pr:
            if sol:
                return f'растворение твёрдого вещества с образованием {SOLN_GEN[sol[0]]} раствора'
            return 'растворение твёрдого вещества с образованием бесцветного раствора'
        if gas == ['H2'] and not pr:
            return 'растворение твёрдого вещества с выделением газа'
        return None
    return None


EXTRA_SIGNS = {
    'general': ['выделение газа', 'образование осадка', 'растворение осадка', 'видимые признаки реакции отсутствуют'],
    'color': ['выпадение белого осадка', 'выпадение голубого осадка', 'выпадение бурого осадка',
              'выпадение серо-зелёного осадка', 'выпадение жёлтого осадка', 'выпадение чёрного осадка',
              'выделение бесцветного газа'],
    'gas': ['выделение бесцветного газа без запаха', 'выделение бесцветного газа с резким запахом',
            'выделение газа с запахом тухлых яиц', 'выпадение белого осадка', 'видимые признаки реакции отсутствуют'],
    'solid': ['растворение твёрдого вещества с выделением газа', 'растворение твёрдого вещества с образованием '
              'голубого раствора', 'растворение твёрдого вещества с образованием бесцветного раствора',
              'растворение твёрдого вещества с образованием жёлтого раствора', 'выделение красного металла на поверхности',
              'появление серого налёта металла'],
}


def _pairs12():
    out = []
    pool = SOL_EL + INSOL12 + METAL12
    for i, a in enumerate(pool):
        for b in pool[i + 1:]:
            if (a in INSOL12 or a in METAL12) and (b in INSOL12 or b in METAL12):
                continue
            if a == 'Ca(OH)2' and b in INSOL12:
                continue
            ob = observe(a, b)
            if ob is not None:
                out.append((a, b, ob))
    return out


PAIRS12 = _pairs12()
STEM12 = ['Установите соответствие между реагирующими веществами и признаком протекающей между ними реакции: к каждой '
          'позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой.']


def _p12_text(f):
    if f in INSOL12 or f in METAL12:
        return disp(f)
    return disp(f) + (' (р-р)' if f not in STRONG or f == 'H2SO4' else '')


def _gen12(rng, pid, level, filt=None):
    cands = [(a, b, ob, sign_text(ob, level)) for a, b, ob in PAIRS12 if (filt is None or filt(a, b, ob))
             and not ({a, b} & EXOTIC) and not any(t.split(':')[-1] in EXOTIC for t in ob)]
    cands = [c for c in cands if c[3]]
    # «признаки отсутствуют» — только для реакции, которая идёт без видимых признаков (нейтрализация растворов)
    none_c = [c for c in cands if c[3] == 'видимые признаки реакции отсутствуют' and
              ({c[0], c[1]} & set(STRONG)) and ({c[0], c[1]} & set(ALK))]
    some_c = [c for c in cands if c[3] != 'видимые признаки реакции отсутствуют']
    chosen, used = [], set()
    for _ in range(80):
        if len(chosen) == 3:
            break
        use_none = level in ('general', 'gas') and none_c and rng.random() < 0.15 and \
            not any(x[3] == 'видимые признаки реакции отсутствуют' for x in chosen)
        pool = none_c if use_none else some_c
        if level == 'gas' and not any('запах' in x[3] and 'без' not in x[3] for x in chosen):
            pool = [c for c in some_c if 'запах' in c[3] and 'без' not in c[3]]   # ловушка: газ с запахом
        c = rng.choice(pool)
        if {c[0], c[1]} & used or any(x[3] == c[3] for x in chosen) and rng.random() < 0.9:
            continue
        chosen.append(c)
        used |= {c[0], c[1]}
    if len(chosen) < 3:
        raise Retry
    signs = list(dict.fromkeys(c[3] for c in chosen))
    extra = [s for s in EXTRA_SIGNS[level] if s not in signs]
    signs += rng.sample(extra, 4 - len(signs))
    signs = shuffled(rng, signs)
    left = []
    for a, b, _, _ in chosen:
        x, y = (a, b) if rng.random() < 0.5 else (b, a)
        left.append(f'{_p12_text(x)} и {_p12_text(y)}')
    o = match_opts(left, signs)
    a = {LET[i]: str(signs.index(c[3]) + 1) for i, c in enumerate(chosen)}
    q = rng.choice(STEM12) + END_M
    eqs = [e for e in (_eq_of(c[0], c[1]) for c in chosen) if e]
    e = ' '.join(f'{LET[i]}) {c[3]}.' for i, c in enumerate(chosen)) + (' Уравнения: ' + '; '.join(eq_text(x) for x in eqs)
                                                                        if eqs else '') + \
        '. Ответ: ' + ''.join(a[x] for x in LET[:3]) + '.'
    return pcard(pid, q, a, e, k='match', o=o, eqs=eqs,
                 p={'pairs': [[c[0], c[1]] for c in chosen], 'signs': signs, 'level': level})


def _solve12(p):
    a = {}
    for i, (x, y) in enumerate(p['pairs']):
        t = sign_text(obs_db(x, y), p['level'])
        if t not in p['signs']:
            return f'признак {x}+{y}: {t}'
        a[LET[i]] = str(p['signs'].index(t) + 1)
    return a


_F12 = lambda scale, trap: F(MATCH3 + ' (3 пары веществ, 4 признака)', 'как в демоверсии 2027 №12: «реагирующие вещества — '
                            'признак протекающей между ними реакции»', 'П', 7, scale, trap, ['1.6', '5.5'], SC2)


@proto('ch-oge-12-general', 'ОГЭ', 12, 'Признак реакции: газ, осадок, растворение осадка, нет видимых признаков',
       invariant='три пары веществ; признаки общего вида (газ / осадок / растворение осадка / нет признаков)',
       varies='пары растворов солей, кислот, щелочей и нерастворимых гидроксидов/карбонатов',
       answer_rule='газ — при образовании CO2, SO2, H2S, NH3; осадок — по таблице растворимости; нерастворимое основание '
                   'растворяется в кислоте; нейтрализация растворов идёт без видимых признаков',
       mistakes=['нейтрализацию NaOH + HCl считают «выделением газа»', 'карбонат + кислота — «осадок»',
                 'реакцию нерастворимого основания с кислотой считают «без признаков»'],
       solve=_solve12, kind='dict', kes=['1.6', '5.5'],
       fidelity=_F12('как в банке: «K2CO3 и HCl», «K2SiO3 и HCl», «Ca(OH)2 и HCl», «Mg(OH)2 и H2SO4»',
                     'нейтрализация без признаков, силикат + кислота — осадок'))
def g12_general(rng):
    return _gen12(rng, 'ch-oge-12-general', 'general', lambda a, b, ob: not ({a, b} & set(METAL12 + OX_B + OX_AM)))


@proto('ch-oge-12-precipitate-color', 'ОГЭ', 12, 'Признак реакции: цвет выпадающего осадка',
       invariant='три пары растворов; признаки — цвет осадка (белый, голубой, бурый, серо-зелёный, жёлтый, чёрный)',
       varies='катионы Cu2+, Fe2+, Fe3+, Ag+, Ba2+, Mg2+, Al3+, анионы OH−, SO4 2−, PO4 3−, S2−, I−, CO3 2−',
       answer_rule='Cu(OH)2 — голубой, Fe(OH)2 — серо-зелёный, Fe(OH)3 — бурый, AgI и Ag3PO4 — жёлтые, CuS, FeS, Ag2S — '
                   'чёрные, BaSO4, AgCl, CaCO3, Mg(OH)2, Al(OH)3 — белые',
       mistakes=['Fe(OH)3 называют зелёным', 'Ag3PO4 — белым', 'не замечают, что соль не даёт осадка'],
       solve=_solve12, kind='dict', kes=['1.6', '5.5'],
       fidelity=_F12('как в демоверсии 2027: «NaCl и AgNO3», «Fe2(SO4)3 и KOH», «CuSO4 и NaOH»', 'цвета гидроксидов железа'))
def g12_color(rng):
    return _gen12(rng, 'ch-oge-12-precipitate-color', 'color', lambda a, b, ob: 'растворение' not in ob)


@proto('ch-oge-12-gas', 'ОГЭ', 12, 'Признак реакции: выделение газа (цвет, запах) или белого осадка',
       invariant='три пары веществ; признаки — газ без запаха, газ с резким запахом, газ с запахом тухлых яиц, осадок',
       varies='карбонаты, сульфиты, сульфиды, соли аммония с кислотами/щелочами; металлы с кислотами',
       answer_rule='CO2 и H2 — без запаха, SO2 и NH3 — с резким запахом, H2S — запах тухлых яиц',
       mistakes=['SO2 считают газом без запаха', 'H2 из металла и кислоты «пахнет»', 'NH4Cl + NaOH — «без признаков»'],
       solve=_solve12, kind='dict', kes=['1.6', '5.5'],
       fidelity=_F12('как в банке: «K2SO3 и HCl», «K2CO3 и HCl», «Na2S и HCl», «NH4Br и NaOH»', 'SO2/CO2/H2S — различие по запаху'))
def g12_gas(rng):
    return _gen12(rng, 'ch-oge-12-gas', 'gas', lambda a, b, ob: not ({a, b} & set(INSOL12)))


@proto('ch-oge-12-solids', 'ОГЭ', 12, 'Признак реакции с участием твёрдых веществ и металлов (растворение, окраска, налёт)',
       invariant='три пары: нерастворимое вещество/металл + раствор; признаки — растворение с газом / окрашенным или '
                 'бесцветным раствором, выделение металла, водорода',
       varies='оксиды и гидроксиды (Cu, Fe, Mg, Zn, Al), карбонаты, сульфиды; металлы с кислотами и солями',
       answer_rule='соли меди(II) — голубые, железа(III) — жёлтые; карбонат/сульфид + кислота — газ; более активный металл '
                   'вытесняет медь (красный налёт)',
       mistakes=['CuO + HCl — «бесцветный раствор»', 'Cu + HCl — «газ»', 'Fe2O3 + H2SO4 — «голубой раствор»'],
       solve=_solve12, kind='dict', kes=['1.6', '4.3', '4.8'],
       fidelity=_F12('как в банке: «CuO и H2SO4», «Fe2O3 и H2SO4», «CaCO3 и HNO3», «Cu(NO3)2 и Fe», «Zn и HCl»',
                     'окраска раствора по катиону'))
def g12_solid(rng):
    return _gen12(rng, 'ch-oge-12-solids', 'solid', lambda a, b, ob: a in INSOL12 + METAL12 or b in INSOL12 + METAL12)


# ================================================================= ионы: запись и независимый разбор формул (13, 14)

SUPD = str.maketrans('0123456789+-', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻')
ION_F = {'NH4': 'NH4', 'Fe2': 'Fe', 'Fe3': 'Fe'}


def ion_txt(key, anion=False):
    if anion:
        f, q = (D.ANIONS[key][0], -D.ANIONS[key][1]) if key in D.ANIONS else ({'NO2': 'NO2'}[key], -1)
    elif key == 'H':
        f, q = 'H', 1
    else:
        f, q = D.CATIONS[key][0], D.CATIONS[key][1]
    ch = ('' if abs(q) == 1 else str(abs(q))) + ('+' if q > 0 else '-')
    return pretty(f) + ch.translate(SUPD)


ANION_Q = {'Cl': 1, 'Br': 1, 'I': 1, 'F': 1, 'NO3': 1, 'NO2': 1, 'OH': 1, 'SO4': 2, 'SO3': 2, 'S': 2, 'CO3': 2, 'SiO3': 2,
           'PO4': 3}


def dissociate(f):
    """Независимый разбор формулы электролита на ионы: [(катион, число, заряд), (анион, число, заряд)]."""
    m = re.match(r'^(\(NH4\)|NH4|[A-Z][a-z]?)(\d*)(.*)$', f)
    cat, nc, rest = m.group(1).strip('()'), int(m.group(2) or 1), m.group(3)
    m2 = re.match(r'^\((.+)\)(\d+)$', rest)
    if m2:
        an, na = m2.group(1), int(m2.group(2))
    else:
        m3 = re.match(r'^([A-Z][a-z]?)(\d+)$', rest)
        if m3 and m3.group(1) in ANION_Q:
            an, na = m3.group(1), int(m3.group(2))
        else:
            an, na = rest, 1
    qa = ANION_Q[an]
    qc = Fr(qa * na, nc)
    return [(cat, nc, qc), (an, na, -qa)]


def ion_key_txt(sym, q):
    ch = ('' if abs(q) == 1 else str(abs(q))) + ('+' if q > 0 else '-')
    return pretty(sym) + ch.translate(SUPD)


# ================================================================= 13. Электролитическая диссоциация

SALTS13 = [f for f in COMMON_SALTS if SALT[f][2] == 'р' and f not in EXOTIC] + ['Al2(SO4)3', 'Fe2(SO4)3', 'Cr2(SO4)3',
                                                                                'Cr(NO3)3', 'CrCl3']
SALTS13 = [f for f in dict.fromkeys(SALTS13) if f in SALT or f in ('Cr2(SO4)3', 'Cr(NO3)3', 'CrCl3')]
EL13 = SALTS13 + ['HCl', 'HNO3', 'H2SO4', 'HBr', 'HI', 'NaOH', 'KOH', 'LiOH', 'Ba(OH)2']
ION_SWAP_AN = {'SO4': 'SO3', 'SO3': 'SO4', 'S': 'SO4', 'NO3': 'NO2', 'CO3': 'SO3', 'PO4': 'SO4', 'Cl': 'Br', 'Br': 'Cl',
               'I': 'Cl', 'SiO3': 'CO3'}


def _ions13(f):
    """Генератор: ионы из базы (SALT/ACID/ALK) → [(ключ, число, текст)]."""
    if f in SALT:
        c, a, _ = SALT[f]
        cq, aq = D.CATIONS[c][1], D.ANIONS[a][1]
        from math import gcd
        g = gcd(cq, aq)
        return [(c, aq // g, ion_txt(c)), (a, cq // g, ion_txt(a, True))]
    if f in ACID:
        a = ACID[f]
        return [('H', D.ANIONS[a][1], ion_txt('H')), (a, 1, ion_txt(a, True))]
    if f in ALK:
        c = ALK[f]
        return [(c, 1, ion_txt(c)), ('OH', D.CATIONS[c][1], ion_txt('OH', True))]
    d = dissociate(f)
    return [(d[0][0], d[0][1], ion_key_txt(d[0][0], d[0][2])), (d[1][0], d[1][1], ion_key_txt(d[1][0], d[1][2]))]


def _solve13_ions(p):
    d = dissociate(p['f'])
    have = {(n, ion_key_txt(sym, q)) for sym, n, q in d}
    return ids_of([i for i, (n, t) in enumerate(p['opts']) if (n, t) in have])


_F13 = lambda scale, trap: F(MANY2, 'как в демоверсии 2027 №13 и банке: «Укажите, какие ионы и в каком количестве '
                            'образуются …», «При полной диссоциации 1 моль каких двух веществ …»', 'Б', 5, scale, trap,
                            ['5.4'], SC1M)


@proto('ch-oge-13-ions-of-salt', 'ОГЭ', 13, 'Какие ионы и в каком количестве образуются при диссоциации 1 моль соли',
       invariant='1 моль соли; из пяти вариантов «n моль иона» выбрать два верных (катион и анион)',
       varies='соль (нитраты, сульфаты, хлориды, фосфаты Al, Fe, Cu, Mg, Ca, Na, K, NH4 …), отвлекающие ионы',
       answer_rule='число катионов = индекс металла, число анионов = индекс кислотного остатка; заряд иона — по валентности',
       mistakes=['Fe3+ путают с Fe2+', 'сульфат-ион путают с сульфит-ионом', 'число ионов берут из индекса кислорода'],
       solve=_solve13_ions, kind='param', kes=['5.4'],
       fidelity=_F13('как в демоверсии 2027 (нитрат алюминия) и банке (хлорид железа(III), сульфид калия, сульфат меди(II))',
                     'количество и заряд ионов, сульфат/сульфит'))
def g13_ions(rng):
    f = rng.choice([x for x in SALTS13 if x in SALT])
    (c, nc, ct), (a, na, at) = _ions13(f)
    right = [(nc, ct), (na, at)]
    wrong = {(na, ct), (nc, at), (1, ct) if nc != 1 else (2, ct), (1, at) if na != 1 else (2, at)}
    if c in ('Fe2', 'Fe3'):
        wrong.add((nc, ion_txt('Fe3' if c == 'Fe2' else 'Fe2')))
    if a in ION_SWAP_AN:
        wrong.add((na, ion_txt(ION_SWAP_AN[a], True)))
    wrong = [w for w in wrong if w not in right]
    if len(wrong) < 3:
        raise Retry
    items = shuffled(rng, right + rng.sample(wrong, 3))
    o = opts([f'{n} моль {t}' for n, t in items])
    a_ = ids_of([items.index(x) for x in right])
    q = (f'Какие ионы и в каком количестве образуются при полной диссоциации в водном растворе 1 моль {gen(f)}? '
         'Запишите номера выбранных ответов.')
    e = f'{disp(f)} = {nc if nc > 1 else ""}{ct} + {na if na > 1 else ""}{at}: {nc} моль {ct} и {na} моль {at}. Ответ: {"".join(a_)}.'
    return pcard('ch-oge-13-ions-of-salt', q, a_, e, k='many', o=o, p={'f': f, 'opts': items})


def _count13(f, what):
    d = dissociate(f)
    nc, na = d[0][1], d[1][1]
    return {'ions': nc + na, 'cat': nc, 'an': na, 'both': (nc, na)}[what]


def _solve13_count(p):
    return ids_of([i for i, f in enumerate(p['items']) if _count13(f, p['what']) == p['val']])


@proto('ch-oge-13-count-ions', 'ОГЭ', 13, 'При диссоциации 1 моль каких веществ образуется N моль ионов (катионов, анионов)',
       invariant='пять веществ (формулы или названия); выбрать два, при диссоциации 1 моль которых образуется заданное '
                 'число моль ионов / катионов / анионов',
       varies='вопрос (всего ионов, катионов, анионов, «n катионов и m анионов»), число, вещества',
       answer_rule='уравнение диссоциации: число катионов и анионов — по индексам в формуле',
       mistakes=['считают атомы кислорода', 'для сульфата алюминия получают 2 иона', 'путают катионы и анионы'],
       solve=_solve13_count, kind='param', kes=['5.4'],
       fidelity=_F13('как в банке: «3 моль ионов», «2 моль катионов», «1 моль катионов и 1 моль анионов»; соли, кислоты, '
                     'щёлочи', 'катионы/анионы, индексы'))
def g13_count(rng):
    what = rng.choice(['ions', 'ions', 'cat', 'an', 'both'])
    pool = EL13
    vals = Counter(_count13_gen(f, what) for f in pool)
    val = rng.choice([v for v, n in vals.items() if n >= 2])
    good = [f for f in pool if _count13_gen(f, what) == val]
    bad = [f for f in pool if _count13_gen(f, what) != val]
    items = shuffled(rng, rng.sample(good, 2) + rng.sample(bad, 3))
    names = rng.random() < 0.5
    o = opts([name(f) if names else disp(f) for f in items])
    a = ids_of([i for i, f in enumerate(items) if f in good])
    txt = {'ions': f'{val} моль ионов', 'cat': f'{val} моль катионов', 'an': f'{val} моль анионов'}.get(what) or \
        f'{val[0]} моль катионов и {val[1]} моль анионов'
    q = f'Выберите два вещества, при полной диссоциации 1 моль каждого из которых в растворе образуется {txt}. Запишите номера выбранных ответов.'
    e = '; '.join(f'{disp(f)}: {_ions13(f)[0][1]} + {_ions13(f)[1][1]}' for f in items) + f'. Ответ: {"".join(a)}.'
    return pcard('ch-oge-13-count-ions', q, a, e, k='many', o=o, p={'items': items, 'what': what, 'val': val})


def _count13_gen(f, what):
    (_, nc, _), (_, na, _) = _ions13(f)
    return {'ions': nc + na, 'cat': nc, 'an': na, 'both': (nc, na)}[what]


WEAK13 = ['HNO2', 'H2S', 'H2SO3', 'H2CO3', 'HF', 'CH3COOH', 'NH3·H2O']
STRONG13 = ['HCl', 'HNO3', 'H2SO4', 'HBr', 'HI', 'HClO4', 'NaOH', 'KOH', 'LiOH', 'Ba(OH)2', 'NaCl', 'KNO3', 'CuSO4',
            'MgCl2', 'Na2SO4', 'K2CO3', 'Na3PO4', 'NH4Cl', 'ZnSO4', 'AlCl3', 'Ca(NO3)2', 'FeCl3', 'Na2SiO3', 'K2S']
NONEL13 = ['O2', 'N2', 'S', 'P', 'CO', 'NO', 'N2O', 'SiO2', 'CuO', 'Fe2O3', 'Al2O3', 'C2H5OH', 'C12H22O11', 'C6H12O6', 'CH4',
           'H2']


def el_class(f):
    """Независимая классификация: сильный / слабый / неэлектролит — по классу вещества (правила 9 кл.)."""
    c = classify(f) if f not in ('NH3·H2O', 'CH3COOH', 'C2H5OH', 'C12H22O11', 'C6H12O6') else {'особое'}
    if f in ('NH3·H2O', 'CH3COOH'):
        return 'слабый'
    if 'простое вещество' in c or 'оксид' in c or f in ('C2H5OH', 'C12H22O11', 'C6H12O6', 'CH4'):
        return 'неэлектролит'
    if 'кислота' in c:
        return 'сильный' if f in ('HCl', 'HBr', 'HI', 'HNO3', 'H2SO4', 'HClO4') else 'слабый'
    if 'щёлочь' in c or 'соль' in c:
        return 'сильный'
    return '?'


def _solve13_el(p):
    return ids_of([i for i, f in enumerate(p['items']) if (el_class(f) in p['want'])])


@proto('ch-oge-13-electrolytes', 'ОГЭ', 13, 'Сильные и слабые электролиты, неэлектролиты',
       invariant='пять веществ; выбрать два слабых электролита / два сильных / два неэлектролита / два электролита',
       varies='вопрос и вещества (кислоты, щёлочи, соли, оксиды, простые вещества, органические вещества)',
       answer_rule='сильные: HCl, HBr, HI, HNO3, H2SO4, HClO4, щёлочи, растворимые соли; слабые: H2S, HNO2, H2SO3, H2CO3, '
                   'HF, CH3COOH, NH3·H2O; неэлектролиты: оксиды, простые вещества, спирт, сахар, глюкоза',
       mistakes=['H2S считают сильной кислотой', 'оксиды считают электролитами', 'сахар — электролит'],
       solve=_solve13_el, kind='dict', kes=['5.4'],
       fidelity=_F13('как в банке: «два слабых электролита», «два неэлектролита», «два электролита»',
                     'сила кислот, оксиды — неэлектролиты'))
def g13_el(rng):
    want = rng.choice(['слабый', 'неэлектролит', 'сильный', 'электролит'])
    pools = {'слабый': WEAK13, 'сильный': STRONG13, 'неэлектролит': NONEL13}
    if want == 'электролит':
        good_pool, bad_pool, wset = WEAK13 + STRONG13, NONEL13, {'слабый', 'сильный'}
    else:
        good_pool = pools[want]
        bad_pool = [f for k, v in pools.items() if k != want for f in v]
        wset = {want}
    items = shuffled(rng, rng.sample(good_pool, 2) + rng.sample(bad_pool, 3))
    names = rng.random() < 0.5 and all(f in SUB for f in items)
    o = opts([name(f) if names else disp(f) for f in items])
    a = ids_of([i for i, f in enumerate(items) if f in good_pool])
    word = {'слабый': 'два слабых электролита', 'сильный': 'два сильных электролита', 'неэлектролит': 'два неэлектролита',
            'электролит': 'два электролита'}[want]
    q = f'Из предложенного перечня веществ выберите {word}. Запишите номера выбранных ответов.'
    e = '; '.join(f'{disp(f)} — {el_class(f)}' for f in items) + f'. Ответ: {"".join(a)}.'
    return pcard('ch-oge-13-electrolytes', q, a, e, k='many', o=o, p={'items': items, 'want': sorted(wset)})


# ================================================================= 14. Реакции ионного обмена: сокращённое ионное уравнение

def _ion_events(a, b):
    """Генератор: какие пары ионов связываются при сливании растворов a и b; None — одно из веществ не сильный
    растворимый электролит (в сокращённом уравнении осталось бы в молекулярном виде)."""
    ia, ib = _ions(a), _ions(b)
    if not ia or not ib or a in ('H3PO4',) or b in ('H3PO4',):
        return None
    if ia[0] == ib[0] or ia[1] == ib[1]:
        return frozenset()
    if 'HNO3' in (a, b) and ({ia[1], ib[1]} & {'S', 'SO3', 'I', 'Br'} or {ia[0], ib[0]} & {'Fe2'}):
        return None
    ev = set()
    for c, an in ((ia[0], ib[1]), (ib[0], ia[1])):
        t = _prod_obs(c, an)
        if t is None:
            return None
        if t or (c, an) == ('H', 'OH'):
            ev.add((c, an))
    return frozenset(ev)


# цели: (катион, анион) → (левая часть {ион: коэфф.}, правая часть {частица: коэфф.})
def _target(c, a):
    if (c, a) == ('H', 'OH'):
        return ({'H+': 1, 'OH-': 1}, {'H2O': 1})
    if c == 'H':
        if a == 'SiO3':
            return ({'H+': 2, 'SiO3 2-': 1}, {'H2SiO3': 1})
        g = GAS_OF[a]
        return ({'H+': 2, f'{a} 2-': 1}, {g: 1} if a == 'S' else {g: 1, 'H2O': 1})
    if (c, a) == ('NH4', 'OH'):
        return ({'NH4+': 1, 'OH-': 1}, {'NH3': 1, 'H2O': 1})
    cq, aq = D.CATIONS[c][1], D.ANIONS[a][1]
    from math import gcd
    g = gcd(cq, aq)
    f = D._salt_formula(c, a) if a != 'OH' else [x for x, k in {**BINS, **BAMP}.items() if k == c][0]
    sym_c = D.CATIONS[c][0]
    return ({f'{sym_c}{cq if cq > 1 else ""}+': aq // g, f'{a} {aq if aq > 1 else ""}-'.replace(' -', '-'): cq // g}, {f: 1})


def ionic_eq_text(t):
    lhs, rhs = t

    def sp(s):
        m = re.match(r'^(.+?)\s?(\d?)([+-])$', s)
        if not m:
            return pretty(s)
        return pretty(m.group(1)) + (m.group(2) + m.group(3)).translate(SUPD)
    side = lambda d: ' + '.join((f'{k}' if k > 1 else '') + sp(s) for s, k in d.items())
    return f'{side(lhs)} = {side(rhs)}'


TARGETS14 = [('H', 'OH'), ('H', 'CO3'), ('H', 'SO3'), ('H', 'S'), ('H', 'SiO3'), ('NH4', 'OH'), ('Ba', 'SO4'),
             ('Ba', 'CO3'), ('Ca', 'CO3'), ('Ag', 'Cl'), ('Ag', 'Br'), ('Ag', 'I'), ('Ag', 'PO4'), ('Ba', 'PO4'),
             ('Ca', 'PO4'), ('Mg', 'OH'), ('Cu', 'OH'), ('Fe2', 'OH'), ('Fe3', 'OH'), ('Al', 'OH'), ('Zn', 'OH'),
             ('Cu', 'S'), ('Zn', 'S'), ('Fe2', 'S'), ('Mg', 'CO3'), ('Zn', 'CO3'), ('Ba', 'SO3'), ('Ca', 'SO3'),
             ('Mg', 'PO4'), ('Zn', 'PO4')]
DIST14_EXTRA = ['BaCO3', 'CaCO3', 'BaSO4', 'AgCl', 'Mg(OH)2', 'Cu(OH)2', 'Fe(OH)3', 'Al(OH)3', 'Zn(OH)2', 'CuS', 'FeS',
                'ZnS', 'Ca3(PO4)2', 'H2S', 'H2SiO3', 'CO2', 'SO2', 'NH3', 'H3PO4', 'MgO', 'CuO', 'CaO', 'BaO', 'ZnO',
                'Al2O3', 'Fe2O3', 'Ba', 'Ca', 'Zn', 'Mg', 'Cu', 'Fe', 'Al', 'H2O', 'MgCO3', 'Ag2O']


def _providers(ion_key, is_anion):
    out = []
    for f in SOL_EL:
        i = _ions(f)
        if i and (i[1] if is_anion else i[0]) == ion_key and f not in EXOTIC:
            out.append(f)
    return out


_BYLHS = None


def _by_lhs():
    global _BYLHS
    if _BYLHS is None:
        _BYLHS = {}
        for x in chemdb.load()['reactions']:
            _BYLHS.setdefault(frozenset(x['lhs']), []).append(x)
    return _BYLHS


def net_ionic_db(a, b):
    """solve: найти реакцию заново по реагентам в базе, записать полное ионное уравнение (сильные растворимые
    электролиты — на ионы) и сократить одинаковые ионы. Возвращает (левая часть, правая часть) или None."""
    ps = products_db([a, b], '')
    if ps is None:
        return None
    r = [x for x in _by_lhs().get(frozenset((a, b)), []) if frozenset(x['rhs']) == ps]
    if not r:
        return None
    r = r[0]
    left, right = Counter(), Counter()
    for side, fs, ks in ((left, r['lhs'], r['k'][0]), (right, r['rhs'], r['k'][1])):
        for f, k in zip(fs, ks):
            parts = _split_strong(f)
            if parts is None:
                side[f] += k
            else:
                for sp, n in parts:
                    side[sp] += n * k
    for s in list(left):
        common = min(left[s], right.get(s, 0))
        left[s] -= common
        right[s] -= common
    left = {s: n for s, n in left.items() if n}
    right = {s: n for s, n in right.items() if n}
    from math import gcd
    g = 0
    for v in list(left.values()) + list(right.values()):
        g = gcd(g, v)
    return ({s: n // g for s, n in left.items()}, {s: n // g for s, n in right.items()})


STRONG_ACIDS = {'HCl': [('H+', 1), ('Cl-', 1)], 'HBr': [('H+', 1), ('Br-', 1)], 'HI': [('H+', 1), ('I-', 1)],
                'HNO3': [('H+', 1), ('NO3-', 1)], 'H2SO4': [('H+', 2), ('SO4 2-', 1)]}


def _split_strong(f):
    """Сильный растворимый электролит → ионы (для записи полного ионного уравнения); иначе None."""
    if f in STRONG_ACIDS:
        return STRONG_ACIDS[f]
    if f in ('NaOH', 'KOH', 'LiOH', 'Ba(OH)2', 'Ca(OH)2'):
        d = dissociate(f)
    elif re.match(r'^(\(NH4\)|NH4|[A-Z][a-z]?)', f) and parse_formula(f).keys() - {'H', 'O'} and f not in (
            'H2O', 'H2S', 'H2SiO3', 'H3PO4', 'CO2', 'SO2', 'NH3'):
        try:
            d = dissociate(f)
        except Exception:  # noqa: BLE001
            return None
        cat = {'NH4': 'NH4'}.get(d[0][0], d[0][0])
        key_c = {('Fe', 2): 'Fe2', ('Fe', 3): 'Fe3'}.get((cat, d[0][2]), cat)
        if D.SOL.get((key_c, d[1][0])) != 'р':
            return None
    else:
        return None
    (c, nc, qc), (a, na, qa) = d
    cs = f'{c}{qc if qc > 1 else ""}+'
    as_ = f'{a} {abs(qa) if abs(qa) > 1 else ""}-'.replace(' -', '-')
    return [(cs, nc), (as_, na)]


def _solve14(p):
    tgt = (p['t'][0], p['t'][1])
    items = p['items']
    hits = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            ne = net_ionic_db(items[i], items[j])
            if ne == tgt:
                hits.append((i, j))
    if len(hits) != 1:
        return f'пар с этим уравнением: {hits}'
    return ids_of(list(hits[0]))


def _gen14(rng, pid, names):
    c, a = rng.choice(TARGETS14)
    tgt = _target(c, a)
    pc_ = _providers(c, False)
    pa_ = _providers(a, True)
    right = None
    for _ in range(30):
        x, y = rng.choice(pc_), rng.choice(pa_)
        if x != y and _ion_events(x, y) == frozenset({(c, a)}):
            right = [x, y]
            break
    if not right:
        raise Retry
    # отвлекающие: нерастворимые/слабые/простые вещества с теми же ионами, «лишние» соли
    cands = [f for f in DIST14_EXTRA + SOL_EL if f not in right and (not names or f in SUB)]
    for _ in range(50):
        dist = rng.sample(cands, 4)
        items = right + dist
        ok = True
        for i in range(6):
            for j in range(i + 1, 6):
                if (i, j) == (0, 1):
                    continue
                ev = _ion_events(items[i], items[j])
                if ev == frozenset({(c, a)}):
                    ok = False
        # хотя бы один отвлекающий содержит «нужный» ион в нерастворимом/молекулярном виде
        related = [f for f in dist if f in DIST14_EXTRA and any(e in parse_formula(f) for e in
                                                               (set(parse_formula(right[0])) | set(parse_formula(right[1])))
                                                               - {'H', 'O'})]
        if ok and related:
            break
    else:
        raise Retry
    items = shuffled(rng, items)
    o = opts([name(f) if names else disp(f) for f in items])
    ans = ids_of([items.index(f) for f in right])
    eqt = ionic_eq_text(tgt)
    if names:
        q = ('Выберите два вещества, при взаимодействии которых в водном растворе протекает реакция, выраженная '
             f'сокращённым ионным уравнением\n{eqt}\nЗапишите номера выбранных ответов.')
    else:
        q = ('Выберите два исходных вещества, взаимодействию которых соответствует сокращённое ионное уравнение реакции\n'
             f'{eqt}\nЗапишите номера выбранных ответов.')
    eq = _eq_of(right[0], right[1])
    e = (f'{disp(right[0])} и {disp(right[1])} — растворимые сильные электролиты: ' +
         (eq_text(eq) + '; ' if eq else '') + f'сокращённое уравнение {eqt}. Остальные вещества — нерастворимые, '
         'слабые электролиты или дают другое уравнение.' + f' Ответ: {"".join(ans)}.')
    return pcard(pid, q, ans, e, k='many', o=o, p={'items': items, 't': [tgt[0], tgt[1]]}, eqs=[eq] if eq else None)


_F14 = lambda scale: F(MANY2, 'как в демоверсии 2027 №14: «…выберите названия двух веществ, взаимодействию которых '
                       'в растворе соответствует сокращённое ионное уравнение»; шесть вариантов', 'Б', 3, scale,
                       'нерастворимое вещество или слабый электролит с тем же ионом; пара, дающая «лишний» осадок/воду',
                       ['5.5'], SC1M)


@proto('ch-oge-14-reactants', 'ОГЭ', 14, 'Сокращённое ионное уравнение → два исходных вещества (формулы)',
       invariant='сокращённое ионное уравнение и шесть формул; выбрать два вещества, дающих именно это уравнение',
       varies='уравнение (осадок, газ, вода), вещества-источники ионов, отвлекающие (нерастворимые, слабые, металлы, '
              'оксиды, соли с «лишним» ионом)',
       answer_rule='оба вещества — растворимые сильные электролиты, содержащие нужные ионы; другие их ионы не должны '
                   'давать осадок, газ или воду',
       mistakes=['берут нерастворимую соль (BaCO3, CaCO3)', 'берут Ba(OH)2 + H2SO4 для Ba2+ + SO4 2−',
                 'берут слабую кислоту H2S или металл'],
       solve=_solve14, kind='param', kes=['5.5'],
       fidelity=_F14('как в банке: «H+ + OH− = H2O», «CO3 2− + 2H+», «Al3+ + 3OH−», «Ba2+ + SO4 2−»'))
def g14_formulas(rng):
    return _gen14(rng, 'ch-oge-14-reactants', False)


@proto('ch-oge-14-names', 'ОГЭ', 14, 'Сокращённое ионное уравнение → два исходных вещества (названия)',
       invariant='сокращённое ионное уравнение и шесть названий веществ; выбрать два',
       varies='как в ch-oge-14-reactants',
       answer_rule='как в ch-oge-14-reactants; дополнительно — узнать вещество по названию',
       mistakes=['оксид бария вместо хлорида бария', 'карбонат кальция вместо карбоната натрия'],
       solve=_solve14, kind='param', kes=['5.5'],
       fidelity=_F14('как в демоверсии 2027: «серная кислота, гидроксид бария, сульфат магния, оксид бария, барий, сульфат калия»'))
def g14_names(rng):
    return _gen14(rng, 'ch-oge-14-names', True)


ION_CAT14 = ['H', 'NH4', 'Na', 'K', 'Li', 'Ba', 'Ca', 'Mg', 'Zn', 'Cu', 'Fe2', 'Fe3', 'Al', 'Ag']
ION_AN14 = ['OH', 'Cl', 'Br', 'I', 'NO3', 'SO4', 'SO3', 'S', 'CO3', 'PO4', 'SiO3']


def _ion_pair_kind(c, a):
    """solve: что даёт пара ионов — 'газ', 'осадок', 'вода' или '' (по таблице растворимости и списку газов)."""
    if c == 'H':
        if a == 'OH':
            return 'вода'
        if a in ('CO3', 'SO3', 'S'):
            return 'газ'
        return 'осадок' if a == 'SiO3' else ''
    if (c, a) == ('NH4', 'OH'):
        return 'газ'
    s = D.SOL.get((c, a))
    return 'осадок' if s == 'н' else ('' if s == 'р' else '?')


def _solve14_ions(p):
    items = p['items']
    hits = []
    for i, (ki, ti) in enumerate(items):
        for j, (kj, tj) in enumerate(items):
            if ti == 'c' and tj == 'a' and _ion_pair_kind(ki, kj) == p['want']:
                hits.append(tuple(sorted((i, j))))
    return ids_of(list(hits[0])) if len(hits) == 1 else f'пар: {hits}'


@proto('ch-oge-14-ion-pairs', 'ОГЭ', 14, 'Два иона, взаимодействие которых даёт газ (осадок, воду)',
       invariant='шесть ионов; выбрать два, взаимодействие которых сопровождается выделением газа (образованием осадка)',
       varies='вопрос (газ / осадок), ионы',
       answer_rule='газ: H+ с CO3 2−, SO3 2−, S2−; NH4+ с OH−; осадок — по таблице растворимости',
       mistakes=['H+ + SO4 2− «даёт газ»', 'Na+ + OH− «даёт осадок»'],
       solve=_solve14_ions, kind='param', kes=['5.5'],
       fidelity=F(MANY2, 'как в банке: «Выберите два иона, взаимодействие которых сопровождается выделением газа / '
                  'образованием осадка»; шесть ионов', 'Б', 3, 'ионы банка: H+, Ca2+, Na+, OH−, S2−, PO4 3−, NH4+, SO3 2−',
                  'ионы-«соседи», не дающие газа/осадка', ['5.5'], SC1M))
def g14_ions(rng):
    want = rng.choice(['газ', 'газ', 'осадок'])
    for _ in range(60):
        cats = rng.sample(ION_CAT14, 3)
        ans = rng.sample(ION_AN14, 3)
        pairs = [(c, a) for c in cats for a in ans if _prod_obs(c, a)]
        good = [(c, a) for c, a in pairs if (_prod_obs(c, a) or '').startswith('газ' if want == 'газ' else 'осадок')
                and not (want == 'газ' and False)]
        amb = [(c, a) for c in cats for a in ans if _prod_obs(c, a) is None]
        if len(good) == 1 and not amb and not ((want == 'газ') and any(
                (_prod_obs(c, a) or '').startswith('осадок') and c == 'H' for c, a in pairs)):
            break
    else:
        raise Retry
    items = shuffled(rng, [(c, 'c') for c in cats] + [(a, 'a') for a in ans])
    o = opts([ion_txt(k, t == 'a') for k, t in items])
    c, a = good[0]
    res = ids_of([items.index((c, 'c')), items.index((a, 'a'))])
    q = (f'Выберите два иона, взаимодействие которых сопровождается '
         f'{"выделением газа" if want == "газ" else "образованием осадка"}. Запишите номера выбранных ответов.')
    e = f'{ionic_eq_text(_target(c, a))}. Остальные пары ионов не дают ни газа, ни осадка. Ответ: {"".join(res)}.'
    return pcard('ch-oge-14-ion-pairs', q, res, e, k='many', o=o,
                 p={'items': [[k, t] for k, t in items], 'want': want})


# ================================================================= 15. Окислительно-восстановительные процессы

EL_OX = {'S': [-2, 0, 4, 6], 'N': [-3, 0, 1, 2, 3, 4, 5], 'Cl': [-1, 0, 1, 3, 5, 7], 'Br': [-1, 0, 1, 5, 7],
         'I': [-1, 0, 1, 5, 7], 'P': [-3, 0, 3, 5], 'C': [-4, 0, 2, 4], 'Mn': [0, 2, 4, 6, 7], 'Cr': [0, 2, 3, 6],
         'Fe': [0, 2, 3], 'Cu': [0, 1, 2], 'O': [-2, -1, 0], 'H': [-1, 0, 1], 'Si': [-4, 0, 4], 'Zn': [0, 2],
         'Al': [0, 3], 'Mg': [0, 2], 'Au': [0, 1, 3], 'Ag': [0, 1], 'Na': [0, 1], 'Ca': [0, 2], 'Ba': [0, 2]}
DIATOMIC = {'H', 'N', 'O', 'Cl', 'Br', 'I', 'F'}


def ox_sup(n):
    return '⁰' if n == 0 else (('⁺' if n > 0 else '⁻') + str(abs(n)).translate(SUPD))


def scheme_text(el, a, b):
    """Схема процесса: «Cl₂⁰ → 2Cl⁻¹», «S⁻² → S⁺⁴», «2N⁻³ → N₂⁰»."""
    if el in DIATOMIC and a == 0:
        return f'{el}₂{ox_sup(0)} → 2{el}{ox_sup(b)}'
    if el in DIATOMIC and b == 0:
        return f'2{el}{ox_sup(a)} → {el}₂{ox_sup(0)}'
    return f'{el}{ox_sup(a)} → {el}{ox_sup(b)}'


def _solve15_scheme(p):
    return {LET[i]: ('1' if b > a else '2') for i, (el, a, b) in enumerate(p['schemes'])}


@proto('ch-oge-15-scheme-process', 'ОГЭ', 15, 'Схема процесса → окисление или восстановление',
       invariant='три схемы изменения степени окисления атома; для каждой — окисление или восстановление',
       varies='элемент (S, N, Cl, Br, I, P, C, Mn, Cr, Fe, Cu, H, O, металлы), начальная и конечная степени окисления',
       answer_rule='степень окисления повышается — окисление (электроны отдаются), понижается — восстановление',
       mistakes=['путают направление: повышение называют восстановлением', 'сбиваются на отрицательных степенях: −3 → 0'],
       solve=_solve15_scheme, kind='param', kes=['5.3'],
       fidelity=F(MATCH3 + ' (два варианта: окисление, восстановление)', 'как в демоверсии 2027 №15: «схема процесса, '
                  'происходящего в ОВР — название процесса»', 'Б', 4,
                  'элементы и степени окисления банка: Fe+3→Fe0, Cl2 0→2Cl+1, S−2→S+4, N+5→N−3, Mn+7→Mn+4',
                  'отрицательные степени окисления, двухатомные молекулы', ['5.3'], SC1))
def g15_scheme(rng):
    schemes = []
    els = rng.sample(list(EL_OX), 3)
    for el in els:
        a, b = rng.sample(EL_OX[el], 2)
        schemes.append((el, a, b))
    if len({b > a for _, a, b in schemes}) == 1 and rng.random() < 0.7:
        raise Retry
    o = match_opts([scheme_text(*x) for x in schemes], ['окисление', 'восстановление'])
    a_ = {LET[i]: ('1' if b > a else '2') for i, (el, a, b) in enumerate(schemes)}
    q = ('Установите соответствие между схемой процесса, происходящего в окислительно-восстановительной реакции, '
         'и названием этого процесса: к каждой позиции, обозначенной буквой, подберите соответствующую позицию, '
         'обозначенную цифрой.' + END_M)
    e = ' '.join(f'{LET[i]}) {el}: {a:+d} → {b:+d} — степень окисления {"повышается, окисление" if b > a else "понижается, восстановление"}.'
                 .replace('+0', '0') for i, (el, a, b) in enumerate(schemes)) + ' Ответ: ' + ''.join(a_[x] for x in LET[:3]) + '.'
    return pcard('ch-oge-15-scheme-process', q, a_, e, k='match', o=o, p={'schemes': [list(x) for x in schemes]})


ROLE_T = ['окислитель', 'восстановитель', 'и окислитель, и восстановитель', 'не проявляет окислительно-восстановительных свойств']
ROLE_EL = {'N': 'азот', 'S': 'сера', 'Cl': 'хлор', 'Fe': 'железо', 'P': 'фосфор', 'C': 'углерод', 'Br': 'бром',
           'Mn': 'марганец', 'Cu': 'медь', 'H': 'водород', 'O': 'кислород'}
ROLE_EL_GEN = {'N': 'азота', 'S': 'серы', 'Cl': 'хлора', 'Fe': 'железа', 'P': 'фосфора', 'C': 'углерода', 'Br': 'брома',
               'Mn': 'марганца', 'Cu': 'меди', 'H': 'водорода', 'O': 'кислорода'}


def el_role(r, el):
    """Роль элемента в реакции по степеням окисления (генератор): индекс в ROLE_T или None."""
    src = [f for f in r['lhs'] if el in parse_formula(f)]
    if len(src) != 1:
        return None
    a = ox_states(src[0])[el]
    if len(a) != 1:
        return None
    a = a[0]
    rs = {x for f in r['rhs'] if el in parse_formula(f) for x in ox_states(f)[el]}
    up, down = any(x > a for x in rs), any(x < a for x in rs)
    return 2 if up and down else (0 if down else (1 if up else 3))


def _solve15_role(p):
    el = p['el']
    out = {}
    for i, (lhs, rhs) in enumerate(p['rx']):
        ch = redox_changes(lhs, rhs).get(el)
        if not ch:
            k = 3
        else:
            before, after = ch
            (b0,) = tuple(before) if len(before) == 1 else (None,)
            new = after - before
            k = 2 if any(x > b0 for x in new) and any(x < b0 for x in new) else (0 if all(x < b0 for x in new) else 1)
        out[LET[i]] = str(p['order'].index(k) + 1)
    return out


R15 = [r for r in D.REACTIONS if 1 <= len(r['lhs']) <= 3 and not any(x in EXOTIC for x in r['lhs'] + r['rhs'])]


# Прототип «свойство элемента в реакции» (формат прошлых лет) удалён: в демо 2027 и банке №15 такого формата нет.


# ================================================================= 16. Безопасность, лаборатория, смеси

SAFE_T = {t: v for _, t, v in D.SAFETY}
STEM16 = {'лаб': 'Из перечисленных суждений о правилах работы с веществами и оборудованием в школьной лаборатории '
                 'выберите верное(-ые) суждение(-я).',
          'быт': 'Из перечисленных суждений о правилах безопасного обращения с веществами в лаборатории и быту '
                 'выберите верное(-ые) суждение(-я).',
          'смеси': 'Из перечисленных суждений о веществах, смесях и методах разделения смесей выберите верное(-ые) '
                   'суждение(-я).'}
END16 = ' Запишите в поле ответа номер(а) верного(-ых) суждения(-й).'


def _pick_statements(rng, pool):
    """Четыре суждения, верных — от одного до трёх."""
    n_true = rng.choice([1, 2, 2, 3])
    tr = [x for x in pool if x[1]]
    fl = [x for x in pool if not x[1]]
    items = rng.sample(tr, n_true) + rng.sample(fl, 4 - n_true)
    return shuffled(rng, items)


def _solve16(p):
    return ids_of([i for i, t in enumerate(p['items']) if SAFE_T.get(t)])


_F16 = lambda scale, trap: F('номер(а) верного(-ых) суждения(-й): от одной до трёх цифр, порядок не важен',
                            'как в демоверсии 2027 №16: «Из перечисленных суждений … выберите верное(-ые) суждение(-я)», '
                            'четыре суждения', 'Б', 5, scale, trap, ['1.1', '6.1'], SC1M)


@proto('ch-oge-16-lab', 'ОГЭ', 16, 'Правила работы в школьной лаборатории (посуда, нагревание, вытяжной шкаф)',
       invariant='четыре суждения о правилах работы в лаборатории; выбрать верные (одно — три)',
       varies='суждения о нагревании, посуде (ступка, выпарительная чашка, мерный цилиндр), вытяжном шкафе, '
              'отборе реактивов, запахе, разбавлении кислоты',
       answer_rule='правила техники безопасности школьного практикума',
       mistakes=['ступку путают с выпарительной чашкой', 'считают, что CO2 получают только под тягой',
                 'пробирку после нагревания закрывают пробкой'],
       solve=_solve16, kind='dict', kes=['1.1', '6.1'],
       fidelity=_F16('как в банке: нагревание пробирки, ступка/чашка, вытяжной шкаф для H2S, NH3, Cl2', 'похожие приборы'))
def g16_lab(rng):
    items = _pick_statements(rng, [(t, v) for tp, t, v in D.SAFETY if tp == 'лаб'])
    return _card16(rng, 'ch-oge-16-lab', items, 'лаб')


@proto('ch-oge-16-household', 'ОГЭ', 16, 'Безопасное обращение с веществами в быту и лаборатории',
       invariant='четыре суждения о правилах обращения с бытовой химией (и лабораторными веществами); выбрать верные',
       varies='суждения о чистящих средствах, отбеливателях, удобрениях, растворителях, газе, ртути, батарейках',
       answer_rule='средства со щёлочью/кислотой — в перчатках, хлорсодержащие средства не смешивают с кислотными, '
                   'горючие жидкости — вдали от огня, ртуть и батарейки — в спецпункты',
       mistakes=['считают безопасными отбеливатели', 'разрешают сливать растворители в канализацию'],
       solve=_solve16, kind='dict', kes=['6.1'],
       fidelity=_F16('как в банке: «препараты бытовой химии», «Белизна», «ядохимикаты», «лакокрасочные покрытия»',
                     'бытовые вещества'))
def g16_house(rng):
    pool = [(t, v) for tp, t, v in D.SAFETY if tp == 'быт']
    items = _pick_statements(rng, pool)
    if rng.random() < 0.4:   # одно суждение — из лабораторных правил, как в смешанных заданиях банка
        lab = [(t, v) for tp, t, v in D.SAFETY if tp == 'лаб']
        i = rng.randrange(4)
        cand = [x for x in lab if x[1] == items[i][1]]
        items[i] = rng.choice(cand)
    return _card16(rng, 'ch-oge-16-household', items, 'быт')


def _card16(rng, pid, items, topic):
    o = opts([t for t, _ in items])
    a = ids_of([i for i, (t, v) in enumerate(items) if v])
    q = STEM16[topic] + END16
    e = ' '.join(f'{i + 1}) {"верно" if v else "неверно"}.' for i, (t, v) in enumerate(items)) + f' Ответ: {"".join(a)}.'
    return pcard(pid, q, a, e, k='many', o=o, p={'items': [t for t, _ in items]})


# смеси: фраза (род. падеж) → (категория, верные способы, заведомо неверные способы)
MIX16 = {
    'речного песка и воды': ('взвесь', {'фильтрованием', 'отстаиванием'}, {'с помощью магнита', 'с помощью делительной воронки'}),
    'мела и воды': ('взвесь', {'фильтрованием', 'отстаиванием'}, {'с помощью магнита', 'с помощью делительной воронки'}),
    'глины и воды': ('взвесь', {'фильтрованием', 'отстаиванием'}, {'с помощью магнита'}),
    'растительного масла и воды': ('эмульсия', {'с помощью делительной воронки', 'отстаиванием'},
                                   {'фильтрованием', 'с помощью магнита'}),
    'бензина и воды': ('эмульсия', {'с помощью делительной воронки', 'отстаиванием'}, {'фильтрованием', 'с помощью магнита'}),
    'керосина и воды': ('эмульсия', {'с помощью делительной воронки', 'отстаиванием'}, {'фильтрованием', 'с помощью магнита'}),
    'железных и медных опилок': ('магнитная', {'с помощью магнита'}, {'фильтрованием', 'с помощью делительной воронки',
                                                                    'выпариванием'}),
    'железных опилок и серы': ('магнитная', {'с помощью магнита'}, {'с помощью делительной воронки', 'выпариванием'}),
    'стальных и алюминиевых скрепок': ('магнитная', {'с помощью магнита'}, {'фильтрованием', 'выпариванием'}),
    'железных и деревянных стружек': ('магнитная', {'с помощью магнита'}, {'с помощью делительной воронки', 'выпариванием'}),
    'поваренной соли и воды': ('раствор', {'выпариванием', 'перегонкой'}, {'фильтрованием', 'отстаиванием',
                                                                         'с помощью делительной воронки'}),
    'сахара и воды': ('раствор', {'выпариванием', 'перегонкой'}, {'фильтрованием', 'отстаиванием'}),
    'медного купороса и воды': ('раствор', {'выпариванием', 'перегонкой'}, {'фильтрованием', 'отстаиванием'}),
    'спирта и воды': ('раствор жидкостей', {'перегонкой'}, {'фильтрованием', 'с помощью делительной воронки',
                                                            'с помощью магнита'}),
}
CAT_METHODS = {'взвесь': {'фильтрованием', 'отстаиванием'}, 'эмульсия': {'с помощью делительной воронки', 'отстаиванием'},
               'магнитная': {'с помощью магнита'}, 'раствор': {'выпариванием', 'перегонкой'},
               'раствор жидкостей': {'перегонкой'}}
METHOD_KIND = {'Фильтрование': 'неоднородных', 'Отстаивание': 'неоднородных', 'Выпаривание': 'однородных',
               'Дистилляция (перегонка)': 'однородных', 'Кристаллизация': 'однородных',
               'Разделение с помощью делительной воронки': 'неоднородных', 'Действие магнитом': 'неоднородных'}
MIXTYPE = dict(D.MIXTURES)
MIX_WORD = {'чистое': 'является чистым веществом', 'однородная': 'является однородной смесью',
            'неоднородная': 'является неоднородной смесью'}


def _st16(rng):
    """Одно суждение о смесях: (текст, параметры для solve, истинность)."""
    kind_ = rng.choice(['type', 'type', 'sep', 'sep', 'method'])
    if kind_ == 'type':
        x, t = rng.choice(D.MIXTURES)
        claim = rng.choice(list(MIX_WORD))
        return f'{x[0].upper() + x[1:]} {MIX_WORD[claim]}.', ('type', x, claim), t == claim
    if kind_ == 'sep':
        mix, (cat, good, bad) = rng.choice(list(MIX16.items()))
        m = rng.choice(sorted(good | bad))
        return f'Смесь {mix} можно разделить {m}.', ('sep', mix, m), m in good
    meth, kindw = rng.choice(list(METHOD_KIND.items()))
    claim = rng.choice(['однородных', 'неоднородных'])
    return f'{meth} является способом разделения {claim} смесей.', ('method', meth, claim), kindw == claim


def _solve16mix(p):
    out = []
    for i, (k, x, c) in enumerate(p['st']):
        if k == 'type':
            ok = MIXTYPE[x] == c
        elif k == 'sep':
            ok = c in CAT_METHODS[MIX16[x][0]]
        else:
            ok = METHOD_KIND[x] == c
        if ok:
            out.append(i)
    return ids_of(out)


@proto('ch-oge-16-mixtures', 'ОГЭ', 16, 'Чистые вещества и смеси, способы разделения смесей',
       invariant='четыре суждения о чистых веществах, однородных и неоднородных смесях и способах их разделения; '
                 'выбрать верные',
       varies='вещества и смеси (воздух, морская вода, сталь, молоко, смесь масла и воды …), способы (фильтрование, '
              'отстаивание, делительная воронка, магнит, выпаривание, перегонка)',
       answer_rule='фильтрование и отстаивание — для неоднородных смесей твёрдого с жидкостью; делительная воронка — '
                   'несмешивающиеся жидкости; магнит — смеси с железом; выпаривание и перегонка — растворы',
       mistakes=['раствор соли «разделяют фильтрованием»', 'водопроводную воду считают чистым веществом',
                 'сталь считают чистым веществом'],
       solve=_solve16mix, kind='param', kes=['1.1'],
       fidelity=_F16('как в банке: «морская вода — смесь», «смесь бензина и воды — делительная воронка», «дистилляция»',
                     'однородные смеси нельзя разделить фильтрованием'))
def g16_mix(rng):
    for _ in range(40):
        sts = []
        seen = set()
        while len(sts) < 4:
            t, prm, v = _st16(rng)
            if t in seen or prm[1] in {s[1][1] for s in sts}:
                continue
            seen.add(t)
            sts.append((t, prm, v))
        nt = sum(v for _, _, v in sts)
        if 1 <= nt <= 3:
            break
    else:
        raise Retry
    o = opts([t for t, _, _ in sts])
    a = ids_of([i for i, (_, _, v) in enumerate(sts) if v])
    q = STEM16['смеси'] + END16
    e = ' '.join(f'{i + 1}) {"верно" if v else "неверно"}.' for i, (_, _, v) in enumerate(sts)) + f' Ответ: {"".join(a)}.'
    return pcard('ch-oge-16-mixtures', q, a, e, k='many', o=o, p={'st': [list(p_) for _, p_, _ in sts]})


# ================================================================= 17. Различение веществ (качественные реакции)

INDICATORS = {'фенолфталеин': {'кислая': 'бесцветный', 'нейтральная': 'бесцветный', 'щелочная': 'малиновый'},
              'лакмус': {'кислая': 'красный', 'нейтральная': 'фиолетовый', 'щелочная': 'синий'},
              'метилоранж': {'кислая': 'красный', 'нейтральная': 'оранжевый', 'щелочная': 'жёлтый'}}


def medium(f):
    """Среда раствора без учёта гидролиза (гидролиз в ОГЭ не проверяется): кислоты, щёлочи, соли сильных кислот
    и щелочей; остальное — None (в заданиях с индикатором не используем)."""
    if f in STRONG:
        return 'кислая'
    if f in ALK or f == 'NH3':
        return 'щелочная'
    if f in SALT:
        c, a, v = SALT[f]
        if v == 'р' and c in ('Na', 'K', 'Li', 'Ba', 'Ca') and a in ('Cl', 'Br', 'I', 'NO3', 'SO4'):
            return 'нейтральная'
    return None


def obs17(s, r):
    if r in INDICATORS:
        m = medium(s)
        return None if m is None else frozenset({'окраска:' + INDICATORS[r][m]})
    return observe(s, r)


def _medium_db(f):
    """solve: среда по классу вещества из базы (сильная кислота / щёлочь / соль щелочного (щ.-з.) металла и сильной кислоты)."""
    row = SUB.get(f, {})
    if row.get('cls') == 'кислота' and row.get('strength') == 'сильный':
        return 'кислая'
    if row.get('sub') == 'щёлочь':
        return 'щелочная'
    if row.get('cls') == 'соль' and row.get('ion'):
        c, a = row['ion']
        if c in ('Na', 'K', 'Li', 'Ba', 'Ca') and a in ('Cl', 'Br', 'I', 'NO3', 'SO4'):
            return 'нейтральная'
    return None


def obs17_db(s, r):
    if r in INDICATORS:
        m = _medium_db(s)
        return None if m is None else frozenset({'окраска:' + INDICATORS[r][m]})
    return obs_db(s, r)


R17_SOL = [f for f in SOL_EL if f not in ('HI', 'HBr')]
AMPH_PREC = {'Zn(OH)2', 'Al(OH)3'}


def vis(t, r):
    """Что видит ученик: осадок — только цвет (оттенки белого не различаем, AgBr/AgI — «жёлтый»), газ — цвет и запах;
    амфотерный гидроксид с щёлочью — осадок, растворимый в избытке. None — если описать нельзя."""
    if t is None:
        return None
    out = set()
    for x in t:
        k, _, v = x.partition(':')
        if k == 'осадок':
            col = D.PRECIP_COLOR.get(v)
            if not col:
                return None
            col = 'белый' if col.startswith('белый') else ('жёлтый' if 'жёлт' in col else col)
            if v in AMPH_PREC and r in ('NaOH', 'KOH'):
                col += ', растворим в избытке щёлочи'
            out.add('осадок:' + col)
        elif k == 'газ':
            out.add('газ:' + ' '.join(D.GASES[v]))
        else:
            out.add(x)
    return frozenset(out)
SOLID17 = [('Al', 'Mg'), ('Zn', 'Cu'), ('Mg', 'Cu'), ('Fe', 'Cu'), ('Al', 'Cu'), ('Zn', 'Ag'), ('Al(OH)3', 'Mg(OH)2'),
           ('Zn(OH)2', 'Mg(OH)2'), ('Zn(OH)2', 'Cu(OH)2'), ('Al(OH)3', 'Cu(OH)2'), ('CaCO3', 'BaSO4'), ('MgCO3', 'BaSO4'),
           ('BaCO3', 'BaSO4'), ('MgO', 'ZnO'), ('MgO', 'Al2O3'), ('CuO', 'MgO'), ('CuO', 'ZnO'), ('CaCO3', 'AgCl'),
           ('FeS', 'CuO'), ('Fe2O3', 'MgO'), ('Fe(OH)3', 'Mg(OH)2'), ('FeS', 'MgO'), ('Al', 'Zn'), ('MgCO3', 'MgO')]


def _dist(s1, s2, r, fn):
    """Различает ли реактив r вещества s1 и s2: видимые наблюдения должны быть РАЗНЫМИ."""
    o1, o2 = vis(fn(s1, r), r), vis(fn(s2, r), r)
    if o1 is None or o2 is None:
        return None
    p1 = {x.split(',')[0] for x in o1 if x.startswith('осадок:')}
    p2 = {x.split(',')[0] for x in o2 if x.startswith('осадок:')}
    if p1 & p2:            # осадок одного цвета в обоих случаях (даже с примесью другого) — не различить
        return False
    return o1 != o2


from functools import lru_cache


@lru_cache(maxsize=None)
def obs17c(s, r):
    return obs17(s, r)


def _pairs17(mode):
    if mode == 'solid':
        return [tuple(p) for p in SOLID17]
    pool = [f for f in SOL_EL if f in SALT or f in ALK or f in STRONG]
    out = []
    for i, a in enumerate(pool):
        for b in pool[i + 1:]:
            ia, ib = _ions(a), _ions(b)
            if mode == 'sol' and (ia[0] == ib[0]) != (ia[1] == ib[1]):
                out.append((a, b))
            if mode == 'ind' and medium(a) and medium(b) and (medium(a) != medium(b) or (ia[0] == ib[0]) != (ia[1] == ib[1])):
                out.append((a, b))
    return out


PAIRS17 = {m: _pairs17(m) for m in ('sol', 'ind', 'solid')}
R17_TYP = ['HCl', 'H2SO4', 'HNO3', 'NaOH', 'KOH', 'Ba(OH)2', 'BaCl2', 'Ba(NO3)2', 'AgNO3', 'Na2CO3', 'K2CO3', 'Na2SO4',
           'K2SO4', 'K3PO4', 'Na3PO4', 'CuSO4', 'CuCl2', 'Na2S', 'NaCl', 'KCl', 'KNO3', 'NaNO3', 'MgCl2', 'ZnSO4', 'FeCl3',
           'LiCl', 'KBr', 'NaBr', 'Ca(NO3)2', 'CaCl2']
REAG17 = {'sol': R17_TYP, 'ind': R17_TYP, 'solid': ['HCl', 'HNO3', 'H2SO4', 'NaOH', 'KOH', 'Ba(OH)2', 'CuSO4', 'AgNO3',
                                                    'NaCl', 'KNO3', 'Na2SO4', 'BaCl2', 'FeSO4', 'CuCl2']}


def _gen17(rng, pid, mode):
    for _ in range(60):
        if mode == 'ind':
            reag = rng.sample(list(INDICATORS), rng.choice([1, 2])) 
            reag += rng.sample([r for r in REAG17['ind'] if r not in reag], 4 - len(reag))
        else:
            reag = rng.sample(REAG17[mode], 4)
        comp = []
        for a, b in PAIRS17[mode]:
            if a in reag or b in reag:
                continue
            ds = [_dist(a, b, r, obs17c) for r in reag]
            if any(d is None for d in ds) or sum(ds) != 1:
                continue
            comp.append(((a, b), ds.index(True)))
        rng.shuffle(comp)
        pairs, ans_idx, used = [], [], set()
        for (a, b), k in comp:
            if {a, b} & used:
                continue
            if ans_idx.count(k) >= 2:
                continue
            pairs.append([a, b] if rng.random() < 0.5 else [b, a])
            ans_idx.append(k)
            used |= {a, b}
            if len(pairs) == 3:
                break
        if len(pairs) == 3 and len(set(ans_idx)) >= 2 and (mode != 'ind' or any(reag[k] in INDICATORS for k in ans_idx)):
            break
    else:
        raise Retry
    opts4 = reag
    ans = {LET[i]: str(k + 1) for i, k in enumerate(ans_idx)}
    sol_tag = mode != 'solid'
    left = [f'{disp(a)} и {disp(b)}' for a, b in pairs]
    right = [r if r in INDICATORS else disp(r) + (' (р-р)' if sol_tag and r not in ('Cu', 'Zn') and rng.random() < 0.3 else '')
             for r in opts4]
    o = match_opts(left, right)
    if mode == 'solid':
        q = ('Установите соответствие между двумя твёрдыми веществами и реактивом, с помощью которого можно различить эти '
             'вещества: к каждой позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой.')
    elif rng.random() < 0.5:
        q = ('Установите соответствие между двумя веществами, взятыми в виде водных растворов, и реактивом, с помощью '
             'которого можно различить эти вещества: к каждой позиции, обозначенной буквой, подберите соответствующую '
             'позицию, обозначенную цифрой.')
    else:
        q = ('Установите соответствие между двумя веществами и реактивом, с помощью которого можно различить эти '
             'вещества: к каждой позиции, обозначенной буквой, подберите соответствующую позицию, обозначенную цифрой.')
    q += END_M
    parts = []
    for i, (a, b) in enumerate(pairs):
        r = opts4[ans_idx[i]]
        oa, ob = obs17c(a, r), obs17c(b, r)
        rt = {'фенолфталеин': 'фенолфталеина', 'лакмус': 'лакмуса', 'метилоранж': 'метилоранжа'}.get(r) or disp(r)
        parts.append(f'{LET[i]}) при добавлении {rt}: {disp(a)} — {_obs_words(oa, r)}, {disp(b)} — {_obs_words(ob, r)}.')
    e = ' '.join(parts) + ' Ответ: ' + ''.join(ans[x] for x in LET[:3]) + '.'
    return pcard(pid, q, ans, e, k='match', o=o, p={'pairs': pairs, 'reagents': opts4})


def _obs_words(t, r=None):
    t = set(t)
    if t == {'нет'}:
        return 'нет видимых изменений'
    w = []
    for x in sorted(t):
        k, _, v = x.partition(':')
        if k == 'окраска':
            w.append({'бесцветный': 'окраска не появляется', 'малиновый': 'малиновая окраска', 'красный': 'красная окраска',
                      'фиолетовый': 'фиолетовая окраска', 'синий': 'синяя окраска', 'оранжевый': 'оранжевая окраска',
                      'жёлтый': 'жёлтая окраска'}[v])
        elif k == 'осадок':
            col = D.PRECIP_COLOR.get(v)
            w.append(f'осадок {pretty(v)}' + (f' ({col})' if col else '') +
                     (', растворяется в избытке щёлочи' if v in AMPH_PREC and r in ('NaOH', 'KOH') else ''))
        elif k == 'газ':
            w.append(f'газ {pretty(v)}')
        elif k == 'растворение':
            w.append('растворение')
        elif k == 'раствор':
            w.append(f'{v} раствор')
        elif k == 'налёт':
            w.append(f'налёт {v}')
    return ', '.join(w)


def _solve17(p):
    a = {}
    for i, (x, y) in enumerate(p['pairs']):
        ds = [r not in (x, y) and _dist(x, y, r, obs17_db) for r in p['reagents']]
        if sum(bool(d) for d in ds) != 1:
            return f'пара {x}/{y}: различают {ds}'
        a[LET[i]] = str([bool(d) for d in ds].index(True) + 1)
    return a


_F17 = lambda scale, trap: F(MATCH3 + ' (3 пары, 4 реактива)', 'как в демоверсии 2027 №17: «два вещества — реактив, с помощью '
                            'которого можно различить эти вещества»', 'П', 7, scale, trap, ['4.2', '4.7', '4.8', '4.9', '4.10'],
                            SC2)


@proto('ch-oge-17-solutions', 'ОГЭ', 17, 'Различение растворов солей, кислот, щелочей реактивом (качественные реакции на ионы)',
       invariant='три пары растворов с общим ионом; четыре реактива; для каждой пары — реактив, дающий с веществами '
                 'разный видимый результат',
       varies='пары (хлорид/сульфат, карбонат/сульфат, соль Mg/Zn/Al/Cu/Fe/NH4, кислота/соль) и реактивы',
       answer_rule='качественные реакции: SO4 2− — Ba2+ (белый осадок), Cl−/Br−/I− — Ag+, CO3 2−, SO3 2−, S2− — кислота '
                   '(газ), Cu2+, Fe2+, Fe3+, Mg2+ — щёлочь (осадки разного цвета), Al3+, Zn2+ — осадок, растворимый в '
                   'избытке щёлочи, NH4+ — щёлочь (аммиак)',
       mistakes=['берут реактив, дающий одинаковый признак с обоими веществами', 'AgNO3 для различения хлоридов'],
       solve=_solve17, kind='dict', kes=['4.9', '4.10'],
       fidelity=_F17('как в банке: «BaCl2 и LiCl», «ZnSO4 и NH4Cl», «Na2SO4 и Na2CO3», «KCl и MgCl2»',
                     'одинаковый признак с обоими веществами'))
def g17_sol(rng):
    return _gen17(rng, 'ch-oge-17-solutions', 'sol')


@proto('ch-oge-17-indicators', 'ОГЭ', 17, 'Различение кислоты, щёлочи и нейтральной соли с помощью индикатора или реактива',
       invariant='три пары растворов (кислота, щёлочь, соль сильных кислоты и основания); среди реактивов — индикаторы',
       varies='пары веществ, индикатор (фенолфталеин, лакмус, метилоранж), другие реактивы',
       answer_rule='фенолфталеин — малиновый только в щелочной среде; лакмус — красный в кислой, синий в щелочной; '
                   'метилоранж — красный в кислой, жёлтый в щелочной',
       mistakes=['фенолфталеином различают кислоту и нейтральную соль', 'путают окраску лакмуса'],
       solve=_solve17, kind='dict', kes=['4.10', '5.4'],
       fidelity=_F17('как в банке: «H2SO4 и KOH — метилоранж», «NaCl и HCl — лакмус», «Ca(OH)2 и NaOH», «HNO3 и HCl»',
                     'фенолфталеин не различает кислую и нейтральную среду'))
def g17_ind(rng):
    return _gen17(rng, 'ch-oge-17-indicators', 'ind')


@proto('ch-oge-17-solids', 'ОГЭ', 17, 'Различение твёрдых веществ (металлы, оксиды, гидроксиды, соли) реактивом',
       invariant='три пары твёрдых веществ; четыре реактива (кислоты, щёлочи, соли); для каждой пары — реактив',
       varies='пары (Al/Mg, Zn/Cu, Al(OH)3/Mg(OH)2, CaCO3/BaSO4, MgO/ZnO …), реактивы',
       answer_rule='амфотерные Al, Zn и их оксиды/гидроксиды растворяются в щёлочи; металлы до H растворяются в кислоте '
                   'с газом; карбонаты — в кислоте с газом, BaSO4 и AgCl — не растворяются',
       mistakes=['Mg «растворяется в щёлочи»', 'BaSO4 «растворяется в кислоте»'],
       solve=_solve17, kind='dict', kes=['4.3', '4.7', '4.9'],
       fidelity=_F17('как в демоверсии 2027: «Al(OH)3 и Mg(OH)2», «CaCO3 и BaSO4»; банк: «Mg и Al», «MgO и ZnO»',
                     'амфотерность, нерастворимость BaSO4'))
def g17_solid(rng):
    return _gen17(rng, 'ch-oge-17-solids', 'solid')


# ================================================================= 20. ОВР: электронный баланс (шаги развёрнутого ответа)
# Схема | вещество-восстановитель:элемент:было>стало | вещество-окислитель:элемент:было>стало
# (разметка ручная — генератор; solve пересчитывает роли и коэффициенты по степеням окисления независимо).
_S20 = r"""
Cu + HNO3 = Cu(NO3)2 + NO2 + H2O | Cu:Cu:0>2 | HNO3:N:5>4
Cu + HNO3 = Cu(NO3)2 + NO + H2O | Cu:Cu:0>2 | HNO3:N:5>2
Ag + HNO3 = AgNO3 + NO2 + H2O | Ag:Ag:0>1 | HNO3:N:5>4
Ag + HNO3 = AgNO3 + NO + H2O | Ag:Ag:0>1 | HNO3:N:5>2
Mg + HNO3 = Mg(NO3)2 + N2O + H2O | Mg:Mg:0>2 | HNO3:N:5>1
Zn + HNO3 = Zn(NO3)2 + N2O + H2O | Zn:Zn:0>2 | HNO3:N:5>1
Ca + HNO3 = Ca(NO3)2 + N2O + H2O | Ca:Ca:0>2 | HNO3:N:5>1
Al + HNO3 = Al(NO3)3 + N2O + H2O | Al:Al:0>3 | HNO3:N:5>1
Zn + HNO3 = Zn(NO3)2 + N2 + H2O | Zn:Zn:0>2 | HNO3:N:5>0
Mg + HNO3 = Mg(NO3)2 + NH4NO3 + H2O | Mg:Mg:0>2 | HNO3:N:5>-3
Fe + HNO3 = Fe(NO3)3 + NO + H2O | Fe:Fe:0>3 | HNO3:N:5>2
Zn + H2SO4 = ZnSO4 + H2S + H2O | Zn:Zn:0>2 | H2SO4:S:6>-2
Zn + H2SO4 = ZnSO4 + S + H2O | Zn:Zn:0>2 | H2SO4:S:6>0
Mg + H2SO4 = MgSO4 + S + H2O | Mg:Mg:0>2 | H2SO4:S:6>0
Mg + H2SO4 = MgSO4 + H2S + H2O | Mg:Mg:0>2 | H2SO4:S:6>-2
Al + H2SO4 = Al2(SO4)3 + S + H2O | Al:Al:0>3 | H2SO4:S:6>0
Al + H2SO4 = Al2(SO4)3 + H2S + H2O | Al:Al:0>3 | H2SO4:S:6>-2
Cu + H2SO4 = CuSO4 + SO2 + H2O | Cu:Cu:0>2 | H2SO4:S:6>4
Ag + H2SO4 = Ag2SO4 + SO2 + H2O | Ag:Ag:0>1 | H2SO4:S:6>4
Fe + H2SO4 = Fe2(SO4)3 + SO2 + H2O | Fe:Fe:0>3 | H2SO4:S:6>4
C + HNO3 = CO2 + NO2 + H2O | C:C:0>4 | HNO3:N:5>4
S + HNO3 = H2SO4 + NO2 + H2O | S:S:0>6 | HNO3:N:5>4
P + HNO3 = H3PO4 + NO2 + H2O | P:P:0>5 | HNO3:N:5>4
P + HNO3 + H2O = H3PO4 + NO | P:P:0>5 | HNO3:N:5>2
S + HNO3 = H2SO4 + NO | S:S:0>6 | HNO3:N:5>2
C + H2SO4 = CO2 + SO2 + H2O | C:C:0>4 | H2SO4:S:6>4
P + H2SO4 = H3PO4 + SO2 + H2O | P:P:0>5 | H2SO4:S:6>4
S + H2SO4 = SO2 + H2O | S:S:0>4 | H2SO4:S:6>4
I2 + HNO3 = HIO3 + NO + H2O | I2:I:0>5 | HNO3:N:5>2
NH3 + O2 = NO + H2O | NH3:N:-3>2 | O2:O:0>-2
NH3 + O2 = N2 + H2O | NH3:N:-3>0 | O2:O:0>-2
NH3 + CuO = Cu + N2 + H2O | NH3:N:-3>0 | CuO:Cu:2>0
NH3 + Cl2 = N2 + HCl | NH3:N:-3>0 | Cl2:Cl:0>-1
H2S + O2 = SO2 + H2O | H2S:S:-2>4 | O2:O:0>-2
H2S + O2 = S + H2O | H2S:S:-2>0 | O2:O:0>-2
H2S + HNO3 = S + NO2 + H2O | H2S:S:-2>0 | HNO3:N:5>4
H2S + HNO3 = H2SO4 + NO2 + H2O | H2S:S:-2>6 | HNO3:N:5>4
H2S + HNO3 = S + NO + H2O | H2S:S:-2>0 | HNO3:N:5>2
H2S + SO2 = S + H2O | H2S:S:-2>0 | SO2:S:4>0
H2S + Cl2 + H2O = H2SO4 + HCl | H2S:S:-2>6 | Cl2:Cl:0>-1
H2S + Br2 = S + HBr | H2S:S:-2>0 | Br2:Br:0>-1
H2S + Br2 + H2O = H2SO4 + HBr | H2S:S:-2>6 | Br2:Br:0>-1
HI + H2SO4 = I2 + H2S + H2O | HI:I:-1>0 | H2SO4:S:6>-2
HI + H2SO4 = I2 + SO2 + H2O | HI:I:-1>0 | H2SO4:S:6>4
HBr + H2SO4 = Br2 + SO2 + H2O | HBr:Br:-1>0 | H2SO4:S:6>4
HCl + MnO2 = MnCl2 + Cl2 + H2O | HCl:Cl:-1>0 | MnO2:Mn:4>2
HBr + MnO2 = MnBr2 + Br2 + H2O | HBr:Br:-1>0 | MnO2:Mn:4>2
KMnO4 + HCl = KCl + MnCl2 + Cl2 + H2O | HCl:Cl:-1>0 | KMnO4:Mn:7>2
K2Cr2O7 + HCl = KCl + CrCl3 + Cl2 + H2O | HCl:Cl:-1>0 | K2Cr2O7:Cr:6>3
KClO3 + HCl = KCl + Cl2 + H2O | HCl:Cl:-1>0 | KClO3:Cl:5>0
PH3 + O2 = P2O5 + H2O | PH3:P:-3>5 | O2:O:0>-2
NO2 + O2 + H2O = HNO3 | NO2:N:4>5 | O2:O:0>-2
NO + O2 + H2O = HNO3 | NO:N:2>5 | O2:O:0>-2
SO2 + Br2 + H2O = H2SO4 + HBr | SO2:S:4>6 | Br2:Br:0>-1
SO2 + Cl2 + H2O = H2SO4 + HCl | SO2:S:4>6 | Cl2:Cl:0>-1
SO2 + HNO3 + H2O = H2SO4 + NO | SO2:S:4>6 | HNO3:N:5>2
SO2 + HNO3 = H2SO4 + NO2 | SO2:S:4>6 | HNO3:N:5>4
Fe2O3 + CO = Fe + CO2 | CO:C:2>4 | Fe2O3:Fe:3>0
Fe2O3 + H2 = Fe + H2O | H2:H:0>1 | Fe2O3:Fe:3>0
Fe2O3 + C = Fe + CO | C:C:0>2 | Fe2O3:Fe:3>0
CuO + C = Cu + CO2 | C:C:0>4 | CuO:Cu:2>0
Fe2O3 + Al = Al2O3 + Fe | Al:Al:0>3 | Fe2O3:Fe:3>0
FeO + HNO3 = Fe(NO3)3 + NO2 + H2O | FeO:Fe:2>3 | HNO3:N:5>4
FeO + HNO3 = Fe(NO3)3 + NO + H2O | FeO:Fe:2>3 | HNO3:N:5>2
Fe(OH)2 + O2 + H2O = Fe(OH)3 | Fe(OH)2:Fe:2>3 | O2:O:0>-2
Fe(OH)2 + HNO3 = Fe(NO3)3 + NO + H2O | Fe(OH)2:Fe:2>3 | HNO3:N:5>2
FeCl3 + KI = FeCl2 + KCl + I2 | KI:I:-1>0 | FeCl3:Fe:3>2
FeCl3 + H2S = FeCl2 + S + HCl | H2S:S:-2>0 | FeCl3:Fe:3>2
FeCl3 + HI = FeCl2 + HCl + I2 | HI:I:-1>0 | FeCl3:Fe:3>2
KClO3 + P = KCl + P2O5 | P:P:0>5 | KClO3:Cl:5>-1
KClO3 + S = KCl + SO2 | S:S:0>4 | KClO3:Cl:5>-1
KClO3 + C = KCl + CO2 | C:C:0>4 | KClO3:Cl:5>-1
Na2SO3 + HNO3 = Na2SO4 + NO2 + H2O | Na2SO3:S:4>6 | HNO3:N:5>4
K2SO3 + HNO3 = K2SO4 + NO + H2O | K2SO3:S:4>6 | HNO3:N:5>2
K2SO3 + KMnO4 + H2O = K2SO4 + MnO2 + KOH | K2SO3:S:4>6 | KMnO4:Mn:7>4
CuS + HNO3 = CuSO4 + NO2 + H2O | CuS:S:-2>6 | HNO3:N:5>4
K2S + HNO3 = K2SO4 + NO + H2O | K2S:S:-2>6 | HNO3:N:5>2
ZnS + O2 = ZnO + SO2 | ZnS:S:-2>4 | O2:O:0>-2
Mg + CO2 = MgO + C | Mg:Mg:0>2 | CO2:C:4>0
Cr(OH)3 + Cl2 + KOH = K2CrO4 + KCl + H2O | Cr(OH)3:Cr:3>6 | Cl2:Cl:0>-1
H2O2 + KI + H2SO4 = I2 + K2SO4 + H2O | KI:I:-1>0 | H2O2:O:-1>-2
HNO2 + HI = I2 + NO + H2O | HI:I:-1>0 | HNO2:N:3>2
KI + Cu(NO3)2 = CuI + I2 + KNO3 | KI:I:-1>0 | Cu(NO3)2:Cu:2>1
MnO2 + KClO3 + KOH = K2MnO4 + KCl + H2O | MnO2:Mn:4>6 | KClO3:Cl:5>-1
Br2 + KI = KBr + I2 | KI:I:-1>0 | Br2:Br:0>-1
Cl2 + KBr = KCl + Br2 | KBr:Br:-1>0 | Cl2:Cl:0>-1
Zn + HNO3 = Zn(NO3)2 + NO2 + H2O | Zn:Zn:0>2 | HNO3:N:5>4
Mg + HNO3 = Mg(NO3)2 + NO2 + H2O | Mg:Mg:0>2 | HNO3:N:5>4
Fe + HNO3 = Fe(NO3)3 + NO2 + H2O | Fe:Fe:0>3 | HNO3:N:5>4
Na + H2O = NaOH + H2 | Na:Na:0>1 | H2O:H:1>0
Ca + H2O = Ca(OH)2 + H2 | Ca:Ca:0>2 | H2O:H:1>0
KI + H2SO4 = I2 + H2S + K2SO4 + H2O | KI:I:-1>0 | H2SO4:S:6>-2
KBr + H2SO4 = Br2 + SO2 + K2SO4 + H2O | KBr:Br:-1>0 | H2SO4:S:6>4
NaI + H2SO4 = I2 + H2S + Na2SO4 + H2O | NaI:I:-1>0 | H2SO4:S:6>-2
CuS + O2 = CuO + SO2 | CuS:S:-2>4 | O2:O:0>-2
SO2 + KMnO4 + H2O = MnSO4 + K2SO4 + H2SO4 | SO2:S:4>6 | KMnO4:Mn:7>2
Na2SO3 + KMnO4 + H2SO4 = Na2SO4 + MnSO4 + K2SO4 + H2O | Na2SO3:S:4>6 | KMnO4:Mn:7>2
K2SO3 + K2Cr2O7 + H2SO4 = K2SO4 + Cr2(SO4)3 + H2O | K2SO3:S:4>6 | K2Cr2O7:Cr:6>3
H2S + KMnO4 + H2SO4 = S + MnSO4 + K2SO4 + H2O | H2S:S:-2>0 | KMnO4:Mn:7>2
H2S + K2Cr2O7 + H2SO4 = S + Cr2(SO4)3 + K2SO4 + H2O | H2S:S:-2>0 | K2Cr2O7:Cr:6>3
"""


def _parse20(text):
    out = []
    for line in text.strip().splitlines():
        eq, red, ox = [x.strip() for x in line.split('|')]
        lhs, rhs = [x.strip().split(' + ') for x in eq.split('=')]
        rs, re_, rab = red.split(':')
        os_, oe, oab = ox.split(':')
        ra, rb = map(int, rab.split('>'))
        oa, ob = map(int, oab.split('>'))
        out.append(dict(lhs=lhs, rhs=rhs, red=(rs, re_, ra, rb), ox=(os_, oe, oa, ob)))
    return out


EXTRA20 = {'CuI': 'иодид меди(I)', 'MnBr2': 'бромид марганца(II)', 'HIO3': 'иодноватая кислота', 'K2SiO3': 'силикат калия'}
S20 = []
for _s in _parse20(_S20):
    try:
        _kl, _kr = balance(_s['lhs'], _s['rhs'])
    except ValueError:
        continue
    _s['k'] = (_kl, _kr)
    S20.append(_s)


def pick_target(el, b, rhs):
    """Продукт, в котором элемент имеет степень окисления b (простое вещество и больший индекс — в приоритете)."""
    c = [f for f in rhs if el in parse_formula(f) and b in ox_states(f).get(el, [])]
    return max(c, key=lambda f: (_is_simple(f), parse_formula(f)[el])) if c else None


def half_text(el, a, b, src, tgt):
    """Уравнение процесса по школьной записи: «Cu⁰ − 2ē → Cu⁺²», «Cl₂⁰ + 2ē → 2Cl⁻¹», «2N⁺⁵ + 8ē → 2N⁺¹»
    (для N2O), «2Cr⁺⁶ + 6ē → 2Cr⁺³» (для K2Cr2O7): число атомов — по индексу элемента в исходном веществе или продукте."""
    nf, nt = min(parse_formula(src)[el], 2), min(parse_formula(tgt)[el], 2)
    n = max(nf, nt)
    e = n * abs(b - a)
    left = f'{el}₂{ox_sup(a)}' if _is_simple(src) and nf == 2 else (f'{n}{el}{ox_sup(a)}' if n > 1 else f'{el}{ox_sup(a)}')
    right = f'{el}₂{ox_sup(b)}' if _is_simple(tgt) and nt == 2 else (f'{n}{el}{ox_sup(b)}' if n > 1 else f'{el}{ox_sup(b)}')
    return f'{left} {"−" if b > a else "+"} {e}ē → {right}'


def _is_simple(f):
    return len(parse_formula(f)) == 1


def _half_from(sch, which):
    sp, el, a, b = sch[which]
    return half_text(el, a, b, sp, pick_target(el, b, sch['rhs']))


def e_of(half):
    return int(re.search(r'(\d+)ē', half).group(1))


def multipliers(e_red, e_ox):
    from math import gcd
    L = e_red * e_ox // gcd(e_red, e_ox)
    return L // e_red, L // e_ox


def scheme_str(sch):
    return ' + '.join(disp(x) for x in sch['lhs']) + ' → ' + ' + '.join(disp(x) for x in sch['rhs'])


INTRO20 = 'Дана схема окислительно-восстановительной реакции\n{s}\n'
TASK20 = ('1) Составьте электронный баланс, записав уравнения процессов окисления и восстановления.\n'
          '2) По электронному балансу расставьте коэффициенты и запишите молекулярное уравнение реакции.\n'
          '3) Укажите вещество (частицу) — окислитель и вещество (частицу) — восстановитель.')


def _solution20(sch):
    kl, kr = sch['k']
    eq = eq_text((sch['lhs'], sch['rhs'], kl, kr))
    hr, ho = _half_from(sch, "red"), _half_from(sch, "ox")
    m1, m2 = multipliers(e_of(hr), e_of(ho))
    return (f'Электронный баланс: {hr} (окисление, множитель {m1}); {ho} (восстановление, множитель {m2}). '
            f'Уравнение: {eq}. Восстановитель — {disp(sch["red"][0])} ({sch["red"][1]} в степени окисления '
            f'{sch["red"][2]:+d}), окислитель — {disp(sch["ox"][0])} ({sch["ox"][1]} в степени окисления '
            f'{sch["ox"][2]:+d}).').replace('+0)', '0)')


def roles_calc(lhs, rhs):
    """solve: окислитель и восстановитель по степеням окисления. Возвращает (окислители, восстановители)."""
    R_states = {}
    for f in rhs:
        for e, sts in ox_states(f).items():
            R_states.setdefault(e, set()).update(sts)
    oxs, reds = [], []
    for f in lhs:
        up = down = False
        for e, sts in ox_states(f).items():
            if e in ('H', 'O') and not (_is_simple(f) or f in ('H2O2',) or 'H2' in rhs or 'O2' in rhs and e == 'O'):
                if not (e == 'H' and 'H2' in rhs):
                    continue
            for x in sts:
                if any(y > x for y in R_states.get(e, ())) and not (e == 'O' and 'O2' not in rhs):
                    up = True
                if any(y < x for y in R_states.get(e, ())):
                    down = True
        if up and not down:
            reds.append(f)
        if down and not up:
            oxs.append(f)
    return oxs, reds


S20_ROLES = [s for s in S20 if s['ox'][0] != s['red'][0]]


def _steps20_e(p):
    h = _halves_calc(p['lhs'], p['rhs'])
    return [e_of(h['red']), e_of(h['ox'])]


def _steps20_mult(p):
    h = _halves_calc(p['lhs'], p['rhs'])
    return list(multipliers(e_of(h['red']), e_of(h['ox'])))


def _solve20_roles(p):
    oxs, reds = roles_calc(p['lhs'], p['rhs'])
    if len(oxs) != 1 or len(reds) != 1:
        return f'роли не однозначны: {oxs} {reds}'
    return {'А': str(p['items'].index(oxs[0]) + 1), 'Б': str(p['items'].index(reds[0]) + 1)}


_F20 = lambda step, cov='': F('развёрнутый ответ (3 балла: баланс, уравнение, окислитель/восстановитель); в тренажёре — шаг: ' + step,
                     'условие — по структуре демоверсии 2027 №20 (три пункта: баланс, уравнение, окислитель и '
                     'восстановитель), своими словами', 'В', 20,
                     'схемы школьного уровня как в банке: металлы и неметаллы с HNO3 и H2SO4(конц.), H2S, NH3, HCl + '
                     'MnO2/KMnO4/KClO3, FeCl3 + KI, KClO3 + P/S', 'кислота как окислитель и как среда; «лишняя» H2O',
                     ['5.3'], '3 балла по критериям (баланс, уравнение, окислитель/восстановитель); покрыто: ' + cov)


@proto('ch-oge-20-roles', 'ОГЭ', 20, 'ОВР (электронный баланс): окислитель и восстановитель в схеме реакции',
       invariant='схема ОВР из задания 20; установить, какое вещество окислитель, какое восстановитель',
       varies='схема (металлы/неметаллы с кислотами-окислителями, сероводород, аммиак, галогеноводороды, соли железа(III) …)',
       answer_rule='восстановитель содержит элемент, повышающий степень окисления; окислитель — понижающий',
       mistakes=['азотную кислоту в роли среды не считают окислителем', 'путают окислитель с продуктом восстановления',
                 'воду считают окислителем'],
       solve=_solve20_roles, kind='param', kes=['5.3'], solve_steps=_steps20_e,
       fidelity=_F20('окислитель и восстановитель (соответствие) + числа электронов в процессах',
                     'элемент 3 критериев (окислитель/восстановитель) полностью; элемент 1 (баланс) — числа электронов'))
def g20_roles(rng):
    sch = rng.choice(S20_ROLES)
    items = shuffled(rng, list(dict.fromkeys(sch['lhs'] + sch['rhs'])))
    o = match_opts(['окислитель', 'восстановитель'], [disp(f) for f in items])
    a = {'А': str(items.index(sch['ox'][0]) + 1), 'Б': str(items.index(sch['red'][0]) + 1)}
    q = (INTRO20.format(s=scheme_str(sch)) + TASK20 + '\n\nПроверьте себя: установите соответствие между ролью вещества '
         'в этой реакции и его формулой.')
    kl, kr = sch['k']
    er, eo = e_of(_half_from(sch, 'red')), e_of(_half_from(sch, 'ox'))
    return pcard('ch-oge-20-roles', q, a, _solution20(sch), k='match', o=o, eq=(sch['lhs'], sch['rhs'], kl, kr),
                 p={'lhs': sch['lhs'], 'rhs': sch['rhs'], 'items': items},
                 steps=[('число электронов в уравнении процесса окисления', er),
                        ('число электронов в уравнении процесса восстановления', eo)])


def _halves_calc(lhs, rhs):
    """solve: процессы окисления и восстановления по степеням окисления."""
    oxs, reds = roles_calc(lhs, rhs)
    res = {}
    for key, sp in (('red', reds[0]), ('ox', oxs[0])):
        best = None
        for e, sts in ox_states(sp).items():
            a = sts[0]
            for f in rhs:
                if e in parse_formula(f):
                    for b in ox_states(f)[e]:
                        if (key == 'red' and b > a) or (key == 'ox' and b < a):
                            if e in ('H', 'O') and not _is_simple(f) and not _is_simple(sp) and sp != 'H2O2':
                                continue
                            best = (e, a, b)
        res[key] = half_text(best[0], best[1], best[2], sp, pick_target(best[0], best[2], rhs)) if best else None
    return res


def _solve20_halves(p):
    h = _halves_calc(p['lhs'], p['rhs'])
    try:
        return {'А': str(p['items'].index(h['red']) + 1), 'Б': str(p['items'].index(h['ox']) + 1)}
    except ValueError:
        return f'нет процесса среди вариантов: {h}'


S20_HALF = [s for s in S20_ROLES if s['red'][1] != s['ox'][1] or s['red'][2] != s['ox'][3]]


def _wrong_halves(h, n_atoms):
    """Отвлекающие записи процесса: неверное число электронов (в т. ч. без учёта индекса) и неверный знак."""
    m = re.match(r'^(.*) ([+−]) (\d+)ē → (.*)$', h)
    e = int(m.group(3))
    counts = {e // 2} if n_atoms == 2 and e % 2 == 0 else {e * 2}
    counts |= {e + 1, e - 1}
    out = [f'{m.group(1)} {m.group(2)} {k}ē → {m.group(4)}' for k in sorted(counts) if k > 0 and k != e]
    out.append(f'{m.group(1)} {"+" if m.group(2) == "−" else "−"} {e}ē → {m.group(4)}')
    return out


@proto('ch-oge-20-electron-balance', 'ОГЭ', 20, 'ОВР (электронный баланс): уравнения процессов окисления и восстановления',
       invariant='схема ОВР из задания 20; выбрать верно записанные процессы окисления и восстановления',
       varies='схема; отвлекающие варианты — неверное число электронов, перепутан знак (отдача/присоединение), '
              'пропущен коэффициент 2 у двухатомной молекулы',
       answer_rule='окисление: атом отдаёт электроны, степень окисления растёт; число электронов = изменение степени '
                   'окисления × число атомов',
       mistakes=['для Cl2 пишут 1ē вместо 2ē', 'окисление записывают с «+ē»', 'путают конечную степень окисления'],
       solve=_solve20_halves, kind='param', kes=['5.3'], solve_steps=_steps20_mult,
       fidelity=_F20('уравнения процессов (соответствие) + множители баланса',
                     'элемент 1 критериев (электронный баланс: процессы и множители) полностью'))
def g20_halves(rng):
    sch = rng.choice(S20_HALF)
    hr, ho = _half_from(sch, 'red'), _half_from(sch, 'ox')
    items = [hr, ho]
    for which, h in (('red', hr), ('ox', ho)):
        sp, el, a, b = sch[which]
        n = max(min(parse_formula(sp)[el], 2), min(parse_formula(pick_target(el, b, sch['rhs']))[el], 2))
        ws = [w for w in _wrong_halves(h, n) if w not in items]
        idx = [0] + ([len(ws) - 1] if len(ws) > 1 else [])      # число ē и знак — по одному варианту на процесс
        items += [ws[i] for i in idx]
    if len(set(items)) != len(items):
        raise Retry
    items = shuffled(rng, items)
    o = match_opts(['процесс окисления', 'процесс восстановления'], items)
    a = {'А': str(items.index(hr) + 1), 'Б': str(items.index(ho) + 1)}
    q = (INTRO20.format(s=scheme_str(sch)) + TASK20 + '\n\nПроверьте себя (пункт 1): установите соответствие между '
         'процессом и его уравнением; множители электронного баланса проверяются отдельным шагом решения.')
    kl, kr = sch['k']
    m1, m2 = multipliers(e_of(hr), e_of(ho))
    return pcard('ch-oge-20-electron-balance', q, a, _solution20(sch), k='match', o=o, eq=(sch['lhs'], sch['rhs'], kl, kr),
                 p={'lhs': sch['lhs'], 'rhs': sch['rhs'], 'items': items},
                 steps=[('множитель для процесса окисления', m1), ('множитель для процесса восстановления', m2)])


def coef_by_electrons(lhs, rhs):
    """solve: коэффициенты методом электронного баланса и последующего подбора по атомам (без общего решения системы).
    1) для каждого процесса берём вещество, в котором считаем электроны: реагент, если весь элемент в нём меняет
       степень окисления, иначе — продукт с новой степенью окисления (кислота-среда, HCl → Cl2 + MnCl2);
    2) множители баланса — их коэффициенты; 3) остальные — по элементу, встречающемуся у единственного неизвестного."""
    oxs, reds = roles_calc(lhs, rhs)
    if len(oxs) != 1 or len(reds) != 1:
        raise ValueError('роли')
    rstates = {}
    for f in rhs:
        for e, sts in ox_states(f).items():
            rstates.setdefault(e, set()).update(sts)

    def carrier(sp, up):
        for e, sts in ox_states(sp).items():
            x = sts[0]
            new = [y for y in rstates.get(e, ()) if (y > x if up else y < x)]
            if not new or (e in ('H', 'O') and not _is_simple(sp) and sp != 'H2O2' and not any(
                    _is_simple(f) and e in parse_formula(f) for f in rhs)):
                continue
            y = new[0]
            if x not in rstates[e]:                        # элемент целиком меняет степень окисления
                return sp, parse_formula(sp)[e] * abs(y - x)
            prods = [f for f in rhs if e in parse_formula(f) and y in ox_states(f)[e]]
            if len(prods) != 1:
                raise ValueError('несколько продуктов')
            return prods[0], parse_formula(prods[0])[e] * abs(y - x)
        raise ValueError('нет процесса')
    a, ea = carrier(reds[0], True)
    b, eb = carrier(oxs[0], False)
    if a == b:
        raise ValueError('общий продукт')
    species = lhs + rhs
    coef = {a: Fr(eb), b: Fr(ea)}
    for _ in range(20):
        if len(coef) == len(species):
            break
        progress = False
        for el in sorted({e for f in species for e in parse_formula(f)}):
            unk = [f for f in species if el in parse_formula(f) and f not in coef]
            if len(unk) != 1:
                continue
            u = unk[0]
            left = sum(coef[f] * parse_formula(f)[el] for f in lhs if f in coef and el in parse_formula(f))
            right = sum(coef[f] * parse_formula(f)[el] for f in rhs if f in coef and el in parse_formula(f))
            val = (left - right) if u in rhs else (right - left)
            coef[u] = Fr(val) / parse_formula(u)[el]
            progress = True
        if not progress:
            raise ValueError('не подобрать')
    vals = [coef[f] for f in species]
    if any(v <= 0 for v in vals):
        raise ValueError('отрицательный коэффициент')
    from math import lcm, gcd
    m = 1
    for v in vals:
        m = lcm(m, v.denominator)
    ints = [int(v * m) for v in vals]
    g = 0
    for v in ints:
        g = gcd(g, v)
    ints = [v // g for v in ints]
    if not check_balance(lhs, rhs, ints[:len(lhs)], ints[len(lhs):]):
        raise ValueError('баланс не сошёлся')
    return ints


def _coef_ok(s):
    kl, kr = s['k']
    if max(kl + kr) > 9 or s['ox'][0] == s['red'][0]:
        return False
    if len(s['lhs']) + len(s['rhs']) < 5:        # как в банке: со средой (кислота, щёлочь, вода), не «X + Y = Z + W»
        return False
    try:
        return coef_by_electrons(s['lhs'], s['rhs']) == list(kl) + list(kr)
    except (ValueError, KeyError, ZeroDivisionError, TypeError):
        return False


S20_COEF = [s for s in S20 if _coef_ok(s)]


def _solve20_coef(p):
    return ''.join(str(x) for x in coef_by_electrons(p['lhs'], p['rhs']))


@proto('ch-oge-20-coefficients', 'ОГЭ', 20, 'ОВР (электронный баланс): коэффициенты в уравнении реакции',
       invariant='схема ОВР из задания 20; расставить коэффициенты методом электронного баланса',
       varies='схема ОВР (коэффициенты не больше 9)',
       answer_rule='множители электронного баланса — коэффициенты перед восстановителем и продуктом восстановления, '
                   'остальные — по сохранению атомов (последними — водород и кислород)',
       mistakes=['кислоту-среду учитывают только в окислителе', 'забывают коэффициент перед водой',
                 'не удваивают электроны для двухатомных молекул'],
       solve=_solve20_coef, kind='param', kes=['5.3'], solve_steps=_steps20_mult,
       fidelity=_F20('коэффициенты — цифры подряд в порядке записи веществ в схеме; множители баланса',
                     'элемент 2 критериев (уравнение реакции) полностью; элемент 1 — множители баланса'))
def g20_coef(rng):
    sch = rng.choice(S20_COEF)
    kl, kr = sch['k']
    ans = ''.join(str(x) for x in list(kl) + list(kr))
    q = (INTRO20.format(s=scheme_str(sch)) + TASK20 + '\n\nПроверьте себя: запишите в ответ полученные коэффициенты '
         'по порядку следования веществ в схеме (цифры подряд, коэффициент 1 тоже записывается).')
    wrong = []
    ks = list(kl) + list(kr)
    for i in range(len(ks)):
        w = ks[:]
        w[i] = w[i] + 1 if w[i] < 9 else w[i] - 1
        wrong.append(''.join(map(str, w)))
    m1, m2 = multipliers(e_of(_half_from(sch, 'red')), e_of(_half_from(sch, 'ox')))
    return pcard('ch-oge-20-coefficients', q, ans, _solution20(sch), k='num', eq=(sch['lhs'], sch['rhs'], kl, kr),
                 p={'lhs': sch['lhs'], 'rhs': sch['rhs']}, wrong=wrong[:3],
                 steps=[('множитель для процесса окисления', m1), ('множитель для процесса восстановления', m2)])


# ================================================================= 21. Цепочка превращений (шаги развёрнутого ответа)

REAG21 = ['H2O', 'O2', 'H2', 'Cl2', 'HCl', 'H2SO4', 'HNO3', 'H3PO4', 'NaOH', 'KOH', 'Ca(OH)2', 'Ba(OH)2', 'AgNO3', 'BaCl2',
          'Ba(NO3)2', 'Na2CO3', 'K2CO3', 'Na2SO4', 'K2SO4', 'CO2', 'SO2', 'SO3', 'C', 'CO', 'Na2S', 'H2S', 'Na3PO4',
          'K3PO4', 'NH3', 'CaCl2', 'Fe', 'Zn', 'Mg', 'Al', 'Cu', 'CuSO4', 'CuCl2', 'Na2SiO3', 'Ca(NO3)2', 'N2', 'S',
          'FeCl2', 'NaCl', 'KCl']
NODE21 = sorted(f for f, r in SUB.items() if r.get('cls') in ('оксид', 'основание', 'амфотерный гидроксид', 'кислота', 'соль',
                                                              'простое вещество', 'водородное соединение')
                and f not in EXOTIC and not r.get('org') and r.get('sub') not in ('кислая', 'основная')
                and f not in ('HNO2', 'N2O3', 'N2O', 'NO', 'P2O3', 'HF', 'H2SO3', 'H2CO3', 'HClO4', 'Cl2O7', 'NCl3', 'PH3',
                              'CrO3', 'Mn2O7', 'BeO', 'SrO', 'MnO', 'Cr2O3', 'KNO2', 'NaNO2', 'NH4NO2') and f not in ('Na2O2', 'KO2', 'Fe3O4', 'NH3·H2O', 'H2O', 'O2', 'H2', 'CH3COOH',
                                                  'H2O2', 'Hg', 'HgO', 'Ag2O', 'NaAlO2', 'KAlO2', 'Na2ZnO2', 'K2ZnO2',
                                                  'Ca(AlO2)2', 'SiO', 'Cu2O', 'O3', 'HClO', 'KClO3', 'NaClO', 'Ca(ClO)2',
                                                  'KMnO4', 'K2MnO4', 'MnO2', 'I2', 'HI')
                and all(e in {'H', 'O', 'N', 'C', 'S', 'P', 'Si', 'Cl', 'Li', 'Na', 'K', 'Mg', 'Ca', 'Ba', 'Al', 'Zn', 'Fe',
                              'Cu', 'Ag'} for e in parse_formula(f)))
T21 = 'нагревание'


def _edges21(reactions):
    """Переходы A → B: A среди реагентов, B среди продуктов, остальные реагенты — из списка REAG21."""
    edges = {}
    for r in reactions:
        if 'электролиз' in (r.get('cond') or '') or 'электролиз' in ' '.join(r.get('type', [])):
            continue
        L = r['lhs']
        for A in L:
            if A not in NODE21:
                continue
            others = [x for x in L if x != A]
            if len(L) == 1:
                rg = T21
            else:
                rest = [x for x in others if x != 'H2O']
                if len(rest) > 1 or any(x not in REAG21 for x in rest):
                    continue
                rg = rest[0] if rest else 'H2O'
            for B in r['rhs']:
                if B in NODE21 and B != A and (set(parse_formula(A)) & set(parse_formula(B))) - {'H', 'O'}:
                    edges.setdefault((A, B), set()).add(rg)
    return edges


_E21 = {}


def edges21(which='all'):
    """'my' — факты базы участка (по ним строим цепочку), 'all' — вся база (по ней отсекаем отвлекающие варианты)."""
    if which not in _E21:
        _E21[which] = _edges21(D.REACTIONS if which == 'my' else chemdb.load()['reactions'])
    return _E21[which]


_BYREAG = None


def _by_reagent():
    global _BYREAG
    if _BYREAG is None:
        _BYREAG = {}
        for x in chemdb.load()['reactions']:
            for f in set(x['lhs']):
                _BYREAG.setdefault(f, []).append(x)
    return _BYREAG


def can21(a, b, reagent=None):
    """solve: можно ли получить b из a (при необходимости — указанным реагентом): поиск реакции заново по базе."""
    for r in _by_reagent().get(a, []):
        if b in r['rhs'] and 'электролиз' not in (r.get('cond') or '') + ' '.join(r.get('type', [])):
            rest = [x for x in r['lhs'] if x not in (a, 'H2O')]
            if len(r['lhs']) == 1:
                rg = T21
            elif len(rest) == 1 and rest[0] in REAG21:
                rg = rest[0]
            elif not rest:
                rg = 'H2O'
            else:
                continue
            if reagent is None or rg == reagent:
                return True
    return False


def _key_el(a, b):
    return (set(parse_formula(a)) & set(parse_formula(b))) - {'H', 'O'}


def char_el(f):
    """«Главный» элемент вещества: металл катиона (N для NH4+), элемент оксида, центральный атом кислоты."""
    if f in SALT:
        c = SALT[f][0]
        return 'N' if c == 'NH4' else MET_OF[c]
    els = [e for e in parse_formula(f) if e not in ('H', 'O')]
    if not els:
        return None
    ms = [e for e in els if e in METALS_ALL]
    if ms:
        return ms[0]
    if f.startswith('(NH4)') or f.startswith('NH4'):
        return 'N'
    return els[0] if len(els) == 1 else [e for e in els if e not in ('Cl', 'Br', 'I', 'F')][0]


def _chain21(rng):
    E = edges21('my')
    out_ = {}
    for (a, b) in E:
        out_.setdefault(a, []).append(b)
    starts = [a for a in out_ if char_el(a) and char_el(a) not in ('Cl', 'Br', 'I')]   # цепочки по элементу, как в банке
    for _ in range(200):
        a = rng.choice(starts)
        el = char_el(a)
        chain = [a]
        for _step in range(3):
            nxt = [b for b in out_.get(chain[-1], []) if b not in chain and el in parse_formula(b)]
            if not nxt:
                break
            chain.append(rng.choice(nxt))
        if len(chain) == 4:
            return chain, el
    raise Retry


INTRO21 = 'Дана схема превращений:\n{s}\nНапишите молекулярные уравнения реакций, с помощью которых можно осуществить указанные превращения.'


def _solve21x(p):
    ch, pos = p['chain'], p['pos']
    good = [i for i, x in enumerate(p['items']) if can21(ch[pos - 1], x) and can21(x, ch[pos + 1])]
    return ids_of(good)[0] if len(good) == 1 else f'подходят {good}'


_F21 = lambda step, cov='': F('развёрнутый ответ (3 балла: по баллу за каждое уравнение); в тренажёре — шаг: ' + step,
                     'условие — как в демоверсии 2027 №21 и банке: «Дана схема превращений: … Напишите молекулярные '
                     'уравнения реакций…»', 'В', 17, 'цепочки из четырёх веществ одного элемента, как в банке: '
                     'Li2O → X → LiCl → LiNO3, Fe → X → Fe(OH)3 → Fe(NO3)3, S → X → Na2SO3 → CaSO3',
                     'вещество X, которое получается из предыдущего, но не даёт следующее', ['4.12'],
                     '3 балла по критериям (по баллу за уравнение); покрыто: ' + cov)


@proto('ch-oge-21-find-x', 'ОГЭ', 21, 'Цепочка превращений: какое вещество может быть X',
       invariant='схема из четырёх веществ одного элемента с неизвестным X; выбрать X из четырёх формул',
       varies='элемент и цепочка (металлы, их оксиды, гидроксиды, соли; неметаллы S, C, N, P, Si и их соединения), '
              'место X в цепочке',
       answer_rule='X должен получаться из предыдущего вещества одной реакцией и сам давать следующее',
       mistakes=['выбирают вещество, которое не получается из предыдущего', 'нарушают степень окисления (Fe2+ / Fe3+)'],
       solve=_solve21x, kind='dict', kes=['4.12'],
       fidelity=_F21('определить вещество X (один ответ из четырёх; X — единственное подходящее вещество базы)',
                     'предпосылка к трём уравнениям (отдельного балла нет)'))
def g21_x(rng):
    chain, el = _chain21(rng)
    pos = 1 if rng.random() < 0.7 else 2
    x = chain[pos]
    E = edges21()
    # единственность: среди ВСЕХ веществ базы X подходит только одно
    if [f for f in NODE21 if (chain[pos - 1], f) in E and (f, chain[pos + 1]) in E] != [x]:
        raise Retry
    cands = [f for f in NODE21 if el in parse_formula(f) and f not in chain and
             not ((chain[pos - 1], f) in E and (f, chain[pos + 1]) in E)]
    if len(cands) < 3:
        raise Retry
    nxt = chain[pos + 1]
    if kind(nxt) in ('oxb', 'oxam', 'oxa'):   # к «→ оксид» не даём соли/гидроксиды, которые сами разлагаются до оксида
        cands = [f for f in cands if not (char_el(f) == char_el(nxt) and (f in SALT and SALT[f][1] in ('NO3', 'CO3', 'SO4', 'SO3')
                                                                          or kind(f) in ('bins', 'bamp', 'alk')))]
        if len(cands) < 3:
            raise Retry
    near = [f for f in cands if (chain[pos - 1], f) in E or (f, chain[pos + 1]) in E]
    dist = rng.sample(near, min(2, len(near)))
    dist += rng.sample([f for f in cands if f not in dist], 3 - len(dist))
    items = shuffled(rng, [x] + dist)
    shown = [disp(f) if i != pos else 'X' for i, f in enumerate(chain)]
    q = INTRO21.format(s=' → '.join(shown)) + '\n\nПроверьте себя: какое из приведённых веществ может быть веществом X?'
    o = opts([disp(f) for f in items])
    a = str(items.index(x) + 1)
    eqs = _typical_eqs(chain)
    e = f'X — {disp(x)}. Уравнения: ' + '; '.join(f'{i + 1}) {eq_text(eq)}' for i, eq in enumerate(eqs)) + '.'
    return pcard('ch-oge-21-find-x', q, a, e, k='one', o=o, eqs=eqs, p={'chain': chain, 'pos': pos, 'items': items})


PREF21 = ['O2', 'H2O', T21, 'HCl', 'H2SO4', 'HNO3', 'NaOH', 'KOH', 'CO2', 'SO2', 'SO3', 'H2', 'Cl2', 'AgNO3', 'BaCl2',
          'Ba(NO3)2', 'Na2CO3', 'K2CO3', 'Ca(OH)2', 'Ba(OH)2', 'H3PO4', 'Na3PO4', 'K3PO4', 'CuSO4', 'C', 'CO', 'Fe', 'Zn',
          'Mg', 'Al', 'Cu']


def _typical_eqs(chain):
    """Пояснение: для каждой стадии — самое типовое уравнение из базы участка (реагенты O2, H2O, нагревание, HCl …)."""
    Em = edges21('my')
    eqs = []
    for i in range(3):
        pref = (['NaOH', 'KOH', 'Ca(OH)2'] + PREF21) if 'NH4' in chain[i] and chain[i + 1] == 'NH3' else PREF21
        rgs = sorted(Em.get((chain[i], chain[i + 1]), ()), key=lambda x: pref.index(x) if x in pref else 99)
        done = False
        for rg in rgs:
            for r in D.REACTIONS:
                if chain[i] in r['lhs'] and chain[i + 1] in r['rhs'] and (
                        (rg == T21 and len(r['lhs']) == 1) or (rg != T21 and rg in r['lhs'])):
                    kl, kr = balance(r['lhs'], r['rhs'])
                    eqs.append((r['lhs'], r['rhs'], kl, kr))
                    done = True
                    break
            if done:
                break
    return eqs


def _stage_eqs(a, b, rg):
    """Все разные уравнения стадии a → b данным реагентом (по всей базе)."""
    out = set()
    for r in _by_reagent().get(a, []):
        if b not in r['rhs']:
            continue
        rest = [x for x in r['lhs'] if x not in (a, 'H2O')]
        if (rg == T21 and len(r['lhs']) == 1) or (rest == [rg]) or (rg == 'H2O' and not rest and len(r['lhs']) > 1):
            out.add((tuple(r['lhs']), tuple(r['rhs'])))
    return out


def _steps21(p):
    ch, res = p['chain'], []
    for i in range(3):
        rg = p['reag'][int(p['ans'][LET[i]]) - 1]
        (lhs, rhs), = _stage_eqs(ch[i], ch[i + 1], rg)
        kl, kr = balance(list(lhs), list(rhs))
        res.append(sum(kl) + sum(kr))
    return res


def _solve21r(p):
    ch = p['chain']
    a = {}
    for i in range(3):
        good = [j for j, r in enumerate(p['reag']) if can21(ch[i], ch[i + 1], r)]
        if len(good) != 1:
            return f'переход {i}: {good}'
        a[LET[i]] = str(good[0] + 1)
    return a


@proto('ch-oge-21-reagents', 'ОГЭ', 21, 'Цепочка превращений: реагент для каждой стадии',
       invariant='схема из четырёх веществ; для каждого превращения выбрать реагент (или нагревание) из пяти вариантов',
       varies='цепочка и реагенты (кислоты, щёлочи, соли, кислород, вода, нагревание …)',
       answer_rule='реагент выбирают по классу превращения: основание → соль — кислота; соль → нерастворимое основание — '
                   'щёлочь; хлорид → нитрат — AgNO3; нерастворимый гидроксид → оксид — нагревание …',
       mistakes=['для замены аниона берут кислоту вместо соли серебра/бария', 'нерастворимое основание «получают» водой'],
       solve=_solve21r, kind='dict', kes=['4.12'], solve_steps=_steps21,
       fidelity=_F21('реагент для каждой стадии (соответствие 3 → 5) + сумма коэффициентов каждого уравнения',
                     'три элемента критериев (по уравнению на стадию): реагент и коэффициенты каждого уравнения'))
def g21_reag(rng):
    chain, el = _chain21(rng)
    E = edges21()
    Em = edges21('my')
    pools = [sorted(Em[(chain[i], chain[i + 1])]) for i in range(3)]
    for _ in range(30):
        pick = [rng.choice(p) for p in pools]
        if len(set(pick)) < 3:
            continue
        # каждый выбранный реагент подходит только к «своему» переходу
        if any(pick[j] in E[(chain[i], chain[i + 1])] for i in range(3) for j in range(3) if i != j):
            continue
        extra = [r for r in REAG21 + [T21] if r not in pick and all(r not in E[(chain[i], chain[i + 1])] for i in range(3))]
        dist = rng.sample(extra, 2)
        break
    else:
        raise Retry
    reag = shuffled(rng, pick + dist)
    shown = ' → '.join(disp(f) for f in chain)
    q = INTRO21.format(s=shown) + ('\n\nПроверьте себя: установите соответствие между превращением и реагентом (условием), '
                                   'с помощью которого его можно осуществить.')
    left = [f'{disp(chain[i])} → {disp(chain[i + 1])}' for i in range(3)]
    o = match_opts(left, [r if r == T21 else disp(r) for r in reag])
    a = {LET[i]: str(reag.index(pick[i]) + 1) for i in range(3)}
    eqs = []
    for i in range(3):
        for r in chemdb.load()['reactions']:
            if chain[i] in r['lhs'] and chain[i + 1] in r['rhs'] and ((pick[i] == T21 and len(r['lhs']) == 1) or pick[i] in r['lhs']):
                eqs.append((r['lhs'], r['rhs'], r['k'][0], r['k'][1]))
                break
    e = 'Уравнения: ' + '; '.join(f'{LET[i]}) {eq_text(eq)}' for i, eq in enumerate(eqs)) + '. Ответ: ' + \
        ''.join(a[x] for x in LET[:3]) + '.'
    steps = None
    uniq = [_stage_eqs(chain[i], chain[i + 1], pick[i]) for i in range(3)]
    if all(len(u) == 1 for u in uniq) and len(eqs) == 3:
        steps = [(f'сумма коэффициентов в уравнении стадии {i + 1}', sum(eqs[i][2]) + sum(eqs[i][3])) for i in range(3)]
    return pcard('ch-oge-21-reagents', q, a, e, k='match', o=o, eqs=eqs, p={'chain': chain, 'reag': reag, 'ans': a},
                 steps=steps)


# ================================================================= 23. Реальный эксперимент: определение веществ в склянках

BOTTLE23 = [f for f in SOL_EL if f not in EXOTIC and f not in ('HI', 'HBr', 'Ca(OH)2')]
REAG23 = [f for f in SOL_EL if f not in EXOTIC and f not in ('HI', 'HBr')] + ['Zn', 'Cu']


def _vis(t):
    return t is not None and t != frozenset({'нет'})


def _ident(r, s, other, fn):
    """Реактив r обнаруживает вещество s: с s есть видимый признак, с другим веществом — нет."""
    a, b = fn(s, r), fn(other, r)
    if a is None or b is None:
        return None
    return _vis(a) and not _vis(b)


def _valid_pairs23(s1, s2, reag, fn):
    out = []
    for i in range(3):
        for j in range(3):
            if i != j:
                x, y = _ident(reag[i], s1, s2, fn), _ident(reag[j], s2, s1, fn)
                if x is None or y is None:
                    return None
                if x and y:
                    out.append(tuple(sorted((i, j))))
    return sorted(set(out))


@lru_cache(maxsize=None)
def obs23(s, r):
    """Наблюдение для задания 23; None — если признак не описывается школьными словами или продукт экзотичен."""
    t = observe(s, r)
    if t is None or any(x.split(':')[-1] in EXOTIC for x in t) or sign23(t) is None:
        return None
    return t


def _gen23_setup(rng, need_single_event=False):
    for _ in range(300):
        s1, s2 = rng.sample(BOTTLE23, 2)
        if s1 in REAG23 and False:
            continue
        cand = [r for r in REAG23 if r not in (s1, s2)]
        ra = [r for r in cand if _ident(r, s1, s2, obs23)]
        rb = [r for r in cand if _ident(r, s2, s1, obs23)]
        if not ra or not rb:
            continue
        a, b = rng.choice(ra), rng.choice(rb)
        if a == b:
            continue
        if need_single_event and (a in ('Zn', 'Cu') or b in ('Zn', 'Cu') or
                                  len(_ion_events(s1, a) or ()) != 1 or len(_ion_events(s2, b) or ()) != 1):
            continue
        rest = [r for r in cand if r not in (a, b) and obs23(s1, r) is not None and obs23(s2, r) is not None
                and not _ident(r, s1, s2, obs23) and not _ident(r, s2, s1, obs23)]
        if not rest:
            continue
        c = rng.choice(rest)
        reag = shuffled(rng, [a, b, c])
        vp = _valid_pairs23(s1, s2, reag, obs23)
        if vp and len(vp) == 1:
            return s1, s2, reag, a, b
    raise Retry


def _names_list(fs):
    ns = [gen(f) for f in fs]
    return ', '.join(ns[:-1]) + ' и ' + ns[-1]


def stem23(s1, s2, reag):
    metals = [r for r in reag if r in METALS]
    sols = [r for r in reag if r not in METALS]
    if metals:
        rg = 'а также три реактива: ' + ', '.join(name(m) for m in metals) + (', растворы ' + _names_list(sols) if len(sols) > 1
                                                                            else ', раствор ' + gen(sols[0]))
    else:
        rg = 'а также растворы трёх реактивов: ' + _names_list(reag)
    return (f'Для проведения эксперимента выданы склянки № 1 и № 2 с растворами {gen(s1)} и {gen(s2)}, {rg}.\n'
            '1) только из указанных в перечне трёх реактивов выберите два, которые необходимы для определения каждого '
            'вещества, находящегося в склянках № 1 и № 2;\n'
            '2) составьте молекулярное, полное и сокращённое ионные уравнения реакции, которую планируете провести для '
            'определения вещества из склянки № 1;\n'
            '3) составьте молекулярное, полное и сокращённое ионные уравнения реакции, которую планируете провести для '
            'определения вещества из склянки № 2.')


def sign23(t):
    if t is None:
        return None
    if t == frozenset({'нет'}):
        return 'видимые признаки реакции отсутствуют'
    for lvl in ('color', 'gas', 'solid'):
        x = sign_text(t, lvl)
        if x and x != 'выделение бесцветного газа':
            return x
    return sign_text(t, 'solid')


def _solve23_reag(p):
    vp = _valid_pairs23(p['s1'], p['s2'], p['reag'], obs_db)
    if not vp or len(vp) != 1:
        return f'пары реактивов: {vp}'
    return ids_of(list(vp[0]))


_F23 = lambda step, cov='': F('практическое задание (5 баллов: выбор реактивов, два ионных уравнения, признаки, вывод); в тренажёре — '
                     'шаг: ' + step, 'условие — как в демоверсии 2027 №23 («Для проведения эксперимента выданы склянки '
                     '№ 1 и № 2 …»)', 'В', 30, 'пары веществ и реактивы как в банке: HCl и CaCl2 (Zn, AgNO3, KOH), MgCl2 и '
                     'BaCl2 (HCl, NaOH, H2SO4), K3PO4 и ZnSO4 (NaOH, MgCl2, NH4Cl)',
                     'реактив, дающий одинаковый признак с обоими веществами', ['1.6', '4.9', '4.10', '5.5'],
                     '5 баллов по критериям; покрыто: ' + cov)


@proto('ch-oge-23-choose-reagents', 'ОГЭ', 23, 'Реальный эксперимент: выбор двух реактивов для определения веществ в склянках',
       invariant='две склянки с растворами и три реактива; выбрать два реактива, каждый из которых даёт видимый признак '
                 'только с одним из веществ',
       varies='вещества в склянках (соли, кислоты, щёлочи) и реактивы',
       answer_rule='реактив подходит, если с «своим» веществом даёт осадок/газ, а с другим — нет видимых изменений',
       mistakes=['берут реактив, дающий одинаковый осадок с обоими веществами (AgNO3 с двумя хлоридами)',
                 'берут реактив, реакция с которым идёт без видимых признаков (нейтрализация)'],
       solve=_solve23_reag, kind='dict', kes=['1.6', '4.9', '4.10'],
       fidelity=_F23('выбор двух реактивов из трёх', 'пункт 1 (выбор реактивов), предпосылка к К1–К3'))
def g23_reag(rng):
    s1, s2, reag, a, b = _gen23_setup(rng)
    q = stem23(s1, s2, reag) + '\n\nПроверьте себя: выберите два реактива, необходимые для определения веществ.'
    o = opts([name(r) for r in reag])
    ans = ids_of([reag.index(a), reag.index(b)])
    e = (f'{cap(name(a))}: с {ins(s1)} — {sign23(obs23(s1, a))}, с {ins(s2)} — {sign23(obs23(s2, a))}. '
         f'{cap(name(b))}: с {ins(s2)} — {sign23(obs23(s2, b))}, с {ins(s1)} — {sign23(obs23(s1, b))}. '
         f'Ответ: {"".join(ans)}.')
    eqs = [x for x in (_eq_of(s1, a), _eq_of(s2, b)) if x]
    return pcard('ch-oge-23-choose-reagents', q, ans, e, k='many', o=o, eqs=eqs, p={'s1': s1, 's2': s2, 'reag': reag})


def _solve23_signs(p):
    a = {}
    for i, (s, r) in enumerate(p['left']):
        t = sign23(obs_db(s, r))
        if t not in p['signs']:
            return f'признак {s}+{r}: {t}'
        a[LET[i]] = str(p['signs'].index(t) + 1)
    return a


ALL_SIGNS23 = sorted({x for v in EXTRA_SIGNS.values() for x in v} - {'выделение газа', 'образование осадка',
                                                                    'растворение осадка', 'выделение бесцветного газа'})


@proto('ch-oge-23-signs', 'ОГЭ', 23, 'Реальный эксперимент: признаки реакций веществ из склянок с выбранными реактивами',
       invariant='две склянки и три реактива; для трёх сочетаний «вещество + реактив» указать наблюдаемый признак',
       varies='вещества, реактивы, сочетания (включая сочетание без видимых изменений)',
       answer_rule='признак — по продуктам ионного обмена: цвет осадка, газ и его запах, отсутствие изменений',
       mistakes=['цвет осадка гидроксида железа', 'запах газа', 'нейтрализация «с признаком»'],
       solve=_solve23_signs, kind='dict', kes=['1.6', '4.9', '4.10'],
       fidelity=_F23('признаки реакций (таблица наблюдений)', 'К2: признаки реакций в таблице'))
def g23_signs(rng):
    s1, s2, reag, a, b = _gen23_setup(rng)
    combos = [(s1, a), (s2, b), rng.choice([(s1, b), (s2, a)])]
    signs = [sign23(obs23(s, r)) for s, r in combos]
    if None in signs:
        raise Retry
    extra = [x for x in ALL_SIGNS23 if x not in signs]
    right = list(dict.fromkeys(signs))
    right += rng.sample(extra, 4 - len(right))
    right = shuffled(rng, right)
    q = stem23(s1, s2, reag) + ('\n\nПроверьте себя: установите соответствие между сочетанием «вещество + реактив» '
                                'и признаком реакции, который будет наблюдаться.')
    o = match_opts([f'{cap(name(s))} + {name(r)}' for s, r in combos], right)
    ans = {LET[i]: str(right.index(sg) + 1) for i, sg in enumerate(signs)}
    eqs = [x for x in (_eq_of(s, r) for s, r in combos) if x]
    e = ' '.join(f'{LET[i]}) {sg}.' for i, sg in enumerate(signs)) + (' Уравнения: ' + '; '.join(eq_text(x) for x in eqs) + '.'
                                                                       if eqs else '') + \
        ' Ответ: ' + ''.join(ans[x] for x in LET[:3]) + '.'
    return pcard('ch-oge-23-signs', q, ans, e, k='match', o=o, eqs=eqs,
                 p={'left': [list(c) for c in combos], 'signs': right})


def _steps23(p):
    out = []
    for s_, r in p['left']:
        l_, r_ = net_ionic_db(s_, r)
        out.append(sum(l_.values()) + sum(r_.values()))
    return out


def _solve23_ionic(p):
    a = {}
    for i, (s, r) in enumerate(p['left']):
        ne = net_ionic_db(s, r)
        hits = [j for j, t in enumerate(p['eqs']) if ne == (t[0], t[1])]
        if len(hits) != 1:
            return f'уравнение для {s}+{r}: {ne}'
        a[LET[i]] = str(hits[0] + 1)
    return a


@proto('ch-oge-23-ionic', 'ОГЭ', 23, 'Реальный эксперимент: сокращённые ионные уравнения реакций определения веществ',
       invariant='две склянки и три реактива; для каждого вещества выбрать сокращённое ионное уравнение реакции, '
                 'по которой его определяют выбранным реактивом',
       varies='вещества, реактивы, уравнения (осадок, газ)',
       answer_rule='в сокращённом уравнении — только ионы, образующие осадок/газ/воду, и сам этот продукт',
       mistakes=['записывают ионы-наблюдатели', 'выбирают уравнение для другого вещества'],
       solve=_solve23_ionic, kind='param', kes=['5.5'], solve_steps=_steps23,
       fidelity=_F23('сокращённые ионные уравнения (пункты 2, 3) + сумма их коэффициентов',
                     'часть К1: сокращённые ионные уравнения обеих реакций (молекулярное и полное — в пояснении)'))
def g23_ionic(rng):
    s1, s2, reag, a, b = _gen23_setup(rng, need_single_event=True)
    t1 = _target(*next(iter(_ion_events(s1, a))))
    t2 = _target(*next(iter(_ion_events(s2, b))))
    if t1 == t2:
        raise Retry
    others = [_target(c, an) for c, an in TARGETS14]
    others = [t for t in others if t not in (t1, t2)]
    eqs_t = shuffled(rng, [t1, t2] + rng.sample(others, 2))
    q = stem23(s1, s2, reag) + ('\n\nПроверьте себя: установите соответствие между веществом и сокращённым ионным '
                                'уравнением реакции, с помощью которой его можно определить выбранным реактивом.')
    o = match_opts([cap(name(s1)), cap(name(s2))], [ionic_eq_text(t) for t in eqs_t])
    ans = {'А': str(eqs_t.index(t1) + 1), 'Б': str(eqs_t.index(t2) + 1)}
    eqs = [x for x in (_eq_of(s1, a), _eq_of(s2, b)) if x]
    e = (f'А) {name(s1)} + {name(a)}: {ionic_eq_text(t1)}. Б) {name(s2)} + {name(b)}: {ionic_eq_text(t2)}. '
         f'Ответ: {ans["А"]}{ans["Б"]}.')
    steps = [(f'сумма коэффициентов в сокращённом ионном уравнении для {gen(x)}', sum(t[0].values()) + sum(t[1].values()))
             for x, t in ((s1, t1), (s2, t2))]
    return pcard('ch-oge-23-ionic', q, ans, e, k='match', o=o, eqs=eqs,
                 p={'left': [[s1, a], [s2, b]], 'eqs': [[t[0], t[1]] for t in eqs_t]}, steps=steps)
