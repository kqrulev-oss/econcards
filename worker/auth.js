/* ============================================================
   Аккаунты «Между уроками»: вход, сессии, облачная копия
   ------------------------------------------------------------
   POST /auth/tg/start            ссылка на бота с одноразовым кодом входа
   GET  /auth/tg/poll?nonce=      ждём, пока человек нажмёт «Start» в боте
   POST /auth/email/start         код на почту (Resend: RESEND_KEY, EMAIL_FROM)
   POST /auth/email/verify        проверка кода
   GET  /auth/providers           какие способы входа включены
   POST /auth/logout
   GET  /me                       аккаунт; PATCH /me {name}; POST /me/role {role}
   GET|PUT /me/studio             облачная копия студии репетитора
   GET|PUT /me/progress/:ref      прогресс ученика по набору

   KV: acct:<id>, ident:<provider>:<sub> → id, sess:<token> → id,
       tgauth:<nonce>, mailcode:<email>, studio:<id>, progress:<id>:<ref>
   ============================================================ */

export class AuthError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

const DAY = 86400;
const SESSION_TTL = 180 * DAY;
const ROLES = ['tutor', 'student', 'parent'];
const MAX_STUDIO = 10e6;
const MAX_PROGRESS = 2e6;

export function randomId(n = 24) {
  const abc = 'abcdefghijklmnopqrstuvwxyz0123456789';
  const bytes = crypto.getRandomValues(new Uint8Array(n));
  return [...bytes].map(b => abc[b % abc.length]).join('');
}

const readBody = async (req, max = 20000) => {
  const t = await req.text();
  if (t.length > max) throw new AuthError(413, 'Слишком большой запрос.');
  try { return t ? JSON.parse(t) : {}; } catch { throw new AuthError(400, 'Некорректный запрос.'); }
};

// Не больше `max` действий `what` за час с одного ключа (IP или адреса)
async function limit(env, what, key, max) {
  const k = `lim:${what}:${key}:${Math.floor(Date.now() / 3600e3)}`;
  const used = Number(await env.DB.get(k) || 0);
  if (used >= max) throw new AuthError(429, 'Слишком много попыток. Попробуйте через час.');
  await env.DB.put(k, String(used + 1), { expirationTtl: 7200 });
}
const ip = req => req.headers.get('CF-Connecting-IP') || 'anon';

// ---------- аккаунты и сессии ----------

export async function getAccount(env, id) {
  return id ? env.DB.get(`acct:${id}`, 'json') : null;
}
export const saveAccount = (env, a) => env.DB.put(`acct:${a.id}`, JSON.stringify(a));

export function publicAccount(a) {
  return { id: a.id, name: a.name, email: a.email || null, roles: a.roles, idents: a.idents.map(i => i.split(':')[0]), plans: a.plans || {} };
}

// Сессия из заголовка Authorization: Bearer <token>
export async function sessionAccount(env, req) {
  const m = /^Bearer\s+([a-z0-9]{32})$/.exec(req.headers.get('Authorization') || '');
  if (!m) return null;
  const id = await env.DB.get(`sess:${m[1]}`);
  return id ? getAccount(env, id) : null;
}

async function requireAccount(env, req) {
  const a = await sessionAccount(env, req);
  if (!a) throw new AuthError(401, 'Нужно войти.');
  return a;
}

/* Вход через способ provider/sub. Если человек уже вошёл (current) — привязываем
   способ к его аккаунту; если способ уже знаком — входим в его аккаунт. */
export async function login(env, provider, sub, profile = {}, current = null) {
  const identKey = `ident:${provider}:${sub}`;
  const known = await env.DB.get(identKey);
  let acct = known ? await getAccount(env, known) : null;
  if (!acct && current) acct = current;
  if (!acct) {
    acct = { id: 'a' + randomId(12), name: '', roles: {}, idents: [], plans: {}, created: Date.now() };
  }
  const ident = `${provider}:${sub}`;
  if (!acct.idents.includes(ident)) acct.idents.push(ident);
  if (!acct.name && profile.name) acct.name = String(profile.name).slice(0, 80);
  if (!acct.email && profile.email) acct.email = String(profile.email).slice(0, 120);
  await saveAccount(env, acct);
  if (!known) await env.DB.put(identKey, acct.id);
  const token = randomId(32);
  await env.DB.put(`sess:${token}`, acct.id, { expirationTtl: SESSION_TTL });
  return { token, account: publicAccount(acct) };
}

// ---------- Telegram: вход по диплинку бота ----------

async function botName(env) {
  let name = await env.DB.get('tg:botname');
  if (!name && env.TG_TOKEN) {
    const r = await fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/getMe`).then(x => x.json()).catch(() => ({}));
    name = r.result?.username;
    if (name) await env.DB.put('tg:botname', name, { expirationTtl: 7 * DAY });
  }
  return name;
}

// Вызывается ботом на «/start login_<nonce>» — из любого чата
export async function confirmTelegram(env, nonce, from) {
  const k = `tgauth:${nonce}`;
  const state = await env.DB.get(k, 'json');
  if (!state || state.tg) return false;
  const name = [from.first_name, from.last_name].filter(Boolean).join(' ') || from.username || '';
  await env.DB.put(k, JSON.stringify({ ...state, tg: String(from.id), name }), { expirationTtl: 600 });
  return true;
}

// ---------- почта ----------

async function sendMail(env, to, code) {
  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${env.RESEND_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: env.EMAIL_FROM, to, subject: `Код входа: ${code}`,
      text: `Ваш код для входа в «Между уроками»: ${code}\n\nОн действует 10 минут. Если вы не запрашивали код — просто удалите письмо.`,
    }),
  });
  if (!r.ok) throw new AuthError(502, 'Не получилось отправить письмо. Попробуйте позже.');
}

const normEmail = e => String(e || '').trim().toLowerCase();
const validEmail = e => /^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,}$/.test(e);

// ---------- облачные копии ----------

const refKey = ref => {
  const r = String(ref || '');
  if (!/^(t:)?[a-z0-9-]{3,40}$/.test(r)) throw new AuthError(400, 'Некорректный набор.');
  return r;
};

// ---------- маршруты ----------

export function providers(env) {
  return {
    tg: !!env.TG_TOKEN,
    email: !!(env.RESEND_KEY && env.EMAIL_FROM),
    yandex: !!(env.YANDEX_ID && env.YANDEX_SECRET),
    vk: !!env.VK_ID,
    google: !!(env.GOOGLE_ID && env.GOOGLE_SECRET),
  };
}

export async function handleAuth(req, env, parts) {
  const [a, b, c] = parts;
  const m = req.method;

  if (a === 'auth') {
    if (b === 'providers' && m === 'GET') return providers(env);

    if (b === 'tg' && c === 'start' && m === 'POST') {
      if (!env.TG_TOKEN) throw new AuthError(503, 'Вход через Telegram не настроен.');
      await limit(env, 'tgstart', ip(req), 30);
      const name = await botName(env);
      if (!name) throw new AuthError(502, 'Бот недоступен. Попробуйте позже.');
      const nonce = randomId(24);
      await env.DB.put(`tgauth:${nonce}`, JSON.stringify({ at: Date.now() }), { expirationTtl: 600 });
      return { nonce, link: `https://t.me/${name}?start=login_${nonce}` };
    }

    if (b === 'tg' && c === 'poll' && m === 'GET') {
      const nonce = new URL(req.url).searchParams.get('nonce') || '';
      if (!/^[a-z0-9]{24}$/.test(nonce)) throw new AuthError(400, 'Некорректный код.');
      const state = await env.DB.get(`tgauth:${nonce}`, 'json');
      if (!state) throw new AuthError(410, 'Время входа истекло. Начните заново.');
      if (!state.tg) return { pending: true };
      await env.DB.delete(`tgauth:${nonce}`);
      return login(env, 'tg', state.tg, { name: state.name }, await sessionAccount(env, req));
    }

    if (b === 'email' && c === 'start' && m === 'POST') {
      if (!providers(env).email) throw new AuthError(503, 'Вход по почте пока не настроен.');
      const email = normEmail((await readBody(req)).email);
      if (!validEmail(email)) throw new AuthError(400, 'Проверьте адрес почты.');
      await limit(env, 'mailip', ip(req), 10);
      await limit(env, 'mailto', email, 3);
      const code = String(crypto.getRandomValues(new Uint32Array(1))[0] % 1e6).padStart(6, '0');
      await env.DB.put(`mailcode:${email}`, JSON.stringify({ code, tries: 0 }), { expirationTtl: 600 });
      await sendMail(env, email, code);
      return { ok: true };
    }

    if (b === 'email' && c === 'verify' && m === 'POST') {
      const body = await readBody(req);
      const email = normEmail(body.email);
      const k = `mailcode:${email}`;
      const state = await env.DB.get(k, 'json');
      if (!state) throw new AuthError(410, 'Код устарел. Запросите новый.');
      if (String(body.code || '').trim() !== state.code) {
        state.tries++;
        if (state.tries >= 5) await env.DB.delete(k);
        else await env.DB.put(k, JSON.stringify(state), { expirationTtl: 600 });
        throw new AuthError(400, state.tries >= 5 ? 'Слишком много ошибок. Запросите новый код.' : 'Неверный код.');
      }
      await env.DB.delete(k);
      return login(env, 'email', email, { email }, await sessionAccount(env, req));
    }

    if (b === 'logout' && m === 'POST') {
      const t = /^Bearer\s+([a-z0-9]{32})$/.exec(req.headers.get('Authorization') || '');
      if (t) await env.DB.delete(`sess:${t[1]}`);
      return { ok: true };
    }
    throw new AuthError(404, 'Нет такого адреса.');
  }

  if (a === 'me') {
    const acct = await requireAccount(env, req);
    if (!b && m === 'GET') return publicAccount(acct);
    if (!b && m === 'PATCH') {
      const body = await readBody(req);
      if (typeof body.name === 'string') acct.name = body.name.trim().slice(0, 80);
      await saveAccount(env, acct);
      return publicAccount(acct);
    }
    if (b === 'role' && m === 'POST') {
      const { role } = await readBody(req);
      if (!ROLES.includes(role)) throw new AuthError(400, 'Неизвестная роль.');
      if (!acct.roles[role]) acct.roles[role] = Date.now();
      await saveAccount(env, acct);
      return publicAccount(acct);
    }
    if (b === 'studio' && m === 'GET') return (await env.DB.get(`studio:${acct.id}`, 'json')) || { packs: {}, keys: {}, deleted: {} };
    if (b === 'studio' && m === 'PUT') {
      const data = await readBody(req, MAX_STUDIO);
      if (!data || typeof data.packs !== 'object' || typeof data.keys !== 'object') throw new AuthError(400, 'Некорректные данные студии.');
      await env.DB.put(`studio:${acct.id}`, JSON.stringify({ packs: data.packs, keys: data.keys, deleted: data.deleted || {}, saved: Date.now() }));
      if (!acct.roles.tutor) { acct.roles.tutor = Date.now(); await saveAccount(env, acct); }
      return { ok: true, saved: Date.now() };
    }
    if (b === 'progress' && c) {
      const k = `progress:${acct.id}:${refKey(decodeURIComponent(c))}`;
      if (m === 'GET') return (await env.DB.get(k, 'json')) || null;
      if (m === 'PUT') {
        const data = await readBody(req, MAX_PROGRESS);
        if (!data || typeof data.cards !== 'object' || typeof data.log !== 'object') throw new AuthError(400, 'Некорректный прогресс.');
        await env.DB.put(k, JSON.stringify({ ...data, saved: Date.now() }));
        if (!acct.roles.student) { acct.roles.student = Date.now(); await saveAccount(env, acct); }
        return { ok: true };
      }
    }
    throw new AuthError(404, 'Нет такого адреса.');
  }
  return null;
}
