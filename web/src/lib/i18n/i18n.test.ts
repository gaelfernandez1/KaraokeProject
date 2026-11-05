import { describe, expect, it } from 'vitest';
import { en } from './en';
import { es } from './es';
import { gl } from './gl';
import { detectLocale } from './index.svelte';
import { plural } from './plural';

/** Every key path of a dictionary with the kind of its value (text or function). */
function shape(value: unknown, path = ''): string[] {
	if (typeof value === 'object' && value !== null) {
		return Object.entries(value).flatMap(([key, inner]) => shape(inner, `${path}.${key}`));
	}
	return [`${path}:${typeof value}`];
}

describe('detectLocale', () => {
	it('prefers a stored choice', () => {
		expect(detectLocale('en', ['gl'])).toBe('en');
		expect(detectLocale('es', ['gl'])).toBe('es');
	});

	it('is Galician for Galician and every other Iberian browser', () => {
		expect(detectLocale(null, ['gl-ES', 'es'])).toBe('gl');
		expect(detectLocale(null, ['es-ES'])).toBe('gl');
		expect(detectLocale(null, ['pt-PT', 'en'])).toBe('gl');
		expect(detectLocale(null, ['en-GB', 'gl'])).toBe('gl');
	});

	it('is English for browsers with no Iberian language that speak English', () => {
		expect(detectLocale(null, ['en-US'])).toBe('en');
		expect(detectLocale(null, ['de-DE', 'en'])).toBe('en');
	});

	it('falls back to Galician', () => {
		expect(detectLocale(null, ['fr'])).toBe('gl');
		expect(detectLocale('xx', [])).toBe('gl');
	});
});

describe('plural', () => {
	it('picks the form and formats the number for the locale', () => {
		expect(plural(1, 'gl', { one: '# canción', other: '# cancións' })).toBe('1 canción');
		expect(plural(3, 'gl', { one: '# canción', other: '# cancións' })).toBe('3 cancións');
		const big = new Intl.NumberFormat('es').format(1200);
		expect(plural(1200, 'es', { one: '# canción', other: '# canciones' })).toBe(`${big} canciones`);
	});
});

describe('dictionaries', () => {
	it('have exactly the keys of the Galician one, with the same kinds of value', () => {
		expect(shape(es)).toEqual(shape(gl));
		expect(shape(en)).toEqual(shape(gl));
	});

	it('have no empty texts', () => {
		for (const dict of [gl, es, en]) {
			for (const entry of shape(dict)) expect(entry).not.toMatch(/:undefined$/);
			const texts = JSON.stringify(dict);
			expect(texts).not.toContain('""');
		}
	});
});
