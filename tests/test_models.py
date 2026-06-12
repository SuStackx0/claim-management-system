def test_data_files_load(policy_dict, test_cases):
    assert policy_dict["policy_id"] == "PLUM_GHI_2024"
    assert len(test_cases) == 12


from datetime import date
from app.models.domain import ClaimSubmission, DocumentInput, DocType, Readability, DecisionStatus

def test_submission_parses_test_case_input(test_cases):
    tc4 = next(c for c in test_cases if c["case_id"] == "TC004")
    sub = ClaimSubmission.model_validate(tc4["input"])
    assert sub.member_id == "EMP001"
    assert sub.treatment_date == date(2024, 11, 1)
    assert sub.documents[0].actual_type == DocType.PRESCRIPTION
    assert sub.documents[0].content["doctor_name"] == "Dr. Arun Sharma"
    assert sub.ytd_claims_amount == 5000
    assert sub.simulate_component_failure is False

def test_submission_parses_every_test_case(test_cases):
    for case in test_cases:
        ClaimSubmission.model_validate(case["input"])  # must not raise

def test_quality_hint(test_cases):
    tc2 = next(c for c in test_cases if c["case_id"] == "TC002")
    sub = ClaimSubmission.model_validate(tc2["input"])
    assert sub.documents[1].quality == Readability.UNREADABLE

def test_extraction_schema_registry():
    from app.models.extraction import SCHEMA_BY_DOCTYPE, BillData, PrescriptionData
    assert SCHEMA_BY_DOCTYPE["HOSPITAL_BILL"] is BillData
    assert SCHEMA_BY_DOCTYPE["PRESCRIPTION"] is PrescriptionData
    bill = BillData.model_validate({"line_items": [{"description": "X", "amount": 100}], "total": 100})
    assert bill.line_items[0].amount == 100
