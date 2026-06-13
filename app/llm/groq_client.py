from __future__ import annotations
import asyncio, base64, json, re
import httpx
from pydantic import BaseModel, ValidationError
from app.llm.base import DocClassification, ExtractionOutput, LLMError, LLMErrorKind, NameMatch
from app.models.domain import DocumentInput

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

CLASSIFY_PROMPT = """You are a medical document classifier for Indian health insurance claims.

Examine the document image and return ONLY a JSON object with these exact keys:

{
  "detected_type": "PRESCRIPTION | HOSPITAL_BILL | PHARMACY_BILL | LAB_REPORT | DIAGNOSTIC_REPORT | DISCHARGE_SUMMARY | DENTAL_REPORT | UNKNOWN",
  "readability": "GOOD | PARTIAL | UNREADABLE",
  "confidence": 0.0–1.0,
  "degradation_flags": ["STAMP_OVERLAP", "SKEW", "BLUR", "HANDWRITTEN", "LOW_LIGHT"]
}

Classification rules:
- Use UNKNOWN only when the document type is genuinely ambiguous after careful inspection.
- PARTIAL: one or more key fields are obscured but the document type is still identifiable even this should be mentioned to rescan and reupload.
- UNREADABLE: document type cannot be determined at all. Mostly blurry, low-light, or heavily stamped documents. Mark them as unreadable even if some is blurry
- confidence reflects certainty about detected_type, not readability.
- degradation_flags lists every applicable condition; use [] if none apply.

Documents may be handwritten, photographed at an angle, rubber-stamped, or low-resolution.
Return ONLY the JSON object — no explanation, no markdown fences."""

EXTRACT_PROMPT = """You are a data extraction specialist for Indian health insurance claims processing.

Extract all available structured data from this medical document and return it as a JSON object.

Extraction rules:
1. Expand all medical shorthand — e.g. HTN → Hypertension, T2DM → Type 2 Diabetes Mellitus, SOB → Shortness of Breath, BP → Blood Pressure, Rx → Prescription.
2. Monetary amounts: integers in INR. Strip currency symbols and commas (₹1,500 → 1500). If a total is partially obscured but line items are visible, sum the visible items.
3. Dates: YYYY-MM-DD. If only month+year visible, use YYYY-MM-01. If day+month only, use current year.
4. Omit a field entirely if it is obscured by a stamp, illegible, or absent — never guess or interpolate.
5. Names: preserve original spelling exactly as written; do not normalise or reorder.
6. Quantities and dosages: include the unit (e.g. "500mg", "10ml", "2 tablets").
7. If the document contains a table (itemised bill, lab results), extract each row as an object in an array.

Return ONLY the JSON object — no explanation, no markdown fences."""

NAME_PROMPT = """Determine whether these two name strings refer to the same person, applying Indian naming conventions.

A: "{a}"
B: "{b}"

Matching rules — treat as equivalent when:
- One name uses initials for given/father's name (e.g. "R. Krishnamurthy" ≡ "Ravi Krishnamurthy")
- Name components appear in different order (e.g. "Sharma Priya" ≡ "Priya Sharma")
- Honorifics or titles differ or are absent (e.g. "Dr. Anand" ≡ "Anand", "Smt. Lakshmi" ≡ "Lakshmi")
- Common transliteration variants (e.g. "Suresh" ≡ "Sureesh", "Mohammed" ≡ "Mohammad" ≡ "Mohamed")
- Patronymic suffix present in one only (e.g. "Ramesh s/o Venkat" ≡ "Ramesh Venkat")
- Nickname vs full name when unambiguous (e.g. "Raju" ≡ "Rajesh" — only if surname matches)

Do NOT treat as equivalent when:
- Core given name differs entirely with no initial/abbreviation explanation
- Surname differs and no reasonable transliteration variant applies

Return ONLY a JSON object:
{{"equivalent": bool, "confidence": 0.0–1.0, "fuzzy": bool, "reason": "one-line explanation"}}

fuzzy=true when they match but not exactly (initials, order, honorifics, transliteration)."""


class GroqClient:
    """LLMClient backed by Groq's OpenAI-compatible vision API (Llama 4 multimodal).

    Same retry/backoff + error-classification contract as GeminiClient. Uses httpx
    (already a dependency) against the chat-completions endpoint with JSON-mode output;
    malformed JSON self-corrects once, transient failures (429/timeout/5xx) retry.
    """

    def __init__(self, api_key: str, model: str = "meta-llama/llama-4-scout-17b-16e-instruct",
                 timeout_s: int = 60, max_retries: int = 3,
                 backoff_base_s: float = 1.0, backoff_cap_s: float = 30.0):
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.backoff_base_s = backoff_base_s
        self.backoff_cap_s = backoff_cap_s
        self._sleep = asyncio.sleep

    @staticmethod
    def _parse_retry_delay(detail: str) -> float | None:
        """Honor a returned retry delay (Groq returns 'try again in 12.3s')."""
        m = re.search(r"(?:retry|try again)\D*?(\d+(?:\.\d+)?)\s*s", detail, re.I)
        return float(m.group(1)) if m else None

    def _image_content(self, doc: DocumentInput) -> dict:
        if not doc.file_bytes:
            raise LLMError(LLMErrorKind.PROVIDER_ERROR,
                           f"document {doc.file_id!r} has no file_bytes", retryable=False)
        b64 = base64.b64encode(doc.file_bytes).decode("ascii")
        mime = doc.mime_type or "image/jpeg"
        return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}

    @staticmethod
    def _schema_hint(schema: type[BaseModel]) -> str:
        return ("Return a JSON object with these keys when present: "
                + ", ".join(schema.model_fields)
                + ". Use [] for empty lists and null for unknown values — never an empty string.")

    @staticmethod
    def _coerce(obj):
        """Cheap first pass over Groq's non-schema-bound JSON: recursively drop
        empty-string values so schema defaults apply. The real, type-aware coercion
        guarantee (empty-list, scalar→list, '₹1,500'→1500, date normalization) lives
        in the extraction schemas (CoercibleModel) and covers every provider; this
        stays as a lightweight belt-and-suspenders pass."""
        if isinstance(obj, dict):
            return {k: GroqClient._coerce(v) for k, v in obj.items() if v != ""}
        if isinstance(obj, list):
            return [GroqClient._coerce(x) for x in obj]
        return obj

    async def _generate(self, content: list) -> str:
        body = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": content}],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(GROQ_URL, headers=headers, json=body)
        except httpx.TimeoutException:
            raise LLMError(LLMErrorKind.TIMEOUT, "groq timeout", retryable=True)
        except Exception as e:
            raise LLMError(LLMErrorKind.PROVIDER_ERROR, str(e), retryable=True)

        if resp.status_code == 429:
            raise LLMError(LLMErrorKind.RATE_LIMIT, resp.text, retryable=True)
        if resp.status_code >= 500:
            raise LLMError(LLMErrorKind.PROVIDER_ERROR, f"{resp.status_code}: {resp.text}", retryable=True)
        if resp.status_code != 200:
            raise LLMError(LLMErrorKind.PROVIDER_ERROR, f"{resp.status_code}: {resp.text}", retryable=False)

        try:
            text = resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as e:
            raise LLMError(LLMErrorKind.PROVIDER_ERROR, f"unexpected response shape: {e}", retryable=True)
        if not text:
            raise LLMError(LLMErrorKind.PROVIDER_ERROR, "empty response text", retryable=True)
        return text

    async def _call(self, content: list, out_model: type[BaseModel], feedback: str = ""):
        """Retry transient failures (429/timeout/5xx) with backoff; raise the rest."""
        for attempt in range(self.max_retries + 1):
            try:
                return await self._attempt(content, out_model, feedback)
            except LLMError as e:
                if not e.retryable or attempt == self.max_retries:
                    raise
                delay = self._parse_retry_delay(e.detail) or self.backoff_base_s * (2 ** attempt)
                await self._sleep(min(delay, self.backoff_cap_s))

    async def _attempt(self, content: list, out_model: type[BaseModel], feedback: str):
        """One call; self-corrects malformed JSON once; classifies failures."""
        last_err = None
        for _ in range(2):
            msg = content + ([{"type": "text", "text": feedback}] if feedback else [])
            try:
                text = await self._generate(msg)
                return out_model.model_validate(self._coerce(json.loads(text)))
            except (json.JSONDecodeError, ValidationError) as e:
                last_err = e
                feedback = f"Previous output was invalid: {e}. Return ONLY valid JSON."
            except LLMError:
                raise
        raise LLMError(LLMErrorKind.SCHEMA_INVALID, str(last_err))

    async def classify_document(self, doc: DocumentInput) -> DocClassification:
        content = [{"type": "text", "text": CLASSIFY_PROMPT}, self._image_content(doc)]
        return await self._call(content, DocClassification)

    async def extract(self, doc: DocumentInput, schema: type[BaseModel]) -> ExtractionOutput:
        content = [{"type": "text", "text": f"{EXTRACT_PROMPT}\n{self._schema_hint(schema)}"},
                   self._image_content(doc)]
        data = await self._call(content, schema)
        present = {k for k, v in data.model_dump().items() if v not in (None, [], "")}
        all_fields = set(schema.model_fields)
        return ExtractionOutput(data=data,
                                field_confidence={k: 0.85 for k in present},
                                unextracted_fields=sorted(all_fields - present),
                                source="vision")

    async def names_equivalent(self, a: str, b: str) -> NameMatch:
        content = [{"type": "text", "text": NAME_PROMPT.format(a=a, b=b)}]
        return await self._call(content, NameMatch)
