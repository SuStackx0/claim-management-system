from __future__ import annotations
import time
from app.agents.base import Agent
from app.core.context import ClaimContext
from app.core.trace import StepResult, StepStatus
from app.models.domain import Decision, DecisionStatus

CONFIDENCE_REVIEW_THRESHOLD = 0.75


class Aggregator(Agent):
    name = "Aggregator"
    step = "AGGREGATION"
    fatal = True

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        confidence = round(ctx.trace.confidence(), 4)
        degraded_steps = [s.step for s in ctx.trace.steps
                          if s.status in (StepStatus.DEGRADED, StepStatus.SKIPPED)]
        notes = []
        if degraded_steps:
            notes.append(f"Components degraded/skipped: {', '.join(degraded_steps)}. "
                         f"Manual review recommended due to incomplete processing.")
        if ctx.unverified_checks:
            notes.append("Could not verify: " + ", ".join(dict.fromkeys(ctx.unverified_checks))
                         + ". Manual review required — a decision-relevant check could not be "
                         "confirmed from the submitted documents.")
        if confidence < CONFIDENCE_REVIEW_THRESHOLD and not degraded_steps:
            notes.append("Low confidence — manual review recommended.")

        if ctx.fraud_signals:
            reasons = [f"{s.signal}: {s.detail}" for s in ctx.fraud_signals]
            decision = Decision(
                status=DecisionStatus.MANUAL_REVIEW,
                approved_amount=0,
                reasons=reasons,
                confidence=confidence,
                member_message=("Your claim needs a quick manual check by our team before we can "
                                "process it. No action is needed from you right now."),
                ops_summary="Routed to manual review. Signals: " + "; ".join(reasons)
                            + (" | " + " ".join(notes) if notes else ""))
        elif ctx.blocking_reasons:
            decision = Decision(
                status=DecisionStatus.REJECTED,
                approved_amount=0,
                reasons=list(dict.fromkeys(ctx.blocking_reasons)),
                confidence=confidence,
                member_message=self._rejection_message(ctx),
                ops_summary=f"Rejected: {ctx.blocking_reasons}. "
                            + (" ".join(notes) if notes else ""))
        elif ctx.unverified_checks:
            # No hard rejection and no fraud, but a decision-relevant check could not be
            # verified (e.g. patient identity, because a required doc failed extraction).
            # Never auto-approve on the back of an unverifiable check — route to a human.
            unverified = list(dict.fromkeys(ctx.unverified_checks))
            decision = Decision(
                status=DecisionStatus.MANUAL_REVIEW,
                approved_amount=0,
                reasons=[f"UNVERIFIED_{c}" for c in unverified],
                confidence=confidence,
                member_message=("We're reviewing your claim manually because we couldn't fully "
                                "verify it from the documents provided. No action is needed from "
                                "you right now."),
                ops_summary="Routed to manual review — unverifiable checks: "
                            + ", ".join(unverified) + ". " + (" ".join(notes) if notes else ""))
        else:
            approved = [v for v in ctx.line_verdicts if v.verdict in ("APPROVED", "CAPPED")]
            rejected = [v for v in ctx.line_verdicts if v.verdict == "REJECTED"]
            payable = int(ctx.financial.get("payable", 0))
            if approved and rejected:
                status = DecisionStatus.PARTIAL
            elif approved:
                status = DecisionStatus.APPROVED
            else:
                # No payable line items. This is a REJECTED outcome even though every
                # pipeline step PASSed — so the reason must be made explicit, never a
                # vacuous "All checks passed" (see _zero_payable_reasons / member msg).
                status = DecisionStatus.REJECTED
            line_summary = "; ".join(f"{v.description}: {v.verdict} ({v.reason})"
                                     for v in ctx.line_verdicts)
            if status == DecisionStatus.REJECTED:
                reasons = self._zero_payable_reasons(ctx, rejected)
                member_message = self._zero_payable_message(ctx, rejected)
            else:
                reasons = [v.reason for v in rejected] if rejected else ["All checks passed"]
                member_message = self._approval_message(ctx, payable, rejected)
            decision = Decision(
                status=status,
                approved_amount=payable,
                reasons=reasons,
                confidence=confidence,
                member_message=member_message,
                ops_summary=f"{status}: payable ₹{payable}. Lines: {line_summary}. "
                            f"Financial: {ctx.financial}. "
                            + (" ".join(notes) if notes else ""))

        ctx.trace.decision = decision
        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          duration_ms=int((time.monotonic() - t0) * 1000))

    def _rejection_message(self, ctx) -> str:
        parts = []
        for s in ctx.trace.steps:
            for c in s.checks:
                if c.result == "FAIL" and c.check == "WAITING_PERIOD":
                    parts.append(f"This treatment falls inside a waiting period. You will be "
                                 f"eligible for {c.detail.get('condition_matched', 'this')} "
                                 f"claims from {c.detail['eligible_from']}.")
                elif c.result == "FAIL" and c.check == "PER_CLAIM_LIMIT":
                    parts.append(f"Your claimed amount ₹{c.detail['claimed']} exceeds the "
                                 f"per-claim limit of ₹{c.detail['limit']}.")
                elif c.result == "FAIL" and c.check == "PRE_AUTHORIZATION":
                    parts.append(f"{c.detail['test']} above ₹{c.detail['threshold']} requires "
                                 f"pre-authorization, which was not obtained. Please get "
                                 f"pre-authorization from your insurer and resubmit the claim "
                                 f"with the pre-authorization ID.")
                elif c.result == "FAIL" and c.check == "EXCLUSIONS":
                    parts.append(f"'{c.detail['matched_exclusion']}' is excluded under your "
                                 f"policy and cannot be claimed.")
        return " ".join(parts) or "Your claim was rejected. See the decision details."

    def _approval_message(self, ctx, payable: int, rejected) -> str:
        f = ctx.financial
        msg = f"Approved amount: ₹{payable}."
        if f.get("network_discount"):
            nd_pct = f.get("network_discount_percent", 0)
            cp_pct = f.get("copay_percent", 0)
            pre_copay = payable + f.get("copay", 0)
            msg += (f" Network discount {nd_pct}% (−₹{f['network_discount']}) applied first"
                    f" (net ₹{pre_copay}), then co-pay {cp_pct}% (−₹{f['copay']}).")
        elif f.get("copay"):
            cp_pct = f.get("copay_percent", 0)
            msg += f" A {cp_pct}% co-pay (−₹{f['copay']}) was applied."
        if rejected:
            msg += " Not covered: " + "; ".join(f"{v.description} (₹{v.amount}) — {v.reason}"
                                                for v in rejected)
        return msg

    def _zero_payable_reasons(self, ctx, rejected) -> list[str]:
        """Reasons for a REJECTED outcome where NO line item is payable, despite every
        step passing. Distinguishes 'everything billed was excluded/non-covered' from
        'nothing billable could be extracted' so the trace explains the ₹0, never the
        contradictory 'All checks passed'."""
        if rejected:
            return list(dict.fromkeys(["NOT_COVERED"] + [v.reason for v in rejected]))
        return ["NOTHING_BILLABLE"]

    def _zero_payable_message(self, ctx, rejected) -> str:
        """Member-facing explanation for a ₹0 REJECTED outcome (no payable lines)."""
        if rejected:
            return ("Approved amount: ₹0 — none of the billed items are covered under your "
                    "policy. Not covered: "
                    + "; ".join(f"{v.description} (₹{v.amount}) — {v.reason}" for v in rejected))
        return ("Approved amount: ₹0 — we could not identify any billable, covered item on the "
                "documents provided. Please upload an itemised bill showing the treatment and "
                "amounts so we can process your claim.")
