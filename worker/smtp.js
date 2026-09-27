// Отправка письма через SMTP почтового ящика (по умолчанию — Яндекс Почта, порт 465, TLS).
// Нужен, пока у сайта нет своего домена для сервиса рассылок: код входа уходит
// с обычного ящика вида mezhdu.urokami@yandex.ru по паролю приложения.
// connect — из 'cloudflare:sockets' (в тестах подменяется).

const enc = new TextEncoder();
const b64 = s => { let bin = ''; for (const b of enc.encode(s)) bin += String.fromCharCode(b); return btoa(bin); };
const header = s => `=?UTF-8?B?${b64(s)}?=`;
const wrap = s => s.replace(/.{1,76}/g, '$&\r\n');

export class SmtpError extends Error {}

export async function sendSmtp({ host = 'smtp.yandex.ru', port = 465, user, pass, name = '', to, subject, text }, connect) {
  if (!connect) ({ connect } = await import('cloudflare:sockets'));
  const socket = connect({ hostname: host, port: Number(port) }, { secureTransport: Number(port) === 465 ? 'on' : 'off', allowHalfOpen: false });
  const writer = socket.writable.getWriter();
  const reader = socket.readable.getReader();
  const dec = new TextDecoder();
  let buf = '';
  // Ответ сервера: строки «250-…» продолжаются, «250 …» — последняя
  const reply = async () => {
    for (;;) {
      const lines = buf.split('\r\n');
      for (let i = 0; i < lines.length - 1; i++) {
        if (/^\d{3} /.test(lines[i]) || /^\d{3}$/.test(lines[i])) {
          buf = lines.slice(i + 1).join('\r\n');
          return { code: Number(lines[i].slice(0, 3)), text: lines.slice(0, i + 1).join('\n') };
        }
      }
      const { value, done } = await reader.read();
      if (done) throw new SmtpError('SMTP: соединение закрыто');
      buf += dec.decode(value, { stream: true });
    }
  };
  const step = async (cmd, ok, shown = cmd) => {
    if (cmd !== null) await writer.write(enc.encode(cmd + '\r\n'));
    const r = await reply();
    if (!ok.includes(r.code)) throw new SmtpError(`SMTP ${shown || 'greeting'} → ${r.text.slice(0, 200)}`);
    return r;
  };
  const from = user;
  const msg = [
    `From: ${name ? header(name) + ' ' : ''}<${from}>`,
    `To: <${to}>`,
    `Subject: ${header(subject)}`,
    `Date: ${new Date().toUTCString()}`,
    `Message-ID: <${crypto.randomUUID()}@${from.split('@')[1]}>`,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=utf-8',
    'Content-Transfer-Encoding: base64',
    '',
    wrap(b64(text)),
  ].join('\r\n');
  const run = async () => {
    await step(null, [220]);
    await step('EHLO mezhdu-urokami', [250]);
    await step('AUTH PLAIN ' + b64(`\0${user}\0${pass}`), [235], 'AUTH'); // пароль в ошибку не попадает
    await step(`MAIL FROM:<${from}>`, [250]);
    await step(`RCPT TO:<${to}>`, [250, 251]);
    await step('DATA', [354]);
    await step(msg + '.', [250], 'message'); // тело в base64 — строк, начинающихся с точки, нет
    await writer.write(enc.encode('QUIT\r\n')).catch(() => {});
  };
  let timer;
  try {
    await Promise.race([run(), new Promise((_, no) => { timer = setTimeout(() => no(new SmtpError('SMTP: нет ответа 15 с')), 15000); })]);
  } finally {
    clearTimeout(timer);
    try { await socket.close(); } catch { /* уже закрыт */ }
  }
}
