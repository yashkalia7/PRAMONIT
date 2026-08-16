import { expect, test } from '@playwright/test';

import { DEMO_PASSWORD, SEEDED_COACH, login } from './helpers';

test.describe('coach workspace', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, SEEDED_COACH, DEMO_PASSWORD);
    await expect(page.getByTestId('coach-dashboard')).toBeVisible({ timeout: 25_000 });
  });

  test('the dashboard summarises the academy', async ({ page }) => {
    await expect(page.getByTestId('stat-students')).toContainText('4');
    await expect(page.getByTestId('stat-pending')).toBeVisible();
    await expect(page.getByTestId('stat-compliance')).toContainText('%');

    // Seeded coach runs two batches.
    await expect(page.getByTestId('batch-Powai batch')).toBeVisible();
    await expect(page.getByTestId('batch-Powai evening batch')).toBeVisible();
  });

  test('the review queue shows a real video with student context', async ({ page }) => {
    await page.goto('/coach/review');

    // The seeder guarantees every coach opens with work waiting.
    await expect(page.getByTestId('review-student')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('review-drill')).toBeVisible();
    await expect(page.getByTestId('video-preview')).toBeVisible();
    await expect(page.getByTestId('approve-button')).toBeVisible();
    await expect(page.getByTestId('reject-button')).toBeVisible();
  });

  test('the roster lists students and filters by batch', async ({ page }) => {
    await page.goto('/coach/roster');
    await expect(page.getByTestId('roster-screen')).toBeVisible();

    const rows = page.locator('[data-testid^="roster-"]');
    await expect(rows.first()).toBeVisible({ timeout: 20_000 });
    const total = await rows.count();
    expect(total).toBeGreaterThan(0);

    await page.getByTestId('filter-Powai batch').click();
    await expect(rows.first()).toBeVisible();
    expect(await rows.count()).toBeLessThanOrEqual(total);
  });

  test('a coach can assign drills to a batch for the week', async ({ page }) => {
    await page.goto('/coach/assign');
    await expect(page.getByTestId('assign-screen')).toBeVisible();

    await page.getByTestId('assign-batch-Powai batch').click();
    await page.getByTestId('pick-drill-wall-pass-both-feet-200').click();
    await page.getByTestId('pick-drill-sole-rolls-100').click();
    await page.getByTestId('assign-notes').fill('Control before speed.');
    await page.getByTestId('assign-submit').click();

    await expect(page.getByTestId('assign-success')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('assign-success')).toContainText('Powai batch');
  });

  test('every leaderboard tab combination returns data', async ({ page }) => {
    await page.goto('/coach/leaderboard');
    await expect(page.getByTestId('leaderboard-view')).toBeVisible({ timeout: 20_000 });

    for (const scope of ['coach', 'academy']) {
      for (const window of ['week', 'all']) {
        await page.getByTestId(`scope-${scope}`).click();
        await page.getByTestId(`window-${window}`).click();
        await expect(page.getByTestId('leaderboard-table')).toBeVisible({ timeout: 15_000 });
      }
    }
  });

  test('signing out returns to the login screen', async ({ page }) => {
    await page.getByTestId('sign-out').click();
    await expect(page.getByTestId('login-screen')).toBeVisible({ timeout: 15_000 });

    // And the session really is gone, not just navigated away from.
    await page.goto('/coach');
    await expect(page.getByTestId('login-screen')).toBeVisible({ timeout: 15_000 });
  });
});
