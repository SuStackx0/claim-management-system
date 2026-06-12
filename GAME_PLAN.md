# Plum AI Engineer Assignment — What They Want & How to Crack It

## TL;DR

Build an **automated health insurance claims adjudicator**: a member submits a claim (member details + claim type + amount + medical documents), and the system validates documents, extracts data from them with an LLM, applies policy rules from `policy_terms.json`, and outputs a decision — `APPROVED` / `PARTIAL` / `REJECTED` / `MANUAL_REVIEW` — with an approved amount, reasons, confidence score, and a **complete audit trace** of every check it ran.

It's a real Plum problem (they process 75k+ claims/year manually). They're hiring for their AI Pod, so this assignment *is* the job.

---

## 1. What exactly must the system do (the 6 non-negotiables)

1. **Accept a claim submission** — member ID, claim category (consultation/diagnostic/pharmacy/dental/vision/alt-medicine), treatment date, claimed amount, documents (images/PDFs).
2. **Catch document problems EARLY** — before any decisioning:
   - Wrong doc type uploaded (prescription where a bill is needed) → stop, tell them *exactly* what was uploaded vs. what's required. Generic errors = fail.
   - Unreadable/blurry doc → ask for re-upload of *that specific document*, don't reject the claim.
   - Documents belonging to *different patients* (cross-doc consistency) → stop, name the names found.
3. **Extract structured info** from messy documents — handwritten Rx, stamps over text, phone photos, medical shorthand (HTN, T2DM).
4. **Decide** — one of the 4 decisions + approved amount + reason + confidence score.
5. **Explainable** — an ops person must reconstruct *exactly* why any decision happened from the trace alone. This is worth 20% on its own.
6. **Degrade gracefully** — LLM timeouts/parse failures must not crash the pipeline; continue with what you have, lower confidence, recommend manual review.

**Hard rule:** policy logic must be *read from `policy_terms.json`*, not hardcoded.

---

## 2. The deliverables (5 things, not just code)

| # | Deliverable | Notes |
|---|---|---|
| 1 | **Working app + UI** | Claim submission + decision review UI. Deployed URL. GitHub repo with clean commit history. |
| 2 | **Architecture doc** | Components, interactions, why this design, what you rejected, limits, how it scales 10x. *"As important as the code."* |
| 3 | **Component contracts** | Input/output/errors for every component — precise enough to reimplement without reading code. |
| 4 | **Eval report** | Run all 12 test cases, show decision + full trace + match/mismatch per case, explain mismatches. |
| 5 | **Demo video (8–12 min)** | (a) a doc-problem early stop with the error message, (b) a full approval with trace, (c) one decision you're proud of + one you'd change. |

---

## 3. Where the points are (allocate effort accordingly)

- **System Design 30%** — clean component separation, failure resilience, scaling story. *Bonus points explicitly for multi-agent architecture.*
- **Engineering Quality 25%** — error handling, data modeling, async, **tests** ("a system with no tests is incomplete").
- **Observability 20%** — the trace. Reconstruct any decision from it.
- **AI Integration 15%** — LLMs used *thoughtfully*: structured + validated output, failure handling. Implication: do NOT let the LLM do the math or apply policy rules.
- **Document Verification 10%** — early detection + specific, actionable error messages.

Notice: **75% of the grade is engineering/design/observability, only 15% is "AI."** The trap is over-investing in fancy prompting and under-investing in architecture, traces, and tests.

---

## 4. What the 12 test cases tell us (reverse-engineer the spec)

| Case | What it forces you to build |
|---|---|
| TC001 wrong doc type | Doc-type classification + requirements check per category (from policy JSON) → specific error |
| TC002 unreadable doc | Quality/readability assessment → re-upload request, not rejection |
| TC003 patient mismatch | Cross-document consistency check (names on each doc vs each other vs member) |
| TC004 clean approval | Full happy path; **10% co-pay on consultation** → 1500 → 1350, confidence > 0.85 |
| TC005 waiting period | Member join date + condition-specific waiting periods (diabetes 90d); must state the *eligibility date* |
| TC006 partial approval | **Line-item level adjudication**: root canal covered, teeth whitening excluded → approve 8000 of 12000, reason per line item |
| TC007 pre-auth missing | MRI > ₹10k needs pre-auth → reject with "how to resubmit" guidance |
| TC008 per-claim limit | ₹7,500 > ₹5,000 per-claim limit → reject, state both numbers |
| TC009 fraud signal | Claims-history analysis: 4th same-day claim (> limit of 2... actually 3 prior) → MANUAL_REVIEW, list the signals |
| TC010 network discount | **Order of operations: 20% network discount FIRST, then 10% co-pay** → 4500→3600→3240. Show breakdown. |
| TC011 component failure | `simulate_component_failure: true` flag → skip a component, still APPROVE, lower confidence, note "manual review recommended" |
| TC012 exclusion | Obesity treatment excluded → REJECTED, confidence > 0.90 |

**Key observation:** test cases provide document `content` as *structured JSON*, not actual image files. So the system needs two entry paths:
1. **Real path**: upload an image/PDF → vision LLM extracts structured content.
2. **Test/eval path**: pre-extracted content injected directly (the eval harness feeds `test_cases.json` through the same pipeline, bypassing OCR).

This is actually good design, not a hack — it means extraction and adjudication are decoupled, and you generate a few **mock document images** (the guide tells you how) to demo the real vision path live.

---

## 5. My recommended architecture (the "crack")

### Multi-agent pipeline with a deterministic core

```
Claim Submission (UI / API)
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ ORCHESTRATOR  (owns the trace, owns failure handling)   │
│                                                         │
│ 1. INTAKE VALIDATOR        — schema, member exists,     │
│    (pure code)               min amount, deadline       │
│                                                         │
│ 2. DOCUMENT VERIFIER agent — classify doc type,         │
│    (LLM, vision)             assess readability,        │
│                              check against requirements │
│                              ── EARLY EXIT HERE ──      │
│                                                         │
│ 3. EXTRACTION agent        — structured extraction      │
│    (LLM, vision)             per doc type, field-level  │
│                              confidence                 │
│                                                         │
│ 4. CONSISTENCY CHECKER     — patient names match,       │
│    (code + LLM for fuzzy)    dates align, amounts vs    │
│                              claimed ── EARLY EXIT ──   │
│                                                         │
│ 5. POLICY/ADJUDICATION     — DETERMINISTIC RULE ENGINE  │
│    (pure code, no LLM)       reads policy_terms.json:   │
│                              coverage, waiting periods, │
│                              exclusions, pre-auth,      │
│                              limits, discount→copay     │
│                              order, line-item verdicts  │
│                                                         │
│ 6. FRAUD/RISK CHECKER      — same-day count, monthly    │
│    (code)                    count, high-value, doc     │
│                              alteration flags           │
│                                                         │
│ 7. DECISION AGGREGATOR     — combines verdicts →        │
│    (code)                    decision + amount +        │
│                              confidence + reasons       │
└─────────────────────────────────────────────────────────┘
        │
        ▼
Decision + full structured TRACE  →  Review UI
```

### The judgment calls that win the interview

1. **LLMs only where language/vision is needed** (doc classification, extraction, fuzzy name matching). **All money math and policy rules are deterministic code.** You never want an LLM deciding ₹3,240 vs ₹3,239 — and you can unit-test the rule engine exhaustively. This directly answers "Are LLMs used thoughtfully?"

2. **Trace-first design.** Define the trace schema *first*: every pipeline step appends `{step, status: PASS/FAIL/SKIPPED/DEGRADED, input_summary, output, rule_applied, policy_reference, duration, confidence_impact}`. The decision is *derived from* the trace, not logged alongside it. That makes 20% of the grade fall out of the architecture for free.

3. **Confidence as an explicit model**, not a vibe: start at 1.0 (or compose from extraction field confidences), apply documented multipliers/deductions for degraded steps, unreadable fields, fuzzy matches. Show the confidence ledger in the trace. (TC011 requires "lower than normal" — make that mechanical.)

4. **Every step returns a Result, never throws upward.** Orchestrator decides per-step: required (early exit), or skippable (mark DEGRADED, lower confidence, continue). `simulate_component_failure` flag just forces one step to fail — graceful degradation falls out naturally.

5. **Structured LLM output, validated.** Use tool-calling / JSON schema mode + Pydantic validation + one retry on validation failure + fallback to DEGRADED. This is exactly what "structured and validated" in the rubric means.

### Stack recommendation

- **Backend: Python + FastAPI** (async, Pydantic data modeling, pytest — hits the rubric directly; Python is the AI-pod default).
- **Orchestration: hand-rolled** (a simple typed pipeline/state machine), *not* LangGraph/CrewAI. You'll be asked to extend it live in the 60-min review — you want to own every line. Frame it in the arch doc: "considered LangGraph, rejected because X."
- **LLM: Claude (or GPT-4o) with vision** for doc classification + extraction. One provider, thin client wrapper with timeout/retry, so failure simulation is easy.
- **Frontend: simple React (Vite) or server-rendered** — two screens: submit claim (with file upload + a "load test case" dropdown), and decision review (decision banner + collapsible step-by-step trace + confidence ledger + line-item table).
- **Deploy: Railway/Render** (single service serving API + static UI) — they require a deployed URL.
- **Storage: SQLite or in-memory + JSON files.** A real DB is not where the points are; say so in trade-offs.

### Mock documents

Generate ~6–8 realistic Indian medical doc images (prescription, hospital bill, pharmacy bill, lab report — plus one blurry, one with mismatched patient name) using HTML→screenshot or PIL, per the guide. These power the demo video's "real upload" moments.

---

## 6. Suggested build order (2–3 days)

| Phase | What | Why first |
|---|---|---|
| **1. Core domain (no LLM, no UI)** | Trace schema, Result types, policy rule engine reading `policy_terms.json`, decision aggregator, unit tests against TC004–TC012 expected numbers | This is 50%+ of the grade and fully testable offline |
| **2. Pipeline + degradation** | Orchestrator, early-exit doc checks (on structured input), consistency checker, fraud checker, failure simulation, eval runner producing the eval report from `test_cases.json` | Gets all 12 test cases green end-to-end |
| **3. LLM layer** | Vision classification + extraction with structured output, validation, retries, mock documents | Now the real-upload path works |
| **4. UI + deploy** | Submit + review screens, trace visualization, deploy | |
| **5. Docs + video** | Architecture doc, component contracts, eval report, record demo | Budget real time — docs are weighted heavily |

Clean commit history matters — commit per component with meaningful messages.

---

## 7. Traps to avoid

- ❌ Hardcoding any policy values (explicitly forbidden — everything from the JSON).
- ❌ LLM doing arithmetic or rule application → wrong amounts on TC004/TC010 and a weak interview answer.
- ❌ Generic error messages ("invalid documents") → fails TC001–TC003 and the 10% doc-verification criterion.
- ❌ Co-pay before discount on TC010 (they call this out explicitly: discount first → 3240, not 3195).
- ❌ Auto-rejecting the fraud case (TC009 must go to MANUAL_REVIEW) or the unreadable doc (TC002 must request re-upload).
- ❌ No tests, thin architecture doc, or skipping component contracts — each is an explicit deliverable.
- ❌ Framework-heavy agent orchestration you can't defend or extend live in the interview.

---

## 8. Open questions to brainstorm

1. **How "multi-agent" to go?** My pipeline above is multi-*component* with 2–3 LLM agents. We could make it more agentic (e.g., a supervisor agent routing, agents as parallel workers with a shared blackboard) for the bonus — worth discussing how far to push before it becomes indefensible theater.
2. **Stack confirmation** — FastAPI+React vs full Next.js vs Streamlit (fastest but looks less "engineered").
3. **LLM provider & budget** — Claude vs OpenAI, and do you have API credits?
4. **Deploy target** — Railway/Render/Fly/Vercel; any preference/accounts?
5. **Scope of the fraud checker** — rules-only (sufficient for TC009) vs adding an LLM "anomaly narrator" for flair.
6. **What's the "decision I'm proud of"** for the video — my vote: deterministic rule engine + trace-first design. And "what I'd change" — e.g., queue-based async processing for 10x scale, or human-in-the-loop review queue.
