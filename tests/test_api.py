import pytest
from httpx import ASGITransport, AsyncClient
from app.api.main import create_app

@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
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
