import { currentDesign } from './theme.js';

// Реальное приложение, тот же app.js. Оболочка удерживает внутренние ссылки
// на student.html, чтобы сравнение дизайна не требовало изменения корня проекта.
document.addEventListener('click', e => {
  const a = e.target.closest('#app a');
  if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || a.target === '_blank') return;
  const href = a.getAttribute('href'), u = new URL(a.href);
  if (href.startsWith('#/')) { e.preventDefault(); location.hash = href; return; }
  if (u.origin !== location.origin || u.pathname !== '/') return;
  e.preventDefault();
  u.pathname = new URL('student.html', import.meta.url).pathname;
  u.searchParams.set('design', currentDesign);
  location.href = u;
});

const app = document.getElementById('app');
let pendingVariant = new URLSearchParams(location.search).get('preview-action') === 'variant';
const nav = document.createElement('nav'); nav.className = 'student-nav'; nav.setAttribute('aria-label', 'Разделы тренажёра');
nav.innerHTML = '<button data-route="tasks" aria-pressed="true">Задания</button><button data-route="errors" aria-pressed="false">Ошибки</button><button data-route="progress" aria-pressed="false">Прогресс</button>';
nav.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
  if (b.dataset.route === 'errors') {
    const errors = app.querySelector('#errs');
    if (errors) errors.click();
    else { import('../lib.js').then(({ toast }) => toast('Пока нет ошибок для повторения')); }
  } else location.hash = b.dataset.route === 'progress' ? '#/me' : '#/';
}));
document.body.append(nav);
function updateNav() {
  // На стенде сравниваем палитру направления, а не брендовый цвет набора.
  document.documentElement.style.removeProperty('--accent');
  nav.hidden = currentDesign !== 'c' || !!app.querySelector('.card, .finish, .landing') || location.hash.includes('/library');
  nav.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.route === (location.hash === '#/me' ? 'progress' : 'tasks'))));
  if (pendingVariant && app.querySelector('#variant')) {
    pendingVariant = false;
    const url = new URL(location.href); url.searchParams.delete('preview-action'); history.replaceState(history.state, '', url);
    app.querySelector('#variant').click();
  }
}
new MutationObserver(updateNav).observe(app, { childList: true });
document.addEventListener('designchange', updateNav);
updateNav();
