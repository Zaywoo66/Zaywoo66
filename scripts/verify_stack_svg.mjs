#!/usr/bin/env node
/** Inspect the generated SVG as an image, matching GitHub's rendering context. */
import { chromium } from 'playwright';
import { readFile, mkdir } from 'node:fs/promises';
import { resolve, join } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const out = join(root, 'assets', 'evidence', 'stack');
await mkdir(out, { recursive: true });
const chrome = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const browser = await chromium.launch({
  headless: true,
  executablePath: chrome,
});

async function render(activeBrowser, theme, width, reducedMotion, times) {
  const page = await activeBrowser.newPage({ viewport: { width, height: 460 }, deviceScaleFactor: 1 });
  await page.emulateMedia({ colorScheme: theme, reducedMotion: reducedMotion ? 'reduce' : 'no-preference' });
  const svg = await readFile(join(root, 'assets', `stack-${theme}.svg`));
  const src = `data:image/svg+xml;base64,${svg.toString('base64')}`;
  const external = [];
  page.on('request', request => { if (!request.url().startsWith('data:')) external.push(request.url()); });
  await page.setContent(`<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;background:${theme === 'dark' ? '#0d1117' : '#fff'};color:${theme === 'dark' ? '#f0f6fc' : '#1f2328'};font-family:system-ui,sans-serif}.readme{max-width:1200px;margin:auto;padding:16px;box-sizing:border-box}h2{font-size:25px;margin:0 0 16px}img{display:block;width:100%;height:auto}</style><main class="readme"><h2>Stack</h2><img alt="Stack" src="${src}"></main>`);
  await page.locator('img').evaluate(image => image.decode());
  let elapsed = 0;
  const frames = [];
  for (const time of times) {
    if (time > elapsed) await page.waitForTimeout((time - elapsed) * 1000);
    elapsed = time;
    const suffix = reducedMotion ? `reduced-${time}s` : `${time}s`;
    frames.push(await page.screenshot({ path: join(out, `${theme}-${width}-${suffix}.png`) }));
  }
  if (reducedMotion && !frames[0].equals(frames.at(-1))) {
    throw new Error('Reduced-motion image changed over time');
  }
  if (!reducedMotion && frames.length > 1 && frames[0].equals(frames.at(-1))) {
    throw new Error('Animated image did not change over time');
  }
  const horizontalScroll = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  if (horizontalScroll) throw new Error(`${theme}/${width}: horizontal scroll`);
  if (external.length) throw new Error(`External requests: ${external.join(', ')}`);
  await page.close();
}

try {
  await render(browser, 'dark', 1200, false, [0, 3, 6, 9]);
  await render(browser, 'light', 1200, false, [3]);
  await render(browser, 'dark', 375, false, [3]);
  const reducedBrowser = await chromium.launch({
    headless: true, executablePath: chrome, args: ['--force-prefers-reduced-motion=reduce'],
  });
  try {
    await render(reducedBrowser, 'dark', 375, true, [0, 3]);
  } finally {
    await reducedBrowser.close();
  }
  console.log('Eight image-context screenshots, no horizontal scroll or external request.');
} finally {
  await browser.close();
}
