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
    return {'atoms': cnt, 'sigma': len(bonds) + nh, 'pi': pi, 'hyb': hyb, 'rings': rings,
            'graph': ([(a['el'], a['arom']) for a in atoms], bonds)}


# ================================================================= вещества

SUBSTANCES = []
SMILES = {}
_SRC = 'школьный курс органической химии; названия сверены с Wikidata (CC0), где найдено'


def _view(v):
    if not v:
        return v
    v = v.replace('#', '≡').replace('-', '–')
    return re.sub(r'\(([\d,]+|орто|мета|пара)–\)', r'(\1-)', v)


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
  triv=['терефталевая кислота'], view='HOOC-C6H4-COOH (1,4-)', state='тв')
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
S('KOOCC6H4COOK', 'терефталат калия', SA, A, '[K]OC(=O)c1ccc(cc1)C(=O)O[K]', view='KOOC-C6H4-COOK (1,4-)', state='тв')
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
S('(C6H5)2NH', 'дифениламин', AM, 'ароматические амины', 'N(c1ccccc1)c1ccccc1', view='(C6H5)2NH', state='тв')
S('(C6H5)3N', 'трифениламин', AM, 'ароматические амины', 'N(c1ccccc1)(c1ccccc1)c1ccccc1', view='(C6H5)3N', state='тв')
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
S('CH3CH2CH2NH3Cl', 'хлорид пропиламмония', 'соль амина', A, 'CCC[NH3]Cl', view='[CH3CH2CH2NH3]Cl', state='тв')
S('(CH3)2CHNH3Cl', 'хлорид изопропиламмония', 'соль амина', A, 'CC(C)[NH3]Cl', view='[(CH3)2CHNH3]Cl', state='тв')
S('CH3NH2C2H5Cl', 'хлорид метилэтиламмония', 'соль амина', A, 'C[NH2](CC)Cl', view='[CH3NH2C2H5]Cl', state='тв')
S('(C2H5)3NHCl', 'хлорид триэтиламмония', 'соль амина', A, 'CC[NH](CC)(CC)Cl', view='[(C2H5)3NH]Cl', state='тв')
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
S('H2NCH2COONa', 'глицинат натрия', 'соль аминокислоты', 'соли аминокислот', 'NCC(=O)O[Na]', view='H2N-CH2-COONa',
  state='тв')
S('H2NCH2CH2COONa', '3-аминопропаноат натрия', 'соль аминокислоты', 'соли аминокислот', 'NCCC(=O)O[Na]',
  view='H2N-CH2-CH2-COONa', state='тв')
S('H2NCH2COOK', 'глицинат калия', 'соль аминокислоты', 'соли аминокислот', 'NCC(=O)O[K]', view='H2N-CH2-COOK', state='тв')
S('CH3CH(NH2)COONa', 'аланинат натрия', 'соль аминокислоты', 'соли аминокислот', 'CC(N)C(=O)O[Na]',
  view='CH3-CH(NH2)-COONa', state='тв')
S('ClH3NCH2COOH', 'гидрохлорид глицина', 'соль аминокислоты', 'соли аминокислот', 'Cl[NH3]CC(=O)O',
  triv=['хлорид глициния'], view='[H3N-CH2-COOH]Cl', state='тв')
S('CH3CH(NH3Cl)COOH', 'гидрохлорид аланина', 'соль аминокислоты', 'соли аминокислот', 'CC([NH3]Cl)C(=O)O',
  triv=['хлорид аланиния'], view='[CH3-CH(NH3)-COOH]Cl', state='тв')
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
S('C6H8(OH)6', 'гексангексаол-1,2,3,4,5,6', 'спирт', 'многоатомные спирты', 'OCC(O)C(O)C(O)C(O)CO', triv=['сорбит'],
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

# дополнительные вещества, нужные реакциям
S('CH3CH2NO2', 'нитроэтан', NI, 'нитроалканы', 'CCN(=O)=O', view='CH3-CH2-NO2', state='ж')
S('CH3CH(NO2)CH2CH3', '2-нитробутан', NI, 'нитроалканы', 'CCC(C)N(=O)=O', view='CH3-CH(NO2)-CH2-CH3', state='ж')
S('C6H4(NO2)2', '1,3-динитробензол', NI, 'нитроарены', 'O=N(=O)c1cccc(c1)N(=O)=O', triv=['м-динитробензол'],
  view='C6H4(NO2)2 (1,3-)', state='тв')
S('BrC6H4NO2', '1-бром-3-нитробензол', NI, 'нитроарены', 'Brc1cccc(c1)N(=O)=O', triv=['м-бромнитробензол'],
  view='Br-C6H4-NO2 (мета-)', state='тв')
S('O2NC6H4COOH', '3-нитробензойная кислота', AC, 'ароматические карбоновые кислоты', 'OC(=O)c1cccc(c1)N(=O)=O',
  triv=['м-нитробензойная кислота'], view='O2N-C6H4-COOH (мета-)', state='тв')
S('BrC6H4COOH', '3-бромбензойная кислота', AC, 'ароматические карбоновые кислоты', 'OC(=O)c1cccc(Br)c1',
  triv=['м-бромбензойная кислота'], view='Br-C6H4-COOH (мета-)', state='тв')
S('C6H4(COOH)2', 'бензол-1,2-дикарбоновая кислота', AC, 'двухосновные карбоновые кислоты', 'OC(=O)c1ccccc1C(=O)O',
  triv=['фталевая кислота'], view='C6H4(COOH)2 (1,2-)', state='тв')
S('C6H5CHClCH3', '(1-хлорэтил)бензол', HL, 'галогенарены', 'CC(Cl)c1ccccc1', view='C6H5-CHCl-CH3', state='ж')
S('CHBr2CBr2CH3', '1,1,2,2-тетрабромпропан', HL, 'галогеналканы', 'CC(Br)(Br)C(Br)Br', view='CHBr2-CBr2-CH3', state='ж')
S('CH3CHCHCH2Br', '1-бромбутен-2', HL, 'галогеналкены', 'CC=CCBr', view='CH3-CH=CH-CH2Br', state='ж')
S('BrCH2CH2COOH', '3-бромпропановая кислота', AC, 'галогенкарбоновые кислоты', 'OC(=O)CCBr', view='BrCH2-CH2-COOH',
  state='тв')
S('CH2BrCHBrCOOH', '2,3-дибромпропановая кислота', AC, 'галогенкарбоновые кислоты', 'OC(=O)C(Br)CBr',
  view='CH2Br-CHBr-COOH', state='тв')
S('C17H33Br2COOH', '9,10-дибромоктадекановая кислота', AC, 'галогенкарбоновые кислоты', 'CCCCCCCCC(Br)C(Br)CCCCCCCC(=O)O',
  view='C17H33Br2-COOH', state='тв')
S('CH2ClCH(OH)CH2OH', '3-хлорпропандиол-1,2', HL, 'галогенспирты', 'OCC(O)CCl', view='CH2Cl-CH(OH)-CH2-OH', state='ж')
S('CH3CH(OH)(CH2)2CH3', 'пентанол-2', AL, 'предельные одноатомные спирты', 'CCCC(C)O', view='CH3-CH(OH)-CH2-CH2-CH3',
  state='ж')
S('(C2H5)2CHOH', 'пентанол-3', AL, 'предельные одноатомные спирты', 'CCC(O)CC', view='CH3-CH2-CH(OH)-CH2-CH3', state='ж')
S('(CH3CO)2O', 'уксусный ангидрид', 'ангидрид карбоновой кислоты', 'ангидриды', 'CC(=O)OC(C)=O', view='(CH3CO)2O', state='ж')
S('C6H5CH2ONa', 'бензилат натрия', 'алкоголят', 'алкоголяты', '[Na]OCc1ccccc1', view='C6H5-CH2-ONa', state='тв')
for _f, _n in [('AlCl3', 'хлорид алюминия'), ('K2MnO4', 'манганат калия'), ('KHSO4', 'гидросульфат калия'),
               ('FeCl3', 'хлорид железа(III)'), ('ZnO', 'оксид цинка'), ('Ca(HCO3)2', 'гидрокарбонат кальция'),
               ('MgO', 'оксид магния'), ('Ba(OH)2', 'гидроксид бария')]:
    I(_f, _n)

# ================================================================= идентификаторы Wikidata (CC0) и PubChem CID
# Найдены SPARQL-запросом по русской метке и сверены по брутто-формуле (P274); CID — свойство P662 того же элемента.
WD = {
    '(C6H11O5)2O': ('Q170002', 439186),
    '(C6H5)2NH': ('Q412265', 11487),
    '(CH2)3': ('Q80250', 6351),
    '(CH2)4': ('Q80232', 9250),
    '(CH2)5': ('Q80260', 9253),
    '(CH2)6': ('Q211433', 8078),
    '(CH3)2CH(CH2)2CH(CH3)2': ('Q2813798', 11592),
    '(CH3)2CHCH2CH2OH': ('Q223101', 31260),
    '(CH3)2NH': ('Q408022', 674),
    '(CH3)3CCH2CH(CH3)2': ('Q209130', 10907),
    '(CH3)3COH': ('Q285790', 6386),
    '(CH3)3N': ('Q423953', 1146),
    '(CH3COO)2Ca': ('Q409251', 6116),
    '(CH3COO)2Cu': ('Q421854', 8895),
    'C12H22O11': ('Q4027534', 5988),
    'C15H31COOH': ('Q209727', 985),
    'C17H31COOH': ('Q407426', 5280450),
    'C17H33COOH': ('Q207688', 445639),
    'C17H35COOH': ('Q209685', 5281),
    'C17H35COOK': ('Q15629420', 23673840),
    'C2H2': ('Q133145', 6326),
    'C2H5Br': ('Q412245', 6332),
    'C2H5Cl': ('Q409133', 6337),
    'C2H5OC2H5': ('Q202218', 3283),
    'C2H5OH': ('Q153', 702),
    'C2H6': ('Q52858', 6324),
    'C3H4(OH)(COOH)3': ('Q159683', 311),
    'C3H8': ('Q131189', 6334),
    'C5H10O4': ('Q192454', 439576),
    'C5H10O5': ('Q179271', 5779),
    'C5H11O5COOH': ('Q407569', 10690),
    'C6H10O': ('Q409178', 7967),
    'C6H11OH': ('Q423282', 7966),
    'C6H12O6': ('Q37525', None),
    'C6H2Br3NH2': ('Q4029749', 8986),
    'C6H3(CH3)3': ('Q425161', 7947),
    'C6H4(NO2)2': ('Q2653558', 7452),
    'C6H4(OH)2': ('Q282440', 289),
    'C6H5Br': ('Q410597', 7961),
    'C6H5CH(CH3)2': ('Q410107', 7406),
    'C6H5CH2CH2CH3': ('Q288806', 7668),
    'C6H5CH2Cl': ('Q412260', 7503),
    'C6H5CH2OH': ('Q52353', 244),
    'C6H5CH3': ('Q15779', 1140),
    'C6H5CHCH2': ('Q28917', 7501),
    'C6H5COCH3': ('Q375112', 7410),
    'C6H5COOH': ('Q191700', 243),
    'C6H5COOK': ('Q413611', 23661960),
    'C6H5COONa': ('Q423971', 517055),
    'C6H5NH2': ('Q186414', 6115),
    'C6H6': ('Q2270', 241),
    'C6H8(OH)6': ('Q245280', 5780),
    'CCl4': ('Q225045', 5943),
    'CF2CF2': ('Q412460', 8301),
    'CH2BrCH2Br': ('Q161471', 7839),
    'CH2C(CH3)2': ('Q776976', 8255),
    'CH2C(CH3)CHCH2': ('Q271943', 6557),
    'CH2C(CH3)COOH': ('Q165949', 4093),
    'CH2CCH2': ('Q422942', 10037),
    'CH2CClCHCH2': ('Q410871', 31369),
    'CH2CHCH2Cl': ('Q420473', 7850),
    'CH2CHCH2OH': ('Q414553', 7858),
    'CH2CHCH3': ('Q151324', 8252),
    'CH2CHCHO': ('Q342790', 7847),
    'CH2CHCN': ('Q342968', 7855),
    'CH2CHCOOCH3': ('Q343028', 7294),
    'CH2CHCOOH': ('Q324628', 6581),
    'CH2Cl2': ('Q421748', 6344),
    'CH2ClCH2Cl': ('Q161480', 11),
    'CH3(CH2)2CHO': ('Q410603', 261),
    'CH3(CH2)2COOH': ('Q193213', 264),
    'CH3(CH2)3Br': ('Q59081', 8002),
    'CH3(CH2)3CH3': ('Q150429', 8003),
    'CH3(CH2)3CHO': ('Q420652', 8063),
    'CH3(CH2)3OH': ('Q16391', 263),
    'CH3(CH2)6CH3': ('Q150681', 356),
    'CH3(CH2)8CH3': ('Q150717', 15600),
    'CH3CH(CH3)CH(CH3)CH3': ('Q209178', 6589),
    'CH3CH(CH3)CH2CH3': ('Q422703', 6556),
    'CH3CH(CH3)CH3': ('Q407225', 6360),
    'CH3CH(NH2)COOH': ('Q218642', 5950),
    'CH3CH(OH)CH(OH)CH3': ('Q209157', 262),
    'CH3CH(OH)CH2CH3': ('Q209332', 6568),
    'CH3CH(OH)CH2OH': ('Q161495', 1030),
    'CH3CH(OH)CH3': ('Q16392', 3776),
    'CH3CH(OH)COONa': ('Q418235', 23666456),
    'CH3CH2CH(CH3)CH2CH3': ('Q223107', 7282),
    'CH3CH2CH(OH)CH2OH': ('Q161457', 11429),
    'CH3CH2CH2Br': ('Q161589', 7840),
    'CH3CH2CH2CH3': ('Q134192', 7843),
    'CH3CH2CH2OH': ('Q14985', 1031),
    'CH3CH2CHO': ('Q422909', 527),
    'CH3CH2COOH': ('Q422956', 1032),
    'CH3CHCl2': ('Q161282', 6365),
    'CH3CHClCH2CH3': ('Q209347', 6563),
    'CH3CHClCH3': ('Q209360', 6361),
    'CH3CHO': ('Q61457', 177),
    'CH3COCH3': ('Q49546', 180),
    'CH3COOC6H4COOH': ('Q18216', 2244),
    'CH3COOK': ('Q409199', 517044),
    'CH3COONH4': ('Q410156', 12432),
    'CH3COONa': ('Q339940', 517045),
    'CH3Cl': ('Q422709', 6327),
    'CH3I': ('Q421729', 6328),
    'CH3NH2': ('Q409304', 6329),
    'CH3OCH3': ('Q408050', 8254),
    'CH3OH': ('Q14982', 887),
    'CH4': ('Q37129', 297),
    'CHCCH3': ('Q151446', 6335),
    'CHCl3': ('Q172275', 6212),
    'H2NCH2COOH': ('Q620730', 750),
    'HOOCCOOH': ('Q184832', 971),
    'KOOCCOOK': ('Q767561', 11413),
    'O2NC6H4COOH': ('Q4634183', 8497),
}
for _s in SUBSTANCES:
    if _s['f'] in WD:
        _q, _cid = WD[_s['f']]
        _s['wd'] = _q
        if _cid:
            _s['pubchem'] = _cid
        _s['src'] = _s['src'] + f'; Wikidata {_q}'

# ================================================================= реакции
REACTIONS = []
FACTS = []
_RSRC = 'школьный факт (органическая химия 10–11 кл.)'


def R(lhs, rhs, typ, cond='', rk=None, tags=(), sign='', **kw):
    """lhs[0] — органический субстрат, rhs[0] — главный органический продукт; rk — ключ реагента (см. RK)."""
    if rk is None:
        rk = lhs[1] if len(lhs) > 1 else ''
    row = dict(lhs=list(lhs), rhs=list(rhs), type=list(typ), cond=cond, rk=rk, tags=list(tags), sign=sign, src=_RSRC)
    row.update(kw)
    REACTIONS.append(row)
    return row


def F(lhs, prod, typ, cond='', rk=None, sign='', **kw):
    """Факт без уравнения: prod — список продуктов (формулы из базы или текст)."""
    if rk is None:
        rk = lhs[1] if len(lhs) > 1 else ''
    row = dict(lhs=list(lhs), prod=list(prod), type=list(typ), cond=cond, rk=rk, sign=sign, src=_RSRC)
    row.update(kw)
    FACTS.append(row)
    return row


# Ключи реагентов (rk) → как реагент называют в заданиях
RK = {
    'O2': 'кислород', 'H2': 'водород', 'Br2aq': 'бромная вода', 'Br2hv': 'бром (на свету)', 'Br2Fe': 'бром (FeBr₃)',
    'Br2': 'бром', 'Cl2hv': 'хлор (на свету)', 'Cl2Fe': 'хлор (FeCl₃)', 'Cl2': 'хлор', 'HCl': 'хлороводород',
    'HBr': 'бромоводород', 'H2O': 'вода', 'KMnO4': 'перманганат калия', 'Na': 'натрий', 'K': 'калий',
    'NaOH': 'гидроксид натрия (р-р)', 'KOH': 'гидроксид калия (р-р)', 'KOHalc': 'гидроксид калия (спирт. р-р)',
    'NaOHalc': 'гидроксид натрия (спирт. р-р)', 'NaHCO3': 'гидрокарбонат натрия', 'Na2CO3': 'карбонат натрия',
    'Cu(OH)2': 'гидроксид меди(II)', 'AgNH3': 'аммиачный раствор оксида серебра', 'HNO3': 'азотная кислота',
    'CuO': 'оксид меди(II)', 'Zn': 'цинк', 'Mg': 'магний', 'NH3': 'аммиак', 'H2SO4': 'серная кислота',
    'K2Cr2O7': 'дихромат калия', 'CH3OH': 'метанол', 'C2H5OH': 'этанол', 'CH3COOH': 'уксусная кислота',
}

# ---------------------------------------------------------------- алканы
for a, cl, br in [('CH4', 'CH3Cl', 'CH3Br'), ('C2H6', 'C2H5Cl', 'C2H5Br'), ('C3H8', 'CH3CHClCH3', 'CH3CHBrCH3'),
                  ('CH3CH2CH2CH3', 'CH3CHClCH2CH3', 'CH3CHBrCH2CH3'), ('CH3CH(CH3)CH3', None, '(CH3)3CBr'),
                  ('CH3CH(CH3)CH2CH3', None, '(CH3)2CBrCH2CH3'), ('(CH2)6', 'C6H11Cl', None)]:
    if cl:
        R([a, 'Cl2'], [cl, 'HCl'], ['замещения', 'галогенирования', 'радикальная'], 'hv', rk='Cl2hv',
          tags=['свободнорадикальный механизм'])
    if br:
        R([a, 'Br2'], [br, 'HBr'], ['замещения', 'галогенирования', 'радикальная'], 'hv', rk='Br2hv',
          tags=['свободнорадикальный механизм', 'замещение у наименее гидрогенизированного атома C'])
R(['CH3Cl', 'Cl2'], ['CH2Cl2', 'HCl'], ['замещения', 'галогенирования'], 'hv', rk='Cl2hv')
R(['CH2Cl2', 'Cl2'], ['CHCl3', 'HCl'], ['замещения', 'галогенирования'], 'hv', rk='Cl2hv')
R(['CHCl3', 'Cl2'], ['CCl4', 'HCl'], ['замещения', 'галогенирования'], 'hv', rk='Cl2hv')
R(['CH4', 'Cl2'], ['CCl4', 'HCl'], ['замещения', 'галогенирования'], 'hv, избыток хлора', rk='Cl2hv')
for a, p in [('CH4', 'CH3NO2'), ('C2H6', 'CH3CH2NO2'), ('C3H8', 'CH3CH(NO2)CH3'), ('CH3CH2CH2CH3', 'CH3CH(NO2)CH2CH3')]:
    R([a, 'HNO3'], [p, 'H2O'], ['замещения', 'нитрования'], 'HNO3 (разб.), t', tags=['реакция Коновалова'])
R(['CH3CH2CH2CH3'], ['CH3CH(CH3)CH3'], ['изомеризации'], 'AlCl3, t', rk='AlCl3')
R(['CH3(CH2)3CH3'], ['CH3CH(CH3)CH2CH3'], ['изомеризации'], 'AlCl3, t', rk='AlCl3')
R(['CH3(CH2)4CH3'], ['CH3CH(CH3)(CH2)2CH3'], ['изомеризации'], 'AlCl3, t', rk='AlCl3')
for a, p in [('C2H6', 'C2H4'), ('C3H8', 'CH2CHCH3'), ('CH3CH(CH3)CH3', 'CH2C(CH3)2'), ('C6H5C2H5', 'C6H5CHCH2')]:
    R([a], [p, 'H2'], ['отщепления', 'дегидрирования'], 'Cr2O3 (Ni), t', rk='')
R(['CH3CH2CH2CH3'], ['CH2CHCHCH2', 'H2'], ['отщепления', 'дегидрирования'], 'Cr2O3, Al2O3, t', rk='')
R(['CH3CH(CH3)CH2CH3'], ['CH2C(CH3)CHCH2', 'H2'], ['отщепления', 'дегидрирования'], 'Cr2O3, Al2O3, t', rk='')
R(['CH3(CH2)4CH3'], ['C6H6', 'H2'], ['отщепления', 'дегидрирования', 'ароматизации'], 'Pt, t', rk='',
  tags=['дегидроциклизация'])
R(['CH3(CH2)5CH3'], ['C6H5CH3', 'H2'], ['отщепления', 'дегидрирования', 'ароматизации'], 'Pt, t', rk='',
  tags=['дегидроциклизация'])
R(['CH3(CH2)4CH3'], ['(CH2)6', 'H2'], ['отщепления', 'дегидрирования'], 'Pt, t', rk='', tags=['дегидроциклизация'])
R(['(CH2)6'], ['C6H6', 'H2'], ['отщепления', 'дегидрирования'], 'Pt, t', rk='')
R(['C6H11CH3'], ['C6H5CH3', 'H2'], ['отщепления', 'дегидрирования'], 'Pt, t', rk='')
R(['CH4'], ['C2H2', 'H2'], ['разложения', 'дегидрирования'], '1500 °C', rk='', tags=['пиролиз метана'])
R(['CH4'], ['C', 'H2'], ['разложения'], '1000 °C', rk='')
R(['CH4', 'H2O'], ['CO', 'H2'], ['ОВР'], 'Ni, t', rk='H2Ocat', tags=['конверсия метана (синтез-газ)'])
R(['CH4', 'O2'], ['HCHO', 'H2O'], ['окисления', 'каталитическое окисление'], 'кат., t', rk='O2cat')
for a, p1, p2 in [('CH3(CH2)6CH3', 'CH3CH2CH2CH3', 'CH2CHCH2CH3'), ('CH3(CH2)8CH3', 'CH3(CH2)3CH3', 'CH2CH(CH2)2CH3'),
                  ('CH3(CH2)4CH3', 'C3H8', 'CH2CHCH3'), ('CH3CH2CH2CH3', 'C2H6', 'C2H4'),
                  ('CH3CH2CH2CH3', 'CH4', 'CH2CHCH3'), ('C3H8', 'CH4', 'C2H4'), ('CH3(CH2)5CH3', 'CH3CH2CH2CH3', 'CH2CHCH3'),
                  ('CH3(CH2)3CH3', 'C2H6', 'CH2CHCH3'), ('CH3(CH2)3CH3', 'C3H8', 'C2H4')]:
    R([a], [p1, p2], ['разложения', 'крекинга'], 't', rk='', tags=['крекинг'])
# Вюрц
for x, p, na in [('CH3Cl', 'C2H6', 'NaCl'), ('CH3Br', 'C2H6', 'NaBr'), ('C2H5Cl', 'CH3CH2CH2CH3', 'NaCl'),
                 ('C2H5Br', 'CH3CH2CH2CH3', 'NaBr'), ('CH3CH2CH2Br', 'CH3(CH2)4CH3', 'NaBr'),
                 ('CH3CH2CH2Cl', 'CH3(CH2)4CH3', 'NaCl'), ('CH3CHBrCH3', 'CH3CH(CH3)CH(CH3)CH3', 'NaBr'),
                 ('CH3CHClCH3', 'CH3CH(CH3)CH(CH3)CH3', 'NaCl'), ('(CH3)2CHCH2Br', '(CH3)2CH(CH2)2CH(CH3)2', 'NaBr'),
                 ('CH3(CH2)3Br', 'CH3(CH2)6CH3', 'NaBr')]:
    R([x, 'Na'], [p, na], ['замещения', 'реакция Вюрца'], 't', tags=['реакция Вюрца'])
R(['CH3Cl', 'C2H5Cl', 'Na'], ['C3H8', 'NaCl'], ['замещения', 'реакция Вюрца'], 't', rk='Na', tags=['реакция Вюрца'])
R(['CH3Br', 'C2H5Br', 'Na'], ['C3H8', 'NaBr'], ['замещения', 'реакция Вюрца'], 't', rk='Na', tags=['реакция Вюрца'])
R(['C2H5Br', 'CH3CHBrCH3', 'Na'], ['CH3CH(CH3)CH2CH3', 'NaBr'], ['замещения', 'реакция Вюрца'], 't', rk='Na',
  tags=['реакция Вюрца'])
R(['C6H5Br', 'CH3Br', 'Na'], ['C6H5CH3', 'NaBr'], ['замещения', 'реакция Вюрца'], 't', rk='Na', tags=['реакция Вюрца–Фиттига'])
# Дюма (декарбоксилирование солей), карбид алюминия, синтезы из CO
for s_, al, p, c in [('CH3COONa', 'NaOH', 'CH4', 'Na2CO3'), ('CH3COOK', 'KOH', 'CH4', 'K2CO3'),
                     ('CH3CH2COONa', 'NaOH', 'C2H6', 'Na2CO3'), ('CH3(CH2)2COONa', 'NaOH', 'C3H8', 'Na2CO3'),
                     ('(CH3)2CHCOONa', 'NaOH', 'C3H8', 'Na2CO3'), ('C6H5COONa', 'NaOH', 'C6H6', 'Na2CO3'),
                     ('C6H5COOK', 'KOH', 'C6H6', 'K2CO3'), ('CH3CH2COOK', 'KOH', 'C2H6', 'K2CO3')]:
    R([s_, al], [p, c], ['декарбоксилирования', 'разложения'], 'сплавление, t', rk=al + 'fus',
      tags=['реакция Дюма (сплавление со щёлочью)'])
R(['KOOCCOOK', 'KOH'], ['H2', 'K2CO3'], ['декарбоксилирования'], 'сплавление, t', rk='KOHfus')
R(['Al4C3', 'H2O'], ['CH4', 'Al(OH)3'], ['гидролиза'], '', rk='H2O')
R(['Al4C3', 'HCl'], ['CH4', 'AlCl3'], ['обмена'], '', rk='HCl')
R(['CaC2', 'H2O'], ['C2H2', 'Ca(OH)2'], ['гидролиза'], '', rk='H2O')
R(['CaC2', 'HCl'], ['C2H2', 'CaCl2'], ['обмена'], '', rk='HCl')
R(['C', 'H2'], ['CH4'], ['соединения'], 'Ni, t', rk='H2')
R(['CO', 'H2'], ['CH3OH'], ['соединения', 'ОВР'], 'ZnO, Cr2O3 (Cu), t, p', rk='H2', tags=['промышленный синтез метанола'])
R(['CaO', 'C'], ['CaC2', 'CO'], ['ОВР'], '2000 °C (электропечь)', rk='C')

# ---------------------------------------------------------------- циклоалканы
R(['(CH2)3', 'H2'], ['C3H8'], ['присоединения', 'гидрирования'], 'Ni, t', tags=['раскрытие малого цикла'])
R(['(CH2)4', 'H2'], ['CH3CH2CH2CH3'], ['присоединения', 'гидрирования'], 'Ni, t', tags=['раскрытие малого цикла'])
R(['C3H5CH3', 'H2'], ['CH3CH(CH3)CH3'], ['присоединения', 'гидрирования'], 'Ni, t', tags=['раскрытие малого цикла'])
R(['(CH2)3', 'Br2'], ['CH2BrCH2CH2Br'], ['присоединения', 'галогенирования'], '', rk='Br2', tags=['раскрытие малого цикла'])
R(['(CH2)3', 'HBr'], ['CH3CH2CH2Br'], ['присоединения', 'гидрогалогенирования'], '', tags=['раскрытие малого цикла'])
for dh, c, z in [('CH2BrCH2CH2Br', '(CH2)3', 'Zn'), ('CH2BrCH2CH2Br', '(CH2)3', 'Mg'), ('CH2Br(CH2)2CH2Br', '(CH2)4', 'Zn'),
                 ('CH2Br(CH2)2CH2Br', '(CH2)4', 'Mg')]:
    R([dh, z], [c, z + 'Br2'], ['отщепления', 'дегалогенирования'], 't', tags=['внутримолекулярная реакция Вюрца'])

# ---------------------------------------------------------------- алкены
ALK = [  # алкен, H2→, Br2→, HBr→, HCl→, H2O→, KMnO4(H2O)→ диол, Cl2 →
    ('C2H4', 'C2H6', 'CH2BrCH2Br', 'C2H5Br', 'C2H5Cl', 'C2H5OH', 'C2H4(OH)2', 'CH2ClCH2Cl'),
    ('CH2CHCH3', 'C3H8', 'CH2BrCHBrCH3', 'CH3CHBrCH3', 'CH3CHClCH3', 'CH3CH(OH)CH3', 'CH3CH(OH)CH2OH', 'CH2ClCHClCH3'),
    ('CH2CHCH2CH3', 'CH3CH2CH2CH3', 'CH2BrCHBrCH2CH3', 'CH3CHBrCH2CH3', 'CH3CHClCH2CH3', 'CH3CH(OH)CH2CH3',
     'CH3CH2CH(OH)CH2OH', None),
    ('CH3CHCHCH3', 'CH3CH2CH2CH3', 'CH3CHBrCHBrCH3', 'CH3CHBrCH2CH3', 'CH3CHClCH2CH3', 'CH3CH(OH)CH2CH3',
     'CH3CH(OH)CH(OH)CH3', None),
    ('CH2C(CH3)2', 'CH3CH(CH3)CH3', '(CH3)2CBrCH2Br', '(CH3)3CBr', '(CH3)3CCl', '(CH3)3COH', '(CH3)2C(OH)CH2OH', None),
    ('CH2CH(CH2)2CH3', 'CH3(CH2)3CH3', None, None, None, 'CH3CH(OH)(CH2)2CH3', None, None),
    ('CH3CHCHCH2CH3', 'CH3(CH2)3CH3', None, None, None, None, None, None),
    ('CH2C(CH3)CH2CH3', 'CH3CH(CH3)CH2CH3', None, '(CH3)2CBrCH2CH3', '(CH3)2CClCH2CH3', '(CH3)2C(OH)CH2CH3', None, None),
    ('(CH3)2CCHCH3', 'CH3CH(CH3)CH2CH3', None, '(CH3)2CBrCH2CH3', '(CH3)2CClCH2CH3', '(CH3)2C(OH)CH2CH3', None, None),
    ('CH2CHCH(CH3)2', 'CH3CH(CH3)CH2CH3', None, None, None, None, None, None),  # гидратация — с перегруппировкой, не берём
    ('CH2CH(CH2)3CH3', 'CH3(CH2)4CH3', None, None, None, None, None, None),
    ('(CH3)2CC(CH3)2', 'CH3CH(CH3)CH(CH3)CH3', None, None, None, None, None, None),
    ('C6H10', '(CH2)6', 'C6H10Br2', None, 'C6H11Cl', 'C6H11OH', 'C6H10(OH)2', None),
    ('C5H8', '(CH2)5', None, None, None, None, None, None),
    ('C6H5CHCH2', 'C6H5C2H5', 'C6H5CHBrCH2Br', 'C6H5CHBrCH3', 'C6H5CHClCH3', 'C6H5CH(OH)CH3', 'C6H5CH(OH)CH2OH', None),
]
for a, h2, br2, hbr, hcl, h2o, diol, cl2 in ALK:
    if h2:
        R([a, 'H2'], [h2], ['присоединения', 'гидрирования', 'восстановления'], 'Ni, t')
    if br2:
        R([a, 'Br2'], [br2], ['присоединения', 'галогенирования'], 'бромная вода', rk='Br2aq',
          sign='обесцвечивание бромной воды')
    if cl2:
        R([a, 'Cl2'], [cl2], ['присоединения', 'галогенирования'], '', rk='Cl2')
    if hbr:
        R([a, 'HBr'], [hbr, ], ['присоединения', 'гидрогалогенирования'], '', tags=['правило Марковникова'])
    if hcl:
        R([a, 'HCl'], [hcl], ['присоединения', 'гидрогалогенирования'], '', tags=['правило Марковникова'])
    if h2o:
        R([a, 'H2O'], [h2o], ['присоединения', 'гидратации'], 'H+ (H3PO4), t', tags=['правило Марковникова'])
    if diol:
        R([a, 'KMnO4', 'H2O'], [diol, 'MnO2', 'KOH'], ['окисления', 'ОВР'], 'водн. р-р, 0–20 °C', rk='KMnO4',
          tags=['реакция Вагнера'], sign='обесцвечивание раствора KMnO4, бурый осадок MnO2', medium='нейтр.')
R(['CH2CHCH3', 'Cl2'], ['CH2CHCH2Cl', 'HCl'], ['замещения', 'галогенирования'], '500 °C', rk='Cl2t',
  tags=['замещение в аллильное положение'])
R(['C2H4', 'O2'], ['CH3CHO'], ['окисления'], 'PdCl2, CuCl2, t', rk='O2cat', tags=['вакер-процесс'])
R(['CH2CHCl', 'HCl'], ['CH3CHCl2'], ['присоединения', 'гидрогалогенирования'], '', tags=['правило Марковникова'])
R(['CH2CHCH2Cl', 'NaOH'], ['CH2CHCH2OH', 'NaCl'], ['замещения', 'гидролиза'], 'водн. р-р, t')
# жёсткое окисление, когда продукт один
for a, p, n in [('C2H4', 'CO2', 1), ('CH3CHCHCH3', 'CH3COOH', 1), ('(CH3)2CC(CH3)2', 'CH3COCH3', 1),
                ('C6H10', 'HOOC(CH2)4COOH', 1), ('CH3CCCH3', 'CH3COOH', 1), ('C2H2', 'CO2', 1),
                ('CH3CH2CH(OH)CH2OH', None, 0)]:
    if p:
        R([a, 'KMnO4', 'H2SO4'], [p, 'MnSO4', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4, t', rk='KMnO4',
          medium='кисл.', sign='обесцвечивание раствора KMnO4')
R(['C2H2', 'KMnO4'], ['KOOCCOOK', 'MnO2', 'KOH', 'H2O'], ['окисления', 'ОВР'], 'водн. р-р', rk='KMnO4', medium='нейтр.')
for a, prods in [('CH2CHCH3', ['CH3COOH', 'CO2']), ('CH2CHCH2CH3', ['CH3CH2COOH', 'CO2']),
                 ('CH2C(CH3)2', ['CH3COCH3', 'CO2']), ('(CH3)2CCHCH3', ['CH3COCH3', 'CH3COOH']),
                 ('CH2C(CH3)CH2CH3', ['CH3COCH2CH3', 'CO2']), ('CH3CHCHCH2CH3', ['CH3COOH', 'CH3CH2COOH']),
                 ('CH2CH(CH2)2CH3', ['CH3(CH2)2COOH', 'CO2']), ('C6H5CHCH2', ['C6H5COOH', 'CO2']),
                 ('CHCCH3', ['CH3COOH', 'CO2']), ('CHCCH2CH3', ['CH3CH2COOH', 'CO2']),
                 ('C6H5C2H5', ['C6H5COOH', 'CO2']), ('C6H5CH(CH3)2', ['C6H5COOH', 'CO2']),
                 ('C6H5CH2CH2CH3', ['C6H5COOH', 'CH3COOH']), ('CH2CHCHCH2', ['CO2', 'HOOCCOOH'])]:
    F([a, 'KMnO4', 'H2SO4'], prods + ['MnSO4', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4, t', rk='KMnO4',
      medium='кисл.', why='два продукта окисления — коэффициенты не определяются балансом атомов однозначно')
for a, prods in [('C6H5C2H5', ['C6H5COOK', 'K2CO3']), ('C6H5CHCH2', ['C6H5COOK', 'K2CO3']),
                 ('CH2CHCH3', ['CH3COOK', 'K2CO3'])]:
    F([a, 'KMnO4'], prods + ['MnO2', 'KOH', 'H2O'], ['окисления', 'ОВР'], 'водн. р-р, t', rk='KMnO4', medium='нейтр.',
      why='два продукта окисления')

# ---------------------------------------------------------------- алкадиены
R(['CH2CHCHCH2', 'H2'], ['CH3CH2CH2CH3'], ['присоединения', 'гидрирования'], 'Ni, t, избыток H2', rk='H2')
R(['CH2CHCHCH2', 'H2'], ['CH3CHCHCH3'], ['присоединения', 'гидрирования'], 'Ni, t (1 моль H2)', rk='H2',
  tags=['1,4-присоединение'])
R(['CH2CHCHCH2', 'Br2'], ['CH2BrCHCHCH2Br'], ['присоединения', 'галогенирования'], '1 моль Br2', rk='Br2aq',
  tags=['1,4-присоединение'], sign='обесцвечивание бромной воды')
R(['CH2CHCHCH2', 'Br2'], ['CH2BrCHBrCHBrCH2Br'], ['присоединения', 'галогенирования'], 'избыток Br2', rk='Br2aq',
  sign='обесцвечивание бромной воды')
R(['CH2CHCHCH2', 'HBr'], ['CH3CHCHCH2Br'], ['присоединения', 'гидрогалогенирования'], '1 моль HBr',
  tags=['1,4-присоединение'])
R(['CH2C(CH3)CHCH2', 'H2'], ['CH3CH(CH3)CH2CH3'], ['присоединения', 'гидрирования'], 'Ni, t, избыток H2')
R(['CH2C(CH3)CHCH2', 'Br2'], ['CH2BrCBr(CH3)CHBrCH2Br'], ['присоединения', 'галогенирования'], 'избыток Br2',
  rk='Br2aq', sign='обесцвечивание бромной воды')
R(['CH2CCH2', 'H2'], ['C3H8'], ['присоединения', 'гидрирования'], 'Ni, t, избыток H2')
R(['CH2CHCHCHCH3', 'H2'], ['CH3(CH2)3CH3'], ['присоединения', 'гидрирования'], 'Ni, t, избыток H2')
R(['CH2CHCH2CHCH2', 'H2'], ['CH3(CH2)3CH3'], ['присоединения', 'гидрирования'], 'Ni, t, избыток H2')
R(['CH2C(CH3)C(CH3)CH2', 'H2'], ['CH3CH(CH3)CH(CH3)CH3'], ['присоединения', 'гидрирования'], 'Ni, t, избыток H2')
R(['CH2CCHCH3', 'H2'], ['CH3CH2CH2CH3'], ['присоединения', 'гидрирования'], 'Ni, t, избыток H2')
R(['C5H6', 'H2'], ['(CH2)5'], ['присоединения', 'гидрирования'], 'Ni, t, избыток H2')
R(['C2H5OH'], ['CH2CHCHCH2', 'H2O', 'H2'], ['отщепления', 'дегидратации', 'дегидрирования'], 'ZnO, Al2O3, 425 °C', rk='',
  tags=['способ Лебедева'])
R(['CH2CHCCH', 'HCl'], ['CH2CClCHCH2'], ['присоединения', 'гидрогалогенирования'], '', tags=['правило Марковникова'])
R(['C2H2'], ['CH2CHCCH'], ['присоединения', 'димеризации'], 'CuCl, NH4Cl', rk='', tags=['димеризация ацетилена'])

# ---------------------------------------------------------------- алкины
R(['C2H2', 'H2'], ['C2H4'], ['присоединения', 'гидрирования'], 'Pd (Pb2+), t', tags=['частичное гидрирование'])
R(['C2H2', 'H2'], ['C2H6'], ['присоединения', 'гидрирования'], 'Ni, t, избыток H2')
R(['C2H2', 'Br2'], ['CHBrCHBr'], ['присоединения', 'галогенирования'], '1 моль Br2', rk='Br2aq',
  sign='обесцвечивание бромной воды')
R(['C2H2', 'Br2'], ['CHBr2CHBr2'], ['присоединения', 'галогенирования'], 'избыток Br2', rk='Br2aq',
  sign='обесцвечивание бромной воды')
R(['C2H2', 'HCl'], ['CH2CHCl'], ['присоединения', 'гидрогалогенирования'], 'HgCl2, t')
R(['C2H2', 'HCl'], ['CH3CHCl2'], ['присоединения', 'гидрогалогенирования'], 'избыток HCl', tags=['правило Марковникова'])
R(['C2H2', 'HBr'], ['CH3CHBr2'], ['присоединения', 'гидрогалогенирования'], 'избыток HBr', tags=['правило Марковникова'])
R(['C2H2', 'H2O'], ['CH3CHO'], ['присоединения', 'гидратации'], 'Hg2+, H+', tags=['реакция Кучерова'])
R(['C2H2', 'HCN'], ['CH2CHCN'], ['присоединения'], 'кат.')
R(['C2H2', 'CH3COOH'], ['CH3COOCHCH2'], ['присоединения'], 'ацетат цинка, t')
R(['C2H2'], ['C6H6'], ['присоединения', 'тримеризации'], 'C (акт.), 600 °C', rk='', tags=['реакция Зелинского'])
R(['CHCCH3'], ['C6H3(CH3)3'], ['присоединения', 'тримеризации'], 'C (акт.), t', rk='')
R(['C2H2', 'Ag(NH3)2OH'], ['Ag2C2', 'NH3', 'H2O'], ['замещения'], 'аммиачный р-р', rk='AgNH3',
  sign='серовато-белый осадок')
R(['C2H2', 'Ag2O'], ['Ag2C2', 'H2O'], ['замещения'], 'NH3 (р-р)', rk='AgNH3', sign='серовато-белый осадок')
R(['C2H2', 'Cu(NH3)2Cl'], ['Cu2C2', 'NH4Cl', 'NH3'], ['замещения'], 'аммиачный р-р', rk='CuNH3',
  sign='красно-коричневый осадок')
R(['C2H2', 'Na'], ['Na2C2', 'H2'], ['замещения'], 't')
R(['Ag2C2', 'HCl'], ['C2H2', 'AgCl'], ['обмена'], '')
R(['CHCCH3', 'Ag(NH3)2OH'], ['CH3CCAg', 'NH3', 'H2O'], ['замещения'], 'аммиачный р-р', rk='AgNH3', sign='белый осадок')
R(['CHCCH3', 'Ag2O'], ['CH3CCAg', 'H2O'], ['замещения'], 'NH3 (р-р)', rk='AgNH3', sign='белый осадок')
R(['CHCCH3', 'NaNH2'], ['CH3CCNa', 'NH3'], ['замещения'], 'NH3 (ж.)')
R(['CH3CCNa', 'CH3Br'], ['CH3CCCH3', 'NaBr'], ['замещения'], '', rk='CH3Br')
R(['CH3CCAg', 'HCl'], ['CHCCH3', 'AgCl'], ['обмена'], '')
ALKY = [  # алкин, +H2 (Pd), +2H2, +H2O (Hg2+), +HBr, +2HBr, +2Br2, +2HCl
    ('CHCCH3', 'CH2CHCH3', 'C3H8', 'CH3COCH3', 'CH3CBrCH2', 'CH3CBr2CH3', 'CHBr2CBr2CH3', 'CH3CCl2CH3'),
    ('CHCCH2CH3', 'CH2CHCH2CH3', 'CH3CH2CH2CH3', 'CH3COCH2CH3', None, 'CH3CBr2CH2CH3', None, None),
    ('CH3CCCH3', 'CH3CHCHCH3', 'CH3CH2CH2CH3', 'CH3COCH2CH3', None, 'CH3CBr2CH2CH3', None, None),
    ('CHC(CH2)2CH3', 'CH2CH(CH2)2CH3', 'CH3(CH2)3CH3', 'CH3CO(CH2)2CH3', None, None, None, None),
    ('CHCCH(CH3)2', 'CH2CHCH(CH3)2', 'CH3CH(CH3)CH2CH3', 'CH3COCH(CH3)2', None, None, None, None),
    ('CHC(CH2)3CH3', 'CH2CH(CH2)3CH3', 'CH3(CH2)4CH3', None, None, None, None, None),
    ('CH3CCCH2CH3', 'CH3CHCHCH2CH3', 'CH3(CH2)3CH3', None, None, None, None, None),
    ('C6H5CCH', 'C6H5CHCH2', 'C6H5C2H5', 'C6H5COCH3', None, None, None, None),
]
for a, h1, h2, h2o, hbr, hbr2, br2, hcl2 in ALKY:
    R([a, 'H2'], [h1], ['присоединения', 'гидрирования'], 'Pd (Pb2+), t', tags=['частичное гидрирование'])
    R([a, 'H2'], [h2], ['присоединения', 'гидрирования'], 'Ni, t, избыток H2')
    if h2o:
        R([a, 'H2O'], [h2o], ['присоединения', 'гидратации'], 'Hg2+, H+', tags=['реакция Кучерова', 'правило Марковникова'])
    if hbr:
        R([a, 'HBr'], [hbr], ['присоединения', 'гидрогалогенирования'], '1 моль HBr', tags=['правило Марковникова'])
    if hbr2:
        R([a, 'HBr'], [hbr2], ['присоединения', 'гидрогалогенирования'], 'избыток HBr', tags=['правило Марковникова'])
    if br2:
        R([a, 'Br2'], [br2], ['присоединения', 'галогенирования'], 'избыток Br2', rk='Br2aq', sign='обесцвечивание бромной воды')
    if hcl2:
        R([a, 'HCl'], [hcl2], ['присоединения', 'гидрогалогенирования'], 'избыток HCl', tags=['правило Марковникова'])
for a in ['CHCCH2CH3', 'CH3CCCH3', 'CHC(CH2)2CH3', 'CHCCH(CH3)2', 'CH2CHCCH', 'C6H5CCH', 'CHC(CH2)3CH3', 'CH3CCCH2CH3',
          'CH2CCH2', 'CH2CHCHCH2', 'CH2C(CH3)CHCH2', 'CH2CHCHCHCH3', 'CH2CHCH2CHCH2', 'CH2C(CH3)C(CH3)CH2', 'C5H6',
          'CH2CCHCH3']:
    F([a, 'Br2'], ['продукт присоединения брома'], ['присоединения', 'галогенирования'], 'бромная вода', rk='Br2aq',
      sign='обесцвечивание бромной воды')
    F([a, 'KMnO4'], ['продукты окисления'], ['окисления', 'ОВР'], 'р-р', rk='KMnO4', sign='обесцвечивание раствора KMnO4')
for a in ['CH2CH(CH2)2CH3', 'CH3CHCHCH2CH3', 'CH2C(CH3)CH2CH3', '(CH3)2CCHCH3', 'CH2CHCH(CH3)2', 'CH2CH(CH2)3CH3',
          '(CH3)2CC(CH3)2', 'C5H8', 'CHCCH3']:
    F([a, 'Br2'], ['продукт присоединения брома'], ['присоединения', 'галогенирования'], 'бромная вода', rk='Br2aq',
      sign='обесцвечивание бромной воды')
    F([a, 'KMnO4'], ['продукты окисления'], ['окисления', 'ОВР'], 'р-р', rk='KMnO4', sign='обесцвечивание раствора KMnO4')
for a in ['CHCCH3', 'CHCCH2CH3', 'CHC(CH2)2CH3', 'CHCCH(CH3)2', 'CHC(CH2)3CH3', 'C6H5CCH', 'CH2CHCCH']:
    F([a, 'Ag(NH3)2OH'], ['ацетиленид серебра'], ['замещения'], 'аммиачный р-р', rk='AgNH3', sign='осадок')
for dh, al, z in [('CH2BrCH2Br', 'C2H2', 'KOH'), ('CH3CHBr2', 'C2H2', 'KOH'), ('CH2BrCHBrCH3', 'CHCCH3', 'KOH'),
                  ('CH3CBr2CH3', 'CHCCH3', 'KOH'), ('CH3CHBrCHBrCH3', 'CH3CCCH3', 'KOH'),
                  ('CH2BrCHBrCH2CH3', 'CHCCH2CH3', 'KOH'), ('CH2ClCH2Cl', 'C2H2', 'KOH'), ('CH3CCl2CH3', 'CHCCH3', 'KOH'),
                  ('CH2BrCH2Br', 'C2H2', 'NaOH'), ('CH2BrCHBrCH3', 'CHCCH3', 'NaOH')]:
    R([dh, z], [al, z[0] + ('Br' if 'Br' in dh else 'Cl') if z == 'KOH' else 'Na' + ('Br' if 'Br' in dh else 'Cl'), 'H2O'],
      ['отщепления', 'дегидрогалогенирования'], 'спирт. р-р, t', rk=z + 'alc')
R(['CHBr2CHBr2', 'Zn'], ['C2H2', 'ZnBr2'], ['отщепления', 'дегалогенирования'], 't')

# ---------------------------------------------------------------- арены
AR_ = [  # арен, +3H2 →
    ('C6H6', '(CH2)6'), ('C6H5CH3', 'C6H11CH3'), ('C6H5C2H5', 'C5H9C2H5'),
]
R(['C6H6', 'H2'], ['(CH2)6'], ['присоединения', 'гидрирования'], 'Ni (Pt), t, p')
R(['C6H5CH3', 'H2'], ['C6H11CH3'], ['присоединения', 'гидрирования'], 'Ni (Pt), t, p')
R(['C6H6', 'Cl2'], ['C6H6Cl6'], ['присоединения', 'галогенирования'], 'hv', rk='Cl2hv', tags=['радикальное присоединение'])
R(['C6H6', 'Br2'], ['C6H5Br', 'HBr'], ['замещения', 'галогенирования'], 'FeBr3', rk='Br2Fe', tags=['электрофильное замещение'])
R(['C6H6', 'Cl2'], ['C6H5Cl', 'HCl'], ['замещения', 'галогенирования'], 'FeCl3 (AlCl3)', rk='Cl2Fe',
  tags=['электрофильное замещение'])
R(['C6H6', 'HNO3'], ['C6H5NO2', 'H2O'], ['замещения', 'нитрования'], 'H2SO4 (конц.), t', tags=['электрофильное замещение'])
R(['C6H6', 'CH3Cl'], ['C6H5CH3', 'HCl'], ['замещения', 'алкилирования'], 'AlCl3', tags=['алкилирование по Фриделю–Крафтсу'])
R(['C6H6', 'C2H5Cl'], ['C6H5C2H5', 'HCl'], ['замещения', 'алкилирования'], 'AlCl3', tags=['алкилирование по Фриделю–Крафтсу'])
R(['C6H6', 'CH3CHClCH3'], ['C6H5CH(CH3)2', 'HCl'], ['замещения', 'алкилирования'], 'AlCl3')
R(['C6H6', 'C2H4'], ['C6H5C2H5'], ['присоединения', 'алкилирования'], 'H3PO4 (AlCl3), t')
R(['C6H6', 'CH2CHCH3'], ['C6H5CH(CH3)2'], ['присоединения', 'алкилирования'], 'H3PO4 (AlCl3), t', tags=['правило Марковникова'])
R(['C6H5CH3', 'Cl2'], ['C6H5CH2Cl', 'HCl'], ['замещения', 'галогенирования'], 'hv', rk='Cl2hv',
  tags=['замещение в боковой цепи'])
R(['C6H5CH3', 'Cl2'], ['C6H5CCl3', 'HCl'], ['замещения', 'галогенирования'], 'hv, избыток Cl2', rk='Cl2hv')
R(['C6H5CH3', 'Cl2'], ['ClC6H4CH3', 'HCl'], ['замещения', 'галогенирования'], 'FeCl3', rk='Cl2Fe',
  tags=['орто-, пара-ориентант'], note='образуется смесь 2- и 4-хлортолуола')
R(['C6H5CH3', 'Cl2'], ['CH3C6H4Cl', 'HCl'], ['замещения', 'галогенирования'], 'FeCl3', rk='Cl2Fe',
  tags=['орто-, пара-ориентант'], note='образуется смесь 2- и 4-хлортолуола')
R(['C6H5CH3', 'HNO3'], ['CH3C6H4NO2', 'H2O'], ['замещения', 'нитрования'], 'H2SO4 (конц.)', tags=['орто-, пара-ориентант'],
  note='образуется смесь 2- и 4-нитротолуола')
R(['C6H5CH3', 'HNO3'], ['C6H2(NO2)3CH3', 'H2O'], ['замещения', 'нитрования'], 'H2SO4 (конц.), t, избыток HNO3',
  tags=['орто-, пара-ориентант'])
R(['C6H5C2H5', 'Br2'], ['C6H5CHBrCH3', 'HBr'], ['замещения', 'галогенирования'], 'hv', rk='Br2hv',
  tags=['замещение в боковой цепи'])
R(['C6H5C2H5', 'Cl2'], ['C6H5CHClCH3', 'HCl'], ['замещения', 'галогенирования'], 'hv', rk='Cl2hv',
  tags=['замещение в боковой цепи'])
R(['C6H5CH3', 'KMnO4', 'H2SO4'], ['C6H5COOH', 'MnSO4', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4, t', rk='KMnO4',
  medium='кисл.', sign='обесцвечивание раствора KMnO4')
R(['C6H5CH3', 'KMnO4'], ['C6H5COOK', 'MnO2', 'KOH', 'H2O'], ['окисления', 'ОВР'], 'водн. р-р, t', rk='KMnO4',
  medium='нейтр.', sign='обесцвечивание раствора KMnO4, бурый осадок')
R(['C6H5CH3', 'KMnO4', 'KOH'], ['C6H5COOK', 'K2MnO4', 'H2O'], ['окисления', 'ОВР'], 'KOH, t', rk='KMnO4', medium='щел.')
R(['CH3C6H4CH3', 'KMnO4', 'H2SO4'], ['HOOCC6H4COOH', 'MnSO4', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4, t', rk='KMnO4',
  medium='кисл.')
R(['C6H4(CH3)2', 'KMnO4', 'H2SO4'], ['C6H4(COOH)2', 'MnSO4', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4, t', rk='KMnO4',
  medium='кисл.')
R(['CH3C6H4CH3', 'KMnO4'], ['KOOCC6H4COOK', 'MnO2', 'KOH', 'H2O'], ['окисления', 'ОВР'], 'водн. р-р, t', rk='KMnO4',
  medium='нейтр.')
R(['C6H5CH(CH3)2', 'O2'], ['C6H5OH', 'CH3COCH3'], ['окисления'], 'H2SO4, через гидропероксид', rk='O2cat',
  tags=['кумольный способ'])
R(['C6H5COOH', 'HNO3'], ['O2NC6H4COOH', 'H2O'], ['замещения', 'нитрования'], 'H2SO4 (конц.), t', tags=['мета-ориентант'])
R(['C6H5COOH', 'Br2'], ['BrC6H4COOH', 'HBr'], ['замещения', 'галогенирования'], 'FeBr3', rk='Br2Fe', tags=['мета-ориентант'])
R(['C6H5NO2', 'HNO3'], ['C6H4(NO2)2', 'H2O'], ['замещения', 'нитрования'], 'H2SO4 (конц.), t', tags=['мета-ориентант'])
R(['C6H5NO2', 'Br2'], ['BrC6H4NO2', 'HBr'], ['замещения', 'галогенирования'], 'FeBr3, t', rk='Br2Fe', tags=['мета-ориентант'])

# ---------------------------------------------------------------- галогенпроизводные
HAL = [  # галогеналкан, спирт (водн. щёлочь), алкен (спирт. щёлочь)
    ('CH3Cl', 'CH3OH', None), ('CH3Br', 'CH3OH', None), ('C2H5Cl', 'C2H5OH', 'C2H4'), ('C2H5Br', 'C2H5OH', 'C2H4'),
    ('CH3CH2CH2Cl', 'CH3CH2CH2OH', 'CH2CHCH3'), ('CH3CHClCH3', 'CH3CH(OH)CH3', 'CH2CHCH3'),
    ('CH3CH2CH2Br', 'CH3CH2CH2OH', 'CH2CHCH3'), ('CH3CHBrCH3', 'CH3CH(OH)CH3', 'CH2CHCH3'),
    ('CH3(CH2)3Br', 'CH3(CH2)3OH', 'CH2CHCH2CH3'), ('CH3CHBrCH2CH3', 'CH3CH(OH)CH2CH3', 'CH3CHCHCH3'),
    ('CH3CHClCH2CH3', 'CH3CH(OH)CH2CH3', 'CH3CHCHCH3'), ('(CH3)3CBr', '(CH3)3COH', 'CH2C(CH3)2'),
    ('(CH3)3CCl', '(CH3)3COH', 'CH2C(CH3)2'), ('(CH3)2CHCH2Br', '(CH3)2CHCH2OH', 'CH2C(CH3)2'),
    ('(CH3)2CClCH2CH3', '(CH3)2C(OH)CH2CH3', '(CH3)2CCHCH3'), ('(CH3)2CBrCH2CH3', '(CH3)2C(OH)CH2CH3', '(CH3)2CCHCH3'),
    ('C6H11Cl', 'C6H11OH', 'C6H10'), ('C6H5CH2Cl', 'C6H5CH2OH', None), ('C6H5CHBrCH3', 'C6H5CH(OH)CH3', 'C6H5CHCH2'),
    ('C6H5CHClCH3', 'C6H5CH(OH)CH3', 'C6H5CHCH2'),
]
for x, al, en in HAL:
    X = 'Br' if 'Br' in x else 'Cl'
    R([x, 'NaOH'], [al, 'Na' + X], ['замещения', 'гидролиза'], 'водн. р-р, t', rk='NaOH', tags=['нуклеофильное замещение'])
    R([x, 'KOH'], [al, 'K' + X], ['замещения', 'гидролиза'], 'водн. р-р, t', rk='KOH', tags=['нуклеофильное замещение'])
    if en:
        R([x, 'KOH'], [en, 'K' + X, 'H2O'], ['отщепления', 'дегидрогалогенирования'], 'спирт. р-р, t', rk='KOHalc',
          tags=['правило Зайцева'])
        R([x, 'NaOH'], [en, 'Na' + X, 'H2O'], ['отщепления', 'дегидрогалогенирования'], 'спирт. р-р, t', rk='NaOHalc',
          tags=['правило Зайцева'])
for dh, p in [('CH2ClCH2Cl', 'C2H4(OH)2'), ('CH2BrCH2Br', 'C2H4(OH)2'), ('CH2BrCHBrCH3', 'CH3CH(OH)CH2OH'),
              ('CH2ClCHClCH3', 'CH3CH(OH)CH2OH')]:
    X = 'Br' if 'Br' in dh else 'Cl'
    R([dh, 'NaOH'], [p, 'Na' + X], ['замещения', 'гидролиза'], 'водн. р-р, t', rk='NaOH')
    R([dh, 'KOH'], [p, 'K' + X], ['замещения', 'гидролиза'], 'водн. р-р, t', rk='KOH')
for gd, p in [('CH3CHCl2', 'CH3CHO'), ('CH3CHBr2', 'CH3CHO'), ('CH3CCl2CH3', 'CH3COCH3'), ('CH3CBr2CH3', 'CH3COCH3'),
              ('CH3CBr2CH2CH3', 'CH3COCH2CH3')]:
    X = 'Br' if 'Br' in gd else 'Cl'
    R([gd, 'NaOH'], [p, 'Na' + X, 'H2O'], ['замещения', 'гидролиза'], 'водн. р-р, t', rk='NaOH',
      tags=['гем-дигалогенид → карбонильное соединение'])
    R([gd, 'KOH'], [p, 'K' + X, 'H2O'], ['замещения', 'гидролиза'], 'водн. р-р, t', rk='KOH',
      tags=['гем-дигалогенид → карбонильное соединение'])
for dh, en, z in [('CH2BrCH2Br', 'C2H4', 'Zn'), ('CH2BrCH2Br', 'C2H4', 'Mg'), ('CH2ClCH2Cl', 'C2H4', 'Zn'),
                  ('CH2ClCH2Cl', 'C2H4', 'Mg'), ('CH2BrCHBrCH3', 'CH2CHCH3', 'Zn'), ('CH2BrCHBrCH3', 'CH2CHCH3', 'Mg'),
                  ('CH2ClCHClCH3', 'CH2CHCH3', 'Zn'), ('CH3CHBrCHBrCH3', 'CH3CHCHCH3', 'Zn'),
                  ('CH2BrCHBrCH2CH3', 'CH2CHCH2CH3', 'Zn'), ('(CH3)2CBrCH2Br', 'CH2C(CH3)2', 'Zn'),
                  ('C6H10Br2', 'C6H10', 'Zn'), ('C6H5CHBrCH2Br', 'C6H5CHCH2', 'Zn'), ('CH3CHBrCHBrCH3', 'CH3CHCHCH3', 'Mg')]:
    X = 'Br' if 'Br' in dh else 'Cl'
    R([dh, z], [en, z + X + '2'], ['отщепления', 'дегалогенирования'], 't')
for x, am, s_ in [('CH3Cl', 'CH3NH2', 'NH4Cl'), ('CH3Br', 'CH3NH2', 'NH4Br'), ('C2H5Cl', 'C2H5NH2', 'NH4Cl'),
                  ('C2H5Br', 'C2H5NH2', 'NH4Br')]:
    R([x, 'NH3'], [am, s_], ['замещения'], 'избыток NH3, t', tags=['алкилирование аммиака'])
R(['CH3Cl', 'NH3'], ['CH3NH3Cl'], ['присоединения'], 't')
R(['C2H5Br', 'NH3'], ['C2H5NH3Br'], ['присоединения'], 't')
R(['CH3Br', 'NH3'], ['CH3NH3Br'], ['присоединения'], 't')
R(['CH3NH2', 'CH3Cl'], ['(CH3)2NH2Cl'], ['присоединения', 'алкилирования'], 't', rk='CH3Cl')
R(['(CH3)2NH', 'CH3Cl'], ['(CH3)3NHCl'], ['присоединения', 'алкилирования'], 't', rk='CH3Cl')
R(['C2H5NH2', 'C2H5Cl'], ['(C2H5)2NH2Cl'], ['присоединения', 'алкилирования'], 't', rk='C2H5Cl')
R(['CH3Cl', 'CH3ONa'], ['CH3OCH3', 'NaCl'], ['замещения'], '', rk='CH3ONa', tags=['синтез Вильямсона'])
R(['C2H5Cl', 'C2H5ONa'], ['C2H5OC2H5', 'NaCl'], ['замещения'], '', rk='C2H5ONa', tags=['синтез Вильямсона'])
R(['CH3Br', 'C2H5ONa'], ['CH3OC2H5', 'NaBr'], ['замещения'], '', rk='C2H5ONa', tags=['синтез Вильямсона'])
R(['C6H5Cl', 'NaOH'], ['C6H5OH', 'NaCl'], ['замещения'], 't, p, кат.', rk='NaOHtp')
R(['C6H5Cl', 'NaOH'], ['C6H5ONa', 'NaCl', 'H2O'], ['замещения'], 't, p (избыток щёлочи)', rk='NaOHtp')
R(['C6H5Cl', 'KOH'], ['C6H5OK', 'KCl', 'H2O'], ['замещения'], 't, p (избыток щёлочи)', rk='KOHtp')
R(['C6H5Br', 'NaOH'], ['C6H5ONa', 'NaBr', 'H2O'], ['замещения'], 't, p (избыток щёлочи)', rk='NaOHtp')
R(['CH2ClCOOH', 'NH3'], ['H2NCH2COOH', 'NH4Cl'], ['замещения'], 'избыток NH3', tags=['получение аминокислот'])
R(['CH3CHClCOOH', 'NH3'], ['CH3CH(NH2)COOH', 'NH4Cl'], ['замещения'], 'избыток NH3', tags=['получение аминокислот'])

# ---------------------------------------------------------------- спирты
ALC = [  # спирт, алкоголят Na, +HBr, +HCl, внутримол. дегидратация, CuO →, KMnO4/H2SO4 →
    ('CH3OH', 'CH3ONa', 'CH3Br', 'CH3Cl', None, 'HCHO', 'CO2'),
    ('C2H5OH', 'C2H5ONa', 'C2H5Br', 'C2H5Cl', 'C2H4', 'CH3CHO', 'CH3COOH'),
    ('CH3CH2CH2OH', 'CH3CH2CH2ONa', 'CH3CH2CH2Br', 'CH3CH2CH2Cl', 'CH2CHCH3', 'CH3CH2CHO', 'CH3CH2COOH'),
    ('CH3CH(OH)CH3', 'CH3CH(ONa)CH3', 'CH3CHBrCH3', 'CH3CHClCH3', 'CH2CHCH3', 'CH3COCH3', 'CH3COCH3'),
    ('CH3(CH2)3OH', None, 'CH3(CH2)3Br', None, 'CH2CHCH2CH3', 'CH3(CH2)2CHO', 'CH3(CH2)2COOH'),
    ('CH3CH(OH)CH2CH3', None, 'CH3CHBrCH2CH3', 'CH3CHClCH2CH3', 'CH3CHCHCH3', 'CH3COCH2CH3', 'CH3COCH2CH3'),
    ('(CH3)2CHCH2OH', None, '(CH3)2CHCH2Br', None, 'CH2C(CH3)2', '(CH3)2CHCHO', '(CH3)2CHCOOH'),
    ('(CH3)3COH', None, '(CH3)3CBr', '(CH3)3CCl', 'CH2C(CH3)2', None, None),
    ('CH3(CH2)4OH', None, None, None, 'CH2CH(CH2)2CH3', 'CH3(CH2)3CHO', 'CH3(CH2)3COOH'),
    ('(CH3)2C(OH)CH2CH3', None, '(CH3)2CBrCH2CH3', '(CH3)2CClCH2CH3', '(CH3)2CCHCH3', None, None),
    ('CH3CH(OH)CH(CH3)2', None, None, None, '(CH3)2CCHCH3', 'CH3COCH(CH3)2', 'CH3COCH(CH3)2'),
    ('CH3CH(OH)(CH2)2CH3', None, None, None, 'CH3CHCHCH2CH3', 'CH3CO(CH2)2CH3', None),
    ('(C2H5)2CHOH', None, None, None, 'CH3CHCHCH2CH3', 'CH3CH2COCH2CH3', None),
    ('C6H11OH', None, None, 'C6H11Cl', 'C6H10', 'C6H10O', None),
    ('C6H5CH2OH', 'C6H5CH2ONa', None, 'C6H5CH2Cl', None, 'C6H5CHO', 'C6H5COOH'),
    ('C6H5CH(OH)CH3', None, 'C6H5CHBrCH3', 'C6H5CHClCH3', 'C6H5CHCH2', 'C6H5COCH3', None),
    ('(CH3)2CHCH2CH2OH', None, None, None, 'CH2CHCH(CH3)2', None, None),
]
for al, ona, hbr, hcl, en, cuo, km in ALC:
    if ona:
        R([al, 'Na'], [ona, 'H2'], ['замещения', 'ОВР'], '', sign='выделение газа')
    if hbr:
        R([al, 'HBr'], [hbr, 'H2O'], ['замещения'], 't (H2SO4)', tags=['замещение гидроксогруппы'])
    if hcl:
        R([al, 'HCl'], [hcl, 'H2O'], ['замещения'], 't (ZnCl2)', tags=['замещение гидроксогруппы'])
    if en:
        R([al], [en, 'H2O'], ['отщепления', 'дегидратации'], 'H2SO4 (конц.), t > 140 °C', rk='H2SO4t',
          tags=['внутримолекулярная дегидратация', 'правило Зайцева'])
    if cuo:
        R([al, 'CuO'], [cuo, 'Cu', 'H2O'], ['окисления', 'ОВР'], 't', sign='чёрный CuO → красная медь')
    if km:
        R([al, 'KMnO4', 'H2SO4'], [km, 'MnSO4', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4, t', rk='KMnO4', medium='кисл.')
R(['C2H5OH', 'K'], ['C2H5OK', 'H2'], ['замещения', 'ОВР'], '', sign='выделение газа')
R(['C2H4(OH)2', 'Na'], ['C2H4(ONa)2', 'H2'], ['замещения', 'ОВР'], '')
R(['C3H5(OH)3', 'Na'], ['C3H5(ONa)3', 'H2'], ['замещения', 'ОВР'], '')
R(['C2H4(OH)2', 'HBr'], ['CH2BrCH2Br', 'H2O'], ['замещения'], 't')
R(['C2H4(OH)2', 'HCl'], ['CH2ClCH2Cl', 'H2O'], ['замещения'], 't')
R(['C3H5(OH)3', 'HCl'], ['CH2ClCH(OH)CH2OH', 'H2O'], ['замещения'], 't')
R(['C2H4(OH)2', 'CuO'], ['OHCCHO', 'Cu', 'H2O'], ['окисления', 'ОВР'], 't')
R(['C2H4(OH)2', 'KMnO4', 'H2SO4'], ['HOOCCOOH', 'MnSO4', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4', rk='KMnO4',
  medium='кисл.')
R(['C3H5(OH)3', 'HNO3'], ['C3H5(ONO2)3', 'H2O'], ['замещения', 'этерификации'], 'H2SO4 (конц.)',
  tags=['получение нитроглицерина'])
for a, b, e in [('CH3OH', 'CH3OH', 'CH3OCH3'), ('C2H5OH', 'C2H5OH', 'C2H5OC2H5'),
                ('CH3CH2CH2OH', 'CH3CH2CH2OH', 'C3H7OC3H7')]:
    R([a], [e, 'H2O'], ['отщепления', 'дегидратации'], 'H2SO4 (конц.), t < 140 °C', rk='H2SO4',
      tags=['межмолекулярная дегидратация'])
F(['CH3OH', 'C2H5OH'], ['CH3OC2H5', 'CH3OCH3', 'C2H5OC2H5', 'H2O'], ['отщепления', 'дегидратации'],
  'H2SO4 (конц.), t < 140 °C', rk='C2H5OH', why='смесь трёх эфиров')
R(['CH3OH', 'O2'], ['HCHO', 'H2O'], ['окисления'], 'Cu (Ag), t', rk='O2cat', tags=['промышленное получение формальдегида'])
R(['C2H5OH'], ['CH3CHO', 'H2'], ['отщепления', 'дегидрирования'], 'Cu, t', rk='')
R(['CH3OH'], ['HCHO', 'H2'], ['отщепления', 'дегидрирования'], 'Cu, t', rk='')
R(['CH3CH(OH)CH3'], ['CH3COCH3', 'H2'], ['отщепления', 'дегидрирования'], 'Cu, t', rk='')
R(['C2H5OH', 'K2Cr2O7', 'H2SO4'], ['CH3CHO', 'Cr2(SO4)3', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4', rk='K2Cr2O7')
R(['CH3CH(OH)CH3', 'K2Cr2O7', 'H2SO4'], ['CH3COCH3', 'Cr2(SO4)3', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4',
  rk='K2Cr2O7')
R(['C2H5OH', 'O2'], ['CH3COOH', 'H2O'], ['окисления'], 'ферменты', rk='O2cat', tags=['уксуснокислое брожение'])
R(['C2H5OH', 'NH3'], ['C2H5NH2', 'H2O'], ['замещения'], 'Al2O3, t')
R(['CH3OH', 'NH3'], ['CH3NH2', 'H2O'], ['замещения'], 'Al2O3, t')
for ona, al, na in [('C2H5ONa', 'C2H5OH', 'NaOH'), ('CH3ONa', 'CH3OH', 'NaOH'), ('C2H5OK', 'C2H5OH', 'KOH'),
                    ('CH3CH2CH2ONa', 'CH3CH2CH2OH', 'NaOH')]:
    R([ona, 'H2O'], [al, na], ['гидролиза'], '', rk='H2O')
R(['C2H5ONa', 'HCl'], ['C2H5OH', 'NaCl'], ['обмена'], '')
R(['CH3ONa', 'HCl'], ['CH3OH', 'NaCl'], ['обмена'], '')
F(['C3H5(OH)3', 'Cu(OH)2'], ['глицерат меди(II)'], ['комплексообразования'], 'NaOH (избыток)', rk='Cu(OH)2',
  sign='голубой осадок растворяется, ярко-синий раствор', qual=True)
F(['C2H4(OH)2', 'Cu(OH)2'], ['гликолят меди(II)'], ['комплексообразования'], 'NaOH (избыток)', rk='Cu(OH)2',
  sign='голубой осадок растворяется, ярко-синий раствор', qual=True)
F(['CH3CH(OH)CH2OH', 'Cu(OH)2'], ['комплекс меди(II)'], ['комплексообразования'], 'NaOH (избыток)', rk='Cu(OH)2',
  sign='ярко-синий раствор', qual=True)
F(['C3H5(OH)3', 'KMnO4'], ['продукты окисления'], ['окисления', 'ОВР'], 'р-р', rk='KMnO4')
F(['C2H4(OH)2', 'KMnO4'], ['продукты окисления'], ['окисления', 'ОВР'], 'р-р', rk='KMnO4')

# ---------------------------------------------------------------- фенолы
R(['C6H5OH', 'NaOH'], ['C6H5ONa', 'H2O'], ['обмена', 'нейтрализации'], '', tags=['кислотные свойства фенола'])
R(['C6H5OH', 'KOH'], ['C6H5OK', 'H2O'], ['обмена', 'нейтрализации'], '', tags=['кислотные свойства фенола'])
R(['C6H5OH', 'Na'], ['C6H5ONa', 'H2'], ['замещения', 'ОВР'], 'расплав', sign='выделение газа')
R(['C6H5OH', 'K'], ['C6H5OK', 'H2'], ['замещения', 'ОВР'], 'расплав', sign='выделение газа')
R(['C6H5OH', 'Br2'], ['C6H2Br3OH', 'HBr'], ['замещения', 'галогенирования'], 'бромная вода', rk='Br2aq',
  sign='обесцвечивание бромной воды, белый осадок', tags=['электрофильное замещение', 'орто-, пара-ориентант'])
R(['C6H5OH', 'HNO3'], ['C6H2(NO2)3OH', 'H2O'], ['замещения', 'нитрования'], 'H2SO4 (конц.)', tags=['орто-, пара-ориентант'])
R(['C6H5OH', 'H2'], ['C6H11OH'], ['присоединения', 'гидрирования'], 'Ni, t, p')
R(['C6H5OH', '(CH3CO)2O'], ['CH3COOC6H5', 'CH3COOH'], ['замещения', 'этерификации'], 't', rk='(CH3CO)2O')
R(['C6H5ONa', 'HCl'], ['C6H5OH', 'NaCl'], ['обмена'], '')
R(['C6H5ONa', 'CO2', 'H2O'], ['C6H5OH', 'NaHCO3'], ['обмена'], '', rk='CO2', tags=['фенол слабее угольной кислоты'],
  sign='помутнение раствора')
R(['C6H5ONa', 'CH3COOH'], ['C6H5OH', 'CH3COONa'], ['обмена'], '', rk='CH3COOH')
R(['C6H5OK', 'HCl'], ['C6H5OH', 'KCl'], ['обмена'], '')
F(['C6H5OH', 'FeCl3'], ['комплекс железа(III)'], ['качественная реакция'], '', rk='FeCl3', sign='фиолетовое окрашивание',
  qual=True)
F(['C6H5OH', 'HCHO'], ['фенолформальдегидная смола'], ['поликонденсации'], 'H+ или OH-, t', rk='HCHO')
F(['CH3C6H4OH', 'NaOH'], ['2-метилфенолят натрия'], ['нейтрализации'], '', rk='NaOH')

# ---------------------------------------------------------------- альдегиды и кетоны
ALD = [  # альдегид, +H2 →, кислота, аммонийная соль, натриевая соль
    ('CH3CHO', 'C2H5OH', 'CH3COOH', 'CH3COONH4', 'CH3COONa'),
    ('CH3CH2CHO', 'CH3CH2CH2OH', 'CH3CH2COOH', 'CH3CH2COONH4', 'CH3CH2COONa'),
    ('CH3(CH2)2CHO', 'CH3(CH2)3OH', 'CH3(CH2)2COOH', None, 'CH3(CH2)2COONa'),
    ('(CH3)2CHCHO', '(CH3)2CHCH2OH', '(CH3)2CHCOOH', None, '(CH3)2CHCOONa'),
    ('CH3(CH2)3CHO', 'CH3(CH2)4OH', 'CH3(CH2)3COOH', None, None),
    ('C6H5CHO', 'C6H5CH2OH', 'C6H5COOH', None, 'C6H5COONa'),
]
for ad, h2, ac, nh4, na in ALD:
    R([ad, 'H2'], [h2], ['присоединения', 'гидрирования', 'восстановления'], 'Ni, t')
    R([ad, 'Ag2O'], [ac, 'Ag'], ['окисления', 'ОВР'], 'NH3 (р-р), t', rk='AgNH3', sign='серебряное зеркало',
      tags=['реакция «серебряного зеркала»'])
    if nh4:
        R([ad, 'Ag(NH3)2OH'], [nh4, 'Ag', 'NH3', 'H2O'], ['окисления', 'ОВР'], 't', rk='AgNH3', sign='серебряное зеркало',
          tags=['реакция «серебряного зеркала»'])
    R([ad, 'Cu(OH)2'], [ac, 'Cu2O', 'H2O'], ['окисления', 'ОВР'], 't', sign='красный осадок Cu2O')
    if na:
        R([ad, 'Cu(OH)2', 'NaOH'], [na, 'Cu2O', 'H2O'], ['окисления', 'ОВР'], 'NaOH, t', rk='Cu(OH)2',
          sign='красный осадок Cu2O')
    R([ad, 'KMnO4', 'H2SO4'], [ac, 'MnSO4', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4', rk='KMnO4', medium='кисл.')
    R([ad, 'Br2', 'H2O'], [ac, 'HBr'], ['окисления', 'ОВР'], 'бромная вода', rk='Br2aq', sign='обесцвечивание бромной воды')
    R([ad, 'O2'], [ac], ['окисления'], 'кат. (Mn2+), t', rk='O2cat')
R(['CH3CHO', 'K2Cr2O7', 'H2SO4'], ['CH3COOH', 'Cr2(SO4)3', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4', rk='K2Cr2O7')
R(['HCHO', 'H2'], ['CH3OH'], ['присоединения', 'гидрирования', 'восстановления'], 'Ni, t')
R(['HCHO', 'Ag2O'], ['CO2', 'Ag', 'H2O'], ['окисления', 'ОВР'], 'NH3 (р-р), t', rk='AgNH3', sign='серебряное зеркало',
  tags=['реакция «серебряного зеркала»'])
R(['HCHO', 'Ag(NH3)2OH'], ['(NH4)2CO3', 'Ag', 'NH3', 'H2O'], ['окисления', 'ОВР'], 't', rk='AgNH3', sign='серебряное зеркало')
R(['HCHO', 'Cu(OH)2'], ['CO2', 'Cu2O', 'H2O'], ['окисления', 'ОВР'], 't', sign='красный осадок Cu2O')
R(['HCHO', 'KMnO4', 'H2SO4'], ['CO2', 'MnSO4', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4', rk='KMnO4', medium='кисл.')
R(['HCHO', 'Br2', 'H2O'], ['CO2', 'HBr'], ['окисления', 'ОВР'], 'бромная вода', rk='Br2aq', sign='обесцвечивание бромной воды')
R(['HCHO', 'O2'], ['HCOOH'], ['окисления'], 'кат.', rk='O2cat')
R(['CH2CHCHO', 'H2'], ['CH3CH2CH2OH'], ['присоединения', 'гидрирования'], 'Ni, t, избыток H2')
R(['CH2CHCHO', 'Ag2O'], ['CH2CHCOOH', 'Ag'], ['окисления', 'ОВР'], 'NH3 (р-р), t', rk='AgNH3', sign='серебряное зеркало')
R(['OHCCHO', 'H2'], ['C2H4(OH)2'], ['присоединения', 'гидрирования'], 'Ni, t, избыток H2')
R(['OHCCHO', 'Ag2O'], ['HOOCCOOH', 'Ag'], ['окисления', 'ОВР'], 'NH3 (р-р), t', rk='AgNH3', sign='серебряное зеркало')
KET = [('CH3COCH3', 'CH3CH(OH)CH3'), ('CH3COCH2CH3', 'CH3CH(OH)CH2CH3'), ('CH3CO(CH2)2CH3', 'CH3CH(OH)(CH2)2CH3'),
       ('CH3CH2COCH2CH3', '(C2H5)2CHOH'), ('CH3COCH(CH3)2', 'CH3CH(OH)CH(CH3)2'), ('C6H10O', 'C6H11OH'),
       ('C6H5COCH3', 'C6H5CH(OH)CH3')]
for k, al in KET:
    R([k, 'H2'], [al], ['присоединения', 'гидрирования', 'восстановления'], 'Ni, t')
R(['(CH3COO)2Ca'], ['CH3COCH3', 'CaCO3'], ['разложения'], 't', rk='', tags=['пиролиз солей кальция'])
F(['CH3COCH3', 'KMnO4'], ['продукты жёсткого окисления'], ['окисления'], 'KMnO4, H2SO4, t (жёсткие условия)', rk='KMnO4hard')

# ---------------------------------------------------------------- карбоновые кислоты
ACID = [  # кислота, Na-соль, K-соль, Ca-соль, Mg-соль
    ('HCOOH', 'HCOONa', 'HCOOK', None, None),
    ('CH3COOH', 'CH3COONa', 'CH3COOK', '(CH3COO)2Ca', '(CH3COO)2Mg'),
    ('CH3CH2COOH', 'CH3CH2COONa', 'CH3CH2COOK', None, None),
    ('CH3(CH2)2COOH', 'CH3(CH2)2COONa', None, None, None),
    ('(CH3)2CHCOOH', '(CH3)2CHCOONa', None, None, None),
    ('C6H5COOH', 'C6H5COONa', 'C6H5COOK', None, None),
    ('C17H35COOH', 'C17H35COONa', 'C17H35COOK', None, None),
    ('C15H31COOH', 'C15H31COONa', 'C15H31COOK', None, None),
    ('C17H33COOH', 'C17H33COONa', 'C17H33COOK', None, None),
    ('C17H31COOH', 'C17H31COONa', None, None, None),
    ('CH2CHCOOH', 'CH2CHCOONa', None, None, None),
    ('CH3CH(OH)COOH', 'CH3CH(OH)COONa', None, None, None),
]
for ac, na, k, ca, mg in ACID:
    R([ac, 'NaOH'], [na, 'H2O'], ['обмена', 'нейтрализации'], '')
    R([ac, 'NaHCO3'], [na, 'CO2', 'H2O'], ['обмена'], '', sign='выделение газа')
    R([ac, 'Na2CO3'], [na, 'CO2', 'H2O'], ['обмена'], '', sign='выделение газа')
    R([ac, 'Na'], [na, 'H2'], ['замещения', 'ОВР'], '', sign='выделение газа')
    if k:
        R([ac, 'KOH'], [k, 'H2O'], ['обмена', 'нейтрализации'], '')
        R([ac, 'KHCO3'], [k, 'CO2', 'H2O'], ['обмена'], '', sign='выделение газа')
        R([ac, 'K2CO3'], [k, 'CO2', 'H2O'], ['обмена'], '', sign='выделение газа')
    if ca:
        R([ac, 'Ca(OH)2'], [ca, 'H2O'], ['обмена', 'нейтрализации'], '')
        R([ac, 'CaCO3'], [ca, 'CO2', 'H2O'], ['обмена'], '', sign='растворение осадка, выделение газа')
        R([ac, 'CaO'], [ca, 'H2O'], ['обмена'], '')
    if mg:
        R([ac, 'Mg'], [mg, 'H2'], ['замещения', 'ОВР'], '', sign='выделение газа')
        R([ac, 'MgO'], [mg, 'H2O'], ['обмена'], '')
    R([na, 'HCl'], [ac, 'NaCl'], ['обмена'], '', tags=['вытеснение слабой кислоты сильной'])
R(['CH3COOH', 'Cu(OH)2'], ['(CH3COO)2Cu', 'H2O'], ['обмена', 'нейтрализации'], '', sign='растворение голубого осадка')
R(['CH3COOH', 'CuO'], ['(CH3COO)2Cu', 'H2O'], ['обмена'], 't')
R(['CH3COOH', 'NH3'], ['CH3COONH4'], ['соединения'], '')
R(['CH3COONa', 'H2SO4'], ['CH3COOH', 'Na2SO4'], ['обмена'], 't', tags=['вытеснение слабой кислоты сильной'])
R(['CH3COONa', 'H2SO4'], ['CH3COOH', 'NaHSO4'], ['обмена'], 'H2SO4 (конц.), t', tags=['вытеснение слабой кислоты сильной'])
R(['C6H5COOK', 'HCl'], ['C6H5COOH', 'KCl'], ['обмена'], '')
R(['CH3COOK', 'HCl'], ['CH3COOH', 'KCl'], ['обмена'], '')
R(['C17H35COONa', 'CaCl2'], ['(C17H35COO)2Ca', 'NaCl'], ['обмена'], '', rk='CaCl2', sign='осадок (мыло в жёсткой воде)')
R(['C17H35COONa', 'Ca(HCO3)2'], ['(C17H35COO)2Ca', 'NaHCO3'], ['обмена'], '', rk='CaCl2', sign='осадок')
R(['HOOCCOOH', 'NaOH'], ['NaOOCCOONa', 'H2O'], ['обмена', 'нейтрализации'], '')
R(['HOOCCOOH', 'KOH'], ['KOOCCOOK', 'H2O'], ['обмена', 'нейтрализации'], '')
for _a, _salt, _b in [('HOOCCOOH', 'NaOOCCOONa', 'NaHCO3'), ('HOOCCOOH', 'NaOOCCOONa', 'Na2CO3'),
                      ('HOOCCOOH', 'NaOOCCOONa', 'Na'), ('HOOCCOOH', 'KOOCCOOK', 'K2CO3'),
                      ('HOOCCOOH', 'KOOCCOOK', 'KHCO3'), ('HOOCC6H4COOH', 'KOOCC6H4COOK', 'K2CO3'),
                      ('CH2ClCOOH', 'CH2ClCOONa', 'NaHCO3'), ('CH2ClCOOH', 'CH2ClCOONa', 'NaOH')]:
    R([_a, _b], [_salt] + (['H2'] if _b == 'Na' else ['CO2', 'H2O'] if 'CO3' in _b else ['H2O']),
      ['обмена'] if _b != 'Na' else ['замещения', 'ОВР'], '')
R(['HOOCCOOH', 'KMnO4', 'H2SO4'], ['CO2', 'MnSO4', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4, t', rk='KMnO4',
  medium='кисл.', sign='обесцвечивание раствора KMnO4')
R(['HOOCC6H4COOH', 'KOH'], ['KOOCC6H4COOK', 'H2O'], ['обмена', 'нейтрализации'], '')
R(['CH3COOH', 'Cl2'], ['CH2ClCOOH', 'HCl'], ['замещения', 'галогенирования'], 'P (красный), hv', rk='Cl2P',
  tags=['замещение в α-положение'])
R(['CH3CH2COOH', 'Cl2'], ['CH3CHClCOOH', 'HCl'], ['замещения', 'галогенирования'], 'P (красный), hv', rk='Cl2P',
  tags=['замещение в α-положение'])
R(['HCOOH'], ['CO', 'H2O'], ['разложения', 'дегидратации'], 'H2SO4 (конц.), t', rk='H2SO4t')
R(['HCOOH', 'Ag2O'], ['CO2', 'Ag', 'H2O'], ['окисления', 'ОВР'], 'NH3 (р-р), t', rk='AgNH3', sign='серебряное зеркало',
  tags=['реакция «серебряного зеркала»'])
R(['HCOOH', 'Ag(NH3)2OH'], ['(NH4)2CO3', 'Ag', 'NH3', 'H2O'], ['окисления', 'ОВР'], 't', rk='AgNH3', sign='серебряное зеркало')
R(['HCOOH', 'Cu(OH)2'], ['CO2', 'Cu2O', 'H2O'], ['окисления', 'ОВР'], 't', sign='красный осадок Cu2O')
R(['HCOOH', 'KMnO4', 'H2SO4'], ['CO2', 'MnSO4', 'K2SO4', 'H2O'], ['окисления', 'ОВР'], 'H2SO4', rk='KMnO4', medium='кисл.',
  sign='обесцвечивание раствора KMnO4')
R(['HCOOH', 'Br2'], ['CO2', 'HBr'], ['окисления', 'ОВР'], 'бромная вода', rk='Br2aq', sign='обесцвечивание бромной воды')
R(['HCOOH', 'Cl2'], ['CO2', 'HCl'], ['окисления', 'ОВР'], '', rk='Cl2')
R(['CH2CHCOOH', 'H2'], ['CH3CH2COOH'], ['присоединения', 'гидрирования'], 'Ni, t')
R(['CH2CHCOOH', 'Br2'], ['CH2BrCHBrCOOH'], ['присоединения', 'галогенирования'], 'бромная вода', rk='Br2aq',
  sign='обесцвечивание бромной воды')
R(['CH2CHCOOH', 'HBr'], ['BrCH2CH2COOH'], ['присоединения', 'гидрогалогенирования'], '',
  tags=['против правила Марковникова (влияние COOH)'])
R(['CH2C(CH3)COOH', 'H2'], ['(CH3)2CHCOOH'], ['присоединения', 'гидрирования'], 'Ni, t')
R(['C17H33COOH', 'H2'], ['C17H35COOH'], ['присоединения', 'гидрирования'], 'Ni, t')
R(['C17H33COOH', 'Br2'], ['C17H33Br2COOH'], ['присоединения', 'галогенирования'], 'бромная вода', rk='Br2aq',
  sign='обесцвечивание бромной воды')
R(['C17H31COOH', 'H2'], ['C17H35COOH'], ['присоединения', 'гидрирования'], 'Ni, t, избыток H2')
R(['C6H12O6'], ['CH3CH(OH)COOH'], ['молочнокислое брожение'], 'ферменты', rk='')
# этерификация
EST = [  # кислота, спирт, эфир
    ('HCOOH', 'CH3OH', 'HCOOCH3'), ('HCOOH', 'C2H5OH', 'HCOOC2H5'), ('HCOOH', 'CH3CH2CH2OH', 'HCOOCH2CH2CH3'),
    ('CH3COOH', 'CH3OH', 'CH3COOCH3'), ('CH3COOH', 'C2H5OH', 'CH3COOC2H5'), ('CH3COOH', 'CH3CH2CH2OH', 'CH3COOCH2CH2CH3'),
    ('CH3COOH', 'CH3CH(OH)CH3', 'CH3COOCH(CH3)2'), ('CH3COOH', '(CH3)2CHCH2CH2OH', 'CH3COOCH2CH2CH(CH3)2'),
    ('CH3CH2COOH', 'CH3OH', 'CH3CH2COOCH3'), ('CH3CH2COOH', 'C2H5OH', 'CH3CH2COOC2H5'),
    ('CH3(CH2)2COOH', 'C2H5OH', 'CH3(CH2)2COOC2H5'), ('C6H5COOH', 'CH3OH', 'C6H5COOCH3'),
    ('CH2CHCOOH', 'CH3OH', 'CH2CHCOOCH3'), ('CH2C(CH3)COOH', 'CH3OH', 'CH2C(CH3)COOCH3'),
]
ESTER_SALT = {'HCOOH': ('HCOONa', 'HCOOK'), 'CH3COOH': ('CH3COONa', 'CH3COOK'), 'CH3CH2COOH': ('CH3CH2COONa', 'CH3CH2COOK'),
              'CH3(CH2)2COOH': ('CH3(CH2)2COONa', None), 'C6H5COOH': ('C6H5COONa', 'C6H5COOK'),
              'CH2CHCOOH': ('CH2CHCOONa', None), 'CH2C(CH3)COOH': (None, None)}
for ac, al, es in EST:
    R([ac, al], [es, 'H2O'], ['замещения', 'этерификации'], 'H2SO4 (конц.), t', rk=al, tags=['обратимая'])
    R([es, 'H2O'], [ac, al], ['гидролиза'], 'H+, t', rk='H2O', tags=['обратимая', 'кислотный гидролиз'])
    na, k = ESTER_SALT[ac]
    if na:
        R([es, 'NaOH'], [na, al], ['гидролиза'], 'водн. р-р, t', rk='NaOH', tags=['необратимая', 'щелочной гидролиз'])
    if k:
        R([es, 'KOH'], [k, al], ['гидролиза'], 'водн. р-р, t', rk='KOH', tags=['необратимая', 'щелочной гидролиз'])
R(['CH3COOC6H5', 'NaOH'], ['CH3COONa', 'C6H5ONa', 'H2O'], ['гидролиза'], 'водн. р-р, t', rk='NaOH',
  tags=['щелочной гидролиз', 'фенол связывает щёлочь'])
R(['CH3COOC6H5', 'KOH'], ['CH3COOK', 'C6H5OK', 'H2O'], ['гидролиза'], 'водн. р-р, t', rk='KOH', tags=['щелочной гидролиз'])
R(['CH3COOC6H5', 'H2O'], ['CH3COOH', 'C6H5OH'], ['гидролиза'], 'H+, t', rk='H2O')
R(['CH3COOCHCH2', 'NaOH'], ['CH3COONa', 'CH3CHO'], ['гидролиза'], 'водн. р-р, t', rk='NaOH',
  tags=['виниловый спирт изомеризуется в альдегид'])
R(['CH3COOCHCH2', 'KOH'], ['CH3COOK', 'CH3CHO'], ['гидролиза'], 'водн. р-р, t', rk='KOH')
R(['CH3COOCHCH2', 'H2O'], ['CH3COOH', 'CH3CHO'], ['гидролиза'], 'H+, t', rk='H2O')
for es in ['HCOOCH3', 'HCOOC2H5', 'HCOOCH2CH2CH3']:
    F([es, 'Ag(NH3)2OH'], ['серебро'], ['окисления', 'ОВР'], 't', rk='AgNH3', sign='серебряное зеркало',
      note='эфиры муравьиной кислоты содержат альдегидную группу')
for es in ['CH2CHCOOCH3', 'CH2C(CH3)COOCH3', 'CH3COOCHCH2']:
    F([es, 'Br2'], ['продукт присоединения брома'], ['присоединения'], 'бромная вода', rk='Br2aq',
      sign='обесцвечивание бромной воды')
R(['CH2CHCOOCH3', 'H2'], ['CH3CH2COOCH3'], ['присоединения', 'гидрирования'], 'Ni, t')
# жиры
FAT = [  # жир, кислота, Na-соль, K-соль, + nH2 → жир
    ('(C17H35COO)3C3H5', 'C17H35COOH', 'C17H35COONa', 'C17H35COOK', None),
    ('(C15H31COO)3C3H5', 'C15H31COOH', 'C15H31COONa', 'C15H31COOK', None),
    ('(C17H33COO)3C3H5', 'C17H33COOH', 'C17H33COONa', 'C17H33COOK', '(C17H35COO)3C3H5'),
    ('(C17H31COO)3C3H5', 'C17H31COOH', 'C17H31COONa', None, '(C17H35COO)3C3H5'),
]
for fat, ac, na, k, hyd in FAT:
    R([ac, 'C3H5(OH)3'], [fat, 'H2O'], ['замещения', 'этерификации'], 'H2SO4 (конц.), t', rk='C3H5(OH)3')
    R([fat, 'H2O'], [ac, 'C3H5(OH)3'], ['гидролиза'], 'H+, t', rk='H2O', tags=['кислотный гидролиз жира'])
    R([fat, 'NaOH'], [na, 'C3H5(OH)3'], ['гидролиза', 'омыления'], 'водн. р-р, t', rk='NaOH', tags=['омыление жира'])
    if k:
        R([fat, 'KOH'], [k, 'C3H5(OH)3'], ['гидролиза', 'омыления'], 'водн. р-р, t', rk='KOH', tags=['омыление жира'])
    if hyd:
        R([fat, 'H2'], [hyd], ['присоединения', 'гидрирования'], 'Ni, t, p', tags=['гидрогенизация жиров (маргарин)'])
for fat in ['(C17H33COO)3C3H5', '(C17H31COO)3C3H5']:
    F([fat, 'Br2'], ['продукт присоединения брома'], ['присоединения'], 'бромная вода', rk='Br2aq',
      sign='обесцвечивание бромной воды')
    F([fat, 'KMnO4'], ['продукты окисления'], ['окисления'], 'р-р', rk='KMnO4', sign='обесцвечивание раствора KMnO4')

# ---------------------------------------------------------------- амины
AMN = [  # амин, хлорид, бромид
    ('CH3NH2', 'CH3NH3Cl', 'CH3NH3Br'), ('(CH3)2NH', '(CH3)2NH2Cl', None), ('(CH3)3N', '(CH3)3NHCl', None),
    ('C2H5NH2', 'C2H5NH3Cl', 'C2H5NH3Br'), ('(C2H5)2NH', '(C2H5)2NH2Cl', None), ('C6H5NH2', 'C6H5NH3Cl', None),
    ('CH3CH2CH2NH2', 'CH3CH2CH2NH3Cl', None), ('(CH3)2CHNH2', '(CH3)2CHNH3Cl', None), ('CH3NHC2H5', 'CH3NH2C2H5Cl', None),
    ('(C2H5)3N', '(C2H5)3NHCl', None),
]
for am, cl, br in AMN:
    R([am, 'HCl'], [cl], ['соединения'], '', tags=['основные свойства аминов'])
    if br:
        R([am, 'HBr'], [br], ['соединения'], '', tags=['основные свойства аминов'])
    R([cl, 'NaOH'], [am, 'NaCl', 'H2O'], ['обмена'], '', tags=['вытеснение амина щёлочью'])
    R([cl, 'KOH'], [am, 'KCl', 'H2O'], ['обмена'], '', tags=['вытеснение амина щёлочью'])
R(['CH3NH2', 'H2SO4'], ['(CH3NH3)2SO4'], ['соединения'], '', tags=['основные свойства аминов'])
R(['C6H5NH2', 'H2SO4'], ['C6H5NH3HSO4'], ['соединения'], '', tags=['основные свойства аминов'])
R(['CH3NH2', 'HNO3'], ['CH3NH3NO3'], ['соединения'], '', tags=['основные свойства аминов'])
R(['C6H5NH2', 'Br2'], ['C6H2Br3NH2', 'HBr'], ['замещения', 'галогенирования'], 'бромная вода', rk='Br2aq',
  sign='обесцвечивание бромной воды, белый осадок', tags=['орто-, пара-ориентант'])
R(['C6H5NO2', 'H2'], ['C6H5NH2', 'H2O'], ['восстановления'], 'Ni (Pt), t', tags=['реакция Зинина'])
R(['C6H5NO2', 'Fe', 'HCl'], ['C6H5NH3Cl', 'FeCl2', 'H2O'], ['восстановления', 'ОВР'], 'HCl', rk='Fe+HCl',
  tags=['реакция Зинина'])
R(['C6H5NO2', 'Zn', 'HCl'], ['C6H5NH3Cl', 'ZnCl2', 'H2O'], ['восстановления', 'ОВР'], 'HCl', rk='Zn+HCl',
  tags=['реакция Зинина'])
R(['CH3NO2', 'H2'], ['CH3NH2', 'H2O'], ['восстановления'], 'Ni, t')
F(['CH3NH2', 'H2O'], ['гидроксид метиламмония'], ['соединения'], '', rk='H2O', note='раствор имеет щелочную среду')
F(['C2H5NH2', 'H2O'], ['гидроксид этиламмония'], ['соединения'], '', rk='H2O', note='раствор имеет щелочную среду')
F(['(CH3)2NH', 'H2O'], ['гидроксид диметиламмония'], ['соединения'], '', rk='H2O', note='раствор имеет щелочную среду')

# ---------------------------------------------------------------- аминокислоты, пептиды
R(['H2NCH2COOH', 'NaOH'], ['H2NCH2COONa', 'H2O'], ['обмена', 'нейтрализации'], '', tags=['амфотерность'])
R(['H2NCH2COOH', 'KOH'], ['H2NCH2COOK', 'H2O'], ['обмена', 'нейтрализации'], '', tags=['амфотерность'])
R(['H2NCH2COOH', 'HCl'], ['ClH3NCH2COOH'], ['соединения'], '', tags=['амфотерность'])
R(['CH3CH(NH2)COOH', 'NaOH'], ['CH3CH(NH2)COONa', 'H2O'], ['обмена', 'нейтрализации'], '', tags=['амфотерность'])
R(['H2NCH2CH2COOH', 'NaOH'], ['H2NCH2CH2COONa', 'H2O'], ['обмена', 'нейтрализации'], '', tags=['амфотерность'])
R(['CH3CH(NH2)COOH', 'HCl'], ['CH3CH(NH3Cl)COOH'], ['соединения'], '', tags=['амфотерность'])
R(['H2NCH2COOH', 'Na'], ['H2NCH2COONa', 'H2'], ['замещения', 'ОВР'], '')
R(['H2NCH2COOH', 'NaHCO3'], ['H2NCH2COONa', 'CO2', 'H2O'], ['обмена'], '', sign='выделение газа')
R(['H2NCH2COOH', 'CH3OH'], ['H2NCH2COOCH3', 'H2O'], ['замещения', 'этерификации'], 'HCl (газ), t')
R(['H2NCH2COOH', 'C2H5OH'], ['H2NCH2COOC2H5', 'H2O'], ['замещения', 'этерификации'], 'HCl (газ), t')
R(['CH3CH(NH2)COOH', 'CH3OH'], ['CH3CH(NH2)COOCH3', 'H2O'], ['замещения', 'этерификации'], 'HCl (газ), t')
R(['H2NCH2COOCH3', 'NaOH'], ['H2NCH2COONa', 'CH3OH'], ['гидролиза'], 'водн. р-р, t')
R(['H2NCH2COONa', 'HCl'], ['ClH3NCH2COOH', 'NaCl'], ['обмена'], 'избыток HCl')
R(['ClH3NCH2COOH', 'NaOH'], ['H2NCH2COONa', 'NaCl', 'H2O'], ['обмена'], 'избыток NaOH')
for a, b, d in [('H2NCH2COOH', 'H2NCH2COOH', 'H2NCH2CONHCH2COOH'),
                ('H2NCH2COOH', 'CH3CH(NH2)COOH', 'H2NCH2CONHCH(CH3)COOH'),
                ('CH3CH(NH2)COOH', 'H2NCH2COOH', 'CH3CH(NH2)CONHCH2COOH'),
                ('CH3CH(NH2)COOH', 'CH3CH(NH2)COOH', 'CH3CH(NH2)CONHCH(CH3)COOH')]:
    if a == b:
        R([a], [d, 'H2O'], ['поликонденсации', 'конденсации'], 't', rk='', tags=['образование пептидной связи'])
    else:
        R([a, b], [d, 'H2O'], ['поликонденсации', 'конденсации'], 't', rk=b, tags=['образование пептидной связи'])
    if a == b:
        R([d, 'H2O'], [a], ['гидролиза'], 'H+ или OH-, t', rk='H2O')
    else:
        R([d, 'H2O'], [a, b], ['гидролиза'], 'H+ или OH-, t', rk='H2O')
R(['H2NCH2CONHCH(CH3)COOH', 'NaOH'], ['H2NCH2COONa', 'CH3CH(NH2)COONa', 'H2O'], ['гидролиза'], 'водн. р-р, t', rk='NaOH')
R(['H2NCH2CONHCH2COOH', 'NaOH'], ['H2NCH2COONa', 'H2O'], ['гидролиза'], 'водн. р-р, t', rk='NaOH')
R(['H2NCH2CONHCH2COOH', 'HCl', 'H2O'], ['ClH3NCH2COOH'], ['гидролиза'], 't', rk='HCl')
R(['H2NCH2CONHCH(CH3)COOH', 'HCl', 'H2O'], ['ClH3NCH2COOH', 'CH3CH(NH3Cl)COOH'], ['гидролиза'], 't', rk='HCl')
for pep in ['H2NCH2CONHCH2COOH', 'H2NCH2CONHCH(CH3)COOH', 'CH3CH(NH2)CONHCH2COOH', 'CH3CH(NH2)CONHCH(CH3)COOH']:
    F([pep, 'Cu(OH)2'], ['—'], ['качественная реакция'], 'NaOH', rk='Cu(OH)2biuret', qual=True,
      sign='дипептид биуретовую реакцию НЕ даёт (нужно ≥ 2 пептидных связей)', neg=True)

# ---------------------------------------------------------------- углеводы
R(['C6H12O6'], ['C2H5OH', 'CO2'], ['спиртовое брожение', 'разложения'], 'дрожжи (ферменты)', rk='',
  tags=['спиртовое брожение'])
R(['C6H12O6'], ['CH3(CH2)2COOH', 'CO2', 'H2'], ['маслянокислое брожение', 'разложения'], 'ферменты', rk='')
R(['C6H12O6', 'H2'], ['C6H8(OH)6'], ['присоединения', 'гидрирования', 'восстановления'], 'Ni, t')
R(['HOCH2(CHOH)3COCH2OH', 'H2'], ['C6H8(OH)6'], ['присоединения', 'гидрирования', 'восстановления'], 'Ni, t')
R(['C6H12O6', 'Ag2O'], ['C5H11O5COOH', 'Ag'], ['окисления', 'ОВР'], 'NH3 (р-р), t', rk='AgNH3', sign='серебряное зеркало',
  tags=['реакция «серебряного зеркала»'])
R(['C6H12O6', 'Ag(NH3)2OH'], ['C5H11O5COONH4', 'Ag', 'NH3', 'H2O'], ['окисления', 'ОВР'], 't', rk='AgNH3',
  sign='серебряное зеркало')
R(['C6H12O6', 'Cu(OH)2'], ['C5H11O5COOH', 'Cu2O', 'H2O'], ['окисления', 'ОВР'], 't', sign='красный осадок Cu2O')
R(['C6H12O6', 'Br2', 'H2O'], ['C5H11O5COOH', 'HBr'], ['окисления', 'ОВР'], 'бромная вода', rk='Br2aq',
  sign='обесцвечивание бромной воды')
R(['CO2', 'H2O'], ['C6H12O6', 'O2'], ['фотосинтеза'], 'hv, хлорофилл', rk='H2O', tags=['фотосинтез'])
F(['C12H22O11', 'H2O'], ['C6H12O6', 'HOCH2(CHOH)3COCH2OH'], ['гидролиза'], 'H+, t', rk='H2O',
  eq='C12H22O11 + H2O → C6H12O6 (глюкоза) + C6H12O6 (фруктоза)', why='продукты — изомеры: баланс атомов не различает их')
R(['(C6H11O5)2O', 'H2O'], ['C6H12O6'], ['гидролиза'], 'H+, t', rk='H2O', note='продукт — глюкоза')
R(['C6H10O5', 'H2O'], ['C6H12O6'], ['гидролиза'], 'H+ (ферменты), t', rk='H2O', note='уравнение — на одно звено')
R(['C6H7O2(OH)3', 'H2O'], ['C6H12O6'], ['гидролиза'], 'H+, t', rk='H2O', note='уравнение — на одно звено')
R(['C6H7O2(OH)3', 'HNO3'], ['C6H7O2(ONO2)3', 'H2O'], ['замещения', 'этерификации'], 'H2SO4 (конц.)',
  tags=['получение пироксилина'], note='на одно звено')
F(['C6H7O2(OH)3', '(CH3CO)2O'], ['C6H7O2(OCOCH3)3', 'CH3COOH'], ['замещения', 'этерификации'], 'H2SO4',
  rk='(CH3CO)2O', eq='[C6H7O2(OH)3]n + 3n(CH3CO)2O → [C6H7O2(OCOCH3)3]n + 3nCH3COOH', why='баланс по C, H, O неоднозначен')
F(['C6H7O2(OH)3', 'CH3COOH'], ['C6H7O2(OCOCH3)3', 'H2O'], ['замещения', 'этерификации'], 'H2SO4 (конц.)',
  rk='CH3COOH', eq='[C6H7O2(OH)3]n + 3nCH3COOH → [C6H7O2(OCOCH3)3]n + 3nH2O', why='баланс по C, H, O неоднозначен')
for sug in ['C6H12O6', 'HOCH2(CHOH)3COCH2OH', 'C12H22O11', '(C6H11O5)2O']:
    F([sug, 'Cu(OH)2'], ['комплекс меди(II)'], ['комплексообразования'], 'без нагревания', rk='Cu(OH)2',
      sign='ярко-синий раствор', qual=True, note='многоатомный спирт')
F(['(C6H11O5)2O', 'Ag(NH3)2OH'], ['серебро'], ['окисления', 'ОВР'], 't', rk='AgNH3', sign='серебряное зеркало',
  note='мальтоза — восстанавливающий дисахарид')
F(['(C6H11O5)2O', 'Cu(OH)2'], ['Cu2O'], ['окисления', 'ОВР'], 't', rk='Cu(OH)2t', sign='красный осадок Cu2O')
F(['C6H10O5', 'I2'], ['окрашенный комплекс'], ['качественная реакция'], '', rk='I2', sign='синее окрашивание', qual=True)
F(['C6H10O5', 'H2O'], ['декстрины', 'мальтоза', 'глюкоза'], ['гидролиза'], 'ферменты', rk='H2O', note='ступенчатый гидролиз')

# ---------------------------------------------------------------- горение (полное, в избытке кислорода)
_BURN_HOM = {'алканы', 'циклоалканы', 'алкены', 'циклоалкены', 'алкадиены', 'циклоалкадиены', 'алкины', 'алкенины', 'арены',
             'арены (с непредельной боковой цепью)', 'предельные одноатомные спирты', 'многоатомные спирты', 'простые эфиры',
             'фенолы', 'предельные альдегиды', 'ароматические альдегиды', 'кетоны', 'циклические кетоны',
             'ароматические кетоны', 'предельные одноосновные карбоновые кислоты', 'сложные эфиры', 'предельные амины',
             'ароматические амины', 'аминокислоты', 'моносахариды', 'дисахариды', 'полисахариды', 'циклические спирты',
             'ароматические спирты', 'непредельные спирты', 'непредельные альдегиды', 'непредельные карбоновые кислоты',
             'ароматические карбоновые кислоты', 'двухосновные карбоновые кислоты', 'гидроксикислоты', 'жиры', 'дипептиды',
             'нитроалканы', 'нитроарены', 'высшие карбоновые кислоты', 'эфиры аминокислот'}
for _s in list(SUBSTANCES):
    if not _s.get('org') or _s['hom'] not in _BURN_HOM:
        continue
    _el = set(re.findall(r'[A-Z][a-z]?', _s['f']))
    if not _el <= {'C', 'H', 'O', 'N'}:
        continue
    R([_s['f'], 'O2'], ['CO2', 'H2O'] + (['N2'] if 'N' in _el else []), ['окисления', 'горения'], 't', rk='O2',
      tags=['полное сгорание'])

# ================================================================= «не реагирует» (проверенные школьные факты)
def _hom(*homs):
    return [s['f'] for s in SUBSTANCES if s.get('org') and s['hom'] in homs]


_ALKANES = _hom('алканы')
_CYCLO_BIG = ['(CH2)5', '(CH2)6', 'C5H9CH3', 'C6H11CH3', 'C5H9C2H5']
_ARENES_SAT = ['C6H6', 'C6H5CH3', 'C6H5C2H5', 'C6H4(CH3)2', '(CH3)2C6H4', 'CH3C6H4CH3', 'C6H5CH2CH2CH3',
               'C6H5CH(CH3)2', 'C6H3(CH3)3']
_ALKENES = _hom('алкены', 'циклоалкены', 'алкадиены', 'циклоалкадиены')
_MONO_ALC = _hom('предельные одноатомные спирты', 'циклические спирты')
_POLYOL = ['C2H4(OH)2', 'C3H5(OH)3']
_ETHERS = _hom('простые эфиры')
_KETONES = ['CH3COCH3', 'CH3COCH2CH3', 'CH3CO(CH2)2CH3', 'CH3CH2COCH2CH3', 'C6H10O']
_SAT_ACIDS = ['CH3COOH', 'CH3CH2COOH', 'CH3(CH2)2COOH', '(CH3)2CHCOOH', 'C17H35COOH', 'C15H31COOH', 'C6H5COOH']
_SAT_ESTERS = ['CH3COOCH3', 'CH3COOC2H5', 'CH3COOCH2CH2CH3', 'CH3CH2COOCH3', 'CH3CH2COOC2H5', 'CH3(CH2)2COOC2H5',
               'CH3COOCH(CH3)2']
_ALDEH = ['HCHO', 'CH3CHO', 'CH3CH2CHO', 'CH3(CH2)2CHO', '(CH3)2CHCHO', 'C6H5CHO']
_HALO = ['CH3Cl', 'C2H5Cl', 'C2H5Br', 'CH3CH2CH2Br', 'CH3CHBrCH3', 'CH2ClCH2Cl']
_SAT_FATS = ['(C17H35COO)3C3H5', '(C15H31COO)3C3H5']

NOT_REACT = set()


def _neg(rk, *groups):
    for g in groups:
        for f in g:
            NOT_REACT.add((f, rk))


_neg('Br2aq', _ALKANES, _CYCLO_BIG, _ARENES_SAT, _MONO_ALC, _POLYOL, _ETHERS, ['CH3COCH3', 'CH3COCH2CH3'], _SAT_ACIDS,
     _SAT_ESTERS, _SAT_FATS, _HALO, ['C12H22O11', 'C6H10O5', 'C6H7O2(OH)3', 'H2NCH2COOH', 'CH3CH(NH2)COOH', 'CCl4'])
_neg('KMnO4', _ALKANES, _CYCLO_BIG, ['(CH2)3', '(CH2)4', 'C6H6'], _SAT_ACIDS, ['(CH3)3COH'], _SAT_FATS, ['CCl4', 'CHCl3'])
_neg('H2', _ALKANES, _CYCLO_BIG, _MONO_ALC, _POLYOL, _SAT_ACIDS, _ETHERS, _SAT_FATS, ['CH3NH2'])
_neg('HCl', _ALKANES, _CYCLO_BIG, _ARENES_SAT, _SAT_ACIDS, ['C6H5OH'], ['CH3COCH3'])
_neg('HBr', _ALKANES, _CYCLO_BIG, _ARENES_SAT, _SAT_ACIDS, ['C6H5OH'])
_neg('Na', _ALKANES, _CYCLO_BIG, _ARENES_SAT, _ALKENES, _ETHERS, _SAT_ESTERS, ['CH3CCCH3', 'CH3COCH3'])
_neg('NaOH', _ALKANES, _CYCLO_BIG, _ARENES_SAT, _ALKENES, ['C2H2', 'CHCCH3', 'CH3CCCH3'], _MONO_ALC, _POLYOL, _ETHERS,
     ['CH3COCH3', 'CH3COCH2CH3'], ['C6H5NH2', 'CH3NH2', '(CH3)2NH', 'C2H5NH2', '(CH3)3N'])
_neg('NaHCO3', _ALKANES, _ARENES_SAT, _ALKENES, _MONO_ALC, _POLYOL, ['C6H5OH', 'CH3C6H4OH'], _ALDEH, _KETONES, _SAT_ESTERS,
     _ETHERS, _SAT_FATS)
_neg('Cu(OH)2', _ALKANES, _ARENES_SAT, _ALKENES, _MONO_ALC, _KETONES, _ETHERS)
_neg('AgNH3', _ALKANES, _CYCLO_BIG, _ARENES_SAT, _ALKENES, ['CH3CCCH3', 'CH3CCCH2CH3'], _MONO_ALC, _POLYOL, _KETONES,
     _SAT_ACIDS, _SAT_ESTERS, _SAT_FATS, _ETHERS, ['C6H5OH', 'C12H22O11', 'C6H10O5', 'C6H7O2(OH)3', 'H2NCH2COOH',
                                                    'CH3CH(NH2)COOH', 'C6H5NH2', 'CH3NH2'])
_neg('H2O', _ALKANES, _CYCLO_BIG, _ARENES_SAT, _MONO_ALC, _POLYOL, _ETHERS, ['C6H12O6', 'HOCH2(CHOH)3COCH2OH'])
_neg('CuO', ['(CH3)3COH', '(CH3)2C(OH)CH2CH3'], _ALKANES, _ARENES_SAT, _KETONES, _ETHERS)
_neg('C2H5OH', _ALKANES, _ARENES_SAT)
_neg('KOH', _ALKANES, _CYCLO_BIG, _ARENES_SAT, _ALKENES, _MONO_ALC, _POLYOL, _ETHERS, ['CH3COCH3'],
     ['C6H5NH2', 'CH3NH2', '(CH3)2NH', 'C2H5NH2', '(CH3)3N', '(C2H5)2NH'])
_neg('K', _ALKANES, _CYCLO_BIG, _ARENES_SAT, _ALKENES, _ETHERS, _SAT_ESTERS)
# азотсодержащие, углеводы, жиры
_AMINES = ['CH3NH2', '(CH3)2NH', '(CH3)3N', 'C2H5NH2', '(C2H5)2NH', '(C2H5)3N', 'CH3CH2CH2NH2', '(CH3)2CHNH2',
           'CH3NHC2H5', 'C6H5NH2', 'C6H5NHCH3']
_AAC = ['H2NCH2COOH', 'CH3CH(NH2)COOH']
_CARBS = ['C6H12O6', 'HOCH2(CHOH)3COCH2OH', 'C12H22O11', '(C6H11O5)2O', 'C6H10O5', 'C6H7O2(OH)3']
for _rk in ['NaCl', 'Na2SO4', 'KNO3', 'CH4', 'Cu', 'N2', 'KCl', 'Ag']:
    _neg(_rk, _AMINES, _AAC, _CARBS, _SAT_FATS, ['(C17H33COO)3C3H5'], _MONO_ALC, _SAT_ACIDS, _ALDEH, _ALKANES,
         _ARENES_SAT)
_neg('NaOH', ['(CH3)3N', '(C2H5)3N', 'CH3CH2CH2NH2', '(CH3)2CHNH2', 'CH3NHC2H5', 'C6H5NHCH3', '(C2H5)2NH'])
_neg('KOH', ['(C2H5)3N', 'CH3CH2CH2NH2', '(CH3)2CHNH2', 'CH3NHC2H5', 'C6H5NHCH3'])
_neg('NaHCO3', _AMINES)
_neg('H2', _AAC, ['C12H22O11', 'C6H10O5', 'C6H7O2(OH)3'])
_neg('AgNH3', ['CH3CH(NH2)COOH', '(CH3)2NH', 'C2H5NH2', '(C17H33COO)3C3H5'])
_neg('I2', ['C6H12O6', 'C12H22O11', 'C6H7O2(OH)3', 'H2NCH2COOH', 'CH3NH2', 'C6H5NH2'])
_neg('H2O', _AAC, ['C6H5NH2'])


# ================================================================= полимеры (задание 25, цепочки)
POLYMERS = [
    dict(name='полиэтилен', mon=['C2H4'], unit='-CH2-CH2-', how='полимеризация', kind='пластмасса (термопласт)',
         use=['плёнки', 'упаковка', 'трубы']),
    dict(name='полипропилен', mon=['CH2CHCH3'], unit='-CH2-CH(CH3)-', how='полимеризация', kind='пластмасса (термопласт)',
         use=['трубы', 'тара', 'волокна']),
    dict(name='поливинилхлорид', mon=['CH2CHCl'], unit='-CH2-CHCl-', how='полимеризация', kind='пластмасса (термопласт)',
         use=['линолеум', 'изоляция проводов', 'искусственная кожа'], trivial=['ПВХ']),
    dict(name='полистирол', mon=['C6H5CHCH2'], unit='-CH2-CH(C6H5)-', how='полимеризация', kind='пластмасса (термопласт)',
         use=['пенопласт', 'одноразовая посуда']),
    dict(name='политетрафторэтилен', mon=['CF2CF2'], unit='-CF2-CF2-', how='полимеризация', kind='пластмасса (термопласт)',
         use=['антипригарные покрытия', 'химически стойкая аппаратура'], trivial=['тефлон']),
    dict(name='полиметилметакрилат', mon=['CH2C(CH3)COOCH3'], unit='-CH2-C(CH3)(COOCH3)-', how='полимеризация',
         kind='пластмасса (термопласт)', use=['органическое стекло'], trivial=['оргстекло', 'плексиглас']),
    dict(name='полиакрилонитрил', mon=['CH2CHCN'], unit='-CH2-CH(CN)-', how='полимеризация', kind='синтетическое волокно',
         use=['нитрон — «искусственная шерсть»'], trivial=['нитрон']),
    dict(name='поливинилацетат', mon=['CH3COOCHCH2'], unit='-CH2-CH(OCOCH3)-', how='полимеризация', kind='пластмасса',
         use=['клей ПВА', 'краски']),
    dict(name='бутадиеновый каучук', mon=['CH2CHCHCH2'], unit='-CH2-CH=CH-CH2-', how='полимеризация', kind='каучук',
         use=['резина', 'шины']),
    dict(name='изопреновый каучук', mon=['CH2C(CH3)CHCH2'], unit='-CH2-C(CH3)=CH-CH2-', how='полимеризация', kind='каучук',
         use=['резина'], trivial=['натуральный каучук']),
    dict(name='хлоропреновый каучук', mon=['CH2CClCHCH2'], unit='-CH2-CCl=CH-CH2-', how='полимеризация', kind='каучук',
         use=['маслобензостойкие изделия']),
    dict(name='бутадиен-стирольный каучук', mon=['CH2CHCHCH2', 'C6H5CHCH2'], unit='-CH2-CH=CH-CH2-CH2-CH(C6H5)-',
         how='сополимеризация', kind='каучук', use=['шины']),
    dict(name='капрон', mon=['H2N(CH2)5COOH'], unit='-NH-(CH2)5-CO-', how='поликонденсация',
         kind='синтетическое волокно (полиамидное)', use=['ткани', 'канаты', 'чулки']),
    dict(name='найлон', mon=['H2N(CH2)6NH2', 'HOOC(CH2)4COOH'], unit='-NH-(CH2)6-NH-CO-(CH2)4-CO-', how='поликонденсация',
         kind='синтетическое волокно (полиамидное)', use=['ткани', 'детали машин'], trivial=['анид']),
    dict(name='лавсан', mon=['HOOCC6H4COOH', 'C2H4(OH)2'], unit='-O-CH2-CH2-O-CO-C6H4-CO-', how='поликонденсация',
         kind='синтетическое волокно (полиэфирное)', use=['ткани', 'пластиковые бутылки (ПЭТ)'], trivial=['полиэтилентерефталат']),
    dict(name='фенолформальдегидная смола', mon=['C6H5OH', 'HCHO'], unit='-C6H2(OH)-CH2-', how='поликонденсация',
         kind='пластмасса (термореактивная)', use=['карболиты', 'электротехнические изделия']),
    dict(name='крахмал', mon=['C6H12O6'], unit='-C6H10O5-', how='поликонденсация (в природе)', kind='природный полимер',
         use=['пищевой продукт', 'клей']),
    dict(name='целлюлоза', mon=['C6H12O6'], unit='-C6H10O5-', how='поликонденсация (в природе)', kind='природный полимер',
         use=['бумага', 'хлопок', 'искусственные волокна']),
]
FIBERS = {  # волокно → класс
    'хлопок': 'природное (растительное)', 'лён': 'природное (растительное)', 'шерсть': 'природное (животное)',
    'натуральный шёлк': 'природное (животное)', 'вискоза': 'искусственное', 'ацетатное волокно': 'искусственное',
    'капрон': 'синтетическое', 'нитрон': 'синтетическое', 'лавсан': 'синтетическое', 'найлон': 'синтетическое',
}


# ================================================================= собственные проверки модуля
def positives():
    """(f, rk) из реакций и фактов: субстрат lhs[0] реагирует с реагентом rk."""
    pos = set()
    for r in REACTIONS + [x for x in FACTS if not x.get('neg')]:
        if r['rk']:
            pos.add((r['lhs'][0], r['rk']))
    return pos


def self_check():
    from pc_core import parse_formula, balance, check_balance
    problems = []
    fs = {s['f'] for s in SUBSTANCES}
    for f, smi in SMILES.items():
        a = smiles_info(smi)['atoms']
        if a != Counter(parse_formula(f)):
            problems.append(f'SMILES {smi} ≠ {f}')
    for r in REACTIONS:
        for f in r['lhs'] + r['rhs']:
            if f not in fs:
                problems.append(f'нет вещества {f} ({r["lhs"]}→{r["rhs"]})')
        try:
            kl, kr = balance(r['lhs'], r['rhs'])
            if not check_balance(r['lhs'], r['rhs'], kl, kr):
                problems.append(f'не уравнено {r["lhs"]}')
        except Exception as ex:  # noqa: BLE001
            problems.append(f'{r["lhs"]}→{r["rhs"]}: {ex}')
    for r in FACTS:
        for f in r['lhs']:
            if f not in fs:
                problems.append(f'факт: нет вещества {f}')
    pos = positives()
    for f, rk in sorted(NOT_REACT & pos):
        problems.append(f'противоречие: {f} + {rk} и «реагирует», и «не реагирует»')
    for f, rk in NOT_REACT:
        if f not in fs:
            problems.append(f'NOT_REACT: нет вещества {f}')
    for p in POLYMERS:
        for f in p['mon']:
            if f not in fs:
                problems.append(f'полимер {p["name"]}: нет мономера {f}')
    return problems


if __name__ == '__main__':
    pr = self_check()
    org = [s for s in SUBSTANCES if s.get('org')]
    print(f'органических веществ {len(org)}, реакций {len(REACTIONS)}, фактов {len(FACTS)}, '
          f'«не реагирует» {len(NOT_REACT)}, полимеров {len(POLYMERS)}; проблем {len(pr)}')
    for p in pr[:40]:
        print(' -', p)
