# tests/test_doc_verifier.py
import pytest
from app.agents.doc_verifier import DocVerifierAgent
from app.core.errors import AgentFailure, ErrorCode
from app.core.trace import StepStatus
from app.llm.mock_client import MockClient

@pytest.fixture
def agent():
    return DocVerifierAgent(llm=MockClient())

async def test_tc001_wrong_doc_type_names_both_types(agent, make_ctx, case_input):
    ctx = make_ctx(case_input("TC001"))   # two prescriptions, consultation claim
    ctx.policy_view = ctx.loader.view("CONSULTATION")
    with pytest.raises(AgentFailure) as ei:
        await agent.run(ctx)
    err = ei.value.error
    assert err.code == ErrorCode.WRONG_DOCUMENT_TYPE
    assert "PRESCRIPTION" in err.member_message and "HOSPITAL_BILL" in err.member_message

async def test_tc002_unreadable_asks_specific_reupload(agent, make_ctx, case_input):
    ctx = make_ctx(case_input("TC002"))   # blurry pharmacy bill
    ctx.policy_view = ctx.loader.view("PHARMACY")
    with pytest.raises(AgentFailure) as ei:
        await agent.run(ctx)
    err = ei.value.error
    assert err.code == ErrorCode.DOCUMENT_UNREADABLE
    assert "blurry_bill.jpg" in err.member_message
    assert "re-upload" in err.member_message.lower()

async def test_clean_docs_pass(agent, make_ctx, case_input):
    ctx = make_ctx(case_input("TC004"))
    ctx.policy_view = ctx.loader.view("CONSULTATION")
    result = await agent.run(ctx)
    assert result.status == StepStatus.PASS
    assert {v.detected_type for v in ctx.doc_verdicts} == {"PRESCRIPTION", "HOSPITAL_BILL"}
