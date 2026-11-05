import type { KaraokeDoc } from '#lib/contracts';

/** Jumping to a line lands this long before it, to hear it coming. */
export const LINE_LEAD = 1;
/** Going back within this long of a line's start goes to the line before. */
const GRACE = 0.75;

/** The stretches of the song where someone sings, as fractions of its length. */
export function lineSegments(doc: KaraokeDoc): { from: number; to: number }[] {
	if (doc.duration <= 0) return [];
	const spans = doc.lines
		.map((line) => [line.start, line.end] as const)
		.sort((a, b) => a[0] - b[0]);
	const merged: [number, number][] = [];
	for (const [start, end] of spans) {
		const last = merged.at(-1);
		if (last && start <= last[1]) last[1] = Math.max(last[1], end);
		else merged.push([start, end]);
	}
	const round = (x: number) => Math.round((x / doc.duration) * 1e4) / 1e4;
	return merged.map(([from, to]) => ({ from: round(from), to: round(to) }));
}

/** Where to jump for the next (1) or previous (-1) lead line from `time`; null if none. */
export function lineSeek(doc: KaraokeDoc, time: number, direction: 1 | -1): number | null {
	const starts = doc.lines
		.filter((line) => line.role !== 'backing')
		.map((line) => Math.max(0, line.start - LINE_LEAD))
		.sort((a, b) => a - b);
	if (direction === 1) return starts.find((start) => start > time + 0.01) ?? null;
	return starts.findLast((start) => start <= time - GRACE) ?? 0;
}
