// The README banners (one per language) and GitHub's social preview, drawn with the app's own
// fonts and colours (docs/plan-v3/decisiones/017-noite.md): the name as two lines of a karaoke
// screen, the first one sung and the second half-way, beside the app's night globe of Galicia.
//   node dev/brand.mjs [--out ../docs/assets]
// Needs the Playwright Chromium (and, on WSL without root, LD_LIBRARY_PATH to libnss3).
import { chromium } from '@playwright/test';
import { mkdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const args = process.argv.slice(2);
const outIndex = args.indexOf('--out');
const out = outIndex === -1 ? '../docs/assets' : args[outIndex + 1];

const font = (file) =>
	`data:font/woff2;base64,${readFileSync(new URL(`../src/lib/ui/fonts/${file}`, import.meta.url)).toString('base64')}`;

// The README is in Galician first: its banner is banner.png.
const TAGLINES = {
	gl: 'Karaoke de calquera canción, coa letra acendéndose mentres se canta. Feito para o galego, funciona en calquera lingua.',
	en: 'Karaoke of any song, with the lyrics lighting up as they are sung. Made for Galician, works in any language.',
	es: 'Karaoke de cualquier canción, con la letra iluminándose mientras se canta. Hecho para el gallego, funciona en cualquier idioma.'
};
// A line of "laverca" by Clo Plas (CC BY-SA 4.0), the project's demo song, caught mid-word.
const LYRIC = { sung: 'É domingo ao medio', rest: 'día e non hai nada de ruído' };

// The app icon's globe: Galicia at night, on the same night as the banner.
const icon = readFileSync(new URL('../static/icons/icon.svg', import.meta.url), 'utf8');
// Without the icon's own square of night: the banner has its own.
const globe = `data:image/svg+xml;base64,${Buffer.from(icon.replace(/<rect[^>]*\/>/, '')).toString('base64')}`;

const css = `
	@font-face { font-family: 'Unbounded'; src: url(${font('Unbounded.woff2')}); font-weight: 500 800; }
	@font-face { font-family: 'Figtree'; src: url(${font('Figtree.woff2')}); font-weight: 400 700; }
	* { margin: 0; box-sizing: border-box; }
	html, body { width: 100%; height: 100%; }
	body {
		background: radial-gradient(120% 90% at 85% 0%, #0b2440, transparent 60%), #04070c;
		color: #f1f5f8;
		font-family: 'Figtree', sans-serif;
		display: flex;
		flex-direction: column;
		justify-content: center;
		padding: 0 88px;
		overflow: hidden;
	}
	.globe { position: absolute; top: 50%; right: -60px; height: 125%; transform: translateY(-50%); }
	.name {
		position: relative;
		font-family: 'Unbounded', sans-serif;
		font-weight: 650;
		line-height: 1.06;
		letter-spacing: -0.035em;
	}
	.row { position: relative; display: block; width: max-content; white-space: nowrap; }
	.row.sung { color: #ffd38a; }
	/* The gold copy of the text on top, cut at the point the singing has reached. */
	.fill { position: absolute; inset: 0; color: #ffd38a; }
	.tagline { position: relative; color: #a6b5c3; font-weight: 500; line-height: 1.35; }
	.lyric {
		position: relative;
		font-weight: 700;
		line-height: 1.1;
		white-space: nowrap;
	}
	.lyric .done { color: #ffd38a; }
`;

const name = (size, cut) =>
	`<div class="name" style="font-size:${size}px">` +
	`<span class="row sung">Proxecto Karaoke</span>` +
	`<span class="row">en Galego<span class="fill" style="clip-path: inset(-20% ${100 - cut}% -20% 0)">en Galego</span></span>` +
	`</div>`;

const banner = (lang) => `
	<style>${css} .tagline { font-size: 25px; margin-top: 24px; max-width: 44ch; }</style>
	<img class="globe" src="${globe}" alt="">
	${name(68, 52)}
	<p class="tagline">${TAGLINES[lang]}</p>`;

const social = `
	<style>${css}
		.lyric { font-size: 36px; margin-top: 36px; }
		.tagline { font-size: 26px; margin-top: 26px; max-width: 58ch; }
		.globe { height: 92%; right: -70px; }
		.tagline { max-width: 44ch; }
	</style>
	<img class="globe" src="${globe}" alt="">
	${name(70, 52)}
	<p class="lyric"><span class="done">${LYRIC.sung}</span>${LYRIC.rest}</p>
	<p class="tagline">${TAGLINES.gl}</p>`;

const jobs = [
	...Object.keys(TAGLINES).map((lang) => ({
		file: lang === 'gl' ? 'banner.png' : `banner.${lang}.png`,
		size: { width: 1280, height: 400 },
		html: banner(lang)
	})),
	{ file: 'social-preview.png', size: { width: 1280, height: 640 }, html: social }
];

mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
for (const job of jobs) {
	const page = await browser.newPage({ viewport: job.size, deviceScaleFactor: 1 });
	await page.setContent(`<!doctype html><html><body>${job.html}</body></html>`);
	await page.evaluate(() => document.fonts.ready);
	const file = join(out, job.file);
	await page.screenshot({ path: file });
	console.log(file);
	await page.close();
}
await browser.close();
