// Measures how smoothly the lyrics move on a slower device: plays the demo song in the dev
// server (the stand-in API) with the CPU slowed down as a mid-range phone, and reports the time
// between frames. Local only, like `pnpm perf`: `node scripts/frame-budget.mjs`.
import { chromium } from '@playwright/test';
import { createServer } from 'vite';

const PORT = 5193;
const RUNS = [
	{ name: 'phone ×4', viewport: { width: 390, height: 844 }, throttle: 4 },
	{ name: 'phone ×6', viewport: { width: 390, height: 844 }, throttle: 6 },
	{ name: 'tv ×4', viewport: { width: 1920, height: 1080 }, throttle: 4 }
];

const server = await createServer({ server: { port: PORT, strictPort: true }, logLevel: 'silent' });
await server.listen();
const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
try {
	for (const run of RUNS) {
		const page = await browser.newPage({ viewport: run.viewport, locale: 'gl-ES' });
		await page.goto(`http://localhost:${PORT}/cantar/demo-sintetico`);
		const sing = page.getByRole('button', { name: 'Cantar' });
		await sing.waitFor({ state: 'visible', timeout: 30_000 });
		await page.waitForFunction(
			() => {
				const button = [...document.querySelectorAll('button')].find((b) =>
					b.textContent?.includes('Cantar')
				);
				return button !== undefined && !button.disabled;
			},
			null,
			{ timeout: 30_000 }
		);
		const cdp = await page.context().newCDPSession(page);
		await cdp.send('Emulation.setCPUThrottlingRate', { rate: run.throttle });
		await sing.click();
		const gaps = await page.evaluate(
			() =>
				new Promise((resolve) => {
					const out = [];
					let last = performance.now();
					const until = last + 8000;
					const step = (now) => {
						out.push(now - last);
						last = now;
						if (now < until) requestAnimationFrame(step);
						else resolve(out);
					};
					requestAnimationFrame(step);
				})
		);
		gaps.sort((a, b) => a - b);
		const at = (q) => gaps[Math.min(gaps.length - 1, Math.floor(q * gaps.length))].toFixed(1);
		const long = gaps.filter((g) => g > 33.4).length;
		console.log(
			`${run.name.padEnd(9)} frames ${gaps.length} p50 ${at(0.5)} ms p95 ${at(0.95)} ms p99 ${at(0.99)} ms, >2 frames: ${long}`
		);
		await page.close();
	}
} finally {
	await browser.close();
	await server.close();
}
