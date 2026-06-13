from __future__ import annotations
import asyncio, json
from pydantic import BaseModel, ValidationError
from app.llm.base import DocClassification, ExtractionOutput, LLMError, LLMErrorKind, NameMatch
from app.models.domain import DocumentInput

CLASSIFY_PROMPT = """You are a medical document classifier for Indian health insurance claims.
Look at this document image and return JSON with:
- detected_type: one of PRESCRIPTION, HOSPITAL_BILL, PHARMACY_BILL, LAB_REPORT,
  DIAGNOSTIC_REPORT, DISCHARGE_SUMMARY, DENTAL_REPORT, UNKNOWN
- readability: GOOD (fully legible), PARTIAL (some fields obscured/blurry), UNREADABLE
- confidence: 0.0-1.0
Documents may be handwritten, photographed at an angle, or have rubber stamps over text."""

EXTRACT_PROMPT = """Extract structured data from this Indian medical document.
Rules: expand medical shorthand (HTN=Hypertension, T2DM=Type 2 Diabetes Mellitus).
If a field is obscured by a stamp or illegible, omit it rather than guessing.
Amounts are integers in INR. Dates as YYYY-MM-DD. Return JSON matching the schema."""

NAME_PROMPT = """Are these two strings the same person's name (Indian naming conventions,
initials, honorifics)? A: "{a}"  B: "{b}"
Return JSON: {{"equivalent": bool, "confidence": 0-1, "fuzzy": bool}}
fuzzy=true when they match but not exactly (initials, order, honorifics)."""


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout_s: int = 30):
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self.model = model
        self.timeout_s = timeout_s

    async def _generate(self, parts: list, schema: type[BaseModel] | None = None) -> str:
        from google.genai import types
        cfg = types.GenerateContentConfig(
            response_mime_type="application/json",
            **({"response_schema": schema} if schema else {}))
        resp = await asyncio.wait_for(
            self._client.aio.models.generate_content(
                model=self.model, contents=parts, config=cfg),
            timeout=self.timeout_s)
        try:
            text = resp.text
        except ValueError as e:
            raise LLMError(LLMErrorKind.PROVIDER_ERROR, f"no valid response part: {e}", retryable=True)
        if not text:
            raise LLMError(LLMErrorKind.PROVIDER_ERROR, "empty response text", retryable=True)
        return text

    def _image_part(self, doc: DocumentInput):
        if not doc.file_bytes:
            raise LLMError(LLMErrorKind.PROVIDER_ERROR,
                           f"document {doc.file_id!r} has no file_bytes",
                           retryable=False)
        from google.genai import types
        return types.Part.from_bytes(data=doc.file_bytes,
                                     mime_type=doc.mime_type or "image/jpeg")

    async def _call(self, parts, out_model: type[BaseModel], feedback: str = ""):
        last_err = None
        for _ in range(2):
            try:
                text = await self._generate(
                    parts + ([feedback] if feedback else []),
                    schema=out_model)
                return out_model.model_validate(json.loads(text))
            except (json.JSONDecodeError, ValidationError) as e:
                last_err, feedback = e, f"Previous output was invalid: {e}. Return valid JSON only."
            except LLMError:
                raise
            except asyncio.TimeoutError:
                raise LLMError(LLMErrorKind.TIMEOUT, "gemini timeout", retryable=True)
            except Exception as e:
                kind = LLMErrorKind.RATE_LIMIT if "429" in str(e) else LLMErrorKind.PROVIDER_ERROR
                raise LLMError(kind, str(e), retryable=kind == LLMErrorKind.RATE_LIMIT)
        raise LLMError(LLMErrorKind.SCHEMA_INVALID, str(last_err))

    async def classify_document(self, doc: DocumentInput) -> DocClassification:
        return await self._call([CLASSIFY_PROMPT, self._image_part(doc)], DocClassification)

    async def extract(self, doc: DocumentInput, schema: type[BaseModel]) -> ExtractionOutput:
        data = await self._call([EXTRACT_PROMPT, self._image_part(doc)], schema)
        present = {k for k, v in data.model_dump().items() if v not in (None, [], "")}
        all_fields = set(schema.model_fields)
        return ExtractionOutput(data=data,
                                field_confidence={k: 0.9 for k in present},
                                unextracted_fields=sorted(all_fields - present),
                                source="vision")

    async def names_equivalent(self, a: str, b: str) -> NameMatch:
        return await self._call([NAME_PROMPT.format(a=a, b=b)], NameMatch)
