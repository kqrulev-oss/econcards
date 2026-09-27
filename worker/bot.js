/* ============================================================
   Telegram-бот «Между уроками»: один чат для Claude и Codex
   ------------------------------------------------------------
   Сообщение в бот → Gemini решает, кому задача (Claude — логика и данные,
   Codex — дизайн, Gemini — просто ответить) → бот создаёт issue на GitHub
   с упоминанием @claude или @codex → агенты работают в репозитории.
   Их комментарии и PR приходят обратно в чат (вебхук GitHub → /gh).
   Ответ реплаем на такое сообщение уходит комментарием в тот же issue.

   POST /tg           вебхук Telegram (заголовок X-Telegram-Bot-Api-Secret-Token)
   GET  /tg/setup     один раз: регистрирует вебхук и команды (?key=TG_SECRET)
   POST /gh           вебхук GitHub (подпись X-Hub-Signature-256)

   Секреты (Cloudflare → Worker → Settings → Variables and Secrets):
     TG_TOKEN   токен бота от @BotFather
     TG_SECRET  любая длинная случайная строка (защищает вебхук)
     TG_OWNER   id вашего чата — бот подскажет его на /start
     GH_TOKEN   fine-grained токен GitHub: только этот репозиторий,
                Issues — Read and write, Pull requests — Read and write
     GH_SECRET  секрет вебхука GitHub (любая случайная строка)
     GEMINI_KEY уже есть — им же бот распределяет задачи
   Переменная GH_REPO (по умолч. kqrulev-oss/econcards).
   ============================================================ */

import { confirmTelegram, getAccount, planStatus } from './auth.js';
import { extend } from './billing.js';

const MARK = '<!-- via-telegram -->'; // наши issue и комментарии — не пересылаем их обратно
const AGENTS = { claude: 'Claude', codex: 'Codex', gemini: 'Gemini' };
const MODELS = ['gemini-flash-latest', 'gemini-flash-lite-latest'];
const TTL = 60 * 60 * 24 * 90;

const ROUTER = `Ты диспетчер задач в проекте «Между уроками» (тренажёр для учеников репетитора: статический PWA на ванильном JS, Cloudflare Worker, наборы карточек ЕГЭ).
В команде два агента-программиста:
- codex — ДИЗАЙН: внешний вид, вёрстка, стили app.css, разметка страниц, картинки, иконки, анимации, тексты на лендинге.
- claude — ЛОГИКА И ДАННЫЕ: JavaScript-логика, сервер worker/, генераторы и наборы заданий (tools/, data/, packs/), ИИ-функции, баги, деплой, проверка кода.
- gemini — если это просто вопрос, совет или идея, где не нужно менять код: ответь сам.
Если задача смешанная — отдай тому, чья часть больше, и в brief попроси не трогать чужую зону без нужды.
Главное правило команды: все изменения попадают в проект только через Claude Code. Codex делает дизайн и открывает PR, но проверяет, доводит и готовит к слиянию его всегда Claude. Поэтому в brief для codex напиши: «сделай PR, не сливай его — его проверит Claude».
Верни ТОЛЬКО JSON: {"agent":"claude|codex|gemini","why":"коротко, почему этот агент","title":"заголовок задачи до 70 символов","brief":"понятное ТЗ для агента по-русски: что сделать, где, как проверить; напомни следовать AGENTS.md","answer":"только для gemini: ответ пользователю простым текстом"}`;

const cut = (s, n) => String(s || '').slice(0, n);
// AGENTS_ON_GITHUB=1 — Claude и Codex подключены к GitHub и сами берут задачи по @упоминанию.
// Иначе (по умолчанию) бот — пульт задач: пишет issue, а выполняет их Claude в приложении.
const live = env => env.AGENTS_ON_GITHUB === '1';
const repo = env => env.GH_REPO || 'kqrulev-oss/econcards';

// ---------- Telegram ----------

async function tg(env, method, body) {
  const r = await fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/${method}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  return r.json().catch(() => ({}));
}

const say = (env, text, extra = {}) =>
  tg(env, 'sendMessage', { chat_id: env.TG_OWNER, text: cut(text, 3900), disable_web_page_preview: true, ...extra });

const HELP = `Пишите задачу обычным текстом — Gemini решит, кому её дать, и спросит подтверждение.
Команды:
/claude текст — сразу Claude (логика, данные, сервер)
/codex текст — сразу Codex (дизайн, вёрстка)
/ask вопрос — просто ответ Gemini, без задач
/status — открытые задачи
/grant кто tutor|lib дней — выдать доступ вручную (кто: id аккаунта, почта или id в Telegram)
/stats — аккаунты, пробные периоды, оплаты
Ответ реплаем на сообщение агента уходит ему же в задачу.`;

// ---------- GitHub ----------

async function gh(env, path, body, method = body ? 'POST' : 'GET') {
  const r = await fetch(`https://api.github.com/repos/${repo(env)}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`, Accept: 'application/vnd.github+json',
      'User-Agent': 'mezhdu-urokami-bot', 'X-GitHub-Api-Version': '2022-11-28',
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`GitHub ${r.status}: ${data.message || 'ошибка'}`);
  return data;
}

async function createTask(env, agent, title, brief) {
  const issue = await gh(env, '/issues', {
    title: `[${AGENTS[agent]}] ${cut(title, 110) || 'Задача из Telegram'}`,
    body: !live(env) ? `${brief}\n\nИсполнитель: ${AGENTS[agent]}. Работать по правилам AGENTS.md, результат — PR; все изменения проходят через Claude Code.\n\n${MARK}` : `${brief}\n\n@${agent} возьми, пожалуйста, эту задачу. Работай по правилам AGENTS.md, результат — PR.${agent === 'codex' ? ' Не сливай PR сам: все изменения проходят через Claude Code, он проверит и доведёт.' : ''}\n\n${MARK}`,
  });
  await env.DB.put(`gh:agent:${issue.number}`, agent, { expirationTtl: TTL });
  return issue;
}

// ---------- Gemini ----------

async function route(env, text, force) {
  const payload = {
    systemInstruction: { parts: [{ text: ROUTER + (force ? `\nАгент уже выбран: ${force}. Оформи задачу для него.` : '') }] },
    contents: [{ role: 'user', parts: [{ text: cut(text, 8000) }] }],
    generationConfig: { temperature: 0.2, maxOutputTokens: 2048, responseMimeType: 'application/json' },
  };
  for (const model of MODELS) {
    for (const wait of [0, 1500]) {
      if (wait) await new Promise(ok => setTimeout(ok, wait));
      const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'x-goog-api-key': env.GEMINI_KEY }, body: JSON.stringify(payload),
      }).catch(() => null);
      if (!r?.ok) continue;
      const data = await r.json();
      const raw = data.candidates?.[0]?.content?.parts?.map(p => p.text || '').join('') || '';
      try {
        const out = JSON.parse(raw.replace(/^```(json)?|```$/g, '').trim());
        if (force) out.agent = force;
        if (!AGENTS[out.agent]) out.agent = 'claude';
        return out;
      } catch { /* кривой JSON — пробуем дальше */ }
    }
  }
  // Gemini недоступен: задача целиком, агент — по кнопке
  return { agent: force || 'claude', why: 'Gemini не ответил — выберите агента кнопкой', title: cut(text, 70), brief: text };
}

// ---------- входящие из Telegram ----------

function buttons(id, agent) {
  const other = agent === 'codex' ? 'claude' : 'codex';
  return { inline_keyboard: [
    [{ text: `✅ Отдать ${AGENTS[agent === 'gemini' ? 'claude' : agent]}`, callback_data: `go:${id}:${agent === 'gemini' ? 'claude' : agent}` }],
    [{ text: `→ ${AGENTS[other]}`, callback_data: `go:${id}:${other}` }, { text: '✖ Отмена', callback_data: `no:${id}` }],
  ] };
}

async function onMessage(env, msg) {
  const text = (msg.text || msg.caption || '').trim();
  if (!text) return say(env, 'Пока понимаю только текст. Картинку опишите словами или положите ссылку.');
  const [cmd, ...rest] = text.split(/\s+/);
  const arg = rest.join(' ').trim();

  if (cmd === '/start' || cmd === '/help') return say(env, HELP);

  // Реплай на сообщение агента → комментарий в тот же issue
  const replyTo = msg.reply_to_message?.message_id;
  const num = replyTo && await env.DB.get(`tg:msg:${replyTo}`);
  if (num && !cmd.startsWith('/')) {
    const agent = await env.DB.get(`gh:agent:${num}`) || 'claude';
    await gh(env, `/issues/${num}/comments`, { body: `${live(env) ? '@' + agent + ' ' : ''}${text}\n\n${MARK}` });
    return say(env, `${live(env) ? 'Передал ' + AGENTS[agent] : 'Добавил комментарий'} в задачу #${num}.`, { reply_to_message_id: msg.message_id });
  }

  if (cmd === '/grant') {
    const [whoArg, product, daysArg] = rest;
    const days = Number(daysArg);
    if (!whoArg || !['tutor', 'lib'].includes(product) || !(days > 0 && days <= 400)) return say(env, 'Формат: /grant <id|почта|telegram id> tutor|lib <дней>');
    const id = /^a[a-z0-9]{12}$/.test(whoArg) ? whoArg
      : await env.DB.get(whoArg.includes('@') ? `ident:email:${whoArg.toLowerCase()}` : `ident:tg:${whoArg}`);
    const acct = id && await extend(env, id, product, days, 'вручную');
    if (!acct) return say(env, 'Аккаунт не найден.');
    const until = new Date(planStatus(acct, product).until).toLocaleDateString('ru-RU');
    return say(env, `Готово: ${acct.name || acct.email || acct.id} — ${product === 'tutor' ? 'студия' : 'библиотека'} до ${until}.`);
  }

  if (cmd === '/stats') {
    const all = async prefix => { const keys = []; let cursor; do { const l = await env.DB.list({ prefix, cursor }); keys.push(...l.keys); cursor = l.list_complete ? null : l.cursor; } while (cursor); return keys; };
    const accts = (await Promise.all((await all('acct:')).map(k => getAccount(env, k.name.slice(5))))).filter(Boolean);
    const count = f => accts.filter(f).length;
    const paid = await Promise.all((await all('paid:')).map(k => env.DB.get(k.name, 'json')));
    const month = Date.now() - 30 * 86400e3;
    const sum = list => list.reduce((n, p) => n + Number(p?.amount || 0), 0);
    return say(env, [
      `Аккаунтов: ${accts.length} (репетиторов ${count(a => a.roles?.tutor)}, учеников ${count(a => a.roles?.student)}, родителей ${count(a => a.roles?.parent)})`,
      `Студия: пробный ${count(a => planStatus(a, 'tutor').trial)}, оплачено ${count(a => planStatus(a, 'tutor').paidUntil > Date.now())}`,
      `Библиотека: пробный ${count(a => planStatus(a, 'lib').trial)}, оплачено ${count(a => planStatus(a, 'lib').paidUntil > Date.now())}`,
      `Оплат всего: ${paid.length} на ${sum(paid)} ₽, за 30 дней: ${sum(paid.filter(p => p?.at > month))} ₽`,
    ].join('\n'));
  }

  if (cmd === '/status') {
    const list = await gh(env, '/issues?state=open&per_page=20');
    const mine = list.filter(i => (i.body || '').includes(MARK));
    if (!mine.length) return say(env, 'Открытых задач из Telegram нет.');
    const rows = await Promise.all(mine.map(async i => `#${i.number} ${AGENTS[await env.DB.get(`gh:agent:${i.number}`)] || '?'} — ${i.title}\n${i.html_url}`));
    return say(env, rows.join('\n\n'));
  }

  if (cmd === '/ask') {
    if (!arg) return say(env, 'Напишите вопрос после /ask');
    const r = await route(env, arg, 'gemini');
    return say(env, r.answer || r.brief || 'Gemini не ответил, попробуйте ещё раз.');
  }

  const force = cmd === '/claude' ? 'claude' : cmd === '/codex' ? 'codex' : null;
  const task = force ? arg : text;
  if (!task) return say(env, 'Напишите задачу после команды.');
  await tg(env, 'sendChatAction', { chat_id: env.TG_OWNER, action: 'typing' });
  const r = await route(env, task, force);
  if (r.agent === 'gemini' && r.answer) {
    const id = crypto.randomUUID().slice(0, 8);
    await env.DB.put(`tg:task:${id}`, JSON.stringify({ ...r, agent: 'claude', brief: r.brief || task }), { expirationTtl: 86400 });
    return say(env, `${r.answer}\n\n(Если это всё-таки задача для кода — выберите агента.)`, { reply_markup: buttons(id, 'gemini') });
  }
  const id = crypto.randomUUID().slice(0, 8);
  await env.DB.put(`tg:task:${id}`, JSON.stringify(r), { expirationTtl: 86400 });
  return say(env, `Кому: ${AGENTS[r.agent]} — ${r.why || ''}\n\n«${r.title}»\n\n${cut(r.brief, 2500)}`, { reply_markup: buttons(id, r.agent) });
}

async function onCallback(env, q) {
  const [act, id, agent] = (q.data || '').split(':');
  const saved = await env.DB.get(`tg:task:${id}`, 'json');
  const done = text => Promise.all([
    tg(env, 'answerCallbackQuery', { callback_query_id: q.id }),
    tg(env, 'editMessageReplyMarkup', { chat_id: env.TG_OWNER, message_id: q.message.message_id, reply_markup: { inline_keyboard: [] } }),
    text && say(env, text),
  ]);
  if (!saved) return done('Эта задача устарела — отправьте её заново.');
  await env.DB.delete(`tg:task:${id}`);
  if (act === 'no') return done('Отменено.');
  if (!AGENTS[agent] || agent === 'gemini') return done();
  const issue = await createTask(env, agent, saved.title, saved.brief);
  const m = await say(env, live(env)
    ? `Задача #${issue.number} отдана ${AGENTS[agent]}.\n${issue.html_url}\nОтветы агента будут приходить сюда.`
    : agent === 'codex'
      ? `Задача #${issue.number} для Codex записана.\n${issue.html_url}\n\nСкопируйте ТЗ ниже в ChatGPT/Codex, а готовый результат (PR или архив) передайте Claude на проверку.\n\n${cut(saved.brief, 3000)}`
      : `Задача #${issue.number} для Claude записана.\n${issue.html_url}\n\nНапишите Claude в приложении: «возьми задачи из бота» — он выполнит все открытые.`);
  if (m.result) await env.DB.put(`tg:msg:${m.result.message_id}`, String(issue.number), { expirationTtl: TTL });
  return done();
}

// ---------- входящие из GitHub ----------

async function hmacHex(secret, body) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(body));
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, '0')).join('');
}

function who(login = '') {
  const l = login.toLowerCase();
  return l.includes('claude') ? 'Claude' : l.includes('codex') || l.includes('chatgpt') ? 'Codex' : login;
}

async function forward(env, num, text) {
  const m = await say(env, text);
  if (m.result && num) await env.DB.put(`tg:msg:${m.result.message_id}`, String(num), { expirationTtl: TTL });
}

async function onGithub(env, event, p) {
  if (event === 'issue_comment') {
    const c = p.comment;
    if (!c || (c.body || '').includes(MARK)) return;
    const num = p.issue.number;
    // Claude правит один комментарий по ходу работы — пересылаем его, когда он закончил
    const busy = /is working|working on|работает над|in progress/i.test(c.body);
    if (!['created', 'edited'].includes(p.action) || busy) return;
    if (p.action === 'edited' && await env.DB.get(`gh:sent:${c.id}`)) return;
    await env.DB.put(`gh:sent:${c.id}`, '1', { expirationTtl: TTL });
    return forward(env, num, `💬 ${who(c.user?.login)} · #${num} «${cut(p.issue.title, 60)}»\n\n${cut(c.body, 3000)}\n\n${c.html_url}\n(ответьте реплаем, чтобы продолжить)`);
  }
  if (event === 'pull_request' && ['opened', 'closed', 'ready_for_review'].includes(p.action)) {
    const pr = p.pull_request;
    // Всё, что сделал не Claude (Codex, ChatGPT, правки руками), сначала проверяет Claude Code
    const fromClaude = /claude/i.test(pr.user?.login || '') || (pr.head?.ref || '').startsWith('claude/');
    if (!live(env) && p.action !== 'closed' && !fromClaude) {
      return forward(env, pr.number, `🆕 PR от ${who(pr.user?.login)}: #${pr.number} ${pr.title}\n${pr.html_url}\n\nПопросите Claude в приложении проверить его перед слиянием.`);
    }
    if (['opened', 'ready_for_review'].includes(p.action) && !pr.draft && !fromClaude && !await env.DB.get(`gh:review:${pr.number}`)) {
      await env.DB.put(`gh:review:${pr.number}`, '1', { expirationTtl: TTL });
      await env.DB.put(`gh:agent:${pr.number}`, 'claude', { expirationTtl: TTL });
      await gh(env, `/issues/${pr.number}/comments`, { body: `@claude проверь этот PR по AGENTS.md: открой страницы в браузере на 390 и 1280 px, в светлой и тёмной теме, прогони проверки. Исправь найденное прямо в этой ветке и напиши итог: можно ли сливать. Сам не сливай — решает владелец.\n\n${MARK}` });
      return forward(env, pr.number, `🆕 PR от ${who(pr.user?.login)}: #${pr.number} ${pr.title}\n${pr.html_url}\n\nОтдал Claude на проверку — пришлю, что он скажет.`);
    }
    const state = p.action === 'closed' ? (pr.merged ? '✅ смёржен' : 'закрыт') : '🆕 новый PR';
    return forward(env, null, `${state} · ${who(pr.user?.login)}\n#${pr.number} ${pr.title}\n${pr.html_url}`);
  }
  if (event === 'pull_request_review' && p.action === 'submitted' && p.review?.body) {
    return forward(env, null, `🔎 Ревью от ${who(p.review.user?.login)} к PR #${p.pull_request.number}\n\n${cut(p.review.body, 2500)}\n${p.review.html_url}`);
  }
}

// ---------- точка входа ----------

export async function handleBot(req, env, ctx) {
  const url = new URL(req.url);
  const text = (s, status = 200) => new Response(s, { status, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });

  if (url.pathname === '/tg/setup') {
    if (!env.TG_TOKEN || !env.TG_SECRET) return text('Задайте секреты TG_TOKEN и TG_SECRET.', 500);
    if (url.searchParams.get('key') !== env.TG_SECRET) return text('Неверный key.', 403);
    const hook = await tg(env, 'setWebhook', { url: `${url.origin}/tg`, secret_token: env.TG_SECRET, allowed_updates: ['message', 'callback_query'] });
    await tg(env, 'setMyCommands', { commands: [
      { command: 'claude', description: 'Задача Claude: логика, данные, сервер' },
      { command: 'codex', description: 'Задача Codex: дизайн и вёрстка' },
      { command: 'ask', description: 'Просто спросить Gemini' },
      { command: 'status', description: 'Открытые задачи' },
      { command: 'help', description: 'Как пользоваться' },
    ] });
    return text(hook.ok ? 'Готово: вебхук Telegram подключён. Напишите боту /start.' : `Telegram ответил: ${hook.description}`);
  }

  if (url.pathname === '/tg' && req.method === 'POST') {
    if (!env.TG_SECRET || req.headers.get('X-Telegram-Bot-Api-Secret-Token') !== env.TG_SECRET) return text('forbidden', 403);
    const upd = await req.json().catch(() => ({}));
    const chat = upd.message?.chat?.id ?? upd.callback_query?.message?.chat?.id;
    // Отвечаем Telegram сразу, работаем в фоне — иначе он повторит запрос
    ctx.waitUntil((async () => {
      try {
        // Вход на сайт: «/start login_<код>» принимаем от любого человека
        const login = /^\/start login_([a-z0-9]{24})$/.exec(upd.message?.text || '');
        if (login && upd.message.chat.type === 'private') {
          const ok = await confirmTelegram(env, login[1], upd.message.from);
          await tg(env, 'sendMessage', { chat_id: chat, text: ok
            ? '✅ Вход выполнен. Вернитесь на сайт «Между уроками» — страница откроется сама.'
            : 'Ссылка для входа устарела. Нажмите «Войти через Telegram» на сайте ещё раз.' });
          return;
        }
        if (!env.TG_OWNER) {
          if (chat) await tg(env, 'sendMessage', { chat_id: chat, text: `Ваш chat id: ${chat}\nДобавьте его в секрет TG_OWNER в Cloudflare — после этого бот начнёт принимать задачи только от вас.` });
          return;
        }
        if (String(chat) !== String(env.TG_OWNER)) return; // чужие чаты молча игнорируем
        if (upd.callback_query) await onCallback(env, upd.callback_query);
        else if (upd.message) await onMessage(env, upd.message);
      } catch (err) {
        await say(env, `Ошибка: ${err.message}`);
      }
    })());
    return text('ok');
  }

  if (url.pathname === '/gh' && req.method === 'POST') {
    const body = await req.text();
    const sig = req.headers.get('X-Hub-Signature-256') || '';
    if (!env.GH_SECRET || sig !== `sha256=${await hmacHex(env.GH_SECRET, body)}`) return text('bad signature', 401);
    const event = req.headers.get('X-GitHub-Event');
    if (env.TG_TOKEN && env.TG_OWNER) {
      ctx.waitUntil(onGithub(env, event, JSON.parse(body)).catch(err => say(env, `Ошибка вебхука GitHub: ${err.message}`)));
    }
    return text('ok');
  }
  return null;
}
