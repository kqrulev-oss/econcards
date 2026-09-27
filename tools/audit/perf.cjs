// Скорость ключевых переходов без входа в аккаунт. Режимы:
//   сеть     — обычная сеть машины, пустой кэш;
//   3G       — медленная сеть (THROTTLE_PROXY, см. throttle-proxy.mjs), пустой кэш;
//   3G повт. — второй раз (HTTP-кэш браузера);
//   3G+SW    — второй раз с service worker.
// node tools/audit/perf.cjs [width]   (без THROTTLE_PROXY — только «сеть»)
const { BASE, ORIGIN, launch, newCtx, watch, settle, resetStore, blockWrites, saveJson } = require('./lib.cjs');
const W = +(process.argv[2] || 375);
const day = (d = new Date()) => Math.floor((d - d.getTimezoneOffset() * 60000) / 864e5);
const t = day();
const ST = {
  guest: {},
  library: { 'zd-prog:ege-rus': { cards: {}, log: { [t - 1]: { d: 8, ok: 6, n: 4 } }, errs: [], sid: 'sidperf01', name: '', synced: 0, syncedN: 0 }, 'zd-recent': [{ ref: 'ege-rus', title: 'ЕГЭ: русский язык' }] },
};
// [имя, состояние, стартовый адрес (null — открываем сразу цель), действие]
const SC = [
  ['Главная: первое открытие', 'guest', null, { goto: '/' }],
  ['Главная → «Попробовать»', 'guest', '/', { click: ['a:has-text("Попробовать") >> nth=0'] }],
  ['Главная → «Войти»', 'guest', '/', { click: ['a.ld-nav-cta', 'a:has-text("Войти") >> nth=0'] }],
  ['Главная → якорь «Тарифы»', 'guest', '/', { click: ['a[href="#prices"]:visible >> nth=0'], hash: '#prices' }],
  ['Библиотека ЕГЭ: первое открытие', 'guest', null, { goto: '/?p=ege-rus', wait: '#go' }],
  ['Библиотека: главная → задание 4', 'library', '/?p=ege-rus', { click: ['a.task-tile >> nth=3', 'a[href="#/topic/task-4"]'] }],
  ['Библиотека: задание → теория', 'library', '/?p=ege-rus#/topic/task-4', { click: ['a.lesson-link >> nth=0', 'a[href^="#/lesson/"] >> nth=0'] }],
  ['Библиотека: «Заниматься» → карточка', 'library', '/?p=ege-rus', { click: ['#go'], wait: '.card, .finish' }],
  ['Студия (гость): открытие', 'guest', null, { goto: '/studio/' }],
  ['Студия: готовый пример по ссылке', 'guest', null, { goto: '/studio/#/sample' }],
  ['Кабинет (гость): открытие', 'guest', null, { goto: '/cabinet/' }],
  ['Вход: открытие', 'guest', null, { goto: '/login.html' }],
  ['/parent/ → кабинет родителя', 'guest', null, { goto: '/parent/' }],
  ['Оферта', 'guest', null, { goto: '/offer.html' }],
];

async function clickAny(page, sels) {
  let last;
  for (const s of sels) {
    const loc = page.locator(s);
    if (await loc.count().catch(() => 0)) { await loc.first().click({ timeout: 15000 }); return s; }
    last = s;
  }
  throw new Error('нет элемента: ' + (last || sels.join(' | ')));
}

(async () => {
  // launch() читает THROTTLE_PROXY при запуске: обычный браузер — без него, медленный — с ним
  const TP = process.env.THROTTLE_PROXY;
  delete process.env.THROTTLE_PROXY;
  const bReal = await launch();
  let bSlow = null;
  if (TP) { process.env.THROTTLE_PROXY = TP; bSlow = await launch(); delete process.env.THROTTLE_PROXY; }
  const rows = [];
  const only = process.env.ONLY ? new RegExp(process.env.ONLY) : null;
  const modes = [['сеть', bReal, false, false], ...(bSlow ? [['3G', bSlow, false, false], ['3G повт.', bSlow, true, false], ['3G+SW', bSlow, true, true]] : [])];
  for (const [name, stKey, start, act] of SC) {
    if (only && !only.test(name)) continue;
    for (const [mode, browser, warm, sw] of modes) {
      const ctx = await newCtx(browser, { w: W, sw, guarded: false });
      const page = await ctx.newPage();
      page.setDefaultTimeout(90000);
      await blockWrites(page);
      const w = watch(page);
      const run = async measured => {
        await resetStore(page, ST[stKey]);
        if (start) { await page.goto(BASE + start); await settle(page, w, { max: 90000 }); }
        const t0 = Date.now();
        await page.evaluate(() => { try { sessionStorage.setItem('__clickAt', '0'); } catch { /* */ } }).catch(() => {});
        if (act.goto) await page.goto(BASE + act.goto, { waitUntil: 'commit' });
        else await clickAny(page, act.click).catch(async e => { if (!act.hash) throw e; await page.evaluate(h => { location.hash = h; }, act.hash); });
        if (act.wait) await page.waitForSelector(act.wait, { timeout: 90000 }).catch(() => {});
        const st = await settle(page, w, { max: 90000, quiet: 400 });
        if (!measured) return null;
        const clickAt = act.goto ? t0 : (await page.evaluate(() => Number(sessionStorage.getItem('__clickAt')) || 0).catch(() => 0)) || t0;
        const fr = await page.evaluate(ca => { const r = (window.__appRenders || []).find(x => x.at >= ca && !/^Загружаю/.test(x.sig)); const nav = performance.getEntriesByType('navigation')[0]; return { render: r ? r.at : 0, dcl: nav ? Math.round(performance.timeOrigin + nav.domContentLoadedEventEnd) : 0, origin: performance.timeOrigin }; }, clickAt).catch(() => ({}));
        const reqs = w.reqs.filter(r => r.t0 >= t0 - 20 && r.t0 <= st.settledAt + 5 && !r.ext);
        const by = {};
        for (const r of reqs) { const k = r.method + ' ' + r.url.replace(ORIGIN, '').split('?')[0]; by[k] = (by[k] || 0) + 1; }
        const first = fr.render ? fr.render - clickAt : fr.dcl && fr.origin >= clickAt - 50 ? fr.dcl - clickAt : null;
        return { first, settle: st.settledAt - clickAt, timedOut: st.timedOut, n: reqs.length, kb: Math.round(reqs.reduce((s, r) => s + (r.bytes || 0), 0) / 1024),
          sw: reqs.filter(r => r.sw).length, api: reqs.filter(r => /\/(me|auth|pay|ai)(\/|\?|$)|\/packs\/[^./]+(\/|$|\?)/.test(r.url.replace(ORIGIN, ''))).map(r => r.method + ' ' + r.url.replace(ORIGIN, '').split('?')[0]),
          big: reqs.filter(r => r.bytes > 50 * 1024).map(r => `${r.url.replace(ORIGIN, '')} ${Math.round(r.bytes / 1024)}KB`), dups: Object.entries(by).filter(([, n]) => n > 1).map(([k, n]) => `${k} ×${n}`),
          errs: w.errors.filter(e => e.at >= t0).map(e => e.kind + ': ' + e.text.slice(0, 100)), url: page.url().replace(ORIGIN, '') };
      };
      let res;
      try {
        if (warm) await run(false);
        res = await run(true);
      } catch (e) { res = { error: String(e.message).split('\n')[0].slice(0, 160) }; }
      rows.push({ name, mode, ...res });
      console.log(`${name.padEnd(40)} ${mode.padEnd(8)} первый экран ${res.first ?? '-'} мс, полностью ${res.settle ?? '-'} мс, ${res.n ?? '-'} запр., ${res.kb ?? '-'} КБ${res.sw ? ' sw' + res.sw : ''}${res.dups?.length ? ' ПОВТОРЫ ' + res.dups.join(',') : ''}${res.errs?.length ? ' ОШИБКИ ' + res.errs.join(' | ') : ''}${res.error ? ' СБОЙ ' + res.error : ''}`);
      await ctx.close();
      saveJson(`perf-${W}.json`, rows);
    }
  }
  await bReal.close();
  if (bSlow) await bSlow.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
