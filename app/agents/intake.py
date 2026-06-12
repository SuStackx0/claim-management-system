from __future__ import annotations
import time
from app.agents.base import Agent
from app.core.context import ClaimContext
from app.core.errors import AgentError, AgentFailure, ErrorCode
from app.core.trace import CheckResult, PolicyCheck, StepResult, StepStatus

class IntakeAgent(Agent):
    name = "IntakeAgent"
    step = "INTAKE"
    fatal = True

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        sub, loader = ctx.submission, ctx.loader
        checks: list[PolicyCheck] = []

        if sub.policy_id != loader.policy.policy_id:
            raise AgentFailure(AgentError(
                code=ErrorCode.POLICY_INACTIVE,
                message=f"submission policy {sub.policy_id} != loaded {loader.policy.policy_id}",
                member_message=(f"Policy {sub.policy_id} doesn't match your active policy "
                                f"{loader.policy.policy_id}. Please submit under your "
                                f"current policy."),
            ))
        checks.append(PolicyCheck(check="POLICY_MATCHES", result=CheckResult.PASS,
                                  rule_ref="policy_id",
                                  detail={"policy_id": sub.policy_id}))

        member = loader.member(sub.member_id)
        if member is None:
            raise AgentFailure(AgentError(
                code=ErrorCode.MEMBER_NOT_FOUND,
                message=f"member {sub.member_id} not in roster",
                member_message=(f"We couldn't find member ID {sub.member_id} on policy "
                                f"{sub.policy_id}. Please check your member ID and try again."),
            ))
        ctx.member = member
        checks.append(PolicyCheck(check="MEMBER_EXISTS", result=CheckResult.PASS,
                                  rule_ref="members", detail={"member_id": member.member_id}))

        try:
            ctx.policy_view = loader.view(sub.claim_category)
        except KeyError:
            valid = ", ".join(k.upper() for k in loader.policy.opd_categories)
            raise AgentFailure(AgentError(
                code=ErrorCode.INVALID_CATEGORY,
                message=f"unknown category {sub.claim_category}",
                member_message=(f"'{sub.claim_category}' is not a covered claim category. "
                                f"Covered categories: {valid}."),
            ))
        covered_ref = f"opd_categories.{ctx.policy_view.opd_key}.covered"
        if not ctx.policy_view.rules.covered:
            raise AgentFailure(AgentError(
                code=ErrorCode.INVALID_CATEGORY,
                message=f"category {sub.claim_category} not covered by policy",
                member_message=(f"{sub.claim_category} claims are not covered under your "
                                f"policy {loader.policy.policy_id}."),
                detail={"rule_ref": covered_ref},
            ))
        checks.append(PolicyCheck(check="CATEGORY_COVERED", result=CheckResult.PASS,
                                  rule_ref=covered_ref,
                                  detail={"covered": True}))

        min_amt = loader.policy.submission_rules.minimum_claim_amount
        if sub.claimed_amount < min_amt:
            raise AgentFailure(AgentError(
                code=ErrorCode.AMOUNT_BELOW_MINIMUM,
                message=f"claimed {sub.claimed_amount} < min {min_amt}",
                member_message=(f"The claimed amount ₹{sub.claimed_amount} is below the minimum "
                                f"claimable amount of ₹{min_amt} under your policy."),
                detail={"claimed": sub.claimed_amount, "minimum": min_amt},
            ))
        checks.append(PolicyCheck(check="MINIMUM_AMOUNT", result=CheckResult.PASS,
                                  rule_ref="submission_rules.minimum_claim_amount",
                                  detail={"claimed": sub.claimed_amount, "minimum": min_amt}))

        checks.append(PolicyCheck(check="SUBMISSION_DEADLINE", result=CheckResult.SKIPPED,
                                  rule_ref="submission_rules.deadline_days_from_treatment",
                                  detail={"reason": "no submission timestamp in test data"}))

        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          checks=checks, duration_ms=int((time.monotonic() - t0) * 1000))
