/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

export interface KaraokeDoc {
	schema_version: string;
	id: string;
	title: string;
	artist: string | null;
	language: string;
	duration: number;
	audio: AudioRefs;
	video: VideoRefs | null;
	cover: string | null;
	singers: Singer[];
	lines: Line[];
	provenance: Provenance;
	edited: boolean;
}
export interface AudioRefs {
	instrumental: string;
	vocals: string | null;
	loudness_lufs: number | null;
}
export interface VideoRefs {
	background: string | null;
}
export interface Singer {
	id: string;
	name: string | null;
	color: string | null;
}
export interface Line {
	id: string;
	/**
	 * Seconds from the start of the song audio.
	 */
	start: number;
	/**
	 * Seconds from the start of the song audio.
	 */
	end: number;
	singer: string | null;
	/**
	 * @minItems 1
	 */
	words: Word[];
}
export interface Word {
	/**
	 * Text as displayed, with its original spelling.
	 */
	text: string;
	/**
	 * Seconds from the start of the song audio.
	 */
	start: number;
	/**
	 * Seconds from the start of the song audio.
	 */
	end: number;
	confidence: number | null;
	/**
	 * Optional sub-units; when present their texts concatenate to the word text.
	 */
	parts: Part[];
}
/**
 * A sub-unit of a word (a syllable or a group of letters) with its own timing.
 */
export interface Part {
	text: string;
	/**
	 * Seconds from the start of the song audio.
	 */
	start: number;
	/**
	 * Seconds from the start of the song audio.
	 */
	end: number;
}
export interface Provenance {
	lyrics_source: 'user' | 'asr' | 'lrclib';
	separation_model: string | null;
	asr_model: string | null;
	align_model: string | null;
	engine_version: string;
	language_fallbacks: LanguageFallback[];
}
/**
 * Records that a step could not use a resource for the requested language.
 */
export interface LanguageFallback {
	step: string;
	requested: string;
	used: string;
	reason: string;
}
