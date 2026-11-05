// Screenshots of a page of the dev server at phone, laptop and TV sizes, to review the design:
//   node dev/shots.mjs <path> [--sizes phone,laptop,tv,tv4k] [--out dir] [--full] [--wait ms]
//     [--base http://localhost:5190] [--name prefix] [--eval "js run before the shot"]
// Needs the Playwright Chromium (and, on WSL without root, LD_LIBRARY_PATH to libnss3).
import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

const SIZES = {
	phone: { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
	small: { width: 360, height: 740, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
	laptop: { width: 1440, height: 900, deviceScaleFactor: 1 },
	tv: { width: 1920, height: 1080, deviceScaleFactor: 1 },
	tv4k: { width: 1920, height: 1080, deviceScaleFactor: 2 }
};

const args = process.argv.slice(2);
const path = args.find((a) => !a.startsWith('--') && !args[args.indexOf(a) - 1]?.startsWith('--'));
const option = (name, fallback) => {
	const i = args.indexOf(`--${name}`);
	return i === -1 ? fallback : args[i + 1];
};
const sizes = option('sizes', 'phone,laptop,tv').split(',');
const out = option('out', 'shots');
const base = option('base', 'http://localhost:5190');
const name = option(
	'name',
	(path ?? '/').replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '') || 'home'
);
const wait = Number(option('wait', '600'));
const script = option('eval', null);
const full = args.includes('--full');

mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
for (const size of sizes) {
	const { width, height, ...device } = SIZES[size];
	const context = await browser.newContext({
		...device,
		viewport: { width, height },
		reducedMotion: 'reduce',
		locale: option('locale', 'gl-ES')
	});
	const page = await context.newPage();
	const errors = [];
	page.on('pageerror', (e) => errors.push(e.message));
	page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
	await page.goto(base + (path ?? '/'), { waitUntil: 'networkidle' });
	await page.evaluate(() => document.fonts.ready);
	if (script) await page.evaluate(script);
	await page.waitForTimeout(wait);
	const file = join(out, `${name}-${size}.png`);
	await page.screenshot({ path: file, fullPage: full });
	console.log(file, errors.length ? `errors: ${errors.join(' | ')}` : '');
	await context.close();
}
await browser.close();
