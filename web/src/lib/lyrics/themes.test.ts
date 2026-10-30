import { describe, expect, test } from 'vitest';
import { THEMES, fontFaceFor, metricsFor } from './themes';

describe('bundled themes', () => {
	test('the three themes, by id', () => {
		expect(Object.keys(THEMES).sort()).toEqual(['clasico', 'contraste', 'moderno']);
		expect(THEMES.clasico.font.family).toBe('Nunito Black');
	});

	test('each theme measures with its own font', () => {
		expect(metricsFor(THEMES.clasico).upem).toBe(1000);
		expect(metricsFor(THEMES.moderno).upem).toBe(2048);
		expect(metricsFor(THEMES.clasico).width('ñ', 100)).toBeGreaterThan(0);
	});

	test('a font face for the browser', () => {
		const face = fontFaceFor(THEMES.contraste);

		expect(face?.family).toBe('Atkinson Hyperlegible Next ExtraBold');
		expect(face?.url).toMatch(/AtkinsonHyperlegibleNext-ExtraBold\.woff2/);
	});

	test('a theme without a bundled font measures with the default one', () => {
		const custom = { ...THEMES.clasico, font: { family: 'Noto Sans', weight: 800, file: null } };

		expect(fontFaceFor(custom)).toBeNull();
		expect(metricsFor(custom)).toBe(metricsFor(THEMES.clasico));
	});
});
