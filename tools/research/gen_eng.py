#!/usr/bin/env python3
"""Прототип генератора карточек по английскому (ЕГЭ 19–29, ОГЭ 20–34) на шаблонах — исследование, не сборка.

Запуск:
  python3 tools/research/gen_eng.py            # самопроверка
  python3 tools/research/gen_eng.py --show 3   # по 3 примера каждого типа
  python3 tools/research/gen_eng.py --dump out.json

Что внутри: собственные таблицы форм (неправильные глаголы, множественное число, степени сравнения,
местоимения, порядковые) и собственные предложения-рамки. Тексты ФИПИ и коммерческих банков не используются.
Ответ считает правило, вторая независимая реализация правила (check_*) должна дать тот же ответ.

Формат карточки — как в tools/build_packs.py; `k: 'text'` — ПРЕДЛАГАЕМЫЙ тип (точная строка, сравнение без
регистра и пробелов, как в бланке № 1). `a` — список допустимых ответов, первый — основной
(has found / 's found — в ключах ФИПИ тоже по два варианта).

Предел шаблонов — разнообразие рамок: грамматика даёт тысячи уникальных условий, но однотипных.
Для живых предложений нужен llm (см. docs/research/inf-eng.md), ответ при этом всё равно считает правило.
"""
import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter

SRC = 'Генератор «Между уроками» (собственные предложения)'


def card(t, k, q, a, e, o=None):
    c = {'id': '', 't': t, 'k': k, 'q': q, 'a': a, 'e': e}
    if o is not None:
        c['o'] = o
    c['src'] = SRC
    c['id'] = t + '-' + hashlib.sha1((q + '|' + json.dumps(a, ensure_ascii=False)).encode()).hexdigest()[:10]
    return c


def gap(before, word, after=''):
    return f'{before} ____ {after}'.strip() + f'  ({word.upper()})'


# ---------------------------------------------------------------- таблицы (факты языка, собраны вручную)

IRREGULAR = {  # base: (past, participle)
    'be': ('was/were', 'been'), 'begin': ('began', 'begun'), 'break': ('broke', 'broken'),
    'bring': ('brought', 'brought'), 'build': ('built', 'built'), 'buy': ('bought', 'bought'),
    'catch': ('caught', 'caught'), 'choose': ('chose', 'chosen'), 'come': ('came', 'come'),
    'do': ('did', 'done'), 'draw': ('drew', 'drawn'), 'drink': ('drank', 'drunk'), 'drive': ('drove', 'driven'),
    'eat': ('ate', 'eaten'), 'fall': ('fell', 'fallen'), 'feel': ('felt', 'felt'), 'find': ('found', 'found'),
    'fly': ('flew', 'flown'), 'forget': ('forgot', 'forgotten'), 'get': ('got', 'got'), 'give': ('gave', 'given'),
    'go': ('went', 'gone'), 'grow': ('grew', 'grown'), 'have': ('had', 'had'), 'hear': ('heard', 'heard'),
    'hide': ('hid', 'hidden'), 'keep': ('kept', 'kept'), 'know': ('knew', 'known'), 'leave': ('left', 'left'),
    'lend': ('lent', 'lent'), 'lose': ('lost', 'lost'), 'make': ('made', 'made'), 'meet': ('met', 'met'),
    'pay': ('paid', 'paid'), 'put': ('put', 'put'), 'read': ('read', 'read'), 'ride': ('rode', 'ridden'),
    'ring': ('rang', 'rung'), 'run': ('ran', 'run'), 'say': ('said', 'said'), 'see': ('saw', 'seen'),
    'sell': ('sold', 'sold'), 'send': ('sent', 'sent'), 'sing': ('sang', 'sung'), 'sit': ('sat', 'sat'),
    'sleep': ('slept', 'slept'), 'speak': ('spoke', 'spoken'), 'spend': ('spent', 'spent'),
    'steal': ('stole', 'stolen'), 'swim': ('swam', 'swum'), 'take': ('took', 'taken'), 'teach': ('taught', 'taught'),
    'tell': ('told', 'told'), 'think': ('thought', 'thought'), 'throw': ('threw', 'thrown'),
    'understand': ('understood', 'understood'), 'wear': ('wore', 'worn'), 'win': ('won', 'won'),
    'write': ('wrote', 'written'),
}

# глагол + дополнение: рамки подобраны так, чтобы сочетание было естественным
VERB_OBJ = [
    ('write', 'a long letter to our cousins'), ('buy', 'fresh bread at the corner shop'),
    ('read', 'an article about volcanoes'), ('lose', 'the keys to the garage'), ('find', 'a strange old coin'),
    ('bring', 'sandwiches for the whole team'), ('meet', 'an old friend at the station'),
    ('teach', 'the younger kids to play chess'), ('catch', 'the last bus home'), ('draw', 'a map of the park'),
    ('sell', 'the old bicycle online'), ('send', 'the photos to the organisers'), ('win', 'the school quiz'),
    ('build', 'a treehouse in the garden'), ('choose', 'a present for Grandma'), ('forget', 'the password again'),
    ('hide', 'the presents under the bed'), ('lend', 'his notes to a classmate'), ('wear', 'a funny hat'),
    ('visit', 'the science museum'), ('watch', 'a documentary about whales'), ('cook', 'pancakes for breakfast'),
    ('paint', 'the fence green'), ('clean', 'the kitchen after the party'), ('plan', 'a trip to the mountains'),
    ('stop', 'the car near the bridge'), ('study', 'the history of the city'), ('carry', 'the heavy boxes upstairs'),
    ('enjoy', 'the concert in the park'), ('fix', 'the broken chair'), ('invite', 'the neighbours to dinner'),
    ('try', 'the new Georgian cafe'), ('wash', 'the dishes without complaining'), ('practise', 'the new song'),
    ('decorate', 'the classroom for the holiday'), ('miss', 'the beginning of the film'),
    ('organise', 'a charity fair'), ('answer', 'all the questions correctly'), ('repair', 'the old radio'),
    ('translate', 'the instructions into Russian'),
]

# моментальные действия не ставим в Continuous: «were finding a coin» грамматично, но неестественно
MOMENT = {'find', 'lose', 'win', 'forget', 'catch', 'miss', 'stop', 'choose', 'meet', 'hide', 'send', 'answer',
          'invite', 'lend', 'sell', 'buy', 'try'}

SUBJECTS = [('I', '1'), ('you', 'pl'), ('we', 'pl'), ('they', 'pl'), ('he', '3'), ('she', '3'),
            ('my brother', '3'), ('Anna', '3'), ('our neighbours', 'pl'), ('the twins', 'pl'),
            ('my best friend', '3'), ('Mr Petrov', '3')]
PRONOUN = {'I', 'you', 'we', 'they', 'he', 'she'}

PAST_MARK = ['Yesterday', 'Last Saturday', 'Two days ago', 'In 2019', 'Last summer', 'The day before yesterday']
FUT_MARK = ['Tomorrow', 'Next weekend', 'In a few days', 'Next summer']
PRES_MARK = ['Every Sunday', 'Usually', 'Twice a month', 'On Fridays']


# ---------------------------------------------------------------- морфология: основная реализация (посимвольно)

VOW = 'aeiou'


def cvc_double(v):
    """Удваивать ли последнюю согласную: stop → stopped, plan → planned; visit, open — нет (ударение не на конце)."""
    return v in {'stop', 'plan', 'swim', 'run', 'sit', 'win', 'get', 'begin', 'forget', 'shop', 'drop'}


def past(v):
    if v in IRREGULAR:
        return IRREGULAR[v][0]
    if v.endswith('e'):
        return v + 'd'
    if v.endswith('y') and v[-2] not in VOW:
        return v[:-1] + 'ied'
    if cvc_double(v):
        return v + v[-1] + 'ed'
    return v + 'ed'


def participle(v):
    return IRREGULAR[v][1] if v in IRREGULAR else past(v)


def third(v):
    if v == 'have':
        return 'has'
    if v in ('go', 'do'):
        return v + 'es'
    if v.endswith(('s', 'x', 'ch', 'sh', 'z')):
        return v + 'es'
    if v.endswith('y') and v[-2] not in VOW:
        return v[:-1] + 'ies'
    return v + 's'


def ing(v):
    if v.endswith('ie'):
        return v[:-2] + 'ying'
    if v.endswith('e') and not v.endswith('ee') and v != 'be':
        return v[:-1] + 'ing'
    if cvc_double(v):
        return v + v[-1] + 'ing'
    return v + 'ing'


# ---------------------------------------------------------------- морфология: вторая реализация (регулярные выражения)

IRR_LINES = '\n'.join(f'{b} {p} {pp}' for b, (p, pp) in IRREGULAR.items())
DOUBLE = re.compile(r'^(stop|plan|swim|run|sit|win|get|begin|forget|shop|drop)$')


def past2(v):
    m = re.search(rf'^{v} (\S+) \S+$', IRR_LINES, re.M)
    if m:
        return m.group(1)
    if DOUBLE.match(v):
        return v + v[-1] + 'ed'
    return re.sub(r'e$', 'ed', v) if v.endswith('e') else re.sub(r'([^aeiou])y$', r'\1ied', v) if re.search(
        r'[^aeiou]y$', v) else v + 'ed'


def participle2(v):
    m = re.search(rf'^{v} \S+ (\S+)$', IRR_LINES, re.M)
    return m.group(1) if m else past2(v)


def third2(v):
    for pat, rep in ((r'^have$', 'has'), (r'^(go|do)$', r'\1es'), (r'(s|x|ch|sh|z)$', r'\1es'),
                     (r'([^aeiou])y$', r'\1ies')):
        if re.search(pat, v):
            return re.sub(pat, rep, v)
    return v + 's'


def ing2(v):
    if DOUBLE.match(v):
        return v + v[-1] + 'ing'
    return re.sub(r'ie$', 'y', re.sub(r'([^e])e$', r'\1', v)) + 'ing' if v != 'be' else 'being'


# ---------------------------------------------------------------- ЕГЭ 19–24 / ОГЭ 20–28: времена глагола

TENSES = ['past', 'pres', 'fut', 'perf', 'cont', 'pastcont', 'neg', 'passive']


def be_form(subj_kind, tense):
    if tense == 'pres':
        return {'1': 'am', '3': 'is', 'pl': 'are'}[subj_kind]
    return 'was' if subj_kind in ('1', '3') else 'were'


def verb_answer(tense, v, subj, kind, f):
    """f — набор функций морфологии (основной или проверочный). Возвращает список допустимых ответов."""
    pst, pp, thr, ng = f
    if tense == 'past':
        return [pst(v)]
    if tense == 'pres':
        return [thr(v) if kind == '3' else v]
    if tense == 'fut':
        return ['will ' + v] + (["'ll " + v] if subj in PRONOUN else [])
    if tense == 'perf':
        aux = 'has' if kind == '3' else 'have'
        alt = ("'s " if kind == '3' else "'ve ") + pp(v)
        return [f'{aux} {pp(v)}'] + ([alt] if subj in PRONOUN else [])
    if tense == 'cont':
        b = be_form(kind, 'pres')
        short = {'am': "'m", 'is': "'s", 'are': "'re"}[b]
        return [f'{b} {ng(v)}'] + ([f'{short} {ng(v)}'] if subj in PRONOUN else [])
    if tense == 'pastcont':
        return [f'{be_form(kind, "past")} {ng(v)}']
    if tense == 'neg':
        return ['did not ' + v, "didn't " + v]
    raise ValueError(tense)


PASSIVE = [  # (объект-подлежащее, число, глагол, окончание предложения)
    ('The old bridge', 'sg', 'build', 'in 1898 by Italian engineers'),
    ('These songs', 'pl', 'write', 'by a teenager from Kazan'),
    ('The first message', 'sg', 'send', 'in 1844'),
    ('Our school', 'sg', 'open', 'in 1965'),
    ('The paintings', 'pl', 'steal', 'from the museum last night'),
    ('The winners', 'pl', 'choose', 'by the audience'),
    ('This film', 'sg', 'shoot', 'in two months'),
    ('The keys', 'pl', 'find', 'under the sofa'),
    ('The tickets', 'pl', 'sell', 'out in ten minutes'),
    ('The letter', 'sg', 'translate', 'into three languages'),
    ('The game', 'sg', 'invent', 'in Scotland'),
    ('The cakes', 'pl', 'bake', 'by the pupils themselves'),
    ('The concert', 'sg', 'postpone', 'because of the storm'),
    ('The streets', 'pl', 'clean', 'early in the morning'),
    ('The fence', 'sg', 'paint', 'last week'),
]
IRREGULAR.setdefault('shoot', ('shot', 'shot'))
IRR_LINES = '\n'.join(f'{b} {p} {pp}' for b, (p, pp) in IRREGULAR.items())

TENSE_HINT = {
    'past': 'маркер прошедшего времени → Past Simple (V2 / -ed)',
    'pres': 'регулярное действие → Present Simple; he/she/it → -s/-es',
    'fut': 'маркер будущего → will + V',
    'perf': 'already/just → Present Perfect: have/has + V3',
    'cont': 'Look!/right now → Present Continuous: am/is/are + V-ing',
    'pastcont': 'в конкретный момент в прошлом → Past Continuous: was/were + V-ing',
    'neg': 'отрицание в прошлом → did not + V (глагол без окончания)',
    'passive': 'подлежащее не выполняет действие → пассив: was/were + V3',
}


def gen_verb(rng):
    tense = rng.choice(TENSES)
    main = (past, participle, third, ing)
    if tense == 'passive':
        obj, num, v, tail = rng.choice(PASSIVE)
        ans = [('was ' if num == 'sg' else 'were ') + participle(v)]
        q = gap(obj, v, tail + '.')
        wrong = [participle(v), ('were ' if num == 'sg' else 'was ') + participle(v), past(v),
                 ('has been ' if num == 'sg' else 'have been ') + participle(v)]
        return card('eng-gram-verb', 'text', q, ans, TENSE_HINT[tense]), {'tense': tense, 'v': v, 'num': num}
    subj, kind = rng.choice(SUBJECTS)
    v, obj = rng.choice(VERB_OBJ)
    while tense in ('cont', 'pastcont') and v in MOMENT:
        v, obj = rng.choice(VERB_OBJ)
    S = subj[0].upper() + subj[1:]
    if tense == 'past':
        q = gap(f'{rng.choice(PAST_MARK)} {subj}', v, obj + '.')
    elif tense == 'pres':
        q = gap(f'{rng.choice(PRES_MARK)} {subj}', v, obj + '.')
    elif tense == 'fut':
        q = gap(f'{rng.choice(FUT_MARK)} {subj}', v, obj + '.')
    elif tense == 'perf':
        # «just now» требует Past Simple, поэтому маркер — already в конце или since/for
        q = gap(f'{S}', v, f'{obj} already.')
    elif tense == 'cont':
        q = gap(f'Look! {S}', v, obj + ' right now.')
    elif tense == 'pastcont':
        q = gap(f'At six o\'clock yesterday {subj}', v, obj + ' when the lights went out.')
    else:
        q = gap(f'{S}', 'not ' + v, obj + ' last week.')
    ans = verb_answer(tense, v, subj, kind, main)
    return card('eng-gram-verb', 'text', q, ans, TENSE_HINT[tense]), {'tense': tense, 'v': v, 'subj': subj,
                                                                          'kind': kind}


def check_verb(p, c):
    if p['tense'] == 'passive':
        return c['a'] == [('was ' if p['num'] == 'sg' else 'were ') + participle2(p['v'])]
    return c['a'] == verb_answer(p['tense'], p['v'], p['subj'], p['kind'], (past2, participle2, third2, ing2))


# ---------------------------------------------------------------- существительные: множественное число

PLURAL_IRR = {'child': 'children', 'man': 'men', 'woman': 'women', 'tooth': 'teeth', 'foot': 'feet',
              'mouse': 'mice', 'goose': 'geese', 'person': 'people', 'sheep': 'sheep', 'fish': 'fish',
              'deer': 'deer', 'knife': 'knives', 'leaf': 'leaves', 'wolf': 'wolves', 'shelf': 'shelves',
              'half': 'halves', 'life': 'lives', 'wife': 'wives', 'thief': 'thieves', 'potato': 'potatoes',
              'tomato': 'tomatoes', 'hero': 'heroes'}
NOUN_FRAMES = [
    ('child', 'The Ivanovs have three', 'and a big dog.'), ('man', 'Two', 'were waiting at the gate.'),
    ('woman', 'Several', 'from our street joined the club.'), ('tooth', 'The dentist checked all my', 'yesterday.'),
    ('foot', 'After the hike my', 'hurt a lot.'), ('mouse', 'The cat caught two', 'in the barn.'),
    ('goose', 'A few', 'were swimming in the pond.'), ('person', 'About fifty', 'came to the fair.'),
    ('sheep', 'The farmer has forty', 'on the hill.'), ('knife', 'Put the forks and', 'on the table, please.'),
    ('leaf', 'In October the', 'turn yellow and red.'), ('wolf', 'We heard', 'howling in the forest.'),
    ('shelf', 'The new bookcase has five', '.'), ('potato', 'Peel the', 'and cut them into cubes.'),
    ('tomato', 'Grandad grows', 'in his greenhouse.'), ('hero', 'The main', 'of the book are two teenagers.'),
    ('box', 'We packed all the books into', '.'), ('bus', 'Two', 'arrived at the same time.'),
    ('city', 'We visited four', 'during the holidays.'), ('country', 'How many', 'have you been to?'),
    ('watch', 'The shop sells', 'and clocks.'), ('dish', 'Whose turn is it to wash the', '?'),
    ('toy', 'The kids put their', 'back in the box.'), ('key', 'I can never find my', '.'),
    ('photo', 'Send me the', 'from the trip!'), ('glass', 'There are six', 'on the tray.'),
    ('library', 'The town has two public', '.'), ('day', 'We stayed there for ten', '.'),
]


def plural(n):
    if n in PLURAL_IRR:
        return PLURAL_IRR[n]
    if n.endswith(('s', 'x', 'ch', 'sh')):
        return n + 'es'
    if n.endswith('y') and n[-2] not in VOW:
        return n[:-1] + 'ies'
    return n + 's'


def gen_noun(rng):
    n, a, b = rng.choice(NOUN_FRAMES)
    q = gap(a, n, b).replace(' .', '.').replace(' ?', '?')
    wrong = [n + 's', n + 'es', plural(n)[:-1] + 's' if not plural(n).endswith('s') else n]
    return card('eng-gram-noun', 'text', q, [plural(n)],
                'Множественное число: -s; после s, x, ch, sh → -es; согласная + y → -ies; исключения учим списком.'), \
        {'n': n, 'wrong': wrong}


def check_noun(p, c):
    n = p['n']
    for pat, rep in ((r'(s|x|ch|sh)$', r'\1es'), (r'([^aeiou])y$', r'\1ies')):
        if n not in PLURAL_IRR and re.search(pat, n):
            return c['a'] == [re.sub(pat, rep, n)]
    return c['a'] == [PLURAL_IRR.get(n, n + 's')]


# ---------------------------------------------------------------- степени сравнения

ADJ_IRR = {'good': ('better', 'best'), 'bad': ('worse', 'worst'), 'far': ('farther', 'farthest'),
           'little': ('less', 'least'), 'many': ('more', 'most'), 'much': ('more', 'most')}
ADJ_DOUBLE = {'big', 'hot', 'thin', 'fat', 'wet', 'sad'}
ADJ_LONG = {'interesting', 'difficult', 'expensive', 'comfortable', 'dangerous', 'popular', 'beautiful',
            'exciting', 'important', 'useful', 'famous', 'boring'}
ADJ_FRAMES_CMP = [
    ('This year\'s exam was', 'than last year\'s.'), ('Our new flat is', 'than the old one.'),
    ('The second film is', 'than the first.'), ('The road through the forest is', 'than the highway.'),
]
ADJ_FRAMES_SUP = [
    ('It was the', 'day of the whole trip.'), ('Kate is the', 'player in our team.'),
    ('This is the', 'place in the city, in my opinion.'), ('That was the', 'lesson of the week.'),
]
ADJ_LIST = ['good', 'bad', 'far', 'big', 'hot', 'easy', 'happy', 'busy', 'funny', 'long', 'short', 'cheap',
            'large', 'nice', 'close', 'interesting', 'difficult', 'expensive', 'comfortable', 'dangerous',
            'popular', 'beautiful', 'exciting', 'important', 'useful', 'famous', 'boring', 'thin', 'wet', 'safe',
            'quiet', 'warm', 'cold', 'fast', 'slow', 'clean']


def compare(a, deg):
    if a in ADJ_IRR:
        return ADJ_IRR[a][deg]
    if a in ADJ_LONG:
        return ('more ' if deg == 0 else 'most ') + a
    suf = ('er', 'est')[deg]
    if a.endswith('e'):
        return a + suf[1:]
    if a.endswith('y'):
        return a[:-1] + 'i' + suf
    if a in ADJ_DOUBLE:
        return a + a[-1] + suf
    return a + suf


def gen_adj(rng):
    a = rng.choice(ADJ_LIST)
    deg = rng.randint(0, 1)
    before, after = rng.choice(ADJ_FRAMES_SUP if deg else ADJ_FRAMES_CMP)
    q = gap(before, a, after)
    ans = [compare(a, deg)]
    if deg and a in ('good', 'bad') and 'player' not in before:
        pass
    return card('eng-gram-adj', 'text', q, ans,
                'than → сравнительная степень; the … of/in → превосходная. Длинные — more/most; good–better–best.'), \
        {'a': a, 'deg': deg}


def check_adj(p, c):
    a, deg = p['a'], p['deg']
    table = {'good': 'better best', 'bad': 'worse worst', 'far': 'farther farthest', 'little': 'less least'}
    if a in table:
        return c['a'] == [table[a].split()[deg]]
    if len(re.findall(r'[aeiouy]+', a)) >= 3 or a in ('famous', 'useful', 'boring', 'popular', 'exciting',
                                                         'important', 'expensive', 'difficult', 'dangerous',
                                                         'beautiful', 'comfortable', 'interesting'):
        return c['a'] == [('more ', 'most ')[deg] + a]
    base = re.sub(r'y$', 'i', a)
    base = re.sub(r'e$', '', base)
    if re.fullmatch(r'[^aeiou]*[aeiou][bdgmnpt]', a):
        base = a + a[-1]
    return c['a'] == [base + ('er', 'est')[deg]]


# ---------------------------------------------------------------- порядковые числительные

ONES = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve',
        'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
ORD_IRR = {'one': 'first', 'two': 'second', 'three': 'third', 'five': 'fifth', 'eight': 'eighth', 'nine': 'ninth',
           'twelve': 'twelfth'}
ORD_FRAMES = [('Our flat is on the', 'floor.'), ('Anna came', 'in the race.'),
              ('Today is my grandfather\'s', 'birthday!'), ('This is the', 'time I have read this book.'),
              ('The shop celebrates its', 'anniversary this year.'), ('We live in the', 'house on the left.')]


def words(n):
    return ONES[n] if n < 20 else TENS[n // 10] + ('-' + ONES[n % 10] if n % 10 else '')


def ordinal(n):
    w = words(n)
    head, _, last = w.rpartition('-')
    if last in ORD_IRR:
        o = ORD_IRR[last]
    elif last.endswith('y'):
        o = last[:-1] + 'ieth'
    else:
        o = last + 'th'
    return (head + '-' if head else '') + o


def gen_ord(rng):
    n = rng.randint(1, 99)
    before, after = rng.choice(ORD_FRAMES)
    q = gap(before, words(n), after)
    return card('eng-gram-ord', 'text', q, [ordinal(n)],
                'one → first, two → second, three → third, five → fifth, nine → ninth, twelve → twelfth, '
                'twenty → twentieth; в составных меняется только последнее слово.'), {'n': n}


def check_ord(p, c):
    n = p['n']
    suffix = 'st' if n % 10 == 1 and n % 100 != 11 else 'nd' if n % 10 == 2 and n % 100 != 12 else \
        'rd' if n % 10 == 3 and n % 100 != 13 else 'th'
    # сверяем окончание словесной формы с цифровой записью 1st/2nd/3rd/…th
    return c['a'][0].endswith({'st': 'first', 'nd': 'second', 'rd': 'third', 'th': 'th'}[suffix])


# ---------------------------------------------------------------- местоимения

PRON = {  # личное: (объектное, притяжательное-абсолютное, возвратное)
    'I': ('me', 'mine', 'myself'), 'you': ('you', 'yours', 'yourself'), 'he': ('him', 'his', 'himself'),
    'she': ('her', 'hers', 'herself'), 'we': ('us', 'ours', 'ourselves'), 'they': ('them', 'theirs', 'themselves'),
}
PRON_FRAMES = [
    (0, 'Could you help', 'with this heavy bag?'), (0, 'The coach told', 'to wait outside.'),
    (0, 'Nobody invited', 'to the meeting.'),
    (1, 'This umbrella is not my sister\'s, it is', '.'), (1, 'Whose bikes are these? — They are', '.'),
    (2, 'The kids decorated the room all by', '.'), (2, 'Be careful with the knife — don\'t hurt', '!'),
    (2, 'The twins taught', 'to swim last summer.'),
]
PRON_OK = {  # какие лица подходят в рамку (чтобы не было «don't hurt himself!» в обращении)
    (2, 'The kids decorated the room all by'): ['they'], (2, 'Be careful with the knife — don\'t hurt'): ['you'],
    (2, 'The twins taught'): ['they'],
}


def gen_pron(rng):
    kind, before, after = rng.choice(PRON_FRAMES)
    ok = PRON_OK.get((kind, before), list(PRON))
    p = rng.choice(ok)
    if kind == 1 and p == 'I' and 'Whose bikes' in before:
        p = 'we'
    q = gap(before, p, after).replace(' .', '.').replace(' !', '!')
    ans = [PRON[p][kind]]
    return card('eng-gram-pron', 'text', q, ans,
                'После глагола/предлога — объектный падеж (me, him, us); «чей?» без существительного — mine, hers; '
                'by oneself — возвратное (-self/-selves).'), {'p': p, 'kind': kind}


def check_pron(p, c):
    rows = 'I me mine myself|you you yours yourself|he him his himself|she her hers herself|' \
           'we us ours ourselves|they them theirs themselves'
    t = {r.split()[0]: r.split()[1:] for r in rows.split('|')}
    return c['a'] == [t[p['p']][p['kind']]]


# ---------------------------------------------------------------- словообразование: собственные гнёзда и предложения

# Аффиксы по кодификаторам 2026: ЕГЭ 2.3.11, ОГЭ 2.3.7 (ОГЭ — подмножество).
AFF_EGE = {'dis-', 'mis-', 're-', 'over-', 'under-', '-ise', '-ize', '-en', 'un-', 'in-', 'im-', 'il-', 'ir-',
           '-ance', '-ence', '-er', '-or', '-ing', '-ist', '-ity', '-ment', '-ness', '-sion', '-tion', '-ship',
           'inter-', 'non-', 'post-', 'pre-', '-able', '-ible', '-al', '-ed', '-ese', '-ful', '-ian', '-an',
           '-ical', '-ish', '-ive', '-less', '-ly', '-ous', '-y', '-teen', '-ty', '-th'}
AFF_OGE = {'-er', '-or', '-ist', '-sion', '-tion', '-ance', '-ence', '-ity', '-ship', '-ing', '-ment', '-ness',
           '-ful', '-ian', '-an', '-al', '-less', '-ive', '-ed', '-ly', '-ous', '-y', '-able', '-ible', 'un-',
           'in-', 'im-', 'inter-', 'under-', 'over-', 'dis-', 'mis-', '-teen', '-ty', '-th'}

# (ОСНОВА, ответ, аффиксы, предложение с ____) — предложения составлены для прототипа
WF = [
    ('EXPECT', 'unexpected', ['un-', '-ed'], 'The storm was completely ____ — the forecast promised sunshine.'),
    ('EXPECT', 'expectations', ['-tion'], 'The show was brilliant and went far beyond our ____.'),
    ('DECIDE', 'decision', ['-sion'], 'Moving to another city was a difficult ____ for the whole family.'),
    ('HAPPY', 'happiness', ['-ness'], 'Money cannot buy ____, my grandmother always says.'),
    ('HAPPY', 'unhappy', ['un-'], 'Tom looked ____ because his team had lost the final.'),
    ('CARE', 'careful', ['-ful'], 'Be ____ when you cross the road near the school.'),
    ('CARE', 'careless', ['-less'], 'A ____ mistake cost him a point in the test.'),
    ('CARE', 'carefully', ['-ful', '-ly'], 'Read the instructions ____ before you start.'),
    ('POSSIBLE', 'impossible', ['im-'], 'Without a map it was ____ to find the old path.'),
    ('POSSIBLE', 'possibility', ['-ity'], 'There is a ____ that the flight will be delayed.'),
    ('LEGAL', 'illegal', ['il-'], 'Crossing the border without a passport is ____.'),
    ('REGULAR', 'irregular', ['ir-'], 'Learn the ____ verbs by heart, there are not so many of them.'),
    ('DEPEND', 'independent', ['in-', '-ent'], 'At eighteen Mark became ____ and rented his own flat.'),
    ('DIFFER', 'difference', ['-ence'], 'Can you spot the ____ between these two pictures?'),
    ('PERFORM', 'performance', ['-ance'], 'The actors gave an amazing ____ last night.'),
    ('SCIENCE', 'scientists', ['-ist'], 'A team of young ____ discovered a new kind of beetle.'),
    ('MUSIC', 'musician', ['-ian'], 'Her uncle is a professional ____ who plays the cello.'),
    ('RUSSIA', 'Russian', ['-an'], 'Pushkin is a famous ____ poet.'),
    ('CHINA', 'Chinese', ['-ese'], 'My brother is learning ____ because he wants to work in Beijing.'),
    ('NATION', 'national', ['-al'], 'The ____ park attracts thousands of tourists every year.'),
    ('HISTORY', 'historical', ['-ical'], 'We watched a ____ film about Peter the Great.'),
    ('CHILD', 'childish', ['-ish'], 'Stop being so ____ and say sorry to your sister.'),
    ('ATTRACT', 'attractive', ['-ive'], 'The old town is very ____ to tourists.'),
    ('DANGER', 'dangerous', ['-ous'], 'Swimming in this river is ____ because of the strong current.'),
    ('SUN', 'sunny', ['-y'], 'It was a warm ____ day, perfect for a picnic.'),
    ('COMFORT', 'comfortable', ['-able'], 'The new sofa is really ____.'),
    ('SENSE', 'sensible', ['-ible'], 'Taking an umbrella was a ____ idea.'),
    ('FRIEND', 'friendship', ['-ship'], 'Their ____ started at a summer camp.'),
    ('FRIEND', 'unfriendly', ['un-', '-ly'], 'The shop assistant was rude and ____.'),
    ('ENJOY', 'enjoyment', ['-ment'], 'The kids played in the snow with great ____.'),
    ('EQUIP', 'equipment', ['-ment'], 'All the sports ____ is kept in the storeroom.'),
    ('VISIT', 'visitors', ['-or'], 'The museum welcomes thousands of ____ every summer.'),
    ('TEACH', 'teacher', ['-er'], 'Our new maths ____ explains everything very clearly.'),
    ('BUILD', 'building', ['-ing'], 'The tallest ____ in the city has eighty floors.'),
    ('AGREE', 'disagree', ['dis-'], 'I ____ with you: I think the book is better than the film.'),
    ('UNDERSTAND', 'misunderstood', ['mis-'], 'Sorry, I ____ you — I thought you meant Tuesday.'),
    ('WRITE', 'rewrite', ['re-'], 'The teacher asked me to ____ the essay because of the mistakes.'),
    ('SLEEP', 'overslept', ['over-'], 'I ____ this morning and missed the bus.'),
    ('ESTIMATE', 'underestimated', ['under-'], 'We ____ how long the journey would take and arrived late.'),
    ('MODERN', 'modernise', ['-ise'], 'The city plans to ____ its old tram system.'),
    ('WIDE', 'widen', ['-en'], 'The workers are going to ____ the road next year.'),
    ('NATION', 'international', ['inter-', '-al'], 'Over forty countries took part in the ____ festival.'),
    ('SENSE', 'nonsense', ['non-'], 'Don\'t listen to him — what he says is complete ____.'),
    ('WAR', 'postwar', ['post-'], 'The novel describes ____ life in a small town.'),
    ('HISTORY', 'prehistoric', ['pre-', '-ic'], 'Scientists found the bones of a ____ animal.'),
    ('SUCCESS', 'successful', ['-ful'], 'The concert was so ____ that they decided to repeat it.'),
    ('SUCCESS', 'unsuccessfully', ['un-', '-ful', '-ly'], 'He tried ____ to open the jar and finally gave up.'),
    ('KIND', 'kindness', ['-ness'], 'Thank you for your ____ — I will never forget it.'),
    ('HELP', 'helpless', ['-less'], 'Without the internet I feel absolutely ____.'),
    ('ACT', 'actress', ['-ess'], 'She dreams of becoming a famous ____.'),
    ('POPULAR', 'popularity', ['-ity'], 'The ____ of electric scooters is growing fast.'),
    ('INFORM', 'information', ['-tion'], 'You can find all the ____ on the school website.'),
    ('EXCITE', 'exciting', ['-ing'], 'It was the most ____ match of the season.'),
    ('BORE', 'bored', ['-ed'], 'The kids got ____ during the long speech.'),
    ('FIVE', 'fifteen', ['-teen'], 'The bus leaves in ____ minutes, hurry up!'),
    ('FOUR', 'forty', ['-ty'], 'My dad turned ____ last month.'),
    ('NINE', 'ninth', ['-th'], 'My sister is in the ____ grade.'),
    ('USUAL', 'unusually', ['un-', '-ly'], 'It was ____ cold for May.'),
    ('PATIENT', 'impatiently', ['im-', '-ly'], 'The passengers waited ____ for the delayed train.'),
    ('CORRECT', 'incorrect', ['in-'], 'Two of your answers are ____, please check them again.'),
    ('EMPLOY', 'unemployment', ['un-', '-ment'], '____ fell last year as new factories opened.'),
]
# Замечания к гнёздам:
#   суффиксов -ess (actress), -ic (prehistoric), -ent (independent) в кодификаторах 2026 нет — такие карточки
#   помечаются «вне кодификатора (тренировка)»; в наборе ЕГЭ их лучше не держать.
AFF_VARIANTS = {}


def wf_in_codifier(affixes, allowed):
    return all(AFF_VARIANTS.get(a, a) in allowed for a in affixes)


def gen_wf(rng, _i=[0]):
    base, ans, affs, sent = WF[_i[0] % len(WF)]
    _i[0] += 1
    ege, oge = wf_in_codifier(affs, AFF_EGE), wf_in_codifier(affs, AFF_OGE)
    fam = sorted({a for b, a, _, _ in WF if b == base and a != ans})
    q = sent + f'  ({base})'
    exam = 'ЕГЭ 25–29 и ОГЭ 29–34' if oge else 'ЕГЭ 25–29' if ege else 'вне кодификатора (тренировка)'
    ex = f'{base} → {ans}: {", ".join(affs)}. Формат: {exam}.'
    if fam:
        ex += ' Не путать с: ' + ', '.join(fam) + '.'
    c = card('eng-wf', 'text', q, [ans], ex)
    c['exam'] = exam  # служебное поле прототипа: к какому экзамену относится аффикс
    return c, {'base': base, 'affs': affs, 'ans': ans}


def check_wf(p, c):
    # вторая проверка: ответ содержит основу (с учётом типичных чередований) и каждый заявленный аффикс
    stem_alts = {'DECIDE': 'deci', 'HAPPY': 'happ', 'POSSIBLE': 'possib', 'SCIENCE': 'scien', 'CHINA': 'chin',
                 'HISTORY': 'histor', 'DANGER': 'danger', 'SENSE': 'sens', 'FIVE': 'fif', 'FOUR': 'for',
                 'NINE': 'nin', 'UNDERSTAND': 'understood', 'SLEEP': 'slept', 'EXCITE': 'excit', 'BORE': 'bor',
                 'RUSSIA': 'russia', 'ESTIMATE': 'estimat', 'MODERN': 'modern', 'WIDE': 'wid', 'PATIENT': 'patient',
                 'DIFFER': 'differ', 'INFORM': 'inform', 'POPULAR': 'popular', 'MUSIC': 'music',
                 'EXPECT': 'expect', 'EMPLOY': 'employ', 'LEGAL': 'legal', 'REGULAR': 'regular'}
    a = c['a'][0].lower()
    stem = stem_alts.get(p['base'], p['base'].lower()[:4])
    if stem not in a:
        return False
    for af in p['affs']:
        core = af.strip('-')
        if af.endswith('-') and not a.startswith(core):
            return False
        if af.startswith('-') and core not in a:
            return False
    return True


# ---------------------------------------------------------------- самопроверка

GENERATORS = {
    'verb': (gen_verb, check_verb), 'noun': (gen_noun, check_noun), 'adj': (gen_adj, check_adj),
    'ord': (gen_ord, check_ord), 'pron': (gen_pron, check_pron), 'wf': (gen_wf, check_wf),
}
CAP = {'noun': len(NOUN_FRAMES), 'pron': 32, 'wf': len(WF), 'ord': 99 * len(ORD_FRAMES)}


def selftest(n=200, seed=2026, max_tries=30):
    rng = random.Random(seed)
    report, allcards = [], []
    for name, (gen, chk) in GENERATORS.items():
        want = min(n, CAP.get(name, n))
        seen, cards, bad, tries = set(), [], [], 0
        while len(cards) < want and tries < want * max_tries:
            tries += 1
            c, p = gen(rng)
            if c['q'] in seen:
                continue
            seen.add(c['q'])
            if not (c['a'] and chk(p, c)):
                bad.append(c)
            cards.append(c)
        ids = Counter(c['id'] for c in cards)
        report.append({'type': name, 'want': want, 'cards': len(cards), 'tries': tries,
                       'dup_id': sum(v - 1 for v in ids.values() if v > 1), 'check_failed': len(bad),
                       'distinct_answers': len({json.dumps(c['a']) for c in cards}), 'bad': bad[:3]})
        allcards += cards
    return report, allcards


def capacity(name, limit=5000, seed=1):
    rng = random.Random(seed)
    seen = set()
    for _ in range(limit * 3):
        seen.add(GENERATORS[name][0](rng)[0]['q'])
        if len(seen) >= limit:
            break
    return len(seen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=200)
    ap.add_argument('--show', type=int, default=0)
    ap.add_argument('--dump')
    ap.add_argument('--capacity', action='store_true')
    args = ap.parse_args()
    report, cards = selftest(args.n)
    print(f'{"тип":6} {"нужно":>5} {"карт.":>5} {"попыт.":>6} {"повт.id":>7} {"ошибок":>6} {"разн.отв":>8}')
    for r in report:
        print(f'{r["type"]:6} {r["want"]:5} {r["cards"]:5} {r["tries"]:6} {r["dup_id"]:7} {r["check_failed"]:6} '
              f'{r["distinct_answers"]:8}')
        for b in r['bad']:
            print('   ОШИБКА:', b['q'], b['a'])
    fails = sum(r['check_failed'] + r['dup_id'] + (r['cards'] < r['want']) for r in report)
    print(f'Итого: {sum(r["cards"] for r in report)} карточек, {len(report)} типов, проблем: {fails}')
    wf = [c for c in cards if c['t'] == 'eng-wf']
    print('Словообразование по формату:', dict(Counter(c['exam'] for c in wf)))
    if args.capacity:
        print('Ёмкость (уникальных условий, выборка до 5000):',
              {k: capacity(k) for k in GENERATORS if k != 'wf'}, '| wf:', len(WF))
    if args.show:
        by = {}
        for c in cards:
            by.setdefault(c['t'], []).append(c)
        for cs in by.values():
            for c in cs[:args.show]:
                print(json.dumps(c, ensure_ascii=False))
    if args.dump:
        with open(args.dump, 'w', encoding='utf-8') as f:
            json.dump(cards, f, ensure_ascii=False, indent=1)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
