import { expect, test } from '@playwright/test';

test('the interface language changes at once and is remembered', async ({ page, isMobile }) => {
	await page.goto('/axustes');
	await page.getByRole('radio', { name: 'Castellano' }).click();
	await expect(page.getByRole('heading', { name: 'Ajustes', level: 1 })).toBeVisible();
	await expect(page.locator('html')).toHaveAttribute('lang', 'es');
	await page.goto('/');
	// Phones keep the tab bar on the main menu; laptops and TVs get the big menu instead.
	const link = isMobile
		? page
				.getByRole('navigation', { name: 'Navegación principal' })
				.getByRole('link', { name: 'Canciones' })
		: page.locator('.menu').getByRole('link', { name: /^Fiesta/ });
	await expect(link).toBeVisible();
	await page.goto('/axustes');
	await page.getByRole('radio', { name: 'Galego' }).click();
	await expect(page.getByRole('heading', { name: 'Axustes', level: 1 })).toBeVisible();
});

test('the latency can be nudged and is kept for this device', async ({ page }) => {
	await page.goto('/axustes');
	await page.getByRole('button', { name: 'A letra 10 ms despois' }).click();
	await page.getByRole('button', { name: 'A letra 10 ms despois' }).click();
	await expect(page.locator('#retardo output')).toHaveText('20 ms');
	await page.reload();
	await expect(page.locator('#retardo output')).toHaveText('20 ms');
	await page.getByRole('button', { name: 'A letra 10 ms antes' }).click();
	await page.getByRole('button', { name: 'A letra 10 ms antes' }).click();
	await expect(page.locator('#retardo output')).toHaveText('0 ms');
});

test('the calibration says so when the browser plays no sound', async ({ page }, testInfo) => {
	test.skip(testInfo.project.name !== 'laptop', 'the same on every screen');
	await page.addInitScript(() => {
		AudioContext.prototype.resume = () => new Promise(() => {});
	});
	await page.goto('/axustes');
	await page.getByRole('button', { name: 'Comezar' }).click();
	await expect(page.getByRole('alert')).toContainText('O navegador non está a sacar son', {
		timeout: 10_000
	});
});
