import { defineConfig } from '@playwright/test';

// Browser tests. `pnpm test:e2e` runs them against the dev server and its mock API (port 5181);
// they need the Playwright Chromium (`pnpm exec playwright install chromium --only-shell`).
// The lyrics specs set their own sizes; the app specs run on a phone, a laptop and a TV.
const APP = /app\/.*\.spec\.ts/;
// e2e/server runs against the real server: `pnpm test:e2e:server` (playwright.server.config.ts).
const SERVER = /server\/.*\.spec\.ts/;

export default defineConfig({
	testDir: 'e2e',
	fullyParallel: true,
	reporter: 'list',
	use: { baseURL: 'http://localhost:5181', locale: 'gl-ES' },
	expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.01 } },
	// The lyrics snapshots predate the projects: keep their names.
	snapshotPathTemplate: '{testDir}/{testFilePath}-snapshots/{arg}-{platform}{ext}',
	projects: [
		{ name: 'lyrics', testIgnore: [APP, SERVER] },
		{
			name: 'phone',
			testMatch: APP,
			use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }
		},
		{ name: 'laptop', testMatch: APP, use: { viewport: { width: 1440, height: 900 } } },
		{ name: 'tv', testMatch: APP, use: { viewport: { width: 1920, height: 1080 } } }
	],
	webServer: {
		command: 'pnpm exec vite dev --port 5181 --strictPort',
		url: 'http://localhost:5181/api/songs',
		reuseExistingServer: true,
		env: { KARAOKE_MOCK_JOB_SECONDS: '3' }
	}
});
