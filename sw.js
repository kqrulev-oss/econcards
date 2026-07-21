/* EconCards service worker: полный оффлайн после первого открытия.
   При обновлении базы меняй номер версии — клиенты подтянут новую сами. */
const CACHE = 'econcards-v27';
const ASSETS = [
  './', './index.html', './manifest.webmanifest',
  './icons/icon-192.png', './icons/icon-512.png', './icons/apple-touch-icon.png'
];
/* Картинки к заданиям кэшируются по мере просмотра: класть 65 файлов
   в обязательный список установки — значит замедлить первый запуск. */

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE && k !== 'econcards-state').map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

/* сеть → кэш: свежая версия при наличии сети, оффлайн — из кэша */
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).then(resp => {
      const copy = resp.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
      return resp;
    }).catch(() => caches.match(e.request, { ignoreSearch: true })
      .then(r => r || caches.match('./index.html')))
  );
});

/* ============================================================
   ПУШ-УВЕДОМЛЕНИЯ
   Сервер шлёт пустой «пинг» (без payload) — текст выбирается здесь,
   на устройстве. Так не нужно шифровать полезную нагрузку на сервере.
   ============================================================ */

const NUDGES = [
  ['5 минут — и день засчитан', 'Одна карточка по эластичности займёт меньше, чем очередь в столовой.'],
  ['Твой streak ждёт', 'Пропуск обнулит серию. Три карточки — и он в безопасности.'],
  ['Монополия не выучит себя', 'Открой ленту и пролистай пару задач с разбором.'],
  ['Разминка перед сном', 'Повторённое вечером держится в памяти лучше. Проверено интервальным повторением.'],
  ['Задача дня', 'ВсОШ, МОШ, РАНХиГС — что попадётся, то и решишь.'],
  ['Ты остановился на середине темы', 'Доведи её до конца — останется меньше белых пятен на олимпиаде.'],
  ['Спринт на 5 минут', 'Таймер, десяток вопросов, никакого учебника.'],
  ['Пока едешь — успеешь', 'Приложение работает офлайн, даже в метро.']
];

/* Приложение кладёт сюда свежий прогресс, чтобы уведомление было персональным */
async function readState() {
  try {
    const c = await caches.open('econcards-state');
    const r = await c.match('state');
    return r ? await r.json() : null;
  } catch { return null; }
}

function pickNudge(state) {
  if (state) {
    const left = (state.goalToday || 0) - (state.doneToday || 0);
    if (left > 0 && (state.doneToday || 0) > 0)
      return ['Осталось ' + left + ' до цели дня', 'Ты уже начал — доводить проще, чем начинать.'];
    if ((state.streakDays || 0) >= 3 && (state.doneToday || 0) === 0)
      return [state.streakDays + ' дней подряд — не рви серию', 'Хватит трёх карточек, чтобы день засчитался.'];
  }
  return NUDGES[Math.floor(Math.random() * NUDGES.length)];
}

async function showNudge() {
  const state = await readState();
  const [title, body] = pickNudge(state);
  await self.registration.showNotification(title, {
    body,
    icon: './icons/icon-192.png',
    badge: './icons/icon-192.png',
    tag: 'econcards-nudge',
    renotify: true,
    data: { url: './index.html' }
  });
}

/* Серверный пуш (если появится push-сервер с VAPID). */
self.addEventListener('push', event => { event.waitUntil(showNudge()); });

/* Локальные фоновые напоминания без сервера — там, где браузер их поддерживает. */
self.addEventListener('periodicsync', event => {
  if (event.tag === 'econcards-nudge') event.waitUntil(showNudge());
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const c of all) {
      if (c.url.includes('index.html') || c.url.endsWith('/')) return c.focus();
    }
    return self.clients.openWindow(event.notification.data?.url || './index.html');
  })());
});
