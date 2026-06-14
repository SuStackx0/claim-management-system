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
        # Log submission
        logger.info(
            "[%s] INTAKE member=%s category=%s claimed_amount=%d",
            claim_id,
            submission.member_id,
            submission.claim_category,
            submission.claimed_amount,
        )
        t_start = time.monotonic()
        for agent in self.agents:
            t0 = time.monotonic()
            try:
                result = await self._run_agent(agent, ctx)
            except AgentFailure as f:
                result = StepResult(step=agent.step, agent=agent.name,
                                    status=StepStatus.FAIL, error=f.error,
                                    duration_ms=int((time.monotonic() - t0) * 1000))
                ctx.trace.append(result)
                if agent.fatal:
                    return await self._stopped(ctx, f.error)
                self._degrade(ctx, agent, f.error.message)
                continue
            except asyncio.TimeoutError:
                # The agent blew its wall-clock budget (a hung provider that never
                # responds). Treat it as a step failure and route it like any
                # other: stop a fatal step, degrade a non-fatal one — but never
                # hold the request open waiting on a dependency that won't return.
                err = AgentError(
                    code=ErrorCode.PROCESSING_TIMEOUT,
                    message=f"{agent.name} exceeded {settings.agent_timeout_s:.0f}s deadline",
                    member_message=(
                        "Your claim is taking longer than expected due to a temporary "
                        "system slowdown. No action is needed — we'll keep processing it "
                        "and update you shortly."),
                )
                logger.warning("[%s] %s TIMEOUT after %dms (deadline %.0fs)",
                               claim_id, agent.step,
                               int((time.monotonic() - t0) * 1000), settings.agent_timeout_s)
                result = StepResult(step=agent.step, agent=agent.name,
                                    status=StepStatus.FAIL, error=err,
                                    duration_ms=int((time.monotonic() - t0) * 1000))
                ctx.trace.append(result)
                if agent.fatal and not isinstance(agent, FraudAgent):
                    return await self._stopped(ctx, err)
                self._degrade(ctx, agent, err.message)
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
            # Log step execution with duration
            logger.info("[%s] %s (%dms)", claim_id, agent.step, result.duration_ms)
            ctx.trace.append(result)
        ctx.trace.completed_at = datetime.now(timezone.utc)
        outcome = ClaimOutcome(claim_id=claim_id, status="COMPLETED",
                               decision=ctx.trace.decision,
                               member_message=ctx.trace.decision.member_message,
                               trace=ctx.trace.model_dump(mode="json"))
        await self._persist(ctx.submission, outcome)
        # Log completion
        total_ms = int((time.monotonic() - t_start) * 1000)
        logger.info(
            "[%s] COMPLETED status=%s approved_amount=%d confidence=%.2f total=%dms",
            claim_id,
            ctx.trace.decision.status if ctx.trace.decision else "N/A",
            ctx.trace.decision.approved_amount if ctx.trace.decision else 0,
            ctx.trace.confidence(),
            total_ms,
        )
        return outcome

    async def _run_agent(self, agent, ctx: ClaimContext) -> StepResult:
        """Run one agent under an optional wall-clock deadline.

        With agent_timeout_s <= 0 the deadline is disabled (and on the mock path,
        where every call is instant, it never fires anyway). asyncio.wait_for
        cancels the underlying coroutine on expiry and raises TimeoutError, which
        the caller routes through the normal stop/degrade path.
        """
        timeout = settings.agent_timeout_s
        if timeout and timeout > 0:
            return await asyncio.wait_for(agent.run(ctx), timeout=timeout)
        return await agent.run(ctx)

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
