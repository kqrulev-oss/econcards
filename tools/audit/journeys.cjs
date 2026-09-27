// Пути без входа в аккаунт, со скриншотами каждого шага: node tools/audit/journeys.cjs [width] [scheme]
//   tutor   — новый репетитор: главная → «Попробовать» → готовый пример → глазами ученика → «Ученики» → отчёт → «Опубликовать» (до входа);
//   library — ученик библиотеки ЕГЭ: задания → теория → занятие → «назад» посреди занятия → профиль → другая библиотека;
//   nav     — главная, якоря, вход, кабинет и родитель без входа, документы, неизвестный код, пустой код, 404.
// Записи на сервер заблокированы (lib.cjs), вход не выполняется.
const { BASE, ORIGIN, launch, newCtx, watch, Journey, stepper, playSession, saveJson, blocked } = require('./lib.cjs');
const W = +(process.argv[2] || 375);
const scheme = process.argv[3] || 'light';

// Нажать первый подходящий элемент из списка селекторов
async function tap(page, sels, { timeout = 8000 } = {}) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    for (const s of [].concat(sels)) {
      const loc = page.locator(s).first();
      if (await loc.isVisible().catch(() => false)) { await loc.click({ timeout: 4000 }); return s; }
    }
    await page.waitForTimeout(150);
  }
  throw new Error('не нашёл: ' + [].concat(sels).join(' | '));
}
const has = (page, sel) => page.locator(sel).first().isVisible().catch(() => false);

(async () => {
  const b = await launch();
  const summary = { base: BASE, W, scheme, journeys: {} };
  const only = process.env.ONLY ? new RegExp(process.env.ONLY) : null;

  const J1 = async () => {
    const J = new Journey(`tutor-${W}-${scheme}`, { vp: W });
    const ctx = await newCtx(b, { w: W, scheme, label: J.name });
    const page = await ctx.newPage(); page.setDefaultTimeout(10000);
    const w = watch(page); w.onDialog = d => d.dismiss();
    const S = stepper(J, page, w);
    await S('главная', () => page.goto(BASE + '/'));
    await S('«Попробовать»', () => tap(page, ['a:has-text("Попробовать")', 'a:has-text("Собрать тренажёр")']));
    await S('выбор предмета (если спрашивают) → Русский', async () => { if (await has(page, 'button:has-text("Русский")')) await tap(page, 'button:has-text("Русский")'); });
    await S('пример открыт: карточки', async () => { await page.waitForURL(/#\/p\/[^/]+/, { timeout: 15000 }); });
    await S('«Глазами ученика»', () => tap(page, ['#try', 'button:has-text("глазами ученика")', 'a:has-text("глазами ученика")', 'button:has-text("Попробовать")', 'a:has-text("Открыть как ученик")']));
    await S('закрыть просмотр (Esc)', () => page.keyboard.press('Escape'));
    await S('вкладка «Ученики»', () => tap(page, ['.tabs a[href$="/students"]', 'a:has-text("Ученики")']));
    await S('«Отчёт родителям» у ученика-примера', () => tap(page, ['button:has-text("Отчёт")', 'a:has-text("Отчёт")']));
    const backStay = async (label, url) => {
      const r = await S(label, () => page.goBack());
      if (!page.url().startsWith(ORIGIN)) { r.fail = 'ушло с сайта'; await page.goto(BASE + url).catch(() => {}); }
      return r;
    };
    await backStay('телефонное «назад» закрывает окно', '/studio/');
    await S('вкладка «Публикация» / «Опубликовать»', () => tap(page, ['.tabs a[href$="/publish"]', 'a:has-text("Опубликовать")', 'button:has-text("Опубликовать")']));
    await S('«Опубликовать» без входа → вход', async () => { if (!/login/.test(page.url())) await tap(page, ['button:has-text("Опубликовать")', 'a:has-text("Опубликовать")', 'a:has-text("Войти")']); });
    await backStay('«назад» из входа → студия, пример на месте', '/studio/');
    await S('перезагрузка студии', () => page.reload());
    await S('путь в кабинет из студии', () => tap(page, ['a[href*="cabinet"]', 'a:has-text("Кабинет")']));
    J.save({ blocked: blocked() });
    await ctx.close();
    return J;
  };

  const J2 = async () => {
    const J = new Journey(`library-${W}-${scheme}`, { vp: W });
    const ctx = await newCtx(b, { w: W, scheme, label: J.name });
    const page = await ctx.newPage(); page.setDefaultTimeout(10000);
    const w = watch(page);
    const S = stepper(J, page, w);
    await S('библиотека ЕГЭ: русский', async () => { await page.goto(BASE + '/?p=ege-rus'); await page.waitForSelector('#go', { timeout: 20000 }); });
    await S('задание 4', () => tap(page, ['a[href="#/topic/task-4"]', 'a.task-tile >> nth=3']));
    await S('теория задания', () => tap(page, ['a.lesson-link', 'a[href^="#/lesson/"]']));
    await S('«назад» → задание', () => page.goBack());
    await S('«назад» → главная тренажёра', () => page.goBack());
    await S('«Заниматься»', async () => { await tap(page, '#go'); await page.waitForSelector('.card, .finish', { timeout: 10000 }); });
    await S('ответить на 5 карточек', () => playSession(page, { limit: 5 }));
    let dlg = null;
    w.onDialog = d => { dlg = d.message(); return d.dismiss(); };
    await S('телефонное «назад» посреди занятия (отказаться выходить)', async () => { await page.goBack(); await page.waitForTimeout(600); });
    const mid = J.steps.at(-1);
    const left = !page.url().startsWith(ORIGIN);
    mid.note = dlg ? `спросили: «${dlg}»` : left ? 'ушло с сайта (занятие без своего адреса)' : (await has(page, '.card')) ? 'осталось в занятии без вопроса' : 'вышло из занятия без вопроса';
    if (left) { mid.fail = mid.note; await page.goto(BASE + '/?p=ege-rus'); await tap(page, '#go').catch(() => {}); }
    w.onDialog = d => d.accept();
    await S('доиграть до «Готово»', () => playSession(page, { limit: 40 }));
    await S('«назад» после «Готово» не возвращает в занятие', () => page.goBack());
    await S('профиль', async () => { await page.goto(BASE + '/?p=ege-rus#/me'); });
    await S('все наборы', async () => { await page.goto(BASE + '/?p=ege-rus#/library'); });
    await S('ЕГЭ: математика', () => tap(page, ['a[href*="ege-math"]', 'a:has-text("математика")']));
    await S('перезагрузка', () => page.reload());
    J.save({ blocked: blocked() });
    await ctx.close();
    return J;
  };

  const J3 = async () => {
    const J = new Journey(`nav-${W}-${scheme}`, { vp: W });
    const ctx = await newCtx(b, { w: W, scheme, label: J.name });
    const page = await ctx.newPage(); page.setDefaultTimeout(10000);
    const w = watch(page);
    const S = stepper(J, page, w);
    await S('главная', () => page.goto(BASE + '/'));
    const renders = () => page.evaluate(() => (window.__appRenders || []).length);
    for (const a of ['#how', '#prices', '#faq']) {
      const r0 = await renders();
      const st = await S(`якорь ${a}`, async () => {
        const vis = page.locator(`a[href="${a}"]:visible`);
        if (await vis.count()) await vis.first().click(); else await page.evaluate(h => { location.hash = h; }, a);
      });
      st.note = `перерисовок: ${(await renders()) - r0}`;
    }
    await S('пустой код «Открыть»', async () => { const inp = page.locator('input[name=code], #code, input[placeholder*="код" i]').first(); if (await inp.count()) { await inp.fill(''); await tap(page, ['button:has-text("Открыть")']); } });
    await S('«Войти»', () => tap(page, ['a.ld-nav-cta', 'a:has-text("Войти")']));
    await S('«назад» с входа', () => page.goBack());
    await S('кабинет без входа', () => page.goto(BASE + '/cabinet/'));
    await S('кабинет родителя без входа', () => page.goto(BASE + '/cabinet/#parent'));
    await S('/parent/ (старый адрес)', () => page.goto(BASE + '/parent/'));
    await S('оферта', () => page.goto(BASE + '/offer.html'));
    await S('политика', () => page.goto(BASE + '/privacy.html'));
    await S('неизвестный код тренажёра', () => page.goto(BASE + '/?t=zzzz1234'));
    await S('«К наборам» / выход с неизвестного кода', async () => { if (await has(page, 'a:has-text("наборам"), a:has-text("библиотек")')) await tap(page, ['a:has-text("наборам")', 'a:has-text("библиотек")']); });
    const r404 = await S('несуществующая страница', async () => { const resp = await page.goto(BASE + '/no-such-page-audit'); J.status404 = resp?.status(); });
    r404.note = 'статус ' + J.status404;
    if (J.status404 === 404) r404.errs = r404.errs.filter(e => !/404/.test(e.text)); // ожидаемо
    J.save({ blocked: blocked() });
    await ctx.close();
    return J;
  };

  for (const [key, fn] of [['tutor', J1], ['library', J2], ['nav', J3]]) {
    if (only && !only.test(key)) continue;
    try {
      const J = await fn();
      summary.journeys[key] = J.steps.map(s => ({ n: s.n, label: s.label, url: s.url, head: s.head, fail: s.fail, note: s.note, errs: s.errs.map(e => e.kind + ': ' + e.text), modals: s.modals, blank: s.blank, loading: s.loading, overflowX: s.overflowX, hiddenVisible: s.hiddenVisible, small: s.small, file: s.file, blocked: (s.blocked || []).map(x => x.method + ' ' + x.path) }));
    } catch (e) { summary.journeys[key] = { crash: String(e.message).slice(0, 300) }; console.log('CRASH', key, e.message); }
    saveJson(`journeys-${W}-${scheme}.json`, summary);
  }
  await b.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
