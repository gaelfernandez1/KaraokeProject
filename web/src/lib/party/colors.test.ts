import { describe, expect, it } from 'vitest';
import { singerColor } from './colors';
import { SINGER_COLORS } from './types';

describe('singerColor', () => {
	it('draws the colours the server hands out with the night palette, in order', () => {
		expect(SINGER_COLORS.map((color) => singerColor(color))).toEqual([
			'var(--cantante-1)',
			'var(--cantante-2)',
			'var(--cantante-3)',
			'var(--cantante-4)'
		]);
	});

	it('does not care about the case of the hex code', () => {
		expect(singerColor(SINGER_COLORS[1].toLowerCase())).toBe('var(--cantante-2)');
	});

	it('keeps a colour it does not know', () => {
		expect(singerColor('#123456')).toBe('#123456');
	});

	it('falls back when there is no guest', () => {
		expect(singerColor(undefined)).toBe('var(--texto-2)');
		expect(singerColor(null, 'var(--texto)')).toBe('var(--texto)');
	});
});
