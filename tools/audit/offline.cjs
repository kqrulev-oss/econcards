// Офлайн с service worker: первый визит онлайн, потом сеть пропадает (context.setOffline).
// Ожидание: открытые раньше страницы показываются из кэша, остальные — страница «Нет связи»,
// никогда не главная вместо другой страницы; библиотека, открытая онлайн, работает; ответы API не лежат в кэше.
// node tools/audit/offline.cjs [width]
const { BASE, ORIGIN, LOCAL, launch, newCtx, watch, Journey, stepper, blockWrites, saveJson } = require('./lib.cjs');
const http = require('http');
const net = require('net');
const W = +(process.argv[2] || 375);

// Выключатель сети: браузер ходит через этот прокси; «офлайн» — рвём все соединения и не пускаем новые.
// context.setOffline() не действует на запросы service worker, поэтому без прокси офлайн не настоящий.
function netSwitch(port) {
  const socks = new Set();
  let offline = false;
  const upstream = !LOCAL && process.env.HTTPS_PROXY ? new URL(process.env.HTTPS_PROXY) : null;
  const seen = new WeakSet();
  const track = s => { if (seen.has(s)) return; seen.add(s); socks.add(s); s.on('close', () => socks.delete(s)); s.on('error', () => {}); };
  const srv = http.createServer((req, res) => {
    if (offline) { req.socket.destroy(); return; }
    let u;
    try { u = new URL(req.url); } catch { res.writeHead(400); res.end(); return; }
    const p = http.request({ host: u.hostname, port: u.port || 80, path: u.pathname + u.search, method: req.method, headers: req.headers }, r => { res.writeHead(r.statusCode, r.headers); r.pipe(res); });
    p.on('error', () => res.destroy());
    p.on('socket', track);
    req.pipe(p);
  });
  srv.on('connection', track);
  srv.on('connect', (req, client, head) => {
    if (offline) { client.destroy(); return; }
    const go = (up, rest) => {
      track(up);
      client.write('HTTP/1.1 200 Connection Established\r\n\r\n');
      if (head?.length) up.write(head);
      if (rest?.length) client.write(rest);
      up.pipe(client); client.pipe(up);
      up.on('close', () => client.destroy()); client.on('close', () => up.destroy());
    };
    if (upstream) {
      const s = net.connect(Number(upstream.port || 80), upstream.hostname, () => s.write(`CONNECT ${req.url} HTTP/1.1\r\nHost: ${req.url}\r\n\r\n`));
      let buf = Buffer.alloc(0);
      const onData = d => {
        buf = Buffer.concat([buf, d]);
        const i = buf.indexOf('\r\n\r\n');
        if (i < 0) return;
        s.off('data', onData);
        if (!/^HTTP\/1\.\d 200/.test(buf.toString('latin1', 0, i))) { s.destroy(); client.destroy(); return; }
        go(s, buf.subarray(i + 4));
      };
      s.on('data', onData);
      s.on('error', () => client.destroy());
    } else {
      const [host, port] = req.url.split(':');
      const s = net.connect(Number(port || 443), host, () => go(s));
      s.on('error', () => client.destroy());
    }
  });
  return new Promise(ok => srv.listen(port, '127.0.0.1', () => ok({
    set(v) { offline = v; if (v) for (const s of socks) s.destroy(); },
    close() { for (const s of socks) s.destroy(); srv.close(); },
  })));
}

(async () => {
  const PORT = Number(process.env.SWITCH_PORT || 8898);
  const sw = await netSwitch(PORT);
  // Playwright по умолчанию пускает и localhost через прокси (<-loopback>)
  const b = await launch({ proxy: { server: `http://127.0.0.1:${PORT}` } });
  const out = { base: BASE, W, modes: {} };
  for (const mode of ['visited', 'landing-only']) {
    const J = new Journey(`offline-${mode}-${W}`, { vp: W });
    const ctx = await newCtx(b, { w: W, sw: true, guarded: false });
    const page = await ctx.newPage();
    page.setDefaultTimeout(8000);
    await blockWrites(page);
    const w = watch(page);
    const S = stepper(J, page, w);
    await S('онлайн: главная (ставится service worker)', async () => {
      await page.goto(`${BASE}/?about`);
      await page.evaluate(() => navigator.serviceWorker.ready);
      await page.reload(); // страница под управлением SW
      await page.waitForTimeout(1500);
    });
    if (mode === 'visited') {
      await S('онлайн: библиотека ?p=ege-rus', async () => { await page.goto(`${BASE}/?p=ege-rus`); await page.waitForSelector('#go', { timeout: 20000 }); });
      await S('онлайн: студия', () => page.goto(`${BASE}/studio/`));
      await S('онлайн: вход', () => page.goto(`${BASE}/login.html`));
      await S('онлайн: кабинет', () => page.goto(`${BASE}/cabinet/`));
    }
    const cache = await page.evaluate(async () => {
      const out = {};
      for (const k of await caches.keys()) out[k] = (await (await caches.open(k)).keys()).map(r => r.url.replace(location.origin, ''));
      return out;
    }).catch(e => ({ error: String(e.message) }));
    const cached = Object.values(cache).flat().filter(x => typeof x === 'string');
    const apiCached = cached.filter(u => /^\/(me|auth|pay|ai|tg)(\/|\?|$)|^\/packs\/[^/.]+(\/|\?|$)/.test(u));
    await ctx.setOffline(true);
    sw.set(true);
    const check = async (label, url, expect) => {
      const r = await S(`ОФЛАЙН: ${label}`, () => page.goto(BASE + url, { timeout: 15000 }));
      const html = await page.evaluate(() => ({ title: document.title, offline: /Нет связи|нет связи|Нет интернета|офлайн/i.test(document.body.innerText || ''), landing: !!document.querySelector('.ld-hero, .landing, [class^="ld-"]'), text: (document.body.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 100) })).catch(() => ({}));
      r.expect = expect; r.page = html;
      const landingInstead = html.landing && !/^\/(\?|$)/.test(url);
      r.verdict = r.blank ? 'пустой экран' : r.loading ? 'вечная загрузка' : landingInstead ? 'главная вместо страницы' : expect === 'offline' && !html.offline && !r.fail ? 'нет сообщения «Нет связи»' : r.fail && !html.offline ? 'не открылась' : 'ok';
      return r;
    };
    await check('главная', '/?about', 'page');
    await check('библиотека', '/?p=ege-rus', mode === 'visited' ? 'page' : 'offline');
    if (mode === 'visited') {
      const r = await S('ОФЛАЙН: «Заниматься» в библиотеке', async () => { await page.click('#go'); await page.waitForSelector('.card, .finish', { timeout: 10000 }); });
      r.verdict = r.fail ? 'занятие не открылось' : 'ok';
    }
    await check('задание 4', '/?p=ege-rus#/topic/task-4', mode === 'visited' ? 'page' : 'offline');
    await check('студия', '/studio/', mode === 'visited' ? 'page' : 'offline');
    await check('вход', '/login.html', mode === 'visited' ? 'page' : 'offline');
    await check('кабинет', '/cabinet/', mode === 'visited' ? 'page' : 'offline');
    await check('оферта (не открывали)', '/offer.html', 'offline');
    await check('политика (не открывали)', '/privacy.html', 'offline');
    await check('неизвестный тренажёр', '/?t=zzzz1234', 'any');
    await check('/parent/', '/parent/', 'any');
    // Сеть вернулась: страница должна ожить
    sw.set(false);
    await ctx.setOffline(false);
    const back = await S('СНОВА ОНЛАЙН: студия', () => page.goto(`${BASE}/studio/`));
    back.verdict = back.blank || back.loading || back.fail ? 'не ожила' : 'ok';
    J.save({ cache, apiCached, errorsTotal: w.errors.length });
    out.modes[mode] = { steps: J.steps.map(s => ({ label: s.label, url: s.url, verdict: s.verdict || '', fail: s.fail, head: s.head, text: s.text, file: s.file })), apiCached, cachedCount: cached.length, cacheNames: Object.keys(cache) };
    console.log(J.name, 'в кэше', cached.length, 'файлов; API в кэше:', apiCached.join(', ') || 'нет');
    await ctx.close();
  }
  saveJson(`offline-${W}.json`, out);
  await b.close();
  sw.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
