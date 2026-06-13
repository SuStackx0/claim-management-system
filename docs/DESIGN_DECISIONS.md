# Design Decisions & Scaling

## Architecture at a glance

```
Streamlit UI ──HTTP──▶ FastAPI ──▶ Orchestrator ──▶ [ agents, in order ]
                                                     Intake → DocVerifier → Extraction
                                                     → Consistency → Adjudicator → Fraud
                                                     → Aggregator → Decision
        LLM (Gemini)  ── classify / extract / name-match only
        Policy JSON   ── all coverage, limits, fraud thresholds
        SQLite        ── claim + trace persistence
```

Every agent appends a `StepResult` with typed `PolicyCheck`s (`check`, `result`, `rule_ref` → JSON path into the policy, `detail`). The trace is the audit spine: any decision is fully reconstructable from it.

## Key decisions & trade-offs

| Decision | Why | Trade-off |
|---|---|---|
| **Multi-agent pipeline** (one agent per concern) | Clean separation, independently testable, easy to insert/reorder steps; bonus points | Orchestration overhead; ordering is a contract |
| **LLM does *perception* only** (classify, extract, name-match); all policy/financial logic is pure Python | Deterministic, auditable decisions; eval doesn't depend on LLM variance | LLM can't "reason about" novel policy edge cases — by design |
| **`LLMClient` Protocol** with `GeminiClient` + `MockClient` | Swap real/mock at one seam; deterministic tests & eval | Mock must track the real output schema |
| **Policy loaded from `policy_terms.json`**, never hardcoded; every check carries a `rule_ref` | Config-driven; traceable to the exact rule | Needs schema validation on load (done via Pydantic) |
| **Trace-as-spine** (typed `ClaimTrace`) | Full explainability (20% of the rubric) | Verbose response payloads |
| **Graceful degradation**: fatal agents stop the pipeline; non-fatal failures are skipped with a ×0.7 confidence penalty | One flaky component doesn't sink the claim | Confidence is heuristic, not calibrated |
| **Synchronous in-request pipeline** | Simplest correct model for a take-home | Holds the connection 15–25s/claim under live LLM |
| **SQLite + sync repository wrapped in `asyncio.to_thread`** | Zero-config; event loop never blocked on disk | Single-writer; no horizontal scale (see below) |
| **Retry-with-backoff on transient LLM errors** (429/timeout), honoring Gemini's `retryDelay` | Per-minute rate-limit blips self-heal instead of failing the claim | Adds latency on contended calls |

## Scaling to 10×

> For the per-request failure-response taxonomy (fatal vs. degradable agents, bad-input
> handling, and the global error safety net), see **Resilience & Failure Modes** in the
> [README](../README.md#resilience--failure-modes).

The current design is single-node and processes each claim inline. At 10× the bottlenecks are concurrency, the datastore, and LLM throughput. The seams (`LLMClient`, `Repository`) are already isolated so most changes are swaps, not rewrites.

| Bottleneck | What breaks at 10× | Change | Status |
|---|---|---|---|
| **In-request processing** | Each claim holds a worker 15–25s (LLM-bound) → connection/thread exhaustion | Make submit async: `POST /claims` returns `202 + claim_id`; a worker pool (Arq/Celery + Redis) processes a queue; client polls `GET /claims/{id}` or gets a webhook | Documented (not built — premature for a take-home) |
| **SQLite** | Single-writer serializes concurrent writes; file-bound → can't share across workers | Postgres + connection pool. Repository is already the only DB seam → driver swap | Documented; seam ready |
| **LLM rate limit / cost** | Free tier = 5 req/min; ~4 calls per claim is the hard cap | (a) paid tier; (b) retry/backoff **[done]**; (c) run a claim's per-doc calls concurrently (`asyncio.gather`) to cut latency; (d) cache extraction by file-hash for re-submits | (b) done; rest documented |
| **Stateless scale-out** | One process can't absorb 10× | Run N uvicorn workers behind a load balancer — unblocked once on Postgres | Documented; app is already stateless (app-scoped singletons) |
| **Trace storage** | Full traces inline in each DB row bloat the table | Keep the decision summary in Postgres; ship full traces to object storage / a log store | Documented |
| **Duplicate submissions** | Retried POSTs double-process | Idempotency key on submission to dedupe | Documented |

## Known limitations

- **Transient LLM errors still surface as "document unreadable"** if retries are exhausted — a 429 is mapped to `DOCUMENT_UNREADABLE` with a "re-upload a clearer photo" message. Backoff makes this rare; the clean fix is a distinct *transient/system* error class. Documented, not yet split.
- **Submission-deadline check is skipped** — no submission timestamp in the test inputs; the check is wired but inert until one is provided.
