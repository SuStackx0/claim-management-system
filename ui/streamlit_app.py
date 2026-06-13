from __future__ import annotations
import json
import sys
from pathlib import Path

# `streamlit run ui/streamlit_app.py` only puts the script's own dir (ui/) on
# sys.path, not the project root — so the `ui` package isn't importable. Add the
# project root so package imports resolve for local runs and the Docker image alike.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from ui.helpers import get, post
from ui.render import render_decision, render_trace, inject_css, status_pill

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Plum Claims Processor",
    page_icon="🏥",
    layout="wide",
)

inject_css()

# Pipeline stages shown in the processing status (single source of truth).
_PIPELINE_STAGES = [
    ("Intake", "Validating member, policy & required documents"),
    ("Documents", "Reading uploaded bills, prescriptions & reports"),
    ("Extraction", "Extracting structured fields from documents"),
    ("Consistency", "Cross-checking amounts, dates & member details"),
    ("Adjudication", "Applying policy rules & computing the payout"),
    ("Fraud", "Scanning for anomalies & duplicate claims"),
    ("Decision", "Finalising the outcome & member message"),
]

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🏥 Plum Claims")
    st.caption("AI-powered medical claims processing")
    st.divider()
    page = st.radio(
        "Navigate",
        ["Submit Claim", "Review Claims", "Eval (12 cases)"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown(
        '<div style="font-size:.8rem;color:#6b7280;line-height:1.6;">'
        'Plum Health Insurance<br>'
        '<span class="pc-mono">PLUM_GHI_2024</span>'
        '</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Page: Submit Claim
# ---------------------------------------------------------------------------
if page == "Submit Claim":
    st.title("Submit a Claim")
    st.caption("Fill in the details, attach supporting documents, and the AI pipeline will adjudicate in 15–25 seconds.")
    st.divider()

    members = get("/members")

    with st.form("claim_form"):
        st.subheader("Member & claim details")
        col1, col2 = st.columns(2)
        with col1:
            member = st.selectbox(
                "Member",
                members,
                format_func=lambda m: f"{m['member_id']} — {m['name']}",
                help="Select the insured member for this claim.",
            )
            category = st.selectbox(
                "Claim Category",
                ["CONSULTATION", "DIAGNOSTIC", "PHARMACY", "DENTAL", "VISION", "ALTERNATIVE_MEDICINE"],
                help="Choose the type of medical service.",
            )
            treatment_date = st.date_input(
                "Treatment Date",
                help="Date the treatment or service was received.",
            )
        with col2:
            amount = st.number_input(
                "Claimed Amount (₹)",
                min_value=0,
                step=100,
                help="Total amount claimed for reimbursement.",
            )
            hospital = st.text_input(
                "Hospital / Provider Name",
                placeholder="e.g. Apollo Hospitals, Chennai",
                help="Optional — name of the hospital or clinic.",
            )
            files = st.file_uploader(
                "Supporting Documents",
                accept_multiple_files=True,
                type=["pdf", "jpg", "jpeg", "png"],
                help="Upload bills, prescriptions, or diagnostic reports (PDF/image).",
            )

        st.divider()
        submitted = st.form_submit_button("Submit Claim", type="primary", use_container_width=True)

    if submitted:
        payload = {
            "member_id": member["member_id"],
            "policy_id": "PLUM_GHI_2024",
            "claim_category": category,
            "treatment_date": str(treatment_date),
            "claimed_amount": int(amount),
            "hospital_name": hospital or None,
        }
        with st.status("Processing claim through the AI pipeline", expanded=True) as status_box:
            # A calm, ordered preview of the stages the claim passes through —
            # rendered once, no raw dumps, no per-token chatter.
            stage_html = "".join(
                f'<div style="display:flex;gap:.6rem;align-items:baseline;padding:.18rem 0;">'
                f'<span style="color:#9ca3af;">{i + 1}.</span>'
                f'<span style="font-weight:600;color:#111827;">{name}</span>'
                f'<span style="color:#6b7280;font-size:.85rem;">— {desc}</span>'
                f'</div>'
                for i, (name, desc) in enumerate(_PIPELINE_STAGES)
            )
            st.markdown(
                f'<div style="margin:.1rem 0 .2rem;">{stage_html}</div>',
                unsafe_allow_html=True,
            )
            out = post(
                "/claims/upload",
                data={"payload": json.dumps(payload)},
                files=[("files", (f.name, f.getvalue(), f.type)) for f in (files or [])],
            )
            status_box.update(label="Pipeline complete", state="complete", expanded=False)

        st.divider()
        render_decision(out)

# ---------------------------------------------------------------------------
# Page: Review Claims
# ---------------------------------------------------------------------------
elif page == "Review Claims":
    st.title("Claims Review")
    st.caption("Browse every submitted claim and inspect the full AI pipeline decision for each.")
    st.divider()

    claims = get("/claims")
    if not claims:
        st.info("No claims have been submitted yet. Head to **Submit Claim** to create your first one.")
    else:
        st.subheader(f"All claims · {len(claims)}")
        st.dataframe(
            claims,
            use_container_width=True,
            hide_index=True,
        )
        st.divider()
        st.subheader("Inspect a claim")
        cid = st.selectbox(
            "Select claim ID",
            [c["claim_id"] for c in claims],
            help="Choose a claim to view its full decision and pipeline trace.",
        )
        if cid:
            with st.spinner("Loading claim details…"):
                detail = get(f"/claims/{cid}")
            render_decision(detail)

# ---------------------------------------------------------------------------
# Page: Eval (12 cases)
# ---------------------------------------------------------------------------
else:
    st.title("Eval — 12 Assignment Test Cases")
    st.caption("Runs all 12 predefined cases through the pipeline and checks each decision against its expected outcome.")
    st.divider()

    if st.button("Run all 12 test cases", type="primary"):
        with st.status("Running evaluation suite · 12 cases · ~3 minutes", expanded=True) as eval_box:
            st.markdown(
                '<div style="color:#6b7280;font-size:.9rem;">'
                'Each case is submitted to the live pipeline and its decision is compared '
                'against the expected outcome. Sit tight — results appear below when complete.'
                '</div>',
                unsafe_allow_html=True,
            )
            report = post("/eval/run")
            eval_box.update(label="Evaluation complete", state="complete", expanded=False)

        # --- summary ---
        passed = report["passed"]
        total = 12
        failed = total - passed
        rate = passed / total
        summary_color = "#15803d" if passed == total else ("#b45309" if passed >= total * 0.8 else "#b91c1c")

        st.markdown(
            f'<div class="pc-card">'
            f'<div style="display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap;">'
            f'  <div>'
            f'    <div class="pc-summary-num" style="color:{summary_color};">{passed} / {total}</div>'
            f'    <div class="pc-summary-sub">test cases passed</div>'
            f'  </div>'
            f'  <div style="flex:1;min-width:220px;">'
            f'    <div style="display:flex;justify-content:space-between;font-size:.82rem;color:#6b7280;margin-bottom:.25rem;">'
            f'      <span>Pass rate</span><span style="color:{summary_color};font-weight:650;">{rate:.0%}</span>'
            f'    </div>'
            f'    <div class="pc-meter" style="height:10px;"><span style="width:{rate*100:.0f}%;background:{summary_color};"></span></div>'
            f'    <div class="pc-summary-sub" style="margin-top:.4rem;">'
            f'      {passed} passed · {failed} failed'
            f'    </div>'
            f'  </div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown("")  # breathing room
        st.subheader("Per-case results")

        for c in report["cases"]:
            ok = c["passed"]
            pill_status = "APPROVED" if ok else "REJECTED"
            pill_text = "PASS" if ok else "FAIL"
            # Clean status-chip row as the expander surface.
            st.markdown(
                f'<div class="pc-case">'
                f'  {status_pill(pill_status, text=pill_text)}'
                f'  <span class="pc-case-id">{c["case_id"]}</span>'
                f'  <span style="font-weight:600;color:#111827;">{c["case_name"]}</span>'
                f'  <span style="color:#6b7280;">→</span>'
                f'  <span class="pc-mono">{c["produced_decision"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            icon = "✅" if ok else "❌"
            with st.expander(f"{icon} {c['case_id']} — details"):
                st.markdown("**Member message**")
                st.markdown(
                    f'<div class="pc-callout">{c["member_message"]}</div>',
                    unsafe_allow_html=True,
                )
                if c["failures"]:
                    st.markdown("**Mismatches**")
                    st.error("; ".join(c["failures"]))
                st.markdown("")
                render_trace(c["trace"])
