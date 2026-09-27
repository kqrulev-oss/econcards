// Аккаунт: вход (Telegram, почта, дальше — Яндекс, VK, Google), сессия и выход.
// Один модуль для студии, приложения ученика и кабинета родителя.
import { store, api, esc, toast, modal } from './lib.js';

const KEY = 'zd-session';
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

const TG_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 4L3 11l6 2 2 6 3-4 5 4z"/><path d="M9 13l8-6"/></svg>';
const MAIL_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M4 7l8 6 8-6"/></svg>';

/* Окно входа. onDone(account) вызывается после успешного входа.
   why — одна строка, зачем входить (своя для репетитора, ученика, родителя). */
export async function loginDialog({ why = '', onDone } = {}) {
  let providers = { tg: true };
  try { providers = await api('/auth/providers'); } catch { /* офлайн: покажем Telegram, ошибка будет при нажатии */ }
  const { box, close } = modal(`
    <h3>Вход в «Между уроками»</h3>
    ${why ? `<p class="muted">${esc(why)}</p>` : ''}
    <div class="login-ways">
      ${providers.tg ? `<button class="btn big login-tg" data-way="tg">${TG_ICON}Через Telegram</button>` : ''}
      ${providers.email ? `<button class="btn big" data-way="email">${MAIL_ICON}Код на почту</button>` : ''}
    </div>
    <div class="login-step"></div>
    <p class="muted small-note">Входя, вы соглашаетесь с <a href="${new URL('privacy.html', import.meta.url)}" target="_blank" rel="noopener">политикой обработки данных</a>.</p>`);
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

  box.querySelector('[data-way=tg]')?.addEventListener('click', async e => {
    e.currentTarget.disabled = true;
    try {
      const { nonce, link } = await api('/auth/tg/start', { method: 'POST' });
      step.innerHTML = `
        <a class="btn primary big" href="${esc(link)}" target="_blank" rel="noopener">Открыть Telegram</a>
        <p class="muted center">Нажмите в боте «Start» — вход произойдёт сам. <span class="login-wait">Жду подтверждения…</span></p>`;
      const started = Date.now();
      while (!stop && Date.now() - started < 600e3) {
        await new Promise(ok => setTimeout(ok, 2000));
        if (stop) return;
        try {
          const r = await api(`/auth/tg/poll?nonce=${nonce}`);
          if (r.token) return finish(r);
        } catch (err) {
          step.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
          return;
        }
      }
    } catch (err) {
      step.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
      e.currentTarget.disabled = false;
    }
  });

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
        code.onkeydown = ev => ev.key === 'Enter' && verify();
      } catch (err) {
        toast(err.message);
        step.querySelector('#lg-send').disabled = false;
      }
    };
    step.querySelector('#lg-send').onclick = send;
    input.onkeydown = ev => ev.key === 'Enter' && send();
  });
}
