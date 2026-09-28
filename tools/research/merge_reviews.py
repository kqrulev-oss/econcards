#!/usr/bin/env python3
"""Сводит вердикты экзаменационной проверки в data/research/fidelity-review.json.

Экзаменационная проверка: на каждый прототип 5 случайных аналогов
(gen_phys_chem.py --review-sample), их оценивает эксперт по чек-листу:
формат ответа, стиль КИМ, уровень, масштаб, ловушка, КЭС, оценивание, «неотличимость от банка».
Вердикты эксперта — файлы <участок>-verdict.json ({"reviews": {id: {status, checked, passed, reason, ...}}}).

  FIPI_DIR=<выгрузка банка> python3 tools/research/merge_reviews.py <папка с *-verdict.json>
Тексты банка ФИПИ в вердиктах не хранятся — только id заданий банка (bank_refs).
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, 'data', 'research', 'fidelity-review.json')
KEEP = ('status', 'checked', 'passed', 'fail_points', 'reason', 'bank_refs', 'rounds')


def main(src):
    sys.path.insert(0, HERE)
    import gen_phys_chem as g
    protos = g.load_protos()
    fipi = os.environ.get('FIPI_DIR')
    if not fipi:
        raise SystemExit('нужен FIPI_DIR: по локальной выгрузке банка из причин вычищаются цитаты заданий')
    scrub = g.QuoteScrubber(fipi)
    reviews, areas = {}, {}
    for path in sorted(glob.glob(os.path.join(src, '*-verdict.json'))):
        area = os.path.basename(path)[:-len('-verdict.json')]
        data = json.load(open(path, encoding='utf-8'))
        rv = data.get('reviews', data)
        n = 0
        for pid, v in rv.items():
            if pid not in protos:
                continue  # прототип удалён после проверки
            reviews[pid] = scrub.deep({k: v[k] for k in KEEP if k in v})
            reviews[pid]['area'] = area
            n += 1
        areas[area] = n
    missing = sorted(p for p in protos if p not in reviews)
    summary = {'prototypes': len(protos), 'reviewed': len(reviews),
               'pass': sum(1 for v in reviews.values() if v.get('status') == 'pass'),
               'fail': sum(1 for v in reviews.values() if v.get('status') == 'fail'),
               'unreviewed': missing}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'meta': {'about': 'Экзаменационная проверка аналогов: 5 случайных аналогов на прототип, эксперт по чек-листу '
                                     'КИМ 2027 (формат ответа, стиль, уровень, масштаб, ловушка, КЭС, оценивание, '
                                     'неотличимость от задания открытого банка). Несколько раундов: fail → исправление → повтор.',
                            'areas': areas, 'summary': summary},
                   'reviews': dict(sorted(reviews.items()))}, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('записано', OUT, json.dumps(summary, ensure_ascii=False)[:400], '; цитат банка заменено:', scrub.n)


if __name__ == '__main__':
    main(sys.argv[1])
