from __future__ import annotations
from enum import StrEnum
from pydantic import BaseModel, Field

class ErrorCode(StrEnum):
    MEMBER_NOT_FOUND = "MEMBER_NOT_FOUND"
    POLICY_INACTIVE = "POLICY_INACTIVE"
    AMOUNT_BELOW_MINIMUM = "AMOUNT_BELOW_MINIMUM"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    INVALID_CATEGORY = "INVALID_CATEGORY"
    MISSING_REQUIRED_DOCUMENT = "MISSING_REQUIRED_DOCUMENT"
    WRONG_DOCUMENT_TYPE = "WRONG_DOCUMENT_TYPE"
    DOCUMENT_UNREADABLE = "DOCUMENT_UNREADABLE"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    PATIENT_MISMATCH = "PATIENT_MISMATCH"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class AgentError(BaseModel):
    code: ErrorCode
    message: str                      # for ops/devs
    member_message: str = ""          # what the member sees; specific + actionable
    detail: dict = Field(default_factory=dict)

class AgentFailure(Exception):
    """Raised by agents; orchestrator converts to StepResult and routes fatal/degrade."""
    def __init__(self, error: AgentError):
        self.error = error
        super().__init__(error.message)
