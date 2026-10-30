import type { Theme } from '#lib/contracts';
import { FontMetrics, type MetricsData } from './metrics';
// One copy of the themes and fonts: the Python package's, which the video export uses too.
import clasico from '../../../../packages/engine/src/karaoke_engine/subtitles/themes/clasico.json';
import contraste from '../../../../packages/engine/src/karaoke_engine/subtitles/themes/contraste.json';
import moderno from '../../../../packages/engine/src/karaoke_engine/subtitles/themes/moderno.json';
import atkinsonMetrics from '../../../../packages/engine/src/karaoke_engine/subtitles/themes/fonts/AtkinsonHyperlegibleNext-ExtraBold.metrics.json';
import interMetrics from '../../../../packages/engine/src/karaoke_engine/subtitles/themes/fonts/Inter-ExtraBold.metrics.json';
import nunitoMetrics from '../../../../packages/engine/src/karaoke_engine/subtitles/themes/fonts/Nunito-Black.metrics.json';
import atkinsonUrl from '../../../../packages/engine/src/karaoke_engine/subtitles/themes/fonts/AtkinsonHyperlegibleNext-ExtraBold.woff2?url';
import interUrl from '../../../../packages/engine/src/karaoke_engine/subtitles/themes/fonts/Inter-ExtraBold.woff2?url';
import nunitoUrl from '../../../../packages/engine/src/karaoke_engine/subtitles/themes/fonts/Nunito-Black.woff2?url';

export const THEMES: Record<string, Theme> = {
	clasico: clasico as Theme,
	contraste: contraste as Theme,
	moderno: moderno as Theme
};

/** The theme used when none is chosen, and whose font measures themes without a bundled one. */
export const DEFAULT_THEME = 'clasico';

const FONTS: Record<string, { metrics: FontMetrics; url: string }> = {
	'Nunito-Black.ttf': { metrics: new FontMetrics(nunitoMetrics as MetricsData), url: nunitoUrl },
	'Inter-ExtraBold.ttf': { metrics: new FontMetrics(interMetrics as MetricsData), url: interUrl },
	'AtkinsonHyperlegibleNext-ExtraBold.ttf': {
		metrics: new FontMetrics(atkinsonMetrics as MetricsData),
		url: atkinsonUrl
	}
};

const bundled = (theme: Theme) => (theme.font.file ? FONTS[theme.font.file] : undefined);

export function metricsFor(theme: Theme): FontMetrics {
	return (bundled(theme) ?? FONTS[THEMES[DEFAULT_THEME].font.file as string]).metrics;
}

/** What an @font-face needs for a theme's bundled font; null if it relies on an installed font. */
export function fontFaceFor(theme: Theme): { family: string; url: string } | null {
	const font = bundled(theme);
	return font ? { family: theme.font.family, url: font.url } : null;
}
