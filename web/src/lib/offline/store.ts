/*
 * Songs saved for offline use. Their files go to Cache Storage under the same /media/... URLs
 * the app fetches, so the service worker answers them with no change to the player; the list
 * of saved songs lives in localStorage. Without a secure context (a phone on plain http) there
 * is no Cache API: everything here then reports it instead of throwing.
 */
import { mediaUrl } from '#lib/api/client.js';
import type { SongSummary } from '#lib/api/types.js';
import { OFFLINE_SONGS_URL, SONGS_CACHE } from './names';

export interface SavedSong extends SongSummary {
	/** What the song takes on the device. */
	bytes: number;
	/** ISO 8601. */
	saved_at: string;
}

export type SaveResult = { ok: true } | { ok: false; reason: 'insecure' | 'quota' | 'network' };

/** The browser features used here; tests pass their own. */
export interface OfflineDeps {
	caches: CacheStorage | null;
	fetch: typeof fetch;
	localStorage: Pick<Storage, 'getItem' | 'setItem'> | null;
	storage: Partial<Pick<StorageManager, 'persist' | 'estimate'>> | null;
}

const SAVED_KEY = 'foliada.saved';

function browserLocalStorage(): OfflineDeps['localStorage'] {
	try {
		return globalThis.localStorage ?? null;
	} catch {
		// Thrown when the browser blocks site data.
		return null;
	}
}

function resolveDeps(deps: Partial<OfflineDeps>): OfflineDeps {
	// Looked up on each call, never at import time: on plain http some of these are missing.
	const scope = globalThis as typeof globalThis & { caches?: CacheStorage };
	return {
		caches:
			'caches' in deps
				? (deps.caches ?? null)
				: scope.isSecureContext && scope.caches
					? scope.caches
					: null,
		fetch: deps.fetch ?? ((input, init) => fetch(input, init)),
		localStorage: 'localStorage' in deps ? (deps.localStorage ?? null) : browserLocalStorage(),
		storage:
			'storage' in deps
				? (deps.storage ?? null)
				: typeof navigator !== 'undefined'
					? (navigator.storage ?? null)
					: null
	};
}

/** Whether songs can be saved here: it takes a secure context with the Cache API. */
export function offlineAvailable(deps: Partial<OfflineDeps> = {}): boolean {
	return resolveDeps(deps).caches !== null;
}

function isSavedSong(value: unknown): value is SavedSong {
	if (typeof value !== 'object' || value === null) return false;
	const song = value as Partial<SavedSong>;
	return typeof song.id === 'string' && typeof song.bytes === 'number';
}

function readSaved(local: OfflineDeps['localStorage']): SavedSong[] {
	try {
		const parsed: unknown = JSON.parse(local?.getItem(SAVED_KEY) ?? '[]');
		return Array.isArray(parsed) ? parsed.filter(isSavedSong) : [];
	} catch {
		return [];
	}
}

function writeSaved(local: OfflineDeps['localStorage'], songs: SavedSong[]): void {
	try {
		local?.setItem(SAVED_KEY, JSON.stringify(songs));
	} catch {
		// Blocked or full: the files stay cached, only the list is not kept.
	}
}

export function savedSongs(deps: Partial<OfflineDeps> = {}): SavedSong[] {
	return readSaved(resolveDeps(deps).localStorage);
}

export function isSaved(id: string, deps: Partial<OfflineDeps> = {}): boolean {
	return savedSongs(deps).some((song) => song.id === id);
}

function summary(saved: SavedSong): SongSummary {
	const song: Partial<SavedSong> = { ...saved };
	delete song.bytes;
	delete song.saved_at;
	return song as SongSummary;
}

let listWrite: Promise<void> = Promise.resolve();

/**
 * Stores the saved songs as the /api/songs answer the worker gives offline. Writes run one
 * after another and read the list when they run, so the last one always wins with fresh data.
 */
function publishList(cache: Cache, local: OfflineDeps['localStorage']): Promise<void> {
	listWrite = listWrite
		.then(() =>
			cache.put(
				OFFLINE_SONGS_URL,
				new Response(JSON.stringify(readSaved(local).map(summary)), {
					headers: { 'Content-Type': 'application/json' }
				})
			)
		)
		.catch(() => {
			// The library just shows fewer songs offline.
		});
	return listWrite;
}

/** Deletes every cached file of a song (whatever its package held). */
async function clearSong(cache: Cache, id: string): Promise<void> {
	const prefix = mediaUrl(id, '');
	const keys = await cache.keys();
	await Promise.all(
		keys
			.filter((request) => new URL(request.url).pathname.startsWith(prefix))
			.map((request) => cache.delete(request))
	);
}

const persistAsked = new WeakSet<object>();

/** Asks once for storage the browser will not evict under pressure; Firefox may prompt. */
function askPersistence(storage: OfflineDeps['storage']): void {
	if (!storage?.persist || persistAsked.has(storage)) return;
	persistAsked.add(storage);
	storage.persist().catch(() => {
		// Refused: the songs stay, but the browser may clear them when the disk is short.
	});
}

/** The package files besides karaoke.json, read from the song's document. */
function packageFiles(doc: unknown, song: SongSummary): string[] {
	const { audio, video, cover } = (doc ?? {}) as {
		audio?: { instrumental?: unknown; vocals?: unknown };
		video?: { background?: unknown } | null;
		cover?: unknown;
	};
	if (typeof audio?.instrumental !== 'string') throw new Error('karaoke.json names no audio');
	const files = [audio.instrumental, audio.vocals, cover, video?.background, song.cover];
	return [
		...new Set(files.filter((f): f is string => typeof f === 'string' && f !== 'karaoke.json'))
	];
}

async function fetchOk(fetchImpl: typeof fetch, url: string, signal: AbortSignal) {
	const response = await fetchImpl(url, { signal });
	if (!response.ok) throw new Error(`${url}: ${response.status}`);
	return response;
}

/** The size the server announces, unless the body is compressed (then it is not what we get). */
function announcedSize(response: Response): number | null {
	const value = response.headers.get('Content-Length');
	if (value === null || response.headers.has('Content-Encoding')) return null;
	const size = Number(value);
	return Number.isFinite(size) && size >= 0 ? size : null;
}

/** Only the type is kept: lengths and encodings no longer match a decoded, stored body. */
function storedHeaders(response: Response): HeadersInit {
	const type = response.headers.get('Content-Type');
	return type ? { 'Content-Type': type } : {};
}

/** Downloads and stores a song's package; returns the bytes stored. */
async function download(
	song: SongSummary,
	cache: Cache,
	fetchImpl: typeof fetch,
	controller: AbortController,
	onProgress: (fraction: number) => void
): Promise<number> {
	let reported = 0;
	const report = (fraction: number) => {
		const clamped = Math.min(1, fraction);
		if (clamped > reported) onProgress((reported = clamped));
	};

	const docUrl = mediaUrl(song.id, 'karaoke.json');
	const docResponse = await fetchOk(fetchImpl, docUrl, controller.signal);
	const docBody = await docResponse.arrayBuffer();
	const files = packageFiles(JSON.parse(new TextDecoder().decode(docBody)), song);
	await cache.put(docUrl, new Response(docBody, { headers: storedHeaders(docResponse) }));

	// Fetched together so all the sizes are known before counting bytes against them.
	const responses = await Promise.all(
		files.map((file) => fetchOk(fetchImpl, mediaUrl(song.id, file), controller.signal))
	);
	const sizes = responses.map(announcedSize);
	const total = sizes.every((size) => size !== null)
		? sizes.reduce((sum: number, size) => sum + (size ?? 0), docBody.byteLength)
		: null;
	let loaded = docBody.byteLength;
	let done = 1;
	const update = () => report(total ? loaded / total : done / (files.length + 1));
	update();

	let failure: { error: unknown } | null = null;
	const stores = responses.map(async (response, i) => {
		let size = 0;
		// Counted as it flows into the cache, so progress follows what is really stored.
		const counter = new TransformStream<Uint8Array, Uint8Array>({
			transform(chunk, stream) {
				size += chunk.byteLength;
				loaded += chunk.byteLength;
				if (total) update();
				stream.enqueue(chunk);
			}
		});
		const body = response.body ? response.body.pipeThrough(counter) : null;
		await cache.put(
			mediaUrl(song.id, files[i]),
			new Response(body, { headers: storedHeaders(response) })
		);
		done += 1;
		update();
		return size;
	});
	for (const store of stores) {
		store.catch((error: unknown) => {
			// The first error is the real one; aborting the rest makes theirs AbortErrors.
			failure ??= { error };
			controller.abort();
		});
	}
	const results = await Promise.allSettled(stores);
	if (failure) throw (failure as { error: unknown }).error;
	return results.reduce(
		(sum, result) => sum + (result.status === 'fulfilled' ? result.value : 0),
		docBody.byteLength
	);
}

function isQuotaError(error: unknown): boolean {
	const name = (error as { name?: unknown } | null)?.name;
	const code = (error as { code?: unknown } | null)?.code;
	return name === 'QuotaExceededError' || code === 22;
}

/**
 * Downloads a song's package (lyrics, audio, cover and background video) for offline use.
 * `onProgress` gets 0–1, by bytes when the server gives sizes, else by files. On failure
 * nothing of the song is left stored.
 */
export async function saveSong(
	song: SongSummary,
	onProgress?: (fraction: number) => void,
	deps: Partial<OfflineDeps> = {}
): Promise<SaveResult> {
	const resolved = resolveDeps(deps);
	if (!resolved.caches) return { ok: false, reason: 'insecure' };
	askPersistence(resolved.storage);

	let cache: Cache;
	try {
		cache = await resolved.caches.open(SONGS_CACHE);
	} catch {
		// Firefox private windows have `caches` but refuse to open them.
		return { ok: false, reason: 'insecure' };
	}

	const controller = new AbortController();
	try {
		const bytes = await download(song, cache, resolved.fetch, controller, onProgress ?? (() => {}));
		const others = readSaved(resolved.localStorage).filter((saved) => saved.id !== song.id);
		writeSaved(resolved.localStorage, [
			...others,
			{ ...song, bytes, saved_at: new Date().toISOString() }
		]);
		await publishList(cache, resolved.localStorage);
		return { ok: true };
	} catch (error) {
		controller.abort();
		await removeSong(song.id, deps);
		return { ok: false, reason: isQuotaError(error) ? 'quota' : 'network' };
	}
}

/** Deletes a saved song from the device (the server keeps it). */
export async function removeSong(id: string, deps: Partial<OfflineDeps> = {}): Promise<void> {
	const resolved = resolveDeps(deps);
	const saved = readSaved(resolved.localStorage);
	if (saved.some((song) => song.id === id)) {
		writeSaved(
			resolved.localStorage,
			saved.filter((song) => song.id !== id)
		);
	}
	if (!resolved.caches) return;
	try {
		const cache = await resolved.caches.open(SONGS_CACHE);
		await clearSong(cache, id);
		await publishList(cache, resolved.localStorage);
	} catch {
		// Nothing could be stored here either.
	}
}

/** How much the site stores and may store, in bytes; null where the browser does not say. */
export async function storageEstimate(
	deps: Partial<OfflineDeps> = {}
): Promise<{ usage: number; quota: number } | null> {
	const { storage } = resolveDeps(deps);
	if (!storage?.estimate) return null;
	try {
		const { usage = 0, quota = 0 } = await storage.estimate();
		return { usage, quota };
	} catch {
		return null;
	}
}
