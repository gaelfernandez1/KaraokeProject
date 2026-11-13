import { expect, test } from '@playwright/test';

test('the board shows the songs and finds them without accents', async ({ page }) => {
	await page.goto('/');
	const posters = page.locator('.board .row');
	await expect(posters.first()).toBeVisible();
	const all = await posters.count();
	expect(all).toBeGreaterThan(1);

	await page.getByPlaceholder('Título ou artista').fill('vigo');
	await expect(page.getByRole('link', { name: /Mar de Vigo/ }).first()).toBeVisible();
	expect(await posters.count()).toBeLessThan(all);

	await page.getByPlaceholder('Título ou artista').fill('nada disto existe');
	await expect(page.getByText('Non hai nada con «nada disto existe».')).toBeVisible();
	await page.getByRole('button', { name: 'Quitar os filtros' }).click();
	await expect(posters).toHaveCount(all);
});

test('a row of the board opens its song in the player', async ({ page }) => {
	await page.goto('/');
	await page
		.getByRole('link', { name: /Mar de Vigo/ })
		.first()
		.click();
	await expect(page).toHaveURL(/\/cantar\/demo-sintetico$/);
	await expect(page.getByRole('heading', { name: /Mar de Vigo/ })).toBeVisible();
});

test('with a remote, the arrows go from the main menu down to the board and back', async ({
	page
}, testInfo) => {
	test.skip(testInfo.project.name !== 'tv', 'a remote drives the TV');
	await page.goto('/');
	await expect(page.locator('.board .row').first()).toBeVisible();
	await page.keyboard.press('ArrowDown'); // the menu's first item, Cantar, takes the focus
	await expect(page.locator('.menu :focus')).toHaveCount(1);
	// Down the menu, past the search and the filters, into the board.
	for (let i = 0; i < 12 && (await page.locator('.board :focus').count()) === 0; i++) {
		await page.keyboard.press('ArrowDown');
	}
	await expect(page.locator('.board :focus')).toHaveCount(1);
	// And back up to the menu.
	for (let i = 0; i < 12 && (await page.locator('.menu :focus').count()) === 0; i++) {
		await page.keyboard.press('ArrowUp');
	}
	await expect(page.locator('.menu :focus')).toHaveCount(1);
});

test('the main menu shows Galicia at night, and its motion can be stopped', async ({
	page
}, testInfo) => {
	await page.goto('/');
	await expect(page).toHaveTitle('Karaoke en Galego');
	await expect(page.getByRole('img', { name: /Galicia de noite/ })).toBeVisible();
	// Just the planet and the menu: no clock, moon or lighthouse readings around it.
	await expect(page.getByText(/Galicia esta noite|En Santiago|Faros da costa/)).toHaveCount(0);
	if (testInfo.project.name !== 'phone') {
		await expect(page.getByRole('navigation', { name: 'Menú principal' })).toBeVisible();
	}
	const stop = page.getByRole('button', { name: 'Parar o globo' });
	await stop.click();
	await expect(page.getByRole('button', { name: 'Mover o globo' })).toHaveAttribute(
		'aria-pressed',
		'true'
	);
	// Remembered for the next visit.
	await page.reload();
	await expect(page.getByRole('button', { name: 'Mover o globo' })).toBeVisible();
});

test('Cantar goes down to the board with the cursor in the search', async ({ page }, testInfo) => {
	test.skip(testInfo.project.name === 'phone', 'the phone has the board right below the globe');
	await page.goto('/');
	await page
		.getByRole('navigation', { name: 'Menú principal' })
		.getByRole('link', { name: /Cantar/ })
		.click();
	await expect(page.getByPlaceholder('Título ou artista')).toBeFocused();
});

test('"Todas" clears every filter, the saved one too', async ({ page }) => {
	await page.addInitScript(() => {
		const saved = { bytes: 1000, saved_at: '2026-11-13T10:00:00Z' };
		localStorage.setItem('foliada.saved', JSON.stringify([{ id: 'demo-sintetico', ...saved }]));
		// The planet held still: without a GPU its frames would crowd out the clicks.
		localStorage.setItem('noite.quieta', '1');
	});
	await page.goto('/');
	const rows = page.locator('.board .row');
	await expect(rows.first()).toBeVisible();
	const all = await rows.count();
	const chips = page.getByRole('group', { name: 'Idioma da canción' });
	const chip = (name: string) => chips.getByRole('button', { name, exact: true });

	await chip('Gardadas').click();
	await expect(rows).toHaveCount(1);
	// Only what filters shows as pressed: "Todas" is off while "Gardadas" is on.
	await expect(chip('Gardadas')).toHaveAttribute('aria-pressed', 'true');
	await expect(chip('Todas')).toHaveAttribute('aria-pressed', 'false');

	await chip('Galego').click();
	await expect(chip('Galego')).toHaveAttribute('aria-pressed', 'true');
	await expect(chip('Gardadas')).toHaveAttribute('aria-pressed', 'true');

	await chip('Todas').click();
	await expect(rows).toHaveCount(all);
	await expect(chip('Todas')).toHaveAttribute('aria-pressed', 'true');
	await expect(chip('Galego')).toHaveAttribute('aria-pressed', 'false');
	await expect(chip('Gardadas')).toHaveAttribute('aria-pressed', 'false');
});
