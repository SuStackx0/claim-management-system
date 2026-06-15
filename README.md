# Health Insurance Claims Pipeline

An automated health-insurance claims adjudication system. A FastAPI backend runs a
deterministic 7-agent pipeline — LLM-powered vision extraction of medical documents,
with all policy and financial logic in pure, testable code — and exposes it to a React
SPA (and a Streamlit client) for submitting claims, reviewing decisions with a full
audit trace, and running an evaluation suite.

---

## Run it locally

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

## Project structure

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
