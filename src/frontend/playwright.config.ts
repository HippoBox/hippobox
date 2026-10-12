import { defineConfig } from '@playwright/test';

export default defineConfig({
    testDir: './tests',
    workers: 1,
    projects: [
        { name: 'light', use: { colorScheme: 'light' } },
        { name: 'dark', use: { colorScheme: 'dark' } },
    ],
    use: { baseURL: 'http://127.0.0.1:8127', browserName: 'chromium' },
    webServer: {
        command: '../backend/.venv/bin/python ../../scripts/serve-test-app.py',
        url: 'http://127.0.0.1:8127/ping',
        reuseExistingServer: false,
    },
});
