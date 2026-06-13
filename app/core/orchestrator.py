from __future__ import annotations
import asyncio, logging, time, uuid
from datetime import datetime, timezone
from app.agents.aggregator import Aggregator
from app.agents.adjudicator import AdjudicatorAgent
from app.agents.consistency import ConsistencyAgent
from app.agents.doc_verifier import DocVerifierAgent
from app.agents.extraction import ExtractionAgent
from app.agents.fraud import FraudAgent
from app.agents.intake import IntakeAgent
from app.config import settings
from app.core.context import ClaimContext
from app.core.errors import AgentError, AgentFailure, ErrorCode
from app.core.policy_loader import PolicyLoader
from app.core.trace import ClaimTrace, ConfidenceEntry, StepResult, StepStatus
from app.llm.base import LLMClient
from app.models.domain import ClaimOutcome, ClaimSubmission

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, loader: PolicyLoader, llm: LLMClient, repository=None):
        self.loader = loader
        self.repository = repository
        self.agents = [
            IntakeAgent(),
            DocVerifierAgent(llm=llm),
            ExtractionAgent(llm=llm),
            ConsistencyAgent(llm=llm),
            AdjudicatorAgent(),
            FraudAgent(),
            Aggregator(),
        ]

    async def process(self, submission: ClaimSubmission) -> ClaimOutcome:
        claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"
        ctx = ClaimContext(submission=submission, loader=self.loader,
                           trace=ClaimTrace(claim_id=claim_id,
                                            pipeline_version=settings.pipeline_version))
        for agent in self.agents:
            t0 = time.monotonic()
            try:
                result = await agent.run(ctx)
            except AgentFailure as f:
                result = StepResult(step=agent.step, agent=agent.name,
                                    status=StepStatus.FAIL, error=f.error,
                                    duration_ms=int((time.monotonic() - t0) * 1000))
                ctx.trace.append(result)
                if agent.fatal:
                    return await self._stopped(ctx, f.error)
                self._degrade(ctx, agent, f.error.message)
                continue
            except Exception as e:
                err = AgentError(code=ErrorCode.INTERNAL_ERROR, message=str(e))
                result = StepResult(step=agent.step, agent=agent.name,
                                    status=StepStatus.FAIL, error=err,
                                    duration_ms=int((time.monotonic() - t0) * 1000))
                ctx.trace.append(result)
                if agent.fatal and not isinstance(agent, FraudAgent):
                    return await self._stopped(ctx, err)
                self._degrade(ctx, agent, str(e))
                continue
            ctx.trace.append(result)
        ctx.trace.completed_at = datetime.now(timezone.utc)
        outcome = ClaimOutcome(claim_id=claim_id, status="COMPLETED",
                               decision=ctx.trace.decision,
                               member_message=ctx.trace.decision.member_message,
                               trace=ctx.trace.model_dump(mode="json"))
        await self._persist(ctx.submission, outcome)
        return outcome

    async def _persist(self, submission: ClaimSubmission, outcome: ClaimOutcome) -> None:
        # sqlite3 is synchronous; run it off the event loop so the pipeline's
        # async handlers are never blocked on disk I/O.
        # Persistence is a side effect: a write failure must never discard an
        # already-computed decision. Log it and return the outcome anyway.
        if not self.repository:
            return
        try:
            await asyncio.to_thread(self.repository.save, submission, outcome)
        except Exception as e:
            logger.warning("persistence failed for %s; returning decision anyway: %s",
                           outcome.claim_id, e)

    def _degrade(self, ctx: ClaimContext, agent, reason: str) -> None:
        ctx.trace.steps[-1].status = StepStatus.SKIPPED
        ctx.trace.steps[-1].confidence_entries.append(
            ConfidenceEntry(factor=0.7, reason=f"{agent.name} failed and was skipped: {reason}"))

    async def _stopped(self, ctx: ClaimContext, error: AgentError) -> ClaimOutcome:
        ctx.trace.completed_at = datetime.now(timezone.utc)
        outcome = ClaimOutcome(claim_id=ctx.trace.claim_id, status="STOPPED",
                               decision=None, member_message=error.member_message,
                               trace=ctx.trace.model_dump(mode="json"))
        await self._persist(ctx.submission, outcome)
        return outcome
