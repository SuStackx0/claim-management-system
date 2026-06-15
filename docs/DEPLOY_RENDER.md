# Deploying on Render

This repo ships a `render.yaml` Blueprint that stands up **two web services**: the FastAPI API and the React SPA (static site), wired together automatically.

## Prerequisites

- Code pushed to a GitHub/GitLab repo.
- A [Render](https://render.com) account.
- A **Groq API key** (for live document extraction). If you have several keys, you only need **one** active at a time — keep the rest as spares (see below).

## Deploy (Blueprint)

1. Render dashboard → **New** → **Blueprint**.
2. Connect the repo. Render reads `render.yaml` and proposes two services:
   - **plum-claims-api** — `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
   - **plum-claims-ui** — React SPA, built with `npm install && npm run build`, served as a static site from `frontend/dist`.
3. Click **Apply**. The API builds with `pip install -r requirements.txt`.

## Set the secret

`GROQ_API_KEY` is `sync: false`, so Render won't read it from the file — set it manually:

- **plum-claims-api** service → **Environment** → add `GROQ_API_KEY` = your key → save (triggers a redeploy).

Use **one** of your Groq keys here. Everything else is pre-set in `render.yaml`:

- `LLM_PROVIDER=groq`, `GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct`, `DB_PATH=/tmp/claims.db`, `POLICY_PATH`, `TEST_CASES_PATH`.
- The UI's `VITE_API_BASE_URL` is auto-injected at build time from the API service's public URL (`RENDER_EXTERNAL_URL`) — no manual wiring. The browser calls the API cross-origin; the API allows it via CORS.

### Your spare Groq keys

The app reads a **single** `GROQ_API_KEY` — there is no key rotation. If your active key hits its rate limit, gets revoked, or you simply want to swap providers' keys:

1. **plum-claims-api** → **Environment** → edit `GROQ_API_KEY` → paste one of your other keys → save.
2. The save triggers an automatic redeploy with the new key.

Keep the other two keys somewhere safe (a password manager / your `.env`) as drop-in backups. There's no need to put more than one in Render at a time.

## Verify

- API health: open `https://plum-claims-api-XXXX.onrender.com/health` → `{"status":"ok","llm_provider":"groq",...}`.
- UI: open the **plum-claims-ui** URL → Submit / Review / Eval pages.

## Notes & gotchas

- **Free tier sleeps** after ~15 min idle; the first request cold-starts (~30–60s). Not stuck — just slow on the first hit.
- **`DB_PATH=/tmp/claims.db` is ephemeral** — claims don't survive a restart/redeploy. Fine for a demo; for persistence attach a Render Disk or use Postgres (the `Repository` is the only DB seam to swap).
- **Groq free tier is rate-limited** (requests + tokens per minute). Each claim makes ~4 vision calls, so pace live submissions during the demo. If you hit a limit, swap in a spare key (above). The **mock-backed eval** (`python -m app.eval`) is deterministic and unaffected by rate limits — only the `--live` run hits Groq.
- **React SPA routing:** the static service has a rewrite rule (`/* → /index.html`) in `render.yaml` so client-side routes resolve on refresh. If you change the build output dir, update `staticPublishPath`.
- **CORS:** the SPA calls the API on a different origin, so the API must allow the UI's origin. This works out of the box with the Blueprint's auto-injected `VITE_API_BASE_URL`; if you point the UI at a custom domain, make sure the API's CORS config allows it.
- **Redeploys:** push to the connected branch → Render auto-builds. Or **Manual Deploy** from the dashboard.

## Alternative: Docker / local

Not deploying to Render? `docker compose up --build` brings the same two services up locally (see `docs/RUNNING_AND_TESTING.md`).
