"""
Render helpers for claim outcomes and traces.
Pure Streamlit display logic — no HTTP calls, safe to unit-test with mock st.
"""
from __future__ import annotations
import json

import streamlit as st


def render_trace(trace: dict) -> None:
    steps = trace.get("steps", [])
    if not steps:
        return
    st.subheader("Decision trace")
    icons = {"PASS": "✅", "FAIL": "❌", "DEGRADED": "⚠️", "SKIPPED": "⏭️"}
    for step in steps:
        icon = icons.get(step.get("status", ""), "•")
        label = (
            f"{icon} {step.get('step', '')} — {step.get('agent', '')} "
            f"({step.get('status', '')}, {step.get('duration_ms', 0)}ms)"
        )
        with st.expander(label):
            for c in step.get("checks", []):
                line = f"- **{c['check']}** → {c['result']}"
                if c.get("rule_ref"):
                    line += f" · rule: `{c['rule_ref']}`"
                st.markdown(line)
                if c.get("detail"):
                    st.json(c["detail"], expanded=False)
            if step.get("error"):
                st.code(json.dumps(step["error"], indent=2))
            for e in step.get("confidence_entries", []):
                st.caption(f"confidence ×{e['factor']} — {e['reason']}")


def render_decision(out: dict) -> None:
    if out["status"] == "STOPPED":
        st.error(f"Claim stopped\n\n**{out['member_message']}**")
    else:
        d = out["decision"]
        color = {
            "APPROVED": st.success,
            "PARTIAL": st.warning,
            "REJECTED": st.error,
            "MANUAL_REVIEW": st.info,
        }.get(d["status"], st.info)
        color(
            f"**{d['status']}** — approved ₹{d['approved_amount']} · "
            f"confidence {d['confidence']:.2f}\n\n{d['member_message']}"
        )
    render_trace(out.get("trace", {}))
