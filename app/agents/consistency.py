from __future__ import annotations
import itertools
import time
from app.agents.base import Agent
from app.core.context import ClaimContext, ConsistencyFinding
from app.core.errors import AgentError, AgentFailure, ErrorCode
from app.core.trace import CheckResult, ConfidenceEntry, PolicyCheck, StepResult, StepStatus
from app.llm.base import LLMClient, LLMError
from app.llm.mock_client import name_tokens_match

class ConsistencyAgent(Agent):
    name = "ConsistencyAgent"
    step = "CONSISTENCY"
    fatal = True   # only PATIENT_MISMATCH raises; everything else is a warning

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def _names_match(self, a: str, b: str):
        try:
            m = await self.llm.names_equivalent(a, b)
            return m.equivalent, m.fuzzy
        except LLMError:
            return name_tokens_match(a, b)   # deterministic fallback

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        checks, entries = [], []

        # 1. patient names across documents must agree
        named = [(e, e.data.get("patient_name")) for e in ctx.extractions if e.data.get("patient_name")]
        for (ea, na), (eb, nb) in itertools.combinations(named, 2):
            eq, fuzzy = await self._names_match(na, nb)
            if not eq:
                ctx.findings.append(ConsistencyFinding(check="PATIENT_MATCH", severity="FATAL",
                    detail={"doc_a": ea.file_id, "name_a": na, "doc_b": eb.file_id, "name_b": nb}))
                raise AgentFailure(AgentError(
                    code=ErrorCode.PATIENT_MISMATCH,
                    message=f"patient mismatch: {na} vs {nb}",
                    member_message=(f"Your documents appear to belong to different people: "
                                    f"the {ea.doc_type.replace('_',' ').lower()} is for '{na}' but the "
                                    f"{eb.doc_type.replace('_',' ').lower()} is for '{nb}'. "
                                    f"All documents in one claim must be for the same patient. "
                                    f"Please re-upload matching documents."),
                    detail={"names_found": {ea.file_id: na, eb.file_id: nb}},
                ))
            if fuzzy:
                entries.append(ConfidenceEntry(factor=0.95, reason=f"fuzzy name match: '{na}' ≈ '{nb}'"))
        checks.append(PolicyCheck(check="PATIENT_MATCH", result=CheckResult.PASS,
                                  detail={"names": [n for _, n in named]}))

        # 2. names must belong to member or dependents (warning only — extraction noise)
        allowed = [ctx.member.name] + [d.name for d in ctx.loader.dependents_of(ctx.member.member_id)]
        for e, n in named:
            matches = []
            for a in allowed:
                m = await self._names_match(n, a)
                matches.append(m[0])
            if not any(matches):
                ctx.findings.append(ConsistencyFinding(check="MEMBER_MATCH", severity="WARNING",
                                                       detail={"name_on_doc": n, "allowed": allowed}))
                entries.append(ConfidenceEntry(factor=0.9, reason=f"'{n}' not matched to member/dependents"))

        # 3. bill total vs claimed amount (warning)
        totals = [e.data.get("total") for e in ctx.extractions
                  if e.doc_type in ("HOSPITAL_BILL", "PHARMACY_BILL") and e.data.get("total")]
        if totals:
            bill_sum = sum(totals)
            if bill_sum != ctx.submission.claimed_amount:
                ctx.findings.append(ConsistencyFinding(check="AMOUNT_MATCH", severity="WARNING",
                    detail={"bill_total": bill_sum, "claimed": ctx.submission.claimed_amount}))
                entries.append(ConfidenceEntry(factor=0.9,
                    reason=f"bill total ₹{bill_sum} != claimed ₹{ctx.submission.claimed_amount}"))
                checks.append(PolicyCheck(check="AMOUNT_MATCH", result=CheckResult.WARN,
                    detail={"bill_total": bill_sum, "claimed": ctx.submission.claimed_amount}))
            else:
                checks.append(PolicyCheck(check="AMOUNT_MATCH", result=CheckResult.PASS,
                    detail={"bill_total": bill_sum}))

        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          checks=checks, confidence_entries=entries,
                          duration_ms=int((time.monotonic() - t0) * 1000))
