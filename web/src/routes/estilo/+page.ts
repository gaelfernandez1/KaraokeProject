import { dev } from '$app/env';
import { error } from '@sveltejs/kit';

// The living style guide is a tool for building the app, not part of it.
export function load() {
	if (!dev) error(404);
}
