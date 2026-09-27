#!/usr/bin/env python3
"""Собирает автоматическую часть data/source/geo-facts.json из кэша fetch_geo_facts.py.

Запуск: python3 tools/research/build_geo_facts.py --cache DIR

Обновляет разделы countries, ru_subjects, ru_cities, rivers, lakes, peaks; остальные разделы файла
(ручные таблицы: ru_regions, statements, sets, classes, stations …) не трогает.

Правила:
  * страна попадает в таблицу, если есть и в World Bank (как страна, не агрегат), и в Wikidata (ISO3);
  * для каждого показателя берётся последний год с данными в 2015–2024, год хранится рядом (`year`);
  * численность субъектов и городов — последняя дата в Wikidata (там это оценки Росстата), год хранится;
  * города — от 100 тыс. жителей; реки ≥ 900 км, озёра ≥ 3000 км², вершины ≥ 3500 м с превышением ≥ 1500 м.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data' / 'source' / 'geo-facts.json'

# школьные названия вместо официальных из Wikidata
NAME_FIX = {
    'Королевство Нидерландов': 'Нидерланды', 'Демократическая Республика Конго': 'ДР Конго',
    'Объединённые Арабские Эмираты': 'ОАЭ', 'Багамские Острова': 'Багамы', 'Сейшельские Острова': 'Сейшелы',
    'Федеративные Штаты Микронезии': 'Микронезия', 'Республика Корея': 'Республика Корея',
    'Папуа — Новая Гвинея': 'Папуа — Новая Гвинея',
}
# у части городов в Wikidata остались исторические P131 — выбираем действующий субъект
CITY_SUBJECT = {'Грозный': 'Чечня', 'Каменск-Уральский': 'Свердловская область', 'Кемерово': 'Кемеровская область',
                'Черкесск': 'Карачаево-Черкесия'}
SKIP_ISO = {'PSE', 'XKX', 'TWN', 'VAT'}   # нет полного ряда World Bank или спорный статус — в генерацию не берём


def num(x):
    return float(x) if '.' in x or 'e' in x.lower() else int(x)


def point(s):
    m = re.match(r'Point\(([-\d.eE]+) ([-\d.eE]+)\)', s or '')
    return (round(float(m.group(2)), 2), round(float(m.group(1)), 2)) if m else None


def wd(cache, name):
    return json.loads((cache / f'wd_{name}.json').read_text('utf-8'))['results']['bindings']


def countries(cache):
    meta = json.loads((cache / 'wb_countries.json').read_text('utf-8'))[1]
    real = {c['id']: c for c in meta if c['region']['value'] != 'Aggregates'}
    wb = {}
    for f in sorted(cache.glob('wb_*.json')):
        key = f.stem[3:]
        if key == 'countries':
            continue
        page = json.loads(f.read_text('utf-8'))
        for r in page[1] or []:
            iso = r['countryiso3code']
            if iso not in real or r['value'] is None:
                continue
            y = int(r['date'])
            cur = wb.setdefault(iso, {}).get(key)
            if cur is None or y > cur[1]:
                wb[iso][key] = (r['value'], y)
    rows = {}
    for b in wd(cache, 'countries'):
        iso = b['iso']['value']
        if iso in SKIP_ISO or iso not in wb or 'ru' not in b:
            continue
        r = rows.setdefault(iso, {'name': NAME_FIX.get(b['ru']['value'], b['ru']['value']), 'capital': set(),
                                  'continent': set(), 'gov': set(), 'landlocked': b['landlocked']['value'] == 'true'})
        for k, f in (('capital', 'capRu'), ('continent', 'contRu'), ('gov', 'govRu')):
            if f in b:
                r[k].add(b[f]['value'])
    caps = {}
    if (cache / 'wd_capitals.json').exists():
        for b in wd(cache, 'capitals'):
            caps.setdefault(b['iso']['value'], {})[b['capRu']['value']] = point(b['coord']['value'])
    out = {}
    for iso, r in sorted(rows.items(), key=lambda kv: kv[1]['name']):
        d = {'name': r['name'], 'capital': sorted(r['capital']),
             'capital_coords': {k: list(v) for k, v in sorted(caps.get(iso, {}).items()) if v}, 'continent': sorted(r['continent']),
             'gov_wd': sorted(r['gov']), 'landlocked': r['landlocked'], 'wb': {}}
        for k, (v, y) in sorted(wb[iso].items()):
            d['wb'][k] = [round(v, 3) if isinstance(v, float) else v, y]
        out[iso] = d
    return out


def latest(rows, key_val='pop', key_date='popDate'):
    best = {}
    for b in rows:
        k = b.get('_key')
        if key_val not in b:
            continue
        date = b.get(key_date, {}).get('value', '0000')
        if k not in best or date > best[k][1]:
            best[k] = (num(b[key_val]['value']), date)
    return best


def subjects(cache):
    rows = wd(cache, 'regions')
    for b in rows:
        b['_key'] = b['ru']['value']
    pop = latest(rows)
    out = {}
    for b in rows:
        name = b['ru']['value']
        d = out.setdefault(name, {'wd': b['s']['value'].rsplit('/', 1)[1]})
        if 'area' in b:
            d['area'] = max(d.get('area', 0), round(num(b['area']['value'])))
        if 'capRu' in b:
            d['center'] = b['capRu']['value']
        if 'coord' in b and point(b['coord']['value']):
            d['center_lat'], d['center_lon'] = point(b['coord']['value'])
        if name in pop:
            d['pop'], d['pop_date'] = pop[name][0], pop[name][1][:10]
    for d in out.values():
        if d.get('pop') and d.get('area'):
            d['density'] = round(d['pop'] / d['area'], 2)
    return dict(sorted(out.items()))


def cities(cache):
    rows = wd(cache, 'cities')
    for b in rows:
        b['_key'] = b['c']['value']
    pop = latest(rows)
    out = {}
    for b in rows:
        k = b['c']['value']
        if pop.get(k, (0,))[0] < 100000:
            continue
        name = b['ru']['value']
        d = out.setdefault(k, {'name': name, 'subjects': set()})
        d['subjects'].add(b['subjRu']['value'])
        d['lat'], d['lon'] = point(b['coord']['value'])
        d['pop'], d['pop_date'] = pop[k][0], pop[k][1][:10]
    res = {}
    for k, d in out.items():
        subj = sorted(d['subjects'])
        if d['name'] in CITY_SUBJECT:
            subj = [CITY_SUBJECT[d['name']]]
        elif len(subj) == 2 and 'Тюменская область' in subj:   # города автономных округов
            subj = [x for x in subj if x != 'Тюменская область']
        name = d['name'] if d['name'] not in res else f"{d['name']} ({subj[0]})"
        res[name] = {'subject': subj[0] if len(subj) == 1 else subj, 'lat': d['lat'], 'lon': d['lon'],
                     'pop': d['pop'], 'pop_date': d['pop_date'], 'wd': k.rsplit('/', 1)[1]}
    return dict(sorted(res.items()))


def objects(cache, name, key, val, extra, scale=1):
    out = {}
    for b in wd(cache, name):
        n = b['ru']['value']
        if re.match(r'^Q\d+$', n):
            continue
        v = round(float(b[val]['value']) / scale)   # значения нормализованы Wikidata в СИ (м, м²)
        d = out.setdefault(n, {key: v})
        d[key] = max(d[key], v)
        c = point(b.get('coord', {}).get('value'))
        if c:
            d['lat'], d['lon'] = c
        for f, g in extra:
            if g in b:
                d.setdefault(f, set()).add(b[g]['value'])
    for d in out.values():
        for f, _ in extra:
            if f in d:
                d[f] = sorted(d[f])
    return dict(sorted(out.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', required=True)
    a = ap.parse_args()
    cache = Path(a.cache)
    data = json.loads(OUT.read_text('utf-8')) if OUT.exists() else {}
    fetched = (cache / 'fetched.txt').read_text().strip()
    data.setdefault('meta', {})['auto'] = {
        'fetched': fetched,
        'sources': {
            'World Bank WDI': 'https://data.worldbank.org — CC BY 4.0 (© World Bank). Показатель и год — в поле wb.',
            'Wikidata': 'https://www.wikidata.org — CC0. Названия, столицы, части света, субъекты РФ, города, реки, озёра, вершины.',
        },
        'script': 'tools/research/fetch_geo_facts.py + tools/research/build_geo_facts.py',
    }
    data['countries'] = countries(cache)
    data['ru_subjects'] = subjects(cache)
    data['ru_cities'] = cities(cache)
    data['rivers'] = objects(cache, 'rivers', 'len_km', 'len', [('mouth', 'mouthRu')], 1000)
    data['lakes'] = objects(cache, 'lakes', 'area_km2', 'area', [], 1e6)
    data['peaks'] = objects(cache, 'peaks', 'elev_m', 'elev', [('country', 'countryRu')])
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for k in ('countries', 'ru_subjects', 'ru_cities', 'rivers', 'lakes', 'peaks'):
        print(k, len(data[k]))


if __name__ == '__main__':
    main()
