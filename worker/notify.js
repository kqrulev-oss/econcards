/* ============================================================
   Уведомления в Telegram: напоминания ученикам, отчёты родителям,
   задания и служебные сообщения репетитору
   ------------------------------------------------------------
   PUT|DELETE /packs/:id/hw          задание тренажёра (X-Key или сессия владельца)
   GET  /packs/:id/notify?sid=       включены ли напоминания ученика + ссылка s_ в бота
   POST /packs/:id/notify/off        ученик выключает напоминания (отметка nt:x:s)
   POST /packs/:id/notify/parent     репетитор: ссылка r_ для родителя (7 дней)
   POST /packs/:id/notify/parent-off репетитор гасит отчёты ученика и старые ссылки r_
   GET  /me/notify?tz=               репетитор: подключён ли бот + ссылка t_ (60 минут)
   runNotify                         cron каждые 5 минут
   handleNotifyUpdate                вебхук: /start s_|r_|t_, /settings, /stop, /dz, n:*, dz:*

   KV: nt:list {v, at, e:[{i,k,c,p,s,a,n,tz,m,sk,at}]} — индекс подписок. Пишет ТОЛЬКО
       вебхук бота, синхронно, при max_connections 1: второй писатель потерял бы чужие
       изменения. Сайт отключает подписки отметками nt:x:<s|r>:<pack>:<sid> (ms, 400 дней),
       cron — списком nt:gone {e:[i], at}; вебхук выбрасывает их при следующей записи.
       hw:<pack> — задание (живёт до срока + 31 день), hwp:<pack> — время рассылок снятого задания (сутки),
       lim:full:<pack>:<день> — T-full раз в сутки.
   Отправка сообщения ничего не пишет в KV. Без parse_mode: текст людей не становится разметкой.
   ============================================================ */
import { AuthError, getAccount, planStatus, sessionAccount, randomId, botName } from './auth.js';

const DAY = 864e5;
const WIN = [540, 1260];                      // шлём только 09:00–20:59 местного времени
// all: при 2000 записях запись индекса ещё укладывается в 10 мс CPU; дальше — делить по UTC-часу (v2)
const LIMIT = { all: 2000, chat: 10, s: 3, r: 4 };
const RUN = { subs: 60, msgs: 45, par: 6 };   // за запуск cron: Free — 50 подзапросов на вызов
const HOUR = { s: 19, r: 18, t: 10 };         // час слота по умолчанию
const HOURS = [16, 17, 18, 19, 20];           // ученик выбирает час напоминания
const R_LINK = 7 * DAY, T_LINK = 3600e3;
const MARK_TTL = 400 * 86400;
const DEAD = 'dead';

const SITE = env => env.SITE_URL || 'https://econcards.kqrulev.workers.dev';
const payUrl = env => `${SITE(env)}/cabinet/?pay=tutor#tutor`;
const cut = (s, n) => String(s ?? '').slice(0, n);
const mod = (a, n) => ((a % n) + n) % n;
const pad = n => String(n).padStart(2, '0');
const first = name => String(name || '').trim().split(/\s+/)[0].slice(0, 40);
const end = s => /[.!?…]$/.test(s) ? s : s + '.';
const validSid = sid => /^[a-z0-9]{6,20}$/.test(sid || '');

// Местная минута суток и номер дня (тот же счёт, что lib.day() на устройстве)
export const lmin = (t, tz) => mod(Math.floor(t / 6e4) + tz, 1440);
export const lday = (t, tz) => Math.floor((t + tz * 6e4) / DAY);
const inWin = m => m >= WIN[0] && m < WIN[1];
// Пояс кратен 15 минутам: тогда слот (кратен 5) попадает ровно в один запуск cron за сутки
export const normTz = tz => {
  const n = Number(tz);
  return tz == null || tz === '' || !Number.isFinite(n) ? 180 : Math.max(-720, Math.min(840, Math.round(n / 15) * 15));
};

// ---------- тексты: свои склонения и даты, без Intl ----------

export const plural = (n, one, few, many) => {
  const m10 = n % 10, m100 = n % 100;
  return `${n} ${m10 === 1 && m100 !== 11 ? one : m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20) ? few : many}`;
};
const cards = n => plural(n, 'карточку', 'карточки', 'карточек');
const days = n => plural(n, 'день', 'дня', 'дней');
const WD = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб'];
const MON = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
export const dueDay = due => { const [y, m, d] = String(due).split('-').map(Number); return Date.UTC(y, m - 1, d) / DAY; };
const dayIso = L => new Date(L * DAY).toISOString().slice(0, 10);
const dateOf = L => { const d = new Date(L * DAY); return `${d.getUTCDate()} ${MON[d.getUTCMonth()]}`; };
const dateWd = L => `${WD[new Date(L * DAY).getUTCDay()]}, ${dateOf(L)}`;
export const dueText = due => dateWd(dueDay(due));

export const HELLO = `Это бот «Между уроками». Ученикам он напоминает о тренажёре и присылает задания репетитора, родителям — отчёт о занятиях по воскресеньям, репетиторам — задания командой /dz и сообщения о тарифе.

Как подключить:
• ученику — в тренажёре: Профиль → «Напоминания в Telegram»;
• родителю — по ссылке от репетитора;
• репетитору — в студии: «Подключить Telegram».

/settings — что включено, /stop — отключить всё.`;
export const DESCRIPTION = 'Напоминания о занятиях, задания репетитора и отчёты для родителей от «Между уроками». Пишем только по делу, не чаще раза в день и не ночью. Отключить — /stop.';
export const SHORT_DESCRIPTION = 'Напоминания, задания и отчёты «Между уроками»';
const TXT = {
  sBad: 'Ссылка не подошла. Открой тренажёр → Профиль → «Напоминания в Telegram» и нажми кнопку ещё раз.',
  sNoProg: 'Сначала реши несколько карточек в тренажёре, потом нажми «Напоминания в Telegram» ещё раз.',
  pair: 'К этому тренажёру уже подключено несколько чатов. Лишний можно отключить в /settings.',
  chat: 'В этом чате уже 10 подписок. Лишние можно отключить в /settings.',
  sFull: 'Сейчас не получается включить напоминания — попробуй завтра.',
  full: 'Сейчас не получается подключить — попробуйте завтра.',
  sFail: 'Не получилось сохранить — попробуй ещё раз через минуту.',
  fail: 'Не получилось сохранить — попробуйте ещё раз через минуту.',
  rBad: 'Ссылка не подошла или устарела (она действует 7 дней). Попросите у репетитора новую.',
  rOff: 'Отчёты по этому тренажёру сейчас не отправляются. Спросите репетитора.',
  tBad: 'Ссылка устарела (она действует час). Нажмите «Подключить Telegram» в студии ещё раз.',
  stopped: 'Готово: больше ничего не пришлю. Включить снова можно в тренажёре («Напоминания в Telegram»), по ссылке от репетитора или в студии.',
  nothing: 'Сейчас ничего не включено — я и так молчу.',
  empty: 'Сейчас ничего не включено. Ученику — в тренажёре: Профиль → «Напоминания в Telegram». Родителю — по ссылке от репетитора. Репетитору — в студии: «Подключить Telegram».',
  notTutor: 'Задавать задания из Telegram могут репетиторы. Подключите бота: студия → «Подключить Telegram».',
  noAccess: 'Нет доступа к этому тренажёру',
};
const trainer = title => title ? `тренажёр «${title}»` : 'твой тренажёр';

// ---------- Telegram ----------

async function tg(env, method, body) {
  try {
    const r = await fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/${method}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    return await r.json().catch(() => ({ ok: false, error_code: r.status }));
  } catch (err) {
    console.error('tg', method, err?.message);
    return { ok: false };
  }
}
const send = (env, chat, text, rows) => tg(env, 'sendMessage', {
  chat_id: chat, text: cut(text, 4000), disable_web_page_preview: true, ...(rows ? { reply_markup: { inline_keyboard: rows } } : {}),
});
// Пачки по 6 — не чаще раза в 250 мс: иначе 45 сообщений уходят за полсекунды, а Telegram
// пускает боту ~30 в секунду, и всё после первого 429 теряется
const pause = () => new Promise(ok => setTimeout(ok, 250));
// 403 — бот заблокирован, 400 «chat not found» — чата больше нет: подписка мёртвая
const deadChat = r => r.error_code === 403 || (r.error_code === 400 && /chat not found/i.test(r.description || ''));

// ---------- ссылки в бота: подпись HMAC вместо записей в KV ----------

let hkey = null;
async function hmac(env, text) {
  if (hkey?.s !== env.TG_SECRET) {
    hkey = { s: env.TG_SECRET, k: await crypto.subtle.importKey('raw', new TextEncoder().encode(env.TG_SECRET), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']) };
  }
  return new Uint8Array(await crypto.subtle.sign('HMAC', hkey.k, new TextEncoder().encode(text)));
}
const sig10 = async (env, fields) => [...await hmac(env, 'nt|' + fields.join('|'))].slice(0, 5).map(b => b.toString(16).padStart(2, '0')).join('');
/* sid в ссылке r_ скрыт: её пересылают родителю, а sid — бессрочный ключ к записи ученика (GET notify,
   POST progress). Маска — поток HMAC от (набор, срок, подпись): тот же алфавит и длина, записей в KV нет;
   испорченная маска даёт другой sid, и подпись не сходится. dir: 1 — скрыть, −1 — открыть */
const A36 = '0123456789abcdefghijklmnopqrstuvwxyz';
async function maskSid(env, pack, sid, exp, sig, dir) {
  const ks = await hmac(env, `rk|${pack}|${exp}|${sig}`);
  return [...sid].map((c, j) => A36[mod(A36.indexOf(c) + dir * ks[j], 36)]).join('');
}
// s_{pack}_{sid}_{sig} | r_{pack}_{маска sid}_{exp36}_{sig} | t_{acct}_{tz36}_{exp36}_{sig}; вид ссылки входит в подпись
export async function startParam(env, k, fields) {
  const sig = await sig10(env, [k, ...fields]);
  const f = k === 'r' ? [fields[0], await maskSid(env, fields[0], fields[1], fields[2], sig, 1), fields[2]] : fields;
  return `${k}_${f.join('_')}_${sig}`;
}
const exp36 = ms => Math.floor(ms / 6e5).toString(36);
const tz36 = tz => (normTz(tz) / 15 + 48).toString(36).padStart(2, '0');
const START = {
  s: /^s_([a-z0-9-]{4,40})_([a-z0-9]{6,20})_([0-9a-f]{10})$/,
  r: /^r_([a-z0-9-]{4,40})_([a-z0-9]{6,20})_([0-9a-z]{1,9})_([0-9a-f]{10})$/,
  t: /^t_([a-z0-9]{6,20})_([0-9a-z]{2})_([0-9a-z]{1,9})_([0-9a-f]{10})$/,
};
// null — формат или подпись не сошлись; срок (exp, ms) проверяет вызывающий
export async function parseStart(env, arg) {
  const k = String(arg || '')[0], m = START[k]?.exec(arg);
  if (!m || !env.TG_SECRET) return null;
  const f = m.slice(1, -1);
  if (k === 'r') f[1] = await maskSid(env, f[0], f[1], f[2], m.at(-1), -1);
  if (m.at(-1) !== await sig10(env, [k, ...f])) return null;
  if (k === 's') return { k, p: f[0], s: f[1] };
  if (k === 'r') return { k, p: f[0], s: f[1], exp: parseInt(f[2], 36) * 6e5 };
  return { k, a: f[0], tz: (parseInt(f[1], 36) - 48) * 15, exp: parseInt(f[2], 36) * 6e5 };
}
const tme = (bot, param) => bot && param && param.length <= 64 ? `https://t.me/${bot}?start=${param}` : null;

// ---------- индекс nt:list ----------

let mem = null; // последняя версия индекса в этом изоляте: KV может отдать копию старее
async function loadIndex(env) {
  const [idx, gone] = await Promise.all([env.DB.get('nt:list', 'json'), env.DB.get('nt:gone', 'json')]);
  const fresh = mem && mem.v > (idx?.v || 0) ? mem : idx?.e ? idx : { v: 0, at: 0, e: [] };
  return { idx: fresh, gone: new Set(gone?.e || []), goneList: gone?.e || [] };
}

/* Вебхук идёт в одно соединение (max_connections 1): один чат, который шлёт /start и /stop
   без остановки, задерживал бы всех, и вход через Telegram тоже. Поэтому в памяти изолята —
   не больше 3 записей индекса в минуту от чата. Если KV ответил «чаще раза в секунду»
   (класс подписывается разом), ждём 1,1 с и повторяем — подписка не падает. */
const edits = new Map();
function tooOften(chat, now) {
  if (chat == null) return false;
  const a = (edits.get(chat) || []).filter(t => now - t < 60e3);
  if (a.length >= 3) return true;
  if (edits.size > 5000) edits.clear();
  edits.set(chat, [...a, now]);
  return false;
}
// Записи индекса — плоские объекты из чисел и строк: сравниваем по полям, без JSON всего индекса
const sameEntry = (a, b) => { const ka = Object.keys(a); return ka.length === Object.keys(b).length && ka.every(k => a[k] === b[k]); };

/* Единственная запись nt:list — отсюда, из вебхука бота. fn меняет копию (ix.e) и возвращает
   результат; мёртвые из nt:gone выбрасываются. Нет изменений — не пишем. chat — чей запрос
   (для ограничения выше; у блокировки бота его нет). KV держит одну запись в секунду на ключ:
   при ошибке ждём 1,1 с и повторяем один раз, вторая ошибка — наружу. Ошибку вызывающие
   показывают как «Не получилось сохранить — попробуйте через минуту». */
async function editIndex(env, fn, chat = null) {
  const { idx, gone } = await loadIndex(env);
  const orig = idx.e.filter(e => !gone.has(e.i));
  const ix = { e: orig.map(e => ({ ...e })), gone };
  const res = await fn(ix);
  if (ix.e.length === orig.length && ix.e.every((e, j) => sameEntry(e, orig[j]))) return res;
  const now = Date.now();
  if (tooOften(chat, now)) throw new Error('nt:list: too often from ' + chat);
  const next = { v: idx.v + 1, at: now, e: ix.e };
  const body = JSON.stringify(next);
  try {
    await env.DB.put('nt:list', body);
  } catch (err) {
    console.error('nt:list put', err?.message);
    await new Promise(ok => setTimeout(ok, 1100));
    await env.DB.put('nt:list', body);
  }
  mem = next;
  return res;
}

// Слот: из двенадцати 5-минутных слотов часа H — тот, где меньше всего подписок с тем же UTC-слотом
export function pickSlot(list, H, tz, self = null) {
  const used = new Map();
  for (const e of list) if (e !== self) { const u = mod(e.m - e.tz, 1440); used.set(u, (used.get(u) || 0) + 1); }
  let best = H * 60, min = Infinity;
  for (let m = H * 60; m < H * 60 + 60; m += 5) {
    const n = used.get(mod(m - tz, 1440)) || 0;
    if (n < min) { min = n; best = m; }
  }
  return best;
}

function newId(ix) {
  let i;
  do i = randomId(6); while (ix.e.some(e => e.i === i) || ix.gone.has(i));
  return i;
}

/* Подписка. Тот же (k,c,p,s) или (t,a) заменяет запись: слот и sk остаются. live(e) — действует
   ли запись (не отключена отметкой nt:x); уже действующую и неизменную не трогаем — записи не будет.
   Отключённая и включённая снова получает новый i: nt:gone помнит только i, и запоздалый приговор
   cron старой записи иначе навсегда убил бы новую после «Готово!». */
function subscribe(ix, add, live) {
  const key = e => e.k === add.k && (add.k === 't' ? e.a === add.a : e.c === add.c && e.p === add.p && e.s === add.s);
  // Отключённые с сайта подписки того же ученика из других чатов больше не нужны — не занимают места
  if (add.k !== 't') ix.e = ix.e.filter(e => !(e.k === add.k && e.p === add.p && e.s === add.s && e.c !== add.c && !live(e)));
  const same = ix.e.find(key);
  const inChat = ix.e.filter(e => e.c === add.c).length;
  if (same) {
    const was = live(same);
    if (same.c !== add.c && inChat >= LIMIT.chat) return { err: 'chat' };
    if (!was || same.c !== add.c || same.tz !== add.tz || same.n !== add.n) Object.assign(same, add);
    if (!was) same.i = newId(ix);
    return { e: same, was };
  }
  if (ix.e.length >= LIMIT.all) { console.error('nt:list full', ix.e.length); return { err: 'full' }; }
  if (inChat >= LIMIT.chat) return { err: 'chat' };
  if (add.k !== 't' && ix.e.filter(e => e.k === add.k && e.p === add.p && e.s === add.s).length >= LIMIT[add.k]) return { err: 'pair' };
  const e = { i: newId(ix), ...add, m: pickSlot(ix.e, HOUR[add.k], add.tz) };
  ix.e.push(e);
  return { e, was: false };
}

// Название и репетитор из метаданных pack:<id>: тело набора (до 5 МБ) не читаем
async function packMeta(env, id) {
  const r = await env.DB.getWithMetadata(`pack:${id}`, { type: 'stream' }).catch(() => null);
  r?.value?.cancel?.().catch?.(() => {});
  return r?.value ? r.metadata || {} : null;
}

// ---------- задание ----------

const pub = hw => { const { bc, pings, ...rest } = hw; return rest; };

// GET /packs/:id: задание вставляем в строку набора, не разбирая её
export function withHw(pack, raw) {
  if (!raw) return pack;
  try {
    return pack.slice(0, pack.lastIndexOf('}')) + ',"hw":' + JSON.stringify(pub(JSON.parse(raw))) + '}';
  } catch { return pack; }
}

/* Отметки nt:x пачками по 100 ключей: пачка — одна операция из 1000 на вызов, а по одной на ученика
   вкладка «Ученики» большого тренажёра упиралась в лимит. Без пачек (старый рантайм, заглушка) — по одной */
async function getMarks(env, keys) {
  const all = [...new Set(keys)], marks = {};
  const parts = [];
  for (let j = 0; j < all.length; j += 100) parts.push(all.slice(j, j + 100));
  await Promise.all(parts.map(async ks => {
    let got = null;
    try { got = await env.DB.get(ks); } catch { /* по одной ниже */ }
    if (got instanceof Map) for (const k of ks) marks[k] = Number(got.get(k)) || 0;
    else await Promise.all(ks.map(async k => { marks[k] = Number(await env.DB.get(k)) || 0; }));
  }));
  return marks;
}

// Действующие s-подписки набора (не мёртвые и новее отметки nt:x:s)
async function liveSubs(env, id, idx, gone) {
  const subs = idx.e.filter(e => e.k === 's' && e.p === id && !gone.has(e.i));
  const marks = await getMarks(env, subs.map(e => `nt:x:s:${id}:${e.s}`));
  return subs.filter(e => e.at > marks[`nt:x:s:${id}:${e.s}`]);
}

async function setHw(env, id, b, by, bg) {
  const goal = Number(b.goal);
  if (!Number.isInteger(goal) || goal < 1 || goal > 200) throw new AuthError(400, 'Сколько карточек — от 1 до 200.');
  const now = Date.now(), today = Math.floor(now / DAY);
  const due = String(b.due || '');
  const dd = /^\d{4}-\d{2}-\d{2}$/.test(due) ? dueDay(due) : NaN;
  if (!(dd >= today - 1 && dd <= today + 90) || dayIso(dd) !== due) throw new AuthError(400, 'Срок — не раньше сегодняшнего дня и не позже чем через 90 дней.');
  const raw = typeof b.text === 'string' ? b.text.trim() : '';
  if (raw.length > 300) throw new AuthError(400, 'Текст задания — до 300 символов.');
  const topic = b.topic == null || b.topic === '' ? null : String(b.topic);
  if (topic !== null && !/^[\w-]{1,40}$/.test(topic)) throw new AuthError(400, 'Некорректная тема.');
  // Тема только в неопубликованных правках студии: у учеников по ней нет карточек, задание не сделать.
  // Ищем в строке набора карточку этой темы, без разбора JSON (id темы — [\w-], экранировать нечего)
  if (topic !== null && !(await env.DB.get(`pack:${id}`) || '').includes(`"t":"${topic}"`)) {
    throw new AuthError(400, 'Этой темы нет у учеников — сначала опубликуйте правки.');
  }
  const topicTitle = topic && b.topicTitle ? cut(String(b.topicTitle).trim(), 80) || null : null;
  const text = raw || `Решить ${cards(goal)}${topicTitle ? ` по теме «${topicTitle}»` : ''}`;
  // То же задание, сохранённое повторно в течение 10 минут (двойное нажатие), заново не рассылаем
  const old = await env.DB.get(`hw:${id}`, 'json');
  // Задание сняли — время его рассылок лежит в hwp:<id>: «снять и задать» не обходит лимит 3 в сутки
  const prev = old ? null : await env.DB.get(`hwp:${id}`, 'json');
  if (old && now - old.set < 600e3 && old.text === text && old.topic === topic && old.goal === goal && old.due === due) {
    return { hw: pub(old), repeat: true, tg: { now: 0, later: 0 } };
  }
  const { idx, gone } = await loadIndex(env);
  const live = await liveSubs(env, id, idx, gone);
  const day = live.filter(e => inWin(lmin(now, e.tz)));
  // Не больше 3 рассылок в сутки на тренажёр и 45 сообщений за раз; остальные — вечерним напоминанием
  const pings = (old?.pings || prev || []).filter(p => now - p < DAY);
  const to = pings.length < 3 ? day.slice(0, RUN.msgs) : [];
  const hw = { id: 'h' + randomId(6), text, topic, topicTitle, goal, due, set: now, tutor: cut(b.tutor, 80), title: cut(b.title, 80), by,
    bc: pings.length < 3 && day.length <= RUN.msgs, pings: to.length ? [...pings, now] : pings };
  // Старое задание исчезает само через месяц после срока — удалять не нужно
  await env.DB.put(`hw:${id}`, JSON.stringify(hw), { expirationTtl: Math.max(60, Math.ceil((dd + 31) * 86400 - now / 1000)) });
  if (to.length) bg(broadcastHw(env, id, hw, to, !raw));
  return { hw: pub(hw), repeat: false, tg: { now: to.length, later: live.length - to.length } };
}

/* «Новое задание» сразу тем, у кого сейчас день; по 6 параллельно с паузой, на 429 останавливаемся.
   В кнопке — sid ученика: бот открывает тренажёр и там, где ученик ещё не занимался (приложение
   на домашнем экране iPhone, браузер Telegram), и сервер видит того же ученика, а не нового */
export async function broadcastHw(env, id, hw, to, auto) {
  const text = `Новое задание от репетитора:\n${hw.text}\n\n`
    + (auto ? `Срок — до ${dueText(hw.due)}.` : `Решить ${cards(hw.goal)}${hw.topicTitle ? ` по теме «${hw.topicTitle}»` : ''}, срок — до ${dueText(hw.due)}.`);
  let stop = false;
  for (let j = 0; j < to.length && !stop; j += RUN.par) {
    await Promise.all(to.slice(j, j + RUN.par).map(async e => {
      const r = await send(env, e.c, text, [[{ text: 'Делать задание', url: `${SITE(env)}/?t=${id}&s=${e.s}#/hw` }], [{ text: 'Не напоминать', callback_data: `n:off:${e.i}` }]]);
      if (r.error_code === 429) stop = true;
    }));
    if (!stop && j + RUN.par < to.length) await pause();
  }
}

// ---------- решения cron: что написать ученику, родителю, репетитору ----------

// Сводка ученика на местный день L: days — 14 значений, последнее относится к дню stats.day
function activity(st, L) {
  const D = Number.isInteger(st.day) ? st.day : null;
  const arr = Array.isArray(st.days) ? st.days : [];
  let last = null;
  if (D !== null) for (let j = arr.length - 1; j >= 0; j--) if (arr[j] > 0) { last = D - (arr.length - 1 - j); break; }
  const today = D !== null && D >= L ? st.today?.d || arr.at(-1) || 0 : 0;
  const idle = last === null ? 99 : Math.max(0, L - last);
  return { D, arr, last, today, idle, streak: last !== null && last >= L - 1 ? st.streak || 0 : 0 };
}

function hwState(hw, st, L, t, tz) {
  if (!hw) return {};
  const d = st.hw?.id === hw.id ? Math.max(0, Math.floor(st.hw.d) || 0) : 0;
  const due = dueDay(hw.due), live = d < hw.goal && L <= due + 3;
  return { d, due, live, soon: live && (due - L === 0 || due - L === 1),
    fresh: live && st.hw?.id !== hw.id && t - hw.set < 36 * 3600e3 && (!hw.bc || !inWin(lmin(hw.set, tz))) };
}
const hwNewText = (hw, h) => `Новое задание от репетитора: ${end(hw.text)} Срок — до ${dueText(hw.due)}, сделано ${h.d} из ${hw.goal}.`;

export function decideS(env, e, prog, hw, t) {
  const st = prog.stats || {};
  const tz = normTz(st.tz ?? e.tz);
  if (!inWin(lmin(t, tz))) return null; // устройство ученика в другом поясе, и у него сейчас ночь
  const L = lday(t, tz), a = activity(st, L), h = hwState(hw, st, L, t, tz);
  const name = first(prog.name) || e.n, title = cut(st.title || hw?.title, 80);
  const line = !h.live ? '' : '\n\n' + (h.fresh ? hwNewText(hw, h)
    : h.due === L ? `Сегодня последний день задания: ${hw.text} — сделано ${h.d} из ${hw.goal}.`
      : `Задание до ${dueText(hw.due)}: ${hw.text} — сделано ${h.d} из ${hw.goal}.`);
  let text, aboutHw = h.live;
  if (a.idle > 15) {
    if (!h.fresh) return null;
    text = hwNewText(hw, h);
  } else if (a.today === 0 && (a.idle <= 3 || [6, 9, 12, 15].includes(a.idle))) {
    if (a.idle === 15) { text = `${name}, пока не буду напоминать каждый день. Захочешь вернуться — тренажёр на месте, а новые задания репетитора я пришлю.${h.fresh ? line : ''}`; aboutHw = h.fresh; }
    else if (a.idle > 3) text = `${name}, уже ${days(a.idle)} без карточек. Начни с 5 минут — повторим то, что успело подзабыться.${line}`;
    else if (a.streak >= 2 && a.idle <= 1) text = `${name}, серия ${days(a.streak)} — не прерывай её сегодня. 10 минут карточек, и день засчитан.${line}`;
    else text = `${name}, 10 минут карточек сегодня? ${title ? `Тренажёр «${title}» ждёт.` : 'Тренажёр ждёт.'}${line}`;
  } else if (h.fresh) text = hwNewText(hw, h);
  else if (h.soon) text = `${name}, задание нужно сделать ${h.due === L ? 'сегодня' : 'до завтра'}: ${hw.text} — сделано ${h.d} из ${hw.goal}.`;
  else return null;
  // sid в кнопке — как в broadcastHw
  return { e, text, rows: [[{ text: 'Открыть тренажёр', url: `${SITE(env)}/?t=${e.p}&s=${e.s}#/${aboutHw ? 'hw' : 'go'}` }], [{ text: 'Не напоминать', callback_data: `n:off:${e.i}` }]] };
}

// Динамика точности: эта неделя против предыдущей активной (как trend() в студии)
function trend(st) {
  const acc = w => w?.d ? Math.round(w.ok / w.d * 100) : null;
  const ws = (st.weeks || []).filter(w => w.d);
  if (ws.length < 2 || !st.weeks.at(-1).d) return '';
  const now = acc(st.weeks.at(-1)), before = acc(ws.at(-2));
  if (now === null || before === null) return '';
  const diff = now - before;
  return diff > 0 ? ` (было ${before}%, +${diff})` : diff < 0 ? ` (было ${before}%)` : ' (как и неделей раньше)';
}

// Отчёт родителю (R-week, а без занятий за 7 дней — R-none): те же строки, что parentReport() в студии
export function parentReportText(prog, hw, L, p) {
  const st = prog.stats || {}, a = activity(st, L);
  const name = first(prog.name), title = cut(st.title || hw?.title, 80) || p, tutor = cut(st.tutor || hw?.tutor, 80);
  const shift = a.D === null ? 14 : Math.max(0, Math.min(14, L - a.D));
  const week = [...a.arr.slice(shift), ...Array(shift).fill(0)].slice(-7);
  const k = week.filter(n => n > 0).length, n = week.reduce((s, x) => s + (Number(x) || 0), 0);
  const d = hw ? (st.hw?.id === hw.id ? Math.max(0, Math.floor(st.hw.d) || 0) : 0) : 0;
  // ДЗ курса (уроки внутри набора) считает телефон ученика: только целые, onTime ≤ n — как в studio courseDone
  const cn = Math.max(0, Math.floor(st.course?.n) || 0), ct = Math.min(cn, Math.max(0, Math.floor(st.course?.onTime) || 0));
  if (!k) {
    return `${name} на этой неделе не занимался(ась) в тренажёре «${title}».${a.last !== null ? ` Последнее занятие — ${dateOf(a.last)}.` : ''}`
      + (hw ? `\nЗадание репетитора «${hw.text}» до ${dueText(hw.due)}: сделано ${d} из ${hw.goal}.` : '')
      + (cn ? `\nДЗ курса: ${ct} из ${cn} в срок.` : '') + (tutor ? `\n\n${tutor}` : '');
  }
  const acc = st.week?.d ? Math.round(st.week.ok / st.week.d * 100) : 0;
  const weak = Array.isArray(st.weak) ? st.weak.slice(0, 3).map(w => cut(w?.t, 60)).filter(Boolean) : null;
  return [
    `${name} — тренажёр «${title}», последние 7 дней:`,
    `• занимался(ась) ${days(k)} из 7, решено ${plural(n, 'задание', 'задания', 'заданий')};`,
    `• точность ${acc}%${trend(st)}, серия без пропусков — ${days(a.streak)};`,
    `• освоено ${st.mastered || 0} из ${st.total || 0} карточек курса${hw || cn ? ';' : '.'}`,
    ...(hw ? [`• задание репетитора «${hw.text}» до ${dueText(hw.due)}: сделано ${d} из ${hw.goal}${d >= hw.goal ? ' — выполнено' : ''}${cn ? ';' : '.'}`] : []),
    ...(cn ? [`• ДЗ курса: ${ct} из ${cn} в срок.`] : []),
    // Старые версии приложения не присылают слабые темы — строку тогда не пишем, чтобы не соврать
    ...(weak ? [weak.length ? `Что подтягиваем на занятиях: ${weak.join(', ')}.` : 'Слабых тем сейчас нет — держим темп.'] : []),
    tutor ? `\n${tutor}` : '',
  ].join('\n').trim();
}

// Родителю: в воскресенье отчёт, в остальные дни — одно сообщение на 3-й день без занятий
export function decideR(env, e, prog, hw, t) {
  const st = prog.stats || {};
  const tz = normTz(st.tz ?? e.tz);
  if (!inWin(lmin(t, tz))) return null;
  const L = lday(t, tz), a = activity(st, L);
  let text;
  if (mod(L + 4, 7) === 0) { // 1 января 1970 — четверг
    if (a.last === null || L - a.last > 28) return null;
    text = parentReportText(prog, hw, L, e.p);
  } else if (a.idle === 3 && a.arr.filter(n => n > 0).length >= 2) {
    const d = hw && st.hw?.id === hw.id ? Math.max(0, Math.floor(st.hw.d) || 0) : 0;
    text = `${first(prog.name)} не занимается в тренажёре «${cut(st.title || hw?.title, 80) || e.p}» уже 3 дня.`
      + (hw ? ` Задание репетитора: ${hw.text} — сделано ${d} из ${hw.goal}, срок до ${dueText(hw.due)}.` : '')
      + ' Иногда достаточно просто спросить, как дела с подготовкой.';
  } else return null;
  return { e, text, rows: [[{ text: 'Отписаться от отчётов', callback_data: `n:off:${e.i}` }]] };
}

// Репетитору в 10:xx его времени: пробный кончится через 2 дня, оплата — через 3 или 1 день, тариф кончился вчера
export function decideT(env, e, acct, t) {
  const st = planStatus(acct, 'tutor', t);
  const L = lday(t, e.tz), on = ms => lday(ms, e.tz);
  let text, btn = 'Продлить';
  if (st.trial && on(st.trialEnd) - L === 2) {
    text = `Пробный период студии закончится ${dateWd(on(st.trialEnd))} (через 2 дня). После — бесплатно 1 тренажёр и до 3 учеников в нём, а отчёты родителям в Telegram будут приостановлены. Автосписаний нет.`;
    btn = 'Выбрать тариф';
  } else if (!st.trial && st.paidUntil > t && [1, 3].includes(on(st.paidUntil) - L)) {
    text = `Тариф репетитора оплачен до ${dateWd(on(st.paidUntil))} (осталось ${on(st.paidUntil) - L === 1 ? '1 день' : '3 дня'}). Автосписаний нет — продлите, чтобы новые ученики могли присоединяться, а родители получали отчёты.`;
  } else if (st.until > 0 && !st.active && L === on(st.until) + 1) {
    text = `Тариф репетитора закончился ${dateWd(on(st.until))}. Ученики занимаются как раньше, но новые сверх трёх не смогут присоединиться, а отчёты родителям в Telegram приостановлены до продления.`;
  } else return null;
  return { e, text: `${text}\n\nОтключить — /stop.`, rows: [[{ text: btn, url: payUrl(env) }]] };
}

// ---------- cron ----------

/* Каждые 5 минут. В большинстве запусков — 2 чтения и выход. Каждая подписка привязана к одному
   5-минутному слоту местного дня и попадает ровно в один запуск. Ни одного list, ни pack:<id>,
   ни progress:*; не больше 60 подписок и 45 сообщений; запись — только nt:gone, и то не всегда. */
export async function runNotify(env, t = Date.now()) {
  if (!env.DB || !env.TG_TOKEN) return null;
  const ops = { reads: 2, writes: 0 };
  const { idx, gone, goneList } = await loadIndex(env);
  const rank = { t: 0, r: 1, s: 2 };
  let due = idx.e.filter(e => !gone.has(e.i) && lmin(t, e.tz) === e.m && inWin(e.m) && lday(t, e.tz) !== e.sk);
  if (!due.length) return { due: 0, sent: 0, dead: 0, ...ops };
  // Переполненный слот каждый день режет другой хвост: иначе одни и те же подписки (новые, в конце
  // индекса) не получали бы ничего и не проверялись бы на смерть. Сортировка по виду устойчивая
  const off = mod(Math.floor(t / DAY) * RUN.msgs, due.length);
  due = [...due.slice(off), ...due.slice(0, off)].sort((a, b) => rank[a.k] - rank[b.k]);
  if (due.length > RUN.subs) { console.error('notify overflow', { due: due.length, t }); due = due.slice(0, RUN.subs); }
  const memo = new Map();
  const read = (k, type) => { if (!memo.has(k)) { ops.reads++; memo.set(k, env.DB.get(k, type)); } return memo.get(k); };
  const decide = async e => {
    if (e.k === 't') {
      const acct = await read(`acct:${e.a}`, 'json');
      return acct?.roles?.tutor ? decideT(env, e, acct, t) : DEAD;
    }
    const [prog, mark, hw] = await Promise.all([read(`prog:${e.p}:${e.s}`, 'json'), read(`nt:x:${e.k}:${e.p}:${e.s}`), read(`hw:${e.p}`, 'json')]);
    if (!prog || Number(mark) > e.at) return DEAD;
    if (e.k === 's') return decideS(env, e, prog, hw, t);
    const msg = decideR(env, e, prog, hw, t);
    if (!msg) return null;
    // Родителю — только пока у репетитора активен тариф (у старых наборов без packacct — всегда); про оплату не пишем
    const owner = await read(`packacct:${e.p}`);
    return !owner || planStatus(await read(`acct:${owner}`, 'json'), 'tutor', t).active ? msg : null;
  };
  const res = await Promise.all(due.map(e => decide(e).catch(err => { console.error('notify', e.i, err?.message); return null; })));
  const dead = due.filter((e, j) => res[j] === DEAD).map(e => e.i);
  const msgs = res.filter(r => r && r !== DEAD);
  if (msgs.length > RUN.msgs) console.error('notify overflow', { msgs: msgs.length, t });
  let sent = 0, stop = false;
  const list = msgs.slice(0, RUN.msgs);
  for (let j = 0; j < list.length && !stop; j += RUN.par) {
    await Promise.all(list.slice(j, j + RUN.par).map(async m => {
      const r = await send(env, m.e.c, m.text, m.rows);
      if (r.ok) sent++;
      else if (deadChat(r)) dead.push(m.e.i);
      else if (r.error_code === 429) stop = true; // остальное — в следующий раз, без повторов
    }));
    if (!stop && j + RUN.par < list.length) await pause();
  }
  // nt:gone пишет только cron, раз за запуск и только с новыми мёртвыми; из прежних — те, что ещё в индексе
  if (dead.length) {
    const inList = new Set(idx.e.map(e => e.i));
    await env.DB.put('nt:gone', JSON.stringify({ e: [...new Set([...goneList.filter(i => inList.has(i)), ...dead])], at: t }));
    ops.writes++;
  }
  const out = { due: due.length, sent, dead: dead.length, ...ops };
  console.log('notify', { t, ...out });
  return out;
}

// ---------- сайт: задание, выключатель, ссылки ----------

const readBody = async req => {
  const t = await req.text();
  if (t.length > 4000) throw new AuthError(413, 'Слишком большой запрос.');
  try { return t ? JSON.parse(t) : {}; } catch { throw new AuthError(400, 'Некорректный запрос.'); }
};

// Запросы /packs/:id/hw и /packs/:id/notify*; owner() — проверка доступа к набору (requireOwner)
export async function handleNotify(req, env, id, parts, ctx, owner) {
  const [, , what, sub] = parts, m = req.method;
  const bg = p => ctx?.waitUntil(p.catch(err => console.error('notify', err?.message)));
  if (parts.length > 4) throw new AuthError(404, 'Нет такого адреса.');

  if (what === 'hw' && !sub && m === 'PUT') {
    await owner();
    const b = await readBody(req);
    if (!b.title || !b.tutor) { const meta = await packMeta(env, id); b.title ||= meta?.t; b.tutor ||= meta?.u; }
    return setHw(env, id, b, 'studio', bg);
  }
  if (what === 'hw' && !sub && m === 'DELETE') {
    await owner();
    // Время рассылок переживает снятие задания (сутки): лимит 3 в сутки не обойти «снять — задать»
    const old = await env.DB.get(`hw:${id}`, 'json');
    const pings = (old?.pings || []).filter(p => Date.now() - p < DAY);
    if (pings.length) await env.DB.put(`hwp:${id}`, JSON.stringify(pings), { expirationTtl: 86400 });
    await env.DB.delete(`hw:${id}`);
    return { ok: true };
  }
  if (what !== 'notify') throw new AuthError(404, 'Нет такого адреса.');

  // Ученик без входа: включены ли напоминания и готовая ссылка в бота
  if (!sub && m === 'GET') {
    const q = new URL(req.url).searchParams, sid = q.get('sid');
    if (!validSid(sid)) throw new AuthError(400, 'Некорректный запрос.');
    const [{ idx, gone }, mark, bot, prog] = await Promise.all([loadIndex(env), env.DB.get(`nt:x:s:${id}:${sid}`),
      env.TG_TOKEN && env.TG_SECRET ? botName(env) : null,
      // who=1 — приложение сверяет имя, прежде чем принять sid из кнопки бота (сообщение могли переслать)
      q.get('who') ? env.DB.get(`prog:${id}:${sid}`, 'json') : null]);
    const e = idx.e.filter(x => x.k === 's' && x.p === id && x.s === sid && !gone.has(x.i) && x.at > (Number(mark) || 0)).at(-1);
    return { on: !!e, at: e ? `${pad(Math.floor(e.m / 60))}:00` : null, link: bot ? tme(bot, await startParam(env, 's', [id, sid])) : null,
      ...(q.get('who') ? { name: prog ? first(prog.name) : null } : {}) };
  }
  if (m !== 'POST' || !['off', 'parent', 'parent-off'].includes(sub)) throw new AuthError(404, 'Нет такого адреса.');
  if (sub !== 'off') await owner();
  const { sid } = await readBody(req);
  if (!validSid(sid)) throw new AuthError(400, 'Некорректный запрос.');

  // Выключатель в тренажёре: одна отметка, и только если есть что выключать
  if (sub === 'off') {
    const [{ idx, gone }, mark] = await Promise.all([loadIndex(env), env.DB.get(`nt:x:s:${id}:${sid}`)]);
    if (idx.e.some(e => e.k === 's' && e.p === id && e.s === sid && !gone.has(e.i) && e.at > (Number(mark) || 0))) {
      await env.DB.put(`nt:x:s:${id}:${sid}`, String(Date.now()), { expirationTtl: MARK_TTL });
    }
    return { ok: true };
  }
  const [{ idx, gone }, mark] = await Promise.all([loadIndex(env), env.DB.get(`nt:x:r:${id}:${sid}`)]);
  const m0 = Number(mark) || 0;
  const parents = idx.e.filter(e => e.k === 'r' && e.p === id && e.s === sid && !gone.has(e.i) && e.at > m0).length;
  if (sub === 'parent-off') {
    await env.DB.put(`nt:x:r:${id}:${sid}`, String(Date.now()), { expirationTtl: MARK_TTL });
    return { ok: true, off: parents };
  }
  const [prog, acctId] = await Promise.all([env.DB.get(`prog:${id}:${sid}`), env.DB.get(`packacct:${id}`)]);
  if (!prog) throw new AuthError(404, 'Ученик не найден.');
  if (acctId && !planStatus(await getAccount(env, acctId), 'tutor').active) {
    throw new AuthError(402, 'Отчёты родителям в Telegram входят в тариф репетитора. Продлите тариф — и ссылка появится.');
  }
  const bot = env.TG_TOKEN && env.TG_SECRET && await botName(env);
  if (!bot) throw new AuthError(503, 'Telegram-бот не настроен.');
  // Ссылка, выданная раньше отметки отключения, не принимается. Срок хранится в 10-минутных долях,
  // поэтому новую ссылку делаем «выданной» не раньше отметки — иначе она не сработала бы 10 минут
  const exp = Math.max(Math.floor((Date.now() + R_LINK) / 6e5), Math.ceil((m0 + R_LINK) / 6e5));
  const link = tme(bot, await startParam(env, 'r', [id, sid, exp.toString(36)]));
  if (!link) throw new AuthError(400, 'Код тренажёра слишком длинный для ссылки в Telegram.');
  return { link, expires: exp * 6e5, parents };
}

// GET /me/notify: подключён ли репетитор к боту и свежая ссылка t_ на час
export async function meNotify(env, req) {
  const acct = await sessionAccount(env, req);
  if (!acct) throw new AuthError(401, 'Нужно войти.');
  const tz = normTz(new URL(req.url).searchParams.get('tz'));
  const [{ idx, gone }, bot] = await Promise.all([loadIndex(env), env.TG_TOKEN ? botName(env) : null]);
  const e = idx.e.find(x => x.k === 't' && x.a === acct.id && !gone.has(x.i));
  const link = acct.roles?.tutor && bot && env.TG_SECRET ? tme(bot, await startParam(env, 't', [acct.id, tz36(tz), exp36(Date.now() + T_LINK)])) : null;
  return { bot: bot ? '@' + bot : null, tutor: { on: !!e, at: e ? `${pad(Math.floor(e.m / 60))}:00` : null }, link };
}

// GET /packs/:id/progress: флаги tg и parents у учеников и текущее задание
export async function progressFlags(env, id, students) {
  const [hw, { idx, gone }] = await Promise.all([env.DB.get(`hw:${id}`, 'json'), loadIndex(env)]);
  const mine = idx.e.filter(e => e.p === id && (e.k === 's' || e.k === 'r') && !gone.has(e.i));
  const marks = await getMarks(env, mine.map(e => `nt:x:${e.k}:${id}:${e.s}`));
  const live = e => e.at > marks[`nt:x:${e.k}:${id}:${e.s}`];
  for (const s of students) {
    s.tg = mine.some(e => e.k === 's' && e.s === s.sid && live(e));
    s.parents = mine.filter(e => e.k === 'r' && e.s === s.sid && live(e)).length;
  }
  return { students, hw: hw ? pub(hw) : null };
}

/* 402 на новом ученике: репетитору T-full сразу, днём и не чаще раза в сутки на тренажёр.
   Запрос без входа, поэтому из него — только имя, и то одними буквами: Telegram не сделает из
   него ссылку, @упоминание или команду. Название — из метаданных набора. full — параллельные 402
   в одном изоляте: оба прочли бы пустой lim:full до записи и прислали бы два сообщения */
const full = new Set();
export async function alertTutorFull(env, pack, name) {
  if (!env.TG_TOKEN) return;
  const owner = await env.DB.get(`packacct:${pack}`);
  if (!owner) return;
  const { idx, gone } = await loadIndex(env);
  const e = idx.e.find(x => x.k === 't' && x.a === owner && !gone.has(x.i));
  const now = Date.now();
  if (!e || !inWin(lmin(now, e.tz))) return;
  const k = `lim:full:${pack}:${Math.floor(now / DAY)}`;
  if (full.has(k)) return;
  if (full.size > 1000) full.clear();
  full.add(k);
  if (await env.DB.get(k)) return;
  await env.DB.put(k, '1', { expirationTtl: 172800 });
  const t = cut((await packMeta(env, pack))?.t, 80) || pack;
  const who = cut(String(name || '').replace(/\s+/g, ' ').replace(/[^\p{L} '-]/gu, '').trim(), 40);
  await send(env, e.c, `${who ? `Новый ученик «${who}»` : 'Новый ученик'} хочет заниматься в тренажёре «${t}», но на бесплатном тарифе — до 3 учеников в тренажёре. Продлите тариф — место откроется сразу, ученику ничего не нужно делать заново.\n\nОтключить — /stop.`,
    [[{ text: 'Продлить тариф', url: payUrl(env) }]]);
}

// Владельцу, /notify
export async function notifyStats(env) {
  const { idx, gone } = await loadIndex(env);
  const live = idx.e.filter(e => !gone.has(e.i));
  const n = k => live.filter(e => e.k === k).length;
  return `Уведомления: напоминания учеников — ${n('s')}, отчёты родителям — ${n('r')}, репетиторов — ${n('t')}, чатов — ${new Set(live.map(e => e.c)).size}, ждут удаления — ${idx.e.length - live.length}. Проверка каждые 5 минут, до ${RUN.msgs} сообщений за раз.`;
}

// ---------- бот ----------

// Что из вебхука относится к уведомлениям (только личные чаты)
export function isNotifyUpdate(upd) {
  if (upd.my_chat_member) return upd.my_chat_member.chat?.type === 'private';
  const msg = upd.message, q = upd.callback_query;
  if (msg) return msg.chat?.type === 'private' && /^\/(start [srt]_|(stop|settings|dz)(@\w+)?(\s|$))/.test((msg.text || '').trim());
  return !!q && q.message?.chat?.type === 'private' && /^(n|dz):/.test(q.data || '');
}

const hourRow = i => HOURS.map(H => ({ text: `${H}:00`, callback_data: `n:h:${i}:${H}` }));

/* Вебхук. Всё, что меняет nt:list (/start s_|r_|t_, /stop, n:h, n:off, n:all, блокировка бота),
   выполняется до ответа Telegram; ответы в чат и /dz — в ctx.waitUntil. */
export async function handleNotifyUpdate(env, upd, ctx) {
  const bg = p => ctx.waitUntil(Promise.resolve(p).catch(err => console.error('notify', err?.message)));
  if (upd.my_chat_member) {
    const m = upd.my_chat_member;
    // Бота заблокировали: удаляем все подписки чата и ничего не отвечаем
    if (m.chat?.type === 'private' && m.new_chat_member?.status === 'kicked') {
      await editIndex(env, ix => { ix.e = ix.e.filter(e => e.c !== m.chat.id); });
    }
    return;
  }
  if (upd.callback_query) return onButton(env, upd.callback_query, bg, ctx);
  const chat = upd.message.chat.id;
  const [cmd, arg = ''] = (upd.message.text || '').trim().split(/\s+/);
  const reply = (text, rows) => bg(send(env, chat, text, rows));
  const c = cmd.replace(/@\w+$/, '');
  if (c === '/start') return onStart(env, chat, arg, reply, bg);
  if (c === '/stop') {
    const n = await dropChat(env, chat).catch(err => { console.error('notify stop', err?.message); return -1; });
    return reply(n < 0 ? TXT.fail : n ? TXT.stopped : TXT.nothing);
  }
  if (c === '/settings') return bg(settings(env, chat));
  if (c === '/dz') return bg(dzStart(env, chat));
}

const dropChat = (env, chat) => editIndex(env, ix => { const n = ix.e.length; ix.e = ix.e.filter(e => e.c !== chat); return n - ix.e.length; }, chat);

async function onStart(env, chat, arg, reply, bg) {
  const now = Date.now(), lk = await parseStart(env, arg), k = arg[0];
  const save = async (add, live) => {
    try { return await editIndex(env, ix => subscribe(ix, add, live), chat); } catch (err) { console.error('notify save', err?.message); return { err: 'fail' }; }
  };
  const oops = (err, kind) => reply(err === 'pair' ? TXT.pair : err === 'chat' ? TXT.chat
    : err === 'full' ? (kind === 's' ? TXT.sFull : TXT.full) : kind === 's' ? TXT.sFail : TXT.fail);

  if (k === 's') {
    if (!lk) return reply(TXT.sBad);
    const [prog, mark] = await Promise.all([env.DB.get(`prog:${lk.p}:${lk.s}`, 'json'), env.DB.get(`nt:x:s:${lk.p}:${lk.s}`)]);
    if (!prog) return reply(TXT.sNoProg);
    const title = cut(prog.stats?.title, 80) || cut((await packMeta(env, lk.p))?.t, 80);
    const r = await save({ k: 's', c: chat, p: lk.p, s: lk.s, n: first(prog.name), tz: normTz(prog.stats?.tz), at: now }, e => e.at > (Number(mark) || 0));
    if (r.err) return oops(r.err, 's');
    const H = pad(Math.floor(r.e.m / 60));
    return reply(r.was ? `Напоминания уже включены: ${trainer(title)}, около ${H}:00.`
      : `Готово! Буду напоминать про ${trainer(title)} около ${H}:00, если в этот день ещё не было занятия, и присылать задания репетитора.\n\nПишу не чаще раза в день и только с 9:00 до 21:00. Время — кнопками ниже или в /settings, отключить — /stop.`,
    [hourRow(r.e.i), [{ text: 'Выключить', callback_data: `n:off:${r.e.i}` }]]);
  }

  if (k === 'r') {
    if (!lk || lk.exp < now) return reply(TXT.rBad);
    const [prog, mark, hw, owner] = await Promise.all([env.DB.get(`prog:${lk.p}:${lk.s}`, 'json'), env.DB.get(`nt:x:r:${lk.p}:${lk.s}`),
      env.DB.get(`hw:${lk.p}`, 'json'), env.DB.get(`packacct:${lk.p}`)]);
    const m0 = Number(mark) || 0;
    // Репетитор отключил отчёты ученика — ссылки, выданные до этого, больше не работают
    if (!prog || lk.exp - R_LINK < m0) return reply(TXT.rBad);
    if (owner && !planStatus(await getAccount(env, owner), 'tutor').active) return reply(TXT.rOff);
    const st = prog.stats || {}, tz = normTz(st.tz);
    // Отчёт уходит сразу — сегодня cron его не повторяет (в воскресенье до 18:00 было бы два)
    const r = await save({ k: 'r', c: chat, p: lk.p, s: lk.s, n: first(prog.name), tz, at: now, sk: lday(now, tz) }, e => e.at > m0);
    if (r.err) return oops(r.err, 'r');
    const meta = st.title && st.tutor ? {} : await packMeta(env, lk.p) || {};
    const title = cut(st.title || hw?.title || meta.t, 80) || lk.p, tutor = cut(st.tutor || hw?.tutor || meta.u, 80);
    const name = first(prog.name);
    const report = parentReportText({ ...prog, stats: { ...st, title, tutor } }, hw, lday(now, tz), lk.p);
    // Сначала подтверждение, следом — текущий отчёт
    return bg((async () => {
      await send(env, chat, `Вы подписались на отчёты о занятиях: ${name}, тренажёр «${title}»${tutor ? `, репетитор ${tutor}` : ''}.\n\nПо воскресеньям около 18:00 — отчёт за неделю: дни занятий, точность, задание репетитора и темы, которые стоит подтянуть. И одно сообщение, если ${name} не занимается 3 дня подряд. Ночью не пишем.\n\nОтписаться — кнопкой под отчётом или командой /stop.`);
      await send(env, chat, report, [[{ text: 'Отписаться от отчётов', callback_data: `n:off:${r.e.i}` }]]);
    })());
  }

  // t_: ссылка репетитора живёт час и выдаётся только в сессию с ролью tutor
  if (!lk || lk.exp < now) return reply(TXT.tBad);
  const acct = await getAccount(env, lk.a);
  if (!acct?.roles?.tutor) return reply(TXT.tBad);
  const r = await save({ k: 't', c: chat, a: acct.id, n: cut(acct.name, 40), tz: normTz(lk.tz), at: now }, () => true);
  if (r.err) return oops(r.err, 't');
  return reply(`Готово! Аккаунт репетитора${acct.name ? ' ' + acct.name : ''} подключён.\n\nЗдесь можно задавать задания ученикам — команда /dz. Ещё напишу, если новый ученик не может присоединиться к тренажёру, и за несколько дней до конца тарифа. Сообщения — с 9:00 до 21:00.\n\nОтключить — /stop.`);
}

// /settings: подписки чата, отключённые на сайте не показываем
async function settings(env, chat) {
  const { idx, gone } = await loadIndex(env);
  const rank = { s: 0, r: 1, t: 2 };
  const mine = idx.e.filter(e => e.c === chat && !gone.has(e.i)).sort((a, b) => rank[a.k] - rank[b.k]);
  const info = await Promise.all(mine.map(async e => {
    if (e.k === 't') return { e };
    const [prog, mark] = await Promise.all([env.DB.get(`prog:${e.p}:${e.s}`, 'json'), env.DB.get(`nt:x:${e.k}:${e.p}:${e.s}`)]);
    if (!prog || Number(mark) > e.at) return null;
    return { e, title: cut(prog.stats?.title, 80) || cut((await packMeta(env, e.p))?.t, 80) || `Тренажёр ${e.p}` };
  }));
  const rows = info.filter(Boolean);
  if (!rows.length) return send(env, chat, TXT.empty);
  const lines = rows.map(({ e, title }, j) => `${j + 1}. ` + (e.k === 's' ? `Напоминания: ${e.n} · «${title}» · около ${pad(Math.floor(e.m / 60))}:00`
    : e.k === 'r' ? `Отчёты по воскресеньям: ${e.n} · «${title}»` : `Репетитор: ${e.n} · задания /dz и сообщения о тарифе`));
  const kb = rows.map(({ e }, j) => [
    ...(e.k === 's' ? [{ text: `${j + 1}. Время`, callback_data: `n:t:${e.i}` }] : []),
    { text: `${j + 1}. Выключить`, callback_data: `n:off:${e.i}` },
  ]);
  return send(env, chat, `Что сейчас включено:\n${lines.join('\n')}`, [...kb, [{ text: 'Выключить всё', callback_data: 'n:all' }]]);
}

async function onButton(env, q, bg, ctx) {
  const chat = q.message.chat.id, mid = q.message.message_id, data = q.data || '';
  const answer = text => tg(env, 'answerCallbackQuery', { callback_query_id: q.id, ...(text ? { text } : {}) });
  const unkb = () => tg(env, 'editMessageReplyMarkup', { chat_id: chat, message_id: mid, reply_markup: { inline_keyboard: [] } });
  if (data.startsWith('dz:')) return bg(dzButton(env, q, answer, ctx));
  let m;
  // Любая кнопка n:* меняет только подписки того чата, который её нажал
  if ((m = /^n:off:([a-z0-9]{6})$/.exec(data))) {
    let e;
    try { e = await editIndex(env, ix => { const x = ix.e.find(y => y.i === m[1] && y.c === chat); if (x) ix.e = ix.e.filter(y => y !== x); return x; }, chat); }
    catch (err) { console.error('notify off', err?.message); return bg(answer(TXT.fail)); }
    if (!e) return bg(answer('Уже отключено'));
    return bg(Promise.all([answer('Отключено'), unkb(), (async () => {
      if (e.k === 'r') return send(env, chat, `Вы отписались от отчётов про ${e.n}. Подписаться снова можно по новой ссылке от репетитора.`);
      if (e.k === 't') return send(env, chat, 'Аккаунт репетитора отключён от бота. Подключить снова — в студии: «Подключить Telegram».');
      const prog = await env.DB.get(`prog:${e.p}:${e.s}`, 'json');
      const title = cut(prog?.stats?.title, 80);
      return send(env, chat, `Напоминания про ${title ? `«${title}»` : 'тренажёр'} выключены. Включить снова — в тренажёре: Профиль → «Напоминания в Telegram».`);
    })()]));
  }
  if ((m = /^n:h:([a-z0-9]{6}):(1[6-9]|20)$/.exec(data))) {
    const H = Number(m[2]);
    let e;
    try {
      e = await editIndex(env, ix => {
        const x = ix.e.find(y => y.i === m[1] && y.c === chat && y.k === 's');
        if (!x || Math.floor(x.m / 60) === H) return x;
        const now = Date.now(), lm = lmin(now, x.tz), L = lday(now, x.tz), to = pickSlot(ix.e, H, x.tz, x);
        // Старый слот сегодня уже прошёл, а новый впереди — сегодня не пишем, иначе было бы два сообщения
        if (x.sk !== L) delete x.sk;
        if (lm >= x.m && to > lm) x.sk = L;
        x.m = to;
        return x;
      }, chat);
    } catch (err) { console.error('notify hour', err?.message); return bg(answer(TXT.fail)); }
    if (!e) return bg(answer('Уже отключено'));
    return bg(Promise.all([answer(`Буду напоминать около ${pad(H)}:00`),
      tg(env, 'editMessageText', { chat_id: chat, message_id: mid, text: `Готово: напоминания около ${pad(H)}:00.` })]));
  }
  if ((m = /^n:t:([a-z0-9]{6})$/.exec(data))) {
    return bg((async () => {
      const { idx, gone } = await loadIndex(env);
      const e = idx.e.find(y => y.i === m[1] && y.c === chat && y.k === 's' && !gone.has(y.i));
      if (!e) return answer('Уже отключено');
      await answer();
      return tg(env, 'editMessageReplyMarkup', { chat_id: chat, message_id: mid, reply_markup: { inline_keyboard: [hourRow(e.i)] } });
    })());
  }
  if (data === 'n:all') {
    const n = await dropChat(env, chat).catch(err => { console.error('notify all', err?.message); return -1; });
    return bg(Promise.all([answer(n < 0 ? TXT.fail : n ? 'Отключено' : 'Уже отключено'), n >= 0 && unkb(),
      n >= 0 && send(env, chat, n ? TXT.stopped : TXT.nothing)]));
  }
  return bg(answer());
}

// ---------- /dz: задание в три нажатия ----------

// Кнопки dz:* — только репетитору этого набора: t-подписка чата, набор в acctpacks и packacct совпадает
async function dzAccess(env, chat, pack) {
  const [{ idx, gone }, owner] = await Promise.all([loadIndex(env), env.DB.get(`packacct:${pack}`)]);
  const e = owner && idx.e.find(x => x.k === 't' && x.c === chat && x.a === owner && !gone.has(x.i));
  if (!e) return null;
  const mine = (await env.DB.get(`acctpacks:${owner}`, 'json')) || [];
  return mine.includes(pack) ? e : null;
}

async function dzStart(env, chat) {
  const { idx, gone } = await loadIndex(env);
  const ts = idx.e.filter(x => x.k === 't' && x.c === chat && !gone.has(x.i));
  if (!ts.length) return send(env, chat, TXT.notTutor);
  const packs = [...new Set((await Promise.all(ts.map(e => env.DB.get(`acctpacks:${e.a}`, 'json')))).flatMap(l => l || []))].reverse().slice(0, 8);
  if (!packs.length) return send(env, chat, `У вас пока нет опубликованных тренажёров. Создайте тренажёр в студии: ${SITE(env)}/studio/`);
  const metas = await Promise.all(packs.map(p => packMeta(env, p)));
  return send(env, chat, 'Какому тренажёру задать задание?', packs.map((p, j) => [{ text: cut(metas[j]?.t, 60) || `Тренажёр ${p}`, callback_data: `dz:p:${p}` }]));
}

async function dzButton(env, q, answer, ctx) {
  const chat = q.message.chat.id, mid = q.message.message_id;
  const edit = (text, rows) => tg(env, 'editMessageText', { chat_id: chat, message_id: mid, text, disable_web_page_preview: true,
    ...(rows ? { reply_markup: { inline_keyboard: rows } } : {}) });
  if (q.data === 'dz:x') return Promise.all([answer(), edit('Отменено.')]);
  const m = /^dz:(p|n|k|ok):([a-z0-9-]{4,40})(?::(\d{1,3}))?(?::([137]))?$/.exec(q.data);
  const n = Number(m?.[3]), k = Number(m?.[4]);
  const valid = m && (m[1] === 'p' ? !m[3] : n >= 1 && n <= 200 && (m[1] === 'n' ? !m[4] : k > 0));
  const e = valid && await dzAccess(env, chat, m[2]);
  if (!e) return answer(TXT.noAccess);
  const pack = m[2], meta = await packMeta(env, pack) || {};
  const title = cut(meta.t, 80) || `Тренажёр ${pack}`;
  await answer();
  if (m[1] === 'p') {
    const hw = await env.DB.get(`hw:${pack}`, 'json');
    return edit(`«${title}»${hw ? ` — сейчас: ${hw.text} до ${dueText(hw.due)}` : ''}. Сколько карточек решить?\nСвоё задание с текстом и темой — в студии, вкладка «Ученики».`,
      [[10, 20, 30, 50].map(x => ({ text: String(x), callback_data: `dz:n:${pack}:${x}` }))]);
  }
  if (m[1] === 'n') {
    return edit('Срок?', [[{ text: 'Завтра', callback_data: `dz:k:${pack}:${n}:1` }, { text: 'Через 3 дня', callback_data: `dz:k:${pack}:${n}:3` },
      { text: 'Через неделю', callback_data: `dz:k:${pack}:${n}:7` }]]);
  }
  // День срока — по поясу репетитора
  const due = dayIso(lday(Date.now(), e.tz) + k), date = dueText(due);
  if (m[1] === 'k') {
    return edit(`Задать: решить ${cards(n)} в «${title}» до ${date}? Ученики с Telegram получат сообщение сразу, если у них день.`,
      [[{ text: 'Задать', callback_data: `dz:ok:${pack}:${n}:${k}` }, { text: 'Отмена', callback_data: 'dz:x' }]]);
  }
  const tutor = meta.u || (await getAccount(env, e.a))?.name;
  const res = await setHw(env, pack, { goal: n, due, tutor, title: meta.t }, 'tg', p => ctx.waitUntil(p.catch(err => console.error('notify hw', err?.message))));
  if (res.repeat) return edit('Это задание уже выдано.');
  await edit(`Задание выдано: решить ${cards(n)} в «${title}» до ${date}. В Telegram сейчас: ${res.tg.now}${res.tg.later ? `; ещё ${res.tg.later} — с вечерним напоминанием` : ''}. Остальные увидят задание в тренажёре. Перешлите сообщение ниже тем, у кого нет бота.`);
  return send(env, chat, `Задание по «${title}»: решить ${cards(n)} до ${date}. Открыть тренажёр: ${SITE(env)}/?t=${pack}#/hw`);
}
