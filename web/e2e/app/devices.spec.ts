import { expect, test } from '@playwright/test';

// The stand-in server treats a browser with this cookie as an unpaired phone at home.
const asVisitor = async (context: import('@playwright/test').BrowserContext) =>
	context.addCookies([{ name: 'karaoke_mock_visitor', value: '1', url: 'http://localhost:5181' }]);

test('the laptop shows a code and a QR to pair another device', async ({ page }) => {
	await page.goto('/axustes#aparello');
	const section = page.locator('#aparello');
	await expect(section.getByText('Este é o portátil que fai os karaokes')).toBeVisible();
	await section.getByRole('button', { name: 'Vincular outro aparello' }).click();
	await expect(section.getByLabel('Código de vinculación')).toHaveText('BCDFGHJK');
	await expect(
		section.getByRole('img', { name: 'Código QR para vincular un aparello' })
	).toBeVisible();
});

test('a phone types the code and becomes the owner’s', async ({ page, context }) => {
	await asVisitor(context);
	await page.goto('/axustes#aparello');
	const section = page.locator('#aparello');
	await expect(section.getByText('pode ver e cantar as cancións')).toBeVisible();
	await section.getByLabel('Código de vinculación').fill('bcdf ghjk');
	await section.getByRole('button', { name: 'Vincular', exact: true }).click();
	await expect(section.getByRole('status')).toHaveText(/Vinculado/);
	await expect(section.getByText('Este é o portátil')).toBeVisible();
});

test('a wrong code says so', async ({ page, context }) => {
	await asVisitor(context);
	await page.goto('/axustes#aparello');
	const section = page.locator('#aparello');
	await section.getByLabel('Código de vinculación').fill('XXXXXXXX');
	await section.getByRole('button', { name: 'Vincular', exact: true }).click();
	await expect(section.getByRole('status')).toHaveText('Ese código non vale ou xa caducou.');
});

test('the pairing link from the QR pairs the phone', async ({ page, context }) => {
	await asVisitor(context);
	await page.goto('/vincular?code=BCDFGHJK');
	await expect(page.getByRole('status')).toHaveText(/Vinculado/);
	await page.getByRole('link', { name: 'Ir ás cancións' }).click();
	await expect(page).toHaveURL(/\/$/);
});

test('an unpaired phone is told how to create songs', async ({ page, context }) => {
	await asVisitor(context);
	await page.goto('/crear');
	await page.getByLabel('Ligazón').fill('https://example.com/video');
	await page.getByRole('button', { name: 'Crear karaoke' }).click();
	const notice = page.getByRole('alert').filter({ hasText: 'aparello vinculado' });
	await expect(notice).toBeVisible();
	await notice.getByRole('link', { name: 'Vincular este aparello' }).click();
	await expect(page).toHaveURL(/\/axustes#aparello$/);
});
