import { readdirSync } from 'node:fs';
import { expect, test, type Browser, type Page } from '@playwright/test';
import { phoneAtHome, tone } from './home';

// serve.sh imports every example package.
const EXAMPLES = readdirSync(new URL('../../../fixtures/packages/', import.meta.url)).length;

// The whole app against the real server, as at home: the laptop (localhost) is the owner and the
// TV; phones come in over the network. The engine is the fake one, so no GPU is needed.

async function upload(page: Page, title: string) {
	await page.goto('/crear');
	await page.locator('input[type="file"]').setInputFiles({
		name: 'proba.wav',
		mimeType: 'audio/wav',
		buffer: tone(3)
	});
	await page.getByLabel(/^Título/).fill(title);
	await page.getByLabel(/^Letra/).fill('Ola mar de Vigo\ncántame a túa canción');
	await page.getByRole('button', { name: 'Crear karaoke' }).last().click();
}

test('the library comes from the server and a song opens in the player', async ({ page }) => {
	await page.goto('/');
	const posters = page.locator('.wall .poster');
	await expect(posters).toHaveCount(EXAMPLES);
	await page.getByRole('link', { name: /Esencia/ }).click();
	await expect(page).toHaveURL(/\/cantar\/esencia$/);
	await expect(page.getByRole('heading', { name: 'Esencia' })).toBeVisible();

	// The audio is served with ranges, so the player can jump.
	const doc = await (await page.request.get('/media/esencia/karaoke.json')).json();
	const audio = await page.request.get(`/media/esencia/${doc.audio.instrumental}`, {
		headers: { Range: 'bytes=0-99' }
	});
	expect(audio.status()).toBe(206);
	expect((await audio.body()).length).toBe(100);
});

test('a song uploaded on the laptop is made and sung', async ({ page }) => {
	const title = `Subida ${Date.now()}`;
	await upload(page, title);
	const card = page.locator('.job').filter({ hasText: title });
	await expect(card).toBeVisible();
	await expect(card.getByRole('link', { name: 'Cantar agora' })).toBeVisible({ timeout: 30_000 });
	await card.getByRole('link', { name: 'Cantar agora' }).click();
	await expect(page.getByRole('heading', { name: title })).toBeVisible();
	await page.goto('/');
	await expect(page.getByRole('link', { name: new RegExp(`^${title},`) })).toBeVisible();
});

test('the karaoke video is made in the player and downloaded with the song name', async ({
	page
}) => {
	const title = `Vídeo ${Date.now()}`;
	await upload(page, title);
	const card = page.locator('.job').filter({ hasText: title });
	await card.getByRole('link', { name: 'Cantar agora' }).click({ timeout: 30_000 });
	await page.getByRole('button', { name: 'Descargar' }).click();
	const panel = page.getByRole('complementary', { name: 'Descargar' });
	await panel.getByRole('button', { name: 'Vertical, para redes' }).click();

	const link = panel.getByRole('link', { name: 'Descargar o vídeo' });
	await expect(link).toBeVisible({ timeout: 30_000 });
	await expect(panel.getByText('Vertical · Clásico')).toBeVisible();
	const [download] = await Promise.all([page.waitForEvent('download'), link.click()]);
	expect(download.suggestedFilename()).toBe(`${title} (karaoke vertical).mp4`);

	// The video stays with the song: the create page offers it too, under the same name.
	await page.goto('/crear');
	const made = page.locator('.job').filter({ hasText: title });
	await expect(made.getByRole('link', { name: 'Descargar o vídeo' })).toHaveAttribute(
		'download',
		`${title} (karaoke vertical).mp4`
	);
});

test('a phone at home can browse, but creates only once it is paired', async ({
	page: laptop,
	browser
}) => {
	const phone = await (await phoneAtHome(browser)).newPage();
	await phone.goto('/');
	await expect(phone.locator('.wall .poster').first()).toBeVisible();

	const title = `Dende o móbil ${Date.now()}`;
	await upload(phone, title);
	const notice = phone.getByRole('alert').filter({ hasText: 'aparello vinculado' });
	await expect(notice).toBeVisible();

	await laptop.goto('/axustes#aparello');
	await laptop.getByRole('button', { name: 'Vincular outro aparello' }).click();
	const code = (await laptop.getByLabel('Código de vinculación').textContent())!.trim();
	expect(code).toMatch(/^[A-Z]{8}$/);

	await notice.getByRole('link', { name: 'Vincular este aparello' }).click();
	const section = phone.locator('#aparello');
	await section.getByLabel('Código de vinculación').fill(code.toLowerCase());
	await section.getByRole('button', { name: 'Vincular', exact: true }).click();
	await expect(section.getByRole('status')).toHaveText(/Vinculado/);

	await upload(phone, title);
	const card = phone.locator('.job').filter({ hasText: title });
	await expect(card.getByRole('link', { name: 'Cantar agora' })).toBeVisible({ timeout: 30_000 });

	// The laptop sees the phone among its devices, and can unpair it.
	await laptop.reload();
	const devices = laptop.locator('#aparello .devices li');
	await expect(devices).toHaveCount(1);
	await devices.getByRole('button').click();
	await expect(devices).toHaveCount(0);
	await phone.goto('/axustes#aparello');
	await expect(phone.getByText('pode ver e cantar as cancións')).toBeVisible();
});

async function guest(browser: Browser, code: string, name: string): Promise<Page> {
	const page = await (await phoneAtHome(browser)).newPage();
	await page.goto(`/festa/${code}`);
	await page.getByLabel('Como te chamas?').fill(name);
	await page.getByRole('button', { name: 'Entrar na festa' }).click();
	await expect(page.locator('.songs li').first()).toBeVisible();
	return page;
}

test('a party: the laptop is the TV and the phones at home ask for songs', async ({
	page: tv,
	browser
}) => {
	await tv.setViewportSize({ width: 1920, height: 1080 });
	await tv.goto('/festa');
	await tv.getByRole('button', { name: /Comezar a festa|Comezar outra festa/ }).click();
	const code = (await tv.locator('.code').textContent())!.trim();
	expect(code).toMatch(/^[A-Z]{4}$/);
	// While WSL keeps the laptop off the Wi-Fi (NAT), the TV says why phones cannot get in.
	const info = await (await tv.request.get('/api/server')).json();
	const warning = tv.getByText('Os móbiles aínda non poden entrar');
	if (info.home_reachable) await expect(warning).toHaveCount(0);
	else await expect(warning).toBeVisible();

	const ana = await guest(browser, code, 'Ana');
	const brais = await guest(browser, code, 'Brais');
	await expect(tv.getByText('2 convidados')).toBeVisible();

	const request = (page: Page, title: RegExp) =>
		page.locator('.songs li').filter({ hasText: title }).first().getByRole('button').click();
	await request(ana, /Esencia/);
	await request(brais, /Feel/);
	await ana.getByRole('button', { name: 'A cola', exact: true }).click();
	await expect(ana.locator('.queue .who')).toHaveText(['Ana', 'Brais']);

	await expect(tv.locator('.up-next .name')).toHaveText('Ana');
	await tv.getByRole('button', { name: 'Comezar xa' }).click();
	await expect(tv.locator('[data-testid="stage"]')).toBeVisible({ timeout: 15_000 });

	// A guest who reloads is still the same guest (the server keeps the party).
	await brais.reload();
	await expect(brais.locator('.me')).toHaveText('Brais');
});

test('a correction made in the editor is saved in the library', async ({ page }) => {
	const id = 'mar-de-vigo-demo-sintetica';
	await page.goto(`/editar/${id}`);
	await page
		.getByRole('navigation', { name: 'Liñas' })
		.getByRole('button', { name: /cántame/ })
		.click();
	const word = `nosa${Date.now() % 1000}`;
	await page.getByRole('option').nth(2).click();
	await page.getByRole('button', { name: 'Corrixir o texto' }).click();
	await page.getByLabel('Corrixir o texto').fill(word);
	await page.locator('form.edit').getByRole('button', { name: 'Gardar' }).click();
	await page.locator('.bar').getByRole('button', { name: 'Gardar' }).click();
	await expect(page.getByText('Gardado', { exact: true })).toBeVisible();

	const doc = await (await page.request.get(`/media/${id}/karaoke.json`)).json();
	expect(doc.edited).toBe(true);
	expect(JSON.stringify(doc.lines)).toContain(word);
	await page.goto(`/cantar/${id}?t=8&controis`);
	await expect(page.locator('[data-testid="stage"]')).toContainText(word);
});

test('a song deleted in the editor leaves the library', async ({ page }) => {
	const title = `Borrar ${Date.now()}`;
	await upload(page, title);
	const card = page.locator('.job').filter({ hasText: title });
	await card.getByRole('link', { name: 'Cantar agora' }).click({ timeout: 30_000 });
	const id = new URL(page.url()).pathname.split('/').pop()!;
	await page.getByRole('link', { name: 'Corrixir a letra' }).click();
	await page.getByRole('button', { name: 'Borrar esta canción' }).click();
	await page.getByRole('button', { name: 'Si, borrala' }).click();
	await expect(page).toHaveURL(/\/$/);
	const songs = await (await page.request.get('/api/songs')).json();
	expect(songs.map((song: { id: string }) => song.id)).not.toContain(id);
	expect((await page.request.get(`/media/${id}/karaoke.json`)).status()).toBe(404);
});
