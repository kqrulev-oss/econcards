/* ============================================================
   Между уроками — сервер на Cloudflare Worker
   ------------------------------------------------------------
   POST /ai                       ИИ: check | hint | explain | similar | generate
   GET  /packs/:id                набор репетитора (открыт по ссылке)
   PUT  /packs/:id                сохранить набор (X-Key; первый PUT задаёт ключ)
   POST /packs/:id/progress       ученик присылает сводку прогресса
   GET  /packs/:id/progress       репетитор смотрит учеников (X-Key)
   /packs/:id/hw, /packs/:id/notify*, GET /me/notify, cron
                                  задания и уведомления в Telegram (worker/notify.js)
   /pay/*                         тарифы и оплата ЮKassa (worker/billing.js)
   /auth/*, /me/*                 аккаунты: вход, облачная копия (worker/auth.js)
   /tg, /tg/setup, /gh            Telegram-бот для задач Claude и Codex (worker/bot.js)

   Переменные (см. worker/README.md):
     GEMINI_KEY  — секрет, ключ Google AI Studio (обязательно для ИИ)
     MODEL       — модель Gemini (по умолч. gemini-flash-latest, запасная —
                   gemini-flash-lite-latest)
     DAILY_LIMIT — лимит ИИ-запросов на IP в сутки (по умолч. 60)
     DB          — KV-namespace: наборы, прогресс, лимиты (обязательно)
   ============================================================ */

import { handleBot } from './bot.js';
import { handleAuth, sessionAccount, parentCode, planStatus, saveAccount, getAccount } from './auth.js';
import { handleBilling, checkPublish, checkNewStudent, trimLibrary, LIB_PACKS } from './billing.js';
import { handleNotify, withHw, progressFlags, alertTutorFull, meNotify, runNotify } from './notify.js';

// «-latest» — псевдонимы Google на актуальную модель: конкретные версии
// закрывают для новых ключей (так случилось с gemini-2.5-flash)
const MODEL_DEFAULT = 'gemini-flash-latest';
const MODEL_FALLBACK = 'gemini-flash-lite-latest';
const PLAIN = ' Пиши простым текстом: без Markdown (никаких **, #, списков со звёздочками) и без LaTeX ($…$) — формулы вроде Qd = 100 − 2P.';
const MAX = 4000;           // обрезаем входы проверок, чтобы не жечь токены
const MAX_MATERIAL = 30000; // материалы репетитора для генерации
const MAX_PACK = 5e6;       // байт на набор
const MAX_STATS = 20000;    // байт на сводку ученика
const MAX_REQUEST_AI = 15e6; // генерация с PDF и фото

const cors = origin => ({
  'Access-Control-Allow-Origin': origin || '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, X-Key, Authorization',
  'Access-Control-Max-Age': '86400',
});
const cut = (s, n = MAX) => String(s || '').slice(0, n);

class HttpError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

const SYSTEM = {
  check: 'Ты доброжелательный, но требовательный репетитор. Тебе дают условие задачи, ЭТАЛОННОЕ решение и решение ученика. Сверь ход ученика с эталоном: отметь, что сделано верно, укажи конкретные ошибки и где именно, подскажи направление (не переписывай весь эталон, если ученик близок). В конце дай оценку в процентах. Кратко и по делу, по-русски. Формулы — обычным текстом.',
  hint: 'Ты репетитор. Дай РОВНО ОДНУ подсказку запрошенного уровня, НЕ раскрывая финальный ответ. Уровень 1 — идея или направление; уровень 2 — ключевой шаг; уровень 3 — почти полное решение, но без итогового ответа. Кратко, по-русски.',
  explain: 'Ты репетитор. Переобъясни эталонное решение ПРОЩЕ, чем в оригинале: другими словами, с интуицией и аналогией, по понятным шагам. По-русски.',
  similar: 'Ты делаешь КЛОН задачи-образца для тренировки. Меняй ТОЛЬКО числовые значения, сохраняя формулировку, структуру и метод решения. Подбери числа так, чтобы ответ был аккуратным. Затем реши клон тем же методом по шагам. По-русски. Формат: «Задача: …\\n\\nРешение: …\\n\\nОтвет: …».',
  generate: `Ты методист. Из материалов репетитора сделай карточки для тренажёра ученика.
Правила:
- Опирайся ТОЛЬКО на материалы: не выдумывай фактов, правил и чисел, которых там нет.
- Одна карточка — одна проверяемая мысль. Формулировки короткие и однозначные.
- Если в материалах есть задачи с решениями — переноси их как карточки типа "open" с полным решением в "a".
- Для правил, определений и фактов делай "one" (4 варианта, один верный) или "flip" (вопрос → короткий ответ).
- Если ответ задачи — одно число (целое или конечная десятичная дробь), делай "num": в "a" только число, например "0,35".
- "many" — только если верных вариантов действительно несколько.
- Неверные варианты должны быть правдоподобными — типичные ошибки учеников.
- В "e" коротко объясни, почему ответ верный (1–2 предложения).
- Раздели карточки на 2–6 тем по смыслу материала.
- Тексты карточек — простым текстом, без Markdown и LaTeX.
- Не придумывай задач на вычисления, которых нет в материалах. Если в карточке есть расчёт — перепроверь каждое действие; сомневаешься в ответе — не делай такую карточку.
Верни ТОЛЬКО JSON:
{"topics":[{"id":"t1","title":"…"}],
 "cards":[{"t":"t1","k":"one","q":"…","o":[{"id":"а","t":"…"},{"id":"б","t":"…"},{"id":"в","t":"…"},{"id":"г","t":"…"}],"a":"б","e":"…"},
          {"t":"t1","k":"many","q":"…","o":[…],"a":["а","в"],"e":"…"},
          {"t":"t2","k":"flip","q":"…","a":"…"},
          {"t":"t2","k":"num","q":"задача с числовым ответом","a":"12","e":"решение"},
          {"t":"t2","k":"open","q":"…","a":"полное решение с ответом"}]}`,
};
for (const task of ['check', 'hint', 'explain', 'similar']) SYSTEM[task] += PLAIN;

// Вложения к генерации: PDF и фото страниц (base64), не больше 10 штук
const ATTACH_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif'];
const attachments = d => (Array.isArray(d.files) ? d.files : [])
  .filter(f => f && ATTACH_TYPES.includes(f.mime) && typeof f.data === 'string' && f.data.length > 0)
  .slice(0, 10);

const PROMPT = {
  check: d => `Условие:\n${cut(d.problem)}\n\nЭталонное решение:\n${cut(d.reference)}\n\nРешение ученика:\n${cut(d.answer)}\n\nПроверь решение ученика.`,
  hint: d => `Условие:\n${cut(d.problem)}\n\nЭталонное решение (ученику не показывай):\n${cut(d.reference)}\n\nДай подсказку уровня ${Math.max(1, Math.min(3, Number(d.level) || 1))}.`,
  explain: d => `Условие:\n${cut(d.problem)}\n\nЭталонное решение:\n${cut(d.reference)}\n\nПереобъясни это решение проще.`,
  similar: d => `Задача-образец:\n${cut(d.problem)}\n\nЭталонное решение:\n${cut(d.reference)}\n\nСделай клон: замени ТОЛЬКО числа и реши заново тем же способом.`,
  generate: d => `Предмет: ${cut(d.subject, 100) || 'не указан'}\nУровень учеников: ${cut(d.level, 100) || 'не указан'}\nСколько карточек: около ${Math.max(5, Math.min(40, Number(d.count) || 15))}\n\nМатериалы:\n${cut(d.material, MAX_MATERIAL) || '(только во вложениях)'}${attachments(d).length ? `\n\nЕщё ${attachments(d).length} вложени(я) — PDF или фото страниц: прочитай их полностью, включая рукописный текст, таблицы и формулы.` : ''}`,
};

async function gemini(env, task, body) {
  if (!env.GEMINI_KEY) throw new HttpError(500, 'На сервере не задан GEMINI_KEY.');
  const json = task === 'generate';
  const payload = {
    systemInstruction: { parts: [{ text: SYSTEM[task] }] },
    contents: [{ role: 'user', parts: [
      { text: PROMPT[task](body) },
      ...(task === 'generate' ? attachments(body).map(f => ({ inlineData: { mimeType: f.mime, data: f.data } })) : []),
    ] }],
    generationConfig: {
      temperature: task === 'similar' ? 0.7 : 0.3,
      maxOutputTokens: json ? 16384 : 2048,
      ...(json ? { responseMimeType: 'application/json' } : {}),
    },
  };
  // Ключ — в заголовке, а не в адресе: так принимаются и старые ключи (AIza…),
  // и новые (AQ.…), и ключ не оседает в логах запросов
  const headers = { 'Content-Type': 'application/json', 'x-goog-api-key': env.GEMINI_KEY };
  const models = [...new Set([env.MODEL || MODEL_DEFAULT, MODEL_FALLBACK])];
  let r, detail = '';
  // Бесплатный Gemini часто отвечает 503/429 под нагрузкой: повторяем с паузой,
  // затем пробуем запасную модель. Ошибки ключа (400/401/403) не повторяем.
  attempts: for (const model of models) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
    for (const wait of [0, 1500, 4000]) {
      if (wait) await new Promise(ok => setTimeout(ok, wait));
      try {
        r = await fetch(url, { method: 'POST', headers, body: JSON.stringify(payload) });
      } catch {
        r = null;
        continue;
      }
      if (r.ok) break attempts;
      detail = await r.json().then(d => d.error?.message, () => '').catch(() => '');
      if (r.status === 404) continue attempts;                    // модель закрыта — берём запасную
      if (![429, 500, 503].includes(r.status)) break attempts;   // ключ, регион, запрос — повтор не поможет
    }
  }
  if (!r) throw new HttpError(502, 'ИИ временно недоступен. Попробуйте позже.');
  if (!r.ok) {
    const busy = [429, 500, 503].includes(r.status);
    throw new HttpError(502, busy ? 'ИИ сейчас перегружен. Попробуйте через минуту.'
      : `ИИ-сервис вернул ошибку ${r.status}. ${cut(detail, 200) || 'Проверьте модель и ключ.'}`);
  }
  const data = await r.json();
  return (data.candidates?.[0]?.content?.parts || []).map(p => p.text).join('').trim();
}

// Приводим ответ модели к формату карточек и выкидываем битые
function cleanGenerated(raw) {
  let data;
  try { data = JSON.parse(raw.replace(/^```(?:json)?|```$/g, '')); }
  catch { throw new HttpError(502, 'ИИ вернул неразборчивый ответ. Попробуйте ещё раз или сократите материал.'); }
  const topics = (Array.isArray(data.topics) ? data.topics : [])
    .filter(t => t && t.id && t.title).map(t => ({ id: String(t.id), title: String(t.title) }));
  const known = new Set(topics.map(t => t.id));
  const cards = [];
  for (const c of Array.isArray(data.cards) ? data.cards : []) {
    if (!c || !c.q || !['one', 'many', 'flip', 'num', 'open'].includes(c.k)) continue;
    if (c.k === 'num' && !/^-?\d+([.,]\d+)?$/.test(String(c.a).trim())) c.k = 'flip'; // не число — самопроверка
    const card = { t: known.has(String(c.t)) ? String(c.t) : topics[0]?.id || 't1', k: c.k, q: String(c.q) };
    if (c.k === 'one' || c.k === 'many') {
      const o = (Array.isArray(c.o) ? c.o : []).filter(x => x && x.id && x.t).map(x => ({ id: String(x.id), t: String(x.t) }));
      const ids = new Set(o.map(x => x.id));
      const a = c.k === 'one' ? String(c.a) : (Array.isArray(c.a) ? c.a.map(String) : []);
      if (o.length < 2 || (c.k === 'one' ? !ids.has(a) : !a.length || !a.every(x => ids.has(x)))) continue;
      Object.assign(card, { o, a });
    } else {
      if (!c.a) continue;
      card.a = String(c.a);
    }
    if (c.e) card.e = String(c.e);
    cards.push(card);
  }
  if (!topics.length) topics.push({ id: 't1', title: 'Материал' });
  if (!cards.length) throw new HttpError(502, 'Не получилось сделать карточки из этого текста.');
  return { topics, cards };
}

async function sha256(s) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
}

// Доступ к набору: ключ репетитора (X-Key) или вход в аккаунт, к которому набор привязан
async function requireOwner(env, id, req) {
  const key = req.headers.get('X-Key') || '';
  const owner = await env.DB.get(`owner:${id}`);
  if (!owner) throw new HttpError(404, 'Набор не найден.');
  if (key && owner === await sha256(key)) return;
  const acct = await sessionAccount(env, req);
  if (acct && acct.id === await env.DB.get(`packacct:${id}`)) return;
  throw new HttpError(403, 'Нет доступа к набору.');
}

async function limitAi(env, req) {
  const limit = Number(env.DAILY_LIMIT || 60);
  const ip = req.headers.get('CF-Connecting-IP') || 'anon';
  const k = `rate:${ip}:${new Date().toISOString().slice(0, 10)}`;
  const used = Number((await env.DB.get(k)) || 0);
  if (used >= limit) throw new HttpError(429, 'Дневной лимит ИИ исчерпан. Возвращайтесь завтра.');
  await env.DB.put(k, String(used + 1), { expirationTtl: 172800 });
}

const readJson = async (req, max) => {
  const t = await req.text();
  if (t.length > max) throw new HttpError(413, 'Слишком большой запрос.');
  try { return JSON.parse(t); } catch { throw new HttpError(400, 'Некорректный запрос.'); }
};

async function handle(req, env, ctx) {
  const url = new URL(req.url);
  const parts = url.pathname.split('/').filter(Boolean);
  if (!env.DB) throw new HttpError(500, 'На сервере не подключено хранилище DB (KV).');

  if (parts[0] === 'me' && parts[1] === 'notify' && parts.length === 2 && req.method === 'GET') return meNotify(env, req);
  if (parts[0] === 'auth' || parts[0] === 'me') return handleAuth(req, env, parts);
  if (parts[0] === 'pay') return handleBilling(req, env, parts);

  // POST /ai и старый вызов POST / из прежнего приложения
  if (req.method === 'POST' && (parts[0] === 'ai' || !parts.length)) {
    const body = await readJson(req, MAX_REQUEST_AI);
    if (!SYSTEM[body.task]) throw new HttpError(400, 'Неизвестное действие.');
    await limitAi(env, req);
    const out = await gemini(env, body.task, body);
    return body.task === 'generate' ? cleanGenerated(out) : { text: out || 'Пустой ответ модели.' };
  }

  if (parts[0] !== 'packs' || !parts[1]) throw new HttpError(404, 'Нет такого адреса.');
  const id = parts[1];
  if (!/^[a-z0-9-]{4,40}$/.test(id)) throw new HttpError(400, 'Некорректный код набора.');

  if (parts.length === 2 && req.method === 'GET') {
    const [pack, hw] = await Promise.all([env.DB.get(`pack:${id}`), env.DB.get(`hw:${id}`)]);
    if (!pack) throw new HttpError(404, 'Набор не найден. Проверьте код у репетитора.');
    // Задание репетитора приходит внутри набора — попадает и в офлайн-копию ученика
    return new Response(withHw(pack, hw), { headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' } });
  }

  if (parts.length === 2 && req.method === 'PUT') {
    const key = req.headers.get('X-Key') || '';
    if (key.length < 16) throw new HttpError(400, 'Нужен ключ репетитора.');
    const owner = await env.DB.get(`owner:${id}`);
    if (owner && owner !== await sha256(key)) throw new HttpError(403, 'Этот код уже занят другим набором.');
    const acct = await checkPublish(env, req, id, !owner);
    const pack = await readJson(req, MAX_PACK);
    if (!pack.title || !Array.isArray(pack.cards) || !Array.isArray(pack.topics)) throw new HttpError(400, 'Набор без названия, тем или карточек.');
    pack.id = id;
    pack.updated = Date.now();
    delete pack.hw; // задание хранится отдельно (hw:<id>) и вставляется при чтении
    if (!owner) await env.DB.put(`owner:${id}`, await sha256(key));
    // Название и репетитор — в метаданных того же ключа: бот читает их, не открывая набор
    await env.DB.put(`pack:${id}`, JSON.stringify(pack), { metadata: { t: cut(pack.title, 60), u: cut(pack.tutor, 60) } });
    // Репетитор вошёл в аккаунт — набор привязывается к нему (доступ с любого устройства)
    if (acct && !owner) await env.DB.put(`packacct:${id}`, acct.id);
    return { ok: true, id, updated: pack.updated };
  }

  if (parts[2] === 'progress' && req.method === 'POST') {
    // Метаданные pack:<id> вместо owner:<id> — то же одно чтение (тело набора не читаем): pack:<id>
    // есть ровно у опубликованных наборов (owner пишется перед ним, оба не удаляются)
    const pk = await env.DB.getWithMetadata(`pack:${id}`, { type: 'stream' });
    pk.value?.cancel?.().catch?.(() => {});
    if (!pk.value) throw new HttpError(404, 'Набор не найден.');
    const { sid, name, stats } = await readJson(req, MAX_STATS);
    if (!/^[a-z0-9]{6,20}$/.test(sid || '') || !name) throw new HttpError(400, 'Нет имени ученика.');
    // Название и репетитора бот пишет родителю от своего имени — только из набора, не от ученика
    // (запрос без входа: иначе любой, кто знает sid, подписал бы отчёт своим текстом)
    let meta = pk.metadata;
    // Набор опубликован до метаданных: один раз достаём название из тела и дописываем метаданные
    // (одна запись на старый набор; большие тела не разбираем — хватит лимита CPU)
    if (!meta) {
      const raw = await env.DB.get(`pack:${id}`);
      if (raw && raw.length < 1e6) {
        try {
          const pack = JSON.parse(raw);
          meta = { t: cut(pack.title || '', 60), u: cut(pack.tutor || '', 60) };
          await env.DB.put(`pack:${id}`, raw, { metadata: meta });
        } catch (err) { console.error('pack meta backfill', id, err?.message); }
      }
    }
    if (stats && typeof stats === 'object') { stats.title = meta?.t || ''; stats.tutor = meta?.u || ''; }
    // Новый ученик сверх бесплатного лимита репетитора не добавляется
    const known = await env.DB.get(`prog:${id}:${sid}`);
    let tutor = null;
    if (!known) {
      try {
        tutor = await checkNewStudent(env, id);
      } catch (err) {
        // Ученик не смог присоединиться — репетитору сообщение в Telegram, иначе он не узнает
        if (err.status === 402) ctx?.waitUntil(alertTutorFull(env, id, name).catch(e => console.error('notify full', e?.message)));
        throw err;
      }
    }
    // Ученик вошёл в аккаунт — запоминаем, чтобы репетитор мог выдать код для родителя;
    // у репетитора с тарифом ученики получают и библиотеку ЕГЭ
    const acct = await sessionAccount(env, req);
    const owner = acct && await env.DB.get(`packacct:${id}`);
    if (owner) {
      const st = tutor || planStatus(await getAccount(env, owner), 'tutor');
      if (st.active && (acct.plans?.libVia || 0) < st.until) { acct.plans ||= {}; acct.plans.libVia = st.until; await saveAccount(env, acct); }
    }
    await env.DB.put(`prog:${id}:${sid}`, JSON.stringify({ sid, name: cut(name, 80), stats, at: Date.now(), acct: acct?.id }),
      { expirationTtl: 60 * 60 * 24 * 180 });
    return { ok: true };
  }

  // Репетитор выдаёт код для родителя ученика, который вошёл в аккаунт
  if (parts[2] === 'parent-code' && req.method === 'POST') {
    await requireOwner(env, id, req);
    const { sid } = await readJson(req, 1000);
    const rec = /^[a-z0-9]{6,20}$/.test(sid || '') && await env.DB.get(`prog:${id}:${sid}`, 'json');
    if (!rec) throw new HttpError(404, 'Ученик не найден.');
    if (!rec.acct) throw new HttpError(400, 'Ученик ещё не вошёл в аккаунт. Попросите его: Профиль → «Войти» — и код появится.');
    return parentCode(env, rec.acct);
  }

  if (parts[2] === 'progress' && req.method === 'GET') {
    await requireOwner(env, id, req);
    const students = [];
    let cursor;
    do {
      const list = await env.DB.list({ prefix: `prog:${id}:`, cursor });
      const rows = await Promise.all(list.keys.map(k => env.DB.get(k.name)));
      rows.forEach(r => r && students.push(JSON.parse(r)));
      cursor = list.list_complete ? null : list.cursor;
    } while (cursor);
    return progressFlags(env, id, students);
  }

  if (parts[2] === 'hw' || parts[2] === 'notify') return handleNotify(req, env, id, parts, ctx, () => requireOwner(env, id, req));

  throw new HttpError(404, 'Нет такого адреса.');
}

export default {
  async fetch(req, env, ctx) {
    const path = new URL(req.url).pathname;
    if (path === '/gh' || path === '/tg' || path.startsWith('/tg/')) {
      return (await handleBot(req, env, ctx)) || new Response('Нет такого адреса.', { status: 404 });
    }
    // Когда сервер развёрнут вместе с сайтом (wrangler.jsonc в корне), сюда же
    // приходят запросы к библиотеке packs/*.json — это статика, отдаём как есть
    if (env.ASSETS && path.endsWith('.json')) {
      const res = await env.ASSETS.fetch(req);
      // Библиотека ЕГЭ: полная — с доступом (пробный, оплата, репетитор с тарифом), иначе бесплатная часть
      const lib = /^\/packs\/([a-z-]+)\.json$/.exec(path);
      if (!lib || !LIB_PACKS.includes(lib[1]) || !res.ok) return res;
      const acct = env.DB && await sessionAccount(env, req).catch(() => null);
      if (acct && planStatus(acct, 'lib').active) return res;
      return Response.json(trimLibrary(await res.json()), { headers: { 'Cache-Control': 'no-store' } });
    }
    const origin = req.headers.get('Origin');
    if (req.method === 'OPTIONS') return new Response(null, { headers: cors(origin) });
    let res;
    try {
      const out = await handle(req, env, ctx);
      res = out instanceof Response ? out : Response.json(out);
    } catch (err) {
      const status = err.status || 500;
      res = Response.json({ error: true, message: err.status ? err.message : 'Ошибка сервера.' }, { status });
    }
    const headers = new Headers(res.headers);
    for (const [k, v] of Object.entries(cors(origin))) headers.set(k, v);
    // Явная кодировка: иначе браузер, открывший ответ напрямую, показывает кракозябры
    if ((headers.get('Content-Type') || '').startsWith('application/json')) headers.set('Content-Type', 'application/json; charset=utf-8');
    return new Response(res.body, { status: res.status, headers });
  },
  // Cron '*/5 * * * *': напоминания, отчёты родителям, сообщения репетиторам (worker/notify.js).
  // Время слота — из scheduledTime: опоздавший запуск не сдвигает слоты
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(runNotify(env, controller.scheduledTime).catch(err => console.error('notify cron', err?.message)));
  },
};
