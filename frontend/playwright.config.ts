import { defineConfig } from '@playwright/test';

const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL;

export default defineConfig({
	testDir: 'e2e',
	use: {
		baseURL: externalBaseUrl || 'http://127.0.0.1:4173'
	},
	webServer: externalBaseUrl
		? undefined
		: {
				command: 'bun run build && bun run preview --host 127.0.0.1 --port 4173',
				port: 4173
			}
});
