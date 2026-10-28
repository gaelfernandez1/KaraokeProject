import { describe, expect, it } from 'vitest';
import demo from '../../../../fixtures/packages/demo-sintetico/karaoke.json';
import type { KaraokeDoc, PlaybackClock } from '#lib/contracts';

// JSON imports widen string literals, so the fixture is cast; the runtime checks below
// confirm the shape the generated types describe.
const doc = demo as KaraokeDoc;

describe('karaoke document contract', () => {
	it('reads the demo fixture through the generated types', () => {
		expect(doc.language).toBe('gl');
		expect(doc.lines.length).toBeGreaterThan(0);
	});

	it('has parts that spell out their word', () => {
		const words = doc.lines.flatMap((line) => line.words).filter((w) => w.parts.length > 0);

		expect(words.length).toBeGreaterThan(0);
		for (const word of words) {
			expect(word.parts.map((part) => part.text).join('')).toBe(word.text);
		}
	});

	it('lets any object with now() act as the playback clock', () => {
		const clock: PlaybackClock = { now: () => 4.2 };

		expect(clock.now()).toBe(4.2);
	});
});
