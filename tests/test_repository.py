import pytest
from app.core.repository import Repository
from app.models.domain import ClaimOutcome, ClaimSubmission, Decision, DecisionStatus

@pytest.fixture
def repo(tmp_path):
    return Repository(str(tmp_path / "test.db"))

def make_outcome(claim_id="CLM-1"):
    return ClaimOutcome(claim_id=claim_id, status="COMPLETED",
        decision=Decision(status=DecisionStatus.APPROVED, approved_amount=1350, confidence=0.95),
        trace={"claim_id": claim_id, "steps": []})

def test_save_and_get(repo, case_input):
    sub = ClaimSubmission.model_validate(case_input("TC004"))
    repo.save(sub, make_outcome())
    row = repo.get("CLM-1")
    assert row["decision"]["approved_amount"] == 1350
    assert row["member_id"] == "EMP001"

def test_list_newest_first(repo, case_input):
    sub = ClaimSubmission.model_validate(case_input("TC004"))
    repo.save(sub, make_outcome("CLM-1"))
    repo.save(sub, make_outcome("CLM-2"))
    ids = [r["claim_id"] for r in repo.list_claims()]
    assert ids[0] == "CLM-2"

def test_get_missing_returns_none(repo):
    assert repo.get("NOPE") is None
