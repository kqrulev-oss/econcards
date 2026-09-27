// Личный кабинет. Новый аккаунт сначала выбирает, кто он, — дальше у каждой
// роли свой раздел: репетитор (ученики и тариф), ученик (серия, тренажёры,
// библиотека), родитель (дети и оплата). Ролей у одного аккаунта может быть несколько.
import { store, api, esc, day, plural, toast, loadLibrary } from '../lib.js';
import { signedIn, account, logout, addRole, finishRedirectLogin, finishPayment, refreshAccount,
  loginDialog, payDialog, planOf, daysLeft, dateRu } from '../account.js';
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

function shell(tab, body) {
  const a = account();
  const tabs = [...rolesOf(a).map(r => [r, ROLES[r].tab]), ['settings', 'Настройки']];
  $app.innerHTML = `
    <header class="cab-top">
      <a class="ld-logo" href="../?about"><span class="ld-mark">М</span><span class="cab-logo-text">Между уроками</span></a>
      <a class="cab-me" href="#settings" aria-label="Настройки аккаунта"><span class="avatar">${initials(a)}</span><span class="cab-me-name">${esc(a?.name || a?.email || 'Аккаунт')}</span></a>
    </header>
    <nav class="cab-tabs" aria-label="Разделы кабинета">${tabs.map(([id, t]) =>
      `<a href="#${id}" class="${tab === id ? 'on' : ''}" ${tab === id ? 'aria-current="page"' : ''}>${ICON[id]}<span>${t}</span></a>`).join('')}
      ${rolesOf(a).length < 3 ? '<a href="#role" class="cab-add" aria-label="Добавить роль">+</a>' : ''}</nav>
    <div id="cab-body">${body}</div>`;
  return $app.querySelector('#cab-body');
}

// Плашка тарифа: пробный / оплачен / бесплатный — и кнопка оплаты
function planPanel(product, { name, free, via }) {
  const st = planOf(product), now = Date.now();
  let tone = 'free', text = free, btn = 'Оплатить';
  if ((st.paidUntil || 0) > now) { tone = 'ok'; text = `${name} оплачен до ${dateRu(st.paidUntil)}`; btn = 'Продлить'; }
  else if (via && st.via > now) { tone = 'ok'; text = via; btn = ''; }
  else if ((st.trialEnd || 0) > now) { tone = 'trial'; text = `Пробный период: ${plural(daysLeft(st.trialEnd), 'день', 'дня', 'дней')} без ограничений`; }
  return `<div class="panel plan ${tone} cab-plan"><span>${text}</span>${btn ? `<button class="btn small primary" data-pay="${product}">${btn}</button>` : ''}</div>`;
}
const bindPay = box => box.querySelectorAll('[data-pay]').forEach(b => { b.onclick = () => payDialog({ product: b.dataset.pay }); });

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
    ${first ? `<label class="field cab-name"><span>Как вас зовут</span><input id="name" maxlength="80" autocomplete="name" value="${esc(a?.name || '')}" placeholder="Имя и фамилия"></label>` : ''}
    <button class="btn primary big cab-go" id="go">Продолжить</button>`;
  const box = first ? ($app.innerHTML = `<header class="cab-top"><a class="ld-logo" href="../?about"><span class="ld-mark">М</span><span class="cab-logo-text">Между уроками</span></a>
    <button class="btn small" id="out">Выйти</button></header><div id="cab-body">${body}</div>`, $app) : shell('role', body);
  box.querySelector('#out')?.addEventListener('click', async () => { await logout(); location.href = '../login.html'; });
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

async function viewTutor() {
  const box = shell('tutor', '<p class="loading">Загружаю учеников…</p>');
  let studio;
  try { studio = await api('/me/studio'); } catch (err) { box.innerHTML = `<section class="panel">${esc(err.message)}</section>`; return; }
  const packs = Object.values(studio.packs || {}).filter(p => !studio.deleted?.[p.id]).sort((x, y) => y.edited - x.edited);
  const withStudents = await Promise.all(packs.map(async p => {
    if (!p.published) return { p, students: [] };
    try { return { p, students: (await api(`/packs/${encodeURIComponent(p.id)}/progress`)).students }; }
    catch { return { p, students: [] }; }
  }));
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

  const studio$ = '../studio/';
  box.innerHTML = `
    ${planPanel('tutor', { name: 'Тариф репетитора', free: 'Бесплатный тариф: 1 опубликованный тренажёр и до 3 учеников' })}
    <section class="hero-stats cab-stats">
      <div><b>${all.length}</b><span>${words(all.length, 'ученик', 'ученика', 'учеников')}</span></div>
      <div><b>${active.length}</b><span>занимались за неделю</span></div>
      <div><b>${weekCards ? Math.round(weekOk / weekCards * 100) + '%' : '—'}</b><span>точность за неделю</span></div>
    </section>
    ${packs.length ? '' : `<section class="panel cab-empty">
      <h2>Первый тренажёр — за 15 минут</h2>
      <p>Вставьте свои материалы или возьмите карточки из библиотеки ЕГЭ, опубликуйте и отправьте ученикам ссылку. Здесь появится, кто занимается и где ошибки.</p>
      <a class="btn primary big" href="${studio$}#/new">Создать тренажёр</a></section>`}
    ${all.length ? `<section class="panel">
      <h2>Требуют внимания</h2>
      ${attention.length ? `<ul class="cab-list">${attention.map(({ s, why, tone }) => `
        <li><a href="${studio$}#/p/${esc(s.pack.id)}/students"><span class="avatar small">${esc(s.name.slice(0, 2).toUpperCase())}</span>
          <span class="cab-li-main"><b>${esc(s.name)}</b><small>${esc(s.pack.title)}</small></span><span class="pill ${tone}">${esc(why)}</span></a></li>`).join('')}</ul>`
        : '<p class="muted">Все занимаются — никого не нужно догонять.</p>'}
    </section>` : packs.length ? `<section class="panel"><h2>Ученики</h2><p class="muted">Пока никто не занимался. Отправьте ученикам ссылку из вкладки тренажёра «Ссылка» — как только ученик ответит на первые карточки, он появится здесь.</p></section>` : ''}
    ${packs.length ? `<section class="panel">
      <div class="cab-head"><h2>Мои тренажёры</h2><a class="btn small primary" href="${studio$}#/new">+ Создать</a></div>
      <ul class="cab-list">${withStudents.map(({ p, students }) => `
        <li><a href="${studio$}#/p/${esc(p.id)}/${students.length ? 'students' : 'cards'}"><span class="dot" style="background:${esc(p.color || '#5B3DF5')}"></span>
          <span class="cab-li-main"><b>${esc(p.title)}</b><small>${plural(p.cards?.length || 0, 'карточка', 'карточки', 'карточек')} · ${p.published ? (p.published >= p.edited ? 'опубликован' : 'есть правки') : 'черновик'}</small></span>
          <span class="pill">${plural(students.length, 'ученик', 'ученика', 'учеников')}</span></a></li>`).join('')}</ul>
    </section>` : ''}
    <section class="panel cab-tip">
      <h2>Родителям</h2>
      <p class="muted">Отчёт родителю — в тренажёре: Ученики → ученик → «Отчёт». Или дайте родителю код: он увидит прогресс ребёнка в своём кабинете.</p>
      <a class="btn" href="${studio$}">Открыть студию</a>
    </section>`;
  bindPay(box);
}

// ---------- ученик ----------

async function packTitles(refs) {
  const titles = Object.fromEntries(store.get('zd-recent', []).map(r => [r.ref, r.title]));
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
  const { titles, lib } = await packTitles(refs);
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
        <p class="muted small-note">Родитель входит на ${esc(new URL('../login.html', location.href).host)} как «Родитель» и вводит код. Действует сутки, подходит один раз.</p>`;
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
      <label class="field"><span>Имя</span><input id="name" maxlength="80" autocomplete="name" value="${esc(a?.name || '')}"></label>
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
  box.querySelector('#out').onclick = async () => { await logout(); location.href = '../login.html'; };
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
  if (r !== tab) history.replaceState(null, '', location.pathname + location.search + '#' + r);
  if (ROLES[r]) store.set('zd-cab', r);
  window.scrollTo(0, 0);
  ({ tutor: viewTutor, student: viewStudent, parent: viewParent, settings: viewSettings })[r]();
}

async function main() {
  await finishRedirectLogin();
  if (!signedIn()) {
    // Ссылка вида cabinet/#parent — на странице входа сразу открыта нужная вкладка
    const want = location.hash.slice(1);
    location.replace(`../login.html?${ROLES[want] ? `role=${want}&` : ''}next=${encodeURIComponent('cabinet/' + location.hash)}`);
    return;
  }
  await finishPayment();
  if (!await refreshAccount() && !signedIn()) { location.replace('../login.html?next=cabinet/'); return; }
  window.addEventListener('hashchange', route);
  route();
}

main();
