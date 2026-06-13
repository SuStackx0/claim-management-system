# Plum Claims Pipeline — AI Engineer Assignment

Automated health insurance claims adjudication system. A FastAPI backend runs a deterministic 7-agent pipeline (LLM-powered document extraction via Gemini 2.5 Flash, pure-code policy/financial logic) and a Streamlit UI for submitting claims, reviewing decisions, and running the 12-case evaluation suite.

---

## Quickstart

```bash
# 1. Create and activate env (conda shown; venv works too)
conda create -n plum python=3.13 -y && conda activate plum
pip install -r requirements.txt

# 2. Set env vars
cp .env.example .env
# Edit .env: set LLM_PROVIDER=mock (no key needed) or LLM_PROVIDER=gemini + GEMINI_API_KEY=...

# 3. Run the API
uvicorn app.api.main:app --reload

# 4. Run the UI (new terminal)
streamlit run ui/streamlit_app.py

# 5. Run the 12-case eval suite
python -m app.eval
# → writes docs/eval_report.md
```

**Mock mode** (default) uses deterministic test hints — no API key, instant responses.  
**Gemini mode** (`LLM_PROVIDER=gemini`) uses real vision LLM to classify and extract from uploaded images.

---

## Architecture

```
ClaimSubmission ──► Intake ──► DocVerifier ──► Extraction ──► Consistency
                ──► Adjudicator ──► Fraud ──► Aggregator ──► ClaimOutcome
```

| Agent | Role |
|---|---|
| **Intake** | Required docs present, member lookup |
| **DocVerifier** | Readability check; UNREADABLE doc → STOPPED with filename |
| **Extraction** | Mock path (test hints) or Gemini vision → structured fields |
| **Consistency** | Cross-doc patient name match, treatment date sanity |
| **Adjudicator** | Policy rule checks + line-item math (network discount before copay) |
| **FraudAgent** | Signal scoring; high score → MANUAL_REVIEW |
| **Aggregator** | Final decision, member message, ops summary |

**LLMClient Protocol**: `GeminiClient` (real) | `MockClient` (test) — swapped via `LLM_PROVIDER` env var.  
**Decisions**: `APPROVED` | `PARTIAL` | `REJECTED` | `MANUAL_REVIEW` | `STOPPED`  
**Confidence**: multiplicative product of all agent scores, clamped [0, 1].

---

## Resilience & Failure Modes

The orchestrator is the failure boundary: **agents never throw past it.** Every step
becomes a typed `StepResult`, and the decision is *computed from the trace*, so any
outcome is reconstructable. Each failure class has a defined, tested response:

| Failure | Response |
|---|---|
| **Fatal agent** (Intake, DocVerifier, patient mismatch) | Pipeline stops; HTTP 200 `STOPPED` with a specific, member-facing message |
| **Degradable agent** (Extraction per-doc, Fraud) | Step `DEGRADED`/`SKIPPED`, confidence docked, pipeline continues, manual-review noted (TC011) |
| **LLM** timeout / rate-limit / invalid schema | Wrapped in `LLMError`, one retry where sensible, else step `DEGRADED` — the app never 500s on an LLM problem |
| **Bad client input** (malformed or invalid upload payload) | `422` with field detail — a client error, not a crash |
| **Persistence** (SQLite write) failure | Logged; the computed decision is **still returned** — a side-effect failure never discards adjudication |
| **Any unhandled error** | Global handler → structured `500 {"error": "internal_error"}`; full detail logged, internals never leaked to the member |

### Single points of failure & scaling to 10×

The current design is single-node by choice; the SPOFs are deliberate, deferred cuts
sitting behind isolated seams (`LLMClient`, `Repository`, the agent `Protocol`,
`rule_ref`) so each is a contained swap, not a rewrite. The full SPOF table and the
10× plan (queue/workers, Postgres, provider limits, idempotency) live in
**[docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md)**.

---

## Project Structure

```
app/
  agents/          ← 7 agents (intake, doc_verifier, extraction, consistency,
                               adjudicator, fraud, aggregator)
  api/             ← FastAPI routes (POST /claims, GET /claims, POST /upload, POST /eval/run)
  core/            ← orchestrator, policy_loader, trace, repository (SQLite)
  eval/            ← EvalRunner: 12-case suite → eval_report.md
  llm/             ← LLMClient protocol, GeminiClient, MockClient
  models/          ← domain, extraction, policy Pydantic models
ui/
  streamlit_app.py ← Submit / Review / Eval pages
  helpers.py       ← HTTP helpers (get/post)
  render.py        ← render_decision / render_trace
scripts/
  generate_sample_docs.py  ← PIL-rendered synthetic medical images
sample_docs/       ← 6 pre-generated demo images
data/
  policy_terms.json   ← full policy: benefits, limits, exclusions, network discounts
  test_cases.json     ← 12 eval cases (TC001–TC012)
tests/             ← 160+ tests, all pass
```

---

## Env Vars

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `mock` or `gemini` |
| `GEMINI_API_KEY` | — | Required for `gemini` mode |
| `DB_PATH` | `claims.db` | SQLite database path |
| `POLICY_PATH` | `data/policy_terms.json` | Policy config |
| `TEST_CASES_PATH` | `data/test_cases.json` | Eval test cases |
| `API_BASE_URL` | `http://localhost:8000` | Used by Streamlit UI |

---

## Running Tests

```bash
# Fast suite (excludes slow 12-case full run)
pytest -q -k "not run_all"

# Full suite including 12-case eval (~3 min)
pytest -q

# Live Gemini tests (requires GEMINI_API_KEY in .env)
pytest -m live
```

---

## Deploy (Render)

See `render.yaml`. Deploy via Render Blueprint:
1. Push repo to GitHub
2. Connect in Render dashboard → New Blueprint
3. Set `GEMINI_API_KEY` in the `plum-claims-api` service env vars (marked `sync: false`)
4. Both services deploy automatically

> **Note:** Render free tier has cold starts (~30s). The eval run takes ~3 min on mock mode.

---

## Key Design Decisions

- **Option A per-claim limit**: Line-item adjudication runs first, then cap against `max(per_claim_limit, sub_limit)`.
- **Network discount before copay**: TC010 validates this — discount applied to gross amount, copay on the net.
- **Early exit on document issues**: UNREADABLE or missing required docs → `status: STOPPED` (HTTP 200, domain outcome, not error).
- **Graceful degradation**: Non-critical agent failure reduces confidence but doesn't stop the pipeline.
- **No LLM for policy/money logic**: All rule evaluation and financial math is pure Python reading `policy_terms.json`.
