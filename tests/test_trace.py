from app.core.trace import ClaimTrace, StepResult, StepStatus, PolicyCheck, CheckResult, ConfidenceEntry
from app.core.errors import AgentError, AgentFailure, ErrorCode

def make_step(status=StepStatus.PASS, entries=None):
    return StepResult(step="X", agent="XAgent", status=status,
                      confidence_entries=entries or [])

def test_confidence_starts_at_one():
    t = ClaimTrace(claim_id="C1")
    assert t.confidence() == 1.0

def test_confidence_multiplies():
    t = ClaimTrace(claim_id="C1")
    t.append(make_step(entries=[ConfidenceEntry(factor=0.9, reason="partial readability")]))
    t.append(make_step(status=StepStatus.SKIPPED,
                       entries=[ConfidenceEntry(factor=0.7, reason="FraudAgent failed")]))
    assert abs(t.confidence() - 0.63) < 1e-9

def test_confidence_clamped():
    t = ClaimTrace(claim_id="C1")
    t.append(make_step(entries=[ConfidenceEntry(factor=1.5, reason="bad factor")]))
    assert t.confidence() == 1.0

def test_confidence_ledger_flattens():
    t = ClaimTrace(claim_id="C1")
    t.append(make_step(entries=[ConfidenceEntry(factor=0.9, reason="a")]))
    t.append(make_step(entries=[ConfidenceEntry(factor=0.8, reason="b")]))
    assert [e.reason for e in t.confidence_ledger()] == ["a", "b"]

def test_trace_serializes_with_rule_refs():
    t = ClaimTrace(claim_id="C1")
    t.append(StepResult(step="ADJUDICATION", agent="AdjudicatorAgent", status=StepStatus.PASS,
        checks=[PolicyCheck(check="WAITING_PERIOD", result=CheckResult.FAIL,
                            rule_ref="waiting_periods.specific_conditions.diabetes",
                            detail={"eligible_from": "2024-11-30"})]))
    d = t.model_dump()
    assert d["steps"][0]["checks"][0]["rule_ref"].endswith("diabetes")
    assert d["pipeline_version"] == "1.0.0"

def test_agent_error_carries_member_message():
    e = AgentError(code=ErrorCode.WRONG_DOCUMENT_TYPE, message="dev detail",
                   member_message="You uploaded X, we need Y")
    assert "uploaded" in e.member_message

def test_agent_failure_wraps_error():
    err = AgentError(code=ErrorCode.PATIENT_MISMATCH, message="names differ")
    try:
        raise AgentFailure(err)
    except AgentFailure as f:
        assert f.error.code == ErrorCode.PATIENT_MISMATCH

def test_claim_context_constructs():
    from app.core.context import ClaimContext
    from app.core.policy_loader import PolicyLoader
    from app.models.domain import ClaimSubmission
    from app.config import settings
    import json
    loader = PolicyLoader.load(settings.policy_path)
    with open(settings.test_cases_path) as f:
        case = json.load(f)["test_cases"][3]  # TC004
    ctx = ClaimContext(submission=ClaimSubmission.model_validate(case["input"]),
                       loader=loader, trace=ClaimTrace(claim_id="T"))
    assert ctx.member is None and ctx.blocking_reasons == [] and ctx.financial == {}
