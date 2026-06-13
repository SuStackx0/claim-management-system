import pytest
from httpx import ASGITransport, AsyncClient
from app.api.main import create_app

@pytest.fixture
async def client(tmp_path, monkeypatch):
    # settings is a module-level singleton read at import time, so setenv alone is
    # too late — patch the live attribute so a developer's local .env (e.g.
    # LLM_PROVIDER=groq) can't leak the real client into these tests.
    from app.config import settings
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(settings, "llm_provider", "mock")
    app = create_app(db_path=str(tmp_path / "api.db"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c

async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"

async def test_submit_json_claim_tc004(client, case_input):
    r = await client.post("/claims", json=case_input("TC004"))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "COMPLETED"
    assert body["decision"]["approved_amount"] == 1350

async def test_doc_problem_is_200_stopped(client, case_input):
    r = await client.post("/claims", json=case_input("TC001"))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "STOPPED" and body["decision"] is None
    assert "HOSPITAL_BILL" in body["member_message"]

async def test_get_claim_returns_trace(client, case_input):
    claim_id = (await client.post("/claims", json=case_input("TC004"))).json()["claim_id"]
    r = await client.get(f"/claims/{claim_id}")
    assert r.status_code == 200
    assert any(s["step"] == "ADJUDICATION" for s in r.json()["trace"]["steps"])

async def test_get_unknown_claim_404(client):
    assert (await client.get("/claims/NOPE")).status_code == 404

async def test_list_members(client):
    r = await client.get("/members")
    assert any(m["member_id"] == "EMP001" for m in r.json())


# ---------------------------------------------------------------------------
# Multipart upload path  (POST /claims/upload)
# ---------------------------------------------------------------------------
# The mock LLM client classifies documents by filename keywords:
#   "bill"  / "invoice" / "receipt"  => HOSPITAL_BILL
#   "prescription" / "rx"            => PRESCRIPTION
# The mock extraction fixture is keyed by exact filename.  "sample_bill.jpg"
# returns City Clinic data (total=1500, patient=Rajesh Kumar) and
# "sample_prescription.jpg" returns the matching Viral Fever prescription.
# The consultation policy requires both HOSPITAL_BILL and PRESCRIPTION.
# ---------------------------------------------------------------------------

_UPLOAD_PAYLOAD = {
    "member_id": "EMP001",
    "policy_id": "PLUM_GHI_2024",
    "claim_category": "CONSULTATION",
    "treatment_date": "2024-11-01",
    "claimed_amount": 1500,
    "ytd_claims_amount": 5000,
}


async def test_upload_single_file_stops_on_missing_doc(client):
    """One bill file only — prescription missing — pipeline stops with a
    doc-problem message listing both required types."""
    import json as _json

    r = await client.post(
        "/claims/upload",
        data={"payload": _json.dumps(_UPLOAD_PAYLOAD)},
        files=[("files", ("sample_bill.jpg", b"fake-bytes", "image/jpeg"))],
    )
    assert r.status_code == 200
    body = r.json()
    # Response shape: claim_id present, status STOPPED, no decision
    assert "claim_id" in body
    assert body["status"] == "STOPPED"
    assert body["decision"] is None
    # Member message names the missing document type
    assert "PRESCRIPTION" in body["member_message"]
    # Trace dict is always present (may be empty on early stop but key exists)
    assert "trace" in body


async def test_upload_two_files_completes_and_approves(client):
    """Bill + prescription files → pipeline completes with APPROVED outcome and
    a 10% co-pay deduction (1500 - 150 = 1350), mirroring TC004 on the JSON path."""
    import json as _json

    r = await client.post(
        "/claims/upload",
        data={"payload": _json.dumps(_UPLOAD_PAYLOAD)},
        files=[
            ("files", ("sample_bill.jpg", b"fake-bytes", "image/jpeg")),
            ("files", ("sample_prescription.jpg", b"fake-bytes", "image/jpeg")),
        ],
    )
    assert r.status_code == 200
    body = r.json()
    assert "claim_id" in body
    assert body["status"] == "COMPLETED"
    decision = body["decision"]
    assert decision is not None
    assert decision["status"] == "APPROVED"
    assert decision["approved_amount"] == 1350
    # Trace must be present and contain the ADJUDICATION step
    assert any(s["step"] == "ADJUDICATION" for s in body["trace"]["steps"])


# ---------------------------------------------------------------------------
# Resilience: the API edge must not 500 on bad input or unexpected errors
# ---------------------------------------------------------------------------

async def test_upload_malformed_payload_is_422_not_500(client):
    """A non-JSON payload string is a client error, not a server crash."""
    r = await client.post(
        "/claims/upload",
        data={"payload": "{not valid json"},
        files=[("files", ("sample_bill.jpg", b"fake-bytes", "image/jpeg"))],
    )
    assert r.status_code == 422


async def test_upload_invalid_schema_is_422_not_500(client):
    """Valid JSON but missing required claim fields is a client error."""
    import json as _json

    r = await client.post(
        "/claims/upload",
        data={"payload": _json.dumps({"member_id": "EMP001"})},
        files=[("files", ("sample_bill.jpg", b"fake-bytes", "image/jpeg"))],
    )
    assert r.status_code == 422


async def test_unexpected_error_returns_structured_500(case_input, monkeypatch, tmp_path):
    """An unhandled internal error returns a structured JSON 500, never a
    bare crash — the API stays explainable even on the unhappy path.

    The default ASGITransport re-raises server exceptions for test visibility;
    a real HTTP client over uvicorn receives the response the handler emits, so
    we set raise_app_exceptions=False to observe that wire behavior here.
    """
    from app.core.orchestrator import Orchestrator

    monkeypatch.setenv("LLM_PROVIDER", "mock")

    async def boom(self, submission):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(Orchestrator, "process", boom)

    app = create_app(db_path=str(tmp_path / "api.db"))
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.post("/claims", json=case_input("TC004"))
    assert r.status_code == 500
    assert r.json()["error"] == "internal_error"
