from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from app.core.policy_loader import PolicyLoader
from app.core.trace import ClaimTrace
from app.models.domain import ClaimSubmission, Member
from app.models.policy import PolicyView

class DocVerdict(BaseModel):
    file_id: str
    file_name: str | None = None
    detected_type: str
    readability: str
    confidence: float = 1.0

class ExtractionRecord(BaseModel):
    file_id: str
    doc_type: str
    data: dict = Field(default_factory=dict)      # validated model, dumped
    field_confidence: dict[str, float] = Field(default_factory=dict)
    unextracted_fields: list[str] = Field(default_factory=list)
    source: str = "provided"                       # "vision" | "provided"
    degraded: bool = False

class ConsistencyFinding(BaseModel):
    check: str
    severity: str                                  # "FATAL" | "WARNING"
    detail: dict = Field(default_factory=dict)

class LineItemVerdict(BaseModel):
    description: str
    amount: int
    eligible_amount: int
    verdict: str                                   # "APPROVED" | "REJECTED" | "CAPPED"
    reason: str
    rule_ref: str | None = None

class FraudSignal(BaseModel):
    signal: str
    detail: dict = Field(default_factory=dict)
    rule_ref: str | None = None

class ClaimContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    submission: ClaimSubmission
    loader: PolicyLoader
    trace: ClaimTrace
    member: Member | None = None
    policy_view: PolicyView | None = None
    doc_verdicts: list[DocVerdict] = Field(default_factory=list)
    extractions: list[ExtractionRecord] = Field(default_factory=list)
    findings: list[ConsistencyFinding] = Field(default_factory=list)
    line_verdicts: list[LineItemVerdict] = Field(default_factory=list)
    fraud_signals: list[FraudSignal] = Field(default_factory=list)
    financial: dict = Field(default_factory=dict)  # breakdown: base, discount, copay, payable
    blocking_reasons: list[str] = Field(default_factory=list)  # e.g. WAITING_PERIOD
    # decision-relevant checks that could NOT be verified (e.g. PATIENT_MATCH when a
    # patient-bearing doc failed extraction). A non-empty list caps the outcome at
    # MANUAL_REVIEW — an unverifiable check must never prop up a confident approval.
    unverified_checks: list[str] = Field(default_factory=list)
