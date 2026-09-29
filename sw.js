/* Между уроками: service worker — быстрые переходы между страницами и офлайн.
   - Статика (js, css, шрифты, иконки, картинки) — сразу из кэша этой версии (CACHE):
     не ждём сеть на каждом переходе. packs/index.json, packs/*.free.json,
     packs/sample-*.json — из кэша сразу, а в фоне обновляются.
   - Страницы — из сети, но ждём не дольше 2,5 с, если есть сохранённая копия этой же
     страницы; без сети — копия, а если её нет — offline.html (не чужая страница).
   - Наборы библиотеки packs/<id>.json без входа — из сети, без сети — сохранённая копия:
     ученик занимается офлайн (наборы репетиторов приложение хранит само, в localStorage).
   - Ответы API (/me, /auth, /pay, /packs/<код>, /tg, /gh, /ai) и любые запросы
     с Authorization в кэш не попадают никогда.
   Изменили любой файл сайта — подними версию CACHE: новая версия заново скачает
   файлы из списка ниже, а старый кэш удалится. */
const CACHE = 'zadachnik-v42';
const WAIT = 2500; // мс: столько ждём страницу из сети, если есть сохранённая копия
const PAGES = ['./', './studio/', './cabinet/', './login.html', './parent/', './offline.html'];
const FILES = [
  './app.css', './config.js', './app.js', './lib.js', './landing.js', './account.js', './login.js',
  './studio/studio.js', './cabinet/cabinet.js', './parent/view.js',
  './manifest.webmanifest', './packs/index.json', './img/hero-student-768.webp',
  './fonts/nunito-cyrillic.woff2', './fonts/nunito-latin.woff2', './fonts/unbounded-cyrillic.woff2', './fonts/unbounded-latin.woff2',
  './icons/icon-192.png', './icons/favicon-48.png', './icons/icon-512.png', './icons/apple-touch-icon.png',
];

// Сервер (worker/worker.js): не кэшируем. packs/<id>.json — файлы библиотеки, это не API
const API = /^\/(ai|me|auth|pay|tg|gh)(\/|$)|^\/packs\/[^/]+(\/|$)/;
const isApi = path => API.test(path) && !/^\/packs\/[\w.-]+\.json$/.test(path);
const STATIC = /\.(js|mjs|css|woff2?|png|jpe?g|webp|gif|svg|ico|webmanifest)$/;
const REFRESH = /^packs\/(index|sample-[\w-]+|[\w-]+\.free)\.json$/; // из кэша + обновление в фоне
const LIBRARY = /^packs\/[\w-]+\.json$/;                            // сеть, без сети — копия

// Ключ страницы: без ?параметров, /index.html = /, /login.html = /login (Cloudflare
// перенаправляет x.html → x): у одной страницы одна копия, какой бы адрес ни открыли
const pageKey = url => {
  const u = new URL(url, self.location);
  return u.origin + u.pathname.replace(/\/index(\.html)?$/, '/').replace(/\.html$/, '');
};
const within = url => url.startsWith(self.registration.scope);

async function put(key, resp) {
  // Ответ после редиректа нельзя отдать на переход по странице — пересобираем без пометки
  const clean = resp.redirected
    ? new Response(await resp.blob(), { status: resp.status, statusText: resp.statusText, headers: resp.headers })
    : resp;
  await (await caches.open(CACHE)).put(key, clean);
}
const cachable = r => r.ok && r.type === 'basic';

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    await Promise.all([...PAGES, ...FILES].map(async path => {
      const url = new URL(path, self.location).href;
      // no-cache: сверяемся с сервером, а не берём файл из HTTP-кэша браузера
      const r = await fetch(new Request(url, { cache: 'no-cache' }));
      if (!r.ok) throw new Error(`${path}: ${r.status}`);
      await put(PAGES.includes(path) ? pageKey(url) : url, r);
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    // Старые версии кэша (и ответы API, которые кэшировали версии до v32) — удаляем
    for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
    // Переход по странице начинает загрузку, пока service worker ещё просыпается
    await self.registration.navigationPreload?.enable().catch(() => {});
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || isApi(url.pathname)) return;
  if (req.mode === 'navigate') return e.respondWith(page(e));
  // Вход в аккаунт: ответ свой у каждого человека — только сеть, мимо кэша
  if (req.headers.has('Authorization') || req.headers.has('Range') || !within(req.url)) return;
  const rel = req.url.slice(self.registration.scope.length).split(/[?#]/)[0];
  if (REFRESH.test(rel)) return e.respondWith(fromCache(e, true));
  if (LIBRARY.test(rel)) return e.respondWith(fresh(e, req.url, () => match(req)));
  if (STATIC.test(url.pathname)) return e.respondWith(fromCache(e, false));
});

// Кэш недоступен (переполнен, почищен) — считаем, что копии нет: страница пойдёт в сеть
const match = async req => { try { return await (await caches.open(CACHE)).match(req); } catch { return undefined; } };

// Статика: из кэша сразу; нет в кэше — из сети и в кэш. refresh — ещё и обновить в фоне
async function fromCache(e, refresh) {
  const hit = await match(e.request);
  if (hit && !refresh) return hit;
  const net = fetch(e.request).then(r => {
    if (cachable(r)) e.waitUntil(put(e.request, r.clone()).catch(() => {}));
    return r;
  });
  if (!hit) return net;
  e.waitUntil(net.catch(() => {}));
  return hit;
}

// Сеть, но не дольше WAIT, если есть сохранённая копия (saved); без сети — копия или fallback
function fresh(e, key, saved, { navigate = false, fallback = () => Response.error() } = {}) {
  const net = (async () => {
    const r = (navigate && await e.preloadResponse) || await fetch(e.request);
    const html = !navigate || /text\/html/.test(r.headers.get('Content-Type') || '');
    if (cachable(r) && html) e.waitUntil(put(key, r.clone()).catch(() => {}));
    return r;
  })();
  e.waitUntil(net.catch(() => {}));
  return new Promise(resolve => {
    let done = false;
    const give = r => { if (r && !done) { done = true; resolve(r); } };
    net.then(async r => give((r.status >= 500 && await saved()) || r),
      async () => give((await saved()) || await fallback()));
    setTimeout(async () => give(await saved()), WAIT);
  });
}

// Переход по странице: сеть → копия этой же страницы → offline.html
function page(e) {
  const key = pageKey(e.request.url);
  return fresh(e, key, () => savedPage(e.request.url), { navigate: true, fallback: offline });
}

async function savedPage(url) {
  const key = pageKey(url);
  const hit = await match(key);
  if (hit) return hit;
  // /studio без слэша: копия лежит у /studio/ — туда и ведём (пути внутри страницы — от папки)
  if (!key.endsWith('/') && await match(key + '/')) return Response.redirect(key + '/' + new URL(url).search, 302);
  return null;
}

// «Нет связи»: страница открывается по чужому адресу (например, /offer.html) — пути в ней от корня сайта
async function offline() {
  const r = await match(pageKey(new URL('./offline.html', self.location).href));
  if (!r) return Response.error();
  const html = (await r.text()).replace('<head>', `<head><base href="${self.registration.scope}">`);
  return new Response(html, { headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' } });
}
