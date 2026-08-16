import { expect, test } from '@playwright/test';

import { DEMO_PASSWORD, SEEDED_COACH, login, registerCoach, registerStudent } from './helpers';

/**
 * The split layout decision: coaches get a real desktop dashboard, students get
 * a phone-shaped column that is a 1:1 preview of the native build.
 */
test.describe('responsive layout', () => {
  test('the student app renders inside a phone frame on desktop', async ({ page }) => {
    const coachPage = await (await page.context().browser()!.newContext()).newPage();
    const coach = await registerCoach(coachPage, { name: 'Layout Coach' });
    await registerStudent(page, { name: 'Layout Player', coachName: coach.name });

    await expect(page.getByTestId('phone-frame')).toBeVisible();
    await expect(page.getByText(/IDENTICAL TO THE IOS \/ ANDROID BUILD/i)).toBeVisible();

    // The simulated device really is phone width, not a stretched column.
    const box = await page.getByTestId('phone-frame').boundingBox();
    expect(box!.width).toBeGreaterThan(400);
    expect(box!.width).toBeLessThan(480);

    // Bottom tabs, exactly as on a phone.
    await expect(page.getByTestId('tab-bar')).toBeVisible();
    await expect(page.getByTestId('tab-upload')).toBeVisible();
  });

  test('the coach app uses a sidebar, not a phone frame', async ({ page }) => {
    await login(page, SEEDED_COACH, DEMO_PASSWORD);
    await expect(page.getByTestId('coach-dashboard')).toBeVisible({ timeout: 20_000 });

    await expect(page.getByTestId('sidebar')).toBeVisible();
    await expect(page.getByTestId('phone-frame')).toBeHidden();

    for (const item of ['dashboard', 'review', 'roster', 'assign', 'ranks']) {
      await expect(page.getByTestId(`nav-${item}`)).toBeVisible();
    }
  });

  test('the coach layout collapses to tabs on a narrow window', async ({ page }) => {
    await login(page, SEEDED_COACH, DEMO_PASSWORD);
    await expect(page.getByTestId('coach-dashboard')).toBeVisible({ timeout: 20_000 });

    await page.setViewportSize({ width: 420, height: 860 });
    await expect(page.getByTestId('tab-bar')).toBeVisible();
    await expect(page.getByTestId('sidebar')).toBeHidden();
  });

  test('the page never scrolls sideways', async ({ page }) => {
    await login(page, SEEDED_COACH, DEMO_PASSWORD);
    await expect(page.getByTestId('coach-dashboard')).toBeVisible({ timeout: 20_000 });

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });
});
