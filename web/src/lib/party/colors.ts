import { SINGER_COLORS } from './types';

/**
 * A guest's colour as the screens draw it. The server hands out SINGER_COLORS by order of
 * arrival; on screen each becomes the night's own colour for people (--cantante-1 to 4), which
 * is never the amber of what is lit nor the blue of what is selected. A colour from elsewhere
 * is kept as it is.
 */
export function singerColor(color: string | null | undefined, fallback = 'var(--texto-2)'): string {
	if (!color) return fallback;
	const index = SINGER_COLORS.findIndex((known) => known.toLowerCase() === color.toLowerCase());
	return index === -1 ? color : `var(--cantante-${index + 1})`;
}
