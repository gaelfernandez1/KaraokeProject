// Renders the app icons as PNG from the SVGs in static/icons, for the web manifest and iOS:
//   node dev/icons.mjs
// Run it again after changing an SVG. Needs the Playwright Chromium (and, on WSL without root,
// LD_LIBRARY_PATH to libnss3).
import { chromium } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const ICONS = new URL('../static/icons/', import.meta.url);

/** [source SVG, PNG written, size in pixels] */
const OUTPUTS = [
	['icon.svg', 'icon-192.png', 192],
	['icon.svg', 'icon-512.png', 512],
	['icon-maskable.svg', 'icon-maskable-512.png', 512],
	// iOS rounds the corners itself and wants a square without transparency.
	['icon.svg', 'apple-touch-icon-180.png', 180]
];

const browser = await chromium.launch();
try {
	const page = await browser.newPage({ deviceScaleFactor: 1 });
	for (const [source, target, size] of OUTPUTS) {
		const svg = readFileSync(new URL(source, ICONS)).toString('base64');
		await page.setViewportSize({ width: size, height: size });
		await page.setContent(
			'<style>html, body { margin: 0; } img { display: block; }</style>' +
				`<img src="data:image/svg+xml;base64,${svg}" width="${size}" height="${size}" alt="">`
		);
		await page.locator('img').evaluate((img) => img.decode());
		await page.screenshot({
			path: fileURLToPath(new URL(target, ICONS)),
			clip: { x: 0, y: 0, width: size, height: size }
		});
		console.log(`static/icons/${target} (${size}×${size})`);
	}
} finally {
	await browser.close();
}
