import { expect, test, type Page } from '@playwright/test';
import { createSong } from './songs';

const time = async (page: Page) => Number(await page.locator('.player').getAttribute('data-time'));

test('a song plays, pauses and jumps with the keyboard', async ({ page }) => {
	await page.goto('/cantar/demo-sintetico');
	const sing = page.getByRole('button', { name: 'Cantar' });
	await expect(sing).toBeEnabled({ timeout: 15_000 });
	await sing.click();
	await expect(page.locator('.player')).toHaveAttribute('data-state', 'playing');
	await expect.poll(() => time(page), { timeout: 5000 }).toBeGreaterThan(0.5);

	await page.keyboard.press('Space');
	await expect(page.locator('.player')).toHaveAttribute('data-state', 'paused');
	const paused = await time(page);
	await page.keyboard.press('ArrowRight');
	await expect.poll(() => time(page)).toBeGreaterThan(paused + 4.5);
});

test('the keyboard still works after clicking the picture', async ({ page }, testInfo) => {
	test.skip(testInfo.project.name === 'phone', 'phones have no keyboard');
	await page.goto('/cantar/demo-sintetico');
	const sing = page.getByRole('button', { name: 'Cantar' });
	await expect(sing).toBeEnabled({ timeout: 15_000 });
	await sing.click();
	await expect(page.locator('.player')).toHaveAttribute('data-state', 'playing');
	await page.locator('.hit').click(); // pauses
	await expect(page.locator('.player')).toHaveAttribute('data-state', 'paused');
	await page.keyboard.press('Space');
	await expect(page.locator('.player')).toHaveAttribute('data-state', 'playing');
});

test('the sound panel changes the guide vocals and the lyrics style', async ({ page }) => {
	await page.goto('/cantar/demo-sintetico');
	await page.getByRole('button', { name: 'Son' }).click();
	const panel = page.getByRole('complementary', { name: 'Son' });
	await expect(panel).toBeVisible();
	await panel.getByRole('radio', { name: /Moderno/ }).click();
	await expect(panel.getByRole('radio', { name: /Moderno/ })).toHaveAttribute(
		'aria-checked',
		'true'
	);
	await panel.getByRole('button', { name: 'Pechar' }).click();
	await expect(panel).toBeHidden();
});

test('the karaoke video is made and downloaded from the player', async ({ page }, testInfo) => {
	const title = `Vídeo ${testInfo.project.name}`;
	const id = await createSong(page, title);
	await page.getByRole('button', { name: 'Descargar' }).click();
	const panel = page.getByRole('complementary', { name: 'Descargar' });
	// The sound and the lyrics, named after the song.
	await expect(panel.getByRole('link', { name: 'Música sen voz' })).toHaveAttribute(
		'download',
		`${title} (sen voz).wav`
	);
	await expect(panel.getByText('Aínda non hai vídeos desta canción.')).toBeVisible();

	await panel.getByRole('button', { name: 'Horizontal, para a tele' }).click();
	await expect(panel.getByRole('progressbar', { name: 'Facendo o vídeo' })).toBeVisible();
	// Pressing again while it is made does not queue a second copy.
	await panel.getByRole('button', { name: 'Horizontal, para a tele' }).click();
	await expect(panel.getByRole('progressbar', { name: 'Facendo o vídeo' })).toHaveCount(1);
	const video = panel.getByRole('link', { name: 'Descargar o vídeo' });
	await expect(video).toBeVisible({ timeout: 15_000 });
	const name = `${title} (karaoke).mp4`;
	await expect(video).toHaveAttribute('download', name);
	await expect(video).toHaveAttribute(
		'href',
		`/media/${id}/exports/${id}-16x9-clasico.mp4?download=1&name=${encodeURIComponent(name)}`
	);
	// The video's line says its shape, style and guide vocals.
	const row = panel
		.getByRole('listitem')
		.filter({ has: page.getByRole('link', { name: 'Descargar o vídeo' }) });
	await expect(row).toContainText('Horizontal');
	await expect(row).toContainText('Clásico');
	await expect(row).toContainText('sen voz');

	await panel.getByRole('button', { name: 'Borrar o vídeo' }).click();
	await panel.getByRole('button', { name: 'Si, borralo' }).click();
	await expect(panel.getByText('Aínda non hai vídeos desta canción.')).toBeVisible();

	// Another one with the guide vocals heard, as loud as chosen.
	await panel.getByLabel('Voz guía no vídeo').fill('0.5');
	await panel.getByRole('button', { name: 'Vertical, para redes' }).click();
	const sung = panel.getByRole('link', { name: 'Descargar o vídeo' });
	await expect(sung).toHaveAttribute('download', `${title} (karaoke vertical, voz 50%).mp4`, {
		timeout: 15_000
	});
	await expect(row).toContainText('Vertical');
	await expect(row).toContainText('Clásico');
	await expect(row).toContainText('voz 50 %');
});

test('a song that does not exist says so and leads back', async ({ page }) => {
	await page.goto('/cantar/non-existe');
	await expect(page.getByText('Esta canción non está na biblioteca.')).toBeVisible();
	await page.getByRole('link', { name: 'Ir ás cancións' }).click();
	await expect(page).toHaveURL(/\/$/);
});

// What a browser whose sound output is stuck does: the audio either never starts or starts with
// a clock that does not move. The song must not sit frozen at 0:00 without a word.
const STUCK = {
	'never starts': () => {
		// As in Chrome before a tap: suspended, and here resume() never gets anywhere.
		Object.defineProperty(BaseAudioContext.prototype, 'state', { get: () => 'suspended' });
		AudioContext.prototype.resume = () => new Promise(() => {});
	},
	'clock stands still': () => {
		Object.defineProperty(BaseAudioContext.prototype, 'currentTime', { get: () => 0 });
	}
};

for (const [name, stick] of Object.entries(STUCK)) {
	test(`a browser that plays no sound says so (${name})`, async ({ page }, testInfo) => {
		test.skip(testInfo.project.name !== 'laptop', 'the same on every screen');
		await page.addInitScript(stick);
		await page.goto('/cantar/demo-sintetico');
		const sing = page.getByRole('button', { name: 'Cantar' });
		await expect(sing).toBeEnabled({ timeout: 15_000 });
		await sing.click();
		await expect(page.getByRole('alert')).toContainText('O navegador non está a sacar son', {
			timeout: 10_000
		});
	});
}
