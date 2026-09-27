"""База органических веществ и реакций (ЕГЭ-химия, задания 10–16, 25, 32, 33).

Формат — как в chemdb.py: SUBSTANCES (f, name, cls, hom, trivial, view, org=True …), REACTIONS (lhs, rhs, type, cond, …).
Соглашения этого модуля:
  * f — ASCII-запись, которую понимает parse_formula; у изомеров — полуструктурная (CH3CH(CH3)CH3), чтобы ключи
    не совпадали; циклоалканы — (CH2)n; положение в кольце различают порядком записи (о-, м-, п-ксилол).
  * view — структурная запись для показа (с индексами, «=», «≡»).
  * SMILES[f] — строение для независимых проверок: брутто-формула по SMILES должна совпасть с parse_formula(f);
    по SMILES же считаются σ/π-связи и гибридизация атомов углерода (задание 11).
  * В реакции lhs[0] — органический субстрат, rhs[0] — главный органический продукт; rk — «ключ реагента»
    (с чем реагирует субстрат в данном смысле: 'Br2aq' — бромная вода, 'Br2hv' — бром на свету и т. п.).
  * Реакции, которые balance() не уравнивает однозначно (окисление KMnO4 с двумя продуктами окисления, полимеризация,
    качественные реакции с комплексами), — в FACTS (без уравнения).
  * NOT_REACT — проверенные «не реагирует» (для заданий «выберите все/два вещества, с которыми реагирует…»).
Источники: школьные факты (учебники органической химии 10–11 кл., кодификатор ЕГЭ 2027); названия и ID — Wikidata (CC0).

  python3 tools/research/chemdb_org.py     # собственные проверки модуля (SMILES ↔ формула, реакции, NOT_REACT)
"""
import re
from collections import Counter

# ================================================================= SMILES (упрощённый разбор для проверок)

_VAL = {'C': 4, 'N': 3, 'O': 2, 'S': 2, 'F': 1, 'Cl': 1, 'Br': 1, 'I': 1, 'P': 3, 'B': 3}
_TOK = re.compile(r'\[[^\]]+\]|Br|Cl|[BCNOSPFI]|[cnos]|[=#:\-\(\)\.]|%\d\d|\d')


def smiles_info(smi):
    """SMILES → dict(atoms=Counter (с H), sigma, pi, hyb=Counter{'sp3','sp2','sp'} по атомам C, rings).
    Поддержка: органическое подмножество, ароматика (c, n, o), кольца, ветви, [атом с H/зарядом], '.'."""
    atoms, bonds = [], []          # atoms: dict(el, arom, hexp or None); bonds: (i, j, order)
    stack, ring, prev, order = [], {}, None, None
    for t in _TOK.findall(smi):
        if t == '(':
            stack.append(prev)
        elif t == ')':
            prev = stack.pop()
        elif t == '.':
            prev = None
        elif t in '-=#:':
            order = {'-': 1, '=': 2, '#': 3, ':': 1.5}[t]
        elif t[0] == '%' or t.isdigit():
            d = t
            if d in ring:
                j, o0 = ring.pop(d)
                o = order or o0 or (1.5 if atoms[prev]['arom'] and atoms[j]['arom'] else 1)
                bonds.append((j, prev, o))
            else:
                ring[d] = (prev, order)
            order = None
        else:
            if t[0] == '[':
                m = re.match(r'\[(\d*)([A-Z][a-z]?|[cnos])(H\d*)?([+-]\d*)?\]', t)
                el = m.group(2)
                h = m.group(3)
                hexp = (int(h[1:] or 1) if h else 0)
            else:
                el, hexp = t, None
            arom = el.islower()
            atoms.append({'el': el.upper() if arom else el, 'arom': arom, 'hexp': hexp})
            i = len(atoms) - 1
            if prev is not None:
                o = order or (1.5 if atoms[prev]['arom'] and arom else 1)
                bonds.append((prev, i, o))
            prev, order = i, None
    deg = [0.0] * len(atoms)
    for i, j, o in bonds:
        deg[i] += o
        deg[j] += o
    cnt, hyb = Counter(), Counter()
    nh = 0
    for i, a in enumerate(atoms):
        cnt[a['el']] += 1
        if a['hexp'] is not None:
            h = a['hexp']
        else:
            h = max(0, int(_VAL.get(a['el'], 0) - deg[i] + 1e-9))
        nh += h
        if a['el'] == 'C':
            os_ = [o for x, y, o in bonds if i in (x, y)]
            if any(o == 3 for o in os_) or sum(o == 2 for o in os_) >= 2:
                hyb['sp'] += 1
            elif any(o in (2, 1.5) for o in os_):
                hyb['sp2'] += 1
            else:
                hyb['sp3'] += 1
    if nh:
        cnt['H'] += nh
    pi = sum({1: 0, 1.5: 0.5, 2: 1, 3: 2}[o] for _, _, o in bonds)
    rings = len(bonds) - len(atoms) + (smi.count('.') + 1)
    return {'atoms': cnt, 'sigma': len(bonds) + nh, 'pi': pi, 'hyb': hyb, 'rings': rings}


# ================================================================= вещества

SUBSTANCES = []
SMILES = {}
_SRC = 'школьный курс органической химии; названия сверены с Wikidata (CC0), где найдено'


def _view(v):
    return v.replace('#', '≡').replace('-', '–') if v else v


def _sub_digits(v):
    return re.sub(r'(?<=[A-Za-z)\]])(\d+)', lambda m: m.group(1).translate(str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')), v)


def S(f, name, cls, hom, smi=None, triv=(), view=None, **kw):
    row = dict(f=f, name=name, cls=cls, hom=hom, org=True, src=_SRC)
    if triv:
        row['trivial'] = list(triv)
    row['view'] = _sub_digits(_view(view or f))
    row.update(kw)
    SUBSTANCES.append(row)
    if smi:
        SMILES[f] = smi
    return row


def I(f, name, cls='неорганическое', **kw):
    """Неорганический реагент (основная запись — в chemdb_inorg.py; здесь — чтобы реакции органики были замкнуты)."""
    row = dict(f=f, name=name, cls=cls, org=False, src='реагент для реакций органики')
    row.update(kw)
    SUBSTANCES.append(row)


HC = 'углеводород'
# ---------------------------------------------------------------- алканы
A = 'алканы'
S('CH4', 'метан', HC, A, 'C', state='г', props=['основной компонент природного газа'])
S('C2H6', 'этан', HC, A, 'CC', view='CH3-CH3', state='г')
S('C3H8', 'пропан', HC, A, 'CCC', view='CH3-CH2-CH3', state='г')
S('CH3CH2CH2CH3', 'бутан', HC, A, 'CCCC', view='CH3-CH2-CH2-CH3', state='г')
S('CH3CH(CH3)CH3', '2-метилпропан', HC, A, 'CC(C)C', triv=['изобутан'], view='CH3-CH(CH3)-CH3', state='г')
S('CH3(CH2)3CH3', 'пентан', HC, A, 'CCCCC', view='CH3-(CH2)3-CH3', state='ж')
S('CH3CH(CH3)CH2CH3', '2-метилбутан', HC, A, 'CC(C)CC', triv=['изопентан'], view='CH3-CH(CH3)-CH2-CH3', state='ж')
S('C(CH3)4', '2,2-диметилпропан', HC, A, 'CC(C)(C)C', triv=['неопентан'], view='C(CH3)4', state='г')
S('CH3(CH2)4CH3', 'гексан', HC, A, 'CCCCCC', view='CH3-(CH2)4-CH3', state='ж')
S('CH3CH(CH3)(CH2)2CH3', '2-метилпентан', HC, A, 'CC(C)CCC', view='CH3-CH(CH3)-CH2-CH2-CH3', state='ж')
S('CH3CH2CH(CH3)CH2CH3', '3-метилпентан', HC, A, 'CCC(C)CC', view='CH3-CH2-CH(CH3)-CH2-CH3', state='ж')
S('CH3CH(CH3)CH(CH3)CH3', '2,3-диметилбутан', HC, A, 'CC(C)C(C)C', view='CH3-CH(CH3)-CH(CH3)-CH3', state='ж')
S('CH3C(CH3)2CH2CH3', '2,2-диметилбутан', HC, A, 'CC(C)(C)CC', view='CH3-C(CH3)2-CH2-CH3', state='ж')
S('CH3(CH2)5CH3', 'гептан', HC, A, 'CCCCCCC', view='CH3-(CH2)5-CH3', state='ж')
S('CH3(CH2)6CH3', 'октан', HC, A, 'CCCCCCCC', view='CH3-(CH2)6-CH3', state='ж')
S('(CH3)3CCH2CH(CH3)2', '2,2,4-триметилпентан', HC, A, 'CC(C)(C)CC(C)C', triv=['изооктан'],
  view='(CH3)3C-CH2-CH(CH3)2', state='ж', use=['эталон октанового числа 100'])
S('(CH3)2CH(CH2)2CH(CH3)2', '2,5-диметилгексан', HC, A, 'CC(C)CCC(C)C', view='(CH3)2CH-CH2-CH2-CH(CH3)2', state='ж')
S('CH3(CH2)8CH3', 'декан', HC, A, 'CCCCCCCCCC', view='CH3-(CH2)8-CH3', state='ж')
# ---------------------------------------------------------------- циклоалканы
A = 'циклоалканы'
S('(CH2)3', 'циклопропан', HC, A, 'C1CC1', view='C3H6 (цикл)', state='г')
S('(CH2)4', 'циклобутан', HC, A, 'C1CCC1', view='C4H8 (цикл)', state='г')
S('(CH2)5', 'циклопентан', HC, A, 'C1CCCC1', view='C5H10 (цикл)', state='ж')
S('(CH2)6', 'циклогексан', HC, A, 'C1CCCCC1', view='C6H12 (цикл)', state='ж')
S('C3H5CH3', 'метилциклопропан', HC, A, 'CC1CC1', view='CH3-C3H5 (цикл)', state='г')
S('C4H7CH3', 'метилциклобутан', HC, A, 'CC1CCC1', view='CH3-C4H7 (цикл)', state='ж')
S('C5H9CH3', 'метилциклопентан', HC, A, 'CC1CCCC1', view='CH3-C5H9 (цикл)', state='ж')
S('C6H11CH3', 'метилциклогексан', HC, A, 'CC1CCCCC1', view='CH3-C6H11 (цикл)', state='ж')
S('C3H4(CH3)2', '1,2-диметилциклопропан', HC, A, 'CC1CC1C', view='(CH3)2C3H4 (цикл)', state='ж')
S('C5H9C2H5', 'этилциклопентан', HC, A, 'CCC1CCCC1', view='C2H5-C5H9 (цикл)', state='ж')
# ---------------------------------------------------------------- алкены
A = 'алкены'
S('C2H4', 'этен', HC, A, 'C=C', triv=['этилен'], view='CH2=CH2', state='г')
S('CH2CHCH3', 'пропен', HC, A, 'C=CC', triv=['пропилен'], view='CH2=CH-CH3', state='г')
S('CH2CHCH2CH3', 'бутен-1', HC, A, 'C=CCC', view='CH2=CH-CH2-CH3', state='г')
S('CH3CHCHCH3', 'бутен-2', HC, A, 'CC=CC', view='CH3-CH=CH-CH3', state='г', notes='цис-транс-изомерия')
S('CH2C(CH3)2', '2-метилпропен', HC, A, 'C=C(C)C', triv=['изобутилен'], view='CH2=C(CH3)-CH3', state='г')
S('CH2CH(CH2)2CH3', 'пентен-1', HC, A, 'C=CCCC', view='CH2=CH-CH2-CH2-CH3', state='ж')
S('CH3CHCHCH2CH3', 'пентен-2', HC, A, 'CC=CCC', view='CH3-CH=CH-CH2-CH3', state='ж', notes='цис-транс-изомерия')
S('CH2C(CH3)CH2CH3', '2-метилбутен-1', HC, A, 'C=C(C)CC', view='CH2=C(CH3)-CH2-CH3', state='ж')
S('(CH3)2CCHCH3', '2-метилбутен-2', HC, A, 'CC=C(C)C', view='CH3-C(CH3)=CH-CH3', state='ж')
S('CH2CHCH(CH3)2', '3-метилбутен-1', HC, A, 'C=CC(C)C', view='CH2=CH-CH(CH3)-CH3', state='ж')
S('CH2CH(CH2)3CH3', 'гексен-1', HC, A, 'C=CCCCC', view='CH2=CH-(CH2)3-CH3', state='ж')
S('(CH3)2CC(CH3)2', '2,3-диметилбутен-2', HC, A, 'CC(C)=C(C)C', view='(CH3)2C=C(CH3)2', state='ж')
S('C6H10', 'циклогексен', HC, 'циклоалкены', 'C1=CCCCC1', view='C6H10 (цикл)', state='ж')
S('C5H8', 'циклопентен', HC, 'циклоалкены', 'C1=CCCC1', view='C5H8 (цикл)', state='ж')
# ---------------------------------------------------------------- алкадиены
A = 'алкадиены'
S('CH2CCH2', 'пропадиен', HC, A, 'C=C=C', triv=['аллен'], view='CH2=C=CH2', state='г')
S('CH2CHCHCH2', 'бутадиен-1,3', HC, A, 'C=CC=C', triv=['дивинил'], view='CH2=CH-CH=CH2', state='г',
  use=['сырьё для бутадиенового каучука'])
S('CH2CCHCH3', 'бутадиен-1,2', HC, A, 'C=C=CC', view='CH2=C=CH-CH3', state='г')
S('CH2C(CH3)CHCH2', '2-метилбутадиен-1,3', HC, A, 'C=CC(C)=C', triv=['изопрен'], view='CH2=C(CH3)-CH=CH2', state='ж',
  use=['мономер натурального (изопренового) каучука'])
S('CH2CHCHCHCH3', 'пентадиен-1,3', HC, A, 'C=CC=CC', view='CH2=CH-CH=CH-CH3', state='ж')
S('CH2CHCH2CHCH2', 'пентадиен-1,4', HC, A, 'C=CCC=C', view='CH2=CH-CH2-CH=CH2', state='ж')
S('CH2C(CH3)C(CH3)CH2', '2,3-диметилбутадиен-1,3', HC, A, 'C=C(C)C(C)=C', view='CH2=C(CH3)-C(CH3)=CH2', state='ж')
S('C5H6', 'циклопентадиен-1,3', HC, 'циклоалкадиены', 'C1=CC=CC1', view='C5H6 (цикл)', state='ж')
# ---------------------------------------------------------------- алкины
A = 'алкины'
S('C2H2', 'этин', HC, A, 'C#C', triv=['ацетилен'], view='CH#CH', state='г')
S('CHCCH3', 'пропин', HC, A, 'C#CC', view='CH#C-CH3', state='г')
S('CHCCH2CH3', 'бутин-1', HC, A, 'C#CCC', view='CH#C-CH2-CH3', state='г')
S('CH3CCCH3', 'бутин-2', HC, A, 'CC#CC', view='CH3-C#C-CH3', state='ж')
S('CHC(CH2)2CH3', 'пентин-1', HC, A, 'C#CCCC', view='CH#C-CH2-CH2-CH3', state='ж')
S('CH3CCCH2CH3', 'пентин-2', HC, A, 'CC#CCC', view='CH3-C#C-CH2-CH3', state='ж')
S('CHCCH(CH3)2', '3-метилбутин-1', HC, A, 'C#CC(C)C', view='CH#C-CH(CH3)-CH3', state='ж')
S('CHC(CH2)3CH3', 'гексин-1', HC, A, 'C#CCCCC', view='CH#C-(CH2)3-CH3', state='ж')
S('CH2CHCCH', 'бутен-1-ин-3', HC, 'алкенины', 'C=CC#C', triv=['винилацетилен'], view='CH2=CH-C#CH', state='г')
# ---------------------------------------------------------------- арены
A = 'арены'
S('C6H6', 'бензол', HC, A, 'c1ccccc1', view='C6H6', state='ж')
S('C6H5CH3', 'метилбензол', HC, A, 'Cc1ccccc1', triv=['толуол'], view='C6H5-CH3', state='ж')
S('C6H5C2H5', 'этилбензол', HC, A, 'CCc1ccccc1', view='C6H5-CH2-CH3', state='ж')
S('C6H4(CH3)2', '1,2-диметилбензол', HC, A, 'Cc1ccccc1C', triv=['о-ксилол'], view='C6H4(CH3)2 (1,2-)', state='ж')
S('(CH3)2C6H4', '1,3-диметилбензол', HC, A, 'Cc1cccc(C)c1', triv=['м-ксилол'], view='C6H4(CH3)2 (1,3-)', state='ж')
S('CH3C6H4CH3', '1,4-диметилбензол', HC, A, 'Cc1ccc(C)cc1', triv=['п-ксилол'], view='CH3-C6H4-CH3 (1,4-)', state='ж')
S('C6H5CH2CH2CH3', 'пропилбензол', HC, A, 'CCCc1ccccc1', view='C6H5-CH2-CH2-CH3', state='ж')
S('C6H5CH(CH3)2', 'изопропилбензол', HC, A, 'CC(C)c1ccccc1', triv=['кумол'], view='C6H5-CH(CH3)2', state='ж')
S('C6H3(CH3)3', '1,3,5-триметилбензол', HC, A, 'Cc1cc(C)cc(C)c1', triv=['мезитилен'], view='C6H3(CH3)3', state='ж')
S('C6H5CHCH2', 'винилбензол', HC, 'арены (с непредельной боковой цепью)', 'C=Cc1ccccc1', triv=['стирол'],
  view='C6H5-CH=CH2', state='ж')
S('C6H5CCH', 'этинилбензол', HC, 'арены (с непредельной боковой цепью)', 'C#Cc1ccccc1', triv=['фенилацетилен'],
  view='C6H5-C#CH', state='ж')
S('C10H8', 'нафталин', HC, 'арены (конденсированные)', 'c1ccc2ccccc2c1', view='C10H8', state='тв')

# ---------------------------------------------------------------- галогенпроизводные
HL = 'галогенпроизводное'
A = 'галогеналканы'
S('CH3Cl', 'хлорметан', HL, A, 'CCl', triv=['метилхлорид'], state='г')
S('CH2Cl2', 'дихлорметан', HL, A, 'ClCCl', state='ж')
S('CHCl3', 'трихлорметан', HL, A, 'ClC(Cl)Cl', triv=['хлороформ'], state='ж')
S('CCl4', 'тетрахлорметан', HL, A, 'ClC(Cl)(Cl)Cl', triv=['четырёххлористый углерод'], state='ж')
S('CH3Br', 'бромметан', HL, A, 'CBr', state='г')
S('CH3I', 'иодметан', HL, A, 'CI', state='ж')
S('C2H5Cl', 'хлорэтан', HL, A, 'CCCl', triv=['этилхлорид'], view='CH3-CH2Cl', state='г')
S('C2H5Br', 'бромэтан', HL, A, 'CCBr', view='CH3-CH2Br', state='ж')
S('CH3CH2CH2Cl', '1-хлорпропан', HL, A, 'CCCCl', view='CH3-CH2-CH2Cl', state='ж')
S('CH3CHClCH3', '2-хлорпропан', HL, A, 'CC(C)Cl', view='CH3-CHCl-CH3', state='ж')
S('CH3CH2CH2Br', '1-бромпропан', HL, A, 'CCCBr', view='CH3-CH2-CH2Br', state='ж')
S('CH3CHBrCH3', '2-бромпропан', HL, A, 'CC(C)Br', view='CH3-CHBr-CH3', state='ж')
S('CH3(CH2)3Br', '1-бромбутан', HL, A, 'CCCCBr', view='CH3-(CH2)2-CH2Br', state='ж')
S('CH3CHBrCH2CH3', '2-бромбутан', HL, A, 'CCC(C)Br', view='CH3-CHBr-CH2-CH3', state='ж')
S('CH3CHClCH2CH3', '2-хлорбутан', HL, A, 'CCC(C)Cl', view='CH3-CHCl-CH2-CH3', state='ж')
S('(CH3)3CBr', '2-бром-2-метилпропан', HL, A, 'CC(C)(C)Br', view='(CH3)3C-Br', state='ж')
S('(CH3)3CCl', '2-хлор-2-метилпропан', HL, A, 'CC(C)(C)Cl', view='(CH3)3C-Cl', state='ж')
S('(CH3)2CHCH2Br', '1-бром-2-метилпропан', HL, A, 'CC(C)CBr', view='(CH3)2CH-CH2Br', state='ж')
S('(CH3)2CClCH2CH3', '2-хлор-2-метилбутан', HL, A, 'CCC(C)(C)Cl', view='CH3-CCl(CH3)-CH2-CH3', state='ж')
S('(CH3)2CBrCH2CH3', '2-бром-2-метилбутан', HL, A, 'CCC(C)(C)Br', view='CH3-CBr(CH3)-CH2-CH3', state='ж')
S('CH2ClCH2Cl', '1,2-дихлорэтан', HL, A, 'ClCCCl', view='CH2Cl-CH2Cl', state='ж')
S('CH2BrCH2Br', '1,2-дибромэтан', HL, A, 'BrCCBr', view='CH2Br-CH2Br', state='ж')
S('CH3CHCl2', '1,1-дихлорэтан', HL, A, 'CC(Cl)Cl', view='CH3-CHCl2', state='ж')
S('CH3CHBr2', '1,1-дибромэтан', HL, A, 'CC(Br)Br', view='CH3-CHBr2', state='ж')
S('CH2BrCHBrCH3', '1,2-дибромпропан', HL, A, 'CC(Br)CBr', view='CH2Br-CHBr-CH3', state='ж')
S('CH2ClCHClCH3', '1,2-дихлорпропан', HL, A, 'CC(Cl)CCl', view='CH2Cl-CHCl-CH3', state='ж')
S('CH3CBr2CH3', '2,2-дибромпропан', HL, A, 'CC(C)(Br)Br', view='CH3-CBr2-CH3', state='ж')
S('CH3CCl2CH3', '2,2-дихлорпропан', HL, A, 'CC(C)(Cl)Cl', view='CH3-CCl2-CH3', state='ж')
S('CH2BrCH2CH2Br', '1,3-дибромпропан', HL, A, 'BrCCCBr', view='CH2Br-CH2-CH2Br', state='ж')
S('CH2BrCHBrCH2CH3', '1,2-дибромбутан', HL, A, 'CCC(Br)CBr', view='CH2Br-CHBr-CH2-CH3', state='ж')
S('CH3CHBrCHBrCH3', '2,3-дибромбутан', HL, A, 'CC(Br)C(C)Br', view='CH3-CHBr-CHBr-CH3', state='ж')
S('CH3CBr2CH2CH3', '2,2-дибромбутан', HL, A, 'CCC(C)(Br)Br', view='CH3-CBr2-CH2-CH3', state='ж')
S('CH2Br(CH2)2CH2Br', '1,4-дибромбутан', HL, A, 'BrCCCCBr', view='CH2Br-CH2-CH2-CH2Br', state='ж')
S('(CH3)2CBrCH2Br', '1,2-дибром-2-метилпропан', HL, A, 'CC(C)(Br)CBr', view='CH2Br-CBr(CH3)-CH3', state='ж')
S('CHBr2CHBr2', '1,1,2,2-тетрабромэтан', HL, A, 'BrC(Br)C(Br)Br', view='CHBr2-CHBr2', state='ж')
S('CH2BrCHBrCHBrCH2Br', '1,2,3,4-тетрабромбутан', HL, A, 'BrCC(Br)C(Br)CBr', view='CH2Br-CHBr-CHBr-CH2Br', state='тв')
S('CH2BrCBr(CH3)CHBrCH2Br', '1,2,3,4-тетрабром-2-метилбутан', HL, A, 'BrCC(C)(Br)C(Br)CBr',
  view='CH2Br-CBr(CH3)-CHBr-CH2Br', state='ж')
S('C6H6Cl6', '1,2,3,4,5,6-гексахлорциклогексан', HL, A, 'ClC1C(Cl)C(Cl)C(Cl)C(Cl)C1Cl', triv=['гексахлоран'],
  view='C6H6Cl6', state='тв')
S('(CH2)2CHBr', 'бромциклопропан', HL, A, 'BrC1CC1', view='C3H5Br (цикл)', state='ж')
S('C6H11Cl', 'хлорциклогексан', HL, A, 'ClC1CCCCC1', view='C6H11Cl (цикл)', state='ж')
S('C6H10Br2', '1,2-дибромциклогексан', HL, A, 'BrC1CCCCC1Br', view='C6H10Br2 (цикл)', state='ж')
A = 'галогеналкены'
S('CH2CHCl', 'хлорэтен', HL, A, 'C=CCl', triv=['винилхлорид'], view='CH2=CHCl', state='г', use=['мономер ПВХ'])
S('CHBrCHBr', '1,2-дибромэтен', HL, A, 'BrC=CBr', view='CHBr=CHBr', state='ж')
S('CH3CBrCH2', '2-бромпропен', HL, A, 'CC(Br)=C', view='CH2=CBr-CH3', state='г')
S('CH2CHCH2Cl', '3-хлорпропен', HL, A, 'C=CCCl', triv=['аллилхлорид'], view='CH2=CH-CH2Cl', state='ж')
S('CH2BrCHCHCH2Br', '1,4-дибромбутен-2', HL, A, 'BrCC=CCBr', view='CH2Br-CH=CH-CH2Br', state='ж')
S('CH2CClCHCH2', '2-хлорбутадиен-1,3', HL, 'галогеналкадиены', 'C=CC(Cl)=C', triv=['хлоропрен'],
  view='CH2=CCl-CH=CH2', state='ж', use=['мономер хлоропренового каучука'])
S('CF2CF2', 'тетрафторэтен', HL, A, 'FC(F)=C(F)F', triv=['тетрафторэтилен'], view='CF2=CF2', state='г',
  use=['мономер тефлона'])
A = 'галогенарены'
S('C6H5Cl', 'хлорбензол', HL, A, 'Clc1ccccc1', view='C6H5Cl', state='ж')
S('C6H5Br', 'бромбензол', HL, A, 'Brc1ccccc1', view='C6H5Br', state='ж')
S('C6H5CH2Cl', 'хлорметилбензол', HL, A, 'ClCc1ccccc1', triv=['бензилхлорид'], view='C6H5-CH2Cl', state='ж')
S('C6H5CHBrCH3', '(1-бромэтил)бензол', HL, A, 'CC(Br)c1ccccc1', view='C6H5-CHBr-CH3', state='ж')
S('C6H5CHBrCH2Br', '(1,2-дибромэтил)бензол', HL, A, 'BrCC(Br)c1ccccc1', view='C6H5-CHBr-CH2Br', state='тв')
S('ClC6H4CH3', '2-хлортолуол', HL, A, 'Cc1ccccc1Cl', triv=['о-хлортолуол'], view='CH3-C6H4-Cl (орто-)', state='ж')
S('CH3C6H4Cl', '4-хлортолуол', HL, A, 'Cc1ccc(Cl)cc1', triv=['п-хлортолуол'], view='CH3-C6H4-Cl (пара-)', state='ж')
S('C6H5CCl3', '(трихлорметил)бензол', HL, A, 'ClC(Cl)(Cl)c1ccccc1', view='C6H5-CCl3', state='ж')

# ---------------------------------------------------------------- нитросоединения
NI = 'нитросоединение'
S('CH3NO2', 'нитрометан', NI, 'нитроалканы', 'CN(=O)=O', view='CH3-NO2', state='ж')
S('CH3CH(NO2)CH3', '2-нитропропан', NI, 'нитроалканы', 'CC(C)N(=O)=O', view='CH3-CH(NO2)-CH3', state='ж')
S('C6H5NO2', 'нитробензол', NI, 'нитроарены', 'O=N(=O)c1ccccc1', view='C6H5-NO2', state='ж')
S('CH3C6H4NO2', '2-нитротолуол', NI, 'нитроарены', 'Cc1ccccc1N(=O)=O', triv=['о-нитротолуол'],
  view='CH3-C6H4-NO2 (орто-)', state='ж')
S('C6H2(NO2)3CH3', '2,4,6-тринитротолуол', NI, 'нитроарены', 'Cc1c(N(=O)=O)cc(N(=O)=O)cc1N(=O)=O', triv=['тротил', 'тол'],
  view='CH3-C6H2(NO2)3', state='тв', use=['взрывчатое вещество'])

# ---------------------------------------------------------------- спирты
AL = 'спирт'
A = 'предельные одноатомные спирты'
S('CH3OH', 'метанол', AL, A, 'CO', triv=['метиловый спирт', 'древесный спирт'], view='CH3-OH', state='ж', props=['ядовит'])
S('C2H5OH', 'этанол', AL, A, 'CCO', triv=['этиловый спирт', 'винный спирт'], view='CH3-CH2-OH', state='ж')
S('CH3CH2CH2OH', 'пропанол-1', AL, A, 'CCCO', triv=['пропиловый спирт'], view='CH3-CH2-CH2-OH', state='ж')
S('CH3CH(OH)CH3', 'пропанол-2', AL, A, 'CC(C)O', triv=['изопропиловый спирт'], view='CH3-CH(OH)-CH3', state='ж')
S('CH3(CH2)3OH', 'бутанол-1', AL, A, 'CCCCO', triv=['бутиловый спирт'], view='CH3-(CH2)3-OH', state='ж')
S('CH3CH(OH)CH2CH3', 'бутанол-2', AL, A, 'CCC(C)O', view='CH3-CH(OH)-CH2-CH3', state='ж')
S('(CH3)2CHCH2OH', '2-метилпропанол-1', AL, A, 'CC(C)CO', view='(CH3)2CH-CH2-OH', state='ж')
S('(CH3)3COH', '2-метилпропанол-2', AL, A, 'CC(C)(C)O', triv=['трет-бутиловый спирт'], view='(CH3)3C-OH', state='ж')
S('CH3(CH2)4OH', 'пентанол-1', AL, A, 'CCCCCO', view='CH3-(CH2)4-OH', state='ж')
S('(CH3)2CHCH2CH2OH', '3-метилбутанол-1', AL, A, 'CC(C)CCO', triv=['изоамиловый спирт'], view='(CH3)2CH-CH2-CH2-OH',
  state='ж')
S('(CH3)2C(OH)CH2CH3', '2-метилбутанол-2', AL, A, 'CCC(C)(C)O', view='CH3-C(OH)(CH3)-CH2-CH3', state='ж')
S('CH3CH(OH)CH(CH3)2', '3-метилбутанол-2', AL, A, 'CC(C)C(C)O', view='CH3-CH(OH)-CH(CH3)-CH3', state='ж')
S('C6H11OH', 'циклогексанол', AL, 'циклические спирты', 'OC1CCCCC1', view='C6H11-OH', state='ж')
S('C6H5CH2OH', 'фенилметанол', AL, 'ароматические спирты', 'OCc1ccccc1', triv=['бензиловый спирт'],
  view='C6H5-CH2-OH', state='ж')
S('C6H5CH(OH)CH3', '1-фенилэтанол', AL, 'ароматические спирты', 'CC(O)c1ccccc1', view='C6H5-CH(OH)-CH3', state='ж')
S('CH2CHCH2OH', 'пропен-2-ол-1', AL, 'непредельные спирты', 'C=CCO', triv=['аллиловый спирт'], view='CH2=CH-CH2-OH',
  state='ж')
A = 'многоатомные спирты'
S('C2H4(OH)2', 'этандиол-1,2', AL, A, 'OCCO', triv=['этиленгликоль'], view='HO-CH2-CH2-OH', state='ж',
  props=['ядовит'], use=['антифриз'])
S('C3H5(OH)3', 'пропантриол-1,2,3', AL, A, 'OCC(O)CO', triv=['глицерин'], view='HO-CH2-CH(OH)-CH2-OH', state='ж',
  use=['косметика', 'производство нитроглицерина'])
S('CH3CH(OH)CH2OH', 'пропандиол-1,2', AL, A, 'CC(O)CO', triv=['пропиленгликоль'], view='CH3-CH(OH)-CH2-OH', state='ж')
S('HO(CH2)3OH', 'пропандиол-1,3', AL, A, 'OCCCO', view='HO-CH2-CH2-CH2-OH', state='ж')
S('CH3CH(OH)CH(OH)CH3', 'бутандиол-2,3', AL, A, 'CC(O)C(C)O', view='CH3-CH(OH)-CH(OH)-CH3', state='ж')
S('CH3CH2CH(OH)CH2OH', 'бутандиол-1,2', AL, A, 'CCC(O)CO', view='CH2(OH)-CH(OH)-CH2-CH3', state='ж')
S('(CH3)2C(OH)CH2OH', '2-метилпропандиол-1,2', AL, A, 'CC(C)(O)CO', view='CH2(OH)-C(OH)(CH3)-CH3', state='ж')
S('C6H5CH(OH)CH2OH', '1-фенилэтандиол-1,2', AL, A, 'OCC(O)c1ccccc1', view='C6H5-CH(OH)-CH2-OH', state='тв')
S('C6H10(OH)2', 'циклогександиол-1,2', AL, A, 'OC1CCCCC1O', view='C6H10(OH)2 (цикл)', state='тв')
A = 'алкоголяты'
S('CH3ONa', 'метилат натрия', 'алкоголят', A, 'CO[Na]', view='CH3-ONa', state='тв')
S('C2H5ONa', 'этилат натрия', 'алкоголят', A, 'CCO[Na]', view='CH3-CH2-ONa', state='тв')
S('C2H5OK', 'этилат калия', 'алкоголят', A, 'CCO[K]', view='CH3-CH2-OK', state='тв')
S('CH3CH2CH2ONa', 'пропилат натрия', 'алкоголят', A, 'CCCO[Na]', view='CH3-CH2-CH2-ONa', state='тв')
S('CH3CH(ONa)CH3', 'изопропилат натрия', 'алкоголят', A, 'CC(C)O[Na]', view='CH3-CH(ONa)-CH3', state='тв')
S('C2H4(ONa)2', 'этиленгликолят натрия', 'алкоголят', A, '[Na]OCCO[Na]', view='NaO-CH2-CH2-ONa', state='тв')
S('C3H5(ONa)3', 'глицерат натрия', 'алкоголят', A, '[Na]OCC(O[Na])CO[Na]', view='NaO-CH2-CH(ONa)-CH2-ONa', state='тв')
# ---------------------------------------------------------------- простые эфиры
A = 'простые эфиры'
S('CH3OCH3', 'диметиловый эфир', 'простой эфир', A, 'COC', view='CH3-O-CH3', state='г')
S('C2H5OC2H5', 'диэтиловый эфир', 'простой эфир', A, 'CCOCC', view='CH3-CH2-O-CH2-CH3', state='ж')
S('CH3OC2H5', 'метилэтиловый эфир', 'простой эфир', A, 'COCC', view='CH3-O-CH2-CH3', state='г')
S('C3H7OC3H7', 'дипропиловый эфир', 'простой эфир', A, 'CCCOCCC', view='CH3-CH2-CH2-O-CH2-CH2-CH3', state='ж')
# ---------------------------------------------------------------- фенолы
A = 'фенолы'
S('C6H5OH', 'фенол', 'фенол', A, 'Oc1ccccc1', triv=['карболовая кислота', 'гидроксибензол'], view='C6H5-OH', state='тв',
  props=['ядовит'])
S('CH3C6H4OH', '2-метилфенол', 'фенол', A, 'Cc1ccccc1O', triv=['о-крезол'], view='CH3-C6H4-OH (орто-)', state='тв')
S('C6H4(OH)2', '1,2-дигидроксибензол', 'фенол', A, 'Oc1ccccc1O', triv=['пирокатехин'], view='C6H4(OH)2 (1,2-)', state='тв')
S('C6H2Br3OH', '2,4,6-трибромфенол', 'фенол', A, 'Oc1c(Br)cc(Br)cc1Br', view='C6H2Br3-OH', state='тв',
  color='белый')
S('C6H2(NO2)3OH', '2,4,6-тринитрофенол', 'фенол', A, 'Oc1c(N(=O)=O)cc(N(=O)=O)cc1N(=O)=O', triv=['пикриновая кислота'],
  view='C6H2(NO2)3-OH', state='тв', color='жёлтый')
S('C6H5ONa', 'фенолят натрия', 'фенолят', 'феноляты', '[Na]Oc1ccccc1', view='C6H5-ONa', state='тв')
S('C6H5OK', 'фенолят калия', 'фенолят', 'феноляты', '[K]Oc1ccccc1', view='C6H5-OK', state='тв')
# ---------------------------------------------------------------- альдегиды
AD = 'альдегид'
A = 'предельные альдегиды'
S('HCHO', 'метаналь', AD, A, 'C=O', triv=['формальдегид', 'муравьиный альдегид'], view='H-CHO', state='г',
  use=['формалин — консервант', 'фенолформальдегидные смолы'])
S('CH3CHO', 'этаналь', AD, A, 'CC=O', triv=['ацетальдегид', 'уксусный альдегид'], view='CH3-CHO', state='ж')
S('CH3CH2CHO', 'пропаналь', AD, A, 'CCC=O', triv=['пропионовый альдегид'], view='CH3-CH2-CHO', state='ж')
S('CH3(CH2)2CHO', 'бутаналь', AD, A, 'CCCC=O', triv=['масляный альдегид'], view='CH3-CH2-CH2-CHO', state='ж')
S('(CH3)2CHCHO', '2-метилпропаналь', AD, A, 'CC(C)C=O', view='(CH3)2CH-CHO', state='ж')
S('CH3(CH2)3CHO', 'пентаналь', AD, A, 'CCCCC=O', view='CH3-(CH2)3-CHO', state='ж')
S('C6H5CHO', 'бензальдегид', AD, 'ароматические альдегиды', 'O=Cc1ccccc1', view='C6H5-CHO', state='ж')
S('CH2CHCHO', 'пропеналь', AD, 'непредельные альдегиды', 'C=CC=O', triv=['акролеин'], view='CH2=CH-CHO', state='ж')
S('OHCCHO', 'этандиаль', AD, 'диальдегиды', 'O=CC=O', triv=['глиоксаль'], view='OHC-CHO', state='ж')
# ---------------------------------------------------------------- кетоны
A = 'кетоны'
S('CH3COCH3', 'пропанон', 'кетон', A, 'CC(C)=O', triv=['ацетон', 'диметилкетон'], view='CH3-CO-CH3', state='ж',
  use=['растворитель'])
S('CH3COCH2CH3', 'бутанон', 'кетон', A, 'CCC(C)=O', triv=['метилэтилкетон'], view='CH3-CO-CH2-CH3', state='ж')
S('CH3CO(CH2)2CH3', 'пентанон-2', 'кетон', A, 'CCCC(C)=O', view='CH3-CO-CH2-CH2-CH3', state='ж')
S('CH3CH2COCH2CH3', 'пентанон-3', 'кетон', A, 'CCC(=O)CC', triv=['диэтилкетон'], view='CH3-CH2-CO-CH2-CH3', state='ж')
S('CH3COCH(CH3)2', '3-метилбутанон', 'кетон', A, 'CC(C)C(C)=O', view='CH3-CO-CH(CH3)-CH3', state='ж')
S('C6H10O', 'циклогексанон', 'кетон', 'циклические кетоны', 'O=C1CCCCC1', view='C6H10=O (цикл)', state='ж')
S('C6H5COCH3', 'метилфенилкетон', 'кетон', 'ароматические кетоны', 'CC(=O)c1ccccc1', triv=['ацетофенон'],
  view='C6H5-CO-CH3', state='ж')

# ---------------------------------------------------------------- карбоновые кислоты
AC = 'карбоновая кислота'
A = 'предельные одноосновные карбоновые кислоты'
S('HCOOH', 'метановая кислота', AC, A, 'OC=O', triv=['муравьиная кислота'], view='H-COOH', state='ж')
S('CH3COOH', 'этановая кислота', AC, A, 'CC(=O)O', triv=['уксусная кислота'], view='CH3-COOH', state='ж')
S('CH3CH2COOH', 'пропановая кислота', AC, A, 'CCC(=O)O', triv=['пропионовая кислота'], view='CH3-CH2-COOH', state='ж')
S('CH3(CH2)2COOH', 'бутановая кислота', AC, A, 'CCCC(=O)O', triv=['масляная кислота'], view='CH3-(CH2)2-COOH', state='ж')
S('(CH3)2CHCOOH', '2-метилпропановая кислота', AC, A, 'CC(C)C(=O)O', triv=['изомасляная кислота'],
  view='(CH3)2CH-COOH', state='ж')
S('CH3(CH2)3COOH', 'пентановая кислота', AC, A, 'CCCCC(=O)O', triv=['валериановая кислота'], view='CH3-(CH2)3-COOH',
  state='ж')
S('C15H31COOH', 'гексадекановая кислота', AC, 'высшие карбоновые кислоты', 'CCCCCCCCCCCCCCCC(=O)O',
  triv=['пальмитиновая кислота'], view='C15H31-COOH', state='тв')
S('C17H35COOH', 'октадекановая кислота', AC, 'высшие карбоновые кислоты', 'CCCCCCCCCCCCCCCCCC(=O)O',
  triv=['стеариновая кислота'], view='C17H35-COOH', state='тв')
S('C17H33COOH', 'октадецен-9-овая кислота', AC, 'высшие карбоновые кислоты', 'CCCCCCCCC=CCCCCCCCC(=O)O',
  triv=['олеиновая кислота'], view='C17H33-COOH', state='ж')
S('C17H31COOH', 'октадекадиен-9,12-овая кислота', AC, 'высшие карбоновые кислоты', 'CCCCCC=CCC=CCCCCCCCC(=O)O',
  triv=['линолевая кислота'], view='C17H31-COOH', state='ж')
S('CH2CHCOOH', 'пропеновая кислота', AC, 'непредельные карбоновые кислоты', 'C=CC(=O)O', triv=['акриловая кислота'],
  view='CH2=CH-COOH', state='ж')
S('CH2C(CH3)COOH', '2-метилпропеновая кислота', AC, 'непредельные карбоновые кислоты', 'C=C(C)C(=O)O',
  triv=['метакриловая кислота'], view='CH2=C(CH3)-COOH', state='ж')
S('C6H5COOH', 'бензойная кислота', AC, 'ароматические карбоновые кислоты', 'OC(=O)c1ccccc1', view='C6H5-COOH', state='тв')
S('C6H5CH2COOH', 'фенилуксусная кислота', AC, 'ароматические карбоновые кислоты', 'OC(=O)Cc1ccccc1',
  view='C6H5-CH2-COOH', state='тв')
S('HOOCCOOH', 'этандиовая кислота', AC, 'двухосновные карбоновые кислоты', 'OC(=O)C(=O)O', triv=['щавелевая кислота'],
  view='HOOC-COOH', state='тв')
S('HOOC(CH2)4COOH', 'гександиовая кислота', AC, 'двухосновные карбоновые кислоты', 'OC(=O)CCCCC(=O)O',
  triv=['адипиновая кислота'], view='HOOC-(CH2)4-COOH', state='тв')
S('HOOCC6H4COOH', 'бензол-1,4-дикарбоновая кислота', AC, 'двухосновные карбоновые кислоты', 'OC(=O)c1ccc(cc1)C(=O)O',
  triv=['терефталевая кислота'], view='HOOC-C6H4-COOH', state='тв')
S('CH3CH(OH)COOH', '2-гидроксипропановая кислота', AC, 'гидроксикислоты', 'CC(O)C(=O)O', triv=['молочная кислота'],
  view='CH3-CH(OH)-COOH', state='ж')
S('CH2ClCOOH', 'хлоруксусная кислота', AC, 'галогенкарбоновые кислоты', 'OC(=O)CCl', triv=['хлорэтановая кислота'],
  view='CH2Cl-COOH', state='тв')
S('CH3CHClCOOH', '2-хлорпропановая кислота', AC, 'галогенкарбоновые кислоты', 'CC(Cl)C(=O)O', view='CH3-CHCl-COOH',
  state='ж')
S('C5H11O5COOH', 'глюконовая кислота', AC, 'гидроксикислоты', 'OCC(O)C(O)C(O)C(O)C(=O)O', view='HOCH2-(CHOH)4-COOH',
  state='тв')
S('C3H4(OH)(COOH)3', 'лимонная кислота', AC, 'гидроксикислоты', 'OC(=O)CC(O)(C(=O)O)CC(=O)O', view='C3H4(OH)(COOH)3',
  state='тв', use=['пищевая добавка (регулятор кислотности)'])
S('CH3COOC6H4COOH', 'ацетилсалициловая кислота', AC, 'ароматические карбоновые кислоты', 'CC(=O)Oc1ccccc1C(=O)O',
  triv=['аспирин'], view='CH3COO-C6H4-COOH', state='тв', use=['жаропонижающее средство'])
# ---------------------------------------------------------------- соли карбоновых кислот
SA = 'соль карбоновой кислоты'
A = 'соли карбоновых кислот'
S('HCOONa', 'формиат натрия', SA, A, 'O=CO[Na]', view='H-COONa', state='тв')
S('HCOOK', 'формиат калия', SA, A, 'O=CO[K]', view='H-COOK', state='тв')
S('CH3COONa', 'ацетат натрия', SA, A, 'CC(=O)O[Na]', view='CH3-COONa', state='тв')
S('CH3COOK', 'ацетат калия', SA, A, 'CC(=O)O[K]', view='CH3-COOK', state='тв')
S('(CH3COO)2Ca', 'ацетат кальция', SA, A, 'CC(=O)O[Ca]OC(C)=O', view='(CH3COO)2Ca', state='тв')
S('(CH3COO)2Mg', 'ацетат магния', SA, A, 'CC(=O)O[Mg]OC(C)=O', view='(CH3COO)2Mg', state='тв')
S('(CH3COO)2Cu', 'ацетат меди(II)', SA, A, 'CC(=O)O[Cu]OC(C)=O', view='(CH3COO)2Cu', state='тв', color='сине-зелёный')
S('CH3COONH4', 'ацетат аммония', SA, A, 'CC(=O)O[NH4]', view='CH3-COONH4', state='тв')
S('CH3CH2COONa', 'пропионат натрия', SA, A, 'CCC(=O)O[Na]', view='CH3-CH2-COONa', state='тв')
S('CH3CH2COOK', 'пропионат калия', SA, A, 'CCC(=O)O[K]', view='CH3-CH2-COOK', state='тв')
S('CH3CH2COONH4', 'пропионат аммония', SA, A, 'CCC(=O)O[NH4]', view='CH3-CH2-COONH4', state='тв')
S('CH3(CH2)2COONa', 'бутират натрия', SA, A, 'CCCC(=O)O[Na]', view='CH3-(CH2)2-COONa', state='тв')
S('(CH3)2CHCOONa', '2-метилпропаноат натрия', SA, A, 'CC(C)C(=O)O[Na]', view='(CH3)2CH-COONa', state='тв')
S('C6H5COONa', 'бензоат натрия', SA, A, 'O=C(O[Na])c1ccccc1', view='C6H5-COONa', state='тв',
  use=['консервант E211'])
S('C6H5COOK', 'бензоат калия', SA, A, 'O=C(O[K])c1ccccc1', view='C6H5-COOK', state='тв')
S('KOOCCOOK', 'оксалат калия', SA, A, '[K]OC(=O)C(=O)O[K]', view='KOOC-COOK', state='тв')
S('NaOOCCOONa', 'оксалат натрия', SA, A, '[Na]OC(=O)C(=O)O[Na]', view='NaOOC-COONa', state='тв')
S('KOOCC6H4COOK', 'терефталат калия', SA, A, '[K]OC(=O)c1ccc(cc1)C(=O)O[K]', view='KOOC-C6H4-COOK', state='тв')
S('C17H35COONa', 'стеарат натрия', SA, 'мыла', 'CCCCCCCCCCCCCCCCCC(=O)O[Na]', view='C17H35-COONa', state='тв',
  use=['твёрдое мыло'])
S('C17H35COOK', 'стеарат калия', SA, 'мыла', 'CCCCCCCCCCCCCCCCCC(=O)O[K]', view='C17H35-COOK', state='тв',
  use=['жидкое мыло'])
S('(C17H35COO)2Ca', 'стеарат кальция', SA, 'мыла', 'CCCCCCCCCCCCCCCCCC(=O)O[Ca]OC(=O)CCCCCCCCCCCCCCCCC',
  view='(C17H35COO)2Ca', state='тв', sol='н')
S('C15H31COONa', 'пальмитат натрия', SA, 'мыла', 'CCCCCCCCCCCCCCCC(=O)O[Na]', view='C15H31-COONa', state='тв')
S('C15H31COOK', 'пальмитат калия', SA, 'мыла', 'CCCCCCCCCCCCCCCC(=O)O[K]', view='C15H31-COOK', state='тв')
S('C17H33COONa', 'олеат натрия', SA, 'мыла', 'CCCCCCCCC=CCCCCCCCC(=O)O[Na]', view='C17H33-COONa', state='тв')
S('C17H33COOK', 'олеат калия', SA, 'мыла', 'CCCCCCCCC=CCCCCCCCC(=O)O[K]', view='C17H33-COOK', state='тв')
S('C17H31COONa', 'линолеат натрия', SA, 'мыла', 'CCCCCC=CCC=CCCCCCCCC(=O)O[Na]', view='C17H31-COONa', state='тв')
S('C5H11O5COONH4', 'глюконат аммония', SA, A, 'OCC(O)C(O)C(O)C(O)C(=O)O[NH4]', view='HOCH2-(CHOH)4-COONH4', state='тв')
S('CH3CH(OH)COONa', 'лактат натрия', SA, A, 'CC(O)C(=O)O[Na]', view='CH3-CH(OH)-COONa', state='тв')
S('CH2ClCOONa', 'хлорацетат натрия', SA, A, 'ClCC(=O)O[Na]', view='CH2Cl-COONa', state='тв')
S('CH2CHCOONa', 'акрилат натрия', SA, A, 'C=CC(=O)O[Na]', view='CH2=CH-COONa', state='тв')

# ---------------------------------------------------------------- сложные эфиры
ES = 'сложный эфир'
A = 'сложные эфиры'
S('HCOOCH3', 'метилформиат', ES, A, 'COC=O', triv=['метиловый эфир муравьиной кислоты'], view='H-COO-CH3', state='ж')
S('HCOOC2H5', 'этилформиат', ES, A, 'CCOC=O', triv=['этиловый эфир муравьиной кислоты'], view='H-COO-CH2-CH3', state='ж')
S('HCOOCH2CH2CH3', 'пропилформиат', ES, A, 'CCCOC=O', view='H-COO-CH2-CH2-CH3', state='ж')
S('CH3COOCH3', 'метилацетат', ES, A, 'COC(C)=O', triv=['метиловый эфир уксусной кислоты'], view='CH3-COO-CH3', state='ж')
S('CH3COOC2H5', 'этилацетат', ES, A, 'CCOC(C)=O', triv=['этиловый эфир уксусной кислоты'], view='CH3-COO-CH2-CH3',
  state='ж', use=['растворитель'])
S('CH3COOCH2CH2CH3', 'пропилацетат', ES, A, 'CCCOC(C)=O', view='CH3-COO-CH2-CH2-CH3', state='ж')
S('CH3COOCH(CH3)2', 'изопропилацетат', ES, A, 'CC(C)OC(C)=O', view='CH3-COO-CH(CH3)2', state='ж')
S('CH3CH2COOCH3', 'метилпропионат', ES, A, 'CCC(=O)OC', triv=['метиловый эфир пропионовой кислоты'],
  view='CH3-CH2-COO-CH3', state='ж')
S('CH3CH2COOC2H5', 'этилпропионат', ES, A, 'CCOC(=O)CC', view='CH3-CH2-COO-CH2-CH3', state='ж')
S('CH3(CH2)2COOC2H5', 'этилбутират', ES, A, 'CCCC(=O)OCC', triv=['этиловый эфир масляной кислоты'],
  view='CH3-(CH2)2-COO-C2H5', state='ж', use=['ароматизатор (запах ананаса)'])
S('CH3COOCH2CH2CH(CH3)2', 'изоамилацетат', ES, A, 'CC(C)CCOC(C)=O', view='CH3-COO-CH2-CH2-CH(CH3)2', state='ж',
  use=['ароматизатор (запах груши, банана)'])
S('CH3COOC6H5', 'фенилацетат', ES, A, 'CC(=O)Oc1ccccc1', view='CH3-COO-C6H5', state='ж')
S('C6H5COOCH3', 'метилбензоат', ES, A, 'COC(=O)c1ccccc1', view='C6H5-COO-CH3', state='ж')
S('CH3COOCHCH2', 'винилацетат', ES, A, 'CC(=O)OC=C', view='CH3-COO-CH=CH2', state='ж')
S('CH2CHCOOCH3', 'метилакрилат', ES, A, 'COC(=O)C=C', view='CH2=CH-COO-CH3', state='ж')
S('CH2C(CH3)COOCH3', 'метилметакрилат', ES, A, 'COC(=O)C(C)=C', view='CH2=C(CH3)-COO-CH3', state='ж',
  use=['мономер органического стекла'])
S('C3H5(ONO2)3', 'тринитрат глицерина', 'сложный эфир (неорганической кислоты)', 'эфиры азотной кислоты',
  'O=N(=O)OCC(ON(=O)=O)CON(=O)=O', triv=['нитроглицерин'], view='CH2(ONO2)-CH(ONO2)-CH2(ONO2)', state='ж',
  use=['лекарство при стенокардии', 'динамит'])


def _fat(chain, n=None):
    return f'{chain}C(=O)OCC(OC(=O){chain})COC(=O){chain}'


A = 'жиры'
S('(C17H35COO)3C3H5', 'тристеарат глицерина', 'жир', A, _fat('CCCCCCCCCCCCCCCCC'), triv=['тристеарин'],
  view='(C17H35COO)3C3H5', state='тв')
S('(C15H31COO)3C3H5', 'трипальмитат глицерина', 'жир', A, _fat('CCCCCCCCCCCCCCC'), triv=['трипальмитин'],
  view='(C15H31COO)3C3H5', state='тв')
S('(C17H33COO)3C3H5', 'триолеат глицерина', 'жир', A, _fat('CCCCCCCCC=CCCCCCCC'), triv=['триолеин'],
  view='(C17H33COO)3C3H5', state='ж')
S('(C17H31COO)3C3H5', 'трилинолеат глицерина', 'жир', A, _fat('CCCCCC=CCC=CCCCCCCC'), triv=['трилинолеин'],
  view='(C17H31COO)3C3H5', state='ж')

# ---------------------------------------------------------------- амины
AM = 'амин'
A = 'предельные амины'
S('CH3NH2', 'метиламин', AM, A, 'CN', view='CH3-NH2', state='г', smell='запах аммиака / рыбы')
S('(CH3)2NH', 'диметиламин', AM, A, 'CNC', view='(CH3)2NH', state='г')
S('(CH3)3N', 'триметиламин', AM, A, 'CN(C)C', view='(CH3)3N', state='г')
S('C2H5NH2', 'этиламин', AM, A, 'CCN', view='CH3-CH2-NH2', state='г')
S('CH3NHC2H5', 'метилэтиламин', AM, A, 'CCNC', view='CH3-NH-CH2-CH3', state='ж')
S('(C2H5)2NH', 'диэтиламин', AM, A, 'CCNCC', view='(C2H5)2NH', state='ж')
S('(C2H5)3N', 'триэтиламин', AM, A, 'CCN(CC)CC', view='(C2H5)3N', state='ж')
S('CH3CH2CH2NH2', 'пропиламин', AM, A, 'CCCN', triv=['пропанамин-1'], view='CH3-CH2-CH2-NH2', state='ж')
S('(CH3)2CHNH2', 'изопропиламин', AM, A, 'CC(C)N', triv=['пропанамин-2'], view='(CH3)2CH-NH2', state='ж')
S('(CH3)2NC2H5', 'диметилэтиламин', AM, A, 'CCN(C)C', view='(CH3)2N-CH2-CH3', state='ж')
S('H2N(CH2)6NH2', 'гексаметилендиамин', AM, 'диамины', 'NCCCCCCN', triv=['гександиамин-1,6'],
  view='H2N-(CH2)6-NH2', state='тв', use=['мономер найлона'])
A = 'ароматические амины'
S('C6H5NH2', 'анилин', AM, A, 'Nc1ccccc1', triv=['фениламин', 'аминобензол'], view='C6H5-NH2', state='ж')
S('C6H5NHCH3', 'N-метиланилин', AM, A, 'CNc1ccccc1', view='C6H5-NH-CH3', state='ж')
S('CH3C6H4NH2', '4-метиланилин', AM, A, 'Cc1ccc(N)cc1', triv=['п-толуидин'], view='CH3-C6H4-NH2 (пара-)', state='тв')
S('C6H2Br3NH2', '2,4,6-триброманилин', AM, A, 'Nc1c(Br)cc(Br)cc1Br', view='C6H2Br3-NH2', state='тв', color='белый')
A = 'соли аминов'
S('CH3NH3Cl', 'хлорид метиламмония', 'соль амина', A, 'C[NH3]Cl', view='[CH3NH3]Cl', state='тв')
S('(CH3)2NH2Cl', 'хлорид диметиламмония', 'соль амина', A, 'C[NH2](C)Cl', view='[(CH3)2NH2]Cl', state='тв')
S('(CH3)3NHCl', 'хлорид триметиламмония', 'соль амина', A, 'C[NH](C)(C)Cl', view='[(CH3)3NH]Cl', state='тв')
S('C2H5NH3Cl', 'хлорид этиламмония', 'соль амина', A, 'CC[NH3]Cl', view='[C2H5NH3]Cl', state='тв')
S('(C2H5)2NH2Cl', 'хлорид диэтиламмония', 'соль амина', A, 'CC[NH2](CC)Cl', view='[(C2H5)2NH2]Cl', state='тв')
S('C6H5NH3Cl', 'хлорид фениламмония', 'соль амина', A, 'Cl[NH3]c1ccccc1', view='[C6H5NH3]Cl', state='тв')
S('C2H5NH3Br', 'бромид этиламмония', 'соль амина', A, 'CC[NH3]Br', view='[C2H5NH3]Br', state='тв')
S('CH3NH3Br', 'бромид метиламмония', 'соль амина', A, 'C[NH3]Br', view='[CH3NH3]Br', state='тв')
S('(CH3NH3)2SO4', 'сульфат метиламмония', 'соль амина', A, None, view='[CH3NH3]2SO4', state='тв')
S('C6H5NH3HSO4', 'гидросульфат фениламмония', 'соль амина', A, None, view='[C6H5NH3]HSO4', state='тв')
S('CH3NH3NO3', 'нитрат метиламмония', 'соль амина', A, None, view='[CH3NH3]NO3', state='тв')

# ---------------------------------------------------------------- аминокислоты, пептиды
AA = 'аминокислота'
A = 'аминокислоты'
S('H2NCH2COOH', 'аминоуксусная кислота', AA, A, 'NCC(=O)O', triv=['глицин', 'аминоэтановая кислота'],
  view='H2N-CH2-COOH', state='тв')
S('CH3CH(NH2)COOH', '2-аминопропановая кислота', AA, A, 'CC(N)C(=O)O', triv=['аланин', 'α-аминопропионовая кислота'],
  view='CH3-CH(NH2)-COOH', state='тв')
S('H2NCH2CH2COOH', '3-аминопропановая кислота', AA, A, 'NCCC(=O)O', triv=['β-аланин'], view='H2N-CH2-CH2-COOH',
  state='тв')
S('H2N(CH2)5COOH', '6-аминогексановая кислота', AA, A, 'NCCCCCC(=O)O', triv=['ε-аминокапроновая кислота'],
  view='H2N-(CH2)5-COOH', state='тв', use=['мономер капрона'])
S('C6H5CH2CH(NH2)COOH', 'фенилаланин', AA, A, 'NC(Cc1ccccc1)C(=O)O', triv=['2-амино-3-фенилпропановая кислота'],
  view='C6H5-CH2-CH(NH2)-COOH', state='тв')
S('HSCH2CH(NH2)COOH', 'цистеин', AA, A, 'NC(CS)C(=O)O', triv=['2-амино-3-сульфанилпропановая кислота'],
  view='HS-CH2-CH(NH2)-COOH', state='тв')
S('H2NCH2COONa', 'глицинат натрия', 'соль аминокислоты', 'соли аминокислот', 'NCC(=O)O[Na]', view='H2N-CH2-COONa',
  state='тв')
S('H2NCH2COOK', 'глицинат калия', 'соль аминокислоты', 'соли аминокислот', 'NCC(=O)O[K]', view='H2N-CH2-COOK', state='тв')
S('CH3CH(NH2)COONa', 'аланинат натрия', 'соль аминокислоты', 'соли аминокислот', 'CC(N)C(=O)O[Na]',
  view='CH3-CH(NH2)-COONa', state='тв')
S('ClH3NCH2COOH', 'хлорид глициния', 'соль аминокислоты', 'соли аминокислот', 'Cl[NH3]CC(=O)O',
  triv=['гидрохлорид глицина'], view='[H3N-CH2-COOH]Cl', state='тв')
S('CH3CH(NH3Cl)COOH', 'хлорид аланиния', 'соль аминокислоты', 'соли аминокислот', 'CC([NH3]Cl)C(=O)O',
  triv=['гидрохлорид аланина'], view='[CH3-CH(NH3)-COOH]Cl', state='тв')
S('H2NCH2COOCH3', 'метиловый эфир глицина', ES, 'эфиры аминокислот', 'COC(=O)CN', view='H2N-CH2-COO-CH3', state='ж')
S('H2NCH2COOC2H5', 'этиловый эфир глицина', ES, 'эфиры аминокислот', 'CCOC(=O)CN', view='H2N-CH2-COO-C2H5', state='ж')
S('CH3CH(NH2)COOCH3', 'метиловый эфир аланина', ES, 'эфиры аминокислот', 'COC(=O)C(C)N', view='CH3-CH(NH2)-COO-CH3',
  state='ж')
A = 'дипептиды'
S('H2NCH2CONHCH2COOH', 'глицилглицин', 'пептид', A, 'NCC(=O)NCC(=O)O', view='H2N-CH2-CO-NH-CH2-COOH', state='тв')
S('H2NCH2CONHCH(CH3)COOH', 'глицилаланин', 'пептид', A, 'NCC(=O)NC(C)C(=O)O', view='H2N-CH2-CO-NH-CH(CH3)-COOH',
  state='тв')
S('CH3CH(NH2)CONHCH2COOH', 'аланилглицин', 'пептид', A, 'CC(N)C(=O)NCC(=O)O', view='H2N-CH(CH3)-CO-NH-CH2-COOH',
  state='тв')
S('CH3CH(NH2)CONHCH(CH3)COOH', 'аланилаланин', 'пептид', A, 'CC(N)C(=O)NC(C)C(=O)O',
  view='H2N-CH(CH3)-CO-NH-CH(CH3)-COOH', state='тв')
S('CO(NH2)2', 'мочевина', 'амид', 'амиды', 'NC(N)=O', triv=['карбамид'], view='H2N-CO-NH2', state='тв',
  use=['азотное удобрение'])

# ---------------------------------------------------------------- углеводы
CB = 'углевод'
S('C6H12O6', 'глюкоза', CB, 'моносахариды', 'OCC(O)C(O)C(O)C(O)C=O', triv=['виноградный сахар'],
  view='HOCH2-(CHOH)4-CHO', state='тв', notes='альдогексоза')
S('HOCH2(CHOH)3COCH2OH', 'фруктоза', CB, 'моносахариды', 'OCC(O)C(O)C(O)C(=O)CO', triv=['фруктовый сахар'],
  view='HOCH2-(CHOH)3-CO-CH2OH', state='тв', notes='кетогексоза')
S('C5H10O5', 'рибоза', CB, 'моносахариды', 'OCC(O)C(O)C(O)C=O', view='HOCH2-(CHOH)3-CHO', state='тв', notes='альдопентоза')
S('C5H10O4', 'дезоксирибоза', CB, 'моносахариды', 'OCC(O)C(O)CC=O', view='HOCH2-(CHOH)2-CH2-CHO', state='тв')
S('C12H22O11', 'сахароза', CB, 'дисахариды', None, triv=['тростниковый сахар', 'свекловичный сахар'], view='C12H22O11',
  state='тв', notes='невосстанавливающий дисахарид: остатки α-глюкозы и β-фруктозы')
S('(C6H11O5)2O', 'мальтоза', CB, 'дисахариды', None, triv=['солодовый сахар'], view='C12H22O11', state='тв',
  notes='восстанавливающий дисахарид: два остатка α-глюкозы')
S('C6H10O5', 'крахмал', CB, 'полисахариды', None, view='(C6H10O5)n', state='тв', notes='формула — одного звена; α-глюкоза')
S('C6H7O2(OH)3', 'целлюлоза', CB, 'полисахариды', None, triv=['клетчатка'], view='[C6H7O2(OH)3]n', state='тв',
  notes='формула — одного звена; β-глюкоза')
S('C6H8(OH)6', 'сорбит', 'спирт', 'многоатомные спирты', 'OCC(O)C(O)C(O)C(O)CO', triv=['гександиол-1,2,3,4,5,6'],
  view='HOCH2-(CHOH)4-CH2OH', state='тв', use=['сахарозаменитель'])
S('C6H7O2(ONO2)3', 'тринитрат целлюлозы', 'сложный эфир (неорганической кислоты)', 'эфиры целлюлозы', None,
  triv=['пироксилин'], view='[C6H7O2(ONO2)3]n', state='тв', use=['бездымный порох'])
S('C6H7O2(OCOCH3)3', 'триацетат целлюлозы', ES, 'эфиры целлюлозы', None, view='[C6H7O2(OCOCH3)3]n', state='тв',
  use=['ацетатное волокно'])

# ---------------------------------------------------------------- прочие (карбиды, ацетилениды, нитрилы)
S('Ag2C2', 'ацетиленид серебра', 'ацетиленид', 'ацетилениды', '[Ag]C#C[Ag]', view='Ag-C#C-Ag', state='тв',
  color='серовато-белый', props=['взрывчат в сухом виде'])
S('CH3CCAg', 'пропинид серебра', 'ацетиленид', 'ацетилениды', 'CC#C[Ag]', view='CH3-C#C-Ag', state='тв', color='белый')
S('Cu2C2', 'ацетиленид меди(I)', 'ацетиленид', 'ацетилениды', '[Cu]C#C[Cu]', view='Cu-C#C-Cu', state='тв',
  color='красно-коричневый')
S('Na2C2', 'ацетиленид натрия', 'ацетиленид', 'ацетилениды', '[Na]C#C[Na]', view='Na-C#C-Na', state='тв')
S('CH3CCNa', 'пропинид натрия', 'ацетиленид', 'ацетилениды', 'CC#C[Na]', view='CH3-C#C-Na', state='тв')
S('CH2CHCN', 'пропеннитрил', 'нитрил', 'нитрилы', 'C=CC#N', triv=['акрилонитрил'], view='CH2=CH-C#N', state='ж',
  use=['мономер нитрона'])

# ---------------------------------------------------------------- неорганические реагенты
for _f, _n in [('H2', 'водород'), ('O2', 'кислород'), ('N2', 'азот'), ('Cl2', 'хлор'), ('Br2', 'бром'), ('I2', 'иод'),
               ('H2O', 'вода'), ('HCl', 'хлороводород'), ('HBr', 'бромоводород'), ('HI', 'иодоводород'),
               ('HNO3', 'азотная кислота'), ('H2SO4', 'серная кислота'), ('NaOH', 'гидроксид натрия'),
               ('KOH', 'гидроксид калия'), ('Na', 'натрий'), ('K', 'калий'), ('Mg', 'магний'), ('Zn', 'цинк'),
               ('Fe', 'железо'), ('Cu', 'медь'), ('Ag', 'серебро'), ('C', 'углерод'), ('CuO', 'оксид меди(II)'),
               ('Cu2O', 'оксид меди(I)'), ('Cu(OH)2', 'гидроксид меди(II)'), ('Ag2O', 'оксид серебра(I)'),
               ('Ag(NH3)2OH', 'гидроксид диамминсеребра(I)'), ('NH3', 'аммиак'), ('NH4Cl', 'хлорид аммония'),
               ('NaCl', 'хлорид натрия'), ('KCl', 'хлорид калия'), ('NaBr', 'бромид натрия'), ('KBr', 'бромид калия'),
               ('MgBr2', 'бромид магния'), ('MgCl2', 'хлорид магния'), ('ZnBr2', 'бромид цинка'),
               ('ZnCl2', 'хлорид цинка'), ('CO2', 'оксид углерода(IV)'), ('CO', 'оксид углерода(II)'),
               ('Na2CO3', 'карбонат натрия'), ('K2CO3', 'карбонат калия'), ('NaHCO3', 'гидрокарбонат натрия'),
               ('KHCO3', 'гидрокарбонат калия'), ('CaCO3', 'карбонат кальция'), ('CaC2', 'карбид кальция'),
               ('Ca(OH)2', 'гидроксид кальция'), ('Al4C3', 'карбид алюминия'), ('Al(OH)3', 'гидроксид алюминия'),
               ('KMnO4', 'перманганат калия'), ('MnO2', 'оксид марганца(IV)'), ('MnSO4', 'сульфат марганца(II)'),
               ('K2SO4', 'сульфат калия'), ('K2Cr2O7', 'дихромат калия'), ('Cr2(SO4)3', 'сульфат хрома(III)'),
               ('HCN', 'циановодород'), ('NaNH2', 'амид натрия'), ('FeCl2', 'хлорид железа(II)'),
               ('AgCl', 'хлорид серебра'), ('AgBr', 'бромид серебра'), ('(NH4)2CO3', 'карбонат аммония'),
               ('Na2SO4', 'сульфат натрия'), ('CaCl2', 'хлорид кальция'), ('CuCl', 'хлорид меди(I)'),
               ('CuCl2', 'хлорид меди(II)'), ('NH4NO3', 'нитрат аммония'), ('CaO', 'оксид кальция'),
               ('Cu(NH3)2Cl', 'хлорид диамминмеди(I)'), ('SO2', 'оксид серы(IV)'), ('NaNO2', 'нитрит натрия'),
               ('KNO3', 'нитрат калия'), ('AgNO3', 'нитрат серебра'), ('NH4Br', 'бромид аммония'),
               ('(NH4)2SO4', 'сульфат аммония'), ('NaHSO4', 'гидросульфат натрия')]:
    I(_f, _n)
