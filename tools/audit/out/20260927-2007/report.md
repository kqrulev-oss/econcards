# Проверка живого сайта

Адрес: https://econcards.kqrulev.workers.dev · время: 2026-09-27T20:07:22.451Z

## Выводы

Проверка 27.09.2026, 20:07–20:58 UTC, живой сайт. Версия service worker на сайте — `zadachnik-v34`: PR #46 выложен. Вход в аккаунты не выполнялся, записей на сервер не было. Все 10 попыток записи заблокировала проверка (раздел 6).

### Что сломано

- **Несуществующая страница показывает человеку сырой JSON**: `/no-such-page-audit` → 404, `application/json`, на экране `{"error":true,"message":"Нет такого адреса."}` (скрин `shots/nav-375-light/15-несуществующая-страница.png`). `404.html` в репозитории есть, но на сайте не включена: `not_found_handling` в `wrangler.jsonc` не задан, это правка с согласия владельца. Это та же проблема № 38 из `docs/audit.md`.
- **Ошибок JavaScript нет** ни в путях, ни в обходе (324 нажатия, 64 страницы). В консоли только ожидаемые 404: неизвестный код тренажёра `/packs/zzzz1234` и несуществующая страница. Пустых экранов, вечной «Загрузки» и 5xx нет.
- **Остальные пометки из разделов 2 и 3 — не поломки**:
  - «окно висит» в пути репетитора — окна, открытые по задумке: «Глазами ученика» открывается само вместе с примером, «Отчёт», вход перед публикацией;
  - шаг 05 «не вышло» — скрипт жмёт кнопку под уже открытым окном «Глазами ученика»;
  - шаг 14 — у гостя в студии ссылки на кабинет нет по задумке, она только для вошедших (`studio/studio.js:176`);
  - «ничего не происходит» — это:
    - вопросы в `<details>`;
    - кнопки входа Telegram и «Код на почту»: их POST заблокировала проверка;
    - «Импорт из файла» (окно выбора файла);
    - переключатели предмета;
    - ответы демо-карточки на главной;
  - «не нажимается» — ссылки на оферту и политику внутри закрытого `<details>`;
  - «назад» → `/manifest.webmanifest` — это страница сброса самого обхода; из занятия «назад» по задумке спрашивает «Выйти из занятия?».
- **Офлайн работает как задумано** в обоих режимах. Страницы, которые не открывали, показывают «Нет связи», незнакомый набор — «Нет связи — этот набор ещё не открывали» с «Повторить». Ответов API в кэше нет.
- **Для сведения:** у гостя с черновиком кнопка «Похожие» отправляет `POST /ai` без входа (заблокирован проверкой, раздел 6). Возможно, так задумано, но это единственная запись без входа, кроме кнопок входа.

### Что медленно

Цифры «3G» здесь выше, чем в локальной проверке, и сравнивать их напрямую нельзя. Браузер ходит через прокси облачной среды, и открытие страницы даже без замедления занимает 0,5–1,2 с. Сравнивать стоит строки между собой.

- **Кабинет без входа — самый медленный переход**: первый экран 1,1 с на обычной сети и 7,7 с на 3G, 23 запроса. Сначала целиком грузится `/cabinet/`: HTML, CSS, `lib.js`, `account.js`, `config.js`, шрифты. Потом JS переводит на `login.html`, Cloudflare отвечает 307 на `/login`, и всё грузится второй раз (раздел 5, «повтор … ×2»). Старый адрес `/parent/` добавляет ещё один шаг: `/parent/` → `/cabinet/#parent` → `login.html` → `/login`. Итого 1,2 с на обычной сети и 8,9 с на 3G.
- **Библиотека ЕГЭ, первое открытие**: 6,2 с на 3G, 476 КБ, из них 250 КБ — `packs/ege-rus.json`. Повторно — 4,4 с и 6 КБ: набор приходит ответом 304.
- **Вход**: 4,3–4,4 с на 3G, из них один лишний круг — 307 с `login.html` на `/login`.
- **Service worker**: в режиме «3G+SW» на главной (15 ответов из SW) первый экран — 1,4 с вместо 4,4 с. На входе ответов из SW 13, первый экран — 2,6 с вместо 4,3 с. На студии, библиотеке, кабинете и оферте из SW не пришло ни одного ответа: он не успел установиться за прогревочный заход на медленной сети. Поэтому эти цифры равны «повторно без SW».
- **Переходы внутри страницы** (библиотека: задание, теория, занятие) — 1–18 мс даже на 3G.

### Чем живой сайт отличается от локальной проверки

- **Перенаправления `.html` → без `.html`**: `/login.html`, `/offer.html`, `/privacy.html`, `/offline.html` отвечают 307 на `/login`, `/offer`, `/privacy`, `/offline`. Так же `/index.html` → `/`, а `/studio`, `/cabinet`, `/parent` → со слэшем. Локальный мок отдавал `.html` сразу с кодом 200. На сайте ссылки на `login.html`, `offer.html`, `privacy.html` остаются в `landing.js`, `account.js`, `studio/studio.js`, `cabinet/cabinet.js`, `app.js`. Каждый такой переход стоит лишнего круга: около 0,56 с на 3G. Service worker это учитывает, ключ страницы без `.html`, и офлайн-переходы на `login.html` работают.
- **Заголовки кэша**: страницы, JS, CSS, шрифты, `packs/*.free.json` и `sample-*.json` — `public, max-age=0, must-revalidate`, с weak ETag и сжатием br. Полный набор `packs/ege-rus.json` из воркера — `no-cache`. API (`/auth/providers`, `/pay/prices`, `/me`) — без `Cache-Control`.
- **ETag/304 у библиотеки работает**, в отличие от локального мока. `packs/ege-rus.json` и `ege-math.json` с `If-None-Match` получают 304 и 0 байт, повторное открытие библиотеки весит 6 КБ вместо 476 КБ. Готовая бесплатная часть `ege-rus.free.json` совпадает с тем, что воркер отдаёт гостю: тот же ETag, 27 тем / 1199 карточек; у математики — 19 тем / 111 карточек.
- **Способы входа**: включены Telegram, почта и Яндекс ID; VK и Google выключены (`/auth/providers`). В окне входа три кнопки. Локально были все способы.
- **Ответ на несуществующую страницу**: JSON воркера (404, `application/json`, 60 байт), а не страница сайта. Локально была голая 404 сервера. `404.html` не подключена ни там, ни там.

### Замечания о самой проверке

- Сначала Chromium не доверял CA прокси среды (`ERR_CERT_AUTHORITY_INVALID`). Сертификаты прокси добавлены в хранилище NSS браузера (`certutil`), проверка TLS не отключалась. Прогон начат заново.
- Прокси «3G» (`tools/audit/throttle-proxy.mjs`) переставлял куски данных, и TLS рвался: `ERR_SSL_PROTOCOL_ERROR`, `ERR_RESPONSE_HEADERS_TRUNCATED`. Исправлено отдельным коммитом, замер скорости перезапущен. В разделе 5 — результат после исправления, сбоев нет.

Проверка только читает: записи на сервер (вход, отправка прогресса, оплата, ИИ, бот) браузер не отправлял — такие попытки перечислены в разделе 6.

## Коротко

- **Адреса:** 42 проверено, проблем — 4. Перенаправления: /login.html → 307 /login; /offer.html → 307 /offer; /privacy.html → 307 /privacy; /offline.html → 307 /offline; /studio → 307 /studio/; /cabinet → 307 /cabinet/; /parent → 307 /parent/; /index.html → 307 /; /packs/ege-rus.json → 304 ; /packs/ege-math.json → 304 .
- **Способы входа на сервере:** tg ✓, email ✓, yandex ✓, vk ✗, google ✗.
- **Библиотека для гостя:** ege-rus: 27 тем / 1199 карточек, готовый файл совпадает; ege-math: 19 тем / 111 карточек, готовый файл совпадает.
- **Путь tutor (1280, light):** 14 шагов, с проблемами — 6: 03 «выбор предмета (если спрашивают) → Русский», 04 «пример открыт: карточки», 05 ««Глазами ученика»», 08 ««Отчёт родителям» у ученика-примера», 11 ««Опубликовать» без входа → вход», 14 «путь в кабинет из студии».
- **Путь library (1280, light):** 14 шагов, с проблемами — 0.
- **Путь nav (1280, light):** 15 шагов, с проблемами — 2: 13 «неизвестный код тренажёра», 15 «несуществующая страница».
- **Путь tutor (375, dark):** 14 шагов, с проблемами — 6: 03 «выбор предмета (если спрашивают) → Русский», 04 «пример открыт: карточки», 05 ««Глазами ученика»», 08 ««Отчёт родителям» у ученика-примера», 11 ««Опубликовать» без входа → вход», 14 «путь в кабинет из студии».
- **Путь library (375, dark):** 14 шагов, с проблемами — 0.
- **Путь nav (375, dark):** 15 шагов, с проблемами — 2: 13 «неизвестный код тренажёра», 15 «несуществующая страница».
- **Путь tutor (375, light):** 14 шагов, с проблемами — 6: 03 «выбор предмета (если спрашивают) → Русский», 04 «пример открыт: карточки», 05 ««Глазами ученика»», 08 ««Отчёт родителям» у ученика-примера», 11 ««Опубликовать» без входа → вход», 14 «путь в кабинет из студии».
- **Путь library (375, light):** 14 шагов, с проблемами — 0.
- **Путь nav (375, light):** 15 шагов, с проблемами — 2: 13 «неизвестный код тренажёра», 15 «несуществующая страница».
- **Обход:** 6 прогонов, 64 страниц, 324 ссылок и кнопок нажато (260 повторов пропущено), с проблемами — 129.
- **Офлайн (visited, 375):** всё открывается как задумано.
- **Офлайн (landing-only, 375):** всё открывается как задумано.
- **Попытки записи (заблокированы проверкой):** 10.

## 1. Адреса

| Адрес | Статус | мс | Байт | Сжатие | Cache-Control | Замечания |
|---|---|---|---|---|---|---|
| / | 200 | 304 | 2100 | br | public, max-age=0, must-revalidate |  |
| /?about | 200 | 85 | 2100 | br | public, max-age=0, must-revalidate |  |
| /studio/ | 200 | 80 | 1931 | br | public, max-age=0, must-revalidate |  |
| /cabinet/ | 200 | 73 | 1311 | br | public, max-age=0, must-revalidate |  |
| /login.html | 307 → /login | 61 | 0 | — | — | ✗ статус 307, ожидали 200; тип «», ожидали text/html |
| /offer.html | 307 → /offer | 197 | 0 | — | — | ✗ статус 307, ожидали 200; тип «», ожидали text/html |
| /privacy.html | 307 → /privacy | 53 | 0 | — | — | ✗ статус 307, ожидали 200; тип «», ожидали text/html |
| /offline.html | 307 → /offline | 63 | 0 | — | — | ✗ статус 307, ожидали 200; тип «», ожидали text/html |
| /studio <br><sub>перенаправление?</sub> | 307 → /studio/ | 52 | 0 | — | — |  |
| /cabinet <br><sub>перенаправление?</sub> | 307 → /cabinet/ | 54 | 0 | — | — |  |
| /login <br><sub>перенаправление?</sub> | 200 | 64 | 1259 | br | public, max-age=0, must-revalidate |  |
| /parent/ <br><sub>перенаправление?</sub> | 200 | 89 | 871 | br | public, max-age=0, must-revalidate |  |
| /parent <br><sub>перенаправление?</sub> | 307 → /parent/ | 59 | 0 | — | — |  |
| /index.html <br><sub>перенаправление?</sub> | 307 → / | 67 | 0 | — | — |  |
| /no-such-page-audit <br><sub>нет такой страницы</sub> | 404 | 65 | 60 | br | — |  |
| /app.js | 200 | 76 | 86863 | br | public, max-age=0, must-revalidate |  |
| /lib.js | 200 | 58 | 26219 | br | public, max-age=0, must-revalidate |  |
| /account.js | 200 | 62 | 29422 | br | public, max-age=0, must-revalidate |  |
| /landing.js | 200 | 63 | 21721 | br | public, max-age=0, must-revalidate |  |
| /app.css | 200 | 69 | 88128 | br | public, max-age=0, must-revalidate |  |
| /sw.js | 200 | 59 | 8516 | br | public, max-age=0, must-revalidate |  |
| /manifest.webmanifest | 200 | 65 | 784 | br | public, max-age=0, must-revalidate |  |
| /studio/studio.js | 200 | 71 | 121973 | br | public, max-age=0, must-revalidate |  |
| /cabinet/cabinet.js | 200 | 78 | 32083 | br | public, max-age=0, must-revalidate |  |
| /login.js | 200 | 59 | 8663 | br | public, max-age=0, must-revalidate |  |
| /fonts/nunito-cyrillic.woff2 | 200 | 68 | 20776 | — | public, max-age=0, must-revalidate |  |
| /fonts/unbounded-cyrillic.woff2 | 200 | 66 | 31424 | — | public, max-age=0, must-revalidate |  |
| /vendor/qrcode.js | 200 | 61 | 56694 | br | public, max-age=0, must-revalidate |  |
| /packs/index.json | 200 | 68 | 1294 | br | public, max-age=0, must-revalidate |  |
| /packs/ege-rus.json <br><sub>гостю — бесплатная часть</sub> | 200 | 139 | 1192935 | br | no-cache |  |
| /packs/ege-rus.free.json <br><sub>заранее собранная бесплатная часть</sub> | 200 | 107 | 1192935 | br | public, max-age=0, must-revalidate |  |
| /packs/ege-rus.json <br><sub>повтор с If-None-Match</sub> | 304 | 66 | 0 | — | no-cache |  |
| /packs/ege-math.json <br><sub>гостю — бесплатная часть</sub> | 200 | 116 | 247275 | br | no-cache |  |
| /packs/ege-math.free.json <br><sub>заранее собранная бесплатная часть</sub> | 200 | 82 | 247275 | br | public, max-age=0, must-revalidate |  |
| /packs/ege-math.json <br><sub>повтор с If-None-Match</sub> | 304 | 60 | 0 | — | no-cache |  |
| /packs/sample-rus.json <br><sub>пример для студии</sub> | 200 | 62 | 44739 | br | public, max-age=0, must-revalidate | 3 тем, 36 карточек |
| /packs/sample-math.json <br><sub>пример для студии</sub> | 200 | 68 | 30207 | br | public, max-age=0, must-revalidate | 3 тем, 18 карточек |
| /auth/providers | 200 | 55 | 64 | br | — |  |
| /pay/prices | 200 | 58 | 129 | br | — |  |
| /me <br><sub>без входа — отказ</sub> | 401 | 54 | 49 | — | — |  |
| /packs/zzzz1234 <br><sub>неизвестный тренажёр</sub> | 404 | 161 | 107 | br | — |  |
| /packs/zzzz1234/progress <br><sub>чужой прогресс без ключа</sub> | 404 | 149 | 56 | br | — |  |

## 2. Пути

### tutor — 1280 px, light

| № | Шаг | Адрес | Заголовок | Проблемы / заметки | Скриншот |
|---|---|---|---|---|---|
| 01 | главная | / | Домашка, от которой не сбегают |  | `shots/tutor-1280-light/01-главная.png` |
| 02 | «Попробовать» | /studio/#/sample | Готовый пример |  | `shots/tutor-1280-light/02--Попробовать-.png` |
| 03 | выбор предмета (если спрашивают) → Русский | /studio/#/p/ewnr4qc3/cards | Пример: русский, ЕГЭ | окно висит ×1 | `shots/tutor-1280-light/03-выбор-предмета-если-спрашивают-Русский.png` |
| 04 | пример открыт: карточки | /studio/#/p/ewnr4qc3/cards | Пример: русский, ЕГЭ | окно висит ×1 | `shots/tutor-1280-light/04-пример-открыт-карточки.png` |
| 05 | «Глазами ученика» | /studio/#/p/ewnr4qc3/cards | Пример: русский, ЕГЭ | не вышло: locator.click: Timeout 4000ms exceeded. · окно висит ×1 | `shots/tutor-1280-light/05--Глазами-ученика-.png` |
| 06 | закрыть просмотр (Esc) | /studio/#/p/ewnr4qc3/cards | Пример: русский, ЕГЭ |  | `shots/tutor-1280-light/06-закрыть-просмотр-Esc-.png` |
| 07 | вкладка «Ученики» | /studio/#/p/ewnr4qc3/students | Пример: русский, ЕГЭ |  | `shots/tutor-1280-light/07-вкладка-Ученики-.png` |
| 08 | «Отчёт родителям» у ученика-примера | /studio/#/p/ewnr4qc3/students | Пример: русский, ЕГЭ | окно висит ×1 | `shots/tutor-1280-light/08--Отчёт-родителям-у-ученика-примера.png` |
| 09 | телефонное «назад» закрывает окно | /studio/#/p/ewnr4qc3/students | Пример: русский, ЕГЭ |  | `shots/tutor-1280-light/09-телефонное-назад-закрывает-окно.png` |
| 10 | вкладка «Публикация» / «Опубликовать» | /studio/#/p/ewnr4qc3/publish | Пример: русский, ЕГЭ |  | `shots/tutor-1280-light/10-вкладка-Публикация-Опубликовать-.png` |
| 11 | «Опубликовать» без входа → вход | /studio/#/p/ewnr4qc3/publish | Пример: русский, ЕГЭ | окно висит ×1 | `shots/tutor-1280-light/11--Опубликовать-без-входа-вход.png` |
| 12 | «назад» из входа → студия, пример на месте | /studio/#/p/ewnr4qc3/publish | Пример: русский, ЕГЭ |  | `shots/tutor-1280-light/12--назад-из-входа-студия-пример-на-месте.png` |
| 13 | перезагрузка студии | /studio/#/p/ewnr4qc3/publish | Пример: русский, ЕГЭ |  | `shots/tutor-1280-light/13-перезагрузка-студии.png` |
| 14 | путь в кабинет из студии | /studio/#/p/ewnr4qc3/publish | Пример: русский, ЕГЭ | не вышло: не нашёл: a[href*="cabinet"] \| a:has-text("Кабинет") | `shots/tutor-1280-light/14-путь-в-кабинет-из-студии.png` |

### library — 1280 px, light

| № | Шаг | Адрес | Заголовок | Проблемы / заметки | Скриншот |
|---|---|---|---|---|---|
| 01 | библиотека ЕГЭ: русский | /?p=ege-rus | Привет! |  | `shots/library-1280-light/01-библиотека-ЕГЭ-русский.png` |
| 02 | задание 4 | /?p=ege-rus#/topic/task-4 | Ударение |  | `shots/library-1280-light/02-задание-4.png` |
| 03 | теория задания | /?p=ege-rus#/lesson/RU002 | Фонетика, буквы, звуки и ударение |  | `shots/library-1280-light/03-теория-задания.png` |
| 04 | «назад» → задание | /?p=ege-rus#/topic/task-4 | Ударение |  | `shots/library-1280-light/04--назад-задание.png` |
| 05 | «назад» → главная тренажёра | /?p=ege-rus | Привет! |  | `shots/library-1280-light/05--назад-главная-тренажёра.png` |
| 06 | «Заниматься» | /?p=ege-rus#/s |  |  | `shots/library-1280-light/06--Заниматься-.png` |
| 07 | ответить на 5 карточек | /?p=ege-rus#/s |  |  | `shots/library-1280-light/07-ответить-на-5-карточек.png` |
| 08 | телефонное «назад» посреди занятия (отказаться выходить) | /?p=ege-rus#/s |  | спросили: «Выйти из занятия?» | `shots/library-1280-light/08-телефонное-назад-посреди-занятия-отказаться-выходи.png` |
| 09 | доиграть до «Готово» | /?p=ege-rus#/s | Серия 1 день! |  | `shots/library-1280-light/09-доиграть-до-Готово-.png` |
| 10 | «назад» после «Готово» не возвращает в занятие | /?p=ege-rus | Привет! |  | `shots/library-1280-light/10--назад-после-Готово-не-возвращает-в-занятие.png` |
| 11 | профиль | /?p=ege-rus#/me | Профиль |  | `shots/library-1280-light/11-профиль.png` |
| 12 | все наборы | /?p=ege-rus#/library | Открытые наборы |  | `shots/library-1280-light/12-все-наборы.png` |
| 13 | ЕГЭ: математика | /?p=ege-math | Привет! |  | `shots/library-1280-light/13-ЕГЭ-математика.png` |
| 14 | перезагрузка | /?p=ege-math | Привет! |  | `shots/library-1280-light/14-перезагрузка.png` |

### nav — 1280 px, light

| № | Шаг | Адрес | Заголовок | Проблемы / заметки | Скриншот |
|---|---|---|---|---|---|
| 01 | главная | / | Домашка, от которой не сбегают |  | `shots/nav-1280-light/01-главная.png` |
| 02 | якорь #how | /#how | Домашка, от которой не сбегают | перерисовок: 0 | `shots/nav-1280-light/02-якорь-how.png` |
| 03 | якорь #prices | /#prices | Домашка, от которой не сбегают | перерисовок: 0 | `shots/nav-1280-light/03-якорь-prices.png` |
| 04 | якорь #faq | /#faq | Домашка, от которой не сбегают | перерисовок: 0 | `shots/nav-1280-light/04-якорь-faq.png` |
| 05 | пустой код «Открыть» | /#faq | Домашка, от которой не сбегают |  | `shots/nav-1280-light/05-пустой-код-Открыть-.png` |
| 06 | «Войти» | /login | Вход в «Между уроками» |  | `shots/nav-1280-light/06--Войти-.png` |
| 07 | «назад» с входа | /#faq | Домашка, от которой не сбегают |  | `shots/nav-1280-light/07--назад-с-входа.png` |
| 08 | кабинет без входа | /login?next=cabinet%2F | Вход в «Между уроками» |  | `shots/nav-1280-light/08-кабинет-без-входа.png` |
| 09 | кабинет родителя без входа | /login?role=parent&next=cabinet%2F%23parent | Вход в «Между уроками» |  | `shots/nav-1280-light/09-кабинет-родителя-без-входа.png` |
| 10 | /parent/ (старый адрес) | /login?role=parent&next=cabinet%2F%23parent | Вход в «Между уроками» |  | `shots/nav-1280-light/10--parent-старый-адрес-.png` |
| 11 | оферта | /offer | Публичная оферта |  | `shots/nav-1280-light/11-оферта.png` |
| 12 | политика | /privacy | Политика обработки персональных данных |  | `shots/nav-1280-light/12-политика.png` |
| 13 | неизвестный код тренажёра | /?t=zzzz1234 |  | ошибки ×2 · console: Failed to load resource: the server responded with a status of 404 (Not Found) · http404: GET /packs/zzzz1234 | `shots/nav-1280-light/13-неизвестный-код-тренажёра.png` |
| 14 | «К наборам» / выход с неизвестного кода | /#/library | Открытые наборы |  | `shots/nav-1280-light/14--К-наборам-выход-с-неизвестного-кода.png` |
| 15 | несуществующая страница | /no-such-page-audit |  | ошибки ×1 · http404: GET /no-such-page-audit · статус 404 | `shots/nav-1280-light/15-несуществующая-страница.png` |

### tutor — 375 px, dark

| № | Шаг | Адрес | Заголовок | Проблемы / заметки | Скриншот |
|---|---|---|---|---|---|
| 01 | главная | / | Домашка, от которой не сбегают |  | `shots/tutor-375-dark/01-главная.png` |
| 02 | «Попробовать» | /studio/#/sample | Готовый пример |  | `shots/tutor-375-dark/02--Попробовать-.png` |
| 03 | выбор предмета (если спрашивают) → Русский | /studio/#/p/b6y9nzc7/cards | Пример: русский, ЕГЭ | окно висит ×1 | `shots/tutor-375-dark/03-выбор-предмета-если-спрашивают-Русский.png` |
| 04 | пример открыт: карточки | /studio/#/p/b6y9nzc7/cards | Пример: русский, ЕГЭ | окно висит ×1 | `shots/tutor-375-dark/04-пример-открыт-карточки.png` |
| 05 | «Глазами ученика» | /studio/#/p/b6y9nzc7/cards | Пример: русский, ЕГЭ | не вышло: locator.click: Timeout 4000ms exceeded. · окно висит ×1 | `shots/tutor-375-dark/05--Глазами-ученика-.png` |
| 06 | закрыть просмотр (Esc) | /studio/#/p/b6y9nzc7/cards | Пример: русский, ЕГЭ |  | `shots/tutor-375-dark/06-закрыть-просмотр-Esc-.png` |
| 07 | вкладка «Ученики» | /studio/#/p/b6y9nzc7/students | Пример: русский, ЕГЭ |  | `shots/tutor-375-dark/07-вкладка-Ученики-.png` |
| 08 | «Отчёт родителям» у ученика-примера | /studio/#/p/b6y9nzc7/students | Пример: русский, ЕГЭ | окно висит ×1 | `shots/tutor-375-dark/08--Отчёт-родителям-у-ученика-примера.png` |
| 09 | телефонное «назад» закрывает окно | /studio/#/p/b6y9nzc7/students | Пример: русский, ЕГЭ |  | `shots/tutor-375-dark/09-телефонное-назад-закрывает-окно.png` |
| 10 | вкладка «Публикация» / «Опубликовать» | /studio/#/p/b6y9nzc7/publish | Пример: русский, ЕГЭ |  | `shots/tutor-375-dark/10-вкладка-Публикация-Опубликовать-.png` |
| 11 | «Опубликовать» без входа → вход | /studio/#/p/b6y9nzc7/publish | Пример: русский, ЕГЭ | окно висит ×1 | `shots/tutor-375-dark/11--Опубликовать-без-входа-вход.png` |
| 12 | «назад» из входа → студия, пример на месте | /studio/#/p/b6y9nzc7/publish | Пример: русский, ЕГЭ |  | `shots/tutor-375-dark/12--назад-из-входа-студия-пример-на-месте.png` |
| 13 | перезагрузка студии | /studio/#/p/b6y9nzc7/publish | Пример: русский, ЕГЭ |  | `shots/tutor-375-dark/13-перезагрузка-студии.png` |
| 14 | путь в кабинет из студии | /studio/#/p/b6y9nzc7/publish | Пример: русский, ЕГЭ | не вышло: не нашёл: a[href*="cabinet"] \| a:has-text("Кабинет") | `shots/tutor-375-dark/14-путь-в-кабинет-из-студии.png` |

### library — 375 px, dark

| № | Шаг | Адрес | Заголовок | Проблемы / заметки | Скриншот |
|---|---|---|---|---|---|
| 01 | библиотека ЕГЭ: русский | /?p=ege-rus | Привет! |  | `shots/library-375-dark/01-библиотека-ЕГЭ-русский.png` |
| 02 | задание 4 | /?p=ege-rus#/topic/task-4 | Ударение |  | `shots/library-375-dark/02-задание-4.png` |
| 03 | теория задания | /?p=ege-rus#/lesson/RU002 | Фонетика, буквы, звуки и ударение |  | `shots/library-375-dark/03-теория-задания.png` |
| 04 | «назад» → задание | /?p=ege-rus#/topic/task-4 | Ударение |  | `shots/library-375-dark/04--назад-задание.png` |
| 05 | «назад» → главная тренажёра | /?p=ege-rus | Привет! |  | `shots/library-375-dark/05--назад-главная-тренажёра.png` |
| 06 | «Заниматься» | /?p=ege-rus#/s |  |  | `shots/library-375-dark/06--Заниматься-.png` |
| 07 | ответить на 5 карточек | /?p=ege-rus#/s |  |  | `shots/library-375-dark/07-ответить-на-5-карточек.png` |
| 08 | телефонное «назад» посреди занятия (отказаться выходить) | /?p=ege-rus#/s |  | спросили: «Выйти из занятия?» | `shots/library-375-dark/08-телефонное-назад-посреди-занятия-отказаться-выходи.png` |
| 09 | доиграть до «Готово» | /?p=ege-rus#/s | Серия 1 день! |  | `shots/library-375-dark/09-доиграть-до-Готово-.png` |
| 10 | «назад» после «Готово» не возвращает в занятие | /?p=ege-rus | Привет! |  | `shots/library-375-dark/10--назад-после-Готово-не-возвращает-в-занятие.png` |
| 11 | профиль | /?p=ege-rus#/me | Профиль |  | `shots/library-375-dark/11-профиль.png` |
| 12 | все наборы | /?p=ege-rus#/library | Открытые наборы |  | `shots/library-375-dark/12-все-наборы.png` |
| 13 | ЕГЭ: математика | /?p=ege-math | Привет! |  | `shots/library-375-dark/13-ЕГЭ-математика.png` |
| 14 | перезагрузка | /?p=ege-math | Привет! |  | `shots/library-375-dark/14-перезагрузка.png` |

### nav — 375 px, dark

| № | Шаг | Адрес | Заголовок | Проблемы / заметки | Скриншот |
|---|---|---|---|---|---|
| 01 | главная | / | Домашка, от которой не сбегают |  | `shots/nav-375-dark/01-главная.png` |
| 02 | якорь #how | /#how | Домашка, от которой не сбегают | перерисовок: 0 | `shots/nav-375-dark/02-якорь-how.png` |
| 03 | якорь #prices | /#prices | Домашка, от которой не сбегают | перерисовок: 0 | `shots/nav-375-dark/03-якорь-prices.png` |
| 04 | якорь #faq | /#faq | Домашка, от которой не сбегают | перерисовок: 0 | `shots/nav-375-dark/04-якорь-faq.png` |
| 05 | пустой код «Открыть» | /#faq | Домашка, от которой не сбегают |  | `shots/nav-375-dark/05-пустой-код-Открыть-.png` |
| 06 | «Войти» | /login | Вход в «Между уроками» |  | `shots/nav-375-dark/06--Войти-.png` |
| 07 | «назад» с входа | /#faq | Домашка, от которой не сбегают |  | `shots/nav-375-dark/07--назад-с-входа.png` |
| 08 | кабинет без входа | /login?next=cabinet%2F | Вход в «Между уроками» |  | `shots/nav-375-dark/08-кабинет-без-входа.png` |
| 09 | кабинет родителя без входа | /login?role=parent&next=cabinet%2F%23parent | Вход в «Между уроками» |  | `shots/nav-375-dark/09-кабинет-родителя-без-входа.png` |
| 10 | /parent/ (старый адрес) | /login?role=parent&next=cabinet%2F%23parent | Вход в «Между уроками» |  | `shots/nav-375-dark/10--parent-старый-адрес-.png` |
| 11 | оферта | /offer | Публичная оферта |  | `shots/nav-375-dark/11-оферта.png` |
| 12 | политика | /privacy | Политика обработки персональных данных |  | `shots/nav-375-dark/12-политика.png` |
| 13 | неизвестный код тренажёра | /?t=zzzz1234 |  | ошибки ×2 · console: Failed to load resource: the server responded with a status of 404 (Not Found) · http404: GET /packs/zzzz1234 | `shots/nav-375-dark/13-неизвестный-код-тренажёра.png` |
| 14 | «К наборам» / выход с неизвестного кода | /#/library | Открытые наборы |  | `shots/nav-375-dark/14--К-наборам-выход-с-неизвестного-кода.png` |
| 15 | несуществующая страница | /no-such-page-audit |  | ошибки ×1 · http404: GET /no-such-page-audit · статус 404 | `shots/nav-375-dark/15-несуществующая-страница.png` |

### tutor — 375 px, light

| № | Шаг | Адрес | Заголовок | Проблемы / заметки | Скриншот |
|---|---|---|---|---|---|
| 01 | главная | / | Домашка, от которой не сбегают |  | `shots/tutor-375-light/01-главная.png` |
| 02 | «Попробовать» | /studio/#/sample | Готовый пример |  | `shots/tutor-375-light/02--Попробовать-.png` |
| 03 | выбор предмета (если спрашивают) → Русский | /studio/#/p/hgsbpmap/cards | Пример: русский, ЕГЭ | окно висит ×1 | `shots/tutor-375-light/03-выбор-предмета-если-спрашивают-Русский.png` |
| 04 | пример открыт: карточки | /studio/#/p/hgsbpmap/cards | Пример: русский, ЕГЭ | окно висит ×1 | `shots/tutor-375-light/04-пример-открыт-карточки.png` |
| 05 | «Глазами ученика» | /studio/#/p/hgsbpmap/cards | Пример: русский, ЕГЭ | не вышло: locator.click: Timeout 4000ms exceeded. · окно висит ×1 | `shots/tutor-375-light/05--Глазами-ученика-.png` |
| 06 | закрыть просмотр (Esc) | /studio/#/p/hgsbpmap/cards | Пример: русский, ЕГЭ |  | `shots/tutor-375-light/06-закрыть-просмотр-Esc-.png` |
| 07 | вкладка «Ученики» | /studio/#/p/hgsbpmap/students | Пример: русский, ЕГЭ |  | `shots/tutor-375-light/07-вкладка-Ученики-.png` |
| 08 | «Отчёт родителям» у ученика-примера | /studio/#/p/hgsbpmap/students | Пример: русский, ЕГЭ | окно висит ×1 | `shots/tutor-375-light/08--Отчёт-родителям-у-ученика-примера.png` |
| 09 | телефонное «назад» закрывает окно | /studio/#/p/hgsbpmap/students | Пример: русский, ЕГЭ |  | `shots/tutor-375-light/09-телефонное-назад-закрывает-окно.png` |
| 10 | вкладка «Публикация» / «Опубликовать» | /studio/#/p/hgsbpmap/publish | Пример: русский, ЕГЭ |  | `shots/tutor-375-light/10-вкладка-Публикация-Опубликовать-.png` |
| 11 | «Опубликовать» без входа → вход | /studio/#/p/hgsbpmap/publish | Пример: русский, ЕГЭ | окно висит ×1 | `shots/tutor-375-light/11--Опубликовать-без-входа-вход.png` |
| 12 | «назад» из входа → студия, пример на месте | /studio/#/p/hgsbpmap/publish | Пример: русский, ЕГЭ |  | `shots/tutor-375-light/12--назад-из-входа-студия-пример-на-месте.png` |
| 13 | перезагрузка студии | /studio/#/p/hgsbpmap/publish | Пример: русский, ЕГЭ |  | `shots/tutor-375-light/13-перезагрузка-студии.png` |
| 14 | путь в кабинет из студии | /studio/#/p/hgsbpmap/publish | Пример: русский, ЕГЭ | не вышло: не нашёл: a[href*="cabinet"] \| a:has-text("Кабинет") | `shots/tutor-375-light/14-путь-в-кабинет-из-студии.png` |

### library — 375 px, light

| № | Шаг | Адрес | Заголовок | Проблемы / заметки | Скриншот |
|---|---|---|---|---|---|
| 01 | библиотека ЕГЭ: русский | /?p=ege-rus | Привет! |  | `shots/library-375-light/01-библиотека-ЕГЭ-русский.png` |
| 02 | задание 4 | /?p=ege-rus#/topic/task-4 | Ударение |  | `shots/library-375-light/02-задание-4.png` |
| 03 | теория задания | /?p=ege-rus#/lesson/RU002 | Фонетика, буквы, звуки и ударение |  | `shots/library-375-light/03-теория-задания.png` |
| 04 | «назад» → задание | /?p=ege-rus#/topic/task-4 | Ударение |  | `shots/library-375-light/04--назад-задание.png` |
| 05 | «назад» → главная тренажёра | /?p=ege-rus | Привет! |  | `shots/library-375-light/05--назад-главная-тренажёра.png` |
| 06 | «Заниматься» | /?p=ege-rus#/s |  |  | `shots/library-375-light/06--Заниматься-.png` |
| 07 | ответить на 5 карточек | /?p=ege-rus#/s |  |  | `shots/library-375-light/07-ответить-на-5-карточек.png` |
| 08 | телефонное «назад» посреди занятия (отказаться выходить) | /?p=ege-rus#/s |  | спросили: «Выйти из занятия?» | `shots/library-375-light/08-телефонное-назад-посреди-занятия-отказаться-выходи.png` |
| 09 | доиграть до «Готово» | /?p=ege-rus#/s | Серия 1 день! |  | `shots/library-375-light/09-доиграть-до-Готово-.png` |
| 10 | «назад» после «Готово» не возвращает в занятие | /?p=ege-rus | Привет! |  | `shots/library-375-light/10--назад-после-Готово-не-возвращает-в-занятие.png` |
| 11 | профиль | /?p=ege-rus#/me | Профиль |  | `shots/library-375-light/11-профиль.png` |
| 12 | все наборы | /?p=ege-rus#/library | Открытые наборы |  | `shots/library-375-light/12-все-наборы.png` |
| 13 | ЕГЭ: математика | /?p=ege-math | Привет! |  | `shots/library-375-light/13-ЕГЭ-математика.png` |
| 14 | перезагрузка | /?p=ege-math | Привет! |  | `shots/library-375-light/14-перезагрузка.png` |

### nav — 375 px, light

| № | Шаг | Адрес | Заголовок | Проблемы / заметки | Скриншот |
|---|---|---|---|---|---|
| 01 | главная | / | Домашка, от которой не сбегают |  | `shots/nav-375-light/01-главная.png` |
| 02 | якорь #how | /#how | Домашка, от которой не сбегают | перерисовок: 0 | `shots/nav-375-light/02-якорь-how.png` |
| 03 | якорь #prices | /#prices | Домашка, от которой не сбегают | перерисовок: 0 | `shots/nav-375-light/03-якорь-prices.png` |
| 04 | якорь #faq | /#faq | Домашка, от которой не сбегают | перерисовок: 0 | `shots/nav-375-light/04-якорь-faq.png` |
| 05 | пустой код «Открыть» | /#faq | Домашка, от которой не сбегают |  | `shots/nav-375-light/05-пустой-код-Открыть-.png` |
| 06 | «Войти» | /login | Вход в «Между уроками» |  | `shots/nav-375-light/06--Войти-.png` |
| 07 | «назад» с входа | /#faq | Домашка, от которой не сбегают |  | `shots/nav-375-light/07--назад-с-входа.png` |
| 08 | кабинет без входа | /login?next=cabinet%2F | Вход в «Между уроками» |  | `shots/nav-375-light/08-кабинет-без-входа.png` |
| 09 | кабинет родителя без входа | /login?role=parent&next=cabinet%2F%23parent | Вход в «Между уроками» |  | `shots/nav-375-light/09-кабинет-родителя-без-входа.png` |
| 10 | /parent/ (старый адрес) | /login?role=parent&next=cabinet%2F%23parent | Вход в «Между уроками» |  | `shots/nav-375-light/10--parent-старый-адрес-.png` |
| 11 | оферта | /offer | Публичная оферта |  | `shots/nav-375-light/11-оферта.png` |
| 12 | политика | /privacy | Политика обработки персональных данных |  | `shots/nav-375-light/12-политика.png` |
| 13 | неизвестный код тренажёра | /?t=zzzz1234 |  | ошибки ×2 · console: Failed to load resource: the server responded with a status of 404 (Not Found) · http404: GET /packs/zzzz1234 | `shots/nav-375-light/13-неизвестный-код-тренажёра.png` |
| 14 | «К наборам» / выход с неизвестного кода | /#/library | Открытые наборы |  | `shots/nav-375-light/14--К-наборам-выход-с-неизвестного-кода.png` |
| 15 | несуществующая страница | /no-such-page-audit |  | ошибки ×1 · http404: GET /no-such-page-audit · статус 404 | `shots/nav-375-light/15-несуществующая-страница.png` |

## 3. Обход ссылок и кнопок

| Роль, ширина | Страница | Загрузка, мс | Статус | Ошибки при загрузке |
|---|---|---|---|---|
| guest 1280 | https://econcards.kqrulev.workers.dev/ → / | 1012 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/?about → /?about | 1005 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/#/library → /#/library | 852 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/login → /login | 1097 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/login?role=parent → /login?role=parent | 948 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/login?next=%2Fcabinet%2F → /login?next=%2Fcabinet%2F | 806 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/studio/ → /studio/ | 717 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/studio/#/sample → /studio/#/sample | 714 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/login?next=cabinet%2F → /login?next=cabinet%2F | 1539 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/login?role=parent&next=cabinet%2F%23parent → /login?role=parent&next=cabinet%2F%23parent | 1444 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/login?role=parent&next=cabinet%2F%23parent → /login?role=parent&next=cabinet%2F%23parent | 1649 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/offer → /offer | 587 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/privacy → /privacy | 569 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus → /?p=ege-rus | 920 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/?p=ege-math → /?p=ege-math | 874 | 200 |  |
| guest 1280 | https://econcards.kqrulev.workers.dev/?t=zzzz1234 → /?t=zzzz1234 | 670 | 200 | console: Failed to load resource: the server responded with a status of 404 (Not Found) · http404: GET /packs/zzzz1234 |
| guest 1280 | https://econcards.kqrulev.workers.dev/offline → /offline | 590 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/ → / | 1384 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/?about → /?about | 1171 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/#/library → /#/library | 780 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/login → /login | 1230 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/login?role=parent → /login?role=parent | 1015 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/login?next=%2Fcabinet%2F → /login?next=%2Fcabinet%2F | 1158 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/studio/ → /studio/ | 602 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/studio/#/sample → /studio/#/sample | 709 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/login?next=cabinet%2F → /login?next=cabinet%2F | 1521 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/login?role=parent&next=cabinet%2F%23parent → /login?role=parent&next=cabinet%2F%23parent | 1359 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/login?role=parent&next=cabinet%2F%23parent → /login?role=parent&next=cabinet%2F%23parent | 1828 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/offer → /offer | 550 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/privacy → /privacy | 596 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus → /?p=ege-rus | 843 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/?p=ege-math → /?p=ege-math | 935 | 200 |  |
| guest 375 | https://econcards.kqrulev.workers.dev/?t=zzzz1234 → /?t=zzzz1234 | 722 | 200 | console: Failed to load resource: the server responded with a status of 404 (Not Found) · http404: GET /packs/zzzz1234 |
| guest 375 | https://econcards.kqrulev.workers.dev/offline → /offline | 624 | 200 |  |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/ → /studio/ | 675 | 200 |  |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/cards → /studio/#/p/gdraft01/cards | 575 | 200 |  |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add → /studio/#/p/gdraft01/add | 731 | 200 |  |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/course → /studio/#/p/gdraft01/course | 654 | 200 |  |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/students → /studio/#/p/gdraft01/students | 654 | 200 |  |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings → /studio/#/p/gdraft01/settings | 701 | 200 |  |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/publish → /studio/#/p/gdraft01/publish | 708 | 200 |  |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/ → /studio/ | 673 | 200 |  |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/cards → /studio/#/p/gdraft01/cards | 618 | 200 |  |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add → /studio/#/p/gdraft01/add | 626 | 200 |  |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/course → /studio/#/p/gdraft01/course | 648 | 200 |  |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/students → /studio/#/p/gdraft01/students | 634 | 200 |  |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings → /studio/#/p/gdraft01/settings | 590 | 200 |  |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/publish → /studio/#/p/gdraft01/publish | 748 | 200 |  |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/ → /?p=ege-rus#/ | 893 | 200 |  |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-4 → /?p=ege-rus#/topic/task-4 | 948 | 200 |  |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-26 → /?p=ege-rus#/topic/task-26 | 910 | 200 |  |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/me → /?p=ege-rus#/me | 891 | 200 |  |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/library → /?p=ege-rus#/library | 1024 | 200 |  |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/s → /?p=ege-rus#/s | 855 | 200 |  |
| library 1280 | https://econcards.kqrulev.workers.dev/ → / | 864 | 200 |  |
| library 1280 | https://econcards.kqrulev.workers.dev/login?next=cabinet%2F → /login?next=cabinet%2F | 1515 | 200 |  |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/ → /?p=ege-rus#/ | 782 | 200 |  |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-4 → /?p=ege-rus#/topic/task-4 | 902 | 200 |  |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-26 → /?p=ege-rus#/topic/task-26 | 883 | 200 |  |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/me → /?p=ege-rus#/me | 840 | 200 |  |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/library → /?p=ege-rus#/library | 982 | 200 |  |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/s → /?p=ege-rus#/s | 935 | 200 |  |
| library 375 | https://econcards.kqrulev.workers.dev/ → / | 808 | 200 |  |
| library 375 | https://econcards.kqrulev.workers.dev/login?next=cabinet%2F → /login?next=cabinet%2F | 1334 | 200 |  |

**Элементы с проблемами**

| Роль, ширина | Страница | Элемент | Что произошло | Проблемы |
|---|---|---|---|---|
| guest 1280 | https://econcards.kqrulev.workers.dev/ | a «Между уроками» ./ | full → / (1160 мс) | «назад» → /manifest.webmanifest |
| guest 1280 | https://econcards.kqrulev.workers.dev/ | button «н»  | nothing → / (1 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/ | button «нн»  | nothing → / (1 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/ | summary «Какие предметы подходят?»  | nothing → / (2 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/ | summary «А если ИИ ошибётся в карточке?»  | nothing → / (2 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/ | summary «Сколько времени это займёт у ученика?»  | nothing → / (2 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/ | summary «Что видят родители?»  | nothing → / (1 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/ | summary «Какие данные хранятся?»  | nothing → / (1 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/ | a «» privacy.html | nothing → / (0 мс) | ничего не происходит · не нажимается |
| guest 1280 | https://econcards.kqrulev.workers.dev/ | summary «Как вернуть деньги?»  | nothing → / (2 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/ | a «» offer.html | nothing → / (0 мс) | ничего не происходит · не нажимается |
| guest 1280 | https://econcards.kqrulev.workers.dev/ | a «kqrulev@yandex.ru» mailto:kqrulev@yandex.ru | nothing → / (5 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/login | button «Репетитор»  | nothing → /login (141 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/login | button «ЧЕРЕЗ TELEGRAM»  | nothing → /login (12 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/login | button «КОД НА ПОЧТУ»  | nothing → /login (2 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/login?role=parent | button «Родитель»  | nothing → /login?role=parent (146 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/studio/ | button «Русский»  | nothing → /studio/ (0 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/studio/ | button «Математика»  | nothing → /studio/ (0 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/studio/ | button «Готовый пример за 1 клик»  | hash → /studio/#/p/zaw4zffk/cards (173 мс) | окно осталось висеть · «назад» → /studio/#/p/zaw4zffk/cards |
| guest 1280 | https://econcards.kqrulev.workers.dev/studio/ | button «Импорт из файла»  | nothing → /studio/ (0 мс) | ничего не происходит |
| guest 1280 | https://econcards.kqrulev.workers.dev/studio/#/sample | button «РУССКИЙ ЯЗЫК»  | hash → /studio/#/p/mpifiqyj/cards (149 мс) | окно осталось висеть · «назад» → /studio/#/p/mpifiqyj/cards |
| guest 1280 | https://econcards.kqrulev.workers.dev/studio/#/sample | button «МАТЕМАТИКА»  | hash → /studio/#/p/47zdg3ap/cards (152 мс) | окно осталось висеть · «назад» → /studio/#/p/47zdg3ap/cards |
| guest 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus | button «ЗАНИМАТЬСЯ · 6 МИН»  | hash → /?p=ege-rus#/s (3 мс) | «назад» → /?p=ege-rus#/s |
| guest 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus | button «Пробный вариант»  | hash → /?p=ege-rus#/s (3 мс) | «назад» → /?p=ege-rus#/s |
| guest 1280 | https://econcards.kqrulev.workers.dev/offline | button «ПОВТОРИТЬ»  | full → /offline (456 мс) | «назад» → /manifest.webmanifest |
| guest 1280 | https://econcards.kqrulev.workers.dev/offline | a «Личный кабинет Ученики и отчёты обновятся, когда появится св» cabinet/ | full+redirect → /login?next=cabinet%2F (1354 мс) | повторные запросы: GET /app.css ×2, GET /account.js ×2, GET /lib.js ×2, GET /config.js ×2, GET /fonts/nunito-cyrillic.woff2 ×2, GET /fonts/nunito-latin.woff2 ×2 |
| guest 375 | https://econcards.kqrulev.workers.dev/ | a «Между уроками» ./ | full → / (1248 мс) | «назад» → /manifest.webmanifest |
| guest 375 | https://econcards.kqrulev.workers.dev/ | button «н»  | nothing → / (1 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/ | button «нн»  | nothing → / (1 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/ | summary «Какие предметы подходят?»  | nothing → / (2 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/ | summary «А если ИИ ошибётся в карточке?»  | nothing → / (1 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/ | summary «Сколько времени это займёт у ученика?»  | nothing → / (2 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/ | summary «Что видят родители?»  | nothing → / (2 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/ | summary «Какие данные хранятся?»  | nothing → / (2 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/ | a «» privacy.html | nothing → / (0 мс) | ничего не происходит · не нажимается |
| guest 375 | https://econcards.kqrulev.workers.dev/ | summary «Как вернуть деньги?»  | nothing → / (2 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/ | a «» offer.html | nothing → / (0 мс) | ничего не происходит · не нажимается |
| guest 375 | https://econcards.kqrulev.workers.dev/ | a «kqrulev@yandex.ru» mailto:kqrulev@yandex.ru | nothing → / (4 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/login | button «Репетитор»  | nothing → /login (169 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/login | button «ЧЕРЕЗ TELEGRAM»  | nothing → /login (12 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/login | button «КОД НА ПОЧТУ»  | nothing → /login (2 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/login?role=parent | button «Родитель»  | nothing → /login?role=parent (138 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/studio/ | button «Русский»  | nothing → /studio/ (0 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/studio/ | button «Математика»  | nothing → /studio/ (0 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/studio/ | button «Готовый пример за 1 клик»  | hash → /studio/#/p/jd638yjt/cards (192 мс) | окно осталось висеть · «назад» → /studio/#/p/jd638yjt/cards |
| guest 375 | https://econcards.kqrulev.workers.dev/studio/ | button «Импорт из файла»  | nothing → /studio/ (0 мс) | ничего не происходит |
| guest 375 | https://econcards.kqrulev.workers.dev/studio/#/sample | button «РУССКИЙ ЯЗЫК»  | hash → /studio/#/p/xgth75pq/cards (150 мс) | окно осталось висеть · «назад» → /studio/#/p/xgth75pq/cards |
| guest 375 | https://econcards.kqrulev.workers.dev/studio/#/sample | button «МАТЕМАТИКА»  | hash → /studio/#/p/nrbiq22s/cards (148 мс) | окно осталось висеть · «назад» → /studio/#/p/nrbiq22s/cards |
| guest 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus | button «ЗАНИМАТЬСЯ · 6 МИН»  | hash → /?p=ege-rus#/s (3 мс) | «назад» → /?p=ege-rus#/s |
| guest 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus | button «Пробный вариант»  | hash → /?p=ege-rus#/s (3 мс) | «назад» → /?p=ege-rus#/s |
| guest 375 | https://econcards.kqrulev.workers.dev/offline | button «ПОВТОРИТЬ»  | full → /offline (442 мс) | «назад» → /manifest.webmanifest |
| guest 375 | https://econcards.kqrulev.workers.dev/offline | a «Личный кабинет Ученики и отчёты обновятся, когда появится св» cabinet/ | full+redirect → /login?next=cabinet%2F (1424 мс) | повторные запросы: GET /app.css ×2, GET /lib.js ×2, GET /account.js ×2, GET /config.js ×2, GET /fonts/nunito-latin.woff2 ×2, GET /fonts/nunito-cyrillic.woff2 ×2 |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/ | button «Русский»  | nothing → /studio/ (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/ | button «Математика»  | nothing → /studio/ (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/ | button «Готовый пример за 1 клик»  | hash → /studio/#/p/thpeq4em/cards (176 мс) | окно осталось висеть · «назад» → /studio/#/p/thpeq4em/cards |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/ | button «Импорт из файла»  | nothing → /studio/ (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/cards | a «Карточки · 1» #/p/gdraft01/cards | nothing → /studio/#/p/gdraft01/cards (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/cards | button «✕»  | nothing → /studio/#/p/gdraft01/cards (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add | a «Добавить» #/p/gdraft01/add | nothing → /studio/#/p/gdraft01/add (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add | button «+ PDF, фото или .txt»  | nothing → /studio/#/p/gdraft01/add (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add | button «ЕГЭ: русский язык · 1783»  | nothing → /studio/#/p/gdraft01/add (205 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add | button «ЕГЭ: профильная математика · 237»  | nothing → /studio/#/p/gdraft01/add (157 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add | button «Олимпиадная экономика · 1229»  | nothing → /studio/#/p/gdraft01/add (167 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add | button «Ударения · 394»  | nothing → /studio/#/p/gdraft01/add (121 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/course | a «Курс» #/p/gdraft01/course | nothing → /studio/#/p/gdraft01/course (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/students | a «Ученики» #/p/gdraft01/students | nothing → /studio/#/p/gdraft01/students (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | a «Настройки» #/p/gdraft01/settings | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #5B3DF5»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #0E7C86»  | nothing → /studio/#/p/gdraft01/settings (1 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #2F6BFF»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #1F8A4C»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #C2185B»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #D8452B»  | nothing → /studio/#/p/gdraft01/settings (1 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #8A4FFF»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #1B1440»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Удалить»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Удалить тренажёр»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 1280 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/publish | a «Опубликовать» #/p/gdraft01/publish | nothing → /studio/#/p/gdraft01/publish (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/ | button «Русский»  | nothing → /studio/ (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/ | button «Математика»  | nothing → /studio/ (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/ | button «Готовый пример за 1 клик»  | hash → /studio/#/p/fkaqukfi/cards (153 мс) | окно осталось висеть · «назад» → /studio/#/p/fkaqukfi/cards |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/ | button «Импорт из файла»  | nothing → /studio/ (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/cards | a «Карточки · 1» #/p/gdraft01/cards | nothing → /studio/#/p/gdraft01/cards (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/cards | button «✕»  | nothing → /studio/#/p/gdraft01/cards (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add | a «Добавить» #/p/gdraft01/add | nothing → /studio/#/p/gdraft01/add (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add | button «+ PDF, фото или .txt»  | nothing → /studio/#/p/gdraft01/add (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add | button «ЕГЭ: русский язык · 1783»  | nothing → /studio/#/p/gdraft01/add (213 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add | button «ЕГЭ: профильная математика · 237»  | nothing → /studio/#/p/gdraft01/add (136 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add | button «Олимпиадная экономика · 1229»  | nothing → /studio/#/p/gdraft01/add (149 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/add | button «Ударения · 394»  | nothing → /studio/#/p/gdraft01/add (146 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/course | a «Курс» #/p/gdraft01/course | nothing → /studio/#/p/gdraft01/course (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/students | a «Ученики» #/p/gdraft01/students | nothing → /studio/#/p/gdraft01/students (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | a «Настройки» #/p/gdraft01/settings | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #5B3DF5»  | nothing → /studio/#/p/gdraft01/settings (1 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #0E7C86»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #2F6BFF»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #1F8A4C»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #C2185B»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #D8452B»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #8A4FFF»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Цвет #1B1440»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Удалить»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/settings | button «Удалить тренажёр»  | nothing → /studio/#/p/gdraft01/settings (0 мс) | ничего не происходит |
| guest-draft 375 | https://econcards.kqrulev.workers.dev/studio/#/p/gdraft01/publish | a «Опубликовать» #/p/gdraft01/publish | nothing → /studio/#/p/gdraft01/publish (0 мс) | ничего не происходит |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/ | button «ПРОДОЛЖИТЬ · 3 МИН»  | hash → /?p=ege-rus#/s (3 мс) | «назад» → /?p=ege-rus#/s |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/ | button «Пробный вариант»  | hash → /?p=ege-rus#/s (3 мс) | «назад» → /?p=ege-rus#/s |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-4 | button «Тренировать все»  | hash → /?p=ege-rus#/s (2 мс) | «назад» → /?p=ege-rus#/s |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-4 | button «— Ударение в именах существительных Запоминайте слова с непо»  | hash → /?p=ege-rus#/s (1 мс) | «назад» → /?p=ege-rus#/s |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-4 | button «— Ударение в глаголах В глаголах прошедшего времени женского»  | hash → /?p=ege-rus#/s (2 мс) | «назад» → /?p=ege-rus#/s |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-26 | button «— Рецензия и средства выразительности Сопоставьте термины из»  | hash → /?p=ege-rus#/s (2 мс) | «назад» → /?p=ege-rus#/s |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-26 | button «— Связь предложений в тексте Определите средство связи сосед»  | hash → /?p=ege-rus#/s (1 мс) | «назад» → /?p=ege-rus#/s |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/me | button «Сбросить прогресс по набору»  | nothing → /?p=ege-rus#/me (0 мс) | ничего не происходит |
| library 1280 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/s | button «✕»  | hash → /?p=ege-rus#/ (4 мс) | «назад» → /manifest.webmanifest |
| library 1280 | https://econcards.kqrulev.workers.dev/login?next=cabinet%2F | button «Репетитор»  | nothing → /login?next=cabinet%2F (134 мс) | ничего не происходит |
| library 1280 | https://econcards.kqrulev.workers.dev/login?next=cabinet%2F | button «ЧЕРЕЗ TELEGRAM»  | nothing → /login?next=cabinet%2F (14 мс) | ничего не происходит |
| library 1280 | https://econcards.kqrulev.workers.dev/login?next=cabinet%2F | button «КОД НА ПОЧТУ»  | nothing → /login?next=cabinet%2F (1 мс) | ничего не происходит |
| library 1280 | https://econcards.kqrulev.workers.dev/login?next=cabinet%2F | a «политикой обработки данных» https://econcards.kqrulev.workers.dev/privacy.html | nothing → /login?next=cabinet%2F (0 мс) | ничего не происходит |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/ | button «ПРОДОЛЖИТЬ · 3 МИН»  | hash → /?p=ege-rus#/s (2 мс) | «назад» → /?p=ege-rus#/s |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/ | button «Пробный вариант»  | hash → /?p=ege-rus#/s (3 мс) | «назад» → /?p=ege-rus#/s |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-4 | button «Тренировать все»  | hash → /?p=ege-rus#/s (2 мс) | «назад» → /?p=ege-rus#/s |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-4 | button «— Ударение в именах существительных Запоминайте слова с непо»  | hash → /?p=ege-rus#/s (1 мс) | «назад» → /?p=ege-rus#/s |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-4 | button «— Ударение в глаголах В глаголах прошедшего времени женского»  | hash → /?p=ege-rus#/s (2 мс) | «назад» → /?p=ege-rus#/s |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-26 | button «— Рецензия и средства выразительности Сопоставьте термины из»  | hash → /?p=ege-rus#/s (3 мс) | «назад» → /?p=ege-rus#/s |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/topic/task-26 | button «— Связь предложений в тексте Определите средство связи сосед»  | hash → /?p=ege-rus#/s (2 мс) | «назад» → /?p=ege-rus#/s |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/me | button «Сбросить прогресс по набору»  | nothing → /?p=ege-rus#/me (0 мс) | ничего не происходит |
| library 375 | https://econcards.kqrulev.workers.dev/?p=ege-rus#/s | button «✕»  | hash → /?p=ege-rus#/ (5 мс) | «назад» → /manifest.webmanifest |
| library 375 | https://econcards.kqrulev.workers.dev/login?next=cabinet%2F | button «Репетитор»  | nothing → /login?next=cabinet%2F (265 мс) | ничего не происходит |
| library 375 | https://econcards.kqrulev.workers.dev/login?next=cabinet%2F | button «ЧЕРЕЗ TELEGRAM»  | nothing → /login?next=cabinet%2F (11 мс) | ничего не происходит |
| library 375 | https://econcards.kqrulev.workers.dev/login?next=cabinet%2F | button «КОД НА ПОЧТУ»  | nothing → /login?next=cabinet%2F (3 мс) | ничего не происходит |

## 4. Офлайн (service worker)

### Страницы открывали онлайн — 375 px

В кэше 29 файлов (zadachnik-v34); ответы API в кэше: нет.

| Шаг | Адрес | Итог | Что на экране | Скриншот |
|---|---|---|---|---|
| онлайн: главная (ставится service worker) | /?about |  | Домашка, от которой не сбегают | `shots/offline-visited-375/01-онлайн-главная-ставится-service-worker-.png` |
| онлайн: библиотека ?p=ege-rus | /?p=ege-rus |  | Привет! | `shots/offline-visited-375/02-онлайн-библиотека-p-ege-rus.png` |
| онлайн: студия | /studio/ |  | Студия | `shots/offline-visited-375/03-онлайн-студия.png` |
| онлайн: вход | /login |  | Вход в «Между уроками» | `shots/offline-visited-375/04-онлайн-вход.png` |
| онлайн: кабинет | /login?next=cabinet%2F |  | Вход в «Между уроками» | `shots/offline-visited-375/05-онлайн-кабинет.png` |
| ОФЛАЙН: главная | /?about | ok | Домашка, от которой не сбегают | `shots/offline-visited-375/06-ОФЛАЙН-главная.png` |
| ОФЛАЙН: библиотека | /?p=ege-rus | ok | Привет! | `shots/offline-visited-375/07-ОФЛАЙН-библиотека.png` |
| ОФЛАЙН: «Заниматься» в библиотеке | /?p=ege-rus#/s | ok | ✕ 1/10 12 Личные окончания глаголов и спряжение Вставьте букву: «Они слыш..т музыку». Показать ответ | `shots/offline-visited-375/08-ОФЛАЙН-Заниматься-в-библиотеке.png` |
| ОФЛАЙН: задание 4 | /?p=ege-rus#/topic/task-4 | ok | Ударение | `shots/offline-visited-375/09-ОФЛАЙН-задание-4.png` |
| ОФЛАЙН: студия | /studio/ | ok | Студия | `shots/offline-visited-375/10-ОФЛАЙН-студия.png` |
| ОФЛАЙН: вход | /login.html | ok | Вход в «Между уроками» | `shots/offline-visited-375/11-ОФЛАЙН-вход.png` |
| ОФЛАЙН: кабинет | /login.html?next=cabinet%2F | ok | Вход в «Между уроками» | `shots/offline-visited-375/12-ОФЛАЙН-кабинет.png` |
| ОФЛАЙН: оферта (не открывали) | /offer.html | ok | Нет связи | `shots/offline-visited-375/13-ОФЛАЙН-оферта-не-открывали-.png` |
| ОФЛАЙН: политика (не открывали) | /privacy.html | ok | Нет связи | `shots/offline-visited-375/14-ОФЛАЙН-политика-не-открывали-.png` |
| ОФЛАЙН: неизвестный тренажёр | /?t=zzzz1234 | ok | Нет связи — этот набор ещё не открывали на этом устройстве. Подключитесь к интернету и нажмите «Повторить». Повторить К наборам | `shots/offline-visited-375/15-ОФЛАЙН-неизвестный-тренажёр.png` |
| ОФЛАЙН: /parent/ | /login.html?role=parent&next=cabinet%2F%23parent | ok | Вход в «Между уроками» | `shots/offline-visited-375/16-ОФЛАЙН-parent-.png` |
| СНОВА ОНЛАЙН: студия | /studio/ | ok | Студия | `shots/offline-visited-375/17-СНОВА-ОНЛАЙН-студия.png` |

### Онлайн открыли только главную — 375 px

В кэше 28 файлов (zadachnik-v34); ответы API в кэше: нет.

| Шаг | Адрес | Итог | Что на экране | Скриншот |
|---|---|---|---|---|
| онлайн: главная (ставится service worker) | /?about |  | Домашка, от которой не сбегают | `shots/offline-landing-only-375/01-онлайн-главная-ставится-service-worker-.png` |
| ОФЛАЙН: главная | /?about | ok | Домашка, от которой не сбегают | `shots/offline-landing-only-375/02-ОФЛАЙН-главная.png` |
| ОФЛАЙН: библиотека | /?p=ege-rus | ok | Нет связи — этот набор ещё не открывали на этом устройстве. Подключитесь к интернету и нажмите «Повторить». Повторить К наборам | `shots/offline-landing-only-375/03-ОФЛАЙН-библиотека.png` |
| ОФЛАЙН: задание 4 | /?p=ege-rus#/topic/task-4 | ok | Нет связи — этот набор ещё не открывали на этом устройстве. Подключитесь к интернету и нажмите «Повторить». Повторить К наборам | `shots/offline-landing-only-375/04-ОФЛАЙН-задание-4.png` |
| ОФЛАЙН: студия | /studio/ | ok | Студия | `shots/offline-landing-only-375/05-ОФЛАЙН-студия.png` |
| ОФЛАЙН: вход | /login.html | ok | Вход в «Между уроками» | `shots/offline-landing-only-375/06-ОФЛАЙН-вход.png` |
| ОФЛАЙН: кабинет | /login.html?next=cabinet%2F | ok | Вход в «Между уроками» | `shots/offline-landing-only-375/07-ОФЛАЙН-кабинет.png` |
| ОФЛАЙН: оферта (не открывали) | /offer.html | ok | Нет связи | `shots/offline-landing-only-375/08-ОФЛАЙН-оферта-не-открывали-.png` |
| ОФЛАЙН: политика (не открывали) | /privacy.html | ok | Нет связи | `shots/offline-landing-only-375/09-ОФЛАЙН-политика-не-открывали-.png` |
| ОФЛАЙН: неизвестный тренажёр | /?t=zzzz1234 | ok | Нет связи — этот набор ещё не открывали на этом устройстве. Подключитесь к интернету и нажмите «Повторить». Повторить К наборам | `shots/offline-landing-only-375/10-ОФЛАЙН-неизвестный-тренажёр.png` |
| ОФЛАЙН: /parent/ | /login.html?role=parent&next=cabinet%2F%23parent | ok | Вход в «Между уроками» | `shots/offline-landing-only-375/11-ОФЛАЙН-parent-.png` |
| СНОВА ОНЛАЙН: студия | /studio/ | ok | Студия | `shots/offline-landing-only-375/12-СНОВА-ОНЛАЙН-студия.png` |

## 5. Скорость — 375 px

Первый экран / полностью, мс. «3G» — медленная сеть (задержка 562 мс, 1,44 Мбит/с) через прокси, замедляет и service worker.

| Переход | сеть | 3G | 3G повт. | 3G+SW | Запросов / КБ (3G) | Замечания |
|---|---|---|---|---|---|---|
| Главная: первое открытие | 685 / 1120 | 4805 / 7154 | 4366 / 5791 | 1387 / 2790 | 16 / 314 | тяжёлое /fonts/unbounded-latin.woff2 50KB |
| Главная → «Попробовать» | 499 / 504 | 3044 / 3049 | 3179 / 3179 | 2772 / 2772 | 10 / 41 |  |
| Главная → «Войти» | 558 / 700 | 4319 / 5721 | 4330 / 5729 | 2571 / 3924 | 14 / 11 |  |
| Главная → якорь «Тарифы» | — / -335 | — / -326 | — / -308 | — / -307 | 0 / 0 |  |
| Библиотека ЕГЭ: первое открытие | 794 / 958 | 6242 / 8086 | 4380 / 4381 | 4616 / 4616 | 12 / 476 | тяжёлое /packs/ege-rus.json 250KB · тяжёлое /fonts/unbounded-latin.woff2 50KB |
| Библиотека: главная → задание 4 | 15 / 16 | 15 / 15 | 17 / 18 | 17 / 17 | 0 / 0 |  |
| Библиотека: задание → теория | 11 / 11 | 10 / 10 | 12 / 12 | 12 / 12 | 0 / 0 |  |
| Библиотека: «Заниматься» → карточка | 2 / 2 | 2 / 2 | 1 / 1 | 1 / 1 | 0 / 0 |  |
| Студия (гость): открытие | 615 / 775 | 3237 / 5238 | 3047 / 4437 | 3300 / 4642 | 11 / 233 | тяжёлое /fonts/unbounded-latin.woff2 50KB |
| Студия: готовый пример по ссылке | 578 / 731 | 3215 / 5163 | 2917 / 2917 | 3147 / 3147 | 10 / 226 | тяжёлое /fonts/unbounded-latin.woff2 50KB |
| Кабинет (гость): открытие | 1140 / 1457 | 7677 / 9836 | 7296 / 8687 | 8764 / 11761 | 23 / 267 | повтор GET /app.css ×2 · повтор GET /lib.js ×2 · повтор GET /account.js ×2 · повтор GET /config.js ×2 · повтор GET /fonts/nunito-cyrillic.woff2 ×2 · повтор GET /fonts/nunito-latin.woff2 ×2 · тяжёлое /fonts/unbounded-latin.woff2 50KB · повтор GET /fonts/unbounded-cyrillic.woff2 ×2 · повтор GET /fonts/unbounded-latin.woff2 ×2 |
| Вход: открытие | 639 / 1108 | 4416 / 7578 | 4357 / 5808 | 4488 / 6154 | 14 / 246 | тяжёлое /fonts/unbounded-latin.woff2 50KB |
| /parent/ → кабинет родителя | 1239 / 1625 | 8945 / 11085 | 8506 / 9908 | 10509 / 11906 | 24 / 268 | повтор GET /app.css ×2 · повтор GET /lib.js ×2 · повтор GET /account.js ×2 · повтор GET /config.js ×2 · повтор GET /fonts/nunito-cyrillic.woff2 ×2 · повтор GET /fonts/nunito-latin.woff2 ×2 · тяжёлое /fonts/unbounded-latin.woff2 50KB · повтор GET /fonts/unbounded-cyrillic.woff2 ×2 · повтор GET /fonts/unbounded-latin.woff2 ×2 |
| Оферта | 237 / 584 | 2724 / 6394 | 2721 / 4075 | 2764 / 4123 | 7 / 166 | тяжёлое /fonts/unbounded-latin.woff2 50KB |

## 6. Попытки записи на сервер (заблокированы проверкой)

- POST /auth/tg/start ×4
- POST /auth/oauth/yandex ×4
- POST /ai ×2

Ожидаемы: POST /auth/tg/start и /auth/oauth/* (кнопки входа). Другие — повод посмотреть, кто и зачем пишет без входа.

## 7. Ошибки (уникальные)

- `console: Failed to load resource: the server responded with a status of # (Not Found)` — путь nav 1280: неизвестный код тренажёра; путь nav 375: неизвестный код тренажёра; guest 1280: загрузка https://econcards.kqrulev.workers.dev/?t=zzzz1234; guest 375: загрузка https://econcards.kqrulev.workers.dev/?t=zzzz1234
- `http#: GET /packs/zzzz#` — путь nav 1280: неизвестный код тренажёра; путь nav 375: неизвестный код тренажёра; guest 1280: загрузка https://econcards.kqrulev.workers.dev/?t=zzzz1234; guest 375: загрузка https://econcards.kqrulev.workers.dev/?t=zzzz1234
- `http#: GET /no-such-page-audit` — путь nav 1280: несуществующая страница; путь nav 375: несуществующая страница

