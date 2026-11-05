import { expect, test } from '@playwright/test';

test('the interface language changes at once and is remembered', async ({ page, isMobile }) => {
	await page.goto('/axustes');
	await page.getByRole('radio', { name: 'Castellano' }).click();
	await expect(page.getByRole('heading', { name: 'Ajustes', level: 1 })).toBeVisible();
	await expect(page.locator('html')).toHaveAttribute('lang', 'es');
	await page.goto('/');
	const nav = page.getByRole('navigation', { name: 'Navegación principal' });
	await expect(nav.getByRole('link', { name: isMobile ? 'Canciones' : 'Canciones' })).toBeVisible();
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
