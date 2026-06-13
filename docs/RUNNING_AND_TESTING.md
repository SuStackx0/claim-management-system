# Running & Testing

## Start the app

```bash
conda activate task

# API (mock mode — no key needed, instant, deterministic)
python -m uvicorn app.api.main:app --port 8000

# API (real Gemini — reads/extracts from document images)
LLM_PROVIDER=gemini GEMINI_API_KEY=<key> python -m uvicorn app.api.main:app --port 8000

# UI (separate terminal) → http://localhost:8501
API_BASE_URL=http://127.0.0.1:8000 streamlit run ui/streamlit_app.py

# Or the full stack via Docker (API :8000, UI :8501)
docker compose up                          # mock mode
GEMINI_API_KEY=<key> docker compose up      # gemini mode
```

Health check: `curl http://127.0.0.1:8000/health` → `{"status":"ok","llm_provider":"mock|gemini",...}`
(In gemini mode the API takes ~10s to start while the SDK imports — normal.)

## Input

Submit a claim with documents (multipart): form field `payload` = the claim JSON, plus one or more `files`.

```bash
curl -s -X POST http://127.0.0.1:8000/claims/upload \
  -F 'payload={"member_id":"EMP001","policy_id":"PLUM_GHI_2024","claim_category":"consultation","treatment_date":"2024-11-01","claimed_amount":1500,"hospital_name":"City Clinic"}' \
  -F 'files=@sample_docs/prescription_clean.png;type=image/png' \
  -F 'files=@sample_docs/bill_clean.png;type=image/png'
```

`claim_category`: `consultation | diagnostic | pharmacy | dental | vision | alternative_medicine` (consultation needs a PRESCRIPTION + HOSPITAL_BILL).

Valid members: `EMP001`…`EMP010` (e.g. EMP001 = Rajesh Kumar); policy `PLUM_GHI_2024`.

JSON-only variant: `POST /claims` with the same body. Also: `GET /claims`, `GET /claims/{id}`.

## Output

```json
{
  "claim_id": "CLM-E177B661",
  "status": "COMPLETED",
  "decision": {
    "status": "APPROVED",          // APPROVED | PARTIAL | REJECTED | MANUAL_REVIEW
    "approved_amount": 1350,
    "confidence": 1.0,
    "reasons": ["All checks passed"]
  },
  "member_message": "Approved amount: ₹1350. A 10% co-pay (−₹150) was applied.",
  "trace": { "steps": [ /* per-agent step: status, checks[], rule_ref, duration_ms */ ] }
}
```

`status` is `COMPLETED` or `STOPPED` (early exit, e.g. wrong/missing document). `trace.steps` is the full audit trail — every agent, every policy check, and the rule it referenced.

## Tests

```bash
python -m pytest -q -k "not run_all"   # 152 passed (unit/integration, no LLM calls)
python -m app.eval                     # 12/12 assignment cases → docs/eval_report.md
```
