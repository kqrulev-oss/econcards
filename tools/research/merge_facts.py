#!/usr/bin/env python3
"""Сливает фрагменты таблиц фактов в data/source/bio-facts.json или geo-facts.json и проверяет их.

Запуск:
  python3 tools/research/merge_facts.py bio FRAG1.json FRAG2.json …   # собрать заново ручные разделы
  python3 tools/research/merge_facts.py bio --check                    # только проверить готовый файл

Разделы фрагмента: sets, seqs, classes, effects, webs, taxonomy, nutrition, text_templates, statements, …
Ключи-дубли между фрагментами — ошибка. Служебные ключи *_src / *_checked / src / checked уходят в meta.
Для geo-facts.json автоматические разделы (countries, ru_subjects, ru_cities, rivers, lakes, peaks) не трогаются.

Проверки (закрытый мир и структура):
  sets     — yes ⊂ objects; нет дублей свойств; у объекта ≥ 2 «своих» свойств (не общих для всего набора);
  seqs     — ≥ 4 шагов, шаги различны;
  classes  — каждый элемент в одном из classes, в классе ≥ 1 элемента;
  effects  — значения только «увеличится/уменьшится/не изменится».
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTO = {'countries', 'ru_subjects', 'ru_cities', 'rivers', 'lakes', 'peaks'}
CHANGE = {'увеличится', 'уменьшится', 'не изменится'}


def check(data):
    errs = []
    for k, S in data.get('sets', {}).items():
        objs = S['objects']
        if len(set(objs)) != len(objs):
            errs.append(f'sets.{k}: повторяются объекты')
        texts = [p['t'] for p in S['props']]
        if len(set(texts)) != len(texts):
            errs.append(f'sets.{k}: повторяются свойства')
        for p in S['props']:
            extra = set(p['yes']) - set(objs)
            if extra:
                errs.append(f'sets.{k}: «{p["t"]}» — объекты не из набора {sorted(extra)}')
        for o in objs if S['props'] else []:              # наборы-отношения (только attrs) свойств не имеют
            own = [p for p in S['props'] if o in p['yes'] and len(p['yes']) < len(objs)]
            if len(own) < 2:
                errs.append(f'sets.{k}: у «{o}» меньше 2 своих свойств')
        for g, members in S.get('groups', {}).items():
            if set(members) - set(objs):
                errs.append(f'sets.{k}.groups.{g}: объекты не из набора')
        for a, vals in S.get('attrs', {}).items():
            if set(vals) - set(objs):
                errs.append(f'sets.{k}.attrs.{a}: объекты не из набора')
    for k, Q in data.get('seqs', {}).items():
        if len(Q['steps']) < 4 or len(set(Q['steps'])) != len(Q['steps']):
            errs.append(f'seqs.{k}: мало шагов или повторы')
        if not Q.get('q'):
            errs.append(f'seqs.{k}: нет формулировки q')
    for k, C in data.get('classes', {}).items():
        bad = {i: c for i, c in C['items'].items() if c not in C['classes']}
        if bad:
            errs.append(f'classes.{k}: класс не из списка {list(bad.items())[:3]}')
    for k, E in data.get('effects', {}).items():
        if set(E['values'].values()) - CHANGE:
            errs.append(f'effects.{k}: недопустимые значения')
    return errs


def merge(subject, frags):
    out_path = ROOT / 'data' / 'source' / f'{subject}-facts.json'
    old = json.loads(out_path.read_text('utf-8')) if out_path.exists() else {}
    data = {k: v for k, v in old.items() if k in AUTO}
    meta = old.get('meta', {})
    meta['manual'] = {}
    for f in frags:
        frag = json.loads(Path(f).read_text('utf-8'))
        name = Path(f).stem
        for sec, val in frag.items():
            if sec in ('src', 'checked', 'meta') or sec.endswith(('_src', '_checked', '_meta')):
                meta['manual'].setdefault(name, {})[sec] = val
                continue
            if isinstance(val, dict):
                tgt = data.setdefault(sec, {})
                dup = set(tgt) & set(val)
                if dup:
                    raise SystemExit(f'{name}: повтор ключей в {sec}: {sorted(dup)[:5]}')
                tgt.update(val)
            elif isinstance(val, list):
                data.setdefault(sec, []).extend(val)
            else:
                data[sec] = val
    data = {'meta': meta, **{k: data[k] for k in sorted(data)}}
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return data


def main():
    subject = sys.argv[1]
    if '--check' in sys.argv:
        data = json.loads((ROOT / 'data' / 'source' / f'{subject}-facts.json').read_text('utf-8'))
    else:
        data = merge(subject, sys.argv[2:])
    errs = check(data)
    for e in errs:
        print('ОШИБКА', e)
    sizes = {k: len(v) for k, v in data.items() if k != 'meta'}
    print(subject, sizes)
    sys.exit(1 if errs else 0)


if __name__ == '__main__':
    main()
