import { describe, expect, it, vi } from 'vitest';
import type { SongSummary } from '#lib/api/types.js';
import { OFFLINE_SONGS_URL, SONGS_CACHE } from './names';
import {
	isSaved,
	offlineAvailable,
	removeSong,
	saveSong,
	savedSongs,
	storageEstimate,
	type OfflineDeps
} from './store';

const ORIGIN = 'http://localhost';
const keyOf = (request: RequestInfo | URL) =>
	new URL(request instanceof Request ? request.url : String(request), ORIGIN).href;

/** A Cache that keeps bodies in memory; `quota` makes it fail like a full disk. */
class FakeCache {
	readonly entries = new Map<string, { body: Uint8Array<ArrayBuffer>; type: string | null }>();

	constructor(private readonly quota = Infinity) {}

	used(): number {
		let total = 0;
		for (const { body } of this.entries.values()) total += body.byteLength;
		return total;
	}

	async put(request: RequestInfo | URL, response: Response): Promise<void> {
		const body = new Uint8Array(await response.arrayBuffer());
		if (this.used() + body.byteLength > this.quota) {
			throw new DOMException('The quota has been exceeded.', 'QuotaExceededError');
		}
		this.entries.set(keyOf(request), { body, type: response.headers.get('Content-Type') });
	}

	async match(request: RequestInfo | URL): Promise<Response | undefined> {
		const entry = this.entries.get(keyOf(request));
		if (!entry) return undefined;
		return new Response(entry.body, entry.type ? { headers: { 'Content-Type': entry.type } } : {});
	}

	async delete(request: RequestInfo | URL): Promise<boolean> {
		return this.entries.delete(keyOf(request));
	}

	async keys(): Promise<Request[]> {
		return [...this.entries.keys()].map((url) => new Request(url));
	}

	paths(): string[] {
		return [...this.entries.keys()].map((url) => new URL(url).pathname);
	}
}

class FakeCaches {
	readonly named = new Map<string, FakeCache>();

	constructor(private readonly quota = Infinity) {}

	async open(name: string): Promise<FakeCache> {
		let cache = this.named.get(name);
		if (!cache) {
			cache = new FakeCache(this.quota);
			this.named.set(name, cache);
		}
		return cache;
	}

	songs(): FakeCache {
		return this.named.get(SONGS_CACHE) ?? new FakeCache();
	}
}

class FakeLocalStorage {
	readonly items = new Map<string, string>();
	getItem = (key: string) => this.items.get(key) ?? null;
	setItem = (key: string, value: string) => void this.items.set(key, value);
}

const SONG: SongSummary = {
	id: 's1',
	title: 'Muiñeira',
	artist: 'Clo Plas',
	language: 'gl',
	duration: 180,
	cover: 'cover.jpg',
	has_video: true,
	created_at: '2026-10-01T10:00:00Z',
	edited: false,
	lyrics_source: 'user',
	hook: null
};

const DOC = {
	id: 's1',
	audio: { instrumental: 'instrumental.m4a', vocals: 'vocals.m4a', loudness_lufs: null },
	video: { background: 'background.mp4' },
	cover: 'cover.jpg'
};

const SIZES: Record<string, number> = {
	'instrumental.m4a': 3000,
	'vocals.m4a': 2000,
	'cover.jpg': 500,
	'background.mp4': 4000
};

/**
 * The server's /media for one song. Bodies arrive in 500-byte chunks so progress moves;
 * `fail` names files whose request fails, `lengths: false` leaves out Content-Length.
 */
function server(options: { id?: string; fail?: string[]; lengths?: boolean; doc?: unknown } = {}) {
	const { id = 's1', fail = [], lengths = true, doc = DOC } = options;
	const requested: string[] = [];
	const impl = async (input: RequestInfo | URL): Promise<Response> => {
		const url = input instanceof Request ? input.url : input.toString();
		requested.push(url);
		const prefix = `/media/${encodeURIComponent(id)}/`;
		const file = url.startsWith(prefix) ? url.slice(prefix.length) : '';
		if (fail.includes(file)) throw new TypeError('Failed to fetch');
		let body: Uint8Array<ArrayBuffer>;
		if (file === 'karaoke.json') body = new TextEncoder().encode(JSON.stringify(doc));
		else if (SIZES[file]) body = new Uint8Array(SIZES[file]).fill(7);
		else return new Response('not found', { status: 404 });
		const stream = new ReadableStream<Uint8Array>({
			start(controller) {
				for (let i = 0; i < body.byteLength; i += 500) controller.enqueue(body.slice(i, i + 500));
				controller.close();
			}
		});
		const headers = new Headers({
			'Content-Type': file.endsWith('.json') ? 'application/json' : 'application/octet-stream'
		});
		if (lengths) headers.set('Content-Length', String(body.byteLength));
		return new Response(stream, { headers });
	};
	return { requested, fetch: impl };
}

function setup(options: { quota?: number; fail?: string[]; lengths?: boolean } = {}) {
	const caches = new FakeCaches(options.quota);
	const localStorage = new FakeLocalStorage();
	const persist = vi.fn(async () => true);
	const estimate = vi.fn(async () => ({ usage: 1234, quota: 5678 }));
	const { requested, fetch } = server(options);
	const deps: Partial<OfflineDeps> = {
		caches: caches as unknown as CacheStorage,
		fetch,
		localStorage,
		storage: { persist, estimate }
	};
	return { caches, localStorage, persist, estimate, requested, deps };
}

const PACKAGE_BYTES = JSON.stringify(DOC).length + 3000 + 2000 + 500 + 4000;

describe('saving songs for offline use', () => {
	it('stores the whole package under its media URLs and lists the song', async () => {
		const { caches, deps } = setup();
		expect(await saveSong(SONG, undefined, deps)).toEqual({ ok: true });

		expect(caches.songs().paths().sort()).toEqual(
			[
				'/media/s1/background.mp4',
				'/media/s1/cover.jpg',
				'/media/s1/instrumental.m4a',
				'/media/s1/karaoke.json',
				'/media/s1/vocals.m4a',
				OFFLINE_SONGS_URL
			].sort()
		);
		const saved = savedSongs(deps);
		expect(saved).toHaveLength(1);
		expect(saved[0]).toMatchObject({ ...SONG, bytes: PACKAGE_BYTES });
		expect(Date.parse(saved[0].saved_at)).not.toBeNaN();
		expect(isSaved('s1', deps)).toBe(true);
		expect(isSaved('other', deps)).toBe(false);
	});

	it('keeps the stored files byte for byte', async () => {
		const { caches, deps } = setup();
		await saveSong(SONG, undefined, deps);
		const video = await caches.songs().match('/media/s1/background.mp4');
		expect((await video!.arrayBuffer()).byteLength).toBe(4000);
		const doc = await caches.songs().match('/media/s1/karaoke.json');
		expect(await doc!.json()).toEqual(DOC);
		expect(doc!.headers.get('Content-Type')).toBe('application/json');
	});

	it('writes the saved songs as the library list the worker answers with offline', async () => {
		const { caches, deps } = setup();
		await saveSong(SONG, undefined, deps);
		const list = await caches.songs().match(OFFLINE_SONGS_URL);
		expect(await list!.json()).toEqual([SONG]);

		await removeSong('s1', deps);
		const empty = await caches.songs().match(OFFLINE_SONGS_URL);
		expect(await empty!.json()).toEqual([]);
	});

	it('removes a song: files, list entry and offline list', async () => {
		const { caches, deps } = setup();
		await saveSong(SONG, undefined, deps);
		await removeSong('s1', deps);
		expect(caches.songs().paths()).toEqual([OFFLINE_SONGS_URL]);
		expect(savedSongs(deps)).toEqual([]);
		expect(isSaved('s1', deps)).toBe(false);
	});

	it('only removes the files of the song asked for', async () => {
		const { caches, deps } = setup();
		await saveSong(SONG, undefined, deps);
		const other = server({ id: 'a b' });
		await saveSong({ ...SONG, id: 'a b' }, undefined, { ...deps, fetch: other.fetch });
		await removeSong('a b', deps);
		expect(caches.songs().paths()).toContain('/media/s1/instrumental.m4a');
		expect(
			caches
				.songs()
				.paths()
				.some((path) => path.startsWith('/media/a%20b/'))
		).toBe(false);
		expect(savedSongs(deps).map((song) => song.id)).toEqual(['s1']);
	});

	it('reports progress by bytes that grows and ends at 1', async () => {
		const { deps } = setup();
		const steps: number[] = [];
		await saveSong(SONG, (fraction) => steps.push(fraction), deps);
		expect(steps.length).toBeGreaterThan(5);
		expect(steps.at(-1)).toBe(1);
		for (let i = 1; i < steps.length; i++) expect(steps[i]).toBeGreaterThanOrEqual(steps[i - 1]);
		expect(steps.every((step) => step >= 0 && step <= 1)).toBe(true);
	});

	it('reports progress by files when the sizes are unknown', async () => {
		const { deps } = setup({ lengths: false });
		const steps: number[] = [];
		await saveSong(SONG, (fraction) => steps.push(fraction), deps);
		// karaoke.json and then each of the four files.
		expect(steps.map((step) => Math.round(step * 100) / 100)).toEqual([0.2, 0.4, 0.6, 0.8, 1]);
	});

	it('says when the disk is full and leaves nothing behind', async () => {
		const { caches, deps } = setup({ quota: 5000 });
		expect(await saveSong(SONG, undefined, deps)).toEqual({ ok: false, reason: 'quota' });
		expect(
			caches
				.songs()
				.paths()
				.filter((path) => path.startsWith('/media/'))
		).toEqual([]);
		expect(savedSongs(deps)).toEqual([]);
		expect(isSaved('s1', deps)).toBe(false);
	});

	it('says when the network fails and leaves nothing behind', async () => {
		const { caches, deps } = setup({ fail: ['vocals.m4a'] });
		expect(await saveSong(SONG, undefined, deps)).toEqual({ ok: false, reason: 'network' });
		expect(
			caches
				.songs()
				.paths()
				.filter((path) => path.startsWith('/media/'))
		).toEqual([]);
		expect(savedSongs(deps)).toEqual([]);
	});

	it('treats a package that cannot be read as a network failure', async () => {
		const { deps } = setup();
		const broken = server({ doc: { audio: {} } });
		const result = await saveSong(SONG, undefined, { ...deps, fetch: broken.fetch });
		expect(result).toEqual({ ok: false, reason: 'network' });
	});

	it('cannot save without the Cache API (plain http) and does not try', async () => {
		const { deps, requested } = setup();
		const result = await saveSong(SONG, undefined, { ...deps, caches: null });
		expect(result).toEqual({ ok: false, reason: 'insecure' });
		expect(requested).toEqual([]);
		expect(offlineAvailable({ caches: null })).toBe(false);
	});

	it('asks for persistent storage once', async () => {
		const { deps, persist } = setup();
		await saveSong(SONG, undefined, deps);
		await saveSong({ ...SONG, id: 's1' }, undefined, deps);
		expect(persist).toHaveBeenCalledTimes(1);
	});

	it('replaces the entry when a song is saved again', async () => {
		const { deps } = setup();
		await saveSong(SONG, undefined, deps);
		await saveSong({ ...SONG, title: 'Novo' }, undefined, deps);
		expect(savedSongs(deps).map((song) => song.title)).toEqual(['Novo']);
	});
});

describe('the saved list', () => {
	it('is empty when localStorage holds something that is not a list', () => {
		for (const stored of ['{not json', '{"id":"x"}', '42', 'null']) {
			const localStorage = new FakeLocalStorage();
			localStorage.setItem('foliada.saved', stored);
			expect(savedSongs({ localStorage }), stored).toEqual([]);
		}
	});

	it('skips entries that are not songs', () => {
		const localStorage = new FakeLocalStorage();
		localStorage.setItem(
			'foliada.saved',
			JSON.stringify([{ ...SONG, bytes: 10, saved_at: 'x' }, 'junk', { id: 3 }])
		);
		expect(savedSongs({ localStorage }).map((song) => song.id)).toEqual(['s1']);
	});

	it('is empty when localStorage cannot be used', () => {
		expect(savedSongs({ localStorage: null })).toEqual([]);
		expect(isSaved('s1', { localStorage: null })).toBe(false);
	});
});

describe('storage information', () => {
	it('reads the usage and quota', async () => {
		const { deps } = setup();
		expect(await storageEstimate(deps)).toEqual({ usage: 1234, quota: 5678 });
	});

	it('is null where the browser does not tell', async () => {
		expect(await storageEstimate({ storage: null })).toBeNull();
	});

	it('knows offline saving needs a secure context with the Cache API', () => {
		const { deps } = setup();
		expect(offlineAvailable(deps)).toBe(true);
		// Node has neither, like a phone on plain http.
		expect(offlineAvailable()).toBe(false);
	});
});
