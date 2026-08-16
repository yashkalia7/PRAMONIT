# Pramonit Football Academy

Training-video accountability for a football academy. Students film ball-mastery
drills, coaches review them, and week streaks plus leaderboards make it obvious
who is actually putting the work in.

**One React Native codebase.** It ships to the web today and to iOS/Android later
with no rewrite — same components, same screens, same logic.

---

## Run it right now (no database, no accounts, ~2 minutes)

Two terminals.

### Windows — cmd.exe

> Use `py -3.11`, not a bare `python`. If a WSL or Git-Bash `python` builds the
> venv, it writes `home = /usr/bin` into `.venv\pyvenv.cfg` and every later
> command dies with `No Python at '/usr/bin\python.exe'`.
>
> Always run these from `apps\api` itself — **not** from inside `.venv\Scripts`,
> where the requirements files do not exist.

```bat
:: 1 — API
cd /d %USERPROFILE%\Desktop\PRAMONIT\apps\api
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m app.db.seed --reset
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

```bat
:: 2 — web app
cd /d %USERPROFILE%\Desktop\PRAMONIT\apps\app
npm install
npm run web
```

### macOS / Linux

```bash
# 1 — API
cd apps/api
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m app.db.seed --reset
.venv/bin/python -m uvicorn app.main:app --port 8000
```

```bash
# 2 — web app
cd apps/app && npm install && npm run web
```

The app opens at **http://localhost:8081**.

With no `DATABASE_URL` set, the API falls back to a local SQLite file. Everything
works — registration, uploads, review, streaks, leaderboards — with nothing
installed and no credentials handed over. Swap in Supabase whenever you're ready.

### Demo logins

Password for every seeded account: **`pramonit123`**

| Role | Email |
|---|---|
| Coach | `rahul@pramonit.dev` (4 students, 2 batches) |
| Coach | `sameer@pramonit.dev` · `neha@pramonit.dev` |
| Student | `<firstname>.<lastname>@pramonit.dev` — see the roster screen |

---

## What it does

**Students** get a phone-shaped app: a week streak, a `1 / 2` progress card, the
drills their coach set, an upload flow, their submission history with coach
feedback, and three leaderboards.

**Coaches** get a desktop dashboard: batch compliance, an at-risk list, a review
queue with keyboard shortcuts (`A` approve, `R` reject, `J`/`K` navigate, `1`–`5`
rate), a sortable roster, and weekly drill assignment.

### The rules, precisely

| Rule | Behaviour |
|---|---|
| Weekly minimum | **2 approved videos**, Monday 00:00 → Sunday 23:59 **IST** |
| Streak | Consecutive weeks meeting that minimum |
| Counting | A video counts **only once the coach approves it** |
| Coach lag | Anything unreviewed **auto-approves after 72 h**, tagged `auto` |
| Late review | Credits the week the video was **uploaded**, never the review week |
| Undecided week | Neither extends nor breaks the streak — shown as *pending confirmation* |
| Duplicates | Global SHA-256 index; the same footage can never be submitted twice, by anyone |

Points: `+10` per approved video · `+25` for meeting the week · `+5` per extra
(max 5) · `+5` for a 4–5★ rating · `+50` at 4/8/12/26/52-week milestones.

---

## Architecture

```
┌──────────── ONE EXPO CODEBASE (apps/app) ────────────┐
│  expo-router · React Native · react-native-web        │
│  npm run build:web   → static SPA → your domain  ★NOW │
│  eas build           → .ipa / .aab → stores    ★LATER │
└───────────────────────┬───────────────────────────────┘
                        │ HTTPS · JWT (access + refresh)
             ┌──────────▼───────────┐
             │  FastAPI (apps/api)  │
             │  SQLAlchemy 2 async  │
             │  Alembic · Pydantic  │
             │  APScheduler → 72 h sweeper
             └───┬──────────────┬───┘
    ┌────────────▼───┐   ┌──────▼─────────────────┐
    │ Supabase       │   │  VideoStore interface  │
    │ Postgres       │   │  dev  → LocalDiskStore │
    │ (SQLite when   │   │  prod → S3Store (R2)   │
    │  unset)        │   │  v1   → Cloudflare Stream
    └────────────────┘   └────────────────────────┘
```

**Why the storage seam matters.** Video is the one thing guaranteed to change.
`VideoStore` exposes three methods — `create_upload_target`, `get_playback_url`,
`delete`. Moving R2 → Cloudflare Stream (if iPhone HEVC footage won't play back
in a coach's desktop browser) is one new class and one env var. No route, model
or UI changes.

**The API never proxies video.** Clients hash the file, exchange the hash for a
presigned URL, and PUT the bytes straight to storage. A duplicate is rejected at
the hash exchange — before a single byte crosses a mobile connection.

### Layout

```
apps/api/               FastAPI backend
  app/core/             config, security (JWT + bcrypt), IST week maths, deps
  app/models/           SQLAlchemy — dialect-portable, runs on Postgres and SQLite
  app/services/         streak · scoring · sweeper · leaderboard · storage/
  app/routers/          auth · drills · submissions · me · leaderboard · coach · media
  app/db/               session, seed, init_db
  alembic/              migrations (Postgres)
  tests/                100 pytest tests
apps/app/               Expo — web + iOS + Android
  src/app/              expo-router routes (/login, /student/*, /coach/*)
  src/components/       ui primitives, PhoneFrame, VideoPicker(.web), VideoPreview(.web)
  src/lib/              hash, upload pipeline
  e2e/                  34 Playwright tests
screenshots/            captured from the running app
```

---

## The product tour video

A 3-minute narrated walkthrough is recorded straight from a real browser driving
the real app — nothing is mocked or storyboarded.

```bash
cd apps/app
npm run demo:video     # records, then encodes to MP4
```

Output: **`video/pramonit-product-tour.mp4`** (1280×800, H.264, ~4 MB).

It covers registration → the coach dropdown → uploading → **the approval gate
holding credit back** → duplicate rejection → the coach's review queue →
approval → the week and streak turning over → leaderboards → the phone viewport.
Captions, a step counter and spotlight rings are injected at record time by
`demo/narrate.ts`; none of it exists in the shipped bundle.

Because it drives the app for real, it can never drift from the product: if a
screen changes, the tour either reflects it or fails to record.

Requires **ffmpeg** on `PATH` for the MP4 step. Without it, Playwright's raw
`.webm` is still written to `apps/app/test-results/`.

---

## Testing

```bash
cd apps/api && .venv/Scripts/python -m pytest        # 100 tests
cd apps/app && npm run build:web && npm run test:e2e # 34 tests, Chromium
```

Both run with **no database**. Playwright boots the API and a static server
itself, reseeding from scratch each run, and drives the *exported production
bundle* — not a dev server.

The backend suite pins the parts that are easy to get quietly wrong:

- Sunday 23:59 IST and Monday 00:01 IST land in **different** weeks; 18:31 UTC on
  a Sunday is already Monday in India
- a duplicate hash is refused at `upload-url`, at commit, and across students
- the sweeper approves at 72 h + 1 and leaves 71 h alone, and never double-counts
- a late approval credits the upload week, not the review week
- a week with pending videos holds the streak instead of breaking it
- rejecting an approved video claws back the points, including the week bonus

The browser suite runs at **both** a desktop and a phone viewport, and covers the
full loop: register → upload → *not counted while pending* → coach approves →
week turns over → streak and leaderboard move together.

---

## Deploying

### Web (today)

```bash
cd apps/app
EXPO_PUBLIC_API_URL=https://api.your-domain.com/api npm run build:web
```

`dist/` is a static SPA — drop it on Cloudflare Pages, Vercel, Netlify, or any
static host. Configure a catch-all rewrite to `/index.html`.

### API

`apps/api/Dockerfile` deploys to Fly.io, Railway or Render. It runs
`alembic upgrade head` at boot. Required environment:

```
DATABASE_URL           Supabase pooled URI  (:6543)
DATABASE_URL_DIRECT    Supabase direct URI  (:5432)   — migrations
JWT_SECRET             python -c "import secrets;print(secrets.token_urlsafe(48))"
CORS_ORIGINS           https://your-domain.com
STORAGE_BACKEND        s3
S3_ENDPOINT_URL        https://<account-id>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID       …
S3_SECRET_ACCESS_KEY   …
S3_BUCKET              pramonit-videos
```

### Mobile (later)

```bash
cd apps/app
npx eas build --platform all
```

Needs an Expo account, Apple Developer ($99/yr) and Google Play ($25 one-off).
No code changes — `app.json` already carries `com.pramonit.app`.

---

## Known limits in v0

- **Seeded demo videos don't play.** They point at a placeholder key; real
  uploads play normally. Cosmetic, demo-data only.
- **The sweeper needs an advisory lock past one API instance**, or two workers
  could double-approve. Fine as-is; flagged for the first scale-out.
- **`counts_for_week` is pinned at upload.** Deliberate — see the rules table.
- **Integrity is dedupe-only.** Camera-only capture, GPS and perceptual hashing
  are deferred to v1.
- **Coach accounts are self-service.** Anyone can register as a coach; there is
  no academy-admin gate yet.
