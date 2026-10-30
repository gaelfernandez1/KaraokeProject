/** What `scripts/build_fonts.py` writes next to each font (`*.metrics.json`). */
export interface MetricsData {
	upem: number;
	ascender: number;
	descender: number;
	win_ascent: number;
	win_descent: number;
	default_advance: number;
	average_lowercase: number;
	advances: Record<string, number>;
}

/**
 * Advance widths of a theme's font: the web and the video export (Python) measure text with the
 * same table, so they break lines in the same places whatever the browser's text engine does.
 */
export class FontMetrics {
	readonly upem: number;
	readonly averageLowercase: number;
	readonly #advances: Map<string, number>;
	readonly #default: number;

	constructor(data: MetricsData) {
		this.upem = data.upem;
		this.averageLowercase = data.average_lowercase;
		this.#advances = new Map(Object.entries(data.advances));
		this.#default = data.default_advance;
	}

	/**
	 * Width of `text` at `px` pixels per em, without kerning. Sums in text order and scales once,
	 * exactly like the Python side, so both get the same floating-point result.
	 */
	width(text: string, px: number): number {
		let total = 0;
		// for…of walks code points, as Python iterates a str.
		for (const char of text) total += this.#advances.get(char) ?? this.#default;
		return (total * px) / this.upem;
	}
}
