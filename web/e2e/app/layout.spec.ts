import { expect, test } from '@playwright/test';

const PAGES = [
	'/',
	'/crear',
	'/axustes',
	'/cantar/demo-sintetico',
	'/editar/demo-sintetico',
	'/festa'
];

for (const path of PAGES) {
	test(`${path} fits the screen width`, async ({ page }) => {
		await page.goto(path);
		await page.waitForLoadState('networkidle');
		const width = page.viewportSize()!.width;
		const scroll = await page.evaluate(() => document.documentElement.scrollWidth);
		expect(scroll).toBeLessThanOrEqual(width);
	});
}

test('the lyrics style previews show their whole lines', async ({ page }) => {
	await page.goto('/axustes');
	await page.waitForFunction(() => document.fonts.status === 'loaded');
	const previews = page.locator('.preview');
	await expect(previews).toHaveCount(3);
	for (let i = 0; i < 3; i++) {
		const clipped = await previews.nth(i).evaluate((preview) => {
			const box = preview.getBoundingClientRect();
			return [...preview.querySelectorAll('.row')].some((row) => {
				const r = row.getBoundingClientRect();
				return r.left < box.left - 1 || r.right > box.right + 1 || r.top < box.top - 1;
			});
		});
		expect(clipped).toBe(false);
	}
});
