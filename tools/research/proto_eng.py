#!/usr/bin/env python3
"""Английский язык: каталог прототипов ЕГЭ 1–42 и ОГЭ 1–35 (+ устная часть) и генератор аналогов.

Запуск (то же, что `python3 tools/research/gen_eng.py --protos …`):
  python3 tools/research/proto_eng.py                 # самопроверка: до 50 карточек на прототип
  python3 tools/research/proto_eng.py --show ID -n 3  # примеры по прототипу
  python3 tools/research/proto_eng.py --sample 3 --seed 7 --out FILE   # выборка для экзаменационной проверки
  python3 tools/research/proto_eng.py --export        # data/source/eng-prototypes.json
  python3 tools/research/proto_eng.py --tables        # таблицы покрытия и проверки для отчёта (markdown)

Устройство. Прототип — «что неизменно, что меняется, как считается ответ». Генератор `param` собирает
предложение из собственных рамок и таблиц форм (морфология — из gen_eng.py), `dict` — из собственных
таблиц гнёзд и путаниц. Ответ у каждой карточки считает правило или таблица, а независимая проверка
(вторая реализация правила, вторая таблица или обратное преобразование) должна дать тот же ответ.
Чтение, аудирование, письмо и говорение — только рецепты `llm`, без генерации.

Тексты ФИПИ и коммерческих банков не используются: структура — из спецификаций и кодификаторов 2026
(ЕГЭ 2027 без изменений), все предложения придуманы для этого генератора. Словари сторонние в репозиторий
не кладутся: таблицы ниже — собственные факты языка (см. docs/research/inf-eng.md, раздел `dict`).
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_eng as G  # noqa: E402  таблицы форм и две реализации морфологии

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG = os.path.join(ROOT, 'data', 'source', 'eng-prototypes.json')
FIDELITY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eng_fidelity.json')
SRC = 'Генератор «Между уроками» (собственные предложения)'

PROTOS = []  # каталог: словари с полями прототипа + gen/check


def blank(a):
    """Запись ответа как в бланке: без пробелов и регистра, апостроф остаётся (ключи ФИПИ: 'vefound)."""
    return re.sub(r'\s+', '', a).lower()


def card(proto, q, a, e, k='text', o=None):
    c = {'id': '', 'p': proto, 'k': k, 'q': q, 'a': a, 'e': e}
    if o is not None:
        c['o'] = o
    if k == 'text':
        c['blank'] = [blank(x) for x in a]
    c['src'] = SRC
    c['id'] = proto + '-' + hashlib.sha1((q + '|' + json.dumps(a, ensure_ascii=False)).encode()).hexdigest()[:8]
    return c


def gap(before, word, after=''):
    """Предложение с пропуском; слово-основа заглавными в конце строки, как в КИМ."""
    s = f'{before} ____ {after}'.strip()
    s = re.sub(r' ([.,!?])', r'\1', s)
    return s + f'  ({word.upper()})'


def cap(s):
    return s[0].upper() + s[1:]


def proto(**meta):
    """Декоратор: регистрирует генератор (rng, exam) -> (card, params) и проверку check(params, card)."""

    def wrap(fn):
        m = dict(meta)
        m['gen_fn'] = fn
        PROTOS.append(m)
        return fn

    return wrap


MAIN = (G.past, G.participle, G.third, G.ing)
ALT = (G.past2, G.participle2, G.third2, G.ing2)

# ---------------------------------------------------------------- общие рамки (собственные)

PAST_MARK = G.PAST_MARK + ['A week ago', 'Last night', 'On Monday', 'In 2021']
PRES_MARK = G.PRES_MARK + ['Every morning', 'Once a week', 'As a rule', 'After school']
FUT_MARK = G.FUT_MARK + ['Next Friday', 'In two weeks', 'On Saturday', 'This evening']
PRON_SUBJ = G.PRONOUN

BE2 = {'pres': {'1': 'am', '3': 'is', 'pl': 'are'}, 'past': {'1': 'was', '3': 'was', 'pl': 'were'}}  # вторая таблица

BE_FRAMES = [  # (tense, subject, kind, tail)
    ('pres', 'my parents', 'pl', 'doctors, and I want to become a doctor too.'),
    ('pres', 'Sam', '3', 'at the swimming pool right now.'),
    ('pres', 'I', '1', 'fourteen years old, and my brother is twelve.'),
    ('pres', 'the shops in our street', 'pl', 'open until nine in the evening.'),
    ('pres', 'my grandmother', '3', 'a very good cook.'),
    ('pres', 'we', 'pl', 'always happy to see our cousins.'),
    ('past', 'the weather', '3', 'terrible yesterday, so we stayed at home.'),
    ('past', 'my parents', 'pl', 'students in 2015.'),
    ('past', 'I', '1', 'ill last week and missed three lessons.'),
    ('past', 'the tickets', 'pl', 'quite cheap, so we bought four.'),
    ('past', 'our first flat', '3', 'very small, but we loved it.'),
    ('past', 'you', 'pl', 'late for the lesson again yesterday, Tom!'),
    ('pres', 'my cousin and I', 'pl', 'in the same class this year.'),
    ('pres', 'the water in the lake', '3', 'too cold for swimming in May.'),
    ('pres', 'you', 'pl', 'the best goalkeeper in the school, everybody says so.'),
    ('pres', 'these apples', 'pl', 'from our own garden.'),
    ('past', 'Grandma', '3', 'a teacher for thirty years.'),
    ('past', 'we', 'pl', 'at the seaside when the storm began.'),
    ('past', 'the film', '3', 'much better than I had expected.'),
    ('past', 'my grandparents', 'pl', 'born in a small village near Tver.'),
]
THERE_FRAMES = [  # (tense, number, tail)
    ('past', 'pl', 'two old oak trees in our yard when I was a child.'),
    ('past', 'sg', 'a lot of snow last winter.'),
    ('past', 'sg', 'nobody at home when I came back.'),
    ('past', 'pl', 'only five people at the bus stop this morning.'),
    ('pres', 'pl', 'twenty-six pupils in our class this year.'),
    ('pres', 'sg', 'nothing in the fridge, so we need to go shopping.'),
    ('pres', 'sg', 'a new cafe next to the school now.'),
    ('pres', 'pl', 'three bridges across the river in our town.'),
    ('pres', 'sg', 'too much salt in this soup.'),
    ('pres', 'pl', 'some letters for you on the table.'),
    ('past', 'sg', 'a small bakery on this corner ten years ago.'),
    ('past', 'pl', 'no computers in schools when my grandfather was a pupil.'),
    ('pres', 'sg', 'always a long queue at this cafe at lunchtime.'),
    ('past', 'pl', 'a lot of people at the concert last night.'),
]


@proto(id='eng-ege-19-be', exam='ЕГЭ', n=19, n_range='19–24', title='Формы глагола be (am/is/are/was/were), в том числе there + be',
       kes=['2.4.24'], level='Б', kind='param',
       invariant='одно предложение с пропуском, основа BE заглавными в конце строки; лицо/число и время однозначно заданы подлежащим и маркером',
       varies='подлежащее (лицо, число), время (настоящее или прошедшее), обстоятельство, конструкция there + be',
       answer_rule='таблица форм be по лицу, числу и времени; в there + be число берётся от существительного после be',
       mistakes=['there is при множественном числе', 'was с they/you', 'am с he/she'])
def g_be(rng, exam):
    if rng.random() < 0.4:
        tense, num, tail = rng.choice(THERE_FRAMES)
        kind = '3' if num == 'sg' else 'pl'
        q = gap('There', 'be', tail)
        subj = 'there'
    else:
        tense, subj, kind, tail = rng.choice(BE_FRAMES)
        q = gap(cap(subj), 'be', tail)
    ans = [G.be_form(kind, tense)]
    return card(meta_id(), q, ans, 'be: am/is/are в настоящем, was/were в прошедшем; число — по подлежащему (после there — по существительному).'), \
        {'kind': kind, 'tense': tense, 'subj': subj}


def c_be(p, c):
    return c['a'] == [BE2[p['tense']][p['kind']]]


def meta_id():
    """id текущего прототипа подставляет generate(); здесь — заглушка для card()."""
    return _CUR[0]


_CUR = ['']


@proto(id='eng-oge-20-be', exam='ОГЭ', n=20, n_range='20–28', title='Формы глагола be', kes=['2.4.30', '2.4.31'], level='Б', kind='param',
       invariant='одно предложение, основа BE заглавными; лицо, число и время заданы подлежащим и маркером',
       varies='подлежащее, время, обстоятельство', answer_rule='таблица форм be по лицу, числу и времени',
       mistakes=['was с they', 'is с I', 'are с he/she'])
def g_be_oge(rng, exam):
    tense, subj, kind, tail = rng.choice(BE_FRAMES)
    q = gap(cap(subj), 'be', tail)
    return card(meta_id(), q, [G.be_form(kind, tense)], 'be: am/is/are — настоящее, was/were — прошедшее; форма по подлежащему.'), \
        {'kind': kind, 'tense': tense, 'subj': subj}


@proto(id='eng-oge-20-there-be', exam='ОГЭ', n=20, n_range='20–28', title='Конструкция there + be', kes=['2.4.5'], level='Б', kind='param',
       invariant='предложение начинается с There, основа BE заглавными; число задано существительным, время — обстоятельством',
       varies='существительное (ед./мн. число), время, обстоятельство', answer_rule='число — от существительного после be, время — от маркера',
       mistakes=['there is с множественным числом', 'there were с a lot of snow (неисчисляемое)'])
def g_there(rng, exam):
    tense, num, tail = rng.choice(THERE_FRAMES)
    kind = '3' if num == 'sg' else 'pl'
    return card(meta_id(), gap('There', 'be', tail), [G.be_form(kind, tense)],
                'there + be: is/was — единственное число и неисчисляемые, are/were — множественное.'), {'kind': kind, 'tense': tense}


# ---------------------------------------------------------------- времена

HABIT_OBJ = [  # регулярные действия — для Present Simple
    ('walk', 'the dog in the park'), ('play', 'football with friends'), ('visit', 'our grandparents'), ('go', 'to the swimming pool'),
    ('watch', 'cartoons after breakfast'), ('help', 'Mum in the kitchen'), ('read', 'a chapter of a book'), ('practise', 'the piano'),
    ('cook', 'dinner for the whole family'), ('clean', 'the flat'), ('water', 'the flowers on the balcony'), ('study', 'French'),
    ('do', 'the shopping'), ('have', 'lunch at school'), ('take', 'the bus to school'), ('feed', 'the cat'), ('wash', 'the car'),
    ('meet', 'friends in the park'), ('buy', 'fresh bread at the corner shop'), ('write', 'in a diary'), ('fly', 'to Sochi'),
    ('carry', 'the shopping upstairs for Grandma'), ('fix', 'old bikes in the garage'), ('try', 'a new recipe'),
]
CONT_OBJ = [  # процессы — для Continuous
    ('paint', 'the fence'), ('cook', 'pancakes'), ('read', 'an article about volcanoes'), ('write', 'a letter to our cousins'),
    ('watch', 'a documentary about whales'), ('clean', 'the kitchen'), ('practise', 'the new song'), ('decorate', 'the classroom'),
    ('play', 'chess'), ('wash', 'the dishes'), ('build', 'a treehouse'), ('draw', 'a map of the park'), ('study', 'for the history test'),
    ('repair', 'the old radio'), ('translate', 'the instructions'), ('carry', 'the heavy boxes upstairs'), ('swim', 'in the lake'),
    ('make', 'a cake'), ('have', 'breakfast'), ('plan', 'a trip to the mountains'), ('pack', 'the suitcases'), ('water', 'the garden'),
]
CHORE_OBJ = [  # дела с результатом — для Perfect
    ('paint', 'the fence'), ('clean', 'the kitchen'), ('fix', 'the broken chair'), ('decorate', 'the classroom'), ('repair', 'the old radio'),
    ('cook', 'dinner'), ('build', 'a treehouse'), ('draw', 'a map of the park'), ('wash', 'the dishes'), ('translate', 'the instructions'),
    ('send', 'the photos to the organisers'), ('write', 'the invitations'), ('pack', 'the suitcases'), ('water', 'the flowers'), ('finish', 'the project'),
]
ACCIDENT = {'lose', 'find', 'forget', 'miss', 'hide', 'catch', 'steal'}  # не планируют: не для будущего и Present Simple


def pick_verb(rng, cont=False, pool=None):
    pool = pool or G.VERB_OBJ
    v, obj = rng.choice(pool)
    while cont and v in G.MOMENT:
        v, obj = rng.choice(pool)
    return v, obj


def lc(m):
    return m[0].lower() + m[1:]  # маркер внутрь предложения: 'Last Saturday' → 'last Saturday'


@proto(id='eng-ege-19-past-simple', exam='ЕГЭ', n=19, n_range='19–24', title='Past Simple: правильные и неправильные глаголы',
       kes=['2.4.24'], level='Б', kind='param',
       invariant='одно предложение с маркером прошедшего времени (yesterday, ago, in 2019…), глагол заглавными',
       varies='маркер, подлежащее, глагол (60 неправильных + правильные с орфографией -ed), дополнение',
       answer_rule='таблица неправильных глаголов; для правильных — -ed с правилами (stop → stopped, study → studied, live → lived)',
       mistakes=['teached, bringed, catched', 'stoped, studyed', 'Present Perfect при маркере yesterday/ago'])
def g_past(rng, exam):
    subj, kind = rng.choice(G.SUBJECTS)
    v, obj = pick_verb(rng)
    q = gap(f'{rng.choice(PAST_MARK)} {subj}', v, obj + '.')
    return card(meta_id(), q, [G.past(v)], G.TENSE_HINT['past']), {'v': v}


def c_past(p, c):
    return c['a'] == [G.past2(p['v'])]


@proto(id='eng-oge-21-past-simple', exam='ОГЭ', n=21, n_range='20–28', title='Past Simple: правильные и неправильные глаголы',
       kes=['2.4.30'], level='Б', kind='param', gen_of='eng-ege-19-past-simple',
       invariant='одно предложение с маркером прошедшего времени, глагол заглавными', varies='маркер, подлежащее, глагол, дополнение',
       answer_rule='таблица неправильных глаголов или -ed с правилами орфографии', mistakes=['goed, teached', 'stoped'])
def g_past_oge(rng, exam):
    return g_past(rng, exam)


@proto(id='eng-ege-19-past-neg', exam='ЕГЭ', n=19, n_range='19–24', title='Past Simple: отрицание (did not / didn\'t)',
       kes=['2.4.24'], level='Б', kind='param',
       invariant='предложение с маркером прошедшего времени, в скобках NOT + глагол', varies='подлежащее, глагол, дополнение, маркер',
       answer_rule='did not + инфинитив; в ключе два варианта: полная и краткая форма', mistakes=['did not went', 'didn\'t + -ed', 'not + V2 без did'])
def g_past_neg(rng, exam):
    subj, kind = rng.choice(G.SUBJECTS)
    v, obj = pick_verb(rng)
    q = gap(cap(subj), 'not ' + v, f'{obj} {lc(rng.choice(PAST_MARK))}.')
    return card(meta_id(), q, ['did not ' + v, "didn't " + v], G.TENSE_HINT['neg']), {'v': v}


def c_past_neg(p, c):
    return c['blank'] == ['didnot' + p['v'], "didn't" + p['v']] and p['v'] == re.sub(r'^did not ', '', c['a'][0])


@proto(id='eng-oge-21-past-neg', exam='ОГЭ', n=21, n_range='20–28', title='Past Simple: отрицание', kes=['2.4.30'], level='Б', kind='param',
       gen_of='eng-ege-19-past-neg', invariant='маркер прошедшего времени, в скобках NOT + глагол', varies='подлежащее, глагол, маркер',
       answer_rule='did not / didn\'t + инфинитив', mistakes=['did not went'])
def g_past_neg_oge(rng, exam):
    return g_past_neg(rng, exam)


@proto(id='eng-ege-20-present-simple', exam='ЕГЭ', n=20, n_range='19–24', title='Present Simple: окончание -s/-es у 3-го лица',
       kes=['2.4.24'], level='Б', kind='param',
       invariant='маркер регулярности (every Sunday, usually, twice a month), глагол заглавными', varies='подлежащее (лицо и число), глагол, дополнение, маркер',
       answer_rule='he/she/it → -s; после s, x, ch, sh, o → -es; согласная + y → -ies; have → has; остальные лица — словарная форма',
       mistakes=['studys, gos, watchs', 'haves', 'нет -s у he/she'])
def g_pres(rng, exam):
    subj, kind = rng.choice(G.SUBJECTS)
    v, obj = pick_verb(rng, pool=HABIT_OBJ)
    q = gap(f'{rng.choice(PRES_MARK)} {subj}', v, obj + '.')
    return card(meta_id(), q, [G.third(v) if kind == '3' else v], G.TENSE_HINT['pres']), {'v': v, 'kind': kind}


def c_pres(p, c):
    return c['a'] == [G.third2(p['v']) if p['kind'] == '3' else p['v']]


@proto(id='eng-oge-22-present-simple', exam='ОГЭ', n=22, n_range='20–28', title='Present Simple: -s/-es у 3-го лица', kes=['2.4.30'],
       level='Б', kind='param', gen_of='eng-ege-20-present-simple', invariant='маркер регулярности, глагол заглавными',
       varies='подлежащее, глагол, маркер', answer_rule='-s/-es/-ies у he/she/it, иначе словарная форма', mistakes=['gos, studys'])
def g_pres_oge(rng, exam):
    return g_pres(rng, exam)


CONT_FRAMES = [  # (before с подлежащим-заглушкой {S}, after)
    ('Look! {S}', '{obj} right now.'), ('Listen! {S}', '{obj} at the moment.'),
    ('Where is everybody? — {S}', '{obj} in the garden.'), ('Don\'t make so much noise: {S}', '{obj} now.'),
    ('Can you call back later? {S}', '{obj} at the moment.'),
]


@proto(id='eng-ege-20-present-cont', exam='ЕГЭ', n=20, n_range='19–24', title='Present Continuous: действие в момент речи',
       kes=['2.4.24'], level='Б', kind='param',
       invariant='маркер момента речи (Look!, right now, at the moment), глагол заглавными', varies='подлежащее, глагол (не моментальный), дополнение, рамка',
       answer_rule='am/is/are + V-ing; орфография -ing (make → making, swim → swimming); стяжение в ключе как второй вариант',
       mistakes=['is makeing, swiming', 'пропущен be', 'Present Simple при Look!'])
def g_cont(rng, exam):
    subj, kind = rng.choice(G.SUBJECTS)
    v, obj = pick_verb(rng, pool=CONT_OBJ)
    before, after = rng.choice(CONT_FRAMES)
    head = before[:-3].rstrip(' —')
    q = gap(before.replace('{S}', cap(subj) if not head or head[-1] in '!?' else subj), v, after.replace('{obj}', obj))
    return card(meta_id(), q, G.verb_answer('cont', v, subj, kind, MAIN), G.TENSE_HINT['cont']), {'v': v, 'subj': subj, 'kind': kind}


def c_cont(p, c):
    return c['a'] == G.verb_answer('cont', p['v'], p['subj'], p['kind'], ALT)


@proto(id='eng-oge-22-present-cont', exam='ОГЭ', n=22, n_range='20–28', title='Present Continuous', kes=['2.4.30'], level='Б', kind='param',
       gen_of='eng-ege-20-present-cont', invariant='маркер момента речи, глагол заглавными', varies='подлежащее, глагол, рамка',
       answer_rule='am/is/are + V-ing', mistakes=['swiming', 'без be'])
def g_cont_oge(rng, exam):
    return g_cont(rng, exam)


PASTCONT_FRAMES = [
    ('At six o\'clock yesterday {S}', '{obj} when the lights went out.'), ('While {S}', '{obj}, the phone rang.'),
    ('When Mum came home, {S}', '{obj}.'), ('{S}', '{obj} at this time last Sunday.'),
    ('Sorry, I didn\'t hear the doorbell: {S}', '{obj}.'), ('The children', '{obj} when the teacher came in.'),
]


@proto(id='eng-ege-20-past-cont', exam='ЕГЭ', n=20, n_range='19–24', title='Past Continuous: процесс в момент в прошлом',
       kes=['2.4.24'], level='Б', kind='param',
       invariant='момент в прошлом задан (at six o\'clock yesterday, when Mum came home, while …), глагол заглавными',
       varies='подлежащее, глагол (не моментальный), дополнение, рамка', answer_rule='was/were + V-ing; число по подлежащему',
       mistakes=['were с I/he', 'Past Simple вместо процесса', 'орфография -ing'])
def g_pastcont(rng, exam):
    subj, kind = rng.choice(G.SUBJECTS)
    v, obj = pick_verb(rng, pool=CONT_OBJ)
    before, after = rng.choice(PASTCONT_FRAMES)
    if 'I didn\'t hear' in before and subj == 'I':
        subj, kind = 'my sister', '3'
    if before == 'The children':
        subj, kind = 'the children', 'pl'
    q = gap(before.replace('{S}', cap(subj) if before.startswith('{S}') else subj), v, after.replace('{obj}', obj))
    return card(meta_id(), q, G.verb_answer('pastcont', v, subj, kind, MAIN), G.TENSE_HINT['pastcont']), {'v': v, 'subj': subj, 'kind': kind}


def c_pastcont(p, c):
    return c['a'] == G.verb_answer('pastcont', p['v'], p['subj'], p['kind'], ALT)


@proto(id='eng-oge-23-past-cont', exam='ОГЭ', n=23, n_range='20–28', title='Past Continuous', kes=['2.4.30'], level='Б', kind='param',
       gen_of='eng-ege-20-past-cont', invariant='момент в прошлом задан, глагол заглавными', varies='подлежащее, глагол, рамка',
       answer_rule='was/were + V-ing', mistakes=['were с he', 'Past Simple'])
def g_pastcont_oge(rng, exam):
    return g_pastcont(rng, exam)


PERF_STATE = [('live', 'in this town'), ('work', 'at the city hospital'), ('know', 'each other'), ('have', 'this bike'),
              ('study', 'English'), ('play', 'the piano'), ('be', 'friends'), ('collect', 'stamps')]
PERF_FRAMES = [  # (kind of frame, before, after)
    ('already', '{S}', '{obj} already, so we can go out.'), ('just', 'Look at the result! {S}', '{obj} at last.'),
    ('since', '{S}', '{state} since {year}.'), ('for', '{S}', '{state} for {n} years.'),
    ('times', '{S}', '{obj} twice this week.'), ('first', 'This is the first time {s}', '{obj}.'),
    ('never', '{S}', '{obj} before, so it will be easy.'), ('yet', 'Don\'t worry, {s}', '{obj} already — everything is ready.'),
]


@proto(id='eng-ege-21-present-perfect', exam='ЕГЭ', n=21, n_range='19–24', title='Present Perfect: результат к настоящему, since/for',
       kes=['2.4.24'], level='Б', kind='param',
       invariant='маркер результата или периода до настоящего (already, since 2019, for three years, twice this week, this is the first time …), глагол заглавными',
       varies='подлежащее, глагол, дополнение, маркер; для since/for — глаголы состояния и длительной деятельности',
       answer_rule='have/has + V3; число по подлежащему; стяжение (\'ve, \'s) — второй вариант ключа',
       mistakes=['Past Simple при since/for', 'has с they', 'V2 вместо V3 (has went)'])
def g_perf(rng, exam):
    subj, kind = rng.choice(G.SUBJECTS)
    ftype, before, after = rng.choice(PERF_FRAMES)
    if ftype in ('since', 'for'):
        v, state = rng.choice(PERF_STATE)
        after = after.replace('{state}', state).replace('{year}', str(rng.randint(2010, 2023))).replace('{n}', rng.choice(['two', 'three', 'five', 'ten']))
    else:
        v, obj = pick_verb(rng)
        if ftype in ('just', 'already', 'yet'):
            v, obj = rng.choice(CHORE_OBJ)
        elif ftype in ('first', 'never'):
            v, obj = rng.choice([x for x in G.VERB_OBJ if x[0] in ('visit', 'read', 'watch', 'cook', 'try', 'build', 'ride', 'see', 'organise')])
        after = after.replace('{obj}', obj)
    q = gap(before.replace('{S}', cap(subj)).replace('{s}', subj), v, after)
    q = cap(q)
    ans = G.verb_answer('perf', v, subj, kind, MAIN)
    if ftype in ('since', 'for') and v not in ('know', 'have', 'be'):  # с since/for допустим и Present Perfect Continuous — как в ключах ФИПИ
        ans = ans + [('has' if kind == '3' else 'have') + ' been ' + G.ing(v)]
    return card(meta_id(), q, ans, G.TENSE_HINT['perf']), {'v': v, 'subj': subj, 'kind': kind}


def c_perf(p, c):
    want = G.verb_answer('perf', p['v'], p['subj'], p['kind'], ALT)
    return c['a'][:len(want)] == want and all(x.endswith(G.ing2(p['v'])) for x in c['a'][len(want):])


@proto(id='eng-oge-23-present-perfect', exam='ОГЭ', n=23, n_range='20–28', title='Present Perfect', kes=['2.4.30'], level='Б', kind='param',
       gen_of='eng-ege-21-present-perfect', invariant='маркер already / since / for / this is the first time, глагол заглавными',
       varies='подлежащее, глагол, маркер', answer_rule='have/has + V3', mistakes=['has went', 'Past Simple при since'])
def g_perf_oge(rng, exam):
    return g_perf(rng, exam)


PASTPERF_FRAMES = [
    ('By the time {s} got to the station, the train', 'leave', '.'), ('When we arrived at the cinema, the film', 'start', 'already.'),
    ('{S}', '{v}', '{obj} before the guests came.'), ('After {s}', '{v}', '{obj}, we all went for a walk.'),
    ('By the time the guests arrived, {s}', '{v}', '{obj}.'), ('When Mum came home, {s}', '{v}', '{obj} already.'),
    ('{S} was proud: {s} ', '{v}', '{obj} without any help.'),
]



@proto(id='eng-ege-21-past-perfect', exam='ЕГЭ', n=21, n_range='19–24', title='Past Perfect: действие раньше другого в прошлом',
       kes=['2.4.24'], level='Б', kind='param',
       invariant='два действия в прошлом, порядок задан союзом или рамкой (by the time, before, after, when … already), глагол заглавными',
       varies='подлежащее, глагол, дополнение, рамка', answer_rule='had + V3 для любого лица',
       mistakes=['Past Simple для более раннего действия', 'had + V2', 'has вместо had'])
def g_pastperf(rng, exam):
    subj, kind = rng.choice(G.SUBJECTS)
    before, v, after = rng.choice(PASTPERF_FRAMES)
    if v == '{v}':
        v, obj = rng.choice(CHORE_OBJ)
        after = after.replace('{obj}', obj)
    if 'was proud' in before:
        pron = {'1': 'I', '3': 'he' if subj in ('he', 'my brother', 'Mr Petrov', 'my best friend') else 'she', 'pl': 'they'}[kind]
        if subj in ('you', 'we'):
            pron = subj
        before = before.replace('{s} ', pron)
    q = gap(before.replace('{S}', cap(subj)).replace('{s}', subj), v, after)
    return card(meta_id(), q, ['had ' + G.participle(v)], 'более раннее из двух прошедших действий → Past Perfect: had + V3'), {'v': v}


def c_pastperf(p, c):
    return c['a'] == ['had ' + G.participle2(p['v'])]


PERFCONT = [('rain', 'It', '3', 'since morning, and the streets are still wet.'), ('wait', '{S}', None, 'for the bus for forty minutes, and it still hasn\'t come.'),
            ('work', '{S}', None, 'on this project for three months, and it is almost ready.'), ('study', '{S}', None, 'Spanish since September and can already read simple texts.'),
            ('play', '{S}', None, 'tennis for an hour, and now it\'s time for a break.'), ('learn', '{S}', None, 'to drive since May and will take the test soon.')]


@proto(id='eng-ege-21-perfect-cont', exam='ЕГЭ', n=21, n_range='19–24', title='Present Perfect Continuous: процесс, длящийся до сих пор',
       kes=['2.4.24'], level='Б', kind='param',
       invariant='длительное действие с since/for, продолжающееся в момент речи; глагол деятельности заглавными',
       varies='подлежащее, глагол, период', answer_rule='have/has been + V-ing; в ключе второй вариант — Present Perfect (has worked), как в ключах ФИПИ',
       mistakes=['is working при since/for', 'has been work', 'Past Simple'])
def g_perfcont(rng, exam):
    v, s, kind, tail = rng.choice(PERFCONT)
    if s == '{S}':
        s, kind = rng.choice(G.SUBJECTS)
    aux = 'has' if kind == '3' else 'have'
    ans = [f'{aux} been {G.ing(v)}', f'{aux} {G.participle(v)}']
    if s in PRON_SUBJ:
        ans.append(("'s" if kind == '3' else "'ve") + f' been {G.ing(v)}')
    return card(meta_id(), gap(cap(s), v, tail), ans, 'since/for + действие продолжается → Present Perfect Continuous: have/has been + V-ing'), {'v': v, 'kind': kind, 's': s}


def c_perfcont(p, c):
    aux = 'has' if p['kind'] == '3' else 'have'
    return c['a'][:2] == [f'{aux} been {G.ing2(p["v"])}', f'{aux} {G.participle2(p["v"])}']


FUT_FRAMES = [('{M} {s}', '{obj}.'), ('I am sure {s}', '{obj} {m}.'), ('I think {s}', '{obj} {m}.'), ('Don\'t worry, {s}', '{obj} {m}.')]


@proto(id='eng-ege-22-future', exam='ЕГЭ', n=22, n_range='19–24', title='Future Simple: will + инфинитив',
       kes=['2.4.24', '2.4.25'], level='Б', kind='param',
       invariant='маркер будущего (tomorrow, next week, in a few days) или I\'m sure / I think, глагол заглавными',
       varies='подлежащее, глагол, дополнение, маркер, рамка', answer_rule='will + инфинитив без to; стяжение \'ll — второй вариант ключа для местоимений',
       mistakes=['will + V-s / V-ed', 'shall с he', 'Present Simple при tomorrow'])
def g_fut(rng, exam):
    subj, kind = rng.choice(G.SUBJECTS)
    v, obj = pick_verb(rng, pool=[x for x in G.VERB_OBJ if x[0] not in ACCIDENT])
    before, after = rng.choice(FUT_FRAMES)
    m = rng.choice(FUT_MARK)
    q = gap(before.replace('{M}', m).replace('{s}', subj), v, after.replace('{obj}', obj).replace('{m}', lc(m)))
    q = cap(q)
    return card(meta_id(), q, G.verb_answer('fut', v, subj, kind, MAIN), G.TENSE_HINT['fut']), {'v': v, 'subj': subj, 'kind': kind}


def c_fut(p, c):
    return c['a'] == G.verb_answer('fut', p['v'], p['subj'], p['kind'], ALT)


@proto(id='eng-oge-24-future', exam='ОГЭ', n=24, n_range='20–28', title='Future Simple', kes=['2.4.19'], level='Б', kind='param',
       gen_of='eng-ege-22-future', invariant='маркер будущего, глагол заглавными', varies='подлежащее, глагол, маркер', answer_rule='will + инфинитив',
       mistakes=['will + V-s', 'Present Simple при tomorrow'])
def g_fut_oge(rng, exam):
    return g_fut(rng, exam)


# ---------------------------------------------------------------- пассив

PASSIVE_PRES = [('The museum', 'sg', 'visit', 'by over a million people every year'), ('These cars', 'pl', 'make', 'in Japan'),
                ('English', 'sg', 'speak', 'in many countries'), ('The rooms', 'pl', 'clean', 'every morning'),
                ('Breakfast', 'sg', 'serve', 'from seven to ten'), ('The letters', 'pl', 'deliver', 'twice a day'),
                ('The festival', 'sg', 'hold', 'every August'), ('Our school newspaper', 'sg', 'print', 'once a month'),
                ('The best essays', 'pl', 'publish', 'on the school website'), ('The bread', 'sg', 'bake', 'in a stone oven'),
                ('Tea', 'sg', 'grow', 'in the south of the country'), ('The animals', 'pl', 'feed', 'twice a day'),
                ('The classroom', 'sg', 'clean', 'by the pupils on duty every day'), ('Oranges', 'pl', 'grow', 'in warm countries'),
                ('The news', 'sg', 'read', 'by the same presenter every evening'), ('Most of these toys', 'pl', 'make', 'of wood'),
                ('The school gates', 'pl', 'lock', 'at eight in the evening'), ('This cheese', 'sg', 'produce', 'in a small village in the Alps'),
                ('The lessons', 'pl', 'teach', 'in English and Russian'), ('Our house', 'sg', 'heat', 'by a wood stove in winter')]
PASSIVE_PAST = G.PASSIVE + [('The pyramids', 'pl', 'build', 'thousands of years ago'), ('The telephone', 'sg', 'invent', 'in 1876'),
                            ('The library', 'sg', 'close', 'for repairs last month'), ('The photos', 'pl', 'take', 'by my uncle'),
                            ('The medal', 'sg', 'give', 'to the youngest runner'), ('The story', 'sg', 'tell', 'to me by my grandmother'),
                            ('The first metro line in Moscow', 'sg', 'open', 'in 1935'), ('These photos', 'pl', 'take', 'during our trip to Kazan'),
                            ('The castle', 'sg', 'destroy', 'by fire in the seventeenth century'), ('Two new schools', 'pl', 'build', 'in our district last year'),
                            ('The lost dog', 'sg', 'find', 'by a group of schoolchildren'), ('The letters', 'pl', 'write', 'in French, so I could not read them'),
                            ('The match', 'sg', 'stop', 'because of the heavy rain'), ('The old trees in the park', 'pl', 'cut', 'down last spring'),
                            ('My bike', 'sg', 'steal', 'from the school yard'), ('The prizes', 'pl', 'give', 'to the winners by the mayor')]
PASSIVE_PERF = [('This book', 'sg', 'translate', 'into thirty languages so far'), ('The bridge', 'sg', 'repair', 'twice since 2010'),
                ('The rules', 'pl', 'change', 'several times this year'), ('The password', 'sg', 'change', 'recently'),
                ('All the tickets', 'pl', 'sell', 'already'), ('The road', 'sg', 'close', 'since Monday because of the floods'),
                ('The photos', 'pl', 'send', 'to all the parents already'), ('The kitchen', 'sg', 'paint', 'twice this year'),
                ('Three new stations', 'pl', 'open', 'since January'), ('The problem', 'sg', 'solve', 'at last')]
PASSIVE_MODAL = [('The report', 'must', 'send', 'by Friday'), ('The mountains', 'can', 'see', 'from our window'),
                 ('This medicine', 'should', 'keep', 'in a cool place'), ('The tickets', 'can', 'buy', 'online'),
                 ('The homework', 'must', 'do', 'by Monday'), ('Dogs', 'must', 'keep', 'on a lead in the park'),
                 ('The old bridge', 'should', 'repair', 'before winter'), ('The photos', 'can', 'print', 'in ten minutes'),
                 ('The forms', 'must', 'fill', 'in with a black pen'), ('The parcel', 'can', 'collect', 'from the post office tomorrow')]
IRR_EXTRA = {'hold': ('held', 'held'), 'feed': ('fed', 'fed')}
for k_, v_ in IRR_EXTRA.items():
    G.IRREGULAR.setdefault(k_, v_)
G.IRR_LINES = '\n'.join(f'{b} {p} {pp}' for b, (p, pp) in G.IRREGULAR.items())
PASS_BE2 = {('past', 'sg'): 'was', ('past', 'pl'): 'were', ('pres', 'sg'): 'is', ('pres', 'pl'): 'are',
            ('perf', 'sg'): 'has been', ('perf', 'pl'): 'have been'}


@proto(id='eng-ege-22-passive-past', exam='ЕГЭ', n=22, n_range='19–24', title='Past Simple Passive',
       kes=['2.4.24'], level='Б', kind='param',
       invariant='подлежащее не выполняет действие, есть маркер прошедшего (in 1898, last night, by …), глагол заглавными',
       varies='подлежащее (ед./мн.), глагол, обстоятельство', answer_rule='was/were + V3; число по подлежащему',
       mistakes=['V3 без be (The bridge built in 1898)', 'was с множественным числом', 'Past Simple актив'])
def g_pass_past(rng, exam):
    obj, num, v, tail = rng.choice(PASSIVE_PAST)
    return card(meta_id(), gap(obj, v, tail + '.'), [('was ' if num == 'sg' else 'were ') + G.participle(v)], G.TENSE_HINT['passive']), \
        {'v': v, 'num': num, 't': 'past'}


def c_pass(p, c):
    return c['a'] == [PASS_BE2[(p['t'], p['num'])] + ' ' + G.participle2(p['v'])]


@proto(id='eng-oge-25-passive-past', exam='ОГЭ', n=25, n_range='20–28', title='Past Simple Passive', kes=['2.4.31'], level='Б', kind='param',
       gen_of='eng-ege-22-passive-past', invariant='подлежащее — объект действия, маркер прошедшего, глагол заглавными',
       varies='подлежащее, глагол, обстоятельство', answer_rule='was/were + V3', mistakes=['без be', 'V2 вместо V3'])
def g_pass_past_oge(rng, exam):
    return g_pass_past(rng, exam)


@proto(id='eng-ege-22-passive-present', exam='ЕГЭ', n=22, n_range='19–24', title='Present Simple Passive',
       kes=['2.4.24'], level='Б', kind='param',
       invariant='регулярное действие над подлежащим (every year, twice a day), глагол заглавными',
       varies='подлежащее, глагол, обстоятельство', answer_rule='is/are + V3; число по подлежащему',
       mistakes=['is visit', 'are visits', 'актив (visits)'])
def g_pass_pres(rng, exam):
    obj, num, v, tail = rng.choice(PASSIVE_PRES)
    return card(meta_id(), gap(obj, v, tail + '.'), [('is ' if num == 'sg' else 'are ') + G.participle(v)],
                'регулярное действие над подлежащим → Present Simple Passive: is/are + V3'), {'v': v, 'num': num, 't': 'pres'}


@proto(id='eng-oge-25-passive-present', exam='ОГЭ', n=25, n_range='20–28', title='Present Simple Passive', kes=['2.4.31'], level='Б', kind='param',
       gen_of='eng-ege-22-passive-present', invariant='регулярное действие над подлежащим, глагол заглавными', varies='подлежащее, глагол, обстоятельство',
       answer_rule='is/are + V3', mistakes=['без be', 'актив'])
def g_pass_pres_oge(rng, exam):
    return g_pass_pres(rng, exam)


@proto(id='eng-ege-22-passive-perfect-modal', exam='ЕГЭ', n=22, n_range='19–24', title='Пассив в Present Perfect и после модальных глаголов',
       kes=['2.4.24', '2.4.26'], level='Б', kind='param',
       invariant='подлежащее — объект действия; маркер результата (so far, since 2010, already) или модальный глагол перед пропуском; глагол заглавными',
       varies='подлежащее, глагол, обстоятельство, модальный глагол', answer_rule='has/have been + V3 или be + V3 после модального',
       mistakes=['has been V2', 'must be send', 'must been sent'])
def g_pass_perf(rng, exam):
    if rng.random() < 0.5:
        obj, num, v, tail = rng.choice(PASSIVE_PERF)
        return card(meta_id(), gap(obj, v, tail + '.'), [('has been ' if num == 'sg' else 'have been ') + G.participle(v)],
                    'результат к настоящему + пассив → has/have been + V3'), {'v': v, 'num': num, 't': 'perf'}
    obj, modal, v, tail = rng.choice(PASSIVE_MODAL)
    return card(meta_id(), gap(f'{obj} {modal}', v, tail + '.'), ['be ' + G.participle(v)], 'после модального глагола пассив: be + V3'), \
        {'v': v, 'num': 'modal', 't': 'modal'}


def c_pass_perf(p, c):
    if p['t'] == 'modal':
        return c['a'] == ['be ' + G.participle2(p['v'])]
    return c_pass(p, c)


# ---------------------------------------------------------------- условные, косвенная речь, неличные формы, модальные

COND1 = [  # (if-clause subject, verb, tail, main subject, verb, tail, conj)
    ('it', 'rain', 'tomorrow', 'the match', 'move', 'to Sunday', 'If'),  # main passive? no — заменяем: (main) we, stay, at home
    ('you', 'help', 'me', 'we', 'finish', 'by five', 'If'),
    ('Anna', 'come', 'home', 'we', 'have', 'dinner', 'When'),
    ('I', 'arrive', 'in Sochi', 'I', 'call', 'you', 'As soon as'),
    ('the weather', 'be', 'good', 'the children', 'play', 'outside', 'If'),
    ('my brother', 'pass', 'the exam', 'my parents', 'buy', 'him a bike', 'If'),
    ('the shop', 'close', 'early', 'we', 'go', 'to the market', 'If'),
    ('the train', 'be', 'late', 'I', 'send', 'you a message', 'If'),
    ('Tom', 'finish', 'his homework', 'he', 'join', 'us in the park', 'When'),
    ('the guests', 'arrive', '', 'I', 'open', 'the door', 'As soon as'),
    ('the museum', 'be', 'open', 'we', 'go', 'there on Sunday', 'If'),
    ('you', 'call', 'me', 'I', 'meet', 'you at the station', 'If'),
    ('the film', 'start', '', 'everybody', 'stop', 'talking', 'When'),
    ('Kate', 'get', 'the tickets', 'she', 'send', 'us a message', 'As soon as'),
    ('the bus', 'come', '', 'we', 'get', 'to the theatre in time', 'If'),
    ('my parents', 'agree', '', 'we', 'buy', 'a puppy', 'If'),
]
COND1[0] = ('it', 'rain', 'tomorrow', 'we', 'stay', 'at home', 'If')
KIND = {s: k for s, k in G.SUBJECTS}
KIND.update({'it': '3', 'the match': '3', 'the museum': '3', 'the film': '3', 'everybody': '3', 'Kate': '3', 'the bus': '3', 'the weather': '3', 'the shop': '3', 'the train': '3', 'the children': 'pl', 'the guests': 'pl',
             'my parents': 'pl', 'Tom': '3', 'my brother': '3', 'Anna': '3'})


def pres_form(v, kind, f):
    if v == 'be':
        return {'1': 'am', '3': 'is', 'pl': 'are'}[kind]
    return f(v) if kind == '3' else v


@proto(id='eng-ege-23-conditional-1', exam='ЕГЭ', n=23, n_range='19–24', title='Условное I и придаточные времени: Present Simple после if/when, will в главном',
       kes=['2.4.12', '2.4.24'], level='Б', kind='param',
       invariant='сложное предложение с if / when / as soon as о будущем; пропуск либо в придаточном (нужен Present Simple), либо в главном (will + V); глагол заглавными',
       varies='какая часть с пропуском, союз, подлежащие, глаголы', answer_rule='придаточное условия/времени — Present Simple (-s у 3-го лица), главное — will + инфинитив',
       mistakes=['will после if/when', 'нет -s в придаточном (if he come)', 'Present Simple в главном'])
def g_cond1(rng, exam):
    s1, v1, t1, s2, v2, t2, conj = rng.choice(COND1)
    where = rng.choice(['if', 'main'])
    k1, k2 = KIND[s1], KIND[s2]
    if where == 'if':
        main = f'{s2} will {v2} {t2}'.strip()
        q = gap(f'{conj} {s1}', v1, f'{t1}, {main}.'.replace(' ,', ','))
        ans = [pres_form(v1, k1, G.third)]
        p = {'where': 'if', 'v': v1, 'kind': k1}
    else:
        cond = f'{conj} {s1} {pres_form(v1, k1, G.third)} {t1}'.strip()
        q = gap(f'{cond}, {s2}', v2, t2 + '.')
        ans = ['will ' + v2] + (["'ll " + v2] if s2 in PRON_SUBJ else [])
        p = {'where': 'main', 'v': v2, 'kind': k2, 's': s2}
    return card(meta_id(), q, ans, 'после if/when/as soon as о будущем — Present Simple; в главном предложении — will + V'), p


def c_cond1(p, c):
    if p['where'] == 'if':
        return c['a'] == [pres_form(p['v'], p['kind'], G.third2)]
    return c['a'] == G.verb_answer('fut', p['v'], p['s'], p['kind'], ALT)


@proto(id='eng-oge-26-conditional-1', exam='ОГЭ', n=26, n_range='20–28', title='Условное I и придаточные времени', kes=['2.4.10', '2.4.19'], level='Б', kind='param',
       gen_of='eng-ege-23-conditional-1', invariant='if / when о будущем, пропуск в одной части, глагол заглавными', varies='часть с пропуском, союз, подлежащие, глаголы',
       answer_rule='Present Simple после if/when, will в главном', mistakes=['will после if'])
def g_cond1_oge(rng, exam):
    return g_cond1(rng, exam)


COND2 = [  # (if subject, verb, tail, main subject, verb, tail)
    ('I', 'have', 'more free time', 'I', 'learn', 'to play the guitar'), ('Tom', 'be', 'taller', 'he', 'join', 'the basketball team'),
    ('we', 'live', 'nearer', 'we', 'visit', 'you more often'), ('you', 'read', 'more', 'you', 'write', 'better essays'),
    ('I', 'be', 'you', 'I', 'tell', 'the teacher the truth'), ('my parents', 'have', 'a car', 'we', 'go', 'to the sea every weekend'),
    ('Kate', 'know', 'his number', 'she', 'call', 'him at once'), ('it', 'be', 'warmer', 'we', 'swim', 'in the lake'),
    ('the shop', 'sell', 'fresh fish', 'Grandma', 'buy', 'it every day'), ('I', 'speak', 'Chinese', 'I', 'work', 'in Shanghai'),
    ('the weather', 'be', 'better', 'we', 'have', 'the picnic in the park'), ('you', 'go', 'to bed earlier', 'you', 'feel', 'better in the morning'),
    ('my brother', 'have', 'a bike', 'he', 'ride', 'to school every day'), ('I', 'live', 'in Moscow', 'I', 'visit', 'the Tretyakov Gallery every month'),
    ('the tickets', 'cost', 'less', 'more people', 'come', 'to the concert'), ('Nick', 'train', 'harder', 'he', 'win', 'the race'),
]


@proto(id='eng-ege-23-conditional-2', exam='ЕГЭ', n=23, n_range='19–24', title='Условное II: Past Simple после if, would в главном',
       kes=['2.4.12'], level='Б', kind='param',
       invariant='нереальное условие в настоящем: во второй части would + V (если пропуск в if-части) или Past Simple в if-части (если пропуск в главной); глагол заглавными',
       varies='часть с пропуском, подлежащие, глаголы', answer_rule='if-часть — Past Simple (be → were, was допустим), главная — would + инфинитив',
       mistakes=['would после if', 'Present Simple в if-части', 'would + V2'])
def g_cond2(rng, exam):
    s1, v1, t1, s2, v2, t2 = rng.choice(COND2)
    where = rng.choice(['if', 'main'])
    if where == 'if':
        q = gap(f'If {s1}', v1, f'{t1}, {s2} would {v2} {t2}.')
        ans = ['were', 'was'] if v1 == 'be' else [G.past(v1)]
        p = {'where': 'if', 'v': v1}
    else:
        past1 = 'were' if v1 == 'be' else G.past(v1)
        q = gap(f'If {s1} {past1} {t1}, {s2}', v2, t2 + '.')
        ans = ['would ' + v2] + (["'d " + v2] if s2 in PRON_SUBJ else [])
        p = {'where': 'main', 'v': v2, 's': s2}
    return card(meta_id(), cap(q), ans, 'нереальное условие: If + Past Simple, … would + V'), p


def c_cond2(p, c):
    if p['where'] == 'if':
        return c['a'] == (['were', 'was'] if p['v'] == 'be' else [G.past2(p['v'])])
    return c['a'] == ['would ' + p['v']] + (["'d " + p['v']] if p['s'] in PRON_SUBJ else [])


@proto(id='eng-oge-26-conditional-2', exam='ОГЭ', n=26, n_range='20–28', title='Условное II', kes=['2.4.11'], level='Б', kind='param',
       gen_of='eng-ege-23-conditional-2', invariant='нереальное условие, пропуск в одной части, глагол заглавными', varies='часть с пропуском, подлежащие, глаголы',
       answer_rule='Past Simple после if, would + V в главном', mistakes=['would после if'])
def g_cond2_oge(rng, exam):
    return g_cond2(rng, exam)


REPORTED = [  # (тип прямой речи, рамка-начало, глагол, хвост)
    ('past', 'Tom said that he', 'finish', 'the project the day before.'), ('past', 'Kate told me that she', 'see', 'that film a week before.'),
    ('past', 'The boys said that they', 'lose', 'the keys the previous evening.'), ('past', 'Mum said that she', 'buy', 'the tickets two days before.'),
    ('will', 'Ann promised that she', 'help', 'me with the project the following day.'), ('will', 'The teacher said that we', 'write', 'a test the next week.'),
    ('will', 'Dad said that he', 'meet', 'us at the station the following morning.'), ('will', 'Nick told us that he', 'bring', 'the camera the next day.'),
    ('cont', 'Kate said that she', 'watch', 'a film at that moment.'), ('cont', 'The twins said that they', 'wait', 'for the bus then.'),
    ('cont', 'Sam told me that he', 'read', 'a book about space at that moment.'),
    ('can', 'Tom said that he', 'can', 'swim across the river easily.'), ('can', 'Anna told me that she', 'can', 'not come the following day.'),
    ('is', 'My friend said that he', 'be', 'busy at that moment.'), ('is', 'The girls said that they', 'be', 'tired after the trip.'),
]
KIND_REP = {'he': '3', 'she': '3', 'they': 'pl', 'we': 'pl'}


@proto(id='eng-ege-23-reported', exam='ЕГЭ', n=23, n_range='19–24', title='Косвенная речь: сдвиг времён',
       kes=['2.4.14', '2.4.15'], level='Б', kind='param',
       invariant='главное предложение в прошедшем (said / told … that), в придаточном — маркер сдвига (the day before, the following day, at that moment); глагол заглавными',
       varies='тип сдвига (Past → Past Perfect, will → would, Present Continuous → Past Continuous, can → could, is → was), подлежащее, глагол',
       answer_rule='таблица сдвига времён; ключ допускает стяжения и, для будущего, was/were going to',
       mistakes=['нет сдвига (he finishes / he will)', 'had + V2', 'would + V-ed'])
def g_reported(rng, exam):
    t, before, v, tail = rng.choice(REPORTED)
    subj = before.split()[-1]
    kind = KIND_REP[subj]
    if t == 'past':
        ans = ['had ' + G.participle(v)]
    elif t == 'will':
        ans = ['would ' + v, ('was ' if kind == '3' else 'were ') + 'going to ' + v]
    elif t == 'cont':
        ans = [('was ' if kind == '3' else 'were ') + G.ing(v)]
    elif t == 'can':
        ans = ['could'] if 'not' not in tail else ['could not', "couldn't"]
        if 'not' in tail:
            tail = tail.replace('not ', '')
            q = gap(before, 'can not', tail)
            return card(meta_id(), q, ans, 'косвенная речь после said/told: can → could'), {'t': t, 'v': v, 'kind': kind, 'neg': True}
    else:
        ans = ['was' if kind == '3' else 'were']
    q = gap(before, v, tail)
    return card(meta_id(), q, ans, 'косвенная речь после said/told: время сдвигается на шаг назад (Past → Past Perfect, will → would, is → was)'), \
        {'t': t, 'v': v, 'kind': kind}


def c_reported(p, c):
    """Обратное преобразование: из ответа восстанавливаем форму прямой речи и сверяем с типом."""
    a = c['a'][0]
    v, kind = p['v'], p['kind']
    if p['t'] == 'past':
        return a.startswith('had ') and a[4:] == G.participle2(v)
    if p['t'] == 'will':
        return a == 'would ' + v and c['a'][1].endswith('going to ' + v)
    if p['t'] == 'cont':
        be, ing = a.split(' ', 1)
        return {'was': '3', 'were': 'pl'}[be] == kind and ing == G.ing2(v)
    if p['t'] == 'can':
        return a in ('could', 'could not') and (('not' in a) == p.get('neg', False))
    return {'was': '3', 'were': 'pl'}[a] == kind


@proto(id='eng-oge-27-reported', exam='ОГЭ', n=27, n_range='20–28', title='Косвенная речь: сдвиг времён', kes=['2.4.12', '2.4.13'], level='Б', kind='param',
       gen_of='eng-ege-23-reported', invariant='said/told … that + маркер сдвига, глагол заглавными', varies='тип сдвига, подлежащее, глагол',
       answer_rule='таблица сдвига времён', mistakes=['нет сдвига'])
def g_reported_oge(rng, exam):
    return g_reported(rng, exam)


GOV_FRAMES = [  # (управляющая фраза с подлежащим, глагол, хвост, тип: ger / inf / bare)
    ('My sister enjoys', 'swim', 'in the lake early in the morning.', 'ger'), ('We have finished', 'decorate', 'the hall for the party.', 'ger'),
    ('Try to avoid', 'eat', 'sweets before dinner.', 'ger'), ('Would you mind', 'open', 'the window, please?', 'ger'),
    ('Dad suggested', 'go', 'to the mountains in July.', 'ger'), ('The baby kept', 'cry', 'all night.', 'ger'),
    ('Grandpa gave up', 'smoke', 'ten years ago.', 'ger'), ('You should practise', 'speak', 'English every day.', 'ger'),
    ('I can\'t stand', 'wait', 'in long queues.', 'ger'), ('We are looking forward to', 'see', 'you in August.', 'ger'),
    ('Nina is good at', 'draw', 'animals.', 'ger'), ('Are you interested in', 'collect', 'old coins?', 'ger'),
    ('My cousins are fond of', 'ride', 'horses.', 'ger'), ('Stop', 'talk', 'and listen to the teacher.', 'ger'),
    ('I want', 'visit', 'Japan one day.', 'inf'), ('They decided', 'stay', 'at home because of the rain.', 'inf'),
    ('We hope', 'win', 'the final match.', 'inf'), ('Tom promised', 'call', 'me in the evening.', 'inf'),
    ('The boy refused', 'eat', 'his soup.', 'inf'), ('We are planning', 'travel', 'around Europe by train.', 'inf'),
    ('My neighbour offered', 'help', 'me with the bags.', 'inf'), ('Last year I learnt', 'play', 'chess.', 'inf'),
    ('Luckily, we managed', 'catch', 'the last bus.', 'inf'), ('Mum agreed', 'buy', 'me a new phone.', 'inf'),
    ('I would like', 'thank', 'everybody for the help.', 'inf'), ('You need', 'sleep', 'more before the exam.', 'inf'),
    ('We expect', 'arrive', 'in Moscow at noon.', 'inf'), ('Don\'t forget', 'lock', 'the door when you leave.', 'inf'),
    ('Let me', 'carry', 'the bag for you.', 'bare'), ('The teacher made us', 'rewrite', 'the essay.', 'bare'),
    ('You had better', 'take', 'an umbrella.', 'bare'), ('I would rather', 'walk', 'than take a taxi.', 'bare'),
    ('My little brother can already', 'read', 'short stories.', 'bare'), ('Everybody must', 'wear', 'a helmet here.', 'bare'),
    ('You should', 'drink', 'more water in summer.', 'bare'), ('Our parents let us', 'stay', 'up late on Saturdays.', 'bare'),
]
# вторая таблица: поверхностная форма управляющего слова → тип (для независимой проверки)
GOV2 = {}
for _t, _ws in (('ger', 'enjoys|finished|avoid|mind|suggested|kept|gave up|practise|stand|looking forward to|good at|interested in|fond of|stop'),
                ('inf', 'want|decided|hope|promised|refused|planning|offered|learnt|managed|agreed|would like|need|expect|forget'),
                ('bare', 'let me|made us|had better|would rather|can already|must|should|let us')):
    for _w in _ws.split('|'):
        GOV2[_w] = _t


@proto(id='eng-ege-23-gerund-infinitive', exam='ЕГЭ', n=23, n_range='19–24', title='Герундий, инфинитив с to и без to после глаголов',
       kes=['2.4.18', '2.4.19', '2.4.27'], level='Б', kind='param',
       invariant='управляющий глагол или выражение стоит перед пропуском (enjoy, want, let, would rather, look forward to); глагол заглавными',
       varies='управляющее слово, глагол в пропуске, дополнение', answer_rule='таблица управления: enjoy/finish/mind/look forward to → V-ing; want/decide/hope → to + V; let/make/modal/had better → V',
       mistakes=['enjoy to swim', 'look forward to see', 'let me to carry', 'орфография -ing'])
def g_gov(rng, exam):
    before, v, tail, t = rng.choice(GOV_FRAMES)
    ans = [G.ing(v) if t == 'ger' else 'to ' + v if t == 'inf' else v]
    return card(meta_id(), gap(before, v, tail), ans, 'после enjoy, finish, mind, look forward to — V-ing; после want, decide, hope — to + V; после let, make, модальных — V'), \
        {'before': before, 'v': v}


def c_gov(p, c):
    b = p['before'].lower()
    keys = [w for w in GOV2 if b.endswith(w)]
    if not keys:
        return False
    t = GOV2[max(keys, key=len)]  # вторая таблица: тип управления по поверхностной форме в конце рамки
    return c['a'] == [G.ing2(p['v']) if t == 'ger' else 'to ' + p['v'] if t == 'inf' else p['v']]


@proto(id='eng-oge-27-gerund-infinitive', exam='ОГЭ', n=27, n_range='20–28', title='Герундий и инфинитив после глаголов', kes=['2.4.15', '2.4.33'], level='Б', kind='param',
       gen_of='eng-ege-23-gerund-infinitive', invariant='управляющее слово перед пропуском, глагол заглавными', varies='управляющее слово, глагол',
       answer_rule='таблица управления', mistakes=['enjoy to swim', 'let me to go'])
def g_gov_oge(rng, exam):
    return g_gov(rng, exam)


MODAL_FRAMES = [  # (before, word, after, answer list)
    ('When I was five, I', 'can', 'already read.', ['could']), ('Yesterday Sam', 'can', 'not come to the training.', ['could not', "couldn't"]),
    ('Last winter we', 'can', 'skate on the lake every day.', ['could']), ('Ten years ago my grandfather', 'can', 'run five kilometres.', ['could']),
    ('Yesterday I', 'have to', 'stay at home and look after my little sister.', ['had to']), ('Last week the pupils', 'have to', 'wear school uniform.', ['had to']),
    ('Anna', 'have to', 'get up at six every day because she lives far from school.', ['has to']),
    ('My brother', 'have to', 'help Dad in the garage every Saturday.', ['has to']),
    ('Luckily, we', 'be able to', 'find the way back before it got dark.', ['were able to']),
    ('In the end I', 'be able to', 'open the old lock.', ['was able to']),
    ('After the operation Grandma', 'be able to', 'walk again.', ['was able to']),
    ('The firemen', 'be able to', 'save everybody from the burning house.', ['were able to']),
    ('When my grandmother was young, she', 'can', 'sing beautifully.', ['could']), ('Last year the pupils', 'can', 'not use phones at school.', ['could not', "couldn't"]),
    ('Last Sunday we', 'have to', 'clean the whole flat before the guests came.', ['had to']), ('My mother', 'have to', 'work on Saturdays this month.', ['has to']),
    ('Yesterday Nick', 'have to', 'stay at school after the lessons.', ['had to']), ('Every morning my sister', 'have to', 'walk the dog before school.', ['has to']),
    ('Finally the climbers', 'be able to', 'reach the top of the mountain.', ['were able to']), ('After a few lessons Ann', 'be able to', 'swim across the pool.', ['was able to']),
]
MODAL2 = {('can', 'past'): 'could', ('have to', 'past'): 'had to', ('have to', 'pres3'): 'has to', ('be able to', 'past-sg'): 'was able to',
          ('be able to', 'past-pl'): 'were able to'}
MODAL_KEY = {  # вторая таблица: рамка → признак
    'When I was five, I': ('can', 'past'), 'Yesterday Sam': ('can', 'past'), 'Last winter we': ('can', 'past'), 'Ten years ago my grandfather': ('can', 'past'),
    'Yesterday I': ('have to', 'past'), 'Last week the pupils': ('have to', 'past'), 'Anna': ('have to', 'pres3'), 'My brother': ('have to', 'pres3'),
    'Luckily, we': ('be able to', 'past-pl'), 'In the end I': ('be able to', 'past-sg'), 'After the operation Grandma': ('be able to', 'past-sg'),
    'The firemen': ('be able to', 'past-pl'), 'When my grandmother was young, she': ('can', 'past'), 'Last year the pupils': ('can', 'past'),
    'Last Sunday we': ('have to', 'past'), 'My mother': ('have to', 'pres3'), 'Yesterday Nick': ('have to', 'past'), 'Every morning my sister': ('have to', 'pres3'),
    'Finally the climbers': ('be able to', 'past-pl'), 'After a few lessons Ann': ('be able to', 'past-sg'),
}


@proto(id='eng-ege-23-modal', exam='ЕГЭ', n=23, n_range='19–24', title='Модальные глаголы и эквиваленты: can → could, have to → had to / has to, be able to',
       kes=['2.4.26'], level='Б', kind='param',
       invariant='маркер времени и подлежащее задают форму модального глагола или эквивалента; в скобках CAN, HAVE TO или BE ABLE TO',
       varies='рамка, подлежащее, маркер', answer_rule='таблица: can → could в прошедшем, have to → had to / has to, be able to → was/were able to',
       mistakes=['can в прошедшем', 'have to с he/she', 'was able с they'])
def g_modal(rng, exam):
    before, word, after, ans = rng.choice(MODAL_FRAMES)
    if 'not' in after and word == 'can':
        return card(meta_id(), gap(before, 'can not', after.replace('not ', '')), ans, 'can в прошедшем → could'), {'before': before, 'neg': True}
    return card(meta_id(), gap(before, word, after), ans, 'can → could, have to → had to (прошедшее) / has to (he, she), be able to → was/were able to'), {'before': before}


def c_modal(p, c):
    a = MODAL2[MODAL_KEY[p['before']]]
    if p.get('neg'):
        return c['a'] == [a + ' not', a + "n't"]
    return c['a'] == [a]


@proto(id='eng-oge-28-modal', exam='ОГЭ', n=28, n_range='20–28', title='Модальные глаголы и эквиваленты', kes=['2.4.34'], level='Б', kind='param',
       gen_of='eng-ege-23-modal', invariant='маркер времени задаёт форму, в скобках CAN / HAVE TO / BE ABLE TO', varies='рамка, подлежащее',
       answer_rule='таблица форм', mistakes=['can в прошедшем'])
def g_modal_oge(rng, exam):
    return g_modal(rng, exam)


# ---------------------------------------------------------------- существительные, прилагательные, числительные, местоимения

NOUN_FRAMES = G.NOUN_FRAMES + [
    ('child', 'Most', 'in our class have pets.'), ('woman', 'Three', 'in white coats came into the room.'),
    ('foot', 'The table is about six', 'long.'), ('mouse', 'There are', 'in the old barn, so we need a cat.'),
    ('person', 'How many', 'live in your village?'), ('life', 'The doctors saved many', 'that night.'),
    ('wolf', 'A pack of', 'was seen near the village.'), ('half', 'Cut the apples into', 'and put them on a plate.'),
    ('sandwich', 'Mum made ten', 'for the picnic.'), ('story', 'Grandad tells the best', 'in the world.'),
    ('family', 'Two', 'from Kazan moved into our house last month.'), ('strawberry', 'We picked', 'in the garden all morning.'),
    ('boy', 'The', 'from the fifth form won the football match.'), ('class', 'Our school has two', 'of ten-year-olds.'),
    ('church', 'The old town has five', 'and a monastery.'), ('video', 'My brother makes', 'about cooking.'),
    ('holiday', 'Where do you usually spend your summer', '?'), ('brush', 'Wash the', 'after painting.'),
    ('fish', 'We caught seven', 'in two hours!'), ('deer', 'In winter', 'come close to the houses looking for food.'),
    ('thief', 'The police caught the', 'the same night.'), ('goose', 'Grandma keeps ten', 'and a lot of hens.'),
]


@proto(id='eng-ege-24-plural', exam='ЕГЭ', n=24, n_range='19–24', title='Множественное число существительных',
       kes=['2.4.29', '2.4.30'], level='Б', kind='param',
       invariant='числительное или контекст множественности перед пропуском, существительное заглавными в единственном числе',
       varies='существительное: правильное (-s, -es, -ies), исключения (children, feet, knives, sheep), рамка', answer_rule='таблица исключений, иначе правило: -s; после s, x, ch, sh → -es; согласная + y → -ies; -f(e) → -ves',
       mistakes=['childs, mans, foots', 'citys, familys', 'knifes', 'sheeps, fishes'])
def g_plural(rng, exam):
    n, a, b = rng.choice(NOUN_FRAMES)
    return card(meta_id(), gap(a, n, b), [G.plural(n)], 'множественное число: -s; после s, x, ch, sh → -es; согласная + y → -ies; исключения учим списком'), {'n': n}


def c_plural(p, c):
    n = p['n']
    if n in G.PLURAL_IRR:
        return c['a'] == [G.PLURAL_IRR[n]]
    for pat, rep in ((r'(s|x|ch|sh)$', r'\1es'), (r'([^aeiou])y$', r'\1ies')):
        if re.search(pat, n):
            return c['a'] == [re.sub(pat, rep, n)]
    return c['a'] == [n + 's']


@proto(id='eng-oge-28-plural', exam='ОГЭ', n=28, n_range='20–28', title='Множественное число существительных', kes=['2.4.37', '2.4.38'], level='Б', kind='param',
       gen_of='eng-ege-24-plural', invariant='контекст множественности, существительное заглавными', varies='существительное, рамка',
       answer_rule='правило -s/-es/-ies/-ves и таблица исключений', mistakes=['childs', 'citys'])
def g_plural_oge(rng, exam):
    return g_plural(rng, exam)


EVAL = ['good', 'bad', 'interesting', 'boring', 'exciting', 'difficult', 'easy', 'useful', 'important', 'popular', 'famous']
THING = EVAL + ['expensive', 'cheap', 'nice', 'big', 'large', 'long', 'short', 'comfortable', 'beautiful', 'quiet', 'safe', 'dangerous', 'clean']
ADJ_FRAMES_CMP = [  # (before, after, допустимые прилагательные)
    ('This year\'s exam was', 'than last year\'s.', EVAL + ['long', 'short']),
    ('Our new flat is', 'than the old one.', ['big', 'large', 'small', 'nice', 'comfortable', 'quiet', 'warm', 'cheap', 'expensive', 'clean', 'beautiful', 'good']),
    ('The second film is', 'than the first.', EVAL + ['long', 'short', 'funny', 'sad']),
    ('The road through the forest is', 'than the highway.', ['long', 'short', 'dangerous', 'safe', 'quiet', 'busy', 'beautiful', 'bad', 'good', 'narrow']),
    ('My new phone is much', 'than the old one.', ['good', 'fast', 'cheap', 'expensive', 'big', 'small', 'thin', 'light', 'useful', 'nice']),
    ('The film was', 'than the book, to be honest.', EVAL + ['funny', 'sad', 'short', 'long']),
    ('Living in the country is', 'than living in the city.', ['cheap', 'quiet', 'safe', 'healthy', 'boring', 'interesting', 'difficult', 'easy', 'comfortable', 'good']),
    ('Today the sea is', 'than it was yesterday.', ['warm', 'cold', 'quiet', 'calm', 'rough', 'clean']),
    ('My brother is', 'than me, but I am taller.', ['old', 'young', 'strong', 'fast', 'clever', 'funny', 'quiet', 'busy', 'lazy']),
    ('The weather today is', 'than the forecast promised.', ['warm', 'cold', 'wet', 'good', 'bad', 'nice', 'hot', 'windy']),
]
ADJ_FRAMES_SUP = [
    ('It was the', 'day of the whole trip.', ['hot', 'cold', 'wet', 'long', 'short', 'busy', 'nice', 'good', 'bad', 'happy', 'boring', 'exciting', 'interesting']),
    ('Kate is the', 'player in our team.', ['good', 'bad', 'fast', 'slow', 'strong', 'young', 'old', 'tall', 'careful', 'popular', 'famous']),
    ('This is the', 'place in the city, in my opinion.', ['beautiful', 'quiet', 'dangerous', 'safe', 'popular', 'famous', 'busy', 'clean', 'expensive', 'cheap', 'interesting', 'nice', 'ugly']),
    ('That was the', 'lesson of the week.', EVAL + ['long', 'short', 'funny']),
    ('My grandfather is the', 'person I know.', ['kind', 'clever', 'funny', 'calm', 'busy', 'strong', 'happy', 'wise', 'patient', 'polite', 'old']),
    ('It is the', 'restaurant in our town.', ['expensive', 'cheap', 'popular', 'famous', 'nice', 'good', 'bad', 'big', 'busy', 'comfortable', 'old', 'new']),
    ('What is the', 'way to get to the airport?', ['fast', 'slow', 'cheap', 'expensive', 'easy', 'difficult', 'short', 'long', 'safe', 'dangerous', 'quick', 'good']),
    ('Sunday was the', 'day of the holidays.', ['hot', 'cold', 'wet', 'long', 'busy', 'nice', 'good', 'bad', 'happy', 'boring', 'exciting', 'quiet']),
    ('The blue whale is the', 'animal on the planet.', ['big', 'large', 'heavy', 'long', 'loud']),
    ('This is the', 'book I have ever read.', EVAL + ['long', 'short', 'funny', 'sad', 'strange']),
]
G.ADJ_LONG |= {'careful', 'patient', 'polite'}
G.ADJ_DOUBLE |= {'sad'}
QUANT_FRAMES = [('many', 'There are', 'cars in the city centre than ten years ago.', 0), ('little', 'I have', 'free time than last year.', 0),
                ('much', 'Nowadays people spend', 'time online than they did before.', 0), ('far', 'The station is', 'from here than the bus stop.', 0),
                ('little', 'Ann made the', 'mistakes in the test.', 1), ('many', 'Who has got the', 'points in the game?', 1),
                ('far', 'Pluto is the', 'planet from the Sun.', 1)]
ADJ_IRR2 = {'good': 'better|best', 'bad': 'worse|worst', 'far': 'farther|farthest', 'little': 'less|least', 'many': 'more|most', 'much': 'more|most'}


@proto(id='eng-ege-24-comparison', exam='ЕГЭ', n=24, n_range='19–24', title='Степени сравнения прилагательных и наречий',
       kes=['2.4.33', '2.4.35'], level='Б', kind='param',
       invariant='than → сравнительная, the … in/of → превосходная; прилагательное (или many/much/little/far) заглавными',
       varies='прилагательное: короткое (-er/-est с орфографией), длинное (more/most), исключения (good, bad, far, little, many)', answer_rule='две таблицы (исключения, длинные) и правило орфографии: big → bigger, easy → easier, nice → nicer; для far — farther/further оба в ключе',
       mistakes=['more better, most biggest', 'biger, easyer', 'gooder', 'much вместо more'])
def g_cmp(rng, exam):
    if rng.random() < 0.25:
        a, before, after, deg = rng.choice(QUANT_FRAMES)
    else:
        deg = rng.randint(0, 1)
        before, after, allowed = rng.choice(ADJ_FRAMES_SUP if deg else ADJ_FRAMES_CMP)
        a = rng.choice(allowed)
    ans = [G.compare(a, deg)]
    if a == 'far':
        ans.append(('further', 'furthest')[deg])
    return card(meta_id(), gap(before, a, after), ans, 'than → сравнительная степень; the … of/in → превосходная; длинные — more/most; good — better — best'), {'a': a, 'deg': deg}


def c_cmp(p, c):
    a, deg = p['a'], p['deg']
    if a in ADJ_IRR2:
        return c['a'][0] == ADJ_IRR2[a].split('|')[deg]
    if a in ('careful', 'patient', 'polite', 'narrow'):  # двусложные без -er/-est в наших рамках: more/most
        return c['a'][0] == ('more ', 'most ')[deg] + a if a != 'narrow' else c['a'][0] == 'narrow' + ('er', 'est')[deg]
    return G.check_adj(p, {'a': c['a'][:1]})


@proto(id='eng-oge-28-comparison', exam='ОГЭ', n=28, n_range='20–28', title='Степени сравнения', kes=['2.4.39', '2.4.40', '2.4.42'], level='Б', kind='param',
       gen_of='eng-ege-24-comparison', invariant='than или the … in/of, прилагательное заглавными', varies='прилагательное, рамка',
       answer_rule='таблицы и правило орфографии', mistakes=['more better', 'biger'])
def g_cmp_oge(rng, exam):
    return g_cmp(rng, exam)


ORD_FRAMES = G.ORD_FRAMES + [('My birthday is on the', 'of May.'), ('The school was founded in the', 'century.'),
                             ('We got off at the', 'stop.'), ('Read the', 'paragraph and answer the questions.')]


@proto(id='eng-ege-24-ordinal', exam='ЕГЭ', n=24, n_range='19–24', title='Порядковые числительные',
       kes=['2.4.37'], level='Б', kind='param',
       invariant='контекст порядка (the … floor, came … in the race, on the … of May, … century), количественное числительное словом заглавными',
       varies='число 1–99 (для century — до 21), рамка', answer_rule='таблица исключений (first, second, third, fifth, eighth, ninth, twelfth), -y → -ieth, иначе -th; в составных меняется последняя часть',
       mistakes=['fiveth, nineth, twelveth', 'twentyth', 'oneth', 'twenty-oneth'])
def g_ord(rng, exam):
    before, after = rng.choice(ORD_FRAMES)
    lim = {'century.': 21, 'of May.': 31, 'floor.': 25, 'in the race.': 30, 'house on the left.': 10, 'stop.': 12, 'paragraph and answer the questions.': 12,
           'time I have read this book.': 10}.get(after, 99)
    n = rng.randint(1, lim)
    return card(meta_id(), gap(before, G.words(n), after), [G.ordinal(n)],
                'one → first, two → second, three → third, five → fifth, nine → ninth, twelve → twelfth, twenty → twentieth; в составных меняется только последнее слово'), {'n': n}


def c_ord(p, c):
    if not G.check_ord(p, c):
        return False
    # второй способ: словесная форма числа восстанавливается из ответа обратной заменой суффиксов
    a = c['a'][0]
    back = {'first': 'one', 'second': 'two', 'third': 'three', 'fifth': 'five', 'eighth': 'eight', 'ninth': 'nine', 'twelfth': 'twelve'}
    head, _, last = a.rpartition('-')
    w = back.get(last) or (last[:-4] + 'y' if last.endswith('ieth') else last[:-2])
    return (head + '-' if head else '') + w == G.words(p['n'])


@proto(id='eng-oge-28-ordinal', exam='ОГЭ', n=28, n_range='20–28', title='Порядковые числительные', kes=['2.4.50'], level='Б', kind='param',
       gen_of='eng-ege-24-ordinal', invariant='контекст порядка, числительное словом заглавными', varies='число, рамка',
       answer_rule='таблица исключений и -th', mistakes=['fiveth', 'twelveth'])
def g_ord_oge(rng, exam):
    return g_ord(rng, exam)


POSS_ADJ = {'I': 'my', 'you': 'your', 'he': 'his', 'she': 'her', 'we': 'our', 'they': 'their'}
PRON_FRAMES = [(k, b, a, None) for k, b, a in G.PRON_FRAMES] + [
    (3, 'The children forgot', 'umbrellas at school.', ['they']), (3, 'Anna is showing', 'new phone to everybody.', ['she']),
    (3, 'My brother lost', 'keys again.', ['he']), (3, 'We painted', 'garden fence green.', ['we']),
    (3, 'I can\'t find', 'glasses anywhere.', ['I']), (3, 'Have you done', 'homework yet?', ['you']),
    (0, 'My aunt sent', 'a parcel from Spain.', ['I', 'we', 'he', 'she', 'they']), (0, 'Please wait for', 'at the entrance.', ['I', 'we', 'he', 'she', 'they']),
    (0, 'The teacher gave', 'an extra day for the project.', ['I', 'we', 'he', 'she', 'they']),
    (1, 'This is not your pen, it is', '.', ['I', 'he', 'she', 'we', 'they']), (1, 'Their garden is bigger than', '.', ['I', 'he', 'she', 'we', 'you']),
    (2, 'My grandfather built this house', 'when he was young.', ['he']), (2, 'I cut', 'while I was cooking.', ['I']),
    (2, 'My sister taught', 'to play the guitar.', ['she']), (2, 'Did you make this cake', '?', ['you']),
    (2, 'We enjoyed', 'at the party.', ['we']), (2, 'Ann and Kate looked at', 'in the mirror.', ['they']),
]
PRON_OK_ALL = {(k, b): (ok or G.PRON_OK.get((k, b)) or list(G.PRON)) for k, b, a, ok in PRON_FRAMES}


@proto(id='eng-ege-24-pronoun', exam='ЕГЭ', n=24, n_range='19–24', title='Местоимения: объектные, притяжательные (two forms), возвратные',
       kes=['2.4.36'], level='Б', kind='param',
       invariant='личное местоимение заглавными (I, HE, THEY…); рамка задаёт падеж или разряд: после глагола/предлога — объектное, перед существительным — притяжательное, без существительного — абсолютное, by/сам — возвратное',
       varies='местоимение, разряд, рамка', answer_rule='таблица форм по лицу и разряду', mistakes=['between you and I', 'theirs umbrellas', 'hisself, theirselves', 'me вместо my'])
def g_pron(rng, exam):
    k, b, a, ok = rng.choice(PRON_FRAMES)
    p = rng.choice(PRON_OK_ALL[(k, b)])
    if k == 1 and p == 'I' and 'Whose bikes' in b:
        p = 'we'
    ans = [POSS_ADJ[p] if k == 3 else G.PRON[p][k]]
    return card(meta_id(), gap(b, p, a), ans, 'после глагола/предлога — me, him, us; перед существительным — my, his, their; без существительного — mine, hers; сам — -self/-selves'), \
        {'p': p, 'kind': k}


def c_pron(p, c):
    rows = 'I me mine myself my|you you yours yourself your|he him his himself his|she her hers herself her|we us ours ourselves our|they them theirs themselves their'
    t = {r.split()[0]: r.split()[1:] for r in rows.split('|')}
    return c['a'] == [t[p['p']][p['kind']]]


@proto(id='eng-oge-28-pronoun', exam='ОГЭ', n=28, n_range='20–28', title='Местоимения', kes=['2.4.43', '2.4.44', '2.4.45'], level='Б', kind='param',
       gen_of='eng-ege-24-pronoun', invariant='личное местоимение заглавными, рамка задаёт разряд', varies='местоимение, разряд, рамка',
       answer_rule='таблица форм', mistakes=['we вместо us', 'theirselves'])
def g_pron_oge(rng, exam):
    return g_pron(rng, exam)


CHECKS = {'be': c_be, 'there-be': c_be, 'past-simple': c_past, 'past-neg': c_past_neg, 'present-simple': c_pres, 'present-cont': c_cont,
          'past-cont': c_pastcont, 'present-perfect': c_perf, 'past-perfect': c_pastperf, 'perfect-cont': c_perfcont, 'future': c_fut,
          'passive-past': c_pass, 'passive-present': c_pass, 'passive-perfect-modal': c_pass_perf, 'conditional-1': c_cond1,
          'conditional-2': c_cond2, 'reported': c_reported, 'gerund-infinitive': c_gov, 'modal': c_modal, 'plural': c_plural,
          'comparison': c_cmp, 'ordinal': c_ord, 'pronoun': c_pron}

# ---------------------------------------------------------------- словообразование: собственные гнёзда (dict)

from eng_wf import WF_ENTRIES, derive, WF_FAMILY_TITLES  # noqa: E402

WF_EGE = {'noun': 25, 'agent': 25, 'adj': 26, 'nationality': 26, 'participle': 27, 'negative': 27, 'adverb': 28, 'verb-prefix': 28,
          'verb-suffix': 29, 'numeral': 29, 'inter-pre-post': 27}
WF_OGE = {'noun': 29, 'agent': 29, 'adj': 30, 'participle': 31, 'negative': 31, 'adverb': 32, 'verb-prefix': 33, 'numeral': 34}


def wf_entries(fam, exam):
    allowed = G.AFF_OGE if exam == 'ОГЭ' else G.AFF_EGE
    return [e for e in WF_ENTRIES if e['fam'] == fam and all(a in allowed for a in e['aff']) and (exam == 'ЕГЭ' or e.get('lvl', 'B1') in ('A2', 'B1'))]


def make_wf(fam, exam, home):
    ex = 'ege' if exam == 'ЕГЭ' else 'oge'
    n_range = '25–29' if exam == 'ЕГЭ' else '29–34'
    title, invariant, mistakes = WF_FAMILY_TITLES[fam]

    @proto(id=f'eng-{ex}-{home}-wf-{fam}', exam=exam, n=home, n_range=n_range, title=title, kes=['2.3.11'] if exam == 'ЕГЭ' else ['2.3.7'],
           level='Б', kind='dict', invariant=invariant + '; основа заглавными в конце строки, аффиксы — только из кодификатора',
           varies='основа и её гнездо, предложение (собственные), при одной основе — разные производные',
           answer_rule='таблица гнёзд: основа + аффиксы с правилами орфографии (drop e, y → i, удвоение); -ise/-ize оба в ключе; проверка — независимый вывод формы по аффиксам',
           mistakes=mistakes, fam=fam)
    def g(rng, exam_):
        es = wf_entries(fam, exam)
        e = rng.choice(es)
        s = rng.choice(e['s'])
        alts = [e['a']] + ([e['a'].replace('ise', 'ize')] if '-ise' in e['aff'] and 'ise' in e['a'] else [])
        fam_alts = sorted({x['a'] for x in WF_ENTRIES if x['b'] == e['b'] and x['a'] != e['a']})
        hint = f'{e["b"]} → {e["a"]}: {", ".join(e["aff"])}.' + (' Не путать с: ' + ', '.join(fam_alts) + '.' if fam_alts else '')
        return card(meta_id(), s + f'  ({e["b"]})', alts, hint), {'e': e}

    return g


def c_wf(p, c):
    e = p['e']
    d = derive(e['b'], e['aff'], e.get('stem'))
    a = c['a'][0].lower()
    return a in (d, d + 's') and c['a'][0] == e['a']  # множественное число производного (visitors) — по рамке


for fam_, home_ in WF_EGE.items():
    make_wf(fam_, 'ЕГЭ', home_)
for fam_, home_ in WF_OGE.items():
    make_wf(fam_, 'ОГЭ', home_)

# ---------------------------------------------------------------- лексика ЕГЭ 30–36 (dict: таблицы путаниц)

from eng_lex import LEX_PROTOS  # noqa: E402


def make_lex(spec):
    @proto(id=spec['id'], exam='ЕГЭ', n=spec['n'], n_range='30–36', title=spec['title'], kes=spec['kes'], level='В', kind='dict',
           invariant=spec['invariant'] + '; четыре варианта ответа, ответ — цифра', varies=spec['varies'], answer_rule=spec['answer_rule'],
           mistakes=spec['mistakes'])
    def g(rng, exam):
        q, opts, right, hint, feat = spec['gen'](rng)
        idx = list(range(4))
        rng.shuffle(idx)
        o = [opts[i] for i in idx]
        a = str(o.index(right) + 1)
        text = q + '\n' + '\n'.join(f'{i + 1}) {w}' for i, w in enumerate(o))
        return card(meta_id(), text, [a], hint, k='one', o=o), {'feat': feat, 'right': right, 'o': o, 'check': spec['check']}

    return g


for spec_ in LEX_PROTOS:
    make_lex(spec_)


def c_lex(p, c):
    want = p['check'](p['feat'])  # вторая таблица / обратный словарь
    return want == p['right'] and c['a'] == [str(p['o'].index(want) + 1)] and len(set(p['o'])) == 4


# ---------------------------------------------------------------- рецепты llm (без генерации)

from eng_llm import LLM_PROTOS  # noqa: E402

for spec_ in LLM_PROTOS:
    m = dict(spec_)
    m['kind'] = 'llm'
    m['gen_fn'] = None
    PROTOS.append(m)


# ---------------------------------------------------------------- генерация, проверка, каталог

def check_of(m):
    if m['kind'] == 'llm':
        return None
    if m['id'].split('-', 3)[3].startswith('wf-'):
        return c_wf
    if m['n_range'] == '30–36':
        return c_lex
    key = m['id'].split('-', 3)[3]
    return CHECKS[key]


def generate(m, rng, want, max_tries=40):
    """До want разных карточек (по тексту), с проверкой; возвращает (cards, bad, tries)."""
    _CUR[0] = m['id']
    chk = check_of(m)
    seen, cards, bad, tries = set(), [], [], 0
    while len(cards) < want and tries < want * max_tries:
        tries += 1
        c, p = m['gen_fn'](rng, m['exam'])
        key = c['q'].split('\n')[0]  # для выбора из четырёх — само предложение, без порядка вариантов
        if key in seen:
            continue
        seen.add(key)
        if not (c['a'] and chk(p, c)):
            bad.append(c)
        cards.append(c)
    return cards, bad, tries


def capacity(m, limit=2000, seed=1):
    _CUR[0] = m['id']
    rng = random.Random(seed)
    seen = set()
    for _ in range(limit * 4):
        seen.add(m['gen_fn'](rng, m['exam'])[0]['q'].split('\n')[0])
        if len(seen) >= limit:
            break
    return len(seen)


def selftest(n=50, seed=2026):
    rng = random.Random(seed)
    rows, allcards = [], []
    for m in PROTOS:
        if m['kind'] == 'llm':
            continue
        cards, bad, tries = generate(m, rng, n)
        ids = Counter(c['id'] for c in cards)
        cp = capacity(m)
        m['capacity'] = cp
        rows.append({'id': m['id'], 'want': n, 'cards': len(cards), 'tries': tries, 'dup': sum(v - 1 for v in ids.values() if v > 1),
                     'bad': len(bad), 'capacity': cp, 'badcards': bad[:3]})
        allcards += cards
    dup_all = 0
    for ex in ('eng-ege-', 'eng-oge-'):
        dup_all += sum(v - 1 for v in Counter(c['q'] for c in allcards if c['p'].startswith(ex)).values() if v > 1)
    return rows, allcards, dup_all


def public(m):
    keys = ['id', 'exam', 'n', 'n_range', 'title', 'kes', 'level', 'invariant', 'varies', 'answer_rule', 'mistakes']
    d = {k: m.get(k) for k in keys}
    d['kim'] = kim_passport(m)
    d['gen'] = {'kind': m['kind']}
    if m['kind'] == 'llm':
        d['gen']['recipe'] = m['recipe']
    else:
        d['gen']['fn'] = f'tools/research/proto_eng.py:{m["gen_fn"].__name__}' + (f' (как {m["gen_of"]})' if m.get('gen_of') else '')
        d['gen']['check'] = check_of(m).__name__
    d['capacity'] = m.get('capacity')
    d['capacity_note'] = m.get('capacity_note') or ('замер до 2000 разных условий' if m['kind'] != 'llm' else 'по цене генерации и проверки')
    d['example'] = m.get('example')
    d['fidelity'] = m.get('fidelity', {'status': 'unchecked'})
    return d


def kim_passport(m):
    e = m['exam']
    if e == 'ЕГЭ':
        n = m['n']
        if n == 1: sec, score, time = 'аудирование', 2, 5
        elif n == 2: sec, score, time = 'аудирование', 3, 5
        elif n <= 9: sec, score, time = 'аудирование', 1, 3
        elif n == 10: sec, score, time = 'чтение', 3, 10
        elif n == 11: sec, score, time = 'чтение', 2, 10
        elif n <= 18: sec, score, time = 'чтение', 1, 4
        elif n <= 36: sec, score, time = 'грамматика и лексика', 1, 2
        elif n == 37: sec, score, time = 'письмо', 6, 30
        elif n == 38: sec, score, time = 'письмо', 14, 60
        else: sec, score, time = 'говорение', {39: 1, 40: 4, 41: 5, 42: 10}[n], {39: 1.5, 40: 2, 41: 2.5, 42: 3.5}[n]
        fmt = 'краткий ответ' if n <= 36 else 'развёрнутый ответ'
        if 19 <= n <= 29:
            fmt = 'слово или несколько слов, в бланк — без пробелов; орфографическая ошибка = 0'
        elif 30 <= n <= 36:
            fmt = 'цифра выбранного варианта'
        return {'section': sec, 'score': score, 'time_min': time, 'answer': fmt, 'source': 'спецификация и демоверсия ЕГЭ 2026 (ФИПИ, 05.11.2025; 2027 — без изменений)'}
    n = m['n']
    if m.get('oral'):
        return {'section': 'говорение', 'score': {1: 2, 2: 6, 3: 7}[n], 'time_min': {1: 2, 2: 3, 3: 4}[n], 'answer': 'развёрнутый ответ',
                'source': 'спецификация и демоверсия ОГЭ 2026 (ФИПИ, 06.11.2025; 2027 — без изменений)'}
    if n <= 4: sec, score, time = 'аудирование', 1, 3
    elif n == 5: sec, score, time = 'аудирование', 5, 5
    elif n <= 11: sec, score, time = 'аудирование', 1, 3
    elif n == 12: sec, score, time = 'чтение', 6, 10
    elif n <= 19: sec, score, time = 'чтение', 1, 4
    elif n <= 34: sec, score, time = 'грамматика и лексика', 1, 2
    else: sec, score, time = 'письмо', 10, 30
    fmt = 'краткий ответ' if n <= 34 else 'развёрнутый ответ'
    if 20 <= n <= 34:
        fmt = 'слово или несколько слов, в бланк — без пробелов; орфографическая ошибка = 0'
    elif 6 <= n <= 11:
        fmt = 'одно слово из текста, числа словами, без артиклей'
    return {'section': sec, 'score': score, 'time_min': time, 'answer': fmt, 'source': 'спецификация и демоверсия ОГЭ 2026 (ФИПИ, 06.11.2025; 2027 — без изменений)'}


def load_fidelity():
    if os.path.exists(FIDELITY):
        with open(FIDELITY, encoding='utf-8') as f:
            return json.load(f)
    return {}


def export(rows):
    fid = load_fidelity()
    rng = random.Random(7)
    for m in PROTOS:
        if m['kind'] != 'llm':
            cards, _, _ = generate(m, rng, 1)
            c = cards[0]
            m['example'] = {'k': 'word' if c['k'] == 'text' else c['k'], 'q': c['q'], 'a': c['a'], 'e': c['e']}
            if c['k'] == 'text':
                m['example']['blank'] = c['blank']
        m['fidelity'] = fid.get(m['id'], {'status': 'unchecked'})
    meta = {
        'about': 'Каталог прототипов заданий ЕГЭ (1–42, КИМ 2026 = 2027) и ОГЭ (1–35 и устная часть) по английскому языку: '
                 'что неизменно, что меняется, как считается ответ; генератор аналогов (param / dict) или рецепт llm. '
                 'Тексты ФИПИ, Решу ЕГЭ и коммерческих банков не включены; примеры и все предложения генератора составлены самостоятельно.',
        'built_by': 'python3 tools/research/proto_eng.py --export',
        'exam_docs': 'спецификации, кодификаторы и демоверсии ФИПИ: ЕГЭ 2026 (05.11.2025), ОГЭ 2026 (06.11.2025); 2027 — без изменений',
        'answer_types': {'word': 'слово/несколько слов как в бланке: без регистра и пробелов, апостроф сохраняется, варианты в списке a',
                         'one': 'выбор одного из четырёх, ответ — цифра', 'open': 'развёрнутый ответ, проверка по критериям (llm)'},
        'dicts': 'сторонние словари в репозиторий не включены; таблицы форм, гнёзд и путаниц — собственные факты языка. '
                 'Для расширения: CEFR-J (с атрибуцией), Open English WordNet (CC BY 4.0); Oxford 3000/5000 и English Vocabulary Profile — нельзя.',
        'selftest': {r['id']: {'cards': r['cards'], 'bad': r['bad'], 'dup': r['dup'], 'capacity': r['capacity']} for r in rows},
        'counts': Counter(f'{m["exam"]}:{m["kind"]}' for m in PROTOS),
    }
    with open(CATALOG, 'w', encoding='utf-8') as f:
        json.dump({'meta': meta, 'prototypes': [public(m) for m in PROTOS]}, f, ensure_ascii=False, indent=1)
    print('записано', CATALOG, len(PROTOS), 'прототипов')


def sample(k, seed, out):
    rng = random.Random(seed)
    res = []
    for m in PROTOS:
        if m['kind'] == 'llm':
            continue
        cards, _, _ = generate(m, rng, 60)
        for c in rng.sample(cards, min(k, len(cards))):
            res.append({'p': m['id'], 'n': f'{m["exam"]} {m["n"]}', 'q': c['q'], 'a': c['a']})
    with open(out, 'w', encoding='utf-8') as f:
        for r in res:
            f.write(f'{r["p"]} [{r["n"]}]\n  {r["q"]}\n  → {" | ".join(r["a"])}\n')
    print('выборка', len(res), 'карточек →', out)


def tables(rows):
    fid = load_fidelity()
    print('<!-- COVERAGE -->')
    print('| Экзамен | № | Прототипов | Способ | Что проверяет (прототипы) | Ёмкость |')
    print('|---|---|---|---|---|---|')
    by = {}
    for m in PROTOS:
        by.setdefault((m['exam'], 'устн. ' + str(m['n']) if m.get('oral') else m['n']), []).append(m)
    order = sorted(by, key=lambda k: (k[0] != 'ЕГЭ', isinstance(k[1], str), k[1] if isinstance(k[1], int) else int(k[1].split()[-1])))
    for key in order:
        ms = by[key]
        kinds = sorted({m['kind'] for m in ms})
        caps = [m.get('capacity') for m in ms if m.get('capacity')]
        cap_s = ('–'.join(str(x) for x in sorted({min(caps), max(caps)})) if caps else 'рецепт')
        rng_s = ms[0].get('n_range', '')
        titles = '; '.join(m['title'].split(': ', 1)[-1] if m['title'].startswith(('Словообразование', 'Лексическая', 'Аудирование', 'Чтение', 'Письмо', 'Говорение'))
                           else m['title'].split(':')[0] for m in ms)
        print(f'| {key[0]} | {key[1]}{(" (из " + rng_s + ")") if rng_s and str(key[1]) not in ("", rng_s) and ms[0]["kind"] != "llm" else ""} | {len(ms)} | {", ".join(kinds)} | {titles} | {cap_s} |')
    print()
    print('<!-- SELFTEST -->')
    print('| Прототип | Карточек | Попыток | Ошибок | Дублей | Ёмкость |')
    print('|---|---|---|---|---|---|')
    for r in rows:
        print(f'| {r["id"]} | {r["cards"]} | {r["tries"]} | {r["bad"]} | {r["dup"]} | {r["capacity"]}{"+" if r["capacity"] >= 2000 else ""} |')
    print()
    print('<!-- FIDELITY -->')
    print('| Прототип | Экз. № | Проверено | Прошло | Итог | Замечание |')
    print('|---|---|---|---|---|---|')
    st = Counter()
    for m in PROTOS:
        f = fid.get(m['id'])
        if not f:
            continue
        st[f['status']] += 1
        print(f'| {m["id"]} | {m["exam"]} {m["n"]} | {f.get("checked", "")} | {f.get("passed", "")} | {"**fail**" if f["status"] == "fail" else f["status"]} | {f.get("note", "")} |')
    print()
    print('Итого:', dict(st))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=50)
    ap.add_argument('--seed', type=int, default=2026)
    ap.add_argument('--show')
    ap.add_argument('--sample', type=int)
    ap.add_argument('--out')
    ap.add_argument('--export', action='store_true')
    ap.add_argument('--tables', action='store_true')
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args(argv)
    if args.list:
        for m in PROTOS:
            print(f'{m["id"]:40} {m["exam"]} {m["n"]:>2} {m["kind"]:5} {m["title"]}')
        return
    if args.show:
        m = next(m for m in PROTOS if m['id'] == args.show)
        cards, bad, _ = generate(m, random.Random(args.seed), args.n)
        for c in cards:
            print(json.dumps(c, ensure_ascii=False))
        print('ошибок:', len(bad))
        return
    if args.sample:
        sample(args.sample, args.seed, args.out or 'eng_sample.txt')
        return
    rows, cards, dup_all = selftest(args.n, args.seed)
    print(f'{"прототип":42} {"карт.":>5} {"попыт.":>6} {"ошибок":>6} {"дублей":>6} {"ёмкость":>7}')
    for r in rows:
        print(f'{r["id"]:42} {r["cards"]:5} {r["tries"]:6} {r["bad"]:6} {r["dup"]:6} {r["capacity"]:7}')
        for b in r['badcards']:
            print('   ОШИБКА:', b['q'], b['a'])
    short = [r['id'] for r in rows if r['cards'] < r['want']]
    problems = sum(r['bad'] + r['dup'] for r in rows) + dup_all
    llm = sum(1 for m in PROTOS if m['kind'] == 'llm')
    print(f'Итого: {len(rows)} генерируемых прототипов + {llm} рецептов llm = {len(PROTOS)}; карточек {len(cards)}, '
          f'ошибок {sum(r["bad"] for r in rows)}, дублей {sum(r["dup"] for r in rows)} (между прототипами одного экзамена {dup_all}); '
          f'меньше {args.n}: {len(short)} {short if short else ""}')
    if args.export:
        export(rows)
    if args.tables:
        tables(rows)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
