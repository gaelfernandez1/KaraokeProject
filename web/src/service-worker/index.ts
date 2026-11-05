/*
 * The app's offline side. Each build precaches its shell; songs saved with
 * #lib/offline/store.ts are answered from their own cache, with byte ranges for <video>; the
 * rest of the API goes to the network untouched. During `vite dev` it does nothing, so the
 * dev server and the browser tests see every request.
 */
import { self } from '$app/service-worker';
import { dev, version } from '$app/env';
import { assets, immutable } from '$app/manifest';
import { resolve } from '$app/paths';
import { APP_CACHE_PREFIX, OFFLINE_SONGS_URL, SONGS_CACHE } from '#lib/offline/names.js';
import { rangeResponse } from '#lib/offline/range.js';

const APP_CACHE = APP_CACHE_PREFIX + version;
/** The base path with its trailing slash; the manifest's paths are relative to it. */
const ROOT = resolve('');
/** The SPA page that answers every route (adapter-static's fallback). */
const SHELL = ROOT + 'index.html';
/** Build output and static files, as the pathnames the page will ask for. */
const PRECACHED = new Set(
	[...immutable, ...assets].map(({ path }) => new URL(ROOT + path, self.location.href).pathname)
);
/**
 * How long to wait for the server before answering from the device. Away from home an
 * unreachable server can take a minute to fail, while at home it answers in milliseconds.
 */
const NETWORK_TIMEOUT_MS = 4000;

function within<T>(promise: Promise<T>, ms: number): Promise<T> {
	return new Promise((resolve, reject) => {
		const timer = setTimeout(() => reject(new Error('The server did not answer in time')), ms);
		promise.then(resolve, reject).finally(() => clearTimeout(timer));
	});
}

/** A copy fit to store: a redirected response cannot answer a navigation, and only the type matters. */
async function storable(response: Response): Promise<Response> {
	const type = response.headers.get('Content-Type');
	return new Response(await response.blob(), type ? { headers: { 'Content-Type': type } } : {});
}

async function fetchShell(): Promise<Response> {
	// `vite preview` has no index.html and renders the page at the root instead.
	for (const url of [SHELL, ROOT]) {
		const response = await fetch(new Request(url, { cache: 'reload' }));
		if (response.ok) return storable(response);
	}
	throw new Error('The app shell could not be fetched');
}

async function precache(): Promise<void> {
	const cache = await caches.open(APP_CACHE);
	// `reload` skips the HTTP cache, so a new build never stores a file left from an older one.
	await cache.addAll([...PRECACHED].map((path) => new Request(path, { cache: 'reload' })));
	await cache.put(SHELL, await fetchShell());
}

async function cleanUp(): Promise<void> {
	// Saved songs (SONGS_CACHE) outlive every version of the app.
	for (const name of await caches.keys()) {
		if (name.startsWith(APP_CACHE_PREFIX) && name !== APP_CACHE) await caches.delete(name);
	}
	// On a first visit, take the open page too: a song saved right away then plays offline.
	await self.clients.claim();
}

/** Network first, so a new version is seen; the cached shell when there is none. */
async function navigate(request: Request): Promise<Response> {
	try {
		return await within(fetch(request), NETWORK_TIMEOUT_MS);
	} catch {
		const shell = await (await caches.open(APP_CACHE)).match(SHELL);
		return shell ?? Response.error();
	}
}

/** Saved songs from the device (the files do not change); the rest from the server. */
async function media(request: Request, url: URL): Promise<Response> {
	const songs = await caches.open(SONGS_CACHE);
	const stored = await songs.match(request.url, { ignoreVary: true });
	if (!stored) return fetch(request);
	if (url.pathname.endsWith('/karaoke.json')) return freshDoc(request, songs, stored);
	return rangeResponse(stored, request.headers.get('Range'));
}

/** Lyrics may be corrected after saving: the server's copy wins and refreshes the saved one. */
async function freshDoc(request: Request, songs: Cache, stored: Response): Promise<Response> {
	try {
		const response = await within(fetch(request), NETWORK_TIMEOUT_MS);
		if (!response.ok) return stored;
		await songs.put(request.url, await storable(response.clone()));
		return response;
	} catch {
		return stored;
	}
}

/** The server's library; without it, the songs saved on this device. */
async function songList(request: Request): Promise<Response> {
	const network = fetch(request);
	const saved = await (await caches.open(SONGS_CACHE)).match(OFFLINE_SONGS_URL);
	if (!saved) return network;
	try {
		return await within(network, NETWORK_TIMEOUT_MS);
	} catch {
		network.catch(() => {
			// Already answered with the saved list.
		});
		return saved;
	}
}

async function fromApp(request: Request): Promise<Response> {
	// One copy per URL: `Vary: Origin` (sent by vite preview and CORS middleware) must not make
	// a module script, which carries an Origin header, miss the copy stored without one.
	const cached = await (await caches.open(APP_CACHE)).match(request, { ignoreVary: true });
	return cached ?? fetch(request);
}

function onFetch(event: FetchEvent): void {
	const { request } = event;
	if (request.method !== 'GET') return;
	const url = new URL(request.url);
	if (url.origin !== self.location.origin) return;
	const isMedia = url.pathname.startsWith('/media/');
	const isApi = url.pathname.startsWith('/api/');

	if (request.mode === 'navigate') {
		// Opening a media file or an API URL directly (a download) is not an app page.
		if (!isMedia && !isApi) event.respondWith(navigate(request));
	} else if (isMedia) event.respondWith(media(request, url));
	else if (url.pathname === '/api/songs') event.respondWith(songList(request));
	else if (PRECACHED.has(url.pathname)) event.respondWith(fromApp(request));
	// Anything else (the rest of the API, live job events) goes to the network as usual.
}

if (!dev) {
	self.addEventListener('install', (event) => event.waitUntil(precache()));
	self.addEventListener('activate', (event) => event.waitUntil(cleanUp()));
	self.addEventListener('fetch', onFetch);
}

// A new version waits until the page asks for it (#lib/offline/register.ts), so a song that
// is playing is never cut by a reload.
self.addEventListener('message', (event) => {
	if ((event.data as { type?: unknown } | null)?.type === 'skip-waiting') void self.skipWaiting();
});
