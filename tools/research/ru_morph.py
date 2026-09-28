"""Русская морфология для формулировок карточек: согласование с числом и склонение словосочетаний.

Использует pymorphy3 (pip install pymorphy3 pymorphy3-dicts-ru). Если библиотеки нет — возвращает слова как есть,
генератор работает, но формулировки будут менее гладкими.
"""
import re

try:
    import pymorphy3
    _M = pymorphy3.MorphAnalyzer()
except Exception:                      # библиотеки нет — без склонения
    _M = None

CASES = {'nomn', 'gent', 'datv', 'accs', 'ablt', 'loct'}
# формы, которые pymorphy склоняет неверно (собирательное мн. число и т. п.)
IRREG = {'листья': {'gent': 'листьев', 'datv': 'листьям', 'accs': 'листья', 'ablt': 'листьями', 'loct': 'листьях'},
         'корни': {'gent': 'корней', 'datv': 'корням', 'accs': 'корни', 'ablt': 'корнями', 'loct': 'корнях'}}


def _best(word, want=('NOUN',)):
    for p in _M.parse(word):
        if p.tag.POS in want:
            return p
    return None


def agree(n, word, case='nomn'):
    """«24 хромосомы», «1 замена», «74 различия»; case='gent' — «из 501 аминокислоты», «из 24 аминокислот»."""
    if _M is None:
        return f'{n} {word}'
    p = _best(word, ('NOUN',))
    if p is None:
        return f'{n} {word}'
    if case != 'nomn':
        k = abs(int(n))
        w = p.inflect({case, 'sing' if k % 10 == 1 and k % 100 != 11 else 'plur'})
        return f'{n} {w.word if w else word}'
    w = p.make_agree_with_number(abs(int(n)))
    return f'{n} {w.word if w else word}'


def inflect(phrase, case, number=None):
    """Склоняет именную группу: определения и главное существительное до первого существительного;
    зависимые слова после него (родительный падеж, предлоги, скобки) не трогает. «шероховатая ЭПС» → «шероховатой ЭПС»."""
    if _M is None or case not in CASES or not phrase:
        return phrase
    words = re.split(r'(\s+)', phrase)
    # главное существительное: первое слово, у которого среди двух лучших разборов нет прилагательного
    head, gender, num, anim = None, None, None, None
    for i, w in enumerate(words):
        if not w.strip():
            continue
        if re.match(r'^[«(\[]', w):
            break
        ps = _M.parse(re.sub(r'[^\w-]', '', w).lower())
        if any(x.tag.POS in ('ADJF', 'PRTF') for x in ps[:2]):
            continue
        p = next((x for x in ps if x.tag.POS in ('NOUN', 'NPRO') and x.tag.case == 'nomn'), None)
        if p:
            head, gender, num, anim = i, p.tag.gender, p.tag.number, p.tag.animacy
        break
    if head is None:                   # аббревиатура («ЭПС») — главное слово последнее перед скобкой/предлогом
        ws = [i for i, w in enumerate(words) if w.strip() and not re.match(r'^[«(\[]', w)]
        adj = [i for i in ws if any(x.tag.POS in ('ADJF', 'PRTF') for x in _M.parse(re.sub(r'[^\w-]', '', words[i]).lower())[:2])]
        if not adj:
            return phrase
        head = adj[-1] + 1 if len(ws) >= 2 and adj[-1] + 1 < len(words) else None
        if head is None:                   # субстантивированное прилагательное («земноводные») — склоняем как прилагательное
            p = next(x for x in _M.parse(re.sub(r'[^\w-]', '', words[adj[0]]).lower()) if x.tag.POS in ('ADJF', 'PRTF'))
            feats = {case} | ({'plur'} if p.tag.number == 'plur' else {p.tag.gender or 'masc'})
            if case == 'accs':
                feats.add('anim')
            r = p.inflect(feats)
            return phrase.replace(words[adj[0]].strip(), r.word) if r else phrase
        p = next(x for x in _M.parse(re.sub(r'[^\w-]', '', words[adj[0]]).lower()) if x.tag.POS in ('ADJF', 'PRTF'))
        gender, num, anim = p.tag.gender, p.tag.number, 'inan'
    out = []
    for i, w in enumerate(words):
        if i > head or not w.strip():
            out.append(w)
            continue
        m = re.match(r'^([\w-]+)(.*)$', w)
        if not m:
            out.append(w)
            continue
        core, tail = m.groups()
        if len(core) > 1 and sum(ch.isupper() for ch in core) >= 2:   # аббревиатура (США, ЭПС, рРНК) — не склоняется
            out.append(w)
            continue
        if core.lower() in IRREG:
            out.append(IRREG[core.lower()].get(case, core) + tail)
            continue
        want = ('NOUN', 'NPRO') if i == head else ('ADJF', 'PRTF')
        parsed = next((x for x in _M.parse(core.lower()) if x.tag.POS in want and x.tag.case == 'nomn'), None)
        if parsed is None:
            out.append(w)
            continue
        feats = {case}
        if number:
            feats.add(number)
        if i != head:
            if (number or num) == 'plur':
                feats.add('plur')
            elif gender:
                feats.add(gender)
            if case == 'accs' and anim:
                feats.add(anim)
        r = parsed.inflect(feats) or parsed.inflect({case})
        new = r.word if r else core.lower()
        if core[:1].isupper():
            new = new[:1].upper() + new[1:]
        out.append(new + tail)
    return ''.join(out)


def plural_of(phrase):
    """Число главного существительного: 'plur' или 'sing'."""
    if _M is None:
        return 'sing'
    for w in re.findall(r'[\w-]+', phrase):
        ps = [x for x in _M.parse(w.lower()) if x.tag.POS == 'NOUN' and x.tag.case == 'nomn']
        if any(x.tag.POS in ('ADJF', 'PRTF') for x in _M.parse(w.lower())[:2]):
            continue
        if ps:
            nums = {x.tag.number for x in ps}
            return 'sing' if 'sing' in nums and 'plur' not in nums else 'plur' if 'plur' in nums and 'sing' not in nums else ps[0].tag.number or 'sing'
    for w in re.findall(r'[\w-]+', phrase):          # только прилагательные («голосеменные») — по их числу
        a = next((x for x in _M.parse(w.lower()) if x.tag.POS in ('ADJF', 'PRTF') and x.tag.case == 'nomn'), None)
        if a:
            return a.tag.number or 'sing'
    return 'sing'


def predicate(subject, pred):
    """Предложение «подлежащее + сказуемое» с согласованием числа глагола: «Эритроциты переносят кислород»."""
    subj = subject[:1].upper() + subject[1:]
    words = pred.split(' ', 1)
    if _M is None:
        return f'{subj} — {pred}'
    first = words[0]
    p = None
    for x in _M.parse(first.lower()):
        if x.tag.POS in ('VERB', 'PRTS', 'ADJS'):
            p = x
            break
    if p is None:
        return f'{subj} — {pred}'
    num = plural_of(subject)
    if p.tag.number and p.tag.number != num:
        r = p.inflect({num}) if p.tag.POS != 'VERB' else p.inflect({num, '3per'} if p.tag.person else {num})
        if r:
            first = r.word
    return f'{subj} {first}' + (' ' + words[1] if len(words) > 1 else '')


def short_adj(subject, adj):
    """Краткое прилагательное в роде/числе подлежащего: («число бактерий», «максимальный») → «максимально»."""
    if _M is None:
        return adj
    num, gender = 'sing', 'masc'
    for w in re.findall(r'[\w-]+', subject):
        ps = _M.parse(w.lower())
        if any(x.tag.POS in ('ADJF', 'PRTF') for x in ps[:2]):
            continue
        p = next((x for x in ps if x.tag.POS == 'NOUN' and x.tag.case == 'nomn'), None)
        if p:
            num, gender = p.tag.number or 'sing', p.tag.gender or 'masc'
        break
    p = _best(adj, ('ADJF',))
    if p is None:
        return adj
    r = p.inflect({'ADJS', 'plur'} if num == 'plur' else {'ADJS', gender, 'sing'})
    return r.word if r else adj


def ob(word_loct):
    """Предлог «о/об» перед словом в предложном падеже: «об общей», «о клетке»."""
    return ('об ' if word_loct[:1].lower() in 'аоуэиы' else 'о ') + word_loct


def which(noun):
    """«Какой/Какая/Какое/Какие» по роду и числу существительного."""
    if _M is None:
        return 'Какой'
    p = _best(noun.split()[-1].lower(), ('NOUN',))
    if p is None:
        return 'Какой'
    if p.tag.number == 'plur':
        return 'Какие'
    return {'femn': 'Какая', 'neut': 'Какое'}.get(p.tag.gender, 'Какой')
