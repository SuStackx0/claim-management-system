from __future__ import annotations
from datetime import date
from enum import StrEnum
from pydantic import BaseModel, Field

class DocType(StrEnum):
    PRESCRIPTION = "PRESCRIPTION"
    HOSPITAL_BILL = "HOSPITAL_BILL"
    PHARMACY_BILL = "PHARMACY_BILL"
    LAB_REPORT = "LAB_REPORT"
    DIAGNOSTIC_REPORT = "DIAGNOSTIC_REPORT"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    DENTAL_REPORT = "DENTAL_REPORT"
    UNKNOWN = "UNKNOWN"

class Readability(StrEnum):
    GOOD = "GOOD"
    PARTIAL = "PARTIAL"
    UNREADABLE = "UNREADABLE"

class DecisionStatus(StrEnum):
    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"

class DocumentInput(BaseModel):
    file_id: str
    file_name: str | None = None
    # test-path hints (eval injects these); real path fills them via LLM
    actual_type: DocType | None = None
    quality: Readability | None = None
    patient_name_on_doc: str | None = None
    content: dict | None = None
    # real-path payload
    file_bytes: bytes | None = None
    mime_type: str | None = None

class ClaimHistoryItem(BaseModel):
    claim_id: str
    date: date
    amount: int
    provider: str | None = None

class ClaimSubmission(BaseModel):
    member_id: str
    policy_id: str
    claim_category: str
    treatment_date: date
    claimed_amount: int
    hospital_name: str | None = None
    ytd_claims_amount: int = 0
    pre_authorization_id: str | None = None
    claims_history: list[ClaimHistoryItem] = Field(default_factory=list)
    simulate_component_failure: bool = False
    documents: list[DocumentInput]

class Member(BaseModel):
    member_id: str
    name: str
    date_of_birth: date
    gender: str
    relationship: str
    join_date: date | None = None
    primary_member_id: str | None = None
    dependents: list[str] = Field(default_factory=list)

class Decision(BaseModel):
    status: DecisionStatus
    approved_amount: int = 0
    reasons: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    member_message: str = ""
    ops_summary: str = ""

class ClaimOutcome(BaseModel):
    claim_id: str
    status: str  # "COMPLETED" | "STOPPED"
    decision: Decision | None = None
    member_message: str = ""
    trace: dict = Field(default_factory=dict)
