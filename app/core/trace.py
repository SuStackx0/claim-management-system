from __future__ import annotations
from datetime import datetime, timezone
from enum import StrEnum
from pydantic import BaseModel, Field
from app.core.errors import AgentError
from app.models.domain import Decision

class StepStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    DEGRADED = "DEGRADED"
    SKIPPED = "SKIPPED"

class CheckResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIPPED = "SKIPPED"

class PolicyCheck(BaseModel):
    check: str
    result: CheckResult
    rule_ref: str | None = None       # JSON path into policy_terms.json
    detail: dict = Field(default_factory=dict)

class ConfidenceEntry(BaseModel):
    factor: float
    reason: str

class StepResult(BaseModel):
    step: str
    agent: str
    status: StepStatus
    checks: list[PolicyCheck] = Field(default_factory=list)
    confidence_entries: list[ConfidenceEntry] = Field(default_factory=list)
    error: AgentError | None = None
    duration_ms: int = 0

class ClaimTrace(BaseModel):
    claim_id: str
    pipeline_version: str = "1.0.0"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    steps: list[StepResult] = Field(default_factory=list)
    decision: Decision | None = None

    def append(self, result: StepResult) -> None:
        self.steps.append(result)

    def confidence(self) -> float:
        c = 1.0
        for s in self.steps:
            for e in s.confidence_entries:
                c *= e.factor
        return max(0.0, min(1.0, c))

    def confidence_ledger(self) -> list[ConfidenceEntry]:
        return [e for s in self.steps for e in s.confidence_entries]
