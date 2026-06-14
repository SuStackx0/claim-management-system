from __future__ import annotations
import asyncio
import logging
import time

from app.llm.base import DocClassification, ExtractionOutput, LLMError, LLMErrorKind, NameMatch

logger = logging.getLogger(__name__)

# Failures that signal the *provider* is unhealthy. SCHEMA_INVALID is the model
# emitting malformed JSON — a content problem, not an availability signal — so it
# never trips the breaker (and is non-retryable anyway, handled upstream).
_INFRA_FAILURES = frozenset(
    {LLMErrorKind.TIMEOUT, LLMErrorKind.RATE_LIMIT, LLMErrorKind.PROVIDER_ERROR}
)


class CircuitState:
    CLOSED = "CLOSED"        # normal operation
    OPEN = "OPEN"            # failing fast; provider presumed down
    HALF_OPEN = "HALF_OPEN"  # cooldown elapsed; allowing one probe


class CircuitBreakerLLM:
    """Wrap any ``LLMClient`` with an in-process circuit breaker.

    Why this exists
    ---------------
    A degraded-but-reachable provider (persistent 429 / 5xx / timeout) is far
    more dangerous than a cleanly-down one: every LLM call burns its *entire*
    retry+backoff budget — tens of seconds each — and a single claim makes many
    calls (classify + extract per document, plus name matches). Under load those
    slow calls pin FastAPI's request handlers open until the worker pool is
    exhausted, and one slow dependency cascades into a total API outage.

    The breaker converts that slow, cascading failure into a fast, contained one:
    after ``fail_max`` consecutive infrastructure failures it opens and every
    subsequent call raises immediately (in microseconds) for ``cooldown_s``, so
    the pipeline degrades cleanly instead of hanging.

    Self-healing
    ------------
    When the cooldown elapses the breaker moves to HALF_OPEN and lets a single
    probe through. Success closes the circuit and normal traffic resumes;
    failure re-opens it and the cooldown restarts. No human intervention, no
    restart — the provider coming back is detected automatically.

    Contract preservation
    ----------------------
    The fast-fail is raised as ``LLMError(PROVIDER_ERROR, retryable=False)`` —
    the same exception type every agent already handles — so the breaker changes
    failure *timing*, never failure *shape*. Downstream degrade/stop routing is
    untouched.

    Scope
    -----
    State is per-process (one breaker per worker). That is the correct unit here:
    each worker has its own connection pool to protect. A multi-replica
    deployment that wanted a *shared* view of provider health would back this
    with Redis — noted, deliberately out of scope for a single-instance service.
    """

    def __init__(self, inner, *, fail_max: int = 5, cooldown_s: float = 30.0,
                 name: str = "llm"):
        self._inner = inner
        self._fail_max = fail_max
        self._cooldown_s = cooldown_s
        self._name = name
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at = 0.0
        self._lock = asyncio.Lock()
        self._clock = time.monotonic  # injectable for tests

    # ── state machine ────────────────────────────────────────────────────────
    async def _before_call(self) -> None:
        """Raise immediately if the circuit is open and still cooling down."""
        if self._fail_max <= 0:        # breaker disabled
            return
        async with self._lock:
            if self._state != CircuitState.OPEN:
                return
            remaining = self._cooldown_s - (self._clock() - self._opened_at)
            if remaining > 0:
                raise LLMError(
                    LLMErrorKind.PROVIDER_ERROR,
                    f"circuit '{self._name}' open; failing fast "
                    f"({remaining:.0f}s until retry)",
                    retryable=False,
                )
            # cooldown elapsed → let exactly one probe attempt through
            self._state = CircuitState.HALF_OPEN
            logger.warning("circuit '%s' OPEN→HALF_OPEN: probing provider", self._name)

    async def _on_success(self) -> None:
        if self._fail_max <= 0:
            return
        async with self._lock:
            if self._state != CircuitState.CLOSED:
                logger.info("circuit '%s' %s→CLOSED: provider recovered",
                            self._name, self._state)
            self._state = CircuitState.CLOSED
            self._consecutive_failures = 0

    async def _on_failure(self, err: LLMError) -> None:
        if self._fail_max <= 0 or err.kind not in _INFRA_FAILURES:
            return  # disabled, or a content error that says nothing about health
        async with self._lock:
            self._consecutive_failures += 1
            if self._state == CircuitState.HALF_OPEN:
                self._open_locked("probe failed")
            elif self._consecutive_failures >= self._fail_max:
                self._open_locked(f"{self._consecutive_failures} consecutive failures")

    def _open_locked(self, reason: str) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
        logger.warning("circuit '%s' OPEN (%s): failing fast for %.0fs",
                       self._name, reason, self._cooldown_s)

    async def _guard(self, make_coro):
        """Run one provider call under the breaker.

        ``make_coro`` is a zero-arg factory, not a coroutine: we only create the
        coroutine *after* the open-circuit check passes, so a fast-fail never
        leaves an un-awaited coroutine behind.
        """
        await self._before_call()
        try:
            result = await make_coro()
        except LLMError as e:
            await self._on_failure(e)
            raise
        await self._on_success()
        return result

    # ── LLMClient protocol passthrough ───────────────────────────────────────
    async def classify_document(self, doc) -> DocClassification:
        return await self._guard(lambda: self._inner.classify_document(doc))

    async def extract(self, doc, schema) -> ExtractionOutput:
        return await self._guard(lambda: self._inner.extract(doc, schema))

    async def names_equivalent(self, a: str, b: str) -> NameMatch:
        return await self._guard(lambda: self._inner.names_equivalent(a, b))
