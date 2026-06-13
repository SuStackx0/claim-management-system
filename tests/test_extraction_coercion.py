"""Regression tests for schema-level coercion of messy LLM output.

These lock in the guarantee that the extraction Pydantic models NEVER raise and
NEVER silently lose data on the type-sloppy JSON that providers (esp. Groq's
non-schema-bound JSON mode) emit. The original bug: Groq returned
`tests_ordered: ""` (empty STRING) where a LIST was expected; pydantic rejected
it, extraction degraded, and a patient mismatch slipped through as an approval.

Every clean-data case asserts the validators are a strict no-op, so the
deterministic mock/eval path (clean fixtures through these same schemas) is
unaffected.
"""
import pytest
from app.models.extraction import (
    BillData, LabReportData, LineItem, PharmacyBillData, PrescriptionData,
)


# ── lists: "" → [], scalar → [scalar], null-ish stripped ─────────────────────
@pytest.mark.parametrize("raw, expected", [
    ("", []),                                   # the exact original bug
    (None, []),
    ("N/A", []),
    ("Paracetamol", ["Paracetamol"]),           # bare scalar promoted to list
    (["Paracetamol", "Vitamin C"], ["Paracetamol", "Vitamin C"]),  # clean: no-op
    (["CBC", "N/A", "", None, "Lipid"], ["CBC", "Lipid"]),         # drop null-ish elems
])
def test_list_field_coercion(raw, expected):
    p = PrescriptionData.model_validate({"tests_ordered": raw})
    assert p.tests_ordered == expected


# ── amounts: currency/commas/floats/strings → int ───────────────────────────
@pytest.mark.parametrize("raw, expected", [
    (1500, 1500),                               # clean: no-op
    ("1500", 1500),
    ("1500.0", 1500),
    ("₹1,500", 1500),
    ("Rs 1500", 1500),
    ("Rs. 1,500.50", 1500),
    ("INR 2,00,000", 200000),                   # Indian grouping
    ("", None),
    ("N/A", None),
    ("-", None),
])
def test_amount_coercion(raw, expected):
    b = BillData.model_validate({"total": raw})
    assert b.total == expected


# ── dates: Indian formats → ISO YYYY-MM-DD ───────────────────────────────────
@pytest.mark.parametrize("raw, expected", [
    ("2024-11-01", "2024-11-01"),               # clean ISO: no-op
    ("01-11-2024", "2024-11-01"),
    ("01/11/2024", "2024-11-01"),
    ("2024/11/01", "2024-11-01"),
    ("01-Nov-2024", "2024-11-01"),
    ("01 Nov 2024", "2024-11-01"),
    ("Nov 1, 2024", "2024-11-01"),
    ("01.11.2024", "2024-11-01"),
    ("NIL", None),
    ("N/A", None),
])
def test_date_coercion(raw, expected):
    b = BillData.model_validate({"date": raw})
    assert b.date == expected


def test_unrecognized_date_left_intact_not_raised():
    # an unparseable date must not crash; the field tolerates a raw string
    b = BillData.model_validate({"date": "sometime last week"})
    assert b.date == "sometime last week"


# ── scalars: null-ish → None; single-element list collapsed ──────────────────
@pytest.mark.parametrize("raw, expected", [
    ("Rajesh Kumar", "Rajesh Kumar"),           # clean: no-op
    ("", None),
    ("N/A", None),
    ("--", None),
    ("none", None),
    (["Rajesh Kumar"], "Rajesh Kumar"),         # collapse 1-elem list to scalar
])
def test_scalar_field_coercion(raw, expected):
    p = PrescriptionData.model_validate({"patient_name": raw})
    assert p.patient_name == expected


# ── nested objects: line_items amounts coerced the same way ──────────────────
def test_nested_line_item_amounts_coerced():
    b = BillData.model_validate({
        "total": "₹1,500",
        "line_items": [
            {"description": "Consultation", "amount": "Rs 1,000"},
            {"description": "CBC", "amount": "300.0"},
            {"description": "Dengue NS1", "amount": 200},   # clean: no-op
        ],
    })
    assert b.total == 1500
    assert [(li.description, li.amount) for li in b.line_items] == [
        ("Consultation", 1000), ("CBC", 300), ("Dengue NS1", 200)]


def test_line_items_empty_string_becomes_empty_list():
    b = BillData.model_validate({"line_items": "", "total": 0})
    assert b.line_items == []


def test_line_item_standalone_amount_string():
    li = LineItem.model_validate({"description": "X-Ray", "amount": "₹450"})
    assert li.amount == 450


# ── the precise original failure, end to end on the schema ───────────────────
def test_original_bug_empty_string_for_list_does_not_raise():
    # Groq's Llama-4 returned tests_ordered:"" — this MUST validate, not raise.
    p = PrescriptionData.model_validate({
        "doctor_name": "Dr. Arun Sharma",
        "patient_name": "Rajesh Kumar",
        "tests_ordered": "",        # empty STRING where a LIST is expected
        "medicines": "Paracetamol",  # bare scalar where a LIST is expected
    })
    assert p.tests_ordered == []
    assert p.medicines == ["Paracetamol"]
    assert p.patient_name == "Rajesh Kumar"


# ── clean-data no-op guarantee (eval path must be unaffected) ────────────────
def test_clean_fixture_is_exact_noop():
    clean = {
        "hospital_name": "City Clinic, Bengaluru", "patient_name": "Rajesh Kumar",
        "date": "2024-11-01", "total": 1500,
        "line_items": [
            {"description": "Consultation Fee", "amount": 1000},
            {"description": "CBC Test", "amount": 300},
            {"description": "Dengue NS1 Test", "amount": 200},
        ],
    }
    b = BillData.model_validate(clean)
    assert b.model_dump() == {
        "hospital_name": "City Clinic, Bengaluru", "patient_name": "Rajesh Kumar",
        "date": "2024-11-01", "bill_number": None, "total": 1500,
        "line_items": [
            {"description": "Consultation Fee", "amount": 1000, "quantity": 1},
            {"description": "CBC Test", "amount": 300, "quantity": 1},
            {"description": "Dengue NS1 Test", "amount": 200, "quantity": 1},
        ],
    }


def test_clean_prescription_fixture_noop():
    clean = {"doctor_name": "Dr. Arun Sharma", "patient_name": "Rajesh Kumar",
             "date": "2024-11-01", "diagnosis": "Viral Fever",
             "medicines": ["Paracetamol 650mg", "Vitamin C 500mg"]}
    p = PrescriptionData.model_validate(clean)
    assert p.medicines == ["Paracetamol 650mg", "Vitamin C 500mg"]
    assert p.patient_name == "Rajesh Kumar"
    assert p.date == "2024-11-01"
    assert p.tests_ordered == []


def test_pharmacy_and_lab_schemas_coerce_too():
    ph = PharmacyBillData.model_validate({"patient_name": "", "total": "Rs 800", "date": "25/10/2024"})
    assert ph.patient_name is None and ph.total == 800 and ph.date == "2024-10-25"
    lab = LabReportData.model_validate({"test_name": ["CBC"], "report_date": "01-Nov-2024", "lab_name": "N/A"})
    assert lab.test_name == "CBC" and lab.report_date == "2024-11-01" and lab.lab_name is None
