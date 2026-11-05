import type { CreateJobInput } from '#lib/api';

/** Largest upload the server takes (a long concert video). */
export const MAX_BYTES = 2_000_000_000;

const MEDIA_EXTENSIONS = new Set([
	'mp3',
	'm4a',
	'aac',
	'wav',
	'flac',
	'ogg',
	'oga',
	'opus',
	'wma',
	'aiff',
	'aif',
	'mp4',
	'm4v',
	'mkv',
	'webm',
	'mov',
	'avi'
]);

export interface CreateForm {
	file: File | null;
	url: string;
	language: string;
	lyrics: string;
	lrclib: boolean;
	title: string;
	artist: string;
}

/** Message keys of `create` in the dictionaries. */
export type CreateError =
	'errorSourceMissing' | 'errorSourceBoth' | 'errorUrl' | 'errorFile' | 'errorFileSize';

export type Validation = { ok: true; value: CreateJobInput } | { ok: false; error: CreateError };

function isMedia(file: File): boolean {
	if (file.type.startsWith('audio/') || file.type.startsWith('video/')) return true;
	const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
	return file.name.includes('.') && MEDIA_EXTENSIONS.has(extension);
}

function isWebLink(text: string): boolean {
	try {
		const url = new URL(text);
		return url.protocol === 'http:' || url.protocol === 'https:';
	} catch {
		return false;
	}
}

/** Checks the create form and turns it into the job request the server takes. */
export function validateCreate(form: CreateForm): Validation {
	const url = form.url.trim();
	if (!form.file && !url) return { ok: false, error: 'errorSourceMissing' };
	if (form.file && url) return { ok: false, error: 'errorSourceBoth' };
	if (url && !isWebLink(url)) return { ok: false, error: 'errorUrl' };
	if (form.file && !isMedia(form.file)) return { ok: false, error: 'errorFile' };
	if (form.file && form.file.size > MAX_BYTES) return { ok: false, error: 'errorFileSize' };
	const lyrics = form.lyrics.trim();
	const value: CreateJobInput = { language: form.language, lrclib: !lyrics && form.lrclib };
	if (form.file) value.file = form.file;
	if (url) value.url = url;
	if (lyrics) value.lyrics = lyrics;
	if (form.title.trim()) value.title = form.title.trim();
	if (form.artist.trim()) value.artist = form.artist.trim();
	return { ok: true, value };
}

/** Title and artist from a file name like "Artist - Title (Official Video).mp4". */
export function guessTitle(fileName: string): { title: string; artist: string | null } {
	const base = fileName
		.replace(/\.[^.]+$/, '')
		.replace(/[_]+/g, ' ')
		.replace(/\s*[([](official|oficial|video|vídeo|audio|lyrics?|letra)[^)\]]*[)\]]/gi, '')
		.replace(/\s+/g, ' ')
		.trim();
	const match = /^(.+?)\s+[-–—]\s+(.+)$/.exec(base);
	return match
		? { title: match[2].trim(), artist: match[1].trim() }
		: { title: base, artist: null };
}
