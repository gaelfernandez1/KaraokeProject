import { describe, expect, it } from 'vitest';
import { loadFontOnce } from './fontload';

class FakeFace {
	static made = 0;
	constructor(
		readonly family: string,
		readonly source: string
	) {
		FakeFace.made++;
	}
	async load() {
		return this;
	}
}

describe('loadFontOnce', () => {
	it('loads and adds a theme font once, however many lyrics show it', async () => {
		const added: unknown[] = [];
		const fonts = { add: (face: unknown) => added.push(face) };
		const make = (family: string, source: string) => new FakeFace(family, source);
		const first = loadFontOnce('Nunito', '/n.woff2', make, fonts);
		const again = loadFontOnce('Nunito', '/n.woff2', make, fonts);
		expect(again).toBe(first);
		await first;
		expect(FakeFace.made).toBe(1);
		expect(added).toHaveLength(1);
	});
});
