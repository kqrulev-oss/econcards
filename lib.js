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
  return withTexts(await r.json());
}

// Общий текст группы заданий (банк ФИПИ) лежит в наборе один раз, а в карточку попадает
// при загрузке — дальше карточки самодостаточны и в приложении, и в студии
function withTexts(pack) {
  const texts = pack.texts || {};
  for (const c of pack.cards) {
    const t = texts[c.tx];
    if (!t) continue;
    c.h = t.h + (c.h || '');
    c.q += t.q;
    delete c.tx;
  }
  delete pack.texts;
  return pack;
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
// Ответ ИИ: если модель всё же прислала Markdown или LaTeX — показываем по-человечески
const aiText = s => text(String(s || '')
  .replace(/\$([^$\n]+)\$/g, (m, f) => f.replace(/_\{?([^}\s]+)\}?/g, '$1').replace(/\\cdot/g, '·').replace(/\\/g, ''))
  .replace(/^#+\s*/gm, '')
  .replace(/^\s*[*-]\s+/gm, '• '))
  .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
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

// Сравнение числовых ответов: «0,35», «0.35» и «.35» — одно и то же
export function sameNumber(a, b) {
  const norm = x => String(x).trim().replace(/\s+/g, '').replace(',', '.').replace(/^(-?)\./, '$10.');
  const x = norm(a), y = norm(b);
  if (x === y) return true;
  const nx = Number(x), ny = Number(y);
  return !Number.isNaN(nx) && !Number.isNaN(ny) && Math.abs(nx - ny) < 1e-9;
}

// Краткий ответ словом или цифрами: регистр, ё/е, пробелы и запятые не важны;
// any — порядок цифр не важен (так проверяет ФИПИ для «запишите номера…»)
export function sameShort(got, want, any = false) {
  const norm = x => String(x).toLowerCase().replace(/ё/g, 'е').replace(/[\s.,;]+/g, '');
  const key = x => any ? [...norm(x)].sort().join('') : norm(x);
  return [].concat(want).some(w => key(w) === key(got));
}

export const KIND_NAMES = {
  one: 'Один ответ', many: 'Несколько ответов', match: 'Соответствие',
  flip: 'Вопрос — ответ', open: 'Развёрнутое решение', stress: 'Ударение', num: 'Числовой ответ',
  short: 'Краткий ответ',
};

// ---------- условие с разметкой (банк ФИПИ) ----------
// Поле h: таблицы, картинки и формулы MathML (браузер рисует их сам). Разметка
// может прийти и в наборе репетитора, поэтому пропускаем только безопасные теги
// и атрибуты и вставляем готовые узлы, а не строку HTML.
const RICH_TAGS = new Set(('p div br b i u sub sup table tbody thead tr td th ul ol li img span details summary '
  + 'math mrow mi mn mo mtext mspace ms mfrac msqrt mroot msup msub msubsup mover munder munderover '
  + 'mtable mtr mtd mstyle mpadded mphantom menclose mmultiscripts mprescripts none').split(' '));
const RICH_ATTRS = new Set(('colspan rowspan start display displaystyle scriptlevel stretchy fence separator '
  + 'lspace rspace form largeop movablelimits accent accentunder linethickness columnalign rowalign '
  + 'columnspan width mathvariant notation').split(' '));
const RICH_DROP = new Set(('script style template iframe frame object embed svg noscript textarea select button '
  + 'input form link meta base annotation annotation-xml mglyph malignmark').split(' '));

export function rich(html, imgRoot = './') {
  const doc = new DOMParser().parseFromString(`<!doctype html><body>${html}`, 'text/html');
  const walk = node => {
    for (const el of [...node.children]) {
      const tag = el.localName;
      if (RICH_DROP.has(tag)) { el.remove(); continue; }
      walk(el);
      if (!RICH_TAGS.has(tag)) { el.replaceWith(...el.childNodes); continue; }
      const src = el.getAttribute('src') || '';
      for (const { name } of [...el.attributes]) if (!RICH_ATTRS.has(name)) el.removeAttribute(name);
      if (tag === 'img') {
        // Картинки — только из папки img/ сайта
        if (!/^img\/[\w\/.-]+$/.test(src) || src.includes('..')) { el.remove(); continue; }
        el.setAttribute('src', imgRoot + src);
        el.setAttribute('alt', '');
        el.setAttribute('loading', 'lazy');
      }
    }
  };
  walk(doc.body);
  const frag = document.createDocumentFragment();
  frag.append(...[...doc.body.childNodes].map(n => document.importNode(n, true)));
  return frag;
}

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
    if (card.e && !['flip', 'open'].includes(card.k)) {
      root.querySelector('.explain').innerHTML = `<b>Разбор.</b> ${text(card.e)}`
        + (card.ai ? '<p class="muted small">Решение составил ИИ, ответ подтверждён на сайте ФИПИ.</p>' : '');
    }
    onDone(score);
  };

  const imgs = (card.img || []).map(src => `<img src="${esc(imgRoot + src)}" alt="" loading="lazy">`).join('')
    // График из набора — картинкой через data:, чтобы SVG не мог выполнить код
    + (card.svg ? `<img class="graph" src="data:image/svg+xml;charset=utf-8,${encodeURIComponent(card.svg)}" alt="График к заданию">` : '');
  // Файлы к заданию (архивы, таблицы) — ссылками на сайт ФИПИ, других адресов не пускаем
  const files = (card.files || []).filter(u => /^https:\/\/(ege|oge)\.fipi\.ru\/[^\s"'<>]+$/.test(u))
    .map(u => `<a class="btn small ghost" href="${esc(u)}" target="_blank" rel="noopener noreferrer">📎 Файл к заданию · ${esc(u.split('.').pop())}</a>`).join('');
  // Аудирование: запись с сайта ФИПИ
  const audio = (card.audio || []).filter(u => /^https:\/\/(ege|oge)\.fipi\.ru\/[^\s"'<>]+\.(mp3|ogg|wav)$/i.test(u))
    .map(u => `<audio controls preload="none" src="${esc(u)}"></audio>`).join('');
  root.innerHTML = `
    ${card.src ? `<div class="card-src">${esc(card.src)}</div>` : ''}
    ${audio ? `<div class="card-audio">${audio}</div>` : ''}
    <div class="card-q${card.h ? ' rich' : ''}">${card.h ? '' : text(card.q)}</div>
    ${imgs ? `<div class="card-img">${imgs}</div>` : ''}
    ${files ? `<div class="card-files">${files}</div>` : ''}
    <div class="card-body"></div>
    <div class="explain"></div>`;
  const body = root.querySelector('.card-body');
  if (card.h) root.querySelector('.card-q').append(rich(card.h, imgRoot));

  if (card.k === 'one' || card.k === 'many') {
    const multi = card.k === 'many';
    const right = new Set(multi ? card.a : [card.a]);
    body.innerHTML = `<div class="opts">${card.o.map(o =>
      `<button class="opt" data-id="${esc(o.id)}"><span class="opt-id">${esc(o.id)}</span><span class="rich">${o.h ? '' : text(o.t)}</span></button>`).join('')}</div>
      ${multi ? '<button class="btn primary check" disabled>Проверить</button>' : ''}`;
    const opts = [...body.querySelectorAll('.opt')];
    card.o.forEach((o, i) => o.h && opts[i].lastElementChild.append(rich(o.h, imgRoot)));
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
  } else if (card.k === 'num' || card.k === 'short') {
    // Краткий ответ ЕГЭ: число (запятая и точка равноправны), слово или цифры подряд
    const num = card.k === 'num';
    const want = [].concat(card.a);
    const digits = !num && /^\d+$/.test(want[0]);
    const hint = num ? 'Целое число или десятичная дробь, как в бланке ЕГЭ'
      : digits ? 'Цифры подряд, без пробелов и запятых' : 'Как в бланке ЕГЭ: без пробелов и знаков препинания';
    body.innerHTML = `
      <div class="num-row"><input class="num-input" inputmode="${num ? 'decimal' : digits ? 'numeric' : 'text'}" autocomplete="off"
        autocapitalize="off" spellcheck="false" placeholder="Ответ">
        <button class="btn primary check">Проверить</button></div>
      <p class="hint">${hint}</p>`;
    const input = body.querySelector('.num-input');
    const check = () => {
      const got = input.value.trim();
      if (!got) return toast('Введи ответ');
      const ok = num ? sameNumber(got, card.a) : sameShort(got, want, card.any);
      input.disabled = true;
      input.classList.add(ok ? 'ok' : 'bad');
      body.querySelector('.check').remove();
      body.querySelector('.hint').innerHTML = ok ? 'Верно!' : `Правильный ответ: <b>${esc(want[0])}</b>`;
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
        <div class="solution">${text(card.a)}${card.e && !open ? `<p class="muted">${text(card.e)}</p>` : ''}
          ${card.ai ? '<p class="muted small">Решение составил ИИ — сверяйся с критериями оценивания ФИПИ.</p>' : ''}</div>
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
