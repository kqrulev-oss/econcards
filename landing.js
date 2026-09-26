// Главная для репетиторов: что такое «Между уроками», как это выглядит у
// ученика и что видит репетитор. Ученики сюда не попадают — они приходят по
// ссылке ?t=… и сразу открывают тренажёр.

const STUDIO = 'studio/';
const TG = 'https://t.me/trwqxp';
const FLAME = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3c1 4 5 5 5 10a5 5 0 0 1-10 0c0-3 2-4 2-6 1.5 1 2 2 2 3 0-3 1-5 1-7z"/></svg>';
const ICONS = {
  inbox: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 13l2-8h12l2 8v6H4z"/><path d="M4 13h5l1 2h4l1-2h5"/></svg>',
  phone: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h4l2 5-3 2a11 11 0 0 0 5 5l2-3 5 2v4a2 2 0 0 1-2 2A17 17 0 0 1 3 6a2 2 0 0 1 2-2z"/></svg>',
  clock: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
};

const phone = `
  <div class="ld-phone">
    <div class="ld-phone-top">
      <span class="ld-phone-bar"><i style="width:40%"></i></span>
      <span class="ld-phone-n">4/10</span>
    </div>
    <div class="ld-phone-topic"><span>15</span> Н и НН</div>
    <div class="ld-phone-card">
      <p>Сколько Н пишется в слове?</p>
      <p class="ld-phone-word">серебря_ый</p>
      <div class="ld-opts"><button class="ld-opt" data-ok="1">н</button><button class="ld-opt">нн</button></div>
      <div class="ld-phone-exp" hidden><b>Разбор.</b> Суффикс -ЯН- → одна Н: серебряный.</div>
      <p class="ld-phone-hint">Попробуйте ответить</p>
    </div>
  </div>`;

const sticker = `<div class="ld-sticker" aria-hidden="true">${FLAME}<b>серия 6 дней</b></div>`;

const report = `
  <div class="ld-report" aria-hidden="true">
    <div class="ld-report-head">
      <span class="ld-avatar">ИП</span>
      <div><b>Иван Петров</b><small>был 2 часа назад</small></div>
      <span class="ld-badge">серия 6 дней</span>
    </div>
    <div class="ld-report-stats">
      <div><b>5 из 7</b><span>дней занимался</span></div>
      <div><b>142</b><span>задания</span></div>
      <div><b>78%</b><span>точность</span></div>
    </div>
    <div class="ld-report-weak">
      <span>Разобрать на уроке</span>
      <div class="ld-weak"><i>Н и НН</i><em style="--w:54%">54%</em></div>
      <div class="ld-weak"><i>Обособление</i><em style="--w:61%">61%</em></div>
    </div>
    <div class="ld-report-copy">Отчёт для родителей — скопировать ↗</div>
  </div>`;

export function renderLanding(root, library) {
  const total = library.reduce((n, p) => n + p.cards, 0);
  const rounded = Math.floor(total / 500) * 500;
  root.innerHTML = `
  <header class="ld-nav">
    <a class="ld-logo" href="./"><span class="ld-mark">М</span>Между уроками</a>
    <nav><a href="#how">Как это работает</a><a href="#faq">Вопросы</a></nav>
    <a class="ld-nav-tg" href="${TG}" target="_blank" rel="noopener" aria-label="Написать в Telegram"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 4L3 11l6 2 2 6 3-4 5 4z"/><path d="M9 13l8-6"/></svg></a>
    <a class="ld-nav-cta" href="${STUDIO}">Войти в студию</a>
  </header>

  <section class="ld-hero">
    <div class="ld-hero-text">
      <p class="ld-kicker">Для репетиторов</p>
      <h1>Домашка, от&nbsp;которой не&nbsp;сбегают</h1>
      <p class="ld-lead">Соберите тренажёр из своих материалов за&nbsp;15&nbsp;минут. Серии, цель дня и&nbsp;очки возвращают учеников к&nbsp;карточкам, а&nbsp;вы видите, кто занимался, где ошибки и&nbsp;что разобрать на&nbsp;уроке.</p>
      <div class="ld-cta">
        <a class="ld-btn primary" href="${STUDIO}">Собрать тренажёр</a>
        <a class="ld-btn" href="?p=ege-rus">Попробовать</a>
      </div>
      <p class="ld-note">Бесплатно для первых репетиторов · без установки · работает с&nbsp;телефона</p>
    </div>
    <div class="ld-hero-art"><span class="ld-blob" aria-hidden="true"></span>${phone}${sticker}${report}</div>
  </section>

  <section class="ld-scene">
    <img srcset="img/hero-bus-768.webp 768w, img/hero-bus.webp 1536w" sizes="(max-width: 800px) 100vw, 1080px"
      src="img/hero-bus.webp" width="1536" height="1024" loading="lazy" alt="Ученик решает карточки на телефоне в автобусе">
    <div class="ld-scene-cap"><b>10 минут в&nbsp;день — там, где удобно</b><span>В&nbsp;автобусе, в&nbsp;очереди, перед сном. Без учебника и&nbsp;даже без интернета.</span></div>
  </section>

  <section class="ld-pains">
    <h2>Знакомо?</h2>
    <div class="ld-grid3">
      <article><span class="ld-ico">${ICONS.inbox}</span><h3>Домашку делают в&nbsp;последний вечер</h3><p>Неделю тишина, а&nbsp;перед уроком — всё за&nbsp;час. Через месяц половина забыта.</p></article>
      <article><span class="ld-ico">${ICONS.phone}</span><h3>Родители спрашивают, есть ли прогресс</h3><p>А&nbsp;показать нечего, кроме ощущений. Оплата продлевается на&nbsp;доверии.</p></article>
      <article><span class="ld-ico">${ICONS.clock}</span><h3>Урок уходит на&nbsp;повторение</h3><p>Вместо нового материала — снова правила, которые проходили три недели назад.</p></article>
    </div>
  </section>

  <section class="ld-how" id="how">
    <h2>Три шага — и&nbsp;ученики в&nbsp;игре</h2>
    <ol class="ld-steps">
      <li><b>Добавьте материалы</b><p>Вставьте конспект, правила или задачи с&nbsp;решениями — ИИ сделает карточки, вы проверите их перед добавлением. Или возьмите готовые из&nbsp;библиотеки: больше ${rounded}&nbsp;заданий ЕГЭ и&nbsp;олимпиад с&nbsp;разборами.</p></li>
      <li><b>Отправьте ссылку ученикам</b><p>В&nbsp;Telegram или WhatsApp. Ничего устанавливать не&nbsp;нужно. Карточки возвращаются к&nbsp;ученику ровно тогда, когда он начинает их забывать.</p></li>
      <li><b>Смотрите прогресс</b><p>Кто занимался, сколько, с&nbsp;какой точностью и&nbsp;в&nbsp;каких темах ошибается. Готовый отчёт для родителей — в&nbsp;один клик.</p></li>
    </ol>
  </section>

  <section class="ld-features">
    <div class="ld-feature">
      <h3>ИИ проверяет развёрнутые решения</h3>
      <p>Ученик пишет решение — ИИ сверяет с&nbsp;вашим эталоном, показывает ошибку и&nbsp;даёт подсказку, не&nbsp;раскрывая ответ.</p>
    </div>
    <div class="ld-feature">
      <h3>Все задания ЕГЭ по прототипам</h3>
      <p>Русский язык и&nbsp;профильная математика: все задания по&nbsp;прототипам, подсказка «как решать» к&nbsp;каждому и&nbsp;пробный вариант с&nbsp;первичным баллом.</p>
    </div>
    <div class="ld-feature">
      <h3>Ваш бренд</h3>
      <p>Ученики видят ваше имя и&nbsp;ваш цвет. Для них это ваш тренажёр, а&nbsp;не&nbsp;очередное приложение.</p>
    </div>
    <div class="ld-feature">
      <h3>Работает без интернета</h3>
      <p>В&nbsp;метро и&nbsp;в&nbsp;очереди. Результаты отправятся, когда появится связь.</p>
    </div>
  </section>

  <section class="ld-faq" id="faq">
    <h2>Вопросы</h2>
    <details><summary>Какие предметы подходят?</summary><p>Любые, где есть правила, термины и&nbsp;задачи: тренажёр собирается из&nbsp;ваших материалов. Готовая библиотека: ЕГЭ по&nbsp;русскому языку (все задания), профильная математика (все 19 заданий) и&nbsp;олимпиадная экономика.</p></details>
    <details><summary>А&nbsp;если ИИ ошибётся в&nbsp;карточке?</summary><p>Каждую карточку вы видите до&nbsp;того, как она попадёт к&nbsp;ученикам, и&nbsp;можете исправить или убрать. Без вашего подтверждения ничего не&nbsp;публикуется.</p></details>
    <details><summary>Сколько времени это займёт у&nbsp;ученика?</summary><p>10&nbsp;минут в&nbsp;день. Новые карточки приходят понемногу, старые — на&nbsp;повторение по&nbsp;графику, который подстраивается под ученика.</p></details>
    <details><summary>Что видят родители?</summary><p>Короткий текст: сколько дней занимался, сколько решил, точность и&nbsp;что подтягиваете на&nbsp;занятиях. Вы копируете его и&nbsp;отправляете сами.</p></details>
    <details><summary>Какие данные учеников хранятся?</summary><p>Только имя, которое ученик ввёл сам, и&nbsp;статистика занятий. Ни&nbsp;телефонов, ни&nbsp;почты.</p></details>
  </section>

  <section class="ld-final">
    <h2>Соберите первый тренажёр сегодня</h2>
    <p>15&nbsp;минут — и&nbsp;ученики получат ссылку. Есть вопросы или хотите, чтобы тренажёр собрали за&nbsp;вас? Напишите.</p>
    <div class="ld-cta center-cta">
      <a class="ld-btn primary" href="${STUDIO}">Собрать тренажёр</a>
      <a class="ld-btn tg" href="${TG}" target="_blank" rel="noopener">Написать в&nbsp;Telegram</a>
    </div>
  </section>

  <footer class="ld-foot">
    <div class="ld-student">
      <b>Вы ученик?</b>
      <span class="row"><input id="code" placeholder="Код от репетитора" autocapitalize="off"><button class="ld-btn primary small" id="join">Открыть</button></span>
      <a href="#/library">Открытые наборы для самостоятельной подготовки</a>
    </div>
    <p class="ld-copy">Между уроками · тренажёр для учеников репетитора · <a href="${TG}" target="_blank" rel="noopener">Telegram @trwqxp</a></p>
  </footer>`;

  const join = () => {
    const c = root.querySelector('#code').value.trim().replace(/.*[?&]t=/, '');
    if (c) location.search = '?t=' + encodeURIComponent(c);
  };
  root.querySelector('#join').onclick = join;
  // Живой пример карточки: ответ, подсветка и разбор — как у ученика
  const opts = [...root.querySelectorAll('.ld-opt')];
  opts.forEach(o => o.onclick = () => {
    opts.forEach(x => { x.disabled = true; if (x.dataset.ok) x.classList.add('ok'); });
    if (!o.dataset.ok) o.classList.add('bad');
    root.querySelector('.ld-phone-exp').hidden = false;
    root.querySelector('.ld-phone-hint').textContent = o.dataset.ok ? '+10 · Верно! Так ученик занимается каждый день' : 'Ошибка вернётся завтра — и репетитор её увидит';
    root.querySelector('.ld-phone-hint').classList.add(o.dataset.ok ? 'ok' : 'bad');
  });
  root.querySelector('#code').onkeydown = e => e.key === 'Enter' && join();
}
