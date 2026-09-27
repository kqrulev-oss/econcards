// Общее для приложения ученика и студии репетитора: загрузка наборов,
// запросы к серверу, отрисовка и проверка карточек.

const CFG = Object.assign({ api: '' }, window.ZD_CONFIG);

export const store = {
  get(key, fallback) {
    try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; }
    catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* приватный режим */ }
  },
};

// Адрес сервера можно переопределить в настройках без пересборки
export const apiBase = () => (store.get('zd-api', '') || CFG.api || '').replace(/\/+$/, '');

export async function api(path, { method = 'GET', body, key, keepalive = false } = {}) {
  const base = apiBase();
  if (!base) throw new Error('Не задан адрес сервера');
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (key) headers['X-Key'] = key;
  // Вход в аккаунт (account.js): сессия едет с каждым запросом к своему серверу
  const token = store.get('zd-session', null)?.token;
  if (token) headers.Authorization = `Bearer ${token}`;
  let r;
  try {
    r = await fetch(base + path, { method, headers, keepalive, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw Object.assign(new Error('Нет связи с сервером'), { status: 0 });
  }
  const data = await r.json().catch(() => ({}));
  // 401 на запрос с сессией — сессия больше не действует (вышли на другом устройстве, истёк срок).
  // account.js забывает её и показывает «Сессия закончилась — войдите снова»
  if (r.status === 401 && token) window.dispatchEvent(new CustomEvent('zd-unauthorized', { detail: { token } }));
  if (!r.ok) throw Object.assign(new Error(data.message || `Ошибка сервера (${r.status})`), { status: r.status });
  return data;
}

export const ai = (task, payload) => api('/ai', { method: 'POST', body: { task, ...payload } });

// Встроенные наборы лежат в packs/, наборы репетиторов — на сервере
export async function loadPack(ref, root = './') {
  if (ref.startsWith('t:')) return api('/packs/' + encodeURIComponent(ref.slice(2)));
  // С сессией сервер отдаёт библиотеку целиком, если есть доступ (пробный, оплата)
  const token = store.get('zd-session', null)?.token;
  const r = await fetch(`${root}packs/${encodeURIComponent(ref)}.json`, token ? { headers: { Authorization: `Bearer ${token}` } } : {});
  if (!r.ok) throw new Error('Набор не найден');
  return r.json();
}

export async function loadLibrary(root = './') {
  const r = await fetch(root + 'packs/index.json');
  return r.ok ? r.json() : [];
}

// ---------- мелочи ----------

// Конспект урока из набора: набор репетитора приходит с сервера как есть, поэтому
// оставляем только простую разметку (белый список тегов, из атрибутов — class).
// Скрипты, обработчики событий, ссылки и картинки вырезаются — иначе чужой набор
// мог бы украсть вход у ученика.
const SAFE_TAGS = new Set(['P', 'B', 'I', 'U', 'EM', 'STRONG', 'BR', 'DIV', 'SPAN', 'H3', 'H4', 'UL', 'OL', 'LI',
  'TABLE', 'THEAD', 'TBODY', 'TR', 'TD', 'TH', 'SUP', 'SUB', 'SMALL', 'BLOCKQUOTE', 'CODE', 'PRE', 'HR']);
export function safeHtml(html) {
  const doc = new DOMParser().parseFromString(`<body>${String(html ?? '')}</body>`, 'text/html');
  const clean = node => {
    for (const ch of [...node.childNodes]) {
      if (ch.nodeType === 3) continue;
      if (ch.nodeType !== 1 || !SAFE_TAGS.has(ch.tagName)) {
        // Незнакомый тег: текст внутри оставляем (кроме script/style и т. п.), сам тег — нет
        if (ch.nodeType === 1 && !/^(SCRIPT|STYLE|IFRAME|OBJECT|EMBED|TEMPLATE|NOSCRIPT|SVG|MATH|TEXTAREA|SELECT)$/.test(ch.tagName)) {
          clean(ch); ch.replaceWith(...ch.childNodes);
        } else ch.remove();
        continue;
      }
      for (const a of [...ch.attributes]) if (a.name !== 'class') ch.removeAttribute(a.name);
      clean(ch);
    }
  };
  clean(doc.body);
  return doc.body.innerHTML;
}

export const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
// Формулы в данных помечены ⟦ ⟧: формула на всю строку — отдельным блоком,
// внутри текста — выделенным фрагментом; ^2, ^{n}, ^(−1) — степени
const supify = t => t
  .replace(/\^\{([^}]*)\}/g, '<sup>$1</sup>')
  .replace(/\^\(([^)]*)\)/g, '<sup>$1</sup>')
  .replace(/\^([0-9A-Za-zА-Яа-яα-ωΑ-Ω]|[+\-−][0-9]+)/g, '<sup>$1</sup>');
export const text = s => esc(s).split('\n').map(line => {
  const solo = line.trim().match(/^⟦(.+)⟧$/);
  if (solo) return `<span class="fblock">${supify(solo[1])}</span>`;
  return line.replace(/⟦(.+?)⟧/g, (m, g) => `<span class="f">${supify(g)}</span>`);
}).join('<br>');
// Ответ ИИ: если модель всё же прислала Markdown или LaTeX — показываем по-человечески
const aiText = s => text(String(s || '')
  .replace(/\$([^$\n]+)\$/g, (m, f) => f.replace(/_\{?([^}\s]+)\}?/g, '$1').replace(/\\cdot/g, '·').replace(/\\/g, ''))
  .replace(/^#+\s*/gm, '')
  .replace(/^\s*[*-]\s+/gm, '• '))
  .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
export const day = (d = new Date()) => Math.floor((d - d.getTimezoneOffset() * 60000) / 86400000);
// Срок задания 'YYYY-MM-DD' → номер дня (тот же счёт, что day()) и подпись «сб, 3 октября»
export const dueDay = due => { const [y, m, d] = String(due).split('-').map(Number); return Date.UTC(y, m - 1, d) / 864e5; };
const WD = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб'];
const MON = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
export const dueText = due => { const t = new Date(dueDay(due) * 864e5); return `${WD[t.getUTCDay()]}, ${t.getUTCDate()} ${MON[t.getUTCMonth()]}`; };
// Время эфира (ISO) по часам ученика: «сб, 3 октября, 18:00»
export const whenText = iso => {
  const t = new Date(iso);
  return `${WD[t.getDay()]}, ${t.getDate()} ${MON[t.getMonth()]}, ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`;
};

// ---------- курс ----------

// Видео урока: iframe только трёх сервисов, и src собирается из разобранного id — сам адрес
// в страницу не попадает. Любая другая https-ссылка — кнопкой, всё прочее не показываем
export function videoEmbed(url) {
  let u;
  try { u = new URL(String(url ?? '').trim()); } catch { return ''; }
  if (u.protocol !== 'https:' || u.username || u.password || u.port) return '';
  const host = u.hostname.replace(/^(www|m)\./, ''), path = u.pathname;
  let src = null, m;
  if (host === 'kinescope.io' && (m = path.match(/^\/(?:embed\/)?([A-Za-z0-9]{6,40})\/?$/))) src = `https://kinescope.io/embed/${m[1]}`;
  else if (host === 'rutube.ru' && (m = path.match(/^\/(?:video|play\/embed)\/([0-9a-f]{32})\/?$/))) src = `https://rutube.ru/play/embed/${m[1]}`;
  else if (host === 'vk.com' || host === 'vkvideo.ru') {
    const q = u.searchParams;
    if ((m = path.match(/^\/video(-?\d{1,20})_(\d{1,20})\/?$/))) src = `https://vk.com/video_ext.php?oid=${m[1]}&id=${m[2]}`;
    else if (path === '/video_ext.php' && /^-?\d{1,20}$/.test(q.get('oid')) && /^\d{1,20}$/.test(q.get('id'))) {
      src = `https://vk.com/video_ext.php?oid=${q.get('oid')}&id=${q.get('id')}`;
      if (/^[0-9a-f]{1,40}$/i.test(q.get('hash') || '')) src += `&hash=${q.get('hash')}`;
    }
  }
  if (src) return `<div class="video-frame"><iframe src="${src}" title="Видео урока" allow="autoplay; fullscreen; picture-in-picture; encrypted-media" allowfullscreen loading="lazy" referrerpolicy="origin"></iframe></div>`;
  return `<a class="btn" href="${esc(u.href)}" target="_blank" rel="noopener">Открыть видео</a>`;
}

// ДЗ курса для отчётов: n — уроки с ДЗ, у которых срок прошёл или ДЗ уже сделано; done — сделано;
// onTime — сделано не позже срока. les — prog.les ученика ({ id: { d, ok, at } }, at — номер дня)
export function courseStats(les, course, today) {
  const r = { n: 0, done: 0, onTime: 0 };
  for (const l of course?.lessons || []) {
    if (!l.hw?.due) continue;
    const at = les?.[l.id]?.at, end = dueDay(l.hw.due);
    if (!at && today <= end) continue;
    r.n++;
    if (at) { r.done++; if (at <= end) r.onTime++; }
  }
  return r;
}

// ДЗ урока с двух устройств: у урока берём, где решено больше (вместе с его точностью),
// а день выполнения — самый ранний
export function mergeLes(a = {}, b = {}) {
  const out = {};
  for (const id of new Set([...Object.keys(a), ...Object.keys(b)])) {
    const x = a[id], y = b[id];
    const best = !x ? y : !y ? x : (y.d > x.d ? y : x);
    const at = [x?.at, y?.at].filter(Boolean);
    out[id] = { d: best.d || 0, ok: best.ok || 0, ...(at.length && { at: Math.min(...at) }) };
  }
  return out;
}

export const uid = (n = 8) => Array.from(crypto.getRandomValues(new Uint8Array(n)), b => 'abcdefghijkmnpqrstuvwxyz23456789'[b % 32]).join('');
export const plural = (n, one, few, many) => {
  const m10 = n % 10, m100 = n % 100;
  const w = m10 === 1 && m100 !== 11 ? one : m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20) ? few : many;
  return `${n} ${w}`;
};
export function el(html) {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}
export function toast(msg) {
  document.querySelectorAll('.toast').forEach(x => x.remove());
  const t = el(`<div class="toast">${esc(msg)}</div>`);
  document.body.append(t);
  setTimeout(() => t.classList.add('on'));
  setTimeout(() => { t.classList.remove('on'); setTimeout(() => t.remove(), 300); }, 2600);
}

// ---------- модальные окна ----------
// Открытое окно — своя запись в истории: «Назад» телефона закрывает окно, а не уводит
// со страницы. Ещё закрывают крестик, клик мимо окна, Esc и смена адреса (окно не висит
// над другим экраном). Окна могут открываться друг над другом — закрывается верхнее.
// history.state открытого окна — { zdModal: id }: обработчикам popstate его можно пропускать.
// Окно, открытое без нажатия (при загрузке страницы), записи не получает: Chrome такие записи
// на «Назад» пропускает — такое окно закрывают крестик, Esc и смена адреса
const modals = []; // открытые окна снизу вверх: { id, href, shut }
let modalSeq = 0;
let pendingBack = null; // окно закрыто кодом, его запись истории ещё не снята
let ownBacks = 0; // наши history.back() при закрытии окна: такой popstate — не «Назад» человека

// «Назад» (или вперёд) по истории: закрываем окна, открытые после текущей записи
window.addEventListener('popstate', () => {
  if (ownBacks > 0) { ownBacks--; return; }
  const k = modals.findIndex(x => x.id === history.state?.zdModal);
  for (const x of modals.slice(k + 1).reverse()) x.shut('history');
});
// Переход на другой адрес (#-ссылка, код страницы) — окна прежнего экрана закрываются.
// Окно, открытое уже на новом адресе, остаётся
window.addEventListener('hashchange', () => {
  for (const x of [...modals].reverse()) if (x.href !== location.href) x.shut('history');
});
document.addEventListener('keydown', e => {
  if (e.key !== 'Escape' || e.isComposing || e.defaultPrevented || !modals.length) return;
  e.preventDefault();
  modals.at(-1).shut('user');
});

/* Модальное окно поверх страницы. Возвращает { box, close }; close() возвращает Promise,
   который выполнится, когда запись окна снята с истории, — после него можно менять адрес.
   onClose — вызывается при любом закрытии окна. */
export function modal(html, { onClose } = {}) {
  const m = el(`<div class="modal" role="dialog" aria-modal="true"><div class="modal-box" tabindex="-1"><button class="modal-x" aria-label="Закрыть">✕</button>${html}</div></div>`);
  const id = `m${++modalSeq}-${Date.now().toString(36)}`;
  const from = document.activeElement;
  let open = true;
  // how: 'history' — закрыто переходом по истории или адресу (запись уже не текущая);
  // 'user' — крестик, клик мимо, Esc: запись снимаем сразу; 'code' — close() из кода: чуть позже
  const shut = (how = 'code') => {
    if (!open) return Promise.resolve();
    open = false;
    m.remove();
    const i = modals.findIndex(x => x.id === id);
    if (i >= 0) modals.splice(i, 1);
    if (from?.isConnected && !document.querySelector('.modal')) from.focus?.({ preventScroll: true });
    try { onClose?.(); } catch (err) { console.error(err); }
    if (how === 'history' || history.state?.zdModal !== id) return Promise.resolve();
    const back = done => {
      if (history.state?.zdModal !== id) return done();
      let popped = false;
      const fin = () => { popped = true; removeEventListener('popstate', fin); clearTimeout(guard); done(); };
      // popstate так и не пришёл — не считаем следующий «Назад» человека своим
      const guard = setTimeout(() => { if (!popped) ownBacks = Math.max(0, ownBacks - 1); fin(); }, 600);
      addEventListener('popstate', fin);
      ownBacks++;
      history.back();
    };
    if (how === 'user') return new Promise(back);
    // Из кода — не сразу: если следом меняют адрес (close(); location.hash = …), «назад» отменил бы
    // этот переход, а новая запись уже не наша — тогда её не трогаем
    return new Promise(done => {
      const t = setTimeout(() => { pendingBack = null; back(done); });
      pendingBack = { id, t, done };
    });
  };
  const close = () => shut();
  m.querySelector('.modal-x').onclick = () => { shut('user'); };
  // Только клик по фону закрывает окно; return false здесь отменил бы клики по ссылкам внутри
  m.onclick = e => { if (e.target === m) shut('user'); };
  // Окно сменяет только что закрытое (вход → оплата): занимаем его запись истории вместо новой.
  // Новую запись — только после нажатия человека (иначе Chrome пропустит её на «Назад»)
  if (pendingBack && history.state?.zdModal === pendingBack.id) {
    clearTimeout(pendingBack.t);
    pendingBack.done();
    pendingBack = null;
    history.replaceState({ zdModal: id }, '');
  } else if (navigator.userActivation?.isActive ?? true) {
    history.pushState({ zdModal: id }, '');
  }
  modals.push({ id, href: location.href, shut });
  document.body.append(m);
  const box = m.querySelector('.modal-box');
  box.focus({ preventScroll: true });
  return { box, close };
}

// Сравнение числовых ответов: «0,35», «0.35» и «.35» — одно и то же
export function sameNumber(a, b) {
  const norm = x => String(x).trim().replace(/\s+/g, '').replace(',', '.').replace(/^(-?)\./, '$10.');
  const x = norm(a), y = norm(b);
  if (x === y) return true;
  const nx = Number(x), ny = Number(y);
  return !Number.isNaN(nx) && !Number.isNaN(ny) && Math.abs(nx - ny) < 1e-9;
}

export const KIND_NAMES = {
  one: 'Один ответ', many: 'Несколько ответов', match: 'Соответствие',
  flip: 'Вопрос — ответ', open: 'Развёрнутое решение', stress: 'Ударение', num: 'Числовой ответ',
};

// ---------- карточка ----------

const VOWELS = 'аеёиоуыэюя';

/**
 * Рисует карточку в `root` и вызывает onDone(score) после ответа:
 * 1 — верно, 0.5 — частично, 0 — неверно. `root` получает готовую разметку.
 */
export function renderCard(card, root, onDone, { imgRoot = './', aiEnabled = !!apiBase() } = {}) {
  let done = false;
  const finish = score => {
    if (done) return;
    done = true;
    root.classList.add('answered');
    if (card.e && !['flip', 'open'].includes(card.k)) root.querySelector('.explain').innerHTML = `<b>Разбор.</b> ${text(card.e)}`;
    onDone(score);
  };

  const imgs = (card.img || []).map(src => `<img src="${esc(imgRoot + src)}" alt="" loading="lazy">`).join('')
    // График из набора — картинкой через data:, чтобы SVG не мог выполнить код
    + (card.svg ? `<img class="graph" src="data:image/svg+xml;charset=utf-8,${encodeURIComponent(card.svg)}" alt="График к заданию">` : '');
  root.innerHTML = `
    ${card.src ? `<div class="card-src">${esc(card.src)}</div>` : ''}
    <div class="card-q">${text(card.q)}</div>
    ${imgs ? `<div class="card-img">${imgs}</div>` : ''}
    <div class="card-body"></div>
    <div class="explain"></div>`;
  const body = root.querySelector('.card-body');

  if (card.k === 'one' || card.k === 'many') {
    const multi = card.k === 'many';
    const right = new Set(multi ? card.a : [card.a]);
    body.innerHTML = `<div class="opts">${card.o.map(o =>
      `<button class="opt" data-id="${esc(o.id)}"><span class="opt-id">${esc(o.id)}</span><span>${text(o.t)}</span></button>`).join('')}</div>
      ${multi ? '<button class="btn primary check" disabled>Проверить</button>' : ''}`;
    const opts = [...body.querySelectorAll('.opt')];
    const reveal = picked => {
      opts.forEach(b => {
        const id = b.dataset.id;
        b.disabled = true;
        if (right.has(id)) b.classList.add(picked.has(id) ? 'ok' : 'missed');
        else if (picked.has(id)) b.classList.add('bad');
      });
      const ok = picked.size === right.size && [...picked].every(id => right.has(id));
      finish(ok ? 1 : 0);
    };
    if (!multi) opts.forEach(b => b.onclick = () => reveal(new Set([b.dataset.id])));
    else {
      const btn = body.querySelector('.check');
      opts.forEach(b => b.onclick = () => {
        b.classList.toggle('picked');
        btn.disabled = !body.querySelector('.picked');
      });
      btn.onclick = () => { btn.remove(); reveal(new Set(opts.filter(b => b.classList.contains('picked')).map(b => b.dataset.id))); };
    }
  } else if (card.k === 'match') {
    const { left, right } = card.o;
    body.innerHTML = `
      <div class="match-right">${right.map(r => `<div><b>${esc(r.id)}</b> ${text(r.t)}</div>`).join('')}</div>
      <div class="match-left">${left.map(l => `
        <label class="match-row"><span><b>${esc(l.id)}</b> ${text(l.t)}</span>
          <select data-id="${esc(l.id)}"><option value="">—</option>${right.map(r => `<option>${esc(r.id)}</option>`).join('')}</select>
        </label>`).join('')}</div>
      <button class="btn primary check">Проверить</button>`;
    body.querySelector('.check').onclick = e => {
      e.target.remove();
      let good = 0;
      body.querySelectorAll('select').forEach(s => {
        const want = card.a[s.dataset.id];
        s.disabled = true;
        const ok = s.value === want;
        good += ok;
        s.closest('.match-row').classList.add(ok ? 'ok' : 'bad');
        if (!ok) s.insertAdjacentHTML('afterend', `<span class="want">→ ${esc(want)}</span>`);
      });
      finish(good === left.length ? 1 : good >= left.length / 2 ? 0.5 : 0);
    };
  } else if (card.k === 'stress') {
    const word = card.a;
    const target = [...word].findIndex(c => c !== c.toLowerCase());
    body.innerHTML = `<div class="stress">${[...word.toLowerCase()].map((c, i) =>
      VOWELS.includes(c) ? `<button class="vowel" data-i="${i}">${c}</button>` : `<span>${c}</span>`).join('')}</div>
      <p class="hint">Нажми на ударную гласную</p>`;
    body.querySelectorAll('.vowel').forEach(b => b.onclick = () => {
      body.querySelectorAll('.vowel').forEach(v => {
        v.disabled = true;
        if (+v.dataset.i === target) v.classList.add('ok');
      });
      if (+b.dataset.i !== target) b.classList.add('bad');
      body.querySelector('.hint').innerHTML = `Правильно: <b>${esc(word)}</b>`;
      finish(+b.dataset.i === target ? 1 : 0);
    });
  } else if (card.k === 'num') {
    // Краткий ответ ЕГЭ: число вводится с клавиатуры, запятая и точка равноправны
    body.innerHTML = `
      <div class="num-row"><input class="num-input" inputmode="decimal" autocomplete="off" placeholder="Ответ">
        <button class="btn primary check">Проверить</button></div>
      <p class="hint">Целое число или десятичная дробь, как в бланке ЕГЭ</p>`;
    const input = body.querySelector('.num-input');
    const check = () => {
      const got = input.value.trim();
      if (!got) return toast('Введи ответ');
      const ok = sameNumber(got, card.a);
      input.disabled = true;
      input.classList.add(ok ? 'ok' : 'bad');
      body.querySelector('.check').remove();
      body.querySelector('.hint').innerHTML = ok ? 'Верно!' : `Правильный ответ: <b>${esc(card.a)}</b>`;
      finish(ok ? 1 : 0);
    };
    body.querySelector('.check').onclick = check;
    // preventDefault: иначе тот же Enter нажмёт «Дальше», и ученик не увидит результат
    input.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); check(); } };
    setTimeout(() => input.focus({ preventScroll: true }), 50);
  } else {
    // flip и open: ответ показывается, ученик оценивает себя сам (или с ИИ)
    const open = card.k === 'open';
    body.innerHTML = `
      ${open ? '<textarea class="answer" rows="5" placeholder="Запиши решение и ответ — так легче сверить"></textarea>' : ''}
      <div class="row">
        ${open && aiEnabled ? '<button class="btn ghost ai-hint">Подсказка</button><button class="btn ghost ai-check">Проверить с ИИ</button>' : ''}
        <button class="btn primary show">Показать ${open ? 'решение' : 'ответ'}</button>
      </div>
      <div class="ai-out"></div>
      <div class="reveal" hidden>
        <div class="solution">${text(card.a)}${card.e && !open ? `<p class="muted">${text(card.e)}</p>` : ''}</div>
        <p class="hint">Оцени себя честно — от этого зависит, когда карточка вернётся</p>
        <div class="row grade">
          <button class="btn bad" data-s="0">${open ? 'Не решил' : 'Не знал'}</button>
          ${open ? '<button class="btn mid" data-s="0.5">Частично</button>' : ''}
          <button class="btn good" data-s="1">${open ? 'Решил' : 'Знал'}</button>
        </div>
      </div>`;
    const reveal = body.querySelector('.reveal');
    body.querySelector('.show').onclick = e => { e.target.remove(); reveal.hidden = false; };
    body.querySelectorAll('.grade .btn').forEach(b => b.onclick = () => {
      body.querySelectorAll('.grade .btn').forEach(x => x.disabled = true);
      b.classList.add('chosen');
      finish(+b.dataset.s);
    });
    const out = body.querySelector('.ai-out');
    let level = 0;
    const ask = async (task, extra, btn) => {
      btn.disabled = true;
      out.innerHTML = '<p class="muted">Думаю…</p>';
      try {
        const r = await ai(task, { problem: card.q, reference: card.a, ...extra });
        out.innerHTML = `<div class="ai-box">${aiText(r.text)}</div>`;
      } catch (err) {
        out.innerHTML = `<p class="muted">${esc(err.message)}</p>`;
      }
      btn.disabled = false;
    };
    body.querySelector('.ai-hint')?.addEventListener('click', e => {
      level = Math.min(3, level + 1);
      ask('hint', { level }, e.target);
    });
    body.querySelector('.ai-check')?.addEventListener('click', e => {
      const answer = body.querySelector('.answer').value.trim();
      if (!answer) return toast('Сначала запиши решение');
      ask('check', { answer }, e.target);
    });
  }
}
