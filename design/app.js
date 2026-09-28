import { renderCard, esc, text, plural } from '../lib.js';
import { currentDesign } from './theme.js';

const icon = (path, name = '') => `<svg viewBox="0 0 24 24" ${name ? `role="img" aria-label="${name}"` : 'aria-hidden="true"'}>${path}</svg>`;
const icons = {
  play: icon('<path d="m9 5 11 7-11 7z"/>'),
  book: icon('<path d="M4 4h6a3 3 0 0 1 3 3v14a4 4 0 0 0-4-3H4zM20 4h-4a3 3 0 0 0-3 3v14a4 4 0 0 1 4-3h3z"/>'),
  star: icon('<path d="m12 3 3 6 6 1-4 5 1 6-6-3-6 3 1-6-4-5 6-1z"/>'),
  grid: icon('<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/>'),
  errors: icon('<path d="M9 4 3 10l6 6M3 10h11a7 7 0 0 1 7 7v3"/>'),
  chart: icon('<path d="M4 4v16h17M8 15v-4M13 15V7M18 15v-7"/>'),
  back: icon('<path d="m14 5-7 7 7 7"/>'),
};
const screen = (id, n, title, content, controls = '') => `<section class="design-section" id="${id}">
  <header class="screen-caption"><div><span>${n} / 04</span><h2>${title}</h2></div>${controls}</header>
  <div class="design-screen" data-screen="${id}"><div class="wrap screen-wrap">${content}</div></div></section>`;
const nav = active => `<nav class="student-nav" aria-label="Разделы тренажёра">
  ${[['tasks', icons.grid, 'Задания'], ['errors', icons.errors, 'Ошибки'], ['progress', icons.chart, 'Прогресс']].map(([id, svg, label]) => `<button type="button" data-view="${id}" aria-pressed="${id === active}">${svg}<span>${label}</span></button>`).join('')}
</nav>`;
const status = (acc) => acc === null ? ['new', '—', 'Новое'] : acc >= 80 ? ['ok', '✓', 'Уверенно'] : acc >= 60 ? ['mid', '≈', 'Закрепить'] : ['bad', '!', 'Повторить'];
const sampleAccuracy = [92, 83, 67, 100, 42, 75, 89, 50, null, null, null, null];
const shortTitle = t => t.title.replace(/^\d+\.\s*/, '');
let math, physics, library;

function tile(t, i) {
  const accuracy = sampleAccuracy[i] ?? null;
  const [tone, symbol, label] = status(accuracy);
  return `<a class="task-tile ${tone}" data-topic="${esc(t.id)}" href="student.html?p=ege-math&design=${currentDesign}#/topic/${encodeURIComponent(t.id)}" aria-label="Задание ${t.n}. ${esc(shortTitle(t))}. ${label}${accuracy === null ? '' : `, точность ${accuracy}%`}">
    <b>${t.n}</b><em>${esc(shortTitle(t))}</em><span class="tile-accuracy"><i aria-hidden="true">${symbol}</i>${accuracy === null ? label : accuracy + '%'}</span></a>`;
}

function renderHome() {
  const topics = math.topics.filter(t => t.n && t.section === 'Часть 1');
  return `<header class="top home-top"><span class="avatar" aria-hidden="true">м.</span><div><div class="brand-by">ЕГЭ · профильный уровень</div><div class="brand-title">Математика</div></div><span class="streak-badge" aria-label="Серия: 5 дней">${icons.star}<b>5 дней</b></span></header>
    <div class="home-greeting"><span class="eyebrow">Понемногу — каждый день</span><h1>Ещё один шаг<br>к твоим 100.</h1></div>
    <section class="goal-card" aria-label="Цель дня: 6 из 10 карточек"><svg class="ring" viewBox="0 0 92 92" aria-hidden="true"><circle cx="46" cy="46" r="38" class="ring-bg"/><circle cx="46" cy="46" r="38" class="ring-fg" stroke-dasharray="143.3 238.8" transform="rotate(-90 46 46)"/><text x="46" y="53" text-anchor="middle">6/10</text></svg><div><b>Ты уже в ритме</b><span>Ещё 4 карточки — цель дня выполнена</span></div></section>
    <button class="btn cta big" id="go">${icons.play}Продолжить · 4 мин</button>
    <div class="home-actions"><button class="btn" id="variant">Пробный вариант ${icons.chevron || '↗'}</button><button class="btn" id="errs">Ошибки <span class="count-pill">3</span></button></div>
    <section class="topics task-section" data-view-panel="tasks"><div class="section-heading"><h2>Задания</h2><span class="muted">Часть 1</span></div><div class="task-grid">${topics.map(tile).join('')}</div><p class="legend"><span class="legend-item ok">✓ Уверенно</span><span class="legend-item mid">≈ Закрепить</span><span class="legend-item bad">! Повторить</span></p></section>
    <section class="topics" data-view-panel="errors" hidden><h2>Здесь можно прибавить</h2><p class="muted">Начни с заданий, в которых пока больше ошибок.</p><div class="task-grid">${topics.filter((_, i) => [4, 5, 7].includes(i)).map(t => tile(t, topics.indexOf(t))).join('')}</div></section>
    <section class="topics" data-view-panel="progress" hidden><h2>Твой прогресс</h2><div class="progress-overview"><div><b>5</b><span>дней подряд</span></div><div><b>75%</b><span>точность</span></div><div><b>8</b><span>заданий начато</span></div></div><p class="muted">Каждое короткое занятие помогает удержать знания.</p></section>
    ${nav('tasks')}`;
}

function cardHeader(n, title, subject) {
  return `<header class="top session-top"><a class="back" href="#home" aria-label="К набору">${icons.back}</a><div><div class="brand-by">${subject}</div><div class="brand-title">Задание ${n}</div></div><span class="session-counter">3 / 10</span></header><div class="progress session-progress" aria-label="Выполнено 2 из 10"><i></i></div><div class="card-topic"><span class="num-badge">${n}</span><span>${esc(title)}</span></div>`;
}

function renderTrainer() {
  const subjects = ['Математика', 'Физика', 'Русский язык', 'Биология'];
  const packs = subjects.map(s => library.find(p => p.subject === s && p.id === ({'Математика':'ege-math','Физика':'ege-phys','Русский язык':'ege-rus','Биология':'ege-bio'})[s])).filter(Boolean);
  return `<header class="top"><span class="avatar" aria-hidden="true">м.</span><div class="brand-title">Тренажёр</div><span class="eyebrow">Твой темп</span></header>
    <div class="trainer-intro"><span class="eyebrow">Между уроками есть время</span><h1>Что сегодня<br>потренируем?</h1><p class="muted">Выбери предмет. Начнём с десяти минут.</p></div>
    <div class="subject-list">${packs.map((p, i) => `<a class="topic subject-card" href="student.html?p=${encodeURIComponent(p.id)}&design=${currentDesign}"><span class="subject-symbol" aria-hidden="true">${['x²', 'F', 'Аа', 'ДНК'][i]}</span><span class="topic-title"><span class="lib-exam">ЕГЭ</span><b>${esc(p.subject)}</b><small>${p.topics} заданий · ${plural(p.cards, 'карточка', 'карточки', 'карточек')}</small></span><span class="subject-arrow" aria-hidden="true">↗</span></a>`).join('')}</div>
    <section class="panel tutor-code"><div>${icons.book}<b>Занимаешься с репетитором?</b></div><p class="muted">Введи код, чтобы открыть его тренажёр.</p><label for="code">Код от репетитора</label><div class="row"><input id="code" placeholder="например, k7m2p9xq" autocomplete="off" autocapitalize="off"><button class="btn primary" id="join">Открыть</button></div><p class="hint" id="code-feedback" role="status" hidden></p></section>`;
}

function typeset(root) {
  // Степени и простые числовые дроби: меняется только разметка, не данные набора.
  root.querySelectorAll('.f, .fblock, .explain').forEach(f => {
    const walker = document.createTreeWalker(f, NodeFilter.SHOW_TEXT), nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      if (node.parentElement.closest('.fraction, sup') || !/\b\d+\/\d+\b|\^\{[^}]+\}/.test(node.textContent)) continue;
      const holder = document.createElement('span');
      holder.innerHTML = esc(node.textContent).replace(/\^\{([^}]+)\}/g, '<sup>$1</sup>')
        .replace(/\b(\d+)\/(\d+)\b/g, (_, a, b) => `<span class="fraction" role="math" aria-label="${a} разделить на ${b}"><span aria-hidden="true">${a}</span><span aria-hidden="true">${b}</span></span>`);
      node.replaceWith(...holder.childNodes);
    }
  });
}

function numberCard(state = 'ok') {
  const card = math.cards.find(c => c.id === 'ep07-exp-base-1') || math.cards.find(c => c.k === 'num');
  const root = document.getElementById('number-card');
  root.classList.remove('answered');
  renderCard(card, root, score => {
    const check = root.querySelector('.num-row');
    check.insertAdjacentHTML('beforeend', `<span class="answer-status ${score === 1 ? 'ok' : 'bad'}" role="status">${score === 1 ? '✓ Верно' : '! Есть ошибка'}</span>`);
    root.querySelector('.explain').setAttribute('aria-label', 'Разбор решения');
    typeset(root);
    document.querySelector('#number .sample-next').hidden = false;
  }, { imgRoot: '../', aiEnabled: false });
  const input = root.querySelector('.num-input');
  input.placeholder = 'Число'; input.setAttribute('aria-label', 'Твой ответ');
  root.querySelector('.hint').hidden = true;
  typeset(root);
  document.querySelector('#number .sample-next').hidden = true;
  if (state !== 'idle') {
    input.value = state === 'ok' ? card.a : '9';
    root.querySelector('.check').click();
    root.querySelector('.hint').hidden = state === 'ok';
  }
  document.querySelectorAll('[data-answer-state]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.answerState === state)));
}

function matchCard(state = 'idle') {
  const card = physics.cards.find(c => c.id === 'p-ph-ege-06-change-float-9d05dd1465') || physics.cards.find(c => c.k === 'match');
  const root = document.getElementById('match-card');
  root.classList.remove('answered');
  renderCard(card, root, score => {
    root.querySelectorAll('.match-choice').forEach(b => b.disabled = true);
    const label = score === 1 ? '✓ Все пары верны' : score > 0 ? '≈ Часть пар верна' : '! Есть ошибки';
    root.querySelector('.match-left').insertAdjacentHTML('afterend', `<p class="answer-status ${score === 1 ? 'ok' : score ? 'mid' : 'bad'}" role="status">${label}</p>`);
  }, { imgRoot: '../', aiEnabled: false });
  const check = root.querySelector('.check');
  check.hidden = true;
  root.querySelectorAll('.match-row').forEach((oldRow, i) => {
    // Адаптер только стенда: оригинальный select и проверка из renderCard
    // остаются источником значения; кнопки показывают будущий вид ответа.
    const row = document.createElement('div');
    row.className = 'match-row'; row.append(...oldRow.childNodes); oldRow.replaceWith(row);
    const select = row.querySelector('select'); select.hidden = true;
    row.setAttribute('role', 'group'); row.setAttribute('aria-label', `${card.o.left[i].id}. ${card.o.left[i].t}`);
    const choices = document.createElement('div'); choices.className = 'match-choices';
    choices.innerHTML = card.o.right.map(r => `<button class="match-choice" type="button" data-value="${esc(r.id)}" aria-label="${esc(r.id)}: ${esc(r.t)}" aria-pressed="false">${esc(r.id)}</button>`).join('');
    row.append(choices);
    choices.querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
      select.value = b.dataset.value;
      choices.querySelectorAll('button').forEach(x => { x.classList.toggle('picked', x === b); x.setAttribute('aria-pressed', String(x === b)); });
      check.hidden = [...root.querySelectorAll('select')].some(s => !s.value);
    }));
  });
  if (state !== 'idle') {
    root.querySelectorAll('.match-row').forEach((row, i) => {
      const correct = card.a[card.o.left[i].id];
      const value = state === 'ok' || (state === 'mid' && i === 0) ? correct : card.o.right.find(r => r.id !== correct).id;
      [...row.querySelectorAll('.match-choice')].find(b => b.dataset.value === value).click();
    });
    check.click();
  }
  document.querySelectorAll('[data-match-state]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.matchState === state)));
}

function setHomeView(view) {
  const home = document.getElementById('home');
  home.querySelectorAll('[data-view-panel]').forEach(p => p.hidden = p.dataset.viewPanel !== view);
  home.querySelectorAll('[data-view]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === view)));
}

async function init() {
  [math, physics, library] = await Promise.all(['ege-math.json', 'ege-phys.json', 'index.json'].map(async file => {
    const response = await fetch(new URL(`../packs/${file}`, import.meta.url));
    if (!response.ok) throw new Error('Не удалось загрузить наборы');
    return response.json();
  }));
  document.getElementById('screens').innerHTML =
    screen('home', '01', 'Главная набора', renderHome()) +
    screen('number', '02', 'Ответ и разбор', `${cardHeader(7, 'Уравнения', 'Математика · ЕГЭ')}<article class="card" id="number-card"></article><button class="btn primary big sample-next" type="button">Попробовать самому →</button>`, `<div class="state-picker" role="group" aria-label="Состояние числового ответа">${[['idle','Ввод'], ['ok','Верно'], ['bad','Ошибка']].map(([id, name]) => `<button data-answer-state="${id}" aria-pressed="false">${name}</button>`).join('')}</div>`) +
    screen('matching', '03', 'Найти соответствие', `${cardHeader(6, 'Как изменятся величины', 'Физика · ЕГЭ')}<article class="card" id="match-card"></article>`, `<div class="state-picker" role="group" aria-label="Состояние соответствия">${[['idle','Ввод'], ['ok','Верно'], ['mid','Частично'], ['bad','Ошибка']].map(([id, name]) => `<button data-match-state="${id}" aria-pressed="false">${name}</button>`).join('')}</div>`) +
    screen('trainer', '04', 'Выбор предмета', renderTrainer());
  numberCard(); matchCard();
  document.querySelectorAll('[data-answer-state]').forEach(b => b.addEventListener('click', () => numberCard(b.dataset.answerState)));
  document.querySelectorAll('[data-match-state]').forEach(b => b.addEventListener('click', () => matchCard(b.dataset.matchState)));
  document.querySelector('.sample-next').addEventListener('click', () => numberCard('idle'));
  document.getElementById('go').addEventListener('click', () => { numberCard('idle'); document.getElementById('number').scrollIntoView({ behavior: 'smooth' }); });
  document.getElementById('variant').addEventListener('click', () => { location.href = `student.html?p=ege-math&design=${currentDesign}&preview-action=variant`; });
  document.getElementById('errs').addEventListener('click', () => setHomeView('errors'));
  document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => setHomeView(b.dataset.view)));
  const panel = document.querySelector('#home .screen-wrap');
  let start;
  panel.addEventListener('pointerdown', e => { start = e.pointerType === 'touch' && !e.target.closest('a, button, input') ? [e.clientX, e.clientY] : null; });
  panel.addEventListener('pointerup', e => {
    if (!start || currentDesign !== 'c') return;
    const dx = e.clientX - start[0], dy = e.clientY - start[1]; start = null;
    if (Math.abs(dx) < 70 || Math.abs(dy) > 40) return;
    const views = ['tasks', 'errors', 'progress'];
    const at = views.indexOf(panel.querySelector('[data-view][aria-pressed="true"]').dataset.view);
    setHomeView(views[Math.max(0, Math.min(2, at + (dx < 0 ? 1 : -1)))]);
  });
  const join = () => {
    const code = document.getElementById('code').value.trim();
    const feedback = document.getElementById('code-feedback');
    if (!/^[a-z0-9]{6,12}$/i.test(code)) { feedback.textContent = 'Проверь код: нужны латинские буквы и цифры.'; feedback.hidden = false; return; }
    location.href = `student.html?t=${encodeURIComponent(code)}&design=${currentDesign}`;
  };
  document.getElementById('join').addEventListener('click', join);
  document.getElementById('code').addEventListener('keydown', e => { if (e.key === 'Enter') join(); });
  document.addEventListener('designchange', () => document.querySelectorAll('.design-screen a[href*="student.html"]').forEach(a => {
    const u = new URL(a.href); u.searchParams.set('design', currentDesign); a.href = u;
  }));
  const states = [['normal', 'Обычное', ''], ['pressed', 'Нажатое', 'demo-pressed'], ['ok','✓ Верно','ok'], ['bad','! Неверно','bad'], ['mid','≈ Частично','mid']];
  document.getElementById('state-examples').innerHTML = states.map(([id, label, cls]) => `<div class="state-example"><span>${label}</span><button class="btn ${id === 'normal' || id === 'pressed' ? 'primary' : ''} ${cls}" type="button">Проверить</button><label class="sr-only" for="field-${id}">${label}</label><input class="num-input ${cls}" id="field-${id}" value="12" readonly></div>`).join('');
  document.documentElement.dataset.ready = 'true';
}
init().catch(err => {
  document.getElementById('screens').innerHTML = `<p class="panel" role="alert">${esc(err.message)}. <a href="">Попробовать ещё раз</a></p>`;
});
