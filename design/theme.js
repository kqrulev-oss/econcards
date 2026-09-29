const allowed = new Set(['a', 'b', 'c']);
export const descriptions = {
  a: 'Стикеры — энергия коротких занятий. Чёткие контуры, заметные действия, маленькие победы.',
  b: 'Тетрадь — пространство для мысли. Тёплая бумага, спокойный ритм, внимание к решению.',
  c: 'Приложение — всё под рукой. Компактные карточки, быстрые переходы, лёгкие слои.',
};
const params = new URLSearchParams(location.search);
let saved;
try { saved = localStorage.getItem('zd-design'); } catch { /* приватный режим */ }
export let currentDesign = allowed.has(params.get('design')) ? params.get('design') : allowed.has(saved) ? saved : 'a';
export function setDesign(value) {
  if (!allowed.has(value)) return;
  currentDesign = value;
  document.documentElement.dataset.design = value;
  document.getElementById('design-css').href = new URL(`app-${value}.css`, import.meta.url).href;
  try { localStorage.setItem('zd-design', value); } catch { /* приватный режим */ }
  const url = new URL(location.href); url.searchParams.set('design', value); history.replaceState(history.state, '', url);
  document.querySelectorAll('[data-design]').forEach(b => {
    if (b.tagName === 'BUTTON') b.setAttribute('aria-pressed', String(b.dataset.design === value));
  });
  const note = document.getElementById('direction-description');
  if (note) note.textContent = descriptions[value];
  document.querySelectorAll('.design-open').forEach(a => { a.href = `student.html?p=ege-math&design=${value}`; });
  document.dispatchEvent(new CustomEvent('designchange', { detail: value }));
}
export function setAppearance(value) {
  const mode = ['light', 'dark'].includes(value) ? value : 'auto';
  document.documentElement.dataset.appearance = mode;
  const url = new URL(location.href);
  if (mode === 'auto') url.searchParams.delete('theme'); else url.searchParams.set('theme', mode);
  history.replaceState(history.state, '', url);
  // Тёмные правила остаются обычным prefers-color-scheme; ручной просмотр
  // использует те же объявления, извлечённые из активного CSS ниже.
  refreshAppearance();
}
function refreshAppearance() {
  const override = document.getElementById('appearance-css') || Object.assign(document.createElement('style'), { id: 'appearance-css' });
  if (!override.isConnected) document.head.append(override);
  override.textContent = '';
  const mode = document.documentElement.dataset.appearance;
  if (!mode || mode === 'auto') return;
  const sheet = document.getElementById('design-css').sheet;
  if (!sheet) return;
  // Только токены самого направления, без второй копии палитры в JS.
  for (const rule of sheet.cssRules) {
    if (mode === 'light' && rule.selectorText === ':root') override.textContent += rule.cssText;
    if (mode === 'dark' && rule.conditionText === '(prefers-color-scheme: dark)') override.textContent += [...rule.cssRules].map(r => r.cssText).join('\n');
  }
  override.textContent += `:root { color-scheme: ${mode}; }`;
}
document.getElementById('design-css').addEventListener('load', refreshAppearance);
document.querySelectorAll('button[data-design]').forEach(b => b.addEventListener('click', () => setDesign(b.dataset.design)));
const appearance = document.getElementById('appearance');
if (appearance) {
  appearance.value = ['light', 'dark'].includes(params.get('theme')) ? params.get('theme') : 'auto';
  appearance.addEventListener('change', () => setAppearance(appearance.value));
}
setDesign(currentDesign);
setAppearance(params.get('theme'));
