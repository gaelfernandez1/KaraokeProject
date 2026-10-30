import { createReadStream, readdirSync, statSync } from 'node:fs';
import { extname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Plugin } from 'vite';
import { defineConfig } from 'vitest/config';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';

const ROOT = resolve(fileURLToPath(new URL('.', import.meta.url)), '..');
/** Versioned example packages, then local ones (bench/data is never versioned). */
const PACKAGE_DIRS = [resolve(ROOT, 'fixtures/packages'), resolve(ROOT, 'bench/data/paquetes')];
const TYPES: Record<string, string> = {
	'.json': 'application/json',
	'.m4a': 'audio/mp4',
	'.wav': 'audio/wav'
};

function packageIds(): string[] {
	return PACKAGE_DIRS.flatMap((dir) => {
		try {
			return readdirSync(dir).filter((id) => statSync(resolve(dir, id, 'karaoke.json')).isFile());
		} catch {
			return [];
		}
	});
}

/** Dev server only: packages under /paquetes/ (and their list) for the audio test page. */
function servePackages(): Plugin {
	return {
		name: 'serve-example-packages',
		configureServer(server) {
			server.middlewares.use('/paquetes', (req, res, next) => {
				const url = decodeURIComponent((req.url ?? '').split('?')[0]);
				if (url === '/index.json') {
					res.setHeader('Content-Type', 'application/json');
					res.end(JSON.stringify(packageIds()));
					return;
				}
				for (const dir of PACKAGE_DIRS) {
					const path = resolve(dir, '.' + url);
					const type = TYPES[extname(path)];
					if (!path.startsWith(dir + sep) || !type) continue;
					let size: number;
					try {
						size = statSync(path).size;
					} catch {
						continue;
					}
					res.setHeader('Content-Type', type);
					res.setHeader('Content-Length', size);
					createReadStream(path).pipe(res);
					return;
				}
				next();
			});
		}
	};
}

export default defineConfig({
	// The lyrics themes and fonts live in the Python package, outside web/.
	server: { fs: { allow: [ROOT] } },
	plugins: [
		servePackages(),
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
					include: ['src/**/*.{test,spec}.{js,ts}'],
					exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
				}
			}
		]
	}
});
