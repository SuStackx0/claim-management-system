import pytest
from app.core.orchestrator import Orchestrator
from app.core.policy_loader import PolicyLoader
from app.llm.mock_client import MockClient
from app.models.domain import ClaimSubmission, DecisionStatus

@pytest.fixture
def orch(loader):
    return Orchestrator(loader=loader, llm=MockClient())

async def run_case(orch, case_input, case_id):
    sub = ClaimSubmission.model_validate(case_input(case_id))
    return await orch.process(sub)

async def test_tc001_stops_early(orch, case_input):
    out = await run_case(orch, case_input, "TC001")
    assert out.status == "STOPPED"
    assert out.decision is None
    assert "PRESCRIPTION" in out.member_message and "HOSPITAL_BILL" in out.member_message
    # adjudication never ran
    assert not any(s["step"] == "ADJUDICATION" for s in out.trace["steps"])

async def test_tc004_completes_approved(orch, case_input):
    out = await run_case(orch, case_input, "TC004")
    assert out.status == "COMPLETED"
    assert out.decision.status == DecisionStatus.APPROVED
    assert out.decision.approved_amount == 1350
    assert out.decision.confidence > 0.85

async def test_tc011_degrades_not_crashes(orch, case_input):
    out = await run_case(orch, case_input, "TC011")
    assert out.status == "COMPLETED"
    assert out.decision.status == DecisionStatus.APPROVED
    fraud_step = next(s for s in out.trace["steps"] if s["step"] == "FRAUD_CHECK")
    assert fraud_step["status"] == "SKIPPED"
    assert out.decision.confidence <= 0.7
    assert "manual review" in out.decision.ops_summary.lower()

async def test_internal_error_in_degradable_agent_never_propagates(orch, case_input):
    # TC011 exercises this via the simulate flag; assert no exception type leaks
    out = await run_case(orch, case_input, "TC011")
    assert out.trace["steps"][-1]["step"] == "AGGREGATION"


async def test_persistence_failure_does_not_drop_a_computed_decision(loader, case_input):
    """A repository write failure is a side-effect failure: the adjudicated
    decision must still be returned, not lost behind a 500."""
    class FailingRepo:
        def save(self, sub, outcome):
            raise RuntimeError("disk full")

    orch = Orchestrator(loader=loader, llm=MockClient(), repository=FailingRepo())
    out = await run_case(orch, case_input, "TC004")
    assert out.status == "COMPLETED"
    assert out.decision.status == DecisionStatus.APPROVED
    assert out.decision.approved_amount == 1350
