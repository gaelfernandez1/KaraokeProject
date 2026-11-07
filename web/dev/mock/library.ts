import { readdirSync, readFileSync, statSync } from 'node:fs';
import { extname, resolve, sep } from 'node:path';
import type { Export, SongSummary } from '../../src/lib/api/types.ts';
import type { KaraokeDoc } from '../../src/lib/contracts/generated/karaoke.ts';
import { hookOf } from '../../src/lib/poster/hook.ts';

/** Media types the mock serves from a package folder. */
export const MEDIA_TYPES: Record<string, string> = {
	'.json': 'application/json',
	'.m4a': 'audio/mp4',
	'.wav': 'audio/wav',
	'.mp4': 'video/mp4',
	'.jpg': 'image/jpeg',
	'.png': 'image/png',
	'.webp': 'image/webp'
};

interface Virtual {
	/** The real package whose media it reuses. */
	source: string;
	doc: KaraokeDoc;
	created: string;
}

/**
 * The song library of the dev server: the package folders on disk plus songs "made" by the mock
 * jobs (which reuse a real package's media). Edits and deletions live in memory only: the mock
 * never writes to the packages.
 */
export class Library {
	readonly dirs: string[];
	readonly #virtual = new Map<string, Virtual>();
	readonly #edited = new Map<string, KaraokeDoc>();
	readonly #deleted = new Set<string>();
	/** Videos "made" by the mock export jobs (it cannot render: it serves stand-ins). */
	readonly #exports = new Map<string, Export[]>();
	readonly #editedAt = new Map<string, string>();

	constructor(dirs: string[]) {
		this.dirs = dirs;
	}

	/** Package folder of a song on disk (for a made song, the folder whose media it uses). */
	find(id: string): string | undefined {
		if (this.#deleted.has(id)) return undefined;
		const virtual = this.#virtual.get(id);
		if (virtual) return this.find(virtual.source);
		for (const dir of this.dirs) {
			const folder = resolve(dir, id);
			if (!folder.startsWith(dir + sep)) continue;
			try {
				if (statSync(resolve(folder, 'karaoke.json')).isFile()) return folder;
			} catch {
				// Not in this folder.
			}
		}
		return undefined;
	}

	doc(id: string): KaraokeDoc | undefined {
		if (this.#deleted.has(id)) return undefined;
		const edited = this.#edited.get(id) ?? this.#virtual.get(id)?.doc;
		if (edited) return edited;
		const folder = this.find(id);
		if (!folder) return undefined;
		return JSON.parse(readFileSync(resolve(folder, 'karaoke.json'), 'utf8')) as KaraokeDoc;
	}

	list(): SongSummary[] {
		const ids = new Set<string>(this.#virtual.keys());
		for (const dir of this.dirs) {
			let names: string[];
			try {
				names = readdirSync(dir);
			} catch {
				continue;
			}
			for (const name of names) if (this.find(name)) ids.add(name);
		}
		return [...ids].flatMap((id) => {
			const summary = this.summary(id);
			return summary ? [summary] : [];
		});
	}

	summary(id: string): SongSummary | undefined {
		const doc = this.doc(id);
		if (!doc) return undefined;
		const virtual = this.#virtual.get(id);
		let created = virtual?.created;
		if (!created) {
			const folder = this.find(id) as string;
			created = statSync(resolve(folder, 'karaoke.json')).mtime.toISOString();
		}
		return {
			id,
			title: doc.title,
			artist: doc.artist,
			language: doc.language,
			duration: doc.duration,
			cover: doc.cover ?? null,
			has_video: Boolean(doc.video?.background),
			created_at: created,
			edited: doc.edited,
			lyrics_source: doc.provenance.lyrics_source,
			hook: hookOf(doc)
		};
	}

	/** Path of a media file of a song, or undefined if there is no such file to serve. */
	filePath(id: string, file: string): string | undefined {
		const folder = this.find(id);
		if (!folder || !MEDIA_TYPES[extname(file)]) return undefined;
		const path = resolve(folder, file);
		if (!path.startsWith(folder + sep)) return undefined;
		try {
			return statSync(path).isFile() ? path : undefined;
		} catch {
			return undefined;
		}
	}

	/** A new song that reuses the media of `source`; returns its id. */
	addVirtual(
		source: string,
		info: {
			title: string;
			artist: string | null;
			language: string;
			lyricsSource: 'user' | 'asr' | 'lrclib';
		}
	): string {
		const base = this.doc(source);
		if (!base) throw new Error(`no package ${source} to copy`);
		const slug =
			info.title
				.normalize('NFD')
				.replace(/\p{M}/gu, '')
				.toLowerCase()
				.replace(/[^a-z0-9]+/g, '-')
				.replace(/^-|-$/g, '') || 'cancion';
		let id = slug;
		for (let n = 2; this.doc(id); n++) id = `${slug}-${n}`;
		this.#virtual.set(id, {
			source,
			created: new Date().toISOString(),
			doc: {
				...base,
				id,
				title: info.title,
				artist: info.artist,
				language: info.language,
				provenance: { ...base.provenance, lyrics_source: info.lyricsSource }
			}
		});
		return id;
	}

	saveDoc(id: string, doc: KaraokeDoc): KaraokeDoc {
		const saved = { ...doc, id, edited: true };
		this.#edited.set(id, saved);
		this.#editedAt.set(id, new Date(Date.now() + 1).toISOString());
		return saved;
	}

	/** The song's videos, newest first, like GET /api/songs/{id}/exports. */
	exports(id: string): Export[] {
		const edited = this.#editedAt.get(id);
		return (this.#exports.get(id) ?? []).map((video) => ({
			...video,
			outdated: Boolean(edited && edited > video.created_at)
		}));
	}

	/** Records a finished video; one per shape, style and vocals level, like the server. */
	addExport(id: string, aspect: Export['aspect'], theme: string, vocals = 0): string {
		const level = vocals > 0 ? `-v${Math.round(vocals * 100)}` : '';
		const file = `exports/${id}-${aspect.replace(':', 'x')}-${theme}${level}.mp4`;
		const others = (this.#exports.get(id) ?? []).filter((video) => video.file !== file);
		const video: Export = {
			file,
			aspect,
			theme,
			size: 48_000_000,
			created_at: new Date().toISOString(),
			thumbnail: null,
			outdated: false,
			vocals
		};
		this.#exports.set(id, [video, ...others]);
		return file;
	}

	deleteExport(id: string, name: string): boolean {
		const videos = this.#exports.get(id) ?? [];
		const left = videos.filter((video) => video.file !== `exports/${name}`);
		this.#exports.set(id, left);
		return left.length < videos.length;
	}

	/** What the mock serves for a video: the song's background if it has one, else nothing. */
	exportFile(id: string, file: string): string | undefined {
		if (!this.#exports.get(id)?.some((video) => video.file === file)) return undefined;
		const background = this.doc(id)?.video?.background;
		return background ? this.filePath(id, background) : undefined;
	}

	delete(id: string): boolean {
		if (!this.doc(id)) return false;
		this.#deleted.add(id);
		return true;
	}
}
