import { expect, test, type Page } from '@playwright/test';

// The synthetic demo song (fixtures/packages/demo-sintetico): line l1 "Ola, mar de Vigo," from
// 4.0 s with syllables O (4.0–4.3) and la, (4.3–4.8); l3 sung by a second singer; l4 at 23.0 s
// after a break, with a countdown.
// Times on screen run 0.05 s ahead of the song (theme anticipation).
const SIZES = {
	phone: { width: 390, height: 844 },
	laptop: { width: 1440, height: 900 },
	tv: { width: 1920, height: 1080 }
};

async function open(page: Page, t: number, row = 'row-l1-0', theme = 'clasico') {
	await page.goto(`/proba-letra?paquete=demo-sintetico&tema=${theme}&fondo=liso&t=${t}`);
	await expect(page.getByTestId(row)).toBeVisible();
	// The theme's font arrives after the first paint; rows are measured again when it does.
	await page.waitForFunction(() =>
		[...document.fonts].some((f) => f.family.includes('Nunito Black') && f.status === 'loaded')
	);
	await setTime(page, t);
}

async function setTime(page: Page, t: number) {
	await page.evaluate((time) => {
		(window as unknown as { __lyricsTime: (t: number) => void }).__lyricsTime(time);
	}, t);
	// Two frames: one for the clock, one for the loop to write the styles.
	await page.evaluate(
		() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))
	);
}

/** The fill edge of a row and the box of one of its syllables, in px from the row's left edge. */
async function fillAndPart(page: Page, rowId: string, partText: string) {
	return page.getByTestId(rowId).evaluate((row, text) => {
		const fill = parseFloat(
			getComputedStyle(row.querySelector('.sung')!).getPropertyValue('--fill')
		);
		const part = [...row.querySelectorAll<HTMLElement>('[data-part]')].find(
			(p) => p.textContent === text
		)!;
		return { fill, x0: part.offsetLeft, x1: part.offsetLeft + part.offsetWidth };
	}, partText);
}

for (const [name, viewport] of Object.entries(SIZES)) {
	test.describe(name, () => {
		test.use({ viewport });

		test('a syllable fills in step with its time', async ({ page }) => {
			// Halfway through "la," (4.3–4.8 s): 4.55 − 0.05.
			await open(page, 4.5);
			const { fill, x0, x1 } = await fillAndPart(page, 'row-l1-0', 'la,');

			expect(Math.abs(fill - (x0 + x1) / 2)).toBeLessThanOrEqual(1);
		});

		test('the next line is already written while this one is sung', async ({ page }) => {
			await open(page, 5);

			await expect(page.getByTestId('row-l2-0')).toBeVisible();
			await expect(page.getByTestId('row-l2-0')).toHaveCSS('opacity', '1');
		});

		test('seeking back and forth gives the same picture', async ({ page }) => {
			await open(page, 4.5);
			const before = await fillAndPart(page, 'row-l1-0', 'la,');

			await setTime(page, 25);
			await setTime(page, 4.5);

			expect(await fillAndPart(page, 'row-l1-0', 'la,')).toEqual(before);
		});

		test('looks right', async ({ page }) => {
			await open(page, 4.5);

			await expect(page).toHaveScreenshot(`demo-${name}.png`);
		});
	});
}

test('the countdown after a break goes out dot by dot', async ({ page }) => {
	await open(page, 20.5, 'row-l4-0');
	await expect(page.locator('.dot')).toHaveCount(3);

	await setTime(page, 21.5);
	await expect(page.locator('.dot')).toHaveCount(2);

	await setTime(page, 22.5);
	await expect(page.locator('.dot')).toHaveCount(1);
});

test('rows show the text of the document as written', async ({ page }) => {
	await open(page, 5);

	await expect(page.getByTestId('row-l1-0').locator('.base')).toHaveText('Ola, mar de Vigo,');
});

test('each singer fills with their own colour', async ({ page }) => {
	await open(page, 13, 'row-l3-0');

	await expect(page.getByTestId('row-l3-0').locator('.sung')).toHaveCSS(
		'color',
		'rgb(255, 107, 157)'
	);
});

test('in scroll mode the list moves up to the line being sung', async ({ page }) => {
	await page.setViewportSize(SIZES.phone);
	await page.goto('/proba-letra?paquete=demo-sintetico&tema=moderno&fondo=liso&t=5');
	await expect(page.getByTestId('row-l1-0')).toBeVisible();
	const offset = () =>
		page.locator('.list').evaluate((list) => new DOMMatrix(getComputedStyle(list).transform).m42);
	const first = await offset();

	await setTime(page, 9.5);

	expect(await offset()).toBeLessThan(first);
	await expect(page.getByTestId('row-l2-0')).toHaveCSS('opacity', '1');
});

test('the break bar shows its progress when opened in the middle of a break', async ({ page }) => {
	// nandomalo-esencia starts singing at 19.47 s: the intro bar runs from 0 to 16.47 s.
	await page.goto('/proba-letra?paquete=nandomalo-esencia&fondo=liso&t=8');
	await expect(page.locator('.bar')).toBeVisible();
	await setTime(page, 8);

	const inset = await page.locator('.bar-fill').evaluate((el) => getComputedStyle(el).clipPath);
	const right = parseFloat(inset.split(' ')[1]);
	expect(right).toBeCloseTo(100 * (1 - 8.05 / 16.4678), 0);
});

test('a backing line is faint as a whole, not layer by layer', async ({ page }) => {
	await page.route('**/paquetes/demo-sintetico/karaoke.json', async (route) => {
		const doc = await (await route.fetch()).json();
		doc.lines.splice(1, 0, {
			id: 'b1',
			start: 4.5,
			end: 5.0,
			singer: 's1',
			role: 'backing',
			words: [{ text: 'ei', start: 4.5, end: 5.0, confidence: null, parts: [] }]
		});
		await route.fulfill({ json: doc });
	});
	await open(page, 6);

	const row = page.getByTestId('row-b1-0');
	await expect(row).toHaveCSS('opacity', '0.85');
	await expect(row.locator('.base')).toHaveCSS('opacity', '1');
	await expect(row.locator('.sung')).toHaveCSS('opacity', '1');
});
