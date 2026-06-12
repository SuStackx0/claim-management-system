from __future__ import annotations
import asyncio, time
from app.agents.base import Agent
from app.core.context import ClaimContext, ExtractionRecord
from app.core.trace import CheckResult, ConfidenceEntry, PolicyCheck, StepResult, StepStatus
from app.llm.base import LLMClient, LLMError
from app.models.domain import DocumentInput
from app.models.extraction import SCHEMA_BY_DOCTYPE

class ExtractionAgent(Agent):
    name = "ExtractionAgent"
    step = "EXTRACTION"
    fatal = False

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        verdict_by_id = {v.file_id: v for v in ctx.doc_verdicts}
        records = await asyncio.gather(
            *(self._extract_one(doc, verdict_by_id.get(doc.file_id)) for doc in ctx.submission.documents)
        )
        ctx.extractions = list(records)

        checks, entries = [], []
        degraded = [r for r in records if r.degraded]
        for r in records:
            checks.append(PolicyCheck(
                check="FIELDS_EXTRACTED",
                result=CheckResult.FAIL if r.degraded else CheckResult.PASS,
                detail={"file_id": r.file_id, "doc_type": r.doc_type, "source": r.source,
                        "unextracted_fields": r.unextracted_fields}))
        for r in degraded:
            entries.append(ConfidenceEntry(factor=0.7,
                           reason=f"extraction failed for {r.file_id}; proceeding without it"))

        status = StepStatus.DEGRADED if degraded else StepStatus.PASS
        return StepResult(step=self.step, agent=self.name, status=status, checks=checks,
                          confidence_entries=entries,
                          duration_ms=int((time.monotonic() - t0) * 1000))

    async def _extract_one(self, doc: DocumentInput, verdict) -> ExtractionRecord:
        doc_type = verdict.detected_type if verdict else (str(doc.actual_type) if doc.actual_type else "UNKNOWN")
        if doc.content is not None or doc.patient_name_on_doc:   # test path: provided content/hints
            data = dict(doc.content or {})
            if doc.patient_name_on_doc and "patient_name" not in data:
                data["patient_name"] = doc.patient_name_on_doc
            return ExtractionRecord(file_id=doc.file_id, doc_type=doc_type, data=data,
                                    field_confidence={k: 1.0 for k in data}, source="provided")
        schema = SCHEMA_BY_DOCTYPE.get(doc_type)
        if schema is None:
            return ExtractionRecord(file_id=doc.file_id, doc_type=doc_type, degraded=True,
                                    unextracted_fields=["*"], source="vision")
        try:
            out = await self.llm.extract(doc, schema)
            return ExtractionRecord(file_id=doc.file_id, doc_type=doc_type,
                                    data=out.data.model_dump(),
                                    field_confidence=out.field_confidence,
                                    unextracted_fields=out.unextracted_fields, source="vision")
        except LLMError:
            return ExtractionRecord(file_id=doc.file_id, doc_type=doc_type, degraded=True,
                                    unextracted_fields=["*"], source="vision")
