// The screenshots and the animation of the README (docs/assets/), taken from the real server
// with the demo song "laverca" (Clo Plas, CC BY-SA 4.0) and the three example songs:
//   karaoke-server --data <dir> import fixtures/packages/{cortez-feel-stripped,law-mere-nature,nandomalo-esencia} <laverca package>
//   karaoke-server --data <dir> serve --port 8775
//   node dev/readme-media.mjs [--base http://localhost:8775] [--out ../docs/assets] [--only gif]
// The laverca package is made with `karaoke make` (fixtures/packages/cloplas-laverca/LICENSE).
// Needs ffmpeg and the Playwright Chromium (on WSL without root, LD_LIBRARY_PATH to libnss3).
import { chromium } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readdirSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const args = process.argv.slice(2);
const option = (name, fallback) => {
	const i = args.indexOf(`--${name}`);
	return i === -1 ? fallback : args[i + 1];
};
const base = option('base', 'http://localhost:8775');
const out = option('out', '../docs/assets');
const only = option('only', null);

const PHONE = { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true };
const SONG = 'laverca';
// The GIF: "Non pasará non pasará nada…", four lines in a row, from a few seconds before so the
// controls have hidden, for this many seconds.
const GIF = { seek: 229, settle: 3.5, seconds: 10, fps: 10, width: 820 };

const shots = [
	{
		// The main menu: the night globe with the lights of Galicia on.
		file: 'menu.png',
		viewport: { width: 1440, height: 810 },
		path: '/',
		ready: (page) => page.locator('canvas.shown').waitFor()
	},
	{
		file: 'player-tv.png',
		viewport: { width: 1920, height: 1080 },
		path: `/cantar/${SONG}?t=63.6`
	},
	{ file: 'player-phone.png', device: PHONE, path: `/cantar/${SONG}?t=159.1` },
	{
		file: 'party-tv.png',
		viewport: { width: 1920, height: 1080 },
		path: '/festa',
		// Two phones join with the QR code and ask for songs; the TV calls the first singer.
		ready: async (page, browser) => {
			await page.getByRole('button', { name: /Comezar a festa|Comezar outra festa/ }).click();
			const code = (await page.locator('.code').textContent()).trim();
			const uxia = await guest(browser, code, 'Uxía');
			const brais = await guest(browser, code, 'Brais');
			await ask(uxia, /laverca/);
			await ask(brais, /Esencia/);
			await ask(uxia, /Mère nature/);
			await page.getByText('Agora canta').waitFor();
			await page.waitForTimeout(1500);
			await page.screenshot({ path: join(out, 'screens', 'party-tv.png') });
			await uxia.getByRole('button', { name: 'A cola', exact: true }).click();
			await uxia.waitForTimeout(800);
			await uxia.screenshot({ path: join(out, 'screens', 'party-phone.png') });
			console.log(join(out, 'screens', 'party-phone.png'));
			await uxia.context().close();
			await brais.context().close();
		},
		taken: true
	},
	{
		file: 'editor.png',
		viewport: { width: 1440, height: 900 },
		path: `/editar/${SONG}`,
		ready: async (page) => {
			await page.getByText('É domingo ao mediodía e non hai nada de ruído').first().click();
			await page.waitForTimeout(800);
		}
	}
];

async function guest(browser, code, name) {
	const { width, height, ...device } = PHONE;
	const context = await browser.newContext({
		...device,
		viewport: { width, height },
		locale: 'gl-ES'
	});
	const page = await context.newPage();
	await page.goto(`${base}/festa/${code}`);
	await page.getByLabel('Como te chamas?').fill(name);
	await page.getByRole('button', { name: 'Entrar na festa' }).click();
	await page.locator('.songs li').first().waitFor();
	return page;
}

const ask = (page, title) =>
	page.locator('.songs li').filter({ hasText: title }).first().getByRole('button').click();

async function open(browser, shot, extra = {}) {
	const { width, height, ...device } = shot.device ?? { ...shot.viewport };
	const context = await browser.newContext({
		...device,
		viewport: { width, height },
		locale: 'gl-ES',
		...extra
	});
	const page = await context.newPage();
	return { context, page };
}

mkdirSync(join(out, 'screens'), { recursive: true });
const browser = await chromium.launch();

if (only === null || only === 'shots') {
	for (const shot of shots) {
		const { context, page } = await open(browser, shot, { reducedMotion: 'reduce' });
		await page.goto(base + shot.path, { waitUntil: 'networkidle' });
		await page.evaluate(() => document.fonts.ready);
		if (shot.ready) await shot.ready(page, browser);
		await page.waitForTimeout(1200);
		const file = join(out, 'screens', shot.file);
		if (!shot.taken) await page.screenshot({ path: file });
		console.log(file);
		await context.close();
	}
}

if (only === null || only === 'gif') {
	const videos = mkdtempSync(join(tmpdir(), 'karaoke-gif-'));
	// TV size: the lyrics are drawn bigger there, and stay legible once scaled down.
	const size = { width: 1920, height: 1080 };
	const { context, page } = await open(
		browser,
		{ viewport: size },
		{ recordVideo: { dir: videos, size } }
	);
	const started = Date.now();
	await page.goto(`${base}/cantar/${SONG}`, { waitUntil: 'networkidle' });
	await page.evaluate(() => document.fonts.ready);
	const sing = page.getByRole('button', { name: 'Cantar' });
	await sing.waitFor();
	await sing.click();
	await page.locator('.player[data-state="playing"]').waitFor();
	await page
		.locator('input[type="range"]')
		.first()
		.evaluate((input, seconds) => {
			input.value = String(seconds);
			input.dispatchEvent(new Event('input', { bubbles: true }));
		}, GIF.seek);
	await page.mouse.move(size.width - 2, size.height / 2);
	await page.waitForTimeout(GIF.settle * 1000);
	const from = (Date.now() - started) / 1000;
	await page.waitForTimeout(GIF.seconds * 1000 + 500);
	await context.close();
	const video = join(
		videos,
		readdirSync(videos).find((name) => name.endsWith('.webm'))
	);
	const gif = join(out, 'demo.gif');
	const scale = `fps=${GIF.fps},scale=${GIF.width}:-1:flags=lanczos`;
	execFileSync('ffmpeg', [
		'-v',
		'error',
		'-y',
		'-ss',
		from.toFixed(2),
		'-t',
		String(GIF.seconds),
		'-i',
		video,
		'-filter_complex',
		`[0:v]${scale},split[a][b];[a]palettegen=max_colors=72:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle`,
		'-loop',
		'0',
		gif
	]);
	rmSync(videos, { recursive: true, force: true });
	console.log(gif, `${(statSync(gif).size / 1e6).toFixed(1)} MB`);
}

await browser.close();
