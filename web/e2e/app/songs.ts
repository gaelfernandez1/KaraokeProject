import { expect, type Page } from '@playwright/test';

/**
 * Makes a song of its own through the create page (the stand-in turns any link into a copy of
 * the demo song in a few seconds) and returns its id. Tests that change a song use one each, so
 * the phone and laptop runs never write over each other's edits.
 */
export async function createSong(page: Page, title: string): Promise<string> {
	await page.goto('/crear');
	await page.getByLabel('Ligazón').fill('https://example.com/video');
	await page.getByLabel(/^Título/).fill(title);
	await page.getByRole('button', { name: 'Crear karaoke' }).last().click();
	const card = page.locator('.job').filter({ hasText: title });
	await card.getByRole('link', { name: 'Cantar agora' }).click({ timeout: 20_000 });
	await expect(page).toHaveURL(/\/cantar\/[^/?]+/);
	return decodeURIComponent(new URL(page.url()).pathname.split('/')[2]);
}
