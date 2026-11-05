import { dev } from '$app/env';
import { error } from '@sveltejs/kit';

// A test page for the lyrics component (its browser tests use it), not part of the app.
export function load() {
	if (!dev) error(404);
}
