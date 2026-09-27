// Проверка адресов сайта без браузера: статус, перенаправления, заголовки кэша, сжатие, размер, время,
// форма ответов API (только GET, ничего не записывает). BASE=… OUT=… node tools/audit/http.mjs
// За прокси: NODE_USE_ENV_PROXY=1 (Node ≥ 22.21), иначе fetch идёт мимо HTTPS_PROXY.
import { writeFileSync, mkdirSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const BASE = (process.env.BASE || 'https://econcards.kqrulev.workers.dev').replace(/\/+$/, '');
const OUT = resolve(process.env.OUT || join(dirname(fileURLToPath(import.meta.url)), 'out', 'last'));
mkdirSync(join(OUT, 'results'), { recursive: true });

const rows = [];
async function get(p, { headers = {}, expect, note = '', json = false } = {}) {
  const t0 = Date.now();
  let r, body = null, err = null;
  try {
    r = await fetch(BASE + p, { redirect: 'manual', headers: { 'Accept-Encoding': 'br, gzip', 'User-Agent': 'econcards-audit', ...headers } });
    const buf = Buffer.from(await r.arrayBuffer());
    body = buf;
  } catch (e) { err = String(e.cause?.code || e.message).slice(0, 160); }
  const ms = Date.now() - t0;
  const h = k => r?.headers.get(k) || '';
  const row = { path: p, note, status: r?.status ?? null, ms, bytes: body?.length ?? 0, location: h('location'), type: h('content-type'), cache: h('cache-control'),
    etag: h('etag'), encoding: h('content-encoding'), cfCache: h('cf-cache-status'), err, ok: true, problems: [] };
  if (json && body && r?.ok) { try { row.json = JSON.parse(body.toString('utf8')); } catch { row.problems.push('ответ не JSON'); } }
  if (expect) {
    const want = [].concat(expect.status ?? []);
    if (want.length && !want.includes(row.status)) row.problems.push(`статус ${row.status}, ожидали ${want.join('/')}`);
    if (expect.type && !new RegExp(expect.type).test(row.type)) row.problems.push(`тип «${row.type}», ожидали ${expect.type}`);
  }
  if (err) row.problems.push('ошибка сети: ' + err);
  row.ok = !row.problems.length;
  rows.push(row);
  console.log(`${row.ok ? '✓' : '✗'} ${String(row.status).padEnd(4)} ${p.padEnd(40)} ${String(ms).padStart(5)}ms ${String(row.bytes).padStart(8)}B ${row.encoding || '-'} ${row.cache || '-'}${row.location ? ' → ' + row.location : ''}${row.problems.length ? '  ✗ ' + row.problems.join('; ') : ''}`);
  return row;
}

// Страницы сайта
const HTML = { status: 200, type: 'text/html' };
for (const p of ['/', '/?about', '/studio/', '/cabinet/', '/login.html', '/offer.html', '/privacy.html', '/offline.html']) await get(p, { expect: HTML });
// Перенаправления Cloudflare (html_handling): каждое — лишний круг по сети на телефоне
for (const p of ['/studio', '/cabinet', '/login', '/parent/', '/parent', '/index.html']) await get(p, { note: 'перенаправление?' });
// Несуществующая страница: 404 (или своя страница 404, если включена)
await get('/no-such-page-audit', { expect: { status: [404] }, note: 'нет такой страницы' });
// Статика: скрипты, стили, шрифты, воркер
for (const p of ['/app.js', '/lib.js', '/account.js', '/landing.js', '/app.css', '/sw.js', '/manifest.webmanifest', '/studio/studio.js', '/cabinet/cabinet.js', '/login.js', '/fonts/nunito-cyrillic.woff2', '/fonts/unbounded-cyrillic.woff2', '/vendor/qrcode.js']) await get(p, { expect: { status: 200 } });
// Библиотека: список, бесплатная часть ЕГЭ, маленькие примеры
const idx = await get('/packs/index.json', { expect: { status: 200, type: 'json' }, json: true });
const libIds = (idx.json?.packs || idx.json || []).map?.(x => x.id || x.file || x).filter(Boolean) || [];
const lib = {};
for (const id of ['ege-rus', 'ege-math']) {
  const full = await get(`/packs/${id}.json`, { expect: { status: 200, type: 'json' }, json: true, note: 'гостю — бесплатная часть' });
  const free = await get(`/packs/${id}.free.json`, { json: true, note: 'заранее собранная бесплатная часть' });
  const cards = j => (j?.cards || []).length, topics = j => (j?.topics || []).length;
  lib[id] = { guestCards: cards(full.json), guestTopics: topics(full.json), freeFile: free.status, freeCards: cards(free.json), same: full.json && free.json ? JSON.stringify(full.json) === JSON.stringify(free.json) : null };
  delete full.json; delete free.json;
  // Повторная загрузка с ETag — должен прийти 304
  if (full.etag) await get(`/packs/${id}.json`, { headers: { 'If-None-Match': full.etag }, note: 'повтор с If-None-Match' });
}
for (const p of ['/packs/sample-rus.json', '/packs/sample-math.json']) { const r = await get(p, { json: true, note: 'пример для студии' }); if (r.json) { r.cards = (r.json.cards || []).length; r.topics = (r.json.topics || []).length; delete r.json; } }
// API без входа: только чтение
const prov = await get('/auth/providers', { expect: { status: 200, type: 'json' }, json: true });
const prices = await get('/pay/prices', { expect: { status: 200, type: 'json' }, json: true });
await get('/me', { expect: { status: [401, 403] }, note: 'без входа — отказ' });
await get('/packs/zzzz1234', { expect: { status: [404] }, note: 'неизвестный тренажёр' });
await get('/packs/zzzz1234/progress', { expect: { status: [401, 403, 404] }, note: 'чужой прогресс без ключа' });

const summary = {
  base: BASE, at: new Date().toISOString(), total: rows.length, bad: rows.filter(r => !r.ok).length,
  providers: prov.json || null, prices: prices.json || null, libraryIndex: libIds, library: lib,
  redirects: rows.filter(r => r.status >= 300 && r.status < 400).map(r => `${r.path} → ${r.status} ${r.location}`),
  uncompressed: rows.filter(r => r.status === 200 && r.bytes > 2048 && /javascript|css|json|html/.test(r.type) && !r.encoding).map(r => r.path),
};
delete prov.json; delete prices.json;
writeFileSync(join(OUT, 'results', 'http.json'), JSON.stringify({ summary, rows }, null, 1));
console.log('\nВсего', rows.length, 'проблем', summary.bad, '| перенаправления:', summary.redirects.join(', ') || 'нет', '| без сжатия:', summary.uncompressed.join(', ') || 'нет');
console.log('Способы входа:', JSON.stringify(summary.providers), '| библиотека:', JSON.stringify(lib));
