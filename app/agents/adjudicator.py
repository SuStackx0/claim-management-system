from __future__ import annotations
import time
from datetime import timedelta
from app.agents.base import Agent
from app.core.context import ClaimContext
from app.core.matching import match_condition, match_exclusion, text_matches_any
from app.core.trace import CheckResult, PolicyCheck, StepResult, StepStatus

class AdjudicatorAgent(Agent):
    name = "AdjudicatorAgent"
    step = "ADJUDICATION"
    fatal = True   # raises only on internal error

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        checks: list[PolicyCheck] = []
        self._check_exclusions(ctx, checks)
        self._check_waiting_periods(ctx, checks)
        self._check_pre_auth(ctx, checks)
        self._check_limits(ctx, checks)
        if not ctx.blocking_reasons:
            self._adjudicate_line_items(ctx, checks)   # Task 11
            self._compute_financials(ctx, checks)      # Task 11
        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          checks=checks, duration_ms=int((time.monotonic() - t0) * 1000))

    # ---- helpers ----
    def _diagnosis_texts(self, ctx) -> list[str]:
        out = []
        for e in ctx.extractions:
            for f in ("diagnosis", "treatment"):
                if e.data.get(f):
                    out.append(e.data[f])
        return out

    def _check_exclusions(self, ctx, checks):
        texts = self._diagnosis_texts(ctx)
        matched = match_exclusion(*texts)
        if matched and matched in ctx.loader.policy.exclusions.conditions:
            ctx.blocking_reasons.append("EXCLUDED_CONDITION")
            checks.append(PolicyCheck(check="EXCLUSIONS", result=CheckResult.FAIL,
                rule_ref="exclusions.conditions",
                detail={"matched_exclusion": matched, "diagnosis_texts": texts}))
        else:
            checks.append(PolicyCheck(check="EXCLUSIONS", result=CheckResult.PASS,
                rule_ref="exclusions.conditions", detail={"diagnosis_texts": texts}))

    def _check_waiting_periods(self, ctx, checks):
        wp = ctx.loader.policy.waiting_periods
        join, treat = ctx.member.join_date, ctx.submission.treatment_date
        if join and (treat - join).days < wp.initial_waiting_period_days:
            eligible = join + timedelta(days=wp.initial_waiting_period_days)
            ctx.blocking_reasons.append("WAITING_PERIOD")
            checks.append(PolicyCheck(check="WAITING_PERIOD", result=CheckResult.FAIL,
                rule_ref="waiting_periods.initial_waiting_period_days",
                detail={"kind": "initial", "join_date": str(join),
                        "eligible_from": str(eligible), "treatment_date": str(treat)}))
            return
        cond = match_condition(*self._diagnosis_texts(ctx))
        if cond and cond in wp.specific_conditions and join:
            days = wp.specific_conditions[cond]
            eligible = join + timedelta(days=days)
            if treat < eligible:
                ctx.blocking_reasons.append("WAITING_PERIOD")
                checks.append(PolicyCheck(check="WAITING_PERIOD", result=CheckResult.FAIL,
                    rule_ref=f"waiting_periods.specific_conditions.{cond}",
                    detail={"condition_matched": cond, "waiting_days": days,
                            "member_join_date": str(join), "eligible_from": str(eligible),
                            "treatment_date": str(treat)}))
                return
        checks.append(PolicyCheck(check="WAITING_PERIOD", result=CheckResult.PASS,
            rule_ref="waiting_periods", detail={"condition_matched": cond}))

    def _check_pre_auth(self, ctx, checks):
        rules = ctx.policy_view.rules
        high_value = rules.high_value_tests_requiring_pre_auth
        threshold = rules.pre_auth_threshold
        if not high_value or threshold is None:
            checks.append(PolicyCheck(check="PRE_AUTHORIZATION", result=CheckResult.PASS,
                rule_ref=f"opd_categories.{ctx.policy_view.opd_key}",
                detail={"reason": "category has no pre-auth rules"}))
            return
        for e in ctx.extractions:
            items = e.data.get("line_items") or []
            names = [i["description"] for i in items] + \
                    (e.data.get("tests_ordered") or []) + \
                    ([e.data.get("test_name")] if e.data.get("test_name") else [])
            for item in items:
                test = text_matches_any(item["description"], high_value)
                if test and item["amount"] > threshold and not ctx.submission.pre_authorization_id:
                    ctx.blocking_reasons.append("PRE_AUTH_MISSING")
                    checks.append(PolicyCheck(check="PRE_AUTHORIZATION", result=CheckResult.FAIL,
                        rule_ref=f"opd_categories.{ctx.policy_view.opd_key}.high_value_tests_requiring_pre_auth",
                        detail={"test": test, "amount": item["amount"], "threshold": threshold,
                                "names_seen": names}))
                    return
        checks.append(PolicyCheck(check="PRE_AUTHORIZATION", result=CheckResult.PASS,
            rule_ref=f"opd_categories.{ctx.policy_view.opd_key}.pre_auth_threshold",
            detail={"threshold": threshold}))

    def _check_limits(self, ctx, checks):
        cov = ctx.loader.policy.coverage
        claimed = ctx.submission.claimed_amount
        if claimed > cov.per_claim_limit:
            ctx.blocking_reasons.append("PER_CLAIM_EXCEEDED")
            checks.append(PolicyCheck(check="PER_CLAIM_LIMIT", result=CheckResult.FAIL,
                rule_ref="coverage.per_claim_limit",
                detail={"claimed": claimed, "limit": cov.per_claim_limit}))
        else:
            checks.append(PolicyCheck(check="PER_CLAIM_LIMIT", result=CheckResult.PASS,
                rule_ref="coverage.per_claim_limit",
                detail={"claimed": claimed, "limit": cov.per_claim_limit}))
        ytd = ctx.submission.ytd_claims_amount
        if ytd + claimed > cov.annual_opd_limit:
            ctx.blocking_reasons.append("ANNUAL_LIMIT_EXCEEDED")
            checks.append(PolicyCheck(check="ANNUAL_OPD_LIMIT", result=CheckResult.FAIL,
                rule_ref="coverage.annual_opd_limit",
                detail={"ytd": ytd, "claimed": claimed, "limit": cov.annual_opd_limit}))
        else:
            checks.append(PolicyCheck(check="ANNUAL_OPD_LIMIT", result=CheckResult.PASS,
                rule_ref="coverage.annual_opd_limit",
                detail={"ytd": ytd, "claimed": claimed, "limit": cov.annual_opd_limit}))

    # implemented in Task 11
    def _adjudicate_line_items(self, ctx, checks): ...
    def _compute_financials(self, ctx, checks): ...
