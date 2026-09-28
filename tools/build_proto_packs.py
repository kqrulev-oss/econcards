#!/usr/bin/env python3
"""Наборы библиотеки из каталогов прототипов: физика, химия (tools/research/gen_phys_chem.py)
и русский язык (tools/research/gen_rus.py). Математика — в build_math_packs.py.

Наборы: ege-phys, oge-phys, ege-chem, oge-chem, oge-rus. Темы — номера заданий,
разделы «Часть 1» / «Часть 2», бесплатная часть — первые два прототипа темы (trimLibrary).
Карточки делает генератор прототипа: ответ пересчитан независимой проверкой (solve),
рецепты llm и bank без генератора в набор не попадают.

Запуск — через tools/build_packs.py; отдельно: python3 tools/build_proto_packs.py (сводка).
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools' / 'research'))

SEED = 'pack-2026-09'
PER_PROTO = 8


def esc(s):
    return str(s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# Короткие названия тем: одно-два слова о номере
PHYS_EGE = {1: 'Кинематика', 2: 'Динамика', 3: 'Законы сохранения', 4: 'Статика и колебания', 5: 'Механика: утверждения',
            6: 'Механика: изменения', 7: 'МКТ', 8: 'Термодинамика', 9: 'Молекулярная физика: утверждения',
            10: 'Молекулярная физика: изменения', 11: 'Электростатика и ток', 12: 'Магнетизм и индукция', 13: 'Колебания и оптика',
            14: 'Электродинамика: утверждения', 15: 'Электродинамика: изменения', 16: 'Атом и ядро', 17: 'Кванты: изменения',
            18: 'Смысл величин', 19: 'Приборы и погрешность', 20: 'Планирование опыта', 21: 'Качественная задача',
            22: 'Механика: расчёт', 23: 'Расчётная задача', 24: 'Молекулярная физика: задача', 25: 'Электродинамика: задача',
            26: 'Механика с обоснованием'}
PHYS_OGE = {1: 'Величины и единицы', 2: 'Приборы', 3: 'Явления', 4: 'Текст с пропусками', 5: 'Объяснить явление', 6: 'Механика',
            7: 'Механика: расчёт', 8: 'Тепловые явления', 9: 'Электричество', 10: 'Электричество и оптика', 11: 'Квантовые явления',
            12: 'Изменения: механика, тепло', 13: 'Изменения: электричество', 14: 'Графики и таблицы', 15: 'Приборы и погрешность',
            16: 'Анализ опыта', 17: 'Эксперимент', 18: 'Работа с текстом', 19: 'Качественная задача', 20: 'Расчётная задача',
            21: 'Задача высокого уровня', 22: 'Комбинированная задача'}
CHEM_EGE = {1: 'Строение атома', 2: 'Периодический закон', 3: 'Степень окисления', 4: 'Химическая связь', 5: 'Классы веществ',
            6: 'Мысленный эксперимент', 7: 'Вещество — реагенты', 8: 'Реагенты — продукты', 9: 'Цепочка неорганики',
            10: 'Органика: классы', 11: 'Органика: строение', 12: 'Углеводороды и спирты', 13: 'Азот, жиры, углеводы',
            14: 'Углеводороды: соответствие', 15: 'Кислородсодержащие', 16: 'Цепочка органики', 17: 'Типы реакций',
            18: 'Скорость реакции', 19: 'ОВР', 20: 'Электролиз', 21: 'Гидролиз и pH', 22: 'Равновесие', 23: 'Равновесные концентрации',
            24: 'Качественные реакции', 25: 'Химия и жизнь', 26: 'Массовая доля', 27: 'Тепловой эффект', 28: 'Расчёт по уравнению',
            29: 'ОВР: баланс', 30: 'Ионный обмен', 31: 'Неорганическая цепочка', 32: 'Органическая цепочка', 33: 'Формула вещества',
            34: 'Комбинированная задача'}
CHEM_OGE = {1: 'Элемент и вещество', 2: 'Строение атома', 3: 'Закономерности ПСХЭ', 4: 'Степень окисления', 5: 'Связь и решётка',
            6: 'Два элемента', 7: 'Классы веществ', 8: 'Свойства веществ', 9: 'Реагенты → продукты', 10: 'Вещество → реагенты',
            11: 'Типы реакций', 12: 'Признаки реакций', 13: 'Диссоциация', 14: 'Ионный обмен', 15: 'ОВР', 16: 'Безопасность',
            17: 'Качественные реакции', 18: 'Массовая доля элемента', 19: 'Практический расчёт', 20: 'ОВР: баланс',
            21: 'Цепочка превращений', 22: 'Расчёт с раствором', 23: 'Эксперимент'}
RUS_OGE = {2: 'Грамматическая основа', 3: 'Пунктуация', 4: 'Синтаксис', 5: 'Орфография: анализ', 6: 'Орфография: объяснение',
           7: 'Средства выразительности', 8: 'Формы слова', 9: 'Словосочетания', 10: 'Текст', 11: 'Лексика', 12: 'Сочинение'}

PACKS = [
    dict(id='ege-phys', subj='phys', exam='ЕГЭ', prefix='ph-task', titles=PHYS_EGE, part2=21, subject='Физика',
         title='ЕГЭ: физика', desc='Все 26 заданий по прототипам: механика, МКТ, электродинамика, кванты, расчётные задачи', color='#B23A48'),
    dict(id='oge-phys', subj='phys', exam='ОГЭ', prefix='ph-task', titles=PHYS_OGE, part2=17, subject='Физика',
         title='ОГЭ: физика', desc='Все 22 задания ОГЭ: величины и приборы, расчёты, изменения величин, задачи части 2', color='#D4652F'),
    dict(id='ege-chem', subj='chem', exam='ЕГЭ', prefix='ch-task', titles=CHEM_EGE, part2=29, subject='Химия',
         title='ЕГЭ: химия', desc='Все 34 задания по прототипам: строение, свойства веществ, реакции, расчёты', color='#2E7D32'),
    dict(id='oge-chem', subj='chem', exam='ОГЭ', prefix='ch-task', titles=CHEM_OGE, part2=20, subject='Химия',
         title='ОГЭ: химия', desc='Все 23 задания ОГЭ: атом и связь, классы веществ, реакции, расчёты', color='#4E9A51'),
]


def proto_page(tid, n, protos):
    items = ''.join(f'<li><b>{esc(p["title"])}.</b> {esc(p["invariant"])} <span class="muted">Ответ: {esc(p["answer_rule"])}</span></li>' for p in protos)
    return {'id': f'th-protos-{tid}', 'topic': tid, 'title': f'Прототипы задания {n}', 'min': 3, 'section': 'Прототипы',
            'html': f'<p>Все задания этого номера сводятся к {len(protos)} схемам. Узнал схему — знаешь, как решать.</p><ol>{items}</ol>'}


def clean(c, tid, pid):
    card = {'id': c['id'], 't': tid, 'p': pid, 'k': c['k'], 'q': c['q'], 'a': c['a']}
    if c['k'] == 'pm':
        # ЕГЭ-физика 19: значение и погрешность; в бланке пишутся слитно («1,80,1»), ученику разрешаем и «1,8±0,1»
        v, d = c['a']
        card['k'] = 'word'
        card['a'] = [v + d, f'{v}±{d}', (v + d).replace(',', '.'), f'{v}±{d}'.replace(',', '.')]
    for key in ('o', 'e', 'svg', 'tol'):
        if c.get(key):
            card[key] = c[key]
    return card


def assemble(spec, by_n, make_cards, log):
    topics, theory, cards = [], [], []
    for n in sorted(spec['titles']):
        tid = f'{spec["prefix"]}-{n}'
        ps = by_n.get(n, [])
        section = 'Задания' if spec.get('part2') is None else ('Часть 2' if n >= spec['part2'] else 'Часть 1')
        topics.append({'id': tid, 'title': f'{n}. {spec["titles"][n]}', 'section': section, 'n': n, 'pts': 1,
                       'protos': [{'id': p['id'], 'title': p['title'], 'tip': p['answer_rule']} for p in ps]})
        if ps:
            theory.append(proto_page(tid, n, ps))
        for p in ps:
            for c in make_cards(p):
                cards.append(clean(c, tid, p['id']))
    empty = [t['id'] for t in topics if not t['protos']]
    log(f'{spec["id"]}: {len(topics)} тем, {len(cards)} карточек' + (f', без генератора: {", ".join(empty)}' if empty else ''))
    return {'id': spec['id'], 'title': spec['title'], 'subject': spec['subject'], 'desc': spec['desc'], 'color': spec['color'],
            'topics': topics, 'theory': theory, 'cards': cards}


def phys_chem_packs(log=print):
    import gen_phys_chem as g
    import pc_core as pc
    if hasattr(g, 'load_protos'):
        g.load_protos()
    out = []
    for spec in PACKS:
        by_n = {}
        for m in sorted(pc.PROTOS.values(), key=lambda m: (m['n'], m['id'])):
            if m['subj'] == spec['subj'] and m['exam'] == spec['exam'] and m.get('fn'):
                by_n.setdefault(m['n'], []).append(m)

        def make(m):
            cards, _, _ = g.sample_unique(m, random.Random(f'{SEED}-{m["id"]}'), PER_PROTO)
            bad = [c for c in cards if m['solve'] is not None and not same_answer(m['solve'](c['gen']['p']), c['a'])]
            if bad:
                raise SystemExit(f'{m["id"]}: ответ не сошёлся с независимым пересчётом')
            return cards
        out.append(assemble(spec, by_n, make, log))
    return out


def same_answer(x, y):
    if isinstance(x, (list, tuple)) and isinstance(y, (list, tuple)):
        return sorted(map(str, x)) == sorted(map(str, y))
    if isinstance(x, dict) and isinstance(y, dict):
        return {str(k): str(v) for k, v in x.items()} == {str(k): str(v) for k, v in y.items()}
    return str(x).replace(',', '.').strip() == str(y).replace(',', '.').strip()


def rus_oge_pack(log=print):
    import gen_rus as g
    cat = {p['id']: p for p in json.loads((ROOT / 'data/source/rus-prototypes.json').read_text('utf-8'))['prototypes']}
    by_n = {}
    for pid in g.GEN:
        p = cat[pid]
        if p['exam'] == 'ОГЭ':
            by_n.setdefault(p['n'], []).append(p)
    spec = dict(id='oge-rus', prefix='o-task', titles={n: RUS_OGE[n] for n in RUS_OGE if n in by_n}, part2=None, subject='Русский язык',
                title='ОГЭ: русский язык', desc='Орфография, формы слова и словосочетания по прототипам ОГЭ: каждое слово сверено со словарём',
                color='#7B3FE4')

    def make(p):
        cards = g.generate(p['id'], PER_PROTO)
        for i, c in enumerate(cards, 1):
            c['id'] = f'{p["id"]}-{i}'
        return cards
    return assemble(spec, by_n, make, log)


def proto_packs(log=print):
    # oge-rus пока не выкладываем: генераторы есть только у заданий 6, 8, 9 (56 карточек)
    return phys_chem_packs(log)


if __name__ == '__main__':
    for pack in proto_packs():
        kinds = {}
        for c in pack['cards']:
            kinds[c['k']] = kinds.get(c['k'], 0) + 1
        print(' ', pack['id'], kinds)
