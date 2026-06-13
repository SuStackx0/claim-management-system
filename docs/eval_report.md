# Eval Report — 12 Test Cases

**Result: 12/12 passed**

> These cases run against the deterministic `MockClient` by design: `test_cases.json` ships document *content* as structured fixtures (no image files), so the eval validates the decision engine — policy checks, financial math, consistency, fraud, and the full trace — independently of the stochastic LLM perception layer. The real Gemini vision/extraction path is the same Orchestrator with the `LLMClient` swapped, and is exercised separately via the live API and the `@pytest.mark.live` tests.

## TC001 — Wrong Document Uploaded
- Expected: `None` | Produced: `None` | **PASS**
- Member message: For a CONSULTATION claim you must upload: HOSPITAL_BILL, PRESCRIPTION. You uploaded: PRESCRIPTION ('dr_sharma_prescription.jpg'), PRESCRIPTION ('another_prescription.jpg'). Missing: HOSPITAL_BILL. Please upload your hospital bill to proceed.

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-D1F99D53",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-13T18:29:23.330844Z",
  "completed_at": "2026-06-13T18:29:23.331819Z",
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
      "duration_ms": 0
    }
  ],
  "decision": null
}
```
</details>

## TC002 — Unreadable Document
- Expected: `None` | Produced: `None` | **PASS**
- Member message: Your Pharmacy Bill ('blurry_bill.jpg') is too blurry to read. Please re-upload a clear photo of this document. Your claim is on hold — it has not been rejected.

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-FA44E195",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-13T18:29:23.332180Z",
  "completed_at": "2026-06-13T18:29:23.332418Z",
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
        "code": "DOCUMENT_UNREADABLE",
        "message": "F004 unreadable",
        "member_message": "Your Pharmacy Bill ('blurry_bill.jpg') is too blurry to read. Please re-upload a clear photo of this document. Your claim is on hold \u2014 it has not been rejected.",
        "detail": {
          "file_id": "F004",
          "readability": "UNREADABLE"
        }
      },
      "duration_ms": 0
    }
  ],
  "decision": null
}
```
</details>

## TC003 — Documents Belong to Different Patients
- Expected: `None` | Produced: `None` | **PASS**
- Member message: Your documents appear to belong to different people: the prescription is for 'Rajesh Kumar' but the hospital bill is for 'Arjun Mehta'. All documents in one claim must be for the same patient. Please re-upload matching documents.

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-C73C82B2",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-13T18:29:23.332541Z",
  "completed_at": "2026-06-13T18:29:23.333343Z",
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
            "confidence": 1.0
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
            "readability": "GOOD",
            "confidence": 1.0
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
      "duration_ms": 0
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
            "source": "provided",
            "unextracted_fields": []
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F006",
            "doc_type": "HOSPITAL_BILL",
            "source": "provided",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
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
      "duration_ms": 0
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

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-2329C7E9",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-13T18:29:23.333661Z",
  "completed_at": "2026-06-13T18:29:23.334782Z",
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
            "confidence": 1.0
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
            "confidence": 1.0
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
      "duration_ms": 0
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
            "source": "provided",
            "unextracted_fields": []
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F008",
            "doc_type": "HOSPITAL_BILL",
            "source": "provided",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
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

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-F6DAFC7F",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-13T18:29:23.334920Z",
  "completed_at": "2026-06-13T18:29:23.335159Z",
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
            "confidence": 1.0
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
            "confidence": 1.0
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
      "duration_ms": 0
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
            "source": "provided",
            "unextracted_fields": []
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F010",
            "doc_type": "HOSPITAL_BILL",
            "source": "provided",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
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

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-1D219AED",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-13T18:29:23.335281Z",
  "completed_at": "2026-06-13T18:29:23.335677Z",
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
            "confidence": 1.0
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
      "duration_ms": 0
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
            "source": "provided",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
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

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-39650237",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-13T18:29:23.335803Z",
  "completed_at": "2026-06-13T18:29:23.336198Z",
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
            "confidence": 1.0
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
            "confidence": 1.0
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
            "confidence": 1.0
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
      "duration_ms": 0
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
            "source": "provided",
            "unextracted_fields": []
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F013",
            "doc_type": "LAB_REPORT",
            "source": "provided",
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
            "source": "provided",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
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
            "names": []
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

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-65EFE350",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-13T18:29:23.336398Z",
  "completed_at": "2026-06-13T18:29:23.336687Z",
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
            "confidence": 1.0
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
            "confidence": 1.0
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
      "duration_ms": 0
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
            "source": "provided",
            "unextracted_fields": []
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F016",
            "doc_type": "HOSPITAL_BILL",
            "source": "provided",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
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
            "names": []
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

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-66C0C430",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-13T18:29:23.336772Z",
  "completed_at": "2026-06-13T18:29:23.337242Z",
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
            "confidence": 1.0
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
            "confidence": 1.0
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
      "duration_ms": 0
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
            "source": "provided",
            "unextracted_fields": []
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F018",
            "doc_type": "HOSPITAL_BILL",
            "source": "provided",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
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
            "names": []
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
            "hospital": null,
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

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-6A5CA354",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-13T18:29:23.337318Z",
  "completed_at": "2026-06-13T18:29:23.337679Z",
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
            "confidence": 1.0
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
            "confidence": 1.0
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
      "duration_ms": 0
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
            "source": "provided",
            "unextracted_fields": []
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F020",
            "doc_type": "HOSPITAL_BILL",
            "source": "provided",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
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

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-496E3F50",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-13T18:29:23.337788Z",
  "completed_at": "2026-06-13T18:29:23.338104Z",
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
            "confidence": 1.0
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
            "confidence": 1.0
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
      "duration_ms": 0
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
            "source": "provided",
            "unextracted_fields": []
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F022",
            "doc_type": "HOSPITAL_BILL",
            "source": "provided",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
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
            "names": []
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
      "duration_ms": 0
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

<details><summary>Full trace</summary>

```json
{
  "claim_id": "CLM-477EE2B2",
  "pipeline_version": "1.0.0",
  "started_at": "2026-06-13T18:29:23.338404Z",
  "completed_at": "2026-06-13T18:29:23.338657Z",
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
            "confidence": 1.0
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
            "confidence": 1.0
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
      "duration_ms": 0
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
            "source": "provided",
            "unextracted_fields": []
          }
        },
        {
          "check": "FIELDS_EXTRACTED",
          "result": "PASS",
          "rule_ref": null,
          "detail": {
            "file_id": "F024",
            "doc_type": "HOSPITAL_BILL",
            "source": "provided",
            "unextracted_fields": []
          }
        }
      ],
      "confidence_entries": [],
      "error": null,
      "duration_ms": 0
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
            "names": []
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
              "Morbid Obesity \u2014 BMI 37",
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
