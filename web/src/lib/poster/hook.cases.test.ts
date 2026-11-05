import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { KaraokeDoc } from '#lib/contracts';
import { hookOf } from './hook';

// The same cases the server's Python port is tested with (karaoke_server.hook).
const root = new URL('../../../../', import.meta.url);
const cases = JSON.parse(readFileSync(new URL('fixtures/hook-cases.json', root), 'utf8')) as {
	cases: { name: string; lines: string[][]; expected: string | null }[];
	packages: { package: string; expected: string | null }[];
};

function docWith(lines: string[][]): KaraokeDoc {
	return {
		lines: lines.map(([text, role = 'lead'], i) => ({
			id: `l${i}`,
			start: i,
			end: i + 0.5,
			singer: null,
			role,
			words: text
				.split(' ')
				.map((w) => ({ text: w, start: i, end: i + 0.5, confidence: null, parts: [] }))
		}))
	} as unknown as KaraokeDoc;
}

describe('hookOf agrees with the server', () => {
	it.each(cases.cases)('$name', ({ lines, expected }) => {
		expect(hookOf(docWith(lines))).toBe(expected);
	});

	it.each(cases.packages)('$package', ({ package: id, expected }) => {
		const doc = JSON.parse(
			readFileSync(new URL(`fixtures/packages/${id}/karaoke.json`, root), 'utf8')
		) as KaraokeDoc;
		expect(hookOf(doc)).toBe(expected);
	});
});
