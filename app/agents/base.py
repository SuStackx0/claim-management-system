from __future__ import annotations
from abc import ABC, abstractmethod
from app.core.context import ClaimContext
from app.core.trace import StepResult

class Agent(ABC):
    name: str = "Agent"
    step: str = "STEP"
    fatal: bool = True

    @abstractmethod
    async def run(self, ctx: ClaimContext) -> StepResult: ...
