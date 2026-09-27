// Приложение ученика: ежедневное занятие по интервальному повторению,
// темы с теорией, работа над ошибками и отправка прогресса репетитору.
import { store, api, apiBase, loadPack, loadLibrary, renderCard, esc, safeHtml, text, day, dueDay, dueText, whenText, uid, plural, el, toast, modal, videoEmbed, courseStats, mergeLes } from './lib.js';
import { renderLanding } from './landing.js';
import { signedIn, account, loginDialog, logout, addRole, finishRedirectLogin, finishPayment, payDialog, planOf, TG_ICON } from './account.js';

const $app = document.getElementById('app');
const INTERVALS = [0, 1, 3, 7, 14, 30, 60]; // дни до повтора по «коробкам»
const SESSION = 20;
const NEW_DEFAULT = 10;
const DAILY_GOAL = 10; // карточек в день, чтобы день засчитался в цель

let ref = null;   // 'econ-olymp' или 't:<id>' для набора репетитора
let pack = null;
let prog = null;
let topicsById = {};

// ---------- прогресс ----------

const progKey = () => 'zd-prog:' + ref;
// Прогресс хранится в браузере, а после входа в аккаунт — ещё и на сервере
// В облако — в конце занятия, при уходе со страницы и не чаще раза в 5 минут между ними:
// у бесплатного хранилища Cloudflare 1000 записей в сутки на весь сайт
let progTimer, progDirty = false;
const save = () => {
  store.set(progKey(), prog);
  if (!signedIn()) return;
  progDirty = true;
  progTimer ||= setTimeout(() => { progTimer = null; pushProg(); }, 300e3);
};
const flushProg = () => { if (progDirty && prog && signedIn()) pushProg(true); };
addEventListener('pagehide', flushProg);
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') flushProg(); });
const progUrl = () => `/me/progress/${encodeURIComponent(ref)}`;
async function pushProg(leaving = false) {
  if (!ref) return;
  progDirty = false;
  clearTimeout(progTimer); progTimer = null;
  // keepalive (отправка при закрытии вкладки) ограничен 64 КБ
  try { await api(progUrl(), { method: 'PUT', body: prog, keepalive: leaving && JSON.stringify(prog).length < 60000 }); } catch { progDirty = true; /* офлайн — отправим позже */ }
}

// Прогресс с двух устройств → один: по карточке и по дню берём, где сделано больше
function mergeProg(a, b) {
  const cards = { ...b.cards };
  for (const [id, st] of Object.entries(a.cards || {})) if (!cards[id] || st.n >= cards[id].n) cards[id] = st;
  const log = { ...b.log };
  for (const [d, l] of Object.entries(a.log || {})) if (!log[d] || l.d >= log[d].d) log[d] = l;
  const errs = [...new Set([...(a.errs || []), ...(b.errs || [])])].slice(0, 30);
  // Задание: одно и то же — где засчитано больше; разные — то, что сейчас задано в наборе
  const hw = a.hw?.id === b.hw?.id ? a.hw && { id: a.hw.id, d: Math.max(a.hw.d || 0, b.hw.d || 0) }
    : b.hw?.id && b.hw.id === pack?.hw?.id ? b.hw : a.hw;
  // sid из облака — репетитор видит одного ученика, с какого бы устройства тот ни занимался.
  // Сменился sid — сервер этого ученика ещё не видел с этого устройства: сводку отправить заново
  const sid = b.sid || a.sid, moved = sid !== a.sid;
  const les = a.les || b.les ? { les: mergeLes(a.les, b.les) } : {};
  return { ...a, cards, log, errs, hw, ...les, sid, name: a.name || b.name, variants: a.variants || b.variants,
    synced: moved ? 0 : a.synced, syncedN: moved ? -1 : a.syncedN };
}

async function pullProg() {
  if (!signedIn() || !prog) return false;
  try {
    const remote = await api(progUrl());
    if (remote) prog = mergeProg(prog, remote);
    if (!prog.name && account()?.name) prog.name = account().name;
    store.set(progKey(), prog);
    // Обратно в облако — только если здесь есть ответы, которых там нет: иначе каждое
    // открытие тренажёра стоило бы записи
    if (JSON.stringify([prog.cards, prog.log, prog.les]) !== JSON.stringify([remote?.cards || {}, remote?.log || {}, remote?.les])) await pushProg();
    else { progDirty = false; clearTimeout(progTimer); progTimer = null; }
    return !!remote;
  } catch { return false; }
}

function loadProg() {
  prog = Object.assign({ cards: {}, log: {}, errs: [], sid: uid(10), name: '', synced: 0 }, store.get(progKey(), {}));
  // Новое задание репетитора (приходит внутри набора) — счёт с нуля
  if (pack.hw && prog.hw?.id !== pack.hw.id) prog.hw = { id: pack.hw.id, d: 0 };
  save();
}

// Сколько карточек задания засчитано на этом устройстве
const hwD = () => pack.hw && prog.hw?.id === pack.hw.id ? prog.hw.d : 0;

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
  // Задание: каждый ответ по его теме (и повтор ошибки тоже), в том числе после срока
  const hw = pack.hw;
  if (hw && prog.hw?.id === hw.id && (!hw.topic || card.t === hw.topic) && prog.hw.d < hw.goal) prog.hw.d++;
  // ДЗ уроков курса: ответы по теме открытого урока, пока обе нормы не выполнены (at — день выполнения)
  for (const l of lessons()) {
    if (!l.hw || !lesOpen(l) || (l.topic && card.t !== l.topic) || prog.les?.[l.id]?.at) continue;
    const r = (prog.les ||= {})[l.id] ||= { d: 0, ok: 0 };
    r.d++;
    r.ok += score;
    if (r.d >= l.hw.goal && r.ok / r.d * 100 >= l.hw.acc) r.at = t;
  }
  save();
}

function streak() {
  let t = day(), n = 0;
  if (!prog.log[t]?.d) t--;
  while (prog.log[t]?.d) { n++; t--; }
  return n;
}

function topicStats(tid, pid) {
  const cards = pack.cards.filter(c => c.t === tid && (!pid || c.p === pid));
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

// Задание (репетитора или урока курса): сначала пора повторить, потом новые без дневной нормы,
// потом начатые — давно не виденные первыми. Так норму можно добрать, даже если новых карточек нет
function hwQueue(topic, left) {
  const hp = pack.cards.filter(c => !topic || c.t === topic);
  const due = dueCards(hp), seen = new Set(due);
  const fresh = hp.filter(c => !prog.cards[c.id]);
  const rest = hp.filter(c => prog.cards[c.id] && !seen.has(c)).sort((a, b) => (prog.cards[a.id].last || 0) - (prog.cards[b.id].last || 0));
  return [...due, ...(topic ? fresh : shuffle(fresh)), ...rest].slice(0, Math.max(0, Math.min(SESSION, left)));
}

function buildQueue(mode, tid, pid) {
  const pool = pack.cards.filter(c => (!tid || c.t === tid) && (!pid || c.p === pid));
  if (mode === 'errors') {
    const byId = Object.fromEntries(pack.cards.map(c => [c.id, c]));
    return prog.errs.map(id => byId[id]).filter(c => c && (!tid || c.t === tid) && (!pid || c.p === pid)).slice(0, SESSION);
  }
  if (mode === 'hw') return pack.hw ? hwQueue(pack.hw.topic, pack.hw.goal - hwD()) : [];
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
  // Слабые темы — как в студии (weakTopics): до трёх с точностью ниже 80%, от худшей
  const weak = Object.entries(topics).filter(([, s]) => s.acc !== null && s.s >= 3 && s.acc < 80)
    .sort((a, b) => a[1].acc - b[1].acc).slice(0, 3)
    .map(([id, s]) => ({ t: shortTitle(topicsById[id]).slice(0, 60), a: s.acc }));
  return {
    last: Date.now(), streak: streak(), today: prog.log[t] || { d: 0, ok: 0 }, week,
    // Карточек по дням за 14 дней, от старых к сегодняшнему — для полоски активности у репетитора
    days: Array.from({ length: 14 }, (_, i) => prog.log[t - 13 + i]?.d || 0), day: t,
    // 8 недель по 7 дней, последняя заканчивается сегодня: {d, ok} — для динамики точности
    weeks: Array.from({ length: 8 }, (_, i) => {
      const w = { d: 0, ok: 0 };
      for (let j = 0; j < 7; j++) {
        const l = prog.log[t - (7 - i) * 7 - j];
        if (l?.d) { w.d += l.d; w.ok += l.ok; }
      }
      w.ok = Math.round(w.ok * 2) / 2;
      return w;
    }),
    total: pack.cards.length, started: states.length, mastered: states.filter(s => s.b >= 3).length,
    topics, errs: prog.errs.slice(0, 15),
    // Для бота: он не читает сам набор, а напоминания считает по местному времени ученика
    tz: -new Date().getTimezoneOffset(), ...(prog.hw && { hw: prog.hw }),
    ...(lessons().length && { course: courseStats(prog.les, pack.course, t) }),
    title: (pack.title || '').slice(0, 80), tutor: (pack.tutor || '').slice(0, 80), weak,
  };
}

// Сколько всего ответов в журнале — по нему видно, есть ли что-то новое для репетитора
const answers = () => Object.values(prog.log).reduce((n, l) => n + (l.d || 0), 0);

async function sync(force) {
  if (!ref.startsWith('t:') || !apiBase() || !prog.name) return;
  // При открытии сводка уходит, только если с прошлой отправки появились ответы: каждая — запись в KV
  const n = answers();
  if (!force && n === prog.syncedN) return;
  // sid взят из ссылки бота (adoptSid): у сервера уже есть сводка этого ученика с другого устройства —
  // пустой её не затираем, первая уйдёт после ответов
  if (!n && prog.syncedN === 0 && !prog.synced) return;
  try {
    await api(`/packs/${encodeURIComponent(ref.slice(2))}/progress`, {
      method: 'POST', body: { sid: prog.sid, name: prog.name, stats: summary() },
    });
    prog.synced = Date.now();
    prog.syncedN = n;
    store.set(progKey(), prog); // отметки этого устройства: ради них в облако не пишем
  } catch { /* офлайн — отправим в следующий раз */ }
}

/* Кнопки бота открывают ?t=<набор>&s=<sid>: ссылка может открыться там, где ученик ещё не
   занимался (приложение на домашнем экране iPhone, браузер Telegram). Пустой прогресс (ни имени,
   ни ответов) берёт sid подписчика — у репетитора один ученик, и бот видит его занятия, а не
   застывшую запись. Непустой не трогаем. syncedN 0 при synced 0 — знак для sync() выше */
function adoptSid(s) {
  if (!/^[a-z0-9]{6,20}$/.test(s || '') || s === prog.sid || prog.name || Object.keys(prog.cards).length) return;
  Object.assign(prog, { sid: s, synced: 0, syncedN: 0, adopted: s });
  store.set(progKey(), prog);
}
// Сообщение бота могли переслать однокласснику: sid из кнопки оставляем, только если введённое
// имя совпадает с тем, под которым этот ученик уже занимается; иначе — новый ученик со своим sid
async function checkAdopted(name) {
  const s = prog.adopted;
  if (!s) return;
  delete prog.adopted;
  let known = null;
  try { known = (await api(`/packs/${encodeURIComponent(ref.slice(2))}/notify?sid=${s}&who=1`)).name; } catch { /* офлайн — оставляем */ }
  const w = x => String(x || '').trim().split(/\s+/)[0].toLowerCase().replace(/ё/g, 'е');
  if (known && w(known) !== w(name)) Object.assign(prog, { sid: uid(10), synced: 0, syncedN: -1 });
}

// ---------- напоминания в Telegram ----------

// Только в тренажёрах репетитора и когда сервер уже знает ученика (сводка уходила): иначе бот
// ответит «сначала реши несколько карточек». Ссылку в бота получаем заранее и храним, чтобы
// кнопка была обычной ссылкой — такую новую вкладку браузер не заблокирует.
// По sid: после входа (sid из облака) или сброса прогресса старая ссылка в бота не подходит
const tgKey = () => 'zd-tg:' + ref + ':' + prog.sid;
const tgState = () => (tgReady() && store.get(tgKey(), null)) || {};
const tgReady = () => ref.startsWith('t:') && !!apiBase() && prog.synced > 0;
const tgStale = () => Date.now() - (tgState().chk || 0) > 864e5;
const tgPend = () => store.set(tgKey(), { ...tgState(), pend: Date.now() });
async function refreshTg() {
  if (!tgReady()) return null;
  try {
    const r = await api(`/packs/${encodeURIComponent(ref.slice(2))}/notify?sid=${encodeURIComponent(prog.sid)}`);
    const tg = { ...tgState(), on: !!r.on, at: r.at || null, link: r.link || null, chk: Date.now() };
    store.set(tgKey(), tg);
    return tg;
  } catch { return null; }
}

// ---------- экраны ----------

// Иконки — inline SVG, цвет берут из currentColor
const ICON = {
  flame: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3c1 4 5 5 5 10a5 5 0 0 1-10 0c0-3 2-4 2-6 1.5 1 2 2 2 3 0-3 1-5 1-7z"/></svg>',
  star: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/></svg>',
  gear: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>',
  play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4v16l13-8z"/></svg>',
  chevron: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>',
  book: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h11a4 4 0 0 1 4 4v10H8a4 4 0 0 1-4-4z"/><path d="M8 10h7M8 14h5"/></svg>',
};

// Очки: 10 за каждый верный ответ за всё время (считаются из журнала, отдельно не хранятся)
const POINTS = 10;
const totalPoints = () => Math.round(Object.values(prog.log).reduce((n, l) => n + (l.ok || 0), 0) * POINTS);

function initials(s) {
  return (s || '').replace(/[^\p{L}\s]/gu, ' ').trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase() || 'М';
}

function streakBadge() {
  const s = streak();
  return `<span class="streak-badge${s ? '' : ' off'}" title="${plural(s, 'день', 'дня', 'дней')} подряд">${ICON.flame}<b>${s}</b></span>`;
}

// Кольцо цели дня
function goalRing(n, goal) {
  const c = 2 * Math.PI * 38;
  const part = Math.min(n, goal) / goal * c;
  return `<svg class="ring" viewBox="0 0 92 92" aria-hidden="true">
    <circle cx="46" cy="46" r="38" class="ring-bg"/>
    <circle cx="46" cy="46" r="38" class="ring-fg" stroke-dasharray="${part.toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 46 46)"/>
    <text x="46" y="53" text-anchor="middle">${Math.min(n, goal)}/${goal}</text></svg>`;
}

// Цвет по точности: зелёный ≥ 80%, жёлтый 60–79%, красный ниже
const accTone = acc => acc === null ? 'new' : acc >= 0.8 ? 'ok' : acc >= 0.6 ? 'mid' : 'bad';

function brandHeader(sub) {
  const who = pack.tutor ? `<div class="brand-by">${esc(pack.tutor)}</div>` : '';
  return `<header class="top">
    <div><div class="brand-title">${esc(pack.title)}</div>${who}</div>
    ${sub || ''}
  </header>`;
}

function goalBar(done) {
  const n = Math.min(done, DAILY_GOAL);
  return n >= DAILY_GOAL
    ? '<div class="goal done">✓ Цель дня выполнена</div>'
    : `<div class="goal"><span>Цель дня</span><span class="bar"><i style="width:${n / DAILY_GOAL * 100}%"></i></span><b>${n}/${DAILY_GOAL}</b></div>`;
}

// Задание репетитора на главной: видно до срока (невыполненное — ещё 3 дня после него)
function hwCard() {
  const hw = pack.hw;
  if (!hw) return '';
  const d = Math.min(hwD(), hw.goal), done = d >= hw.goal, L = day(), end = dueDay(hw.due);
  if (L > end + (done ? 0 : 3)) return '';
  const [tone, when] = done ? ['ok', 'Выполнено'] : L > end ? ['bad', 'Срок прошёл — доделать ещё можно']
    : L === end ? ['mid', 'Сегодня последний день'] : ['', 'до ' + dueText(hw.due)];
  return `<section class="panel hw-card${tone ? ' ' + tone : ''}">
      <div class="row"><b>Задание репетитора</b><span class="pill${tone ? ' ' + tone : ''}">${when}</span></div>
      <p>${esc(hw.text)}</p>
      <div class="goal"><span>Сделано</span><span class="bar"><i style="width:${Math.round(d / hw.goal * 100)}%"></i></span><b>${d}/${hw.goal}</b></div>
      ${done ? '' : '<button class="btn primary" id="hw-go">Делать задание</button>'}
    </section>`;
}

// Сессия задания: с главной, по ссылке #/hw из бота и кнопкой «Ещё» после неё
function startHw() {
  const q = buildQueue('hw');
  if (q.length) return startSession(q, 'Домашнее задание', '#/', { hw: true });
  viewHome();
  toast(hwD() < pack.hw.goal ? 'Здесь пока нечего повторять' : 'Задание уже выполнено');
}

// ---------- курс ----------

// Курс лежит в наборе (pack.course): уроки по порядку и эфиры. Выполнение ДЗ считает grade()
const LIVE_MS = 2 * 3600e3; // эфир считаем идущим ещё 2 часа после начала
const lessons = () => pack.course?.lessons || [];
const lives = () => (pack.course?.lives || []).slice().sort((a, b) => Date.parse(a.at) - Date.parse(b.at));
const lesOpen = l => !l.open || dueDay(l.open) <= day();
const lesRec = l => prog.les?.[l.id] || { d: 0, ok: 0 };
const lesDone = l => !!lesRec(l).at;
const lesNum = l => lessons().indexOf(l) + 1;
// Ссылки эфира вписывает репетитор — в страницу попадает только https
const httpsUrl = u => { try { const x = new URL(u); return x.protocol === 'https:' ? x.href : ''; } catch { return ''; } };

// ДЗ не сделано — очередь как у задания (норму можно добрать и повторами); точность ниже нормы —
// ещё 10 карточек. Урок без ДЗ — обычная тренировка темы
function lesQueue(l) {
  const r = lesRec(l);
  if (l.hw && !r.at) return hwQueue(l.topic, r.d >= l.hw.goal ? 10 : l.hw.goal - r.d);
  return l.topic ? buildQueue('topic', l.topic) : buildQueue('daily');
}

// Тон и подпись урока — как у задания репетитора на главной
function lesState(l) {
  const r = lesRec(l), L = day();
  if (!l.hw) return r.at ? ['ok', 'Пройден'] : ['', 'Без ДЗ'];
  const end = dueDay(l.hw.due);
  return r.at ? (r.at <= end ? ['ok', 'ДЗ выполнено'] : ['mid', 'ДЗ сдано после срока'])
    : L > end ? ['bad', 'Срок прошёл'] : L === end ? ['mid', 'Сегодня последний день'] : ['', 'ДЗ до ' + dueText(l.hw.due)];
}

function lesHwBar(l) {
  const r = lesRec(l), d = Math.min(r.d, l.hw.goal), acc = r.d ? Math.round(r.ok / r.d * 100) : null;
  return `<div class="goal"><span>ДЗ</span><span class="bar"><i style="width:${Math.round(d / l.hw.goal * 100)}%"></i></span><b>${d}/${l.hw.goal}</b></div>
    <p class="les-hw-note">${d} из ${l.hw.goal} · точность ${acc === null ? '—' : acc + '%'} (нужно от ${l.hw.acc}%) · срок ${dueText(l.hw.due)}</p>`;
}

function liveIcs(v) {
  const url = httpsUrl(v.url) || packLink();
  icsEvent({ start: new Date(v.at), durationMin: 60, summary: `Эфир: ${v.title}`, desc: `${pack.title}. Ссылка: ${url}`, url, alarmMin: 15, utc: true, file: 'efir.ics' });
  toast('Откроется календарь — подтвердите эфир');
}

// Карточка курса на главной: ближайший эфир (в течение суток) или следующий урок
function courseCard() {
  if (!lessons().length && !pack.course?.lives?.length) return '';
  const now = Date.now();
  const live = lives().find(v => Date.parse(v.at) + LIVE_MS > now && Date.parse(v.at) - now < 864e5);
  const next = lessons().find(l => lesOpen(l) && !lesDone(l));
  const soon = lessons().find(l => !lesOpen(l));
  let body;
  if (live) {
    const url = httpsUrl(live.url);
    body = `<div class="course-next"><span class="pill mid">${Date.parse(live.at) <= now ? 'Эфир идёт' : 'Эфир'}</span><b>${esc(live.title)}</b><span class="muted">${whenText(live.at)}</span></div>
      ${url ? `<a class="btn primary" href="${esc(url)}" target="_blank" rel="noopener">Подключиться</a>` : ''}`;
  } else if (next) {
    const [tone, when] = lesState(next);
    body = `<div class="course-next"><span class="pill${tone ? ' ' + tone : ''}">${when}</span><b>Урок ${lesNum(next)}. ${esc(next.title)}</b></div>
      <a class="btn primary" href="#/c/${encodeURIComponent(next.id)}">Открыть</a>`;
  } else {
    body = `<p class="course-next">${lessons().length ? 'Все открытые уроки пройдены.' : 'Скоро здесь появятся уроки.'}${soon ? ` Следующий откроется ${dueText(soon.open)}.` : ''}</p>`;
  }
  return `<section class="panel course-card">
      <div class="row"><b>Курс</b><span class="muted">${lessons().filter(lesDone).length} из ${lessons().length} уроков</span></div>
      ${body}
      <a class="course-all" href="#/course">Все уроки ${ICON.chevron}</a>
    </section>`;
}

// Лента курса: сейчас — открытые и не пройденные, скоро — ещё закрытые, пройдено, эфиры
function viewCourse() {
  const ls = lessons(), now = Date.now();
  const row = l => {
    const [tone, when] = lesOpen(l) ? lesState(l) : ['', 'откроется ' + dueText(l.open)];
    const inner = `<span class="les-n">${lesNum(l)}</span><span class="topic-title">${esc(l.title)}</span><span class="pill${tone ? ' ' + tone : ''}">${when}</span>`;
    return lesOpen(l) ? `<a class="les-row" href="#/c/${encodeURIComponent(l.id)}">${inner}</a>` : `<div class="les-row locked">${inner}</div>`;
  };
  const group = (title, items) => items.length ? `<section class="topics"><h2>${title}</h2>${items.map(row).join('')}</section>` : '';
  const lv = lives(), next = lv.filter(v => Date.parse(v.at) + LIVE_MS > now), old = lv.filter(v => Date.parse(v.at) + LIVE_MS <= now).reverse();
  const liveRow = v => {
    const url = httpsUrl(v.url), rec = httpsUrl(v.rec), past = Date.parse(v.at) + LIVE_MS <= now;
    return `<div class="live-row"><div><b>${esc(v.title)}</b><span class="muted">${whenText(v.at)}</span></div>
      <div class="row">${past ? (rec ? `<a class="btn" href="${esc(rec)}" target="_blank" rel="noopener">Запись</a>` : '<span class="muted small-note">Запись появится позже</span>')
        : `${url ? `<a class="btn primary" href="${esc(url)}" target="_blank" rel="noopener">Подключиться</a>` : ''}<button class="btn" data-ics="${esc(v.id)}">В календарь</button>`}</div></div>`;
  };
  $app.innerHTML = `
    <header class="top"><a class="back" href="#/" aria-label="Назад">←</a><div><div class="brand-by">${esc(pack.title)}</div><div class="brand-title">Курс</div></div></header>
    ${group('Сейчас', ls.filter(l => lesOpen(l) && !lesDone(l)))}
    ${group('Скоро', ls.filter(l => !lesOpen(l)))}
    ${group('Пройдено', ls.filter(l => lesOpen(l) && lesDone(l)))}
    ${lv.length ? `<section class="topics"><h2>Эфиры</h2>${[...next, ...old].map(liveRow).join('')}</section>` : ''}
    ${ls.length || lv.length ? '' : '<p class="panel empty">Уроков пока нет.</p>'}`;
  $app.querySelectorAll('[data-ics]').forEach(b => b.onclick = () => liveIcs(lv.find(v => v.id === b.dataset.ics)));
  window.scrollTo(0, 0);
}

// Урок по шагам: видео → конспект → тренажёр с ДЗ
function viewCourseLesson(id) {
  const l = lessons().find(x => x.id === id);
  if (!l) return go('#/course');
  const head = `<header class="top"><a class="back" href="#/course" aria-label="Назад">←</a><div><div class="brand-by">Урок ${lesNum(l)}</div><div class="brand-title">${esc(l.title)}</div></div></header>`;
  if (!lesOpen(l)) {
    $app.innerHTML = `${head}<p class="panel empty">Урок откроется ${dueText(l.open)}.</p>`;
    return;
  }
  // Урок без ДЗ пройден, когда его открыли
  if (!l.hw && !lesRec(l).at) { (prog.les ||= {})[l.id] = { d: 0, ok: 0, at: day() }; save(); }
  const hasCards = pack.cards.some(c => !l.topic || c.t === l.topic);
  const steps = [
    l.video && videoEmbed(l.video) ? ['Видео', videoEmbed(l.video)] : null,
    l.notes ? ['Конспект', `<div class="lesson les-notes">${text(l.notes)}</div>`] : null,
    hasCards && (l.hw || l.topic) ? ['Тренажёр', `<div class="panel les-train${l.hw && lesDone(l) ? ' ok' : ''}">
      ${l.hw ? lesHwBar(l) : '<p class="les-hw-note">Закрепите тему карточками — они вернутся на повторение, когда начнут забываться.</p>'}
      <button class="btn primary" id="train">${ICON.play}Закрепить в тренажёре</button></div>`] : null,
  ].filter(Boolean);
  $app.innerHTML = `${head}
    ${steps.map(([t, html], i) => `<section class="lesson-step"><h2><span class="les-n">${i + 1}</span>${t}</h2>${html}</section>`).join('')}
    ${steps.length ? '' : '<p class="panel empty">В уроке пока ничего нет.</p>'}`;
  $app.querySelector('#train')?.addEventListener('click', () =>
    startSession(lesQueue(l), `Урок ${lesNum(l)}. ${l.title}`, '#/c/' + encodeURIComponent(l.id), { les: l.id }));
  window.scrollTo(0, 0);
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
  const s = streak();
  const n = Math.min(today.d, DAILY_GOAL);
  const goalText = n >= DAILY_GOAL ? `Выполнена! Серия ${plural(s, 'день', 'дня', 'дней')}`
    : today.d ? `Ещё ${plural(DAILY_GOAL - n, 'карточка', 'карточки', 'карточек')} — и цель выполнена`
    : `Начни сегодня — серия станет ${plural(s + 1, 'день', 'дня', 'дней')}`;
  const first = (prog.name || '').split(/\s+/)[0];
  $app.innerHTML = `
    <header class="top home-top">
      <span class="avatar" aria-hidden="true">${esc(initials(pack.tutor || pack.title))}</span>
      <div><div class="brand-by">${esc([pack.tutor, pack.title].filter(Boolean).join(' · '))}</div>
        <div class="brand-title">${first ? `Привет, ${esc(first)}!` : 'Привет!'}</div></div>
      ${streakBadge()}
      <a class="icon-btn" href="#/me" aria-label="Профиль">${ICON.gear}</a>
    </header>
    <section class="goal-card">
      ${goalRing(today.d, DAILY_GOAL)}
      <div><b>Цель дня</b><span>${goalText}</span></div>
    </section>
    ${hwCard()}
    ${courseCard()}
    ${doneToday
      ? '<p class="hero-done">На сегодня всё. Возвращайся завтра — карточки придут, когда начнёшь их забывать.</p>'
      : `<button class="btn cta big" id="go">${ICON.play}${today.d ? 'Продолжить' : 'Заниматься'} · ${Math.max(3, Math.round(queue.length * 0.6))} мин</button>
         <p class="muted center small-note">${plural(queue.length, 'карточка', 'карточки', 'карточек')}${due ? ` · ${due} на повторение` : ''} · ${totalPoints()} очков</p>`}
    ${prog.errs.length || isExam() ? `<div class="home-actions">
      ${prog.errs.length ? `<button class="btn" id="errs">Ошибки · ${prog.errs.length}</button>` : ''}
      ${isExam() ? `<button class="btn" id="variant">Пробный вариант${lastVariant()}</button>` : ''}
    </div>` : ''}
    ${unlockBlock()}
    ${isExam() ? examGrid() : sections.map(s => `
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
    <footer class="foot"><a href="#/library">Другие наборы</a> · <a href="./?about">Для репетиторов</a></footer>`;
  bindUnlock();
  $app.querySelector('#go')?.addEventListener('click', () => startSession(queue, 'Занятие'));
  $app.querySelector('#hw-go')?.addEventListener('click', startHw);
  $app.querySelector('#errs')?.addEventListener('click', () => startSession(buildQueue('errors'), 'Работа над ошибками'));
  $app.querySelector('#variant')?.addEventListener('click', () => startSession(buildVariant(), 'Пробный вариант', '#/', { variant: true }));
}

// ---------- доступ к библиотеке ----------

// Без доступа сервер отдаёт часть библиотеки (pack.limited) — предлагаем открыть всё
function unlockBlock(short) {
  if (!pack.limited) return '';
  const trialFree = !signedIn() || !planOf('lib').trialEnd;
  if (short) return `<p class="locked">Остальные прототипы — в полном доступе. <button class="link-btn unlock">${trialFree ? 'Открыть бесплатно' : 'Открыть'}</button></p>`;
  return `<section class="paywall">
    <b>Открыто ${pack.limited.shown} из ${pack.limited.total} заданий</b>
    <span>${trialFree ? 'Все прототипы, разборы и пробные варианты — первые 7 дней бесплатно.' : 'Все прототипы, разборы и пробные варианты по подписке.'}</span>
    <button class="btn cta unlock">${trialFree ? 'Открыть бесплатно' : 'Открыть полный доступ'}</button>
  </section>`;
}

function bindUnlock() {
  $app.querySelectorAll('.unlock').forEach(b => b.addEventListener('click', () => {
    if (!signedIn()) return loginDialog({ role: 'student', why: 'Войдите — и откроется пробный период с полным доступом.', onDone: async () => { await addRole('student'); location.reload(); } });
    if (!planOf('lib').trialEnd) return addRole('student').then(() => location.reload());
    payDialog({ product: 'lib' });
  }));
}

// ---------- каталог заданий экзамена ----------

// Подпись над карточкой: номер задания и прототип, если они есть
function cardLabel(card, fallback) {
  const t = topicsById[card.t];
  if (!t) return fallback;
  const pr = card.p && (t.protos || []).find(x => x.id === card.p);
  return pr ? `${t.n ? t.n + '. ' : ''}${pr.title}` : t.title;
}

// Набор-экзамен: темы пронумерованы как задания (у ЕГЭ по русскому — 1–27)
const isExam = () => pack.topics.some(t => t.n);
const shortTitle = t => t.title.replace(/^\d+\.\s*/, '');

function examGrid() {
  return `<section class="topics"><h2>Задания ЕГЭ</h2><div class="task-grid">${pack.topics.map(tp => {
    const st = topicStats(tp.id);
    const acc = st.started ? st.acc : null;
    return `<a class="task-tile ${accTone(acc)}" href="#/topic/${encodeURIComponent(tp.id)}" title="${esc(tp.title)}" aria-label="Задание ${tp.n}: ${esc(shortTitle(tp))}">
      <b>${tp.n}</b><span>${acc === null ? 'новое' : Math.round(acc * 100) + '%'}</span></a>`;
  }).join('')}</div>
  <p class="muted legend">Точность: <span class="dot ok"></span> 80%+ <span class="dot mid"></span> 60–79% <span class="dot bad"></span> ниже 60%</p></section>`;
}

// Вариант: по одной карточке на каждое задание с тестовым ответом
function buildVariant() {
  return pack.topics.filter(t => t.n && t.pts < 10).map(t => {
    const pool = pack.cards.filter(c => c.t === t.id && c.k !== 'flip');
    return pool.length ? pool[Math.floor(Math.random() * pool.length)] : null;
  }).filter(Boolean);
}

function lastVariant() {
  const v = (prog.variants || []).at(-1);
  return v ? ` · прошлый ${v.s}/${v.max}` : '';
}

function viewTopic(tid) {
  const tp = topicsById[tid];
  if (!tp) return go('#/');
  const st = topicStats(tid);
  const lessons = (pack.theory || []).filter(l => l.topic === tid);
  const errs = buildQueue('errors', tid);
  const protos = (tp.protos || []).filter(pr => pack.cards.some(c => c.p === pr.id));
  const pct = st.total ? Math.round(st.mastered / st.total * 100) : 0;
  $app.innerHTML = `
    <header class="top"><a class="back" href="#/" aria-label="Назад">←</a><div>
      ${tp.n ? `<div class="brand-by">Задание ${tp.n} · ${plural(tp.pts, 'балл', 'балла', 'баллов')}</div>` : ''}</div></header>
    <section class="topic-hero">
      <h1>${esc(tp.n ? shortTitle(tp) : tp.title)}</h1>
      ${st.total ? `<span class="bar big-bar"><i style="width:${pct}%"></i></span>
        <span class="topic-hero-meta">${st.acc !== null ? `${Math.round(st.acc * 100)}% точность · ` : ''}${st.mastered} из ${st.total} освоено</span>`
        : '<span class="topic-hero-meta">В этой теме пока только теория</span>'}
    </section>
    ${st.total ? `<div class="home-actions">
      <button class="btn primary" id="train">${protos.length ? 'Тренировать все' : 'Тренировать'}</button>
      ${errs.length ? `<button class="btn" id="errs">Ошибки · ${errs.length}</button>` : ''}
    </div>` : ''}
    ${protos.length ? `<section class="topics"><h2>Прототипы</h2>${protos.map(pr => {
      const ps = topicStats(tid, pr.id);
      const acc = ps.started ? ps.acc : null;
      return `<button class="proto" data-proto="${esc(pr.id)}">
        <span class="acc-badge ${accTone(acc)}">${acc === null ? '—' : Math.round(acc * 100) + '%'}</span>
        <span class="proto-body"><b>${esc(pr.title)}</b>${pr.tip ? `<span class="proto-tip">${esc(pr.tip)}</span>` : ''}
          <span class="proto-meta">${ps.mastered} из ${ps.total} освоено</span></span>
        ${ICON.chevron}
      </button>`;
    }).join('')}${(tp.protos || []).length > protos.length ? unlockBlock(true) : ''}</section>` : ''}
    ${lessons.length ? `<section class="topics"><h2>Теория</h2>${lessons.map(l =>
      `<a class="topic lesson-link" href="#/lesson/${encodeURIComponent(l.id)}">${ICON.book}<span class="topic-title">${esc(l.title)}</span>
       <span class="topic-meta">${l.min ? l.min + ' мин' : ''}</span></a>`).join('')}</section>` : ''}`;
  bindUnlock();
  $app.querySelector('#train')?.addEventListener('click', () => startSession(buildQueue('topic', tid), tp.title, `#/topic/${tid}`));
  $app.querySelector('#errs')?.addEventListener('click', () => startSession(errs, 'Ошибки: ' + tp.title, `#/topic/${tid}`));
  $app.querySelectorAll('[data-proto]').forEach(b => b.onclick = () => {
    const pr = protos.find(x => x.id === b.dataset.proto);
    startSession(buildQueue('topic', tid, pr.id), pr.title, `#/topic/${tid}`);
  });
}

function viewLesson(lid) {
  const l = (pack.theory || []).find(x => x.id === lid);
  if (!l) return go('#/');
  const hasCards = pack.cards.some(c => c.t === l.topic);
  $app.innerHTML = `
    <header class="top"><a class="back" href="#/topic/${encodeURIComponent(l.topic)}">←</a><div class="brand-title">${esc(l.title)}</div></header>
    <article class="lesson">${safeHtml(l.html)}</article>
    ${hasCards ? '<div class="panel"><button class="btn primary" id="train">Закрепить карточками</button></div>' : ''}`;
  $app.querySelector('#train')?.addEventListener('click', () =>
    startSession(buildQueue('topic', l.topic), topicsById[l.topic]?.title || l.title, `#/topic/${l.topic}`));
  window.scrollTo(0, 0);
}

const PRAISE = ['Верно!', 'Точно!', 'Отлично!', 'Так держать!', 'В точку!'];

function startSession(queue, title, back = '#/', { variant = false, hw = false, les = null } = {}) {
  if (!queue.length) return toast('Здесь пока нечего повторять');
  const q = queue.slice();
  const requeued = new Set();
  let i = 0, ok = 0, answered = 0, points = 0;
  const started = Date.now();
  const streakBefore = streak();
  const hwBefore = hwD();
  const lesson = les && lessons().find(l => l.id === les), lesBefore = lesson && lesDone(lesson);
  const missed = new Map();
  const results = [];
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
      <div class="card-topic">${topicsById[card.t]?.n ? `<span class="num-badge">${topicsById[card.t].n}</span>` : ''}<span>${esc(cardLabel(card, title).replace(/^\d+\.\s*/, ''))}</span></div>
      <article class="card"></article>
      <div class="next-bar" hidden><div class="verdict"></div><button class="btn primary big" id="next">Дальше</button></div>`;
    const bar = $app.querySelector('.next-bar');
    renderCard(card, $app.querySelector('.card'), score => {
      grade(card, score);
      answered++;
      ok += score;
      points += score * POINTS;
      const v = $app.querySelector('.verdict');
      v.className = `verdict ${score === 1 ? 'ok' : score > 0 ? 'mid' : 'bad'}`;
      v.innerHTML = variant ? '<span>Ответ записан</span>'
        : score === 1 ? `<b>+${POINTS}</b><span>${PRAISE[Math.floor(Math.random() * PRAISE.length)]}</span>`
        : score > 0 ? `<b>+${score * POINTS}</b><span>Почти! Карточка вернётся завтра</span>`
        : '<span>Не страшно — карточка вернётся в конце и завтра</span>';
      // Ошибку показываем ещё раз в конце занятия, но только один раз
      if (score < 1) missed.set(card.id, card);
      if (variant) results.push({ card, score });
      else if (score < 1 && !requeued.has(card.id)) { requeued.add(card.id); q.push(card); }
      bar.hidden = false;
      bar.querySelector('#next').focus({ preventScroll: true });
    });
    $app.querySelector('#next').onclick = () => { i++; next(); window.scrollTo(0, 0); };
    $app.querySelector('#leave').onclick = leave;
  };

  const finishSession = () => {
    if (variant) return finishVariant();
    const mins = Math.max(1, Math.round((Date.now() - started) / 60000));
    const pct = answered ? Math.round(ok / answered * 100) : 0;
    const st = streak();
    let [icon, head] = st > streakBefore ? [ICON.flame, `Серия ${plural(st, 'день', 'дня', 'дней')}!`]
      : pct >= 90 ? [ICON.star, 'Отлично!'] : pct >= 70 ? [ICON.star, 'Хорошая работа'] : [ICON.flame, 'Начало положено'];
    // Задание: итог сессии задания, а в обычном занятии — если оно выполнилось только что
    const goal = pack.hw?.goal, d = Math.min(hwD(), goal);
    if (goal && d >= goal && (hw || hwBefore < goal)) [icon, head] = [ICON.star, 'Задание выполнено!'];
    else if (goal && hw) head = `Задание: ${d} из ${goal}`;
    // ДЗ урока курса: так же — выполнено только что или сколько сделано
    if (lesson?.hw && lesDone(lesson) && !lesBefore) [icon, head] = [ICON.star, 'ДЗ урока выполнено!'];
    else if (lesson?.hw && !lesDone(lesson)) head = `ДЗ урока: ${Math.min(lesRec(lesson).d, lesson.hw.goal)} из ${lesson.hw.goal}`;
    // После задания «Ещё» продолжает задание, пока оно не сделано; после урока — ДЗ урока
    const hwMore = hw ? buildQueue('hw') : [];
    const lesMore = lesson?.hw && !lesDone(lesson) ? lesQueue(lesson) : [];
    const more = hwMore.length ? hwMore : lesMore.length ? lesMore : back === '#/' ? buildQueue('daily') : [];
    const wrong = [...missed.values()];
    // Telegram: предлагаем, пока не включён, и не чаще раза в сутки после нажатия
    const tg = tgState();
    const tgOffer = tg.link && !tg.on && Date.now() - (tg.pend || 0) > 864e5;
    $app.innerHTML = `
      <section class="finish">
        <div class="confetti" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></div>
        <div class="finish-icon">${icon}</div>
        <h1 class="finish-title">${head}</h1>
        ${ref.startsWith('t:') && prog.name ? `<p class="finish-sub">${esc(pack.tutor || 'Репетитор')} увидит результат</p>` : ''}
        <div class="finish-stats">
          <div><b>${Math.round(ok)}/${answered}</b><span>верно</span></div>
          <div><b>+${Math.round(points)}</b><span>очков</span></div>
          <div><b>${mins}</b><span>${plural(mins, 'минута', 'минуты', 'минут').replace(/^\d+ /, '')}</span></div>
        </div>
        ${goalBar((prog.log[day()] || { d: 0 }).d)}
        ${wrong.length ? `<div class="finish-wrong"><b>Вернутся завтра</b><ul>${wrong.slice(0, 5).map(c =>
          `<li>${esc(c.q.replace(/\s+/g, ' ').slice(0, 90))}${c.q.length > 90 ? '…' : ''}</li>`).join('')}</ul></div>` : ''}
        ${more.length ? `<button class="btn big" id="more">Ещё ${plural(more.length, 'карточка', 'карточки', 'карточек')}</button>` : ''}
        ${tgOffer ? `<a class="btn big tg" id="tg" href="${esc(tg.link)}" target="_blank" rel="noopener">${TG_ICON}Напоминать в Telegram</a>
          <p class="muted small-note tg-note">Бот напишет вечером, только если ты забудешь позаниматься, и пришлёт задание репетитора.</p>` : ''}
        ${tg.on || store.get('zd-remind:' + ref, '') ? '' : '<button class="btn big" id="remind">Напоминать каждый день в 19:00</button>'}
        <button class="btn primary big" id="done">Готово</button>
      </section>`;
    $app.querySelector('#done').onclick = leave;
    $app.querySelector('#more')?.addEventListener('click', () => startSession(more, title, back, { hw: hwMore.length > 0, les: lesMore.length ? les : null }));
    $app.querySelector('#remind')?.addEventListener('click', e => { addReminder(store.get('zd-remind-time', '19:00')); e.target.remove(); });
    // Ссылка открывается сама (target=_blank); убираем кнопку уже после перехода
    $app.querySelector('#tg')?.addEventListener('click', () => {
      tgPend();
      setTimeout(() => $app.querySelectorAll('#tg, .tg-note').forEach(x => x.remove()));
    });
    sync(true).then(() => { if (progDirty && signedIn()) pushProg(); }); // урок окончен — прогресс в облако сразу
  };
  const finishVariant = () => {
    const tasks = results.map(({ card, score }) => {
      const t = topicsById[card.t];
      return { id: t.id, n: t.n, title: shortTitle(t), pts: t.pts, got: Math.round(t.pts * score * 2) / 2 };
    }).sort((a, b) => a.n - b.n);
    const s = tasks.reduce((n, t) => n + t.got, 0);
    const max = tasks.reduce((n, t) => n + t.pts, 0);
    const mins = Math.max(1, Math.round((Date.now() - started) / 60000));
    prog.variants = [...(prog.variants || []), { at: Date.now(), s, max, mins }].slice(-20);
    save();
    $app.innerHTML = `
      <section class="finish">
        <div class="finish-icon">${ICON.star}</div>
        <h1 class="finish-title">${s} из ${max}</h1>
        <p class="finish-sub">первичных баллов · ${plural(mins, 'минута', 'минуты', 'минут')}</p>
        <div class="variant-list">${tasks.map(t => `
          <a class="variant-row ${t.got >= t.pts ? 'ok' : t.got > 0 ? 'mid' : 'bad'}" href="#/topic/${esc(t.id)}">
            <b>${t.n}</b><span>${esc(t.title)}</span><em>${t.got}/${t.pts}</em></a>`).join('')}</div>
        <p class="finish-sub">Нажми на задание с ошибкой — откроются его прототипы и правила</p>
        <button class="btn primary big" id="done">Готово</button>
      </section>`;
    $app.querySelector('#done').onclick = leave;
    sync(true).then(() => { if (progDirty && signedIn()) pushProg(); }); // урок окончен — прогресс в облако сразу
  };
  next();
}

// Напоминание без push-сервера: ежедневное событие календаря (.ics) со звуком и ссылкой.
// Телефон сам предлагает добавить его в календарь — работает и на iPhone.
function packLink() {
  const base = location.origin + location.pathname;
  return ref.startsWith('t:') ? `${base}?t=${encodeURIComponent(ref.slice(2))}` : `${base}?p=${encodeURIComponent(ref)}`;
}

// Событие календаря: utc — точный момент (эфир), иначе местное время без пояса (ежедневное
// напоминание остаётся в 19:00 и после переезда в другой часовой пояс)
function icsEvent({ start, durationMin, rrule, summary, desc, url, alarmMin = 0, utc = false, file }) {
  const pad = n => String(n).padStart(2, '0');
  const local = d => `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}T${pad(d.getHours())}${pad(d.getMinutes())}00`;
  const stamp = d => d.toISOString().replace(/[-:]/g, '').replace(/\.\d+/, '');
  const icsText = s => s.replace(/[\\;,]/g, m => '\\' + m).replace(/\n/g, '\\n');
  const title = icsText(summary);
  const ics = [
    'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Между уроками//RU', 'CALSCALE:GREGORIAN',
    'BEGIN:VEVENT', `UID:${uid(12)}@mezhdu-urokami`, `DTSTAMP:${stamp(new Date())}`, `DTSTART:${utc ? stamp(start) : local(start)}`, `DURATION:PT${durationMin}M`,
    ...(rrule ? [`RRULE:${rrule}`] : []), `SUMMARY:${title}`, `URL:${url}`,
    `DESCRIPTION:${icsText(desc)}`,
    'BEGIN:VALARM', 'ACTION:DISPLAY', `TRIGGER:${alarmMin ? `-PT${alarmMin}M` : 'PT0M'}`, `DESCRIPTION:${title}`, 'END:VALARM',
    'END:VEVENT', 'END:VCALENDAR', '',
  ].join('\r\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([ics], { type: 'text/calendar;charset=utf-8' }));
  a.download = file;
  document.body.append(a);
  a.click();
  a.remove();
}

function addReminder(time) {
  const [hh, mm] = time.split(':').map(Number);
  const start = new Date();
  start.setHours(hh, mm, 0, 0);
  if (start < new Date()) start.setDate(start.getDate() + 1);
  const link = packLink();
  icsEvent({ start, durationMin: 10, rrule: 'FREQ=DAILY', summary: `10 минут: ${pack.title}`, desc: 'Карточки на сегодня ждут: ' + link, url: link, file: 'napominanie.ics' });
  store.set('zd-remind:' + ref, time);
  toast(`Откроется календарь — подтвердите событие на ${time}`);
}

// Панель «Напоминания в Telegram» в профиле: пусто, если бот не настроен и ничего не включено
function tgPanel(tg) {
  if (tg.on) return `<h2>Напоминания в Telegram</h2>
    <p><span class="pill ok">Включены</span> Бот напишет около ${esc(tg.at || '19:00')}, если в этот день ещё не было занятия, и пришлёт задания репетитора.</p>
    <button class="btn" id="tg-off">Выключить</button>
    <p class="muted small-note">Время — в боте: /settings.</p>`;
  if (!tg.link) return '';
  return `<h2>Напоминания в Telegram</h2>
    <p class="muted">Бот напишет вечером, только если ты забудешь позаниматься, и пришлёт задание от репетитора. Не чаще раза в день и не ночью.</p>
    <a class="btn primary tg" id="tg-on" href="${esc(tg.link)}" target="_blank" rel="noopener">${TG_ICON}Напоминать в Telegram</a>
    <p class="muted small-note">Откроется Telegram — нажми там «Запустить».</p>`;
}

function viewMe() {
  const tutorPack = ref.startsWith('t:');
  const a = account();
  $app.innerHTML = `
    <header class="top"><a class="back" href="#/">←</a><div class="brand-title">Профиль</div></header>
    <section class="panel">
      <h2>Аккаунт</h2>
      ${signedIn()
        ? `<p>Вы вошли как <b>${esc(a?.name || a?.email || 'ученик')}</b>. Прогресс сохраняется в аккаунте — можно заниматься с телефона и компьютера.</p>
           <div class="row"><a class="btn primary" href="cabinet/#student">Личный кабинет</a><button class="btn" id="pcode">Код для родителя</button><button class="btn" id="logout">Выйти</button></div>`
        : `<p class="muted">Войдите, чтобы прогресс не потерялся и был доступен на любом устройстве.</p>
           <button class="btn primary" id="login">Войти</button>`}
    </section>
    <section class="panel">
      ${tutorPack ? `<label class="field"><span>Имя (его видит репетитор)</span><input id="name" value="${esc(prog.name)}"></label>` : ''}
      <label class="field"><span>Новых карточек в день</span>
        <input id="daily" type="number" min="0" max="50" value="${pack.daily || NEW_DEFAULT}" ${tutorPack ? 'disabled' : ''}></label>
      ${tutorPack ? '<p class="muted">Норму задаёт репетитор</p>' : ''}
      <button class="btn primary" id="save">Сохранить</button>
    </section>
    <section class="panel tg-panel" id="tg-box" hidden></section>
    <section class="panel">
      <h2 id="cal-h">Напоминание</h2>
      <p class="muted">Добавит в календарь телефона ежедневное событие со звуком и ссылкой на тренажёр.</p>
      <div class="row"><input id="remind-time" type="time" value="${esc(store.get('zd-remind-time', '19:00'))}" class="time-input">
        <button class="btn" id="remind">Добавить в календарь</button></div>
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
  $app.querySelector('#login')?.addEventListener('click', () => loginDialog({
    role: 'student',
    why: 'Прогресс, серия и ошибки сохранятся в аккаунте.',
    onDone: async () => { await addRole('student'); await pullProg(); sync(true); if (pack.limited) location.reload(); else viewMe(); },
  }));
  $app.querySelector('#logout')?.addEventListener('click', async () => { if (progDirty && prog) await pushProg(); await logout(); viewMe(); });
  $app.querySelector('#pcode')?.addEventListener('click', async () => {
    try {
      const { code } = await api('/me/parent-code', { method: 'POST' });
      const where = new URL('login.html?role=parent', location.href.split('#')[0].split('?')[0]).href;
      modal(`<h3>Код для родителя</h3><div class="code-big">${esc(code)}</div>
        <p>Родитель открывает <b>${esc(where)}</b>, входит и вводит этот код. Код действует сутки и подходит один раз.</p>
        <p class="muted">Родитель будет видеть дни занятий, точность и темы, которые стоит подтянуть.</p>`);
    } catch (err) { toast(err.message); }
  });
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
  $app.querySelector('#remind').onclick = () => {
    const time = $app.querySelector('#remind-time').value || '19:00';
    store.set('zd-remind-time', time);
    addReminder(time);
  };
  // Telegram: сразу из сохранённого, потом — свежий ответ сервера
  const fillTg = tg => {
    const box = $app.querySelector('#tg-box');
    if (!box) return; // ученик уже ушёл с профиля
    const html = tgPanel(tg);
    box.innerHTML = html;
    box.hidden = !html;
    $app.querySelector('#cal-h').textContent = html ? 'Или напоминание в календаре' : 'Напоминание';
    box.querySelector('#tg-off')?.addEventListener('click', async e => {
      e.target.disabled = true;
      try {
        await api(`/packs/${encodeURIComponent(ref.slice(2))}/notify/off`, { method: 'POST', body: { sid: prog.sid } });
        // Не перечитываем: копия KV в этом регионе может отставать до минуты и показать «Включены»
        store.set(tgKey(), { ...tgState(), on: false, at: null, chk: Date.now() });
        toast('Напоминания выключены');
      } catch (err) { toast(err.message); }
      fillTg(tgState());
    });
    box.querySelector('#tg-on')?.addEventListener('click', () => {
      tgPend();
      // Вернулся из Telegram — показываем, включилось ли
      const back = () => {
        if (document.visibilityState !== 'visible') return;
        document.removeEventListener('visibilitychange', back);
        refreshTg().then(t => { if (t) fillTg(t); });
      };
      document.addEventListener('visibilitychange', back);
    });
  };
  fillTg(tgState());
  refreshTg().then(tg => { if (tg) fillTg(tg); });
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
  $app.querySelector('#code').onkeydown = e => { if (e.key === 'Enter') join(); };
}

function viewName() {
  $app.innerHTML = `
    ${brandHeader()}
    <section class="panel intro">
      <p>${esc(pack.tutor || 'Репетитор')} собрал для тебя тренажёр: ${plural(pack.cards.length, 'карточка', 'карточки', 'карточек')}.
      Занимайся по 10 минут в день — репетитор будет видеть прогресс и знать, что разобрать на уроке.</p>
      <label class="field"><span>Как тебя зовут?</span><input id="name" placeholder="Имя и фамилия" autocomplete="name"></label>
      <button class="btn primary big" id="ok">Начать</button>
      ${signedIn() ? '' : '<p class="center small-note"><button class="link-btn" id="login">Уже занимался? Войти в аккаунт</button></p>'}
    </section>`;
  $app.querySelector('#login')?.addEventListener('click', () => loginDialog({
    role: 'student',
    why: 'Прогресс подтянется с другого устройства.',
    onDone: async () => { await addRole('student'); await pullProg(); if (prog.name) { save(); sync(true); } route(); },
  }));
  const ok = () => {
    const name = $app.querySelector('#name').value.trim();
    if (!name) return toast('Напиши имя, чтобы репетитор тебя узнал');
    prog.name = name;
    save();
    // Сервер узнал ученика — ссылка в бота будет готова уже к концу первого занятия
    checkAdopted(name).then(() => { save(); return sync(true); }).then(() => { if (tgStale()) refreshTg(); });
    route();
  };
  $app.querySelector('#ok').onclick = ok;
  $app.querySelector('#name').onkeydown = e => { if (e.key === 'Enter') ok(); };
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
  if (view === 'go' || view === 'hw') return openFromBot(view);
  if (view === 'library') return viewLibrary();
  if (view === 'topic') return viewTopic(arg);
  if (view === 'lesson') return viewLesson(arg);
  if (view === 'course') return viewCourse();
  if (view === 'c') return viewCourseLesson(arg);
  if (view === 'me') return viewMe();
  viewHome();
}

// Ссылки из бота: #/go — сразу занятие дня, #/hw — задание. Адрес сразу заменяем на главную,
// чтобы «Назад» и обновление страницы не начинали занятие заново
function openFromBot(view) {
  history.replaceState(null, '', location.pathname + location.search + '#/');
  if (view === 'hw') return pack.hw ? startHw() : viewHome();
  const q = buildQueue('daily');
  if (q.length) return startSession(q, 'Занятие');
  viewHome();
  toast('На сегодня всё — возвращайся завтра');
}

function applyBrand() {
  document.title = pack.title;
  if (pack.color) {
    document.documentElement.style.setProperty('--accent', pack.color);
    document.querySelector('meta[name=theme-color]')?.setAttribute('content', pack.color);
  }
}

async function init() {
  const redirected = await finishRedirectLogin(); // вернулись от Яндекса/VK/Google
  if (redirected?.role) await addRole(redirected.role);
  await finishPayment(); // вернулись с оплаты — пакет ниже загрузится уже полным
  const params = new URLSearchParams(location.search);
  const recent = store.get('zd-recent', []);
  // sid из кнопки бота — сразу убираем из адреса: скопированная или пересланная ссылка его не разнесёт
  const sidFromBot = params.get('s');
  if (sidFromBot !== null) {
    const u = new URL(location.href);
    u.searchParams.delete('s');
    history.replaceState(null, '', u);
  }
  // ?about — лендинг для репетиторов даже у тех, кто уже занимается в каком-то наборе
  ref = params.has('about') ? null : params.get('t') ? 't:' + params.get('t') : params.get('p') || recent[0]?.ref || null;
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
  if (ref.startsWith('t:')) adoptSid(sidFromBot);
  // «Новых в день» в открытых наборах ученик задаёт сам, в наборе репетитора — репетитор
  if (!ref.startsWith('t:')) pack.daily = store.get('zd-daily:' + ref, pack.daily);
  applyBrand();
  route();
  if (await pullProg() && !document.querySelector(".card")) route();
  await sync(false);
  // Включены ли напоминания в Telegram и ссылка в бота — раз в сутки
  if (tgStale()) refreshTg();
}

init();
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
