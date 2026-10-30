// Screenshots of /proba-letra frozen at given times, for scripts/side_by_side.py:
// node e2e/capture.mjs <page url without t> <width> <height> <font family> <t>=<png> ...
import { chromium } from '@playwright/test';

const [url, width, height, family, ...shots] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: Number(width), height: Number(height) } });
const first = Number(shots[0].split('=')[0]);
await page.goto(`${url}&t=${first}`);
await page.waitForSelector('.row');
await page.waitForFunction(
	(name) => [...document.fonts].some((f) => f.family.includes(name) && f.status === 'loaded'),
	family
);
for (const shot of shots) {
	const [t, path] = shot.split('=');
	await page.evaluate((time) => window.__lyricsTime(time), Number(t));
	await page.evaluate(
		() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))
	);
	await page.screenshot({ path });
}
await browser.close();
