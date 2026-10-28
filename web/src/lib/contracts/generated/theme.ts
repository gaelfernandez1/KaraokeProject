/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

export interface Theme {
	schema_version: string;
	id: string;
	name: string;
	font: ThemeFont;
	colors: ThemeColors;
	layout: ThemeLayout;
	animation: ThemeAnimation;
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
}
export interface ThemeLayout {
	visible_lines: number;
	position: 'bottom' | 'center' | 'top';
	/**
	 * Fraction of screen height.
	 */
	font_size: number;
	line_spacing: number;
}
export interface ThemeAnimation {
	fill: 'wipe' | 'word';
	/**
	 * Instrumental gap (s) that triggers a countdown; 0 = off.
	 */
	countdown_min_gap: number;
}
