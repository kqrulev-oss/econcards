/* ============================================================
   Аккаунты «Между уроками»: вход, сессии, облачная копия
   ------------------------------------------------------------
   POST /auth/tg/start            ссылка на бота с одноразовым кодом входа
   GET  /auth/tg/poll?nonce=      ждём, пока человек нажмёт «Start» в боте
   POST /auth/email/start         код на почту (Resend: RESEND_KEY, EMAIL_FROM)
   POST /auth/email/verify        проверка кода
   GET  /auth/providers           какие способы входа включены
   POST /auth/oauth/:p            ссылка на вход через Яндекс ID, VK ID или Google
   GET  /auth/:p/callback         возврат от провайдера → сайт с #login=<ticket>
   POST /auth/ticket              одноразовый ticket → сессия
   POST /auth/logout
   GET  /me                       аккаунт; PATCH /me {name}; POST /me/role {role}
   GET|PUT /me/studio             облачная копия студии репетитора
   GET|PUT /me/progress/:ref      прогресс ученика по набору
   POST /me/parent-code           ученик: код для родителя (24 часа)
   GET  /me/children              родитель: дети и их прогресс; POST {code} — добавить,
                                  DELETE /me/children/:id — убрать

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

// Пробный период: один раз на аккаунт и продукт (tutor — студия, lib — библиотека ЕГЭ)
export const TRIAL_DAYS = env => ({ tutor: Number(env.TRIAL_TUTOR_DAYS || 14), lib: Number(env.TRIAL_LIB_DAYS || 7) });
export function startTrial(env, acct, product) {
  acct.plans ||= {};
  const p = acct.plans[product] ||= {};
  if (p.trialEnd) return false;
  p.trialEnd = Date.now() + TRIAL_DAYS(env)[product] * DAY * 1000;
  return true;
}

// Доступ сейчас: пробный, оплаченный или (для библиотеки) через репетитора с тарифом
export function planStatus(acct, product) {
  const p = acct?.plans?.[product] || {};
  const now = Date.now();
  const via = product === 'lib' ? acct?.plans?.libVia || 0 : 0;
  const until = Math.max(p.trialEnd || 0, p.paidUntil || 0, via);
  return { active: until > now, until, trialEnd: p.trialEnd || 0, paidUntil: p.paidUntil || 0, via,
    trial: (p.trialEnd || 0) > now && !((p.paidUntil || 0) > now) && !(via > now) };
}

export function publicAccount(a) {
  return { id: a.id, name: a.name, email: a.email || null, roles: a.roles, idents: a.idents.map(i => i.split(':')[0]), plans: a.plans || {},
    status: { tutor: planStatus(a, 'tutor'), lib: planStatus(a, 'lib') } };
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

// ---------- Яндекс ID, VK ID, Google (OAuth 2.0 / 2.1 с PKCE) ----------

const b64url = buf => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const form = o => new URLSearchParams(Object.entries(o).filter(([, v]) => v != null)).toString();

async function postForm(url, body, headers = {}) {
  const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', ...headers }, body: form(body) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.error) throw new AuthError(502, 'Провайдер не подтвердил вход. Попробуйте ещё раз.');
  return data;
}

const OAUTH = {
  yandex: {
    on: env => env.YANDEX_ID && env.YANDEX_SECRET,
    authorize: (env, q) => `https://oauth.yandex.ru/authorize?${form({ response_type: 'code', client_id: env.YANDEX_ID, redirect_uri: q.redirect, state: q.state, force_confirm: 'no' })}`,
    async profile(env, q) {
      const t = await postForm('https://oauth.yandex.ru/token', { grant_type: 'authorization_code', code: q.code, client_id: env.YANDEX_ID, client_secret: env.YANDEX_SECRET });
      const u = await fetch('https://login.yandex.ru/info?format=json', { headers: { Authorization: `OAuth ${t.access_token}` } }).then(r => r.json());
      if (!u.id) throw new AuthError(502, 'Яндекс не вернул профиль.');
      return { sub: String(u.id), name: u.real_name || u.display_name || u.login, email: u.default_email };
    },
  },
  google: {
    on: env => env.GOOGLE_ID && env.GOOGLE_SECRET,
    authorize: (env, q) => `https://accounts.google.com/o/oauth2/v2/auth?${form({ response_type: 'code', client_id: env.GOOGLE_ID, redirect_uri: q.redirect, state: q.state, scope: 'openid email profile', prompt: 'select_account' })}`,
    async profile(env, q) {
      const t = await postForm('https://oauth2.googleapis.com/token', { grant_type: 'authorization_code', code: q.code, client_id: env.GOOGLE_ID, client_secret: env.GOOGLE_SECRET, redirect_uri: q.redirect });
      const u = await fetch('https://openidconnect.googleapis.com/v1/userinfo', { headers: { Authorization: `Bearer ${t.access_token}` } }).then(r => r.json());
      if (!u.sub) throw new AuthError(502, 'Google не вернул профиль.');
      return { sub: u.sub, name: u.name, email: u.email_verified ? u.email : undefined };
    },
  },
  // VK ID — OAuth 2.1: без секрета, но с PKCE и device_id из ответа
  vk: {
    on: env => env.VK_ID,
    pkce: true,
    authorize: (env, q) => `https://id.vk.com/authorize?${form({ response_type: 'code', client_id: env.VK_ID, redirect_uri: q.redirect, state: q.state, code_challenge: q.challenge, code_challenge_method: 'S256', scope: 'email' })}`,
    async profile(env, q) {
      const t = await postForm('https://id.vk.com/oauth2/auth', { grant_type: 'authorization_code', code: q.code, code_verifier: q.verifier, client_id: env.VK_ID, device_id: q.device_id, redirect_uri: q.redirect, state: q.state });
      const u = (await postForm('https://id.vk.com/oauth2/user_info', { client_id: env.VK_ID, access_token: t.access_token })).user || {};
      if (!u.user_id) throw new AuthError(502, 'VK не вернул профиль.');
      return { sub: String(u.user_id), name: [u.first_name, u.last_name].filter(Boolean).join(' '), email: u.email };
    },
  },
};

// Вернуться можно только на свой сайт (и localhost для разработки)
function safeBack(back, origin) {
  try {
    const u = new URL(back);
    if (u.origin === origin || /^http:\/\/localhost(:\d+)?$/.test(u.origin)) return u.origin + u.pathname + u.search;
  } catch { /* не адрес */ }
  return origin + '/';
}

// ---------- родители ----------

// Код без похожих символов (0/O, 1/I), чтобы его легко продиктовать
export async function parentCode(env, childId) {
  const abc = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  const code = [...crypto.getRandomValues(new Uint8Array(6))].map(b => abc[b % abc.length]).join('');
  await env.DB.put(`link:${code}`, childId, { expirationTtl: DAY });
  return { code, expires: Date.now() + DAY * 1000 };
}

async function childrenOf(env, parent) {
  const ids = (await env.DB.get(`parent:${parent.id}`, 'json')) || [];
  return Promise.all(ids.map(async id => {
    const child = await getAccount(env, id);
    if (!child) return null;
    const list = await env.DB.list({ prefix: `progress:${id}:` });
    const packs = await Promise.all(list.keys.map(async k => {
      const p = await env.DB.get(k.name, 'json');
      return p && { ref: k.name.slice(`progress:${id}:`.length), cards: p.cards, log: p.log, saved: p.saved };
    }));
    return { id, name: child.name || 'Ученик', packs: packs.filter(Boolean), plans: child.plans || {} };
  })).then(r => r.filter(Boolean));
}

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
    yandex: !!OAUTH.yandex.on(env),
    vk: !!OAUTH.vk.on(env),
    google: !!OAUTH.google.on(env),
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

    // Начало входа через провайдера: сайт получает адрес и сам переходит по нему
    if (b === 'oauth' && OAUTH[c] && m === 'POST') {
      const prov = OAUTH[c];
      if (!prov.on(env)) throw new AuthError(503, 'Этот способ входа пока не настроен.');
      await limit(env, 'oauth', ip(req), 30);
      const origin = new URL(req.url).origin;
      const body = await readBody(req);
      const state = randomId(32);
      const verifier = prov.pkce ? randomId(64) : undefined;
      const challenge = verifier ? b64url(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))) : undefined;
      const current = await sessionAccount(env, req); // уже вошёл — привязываем новый способ к этому аккаунту
      await env.DB.put(`oauth:${state}`, JSON.stringify({ p: c, back: safeBack(body.back, origin), verifier, link: current?.id }), { expirationTtl: 600 });
      return { url: prov.authorize(env, { redirect: `${origin}/auth/${c}/callback`, state, challenge }) };
    }

    // Провайдер вернул человека: код → профиль → вход → назад на сайт с одноразовым ticket
    if (OAUTH[b] && c === 'callback' && m === 'GET') {
      const url = new URL(req.url);
      const q = Object.fromEntries(url.searchParams);
      const saved = /^[a-z0-9]{32}$/.test(q.state || '') && await env.DB.get(`oauth:${q.state}`, 'json');
      if (!saved || saved.p !== b) return Response.redirect(`${url.origin}/?login_error=expired`, 302);
      await env.DB.delete(`oauth:${q.state}`);
      if (!q.code) return Response.redirect(`${saved.back}#login_error=cancelled`, 302);
      try {
        const prof = await OAUTH[b].profile(env, { ...q, verifier: saved.verifier, redirect: `${url.origin}/auth/${b}/callback` });
        const res = await login(env, b, prof.sub, prof, saved.link ? await getAccount(env, saved.link) : null);
        const ticket = randomId(32);
        await env.DB.put(`ticket:${ticket}`, JSON.stringify(res), { expirationTtl: 120 });
        return Response.redirect(`${saved.back}#login=${ticket}`, 302);
      } catch {
        return Response.redirect(`${saved.back}#login_error=failed`, 302);
      }
    }

    if (b === 'ticket' && m === 'POST') {
      const { ticket } = await readBody(req);
      if (!/^[a-z0-9]{32}$/.test(ticket || '')) throw new AuthError(400, 'Некорректный вход.');
      const res = await env.DB.get(`ticket:${ticket}`, 'json');
      if (!res) throw new AuthError(410, 'Вход устарел. Попробуйте ещё раз.');
      await env.DB.delete(`ticket:${ticket}`);
      return res;
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
      if (role === 'tutor') startTrial(env, acct, 'tutor');
      if (role === 'student') startTrial(env, acct, 'lib');
      await saveAccount(env, acct);
      return publicAccount(acct);
    }
    if (b === 'studio' && m === 'GET') return (await env.DB.get(`studio:${acct.id}`, 'json')) || { packs: {}, keys: {}, deleted: {} };
    if (b === 'studio' && m === 'PUT') {
      const data = await readBody(req, MAX_STUDIO);
      if (!data || typeof data.packs !== 'object' || typeof data.keys !== 'object') throw new AuthError(400, 'Некорректные данные студии.');
      await env.DB.put(`studio:${acct.id}`, JSON.stringify({ packs: data.packs, keys: data.keys, deleted: data.deleted || {}, saved: Date.now() }));
      if (!acct.roles.tutor || startTrial(env, acct, 'tutor')) { acct.roles.tutor ||= Date.now(); await saveAccount(env, acct); }
      return { ok: true, saved: Date.now() };
    }
    if (b === 'parent-code' && m === 'POST') {
      await limit(env, 'pcode', acct.id, 10);
      return parentCode(env, acct.id);
    }
    if (b === 'children') {
      if (m === 'GET' && !c) return { children: await childrenOf(env, acct) };
      if (m === 'POST' && !c) {
        const code = String((await readBody(req)).code || '').trim().toUpperCase();
        await limit(env, 'plink', acct.id, 20);
        const childId = /^[A-Z0-9]{6}$/.test(code) && await env.DB.get(`link:${code}`);
        if (!childId) throw new AuthError(400, 'Код не подошёл: проверьте его или попросите новый (код действует сутки).');
        if (childId === acct.id) throw new AuthError(400, 'Это ваш собственный код.');
        const ids = (await env.DB.get(`parent:${acct.id}`, 'json')) || [];
        if (!ids.includes(childId)) ids.push(childId);
        await env.DB.put(`parent:${acct.id}`, JSON.stringify(ids.slice(-10)));
        await env.DB.delete(`link:${code}`);
        if (!acct.roles.parent) { acct.roles.parent = Date.now(); await saveAccount(env, acct); }
        return { children: await childrenOf(env, acct) };
      }
      if (m === 'DELETE' && c) {
        const ids = ((await env.DB.get(`parent:${acct.id}`, 'json')) || []).filter(x => x !== c);
        await env.DB.put(`parent:${acct.id}`, JSON.stringify(ids));
        return { children: await childrenOf(env, acct) };
      }
    }
    // Список тренажёров ученика (для личного кабинета): журнал по дням и сколько карточек начато
    if (b === 'progress' && !c && m === 'GET') {
      const list = await env.DB.list({ prefix: `progress:${acct.id}:` });
      const items = await Promise.all(list.keys.map(async k => {
        const p = await env.DB.get(k.name, 'json');
        return p && { ref: k.name.slice(`progress:${acct.id}:`.length), log: p.log || {}, started: Object.keys(p.cards || {}).length, saved: p.saved || 0 };
      }));
      return { items: items.filter(Boolean).sort((x, y) => y.saved - x.saved) };
    }
    if (b === 'progress' && c) {
      const k = `progress:${acct.id}:${refKey(decodeURIComponent(c))}`;
      if (m === 'GET') return (await env.DB.get(k, 'json')) || null;
      if (m === 'PUT') {
        const data = await readBody(req, MAX_PROGRESS);
        if (!data || typeof data.cards !== 'object' || typeof data.log !== 'object') throw new AuthError(400, 'Некорректный прогресс.');
        await env.DB.put(k, JSON.stringify({ ...data, saved: Date.now() }));
        if (!acct.roles.student || startTrial(env, acct, 'lib')) { acct.roles.student ||= Date.now(); await saveAccount(env, acct); }
        return { ok: true };
      }
    }
    throw new AuthError(404, 'Нет такого адреса.');
  }
  return null;
}
