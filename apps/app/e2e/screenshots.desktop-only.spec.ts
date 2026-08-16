import path from 'node:path';

import { expect, test } from '@playwright/test';

import {
  DEMO_PASSWORD,
  SEEDED_COACH,
  login,
  registerCoach,
  registerStudent,
  routeApiToTestBackend,
  uploadVideo,
} from './helpers';

/**
 * Not an assertion suite — this captures the handover screenshots.
 * Run with: npx playwright test --project=desktop e2e/screenshots
 */

const OUT = path.resolve(__dirname, '../../../screenshots');
const shot = (name: string) => path.join(OUT, `${name}.png`);

test.describe('screenshots', () => {
  test('login and student signup', async ({ page }) => {
    await routeApiToTestBackend(page);
    await page.goto('/login');
    await expect(page.getByTestId('login-screen')).toBeVisible();
    await page.screenshot({ path: shot('01-login'), fullPage: true });

    await page.goto('/register/student');
    await page.getByTestId('reg-name').fill('Arjun Mehta');
    await page.getByTestId('reg-email').fill('arjun.shot@pramonit.dev');
    await page.getByTestId('reg-password').fill(DEMO_PASSWORD);
    await page.getByTestId('reg-next').click();
    await expect(page.getByLabel('Coach Rahul Menon')).toBeVisible();
    await page.screenshot({ path: shot('02-register-coach-picker'), fullPage: true });
  });

  test('student app in the phone frame', async ({ page }) => {
    const coachPage = await (await page.context().browser()!.newContext()).newPage();
    const coach = await registerCoach(coachPage, { name: 'Demo Coach' });
    await registerStudent(page, { name: 'Myra Mehta', coachName: coach.name });

    await page.screenshot({ path: shot('03-student-home-empty') });

    await uploadVideo(page, 'shot-one', 'Left foot felt sharper today.');
    await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 });
    await page.screenshot({ path: shot('04-upload-success') });

    await page.getByTestId('upload-again').click();
    await uploadVideo(page, 'shot-two');
    await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 });
    await page.getByTestId('upload-done-home').click();
    await page.screenshot({ path: shot('05-student-home-pending') });

    // Coach approves both, then the student's week turns over.
    await coachPage.goto('/coach/review');
    await coachPage.getByTestId('rate-5').click();
    await coachPage.getByTestId('review-feedback').fill('Excellent tempo — head up more.');
    await coachPage.screenshot({ path: shot('06-coach-review') });
    await coachPage.getByTestId('approve-button').click();
    await coachPage.waitForTimeout(1000);
    await coachPage.getByTestId('approve-button').click();
    await coachPage.waitForTimeout(1000);

    await page.reload();
    await expect(page.getByTestId('week-met')).toBeVisible({ timeout: 20_000 });
    await page.screenshot({ path: shot('07-student-home-streak') });

    await page.getByTestId('tab-ranks').click();
    await expect(page.getByTestId('leaderboard-table')).toBeVisible({ timeout: 20_000 });
    await page.screenshot({ path: shot('08-student-leaderboard') });

    await page.getByTestId('tab-history').click();
    await expect(page.getByTestId('history-screen')).toBeVisible();
    await page.screenshot({ path: shot('09-student-history') });
  });

  test('coach dashboard, roster and assignment', async ({ page }) => {
    await login(page, SEEDED_COACH, DEMO_PASSWORD);
    await expect(page.getByTestId('coach-dashboard')).toBeVisible({ timeout: 20_000 });
    await page.screenshot({ path: shot('10-coach-dashboard'), fullPage: true });

    await page.goto('/coach/roster');
    await expect(page.getByTestId('roster-screen')).toBeVisible();
    await page.screenshot({ path: shot('11-coach-roster'), fullPage: true });

    await page.goto('/coach/assign');
    await expect(page.getByTestId('assign-screen')).toBeVisible();
    await page.getByTestId('pick-drill-wall-pass-both-feet-200').click();
    await page.getByTestId('pick-drill-one-tap-juggles-wall-50').click();
    await page.screenshot({ path: shot('12-coach-assign'), fullPage: true });

    await page.goto('/coach/leaderboard');
    await expect(page.getByTestId('leaderboard-table')).toBeVisible({ timeout: 20_000 });
    await page.screenshot({ path: shot('13-coach-leaderboard'), fullPage: true });
  });
});
