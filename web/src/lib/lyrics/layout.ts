import type { KaraokeDoc, Line, Theme } from '#lib/contracts';
import type { FontMetrics } from './metrics';

/*
 * Where and when every lyrics row shows, for any screen size: a line-for-line port of
 * `karaoke_engine/subtitles/layout.py`, the reference. The shared cases in
 * `fixtures/lyrics-layout/` keep both identical, so the browser and the video break lines and take
 * turns in exactly the same way. Keep the order of operations as there (floating-point results
 * must match) and the field names as in its JSON.
 */

const BREAK_AFTER = ',.;:!?…»)';
const PUNCTUATION_BONUS = 0.9;
const MIN_SCALE = 0.6;
const BACKING_ATTACH = 1.5;
const MIN_LEAD = 0.5;
const SCROLL_GAP = 0.35;
const SCROLL_ANCHOR = { top: 0.3, center: 0.42, bottom: 0.62 } as const;
const SCROLL_SETTLE = 0.25;

export interface PartSpan {
	text: string;
	start: number;
	end: number;
}

/** A word as displayed: its syllables, or one part for the whole word. */
export interface RowWord {
	parts: PartSpan[];
}

export interface Row {
	line_id: string;
	role: 'lead' | 'backing';
	singer: string | null;
	color: string;
	words: RowWord[];
	text: string;
	scale: number;
	x: number;
	y: number;
	width: number;
	height: number;
}

/** A lead line with the backing lines sung over or right after it, shown together. */
export interface Group {
	index: number;
	block: number;
	slot: number;
	start: number;
	end: number;
	show: number;
	hide: number;
	rows: Row[];
}

export interface Dot {
	x: number;
	y: number;
	r: number;
	off: number;
}

export interface Countdown {
	block: number;
	start: number;
	end: number;
	dots: Dot[];
}

/** Progress through an instrumental break, from the last line shown to the next one. */
export interface BreakBar {
	start: number;
	end: number;
	x: number;
	y: number;
	width: number;
	height: number;
}

/**
 * Scroll mode: rows are placed in one long list that moves up as the song goes on. `offsets[k]`
 * moves the list so that group k sits on the anchor; the list starts moving to group k at
 * `switches[k - 1]` and takes `transition` seconds (ease-out).
 */
export interface ScrollPlan {
	offsets: number[];
	switches: number[];
	transition: number;
	visible: number;
}

export interface Layout {
	width: number;
	height: number;
	font_px: number;
	mode: 'pages' | 'scroll';
	groups: Group[];
	countdowns: Countdown[];
	bars: BreakBar[];
	scroll: ScrollPlan | null;
}

/**
 * The generated types say every field is present, because the engine always writes them; a 1.0.0
 * package (or a hand-made one) may leave out `role`, `singer`, `parts` or `singers`.
 */
export function normalizeDoc(doc: KaraokeDoc): KaraokeDoc {
	return {
		...doc,
		singers: doc.singers ?? [],
		lines: doc.lines.map((line) => ({
			...line,
			singer: line.singer ?? null,
			role: line.role ?? 'lead',
			words: line.words.map((word) => ({ ...word, parts: word.parts ?? [] }))
		}))
	};
}

const range = (from: number, to: number): number[] =>
	Array.from({ length: to - from }, (_, i) => from + i);

/** Rows (word indices) for a line, and how much to shrink it so the widest row fits. */
export function wrap(
	words: string[],
	px: number,
	maxWidth: number,
	maxRows: number,
	metrics: FontMetrics
): [number[][], number] {
	const full = metrics.width(words.join(' '), px);
	if (full <= maxWidth) return [[range(0, words.length)], 1];
	if (maxRows < 2 || words.length < 2) {
		return [[range(0, words.length)], Math.max(MIN_SCALE, maxWidth / full)];
	}
	let best = 1;
	let bestCost = 0;
	let bestWidest = 0;
	for (let i = 1; i < words.length; i++) {
		const widest = Math.max(
			metrics.width(words.slice(0, i).join(' '), px),
			metrics.width(words.slice(i).join(' '), px)
		);
		const cost = BREAK_AFTER.includes(words[i - 1].slice(-1)) ? widest * PUNCTUATION_BONUS : widest;
		if (i === 1 || cost < bestCost) [best, bestCost, bestWidest] = [i, cost, widest];
	}
	const rows = [range(0, best), range(best, words.length)];
	if (bestWidest <= maxWidth) return [rows, 1];
	return [rows, Math.max(MIN_SCALE, maxWidth / bestWidest)];
}

function displayWords(line: Line, brackets: boolean): RowWord[] {
	const words: RowWord[] = line.words.map((word) => ({
		parts:
			word.parts.length > 0
				? word.parts.map((p) => ({ text: p.text, start: p.start, end: p.end }))
				: [{ text: word.text, start: word.start, end: word.end }]
	}));
	if (brackets) {
		const first = words[0].parts[0];
		words[0].parts[0] = { ...first, text: '[' + first.text };
		const lastWord = words[words.length - 1];
		const last = lastWord.parts[lastWord.parts.length - 1];
		lastWord.parts[lastWord.parts.length - 1] = { ...last, text: last.text + ']' };
	}
	return words;
}

const lineStart = (lines: Line[]): number => Math.min(...lines.map((l) => l.start));

/** Lead lines with their backing lines attached; lone backing lines are groups of their own. */
function makeGroups(doc: KaraokeDoc): Line[][] {
	const leads = doc.lines.filter((l) => l.role === 'lead').sort((a, b) => a.start - b.start);
	const attached: Line[][] = leads.map(() => []);
	const alone: Line[] = [];
	for (const line of doc.lines) {
		if (line.role !== 'backing') continue;
		let target = -1;
		let best = 0;
		leads.forEach((lead, i) => {
			const overlap = Math.min(line.end, lead.end) - Math.max(line.start, lead.start);
			if (overlap > best) [target, best] = [i, overlap];
		});
		if (target < 0) {
			let previous = -1;
			leads.forEach((lead, i) => {
				if (lead.end <= line.start && (previous < 0 || lead.end >= leads[previous].end))
					previous = i;
			});
			if (previous >= 0 && line.start - leads[previous].end < BACKING_ATTACH) target = previous;
		}
		if (target >= 0) attached[target].push(line);
		else alone.push(line);
	}
	const groups = leads.map((lead, i) => [
		lead,
		...[...attached[i]].sort((a, b) => a.start - b.start)
	]);
	for (const line of alone) groups.push([line]);
	return groups.sort((a, b) => lineStart(a) - lineStart(b));
}

function singerColors(doc: KaraokeDoc, theme: Theme): Map<string | null, string> {
	const colors = new Map<string | null, string>([[null, theme.colors.sung]]);
	const palette = theme.colors.singers;
	doc.singers.forEach((singer, i) => {
		if (singer.color !== null && singer.color !== undefined) colors.set(singer.id, singer.color);
		else if (doc.singers.length >= 2 && palette.length > 0) {
			colors.set(singer.id, palette[i % palette.length]);
		} else colors.set(singer.id, theme.colors.sung);
	});
	return colors;
}

/** The rows of one group, stacked from y = 0 (moved into place later). */
function makeRows(
	lines: Line[],
	theme: Theme,
	fontPx: number,
	usable: number,
	metrics: FontMetrics,
	colors: Map<string | null, string>
): Row[] {
	const rows: Row[] = [];
	let top = 0;
	for (const line of lines) {
		const backing = line.role === 'backing';
		const roleScale = backing ? theme.backing.scale : 1;
		const words = displayWords(line, backing && theme.backing.brackets);
		const texts = words.map((w) => w.parts.map((p) => p.text).join(''));
		const [indices, wrapScale] = wrap(
			texts,
			fontPx * roleScale,
			usable,
			theme.layout.max_rows,
			metrics
		);
		const scale = roleScale * wrapScale;
		const rowPx = fontPx * scale;
		const height = rowPx * theme.layout.line_spacing;
		for (const rowWords of indices) {
			const text = rowWords.map((i) => texts[i]).join(' ');
			rows.push({
				line_id: line.id,
				role: line.role,
				singer: line.singer,
				color: colors.get(line.singer) ?? theme.colors.sung,
				words: rowWords.map((i) => words[i]),
				text,
				scale,
				x: 0,
				y: top + height / 2,
				width: metrics.width(text, rowPx),
				height
			});
			top += height;
		}
	}
	return rows;
}

function rowsHeight(rows: Row[]): number {
	let total = 0;
	for (const row of rows) total += row.height;
	return total;
}

/** Dots above the left end of the first row of a block, going out right to left. */
function makeCountdown(
	block: number,
	row: Row,
	yOffset: number,
	start: number,
	end: number,
	fontPx: number,
	theme: Theme
): Countdown {
	const anim = theme.animation;
	const left = row.x - row.width / 2;
	const y = row.y + yOffset - row.height / 2 - 0.45 * fontPx;
	const dots = range(0, anim.countdown_dots).map((j) => ({
		x: left + 0.2 * fontPx + j * 0.55 * fontPx,
		y,
		r: 0.14 * fontPx,
		off: end - j * anim.countdown_step
	}));
	return { block, start, end, dots };
}

/** Ease-out cubic, written as products so Python and JS round alike. */
function ease(u: number): number {
	const v = 1 - u;
	return 1 - v * v * v;
}

/** The group the list is moving to (or resting on) at `t`, and how far it has got (0–1). */
function scrollStep(plan: ScrollPlan, t: number): [number, number] {
	let k = 0;
	while (k < plan.switches.length && plan.switches[k] <= t) k++;
	if (k === 0) return [0, 1];
	if (plan.transition <= 0) return [k, 1];
	const u = (t - plan.switches[k - 1]) / plan.transition;
	return [k, u < 1 ? ease(u) : 1];
}

/** Which group is on the anchor at `t`, with the fraction of a move in progress. */
export function scrollFocus(plan: ScrollPlan, t: number): number {
	const [k, done] = scrollStep(plan, t);
	return k > 0 ? k - 1 + done : 0;
}

/** How far down the list is drawn at `t`, in px. */
export function scrollOffset(plan: ScrollPlan, t: number): number {
	const [k, done] = scrollStep(plan, t);
	if (k === 0) return plan.offsets[0];
	return plan.offsets[k - 1] + (plan.offsets[k] - plan.offsets[k - 1]) * done;
}

/** Opacity of a group `rank` places after the one on the anchor (negative: already sung). */
export function scrollOpacity(rank: number, visible: number): number {
	if (rank < 0) return Math.max(0, 1 + 0.6 * rank);
	if (rank <= visible - 1) return 1 - 0.12 * rank;
	return Math.max(0, (1 - 0.12 * (visible - 1)) * (visible - rank));
}

function scrollLayout(
	theme: Theme,
	width: number,
	height: number,
	fontPx: number,
	rowsByGroup: Row[][],
	starts: number[],
	ends: number[],
	blocks: number[][]
): Layout {
	const anim = theme.animation;
	const visible = theme.layout.visible_lines;
	const anchor = SCROLL_ANCHOR[theme.layout.position] * height;
	const n = rowsByGroup.length;
	const tops: number[] = [];
	let top = 0;
	for (const rows of rowsByGroup) {
		tops.push(top);
		top += rowsHeight(rows) + SCROLL_GAP * fontPx;
	}
	const offsets = range(0, n).map((k) => anchor - (tops[k] + rowsHeight(rowsByGroup[k]) / 2));
	const switches: number[] = [];
	for (let k = 1; k < n; k++) {
		let sw = Math.min(ends[k - 1] + anim.hold, starts[k] - anim.transition - SCROLL_SETTLE);
		if (switches.length > 0) sw = Math.max(sw, switches[switches.length - 1] + anim.transition);
		switches.push(sw);
	}
	const plan: ScrollPlan = { offsets, switches, transition: anim.transition, visible };
	const lastHide = ends.length > 0 ? Math.max(...ends) + 2 * anim.hold : 0;
	const blockOf = new Map<number, number>();
	blocks.forEach((members, b) => members.forEach((k) => blockOf.set(k, b)));
	const groups: Group[] = rowsByGroup.map((rows, k) => ({
		index: k,
		block: blockOf.get(k) ?? 0,
		slot: 0,
		start: starts[k],
		end: ends[k],
		show: k >= visible ? switches[k - visible] : 0,
		hide: k + 1 < switches.length ? switches[k + 1] + anim.transition : lastHide,
		rows: rows.map((row) => ({ ...row, x: width / 2, y: tops[k] + row.y }))
	}));
	const countdowns: Countdown[] = [];
	let previousEnd = 0;
	blocks.forEach((members, b) => {
		const first = members[0];
		const gapBefore = b > 0 ? starts[first] - previousEnd : starts[first];
		if (
			anim.countdown_min_gap > 0 &&
			anim.countdown_dots > 0 &&
			gapBefore >= anim.countdown_min_gap
		) {
			const start = Math.max(
				starts[first] - anim.countdown_dots * anim.countdown_step,
				groups[first].show
			);
			countdowns.push(
				makeCountdown(b, groups[first].rows[0], offsets[first], start, starts[first], fontPx, theme)
			);
		}
		previousEnd = Math.max(...members.map((k) => ends[k]));
	});
	return {
		width,
		height,
		font_px: fontPx,
		mode: 'scroll',
		groups,
		countdowns,
		bars: [],
		scroll: plan
	};
}

export function buildLayout(
	doc: KaraokeDoc,
	theme: Theme,
	width: number,
	height: number,
	metrics: FontMetrics
): Layout {
	const marginX = theme.layout.margin * width;
	const marginY = theme.layout.margin * height;
	const usable = width - 2 * marginX;
	const fontPx = Math.min(
		theme.layout.font_size * height,
		usable / ((theme.layout.min_row_chars * metrics.averageLowercase) / metrics.upem)
	);
	const colors = singerColors(doc, theme);
	const anim = theme.animation;
	const slots = theme.layout.visible_lines;

	const linesByGroup = makeGroups(doc);
	const starts = linesByGroup.map(lineStart);
	const ends = linesByGroup.map((g) => Math.max(...g.map((l) => l.end)));
	const rowsByGroup = linesByGroup.map((g) => makeRows(g, theme, fontPx, usable, metrics, colors));

	// Blocks: runs of groups between instrumental breaks.
	const blocks: number[][] = [];
	let latestEnd = 0;
	for (let k = 0; k < linesByGroup.length; k++) {
		const gap = starts[k] - latestEnd;
		if (k === 0 || (anim.countdown_min_gap > 0 && gap >= anim.countdown_min_gap)) blocks.push([]);
		blocks[blocks.length - 1].push(k);
		latestEnd = k === 0 ? ends[k] : Math.max(latestEnd, ends[k]);
	}

	if (theme.layout.mode === 'scroll') {
		return scrollLayout(theme, width, height, fontPx, rowsByGroup, starts, ends, blocks);
	}

	const n = linesByGroup.length;
	const show = new Array<number>(n).fill(0);
	const hide = new Array<number>(n).fill(0);
	const slotOf = new Array<number>(n).fill(0);
	const blockOf = new Array<number>(n).fill(0);
	const countdowns: Countdown[] = [];
	const bars: BreakBar[] = [];
	let previousHide = 0;
	let previousEnd = 0;
	blocks.forEach((members, b) => {
		const first = members[0];
		const blockStart = starts[first];
		const blockEnd = Math.max(...members.map((k) => ends[k]));
		const blockShow = Math.max(blockStart - anim.lead_in, previousHide, 0);
		const blockHide =
			b + 1 < blocks.length
				? Math.min(blockEnd + 2 * anim.hold, starts[blocks[b + 1][0]])
				: blockEnd + 2 * anim.hold;
		members.forEach((k, j) => {
			slotOf[k] = j % slots;
			blockOf[k] = b;
			show[k] = j < slots ? blockShow : hide[members[j - slots]];
			if (j + slots < members.length) {
				const later = starts[members[j + slots]];
				// The next line in this slot shows MIN_LEAD early, never before this one ends.
				const ready = Math.max(later - MIN_LEAD, ends[k]);
				hide[k] = Math.max(show[k], Math.min(ends[k] + anim.hold, ready));
			} else {
				hide[k] = blockHide;
			}
		});

		// Slot bands: as tall as the tallest group they hold in this block.
		const bands = new Array<number>(slots).fill(0);
		for (const k of members) {
			bands[slotOf[k]] = Math.max(bands[slotOf[k]], rowsHeight(rowsByGroup[k]));
		}
		let total = 0;
		for (const band of bands) total += band;
		let top: number;
		if (theme.layout.position === 'bottom') top = height - marginY - total;
		else if (theme.layout.position === 'top') top = marginY;
		else top = height / 2 - total / 2;
		const bandTops: number[] = [];
		for (const band of bands) {
			bandTops.push(top);
			top += band;
		}
		for (const k of members) {
			const slot = slotOf[k];
			const groupHeight = rowsHeight(rowsByGroup[k]);
			let offset: number;
			if (slots === 1 || (slots % 2 === 1 && slot === Math.floor(slots / 2))) {
				offset = bandTops[slot] + (bands[slot] - groupHeight) / 2;
			} else if (slot < slots / 2) {
				offset = bandTops[slot] + bands[slot] - groupHeight;
			} else {
				offset = bandTops[slot];
			}
			rowsByGroup[k] = rowsByGroup[k].map((row) => ({ ...row, x: width / 2, y: offset + row.y }));
		}

		const gapBefore = b > 0 ? blockStart - previousEnd : blockStart;
		if (
			anim.countdown_min_gap > 0 &&
			anim.countdown_dots > 0 &&
			gapBefore >= anim.countdown_min_gap
		) {
			const start = Math.max(blockStart - anim.countdown_dots * anim.countdown_step, blockShow);
			countdowns.push(makeCountdown(b, rowsByGroup[first][0], 0, start, blockStart, fontPx, theme));
		}

		if (anim.break_bar_min > 0 && blockShow - previousHide >= anim.break_bar_min) {
			bars.push({
				start: previousHide,
				end: blockShow,
				x: width / 2,
				y: bandTops[0] + total / 2,
				width: 0.3 * usable,
				height: 0.08 * fontPx
			});
		}
		previousHide = blockHide;
		previousEnd = blockEnd;
	});

	const groups: Group[] = rowsByGroup.map((rows, k) => ({
		index: k,
		block: blockOf[k],
		slot: slotOf[k],
		start: starts[k],
		end: ends[k],
		show: show[k],
		hide: hide[k],
		rows
	}));
	return {
		width,
		height,
		font_px: fontPx,
		mode: theme.layout.mode,
		groups,
		countdowns,
		bars,
		scroll: null
	};
}
