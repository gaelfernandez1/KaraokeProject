/*
 * New versions of the app. SvelteKit registers the service worker itself; a new one installs
 * in the background and waits while the old one controls the open pages, so the app can offer
 * to switch at a good moment instead of reloading under a song.
 */

/** Set once the page reloads when the new worker takes control, so it reloads only once. */
let reloadOnSwitch = false;

/**
 * Calls `onUpdate` when a new version is installed and waiting, also when one already was as the
 * page loads. `apply()` hands control to it and reloads the page once it has taken over.
 * Does nothing without service workers (plain http, `vite dev` before the first install).
 */
export function watchForUpdate(onUpdate: (apply: () => void) => void): void {
	if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
	const container = navigator.serviceWorker;

	// `ready` rather than getRegistration(): SvelteKit registers on `load`, so on a first visit
	// there is nothing to find yet, and later versions can still arrive in this session.
	container.ready
		.then((registration) => {
			const apply = () => {
				if (!reloadOnSwitch) {
					reloadOnSwitch = true;
					container.addEventListener('controllerchange', () => location.reload(), { once: true });
				}
				const waiting = registration.waiting;
				// Another tab may have switched already: then this page only needs the reload.
				if (waiting) waiting.postMessage({ type: 'skip-waiting' });
				else location.reload();
			};

			// Without a controller this is the first install, not an update.
			if (registration.waiting && container.controller) onUpdate(apply);
			registration.addEventListener('updatefound', () => {
				const worker = registration.installing;
				worker?.addEventListener('statechange', () => {
					if (worker.state === 'installed' && container.controller) onUpdate(apply);
				});
			});
		})
		.catch(() => {
			// No usable registration: the app simply never offers an update.
		});
}
