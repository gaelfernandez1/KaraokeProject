import { expect, test } from '@playwright/test';

test('the library shows the songs as posters and finds them without accents', async ({ page }) => {
	await page.goto('/');
	const posters = page.locator('.wall .poster');
	await expect(posters.first()).toBeVisible();
	const all = await posters.count();
	expect(all).toBeGreaterThan(1);

	await page.getByPlaceholder('Título ou artista').fill('vigo');
	await expect(page.getByRole('link', { name: /Mar de Vigo/ }).first()).toBeVisible();
	expect(await posters.count()).toBeLessThan(all);

	await page.getByPlaceholder('Título ou artista').fill('nada disto existe');
	await expect(page.getByText('Non hai nada con «nada disto existe».')).toBeVisible();
	await page.getByRole('button', { name: 'Quitar os filtros' }).click();
	expect(await posters.count()).toBe(all);
});

test('a poster opens its song in the player', async ({ page }) => {
	await page.goto('/');
	await page
		.getByRole('link', { name: /Mar de Vigo/ })
		.first()
		.click();
	await expect(page).toHaveURL(/\/cantar\/demo-sintetico$/);
	await expect(page.getByRole('heading', { name: /Mar de Vigo/ })).toBeVisible();
});

test('with a remote, the arrows reach the search and filters above the posters', async ({
	page
}, testInfo) => {
	test.skip(testInfo.project.name !== 'tv', 'a remote drives the TV');
	await page.goto('/');
	await expect(page.locator('.wall .poster').first()).toBeVisible();
	await page.keyboard.press('ArrowDown'); // into the wall
	await expect(page.locator('.wall :focus')).toHaveCount(1);
	await page.keyboard.press('ArrowUp'); // out of it, to what sits above
	await expect(page.locator('.wall :focus')).toHaveCount(0);
	await expect(page.locator(':focus')).toHaveCount(1);
	// Further up, the menu (Crear, Festa, Axustes) is reachable too.
	for (let i = 0; i < 5 && (await page.locator('nav :focus').count()) === 0; i++) {
		await page.keyboard.press('ArrowUp');
	}
	await expect(page.locator('nav :focus')).toHaveCount(1);
});
