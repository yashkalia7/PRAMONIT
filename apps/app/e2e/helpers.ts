import { expect, type Page } from '@playwright/test';

export const API_BASE = 'http://127.0.0.1:8111/api';
export const DEMO_PASSWORD = 'pramonit123';
export const SEEDED_COACH = 'rahul@pramonit.dev';

/**
 * The exported bundle resolves the API from window.location.hostname:8000, but
 * the test backend runs on 8111 to avoid colliding with a dev server. Rather
 * than rebuilding the bundle per environment, rewrite the port in flight — the
 * app code under test is untouched.
 */
export async function routeApiToTestBackend(page: Page) {
  await page.route('**://127.0.0.1:8000/**', (route) => {
    const url = route.request().url().replace(':8000', ':8111');
    route.continue({ url });
  });
  await page.route('**://localhost:8000/**', (route) => {
    const url = route.request().url().replace(':8000', ':8111');
    route.continue({ url });
  });
}

export function uniqueEmail(prefix: string): string {
  return `${prefix}.${Date.now()}.${Math.floor(Math.random() * 10_000)}@pramonit.dev`;
}

/** A distinct byte payload per call, so each upload has its own SHA-256. */
export function videoBuffer(seed: string): Buffer {
  const header = Buffer.from([0x00, 0x00, 0x00, 0x18, 0x66, 0x74, 0x79, 0x70]);
  const body = Buffer.from(`${seed}:${Date.now()}:${Math.random()}`.repeat(64));
  return Buffer.concat([header, body]);
}

/**
 * Byte-identical for a given seed, across calls and across runs.
 *
 * Use this to demonstrate duplicate rejection — `videoBuffer` deliberately
 * salts with the clock, so calling it twice with the same seed produces two
 * *different* files and no duplicate is detected.
 */
export function fixedVideoBuffer(seed: string): Buffer {
  const header = Buffer.from([0x00, 0x00, 0x00, 0x18, 0x66, 0x74, 0x79, 0x70]);
  return Buffer.concat([header, Buffer.from(`${seed}`.repeat(256))]);
}

export async function login(page: Page, email: string, password = DEMO_PASSWORD) {
  await routeApiToTestBackend(page);
  await page.goto('/login');
  await page.getByTestId('login-email').fill(email);
  await page.getByTestId('login-password').fill(password);
  await page.getByTestId('login-submit').click();
}

/**
 * Register a fresh coach through the UI.
 *
 * The journey test needs a coach whose review queue contains nothing but the
 * videos that test uploaded — the seeded coaches already have a backlog, which
 * would make "approve everything" assertions meaningless.
 */
export async function registerCoach(
  page: Page,
  options: { name?: string; email?: string; batch?: string } = {},
): Promise<{ email: string; name: string; batch: string }> {
  const email = options.email ?? uniqueEmail('coach');
  // Always suffixed: the desktop and phone projects share one database, so a
  // fixed name would collide across projects and make getByLabel ambiguous.
  const name = `${options.name ?? 'Coach'} ${Math.floor(Math.random() * 1e6)}`;
  const batch = options.batch ?? 'Test batch';

  await routeApiToTestBackend(page);
  await page.goto('/register/coach');
  await expect(page.getByTestId('register-coach-screen')).toBeVisible();

  await page.getByTestId('coach-name').fill(name);
  await page.getByTestId('coach-email').fill(email);
  await page.getByTestId('coach-password').fill(DEMO_PASSWORD);
  await page.getByTestId('coach-specialization').fill('Ball mastery');
  await page.getByTestId('coach-location').fill('Powai');
  await page.getByTestId('coach-batch-input').fill(batch);
  await page.getByTestId('coach-batch-add').click();
  await page.getByTestId('coach-submit').click();

  await expect(page.getByTestId('coach-dashboard')).toBeVisible({ timeout: 20_000 });
  return { email, name, batch };
}

export async function registerStudent(
  page: Page,
  options: { name?: string; email?: string; coachName?: string } = {},
): Promise<string> {
  const email = options.email ?? uniqueEmail('student');
  const name = options.name ?? 'Test Player';

  await routeApiToTestBackend(page);
  await page.goto('/register/student');
  await expect(page.getByTestId('register-student-screen')).toBeVisible();

  // Step 1 — account
  await page.getByTestId('reg-name').fill(name);
  await page.getByTestId('reg-email').fill(email);
  await page.getByTestId('reg-password').fill(DEMO_PASSWORD);
  await page.getByTestId('reg-next').click();

  // Step 2 — football profile: pick the coach, which pre-fills the batch
  const coach = page.getByLabel(`Coach ${options.coachName ?? 'Rahul Menon'}`);
  await expect(coach).toBeVisible();
  await coach.click();
  await expect(page.getByTestId('reg-batch')).toHaveValue(/.+/);
  await page.getByTestId('reg-next').click();

  // Step 3 — guardian & consent
  await page.getByTestId('reg-guardian').fill('Mrs. Test');
  await page.getByTestId('reg-consent').click();
  await page.getByTestId('reg-submit').click();

  await expect(page.getByTestId('student-home')).toBeVisible({ timeout: 20_000 });
  return email;
}

/** Full upload flow through the real file input, hashing and presigned PUT. */
export async function uploadVideo(page: Page, seed: string, note = 'Felt sharp today.') {
  await page.getByTestId('tab-upload').click();
  await expect(page.getByTestId('upload-screen')).toBeVisible();

  await page.getByTestId('video-file-input').setInputFiles({
    name: `${seed}.mp4`,
    mimeType: 'video/mp4',
    buffer: videoBuffer(seed),
  });

  await expect(page.getByTestId('video-size')).toBeVisible();
  await page.getByTestId('upload-note').fill(note);
  await page.getByTestId('upload-submit').click();
}

export async function approveAllPending(page: Page, max = 10): Promise<number> {
  await page.goto('/coach/review');
  let approved = 0;
  for (let i = 0; i < max; i += 1) {
    const empty = page.getByTestId('queue-empty');
    if (await empty.isVisible().catch(() => false)) break;

    const button = page.getByTestId('approve-button');
    if (!(await button.isVisible().catch(() => false))) break;

    await button.click();
    approved += 1;
    await page.waitForTimeout(600);
  }
  return approved;
}
