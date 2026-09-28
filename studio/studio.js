// Студия репетитора: собрать набор из своих материалов (через ИИ) или из
// библиотеки, опубликовать ссылку для учеников и смотреть их прогресс.
import { signedIn, session, account, loginDialog, signOut, refreshAccount, accountFresh, addRole, finishRedirectLogin, finishPayment, payDialog, planOf, daysLeft, dateRu, TG_ICON, openLink } from '../account.js';
import { store, api, apiBase, ai, loadPack, loadLibrary, renderCard, esc, text, day, uid, plural, el, toast, modal, dueDay, dueText, whenText, videoEmbed, KIND_NAMES } from '../lib.js';

const $app = document.getElementById('app');
const ROOT = '../';
// Цвета тренажёра: все читаются с белым текстом и не спорят с жёлтыми кнопками
const COLORS = ['#5B3DF5', '#0E7C86', '#2F6BFF', '#1F8A4C', '#C2185B', '#D8452B', '#8A4FFF', '#1B1440'];
// ?debug — служебные поля (адрес сервера) для разработки; репетитору они не нужны
const DEBUG = new URLSearchParams(location.search).has('debug');
// sessionStorage: то, что живёт до закрытия вкладки (набранный материал, «опубликовать после входа»)
const tabStore = {
  get: k => { try { return sessionStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { if (v == null) sessionStorage.removeItem(k); else sessionStorage.setItem(k, v); } catch { /* приватный режим */ } },
};

// ---------- данные и облако ----------

// Черновики наборов и ключи публикации живут в браузере репетитора, а после
// входа в аккаунт — ещё и на сервере (не теряются при очистке браузера)
let db = { packs: {}, keys: {}, deleted: {}, ...store.get('zd-studio', {}) };
// Новый тренажёр живёт только здесь, пока в него ничего не добавили, — пустые черновики не копятся
let draft = null, draftKey = '';
let cloud = signedIn() ? 'saved' : 'off'; // off | saving | saved | error
let cloudReady = !signedIn(); // облачная копия получена (или её нет): можно сказать «тренажёр не найден»
let cloudFailed = false;
let cloudTimer;
const DIRTY = 'zd-studio-dirty'; // есть правки, которых ещё нет в облаке (account.js смотрит при выходе)
// Чьи тренажёры в этом браузере: после входа другим аккаунтом (общий компьютер, человек вышел,
// оставив данные, или его сессия закончилась) чужие тренажёры и ключи учеников в своё облако
// не берём — откладываем в zd-stash-studio до его входа (выход другого человека их не стирает)
const OWNER = 'zd-studio-owner', STASH = 'zd-stash-studio';
const hasData = s => !!(Object.keys(s.packs || {}).length || Object.keys(s.keys || {}).length);
const EMPTY = () => ({ packs: {}, keys: {}, deleted: {} });

const persist = () => {
  store.set('zd-studio', db);
  if (!signedIn()) return;
  store.set(DIRTY, Date.now());
  setCloud('saving');
  clearTimeout(cloudTimer);
  cloudTimer = setTimeout(pushCloud, 2000);
};

async function pushCloud() {
  clearTimeout(cloudTimer);
  if (!signedIn()) return setCloud('off');
  const mark = store.get(DIRTY, null);
  try {
    await api('/me/studio', { method: 'PUT', body: { packs: db.packs, keys: db.keys, deleted: db.deleted } });
    if (store.get(DIRTY, null) === mark) store.set(DIRTY, null);
    setCloud('saved');
  } catch { setCloud(signedIn() ? 'error' : 'off'); }
}

function setCloud(state) {
  cloud = state;
  const b = document.querySelector('.cloud');
  if (b) b.outerHTML = cloudBadge();
}
const cloudBadge = () => signedIn()
  ? `<span class="badge cloud ${cloud}">${{ saving: 'сохраняю…', saved: 'в облаке', error: 'не сохранено', off: '' }[cloud]}</span>` : '';

// Две копии студии (эта и облачная) → одна: у набора побеждает свежая правка,
// удалённый набор не возвращается, ключи объединяются. При равной правке остаётся
// здешний объект — по нему видно, что показанный экран не устарел
function mergeStudio(a, b) {
  const deleted = { ...b.deleted };
  for (const [id, t] of Object.entries(a.deleted || {})) deleted[id] = Math.max(t, deleted[id] || 0);
  const packs = {};
  for (const id of new Set([...Object.keys(a.packs || {}), ...Object.keys(b.packs || {})])) {
    const x = a.packs?.[id], y = b.packs?.[id];
    const best = !x ? y : !y ? x : (y.edited > x.edited ? y : x);
    if (!(deleted[id] >= best.edited)) packs[id] = best;
  }
  return { packs, keys: { ...b.keys, ...a.keys }, deleted };
}

// Подпись содержимого студии: какие тренажёры, их правки и публикации, ключи, удалённые
const packSig = p => `${p.edited}|${p.published}`;
const studioSig = s => JSON.stringify([
  Object.keys(s.packs || {}).sort().map(id => `${id}:${packSig(s.packs[id])}`),
  Object.entries(s.keys || {}).sort(), Object.entries(s.deleted || {}).sort()]);

// Облачная копия ↔ здешняя. В облако пишем, только если слияние что-то добавило к облачной
// копии (каждая запись — трафик и лимит хранилища); экран трогаем, только если поменялось
// то, что на нём показано
let syncing = null;
const syncCloud = () => (syncing ||= doSync().finally(() => { syncing = null; }));
async function doSync() {
  const wasReady = cloudReady;
  if (!signedIn()) { cloudReady = true; if (!wasReady) dataChanged(); return; }
  const token = session()?.token, me = account()?.id;
  try {
    const remote = (await api('/me/studio')) || {};
    // Пока ждали облако, вышли или вошли другим аккаунтом — облачное в этот браузер не пишем
    if (session()?.token !== token) return;
    const before = studioSig(db);
    let moved = false;
    if (me) {
      const owner = store.get(OWNER, null), stash = store.get(STASH, null) || {};
      if (owner && owner !== me && hasData(db)) {
        stash[owner] = mergeStudio(stash[owner] || EMPTY(), db);
        db = EMPTY();
        draft = null;
        store.set(DIRTY, null); // несохранённые правки — того аккаунта, не этого
        moved = true;
      }
      // Свои тренажёры, отложенные, пока здесь работал другой аккаунт, — возвращаем
      if (stash[me]) { db = mergeStudio(db, stash[me]); delete stash[me]; }
      store.set(STASH, Object.keys(stash).length ? stash : null);
      store.set(OWNER, me);
      if (moved) { store.set('zd-studio', db); notice('stash', 'Тренажёры другого аккаунта убраны из этой студии — они вернутся, когда он снова войдёт в этом браузере.', 'Понятно', () => {}); }
    }
    db = mergeStudio(db, remote);
    const now = studioSig(db);
    if (now !== before) store.set('zd-studio', db);
    cloudReady = true;
    cloudFailed = false;
    if (now !== studioSig(remote)) await pushCloud();
    else { clearTimeout(cloudTimer); store.set(DIRTY, null); setCloud('saved'); }
    if (now !== before || !wasReady) dataChanged();
  } catch (err) {
    cloudReady = true;
    // 401 — сессия закончилась: скажет обработчик zd-session-expired
    if (err.status !== 401) { cloudFailed = true; setCloud('error'); }
    if (!wasReady) dataChanged();
  }
}

// Что сейчас на экране: тренажёр и вкладка (пусто — список и служебные экраны)
let shown = { pack: null, tab: '' };
const busy = () => !!document.querySelector('.modal') || ['add', 'settings', 'students'].includes(shown.tab)
  || !!document.activeElement?.closest?.('#app input, #app textarea, #app select');

// Данные поменялись извне (облако, соседняя вкладка). Показанный экран перерисовываем, только
// если он от них зависит и на нём нечего потерять; иначе — плашка «Есть изменения — обновить»
function dataChanged() {
  const p = shown.pack;
  if (!p) return route(); // список, «Загружаю тренажёр…», «не найден»
  if (db.packs[p.id] === p || p === draft) return; // показанный тренажёр не менялся
  if (busy()) return notice('cloud', 'Есть изменения из облака.', 'Обновить', route);
  route();
}

// Плашка внизу экрана: «Есть изменения из облака — обновить», «Сессия закончилась — войти»
function notice(kind, msg, btn, onClick) {
  let bar = document.getElementById('studio-notice');
  if (!bar) {
    bar = el('<div id="studio-notice" class="notice-bar" role="status"></div>');
    document.body.append(bar);
  }
  bar.dataset.kind = kind;
  bar.innerHTML = `<span>${esc(msg)}</span><button class="btn small primary">${esc(btn)}</button>`;
  bar.querySelector('button').onclick = () => { hideNotice(); onClick(); };
  document.body.classList.add('has-notice');
}
function hideNotice(kind) {
  const bar = document.getElementById('studio-notice');
  if (!bar || (kind && bar.dataset.kind !== kind)) return;
  bar.remove();
  document.body.classList.remove('has-notice');
}

// ---------- аккаунт ----------

const initials = a => esc((a?.name || a?.email || '?').trim().slice(0, 2).toUpperCase());
// Путь в личный кабинет виден всегда, и на телефоне: аватар + «Кабинет»
function accountBar() {
  if (!signedIn()) return `<a class="btn small primary" href="${ROOT}login?role=tutor&next=studio/">Войти</a>`;
  const a = account();
  return `${cloudBadge()}<a class="acct-link" href="${ROOT}cabinet/#tutor" title="Личный кабинет"><span class="avatar small">${initials(a)}</span>
    <span class="acct-text"><span class="acct-name">${esc(a?.name || a?.email || 'Аккаунт')}</span><small>Кабинет</small></span></a>`;
}
const cabLink = () => (signedIn() ? `<a class="acct-link" href="${ROOT}cabinet/#tutor" title="Личный кабинет" aria-label="Личный кабинет"><span class="avatar small">${initials(account())}</span></a>` : '');

// Тариф репетитора: пробный / оплачен / бесплатный с лимитами. Стоит под тренажёрами, а не над ними:
// в пробный период — мелкая ссылка «Тарифы», а не «Оплатить» первой кнопкой
function tariffPanel() {
  if (!signedIn()) return '';
  const st = planOf('tutor');
  if (st.paidUntil > Date.now()) return `<section class="panel plan ok"><span>Тариф оплачен до <b>${dateRu(st.paidUntil)}</b>.</span> <button class="link-btn" id="pay">Продлить</button></section>`;
  if (st.trialEnd > Date.now()) return `<section class="panel plan trial"><span><b>Пробный период: осталось ${plural(daysLeft(st.trialEnd), 'день', 'дня', 'дней')}</b> — всё без ограничений.</span> <button class="link-btn" id="pay">Тарифы</button></section>`;
  return `<section class="panel plan free"><span><b>Бесплатный тариф:</b> 1 тренажёр и до 3 учеников в нём. Без ограничений — по подписке.</span> <button class="btn small primary" id="pay">Оплатить</button></section>`;
}

function accountPanel() {
  const a = account();
  return `<section class="panel acct-panel">
    <div class="acct-who"><span class="avatar small">${initials(a)}</span><span><small>Вы вошли</small><b>${esc(a?.name || a?.email || 'Аккаунт')}</b></span></div>
    <div class="row"><a class="btn small" href="${ROOT}cabinet/#tutor">Личный кабинет</a><button class="btn small ghost" id="logout">Выйти</button></div>
  </section>`;
}

// Вход из студии (плашка «Сессия закончилась», публикация). then — что сделать после входа
function login({ why = 'Тренажёры, ключи и ученики сохранятся в аккаунте — не пропадут при очистке браузера и откроются с любого устройства.', then, onCancel } = {}) {
  return loginDialog({
    role: 'tutor', why, onCancel,
    onDone: async () => {
      hideNotice('session');
      for (const k of Object.keys(packCache)) delete packCache[k]; // с аккаунтом библиотека может быть полной
      await addRole('tutor');
      setCloud('saving');
      await syncCloud();
      if (then) await then();
      else if (!busy()) route();
    },
  });
}

function bindAccount(root) {
  root.querySelector('#pay')?.addEventListener('click', () => payDialog({ product: 'tutor' }));
  root.querySelector('#logout')?.addEventListener('click', async e => {
    const btn = e.currentTarget;
    btn.disabled = true;
    // Несохранённое — сначала в облако: тогда выход сотрёт этот браузер без потерь
    if (store.get(DIRTY, null)) await pushCloud();
    const r = await signOut();
    if (!r.out) { btn.disabled = false; return; }
    if (r.wiped) { db = { packs: {}, keys: {}, deleted: {} }; draft = null; }
    cloud = 'off';
    toast(r.wiped ? 'Вы вышли. Тренажёры — в облаке, в этом браузере их больше нет' : 'Вы вышли из аккаунта');
    route();
  });
}

// Сессия закончилась (вышли на другом устройстве, истёк срок) — говорим прямо, а не молча
// превращаемся в гостевую студию. Тренажёры остаются в браузере, после входа уйдут в облако
function sessionBar() {
  notice('session', 'Сессия закончилась — войдите снова. Тренажёры остались в этом браузере.', 'Войти', () => login());
}
window.addEventListener('zd-session-expired', () => {
  setCloud('off');
  sessionBar();
  if (!shown.pack && !busy()) route();
});

const touch = p => { p.edited = Date.now(); keep(p); persist(); };

// Telegram репетитора (GET /me/notify): подключён ли бот и свежая ссылка t_ на час.
// Ответ держим минуту — список перерисовывается часто, а каждый запрос — 3 чтения KV
const tzNow = () => -new Date().getTimezoneOffset();
let tgMe = null, tgWait = false;
async function tgPanel(slot) {
  if (!tgMe || Date.now() - tgMe.at > 60e3) tgMe = { at: Date.now(), p: api(`/me/notify?tz=${tzNow()}`).catch(() => null) };
  const { at, p } = tgMe, r = await p;
  if (!slot.isConnected || !r) return;
  if (r.tutor?.on) {
    slot.innerHTML = `<p class="muted small-note">Telegram подключён · задания — командой /dz${r.bot ? ` в <a href="https://t.me/${esc(r.bot.slice(1))}" target="_blank" rel="noopener">${esc(r.bot)}</a>` : ''}</p>`;
    return;
  }
  if (!r.link) { slot.innerHTML = ''; return; } // бот не настроен или нет роли репетитора
  slot.innerHTML = `<section class="panel cab-tip"><h2>Telegram для репетитора</h2>
    <p class="muted">Задания ученикам командой /dz, сообщение, если новый ученик не может присоединиться, и напоминание о конце тарифа.</p>
    <a class="btn primary" id="tg-link" target="_blank" rel="noopener" href="${esc(r.link)}">${TG_ICON}Подключить Telegram</a>
    <p class="muted small-note">Откроется бот — нажмите «Запустить». Ссылка действует час.</p></section>`;
  slot.querySelector('#tg-link').onclick = e => {
    tgWait = true;
    tgMe = null;
    if (Date.now() - at < 50 * 60e3) return;
    // Страница открыта почти час — ссылка вот-вот истечёт, берём свежую
    e.preventDefault();
    api(`/me/notify?tz=${tzNow()}`).then(x => { if (x.link) openLink(x.link); }).catch(err => toast(err.message));
  };
}
// Вернулись из Telegram после «Подключить» — сразу видно, что бот подключён
document.addEventListener('visibilitychange', () => {
  const slot = document.getElementById('tg-me');
  if (!document.hidden && tgWait && slot) { tgWait = false; tgPanel(slot); }
});

// ---------- тренажёры ----------

const studentLink = id => new URL(`${ROOT}?t=${id}`, location.href).href;
// «Открыть как ученик»: режим просмотра — ничего не уходит на сервер, репетитор не попадает в ученики
const previewLink = id => `${studentLink(id)}&preview=1`;
const isPublished = p => p.published && p.published >= p.edited;
// Нетронутый «Новый тренажёр» (так создавались раньше) в списках не показываем
const isBlank = p => !p.cards?.length && !p.topics?.length && !p.theory?.length && !p.published
  && !p.course?.lessons?.length && !p.course?.lives?.length && (p.title || 'Новый тренажёр') === 'Новый тренажёр';

function newPack(id = uid(8)) {
  draft = {
    id, title: 'Новый тренажёр', tutor: '', subject: '', color: COLORS[0], daily: 10,
    topics: [], theory: [], cards: [], edited: Date.now(), published: 0,
  };
  draftKey = uid(24);
  return draft;
}
// Тренажёр попадает в студию (и в облако) с первой правкой. Держим в студии именно этот объект:
// если облако успело заменить его своей копией, правка на открытом экране всё равно не теряется
function keep(p) {
  if (db.packs[p.id] !== p) db.packs[p.id] = p;
  // Ключ — у каждого тренажёра: черновик могли заменить новым (пример ещё грузился, а нажали «+ Создать»)
  db.keys[p.id] ||= p === draft ? draftKey : uid(24);
  if (p === draft) draft = null;
}

// Готовые наборы (packs/*.json) — один раз за открытие страницы
const packCache = {};
const packFile = id => (packCache[id] ||= loadPack(id, ROOT).catch(err => { delete packCache[id]; throw err; }));
let libList = null;
const library = () => (libList ||= loadLibrary(ROOT).then(l => {
  if (!l.length) throw new Error('Библиотека недоступна');
  return l;
}).catch(err => { libList = null; throw err; }));

// ---------- общий каркас ----------

function shell(p, tab, body) {
  // «Курс» — после первой публикации (или если курс уже начат): новичку он не нужен
  const course = p.published || p.course?.lessons?.length || p.course?.lives?.length || tab === 'course';
  const tabs = [['cards', `Карточки · ${p.cards.length}`], ['add', 'Добавить'], ...(course ? [['course', 'Курс']] : []),
    ['students', 'Ученики'], ['settings', 'Настройки'], ['publish', isPublished(p) ? 'Ссылка' : 'Опубликовать']];
  $app.innerHTML = `
    <header class="top pack-top">
      <a class="back" href="#/" aria-label="Все тренажёры">←</a>
      <div><div class="brand-title">${esc(p.title)}</div><div class="brand-by">${esc(p.tutor || 'Без имени репетитора')}${p.published && !isPublished(p) ? ' · есть неопубликованные правки' : ''}</div></div>
      <a class="btn small" href="${esc(previewLink(p.id))}" id="try" title="Посмотреть карточки глазами ученика">Попробовать</a>
      ${cabLink()}
    </header>
    <nav class="tabs" aria-label="Разделы тренажёра">${tabs.map(([id, t]) => `<a href="#/p/${p.id}/${id}" class="${tab === id ? 'on' : ''}" ${tab === id ? 'aria-current="page"' : ''}>${t}</a>`).join('')}</nav>
    <div id="tab"></div>`;
  $app.querySelector('#try').onclick = e => { e.preventDefault(); preview(p); };
  const box = $app.querySelector('#tab');
  box.innerHTML = body;
  return box;
}

// Просмотр набора глазами ученика: карточки по очереди без записи прогресса.
// Листалка — под карточкой: сверху справа крестик окна
function preview(p, start = 0, { intro = false } = {}) {
  if (!p.cards.length) return toast('Сначала добавьте карточки');
  let i = start;
  const { box } = modal(`<h3>Глазами ученика</h3>
    ${intro ? '<p class="muted pv-intro">Так ученик видит карточки: ответьте — появится разбор. Потом загляните во вкладку «Ученики» — там пример прогресса и отчёта родителям.</p>' : ''}
    <div class="pv"></div>`);
  const pv = box.querySelector('.pv');
  const draw = () => {
    const c = p.cards[i];
    pv.innerHTML = `
      <p class="muted pv-where">${i + 1} из ${p.cards.length} · ${esc(p.topics.find(t => t.id === c.t)?.title || '')}</p>
      <article class="card"></article>
      <div class="row pv-nav"><button class="btn" id="prev" aria-label="Предыдущая карточка">←</button>
        <button class="btn primary" id="nxt">Дальше →</button></div>`;
    renderCard(c, pv.querySelector('.card'), () => pv.querySelector('#nxt')?.focus({ preventScroll: true }), { imgRoot: ROOT });
    pv.querySelector('#prev').onclick = () => { i = (i - 1 + p.cards.length) % p.cards.length; draw(); };
    pv.querySelector('#nxt').onclick = () => { i = (i + 1) % p.cards.length; draw(); box.scrollTo?.(0, 0); };
  };
  draw();
}

// ---------- список наборов ----------

const SUBJECTS = [['rus', 'Русский'], ['math', 'Математика']];
let sampleSubj = 'rus';
const subjectSeg = () => `<div class="seg" role="radiogroup" aria-label="Предмет примера">${SUBJECTS.map(([id, t]) =>
  `<button type="button" role="radio" aria-checked="${id === sampleSubj}" class="${id === sampleSubj ? 'on' : ''}" data-subj="${id}">${t}</button>`).join('')}</div>`;

const packRow = p => `
  <a class="topic" href="#/p/${p.id}/cards"><span class="dot" style="background:${esc(p.color)}"></span>
    <span class="topic-title">${esc(p.title)}<small>${p.tutor ? esc(p.tutor) + ' · ' : ''}${plural(p.cards.length, 'карточка', 'карточки', 'карточек')}${p.sample ? ' · пример' : ''}</small></span>
    <span class="topic-meta">${isPublished(p) ? 'опубликован' : p.published ? 'есть правки' : 'черновик'}</span></a>`;

// Новый репетитор: один шаг — «Создайте первый тренажёр». Тариф, Telegram и «Курс» — потом
const firstStep = () => `
  <section class="panel first-step">
    <h1>Создайте первый тренажёр</h1>
    <p>Вставьте свой конспект или задачи — ИИ сделает карточки. Или возьмите готовые задания ЕГЭ с разборами. Потом отправите ученикам ссылку и будете видеть, кто занимался и где ошибки.</p>
    <div class="first-ways">
      <button class="btn primary big" id="new">Из своих материалов</button>
      <button class="btn big" id="new-lib">Готовые задания ЕГЭ</button>
    </div>
  </section>
  <section class="panel sample-box">
    <h2>Сначала посмотреть, как это работает?</h2>
    <p class="muted">Пример откроется глазами ученика, а во вкладке «Ученики» — как выглядят прогресс, ошибки и отчёт родителям.</p>
    <div class="sample-pick">${subjectSeg()}<button class="btn" id="sample">Готовый пример за 1 клик</button></div>
  </section>
  <p class="muted small-note studio-import">Есть файл тренажёра? <button class="link-btn" id="imp-btn">Импорт из файла</button><input type="file" accept=".json,application/json" id="imp" hidden></p>`;

function viewList() {
  const packs = Object.values(db.packs).filter(p => !isBlank(p)).sort((a, b) => b.edited - a.edited);
  const fresh = !packs.length;
  const published = packs.some(p => p.published);
  $app.innerHTML = `
    <header class="top studio-top"><a class="studio-mark" href="${ROOT}?about" aria-label="Между уроками — о сервисе"><img class="ld-mark" src="${ROOT}icons/icon-192.png" alt="" width="40" height="40"></a>
      <div><div class="brand-title">Студия</div>
      <div class="brand-by">Тренажёры для ваших учеников</div></div>
      <div class="acct-bar">${accountBar()}</div></header>
    ${fresh ? firstStep() : `
      <div class="list-head"><h2>Мои тренажёры</h2><button class="btn small primary" id="new">+ Создать</button></div>
      ${packs.map(packRow).join('')}
      <section class="panel more-ways">
        <div class="sample-pick"><span class="muted">Пример:</span>${subjectSeg()}<button class="btn small" id="sample">Готовый пример за 1 клик</button></div>
        <button class="btn small ghost" id="imp-btn">Импорт из файла</button><input type="file" accept=".json,application/json" id="imp" hidden>
      </section>`}
    ${published && signedIn() && apiBase() ? '<div id="tg-me"></div>' : ''}
    ${tariffPanel()}
    ${!signedIn() && !fresh ? `<section class="panel login-hint"><b>Войдите, чтобы ничего не потерять.</b> Сейчас тренажёры и доступ к ученикам хранятся только в этом браузере. С аккаунтом они сохраняются в облаке и открываются с телефона и компьютера. <a class="link-btn" href="${ROOT}login?role=tutor&next=studio/">Войти</a></section>` : ''}
    ${signedIn() ? accountPanel() : ''}
    ${apiBase() ? '' : `<section class="panel warn-box"><b>Сервер не подключён.</b> Собирать тренажёры и смотреть их можно, а ИИ, ссылки ученикам и отчёты заработают, когда появится связь с сервером.${DEBUG ? ' Адрес — во вкладке тренажёра «Настройки».' : ''}</section>`}
    <p class="muted small-note studio-help">Вопросы, идеи, хотите, чтобы тренажёр собрали за вас? <a href="https://t.me/trwqxp" target="_blank" rel="noopener">Напишите в Telegram @trwqxp</a></p>`;
  bindAccount($app);
  const tgSlot = $app.querySelector('#tg-me');
  if (tgSlot) tgPanel(tgSlot);
  $app.querySelector('#new').onclick = () => { location.hash = `#/p/${newPack().id}/add`; };
  $app.querySelector('#new-lib')?.addEventListener('click', () => { location.hash = `#/p/${newPack().id}/add/lib`; });
  $app.querySelectorAll('[data-subj]').forEach(b => {
    b.onclick = () => {
      sampleSubj = b.dataset.subj;
      $app.querySelectorAll('[data-subj]').forEach(x => { x.classList.toggle('on', x === b); x.setAttribute('aria-checked', x === b); });
    };
  });
  $app.querySelector('#sample').onclick = e => { openSample(sampleSubj, e.currentTarget); };
  $app.querySelector('#imp-btn').onclick = () => $app.querySelector('#imp').click();
  $app.querySelector('#imp').onchange = importFile;
}

async function importFile(e) {
  const f = e.target.files[0];
  e.target.value = '';
  if (!f) return;
  try {
    const data = JSON.parse(await f.text());
    // Копия, скачанная при выходе (account.js downloadBackup): тренажёры с ключами и прогресс
    if (data?.kind === 'mezhdu-urokami-backup') {
      const s = data.studio || {};
      const before = studioSig(db);
      db = mergeStudio(db, { packs: s.packs || {}, keys: s.keys || {}, deleted: {} });
      for (const [ref, prog] of Object.entries(data.progress || {})) if (prog && !store.get('zd-prog:' + ref, null)) store.set('zd-prog:' + ref, prog);
      if (studioSig(db) !== before) persist();
      toast(`Из копии: ${plural(Object.keys(s.packs || {}).length, 'тренажёр', 'тренажёра', 'тренажёров')}`);
      route();
      return;
    }
    if (!Array.isArray(data.cards) || !Array.isArray(data.topics)) throw new Error();
    const p = newPack();
    Object.assign(p, { ...data, id: p.id, published: 0 });
    delete p.sample;
    touch(p);
    location.hash = `#/p/${p.id}/cards`;
  } catch { toast('Это не файл тренажёра'); }
}

// ---------- готовый пример ----------

// Маленький набор по предмету (packs/sample-<предмет>.json); если его нет — три темы из библиотеки
const SAMPLES = {
  rus: { file: 'sample-rus', lib: 'ege-rus', topics: ['task-4', 'task-13', 'task-15'], title: 'Пример: русский, ЕГЭ', subject: 'Русский язык', color: COLORS[1] },
  math: { file: 'sample-math', lib: 'ege-math', topics: ['m-task-1', 'm-task-5', 'm-task-6'], title: 'Пример: математика, ЕГЭ', subject: 'Математика', color: COLORS[2] },
};

async function makeSample(subj) {
  const s = SAMPLES[subj] || SAMPLES.rus;
  // Пример по этому предмету уже есть (может быть, пока только в облаке) — открываем его, а не копим копии
  if (signedIn() && !cloudReady) await syncCloud();
  const have = Object.values(db.packs).find(p => p.sample === subj);
  if (have) return have;
  let src, tids;
  try {
    src = await packFile(s.file);
    tids = src.topics.map(t => t.id);
  } catch {
    src = await packFile(s.lib);
    tids = s.topics;
  }
  const p = newPack();
  Object.assign(p, { title: s.title, subject: s.subject, color: s.color, sample: subj });
  if (!importTopics(p, src, tids)) throw new Error('в примере нет карточек');
  touch(p);
  return p;
}

// Пример → его карточки и сразу окно «Глазами ученика». replace — пришли по ссылке #/sample
let sampleBusy = false; // пример уже готовится (перерисовка экрана не запускает второй)
async function openSample(subj, btn, { replace = false } = {}) {
  if (sampleBusy) return;
  sampleBusy = true;
  const from = location.hash;
  if (btn) btn.disabled = true;
  try {
    const p = await makeSample(subj);
    if (location.hash !== from) { toast('Пример готов — он в списке тренажёров'); return; } // пока грузили, ушли на другой экран
    const url = `#/p/${p.id}/cards`;
    if (replace) history.replaceState(null, '', url); else history.pushState(null, '', url);
    lastHash = location.hash;
    scrollTo(0, 0);
    route();
    preview(p, 0, { intro: true });
  } catch (err) {
    toast(`Не получилось загрузить пример: ${err.message}`);
    if (btn?.isConnected) btn.disabled = false;
    if (replace && !btn) { sampleBusy = false; viewSampleStart(); }
  } finally { sampleBusy = false; }
}

// studio/#/sample — «Попробовать» с главной: выбрать предмет; #/sample/rus — сразу пример
function viewSampleStart(subj) {
  if (SAMPLES[subj]) {
    $app.innerHTML = '<p class="loading">Готовлю пример…</p>';
    return openSample(subj, null, { replace: true });
  }
  if (sampleBusy) { $app.innerHTML = '<p class="loading">Готовлю пример…</p>'; return; }
  $app.innerHTML = `
    <header class="top"><a class="back" href="#/" aria-label="В студию">←</a>
      <div><div class="brand-title">Готовый пример</div><div class="brand-by">Студия · Между уроками</div></div>
      <div class="acct-bar">${accountBar()}</div></header>
    <section class="panel first-step sample-start">
      <h1>Посмотрите, как это работает</h1>
      <p>Откроем небольшой тренажёр глазами ученика. А во вкладке «Ученики» покажем, что увидите вы: кто занимался, где ошибки и готовый отчёт родителям.</p>
      <p><b>Какой предмет?</b></p>
      <div class="first-ways"><button class="btn primary big" data-sample="rus">Русский язык</button><button class="btn big" data-sample="math">Математика</button></div>
    </section>
    <p class="muted small-note">Или сразу <a href="#/new">соберите свой тренажёр</a> из своих материалов.</p>`;
  $app.querySelectorAll('[data-sample]').forEach(b => { b.onclick = () => { openSample(b.dataset.sample, b, { replace: true }); }; });
}

// ---------- служебные экраны ----------

// Ссылка на тренажёр, которого в этом браузере ещё нет: облако не ответило
function viewWaiting() {
  $app.innerHTML = `
    <header class="top"><a class="back" href="#/" aria-label="Все тренажёры">←</a><div><div class="brand-title">Студия</div></div><div class="acct-bar">${accountBar()}</div></header>
    <p class="loading" id="wait">Загружаю тренажёр…</p>`;
  setTimeout(() => {
    const w = document.getElementById('wait');
    if (w && !cloudReady) w.innerHTML = 'Загружаю тренажёр…<br><span class="small-note">Долго? Проверьте интернет или <a href="#/">откройте список тренажёров</a>.</span>';
  }, 8000);
}

function viewMissing() {
  $app.innerHTML = `
    <header class="top"><a class="back" href="#/" aria-label="Все тренажёры">←</a><div><div class="brand-title">Студия</div></div><div class="acct-bar">${accountBar()}</div></header>
    <section class="panel empty missing">
      ${cloudFailed ? '<p><b>Не получилось загрузить тренажёр — нет связи с сервером.</b></p><button class="btn primary" id="retry">Повторить</button>'
        : `<p><b>Тренажёр не найден.</b> ${signedIn() ? 'Возможно, его удалили или он в другом аккаунте.' : 'Если он в вашем аккаунте — войдите.'}</p>`}
      ${!signedIn() && !cloudFailed ? '<button class="btn primary" id="login-here">Войти</button>' : ''}
      <a class="btn" href="#/">Все тренажёры</a>
    </section>`;
  $app.querySelector('#retry')?.addEventListener('click', e => {
    e.currentTarget.disabled = true;
    cloudReady = false;
    viewWaiting();
    syncCloud();
  });
  $app.querySelector('#login-here')?.addEventListener('click', () => login({ then: async () => route() }));
}

// ---------- карточки ----------

function viewCards(p) {
  const f = store.get('zd-studio-filter', { q: '', t: '' });
  // Пример ещё не опубликован — подсказываем, что в нём посмотреть
  const guide = p.sample && !p.published ? `
    <section class="panel sample-guide">
      <p><b>Это пример тренажёра.</b> Посмотрите, что получат ученики и что увидите вы, — и отправьте ссылку, если подходит.</p>
      <div class="row">
        <button class="btn primary" id="g-try">Глазами ученика</button>
        <a class="btn" href="#/p/${p.id}/students">Ученики и отчёт родителям</a>
        <a class="btn" href="#/p/${p.id}/publish">Отправить ученикам</a>
      </div>
      <p class="muted small-note">Свой тренажёр — из ваших материалов или заданий ЕГЭ: <a href="#/new">создать</a>.</p>
    </section>` : '';
  const box = shell(p, 'cards', `${guide}
    <div class="row toolbar">
      <input id="q" placeholder="Поиск по тексту" value="${esc(f.q)}" aria-label="Поиск по тексту карточек">
      <select id="t" aria-label="Тема"><option value="">Все темы</option>${p.topics.map(t =>
        `<option value="${esc(t.id)}" ${f.t === t.id ? 'selected' : ''}>${esc(t.title)} · ${p.cards.filter(c => c.t === t.id).length}</option>`).join('')}</select>
      <button class="btn" id="add">+ Карточка</button>
    </div>
    <div id="list"></div>`);
  const list = box.querySelector('#list');
  const draw = () => {
    const q = f.q.toLowerCase();
    const cards = p.cards.map((c, i) => [c, i]).filter(([c]) => (!f.t || c.t === f.t) && (!q || c.q.toLowerCase().includes(q)));
    if (!p.cards.length) {
      list.innerHTML = `<div class="panel empty">Карточек пока нет. <a href="#/p/${p.id}/add">Добавьте из материалов или библиотеки</a>.</div>`;
      return;
    }
    const shownCards = cards.slice(0, 200);
    list.innerHTML = shownCards.map(([c, i]) => `
      <div class="card-row" data-i="${i}">
        <span class="badge">${KIND_NAMES[c.k] || c.k}</span>
        <span class="card-row-q">${esc(c.q.slice(0, 160))}${c.q.length > 160 ? '…' : ''}</span>
        <span class="card-row-actions">
          <button class="btn small" data-a="view">Открыть</button>
          ${c.k === 'match' || c.k === 'stress' ? '' : '<button class="btn small" data-a="edit">Изменить</button>'}
          ${c.k === 'stress' || !apiBase() ? '' : '<button class="btn small" data-a="more" title="ИИ сделает новые варианты этого типа">Похожие</button>'}
          <button class="btn small danger" data-a="del" aria-label="Удалить">✕</button>
        </span>
      </div>`).join('') + (cards.length > shownCards.length ? `<p class="muted center">Показаны первые 200 из ${cards.length} — уточните поиск</p>` : '');
  };
  draw();
  box.querySelector('#g-try')?.addEventListener('click', () => preview(p, 0, { intro: true }));
  box.querySelector('#q').oninput = e => { f.q = e.target.value; store.set('zd-studio-filter', f); draw(); };
  box.querySelector('#t').onchange = e => { f.t = e.target.value; store.set('zd-studio-filter', f); draw(); };
  box.querySelector('#add').onclick = () => editCard(p, null, draw);
  list.onclick = e => {
    const b = e.target.closest('button');
    if (!b) return;
    const i = +b.closest('.card-row').dataset.i;
    if (b.dataset.a === 'view') preview(p, i);
    if (b.dataset.a === 'edit') editCard(p, i, draw);
    if (b.dataset.a === 'more') { if (!signedIn()) return login({ why: 'Похожие карточки делает ИИ — для вошедших репетиторов.', then: () => route() }); similarCards(p, p.cards[i], draw); }
    if (b.dataset.a === 'del' && confirm('Удалить карточку?')) { p.cards.splice(i, 1); touch(p); draw(); }
  };
}

// Ошибка ИИ — по-человечески: что случилось и что делать (текст и файлы остаются на месте)
function aiErrorText(err) {
  if (!err.status) return 'Нет связи с сервером — проверьте интернет.';
  if (err.status === 413) return 'Материал слишком большой — разбейте его на части.';
  if (err.status >= 500 && /^Ошибка сервера/.test(err.message)) return 'ИИ сейчас недоступен.';
  return err.message;
}

// «Похожие»: ИИ делает новые варианты того же типа (прототипа) с другими данными.
// Новые карточки попадают в ту же тему и прототип, что и исходная.
async function similarCards(p, src, onAdd) {
  const kind = src.k === 'match' || src.k === 'many' ? 'one' : src.k;
  const opts = src.o && !src.o.left ? '\nВарианты: ' + src.o.map(o => `${o.id}) ${o.t}`).join('; ') : '';
  const answer = Array.isArray(src.a) ? src.a.join(', ') : typeof src.a === 'object' ? JSON.stringify(src.a) : src.a;
  const material = `Образец карточки (тип "${kind}"):\nВопрос: ${src.q}${opts}\nОтвет: ${answer}${src.e ? '\nРазбор: ' + src.e : ''}\n\n`
    + 'Сделай новые карточки ТОГО ЖЕ прототипа и того же типа: та же проверяемая идея и формат ответа, '
    + 'но другие слова, числа или примеры. Не повторяй образец. Все ответы перепроверь.';
  const { box, close } = modal('<h3>Похожие карточки</h3><p class="muted" id="sim-note"></p><div id="sim-out"></div>');
  const note = box.querySelector('#sim-note'), out = box.querySelector('#sim-out');
  const run = async () => {
    note.textContent = 'ИИ делает новые варианты этого типа — до минуты…';
    out.innerHTML = '';
    let r;
    try {
      r = await ai('generate', { material, subject: p.subject, count: 5 });
    } catch (err) {
      note.textContent = '';
      out.innerHTML = `<div class="ai-fail" role="alert"><p><b>${esc(aiErrorText(err))}</b></p>${err.status === 429 ? '' : '<button class="btn" id="sim-retry">Повторить</button>'}</div>`;
      out.querySelector('#sim-retry')?.addEventListener('click', run);
      return;
    }
    note.textContent = 'Снимите галочку с неудачных — остальные добавятся в ту же тему.';
    out.innerHTML = `<div class="gen-list">${r.cards.map((c, i) => `
      <label class="gen-card"><input type="checkbox" checked data-i="${i}">
        <span><span class="badge">${KIND_NAMES[c.k]}</span><br><b>${text(c.q)}</b>
        ${c.o ? `<ul>${c.o.map(o => `<li class="${(Array.isArray(c.a) ? c.a : [c.a]).includes(o.id) ? 'right' : ''}">${esc(o.id)}) ${esc(o.t)}</li>`).join('')}</ul>` : `<br><span class="muted">Ответ: ${text(c.a)}</span>`}
        </span></label>`).join('')}</div>
      <button class="btn primary" id="sim-take">Добавить выбранные</button>`;
    out.querySelector('#sim-take').onclick = () => {
      const picked = [...out.querySelectorAll('input:checked')].map(x => r.cards[+x.dataset.i]);
      for (const c of picked) {
        const { t, ...rest } = c;
        p.cards.push({ ...rest, id: 'c-' + uid(6), t: src.t, ...(src.p ? { p: src.p } : {}) });
      }
      touch(p);
      close();
      toast(`Добавлено ${plural(picked.length, 'карточка', 'карточки', 'карточек')}`);
      onAdd();
    };
  };
  run();
}

// Редактор карточки. id полей — свои (ce-…): у вкладки «Карточки» за окном тоже есть #q и #t
function editCard(p, index, onSave) {
  const c = index === null ? { k: 'one', t: p.topics[0]?.id || '', q: '', o: [], a: '' } : structuredClone(p.cards[index]);
  const opts = c.k === 'one' || c.k === 'many' ? c.o : [{ id: 'а', t: '' }, { id: 'б', t: '' }, { id: 'в', t: '' }, { id: 'г', t: '' }];
  const right = new Set(c.k === 'many' ? c.a : c.k === 'one' ? [c.a] : []);
  const { box, close } = modal(`
    <h3>${index === null ? 'Новая карточка' : 'Карточка'}</h3>
    <div class="grid2">
      <div class="field"><label for="ce-t">Тема</label><select id="ce-t">${p.topics.map(t => `<option value="${esc(t.id)}" ${t.id === c.t ? 'selected' : ''}>${esc(t.title)}</option>`).join('')}<option value="__new">+ Новая тема…</option></select></div>
      <div class="field"><label for="ce-k">Тип</label><select id="ce-k">${['one', 'many', 'flip', 'num', 'word', 'seq', 'open'].map(k => `<option value="${k}" ${k === c.k ? 'selected' : ''}>${KIND_NAMES[k]}</option>`).join('')}</select></div>
    </div>
    <div class="field"><label for="ce-q">Вопрос или условие</label><textarea id="ce-q" rows="4">${esc(c.q)}</textarea></div>
    <div id="ce-opts" class="field"><span>Варианты — отметьте верные</span>
      <div id="ce-optlist">${opts.map(o => optRow(o, right.has(o.id))).join('')}</div>
      <button class="btn small" id="ce-addopt">+ Вариант</button></div>
    <div class="field" id="ce-ans"><label for="ce-a" id="ce-ans-l">Ответ</label><textarea id="ce-a" rows="4">${esc(['flip', 'open', 'num', 'word', 'text', 'seq'].includes(c.k) ? c.a : '')}</textarea></div>
    <div class="field"><label for="ce-e">Разбор (необязательно)</label><textarea id="ce-e" rows="3">${esc(c.e || '')}</textarea></div>
    <div class="row"><button class="btn primary" id="ce-save">Сохранить</button><button class="btn ghost" id="ce-cancel">Отмена</button></div>`);
  const $ = s => box.querySelector(s);
  const sync = () => {
    const k = $('#ce-k').value;
    $('#ce-opts').hidden = !(k === 'one' || k === 'many');
    $('#ce-ans').hidden = !$('#ce-opts').hidden;
    $('#ce-ans-l').textContent = k === 'open' ? 'Эталонное решение с ответом' : k === 'num' ? 'Ответ — число (например, 0,35)'
      : k === 'word' ? 'Ответ словом; несколько допустимых — через | (например, «неверно|не верно»)'
      : k === 'seq' ? 'Ответ — цифры по порядку (например, 2413)' : 'Ответ';
  };
  sync();
  $('#ce-k').onchange = sync;
  $('#ce-t').onchange = e => {
    if (e.target.value !== '__new') return;
    const title = prompt('Название темы');
    if (!title) { e.target.value = p.topics[0]?.id || ''; return; }
    const id = 'u-' + uid(5);
    p.topics.push({ id, title });
    e.target.insertAdjacentHTML('afterbegin', `<option value="${id}">${esc(title)}</option>`);
    e.target.value = id;
  };
  $('#ce-addopt').onclick = () => {
    const ids = 'абвгдежзик';
    const n = $('#ce-optlist').children.length;
    $('#ce-optlist').insertAdjacentHTML('beforeend', optRow({ id: ids[n] || String(n + 1), t: '' }, false));
  };
  $('#ce-optlist').onclick = e => { if (e.target.closest('.rm')) e.target.closest('.opt-edit').remove(); };
  $('#ce-cancel').onclick = () => { close(); };
  $('#ce-save').onclick = () => {
    const k = $('#ce-k').value;
    const card = { id: c.id || 'c-' + uid(6), t: $('#ce-t').value, k, q: $('#ce-q').value.trim() };
    if (!card.t || card.t === '__new') return toast('Выберите тему');
    if (!card.q) return toast('Напишите вопрос');
    if (k === 'one' || k === 'many') {
      const rows = [...box.querySelectorAll('.opt-edit')].map(r => ({ id: r.dataset.id, t: r.querySelector('input[type=text]').value.trim(), ok: r.querySelector('input[type=checkbox]').checked }))
        .filter(o => o.t);
      const oks = rows.filter(o => o.ok).map(o => o.id);
      if (rows.length < 2) return toast('Нужно хотя бы два варианта');
      if (!oks.length) return toast('Отметьте верный вариант');
      if (k === 'one' && oks.length > 1) return toast('Для «одного ответа» отметьте один вариант');
      card.o = rows.map(({ id, t }) => ({ id, t }));
      card.a = k === 'one' ? oks[0] : oks;
    } else {
      card.a = $('#ce-a').value.trim();
      if (!card.a) return toast('Напишите ответ');
      if (k === 'num' && !/^-?\d+([.,]\d+)?$/.test(card.a)) return toast('Для числового ответа нужно число: 12 или 0,35');
      if (k === 'seq' && !/^\d{2,}$/.test(card.a)) return toast('Для последовательности нужны цифры без пробелов: 2413');
    }
    const e = $('#ce-e').value.trim();
    if (e) card.e = e;
    for (const key of ['src', 'img']) if (c[key]) card[key] = c[key];
    if (index === null) p.cards.push(card); else p.cards[index] = card;
    touch(p);
    close();
    onSave();
  };
}

const optRow = (o, ok) => `<div class="opt-edit row" data-id="${esc(o.id)}">
  <input type="checkbox" ${ok ? 'checked' : ''} aria-label="верный"><b>${esc(o.id)}</b>
  <input type="text" value="${esc(o.t)}" placeholder="Вариант" aria-label="Вариант ${esc(o.id)}"><button class="btn small ghost rm" aria-label="Убрать">✕</button></div>`;

// ---------- добавление: ИИ и библиотека ----------

function viewAdd(p, sub) {
  // Набранный материал живёт в sessionStorage: не пропадёт ни при перерисовке, ни при ошибке ИИ
  const matKey = 'zd-mat:' + p.id;
  const box = shell(p, 'add', `
    <section class="panel" id="mat-panel">
      <h2>Из ваших материалов</h2>
      <p class="muted">Вставьте конспект, правила или разбор задач — или загрузите PDF и фото страниц. ИИ сделает карточки, а вы проверите их перед добавлением.</p>
      <div class="field"><label for="mat">Материал</label><textarea id="mat" rows="10" placeholder="Например: правила пунктуации при причастном обороте с примерами…">${esc(tabStore.get(matKey) || '')}</textarea></div>
      <div class="row gen-row">
        <button class="btn small" id="file-btn" type="button">+ PDF, фото или .txt</button><input type="file" accept=".txt,.md,.csv,.pdf,application/pdf,image/*" id="file" multiple hidden>
        <span class="row inline"><label for="count">Карточек:</label><input id="count" class="count-input" type="number" inputmode="numeric" min="5" max="40" value="15"></span>
        <button class="btn primary" id="gen" ${apiBase() ? '' : 'disabled'}>Сделать карточки</button>
      </div>
      ${apiBase() ? '' : `<p class="muted">Сервер ИИ не подключён${DEBUG ? ' — укажите адрес во вкладке «Настройки»' : ''}.</p>`}
      <div id="att" class="att"></div>
      <div id="gen-out"></div>
    </section>
    <section class="panel" id="lib-panel">
      <h2>Из библиотеки</h2>
      <p class="muted">Готовые задания с разборами. Выберите тему — карточки и теория по ней добавятся в ваш тренажёр.</p>
      <div id="lib"><p class="muted">Загружаю…</p></div>
    </section>`);

  const mat = box.querySelector('#mat');
  mat.oninput = () => tabStore.set(matKey, mat.value || null);
  const files = [];
  const drawAtt = () => {
    box.querySelector('#att').innerHTML = files.map((f, i) =>
      `<span class="chip">${f.mime === 'application/pdf' ? 'PDF' : 'Фото'} · ${esc(f.name)}<button data-rm="${i}" aria-label="Убрать">✕</button></span>`).join('');
  };
  box.querySelector('#att').onclick = e => {
    const b = e.target.closest('[data-rm]');
    if (b) { files.splice(+b.dataset.rm, 1); drawAtt(); }
  };
  box.querySelector('#file-btn').onclick = () => box.querySelector('#file').click();
  box.querySelector('#file').onchange = async e => {
    for (const f of e.target.files) {
      try {
        const a = await readAttachment(f);
        if (a.text !== undefined) {
          mat.value = (mat.value ? mat.value + '\n\n' : '') + a.text.slice(0, 30000);
          tabStore.set(matKey, mat.value);
        } else {
          if (files.reduce((n, x) => n + x.data.length, 0) + a.data.length > MAX_ATTACH) throw new Error('Слишком много файлов за раз — до 10 МБ всего');
          files.push({ name: f.name, ...a });
        }
      } catch (err) { toast(`${f.name}: ${err.message}`); }
    }
    e.target.value = '';
    drawAtt();
  };
  const toLibrary = () => {
    box.querySelector('#lib-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
    box.querySelector('#lib [data-id]')?.focus({ preventScroll: true });
  };
  const gen = async () => {
    const material = mat.value.trim();
    if (material.length < 80 && !files.length) return toast('Добавьте текст (хотя бы абзац), PDF или фото');
    // ИИ — только с аккаунтом (лимит и расходы — на аккаунт). Вставленный текст сохранён в этой вкладке
    if (!signedIn()) return login({ why: 'ИИ делает карточки из материалов для вошедших репетиторов. Вставленный текст не пропадёт.', then: () => route() });
    const out = box.querySelector('#gen-out'), btn = box.querySelector('#gen');
    btn.disabled = true;
    out.innerHTML = `<p class="muted">ИИ читает материал и делает карточки — это до ${files.length ? 'двух минут' : 'минуты'}…</p>`;
    try {
      const r = await ai('generate', { material, subject: p.subject, count: +box.querySelector('#count').value || 15,
        files: files.map(({ mime, data }) => ({ mime, data })) });
      if (out.isConnected) reviewGenerated(p, r, out, () => tabStore.set(matKey, null));
    } catch (err) {
      if (!out.isConnected) return;
      out.innerHTML = `<div class="ai-fail" role="alert">
        <p><b>${esc(aiErrorText(err))}</b> Ваш текст сохранён — он остался в поле выше${files.length ? ', файлы тоже' : ''}.</p>
        <div class="row">${err.status === 429 ? '' : '<button class="btn primary" id="gen-retry">Повторить</button>'}<button class="btn" id="gen-lib">Взять из библиотеки</button></div></div>`;
      out.querySelector('#gen-retry')?.addEventListener('click', () => { gen(); });
      out.querySelector('#gen-lib').onclick = toLibrary;
    }
    btn.disabled = false;
  };
  box.querySelector('#gen').onclick = () => { gen(); };
  drawLibrary(p, box.querySelector('#lib'));
  // «Готовые задания ЕГЭ» из первого шага — сразу к библиотеке
  if (sub === 'lib') requestAnimationFrame(() => box.querySelector('#lib-panel').scrollIntoView({ block: 'start' }));
}

function reviewGenerated(p, { topics, cards }, out, onTaken) {
  const tmap = Object.fromEntries(topics.map(t => [t.id, t.title]));
  out.innerHTML = `
    <h3>Проверьте карточки</h3>
    <p class="muted">Снимите галочку с неудачных. Поправить текст можно после добавления.</p>
    <div class="gen-list">${cards.map((c, i) => `
      <label class="gen-card">
        <input type="checkbox" checked data-i="${i}">
        <span><span class="badge">${KIND_NAMES[c.k]}</span> <span class="muted">${esc(tmap[c.t] || '')}</span><br>
          <b>${text(c.q)}</b>
          ${c.o ? `<ul>${c.o.map(o => `<li class="${(Array.isArray(c.a) ? c.a : [c.a]).includes(o.id) ? 'right' : ''}">${esc(o.id)}) ${esc(o.t)}</li>`).join('')}</ul>` : `<br><span class="muted">Ответ: ${text(c.a)}</span>`}
        </span>
      </label>`).join('')}</div>
    <button class="btn primary" id="take">Добавить выбранные</button>`;
  out.querySelector('#take').onclick = () => {
    const picked = [...out.querySelectorAll('input:checked')].map(i => cards[+i.dataset.i]);
    if (!picked.length) return toast('Ничего не выбрано');
    // Темы из ответа ИИ получают свои id, чтобы не пересечься с существующими
    const ids = {};
    for (const t of topics) {
      if (!picked.some(c => c.t === t.id)) continue;
      const same = p.topics.find(x => x.title.toLowerCase() === t.title.toLowerCase());
      ids[t.id] = same ? same.id : 'g-' + uid(5);
      if (!same) p.topics.push({ id: ids[t.id], title: t.title });
    }
    for (const c of picked) p.cards.push({ ...c, id: 'c-' + uid(6), t: ids[c.t] });
    touch(p);
    onTaken?.();
    toast(`Добавлено ${plural(picked.length, 'карточка', 'карточки', 'карточек')}`);
    location.hash = `#/p/${p.id}/cards`;
  };
}

// Переносит темы библиотеки в набор репетитора вместе с карточками и теорией
function importTopics(p, src, tids) {
  const have = new Set(p.cards.map(c => c.id));
  let n = 0;
  for (const tid of tids) {
    const t = src.topics.find(x => x.id === tid);
    if (!t) continue;
    if (!p.topics.some(x => x.id === tid)) {
      // Номер задания, баллы и прототипы переносятся — у учеников будет сетка заданий и пробник
      const { id, title, n, pts, protos } = t;
      p.topics.push({ id, title, section: src.title, ...(n ? { n, pts } : {}), ...(protos ? { protos } : {}) });
    }
    for (const c of src.cards) if (c.t === tid && !have.has(c.id)) { p.cards.push(c); have.add(c.id); n++; }
    for (const l of src.theory || []) if (l.topic === tid && !p.theory.some(x => x.id === l.id)) p.theory.push(l);
  }
  if (!p.subject) p.subject = src.subject;
  return n;
}

// PDF и фото уходят в ИИ как вложения; фото уменьшаем, чтобы не гонять мегабайты
const MAX_ATTACH = 14e6; // символов base64 ≈ 10 МБ
const toBase64 = blob => new Promise((ok, fail) => {
  const r = new FileReader();
  r.onload = () => ok(String(r.result).split(',')[1]);
  r.onerror = () => fail(new Error('не удалось прочитать файл'));
  r.readAsDataURL(blob);
});
async function readAttachment(f) {
  if (/^text\//.test(f.type) || /\.(txt|md|csv)$/i.test(f.name)) return { text: await f.text() };
  if (f.type === 'application/pdf' || /\.pdf$/i.test(f.name)) {
    if (f.size > 10e6) throw new Error('PDF больше 10 МБ — разбейте на части');
    return { mime: 'application/pdf', data: await toBase64(f) };
  }
  if (f.type.startsWith('image/') || /\.(heic|jpe?g|png|webp)$/i.test(f.name)) {
    try {
      const img = await createImageBitmap(f);
      const k = Math.min(1, 1600 / Math.max(img.width, img.height));
      const c = document.createElement('canvas');
      c.width = Math.round(img.width * k);
      c.height = Math.round(img.height * k);
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      const blob = await new Promise(ok => c.toBlob(ok, 'image/jpeg', 0.85));
      return { mime: 'image/jpeg', data: await toBase64(blob) };
    } catch {
      if (f.size > 8e6) throw new Error('фото слишком большое');
      return { mime: f.type || 'image/jpeg', data: await toBase64(f) };
    }
  }
  throw new Error('поддерживаются PDF, фото и .txt');
}

// Не загрузилось (плохая сеть) — говорим об этом и даём повторить, а не «Загружаю…» навсегда
function loadFailed(where, msg, retry) {
  where.innerHTML = `<div class="ai-fail" role="alert"><p><b>${esc(msg)}</b> Проверьте интернет.</p><button class="btn" data-retry>Повторить</button></div>`;
  where.querySelector('[data-retry]').onclick = retry;
}

async function drawLibrary(p, box) {
  box.innerHTML = '<p class="muted">Загружаю…</p>';
  let lib;
  try { lib = await library(); } catch { if (box.isConnected) loadFailed(box, 'Не получилось загрузить библиотеку.', () => drawLibrary(p, box)); return; }
  if (!box.isConnected) return;
  box.innerHTML = `<div class="row lib-row">${lib.map(l => `<button class="btn" data-id="${esc(l.id)}">${esc(l.title)} · ${l.cards}</button>`).join('')}</div><div id="lib-topics"></div>`;
  const out = box.querySelector('#lib-topics');
  const open = async b => {
    box.querySelectorAll('[data-id]').forEach(x => x.classList.toggle('primary', x === b));
    out.innerHTML = '<p class="muted">Загружаю…</p>';
    let src;
    try { src = await packFile(b.dataset.id); } catch {
      if (!b.classList.contains('primary')) return; // уже выбрали другой набор
      b.classList.remove('primary');
      loadFailed(out, `Не получилось загрузить «${b.textContent.split(' · ')[0]}».`, () => open(b));
      return;
    }
    if (!out.isConnected || !b.classList.contains('primary')) return;
    const have = new Set(p.cards.map(c => c.id));
    out.innerHTML = `<div class="lib-topics">${src.topics.map(t => {
      const n = src.cards.filter(c => c.t === t.id).length;
      const added = n && src.cards.filter(c => c.t === t.id).every(c => have.has(c.id));
      return `<label class="gen-card"><input type="checkbox" data-t="${esc(t.id)}" ${added ? 'disabled checked' : ''}>
        <span>${esc(t.title)} <span class="muted">· ${plural(n, 'карточка', 'карточки', 'карточек')}${t.protos ? ` · ${plural(t.protos.length, 'прототип', 'прототипа', 'прототипов')}` : ''}${added ? ' · уже добавлена' : ''}</span></span></label>`;
    }).join('')}</div>
      <button class="btn primary" id="lib-take">Добавить выбранные темы</button>`;
    out.querySelector('#lib-take').onclick = () => {
      const tids = [...out.querySelectorAll('input:checked:not(:disabled)')].map(i => i.dataset.t);
      if (!tids.length) return toast('Выберите темы');
      const n = importTopics(p, src, tids);
      touch(p);
      toast(`Добавлено ${plural(n, 'карточка', 'карточки', 'карточек')}`);
      location.hash = `#/p/${p.id}/cards`;
    };
  };
  box.querySelectorAll('[data-id]').forEach(b => { b.onclick = () => { open(b); }; });
}

// ---------- ученики ----------

const ago = ts => {
  const m = Math.round((Date.now() - ts) / 60000);
  if (m < 60) return m < 2 ? 'только что' : `${m} мин назад`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} ч назад`;
  const d = Math.round(h / 24);
  return d === 1 ? 'вчера' : `${plural(d, 'день', 'дня', 'дней')} назад`;
};

function weakTopics(p, st) {
  return Object.entries(st.topics || {})
    .filter(([, t]) => t.acc !== null && t.s >= 3)
    .sort((a, b) => a[1].acc - b[1].acc)
    .slice(0, 3)
    .filter(([, t]) => t.acc < 80)
    .map(([id, t]) => ({ title: p.topics.find(x => x.id === id)?.title || id, acc: t.acc }));
}

// 14 квадратиков по дням: пустой — не занимался, чем темнее — тем больше карточек.
// Сводка сдвигается на дни, прошедшие с её отправки, чтобы последний квадрат был «сегодня».
function activityStrip(st) {
  if (!Array.isArray(st.days)) return '';
  const shift = Math.max(0, Math.min(14, day() - (st.day ?? day())));
  const days = [...st.days.slice(shift), ...Array(shift).fill(0)];
  const level = n => n === 0 ? 0 : n < 5 ? 1 : n < 15 ? 2 : 3;
  return `<div class="strip" title="Карточек по дням за 2 недели">${days.map((n, i) =>
    `<i class="l${level(n)}" title="${i === 13 ? 'сегодня' : `${13 - i} дн. назад`}: ${n}"></i>`).join('')}</div>`;
}

// Точность по неделям: высота столбика — точность, подпись — сколько карточек
function weekAcc(w) {
  return w?.d ? Math.round(w.ok / w.d * 100) : null;
}

function weeksChart(st) {
  if (!Array.isArray(st.weeks) || !st.weeks.some(w => w.d)) return '';
  const cols = st.weeks.map((w, i) => {
    const acc = weekAcc(w);
    const tone = acc === null ? '' : acc < 60 ? 'bad' : acc < 80 ? 'mid' : 'ok';
    const label = i === 7 ? 'эта' : `−${7 - i}`;
    return `<div class="wk ${tone}" title="${i === 7 ? 'Последние 7 дней' : `${7 - i} нед. назад`}: ${w.d} карточек">
      <b>${acc === null ? '—' : acc + '%'}</b><span class="wk-bar"><i style="height:${acc ?? 0}%"></i></span>
      <small>${w.d || ''}</small><em>${label}</em></div>`;
  }).join('');
  return `<div class="weeks">${cols}</div><p class="muted small-note">Под столбиком — сколько карточек решено за неделю</p>`;
}

// Динамика для отчёта: эта неделя против предыдущей активной
function trend(st) {
  const ws = (st.weeks || []).filter(w => w.d);
  if (ws.length < 2) return '';
  const now = weekAcc(st.weeks.at(-1)), before = weekAcc(ws.at(-2));
  if (now === null || before === null || !st.weeks.at(-1).d) return '';
  const diff = now - before;
  return diff > 0 ? ` (было ${before}%, +${diff})` : diff < 0 ? ` (было ${before}%)` : ' (как и неделей раньше)';
}

// «Что разобрать на уроке»: карточки и темы, где ошибается больше всего учеников
function lessonPlan(p, students) {
  const byId = Object.fromEntries(p.cards.map(c => [c.id, c]));
  const cardErr = new Map();
  for (const s of students) for (const id of new Set(s.stats.errs || [])) {
    if (byId[id]) cardErr.set(id, [...(cardErr.get(id) || []), s.name]);
  }
  const topicWeak = new Map();
  for (const s of students) for (const w of weakTopics(p, s.stats)) {
    topicWeak.set(w.title, [...(topicWeak.get(w.title) || []), `${s.name} ${w.acc}%`]);
  }
  const cards = [...cardErr.entries()].sort((a, b) => b[1].length - a[1].length).slice(0, 8);
  const topics = [...topicWeak.entries()].sort((a, b) => b[1].length - a[1].length).slice(0, 5);
  if (!cards.length && !topics.length) return '';
  const who = names => names.length > 3 ? `${names.slice(0, 3).join(', ')} и ещё ${names.length - 3}` : names.join(', ');
  return `<section class="panel plan lesson-plan">
    <h2>Что разобрать на уроке</h2>
    ${topics.length ? `<h3>Темы, которые проседают</h3><ul>${topics.map(([t, n]) =>
      `<li><b>${esc(t)}</b> <span class="muted">— ${esc(who(n))}</span></li>`).join('')}</ul>` : ''}
    ${cards.length ? `<h3>Задания, где ошибаются чаще всего</h3><ol>${cards.map(([id, n]) =>
      `<li>${esc(byId[id].q.replace(/\s+/g, ' ').slice(0, 160))}${byId[id].q.length > 160 ? '…' : ''}
        <span class="plan-who">${plural(n.length, 'ученик', 'ученика', 'учеников')}: ${esc(who(n))}</span></li>`).join('')}</ol>` : ''}
    <button class="btn small" id="copy-plan">Скопировать план урока</button>
  </section>`;
}

// Сколько карточек задания решил ученик: счётчик в сводке относится к заданию с тем же id
const hwDone = (st, hw) => (hw && st.hw?.id === hw.id ? Math.max(0, Math.floor(st.hw.d) || 0) : 0);

// ДЗ курса из сводки ученика ({n, onTime}); числа приходят от ученика — только целые, onTime ≤ n
const courseDone = st => {
  const n = Math.max(0, Math.floor(st.course?.n) || 0);
  return { n, onTime: Math.min(n, Math.max(0, Math.floor(st.course?.onTime) || 0)) };
};

// Строки о задании и ДЗ курса — слово в слово как в отчёте бота родителю (worker/notify.js parentReportText)
function parentReport(p, s, hw) {
  const st = s.stats;
  const acc = st.week.d ? Math.round(st.week.ok / st.week.d * 100) : 0;
  const weak = weakTopics(p, st);
  const d = hwDone(st, hw), c = courseDone(st);
  return [
    `${s.name} — тренажёр «${p.title}», последние 7 дней:`,
    `• занимался(ась) ${plural(st.week.days, 'день', 'дня', 'дней')} из 7, решено ${plural(st.week.d, 'задание', 'задания', 'заданий')};`,
    `• точность ${acc}%${trend(st)}, серия без пропусков — ${plural(st.streak, 'день', 'дня', 'дней')};`,
    `• освоено ${st.mastered} из ${st.total} карточек курса${hw || c.n ? ';' : '.'}`,
    ...(hw ? [`• задание репетитора «${hw.text}» до ${dueText(hw.due)}: сделано ${d} из ${hw.goal}${d >= hw.goal ? ' — выполнено' : ''}${c.n ? ';' : '.'}`] : []),
    ...(c.n ? [`• ДЗ курса: ${c.onTime} из ${c.n} в срок.`] : []),
    weak.length ? `Что подтягиваем на занятиях: ${weak.map(w => w.title.replace(/^\d+\.\s*/, '')).join(', ')}.` : 'Слабых тем сейчас нет — держим темп.',
    p.tutor ? `\n${p.tutor}` : '',
  ].join('\n').trim();
}

// Пример «Учеников»: три выдуманных ученика с активностью, слабыми темами и ошибками — чтобы
// до первых настоящих учеников было видно, что получит репетитор. Считается здесь же, в браузере,
// и никуда не отправляется (ни в облако студии, ни на сервер)
function demoStudents(p) {
  const topics = p.topics.filter(t => p.cards.some(c => c.t === t.id));
  const now = Date.now(), H = 3600e3, D = 864e5;
  const make = (sid, name, { at, days, accs, streak, tg, prev, errs }) => {
    const week = days.slice(7), d = week.reduce((a, b) => a + b, 0);
    const st = Object.fromEntries(topics.map((t, i) => {
      const n = p.cards.filter(c => c.t === t.id).length, acc = accs[i % accs.length];
      const s = Math.min(n, Math.max(3, Math.round(n * 0.6)));
      return [t.id, { acc, s, m: Math.round(s * acc / 125) }];
    }));
    const avg = topics.length ? topics.reduce((a, t) => a + st[t.id].acc, 0) / topics.length : 80;
    const ok = Math.round(d * avg / 100);
    // Ошибки — карточки самых слабых тем
    const weakest = [...topics].sort((a, b) => st[a.id].acc - st[b.id].acc).map(t => t.id);
    const errIds = weakest.flatMap(tid => p.cards.filter(c => c.t === tid).slice(0, errs).map(c => c.id)).slice(0, errs);
    const weeks = [...Array(6).fill(0).map((_, i) => ({ d: i < 3 ? 0 : prev.d - (5 - i) * 4, ok: 0 })), prev, { d, ok }]
      .map(w => ({ d: Math.max(0, w.d), ok: w.ok || Math.round(Math.max(0, w.d) * (avg - 6) / 100) }));
    return {
      sid, name, at, tg, parents: 0, demo: true,
      stats: { day: day(), days, today: { d: days[13], ok: Math.round(days[13] * avg / 100) }, week: { d, ok, days: week.filter(Boolean).length },
        weeks, streak, mastered: Object.values(st).reduce((a, x) => a + x.m, 0), total: p.cards.length, topics: st, errs: errIds },
    };
  };
  return [
    make('demo-anya', 'Аня', { at: now - 2 * H, days: [4, 6, 0, 8, 5, 7, 6, 5, 8, 6, 0, 9, 7, 11], accs: [92, 88, 72], streak: 3, tg: true, prev: { d: 30, ok: 23 }, errs: 2 }),
    make('demo-sonya', 'Соня', { at: now - D - 2 * H, days: [0, 3, 5, 0, 4, 6, 2, 4, 5, 3, 6, 0, 6, 0], accs: [78, 62, 90], streak: 1, tg: false, prev: { d: 20, ok: 14 }, errs: 3 }),
    make('demo-dima', 'Дима', { at: now - 4 * D - 3 * H, days: [5, 0, 7, 3, 0, 6, 4, 3, 6, 0, 0, 0, 0, 0], accs: [48, 64, 81], streak: 0, tg: false, prev: { d: 25, ok: 17 }, errs: 5 }),
  ];
}

// Задание тренажёра — одно на всех учеников. Задание и счётчики берём только из ответа /progress
function hwPanel(p, hw, students, demo) {
  if (demo) return `<section class="panel"><h2>Задание</h2>
    <p class="muted">После публикации сможете задать, сколько карточек решить к сроку: ученики увидят задание в тренажёре, а подключившие Telegram получат сообщение.</p></section>`;
  if (!hw) return `<section class="panel"><h2>Задание</h2>
    <p class="muted">Задайте, сколько карточек решить к сроку, — ученики увидят задание в тренажёре, а подключившие Telegram получат сообщение.</p>
    <button class="btn primary" id="hw-new">Задать задание</button></section>`;
  const topic = hw.topic ? hw.topicTitle || p.topics.find(t => t.id === hw.topic)?.title || hw.topic : null;
  const done = students.filter(s => hwDone(s.stats, hw) >= hw.goal).length;
  return `<section class="panel"><h2>Задание</h2>
    <p><b>${esc(hw.text)}</b></p>
    <p class="muted">${topic ? `Тема «${esc(topic)}»` : 'Весь тренажёр'} · ${plural(hw.goal, 'карточка', 'карточки', 'карточек')} · до ${dueText(hw.due)}${day() > dueDay(hw.due) ? ' · срок прошёл' : ''}</p>
    ${students.length ? `<p>Выполнили ${done} из ${students.length}</p>` : ''}
    <div class="row"><button class="btn" id="hw-new">Новое задание</button><button class="btn ghost danger" id="hw-del">Снять задание</button></div></section>`;
}

// Окно задания. Срок — дата по часам репетитора; сервер принимает до +90 дней по UTC
function hwDialog(p, hw, onDone) {
  const iso = d => new Date(d * 864e5).toISOString().slice(0, 10);
  // Темы без карточек ученику не решить, а id темы сервер принимает только вида [\w-]
  const topics = p.topics.filter(t => /^[\w-]{1,40}$/.test(t.id) && p.cards.some(c => c.t === t.id));
  const { box, close } = modal(`
    <h3>${hw ? 'Новое задание' : 'Задание ученикам'}</h3>
    <div class="field"><label for="hw-text">Что сделать (увидит ученик)</label><textarea id="hw-text" rows="3" maxlength="300" placeholder="Например: повторить правило и решить 20 карточек"></textarea></div>
    <div class="field"><label for="hw-topic">Тема</label><select id="hw-topic"><option value="">Весь тренажёр</option>${topics.map(t =>
      `<option value="${esc(t.id)}">${esc(t.title)} · ${p.cards.filter(c => c.t === t.id).length}</option>`).join('')}</select></div>
    <div class="grid2">
      <div class="field"><label for="hw-goal">Сколько карточек</label><input id="hw-goal" type="number" inputmode="numeric" min="1" max="200" value="20"></div>
      <div class="field"><label for="hw-due">Срок</label><input id="hw-due" type="date" min="${iso(day())}" max="${iso(Math.floor(Date.now() / 864e5) + 90)}" value="${iso(day() + 7)}"></div>
    </div>
    ${hw ? '<p class="muted">Новое задание заменит текущее — счётчики учеников начнутся с нуля.</p>' : ''}
    <div class="row"><button class="btn primary" id="hw-send">Отправить ученикам</button><button class="btn ghost" id="hw-cancel">Отмена</button></div>`);
  const $ = s => box.querySelector(s);
  $('#hw-cancel').onclick = () => { close(); };
  $('#hw-send').onclick = async e => {
    const goal = Number($('#hw-goal').value), due = $('#hw-due').value, topic = $('#hw-topic').value || null;
    if (!Number.isInteger(goal) || goal < 1 || goal > 200) return toast('Сколько карточек — от 1 до 200');
    if (!due) return toast('Укажите срок');
    const btn = e.currentTarget;
    btn.disabled = true;
    try {
      const r = await api(`/packs/${p.id}/hw`, { method: 'PUT', key: db.keys[p.id], body: {
        text: $('#hw-text').value.trim(), topic, topicTitle: topic ? topics.find(t => t.id === topic).title : null,
        goal, due, tutor: p.tutor, title: p.title } });
      close();
      // now — сообщение ушло сразу; later — у кого сейчас ночь или лимит рассылок: придёт вечерним напоминанием
      toast(r.repeat ? 'Это задание уже отправлено' : 'Задание отправлено'
        + (r.tg?.now ? ` · в Telegram — ${plural(r.tg.now, 'ученику', 'ученикам', 'ученикам')}` : '')
        + (r.tg?.later ? ` · ещё ${r.tg.later} — вечером` : ''));
      onDone();
    } catch (err) { toast(err.message); btn.disabled = false; }
  };
}

const DEMO_OFF = 'Это пример — опубликуйте тренажёр, и с настоящими учениками это заработает';

// Строка ученика. На телефоне таблица становится карточками (app.css): подписи из data-label
function studentRow(p, s, i, hw, { t, overdue, hasCourse }) {
  const st = s.stats;
  const acc = st.week?.d ? Math.round(st.week.ok / st.week.d * 100) : null;
  const todayDone = day(new Date(s.at)) === t ? st.today?.d || 0 : 0;
  const weak = weakTopics(p, st);
  const d = hwDone(st, hw);
  const late = Date.now() - s.at > 3 * 864e5;
  return `<tr>
    <td class="st-name" data-label="Ученик"><button class="link-btn" data-stu="${i}">${esc(s.name)}</button>${s.demo ? ' <span class="pill demo">пример</span>' : ''}${s.tg ? ' <span class="pill ok" title="Напоминания в Telegram включены">TG</span>' : ''}</td>
    <td class="st-seen ${late ? 'late' : ''}" data-label="Был(а)">${ago(s.at)}</td>
    <td class="st-today" data-label="Сегодня">${todayDone || '—'}</td>
    <td class="st-week" data-label="7 дней">${st.week?.d || 0} <span class="muted">· ${st.week?.days || 0} дн.</span>${activityStrip(st)}</td>
    ${hw ? `<td class="st-hw ${d >= hw.goal ? 'ok' : overdue ? 'late' : ''}" data-label="Задание">${d}/${hw.goal}</td>` : '<td class="st-hw st-none" data-label="Задание">—</td>'}
    ${hasCourse ? (cd => `<td class="st-course nowrap ${cd.n && cd.onTime === cd.n ? 'ok' : cd.onTime < cd.n ? 'late' : ''}" data-label="ДЗ курса">${cd.n ? `${cd.onTime}/${cd.n} в срок` : '—'}</td>`)(courseDone(st)) : ''}
    <td class="st-acc" data-label="Точность">${acc === null ? '—' : `<span class="${acc < 60 ? 'late' : ''}">${acc}%</span>`}</td>
    <td class="st-streak" data-label="Серия">${st.streak || 0}</td>
    <td class="st-mast" data-label="Освоено">${st.mastered}/${st.total}</td>
    <td class="st-weak" data-label="Слабые темы">${weak.map(w => `${esc(w.title)} <span class="muted">${w.acc}%</span>`).join('<br>') || '—'}</td>
    <td class="st-act nowrap"><button class="btn small" data-err="${i}">Ошибки</button> <button class="btn small" data-rep="${i}">Отчёт</button></td>
  </tr>`;
}

async function viewStudents(p, { demo = false } = {}) {
  const box = shell(p, 'students', '<p class="muted">Загружаю…</p>');
  // Неопубликованный пример — сразу демо-ученики: видно, что получит репетитор
  const isDemo = demo || (!p.published && !!p.sample);
  let students, hw = null;
  if (isDemo) students = demoStudents(p);
  else if (!p.published) {
    box.innerHTML = `<div class="panel empty">Опубликуйте тренажёр и отправьте ссылку ученикам — здесь появится их прогресс. <a href="#/p/${p.id}/publish">Опубликовать</a>
      ${p.cards.length ? '<p><button class="btn" id="demo">Как это будет выглядеть — пример</button></p>' : ''}</div>`;
    box.querySelector('#demo')?.addEventListener('click', () => { viewStudents(p, { demo: true }); });
    return;
  } else {
    try {
      ({ students, hw = null } = await api(`/packs/${p.id}/progress`, { key: db.keys[p.id] }));
    } catch (err) {
      if (!box.isConnected) return;
      box.innerHTML = `<div class="panel empty" role="alert"><p>${esc(err.message)}</p><button class="btn" id="st-retry">Повторить</button></div>`;
      box.querySelector('#st-retry').onclick = () => { viewStudents(p); };
      return;
    }
    if (!box.isConnected) return; // пока ждали ответ, репетитор ушёл на другую вкладку
  }
  const demoNote = isDemo ? `<section class="panel demo-note" role="note">
    <p><b>Пример — так будет выглядеть, когда ученики начнут заниматься.</b> Ученики ниже выдуманные: после публикации здесь появятся ваши. Нажмите «Отчёт» — это готовый текст для родителей.</p>
    <div class="row">${p.published ? '<button class="btn small" id="demo-off">Скрыть пример</button>'
      : `<a class="btn small primary" href="#/p/${p.id}/publish">Опубликовать и отправить ученикам</a><button class="btn small" id="demo-try">Глазами ученика</button>`}</div></section>` : '';
  if (!students.length) {
    // Задание можно задать заранее — ученики увидят его с первого открытия
    box.innerHTML = `${hwPanel(p, hw, students)}<div class="panel empty">Пока никто не занимался. Ссылка для учеников: <a href="${esc(studentLink(p.id))}" target="_blank">${esc(studentLink(p.id))}</a>
      <p><button class="btn" id="demo">Как это будет выглядеть — пример</button></p></div>`;
  } else {
    students.sort((a, b) => b.at - a.at);
    const t = day();
    const active = students.filter(s => Date.now() - s.at < 7 * 864e5).length;
    const overdue = hw && t > dueDay(hw.due);
    const hasCourse = p.course?.lessons?.some(l => l.hw); // колонка «ДЗ курса» — только если в курсе есть ДЗ
    box.innerHTML = `${demoNote}
    <div class="hero-stats wide-stats">
      <div><b>${students.length}</b><span>учеников</span></div>
      <div><b>${active}</b><span>занимались за неделю</span></div>
      <div><b>${students.reduce((n, s) => n + (s.stats.week?.d || 0), 0)}</b><span>карточек за неделю</span></div>
    </div>
    ${hwPanel(p, hw, students, isDemo)}
    <div class="table-wrap students-wrap"><table class="students">
      <thead><tr><th>Ученик</th><th>Был(а)</th><th>Сегодня</th><th>7 дней</th><th>Задание</th>${hasCourse ? '<th>ДЗ курса</th>' : ''}<th>Точность</th><th>Серия</th><th>Освоено</th><th>Слабые темы</th><th><span class="sr-only">Действия</span></th></tr></thead>
      <tbody>${students.map((s, i) => studentRow(p, s, i, hw, { t, overdue, hasCourse })).join('')}</tbody></table></div>
    <p class="muted">Ученик отправляет прогресс после каждого занятия. «Отчёт» — готовый текст для родителей, а «Отчёты родителю в Telegram» в карточке ученика присылают его родителю каждое воскресенье.</p>
    ${lessonPlan(p, students)}`;
  }
  box.onclick = e => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.id === 'demo') return viewStudents(p, { demo: true });
    if (b.id === 'demo-off') return viewStudents(p);
    if (b.id === 'demo-try') return preview(p, 0, { intro: true });
    // После записи или снятия задания панель и колонка рисуются заново по свежему /progress
    if (b.id === 'hw-new') return isDemo ? toast(DEMO_OFF) : hwDialog(p, hw, route);
    if (b.id === 'hw-del') {
      if (!confirm('Снять задание? Ученики перестанут его видеть.')) return;
      b.disabled = true;
      api(`/packs/${p.id}/hw`, { method: 'DELETE', key: db.keys[p.id] })
        .then(() => { toast('Задание снято'); route(); })
        .catch(err => { toast(err.message); b.disabled = false; });
      return;
    }
    if (b.id === 'copy-plan') {
      const txt = [...box.querySelectorAll('.lesson-plan h3, .lesson-plan li')].map(x => (x.tagName === 'H3' ? '\n' : '• ') + x.textContent.replace(/\s+/g, ' ').trim()).join('\n').trim();
      navigator.clipboard.writeText(`План урока — ${p.title}\n${txt}`).then(() => toast('Скопировано'), () => toast('Не получилось скопировать'));
      return;
    }
    if (b.dataset.stu !== undefined) return studentCard(p, students[+b.dataset.stu], hw, isDemo);
    const s = students[+(b.dataset.err ?? b.dataset.rep)];
    if (!s) return;
    if (b.dataset.rep !== undefined) {
      const txt = parentReport(p, s, hw);
      const { box: m } = modal(`<h3>Отчёт для родителей</h3>${isDemo ? '<p class="muted">Пример отчёта — у настоящих учеников цифры будут их.</p>' : ''}<textarea rows="9" id="rep" aria-label="Текст отчёта">${esc(txt)}</textarea>
        <div class="row"><button class="btn primary" id="copy">Скопировать</button></div>`);
      m.querySelector('#copy').onclick = () => navigator.clipboard.writeText(m.querySelector('#rep').value).then(() => toast('Скопировано'), () => toast('Не получилось скопировать'));
    } else {
      const byId = Object.fromEntries(p.cards.map(c => [c.id, c]));
      const errs = (s.stats.errs || []).map(id => byId[id]).filter(Boolean);
      modal(`<h3>Ошибки: ${esc(s.name)}</h3>
        ${errs.length ? `<p class="muted">Последние карточки, где ученик ошибся, — готовый план разбора на уроке.</p><ol class="err-list">${errs.map(c => `<li>${esc(c.q.slice(0, 220))}</li>`).join('')}</ol>` : '<p>Ошибок нет.</p>'}`);
    }
  };
}

// Подробно про одного ученика: активность, все темы по точности, последние ошибки
function studentCard(p, s, hw, demo = false) {
  const st = s.stats;
  const acc = st.week?.d ? Math.round(st.week.ok / st.week.d * 100) : null;
  const topics = Object.entries(st.topics || {})
    .map(([id, t]) => ({ title: p.topics.find(x => x.id === id)?.title || id, ...t }))
    .sort((a, b) => (a.acc ?? 101) - (b.acc ?? 101));
  const byId = Object.fromEntries(p.cards.map(c => [c.id, c]));
  const errs = (st.errs || []).map(id => byId[id]).filter(Boolean).slice(0, 8);
  const { box } = modal(`
    <h3>${esc(s.name)}${demo ? ' <span class="pill demo">пример</span>' : ''}</h3>
    <p class="muted">Был(а) ${ago(s.at)} · серия ${plural(st.streak || 0, 'день', 'дня', 'дней')}</p>
    <p class="muted">Напоминания в Telegram: ${s.tg ? 'включены' : 'не подключены — попросите ученика: тренажёр → Профиль → «Напоминания в Telegram»'}</p>
    <div class="hero-stats wide-stats">
      <div><b>${st.week?.d || 0}</b><span>карточек за 7 дней</span></div>
      <div><b>${acc === null ? '—' : acc + '%'}</b><span>точность</span></div>
      <div><b>${st.mastered}/${st.total}</b><span>освоено</span></div>
    </div>
    <h2>Активность за 2 недели</h2>
    <div class="strip-big">${activityStrip(st)}</div>
    ${weeksChart(st) ? `<h2>Точность по неделям</h2>${weeksChart(st)}` : ''}
    <h2>Темы — от слабых к сильным</h2>
    ${topics.length ? `<div class="stu-topics">${topics.map(t => `
      <div class="stu-topic"><span>${esc(t.title)}</span>
        <span class="bar"><i style="width:${t.acc ?? 0}%;background:${(t.acc ?? 100) < 60 ? 'var(--bad)' : (t.acc ?? 0) < 80 ? 'var(--mid)' : 'var(--ok)'}"></i></span>
        <b>${t.acc === null ? '—' : t.acc + '%'}</b><small>${t.m} из ${t.s} освоено</small></div>`).join('')}</div>` : '<p class="muted">Пока нет данных по темам.</p>'}
    ${errs.length ? `<h2>Последние ошибки</h2><ol class="err-list">${errs.map(c => `<li>${esc(c.q.replace(/\s+/g, ' ').slice(0, 200))}</li>`).join('')}</ol>` : ''}
    <div class="row"><button class="btn primary" id="stu-rep">Отчёт для родителей</button><button class="btn" id="stu-tg">${TG_ICON}Отчёты родителю в Telegram</button><button class="btn" id="stu-code">Код для родителя</button></div>
    <div id="stu-tg-state"></div>
    <div id="stu-code-out"></div>`);
  const out = box.querySelector('#stu-code-out'), state = box.querySelector('#stu-tg-state');
  box.querySelector('#stu-rep').onclick = () => navigator.clipboard.writeText(parentReport(p, s, hw)).then(() => toast('Отчёт скопирован'), () => toast('Не получилось скопировать'));
  // В примере ничего не уходит на сервер: код и ссылки для родителей — только у настоящих учеников
  if (demo) {
    box.querySelector('#stu-code').onclick = () => toast(DEMO_OFF);
    box.querySelector('#stu-tg').onclick = () => toast(DEMO_OFF);
    return;
  }
  box.querySelector('#stu-code').onclick = async () => {
    try {
      const { code } = await api(`/packs/${p.id}/parent-code`, { method: 'POST', body: { sid: s.sid }, key: db.keys[p.id] });
      out.innerHTML = `<div class="code-big">${esc(code)}</div><p class="muted">Родитель открывает ${esc(new URL(ROOT + 'login?role=parent', location.href).href)}, входит и вводит код. Действует сутки.</p>`;
    } catch (err) { out.innerHTML = `<p class="muted">${esc(err.message)}</p>`; }
  };

  // Отчёты родителю в Telegram: ссылка r_ на 7 дней. Отчёты идут, пока активен тариф репетитора;
  // «Отключить» гасит и подписки родителей, и все выданные ссылки
  const drawTg = () => {
    const paused = s.parents > 0 && signedIn() && !planOf('tutor').active;
    state.innerHTML = `${s.parents ? `<p>Подписано родителей: ${s.parents} <button class="btn small ghost danger" id="stu-tg-off">Отключить отчёты</button></p>` : ''}
      ${paused ? '<p class="muted">Отчёты родителям приостановлены — тариф закончился.</p> <button class="btn small primary" id="stu-pay">Продлить</button>' : ''}`;
    state.querySelector('#stu-pay')?.addEventListener('click', () => payDialog({ product: 'tutor' }));
    state.querySelector('#stu-tg-off')?.addEventListener('click', async e => {
      if (!confirm('Родители перестанут получать отчёты об этом ученике, старые ссылки тоже перестанут работать.')) return;
      const btn = e.currentTarget;
      btn.disabled = true;
      try {
        await api(`/packs/${p.id}/notify/parent-off`, { method: 'POST', body: { sid: s.sid }, key: db.keys[p.id] });
        s.parents = 0;
        out.innerHTML = ''; // показанная ссылка тоже больше не действует
        drawTg();
        toast('Отчёты родителям отключены');
      } catch (err) { toast(err.message); btn.disabled = false; }
    });
  };
  drawTg();
  box.querySelector('#stu-tg').onclick = async e => {
    const btn = e.currentTarget;
    btn.disabled = true;
    try {
      const r = await api(`/packs/${p.id}/notify/parent`, { method: 'POST', body: { sid: s.sid }, key: db.keys[p.id] });
      s.parents = r.parents;
      drawTg();
      const name = String(s.name || '').trim().split(/\s+/)[0];
      const share = `https://t.me/share/url?url=${encodeURIComponent(r.link)}&text=${encodeURIComponent(`Отчёты о занятиях в Telegram: ${name}`)}`;
      out.innerHTML = `<p>Отправьте ссылку родителю. Он откроет бота, нажмёт «Запустить» — и сразу получит отчёт, а дальше каждое воскресенье. Ссылка действует 7 дней.</p>
        <div class="row"><input readonly id="stu-tg-link" value="${esc(r.link)}" aria-label="Ссылка для родителя"><button class="btn" id="stu-tg-copy">Скопировать</button></div>
        <p><a class="btn" target="_blank" rel="noopener" href="${esc(share)}">${TG_ICON}Отправить в Telegram</a></p>`;
      out.querySelector('#stu-tg-copy').onclick = () => navigator.clipboard.writeText(r.link).then(() => toast('Скопировано'), () => toast('Не получилось скопировать'));
    } catch (err) {
      // Тариф репетитора неактивен — ссылки нет, сразу предлагаем продлить
      if (err.status === 402) { toast(err.message); payDialog({ product: 'tutor' }); }
      else out.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
    }
    btn.disabled = false;
  };
}

// ---------- курс ----------

// Курс хранится в самом наборе (p.course) и уходит ученикам обычной публикацией.
// Урок: видео по ссылке, конспект (простой текст), тема тренажёра, дата открытия, ДЗ со сроком
const iso = d => new Date(d * 864e5).toISOString().slice(0, 10);
const course = p => (p.course ||= { lessons: [], lives: [] });

function viewCourse(p) {
  const c = p.course || { lessons: [], lives: [] };
  const tTitle = id => p.topics.find(t => t.id === id)?.title;
  const box = shell(p, 'course', `
    <section class="panel">
      <h2>Уроки</h2>
      <p class="muted">Урок — это видео (Kinescope, VK Видео, Rutube), конспект и тема тренажёра. ДЗ «решить N карточек с точностью от X% к сроку» засчитывается само. Ученики увидят курс после публикации.</p>
      ${c.lessons.map((l, i) => `<div class="course-row" data-i="${i}">
        <span class="les-n">${i + 1}</span>
        <span class="course-row-main"><b>${esc(l.title)}</b>
          <small>${l.open ? `откроется ${dueText(l.open)}` : 'открыт сразу'}${l.topic ? ` · ${esc(tTitle(l.topic) || 'тема удалена')}` : ''}${l.video ? ' · видео' : ''}</small>
          <small>${l.hw ? `ДЗ: ${plural(l.hw.goal, 'карточка', 'карточки', 'карточек')} от ${l.hw.acc}% до ${dueText(l.hw.due)}` : 'без ДЗ'}</small></span>
        <span class="card-row-actions">
          <button class="btn small" data-a="up" aria-label="Выше" ${i ? '' : 'disabled'}>↑</button>
          <button class="btn small" data-a="down" aria-label="Ниже" ${i < c.lessons.length - 1 ? '' : 'disabled'}>↓</button>
          <button class="btn small" data-a="edit">Изменить</button>
          <button class="btn small danger" data-a="del" aria-label="Удалить">✕</button></span>
      </div>`).join('') || '<p class="muted">Уроков пока нет.</p>'}
      <button class="btn primary" id="les-add">+ Урок</button>
    </section>
    <section class="panel">
      <h2>Эфиры</h2>
      <p class="muted">Время и ссылка на Телемост или Kinescope. Ученик добавит эфир в календарь с напоминанием за 15 минут. После эфира вставьте ссылку на запись.</p>
      ${c.lives.map((v, i) => `<div class="course-row" data-v="${i}">
        <span class="course-row-main"><b>${esc(v.title)}</b><small>${whenText(v.at)}${v.rec ? ' · есть запись' : ''}</small></span>
        <span class="card-row-actions"><button class="btn small" data-a="edit">Изменить</button><button class="btn small danger" data-a="del" aria-label="Удалить">✕</button></span>
      </div>`).join('') || '<p class="muted">Эфиров пока нет.</p>'}
      <button class="btn" id="live-add">+ Эфир</button>
    </section>
    ${isPublished(p) || !c.lessons.length ? '' : `<p class="muted">Курс изменился — <a href="#/p/${p.id}/publish">обновите у учеников</a>.</p>`}`);
  box.querySelector('#les-add').onclick = () => lessonDialog(p, null);
  box.querySelector('#live-add').onclick = () => liveDialog(p, null);
  box.onclick = e => {
    const b = e.target.closest('[data-a]'), row = b?.closest('.course-row');
    if (!row) return;
    const a = b.dataset.a;
    if (row.dataset.v !== undefined) {
      const i = +row.dataset.v;
      if (a === 'edit') liveDialog(p, i);
      if (a === 'del' && confirm('Удалить эфир?')) { c.lives.splice(i, 1); touch(p); route(); }
      return;
    }
    const i = +row.dataset.i, j = a === 'up' ? i - 1 : a === 'down' ? i + 1 : -1;
    if (a === 'edit') lessonDialog(p, i);
    if (a === 'del' && confirm(`Удалить урок «${c.lessons[i].title}»?`)) { c.lessons.splice(i, 1); touch(p); route(); }
    if (j >= 0 && j < c.lessons.length) { [c.lessons[i], c.lessons[j]] = [c.lessons[j], c.lessons[i]]; touch(p); route(); }
  };
}

// Окно урока. Поля — не внутри <label> (на iOS в таких не печатается)
function lessonDialog(p, index) {
  const l = index === null ? { title: '', video: '', notes: '', topic: null, open: null, hw: null } : course(p).lessons[index];
  const topics = p.topics.filter(t => p.cards.some(c => c.t === t.id));
  const { box, close } = modal(`
    <h3>${index === null ? 'Новый урок' : 'Урок'}</h3>
    <div class="field"><label for="les-title">Название</label><input id="les-title" maxlength="120" value="${esc(l.title)}" placeholder="Например: Причастный оборот"></div>
    <div class="field"><label for="les-video">Ссылка на видео</label><input id="les-video" type="url" inputmode="url" value="${esc(l.video)}" placeholder="https://kinescope.io/…"></div>
    <p class="muted small-note field-note les-video-hint"></p>
    <div class="field"><label for="les-notes">Конспект (увидит ученик под видео)</label><textarea id="les-notes" rows="6" maxlength="20000" placeholder="Правило, примеры, формулы в ⟦ ⟧">${esc(l.notes)}</textarea></div>
    <div class="grid2">
      <div class="field"><label for="les-topic">Тема тренажёра</label><select id="les-topic"><option value="">Без тренажёра</option>${topics.map(t =>
        `<option value="${esc(t.id)}" ${t.id === l.topic ? 'selected' : ''}>${esc(t.title)} · ${p.cards.filter(c => c.t === t.id).length}</option>`).join('')}</select></div>
      <div class="field"><label for="les-open">Откроется</label><input id="les-open" type="date" value="${esc(l.open || '')}"></div>
    </div>
    <h3>ДЗ</h3>
    <p class="muted small-note field-note">Оставьте «сколько карточек» пустым — урок будет без ДЗ.</p>
    <div class="grid3">
      <div class="field"><label for="les-goal">Сколько карточек</label><input id="les-goal" type="number" inputmode="numeric" min="1" max="200" value="${l.hw?.goal ?? ''}" placeholder="20"></div>
      <div class="field"><label for="les-acc">Точность от, %</label><input id="les-acc" type="number" inputmode="numeric" min="0" max="100" value="${l.hw?.acc ?? 70}"></div>
      <div class="field"><label for="les-due">Срок</label><input id="les-due" type="date" value="${esc(l.hw?.due || iso(day() + 7))}"></div>
    </div>
    <div class="row"><button class="btn primary" id="les-save">Сохранить</button><button class="btn ghost" id="les-cancel">Отмена</button></div>`);
  const $ = s => box.querySelector(s);
  // Подсказка: встроится ли видео в урок или будет кнопкой
  const hint = () => {
    const v = $('#les-video').value.trim(), html = v ? videoEmbed(v) : '';
    $('.les-video-hint').textContent = !v ? 'Kinescope, VK Видео и Rutube встроятся в урок, другие сайты — кнопкой «Открыть видео».'
      : html.includes('<iframe') ? 'Видео встроится в урок.' : html ? 'Этот сайт не встраивается — у ученика будет кнопка «Открыть видео».' : 'Нужна ссылка, которая начинается с https://';
  };
  hint();
  $('#les-video').oninput = hint;
  $('#les-cancel').onclick = () => { close(); };
  $('#les-save').onclick = () => {
    const title = $('#les-title').value.trim(), video = $('#les-video').value.trim(), goalRaw = $('#les-goal').value.trim();
    if (!title) return toast('Назовите урок');
    if (video && !videoEmbed(video)) return toast('Ссылка на видео должна начинаться с https://');
    let hw = null;
    if (goalRaw) {
      const goal = Number(goalRaw), acc = Number($('#les-acc').value), due = $('#les-due').value;
      if (!Number.isInteger(goal) || goal < 1 || goal > 200) return toast('Сколько карточек — от 1 до 200');
      if (!Number.isInteger(acc) || acc < 0 || acc > 100) return toast('Точность — от 0 до 100%');
      if (!due) return toast('Укажите срок ДЗ');
      hw = { goal, acc, due };
    }
    const data = { title, video, notes: $('#les-notes').value.trim(), topic: $('#les-topic').value || null, open: $('#les-open').value || null, hw };
    if (index === null) course(p).lessons.push({ id: 'l' + uid(8), ...data });
    else Object.assign(course(p).lessons[index], data);
    touch(p);
    close();
    route();
  };
}

// Окно эфира: время вводится по часам репетитора, хранится в UTC (ISO) — у ученика покажется по его часам
function liveDialog(p, index) {
  const v = index === null ? { title: '', at: '', url: '', rec: '' } : course(p).lives[index];
  const pad = n => String(n).padStart(2, '0');
  const local = at => { const d = new Date(at); return at && !isNaN(d) ? `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}` : ''; };
  const { box, close } = modal(`
    <h3>${index === null ? 'Новый эфир' : 'Эфир'}</h3>
    <div class="field"><label for="live-title">Название</label><input id="live-title" maxlength="120" value="${esc(v.title)}" placeholder="Разбор ДЗ и вопросы"></div>
    <div class="field"><label for="live-at">Дата и время</label><input id="live-at" type="datetime-local" value="${local(v.at)}"></div>
    <div class="field"><label for="live-url">Ссылка на эфир (Телемост, Kinescope)</label><input id="live-url" type="url" inputmode="url" value="${esc(v.url)}" placeholder="https://telemost.yandex.ru/…"></div>
    <div class="field"><label for="live-rec">Ссылка на запись (после эфира)</label><input id="live-rec" type="url" inputmode="url" value="${esc(v.rec)}" placeholder="https://kinescope.io/…"></div>
    <div class="row"><button class="btn primary" id="live-save">Сохранить</button><button class="btn ghost" id="live-cancel">Отмена</button></div>`);
  const $ = s => box.querySelector(s);
  $('#live-cancel').onclick = () => { close(); };
  $('#live-save').onclick = () => {
    const title = $('#live-title').value.trim(), at = new Date($('#live-at').value), url = $('#live-url').value.trim(), rec = $('#live-rec').value.trim();
    if (!title) return toast('Назовите эфир');
    if (!$('#live-at').value || isNaN(at)) return toast('Укажите дату и время');
    if ([url, rec].some(u => u && !/^https:\/\/\S+$/i.test(u))) return toast('Ссылки должны начинаться с https://');
    const data = { title, at: at.toISOString(), url, rec };
    if (index === null) course(p).lives.push({ id: 'v' + uid(8), ...data });
    else Object.assign(course(p).lives[index], data);
    touch(p);
    close();
    route();
  };
}

// ---------- настройки и публикация ----------

function viewSettings(p) {
  const box = shell(p, 'settings', `
    <section class="panel">
      <div class="grid2">
        <div class="field"><label for="title">Название тренажёра</label><input id="title" value="${esc(p.title)}"></div>
        <div class="field"><label for="tutor">Репетитор (видят ученики)</label><input id="tutor" value="${esc(p.tutor)}" placeholder="Анна Сергеевна · ЕГЭ по русскому"></div>
        <div class="field"><label for="subject">Предмет</label><input id="subject" value="${esc(p.subject)}" placeholder="Русский язык"></div>
        <div class="field"><label for="daily">Новых карточек в день</label><input id="daily" type="number" inputmode="numeric" min="1" max="50" value="${p.daily || 10}"></div>
      </div>
      <div class="field"><span>Цвет</span><div class="row">${COLORS.map(c => `<button class="swatch ${c === p.color ? 'on' : ''}" data-c="${c}" style="background:${c}" aria-label="Цвет ${c}" aria-pressed="${c === p.color}"></button>`).join('')}</div></div>
      <button class="btn primary" id="save">Сохранить</button>
    </section>
    <section class="panel">
      <h2>Темы</h2>
      ${p.topics.length ? p.topics.map((t, i) => `<div class="row topic-edit"><input data-i="${i}" value="${esc(t.title)}" aria-label="Название темы"><span class="muted">${p.cards.filter(c => c.t === t.id).length}</span><button class="btn small danger" data-del="${i}">Удалить</button></div>`).join('') : '<p class="muted">Темы появятся вместе с карточками.</p>'}
    </section>
    ${DEBUG ? `<section class="panel">
      <h2>Сервер</h2>
      <div class="field"><label for="api">Адрес Cloudflare Worker (один на все тренажёры)</label><input id="api" value="${esc(store.get('zd-api', ''))}" placeholder="https://zadachnik.…workers.dev"></div>
      <button class="btn" id="save-api">Сохранить адрес</button>
    </section>` : ''}
    <section class="panel">
      <h2>Файл</h2>
      <p class="muted">Резервная копия набора — на случай, если очистите браузер.</p>
      <button class="btn" id="export">Скачать набор</button>
      <button class="btn danger" id="drop">Удалить тренажёр</button>
    </section>`);
  let color = p.color;
  box.querySelectorAll('.swatch').forEach(s => {
    s.onclick = () => {
      color = s.dataset.c;
      box.querySelectorAll('.swatch').forEach(x => { x.classList.toggle('on', x === s); x.setAttribute('aria-pressed', x === s); });
    };
  });
  box.querySelector('#save').onclick = () => {
    p.title = box.querySelector('#title').value.trim() || 'Тренажёр';
    p.tutor = box.querySelector('#tutor').value.trim();
    p.subject = box.querySelector('#subject').value.trim();
    p.daily = Math.max(1, Math.min(50, +box.querySelector('#daily').value || 10));
    p.color = color;
    box.querySelectorAll('.topic-edit input').forEach(i => { p.topics[+i.dataset.i].title = i.value.trim() || p.topics[+i.dataset.i].title; });
    touch(p);
    toast('Сохранено');
    route();
  };
  box.querySelectorAll('[data-del]').forEach(b => {
    b.onclick = () => {
      const t = p.topics[+b.dataset.del];
      const n = p.cards.filter(c => c.t === t.id).length;
      if (!confirm(n ? `Удалить тему «${t.title}» и ${plural(n, 'карточку', 'карточки', 'карточек')} в ней?` : `Удалить тему «${t.title}»?`)) return;
      p.topics = p.topics.filter(x => x !== t);
      p.cards = p.cards.filter(c => c.t !== t.id);
      p.theory = p.theory.filter(l => l.topic !== t.id);
      p.course?.lessons.forEach(l => { if (l.topic === t.id) l.topic = null; }); // урок остаётся, без тренажёра
      touch(p);
      route();
    };
  });
  box.querySelector('#save-api')?.addEventListener('click', () => { store.set('zd-api', box.querySelector('#api').value.trim()); toast('Адрес сохранён'); route(); });
  box.querySelector('#export').onclick = () => {
    const { edited, published, sample, ...data } = p;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(data)], { type: 'application/json' }));
    a.download = `${p.title.replace(/[^\p{L}\p{N}]+/gu, '-')}.json`;
    a.click();
  };
  box.querySelector('#drop').onclick = () => {
    if (!confirm('Удалить тренажёр из студии? Ученики с опубликованной ссылкой продолжат заниматься.')) return;
    if (db.packs[p.id]) {
      delete db.packs[p.id];
      db.deleted[p.id] = Date.now();
      persist();
    }
    if (draft === p) draft = null;
    location.hash = '#/';
  };
}

// QR-код ссылки (vendor/qrcode.js, MIT): чёрные модули на белом — читается любой камерой
function qrSvg(link, cell) {
  const qr = window.qrcode(0, 'M');
  qr.addData(link);
  qr.make();
  return qr.createSvgTag({ cellSize: cell, margin: 2, scalable: true });
}
// Библиотека QR подгружается, когда нужна (studio/index.html: window.loadQR)
async function drawQr(slot, link, title) {
  try { await window.loadQR?.(); } catch { /* без QR ссылка всё равно работает */ }
  if (!window.qrcode || !slot.isConnected) return;
  slot.innerHTML = `<div class="qr">${qrSvg(link, 5)}</div>
    <div><b>QR-код для урока</b><p class="muted">Покажите на экране — ученики наведут камеру телефона и сразу откроют тренажёр.</p>
    <button class="btn small" id="qr-big">На весь экран</button></div>`;
  slot.hidden = false;
  slot.querySelector('#qr-big').onclick = () =>
    modal(`<div class="qr-big">${qrSvg(link, 12)}<p><b>${esc(title)}</b><br><span class="muted">Наведите камеру телефона</span></p></div>`);
}

let justPublished = null; // id тренажёра, который только что опубликовали впервые

function viewPublish(p) {
  const link = studentLink(p.id);
  const first = justPublished === p.id;
  justPublished = null;
  const share = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(`Тренажёр «${p.title}»: занимайся по 10 минут в день`)}`;
  const box = shell(p, 'publish', `
    ${p.published ? `
    <section class="panel share-card">
      ${first ? '<p class="share-done">Опубликовано!</p>' : ''}
      <h2>Отправьте ссылку ученикам</h2>
      <p>Ученик откроет ссылку, напишет имя — и сразу начнёт заниматься. Его прогресс появится во вкладке «Ученики».</p>
      <label class="share-label" for="link">Ссылка для учеников</label>
      <div class="row share-link"><input readonly value="${esc(link)}" id="link"><button class="btn primary" id="copy">Скопировать</button></div>
      <div class="row share-actions">
        <a class="btn tg" id="share-tg" target="_blank" rel="noopener" href="${esc(share)}">${TG_ICON}Отправить в Telegram</a>
        <a class="btn ghost" id="as-student" target="_blank" rel="noopener" href="${esc(previewLink(p.id))}">Открыть как ученик</a>
      </div>
      <div class="qr-wrap" id="qr-slot" hidden></div>
      <p class="muted small-note">Или код <b>${esc(p.id)}</b> — ученик вводит его на главной. «Открыть как ученик» — просмотр: вы не попадёте в список учеников.</p>
    </section>` : ''}
    <section class="panel">
      ${p.published ? `<p>${isPublished(p) ? 'Ученики видят актуальную версию.' : '<b>Есть изменения, которых ученики пока не видят.</b>'}</p>`
        : '<h2>Опубликуйте тренажёр</h2><p>После публикации появится ссылка для учеников — отправите её в Telegram или покажете QR-код на уроке.</p>'}
      <button class="btn ${p.published && isPublished(p) ? '' : 'primary'}" id="pub" ${apiBase() ? '' : 'disabled'}>${p.published ? 'Обновить у учеников' : 'Опубликовать'}</button>
      ${apiBase() ? '' : `<p class="muted">Сервер не подключён — опубликовать пока нельзя.${DEBUG ? ' Адрес — во вкладке «Настройки».' : ''}</p>`}
    </section>
    <section class="panel">
      <h2>Проверка перед отправкой</h2>
      <ul class="checklist">
        <li class="${p.tutor ? 'ok' : ''}">Указано имя репетитора — ученик должен понять, от кого тренажёр</li>
        <li class="${p.cards.length >= 20 ? 'ok' : ''}">Хотя бы 20 карточек (сейчас ${p.cards.length}) — чтобы хватило на пару занятий</li>
        <li class="${p.topics.length >= 2 ? 'ok' : ''}">Больше одной темы — ученику проще ориентироваться</li>
      </ul>
    </section>`);
  box.querySelector('#copy')?.addEventListener('click', () => {
    navigator.clipboard.writeText(link).then(() => toast('Ссылка скопирована — отправьте её ученикам'), () => {
      box.querySelector('#link').select();
      toast('Выделил ссылку — скопируйте её');
    });
  });
  const slot = box.querySelector('#qr-slot');
  if (slot) drawQr(slot, link, p.title);
  box.querySelector('#pub').onclick = e => { publish(p, e.currentTarget); };
}

// Опубликовать после входа: вход мог увести со страницы (Яндекс, VK, Google, Telegram в этой вкладке)
const PUB_AFTER = 'zd-publish-after';

async function publish(p, btn) {
  if (!p.cards.length) return toast('Добавьте карточки');
  // Новый тренажёр публикуется из аккаунта — так ключи и ученики не потеряются.
  // После входа публикация продолжается сама, второй раз нажимать не нужно
  if (!p.published && !signedIn()) {
    tabStore.set(PUB_AFTER, JSON.stringify({ id: p.id, at: Date.now() }));
    return login({
      why: 'Чтобы опубликовать тренажёр, войдите: ключи и ученики сохранятся в аккаунте. Первые 14 дней — всё без ограничений.',
      then: publishAfterLogin,
      onCancel: () => tabStore.set(PUB_AFTER, null),
    });
  }
  if (btn) btn.disabled = true;
  try {
    const { edited, published, sample, ...data } = p;
    // Пустые темы (например, созданные и брошенные в редакторе) ученику не нужны
    // Темы уроков курса тоже нужны: по ним считается ДЗ
    data.topics = p.topics.filter(t => p.cards.some(c => c.t === t.id) || p.theory.some(l => l.topic === t.id) || p.course?.lessons?.some(l => l.topic === t.id));
    keep(p);
    await api(`/packs/${p.id}`, { method: 'PUT', body: data, key: db.keys[p.id] });
    if (!p.published) justPublished = p.id;
    p.published = Date.now();
    p.edited = Math.min(p.edited, p.published);
    keep(p);
    persist();
    tabStore.set(PUB_AFTER, null);
    toast('Опубликовано');
    if (location.hash === `#/p/${p.id}/publish`) { route(); scrollTo(0, 0); } else location.hash = `#/p/${p.id}/publish`;
  } catch (err) {
    toast(err.message);
    if (btn?.isConnected) btn.disabled = false;
    if (err.status === 402) payDialog({ product: 'tutor' });
  }
}

async function publishAfterLogin() {
  let want = null;
  try { want = JSON.parse(tabStore.get(PUB_AFTER) || 'null'); } catch { /* испорчено — забываем */ }
  tabStore.set(PUB_AFTER, null);
  if (!want || Date.now() - want.at > 30 * 60e3 || !signedIn()) return;
  const p = db.packs[want.id];
  if (!p) return;
  if (location.hash !== `#/p/${p.id}/publish`) { history.replaceState(history.state, '', `#/p/${p.id}/publish`); lastHash = location.hash; route(); }
  await publish(p, document.getElementById('pub'));
}

// ---------- навигация ----------

const VIEWS = { cards: viewCards, add: viewAdd, course: viewCourse, students: viewStudents, settings: viewSettings, publish: viewPublish };

function route() {
  hideNotice('cloud');
  const [, kind, id, tab, sub] = location.hash.split('/');
  if (kind === 'new') {
    const p = newPack();
    history.replaceState(history.state, '', `#/p/${p.id}/add`);
    lastHash = location.hash;
    return route();
  }
  document.documentElement.style.removeProperty('--accent');
  if (kind === 'sample') { shown = { pack: null, tab: '' }; return viewSampleStart(id); }
  let p = kind === 'p' && (db.packs[id] || (draft?.id === id ? draft : null));
  // Черновик, в который ещё ничего не добавили, пережил перезагрузку только адресом — начинаем заново
  if (kind === 'p' && !p && tab === 'add' && cloudReady && !cloudFailed && /^[a-z0-9]{6,12}$/.test(id || '') && !db.deleted[id]) p = newPack(id);
  if (kind === 'p' && !p) {
    shown = { pack: null, tab: '' };
    return cloudReady ? viewMissing() : viewWaiting();
  }
  if (!p) { shown = { pack: null, tab: '' }; return viewList(); }
  const t = VIEWS[tab] ? tab : 'cards';
  shown = { pack: p, tab: t };
  document.documentElement.style.setProperty('--accent', p.color);
  VIEWS[t](p, sub);
}

// Новый экран — с начала страницы (кроме перерисовки того же адреса)
let lastHash = location.hash;
window.addEventListener('hashchange', () => {
  if (location.hash !== lastHash) { lastHash = location.hash; scrollTo(0, 0); }
  route();
});
// Правки из соседней вкладки студии: сливаем, а экран трогаем только если он устарел
window.addEventListener('storage', e => {
  if (e.key === 'zd-session' && !signedIn()) { cloud = 'off'; if (!busy()) route(); return; }
  if (e.key !== 'zd-studio') return;
  if (e.newValue === null) { db = { packs: {}, keys: {}, deleted: {} }; route(); return; } // вышли в другой вкладке
  const before = studioSig(db);
  db = mergeStudio(db, { packs: {}, keys: {}, deleted: {}, ...store.get('zd-studio', {}) });
  if (studioSig(db) !== before) dataChanged();
});

route();
init();

async function init() {
  const h0 = location.hash;
  const done = await finishRedirectLogin();
  if (done) { await addRole('tutor'); setCloud('saving'); }
  await finishPayment();
  // Возврат со входа или оплаты вернул прежний адрес (#/p/…) — показываем его
  if (location.hash !== h0) { lastHash = location.hash; route(); }
  if (!signedIn()) {
    await syncCloud(); // гостю облако не нужно: отмечаем, что ждать нечего
    return;
  }
  // Аккаунт (тариф, имя) и облачная студия — параллельно. /me уже спрашивали в этой вкладке — не ждём его
  const before = JSON.stringify(account());
  await Promise.all([syncCloud(), accountFresh() && !done ? null : refreshAccount()]);
  if (JSON.stringify(account()) !== before && !shown.pack && !busy()) route();
  // Публикация после входа — только если вход завершился именно сейчас (возврат от Яндекса/VK/Google,
  // Telegram в этой вкладке). Метка от брошенного входа не должна публиковать потом, при другом входе
  if (tabStore.get(PUB_AFTER)) { if (done) await publishAfterLogin(); else tabStore.set(PUB_AFTER, null); }
}
