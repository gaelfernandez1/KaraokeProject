import { defineConfig } from '@playwright/test';

// Browser tests against the real karaoke server (`pnpm test:e2e:server`): the built app, the
// fake engine and a fresh library. The laptop opens it on localhost, as the owner; phones come
// in through the machine's network address, as the home network would.
const PORT = 8785;

export default defineConfig({
	testDir: 'e2e/server',
	// One server, one library and one GPU lane: the flows run one after another.
	workers: 1,
	reporter: 'list',
	timeout: 60_000,
	use: {
		baseURL: `http://localhost:${PORT}`,
		locale: 'gl-ES',
		viewport: { width: 1440, height: 900 }
	},
	webServer: {
		command: `bash e2e/server/serve.sh ${PORT}`,
		url: `http://localhost:${PORT}/api/health`,
		reuseExistingServer: false,
		timeout: 180_000
	}
});
