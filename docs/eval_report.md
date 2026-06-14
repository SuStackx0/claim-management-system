# Eval Report — 12 Test Cases (Live Vision)

**Result: 12/12 passed**

> **Live vision run.** Each case is rendered to document image(s) (`eval_docs/<case_id>_<file_id>.png`, generated from `test_cases.json` by `scripts/generate_eval_docs.py`) and run through the **real Groq Llama-4 multimodal pipeline** — the LLM classifies each document, extracts its fields, and resolves patient-name equivalence. No structured content is injected; the `source: "vision"` on every extraction below is the evidence. All money and policy logic remains deterministic code reading `policy_terms.json`. Because perception is stochastic, assertions are strict and any mismatch is reported honestly. Runs are paced to respect the provider rate limit.

## TC001 — Wrong Document Uploaded
- Expected: `None` | Produced: `None` | **PASS**
- Member message: For a CONSULTATION claim you must upload: HOSPITAL_BILL, PRESCRIPTION. You uploaded: PRESCRIPTION ('dr_sharma_prescription.jpg'), PRESCRIPTION ('another_prescription.jpg'). Missing: HOSPITAL_BILL. Please upload your hospital bill to proceed.
- Pipeline:
  - `INTAKE` PASS (0ms)
  - `DOC_VERIFICATION` FAIL (852ms)

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-CE4953A1",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-14T06:15:19.795596Z",
  "completed_at": "2026-06-14T06:15:20.649107Z",
  "steps": [
    {
      "step": "INTAKE",
      "agent": "IntakeAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "POLICY_MATCHES",
          "result": "PASS",
          "rule_ref": "policy_id",
          "detail": {
            "policy_id": "PLUM_GHI_2024"
          }
        },
        {
          "check": "MEMBER_EXISTS",
          "result": "PASS",
          "rule_ref": "members",
          "detail": {
            "member_id": "EMP001"
          }
        },
        {
          "check": "CATEGORY_COVERED",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation.covered",
          "detail": {
            "covered": true
          }
        },
        {
          "check": "MINIMUM_AMOUNT",
          "result": "PASS",
          "rule_ref": "submission_rules.minimum_claim_amount",
          "detail": {
            "claimed": 1500,
            "minimum": 500
          }
        },
        {
          "check": "SUBMISSION_DEADLINE",
          "result": "SKIPPED",
          "rule_ref": "submission_rules.deadline_days_from_treatment",
          "detail": {
            "reason": "no submission_date provided; cannot measure days-from-treatment without guessing against the processing clock",
            "treatment_date": "2024-11-01",
            "deadline_days": 30
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "DOC_VERIFICATION",
      "agent": "DocVerifierAgent",
      "status": "FAIL",
      "checks": [],
      "confidence_entries": [],
      "error": {
        "code": "WRONG_DOCUMENT_TYPE",
        "message": "missing required docs: ['HOSPITAL_BILL']",
        "member_message": "For a CONSULTATION claim you must upload: HOSPITAL_BILL, PRESCRIPTION. You uploaded: PRESCRIPTION ('dr_sharma_prescription.jpg'), PRESCRIPTION ('another_prescription.jpg'). Missing: HOSPITAL_BILL. Please upload your hospital bill to proceed.",
        "detail": {
          "required": [
            "HOSPITAL_BILL",
            "PRESCRIPTION"
          ],
          "detected": [
            "PRESCRIPTION"
          ],
          "missing": [
            "HOSPITAL_BILL"
          ]
        }
      },
      "duration_ms": 852
    }
  ],
  "decision": null
}
```
</details>

## TC002 — Unreadable Document
- Expected: `None` | Produced: `None` | **PASS**
- Member message: For a PHARMACY claim you must upload: PHARMACY_BILL, PRESCRIPTION. You uploaded: PRESCRIPTION ('prescription.jpg'), UNKNOWN ('blurry_bill.jpg'). Missing: PHARMACY_BILL. Please upload your pharmacy bill to proceed.
- Pipeline:
  - `INTAKE` PASS (0ms)
  - `DOC_VERIFICATION` FAIL (1126ms)

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-51F12F29",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-14T06:15:48.686438Z",
  "completed_at": "2026-06-14T06:15:49.815047Z",
  "steps": [
    {
      "step": "INTAKE",
      "agent": "IntakeAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "POLICY_MATCHES",
          "result": "PASS",
          "rule_ref": "policy_id",
          "detail": {
            "policy_id": "PLUM_GHI_2024"
          }
        },
        {
          "check": "MEMBER_EXISTS",
          "result": "PASS",
          "rule_ref": "members",
          "detail": {
            "member_id": "EMP004"
          }
        },
        {
          "check": "CATEGORY_COVERED",
          "result": "PASS",
          "rule_ref": "opd_categories.pharmacy.covered",
          "detail": {
            "covered": true
          }
        },
        {
          "check": "MINIMUM_AMOUNT",
          "result": "PASS",
          "rule_ref": "submission_rules.minimum_claim_amount",
          "detail": {
            "claimed": 800,
            "minimum": 500
          }
        },
        {
          "check": "SUBMISSION_DEADLINE",
          "result": "SKIPPED",
          "rule_ref": "submission_rules.deadline_days_from_treatment",
          "detail": {
            "reason": "no submission_date provided; cannot measure days-from-treatment without guessing against the processing clock",
            "treatment_date": "2024-10-25",
            "deadline_days": 30
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "DOC_VERIFICATION",
      "agent": "DocVerifierAgent",
      "status": "FAIL",
      "checks": [],
      "confidence_entries": [],
      "error": {
        "code": "WRONG_DOCUMENT_TYPE",
        "message": "missing required docs: ['PHARMACY_BILL']",
        "member_message": "For a PHARMACY claim you must upload: PHARMACY_BILL, PRESCRIPTION. You uploaded: PRESCRIPTION ('prescription.jpg'), UNKNOWN ('blurry_bill.jpg'). Missing: PHARMACY_BILL. Please upload your pharmacy bill to proceed.",
        "detail": {
          "required": [
            "PHARMACY_BILL",
            "PRESCRIPTION"
          ],
          "detected": [
            "PRESCRIPTION",
            "UNKNOWN"
          ],
          "missing": [
            "PHARMACY_BILL"
          ]
        }
      },
      "duration_ms": 1126
    }
  ],
  "decision": null
}
```
</details>

## TC003 — Documents Belong to Different Patients
- Expected: `None` | Produced: `None` | **PASS**
- Member message: Your documents appear to belong to different people: the prescription is for 'Rajesh Kumar' but the hospital bill is for 'Arjun Mehta'. All documents in one claim must be for the same patient. Please re-upload matching documents.
- Pipeline:
  - `INTAKE` PASS (0ms)
  - `DOC_VERIFICATION` PASS (771ms)  — F005:PRESCRIPTION@0.95, F006:HOSPITAL_BILL@0.95
  - `EXTRACTION` PASS (905ms)  — F005:PRESCRIPTION=vision, F006:HOSPITAL_BILL=vision
  - `CONSISTENCY` FAIL (421ms)

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-C436BEE2",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-14T06:16:15.974348Z",
  "completed_at": "2026-06-14T06:16:18.074092Z",
  "steps": [
    {
      "step": "INTAKE",
      "agent": "IntakeAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "POLICY_MATCHES",
          "result": "PASS",
          "rule_ref": "policy_id",
          "detail": {
            "policy_id": "PLUM_GHI_2024"
          }
        },
        {
          "check": "MEMBER_EXISTS",
          "result": "PASS",
          "rule_ref": "members",
          "detail": {
            "member_id": "EMP001"
          }
        },
        {
          "check": "CATEGORY_COVERED",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation.covered",
          "detail": {
            "covered": true
          }
        },
        {
          "check": "MINIMUM_AMOUNT",
          "result": "PASS",
          "rule_ref": "submission_rules.minimum_claim_amount",
          "detail": {
            "claimed": 1500,
            "minimum": 500
          }
        },
        {
          "check": "SUBMISSION_DEADLINE",
          "result": "SKIPPED",
          "rule_ref": "submission_rules.deadline_days_from_treatment",
          "detail": {
            "reason": "no submission_date provided; cannot measure days-from-treatment without guessing against the processing clock",
            "treatment_date": "2024-11-01",
            "deadline_days": 30
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "DOC_VERIFICATION",
      "agent": "DocVerifierAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F005",
            "file_name": "prescription_rajesh.jpg",
            "detected_type": "PRESCRIPTION",
            "readability": "GOOD",
            "confidence": 0.95
          }
        },
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F006",
            "file_name": "bill_arjun.jpg",
            "detected_type": "HOSPITAL_BILL",
            "readability": "PARTIAL",
            "confidence": 0.95
          }
        },
        {
          "check": "REQUIREMENTS_MET",
          "result": "PASS",
          "rule_ref": "document_requirements.CONSULTATION",
          "detail": {
            "required": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ],
            "detected": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ]
          }
        }
      ],
      "confidence_entries": [
        {
          "factor": 0.9,
          "reason": "bill_arjun.jpg partially readable"
        }
      ],
      "error": null,
      "duration_ms": 771
    },
    {
      "step": "EXTRACTION",
      "agent": "ExtractionAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F005",
            "doc_type": "PRESCRIPTION",
            "source": "vision",
            "unextracted_fields": [
              "diagnosis",
              "medicines",
              "tests_ordered",
              "treatment"
            ]
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F006",
            "doc_type": "HOSPITAL_BILL",
            "source": "vision",
            "unextracted_fields": [
              "line_items",
              "total"
            ]
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 905
    },
    {
      "step": "CONSISTENCY",
      "agent": "ConsistencyAgent",
      "status": "FAIL",
      "checks": [],
      "confidence_entries": [],
      "error": {
        "code": "PATIENT_MISMATCH",
        "message": "patient mismatch: Rajesh Kumar vs Arjun Mehta",
        "member_message": "Your documents appear to belong to different people: the prescription is for 'Rajesh Kumar' but the hospital bill is for 'Arjun Mehta'. All documents in one claim must be for the same patient. Please re-upload matching documents.",
        "detail": {
          "names_found": {
            "F005": "Rajesh Kumar",
            "F006": "Arjun Mehta"
          }
        }
      },
      "duration_ms": 421
    }
  ],
  "decision": null
}
```
</details>

## TC004 — Clean Consultation — Full Approval
- Expected: `APPROVED` | Produced: `APPROVED` | **PASS**
- Approved amount: ₹1350 | Confidence: 1.0
- Member message: Approved amount: ₹1350. A 10% co-pay (−₹150) was applied.
- Pipeline:
  - `INTAKE` PASS (0ms)
  - `DOC_VERIFICATION` PASS (949ms)  — F007:PRESCRIPTION@0.95, F008:HOSPITAL_BILL@0.99
  - `EXTRACTION` PASS (1570ms)  — F007:PRESCRIPTION=vision, F008:HOSPITAL_BILL=vision
  - `CONSISTENCY` PASS (1051ms)
  - `ADJUDICATION` PASS (0ms)
  - `FRAUD_CHECK` PASS (0ms)
  - `AGGREGATION` PASS (0ms)

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-061C0B88",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-14T06:16:45.796983Z",
  "completed_at": "2026-06-14T06:16:49.371097Z",
  "steps": [
    {
      "step": "INTAKE",
      "agent": "IntakeAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "POLICY_MATCHES",
          "result": "PASS",
          "rule_ref": "policy_id",
          "detail": {
            "policy_id": "PLUM_GHI_2024"
          }
        },
        {
          "check": "MEMBER_EXISTS",
          "result": "PASS",
          "rule_ref": "members",
          "detail": {
            "member_id": "EMP001"
          }
        },
        {
          "check": "CATEGORY_COVERED",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation.covered",
          "detail": {
            "covered": true
          }
        },
        {
          "check": "MINIMUM_AMOUNT",
          "result": "PASS",
          "rule_ref": "submission_rules.minimum_claim_amount",
          "detail": {
            "claimed": 1500,
            "minimum": 500
          }
        },
        {
          "check": "SUBMISSION_DEADLINE",
          "result": "SKIPPED",
          "rule_ref": "submission_rules.deadline_days_from_treatment",
          "detail": {
            "reason": "no submission_date provided; cannot measure days-from-treatment without guessing against the processing clock",
            "treatment_date": "2024-11-01",
            "deadline_days": 30
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "DOC_VERIFICATION",
      "agent": "DocVerifierAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F007",
            "file_name": null,
            "detected_type": "PRESCRIPTION",
            "readability": "GOOD",
            "confidence": 0.95
          }
        },
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F008",
            "file_name": null,
            "detected_type": "HOSPITAL_BILL",
            "readability": "GOOD",
            "confidence": 0.99
          }
        },
        {
          "check": "REQUIREMENTS_MET",
          "result": "PASS",
          "rule_ref": "document_requirements.CONSULTATION",
          "detail": {
            "required": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ],
            "detected": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ]
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 949
    },
    {
      "step": "EXTRACTION",
      "agent": "ExtractionAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F007",
            "doc_type": "PRESCRIPTION",
            "source": "vision",
            "unextracted_fields": [
              "tests_ordered",
              "treatment"
            ]
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F008",
            "doc_type": "HOSPITAL_BILL",
            "source": "vision",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 1570
    },
    {
      "step": "CONSISTENCY",
      "agent": "ConsistencyAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "PATIENT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "names": [
              "Rajesh Kumar",
              "Rajesh Kumar"
            ]
          }
        },
        {
          "check": "AMOUNT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "bill_total": 1500
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 1051
    },
    {
      "step": "ADJUDICATION",
      "agent": "AdjudicatorAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "EXCLUSIONS",
          "result": "PASS",
          "rule_ref": "exclusions.conditions",
          "detail": {
            "diagnosis_texts": [
              "Viral Fever"
            ]
          }
        },
        {
          "check": "WAITING_PERIOD",
          "result": "PASS",
          "rule_ref": "waiting_periods",
          "detail": {
            "condition_matched": null
          }
        },
        {
          "check": "PRE_AUTHORIZATION",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation",
          "detail": {
            "reason": "category has no pre-auth rules"
          }
        },
        {
          "check": "ANNUAL_OPD_LIMIT",
          "result": "PASS",
          "rule_ref": "coverage.annual_opd_limit",
          "detail": {
            "ytd": 5000,
            "claimed": 1500,
            "limit": 50000
          }
        },
        {
          "check": "LINE_ITEMS",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "verdicts": [
              {
                "description": "Consultation Fee",
                "amount": 1000,
                "eligible_amount": 1000,
                "verdict": "APPROVED",
                "reason": "covered",
                "rule_ref": null
              },
              {
                "description": "CBC Test",
                "amount": 300,
                "eligible_amount": 300,
                "verdict": "APPROVED",
                "reason": "covered",
                "rule_ref": null
              },
              {
                "description": "Dengue NS1 Test",
                "amount": 200,
                "eligible_amount": 200,
                "verdict": "APPROVED",
                "reason": "covered",
                "rule_ref": null
              }
            ],
            "no_billable_items": false
          }
        },
        {
          "check": "PER_CLAIM_LIMIT",
          "result": "PASS",
          "rule_ref": "coverage.per_claim_limit",
          "detail": {
            "claimed": 1500,
            "limit": 5000
          }
        },
        {
          "check": "FINANCIAL_CALCULATION",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation",
          "detail": {
            "base": 1500,
            "in_network": false,
            "hospital": "City Clinic, Bengaluru",
            "network_discount_percent": 0,
            "network_discount": 0,
            "after_discount": 1500,
            "copay_percent": 10,
            "copay": 150,
            "payable": 1350,
            "order": "network discount applied before co-pay"
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "FRAUD_CHECK",
      "agent": "FraudAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "SAME_DAY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.same_day_claims_limit",
          "detail": {
            "count_today": 1,
            "limit": 2
          }
        },
        {
          "check": "MONTHLY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.monthly_claims_limit",
          "detail": {
            "count_month": 1,
            "limit": 6
          }
        },
        {
          "check": "HIGH_VALUE",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.auto_manual_review_above",
          "detail": {
            "claimed": 1500,
            "threshold": 25000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "AGGREGATION",
      "agent": "Aggregator",
      "status": "PASS",
      "checks": [],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    }
  ],
  "decision": {
    "status": "APPROVED",
    "approved_amount": 1350,
    "reasons": [
      "All checks passed"
    ],
    "confidence": 1.0,
    "member_message": "Approved amount: \u20b91350. A 10% co-pay (\u2212\u20b9150) was applied.",
    "ops_summary": "APPROVED: payable \u20b91350. Lines: Consultation Fee: APPROVED (covered); CBC Test: APPROVED (covered); Dengue NS1 Test: APPROVED (covered). Financial: {'base': 1500, 'in_network': False, 'hospital': 'City Clinic, Bengaluru', 'network_discount_percent': 0, 'network_discount': 0, 'after_discount': 1500, 'copay_percent': 10, 'copay': 150, 'payable': 1350}. "
  }
}
```
</details>

## TC005 — Waiting Period — Diabetes
- Expected: `REJECTED` | Produced: `REJECTED` | **PASS**
- Approved amount: ₹0 | Confidence: 1.0
- Member message: This treatment falls inside a waiting period. You will be eligible for diabetes claims from 2024-11-30.
- Pipeline:
  - `INTAKE` PASS (0ms)
  - `DOC_VERIFICATION` PASS (1066ms)  — F009:PRESCRIPTION@0.9, F010:HOSPITAL_BILL@0.99
  - `EXTRACTION` PASS (948ms)  — F009:PRESCRIPTION=vision, F010:HOSPITAL_BILL=vision
  - `CONSISTENCY` PASS (0ms)
  - `ADJUDICATION` PASS (0ms)
  - `FRAUD_CHECK` PASS (0ms)
  - `AGGREGATION` PASS (0ms)

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-701F07BF",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-14T06:17:15.447776Z",
  "completed_at": "2026-06-14T06:17:17.466169Z",
  "steps": [
    {
      "step": "INTAKE",
      "agent": "IntakeAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "POLICY_MATCHES",
          "result": "PASS",
          "rule_ref": "policy_id",
          "detail": {
            "policy_id": "PLUM_GHI_2024"
          }
        },
        {
          "check": "MEMBER_EXISTS",
          "result": "PASS",
          "rule_ref": "members",
          "detail": {
            "member_id": "EMP005"
          }
        },
        {
          "check": "CATEGORY_COVERED",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation.covered",
          "detail": {
            "covered": true
          }
        },
        {
          "check": "MINIMUM_AMOUNT",
          "result": "PASS",
          "rule_ref": "submission_rules.minimum_claim_amount",
          "detail": {
            "claimed": 3000,
            "minimum": 500
          }
        },
        {
          "check": "SUBMISSION_DEADLINE",
          "result": "SKIPPED",
          "rule_ref": "submission_rules.deadline_days_from_treatment",
          "detail": {
            "reason": "no submission_date provided; cannot measure days-from-treatment without guessing against the processing clock",
            "treatment_date": "2024-10-15",
            "deadline_days": 30
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "DOC_VERIFICATION",
      "agent": "DocVerifierAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F009",
            "file_name": null,
            "detected_type": "PRESCRIPTION",
            "readability": "GOOD",
            "confidence": 0.9
          }
        },
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F010",
            "file_name": null,
            "detected_type": "HOSPITAL_BILL",
            "readability": "GOOD",
            "confidence": 0.99
          }
        },
        {
          "check": "REQUIREMENTS_MET",
          "result": "PASS",
          "rule_ref": "document_requirements.CONSULTATION",
          "detail": {
            "required": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ],
            "detected": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ]
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 1066
    },
    {
      "step": "EXTRACTION",
      "agent": "ExtractionAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F009",
            "doc_type": "PRESCRIPTION",
            "source": "vision",
            "unextracted_fields": [
              "tests_ordered",
              "treatment"
            ]
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F010",
            "doc_type": "HOSPITAL_BILL",
            "source": "vision",
            "unextracted_fields": [
              "line_items"
            ]
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 948
    },
    {
      "step": "CONSISTENCY",
      "agent": "ConsistencyAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "PATIENT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "names": [
              "Vikram Joshi",
              "Vikram Joshi"
            ]
          }
        },
        {
          "check": "AMOUNT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "bill_total": 3000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "ADJUDICATION",
      "agent": "AdjudicatorAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "EXCLUSIONS",
          "result": "PASS",
          "rule_ref": "exclusions.conditions",
          "detail": {
            "diagnosis_texts": [
              "Type 2 Diabetes Mellitus"
            ]
          }
        },
        {
          "check": "WAITING_PERIOD",
          "result": "FAIL",
          "rule_ref": "waiting_periods.specific_conditions.diabetes",
          "detail": {
            "condition_matched": "diabetes",
            "waiting_days": 90,
            "member_join_date": "2024-09-01",
            "eligible_from": "2024-11-30",
            "treatment_date": "2024-10-15"
          }
        },
        {
          "check": "PRE_AUTHORIZATION",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation",
          "detail": {
            "reason": "category has no pre-auth rules"
          }
        },
        {
          "check": "ANNUAL_OPD_LIMIT",
          "result": "PASS",
          "rule_ref": "coverage.annual_opd_limit",
          "detail": {
            "ytd": 0,
            "claimed": 3000,
            "limit": 50000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "FRAUD_CHECK",
      "agent": "FraudAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "SAME_DAY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.same_day_claims_limit",
          "detail": {
            "count_today": 1,
            "limit": 2
          }
        },
        {
          "check": "MONTHLY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.monthly_claims_limit",
          "detail": {
            "count_month": 1,
            "limit": 6
          }
        },
        {
          "check": "HIGH_VALUE",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.auto_manual_review_above",
          "detail": {
            "claimed": 3000,
            "threshold": 25000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "AGGREGATION",
      "agent": "Aggregator",
      "status": "PASS",
      "checks": [],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    }
  ],
  "decision": {
    "status": "REJECTED",
    "approved_amount": 0,
    "reasons": [
      "WAITING_PERIOD"
    ],
    "confidence": 1.0,
    "member_message": "This treatment falls inside a waiting period. You will be eligible for diabetes claims from 2024-11-30.",
    "ops_summary": "Rejected: ['WAITING_PERIOD']. "
  }
}
```
</details>

## TC006 — Dental Partial Approval — Cosmetic Exclusion
- Expected: `PARTIAL` | Produced: `PARTIAL` | **PASS**
- Approved amount: ₹8000 | Confidence: 1.0
- Member message: Approved amount: ₹8000. Not covered: Teeth Whitening (₹4000) — 'Teeth Whitening' matches excluded procedure 'Teeth Whitening' — not covered
- Pipeline:
  - `INTAKE` PASS (0ms)
  - `DOC_VERIFICATION` PASS (409ms)  — F011:HOSPITAL_BILL@0.9
  - `EXTRACTION` PASS (645ms)  — F011:HOSPITAL_BILL=vision
  - `CONSISTENCY` PASS (0ms)
  - `ADJUDICATION` PASS (0ms)
  - `FRAUD_CHECK` PASS (0ms)
  - `AGGREGATION` PASS (0ms)

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-B3CD7BD0",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-14T06:17:42.629991Z",
  "completed_at": "2026-06-14T06:17:43.687672Z",
  "steps": [
    {
      "step": "INTAKE",
      "agent": "IntakeAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "POLICY_MATCHES",
          "result": "PASS",
          "rule_ref": "policy_id",
          "detail": {
            "policy_id": "PLUM_GHI_2024"
          }
        },
        {
          "check": "MEMBER_EXISTS",
          "result": "PASS",
          "rule_ref": "members",
          "detail": {
            "member_id": "EMP002"
          }
        },
        {
          "check": "CATEGORY_COVERED",
          "result": "PASS",
          "rule_ref": "opd_categories.dental.covered",
          "detail": {
            "covered": true
          }
        },
        {
          "check": "MINIMUM_AMOUNT",
          "result": "PASS",
          "rule_ref": "submission_rules.minimum_claim_amount",
          "detail": {
            "claimed": 12000,
            "minimum": 500
          }
        },
        {
          "check": "SUBMISSION_DEADLINE",
          "result": "SKIPPED",
          "rule_ref": "submission_rules.deadline_days_from_treatment",
          "detail": {
            "reason": "no submission_date provided; cannot measure days-from-treatment without guessing against the processing clock",
            "treatment_date": "2024-10-15",
            "deadline_days": 30
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "DOC_VERIFICATION",
      "agent": "DocVerifierAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F011",
            "file_name": null,
            "detected_type": "HOSPITAL_BILL",
            "readability": "GOOD",
            "confidence": 0.9
          }
        },
        {
          "check": "REQUIREMENTS_MET",
          "result": "PASS",
          "rule_ref": "document_requirements.DENTAL",
          "detail": {
            "required": [
              "HOSPITAL_BILL"
            ],
            "detected": [
              "HOSPITAL_BILL"
            ]
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 409
    },
    {
      "step": "EXTRACTION",
      "agent": "ExtractionAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F011",
            "doc_type": "HOSPITAL_BILL",
            "source": "vision",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 645
    },
    {
      "step": "CONSISTENCY",
      "agent": "ConsistencyAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "PATIENT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "names": [
              "Priya Singh"
            ]
          }
        },
        {
          "check": "AMOUNT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "bill_total": 12000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "ADJUDICATION",
      "agent": "AdjudicatorAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "EXCLUSIONS",
          "result": "PASS",
          "rule_ref": "exclusions.conditions",
          "detail": {
            "diagnosis_texts": []
          }
        },
        {
          "check": "WAITING_PERIOD",
          "result": "PASS",
          "rule_ref": "waiting_periods",
          "detail": {
            "condition_matched": null
          }
        },
        {
          "check": "PRE_AUTHORIZATION",
          "result": "PASS",
          "rule_ref": "opd_categories.dental",
          "detail": {
            "reason": "category has no pre-auth rules"
          }
        },
        {
          "check": "ANNUAL_OPD_LIMIT",
          "result": "PASS",
          "rule_ref": "coverage.annual_opd_limit",
          "detail": {
            "ytd": 0,
            "claimed": 12000,
            "limit": 50000
          }
        },
        {
          "check": "LINE_ITEMS",
          "result": "WARN",
          "rule_ref": null,
          "detail": {
            "verdicts": [
              {
                "description": "Root Canal Treatment",
                "amount": 8000,
                "eligible_amount": 8000,
                "verdict": "APPROVED",
                "reason": "covered",
                "rule_ref": null
              },
              {
                "description": "Teeth Whitening",
                "amount": 4000,
                "eligible_amount": 0,
                "verdict": "REJECTED",
                "reason": "'Teeth Whitening' matches excluded procedure 'Teeth Whitening' \u2014 not covered",
                "rule_ref": "opd_categories.dental.excluded_procedures"
              }
            ],
            "no_billable_items": false
          }
        },
        {
          "check": "PER_CLAIM_LIMIT",
          "result": "PASS",
          "rule_ref": "opd_categories.dental.sub_limit",
          "detail": {
            "claimed": 8000,
            "limit": 10000
          }
        },
        {
          "check": "FINANCIAL_CALCULATION",
          "result": "PASS",
          "rule_ref": "opd_categories.dental",
          "detail": {
            "base": 8000,
            "in_network": false,
            "hospital": "Smile Dental Clinic",
            "network_discount_percent": 0,
            "network_discount": 0,
            "after_discount": 8000,
            "copay_percent": 0,
            "copay": 0,
            "payable": 8000,
            "order": "network discount applied before co-pay"
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "FRAUD_CHECK",
      "agent": "FraudAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "SAME_DAY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.same_day_claims_limit",
          "detail": {
            "count_today": 1,
            "limit": 2
          }
        },
        {
          "check": "MONTHLY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.monthly_claims_limit",
          "detail": {
            "count_month": 1,
            "limit": 6
          }
        },
        {
          "check": "HIGH_VALUE",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.auto_manual_review_above",
          "detail": {
            "claimed": 12000,
            "threshold": 25000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "AGGREGATION",
      "agent": "Aggregator",
      "status": "PASS",
      "checks": [],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    }
  ],
  "decision": {
    "status": "PARTIAL",
    "approved_amount": 8000,
    "reasons": [
      "'Teeth Whitening' matches excluded procedure 'Teeth Whitening' \u2014 not covered"
    ],
    "confidence": 1.0,
    "member_message": "Approved amount: \u20b98000. Not covered: Teeth Whitening (\u20b94000) \u2014 'Teeth Whitening' matches excluded procedure 'Teeth Whitening' \u2014 not covered",
    "ops_summary": "PARTIAL: payable \u20b98000. Lines: Root Canal Treatment: APPROVED (covered); Teeth Whitening: REJECTED ('Teeth Whitening' matches excluded procedure 'Teeth Whitening' \u2014 not covered). Financial: {'base': 8000, 'in_network': False, 'hospital': 'Smile Dental Clinic', 'network_discount_percent': 0, 'network_discount': 0, 'after_discount': 8000, 'copay_percent': 0, 'copay': 0, 'payable': 8000}. "
  }
}
```
</details>

## TC007 — MRI Without Pre-Authorization
- Expected: `REJECTED` | Produced: `REJECTED` | **PASS**
- Approved amount: ₹0 | Confidence: 1.0
- Member message: MRI above ₹10000 requires pre-authorization, which was not obtained. Please get pre-authorization from your insurer and resubmit the claim with the pre-authorization ID.
- Pipeline:
  - `INTAKE` PASS (0ms)
  - `DOC_VERIFICATION` PASS (1376ms)  — F012:PRESCRIPTION@0.95, F013:LAB_REPORT@0.95, F014:HOSPITAL_BILL@0.99
  - `EXTRACTION` PASS (1825ms)  — F012:PRESCRIPTION=vision, F013:LAB_REPORT=vision, F014:HOSPITAL_BILL=vision
  - `CONSISTENCY` PASS (0ms)
  - `ADJUDICATION` PASS (0ms)
  - `FRAUD_CHECK` PASS (0ms)
  - `AGGREGATION` PASS (0ms)

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-797F6F29",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-14T06:22:31.794236Z",
  "completed_at": "2026-06-14T06:22:34.997828Z",
  "steps": [
    {
      "step": "INTAKE",
      "agent": "IntakeAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "POLICY_MATCHES",
          "result": "PASS",
          "rule_ref": "policy_id",
          "detail": {
            "policy_id": "PLUM_GHI_2024"
          }
        },
        {
          "check": "MEMBER_EXISTS",
          "result": "PASS",
          "rule_ref": "members",
          "detail": {
            "member_id": "EMP007"
          }
        },
        {
          "check": "CATEGORY_COVERED",
          "result": "PASS",
          "rule_ref": "opd_categories.diagnostic.covered",
          "detail": {
            "covered": true
          }
        },
        {
          "check": "MINIMUM_AMOUNT",
          "result": "PASS",
          "rule_ref": "submission_rules.minimum_claim_amount",
          "detail": {
            "claimed": 15000,
            "minimum": 500
          }
        },
        {
          "check": "SUBMISSION_DEADLINE",
          "result": "SKIPPED",
          "rule_ref": "submission_rules.deadline_days_from_treatment",
          "detail": {
            "reason": "no submission_date provided; cannot measure days-from-treatment without guessing against the processing clock",
            "treatment_date": "2024-11-02",
            "deadline_days": 30
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "DOC_VERIFICATION",
      "agent": "DocVerifierAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F012",
            "file_name": null,
            "detected_type": "PRESCRIPTION",
            "readability": "GOOD",
            "confidence": 0.95
          }
        },
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F013",
            "file_name": null,
            "detected_type": "LAB_REPORT",
            "readability": "GOOD",
            "confidence": 0.95
          }
        },
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F014",
            "file_name": null,
            "detected_type": "HOSPITAL_BILL",
            "readability": "GOOD",
            "confidence": 0.99
          }
        },
        {
          "check": "REQUIREMENTS_MET",
          "result": "PASS",
          "rule_ref": "document_requirements.DIAGNOSTIC",
          "detail": {
            "required": [
              "HOSPITAL_BILL",
              "LAB_REPORT",
              "PRESCRIPTION"
            ],
            "detected": [
              "HOSPITAL_BILL",
              "LAB_REPORT",
              "PRESCRIPTION"
            ]
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 1376
    },
    {
      "step": "EXTRACTION",
      "agent": "ExtractionAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F012",
            "doc_type": "PRESCRIPTION",
            "source": "vision",
            "unextracted_fields": [
              "medicines",
              "treatment"
            ]
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F013",
            "doc_type": "LAB_REPORT",
            "source": "vision",
            "unextracted_fields": []
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F014",
            "doc_type": "HOSPITAL_BILL",
            "source": "vision",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 1825
    },
    {
      "step": "CONSISTENCY",
      "agent": "ConsistencyAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "PATIENT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "names": [
              "Suresh Patil",
              "Suresh Patil",
              "Suresh Patil"
            ]
          }
        },
        {
          "check": "AMOUNT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "bill_total": 15000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "ADJUDICATION",
      "agent": "AdjudicatorAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "EXCLUSIONS",
          "result": "PASS",
          "rule_ref": "exclusions.conditions",
          "detail": {
            "diagnosis_texts": [
              "Suspected Lumbar Disc Herniation"
            ]
          }
        },
        {
          "check": "WAITING_PERIOD",
          "result": "PASS",
          "rule_ref": "waiting_periods",
          "detail": {
            "condition_matched": null
          }
        },
        {
          "check": "PRE_AUTHORIZATION",
          "result": "FAIL",
          "rule_ref": "opd_categories.diagnostic.high_value_tests_requiring_pre_auth",
          "detail": {
            "test": "MRI",
            "amount": 15000,
            "threshold": 10000,
            "names_seen": [
              "MRI Lumbar Spine"
            ]
          }
        },
        {
          "check": "ANNUAL_OPD_LIMIT",
          "result": "PASS",
          "rule_ref": "coverage.annual_opd_limit",
          "detail": {
            "ytd": 0,
            "claimed": 15000,
            "limit": 50000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "FRAUD_CHECK",
      "agent": "FraudAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "SAME_DAY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.same_day_claims_limit",
          "detail": {
            "count_today": 1,
            "limit": 2
          }
        },
        {
          "check": "MONTHLY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.monthly_claims_limit",
          "detail": {
            "count_month": 1,
            "limit": 6
          }
        },
        {
          "check": "HIGH_VALUE",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.auto_manual_review_above",
          "detail": {
            "claimed": 15000,
            "threshold": 25000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "AGGREGATION",
      "agent": "Aggregator",
      "status": "PASS",
      "checks": [],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    }
  ],
  "decision": {
    "status": "REJECTED",
    "approved_amount": 0,
    "reasons": [
      "PRE_AUTH_MISSING"
    ],
    "confidence": 1.0,
    "member_message": "MRI above \u20b910000 requires pre-authorization, which was not obtained. Please get pre-authorization from your insurer and resubmit the claim with the pre-authorization ID.",
    "ops_summary": "Rejected: ['PRE_AUTH_MISSING']. "
  }
}
```
</details>

## TC008 — Per-Claim Limit Exceeded
- Expected: `REJECTED` | Produced: `REJECTED` | **PASS**
- Approved amount: ₹0 | Confidence: 1.0
- Member message: Your claimed amount ₹7500 exceeds the per-claim limit of ₹5000.
- Pipeline:
  - `INTAKE` PASS (0ms)
  - `DOC_VERIFICATION` PASS (1181ms)  — F015:PRESCRIPTION@0.95, F016:HOSPITAL_BILL@0.99
  - `EXTRACTION` PASS (6651ms)  — F015:PRESCRIPTION=vision, F016:HOSPITAL_BILL=vision
  - `CONSISTENCY` PASS (0ms)
  - `ADJUDICATION` PASS (0ms)
  - `FRAUD_CHECK` PASS (0ms)
  - `AGGREGATION` PASS (0ms)

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-85770C12",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-14T06:23:02.304038Z",
  "completed_at": "2026-06-14T06:23:10.140207Z",
  "steps": [
    {
      "step": "INTAKE",
      "agent": "IntakeAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "POLICY_MATCHES",
          "result": "PASS",
          "rule_ref": "policy_id",
          "detail": {
            "policy_id": "PLUM_GHI_2024"
          }
        },
        {
          "check": "MEMBER_EXISTS",
          "result": "PASS",
          "rule_ref": "members",
          "detail": {
            "member_id": "EMP003"
          }
        },
        {
          "check": "CATEGORY_COVERED",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation.covered",
          "detail": {
            "covered": true
          }
        },
        {
          "check": "MINIMUM_AMOUNT",
          "result": "PASS",
          "rule_ref": "submission_rules.minimum_claim_amount",
          "detail": {
            "claimed": 7500,
            "minimum": 500
          }
        },
        {
          "check": "SUBMISSION_DEADLINE",
          "result": "SKIPPED",
          "rule_ref": "submission_rules.deadline_days_from_treatment",
          "detail": {
            "reason": "no submission_date provided; cannot measure days-from-treatment without guessing against the processing clock",
            "treatment_date": "2024-10-20",
            "deadline_days": 30
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "DOC_VERIFICATION",
      "agent": "DocVerifierAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F015",
            "file_name": null,
            "detected_type": "PRESCRIPTION",
            "readability": "GOOD",
            "confidence": 0.95
          }
        },
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F016",
            "file_name": null,
            "detected_type": "HOSPITAL_BILL",
            "readability": "GOOD",
            "confidence": 0.99
          }
        },
        {
          "check": "REQUIREMENTS_MET",
          "result": "PASS",
          "rule_ref": "document_requirements.CONSULTATION",
          "detail": {
            "required": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ],
            "detected": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ]
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 1181
    },
    {
      "step": "EXTRACTION",
      "agent": "ExtractionAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F015",
            "doc_type": "PRESCRIPTION",
            "source": "vision",
            "unextracted_fields": [
              "tests_ordered",
              "treatment"
            ]
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F016",
            "doc_type": "HOSPITAL_BILL",
            "source": "vision",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 6651
    },
    {
      "step": "CONSISTENCY",
      "agent": "ConsistencyAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "PATIENT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "names": [
              "Amit Verma",
              "Amit Verma"
            ]
          }
        },
        {
          "check": "AMOUNT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "bill_total": 7500
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "ADJUDICATION",
      "agent": "AdjudicatorAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "EXCLUSIONS",
          "result": "PASS",
          "rule_ref": "exclusions.conditions",
          "detail": {
            "diagnosis_texts": [
              "Gastroenteritis"
            ]
          }
        },
        {
          "check": "WAITING_PERIOD",
          "result": "PASS",
          "rule_ref": "waiting_periods",
          "detail": {
            "condition_matched": null
          }
        },
        {
          "check": "PRE_AUTHORIZATION",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation",
          "detail": {
            "reason": "category has no pre-auth rules"
          }
        },
        {
          "check": "ANNUAL_OPD_LIMIT",
          "result": "PASS",
          "rule_ref": "coverage.annual_opd_limit",
          "detail": {
            "ytd": 10000,
            "claimed": 7500,
            "limit": 50000
          }
        },
        {
          "check": "LINE_ITEMS",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "verdicts": [
              {
                "description": "Consultation Fee",
                "amount": 2000,
                "eligible_amount": 2000,
                "verdict": "APPROVED",
                "reason": "covered",
                "rule_ref": null
              },
              {
                "description": "Medicines",
                "amount": 5500,
                "eligible_amount": 5500,
                "verdict": "APPROVED",
                "reason": "covered",
                "rule_ref": null
              }
            ],
            "no_billable_items": false
          }
        },
        {
          "check": "PER_CLAIM_LIMIT",
          "result": "FAIL",
          "rule_ref": "coverage.per_claim_limit",
          "detail": {
            "claimed": 7500,
            "limit": 5000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "FRAUD_CHECK",
      "agent": "FraudAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "SAME_DAY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.same_day_claims_limit",
          "detail": {
            "count_today": 1,
            "limit": 2
          }
        },
        {
          "check": "MONTHLY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.monthly_claims_limit",
          "detail": {
            "count_month": 1,
            "limit": 6
          }
        },
        {
          "check": "HIGH_VALUE",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.auto_manual_review_above",
          "detail": {
            "claimed": 7500,
            "threshold": 25000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "AGGREGATION",
      "agent": "Aggregator",
      "status": "PASS",
      "checks": [],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    }
  ],
  "decision": {
    "status": "REJECTED",
    "approved_amount": 0,
    "reasons": [
      "PER_CLAIM_EXCEEDED"
    ],
    "confidence": 1.0,
    "member_message": "Your claimed amount \u20b97500 exceeds the per-claim limit of \u20b95000.",
    "ops_summary": "Rejected: ['PER_CLAIM_EXCEEDED']. "
  }
}
```
</details>

## TC009 — Fraud Signal — Multiple Same-Day Claims
- Expected: `MANUAL_REVIEW` | Produced: `MANUAL_REVIEW` | **PASS**
- Approved amount: ₹0 | Confidence: 1.0
- Member message: Your claim needs a quick manual check by our team before we can process it. No action is needed from you right now.
- Pipeline:
  - `INTAKE` PASS (0ms)
  - `DOC_VERIFICATION` PASS (944ms)  — F017:PRESCRIPTION@0.9, F018:HOSPITAL_BILL@0.99
  - `EXTRACTION` PASS (7289ms)  — F017:PRESCRIPTION=vision, F018:HOSPITAL_BILL=vision
  - `CONSISTENCY` PASS (0ms)
  - `ADJUDICATION` PASS (0ms)
  - `FRAUD_CHECK` PASS (1ms)
  - `AGGREGATION` PASS (0ms)

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-660AAA50",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-14T06:23:38.068327Z",
  "completed_at": "2026-06-14T06:23:46.307287Z",
  "steps": [
    {
      "step": "INTAKE",
      "agent": "IntakeAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "POLICY_MATCHES",
          "result": "PASS",
          "rule_ref": "policy_id",
          "detail": {
            "policy_id": "PLUM_GHI_2024"
          }
        },
        {
          "check": "MEMBER_EXISTS",
          "result": "PASS",
          "rule_ref": "members",
          "detail": {
            "member_id": "EMP008"
          }
        },
        {
          "check": "CATEGORY_COVERED",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation.covered",
          "detail": {
            "covered": true
          }
        },
        {
          "check": "MINIMUM_AMOUNT",
          "result": "PASS",
          "rule_ref": "submission_rules.minimum_claim_amount",
          "detail": {
            "claimed": 4800,
            "minimum": 500
          }
        },
        {
          "check": "SUBMISSION_DEADLINE",
          "result": "SKIPPED",
          "rule_ref": "submission_rules.deadline_days_from_treatment",
          "detail": {
            "reason": "no submission_date provided; cannot measure days-from-treatment without guessing against the processing clock",
            "treatment_date": "2024-10-30",
            "deadline_days": 30
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "DOC_VERIFICATION",
      "agent": "DocVerifierAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F017",
            "file_name": null,
            "detected_type": "PRESCRIPTION",
            "readability": "GOOD",
            "confidence": 0.9
          }
        },
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F018",
            "file_name": null,
            "detected_type": "HOSPITAL_BILL",
            "readability": "GOOD",
            "confidence": 0.99
          }
        },
        {
          "check": "REQUIREMENTS_MET",
          "result": "PASS",
          "rule_ref": "document_requirements.CONSULTATION",
          "detail": {
            "required": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ],
            "detected": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ]
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 944
    },
    {
      "step": "EXTRACTION",
      "agent": "ExtractionAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F017",
            "doc_type": "PRESCRIPTION",
            "source": "vision",
            "unextracted_fields": [
              "medicines",
              "tests_ordered",
              "treatment"
            ]
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F018",
            "doc_type": "HOSPITAL_BILL",
            "source": "vision",
            "unextracted_fields": [
              "line_items"
            ]
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 7289
    },
    {
      "step": "CONSISTENCY",
      "agent": "ConsistencyAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "PATIENT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "names": [
              "Ravi Menon",
              "Ravi Menon"
            ]
          }
        },
        {
          "check": "AMOUNT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "bill_total": 4800
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "ADJUDICATION",
      "agent": "AdjudicatorAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "EXCLUSIONS",
          "result": "PASS",
          "rule_ref": "exclusions.conditions",
          "detail": {
            "diagnosis_texts": [
              "Migraine"
            ]
          }
        },
        {
          "check": "WAITING_PERIOD",
          "result": "PASS",
          "rule_ref": "waiting_periods",
          "detail": {
            "condition_matched": null
          }
        },
        {
          "check": "PRE_AUTHORIZATION",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation",
          "detail": {
            "reason": "category has no pre-auth rules"
          }
        },
        {
          "check": "ANNUAL_OPD_LIMIT",
          "result": "PASS",
          "rule_ref": "coverage.annual_opd_limit",
          "detail": {
            "ytd": 0,
            "claimed": 4800,
            "limit": 50000
          }
        },
        {
          "check": "LINE_ITEMS",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "verdicts": [
              {
                "description": "Consultation",
                "amount": 4800,
                "eligible_amount": 2000,
                "verdict": "CAPPED",
                "reason": "consultation fee capped at category sub-limit \u20b92000",
                "rule_ref": "opd_categories.consultation.sub_limit"
              }
            ],
            "no_billable_items": false
          }
        },
        {
          "check": "PER_CLAIM_LIMIT",
          "result": "PASS",
          "rule_ref": "coverage.per_claim_limit",
          "detail": {
            "claimed": 2000,
            "limit": 5000
          }
        },
        {
          "check": "FINANCIAL_CALCULATION",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation",
          "detail": {
            "base": 2000,
            "in_network": false,
            "hospital": "City Hospital",
            "network_discount_percent": 0,
            "network_discount": 0,
            "after_discount": 2000,
            "copay_percent": 10,
            "copay": 200,
            "payable": 1800,
            "order": "network discount applied before co-pay"
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "FRAUD_CHECK",
      "agent": "FraudAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "SAME_DAY_CLAIMS",
          "result": "FAIL",
          "rule_ref": "fraud_thresholds.same_day_claims_limit",
          "detail": {
            "count_today": 4,
            "limit": 2
          }
        },
        {
          "check": "MONTHLY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.monthly_claims_limit",
          "detail": {
            "count_month": 4,
            "limit": 6
          }
        },
        {
          "check": "HIGH_VALUE",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.auto_manual_review_above",
          "detail": {
            "claimed": 4800,
            "threshold": 25000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 1
    },
    {
      "step": "AGGREGATION",
      "agent": "Aggregator",
      "status": "PASS",
      "checks": [],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    }
  ],
  "decision": {
    "status": "MANUAL_REVIEW",
    "approved_amount": 0,
    "reasons": [
      "SAME_DAY_CLAIMS: {'count_today': 4, 'limit': 2, 'prior_claims': [{'claim_id': 'CLM_0081', 'date': '2024-10-30', 'amount': 1200, 'provider': 'City Clinic A'}, {'claim_id': 'CLM_0082', 'date': '2024-10-30', 'amount': 1800, 'provider': 'City Clinic B'}, {'claim_id': 'CLM_0083', 'date': '2024-10-30', 'amount': 2100, 'provider': 'Wellness Center'}]}"
    ],
    "confidence": 1.0,
    "member_message": "Your claim needs a quick manual check by our team before we can process it. No action is needed from you right now.",
    "ops_summary": "Routed to manual review. Signals: SAME_DAY_CLAIMS: {'count_today': 4, 'limit': 2, 'prior_claims': [{'claim_id': 'CLM_0081', 'date': '2024-10-30', 'amount': 1200, 'provider': 'City Clinic A'}, {'claim_id': 'CLM_0082', 'date': '2024-10-30', 'amount': 1800, 'provider': 'City Clinic B'}, {'claim_id': 'CLM_0083', 'date': '2024-10-30', 'amount': 2100, 'provider': 'Wellness Center'}]}"
  }
}
```
</details>

## TC010 — Network Hospital — Discount Applied
- Expected: `APPROVED` | Produced: `APPROVED` | **PASS**
- Approved amount: ₹3240 | Confidence: 1.0
- Member message: Approved amount: ₹3240. Network discount 20% (−₹900) applied first (net ₹3600), then co-pay 10% (−₹360).
- Pipeline:
  - `INTAKE` PASS (0ms)
  - `DOC_VERIFICATION` PASS (827ms)  — F019:PRESCRIPTION@0.9, F020:HOSPITAL_BILL@0.99
  - `EXTRACTION` PASS (7761ms)  — F019:PRESCRIPTION=vision, F020:HOSPITAL_BILL=vision
  - `CONSISTENCY` PASS (0ms)
  - `ADJUDICATION` PASS (0ms)
  - `FRAUD_CHECK` PASS (0ms)
  - `AGGREGATION` PASS (0ms)

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-7D4864DD",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-14T06:24:13.634607Z",
  "completed_at": "2026-06-14T06:24:22.228198Z",
  "steps": [
    {
      "step": "INTAKE",
      "agent": "IntakeAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "POLICY_MATCHES",
          "result": "PASS",
          "rule_ref": "policy_id",
          "detail": {
            "policy_id": "PLUM_GHI_2024"
          }
        },
        {
          "check": "MEMBER_EXISTS",
          "result": "PASS",
          "rule_ref": "members",
          "detail": {
            "member_id": "EMP010"
          }
        },
        {
          "check": "CATEGORY_COVERED",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation.covered",
          "detail": {
            "covered": true
          }
        },
        {
          "check": "MINIMUM_AMOUNT",
          "result": "PASS",
          "rule_ref": "submission_rules.minimum_claim_amount",
          "detail": {
            "claimed": 4500,
            "minimum": 500
          }
        },
        {
          "check": "SUBMISSION_DEADLINE",
          "result": "SKIPPED",
          "rule_ref": "submission_rules.deadline_days_from_treatment",
          "detail": {
            "reason": "no submission_date provided; cannot measure days-from-treatment without guessing against the processing clock",
            "treatment_date": "2024-11-03",
            "deadline_days": 30
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "DOC_VERIFICATION",
      "agent": "DocVerifierAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F019",
            "file_name": null,
            "detected_type": "PRESCRIPTION",
            "readability": "GOOD",
            "confidence": 0.9
          }
        },
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F020",
            "file_name": null,
            "detected_type": "HOSPITAL_BILL",
            "readability": "GOOD",
            "confidence": 0.99
          }
        },
        {
          "check": "REQUIREMENTS_MET",
          "result": "PASS",
          "rule_ref": "document_requirements.CONSULTATION",
          "detail": {
            "required": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ],
            "detected": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ]
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 827
    },
    {
      "step": "EXTRACTION",
      "agent": "ExtractionAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F019",
            "doc_type": "PRESCRIPTION",
            "source": "vision",
            "unextracted_fields": [
              "tests_ordered",
              "treatment"
            ]
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F020",
            "doc_type": "HOSPITAL_BILL",
            "source": "vision",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 7761
    },
    {
      "step": "CONSISTENCY",
      "agent": "ConsistencyAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "PATIENT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "names": [
              "Deepak Shah",
              "Deepak Shah"
            ]
          }
        },
        {
          "check": "AMOUNT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "bill_total": 4500
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "ADJUDICATION",
      "agent": "AdjudicatorAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "EXCLUSIONS",
          "result": "PASS",
          "rule_ref": "exclusions.conditions",
          "detail": {
            "diagnosis_texts": [
              "Acute Bronchitis"
            ]
          }
        },
        {
          "check": "WAITING_PERIOD",
          "result": "PASS",
          "rule_ref": "waiting_periods",
          "detail": {
            "condition_matched": null
          }
        },
        {
          "check": "PRE_AUTHORIZATION",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation",
          "detail": {
            "reason": "category has no pre-auth rules"
          }
        },
        {
          "check": "ANNUAL_OPD_LIMIT",
          "result": "PASS",
          "rule_ref": "coverage.annual_opd_limit",
          "detail": {
            "ytd": 8000,
            "claimed": 4500,
            "limit": 50000
          }
        },
        {
          "check": "LINE_ITEMS",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "verdicts": [
              {
                "description": "Consultation Fee",
                "amount": 1500,
                "eligible_amount": 1500,
                "verdict": "APPROVED",
                "reason": "covered",
                "rule_ref": null
              },
              {
                "description": "Medicines",
                "amount": 3000,
                "eligible_amount": 3000,
                "verdict": "APPROVED",
                "reason": "covered",
                "rule_ref": null
              }
            ],
            "no_billable_items": false
          }
        },
        {
          "check": "PER_CLAIM_LIMIT",
          "result": "PASS",
          "rule_ref": "coverage.per_claim_limit",
          "detail": {
            "claimed": 4500,
            "limit": 5000
          }
        },
        {
          "check": "FINANCIAL_CALCULATION",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation",
          "detail": {
            "base": 4500,
            "in_network": true,
            "hospital": "Apollo Hospitals",
            "network_discount_percent": 20,
            "network_discount": 900,
            "after_discount": 3600,
            "copay_percent": 10,
            "copay": 360,
            "payable": 3240,
            "order": "network discount applied before co-pay"
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "FRAUD_CHECK",
      "agent": "FraudAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "SAME_DAY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.same_day_claims_limit",
          "detail": {
            "count_today": 1,
            "limit": 2
          }
        },
        {
          "check": "MONTHLY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.monthly_claims_limit",
          "detail": {
            "count_month": 1,
            "limit": 6
          }
        },
        {
          "check": "HIGH_VALUE",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.auto_manual_review_above",
          "detail": {
            "claimed": 4500,
            "threshold": 25000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "AGGREGATION",
      "agent": "Aggregator",
      "status": "PASS",
      "checks": [],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    }
  ],
  "decision": {
    "status": "APPROVED",
    "approved_amount": 3240,
    "reasons": [
      "All checks passed"
    ],
    "confidence": 1.0,
    "member_message": "Approved amount: \u20b93240. Network discount 20% (\u2212\u20b9900) applied first (net \u20b93600), then co-pay 10% (\u2212\u20b9360).",
    "ops_summary": "APPROVED: payable \u20b93240. Lines: Consultation Fee: APPROVED (covered); Medicines: APPROVED (covered). Financial: {'base': 4500, 'in_network': True, 'hospital': 'Apollo Hospitals', 'network_discount_percent': 20, 'network_discount': 900, 'after_discount': 3600, 'copay_percent': 10, 'copay': 360, 'payable': 3240}. "
  }
}
```
</details>

## TC011 — Component Failure — Graceful Degradation
- Expected: `APPROVED` | Produced: `APPROVED` | **PASS**
- Approved amount: ₹4000 | Confidence: 0.7
- Member message: Approved amount: ₹4000.
- Pipeline:
  - `INTAKE` PASS (0ms)
  - `DOC_VERIFICATION` PASS (781ms)  — F021:PRESCRIPTION@0.9, F022:HOSPITAL_BILL@0.99
  - `EXTRACTION` PASS (45903ms)  — F021:PRESCRIPTION=vision, F022:HOSPITAL_BILL=vision
  - `CONSISTENCY` PASS (0ms)
  - `ADJUDICATION` PASS (1ms)
  - `FRAUD_CHECK` SKIPPED (0ms)
  - `AGGREGATION` PASS (0ms)

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-85AEF4BE",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-14T06:24:50.472793Z",
  "completed_at": "2026-06-14T06:25:37.162757Z",
  "steps": [
    {
      "step": "INTAKE",
      "agent": "IntakeAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "POLICY_MATCHES",
          "result": "PASS",
          "rule_ref": "policy_id",
          "detail": {
            "policy_id": "PLUM_GHI_2024"
          }
        },
        {
          "check": "MEMBER_EXISTS",
          "result": "PASS",
          "rule_ref": "members",
          "detail": {
            "member_id": "EMP006"
          }
        },
        {
          "check": "CATEGORY_COVERED",
          "result": "PASS",
          "rule_ref": "opd_categories.alternative_medicine.covered",
          "detail": {
            "covered": true
          }
        },
        {
          "check": "MINIMUM_AMOUNT",
          "result": "PASS",
          "rule_ref": "submission_rules.minimum_claim_amount",
          "detail": {
            "claimed": 4000,
            "minimum": 500
          }
        },
        {
          "check": "SUBMISSION_DEADLINE",
          "result": "SKIPPED",
          "rule_ref": "submission_rules.deadline_days_from_treatment",
          "detail": {
            "reason": "no submission_date provided; cannot measure days-from-treatment without guessing against the processing clock",
            "treatment_date": "2024-10-28",
            "deadline_days": 30
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "DOC_VERIFICATION",
      "agent": "DocVerifierAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F021",
            "file_name": null,
            "detected_type": "PRESCRIPTION",
            "readability": "GOOD",
            "confidence": 0.9
          }
        },
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F022",
            "file_name": null,
            "detected_type": "HOSPITAL_BILL",
            "readability": "GOOD",
            "confidence": 0.99
          }
        },
        {
          "check": "REQUIREMENTS_MET",
          "result": "PASS",
          "rule_ref": "document_requirements.ALTERNATIVE_MEDICINE",
          "detail": {
            "required": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ],
            "detected": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ]
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 781
    },
    {
      "step": "EXTRACTION",
      "agent": "ExtractionAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F021",
            "doc_type": "PRESCRIPTION",
            "source": "vision",
            "unextracted_fields": [
              "medicines",
              "tests_ordered"
            ]
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F022",
            "doc_type": "HOSPITAL_BILL",
            "source": "vision",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 45903
    },
    {
      "step": "CONSISTENCY",
      "agent": "ConsistencyAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "PATIENT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "names": [
              "Kavita Nair",
              "Kavita Nair"
            ]
          }
        },
        {
          "check": "AMOUNT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "bill_total": 4000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "ADJUDICATION",
      "agent": "AdjudicatorAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "EXCLUSIONS",
          "result": "PASS",
          "rule_ref": "exclusions.conditions",
          "detail": {
            "diagnosis_texts": [
              "Chronic Joint Pain",
              "Panchakarma Therapy"
            ]
          }
        },
        {
          "check": "WAITING_PERIOD",
          "result": "PASS",
          "rule_ref": "waiting_periods",
          "detail": {
            "condition_matched": null
          }
        },
        {
          "check": "PRE_AUTHORIZATION",
          "result": "PASS",
          "rule_ref": "opd_categories.alternative_medicine",
          "detail": {
            "reason": "category has no pre-auth rules"
          }
        },
        {
          "check": "ANNUAL_OPD_LIMIT",
          "result": "PASS",
          "rule_ref": "coverage.annual_opd_limit",
          "detail": {
            "ytd": 0,
            "claimed": 4000,
            "limit": 50000
          }
        },
        {
          "check": "LINE_ITEMS",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "verdicts": [
              {
                "description": "Panchakarma Therapy (5 sessions)",
                "amount": 3000,
                "eligible_amount": 3000,
                "verdict": "APPROVED",
                "reason": "covered",
                "rule_ref": null
              },
              {
                "description": "Consultation",
                "amount": 1000,
                "eligible_amount": 1000,
                "verdict": "APPROVED",
                "reason": "covered",
                "rule_ref": null
              }
            ],
            "no_billable_items": false
          }
        },
        {
          "check": "PER_CLAIM_LIMIT",
          "result": "PASS",
          "rule_ref": "opd_categories.alternative_medicine.sub_limit",
          "detail": {
            "claimed": 4000,
            "limit": 8000
          }
        },
        {
          "check": "FINANCIAL_CALCULATION",
          "result": "PASS",
          "rule_ref": "opd_categories.alternative_medicine",
          "detail": {
            "base": 4000,
            "in_network": false,
            "hospital": "Ayur Wellness Centre",
            "network_discount_percent": 0,
            "network_discount": 0,
            "after_discount": 4000,
            "copay_percent": 0,
            "copay": 0,
            "payable": 4000,
            "order": "network discount applied before co-pay"
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 1
    },
    {
      "step": "FRAUD_CHECK",
      "agent": "FraudAgent",
      "status": "SKIPPED",
      "checks": [],
      "confidence_entries": [
        {
          "factor": 0.7,
          "reason": "FraudAgent failed and was skipped: simulated component failure (test flag)"
        }
      ],
      "error": {
        "code": "INTERNAL_ERROR",
        "message": "simulated component failure (test flag)",
        "member_message": "",
        "detail": {}
      },
      "duration_ms": 0
    },
    {
      "step": "AGGREGATION",
      "agent": "Aggregator",
      "status": "PASS",
      "checks": [],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    }
  ],
  "decision": {
    "status": "APPROVED",
    "approved_amount": 4000,
    "reasons": [
      "All checks passed"
    ],
    "confidence": 0.7,
    "member_message": "Approved amount: \u20b94000.",
    "ops_summary": "APPROVED: payable \u20b94000. Lines: Panchakarma Therapy (5 sessions): APPROVED (covered); Consultation: APPROVED (covered). Financial: {'base': 4000, 'in_network': False, 'hospital': 'Ayur Wellness Centre', 'network_discount_percent': 0, 'network_discount': 0, 'after_discount': 4000, 'copay_percent': 0, 'copay': 0, 'payable': 4000}. Components degraded/skipped: FRAUD_CHECK. Manual review recommended due to incomplete processing."
  }
}
```
</details>

## TC012 — Excluded Treatment
- Expected: `REJECTED` | Produced: `REJECTED` | **PASS**
- Approved amount: ₹0 | Confidence: 1.0
- Member message: 'Obesity and weight loss programs' is excluded under your policy and cannot be claimed. This treatment falls inside a waiting period. You will be eligible for obesity_treatment claims from 2025-04-01.
- Pipeline:
  - `INTAKE` PASS (0ms)
  - `DOC_VERIFICATION` PASS (831ms)  — F023:PRESCRIPTION@0.95, F024:HOSPITAL_BILL@0.99
  - `EXTRACTION` PASS (1186ms)  — F023:PRESCRIPTION=vision, F024:HOSPITAL_BILL=vision
  - `CONSISTENCY` PASS (0ms)
  - `ADJUDICATION` PASS (0ms)
  - `FRAUD_CHECK` PASS (0ms)
  - `AGGREGATION` PASS (0ms)

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-8D7563D0",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-14T06:26:51.434668Z",
  "completed_at": "2026-06-14T06:26:53.455449Z",
  "steps": [
    {
      "step": "INTAKE",
      "agent": "IntakeAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "POLICY_MATCHES",
          "result": "PASS",
          "rule_ref": "policy_id",
          "detail": {
            "policy_id": "PLUM_GHI_2024"
          }
        },
        {
          "check": "MEMBER_EXISTS",
          "result": "PASS",
          "rule_ref": "members",
          "detail": {
            "member_id": "EMP009"
          }
        },
        {
          "check": "CATEGORY_COVERED",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation.covered",
          "detail": {
            "covered": true
          }
        },
        {
          "check": "MINIMUM_AMOUNT",
          "result": "PASS",
          "rule_ref": "submission_rules.minimum_claim_amount",
          "detail": {
            "claimed": 8000,
            "minimum": 500
          }
        },
        {
          "check": "SUBMISSION_DEADLINE",
          "result": "SKIPPED",
          "rule_ref": "submission_rules.deadline_days_from_treatment",
          "detail": {
            "reason": "no submission_date provided; cannot measure days-from-treatment without guessing against the processing clock",
            "treatment_date": "2024-10-18",
            "deadline_days": 30
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "DOC_VERIFICATION",
      "agent": "DocVerifierAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F023",
            "file_name": null,
            "detected_type": "PRESCRIPTION",
            "readability": "GOOD",
            "confidence": 0.95
          }
        },
        {
          "check": "DOC_CLASSIFIED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F024",
            "file_name": null,
            "detected_type": "HOSPITAL_BILL",
            "readability": "GOOD",
            "confidence": 0.99
          }
        },
        {
          "check": "REQUIREMENTS_MET",
          "result": "PASS",
          "rule_ref": "document_requirements.CONSULTATION",
          "detail": {
            "required": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ],
            "detected": [
              "HOSPITAL_BILL",
              "PRESCRIPTION"
            ]
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 831
    },
    {
      "step": "EXTRACTION",
      "agent": "ExtractionAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F023",
            "doc_type": "PRESCRIPTION",
            "source": "vision",
            "unextracted_fields": [
              "medicines",
              "tests_ordered"
            ]
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F024",
            "doc_type": "HOSPITAL_BILL",
            "source": "vision",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 1186
    },
    {
      "step": "CONSISTENCY",
      "agent": "ConsistencyAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "PATIENT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "names": [
              "Anita Desai",
              "Anita Desai"
            ]
          }
        },
        {
          "check": "AMOUNT_MATCH",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "bill_total": 8000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "ADJUDICATION",
      "agent": "AdjudicatorAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "EXCLUSIONS",
          "result": "FAIL",
          "rule_ref": "exclusions.conditions",
          "detail": {
            "matched_exclusion": "Obesity and weight loss programs",
            "diagnosis_texts": [
              "Morbid Obesity - BMI 37",
              "Bariatric Consultation and Customised Diet Plan"
            ]
          }
        },
        {
          "check": "WAITING_PERIOD",
          "result": "FAIL",
          "rule_ref": "waiting_periods.specific_conditions.obesity_treatment",
          "detail": {
            "condition_matched": "obesity_treatment",
            "waiting_days": 365,
            "member_join_date": "2024-04-01",
            "eligible_from": "2025-04-01",
            "treatment_date": "2024-10-18"
          }
        },
        {
          "check": "PRE_AUTHORIZATION",
          "result": "PASS",
          "rule_ref": "opd_categories.consultation",
          "detail": {
            "reason": "category has no pre-auth rules"
          }
        },
        {
          "check": "ANNUAL_OPD_LIMIT",
          "result": "PASS",
          "rule_ref": "coverage.annual_opd_limit",
          "detail": {
            "ytd": 0,
            "claimed": 8000,
            "limit": 50000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "FRAUD_CHECK",
      "agent": "FraudAgent",
      "status": "PASS",
      "checks": [
        {
          "check": "SAME_DAY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.same_day_claims_limit",
          "detail": {
            "count_today": 1,
            "limit": 2
          }
        },
        {
          "check": "MONTHLY_CLAIMS",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.monthly_claims_limit",
          "detail": {
            "count_month": 1,
            "limit": 6
          }
        },
        {
          "check": "HIGH_VALUE",
          "result": "PASS",
          "rule_ref": "fraud_thresholds.auto_manual_review_above",
          "detail": {
            "claimed": 8000,
            "threshold": 25000
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    },
    {
      "step": "AGGREGATION",
      "agent": "Aggregator",
      "status": "PASS",
      "checks": [],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
    }
  ],
  "decision": {
    "status": "REJECTED",
    "approved_amount": 0,
    "reasons": [
      "EXCLUDED_CONDITION",
      "WAITING_PERIOD"
    ],
    "confidence": 1.0,
    "member_message": "'Obesity and weight loss programs' is excluded under your policy and cannot be claimed. This treatment falls inside a waiting period. You will be eligible for obesity_treatment claims from 2025-04-01.",
    "ops_summary": "Rejected: ['EXCLUDED_CONDITION', 'WAITING_PERIOD']. "
  }
}
```
</details>
