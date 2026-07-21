/* ============================================================
   EconCards — AI-тренер · прокси на Cloudflare Worker
   ------------------------------------------------------------
   Держит ключ Gemini на сервере (в браузер не попадает), строит
   промпты по типу задачи, ограничивает запросы по IP в день.
   Полностью бесплатно на бесплатных тирах Cloudflare + Gemini.

   Деплой — см. ai/README.md. Переменные окружения:
     GEMINI_KEY  — секрет, ключ Google AI Studio (обязательно)
     MODEL       — модель Gemini (по умолч. gemini-2.0-flash)
     DAILY_LIMIT — лимит запросов на IP в сутки (по умолч. 40)
     RATE        — привязка KV-namespace для лимита (необязательно)
   ============================================================ */

const MODEL_DEFAULT = 'gemini-2.0-flash';
const MAX = 4000; // обрезаем длинные входы, чтобы не жечь токены

const cors = origin => ({
  'Access-Control-Allow-Origin': origin || '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400',
});
const reply = (obj, status, origin) =>
  new Response(JSON.stringify(obj), { status, headers: { ...cors(origin), 'Content-Type': 'application/json' } });
const cut = s => String(s || '').slice(0, MAX);

const SYSTEM = {
  check: 'Ты доброжелательный, но требовательный тренер по олимпиадной экономике. Тебе дают условие задачи, ЭТАЛОННОЕ решение и решение ученика. Сверь ход ученика с эталоном: отметь, что сделано верно, укажи конкретные ошибки и где именно, подскажи направление (не переписывай весь эталон, если ученик близок). В конце дай оценку в процентах. Пиши кратко и по делу, по-русски. Формулы — обычным текстом.',
  hint: 'Ты тренер по олимпиадной экономике. Дай РОВНО ОДНУ подсказку запрошенного уровня, НЕ раскрывая финальный ответ. Уровень 1 — идея/направление; уровень 2 — ключевой шаг; уровень 3 — почти полное решение, но без итогового числа. Кратко, по-русски.',
  explain: 'Ты тренер по олимпиадной экономике. Переобъясни эталонное решение ПРОЩЕ, чем в оригинале: другими словами, с интуицией и аналогией, по понятным шагам. По-русски.',
  similar: 'Ты автор задач по олимпиадной экономике. Придумай НОВУЮ похожую задачу того же типа и сложности, с конкретными числами, и приведи её краткое решение и ответ. Это учебная генерация — так и пометь. По-русски. Формат: «Задача: …\\n\\nРешение: …\\n\\nОтвет: …».',
};
const PROMPT = {
  check: d => `Условие:\n${cut(d.problem)}\n\nЭталонное решение:\n${cut(d.reference)}\n\nРешение ученика:\n${cut(d.answer)}\n\nПроверь решение ученика.`,
  hint: d => `Условие:\n${cut(d.problem)}\n\nЭталонное решение (ученику не показывай):\n${cut(d.reference)}\n\nДай подсказку уровня ${Math.max(1, Math.min(3, Number(d.level) || 1))}.`,
  explain: d => `Условие:\n${cut(d.problem)}\n\nЭталонное решение:\n${cut(d.reference)}\n\nПереобъясни это решение проще.`,
  similar: d => `Задача-образец:\n${cut(d.problem)}\n\nЭталон для стиля:\n${cut(d.reference)}\n\nПридумай похожую НОВУЮ задачу с решением и ответом.`,
};

export default {
  async fetch(req, env) {
    const origin = req.headers.get('Origin');
    if (req.method === 'OPTIONS') return new Response(null, { headers: cors(origin) });
    if (req.method !== 'POST') return reply({ error: 'method', message: 'Только POST.' }, 405, origin);
    if (!env.GEMINI_KEY) return reply({ error: 'config', message: 'На сервере не задан GEMINI_KEY.' }, 500, origin);

    let body;
    try { body = await req.json(); } catch { return reply({ error: 'json', message: 'Некорректный запрос.' }, 400, origin); }
    const task = body.task;
    if (!SYSTEM[task]) return reply({ error: 'task', message: 'Неизвестное действие.' }, 400, origin);

    // Лимит по IP в сутки (если привязан KV RATE)
    const limit = Number(env.DAILY_LIMIT || 40);
    let remaining = limit;
    if (env.RATE) {
      const ip = req.headers.get('CF-Connecting-IP') || 'anon';
      const day = new Date().toISOString().slice(0, 10);
      const key = `${ip}:${day}`;
      const used = Number((await env.RATE.get(key)) || 0);
      if (used >= limit) return reply({ error: 'limit', message: 'Дневной лимит AI исчерпан. Возвращайся завтра 🙂' }, 429, origin);
      await env.RATE.put(key, String(used + 1), { expirationTtl: 172800 });
      remaining = limit - used - 1;
    }

    const model = env.MODEL || MODEL_DEFAULT;
    const payload = {
      systemInstruction: { parts: [{ text: SYSTEM[task] }] },
      contents: [{ role: 'user', parts: [{ text: PROMPT[task](body) }] }],
      generationConfig: { temperature: task === 'similar' ? 0.7 : 0.3, maxOutputTokens: 900 },
    };
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${env.GEMINI_KEY}`;

    let r;
    try { r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }
    catch { return reply({ error: 'upstream', message: 'AI временно недоступен. Попробуй позже.' }, 502, origin); }
    if (!r.ok) {
      const t = await r.text().catch(() => '');
      return reply({ error: 'upstream', message: 'AI-сервис вернул ошибку. Проверь модель/ключ.', detail: t.slice(0, 300) }, 502, origin);
    }
    const data = await r.json();
    const text = (data.candidates?.[0]?.content?.parts || []).map(p => p.text).join('').trim() || 'Пустой ответ модели.';
    return reply({ text, remaining }, 200, origin);
  },
};
