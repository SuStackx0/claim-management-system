from __future__ import annotations
from enum import StrEnum
from typing import Protocol, TypeVar
from pydantic import BaseModel, ConfigDict, Field

M = TypeVar("M", bound=BaseModel)

class LLMErrorKind(StrEnum):
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    PROVIDER_ERROR = "PROVIDER_ERROR"

class LLMError(Exception):
    def __init__(self, kind: LLMErrorKind, detail: str = "", retryable: bool = False):
        self.kind, self.detail, self.retryable = kind, detail, retryable
        super().__init__(f"{kind}: {detail}")

class DocClassification(BaseModel):
    detected_type: str
    readability: str = "GOOD"
    confidence: float = 1.0

class ExtractionOutput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    data: BaseModel
    field_confidence: dict[str, float] = Field(default_factory=dict)
    unextracted_fields: list[str] = Field(default_factory=list)
    source: str = "vision"

class NameMatch(BaseModel):
    equivalent: bool
    confidence: float = 1.0
    fuzzy: bool = False   # True when not an exact match (docks confidence)

class LLMClient(Protocol):
    async def classify_document(self, doc) -> DocClassification: ...
    async def extract(self, doc, schema: type[M]) -> ExtractionOutput: ...
    async def names_equivalent(self, a: str, b: str) -> NameMatch: ...
