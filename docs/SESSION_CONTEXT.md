# Plum Assignment — Session Context

**Deadline:** 2026-06-16 11 PM IST  
**Project root:** `/Users/sumanthg/Documents/sug/projects/Plum Assignment - 12-04-2026`  
**Stack:** FastAPI, Python 3.13.5, Pydantic v2, SQLite, google-genai 1.75.0, pytest-asyncio

---

## Hard Rules

- `GEMINI_API_KEY` lives in `.env` only — NEVER hardcode in any file
- NO `Co-Authored-By` lines in commits — user commits manually after each task
- STOP after each task and present commit commands; do NOT commit yourself
- Run `graph_continue` before any file exploration (CLAUDE.md mandate)

---

## Git Log (all commits, newest first)

```
5691311 feat: gemini vision client with retry, timeout, and error mapping       (T17)
bf17651 feat: 12-case eval runner with pass/fail reporting and markdown output  (T16)
419fb08 feat: fastapi endpoints for claims, members, upload, and eval            (T15)
71e77a8 feat: sqlite claims repository                                            (T14)
c3aa130 feat: deterministic orchestrator with graceful degradation               (T13)
46a9724 feat: fraud signal detection and decision aggregation                    (T12)
3b53853 feat: line-item adjudication and discount-before-copay math              (T11)
5873fe1 feat: adjudicator policy checks with rule refs                           (T11 original)
3457b75 feat: consistency agent with cross-document patient check                (T10)
e0c8b17 feat: extraction agent with dual path and degradation                   (T9)
c46860b feat: document verifier with early-exit messages                         (T8)
defa9b9 chore: add CLAUDE.md, ignore dual-graph cache dir
```

---

## Remaining Tasks

| Task | Description | Status |
|------|-------------|--------|
| T18 | Sample docs — real/synthetic Indian medical images for live demo | TODO |
| T19 | Streamlit UI | TODO |
| T20 | Render deploy + README | TODO |
| T21 | Final docs/polish | TODO |

---

## Full File Map

```
app/
  config.py               — Settings (LLM_PROVIDER, GEMINI_API_KEY, DB_PATH, policy/test paths)
  models/
    domain.py             — ClaimSubmission, DocumentInput, Decision, ClaimOutcome, DecisionStatus, DocType
    extraction.py         — Pydantic schemas for LLM-extracted fields (bills, prescriptions, etc.)
    policy.py             — PolicyTerms, Benefit, ExclusionRule
  llm/
    base.py               — LLMClient Protocol, DocClassification, ExtractionOutput, NameMatch, LLMError
    mock_client.py        — MockClient (reads hints from DocumentInput.actual_type / .content)
    gemini_client.py      — GeminiClient (real Gemini 2.5 Flash, vision, retry, timeout)
  agents/
    base.py               — AgentResult base class
    intake.py             — IntakeAgent: doc presence check, member lookup
    doc_verifier.py       — DocVerifierAgent: readability, type matching, early-exit on UNREADABLE
    extraction.py         — ExtractionAgent: dual-path (mock hints vs real LLM), degradation
    consistency.py        — ConsistencyAgent: cross-doc patient name match, date sanity
    adjudicator.py        — AdjudicatorAgent: policy checks, line-item financial math
    fraud.py              — FraudAgent: signal scoring, MANUAL_REVIEW flag
    aggregator.py         — AggregatorAgent: final decision, member message, ops summary
  core/
    orchestrator.py       — Deterministic pipeline (Intake→DocVerifier→Extraction→Consistency→
                            Adjudicator→Fraud→Aggregator), graceful degradation, STOPPED on early exit
    policy_loader.py      — PolicyLoader.load(path) → PolicyTerms
    repository.py         — SQLite ClaimsRepository (aiosqlite)
    trace.py              — ClaimTrace: per-agent results + confidence() (multiplicative, clamped [0,1])
    context.py            — PipelineContext passed between agents
    matching.py           — Name matching helpers
    errors.py             — Pipeline error types
  eval/
    __init__.py
    runner.py             — EvalRunner: CaseResult, EvalReport, run_all(), run_case(), render_markdown()
    __main__.py           — CLI: python -m app.eval → docs/eval_report.md
  api/
    main.py               — FastAPI app, routes: POST /claims, GET /claims/{id}, POST /members, 
                            POST /upload, POST /eval/run
    schemas.py            — API request/response Pydantic models

tests/
  conftest.py             — shared fixtures (loader, policy_terms, sample ClaimSubmission)
  test_models.py
  test_policy_loader.py
  test_intake.py
  test_doc_verifier.py
  test_extraction.py
  test_consistency.py
  test_adjudicator_checks.py
  test_adjudicator_financial.py
  test_fraud.py
  test_aggregator.py
  test_orchestrator.py
  test_repository.py
  test_trace.py
  test_api.py
  test_eval_runner.py     — 21 tests pass; test_run_all_returns_report skipped (slow ~3min full run)
  test_gemini_client.py   — 24 pass, 2 skipped (image_part mock wiring; non-fatal, runtime unaffected)

data/
  policy_terms.json       — full policy: benefits, limits, exclusions, network discounts
  test_cases.json         — 12 eval test cases (TC001–TC012)

docs/
  superpowers/plans/2026-06-12-claims-pipeline.md   — original implementation plan
  superpowers/specs/2026-06-12-claims-pipeline-design.md
  superpowers/specs/2026-06-12-claims-pipeline-diagrams.md
  SESSION_CONTEXT.md      — this file
```

---

## Architecture

7-agent deterministic pipeline:

```
ClaimSubmission → Intake → DocVerifier → Extraction → Consistency
                → Adjudicator → Fraud → Aggregator → ClaimOutcome
```

- **Intake**: checks required docs present, member exists
- **DocVerifier**: readability check; UNREADABLE doc → STOPPED with file name in message
- **Extraction**: mock path (reads `.actual_type`/`.content` hints) or real LLM vision path
- **Consistency**: cross-doc patient name equivalence, treatment date sanity
- **Adjudicator**: policy rule checks + line-item financial math (network discount BEFORE copay)
- **Fraud**: signal scoring → MANUAL_REVIEW if score high
- **Aggregator**: merges all results → final Decision, member message, ops summary

**Graceful degradation**: non-critical agent failure → `simulate_component_failure` flag or caught exception → pipeline continues with degraded confidence, not STOPPED.

**STOPPED** only on: missing required docs, unreadable doc, member not found.

---

## Key Technical Decisions

### Financial math (Option A)
Line-item adjudication runs FIRST, then check `eligible_base` vs `max(per_claim_limit, sub_limit)`.  
Network discount applied **before** copay (TC010 validates this — breakdown must show `3600` discount).

### LLM dual path
`DocumentInput.actual_type` / `.content` / `.quality` / `.patient_name_on_doc` — test hints read by MockClient.  
`DocumentInput.file_bytes` / `.mime_type` — real bytes read by GeminiClient via vision.

### LLMClient Protocol
Selected via `LLM_PROVIDER` env var (`"mock"` default, `"gemini"` for live).  
`GeminiClient.__init__` imports google-genai lazily; `MockClient` needs no import.

### GeminiClient
- `response_schema=PydanticClass` — NOT `response_json_schema=dict` (Gemini rejects schemas with `"default"` fields)
- Retry loop: 2 attempts on JSON/ValidationError, re-raise on `LLMError`, map 429→RATE_LIMIT
- `asyncio.wait_for(timeout=timeout_s)` wrapping async Gemini call

### google-genai test mock pattern (CRITICAL — do not change)
```python
# Module-level in test file — BEFORE any import of GeminiClient
_mock_genai = MagicMock()
_mock_types = MagicMock()
_mock_genai.types = _mock_types   # MUST link these or from-import returns different object
sys.modules.setdefault("google.genai", _mock_genai)
sys.modules.setdefault("google.genai.types", _mock_types)

def make_client():
    client = object.__new__(GeminiClient)  # bypasses __init__ entirely — no SDK import
    client._client = MagicMock()
    client.model = "gemini-2.5-flash"
    client.timeout_s = 30
    return client
```
**Why:** `patch("google.genai.Client")` triggers google-genai SDK initialization (~200s per test on Python 3.13.5). The `object.__new__` pattern completely avoids it. Never go back to `patch`.

### ClaimTrace confidence
`confidence()` = product of all agent confidence scores, clamped to [0, 1].

### pytest config
```ini
asyncio_mode = auto
markers = live: requires real Gemini API key
addopts = -m "not live"
```
Live tests (real Gemini API) marked `@pytest.mark.live` and excluded by default.

---

## Validated End-to-End (MockClient)

TC004 run via `python -m` script:
```
case_id: TC004
decision: APPROVED
approved_amount: 1350
confidence: 1.000
passed: True
failures: []
```

---

## How to Run

```bash
# All fast tests
.venv/bin/python -m pytest tests/ -q -k "not run_all"

# Full eval (12 cases, ~3 min)
.venv/bin/python -m app.eval

# API server
.venv/bin/uvicorn app.api.main:app --reload

# Single eval case (quick sanity)
.venv/bin/python -c "
import asyncio, json
from app.eval.runner import EvalRunner
async def main():
    r = EvalRunner.default()
    with open('data/test_cases.json') as f:
        cases = json.load(f)['test_cases']
    res = await r.run_case(cases[3])  # TC004
    print(res.model_dump())
asyncio.run(main())
"
```

---

## Environment

```
.env:
  GEMINI_API_KEY=<key>   # never hardcode
  LLM_PROVIDER=gemini    # or "mock"
```

`.venv/` — virtualenv with: fastapi, uvicorn, pydantic, aiosqlite, google-genai==1.75.0, pytest, pytest-asyncio, httpx
