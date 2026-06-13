from __future__ import annotations
import time
from app.agents.base import Agent
from app.core.context import ClaimContext, FraudSignal
from app.core.trace import CheckResult, PolicyCheck, StepResult, StepStatus


class FraudAgent(Agent):
    name = "FraudAgent"
    step = "FRAUD_CHECK"
    fatal = False

    async def run(self, ctx: ClaimContext) -> StepResult:
        if ctx.submission.simulate_component_failure:
            raise RuntimeError("simulated component failure (test flag)")
        t0 = time.monotonic()
        checks: list[PolicyCheck] = []
        th = ctx.loader.policy.fraud_thresholds
        sub = ctx.submission

        # same-day claims check
        same_day = [h for h in sub.claims_history if h.date == sub.treatment_date]
        count_today = len(same_day) + 1     # +1 = this claim
        if count_today > th.same_day_claims_limit:
            ctx.fraud_signals.append(FraudSignal(
                signal="SAME_DAY_CLAIMS",
                rule_ref="fraud_thresholds.same_day_claims_limit",
                detail={"count_today": count_today, "limit": th.same_day_claims_limit,
                        "prior_claims": [h.model_dump(mode="json") for h in same_day]}))
        checks.append(PolicyCheck(
            check="SAME_DAY_CLAIMS",
            result=CheckResult.FAIL if count_today > th.same_day_claims_limit else CheckResult.PASS,
            rule_ref="fraud_thresholds.same_day_claims_limit",
            detail={"count_today": count_today, "limit": th.same_day_claims_limit}))

        # monthly claims check
        month = [h for h in sub.claims_history
                 if (h.date.year, h.date.month) == (sub.treatment_date.year, sub.treatment_date.month)]
        count_month = len(month) + 1
        if count_month > th.monthly_claims_limit:
            ctx.fraud_signals.append(FraudSignal(
                signal="MONTHLY_CLAIMS",
                rule_ref="fraud_thresholds.monthly_claims_limit",
                detail={"count_month": count_month, "limit": th.monthly_claims_limit}))
        checks.append(PolicyCheck(
            check="MONTHLY_CLAIMS",
            result=CheckResult.FAIL if count_month > th.monthly_claims_limit else CheckResult.PASS,
            rule_ref="fraud_thresholds.monthly_claims_limit",
            detail={"count_month": count_month, "limit": th.monthly_claims_limit}))

        # high-value claim check
        if sub.claimed_amount > th.auto_manual_review_above:
            ctx.fraud_signals.append(FraudSignal(
                signal="HIGH_VALUE_CLAIM",
                rule_ref="fraud_thresholds.auto_manual_review_above",
                detail={"claimed": sub.claimed_amount, "threshold": th.auto_manual_review_above}))
        checks.append(PolicyCheck(
            check="HIGH_VALUE",
            result=CheckResult.FAIL if sub.claimed_amount > th.auto_manual_review_above else CheckResult.PASS,
            rule_ref="fraud_thresholds.auto_manual_review_above",
            detail={"claimed": sub.claimed_amount, "threshold": th.auto_manual_review_above}))

        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          checks=checks, duration_ms=int((time.monotonic() - t0) * 1000))
