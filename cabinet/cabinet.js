// Личный кабинет. Новый аккаунт сначала выбирает, кто он, — дальше у каждой
// роли свой раздел: репетитор (ученики и тариф), ученик (серия, тренажёры,
// библиотека), родитель (дети и оплата). Ролей у одного аккаунта может быть несколько.
import { store, api, esc, day, plural, toast, loadLibrary } from '../lib.js';
import { signedIn, account, signOut, addRole, finishRedirectLogin, finishPayment, refreshAccount, accountFresh,
  loginDialog, payDialog, planOf, daysLeft, dateRu, TG_ICON, openLink } from '../account.js';
import { renderChildren, stats } from '../parent/view.js';

const $app = document.getElementById('app');
const params = new URLSearchParams(location.search);
const DAY = 864e5;

const ICON = {
  tutor: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4M7 8h6M7 11h4"/></svg>',
  student: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c3 2 9 2 12 0v-5"/></svg>',
  parent: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="8" cy="7" r="3"/><circle cx="17" cy="9" r="2.3"/><path d="M2 20c0-4 3-6 6-6s6 2 6 6M14 20c0-3 1.5-5 3-5s4 2 4 5"/></svg>',
  settings: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/></svg>',
};

const ROLES = {
  tutor: { tab: 'Репетитор', title: 'Я репетитор', what: 'Делаю тренажёры ученикам, смотрю, кто занимается, отправляю отчёты родителям.' },
  student: { tab: 'Ученик', title: 'Я ученик', what: 'Решаю карточки между уроками: тренажёр репетитора или библиотека ЕГЭ.' },
  parent: { tab: 'Родитель', title: 'Я родитель', what: 'Хочу видеть, как ребёнок занимается, и оплачивать доступ.' },
};
const ORDER = ['tutor', 'student', 'parent'];
const rolesOf = a => ORDER.filter(r => a?.roles?.[r]);
const initials = a => esc((a?.name || a?.email || '?').trim().slice(0, 2).toUpperCase());
const words = (n, one, few, many) => plural(n, one, few, many).replace(/^\d+ /, '');
const trainerUrl = ref => ref.startsWith('t:') ? `../?t=${encodeURIComponent(ref.slice(2))}` : `../?p=${encodeURIComponent(ref)}`;

// ---------- шапка и вкладки ----------

// Шапка как в студии: логотип, путь в студию (у репетитора) и аватар. Вкладки на телефоне
// переносятся на вторую строку — ни одна не прячется за край экрана
function shell(tab, body) {
  const a = account();
  const tabs = [...rolesOf(a).map(r => [r, ROLES[r].tab]), ['settings', 'Настройки']];
  $app.innerHTML = `
    <header class="cab-top">
      <a class="ld-logo" href="../?about" aria-label="Между уроками — о сервисе"><img class="ld-mark" src="../icons/icon-192.png" alt="" width="40" height="40"><span class="cab-logo-text">Между уроками</span></a>
      <span class="cab-top-right">
        ${a?.roles?.tutor ? '<a class="btn small cab-studio" href="../studio/">Студия</a>' : ''}
        <a class="cab-me" href="#settings" aria-label="Настройки аккаунта"><span class="avatar">${initials(a)}</span><span class="cab-me-name">${esc(a?.name || a?.email || 'Аккаунт')}</span></a>
      </span>
    </header>
    <nav class="cab-tabs" aria-label="Разделы кабинета">${tabs.map(([id, t]) =>
      `<a href="#${id}" class="${tab === id ? 'on' : ''}" ${tab === id ? 'aria-current="page"' : ''} aria-label="${t}">${ICON[id]}<span>${t}</span></a>`).join('')}
      ${rolesOf(a).length < 3 ? '<a href="#role" class="cab-add" aria-label="Добавить роль"><b aria-hidden="true">+</b><span>Роль</span></a>' : ''}</nav>
    <div id="cab-body">${body}</div>`;
  return $app.querySelector('#cab-body');
}

// Плашка тарифа: пробный / оплачен / бесплатный. «Оплатить» кнопкой — только когда пробный
// кончился; в пробный период и при оплаченном — мелкая ссылка «Тарифы» / «Продлить»
function planPanel(product, { name, free, via }) {
  const st = planOf(product), now = Date.now();
  let tone = 'free', text = free, btn = 'Оплатить', quiet = false;
  if ((st.paidUntil || 0) > now) { tone = 'ok'; text = `${name} оплачен до ${dateRu(st.paidUntil)}`; btn = 'Продлить'; quiet = true; }
  else if (via && st.via > now) { tone = 'ok'; text = via; btn = ''; }
  else if ((st.trialEnd || 0) > now) { tone = 'trial'; text = `Пробный период: ${plural(daysLeft(st.trialEnd), 'день', 'дня', 'дней')} без ограничений`; btn = 'Тарифы'; quiet = true; }
  return `<div class="panel plan ${tone} cab-plan"><span>${text}</span>${!btn ? '' : quiet
    ? `<button class="link-btn" data-pay="${product}">${btn}</button>` : `<button class="btn small primary" data-pay="${product}">${btn}</button>`}</div>`;
}
const bindPay = box => box.querySelectorAll('[data-pay]').forEach(b => { b.onclick = () => payDialog({ product: b.dataset.pay }); });

// Telegram репетитора (GET /me/notify): подключён ли бот и свежая ссылка t_ на час.
// Та же панель, что в студии (studio.js tgPanel)
const tzNow = () => -new Date().getTimezoneOffset();
let tgWait = false;
async function tgPanel(slot) {
  const at = Date.now(), r = await api(`/me/notify?tz=${tzNow()}`).catch(() => null);
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

// ---------- выбор роли ----------

function viewRole(first) {
  const a = account(), have = rolesOf(a);
  const ask = [location.hash.slice(1), params.get('role')].find(r => ROLES[r] && !have.includes(r));
  const wanted = ask || null;
  let pick = wanted || ORDER.find(r => !have.includes(r));
  const body = `
    <section class="cab-hello">
      <h1>${first ? 'Кто вы?' : 'Добавить роль'}</h1>
      <p class="muted">${first ? 'От этого зависит, что будет в кабинете. Потом можно добавить ещё роль — например, репетитору стать и родителем.' : 'Раздел появится во вкладках кабинета.'}</p>
    </section>
    <div class="role-cards" role="radiogroup">${ORDER.filter(r => !have.includes(r)).map(r => `
      <button class="role-card ${r === pick ? 'on' : ''}" role="radio" aria-checked="${r === pick}" data-role="${r}">
        <span class="role-ico">${ICON[r]}</span><b>${ROLES[r].title}</b><span>${ROLES[r].what}</span></button>`).join('')}
    </div>
    ${first ? `<div class="field cab-name"><label for="name">Как вас зовут</label><input id="name" maxlength="80" autocomplete="name" value="${esc(a?.name || '')}" placeholder="Имя и фамилия"></div>` : ''}
    <button class="btn primary big cab-go" id="go">Продолжить</button>`;
  const box = first ? ($app.innerHTML = `<header class="cab-top"><a class="ld-logo" href="../?about"><img class="ld-mark" src="../icons/icon-192.png" alt="" width="40" height="40"><span class="cab-logo-text">Между уроками</span></a>
    <button class="btn small" id="out">Выйти</button></header><div id="cab-body">${body}</div>`, $app) : shell('role', body);
  box.querySelector('#out')?.addEventListener('click', leave);
  box.querySelectorAll('[data-role]').forEach(b => {
    b.onclick = () => {
      pick = b.dataset.role;
      box.querySelectorAll('[data-role]').forEach(x => { x.classList.toggle('on', x === b); x.setAttribute('aria-checked', x === b); });
    };
  });
  box.querySelector('#go').onclick = async e => {
    e.target.disabled = true;
    const name = box.querySelector('#name')?.value.trim();
    try {
      if (name && name !== a?.name) await api('/me', { method: 'PATCH', body: { name } });
      await addRole(pick);
      await refreshAccount();
      history.replaceState(null, '', location.pathname + '#' + pick);
      route();
    } catch (err) { toast(err.message); e.target.disabled = false; }
  };
}

// ---------- репетитор ----------

// Нетронутый «Новый тренажёр» (так студия создавала раньше) в списках не показываем — как в студии
const isBlank = p => !p.cards?.length && !p.topics?.length && !p.theory?.length && !p.published
  && !p.course?.lessons?.length && !p.course?.lives?.length && (p.title || 'Новый тренажёр') === 'Новый тренажёр';
const packsOf = s => Object.values(s?.packs || {}).filter(p => !(s.deleted?.[p.id] >= p.edited) && !isBlank(p)).sort((x, y) => y.edited - x.edited);
const packState = p => (p.published ? (p.published >= p.edited ? 'опубликован' : 'есть правки') : 'черновик');
const STUDIO = '../studio/';

async function viewTutor() {
  const box = shell('tutor', '<p class="loading">Загружаю учеников…</p>');
  let studio;
  try { studio = await api('/me/studio'); } catch (err) { if (box.isConnected) tutorOffline(box, err); return; }
  if (!box.isConnected) return;
  const packs = packsOf(studio);
  const plan = planPanel('tutor', { name: 'Тариф репетитора', free: 'Бесплатный тариф: 1 опубликованный тренажёр и до 3 учеников' });
  // Новый репетитор: один шаг — «Создайте первый тренажёр». Статистика из нулей, Telegram и тариф — потом
  if (!packs.length) {
    box.innerHTML = `
      <section class="panel cab-empty first-step">
        <h1>Создайте первый тренажёр</h1>
        <p>Вставьте свои материалы — ИИ сделает карточки — или возьмите готовые задания ЕГЭ. Опубликуйте и отправьте ученикам ссылку: здесь появится, кто занимается, где ошибки и что разобрать на уроке.</p>
        <div class="first-ways">
          <a class="btn primary big" href="${STUDIO}#/new">Создать тренажёр</a>
          <a class="btn big" href="${STUDIO}#/sample">Сначала посмотреть пример</a>
        </div>
      </section>
      ${plan}`;
    bindPay(box);
    return;
  }
  const withStudents = await Promise.all(packs.map(async p => {
    if (!p.published) return { p, students: [] };
    try { return { p, students: (await api(`/packs/${encodeURIComponent(p.id)}/progress`)).students }; }
    catch { return { p, students: [] }; }
  }));
  if (!box.isConnected) return;
  const published = packs.some(p => p.published);
  const all = withStudents.flatMap(({ p, students }) => students.map(s => ({ ...s, pack: p })));
  const now = Date.now();
  const active = all.filter(s => now - s.at < 7 * DAY);
  const weekCards = all.reduce((n, s) => n + (s.stats?.week?.d || 0), 0);
  const weekOk = all.reduce((n, s) => n + (s.stats?.week?.ok || 0), 0);
  // Кому стоит написать: давно не заходил или точность за неделю ниже 60%
  const attention = all.map(s => {
    const idle = Math.floor((now - s.at) / DAY), w = s.stats?.week || {};
    const acc = w.d >= 10 ? Math.round(w.ok / w.d * 100) : null;
    if (idle >= 3) return { s, why: `не занимается ${plural(idle, 'день', 'дня', 'дней')}`, tone: 'bad', rank: idle };
    if (acc !== null && acc < 60) return { s, why: `точность за неделю ${acc}%`, tone: 'mid', rank: 1 };
    return null;
  }).filter(Boolean).sort((x, y) => y.rank - x.rank).slice(0, 6);

  box.innerHTML = `
    ${published ? `<section class="hero-stats cab-stats">
      <div><b>${all.length}</b><span>${words(all.length, 'ученик', 'ученика', 'учеников')}</span></div>
      <div><b>${active.length}</b><span>занимались за неделю</span></div>
      <div><b>${weekCards ? Math.round(weekOk / weekCards * 100) + '%' : '—'}</b><span>точность за неделю</span></div>
    </section>` : ''}
    ${all.length ? `<section class="panel">
      <h2>Требуют внимания</h2>
      ${attention.length ? `<ul class="cab-list">${attention.map(({ s, why, tone }) => `
        <li><a href="${STUDIO}#/p/${esc(s.pack.id)}/students"><span class="avatar small">${esc(s.name.slice(0, 2).toUpperCase())}</span>
          <span class="cab-li-main"><b>${esc(s.name)}</b><small>${esc(s.pack.title)}</small></span><span class="pill ${tone}">${esc(why)}</span></a></li>`).join('')}</ul>`
        : '<p class="muted">Все занимаются — никого не нужно догонять.</p>'}
    </section>` : published ? `<section class="panel"><h2>Ученики</h2><p class="muted">Пока никто не занимался. Отправьте ученикам ссылку из вкладки тренажёра «Ссылка» — как только ученик ответит на первые карточки, он появится здесь.</p></section>`
      : `<section class="panel cab-empty"><h2>Опубликуйте тренажёр</h2><p>Черновик готов — опубликуйте его и отправьте ученикам ссылку. Здесь появится, кто занимается и где ошибки.</p>
        <a class="btn primary" href="${STUDIO}#/p/${esc(packs[0].id)}/publish">Опубликовать «${esc(packs[0].title)}»</a></section>`}
    <section class="panel">
      <div class="cab-head"><h2>Мои тренажёры</h2><a class="btn small primary" href="${STUDIO}#/new">+ Создать</a></div>
      <ul class="cab-list">${withStudents.map(({ p, students }) => `
        <li><a href="${STUDIO}#/p/${esc(p.id)}/${students.length ? 'students' : 'cards'}"><span class="dot" style="background:${esc(p.color || '#5B3DF5')}"></span>
          <span class="cab-li-main"><b>${esc(p.title)}</b><small>${plural(p.cards?.length || 0, 'карточка', 'карточки', 'карточек')} · ${packState(p)}</small></span>
          <span class="pill">${plural(students.length, 'ученик', 'ученика', 'учеников')}</span></a></li>`).join('')}</ul>
    </section>
    ${published ? `<div id="tg-me"></div>
    <section class="panel cab-tip">
      <h2>Родителям</h2>
      <p class="muted">Отчёт родителю может приходить в Telegram каждое воскресенье: Студия → Ученики → ученик → «Отчёты родителю в Telegram». Или дайте код — родитель увидит прогресс в своём кабинете.</p>
      <a class="btn" href="${STUDIO}">Открыть студию</a>
    </section>` : ''}
    ${plan}`;
  bindPay(box);
  const tg = box.querySelector('#tg-me');
  if (tg) tgPanel(tg);
}

// Сервер не отвечает: не «Нет связи» вместо всего, а «Повторить», тренажёры из этого браузера и путь в студию
function tutorOffline(box, err) {
  const local = store.get('zd-studio', null);
  const packs = packsOf(local);
  box.innerHTML = `
    <section class="panel warn-box" role="alert">
      <p><b>${err.status ? esc(err.message) : 'Нет связи с сервером.'}</b> Учеников и отчёты покажем, когда связь вернётся. Тренажёры можно открыть и без неё.</p>
      <div class="row"><button class="btn primary" id="retry">Повторить</button><a class="btn" href="${STUDIO}">Открыть студию</a></div>
    </section>
    ${packs.length ? `<section class="panel">
      <h2>Тренажёры в этом браузере</h2>
      <ul class="cab-list">${packs.map(p => `
        <li><a href="${STUDIO}#/p/${esc(p.id)}/cards"><span class="dot" style="background:${esc(p.color || '#5B3DF5')}"></span>
          <span class="cab-li-main"><b>${esc(p.title)}</b><small>${plural(p.cards?.length || 0, 'карточка', 'карточки', 'карточек')} · ${packState(p)}</small></span></a></li>`).join('')}</ul>
    </section>` : ''}`;
  box.querySelector('#retry').onclick = e => { e.currentTarget.disabled = true; viewTutor(); };
}

// ---------- ученик ----------

// Названия тренажёров: из сводки в облачном прогрессе (/me/progress отдаёт title), из недавних
// в этом браузере и из библиотеки. Набор с сервера качаем, только если названия нигде нет
async function packTitles(refs, items = []) {
  const titles = {};
  for (const i of items) if (i.title) titles[i.ref] = i.title;
  for (const r of store.get('zd-recent', [])) titles[r.ref] ||= r.title;
  const lib = await loadLibrary('../').catch(() => []);
  for (const p of lib) titles[p.id] ||= p.title;
  await Promise.all(refs.filter(r => !titles[r] && r.startsWith('t:')).map(async r => {
    try { titles[r] = (await api('/packs/' + encodeURIComponent(r.slice(2)))).title; } catch { /* набор удалён */ }
  }));
  return { titles, lib };
}

async function viewStudent() {
  const box = shell('student', '<p class="loading">Загружаю прогресс…</p>');
  let items = [];
  try { ({ items } = await api('/me/progress')); } catch (err) { toast(err.message); }
  // Сюда же — тренажёры, открытые на этом устройстве, но ещё без прогресса в аккаунте
  const refs = [...new Set([...items.map(i => i.ref), ...store.get('zd-recent', []).map(r => r.ref)])];
  const { titles, lib } = await packTitles(refs, items);
  const byRef = Object.fromEntries(items.map(i => [i.ref, i]));
  // Общий журнал по всем тренажёрам: серия и «сегодня» — одни на ученика
  const log = {};
  for (const i of items) for (const [d, l] of Object.entries(i.log)) { const x = log[d] ||= { d: 0, ok: 0 }; x.d += l.d || 0; x.ok += l.ok || 0; }
  const s = stats({ log }, null);
  const today = log[day()]?.d || 0, goal = 20;
  const first = refs[0];
  const name = (account()?.name || '').split(' ')[0];

  box.innerHTML = `
    <section class="cab-hello student">
      <h1>${name ? `Привет, ${esc(name)}!` : 'Привет!'}</h1>
      <p>${today >= goal ? 'Цель на сегодня выполнена. Можно ещё, а можно отдохнуть.' : s.streak ? `Серия ${plural(s.streak, 'день', 'дня', 'дней')} — не прерывай её сегодня.` : 'Начни серию: 10 минут в день между уроками.'}</p>
      <div class="cab-goal"><span class="cab-goal-bar"><i style="width:${Math.min(100, Math.round(today / goal * 100))}%"></i></span><b>${today} из ${goal}</b></div>
      ${first ? `<a class="btn cta big" href="${trainerUrl(first)}">Продолжить: ${esc(titles[first] || 'тренажёр')}</a>` : `<a class="btn cta big" href="../#/library">Выбрать тренажёр</a>`}
    </section>
    <section class="hero-stats cab-stats">
      <div><b>${s.streak}</b><span>${words(s.streak, 'день', 'дня', 'дней')} подряд</span></div>
      <div><b>${s.days7} из 7</b><span>дней на неделе</span></div>
      <div><b>${s.acc7 === null ? '—' : s.acc7 + '%'}</b><span>точность</span></div>
    </section>
    ${refs.length ? `<section class="panel">
      <h2>Мои тренажёры</h2>
      <ul class="cab-list">${refs.map(r => {
        const it = byRef[r], st = it ? stats(it, null) : null;
        return `<li><a href="${trainerUrl(r)}"><span class="dot" style="background:${esc(lib.find(p => p.id === r)?.color || '#5B3DF5')}"></span>
          <span class="cab-li-main"><b>${esc(titles[r] || 'Тренажёр')}</b><small>${r.startsWith('t:') ? 'от репетитора' : 'библиотека ЕГЭ'}${it ? ' · начато ' + plural(it.started, 'карточка', 'карточки', 'карточек') : ''}</small></span>
          ${st?.acc7 != null ? `<span class="pill ${st.acc7 < 60 ? 'bad' : st.acc7 < 80 ? 'mid' : 'ok'}">${st.acc7}%</span>` : ''}</a></li>`;
      }).join('')}</ul>
    </section>` : ''}
    <section class="panel">
      <h2>Тренажёр от репетитора</h2>
      <p class="muted">Вставьте ссылку, которую прислал репетитор.</p>
      <div class="row"><input id="link" placeholder="https://…/?t=…" autocomplete="off"><button class="btn primary" id="open">Открыть</button></div>
    </section>
    ${planPanel('lib', { name: 'Доступ к библиотеке ЕГЭ', free: 'Библиотека ЕГЭ: бесплатная часть — 2 прототипа в каждом задании', via: 'Библиотека ЕГЭ открыта — входит в тариф репетитора' })}
    <section class="panel">
      <h2>Родителям</h2>
      <p class="muted">Дай родителю код — он увидит в своём кабинете дни занятий и точность. Ответы и ошибки он не видит.</p>
      <button class="btn" id="pcode">Код для родителя</button>
      <div id="pcode-box"></div>
    </section>`;
  bindPay(box);
  const open = () => {
    const v = box.querySelector('#link').value.trim();
    const id = /[?&]t=([a-z0-9-]+)/i.exec(v)?.[1] || (/^[a-z0-9-]{3,40}$/i.test(v) ? v : null);
    if (!id) { toast('Не похоже на ссылку репетитора'); return; }
    location.href = trainerUrl('t:' + id.toLowerCase());
  };
  box.querySelector('#open').onclick = open;
  box.querySelector('#link').onkeydown = e => { if (e.key === 'Enter') open(); };
  box.querySelector('#pcode').onclick = async () => {
    try {
      const { code } = await api('/me/parent-code', { method: 'POST' });
      box.querySelector('#pcode-box').innerHTML = `<div class="code-big">${esc(code)}</div>
        <p class="muted small-note">Родитель входит на ${esc(new URL('../login', location.href).host)} как «Родитель» и вводит код. Действует сутки, подходит один раз.</p>`;
    } catch (err) { toast(err.message); }
  };
}

// ---------- родитель ----------

async function viewParent() {
  const box = shell('parent', '<p class="loading">Загружаю…</p>');
  const hello = document.createElement('section');
  hello.className = 'cab-hello';
  box.innerHTML = '';
  const inner = document.createElement('div');
  box.append(hello, inner);
  hello.innerHTML = `<h1>Как занимаются дети</h1><p class="muted">Дни занятий, точность по неделям и темы, которые стоит подтянуть. Обновляется после каждого занятия.</p>`;
  await renderChildren(inner);
}

// ---------- настройки ----------

const WAYS = { tg: 'Telegram', email: 'Почта', yandex: 'Яндекс ID', vk: 'VK ID', google: 'Google' };

function viewSettings() {
  const a = account();
  const box = shell('settings', `
    <section class="panel">
      <h2>Профиль</h2>
      <div class="field"><label for="name">Имя</label><input id="name" maxlength="80" autocomplete="name" value="${esc(a?.name || '')}"></div>
      <button class="btn primary" id="save">Сохранить</button>
    </section>
    <section class="panel">
      <h2>Роли</h2>
      <ul class="cab-list">${ORDER.map(r => `<li><div class="cab-li-row"><span class="role-ico small">${ICON[r]}</span>
        <span class="cab-li-main"><b>${ROLES[r].tab}</b><small>${ROLES[r].what}</small></span>
        ${a?.roles?.[r] ? '<span class="pill ok">есть</span>' : `<button class="btn small" data-add="${r}">Добавить</button>`}</div></li>`).join('')}</ul>
    </section>
    <section class="panel">
      <h2>Способы входа</h2>
      <p class="muted">Сейчас: ${[...new Set(a?.idents || [])].map(i => WAYS[i] || i).join(', ') || '—'}${a?.email ? ` · ${esc(a.email)}` : ''}</p>
      <button class="btn" id="link">Привязать ещё способ</button>
      <div id="link-box"></div>
    </section>
    <section class="panel">
      <h2>Помощь</h2>
      <p class="muted">Если что-то не работает с оплатой или доступом, напишите в Telegram <a href="https://t.me/trwqxp" target="_blank" rel="noopener">@trwqxp</a> и приложите номер аккаунта: <code class="acct-id">${esc(a?.id || '')}</code></p>
    </section>
    <button class="btn big cab-out" id="out">Выйти из аккаунта</button>`);
  box.querySelector('#save').onclick = async () => {
    try { await api('/me', { method: 'PATCH', body: { name: box.querySelector('#name').value.trim() } }); await refreshAccount(); toast('Сохранено'); viewSettings(); }
    catch (err) { toast(err.message); }
  };
  box.querySelectorAll('[data-add]').forEach(b => {
    b.onclick = async () => { await addRole(b.dataset.add); location.hash = '#' + b.dataset.add; };
  });
  box.querySelector('#link').onclick = e => {
    e.target.hidden = true;
    loginDialog({ into: box.querySelector('#link-box'), onDone: async () => { await refreshAccount(); toast('Способ входа привязан'); viewSettings(); } });
  };
  box.querySelector('#out').onclick = leave;
}

// «Выйти»: всё, что уже в облаке, стирается из браузера; несохранённое — спросить (account.js signOut)
async function leave(e) {
  const btn = e.currentTarget;
  btn.disabled = true;
  const r = await signOut();
  if (r.out) location.href = '../login';
  else btn.disabled = false;
}

// ---------- навигация ----------

function route() {
  const a = account(), have = rolesOf(a);
  const tab = location.hash.slice(1);
  if (!have.length) return viewRole(true);
  // Раздел роли, которой ещё нет (ссылка cabinet/#parent) — предлагаем её добавить
  if (have.length < 3 && (tab === 'role' || (ROLES[tab] && !have.includes(tab))
    || (ROLES[params.get('role')] && !have.includes(params.get('role')) && !tab))) return viewRole(false);
  const r = have.includes(tab) ? tab : tab === 'settings' ? tab
    : have.includes(params.get('role')) ? params.get('role') : have.includes(store.get('zd-cab', '')) ? store.get('zd-cab', '') : have[0];
  if (r !== tab) history.replaceState(history.state, '', location.pathname + location.search + '#' + r);
  if (ROLES[r]) store.set('zd-cab', r);
  window.scrollTo(0, 0);
  ({ tutor: viewTutor, student: viewStudent, parent: viewParent, settings: viewSettings })[r]();
}

const PAY_WANT = 'zd-pay-want';
// Без входа или вход закончился (401 на любом запросе) — на страницу входа; она скажет «Сессия закончилась».
// Ссылка вида cabinet/#parent — там сразу открыта нужная вкладка
let toLoginOnce = false;
const toLogin = () => {
  if (toLoginOnce) return;
  toLoginOnce = true;
  const want = location.hash.slice(1);
  location.replace(`../login?${ROLES[want] ? `role=${want}&` : ''}next=${encodeURIComponent('cabinet/' + location.hash)}`);
};
window.addEventListener('zd-session-expired', toLogin);

async function main() {
  await finishRedirectLogin();
  // Вернулись после оплаты — платёж применяем даже без входа (например, банк открыл другой браузер)
  await finishPayment();
  // Кнопки «Продлить» из бота ведут на cabinet/?pay=tutor#tutor — сразу окно оплаты. Страница
  // входа возвращает в кабинет без ?pay, поэтому до входа желание оплатить ждёт в sessionStorage
  const pay = [params.get('pay'), sessionStorage.getItem(PAY_WANT)].find(p => p === 'tutor' || p === 'lib');
  if (pay) sessionStorage.setItem(PAY_WANT, pay);
  if (!signedIn()) return toLogin();
  const start = () => {
    window.addEventListener('hashchange', route);
    route();
    sessionStorage.removeItem(PAY_WANT);
    if (pay) {
      // ?pay убираем из адреса сразу: payDialog берёт адрес возврата из ЮKassa из location,
      // и с ?pay окно оплаты открылось бы снова после оплаты
      const q = new URLSearchParams(location.search);
      q.delete('pay');
      history.replaceState(history.state, '', location.pathname + (q.toString() ? '?' + q : '') + location.hash);
      payDialog({ product: pay });
    }
  };
  // /me уже спрашивали в этой вкладке — рисуем кабинет сразу, свежий аккаунт подтягиваем в фоне
  // и перерисовываем, только если он изменился (и человек ничего не вводит)
  if (accountFresh()) {
    const before = JSON.stringify(account());
    start();
    await refreshAccount();
    if (!signedIn()) return toLogin();
    const typing = document.activeElement?.closest?.('input, textarea, select');
    if (JSON.stringify(account()) !== before && !document.querySelector('.modal') && !typing) route();
    return;
  }
  await refreshAccount();
  if (!signedIn()) return toLogin();
  start();
}

main();
