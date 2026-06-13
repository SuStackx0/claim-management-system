import copy
import json
import pytest
from app.config import settings
from app.core.orchestrator import Orchestrator
from app.eval.runner import CaseResult, EvalReport, EvalRunner
from app.llm.mock_client import MockClient


@pytest.fixture
def runner(loader):
    return EvalRunner(Orchestrator(loader=loader, llm=MockClient()))


# ---------------------------------------------------------------------------
# EvalRunner.run_case
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_case_tc004_passes(runner, test_cases):
    """TC004 is a straightforward APPROVED case — should pass."""
    case = copy.deepcopy(next(c for c in test_cases if c["case_id"] == "TC004"))
    result = await runner.run_case(case)
    assert result.passed
    assert result.produced_decision == "APPROVED"
    assert result.approved_amount == 1350


@pytest.mark.asyncio
async def test_run_case_wrong_decision_fails(runner, test_cases):
    """Artificially set expected.decision to wrong value — should produce a failure entry."""
    case = copy.deepcopy(next(c for c in test_cases if c["case_id"] == "TC004"))
    case["expected"]["decision"] = "REJECTED"  # intentionally wrong
    result = await runner.run_case(case)
    assert not result.passed
    assert any("decision:" in f for f in result.failures)
    # pipeline_status included in failure message
    assert any("pipeline_status=" in f for f in result.failures)


@pytest.mark.asyncio
async def test_run_case_wrong_amount_fails(runner, test_cases):
    """Wrong approved_amount expectation should produce a failure."""
    case = copy.deepcopy(next(c for c in test_cases if c["case_id"] == "TC004"))
    case["expected"]["approved_amount"] = 9999  # intentionally wrong
    result = await runner.run_case(case)
    assert not result.passed
    assert any("amount:" in f for f in result.failures)


@pytest.mark.asyncio
async def test_run_case_stopped_pipeline(runner, test_cases):
    """TC001 causes a STOPPED pipeline — decision is None, pipeline_status=STOPPED."""
    case = copy.deepcopy(next(c for c in test_cases if c["case_id"] == "TC001"))
    result = await runner.run_case(case)
    assert result.pipeline_status == "STOPPED"
    assert result.produced_decision is None


@pytest.mark.asyncio
async def test_run_all_returns_report(runner, tmp_path, test_cases):
    """run_all loads the real test_cases.json and returns an EvalReport."""
    report = await runner.run_all(settings.test_cases_path)
    assert isinstance(report, EvalReport)
    assert report.passed + report.failed == len(report.cases)
    assert len(report.cases) == 12


# ---------------------------------------------------------------------------
# _check_system_must
# ---------------------------------------------------------------------------

def _make_out(member_message="", ops_summary="", decision_msg=""):
    """Helper to build a minimal ClaimOutcome-like object using SimpleNamespace."""
    from types import SimpleNamespace
    decision = SimpleNamespace(ops_summary=ops_summary, member_message=decision_msg, reasons=[])
    return SimpleNamespace(member_message=member_message, decision=decision, status="COMPLETED")


def test_system_must_tc001_pass(runner):
    out = _make_out(member_message="Missing docs: PRESCRIPTION and HOSPITAL_BILL required")
    failures = runner._check_system_must({"case_id": "TC001"}, out)
    assert failures == []


def test_system_must_tc001_fail(runner):
    out = _make_out(member_message="Missing documents")
    failures = runner._check_system_must({"case_id": "TC001"}, out)
    assert len(failures) == 1
    assert "TC001" in failures[0]


def test_system_must_tc002_pass(runner):
    out = _make_out(member_message="Cannot read blurry_bill.jpg — please re-upload")
    failures = runner._check_system_must({"case_id": "TC002"}, out)
    assert failures == []


def test_system_must_tc002_fail(runner):
    out = _make_out(member_message="One of your documents is unreadable, please re-upload")
    failures = runner._check_system_must({"case_id": "TC002"}, out)
    assert len(failures) == 1
    assert "TC002" in failures[0]


def test_system_must_tc003_pass(runner):
    out = _make_out(member_message="Documents show two different people: Rajesh Kumar and Arjun Mehta")
    failures = runner._check_system_must({"case_id": "TC003"}, out)
    assert failures == []


def test_system_must_tc003_fail(runner):
    out = _make_out(member_message="Patient names on documents do not match")
    failures = runner._check_system_must({"case_id": "TC003"}, out)
    assert len(failures) == 1
    assert "TC003" in failures[0]


def test_system_must_tc005_pass(runner):
    out = _make_out(member_message="You will be eligible for diabetes-related claims from 2024-11-30")
    failures = runner._check_system_must({"case_id": "TC005"}, out)
    assert failures == []


def test_system_must_tc005_fail(runner):
    out = _make_out(member_message="Your claim is rejected due to waiting period")
    failures = runner._check_system_must({"case_id": "TC005"}, out)
    assert len(failures) == 1
    assert "TC005" in failures[0]


def test_system_must_tc010_pass(runner):
    out = _make_out(member_message="After discount: ₹3600 before co-pay")
    failures = runner._check_system_must({"case_id": "TC010"}, out)
    assert failures == []


def test_system_must_tc010_fail(runner):
    out = _make_out(member_message="Your claim was approved for ₹3240")
    failures = runner._check_system_must({"case_id": "TC010"}, out)
    assert len(failures) == 1


def test_system_must_tc011_pass(runner):
    out = _make_out(ops_summary="This claim requires manual review due to low confidence")
    failures = runner._check_system_must({"case_id": "TC011"}, out)
    assert failures == []


def test_system_must_tc011_fail(runner):
    out = _make_out(ops_summary="Claim approved with degraded confidence")
    failures = runner._check_system_must({"case_id": "TC011"}, out)
    assert len(failures) == 1


def test_system_must_unrelated_case_no_failures(runner):
    """A case_id with no system_must checks should always return empty failures."""
    out = _make_out(member_message="")
    failures = runner._check_system_must({"case_id": "TC004"}, out)
    assert failures == []


# ---------------------------------------------------------------------------
# render_markdown
# ---------------------------------------------------------------------------

def test_render_markdown_dynamic_total():
    """Total in header should reflect actual case count, not a hardcoded 12."""
    cases = [
        CaseResult(
            case_id="TC001",
            case_name="Test",
            expected_decision="APPROVED",
            produced_decision="APPROVED",
            passed=True,
        ),
        CaseResult(
            case_id="TC002",
            case_name="Test2",
            expected_decision="REJECTED",
            produced_decision="APPROVED",
            passed=False,
            failures=["decision: expected REJECTED, got APPROVED (pipeline_status=COMPLETED)"],
        ),
    ]
    report = EvalReport(cases=cases, passed=1, failed=1)
    md = EvalRunner.render_markdown(report)
    assert "1/2 passed" in md
    assert "TC001" in md
    assert "TC002" in md
    assert "PASS" in md
    assert "FAIL" in md


def test_render_markdown_all_pass():
    """All-pass report shows correct count and no FAIL marker."""
    cases = [
        CaseResult(
            case_id=f"TC00{i}",
            case_name=f"Case {i}",
            expected_decision="APPROVED",
            produced_decision="APPROVED",
            passed=True,
        )
        for i in range(1, 4)
    ]
    report = EvalReport(cases=cases, passed=3, failed=0)
    md = EvalRunner.render_markdown(report)
    assert "3/3 passed" in md
    assert "FAIL" not in md


def test_render_markdown_includes_failure_details():
    """Failure messages should appear in the rendered markdown."""
    cases = [
        CaseResult(
            case_id="TC007",
            case_name="Pre-auth missing",
            expected_decision="REJECTED",
            produced_decision="APPROVED",
            passed=False,
            failures=["decision: expected REJECTED, got APPROVED (pipeline_status=COMPLETED)"],
        ),
    ]
    report = EvalReport(cases=cases, passed=0, failed=1)
    md = EvalRunner.render_markdown(report)
    assert "TC007" in md
    assert "FAIL" in md
    assert "decision:" in md


def test_render_markdown_shows_approved_amount():
    """Approved amount and confidence appear in markdown when present."""
    cases = [
        CaseResult(
            case_id="TC004",
            case_name="Simple approval",
            expected_decision="APPROVED",
            produced_decision="APPROVED",
            passed=True,
            approved_amount=1350,
            confidence=0.92,
        ),
    ]
    report = EvalReport(cases=cases, passed=1, failed=0)
    md = EvalRunner.render_markdown(report)
    assert "1350" in md
    assert "0.92" in md
