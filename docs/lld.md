# LLD — Design Patterns

Quick map of the patterns used, where they live, and what they buy us.

## Structural / behavioural

| Pattern | Where | How |
|---|---|---|
| **Strategy** | `app/llm/base.py` (`LLMClient`) + `groq_client.py` / `gemini_client.py` / `mock_client.py` | The perception engine is an interface with interchangeable implementations; the pipeline never knows which LLM (or mock) it's talking to. |
| **Adapter** | `groq_client.py`, `gemini_client.py` | Wrap each vendor's HTTP/SDK and JSON shape into the common `LLMClient` methods, normalising all vendor errors into one `LLMError {kind}`. |
| **Null Object** | `app/llm/mock_client.py` | Deterministic stand-in `LLMClient` so the whole pipeline (and the eval) runs with no API key or network. |
| **Factory Method** | `make_llm()` (`app/api/main.py`), `_make_client()` (`scripts/run_live_eval.py`), `EvalRunner.default()` | Build the right client / fully-wired object from config (`LLM_PROVIDER`) without callers hard-coding constructors. |
| **Pipeline + Chain of Responsibility** | `app/core/orchestrator.py` over `app/agents/*` | A fixed ordered list of agents each transform a shared `ClaimContext`; a `fatal` agent short-circuits the chain with an early exit. |
| **Template Method** | `Agent` ABC (`app/agents/base.py`) + `Orchestrator.process()` | Agents implement only `run(ctx) -> StepResult`; the orchestrator owns the invariant skeleton (time it, append to trace, classify failure, persist). |
| **Repository** | `app/core/repository.py` | Hides SQLite behind `save/get/list`; the orchestrator depends on the seam, so storage can change without touching pipeline logic. |
| **Dependency Injection** | `Orchestrator(loader, llm, repository=…)`; agents receive `llm` in `__init__` | Collaborators are passed in (constructor injection) — no globals reached into, trivially swappable in tests/eval. |
| **Value Object / DTO** | `app/models/*.py`, `app/core/trace.py` (Pydantic v2) | Typed, self-validating data carriers (`ClaimSubmission`, `StepResult`, `Decision`); coercion lives in the extraction schemas. |
| **Singleton** | `settings` in `app/config.py` (pydantic-settings) | One validated config object imported app-wide. |

## Resilience / concurrency

| Pattern | Where | How |
|---|---|---|
| **Retry w/ exponential backoff + jitter** | `GroqClient._call` | Transient 429/5xx/timeout retried, honouring the server's retry window plus jitter so parallel calls don't re-collide. |
| **Bounded concurrency (semaphore)** | `ExtractionAgent` (`max_concurrency`) | Per-document vision calls fan out but are capped, so a free-tier rate limit isn't burst past. |
| **Graceful degradation / fault isolation** | `Orchestrator._degrade`, agent `fatal` flag, confidence ledger | Failures are classified *fatal* (early exit) vs *degradable* (mark `DEGRADED`, dock confidence, continue) — one component dying never crashes the claim. |
| **Deterministic short-circuit** | `ConsistencyAgent._names_match` | Cheap token match first; the LLM is only called for genuinely ambiguous names — fewer calls, stable behaviour. |
