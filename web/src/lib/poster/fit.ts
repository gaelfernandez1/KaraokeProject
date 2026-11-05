import metrics from './display-metrics.json';

const WIDTHS: Record<string, number> = metrics.widths;
/** For characters the table lacks: about an average capital. */
const FALLBACK = 0.5;

/** Width of a text in the poster face, in em. */
export function textWidth(text: string): number {
	let width = 0;
	for (const char of text) width += WIDTHS[char] ?? FALLBACK;
	return width;
}

export interface FitOptions {
	/** Box the title must fit in, in the same unit as the size (e.g. cqi). */
	maxWidth: number;
	maxHeight: number;
	/** Line height as a fraction of the size. */
	lineHeight: number;
	maxSize: number;
	maxLines: number;
}

export interface Fit {
	lines: string[];
	/** Font size, in the unit of the box. */
	size: number;
}

/**
 * Sets a title the way a poster does: in capitals, broken between words into the number of
 * lines that lets it be biggest, as big as the box allows. A word is never broken: one that is
 * too long on its own makes the whole title smaller.
 */
export function fitTitle(title: string, options: FitOptions): Fit {
	const words = title.toLocaleUpperCase('gl').split(/\s+/).filter(Boolean);
	if (words.length === 0) return { lines: [], size: options.maxSize };
	const space = textWidth(' ');
	const widths = words.map(textWidth);
	// Width of the line made of words i..j-1.
	const span = (i: number, j: number) =>
		widths.slice(i, j).reduce((sum, w) => sum + w, 0) + space * (j - i - 1);

	let best: Fit = { lines: [], size: 0 };
	for (let count = 1; count <= Math.min(options.maxLines, words.length); count++) {
		const breaks = narrowest(words.length, count, span);
		const lines = breaks.map(([i, j]) => words.slice(i, j).join(' '));
		const widest = Math.max(...breaks.map(([i, j]) => span(i, j)));
		const size = Math.min(
			options.maxSize,
			options.maxWidth / widest,
			options.maxHeight / (count * options.lineHeight)
		);
		if (size > best.size + 1e-9) best = { lines, size };
	}
	return best;
}

/**
 * Splits n words into `count` consecutive lines so that the widest line is as narrow as
 * possible (dynamic programming over where each line starts).
 */
function narrowest(
	n: number,
	count: number,
	span: (i: number, j: number) => number
): [number, number][] {
	// cost[k][j]: narrowest widest-line for the first j words on k lines; from[k][j]: last start.
	const cost = Array.from({ length: count + 1 }, () => new Array<number>(n + 1).fill(Infinity));
	const from = Array.from({ length: count + 1 }, () => new Array<number>(n + 1).fill(0));
	cost[0][0] = 0;
	for (let k = 1; k <= count; k++) {
		for (let j = k; j <= n; j++) {
			for (let i = k - 1; i < j; i++) {
				const value = Math.max(cost[k - 1][i], span(i, j));
				if (value < cost[k][j]) {
					cost[k][j] = value;
					from[k][j] = i;
				}
			}
		}
	}
	const lines: [number, number][] = [];
	for (let k = count, j = n; k > 0; k--) {
		const i = from[k][j];
		lines.unshift([i, j]);
		j = i;
	}
	return lines;
}

/**
 * A title's version tag, set apart as gig posters do: "Mar de Vigo (demo sintética)" is "Mar de
 * Vigo" with the tag "demo sintética"; so is "Song - Live in Lugo". Titles that are only a
 * bracket keep it.
 */
export function splitTitle(title: string): { main: string; tag: string | null } {
	const clean = title.trim();
	const bracket = /^(.*\S)\s*[([]([^()[\]]+)[)\]]\s*$/.exec(clean);
	if (bracket) return { main: bracket[1], tag: bracket[2].trim() };
	const dash = /^(.*\S)\s+[-–—]\s+(\S.*)$/.exec(clean);
	if (dash) return { main: dash[1], tag: dash[2] };
	return { main: clean, tag: null };
}

/** Words that say nothing about a song on their own, in the languages sung most here. */
const LITTLE_WORDS = new Set(
	'a o os as e de do da dos das en no na nos nas un unha uns unhas co coa el la los las lo del al y con por para que mi tu the of and to in on my your le les des du et un une'.split(
		' '
	)
);

/** The word that best stands for a title on a small cut-out: the first one with some weight. */
export function keyWord(title: string): string {
	const words = splitTitle(title).main.split(/\s+/).filter(Boolean);
	const plain = (word: string) => word.toLocaleLowerCase('gl').replace(/[^\p{L}\p{N}]/gu, '');
	return (
		words.find((w) => plain(w).length > 2 && !LITTLE_WORDS.has(plain(w))) ??
		words[0] ??
		''
	).replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '');
}
