import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, test } from 'vitest';
import type { KaraokeDoc, Theme } from '#lib/contracts';
import { buildLayout, normalizeDoc, wrap } from './layout';
import { FontMetrics, type MetricsData } from './metrics';

const ROOT = resolve(fileURLToPath(new URL('.', import.meta.url)), '../../../..');
const CASES = resolve(ROOT, 'fixtures/lyrics-layout');
const THEMES = resolve(ROOT, 'packages/engine/src/karaoke_engine/subtitles/themes');

const readJson = <T>(path: string): T => JSON.parse(readFileSync(path, 'utf-8')) as T;

const MONO = new FontMetrics({
	upem: 1000,
	ascender: 900,
	descender: -300,
	win_ascent: 1000,
	win_descent: 250,
	default_advance: 500,
	average_lowercase: 500,
	advances: {}
});

/** Same numbers within 1e-6, same everything else. */
function expectClose(actual: unknown, expected: unknown, path = '$'): void {
	if (typeof expected === 'number') {
		expect(typeof actual, path).toBe('number');
		expect(Math.abs((actual as number) - expected), path).toBeLessThanOrEqual(1e-6);
	} else if (Array.isArray(expected)) {
		expect(Array.isArray(actual), path).toBe(true);
		expect((actual as unknown[]).length, path).toBe(expected.length);
		expected.forEach((item, i) => expectClose((actual as unknown[])[i], item, `${path}[${i}]`));
	} else if (expected !== null && typeof expected === 'object') {
		expect(Object.keys(actual as object).sort(), path).toEqual(Object.keys(expected).sort());
		for (const [key, value] of Object.entries(expected)) {
			expectClose((actual as Record<string, unknown>)[key], value, `${path}.${key}`);
		}
	} else {
		expect(actual, path).toBe(expected);
	}
}

interface Case {
	doc: KaraokeDoc | string;
	theme: string;
	width: number;
	height: number;
	layout: unknown;
}

describe('layout matches the Python reference', () => {
	const files = readdirSync(CASES).filter((name) => name.endsWith('.json'));

	test('there are shared cases', () => {
		expect(files.length).toBeGreaterThanOrEqual(10);
	});

	test.each(files)('%s', (file) => {
		const c = readJson<Case>(resolve(CASES, file));
		const doc = typeof c.doc === 'string' ? readJson<KaraokeDoc>(resolve(ROOT, c.doc)) : c.doc;
		const theme = readJson<Theme>(resolve(THEMES, `${c.theme}.json`));
		const stem = (theme.font.file ?? '').replace(/\.ttf$/, '');
		const metrics = new FontMetrics(
			readJson<MetricsData>(resolve(THEMES, 'fonts', `${stem}.metrics.json`))
		);

		expectClose(buildLayout(normalizeDoc(doc), theme, c.width, c.height, metrics), c.layout);
	});
});

describe('wrap', () => {
	test('one row when it fits', () => {
		expect(wrap(['Ola', 'que', 'tal'], 75, 900, 2, MONO)).toEqual([[[0, 1, 2]], 1]);
	});

	test('shrinks when two rows do not fit', () => {
		const [rows, scale] = wrap(['a'.repeat(18), 'b'.repeat(18), 'c'.repeat(18)], 75, 900, 2, MONO);
		expect(rows).toEqual([[0], [1, 2]]);
		expect(scale).toBeCloseTo(900 / (37 * 37.5));
	});

	test('takes more rows rather than cutting a line too long for two', () => {
		expect(wrap(['a'.repeat(20), 'b'.repeat(20), 'c'.repeat(20)], 75, 900, 2, MONO)).toEqual([
			[[0], [1], [2]],
			1
		]);
		const [rows] = wrap(
			['a', 'b', 'c', 'd'].map((c) => c.repeat(20)),
			75,
			900,
			2,
			MONO
		);
		expect(rows).toEqual([[0], [1], [2], [3]]);
	});

	test('always fits the screen, shrinking a huge word further', () => {
		const [rows, scale] = wrap(['a'.repeat(60)], 75, 900, 2, MONO);
		expect(rows).toEqual([[0]]);
		expect(60 * 37.5 * scale).toBeCloseTo(900);
	});
});

describe('normalizeDoc', () => {
	test('fills in what 1.0.0 documents leave out', () => {
		const doc = {
			lines: [{ id: 'l1', start: 0, end: 1, words: [{ text: 'a', start: 0, end: 1 }] }]
		} as unknown as KaraokeDoc;

		const normal = normalizeDoc(doc);

		expect(normal.lines[0].role).toBe('lead');
		expect(normal.lines[0].singer).toBeNull();
		expect(normal.lines[0].words[0].parts).toEqual([]);
		expect(normal.singers).toEqual([]);
	});
});
