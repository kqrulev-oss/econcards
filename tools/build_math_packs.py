#!/usr/bin/env python3
"""Наборы по математике из каталога прототипов (tools/research/proto_*.py, gen_math.py).

Три набора библиотеки:
  ege-math       ЕГЭ профиль в нумерации КИМ 2027 (20 заданий); id тем m-task-N сохранены —
                 на них завязан прогресс учеников. Теория прежнего набора перенесена по
                 таблице OLD2NEW (в 2026 году №6 был №7 и т. д.)
  ege-math-base  ЕГЭ база (21 задание), темы b-task-N
  oge-math       ОГЭ (25 заданий), темы o-task-N

Карточки делает генератор прототипа: ответ выбран кодом и пересчитан независимой проверкой
(run_proto из gen_math.py). Рецепты llm (без генератора) в набор не попадают.
Порядок прототипов в теме важен: бесплатная часть библиотеки — первые два (trimLibrary).

Запуск — через tools/build_packs.py; отдельно: python3 tools/build_math_packs.py (печатает сводку).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools' / 'research'))

from gen_math import load_protos, run_proto  # noqa: E402
import math_meta  # noqa: E402

SEED = 'pack-2026-09'
PER_PROTO = 8          # карточек на прототип без рисунка
PER_PROTO_SVG = 5      # с рисунком: SVG тяжелее

# ЕГЭ профиль: номер 2026 → номер 2027 (новые №6, 13, 17; прежние №12 и №16 ушли)
OLD2NEW = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 7, 7: 8, 8: 9, 9: 10, 10: 11, 11: 12, 13: 14, 14: 15, 15: 16, 17: 18, 18: 19, 19: 20}
PROF_2027 = {**{OLD2NEW[t['n']]: t['title'] for t in math_meta.EGE_PROF if t['n'] in OLD2NEW},
             6: 'Случайная величина', 13: 'Текстовая или финансовая задача', 17: 'Моделирование реальной ситуации'}
BASE = {t['n']: t['title'] for t in math_meta.EGE_BASE}
OGE = {**{n: 'Практико-ориентированная задача' for n in range(1, 6)},
       **{t['n']: t['title'] for t in math_meta.OGE if isinstance(t['n'], int)}}

PACKS = {
    'ege-prof': dict(id='ege-math', prefix='m-task', titles=PROF_2027, section='Задания ЕГЭ',
                     title='ЕГЭ: профильная математика',
                     desc='Все 20 заданий КИМ 2027 по прототипам: от планиметрии и случайной величины до параметра и чисел',
                     color='#0E7C86'),
    'ege-base': dict(id='ege-math-base', prefix='b-task', titles=BASE, section='Задания ЕГЭ',
                     title='ЕГЭ: базовая математика',
                     desc='Все 21 задание базового уровня: арифметика, проценты, графики, планиметрия, смекалка',
                     color='#1B7F4E'),
    'oge': dict(id='oge-math', prefix='o-task', titles=OGE, section='Задания ОГЭ',
                title='ОГЭ: математика',
                desc='Все 25 заданий ОГЭ по прототипам: практические задачи, алгебра, геометрия, часть 2',
                color='#8E44AD'),
}


def esc(s):
    return str(s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def proto_page(tid, n, protos):
    """Страница теории «Прототипы задания N»: что неизменно и как считается ответ."""
    items = ''.join(f'<li><b>{esc(p["title"])}.</b> {esc(p["invariant"])} <span class="muted">Ответ: {esc(p["answer_rule"])}</span></li>'
                    for p in protos)
    kim = protos[0].get('kim') or {}
    tail = ' · '.join(x for x in (f'уровень {kim["level"]}' if kim.get('level') else '', f'{kim["points"]} балл(а)' if kim.get('points') else '',
                                 f'около {kim["minutes"]} мин' if kim.get('minutes') else '') if x)
    return {'id': f'th-protos-{tid}', 'topic': tid, 'title': f'Прототипы задания {n}', 'min': 3, 'section': 'Прототипы',
            'html': f'<p>Все задания этого номера сводятся к {len(protos)} схемам. Узнал схему — знаешь, как решать.</p><ol>{items}</ol>'
                    + (f'<p class="muted">{esc(tail)}</p>' if tail else '')}


def build(exam, protos, old=None, log=print):
    spec = PACKS[exam]
    by_n = {}
    for p in sorted(protos.values(), key=lambda p: (p['n'], p['id'])):
        if p['exam'] == exam and p['kind'] == 'param':
            by_n.setdefault(p['n'], []).append(p)
    topics, theory, cards = [], [], []
    old_theory = {}
    if old:
        for lesson in old['theory']:
            old_n = int(lesson['topic'].rsplit('-', 1)[1])
            if old_n in OLD2NEW:
                old_theory.setdefault(OLD2NEW[old_n], []).append(lesson)
    for n in sorted(spec['titles']):
        tid = f'{spec["prefix"]}-{n}'
        ps = by_n.get(n, [])
        topic = {'id': tid, 'title': f'{n}. {spec["titles"][n]}', 'section': spec['section'], 'n': n,
                 'pts': (ps[0].get('kim') or {}).get('points', 1) if ps else 1,
                 'protos': [{'id': p['id'], 'title': p['title'], 'tip': p['answer_rule']} for p in ps]}
        topics.append(topic)
        for lesson in old_theory.get(n, []):
            lesson = dict(lesson, topic=tid, title=lesson['title'].replace(f'задание {int(lesson["topic"].rsplit("-", 1)[1])}', f'задание {n}'))
            theory.append(lesson)
        if ps:
            theory.append(proto_page(tid, n, ps))
        for p in ps:
            got, info = run_proto(p, PER_PROTO_SVG if p['svg'] else PER_PROTO, None, seed=SEED, cap_tries=0)
            if info['fail']:
                raise SystemExit(f'{p["id"]}: {info["fail"]} несошедшихся ответов')
            for c in got:
                card = {'id': c['id'], 't': tid, 'p': p['id'], 'k': c['k'], 'q': c['q'], 'a': c['a']}
                for key in ('o', 'e', 'svg'):
                    if c.get(key):
                        card[key] = c[key]
                cards.append(card)
    empty = [t['id'] for t in topics if not t['protos']]
    log(f'{spec["id"]}: {len(topics)} тем, {len(cards)} карточек, теория {len(theory)}'
        + (f', без генератора: {", ".join(empty)}' if empty else ''))
    return {'id': spec['id'], 'title': spec['title'], 'subject': 'Математика', 'desc': spec['desc'], 'color': spec['color'],
            'topics': topics, 'theory': theory, 'cards': cards}


def math_packs(old_prof=None, log=print):
    protos = load_protos()
    return [build('ege-prof', protos, old_prof, log), build('ege-base', protos, None, log), build('oge', protos, None, log)]


if __name__ == '__main__':
    old = json.loads((ROOT / 'packs' / 'ege-math.json').read_text('utf-8'))
    for pack in math_packs(old):
        print(pack['id'], {c['k'] for c in pack['cards']}, 'svg:', sum(1 for c in pack['cards'] if c.get('svg')))
