/* ============================================================
   Тарифы и оплата (ЮKassa)
   ------------------------------------------------------------
   GET  /pay/prices               цены, пробные периоды, включена ли оплата
   POST /pay/create               {product: tutor|lib, months: 1|3, forAcct?, back}
                                  → {url} страницы оплаты ЮKassa
   GET  /pay/status?id=           проверить платёж (после возврата с оплаты)
   POST /pay/webhook              уведомление ЮKassa (payment.succeeded)
   POST /pay/promo {code}         проверить промокод: скидка — вернёт %, дни — начислит сразу

   Секреты: YK_SHOP_ID, YK_SECRET (ЮKassa → Интеграция → Ключи API).
   Цены (переменные, ₽): PRICE_TUTOR_1, PRICE_TUTOR_3, PRICE_LIB_1, PRICE_LIB_3.
   Пробные периоды, дней: TRIAL_TUTOR_DAYS (14), TRIAL_LIB_DAYS (7).

   Уведомления ЮKassa не подписаны, поэтому им не верим на слово: по id
   запрашиваем платёж у ЮKassa и начисляем доступ только при succeeded,
   ровно один раз (paid:<id>).
   ============================================================ */
import { AuthError, sessionAccount, getAccount, saveAccount, planStatus, TRIAL_DAYS, randomId } from './auth.js';

const DAY_MS = 86400e3;
export const LIB_PACKS = ['ege-rus', 'ege-math', 'econ-olymp', 'udarenie']; // и LIB_PACKS в tools/build_packs.py
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

// ---------- промокоды ----------
/* promo:<КОД> = { code, kind: 'discount'|'days', value (% или дней), product: tutor|lib|any,
                   maxUses (0 — без лимита), used, until (0 — бессрочно), off }
   Каждый аккаунт использует код один раз (promouse:<КОД>:<аккаунт>).
   Создаются командой бота /promo (только владелец). */
export const normCode = c => String(c || '').trim().toUpperCase().replace(/[^A-Z0-9А-ЯЁ_-]/g, '').slice(0, 24);

export async function savePromo(env, promo) {
  await env.DB.put(`promo:${promo.code}`, JSON.stringify(promo));
}

async function findPromo(env, acct, raw, product) {
  const code = normCode(raw);
  const promo = code && await env.DB.get(`promo:${code}`, 'json');
  const bad = msg => { throw new AuthError(400, msg); };
  if (!promo || promo.off) bad('Такого промокода нет.');
  if (promo.until && promo.until < Date.now()) bad('Срок действия промокода закончился.');
  if (promo.maxUses && promo.used >= promo.maxUses) bad('Промокод уже использован максимальное число раз.');
  if (product && promo.product !== 'any' && promo.product !== product) bad(`Этот промокод — для тарифа «${NAMES[promo.product]}».`);
  if (await env.DB.get(`promouse:${code}:${acct.id}`)) bad('Вы уже использовали этот промокод.');
  return promo;
}

async function markUsed(env, code, acctId) {
  const promo = await env.DB.get(`promo:${code}`, 'json');
  if (!promo || await env.DB.get(`promouse:${code}:${acctId}`)) return;
  promo.used = (promo.used || 0) + 1;
  await savePromo(env, promo);
  await env.DB.put(`promouse:${code}:${acctId}`, String(Date.now()));
}

// Цена со скидкой: не меньше 1 ₽ (минимум ЮKassa)
const discounted = (price, pct) => Math.max(1, Math.round(price * (100 - pct) / 100));

async function yk(env, path, body, idem) {
  const r = await fetch(`https://api.yookassa.ru/v3${path}`, {
    method: body ? 'POST' : 'GET',
    headers: {
      Authorization: 'Basic ' + btoa(`${String(env.YK_SHOP_ID).trim()}:${String(env.YK_SECRET).trim()}`),
      'Content-Type': 'application/json',
      ...(idem ? { 'Idempotence-Key': idem } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    // Причина — в логах Cloudflare (неверный shopId/ключ, тестовый ключ у боевого магазина…)
    console.error('yookassa', path, r.status, data.code, data.description, data.parameter);
    throw new AuthError(502, 'Платёжный сервис недоступен. Попробуйте позже.');
  }
  return data;
}

// Продлеваем доступ. С id платежа — идемпотентно: один платёж продлевает один раз,
// даже если уведомление ЮKassa и возврат человека на сайт пришли одновременно
export async function extend(env, acctId, product, days, note, pay = null) {
  const acct = await getAccount(env, acctId);
  if (!acct) return null;
  acct.plans ||= {};
  const p = acct.plans[product] ||= {};
  if (pay && (p.history || []).some(h => h.pay === pay)) return { acct, already: true };
  // Отрицательные дни (владелец снимает доступ после возврата) — от конца оплаченного срока
  p.paidUntil = days > 0 ? Math.max(Date.now(), p.paidUntil || 0) + days * DAY_MS : Math.max(0, (p.paidUntil || 0) + days * DAY_MS);
  (p.history ||= []).push({ at: Date.now(), days, note, ...(pay ? { pay } : {}) });
  p.history = p.history.slice(-20);
  await saveAccount(env, acct);
  return pay ? { acct } : acct;
}

async function tellOwner(env, text) {
  if (!env.TG_TOKEN || !env.TG_OWNER) return;
  await fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/sendMessage`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: env.TG_OWNER, text }),
  }).catch(err => console.error('tg owner', err?.message));
}

async function applyPayment(env, id) {
  const pay = await yk(env, `/payments/${encodeURIComponent(id)}`);
  const meta = pay.metadata || {};
  if (pay.status !== 'succeeded' || !meta.acct || !NAMES[meta.product]) return { status: pay.status };
  // Сумму сверяем с той, что была при создании платежа (цены могли поменяться с тех пор)
  const base = prices(env)[meta.product][meta.months];
  const want = meta.value ? Number(meta.value) : base && (meta.promo ? discounted(base, Number(meta.pct)) : base);
  if (!want || pay.amount?.currency !== 'RUB' || Number(pay.amount?.value) < want) {
    console.error('yookassa amount mismatch', id, pay.amount, want);
    await tellOwner(env, `⚠️ Платёж ${id}: сумма ${pay.amount?.value} ${pay.amount?.currency}, ожидалось ${want} ₽. Доступ не выдан — проверьте в кабинете ЮKassa.`);
    return { status: 'amount_mismatch' };
  }
  // paid:<id> — отметка «всё сделано», пишется последней. Если что-то упало на полпути,
  // повтор уведомления доделает остальное, а продление по history.pay второй раз не случится
  if (await env.DB.get(`paid:${id}`)) return { status: 'succeeded', already: true };
  const res = await extend(env, meta.acct, meta.product, 30 * Number(meta.months), `ЮKassa ${id}${meta.promo ? ' · ' + meta.promo : ''}`, id);
  // Не продлилось (аккаунт не найден, KV недоступен) — ошибка: ЮKassa повторит уведомление
  if (!res) throw new AuthError(500, 'Не удалось продлить доступ.');
  if (meta.promo) await markUsed(env, meta.promo, meta.payer || meta.acct);
  // Владельцу — уведомление в Telegram: с 29.12.2025 чек самозанятого оформляется
  // вручную в «Мой налог», поэтому здесь всё, что нужно для чека и чтобы его отправить
  const payer = meta.payer && meta.payer !== meta.acct ? await getAccount(env, meta.payer) : res.acct;
  const tg = (payer?.idents || []).find(i => i.startsWith('tg:'))?.slice(3);
  await tellOwner(env, [
    `💰 Оплата ${pay.amount.value} ₽${pay.test ? ' (тестовая)' : ''} · ${NAMES[meta.product]} на ${meta.months} мес. · платёж ${id}`,
    `Кто: ${res.acct.name || res.acct.id}${payer !== res.acct ? ` (платил ${payer?.name || meta.payer})` : ''}`,
    `Чек: ${meta.email || payer?.email || (tg ? `Telegram tg://user?id=${tg}` : 'контакта нет — спросите в поддержке')}`,
    'Оформите чек в «Мой налог» → «Новая продажа» и отправьте покупателю.',
  ].join('\n'));
  await env.DB.put(`paid:${id}`, JSON.stringify({ at: Date.now(), ...meta, amount: pay.amount.value, test: !!pay.test }));
  return { status: 'succeeded', ...(res.already ? { already: true } : {}) };
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
    // Промокод со скидкой проверяем здесь; засчитывается он после успешной оплаты
    const promo = body.promo ? await findPromo(env, payer, body.promo, product) : null;
    if (promo && promo.kind !== 'discount') throw new AuthError(400, 'Этот промокод даёт бесплатные дни — активируйте его отдельно.');
    const value = (promo ? discounted(prices(env)[product][months], promo.value) : prices(env)[product][months]).toFixed(2);
    // Почта для чека «Мой налог» (у вошедших через Telegram её нет — спрашиваем в окне оплаты)
    const email = /^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,20}$/.test(String(body.email || '').trim()) ? String(body.email).trim().toLowerCase() : '';
    const back = safeBack(body.back, url.origin);
    const idem = randomId(32);
    const pay = await yk(env, '/payments', {
      amount: { value, currency: 'RUB' },
      capture: true,
      confirmation: { type: 'redirect', return_url: `${back}${back.includes('?') ? '&' : '?'}paid=${idem}` },
      description: `${NAMES[product]}, ${months} мес. — ${target.name || 'аккаунт'}`.slice(0, 128),
      metadata: { acct: target.id, payer: payer.id, product, months: String(months), ref: idem, value,
        ...(email ? { email } : {}), ...(promo ? { promo: promo.code, pct: String(promo.value) } : {}) },
    }, idem);
    // На возврате у нас есть только наш ref — запоминаем, какому платежу он соответствует
    await env.DB.put(`payref:${idem}`, pay.id, { expirationTtl: 7 * 86400 });
    return { url: pay.confirmation?.confirmation_url, id: pay.id };
  }

  if (b === 'promo' && req.method === 'POST') {
    const acct = await sessionAccount(env, req);
    if (!acct) throw new AuthError(401, 'Нужно войти.');
    const lim = `lim:promo:${acct.id}:${Math.floor(Date.now() / 3600e3)}`;
    const tries = Number(await env.DB.get(lim) || 0);
    if (tries >= 15) throw new AuthError(429, 'Слишком много попыток. Попробуйте через час.');
    await env.DB.put(lim, String(tries + 1), { expirationTtl: 7200 });
    const body = await req.json().catch(() => ({}));
    const promo = await findPromo(env, acct, body.code, body.product || null);
    if (promo.kind === 'discount') return { code: promo.code, kind: 'discount', value: promo.value, product: promo.product };
    // Бесплатные дни — начисляем сразу
    const product = promo.product === 'any' ? (NAMES[body.product] ? body.product : 'lib') : promo.product;
    await extend(env, acct.id, product, promo.value, `промокод ${promo.code}`);
    await markUsed(env, promo.code, acct.id);
    return { code: promo.code, kind: 'days', value: promo.value, product, applied: true };
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
    // Сам платёж перезапрашиваем у ЮKassa по id — поддельное уведомление ничего не выдаст.
    // Ошибка → ответ не 200, и ЮKassa повторит уведомление (до суток)
    if (/^payment\./.test(note?.event || '') && typeof id === 'string' && /^[\w-]{10,64}$/.test(id) && prices(env).enabled) {
      await applyPayment(env, id);
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
// в каждом задании (в наборах без прототипов — первые 15 карточек темы).
// Обычно эта часть уже собрана заранее в packs/<id>.free.json (trim_library в
// tools/build_packs.py — те же правила, меняйте вместе); здесь — запасной путь,
// если файла нет
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
