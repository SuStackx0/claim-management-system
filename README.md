# Health Insurance Claims Pipeline

An automated health-insurance claims adjudication system. A FastAPI backend runs a
deterministic 7-agent pipeline — LLM-powered vision extraction of medical documents,
with all policy and financial logic in pure, testable code — and exposes it to a React
SPA (and a Streamlit client) for submitting claims, reviewing decisions with a full
audit trace, and running an evaluation suite.

---

## Quickstart

```bash
# 1. Create and activate an env
python -m venv .venv && source .venv/bin/activate   # (conda works too)
pip install -r requirements.txt

# 2. Set env vars
cp .env.example .env
# Edit .env: LLM_PROVIDER=mock (no key needed) | groq + GROQ_API_KEY | gemini + GEMINI_API_KEY

# 3. Run the API
uvicorn app.api.main:app --reload

# 4. Run a UI (new terminal) — React SPA or Streamlit
cd frontend && npm install && npm run dev        # React SPA
streamlit run ui/streamlit_app.py                # or the Streamlit client

# 5. Run the evaluation suite
python -m app.eval            # deterministic engine check (mock)
python -m app.eval --live     # real vision pipeline over generated document images
```

Or with Docker: `docker compose up` (API + UI).

**Mock mode** (default) injects structured fixtures — no API key, instant, deterministic.
**Vision mode** (`groq` / `gemini`) classifies and extracts from real document images.

---

## Architecture

```
ClaimSubmission ──► Intake ──► DocVerifier ──► Extraction ──► Consistency
                ──► Adjudicator ──► Fraud ──► Aggregator ──► ClaimOutcome
```

| Agent | Role |
|---|---|
| **Intake** | Required docs present, member lookup |
| **DocVerifier** | Classify + readability; UNREADABLE doc → STOPPED with filename |
| **Extraction** | Mock path (fixtures) or vision LLM → structured, validated fields |
| **Consistency** | Cross-doc patient-name match, treatment-date sanity |
| **Adjudicator** | Policy rule checks + line-item math (network discount before copay) |
| **FraudAgent** | Signal scoring; high score → MANUAL_REVIEW |
| **Aggregator** | Final decision, member message, ops summary |

**LLMClient Protocol**: `GroqClient` | `GeminiClient` | `MockClient` — swapped via `LLM_PROVIDER`.
**Decisions**: `APPROVED` | `PARTIAL` | `REJECTED` | `MANUAL_REVIEW` | `STOPPED`
**Confidence**: multiplicative product of all agent scores, clamped [0, 1].

The design patterns used across the codebase are mapped in **[docs/lld.md](docs/lld.md)**.

---

## Resilience & Failure Modes

The orchestrator is the failure boundary: **agents never throw past it.** Every step
becomes a typed `StepResult`, and the decision is *computed from the trace*, so any
outcome is reconstructable. Each failure class has a defined, tested response:

| Failure | Response |
|---|---|
| **Fatal agent** (Intake, DocVerifier, patient mismatch) | Pipeline stops; HTTP 200 `STOPPED` with a specific, member-facing message |
| **Degradable agent** (Extraction per-doc, Fraud) | Step `DEGRADED`/`SKIPPED`, confidence docked, pipeline continues, manual-review noted |
| **LLM** timeout / rate-limit / invalid schema | Wrapped in `LLMError`, retried with backoff, else step `DEGRADED` — the app never 500s on an LLM problem |
| **Bad client input** (malformed/invalid payload) | `422` with field detail — a client error, not a crash |
| **Persistence** (SQLite write) failure | Logged; the computed decision is **still returned** — a side-effect failure never discards adjudication |
| **Any unhandled error** | Global handler → structured `500 {"error": "internal_error"}`; full detail logged, internals never leaked |

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
  api/             ← FastAPI routes (/claims, /claims/upload, /eval/*, /health)
  core/            ← orchestrator, policy_loader, trace, repository (SQLite)
  eval/            ← EvalRunner: 12-case suite → eval_report.md (mock + live vision)
  llm/             ← LLMClient protocol, GroqClient, GeminiClient, MockClient
  models/          ← domain, extraction, policy Pydantic models
frontend/          ← React + Vite SPA (Submit / Review / Eval)
ui/                ← Streamlit client (Submit / Review / Eval)
scripts/
  generate_sample_docs.py  ← PIL-rendered synthetic medical images
  generate_eval_docs.py    ← one image per test-case document → eval_docs/
  run_live_eval.py         ← run cases through the live vision pipeline
eval_docs/         ← per-case document images for the live eval
data/
  policy_terms.json   ← full policy: benefits, limits, exclusions, network discounts
  test_cases.json     ← 12 evaluation cases (TC001–TC012)
tests/             ← unit + integration tests
```

---

## Env Vars

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `mock` \| `groq` \| `gemini` |
| `GROQ_API_KEY` | — | Required for `groq` vision mode |
| `GROQ_MODEL` | `meta-llama/llama-4-scout-17b-16e-instruct` | Groq multimodal model |
| `GEMINI_API_KEY` | — | Required for `gemini` mode |
| `DB_PATH` | `claims.db` | SQLite database path |
| `POLICY_PATH` | `data/policy_terms.json` | Policy config |
| `TEST_CASES_PATH` | `data/test_cases.json` | Evaluation cases |
| `API_BASE_URL` | `http://localhost:8000` | Used by the Streamlit UI |

---

## Evaluation

```bash
python -m app.eval            # deterministic: injected fixtures, no LLM → repeatable 12/12
python -m app.eval --live     # real vision: reads eval_docs/ images through the LLM
```

The live run renders each test-case document to an image (`scripts/generate_eval_docs.py`
→ `eval_docs/<case_id>_<file_id>.png`) and pushes it through the real classify → extract →
adjudicate path. Money and policy logic stay deterministic; only perception is the LLM.
The report is written to **[docs/eval_report.md](docs/eval_report.md)**.

---

## Running Tests

```bash
pytest -q -k "not run_all"   # fast suite (excludes the full 12-case run)
pytest -q                    # full suite
pytest -m live               # live vision tests (requires a provider key in .env)
```

---

## Deploy (Render)

See `render.yaml` — deploy via Render Blueprint:
1. Push the repo to GitHub
2. Connect in the Render dashboard → New Blueprint
3. Set the provider key (e.g. `GROQ_API_KEY`) in the API service env vars (`sync: false`)
4. Both services deploy automatically

> **Note:** Render free tier has cold starts (~30s).

---

## Key Design Decisions

- **Per-claim limit**: Line-item adjudication runs first, then caps against `max(per_claim_limit, sub_limit)`.
- **Network discount before copay**: discount applied to the gross amount, copay on the net.
- **Early exit on document issues**: UNREADABLE or missing required docs → `STOPPED` (HTTP 200, a domain outcome, not an error).
- **Graceful degradation**: a non-critical agent failure reduces confidence but doesn't stop the pipeline.
- **No LLM for policy/money logic**: all rule evaluation and financial math is pure Python reading `policy_terms.json`.
