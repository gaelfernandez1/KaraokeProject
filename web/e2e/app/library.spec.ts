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
