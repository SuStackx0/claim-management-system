from __future__ import annotations
import json

import streamlit as st

from ui.helpers import get, post
from ui.render import render_decision, render_trace

st.set_page_config(page_title="Plum Claims", layout="wide")

page = st.sidebar.radio(
    "Plum Claims",
    ["Submit Claim", "Review Claims", "Eval (12 cases)"],
)

if page == "Submit Claim":
    st.title("Submit a claim")
    members = get("/members")
    col1, col2 = st.columns(2)
    with col1:
        member = st.selectbox(
            "Member", members,
            format_func=lambda m: f"{m['member_id']} — {m['name']}",
        )
        category = st.selectbox(
            "Category",
            ["CONSULTATION", "DIAGNOSTIC", "PHARMACY", "DENTAL", "VISION", "ALTERNATIVE_MEDICINE"],
        )
        treatment_date = st.date_input("Treatment date")
    with col2:
        amount = st.number_input("Claimed amount (₹)", min_value=0, step=100)
        hospital = st.text_input("Hospital name (optional)")
        files = st.file_uploader("Documents (images/PDF)", accept_multiple_files=True)
    if st.button("Submit claim", type="primary"):
        payload = {
            "member_id": member["member_id"],
            "policy_id": "PLUM_GHI_2024",
            "claim_category": category,
            "treatment_date": str(treatment_date),
            "claimed_amount": int(amount),
            "hospital_name": hospital or None,
        }
        with st.spinner("Processing through pipeline..."):
            out = post(
                "/claims/upload",
                data={"payload": json.dumps(payload)},
                files=[("files", (f.name, f.getvalue(), f.type)) for f in (files or [])],
            )
        render_decision(out)

elif page == "Review Claims":
    st.title("Claims review")
    claims = get("/claims")
    if not claims:
        st.info("No claims yet.")
    else:
        st.dataframe(claims, use_container_width=True)
        cid = st.selectbox("Open claim", [c["claim_id"] for c in claims])
        if cid:
            render_decision(get(f"/claims/{cid}"))

else:
    st.title("Eval — 12 assignment test cases")
    if st.button("Run all 12 test cases", type="primary"):
        with st.spinner("Running eval (takes ~3 min)..."):
            report = post("/eval/run")
        st.metric("Passed", f"{report['passed']}/12")
        for c in report["cases"]:
            icon = "✅" if c["passed"] else "❌"
            label = f"{icon} {c['case_id']} — {c['case_name']}: {c['produced_decision']}"
            with st.expander(label):
                st.markdown(f"**Member message:** {c['member_message']}")
                if c["failures"]:
                    st.error("; ".join(c["failures"]))
                render_trace(c["trace"])
