import pytest
from app.llm.base import LLMError, LLMErrorKind
from app.llm.mock_client import MockClient, name_tokens_match
from app.models.domain import DocumentInput
from app.models.extraction import BillData

@pytest.fixture
def mock_llm():
    return MockClient()

async def test_mock_classifies_by_filename(mock_llm):
    doc = DocumentInput(file_id="F1", file_name="dr_sharma_prescription.jpg")
    c = await mock_llm.classify_document(doc)
    assert c.detected_type == "PRESCRIPTION"
    assert c.readability == "GOOD"

async def test_mock_classifies_blurry_as_unreadable(mock_llm):
    doc = DocumentInput(file_id="F1", file_name="blurry_bill.jpg")
    c = await mock_llm.classify_document(doc)
    assert c.detected_type == "HOSPITAL_BILL"
    assert c.readability == "UNREADABLE"

async def test_mock_unknown_filename_low_confidence(mock_llm):
    doc = DocumentInput(file_id="F1", file_name="random.jpg")
    c = await mock_llm.classify_document(doc)
    assert c.detected_type == "UNKNOWN"
    assert c.confidence < 0.5

async def test_mock_extracts_fixture(mock_llm):
    doc = DocumentInput(file_id="F1", file_name="sample_bill.jpg")
    r = await mock_llm.extract(doc, BillData)
    assert isinstance(r.data, BillData)
    assert r.data.total == 1500
    assert r.source == "vision"

async def test_mock_failure_injection_resets(mock_llm):
    mock_llm.fail_next = LLMErrorKind.TIMEOUT
    doc = DocumentInput(file_id="F1", file_name="sample_bill.jpg")
    with pytest.raises(LLMError) as ei:
        await mock_llm.extract(doc, BillData)
    assert ei.value.kind == LLMErrorKind.TIMEOUT
    # next call succeeds (fail_next resets)
    r = await mock_llm.extract(doc, BillData)
    assert r.data.total == 1500

async def test_mock_names_equivalent(mock_llm):
    assert (await mock_llm.names_equivalent("Rajesh Kumar", "R. Kumar")).equivalent
    m = await mock_llm.names_equivalent("Rajesh Kumar", "Arjun Mehta")
    assert not m.equivalent

async def test_fuzzy_match_flagged(mock_llm):
    m = await mock_llm.names_equivalent("Rajesh Kumar", "R. Kumar")
    assert m.fuzzy is True
    m2 = await mock_llm.names_equivalent("Rajesh Kumar", "Rajesh Kumar")
    assert m2.fuzzy is False

def test_name_tokens_match_pure():
    assert name_tokens_match("Rajesh Kumar", "Rajesh Kumar") == (True, False)
    assert name_tokens_match("Rajesh Kumar", "R. Kumar") == (True, True)
    assert name_tokens_match("Rajesh Kumar", "Arjun Mehta") == (False, False)
    assert name_tokens_match("Rajesh Kumar", "Sunita Kumar") == (False, False)  # same surname, diff first
    assert name_tokens_match("", "Rajesh Kumar") == (False, False)
