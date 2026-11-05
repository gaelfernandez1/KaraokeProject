import type { KaraokeDoc, Line } from '#lib/contracts';

/** Builds a line whose words share its time evenly. */
function line(id: string, text: string, start: number, end: number): Line {
	const words = text.split(' ');
	const step = (end - start) / words.length;
	return {
		id,
		start,
		end,
		singer: 's1',
		role: 'lead',
		words: words.map((word, i) => ({
			text: word,
			start: start + i * step,
			end: start + (i + 1) * step - 0.05,
			confidence: null,
			parts: []
		}))
	};
}

/** Two lines to preview a lyrics style, with no audio behind them. */
export const SAMPLE_DOC: KaraokeDoc = {
	schema_version: '1.1.0',
	id: 'mostra',
	title: 'Mostra',
	artist: null,
	language: 'gl',
	duration: 12,
	audio: { instrumental: 'instrumental.m4a', vocals: null, loudness_lufs: null },
	video: null,
	cover: null,
	singers: [{ id: 's1', name: null, color: null }],
	lines: [line('l1', 'Ola, mar de Vigo,', 1, 4), line('l2', 'cántame a túa canción', 4.5, 8)],
	provenance: {
		lyrics_source: 'user',
		separation_model: null,
		asr_model: null,
		align_model: null,
		engine_version: 'sample',
		language_fallbacks: []
	},
	edited: false
};

/** The moment the preview shows: half of the first line sung. */
export const SAMPLE_TIME = 2.6;
