// Кабинет родителя: вход, привязка ребёнка по коду и понятная сводка —
// занимается ли, насколько точно, что подтягивать.
import { api, loadPack, esc, day, plural, toast } from '../lib.js';
import { signedIn, account, loginDialog, logout, addRole, finishRedirectLogin } from '../account.js';

const $app = document.getElementById('app');
const packs = new Map(); // ref → набор (кэш)

async function getPack(ref) {
  if (!packs.has(ref)) packs.set(ref, loadPack(ref, '../').catch(() => null));
  return packs.get(ref);
}

// Сводка по одному набору из сырого прогресса ученика
function stats(prog, pack) {
  const t = day();
  const log = prog.log || {};
  const at = d => log[d] || { d: 0, ok: 0 };
  let streak = 0, d = log[t]?.d ? t : t - 1;
  while (at(d).d) { streak++; d--; }
  const sum = (from, to) => { let n = 0, ok = 0; for (let x = from; x <= to; x++) { n += at(x).d; ok += at(x).ok; } return { n, ok }; };
  const week = sum(t - 6, t), prev = sum(t - 13, t - 7);
  const days7 = Array.from({ length: 7 }, (_, i) => at(t - 6 + i).d).filter(Boolean).length;
  const strip = Array.from({ length: 14 }, (_, i) => at(t - 13 + i).d);
  const weeks = Array.from({ length: 8 }, (_, i) => sum(t - (7 - i) * 7 - 6, t - (7 - i) * 7));
  const active = Object.keys(log).filter(k => log[k].d).map(Number);
  const last = active.length ? Math.max(...active) : null;
  // Слабые темы: по карточкам набора, где ошибок больше 30% (не меньше 5 ответов)
  const byTopic = {};
  if (pack) {
    const topicOf = Object.fromEntries(pack.cards.map(c => [c.id, c.t]));
    for (const [id, s] of Object.entries(prog.cards || {})) {
      const tid = topicOf[id];
      if (!tid) continue;
      const x = byTopic[tid] ||= { n: 0, w: 0 };
      x.n += s.n; x.w += s.w;
    }
  }
  const weak = Object.entries(byTopic).filter(([, x]) => x.n >= 5 && 1 - x.w / x.n < 0.7)
    .map(([tid, x]) => ({ title: pack.topics.find(tp => tp.id === tid)?.title || tid, acc: Math.round((1 - x.w / x.n) * 100) }))
    .sort((a, b) => a.acc - b.acc).slice(0, 3);
  const mastered = Object.values(prog.cards || {}).filter(s => s.b >= 3).length;
  const acc = w => w.n ? Math.round(w.ok / w.n * 100) : null;
  return { streak, days7, strip, weeks, last, weak, mastered, total: pack?.cards.length || 0, week, acc7: acc(week), accPrev: acc(prev), acc };
}

const ago = d => d === null ? 'ещё не занимался' : d === day() ? 'занимался сегодня' : d === day() - 1 ? 'занимался вчера' : `занимался ${plural(day() - d, 'день', 'дня', 'дней')} назад`;

function packBlock(s, pack) {
  const trend = s.acc7 !== null && s.accPrev !== null ? (s.acc7 >= s.accPrev ? ` <span class="trend up">+${s.acc7 - s.accPrev}</span>` : ` <span class="trend down">${s.acc7 - s.accPrev}</span>`) : '';
  const level = n => n === 0 ? 0 : n < 5 ? 1 : n < 15 ? 2 : 3;
  const weeks = s.weeks.some(w => w.n) ? `<div class="weeks">${s.weeks.map((w, i) => {
    const a = s.acc(w), tone = a === null ? '' : a < 60 ? 'bad' : a < 80 ? 'mid' : 'ok';
    return `<div class="wk ${tone}"><b>${a === null ? '—' : a + '%'}</b><span class="wk-bar"><i style="height:${a ?? 0}%"></i></span><small>${w.n || ''}</small><em>${i === 7 ? 'эта' : '−' + (7 - i)}</em></div>`;
  }).join('')}</div>` : '';
  return `
    <section class="panel kid-pack">
      <div class="kid-pack-head"><b>${esc(pack?.title || 'Тренажёр')}</b><span class="muted">${ago(s.last)}</span></div>
      <div class="hero-stats">
        <div><b>${s.days7} из 7</b><span>дней на неделе</span></div>
        <div><b>${s.acc7 === null ? '—' : s.acc7 + '%'}${trend}</b><span>точность</span></div>
        <div><b>${s.streak}</b><span>${plural(s.streak, 'день', 'дня', 'дней').replace(/^\d+ /, '')} подряд</span></div>
      </div>
      <h2>Две недели</h2>
      <div class="strip-big"><div class="strip">${s.strip.map(n => `<i class="l${level(n)}"></i>`).join('')}</div></div>
      ${weeks ? `<h2>Точность по неделям</h2>${weeks}` : ''}
      <h2>Что подтягивать</h2>
      ${s.weak.length ? `<ul class="kid-weak">${s.weak.map(w => `<li><span>${esc(w.title.replace(/^\d+\.\s*/, ''))}</span><b>${w.acc}%</b></li>`).join('')}</ul>`
        : '<p class="muted">Явно слабых тем нет — хороший знак.</p>'}
      <p class="muted small-note">Освоено ${s.mastered} из ${s.total} карточек · решено ${plural(s.week.n, 'карточка', 'карточки', 'карточек')} за неделю</p>
    </section>`;
}

async function viewChildren() {
  let children;
  try { ({ children } = await api('/me/children')); } catch (err) { $app.innerHTML = `<section class="panel">${esc(err.message)}</section>`; return; }
  const a = account();
  const blocks = await Promise.all(children.map(async ch => {
    const parts = await Promise.all(ch.packs.map(async pr => { const pack = await getPack(pr.ref); return packBlock(stats(pr, pack), pack); }));
    return `<section class="kid">
      <div class="kid-head"><span class="avatar">${esc((ch.name || 'У').slice(0, 2).toUpperCase())}</span><h1>${esc(ch.name)}</h1>
        <button class="btn small" data-unlink="${esc(ch.id)}" aria-label="Убрать">Убрать</button></div>
      ${parts.join('') || '<p class="panel muted">Ребёнок ещё не занимался с аккаунтом. Когда он начнёт, здесь появится сводка.</p>'}
    </section>`;
  }));
  $app.innerHTML = `
    <header class="top"><a class="back" href="../?about" aria-label="На главную">←</a>
      <div><div class="brand-by">Между уроками · для родителей</div><div class="brand-title">${esc(a?.name ? 'Здравствуйте, ' + a.name.split(' ')[0] : 'Кабинет родителя')}</div></div>
      <button class="btn small" id="logout">Выйти</button></header>
    ${blocks.join('')}
    <section class="panel">
      <h2>${children.length ? 'Добавить ещё ребёнка' : 'Добавьте ребёнка'}</h2>
      <p class="muted">Попросите у ребёнка код: в тренажёре Профиль → «Код для родителя». Код может выдать и репетитор.</p>
      <div class="row"><input id="code" placeholder="Например, K7M2PX" maxlength="6" autocapitalize="characters" autocomplete="off"><button class="btn primary" id="add">Добавить</button></div>
    </section>`;
  const add = async () => {
    const code = $app.querySelector('#code').value.trim();
    if (!code) return toast('Введите код');
    try { await api('/me/children', { method: 'POST', body: { code } }); toast('Готово'); viewChildren(); }
    catch (err) { toast(err.message); }
  };
  $app.querySelector('#add').onclick = add;
  $app.querySelector('#code').onkeydown = e => e.key === 'Enter' && add();
  $app.querySelector('#logout').onclick = async () => { await logout(); route(); };
  $app.querySelectorAll('[data-unlink]').forEach(b => b.onclick = async () => {
    if (!confirm('Убрать ребёнка из кабинета? Его прогресс не пропадёт, добавить снова можно по новому коду.')) return;
    await api(`/me/children/${b.dataset.unlink}`, { method: 'DELETE' });
    viewChildren();
  });
}

function viewWelcome() {
  $app.innerHTML = `
    <header class="top"><a class="back" href="../?about" aria-label="На главную">←</a>
      <div><div class="brand-by">Между уроками</div><div class="brand-title">Для родителей</div></div></header>
    <section class="topic-hero">
      <h1>Видно, как ребёнок занимается между уроками</h1>
      <span class="topic-hero-meta">Дни занятий, точность по неделям и темы, которые стоит подтянуть. Без звонков репетитору.</span>
    </section>
    <ol class="parent-steps">
      <li><b>Войдите</b> — через Telegram, почту, Яндекс, VK или Google.</li>
      <li><b>Введите код</b> — ребёнок найдёт его в тренажёре: Профиль → «Код для родителя».</li>
      <li><b>Смотрите прогресс</b> — сводка обновляется после каждого занятия.</li>
    </ol>
    <button class="btn cta big" id="login">Войти</button>`;
  $app.querySelector('#login').onclick = () => loginDialog({ role: 'parent', why: 'Кабинет родителя: прогресс ребёнка и оплата доступа.', onDone: async () => { await addRole('parent'); route(); } });
}

function route() {
  return signedIn() ? viewChildren() : viewWelcome();
}

const done = await finishRedirectLogin();
if (done) await addRole('parent');
route();
