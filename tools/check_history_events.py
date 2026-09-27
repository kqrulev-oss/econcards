#!/usr/bin/env python3
"""Сверка дат в data/research/history-events.json с энциклопедиями.

Для каждого события берётся статья `wiki` (русская Википедия; `wiki_en` —
ручная ссылка на английскую, если связи в Викиданных нет) и три
независимо редактируемых источника:
  1) русская Википедия — сырой вики-текст статьи (карточка + преамбула);
  2) английская Википедия — статья, связанная через Викиданные;
  3) Викиданные — структурированные даты (P585, P580, P582, P571, P577, P576).
Дата считается сверенной (`checked: true`), если её подтвердили минимум
два источника. Год ищется в первых ~6000 знаках статьи (карточка и
преамбула), для диапазона «1558–1583» — оба года. Полная дата (ГГГГ-ММ-ДД,
только для событий после 1918 г., новый стиль) — «22 июня 1941» в тексте
или точная дата в Викиданных.

Запуск: python3 tools/check_history_events.py [--only-unchecked]
Даты Викиданных и ссылки на en-статьи берутся одним SPARQL-запросом
(query.wikidata.org) на 40 статей; статьи Википедии — по одной с паузой.
БРЭ (bigenc.ru) закрыта авторизацией, поэтому в автоматическую сверку не
входит; её стоит сверить вручную при редакторской вычитке.
"""
import json, re, sys, time, urllib.parse, urllib.request

PATH = 'data/research/history-events.json'
UA = 'EconcardsResearch/0.1 (https://github.com/kqrulev-oss/econcards; history dates check)'
MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
          'августа', 'сентября', 'октября', 'ноября', 'декабря']
DATE_PROPS = ['P585', 'P580', 'P582', 'P571', 'P577', 'P576', 'P1619', 'P729']
LEAD = 6000


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 ** (i + 1))
        except Exception:
            time.sleep(2 ** (i + 1))
    return None


def raw(lang, title, depth=0):
    url = f'https://{lang}.wikipedia.org/w/index.php?' + urllib.parse.urlencode({'title': title, 'action': 'raw'})
    text = get(url)
    time.sleep(1)
    if text is None:
        return None, title
    m = re.match(r'\s*#(?:перенаправление|redirect)\s*\[\[([^\]|#]+)', text, re.I)
    if m and depth < 2:
        return raw(lang, m.group(1).strip(), depth + 1)
    return text, title


def lead(text):
    text = re.sub(r'<ref[^>/]*/>', '', text)
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.S)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    return text[:LEAD]


def years_of(ev):
    """Годы, которые должны подтвердиться: начало и (если есть) конец."""
    d = str(ev['date'])
    bc = 'до н. э.' in d
    nums = [int(x) for x in re.findall(r'\d{3,4}|\b\d{2}\b(?=\s*до н)', d)]
    if re.match(r'^\d{4}-\d{2}-\d{2}$', d):
        nums = [int(d[:4])]
    if bc:
        nums = [-n for n in nums]
    return nums


def has_year(text, y):
    s = str(abs(y))
    return re.search(r'(?<!\d)' + s + r'(?!\d)', text) is not None


def text_ok(text, ev):
    if not text:
        return False
    t = lead(text)
    d = str(ev['date'])
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', d)
    if m:
        y, mo, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        ru = f'{day} {MONTHS[mo - 1]}'
        en = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
              'September', 'October', 'November', 'December'][mo - 1]
        pats = [ru, f'{day:02d}.{mo:02d}.{y}', f'{day}.{mo:02d}.{y}', f'{en} {day}', f'{day} {en}',
                f'{y}|{mo}|{day}', f'{y}-{mo:02d}-{day:02d}']
        return has_year(t, y) and any(p in t for p in pats)
    return all(has_year(t, y) for y in years_of(ev))


def wd_ok(dates, ev):
    if not dates:
        return False
    d = str(ev['date'])
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', d)
    if m:
        y, mo, day = map(int, m.groups())
        return any(x[1] == y and x[2] == mo and x[3] == day for x in dates)
    ys = {x[1] for x in dates}
    need = years_of(ev)
    # старт обязателен, конец — если указан
    return all(y in ys for y in need)


def enc(title):
    return urllib.parse.quote(title.replace(' ', '_'), safe=";@$!*(),/~:'")


def sparql(ru_titles):
    """Одним запросом: элемент Викиданных, статья en и даты для списка статей ru."""
    out = {}
    titles = list(ru_titles)
    for k in range(0, len(titles), 40):
        chunk = titles[k:k + 40]
        vals = ' '.join('<https://ru.wikipedia.org/wiki/' + enc(t) + '>' for t in chunk)
        props = ' '.join('wdt:' + p for p in DATE_PROPS)
        q = f"""SELECT ?art ?item ?en ?p ?t WHERE {{
          VALUES ?art {{ {vals} }}
          ?art schema:about ?item .
          OPTIONAL {{ ?en schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }}
          OPTIONAL {{ VALUES ?p {{ {props} }} ?item ?p ?t . }}
        }}"""
        txt = get('https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q, 'format': 'json'}))
        time.sleep(2)
        if not txt:
            continue
        for b in json.loads(txt)['results']['bindings']:
            t = urllib.parse.unquote(b['art']['value'].split('/wiki/', 1)[1]).replace('_', ' ')
            r = out.setdefault(t, {'item': b['item']['value'].rsplit('/', 1)[1], 'en': None, 'dates': set()})
            if 'en' in b:
                r['en'] = urllib.parse.unquote(b['en']['value'].split('/wiki/', 1)[1]).replace('_', ' ')
            if 't' in b and 'p' in b:
                m = re.match(r'(-?)0*(\d+)-(\d\d)-(\d\d)', b['t']['value'])
                if m:
                    y = int(m.group(2)) * (-1 if m.group(1) else 1)
                    r['dates'].add((b['p']['value'].rsplit('/', 1)[1], y, int(m.group(3)), int(m.group(4)), 11))
    return out


def check_all(evs):
    ru = {}
    for ev in evs:
        text, title = raw('ru', ev['wiki'])
        ru[id(ev)] = (text, title)
    wd = sparql({t for text, t in ru.values() if text})
    for ev in evs:
        text, title = ru[id(ev)]
        res = {'ruwiki': False, 'enwiki': False, 'wikidata': False}
        urls = {}
        note = []
        if text is None:
            note.append('статья ru не найдена')
        else:
            urls['ruwiki'] = 'https://ru.wikipedia.org/wiki/' + enc(title)
            res['ruwiki'] = text_ok(text, ev)
            w = wd.get(title)
            if not w and ev.get('wiki_en'):
                w = {'item': None, 'en': None, 'dates': set()}
            if not w:
                note.append('нет элемента Викиданных')
            else:
                if w['item']:
                    urls['wikidata'] = 'https://www.wikidata.org/wiki/' + w['item']
                    res['wikidata'] = wd_ok(list(w['dates']), ev)
                en_name = ev.get('wiki_en') or w['en']
                if en_name:
                    en, en_title = raw('en', en_name)
                    if en is None:
                        note.append('статья en недоступна')
                    else:
                        urls['enwiki'] = 'https://en.wikipedia.org/wiki/' + enc(en_title)
                        res['enwiki'] = text_ok(en, ev)
        ok = [k for k in ('ruwiki', 'enwiki', 'wikidata') if res[k]]
        ev['checked'] = len(ok) >= 2
        ev['sources'] = [urls[k] for k in ok] if ok else list(urls.values())[:2]
        ev['verified_by'] = ok
        if note:
            ev['check_note'] = '; '.join(note)
        else:
            ev.pop('check_note', None)
        print(f"{'OK ' if ev['checked'] else '-- '} {ev['date']:>14} {ev['event'][:50]:50} {','.join(ok)} {ev.get('check_note', '')}", flush=True)


def main():
    data = json.load(open(PATH, encoding='utf-8'))
    only = '--only-unchecked' in sys.argv
    evs = [e for e in data['events'] if not (only and e.get('checked'))]
    for k in range(0, len(evs), 20):
        check_all(evs[k:k + 20])
        json.dump(data, open(PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    n = sum(1 for e in data['events'] if e.get('checked'))
    print(f'сверено {n} из {len(data["events"])}')


if __name__ == '__main__':
    main()
