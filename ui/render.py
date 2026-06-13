"""
Render helpers for claim outcomes and traces.
Pure Streamlit display logic — no HTTP calls, safe to unit-test with mock st.

This module also exposes the shared design-system primitives (status colours,
`status_pill`, `inject_css`) so the app, decision card, and eval views all speak
one visual language.
"""
from __future__ import annotations
import json

import streamlit as st


# ---------------------------------------------------------------------------
# Design system — shared colours, status config, reusable HTML primitives
# ---------------------------------------------------------------------------

# Single source of truth for status -> colour + presentation.
_STATUS_THEME = {
    "APPROVED":      {"label": "Approved",      "icon": "✅", "color": "#15803d", "bg": "#dcfce7", "border": "#86efac"},
    "PARTIAL":       {"label": "Partial",       "icon": "🟡", "color": "#b45309", "bg": "#fef3c7", "border": "#fcd34d"},
    "REJECTED":      {"label": "Rejected",      "icon": "❌", "color": "#b91c1c", "bg": "#fee2e2", "border": "#fca5a5"},
    "MANUAL_REVIEW": {"label": "Manual Review", "icon": "🔵", "color": "#1d4ed8", "bg": "#dbeafe", "border": "#93c5fd"},
    "STOPPED":       {"label": "Stopped",       "icon": "⏹", "color": "#475569", "bg": "#e2e8f0", "border": "#cbd5e1"},
}

# Maps decision status -> the Streamlit alert fn the tests assert on.
_DECISION_CONFIG = {
    "APPROVED":      {"fn": "success", "label": "APPROVED",        "icon": "✅"},
    "PARTIAL":       {"fn": "warning", "label": "PARTIAL APPROVAL", "icon": "🟡"},
    "REJECTED":      {"fn": "error",   "label": "REJECTED",         "icon": "❌"},
    "MANUAL_REVIEW": {"fn": "info",    "label": "MANUAL REVIEW",    "icon": "🔵"},
}

_TRACE_ICONS = {"PASS": "✅", "FAIL": "❌", "DEGRADED": "⚠️", "SKIPPED": "⏭️"}
_TRACE_THEME = {
    "PASS":     {"color": "#15803d", "bg": "#dcfce7"},
    "FAIL":     {"color": "#b91c1c", "bg": "#fee2e2"},
    "DEGRADED": {"color": "#b45309", "bg": "#fef3c7"},
    "SKIPPED":  {"color": "#64748b", "bg": "#e2e8f0"},
}


def inject_css() -> None:
    """Inject the global stylesheet. Called once near the top of the app."""
    st.markdown(
        """
        <style>
          :root {
            --pc-radius: 14px;
            --pc-border: #e6e9ef;
            --pc-muted: #6b7280;
            --pc-ink: #111827;
          }
          /* Typography + spacing rhythm */
          .stApp { font-feature-settings: "cv11", "ss01"; }
          h1, h2, h3 { letter-spacing: -0.01em; }
          .block-container { padding-top: 2.2rem; }

          /* Card surface */
          .pc-card {
            background: #ffffff;
            border: 1px solid var(--pc-border);
            border-radius: var(--pc-radius);
            padding: 1.25rem 1.4rem;
            box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.06);
          }
          .pc-card + .pc-card { margin-top: .75rem; }

          /* Status pill */
          .pc-pill {
            display: inline-flex; align-items: center; gap: .4rem;
            padding: .28rem .7rem; border-radius: 999px;
            font-size: .8rem; font-weight: 650; line-height: 1;
            border: 1px solid transparent; white-space: nowrap;
          }

          /* Decision hero */
          .pc-hero { display: flex; align-items: center; gap: 1rem;
                     flex-wrap: wrap; margin-bottom: .25rem; }
          .pc-hero-amt { font-size: 1.9rem; font-weight: 720;
                         color: var(--pc-ink); line-height: 1; }
          .pc-hero-amt small { font-size: .8rem; font-weight: 500;
                               color: var(--pc-muted); display:block; margin-top:.2rem; }

          /* Confidence meter */
          .pc-meter { height: 8px; border-radius: 999px; background: #eef0f4;
                      overflow: hidden; margin: .35rem 0 .15rem; }
          .pc-meter > span { display:block; height:100%; border-radius:999px; }

          /* Member message callout */
          .pc-callout {
            border-left: 4px solid #cbd5e1; background: #f8fafc;
            padding: .75rem 1rem; border-radius: 8px; color: #1f2937;
            font-size: .95rem; line-height: 1.5;
          }

          /* Timeline rows (trace) */
          .pc-step {
            display:flex; align-items:center; gap:.7rem;
            padding:.55rem .15rem; border-bottom:1px solid #f1f3f7;
          }
          .pc-step:last-child { border-bottom:none; }
          .pc-step-dot { width:26px; height:26px; border-radius:999px;
                         display:flex; align-items:center; justify-content:center;
                         font-size:.85rem; flex:none; }
          .pc-step-name { font-weight:600; color:var(--pc-ink); }
          .pc-step-meta { color:var(--pc-muted); font-size:.8rem; }

          /* Eval summary */
          .pc-summary-num { font-size:2.6rem; font-weight:760; line-height:1; }
          .pc-summary-sub { color:var(--pc-muted); font-size:.9rem; }

          /* Eval case row */
          .pc-case {
            display:flex; align-items:center; gap:.8rem;
            padding:.2rem 0;
          }
          .pc-case-id { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                        font-size:.82rem; color:var(--pc-muted); }
          .pc-mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                     font-size:.8rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def status_pill(status: str, *, text: str | None = None) -> str:
    """Return an inline-HTML status pill for the given status key."""
    t = _STATUS_THEME.get(status, _STATUS_THEME["MANUAL_REVIEW"])
    label = text if text is not None else t["label"]
    return (
        f'<span class="pc-pill" style="color:{t["color"]};'
        f'background:{t["bg"]};border-color:{t["border"]};">'
        f'{t["icon"]} {label}</span>'
    )


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "High"
    if confidence >= 0.6:
        return "Medium"
    return "Low"


def _confidence_color(confidence: float) -> str:
    if confidence >= 0.85:
        return "#15803d"
    if confidence >= 0.6:
        return "#b45309"
    return "#b91c1c"


# ---------------------------------------------------------------------------
# Trace
# ---------------------------------------------------------------------------

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
    chips = []
    for key, n in (("PASS", counts.get("PASS")), ("FAIL", counts.get("FAIL")),
                   ("DEGRADED", counts.get("DEGRADED")), ("SKIPPED", counts.get("SKIPPED"))):
        if n:
            th = _TRACE_THEME[key]
            chips.append(
                f'<span class="pc-pill" style="color:{th["color"]};background:{th["bg"]};">'
                f'{_TRACE_ICONS[key]} {n} {key.lower()}</span>'
            )
    if chips:
        st.markdown(
            '<div style="display:flex;gap:.4rem;flex-wrap:wrap;margin:.2rem 0 .6rem;">'
            + "".join(chips)
            + "</div>",
            unsafe_allow_html=True,
        )

    for step in steps:
        status = step.get("status", "")
        icon = _TRACE_ICONS.get(status, "•")
        dur = step.get("duration_ms", 0)
        th = _TRACE_THEME.get(status, {"color": "#64748b", "bg": "#e2e8f0"})
        name = step.get("step", "")
        agent = step.get("agent", "")

        # Clean timeline row as the expander header surface.
        st.markdown(
            f'<div class="pc-step">'
            f'<span class="pc-step-dot" style="color:{th["color"]};background:{th["bg"]};">{icon}</span>'
            f'<span><span class="pc-step-name">{name}</span> '
            f'<span class="pc-step-meta">· {agent} · {dur} ms · {status}</span></span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Expander label keeps the asserted icon; details tucked inside.
        label = f"{icon} {name} — {agent} ({status}, {dur}ms)"
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


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

def render_decision(out: dict) -> None:
    if out["status"] == "STOPPED":
        msg = out["member_message"]
        # Rich stopped card (HTML) + the single asserted st.error call.
        st.markdown(
            f'<div class="pc-card" style="border-left:4px solid #94a3b8;">'
            f'<div class="pc-hero">{status_pill("STOPPED")}</div>'
            f'<div class="pc-callout" style="margin-top:.6rem;">{msg}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.error(f"Claim stopped\n\n**{msg}**")
        render_trace(out.get("trace", {}))
        return

    d = out["decision"]
    status = d["status"]
    cfg = _DECISION_CONFIG.get(status, _DECISION_CONFIG["MANUAL_REVIEW"])
    approved = d["approved_amount"]
    confidence = d["confidence"]
    message = d["member_message"]
    pct = min(int(round(confidence * 100)), 100)
    cc = _confidence_color(confidence)

    # Polished decision card: status pill + amount + confidence meter + callout.
    st.markdown(
        f'<div class="pc-card">'
        f'<div class="pc-hero">'
        f'  {status_pill(status, text=cfg["label"])}'
        f'  <div class="pc-hero-amt">₹{approved:,}<small>Approved amount</small></div>'
        f'  <div style="flex:1;min-width:160px;">'
        f'    <div style="display:flex;justify-content:space-between;font-size:.82rem;color:#6b7280;">'
        f'      <span>Confidence</span><span style="color:{cc};font-weight:650;">{pct}% · {_confidence_label(confidence)}</span>'
        f'    </div>'
        f'    <div class="pc-meter"><span style="width:{pct}%;background:{cc};"></span></div>'
        f'  </div>'
        f'</div>'
        f'<div class="pc-callout" style="margin-top:.8rem;">{message}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Primary status alert — exactly one call to the mapped st.* function.
    # Tests assert assert_called_once() on st.success/warning/error/info.
    st_fn = getattr(st, cfg["fn"])
    st_fn(
        f"**{cfg['icon']} {cfg['label']}** — Approved ₹{approved:,} · "
        f"Confidence {confidence:.0%}\n\n{message}"
    )

    st.divider()
    render_trace(out.get("trace", {}))
