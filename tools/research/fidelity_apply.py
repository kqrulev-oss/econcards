"""Записывает итог «экзаменационной проверки» в поле fidelity каталогов прототипов.

    python3 tools/research/fidelity_apply.py DIR2 [DIR3 …]   # папки с verdict*.json экспертов по раундам (2, 3, …)

Вердикт эксперта (по 5 случайным аналогам) лежит в fidelity.expert; итог — fidelity.status (pass / fail) и
fidelity.reason. Правила итога:
- генератор есть, эксперт — pass, автоматическая сверка формата с КИМ (fidelity.auto) без замечаний → pass;
- в КИМ развёрнутый ответ, а генератор тренирует только шаг → fail (аналог не равен заданию КИМ);
- llm / bank / none — аналогов генератора нет → fail с причиной.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKS = ('format', 'structure', 'style', 'level', 'facts', 'trap', 'codifier', 'scoring')


def load_verdicts(folders):
    """Последний раунд, в котором прототип проверялся, заменяет предыдущие."""
    out = {}
    for rnd, folder in enumerate(folders, start=2):
        for f in sorted(Path(folder).glob('verdict*.json')):
            for v in json.loads(f.read_text('utf-8')):
                out[v['id']] = dict(v, round=rnd)
    return out


def expert_of(v):
    checks = {k: (v['checks'].get(k) or ['?'])[0] for k in CHECKS}
    return {
        'round': v.get('round', 2), 'checked': v.get('checked', 5), 'passed_cards': v.get('passed_cards'),
        'checks': checks, 'indistinguishable': v.get('indistinguishable'), 'verdict': v.get('verdict'),
        'reason': v.get('reason') or '', 'render': v.get('render') or '',
    }


def status_of(p, ex):
    g = p['gen']
    if isinstance(g, dict):
        why = {'llm': 'генератора нет: рецепт для ИИ (аналоги пишет ИИ по таблице фактов, проверка — выборочно экспертом)',
               'bank': 'генератора нет: нужен рисунок/карта (' + g.get('need', '') + ')',
               'none': 'не покрыто: ' + g.get('why', '')}[g['kind']]
        return 'fail', why
    kim = (p.get('fidelity') or {}).get('kim') or {}
    if kim.get('answer') == 'open' or kim.get('answer') == ['open']:
        return 'fail', 'в КИМ развёрнутый ответ; генератор тренирует шаг задания (расчёт/выбор), а не всё задание'
    if ex is None:
        return 'fail', 'экспертная проверка не проведена'
    if ex['verdict'] != 'pass':
        return 'fail', ex['reason'] or 'эксперт: не прошло'
    auto = (p.get('fidelity') or {}).get('auto') or {}
    if auto.get('format') == 'fail' or auto.get('structure') == 'fail':
        return 'fail', 'автосверка с КИМ: ' + '; '.join(auto.get('notes', []))
    return 'pass', ''


def main():
    V = load_verdicts(sys.argv[1:])
    for subj in ('bio', 'geo'):
        path = ROOT / 'data' / 'source' / f'{subj}-prototypes.json'
        data = json.loads(path.read_text('utf-8'))
        for p in data['prototypes']:
            fid = p.setdefault('fidelity', {})
            v = V.get(p['id'])
            ex = expert_of(v) if v and isinstance(p['gen'], str) else None
            if ex:
                fid['expert'] = ex
            else:
                fid.pop('expert', None)
            fid['status'], fid['reason'] = status_of(p, ex)
        data['meta']['fidelity'] = (
            'Экзаменационная проверка: kim — эталон КИМ 2027 для номера (уровень, баллы, время, формат ответа, устройство, '
            'кодификатор); auto — автоматическая сверка формата и числа элементов аналогов с эталоном; expert — второй проход: '
            'эксперт ЕГЭ/ОГЭ оценивает 5 случайных аналогов по чек-листу (format, structure, style, level, facts, trap, codifier, '
            'scoring) и отвечает, отличим ли аналог от задания открытого банка ФИПИ; status/reason — итог (pass — аналоги '
            'неотличимы от экзаменационных, fail — с причиной).')
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        st = [p['fidelity']['status'] for p in data['prototypes']]
        print(subj, 'pass', st.count('pass'), 'fail', st.count('fail'))


if __name__ == '__main__':
    main()
