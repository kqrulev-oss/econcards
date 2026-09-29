#!/usr/bin/env python3
"""Карточки ЕГЭ по русскому в формате КИМ для набора ege-rus (tools/build_packs.py, rus_pack).

Два источника:
  * словарный генератор tools/research/gen_rus.py — ударение, паронимы, формы слов,
    орфография 9–12, Н/НН; ответ каждой карточки пересчитан verify() независимо от генератора;
  * data/research/rus-llm-samples.json — аналоги по рецептам llm (задания 1–3, 6, 8, 13–26),
    прошедшие проверку правилом и слепое решение экспертом (expert == pass).

Формат ответа как в бланке: набор цифр (many с вариантами, seq для позиций и соответствий)
или слово (word, варианты через «|»). Прототипы с пометкой legacy (формат КИМ до 2024) не берём.
Эти прототипы идут в теме первыми: бесплатная часть библиотеки — первые два прототипа темы.

Отдельно: python3 tools/build_rus_pack.py — сводка по видам карточек.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools' / 'research'))

SEED = 'pack-2026-09'
PER_PROTO = 20
KEEP = ('id', 't', 'p', 'k', 'q', 'o', 'a', 'e', 'any', 'digits')


def catalog():
    d = json.loads((ROOT / 'data/source/rus-prototypes.json').read_text('utf-8'))
    return {p['id']: p for p in d['prototypes'] if p['exam'] == 'ЕГЭ'}


def to_pack(c, n, pid):
    """Карточка генератора или аналога ИИ → карточка набора (t = тема, текст задания в q)."""
    q = c['q'] + ('\n\n' + c['t'] if c.get('t') else '')
    card = {'id': c['id'], 't': f'task-{n}', 'p': pid, 'k': c['k'], 'q': q, 'a': c['a']}
    for key in ('o', 'e', 'any'):
        if c.get(key):
            card[key] = c[key]
    if c['k'] == 'match' and isinstance(c['a'], str) and c['a'].isdigit():
        # Соответствие «буквы → цифры»: последовательность цифр, полбалла за одну ошибку
        card['k'] = 'seq'
        card['digits'] = len(c.get('o') or []) or 9
    elif c['k'] == 'many' and c.get('o') and all(o['t'] == o['id'] and o['id'].isdigit() and len(o['id']) == 1 for o in c['o']):
        # Варианты — только номера позиций (Н/НН): ответ цифрами, порядок не важен
        card.update(k='seq', a=''.join(sorted(c['a'])), any=True, digits=len(c['o']))
        del card['o']
    elif c['k'] == 'many' and 'o' not in c:
        nums = [int(x) for x in re.findall(r'\((\d+)\)', c.get('t', ''))]
        if all(len(a) == 1 for a in c['a']) and nums and max(nums) <= 9:
            # Позиции в тексте пронумерованы (1)…(9): ответ — цифры без порядка
            card.update(k='seq', a=''.join(sorted(c['a'])), any=True, digits=max(nums))
        else:
            # Номера предложений двузначные (ЕГЭ 26): варианты — диапазон из формулировки
            m = re.search(r'предложени[йя] (\d+)\s*[–-]\s*(\d+)', c['q'])
            lo, hi = (int(m.group(1)), int(m.group(2))) if m else (min(map(int, c['a'])), max(map(int, c['a'])))
            card['o'] = [{'id': str(i), 't': str(i)} for i in range(lo, hi + 1)]
    return {k: v for k, v in card.items() if k in KEEP}


def dict_cards(cat, log):
    import gen_rus as g
    out = {}
    for pid in g.GEN:
        p = cat.get(pid)
        if not p or p.get('legacy'):
            continue
        cards = g.generate(pid, PER_PROTO, seed=SEED)
        for c in cards:
            err = g.verify(c)
            if err:
                raise SystemExit(f'{pid}: {err}')
        out[pid] = [to_pack(c, p['n'], pid) for c in cards]
    if g.DROPPED:
        log(f'  словарь: отброшено записей {len(g.DROPPED)}')
    return out


def llm_cards(cat):
    out = {}
    d = json.loads((ROOT / 'data/research/rus-llm-samples.json').read_text('utf-8'))
    for c in d['cards']:
        p = cat.get(c['proto'])
        if not p or c['expert'] != 'pass' or p.get('legacy'):
            continue
        out.setdefault(c['proto'], []).append(to_pack(dict(c, id='rus-llm-' + c['id']), p['n'], c['proto']))
    return out


def exam_cards(log=print):
    """→ (протипы по номеру задания [{id,title,tip}], карточки). Порядок прототипов — как в каталоге."""
    cat = catalog()
    by_pid = dict_cards(cat, log)
    for pid, cs in llm_cards(cat).items():
        by_pid.setdefault(pid, []).extend(cs)
    protos, cards = {}, []
    for pid in cat:  # порядок каталога
        if pid not in by_pid:
            continue
        p = cat[pid]
        protos.setdefault(p['n'], []).append({'id': pid, 'title': p['title'], 'tip': p['answer_rule']})
        cards.extend(by_pid[pid])
    log(f'  формат КИМ: {len(cards)} карточек, {sum(map(len, protos.values()))} прототипов в {len(protos)} заданиях')
    return protos, cards


if __name__ == '__main__':
    protos, cards = exam_cards()
    from collections import Counter
    print(Counter(c['k'] for c in cards))
    print({n: [p['id'] for p in ps] for n, ps in sorted(protos.items())})
    print(Counter(c['t'] for c in cards))
