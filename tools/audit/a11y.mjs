/**
 * Автоматическая проверка доступности (WCAG 2.2 A/AA) через Playwright + axe-core.
 *
 * Использование:
 *   BASE_URL=https://skaititaji.onrender.com node a11y.mjs
 *   (по умолчанию http://127.0.0.1:8000)
 *
 * Проходит по списку публичных и авторизованных страниц (демо-вход в один клик),
 * прогоняет axe-core и печатает отчёт. Завершается с кодом 1, если есть
 * нарушения serious/critical — это «ворота качества» для CI.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';

const BASE = process.env.BASE_URL || 'http://127.0.0.1:8000';
const AXE = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js';
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

// Публичные + сценарии авторизованного демо-входа
const PAGES = [
  { url: '/', name: 'landing' },
  { url: '/login', name: 'login' },
  { url: '/demo', name: 'demo' },
  { url: '/palidziba', name: 'help-index' },
  { url: '/palidziba/iedzivotajs', name: 'help-resident' },
  { url: '/palidziba/apsaimniekotajs', name: 'help-manager' },
  { url: '/palidziba/administrators', name: 'help-admin' },
  { url: '/privatums', name: 'privacy' },
  { url: '/pieejamiba', name: 'accessibility' },
  { url: '/demo-login?role=resident', name: 'resident-dashboard' },
  { url: '/demo-login?role=manager', name: 'manager-dashboard' },
  { url: '/demo-login?role=admin', name: 'admin-dashboard' },
  { url: '/admin/inbox', name: 'admin-console' },
];

async function run() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  let totalSerious = 0;
  const report = [];

  for (const p of PAGES) {
    await page.goto(BASE + p.url, { waitUntil: 'networkidle' });
    await page.addScriptTag({ url: AXE });
    const res = await page.evaluate(async (tags) => {
      const r = await window.axe.run(document, { runOnly: tags });
      return r.violations.map((v) => ({
        id: v.id, impact: v.impact, count: v.nodes.length, help: v.help,
      }));
    }, TAGS);

    const serious = res.filter((v) => v.impact === 'serious' || v.impact === 'critical');
    totalSerious += serious.reduce((s, v) => s + v.count, 0);
    report.push({ page: p.name, url: p.url, violations: res });

    const mark = serious.length === 0 ? '✓' : '✗';
    console.log(`${mark} ${p.name.padEnd(20)} ${p.url}`);
    for (const v of res) {
      console.log(`    [${v.impact}] ${v.id} × ${v.count} — ${v.help}`);
    }
  }

  // мобильная проверка: нет горизонтального скролла на 360px
  await page.setViewportSize({ width: 360, height: 780 });
  let overflow = 0;
  for (const p of PAGES.slice(0, 9)) {
    await page.goto(BASE + p.url, { waitUntil: 'networkidle' });
    const o = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    if (o) { overflow++; console.log(`✗ MOBILE overflow: ${p.url}`); }
  }

  fs.writeFileSync('a11y-report.json', JSON.stringify(report, null, 2));
  await browser.close();

  console.log('\n─────────────────────────────');
  console.log(`Serious/critical нарушений: ${totalSerious}`);
  console.log(`Мобильный горизонтальный скролл: ${overflow} страниц`);
  console.log('Отчёт: a11y-report.json');

  if (totalSerious > 0 || overflow > 0) {
    console.error('\n❌ Ворота качества НЕ пройдены.');
    process.exit(1);
  }
  console.log('\n✅ Ворота качества пройдены (WCAG 2.2 AA, mobile).');
}

run().catch((e) => { console.error(e); process.exit(1); });
