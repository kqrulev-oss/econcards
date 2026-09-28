#!/usr/bin/env python3
"""Таблицы покрытия для docs/research/phys-chem-prototypes.md из выгрузки каталога прототипов.

  python3 tools/research/coverage_md.py     # печатает markdown
Читает data/source/{phys,chem}-prototypes.json (их пишет gen_phys_chem.py --protos --export).
"""
import json
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NAMES = {('phys', 'ЕГЭ'): 'ЕГЭ, физика', ('phys', 'ОГЭ'): 'ОГЭ, физика', ('chem', 'ЕГЭ'): 'ЕГЭ, химия', ('chem', 'ОГЭ'): 'ОГЭ, химия'}


def sp(x):
    return f'{x:,}'.replace(',', '\u202f')


def load(subj):
    with open(os.path.join(ROOT, 'data', 'source', f'{subj}-prototypes.json'), encoding='utf-8') as f:
        return json.load(f)['prototypes']


def main():
    grand = defaultdict(int)
    for subj in ('phys', 'chem'):
        recs = load(subj)
        for exam in ('ЕГЭ', 'ОГЭ'):
            rows = defaultdict(lambda: defaultdict(int))
            for r in recs:
                if r['exam'] != exam:
                    continue
                t = rows[r['n']]
                t['protos'] += 1
                gen = r['gen'].get('fn') is not None
                t['gen'] += gen
                t['rec'] += not gen
                t['cap'] += r['capacity'] or 0
                t['cap_min'] = min(t.get('cap_min', 10 ** 9), r['capacity'] or 0)
                st = (r.get('fidelity') or {}).get('status')
                t['pass'] += st == 'pass'
                t['fail'] += st == 'fail'
                t['steps'] += bool(r.get('example') and r['example'].get('steps'))
            print(f'\n### {NAMES[(subj, exam)]}\n')
            print('| № | прототипов | генератор | рецепт | аналогов (сумма ёмкостей) | мин. на прототип | экспертиза: прошло / проверено |')
            print('|---|---|---|---|---|---|---|')
            tot = defaultdict(int)
            for n in sorted(rows):
                t = rows[n]
                print(f"| {n} | {t['protos']} | {t['gen']} | {t['rec']} | {sp(t['cap'])} | {t['cap_min']} | "
                      f"{t['pass']} / {t['pass'] + t['fail']} |")
                for k in ('protos', 'gen', 'rec', 'cap', 'pass', 'fail'):
                    tot[k] += t[k]
                    grand[k] += t[k]
            print(f"| **итого** | **{tot['protos']}** | {tot['gen']} | {tot['rec']} | {sp(tot['cap'])} | | "
                  f"{tot['pass']} / {tot['pass'] + tot['fail']} |")
    print(f"\nВсего: прототипов {grand['protos']} (генераторов {grand['gen']}, рецептов {grand['rec']}); "
          f"аналогов (сумма ёмкостей) {sp(grand['cap'])}; экспертиза: прошло {grand['pass']} из {grand['pass'] + grand['fail']}.")


if __name__ == '__main__':
    main()
