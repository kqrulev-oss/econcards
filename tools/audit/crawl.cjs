// Обход всех ссылок и кнопок без входа в аккаунт: node tools/audit/crawl.cjs <persona> <width>
// persona: guest (чистый браузер), guest-draft (черновик в студии на устройстве), library (занимался библиотекой ЕГЭ).
// Для каждого элемента: свежая загрузка страницы → клик → куда ведёт, тип перехода, время, запросы/КБ,
// ошибки, висящие модалки, пустой экран/вечная загрузка, «назад» возвращает ли на тот же экран, перезагрузка адреса.
// Одинаковые элементы (шапка, подвал) на разных страницах проверяются один раз.
const { BASE, ORIGIN, OUT, launch, newCtx, watch, settle, inspect, resetStore, saveJson, blocked } = require('./lib.cjs');
const fs = require('fs');
const path = require('path');

const persona = process.argv[2] || 'guest';
const W = +(process.argv[3] || 375);
const day = (d = new Date()) => Math.floor((d - d.getTimezoneOffset() * 60000) / 864e5);
const t = day();
const GD = 'gdraft01';
const guestDraft = { packs: { [GD]: { id: GD, title: 'Мой черновик', tutor: '', subject: '', color: '#5B3DF5', daily: 10, topics: [{ id: 'g1', title: 'Тема 1' }], theory: [], cards: [{ id: 'c1', t: 'g1', k: 'one', q: 'Вопрос?', o: [{ id: 'а', t: 'да' }, { id: 'б', t: 'нет' }], a: 'а' }], edited: Date.now(), published: 0 } }, keys: { [GD]: 'k'.repeat(24) }, deleted: {} };
const libProg = { cards: {}, log: { [t]: { d: 5, ok: 3, n: 5 }, [t - 1]: { d: 8, ok: 6, n: 4 } }, errs: [], sid: 'sidaudit01', name: '', synced: 0, syncedN: 0 };

const PERSONAS = {
  guest: { store: {}, pages: ['/', '/?about', '/#/library', '/login.html', '/login.html?role=parent', '/login.html?next=%2Fcabinet%2F', '/studio/', '/studio/#/sample', '/cabinet/', '/cabinet/#parent', '/parent/', '/offer.html', '/privacy.html', '/?p=ege-rus', '/?p=ege-math', '/?t=zzzz1234', '/offline.html'] },
  'guest-draft': { store: { 'zd-studio': guestDraft }, pages: ['/studio/', ...['cards', 'add', 'course', 'students', 'settings', 'publish'].map(x => `/studio/#/p/${GD}/${x}`)] },
  library: { store: { 'zd-prog:ege-rus': libProg, 'zd-recent': [{ ref: 'ege-rus', title: 'ЕГЭ: русский язык' }] },
    pages: ['#/', '#/topic/task-4', '#/topic/task-26', '#/me', '#/library', '#/go'].map(h => `/?p=ege-rus${h}`).concat(['/', '/cabinet/']) },
};
// Не нажимаем: выбор файла, оплата
const SKIP = c => c.fileInput || /pay-opt/.test(c.cls);

const ENUM = () => {
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && !e.closest('[hidden]'); };
  const els = [...document.querySelectorAll('a[href], button, [role=tab], label.btn, summary')].filter(e => vis(e) && !e.closest('.toast'));
  const out = [], count = {}, exactN = {};
  for (const e of els) {
    const tag = e.tagName.toLowerCase();
    const vtext = (e.innerText || '').replace(/\s+/g, ' ').trim();
    const text = (vtext || e.getAttribute('aria-label') || e.querySelector('img[alt]')?.alt || e.title || '').replace(/\s+/g, ' ').trim().slice(0, 60);
    const href = e.getAttribute('href');
    const cls = typeof e.className === 'string' ? e.className.trim().split(/\s+/).slice(0, 3).join('.') : '';
    const exact = [tag, text, href || '', e.id || ''].join('|');
    exactN[exact] = (exactN[exact] || 0) + 1;
    const kind = [tag, text.replace(/\d+/g, '#').slice(0, 40), (href || '').replace(/\d+/g, '#').replace(/[a-z0-9]{8,}/g, 'ID'), cls].join('|');
    count[kind] = (count[kind] || 0) + 1;
    const r = e.getBoundingClientRect();
    out.push({ tag, text, href, id: e.id || '', cls, exact, nth: exactN[exact], kind, kindN: count[kind], inModal: !!e.closest('.modal'), target: e.getAttribute('target') || '',
      noName: !vtext && !e.getAttribute('aria-label') && !e.title, disabled: !!e.disabled, fileInput: !!e.querySelector('input[type=file]'), w: Math.round(r.width), h: Math.round(r.height),
      area: (e.closest('header, nav, footer, .modal, section, .panel')?.tagName || '').toLowerCase() });
  }
  return out;
};
const MARK = d => {
  document.querySelectorAll('[data-audit]').forEach(x => x.removeAttribute('data-audit'));
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && !e.closest('[hidden]'); };
  const els = [...document.querySelectorAll('a[href], button, [role=tab], label.btn, summary')].filter(e => vis(e) && !e.closest('.toast'));
  let n = 0;
  for (const e of els) {
    const tag = e.tagName.toLowerCase();
    const vtext = (e.innerText || '').replace(/\s+/g, ' ').trim();
    const text = (vtext || e.getAttribute('aria-label') || e.querySelector('img[alt]')?.alt || e.title || '').replace(/\s+/g, ' ').trim().slice(0, 60);
    const exact = [tag, text, e.getAttribute('href') || '', e.id || ''].join('|');
    if (exact === d.exact && ++n === d.nth) { e.setAttribute('data-audit', '1'); return true; }
  }
  return false;
};
const STATE = () => ({ url: location.href, origin: performance.timeOrigin, head: (document.querySelector('h1, .brand-title, .login-title, h3')?.innerText || '').trim().slice(0, 60),
  sig: ((document.getElementById('app') || document.body).innerText || '').replace(/\s+/g, ' ').trim().slice(0, 120), modals: document.querySelectorAll('.modal').length });

(async () => {
  const P0 = PERSONAS[persona];
  if (!P0) throw new Error('persona: ' + Object.keys(PERSONAS).join(' | '));
  const b = await launch();
  const ctx = await newCtx(b, { w: W, label: `crawl-${persona}-${W}` });
  let page = await ctx.newPage();
  page.setDefaultTimeout(6000);
  let w = watch(page);
  const results = { persona, W, base: BASE, pages: [] };
  const norm = u => String(u || '').replace(ORIGIN, '');
  const shotsDir = path.join(OUT, 'shots', 'crawl');
  fs.mkdirSync(shotsDir, { recursive: true });
  const reloadSeen = new Set(), kindSeen = new Map();
  const save = () => saveJson(`crawl-${persona}-${W}.json`, results);
  for (const pageUrl of P0.pages) {
    await resetStore(page, P0.store);
    const tStart = Date.now();
    const nav0 = await page.goto(BASE + pageUrl).catch(() => null);
    const st0 = await settle(page, w, { max: 15000 });
    const ins0 = await inspect(page);
    const pageRec = { url: pageUrl, finalUrl: norm(page.url()), status: nav0?.status?.() ?? null, loadMs: st0.settledAt - tStart, timedOut: st0.timedOut, ...ins0, renders: undefined,
      errs: w.errors.filter(e => e.at >= tStart).map(e => e.kind + ': ' + e.text), reqs: w.reqs.filter(r => r.t0 >= tStart && !r.ext).map(r => ({ u: norm(r.url), m: r.method, s: r.status, b: r.bytes, f: r.failed })), controls: [] };
    const shot = path.join(shotsDir, `${persona}-${W}-${pageUrl.replace(/[^\p{L}\p{N}]+/gu, '_').slice(0, 60)}.png`);
    await page.screenshot({ path: shot }).catch(() => {});
    pageRec.shot = path.relative(OUT, shot);
    const all = await page.evaluate(ENUM).catch(() => []);
    const controls = all.filter(c => c.kindN <= 2 && !c.inModal);
    pageRec.enumerated = all.length;
    console.log(`\n== ${persona} ${W} ${pageUrl} → ${pageRec.finalUrl} ${pageRec.status} load ${pageRec.loadMs}ms, ${controls.length}/${all.length} controls${pageRec.errs.length ? ' ERR ' + pageRec.errs.join(' | ').slice(0, 200) : ''}`);
    for (const c of controls) {
      const key = c.kind;
      if (kindSeen.has(key)) { pageRec.controls.push({ ...c, result: 'dup', dupOf: kindSeen.get(key) }); continue; }
      kindSeen.set(key, pageUrl);
      await runControl(pageUrl, c, pageRec);
    }
    results.pages.push(pageRec);
    save();
  }
  results.blocked = blocked();
  save();
  await b.close();
  console.log('DONE', persona, W);

  async function runControl(pageUrl, c, pageRec) {
    const rec = { ...c };
    if (c.disabled) { rec.result = 'disabled'; pageRec.controls.push(rec); return; }
    if (SKIP(c)) { rec.result = 'skipped'; pageRec.controls.push(rec); return; }
    try {
      await resetStore(page, P0.store);
      await page.goto(BASE + pageUrl).catch(() => {});
      await settle(page, w, { max: 12000 });
      const found = await page.evaluate(MARK, c).catch(() => false);
      if (!found) { rec.result = 'not-found-on-fresh-load'; pageRec.controls.push(rec); return; }
      const before = await page.evaluate(STATE);
      const errMark = Date.now();
      w.dialogs = []; w.popups = []; w.navs = []; w.downloads = [];
      const tClick = Date.now();
      let clickErr = null;
      await page.locator('[data-audit="1"]').click({ timeout: 4000 }).catch(e => { clickErr = String(e.message).split('\n')[0].slice(0, 160); });
      if (clickErr) {
        rec.clickErr = clickErr;
        rec.coveredBy = await page.evaluate(() => { const e = document.querySelector('[data-audit="1"]'); if (!e) return null; const r = e.getBoundingClientRect(); const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return top && top !== e && !e.contains(top) ? (top.tagName + '.' + top.className + ' «' + (top.innerText || '').trim().slice(0, 30) + '»') : null; }).catch(() => null);
      }
      const st = await settle(page, w, { max: 15000 });
      const after = await page.evaluate(STATE).catch(() => null);
      const clickAt = await page.evaluate(() => Number(sessionStorage.getItem('__clickAt')) || 0).catch(() => 0) || tClick;
      const ins = await inspect(page);
      const reqs = w.reqs.filter(r => r.t0 >= tClick - 20 && r.t0 <= st.settledAt + 5 && !r.ext);
      const byKey = {};
      for (const r of reqs) { const k = r.method + ' ' + norm(r.url); byKey[k] = (byKey[k] || 0) + 1; }
      const full = after && before && after.origin !== before.origin;
      rec.to = after ? norm(after.url) : norm(page.url());
      rec.type = w.popups.length ? 'popup' : w.downloads.length ? 'download' : full ? (w.navs.length > 1 ? 'full+redirect' : 'full') : (after && after.url !== before.url) ? 'hash' : (after && after.modals > before.modals) ? 'modal' : (after && after.sig !== before.sig) ? 'same-url-screen' : (ins.toasts || []).some(x => x.at >= tClick - 50) ? 'toast' : 'nothing';
      rec.ms = Math.max(0, st.settledAt - clickAt);
      rec.reqN = reqs.length;
      rec.kb = Math.round(reqs.reduce((n, r) => n + (r.bytes || 0), 0) / 102.4) / 10;
      rec.dups = Object.entries(byKey).filter(([, n]) => n > 1).map(([k, n]) => `${k} ×${n}`);
      rec.errs = w.errors.filter(e => e.at >= errMark).map(e => e.kind + ': ' + e.text.slice(0, 160));
      rec.blocked = blocked().filter(x => x.at >= errMark).map(x => `${x.method} ${x.path}`);
      rec.dialogs = w.dialogs.map(d => d.type + ': ' + d.msg.slice(0, 80));
      rec.popups = w.popups.map(p => p.url);
      rec.downloads = w.downloads.map(d => d.name);
      rec.modals = ins.modals; rec.blank = ins.blank; rec.loading = ins.loading; rec.timedOut = st.timedOut; rec.head = ins.head;
      rec.toasts = (ins.toasts || []).filter(x => x.at >= clickAt).map(x => x.t);
      rec.hiddenVisible = ins.hiddenVisible; rec.overflowX = ins.overflowX; rec.scrollY = ins.scrollY;
      for (const p of ctx.pages()) if (p !== page) await p.close().catch(() => {});
      // «Назад» — возвращает ли на тот же экран; модалка после «назад»; перезагрузка адреса назначения
      if (rec.type === 'hash' || rec.type.startsWith('full')) {
        await page.goBack().catch(() => {});
        await settle(page, w, { max: 12000 });
        const back = await page.evaluate(STATE).catch(() => null);
        rec.back = back ? { url: norm(back.url), same: back.url === before.url, sameHead: back.head === before.head, modals: back.modals } : null;
        const dest = rec.to.replace(/[?&]paid=[^&#]*/, '');
        if (!reloadSeen.has(dest) && rec.to.startsWith('/')) {
          reloadSeen.add(dest);
          await page.goForward().catch(() => {});
          await settle(page, w, { max: 12000 });
          const tr = Date.now();
          await page.reload().catch(() => {});
          await settle(page, w, { max: 15000 });
          const ir = await inspect(page);
          rec.reload = { url: norm(ir.url), blank: ir.blank, loading: ir.loading, head: ir.head, errs: w.errors.filter(e => e.at >= tr).map(e => e.kind + ': ' + e.text.slice(0, 120)) };
        }
      }
      const flags = [rec.errs.length && 'ERR', rec.blocked.length && 'WRITE-BLOCKED', rec.modals?.length && rec.type !== 'modal' && 'MODAL-LEFT', rec.blank && 'BLANK', rec.loading && 'LOADING', rec.timedOut && 'TIMEOUT', rec.back && !rec.back.same && 'BACK≠', rec.back?.modals && 'MODAL-AFTER-BACK', rec.type === 'nothing' && 'NOTHING', rec.clickErr && 'NOCLICK', rec.dups.length && 'DUP', rec.reload && (rec.reload.blank || rec.reload.loading || rec.reload.errs.length) && 'RELOAD!'].filter(Boolean).join(' ');
      console.log(`  [${c.tag}] «${c.text.slice(0, 34)}» ${c.href || ''} → ${rec.type} ${rec.to} ${rec.ms}ms ${rec.reqN}req ${rec.kb}KB ${flags}`);
    } catch (e) {
      rec.result = 'crash: ' + String(e.message).slice(0, 160);
      console.log('  CRASH', c.text, rec.result);
      if (page.isClosed()) { page = await ctx.newPage(); page.setDefaultTimeout(6000); w = watch(page); }
    }
    pageRec.controls.push(rec);
  }
})().catch(e => { console.error('FATAL', e); process.exit(1); });
