/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

export interface Theme {
	schema_version: string;
	id: string;
	name: string;
	font: ThemeFont;
	colors: ThemeColors;
	layout: ThemeLayout;
	animation: ThemeAnimation;
	backing: ThemeBacking;
}
export interface ThemeFont {
	family: string;
	weight: number;
	/**
	 * Font file bundled with the theme, if any.
	 */
	file: string | null;
}
export interface ThemeColors {
	sung: string;
	unsung: string;
	outline: string;
	shadow: string | null;
	box: string | null;
	/**
	 * Sung colour of each singer, in order, when a song has two or more.
	 */
	singers: string[];
}
export interface ThemeLayout {
	visible_lines: number;
	position: 'bottom' | 'center' | 'top';
	/**
	 * Fraction of screen height.
	 */
	font_size: number;
	line_spacing: number;
	/**
	 * pages: fixed rows that take turns (classic); scroll: a list that moves up.
	 */
	mode: 'pages' | 'scroll';
	/**
	 * Safe margin on each side, fraction of the screen.
	 */
	margin: number;
	/**
	 * The font shrinks so a row fits this many letters.
	 */
	min_row_chars: number;
	/**
	 * Rows a long line may wrap into before shrinking.
	 */
	max_rows: number;
	/**
	 * Fraction of the font size.
	 */
	outline_width: number;
	/**
	 * Fraction of the font size.
	 */
	shadow_offset: number;
	/**
	 * Fraction of the font size.
	 */
	shadow_blur: number;
}
export interface ThemeAnimation {
	fill: 'wipe' | 'word';
	/**
	 * Instrumental gap (s) that triggers a countdown; 0 = off.
	 */
	countdown_min_gap: number;
	/**
	 * Seconds a block of lines shows before it is sung.
	 */
	lead_in: number;
	/**
	 * Seconds a sung line stays before its slot is reused.
	 */
	hold: number;
	/**
	 * Seconds of fades and scrolling.
	 */
	transition: number;
	/**
	 * Seconds the highlight runs ahead of the sound.
	 */
	anticipation: number;
	countdown_dots: number;
	/**
	 * Seconds per dot.
	 */
	countdown_step: number;
	/**
	 * Gaps this long (s) show a progress bar; 0 = never.
	 */
	break_bar_min: number;
}
/**
 * How backing vocals (lines with role "backing") look.
 */
export interface ThemeBacking {
	scale: number;
	brackets: boolean;
	opacity: number;
}
