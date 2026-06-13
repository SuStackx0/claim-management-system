from __future__ import annotations
import itertools
import time
from app.agents.base import Agent
from app.core.context import ClaimContext, ConsistencyFinding
from app.core.errors import AgentError, AgentFailure, ErrorCode
from app.core.trace import CheckResult, ConfidenceEntry, PolicyCheck, StepResult, StepStatus
from app.llm.base import LLMClient, LLMError
from app.llm.mock_client import name_tokens_match
from app.models.extraction import SCHEMA_BY_DOCTYPE

# Doc types that are expected to carry a patient identity. If one of these
# degrades during extraction, a patient-identity comparison that "passes" would
# be vacuous — we must surface that, not silently pass.
_PATIENT_BEARING = {dt for dt, schema in SCHEMA_BY_DOCTYPE.items()
                    if "patient_name" in schema.model_fields}
_BILL_TYPES = ("HOSPITAL_BILL", "PHARMACY_BILL")


class ConsistencyAgent(Agent):
    name = "ConsistencyAgent"
    step = "CONSISTENCY"
    fatal = True   # only PATIENT_MISMATCH raises; everything else is a warning

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def _names_match(self, a: str, b: str):
        # Deterministic first: an exact or initial-style token match ('Rajesh
        # Kumar' / 'R. Kumar') needs no LLM. We only spend an LLM call when the
        # cheap matcher says "different" — the genuinely ambiguous cases the LLM
        # is good at (transliteration, word order, honorifics). This keeps the
        # AI in the loop where it adds value while collapsing the per-claim call
        # count from O(docs x roster) to ~0 for same-patient claims, so a Groq
        # rate-limit burst can't stall the pipeline on redundant name checks.
        eq, fuzzy = name_tokens_match(a, b)
        if eq:
            return eq, fuzzy
        try:
            m = await self.llm.names_equivalent(a, b)
            return m.equivalent, m.fuzzy
        except LLMError:
            return eq, fuzzy   # deterministic verdict stands if the LLM is unavailable

    def _flag_unverified(self, ctx, entries, check: str, reason: str, detail: dict) -> None:
        """Record a decision-relevant check we could NOT verify (because the data it
        needs is missing/degraded). This must never read as a clean PASS: it lands a
        SKIPPED check with an explicit reason, a confidence penalty, AND an entry in
        ctx.unverified_checks so the Aggregator caps the outcome at MANUAL_REVIEW
        rather than letting an unverifiable check prop up a confident approval."""
        ctx.unverified_checks.append(check)
        ctx.findings.append(ConsistencyFinding(check=check, severity="UNVERIFIED", detail=detail))
        entries.append(ConfidenceEntry(factor=0.6, reason=reason))

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        checks, entries = [], []

        # which patient-bearing / bill documents failed extraction and so can't
        # contribute the data a downstream consistency check depends on?
        degraded_patient_docs = [r for r in ctx.extractions
                                 if r.degraded and r.doc_type in _PATIENT_BEARING]
        degraded_bill_docs = [r for r in ctx.extractions
                              if r.degraded and r.doc_type in _BILL_TYPES]

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

        # A patient-identity check is only meaningful when we could actually compare
        # ≥2 names. If a patient-bearing document degraded and left us with <2 names,
        # the comparison did NOT verify identity — do not report a clean PASS.
        if degraded_patient_docs and len(named) < 2:
            missing = [r.file_id for r in degraded_patient_docs]
            self._flag_unverified(ctx, entries, "PATIENT_MATCH",
                reason=(f"patient identity could not be verified — extraction failed for "
                        f"document(s) {', '.join(missing)}, so cross-document name comparison "
                        f"was not possible"),
                detail={"degraded_docs": missing, "names_seen": [n for _, n in named]})
            checks.append(PolicyCheck(check="PATIENT_MATCH", result=CheckResult.SKIPPED,
                detail={"reason": "extraction degraded; identity unverifiable",
                        "degraded_docs": missing, "names_seen": [n for _, n in named]}))
        else:
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

        # 3. bill total vs claimed amount
        totals = [e.data.get("total") for e in ctx.extractions
                  if e.doc_type in _BILL_TYPES and e.data.get("total")]
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
        elif degraded_bill_docs:
            # A bill document degraded and we have no usable total: we cannot verify the
            # claimed amount against what was actually billed. Don't pass vacuously.
            missing = [r.file_id for r in degraded_bill_docs]
            self._flag_unverified(ctx, entries, "AMOUNT_MATCH",
                reason=(f"claimed amount ₹{ctx.submission.claimed_amount} could not be verified "
                        f"against the bill — extraction failed for document(s) {', '.join(missing)}"),
                detail={"degraded_docs": missing, "claimed": ctx.submission.claimed_amount})
            checks.append(PolicyCheck(check="AMOUNT_MATCH", result=CheckResult.SKIPPED,
                detail={"reason": "bill extraction degraded; claimed amount unverifiable",
                        "degraded_docs": missing, "claimed": ctx.submission.claimed_amount}))

        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          checks=checks, confidence_entries=entries,
                          duration_ms=int((time.monotonic() - t0) * 1000))
