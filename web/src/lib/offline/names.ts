/*
 * Cache names and keys shared by the page (store.ts) and the service worker, which cannot
 * import store.ts: it uses localStorage and the API client, neither of which a worker has.
 */

/** Songs saved for offline use, keyed by the same /media/... URLs the app fetches. */
export const SONGS_CACHE = 'foliada-songs-v1';

/** The app shell of one build is `foliada-app-<version>`; older ones are deleted. */
export const APP_CACHE_PREFIX = 'foliada-app-';

/** The saved songs as a /api/songs list, for the worker to answer with when offline. */
export const OFFLINE_SONGS_URL = '/offline/songs.json';
