// Общая обвязка проверки сайта (живого или локального): браузер, защита от записей на сервер,
// сбор ошибок и запросов, «успокоение» страницы, осмотр экрана, шаги путей со скриншотами.
// Адрес — BASE (по умолчанию живой сайт), папка результатов — OUT.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = (process.env.BASE || 'https://econcards.kqrulev.workers.dev').replace(/\/+$/, '');
const ORIGIN = new URL(BASE).origin;
const LOCAL = /^http:\/\/(localhost|127\.0\.0\.1)(:|$)/.test(ORIGIN);
const OUT = path.resolve(process.env.OUT || path.join(__dirname, 'out', 'last'));
for (const d of ['results', 'shots']) fs.mkdirSync(path.join(OUT, d), { recursive: true });

// Пути сервера, которые что-то записывают (KV, письма, бот). Живой сайт проверяем только чтением:
// любой не-GET запрос на сайт и эти пути браузер не отправляет, а попытку записываем в отчёт.
const WRITE_PATHS = /^\/(ai|tg|gh)(\/|$)|^\/auth\/(tg\/start|email\/|oauth\/|ticket|logout)|^\/auth\/[^/]+\/callback|^\/pay\/(create|promo|webhook)|^\/packs\/[^/]+\/(progress|parent-code|hw|notify)/;
const blockedLog = [];

async function launch(opts = {}) {
  const proxy = process.env.THROTTLE_PROXY ? { server: process.env.THROTTLE_PROXY }
    : !LOCAL && process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY, bypass: 'localhost,127.0.0.1' } : undefined;
  return chromium.launch({ ...(proxy ? { proxy } : {}), ...opts });
}

// Инструментирование страницы: мутации DOM (без тостов), перерисовки #app, тосты, клики, window.open
const INSTR = () => {
  if (window.__audit) return;
  window.__audit = 1;
  window.__lastMut = Date.now();
  window.__appRenders = [];
  window.__toasts = [];
  window.__opened = [];
  const inToast = n => { const e = n && (n.nodeType === 1 ? n : n.parentElement); return !!(e && e.closest && e.closest('.toast')); };
  const mo = new MutationObserver(list => {
    let real = false;
    for (const m of list) {
      if (m.type === 'childList') {
        const nodes = [...m.addedNodes, ...m.removedNodes];
        if (nodes.length && nodes.every(n => n.nodeType === 1 && n.classList && n.classList.contains('toast'))) {
          for (const n of m.addedNodes) window.__toasts.push({ at: Date.now(), t: (n.textContent || '').trim().slice(0, 160) });
          continue;
        }
      }
      if (inToast(m.target)) continue;
      real = true;
      if (m.type === 'childList' && m.target.id === 'app' && m.addedNodes.length) {
        window.__appRenders.push({ at: Date.now(), sig: (m.target.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 70) });
      }
    }
    if (real) window.__lastMut = Date.now();
  });
  const start = () => mo.observe(document, { subtree: true, childList: true, attributes: true, characterData: true });
  if (document.documentElement) start(); else document.addEventListener('readystatechange', start, { once: true });
  document.addEventListener('click', () => { try { sessionStorage.setItem('__clickAt', String(Date.now())); } catch { /* */ } }, true);
  const wo = window.open;
  window.open = function (...a) { window.__opened.push(String(a[0])); return wo.apply(this, a); };
};

// Защита: на сайт — только чтение; Telegram — заглушка; остальные внешние адреса — отказ.
// Внимание: перехват запросов выключает HTTP-кэш браузера, поэтому для замеров скорости guard: false
// (там подстраховка через CDP — blockWrites)
async function guard(ctx, label = '') {
  await ctx.route('**/*', route => {
    const req = route.request();
    let u;
    try { u = new URL(req.url()); } catch { return route.abort(); }
    if (u.origin === ORIGIN) {
      if (!['GET', 'HEAD'].includes(req.method()) || WRITE_PATHS.test(u.pathname)) {
        blockedLog.push({ at: Date.now(), label, method: req.method(), path: u.pathname });
        return route.abort('blockedbyclient');
      }
      return route.continue();
    }
    if (/^(data|blob):/.test(req.url())) return route.continue();
    if (/(^|\.)(t\.me|telegram\.me|telegram\.org)$/.test(u.hostname)) return route.fulfill({ body: '<html><body>telegram stub</body></html>', contentType: 'text/html' });
    return route.abort('blockedbyclient');
  });
}
// Подстраховка без перехвата (кэш работает): CDP блокирует пишущие пути по шаблону
async function blockWrites(page) {
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Network.enable');
  const pats = ['/ai', '/ai?*', '/tg*', '/gh*', '/auth/tg/start*', '/auth/email/*', '/auth/oauth/*', '/auth/ticket*', '/auth/logout*', '/auth/*/callback*', '/pay/create*', '/pay/promo*', '/pay/webhook*', '/packs/*/progress*', '/packs/*/parent-code*', '/packs/*/hw*', '/packs/*/notify*'];
  await cdp.send('Network.setBlockedURLs', { urls: pats.map(p => ORIGIN + p) });
  page.on('request', r => { if (r.url().startsWith(ORIGIN) && !['GET', 'HEAD'].includes(r.method())) blockedLog.push({ at: Date.now(), label: 'cdp', method: r.method(), path: new URL(r.url()).pathname }); });
  return cdp;
}

async function newCtx(browser, { w = 375, h, scheme = 'light', sw = false, guarded = true, label = '' } = {}) {
  const mobile = w < 600;
  const c = await browser.newContext({
    viewport: { width: w, height: h || (mobile ? 812 : 900) }, deviceScaleFactor: 1, colorScheme: scheme,
    serviceWorkers: sw ? 'allow' : 'block', isMobile: mobile, hasTouch: mobile, locale: 'ru-RU', timezoneId: 'Europe/Moscow',
    permissions: ['clipboard-read', 'clipboard-write'],
  });
  // Сервер приложения: на живом сайте — из config.js (тот же адрес); при локальной проверке — локальный
  const api = process.env.API || (LOCAL ? BASE : '');
  if (api) await c.addInitScript(a => { try { localStorage.setItem('zd-api', JSON.stringify(a)); } catch { /* */ } }, api);
  await c.addInitScript(INSTR);
  if (guarded) await guard(c, label);
  return c;
}

// Наблюдатель за страницей: ошибки, запросы, сеть в полёте
function watch(page) {
  const w = { errors: [], reqs: [], inflight: new Set(), lastAt: Date.now(), dialogs: [], popups: [], navs: [], downloads: [] };
  const ext = u => !u.startsWith(ORIGIN);
  page.on('console', m => { if (m.type() === 'error' && !/ERR_BLOCKED_BY_CLIENT/.test(m.text())) w.errors.push({ at: Date.now(), kind: 'console', text: m.text().slice(0, 300), url: page.url() }); });
  page.on('pageerror', e => w.errors.push({ at: Date.now(), kind: 'pageerror', text: String(e.message || e).slice(0, 300), url: page.url() }));
  page.on('request', r => { w.inflight.add(r); w.lastAt = Date.now(); r.__t0 = Date.now(); });
  const done = async (r, failed) => {
    w.inflight.delete(r); w.lastAt = Date.now();
    const errText = failed ? (r.failure()?.errorText || 'failed') : null;
    const rec = { t0: r.__t0, t1: Date.now(), url: r.url(), method: r.method(), type: r.resourceType(), ext: ext(r.url()), failed: errText, blocked: /BLOCKED_BY_CLIENT/.test(errText || ''), status: null, bytes: 0, sw: false };
    try {
      const resp = failed ? null : await r.response();
      if (resp) { rec.status = resp.status(); rec.sw = resp.fromServiceWorker(); }
      if (!failed) { const s = await r.sizes().catch(() => null); if (s) rec.bytes = (s.responseBodySize || 0) + (s.responseHeadersSize || 0); }
    } catch { /* */ }
    w.reqs.push(rec);
    // Отказы защиты — не ошибка сайта; внешние адреса не считаем
    if (!rec.ext && !rec.blocked && (failed || rec.status >= 400) && !/ERR_ABORTED/.test(errText || '')) {
      w.errors.push({ at: Date.now(), kind: failed ? 'requestfailed' : 'http' + rec.status, text: `${rec.method} ${rec.url.replace(ORIGIN, '')}${failed ? ' ' + errText : ''}`, url: page.url() });
    }
  };
  page.on('requestfinished', r => done(r, false));
  page.on('requestfailed', r => done(r, true));
  page.on('dialog', d => { w.dialogs.push({ at: Date.now(), type: d.type(), msg: d.message().slice(0, 200) }); (w.onDialog ? w.onDialog(d) : d.dismiss()).catch(() => {}); });
  page.on('popup', p => { w.popups.push({ at: Date.now(), url: p.url() }); p.waitForLoadState().then(() => { w.popups.at(-1).url = p.url(); }).catch(() => {}); });
  page.on('download', d => { w.downloads.push({ at: Date.now(), name: d.suggestedFilename() }); d.cancel().catch(() => {}); });
  page.on('framenavigated', f => { if (f === page.mainFrame()) w.navs.push({ at: Date.now(), url: f.url() }); });
  w.pendingCount = () => [...w.inflight].filter(r => !ext(r.url())).length;
  return w;
}

// Ждём, пока нет запросов в полёте и DOM не меняется quiet мс
async function settle(page, w, { quiet = 300, max = 15000 } = {}) {
  const t0 = Date.now();
  let lm = 0;
  while (Date.now() - t0 < max) {
    await page.waitForTimeout(40);
    try { lm = await page.evaluate(() => window.__lastMut || 0); } catch { lm = Date.now(); continue; }
    const now = Date.now();
    if (w.pendingCount() === 0 && now - w.lastAt >= quiet && now - lm >= quiet) return { settledAt: Math.max(lm, w.lastAt), timedOut: false };
  }
  return { settledAt: Date.now(), timedOut: true };
}

// Состояние экрана: модалки, пустой экран, вечная загрузка, мелкие кнопки, [hidden] виден, горизонтальная прокрутка
async function inspect(page) {
  try {
    return await page.evaluate(() => {
      const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
      const app = document.getElementById('app') || document.body;
      const txt = ((app && app.innerText) || '').replace(/\s+/g, ' ').trim();
      const small = [];
      document.querySelectorAll('button, .btn, a.back, .icon-btn, [role=tab], .tabs a, .cab-tabs a, input:not([type=hidden]), select, .link-btn, .swatch, .opt, .vowel').forEach(e => {
        if (!vis(e) || e.closest('.toast')) return;
        const r = e.getBoundingClientRect();
        if (r.height < 44 || (r.width < 44 && !['INPUT', 'SELECT'].includes(e.tagName))) small.push(`${e.tagName.toLowerCase()}${e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.') : ''}«${(e.innerText || e.value || e.getAttribute('aria-label') || '').trim().slice(0, 24)}» ${Math.round(r.width)}×${Math.round(r.height)}`);
      });
      const hiddenVisible = [...document.querySelectorAll('[hidden]')].filter(e => getComputedStyle(e).display !== 'none')
        .map(e => `${e.tagName.toLowerCase()}${e.id ? '#' + e.id : ''}${typeof e.className === 'string' && e.className ? '.' + e.className.trim().split(/\s+/).join('.') : ''}`);
      const modals = [...document.querySelectorAll('.modal')].map(m => (m.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 60));
      return {
        url: location.href, title: document.title, scrollY: Math.round(scrollY), docH: document.documentElement.scrollHeight,
        head: (document.querySelector('h1, .brand-title, .login-title')?.innerText || '').trim().slice(0, 80),
        text: txt.slice(0, 160), len: txt.length,
        blank: txt.length < 3 && !(app && app.querySelector('img, svg, canvas')),
        loading: /Загружаю|Загрузка/.test(txt) ? txt.match(/.{0,20}(Загружаю|Загрузка).{0,20}/)[0] : null,
        modals, hiddenVisible, overflowX: document.documentElement.scrollWidth > innerWidth + 1 ? document.documentElement.scrollWidth : 0,
        small: small.length, smallSamples: small.slice(0, 8),
        renders: window.__appRenders ? window.__appRenders.slice() : [],
        toasts: window.__toasts ? window.__toasts.slice() : [],
        opened: window.__opened ? window.__opened.slice() : [],
      };
    });
  } catch (e) { return { error: String(e.message).slice(0, 200), url: page.url() }; }
}

// Сброс состояния браузера на сайте: лёгкая страница того же адреса → очистить хранилища → положить своё
async function resetStore(page, store = {}) {
  await page.goto(BASE + '/manifest.webmanifest', { waitUntil: 'domcontentloaded' }).catch(() => {});
  await page.evaluate(s => { localStorage.clear(); sessionStorage.clear(); for (const [k, v] of Object.entries(s)) localStorage.setItem(k, JSON.stringify(v)); }, store).catch(() => {});
}

// Путь: шаги со скриншотами и сводкой ошибок
class Journey {
  constructor(name, { vp = '' } = {}) { this.name = name; this.vp = vp; this.steps = []; this.n = 0; this.dir = path.join(OUT, 'shots', name); fs.mkdirSync(this.dir, { recursive: true }); }
  async step(page, w, label, { shot = true, full = false, settleOpts, note = '', fail = null } = {}) {
    const st = await settle(page, w, settleOpts);
    const ins = await inspect(page);
    const since = this.lastAt || 0;
    const errs = w.errors.filter(e => e.at > since);
    const n = String(++this.n).padStart(2, '0');
    const file = path.join(this.dir, `${n}-${label.replace(/[^\p{L}\p{N}]+/gu, '-').slice(0, 50)}.png`);
    if (shot) await page.screenshot({ path: file, fullPage: full }).catch(() => {});
    const rec = { n, label, note, fail, ...ins, url: (ins.url || '').replace(ORIGIN, ''), errs, timedOut: st.timedOut, file: shot ? path.relative(OUT, file) : null,
      dialogs: w.dialogs.filter(d => d.at > since), popups: w.popups.filter(p => p.at > since), blocked: blockedLog.filter(b => b.at > since) };
    delete rec.renders;
    this.steps.push(rec);
    this.lastAt = Date.now();
    const flags = [fail && 'FAIL', errs.length && `ERR×${errs.length}`, ins.modals?.length && `MODAL×${ins.modals.length}`, ins.blank && 'BLANK', ins.loading && 'LOADING', st.timedOut && 'TIMEOUT', ins.overflowX && 'OVERFLOW', ins.hiddenVisible?.length && ('HIDDEN:' + ins.hiddenVisible.join(','))].filter(Boolean).join(' ');
    console.log(`${this.name} ${n} ${label} | ${rec.url} | ${ins.head || ''} ${flags ? '| ' + flags : ''}${fail ? '\n    FAIL ' + fail : ''}${errs.length ? '\n    ' + errs.map(e => e.kind + ': ' + e.text).join('\n    ') : ''}`);
    return rec;
  }
  save(extra = {}) { fs.writeFileSync(path.join(OUT, 'results', `${this.name}.json`), JSON.stringify({ name: this.name, vp: this.vp, steps: this.steps, ...extra }, null, 1)); }
}

// Шаг пути с перехватом ошибки действия: шаг записывается всегда
function stepper(J, page, w) {
  return async (label, fn, opts = {}) => {
    let fail = null;
    try { await fn(); } catch (e) { fail = String(e.message || e).split('\n')[0].slice(0, 200); }
    return J.step(page, w, label, { ...opts, fail });
  };
}

// Прохождение занятия: отвечаем на карточки до экрана «Готово» (или limit карточек)
async function playSession(page, { limit = 40, wrongEvery = 3 } = {}) {
  for (let k = 0; k < limit; k++) {
    if (await page.$('.finish')) return k;
    const card = await page.waitForSelector('.card .card-body, .finish', { timeout: 10000 }).catch(() => null);
    if (!card || await page.$('.finish')) return k;
    const wrong = wrongEvery && k % wrongEvery === 1;
    if (await page.$('.card .opt')) {
      const opts = await page.$$('.card .opt');
      await opts[wrong ? opts.length - 1 : 0].click();
      if (await page.$('.card .check:not([disabled])')) await page.click('.card .check');
    } else if (await page.$('.card .num-input')) {
      await page.fill('.card .num-input', wrong ? '999' : '1'); await page.click('.card .check');
    } else if (await page.$('.card .vowel')) {
      await (await page.$$('.card .vowel'))[0].click();
    } else if (await page.$('.card select')) {
      for (const s of await page.$$('.card select')) await s.selectOption({ index: 1 }).catch(() => {});
      await page.click('.card .check');
    } else if (await page.$('.card .show')) {
      await page.click('.card .show');
      await page.click(wrong ? '.card .grade .btn.bad' : '.card .grade .btn.good');
    } else if (await page.$('.card input[type=text], .card textarea')) {
      await page.fill('.card input[type=text], .card textarea', 'ответ'); if (await page.$('.card .check')) await page.click('.card .check');
    }
    await page.waitForSelector('#next', { state: 'visible', timeout: 5000 }).catch(() => {});
    if (await page.$('#next:visible')) await page.click('#next'); else return k;
  }
  return limit;
}

const saveJson = (name, data) => fs.writeFileSync(path.join(OUT, 'results', name), JSON.stringify(data, null, 1));
const blocked = () => blockedLog.slice();

module.exports = { BASE, ORIGIN, LOCAL, OUT, WRITE_PATHS, launch, newCtx, guard, blockWrites, watch, settle, inspect, resetStore, Journey, stepper, playSession, saveJson, blocked, INSTR };
