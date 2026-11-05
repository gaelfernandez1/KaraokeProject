/*
 * What the web app exchanges with the karaoke server. Hand-written until the server publishes
 * its OpenAPI description; then these become generated types with the same names.
 */

export type LyricsSource = 'user' | 'asr' | 'lrclib';

/** A song in the library, without its lyrics. */
export interface SongSummary {
	id: string;
	title: string;
	artist: string | null;
	language: string;
	/** Seconds. */
	duration: number;
	/** File name of the cover inside the package, if it has one. */
	cover: string | null;
	has_video: boolean;
	/** ISO 8601. */
	created_at: string;
	edited: boolean;
	lyrics_source: LyricsSource;
	/** The line sung most often (the chorus hook), else the first full line; for the poster. */
	hook: string | null;
}

export type JobStage =
	| 'queued'
	| 'download'
	| 'separate'
	| 'transcribe'
	| 'align'
	| 'audio'
	| 'video'
	| 'done'
	| 'error'
	| 'cancelled';

export interface Job {
	id: string;
	/** `make` turns a song into a karaoke; `export` renders its MP4. */
	kind: 'make' | 'export';
	/** The song's title, as given or guessed from the file name. */
	title: string;
	stage: JobStage;
	/** How far the current stage has gone, 0–1. */
	progress: number;
	/** Set when a `make` job is done. */
	song_id: string | null;
	/** Set when an `export` job is done: the MP4's file name inside the song's package. */
	file: string | null;
	error: string | null;
	/** Whether the song came with lyrics (the transcription stage is skipped). */
	with_lyrics: boolean;
	/** ISO 8601. */
	created_at: string;
}

export interface CreateJobInput {
	file?: File;
	url?: string;
	language: string;
	lyrics?: string;
	lrclib?: boolean;
	title?: string;
	artist?: string;
}

export interface ExportInput {
	aspect: '16:9' | '9:16';
	theme: string;
}

export interface ServerInfo {
	/** Address of the server on the home network, for the party QR code. */
	url: string;
}
