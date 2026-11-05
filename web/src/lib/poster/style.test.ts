import { describe, expect, it } from 'vitest';
import { PALETTES, posterStyle } from './style';

describe('posterStyle', () => {
	it('gives a song the same poster every time', () => {
		expect(posterStyle('la-favorita')).toEqual(posterStyle('la-favorita'));
	});

	it('spreads songs over every palette and both layouts', () => {
		const styles = Array.from({ length: 1000 }, (_, i) => posterStyle(`song-${i}`));
		expect(new Set(styles.map((s) => s.palette)).size).toBe(PALETTES.length);
		expect(new Set(styles.map((s) => s.layout))).toEqual(new Set(['top', 'bottom']));
	});
});
