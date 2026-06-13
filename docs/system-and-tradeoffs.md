# System & Trade-offs: Health Insurance Claims Adjudication

A FastAPI backend runs a deterministic multi-agent pipeline that adjudicates employee health-insurance claims against a JSON policy file. A thin HTTP client (Streamlit and Vite+React+TypeScript) calls it without importing pipeline code. Persistence is SQLite. LLM access is abstracted behind an `LLMClient` interface with `GeminiClient` (Gemini 2.5 Flash) and `MockClient` implementations, selected by environment variable.

---

## System at a Glance

The pipeline is a fixed-order orchestrator with early exits and seven specialized agents. Each agent returns a typed `StepResult` appended to a `ClaimTrace`. The final `Aggregator` computes a deterministic decision (APPROVED, PARTIAL, REJECTED, or MANUAL_REVIEW) from the trace alone, never re-running agent logic.

| Stage | Role | Type | Fatal? |
|-------|------|------|--------|
| **IntakeAgent** | Validate member, policy, amount, deadline, category | Pure code | Yes |
| **DocVerifierAgent** | Classify document type & readability; emit member-facing errors | LLM + code rules | Yes |
| **ExtractionAgent** | Structured field extraction with per-field confidence scores | LLM vision (async fan-out) | Degradable |
| **ConsistencyAgent** | Patient name, date, and amount cross-checks | Code + LLM fuzzy matching | Fatal on patient mismatch |
| **AdjudicatorAgent** | Exclusions, waiting periods, pre-auth, limits, line-item math (network discount → co-pay) | Pure code | Yes |
| **FraudAgent** | Same-day/monthly counts, high-amount flags, alteration detection; emit fraud_score | Pure code | Degradable |
| **Aggregator** | Compute final Decision from trace; compute approved_amount, reasons, confidence, member & ops messages | Pure code | — |

---

## Architectural Principles

### Trace as the Spine

The `ClaimTrace` is the single source of truth. Every agent appends a `StepResult` with a status (APPROVED, PARTIAL, FAIL, DEGRADED, SKIPPED), a reason, and a `rule_ref` JSON path into the policy file. The Aggregator computes the decision deterministically from the trace; no agent runs twice, and every decision is reproducible and auditable. Observability is structural, not an afterthought.

### Confidence as a Ledger

Confidence starts at 1.0 and degrades multiplicatively via timestamped entries: `{factor, reason}`. A DEGRADED step applies ×0.7; partial readability ×0.9; fuzzy name match ×0.95; low-confidence extracted field ×0.9. The final confidence score is transparent and contextual, guiding ops review of edge cases.

### LLM Used in Exactly Three Places

- Document classification and readability scoring (DocVerifier).
- Structured field extraction with confidence per field (Extraction).
- Fuzzy patient-name equivalence (Consistency).

Money, policy logic, and fraud rules are pure code. This boundary is non-negotiable: adjudication must be testable to the rupee and traceable to a policy rule.

### Deterministic Money

The AdjudicatorAgent applies policy rules in a fixed order, emitting trace entries keyed to policy JSON paths. Network discounts are applied *before* co-pay calculation. Every line-item and summary amount is computed once and recorded in the trace. No LLM touches arithmetic.

### Graceful Degradation

Fatal agents (Intake, DocVerifier, Adjudicator) stop the pipeline and return a STOPPED decision with a member-facing message, HTTP 200. A document problem is a domain outcome, not a server error. Degradable agents (Extraction, Fraud) emit DEGRADED or SKIPPED results, dock confidence, and let the pipeline continue. LLM timeout, rate-limit, or schema-invalid responses trigger 1 retry, then DEGRADED; the app never 500s on an LLM failure. `simulate_component_failure: true` forces FraudAgent to raise, exercising the real degradation path.

### Persistence as a Side Effect

Claims, decisions, and full traces are written to SQLite via `asyncio.to_thread`, off the main event loop. A database write failure is logged but never discards an already-computed decision. The app prioritizes correctness over persistence.

---

## Key Decisions & Trade-offs

| Decision | Chosen | Rejected & Why |
|----------|--------|----------------|
| **Stack** | FastAPI backend + thin HTTP-only client (Streamlit, Vite+React+TS) | Full Next.js SSR — weaker fit for Python AI tooling and pytest; React SPA as primary effort — UI polish isn't where the grade is. |
| **Orchestration** | Hand-rolled deterministic orchestrator with fixed agent order and early exits | LLM supervisor / dynamic routing — non-deterministic adjudication is indefensible in insurance and flaky on eval; LangGraph / CrewAI — want full ownership of every line for live-extension interview. |
| **Document Intake** | Dual path: vision LLM for real uploads; test runner injects content post-extraction | Vision-only — eval becomes LLM-flaky, one misread digit breaks expected amounts; structured-only — fails the AI-integration criterion. |
| **Money & Policy** | Pure deterministic code; LLM never does arithmetic or rule application | LLM adjudication — untestable to the rupee and unmaintainable. |
| **LLM Provider** | Gemini 2.5 Flash (free tier) behind `LLMClient` interface + `MockClient` | Anthropic / OpenAI — no free tier; interface makes provider swappable anyway. |
| **Persistence** | SQLite (claims, decisions, traces as JSON; few indexed columns) | Postgres — ops overhead for this scale; in-memory — review UI needs history and fraud needs lookback. |
| **Deployment** | Render free tier, two services from one repo (render.yaml) | Railway — card requirement; HF Spaces — fiddlier Docker setup; Streamlit Cloud split — API/UI coupling breaks. |
| **Client Design** | Thin HTTP-only client (never imports pipeline code) | Direct import — collapses the API-contract story; the API must be the product. |

---

## Failure Handling & Graceful Degradation

### Fatal vs. Degradable

- **Fatal agents** (Intake, DocVerifier, Adjudicator, Consistency on patient mismatch) halt the pipeline. A fatal failure returns a `STOPPED` decision with a member-facing error message and HTTP 200 OK. This reflects the domain: a bad document or invalid policy match is a valid business outcome, not a server error.
- **Degradable agents** (Extraction, Fraud) emit DEGRADED, PARTIAL, or SKIPPED results, dock confidence by a multiplicative factor, and allow the pipeline to continue. The decision is still computed, but ops review is flagged.

### LLM Robustness

An LLM timeout, rate-limit, or schema-validation error triggers exactly one automatic retry. If the retry fails, the agent returns DEGRADED. The app never returns HTTP 500 due to an LLM problem. `simulate_component_failure: true` forces the FraudAgent to raise an exception, exercising this degradation path in testing.

### HTTP 200 on STOPPED

A claim stopped due to invalid policy, missing member, or unreadable document returns HTTP 200 with a `Decision(status=STOPPED, member_message="...", ...)`. This is semantically correct: the request was valid, the decision is deterministic, and the member needs to know why. Ops logs the `rule_ref` and decision trace for review.

---

## Known Limitations & 10x Scaling

| Limitation | Current | 10x Scaling Move | Seam |
|-----------|---------|------------------|------|
| **Sync request/response** | Single claim processed end-to-end per HTTP call | Claims become async jobs on a queue (SQS, Celery). Orchestrator and agent contracts unchanged; execution model moves to workers and polling/webhook. | Orchestrator + agent interfaces are pure functions; the execution shell is decoupled. |
| **SQLite + ephemeral disk** | On Render free tier, local file | Postgres on a managed service (RDS, Neon). `Repository` module is the only abstraction; swap the implementation. | `SqliteRepository` → `PostgresRepository`; same interface. |
| **Single LLM provider, no caching** | All extraction calls hit Gemini live | Add provider fallback chain + extraction result caching by document hash. | `LLMClient` interface already abstracts provider; add a caching layer and fallback list. |
| **Fraud is rules-only** | Hard-coded thresholds | At scale: feature store + anomaly detection model; emit fraud_score from model, same trace entry. | `FraudAgent` returns a typed `FraudResult`; implement via rules or ML, same contract. |
| **Single policy JSON** | Loaded at startup from `policy_terms.json` | Versioned policy store; `rule_ref` already keys every decision to a policy term. | `rule_ref` is a JSON path; version it in the path or as metadata. Aggregator reads the path; retrieval is unchanged. |

---

## Out of Scope

- **Authentication / Multi-tenancy** — Single-user, single-client for assignment scope.
- **Real PII handling** — Flagged with TODO comments; encrypt at rest and in transit in production.
- **Real OCR preprocessing** — Deskew, denoise, orientation correction. Current approach: prompt-level best effort; readability score flags issues.
- **Regional-language extraction** — Detection and fallback flagged as unextracted; not in scope.
- **Payment / Disbursement** — Claims adjudication ends at the decision; payment flows are separate.
