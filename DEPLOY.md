# Deploying Pramonit

Total cost on these tiers: **₹0/month.**

| Piece | Host | Tier |
|---|---|---|
| Web app | Cloudflare Pages | free, unlimited bandwidth |
| API | Render | free (sleeps after 15 min idle) |
| Database | Supabase Postgres | free (pauses after 7 days idle) |
| Video | Cloudflare R2 | free to 10 GB, £0 egress |

---

## 1 · Database — Supabase

The project already exists. Two things are needed from it:

Dashboard → **PRAMONIT** → **[Connect]** (top bar) → *Connection string*, and copy
both modes. Replace `[YOUR-PASSWORD]` with the database password set at project
creation. If it was never saved it cannot be recovered — reset it under
Settings → Database → *Database password*.

```
DATABASE_URL          …@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
DATABASE_URL_DIRECT   …@db.<project-ref>.supabase.co:5432/postgres
```

> A `sb_secret_…` value is **not** either of these. That is an API key for
> Supabase's own REST/Auth/Storage services. This app connects to Postgres
> directly over the wire, so an API key cannot authenticate it — it is the wrong
> kind of credential, not a wrongly formatted one.

Once set, create the schema:

```bat
cd /d C:\Users\Lenovo\Desktop\PRAMONIT\apps\api
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m app.db.seed
```

## 2 · Video — Cloudflare R2

R2 → **Create bucket** → `pramonit-videos`.
R2 → **Manage API tokens** → *Create API token* → **Object Read & Write**.

Three values go into the environment (the Secret Access Key is shown once):

```
S3_ENDPOINT_URL        https://<account-id>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID       <32-char hex>
S3_SECRET_ACCESS_KEY   <64-char hex>
```

Storage is mandatory in production: Render's disk is wiped on every deploy, so
`STORAGE_BACKEND=local` would silently destroy every student's video.

## 3 · API — Render

Render → **New** → **Blueprint** → connect the `PRAMONIT` repo. It reads
[`render.yaml`](render.yaml) and prompts for each `sync: false` secret.

Set `PUBLIC_BASE_URL` to the URL Render assigns (e.g.
`https://pramonit-api.onrender.com`) and `CORS_ORIGINS` to the web app's origin.

Migrations run automatically at container start — the Dockerfile's command is
`alembic upgrade head && uvicorn …`.

Verify: `https://<your-api>.onrender.com/health` should report
`"backend": "postgresql"` and `"fallback_mode": false`.

## 4 · Web — Cloudflare Pages

Pages → **Create** → connect the repo:

| Setting | Value |
|---|---|
| Root directory | `apps/app` |
| Build command | `npm ci && npx expo export --platform web --output-dir dist` |
| Output directory | `dist` |
| Env var | `EXPO_PUBLIC_API_URL` = `https://<your-api>.onrender.com/api` |

`EXPO_PUBLIC_API_URL` is inlined at build time, so it must be set **before** the
build, and changing it requires a rebuild. `public/_redirects` is copied into the
output and gives the SPA its catch-all route — without it, refreshing on
`/coach/review` returns a 404.

## 5 · Domain

Add two records at your registrar:

```
CNAME   @   or  www     →  <project>.pages.dev
CNAME   api             →  <service>.onrender.com
```

Then add the custom domain in the Pages and Render dashboards so both issue TLS.
Finally update `CORS_ORIGINS` on Render and rebuild Pages with the final
`EXPO_PUBLIC_API_URL`.

---

## Free-tier behaviour worth knowing

- **Render sleeps** after 15 minutes idle; the next request takes ~50s. The
  auto-approve sweeper doesn't tick while asleep, so a 72-hour approval can land
  a few hours late — it self-corrects on the next wake, since the sweep catches
  everything already past the threshold. `plan: starter` ($7/mo) removes both.
- **Supabase pauses** a free project after 7 days with no traffic. One click in
  the dashboard restores it, with no data loss.
- **R2** is free to 10 GB stored with no egress charge. Roughly 300 one-minute
  clips.
