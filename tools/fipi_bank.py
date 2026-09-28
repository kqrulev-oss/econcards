#!/usr/bin/env python3
"""Скачивает открытый банк заданий ФИПИ (ЕГЭ и ОГЭ) в data/source/fipi/.

Банк: https://ege.fipi.ru/bank/ и https://oge.fipi.ru/bank/. Ответов в банке нет,
их находит tools/fipi_answers.py через проверку на сайте ФИПИ. Наборы собирает
tools/build_packs.py.

Запуск (сайт банка обычно открывается только из России):
  python3 tools/fipi_bank.py                   # все предметы ЕГЭ
  python3 tools/fipi_bank.py physics chemistry # выбранные предметы
  python3 tools/fipi_bank.py --exam oge        # ОГЭ
  python3 tools/fipi_bank.py --offline         # пересобрать JSON из кэша страниц, без сети
  python3 tools/fipi_bank.py --list            # ключи предметов

Сервер ФИПИ не отдаёт промежуточный сертификат GlobalSign (браузеры догружают
его сами, Python — нет), поэтому он встроен ниже. Если ФИПИ сменит сертификат:
FIPI_CA=файл.pem с недостающими сертификатами или, в крайнем случае, --insecure.

Результат — data/source/fipi/<exam>-<предмет>.json:
  {exam, key, title, proj, count, kes: [{code, name, themes: [{code, name}]}],
   filters: {qpos: {значение: подпись}, ...}, tasks: [...]}
Задание: {id, guid, kind, hint, text, html?, kes: [коды], opts?, img?, media?, pos?, meta?}
  kind — short (краткий ответ), full (развёрнутый), select (выбор ответа)
  text — условие простым текстом, формулы в ⟦ ⟧ (как в карточках)
  html — то же с разметкой: таблицы, картинки, формулы MathML (если есть что размечать)
Картинки — img/fipi/<exam>-<предмет>/, сырые страницы — data/fipi-cache/ (не в git).
"""
import argparse
import hashlib
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'source' / 'fipi'
CACHE = ROOT / 'data' / 'fipi-cache'
IMG = ROOT / 'img' / 'fipi'

BASE = {'ege': 'https://ege.fipi.ru/bank/', 'oge': 'https://oge.fipi.ru/bank/'}

# Предметы и идентификаторы проектов банка (параметр proj)
SUBJECTS = {
    'ege': {
        'russian': ('Русский язык', 'AF0ED3F2557F8FFC4C06F80B6803FD26'),
        'math_prof': ('Математика. Профильный уровень', 'AC437B34557F88EA4115D2F374B0A07B'),
        'math_base': ('Математика. Базовый уровень', 'E040A72A1A3DABA14C90C97E0B6EE7DC'),
        'physics': ('Физика', 'BA1F39653304A5B041B656915DC36B38'),
        'chemistry': ('Химия', 'EA45D8517ABEB35140D0D83E76F14A41'),
        'informatics': ('Информатика и ИКТ', 'B9ACA5BBB2E19E434CD6BEC25284C67F'),
        'biology': ('Биология', 'CA9D848A31849ED149D382C32A7A2BE4'),
        'history': ('История', '068A227D253BA6C04D0C832387FD0D89'),
        'social': ('Обществознание', '756DF168F63F9A6341711C61AA5EC578'),
        'geography': ('География', '20E79180061DB32845C11FC7BD87C7C8'),
        'literature': ('Литература', '4F431E63B9C9B25246F00AD7B5253996'),
        'english': ('Английский язык', '4B53A6CB75B0B5E1427E596EB4931A2A'),
        'german': ('Немецкий язык', 'B5963A8D84CF9020461EAE42F37F541F'),
        'french': ('Французский язык', '5BAC840990A3AF0A4EE80D1B5A1F9527'),
        'spanish': ('Испанский язык', '8C65A335D93D9DA047C42613F61416F3'),
        'chinese': ('Китайский язык', 'F6298F3470D898D043E18BC680F60434'),
    },
    'oge': {
        'russian': ('Русский язык', '2F5EE3B12FE2A0EA40B06BF61A015416'),
        'math': ('Математика', 'DE0E276E497AB3784C3FC4CC20248DC0'),
        'physics': ('Физика', 'B24AFED7DE6AB5BC461219556CCA4F9B'),
        'chemistry': ('Химия', '33B3A93C5A6599124B04FB95616C835B'),
        'informatics': ('Информатика', '74676951F093A0754D74F2D6E7955F06'),
        'biology': ('Биология', '0E1FA4229923A5CE4FC368155127ED90'),
        'history': ('История', '3CBBE97571208D9140697A6C2ABE91A0'),
        'social': ('Обществознание', 'AE63AB28A2D28E194A286FA5A8EB9A78'),
        'geography': ('География', '0FA4DA9E3AE2BA1547B75F0B08EF6445'),
        'literature': ('Литература', '6B2CD4C77304B2A3478E5A5B61F6899A'),
        'english': ('Английский язык', '8BBD5C99F37898B6402964AB11955663'),
        'german': ('Немецкий язык', 'A2AC67AE354EBC5242C49482CBC13451'),
        'french': ('Французский язык', '2A4C52ED5AC1ADA644B8BBF169FEC0FC'),
        'spanish': ('Испанский язык', '7FF0B02E53DFBCDE4F56B0148BE9A236'),
    },
}

# Промежуточный сертификат, которым подписан *.fipi.ru (GlobalSign GCC R3 DV TLS CA 2020,
# до 18.03.2029, http://secure.globalsign.com/cacert/gsgccr3dvtlsca2020.crt). Корень
# GlobalSign R3 есть в системных сертификатах, так что проверка остаётся полной.
FIPI_INTERMEDIATE = """-----BEGIN CERTIFICATE-----
MIIEsDCCA5igAwIBAgIQd70OB0LV2enQSdd00CpvmjANBgkqhkiG9w0BAQsFADBM
MSAwHgYDVQQLExdHbG9iYWxTaWduIFJvb3QgQ0EgLSBSMzETMBEGA1UEChMKR2xv
YmFsU2lnbjETMBEGA1UEAxMKR2xvYmFsU2lnbjAeFw0yMDA3MjgwMDAwMDBaFw0y
OTAzMTgwMDAwMDBaMFMxCzAJBgNVBAYTAkJFMRkwFwYDVQQKExBHbG9iYWxTaWdu
IG52LXNhMSkwJwYDVQQDEyBHbG9iYWxTaWduIEdDQyBSMyBEViBUTFMgQ0EgMjAy
MDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAKxnlJV/de+OpwyvCXAJ
IcxPCqkFPh1lttW2oljS3oUqPKq8qX6m7K0OVKaKG3GXi4CJ4fHVUgZYE6HRdjqj
hhnuHY6EBCBegcUFgPG0scB12Wi8BHm9zKjWxo3Y2bwhO8Fvr8R42pW0eINc6OTb
QXC0VWFCMVzpcqgz6X49KMZowAMFV6XqtItcG0cMS//9dOJs4oBlpuqX9INxMTGp
6EASAF9cnlAGy/RXkVS9nOLCCa7pCYV+WgDKLTF+OK2Vxw3RUJ/p8009lQeUARv2
UCcNNPCifYX1xIspvarkdjzLwzOdLahDdQbJON58zN4V+lMj0msg+c0KnywPIRp3
BMkCAwEAAaOCAYUwggGBMA4GA1UdDwEB/wQEAwIBhjAdBgNVHSUEFjAUBggrBgEF
BQcDAQYIKwYBBQUHAwIwEgYDVR0TAQH/BAgwBgEB/wIBADAdBgNVHQ4EFgQUDZjA
c3+rvb3ZR0tJrQpKDKw+x3wwHwYDVR0jBBgwFoAUj/BLf6guRSSuTVD6Y5qL3uLd
G7wwewYIKwYBBQUHAQEEbzBtMC4GCCsGAQUFBzABhiJodHRwOi8vb2NzcDIuZ2xv
YmFsc2lnbi5jb20vcm9vdHIzMDsGCCsGAQUFBzAChi9odHRwOi8vc2VjdXJlLmds
b2JhbHNpZ24uY29tL2NhY2VydC9yb290LXIzLmNydDA2BgNVHR8ELzAtMCugKaAn
hiVodHRwOi8vY3JsLmdsb2JhbHNpZ24uY29tL3Jvb3QtcjMuY3JsMEcGA1UdIARA
MD4wPAYEVR0gADA0MDIGCCsGAQUFBwIBFiZodHRwczovL3d3dy5nbG9iYWxzaWdu
LmNvbS9yZXBvc2l0b3J5LzANBgkqhkiG9w0BAQsFAAOCAQEAy8j/c550ea86oCkf
r2W+ptTCYe6iVzvo7H0V1vUEADJOWelTv07Obf+YkEatdN1Jg09ctgSNv2h+LMTk
KRZdAXmsE3N5ve+z1Oa9kuiu7284LjeS09zHJQB4DJJJkvtIbjL/ylMK1fbMHhAW
i0O194TWvH3XWZGXZ6ByxTUIv1+kAIql/Mt29PmKraTT5jrzcVzQ5A9jw16yysuR
XRrLODlkS1hyBjsfyTNZrmL1h117IFgntBA5SQNVl9ckedq5r4RSAU85jV8XK5UL
REjRZt2I6M9Po9QL7guFLu4sPFJpwR1sPJvubS2THeo7SxYoNDtdyBHs7euaGcMa
D/fayQ==
-----END CERTIFICATE-----"""

KINDS = {'краткий ответ': 'short', 'развернутый ответ': 'full', 'развёрнутый ответ': 'full',
         'выбор ответа': 'select', 'выбор ответа из предложенных вариантов': 'select',
         'выбор ответов из предложенных вариантов': 'multi'}
MEDIA = ('.mp3', '.mp4', '.flv', '.swf', '.wav', '.ogg', '.avi', 'show_media.php')


# ---------- сеть ----------

class FipiError(Exception):
    pass


class Client:
    """Страницы банка в cp1251, сессия PHPSESSID в cookie, вежливая пауза между запросами."""

    def __init__(self, exam, insecure=False, delay=0.4):
        self.base = BASE[exam]
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(cadata=FIPI_INTERMEDIATE)
        if os.environ.get('FIPI_CA'):
            ctx.load_verify_locations(cafile=os.environ['FIPI_CA'])
        if insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar()), urllib.request.HTTPSHandler(context=ctx))
        self.opener.addheaders = [
            ('User-Agent', 'Mozilla/5.0 (compatible; econcards-fipi/1.0; +https://github.com/kqrulev-oss/econcards)'),
            ('Accept-Language', 'ru-RU,ru;q=0.9'),
        ]
        self.delay = delay
        self.last = 0.0

    def fetch(self, path, params=None, data=None, raw=False):
        url = urllib.parse.urljoin(self.base, path)
        if params:
            url += '?' + urllib.parse.urlencode(params)
        body = urllib.parse.urlencode(data, doseq=True).encode() if data is not None else None
        for attempt in range(6):
            time.sleep(max(0.0, self.last + self.delay - time.time()))
            self.last = time.time()
            try:
                with self.opener.open(urllib.request.Request(url, data=body), timeout=60) as r:
                    content = r.read()
                return content if raw else content.decode('windows-1251', errors='replace')
            except ssl.SSLCertVerificationError:
                sys.exit('Python не доверяет сертификату ФИПИ. Укажите недостающие сертификаты: '
                         'FIPI_CA=путь/к/файлу.pem, или запустите с --insecure.')
            except urllib.error.HTTPError as e:
                if e.code == 404 or attempt == 5:
                    raise
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt == 5:
                    raise FipiError(f'банк ФИПИ не отвечает ({url}): {e}')
            time.sleep(2 ** attempt)
        raise RuntimeError('unreachable')


# ---------- разбор HTML ----------

VOID = {'br', 'img', 'input', 'hr', 'meta', 'link', 'col', 'area', 'base', 'wbr', 'param', 'source', 'embed', 'track'}


class Node:
    __slots__ = ('tag', 'attrs', 'kids', 'parent')

    def __init__(self, tag, attrs=None, parent=None):
        self.tag, self.attrs, self.kids, self.parent = tag, dict(attrs or {}), [], parent

    def iter(self):
        yield self
        for k in self.kids:
            if isinstance(k, Node):
                yield from k.iter()

    def find(self, pred):
        return next((n for n in self.iter() if pred(n)), None)

    def classes(self):
        return (self.attrs.get('class') or '').split()

    def text(self):
        return ''.join(k if isinstance(k, str) else k.text() for k in self.kids)


class Tree(HTMLParser):
    """Терпимый к «грязному» HTML построитель дерева: сам закрывает p, li, td, tr."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('#root')
        self.stack = [self.root]

    def _close_to(self, tag, stop=()):
        for i in range(len(self.stack) - 1, 0, -1):
            t = self.stack[i].tag
            if t == tag:
                del self.stack[i:]
                return
            if t in stop:
                return

    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            self._close_to('p', stop=('div', 'td', 'th', 'li', 'table'))
        elif tag == 'li':
            self._close_to('li', stop=('ul', 'ol'))
        elif tag in ('td', 'th'):
            self._close_to('td', stop=('tr', 'table'))
            self._close_to('th', stop=('tr', 'table'))
        elif tag == 'tr':
            self._close_to('tr', stop=('table',))
        node = Node(tag, [(k.lower(), v or '') for k, v in attrs], self.stack[-1])
        self.stack[-1].kids.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, [(k.lower(), v or '') for k, v in attrs], self.stack[-1])
        self.stack[-1].kids.append(node)

    def handle_endtag(self, tag):
        if any(n.tag == tag for n in self.stack[1:]):
            self._close_to(tag)

    def handle_data(self, data):
        self.stack[-1].kids.append(data)


def parse(html):
    t = Tree()
    t.feed(html)
    t.close()
    return t.root


# ---------- очистка условия: безопасный компактный HTML с MathML ----------

HTML_TAGS = {'p', 'div', 'br', 'b', 'i', 'u', 'sub', 'sup', 'table', 'tr', 'td', 'th', 'ul', 'ol', 'li', 'img'}
HTML_MAP = {'strong': 'b', 'em': 'i', 'center': 'div', 'blockquote': 'div', 'h1': 'p', 'h2': 'p', 'h3': 'p',
            'h4': 'p', 'h5': 'p', 'h6': 'p', 'dir': 'ul', 'menu': 'ul', 'caption': 'p', 'pre': 'div'}
DROP = {'script', 'style', 'input', 'button', 'select', 'textarea', 'form', 'iframe', 'object', 'embed',
        'noscript', 'head', 'title', 'meta', 'link', 'o:p', 'annotation', 'annotation-xml', 'xml', 'svg'}
MATH_TAGS = {'math', 'mrow', 'mi', 'mn', 'mo', 'mtext', 'mspace', 'ms', 'mfrac', 'msqrt', 'mroot', 'msup', 'msub',
             'msubsup', 'mover', 'munder', 'munderover', 'mtable', 'mtr', 'mtd', 'mstyle', 'mpadded',
             'mphantom', 'menclose', 'mmultiscripts', 'mprescripts', 'none'}
MATH_TOKENS = {'mi', 'mn', 'mo', 'mtext', 'ms'}
ATTRS = {
    'td': {'colspan', 'rowspan'}, 'th': {'colspan', 'rowspan'}, 'img': {'src'}, 'ol': {'start', 'type'},
    'math': {'display'}, 'mstyle': {'displaystyle', 'scriptlevel'},
    'mo': {'stretchy', 'fence', 'separator', 'lspace', 'rspace', 'form', 'largeop', 'movablelimits'},
    'mover': {'accent'}, 'munder': {'accentunder'}, 'munderover': {'accent', 'accentunder'},
    'mfrac': {'linethickness'}, 'mtable': {'columnalign', 'rowalign'}, 'mtd': {'columnalign', 'columnspan'},
    'mspace': {'width'}, 'mi': {'mathvariant'}, 'mn': {'mathvariant'}, 'mtext': {'mathvariant'},
    'menclose': {'notation'},
}
PICTURE = re.compile(r"""(ShowPicture\w*)\s*\(\s*(['"])([^'"]+)\2(?:\s*,\s*(['"])([^'"]*)\4)?""")
IMAGE_EXT = re.compile(r'\.(png|gif|jpe?g|svg|webp|bmp)$', re.I)
DOC_EXT = re.compile(r'\.(zip|rar|7z|xlsx?|ods|docx?|odt|txt|csv|pdf)$', re.I)
AUDIO_EXT = re.compile(r'\.(mp3|ogg|wav)$', re.I)
INVISIBLE = dict.fromkeys(map(ord, '⁡⁢⁣⁤​﻿'), None)


def local(tag):
    return tag.rsplit(':', 1)[-1] if tag.startswith('m:') or ':' not in tag else tag


def pictures(script):
    """ShowPictureQ('docs/…/xs3qstsrc….png') и родственные → [(функция, путь, второй путь)].
    У ShowPictureQ2/Q3 первым идёт большая картинка или файл к заданию (zip, xlsx…),
    вторым — превью."""
    return [(m.group(1), re.sub(r'\.\s+', '.', m.group(3)), m.group(5) or '') for m in PICTURE.finditer(script)]


class Cleaner:
    """Переводит узел условия в компактный HTML: только разрешённые теги и атрибуты,
    MathML без префикса m: и без semantics, пути картинок — локальные."""

    def __init__(self, resolve_img, base=''):
        self.resolve_img = resolve_img  # (путь из страницы, из скрипта?) → локальный путь или None
        self.base = base  # files_location: папка картинок ShowPicture(...) в общих текстах
        self.images = []
        self.files = []  # файлы к заданию (архивы, таблицы) — ссылками на сайт ФИПИ
        self.audio = []  # записи для аудирования — тоже с сайта ФИПИ
        self.media = False

    def image(self, src, script=False):
        if any(x in src.lower() for x in MEDIA):
            self.media = True
            return None
        local_src = self.resolve_img(src, script)
        if local_src and local_src not in self.images:
            self.images.append(local_src)
        return local_src

    def clean(self, node, in_math=False):
        """Список детей (строки и Node) после очистки."""
        out = []
        for k in node.kids:
            if isinstance(k, str):
                s = k.translate(INVISIBLE)
                if in_math:
                    if s.strip():
                        out.append(s.strip())
                else:
                    out.append(re.sub(r'[ \t\r\n\f]+', ' ', s))
                continue
            out.extend(self.element(k, in_math))
        return out

    def element(self, n, in_math):
        tag = local(n.tag)
        if tag == 'script':
            # ShowPictureQ* — от qfiles_location, ShowPicture* — от files_location блока
            imgs = []
            for fn, src, _ in pictures(n.text()):
                q = fn.startswith('ShowPictureQ')
                path = src if q else self.base + src
                if AUDIO_EXT.search(path):
                    url = getattr(self.resolve_img, 'url', lambda s, script: s)(path, q)
                    if url not in self.audio:
                        self.audio.append(url)
                elif IMAGE_EXT.search(path) or any(x in path.lower() for x in MEDIA):
                    imgs.append(self.image(path, script=q))
                else:  # файл к заданию: в репозиторий не кладём, даём ссылку на ФИПИ
                    url = getattr(self.resolve_img, 'url', lambda s, script: s)(path, q)
                    if url not in self.files:
                        self.files.append(url)
            return [Node('img', {'src': s}) for s in imgs if s]
        if tag in DROP or n.tag in DROP:
            return []
        if tag == 'math' or (in_math and tag in MATH_TAGS | {'semantics', 'mfenced'}):
            return self.math(n, tag)
        if in_math:
            return self.clean(n, in_math)  # неизвестный тег внутри формулы — оставляем содержимое
        if tag == 'img':
            src = self.image(n.attrs.get('src', ''))
            return [Node('img', {'src': src})] if src else []
        if tag in ('a', 'embed', 'audio', 'video', 'source') and any(x in (n.attrs.get('href', '') + n.attrs.get('src', '')).lower() for x in MEDIA):
            self.media = True
        elif tag == 'a' and DOC_EXT.search(n.attrs.get('href', '')):
            url = getattr(self.resolve_img, 'url', lambda s, script: s)(n.attrs['href'], False)
            if url not in self.files:
                self.files.append(url)
        tag = HTML_MAP.get(tag, tag)
        kids = self.clean(n, False)
        wrap = self.style_tags(n)
        if tag in HTML_TAGS:
            el = Node(tag, {k: v for k, v in n.attrs.items() if k in ATTRS.get(tag, ())})
            el.kids = self.wrap(kids, wrap)
            if tag == 'div' and not el.kids:
                return []
            return [el]
        return self.wrap(kids, wrap)  # span, font, a, tbody… — только содержимое

    @staticmethod
    def style_tags(n):
        st = (n.attrs.get('style') or '').lower().replace(' ', '')
        tags = []
        if re.search(r'font-weight:(bold|[6-9]00)', st):
            tags.append('b')
        if 'font-style:italic' in st:
            tags.append('i')
        if 'text-decoration:underline' in st:
            tags.append('u')
        if 'vertical-align:super' in st:
            tags.append('sup')
        elif 'vertical-align:sub' in st:
            tags.append('sub')
        return tags

    @staticmethod
    def wrap(kids, tags):
        if not tags or not any(isinstance(k, Node) or k.strip() for k in kids):
            return kids
        for t in reversed(tags):
            el = Node(t)
            el.kids = kids
            kids = [el]
        return kids

    def math(self, n, tag):
        if tag == 'semantics':
            first = next((k for k in n.kids if isinstance(k, Node) and local(k.tag) not in ('annotation', 'annotation-xml')), None)
            return self.math(first, local(first.tag)) if first is not None else []
        if tag == 'mfenced':
            op, cl = n.attrs.get('open', '('), n.attrs.get('close', ')')
            seps = (n.attrs.get('separators', ',') or '').replace(' ', '')
            items = [k for k in n.kids if isinstance(k, Node)]
            row = Node('mrow')
            row.kids.append(self.mo(op))
            for i, it in enumerate(items):
                if i and seps:
                    row.kids.append(self.mo(seps[min(i - 1, len(seps) - 1)]))
                row.kids.extend(self.math(it, local(it.tag)))
            row.kids.append(self.mo(cl))
            return [row]
        el = Node(tag, {k: v for k, v in n.attrs.items() if k in ATTRS.get(tag, ())})
        if tag in MATH_TOKENS:
            el.kids = [re.sub(r'\s+', ' ', n.text().translate(INVISIBLE)).strip()]
            if not el.kids[0]:
                return []
            return [el]
        el.kids = self.clean(n, True)
        # mrow из одного элемента не нужен (кроме корня формулы)
        if tag in ('mrow', 'mstyle', 'mpadded') and not el.attrs and len(el.kids) == 1 and isinstance(el.kids[0], Node):
            return el.kids
        return [el]

    @staticmethod
    def mo(s):
        el = Node('mo')
        el.kids = [s]
        return el


def serialize(kids):
    out = []
    for k in kids:
        if isinstance(k, str):
            out.append(k.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
            continue
        attrs = ''.join(f' {a}="{v.replace("&", "&amp;").replace(chr(34), "&quot;")}"' for a, v in k.attrs.items())
        if k.tag in VOID:
            out.append(f'<{k.tag}{attrs}>')
        else:
            out.append(f'<{k.tag}{attrs}>{serialize(k.kids)}</{k.tag}>')
    return ''.join(out)


def tidy(kids):
    """Убирает пустые абзацы и лишние пробелы по краям блоков."""
    blocks = {'p', 'div', 'td', 'th', 'li', 'tr', 'table', 'ul', 'ol'}
    out = []
    for k in kids:
        if isinstance(k, Node):
            if k.tag not in MATH_TAGS:
                k.kids = tidy(k.kids)
            if k.tag in ('p', 'div', 'li', 'b', 'i', 'u', 'sub', 'sup') and not any(
                    isinstance(x, Node) or x.strip(' \xa0') for x in k.kids):
                continue
            # Картинка-формула в <sub> (так выравнивал Word) — индексом её делать не нужно
            if k.tag in ('sub', 'sup') and all(isinstance(x, Node) and x.tag == 'img' or isinstance(x, str) and not x.strip()
                                               for x in k.kids):
                out.extend(x for x in k.kids if isinstance(x, Node))
                continue
        out.append(k)
    # пробелы в начале и конце блока
    while out and isinstance(out[0], str) and not out[0].strip():
        out.pop(0)
    while out and isinstance(out[-1], str) and not out[-1].strip():
        out.pop()
    if out and isinstance(out[0], str):
        out[0] = out[0].lstrip()
    if out and isinstance(out[-1], str):
        out[-1] = out[-1].rstrip()
    # пробельные строки между блоками не нужны
    return [k for i, k in enumerate(out) if not (isinstance(k, str) and not k.strip() and (
        (i and isinstance(out[i - 1], Node) and out[i - 1].tag in blocks) or
        (i + 1 < len(out) and isinstance(out[i + 1], Node) and out[i + 1].tag in blocks)))]


# ---------- текстовая версия: формулы строкой, как в карточках (⟦…⟧, ^{…}) ----------

FUNCS = {'sin', 'cos', 'tg', 'ctg', 'tan', 'cot', 'arcsin', 'arccos', 'arctg', 'arcctg', 'log', 'ln', 'lg', 'lim', 'max', 'min'}
SUB = str.maketrans('0123456789+-−=()', '₀₁₂₃₄₅₆₇₈₉₊₋₋₌₍₎')
SUP_CHARS = '0123456789+-−=()n'
SUP = str.maketrans(SUP_CHARS, '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻⁼⁽⁾ⁿ')
ROOTS = {'2': '√', '3': '∛', '4': '∜'}


def _group(s):
    """Скобки вокруг составного выражения: a+b → (a+b), 12 → 12."""
    s = s.strip()
    if re.fullmatch(r'[\w.,]+|\([^()]*\)|√\w+|[\w.,]+\^\{?\w+\}?', s):
        return s
    return f'({s})'


def math_text(n):
    if isinstance(n, str):
        return n
    tag = n.tag
    kids = [k for k in n.kids if isinstance(k, Node) or k.strip()]
    t = [math_text(k) for k in kids]
    if tag in MATH_TOKENS:
        s = ''.join(t)
        if tag == 'mo' and s in ('=', '<', '>', '≤', '≥', '≠', '≈', '⇒', '⇔', '∈'):
            return f' {s} '
        # sin 2x, log 5 — имя функции отделяем от аргумента
        return s + ' ' if tag == 'mi' and s in FUNCS else s
    if tag == 'mspace':
        return ' '
    if tag == 'mfrac' and len(t) == 2:
        return f'{_group(t[0])}/{_group(t[1])}'
    if tag == 'msqrt':
        inner = ''.join(t).strip()
        return '√' + (inner if re.fullmatch(r'\d+|[A-Za-zА-Яа-я]', inner) else f'({inner})')
    if tag == 'mroot' and len(t) == 2:
        idx = t[1].strip()
        return (ROOTS[idx] if idx in ROOTS else f'√[{idx}]') + _group(t[0])
    if tag in ('msup', 'msub', 'msubsup') and t:
        t[0] = t[0].rstrip()  # log ₂, а не «log  ₂»
    if tag == 'msup' and len(t) == 2:
        e = t[1].strip()
        return t[0] + (f'^{e}' if re.fullmatch(r'[0-9A-Za-zА-Яа-я]|[+\-−][0-9]+', e) else f'^{{{e}}}')
    if tag == 'msub' and len(t) == 2:
        s = t[1].strip()
        return t[0] + (s.translate(SUB) if re.fullmatch(r'[0-9+\-−=()]+', s) else f'_{s}')
    if tag == 'msubsup' and len(t) == 3:
        s = t[1].strip()
        return t[0] + (s.translate(SUB) if s.isdigit() else f'_{{{s}}}') + f'^{{{t[2].strip()}}}'
    if tag == 'mover' and len(t) == 2:
        acc = t[1].strip()
        if acc in ('→', '⟶', '⇀'):
            return t[0] + '⃗'
        if acc in ('¯', '‾', '_', '―', '−'):
            return t[0] + '̅'
        if acc in ('^', 'ˆ'):
            return t[0] + '̂'
        return f'{t[0]}^{{{acc}}}'
    if tag in ('munder', 'munderover') and len(t) >= 2:
        s = f'{t[0]}_{{{t[1].strip()}}}'
        return s + (f'^{{{t[2].strip()}}}' if len(t) == 3 else '')
    if tag == 'mtable':  # система: фигурная скобка обычно стоит перед таблицей отдельным mo
        return '; '.join(x.strip().rstrip(',;') for x in t)
    if tag == 'mtr':
        return ' '.join(x.strip() for x in t)
    if tag == 'mphantom':
        return ''
    return ''.join(t)


def plain(kids):
    """Условие простым текстом для поиска, ИИ и старых клиентов."""
    out = []

    def walk(k):
        if isinstance(k, str):
            out.append(k.replace('\xa0', ' '))
            return
        tag = k.tag
        if tag == 'math':
            f = re.sub(r'\s+', ' ', math_text(k)).strip()
            if f:
                out.append(f'⟦{f}⟧')
            return
        if tag == 'img':
            out.append(' [рисунок] ')
            return
        if tag == 'br':
            out.append('\n')
            return
        if tag in ('p', 'div', 'tr', 'table', 'ul', 'ol'):
            out.append('\n')
        if tag == 'li':
            out.append('\n— ')
        if tag in ('sup', 'sub'):  # 9<sup>11</sup> → 9¹¹, H<sub>2</sub>O → H₂O
            inner = plain(k.kids)
            table = SUP if tag == 'sup' else SUB
            if inner and all(ch in SUP_CHARS if tag == 'sup' else ch in '0123456789+-−=()' for ch in inner):
                out.append(inner.translate(table))
            elif inner:
                out.append(('^{%s}' if tag == 'sup' else '_{%s}') % inner)
            return
        for x in k.kids:
            walk(x)
        if tag in ('td', 'th'):
            out.append(' | ')
        if tag in ('p', 'div', 'tr', 'table', 'ul', 'ol'):
            out.append('\n')

    for k in kids:
        walk(k)
    s = ''.join(out)
    s = re.sub(r'[ \t]*\|\s*\n', '\n', s)
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r' *\n *', '\n', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    # Знак препинания в конце формулы — за скобку; формула из одного числа — без скобок
    s = re.sub(r'\s*([.,;:])⟧', r'⟧\1', s)
    s = re.sub(r'⟦\s*([\w.,]+|[^\w⟦⟧\s]{1,3})\s*⟧', r'\1', s)  # число или одиночный знак (тире) — не формула
    s = re.sub(r'(\w) +([)\]])', r'\1\2', s)
    return s.strip()


def is_rich(kids):
    """Нужна ли разметка: есть формулы со структурой, таблицы, картинки, списки, выделение."""
    for k in kids:
        if isinstance(k, Node):
            for n in k.iter():
                if n.tag in ('table', 'img', 'ul', 'ol', 'b', 'i', 'u', 'sub', 'sup', 'mfrac', 'msqrt', 'mroot',
                             'msup', 'msub', 'msubsup', 'mover', 'munder', 'munderover', 'mtable'):
                    return True
    return False


# ---------- страница заданий ----------

QBLOCK = re.compile(r'<div class=["\']qblock[^"\']*["\'](?: id=["\']q(\w+)["\'])?', re.I)
GROUP = re.compile(r'number-in-group"\s+title="Задание\s+(\d+)\s+в\s+(\w+)')


def parse_meta(info):
    """Свойства задания из div#i<qid>: {'КЭС': [...], 'Тип ответа': [...], ...}."""
    meta = {}
    if info is None:
        return meta
    for tr in (n for n in info.iter() if n.tag == 'tr'):
        cells = [c for c in tr.kids if isinstance(c, Node) and c.tag == 'td']
        if len(cells) < 2:
            continue
        name = re.sub(r'\s+', ' ', cells[0].text()).strip().rstrip(':')
        divs = [d for d in cells[1].kids if isinstance(d, Node) and d.tag == 'div']
        vals = [re.sub(r'\s+', ' ', d.text()).strip() for d in divs] or [re.sub(r'\s+', ' ', cells[1].text()).strip()]
        meta[name] = [v for v in vals if v]
    return meta


def parse_options(block, cleaner):
    """Варианты ответа (задания с выбором): строки с radio/checkbox или блоки-«дистракторы»."""
    opts = []
    for inp in block.iter():
        if inp.tag != 'input' or inp.attrs.get('type', '').lower() not in ('radio', 'checkbox'):
            continue
        row = inp.parent
        while row is not None and row.tag not in ('tr', 'label', 'div', 'li'):
            row = row.parent
        if row is None:
            continue
        holder = Node('div')
        if row.tag == 'tr':  # текст варианта — в соседних ячейках строки, кроме номера «1)»
            for cell in row.kids:
                if isinstance(cell, Node) and not cell.find(lambda x: x is inp) \
                        and not re.fullmatch(r'[\s\xa0]*\d+\)?[\s\xa0]*', cell.text()):
                    holder.kids += cell.kids if cell.tag in ('td', 'th') else [cell]
        else:
            holder.kids = [k for k in row.kids if k is not inp]
        kids = tidy(cleaner.clean(holder))
        opts.append({'id': inp.attrs.get('value') or str(len(opts) + 1), 'kids': kids})
    if not opts:
        for n in block.iter():
            if 'distractor' in ' '.join(n.classes()):
                kids = tidy(cleaner.clean(n))
                opts.append({'id': n.attrs.get('data-value') or n.attrs.get('value') or str(len(opts) + 1), 'kids': kids})
    return [{'id': o['id'], 'text': plain(o['kids']), **({'html': serialize(o['kids'])} if is_rich(o['kids']) else {})}
            for o in opts if o['kids']]


def text_block(root, resolve_img, files):
    """Общий текст группы заданий («Прочитайте текст и выполните задания»)."""
    block = root.find(lambda n: 'qblock' in n.classes())
    hint = block.find(lambda n: 'hint' in n.classes())
    holder = Node('div')
    holder.kids = [k for k in block.kids if k is not hint]
    cleaner = Cleaner(resolve_img, files)
    kids = tidy(cleaner.clean(holder))
    out = {'text': plain(kids)}
    if is_rich(kids):
        out['html'] = serialize(kids)
    if cleaner.images:
        out['img'] = cleaner.images
    if cleaner.files:
        out['files'] = cleaner.files
    if cleaner.audio:
        out['audio'] = cleaner.audio
    if cleaner.media:
        out['media'] = True
    return out


def parse_questions(html, resolve_img, pending=None):
    """Задания со страницы questions.php, счётчик setQCount(всего, страница, размер),
    общие тексты групп {номер группы: текст} и текст, чьи задания ушли на следующую
    страницу (его передают в pending при разборе следующей). resolve_img(src, script) →
    локальный путь картинки."""
    total = re.search(r'setQCount\((\d+)(?:\s*,\s*\d+\s*,\s*(\d+))?', html)
    starts = [m.start() for m in QBLOCK.finditer(html)]
    tasks, groups = [], {}
    for i, st in enumerate(starts):
        seg = html[st:starts[i + 1] if i + 1 < len(starts) else len(html)]
        qid = QBLOCK.match(seg).group(1)
        files = re.search(r"files_location\s*=\s*'([^']*)'", seg)
        root = parse(seg)
        if not qid:  # блок без номера — общий текст для следующих заданий группы
            pending = text_block(root, resolve_img, files.group(1) if files else '')
            continue
        guid = root.find(lambda n: n.tag == 'input' and n.attrs.get('name') == 'guid')
        cell = root.find(lambda n: n.tag == 'td' and 'cell_0' in n.classes())
        hint = root.find(lambda n: 'hint' in n.classes())
        var = root.find(lambda n: 'varinats-block' in n.classes() or 'variants-block' in n.classes())
        info = root.find(lambda n: n.attrs.get('id') == f'i{qid}')
        meta = parse_meta(info)
        cleaner = Cleaner(resolve_img, files.group(1) if files else '')
        kids = tidy(cleaner.clean(cell)) if cell is not None else []
        opts = parse_options(var, cleaner) if var is not None else []
        # Ответ-маска: для выбора сайт ждёт «01100» — отмечены 2-й и 3-й варианты
        mask = re.search(r"ans\s*\+=\s*'1'\s*;\s*else\s+ans\s*\+=\s*'0'", seg)
        kes = [re.match(r'[\d.]+', v).group(0).rstrip('.') for v in meta.get('КЭС', []) if re.match(r'\d', v)]
        atype = ' '.join(meta.get('Тип ответа', [])).lower().replace('ё', 'е')
        kind = KINDS.get(atype) or ('select' if opts else 'full' if 'развернут' in atype else 'short' if atype else '')
        task = {'id': qid, 'guid': guid.attrs.get('value', '') if guid is not None else '',
                'kind': kind, 'hint': re.sub(r'\s+', ' ', hint.text()).strip() if hint is not None else '',
                'text': plain(kids), 'kes': kes}
        if is_rich(kids):
            task['html'] = serialize(kids)
        if opts:
            task['opts'] = opts
        if cleaner.images:
            task['img'] = cleaner.images
        if cleaner.files:
            task['files'] = cleaner.files
        if cleaner.audio:
            task['audio'] = cleaner.audio
        if cleaner.media:
            task['media'] = True
        if mask and opts:
            task['mask'] = 1
        grp = GROUP.search(seg)
        if grp:
            task['group'], task['gn'] = grp.group(2), int(grp.group(1))
            if pending is not None and grp.group(2) not in groups:
                groups[grp.group(2)] = pending
            pending = None
        rest = {k: v for k, v in meta.items() if k not in ('КЭС', 'Тип ответа')}
        if rest:
            task['meta'] = rest
        tasks.append(task)
    size = int(total.group(2)) if total and total.group(2) else None
    return tasks, int(total.group(1)) if total else None, size, groups, pending


def parse_project(html):
    """Страница предмета: дерево КЭС и значения фильтров (тип ответа, позиция в КИМ…)."""
    root = parse(html)
    kes, filters = {}, {}
    for inp in root.iter():
        if inp.tag != 'input' or inp.attrs.get('type', '').lower() != 'checkbox':
            continue
        name, val = inp.attrs.get('name', ''), inp.attrs.get('value', '').strip()
        label = inp.parent
        while label is not None and label.tag not in ('label', 'li'):
            label = label.parent
        title = re.sub(r'\s+', ' ', (label.text() if label is not None else '')).strip()
        if name == 'theme':
            title = re.sub(r'^' + re.escape(val) + r'\s+', '', title)
            if '.' not in val:
                kes.setdefault(val, {'code': val, 'name': title, 'themes': []})['name'] = title
            else:
                kes.setdefault(val.split('.')[0], {'code': val.split('.')[0], 'name': '', 'themes': []})['themes'].append(
                    {'code': val, 'name': title})
        elif name:
            filters.setdefault(name, {})[val] = title
    order = sorted(kes.values(), key=lambda s: [int(x) for x in re.findall(r'\d+', s['code'])] or [0])
    return order, filters


# ---------- картинки ----------

def image_resolver(client, exam, key, page_base, script_base, offline):
    """Скачивает картинку при первом упоминании и возвращает путь от корня сайта.
    Пути из ShowPictureQ(...) отсчитываются от qfiles_location, из <img> — от страницы."""
    folder = IMG / f'{exam}-{key}'

    def resolve(src, script=False):
        src = src.strip()
        if not src or src.startswith('data:'):
            return None
        url = urllib.parse.urljoin(script_base if script else page_base, src)
        name = re.sub(r'[^A-Za-z0-9_.-]+', '_', urllib.parse.unquote(url.rsplit('/', 1)[-1]))[-80:]
        if not re.search(r'\.(png|gif|jpe?g|svg|webp|bmp)$', name, re.I):
            name = hashlib.sha1(url.encode()).hexdigest()[:16] + '.png'
        # Одинаковые имена в разных папках: добавляем хэш пути
        name = hashlib.sha1(url.encode()).hexdigest()[:6] + '-' + name
        path = folder / name
        if not path.exists() and not offline:
            try:
                data = client.fetch(url, raw=True)
            except (FipiError, urllib.error.HTTPError) as e:  # битая картинка не должна останавливать загрузку
                print(f'  картинка не скачалась: {url} ({e})', flush=True)
                return None
            folder.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return path.relative_to(ROOT).as_posix() if path.exists() else None
    # Файлы к заданиям не скачиваем — нужен только их адрес на сайте ФИПИ
    resolve.url = lambda src, script=False: urllib.parse.urljoin(script_base if script else page_base, src.strip())
    return resolve


# ---------- загрузка предмета ----------

def crawl(exam, key, client, offline=False, pagesize=100):
    title, proj = SUBJECTS[exam][key]
    cache = CACHE / f'{exam}-{key}'
    cache.mkdir(parents=True, exist_ok=True)

    def page(name, fetch):
        f = cache / name
        if f.exists():
            return f.read_text('utf-8')
        if offline:
            return None
        html = fetch()
        # «Ошибка: Нет прав доступа» и прочие короткие ответы вместо страницы — не кэшируем
        err = re.search(r'Ошибка:\s*([^<]+)', html[:2000]) if len(html) < 3000 else None
        if err:
            raise FipiError(f'сайт ответил «{err.group(1).strip()}» на {name}')
        f.write_text(html, 'utf-8')
        return html

    if not offline:
        client.fetch('index.php')  # сессия
    project = page('project.html', lambda: client.fetch('index.php', {'proj': proj}))
    if project is None:
        sys.exit(f'{exam}-{key}: нет кэша страниц, запустите без --offline')
    kes, filters = parse_project(project)
    page_base = urllib.parse.urljoin(BASE[exam], 'questions.php')
    # Картинки в условиях: qfiles_location + путь из ShowPictureQ (обычно '../../' → корень сайта)
    first = page(f'p{pagesize}-0000.html', lambda: client.fetch(
        'questions.php', {'proj': proj, 'page': 0, 'pagesize': pagesize, 'init_filter_themes': 1}))
    if first is None:
        sys.exit(f'{exam}-{key}: нет кэша страниц, запустите без --offline')
    loc = re.search(r"qfiles_location\s*=\s*'([^']*)'", first)
    resolve = image_resolver(client, exam, key, page_base, urllib.parse.urljoin(page_base, loc.group(1) if loc else ''), offline)
    tasks, total, size, groups, pending = parse_questions(first, resolve)
    by_id = {t['id']: t for t in tasks}
    # Сервер может урезать размер страницы — дальше листаем тем размером, что он назвал
    size = size or len(tasks) or pagesize
    n = 1
    while total and len(by_id) < total:
        html = page(f'p{size}-{n:04d}.html', lambda: client.fetch(
            'questions.php', {'proj': proj, 'page': n, 'pagesize': size}))
        if html is None:
            print(f'  {exam}-{key}: в кэше нет страницы {n}, собрано {len(by_id)} из {total}')
            break
        got, _, _, more, pending = parse_questions(html, resolve, pending)
        for g, v in more.items():
            groups.setdefault(g, v)
        new = [t for t in got if t['id'] not in by_id]
        if not new:
            break
        for t in new:
            by_id[t['id']] = t
        n += 1
        print(f'  {exam}-{key}: {len(by_id)}/{total}', end='\r', flush=True)
    # Группа без общего текста (задачи про игру в информатике): условие дано в первом
    # задании группы, остальные на него ссылаются — оно и становится общим текстом
    for g in sorted({t['group'] for t in by_id.values() if t.get('group') and t['group'] not in groups}):
        first = min((t for t in by_id.values() if t.get('group') == g), key=lambda t: t['gn'])
        if first['gn'] == 1:
            groups[g] = {k: first[k] for k in ('text', 'html', 'img', 'files') if k in first}
            groups[g]['from'] = first['id']
    # Запись для аудирования прикреплена к первому заданию группы, а слушать её нужно во всех
    for t in by_id.values():
        if t.get('audio') and t.get('group') in groups:
            g = groups[t['group']]
            g['audio'] = list(dict.fromkeys(g.get('audio', []) + t['audio']))
    lost = sorted({t['group'] for t in by_id.values() if t.get('group') and t['group'] not in groups})
    # Картинки, на которые больше ничего не ссылается (старый разбор, переименования), — удаляем
    folder = IMG / f'{exam}-{key}'
    if total and len(by_id) >= total and folder.exists():
        used = {ROOT / src for x in list(by_id.values()) + list(groups.values()) for src in x.get('img', [])}
        extra = [f for f in folder.iterdir() if f not in used]
        for f in extra:
            f.unlink()
        if extra:
            print(f'  {exam}-{key}: удалено лишних файлов картинок {len(extra)}')
    print(f'  {exam}-{key}: заданий {len(by_id)} из {total}, общих текстов {len(groups)}'
          + (f', не найден текст групп {lost}' if lost else '') + ' ' * 10)

    # Позиция задания в КИМ, если банк даёт такой фильтр (у части предметов)
    try:
        for val in filters.get('qpos', {}):
            p, seen = 0, set()
            while True:
                html = page(f'qpos-{val}-{p:04d}.html', lambda: client.fetch('questions.php', data={
                    'search': 1, 'proj': proj, 'page': p, 'pagesize': size, 'qpos': val, 'theme': '',
                    'qkind': '', 'qlevel': '', 'qsstruct': '', 'qid': '', 'zid': '', 'solved': '',
                    'favorite': '', 'blind': '', 'crtm': int(time.time())}))
                if html is None:
                    break
                got, cnt, _, _, _ = parse_questions(html, lambda s, script=False: None)
                fresh = [t['id'] for t in got if t['id'] not in seen]
                seen.update(fresh)
                if not fresh or (cnt and len(seen) >= cnt):
                    break
                p += 1
            for qid in seen:
                if qid in by_id:
                    by_id[qid]['pos'] = val
    except FipiError as e:
        print(f'  {exam}-{key}: позиции в КИМ не получены: {e}')
    if filters.get('qpos'):
        print(f'  {exam}-{key}: позиция в КИМ у {sum(1 for t in by_id.values() if "pos" in t)} заданий')

    return {'exam': exam, 'key': key, 'title': title, 'proj': proj, 'count': total,
            'fetched': time.strftime('%Y-%m-%d'), 'kes': kes, 'filters': filters, 'groups': groups,
            'tasks': sorted(by_id.values(), key=lambda t: t['id'])}


def main():
    ap = argparse.ArgumentParser(description='Загрузка открытого банка ФИПИ')
    ap.add_argument('subjects', nargs='*', help='ключи предметов (по умолчанию все)')
    ap.add_argument('--exam', choices=['ege', 'oge'], default='ege')
    ap.add_argument('--offline', action='store_true', help='только из кэша data/fipi-cache')
    ap.add_argument('--insecure', action='store_true', help='не проверять сертификат ФИПИ')
    ap.add_argument('--pagesize', type=int, default=100)
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args()
    reg = SUBJECTS[args.exam]
    if args.list:
        for k, (t, _) in reg.items():
            print(f'{k:12} {t}')
        return
    keys = args.subjects or list(reg)
    bad = [k for k in keys if k not in reg]
    if bad:
        sys.exit(f'Неизвестные предметы: {bad}. Список: --list')
    client = Client(args.exam, insecure=args.insecure)
    OUT.mkdir(parents=True, exist_ok=True)
    for key in keys:
        print(f'{args.exam}-{key}: {reg[key][0]}', flush=True)
        try:
            data = crawl(args.exam, key, client, offline=args.offline, pagesize=args.pagesize)
        except FipiError as e:  # скачанное лежит в кэше: повторный запуск продолжит с того же места
            print(f'  {args.exam}-{key}: {e}. Запустите ещё раз — продолжится с места остановки.', flush=True)
            continue
        f = OUT / f'{args.exam}-{key}.json'
        f.write_text(json.dumps(data, ensure_ascii=False, indent=0, separators=(',', ':')) + '\n', 'utf-8')
        kinds = {}
        for t in data['tasks']:
            kinds[t['kind']] = kinds.get(t['kind'], 0) + 1
        print(f'  → {f.relative_to(ROOT)}: {kinds}', flush=True)


if __name__ == '__main__':
    main()
