/*
 * Browser features the player uses where they exist. Each one does nothing where it is missing
 * (older browsers, or a phone on plain http).
 */

/** Keeps the screen on (Wake Lock) until the returned function is called. */
export function keepAwake(): () => void {
	const wakeLock = (
		navigator as Navigator & { wakeLock?: { request(type: 'screen'): Promise<WakeLockSentinel> } }
	).wakeLock;
	if (!wakeLock) return () => {};
	let sentinel: WakeLockSentinel | null = null;
	let active = true;
	const acquire = () => {
		if (!active || document.visibilityState !== 'visible') return;
		wakeLock
			.request('screen')
			.then((s) => {
				if (active) sentinel = s;
				else void s.release();
			})
			.catch(() => {
				// Refused (battery saver, insecure context): the screen may sleep.
			});
	};
	// The lock goes when the page is hidden; take it again when it comes back.
	const onVisibility = () => acquire();
	document.addEventListener('visibilitychange', onVisibility);
	acquire();
	return () => {
		active = false;
		document.removeEventListener('visibilitychange', onVisibility);
		void sentinel?.release();
		sentinel = null;
	};
}

interface MediaHandlers {
	play(): void;
	pause(): void;
	previous(): void;
	next(): void;
	seek(seconds: number): void;
}

/**
 * Title and artwork for the lock screen and the media keys, and what those keys do. Returns a
 * function that clears them.
 */
export function setMediaSession(
	meta: { title: string; artist: string | null; artwork: string | null },
	handlers: MediaHandlers
): () => void {
	if (!('mediaSession' in navigator)) return () => {};
	const session = navigator.mediaSession;
	session.metadata = new MediaMetadata({
		title: meta.title,
		artist: meta.artist ?? '',
		artwork: meta.artwork ? [{ src: meta.artwork }] : []
	});
	const actions: [MediaSessionAction, MediaSessionActionHandler][] = [
		['play', () => handlers.play()],
		['pause', () => handlers.pause()],
		['previoustrack', () => handlers.previous()],
		['nexttrack', () => handlers.next()],
		['seekto', (details) => details.seekTime !== undefined && handlers.seek(details.seekTime)]
	];
	for (const [action, handler] of actions) {
		try {
			session.setActionHandler(action, handler);
		} catch {
			// Some browsers do not know every action.
		}
	}
	return () => {
		session.metadata = null;
		for (const [action] of actions) {
			try {
				session.setActionHandler(action, null);
			} catch {
				// As above.
			}
		}
	};
}

export function isFullscreen(): boolean {
	return document.fullscreenElement !== null;
}

/** Fullscreen on and off for an element; false where the browser does not allow it (iPhone). */
export async function toggleFullscreen(element: HTMLElement): Promise<boolean> {
	try {
		if (document.fullscreenElement) await document.exitFullscreen();
		else if (element.requestFullscreen) await element.requestFullscreen({ navigationUI: 'hide' });
		else return false;
		return true;
	} catch {
		return false;
	}
}

export const canFullscreen = (): boolean =>
	typeof document !== 'undefined' && document.fullscreenEnabled === true;
