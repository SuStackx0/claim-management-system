# Design: Health Insurance Claims Processing System (Plum AI Engineer Assignment)

**Date:** 2026-06-12
**Status:** Approved in brainstorming; pending implementation plan
**Deadline:** Tuesday 2026-06-16, 11:00 PM IST

---

## 1. Problem

Automate manual adjudication of employee health-insurance claims. A member submits member details, a claim category, a claimed amount, and medical documents (images/PDFs). The system must:

1. Validate the submission and catch document problems **before** any decisioning, with specific, actionable member-facing errors.
2. Extract structured data from messy real-world Indian medical documents.
3. Adjudicate against `policy_terms.json` (never hardcoded) and produce `APPROVED | PARTIAL | REJECTED | MANUAL_REVIEW` with approved amount, reasons, and a confidence score.
4. Make every decision fully reconstructable from a trace.
5. Degrade gracefully when any component fails.

Graded weights: System Design 30% (multi-agent bonus), Engineering Quality 25%, Observability 20%, AI Integration 15%, Document Verification 10%. All 12 cases in `test_cases.json` must be evaluated and reported.

## 2. Decisions Made (with rejected alternatives)

| Decision | Chosen | Rejected & why |
|---|---|---|
| Stack | **FastAPI backend + Streamlit thin client over HTTP** | Full Next.js (weaker fit for Python AI tooling and pytest story); React SPA (UI polish is not where the grade is — time goes to engine/tests instead) |
| Orchestration | **Hand-rolled deterministic orchestrator running specialized agents in fixed order with early exits** | LLM supervisor / dynamic routing (non-deterministic adjudication is indefensible in insurance, flaky on eval); LangGraph/CrewAI (must own every line for the live-extension interview) |
| Document intake | **Dual path** — vision LLM for real uploads; eval runner injects test-case content post-extraction | Vision-only (eval becomes LLM-flaky; a misread digit breaks expected amounts); structured-only (fails the AI-integration criterion) |
| Money & policy logic | **Pure deterministic code**; LLM never does arithmetic or rule application | LLM adjudication (untestable to the rupee, weak interview answer) |
| LLM provider | **Gemini 2.5 Flash free tier behind an `LLMClient` interface, plus `MockClient`** | Anthropic/OpenAI (no free tier; provider is swappable behind interface anyway) |
| Persistence | **SQLite** (claims, decisions, traces as JSON; few indexed columns) | Postgres (ops overhead, not where the points are); in-memory (review UI needs history; fraud checks need lookback) |
| Deploy | **Render free tier, two services from one repo** (`render.yaml`) | Railway (card requirement), HF Spaces (fiddlier Docker), Streamlit Cloud split (two platforms) |
| UI | **Streamlit calling the API over HTTP only** — never imports pipeline code | Direct import (collapses the API contract story; the API must be the product) |

## 3. Architecture (HLD)

```
┌──────────────┐   HTTP    ┌────────────────────────────────────────┐
│  Streamlit   │ ────────► │  FastAPI                               │
│  (thin UI)   │           │  POST /claims          (submit)        │
│ - Submit     │           │  GET  /claims          (list)          │
│ - Review     │           │  GET  /claims/{id}     (decision+trace)│
│ - Eval       │           │  POST /eval/run        (12 test cases) │
└──────────────┘           │  GET  /health                          │
                           │  ┌──────────────────────────────────┐  │
                           │  │ ORCHESTRATOR (deterministic)     │  │
                           │  │  1 IntakeAgent      (code)       │  │
                           │  │  2 DocVerifierAgent (LLM+code) ──┼── early exit
                           │  │  3 ExtractionAgent  (LLM, async  │  │
                           │  │     fan-out per document)        │  │
                           │  │  4 ConsistencyAgent (code+LLM) ──┼── early exit
                           │  │  5 AdjudicatorAgent (PURE CODE)  │  │
                           │  │  6 FraudAgent       (code)       │  │
                           │  │  7 Aggregator       (code)       │  │
                           │  └──────────────────────────────────┘  │
                           │   every step appends to the TRACE      │
                           └──────────┬─────────────────────────────┘
                                      │
                  SQLite (claims, decisions, traces)
                  policy_terms.json   (loaded+validated at startup)
                  LLMClient interface → GeminiClient | MockClient
```

Core properties:

- **Deterministic orchestrator.** Fixed agent order; owns the trace; classifies each agent failure as *fatal* (early exit with member-facing message) or *skippable* (mark step `DEGRADED`, dock confidence, continue). `simulate_component_failure: true` forces FraudAgent to raise — graceful degradation (TC011) uses the same mechanism, not a special case.
- **LLM in exactly three places:** document classification + readability, field extraction, fuzzy patient-name equivalence. Everything touching money or policy rules is pure code reading `policy_terms.json`.
- **Trace is the spine.** Agents return typed `StepResult`s appended to a `ClaimTrace`; the Aggregator *computes the decision from the trace*. Observability is structural, not logged-on-the-side.
- **Confidence is a ledger.** Starts at 1.0; multiplicative entries `{factor, reason}` (DEGRADED step ×0.7, PARTIAL readability ×0.9, fuzzy name match ×0.95, low-confidence extraction field ×0.9). Ledger is part of the trace.

## 4. Component Contracts (LLD)

All domain objects are Pydantic v2 models. Every agent implements:

```python
class Agent(Protocol):
    name: str
    fatal: bool                      # is failure an early-exit?
    async def run(self, ctx: ClaimContext) -> StepResult: ...
```

`ClaimContext` is the accumulating state: claim, member, policy view, document verdicts, extractions, findings, trace.

### 4.1 IntakeAgent — pure code, fatal
- **In:** `ClaimSubmission {member_id, policy_id, claim_category, treatment_date, claimed_amount, documents[], claims_history?, ytd_claims_amount?, simulate_component_failure?}`
- **Out:** validated `Claim`, resolved `Member`, `PolicyView` for the category
- **Checks:** member in roster; policy active on treatment date; amount ≥ `submission_rules.minimum_claim_amount`; within `deadline_days_from_treatment`; category in `opd_categories`
- **Errors:** `MEMBER_NOT_FOUND | POLICY_INACTIVE | AMOUNT_BELOW_MINIMUM | DEADLINE_EXCEEDED | INVALID_CATEGORY`

### 4.2 DocVerifierAgent — LLM classify/readability + code rules; fatal (early-exit gate)
- **In:** documents; `document_requirements[category]` from policy
- **Out:** per-doc `DocVerdict {detected_type, readability: GOOD|PARTIAL|UNREADABLE, confidence}`; requirements diff `{missing_types[], unexpected_types[]}`; member-facing message on failure
- **Behavior:** wrong/missing type → names what was uploaded and what is required (TC001); unreadable required doc → `REUPLOAD_REQUIRED` naming the exact file, claim **not** rejected (TC002)
- **Errors:** `MISSING_REQUIRED_DOCUMENT | WRONG_DOCUMENT_TYPE | DOCUMENT_UNREADABLE`

### 4.3 ExtractionAgent — LLM vision, asyncio fan-out per doc; degradable
- **In:** verified documents
- **Out:** per doc-type model (`PrescriptionData`, `BillData` w/ line items, `LabReportData`, `PharmacyBillData`), per-field confidence, `unextracted_fields[]`, `source: "vision"|"provided"`
- **Behavior:** vision path = doc-type-specific prompt → JSON-schema output → Pydantic validation → 1 retry → else doc marked DEGRADED; test path = injected content
- **Errors:** `EXTRACTION_FAILED` (per-doc, non-fatal)

### 4.4 ConsistencyAgent — code + LLM fuzzy names; fatal on patient mismatch only
- **In:** extractions, member + dependents
- **Checks:** patient names pairwise across docs and vs member roster (fuzzy: "R. Kumar" ≈ "Rajesh Kumar"; "Arjun Mehta" ≠) (TC003); document dates vs treatment_date; bill total vs claimed amount
- **Out:** `ConsistencyFinding[] {check, severity: FATAL|WARNING, detail}`
- **Errors:** `PATIENT_MISMATCH` (fatal, includes the names found per document); `DATE_MISMATCH | AMOUNT_MISMATCH` (warnings, dock confidence)

### 4.5 AdjudicatorAgent — pure code, zero LLM; the core
- **In:** claim, extractions, full policy
- **Ordered checks, each emitting a trace entry with `rule_ref` (JSON path into policy_terms.json):**
  1. Exclusions — diagnosis/treatment vs `exclusions.*` (TC012)
  2. Waiting periods — condition match vs `waiting_periods.specific_conditions`, computes and reports `eligible_from` (TC005)
  3. Pre-authorization — `high_value_tests_requiring_pre_auth` + thresholds (TC007)
  4. Limits — per-claim, category sub-limit, annual OPD vs YTD (TC008)
  5. Line-item adjudication — vs `covered_procedures` / `excluded_procedures`, verdict + reason per line (TC006)
  6. Financial math — network discount (`network_discount_percent`) applied **before** co-pay (`copay_percent`), breakdown in trace (TC004: 1500→1350; TC010: 4500→3600→3240)
- **Out:** `LineItemVerdict[]`, `payable_amount`, `applied_rules[]`
- **Errors:** none expected (pure function of validated inputs); orchestrator treats a raise as fatal internal error

### 4.6 FraudAgent — pure code rules; degradable (TC011 kills this one)
- **In:** claim, `claims_history`, `fraud_thresholds`
- **Checks:** same-day count > `same_day_claims_limit` (TC009); monthly count; amount > `auto_manual_review_above`; alteration flags from extraction
- **Out:** `FraudSignal[] {signal, detail}`, fraud_score ∈ [0,1]

### 4.7 Aggregator — pure code
- **In:** complete `ClaimTrace`
- **Logic:** fatal already exited → here: fraud signals ⇒ `MANUAL_REVIEW`; all line items rejected ⇒ `REJECTED`; some rejected ⇒ `PARTIAL`; all approved ⇒ `APPROVED`; confidence < threshold ⇒ append manual-review recommendation
- **Out:** `Decision {status, approved_amount, reasons[], confidence, member_message, ops_summary}`

### 4.8 LLMClient interface
```python
class LLMClient(Protocol):
    async def classify_document(self, doc: DocumentInput) -> DocClassification: ...
    async def extract(self, doc: DocumentInput, schema: type[BaseModel]) -> ExtractionResult: ...
    async def names_equivalent(self, a: str, b: str) -> NameMatch: ...
```
Implementations: `GeminiClient` (google-genai SDK, `gemini-2.5-flash`, JSON-schema response mode, 30s timeout, 1 retry on validation failure) and `MockClient` (canned outputs keyed to bundled sample docs; selected via `LLM_PROVIDER` env var). All raises are wrapped into `LLMError {kind: TIMEOUT|RATE_LIMIT|SCHEMA_INVALID|PROVIDER_ERROR}`.

## 5. Trace Schema

```json
{
  "claim_id": "CLM-2024-0042",
  "pipeline_version": "1.0.0",
  "started_at": "...", "completed_at": "...",
  "steps": [
    {
      "step": "ADJUDICATION",
      "agent": "AdjudicatorAgent",
      "status": "PASS | FAIL | DEGRADED | SKIPPED",
      "duration_ms": 12,
      "checks": [
        {
          "check": "WAITING_PERIOD",
          "result": "FAIL",
          "rule_ref": "waiting_periods.specific_conditions.diabetes",
          "detail": {
            "condition_matched": "diabetes",
            "member_join_date": "2024-09-01",
            "waiting_days": 90,
            "eligible_from": "2024-11-30",
            "treatment_date": "2024-10-15"
          }
        }
      ],
      "confidence_entries": [{ "factor": 0.7, "reason": "FraudAgent failed, step skipped" }],
      "error": null
    }
  ],
  "confidence_ledger": [],
  "decision": {}
}
```

Invariants: every check carries a `rule_ref` into `policy_terms.json`; `detail` carries the numbers so all member/ops messages are rendered **from trace data** (TC005's eligibility date, TC010's discount→co-pay breakdown), never composed ad hoc.

## 6. Error Handling & Degradation

- Agents never throw past the orchestrator; all failures become `StepResult(status=FAIL, error=...)`.
- Fatal agents (Intake, DocVerifier, Consistency-on-patient-mismatch) → pipeline stops, response is a structured early-exit with the member-facing message; HTTP 200 with `status: "STOPPED"` (a document problem is a domain outcome, not a server error).
- Degradable agents (Extraction per-doc, Fraud) → step marked DEGRADED/SKIPPED, confidence ledger entry, pipeline continues, decision notes incomplete processing + manual-review recommendation (TC011).
- LLM failures: timeout/rate-limit/schema-invalid → 1 retry where sensible → DEGRADED. The app never 500s on an LLM problem.
- `simulate_component_failure: true` in a submission forces FraudAgent to raise (exercises the real degradation path).

## 7. Eval Runner

- `POST /eval/run` and CLI `python -m app.eval`.
- Loads `test_cases.json`, runs each case through the **real pipeline** (content injected post-extraction; failure flag honored).
- Assertions per case: decision matches; `approved_amount` matches; expected `rejection_reasons` present in trace; confidence bounds; mechanically-checkable `system_must` items (e.g. TC001 message names both doc types; TC010 breakdown present).
- Output: `docs/eval_report.md` — full decision + trace per case, pass/fail, explanation of mismatches. Regenerated by command; deliverable #4.

## 8. Testing Strategy

1. **Unit (bulk):** AdjudicatorAgent vs every policy rule incl. boundaries (exactly ₹5,000; day-90 treatment; rounding on discount/co-pay); Aggregator decision matrix; confidence ledger; IntakeAgent validations. No LLM.
2. **Pipeline integration:** all 12 cases as parametrized pytest (reusing the eval runner); failure injection — kill each agent in turn, assert no 500, DEGRADED in trace, lower confidence.
3. **LLM contract tests:** with MockClient — schema rejection, retry path, timeout→DEGRADED. Real-Gemini tests `@pytest.mark.live`, excluded from CI.

## 9. UI (Streamlit, thin HTTP client)

- **Submit:** member dropdown (from roster), category, date, amount; file upload **or** "load sample documents" picker; result = early-exit error rendered prominently, or decision summary.
- **Review:** claim list → decision banner, approved-amount breakdown card, line-item verdict table, expander per pipeline step (checks, rule_refs, confidence ledger).
- **Eval:** button to run all 12 cases; results table with per-case drill-down.

## 10. Tech Specs

| Concern | Choice |
|---|---|
| Language | Python 3.12 |
| API | FastAPI + Uvicorn, fully async handlers |
| Domain models | Pydantic v2 |
| Persistence | SQLite (stdlib `sqlite3`; traces/decisions as JSON columns + indexed claim_id/member_id/date); thin repository module |
| LLM | `google-genai` SDK, `gemini-2.5-flash`, JSON-schema response mode; `MockClient` fallback via `LLM_PROVIDER` env |
| UI | Streamlit, `requests`/`httpx` to the API (`API_BASE_URL` env) |
| Tests | pytest + pytest-asyncio; coverage on `app/core` and `app/agents` |
| Docs gen | eval report generated by the eval runner |
| Deploy | Render free tier ×2 services via `render.yaml` (api: uvicorn; ui: streamlit); env vars: `GEMINI_API_KEY`, `LLM_PROVIDER`, `API_BASE_URL` |
| Repo | GitHub; conventional commits per component |

```
repo/
├── app/
│   ├── api/            # FastAPI routers, request/response schemas
│   ├── core/           # orchestrator, trace, confidence, policy loader, repository
│   ├── agents/         # intake, doc_verifier, extraction, consistency, adjudicator, fraud, aggregator
│   ├── llm/            # LLMClient protocol, gemini_client, mock_client
│   └── eval/           # eval runner (also a CLI)
├── ui/streamlit_app.py
├── tests/
├── sample_docs/        # generated mock document images (+ generator script)
├── docs/               # architecture.md, contracts.md, eval_report.md, diagrams
├── data/policy_terms.json, test_cases.json
└── render.yaml
```

## 11. Known Limitations & 10x Scaling Story (for the architecture doc)

- **Sync request/response pipeline.** At 10x, claims become jobs: queue (SQS/Celery), pipeline as workers, decision delivered via polling/webhook. The orchestrator/agent contracts are unchanged — only the execution shell moves.
- **SQLite + ephemeral Render disk.** Swap for Postgres; repository module is the seam.
- **Single LLM provider, no caching.** Add provider fallback chain and extraction caching by document hash.
- **Fraud is rules-only.** At scale: feature store + anomaly model; agent contract already isolates it.
- **Policy loaded from a single JSON.** At scale: versioned policy store; `rule_ref` already keys every decision to a policy version.

## 12. Out of Scope (conscious cuts)

- Auth/multi-tenancy; real member PII handling.
- Real OCR preprocessing (deskew/denoise) — prompt-level best effort only, flagged via readability.
- Regional-language extraction — flagged as unextracted, per the documents guide.
- Payment/disbursement flows.
