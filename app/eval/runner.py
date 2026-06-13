from __future__ import annotations
import json
from pydantic import BaseModel, Field
from app.config import settings
from app.core.orchestrator import Orchestrator
from app.core.policy_loader import PolicyLoader
from app.llm.mock_client import MockClient
from app.models.domain import ClaimSubmission

class CaseResult(BaseModel):
    case_id: str
    case_name: str
    expected_decision: str | None
    produced_decision: str | None
    pipeline_status: str = "COMPLETED"
    approved_amount: int | None = None
    confidence: float | None = None
    passed: bool
    failures: list[str] = Field(default_factory=list)
    member_message: str = ""
    trace: dict = Field(default_factory=dict)

class EvalReport(BaseModel):
    cases: list[CaseResult]
    passed: int
    failed: int

class EvalRunner:
    def __init__(self, orchestrator: Orchestrator):
        self.orch = orchestrator

    @classmethod
    def default(cls) -> "EvalRunner":
        loader = PolicyLoader.load(settings.policy_path)
        return cls(Orchestrator(loader=loader, llm=MockClient()))

    async def run_all(self, cases_path: str) -> EvalReport:
        with open(cases_path) as f:
            cases = json.load(f)["test_cases"]
        results = [await self.run_case(c) for c in cases]
        report = EvalReport(cases=results,
                            passed=sum(c.passed for c in results),
                            failed=sum(not c.passed for c in results))
        return report

    async def run_case(self, case: dict) -> CaseResult:
        sub = ClaimSubmission.model_validate(case["input"])
        out = await self.orch.process(sub)
        exp = case["expected"]
        failures: list[str] = []

        expected_decision = exp.get("decision")
        produced = out.decision.status.value if out.decision else None
        if produced != expected_decision:
            failures.append(
                f"decision: expected {expected_decision}, got {produced} "
                f"(pipeline_status={out.status})"
            )

        if "approved_amount" in exp and out.decision \
           and out.decision.approved_amount != exp["approved_amount"]:
            failures.append(f"amount: expected {exp['approved_amount']}, "
                            f"got {out.decision.approved_amount}")

        for reason in exp.get("rejection_reasons", []):
            if out.decision and reason not in out.decision.reasons:
                failures.append(f"missing rejection reason {reason}")

        cs = exp.get("confidence_score", "")
        if cs.startswith("above") and out.decision:
            bound = float(cs.split()[-1])
            if out.decision.confidence <= bound:
                failures.append(f"confidence {out.decision.confidence} not above {bound}")

        failures += self._check_system_must(case, out)

        return CaseResult(case_id=case["case_id"], case_name=case["case_name"],
                          expected_decision=expected_decision, produced_decision=produced,
                          pipeline_status=out.status,
                          approved_amount=out.decision.approved_amount if out.decision else None,
                          confidence=out.decision.confidence if out.decision else None,
                          passed=not failures, failures=failures,
                          member_message=out.member_message, trace=out.trace)

    def _check_system_must(self, case: dict, out) -> list[str]:
        """Mechanically checkable subset of the prose 'system_must' expectations."""
        f: list[str] = []
        cid, msg = case["case_id"], out.member_message
        if cid == "TC001" and not ("PRESCRIPTION" in msg and "HOSPITAL_BILL" in msg):
            f.append("TC001: message must name uploaded and required doc types")
        if cid == "TC002" and "blurry_bill.jpg" not in msg:
            f.append("TC002: message must name the unreadable file")
        if cid == "TC003" and not ("Rajesh Kumar" in msg and "Arjun Mehta" in msg):
            f.append("TC003: message must include both patient names")
        if cid == "TC005" and "2024-11-30" not in msg:
            f.append("TC005: message must state the eligibility date")
        if cid == "TC010" and "3600" not in msg:
            f.append("TC010: breakdown must show discount applied before co-pay")
        if cid == "TC011" and out.decision \
           and "manual review" not in out.decision.ops_summary.lower():
            f.append("TC011: must recommend manual review")
        return f

    @staticmethod
    def render_markdown(report: EvalReport) -> str:
        lines = ["# Eval Report — 12 Test Cases", "",
                 f"**Result: {report.passed}/{report.passed + report.failed} passed**", "",
                 "> These cases run against the deterministic `MockClient` by design: "
                 "`test_cases.json` ships document *content* as structured fixtures (no image "
                 "files), so the eval validates the decision engine — policy checks, financial "
                 "math, consistency, fraud, and the full trace — independently of the stochastic "
                 "LLM perception layer. The real Gemini vision/extraction path is the same "
                 "Orchestrator with the `LLMClient` swapped, and is exercised separately via the "
                 "live API and the `@pytest.mark.live` tests.", ""]
        for c in report.cases:
            lines += [f"## {c.case_id} — {c.case_name}",
                      f"- Expected: `{c.expected_decision}` | Produced: `{c.produced_decision}`"
                      f" | **{'PASS' if c.passed else 'FAIL'}**"]
            if c.approved_amount is not None:
                lines.append(f"- Approved amount: ₹{c.approved_amount} | Confidence: {c.confidence}")
            if c.member_message:
                lines.append(f"- Member message: {c.member_message}")
            if c.failures:
                lines.append(f"- Mismatches: {'; '.join(c.failures)}")
            lines += ["", "<details><summary>Full trace</summary>", "", "```json",
                      json.dumps(c.trace, indent=2, default=str), "```",
                      "</details>", ""]
        return "\n".join(lines)
