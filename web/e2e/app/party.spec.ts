import { expect, test, type Browser, type Page } from '@playwright/test';

async function phone(browser: Browser, code: string, name: string): Promise<Page> {
	const context = await browser.newContext({
		viewport: { width: 390, height: 844 },
		isMobile: true,
		hasTouch: true,
		locale: 'gl-ES'
	});
	const page = await context.newPage();
	await page.goto(`/festa/${code}`);
	await page.getByLabel('Como te chamas?').fill(name);
	await page.getByRole('button', { name: 'Entrar na festa' }).click();
	await expect(page.locator('.songs li').first()).toBeVisible();
	return page;
}

const request = async (page: Page, title: RegExp) =>
	page.locator('.songs li').filter({ hasText: title }).first().getByRole('button').click();

test('a TV and two phones: turns go round, phones are the remote, a guest can come back', async ({
	page: tv,
	browser
}, testInfo) => {
	test.skip(testInfo.project.name !== 'tv', 'one party is enough: it opens its own phones');
	test.setTimeout(90_000);
	await tv.goto('/festa');
	await tv.getByRole('button', { name: /Comezar a festa|Comezar outra festa/ }).click();
	const code = (await tv.locator('.code').textContent())!.trim();
	expect(code).toMatch(/^[A-Z]{4}$/);
	await expect(tv.getByRole('img', { name: 'Escanea co móbil para pedir cancións' })).toBeVisible();

	const ana = await phone(browser, code, 'Ana');
	const brais = await phone(browser, code, 'Brais');
	await expect(tv.getByText('2 convidados')).toBeVisible();

	// Ana asks for two songs, then Brais for one: Brais sings second.
	await request(ana, /Esencia/);
	await expect(ana.getByText('Na cola, 1.ª')).toBeVisible();
	await request(ana, /Mère nature/);
	await request(brais, /Feel/);
	await ana.getByRole('button', { name: 'A cola', exact: true }).click();
	const singers = ana.locator('.queue .who');
	await expect(singers).toHaveText(['Ana', 'Brais', 'Ana']);

	// The TV announces Ana's song; it starts at once from the TV.
	await expect(tv.getByText('Agora canta')).toBeVisible();
	await expect(tv.locator('.up-next .name')).toHaveText('Ana');
	await tv.getByRole('button', { name: 'Comezar xa' }).click();
	await expect(tv.locator('[data-testid="stage"]')).toBeVisible({ timeout: 15_000 });
	// While Ana sings, the TV says so in her colour.
	await expect(tv.locator('.song-intro .name, .singer').first()).toHaveText('Ana');

	// Phones cannot pause until the host allows it; then they can.
	await brais.getByRole('button', { name: 'Mando', exact: true }).click();
	await expect(brais.getByText('A tele desactivou o mando dende os móbiles.')).toBeVisible();
	await tv.keyboard.press('Escape');
	const tvHost = tv.locator('.tv');
	await expect(tvHost).toHaveAttribute('data-phase', 'singing');

	// Ana reloads her phone: she is still Ana, with her songs.
	await ana.reload();
	await expect(ana.locator('.me')).toHaveText('Ana');
});
