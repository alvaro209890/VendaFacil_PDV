import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    browserName: 'chromium',
    viewport: { width: 1366, height: 900 },
    trace: 'off', // Não registrar cabeçalhos/tokens nem corpos de requests.
    screenshot: 'off',
  },
  webServer: {
    command: 'node e2e/servidor.cjs',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: false,
    timeout: 60000,
  },
});
