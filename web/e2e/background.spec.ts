import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { expect, test } from '@playwright/test';

// The demo package, given a 10 s test video as background on the fly.
let clip = '';

test.beforeAll(() => {
	clip = join(mkdtempSync(join(tmpdir(), 'karaoke-bg-')), 'background.mp4');
	execFileSync('ffmpeg', [
		'-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=s=320x180:r=25:d=10',
		'-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-g', '25', '-movflags', '+faststart', clip
	]); // prettier-ignore
});

test.beforeEach(async ({ page }) => {
	await page.route('**/paquetes/demo-sintetico/karaoke.json', async (route) => {
		const doc = await (await route.fetch()).json();
		doc.video = { background: 'background.mp4' };
		await route.fulfill({ json: doc });
	});
	// With byte ranges, like the real server: without them a browser cannot seek in a video.
	await page.route('**/paquetes/demo-sintetico/background.mp4', (route) => {
		const body = readFileSync(clip);
		const range = /bytes=(\d+)-(\d*)/.exec(route.request().headers()['range'] ?? '');
		const start = range ? Number(range[1]) : 0;
		const end = range?.[2] ? Number(range[2]) : body.length - 1;
		return route.fulfill({
			status: range ? 206 : 200,
			contentType: 'video/mp4',
			headers: {
				'Accept-Ranges': 'bytes',
				...(range ? { 'Content-Range': `bytes ${start}-${end}/${body.length}` } : {})
			},
			body: body.subarray(start, end + 1)
		});
	});
});

const videoTime = (page: import('@playwright/test').Page) =>
	page.locator('video').evaluate((v: HTMLVideoElement) => v.currentTime);

test('the background video follows the song, paused on the right frame', async ({ page }) => {
	await page.goto('/proba-letra?paquete=demo-sintetico&t=4.5');
	await expect(page.locator('video')).toBeAttached();
	await expect.poll(() => videoTime(page)).toBeCloseTo(4.5, 1);

	await page.evaluate(() =>
		(window as unknown as { __lyricsTime: (t: number) => void }).__lyricsTime(7)
	);

	await expect.poll(() => videoTime(page)).toBeCloseTo(7, 1);
	expect(await page.locator('video').evaluate((v: HTMLVideoElement) => v.paused)).toBe(true);
});

test('past its end the background video loops', async ({ page }) => {
	await page.goto('/proba-letra?paquete=demo-sintetico&t=23');

	await expect.poll(() => videoTime(page)).toBeCloseTo(3, 1);
});
