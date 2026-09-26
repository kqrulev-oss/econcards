// Приложение ученика: ежедневное занятие по интервальному повторению,
// темы с теорией, работа над ошибками и отправка прогресса репетитору.
import { store, api, apiBase, loadPack, loadLibrary, renderCard, esc, text, day, uid, plural, el, toast } from './lib.js';
import { renderLanding } from './landing.js';

const $app = document.getElementById('app');
const INTERVALS = [0, 1, 3, 7, 14, 30, 60]; // дни до повтора по «коробкам»
const SESSION = 20;
const NEW_DEFAULT = 10;

let ref = null;   // 'econ-olymp' или 't:<id>' для набора репетитора
let pack = null;
let prog = null;
let topicsById = {};

// ---------- прогресс ----------

const progKey = () => 'zd-prog:' + ref;
const save = () => store.set(progKey(), prog);

function loadProg() {
  prog = Object.assign({ cards: {}, log: {}, errs: [], sid: uid(10), name: '', synced: 0 }, store.get(progKey(), {}));
  save();
}

function grade(card, score) {
  const t = day();
  const isNew = !prog.cards[card.id];
  const s = prog.cards[card.id] || { b: 0, n: 0, w: 0 };
  s.n++;
  s.last = t;
  if (score === 1) { s.b = Math.min(s.b + 1, INTERVALS.length - 1); s.due = t + INTERVALS[s.b]; }
  else if (score > 0) { s.due = t + 1; }
  else {
    s.w++; s.b = 0; s.due = t + 1;
    prog.errs = [card.id, ...prog.errs.filter(id => id !== card.id)].slice(0, 30);
  }
  if (score === 1 && s.b >= 3) prog.errs = prog.errs.filter(id => id !== card.id);
  prog.cards[card.id] = s;
  const l = prog.log[t] || { d: 0, ok: 0, n: 0 };
  l.d++;
  l.ok += score;
  if (isNew) l.n++;
  prog.log[t] = l;
  save();
}

function streak() {
  let t = day(), n = 0;
  if (!prog.log[t]?.d) t--;
  while (prog.log[t]?.d) { n++; t--; }
  return n;
}

function topicStats(tid) {
  const cards = pack.cards.filter(c => c.t === tid);
  let started = 0, mastered = 0, seen = 0, wrong = 0;
  for (const c of cards) {
    const s = prog.cards[c.id];
    if (!s) continue;
    started++;
    if (s.b >= 3) mastered++;
    seen += s.n;
    wrong += s.w;
  }
  return { total: cards.length, started, mastered, acc: seen ? 1 - wrong / seen : null };
}

function dueCards(pool) {
  const t = day();
  return pool.filter(c => prog.cards[c.id] && prog.cards[c.id].due <= t)
    .sort((a, b) => prog.cards[a.id].due - prog.cards[b.id].due || prog.cards[a.id].b - prog.cards[b.id].b);
}

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function buildQueue(mode, tid) {
  const pool = tid ? pack.cards.filter(c => c.t === tid) : pack.cards;
  if (mode === 'errors') {
    const byId = Object.fromEntries(pack.cards.map(c => [c.id, c]));
    return prog.errs.map(id => byId[id]).filter(c => c && (!tid || c.t === tid)).slice(0, SESSION);
  }
  const due = dueCards(pool).slice(0, SESSION);
  const newToday = prog.log[day()]?.n || 0;
  const newLimit = tid ? 10 : Math.max(0, (pack.daily || NEW_DEFAULT) - newToday);
  const fresh = pool.filter(c => !prog.cards[c.id]);
  // В теме — по порядку (от простого к сложному), в общем занятии — вперемешку
  const picked = (tid ? fresh : shuffle(fresh.slice())).slice(0, Math.min(newLimit, SESSION - due.length));
  return [...due, ...picked];
}

// ---------- отчёт репетитору ----------

function summary() {
  const t = day();
  const week = { d: 0, ok: 0, days: 0 };
  for (let i = 0; i < 7; i++) {
    const l = prog.log[t - i];
    if (l?.d) { week.d += l.d; week.ok += l.ok; week.days++; }
  }
  const topics = {};
  for (const tp of pack.topics) {
    const s = topicStats(tp.id);
    if (s.started) topics[tp.id] = { s: s.started, m: s.mastered, acc: s.acc === null ? null : Math.round(s.acc * 100) };
  }
  const states = Object.values(prog.cards);
  return {
    last: Date.now(), streak: streak(), today: prog.log[t] || { d: 0, ok: 0 }, week,
    total: pack.cards.length, started: states.length, mastered: states.filter(s => s.b >= 3).length,
    topics, errs: prog.errs.slice(0, 15),
  };
}

async function sync(force) {
  if (!ref.startsWith('t:') || !apiBase() || !prog.name) return;
  if (!force && Date.now() - prog.synced < 3600e3) return;
  try {
    await api(`/packs/${encodeURIComponent(ref.slice(2))}/progress`, {
      method: 'POST', body: { sid: prog.sid, name: prog.name, stats: summary() },
    });
    prog.synced = Date.now();
    save();
  } catch { /* офлайн — отправим в следующий раз */ }
}

// ---------- экраны ----------

function brandHeader(sub) {
  const who = pack.tutor ? `<div class="brand-by">${esc(pack.tutor)}</div>` : '';
  return `<header class="top">
    <div><div class="brand-title">${esc(pack.title)}</div>${who}</div>
    ${sub || ''}
  </header>`;
}

function viewHome() {
  const t = day();
  const queue = buildQueue('daily');
  const today = prog.log[t] || { d: 0, ok: 0 };
  const due = dueCards(pack.cards).length;
  const sections = [];
  for (const tp of pack.topics) {
    const sec = tp.section || '';
    if (!sections.length || sections.at(-1).name !== sec) sections.push({ name: sec, items: [] });
    sections.at(-1).items.push(tp);
  }
  const doneToday = today.d > 0 && !queue.length;
  $app.innerHTML = `
    ${brandHeader('<a class="icon-btn" href="#/me" aria-label="Профиль">⚙︎</a>')}
    <section class="hero">
      <div class="hero-stats">
        <div><b>${streak()}</b><span>${plural(streak(), 'день', 'дня', 'дней').replace(/^\d+ /, '')} подряд</span></div>
        <div><b>${today.d}</b><span>карточек сегодня</span></div>
        <div><b>${due}</b><span>на повторение</span></div>
      </div>
      ${doneToday
        ? '<p class="hero-done">На сегодня всё. Возвращайся завтра — карточки придут, когда начнёшь их забывать.</p>'
        : `<button class="btn primary big" id="go">${today.d ? 'Продолжить занятие' : 'Начать занятие'} · ${plural(queue.length, 'карточка', 'карточки', 'карточек')}</button>
           <p class="muted center">Примерно ${Math.max(3, Math.round(queue.length * 0.6))} минут</p>`}
      ${prog.errs.length ? `<button class="btn ghost" id="errs">Работа над ошибками · ${prog.errs.length}</button>` : ''}
    </section>
    ${sections.map(s => `
      <section class="topics">
        ${s.name ? `<h2>${esc(s.name)}</h2>` : ''}
        ${s.items.map(tp => {
          const st = topicStats(tp.id);
          const pct = st.total ? Math.round(st.mastered / st.total * 100) : 0;
          return `<a class="topic" href="#/topic/${encodeURIComponent(tp.id)}">
            <span class="topic-title">${esc(tp.title)}</span>
            <span class="topic-meta">${st.total ? `${st.mastered}/${st.total}` : 'теория'}</span>
            <span class="bar"><i style="width:${pct}%"></i></span>
          </a>`;
        }).join('')}
      </section>`).join('')}
    <footer class="foot"><a href="#/library">Другие наборы</a></footer>`;
  $app.querySelector('#go')?.addEventListener('click', () => startSession(queue, 'Занятие'));
  $app.querySelector('#errs')?.addEventListener('click', () => startSession(buildQueue('errors'), 'Работа над ошибками'));
}

function viewTopic(tid) {
  const tp = topicsById[tid];
  if (!tp) return go('#/');
  const st = topicStats(tid);
  const lessons = (pack.theory || []).filter(l => l.topic === tid);
  const errs = buildQueue('errors', tid);
  $app.innerHTML = `
    <header class="top"><a class="back" href="#/">←</a><div class="brand-title">${esc(tp.title)}</div></header>
    <section class="panel">
      <p>${st.total ? `Освоено ${st.mastered} из ${st.total}${st.acc !== null ? ` · точность ${Math.round(st.acc * 100)}%` : ''}` : 'В этой теме пока только теория'}</p>
      ${st.total ? '<button class="btn primary" id="train">Тренировать тему</button>' : ''}
      ${errs.length ? `<button class="btn ghost" id="errs">Ошибки по теме · ${errs.length}</button>` : ''}
    </section>
    ${lessons.length ? `<section class="topics"><h2>Теория</h2>${lessons.map(l =>
      `<a class="topic" href="#/lesson/${encodeURIComponent(l.id)}"><span class="topic-title">${esc(l.title)}</span>
       <span class="topic-meta">${l.min ? l.min + ' мин' : ''}</span></a>`).join('')}</section>` : ''}`;
  $app.querySelector('#train')?.addEventListener('click', () => startSession(buildQueue('topic', tid), tp.title, `#/topic/${tid}`));
  $app.querySelector('#errs')?.addEventListener('click', () => startSession(errs, 'Ошибки: ' + tp.title, `#/topic/${tid}`));
}

function viewLesson(lid) {
  const l = (pack.theory || []).find(x => x.id === lid);
  if (!l) return go('#/');
  const hasCards = pack.cards.some(c => c.t === l.topic);
  $app.innerHTML = `
    <header class="top"><a class="back" href="#/topic/${encodeURIComponent(l.topic)}">←</a><div class="brand-title">${esc(l.title)}</div></header>
    <article class="lesson">${l.html}</article>
    ${hasCards ? '<div class="panel"><button class="btn primary" id="train">Закрепить карточками</button></div>' : ''}`;
  $app.querySelector('#train')?.addEventListener('click', () =>
    startSession(buildQueue('topic', l.topic), topicsById[l.topic]?.title || l.title, `#/topic/${l.topic}`));
  window.scrollTo(0, 0);
}

function startSession(queue, title, back = '#/') {
  if (!queue.length) return toast('Здесь пока нечего повторять');
  const q = queue.slice();
  const requeued = new Set();
  let i = 0, ok = 0, answered = 0;
  const started = Date.now();
  const leave = () => { location.hash = back; route(); };

  const next = () => {
    if (i >= q.length) return finishSession();
    const card = q[i];
    $app.innerHTML = `
      <header class="top session-top">
        <button class="back" id="leave" aria-label="Выйти">✕</button>
        <div class="progress"><i style="width:${Math.round(i / q.length * 100)}%"></i></div>
        <span class="muted">${i + 1}/${q.length}</span>
      </header>
      <div class="card-topic">${esc(topicsById[card.t]?.title || title)}</div>
      <article class="card"></article>
      <div class="next-bar" hidden><button class="btn primary big" id="next">Дальше</button></div>`;
    const bar = $app.querySelector('.next-bar');
    renderCard(card, $app.querySelector('.card'), score => {
      grade(card, score);
      answered++;
      ok += score;
      // Ошибку показываем ещё раз в конце занятия, но только один раз
      if (score < 1 && !requeued.has(card.id)) { requeued.add(card.id); q.push(card); }
      bar.hidden = false;
      bar.querySelector('#next').focus({ preventScroll: true });
    });
    $app.querySelector('#next').onclick = () => { i++; next(); window.scrollTo(0, 0); };
    $app.querySelector('#leave').onclick = leave;
  };

  const finishSession = () => {
    const mins = Math.max(1, Math.round((Date.now() - started) / 60000));
    const pct = answered ? Math.round(ok / answered * 100) : 0;
    $app.innerHTML = `
      <section class="finish">
        <div class="finish-big">${pct}%</div>
        <p>${plural(answered, 'ответ', 'ответа', 'ответов')} за ${plural(mins, 'минуту', 'минуты', 'минут')}</p>
        <p class="muted">Серия: ${plural(streak(), 'день', 'дня', 'дней')}</p>
        ${ref.startsWith('t:') && prog.name ? '<p class="muted">Результат отправлен репетитору</p>' : ''}
        <button class="btn primary big" id="done">Готово</button>
      </section>`;
    $app.querySelector('#done').onclick = leave;
    sync(true);
  };
  next();
}

function viewMe() {
  const tutorPack = ref.startsWith('t:');
  $app.innerHTML = `
    <header class="top"><a class="back" href="#/">←</a><div class="brand-title">Профиль</div></header>
    <section class="panel">
      ${tutorPack ? `<label class="field"><span>Имя (его видит репетитор)</span><input id="name" value="${esc(prog.name)}"></label>` : ''}
      <label class="field"><span>Новых карточек в день</span>
        <input id="daily" type="number" min="0" max="50" value="${pack.daily || NEW_DEFAULT}" ${tutorPack ? 'disabled' : ''}></label>
      ${tutorPack ? '<p class="muted">Норму задаёт репетитор</p>' : ''}
      <button class="btn primary" id="save">Сохранить</button>
    </section>
    <section class="panel">
      <h2>Прогресс</h2>
      <p>Начато ${prog && Object.keys(prog.cards).length} из ${pack.cards.length} карточек.</p>
      <button class="btn ghost danger" id="reset">Сбросить прогресс по набору</button>
    </section>
    <section class="panel">
      <h2>Сервер ИИ</h2>
      <label class="field"><span>Адрес (если дал репетитор)</span><input id="api" placeholder="https://…workers.dev" value="${esc(store.get('zd-api', ''))}"></label>
    </section>`;
  $app.querySelector('#save').onclick = () => {
    const name = $app.querySelector('#name')?.value.trim();
    if (name !== undefined) prog.name = name;
    if (!tutorPack) {
      pack.daily = Math.max(0, Math.min(50, +$app.querySelector('#daily').value || NEW_DEFAULT));
      store.set('zd-daily:' + ref, pack.daily);
    }
    store.set('zd-api', $app.querySelector('#api').value.trim());
    save();
    toast('Сохранено');
    sync(true);
  };
  $app.querySelector('#reset').onclick = () => {
    if (!confirm('Стереть весь прогресс по этому набору?')) return;
    store.set(progKey(), null);
    loadProg();
    toast('Прогресс сброшен');
    go('#/');
  };
}

async function viewLibrary() {
  const lib = await loadLibrary();
  const recent = store.get('zd-recent', []);
  $app.innerHTML = `
    <header class="top"><a class="back" href="./" aria-label="На главную">←</a><div class="brand-title">Открытые наборы</div></header>
    <section class="panel intro">
      <p>Тренажёр на 10 минут в день: карточки возвращаются, когда начинаешь их забывать, а репетитор видит, где ты ошибаешься.</p>
      <label class="field"><span>Код от репетитора</span>
        <span class="row"><input id="code" placeholder="например, k7m2p9xq" autocapitalize="off"><button class="btn primary" id="join">Открыть</button></span>
      </label>
    </section>
    ${recent.length ? `<section class="topics"><h2>Недавние</h2>${recent.map(r =>
      `<a class="topic" href="?${r.ref.startsWith('t:') ? 't=' + encodeURIComponent(r.ref.slice(2)) : 'p=' + encodeURIComponent(r.ref)}">
        <span class="topic-title">${esc(r.title)}</span><span class="topic-meta">${esc(r.tutor || '')}</span></a>`).join('')}</section>` : ''}
    <section class="topics"><h2>Открытые наборы</h2>${lib.map(p =>
      `<a class="topic" href="?p=${encodeURIComponent(p.id)}"><span class="dot" style="background:${esc(p.color)}"></span>
        <span class="topic-title">${esc(p.title)}<small>${esc(p.desc)}</small></span>
        <span class="topic-meta">${p.cards}</span></a>`).join('')}</section>
    <footer class="foot"><a href="studio/">Я репетитор — собрать свой тренажёр</a></footer>`;
  const join = () => {
    const c = $app.querySelector('#code').value.trim().replace(/.*[?&]t=/, '');
    if (c) location.search = '?t=' + encodeURIComponent(c);
  };
  $app.querySelector('#join').onclick = join;
  $app.querySelector('#code').onkeydown = e => e.key === 'Enter' && join();
}

function viewName() {
  $app.innerHTML = `
    ${brandHeader()}
    <section class="panel intro">
      <p>${esc(pack.tutor || 'Репетитор')} собрал для тебя тренажёр: ${plural(pack.cards.length, 'карточка', 'карточки', 'карточек')}.
      Занимайся по 10 минут в день — репетитор будет видеть прогресс и знать, что разобрать на уроке.</p>
      <label class="field"><span>Как тебя зовут?</span><input id="name" placeholder="Имя и фамилия" autocomplete="name"></label>
      <button class="btn primary big" id="ok">Начать</button>
    </section>`;
  const ok = () => {
    const name = $app.querySelector('#name').value.trim();
    if (!name) return toast('Напиши имя, чтобы репетитор тебя узнал');
    prog.name = name;
    save();
    sync(true);
    route();
  };
  $app.querySelector('#ok').onclick = ok;
  $app.querySelector('#name').onkeydown = e => e.key === 'Enter' && ok();
}

// ---------- навигация ----------

const go = h => { location.hash = h; };

async function viewLanding() {
  $app.className = 'landing';
  renderLanding($app, await loadLibrary());
}

function route() {
  $app.className = 'wrap';
  if (!pack) return location.hash === '#/library' ? viewLibrary() : viewLanding();
  const [, view, arg] = decodeURI(location.hash).split('/');
  if (ref.startsWith('t:') && !prog.name) return viewName();
  if (view === 'library') return viewLibrary();
  if (view === 'topic') return viewTopic(arg);
  if (view === 'lesson') return viewLesson(arg);
  if (view === 'me') return viewMe();
  viewHome();
}

function applyBrand() {
  document.title = pack.title;
  if (pack.color) {
    document.documentElement.style.setProperty('--accent', pack.color);
    document.querySelector('meta[name=theme-color]')?.setAttribute('content', pack.color);
  }
}

async function init() {
  const params = new URLSearchParams(location.search);
  const recent = store.get('zd-recent', []);
  ref = params.get('t') ? 't:' + params.get('t') : params.get('p') || recent[0]?.ref || null;
  window.addEventListener('hashchange', route);
  if (!ref) return route();
  $app.innerHTML = '<p class="loading">Загружаю…</p>';
  try {
    pack = await loadPack(ref);
    store.set('zd-pack:' + ref, pack);
  } catch (err) {
    pack = store.get('zd-pack:' + ref, null); // офлайн — последняя сохранённая версия
    if (!pack) {
      $app.innerHTML = '';
      $app.append(el(`<section class="panel"><p>Не получилось открыть набор: ${esc(err.message)}</p><a class="btn primary" href="./">К наборам</a></section>`));
      return;
    }
  }
  topicsById = Object.fromEntries(pack.topics.map(t => [t.id, t]));
  store.set('zd-recent', [{ ref, title: pack.title, tutor: pack.tutor }, ...recent.filter(r => r.ref !== ref)].slice(0, 5));
  loadProg();
  // «Новых в день» в открытых наборах ученик задаёт сам, в наборе репетитора — репетитор
  if (!ref.startsWith('t:')) pack.daily = store.get('zd-daily:' + ref, pack.daily);
  applyBrand();
  route();
  sync(false);
}

init();
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
