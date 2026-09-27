// Раздел родителя в личном кабинете: дети, их прогресс по наборам,
// привязка по коду и оплата доступа к библиотеке.
import { api, loadPack, esc, day, plural, toast, courseStats } from '../lib.js';
import { payDialog, daysLeft, dateRu } from '../account.js';
const packs = new Map(); // ref → набор (кэш)

// Набор нужен только для старых записей прогресса — без сводки sum (см. ниже)
async function getPack(ref) {
  if (!packs.has(ref)) packs.set(ref, loadPack(ref, '../').catch(() => null));
  return packs.get(ref);
}

/* Сводка по одному набору из прогресса ученика. Сервер (GET /me/children) отдаёт журнал по дням,
   ДЗ уроков, число освоенных карточек и sum — то, что посчитало приложение ученика: название,
   слабые темы, размер набора, сроки ДЗ курса. С sum набор не нужен (pack = null). Старые записи
   без sum приходят с карточками — тогда слабые темы считаются по набору */
export function stats(prog, pack) {
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
  const ps = prog.sum;
  // Слабые темы — как у репетитора в студии (сводка приложения ученика). Без сводки — по карточкам
  // набора, где ошибок больше 30% (не меньше 5 ответов)
  let weak = [];
  if (ps) weak = (ps.weak || []).map(w => ({ title: String(w.t || ''), acc: w.a }));
  else if (pack) {
    const byTopic = {};
    const topicOf = Object.fromEntries(pack.cards.map(c => [c.id, c.t]));
    for (const [id, s] of Object.entries(prog.cards || {})) {
      const tid = topicOf[id];
      if (!tid) continue;
      const x = byTopic[tid] ||= { n: 0, w: 0 };
      x.n += s.n; x.w += s.w;
    }
    weak = Object.entries(byTopic).filter(([, x]) => x.n >= 5 && 1 - x.w / x.n < 0.7)
      .map(([tid, x]) => ({ title: pack.topics.find(tp => tp.id === tid)?.title || tid, acc: Math.round((1 - x.w / x.n) * 100) }))
      .sort((a, b) => a.acc - b.acc).slice(0, 3);
  }
  const mastered = prog.mastered ?? Object.values(prog.cards || {}).filter(s => s.b >= 3).length;
  const acc = w => w.n ? Math.round(w.ok / w.n * 100) : null;
  // ДЗ курса — та же функция, что у ученика в сводке и в студии; сроки — из сводки или из набора
  const lessons = ps ? (ps.course || []).map(l => ({ id: l.id, hw: { due: l.due } })) : pack?.course?.lessons;
  const course = lessons?.length ? courseStats(prog.les, { lessons }, t) : null;
  const total = ps?.total || pack?.limited?.total || pack?.cards.length || 0;
  return { streak, days7, strip, weeks, last, weak, mastered, course, total, title: ps?.title || pack?.title || '', week, acc7: acc(week), accPrev: acc(prev), acc };
}

const ago = d => d === null ? 'ещё не занимался' : d === day() ? 'занимался сегодня' : d === day() - 1 ? 'занимался вчера' : `занимался ${plural(day() - d, 'день', 'дня', 'дней')} назад`;

function packBlock(s) {
  const trend = s.acc7 !== null && s.accPrev !== null ? (s.acc7 >= s.accPrev ? ` <span class="trend up">+${s.acc7 - s.accPrev}</span>` : ` <span class="trend down">${s.acc7 - s.accPrev}</span>`) : '';
  const level = n => n === 0 ? 0 : n < 5 ? 1 : n < 15 ? 2 : 3;
  const weeks = s.weeks.some(w => w.n) ? `<div class="weeks">${s.weeks.map((w, i) => {
    const a = s.acc(w), tone = a === null ? '' : a < 60 ? 'bad' : a < 80 ? 'mid' : 'ok';
    return `<div class="wk ${tone}"><b>${a === null ? '—' : a + '%'}</b><span class="wk-bar"><i style="height:${a ?? 0}%"></i></span><small>${w.n || ''}</small><em>${i === 7 ? 'эта' : '−' + (7 - i)}</em></div>`;
  }).join('')}</div>` : '';
  return `
    <section class="panel kid-pack">
      <div class="kid-pack-head"><b>${esc(s.title || 'Тренажёр')}</b><span class="muted">${ago(s.last)}</span></div>
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
      ${s.course?.n ? `<p class="kid-course${s.course.onTime < s.course.n ? ' mid' : ''}"><span>ДЗ курса</span><b>${s.course.onTime} из ${s.course.n} в срок</b></p>` : ''}
      <p class="muted small-note">Освоено ${s.mastered} из ${s.total} карточек · решено ${plural(s.week.n, 'карточка', 'карточки', 'карточек')} за неделю</p>
    </section>`;
}

// Доступ ребёнка к библиотеке ЕГЭ: оплачен, пробный, через репетитора или нет
function libLine(ch) {
  const lib = ch.plans?.lib || {}, now = Date.now();
  const via = ch.plans?.libVia || 0;
  let text, pay = 'Оплатить доступ';
  if ((lib.paidUntil || 0) > now) { text = `Библиотека ЕГЭ оплачена до ${dateRu(lib.paidUntil)}`; pay = 'Продлить'; }
  else if (via > now) { text = 'Библиотека ЕГЭ открыта — входит в тариф репетитора'; pay = ''; }
  else if ((lib.trialEnd || 0) > now) text = `Пробный доступ к библиотеке ЕГЭ: осталось ${plural(daysLeft(lib.trialEnd), 'день', 'дня', 'дней')}`;
  else text = 'Библиотека ЕГЭ: бесплатная часть (2 прототипа в каждом задании)';
  const tone = (lib.paidUntil || 0) > now || via > now ? 'ok' : (lib.trialEnd || 0) > now ? 'trial' : 'free';
  return `<div class="panel plan ${tone} kid-plan"><span>${text}</span>${pay ? `<button class="btn small primary" data-pay="${esc(ch.id)}" data-name="${esc(ch.name)}">${pay}</button>` : ''}</div>`;
}

export async function renderChildren($app) {
  const viewChildren = () => renderChildren($app);
  let children;
  try { ({ children } = await api('/me/children')); } catch (err) { $app.innerHTML = `<section class="panel">${esc(err.message)}</section>`; return; }
  const blocks = await Promise.all(children.map(async ch => {
    // Набор качаем, только если у записи нет сводки (прогресс сохранён старой версией приложения)
    const parts = await Promise.all(ch.packs.map(async pr => packBlock(stats(pr, pr.sum ? null : await getPack(pr.ref)))));
    return `<section class="kid">
      <div class="kid-head"><span class="avatar">${esc((ch.name || 'У').slice(0, 2).toUpperCase())}</span><h1>${esc(ch.name)}</h1>
        <button class="btn small" data-unlink="${esc(ch.id)}" aria-label="Убрать">Убрать</button></div>
      ${libLine(ch)}
      ${parts.join('') || '<p class="panel muted">Ребёнок ещё не занимался с аккаунтом. Когда он начнёт, здесь появится сводка.</p>'}
    </section>`;
  }));
  $app.innerHTML = `
    ${blocks.join('')}
    <section class="panel">
      <h2>${children.length ? 'Добавить ещё ребёнка' : 'Добавьте ребёнка'}</h2>
      <p class="muted">Попросите у ребёнка код: в его личном кабинете или в тренажёре Профиль → «Код для родителя». Код может выдать и репетитор.</p>
      <div class="row"><input id="code" placeholder="Например, K7M2PX" maxlength="6" autocapitalize="characters" autocomplete="off"><button class="btn primary" id="add">Добавить</button></div>
    </section>`;
  const add = async () => {
    const code = $app.querySelector('#code').value.trim();
    if (!code) return toast('Введите код');
    try { await api('/me/children', { method: 'POST', body: { code } }); toast('Готово'); viewChildren(); }
    catch (err) { toast(err.message); }
  };
  $app.querySelector('#add').onclick = add;
  $app.querySelector('#code').onkeydown = e => { if (e.key === 'Enter') add(); };
  $app.querySelectorAll('[data-pay]').forEach(b => b.onclick = () => payDialog({ product: 'lib', forAcct: b.dataset.pay, forName: b.dataset.name }));
  $app.querySelectorAll('[data-unlink]').forEach(b => b.onclick = async () => {
    if (!confirm('Убрать ребёнка из кабинета? Его прогресс не пропадёт, добавить снова можно по новому коду.')) return;
    await api(`/me/children/${b.dataset.unlink}`, { method: 'DELETE' });
    viewChildren();
  });
}

