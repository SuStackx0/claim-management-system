# Demo Test Cases — Submit Form Walkthrough

A ready-to-run demo script of **16 claim scenarios** you can drive entirely through the
**Submit Claim** form (Streamlit or React). Together they exercise every main decision
path and the important edge cases: clean approvals, network-discount math, partial
approval, all four rejection reasons, manual review, and the three "stop early"
document-quality cases.

## How to run a scenario

The Submit form exposes exactly six inputs:

- **Member** — dropdown of the policy roster
- **Claim Category** — CONSULTATION / DIAGNOSTIC / PHARMACY / DENTAL / VISION / ALTERNATIVE_MEDICINE
- **Treatment Date**
- **Claimed Amount (₹)**
- **Hospital / Provider Name** (optional — drives the network-discount check)
- **Supporting Documents** — image uploads from `sample_docs/`

For each scenario below, set the form fields from the table and upload the listed files
from `sample_docs/`, then submit.

### A note on live extraction vs. policy logic

The pipeline reads the uploaded images with a **vision LLM (Groq)**, so the outcome of a
*live* run depends on the LLM correctly reading the patient name, diagnosis, line items,
and totals printed on each image. The sample documents are designed so that, when read
correctly, they drive the outcome stated here. **The policy logic each scenario
demonstrates is deterministic** and has been verified independently of the LLM by running
the equivalent submission through the Orchestrator with the deterministic `MockClient`
(the same harness `app/eval` uses) — all 16 produce the decision shown below. Where a
live result hinges on the LLM reading one specific field, it is flagged with a *Live note*.

> Tip: the **Eval (12 cases)** page runs the 12 graded assignment cases against the
> deterministic engine and is the canonical proof of the decision logic. This page is the
> *interactive* counterpart you can click through with real images.

---

## D1 — Clean Consultation → APPROVED

**Demonstrates:** the happy path — valid member, covered category, correct documents,
within limits; 10% consultation co-pay applied.

* [ ] FieldValueMemberEMP001 — Rajesh KumarCategoryCONSULTATIONTreatment Date2024-11-01Claimed Amount1500Hospital*(leave blank)*Files`prescription_clean.png`, `bill_clean.png`

**Expected:** **APPROVED**, ₹1,350. Message: 10% co-pay (−₹150) applied on ₹1,500.

---

## D2 — Network Hospital → APPROVED with discount

**Demonstrates:** the financial-order rule — network discount is applied **before** co-pay,
and the breakdown is shown. 20% discount on ₹4,500 → ₹3,600, then 10% co-pay → **₹3,240**.

| Field          | Value                                              |
| -------------- | -------------------------------------------------- |
| Member         | EMP010 — Deepak Shah                              |
| Category       | CONSULTATION                                       |
| Treatment Date | 2024-11-03                                         |
| Claimed Amount | 4500                                               |
| Hospital       | `Apollo Hospitals`                               |
| Files          | `prescription_network.png`, `bill_network.png` |

**Expected:** **APPROVED**, ₹3,240. Message states "Network discount 20% (−₹900) applied
first (net ₹3,600), then co-pay 10% (−₹360)."

*Live note:* the Hospital field (`Apollo Hospitals`) is what triggers the network match,
so it must be typed exactly as a `network_hospitals` entry.

---

## D3 — Dental, Cosmetic Line Excluded → PARTIAL

**Demonstrates:** line-item adjudication — root canal (covered) is paid, teeth whitening
(cosmetic, excluded) is rejected, with a per-line reason.

| Field          | Value                     |
| -------------- | ------------------------- |
| Member         | EMP002 — Priya Singh     |
| Category       | DENTAL                    |
| Treatment Date | 2024-10-15                |
| Claimed Amount | 12000                     |
| Hospital       | *(leave blank)*         |
| Files          | `dental_bill_mixed.png` |

**Expected:** **PARTIAL**, ₹8,000. Root Canal approved; Teeth Whitening (₹4,000) rejected
as an excluded cosmetic procedure. (DENTAL needs only a HOSPITAL_BILL.)

---

## D4 — Per-Claim Limit Exceeded → REJECTED

**Demonstrates:** the per-claim limit rule — eligible amount ₹7,500 exceeds the ₹5,000
consultation limit.

| Field          | Value                                               |
| -------------- | --------------------------------------------------- |
| Member         | EMP003 — Amit Verma                                |
| Category       | CONSULTATION                                        |
| Treatment Date | 2024-10-20                                          |
| Claimed Amount | 7500                                                |
| Hospital       | *(leave blank)*                                   |
| Files          | `prescription_gastro.png`, `bill_overlimit.png` |

**Expected:** **REJECTED — PER_CLAIM_EXCEEDED**. Message states the claimed amount ₹7,500
and the ₹5,000 per-claim limit.

---

## D5 — Waiting Period (Diabetes) → REJECTED

**Demonstrates:** the specific-condition waiting period. Vikram Joshi joined 2024-09-01;
diabetes has a 90-day wait, so a 2024-10-15 diabetes claim is inside the window.

| Field          | Value                                                |
| -------------- | ---------------------------------------------------- |
| Member         | EMP005 — Vikram Joshi                               |
| Category       | CONSULTATION                                         |
| Treatment Date | 2024-10-15                                           |
| Claimed Amount | 3000                                                 |
| Hospital       | *(leave blank)*                                    |
| Files          | `prescription_diabetes.png`, `bill_diabetes.png` |

**Expected:** **REJECTED — WAITING_PERIOD**. Message states eligibility from **2024-11-30**.

*Live note:* the diagnosis on the prescription must read as "diabetes" for the waiting
period to match (it does on `prescription_diabetes.png`).

---

## D6 — Excluded Condition (Obesity) → REJECTED

**Demonstrates:** policy-level exclusion. Obesity / weight-loss treatment is explicitly
excluded.

| Field          | Value                                              |
| -------------- | -------------------------------------------------- |
| Member         | EMP009 — Anita Desai                              |
| Category       | CONSULTATION                                       |
| Treatment Date | 2024-10-18                                         |
| Claimed Amount | 8000                                               |
| Hospital       | *(leave blank)*                                  |
| Files          | `prescription_obesity.png`, `bill_obesity.png` |

**Expected:** **REJECTED — EXCLUDED_CONDITION** ("Obesity and weight loss programs" is
excluded). The trace may also note a waiting-period match for obesity treatment — both
point to the same outcome.

---

## D7 — MRI Without Pre-Authorization → REJECTED

**Demonstrates:** the pre-auth rule for high-value diagnostics. An MRI above ₹10,000
requires pre-authorization, which the form cannot supply — so it is correctly missing.

| Field          | Value                                                              |
| -------------- | ------------------------------------------------------------------ |
| Member         | EMP007 — Suresh Patil                                             |
| Category       | DIAGNOSTIC                                                         |
| Treatment Date | 2024-11-02                                                         |
| Claimed Amount | 15000                                                              |
| Hospital       | *(leave blank)*                                                  |
| Files          | `prescription_mri.png`, `lab_report_mri.png`, `bill_mri.png` |

**Expected:** **REJECTED — PRE_AUTH_MISSING**. Message explains pre-auth was required and
tells the member to obtain it and resubmit. (DIAGNOSTIC requires PRESCRIPTION + LAB_REPORT

+ HOSPITAL_BILL — all three uploaded.)

---

## D8 — High-Value Claim → MANUAL_REVIEW

**Demonstrates:** the fraud / auto-manual-review threshold (claims above ₹25,000 route to a
human). No MRI/CT/PET line, so no pre-auth block masks it.

| Field          | Value                                                                                           |
| -------------- | ----------------------------------------------------------------------------------------------- |
| Member         | EMP001 — Rajesh Kumar                                                                          |
| Category       | DIAGNOSTIC                                                                                      |
| Treatment Date | 2024-11-05                                                                                      |
| Claimed Amount | 30000                                                                                           |
| Hospital       | `Manipal Hospitals`                                                                           |
| Files          | `prescription_panel_highvalue.png`, `lab_report_cbc.png`, `bill_diagnostic_highvalue.png` |

**Expected:** **MANUAL_REVIEW** flagged HIGH_VALUE_CLAIM (₹30,000 > ₹25,000 threshold).
Routed to a human rather than auto-decided.

---

## D9 — Wrong / Missing Document → STOPPED

**Demonstrates:** early document-requirement check. A CONSULTATION needs a prescription
**and** a hospital bill; uploading two prescriptions stops the claim before any decision.

| Field          | Value                                                   |
| -------------- | ------------------------------------------------------- |
| Member         | EMP001 — Rajesh Kumar                                  |
| Category       | CONSULTATION                                            |
| Treatment Date | 2024-11-01                                              |
| Claimed Amount | 1500                                                    |
| Hospital       | *(leave blank)*                                       |
| Files          | `prescription_clean.png`, `vision_prescription.png` |

**Expected:** **STOPPED** (no decision). Message names what was uploaded (PRESCRIPTION ×2)
and the missing required document (HOSPITAL_BILL).

*Live note:* both files must be read as prescriptions; both are clearly prescriptions.

---

## D10 — Documents for Different Patients → STOPPED

**Demonstrates:** cross-document patient-consistency. The prescription is for Rajesh Kumar
but the bill is for Arjun Mehta.

| Field          | Value                                                  |
| -------------- | ------------------------------------------------------ |
| Member         | EMP001 — Rajesh Kumar                                 |
| Category       | CONSULTATION                                           |
| Treatment Date | 2024-11-01                                             |
| Claimed Amount | 1500                                                   |
| Hospital       | *(leave blank)*                                      |
| Files          | `prescription_clean.png`, `bill_wrong_patient.png` |

**Expected:** **STOPPED** (no decision). Message surfaces both names — "Rajesh Kumar" vs
"Arjun Mehta" — and asks for matching documents.

*Live note:* depends on the LLM reading the patient name printed on each image (they differ
by design).

---

## D11 — Unreadable Document → STOPPED (re-upload requested)

**Demonstrates:** readability handling — a blurry required document is **not** rejected;
the member is asked to re-upload it.

| Field          | Value                                                    |
| -------------- | -------------------------------------------------------- |
| Member         | EMP004 — Sneha Reddy                                    |
| Category       | PHARMACY                                                 |
| Treatment Date | 2024-10-25                                               |
| Claimed Amount | 800                                                      |
| Hospital       | *(leave blank)*                                        |
| Files          | `prescription_clean.png`, `pharmacy_bill_blurry.png` |

**Expected:** **STOPPED — claim on hold (not rejected)**. Message names the blurry pharmacy
bill and asks for a clear re-upload.

*Live note:* the live LLM must judge `pharmacy_bill_blurry.png` as UNREADABLE; it is
heavily Gaussian-blurred for exactly this purpose.

---

## D12 — Clean Pharmacy → APPROVED

**Demonstrates:** PHARMACY category requirements (PRESCRIPTION + PHARMACY_BILL) and 0%
pharmacy co-pay — full eligible amount approved.

| Field          | Value                                                      |
| -------------- | ---------------------------------------------------------- |
| Member         | EMP004 — Sneha Reddy                                      |
| Category       | PHARMACY                                                   |
| Treatment Date | 2024-10-25                                                 |
| Claimed Amount | 1200                                                       |
| Hospital       | *(leave blank)*                                          |
| Files          | `prescription_pharmacy.png`, `pharmacy_bill_clean.png` |

**Expected:** **APPROVED**, ₹1,200 (no co-pay on pharmacy).

---

## D13 — Clean Diagnostic → APPROVED

**Demonstrates:** DIAGNOSTIC requirements (PRESCRIPTION + LAB_REPORT + HOSPITAL_BILL) and
0% diagnostic co-pay.

| Field          | Value                                                                    |
| -------------- | ------------------------------------------------------------------------ |
| Member         | EMP001 — Rajesh Kumar                                                   |
| Category       | DIAGNOSTIC                                                               |
| Treatment Date | 2024-11-01                                                               |
| Claimed Amount | 1000                                                                     |
| Hospital       | *(leave blank)*                                                        |
| Files          | `prescription_clean.png`, `lab_report_cbc.png`, `lab_bill_cbc.png` |

**Expected:** **APPROVED**, ₹1,000 (no co-pay on diagnostic).

*Live note:* `prescription_clean.png` lists CBC/Dengue investigations, satisfying the
diagnostic prescription requirement.

---

## D14 — Clean Vision → APPROVED

**Demonstrates:** VISION category (PRESCRIPTION + HOSPITAL_BILL), covered items (eye exam +
glasses), 0% co-pay.

| Field          | Value                                            |
| -------------- | ------------------------------------------------ |
| Member         | EMP001 — Rajesh Kumar                           |
| Category       | VISION                                           |
| Treatment Date | 2024-10-15                                       |
| Claimed Amount | 4500                                             |
| Hospital       | *(leave blank)*                                |
| Files          | `vision_prescription.png`, `vision_bill.png` |

**Expected:** **APPROVED**, ₹4,500 (no co-pay on vision; within the ₹5,000 vision sub-limit).

---

## D15 — Vision LASIK Excluded → REJECTED

**Demonstrates:** vision exclusion — LASIK / refractive surgery is not covered, so the only
billed line is rejected and the payable is ₹0.

| Field          | Value                                                 |
| -------------- | ----------------------------------------------------- |
| Member         | EMP006 — Kavita Nair                                 |
| Category       | VISION                                                |
| Treatment Date | 2024-10-20                                            |
| Claimed Amount | 5000                                                  |
| Hospital       | *(leave blank)*                                     |
| Files          | `prescription_lasik.png`, `vision_bill_lasik.png` |

**Expected:** **REJECTED**, ₹0 — LASIK is an excluded refractive procedure; message lists
the non-covered line item.

---

## D16 — Non-Medical Document Uploaded → STOPPED

**Demonstrates:** document-type rejection — a supermarket receipt is not a valid medical
document, so the required HOSPITAL_BILL is still missing and the claim stops.

| Field          | Value                                                 |
| -------------- | ----------------------------------------------------- |
| Member         | EMP001 — Rajesh Kumar                                |
| Category       | CONSULTATION                                          |
| Treatment Date | 2024-11-01                                            |
| Claimed Amount | 1500                                                  |
| Hospital       | *(leave blank)*                                     |
| Files          | `prescription_clean.png`, `unrelated_receipt.png` |

**Expected:** **STOPPED** (no decision). The receipt classifies as a non-medical / UNKNOWN
document; message names the missing HOSPITAL_BILL.

*Live note:* depends on the LLM not mistaking a FreshMart grocery receipt for a hospital
bill.

---

## Coverage summary

| Outcome                 | Scenarios                                                                                        |
| ----------------------- | ------------------------------------------------------------------------------------------------ |
| APPROVED                | D1 (co-pay), D2 (network discount), D12 (pharmacy), D13 (diagnostic), D14 (vision)               |
| PARTIAL                 | D3 (dental cosmetic line)                                                                        |
| REJECTED                | D4 (per-claim limit), D5 (waiting period), D6 (exclusion), D7 (pre-auth), D15 (vision exclusion) |
| MANUAL_REVIEW           | D8 (high value)                                                                                  |
| STOPPED before decision | D9 (wrong/missing doc), D10 (wrong patient), D11 (unreadable), D16 (non-medical doc)             |

Categories exercised: CONSULTATION, DIAGNOSTIC, PHARMACY, DENTAL, VISION.

All 16 outcomes above were confirmed deterministically through the Orchestrator with the
`MockClient` (the eval engine), so they reflect the system's actual policy logic given
correct document extraction.
