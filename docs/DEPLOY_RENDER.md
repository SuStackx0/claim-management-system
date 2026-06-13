# Deploying on Render

This repo ships a `render.yaml` Blueprint that stands up **two web services**: the FastAPI API and the Streamlit UI, wired together automatically.

## Prerequisites

- Code pushed to a GitHub/GitLab repo.
- A [Render](https://render.com) account.
- A Gemini API key (for live extraction).

## Deploy (Blueprint)

1. Render dashboard → **New** → **Blueprint**.
2. Connect the repo. Render reads `render.yaml` and proposes two services:
   - **plum-claims-api** — `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
   - **plum-claims-ui** — `streamlit run ui/streamlit_app.py --server.port $PORT --server.address 0.0.0.0`
3. Click **Apply**. Both build with `pip install -r requirements.txt`.

## Set the secret

`GEMINI_API_KEY` is `sync: false`, so Render won't read it from the file — set it manually:

- **plum-claims-api** service → **Environment** → add `GEMINI_API_KEY` = your key → save (triggers a redeploy).

Everything else is pre-set in `render.yaml`:

- `LLM_PROVIDER=gemini`, `DB_PATH=/tmp/claims.db`, `POLICY_PATH`, `TEST_CASES_PATH`.
- The UI's `API_BASE_URL` is auto-injected from the API service's public URL (`RENDER_EXTERNAL_URL`) — no manual wiring.

## Verify

- API health: open `https://plum-claims-api-XXXX.onrender.com/health` → `{"status":"ok","llm_provider":"gemini",...}`.
- UI: open the **plum-claims-ui** URL → Submit / Review / Eval pages.

## Notes & gotchas

- **Free tier sleeps** after ~15 min idle; the first request cold-starts (~30–60s, plus the one-time genai SDK import). Not stuck — just slow on first hit.
- **`DB_PATH=/tmp/claims.db` is ephemeral** — claims don't survive a restart/redeploy. Fine for a demo; for persistence attach a Render Disk or use Postgres (the `Repository` is the only DB seam to swap).
- **Gemini free tier = 5 req/min.** Each claim makes ~4 calls — pace live submissions, or use a billing-enabled key. The **Eval** page is mock-backed and unaffected.
- **Streamlit behind Render's proxy:** if the UI shows a blank page or websocket errors, append to its start command:
  `--server.headless true --server.enableCORS false --server.enableXsrfProtection false`.
- **Redeploys:** push to the connected branch → Render auto-builds. Or **Manual Deploy** from the dashboard.

## Alternative: Docker / local

Not deploying to Render? `docker compose up --build` brings the same two services up locally (see `docs/RUNNING_AND_TESTING.md`).
