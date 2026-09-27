#!/usr/bin/env python3
"""Таблица покрытия прототипов для docs/research/bio-geo-prototypes.md.

Запуск: python3 tools/research/protos_report.py
Читает data/source/{bio,geo}-prototypes.json (capacity и example заполняет
`gen_bio_geo.py --protos --write`) и заменяет в отчёте блоки между маркерами
<!-- coverage:start --> … <!-- coverage:end --> и <!-- gaps:start --> … <!-- gaps:end -->.

Покрыт генератором — прототип с param/dict-генератором, давший ≥ 50 разных карточек.
llm — рецепт с проверкой (ёмкость — оценка по числу входов). bank/none — не покрыт.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / 'docs' / 'research' / 'bio-geo-prototypes.md'
NAMES = {('bio', 'ЕГЭ'): 'ЕГЭ биология', ('bio', 'ОГЭ'): 'ОГЭ биология', ('geo', 'ЕГЭ'): 'ЕГЭ география', ('geo', 'ОГЭ'): 'ОГЭ география'}
MIN_OK = 50


def sp(n):
    return f'{n:,}'.replace(',', '\u00a0')


def cap(p):
    c = p.get('capacity')
    if isinstance(c, str):
        return int(c.lstrip('≥'))
    return c or 0


def status(p):
    g = p['gen']
    if isinstance(g, dict):
        return g['kind']
    return 'gen' if cap(p) >= MIN_OK else 'gen<50'


def load():
    out = {}
    for s in ('bio', 'geo'):
        out[s] = json.loads((ROOT / 'data' / 'source' / f'{s}-prototypes.json').read_text('utf-8'))['prototypes']
    return out


def coverage(data):
    lines = []
    total = defaultdict(int)
    for (subj, exam), title in NAMES.items():
        protos = [p for p in data[subj] if p['exam'] == exam]
        by = defaultdict(list)
        for p in protos:
            by[p['n']].append(p)
        lines.append(f'\n### {title}\n')
        lines.append('| № | Прототипов | Генератор (≥ 50) | llm | Не покрыто (bank/none/< 50) | Аналогов генератором | Аналогов llm (оценка) |')
        lines.append('|---|---|---|---|---|---|---|')
        agg = defaultdict(int)
        for n in sorted(by):
            ps = by[n]
            st = [status(p) for p in ps]
            g = sum(s == 'gen' for s in st)
            l_ = sum(s == 'llm' for s in st)
            no = len(ps) - g - l_
            ag = sum(cap(p) for p in ps if status(p) in ('gen', 'gen<50'))
            al = sum(cap(p) for p in ps if status(p) == 'llm')
            lines.append(f'| {n} | {len(ps)} | {g} | {l_} | {no} | {sp(ag)} | {sp(al)} |')
            for k, v in (('p', len(ps)), ('g', g), ('l', l_), ('no', no), ('ag', ag), ('al', al)):
                agg[k] += v
                total[k] += v
        lines.append(f'| **Итого** | **{agg["p"]}** | **{agg["g"]}** | **{agg["l"]}** | **{agg["no"]}** | '
                     f'**{sp(agg["ag"])}** | **{sp(agg["al"])}** |')
    head = (f'Всего прототипов: **{total["p"]}**. С генератором (≥ {MIN_OK} разных аналогов): **{total["g"]}** '
            f'({total["g"] * 100 // total["p"]} %), рецептом llm с проверкой: **{total["l"]}**, не покрыто: **{total["no"]}**. '
            f'Аналогов у генераторов: **{sp(total["ag"])}** (нижняя граница: столько разных карточек дали 3000 попыток '
            f'на прототип), у llm-рецептов — оценка **{sp(total["al"])}**.')
    return head + '\n' + '\n'.join(lines), total


def gaps(data):
    rows = []
    for (subj, exam), title in NAMES.items():
        for p in data[subj]:
            if p['exam'] != exam:
                continue
            st = status(p)
            if st in ('gen', 'llm'):
                continue
            g = p['gen']
            if isinstance(g, dict):
                why = g.get('why') or ('нужен рисунок/карта: ' + g.get('need', '') +
                                       (f'; текстовая замена — `{g["fallback"]}`' if g.get('fallback') else ''))
            else:
                why = f'генератор даёт только {cap(p)} разных карточек'
            rows.append(f'| {title} {p["n"]} | {p["title"]} | {st} | {why} |')
    return '| Задание | Прототип | Статус | Почему не покрыт |\n|---|---|---|---|\n' + '\n'.join(rows)


def put(text, name, body):
    return re.sub(rf'(<!-- {name}:start -->\n).*?(<!-- {name}:end -->)', lambda m: m.group(1) + body + '\n' + m.group(2),
                  text, flags=re.S)


def main():
    data = load()
    cov, total = coverage(data)
    doc = DOC.read_text('utf-8')
    doc = put(doc, 'coverage', cov)
    doc = put(doc, 'gaps', gaps(data))
    DOC.write_text(doc, encoding='utf-8')
    print(dict(total))


if __name__ == '__main__':
    main()
