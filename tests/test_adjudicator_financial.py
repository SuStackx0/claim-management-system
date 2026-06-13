# tests/test_adjudicator_financial.py
import pytest
from app.agents.adjudicator import AdjudicatorAgent
from app.agents.extraction import ExtractionAgent
from app.agents.intake import IntakeAgent
from app.llm.mock_client import MockClient

async def adjudicated(make_ctx, case):
    ctx = make_ctx(case)
    await IntakeAgent().run(ctx)
    await ExtractionAgent(llm=MockClient()).run(ctx)
    await AdjudicatorAgent().run(ctx)
    return ctx

async def test_tc004_copay_only(make_ctx, case_input):
    ctx = await adjudicated(make_ctx, case_input("TC004"))
    f = ctx.financial
    assert f["base"] == 1500
    assert f["network_discount"] == 0          # City Clinic not in network
    assert f["copay"] == 150                   # 10% of 1500
    assert f["payable"] == 1350

async def test_tc010_discount_before_copay(make_ctx, case_input):
    ctx = await adjudicated(make_ctx, case_input("TC010"))
    f = ctx.financial
    assert f["base"] == 4500
    assert f["network_discount"] == 900        # 20% of 4500 → 3600
    assert f["after_discount"] == 3600
    assert f["copay"] == 360                   # 10% of 3600
    assert f["payable"] == 3240

async def test_tc006_line_item_exclusion(make_ctx, case_input):
    ctx = await adjudicated(make_ctx, case_input("TC006"))
    by_desc = {v.description: v for v in ctx.line_verdicts}
    assert by_desc["Root Canal Treatment"].verdict == "APPROVED"
    rejected = by_desc["Teeth Whitening"]
    assert rejected.verdict == "REJECTED"
    assert "excluded" in rejected.reason.lower()
    assert rejected.rule_ref == "opd_categories.dental.excluded_procedures"
    assert ctx.financial["payable"] == 8000

async def test_consultation_subline_capped(make_ctx, case_input):
    # consultation fee line above sub_limit gets capped (documented assumption #1)
    import copy
    inp = copy.deepcopy(case_input("TC004"))
    inp["claimed_amount"] = 3000
    inp["documents"][1]["content"] = {**inp["documents"][1]["content"],
        "line_items": [{"description": "Consultation Fee", "amount": 2500},
                       {"description": "CBC Test", "amount": 500}], "total": 3000}
    ctx = await adjudicated(make_ctx, inp)
    capped = next(v for v in ctx.line_verdicts if v.description == "Consultation Fee")
    assert capped.verdict == "CAPPED" and capped.eligible_amount == 2000
    assert ctx.financial["base"] == 2500       # 2000 + 500
