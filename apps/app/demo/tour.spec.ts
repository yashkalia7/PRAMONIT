import { expect, test, type Locator } from '@playwright/test';

import {
  DEMO_PASSWORD,
  fixedVideoBuffer,
  registerCoach,
  routeApiToTestBackend,
  uniqueEmail,
  videoBuffer,
} from '../e2e/helpers';
import { aside, card, clearSpotlight, point, resetSteps, say, spotlight } from './narrate';

/**
 * The recorded product tour.
 *
 * One continuous browser session covering the entire product: register, upload,
 * watch the approval gate hold the credit back, approve as the coach, and watch
 * the week and the streak turn over together. Roles switch by genuinely signing
 * out and back in, so the result is a single unbroken video.
 *
 * Note the `.first()` in `q()`. Unlike the assertion suite — where every test
 * starts on a fresh page — this session signs in and out repeatedly, and
 * expo-router keeps previously visited routes mounted. Several screens
 * therefore exist more than once in the DOM, and a bare getByTestId would trip
 * strict mode even though only one copy is ever visible.
 */
test('Pramonit — full product tour', async ({ page }) => {
  test.setTimeout(600_000);
  resetSteps();

  // Resolve to the *visible* instance, not merely the first in document order:
  // the stale copies expo-router leaves mounted come earlier in the DOM, so
  // `.first()` would consistently pick the hidden one.
  const q = (id: string): Locator => page.locator(`[data-testid="${id}"]:visible`).first();
  // The file input is intentionally a 1×1 transparent element, so it is
  // addressed directly rather than through the visibility filter.
  const fileInput = (): Locator => page.getByTestId('video-file-input').last();
  const studentEmail = uniqueEmail('demo.player');

  // A dedicated coach, so the review queue on camera holds only this tour's
  // uploads. Registered off-screen in a throwaway context.
  const setupContext = await page.context().browser()!.newContext();
  const setupPage = await setupContext.newPage();
  const coach = await registerCoach(setupPage, { name: 'Rahul Menon', batch: 'Powai batch' });
  await setupContext.close();

  await routeApiToTestBackend(page);
  await page.goto('/login');
  await expect(q('login-screen')).toBeVisible();

  await card(
    page,
    'Pramonit Football Academy',
    'Proof of training, every week',
    [
      'Students film ball-mastery drills · coaches review them',
      'Two approved videos a week keeps the streak alive',
      'One React Native codebase — web now, iOS &amp; Android later',
    ],
    4200,
  );

  await say(
    page,
    'One codebase, two front doors',
    'This is the web build running in a browser. The exact same React Native code compiles to iOS and Android — nothing here gets rewritten for mobile.',
    3400,
  );

  // ---------------------------------------------------------------- signup
  await say(
    page,
    'A new student registers',
    'Registration is deliberately verbose in v0: the club collects broadly now, and narrows down once it knows which fields actually get used.',
    3000,
  );
  await point(page, q('link-register-student'));
  await expect(q('register-student-screen')).toBeVisible();

  await q('reg-name').fill('Myra Mehta');
  await q('reg-email').fill(studentEmail);
  await q('reg-password').fill(DEMO_PASSWORD);
  await aside(page, 'Step 1 — account', 'Name, email, password, phone, date of birth.', 2000);
  await point(page, q('reg-next'));

  await say(
    page,
    'Every student has exactly one coach',
    'The coach is chosen here, from a real list served by the API. Picking one links the student to that coach and pre-fills their batch.',
    3200,
  );
  await point(page, page.getByLabel(`Coach ${coach.name}`).first(), 1200);

  await aside(
    page,
    'Batch is free text',
    'Powai batch, Andheri batch — whatever the club runs. No migration needed when a new slot opens.',
    2600,
  );
  await spotlight(page, q('reg-batch'), 1400);
  await clearSpotlight(page);
  await q('reg-position').fill('Attacking midfielder');
  await point(page, q('foot-left'), 700);
  await point(page, q('reg-next'));

  await q('reg-guardian').fill('Mrs. Mehta');
  await aside(
    page,
    'Step 3 — guardian & consent',
    'Guardian contacts, emergency number, medical notes, and explicit consent to store training footage.',
    2600,
  );
  await point(page, q('reg-consent'), 700);
  await point(page, q('reg-submit'));

  // ------------------------------------------------------------ student home
  await expect(q('student-home')).toBeVisible({ timeout: 20_000 });
  await say(
    page,
    'The student app — inside a phone',
    'On a desktop browser the student experience renders in a 440px device frame. What you see here is pixel-identical to the mobile build.',
    3600,
  );

  await spotlight(page, q('streak-card'), 1600);
  await aside(
    page,
    'Week streak, not day streak',
    'Consecutive weeks with 2+ approved videos. A rest day never costs a streak — a missed week does.',
    3000,
  );
  await clearSpotlight(page);

  await spotlight(page, q('week-progress'), 1400);
  await aside(
    page,
    '0 of 2 this week',
    'The club rule is two compulsory videos a week. Anything beyond that is the player’s own ambition — and the leaderboard rewards it.',
    3200,
  );
  await clearSpotlight(page);

  // ---------------------------------------------------------------- upload
  await say(page, 'Filming and submitting a session', undefined, 1600);
  await point(page, q('tab-upload'));
  await expect(q('upload-screen')).toBeVisible();

  await aside(
    page,
    'Drills come from the coach',
    'This week’s ball-mastery set — wall passes, one-tap juggles, turning with the ball — assigned to the whole batch.',
    2800,
  );

  await fileInput().setInputFiles({
    name: 'wall-pass.mp4',
    mimeType: 'video/mp4',
    buffer: videoBuffer('tour-one'),
  });
  await expect(q('video-size')).toBeVisible();
  await q('upload-note').fill('Left foot felt much better today.');

  await aside(
    page,
    'What happens on submit',
    'The file is fingerprinted locally, the hash is checked for duplicates <em>before</em> any bytes move, then the video uploads straight to storage — the API never proxies video.',
    3600,
  );
  await point(page, q('upload-submit'));
  await expect(q('upload-success')).toBeVisible({ timeout: 30_000 });

  await say(
    page,
    'Sent to the coach',
    'It is not counted yet. That is the whole design: a video credits the week only once a human has watched it.',
    3200,
  );

  await point(page, q('upload-again'));
  await fileInput().setInputFiles({
    name: 'turning.mp4',
    mimeType: 'video/mp4',
    buffer: fixedVideoBuffer('tour-two'),
  });
  await q('upload-note').fill('Turns are getting tighter.');
  await point(page, q('upload-submit'));
  await expect(q('upload-success')).toBeVisible({ timeout: 30_000 });

  // ------------------------------------------------------------- duplicate
  await say(
    page,
    'The same footage can never be reused',
    'Sharing one clip around the batch is the obvious way to cheat. Every video carries a SHA-256 fingerprint, unique across the entire academy.',
    3400,
  );
  await point(page, q('upload-again'));
  await fileInput().setInputFiles({
    name: 'turning-again.mp4',
    mimeType: 'video/mp4',
    // Byte-identical to the previous upload, under a different filename —
    // renaming a borrowed clip is exactly the cheat this must catch.
    buffer: fixedVideoBuffer('tour-two'),
  });
  await q('upload-submit').click();
  await expect(q('upload-error')).toBeVisible({ timeout: 20_000 });
  await spotlight(page, q('upload-error'), 1200);
  await aside(
    page,
    'Rejected instantly',
    'Refused in one round trip, before a single byte crossed the connection — not after a 40 MB upload on mobile data.',
    3200,
  );
  await clearSpotlight(page);

  // ----------------------------------------------- the gate, seen on the home
  await point(page, q('tab-home'));
  await expect(q('student-home')).toBeVisible();
  await spotlight(page, q('week-progress'), 1500);
  await say(
    page,
    'Two uploaded. Still 0 of 2.',
    'Pending videos do not count. The streak has not moved. This is the integrity rule the whole app is built around.',
    3600,
  );
  await clearSpotlight(page);
  await aside(
    page,
    'But a busy coach can never cost a student their week',
    'Anything left unreviewed auto-approves after 72 hours, tagged so the origin of the credit stays visible.',
    3400,
  );

  // ------------------------------------------------------ switch to the coach
  await say(page, 'Now the coach’s side', undefined, 1600);
  await point(page, q('tab-me'));
  await point(page, q('sign-out'));
  await expect(q('login-email')).toBeVisible({ timeout: 15_000 });

  await q('login-email').fill(coach.email);
  await q('login-password').fill(DEMO_PASSWORD);
  await point(page, q('login-submit'));
  await expect(q('coach-dashboard')).toBeVisible({ timeout: 20_000 });

  await say(
    page,
    'Coaches get a real desktop dashboard',
    'Not a stretched phone app — a sidebar, a wide review grid and sortable tables. Reviewing thirty videos deserves a desktop layout.',
    3600,
  );
  await spotlight(page, q('stat-pending'), 1400);
  await clearSpotlight(page);

  // ---------------------------------------------------------------- review
  await point(page, q('nav-review'));
  await expect(q('review-student')).toBeVisible({ timeout: 20_000 });
  await say(
    page,
    'The review queue — oldest first',
    'The video closest to auto-approving is always the one that needs a human most, so it surfaces first.',
    3200,
  );

  await aside(
    page,
    'Everything the coach needs, in one view',
    'The footage, who filmed it, which drill, the reps they claimed, how long it has been waiting, and their note.',
    3200,
  );

  await point(page, q('rate-5'), 900);
  await q('review-feedback').fill('Excellent tempo. Head up more between touches.');
  await aside(
    page,
    'Rate and give feedback',
    'A 4 or 5 star rating awards the student a bonus. The feedback appears on their history screen.',
    2800,
  );
  await point(page, q('approve-button'));
  await page.waitForTimeout(1400);

  await aside(
    page,
    'On a desktop, hands never leave the keyboard',
    'A approve · R reject · J / K to move through the queue · 1–5 to rate.',
    3000,
  );
  await point(page, q('approve-button'));
  await expect(q('queue-empty')).toBeVisible({ timeout: 20_000 });
  await say(page, 'Queue clear', 'Both videos approved.', 2200);

  // ------------------------------------------------------ coach oversight
  await point(page, q('nav-dashboard'));
  await expect(q('coach-dashboard')).toBeVisible();
  await say(
    page,
    'Who is actually training',
    'Batch-by-batch compliance, and a list of exactly who needs chasing this week — students who have filmed nothing at all.',
    3400,
  );

  await point(page, q('nav-roster'));
  await expect(q('roster-screen')).toBeVisible();
  await say(
    page,
    'The roster',
    'Every student with their week progress, streak and points. Sortable by risk, and a coach can move a student between batches or reassign them entirely.',
    3400,
  );

  await point(page, q('nav-assign'));
  await expect(q('assign-screen')).toBeVisible();
  await say(
    page,
    'Setting next week’s work',
    'Pick a batch, tick the drills. One action per coach per week, and every student in that batch sees the same set — which keeps the leaderboard fair.',
    3400,
  );
  await point(page, q('pick-drill-wall-pass-both-feet-200'), 700);
  await point(page, q('pick-drill-turning-with-the-ball-3min'), 700);
  await q('assign-notes').fill('Control before speed. Film from the side.');
  await point(page, q('assign-submit'));
  await expect(q('assign-success')).toBeVisible({ timeout: 20_000 });

  // -------------------------------------------------- back to the student
  await say(page, 'Back to the student', 'The approval flows straight through.', 2000);
  await point(page, q('sign-out'));
  await expect(q('login-email')).toBeVisible({ timeout: 15_000 });
  await q('login-email').fill(studentEmail);
  await q('login-password').fill(DEMO_PASSWORD);
  await point(page, q('login-submit'));
  await expect(q('student-home')).toBeVisible({ timeout: 20_000 });

  await spotlight(page, q('week-progress'), 1600);
  await say(
    page,
    '2 of 2 — week complete',
    'The same two videos that counted for nothing while pending now close out the week.',
    3400,
  );
  await clearSpotlight(page);

  await spotlight(page, q('streak-card'), 1600);
  await aside(
    page,
    'Streak: 1 week · 50 points',
    '10 points per approved video, 25 for meeting the week, 5 for the five-star rating. Every figure is traceable to an event in an append-only ledger.',
    3800,
  );
  await clearSpotlight(page);

  // ----------------------------------------------------------- leaderboard
  await point(page, q('tab-ranks'));
  await expect(q('leaderboard-table')).toBeVisible({ timeout: 20_000 });
  await say(
    page,
    'Three leaderboards, two windows',
    'Your batch, your coach’s students, or the whole academy — this week or all time. Your own row is always pinned, even in 87th place.',
    3600,
  );
  await point(page, q('scope-academy'), 800);
  await page.waitForTimeout(1200);
  await point(page, q('window-all'), 800);
  await page.waitForTimeout(1600);

  await point(page, q('tab-history'));
  await expect(q('history-screen')).toBeVisible();
  await say(
    page,
    'Full submission history',
    'Every video with its status, the coach’s rating and their written feedback.',
    3000,
  );

  // --------------------------------------------------------- mobile viewport
  await point(page, q('tab-home'));
  await say(
    page,
    'And on an actual phone',
    'Same build, same code. The device frame simply falls away and the app goes full-bleed.',
    2800,
  );
  await page.setViewportSize({ width: 412, height: 860 });
  await page.waitForTimeout(3400);

  await page.setViewportSize({ width: 1280, height: 800 });
  await page.waitForTimeout(900);

  await card(
    page,
    'That’s Pramonit',
    'Built, tested, ready to deploy',
    [
      '100 backend tests · 37 browser tests — all passing',
      'Runs with no database at all; Supabase Postgres in production',
      'Web today on your own domain · iOS &amp; Android from the same codebase',
    ],
    5000,
  );
});
