"""Обществознание и история: каталог прототипов, генератор аналогов, самопроверка.

    python3 tools/research/gen_social.py --protos [--n 50] [--cap 300] [--subject hist|soc] [--proto PREFIX]
    python3 tools/research/gen_social.py --protos --export           # data/source/hist-prototypes.json, soc-prototypes.json
    python3 tools/research/gen_social.py --protos --samples 3 --seed 7 --out FILE   # аналоги для экзаменационной проверки
    python3 tools/research/gen_social.py --protos --fidelity          # вердикты data/research/social-fidelity.json → каталоги

Прототипы и генераторы — в proto_hist.py (база событий) и proto_soc.py (словари, Конституция).
Самопроверка: до --n разных карточек на прототип, ёмкость — число разных условий за --cap попыток; ответ каждой
карточки пересчитан независимой функцией verify; дубли условий внутри прототипа и между прототипами не допускаются.
Код сайта не трогается.
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import proto_hist  # noqa: E402
import proto_soc  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CATALOGS = {'hist': ROOT / 'data/source/hist-prototypes.json', 'soc': ROOT / 'data/source/soc-prototypes.json'}
FIDELITY = ROOT / 'data/research/social-fidelity.json'

ABOUT = {
    'hist': ('Каталог прототипов заданий ЕГЭ по истории (нумерация проекта КИМ 2027: 22 задания, новое 15 — источник по всеобщей '
             'истории; n2026 — номер 2026 года, где отличается) и ОГЭ (проект 2027: 23 задания, убраны «причины и следствия»). '
             'На прототип: что неизменно, что меняется, правило ответа, типичные ошибки, паспорт КИМ, генератор или рецепт, наш пример. '
             'Факты — только из data/research/history-events.json (события с checked=true) и своих словарей терминов и памятников. '
             'Тексты ФИПИ и коммерческих банков не включены; kes — тема кодификатора словами.'),
    'soc': ('Каталог прототипов заданий ЕГЭ по обществознанию (25 заданий, в 2027 без изменений) и ОГЭ (проект 2027: 20 заданий; '
            'n2026 — номер 2026 года). На прототип: что неизменно, что меняется, правило ответа, типичные ошибки, паспорт КИМ, '
            'генератор или рецепт, наш пример. Опоры: словарь понятий, Конституция РФ (статьи указаны), кодексы (возрасты и сроки). '
            'Тексты ФИПИ и коммерческих банков не включены; kes — тема кодификатора словами.'),
}


def all_protos(subject=None):
    out = []
    if subject in (None, 'hist'):
        out += proto_hist.PROTOS
    if subject in (None, 'soc'):
        out += proto_soc.PROTOS
    return out


def selfcheck(p, n, cap, seed):
    """Возвращает (карточки, число несошедшихся, ёмкость)."""
    rng = random.Random(f'{seed}:{p["id"]}')
    cards, seen, bad = [], set(), 0
    for _ in range(cap):
        c = p['_gen'](rng)
        if not c:
            continue
        c['q'] = re.sub(r'\.\.(?!\.)', '.', c['q'])  # «1760-е гг..» → одна точка
        if c['q'] in seen:
            continue
        seen.add(c['q'])
        v = p['_ver'](c)
        if v != c['a']:
            bad += 1
            c['_mismatch'] = v
        if len(cards) < n:
            c = dict(c)
            c['id'] = f'{p["id"]}-{len(cards) + 1:03d}'
            c['p'] = p['id']
            cards.append(c)
    return cards, bad, len(seen)


def run(args):
    protos = [p for p in all_protos(args.subject) if not args.proto or p['id'].startswith(args.proto)]
    rows, all_cards = [], []
    for p in protos:
        row = {'id': p['id'], 'exam': p['exam'], 'n': p['n'], 'kind': p['gen']['kind']}
        if p['_gen'] is None:
            row.update(cards=None, bad=None, capacity=None)
            rows.append(row)
            continue
        cards, bad, capacity = selfcheck(p, args.n, args.cap, args.seed)
        row.update(cards=len(cards), bad=bad, capacity=capacity, capped=capacity >= args.cap)
        rows.append(row)
        all_cards += cards
        if bad:
            for c in cards:
                if '_mismatch' in c:
                    print(f'MISMATCH {p["id"]}: a={c["a"]} verify={c["_mismatch"]} :: {c["q"][:160]}')
    # дубли между прототипами
    by_q, by_id = {}, {}
    cross = 0
    for c in all_cards:
        if c['q'] in by_q and by_q[c['q']] != c['p']:
            cross += 1
        by_q.setdefault(c['q'], c['p'])
        by_id[c['id']] = by_id.get(c['id'], 0) + 1
    dup_ids = sum(1 for v in by_id.values() if v > 1)
    print(f'{"прототип":34} {"экз":3} {"№":>2} {"вид":5} {"карт":>4} {"ошиб":>4} {"ёмк":>5}')
    for r in rows:
        if r['cards'] is None:
            print(f'{r["id"]:34} {r["exam"]:3} {r["n"]:>2} {r["kind"]:5} {"—":>4} {"—":>4} {"—":>5}')
        else:
            print(f'{r["id"]:34} {r["exam"]:3} {r["n"]:>2} {r["kind"]:5} {r["cards"]:>4} {r["bad"]:>4} {str(r["capacity"]) + ("+" if r["capped"] else ""):>5}')
    gen_rows = [r for r in rows if r['cards'] is not None]
    print(f'\nпрототипов {len(rows)}, с генератором {len(gen_rows)}, карточек {sum(r["cards"] for r in gen_rows)}, '
          f'несошедшихся {sum(r["bad"] for r in gen_rows)}, дублей между прототипами {cross}, повторов id {dup_ids}, '
          f'суммарная ёмкость ≥ {sum(r["capacity"] for r in gen_rows)}')
    return protos, rows, all_cards


def export(protos, rows, cards, args):
    fid = json.loads(FIDELITY.read_text('utf-8')) if FIDELITY.exists() else {}
    by_row = {r['id']: r for r in rows}
    first = {}
    for c in cards:
        first.setdefault(c['p'], c)
    for subj, path in CATALOGS.items():
        items = []
        for p in protos:
            if not p['id'].startswith(subj):
                continue
            r = by_row[p['id']]
            ex = first.get(p['id'])
            old = None
            if path.exists():
                old = {x['id']: x for x in json.loads(path.read_text('utf-8'))['prototypes']}.get(p['id'])
            entry = {k: v for k, v in p.items() if not k.startswith('_')}
            entry['capacity'] = r['capacity']
            entry['capacity_note'] = (f'{r["capacity"]}+ (упёрлось в предел попыток)' if r.get('capped') else
                                      (f'{r["capacity"]} разных условий за {args.cap} попыток' if r['capacity'] is not None else 'генератора нет'))
            entry['selfcheck'] = {'cards': r['cards'], 'mismatched': r['bad']} if r['cards'] is not None else None
            entry['fidelity'] = fid.get(p['id']) or (old or {}).get('fidelity') or {'status': None, 'checked': 0, 'notes': '', 'fixed': ''}
            entry['example'] = {'k': ex['k'], 'q': ex['q'], 'a': ex['a'], 'e': ex['e']} if ex else None
            items.append(entry)
        kinds, fids = {}, {}
        for e in items:
            kinds[e['gen']['kind']] = kinds.get(e['gen']['kind'], 0) + 1
            s = e['fidelity'].get('status')
            if s:
                fids[s] = fids.get(s, 0) + 1
        meta = {
            'about': ABOUT[subj], 'built_by': 'python3 tools/research/gen_social.py --protos --export',
            'sources': ['демоверсии и спецификации ФИПИ 2027 (структура заданий, уровни, баллы)',
                        'data/research/history-events.json' if subj == 'hist' else 'Конституция РФ (pravo.gov.ru), ГК, СК, ТК, УК, КоАП РФ'],
            'counts': {'total': len(items), 'ЕГЭ': sum(1 for e in items if e['exam'] == 'ЕГЭ'), 'ОГЭ': sum(1 for e in items if e['exam'] == 'ОГЭ'),
                       'with_generator': sum(1 for e in items if e['selfcheck']), 'kinds': kinds, 'fidelity': fids},
            'selfcheck': {'cards_per_proto': args.n, 'cap': args.cap, 'seed': args.seed,
                          'cards': sum(e['selfcheck']['cards'] for e in items if e['selfcheck']),
                          'mismatched': sum(e['selfcheck']['mismatched'] for e in items if e['selfcheck'])},
        }
        path.write_text(json.dumps({'meta': meta, 'prototypes': items}, ensure_ascii=False, indent=1) + '\n', 'utf-8')
        print(f'записан {path.relative_to(ROOT)}: {len(items)} прототипов')


def samples(protos, args):
    rng = random.Random(args.seed)
    out = []
    for p in protos:
        if p['_gen'] is None:
            continue
        cards, _, _ = selfcheck(p, args.n, args.cap, args.seed)
        for c in rng.sample(cards, min(args.samples, len(cards))):
            out.append({'p': p['id'], 'exam': p['exam'], 'n': p['n'], 'k': c['k'], 'q': c['q'], 'a': c['a']})
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), 'utf-8')
    print(f'{len(out)} аналогов → {args.out}')


def apply_fidelity():
    fid = json.loads(FIDELITY.read_text('utf-8'))
    for path in CATALOGS.values():
        data = json.loads(path.read_text('utf-8'))
        cnt = {}
        for p in data['prototypes']:
            if p['id'] in fid:
                p['fidelity'] = fid[p['id']]
            s = p['fidelity'].get('status')
            if s:
                cnt[s] = cnt.get(s, 0) + 1
        data['meta']['counts']['fidelity'] = cnt
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', 'utf-8')
        print(f'{path.name}: {cnt}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--protos', action='store_true', help='самопроверка каталога прототипов')
    ap.add_argument('--n', type=int, default=50, help='карточек на прототип')
    ap.add_argument('--cap', type=int, default=300, help='попыток для оценки ёмкости')
    ap.add_argument('--subject', choices=['hist', 'soc'])
    ap.add_argument('--proto', help='только прототипы с этим префиксом id, например hist-ege-04')
    ap.add_argument('--seed', type=int, default=2026)
    ap.add_argument('--export', action='store_true', help='записать каталоги data/source/*-prototypes.json')
    ap.add_argument('--samples', type=int, default=0, help='k случайных аналогов на прототип в --out')
    ap.add_argument('--out')
    ap.add_argument('--fidelity', action='store_true', help='записать вердикты data/research/social-fidelity.json в каталоги')
    args = ap.parse_args()
    if args.fidelity:
        apply_fidelity()
        return
    if args.samples:
        samples([p for p in all_protos(args.subject) if not args.proto or p['id'].startswith(args.proto)], args)
        return
    if not args.protos:
        ap.print_help()
        return
    protos, rows, cards = run(args)
    if args.export:
        export(protos, rows, cards, args)


if __name__ == '__main__':
    main()
