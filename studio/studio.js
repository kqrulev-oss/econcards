// Студия репетитора: собрать набор из своих материалов (через ИИ) или из
// библиотеки, опубликовать ссылку для учеников и смотреть их прогресс.
import { signedIn, account, loginDialog, logout, refreshAccount, addRole, finishRedirectLogin, finishPayment, payDialog, planOf, daysLeft, dateRu, TG_ICON, openLink } from '../account.js';
import { store, api, apiBase, ai, loadPack, loadLibrary, renderCard, esc, text, day, uid, plural, el, toast, modal, dueDay, dueText, whenText, videoEmbed, KIND_NAMES } from '../lib.js';

const $app = document.getElementById('app');
const ROOT = '../';
// Цвета тренажёра: все читаются с белым текстом и не спорят с жёлтыми кнопками
const COLORS = ['#5B3DF5', '#0E7C86', '#2F6BFF', '#1F8A4C', '#C2185B', '#D8452B', '#8A4FFF', '#1B1440'];

// Черновики наборов и ключи публикации живут в браузере репетитора, а после
// входа в аккаунт — ещё и на сервере (не теряются при очистке браузера)
let db = { packs: {}, keys: {}, deleted: {}, ...store.get('zd-studio', {}) };
let cloud = signedIn() ? 'saved' : 'off'; // off | saving | saved | error
let cloudTimer;
const persist = () => {
  store.set('zd-studio', db);
  if (!signedIn()) return;
  setCloud('saving');
  clearTimeout(cloudTimer);
  cloudTimer = setTimeout(pushCloud, 2000);
};

async function pushCloud() {
  try {
    await api('/me/studio', { method: 'PUT', body: { packs: db.packs, keys: db.keys, deleted: db.deleted } });
    setCloud('saved');
  } catch { setCloud('error'); }
}

function setCloud(state) {
  cloud = state;
  const b = document.querySelector('.cloud');
  if (b) b.outerHTML = cloudBadge();
}
const cloudBadge = () => signedIn()
  ? `<span class="badge cloud ${cloud}">${{ saving: 'сохраняю…', saved: 'в облаке', error: 'не сохранено', off: '' }[cloud]}</span>` : '';

// Две копии студии (эта и облачная) → одна: у набора побеждает свежая правка,
// удалённый набор не возвращается, ключи объединяются
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

async function syncCloud() {
  if (!signedIn()) return;
  try {
    const remote = await api('/me/studio');
    db = mergeStudio(db, remote);
    store.set('zd-studio', db);
    await pushCloud();
    route();
  } catch (err) {
    if (/войти/i.test(err.message)) { await refreshAccount(); route(); } else setCloud('error');
  }
}

function accountBar() {
  if (!signedIn()) return `<a class="btn small primary" href="${ROOT}login.html?role=tutor&next=studio/">Войти</a>`;
  const a = account();
  return `<a class="acct-name" href="${ROOT}cabinet/#tutor" title="Личный кабинет">${esc(a?.name || a?.email || 'Аккаунт')}</a>${cloudBadge()}<button class="btn small" id="logout">Выйти</button>`;
}

// Тариф репетитора: пробный / оплачен / бесплатный с лимитами
function tariffPanel() {
  if (!signedIn()) return '';
  const st = planOf('tutor');
  if (st.paidUntil > Date.now()) return `<section class="panel plan ok">Тариф оплачен до <b>${dateRu(st.paidUntil)}</b>. <button class="link-btn" id="pay">Продлить</button></section>`;
  if (st.trialEnd > Date.now()) return `<section class="panel plan trial"><b>Пробный период: осталось ${plural(daysLeft(st.trialEnd), 'день', 'дня', 'дней')}</b> — всё без ограничений. <button class="link-btn" id="pay">Тарифы</button></section>`;
  return `<section class="panel plan free"><b>Бесплатный тариф:</b> 1 тренажёр и до 3 учеников в нём. Без ограничений — по подписке. <button class="btn small primary" id="pay">Оплатить</button></section>`;
}

function bindAccount(root) {
  root.querySelector('#pay')?.addEventListener('click', () => payDialog({ product: 'tutor' }));
  root.querySelector('#login')?.addEventListener('click', () => loginDialog({
    role: 'tutor',
    why: 'Тренажёры, ключи и ученики сохранятся в аккаунте — не пропадут при очистке браузера и откроются с любого устройства.',
    onDone: async () => { await addRole('tutor'); setCloud('saving'); await syncCloud(); },
  }));
  root.querySelector('#logout')?.addEventListener('click', async () => {
    if (!confirm('Выйти из аккаунта? Тренажёры останутся в этом браузере и в облаке.')) return;
    await logout();
    cloud = 'off';
    route();
  });
}
const touch = p => { p.edited = Date.now(); persist(); };

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

const studentLink = id => new URL(`${ROOT}?t=${id}`, location.href).href;
const isPublished = p => p.published && p.published >= p.edited;

function newPack() {
  const id = uid(8);
  db.packs[id] = {
    id, title: 'Новый тренажёр', tutor: '', subject: '', color: COLORS[0], daily: 10,
    topics: [], theory: [], cards: [], edited: Date.now(), published: 0,
  };
  db.keys[id] = uid(24);
  persist();
  return id;
}

// ---------- общий каркас ----------

function shell(p, tab, body) {
  const tabs = [['cards', `Карточки · ${p.cards.length}`], ['add', 'Добавить'], ['course', 'Курс'], ['students', 'Ученики'], ['settings', 'Настройки'], ['publish', isPublished(p) ? 'Ссылка' : 'Опубликовать']];
  $app.innerHTML = `
    <header class="top">
      <a class="back" href="#/">←</a>
      <div><div class="brand-title">${esc(p.title)}</div><div class="brand-by">${esc(p.tutor || 'Без имени репетитора')}${p.published && !isPublished(p) ? ' · есть неопубликованные правки' : ''}</div></div>
      <a class="btn small" href="${ROOT}?preview" id="try">Попробовать</a>
    </header>
    <nav class="tabs">${tabs.map(([id, t]) => `<a href="#/p/${p.id}/${id}" class="${tab === id ? 'on' : ''}">${t}</a>`).join('')}</nav>
    <div id="tab"></div>`;
  $app.querySelector('#try').onclick = e => { e.preventDefault(); preview(p); };
  const box = $app.querySelector('#tab');
  box.innerHTML = body;
  return box;
}

// Просмотр набора глазами ученика: карточки по очереди без записи прогресса
function preview(p, start = 0) {
  if (!p.cards.length) return toast('Сначала добавьте карточки');
  let i = start;
  const { box } = modal('<div class="pv"></div>');
  const pv = box.querySelector('.pv');
  const draw = () => {
    const c = p.cards[i];
    pv.innerHTML = `
      <div class="row pv-nav"><button class="btn small" id="prev">←</button>
        <span class="muted">${i + 1} из ${p.cards.length} · ${esc(p.topics.find(t => t.id === c.t)?.title || '')}</span>
        <button class="btn small" id="nxt">→</button></div>
      <article class="card"></article>`;
    renderCard(c, pv.querySelector('.card'), () => {}, { imgRoot: ROOT });
    pv.querySelector('#prev').onclick = () => { i = (i - 1 + p.cards.length) % p.cards.length; draw(); };
    pv.querySelector('#nxt').onclick = () => { i = (i + 1) % p.cards.length; draw(); };
  };
  draw();
}

// ---------- список наборов ----------

function viewList() {
  const packs = Object.values(db.packs).sort((a, b) => b.edited - a.edited);
  $app.innerHTML = `
    <header class="top"><a class="studio-mark" href="${ROOT}?about" aria-label="Между уроками — о сервисе"><img class="ld-mark" src="${ROOT}icons/icon-192.png" alt="" width="40" height="40"></a>
      <div><div class="brand-title">Студия</div>
      <div class="brand-by">Между уроками · тренажёр для учеников</div></div>
      <div class="acct-bar">${accountBar()}</div></header>
    ${tariffPanel()}
    ${signedIn() && apiBase() ? '<div id="tg-me"></div>' : ''}
    ${signedIn() ? '' : `<section class="panel login-hint"><b>Войдите, чтобы ничего не потерять.</b> Сейчас тренажёры и доступ к ученикам хранятся только в этом браузере. С аккаунтом они сохраняются в облаке и открываются с телефона и компьютера. <a class="link-btn" href="${ROOT}login.html?role=tutor&next=studio/">Войти</a></section>`}
    <section class="panel steps-intro">
      <ol>
        <li><b>Добавьте материалы</b> — вставьте конспект, правила или задачи с решениями, ИИ сделает из них карточки. Или возьмите готовые из библиотеки: больше 3000 заданий ЕГЭ и олимпиад с разборами.</li>
        <li><b>Отправьте ссылку ученикам</b> — они занимаются по 10 минут в день, карточки возвращаются, когда начинают забываться.</li>
        <li><b>Смотрите прогресс</b> — кто занимался, где ошибается, что разобрать на уроке. Готовый отчёт для родителей в один клик.</li>
      </ol>
      <button class="btn primary" id="new">Создать тренажёр</button>
      <button class="btn" id="sample">Готовый пример за 1 клик</button>
      <label class="btn ghost">Импорт из файла<input type="file" accept=".json" id="imp" hidden></label>
      <p class="muted">Вопросы, идеи, хотите, чтобы тренажёр собрали за вас? <a href="https://t.me/trwqxp" target="_blank" rel="noopener">Напишите в Telegram @trwqxp</a></p>
    </section>
    ${packs.length ? `<h2>Мои тренажёры</h2>${packs.map(p => `
      <a class="topic" href="#/p/${p.id}/cards"><span class="dot" style="background:${esc(p.color)}"></span>
        <span class="topic-title">${esc(p.title)}<small>${esc(p.tutor || '')} · ${plural(p.cards.length, 'карточка', 'карточки', 'карточек')}</small></span>
        <span class="topic-meta">${isPublished(p) ? 'опубликован' : p.published ? 'есть правки' : 'черновик'}</span></a>`).join('')}` : ''}
    ${apiBase() ? '' : `<section class="panel warn-box"><b>Сервер не подключён.</b> Можно собирать наборы и смотреть их, но для ИИ, ссылок ученикам и отчётов нужен адрес сервера — укажите его в настройках тренажёра (инструкция в worker/README.md).</section>`}`;
  bindAccount($app);
  const tgSlot = $app.querySelector('#tg-me');
  if (tgSlot) tgPanel(tgSlot);
  $app.querySelector('#new').onclick = () => { location.hash = `#/p/${newPack()}/add`; };
  $app.querySelector('#sample').onclick = async e => {
    e.target.disabled = true;
    try {
      const src = await loadPack('ege-rus', ROOT);
      const id = newPack();
      const p = db.packs[id];
      Object.assign(p, { title: 'Пример: русский, ЕГЭ', subject: 'Русский язык', color: COLORS[1], tutor: '' });
      importTopics(p, src, ['task-4', 'task-13', 'task-15']);
      touch(p);
      toast('Пример готов — нажмите «Попробовать», чтобы увидеть его глазами ученика');
      location.hash = `#/p/${id}/cards`;
    } catch (err) { toast(err.message); e.target.disabled = false; }
  };
  $app.querySelector('#imp').onchange = async e => {
    const f = e.target.files[0];
    if (!f) return;
    try {
      const p = JSON.parse(await f.text());
      if (!Array.isArray(p.cards) || !Array.isArray(p.topics)) throw new Error();
      const id = newPack();
      db.packs[id] = { ...db.packs[id], ...p, id, published: 0, edited: Date.now() };
      persist();
      location.hash = `#/p/${id}/cards`;
    } catch { toast('Это не файл набора'); }
  };
}

// ---------- карточки ----------

function viewCards(p) {
  const f = store.get('zd-studio-filter', { q: '', t: '' });
  const box = shell(p, 'cards', `
    <div class="row toolbar">
      <input id="q" placeholder="Поиск по тексту" value="${esc(f.q)}">
      <select id="t"><option value="">Все темы</option>${p.topics.map(t =>
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
    const shown = cards.slice(0, 200);
    list.innerHTML = shown.map(([c, i]) => `
      <div class="card-row" data-i="${i}">
        <span class="badge">${KIND_NAMES[c.k] || c.k}</span>
        <span class="card-row-q">${esc(c.q.slice(0, 160))}${c.q.length > 160 ? '…' : ''}</span>
        <span class="card-row-actions">
          <button class="btn small" data-a="view">Открыть</button>
          ${c.k === 'match' || c.k === 'stress' ? '' : '<button class="btn small" data-a="edit">Изменить</button>'}
          ${c.k === 'stress' || !apiBase() ? '' : '<button class="btn small" data-a="more" title="ИИ сделает новые варианты этого типа">Похожие</button>'}
          <button class="btn small danger" data-a="del" aria-label="Удалить">✕</button>
        </span>
      </div>`).join('') + (cards.length > shown.length ? `<p class="muted center">Показаны первые 200 из ${cards.length} — уточните поиск</p>` : '');
  };
  draw();
  box.querySelector('#q').oninput = e => { f.q = e.target.value; store.set('zd-studio-filter', f); draw(); };
  box.querySelector('#t').onchange = e => { f.t = e.target.value; store.set('zd-studio-filter', f); draw(); };
  box.querySelector('#add').onclick = () => editCard(p, null, draw);
  list.onclick = e => {
    const b = e.target.closest('button');
    if (!b) return;
    const i = +b.closest('.card-row').dataset.i;
    if (b.dataset.a === 'view') preview(p, i);
    if (b.dataset.a === 'edit') editCard(p, i, draw);
    if (b.dataset.a === 'more') similarCards(p, p.cards[i], draw);
    if (b.dataset.a === 'del' && confirm('Удалить карточку?')) { p.cards.splice(i, 1); touch(p); draw(); }
  };
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
  const { box, close } = modal(`<h3>Похожие карточки</h3><p class="muted">ИИ делает новые варианты этого типа — до минуты…</p><div id="sim-out"></div>`);
  const out = box.querySelector('#sim-out');
  let r;
  try {
    r = await ai('generate', { material, subject: p.subject, count: 5 });
  } catch (err) {
    out.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
    return;
  }
  box.querySelector('p.muted').textContent = 'Снимите галочку с неудачных — остальные добавятся в ту же тему.';
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
}

function editCard(p, index, onSave) {
  const c = index === null ? { k: 'one', t: p.topics[0]?.id || '', q: '', o: [], a: '' } : structuredClone(p.cards[index]);
  const opts = c.k === 'one' || c.k === 'many' ? c.o : [{ id: 'а', t: '' }, { id: 'б', t: '' }, { id: 'в', t: '' }, { id: 'г', t: '' }];
  const right = new Set(c.k === 'many' ? c.a : c.k === 'one' ? [c.a] : []);
  const { box, close } = modal(`
    <h3>${index === null ? 'Новая карточка' : 'Карточка'}</h3>
    <div class="grid2">
      <label class="field"><span>Тема</span><select id="t">${p.topics.map(t => `<option value="${esc(t.id)}" ${t.id === c.t ? 'selected' : ''}>${esc(t.title)}</option>`).join('')}<option value="__new">+ Новая тема…</option></select></label>
      <label class="field"><span>Тип</span><select id="k">${['one', 'many', 'flip', 'num', 'open'].map(k => `<option value="${k}" ${k === c.k ? 'selected' : ''}>${KIND_NAMES[k]}</option>`).join('')}</select></label>
    </div>
    <div class="field"><label for="q">Вопрос или условие</label><textarea id="q" rows="4">${esc(c.q)}</textarea></div>
    <div id="opts" class="field"><span>Варианты — отметьте верные</span>
      <div id="optlist">${opts.map(o => optRow(o, right.has(o.id))).join('')}</div>
      <button class="btn small" id="addopt">+ Вариант</button></div>
    <div class="field" id="ans"><label for="a" id="ans-l">Ответ</label><textarea id="a" rows="4">${esc(['flip', 'open', 'num'].includes(c.k) ? c.a : '')}</textarea></div>
    <div class="field"><label for="e">Разбор (необязательно)</label><textarea id="e" rows="3">${esc(c.e || '')}</textarea></div>
    <div class="row"><button class="btn primary" id="save">Сохранить</button><button class="btn ghost" id="cancel">Отмена</button></div>`);
  const $ = s => box.querySelector(s);
  const sync = () => {
    const k = $('#k').value;
    $('#opts').hidden = !(k === 'one' || k === 'many');
    $('#ans').hidden = !$('#opts').hidden;
    $('#ans-l').textContent = k === 'open' ? 'Эталонное решение с ответом' : k === 'num' ? 'Ответ — число (например, 0,35)' : 'Ответ';
  };
  sync();
  $('#k').onchange = sync;
  $('#t').onchange = e => {
    if (e.target.value !== '__new') return;
    const title = prompt('Название темы');
    if (!title) { e.target.value = p.topics[0]?.id || ''; return; }
    const id = 'u-' + uid(5);
    p.topics.push({ id, title });
    e.target.insertAdjacentHTML('afterbegin', `<option value="${id}">${esc(title)}</option>`);
    e.target.value = id;
  };
  $('#addopt').onclick = () => {
    const ids = 'абвгдежзик';
    const n = $('#optlist').children.length;
    $('#optlist').insertAdjacentHTML('beforeend', optRow({ id: ids[n] || String(n + 1), t: '' }, false));
  };
  $('#optlist').onclick = e => { if (e.target.closest('.rm')) e.target.closest('.opt-edit').remove(); };
  $('#cancel').onclick = close;
  $('#save').onclick = () => {
    const k = $('#k').value;
    const card = { id: c.id || 'c-' + uid(6), t: $('#t').value, k, q: $('#q').value.trim() };
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
      card.a = $('#a').value.trim();
      if (!card.a) return toast('Напишите ответ');
      if (k === 'num' && !/^-?\d+([.,]\d+)?$/.test(card.a)) return toast('Для числового ответа нужно число: 12 или 0,35');
    }
    const e = $('#e').value.trim();
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
  <input type="text" value="${esc(o.t)}" placeholder="Вариант"><button class="btn small ghost rm" aria-label="Убрать">✕</button></div>`;

// ---------- добавление: ИИ и библиотека ----------

function viewAdd(p) {
  const box = shell(p, 'add', `
    <section class="panel">
      <h2>Из ваших материалов</h2>
      <p class="muted">Вставьте конспект, правила или разбор задач — или загрузите PDF и фото страниц. ИИ сделает карточки, а вы проверите их перед добавлением.</p>
      <div class="field"><label for="mat">Материал</label><textarea id="mat" rows="10" placeholder="Например: правила пунктуации при причастном обороте с примерами…"></textarea></div>
      <div class="row">
        <label class="btn small">+ PDF, фото или .txt<input type="file" accept=".txt,.md,.csv,.pdf,application/pdf,image/*" id="file" multiple hidden></label>
        <label class="row inline">Карточек: <input id="count" type="number" min="5" max="40" value="15" style="width:80px"></label>
        <button class="btn primary" id="gen" ${apiBase() ? '' : 'disabled'}>Сделать карточки</button>
      </div>
      ${apiBase() ? '' : '<p class="muted">Нужен сервер ИИ — укажите адрес во вкладке «Настройки».</p>'}
      <div id="att" class="att"></div>
      <div id="gen-out"></div>
    </section>
    <section class="panel">
      <h2>Из библиотеки</h2>
      <p class="muted">Готовые задания с разборами. Выберите тему — карточки и теория по ней добавятся в ваш тренажёр.</p>
      <div id="lib"><p class="muted">Загружаю…</p></div>
    </section>`);

  const files = [];
  const drawAtt = () => {
    box.querySelector('#att').innerHTML = files.map((f, i) =>
      `<span class="chip">${f.mime === 'application/pdf' ? 'PDF' : 'Фото'} · ${esc(f.name)}<button data-rm="${i}" aria-label="Убрать">✕</button></span>`).join('');
  };
  box.querySelector('#att').onclick = e => {
    const b = e.target.closest('[data-rm]');
    if (b) { files.splice(+b.dataset.rm, 1); drawAtt(); }
  };
  box.querySelector('#file').onchange = async e => {
    for (const f of e.target.files) {
      try {
        const a = await readAttachment(f);
        if (a.text !== undefined) {
          const mat = box.querySelector('#mat');
          mat.value = (mat.value ? mat.value + '\n\n' : '') + a.text.slice(0, 30000);
        } else {
          if (files.reduce((n, x) => n + x.data.length, 0) + a.data.length > MAX_ATTACH) throw new Error('Слишком много файлов за раз — до 10 МБ всего');
          files.push({ name: f.name, ...a });
        }
      } catch (err) { toast(`${f.name}: ${err.message}`); }
    }
    e.target.value = '';
    drawAtt();
  };
  box.querySelector('#gen').onclick = async e => {
    const material = box.querySelector('#mat').value.trim();
    if (material.length < 80 && !files.length) return toast('Добавьте текст (хотя бы абзац), PDF или фото');
    const out = box.querySelector('#gen-out');
    e.target.disabled = true;
    out.innerHTML = `<p class="muted">ИИ читает материал и делает карточки — это до ${files.length ? 'двух минут' : 'минуты'}…</p>`;
    try {
      const r = await ai('generate', { material, subject: p.subject, count: +box.querySelector('#count').value || 15,
        files: files.map(({ mime, data }) => ({ mime, data })) });
      reviewGenerated(p, r, out);
    } catch (err) {
      out.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
    }
    e.target.disabled = false;
  };
  drawLibrary(p, box.querySelector('#lib'));
}

function reviewGenerated(p, { topics, cards }, out) {
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

async function drawLibrary(p, box) {
  const lib = await loadLibrary(ROOT);
  box.innerHTML = `<div class="row">${lib.map(l => `<button class="btn" data-id="${esc(l.id)}">${esc(l.title)} · ${l.cards}</button>`).join('')}</div><div id="lib-topics"></div>`;
  box.querySelectorAll('[data-id]').forEach(b => b.onclick = async () => {
    box.querySelectorAll('[data-id]').forEach(x => x.classList.toggle('primary', x === b));
    const out = box.querySelector('#lib-topics');
    out.innerHTML = '<p class="muted">Загружаю…</p>';
    const src = await loadPack(b.dataset.id, ROOT);
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
  });
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
  return `<section class="panel plan">
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

// Задание тренажёра — одно на всех учеников. Задание и счётчики берём только из ответа /progress
function hwPanel(p, hw, students) {
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
  $('#hw-cancel').onclick = close;
  $('#hw-send').onclick = async e => {
    const goal = Number($('#hw-goal').value), due = $('#hw-due').value, topic = $('#hw-topic').value || null;
    if (!Number.isInteger(goal) || goal < 1 || goal > 200) return toast('Сколько карточек — от 1 до 200');
    if (!due) return toast('Укажите срок');
    e.target.disabled = true;
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
    } catch (err) { toast(err.message); e.target.disabled = false; }
  };
}

async function viewStudents(p) {
  const box = shell(p, 'students', '<p class="muted">Загружаю…</p>');
  if (!p.published) {
    box.innerHTML = `<div class="panel empty">Опубликуйте тренажёр и отправьте ссылку ученикам — здесь появится их прогресс. <a href="#/p/${p.id}/publish">Опубликовать</a></div>`;
    return;
  }
  let students, hw;
  try {
    ({ students, hw = null } = await api(`/packs/${p.id}/progress`, { key: db.keys[p.id] }));
  } catch (err) {
    box.innerHTML = `<div class="panel empty">${esc(err.message)}</div>`;
    return;
  }
  if (!students.length) {
    // Задание можно задать заранее — ученики увидят его с первого открытия
    box.innerHTML = `${hwPanel(p, hw, students)}<div class="panel empty">Пока никто не занимался. Ссылка для учеников: <a href="${esc(studentLink(p.id))}" target="_blank">${esc(studentLink(p.id))}</a></div>`;
  } else {
    students.sort((a, b) => b.at - a.at);
    const t = day();
    const active = students.filter(s => Date.now() - s.at < 7 * 864e5).length;
    const overdue = hw && t > dueDay(hw.due);
    const hasCourse = p.course?.lessons?.some(l => l.hw); // колонка «ДЗ курса» — только если в курсе есть ДЗ
    box.innerHTML = `
    <div class="hero-stats wide-stats">
      <div><b>${students.length}</b><span>учеников</span></div>
      <div><b>${active}</b><span>занимались за неделю</span></div>
      <div><b>${students.reduce((n, s) => n + (s.stats.week?.d || 0), 0)}</b><span>карточек за неделю</span></div>
    </div>
    ${hwPanel(p, hw, students)}
    <div class="table-wrap"><table class="students">
      <thead><tr><th>Ученик</th><th>Был(а)</th><th>Сегодня</th><th>7 дней</th><th>Задание</th>${hasCourse ? '<th>ДЗ курса</th>' : ''}<th>Точность</th><th>Серия</th><th>Освоено</th><th>Слабые темы</th><th></th></tr></thead>
      <tbody>${students.map((s, i) => {
        const st = s.stats;
        const acc = st.week?.d ? Math.round(st.week.ok / st.week.d * 100) : null;
        const todayDone = day(new Date(s.at)) === t ? st.today.d : 0;
        const weak = weakTopics(p, st);
        const d = hwDone(st, hw);
        return `<tr>
          <td><button class="link-btn" data-stu="${i}">${esc(s.name)}</button>${s.tg ? ' <span class="pill ok" title="Напоминания в Telegram включены">TG</span>' : ''}</td>
          <td class="${Date.now() - s.at > 3 * 864e5 ? 'late' : ''}">${ago(s.at)}</td>
          <td>${todayDone || '—'}</td>
          <td>${st.week?.d || 0} <span class="muted">· ${st.week?.days || 0} дн.</span>${activityStrip(st)}</td>
          ${hw ? `<td class="${d >= hw.goal ? 'ok' : overdue ? 'late' : ''}">${d}/${hw.goal}</td>` : '<td>—</td>'}
          ${hasCourse ? (cd => `<td class="nowrap ${cd.n && cd.onTime === cd.n ? 'ok' : cd.onTime < cd.n ? 'late' : ''}">${cd.n ? `${cd.onTime}/${cd.n} в срок` : '—'}</td>`)(courseDone(st)) : ''}
          <td>${acc === null ? '—' : `<span class="${acc < 60 ? 'late' : ''}">${acc}%</span>`}</td>
          <td>${st.streak || 0}</td>
          <td>${st.mastered}/${st.total}</td>
          <td>${weak.map(w => `${esc(w.title)} <span class="muted">${w.acc}%</span>`).join('<br>') || '—'}</td>
          <td class="nowrap"><button class="btn small" data-err="${i}">Ошибки</button> <button class="btn small" data-rep="${i}">Отчёт</button></td>
        </tr>`;
      }).join('')}</tbody></table></div>
    <p class="muted">Ученик отправляет прогресс после каждого занятия. «Отчёт» — готовый текст для родителей, а «Отчёты родителю в Telegram» в карточке ученика присылают его родителю каждое воскресенье.</p>
    ${lessonPlan(p, students)}`;
  }
  box.onclick = e => {
    const b = e.target.closest('button');
    if (!b) return;
    // После записи или снятия задания панель и колонка рисуются заново по свежему /progress
    if (b.id === 'hw-new') return hwDialog(p, hw, route);
    if (b.id === 'hw-del') {
      if (!confirm('Снять задание? Ученики перестанут его видеть.')) return;
      b.disabled = true;
      api(`/packs/${p.id}/hw`, { method: 'DELETE', key: db.keys[p.id] })
        .then(() => { toast('Задание снято'); route(); })
        .catch(err => { toast(err.message); b.disabled = false; });
      return;
    }
    if (b.id === 'copy-plan') {
      const txt = [...box.querySelectorAll('.plan h3, .plan li')].map(x => (x.tagName === 'H3' ? '\n' : '• ') + x.textContent.replace(/\s+/g, ' ').trim()).join('\n').trim();
      navigator.clipboard.writeText(`План урока — ${p.title}\n${txt}`).then(() => toast('Скопировано'));
      return;
    }
    if (b.dataset.stu !== undefined) return studentCard(p, students[+b.dataset.stu], hw);
    const s = students[+(b.dataset.err ?? b.dataset.rep)];
    if (!s) return;
    if (b.dataset.rep !== undefined) {
      const txt = parentReport(p, s, hw);
      const { box: m } = modal(`<h3>Отчёт для родителей</h3><textarea rows="9" id="rep">${esc(txt)}</textarea>
        <div class="row"><button class="btn primary" id="copy">Скопировать</button></div>`);
      m.querySelector('#copy').onclick = () => navigator.clipboard.writeText(m.querySelector('#rep').value).then(() => toast('Скопировано'));
    } else {
      const byId = Object.fromEntries(p.cards.map(c => [c.id, c]));
      const errs = (s.stats.errs || []).map(id => byId[id]).filter(Boolean);
      modal(`<h3>Ошибки: ${esc(s.name)}</h3>
        ${errs.length ? `<p class="muted">Последние карточки, где ученик ошибся, — готовый план разбора на уроке.</p><ol class="err-list">${errs.map(c => `<li>${esc(c.q.slice(0, 220))}</li>`).join('')}</ol>` : '<p>Ошибок нет.</p>'}`);
    }
  };
}

// Подробно про одного ученика: активность, все темы по точности, последние ошибки
function studentCard(p, s, hw) {
  const st = s.stats;
  const acc = st.week?.d ? Math.round(st.week.ok / st.week.d * 100) : null;
  const topics = Object.entries(st.topics || {})
    .map(([id, t]) => ({ title: p.topics.find(x => x.id === id)?.title || id, ...t }))
    .sort((a, b) => (a.acc ?? 101) - (b.acc ?? 101));
  const byId = Object.fromEntries(p.cards.map(c => [c.id, c]));
  const errs = (st.errs || []).map(id => byId[id]).filter(Boolean).slice(0, 8);
  const { box } = modal(`
    <h3>${esc(s.name)}</h3>
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
  box.querySelector('#stu-code').onclick = async () => {
    try {
      const { code } = await api(`/packs/${p.id}/parent-code`, { method: 'POST', body: { sid: s.sid }, key: db.keys[p.id] });
      out.innerHTML = `<div class="code-big">${esc(code)}</div><p class="muted">Родитель открывает ${esc(new URL(ROOT + 'login.html?role=parent', location.href).href)}, входит и вводит код. Действует сутки.</p>`;
    } catch (err) { out.innerHTML = `<p class="muted">${esc(err.message)}</p>`; }
  };
  box.querySelector('#stu-rep').onclick = () => navigator.clipboard.writeText(parentReport(p, s, hw)).then(() => toast('Отчёт скопирован'));

  // Отчёты родителю в Telegram: ссылка r_ на 7 дней. Отчёты идут, пока активен тариф репетитора;
  // «Отключить» гасит и подписки родителей, и все выданные ссылки
  const drawTg = () => {
    const paused = s.parents > 0 && signedIn() && !planOf('tutor').active;
    state.innerHTML = `${s.parents ? `<p>Подписано родителей: ${s.parents} <button class="btn small ghost danger" id="stu-tg-off">Отключить отчёты</button></p>` : ''}
      ${paused ? '<p class="muted">Отчёты родителям приостановлены — тариф закончился.</p> <button class="btn small primary" id="stu-pay">Продлить</button>' : ''}`;
    state.querySelector('#stu-pay')?.addEventListener('click', () => payDialog({ product: 'tutor' }));
    state.querySelector('#stu-tg-off')?.addEventListener('click', async e => {
      if (!confirm('Родители перестанут получать отчёты об этом ученике, старые ссылки тоже перестанут работать.')) return;
      e.target.disabled = true;
      try {
        await api(`/packs/${p.id}/notify/parent-off`, { method: 'POST', body: { sid: s.sid }, key: db.keys[p.id] });
        s.parents = 0;
        out.innerHTML = ''; // показанная ссылка тоже больше не действует
        drawTg();
        toast('Отчёты родителям отключены');
      } catch (err) { toast(err.message); e.target.disabled = false; }
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
      out.querySelector('#stu-tg-copy').onclick = () => navigator.clipboard.writeText(r.link).then(() => toast('Скопировано'));
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
  $('#les-cancel').onclick = close;
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
  $('#live-cancel').onclick = close;
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
        <label class="field"><span>Название тренажёра</span><input id="title" value="${esc(p.title)}"></label>
        <label class="field"><span>Репетитор (видят ученики)</span><input id="tutor" value="${esc(p.tutor)}" placeholder="Анна Сергеевна · ЕГЭ по русскому"></label>
        <label class="field"><span>Предмет</span><input id="subject" value="${esc(p.subject)}" placeholder="Русский язык"></label>
        <label class="field"><span>Новых карточек в день</span><input id="daily" type="number" min="1" max="50" value="${p.daily || 10}"></label>
      </div>
      <div class="field"><span>Цвет</span><div class="row">${COLORS.map(c => `<button class="swatch ${c === p.color ? 'on' : ''}" data-c="${c}" style="background:${c}" aria-label="${c}"></button>`).join('')}</div></div>
      <button class="btn primary" id="save">Сохранить</button>
    </section>
    <section class="panel">
      <h2>Темы</h2>
      ${p.topics.length ? p.topics.map((t, i) => `<div class="row topic-edit"><input data-i="${i}" value="${esc(t.title)}"><span class="muted">${p.cards.filter(c => c.t === t.id).length}</span><button class="btn small danger" data-del="${i}">Удалить</button></div>`).join('') : '<p class="muted">Темы появятся вместе с карточками.</p>'}
    </section>
    <section class="panel">
      <h2>Сервер</h2>
      <label class="field"><span>Адрес Cloudflare Worker (один на все тренажёры)</span><input id="api" value="${esc(store.get('zd-api', ''))}" placeholder="https://zadachnik.…workers.dev"></label>
      <button class="btn" id="save-api">Сохранить адрес</button>
    </section>
    <section class="panel">
      <h2>Файл</h2>
      <p class="muted">Резервная копия набора — на случай, если очистите браузер.</p>
      <button class="btn" id="export">Скачать набор</button>
      <button class="btn danger" id="drop">Удалить тренажёр</button>
    </section>`);
  let color = p.color;
  box.querySelectorAll('.swatch').forEach(s => s.onclick = () => {
    color = s.dataset.c;
    box.querySelectorAll('.swatch').forEach(x => x.classList.toggle('on', x === s));
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
  box.querySelectorAll('[data-del]').forEach(b => b.onclick = () => {
    const t = p.topics[+b.dataset.del];
    const n = p.cards.filter(c => c.t === t.id).length;
    if (!confirm(n ? `Удалить тему «${t.title}» и ${plural(n, 'карточку', 'карточки', 'карточек')} в ней?` : `Удалить тему «${t.title}»?`)) return;
    p.topics = p.topics.filter(x => x !== t);
    p.cards = p.cards.filter(c => c.t !== t.id);
    p.theory = p.theory.filter(l => l.topic !== t.id);
    p.course?.lessons.forEach(l => { if (l.topic === t.id) l.topic = null; }); // урок остаётся, без тренажёра
    touch(p);
    route();
  });
  box.querySelector('#save-api').onclick = () => { store.set('zd-api', box.querySelector('#api').value.trim()); toast('Адрес сохранён'); route(); };
  box.querySelector('#export').onclick = () => {
    const { edited, published, ...data } = p;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(data)], { type: 'application/json' }));
    a.download = `${p.title.replace(/[^\p{L}\p{N}]+/gu, '-')}.json`;
    a.click();
  };
  box.querySelector('#drop').onclick = () => {
    if (!confirm('Удалить тренажёр из студии? Ученики с опубликованной ссылкой продолжат заниматься.')) return;
    delete db.packs[p.id];
    db.deleted[p.id] = Date.now();
    persist();
    location.hash = '#/';
  };
}

// QR-код ссылки (vendor/qrcode.js, MIT): чёрные модули на белом — читается любой камерой
function qrSvg(text, cell) {
  const qr = window.qrcode(0, 'M');
  qr.addData(text);
  qr.make();
  return qr.createSvgTag({ cellSize: cell, margin: 2, scalable: true });
}

function viewPublish(p) {
  const link = studentLink(p.id);
  const box = shell(p, 'publish', `
    <section class="panel">
      ${p.published ? `
        <h2>Ссылка для учеников</h2>
        <div class="row"><input readonly value="${esc(link)}" id="link"><button class="btn" id="copy">Скопировать</button></div>
        <p class="muted">Или код: <b>${p.id}</b> — ученик вводит его на главной.</p>
        ${window.qrcode ? `<div class="qr-wrap"><div class="qr">${qrSvg(link, 5)}</div>
          <div><b>QR-код для урока</b><p class="muted">Покажите на экране — ученики наведут камеру телефона и сразу откроют тренажёр.</p>
          <button class="btn small" id="qr-big">На весь экран</button></div></div>` : ''}
        <div class="row">
          <a class="btn" target="_blank" href="https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(`Тренажёр «${p.title}»: занимайся по 10 минут в день`)}">Отправить в Telegram</a>
          <a class="btn ghost" target="_blank" href="${esc(link)}">Открыть как ученик</a>
        </div>` : '<p>Тренажёр ещё не опубликован. После публикации появится ссылка для учеников.</p>'}
      <p>${isPublished(p) ? 'Ученики видят актуальную версию.' : p.published ? '<b>Есть изменения, которых ученики пока не видят.</b>' : ''}</p>
      <button class="btn primary" id="pub" ${apiBase() ? '' : 'disabled'}>${p.published ? 'Обновить у учеников' : 'Опубликовать'}</button>
      ${apiBase() ? '' : '<p class="muted">Для публикации укажите адрес сервера во вкладке «Настройки».</p>'}
    </section>
    <section class="panel">
      <h2>Проверка перед отправкой</h2>
      <ul class="checklist">
        <li class="${p.tutor ? 'ok' : ''}">Указано имя репетитора — ученик должен понять, от кого тренажёр</li>
        <li class="${p.cards.length >= 20 ? 'ok' : ''}">Хотя бы 20 карточек (сейчас ${p.cards.length}) — чтобы хватило на пару занятий</li>
        <li class="${p.topics.length >= 2 ? 'ok' : ''}">Больше одной темы — ученику проще ориентироваться</li>
      </ul>
    </section>`);
  box.querySelector('#copy')?.addEventListener('click', () => navigator.clipboard.writeText(link).then(() => toast('Скопировано')));
  box.querySelector('#qr-big')?.addEventListener('click', () =>
    modal(`<div class="qr-big">${qrSvg(link, 12)}<p><b>${esc(p.title)}</b><br><span class="muted">Наведите камеру телефона</span></p></div>`));
  box.querySelector('#pub').onclick = async e => {
    if (!p.cards.length) return toast('Добавьте карточки');
    // Новый тренажёр публикуется из аккаунта — так ключи и ученики не потеряются
    if (!p.published && !signedIn()) return loginDialog({
      role: 'tutor', why: 'Чтобы опубликовать тренажёр, войдите: ключи и ученики сохранятся в аккаунте. Первые 14 дней — всё без ограничений.',
      onDone: async () => { await addRole('tutor'); await syncCloud(); toast('Готово — теперь нажмите «Опубликовать»'); },
    });
    e.target.disabled = true;
    try {
      const { edited, published, ...data } = p;
      // Пустые темы (например, созданные и брошенные в редакторе) ученику не нужны
      // Темы уроков курса тоже нужны: по ним считается ДЗ
      data.topics = p.topics.filter(t => p.cards.some(c => c.t === t.id) || p.theory.some(l => l.topic === t.id) || p.course?.lessons?.some(l => l.topic === t.id));
      await api(`/packs/${p.id}`, { method: 'PUT', body: data, key: db.keys[p.id] });
      p.published = Date.now();
      p.edited = Math.min(p.edited, p.published);
      persist();
      toast('Опубликовано');
      route();
    } catch (err) {
      toast(err.message);
      e.target.disabled = false;
      if (err.status === 402) payDialog({ product: 'tutor' });
    }
  };
}

// ---------- навигация ----------

function route() {
  const [, kind, id, tab] = location.hash.split('/');
  if (kind === 'new') { history.replaceState(null, '', `#/p/${newPack()}/add`); return route(); }
  const p = kind === 'p' && db.packs[id];
  if (!p) { document.documentElement.style.removeProperty('--accent'); return viewList(); }
  ({ cards: viewCards, add: viewAdd, course: viewCourse, students: viewStudents, settings: viewSettings, publish: viewPublish }[tab] || viewCards)(p);
  document.documentElement.style.setProperty('--accent', p.color);
}

window.addEventListener('hashchange', route);
// Правки из соседней вкладки студии
window.addEventListener('storage', e => { if (e.key === 'zd-studio') { db = { deleted: {}, ...store.get('zd-studio', db) }; route(); } });
route();
finishRedirectLogin().then(async done => {
  if (done) { await addRole('tutor'); setCloud('saving'); }
  await finishPayment();
  if (signedIn()) await refreshAccount(); // свежий статус тарифа
  syncCloud();
});
