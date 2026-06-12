import json, pytest
from app.config import settings

@pytest.fixture(scope="session")
def policy_dict():
    with open(settings.policy_path) as f:
        return json.load(f)

@pytest.fixture(scope="session")
def test_cases():
    with open(settings.test_cases_path) as f:
        return json.load(f)["test_cases"]

from app.core.context import ClaimContext
from app.core.policy_loader import PolicyLoader
from app.core.trace import ClaimTrace
from app.models.domain import ClaimSubmission

@pytest.fixture(scope="session")
def loader():
    return PolicyLoader.load(settings.policy_path)

@pytest.fixture
def make_ctx(loader):
    def _make(case_input: dict) -> ClaimContext:
        sub = ClaimSubmission.model_validate(case_input)
        return ClaimContext(submission=sub, loader=loader, trace=ClaimTrace(claim_id="TEST"))
    return _make

@pytest.fixture
def case_input(test_cases):
    def _get(case_id: str) -> dict:
        return next(c for c in test_cases if c["case_id"] == case_id)["input"]
    return _get
