from __future__ import annotations
from pydantic import BaseModel
from app.llm.base import DocClassification, ExtractionOutput, LLMError, LLMErrorKind, NameMatch

_TYPE_KEYWORDS = [
    ("prescription", "PRESCRIPTION"), ("rx", "PRESCRIPTION"),
    ("pharmacy", "PHARMACY_BILL"),
    ("lab", "LAB_REPORT"), ("report", "LAB_REPORT"),
    ("bill", "HOSPITAL_BILL"), ("invoice", "HOSPITAL_BILL"), ("receipt", "HOSPITAL_BILL"),
]

_FIXTURES: dict[str, dict] = {
    "sample_bill.jpg": {"hospital_name": "City Clinic, Bengaluru", "patient_name": "Rajesh Kumar",
                        "date": "2024-11-01", "total": 1500,
                        "line_items": [{"description": "Consultation Fee", "amount": 1000},
                                       {"description": "CBC Test", "amount": 300},
                                       {"description": "Dengue NS1 Test", "amount": 200}]},
    "sample_prescription.jpg": {"doctor_name": "Dr. Arun Sharma", "doctor_registration": "KA/45678/2015",
                                "patient_name": "Rajesh Kumar", "date": "2024-11-01",
                                "diagnosis": "Viral Fever",
                                "medicines": ["Paracetamol 650mg", "Vitamin C 500mg"]},
}

def name_tokens_match(a: str, b: str) -> tuple[bool, bool]:
    """Returns (equivalent, fuzzy). 'R. Kumar' ≈ 'Rajesh Kumar': surname match + initial match."""
    ta = [t.strip(".").lower() for t in a.split() if t.strip(".")]
    tb = [t.strip(".").lower() for t in b.split() if t.strip(".")]
    if not ta or not tb:
        return False, False
    if ta == tb:
        return True, False
    if ta[-1] != tb[-1]:                      # surname must match
        return False, False
    fa, fb = ta[0], tb[0]
    if fa == fb or (fa[0] == fb[0] and (len(fa) == 1 or len(fb) == 1)):
        return True, True
    return False, False

class MockClient:
    def __init__(self):
        self.fail_next: LLMErrorKind | None = None

    def _maybe_fail(self):
        if self.fail_next:
            kind, self.fail_next = self.fail_next, None
            raise LLMError(kind, "injected failure", retryable=False)

    async def classify_document(self, doc) -> DocClassification:
        self._maybe_fail()
        name = (doc.file_name or "").lower()
        for kw, dtype in _TYPE_KEYWORDS:
            if kw in name:
                readability = "UNREADABLE" if "blur" in name else "GOOD"
                return DocClassification(detected_type=dtype, readability=readability, confidence=0.95)
        return DocClassification(detected_type="UNKNOWN", readability="GOOD", confidence=0.3)

    async def extract(self, doc, schema: type[BaseModel]) -> ExtractionOutput:
        self._maybe_fail()
        fixture = _FIXTURES.get(doc.file_name or "", {})
        data = schema.model_validate(fixture)
        return ExtractionOutput(data=data,
                                field_confidence={k: 0.95 for k in fixture},
                                unextracted_fields=[], source="vision")

    async def names_equivalent(self, a: str, b: str) -> NameMatch:
        self._maybe_fail()
        eq, fuzzy = name_tokens_match(a, b)
        return NameMatch(equivalent=eq, confidence=0.9 if fuzzy else 1.0, fuzzy=fuzzy)
