import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { mockApi } from './dev/mock/plugin.ts';

const ROOT = resolve(fileURLToPath(new URL('.', import.meta.url)), '..');
// With KARAOKE_SERVER=http://127.0.0.1:8765, `pnpm dev` talks to the real server instead of the
// stand-in (SSE and Range go through the proxy as they are).
const SERVER = process.env.KARAOKE_SERVER;

export default defineConfig({
	// The lyrics themes and fonts live in the Python package, outside web/.
	server: {
		fs: { allow: [ROOT] },
		proxy: SERVER
			? {
					'/api': { target: SERVER, changeOrigin: false },
					'/media': { target: SERVER, changeOrigin: false }
				}
			: undefined
	},
	plugins: [
		// Dev server only: a stand-in for the karaoke server's /api and /media.
		...(SERVER ? [] : [mockApi()]),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter({ fallback: 'index.html' })
		})
	],
	test: {
		expect: { requireAssertions: true },
		projects: [
			{
				extends: './vite.config.ts',
				test: {
					name: 'server',
					environment: 'node',
					include: ['src/**/*.{test,spec}.{js,ts}', 'dev/**/*.test.ts'],
					exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
				}
			}
		]
	}
});
