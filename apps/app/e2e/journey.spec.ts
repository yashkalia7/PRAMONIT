import { expect, test } from '@playwright/test';

import {
  DEMO_PASSWORD,
  login,
  registerCoach,
  registerStudent,
  uploadVideo,
  videoBuffer,
} from './helpers';

/**
 * The whole product in one test.
 *
 * Register a coach and a student, upload two videos, prove they do NOT count
 * while pending, have the coach approve them, and prove the week, the streak
 * and the leaderboard all move together. This is the loop the academy actually
 * runs on — if it passes, the app works.
 */
test('a student uploads, a coach approves, and the streak turns over', async ({ browser }) => {
  test.setTimeout(180_000);

  const coachContext = await browser.newContext();
  const studentContext = await browser.newContext();
  const coachPage = await coachContext.newPage();
  const studentPage = await studentContext.newPage();

  // ---------------------------------------------------------------- setup
  const coach = await registerCoach(coachPage, { name: 'Journey Coach' });
  await registerStudent(studentPage, { name: 'Journey Player', coachName: coach.name });

  // A brand-new student starts cold.
  await expect(studentPage.getByTestId('streak-weeks')).toHaveText('0');
  await expect(studentPage.getByTestId('week-count')).toHaveText('0 / 2');

  // ------------------------------------------------- upload two videos
  await uploadVideo(studentPage, 'journey-one', 'First session of the week.');
  await expect(studentPage.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 });
  await studentPage.getByTestId('upload-again').click();

  await uploadVideo(studentPage, 'journey-two', 'Second session.');
  await expect(studentPage.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 });
  await studentPage.getByTestId('upload-done-home').click();

  // THE approval gate: two videos in, still zero credited.
  await expect(studentPage.getByTestId('student-home')).toBeVisible();
  await expect(studentPage.getByTestId('week-count')).toHaveText('0 / 2');
  await expect(studentPage.getByTestId('pending-notice')).toBeVisible();
  await expect(studentPage.getByTestId('streak-weeks')).toHaveText('0');

  // ------------------------------------------------------ coach reviews
  await coachPage.goto('/coach/review');
  await expect(coachPage.getByTestId('review-student')).toContainText('Journey Player');
  await expect(coachPage.getByTestId('pending-count')).toContainText('2');

  await coachPage.getByTestId('rate-5').click();
  await coachPage.getByTestId('review-feedback').fill('Excellent tempo.');
  await coachPage.getByTestId('approve-button').click();
  await coachPage.waitForTimeout(1200);

  await coachPage.getByTestId('approve-button').click();
  await expect(coachPage.getByTestId('queue-empty')).toBeVisible({ timeout: 20_000 });

  // --------------------------------------------- the student's week turns
  await studentPage.reload();
  await expect(studentPage.getByTestId('student-home')).toBeVisible({ timeout: 20_000 });
  await expect(studentPage.getByTestId('week-count')).toHaveText('2 / 2');
  await expect(studentPage.getByTestId('week-met')).toBeVisible();
  await expect(studentPage.getByTestId('streak-weeks')).toHaveText('1');

  // 2 approved x10 = 20, +25 for meeting the week, +5 for the one 5-star rating.
  await expect(studentPage.getByTestId('total-points')).toContainText('50');

  // ------------------------------------------------------- leaderboard
  await studentPage.getByTestId('tab-ranks').click();
  await expect(studentPage.getByTestId('leaderboard-table')).toBeVisible({ timeout: 20_000 });
  await expect(studentPage.getByTestId('leaderboard-viewer-row')).toContainText('Journey Player');
  await expect(studentPage.getByTestId('leaderboard-viewer-row')).toContainText('50');

  // ---------------------------------------------------- coach dashboard
  await coachPage.goto('/coach');
  await expect(coachPage.getByTestId('stat-students')).toContainText('1');
  await expect(coachPage.getByTestId('stat-compliance')).toContainText('100%');

  await coachContext.close();
  await studentContext.close();
});

test('the same video can never be submitted twice', async ({ browser }) => {
  test.setTimeout(120_000);

  const context = await browser.newContext();
  const page = await context.newPage();

  const coachPage = await (await browser.newContext()).newPage();
  const coach = await registerCoach(coachPage, { name: 'Dedupe Coach' });

  await registerStudent(page, { name: 'Dedupe Player', coachName: coach.name });

  // One fixed payload, uploaded twice.
  const buffer = videoBuffer('fixed-payload-for-dedupe');
  const file = { name: 'clip.mp4', mimeType: 'video/mp4', buffer };

  await page.getByTestId('tab-upload').click();
  await page.getByTestId('video-file-input').setInputFiles(file);
  await page.getByTestId('upload-submit').click();
  await expect(page.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 });

  await page.getByTestId('upload-again').click();
  await page.getByTestId('video-file-input').setInputFiles(file);
  await page.getByTestId('upload-submit').click();

  const error = page.getByTestId('upload-error');
  await expect(error).toBeVisible({ timeout: 30_000 });
  await expect(error).toContainText(/already been submitted/i);

  await context.close();
});

test('a rejected video is clawed back from the week', async ({ browser }) => {
  test.setTimeout(150_000);

  const coachPage = await (await browser.newContext()).newPage();
  const studentPage = await (await browser.newContext()).newPage();

  const coach = await registerCoach(coachPage, { name: 'Strict Coach' });
  await registerStudent(studentPage, { name: 'Rejected Player', coachName: coach.name });

  await uploadVideo(studentPage, 'to-be-rejected');
  await expect(studentPage.getByTestId('upload-success')).toBeVisible({ timeout: 30_000 });

  await coachPage.goto('/coach/review');
  await coachPage.getByTestId('review-feedback').fill('Ball out of frame — refilm from the side.');
  await coachPage.getByTestId('reject-button').click();
  await expect(coachPage.getByTestId('queue-empty')).toBeVisible({ timeout: 20_000 });

  // The student is still signed in; navigate back and pull fresh state.
  await studentPage.getByTestId('upload-done-home').click();
  await studentPage.reload();
  await expect(studentPage.getByTestId('student-home')).toBeVisible({ timeout: 20_000 });
  await expect(studentPage.getByTestId('week-count')).toHaveText('0 / 2');
  await expect(studentPage.getByTestId('total-points')).toContainText('0');

  // The student can read exactly why.
  await studentPage.getByTestId('tab-history').click();
  await expect(studentPage.getByTestId('status-rejected')).toBeVisible();
  await expect(studentPage.getByText(/refilm from the side/i)).toBeVisible();
});
