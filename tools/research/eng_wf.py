"""Словообразование (ЕГЭ 25–29, ОГЭ 29–34): собственные гнёзда, предложения и правила вывода формы.

Каждая запись: семейство прототипа, ОСНОВА, ответ, аффиксы по кодификатору (ЕГЭ 2.3.11 / ОГЭ 2.3.7), уровень
(A2/B1 — годится для ОГЭ, B2 — только ЕГЭ), предложения с пропуском (составлены для генератора), при
нерегулярной основе — stem. Ответ хранится явно; `derive()` выводит слово из основы и аффиксов по правилам
орфографии независимо — это вторая таблица для самопроверки. Расхождение = ошибка записи.
"""
import re

VOW = 'aeiou'
DOUBLE = {'run', 'swim', 'begin', 'win', 'shop', 'sun', 'fog', 'fun', 'mud', 'red', 'sad', 'fat', 'flat', 'forget', 'regret', 'stop',
          'plan', 'big', 'hot', 'wet', 'thin', 'snob', 'travel', 'rob'}


def attach(w, s):
    """Присоединить суффикс s (без дефиса) к основе w по правилам орфографии."""
    cy = re.search(r'[^aeiou]y$', w)
    if s == 'tion':
        if w.endswith('te'):
            return w[:-1] + 'ion'
        if w.endswith('t'):
            return w + 'ion'
        return (w[:-1] if w.endswith('e') else w) + 'ation'
    if s == 'sion':
        if w.endswith('ss'):
            return w + 'ion'
        if w.endswith('e'):
            return w[:-1] + 'ion'
        return w + 'sion'
    if s == 'ly':
        if w.endswith('ic') and w != 'public':
            return w + 'ally'
        if w.endswith('le') and w[-3] not in VOW:
            return w[:-1] + 'y'
        if cy:
            return w[:-1] + 'ily'
        return w + 'ly'
    if s in ('ness', 'ful', 'al', 'ous', 'able', 'ment'):
        if cy and s != 'ment':
            w = w[:-1] + 'i'
        if s in ('al', 'ous', 'able') and w.endswith('e') and not (s in ('ous', 'able') and w[-2:] in ('ge', 'ce')):
            w = w[:-1]
        return w + s
    if s in ('ing', 'ed', 'er', 'y', 'en', 'ish'):
        if w in DOUBLE:
            w = w + w[-1]
        elif w.endswith('ie') and s == 'ing':
            w = w[:-2] + 'y'
        elif w.endswith('e') and not w.endswith('ee'):
            w = w[:-1] if s != 'ed' else w[:-1]
        elif cy and s in ('ed', 'er'):
            w = w[:-1] + 'i'
        if s == 'ed' and w.endswith('i') and cy:
            return w + 'ed'
        return w + s
    if s in ('ity', 'ance', 'ence', 'ive', 'ible', 'or', 'ise', 'ize', 'ist'):
        if w.endswith('e') or (s in ('ise', 'ize') and w.endswith('y')) or (s == 'ist' and w.endswith('o')):
            w = w[:-1]
        return w + s
    if s == 'ical':
        return (w[:-1] if w.endswith(('y', 'e')) else w) + s
    if s in ('ian', 'an', 'ese'):
        if w.endswith(('a', 'y')) or (s == 'an' and w.endswith('o')):
            w = w[:-1]
        return w + s
    if s == 'th':
        return w[:-1] + 'ieth' if w.endswith('y') else w + 'th'
    return w + s  # ship, less, teen, ty


def derive(base, affs, stem=None):
    w = stem or base.lower()
    for a in [a for a in affs if a.startswith('-')]:
        w = (w + a[1:]) if stem else attach(w, a[1:])  # stem — задокументированный нерегулярный алломорф, суффикс к нему приписывается буквально
    for p in reversed([a for a in affs if a.endswith('-')]):
        w = p[:-1] + w
    return w


WF_FAMILY_TITLES = {
    'noun': ('Словообразование: абстрактное существительное (-tion/-sion, -ment, -ness, -ity, -ance/-ence, -ship, -ing)',
             'в предложении нужно существительное (после артикля, притяжательного, of, прилагательного)',
             ['глагол или прилагательное вместо существительного', 'decission, goverment', 'begining', '-ance/-ence']),
    'agent': ('Словообразование: деятель и профессия (-er/-or, -ist, -ian)',
              'нужно существительное-лицо (a/an, множественное число, профессия)',
              ['-er вместо -or (visiter)', 'нет множественного числа (thousands of visitor)', 'scientist без t']),
    'adj': ('Словообразование: прилагательное с суффиксом (-ful, -less, -ous, -ive, -al, -able/-ible, -y, -ish, -ical)',
            'нужно прилагательное (перед существительным, после be/look/seem)',
            ['существительное вместо прилагательного', 'carefull, successfull', '-able/-ible', 'famouse, dangerouse']),
    'nationality': ('Словообразование: национальность и язык (-an/-ian, -ese, -ish)', 'название страны → прилагательное или язык',
                    ['Chinian, Japanish', 'строчная буква', 'Englander']),
    'participle': ('Словообразование: причастия-прилагательные -ed / -ing', 'нужно прилагательное: чувство (-ed) или свойство вещи (-ing)',
                   ['bored/boring по смыслу', 'exciteing', 'existing vs excited']),
    'negative': ('Словообразование: отрицательный префикс (un-, in-/im-, il-/ir-, dis-, non-)', 'по смыслу нужно отрицание; часть речи сохраняется или добавляется суффикс',
                 ['unpossible, inregular, unlegal', 'отрицание не услышано по смыслу', 'dis- вместо un-']),
    'adverb': ('Словообразование: наречие на -ly (в том числе с un-, -ful + -ly, -ic + -ally)', 'нужно наречие (при глаголе или прилагательном)',
               ['прилагательное вместо наречия', 'happyly, easyly', 'basicly', 'carefuly']),
    'verb-prefix': ('Словообразование: глагольный префикс (dis-, mis-, re-, over-, under-)', 'нужен глагол с изменённым значением; форма глагола задана рамкой',
                    ['префикс не по смыслу (misagree)', 'не изменена форма глагола (overslept)', 'unlike вместо dislike']),
    'verb-suffix': ('Словообразование: глагол с суффиксом (-ise/-ize, -en)', 'нужен глагол (после to, модального или в личной форме)',
                    ['-ise/-ize — оба верны', 'wide вместо widen', 'modernate']),
    'numeral': ('Словообразование: числительные (-teen, -ty, -th)', 'нужно числительное другого разряда: -teen, -ty или порядковое',
                ['fiveteen, fivety', 'fourty', 'nineth, twelveth']),
    'inter-pre-post': ('Словообразование: префиксы inter-, pre-, post-', 'нужно прилагательное или существительное с этим префиксом',
                       ['пропущен префикс', 'inter- vs intra-', 'prewar/postwar по смыслу']),
}

# (семейство, ОСНОВА, ответ, аффиксы, уровень, предложения[, stem])
_E = [
    # --- существительные абстрактные
    ('noun', 'DECIDE', 'decision', ['-sion'], 'B1', ['Moving to another city was a difficult ____ for the whole family.',
                                                    'It was your ____, so don\'t blame me now.'], 'deci'),
    ('noun', 'HAPPY', 'happiness', ['-ness'], 'A2', ['Money cannot buy ____, my grandmother always says.', 'Her face was full of ____ when she saw the puppy.']),
    ('noun', 'EXPECT', 'expectations', ['-tion'], 'B2', ['The show was brilliant and went far beyond our ____.'], 'expecta'),
    ('noun', 'INFORM', 'information', ['-tion'], 'A2', ['You can find all the ____ on the school website.', 'Tourists can get free ____ about the city at the station.']),
    ('noun', 'INVENT', 'invention', ['-tion'], 'B1', ['The telephone was the most important ____ of the nineteenth century.', 'Grandpa says the bicycle is a wonderful ____.']),
    ('noun', 'CELEBRATE', 'celebration', ['-tion'], 'A2', ['The ____ of the city\'s birthday lasted three days.', 'We had a small ____ when my sister passed her exams.']),
    ('noun', 'EDUCATE', 'education', ['-tion'], 'B1', ['A good ____ opens many doors in life.', 'Free ____ for all children was introduced in the country a hundred years ago.']),
    ('noun', 'COLLECT', 'collection', ['-tion'], 'A2', ['My uncle has a huge ____ of old coins.', 'The museum\'s ____ includes paintings from many countries.']),
    ('noun', 'ORGANISE', 'organisation', ['-tion'], 'B1', ['A charity ____ helped the family after the fire.', 'The ____ of the festival took the volunteers two months.']),
    ('noun', 'DISCUSS', 'discussion', ['-sion'], 'B1', ['After a long ____ the class chose the theme for the party.', 'The ____ of the film went on for an hour.']),
    ('noun', 'EXPLAIN', 'explanation', ['-tion'], 'B1', ['The teacher gave a clear ____ of the new rule.', 'Nobody could find an ____ for the strange noise.'], 'explana'),
    ('noun', 'IMAGINE', 'imagination', ['-tion'], 'B1', ['Children have a rich ____ and love making up stories.', 'Use your ____ and draw a city of the future.']),
    ('noun', 'GOVERN', 'government', ['-ment'], 'B1', ['The ____ has promised to build new roads in the region.', 'The city ____ opened three new parks last year.']),
    ('noun', 'ENJOY', 'enjoyment', ['-ment'], 'B1', ['The kids played in the snow with great ____.', 'Reading gives me a lot of ____ in the evenings.']),
    ('noun', 'EQUIP', 'equipment', ['-ment'], 'B1', ['All the sports ____ is kept in the storeroom.', 'You need special ____ for climbing.']),
    ('noun', 'DEVELOP', 'development', ['-ment'], 'B1', ['The ____ of the internet changed the way we study.', 'The town grew quickly with the ____ of the port.']),
    ('noun', 'ARGUE', 'argument', ['-ment'], 'B1', ['The brothers had an ____ about who should wash the car.', 'It was a silly ____, and they soon made up.'], 'argu'),
    ('noun', 'AGREE', 'agreement', ['-ment'], 'B1', ['The two schools signed an ____ about student exchanges.', 'After an hour they finally reached an ____.']),
    ('noun', 'MOVE', 'movement', ['-ment'], 'B1', ['A sudden ____ in the grass frightened the birds.', 'The ____ of the planets was studied by ancient astronomers.']),
    ('noun', 'ILL', 'illness', ['-ness'], 'A2', ['After a long ____ Grandpa returned to his garden.', 'The doctor said the ____ was not serious.']),
    ('noun', 'KIND', 'kindness', ['-ness'], 'A2', ['Thank you for your ____ — I will never forget it.', 'A small act of ____ can change somebody\'s day.']),
    ('noun', 'DARK', 'darkness', ['-ness'], 'A2', ['We walked home in complete ____ because the street lights were off.', 'The cat\'s eyes shone in the ____.']),
    ('noun', 'WEAK', 'weakness', ['-ness'], 'B1', ['Chocolate is my only ____.', 'The team\'s main ____ is its defence.']),
    ('noun', 'FIT', 'fitness', ['-ness'], 'A2', ['Our PE teacher says ____ is more important than strength.', 'The new ____ club is open from six in the morning.']),
    ('noun', 'POSSIBLE', 'possibility', ['-ity'], 'B1', ['There is a ____ that the flight will be delayed.', 'We discussed the ____ of a trip to Lake Baikal.'], 'possibil'),
    ('noun', 'ABLE', 'ability', ['-ity'], 'B1', ['Dolphins have an amazing ____ to find their way in the dark.', 'His ____ to remember names is unbelievable.'], 'abil'),
    ('noun', 'POPULAR', 'popularity', ['-ity'], 'B1', ['The ____ of electric scooters is growing fast.', 'The singer\'s ____ grew after the festival.']),
    ('noun', 'ACTIVE', 'activity', ['-ity'], 'A2', ['Swimming is my favourite outdoor ____.', 'The camp offers a new ____ every day.']),
    ('noun', 'REAL', 'reality', ['-ity'], 'B1', ['His dream of flying became ____ when he got a job as a pilot.', 'In ____ the trip cost twice as much as we had planned.']),
    ('noun', 'SIMILAR', 'similarity', ['-ity'], 'B2', ['The ____ between the two languages surprised me.', 'There is a strong ____ between the twins\' handwriting.']),
    ('noun', 'CURIOUS', 'curiosity', ['-ity'], 'B2', ['Out of ____ I opened the old box in the attic.', '____ is the best quality in a young scientist.'], 'curios'),
    ('noun', 'PERFORM', 'performance', ['-ance'], 'B1', ['The actors gave an amazing ____ last night.', 'Her ____ in the final was the best of the season.']),
    ('noun', 'APPEAR', 'appearance', ['-ance'], 'B1', ['The actor\'s sudden ____ on stage surprised everybody.', 'Don\'t judge people by their ____.']),
    ('noun', 'IMPORTANT', 'importance', ['-ance'], 'B1', ['The teacher explained the ____ of sleep before an exam.', 'Nobody understood the ____ of the discovery at first.'], 'import'),
    ('noun', 'DIFFER', 'difference', ['-ence'], 'A2', ['Can you spot the ____ between these two pictures?', 'There is a big ____ between reading a book and watching a film.']),
    ('noun', 'PREFER', 'preference', ['-ence'], 'B2', ['My ____ is tea, but coffee is fine too.', 'The hotel asked about our ____ for a room with a view.']),
    ('noun', 'PATIENT', 'patience', ['-ence'], 'B1', ['Fishing needs a lot of ____.', 'The teacher lost her ____ when the noise did not stop.'], 'pati'),
    ('noun', 'SILENT', 'silence', ['-ence'], 'B1', ['There was complete ____ in the hall when the winner was announced.', 'The forest was covered in snow and ____.'], 'sil'),
    ('noun', 'CONFIDENT', 'confidence', ['-ence'], 'B2', ['Winning the school contest gave Ann a lot of ____.', 'He spoke with such ____ that everybody believed him.'], 'confid'),
    ('noun', 'EXIST', 'existence', ['-ence'], 'B2', ['Scientists doubted the ____ of the lake monster.', 'The ____ of water on Mars is still a question.']),
    ('noun', 'FRIEND', 'friendship', ['-ship'], 'A2', ['Their ____ started at a summer camp.', 'True ____ is stronger than distance.']),
    ('noun', 'CHAMPION', 'championship', ['-ship'], 'A2', ['Our team won the city ____ for the first time.', 'The world ____ will take place in July.']),
    ('noun', 'MEMBER', 'membership', ['-ship'], 'B1', ['A yearly ____ of the sports club costs less than monthly payments.', 'The library offers free ____ to schoolchildren.']),
    ('noun', 'RELATION', 'relationship', ['-ship'], 'B1', ['Ann has a good ____ with her older sister.', 'The ____ between the two countries has always been close.']),
    ('noun', 'LEADER', 'leadership', ['-ship'], 'B2', ['Under her ____ the school choir became famous.', 'Good ____ means listening to the team.']),
    ('noun', 'BUILD', 'building', ['-ing'], 'A2', ['The tallest ____ in the city has eighty floors.', 'The old ____ on the corner is now a museum.']),
    ('noun', 'PAINT', 'painting', ['-ing'], 'A2', ['The ____ on the wall shows a winter forest.', 'This ____ was sold for a million dollars.']),
    ('noun', 'MEET', 'meeting', ['-ing'], 'A2', ['The ____ of the school council starts at four.', 'Our first ____ was at a bus stop in the rain.']),
    ('noun', 'BEGIN', 'beginning', ['-ing'], 'A2', ['At the ____ of the film nobody knew who the hero was.', 'The ____ of the school year is always busy.']),
    ('noun', 'FEEL', 'feeling', ['-ing'], 'A2', ['I had a strange ____ that somebody was watching me.', 'The ____ of flying was wonderful.']),
    ('noun', 'TRAIN', 'training', ['-ing'], 'A2', ['Football ____ takes place twice a week.', 'After six months of ____ she ran her first marathon.']),
    # --- деятели и профессии
    ('agent', 'VISIT', 'visitors', ['-or'], 'A2', ['The museum welcomes thousands of ____ every summer.', 'All ____ must leave their bags at the entrance.']),
    ('agent', 'TEACH', 'teacher', ['-er'], 'A2', ['Our new maths ____ explains everything very clearly.', 'My mother works as a primary school ____.']),
    ('agent', 'ACT', 'actor', ['-or'], 'A2', ['My favourite ____ played a pirate in that film.', 'The young ____ forgot his words in the second act.']),
    ('agent', 'DIRECT', 'director', ['-or'], 'B1', ['The ____ of the film was only twenty-five years old.', 'The school ____ opened the sports festival.']),
    ('agent', 'INVENT', 'inventor', ['-or'], 'B1', ['The ____ of the first radio was born in this town.', 'A young ____ from our school won a national prize.']),
    ('agent', 'SAIL', 'sailor', ['-or'], 'A2', ['My grandfather was a ____ and saw half the world.', 'An old ____ told us a story about a storm.']),
    ('agent', 'TRANSLATE', 'translator', ['-or'], 'B1', ['My aunt works as a ____ for a big company.', 'The ____ helped the tourists talk to the guide.']),
    ('agent', 'EDIT', 'editor', ['-or'], 'B1', ['The ____ of the school newspaper is a girl from the tenth form.', 'The ____ cut two pages from the article.']),
    ('agent', 'WRITE', 'writer', ['-er'], 'A2', ['This ____ is famous for her detective stories.', 'A young ____ read his poems to the class.']),
    ('agent', 'DRIVE', 'driver', ['-er'], 'A2', ['The bus ____ waited for the running boy.', 'A taxi ____ showed us the way to the hotel.']),
    ('agent', 'SING', 'singer', ['-er'], 'A2', ['The ____ from the talent show is now on TV.', 'A street ____ was playing the guitar near the fountain.']),
    ('agent', 'PLAY', 'players', ['-er'], 'A2', ['Eleven ____ ran onto the field.', 'The best ____ of the tournament got a golden ball.']),
    ('agent', 'RUN', 'runners', ['-er'], 'A2', ['Two hundred ____ took part in the city marathon.', 'The ____ waited for the signal.']),
    ('agent', 'WIN', 'winner', ['-er'], 'A2', ['The ____ of the quiz gets a trip to St Petersburg.', 'Every ____ received a medal and a book.']),
    ('agent', 'FARM', 'farmer', ['-er'], 'A2', ['The ____ sells fresh milk at the Sunday market.', 'A local ____ let us ride his horse.']),
    ('agent', 'PAINT', 'painter', ['-er'], 'A2', ['The ____ finished the portrait in a week.', 'This ____ loved the sea and painted it all his life.']),
    ('agent', 'BEGIN', 'beginners', ['-er'], 'B1', ['The ski school has special groups for ____.', 'This book is written for ____, so the texts are simple.']),
    ('agent', 'TRAVEL', 'travellers', ['-er'], 'B1', ['The old inn was full of ____ from all over the country.', 'Many ____ choose trains instead of planes now.']),
    ('agent', 'ART', 'artist', ['-ist'], 'A2', ['The young ____ paints portraits of her friends.', 'An unknown ____ decorated the wall of the school.']),
    ('agent', 'SCIENCE', 'scientists', ['-ist'], 'B1', ['A team of young ____ discovered a new kind of beetle.', '____ say the winter will be colder than usual.'], 'scient'),
    ('agent', 'TOUR', 'tourists', ['-ist'], 'A2', ['In summer the old town is full of ____.', 'The guide showed the ____ the way to the castle.']),
    ('agent', 'JOURNAL', 'journalist', ['-ist'], 'B1', ['A ____ from the local newspaper interviewed our headmaster.', 'My cousin wants to be a sports ____.']),
    ('agent', 'PIANO', 'pianist', ['-ist'], 'B1', ['The ____ played for two hours without notes.', 'A famous ____ gave a concert in our town.']),
    ('agent', 'CYCLE', 'cyclists', ['-ist'], 'B1', ['New paths for ____ were built along the river.', 'The ____ stopped to drink water on the hill.']),
    ('agent', 'GUITAR', 'guitarist', ['-ist'], 'A2', ['The ____ of the band is my neighbour.', 'A young ____ won the music competition.']),
    ('agent', 'BIOLOGY', 'biologist', ['-ist'], 'B1', ['A ____ from the university spoke to us about whales.', 'My sister wants to be a marine ____.'], 'biolog'),
    ('agent', 'MUSIC', 'musician', ['-ian'], 'A2', ['Her uncle is a professional ____ who plays the cello.', 'The street ____ collected a lot of coins.']),
    ('agent', 'HISTORY', 'historian', ['-ian'], 'B1', ['A local ____ wrote a book about our street.', 'The ____ found a letter from the eighteenth century.']),
    ('agent', 'LIBRARY', 'librarian', ['-ian'], 'A2', ['The ____ helped me find a book about dinosaurs.', 'Our school ____ organises reading clubs.']),
    ('agent', 'ELECTRIC', 'electrician', ['-ian'], 'B1', ['An ____ came to repair the lights in the hall.', 'My father works as an ____ at the factory.']),
    ('agent', 'POLITICS', 'politician', ['-ian'], 'B2', ['A famous ____ visited our school on Victory Day.', 'The young ____ promised to build a new stadium.'], 'politic'),
    ('agent', 'MAGIC', 'magician', ['-ian'], 'A2', ['The ____ pulled a rabbit out of his hat.', 'A ____ showed tricks at my brother\'s birthday party.']),
    # --- прилагательные
    ('adj', 'CARE', 'careful', ['-ful'], 'A2', ['Be ____ when you cross the road near the school.', 'A ____ driver always looks in the mirror.']),
    ('adj', 'CARE', 'careless', ['-less'], 'B1', ['A ____ mistake cost him a point in the test.', 'It was ____ of you to leave the door open.']),
    ('adj', 'SUCCESS', 'successful', ['-ful'], 'B1', ['The concert was so ____ that they decided to repeat it.', 'She is a ____ designer with her own shop.']),
    ('adj', 'BEAUTY', 'beautiful', ['-ful'], 'A2', ['The view from the hill is really ____.', 'What a ____ dress!']),
    ('adj', 'USE', 'useful', ['-ful'], 'A2', ['A map is very ____ in a new city.', 'The teacher gave us some ____ advice before the exam.']),
    ('adj', 'USE', 'useless', ['-less'], 'B1', ['Without a battery the torch is ____.', 'It is ____ to argue with him.']),
    ('adj', 'HELP', 'helpful', ['-ful'], 'A2', ['The shop assistant was very ____ and polite.', 'Your notes were really ____, thank you.']),
    ('adj', 'HELP', 'helpless', ['-less'], 'B1', ['Without the internet I feel absolutely ____.', 'The tiny kitten looked ____ in the rain.']),
    ('adj', 'PEACE', 'peaceful', ['-ful'], 'B1', ['The village is quiet and ____ in winter.', 'We spent a ____ afternoon by the lake.']),
    ('adj', 'WONDER', 'wonderful', ['-ful'], 'A2', ['We had a ____ time at the seaside.', 'What a ____ idea!']),
    ('adj', 'COLOUR', 'colourful', ['-ful'], 'A2', ['The market was full of ____ fruit and vegetables.', 'The children drew ____ pictures of spring.']),
    ('adj', 'HOPE', 'hopeless', ['-less'], 'B1', ['The situation seemed ____, but then help arrived.', 'I am ____ at maths, so my brother helps me.']),
    ('adj', 'HOME', 'homeless', ['-less'], 'B1', ['The shelter gives food to ____ people every evening.', 'After the flood many families were ____.']),
    ('adj', 'END', 'endless', ['-less'], 'B1', ['The road across the desert seemed ____.', 'The lesson felt ____ because everybody was tired.']),
    ('adj', 'DANGER', 'dangerous', ['-ous'], 'A2', ['Swimming in this river is ____ because of the strong current.', 'Crossing the road here is very ____.']),
    ('adj', 'FAME', 'famous', ['-ous'], 'A2', ['Our town is ____ for its old wooden houses.', 'A ____ singer was born in this street.']),
    ('adj', 'MYSTERY', 'mysterious', ['-ous'], 'B1', ['A ____ light appeared over the lake at night.', 'The stranger left a ____ note on the table.']),
    ('adj', 'NERVE', 'nervous', ['-ous'], 'B1', ['I always feel ____ before an exam.', 'The ____ boy kept looking at his watch.']),
    ('adj', 'POISON', 'poisonous', ['-ous'], 'B1', ['Some of these mushrooms are ____, so don\'t touch them.', 'The snake in the picture is not ____.']),
    ('adj', 'COURAGE', 'courageous', ['-ous'], 'B2', ['It was a ____ decision to leave the well-paid job.', 'The ____ girl pulled the dog out of the ice.']),
    ('adj', 'ADVENTURE', 'adventurous', ['-ous'], 'B1', ['My ____ uncle has climbed mountains on four continents.', 'Ann is not very ____ — she prefers a quiet holiday.']),
    ('adj', 'ATTRACT', 'attractive', ['-ive'], 'B1', ['The old town is very ____ to tourists.', 'The offer looked ____, but we refused.']),
    ('adj', 'ACT', 'active', ['-ive'], 'A2', ['My grandmother is very ____ for her age.', 'Try to be more ____ in class.']),
    ('adj', 'CREATE', 'creative', ['-ive'], 'B1', ['Maria is the most ____ person in our group.', 'The project needs ____ ideas, not money.']),
    ('adj', 'EXPENSE', 'expensive', ['-ive'], 'A2', ['The tickets were too ____ for us.', 'This is the most ____ hotel in the town.']),
    ('adj', 'EFFECT', 'effective', ['-ive'], 'B2', ['Regular exercise is the most ____ way to stay healthy.', 'The new medicine proved ____ against the flu.']),
    ('adj', 'IMPRESS', 'impressive', ['-ive'], 'B1', ['The view from the tower is really ____.', 'Her results in the competition were ____.']),
    ('adj', 'NATION', 'national', ['-al'], 'A2', ['The ____ park attracts thousands of tourists every year.', 'Football is the ____ sport of Brazil.']),
    ('adj', 'NATURE', 'natural', ['-al'], 'A2', ['The lake is a ____ wonder of our region.', 'It is ____ to feel tired after a long walk.']),
    ('adj', 'TRADITION', 'traditional', ['-al'], 'B1', ['Pancakes are a ____ Russian dish.', 'The dancers wore ____ costumes.']),
    ('adj', 'CULTURE', 'cultural', ['-al'], 'B1', ['The city is the ____ centre of the region.', 'There are many ____ events in May.']),
    ('adj', 'PERSON', 'personal', ['-al'], 'B1', ['This is my ____ opinion, you may disagree.', 'Don\'t share ____ information with strangers online.']),
    ('adj', 'MUSIC', 'musical', ['-al'], 'A2', ['Can you play any ____ instrument?', 'Our school has a ____ evening every spring.']),
    ('adj', 'CENTRE', 'central', ['-al'], 'A2', ['The hotel is in the ____ part of the city.', 'The ____ square is closed for the festival.'], 'centr'),
    ('adj', 'ORIGIN', 'original', ['-al'], 'B1', ['Is this the ____ painting or a copy?', 'The ____ plan was to go by train.']),
    ('adj', 'COMFORT', 'comfortable', ['-able'], 'A2', ['The new sofa is really ____.', 'These boots are warm and ____.']),
    ('adj', 'ENJOY', 'enjoyable', ['-able'], 'B1', ['The trip to the farm was ____ for the whole class.', 'Reading in the garden is a very ____ way to spend a Sunday.']),
    ('adj', 'REASON', 'reasonable', ['-able'], 'B1', ['The prices in this cafe are quite ____.', 'It is ____ to leave early if the roads are icy.']),
    ('adj', 'BELIEVE', 'believable', ['-able'], 'B2', ['The film\'s story is not very ____, but the acting is great.', 'His excuse sounded ____ at first.']),
    ('adj', 'VALUE', 'valuable', ['-able'], 'B1', ['The ring is very ____, so keep it in a safe place.', 'The coach gave us some ____ advice.']),
    ('adj', 'FASHION', 'fashionable', ['-able'], 'B1', ['My sister only wears ____ clothes.', 'Short hair was ____ in the 1920s.']),
    ('adj', 'RELY', 'reliable', ['-able'], 'B2', ['Tom is a ____ friend: he never lets you down.', 'We need a ____ car for the long journey.']),
    ('adj', 'SENSE', 'sensible', ['-ible'], 'B1', ['Taking an umbrella was a ____ idea.', 'Be ____ and don\'t swim after the storm.']),
    ('adj', 'RESPONSE', 'responsible', ['-ible'], 'B1', ['Every pupil is ____ for their own textbooks.', 'Who is ____ for the school garden?']),
    ('adj', 'HORROR', 'horrible', ['-ible'], 'B1', ['The weather was ____ all week, so we stayed inside.', 'What a ____ smell!'], 'horr'),
    ('adj', 'TERROR', 'terrible', ['-ible'], 'A2', ['I had a ____ headache after the concert.', 'The hotel food was ____.'], 'terr'),
    ('adj', 'SUN', 'sunny', ['-y'], 'A2', ['It was a warm ____ day, perfect for a picnic.', 'The south side of the house is always ____.']),
    ('adj', 'RAIN', 'rainy', ['-y'], 'A2', ['On ____ days we play board games at home.', 'October is the most ____ month here.']),
    ('adj', 'CLOUD', 'cloudy', ['-y'], 'A2', ['The morning was ____, but by noon the sun came out.', 'The sky is ____, take a jacket.']),
    ('adj', 'WIND', 'windy', ['-y'], 'A2', ['It is too ____ to fly a kite today.', 'The beach is ____ in the evening.']),
    ('adj', 'HEALTH', 'healthy', ['-y'], 'A2', ['Fruit and vegetables are part of a ____ diet.', 'My grandfather is eighty, but he is strong and ____.']),
    ('adj', 'NOISE', 'noisy', ['-y'], 'A2', ['The street is too ____ at night.', 'Our neighbours have a ____ dog.']),
    ('adj', 'TASTE', 'tasty', ['-y'], 'A2', ['Grandma\'s pies are the most ____ in the world.', 'The soup was hot and ____.']),
    ('adj', 'LUCK', 'lucky', ['-y'], 'A2', ['You are ____ to have such a big family.', 'Seven is my ____ number.']),
    ('adj', 'DIRT', 'dirty', ['-y'], 'A2', ['Take off your ____ boots before you come in.', 'The river became ____ after the factory was built.']),
    ('adj', 'FOG', 'foggy', ['-y'], 'A2', ['The morning was so ____ that we could not see the road.', 'Planes cannot land in ____ weather.']),
    ('adj', 'CHILD', 'childish', ['-ish'], 'B1', ['Stop being so ____ and say sorry to your sister.', 'His jokes are a bit ____, but everybody laughs.']),
    ('adj', 'FOOL', 'foolish', ['-ish'], 'B1', ['It was ____ to go sailing in such weather.', 'Don\'t make ____ promises you cannot keep.']),
    ('adj', 'SELF', 'selfish', ['-ish'], 'B1', ['It is ____ to eat the whole cake alone.', 'A ____ person never shares anything.']),
    ('adj', 'HISTORY', 'historical', ['-ical'], 'B1', ['We watched a ____ film about Peter the Great.', 'The old bridge is a ____ monument.']),
    ('adj', 'BIOLOGY', 'biological', ['-ical'], 'B2', ['The scientists made an important ____ discovery.', 'The ____ clock tells animals when to sleep.']),
    ('adj', 'PRACTICE', 'practical', ['-ical'], 'B1', ['The course gives students ____ skills.', 'A ____ present is better than a beautiful but useless one.'], 'pract'),
    ('adj', 'ELECTRIC', 'electrical', ['-al'], 'B1', ['All ____ equipment must be switched off at night.', 'My brother studies ____ engineering.']),
    # --- национальности
    ('nationality', 'RUSSIA', 'Russian', ['-an'], 'A2', ['Pushkin is a famous ____ poet.', 'The ____ winter can be very cold.']),
    ('nationality', 'AMERICA', 'American', ['-an'], 'A2', ['Our new classmate is ____, she comes from Boston.', 'The ____ flag has fifty stars.']),
    ('nationality', 'ITALY', 'Italian', ['-ian'], 'A2', ['Pizza is a traditional ____ dish.', 'My cousin is learning ____ to study in Rome.']),
    ('nationality', 'CANADA', 'Canadian', ['-ian'], 'A2', ['The ____ team won the ice hockey match.', 'A ____ writer visited our library.']),
    ('nationality', 'EGYPT', 'Egyptian', ['-ian'], 'B1', ['The ____ pyramids are more than four thousand years old.', 'We saw an ____ mummy in the museum.']),
    ('nationality', 'BRAZIL', 'Brazilian', ['-ian'], 'B1', ['A ____ dancer taught us samba.', 'The ____ rainforest is the largest in the world.']),
    ('nationality', 'CHINA', 'Chinese', ['-ese'], 'A2', ['My brother is learning ____ because he wants to work in Beijing.', 'We had dinner in a ____ restaurant.']),
    ('nationality', 'JAPAN', 'Japanese', ['-ese'], 'A2', ['Sushi is a popular ____ dish.', 'A group of ____ tourists took photos of the cathedral.']),
    ('nationality', 'VIETNAM', 'Vietnamese', ['-ese'], 'B1', ['My aunt married a ____ doctor.', 'The ____ coffee was very strong.']),
    ('nationality', 'PORTUGAL', 'Portuguese', ['-ese'], 'B1', ['____ is spoken in Brazil too.', 'A ____ ship reached India in 1498.'], 'portugu'),
    ('nationality', 'BRITAIN', 'British', ['-ish'], 'A2', ['The ____ Museum is free for everybody.', 'My pen friend is ____ and lives in Leeds.'], 'brit'),
    ('nationality', 'SPAIN', 'Spanish', ['-ish'], 'A2', ['I speak a little ____ because we often go to Barcelona.', 'The ____ football team is very strong.'], 'span'),
    ('nationality', 'SWEDEN', 'Swedish', ['-ish'], 'B1', ['The ____ singer performed in our city last week.', 'Many ____ families spend summer in the forest.'], 'swed'),
    ('nationality', 'POLAND', 'Polish', ['-ish'], 'B1', ['A ____ film won the festival prize.', 'Our neighbours speak ____ at home.'], 'pol'),
    ('nationality', 'TURKEY', 'Turkish', ['-ish'], 'B1', ['We drank ____ coffee in a tiny cafe.', 'The ____ coast is popular with tourists.'], 'turk'),
    ('nationality', 'IRELAND', 'Irish', ['-ish'], 'B1', ['The ____ dancers wore green costumes.', 'Our teacher is ____, she comes from Dublin.'], 'ir'),
    # --- причастия-прилагательные
    ('participle', 'BORE', 'bored', ['-ed'], 'A2', ['The kids got ____ during the long speech.', 'I was so ____ that I fell asleep.']),
    ('participle', 'BORE', 'boring', ['-ing'], 'A2', ['The lecture was so ____ that half of the audience fell asleep.', 'It is a ____ book with no adventures.']),
    ('participle', 'INTEREST', 'interested', ['-ed'], 'A2', ['My brother is ____ in old cars.', 'Are you ____ in the history of our town?']),
    ('participle', 'INTEREST', 'interesting', ['-ing'], 'A2', ['The film about penguins was really ____.', 'It is an ____ question, let me think.']),
    ('participle', 'EXCITE', 'excited', ['-ed'], 'A2', ['The children were ____ about the trip to the zoo.', 'I am so ____ — tomorrow is my birthday!']),
    ('participle', 'EXCITE', 'exciting', ['-ing'], 'A2', ['It was the most ____ match of the season.', 'The trip down the river was ____.']),
    ('participle', 'SURPRISE', 'surprised', ['-ed'], 'A2', ['We were ____ to see snow in May.', 'Mum was ____ when I cooked dinner.']),
    ('participle', 'SURPRISE', 'surprising', ['-ing'], 'B1', ['It is ____ that the small town has such a big stadium.', 'The end of the story was really ____.']),
    ('participle', 'TIRE', 'tired', ['-ed'], 'A2', ['After the hike we were too ____ to cook.', 'You look ____, go to bed early.']),
    ('participle', 'TIRE', 'tiring', ['-ing'], 'B1', ['Standing all day at the exhibition is ____.', 'It was a long and ____ journey.']),
    ('participle', 'DISAPPOINT', 'disappointed', ['-ed'], 'B1', ['The fans were ____ when the concert was cancelled.', 'I was ____ with my test results.']),
    ('participle', 'DISAPPOINT', 'disappointing', ['-ing'], 'B1', ['The film was ____ after such a good book.', 'The results of the match were ____ for our team.']),
    ('participle', 'AMAZE', 'amazed', ['-ed'], 'B1', ['Everybody was ____ by the magician\'s tricks.', 'I was ____ at how fast she learnt to skate.']),
    ('participle', 'AMAZE', 'amazing', ['-ing'], 'A2', ['The view from the mountain was ____.', 'She has an ____ voice.']),
    ('participle', 'FRIGHTEN', 'frightened', ['-ed'], 'B1', ['The ____ puppy hid under the bed.', 'I was ____ by the thunder.']),
    ('participle', 'FRIGHTEN', 'frightening', ['-ing'], 'B1', ['It was a ____ story about an old castle.', 'The storm at sea was really ____.']),
    ('participle', 'RELAX', 'relaxed', ['-ed'], 'B1', ['After a week at the seaside I felt calm and ____.', 'The teacher was ____ and friendly at the picnic.']),
    ('participle', 'RELAX', 'relaxing', ['-ing'], 'B1', ['A walk in the forest is very ____.', 'We spent a ____ weekend at the lake.']),
    ('participle', 'CONFUSE', 'confused', ['-ed'], 'B1', ['I was ____ by the map and took the wrong turn.', 'The ____ tourist asked three people for the way.']),
    ('participle', 'CONFUSE', 'confusing', ['-ing'], 'B1', ['The rules of the game are ____ at first.', 'The signs at the station were ____.']),
    ('participle', 'EXHAUST', 'exhausted', ['-ed'], 'B2', ['After the marathon the runners were completely ____.', 'I was ____ after two exams in one day.']),
    ('participle', 'FASCINATE', 'fascinating', ['-ing'], 'B2', ['The documentary about octopuses was ____.', 'She told us a ____ story about her trip to Tibet.']),
    ('participle', 'TALENT', 'talented', ['-ed'], 'B1', ['The ____ boy plays the violin and the piano.', 'Our school has many ____ pupils.']),
    ('participle', 'CROWD', 'crowded', ['-ed'], 'B1', ['The beach was ____ on Sunday.', 'The bus was so ____ that we had to stand.']),
    ('participle', 'EXPERIENCE', 'experienced', ['-ed'], 'B2', ['An ____ guide led us across the glacier.', 'The team needs an ____ goalkeeper.']),
    # --- отрицательные префиксы
    ('negative', 'HAPPY', 'unhappy', ['un-'], 'A2', ['Tom looked ____ because his team had lost the final.', 'Why is the baby so ____ today? He has been crying all morning.']),
    ('negative', 'USUAL', 'unusual', ['un-'], 'A2', ['It is very ____ to see snow here in April: it happens once in twenty years.', 'The bird had ____ blue feathers.']),
    ('negative', 'KNOWN', 'unknown', ['un-'], 'B1', ['The letter was signed by an ____ person.', 'The singer was ____ until last year.']),
    ('negative', 'FAIR', 'unfair', ['un-'], 'A2', ['It is ____ that only boys can join the club — girls want to play too.', 'The referee\'s decision was ____, and the fans booed.']),
    ('negative', 'ABLE', 'unable', ['un-'], 'B1', ['I was ____ to come because I was ill.', 'The old man was ____ to read without glasses.']),
    ('negative', 'LUCKY', 'unlucky', ['un-'], 'A2', ['Some people think thirteen is an ____ number and avoid it.', 'We were ____ with the weather on our trip: it rained every day.']),
    ('negative', 'COMFORTABLE', 'uncomfortable', ['un-'], 'B1', ['The chairs in the hall were hard and ____.', 'I felt ____ in my new shoes: they were too tight.']),
    ('negative', 'FRIENDLY', 'unfriendly', ['un-'], 'A2', ['The shop assistant was rude and ____.', 'The new neighbour seemed ____ at first, but later we became good friends.']),
    ('negative', 'EMPLOYED', 'unemployed', ['un-'], 'B1', ['My uncle was ____ for six months after the factory closed.', 'The centre helps ____ people find jobs.']),
    ('negative', 'EXPECTED', 'unexpected', ['un-'], 'B1', ['The storm was completely ____ — the forecast promised sunshine.', 'An ____ guest arrived at dinner time — nobody knew he was in town.']),
    ('negative', 'POSSIBLE', 'impossible', ['im-'], 'A2', ['Without a map it was ____ to find the old path.', 'It is ____ to learn a language in a week.']),
    ('negative', 'POLITE', 'impolite', ['im-'], 'B1', ['It is ____ to talk with your mouth full.', 'The ____ boy did not say thank you.']),
    ('negative', 'PATIENT', 'impatient', ['im-'], 'B1', ['The ____ children could not wait for the cake.', 'Don\'t be so ____ — the bus will come soon.']),
    ('negative', 'CORRECT', 'incorrect', ['in-'], 'A2', ['Two of your answers are ____, please check them again.', 'The address on the letter was ____, so it came back.']),
    ('negative', 'DEPENDENT', 'independent', ['in-'], 'B1', ['At eighteen Mark became ____ and rented his own flat.', 'The country became ____ in 1991.']),
    ('negative', 'FORMAL', 'informal', ['in-'], 'B1', ['Jeans are fine — it is an ____ party.', 'Write an ____ email to your friend: you can use short forms and jokes.']),
    ('negative', 'VISIBLE', 'invisible', ['in-'], 'B1', ['In the fog the lighthouse was almost ____.', 'The hero of the book can become ____.']),
    ('negative', 'LEGAL', 'illegal', ['il-'], 'B1', ['Crossing the border without a passport is ____.', 'It is ____ to park here, you will get a fine.']),
    ('negative', 'REGULAR', 'irregular', ['ir-'], 'B1', ['Learn the ____ verbs by heart, there are not so many of them.', 'His visits to the doctor were ____: once in a few years.']),
    ('negative', 'RESPONSIBLE', 'irresponsible', ['ir-'], 'B2', ['It was ____ to leave the children alone.', 'An ____ driver caused the accident.']),
    ('negative', 'HONEST', 'dishonest', ['dis-'], 'B1', ['It is ____ to copy your friend\'s homework.', 'A ____ shop assistant gave me the wrong change.']),
    ('negative', 'ADVANTAGE', 'disadvantage', ['dis-'], 'B1', ['The only ____ of the flat is the noise from the road.', 'Living far from school is a big ____.']),
    ('negative', 'SENSE', 'nonsense', ['non-'], 'B1', ['Don\'t listen to him — what he says is complete ____.', 'The story about a talking cat is ____, of course.']),
    # --- наречия
    ('adverb', 'CARE', 'carefully', ['-ful', '-ly'], 'A2', ['Read the instructions ____ before you start.', 'Drive ____, the road is icy.']),
    ('adverb', 'QUICK', 'quickly', ['-ly'], 'A2', ['The cat ran ____ up the tree.', 'She answered the question ____.']),
    ('adverb', 'SLOW', 'slowly', ['-ly'], 'A2', ['Speak ____, please, I can\'t follow you.', 'The old bus moved ____ up the hill.']),
    ('adverb', 'HAPPY', 'happily', ['-ly'], 'A2', ['The children played ____ in the garden all day.', 'They lived ____ in a small house by the sea.']),
    ('adverb', 'EASY', 'easily', ['-ly'], 'A2', ['Our team won the match ____.', 'You can ____ find the museum: it is next to the station.']),
    ('adverb', 'LUCKY', 'luckily', ['-ly'], 'B1', ['____, the rain stopped before the match.', 'The vase fell, but ____ it did not break.']),
    ('adverb', 'SUDDEN', 'suddenly', ['-ly'], 'A2', ['____ the lights went out.', 'The dog ____ began to bark.']),
    ('adverb', 'FINAL', 'finally', ['-ly'], 'A2', ['After two hours we ____ found the hotel.', 'The bus ____ arrived at ten.']),
    ('adverb', 'USUAL', 'usually', ['-ly'], 'A2', ['I ____ get up at seven.', 'We ____ spend summer at my grandparents\' place.']),
    ('adverb', 'SAFE', 'safely', ['-ly'], 'B1', ['The plane landed ____ in spite of the storm.', 'Keep your passport ____ in the hotel.']),
    ('adverb', 'QUIET', 'quietly', ['-ly'], 'A2', ['Close the door ____, the baby is sleeping.', 'The students were reading ____ in the library.']),
    ('adverb', 'NERVOUS', 'nervously', ['-ly'], 'B1', ['Nick ____ looked at his watch — the train was late.', 'She laughed ____ before the interview.']),
    ('adverb', 'IMMEDIATE', 'immediately', ['-ly'], 'B1', ['Call the doctor ____ if the temperature goes up.', 'The teacher ____ noticed the mistake.']),
    ('adverb', 'COMPLETE', 'completely', ['-ly'], 'B1', ['I ____ forgot about the meeting.', 'The town was ____ covered in snow.']),
    ('adverb', 'ANGRY', 'angrily', ['-ly'], 'B1', ['"Who broke the window?" Dad asked ____.', 'The driver shouted ____ at the cyclist.']),
    ('adverb', 'BRAVE', 'bravely', ['-ly'], 'B1', ['The boy ____ jumped into the cold water to save the dog.', 'The soldiers fought ____.']),
    ('adverb', 'BASIC', 'basically', ['-ly'], 'B2', ['The two plans are ____ the same.', '____, we need more time.']),
    ('adverb', 'AUTOMATIC', 'automatically', ['-ly'], 'B2', ['The doors open ____ when you come near.', 'The lights switch off ____ at midnight.']),
    ('adverb', 'DRAMATIC', 'dramatically', ['-ly'], 'B2', ['The weather changed ____ in the afternoon.', 'Prices have risen ____ since spring.']),
    ('adverb', 'SUCCESS', 'successfully', ['-ful', '-ly'], 'B1', ['Ann ____ passed her driving test.', 'The rocket was ____ launched at dawn.']),
    ('adverb', 'SUCCESS', 'unsuccessfully', ['un-', '-ful', '-ly'], 'B2', ['He tried ____ to open the jar and finally gave up.', 'The police searched the forest ____ for two days.']),
    ('adverb', 'USUAL', 'unusually', ['un-', '-ly'], 'B1', ['It was ____ cold for May.', 'The streets were ____ quiet on Saturday morning.']),
    ('adverb', 'PATIENT', 'impatiently', ['im-', '-ly'], 'B2', ['The passengers waited ____ for the delayed train.', 'The boy ____ tore open the present.']),
    ('adverb', 'FORTUNATE', 'unfortunately', ['un-', '-ly'], 'B1', ['____, all the tickets for the concert were sold out.', 'We wanted to see the castle, but ____ it was closed.']),
    ('adverb', 'HOPE', 'hopefully', ['-ful', '-ly'], 'B1', ['____, the weather will be fine on Sunday.', 'The dog looked ____ at the sandwich.']),
    ('adverb', 'COMFORTABLE', 'comfortably', ['-ly'], 'B2', ['Five people can sit ____ in the new car.', 'Grandpa settled ____ in his armchair.']),
    ('adverb', 'TERRIBLE', 'terribly', ['-ly'], 'B1', ['I am ____ sorry for being late.', 'The choir sang ____, but everybody clapped.']),
    ('adverb', 'GENTLE', 'gently', ['-ly'], 'B1', ['Hold the kitten ____, it is very small.', 'The wind ____ moved the curtains.']),
    ('adverb', 'DAY', 'daily', ['-ly'], 'B1', ['The museum is open ____ from nine to six.', 'Brushing your teeth ____ keeps them healthy.'], 'dai'),
    ('adverb', 'WEEK', 'weekly', ['-ly'], 'B1', ['The school newspaper comes out ____.', 'We have a ____ meeting of the chess club on Fridays.']),
    # --- глагольные префиксы
    ('verb-prefix', 'AGREE', 'disagree', ['dis-'], 'A2', ['Sorry, but I ____ with you: the book is much better than the film.', 'My parents always ____ about where to spend the holidays, so we usually stay at home.']),
    ('verb-prefix', 'LIKE', 'dislike', ['dis-'], 'A2', ['Cats ____ water, but my cat loves swimming.', 'I ____ getting up early, so weekends are my favourite days.']),
    ('verb-prefix', 'APPEAR', 'disappeared', ['dis-', '-ed'], 'B1', ['The magician\'s rabbit ____ in a second, and nobody could find it.', 'The sun ____ behind the clouds, and it got dark.']),
    ('verb-prefix', 'COVER', 'discovered', ['dis-', '-ed'], 'B1', ['Columbus ____ America in 1492.', 'The children ____ a secret door in the old house.']),
    ('verb-prefix', 'UNDERSTAND', 'misunderstood', ['mis-'], 'B1', ['Sorry, I ____ you — I thought you meant Tuesday.', 'The tourist ____ the sign and went the wrong way.'], 'understood'),
    ('verb-prefix', 'SPELL', 'misspelt', ['mis-'], 'B2', ['I ____ my own surname in the form and had to fill it in again.', 'The name of the street was ____ on the map, so we could not find it.'], 'spelt'),
    ('verb-prefix', 'BEHAVE', 'misbehaved', ['mis-', '-ed'], 'B2', ['The puppy ____ and chewed my shoes.', 'The class ____ when the teacher left the room, so everybody got extra homework.']),
    ('verb-prefix', 'LEAD', 'misled', ['mis-'], 'B2', ['The old map ____ us, and we got lost.', 'The advertisement ____ many buyers.'], 'led'),
    ('verb-prefix', 'WRITE', 'rewrite', ['re-'], 'B1', ['There were so many mistakes that the teacher asked me to ____ the essay.', 'You should ____ this paragraph, it is not clear.']),
    ('verb-prefix', 'BUILD', 'rebuilt', ['re-'], 'B1', ['The old bridge was ____ after the flood, and now it is even stronger.', 'The town was completely ____ after the war, so few old houses remain.'], 'built'),
    ('verb-prefix', 'PLAY', 'replay', ['re-'], 'B1', ['I missed the goal — can you ____ the last minute of the video?', 'The match ended in a draw, so the teams will ____ it on Sunday.']),
    ('verb-prefix', 'CYCLE', 'recycle', ['re-'], 'B1', ['We ____ paper and plastic at school.', 'It is easy to ____ glass bottles.']),
    ('verb-prefix', 'SLEEP', 'overslept', ['over-'], 'B1', ['I ____ this morning and missed the bus.', 'Kate ____ and came to the exam late.'], 'slept'),
    ('verb-prefix', 'EAT', 'overeat', ['over-'], 'B1', ['Try not to ____ at the party.', 'People often ____ during the holidays and then feel sick.']),
    ('verb-prefix', 'COOK', 'overcooked', ['over-', '-ed'], 'B1', ['The pasta was ____: it had been in the pot for half an hour.', 'The meat was ____, dry and hard, because Dad forgot about it.']),
    ('verb-prefix', 'ESTIMATE', 'underestimated', ['under-', '-ed'], 'B2', ['We ____ the journey time: it took twice as long as we had planned.', 'The coach ____ the young team, and it won.']),
    ('verb-prefix', 'PAY', 'underpaid', ['under-'], 'B2', ['The workers felt ____: their wages were the lowest in the region.', 'Teachers in the village felt ____ because their salaries were tiny.'], 'paid'),
    ('verb-prefix', 'LINE', 'underlined', ['under-', '-ed'], 'B1', ['The teacher ____ all the mistakes in red.', 'I ____ the new words in the text.']),
    # --- глагольные суффиксы
    ('verb-suffix', 'MODERN', 'modernise', ['-ise'], 'B1', ['The city plans to ____ its old tram system.', 'The school will ____ its computer classes next year.']),
    ('verb-suffix', 'REAL', 'realise', ['-ise'], 'B1', ['I did not ____ how late it was.', 'Did you ____ that the museum is closed on Mondays?']),
    ('verb-suffix', 'MEMORY', 'memorise', ['-ise'], 'B1', ['You have to ____ the poem by Friday.', 'It is hard to ____ so many dates.']),
    ('verb-suffix', 'APOLOGY', 'apologise', ['-ise'], 'B1', ['You should ____ to your sister for breaking her cup.', 'The shop had to ____ for the mistake.']),
    ('verb-suffix', 'CRITIC', 'criticise', ['-ise'], 'B2', ['It is easy to ____ and hard to help.', 'Don\'t ____ the cook before you try the soup.']),
    ('verb-suffix', 'SPECIAL', 'specialise', ['-ise'], 'B2', ['The shop will ____ in sports shoes.', 'Doctors often ____ in one area of medicine.']),
    ('verb-suffix', 'SUMMARY', 'summarise', ['-ise'], 'B2', ['Can you ____ the article in three sentences?', 'At the end the teacher asked us to ____ the story.']),
    ('verb-suffix', 'ORGAN', 'organise', ['-ise'], 'B1', ['Who will ____ the school trip this year?', 'We need to ____ a meeting for the parents.']),
    ('verb-suffix', 'WIDE', 'widen', ['-en'], 'B1', ['The workers are going to ____ the road next year.', 'Reading helps to ____ your vocabulary.']),
    ('verb-suffix', 'SHORT', 'shorten', ['-en'], 'B1', ['The tailor will ____ the trousers by two centimetres.', 'Try to ____ your speech to five minutes.']),
    ('verb-suffix', 'STRENGTH', 'strengthen', ['-en'], 'B2', ['Regular swimming will ____ your back.', 'The trip helped to ____ our friendship.']),
    ('verb-suffix', 'DARK', 'darkened', ['-en', '-ed'], 'B1', ['The sky ____ and it started to rain.', 'The room ____ when the curtains were closed.']),
    ('verb-suffix', 'DEEP', 'deepen', ['-en'], 'B2', ['The workers will ____ the pond next spring.', 'The course helped me to ____ my knowledge of history.']),
    ('verb-suffix', 'SHARP', 'sharpen', ['-en'], 'B1', ['Please ____ the pencils before the drawing lesson.', 'Crosswords help to ____ the mind.']),
    ('verb-suffix', 'BRIGHT', 'brighten', ['-en'], 'B2', ['Flowers on the table ____ up any room.', 'A few posters will ____ the classroom.']),
    ('verb-suffix', 'FRIGHT', 'frightened', ['-en', '-ed'], 'A2', ['The loud noise ____ the horses.', 'The thunder ____ the little dog.']),
    ('verb-suffix', 'SOFT', 'soften', ['-en'], 'B2', ['Leave the butter on the table to ____.', 'A little milk will ____ the taste of the coffee.']),
    ('verb-suffix', 'LOOSE', 'loosen', ['-en'], 'B2', ['Please ____ the rope a little, it is too tight.', 'You should ____ the screws a little.']),
    # --- числительные
    ('numeral', 'FIVE', 'fifteen', ['-teen'], 'A2', ['The bus leaves in ____ minutes, hurry up!', 'My cousin is ____ and goes to a music school.'], 'fif'),
    ('numeral', 'FIVE', 'fifty', ['-ty'], 'A2', ['About ____ people came to the school concert.', 'The tickets cost ____ roubles each.'], 'fif'),
    ('numeral', 'FIVE', 'fifth', ['-th'], 'A2', ['Our classroom is on the ____ floor.', 'This is the ____ time I have watched this film.'], 'fif'),
    ('numeral', 'FOUR', 'forty', ['-ty'], 'A2', ['My dad turned ____ last month.', 'The lesson lasts ____ minutes.'], 'for'),
    ('numeral', 'FOUR', 'fourteen', ['-teen'], 'A2', ['There are ____ girls in our class.', 'My brother is ____ years old.']),
    ('numeral', 'FOUR', 'fourth', ['-th'], 'A2', ['April is the ____ month of the year.', 'Ann finished ____ in the race.']),
    ('numeral', 'NINE', 'ninth', ['-th'], 'A2', ['My sister is in the ____ grade.', 'The office is on the ____ floor.'], 'nin'),
    ('numeral', 'NINE', 'ninety', ['-ty'], 'A2', ['My great-grandmother is ____ years old.', 'The film lasts ____ minutes.']),
    ('numeral', 'NINE', 'nineteen', ['-teen'], 'A2', ['The school was built in ____ sixty-five.', 'My cousin is ____ and studies at university.']),
    ('numeral', 'EIGHT', 'eighteen', ['-teen'], 'A2', ['You can vote when you are ____.', 'Our team scored ____ points.'], 'eigh'),
    ('numeral', 'EIGHT', 'eighty', ['-ty'], 'A2', ['The tower is ____ metres high.', 'Grandpa is ____, but he still drives.'], 'eigh'),
    ('numeral', 'EIGHT', 'eighth', ['-th'], 'A2', ['Today is the ____ of March.', 'We live on the ____ floor.'], 'eigh'),
    ('numeral', 'THREE', 'thirteen', ['-teen'], 'A2', ['My little brother is ____ next week.', 'There were ____ candles on the cake.'], 'thir'),
    ('numeral', 'THREE', 'thirty', ['-ty'], 'A2', ['The train leaves at ____ minutes past eight.', 'There are ____ days in June.'], 'thir'),
    ('numeral', 'TWELVE', 'twelfth', ['-th'], 'A2', ['Our flat is on the ____ floor.', 'December is the ____ month of the year.'], 'twelf'),
    ('numeral', 'TWENTY', 'twentieth', ['-th'], 'A2', ['The ____ century was full of great inventions.', 'My birthday is on the ____ of June.']),
    ('numeral', 'SIX', 'sixteen', ['-teen'], 'A2', ['My sister got her first phone at ____.', 'The team has ____ players.']),
    ('numeral', 'SIX', 'sixty', ['-ty'], 'A2', ['There are ____ seconds in a minute.', 'The bus can carry ____ passengers.']),
    ('numeral', 'SEVEN', 'seventh', ['-th'], 'A2', ['July is the ____ month of the year.', 'We are in the ____ form.']),
    ('numeral', 'SEVEN', 'seventeen', ['-teen'], 'A2', ['My cousin is ____ and finishes school this year.', 'The bus stops ____ times on the way.']),
    ('numeral', 'HUNDRED', 'hundredth', ['-th'], 'B1', ['The school celebrated its ____ birthday last year.', 'This is the ____ time I am telling you this!']),
    ('numeral', 'TWO', 'twenty', ['-ty'], 'A2', ['My brother is ____ and studies medicine.', 'We waited ____ minutes for the bus.'], 'twen'),
    # --- inter-, pre-, post-
    ('inter-pre-post', 'NATIONAL', 'international', ['inter-'], 'B1', ['Over forty countries took part in the ____ festival.', 'English is the language of ____ business.']),
    ('inter-pre-post', 'ACT', 'interact', ['inter-'], 'B2', ['Children learn to ____ with each other at kindergarten.', 'The robot can ____ with people.']),
    ('inter-pre-post', 'NET', 'internet', ['inter-'], 'A2', ['Our village finally got fast ____ last year.', 'I found the recipe on the ____.']),
    ('inter-pre-post', 'VIEW', 'interview', ['inter-'], 'B1', ['The journalist had an ____ with the champion.', 'Tom has a job ____ on Monday.']),
    ('inter-pre-post', 'WAR', 'postwar', ['post-'], 'B2', ['The novel describes ____ life in a small town.', 'Many ____ houses in our street were built in 1950.']),
    ('inter-pre-post', 'WAR', 'prewar', ['pre-'], 'B2', ['The museum shows photos of ____ Moscow.', 'Grandma still has some ____ furniture.']),
    ('inter-pre-post', 'HISTORIC', 'prehistoric', ['pre-'], 'B2', ['Scientists found the bones of a ____ animal.', 'The cave has ____ paintings of deer.']),
    ('inter-pre-post', 'SCHOOL', 'preschool', ['pre-'], 'B1', ['My little sister goes to a ____ group three times a week.', 'The ____ children sang a song at the concert.']),
    ('inter-pre-post', 'PAID', 'prepaid', ['pre-'], 'B2', ['The tickets are ____, so we don\'t need cash.', 'You can buy a ____ card for the bus.']),
    ('inter-pre-post', 'GRADUATE', 'postgraduate', ['post-'], 'B2', ['My cousin is doing a ____ course in chemistry.', 'The university offers ____ programmes in law.']),
]

WF_ENTRIES = []
for _t in _E:
    fam, b, a, aff, lvl, ss = _t[:6]
    stem = _t[6] if len(_t) > 6 else None
    WF_ENTRIES.append({'fam': fam, 'b': b, 'a': a, 'aff': aff, 'lvl': lvl, 's': ss, 'stem': stem})
