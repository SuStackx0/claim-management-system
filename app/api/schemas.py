from __future__ import annotations
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    llm_provider: str
    pipeline_version: str
