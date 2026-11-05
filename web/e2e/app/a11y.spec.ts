import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const PAGES = [
	'/',
	'/crear',
	'/axustes',
	'/cantar/demo-sintetico',
	'/editar/demo-sintetico',
	'/festa'
];

for (const path of PAGES) {
	test(`${path} has no serious accessibility problems`, async ({ page }) => {
		await page.goto(path);
		await page.waitForLoadState('networkidle');
		// The lyrics (another component, with its own tests) draw outlined text over pictures,
		// whose contrast axe cannot measure.
		const results = await new AxeBuilder({ page })
			.exclude('.lyrics')
			.withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
			.analyze();
		const serious = results.violations.filter(
			(v) => v.impact === 'serious' || v.impact === 'critical'
		);
		expect(
			serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)
		).toEqual([]);
	});
}
