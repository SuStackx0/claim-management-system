import pytest
from app.core.policy_loader import PolicyLoader

@pytest.fixture(scope="module")
def loader():
    from app.config import settings
    return PolicyLoader.load(settings.policy_path)

def test_policy_validates(loader):
    assert loader.policy.policy_id == "PLUM_GHI_2024"
    assert loader.policy.coverage.per_claim_limit == 5000

def test_rule_ref_lookup(loader):
    assert loader.rule("opd_categories.consultation.copay_percent") == 10
    assert loader.rule("waiting_periods.specific_conditions.diabetes") == 90
    assert "Apollo Hospitals" in loader.rule("network_hospitals")

def test_rule_ref_missing_raises(loader):
    with pytest.raises(KeyError):
        loader.rule("opd_categories.nonexistent.copay_percent")

def test_category_view(loader):
    view = loader.view("CONSULTATION")
    assert view.rules.sub_limit == 2000
    assert view.required_docs == ["PRESCRIPTION", "HOSPITAL_BILL"]

def test_view_unknown_category_raises(loader):
    with pytest.raises(KeyError):
        loader.view("SURGERY")

def test_member_lookup(loader):
    m = loader.member("EMP001")
    assert m.name == "Rajesh Kumar"
    assert loader.member("NOPE") is None

def test_dependents_of(loader):
    names = [d.name for d in loader.dependents_of("EMP001")]
    assert "Sunita Kumar" in names and "Arjun Kumar" in names
    assert loader.dependents_of("EMP002") == []  # no dependents
