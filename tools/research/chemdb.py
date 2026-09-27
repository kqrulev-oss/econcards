#!/usr/bin/env python3
"""База веществ и реакций для химических прототипов.

Данные — в модулях tools/research/chemdb_*.py (у каждого исполнителя свой):
  SUBSTANCES = [dict(f='NaOH', name='гидроксид натрия', cls='основание', sub='щёлочь', trivial=['едкий натр'],
                     wd='Q102769', pubchem=14798, state='тв', color='белый', sol='р', props=['гигроскопичен'], ...)]
  REACTIONS  = [dict(lhs=['NaOH', 'HCl'], rhs=['NaCl', 'H2O'], type=['обмена', 'нейтрализации'],
                     cond='', sign='', tags=['кислота+основание'], src='школьный факт'), ...]
Коэффициенты НЕ пишутся руками: load() уравнивает каждую реакцию balance() и перепроверяет check_balance().
В карточках формулы — как в f (ASCII: 'Ca(OH)2', 'Na[Al(OH)4]' → пишем 'Na(Al(OH)4)' или указываем view=).

  python3 tools/research/chemdb.py            # проверить базу
  python3 tools/research/chemdb.py --write    # записать data/source/chem-substances.json
"""
import glob
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from pc_core import balance, check_balance, eq_str, molar, parse_formula, pretty  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, 'data', 'source', 'chem-substances.json')

SUB_FIELDS = {'f', 'name', 'cls', 'sub', 'trivial', 'wd', 'pubchem', 'state', 'color', 'sol', 'props', 'view', 'src',
              'org', 'ion', 'hom', 'group', 'notes', 'ox', 'bond', 'lattice', 'acid_base', 'strength', 'smell', 'use'}

_cache = None


def load(strict=True):
    """Сливает все chemdb_*.py. Возвращает dict(substances={f: row}, reactions=[row + k, eq], problems=[...])."""
    global _cache
    if _cache is not None:
        return _cache
    subs, reacts, problems, seen_r = {}, [], [], {}
    for path in sorted(glob.glob(os.path.join(HERE, 'chemdb_*.py'))):
        mod = importlib.import_module(os.path.basename(path)[:-3])
        src_mod = os.path.basename(path)
        for s in getattr(mod, 'SUBSTANCES', []):
            f = s['f']
            try:
                parse_formula(f)
            except Exception as ex:  # noqa: BLE001
                problems.append(f'{src_mod}: формула {f!r}: {ex}')
                continue
            extra = set(s) - SUB_FIELDS
            if extra:
                problems.append(f'{src_mod}: {f}: неизвестные поля {sorted(extra)}')
            if f in subs:
                # второй источник дополняет, но не перетирает
                for k, v in s.items():
                    subs[f].setdefault(k, v)
                continue
            row = dict(s)
            row['_mod'] = src_mod
            subs[f] = row
        for i, r in enumerate(getattr(mod, 'REACTIONS', [])):
            lhs, rhs = list(r['lhs']), list(r['rhs'])
            key = (tuple(sorted(lhs)), tuple(sorted(rhs)), r.get('cond', ''))
            if key in seen_r:  # та же реакция из другого модуля — дополняем теги, не дублируем
                old = seen_r[key]
                for fld in ('sign', 'cond', 'src', 'note'):  # пустые поля первого модуля дополняем из второго
                    if not old.get(fld) and r.get(fld):
                        old[fld] = r[fld]
                if not old.get('type') and r.get('type'):
                    old['type'] = list(r['type'])
                for t in r.get('type', []) + r.get('tags', []):
                    if t not in old.get('type', []) + old.get('tags', []):
                        old.setdefault('tags', []).append(t)
                continue
            try:
                kl, kr = balance(lhs, rhs)
                ok = check_balance(lhs, rhs, kl, kr)
            except Exception as ex:  # noqa: BLE001
                problems.append(f'{src_mod}: реакция {lhs}→{rhs}: {ex}')
                continue
            if not ok:
                problems.append(f'{src_mod}: не уравнено {lhs}→{rhs}')
                continue
            row = dict(r)
            row.update(k=[kl, kr], eq=eq_str(lhs, rhs, kl, kr), rid=f'{src_mod[7:-3]}-{i:04d}')
            reacts.append(row)
            seen_r[key] = row
    known = set(subs)
    for r in reacts:
        for f in r['lhs'] + r['rhs']:
            if f not in known:
                problems.append(f'{r["rid"]}: вещества {f} нет в SUBSTANCES ({r["eq"]})')
    if strict and problems:
        pass  # проблемы возвращаются, решает вызывающий
    _cache = {'substances': subs, 'reactions': reacts, 'problems': problems}
    return _cache


def reactions_of(f, db=None):
    db = db or load()
    return [r for r in db['reactions'] if f in r['lhs']]


def reacts_with(a, b, db=None):
    """Реакции, где a и b — оба реагенты."""
    db = db or load()
    return [r for r in db['reactions'] if a in r['lhs'] and b in r['lhs']]


def export(db=None):
    db = db or load()
    rows = []
    for f, s in sorted(db['substances'].items(), key=lambda kv: (kv[1].get('org', False), kv[1].get('cls', ''), kv[0])):
        row = {k: v for k, v in s.items() if not k.startswith('_')}
        row['M'] = float(molar(f)) if all(e in __import__('pc_core').AR for e in parse_formula(f)) else None
        row['reacts'] = [{'with': [x for x in r['lhs'] if x != f], 'products': r['rhs'], 'eq': r['eq'],
                          'type': r.get('type', []), 'cond': r.get('cond', ''), 'sign': r.get('sign', ''), 'rid': r['rid']}
                         for r in db['reactions'] if f in r['lhs']]
        row['formed_in'] = [r['rid'] for r in db['reactions'] if f in r['rhs']]
        rows.append(row)
    reactions = [{k: v for k, v in r.items()} for r in db['reactions']]
    meta = {
        'about': 'База веществ и реакций школьной химии для генераторов карточек (ЕГЭ/ОГЭ). Строка вещества: формула, '
                 'название, класс, с чем реагирует, продукты, признаки. Все уравнения уравнены программой (balance) '
                 'и перепроверены.',
        'sources': ['Wikidata (CC0): названия, формулы, идентификаторы wd', 'PubChem (NCBI, без ограничений): CID',
                    'школьные факты (таблица растворимости, ряд активности, типовые свойства классов) — факты, не охраняются'],
        'built_by': 'python3 tools/research/chemdb.py --write (данные — tools/research/chemdb_*.py)',
        'counts': {'substances': len(rows), 'reactions': len(reactions)},
    }
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump({'meta': meta, 'substances': rows, 'reactions': reactions}, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    return OUT, len(rows), len(reactions)


def main():
    db = load()
    print(f'веществ {len(db["substances"])}, реакций {len(db["reactions"])}, проблем {len(db["problems"])}')
    for p in db['problems'][:60]:
        print(' -', p)
    if '--write' in sys.argv:
        print('записано', *export(db))
    sys.exit(1 if db['problems'] else 0)


if __name__ == '__main__':
    main()
