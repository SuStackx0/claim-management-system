from __future__ import annotations
import time
from datetime import timedelta
from app.agents.base import Agent
from app.core.context import ClaimContext, LineItemVerdict
from app.core.matching import match_condition, match_exclusion, text_matches_any
from app.core.trace import CheckResult, PolicyCheck, StepResult, StepStatus


class AdjudicatorAgent(Agent):
    name = "AdjudicatorAgent"
    step = "ADJUDICATION"
    fatal = True

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        checks: list[PolicyCheck] = []
        self._check_exclusions(ctx, checks)
        self._check_waiting_periods(ctx, checks)
        self._check_pre_auth(ctx, checks)
        self._check_annual_limit(ctx, checks)   # annual on gross — always runs
        if not ctx.blocking_reasons:
            self._adjudicate_line_items(ctx, checks)
            self._check_per_claim_limit(ctx, checks)  # per-claim on eligible — after line items
        if not ctx.blocking_reasons:
            self._compute_financials(ctx, checks)
        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          checks=checks, duration_ms=int((time.monotonic() - t0) * 1000))

    # ── diagnosis helpers ──────────────────────────────────────────────────────

    def _diagnosis_texts(self, ctx) -> list[str]:
        out = []
        for e in ctx.extractions:
            for f in ("diagnosis", "treatment"):
                if e.data.get(f):
                    out.append(e.data[f])
        return out

    # ── early-exit policy checks ───────────────────────────────────────────────

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

    def _check_annual_limit(self, ctx, checks):
        """Annual OPD limit check — always runs on gross claimed amount."""
        cov = ctx.loader.policy.coverage
        ytd = ctx.submission.ytd_claims_amount
        claimed = ctx.submission.claimed_amount
        if ytd + claimed > cov.annual_opd_limit:
            ctx.blocking_reasons.append("ANNUAL_LIMIT_EXCEEDED")
            checks.append(PolicyCheck(check="ANNUAL_OPD_LIMIT", result=CheckResult.FAIL,
                rule_ref="coverage.annual_opd_limit",
                detail={"ytd": ytd, "claimed": claimed, "limit": cov.annual_opd_limit}))
        else:
            checks.append(PolicyCheck(check="ANNUAL_OPD_LIMIT", result=CheckResult.PASS,
                rule_ref="coverage.annual_opd_limit",
                detail={"ytd": ytd, "claimed": claimed, "limit": cov.annual_opd_limit}))

    def _check_per_claim_limit(self, ctx, checks):
        """Per-claim limit check — runs AFTER line items, on eligible_base.
        Effective limit = max(coverage.per_claim_limit, category.sub_limit) so that
        dental/diagnostic categories with higher sub_limits aren't falsely blocked.
        TC008 (consultation): eligible 7500 > max(5000, 2000)=5000 → BLOCK.
        TC006 (dental):       eligible 8000 ≤ max(5000,10000)=10000 → pass → PARTIAL.
        """
        cov = ctx.loader.policy.coverage
        eligible_base = sum(v.eligible_amount for v in ctx.line_verdicts)
        sub_limit = ctx.policy_view.rules.sub_limit
        effective_limit = max(cov.per_claim_limit, sub_limit)
        if effective_limit == sub_limit and sub_limit > cov.per_claim_limit:
            rule_ref = f"opd_categories.{ctx.policy_view.opd_key}.sub_limit"
        else:
            rule_ref = "coverage.per_claim_limit"
        if eligible_base > effective_limit:
            ctx.blocking_reasons.append("PER_CLAIM_EXCEEDED")
            checks.append(PolicyCheck(check="PER_CLAIM_LIMIT", result=CheckResult.FAIL,
                rule_ref=rule_ref,
                detail={"claimed": eligible_base, "limit": effective_limit}))
        else:
            checks.append(PolicyCheck(check="PER_CLAIM_LIMIT", result=CheckResult.PASS,
                rule_ref=rule_ref,
                detail={"claimed": eligible_base, "limit": effective_limit}))

    # ── line-item adjudication ─────────────────────────────────────────────────

    def _bill_line_items(self, ctx) -> list[dict]:
        items = []
        for e in ctx.extractions:
            if e.doc_type in ("HOSPITAL_BILL", "PHARMACY_BILL"):
                items.extend(e.data.get("line_items") or [])
        if not items:
            for e in ctx.extractions:
                if e.doc_type in ("HOSPITAL_BILL", "PHARMACY_BILL") and e.data.get("total"):
                    items.append({"description": ctx.policy_view.category.title(),
                                  "amount": e.data["total"]})
        return items

    def _adjudicate_line_items(self, ctx, checks):
        rules = ctx.policy_view.rules
        cat = ctx.policy_view.opd_key
        excluded = rules.excluded_procedures + rules.excluded_items
        for item in self._bill_line_items(ctx):
            desc, amount = item["description"], item["amount"]
            # 1. category excluded_procedures list
            hit = text_matches_any(desc, excluded)
            if hit:
                ctx.line_verdicts.append(LineItemVerdict(
                    description=desc, amount=amount, eligible_amount=0, verdict="REJECTED",
                    reason=f"'{desc}' matches excluded procedure '{hit}' — not covered",
                    rule_ref=f"opd_categories.{cat}.excluded_procedures"))
                continue
            # 2. policy-level exclusion keywords
            excl = match_exclusion(desc)
            if excl and excl in ctx.loader.policy.exclusions.conditions:
                ctx.line_verdicts.append(LineItemVerdict(
                    description=desc, amount=amount, eligible_amount=0, verdict="REJECTED",
                    reason=f"'{desc}' falls under policy exclusion '{excl}'",
                    rule_ref="exclusions.conditions"))
                continue
            # 3. consultation fee sub_limit cap (assumption #1: caps the fee line, not the whole bill)
            eligible = amount
            verdict, reason = "APPROVED", "covered"
            if ("consultation" in desc.lower() and cat == "consultation"
                    and rules.sub_limit and amount > rules.sub_limit):
                eligible, verdict = rules.sub_limit, "CAPPED"
                reason = f"consultation fee capped at category sub-limit ₹{rules.sub_limit}"
            ctx.line_verdicts.append(LineItemVerdict(
                description=desc, amount=amount, eligible_amount=eligible,
                verdict=verdict, reason=reason,
                rule_ref=f"opd_categories.{cat}.sub_limit" if verdict == "CAPPED" else None))
        # Surface line-item rejections at the check level so the per-step trace is
        # not all-green on a claim that is partially or fully non-payable. A reviewer
        # scanning check statuses must see WHY the payable amount was reduced.
        any_rejected = any(v.verdict == "REJECTED" for v in ctx.line_verdicts)
        any_payable = any(v.verdict in ("APPROVED", "CAPPED") for v in ctx.line_verdicts)
        if not ctx.line_verdicts:
            line_result = CheckResult.FAIL          # nothing billable extracted
        elif any_rejected and not any_payable:
            line_result = CheckResult.FAIL          # every billed item rejected → ₹0
        elif any_rejected:
            line_result = CheckResult.WARN          # some items rejected → PARTIAL
        else:
            line_result = CheckResult.PASS
        checks.append(PolicyCheck(check="LINE_ITEMS", result=line_result,
            detail={"verdicts": [v.model_dump() for v in ctx.line_verdicts],
                    "no_billable_items": not ctx.line_verdicts}))

    # ── financial calculation ──────────────────────────────────────────────────

    def _compute_financials(self, ctx, checks):
        rules = ctx.policy_view.rules
        cat = ctx.policy_view.opd_key
        base = sum(v.eligible_amount for v in ctx.line_verdicts)
        # network check: submission hospital_name takes precedence; fallback to extraction
        hospital = ctx.submission.hospital_name or next(
            (e.data.get("hospital_name") for e in ctx.extractions if e.data.get("hospital_name")),
            None)
        in_network = bool(hospital) and any(
            h.lower() in hospital.lower() or hospital.lower() in h.lower()
            for h in ctx.loader.policy.network_hospitals)
        discount = round(base * rules.network_discount_percent / 100) if in_network else 0
        after_discount = base - discount
        copay = round(after_discount * rules.copay_percent / 100)
        payable = after_discount - copay
        ctx.financial = {
            "base": base,
            "in_network": in_network,
            "hospital": hospital,
            "network_discount_percent": rules.network_discount_percent if in_network else 0,
            "network_discount": discount,
            "after_discount": after_discount,
            "copay_percent": rules.copay_percent,
            "copay": copay,
            "payable": payable,
        }
        checks.append(PolicyCheck(check="FINANCIAL_CALCULATION", result=CheckResult.PASS,
            rule_ref=f"opd_categories.{cat}",
            detail=dict(ctx.financial, order="network discount applied before co-pay")))
