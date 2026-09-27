// Страница входа: одна для репетитора, ученика и родителя. После входа —
// туда, откуда пришли (?next=), иначе в личный кабинет: новый аккаунт там
// выбирает, кто он, а выбранная здесь вкладка подсказывает ответ.
import { store, esc } from './lib.js';
import { signedIn, account, loginDialog, logout, addRole, finishRedirectLogin, refreshAccount } from './account.js';

const $app = document.getElementById('app');
const params = new URLSearchParams(location.search);

const ROLES = {
  tutor: {
    tab: 'Репетитор', title: 'Студия репетитора',
    lead: 'Тренажёры, ученики и отчёты родителям — в одном аккаунте. Первые 14 дней всё бесплатно.',
    points: ['Тренажёр из своих материалов за 15 минут', 'Кто занимался и где ошибки', 'Отчёт родителям в один клик'],
  },
  student: {
    tab: 'Ученик', title: 'Тренажёр ученика',
    lead: 'Серия, очки и прогресс сохраняются в аккаунте — занимайся с телефона и компьютера.',
    points: ['10 минут в день', 'Карточки возвращаются, когда начинаешь забывать', 'Все задания ЕГЭ по прототипам'],
  },
  parent: {
    tab: 'Родитель', title: 'Кабинет родителя',
    lead: 'Видно, как ребёнок занимается между уроками: дни, точность по неделям и темы, которые стоит подтянуть.',
    points: ['Без звонков репетитору', 'Сводка обновляется после каждого занятия', 'Оплата доступа для ребёнка'],
  },
};

let role = ROLES[params.get('role')] ? params.get('role') : 'tutor';
// Вернуться можно только внутрь сайта
const safeNext = n => (n && !/^[a-z]+:|^\/\/|\.\./i.test(n) ? n : null);
const asked = () => safeNext(params.get('next')) || safeNext(sessionStorage.getItem('zd-login-next'));
if (safeNext(params.get('next'))) sessionStorage.setItem('zd-login-next', params.get('next'));
// Пришли из студии или тренажёра — роль понятна, возвращаем туда. Иначе — в кабинет
async function go() {
  const next = asked();
  sessionStorage.removeItem('zd-login-next');
  if (next && !next.startsWith('cabinet/')) { await addRole(role); location.href = next; return; }
  location.href = `cabinet/?role=${role}${next?.includes('#') ? next.slice(next.indexOf('#')) : ''}`;
}

function hero() {
  const r = ROLES[role];
  return `
    <p class="ld-kicker">${esc(r.title)}</p>
    <h1>С возвращением между уроками</h1>
    <p class="login-lead">${esc(r.lead)}</p>
    <ul class="login-points">${r.points.map(p => `<li>${esc(p)}</li>`).join('')}</ul>
    <figure class="login-art"><img src="img/hero-student-768.webp" width="768" height="512" alt="Ученица на диване решает карточки на телефоне"></figure>`;
}

function tabs() {
  return `<div class="role-tabs" role="tablist">${Object.entries(ROLES).map(([id, r]) =>
    `<button role="tab" aria-selected="${id === role}" class="${id === role ? 'on' : ''}" data-role="${id}">${r.tab}</button>`).join('')}</div>`;
}

function viewSignedIn() {
  const a = account();
  $app.innerHTML = `
    ${brand()}
    <section class="login-grid">
      <div class="login-hero">${hero()}</div>
      <div class="login-card">
        <div class="login-me"><span class="avatar">${esc((a?.name || a?.email || '?').slice(0, 2).toUpperCase())}</span>
          <div><small>Вы вошли</small><b>${esc(a?.name || a?.email || 'Аккаунт')}</b></div></div>
        <div class="login-go">
          <a class="btn primary big" href="cabinet/">Личный кабинет</a>
          <a class="btn big" href="studio/">Студия репетитора</a>
          <a class="btn big" href="${store.get('zd-recent', []).length ? './' : './#/library'}">Тренажёр ученика</a>
        </div>
        <button class="link-btn" id="logout">Выйти из аккаунта</button>
      </div>
    </section>`;
  $app.querySelector('#logout').onclick = async () => { await logout(); render(); };
}

const brand = () => `<header class="login-top"><a class="ld-logo" href="./?about"><span class="ld-mark">М</span>Между уроками</a>
  <a class="btn small" href="./?about">О сервисе</a></header>`;

function render(resume = null) {
  if (signedIn()) return viewSignedIn();
  $app.innerHTML = `
    ${brand()}
    <section class="login-grid">
      <div class="login-hero">${hero()}</div>
      <div class="login-card">
        <h2 class="login-title">Вход</h2>
        ${tabs()}
        <div id="login-box"></div>
        <p class="muted small-note">Первый раз? Просто войдите — аккаунт создастся сам.</p>
      </div>
    </section>`;
  $app.querySelectorAll('[data-role]').forEach(b => b.onclick = () => {
    role = b.dataset.role;
    $app.querySelector('.login-hero').innerHTML = hero();
    $app.querySelectorAll('[data-role]').forEach(x => { x.classList.toggle('on', x === b); x.setAttribute('aria-selected', x === b); });
  });
  loginDialog({
    into: $app.querySelector('#login-box'),
    role: () => role,
    resume,
    onDone: go,
  });
}

async function main() {
  // Вернулись из Telegram (страница могла перезагрузиться) — продолжаем ждать здесь же
  const pend = store.get('zd-tg-pending', null);
  if (pend && !signedIn() && Date.now() - pend.at < 600e3 && !/^#login/.test(location.hash)) {
    if (ROLES[pend.role]) role = pend.role;
    return render(pend);
  }
  // Вернулись от Яндекса/VK/Google — завершаем вход и уходим дальше
  const done = await finishRedirectLogin();
  if (done) {
    if (done.role && ROLES[done.role]) role = done.role;
    return go();
  }
  if (signedIn()) await refreshAccount();
  render();
}

main();
