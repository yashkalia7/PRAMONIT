import path from 'node:path';

import { defineConfig, devices } from '@playwright/test';

/**
 * Browser E2E against the real stack.
 *
 * Playwright boots both servers itself:
 *   1. the FastAPI backend, reseeded from scratch so every run starts from a
 *      known academy — deterministic streaks, deterministic leaderboards
 *   2. a static server for the exported web bundle, i.e. the exact artefact that
 *      gets deployed, not a dev server with different behaviour
 *
 * No database is required: the API falls back to SQLite.
 */

const API_DIR = path.resolve(__dirname, '../api');
const PYTHON = path.join(API_DIR, '.venv', 'Scripts', 'python.exe');

const WEB_PORT = 3111;
const API_PORT = 8111;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],

  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },

  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      // Same Chromium, phone viewport — proves the layout that ships to iOS and
      // Android renders correctly, without needing a simulator.
      name: 'phone',
      use: { ...devices['Pixel 7'], browserName: 'chromium' },
      testIgnore: /desktop-only/,
    },
    {
      // The recorded product tour. Not part of the assertion suite — run it
      // explicitly with `npm run demo:video`.
      name: 'demo',
      testDir: './demo',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 800 },
        video: { mode: 'on', size: { width: 1280, height: 800 } },
        trace: 'off',
        screenshot: 'off',
        // Actions at human speed, so the recording is followable rather than a
        // blur of instant state changes.
        launchOptions: { slowMo: 180 },
      },
    },
  ],

  webServer: [
    {
      command: `"${PYTHON}" -m app.db.seed --reset && "${PYTHON}" -m uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT} --log-level warning`,
      cwd: API_DIR,
      port: API_PORT,
      reuseExistingServer: false,
      timeout: 180_000,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        // The sweeper is exercised directly in the pytest suite; leaving it off
        // here keeps browser assertions free of background state changes.
        ENABLE_SWEEPER: 'false',
        CORS_ORIGINS: `http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}`,
        PUBLIC_BASE_URL: `http://127.0.0.1:${API_PORT}`,
        ENV: 'test',
      },
    },
    {
      command: `npx serve dist --single --listen ${WEB_PORT} --no-clipboard`,
      cwd: __dirname,
      port: WEB_PORT,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});

export { API_PORT, WEB_PORT };
