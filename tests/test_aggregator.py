# tests/test_aggregator.py
from app.agents.aggregator import Aggregator
from app.core.context import FraudSignal, LineItemVerdict
from app.models.domain import DecisionStatus

async def test_fraud_routes_to_manual_review(make_ctx, case_input):
    ctx = make_ctx(case_input("TC009"))
    ctx.fraud_signals = [FraudSignal(signal="SAME_DAY_CLAIMS", detail={"count_today": 4, "limit": 2})]
    result = await Aggregator().run(ctx)
    d = ctx.trace.decision
    assert d.status == DecisionStatus.MANUAL_REVIEW
    assert "SAME_DAY_CLAIMS" in d.reasons[0] or any("SAME_DAY" in r for r in d.reasons)

async def test_blocking_reason_rejects(make_ctx, case_input):
    ctx = make_ctx(case_input("TC005"))
    ctx.blocking_reasons = ["WAITING_PERIOD"]
    await Aggregator().run(ctx)
    assert ctx.trace.decision.status == DecisionStatus.REJECTED
    assert "WAITING_PERIOD" in ctx.trace.decision.reasons

async def test_mixed_line_items_partial(make_ctx, case_input):
    ctx = make_ctx(case_input("TC006"))
    ctx.line_verdicts = [
        LineItemVerdict(description="Root Canal Treatment", amount=8000, eligible_amount=8000,
                        verdict="APPROVED", reason="covered"),
        LineItemVerdict(description="Teeth Whitening", amount=4000, eligible_amount=0,
                        verdict="REJECTED", reason="excluded"),
    ]
    ctx.financial = {"payable": 8000, "base": 8000, "network_discount": 0, "copay": 0}
    await Aggregator().run(ctx)
    d = ctx.trace.decision
    assert d.status == DecisionStatus.PARTIAL and d.approved_amount == 8000

async def test_all_approved(make_ctx, case_input):
    ctx = make_ctx(case_input("TC004"))
    ctx.line_verdicts = [LineItemVerdict(description="Consultation Fee", amount=1500,
                         eligible_amount=1500, verdict="APPROVED", reason="covered")]
    ctx.financial = {"payable": 1350, "base": 1500, "network_discount": 0, "copay": 150}
    await Aggregator().run(ctx)
    d = ctx.trace.decision
    assert d.status == DecisionStatus.APPROVED and d.approved_amount == 1350

async def test_low_confidence_adds_recommendation_not_status_change(make_ctx, case_input):
    from app.core.trace import StepResult, StepStatus, ConfidenceEntry
    ctx = make_ctx(case_input("TC011"))
    ctx.trace.append(StepResult(step="FRAUD", agent="FraudAgent", status=StepStatus.SKIPPED,
        confidence_entries=[ConfidenceEntry(factor=0.7, reason="FraudAgent failed; skipped")]))
    ctx.line_verdicts = [LineItemVerdict(description="Panchakarma", amount=4000,
                         eligible_amount=4000, verdict="APPROVED", reason="covered")]
    ctx.financial = {"payable": 4000, "base": 4000, "network_discount": 0, "copay": 0}
    await Aggregator().run(ctx)
    d = ctx.trace.decision
    assert d.status == DecisionStatus.APPROVED          # NOT flipped (TC011)
    assert d.confidence < 0.85
    assert "manual review" in d.ops_summary.lower()
