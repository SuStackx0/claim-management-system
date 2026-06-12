# tests/test_consistency.py
import pytest
from app.agents.consistency import ConsistencyAgent
from app.agents.extraction import ExtractionAgent
from app.agents.intake import IntakeAgent
from app.core.errors import AgentFailure, ErrorCode
from app.core.trace import StepStatus
from app.llm.mock_client import MockClient

async def prepared_ctx(make_ctx, case):
    ctx = make_ctx(case)
    await IntakeAgent().run(ctx)
    await ExtractionAgent(llm=MockClient()).run(ctx)
    return ctx

async def test_tc003_patient_mismatch_names_both(make_ctx, case_input):
    ctx = await prepared_ctx(make_ctx, case_input("TC003"))
    with pytest.raises(AgentFailure) as ei:
        await ConsistencyAgent(llm=MockClient()).run(ctx)
    err = ei.value.error
    assert err.code == ErrorCode.PATIENT_MISMATCH
    assert "Rajesh Kumar" in err.member_message and "Arjun Mehta" in err.member_message

async def test_tc004_consistent_passes(make_ctx, case_input):
    ctx = await prepared_ctx(make_ctx, case_input("TC004"))
    result = await ConsistencyAgent(llm=MockClient()).run(ctx)
    assert result.status == StepStatus.PASS

async def test_amount_mismatch_warns_not_fatal(make_ctx, case_input):
    inp = dict(case_input("TC004")); inp["claimed_amount"] = 2000  # bill total is 1500
    ctx = await prepared_ctx(make_ctx, inp)
    result = await ConsistencyAgent(llm=MockClient()).run(ctx)
    assert result.status == StepStatus.PASS
    assert any(f.check == "AMOUNT_MATCH" and f.severity == "WARNING" for f in ctx.findings)
    assert any(e.factor < 1.0 for e in result.confidence_entries)
