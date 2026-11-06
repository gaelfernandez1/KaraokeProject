import { expect, test } from '@playwright/test';
import { createSong } from './songs';

test('a word is corrected and nudged, saved, and the player shows it', async ({
	page
}, testInfo) => {
	test.skip(testInfo.project.name === 'tv', 'the editor is for the phone and the laptop');
	const id = await createSong(page, `Para corrixir ${testInfo.project.name} ${Date.now()}`);
	await page.goto(`/editar/${id}`);
	// On a phone the lines are a drawer.
	if (testInfo.project.name === 'phone') await page.locator('.lines-toggle').click();
	await page
		.getByRole('navigation', { name: 'Liñas' })
		.getByRole('button', { name: /cántame/ })
		.click();
	const text = `nosa${testInfo.project.name}`;
	await page.getByRole('option').nth(2).click();
	await page.getByRole('button', { name: 'Corrixir o texto' }).click();
	await page.getByLabel('Corrixir o texto').fill(text);
	await page.locator('form.edit').getByRole('button', { name: 'Gardar' }).click();
	await expect(page.getByRole('option', { name: text })).toBeVisible();

	const start = page.getByRole('group', { name: 'Comeza' }).locator('output');
	const before = await start.textContent();
	await page
		.getByRole('group', { name: 'Comeza' })
		.getByRole('button', { name: 'Despois' })
		.click();
	await expect(start).not.toHaveText(before!);

	await page.getByRole('button', { name: 'Desfacer' }).click();
	await expect(start).toHaveText(before!);

	await expect(page.getByText('Hai cambios sen gardar')).toBeVisible();
	await page.locator('.bar').getByRole('button', { name: 'Gardar' }).click();
	await expect(page.getByText('Gardado', { exact: true })).toBeVisible();

	await page.goto(`/cantar/${id}?t=8&controis`);
	await expect(page.locator('[data-testid="stage"]')).toContainText(text);
});

test('a song can be deleted from the library, after saying yes', async ({ page }, testInfo) => {
	test.skip(testInfo.project.name !== 'laptop', 'one is enough: it deletes a song');
	const title = `Para borrar ${Date.now()}`;
	await createSong(page, title);
	await page.getByRole('link', { name: 'Corrixir a letra' }).click();

	const remove = page.getByRole('button', { name: 'Borrar esta canción' });
	await remove.click();
	await expect(page.getByText('Vaise da biblioteca')).toBeVisible();
	await page.getByRole('button', { name: 'Cancelar' }).click();
	await expect(page.getByText('Vaise da biblioteca')).toBeHidden();

	await remove.click();
	await page.getByRole('button', { name: 'Si, borrala' }).click();
	await expect(page).toHaveURL(/\/$/);
	await expect(page.locator('.wall .poster').first()).toBeVisible();
	await expect(page.getByRole('link', { name: new RegExp(`^${title}`) })).toHaveCount(0);
});
