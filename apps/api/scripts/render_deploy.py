"""Deploy the whole stack to Render — API and web app — from apps/api/.env.

Render hosts static sites free and unlimited, so both halves live on one
provider with one credential. No Cloudflare token required.

Order matters and is handled here:
  1. create the API web service          -> yields https://pramonit-api.onrender.com
  2. create the static site with EXPO_PUBLIC_API_URL pointing at it
       (that value is inlined at BUILD time, so it must exist first)
  3. patch the API's CORS_ORIGINS to allow the static site's origin

Idempotent: existing services have their environment updated instead of erroring.

    set RENDER_API_KEY=rnd_...
    python -m scripts.render_deploy
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.render.com/v1"
REPO = "https://github.com/yashkalia7/PRAMONIT"
REGION = "singapore"          # closest Render region to India
API_NAME = "pramonit-api"
WEB_NAME = "pramonit-web"

KEY = os.environ.get("RENDER_API_KEY", "")
if not KEY:
    sys.exit("RENDER_API_KEY is not set")


def call(method: str, path: str, body=None):
    req = urllib.request.Request(
        f"{API}{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:700]


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    path = Path(__file__).resolve().parents[1] / ".env"
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"')
    return values


def find_service(name: str):
    status, rows = call("GET", f"/services?name={name}&limit=20")
    if status == 200 and isinstance(rows, list):
        for row in rows:
            if row["service"]["name"] == name:
                return row["service"]
    return None


def service_url(service: dict) -> str:
    details = service.get("serviceDetails", {})
    return details.get("url") or f"https://{service['name']}.onrender.com"


def wait_for_url(service_id: str, tries: int = 10) -> str:
    """Render assigns the hostname a moment after creation."""
    for _ in range(tries):
        status, body = call("GET", f"/services/{service_id}")
        if status == 200:
            url = (body or {}).get("serviceDetails", {}).get("url")
            if url:
                return url
        time.sleep(3)
    return ""


def main() -> int:
    env = read_env()
    owner_status, owners = call("GET", "/owners?limit=1")
    if owner_status != 200:
        print("cannot read owner:", owners)
        return 1
    owner_id = owners[0]["owner"]["id"]

    passthrough = [
        "DATABASE_URL", "DATABASE_URL_DIRECT", "JWT_SECRET",
        "STORAGE_BACKEND", "S3_ENDPOINT_URL", "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY", "S3_BUCKET", "S3_REGION",
        "APP_TIMEZONE", "WEEKLY_REQUIRED_SUBMISSIONS",
        "AUTO_APPROVE_AFTER_HOURS", "SWEEPER_INTERVAL_MINUTES",
        "ENABLE_SWEEPER", "MAX_UPLOAD_MB", "ACCESS_TOKEN_MINUTES",
        "REFRESH_TOKEN_DAYS",
    ]
    api_env = [{"key": k, "value": env[k]} for k in passthrough if k in env]
    api_env += [{"key": "ENV", "value": "prod"}, {"key": "PYTHONUNBUFFERED", "value": "1"}]

    # ------------------------------------------------------------ 1 · API
    api_service = find_service(API_NAME)
    if api_service:
        print(f"api    · exists {api_service['id']}")
    else:
        status, body = call("POST", "/services", {
            "type": "web_service",
            "name": API_NAME,
            "ownerId": owner_id,
            "repo": REPO,
            "branch": "main",
            "autoDeploy": "yes",
            "rootDir": "apps/api",
            "envVars": api_env,
            "serviceDetails": {
                "runtime": "docker",
                "plan": "free",
                "region": REGION,
                "healthCheckPath": "/health",
                "envSpecificDetails": {"dockerfilePath": "./Dockerfile", "dockerContext": "."},
            },
        })
        if status not in (200, 201):
            print("api    · CREATE FAILED", status, body)
            return 1
        api_service = body["service"] if isinstance(body, dict) and "service" in body else body
        print(f"api    · created {api_service['id']}")

    api_url = service_url(api_service) or wait_for_url(api_service["id"])
    print(f"api    · {api_url}")

    # ------------------------------------------------------------ 2 · web
    web_service = find_service(WEB_NAME)
    if web_service:
        print(f"web    · exists {web_service['id']}")
    else:
        status, body = call("POST", "/services", {
            "type": "static_site",
            "name": WEB_NAME,
            "ownerId": owner_id,
            "repo": REPO,
            "branch": "main",
            "autoDeploy": "yes",
            "rootDir": "apps/app",
            # Inlined into the bundle at build time — not read at runtime.
            "envVars": [{"key": "EXPO_PUBLIC_API_URL", "value": f"{api_url}/api"}],
            "serviceDetails": {
                "buildCommand": "npm ci && npx expo export --platform web --output-dir dist",
                "publishPath": "dist",
                # Without this rewrite, refreshing on /coach/review returns 404:
                # the routes exist only in the client-side router.
                "routes": [{"type": "rewrite", "source": "/*", "destination": "/index.html"}],
            },
        })
        if status not in (200, 201):
            print("web    · CREATE FAILED", status, body)
            return 1
        web_service = body["service"] if isinstance(body, dict) and "service" in body else body
        print(f"web    · created {web_service['id']}")

    web_url = service_url(web_service) or wait_for_url(web_service["id"])
    print(f"web    · {web_url}")

    # --------------------------------------------- 3 · let the browser talk
    origins = ",".join(filter(None, [web_url, env.get("EXTRA_CORS_ORIGINS")]))
    status, _ = call("PUT", f"/services/{api_service['id']}/env-vars", [
        *[{"key": v["key"], "value": v["value"]} for v in api_env],
        {"key": "CORS_ORIGINS", "value": origins},
        {"key": "PUBLIC_BASE_URL", "value": api_url},
    ])
    print(f"cors   · {origins} ({status})")

    print("\n  API :", api_url)
    print("  WEB :", web_url)
    print("\n  First build takes a few minutes. Check /health on the API.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
