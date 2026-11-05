import { expect, test } from '@playwright/test';

test('a karaoke is made from a link and can be sung when it is ready', async ({ page }) => {
	const title = `Proba ${Date.now()}`;
	await page.goto('/crear');
	await page.getByRole('button', { name: 'Crear karaoke' }).last().click();
	await expect(
		page.getByText('Falta a canción: escolle un ficheiro ou pega unha ligazón.').first()
	).toBeVisible();

	await page.getByLabel('Ligazón').fill('https://example.com/video');
	await page.getByLabel(/^Título/).fill(title);
	await page.getByLabel(/^Letra/).fill('[Estribillo]\nOla mar de Vigo');
	await page.getByRole('button', { name: 'Crear karaoke' }).last().click();

	const card = page.locator('.job').filter({ hasText: title });
	await expect(card).toBeVisible();
	await expect(card.getByRole('link', { name: 'Cantar agora' })).toBeVisible({ timeout: 15_000 });
	await card.getByRole('link', { name: 'Cantar agora' }).click();
	await expect(page.getByRole('heading', { name: title })).toBeVisible();
});

test('a file name gives the title and the artist', async ({ page }) => {
	await page.goto('/crear');
	await page.locator('input[type="file"]').setInputFiles({
		name: '9Louro - La Favorita (Official Video).m4a',
		mimeType: 'audio/mp4',
		buffer: Buffer.from('fake audio')
	});
	await expect(page.getByLabel(/^Título/)).toHaveValue('La Favorita');
	await expect(page.getByLabel(/^Artista/)).toHaveValue('9Louro');
});
