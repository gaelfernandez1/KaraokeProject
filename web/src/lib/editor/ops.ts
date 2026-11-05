import type { KaraokeDoc, Line, Part, Word } from '#lib/contracts';

/*
 * The edits someone makes by hand to fix a song without reprocessing it. Each one returns a new
 * document that shares every untouched line (cheap to keep for undo), or the same object when it
 * changes nothing. Times are clamped instead of refused, so dragging past a limit stops at it,
 * and every edited line spans exactly its words. A rule the document already breaks only stops a
 * time from getting worse, so a slightly off document from the engine stays editable.
 */

/** Shortest a word can get by dragging or tapping, in seconds. */
export const MIN_WORD = 0.02;
/** Silence left between words timed by tapping, so each one is seen to end. */
const TAP_GAP = 0.02;
/** Tolerance of the contract rules (`TIME_EPS` in `karaoke_contracts.validate`). */
const EPS = 0.001;

export type WordRef = { line: number; word: number };

/** Drops float noise (7.1000000000000005) without losing the engine's precision. */
const snap = (t: number) => Math.round(t * 1e6) / 1e6;
const clamp = (x: number, lo: number, hi: number) => Math.min(Math.max(x, lo), hi);
/** Clamps x, but a bound that `current` already breaks only keeps it from getting worse. */
const within = (x: number, lo: number, hi: number, current: number) =>
	clamp(x, Math.min(lo, current), Math.max(hi, current));

/** Where a line may start: not before the previous line, not after the next one. */
function startRange(doc: KaraokeDoc, index: number): [number, number] {
	const previous = index > 0 ? doc.lines[index - 1].start : 0;
	const next = index < doc.lines.length - 1 ? doc.lines[index + 1].start : doc.duration;
	return [Math.max(0, previous), Math.min(doc.duration, next)];
}

/** The word moved to [start, end], its parts stretched along with it. */
function respan(word: Word, start: number, end: number): Word {
	if (start === word.start && end === word.end) return word;
	const span = word.end - word.start;
	const count = word.parts.length;
	const at = (t: number) =>
		clamp(snap(start + ((t - word.start) / span) * (end - start)), start, end);
	// A zero-length word gives no proportions to keep: share it out evenly.
	const even = (k: number) => clamp(snap(start + (k / count) * (end - start)), start, end);
	const parts = word.parts.map((part, k) =>
		span > 0
			? { ...part, start: at(part.start), end: at(part.end) }
			: { ...part, start: even(k), end: even(k + 1) }
	);
	return { ...word, start, end, parts };
}

/** The line with these words, spanning exactly from the first start to the last end. */
function fit(line: Line, words: Word[]): Line {
	const start = Math.min(...words.map((w) => w.start));
	const end = Math.max(...words.map((w) => w.end));
	return { ...line, words, start, end };
}

function withLine(doc: KaraokeDoc, index: number, line: Line): KaraokeDoc {
	return { ...doc, edited: true, lines: doc.lines.map((l, i) => (i === index ? line : l)) };
}

function withWord(doc: KaraokeDoc, ref: WordRef, word: Word): KaraokeDoc {
	const line = doc.lines[ref.line];
	const words = line.words.map((w, i) => (i === ref.word ? word : w));
	return withLine(doc, ref.line, fit(line, words));
}

function lineAt(doc: KaraokeDoc, index: number): Line | undefined {
	return Number.isInteger(index) ? doc.lines[index] : undefined;
}

function wordAt(doc: KaraokeDoc, ref: WordRef): Word | undefined {
	const line = lineAt(doc, ref.line);
	return line && Number.isInteger(ref.word) ? line.words[ref.word] : undefined;
}

const isLetter = (ch: string) => /[\p{L}\p{N}]/u.test(ch);

/** The letters of a text, one per character, compared without case or accents. */
function letters(text: string): string[] {
	return [...text.normalize('NFC')]
		.filter(isLetter)
		.map((ch) => ch.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase());
}

const sameLetters = (a: string, b: string) => {
	const x = letters(a);
	const y = letters(b);
	return x.length === y.length && x.every((ch, i) => ch === y[i]);
};

/**
 * The new text cut where the old parts were cut, by letter count; leading and inner punctuation
 * stays with the letters before it and trailing punctuation goes to the last part, as the
 * contract wants. Null when a part would end up empty.
 */
function resplit(text: string, parts: Part[]): Part[] | null {
	const quotas = parts.map((p) => letters(p.text).length);
	const texts = parts.map(() => '');
	const chars = [...text];
	let lastLetter = -1;
	chars.forEach((ch, i) => {
		if (isLetter(ch)) lastLetter = i;
	});
	let k = 0;
	let used = 0;
	chars.forEach((ch, i) => {
		if (i > lastLetter) {
			texts[texts.length - 1] += ch;
			return;
		}
		if (isLetter(ch)) {
			while (k < parts.length - 1 && used >= quotas[k]) {
				k++;
				used = 0;
			}
			used++;
		}
		texts[k] += ch;
	});
	if (texts.some((t) => t === '')) return null;
	return parts.map((part, i) => ({ ...part, text: texts[i] }));
}

/**
 * Corrects a word's text. When only case, accents or punctuation change, the syllable timing is
 * kept and the new text is cut the same way; a different word loses its parts (the engine would
 * have to align it again).
 */
export function setWordText(doc: KaraokeDoc, ref: WordRef, text: string): KaraokeDoc {
	const word = wordAt(doc, ref);
	const clean = text.normalize('NFC').trim().replace(/\s+/g, ' ');
	if (!word || clean === '' || clean === word.text) return doc;
	const spelled = word.parts.map((p) => p.text).join('') === word.text;
	const parts =
		word.parts.length > 0 && spelled && sameLetters(clean, word.text)
			? resplit(clean, word.parts)
			: null;
	return withWord(doc, ref, { ...word, text: clean, parts: parts ?? [] });
}

/**
 * Drags the start or end of a word by `delta` seconds. It stops at its neighbours in the line,
 * at MIN_WORD long, at the song's edges and, for a line's first word, where the line would start
 * out of order.
 */
export function moveWordEdge(
	doc: KaraokeDoc,
	ref: WordRef,
	edge: 'start' | 'end',
	delta: number
): KaraokeDoc {
	const word = wordAt(doc, ref);
	if (!word || !Number.isFinite(delta)) return doc;
	const words = doc.lines[ref.line].words;
	let { start, end } = word;
	if (edge === 'start') {
		const [lineLo, lineHi] = ref.word === 0 ? startRange(doc, ref.line) : [0, Infinity];
		const lo = Math.max(lineLo, ref.word > 0 ? words[ref.word - 1].end : 0);
		const hi = Math.min(lineHi, snap(word.end - MIN_WORD));
		start = within(snap(word.start + delta), lo, hi, word.start);
	} else {
		const next = ref.word < words.length - 1 ? words[ref.word + 1].start : Infinity;
		const lo = snap(word.start + MIN_WORD);
		const hi = Math.min(next, doc.duration);
		end = within(snap(word.end + delta), lo, hi, word.end);
	}
	if (start === word.start && end === word.end) return doc;
	return withWord(doc, ref, respan(word, start, end));
}

/** Moves a whole line by `delta` seconds, stopping at the song's edges and its neighbour lines' starts. */
export function shiftLine(doc: KaraokeDoc, index: number, delta: number): KaraokeDoc {
	const line = lineAt(doc, index);
	if (!line || !Number.isFinite(delta)) return doc;
	const start = Math.min(...line.words.map((w) => w.start));
	const end = Math.max(...line.words.map((w) => w.end));
	const [lo, hi] = startRange(doc, index);
	const shift = within(snap(delta), lo - start, Math.min(hi - start, doc.duration - end), 0);
	if (shift === 0) return doc;
	const time = (t: number) => clamp(snap(t + shift), 0, doc.duration);
	const words = line.words.map((w) => respan(w, time(w.start), time(w.end)));
	return withLine(doc, index, fit(line, words));
}

/**
 * Times a line from taps: tap i is where word i starts, and each tapped word lasts until just
 * before the next one. With fewer taps than words, the last tapped word keeps its length and the
 * rest keep their times, pushed later only as far as needed to stay in order.
 */
export function retimeLine(doc: KaraokeDoc, index: number, taps: number[]): KaraokeDoc {
	const line = lineAt(doc, index);
	if (!line) return doc;
	const old = line.words;
	const sorted = taps
		.filter(Number.isFinite)
		.sort((a, b) => a - b)
		.slice(0, old.length);
	if (sorted.length === 0) return doc;
	const n = old.length;
	const k = sorted.length;
	// Leaves room for every later word to last MIN_WORD before the song ends.
	const latest = (i: number) => snap(doc.duration - (n - i) * MIN_WORD);
	const [lo, hi] = startRange(doc, index);
	const starts: number[] = [];
	sorted.forEach((tap, i) => {
		const floor = i === 0 ? lo : snap(starts[i - 1] + MIN_WORD);
		const ceil = i === 0 ? Math.min(hi, latest(0)) : latest(i);
		starts.push(clamp(snap(tap), floor, ceil));
	});

	const words = old.slice();
	// The last tapped word keeps its length: later words that would overlap it move on.
	let cursor = snap(
		Math.max(
			starts[k - 1] + MIN_WORD,
			Math.min(starts[k - 1] + old[k - 1].end - old[k - 1].start, latest(k))
		)
	);
	for (let m = k; m < n && old[m].start < cursor; m++) {
		const word = old[m];
		const end = clamp(snap(word.end + cursor - word.start), snap(cursor + MIN_WORD), latest(m + 1));
		words[m] = respan(word, cursor, end);
		cursor = end;
	}
	for (let i = 0; i < k; i++) {
		const start = starts[i];
		const end =
			i < k - 1
				? clamp(snap(starts[i + 1] - TAP_GAP), snap(start + MIN_WORD), starts[i + 1])
				: clamp(
						snap(start + old[i].end - old[i].start),
						snap(start + MIN_WORD),
						k < n ? words[k].start : doc.duration
					);
		words[i] = respan(old[i], start, end);
	}
	if (words.every((w, i) => w === old[i])) return doc;
	return withLine(doc, index, fit(line, words));
}

const seconds = (t: number) => `${Number.isFinite(t) ? +t.toFixed(3) : t} s`;

/**
 * Every contract rule the document breaks, in words someone can act on; [] when it is valid.
 * Mirrors `validate_doc` in `karaoke_contracts`, which the server applies when saving.
 */
export function checkDoc(doc: KaraokeDoc): string[] {
	const problems: string[] = [];
	const report = (where: string, problem: string) => problems.push(`${where} ${problem}`);
	// Parts skip the song's end: a part past it is outside its word, already reported.
	const span = (where: string, start: number, end: number, song = true) => {
		if (!Number.isFinite(start) || !Number.isFinite(end)) {
			report(where, 'has a time that is not a number');
			return;
		}
		if (start < 0) report(where, `starts at ${seconds(start)}, before the song`);
		if (end < start) report(where, `ends (${seconds(end)}) before it starts (${seconds(start)})`);
		if (song && end > doc.duration + EPS) {
			report(where, `ends at ${seconds(end)}, after the song (${seconds(doc.duration)})`);
		}
	};
	const inside = (where: string, inner: Word | Part, outer: Line | Word, name: string) => {
		if (inner.start < outer.start - EPS || inner.end > outer.end + EPS) {
			const at = `${seconds(outer.start)}–${seconds(outer.end)}`;
			report(
				where,
				`(${seconds(inner.start)}–${seconds(inner.end)}) is outside its ${name} (${at})`
			);
		}
	};

	const singers = new Set(doc.singers.map((s) => s.id));
	const ids = new Set<string>();
	let previousLine = 0;
	doc.lines.forEach((line, i) => {
		const where = `Line ${i + 1}`;
		span(where, line.start, line.end);
		if (line.start < previousLine - EPS) report(where, 'starts before the previous line');
		previousLine = line.start;
		if (ids.has(line.id)) report(where, `has the same id as another line ("${line.id}")`);
		ids.add(line.id);
		if (line.singer !== null && !singers.has(line.singer)) {
			report(where, `is sung by an unknown singer ("${line.singer}")`);
		}
		if (line.words.length === 0) report(where, 'has no words');

		let previousWord = line.start;
		line.words.forEach((word, j) => {
			const at = `${where}, word ${j + 1} ("${word.text}")`;
			span(at, word.start, word.end);
			inside(at, word, line, 'line');
			if (word.start < previousWord - EPS) report(at, 'starts before the previous word');
			previousWord = word.start;
			if (word.parts.length === 0) return;
			const spelled = word.parts.map((p) => p.text).join('');
			if (spelled !== word.text) report(at, `has parts that spell "${spelled}"`);
			let previousPart = word.start;
			word.parts.forEach((part, k) => {
				const pat = `${at}, part ${k + 1} ("${part.text}")`;
				span(pat, part.start, part.end, false);
				inside(pat, part, word, 'word');
				if (part.start < previousPart - EPS) report(pat, 'starts before the previous part');
				previousPart = part.start;
			});
		});
	});
	const singerIds = new Set<string>();
	doc.singers.forEach((singer, i) => {
		if (singerIds.has(singer.id)) {
			report(`Singer ${i + 1}`, `has the same id as another singer ("${singer.id}")`);
		}
		singerIds.add(singer.id);
	});
	return problems;
}
