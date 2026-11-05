// Checks that the built app stays light: the JavaScript (gzipped) each main screen loads on a
// cold visit must fit its budget. Run after `pnpm build`: `pnpm perf`.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { gzipSync } from 'node:zlib';
import { chromium } from '@playwright/test';
import { preview } from 'vite';

/** kB of gzipped JavaScript a cold visit to each screen may load. */
const BUDGETS = { '/': 120, '/cantar/demo': 150, '/festa': 150, '/crear': 130 };

const server = await preview({ preview: { port: 4319, strictPort: true }, logLevel: 'silent' });
const browser = await chromium.launch();
let failed = false;
try {
	for (const [path, budget] of Object.entries(BUDGETS)) {
		const page = await browser.newPage();
		const scripts = new Set();
		page.on('request', (request) => {
			const url = new URL(request.url());
			if (url.pathname.endsWith('.js')) scripts.add(url.pathname);
		});
		await page.goto(`http://localhost:4319${path}`, { waitUntil: 'networkidle' });
		let bytes = 0;
		for (const script of scripts) bytes += gzipSync(readFileSync(join('build', script))).length;
		const kb = bytes / 1000;
		const ok = kb <= budget;
		failed ||= !ok;
		console.log(
			`${ok ? 'ok  ' : 'OVER'} ${path.padEnd(14)} ${kb.toFixed(1)} kB of ${budget} kB (${scripts.size} files)`
		);
		await page.close();
	}
} finally {
	await browser.close();
	await server.close();
}
process.exit(failed ? 1 : 0);
