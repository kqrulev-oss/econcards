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

export async function api(path, { method = 'GET', body, key } = {}) {
  const base = apiBase();
  if (!base) throw new Error('Не задан адрес сервера');
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (key) headers['X-Key'] = key;
  let r;
  try {
    r = await fetch(base + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new Error('Нет связи с сервером');
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.message || `Ошибка сервера (${r.status})`);
  return data;
}

export const ai = (task, payload) => api('/ai', { method: 'POST', body: { task, ...payload } });

// Встроенные наборы лежат в packs/, наборы репетиторов — на сервере
export async function loadPack(ref, root = './') {
  if (ref.startsWith('t:')) return api('/packs/' + encodeURIComponent(ref.slice(2)));
  const r = await fetch(`${root}packs/${encodeURIComponent(ref)}.json`);
  if (!r.ok) throw new Error('Набор не найден');
  return r.json();
}

export async function loadLibrary(root = './') {
  const r = await fetch(root + 'packs/index.json');
  return r.ok ? r.json() : [];
}

// ---------- мелочи ----------

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
export const day = (d = new Date()) => Math.floor((d - d.getTimezoneOffset() * 60000) / 86400000);
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

export const KIND_NAMES = {
  one: 'Один ответ', many: 'Несколько ответов', match: 'Соответствие',
  flip: 'Вопрос — ответ', open: 'Развёрнутое решение', stress: 'Ударение',
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

  const imgs = (card.img || []).map(src => `<img src="${esc(imgRoot + src)}" alt="" loading="lazy">`).join('');
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
        out.innerHTML = `<div class="ai-box">${text(r.text)}</div>`;
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
