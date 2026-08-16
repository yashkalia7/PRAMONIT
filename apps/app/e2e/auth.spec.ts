import { expect, test } from '@playwright/test';

import { DEMO_PASSWORD, SEEDED_COACH, login, routeApiToTestBackend } from './helpers';

test.describe('authentication', () => {
  test('the login screen renders and reaches the API', async ({ page }) => {
    await routeApiToTestBackend(page);
    await page.goto('/login');

    await expect(page.getByTestId('login-screen')).toBeVisible();
    await expect(page.getByText('PRAMONIT')).toBeVisible();
    await expect(page.getByText('Train. Film. Prove it.')).toBeVisible();
  });

  test('a wrong password is rejected with a readable message', async ({ page }) => {
    await login(page, SEEDED_COACH, 'definitely-not-the-password');

    const error = page.getByTestId('login-error');
    await expect(error).toBeVisible();
    await expect(error).toContainText(/incorrect email or password/i);
  });

  test('a seeded coach lands on the coach dashboard', async ({ page }) => {
    await login(page, SEEDED_COACH, DEMO_PASSWORD);

    await expect(page.getByTestId('coach-dashboard')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('stat-students')).toBeVisible();
    expect(page.url()).toContain('/coach');
  });

  test('the signup screen lists real coaches to choose from', async ({ page }) => {
    await routeApiToTestBackend(page);
    await page.goto('/register/student');

    await page.getByTestId('reg-name').fill('Arjun Mehta');
    await page.getByTestId('reg-email').fill('arjun.temp@pramonit.dev');
    await page.getByTestId('reg-password').fill(DEMO_PASSWORD);
    await page.getByTestId('reg-next').click();

    // Loaded from GET /public/coaches — proves the unauthenticated endpoint works.
    await expect(page.getByLabel('Coach Rahul Menon')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByLabel('Coach Sameer Qureshi')).toBeVisible();
    await expect(page.getByLabel('Coach Neha Kulkarni')).toBeVisible();
  });

  test('registration validates before advancing a step', async ({ page }) => {
    await routeApiToTestBackend(page);
    await page.goto('/register/student');

    await page.getByTestId('reg-name').fill('A');
    await page.getByTestId('reg-next').click();
    await expect(page.getByTestId('register-error')).toContainText(/full name/i);

    await page.getByTestId('reg-name').fill('Arjun Mehta');
    await page.getByTestId('reg-email').fill('not-an-email');
    await page.getByTestId('reg-next').click();
    await expect(page.getByTestId('register-error')).toContainText(/valid email/i);

    await page.getByTestId('reg-email').fill('arjun.valid@pramonit.dev');
    await page.getByTestId('reg-password').fill('short');
    await page.getByTestId('reg-next').click();
    await expect(page.getByTestId('register-error')).toContainText(/8 characters/i);
  });

  test('an unauthenticated visitor is sent to login', async ({ page }) => {
    await routeApiToTestBackend(page);
    await page.goto('/student');
    await expect(page.getByTestId('login-screen')).toBeVisible({ timeout: 15_000 });
  });
});
