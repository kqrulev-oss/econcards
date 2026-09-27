// Сводный отчёт по результатам tools/audit/*: OUT=… node tools/audit/report.cjs > OUT/report.md
const fs = require('fs');
const path = require('path');
const OUT = path.resolve(process.env.OUT || path.join(__dirname, 'out', 'last'));
const R = path.join(OUT, 'results');
const read = f => { try { return JSON.parse(fs.readFileSync(path.join(R, f), 'utf8')); } catch { return null; } };
const files = fs.existsSync(R) ? fs.readdirSync(R) : [];
const esc = s => String(s ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
const out = [];
const P = (...a) => out.push(...a);

const http = read('http.json');
const journeys = files.filter(f => /^journeys-.*\.json$/.test(f)).map(read).filter(Boolean);
const crawls = files.filter(f => /^crawl-.*\.json$/.test(f)).map(read).filter(Boolean);
const offline = files.filter(f => /^offline-\d+\.json$/.test(f)).map(read).filter(Boolean);
const perf = files.filter(f => /^perf-\d+\.json$/.test(f)).map(f => ({ W: f.match(/\d+/)[0], rows: read(f) || [] }));

// Проблемы шага пути / элемента обхода
const stepFlags = s => [s.fail && 'не вышло: ' + s.fail, s.errs?.length && `ошибки ×${s.errs.length}`, s.modals?.length && `окно висит ×${s.modals.length}`, s.blank && 'пустой экран',
  s.loading && 'вечная загрузка', s.overflowX && 'горизонтальная прокрутка', s.hiddenVisible?.length && 'видно скрытое: ' + s.hiddenVisible.join(',')].filter(Boolean);
const ctlFlags = c => [c.result?.startsWith('crash') && c.result, c.errs?.length && 'ошибки: ' + c.errs.join(' · '), c.modals?.length && c.type !== 'modal' && 'окно осталось висеть',
  c.blank && 'пустой экран', c.loading && 'вечная загрузка', c.timedOut && 'не успокоилась за 15 с', c.back && !c.back.same && `«назад» → ${c.back.url}`, c.back?.modals && 'окно после «назад»',
  c.type === 'nothing' && 'ничего не происходит', c.clickErr && 'не нажимается' + (c.coveredBy ? ` (перекрыта: ${c.coveredBy})` : ''), c.dups?.length && 'повторные запросы: ' + c.dups.join(', '),
  c.reload && (c.reload.blank || c.reload.loading || c.reload.errs.length) && 'после перезагрузки: ' + [c.reload.blank && 'пусто', c.reload.loading && 'загрузка', ...c.reload.errs].filter(Boolean).join(', '),
  c.overflowX && 'горизонтальная прокрутка', c.hiddenVisible?.length && 'видно скрытое'].filter(Boolean);

P(`# Проверка живого сайта`, '', `Адрес: ${http?.summary?.base || crawls[0]?.base || journeys[0]?.base || '?'} · время: ${http?.summary?.at || new Date().toISOString()}`, '',
  'Проверка только читает: записи на сервер (вход, отправка прогресса, оплата, ИИ, бот) браузер не отправлял — такие попытки перечислены в разделе 6.', '');

// ---- Коротко
P('## Коротко', '');
if (http) {
  const s = http.summary;
  P(`- **Адреса:** ${s.total} проверено, проблем — ${s.bad}.${s.redirects.length ? ` Перенаправления: ${s.redirects.join('; ')}.` : ''}${s.uncompressed.length ? ` Без сжатия: ${s.uncompressed.join(', ')}.` : ''}`);
  if (s.providers) P(`- **Способы входа на сервере:** ${Object.entries(s.providers).map(([k, v]) => `${k} ${v ? '✓' : '✗'}`).join(', ')}.`);
  if (s.library) P(`- **Библиотека для гостя:** ${Object.entries(s.library).map(([id, x]) => `${id}: ${x.guestTopics} тем / ${x.guestCards} карточек${x.freeFile === 200 ? `, готовый файл ${x.same ? 'совпадает' : 'НЕ совпадает'}` : ''}`).join('; ')}.`);
}
for (const j of journeys) {
  for (const [k, steps] of Object.entries(j.journeys)) {
    if (!Array.isArray(steps)) { P(`- **Путь ${k} (${j.W}, ${j.scheme}):** сбой — ${steps.crash}`); continue; }
    const bad = steps.filter(s => stepFlags(s).length);
    P(`- **Путь ${k} (${j.W}, ${j.scheme}):** ${steps.length} шагов, с проблемами — ${bad.length}${bad.length ? ': ' + bad.map(s => `${s.n} «${s.label}»`).join(', ') : ''}.`);
  }
}
if (crawls.length) {
  const all = crawls.flatMap(c => c.pages.flatMap(p => p.controls.map(x => ({ ...x, persona: c.persona, W: c.W, page: p.url }))));
  const tested = all.filter(c => !c.result);
  const bad = tested.filter(c => ctlFlags(c).length);
  P(`- **Обход:** ${crawls.length} прогонов, ${crawls.reduce((n, c) => n + c.pages.length, 0)} страниц, ${tested.length} ссылок и кнопок нажато (${all.filter(c => c.result === 'dup').length} повторов пропущено), с проблемами — ${bad.length}.`);
}
for (const o of offline) {
  for (const [mode, m] of Object.entries(o.modes)) {
    const bad = m.steps.filter(s => s.verdict && s.verdict !== 'ok');
    P(`- **Офлайн (${mode}, ${o.W}):** ${bad.length ? 'проблемы — ' + bad.map(s => `${s.label}: ${s.verdict}`).join('; ') : 'всё открывается как задумано'}${m.apiCached.length ? `; ответы API в кэше: ${m.apiCached.join(', ')}` : ''}.`);
  }
}
const blockedAll = [...journeys.flatMap(j => Object.values(j.journeys).flatMap(s => Array.isArray(s) ? s.flatMap(x => x.blocked || []) : [])), ...crawls.flatMap(c => (c.blocked || []).map(b => `${b.method} ${b.path}`))];
P(`- **Попытки записи (заблокированы проверкой):** ${blockedAll.length}.`, '');

// ---- 1. Адреса
if (http) {
  P('## 1. Адреса', '', '| Адрес | Статус | мс | Байт | Сжатие | Cache-Control | Замечания |', '|---|---|---|---|---|---|---|');
  for (const r of http.rows) P(`| ${esc(r.path)}${r.note ? ` <br><sub>${esc(r.note)}</sub>` : ''} | ${r.status ?? '—'}${r.location ? ' → ' + esc(r.location) : ''} | ${r.ms} | ${r.bytes} | ${r.encoding || '—'} | ${esc(r.cache) || '—'} | ${r.problems.length ? '✗ ' + esc(r.problems.join('; ')) : ''}${r.cards != null ? `${r.topics} тем, ${r.cards} карточек` : ''} |`);
  P('');
}

// ---- 2. Пути
if (journeys.length) {
  P('## 2. Пути', '');
  for (const j of journeys) for (const [k, steps] of Object.entries(j.journeys)) {
    P(`### ${k} — ${j.W} px, ${j.scheme}`, '');
    if (!Array.isArray(steps)) { P(`Сбой: ${steps.crash}`, ''); continue; }
    P('| № | Шаг | Адрес | Заголовок | Проблемы / заметки | Скриншот |', '|---|---|---|---|---|---|');
    for (const s of steps) P(`| ${s.n} | ${esc(s.label)} | ${esc(s.url)} | ${esc(s.head)} | ${esc([...stepFlags(s), ...(s.errs || []), s.note].filter(Boolean).join(' · '))} | ${s.file ? `\`${s.file}\`` : ''} |`);
    P('');
  }
}

// ---- 3. Обход
if (crawls.length) {
  P('## 3. Обход ссылок и кнопок', '');
  P('| Роль, ширина | Страница | Загрузка, мс | Статус | Ошибки при загрузке |', '|---|---|---|---|---|');
  for (const c of crawls) for (const p of c.pages) P(`| ${c.persona} ${c.W} | ${esc(p.url)} → ${esc(p.finalUrl)} | ${p.loadMs} | ${p.status ?? ''} | ${esc((p.errs || []).join(' · ')) || ''}${p.blank ? ' пустой экран' : ''}${p.loading ? ' вечная загрузка' : ''} |`);
  P('');
  const bad = crawls.flatMap(c => c.pages.flatMap(p => p.controls.filter(x => !x.result && ctlFlags(x).length).map(x => ({ ...x, persona: c.persona, W: c.W, page: p.url }))));
  if (bad.length) {
    P('**Элементы с проблемами**', '', '| Роль, ширина | Страница | Элемент | Что произошло | Проблемы |', '|---|---|---|---|---|');
    for (const x of bad) P(`| ${x.persona} ${x.W} | ${esc(x.page)} | ${x.tag} «${esc(x.text)}» ${esc(x.href || '')} | ${x.type} → ${esc(x.to)} (${x.ms} мс) | ${esc(ctlFlags(x).join(' · '))} |`);
    P('');
  } else P('Проблемных элементов нет.', '');
  const slow = crawls.flatMap(c => c.pages.flatMap(p => p.controls.filter(x => x.ms > 2500 && !x.result).map(x => ({ ...x, persona: c.persona, W: c.W, page: p.url })))).sort((a, b) => b.ms - a.ms).slice(0, 15);
  if (slow.length) { P('**Самые долгие переходы при обходе (обычная сеть)**', '', '| Мс | Роль | Страница | Элемент → куда | Запросов / КБ |', '|---|---|---|---|---|'); for (const x of slow) P(`| ${x.ms} | ${x.persona} ${x.W} | ${esc(x.page)} | «${esc(x.text)}» → ${esc(x.to)} | ${x.reqN} / ${x.kb} |`); P(''); }
}

// ---- 4. Офлайн
if (offline.length) {
  P('## 4. Офлайн (service worker)', '');
  for (const o of offline) for (const [mode, m] of Object.entries(o.modes)) {
    P(`### ${mode === 'visited' ? 'Страницы открывали онлайн' : 'Онлайн открыли только главную'} — ${o.W} px`, '', `В кэше ${m.cachedCount} файлов (${m.cacheNames.join(', ')}); ответы API в кэше: ${m.apiCached.join(', ') || 'нет'}.`, '',
      '| Шаг | Адрес | Итог | Что на экране | Скриншот |', '|---|---|---|---|---|');
    for (const s of m.steps) P(`| ${esc(s.label)} | ${esc(s.url)} | ${s.verdict || ''}${s.fail ? ' (' + esc(s.fail) + ')' : ''} | ${esc(s.head || s.text || '')} | ${s.file ? `\`${s.file}\`` : ''} |`);
    P('');
  }
}

// ---- 5. Скорость
for (const { W, rows } of perf) {
  if (!rows.length) continue;
  const modes = [...new Set(rows.map(r => r.mode))];
  P(`## 5. Скорость — ${W} px`, '', 'Первый экран / полностью, мс. «3G» — медленная сеть (задержка 562 мс, 1,44 Мбит/с) через прокси, замедляет и service worker.', '',
    `| Переход | ${modes.join(' | ')} | Запросов / КБ (${modes.includes('3G') ? '3G' : modes[0]}) | Замечания |`, `|---|${modes.map(() => '---|').join('')}---|---|`);
  for (const name of [...new Set(rows.map(r => r.name))]) {
    const by = Object.fromEntries(rows.filter(r => r.name === name).map(r => [r.mode, r]));
    const base = by['3G'] || by[modes[0]] || {};
    const notes = [...new Set(Object.values(by).flatMap(r => [r.error && 'сбой: ' + r.error, ...(r.dups || []).map(d => 'повтор ' + d), ...(r.errs || []), ...(r.big || []).map(x => 'тяжёлое ' + x)]).filter(Boolean))];
    P(`| ${esc(name)} | ${modes.map(m => by[m] ? (by[m].error ? 'сбой' : `${by[m].first ?? '—'} / ${by[m].settle ?? '—'}${by[m].timedOut ? '+' : ''}`) : '—').join(' | ')} | ${base.n ?? '—'} / ${base.kb ?? '—'} | ${esc(notes.join(' · '))} |`);
  }
  P('');
}

// ---- 6. Попытки записи
P('## 6. Попытки записи на сервер (заблокированы проверкой)', '');
const cnt = {};
for (const b of blockedAll) cnt[b] = (cnt[b] || 0) + 1;
P(Object.keys(cnt).length ? Object.entries(cnt).sort((a, b) => b[1] - a[1]).map(([k, n]) => `- ${k} ×${n}`).join('\n') : 'Не было.', '',
  'Ожидаемы: POST /auth/tg/start и /auth/oauth/* (кнопки входа). Другие — повод посмотреть, кто и зачем пишет без входа.', '');

// ---- 7. Уникальные ошибки
const errs = {};
const addErr = (e, where) => { const k = e.replace(/\d{3,}/g, '#'); (errs[k] = errs[k] || new Set()).add(where); };
for (const j of journeys) for (const [k, steps] of Object.entries(j.journeys)) if (Array.isArray(steps)) for (const s of steps) for (const e of s.errs || []) addErr(e, `путь ${k} ${j.W}: ${s.label}`);
for (const c of crawls) for (const p of c.pages) { for (const e of p.errs || []) addErr(e, `${c.persona} ${c.W}: загрузка ${p.url}`); for (const x of p.controls) for (const e of x.errs || []) addErr(e, `${c.persona} ${c.W}: ${p.url} «${x.text}»`); }
P('## 7. Ошибки (уникальные)', '');
P(Object.keys(errs).length ? Object.entries(errs).map(([e, where]) => `- \`${esc(e).slice(0, 200)}\` — ${[...where].slice(0, 4).map(esc).join('; ')}${where.size > 4 ? ` и ещё ${where.size - 4}` : ''}`).join('\n') : 'Ошибок нет.', '');

process.stdout.write(out.join('\n') + '\n');
