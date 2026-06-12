# tests/test_adjudicator_checks.py
import pytest
from app.agents.adjudicator import AdjudicatorAgent
from app.agents.extraction import ExtractionAgent
from app.agents.intake import IntakeAgent
from app.core.trace import CheckResult
from app.llm.mock_client import MockClient

async def adjudicated(make_ctx, case):
    ctx = make_ctx(case)
    await IntakeAgent().run(ctx)
    await ExtractionAgent(llm=MockClient()).run(ctx)
    result = await AdjudicatorAgent().run(ctx)
    return ctx, result

async def test_tc005_waiting_period_with_eligible_date(make_ctx, case_input):
    ctx, result = await adjudicated(make_ctx, case_input("TC005"))
    assert "WAITING_PERIOD" in ctx.blocking_reasons
    wp = next(c for c in result.checks if c.check == "WAITING_PERIOD")
    assert wp.result == CheckResult.FAIL
    assert wp.rule_ref == "waiting_periods.specific_conditions.diabetes"
    assert wp.detail["eligible_from"] == "2024-11-30"   # 2024-09-01 + 90 days

async def test_tc007_pre_auth_missing(make_ctx, case_input):
    ctx, result = await adjudicated(make_ctx, case_input("TC007"))
    assert "PRE_AUTH_MISSING" in ctx.blocking_reasons
    pa = next(c for c in result.checks if c.check == "PRE_AUTHORIZATION")
    assert pa.detail["test"] == "MRI" and pa.detail["amount"] == 15000

async def test_tc008_per_claim_limit(make_ctx, case_input):
    ctx, result = await adjudicated(make_ctx, case_input("TC008"))
    assert "PER_CLAIM_EXCEEDED" in ctx.blocking_reasons
    pc = next(c for c in result.checks if c.check == "PER_CLAIM_LIMIT")
    assert pc.detail == {"claimed": 7500, "limit": 5000}
    assert pc.rule_ref == "coverage.per_claim_limit"

async def test_tc012_excluded_condition(make_ctx, case_input):
    ctx, result = await adjudicated(make_ctx, case_input("TC012"))
    assert "EXCLUDED_CONDITION" in ctx.blocking_reasons
    ex = next(c for c in result.checks if c.check == "EXCLUSIONS")
    assert "Obesity" in ex.detail["matched_exclusion"]

async def test_tc004_all_checks_pass(make_ctx, case_input):
    ctx, result = await adjudicated(make_ctx, case_input("TC004"))
    assert ctx.blocking_reasons == []
