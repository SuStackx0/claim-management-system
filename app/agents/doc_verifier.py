from __future__ import annotations
import time
from app.agents.base import Agent
from app.core.context import ClaimContext, DocVerdict
from app.core.errors import AgentError, AgentFailure, ErrorCode
from app.core.trace import CheckResult, ConfidenceEntry, PolicyCheck, StepResult, StepStatus
from app.llm.base import LLMClient, LLMError

class DocVerifierAgent(Agent):
    name = "DocVerifierAgent"
    step = "DOC_VERIFICATION"
    fatal = True

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        checks: list[PolicyCheck] = []
        entries: list[ConfidenceEntry] = []
        rule_ref = f"document_requirements.{ctx.policy_view.category}"

        for doc in ctx.submission.documents:
            if doc.actual_type is not None:            # test-path hint
                verdict = DocVerdict(file_id=doc.file_id, file_name=doc.file_name,
                                     detected_type=str(doc.actual_type),
                                     readability=str(doc.quality or "GOOD"))
            else:                                       # real path: vision classify
                try:
                    c = await self.llm.classify_document(doc)
                except LLMError as e:
                    raise AgentFailure(AgentError(
                        code=ErrorCode.DOCUMENT_UNREADABLE,
                        message=f"classification failed for {doc.file_id}: {e}",
                        member_message=(f"We couldn't process '{doc.file_name or doc.file_id}'. "
                                        f"Please re-upload a clearer photo or PDF of this document."),
                    ))
                verdict = DocVerdict(file_id=doc.file_id, file_name=doc.file_name,
                                     detected_type=c.detected_type,
                                     readability=c.readability, confidence=c.confidence)
            ctx.doc_verdicts.append(verdict)
            checks.append(PolicyCheck(check="DOC_CLASSIFIED", result=CheckResult.PASS,
                                      detail=verdict.model_dump()))
            if verdict.readability == "PARTIAL":
                entries.append(ConfidenceEntry(factor=0.9,
                               reason=f"{verdict.file_name or verdict.file_id} partially readable"))

        # unreadable required docs → re-upload request (not rejection)
        required = set(ctx.policy_view.required_docs)
        for v in ctx.doc_verdicts:
            if v.readability == "UNREADABLE" and v.detected_type in required:
                raise AgentFailure(AgentError(
                    code=ErrorCode.DOCUMENT_UNREADABLE,
                    message=f"{v.file_id} unreadable",
                    member_message=(f"Your {v.detected_type.replace('_', ' ').title()} "
                                    f"('{v.file_name or v.file_id}') is too blurry to read. "
                                    f"Please re-upload a clear photo of this document. "
                                    f"Your claim is on hold — it has not been rejected."),
                    detail={"file_id": v.file_id, "readability": "UNREADABLE"},
                ))

        detected = {v.detected_type for v in ctx.doc_verdicts}
        missing = sorted(required - detected)
        extra = sorted(t for t in (v.detected_type for v in ctx.doc_verdicts)
                       if t not in required and t not in set(ctx.policy_view.optional_docs))

        if missing:
            uploaded_desc = ", ".join(f"{v.detected_type} ('{v.file_name or v.file_id}')"
                                      for v in ctx.doc_verdicts)
            code = ErrorCode.WRONG_DOCUMENT_TYPE if (extra or len(ctx.doc_verdicts) >= len(required)) \
                   else ErrorCode.MISSING_REQUIRED_DOCUMENT
            raise AgentFailure(AgentError(
                code=code,
                message=f"missing required docs: {missing}",
                member_message=(f"For a {ctx.policy_view.category} claim you must upload: "
                                f"{', '.join(sorted(required))}. You uploaded: {uploaded_desc}. "
                                f"Missing: {', '.join(missing)}. "
                                f"Please upload your {missing[0].replace('_', ' ').lower()} to proceed."),
                detail={"required": sorted(required), "detected": sorted(detected),
                        "missing": missing},
            ))

        checks.append(PolicyCheck(check="REQUIREMENTS_MET", result=CheckResult.PASS,
                                  rule_ref=rule_ref,
                                  detail={"required": sorted(required), "detected": sorted(detected)}))
        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          checks=checks, confidence_entries=entries,
                          duration_ms=int((time.monotonic() - t0) * 1000))
