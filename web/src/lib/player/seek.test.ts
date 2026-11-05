import { describe, expect, it } from 'vitest';
import type { KaraokeDoc, Line } from '#lib/contracts';
import { lineSeek, lineSegments } from './seek';

const line = (id: string, start: number, end: number, role: 'lead' | 'backing' = 'lead'): Line => ({
	id,
	start,
	end,
	singer: null,
	role,
	words: [{ text: id, start, end, confidence: null, parts: [] }]
});

const doc = (lines: Line[], duration = 100) => ({ duration, lines }) as unknown as KaraokeDoc;

describe('lineSegments', () => {
	it('gives the sung stretches as fractions of the song, merging overlaps', () => {
		const segments = lineSegments(
			doc([line('a', 10, 20), line('b', 18, 30, 'backing'), line('c', 50, 60)])
		);
		expect(segments).toEqual([
			{ from: 0.1, to: 0.3 },
			{ from: 0.5, to: 0.6 }
		]);
	});

	it('copes with no lines or no length', () => {
		expect(lineSegments(doc([]))).toEqual([]);
		expect(lineSegments(doc([line('a', 1, 2)], 0))).toEqual([]);
	});
});

describe('lineSeek', () => {
	const lines = doc([line('a', 10, 15), line('b', 20, 25), line('c', 30, 35)]);
	const LEAD = 1;

	it('goes to the start of the next lead line, a little before it', () => {
		expect(lineSeek(lines, 12, 1)).toBe(20 - LEAD);
		expect(lineSeek(lines, 0, 1)).toBe(10 - LEAD);
		expect(lineSeek(lines, 33, 1)).toBeNull();
	});

	it('goes back to the start of this line, or the one before when just started', () => {
		expect(lineSeek(lines, 23, -1)).toBe(20 - LEAD);
		expect(lineSeek(lines, 19.5, -1)).toBe(10 - LEAD);
		expect(lineSeek(lines, 5, -1)).toBe(0);
	});
});
