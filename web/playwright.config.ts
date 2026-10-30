import { defineConfig } from '@playwright/test';

// Browser tests of the lyrics on the /proba-letra page. Run with `pnpm test:e2e`; they need the
// Playwright Chromium (`pnpm exec playwright install chromium --only-shell`).
export default defineConfig({
	testDir: 'e2e',
	fullyParallel: true,
	reporter: 'list',
	use: { baseURL: 'http://localhost:5181' },
	expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.01 } },
	webServer: {
		command: 'pnpm exec vite dev --port 5181 --strictPort',
		url: 'http://localhost:5181/paquetes/index.json',
		reuseExistingServer: true
	}
});
