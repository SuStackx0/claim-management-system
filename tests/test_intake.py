import pytest
from app.agents.intake import IntakeAgent
from app.core.errors import AgentFailure, ErrorCode
from app.core.trace import CheckResult, StepStatus


async def test_intake_resolves_member_and_view(make_ctx, case_input):
    ctx = make_ctx(case_input("TC004"))
    result = await IntakeAgent().run(ctx)
    assert result.status == StepStatus.PASS
    assert ctx.member.name == "Rajesh Kumar"
    assert ctx.policy_view.rules.copay_percent == 10
    assert any(c.check == "MEMBER_EXISTS" and c.rule_ref == "members" for c in result.checks)


async def test_intake_records_skipped_deadline_check(make_ctx, case_input):
    result = await IntakeAgent().run(make_ctx(case_input("TC004")))
    deadline = next(c for c in result.checks if c.check == "SUBMISSION_DEADLINE")
    assert deadline.result == CheckResult.SKIPPED
    assert "reason" in deadline.detail


async def test_intake_deadline_passes_when_within_window(make_ctx, case_input):
    # submission_date provided, within the 30-day deadline → PASS (treatment_date used)
    inp = dict(case_input("TC004"))
    inp["submission_date"] = "2024-11-20"  # treatment 2024-11-01 → 19 days, within 30
    result = await IntakeAgent().run(make_ctx(inp))
    deadline = next(c for c in result.checks if c.check == "SUBMISSION_DEADLINE")
    assert deadline.result == CheckResult.PASS
    assert deadline.detail["submission_date"] == "2024-11-20"


async def test_intake_deadline_exceeded_stops_with_dates(make_ctx, case_input):
    # submission_date past the 30-day window → fatal DEADLINE_EXCEEDED, message names dates
    inp = dict(case_input("TC004"))
    inp["submission_date"] = "2024-12-15"  # treatment 2024-11-01 → 44 days > 30
    with pytest.raises(AgentFailure) as ei:
        await IntakeAgent().run(make_ctx(inp))
    err = ei.value.error
    assert err.code == ErrorCode.DEADLINE_EXCEEDED
    assert "2024-11-01" in err.member_message  # treatment date
    assert "2024-12-01" in err.member_message  # eligible-until = treatment + 30d


async def test_intake_unknown_member(make_ctx, case_input):
    inp = dict(case_input("TC004")); inp["member_id"] = "EMP999"
    with pytest.raises(AgentFailure) as ei:
        await IntakeAgent().run(make_ctx(inp))
    assert ei.value.error.code == ErrorCode.MEMBER_NOT_FOUND
    assert "EMP999" in ei.value.error.member_message


async def test_intake_below_minimum(make_ctx, case_input):
    inp = dict(case_input("TC004")); inp["claimed_amount"] = 300
    with pytest.raises(AgentFailure) as ei:
        await IntakeAgent().run(make_ctx(inp))
    assert ei.value.error.code == ErrorCode.AMOUNT_BELOW_MINIMUM
    assert "500" in ei.value.error.member_message  # states the minimum


async def test_intake_invalid_category(make_ctx, case_input):
    inp = dict(case_input("TC004")); inp["claim_category"] = "SURGERY"
    with pytest.raises(AgentFailure) as ei:
        await IntakeAgent().run(make_ctx(inp))
    assert ei.value.error.code == ErrorCode.INVALID_CATEGORY
    assert "CONSULTATION" in ei.value.error.member_message  # lists valid categories


async def test_agent_base_is_abstract():
    from app.agents.base import Agent
    with pytest.raises(TypeError):
        Agent()
