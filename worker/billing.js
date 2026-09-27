/* ============================================================
   Тарифы и оплата (ЮKassa)
   ------------------------------------------------------------
   GET  /pay/prices               цены, пробные периоды, включена ли оплата
   POST /pay/create               {product: tutor|lib, months: 1|3, forAcct?, back}
                                  → {url} страницы оплаты ЮKassa
   GET  /pay/status?id=           проверить платёж (после возврата с оплаты)
   POST /pay/webhook              уведомление ЮKassa (payment.succeeded)

   Секреты: YK_SHOP_ID, YK_SECRET (ЮKassa → Интеграция → Ключи API).
   Цены (переменные, ₽): PRICE_TUTOR_1, PRICE_TUTOR_3, PRICE_LIB_1, PRICE_LIB_3.
   Пробные периоды, дней: TRIAL_TUTOR_DAYS (14), TRIAL_LIB_DAYS (7).

   Уведомления ЮKassa не подписаны, поэтому им не верим на слово: по id
   запрашиваем платёж у ЮKassa и начисляем доступ только при succeeded,
   ровно один раз (paid:<id>).
   ============================================================ */
import { AuthError, sessionAccount, getAccount, saveAccount, planStatus, TRIAL_DAYS, randomId } from './auth.js';

const DAY_MS = 86400e3;
export const LIB_PACKS = ['ege-rus', 'ege-math', 'econ-olymp', 'udarenie'];
export const FREE_TUTOR = { packs: 1, students: 3 }; // после пробного периода без оплаты

export function prices(env) {
  const n = (v, d) => Number(v || d);
  return {
    enabled: !!(env.YK_SHOP_ID && env.YK_SECRET),
    trial: TRIAL_DAYS(env),
    free: FREE_TUTOR,
    tutor: { 1: n(env.PRICE_TUTOR_1, 790), 3: n(env.PRICE_TUTOR_3, 1990) },
    lib: { 1: n(env.PRICE_LIB_1, 390), 3: n(env.PRICE_LIB_3, 990) },
  };
}

const NAMES = { tutor: 'Студия репетитора', lib: 'Библиотека ЕГЭ' };

async function yk(env, path, body, idem) {
  const r = await fetch(`https://api.yookassa.ru/v3${path}`, {
    method: body ? 'POST' : 'GET',
    headers: {
      Authorization: 'Basic ' + btoa(`${env.YK_SHOP_ID}:${env.YK_SECRET}`),
      'Content-Type': 'application/json',
      ...(idem ? { 'Idempotence-Key': idem } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new AuthError(502, 'Платёжный сервис недоступен. Попробуйте позже.');
  return data;
}

// Продлеваем доступ после успешной оплаты — идемпотентно
export async function extend(env, acctId, product, days, note) {
  const acct = await getAccount(env, acctId);
  if (!acct) return null;
  acct.plans ||= {};
  const p = acct.plans[product] ||= {};
  p.paidUntil = Math.max(Date.now(), p.paidUntil || 0) + days * DAY_MS;
  (p.history ||= []).push({ at: Date.now(), days, note });
  p.history = p.history.slice(-20);
  await saveAccount(env, acct);
  return acct;
}

async function applyPayment(env, id) {
  const pay = await yk(env, `/payments/${encodeURIComponent(id)}`);
  const meta = pay.metadata || {};
  if (pay.status !== 'succeeded' || !meta.acct || !NAMES[meta.product]) return { status: pay.status };
  const want = prices(env)[meta.product][meta.months];
  if (!want || Number(pay.amount?.value) < want) return { status: 'amount_mismatch' };
  if (await env.DB.get(`paid:${id}`)) return { status: 'succeeded', already: true };
  await env.DB.put(`paid:${id}`, JSON.stringify({ at: Date.now(), ...meta, amount: pay.amount.value }));
  const acct = await extend(env, meta.acct, meta.product, 30 * Number(meta.months), `ЮKassa ${id}`);
  // Владельцу — уведомление в Telegram
  if (env.TG_TOKEN && env.TG_OWNER) {
    await fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/sendMessage`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: env.TG_OWNER, text: `💰 Оплата ${pay.amount.value} ₽ · ${NAMES[meta.product]} на ${meta.months} мес.\n${acct?.name || acct?.email || meta.acct}` }),
    }).catch(() => {});
  }
  return { status: 'succeeded' };
}

function safeBack(back, origin) {
  try {
    const u = new URL(back);
    if (u.origin === origin || /^http:\/\/localhost(:\d+)?$/.test(u.origin)) return u.origin + u.pathname + u.search.replace(/[?&]paid=[^&]*/, '');
  } catch { /* не адрес */ }
  return origin + '/';
}

export async function handleBilling(req, env, parts) {
  const [, b] = parts;
  const url = new URL(req.url);

  if (b === 'prices' && req.method === 'GET') return prices(env);

  if (b === 'create' && req.method === 'POST') {
    if (!prices(env).enabled) throw new AuthError(503, 'Оплата скоро появится. Пока напишите в Telegram @trwqxp — включим доступ вручную.');
    const payer = await sessionAccount(env, req);
    if (!payer) throw new AuthError(401, 'Нужно войти.');
    const body = await req.json().catch(() => ({}));
    const product = NAMES[body.product] ? body.product : null;
    const months = [1, 3].includes(Number(body.months)) ? Number(body.months) : null;
    if (!product || !months) throw new AuthError(400, 'Неизвестный тариф.');
    let target = payer;
    if (body.forAcct && body.forAcct !== payer.id) {
      // Родитель платит за ребёнка — только за привязанного
      const kids = (await env.DB.get(`parent:${payer.id}`, 'json')) || [];
      if (!kids.includes(body.forAcct) || product !== 'lib') throw new AuthError(403, 'Можно оплатить только доступ своего ребёнка.');
      target = await getAccount(env, body.forAcct);
    }
    const value = prices(env)[product][months].toFixed(2);
    const back = safeBack(body.back, url.origin);
    const idem = randomId(32);
    const pay = await yk(env, '/payments', {
      amount: { value, currency: 'RUB' },
      capture: true,
      confirmation: { type: 'redirect', return_url: `${back}${back.includes('?') ? '&' : '?'}paid=${idem}` },
      description: `${NAMES[product]}, ${months} мес. — ${target.name || 'аккаунт'}`.slice(0, 128),
      metadata: { acct: target.id, payer: payer.id, product, months: String(months), ref: idem },
    }, idem);
    // На возврате у нас есть только наш ref — запоминаем, какому платежу он соответствует
    await env.DB.put(`payref:${idem}`, pay.id, { expirationTtl: 7 * 86400 });
    return { url: pay.confirmation?.confirmation_url, id: pay.id };
  }

  if (b === 'status' && req.method === 'GET') {
    const ref = url.searchParams.get('id') || '';
    const id = /^[a-z0-9]{32}$/.test(ref) ? await env.DB.get(`payref:${ref}`) : null;
    if (!id) throw new AuthError(404, 'Платёж не найден.');
    return applyPayment(env, id);
  }

  if (b === 'webhook' && req.method === 'POST') {
    const note = await req.json().catch(() => ({}));
    const id = note?.object?.id;
    if (typeof id === 'string' && /^[\w-]{10,64}$/.test(id) && prices(env).enabled) {
      try { await applyPayment(env, id); } catch { /* ЮKassa повторит уведомление */ }
    }
    return { ok: true };
  }
  throw new AuthError(404, 'Нет такого адреса.');
}

// ---------- ограничения бесплатного тарифа ----------

// Публикация нового набора: нужен аккаунт; без тарифа — не больше FREE_TUTOR.packs
export async function checkPublish(env, req, id, isNew) {
  const acct = await sessionAccount(env, req);
  if (!isNew) return acct;
  if (!acct) throw new AuthError(401, 'Войдите, чтобы опубликовать тренажёр: так ученики и ключи не потеряются.');
  const mine = (await env.DB.get(`acctpacks:${acct.id}`, 'json')) || [];
  if (!planStatus(acct, 'tutor').active && mine.length >= FREE_TUTOR.packs) {
    throw new AuthError(402, `На бесплатном тарифе можно опубликовать ${FREE_TUTOR.packs} тренажёр. Продлите тариф, чтобы добавить ещё.`);
  }
  await env.DB.put(`acctpacks:${acct.id}`, JSON.stringify([...mine, id]));
  return acct;
}

// Новый ученик в наборе: без тарифа у репетитора — не больше FREE_TUTOR.students
export async function checkNewStudent(env, packId) {
  const ownerId = await env.DB.get(`packacct:${packId}`);
  if (!ownerId) return null; // наборы, опубликованные до тарифов, не ограничиваем
  const owner = await getAccount(env, ownerId);
  const st = planStatus(owner, 'tutor');
  if (st.active) return st;
  const list = await env.DB.list({ prefix: `prog:${packId}:` });
  if (list.keys.length >= FREE_TUTOR.students) {
    throw new AuthError(402, 'Репетитор ещё не продлил доступ для новых учеников. Напишите ему — место появится сразу после продления.');
  }
  return st;
}

// Библиотека без доступа: все правила и теория, а задания — по 2 первых прототипа
// в каждом задании (в наборах без прототипов — первые 15 карточек темы)
export function trimLibrary(pack) {
  const keep = new Set();
  const perTopic = {};
  for (const t of pack.topics) if (t.protos?.length) t.protos.slice(0, 2).forEach(p => keep.add(p.id));
  const cards = pack.cards.filter(c => {
    if (c.p) return keep.has(c.p);
    perTopic[c.t] = (perTopic[c.t] || 0) + 1;
    return perTopic[c.t] <= 15;
  });
  return { ...pack, cards, limited: { shown: cards.length, total: pack.cards.length } };
}
