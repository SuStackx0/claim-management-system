from __future__ import annotations
import re
from datetime import date, datetime
from typing import Any, get_args, get_origin
from pydantic import BaseModel, Field, model_validator

# ── coercion primitives ─────────────────────────────────────────────────────
# LLM JSON output (esp. Groq's non-schema-bound JSON mode) is type-sloppy: it
# emits "" for empty lists, a bare scalar where a list is expected, amounts as
# "₹1,500", and dates in assorted Indian formats. We normalize at the SCHEMA
# boundary (mode="before") so the guarantee holds for every provider — Groq,
# Gemini, and any future client — not just one client's _coerce pass.
#
# Every coercer is a no-op on already-correct values, so the deterministic
# mock/eval path (which feeds clean fixtures through these same schemas) is
# unaffected.

_NULLISH = {"", "n/a", "na", "-", "--", "nil", "null", "none", "not available",
            "not applicable", "unknown"}

_DATE_FORMATS = (
    "%Y-%m-%d",      # 2024-11-01 (canonical — checked first, so clean data is a no-op)
    "%d-%m-%Y", "%d/%m/%Y",          # 01-11-2024, 01/11/2024
    "%Y/%m/%d",                       # 2024/11/01
    "%d-%b-%Y", "%d %b %Y",          # 01-Nov-2024, 01 Nov 2024
    "%d-%B-%Y", "%d %B %Y",          # 01-November-2024
    "%d.%m.%Y",                       # 01.11.2024
    "%b %d, %Y", "%B %d, %Y",        # Nov 1, 2024
)


def _is_nullish(v: Any) -> bool:
    return isinstance(v, str) and v.strip().lower() in _NULLISH


def coerce_amount(v: Any) -> Any:
    """'₹1,500' / 'Rs 1500' / '1500.0' / '1,500.50' → int 1500. Clean ints pass through."""
    if isinstance(v, bool):          # bool is an int subclass — never an amount
        return v
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(round(v))
    if isinstance(v, str):
        if _is_nullish(v):
            return None
        # strip currency symbols, codes, thousands separators, whitespace
        cleaned = re.sub(r"[^\d.\-]", "", v.replace(",", ""))
        # A symbol like "Rs." leaves a spurious leading dot ("Rs. 1,500.50" → ".1500.50"),
        # and multiple dots can survive. Treat only the LAST dot as the decimal separator:
        # drop all earlier dots (they were never decimals) so the value parses correctly.
        sign = "-" if cleaned.startswith("-") else ""
        digits = cleaned.lstrip("-")
        if "." in digits:
            head, _, frac = digits.rpartition(".")
            head = head.replace(".", "")
            # An empty head means the dot was a spurious symbol artefact ("Rs.1500"
            # → ".1500"), not a real decimal — fold the digits into the integer part.
            digits = (head + frac) if head == "" else (head + "." + frac)
        cleaned = sign + digits
        if cleaned in ("", "-", ".", "-.", "-"):
            return None
        try:
            return int(round(float(cleaned)))
        except ValueError:
            return v                  # let pydantic raise a precise error
    return v


def coerce_date(v: Any) -> Any:
    """Normalize Indian-format date strings to ISO 'YYYY-MM-DD'. Clean ISO is a no-op."""
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10] if isinstance(v, datetime) else v.isoformat()
    if isinstance(v, str):
        s = v.strip()
        if _is_nullish(s):
            return None
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(s, fmt).date().isoformat()
            except ValueError:
                continue
        return s                      # unrecognized — leave as-is (field is str | None)
    return v


def coerce_scalar(v: Any) -> Any:
    """null-ish string → None; collapse a single-element list to its scalar."""
    if _is_nullish(v):
        return None
    if isinstance(v, list):
        non_null = [x for x in v if not _is_nullish(x) and x is not None]
        if not non_null:
            return None
        if len(non_null) == 1:
            return non_null[0]
    return v


def coerce_list(v: Any) -> Any:
    """'' / null-ish → []; a bare scalar → [scalar]; drop null-ish elements from a list."""
    if v is None or _is_nullish(v):
        return []
    if isinstance(v, list):
        return [x for x in v if not _is_nullish(x) and x is not None]
    return [v]                        # 'Paracetamol' → ['Paracetamol']


def _field_is_list(annotation: Any) -> bool:
    if get_origin(annotation) is list:
        return True
    # list[...] | None
    return any(get_origin(a) is list for a in get_args(annotation))


def _field_inner_type(annotation: Any) -> type | None:
    """The non-None concrete type, e.g. int for 'int | None', LineItem for 'list[LineItem]'."""
    args = [a for a in get_args(annotation) if a is not type(None)]
    base = args[0] if args else annotation
    if get_origin(base) is list:
        inner = [a for a in get_args(base) if a is not type(None)]
        return inner[0] if inner else None
    return base


class CoercibleModel(BaseModel):
    """Base for extraction schemas. A single mode='before' validator normalizes
    every field by its declared type, so malformed LLM output NEVER raises and
    NEVER silently loses data. No-op on clean input."""

    @model_validator(mode="before")
    @classmethod
    def _coerce_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out: dict[str, Any] = {}
        for key, value in data.items():
            field = cls.model_fields.get(key)
            if field is None:
                out[key] = value                      # unknown key — leave for pydantic
                continue
            ann = field.annotation
            inner = _field_inner_type(ann)
            if _field_is_list(ann):
                items = coerce_list(value)
                # recurse into nested coercible models (e.g. LineItem amounts)
                if isinstance(inner, type) and issubclass(inner, CoercibleModel):
                    items = [inner._coerce_fields(x) if isinstance(x, dict) else x
                             for x in items]
                out[key] = items
            elif inner is int:
                out[key] = coerce_amount(value)
            elif key in ("date", "report_date") or (isinstance(key, str) and key.endswith("_date")):
                out[key] = coerce_date(value)
            else:
                out[key] = coerce_scalar(value)
        return out


class LineItem(CoercibleModel):
    description: str
    amount: int
    quantity: int = 1

class PrescriptionData(CoercibleModel):
    doctor_name: str | None = None
    doctor_registration: str | None = None
    patient_name: str | None = None
    date: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    medicines: list[str] = Field(default_factory=list)
    tests_ordered: list[str] = Field(default_factory=list)

class BillData(CoercibleModel):
    hospital_name: str | None = None
    patient_name: str | None = None
    date: str | None = None
    bill_number: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    total: int | None = None

class LabReportData(CoercibleModel):
    lab_name: str | None = None
    patient_name: str | None = None
    test_name: str | None = None
    report_date: str | None = None

class PharmacyBillData(CoercibleModel):
    pharmacy_name: str | None = None
    patient_name: str | None = None
    date: str | None = None
    total: int | None = None

SCHEMA_BY_DOCTYPE = {
    "PRESCRIPTION": PrescriptionData,
    "HOSPITAL_BILL": BillData,
    "PHARMACY_BILL": PharmacyBillData,
    "LAB_REPORT": LabReportData,
    "DIAGNOSTIC_REPORT": LabReportData,
    "DISCHARGE_SUMMARY": BillData,
    "DENTAL_REPORT": PrescriptionData,
}
