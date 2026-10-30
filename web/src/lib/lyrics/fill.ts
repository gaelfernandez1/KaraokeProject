import type { Row } from './layout';

/** Between t0 and t1 the fill edge moves from x0 to x1 (px from the row's left edge). */
export interface FillSegment {
	t0: number;
	t1: number;
	x0: number;
	x1: number;
}

/** Where a part of the row is drawn, measured in the DOM (px from the row's left edge). */
export interface PartBox {
	x0: number;
	x1: number;
}

/**
 * The fill of a row as segments. `wipe`: each syllable (or word without syllables) fills across
 * its width while it is sung, like ASS `\kf`. `word`: each word fills at once when it starts, like
 * `\k`. `boxes` has one box per part, in row order.
 */
export function fillSegments(row: Row, boxes: PartBox[], mode: 'wipe' | 'word'): FillSegment[] {
	const parts = row.words.reduce((count, word) => count + word.parts.length, 0);
	if (boxes.length !== parts)
		throw new Error(`row ${row.line_id}: ${boxes.length} boxes for ${parts} parts`);
	const segments: FillSegment[] = [];
	let next = 0;
	for (const word of row.words) {
		const first = boxes[next];
		const last = boxes[next + word.parts.length - 1];
		if (mode === 'word') {
			const t = word.parts[0].start;
			segments.push({ t0: t, t1: t, x0: first.x0, x1: last.x1 });
		} else {
			word.parts.forEach((part, i) => {
				const box = boxes[next + i];
				segments.push({ t0: part.start, t1: part.end, x0: box.x0, x1: box.x1 });
			});
		}
		next += word.parts.length;
	}
	return segments;
}

/** The fill edge at time `t`: 0 before anything is sung, then always moving right. */
export function fillX(segments: FillSegment[], t: number): number {
	let x = 0;
	for (const s of segments) {
		if (t >= s.t1) x = s.x1;
		else if (t > s.t0) return s.x0 + ((s.x1 - s.x0) * (t - s.t0)) / (s.t1 - s.t0);
		else return x;
	}
	return x;
}
