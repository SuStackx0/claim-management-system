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
