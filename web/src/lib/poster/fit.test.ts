import { describe, expect, it } from 'vitest';
import { fitTitle, keyWord, splitTitle, textWidth } from './fit';

const OPTIONS = { maxWidth: 86, maxHeight: 60, lineHeight: 0.9, maxSize: 40, maxLines: 3 };

describe('textWidth', () => {
	it('adds up the advance widths in em', () => {
		expect(textWidth('II')).toBeCloseTo(2 * textWidth('I'));
		expect(textWidth('M')).toBeGreaterThan(textWidth('I'));
		expect(textWidth('Á')).toBeGreaterThan(0);
	});
});

describe('fitTitle', () => {
	it('sets a short title in capitals on as many lines as make it biggest', () => {
		const fit = fitTitle('La Favorita', OPTIONS);
		expect(fit.lines).toEqual(['LA', 'FAVORITA']);
		expect(fit.size).toBeLessThanOrEqual(40);
		expect(fit.size * textWidth('FAVORITA')).toBeLessThanOrEqual(86.001);
	});

	it('keeps long titles inside the box on at most the allowed lines', () => {
		const fit = fitTitle('Ó pé da Ponte Vella de Ourense (versión acústica en directo)', OPTIONS);
		expect(fit.lines.length).toBeLessThanOrEqual(3);
		expect(fit.size).toBeLessThan(40);
		for (const line of fit.lines) expect(fit.size * textWidth(line)).toBeLessThanOrEqual(86.001);
		expect(fit.lines.length * fit.size * 0.9).toBeLessThanOrEqual(60.001);
		expect(fit.lines.join(' ')).toBe(
			'Ó PÉ DA PONTE VELLA DE OURENSE (VERSIÓN ACÚSTICA EN DIRECTO)'
		);
	});

	it('shrinks a single long word instead of breaking it', () => {
		const fit = fitTitle('Supercalifragilisticoespialidoso', OPTIONS);
		expect(fit.lines).toHaveLength(1);
		expect(fit.size).toBeLessThan(40);
		expect(fit.size * textWidth(fit.lines[0])).toBeLessThanOrEqual(86.001);
	});

	it('never goes over the largest size', () => {
		expect(fitTitle('Ai', OPTIONS).size).toBe(40);
	});

	it('copes with an empty title', () => {
		expect(fitTitle('   ', OPTIONS)).toEqual({ lines: [], size: 40 });
	});
});

describe('splitTitle', () => {
	it('sets the version in brackets or after a dash apart from the title', () => {
		expect(splitTitle('Mar de Vigo (demo sintética)')).toEqual({
			main: 'Mar de Vigo',
			tag: 'demo sintética'
		});
		expect(splitTitle('Pelijroso (recorte, letra de LRCLIB)')).toEqual({
			main: 'Pelijroso',
			tag: 'recorte, letra de LRCLIB'
		});
		expect(splitTitle('Feel [Stripped]')).toEqual({ main: 'Feel', tag: 'Stripped' });
		expect(splitTitle('Alalá - en directo')).toEqual({ main: 'Alalá', tag: 'en directo' });
	});

	it('leaves other titles whole', () => {
		expect(splitTitle('La Favorita')).toEqual({ main: 'La Favorita', tag: null });
		expect(splitTitle('(Intro)')).toEqual({ main: '(Intro)', tag: null });
		expect(splitTitle('Ó pé da Ponte Vella')).toEqual({ main: 'Ó pé da Ponte Vella', tag: null });
	});
});

describe('keyWord', () => {
	it('skips articles and short words for the first word with weight', () => {
		expect(keyWord('La Favorita')).toBe('Favorita');
		expect(keyWord('Ó pé da Ponte Vella')).toBe('Ponte');
		expect(keyWord('Mar de Vigo (demo sintética)')).toBe('Mar');
		expect(keyWord('The Rapants')).toBe('Rapants');
		expect(keyWord('«Ai»')).toBe('Ai');
	});
});
