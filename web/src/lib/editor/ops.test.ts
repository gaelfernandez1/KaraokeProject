import { describe, expect, it } from 'vitest';
import type { KaraokeDoc } from '#lib/contracts';
import { normalizeDoc } from '#lib/lyrics';
import demoJson from '../../../../fixtures/packages/demo-sintetico/karaoke.json';
import esenciaJson from '../../../../fixtures/packages/nandomalo-esencia/karaoke.json';
import {
	MIN_WORD,
	checkDoc,
	moveWordEdge,
	retimeLine,
	setWordText,
	shiftLine,
	type WordRef
} from './ops';

/** Any write to the input throws, so a test fails as soon as an op mutates it. */
function deepFreeze<T>(value: T): T {
	if (value && typeof value === 'object' && !Object.isFrozen(value)) {
		Object.freeze(value);
		for (const child of Object.values(value)) deepFreeze(child);
	}
	return value;
}

const load = (json: unknown) => deepFreeze(normalizeDoc(json as KaraokeDoc));
const DEMO = load(demoJson);
const ESENCIA = load(esenciaJson);

/** Seeded so a failure can be replayed (mulberry32). */
function prng(seed: number): () => number {
	return () => {
		seed = (seed + 0x6d2b79f5) | 0;
		let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
		t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

const word = (doc: KaraokeDoc, ref: WordRef) => doc.lines[ref.line].words[ref.word];
const MAR: WordRef = { line: 0, word: 1 };
const OLA: WordRef = { line: 0, word: 0 };
const VIGO: WordRef = { line: 0, word: 3 };

describe('checkDoc', () => {
	it('accepts the example documents', () => {
		expect(checkDoc(DEMO)).toEqual([]);
		expect(checkDoc(ESENCIA)).toEqual([]);
	});

	it('describes every broken rule', () => {
		const broken = structuredClone<KaraokeDoc>(DEMO);
		const [l1, l2, l3, l4] = broken.lines;
		l1.words[1].end = 4.5; // mar: 4.9 → 4.5
		l1.words[3].parts[0].text = 'Ve'; // Vigo, spelled "Vego,"
		l2.words[1].start = 7.0; // before its line
		l3.start = 7.0; // before line 2
		l3.words[0].start = 7.0;
		l4.end = 33;
		l4.words[2].end = 33; // after the song
		l4.words[2].parts[1].end = 33;
		l4.words[0].parts[1].start = 22.9; // before its word and its previous part

		const problems = checkDoc(broken);

		const has = (pattern: RegExp) => expect(problems.some((p) => pattern.test(p))).toBe(true);
		has(/^Line 1, word 2 \("mar"\).*ends.*before it starts/);
		has(/^Line 1, word 4 \("Vigo,"\).*spell "Vego,"/);
		has(/^Line 2, word 2 \("a"\).*outside its line/);
		has(/^Line 2, word 2 \("a"\).*before the previous word/);
		has(/^Line 3 .*before the previous line/);
		has(/^Line 4 .*after the song/);
		has(/^Line 4, word 3 \("beira."\).*after the song/);
		has(/^Line 4, word 1 \("volvo"\), part 2 \("vo"\).*outside its word/);
		has(/^Line 4, word 1 \("volvo"\), part 2 \("vo"\).*before the previous part/);
	});

	it('tolerates a millisecond, like the contract', () => {
		const doc = structuredClone<KaraokeDoc>(DEMO);
		doc.lines[1].words[0].start = 7.4995; // 0.5 ms before its line
		doc.lines[3].end = 32.0009;
		doc.lines[3].words[2].end = 32.0009;
		doc.lines[3].words[2].parts[1].end = 32.0009;
		expect(checkDoc(doc)).toEqual([]);
	});

	it('flags lines without words, unknown singers and repeated ids', () => {
		const doc = structuredClone<KaraokeDoc>(DEMO);
		doc.lines[1].id = 'l1';
		doc.lines[2].singer = 's9';
		doc.lines[3].words = [];
		const problems = checkDoc(doc);
		expect(problems).toHaveLength(3);
		expect(problems.join('\n')).toMatch(/Line 2 .*"l1"/);
		expect(problems.join('\n')).toMatch(/Line 3 .*"s9"/);
		expect(problems.join('\n')).toMatch(/Line 4 .*no words/);
	});
});

describe('setWordText', () => {
	it('refuses an empty text', () => {
		expect(setWordText(DEMO, MAR, '')).toBe(DEMO);
		expect(setWordText(DEMO, MAR, '   ')).toBe(DEMO);
	});

	it('returns the same document when nothing changes', () => {
		expect(setWordText(DEMO, MAR, ' mar ')).toBe(DEMO);
		expect(setWordText(DEMO, { line: 9, word: 0 }, 'x')).toBe(DEMO);
	});

	it('trims, keeps the times and marks the document as edited', () => {
		const doc = setWordText(DEMO, MAR, '  mal  ');
		expect(word(doc, MAR)).toEqual({ ...word(DEMO, MAR), text: 'mal' });
		expect(doc.edited).toBe(true);
		expect(DEMO.edited).toBe(false);
		expect(doc.lines[1]).toBe(DEMO.lines[1]);
	});

	it('drops the syllables of a different word', () => {
		const doc = setWordText(DEMO, OLA, 'Hola,');
		expect(word(doc, OLA).text).toBe('Hola,');
		expect(word(doc, OLA).parts).toEqual([]);
		expect(checkDoc(doc)).toEqual([]);
	});

	it('keeps accents typed apart and emoji whole when it re-splits', () => {
		// «Vígo» with the accent as a separate mark (as some keyboards and sites send it) is
		// stored composed, which looks the same, and the accent stays on its letter.
		const decomposed = setWordText(DEMO, VIGO, 'Vígo,');
		expect(word(decomposed, VIGO).text).toBe('Vígo,');
		expect(word(decomposed, VIGO).parts.map((p) => p.text)).toEqual(['Ví', 'go,']);
		const emoji = setWordText(DEMO, VIGO, 'Vigo\u{1F44D}\u{1F3FD}');
		expect(word(emoji, VIGO).parts.map((p) => p.text)).toEqual(['Vi', 'go\u{1F44D}\u{1F3FD}']);
		expect(checkDoc(decomposed)).toEqual([]);
		expect(checkDoc(emoji)).toEqual([]);
	});

	it('re-splits the same letters over the syllables', () => {
		const doc = setWordText(DEMO, OLA, 'OLA,');
		expect(word(doc, OLA).parts).toEqual([
			{ text: 'O', start: 4.0, end: 4.3 },
			{ text: 'LA,', start: 4.3, end: 4.8 }
		]);
		const exclaimed = setWordText(DEMO, OLA, '¡Ola!');
		expect(word(exclaimed, OLA).parts.map((p) => p.text)).toEqual(['¡O', 'la!']);
		expect(checkDoc(exclaimed)).toEqual([]);
	});

	it('keeps the syllables when only an accent changes', () => {
		const ref = { line: 1, word: 0 };
		const doc = setWordText(DEMO, ref, 'cantame');
		expect(word(doc, ref).parts.map((p) => p.text)).toEqual(['can', 'ta', 'me']);
		expect(word(doc, ref).parts.map((p) => p.start)).toEqual([7.5, 7.9, 8.3]);
	});
});

describe('moveWordEdge', () => {
	it('moves one edge of a word', () => {
		const doc = moveWordEdge(DEMO, MAR, 'start', -0.05);
		expect(word(doc, MAR)).toMatchObject({ start: 4.85, end: 5.6 });
		expect(doc.edited).toBe(true);
	});

	it('does not cross the neighbour words', () => {
		expect(word(moveWordEdge(DEMO, MAR, 'start', -1), MAR).start).toBe(4.8);
		expect(word(moveWordEdge(DEMO, MAR, 'end', 1), MAR).end).toBe(5.7);
	});

	it('keeps every word at least MIN_WORD long', () => {
		const shrunk = moveWordEdge(DEMO, MAR, 'start', 5);
		expect(word(shrunk, MAR).end - word(shrunk, MAR).start).toBeCloseTo(MIN_WORD, 9);
		const ola = word(moveWordEdge(DEMO, OLA, 'end', -5), OLA);
		expect(ola.end - ola.start).toBeCloseTo(MIN_WORD, 9);
		expect(ola.parts[1].end).toBe(ola.end);
	});

	it('stays inside the song and the line order', () => {
		const last = { line: 3, word: 2 };
		expect(word(moveWordEdge(DEMO, last, 'end', 10), last).end).toBe(32);
		const first = moveWordEdge(DEMO, OLA, 'start', -10);
		expect(first.lines[0].start).toBe(0);
		// The first word of line 2 cannot start before line 1 does.
		const second = moveWordEdge(DEMO, { line: 1, word: 0 }, 'start', -10);
		expect(second.lines[1].start).toBe(4);
		expect(checkDoc(second)).toEqual([]);
	});

	it('stretches the syllables and the line with the word', () => {
		const doc = moveWordEdge(DEMO, VIGO, 'end', -0.45);
		expect(word(doc, VIGO).parts).toEqual([
			{ text: 'Vi', start: 6.1, end: 6.3 },
			{ text: 'go,', start: 6.3, end: 6.55 }
		]);
		expect(doc.lines[0].end).toBe(6.55);
	});

	it('returns the same document when the edge cannot move', () => {
		expect(moveWordEdge(DEMO, MAR, 'start', 0)).toBe(DEMO);
		const doc = moveWordEdge(DEMO, { line: 3, word: 2 }, 'end', 10);
		expect(moveWordEdge(doc, { line: 3, word: 2 }, 'end', 1)).toBe(doc);
		expect(moveWordEdge(DEMO, { line: 0, word: 7 }, 'end', 1)).toBe(DEMO);
	});
});

describe('shiftLine', () => {
	it('moves the words and syllables of a line', () => {
		const doc = shiftLine(DEMO, 1, 0.5);
		const line = doc.lines[1];
		expect([line.start, line.end]).toEqual([8, 12]);
		expect(line.words[0].parts.map((p) => [p.start, p.end])).toEqual([
			[8, 8.4],
			[8.4, 8.8],
			[8.8, 9.2]
		]);
		expect(line.words[3]).toMatchObject({ start: 10.5, end: 12 });
		expect(doc.edited).toBe(true);
	});

	it('stays inside the song', () => {
		expect(shiftLine(DEMO, 0, -10).lines[0].start).toBe(0);
		expect(shiftLine(DEMO, 3, 10).lines[3]).toMatchObject({ start: 28, end: 32 });
	});

	it('keeps the line starts in order', () => {
		expect(shiftLine(DEMO, 1, -10).lines[1].start).toBe(4);
		expect(shiftLine(DEMO, 2, 20).lines[2].start).toBe(23);
	});

	it('returns the same document when it cannot move', () => {
		expect(shiftLine(DEMO, 1, 0)).toBe(DEMO);
		const start = shiftLine(DEMO, 0, -10);
		expect(shiftLine(start, 0, -1)).toBe(start);
		expect(shiftLine(DEMO, 7, 1)).toBe(DEMO);
	});
});

describe('retimeLine', () => {
	const taps = [7.6, 8.5, 9.0, 9.8];

	it('sets every start from the taps', () => {
		const doc = retimeLine(DEMO, 1, taps);
		const words = doc.lines[1].words;
		expect(words.map((w) => w.start)).toEqual(taps);
		// Each word ends just before the next; the last keeps its length (1.5 s).
		expect(words.map((w) => w.end)).toEqual([8.48, 8.98, 9.78, 11.3]);
		expect(doc.lines[1]).toMatchObject({ start: 7.6, end: 11.3 });
		expect(doc.edited).toBe(true);
		expect(checkDoc(doc)).toEqual([]);
	});

	it('stretches the syllables', () => {
		const parts = retimeLine(DEMO, 1, taps).lines[1].words[0].parts;
		expect(parts[0].start).toBe(7.6);
		expect(parts[2].end).toBe(8.48);
		expect(parts[1].start).toBeCloseTo(7.6 + 0.88 / 3, 6);
	});

	it('sorts taps out of order', () => {
		expect(retimeLine(DEMO, 1, [9.0, 7.6, 9.8, 8.5])).toEqual(retimeLine(DEMO, 1, taps));
	});

	it('retimes only the tapped words', () => {
		const words = retimeLine(DEMO, 1, [8.0, 8.9]).lines[1].words;
		expect(words.map((w) => [w.start, w.end])).toEqual([
			[8.0, 8.88],
			[8.9, 9.2], // keeps 0.3 s, up to the next word
			[9.2, 9.9],
			[10.0, 11.5]
		]);
	});

	it('pushes the untapped words later to keep them in order', () => {
		const old = DEMO.lines[1].words;
		const doc = retimeLine(DEMO, 1, [9.5]);
		const words = doc.lines[1].words;
		// The tapped word keeps its length; each later word keeps its own and follows on.
		expect(words[0].start).toBe(9.5);
		expect(words[0].end - words[0].start).toBeCloseTo(old[0].end - old[0].start, 6);
		for (let i = 1; i < words.length; i++) {
			expect(words[i].start).toBeGreaterThanOrEqual(words[i - 1].end - 1e-9);
			expect(words[i].end - words[i].start).toBeCloseTo(old[i].end - old[i].start, 6);
		}
		expect(checkDoc(doc)).toEqual([]);
	});

	it('stays inside the song and the line order', () => {
		expect(retimeLine(DEMO, 1, [1, 2]).lines[1].start).toBe(4);
		const end = retimeLine(DEMO, 3, [31.99]);
		expect(end.lines[3].end).toBeLessThanOrEqual(32);
		expect(checkDoc(end)).toEqual([]);
	});

	it('returns the same document without taps', () => {
		expect(retimeLine(DEMO, 1, [])).toBe(DEMO);
		expect(retimeLine(DEMO, 1, [Number.NaN])).toBe(DEMO);
		expect(retimeLine(DEMO, 9, [1])).toBe(DEMO);
	});
});

describe.each([
	['the demo', DEMO, 7],
	['a real song', ESENCIA, 11]
])('300 random edits on %s', (_, start, seed) => {
	it('keep the document valid', () => {
		const random = prng(seed);
		const pick = (n: number) => Math.floor(random() * n);
		let doc = start;
		let changed = 0;
		for (let step = 0; step < 300; step++) {
			const before = doc;
			const index = pick(doc.lines.length);
			const line = doc.lines[index];
			const ref = { line: index, word: pick(line.words.length) };
			const delta = (random() - 0.5) * 8;
			const op = pick(5);
			if (op === 0) doc = moveWordEdge(doc, ref, 'start', delta);
			else if (op === 1) doc = moveWordEdge(doc, ref, 'end', delta);
			else if (op === 2) doc = shiftLine(doc, index, delta);
			else if (op === 3) {
				const count = 1 + pick(line.words.length);
				const taps = Array.from({ length: count }, () => line.start + (random() - 0.3) * 5);
				doc = retimeLine(doc, index, taps);
			} else {
				const text = word(doc, ref).text;
				doc = setWordText(doc, ref, random() < 0.5 ? text.toUpperCase() : `${text}x`);
			}
			deepFreeze(doc);
			if (doc !== before) changed++;

			expect(checkDoc(doc), `step ${step}, op ${op}`).toEqual([]);
			for (const l of doc.lines) {
				expect(l.start).toBe(l.words[0].start);
				expect(l.end).toBe(l.words[l.words.length - 1].end);
				l.words.forEach((w, i) => {
					expect(w.end - w.start).toBeGreaterThanOrEqual(MIN_WORD - 1e-6);
					if (i > 0) expect(w.start).toBeGreaterThanOrEqual(l.words[i - 1].end);
				});
			}
		}
		expect(changed).toBeGreaterThan(200);
		expect(doc.edited).toBe(true);
	});
});

describe('retimeLine with fewer taps than words', () => {
	it('keeps the last tapped word as long as it was and moves the next one after it', () => {
		const word = (text: string, start: number, end: number) => ({
			text,
			start,
			end,
			confidence: null,
			parts: []
		});
		const doc = {
			...DEMO,
			duration: 60,
			lines: [
				{
					id: 'l1',
					start: 10,
					end: 12,
					singer: null,
					role: 'lead' as const,
					words: [word('Ai', 10, 11), word('lelo', 11, 12)]
				}
			]
		} as KaraokeDoc;
		const next = retimeLine(doc, 0, [11.5]);
		const [a, b] = next.lines[0].words;
		expect([a.start, a.end]).toEqual([11.5, 12.5]);
		expect([b.start, b.end]).toEqual([12.5, 13.5]);
		expect(checkDoc(next)).toEqual([]);
	});
});
