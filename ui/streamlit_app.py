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
from ui.render import render_decision, render_trace

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Plum Claims Processor",
    page_icon="🏥",
    layout="wide",
)

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
    st.caption("Plum Health Insurance · PLUM_GHI_2024")

# ---------------------------------------------------------------------------
# Page: Submit Claim
# ---------------------------------------------------------------------------
if page == "Submit Claim":
    st.title("🏥 Submit a Claim")
    st.caption("Fill in the details below and upload supporting documents. Processing takes 15–25 seconds.")
    st.divider()

    members = get("/members")

    with st.form("claim_form"):
        st.subheader("Member & Claim Details")
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
        submitted = st.form_submit_button("🚀 Submit Claim", type="primary", use_container_width=True)

    if submitted:
        payload = {
            "member_id": member["member_id"],
            "policy_id": "PLUM_GHI_2024",
            "claim_category": category,
            "treatment_date": str(treatment_date),
            "claimed_amount": int(amount),
            "hospital_name": hospital or None,
        }
        with st.status("Processing claim through AI pipeline…", expanded=True) as status_box:
            st.write("Submitting to pipeline...")
            out = post(
                "/claims/upload",
                data={"payload": json.dumps(payload)},
                files=[("files", (f.name, f.getvalue(), f.type)) for f in (files or [])],
            )
            status_box.update(label="Pipeline complete!", state="complete", expanded=False)
        st.divider()
        render_decision(out)

# ---------------------------------------------------------------------------
# Page: Review Claims
# ---------------------------------------------------------------------------
elif page == "Review Claims":
    st.title("📋 Claims Review")
    st.caption("Browse all submitted claims and inspect the AI pipeline decision for each.")
    st.divider()

    claims = get("/claims")
    if not claims:
        st.info("No claims have been submitted yet. Use **Submit Claim** to create one.")
    else:
        st.subheader(f"All Claims ({len(claims)} total)")
        # show a tidy summary table
        st.dataframe(
            claims,
            use_container_width=True,
            hide_index=True,
        )
        st.divider()
        st.subheader("Inspect a Claim")
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
    st.title("🧪 Eval — 12 Assignment Test Cases")
    st.caption("Runs all 12 predefined test cases through the pipeline and checks each decision against the expected outcome.")
    st.divider()

    if st.button("▶ Run all 12 test cases", type="primary"):
        with st.spinner("Running eval — this takes approximately 3 minutes…"):
            report = post("/eval/run")

        # --- summary metrics ---
        passed = report["passed"]
        total = 12
        failed = total - passed
        st.subheader("Results")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Passed", f"{passed}/{total}", delta=None)
        mc2.metric("Failed", str(failed), delta=None)
        mc3.metric("Pass Rate", f"{passed/total:.0%}", delta=None)

        if passed == total:
            st.success(f"🎉 All {total} test cases passed!")
        elif passed >= total * 0.8:
            st.warning(f"⚠️ {passed}/{total} passed — {failed} case(s) need attention.")
        else:
            st.error(f"❌ {passed}/{total} passed — significant failures detected.")

        st.divider()
        st.subheader("Per-case Detail")
        for c in report["cases"]:
            icon = "✅" if c["passed"] else "❌"
            label = f"{icon} {c['case_id']} — {c['case_name']}: {c['produced_decision']}"
            with st.expander(label):
                st.markdown(f"**Member message:** {c['member_message']}")
                if c["failures"]:
                    st.error("; ".join(c["failures"]))
                render_trace(c["trace"])
