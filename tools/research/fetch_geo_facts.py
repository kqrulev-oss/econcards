#!/usr/bin/env python3
"""Выгрузка открытых географических данных для data/source/geo-facts.json.

Источники и лицензии:
  World Bank WDI API (CC BY 4.0) — население, площадь, плотность, ВВП на душу, структура ВВП и занятости,
      рождаемость, смертность, доля горожан, продолжительность жизни, возрастная структура;
  Wikidata SPARQL (CC0) — русские названия стран, столицы, части света, форма правления, выход к морю;
      субъекты РФ (население, площадь, центр), города РФ (координаты, население, субъект), реки, озёра, вершины.

Запуск:
  python3 tools/research/fetch_geo_facts.py --cache DIR   # скачать сырые ответы в DIR (не коммитим)
  python3 tools/research/build_geo_facts.py --cache DIR   # собрать data/source/geo-facts.json

Скрипт делает по одному запросу на показатель/выборку (≈ 25 запросов), с паузой; повторный запуск берёт кэш.
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = 'econcards-research/0.1 (school flashcards; github.com/kqrulev-oss/econcards)'

WB_INDICATORS = {
    'pop': 'SP.POP.TOTL',
    'area': 'AG.SRF.TOTL.K2',
    'land': 'AG.LND.TOTL.K2',
    'density': 'EN.POP.DNST',
    'gdp': 'NY.GDP.MKTP.CD',
    'gdp_pc': 'NY.GDP.PCAP.CD',
    'gdp_pc_ppp': 'NY.GDP.PCAP.PP.CD',
    'agr_gdp': 'NV.AGR.TOTL.ZS',
    'ind_gdp': 'NV.IND.TOTL.ZS',
    'srv_gdp': 'NV.SRV.TOTL.ZS',
    'agr_emp': 'SL.AGR.EMPL.ZS',
    'ind_emp': 'SL.IND.EMPL.ZS',
    'srv_emp': 'SL.SRV.EMPL.ZS',
    'birth': 'SP.DYN.CBRT.IN',
    'death': 'SP.DYN.CDRT.IN',
    'tfr': 'SP.DYN.TFRT.IN',
    'urban': 'SP.URB.TOTL.IN.ZS',
    'life': 'SP.DYN.LE00.IN',
    'age65': 'SP.POP.65UP.TO.ZS',
    'age0014': 'SP.POP.0014.TO.ZS',
    'netmig': 'SM.POP.NETM',
    'exp_gdp': 'NE.EXP.GNFS.ZS',
}

SPARQL = {
    'countries': '''
SELECT ?c ?iso ?ru ?capRu ?contRu ?govRu ?landlocked WHERE {
  ?c wdt:P31 wd:Q3624078; wdt:P298 ?iso .
  FILTER NOT EXISTS { ?c wdt:P576 ?end }
  OPTIONAL { ?c rdfs:label ?ru FILTER(lang(?ru) = "ru") }
  OPTIONAL { ?c wdt:P36 ?cap . ?cap rdfs:label ?capRu FILTER(lang(?capRu) = "ru") }
  OPTIONAL { ?c wdt:P30 ?cont . ?cont rdfs:label ?contRu FILTER(lang(?contRu) = "ru") }
  OPTIONAL { ?c wdt:P122 ?gov . ?gov rdfs:label ?govRu FILTER(lang(?govRu) = "ru") }
  BIND(EXISTS { ?c wdt:P31 wd:Q123480 } AS ?landlocked)
}''',
    'capitals': '''
SELECT ?iso ?capRu ?coord WHERE {
  ?c wdt:P31 wd:Q3624078; wdt:P298 ?iso; wdt:P36 ?cap .
  FILTER NOT EXISTS { ?c wdt:P576 ?end }
  ?cap wdt:P625 ?coord . ?cap rdfs:label ?capRu FILTER(lang(?capRu) = "ru")
}''',
    'regions': '''
SELECT ?s ?ru ?area ?pop ?popDate ?capRu ?coord WHERE {
  wd:Q159 wdt:P150 ?s .
  ?s rdfs:label ?ru FILTER(lang(?ru) = "ru")
  OPTIONAL { ?s wdt:P2046 ?area }
  OPTIONAL { ?s p:P1082 ?st . ?st ps:P1082 ?pop . OPTIONAL { ?st pq:P585 ?popDate } }
  OPTIONAL { ?s wdt:P36 ?cap . ?cap rdfs:label ?capRu FILTER(lang(?capRu) = "ru") . OPTIONAL { ?cap wdt:P625 ?coord } }
}''',
    'cities': '''
SELECT ?c ?ru ?pop ?popDate ?coord ?subjRu WHERE {
  ?c wdt:P17 wd:Q159; wdt:P31/wdt:P279* wd:Q515; wdt:P625 ?coord .
  ?c p:P1082 ?st . ?st ps:P1082 ?pop . OPTIONAL { ?st pq:P585 ?popDate }
  FILTER(?pop >= 90000)
  ?c rdfs:label ?ru FILTER(lang(?ru) = "ru")
  ?c wdt:P131* ?subj . wd:Q159 wdt:P150 ?subj .
  ?subj rdfs:label ?subjRu FILTER(lang(?subjRu) = "ru")
}''',
    'rivers': '''
SELECT ?r ?ru ?len ?mouthRu ?coord WHERE {
  ?r wdt:P31 wd:Q4022; p:P2043/psn:P2043/wikibase:quantityAmount ?len .
  FILTER(?len >= 900000)   # нормализованное значение в метрах
  ?r rdfs:label ?ru FILTER(lang(?ru) = "ru")
  OPTIONAL { ?r wdt:P403 ?m . ?m rdfs:label ?mouthRu FILTER(lang(?mouthRu) = "ru") }
  OPTIONAL { ?r wdt:P625 ?coord }
}''',
    'lakes': '''
SELECT ?l ?ru ?area ?depth ?coord WHERE {
  ?l wdt:P31/wdt:P279* wd:Q23397; p:P2046/psn:P2046/wikibase:quantityAmount ?area .
  FILTER(?area >= 3.0e9)   # м²
  ?l rdfs:label ?ru FILTER(lang(?ru) = "ru")
  OPTIONAL { ?l p:P4511/psn:P4511/wikibase:quantityAmount ?depth }
  OPTIONAL { ?l wdt:P625 ?coord }
}''',
    'peaks': '''
SELECT ?p ?ru ?elev ?coord ?countryRu WHERE {
  ?p wdt:P31 wd:Q8502; p:P2044/psn:P2044/wikibase:quantityAmount ?elev; wdt:P625 ?coord .
  FILTER(?elev >= 3500)
  ?p p:P2660/psn:P2660/wikibase:quantityAmount ?prom . FILTER(?prom >= 1500)
  ?p rdfs:label ?ru FILTER(lang(?ru) = "ru")
  OPTIONAL { ?p wdt:P17 ?cn . ?cn rdfs:label ?countryRu FILTER(lang(?countryRu) = "ru") }
}''',
}


def get(url, accept='application/json'):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': accept})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read().decode('utf-8')
        except Exception as e:  # сеть/лимиты — повторить с паузой
            print('  повтор:', e, file=sys.stderr)
            time.sleep(65)   # WDQS может ограничивать до 1 запроса в минуту
    raise SystemExit('не удалось: ' + url)


def fetch_wb(cache):
    for key, ind in WB_INDICATORS.items():
        out = cache / f'wb_{key}.json'
        if out.exists():
            continue
        url = f'https://api.worldbank.org/v2/country/all/indicator/{ind}?format=json&date=2015:2024&per_page=20000'
        out.write_text(get(url), encoding='utf-8')
        print('WB', key, ind)
        time.sleep(1)
    meta = cache / 'wb_countries.json'
    if not meta.exists():
        meta.write_text(get('https://api.worldbank.org/v2/country?format=json&per_page=400'), encoding='utf-8')


def fetch_wd(cache):
    for key, q in SPARQL.items():
        out = cache / f'wd_{key}.json'
        if out.exists():
            continue
        url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q, 'format': 'json'})
        out.write_text(get(url, 'application/sparql-results+json'), encoding='utf-8')
        print('WD', key)
        time.sleep(65)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', required=True)
    a = ap.parse_args()
    cache = Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    fetch_wb(cache)
    fetch_wd(cache)
    (cache / 'fetched.txt').write_text(time.strftime('%Y-%m-%d'), encoding='utf-8')


if __name__ == '__main__':
    main()
