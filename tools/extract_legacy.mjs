// Одноразовый перенос данных из старых приложений (EconCards, Сотка, Ударение,
// Сочинение) в data/source/*.json. Запуск: node tools/extract_legacy.mjs
// Старые приложения удалены: чтобы запустить заново, достань их из коммита
// 92fed0f (git checkout 92fed0f -- index.html sotka udarenie essay).
import fs from 'node:fs';
import vm from 'node:vm';

const out = (name, obj) => {
  fs.writeFileSync(`data/source/${name}.json`, JSON.stringify(obj, null, 1) + '\n');
  console.log('data/source/' + name + '.json');
};
const tag = (html, attrs) => {
  const m = html.match(new RegExp(`<script[^>]*${attrs}[^>]*>([\\s\\S]*?)</script>`));
  if (!m) throw new Error('нет блока ' + attrs);
  return m[1];
};

// Вырезает литерал «const NAME = …;» из исходника: сканирует скобки,
// пропуская строки и шаблоны. Данные в приложениях — чистые литералы.
function literal(src, name, ctx = {}) {
  const start = src.search(new RegExp(`(?:^|\\n)\\s*const ${name}\\s*=`));
  if (start < 0) throw new Error('нет const ' + name);
  let i = src.indexOf('=', start) + 1;
  while (/\s/.test(src[i])) i++;
  const from = i;
  let depth = 0;
  for (; i < src.length; i++) {
    const c = src[i];
    if (c === '"' || c === "'" || c === '`') {
      for (i++; src[i] !== c; i++) if (src[i] === '\\') i++;
    } else if (c === '/' && src[i + 1] === '/') {
      i = src.indexOf('\n', i);
    } else if ('[{('.includes(c)) depth++;
    else if (']})'.includes(c)) { depth--; if (!depth) break; }
  }
  return vm.runInNewContext('(' + src.slice(from, i + 1) + ')', ctx);
}

// EconCards: карточки олимпиад и ЕГЭ, курсы теории
const econ = fs.readFileSync('index.html', 'utf8');
out('econcards', JSON.parse(tag(econ, 'id="appdata"')));
out('econ-courses', JSON.parse(tag(econ, 'id="coursedata"')));

// Сотка: банк заданий ЕГЭ по русскому, уроки, структура экзамена
const sotka = fs.readFileSync('sotka/index.html', 'utf8');
out('sotka-bank', JSON.parse(tag(sotka, 'id="bankdata"')));
out('sotka-lessons', JSON.parse(tag(sotka, 'id="lessondata"')));
out('sotka-exam', JSON.parse(tag(sotka, 'id="examdata"')));

// Ударение: словарь по частям речи и правила (лежат в шаблоне бандла)
const udar = fs.readFileSync('udarenie/index.html', 'utf8');
const tpl = JSON.parse(tag(udar, 'type="__bundler/template"'));
out('udarenie', { rules: literal(tpl, 'RULES'), data: literal(tpl, 'DATA') });

// Сочинение: теория, клише, критерии, примеры
const essay = fs.readFileSync('essay/index.html', 'utf8');
// Уроки собраны через хелперы подсветки — отдаём им те же реализации
const essayCtx = {
  mk: (k, t) => '<span class="mk mk-' + k + '">' + t + '</span>',
  ic: () => '',
};
const essayData = {};
for (const n of ['PARTS', 'SCHOOL', 'BLOCKS', 'REF', 'EGE', 'FINAL', 'CRIT_EGE', 'CRIT_FINAL', 'MODELS'])
  essayData[n] = literal(essay, n, essayCtx);
out('essay', essayData);
