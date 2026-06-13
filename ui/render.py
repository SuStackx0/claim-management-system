"""
Render helpers for claim outcomes and traces.
Pure Streamlit display logic — no HTTP calls, safe to unit-test with mock st.
"""
from __future__ import annotations
import json

import streamlit as st


# ---------------------------------------------------------------------------
# Status badge / display config
# ---------------------------------------------------------------------------

_DECISION_CONFIG = {
    "APPROVED": {
        "fn": "success",
        "label": "APPROVED",
        "icon": "✅",
    },
    "PARTIAL": {
        "fn": "warning",
        "label": "PARTIAL APPROVAL",
        "icon": "🟡",
    },
    "REJECTED": {
        "fn": "error",
        "label": "REJECTED",
        "icon": "❌",
    },
    "MANUAL_REVIEW": {
        "fn": "info",
        "label": "MANUAL REVIEW",
        "icon": "🔵",
    },
}

_TRACE_ICONS = {"PASS": "✅", "FAIL": "❌", "DEGRADED": "⚠️", "SKIPPED": "⏭️"}


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "High"
    if confidence >= 0.6:
        return "Medium"
    return "Low"


def render_trace(trace: dict) -> None:
    steps = trace.get("steps", [])
    if not steps:
        return
    st.subheader("Decision trace")

    # compact step-count summary as markdown (not caption — avoids breaking
    # tests that assert st.caption call_count == len(confidence_entries))
    counts: dict[str, int] = {}
    for s in steps:
        k = s.get("status", "")
        counts[k] = counts.get(k, 0) + 1
    parts = []
    if counts.get("PASS"):
        parts.append(f"✅ {counts['PASS']} passed")
    if counts.get("FAIL"):
        parts.append(f"❌ {counts['FAIL']} failed")
    if counts.get("DEGRADED"):
        parts.append(f"⚠️ {counts['DEGRADED']} degraded")
    if counts.get("SKIPPED"):
        parts.append(f"⏭️ {counts['SKIPPED']} skipped")
    if parts:
        st.markdown("_" + "  ·  ".join(parts) + "_")

    for step in steps:
        icon = _TRACE_ICONS.get(step.get("status", ""), "•")
        status = step.get("status", "")
        dur = step.get("duration_ms", 0)
        label = (
            f"{icon} {step.get('step', '')} — {step.get('agent', '')} "
            f"({status}, {dur}ms)"
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
        render_trace(out.get("trace", {}))
        return

    d = out["decision"]
    status = d["status"]
    cfg = _DECISION_CONFIG.get(status, _DECISION_CONFIG["MANUAL_REVIEW"])
    approved = d["approved_amount"]
    confidence = d["confidence"]
    message = d["member_message"]

    # Primary status alert — exactly one call to the mapped st.* function.
    # Tests assert assert_called_once() on st.success/warning/error/info.
    st_fn = getattr(st, cfg["fn"])
    st_fn(
        f"**{cfg['icon']} {cfg['label']}** — Approved ₹{approved:,} · "
        f"Confidence {confidence:.0%}\n\n{message}"
    )

    # Summary metrics (three separate metric calls; safe with MagicMock)
    st.metric("Approved Amount", f"₹{approved:,}")
    st.metric("Confidence", f"{confidence:.0%} ({_confidence_label(confidence)})")
    st.metric("Decision", cfg["label"])

    # Confidence as a progress bar (visual polish)
    st.progress(min(int(confidence * 100), 100))

    st.divider()
    render_trace(out.get("trace", {}))
