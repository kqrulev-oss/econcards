/* Между уроками: офлайн после первого открытия.
   Сеть → кэш: при наличии сети всегда свежая версия, без сети — из кэша.
   Наборы и картинки кэшируются по мере открытия. Запросы к серверу ИИ
   (другой домен) не трогаем. При смене состава файлов поднимай версию. */
const CACHE = 'zadachnik-v17';
const ASSETS = [
  './', './index.html', './app.css', './app.js', './lib.js', './landing.js', './account.js', './config.js', './manifest.webmanifest',
  './packs/index.json', './img/hero-student-768.webp',
  './fonts/nunito-cyrillic.woff2', './fonts/nunito-latin.woff2', './fonts/unbounded-cyrillic.woff2', './fonts/unbounded-latin.woff2', './icons/icon-192.png', './icons/icon-512.png', './icons/apple-touch-icon.png',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  e.respondWith(
    fetch(e.request).then(resp => {
      if (resp.ok) {
        const copy = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
      }
      return resp;
    }).catch(() => caches.match(e.request, { ignoreSearch: true })
      .then(r => r || (e.request.mode === 'navigate' ? caches.match('./index.html') : undefined)))
  );
});
