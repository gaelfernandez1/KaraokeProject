/**
 * Every song gets a poster of its own, always the same one: two inks of the app's palette
 * (the cover is printed in the dark ink on the coloured paper) and where the title goes.
 */
export const PALETTES = [
	// Printing papers, none of them the lyric amber or a guest's colour.
	{ paper: '#E6D8BC', ink: '#16122E' }, // kraft
	{ paper: '#FF6A4D', ink: '#16122E' }, // tomato
	{ paper: '#F3EFFA', ink: '#16122E' }, // white
	{ paper: '#B9A5FF', ink: '#16122E' }, // lilac
	{ paper: '#2D4FE0', ink: '#F3EFFA' }, // verbena blue, white ink
	// A night poster: kraft ink on dark paper.
	{ paper: '#2A2257', ink: '#E6D8BC' }
] as const;

export interface PosterStyle {
	palette: number;
	paper: string;
	ink: string;
	/** Whether the title sits above the picture or below it. */
	layout: 'top' | 'bottom';
	/** Dark paper prints the picture lighter instead of darker. */
	dark: boolean;
}

/** 32-bit FNV-1a with a final avalanche (MurmurHash3's), so ids that differ by a few letters
 * still land on different papers. */
function hash(text: string): number {
	let h = 0x811c9dc5;
	for (let i = 0; i < text.length; i++) {
		h ^= text.charCodeAt(i);
		h = Math.imul(h, 0x01000193);
	}
	h ^= h >>> 16;
	h = Math.imul(h, 0x85ebca6b);
	h ^= h >>> 13;
	h = Math.imul(h, 0xc2b2ae35);
	h ^= h >>> 16;
	return h >>> 0;
}

/** A song's poster: always the same, wherever it shows. */
export function posterStyle(id: string): PosterStyle {
	const h = hash(id);
	const palette = (h >>> 8) % PALETTES.length;
	return {
		palette,
		...PALETTES[palette],
		layout: (h & 1) === 0 ? 'top' : 'bottom',
		dark: palette === PALETTES.length - 1
	};
}
