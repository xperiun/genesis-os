// Verification loop: tira screenshots desktop + mobile em vários pontos de scroll.
// Requer Playwright instalado no projeto (`npm i -D playwright && npx playwright install chromium`).
// Uso: `node scripts/shoot.cjs`  (o dev server precisa estar rodando).
// Porta: usa PORT do ambiente ou 5173 por padrão -> `PORT=5177 node scripts/shoot.cjs`.
const { chromium } = require('playwright');
const fs = require('fs');

const PORT = process.env.PORT || 5173;
const URL = `http://localhost:${PORT}/`;
const OUT = __dirname + '/shots';
fs.mkdirSync(OUT, { recursive: true });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function run(name, w, h) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: name === 'mobile' ? 2 : 1 });
  await page.goto(URL, { waitUntil: 'load' });
  // espera preloader sair
  await page.waitForSelector('#preloader.done', { timeout: 8000 }).catch(() => {});
  await sleep(600);

  const maxScroll = await page.evaluate(() => document.documentElement.scrollHeight - innerHeight);
  // pontos de scroll: reveal em etapas (0 a ~0.28 do doc é o pin do hero) + seções
  // hero pin ~= innerHeight*5.4; localiza as etapas do reveal dentro dele
  const heroPin = h * 5.4;
  const stops = [
    ['00-top', 0],
    ['01-open', Math.round(heroPin * 0.28)],
    ['02-mid', Math.round(heroPin * 0.55)],
    ['03-dash', Math.round(heroPin * 0.82)],
    ['04-heroEnd', Math.round(heroPin * 0.99)],
    ['05-impact', Math.round((heroPin + (maxScroll - heroPin) * 0.14))],
    ['06-stats', Math.round(heroPin + (maxScroll - heroPin) * 0.34)],
    ['07-cases', Math.round(heroPin + (maxScroll - heroPin) * 0.52)],
    ['07b-statement', Math.round(heroPin + (maxScroll - heroPin) * 0.63)],
    ['08-showcase', Math.round(heroPin + (maxScroll - heroPin) * 0.74)],
    ['09-studio', Math.round(heroPin + (maxScroll - heroPin) * 0.85)],
    ['10-contact', Math.round(maxScroll * 0.985)],
  ];
  for (const [label, y] of stops) {
    await page.evaluate((yy) => window.scrollTo(0, yy), y);
    await sleep(700);
    await page.screenshot({ path: `${OUT}/${name}-${label}.png` });
  }
  await browser.close();
  console.log(`${name} done (maxScroll=${maxScroll})`);
}

(async () => {
  await run('desktop', 1440, 900);
  await run('mobile', 390, 844);
})();
