import { expect, test, type Page } from '@playwright/test';

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

test('a song that does not exist says so and leads back', async ({ page }) => {
	await page.goto('/cantar/non-existe');
	await expect(page.getByText('Esta canción non está na biblioteca.')).toBeVisible();
	await page.getByRole('link', { name: 'Ir ás cancións' }).click();
	await expect(page).toHaveURL(/\/$/);
});
