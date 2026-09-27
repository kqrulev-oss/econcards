// Аккаунт: вход (Telegram, почта, Яндекс ID, VK ID, Google), сессия и выход.
// Один модуль для студии, приложения ученика и кабинета родителя.
import { store, api, esc, toast, modal } from './lib.js';

const KEY = 'zd-session';
const PENDING = 'zd-tg-pending'; // незавершённый вход через Telegram
export const session = () => store.get(KEY, null);
export const signedIn = () => !!session()?.token;
export const account = () => session()?.account || null;
const setSession = s => store.set(KEY, s);

export async function logout() {
  try { await api('/auth/logout', { method: 'POST' }); } catch { /* офлайн — сессия всё равно забывается */ }
  setSession(null);
}

export async function refreshAccount() {
  try {
    const a = await api('/me');
    setSession({ ...session(), account: a });
    return a;
  } catch (err) {
    if (/войти/i.test(err.message)) setSession(null); // сессия истекла
    return null;
  }
}

export async function addRole(role) {
  try { setSession({ ...session(), account: await api('/me/role', { method: 'POST', body: { role } }) }); } catch { /* не критично */ }
}

// Возврат от Яндекса/VK/Google: адрес вида …#login=<ticket>. Вызывается при старте
// страницы; вернёт аккаунт, если вход только что завершился, и роль, ради которой входили.
export async function finishRedirectLogin() {
  const m = /^#login(_error)?=([a-z0-9]+)$/.exec(location.hash);
  // Вернулись от Яндекса/VK/Google — брошенная попытка через Telegram больше не нужна
  if (m) store.set(PENDING, null);
  // Вернулись из Telegram, а страница перезагрузилась — продолжаем ждать подтверждения
  const pend = !m && store.get(PENDING, null);
  if (pend && !signedIn() && Date.now() - pend.at < 600e3) {
    loginDialog({ role: pend.role, resume: pend, onDone: async () => {
      if (pend.role) await addRole(pend.role);
      if (pend.after) location.hash = pend.after;
      location.reload();
    } });
    return null;
  }
  if (!m) return null;
  const after = sessionStorage.getItem('zd-login-after') || '';
  const role = sessionStorage.getItem('zd-login-role') || '';
  sessionStorage.removeItem('zd-login-after');
  sessionStorage.removeItem('zd-login-role');
  history.replaceState(null, '', location.pathname + location.search + after);
  if (m[1]) {
    toast({ cancelled: 'Вход отменён', expired: 'Время на вход истекло — попробуйте ещё раз.' }[m[2]] || 'Не получилось войти. Попробуйте ещё раз.');
    return null;
  }
  try {
    const bind = store.get('zd-oauth-bind', '');
    store.set('zd-oauth-bind', null);
    const res = await api('/auth/ticket', { method: 'POST', body: { ticket: m[2], bind } });
    setSession({ token: res.token, account: res.account });
    toast(`Вы вошли${res.account.name ? ': ' + res.account.name : ''}`);
    return { account: res.account, role };
  } catch (err) { toast(err.message); return null; }
}

const OAUTH_WAYS = [
  ['yandex', 'Яндекс ID', '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 20V4h-2a4 4 0 0 0 0 8h2M12 12l-4 8"/></svg>'],
  ['vk', 'VK ID', '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7c1 6 4 10 9 10h1v-4c2 0 3 2 4 4h3c-1-3-3-5-4-6 1-1 3-3 3-4h-3c-1 2-2 3-3 3V7h-3v7c-2-1-4-4-4-7z"/></svg>'],
  ['google', 'Google', '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.3-5.6M20 12h-8"/></svg>'],
];

export const TG_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 4L3 11l6 2 2 6 3-4 5 4z"/><path d="M9 13l8-6"/></svg>';
// Открыть ссылку (t.me) в новой вкладке, а если браузер не дал — здесь же
export function openLink(url) {
  const w = window.open(url, '_blank');
  if (w) w.opener = null; else location.href = url;
}
const MAIL_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M4 7l8 6 8-6"/></svg>';

/* Окно входа. onDone(account) вызывается после успешного входа.
   why — одна строка, зачем входить (своя для репетитора, ученика, родителя). */
/* into — элемент страницы: форма входа рисуется прямо в нём (страница login.html),
   иначе — во всплывающем окне. role может быть функцией (роль выбирают на странице). */
export async function loginDialog({ why = '', onDone, role = '', resume = null, into = null } = {}) {
  let providers = { tg: true };
  try { providers = await api('/auth/providers'); } catch { /* офлайн: покажем Telegram, ошибка будет при нажатии */ }
  const roleOf = () => (typeof role === 'function' ? role() : role);
  const html = `
    ${into ? '' : '<h3>Вход в «Между уроками»</h3>'}
    ${why ? `<p class="muted">${esc(why)}</p>` : ''}
    <div class="login-ways">
      ${providers.tg ? `<button class="btn big login-tg" data-way="tg">${TG_ICON}Через Telegram</button>` : ''}
      ${providers.email ? `<button class="btn big" data-way="email">${MAIL_ICON}Код на почту</button>` : ''}
      ${OAUTH_WAYS.filter(([id]) => providers[id]).map(([id, label, icon]) =>
        `<button class="btn big login-${id}" data-oauth="${id}">${icon}${label}</button>`).join('')}
    </div>
    <div class="login-step"></div>
    <p class="muted small-note">Входя, вы соглашаетесь с <a href="${new URL('privacy.html', import.meta.url)}" target="_blank" rel="noopener">политикой обработки данных</a>.</p>`;
  let box, close;
  if (into) { into.innerHTML = html; box = into; close = () => {}; } else ({ box, close } = modal(html));
  const step = box.querySelector('.login-step');
  let stop = false;
  const observer = new MutationObserver(() => { if (!box.isConnected) { stop = true; observer.disconnect(); } });
  observer.observe(document.body, { childList: true });

  const finish = res => {
    setSession({ token: res.token, account: res.account });
    close();
    toast(`Вы вошли${res.account.name ? ': ' + res.account.name : ''}`);
    onDone?.(res.account);
  };

  // Telegram: код входа запоминаем, чтобы вход продолжился, даже если браузер
  // открыл Telegram в этой же вкладке и страница перезагрузилась
  const waitTelegram = async (nonce, link) => {
    const cmd = `/start login_${nonce}`;
    box.querySelector('.login-ways').hidden = true; // выбран Telegram — остальные способы не отвлекают
    step.innerHTML = `
      <a class="btn primary big" id="tg-open" href="${esc(link)}" target="_blank" rel="noopener">Открыть Telegram</a>
      <p class="muted center">Нажмите в боте «Start», затем «Да, это я — войти». <span class="login-wait">Жду подтверждения…</span></p>
      <p class="muted small-note">Не открылось? Найдите бота <b>@${esc(link.split('/')[3].split('?')[0])}</b> и отправьте ему: <code class="tg-cmd">${esc(cmd)}</code> <button class="link-btn" id="tg-copy">скопировать</button></p>`;
    step.querySelector('#tg-open').addEventListener('click', ev => {
      ev.preventDefault();
      // Новая вкладка заблокирована (частый случай на iPhone/iPad) — открываем здесь же
      // (без флага noopener: с ним window.open всегда возвращает null)
      const w = window.open(link, '_blank');
      if (w) w.opener = null; else location.href = link;
    });
    step.querySelector('#tg-copy').addEventListener('click', () => navigator.clipboard?.writeText(cmd).then(() => toast('Скопировано')));
    const started = Date.now();
    while (!stop && Date.now() - started < 600e3) {
      await new Promise(ok => setTimeout(ok, 2000));
      if (stop) return;
      try {
        const r = await api(`/auth/tg/poll?nonce=${nonce}`);
        if (r.token) { store.set(PENDING, null); return finish(r); }
      } catch (err) {
        store.set(PENDING, null);
        step.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
        return;
      }
    }
  };

  if (resume) waitTelegram(resume.nonce, resume.link);

  box.querySelector('[data-way=tg]')?.addEventListener('click', async e => {
    const btn = e.currentTarget;
    btn.disabled = true;
    try {
      const { nonce, link } = await api('/auth/tg/start', { method: 'POST' });
      store.set(PENDING, { nonce, link, role: roleOf(), at: Date.now(), after: location.hash });
      waitTelegram(nonce, link);
    } catch (err) {
      step.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
      btn.disabled = false;
    }
  });

  // Яндекс, VK, Google: уходим к провайдеру и возвращаемся на эту же страницу
  box.querySelectorAll('[data-oauth]').forEach(btn => btn.addEventListener('click', async () => {
    btn.disabled = true;
    try {
      const { url, bind } = await api(`/auth/oauth/${btn.dataset.oauth}`, { method: 'POST', body: { back: location.href.split('#')[0] } });
      store.set('zd-oauth-bind', bind); // вход завершится только в этом браузере
      sessionStorage.setItem('zd-login-after', location.hash);
      sessionStorage.setItem('zd-login-role', roleOf());
      store.set(PENDING, null); // выбран другой способ — не возвращаться к ожиданию Telegram
      location.href = url;
    } catch (err) { toast(err.message); btn.disabled = false; }
  }));

  box.querySelector('[data-way=email]')?.addEventListener('click', () => {
    step.innerHTML = `
      <label class="field"><span>Почта</span></label>
      <div class="row"><input id="lg-email" type="email" autocomplete="email" placeholder="you@mail.ru"><button class="btn primary" id="lg-send">Получить код</button></div>`;
    const input = step.querySelector('#lg-email');
    input.focus();
    const send = async () => {
      const email = input.value.trim();
      if (!email) return toast('Введите почту');
      step.querySelector('#lg-send').disabled = true;
      try {
        await api('/auth/email/start', { method: 'POST', body: { email } });
        step.innerHTML = `
          <p class="muted">Код отправлен на <b>${esc(email)}</b>. Проверьте «Спам», если письма нет.</p>
          <div class="row"><input id="lg-code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="6 цифр"><button class="btn primary" id="lg-ok">Войти</button></div>`;
        const code = step.querySelector('#lg-code');
        code.focus();
        const verify = async () => {
          try { finish(await api('/auth/email/verify', { method: 'POST', body: { email, code: code.value } })); }
          catch (err) { toast(err.message); }
        };
        step.querySelector('#lg-ok').onclick = verify;
        code.onkeydown = ev => { if (ev.key === 'Enter') verify(); };
      } catch (err) {
        toast(err.message);
        step.querySelector('#lg-send').disabled = false;
      }
    };
    step.querySelector('#lg-send').onclick = send;
    input.onkeydown = ev => { if (ev.key === 'Enter') send(); };
  });
}

// ---------- тарифы и оплата ----------

const DAY = 86400e3;
export const planOf = (product, acct = account()) => acct?.status?.[product] || { active: false, until: 0, trialEnd: 0, paidUntil: 0 };
export const daysLeft = until => Math.max(0, Math.ceil((until - Date.now()) / DAY));
export const dateRu = t => new Date(t).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });

let pricesCache;
export async function getPrices() {
  if (!pricesCache) {
    pricesCache = api('/pay/prices').catch(() => ({ enabled: false, trial: { tutor: 14, lib: 7 }, free: { packs: 1, students: 3 },
      tutor: { 1: 790, 3: 1990 }, lib: { 1: 390, 3: 990 } }));
  }
  return pricesCache;
}

const PRODUCT = {
  tutor: { title: 'Студия репетитора', what: 'Без ограничений: сколько угодно тренажёров и учеников, а ваши ученики получают всю библиотеку ЕГЭ бесплатно.' },
  lib: { title: 'Библиотека ЕГЭ', what: 'Все задания ЕГЭ по русскому и профильной математике со всеми прототипами, разборами и пробными вариантами.' },
};

/* Окно оплаты. forAcct/forName — родитель платит за ребёнка. */
export async function payDialog({ product, forAcct = null, forName = '' }) {
  if (!signedIn()) return loginDialog({ role: product === 'tutor' ? 'tutor' : 'student', why: 'Сначала войдите — доступ привяжется к аккаунту.', onDone: () => payDialog({ product, forAcct, forName }) });
  const pr = await getPrices();
  const info = PRODUCT[product];
  const { box } = modal(`
    <h3>${esc(info.title)}${forName ? ` для ${esc(forName)}` : ''}</h3>
    <p>${esc(info.what)}</p>
    ${pr.enabled ? `
      <div class="pay-options">
        <button class="pay-opt" data-m="1"><b data-price="1">${pr[product][1]} ₽</b><span>1 месяц</span></button>
        <button class="pay-opt best" data-m="3"><b data-price="3">${pr[product][3]} ₽</b><span>3 месяца · выгоднее на ${Math.round((1 - pr[product][3] / (pr[product][1] * 3)) * 100)}%</span></button>
      </div>
      <label class="field pay-mail"><span>Почта для чека</span><input id="pay-email" type="email" inputmode="email" autocomplete="email" placeholder="you@mail.ru" value="${esc(account()?.email || '')}"></label>
      <p class="muted small-note">Оплата картой или через СБП на странице ЮKassa. Без автосписаний — продлеваете сами, мы напомним. Чек из «Мой налог» пришлём на почту. <a href="${new URL('offer.html', import.meta.url)}" target="_blank" rel="noopener">Оферта</a></p>`
    : `<p class="panel warn-box">Онлайн-оплата скоро появится. Сейчас напишите в Telegram <a href="https://t.me/trwqxp" target="_blank" rel="noopener">@trwqxp</a> — включим доступ вручную.</p>`}
    <details class="promo"><summary>Есть промокод?</summary>
      <div class="row"><input id="promo" placeholder="Например, START20" autocapitalize="characters" autocomplete="off"><button class="btn" id="promo-ok">Применить</button></div>
      <p class="promo-msg muted"></p>
    </details>`);
  let promo = null;
  const msg = box.querySelector('.promo-msg');
  const applyPromo = async () => {
    const code = box.querySelector('#promo').value.trim();
    if (!code) return;
    try {
      const r = await api('/pay/promo', { method: 'POST', body: { code, product } });
      if (r.kind === 'days') {
        msg.textContent = `Промокод активирован: +${r.value} дней. Обновляю страницу…`;
        setTimeout(() => location.reload(), 1200);
        return;
      }
      promo = r;
      msg.textContent = `Скидка ${r.value}% применена.`;
      box.querySelectorAll('[data-price]').forEach(n => {
        const base = pr[product][n.dataset.price];
        n.innerHTML = `<s>${base} ₽</s> ${Math.max(1, Math.round(base * (100 - r.value) / 100))} ₽`;
      });
    } catch (err) { msg.textContent = err.message; }
  };
  box.querySelector('#promo-ok').onclick = applyPromo;
  box.querySelector('#promo').onkeydown = e => { if (e.key === 'Enter') applyPromo(); };
  box.querySelectorAll('[data-m]').forEach(b => b.addEventListener('click', async () => {
    const email = box.querySelector('#pay-email')?.value.trim() || '';
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) { toast('Проверьте почту для чека'); return; }
    b.disabled = true;
    try {
      sessionStorage.setItem('zd-pay-after', location.hash);
      const { url } = await api('/pay/create', { method: 'POST', body: { product, months: Number(b.dataset.m), forAcct, promo: promo?.code, email, back: location.href.split('#')[0] } });
      location.href = url;
    } catch (err) { toast(err.message); b.disabled = false; }
  }));
}

// Возврат со страницы оплаты: ?paid=<ref> → проверяем платёж и обновляем доступ
export async function finishPayment() {
  const params = new URLSearchParams(location.search);
  const ref = params.get('paid');
  if (!ref) return null;
  params.delete('paid');
  const after = sessionStorage.getItem('zd-pay-after') || location.hash;
  sessionStorage.removeItem('zd-pay-after');
  history.replaceState(null, '', location.pathname + (params.toString() ? '?' + params : '') + after);
  try {
    const r = await api(`/pay/status?id=${encodeURIComponent(ref)}`);
    if (r.status === 'succeeded') { toast('Оплата прошла — доступ открыт. Спасибо!'); await refreshAccount(); return true; }
    toast({
      pending: 'Платёж ещё обрабатывается — доступ откроется автоматически.',
      waiting_for_capture: 'Платёж ещё обрабатывается — доступ откроется автоматически.',
      amount_mismatch: 'Оплата получена, но что-то не сошлось с суммой. Мы уже знаем и откроем доступ вручную.',
    }[r.status] || 'Оплата не завершена.');
  } catch (err) { toast(err.message); }
  return false;
}
