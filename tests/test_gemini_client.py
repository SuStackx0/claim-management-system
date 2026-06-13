"""
tests/test_gemini_client.py

Mock-based unit tests for GeminiClient (app/llm/gemini_client.py).
No real API calls are made.

google.genai is injected as a MagicMock in sys.modules before any test runs so
that the lazy `from google.genai import types` calls inside GeminiClient never
touch the real SDK (which may block on Python 3.13 during first import).
"""

import asyncio
import json
import sys
import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel

# --- Inject mock SDK modules BEFORE importing anything that touches google.genai ---
_mock_genai = MagicMock()
_mock_types = MagicMock()
# `from google.genai import types` resolves via getattr(_mock_genai, "types"),
# so we pin _mock_genai.types = _mock_types so both references point to the same mock.
_mock_genai.types = _mock_types
sys.modules.setdefault("google.genai", _mock_genai)
sys.modules.setdefault("google.genai.types", _mock_types)
_mock_genai.Client = MagicMock(return_value=MagicMock())

from app.llm.base import DocClassification, ExtractionOutput, LLMError, LLMErrorKind, NameMatch  # noqa: E402
from app.llm.gemini_client import GeminiClient  # noqa: E402
from app.models.domain import DocumentInput  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_doc(file_bytes: bytes = b"fake-image-data", mime_type: str = "image/jpeg") -> DocumentInput:
    return DocumentInput(
        file_id="D1",
        file_name="test.jpg",
        file_bytes=file_bytes,
        mime_type=mime_type,
    )


def make_client(timeout_s: int = 30) -> GeminiClient:
    """Build a GeminiClient whose __init__ is bypassed.

    sys.modules already has mock google.genai entries (module-level setup above),
    so even if __init__ ran it would be safe — but we skip it anyway for speed.
    """
    client = object.__new__(GeminiClient)
    client._client = MagicMock()
    client.model = "gemini-2.5-flash"
    client.timeout_s = timeout_s
    return client


# ---------------------------------------------------------------------------
# _image_part — null-guard tests
# ---------------------------------------------------------------------------

def test_image_part_raises_on_none_bytes():
    """_image_part must raise PROVIDER_ERROR (non-retryable) when file_bytes is None."""
    client = make_client()
    doc = DocumentInput(file_id="D1", file_name="empty.jpg", file_bytes=None)
    with pytest.raises(LLMError) as exc_info:
        client._image_part(doc)
    err = exc_info.value
    assert err.kind == LLMErrorKind.PROVIDER_ERROR
    assert not err.retryable


def test_image_part_raises_on_empty_bytes():
    """_image_part must raise PROVIDER_ERROR when file_bytes is b'' (falsy)."""
    client = make_client()
    doc = DocumentInput(file_id="D1", file_name="empty.jpg", file_bytes=b"")
    with pytest.raises(LLMError) as exc_info:
        client._image_part(doc)
    assert exc_info.value.kind == LLMErrorKind.PROVIDER_ERROR


@pytest.mark.skip(reason="mock wiring for _image_part return value; deferred")
def test_image_part_returns_part_for_valid_bytes():
    """_image_part must return a types.Part when bytes are present."""
    client = make_client()
    mock_part = MagicMock()
    _mock_types.Part.from_bytes.return_value = mock_part

    result = client._image_part(make_doc())

    _mock_types.Part.from_bytes.assert_called()
    assert result is mock_part


@pytest.mark.skip(reason="mock wiring for _image_part return value; deferred")
def test_image_part_defaults_mime_type_to_jpeg():
    """_image_part must default mime_type to image/jpeg when doc.mime_type is None."""
    client = make_client()
    doc = DocumentInput(file_id="D1", file_name="img.jpg", file_bytes=b"data", mime_type=None)
    _mock_types.Part.from_bytes.reset_mock()

    client._image_part(doc)

    call_kwargs = _mock_types.Part.from_bytes.call_args[1]
    assert call_kwargs.get("mime_type") == "image/jpeg"


# ---------------------------------------------------------------------------
# _call retry on JSON decode error
# ---------------------------------------------------------------------------

async def test_call_retries_on_json_error_and_succeeds():
    """First attempt returns invalid JSON; second attempt returns valid JSON — must succeed."""
    client = make_client()
    call_count = 0

    async def mock_generate(parts, schema=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "not valid json {{{"
        return json.dumps({"detected_type": "HOSPITAL_BILL", "readability": "GOOD", "confidence": 0.95})

    client._generate = mock_generate

    with patch.object(client, "_image_part", return_value="mock-part"):
        result = await client.classify_document(make_doc())

    assert call_count == 2
    assert isinstance(result, DocClassification)
    assert result.detected_type == "HOSPITAL_BILL"
    assert result.readability == "GOOD"
    assert result.confidence == pytest.approx(0.95)


async def test_call_raises_schema_invalid_after_two_json_errors():
    """Two consecutive JSON failures must raise LLMError(SCHEMA_INVALID)."""
    client = make_client()

    async def always_invalid(parts, schema=None):
        return "}{definitely not json}{"

    client._generate = always_invalid

    with patch.object(client, "_image_part", return_value="mock-part"):
        with pytest.raises(LLMError) as exc_info:
            await client.classify_document(make_doc())

    assert exc_info.value.kind == LLMErrorKind.SCHEMA_INVALID


async def test_call_raises_schema_invalid_after_two_validation_errors():
    """Two valid JSON blobs that fail schema validation must raise LLMError(SCHEMA_INVALID)."""
    client = make_client()

    async def missing_required_field(parts, schema=None):
        # DocClassification.detected_type is required; omitting it causes ValidationError
        return json.dumps({"readability": "GOOD", "confidence": 0.9})

    client._generate = missing_required_field

    with patch.object(client, "_image_part", return_value="mock-part"):
        with pytest.raises(LLMError) as exc_info:
            await client.classify_document(make_doc())

    assert exc_info.value.kind == LLMErrorKind.SCHEMA_INVALID


# ---------------------------------------------------------------------------
# _call error mapping
# ---------------------------------------------------------------------------

async def test_call_maps_asyncio_timeout_to_llm_timeout():
    """asyncio.TimeoutError must map to LLMError(TIMEOUT, retryable=True)."""
    client = make_client()

    async def timeout_generate(parts, schema=None):
        raise asyncio.TimeoutError()

    client._generate = timeout_generate

    with patch.object(client, "_image_part", return_value="mock-part"):
        with pytest.raises(LLMError) as exc_info:
            await client.classify_document(make_doc())

    err = exc_info.value
    assert err.kind == LLMErrorKind.TIMEOUT
    assert err.retryable is True


async def test_call_maps_429_exception_to_rate_limit():
    """An exception whose message contains '429' must map to LLMError(RATE_LIMIT, retryable=True)."""
    client = make_client()

    async def rate_limited(parts, schema=None):
        raise Exception("HTTP 429 Too Many Requests")

    client._generate = rate_limited

    with patch.object(client, "_image_part", return_value="mock-part"):
        with pytest.raises(LLMError) as exc_info:
            await client.classify_document(make_doc())

    err = exc_info.value
    assert err.kind == LLMErrorKind.RATE_LIMIT
    assert err.retryable is True


async def test_call_maps_generic_exception_to_provider_error():
    """A non-429 exception must map to LLMError(PROVIDER_ERROR, retryable=False)."""
    client = make_client()

    async def bad_generate(parts, schema=None):
        raise Exception("Internal server error")

    client._generate = bad_generate

    with patch.object(client, "_image_part", return_value="mock-part"):
        with pytest.raises(LLMError) as exc_info:
            await client.classify_document(make_doc())

    err = exc_info.value
    assert err.kind == LLMErrorKind.PROVIDER_ERROR
    assert err.retryable is False


async def test_llm_error_propagates_unchanged():
    """An LLMError raised by _generate must not be re-wrapped — same object must propagate."""
    client = make_client()
    original = LLMError(LLMErrorKind.PROVIDER_ERROR, "no valid part", retryable=True)

    async def raises_llm_error(parts, schema=None):
        raise original

    client._generate = raises_llm_error

    with patch.object(client, "_image_part", return_value="mock-part"):
        with pytest.raises(LLMError) as exc_info:
            await client.classify_document(make_doc())

    assert exc_info.value is original


# ---------------------------------------------------------------------------
# _generate error paths
# ---------------------------------------------------------------------------

async def test_generate_raises_provider_error_on_valueerror():
    """_generate must wrap ValueError from resp.text into LLMError(PROVIDER_ERROR, retryable=True)."""
    client = make_client()

    # Patch the underlying async API call to return a response whose .text raises ValueError
    mock_resp = MagicMock()
    type(mock_resp).text = property(lambda self: (_ for _ in ()).throw(ValueError("no parts")))

    async def fake_generate_content(*args, **kwargs):
        return mock_resp

    client._client.aio.models.generate_content = fake_generate_content

    with patch("google.genai.types.GenerateContentConfig"), \
         pytest.raises(LLMError) as exc_info:
        await client._generate(["prompt"])

    err = exc_info.value
    assert err.kind == LLMErrorKind.PROVIDER_ERROR
    assert err.retryable is True


async def test_generate_raises_provider_error_on_empty_text():
    """_generate must raise LLMError(PROVIDER_ERROR, retryable=True) when resp.text is ''."""
    client = make_client()

    mock_resp = MagicMock()
    mock_resp.text = ""

    async def fake_generate_content(*args, **kwargs):
        return mock_resp

    client._client.aio.models.generate_content = fake_generate_content

    with patch("google.genai.types.GenerateContentConfig"), \
         pytest.raises(LLMError) as exc_info:
        await client._generate(["prompt"])

    err = exc_info.value
    assert err.kind == LLMErrorKind.PROVIDER_ERROR
    assert err.retryable is True


async def test_generate_raises_provider_error_on_none_text():
    """_generate must raise LLMError(PROVIDER_ERROR, retryable=True) when resp.text is None."""
    client = make_client()

    mock_resp = MagicMock()
    mock_resp.text = None

    async def fake_generate_content(*args, **kwargs):
        return mock_resp

    client._client.aio.models.generate_content = fake_generate_content

    with patch("google.genai.types.GenerateContentConfig"), \
         pytest.raises(LLMError) as exc_info:
        await client._generate(["prompt"])

    err = exc_info.value
    assert err.kind == LLMErrorKind.PROVIDER_ERROR
    assert err.retryable is True


# ---------------------------------------------------------------------------
# classify_document
# ---------------------------------------------------------------------------

async def test_classify_document_returns_doc_classification():
    """classify_document must return a populated DocClassification."""
    client = make_client()

    async def mock_generate(parts, schema=None):
        return json.dumps({"detected_type": "LAB_REPORT", "readability": "PARTIAL", "confidence": 0.8})

    client._generate = mock_generate

    with patch.object(client, "_image_part", return_value="mock-part"):
        result = await client.classify_document(make_doc())

    assert isinstance(result, DocClassification)
    assert result.detected_type == "LAB_REPORT"
    assert result.readability == "PARTIAL"
    assert result.confidence == pytest.approx(0.8)


async def test_classify_document_applies_defaults():
    """classify_document must apply model defaults when optional fields are absent."""
    client = make_client()

    async def mock_generate(parts, schema=None):
        return json.dumps({"detected_type": "UNKNOWN"})

    client._generate = mock_generate

    with patch.object(client, "_image_part", return_value="mock-part"):
        result = await client.classify_document(make_doc())

    assert result.readability == "GOOD"   # default
    assert result.confidence == pytest.approx(1.0)  # default


async def test_classify_document_passes_image_part_to_generate():
    """classify_document must include the image part when calling _generate."""
    client = make_client()
    received_parts = []

    async def capturing_generate(parts, schema=None):
        received_parts.extend(parts)
        return json.dumps({"detected_type": "PRESCRIPTION", "readability": "GOOD", "confidence": 0.99})

    client._generate = capturing_generate

    sentinel = object()
    with patch.object(client, "_image_part", return_value=sentinel):
        await client.classify_document(make_doc())

    assert sentinel in received_parts


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------

class BillSchema(BaseModel):
    hospital_name: str | None = None
    total_amount: int | None = None
    date: str | None = None


async def test_extract_builds_extraction_output():
    """extract must return an ExtractionOutput with correct field_confidence and unextracted_fields."""
    client = make_client()

    async def mock_generate(parts, schema=None):
        return json.dumps({"hospital_name": "City Hospital", "total_amount": 5000, "date": None})

    client._generate = mock_generate

    with patch.object(client, "_image_part", return_value="mock-part"):
        out = await client.extract(make_doc(), BillSchema)

    assert isinstance(out, ExtractionOutput)
    assert out.source == "vision"
    # present fields
    assert "hospital_name" in out.field_confidence
    assert "total_amount" in out.field_confidence
    assert all(v == pytest.approx(0.9) for v in out.field_confidence.values())
    # None field is absent → unextracted
    assert "date" in out.unextracted_fields
    # present fields not in unextracted
    assert "hospital_name" not in out.unextracted_fields
    assert "total_amount" not in out.unextracted_fields


async def test_extract_all_fields_present():
    """When all fields are populated, unextracted_fields must be empty."""
    client = make_client()

    async def mock_generate(parts, schema=None):
        return json.dumps({"hospital_name": "Apollo", "total_amount": 12000, "date": "2026-01-15"})

    client._generate = mock_generate

    with patch.object(client, "_image_part", return_value="mock-part"):
        out = await client.extract(make_doc(), BillSchema)

    assert out.unextracted_fields == []
    assert len(out.field_confidence) == 3


async def test_extract_all_fields_missing():
    """When all fields are None, field_confidence must be empty and all fields in unextracted."""
    client = make_client()

    async def mock_generate(parts, schema=None):
        return json.dumps({"hospital_name": None, "total_amount": None, "date": None})

    client._generate = mock_generate

    with patch.object(client, "_image_part", return_value="mock-part"):
        out = await client.extract(make_doc(), BillSchema)

    assert out.field_confidence == {}
    assert set(out.unextracted_fields) == {"hospital_name", "total_amount", "date"}


async def test_extract_returns_data_instance_of_schema():
    """extract must set out.data to an instance of the passed schema class."""
    client = make_client()

    async def mock_generate(parts, schema=None):
        return json.dumps({"hospital_name": "Max Healthcare", "total_amount": 7500, "date": None})

    client._generate = mock_generate

    with patch.object(client, "_image_part", return_value="mock-part"):
        out = await client.extract(make_doc(), BillSchema)

    assert isinstance(out.data, BillSchema)
    assert out.data.hospital_name == "Max Healthcare"
    assert out.data.total_amount == 7500


# ---------------------------------------------------------------------------
# names_equivalent
# ---------------------------------------------------------------------------

async def test_names_equivalent_returns_name_match_true():
    """names_equivalent must return NameMatch with equivalent=True when model says so."""
    client = make_client()

    async def mock_generate(parts, schema=None):
        return json.dumps({"equivalent": True, "confidence": 0.95, "fuzzy": True})

    client._generate = mock_generate
    result = await client.names_equivalent("Rajesh Kumar", "R. Kumar")

    assert isinstance(result, NameMatch)
    assert result.equivalent is True
    assert result.confidence == pytest.approx(0.95)
    assert result.fuzzy is True


async def test_names_equivalent_returns_name_match_false():
    """names_equivalent must return NameMatch with equivalent=False for different names."""
    client = make_client()

    async def mock_generate(parts, schema=None):
        return json.dumps({"equivalent": False, "confidence": 0.99, "fuzzy": False})

    client._generate = mock_generate
    result = await client.names_equivalent("Priya Sharma", "Rohan Verma")

    assert isinstance(result, NameMatch)
    assert result.equivalent is False
    assert result.fuzzy is False


async def test_names_equivalent_embeds_names_in_prompt():
    """names_equivalent must include both name strings when calling _generate."""
    client = make_client()
    received_parts = []

    async def capturing_generate(parts, schema=None):
        received_parts.extend(parts)
        return json.dumps({"equivalent": True, "confidence": 1.0, "fuzzy": False})

    client._generate = capturing_generate
    await client.names_equivalent("Alice", "Bob")

    prompt_text = " ".join(str(p) for p in received_parts)
    assert "Alice" in prompt_text
    assert "Bob" in prompt_text


async def test_names_equivalent_applies_defaults():
    """names_equivalent must apply NameMatch defaults when optional fields are absent."""
    client = make_client()

    async def mock_generate(parts, schema=None):
        # Omit confidence and fuzzy — model defaults should apply
        return json.dumps({"equivalent": True})

    client._generate = mock_generate
    result = await client.names_equivalent("A", "A")

    assert result.confidence == pytest.approx(1.0)
    assert result.fuzzy is False


# ---------------------------------------------------------------------------
# _call: feedback string on retry
# ---------------------------------------------------------------------------

async def test_call_passes_feedback_on_retry():
    """On the second attempt, _call must include a non-empty feedback string in parts."""
    client = make_client()
    call_count = 0
    second_call_parts = []

    async def mock_generate(parts, schema=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "bad json }{{"
        second_call_parts.extend(parts)
        return json.dumps({"detected_type": "PRESCRIPTION", "readability": "GOOD", "confidence": 0.9})

    client._generate = mock_generate

    with patch.object(client, "_image_part", return_value="mock-part"):
        await client.classify_document(make_doc())

    assert call_count == 2
    # The feedback string is appended to parts on the second call
    # There should be more than just the original parts (prompt + image)
    assert len(second_call_parts) >= 3  # prompt + image + feedback


# ---------------------------------------------------------------------------
# Live test (skipped unless -m live)
# ---------------------------------------------------------------------------

@pytest.mark.live
async def test_classify_real_document():
    """Requires GEMINI_API_KEY env var and issues a real Gemini API call."""
    import os
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set")

    client = GeminiClient(api_key=api_key)

    # Minimal valid 1x1 white JPEG
    jpeg_bytes = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
        b"\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c"
        b"\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1edL\t\t\x0c\x11\x0c\x0c"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00"
        b"\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01"
        b"\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00"
        b"\xfb\x00\x00\xff\xd9"
    )
    doc = DocumentInput(file_id="T1", file_name="white.jpg", file_bytes=jpeg_bytes)
    result = await client.classify_document(doc)

    assert isinstance(result, DocClassification)
    valid_types = {
        "PRESCRIPTION", "HOSPITAL_BILL", "PHARMACY_BILL", "LAB_REPORT",
        "DIAGNOSTIC_REPORT", "DISCHARGE_SUMMARY", "DENTAL_REPORT", "UNKNOWN",
    }
    assert result.detected_type in valid_types
