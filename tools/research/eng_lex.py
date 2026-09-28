"""Лексика ЕГЭ 30–36 (dict): собственные таблицы «путаниц» и предложения. Выбор одного из четырёх, ответ — цифра.

У каждого прототипа две таблицы: по первой генератор выбирает верное слово, по второй (обратный словарь или правило
по признаку) проверка восстанавливает ответ независимо. Все предложения составлены для генератора.
"""

# ---------------------------------------------------------------- 30: make / do
FORMS = {'make': ('made', 'makes', 'make', 'making'), 'do': ('did', 'does', 'do', 'doing'), 'take': ('took', 'takes', 'take', 'taking'),
         'get': ('got', 'gets', 'get', 'getting'), 'have': ('had', 'has', 'have', 'having'), 'give': ('gave', 'gives', 'give', 'giving')}
T = {'past': 0, 'pres3': 1, 'base': 2, 'ing': 3}
MAKE_DO = [  # (глагол, объект, предложение, время)
    ('make', 'a mistake', 'Sorry, I ____ a mistake in the last sentence of the letter.', 'past'),
    ('make', 'a decision', 'We have to ____ a decision about the trip before Friday.', 'base'),
    ('make', 'friends', 'At the camp my sister quickly ____ friends with two girls from Tula.', 'past'),
    ('make', 'noise', 'Please stop ____ so much noise — the baby is asleep.', 'ing'),
    ('make', 'progress', 'Nick ____ good progress in maths this term.', 'past'),
    ('make', 'a promise', 'Dad ____ a promise to take us to the zoo on Sunday.', 'past'),
    ('make', 'an effort', 'You should ____ an effort to get up earlier.', 'base'),
    ('make', 'a phone call', 'Excuse me, I need to ____ a quick phone call.', 'base'),
    ('make', 'the bed', 'My brother never ____ his bed in the morning.', 'pres3'),
    ('make', 'a list', 'Let\'s ____ a list of everything we need for the picnic.', 'base'),
    ('make', 'a speech', 'The headmaster ____ a short speech at the end of the concert.', 'past'),
    ('make', 'a choice', 'It was hard to ____ a choice between the two bikes.', 'base'),
    ('make', 'an excuse', 'Tom always ____ an excuse when he is late.', 'pres3'),
    ('make', 'a plan', 'We are ____ a plan for the school trip.', 'ing'),
    ('make', 'money', 'My uncle ____ a lot of money selling honey.', 'pres3'),
    ('make', 'a wish', 'Close your eyes and ____ a wish!', 'base'),
    ('do', 'homework', 'I usually ____ my homework right after school.', 'base'),
    ('do', 'the shopping', 'On Saturdays Mum ____ the shopping at the big market.', 'pres3'),
    ('do', 'the washing-up', 'Whose turn is it to ____ the washing-up tonight?', 'base'),
    ('do', 'exercise', 'Grandpa ____ exercise every morning in the park.', 'pres3'),
    ('do', 'one\'s best', 'I ____ my best, but the test was really difficult.', 'past'),
    ('do', 'a favour', 'Could you ____ me a favour and post this letter?', 'base'),
    ('do', 'the housework', 'On Sundays the whole family ____ the housework together.', 'pres3'),
    ('do', 'research', 'The scientists are ____ research on penguins in Antarctica.', 'ing'),
    ('do', 'a course', 'Last summer my sister ____ a course in web design.', 'past'),
    ('do', 'sport', 'Which sport ____ you ____ at school? — I play basketball.', 'base'),
    ('do', 'harm', 'A little rain won\'t ____ any harm to the tomatoes.', 'base'),
    ('do', 'a puzzle', 'The children spent the evening ____ a big puzzle.', 'ing'),
    ('do', 'the ironing', 'I hate ____ the ironing, so I do it once a week.', 'ing'),
    ('do', 'well', 'Anna ____ very well in the history exam.', 'past'),
    ('do', 'the cooking', 'In our family Dad ____ the cooking on weekends.', 'pres3'),
    ('do', 'business', 'The company ____ business with partners in China.', 'pres3'),
]
MAKE_DO_REV = {}  # обратный словарь: объект → глагол (вторая таблица, строки)
for _line in ('make: a mistake|a decision|friends|noise|progress|a promise|an effort|a phone call|the bed|a list|a speech|a choice|an excuse|a plan|money|a wish',
              'do: homework|the shopping|the washing-up|exercise|one\'s best|a favour|the housework|research|a course|sport|harm|a puzzle|the ironing|well|the cooking|business'):
    _v, _objs = _line.split(': ')
    for _o in _objs.split('|'):
        MAKE_DO_REV[_o] = _v


def gen_make_do(rng):
    v, obj, sent, tense = rng.choice(MAKE_DO)
    other = 'do' if v == 'make' else 'make'
    fill = rng.sample(['take', 'get', 'have', 'give'], 2)
    opts = [FORMS[x][T[tense]] for x in (v, other) + tuple(fill)]
    right = FORMS[v][T[tense]]
    return sent, opts, right, f'{v} + {obj}: устойчивое сочетание; make — «создать, произвести», do — «выполнить, заниматься»', (obj, tense)


def chk_make_do(feat):
    obj, tense = feat
    return FORMS[MAKE_DO_REV[obj]][T[tense]]


# ---------------------------------------------------------------- 31: say / tell / speak / talk
STT_FORMS = {'say': ('said', 'says', 'say', 'saying'), 'tell': ('told', 'tells', 'tell', 'telling'), 'speak': ('spoke', 'speaks', 'speak', 'speaking'),
             'talk': ('talked', 'talks', 'talk', 'talking')}
STT = [  # (глагол, признак, предложение, время)
    ('tell', 'person', 'Please ____ me the truth: who broke the vase?', 'base'),
    ('tell', 'person', 'Grandma ____ us a story about her school every evening.', 'pres3'),
    ('tell', 'person', 'The guide ____ the tourists about the history of the castle.', 'past'),
    ('tell', 'person', 'Did you ____ your parents about the trip?', 'base'),
    ('tell', 'fixed', 'Can you ____ the difference between a frog and a toad?', 'base'),
    ('tell', 'fixed', 'Everybody knows that Nick can\'t ____ a lie.', 'base'),
    ('tell', 'fixed', 'My little brother has learnt to ____ the time.', 'base'),
    ('say', 'clause', 'The teacher ____ that the test would be on Monday.', 'past'),
    ('say', 'clause', 'Kate ____ she was too tired to go out.', 'past'),
    ('say', 'fixed', 'Don\'t forget to ____ goodbye to your grandparents.', 'base'),
    ('say', 'fixed', 'He ____ sorry and left the room.', 'past'),
    ('say', 'fixed', 'Nobody ____ a word during the film.', 'past'),
    ('say', 'clause', 'What did the doctor ____ about your leg?', 'base'),
    ('say', 'fixed', 'Just ____ hello to Ann for me.', 'base'),
    ('speak', 'language', 'My cousin ____ three languages: Russian, English and Tatar.', 'pres3'),
    ('speak', 'language', 'Do you ____ Spanish? — Only a little.', 'base'),
    ('speak', 'language', 'Grandpa ____ German because he lived in Berlin for ten years.', 'pres3'),
    ('speak', 'louder', 'Could you ____ louder, please? I can\'t hear you.', 'base'),
    ('speak', 'louder', 'The girl ____ so quietly that nobody heard her answer.', 'past'),
    ('speak', 'language', 'In Brazil people ____ Portuguese, not Spanish.', 'base'),
    ('talk', 'about', 'We ____ about the film for an hour after the cinema.', 'past'),
    ('talk', 'about', 'Let\'s not ____ about school on holiday!', 'base'),
    ('talk', 'about', 'The boys were ____ about football all the way home.', 'ing'),
    ('talk', 'about', 'My sister ____ about her new phone all day long.', 'pres3'),
    ('talk', 'nonsense', 'Stop ____ nonsense and listen to me.', 'ing'),
    ('talk', 'about', 'What were you two ____ about?', 'ing'),
]
STT_RULE = {'person': 'tell', 'fixed': None, 'clause': 'say', 'language': 'speak', 'louder': 'speak', 'about': 'talk', 'nonsense': 'talk'}
STT_FIXED = {'the difference': 'tell', 'a lie': 'tell', 'the time': 'tell', 'goodbye': 'say', 'sorry': 'say', 'a word': 'say', 'hello': 'say'}


def gen_stt(rng):
    v, feat, sent, tense = rng.choice(STT)
    opts = [STT_FORMS[x][T[tense]] for x in ('say', 'tell', 'speak', 'talk')]
    right = STT_FORMS[v][T[tense]]
    return sent, opts, right, 'tell + кому (tell me, tell the truth); say + что (say that…, say sorry); speak + язык / громче; talk + about', (feat, sent, tense)


def chk_stt(feat):
    f, sent, tense = feat
    v = STT_RULE[f]
    if v is None:
        v = next(w for k, w in STT_FIXED.items() if k in sent)
    return STT_FORMS[v][T[tense]]


# ---------------------------------------------------------------- 32: предлоги после глаголов и прилагательных
PREP = [  # (слово, предлог, дистракторы, предложение)
    ('interested', 'in', ['on', 'at', 'for'], 'My brother is very interested ____ old cars.'),
    ('good', 'at', ['in', 'on', 'for'], 'Ann is really good ____ drawing animals.'),
    ('afraid', 'of', ['from', 'at', 'with'], 'My little sister is afraid ____ big dogs.'),
    ('depend', 'on', ['of', 'from', 'at'], 'Our plans for Sunday depend ____ the weather.'),
    ('listen', 'to', ['at', 'for', 'on'], 'I always listen ____ music while I do my homework.'),
    ('wait', 'for', ['to', 'at', 'on'], 'We waited ____ the bus for half an hour.'),
    ('famous', 'for', ['by', 'with', 'of'], 'The town is famous ____ its chocolate factory.'),
    ('keen', 'on', ['in', 'at', 'for'], 'Tom is keen ____ chess and plays every day.'),
    ('proud', 'of', ['for', 'with', 'on'], 'Her parents are proud ____ her results.'),
    ('responsible', 'for', ['of', 'on', 'to'], 'Who is responsible ____ watering the plants?'),
    ('similar', 'to', ['with', 'as', 'at'], 'Your bag is similar ____ mine.'),
    ('different', 'from', ['of', 'with', 'than'], 'Life in the village is very different ____ life in the city.'),
    ('arrive', 'at', ['to', 'on', 'in'], 'We arrived ____ the station ten minutes before the train.'),
    ('apologise', 'for', ['of', 'about', 'on'], 'Nick apologised ____ being late.'),
    ('belong', 'to', ['for', 'at', 'of'], 'This umbrella belongs ____ my teacher.'),
    ('consist', 'of', ['from', 'in', 'on'], 'The team consists ____ eleven players.'),
    ('look forward', 'to', ['for', 'at', 'on'], 'I am looking forward ____ the summer holidays.'),
    ('laugh', 'at', ['on', 'over', 'to'], 'Don\'t laugh ____ my mistakes, please.'),
    ('worried', 'about', ['for', 'of', 'on'], 'Mum is worried ____ my marks.'),
    ('full', 'of', ['with', 'by', 'in'], 'The basket was full ____ apples.'),
    ('tired', 'of', ['from', 'with', 'by'], 'I am tired ____ this cold weather.'),
    ('pay', 'for', ['to', 'on', 'at'], 'Who paid ____ the tickets?'),
    ('agree', 'with', ['to', 'on', 'at'], 'I don\'t agree ____ you about the film.'),
    ('married', 'to', ['with', 'on', 'at'], 'My aunt is married ____ a pilot.'),
    ('angry', 'with', ['on', 'to', 'for'], 'Why are you angry ____ me? I didn\'t do anything.'),
    ('fond', 'of', ['in', 'at', 'to'], 'Grandma is fond ____ crossword puzzles.'),
    ('search', 'for', ['at', 'on', 'to'], 'The police searched ____ the missing boy all night.'),
    ('succeed', 'in', ['at', 'on', 'to'], 'Ann succeeded ____ passing her driving test.'),
    ('concentrate', 'on', ['at', 'in', 'to'], 'I can\'t concentrate ____ my homework when the TV is on.'),
    ('translate', 'into', ['on', 'to', 'in'], 'Can you translate this text ____ Russian?'),
]
PREP_TABLE2 = dict(l.split(' ') for l in
                   'interested in|good at|afraid of|depend on|listen to|wait for|famous for|keen on|proud of|responsible for|similar to|different from|'
                   'arrive at|apologise for|belong to|consist of|look_forward to|laugh at|worried about|full of|tired of|pay for|agree with|married to|'
                   'angry with|fond of|search for|succeed in|concentrate on|translate into'.split('|'))


def gen_prep(rng):
    head, prep, dis, sent = rng.choice(PREP)
    return sent, [prep] + dis, prep, f'{head} {prep} — управление запоминается вместе со словом', head


def chk_prep(feat):
    return PREP_TABLE2[feat.replace(' ', '_')]


# ---------------------------------------------------------------- 33: прилагательные на -ed / -ing
EDING = [  # (основа, -ed, -ing, существительное-раздражитель, существительное-состояние)
    ('bore', 'bored', 'boring', 'boredom', 'the lecture'), ('interest', 'interested', 'interesting', 'interest', 'the documentary'),
    ('excite', 'excited', 'exciting', 'excitement', 'the match'), ('surprise', 'surprised', 'surprising', 'surprise', 'the news'),
    ('tire', 'tired', 'tiring', 'tiredness', 'the journey'), ('disappoint', 'disappointed', 'disappointing', 'disappointment', 'the result'),
    ('amaze', 'amazed', 'amazing', 'amazement', 'the show'), ('frighten', 'frightened', 'frightening', 'fright', 'the film'),
    ('relax', 'relaxed', 'relaxing', 'relaxation', 'the holiday'), ('confuse', 'confused', 'confusing', 'confusion', 'the map'),
    ('embarrass', 'embarrassed', 'embarrassing', 'embarrassment', 'the question'), ('annoy', 'annoyed', 'annoying', 'annoyance', 'the noise'),
    ('shock', 'shocked', 'shocking', 'shock', 'the story'), ('exhaust', 'exhausted', 'exhausting', 'exhaustion', 'the climb'),
    ('fascinate', 'fascinated', 'fascinating', 'fascination', 'the museum'),
]
EXP_FRAMES = ['I was really ____ by {thing}.', 'The children got ____ during {thing}.', 'Everybody in the room looked ____.',
              'My parents were ____ when they heard about it.', 'After {thing} we all felt ____.']
STIM_FRAMES = ['{Thing} was really ____.', 'It was the most ____ part of the day.', '{Thing} turned out to be ____ for everybody.',
               'What a ____ story!', 'I have never seen anything so ____.']


def gen_eding(rng):
    base, ed, ing, noun, thing = rng.choice(EDING)
    kind = rng.choice(['exp', 'stim'])
    fr = rng.choice(EXP_FRAMES if kind == 'exp' else STIM_FRAMES)
    sent = fr.replace('{thing}', thing).replace('{Thing}', thing[0].upper() + thing[1:])
    fourth = noun if noun not in (base, ed, ing) else ing + 'ly'
    opts = [ed, ing, base, fourth]
    right = ed if kind == 'exp' else ing
    return sent, opts, right, '-ed — чувство человека (I am bored), -ing — свойство предмета или события (the film is boring)', (kind, base)


def chk_eding(feat):
    kind, base = feat
    row = next(r for r in EDING if r[0] == base)
    return {'exp': row[1], 'stim': row[2]}[kind]


# ---------------------------------------------------------------- 34: фразовые глаголы
PHRASAL = [  # (глагол, частица, значение-метка, предложение)
    ('look', 'after', 'care', 'Who will look ____ the cat while you are away?'),
    ('look', 'for', 'search', 'I have been looking ____ my glasses for an hour.'),
    ('look', 'up', 'dictionary', 'If you don\'t know the word, look it ____ in the dictionary.'),
    ('look', 'into', 'investigate', 'The police promised to look ____ the case.'),
    ('get', 'up', 'rise', 'On Sundays I get ____ at ten.'),
    ('get', 'over', 'recover', 'It took Grandpa a month to get ____ the flu.'),
    ('get', 'on', 'relations', 'Do you get ____ well with your new classmates?'),
    ('get', 'off', 'leave-bus', 'We should get ____ the bus at the next stop.'),
    ('give', 'up', 'quit', 'My father gave ____ smoking two years ago.'),
    ('give', 'back', 'return', 'Can you give ____ the book I lent you?'),
    ('give', 'away', 'donate', 'We gave ____ our old toys to the children\'s home.'),
    ('give', 'in', 'surrender', 'The boy did not give ____ and finished the race.'),
    ('put', 'on', 'wear', 'Put ____ your coat, it is cold outside.'),
    ('put', 'off', 'postpone', 'The meeting was put ____ until next week.'),
    ('put', 'out', 'extinguish', 'The firemen put ____ the fire in twenty minutes.'),
    ('put', 'away', 'tidy', 'Put ____ your toys before dinner.'),
    ('take', 'off', 'depart', 'The plane took ____ an hour late.'),
    ('take', 'after', 'resemble', 'Anna takes ____ her mother: they have the same smile.'),
    ('take', 'up', 'start-hobby', 'Last year my brother took ____ tennis.'),
    ('take', 'back', 'return-shop', 'The shoes are too small, so I will take them ____ to the shop.'),
    ('turn', 'on', 'switch-on', 'Turn ____ the light, please, it is dark here.'),
    ('turn', 'off', 'switch-off', 'Don\'t forget to turn ____ the TV before you leave.'),
    ('turn', 'down', 'refuse', 'She turned ____ the job because the office was too far away.'),
    ('turn', 'up', 'appear', 'Nick turned ____ at the party an hour late.'),
    ('bring', 'up', 'raise-child', 'My grandparents brought ____ five children in a tiny house.'),
    ('bring', 'back', 'memories', 'This song brings ____ memories of our first summer camp.'),
    ('bring', 'about', 'cause', 'The new law brought ____ big changes in the school system.'),
    ('bring', 'along', 'with-you', 'You can bring ____ a friend to the party.'),
    ('run', 'out of', 'exhaust', 'We have run ____ milk, could you buy some?'),
    ('run', 'into', 'meet-by-chance', 'Yesterday I ran ____ my old teacher at the market.'),
    ('run', 'away', 'escape', 'The dog ran ____ from home and came back only in the evening.'),
    ('run', 'after', 'chase', 'The boys ran ____ the ball across the field.'),
    ('go', 'on', 'continue', 'Please go ____, the story is very interesting.'),
    ('go', 'off', 'explode-alarm', 'My alarm clock went ____ at six, but I didn\'t hear it.'),
    ('go', 'out', 'leave-home', 'Do you often go ____ with your friends at the weekend?'),
    ('go', 'through', 'experience', 'The family went ____ a difficult time after the fire.'),
    ('come', 'across', 'find-by-chance', 'I came ____ this old photo in Grandma\'s album.'),
    ('come', 'back', 'return-home', 'When will your parents come ____ from Sochi?'),
    ('come', 'up with', 'invent-idea', 'Tom came ____ a brilliant idea for the school project.'),
    ('come', 'round', 'visit', 'Why don\'t you come ____ for tea on Saturday?'),
]
PHRASAL_TABLE2 = {}  # вторая таблица: (глагол, значение) → частица
for _l in ('look: care after, search for, dictionary up, investigate into', 'get: rise up, recover over, relations on, leave-bus off',
           'give: quit up, return back, donate away, surrender in', 'put: wear on, postpone off, extinguish out, tidy away',
           'take: depart off, resemble after, start-hobby up, return-shop back', 'turn: switch-on on, switch-off off, refuse down, appear up',
           'bring: raise-child up, memories back, cause about, with-you along', 'run: exhaust out of, meet-by-chance into, escape away, chase after',
           'go: continue on, explode-alarm off, leave-home out, experience through', 'come: find-by-chance across, return-home back, invent-idea up with, visit round'):
    _v, _rest = _l.split(': ')
    for _item in _rest.split(', '):
        _m, _p = _item.split(' ', 1)
        PHRASAL_TABLE2[(_v, _m)] = _p


def gen_phrasal(rng):
    v, part, meaning, sent = rng.choice(PHRASAL)
    others = [pp for (vv, pp, m, s) in PHRASAL if vv == v and pp != part]
    opts = [part] + rng.sample(others, 3)
    return sent, opts, part, f'{v} {part} — фразовый глагол; значение частицы учится вместе с глаголом', (v, meaning)


def chk_phrasal(feat):
    return PHRASAL_TABLE2[feat]


# ---------------------------------------------------------------- 35: союзы и связки
LINK_SETS = {'A': ['although', 'despite', 'however', 'because'], 'B': ['because of', 'despite', 'although', 'unless'],
             'C': ['so', 'because', 'unless', 'while'], 'D': ['in order to', 'so that', 'because', 'although'],
             'E': ['unless', 'if', 'although', 'because'], 'F': ['however', 'moreover', 'therefore', 'although']}
LINKERS = [  # (признак, предложение, набор вариантов)
    ('clause-contrast', '____ it was raining hard, we went for a walk in the park.', 'A'),
    ('clause-contrast', '____ my brother is only ten, he plays chess better than me.', 'A'),
    ('clause-contrast', 'We enjoyed the trip ____ the hotel was quite far from the sea.', 'A'),
    ('clause-contrast', '____ the tickets were expensive, the stadium was full.', 'A'),
    ('np-contrast', '____ the rain, the football match was not cancelled.', 'A'),
    ('np-contrast', '____ his age, Grandpa still swims in the river every morning.', 'A'),
    ('np-contrast', 'The concert took place ____ the terrible weather.', 'A'),
    ('np-contrast', '____ all the problems, the school play was a success.', 'B'),
    ('sentence-contrast', 'The film was long. ____, nobody was bored.', 'A'),
    ('sentence-contrast', 'It was very cold. ____, the children spent the whole day outside.', 'F'),
    ('sentence-contrast', 'Tom studied hard. ____, he failed the exam.', 'F'),
    ('reason-clause', 'I took an umbrella ____ the sky was dark.', 'C'),
    ('reason-clause', 'We missed the bus ____ my brother could not find his keys.', 'C'),
    ('reason-clause', 'Ann stayed at home ____ she had a bad cold.', 'E'),
    ('reason-np', 'The match was cancelled ____ the heavy rain.', 'B'),
    ('reason-np', 'The train was late ____ the snow.', 'B'),
    ('reason-np', 'Many people moved to the city ____ the new factory.', 'B'),
    ('result', 'It was very hot, ____ we spent the day at the lake.', 'C'),
    ('result', 'The shop was closed, ____ we went to the market instead.', 'C'),
    ('result', 'My phone was dead, ____ I could not call you.', 'C'),
    ('purpose-inf', 'I got up early ____ catch the first train.', 'D'),
    ('purpose-inf', 'Nick is saving money ____ buy a new guitar.', 'D'),
    ('purpose-clause', 'Speak louder ____ everybody can hear you.', 'D'),
    ('purpose-clause', 'Mum wrote the recipe down ____ I could cook the soup myself.', 'D'),
    ('condition-neg', 'You will miss the train ____ you hurry.', 'E'),
    ('condition-neg', 'We can\'t start the game ____ everybody is here.', 'E'),
    ('condition-neg', 'I won\'t go to the party ____ you come with me.', 'E'),
    ('condition-pos', '____ it rains tomorrow, we will stay at home.', 'E'),
    ('condition-pos', 'We will go skiing ____ there is enough snow.', 'E'),
    ('sentence-therefore', 'The road was icy. ____, the buses were late.', 'F'),
    ('sentence-moreover', 'The hotel was cheap. ____, it was next to the beach.', 'F'),
]
LINK_RULE = {'clause-contrast': 'although', 'np-contrast': 'despite', 'sentence-contrast': 'however', 'reason-clause': 'because',
             'reason-np': 'because of', 'result': 'so', 'purpose-inf': 'in order to', 'purpose-clause': 'so that', 'condition-neg': 'unless',
             'condition-pos': 'if', 'sentence-therefore': 'therefore', 'sentence-moreover': 'moreover'}


def gen_linker(rng):
    feat, sent, setname = rng.choice(LINKERS)
    opts = list(LINK_SETS[setname])
    right = LINK_RULE[feat]
    if sent.startswith('____'):
        opts = [o[0].upper() + o[1:] for o in opts]
        right = right[0].upper() + right[1:]
    return sent, opts, right, 'although + придаточное, despite + существительное, however — начало нового предложения; because + причина, so + следствие, unless = if not', (feat, sent.startswith('____'))


def chk_linker(feat):
    f, capital = feat
    w = LINK_RULE[f]
    return w[0].upper() + w[1:] if capital else w


# ---------------------------------------------------------------- 36: пары-путаницы
CONF = [  # (пара, признак, предложение, ответ, три дистрактора)
    ('rise/raise', 'obj', 'The teacher asked us to ____ our hands if we agreed.', 'raise', ['rise', 'arise', 'lift up']),
    ('rise/raise', 'obj', 'The shop ____ its prices before the holidays.', 'raised', ['rose', 'arose', 'grew']),
    ('rise/raise', 'no-obj', 'The sun ____ at five in the morning in June.', 'rises', ['raises', 'arises', 'grows']),
    ('rise/raise', 'no-obj', 'Food prices ____ sharply last month.', 'rose', ['raised', 'arose', 'lifted']),
    ('lie/lay', 'obj', 'Please ____ the plates on the table.', 'lay', ['lie', 'lying', 'lain']),
    ('lie/lay', 'no-obj', 'The cat likes to ____ in the sun all afternoon.', 'lie', ['lay', 'laid', 'lain']),
    ('lie/lay', 'no-obj', 'Grandpa ____ on the sofa and fell asleep.', 'lay', ['laid', 'lied', 'lain']),
    ('borrow/lend', 'from', 'Can I ____ your pen for a minute?', 'borrow', ['lend', 'loan', 'rent']),
    ('borrow/lend', 'to', 'I ____ my bike to Nick, and he broke it.', 'lent', ['borrowed', 'rented', 'hired']),
    ('borrow/lend', 'from', 'Ann ____ two books from the school library.', 'borrowed', ['lent', 'rented', 'hired']),
    ('borrow/lend', 'to', 'Could you ____ me some money until Friday?', 'lend', ['borrow', 'rent', 'hire']),
    ('affect/effect', 'verb', 'The cold weather ____ the harvest badly.', 'affected', ['effected', 'infected', 'defected']),
    ('affect/effect', 'noun', 'The new rules had a positive ____ on the pupils\' marks.', 'effect', ['affect', 'affection', 'defect']),
    ('affect/effect', 'verb', 'Lack of sleep ____ your memory.', 'affects', ['effects', 'infects', 'defects']),
    ('bring/take', 'here', 'Please ____ me a glass of water, I can\'t get up.', 'bring', ['take', 'carry away', 'fetch off']),
    ('bring/take', 'away', 'Don\'t forget to ____ your umbrella when you leave.', 'take', ['bring', 'fetch', 'carry over']),
    ('bring/take', 'here', 'Can you ____ your photos to school tomorrow and show them to us?', 'bring', ['take', 'carry off', 'send off']),
    ('win/beat', 'opponent', 'Our team ____ the champions 3:1 yesterday.', 'beat', ['won', 'gained', 'earned']),
    ('win/beat', 'prize', 'Kate ____ the first prize in the drawing competition.', 'won', ['beat', 'earned', 'gained']),
    ('win/beat', 'opponent', 'Nobody can ____ my grandfather at chess.', 'beat', ['win', 'gain', 'earn']),
    ('win/beat', 'prize', 'Which team ____ the match on Saturday?', 'won', ['beat', 'gained', 'earned']),
    ('lose/miss', 'transport', 'Hurry up, or we will ____ the last bus!', 'miss', ['lose', 'skip', 'drop']),
    ('lose/miss', 'thing', 'I always ____ my keys, so I keep them on a long chain.', 'lose', ['miss', 'skip', 'drop']),
    ('lose/miss', 'transport', 'Tom ____ the first lesson because he overslept.', 'missed', ['lost', 'skipped', 'dropped']),
    ('lose/miss', 'thing', 'Our team ____ the game by one point.', 'lost', ['missed', 'dropped', 'failed']),
    ('remember/remind', 'remind', 'This song ____ me of our summer at the sea.', 'reminds', ['remembers', 'recalls', 'recognises']),
    ('remember/remind', 'remember', 'I can\'t ____ the name of that street.', 'remember', ['remind', 'recognise', 'remain']),
    ('remember/remind', 'remind', 'Please ____ me to call Grandma tonight.', 'remind', ['remember', 'recall', 'recognise']),
    ('hear/listen', 'listen', 'I love ____ to the rain at night.', 'listening', ['hearing', 'sounding', 'noticing']),
    ('hear/listen', 'hear', 'Did you ____ that strange noise a minute ago?', 'hear', ['listen', 'sound', 'notice']),
    ('see/watch/look', 'look', '____ at the board, please, and copy the sentence.', 'Look', ['See', 'Watch', 'Notice']),
    ('see/watch/look', 'watch', 'We ____ a film about dolphins last night.', 'watched', ['looked', 'noticed', 'glanced']),
    ('see/watch/look', 'see', 'It was so dark that I could not ____ anything.', 'see', ['look', 'watch', 'glance']),
    ('job/work', 'job', 'My sister has found a new ____ in a travel agency.', 'job', ['work', 'labour', 'employ']),
    ('job/work', 'work', 'I have a lot of ____ to do before the holidays.', 'work', ['job', 'jobs', 'labours']),
    ('trip/journey/travel', 'trip', 'Our class is going on a ____ to the planetarium on Friday.', 'trip', ['travel', 'travelling', 'voyage']),
    ('trip/journey/travel', 'travel', 'Grandpa says that ____ broadens the mind.', 'travel', ['trip', 'journey', 'voyage']),
    ('trip/journey/travel', 'journey', 'The ____ from Moscow to Vladivostok by train takes six days.', 'journey', ['travel', 'trip', 'voyage']),
    ('teach/learn', 'learn', 'I want to ____ how to play the guitar.', 'learn', ['teach', 'study', 'train']),
    ('teach/learn', 'teach', 'My grandmother ____ me how to bake bread.', 'taught', ['learnt', 'studied', 'trained']),
    ('fun/funny', 'fun', 'The party was great ____.', 'fun', ['funny', 'joke', 'laugh']),
    ('fun/funny', 'funny', 'The clown was so ____ that we could not stop laughing.', 'funny', ['fun', 'joke', 'laugh']),
]
CONF_RULE = {  # вторая таблица: (пара, признак) → лемма
    ('rise/raise', 'obj'): 'raise', ('rise/raise', 'no-obj'): 'rise', ('lie/lay', 'obj'): 'lay', ('lie/lay', 'no-obj'): 'lie',
    ('borrow/lend', 'from'): 'borrow', ('borrow/lend', 'to'): 'lend', ('affect/effect', 'verb'): 'affect', ('affect/effect', 'noun'): 'effect',
    ('bring/take', 'here'): 'bring', ('bring/take', 'away'): 'take', ('win/beat', 'opponent'): 'beat', ('win/beat', 'prize'): 'win',
    ('lose/miss', 'transport'): 'miss', ('lose/miss', 'thing'): 'lose', ('remember/remind', 'remind'): 'remind', ('remember/remind', 'remember'): 'remember',
    ('hear/listen', 'listen'): 'listen', ('hear/listen', 'hear'): 'hear', ('see/watch/look', 'look'): 'look', ('see/watch/look', 'watch'): 'watch',
    ('see/watch/look', 'see'): 'see', ('job/work', 'job'): 'job', ('job/work', 'work'): 'work', ('trip/journey/travel', 'trip'): 'trip',
    ('trip/journey/travel', 'travel'): 'travel', ('trip/journey/travel', 'journey'): 'journey', ('teach/learn', 'learn'): 'learn',
    ('teach/learn', 'teach'): 'teach', ('fun/funny', 'fun'): 'fun', ('fun/funny', 'funny'): 'funny',
}
LEMMA = {'raised': 'raise', 'rose': 'rise', 'rises': 'rise', 'lay': None, 'lent': 'lend', 'borrowed': 'borrow', 'affected': 'affect', 'affects': 'affect',
         'beat': 'beat', 'won': 'win', 'missed': 'miss', 'lost': 'lose', 'reminds': 'remind', 'listening': 'listen', 'Look': 'look', 'watched': 'watch',
         'taught': 'teach'}


def gen_conf(rng):
    pair, feat, sent, right, dis = rng.choice(CONF)
    return sent, [right] + dis, right, f'{pair}: ' + {
        'rise/raise': 'raise + дополнение (поднять что-то), rise — без дополнения (подниматься)', 'lie/lay': 'lay + дополнение (класть), lie — лежать (lie–lay–lain)',
        'borrow/lend': 'borrow — взять у кого-то (from), lend — дать кому-то (to)', 'affect/effect': 'affect — глагол «влиять», effect — существительное «эффект»',
        'bring/take': 'bring — сюда, к говорящему; take — отсюда, с собой', 'win/beat': 'win + игра/приз, beat + соперник', 'lose/miss': 'miss + автобус/урок, lose + вещь/игра',
        'remember/remind': 'remind + кому (remind me of / to), remember — помнить самому', 'hear/listen': 'listen to — слушать, hear — слышать',
        'see/watch/look': 'look at — смотреть на, watch — смотреть (фильм, матч), see — видеть', 'job/work': 'job — исчисляемое (a job), work — неисчисляемое',
        'trip/journey/travel': 'a trip — поездка, a journey — путь (долгий), travel — путешествия вообще', 'teach/learn': 'teach — учить кого-то, learn — учиться самому',
        'fun/funny': 'fun — существительное (great fun), funny — смешной'}[pair], (pair, feat, right)


def chk_conf(feat):
    pair, f, right = feat
    lemma = CONF_RULE[(pair, f)]
    if right == 'lay':  # lay: и инфинитив lay (класть), и прошедшее от lie
        return right if lemma in ('lay', 'lie') else None
    got = LEMMA.get(right, right)
    return right if got == lemma else None


LEX_PROTOS = [
    {'id': 'eng-ege-30-make-do', 'n': 30, 'title': 'Лексическая сочетаемость: make / do', 'kes': ['2.3.1', '2.3.2'],
     'invariant': 'предложение с пропуском глагола перед устойчивым дополнением (a mistake, homework…)', 'varies': 'дополнение, время глагола, дистракторы (take, get, have, give)',
     'answer_rule': 'таблица сочетаний make/do; проверка — обратный словарь «дополнение → глагол»', 'mistakes': ['make homework', 'do a mistake', 'take a decision'],
     'gen': gen_make_do, 'check': chk_make_do},
    {'id': 'eng-ege-31-say-tell-speak-talk', 'n': 31, 'title': 'Лексическая сочетаемость: say / tell / speak / talk', 'kes': ['2.3.1', '2.3.2'],
     'invariant': 'предложение с пропуском; признак в рамке: кому (tell), что (say), язык или громкость (speak), about (talk)', 'varies': 'признак, предложение, время',
     'answer_rule': 'правило по признаку; устойчивые сочетания (tell the truth, say sorry) — отдельная таблица', 'mistakes': ['say me', 'tell that', 'talk English'],
     'gen': gen_stt, 'check': chk_stt},
    {'id': 'eng-ege-32-preposition', 'n': 32, 'title': 'Предлог после глагола или прилагательного', 'kes': ['2.3.1', '2.3.2'],
     'invariant': 'предложение с пропуском предлога после слова с фиксированным управлением; дистракторы — предлоги, не образующие сочетания', 'varies': 'слово (30 сочетаний), предложение',
     'answer_rule': 'таблица управления; проверка — вторая таблица', 'mistakes': ['interested on', 'depend from', 'arrive to', 'good in'],
     'gen': gen_prep, 'check': chk_prep},
    {'id': 'eng-ege-33-ed-ing', 'n': 33, 'title': 'Прилагательные на -ed и -ing', 'kes': ['2.3.4'],
     'invariant': 'рамка задаёт носителя признака: человек (чувство → -ed) или предмет/событие (свойство → -ing); варианты: -ed, -ing, глагол, существительное',
     'varies': 'пара (15), рамка, событие', 'answer_rule': 'правило: испытывающий → -ed, вызывающий → -ing; проверка по второй таблице пар',
     'mistakes': ['I am boring', 'the film was interested', 'excitement вместо exciting'], 'gen': gen_eding, 'check': chk_eding},
    {'id': 'eng-ege-34-phrasal', 'n': 34, 'title': 'Фразовые глаголы: выбор частицы', 'kes': ['2.3.5'],
     'invariant': 'глагол дан, пропущена частица; четыре частицы одного глагола, только одна даёт нужное значение', 'varies': 'глагол (10), значение (40), предложение',
     'answer_rule': 'таблица «глагол + частица → значение»; проверка — обратная таблица «значение → частица»', 'mistakes': ['частица по русскому смыслу (look for = «заботиться»)', 'get on / get over'],
     'gen': gen_phrasal, 'check': chk_phrasal},
    {'id': 'eng-ege-35-linkers', 'n': 35, 'title': 'Союзы и связки: although / despite / however / because / so / unless…', 'kes': ['2.3.2', '2.4.9'],
     'invariant': 'структура после пропуска (придаточное, именная группа, новое предложение) и смысл (уступка, причина, следствие, цель, условие) задают связку; набор из четырёх подобран так, что подходит одна',
     'varies': 'признак (12), предложение, набор вариантов', 'answer_rule': 'правило «признак → связка»; проверка — вторая таблица', 'mistakes': ['despite + придаточное', 'however внутри предложения', 'unless … not'],
     'gen': gen_linker, 'check': chk_linker},
    {'id': 'eng-ege-36-confusables', 'n': 36, 'title': 'Пары-путаницы: rise/raise, lie/lay, borrow/lend, affect/effect, win/beat…', 'kes': ['2.3.1', '2.3.3'],
     'invariant': 'предложение с признаком, различающим пару (есть ли дополнение, направление, часть речи); варианты — оба слова пары и два похожих', 'varies': 'пара (14), признак, предложение',
     'answer_rule': 'таблица «пара + признак → слово»; проверка — лемматизация ответа и сверка со второй таблицей', 'mistakes': ['rise your hand', 'borrow me', 'win the team', 'lose the bus'],
     'gen': gen_conf, 'check': chk_conf},
]
