# Сервер «Между уроками» (Cloudflare Worker)

Один маленький Worker делает три вещи:

- **ИИ**: проверяет решения, даёт подсказки и делает карточки из материалов репетитора. Ключ Gemini хранится только на сервере.
- **Наборы**: хранит опубликованные тренажёры, ученик открывает их по ссылке `?t=<код>`.
- **Прогресс**: принимает сводки учеников и отдаёт их репетитору по ключу.

На бесплатных тарифах Cloudflare и Google AI Studio всё это стоит $0 при небольшом числе учеников.

## Быстрый способ: одна кнопка

[![Deploy to Cloudflare](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/kqrulev-oss/econcards/tree/main/worker)

1. Нажмите кнопку и войдите в Cloudflare (регистрация бесплатная). Cloudflare попросит подключить GitHub: он скопирует папку `worker/` в новый репозиторий в вашем аккаунте.
2. В поле `GEMINI_KEY` вставьте ключ Gemini (как его получить — шаг 1 ниже). Хранилище `DB` создастся само.
3. Нажмите **Deploy** и скопируйте адрес вида `https://zadachnik.<аккаунт>.workers.dev`.
4. Впишите этот адрес в `config.js` в корне сайта (шаг 4 ниже).

Ниже — то же самое вручную.

## 1. Ключ Gemini (1 минута)
1. Откройте https://aistudio.google.com/apikey — нужен только Google-аккаунт.
2. «Create API key», скопируйте ключ. С мая 2026 ключи начинаются с `AQ.` — это нормально, сервер передаёт их в заголовке `x-goog-api-key`, как требует Google.
3. Не подключайте к проекту оплату (billing): тогда при утечке ключа максимум закончится бесплатная квота.
4. Ключ кладите только в секрет Cloudflare (шаг 3 ниже), не в файлы репозитория и не в `config.js`.

## 2. Хранилище KV
Cloudflare → **Storage & Databases → KV → Create namespace**, например `ZADACHNIK`.

## 3. Worker
1. **Workers & Pages → Create → Worker**, имя `zadachnik`, **Deploy**, затем **Edit code**.
2. Вставьте содержимое `worker.js`, снова **Deploy**.
3. **Settings → Bindings → Add → KV namespace**: имя переменной `DB`, namespace из шага 2.
4. **Settings → Variables and Secrets**:
   - секрет `GEMINI_KEY` — ключ из шага 1;
   - (необязательно) `MODEL` — по умолчанию `gemini-flash-latest` (Google сам держит его на актуальной модели), при перегрузке сервер переключается на `gemini-flash-lite-latest`;
   - (необязательно) `DAILY_LIMIT` — ИИ-запросов на IP в сутки, по умолчанию 60.

Через Wrangler то же самое (файл `wrangler.toml` уже лежит в этой папке):
```
cd worker
npx wrangler kv namespace create DB      # выданный id вписать в wrangler.toml
npx wrangler deploy
npx wrangler secret put GEMINI_KEY       # ключ вводится в терминале, в файлы не попадает
```

## 4. Подключить
Впишите адрес Worker'а (`https://zadachnik.<аккаунт>.workers.dev`) в `config.js` в корне сайта — тогда он будет у всех учеников. Или только у себя: Студия → «Настройки» → «Сервер».

## Что уходит на сервер
- Проверка и подсказка: условие, эталонное решение, решение ученика.
- Генерация: текст материалов репетитора (до 30 000 символов).
- Прогресс: имя ученика, которое он сам ввёл, и сводка — сколько карточек решил, точность по темам, id карточек с ошибками. Сводки хранятся 180 дней.

Смотреть прогресс учеников может только тот, у кого есть ключ набора. Ключ создаётся в браузере репетитора при создании тренажёра и лежит там же, поэтому делайте резервную копию: Студия → «Настройки» → «Скачать набор».

## Telegram-бот: один чат для Claude и Codex

Код — `worker/bot.js`, работает на том же воркере. Вы пишете задачу боту, Gemini
решает, кому она (Codex — дизайн, Claude — логика и данные, Gemini — просто
ответить), и спрашивает подтверждение кнопкой. Бот создаёт issue на GitHub с
`@claude` или `@codex`, агенты делают PR, их ответы и PR приходят в чат.
Ответ реплаем на сообщение агента уходит ему в тот же issue.
Все изменения идут через Claude Code: каждый PR, который открыл не Claude (Codex,
ChatGPT, правки руками), бот сам отдаёт Claude на проверку, а тот доводит его и
пишет, можно ли сливать. Сливаете вы.

Настройка (один раз):

1. **Бот.** В Telegram откройте @BotFather → `/newbot` → получите токен.
2. **Токен GitHub.** github.com → Settings → Developer settings → Fine-grained tokens →
   Generate: Repository access — *Only select repositories* → `econcards`;
   Permissions: **Issues — Read and write**, **Pull requests — Read and write** (чтобы просить Claude проверить PR от Codex).
3. **Секреты в Cloudflare** (Workers → econcards → Settings → Variables and Secrets,
   тип *Secret*): `TG_TOKEN` (из п.1), `TG_SECRET` (любая длинная случайная строка),
   `GH_TOKEN` (из п.2), `GH_SECRET` (другая случайная строка).
4. Откройте `https://<адрес воркера>/tg/setup?key=<TG_SECRET>` — бот подключится.
   Напишите боту `/start`: он пришлёт ваш chat id. Добавьте его секретом `TG_OWNER`
   — теперь бот слушается только вас.
5. **Вебхук GitHub.** Репозиторий → Settings → Webhooks → Add webhook:
   Payload URL `https://<адрес воркера>/gh`, Content type `application/json`,
   Secret — значение `GH_SECRET`, события: *Issue comments*, *Pull requests*,
   *Pull request reviews*.
6. **Режим работы.** По умолчанию бот — пульт задач: пишет issue с пометкой
   `[Claude]` или `[Codex]`. Задачи Claude выполняет Claude Code в приложении
   (напишите ему «возьми задачи из бота»), ТЗ для Codex бот присылает текстом —
   его можно вставить в ChatGPT. Если позже подключите агентов к GitHub
   (приложение Claude + workflow с `anthropics/claude-code-action`, Codex на
   chatgpt.com/codex), добавьте переменную `AGENTS_ON_GITHUB=1` — бот начнёт
   звать их через `@claude` / `@codex` и отдавать чужие PR Claude на проверку.

Команды: `/claude …`, `/codex …` — отдать без выбора, `/ask …` — спросить Gemini,
`/status` — открытые задачи.
