import { expect, test } from '@playwright/test';

test('a word is corrected and nudged, saved, and the player shows it', async ({
	page
}, testInfo) => {
	test.skip(testInfo.project.name === 'tv', 'the editor is for the phone and the laptop');
	await page.goto('/editar/demo-sintetico');
	// On a phone the lines are a drawer.
	if (testInfo.project.name === 'phone') await page.locator('.lines-toggle').click();
	await page
		.getByRole('navigation', { name: 'Liñas' })
		.getByRole('button', { name: /cántame/ })
		.click();
	// The mock server keeps edits while it runs: every run writes its own word.
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

	await page.goto('/cantar/demo-sintetico?t=8&controis');
	await expect(page.locator('[data-testid="stage"]')).toContainText(text);
});
