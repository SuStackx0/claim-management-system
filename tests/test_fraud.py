# tests/test_fraud.py
from app.agents.fraud import FraudAgent
from app.agents.intake import IntakeAgent

async def test_tc009_same_day_signal(make_ctx, case_input):
    ctx = make_ctx(case_input("TC009"))
    await IntakeAgent().run(ctx)
    await FraudAgent().run(ctx)
    sig = next(s for s in ctx.fraud_signals if s.signal == "SAME_DAY_CLAIMS")
    assert sig.detail["count_today"] == 4      # 3 prior + this one
    assert sig.detail["limit"] == 2
    assert sig.rule_ref == "fraud_thresholds.same_day_claims_limit"

async def test_simulated_failure_raises(make_ctx, case_input):
    import pytest
    ctx = make_ctx(case_input("TC011"))        # simulate_component_failure: true
    await IntakeAgent().run(ctx)
    with pytest.raises(RuntimeError):
        await FraudAgent().run(ctx)

async def test_clean_claim_no_signals(make_ctx, case_input):
    ctx = make_ctx(case_input("TC004"))
    await IntakeAgent().run(ctx)
    await FraudAgent().run(ctx)
    assert ctx.fraud_signals == []
