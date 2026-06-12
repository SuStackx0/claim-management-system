# Claims Processing Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Plum claims adjudication system — FastAPI pipeline of 7 agents with trace-first observability, Gemini/Mock LLM layer, eval runner for the 12 test cases, and a Streamlit UI.

**Architecture:** Deterministic orchestrator runs 7 agents in fixed order with early exits; LLM only for doc classification/extraction/fuzzy names; all policy/money logic is pure code reading `policy_terms.json`. Decision is computed from the accumulated trace. Spec: `docs/superpowers/specs/2026-06-12-claims-pipeline-design.md`; diagrams: `...-diagrams.md`.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, pytest + pytest-asyncio, stdlib sqlite3, google-genai, Streamlit, Render.

> **PROCESS RULE (overrides default commit steps):** After completing each task, STOP. Present the work + test output to Sumanth for approval. **He makes the git commit himself.** Do not run `git commit`. Only proceed to the next task after he confirms.

**Money convention:** all amounts are `int` rupees. `round()` only at the final payable computation.

---

## File Structure

```
app/
  __init__.py
  config.py                 # env settings (LLM_PROVIDER, GEMINI_API_KEY, DB_PATH, paths)
  models/
    __init__.py
    domain.py               # enums, DocumentInput, ClaimSubmission, Decision, ClaimOutcome
    extraction.py           # PrescriptionData, BillData(+LineItem), LabReportData, PharmacyBillData
    policy.py               # Policy pydantic models (mirrors policy_terms.json)
  core/
    __init__.py
    errors.py               # ErrorCode, AgentError, AgentFailure
    trace.py                # PolicyCheck, ConfidenceEntry, StepResult, ClaimTrace
    context.py              # ClaimContext
    policy_loader.py        # load+validate policy, rule(ref) JSON-path lookup, PolicyView
    matching.py             # deterministic keyword tables: conditions, exclusions, procedures
    orchestrator.py         # fixed-order pipeline, fatal vs degradable handling
    repository.py           # SQLite persistence
  llm/
    __init__.py
    base.py                 # LLMClient protocol, LLMError, DocClassification, NameMatch
    mock_client.py          # fixture-driven client (also used by tests)
    gemini_client.py        # google-genai, JSON-schema mode, timeout+retry
  agents/
    __init__.py
    base.py                 # Agent ABC (name, fatal, run)
    intake.py
    doc_verifier.py
    extraction.py
    consistency.py
    adjudicator.py          # pure code: checks + line items + financial math
    fraud.py
    aggregator.py
  api/
    __init__.py
    schemas.py              # request/response DTOs
    main.py                 # FastAPI app, routers, startup wiring
  eval/
    __init__.py
    runner.py               # run 12 cases, assert expectations, render eval_report.md
    __main__.py             # python -m app.eval
ui/
  streamlit_app.py          # thin HTTP client: Submit / Review / Eval pages
scripts/
  generate_sample_docs.py   # PIL-rendered mock document images
tests/
  conftest.py               # policy fixture, mock LLM fixture, submission builders
  test_models.py
  test_policy_loader.py
  test_trace.py
  test_intake.py
  test_doc_verifier.py
  test_extraction.py
  test_consistency.py
  test_adjudicator_checks.py
  test_adjudicator_financial.py
  test_fraud.py
  test_aggregator.py
  test_orchestrator.py
  test_repository.py
  test_api.py
  test_eval_cases.py        # all 12 test cases, parametrized
data/
  policy_terms.json         # moved from repo root
  test_cases.json
requirements.txt
render.yaml
README.md
```

**Documented assumptions (carry into architecture doc):**
1. Category `sub_limit` caps the matching service line item (e.g. "Consultation Fee" ≤ ₹2,000), not the whole bill — otherwise TC010 (₹4,500 consultation claim, expected APPROVED) contradicts TC008. Over-limit lines are capped, producing PARTIAL.
2. Pre-authorization arrives as `pre_authorization_id` on the submission; absent ⇒ not obtained.
3. Condition/exclusion matching uses deterministic keyword tables keyed by the policy JSON's own keys (e.g. `diabetes`, `Obesity and weight loss programs`). Keywords are domain vocabulary, not policy values; the *rules* (days, lists, limits) always come from the JSON.
4. Early document failures return HTTP 200 with `status: "STOPPED"` — a domain outcome, not a server error.
5. Aggregator: low confidence appends a manual-review *recommendation*; it never flips an APPROVED to MANUAL_REVIEW (TC011 expects APPROVED with low confidence). Only fraud signals produce MANUAL_REVIEW status.

---

### Task 1: Scaffolding, config, data, test harness

**Files:**
- Create: `requirements.txt`, `app/__init__.py`, `app/config.py`, `pytest.ini`, `tests/conftest.py` (minimal), `.gitignore`
- Move: `policy_terms.json`, `test_cases.json` → `data/` (use `git mv`)

- [ ] **Step 1: Create venv and requirements**

```
# requirements.txt
fastapi==0.115.*
uvicorn[standard]==0.34.*
pydantic==2.*
python-multipart==0.0.*
google-genai==1.*
streamlit==1.*
httpx==0.28.*
pytest==8.*
pytest-asyncio==0.25.*
```

Run: `python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt`
Expected: installs cleanly.

- [ ] **Step 2: Move data files**

Run: `mkdir -p data && git mv policy_terms.json test_cases.json data/`

- [ ] **Step 3: Write `app/config.py`**

```python
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")  # "gemini" | "mock"
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    db_path: str = os.getenv("DB_PATH", str(ROOT / "claims.db"))
    policy_path: str = os.getenv("POLICY_PATH", str(ROOT / "data" / "policy_terms.json"))
    test_cases_path: str = os.getenv("TEST_CASES_PATH", str(ROOT / "data" / "test_cases.json"))
    pipeline_version: str = "1.0.0"

settings = Settings()
```

- [ ] **Step 4: pytest.ini + smoke test**

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

```python
# tests/conftest.py
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
```

```python
# tests/test_models.py (smoke for now; grows in Task 2)
def test_data_files_load(policy_dict, test_cases):
    assert policy_dict["policy_id"] == "PLUM_GHI_2024"
    assert len(test_cases) == 12
```

- [ ] **Step 5: Run** `pytest -q` → Expected: `1 passed`.

- [ ] **Step 6: STOP — present to Sumanth for approval; he commits (`chore: scaffold project, move policy data, test harness`).**

---

### Task 2: Domain models

**Files:**
- Create: `app/models/__init__.py`, `app/models/domain.py`, `app/models/extraction.py`
- Test: `tests/test_models.py` (extend)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models.py (append)
from datetime import date
from app.models.domain import ClaimSubmission, DocumentInput, DocType, Readability, DecisionStatus

def test_submission_parses_test_case_input(test_cases):
    tc4 = next(c for c in test_cases if c["case_id"] == "TC004")
    sub = ClaimSubmission.model_validate(tc4["input"])
    assert sub.member_id == "EMP001"
    assert sub.treatment_date == date(2024, 11, 1)
    assert sub.documents[0].actual_type == DocType.PRESCRIPTION
    assert sub.documents[0].content["doctor_name"] == "Dr. Arun Sharma"
    assert sub.ytd_claims_amount == 5000
    assert sub.simulate_component_failure is False

def test_submission_parses_every_test_case(test_cases):
    for case in test_cases:
        ClaimSubmission.model_validate(case["input"])  # must not raise

def test_quality_hint(test_cases):
    tc2 = next(c for c in test_cases if c["case_id"] == "TC002")
    sub = ClaimSubmission.model_validate(tc2["input"])
    assert sub.documents[1].quality == Readability.UNREADABLE
```

- [ ] **Step 2: Run** `pytest tests/test_models.py -q` → Expected: FAIL (`ModuleNotFoundError: app.models`).

- [ ] **Step 3: Implement `app/models/domain.py`**

```python
from __future__ import annotations
from datetime import date
from enum import StrEnum
from pydantic import BaseModel, Field

class DocType(StrEnum):
    PRESCRIPTION = "PRESCRIPTION"
    HOSPITAL_BILL = "HOSPITAL_BILL"
    PHARMACY_BILL = "PHARMACY_BILL"
    LAB_REPORT = "LAB_REPORT"
    DIAGNOSTIC_REPORT = "DIAGNOSTIC_REPORT"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    DENTAL_REPORT = "DENTAL_REPORT"
    UNKNOWN = "UNKNOWN"

class Readability(StrEnum):
    GOOD = "GOOD"
    PARTIAL = "PARTIAL"
    UNREADABLE = "UNREADABLE"

class DecisionStatus(StrEnum):
    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"

class DocumentInput(BaseModel):
    file_id: str
    file_name: str | None = None
    # test-path hints (eval injects these); real path fills them via LLM
    actual_type: DocType | None = None
    quality: Readability | None = None
    patient_name_on_doc: str | None = None
    content: dict | None = None
    # real-path payload
    file_bytes: bytes | None = None
    mime_type: str | None = None

class ClaimHistoryItem(BaseModel):
    claim_id: str
    date: date
    amount: int
    provider: str | None = None

class ClaimSubmission(BaseModel):
    member_id: str
    policy_id: str
    claim_category: str
    treatment_date: date
    claimed_amount: int
    hospital_name: str | None = None
    ytd_claims_amount: int = 0
    pre_authorization_id: str | None = None
    claims_history: list[ClaimHistoryItem] = Field(default_factory=list)
    simulate_component_failure: bool = False
    documents: list[DocumentInput]

class Member(BaseModel):
    member_id: str
    name: str
    date_of_birth: date
    gender: str
    relationship: str
    join_date: date | None = None
    primary_member_id: str | None = None
    dependents: list[str] = Field(default_factory=list)

class Decision(BaseModel):
    status: DecisionStatus
    approved_amount: int = 0
    reasons: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    member_message: str = ""
    ops_summary: str = ""

class ClaimOutcome(BaseModel):
    claim_id: str
    status: str  # "COMPLETED" | "STOPPED"
    decision: Decision | None = None
    member_message: str = ""
    trace: dict = Field(default_factory=dict)
```

- [ ] **Step 4: Implement `app/models/extraction.py`**

```python
from __future__ import annotations
from pydantic import BaseModel, Field

class LineItem(BaseModel):
    description: str
    amount: int
    quantity: int = 1

class PrescriptionData(BaseModel):
    doctor_name: str | None = None
    doctor_registration: str | None = None
    patient_name: str | None = None
    date: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    medicines: list[str] = Field(default_factory=list)
    tests_ordered: list[str] = Field(default_factory=list)

class BillData(BaseModel):
    hospital_name: str | None = None
    patient_name: str | None = None
    date: str | None = None
    bill_number: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    total: int | None = None

class LabReportData(BaseModel):
    lab_name: str | None = None
    patient_name: str | None = None
    test_name: str | None = None
    report_date: str | None = None

class PharmacyBillData(BaseModel):
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
```

`app/models/__init__.py`: empty file.

- [ ] **Step 5: Run** `pytest tests/test_models.py -q` → Expected: all PASS.

- [ ] **Step 6: STOP — present to Sumanth; he commits (`feat: domain and extraction models`).**

---

### Task 3: Policy models + loader

**Files:**
- Create: `app/models/policy.py`, `app/core/__init__.py`, `app/core/policy_loader.py`
- Test: `tests/test_policy_loader.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_policy_loader.py
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

def test_member_lookup(loader):
    m = loader.member("EMP001")
    assert m.name == "Rajesh Kumar"
    assert loader.member("NOPE") is None

def test_dependents_of(loader):
    names = [d.name for d in loader.dependents_of("EMP001")]
    assert "Sunita Kumar" in names and "Arjun Kumar" in names
```

- [ ] **Step 2: Run** `pytest tests/test_policy_loader.py -q` → Expected: FAIL (module missing).

- [ ] **Step 3: Implement `app/models/policy.py`**

```python
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from app.models.domain import Member

class Coverage(BaseModel):
    model_config = ConfigDict(extra="allow")
    sum_insured_per_employee: int
    annual_opd_limit: int
    per_claim_limit: int

class CategoryRules(BaseModel):
    model_config = ConfigDict(extra="allow")
    sub_limit: int
    copay_percent: int = 0
    network_discount_percent: int = 0
    requires_prescription: bool = False
    requires_pre_auth: bool = False
    pre_auth_threshold: int | None = None
    high_value_tests_requiring_pre_auth: list[str] = Field(default_factory=list)
    covered: bool = True
    covered_procedures: list[str] = Field(default_factory=list)
    excluded_procedures: list[str] = Field(default_factory=list)
    covered_items: list[str] = Field(default_factory=list)
    excluded_items: list[str] = Field(default_factory=list)

class WaitingPeriods(BaseModel):
    initial_waiting_period_days: int
    pre_existing_conditions_days: int
    specific_conditions: dict[str, int]

class Exclusions(BaseModel):
    model_config = ConfigDict(extra="allow")
    conditions: list[str]
    dental_exclusions: list[str] = Field(default_factory=list)
    vision_exclusions: list[str] = Field(default_factory=list)

class SubmissionRules(BaseModel):
    deadline_days_from_treatment: int
    minimum_claim_amount: int
    currency: str = "INR"

class FraudThresholds(BaseModel):
    same_day_claims_limit: int
    monthly_claims_limit: int
    high_value_claim_threshold: int
    auto_manual_review_above: int
    fraud_score_manual_review_threshold: float

class Policy(BaseModel):
    model_config = ConfigDict(extra="allow")
    policy_id: str
    coverage: Coverage
    opd_categories: dict[str, CategoryRules]
    waiting_periods: WaitingPeriods
    exclusions: Exclusions
    network_hospitals: list[str]
    submission_rules: SubmissionRules
    document_requirements: dict[str, dict[str, list[str]]]
    fraud_thresholds: FraudThresholds
    members: list[Member]

class PolicyView(BaseModel):
    """Everything the pipeline needs for one claim category."""
    category: str
    rules: CategoryRules
    required_docs: list[str]
    optional_docs: list[str]
```

- [ ] **Step 4: Implement `app/core/policy_loader.py`**

```python
from __future__ import annotations
import json
from app.models.domain import Member
from app.models.policy import Policy, PolicyView

class PolicyLoader:
    def __init__(self, policy: Policy, raw: dict):
        self.policy = policy
        self._raw = raw
        self._members = {m.member_id: m for m in policy.members}

    @classmethod
    def load(cls, path: str) -> "PolicyLoader":
        with open(path) as f:
            raw = json.load(f)
        return cls(Policy.model_validate(raw), raw)

    def rule(self, ref: str):
        """JSON-path lookup into the raw policy; ref is the trace's rule_ref."""
        node = self._raw
        for part in ref.split("."):
            if not isinstance(node, dict) or part not in node:
                raise KeyError(f"rule_ref not found in policy: {ref}")
            node = node[part]
        return node

    def view(self, category: str) -> PolicyView:
        key = category.lower()
        if key not in self.policy.opd_categories:
            raise KeyError(f"unknown category: {category}")
        reqs = self.policy.document_requirements.get(category.upper(), {})
        return PolicyView(
            category=category.upper(),
            rules=self.policy.opd_categories[key],
            required_docs=reqs.get("required", []),
            optional_docs=reqs.get("optional", []),
        )

    def member(self, member_id: str) -> Member | None:
        return self._members.get(member_id)

    def dependents_of(self, member_id: str) -> list[Member]:
        m = self._members.get(member_id)
        if not m:
            return []
        return [self._members[d] for d in m.dependents if d in self._members]
```

- [ ] **Step 5: Run** `pytest tests/test_policy_loader.py -q` → Expected: all PASS.

- [ ] **Step 6: STOP — present to Sumanth; he commits (`feat: policy models and loader with rule_ref lookup`).**

---

### Task 4: Errors, trace, confidence ledger, context

**Files:**
- Create: `app/core/errors.py`, `app/core/trace.py`, `app/core/context.py`
- Test: `tests/test_trace.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_trace.py
from app.core.trace import ClaimTrace, StepResult, StepStatus, PolicyCheck, CheckResult, ConfidenceEntry
from app.core.errors import AgentError, ErrorCode

def make_step(status=StepStatus.PASS, entries=None):
    return StepResult(step="X", agent="XAgent", status=status,
                      confidence_entries=entries or [])

def test_confidence_starts_at_one():
    t = ClaimTrace(claim_id="C1")
    assert t.confidence() == 1.0

def test_confidence_multiplies():
    t = ClaimTrace(claim_id="C1")
    t.append(make_step(entries=[ConfidenceEntry(factor=0.9, reason="partial readability")]))
    t.append(make_step(status=StepStatus.SKIPPED,
                       entries=[ConfidenceEntry(factor=0.7, reason="FraudAgent failed")]))
    assert abs(t.confidence() - 0.63) < 1e-9

def test_trace_serializes_with_rule_refs():
    t = ClaimTrace(claim_id="C1")
    t.append(StepResult(step="ADJUDICATION", agent="AdjudicatorAgent", status=StepStatus.PASS,
        checks=[PolicyCheck(check="WAITING_PERIOD", result=CheckResult.FAIL,
                            rule_ref="waiting_periods.specific_conditions.diabetes",
                            detail={"eligible_from": "2024-11-30"})]))
    d = t.model_dump()
    assert d["steps"][0]["checks"][0]["rule_ref"].endswith("diabetes")

def test_agent_error_carries_member_message():
    e = AgentError(code=ErrorCode.WRONG_DOCUMENT_TYPE, message="dev detail",
                   member_message="You uploaded X, we need Y")
    assert "uploaded" in e.member_message
```

- [ ] **Step 2: Run** `pytest tests/test_trace.py -q` → Expected: FAIL.

- [ ] **Step 3: Implement `app/core/errors.py`**

```python
from __future__ import annotations
from enum import StrEnum
from pydantic import BaseModel, Field

class ErrorCode(StrEnum):
    MEMBER_NOT_FOUND = "MEMBER_NOT_FOUND"
    POLICY_INACTIVE = "POLICY_INACTIVE"
    AMOUNT_BELOW_MINIMUM = "AMOUNT_BELOW_MINIMUM"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    INVALID_CATEGORY = "INVALID_CATEGORY"
    MISSING_REQUIRED_DOCUMENT = "MISSING_REQUIRED_DOCUMENT"
    WRONG_DOCUMENT_TYPE = "WRONG_DOCUMENT_TYPE"
    DOCUMENT_UNREADABLE = "DOCUMENT_UNREADABLE"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    PATIENT_MISMATCH = "PATIENT_MISMATCH"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class AgentError(BaseModel):
    code: ErrorCode
    message: str                      # for ops/devs
    member_message: str = ""          # what the member sees; specific + actionable
    detail: dict = Field(default_factory=dict)

class AgentFailure(Exception):
    """Raised by agents; orchestrator converts to StepResult and routes fatal/degrade."""
    def __init__(self, error: AgentError):
        self.error = error
        super().__init__(error.message)
```

- [ ] **Step 4: Implement `app/core/trace.py`**

```python
from __future__ import annotations
from datetime import datetime, timezone
from enum import StrEnum
from pydantic import BaseModel, Field
from app.core.errors import AgentError
from app.models.domain import Decision

class StepStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    DEGRADED = "DEGRADED"
    SKIPPED = "SKIPPED"

class CheckResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIPPED = "SKIPPED"

class PolicyCheck(BaseModel):
    check: str
    result: CheckResult
    rule_ref: str | None = None       # JSON path into policy_terms.json
    detail: dict = Field(default_factory=dict)

class ConfidenceEntry(BaseModel):
    factor: float
    reason: str

class StepResult(BaseModel):
    step: str
    agent: str
    status: StepStatus
    checks: list[PolicyCheck] = Field(default_factory=list)
    confidence_entries: list[ConfidenceEntry] = Field(default_factory=list)
    error: AgentError | None = None
    duration_ms: int = 0

class ClaimTrace(BaseModel):
    claim_id: str
    pipeline_version: str = "1.0.0"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    steps: list[StepResult] = Field(default_factory=list)
    decision: Decision | None = None

    def append(self, result: StepResult) -> None:
        self.steps.append(result)

    def confidence(self) -> float:
        c = 1.0
        for s in self.steps:
            for e in s.confidence_entries:
                c *= e.factor
        return max(0.0, min(1.0, c))

    def confidence_ledger(self) -> list[ConfidenceEntry]:
        return [e for s in self.steps for e in s.confidence_entries]
```

- [ ] **Step 5: Implement `app/core/context.py`**

```python
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from app.core.policy_loader import PolicyLoader
from app.core.trace import ClaimTrace
from app.models.domain import ClaimSubmission, Member
from app.models.policy import PolicyView

class DocVerdict(BaseModel):
    file_id: str
    file_name: str | None = None
    detected_type: str
    readability: str
    confidence: float = 1.0

class ExtractionRecord(BaseModel):
    file_id: str
    doc_type: str
    data: dict = Field(default_factory=dict)      # validated model, dumped
    field_confidence: dict[str, float] = Field(default_factory=dict)
    unextracted_fields: list[str] = Field(default_factory=list)
    source: str = "provided"                       # "vision" | "provided"
    degraded: bool = False

class ConsistencyFinding(BaseModel):
    check: str
    severity: str                                  # "FATAL" | "WARNING"
    detail: dict = Field(default_factory=dict)

class LineItemVerdict(BaseModel):
    description: str
    amount: int
    eligible_amount: int
    verdict: str                                   # "APPROVED" | "REJECTED" | "CAPPED"
    reason: str
    rule_ref: str | None = None

class FraudSignal(BaseModel):
    signal: str
    detail: dict = Field(default_factory=dict)
    rule_ref: str | None = None

class ClaimContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    submission: ClaimSubmission
    loader: PolicyLoader
    trace: ClaimTrace
    member: Member | None = None
    policy_view: PolicyView | None = None
    doc_verdicts: list[DocVerdict] = Field(default_factory=list)
    extractions: list[ExtractionRecord] = Field(default_factory=list)
    findings: list[ConsistencyFinding] = Field(default_factory=list)
    line_verdicts: list[LineItemVerdict] = Field(default_factory=list)
    fraud_signals: list[FraudSignal] = Field(default_factory=list)
    financial: dict = Field(default_factory=dict)  # breakdown: base, discount, copay, payable
    blocking_reasons: list[str] = Field(default_factory=list)  # e.g. WAITING_PERIOD
```

- [ ] **Step 6: Run** `pytest tests/test_trace.py -q` → Expected: all PASS. Also `pytest -q` (whole suite green).

- [ ] **Step 7: STOP — present to Sumanth; he commits (`feat: trace, confidence ledger, errors, claim context`).**

---

### Task 5: LLM layer — protocol, MockClient

**Files:**
- Create: `app/llm/__init__.py`, `app/llm/base.py`, `app/llm/mock_client.py`
- Test: `tests/test_extraction.py` (LLM contract part)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_extraction.py
import pytest
from app.llm.base import LLMError, LLMErrorKind
from app.llm.mock_client import MockClient
from app.models.domain import DocumentInput, DocType
from app.models.extraction import BillData

@pytest.fixture
def mock_llm():
    return MockClient()

async def test_mock_classifies_by_filename(mock_llm):
    doc = DocumentInput(file_id="F1", file_name="dr_sharma_prescription.jpg")
    c = await mock_llm.classify_document(doc)
    assert c.detected_type == "PRESCRIPTION"
    assert c.readability == "GOOD"

async def test_mock_extracts_fixture(mock_llm):
    doc = DocumentInput(file_id="F1", file_name="sample_bill.jpg")
    r = await mock_llm.extract(doc, BillData)
    assert isinstance(r.data, BillData)
    assert r.source == "vision"

async def test_mock_failure_injection(mock_llm):
    mock_llm.fail_next = LLMErrorKind.TIMEOUT
    doc = DocumentInput(file_id="F1", file_name="x.jpg")
    with pytest.raises(LLMError) as ei:
        await mock_llm.extract(doc, BillData)
    assert ei.value.kind == LLMErrorKind.TIMEOUT

async def test_mock_names_equivalent(mock_llm):
    assert (await mock_llm.names_equivalent("Rajesh Kumar", "R. Kumar")).equivalent
    assert not (await mock_llm.names_equivalent("Rajesh Kumar", "Arjun Mehta")).equivalent
```

- [ ] **Step 2: Run** `pytest tests/test_extraction.py -q` → Expected: FAIL.

- [ ] **Step 3: Implement `app/llm/base.py`**

```python
from __future__ import annotations
from enum import StrEnum
from typing import Protocol, TypeVar
from pydantic import BaseModel, Field

M = TypeVar("M", bound=BaseModel)

class LLMErrorKind(StrEnum):
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    PROVIDER_ERROR = "PROVIDER_ERROR"

class LLMError(Exception):
    def __init__(self, kind: LLMErrorKind, detail: str = "", retryable: bool = False):
        self.kind, self.detail, self.retryable = kind, detail, retryable
        super().__init__(f"{kind}: {detail}")

class DocClassification(BaseModel):
    detected_type: str
    readability: str = "GOOD"
    confidence: float = 1.0

class ExtractionOutput(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    data: BaseModel
    field_confidence: dict[str, float] = Field(default_factory=dict)
    unextracted_fields: list[str] = Field(default_factory=list)
    source: str = "vision"

class NameMatch(BaseModel):
    equivalent: bool
    confidence: float = 1.0
    fuzzy: bool = False   # True when not an exact match (docks confidence)

class LLMClient(Protocol):
    async def classify_document(self, doc) -> DocClassification: ...
    async def extract(self, doc, schema: type[M]) -> ExtractionOutput: ...
    async def names_equivalent(self, a: str, b: str) -> NameMatch: ...
```

- [ ] **Step 4: Implement `app/llm/mock_client.py`**

Deterministic stand-in: classifies from filename keywords, extracts canned fixtures, fuzzy-matches names by token overlap (same logic the ConsistencyAgent falls back to). `fail_next` lets tests inject failures.

```python
from __future__ import annotations
from pydantic import BaseModel
from app.llm.base import DocClassification, ExtractionOutput, LLMError, LLMErrorKind, NameMatch

_TYPE_KEYWORDS = [
    ("prescription", "PRESCRIPTION"), ("rx", "PRESCRIPTION"),
    ("pharmacy", "PHARMACY_BILL"),
    ("lab", "LAB_REPORT"), ("report", "LAB_REPORT"),
    ("bill", "HOSPITAL_BILL"), ("invoice", "HOSPITAL_BILL"), ("receipt", "HOSPITAL_BILL"),
]

_FIXTURES: dict[str, dict] = {
    "sample_bill.jpg": {"hospital_name": "City Clinic, Bengaluru", "patient_name": "Rajesh Kumar",
                        "date": "2024-11-01", "total": 1500,
                        "line_items": [{"description": "Consultation Fee", "amount": 1000},
                                       {"description": "CBC Test", "amount": 300},
                                       {"description": "Dengue NS1 Test", "amount": 200}]},
    "sample_prescription.jpg": {"doctor_name": "Dr. Arun Sharma", "doctor_registration": "KA/45678/2015",
                                "patient_name": "Rajesh Kumar", "date": "2024-11-01",
                                "diagnosis": "Viral Fever",
                                "medicines": ["Paracetamol 650mg", "Vitamin C 500mg"]},
}

def name_tokens_match(a: str, b: str) -> tuple[bool, bool]:
    """Returns (equivalent, fuzzy). 'R. Kumar' ≈ 'Rajesh Kumar': surname match + initial match."""
    ta = [t.strip(".").lower() for t in a.split() if t.strip(".")]
    tb = [t.strip(".").lower() for t in b.split() if t.strip(".")]
    if not ta or not tb:
        return False, False
    if ta == tb:
        return True, False
    if ta[-1] != tb[-1]:                      # surname must match
        return False, False
    fa, fb = ta[0], tb[0]
    if fa == fb or fa[0] == fb[0] and (len(fa) == 1 or len(fb) == 1):
        return True, True
    return False, False

class MockClient:
    def __init__(self):
        self.fail_next: LLMErrorKind | None = None

    def _maybe_fail(self):
        if self.fail_next:
            kind, self.fail_next = self.fail_next, None
            raise LLMError(kind, "injected failure", retryable=False)

    async def classify_document(self, doc) -> DocClassification:
        self._maybe_fail()
        name = (doc.file_name or "").lower()
        for kw, dtype in _TYPE_KEYWORDS:
            if kw in name:
                readability = "UNREADABLE" if "blur" in name else "GOOD"
                return DocClassification(detected_type=dtype, readability=readability, confidence=0.95)
        return DocClassification(detected_type="UNKNOWN", readability="GOOD", confidence=0.3)

    async def extract(self, doc, schema: type[BaseModel]) -> ExtractionOutput:
        self._maybe_fail()
        fixture = _FIXTURES.get(doc.file_name or "", {})
        data = schema.model_validate(fixture)
        return ExtractionOutput(data=data,
                                field_confidence={k: 0.95 for k in fixture},
                                unextracted_fields=[], source="vision")

    async def names_equivalent(self, a: str, b: str) -> NameMatch:
        self._maybe_fail()
        eq, fuzzy = name_tokens_match(a, b)
        return NameMatch(equivalent=eq, confidence=0.9 if fuzzy else 1.0, fuzzy=fuzzy)
```

- [ ] **Step 5: Run** `pytest tests/test_extraction.py -q` → Expected: all PASS.

- [ ] **Step 6: STOP — present to Sumanth; he commits (`feat: LLM client protocol and mock client`).**

---

### Task 6: Agent base + IntakeAgent

**Files:**
- Create: `app/agents/__init__.py`, `app/agents/base.py`, `app/agents/intake.py`
- Modify: `tests/conftest.py` (add context builder)
- Test: `tests/test_intake.py`

- [ ] **Step 1: Implement `app/agents/base.py`** (tiny, no test of its own)

```python
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
```

- [ ] **Step 2: Add context builder to `tests/conftest.py`**

```python
# tests/conftest.py (append)
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
```

- [ ] **Step 3: Write failing tests**

```python
# tests/test_intake.py
import pytest
from app.agents.intake import IntakeAgent
from app.core.errors import AgentFailure, ErrorCode
from app.core.trace import StepStatus

async def test_intake_resolves_member_and_view(make_ctx, case_input):
    ctx = make_ctx(case_input("TC004"))
    result = await IntakeAgent().run(ctx)
    assert result.status == StepStatus.PASS
    assert ctx.member.name == "Rajesh Kumar"
    assert ctx.policy_view.rules.copay_percent == 10
    assert any(c.check == "MEMBER_EXISTS" and c.rule_ref == "members" for c in result.checks)

async def test_intake_unknown_member(make_ctx, case_input):
    inp = dict(case_input("TC004")); inp["member_id"] = "EMP999"
    with pytest.raises(AgentFailure) as ei:
        await IntakeAgent().run(make_ctx(inp))
    assert ei.value.error.code == ErrorCode.MEMBER_NOT_FOUND
    assert "EMP999" in ei.value.error.member_message

async def test_intake_below_minimum(make_ctx, case_input):
    inp = dict(case_input("TC004")); inp["claimed_amount"] = 300
    with pytest.raises(AgentFailure) as ei:
        await IntakeAgent().run(make_ctx(inp))
    assert ei.value.error.code == ErrorCode.AMOUNT_BELOW_MINIMUM
    assert "500" in ei.value.error.member_message  # states the minimum

async def test_intake_invalid_category(make_ctx, case_input):
    inp = dict(case_input("TC004")); inp["claim_category"] = "SURGERY"
    with pytest.raises(AgentFailure) as ei:
        await IntakeAgent().run(make_ctx(inp))
    assert ei.value.error.code == ErrorCode.INVALID_CATEGORY
```

- [ ] **Step 4: Run** `pytest tests/test_intake.py -q` → Expected: FAIL.

- [ ] **Step 5: Implement `app/agents/intake.py`**

```python
from __future__ import annotations
import time
from app.agents.base import Agent
from app.core.context import ClaimContext
from app.core.errors import AgentError, AgentFailure, ErrorCode
from app.core.trace import CheckResult, PolicyCheck, StepResult, StepStatus

class IntakeAgent(Agent):
    name = "IntakeAgent"
    step = "INTAKE"
    fatal = True

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        sub, loader = ctx.submission, ctx.loader
        checks: list[PolicyCheck] = []

        member = loader.member(sub.member_id)
        if member is None:
            raise AgentFailure(AgentError(
                code=ErrorCode.MEMBER_NOT_FOUND,
                message=f"member {sub.member_id} not in roster",
                member_message=(f"We couldn't find member ID {sub.member_id} on policy "
                                f"{sub.policy_id}. Please check your member ID and try again."),
            ))
        ctx.member = member
        checks.append(PolicyCheck(check="MEMBER_EXISTS", result=CheckResult.PASS,
                                  rule_ref="members", detail={"member_id": member.member_id}))

        try:
            ctx.policy_view = loader.view(sub.claim_category)
        except KeyError:
            valid = ", ".join(k.upper() for k in loader.policy.opd_categories)
            raise AgentFailure(AgentError(
                code=ErrorCode.INVALID_CATEGORY,
                message=f"unknown category {sub.claim_category}",
                member_message=(f"'{sub.claim_category}' is not a covered claim category. "
                                f"Covered categories: {valid}."),
            ))
        checks.append(PolicyCheck(check="CATEGORY_COVERED", result=CheckResult.PASS,
                                  rule_ref=f"opd_categories.{sub.claim_category.lower()}.covered"))

        min_amt = loader.policy.submission_rules.minimum_claim_amount
        if sub.claimed_amount < min_amt:
            raise AgentFailure(AgentError(
                code=ErrorCode.AMOUNT_BELOW_MINIMUM,
                message=f"claimed {sub.claimed_amount} < min {min_amt}",
                member_message=(f"The claimed amount ₹{sub.claimed_amount} is below the minimum "
                                f"claimable amount of ₹{min_amt} under your policy."),
                detail={"claimed": sub.claimed_amount, "minimum": min_amt},
            ))
        checks.append(PolicyCheck(check="MINIMUM_AMOUNT", result=CheckResult.PASS,
                                  rule_ref="submission_rules.minimum_claim_amount",
                                  detail={"claimed": sub.claimed_amount, "minimum": min_amt}))

        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          checks=checks, duration_ms=int((time.monotonic() - t0) * 1000))
```

Note: the 30-day submission deadline check needs "today"; for reproducible eval runs we deliberately skip wall-clock deadline enforcement and record a SKIPPED check `SUBMISSION_DEADLINE` with detail `{"reason": "no submission timestamp in test data"}` — add it to `checks`. (Documented assumption; revisit if real submissions carry timestamps.)

```python
        checks.append(PolicyCheck(check="SUBMISSION_DEADLINE", result=CheckResult.SKIPPED,
                                  rule_ref="submission_rules.deadline_days_from_treatment",
                                  detail={"reason": "no submission timestamp in test data"}))
```
(insert before the `return`.)

- [ ] **Step 6: Run** `pytest tests/test_intake.py -q` → Expected: all PASS.

- [ ] **Step 7: STOP — present to Sumanth; he commits (`feat: agent base and intake agent`).**

---

### Task 7: DocVerifierAgent (early-exit gate — TC001, TC002)

**Files:**
- Create: `app/agents/doc_verifier.py`
- Test: `tests/test_doc_verifier.py`

Behavior: for each document, use test-path hints (`actual_type`, `quality`) when present, else call `llm.classify_document`. Then diff detected types against `policy_view.required_docs`:
- a required type is missing AND an extra/duplicate doc exists → `WRONG_DOCUMENT_TYPE`, message names **both** the uploaded type and the required type (TC001)
- a required type is missing, nothing unexpected → `MISSING_REQUIRED_DOCUMENT`
- a required doc is `UNREADABLE` → `DOCUMENT_UNREADABLE`, message asks to re-upload **that specific file** (TC002)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_doc_verifier.py
import pytest
from app.agents.doc_verifier import DocVerifierAgent
from app.core.errors import AgentFailure, ErrorCode
from app.core.trace import StepStatus
from app.llm.mock_client import MockClient

@pytest.fixture
def agent():
    return DocVerifierAgent(llm=MockClient())

async def test_tc001_wrong_doc_type_names_both_types(agent, make_ctx, case_input):
    ctx = make_ctx(case_input("TC001"))   # two prescriptions, consultation claim
    ctx.policy_view = ctx.loader.view("CONSULTATION")
    with pytest.raises(AgentFailure) as ei:
        await agent.run(ctx)
    err = ei.value.error
    assert err.code == ErrorCode.WRONG_DOCUMENT_TYPE
    assert "PRESCRIPTION" in err.member_message and "HOSPITAL_BILL" in err.member_message

async def test_tc002_unreadable_asks_specific_reupload(agent, make_ctx, case_input):
    ctx = make_ctx(case_input("TC002"))   # blurry pharmacy bill
    ctx.policy_view = ctx.loader.view("PHARMACY")
    with pytest.raises(AgentFailure) as ei:
        await agent.run(ctx)
    err = ei.value.error
    assert err.code == ErrorCode.DOCUMENT_UNREADABLE
    assert "blurry_bill.jpg" in err.member_message
    assert "re-upload" in err.member_message.lower()

async def test_clean_docs_pass(agent, make_ctx, case_input):
    ctx = make_ctx(case_input("TC004"))
    ctx.policy_view = ctx.loader.view("CONSULTATION")
    result = await agent.run(ctx)
    assert result.status == StepStatus.PASS
    assert {v.detected_type for v in ctx.doc_verdicts} == {"PRESCRIPTION", "HOSPITAL_BILL"}
```

- [ ] **Step 2: Run** `pytest tests/test_doc_verifier.py -q` → Expected: FAIL.

- [ ] **Step 3: Implement `app/agents/doc_verifier.py`**

```python
from __future__ import annotations
import time
from app.agents.base import Agent
from app.core.context import ClaimContext, DocVerdict
from app.core.errors import AgentError, AgentFailure, ErrorCode
from app.core.trace import CheckResult, ConfidenceEntry, PolicyCheck, StepResult, StepStatus
from app.llm.base import LLMClient, LLMError

class DocVerifierAgent(Agent):
    name = "DocVerifierAgent"
    step = "DOC_VERIFICATION"
    fatal = True

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        checks: list[PolicyCheck] = []
        entries: list[ConfidenceEntry] = []
        rule_ref = f"document_requirements.{ctx.policy_view.category}"

        for doc in ctx.submission.documents:
            if doc.actual_type is not None:            # test-path hint
                verdict = DocVerdict(file_id=doc.file_id, file_name=doc.file_name,
                                     detected_type=str(doc.actual_type),
                                     readability=str(doc.quality or "GOOD"))
            else:                                       # real path: vision classify
                try:
                    c = await self.llm.classify_document(doc)
                except LLMError as e:
                    raise AgentFailure(AgentError(
                        code=ErrorCode.DOCUMENT_UNREADABLE,
                        message=f"classification failed for {doc.file_id}: {e}",
                        member_message=(f"We couldn't process '{doc.file_name or doc.file_id}'. "
                                        f"Please re-upload a clearer photo or PDF of this document."),
                    ))
                verdict = DocVerdict(file_id=doc.file_id, file_name=doc.file_name,
                                     detected_type=c.detected_type,
                                     readability=c.readability, confidence=c.confidence)
            ctx.doc_verdicts.append(verdict)
            checks.append(PolicyCheck(check="DOC_CLASSIFIED", result=CheckResult.PASS,
                                      detail=verdict.model_dump()))
            if verdict.readability == "PARTIAL":
                entries.append(ConfidenceEntry(factor=0.9,
                               reason=f"{verdict.file_name or verdict.file_id} partially readable"))

        # unreadable required docs → re-upload request (not rejection)
        required = set(ctx.policy_view.required_docs)
        for v in ctx.doc_verdicts:
            if v.readability == "UNREADABLE" and v.detected_type in required:
                raise AgentFailure(AgentError(
                    code=ErrorCode.DOCUMENT_UNREADABLE,
                    message=f"{v.file_id} unreadable",
                    member_message=(f"Your {v.detected_type.replace('_', ' ').title()} "
                                    f"('{v.file_name or v.file_id}') is too blurry to read. "
                                    f"Please re-upload a clear photo of this document. "
                                    f"Your claim is on hold — it has not been rejected."),
                    detail={"file_id": v.file_id, "readability": "UNREADABLE"},
                ))

        detected = {v.detected_type for v in ctx.doc_verdicts}
        missing = sorted(required - detected)
        extra = sorted(t for t in (v.detected_type for v in ctx.doc_verdicts)
                       if t not in required and t not in set(ctx.policy_view.optional_docs))

        if missing:
            uploaded_desc = ", ".join(f"{v.detected_type} ('{v.file_name or v.file_id}')"
                                      for v in ctx.doc_verdicts)
            code = ErrorCode.WRONG_DOCUMENT_TYPE if (extra or len(ctx.doc_verdicts) >= len(required)) \
                   else ErrorCode.MISSING_REQUIRED_DOCUMENT
            raise AgentFailure(AgentError(
                code=code,
                message=f"missing required docs: {missing}",
                member_message=(f"For a {ctx.policy_view.category} claim you must upload: "
                                f"{', '.join(sorted(required))}. You uploaded: {uploaded_desc}. "
                                f"Missing: {', '.join(missing)}. "
                                f"Please upload your {missing[0].replace('_', ' ').lower()} to proceed."),
                detail={"required": sorted(required), "detected": sorted(detected),
                        "missing": missing},
            ))

        checks.append(PolicyCheck(check="REQUIREMENTS_MET", result=CheckResult.PASS,
                                  rule_ref=rule_ref,
                                  detail={"required": sorted(required), "detected": sorted(detected)}))
        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          checks=checks, confidence_entries=entries,
                          duration_ms=int((time.monotonic() - t0) * 1000))
```

- [ ] **Step 4: Run** `pytest tests/test_doc_verifier.py -q` → Expected: all PASS.

- [ ] **Step 5: STOP — present to Sumanth; he commits (`feat: document verifier with early-exit messages`).**

---

### Task 8: ExtractionAgent (dual path, async fan-out)

**Files:**
- Create: `app/agents/extraction.py`
- Test: `tests/test_extraction.py` (extend)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_extraction.py (append)
from app.agents.extraction import ExtractionAgent
from app.core.trace import StepStatus
from app.llm.base import LLMErrorKind

async def test_provided_content_is_injected(make_ctx, case_input):
    ctx = make_ctx(case_input("TC004"))
    ctx.policy_view = ctx.loader.view("CONSULTATION")
    agent = ExtractionAgent(llm=MockClient())
    result = await agent.run(ctx)
    assert result.status == StepStatus.PASS
    bill = next(e for e in ctx.extractions if e.doc_type == "HOSPITAL_BILL")
    assert bill.source == "provided"
    assert bill.data["total"] == 1500
    assert len(bill.data["line_items"]) == 3

async def test_llm_failure_degrades_not_crashes(make_ctx, case_input):
    mock = MockClient()
    mock.fail_next = LLMErrorKind.TIMEOUT
    ctx = make_ctx({**case_input("TC004"),
                    "documents": [{"file_id": "F1", "file_name": "sample_bill.jpg"}]})
    ctx.policy_view = ctx.loader.view("CONSULTATION")
    # give the verdict the doc_verifier would have produced
    from app.core.context import DocVerdict
    ctx.doc_verdicts = [DocVerdict(file_id="F1", file_name="sample_bill.jpg",
                                   detected_type="HOSPITAL_BILL", readability="GOOD")]
    result = await ExtractionAgent(llm=mock).run(ctx)
    assert result.status == StepStatus.DEGRADED
    assert ctx.extractions[0].degraded is True
    assert any(e.factor < 1.0 for e in result.confidence_entries)
```

- [ ] **Step 2: Run** → Expected: FAIL.

- [ ] **Step 3: Implement `app/agents/extraction.py`**

```python
from __future__ import annotations
import asyncio, time
from app.agents.base import Agent
from app.core.context import ClaimContext, ExtractionRecord
from app.core.trace import CheckResult, ConfidenceEntry, PolicyCheck, StepResult, StepStatus
from app.llm.base import LLMClient, LLMError
from app.models.domain import DocumentInput
from app.models.extraction import SCHEMA_BY_DOCTYPE

class ExtractionAgent(Agent):
    name = "ExtractionAgent"
    step = "EXTRACTION"
    fatal = False

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        verdict_by_id = {v.file_id: v for v in ctx.doc_verdicts}
        records = await asyncio.gather(
            *(self._extract_one(doc, verdict_by_id.get(doc.file_id)) for doc in ctx.submission.documents)
        )
        ctx.extractions = list(records)

        checks, entries = [], []
        degraded = [r for r in records if r.degraded]
        for r in records:
            checks.append(PolicyCheck(
                check="FIELDS_EXTRACTED",
                result=CheckResult.FAIL if r.degraded else CheckResult.PASS,
                detail={"file_id": r.file_id, "doc_type": r.doc_type, "source": r.source,
                        "unextracted_fields": r.unextracted_fields}))
        for r in degraded:
            entries.append(ConfidenceEntry(factor=0.7,
                           reason=f"extraction failed for {r.file_id}; proceeding without it"))

        status = StepStatus.DEGRADED if degraded else StepStatus.PASS
        return StepResult(step=self.step, agent=self.name, status=status, checks=checks,
                          confidence_entries=entries,
                          duration_ms=int((time.monotonic() - t0) * 1000))

    async def _extract_one(self, doc: DocumentInput, verdict) -> ExtractionRecord:
        doc_type = verdict.detected_type if verdict else (str(doc.actual_type) if doc.actual_type else "UNKNOWN")
        if doc.content is not None:                     # test path: provided content
            data = dict(doc.content)
            if doc.patient_name_on_doc and "patient_name" not in data:
                data["patient_name"] = doc.patient_name_on_doc
            return ExtractionRecord(file_id=doc.file_id, doc_type=doc_type, data=data,
                                    field_confidence={k: 1.0 for k in data}, source="provided")
        schema = SCHEMA_BY_DOCTYPE.get(doc_type)
        if schema is None:
            return ExtractionRecord(file_id=doc.file_id, doc_type=doc_type, degraded=True,
                                    unextracted_fields=["*"], source="vision")
        try:
            out = await self.llm.extract(doc, schema)
            return ExtractionRecord(file_id=doc.file_id, doc_type=doc_type,
                                    data=out.data.model_dump(),
                                    field_confidence=out.field_confidence,
                                    unextracted_fields=out.unextracted_fields, source="vision")
        except LLMError:
            return ExtractionRecord(file_id=doc.file_id, doc_type=doc_type, degraded=True,
                                    unextracted_fields=["*"], source="vision")
```

- [ ] **Step 4: Run** `pytest tests/test_extraction.py -q` → Expected: all PASS.

- [ ] **Step 5: STOP — present to Sumanth; he commits (`feat: extraction agent with dual path and degradation`).**

---

### Task 9: ConsistencyAgent (TC003)

**Files:**
- Create: `app/agents/consistency.py`
- Test: `tests/test_consistency.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_consistency.py
import pytest
from app.agents.consistency import ConsistencyAgent
from app.agents.extraction import ExtractionAgent
from app.agents.intake import IntakeAgent
from app.core.errors import AgentFailure, ErrorCode
from app.core.trace import StepStatus
from app.llm.mock_client import MockClient

async def prepared_ctx(make_ctx, case):
    ctx = make_ctx(case)
    await IntakeAgent().run(ctx)
    await ExtractionAgent(llm=MockClient()).run(ctx)
    return ctx

async def test_tc003_patient_mismatch_names_both(make_ctx, case_input):
    ctx = await prepared_ctx(make_ctx, case_input("TC003"))
    with pytest.raises(AgentFailure) as ei:
        await ConsistencyAgent(llm=MockClient()).run(ctx)
    err = ei.value.error
    assert err.code == ErrorCode.PATIENT_MISMATCH
    assert "Rajesh Kumar" in err.member_message and "Arjun Mehta" in err.member_message

async def test_tc004_consistent_passes(make_ctx, case_input):
    ctx = await prepared_ctx(make_ctx, case_input("TC004"))
    result = await ConsistencyAgent(llm=MockClient()).run(ctx)
    assert result.status == StepStatus.PASS

async def test_amount_mismatch_warns_not_fatal(make_ctx, case_input):
    inp = dict(case_input("TC004")); inp["claimed_amount"] = 2000  # bill total is 1500
    ctx = await prepared_ctx(make_ctx, inp)
    result = await ConsistencyAgent(llm=MockClient()).run(ctx)
    assert result.status == StepStatus.PASS
    assert any(f.check == "AMOUNT_MATCH" and f.severity == "WARNING" for f in ctx.findings)
    assert any(e.factor < 1.0 for e in result.confidence_entries)
```

- [ ] **Step 2: Run** → Expected: FAIL.

- [ ] **Step 3: Implement `app/agents/consistency.py`**

```python
from __future__ import annotations
import time
from app.agents.base import Agent
from app.core.context import ClaimContext, ConsistencyFinding
from app.core.errors import AgentError, AgentFailure, ErrorCode
from app.core.trace import CheckResult, ConfidenceEntry, PolicyCheck, StepResult, StepStatus
from app.llm.base import LLMClient, LLMError
from app.llm.mock_client import name_tokens_match

class ConsistencyAgent(Agent):
    name = "ConsistencyAgent"
    step = "CONSISTENCY"
    fatal = True   # only PATIENT_MISMATCH raises; everything else is a warning

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def _names_match(self, a: str, b: str):
        try:
            m = await self.llm.names_equivalent(a, b)
            return m.equivalent, m.fuzzy
        except LLMError:
            return name_tokens_match(a, b)   # deterministic fallback

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        checks, entries = [], []

        # 1. patient names across documents must agree
        named = [(e, e.data.get("patient_name")) for e in ctx.extractions if e.data.get("patient_name")]
        for i in range(len(named) - 1):
            (ea, na), (eb, nb) = named[i], named[i + 1]
            eq, fuzzy = await self._names_match(na, nb)
            if not eq:
                ctx.findings.append(ConsistencyFinding(check="PATIENT_MATCH", severity="FATAL",
                    detail={"doc_a": ea.file_id, "name_a": na, "doc_b": eb.file_id, "name_b": nb}))
                raise AgentFailure(AgentError(
                    code=ErrorCode.PATIENT_MISMATCH,
                    message=f"patient mismatch: {na} vs {nb}",
                    member_message=(f"Your documents appear to belong to different people: "
                                    f"the {ea.doc_type.replace('_',' ').lower()} is for '{na}' but the "
                                    f"{eb.doc_type.replace('_',' ').lower()} is for '{nb}'. "
                                    f"All documents in one claim must be for the same patient. "
                                    f"Please re-upload matching documents."),
                    detail={"names_found": {ea.file_id: na, eb.file_id: nb}},
                ))
            if fuzzy:
                entries.append(ConfidenceEntry(factor=0.95, reason=f"fuzzy name match: '{na}' ≈ '{nb}'"))
        checks.append(PolicyCheck(check="PATIENT_MATCH", result=CheckResult.PASS,
                                  detail={"names": [n for _, n in named]}))

        # 2. names must belong to member or dependents (warning only — extraction noise)
        allowed = [ctx.member.name] + [d.name for d in ctx.loader.dependents_of(ctx.member.member_id)]
        for e, n in named:
            if not any((await self._names_match(n, a))[0] for a in allowed):
                ctx.findings.append(ConsistencyFinding(check="MEMBER_MATCH", severity="WARNING",
                                                       detail={"name_on_doc": n, "allowed": allowed}))
                entries.append(ConfidenceEntry(factor=0.9, reason=f"'{n}' not matched to member/dependents"))

        # 3. bill total vs claimed amount (warning)
        totals = [e.data.get("total") for e in ctx.extractions
                  if e.doc_type in ("HOSPITAL_BILL", "PHARMACY_BILL") and e.data.get("total")]
        if totals:
            bill_sum = sum(totals)
            if bill_sum != ctx.submission.claimed_amount:
                ctx.findings.append(ConsistencyFinding(check="AMOUNT_MATCH", severity="WARNING",
                    detail={"bill_total": bill_sum, "claimed": ctx.submission.claimed_amount}))
                entries.append(ConfidenceEntry(factor=0.9,
                    reason=f"bill total ₹{bill_sum} != claimed ₹{ctx.submission.claimed_amount}"))
                checks.append(PolicyCheck(check="AMOUNT_MATCH", result=CheckResult.WARN,
                    detail={"bill_total": bill_sum, "claimed": ctx.submission.claimed_amount}))
            else:
                checks.append(PolicyCheck(check="AMOUNT_MATCH", result=CheckResult.PASS,
                    detail={"bill_total": bill_sum}))

        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          checks=checks, confidence_entries=entries,
                          duration_ms=int((time.monotonic() - t0) * 1000))
```

- [ ] **Step 4: Run** `pytest tests/test_consistency.py -q` → Expected: all PASS.
  Note: TC003's docs carry `patient_name_on_doc` but no `content`; the ExtractionAgent injects that hint as `patient_name` (Task 8 `_extract_one`), which is what this agent reads.

- [ ] **Step 5: STOP — present to Sumanth; he commits (`feat: consistency agent with cross-document patient check`).**

---

### Task 10: Matching tables + AdjudicatorAgent policy checks (TC005, TC007, TC008, TC012)

**Files:**
- Create: `app/core/matching.py`, `app/agents/adjudicator.py` (checks; financial math in Task 11)
- Test: `tests/test_adjudicator_checks.py`

- [ ] **Step 1: Implement `app/core/matching.py`** (deterministic vocabulary; tested via the adjudicator tests)

```python
from __future__ import annotations

# Keys mirror policy_terms.json waiting_periods.specific_conditions
CONDITION_KEYWORDS: dict[str, list[str]] = {
    "diabetes": ["diabetes", "diabetic", "t2dm", "dm"],
    "hypertension": ["hypertension", "htn"],
    "thyroid_disorders": ["thyroid", "hypothyroid", "hyperthyroid"],
    "joint_replacement": ["joint replacement", "knee replacement", "hip replacement"],
    "maternity": ["maternity", "pregnancy", "antenatal", "delivery"],
    "mental_health": ["depression", "anxiety", "psychiatric", "mental health"],
    "obesity_treatment": ["obesity", "bariatric", "weight loss"],
    "hernia": ["hernia"],
    "cataract": ["cataract"],
}

# Keys mirror policy_terms.json exclusions.conditions entries
EXCLUSION_KEYWORDS: dict[str, list[str]] = {
    "Self-inflicted injuries": ["self-inflicted", "self inflicted"],
    "Substance abuse treatment": ["substance abuse", "de-addiction", "deaddiction"],
    "Experimental treatments": ["experimental"],
    "Infertility and assisted reproduction": ["infertility", "ivf", "assisted reproduction"],
    "Obesity and weight loss programs": ["obesity", "weight loss", "diet plan",
                                         "diet and nutrition", "diet program"],
    "Bariatric surgery": ["bariatric"],
    "Cosmetic or aesthetic procedures": ["cosmetic", "aesthetic", "whitening", "veneer", "bleaching"],
    "Health supplements and tonics": ["supplement", "tonic"],
}

def match_condition(*texts: str | None) -> str | None:
    blob = " ".join(t.lower() for t in texts if t)
    for cond, kws in CONDITION_KEYWORDS.items():
        if any(kw in blob for kw in kws):
            return cond
    return None

def match_exclusion(*texts: str | None) -> str | None:
    blob = " ".join(t.lower() for t in texts if t)
    for name, kws in EXCLUSION_KEYWORDS.items():
        if any(kw in blob for kw in kws):
            return name
    return None

def text_matches_any(text: str, candidates: list[str]) -> str | None:
    """Case-insensitive substring match either direction; returns matched candidate."""
    t = text.lower()
    for c in candidates:
        if c.lower() in t or t in c.lower():
            return c
    return None
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_adjudicator_checks.py
import pytest
from app.agents.adjudicator import AdjudicatorAgent
from app.agents.extraction import ExtractionAgent
from app.agents.intake import IntakeAgent
from app.core.trace import CheckResult
from app.llm.mock_client import MockClient

async def adjudicated(make_ctx, case):
    ctx = make_ctx(case)
    await IntakeAgent().run(ctx)
    await ExtractionAgent(llm=MockClient()).run(ctx)
    result = await AdjudicatorAgent().run(ctx)
    return ctx, result

async def test_tc005_waiting_period_with_eligible_date(make_ctx, case_input):
    ctx, result = await adjudicated(make_ctx, case_input("TC005"))
    assert "WAITING_PERIOD" in ctx.blocking_reasons
    wp = next(c for c in result.checks if c.check == "WAITING_PERIOD")
    assert wp.result == CheckResult.FAIL
    assert wp.rule_ref == "waiting_periods.specific_conditions.diabetes"
    assert wp.detail["eligible_from"] == "2024-11-30"   # 2024-09-01 + 90 days

async def test_tc007_pre_auth_missing(make_ctx, case_input):
    ctx, result = await adjudicated(make_ctx, case_input("TC007"))
    assert "PRE_AUTH_MISSING" in ctx.blocking_reasons
    pa = next(c for c in result.checks if c.check == "PRE_AUTHORIZATION")
    assert pa.detail["test"] == "MRI" and pa.detail["amount"] == 15000

async def test_tc008_per_claim_limit(make_ctx, case_input):
    ctx, result = await adjudicated(make_ctx, case_input("TC008"))
    assert "PER_CLAIM_EXCEEDED" in ctx.blocking_reasons
    pc = next(c for c in result.checks if c.check == "PER_CLAIM_LIMIT")
    assert pc.detail == {"claimed": 7500, "limit": 5000}
    assert pc.rule_ref == "coverage.per_claim_limit"

async def test_tc012_excluded_condition(make_ctx, case_input):
    ctx, result = await adjudicated(make_ctx, case_input("TC012"))
    assert "EXCLUDED_CONDITION" in ctx.blocking_reasons
    ex = next(c for c in result.checks if c.check == "EXCLUSIONS")
    assert "Obesity" in ex.detail["matched_exclusion"]

async def test_tc004_all_checks_pass(make_ctx, case_input):
    ctx, result = await adjudicated(make_ctx, case_input("TC004"))
    assert ctx.blocking_reasons == []
```

- [ ] **Step 3: Run** → Expected: FAIL.

- [ ] **Step 4: Implement `app/agents/adjudicator.py`** (checks portion; `_financials` lands in Task 11 — for now have it return without computing and `ctx.financial = {}`)

```python
from __future__ import annotations
import time
from datetime import timedelta
from app.agents.base import Agent
from app.core.context import ClaimContext
from app.core.matching import match_condition, match_exclusion, text_matches_any
from app.core.trace import CheckResult, PolicyCheck, StepResult, StepStatus

class AdjudicatorAgent(Agent):
    name = "AdjudicatorAgent"
    step = "ADJUDICATION"
    fatal = True   # raises only on internal error

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        checks: list[PolicyCheck] = []
        self._check_exclusions(ctx, checks)
        self._check_waiting_periods(ctx, checks)
        self._check_pre_auth(ctx, checks)
        self._check_limits(ctx, checks)
        if not ctx.blocking_reasons:
            self._adjudicate_line_items(ctx, checks)   # Task 11
            self._compute_financials(ctx, checks)      # Task 11
        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          checks=checks, duration_ms=int((time.monotonic() - t0) * 1000))

    # ---- helpers ----
    def _diagnosis_texts(self, ctx) -> list[str]:
        out = []
        for e in ctx.extractions:
            for f in ("diagnosis", "treatment"):
                if e.data.get(f):
                    out.append(e.data[f])
        return out

    def _check_exclusions(self, ctx, checks):
        texts = self._diagnosis_texts(ctx)
        matched = match_exclusion(*texts)
        if matched and matched in ctx.loader.policy.exclusions.conditions:
            ctx.blocking_reasons.append("EXCLUDED_CONDITION")
            checks.append(PolicyCheck(check="EXCLUSIONS", result=CheckResult.FAIL,
                rule_ref="exclusions.conditions",
                detail={"matched_exclusion": matched, "diagnosis_texts": texts}))
        else:
            checks.append(PolicyCheck(check="EXCLUSIONS", result=CheckResult.PASS,
                rule_ref="exclusions.conditions", detail={"diagnosis_texts": texts}))

    def _check_waiting_periods(self, ctx, checks):
        wp = ctx.loader.policy.waiting_periods
        join, treat = ctx.member.join_date, ctx.submission.treatment_date
        if join and (treat - join).days < wp.initial_waiting_period_days:
            eligible = join + timedelta(days=wp.initial_waiting_period_days)
            ctx.blocking_reasons.append("WAITING_PERIOD")
            checks.append(PolicyCheck(check="WAITING_PERIOD", result=CheckResult.FAIL,
                rule_ref="waiting_periods.initial_waiting_period_days",
                detail={"kind": "initial", "join_date": str(join),
                        "eligible_from": str(eligible), "treatment_date": str(treat)}))
            return
        cond = match_condition(*self._diagnosis_texts(ctx))
        if cond and cond in wp.specific_conditions and join:
            days = wp.specific_conditions[cond]
            eligible = join + timedelta(days=days)
            if treat < eligible:
                ctx.blocking_reasons.append("WAITING_PERIOD")
                checks.append(PolicyCheck(check="WAITING_PERIOD", result=CheckResult.FAIL,
                    rule_ref=f"waiting_periods.specific_conditions.{cond}",
                    detail={"condition_matched": cond, "waiting_days": days,
                            "member_join_date": str(join), "eligible_from": str(eligible),
                            "treatment_date": str(treat)}))
                return
        checks.append(PolicyCheck(check="WAITING_PERIOD", result=CheckResult.PASS,
            rule_ref="waiting_periods", detail={"condition_matched": cond}))

    def _check_pre_auth(self, ctx, checks):
        rules = ctx.policy_view.rules
        high_value = rules.high_value_tests_requiring_pre_auth
        threshold = rules.pre_auth_threshold
        if not high_value or threshold is None:
            checks.append(PolicyCheck(check="PRE_AUTHORIZATION", result=CheckResult.PASS,
                rule_ref=f"opd_categories.{ctx.policy_view.category.lower()}",
                detail={"reason": "category has no pre-auth rules"}))
            return
        for e in ctx.extractions:
            items = e.data.get("line_items") or []
            names = [i["description"] for i in items] + \
                    (e.data.get("tests_ordered") or []) + \
                    ([e.data.get("test_name")] if e.data.get("test_name") else [])
            for item in items:
                test = text_matches_any(item["description"], high_value)
                if test and item["amount"] > threshold and not ctx.submission.pre_authorization_id:
                    ctx.blocking_reasons.append("PRE_AUTH_MISSING")
                    checks.append(PolicyCheck(check="PRE_AUTHORIZATION", result=CheckResult.FAIL,
                        rule_ref=f"opd_categories.{ctx.policy_view.category.lower()}.high_value_tests_requiring_pre_auth",
                        detail={"test": test, "amount": item["amount"], "threshold": threshold,
                                "names_seen": names}))
                    return
        checks.append(PolicyCheck(check="PRE_AUTHORIZATION", result=CheckResult.PASS,
            rule_ref=f"opd_categories.{ctx.policy_view.category.lower()}.pre_auth_threshold",
            detail={"threshold": threshold}))

    def _check_limits(self, ctx, checks):
        cov = ctx.loader.policy.coverage
        claimed = ctx.submission.claimed_amount
        if claimed > cov.per_claim_limit:
            ctx.blocking_reasons.append("PER_CLAIM_EXCEEDED")
            checks.append(PolicyCheck(check="PER_CLAIM_LIMIT", result=CheckResult.FAIL,
                rule_ref="coverage.per_claim_limit",
                detail={"claimed": claimed, "limit": cov.per_claim_limit}))
        else:
            checks.append(PolicyCheck(check="PER_CLAIM_LIMIT", result=CheckResult.PASS,
                rule_ref="coverage.per_claim_limit",
                detail={"claimed": claimed, "limit": cov.per_claim_limit}))
        ytd = ctx.submission.ytd_claims_amount
        if ytd + claimed > cov.annual_opd_limit:
            ctx.blocking_reasons.append("ANNUAL_LIMIT_EXCEEDED")
            checks.append(PolicyCheck(check="ANNUAL_OPD_LIMIT", result=CheckResult.FAIL,
                rule_ref="coverage.annual_opd_limit",
                detail={"ytd": ytd, "claimed": claimed, "limit": cov.annual_opd_limit}))
        else:
            checks.append(PolicyCheck(check="ANNUAL_OPD_LIMIT", result=CheckResult.PASS,
                rule_ref="coverage.annual_opd_limit",
                detail={"ytd": ytd, "claimed": claimed, "limit": cov.annual_opd_limit}))

    # implemented in Task 11
    def _adjudicate_line_items(self, ctx, checks): ...
    def _compute_financials(self, ctx, checks): ...
```

**Gotcha for TC007:** the DENTAL/DIAGNOSTIC line items arrive as plain dicts inside `e.data["line_items"]` (provided content), so index them as dicts, not `LineItem` models — the code above does.
**Gotcha for TC008:** per-claim check must run even though TC008's category sub-limit also looks violated; expected reason is only `PER_CLAIM_EXCEEDED`. The eval asserts *expected ⊆ produced*, so extra PASS checks are fine, but don't add extra blocking reasons for sub-limits here (sub-limit capping is per-line in Task 11, non-blocking).

- [ ] **Step 5: Run** `pytest tests/test_adjudicator_checks.py -q` → Expected: all PASS.

- [ ] **Step 6: STOP — present to Sumanth; he commits (`feat: adjudicator policy checks with rule refs`).**

---

### Task 11: Adjudicator line items + financial math (TC004, TC006, TC010)

**Files:**
- Modify: `app/agents/adjudicator.py` (fill the two stubs)
- Test: `tests/test_adjudicator_financial.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_adjudicator_financial.py
import pytest
from app.agents.adjudicator import AdjudicatorAgent
from app.agents.extraction import ExtractionAgent
from app.agents.intake import IntakeAgent
from app.llm.mock_client import MockClient

async def adjudicated(make_ctx, case):
    ctx = make_ctx(case)
    await IntakeAgent().run(ctx)
    await ExtractionAgent(llm=MockClient()).run(ctx)
    await AdjudicatorAgent().run(ctx)
    return ctx

async def test_tc004_copay_only(make_ctx, case_input):
    ctx = await adjudicated(make_ctx, case_input("TC004"))
    f = ctx.financial
    assert f["base"] == 1500
    assert f["network_discount"] == 0          # City Clinic not in network
    assert f["copay"] == 150                   # 10% of 1500
    assert f["payable"] == 1350

async def test_tc010_discount_before_copay(make_ctx, case_input):
    ctx = await adjudicated(make_ctx, case_input("TC010"))
    f = ctx.financial
    assert f["base"] == 4500
    assert f["network_discount"] == 900        # 20% of 4500 → 3600
    assert f["after_discount"] == 3600
    assert f["copay"] == 360                   # 10% of 3600
    assert f["payable"] == 3240

async def test_tc006_line_item_exclusion(make_ctx, case_input):
    ctx = await adjudicated(make_ctx, case_input("TC006"))
    by_desc = {v.description: v for v in ctx.line_verdicts}
    assert by_desc["Root Canal Treatment"].verdict == "APPROVED"
    rejected = by_desc["Teeth Whitening"]
    assert rejected.verdict == "REJECTED"
    assert "excluded" in rejected.reason.lower()
    assert rejected.rule_ref == "opd_categories.dental.excluded_procedures"
    assert ctx.financial["payable"] == 8000

async def test_consultation_subline_capped(make_ctx, case_input):
    # consultation fee line above sub_limit gets capped (documented assumption #1)
    inp = dict(case_input("TC004"))
    inp["claimed_amount"] = 3000
    inp["documents"][1]["content"] = {**inp["documents"][1]["content"],
        "line_items": [{"description": "Consultation Fee", "amount": 2500},
                       {"description": "CBC Test", "amount": 500}], "total": 3000}
    ctx = await adjudicated(make_ctx, inp)
    capped = next(v for v in ctx.line_verdicts if v.description == "Consultation Fee")
    assert capped.verdict == "CAPPED" and capped.eligible_amount == 2000
    assert ctx.financial["base"] == 2500       # 2000 + 500
```

- [ ] **Step 2: Run** → Expected: FAIL.

- [ ] **Step 3: Implement the two stubs in `app/agents/adjudicator.py`**

```python
    def _bill_line_items(self, ctx) -> list[dict]:
        items = []
        for e in ctx.extractions:
            if e.doc_type in ("HOSPITAL_BILL", "PHARMACY_BILL"):
                items.extend(e.data.get("line_items") or [])
        if not items:   # bills without itemization: treat the total as one line
            for e in ctx.extractions:
                if e.doc_type in ("HOSPITAL_BILL", "PHARMACY_BILL") and e.data.get("total"):
                    items.append({"description": ctx.policy_view.category.title(),
                                  "amount": e.data["total"]})
        return items

    def _adjudicate_line_items(self, ctx, checks):
        from app.core.context import LineItemVerdict
        rules = ctx.policy_view.rules
        cat = ctx.policy_view.category.lower()
        excluded = rules.excluded_procedures + rules.excluded_items
        covered = rules.covered_procedures + rules.covered_items
        for item in self._bill_line_items(ctx):
            desc, amount = item["description"], item["amount"]
            hit = text_matches_any(desc, excluded)
            if hit:
                ctx.line_verdicts.append(LineItemVerdict(
                    description=desc, amount=amount, eligible_amount=0, verdict="REJECTED",
                    reason=f"'{desc}' matches excluded procedure '{hit}' — not covered",
                    rule_ref=f"opd_categories.{cat}.excluded_procedures"))
                continue
            excl = match_exclusion(desc)
            if excl and excl in ctx.loader.policy.exclusions.conditions:
                ctx.line_verdicts.append(LineItemVerdict(
                    description=desc, amount=amount, eligible_amount=0, verdict="REJECTED",
                    reason=f"'{desc}' falls under policy exclusion '{excl}'",
                    rule_ref="exclusions.conditions"))
                continue
            eligible = amount
            verdict, reason = "APPROVED", "covered"
            if "consultation" in desc.lower() and rules.sub_limit and amount > rules.sub_limit \
               and cat == "consultation":
                eligible, verdict = rules.sub_limit, "CAPPED"
                reason = f"consultation fee capped at category sub-limit ₹{rules.sub_limit}"
            if covered and not text_matches_any(desc, covered) and verdict == "APPROVED":
                reason = "covered (not on explicit covered list; allowed by default)"
            ctx.line_verdicts.append(LineItemVerdict(
                description=desc, amount=amount, eligible_amount=eligible,
                verdict=verdict, reason=reason,
                rule_ref=f"opd_categories.{cat}.sub_limit" if verdict == "CAPPED" else None))
        checks.append(PolicyCheck(check="LINE_ITEMS", result=CheckResult.PASS,
            detail={"verdicts": [v.model_dump() for v in ctx.line_verdicts]}))

    def _compute_financials(self, ctx, checks):
        rules = ctx.policy_view.rules
        cat = ctx.policy_view.category.lower()
        base = sum(v.eligible_amount for v in ctx.line_verdicts)
        hospital = ctx.submission.hospital_name or next(
            (e.data.get("hospital_name") for e in ctx.extractions if e.data.get("hospital_name")), None)
        in_network = bool(hospital) and any(
            h.lower() in hospital.lower() or hospital.lower() in h.lower()
            for h in ctx.loader.policy.network_hospitals)
        discount = round(base * rules.network_discount_percent / 100) if in_network else 0
        after_discount = base - discount
        copay = round(after_discount * rules.copay_percent / 100)
        payable = after_discount - copay
        ctx.financial = {"base": base, "in_network": in_network, "hospital": hospital,
                         "network_discount_percent": rules.network_discount_percent if in_network else 0,
                         "network_discount": discount, "after_discount": after_discount,
                         "copay_percent": rules.copay_percent, "copay": copay, "payable": payable}
        checks.append(PolicyCheck(check="FINANCIAL_CALCULATION", result=CheckResult.PASS,
            rule_ref=f"opd_categories.{cat}",
            detail=dict(ctx.financial, order="network discount applied before co-pay")))
```

- [ ] **Step 4: Run** `pytest tests/test_adjudicator_financial.py -q` then `pytest -q` → Expected: all PASS.

- [ ] **Step 5: STOP — present to Sumanth; he commits (`feat: line-item adjudication and discount-before-copay math`).**

---

### Task 12: FraudAgent (TC009) + Aggregator (decision derivation)

**Files:**
- Create: `app/agents/fraud.py`, `app/agents/aggregator.py`
- Test: `tests/test_fraud.py`, `tests/test_aggregator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_fraud.py
from app.agents.fraud import FraudAgent
from app.agents.intake import IntakeAgent

async def test_tc009_same_day_signal(make_ctx, case_input):
    ctx = make_ctx(case_input("TC009"))
    await IntakeAgent().run(ctx)
    await FraudAgent().run(ctx)
    sig = next(s for s in ctx.fraud_signals if s.signal == "SAME_DAY_CLAIMS")
    assert sig.detail["count_today"] == 4      # 3 prior + this one
    assert sig.detail["limit"] == 2
    assert sig.rule_ref == "fraud_thresholds.same_day_claims_limit"

async def test_simulated_failure_raises(make_ctx, case_input):
    import pytest
    ctx = make_ctx(case_input("TC011"))        # simulate_component_failure: true
    await IntakeAgent().run(ctx)
    with pytest.raises(RuntimeError):
        await FraudAgent().run(ctx)

async def test_clean_claim_no_signals(make_ctx, case_input):
    ctx = make_ctx(case_input("TC004"))
    await IntakeAgent().run(ctx)
    await FraudAgent().run(ctx)
    assert ctx.fraud_signals == []
```

```python
# tests/test_aggregator.py
from app.agents.aggregator import Aggregator
from app.core.context import FraudSignal, LineItemVerdict
from app.models.domain import DecisionStatus

async def test_fraud_routes_to_manual_review(make_ctx, case_input):
    ctx = make_ctx(case_input("TC009"))
    ctx.fraud_signals = [FraudSignal(signal="SAME_DAY_CLAIMS", detail={"count_today": 4, "limit": 2})]
    result = await Aggregator().run(ctx)
    d = ctx.trace.decision
    assert d.status == DecisionStatus.MANUAL_REVIEW
    assert "SAME_DAY_CLAIMS" in d.reasons[0] or any("SAME_DAY" in r for r in d.reasons)

async def test_blocking_reason_rejects(make_ctx, case_input):
    ctx = make_ctx(case_input("TC005"))
    ctx.blocking_reasons = ["WAITING_PERIOD"]
    await Aggregator().run(ctx)
    assert ctx.trace.decision.status == DecisionStatus.REJECTED
    assert "WAITING_PERIOD" in ctx.trace.decision.reasons

async def test_mixed_line_items_partial(make_ctx, case_input):
    ctx = make_ctx(case_input("TC006"))
    ctx.line_verdicts = [
        LineItemVerdict(description="Root Canal Treatment", amount=8000, eligible_amount=8000,
                        verdict="APPROVED", reason="covered"),
        LineItemVerdict(description="Teeth Whitening", amount=4000, eligible_amount=0,
                        verdict="REJECTED", reason="excluded"),
    ]
    ctx.financial = {"payable": 8000, "base": 8000, "network_discount": 0, "copay": 0}
    await Aggregator().run(ctx)
    d = ctx.trace.decision
    assert d.status == DecisionStatus.PARTIAL and d.approved_amount == 8000

async def test_all_approved(make_ctx, case_input):
    ctx = make_ctx(case_input("TC004"))
    ctx.line_verdicts = [LineItemVerdict(description="Consultation Fee", amount=1500,
                         eligible_amount=1500, verdict="APPROVED", reason="covered")]
    ctx.financial = {"payable": 1350, "base": 1500, "network_discount": 0, "copay": 150}
    await Aggregator().run(ctx)
    d = ctx.trace.decision
    assert d.status == DecisionStatus.APPROVED and d.approved_amount == 1350

async def test_low_confidence_adds_recommendation_not_status_change(make_ctx, case_input):
    from app.core.trace import StepResult, StepStatus, ConfidenceEntry
    ctx = make_ctx(case_input("TC011"))
    ctx.trace.append(StepResult(step="FRAUD", agent="FraudAgent", status=StepStatus.SKIPPED,
        confidence_entries=[ConfidenceEntry(factor=0.7, reason="FraudAgent failed; skipped")]))
    ctx.line_verdicts = [LineItemVerdict(description="Panchakarma", amount=4000,
                         eligible_amount=4000, verdict="APPROVED", reason="covered")]
    ctx.financial = {"payable": 4000, "base": 4000, "network_discount": 0, "copay": 0}
    await Aggregator().run(ctx)
    d = ctx.trace.decision
    assert d.status == DecisionStatus.APPROVED          # NOT flipped (TC011)
    assert d.confidence < 0.85
    assert "manual review" in d.ops_summary.lower()
```

- [ ] **Step 2: Run** → Expected: FAIL.

- [ ] **Step 3: Implement `app/agents/fraud.py`**

```python
from __future__ import annotations
import time
from app.agents.base import Agent
from app.core.context import ClaimContext, FraudSignal
from app.core.trace import CheckResult, PolicyCheck, StepResult, StepStatus

class FraudAgent(Agent):
    name = "FraudAgent"
    step = "FRAUD_CHECK"
    fatal = False

    async def run(self, ctx: ClaimContext) -> StepResult:
        if ctx.submission.simulate_component_failure:
            raise RuntimeError("simulated component failure (test flag)")
        t0 = time.monotonic()
        checks: list[PolicyCheck] = []
        th = ctx.loader.policy.fraud_thresholds
        sub = ctx.submission

        same_day = [h for h in sub.claims_history if h.date == sub.treatment_date]
        count_today = len(same_day) + 1     # +1 = this claim
        if count_today > th.same_day_claims_limit:
            ctx.fraud_signals.append(FraudSignal(signal="SAME_DAY_CLAIMS",
                rule_ref="fraud_thresholds.same_day_claims_limit",
                detail={"count_today": count_today, "limit": th.same_day_claims_limit,
                        "prior_claims": [h.model_dump(mode="json") for h in same_day]}))
        checks.append(PolicyCheck(check="SAME_DAY_CLAIMS",
            result=CheckResult.FAIL if count_today > th.same_day_claims_limit else CheckResult.PASS,
            rule_ref="fraud_thresholds.same_day_claims_limit",
            detail={"count_today": count_today, "limit": th.same_day_claims_limit}))

        month = [h for h in sub.claims_history
                 if (h.date.year, h.date.month) == (sub.treatment_date.year, sub.treatment_date.month)]
        count_month = len(month) + 1
        if count_month > th.monthly_claims_limit:
            ctx.fraud_signals.append(FraudSignal(signal="MONTHLY_CLAIMS",
                rule_ref="fraud_thresholds.monthly_claims_limit",
                detail={"count_month": count_month, "limit": th.monthly_claims_limit}))
        checks.append(PolicyCheck(check="MONTHLY_CLAIMS",
            result=CheckResult.FAIL if count_month > th.monthly_claims_limit else CheckResult.PASS,
            rule_ref="fraud_thresholds.monthly_claims_limit",
            detail={"count_month": count_month, "limit": th.monthly_claims_limit}))

        if sub.claimed_amount > th.auto_manual_review_above:
            ctx.fraud_signals.append(FraudSignal(signal="HIGH_VALUE_CLAIM",
                rule_ref="fraud_thresholds.auto_manual_review_above",
                detail={"claimed": sub.claimed_amount, "threshold": th.auto_manual_review_above}))
        checks.append(PolicyCheck(check="HIGH_VALUE",
            result=CheckResult.FAIL if sub.claimed_amount > th.auto_manual_review_above else CheckResult.PASS,
            rule_ref="fraud_thresholds.auto_manual_review_above",
            detail={"claimed": sub.claimed_amount, "threshold": th.auto_manual_review_above}))

        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          checks=checks, duration_ms=int((time.monotonic() - t0) * 1000))
```

- [ ] **Step 4: Implement `app/agents/aggregator.py`**

```python
from __future__ import annotations
import time
from app.agents.base import Agent
from app.core.context import ClaimContext
from app.core.trace import StepResult, StepStatus
from app.models.domain import Decision, DecisionStatus

CONFIDENCE_REVIEW_THRESHOLD = 0.75

class Aggregator(Agent):
    name = "Aggregator"
    step = "AGGREGATION"
    fatal = True

    async def run(self, ctx: ClaimContext) -> StepResult:
        t0 = time.monotonic()
        confidence = round(ctx.trace.confidence(), 4)
        degraded_steps = [s.step for s in ctx.trace.steps
                          if s.status in (StepStatus.DEGRADED, StepStatus.SKIPPED)]
        notes = []
        if degraded_steps:
            notes.append(f"Components degraded/skipped: {', '.join(degraded_steps)}. "
                         f"Manual review recommended due to incomplete processing.")
        if confidence < CONFIDENCE_REVIEW_THRESHOLD and not degraded_steps:
            notes.append("Low confidence — manual review recommended.")

        if ctx.fraud_signals:
            reasons = [f"{s.signal}: {s.detail}" for s in ctx.fraud_signals]
            decision = Decision(status=DecisionStatus.MANUAL_REVIEW, approved_amount=0,
                reasons=reasons, confidence=confidence,
                member_message=("Your claim needs a quick manual check by our team before we can "
                                "process it. No action is needed from you right now."),
                ops_summary="Routed to manual review. Signals: " + "; ".join(reasons)
                            + (" | " + " ".join(notes) if notes else ""))
        elif ctx.blocking_reasons:
            decision = Decision(status=DecisionStatus.REJECTED, approved_amount=0,
                reasons=list(dict.fromkeys(ctx.blocking_reasons)), confidence=confidence,
                member_message=self._rejection_message(ctx),
                ops_summary=f"Rejected: {ctx.blocking_reasons}. "
                            + (" ".join(notes) if notes else ""))
        else:
            approved = [v for v in ctx.line_verdicts if v.verdict in ("APPROVED", "CAPPED")]
            rejected = [v for v in ctx.line_verdicts if v.verdict == "REJECTED"]
            payable = int(ctx.financial.get("payable", 0))
            if approved and rejected:
                status = DecisionStatus.PARTIAL
            elif approved:
                status = DecisionStatus.APPROVED
            else:
                status = DecisionStatus.REJECTED
            line_summary = "; ".join(f"{v.description}: {v.verdict} ({v.reason})"
                                     for v in ctx.line_verdicts)
            decision = Decision(status=status, approved_amount=payable,
                reasons=[v.reason for v in rejected] or ["All checks passed"],
                confidence=confidence,
                member_message=self._approval_message(ctx, payable, rejected),
                ops_summary=f"{status}: payable ₹{payable}. Lines: {line_summary}. "
                            f"Financial: {ctx.financial}. " + (" ".join(notes) if notes else ""))

        ctx.trace.decision = decision
        return StepResult(step=self.step, agent=self.name, status=StepStatus.PASS,
                          duration_ms=int((time.monotonic() - t0) * 1000))

    def _rejection_message(self, ctx) -> str:
        parts = []
        for s in ctx.trace.steps:
            for c in s.checks:
                if c.result == "FAIL" and c.check == "WAITING_PERIOD":
                    parts.append(f"This treatment falls inside a waiting period. You will be "
                                 f"eligible for {c.detail.get('condition_matched', 'this')} "
                                 f"claims from {c.detail['eligible_from']}.")
                elif c.result == "FAIL" and c.check == "PER_CLAIM_LIMIT":
                    parts.append(f"Your claimed amount ₹{c.detail['claimed']} exceeds the "
                                 f"per-claim limit of ₹{c.detail['limit']}.")
                elif c.result == "FAIL" and c.check == "PRE_AUTHORIZATION":
                    parts.append(f"{c.detail['test']} above ₹{c.detail['threshold']} requires "
                                 f"pre-authorization, which was not obtained. Please get "
                                 f"pre-authorization from your insurer and resubmit the claim "
                                 f"with the pre-authorization ID.")
                elif c.result == "FAIL" and c.check == "EXCLUSIONS":
                    parts.append(f"'{c.detail['matched_exclusion']}' is excluded under your "
                                 f"policy and cannot be claimed.")
        return " ".join(parts) or "Your claim was rejected. See the decision details."

    def _approval_message(self, ctx, payable: int, rejected) -> str:
        f = ctx.financial
        msg = f"Approved amount: ₹{payable}."
        if f.get("network_discount"):
            msg += (f" Network discount {f['network_discount_percent']}% (−₹{f['network_discount']}) "
                    f"applied first, then co-pay {f['copay_percent']}% (−₹{f['copay']}).")
        elif f.get("copay"):
            msg += f" A {f['copay_percent']}% co-pay (−₹{f['copay']}) was applied."
        if rejected:
            msg += " Not covered: " + "; ".join(f"{v.description} (₹{v.amount}) — {v.reason}"
                                                for v in rejected)
        return msg
```

- [ ] **Step 5: Run** `pytest tests/test_fraud.py tests/test_aggregator.py -q` → Expected: all PASS.

- [ ] **Step 6: STOP — present to Sumanth; he commits (`feat: fraud signals and decision aggregator`).**

---

### Task 13: Orchestrator (early exits, degradation — TC011 mechanics)

**Files:**
- Create: `app/core/orchestrator.py`
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_orchestrator.py
import pytest
from app.core.orchestrator import Orchestrator
from app.core.policy_loader import PolicyLoader
from app.llm.mock_client import MockClient
from app.models.domain import ClaimSubmission, DecisionStatus

@pytest.fixture
def orch(loader):
    return Orchestrator(loader=loader, llm=MockClient())

async def run_case(orch, case_input, case_id):
    sub = ClaimSubmission.model_validate(case_input(case_id))
    return await orch.process(sub)

async def test_tc001_stops_early(orch, case_input):
    out = await run_case(orch, case_input, "TC001")
    assert out.status == "STOPPED"
    assert out.decision is None
    assert "PRESCRIPTION" in out.member_message and "HOSPITAL_BILL" in out.member_message
    # adjudication never ran
    assert not any(s["step"] == "ADJUDICATION" for s in out.trace["steps"])

async def test_tc004_completes_approved(orch, case_input):
    out = await run_case(orch, case_input, "TC004")
    assert out.status == "COMPLETED"
    assert out.decision.status == DecisionStatus.APPROVED
    assert out.decision.approved_amount == 1350
    assert out.decision.confidence > 0.85

async def test_tc011_degrades_not_crashes(orch, case_input):
    out = await run_case(orch, case_input, "TC011")
    assert out.status == "COMPLETED"
    assert out.decision.status == DecisionStatus.APPROVED
    fraud_step = next(s for s in out.trace["steps"] if s["step"] == "FRAUD_CHECK")
    assert fraud_step["status"] == "SKIPPED"
    assert out.decision.confidence <= 0.7
    assert "manual review" in out.decision.ops_summary.lower()

async def test_internal_error_in_degradable_agent_never_propagates(orch, case_input):
    # TC011 exercises this via the simulate flag; assert no exception type leaks
    out = await run_case(orch, case_input, "TC011")
    assert out.trace["steps"][-1]["step"] == "AGGREGATION"
```

- [ ] **Step 2: Run** → Expected: FAIL.

- [ ] **Step 3: Implement `app/core/orchestrator.py`**

```python
from __future__ import annotations
import time, uuid
from datetime import datetime, timezone
from app.agents.aggregator import Aggregator
from app.agents.adjudicator import AdjudicatorAgent
from app.agents.consistency import ConsistencyAgent
from app.agents.doc_verifier import DocVerifierAgent
from app.agents.extraction import ExtractionAgent
from app.agents.fraud import FraudAgent
from app.agents.intake import IntakeAgent
from app.config import settings
from app.core.context import ClaimContext
from app.core.errors import AgentError, AgentFailure, ErrorCode
from app.core.policy_loader import PolicyLoader
from app.core.trace import ClaimTrace, ConfidenceEntry, StepResult, StepStatus
from app.llm.base import LLMClient
from app.models.domain import ClaimOutcome, ClaimSubmission

class Orchestrator:
    def __init__(self, loader: PolicyLoader, llm: LLMClient, repository=None):
        self.loader = loader
        self.repository = repository
        self.agents = [
            IntakeAgent(),
            DocVerifierAgent(llm=llm),
            ExtractionAgent(llm=llm),
            ConsistencyAgent(llm=llm),
            AdjudicatorAgent(),
            FraudAgent(),
            Aggregator(),
        ]

    async def process(self, submission: ClaimSubmission) -> ClaimOutcome:
        claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"
        ctx = ClaimContext(submission=submission, loader=self.loader,
                           trace=ClaimTrace(claim_id=claim_id,
                                            pipeline_version=settings.pipeline_version))
        for agent in self.agents:
            t0 = time.monotonic()
            try:
                result = await agent.run(ctx)
            except AgentFailure as f:
                result = StepResult(step=agent.step, agent=agent.name,
                                    status=StepStatus.FAIL, error=f.error,
                                    duration_ms=int((time.monotonic() - t0) * 1000))
                ctx.trace.append(result)
                if agent.fatal:
                    return self._stopped(ctx, f.error)
                self._degrade(ctx, agent, f.error.message)
                continue
            except Exception as e:                      # noqa: BLE001 — pipeline must never crash
                err = AgentError(code=ErrorCode.INTERNAL_ERROR, message=str(e))
                result = StepResult(step=agent.step, agent=agent.name,
                                    status=StepStatus.FAIL, error=err,
                                    duration_ms=int((time.monotonic() - t0) * 1000))
                ctx.trace.append(result)
                if agent.fatal and not isinstance(agent, (FraudAgent,)):
                    return self._stopped(ctx, err)
                self._degrade(ctx, agent, str(e))
                continue
            ctx.trace.append(result)
        ctx.trace.completed_at = datetime.now(timezone.utc)
        outcome = ClaimOutcome(claim_id=claim_id, status="COMPLETED",
                               decision=ctx.trace.decision,
                               member_message=ctx.trace.decision.member_message,
                               trace=ctx.trace.model_dump(mode="json"))
        if self.repository:
            self.repository.save(ctx.submission, outcome)
        return outcome

    def _degrade(self, ctx: ClaimContext, agent, reason: str) -> None:
        ctx.trace.steps[-1].status = StepStatus.SKIPPED
        ctx.trace.steps[-1].confidence_entries.append(
            ConfidenceEntry(factor=0.7, reason=f"{agent.name} failed and was skipped: {reason}"))

    def _stopped(self, ctx: ClaimContext, error: AgentError) -> ClaimOutcome:
        ctx.trace.completed_at = datetime.now(timezone.utc)
        outcome = ClaimOutcome(claim_id=ctx.trace.claim_id, status="STOPPED",
                               decision=None, member_message=error.member_message,
                               trace=ctx.trace.model_dump(mode="json"))
        if self.repository:
            self.repository.save(ctx.submission, outcome)
        return outcome
```

**Note on the `except Exception` branch:** a raise from a *fatal* agent that isn't an `AgentFailure` is an internal bug → STOPPED with a generic message; from a degradable agent (FraudAgent) → degrade and continue. TC011's simulated `RuntimeError` exercises exactly this path.

- [ ] **Step 4: Run** `pytest tests/test_orchestrator.py -q` then `pytest -q` → Expected: all PASS.

- [ ] **Step 5: STOP — present to Sumanth; he commits (`feat: deterministic orchestrator with early exit and degradation`).**

---

### Task 14: Repository (SQLite)

**Files:**
- Create: `app/core/repository.py`
- Test: `tests/test_repository.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_repository.py
import pytest
from app.core.repository import Repository
from app.models.domain import ClaimOutcome, ClaimSubmission, Decision, DecisionStatus

@pytest.fixture
def repo(tmp_path):
    return Repository(str(tmp_path / "test.db"))

def make_outcome(claim_id="CLM-1"):
    return ClaimOutcome(claim_id=claim_id, status="COMPLETED",
        decision=Decision(status=DecisionStatus.APPROVED, approved_amount=1350, confidence=0.95),
        trace={"claim_id": claim_id, "steps": []})

def test_save_and_get(repo, case_input):
    sub = ClaimSubmission.model_validate(case_input("TC004"))
    repo.save(sub, make_outcome())
    row = repo.get("CLM-1")
    assert row["decision"]["approved_amount"] == 1350
    assert row["member_id"] == "EMP001"

def test_list_newest_first(repo, case_input):
    sub = ClaimSubmission.model_validate(case_input("TC004"))
    repo.save(sub, make_outcome("CLM-1"))
    repo.save(sub, make_outcome("CLM-2"))
    ids = [r["claim_id"] for r in repo.list_claims()]
    assert ids[0] == "CLM-2"

def test_get_missing_returns_none(repo):
    assert repo.get("NOPE") is None
```

- [ ] **Step 2: Run** → Expected: FAIL.

- [ ] **Step 3: Implement `app/core/repository.py`**

```python
from __future__ import annotations
import json, sqlite3
from datetime import datetime, timezone
from app.models.domain import ClaimOutcome, ClaimSubmission

_SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    member_id TEXT NOT NULL,
    category TEXT NOT NULL,
    treatment_date TEXT NOT NULL,
    claimed_amount INTEGER NOT NULL,
    status TEXT NOT NULL,
    decision_status TEXT,
    approved_amount INTEGER,
    confidence REAL,
    created_at TEXT NOT NULL,
    submission_json TEXT NOT NULL,
    outcome_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_claims_member ON claims(member_id, treatment_date);
"""

class Repository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, sub: ClaimSubmission, outcome: ClaimOutcome) -> None:
        d = outcome.decision
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO claims VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (outcome.claim_id, sub.member_id, sub.claim_category, str(sub.treatment_date),
                 sub.claimed_amount, outcome.status,
                 d.status if d else None, d.approved_amount if d else None,
                 d.confidence if d else None,
                 datetime.now(timezone.utc).isoformat(),
                 sub.model_dump_json(exclude={"documents": {"__all__": {"file_bytes"}}}),
                 outcome.model_dump_json()))

    def get(self, claim_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM claims WHERE claim_id=?", (claim_id,)).fetchone()
        if row is None:
            return None
        out = json.loads(row["outcome_json"])
        out["member_id"] = row["member_id"]
        return out

    def list_claims(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT claim_id, member_id, category, treatment_date, claimed_amount, "
                "status, decision_status, approved_amount, confidence, created_at "
                "FROM claims ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
```

- [ ] **Step 4: Run** `pytest tests/test_repository.py -q` → Expected: all PASS.

- [ ] **Step 5: STOP — present to Sumanth; he commits (`feat: sqlite repository`).**

---

### Task 15: FastAPI app

**Files:**
- Create: `app/api/__init__.py`, `app/api/schemas.py`, `app/api/main.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_api.py
import pytest
from httpx import ASGITransport, AsyncClient
from app.api.main import create_app

@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    app = create_app(db_path=str(tmp_path / "api.db"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c

async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"

async def test_submit_json_claim_tc004(client, case_input):
    r = await client.post("/claims", json=case_input("TC004"))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "COMPLETED"
    assert body["decision"]["approved_amount"] == 1350

async def test_doc_problem_is_200_stopped(client, case_input):
    r = await client.post("/claims", json=case_input("TC001"))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "STOPPED" and body["decision"] is None
    assert "HOSPITAL_BILL" in body["member_message"]

async def test_get_claim_returns_trace(client, case_input):
    claim_id = (await client.post("/claims", json=case_input("TC004"))).json()["claim_id"]
    r = await client.get(f"/claims/{claim_id}")
    assert r.status_code == 200
    assert any(s["step"] == "ADJUDICATION" for s in r.json()["trace"]["steps"])

async def test_get_unknown_claim_404(client):
    assert (await client.get("/claims/NOPE")).status_code == 404

async def test_list_members(client):
    r = await client.get("/members")
    assert any(m["member_id"] == "EMP001" for m in r.json())
```

- [ ] **Step 2: Run** → Expected: FAIL.

- [ ] **Step 3: Implement `app/api/schemas.py`**

```python
from __future__ import annotations
from pydantic import BaseModel
from app.models.domain import ClaimSubmission  # re-exported as the request schema

class HealthResponse(BaseModel):
    status: str = "ok"
    llm_provider: str
    pipeline_version: str
```

- [ ] **Step 4: Implement `app/api/main.py`**

```python
from __future__ import annotations
import base64, json
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from app.api.schemas import HealthResponse
from app.config import settings
from app.core.orchestrator import Orchestrator
from app.core.policy_loader import PolicyLoader
from app.core.repository import Repository
from app.llm.mock_client import MockClient
from app.models.domain import ClaimOutcome, ClaimSubmission, DocumentInput

def make_llm():
    if settings.llm_provider == "gemini":
        from app.llm.gemini_client import GeminiClient   # Task 17
        return GeminiClient(api_key=settings.gemini_api_key)
    return MockClient()

def create_app(db_path: str | None = None) -> FastAPI:
    app = FastAPI(title="Plum Claims Processing", version=settings.pipeline_version)
    loader = PolicyLoader.load(settings.policy_path)
    repo = Repository(db_path or settings.db_path)
    orch = Orchestrator(loader=loader, llm=make_llm(), repository=repo)

    @app.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(llm_provider=settings.llm_provider,
                              pipeline_version=settings.pipeline_version)

    @app.get("/members")
    async def members():
        return [{"member_id": m.member_id, "name": m.name, "relationship": m.relationship}
                for m in loader.policy.members]

    @app.post("/claims", response_model=ClaimOutcome)
    async def submit_claim(submission: ClaimSubmission) -> ClaimOutcome:
        return await orch.process(submission)

    @app.post("/claims/upload", response_model=ClaimOutcome)
    async def submit_claim_with_files(
        payload: str = Form(...),                 # ClaimSubmission JSON minus documents
        files: list[UploadFile] = File(...),
    ) -> ClaimOutcome:
        data = json.loads(payload)
        docs = []
        for i, f in enumerate(files):
            docs.append(DocumentInput(file_id=f"UP{i+1}", file_name=f.filename,
                                      file_bytes=await f.read(),
                                      mime_type=f.content_type))
        data["documents"] = []
        sub = ClaimSubmission.model_validate(data)
        sub.documents = docs
        return await orch.process(sub)

    @app.get("/claims")
    async def list_claims():
        return repo.list_claims()

    @app.get("/claims/{claim_id}")
    async def get_claim(claim_id: str):
        row = repo.get(claim_id)
        if row is None:
            raise HTTPException(404, f"claim {claim_id} not found")
        return row

    return app

app = create_app()
```

- [ ] **Step 5: Run** `pytest tests/test_api.py -q` → Expected: all PASS.
- [ ] **Step 6: Manual smoke:** `.venv/bin/uvicorn app.api.main:app --port 8000` then `curl -s localhost:8000/health` → `{"status":"ok",...}`.

- [ ] **Step 7: STOP — present to Sumanth; he commits (`feat: fastapi endpoints for claims, upload, members`).**

---

### Task 16: Eval runner — all 12 cases (deliverable #4)

**Files:**
- Create: `app/eval/__init__.py`, `app/eval/runner.py`, `app/eval/__main__.py`
- Modify: `app/api/main.py` (add `POST /eval/run`)
- Test: `tests/test_eval_cases.py`

- [ ] **Step 1: Write failing tests** — this is the assignment's acceptance suite.

```python
# tests/test_eval_cases.py
import pytest
from app.eval.runner import EvalRunner

@pytest.fixture(scope="module")
async def report():
    from app.config import settings
    runner = EvalRunner.default()
    return await runner.run_all(settings.test_cases_path)

async def test_all_twelve_cases_pass(report):
    failed = [c for c in report.cases if not c.passed]
    detail = "\n".join(f"{c.case_id}: {c.failures}" for c in failed)
    assert not failed, f"failing cases:\n{detail}"

@pytest.mark.parametrize("case_id,decision", [
    ("TC001", None), ("TC002", None), ("TC003", None),
    ("TC004", "APPROVED"), ("TC005", "REJECTED"), ("TC006", "PARTIAL"),
    ("TC007", "REJECTED"), ("TC008", "REJECTED"), ("TC009", "MANUAL_REVIEW"),
    ("TC010", "APPROVED"), ("TC011", "APPROVED"), ("TC012", "REJECTED"),
])
async def test_case_decision(report, case_id, decision):
    case = next(c for c in report.cases if c.case_id == case_id)
    assert case.produced_decision == decision
```

- [ ] **Step 2: Run** → Expected: FAIL.

- [ ] **Step 3: Implement `app/eval/runner.py`**

```python
from __future__ import annotations
import json
from pydantic import BaseModel, Field
from app.config import settings
from app.core.orchestrator import Orchestrator
from app.core.policy_loader import PolicyLoader
from app.llm.mock_client import MockClient
from app.models.domain import ClaimSubmission

class CaseResult(BaseModel):
    case_id: str
    case_name: str
    expected_decision: str | None
    produced_decision: str | None
    approved_amount: int | None = None
    confidence: float | None = None
    passed: bool
    failures: list[str] = Field(default_factory=list)
    member_message: str = ""
    trace: dict = Field(default_factory=dict)

class EvalReport(BaseModel):
    cases: list[CaseResult]
    passed: int
    failed: int

class EvalRunner:
    def __init__(self, orchestrator: Orchestrator):
        self.orch = orchestrator

    @classmethod
    def default(cls) -> "EvalRunner":
        loader = PolicyLoader.load(settings.policy_path)
        return cls(Orchestrator(loader=loader, llm=MockClient()))

    async def run_all(self, cases_path: str) -> EvalReport:
        with open(cases_path) as f:
            cases = json.load(f)["test_cases"]
        results = [await self.run_case(c) for c in cases]
        report = EvalReport(cases=results,
                            passed=sum(c.passed for c in results),
                            failed=sum(not c.passed for c in results))
        return report

    async def run_case(self, case: dict) -> CaseResult:
        sub = ClaimSubmission.model_validate(case["input"])
        out = await self.orch.process(sub)
        exp = case["expected"]
        failures: list[str] = []

        expected_decision = exp.get("decision")
        produced = out.decision.status if out.decision else None
        if produced != expected_decision:
            failures.append(f"decision: expected {expected_decision}, got {produced}")

        if "approved_amount" in exp and out.decision \
           and out.decision.approved_amount != exp["approved_amount"]:
            failures.append(f"amount: expected {exp['approved_amount']}, "
                            f"got {out.decision.approved_amount}")

        for reason in exp.get("rejection_reasons", []):
            if out.decision and reason not in out.decision.reasons:
                failures.append(f"missing rejection reason {reason}")

        cs = exp.get("confidence_score", "")
        if cs.startswith("above") and out.decision:
            bound = float(cs.split()[-1])
            if out.decision.confidence <= bound:
                failures.append(f"confidence {out.decision.confidence} not above {bound}")

        failures += self._check_system_must(case, out)

        return CaseResult(case_id=case["case_id"], case_name=case["case_name"],
                          expected_decision=expected_decision, produced_decision=produced,
                          approved_amount=out.decision.approved_amount if out.decision else None,
                          confidence=out.decision.confidence if out.decision else None,
                          passed=not failures, failures=failures,
                          member_message=out.member_message, trace=out.trace)

    def _check_system_must(self, case: dict, out) -> list[str]:
        """Mechanically checkable subset of the prose 'system_must' expectations."""
        f: list[str] = []
        cid, msg = case["case_id"], out.member_message
        if cid == "TC001" and not ("PRESCRIPTION" in msg and "HOSPITAL_BILL" in msg):
            f.append("TC001: message must name uploaded and required doc types")
        if cid == "TC002" and "blurry_bill.jpg" not in msg:
            f.append("TC002: message must name the unreadable file")
        if cid == "TC003" and not ("Rajesh Kumar" in msg and "Arjun Mehta" in msg):
            f.append("TC003: message must include both patient names")
        if cid == "TC005" and "2024-11-30" not in msg:
            f.append("TC005: message must state the eligibility date")
        if cid == "TC010" and out.decision and "3600" not in out.decision.member_message:
            f.append("TC010: breakdown must show discount applied before co-pay")
        if cid == "TC011" and out.decision \
           and "manual review" not in out.decision.ops_summary.lower():
            f.append("TC011: must recommend manual review")
        return f

    @staticmethod
    def render_markdown(report: EvalReport) -> str:
        lines = ["# Eval Report — 12 Test Cases", "",
                 f"**Result: {report.passed}/12 passed**", ""]
        for c in report.cases:
            lines += [f"## {c.case_id} — {c.case_name}",
                      f"- Expected: `{c.expected_decision}` | Produced: `{c.produced_decision}`"
                      f" | **{'PASS' if c.passed else 'FAIL'}**"]
            if c.approved_amount is not None:
                lines.append(f"- Approved amount: ₹{c.approved_amount} | Confidence: {c.confidence}")
            if c.member_message:
                lines.append(f"- Member message: {c.member_message}")
            if c.failures:
                lines.append(f"- Mismatches: {'; '.join(c.failures)}")
            lines += ["", "<details><summary>Full trace</summary>", "", "```json",
                      __import__("json").dumps(c.trace, indent=2, default=str), "```",
                      "</details>", ""]
        return "\n".join(lines)
```

- [ ] **Step 4: Implement `app/eval/__main__.py`**

```python
import asyncio, pathlib
from app.config import settings
from app.eval.runner import EvalRunner

async def main():
    runner = EvalRunner.default()
    report = await runner.run_all(settings.test_cases_path)
    out = pathlib.Path("docs/eval_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(EvalRunner.render_markdown(report))
    print(f"{report.passed}/12 passed → {out}")

asyncio.run(main())
```

- [ ] **Step 5: Add to `app/api/main.py`** (inside `create_app`):

```python
    @app.post("/eval/run")
    async def run_eval():
        from app.eval.runner import EvalRunner
        runner = EvalRunner(orchestrator=orch)
        report = await runner.run_all(settings.test_cases_path)
        return report
```

- [ ] **Step 6: Run** `pytest tests/test_eval_cases.py -q` → iterate until **12/12 PASS** (this is the moment mismatches surface; fix the responsible agent, not the eval). Then `python -m app.eval` → writes `docs/eval_report.md`. Then full `pytest -q`.

- [ ] **Step 7: STOP — present 12/12 output + eval_report.md to Sumanth; he commits (`feat: eval runner, 12/12 test cases green`).**

---

### Task 17: GeminiClient (real vision path)

**Files:**
- Create: `app/llm/gemini_client.py`
- Test: `tests/test_gemini_client.py` (mock-transport unit tests + `@pytest.mark.live`)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_gemini_client.py
import pytest
from unittest.mock import AsyncMock, patch
from app.llm.base import LLMError, LLMErrorKind
from app.llm.gemini_client import GeminiClient
from app.models.domain import DocumentInput
from app.models.extraction import BillData

DOC = DocumentInput(file_id="F1", file_name="bill.jpg", file_bytes=b"fake", mime_type="image/jpeg")

@pytest.fixture
def client():
    return GeminiClient(api_key="test-key")

async def test_extract_valid_json(client):
    good = '{"hospital_name": "Apollo", "total": 4500, "line_items": []}'
    with patch.object(client, "_generate", AsyncMock(return_value=good)):
        out = await client.extract(DOC, BillData)
    assert out.data.hospital_name == "Apollo"

async def test_extract_retries_then_fails_schema(client):
    with patch.object(client, "_generate", AsyncMock(return_value="not json")) as gen:
        with pytest.raises(LLMError) as ei:
            await client.extract(DOC, BillData)
    assert ei.value.kind == LLMErrorKind.SCHEMA_INVALID
    assert gen.call_count == 2          # original + 1 retry

async def test_timeout_maps_to_llm_error(client):
    import asyncio
    with patch.object(client, "_generate", AsyncMock(side_effect=asyncio.TimeoutError)):
        with pytest.raises(LLMError) as ei:
            await client.extract(DOC, BillData)
    assert ei.value.kind == LLMErrorKind.TIMEOUT

@pytest.mark.live  # requires GEMINI_API_KEY; excluded from CI: pytest -m "not live"
async def test_live_classification_smoke():
    import os
    client = GeminiClient(api_key=os.environ["GEMINI_API_KEY"])
    doc = DocumentInput(file_id="F1", file_name="sample_docs/prescription_clean.png",
                        file_bytes=open("sample_docs/prescription_clean.png", "rb").read(),
                        mime_type="image/png")
    c = await client.classify_document(doc)
    assert c.detected_type == "PRESCRIPTION"
```

Add to `pytest.ini`: `markers = live: hits the real Gemini API` and set `addopts = -m "not live"`.

- [ ] **Step 2: Run** → Expected: FAIL.

- [ ] **Step 3: Implement `app/llm/gemini_client.py`**

```python
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

    async def _generate(self, parts: list, schema: dict | None = None) -> str:
        from google.genai import types
        cfg = types.GenerateContentConfig(
            response_mime_type="application/json",
            **({"response_json_schema": schema} if schema else {}))
        resp = await asyncio.wait_for(
            self._client.aio.models.generate_content(
                model=self.model, contents=parts, config=cfg),
            timeout=self.timeout_s)
        return resp.text

    def _image_part(self, doc: DocumentInput):
        from google.genai import types
        return types.Part.from_bytes(data=doc.file_bytes,
                                     mime_type=doc.mime_type or "image/jpeg")

    async def _call(self, parts, out_model: type[BaseModel], feedback: str = ""):
        last_err = None
        for attempt in range(2):                      # original + 1 retry
            try:
                text = await self._generate(parts + ([feedback] if feedback else []),
                                            schema=out_model.model_json_schema())
                return out_model.model_validate(json.loads(text))
            except (json.JSONDecodeError, ValidationError) as e:
                last_err, feedback = e, f"Previous output was invalid: {e}. Return valid JSON only."
            except asyncio.TimeoutError:
                raise LLMError(LLMErrorKind.TIMEOUT, "gemini timeout", retryable=True)
            except Exception as e:                    # provider/rate-limit errors
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
```

- [ ] **Step 4: Run** `pytest tests/test_gemini_client.py -q` → unit tests PASS (live test deselected).
- [ ] **Step 5 (manual, needs Sumanth's `GEMINI_API_KEY`):** `GEMINI_API_KEY=... pytest -m live -q` after Task 18 produces sample images.

- [ ] **Step 6: STOP — present to Sumanth; he commits (`feat: gemini vision client with schema retry`).**

---

### Task 18: Sample document generator

**Files:**
- Create: `scripts/generate_sample_docs.py`, output in `sample_docs/`

- [ ] **Step 1: Implement the generator** — PIL-rendered documents matching `sample_documents_guide.md` layouts. Generate:
  1. `prescription_clean.png` — Dr. Arun Sharma Rx for Rajesh Kumar (TC004 contents)
  2. `bill_clean.png` — City Clinic bill, 3 line items, total ₹1,500
  3. `bill_apollo.png` — Apollo Hospitals bill ₹4,500 (network-discount demo)
  4. `pharmacy_bill_blurry.png` — pharmacy bill passed through `GaussianBlur(radius=6)` (TC002 demo)
  5. `prescription_wrong_patient.png` — Rx for "Arjun Mehta" (TC003 demo)
  6. `dental_bill_mixed.png` — root canal + teeth whitening lines (TC006 demo)

```python
# scripts/generate_sample_docs.py (structure; one builder per doc)
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pathlib import Path

OUT = Path("sample_docs"); OUT.mkdir(exist_ok=True)
FONT = ImageFont.load_default(size=18)
BOLD = ImageFont.load_default(size=22)

def new_doc(h=1000):
    img = Image.new("RGB", (800, h), "white")
    return img, ImageDraw.Draw(img)

def header(d, lines, y=40):
    for ln in lines:
        d.text((50, y), ln, fill="black", font=BOLD); y += 30
    d.line((50, y + 5, 750, y + 5), fill="black", width=2)
    return y + 25

def prescription_clean():
    img, d = new_doc()
    y = header(d, ["Dr. Arun Sharma, MBBS, MD", "Reg. No: KA/45678/2015",
                   "City Medical Centre, 12 MG Road, Bengaluru"])
    for ln in ["Patient: Rajesh Kumar        Date: 01-Nov-2024",
               "Age: 39   Gender: M", "Diagnosis: Viral Fever", "",
               "Rx:", "1. Tab Paracetamol 650mg — 1-1-1 x 5 days",
               "2. Tab Vitamin C 500mg — 0-0-1 x 7 days", "",
               "Investigations: CBC, Dengue NS1"]:
        d.text((50, y), ln, fill="black", font=FONT); y += 32
    img.save(OUT / "prescription_clean.png")

# ...analogous builders for the other five; blurry one ends with:
#   img = img.filter(ImageFilter.GaussianBlur(radius=6))

if __name__ == "__main__":
    prescription_clean()
    # call all builders
    print(f"wrote {len(list(OUT.glob('*.png')))} docs to {OUT}/")
```

Write all six builders fully in the implementation (same pattern as `prescription_clean`, using the layouts in `sample_documents_guide.md`; the dental bill uses line items "Root Canal Treatment ₹8000" / "Teeth Whitening ₹4000").

- [ ] **Step 2: Run** `python scripts/generate_sample_docs.py` → Expected: `wrote 6 docs to sample_docs/`. Open 2-3 visually to confirm legibility.
- [ ] **Step 3 (with Sumanth's key):** run the live Gemini test against `prescription_clean.png` and `pharmacy_bill_blurry.png`; blurry one should classify `UNREADABLE`/`PARTIAL`. Add the blurry result to MockClient fixtures if useful for demos.

- [ ] **Step 4: STOP — present generated images to Sumanth; he commits (`feat: sample document generator`).**

---

### Task 19: Streamlit UI

**Files:**
- Create: `ui/streamlit_app.py`

Three pages via sidebar radio. Talks ONLY to the API (`API_BASE_URL` env, default `http://localhost:8000`).

- [ ] **Step 1: Implement `ui/streamlit_app.py`**

```python
from __future__ import annotations
import json, os
import httpx
import streamlit as st

API = os.getenv("API_BASE_URL", "http://localhost:8000")
st.set_page_config(page_title="Plum Claims", layout="wide")

def get(path):  return httpx.get(f"{API}{path}", timeout=120).json()
def post(path, **kw): return httpx.post(f"{API}{path}", timeout=300, **kw).json()

def render_decision(out: dict):
    if out["status"] == "STOPPED":
        st.error(f"⛔ Claim stopped before processing\n\n**{out['member_message']}**")
    else:
        d = out["decision"]
        color = {"APPROVED": st.success, "PARTIAL": st.warning,
                 "REJECTED": st.error, "MANUAL_REVIEW": st.info}[d["status"]]
        color(f"**{d['status']}** — approved ₹{d['approved_amount']} · "
              f"confidence {d['confidence']:.2f}\n\n{d['member_message']}")
    render_trace(out.get("trace", {}))

def render_trace(trace: dict):
    st.subheader("Decision trace")
    for step in trace.get("steps", []):
        icon = {"PASS": "✅", "FAIL": "❌", "DEGRADED": "⚠️", "SKIPPED": "⏭️"}[step["status"]]
        with st.expander(f"{icon} {step['step']} — {step['agent']} ({step['status']}, "
                         f"{step['duration_ms']}ms)"):
            for c in step.get("checks", []):
                st.markdown(f"- **{c['check']}** → {c['result']}"
                            + (f" · rule: `{c['rule_ref']}`" if c.get("rule_ref") else ""))
                if c.get("detail"):
                    st.json(c["detail"], expanded=False)
            if step.get("error"):
                st.code(json.dumps(step["error"], indent=2))
            for e in step.get("confidence_entries", []):
                st.caption(f"confidence ×{e['factor']} — {e['reason']}")

page = st.sidebar.radio("Plum Claims", ["Submit Claim", "Review Claims", "Eval (12 cases)"])

if page == "Submit Claim":
    st.title("Submit a claim")
    members = get("/members")
    col1, col2 = st.columns(2)
    with col1:
        member = st.selectbox("Member", members, format_func=lambda m: f"{m['member_id']} — {m['name']}")
        category = st.selectbox("Category", ["CONSULTATION", "DIAGNOSTIC", "PHARMACY",
                                             "DENTAL", "VISION", "ALTERNATIVE_MEDICINE"])
        treatment_date = st.date_input("Treatment date")
    with col2:
        amount = st.number_input("Claimed amount (₹)", min_value=0, step=100)
        hospital = st.text_input("Hospital name (optional)")
        files = st.file_uploader("Documents (images/PDF)", accept_multiple_files=True)
    if st.button("Submit claim", type="primary"):
        payload = {"member_id": member["member_id"], "policy_id": "PLUM_GHI_2024",
                   "claim_category": category, "treatment_date": str(treatment_date),
                   "claimed_amount": int(amount), "hospital_name": hospital or None}
        with st.spinner("Processing through pipeline..."):
            out = post("/claims/upload", data={"payload": json.dumps(payload)},
                       files=[("files", (f.name, f.getvalue(), f.type)) for f in files])
        render_decision(out)

elif page == "Review Claims":
    st.title("Claims review")
    claims = get("/claims")
    if not claims:
        st.info("No claims yet.")
    else:
        st.dataframe(claims, use_container_width=True)
        cid = st.selectbox("Open claim", [c["claim_id"] for c in claims])
        if cid:
            render_decision(get(f"/claims/{cid}"))

else:
    st.title("Eval — 12 assignment test cases")
    if st.button("Run all 12 test cases", type="primary"):
        with st.spinner("Running eval..."):
            report = post("/eval/run")
        st.metric("Passed", f"{report['passed']}/12")
        for c in report["cases"]:
            icon = "✅" if c["passed"] else "❌"
            with st.expander(f"{icon} {c['case_id']} — {c['case_name']}: "
                             f"{c['produced_decision']}"):
                st.markdown(f"**Member message:** {c['member_message']}")
                if c["failures"]:
                    st.error("; ".join(c["failures"]))
                render_trace(c["trace"])
```

- [ ] **Step 2: Manual verification** — run both: `uvicorn app.api.main:app --port 8000` and `streamlit run ui/streamlit_app.py`. Walk through: submit with sample docs (mock mode), review list, eval page 12/12. Screenshot for the README.

- [ ] **Step 3: STOP — demo to Sumanth; he commits (`feat: streamlit ui with trace viewer and eval page`).**

---

### Task 20: Deploy (Render) + README

**Files:**
- Create: `render.yaml`, `README.md`, `.env.example`

- [ ] **Step 1: `render.yaml`**

```yaml
services:
  - type: web
    name: plum-claims-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.api.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: LLM_PROVIDER
        value: gemini
      - key: GEMINI_API_KEY
        sync: false          # set in dashboard
      - key: DB_PATH
        value: /tmp/claims.db
  - type: web
    name: plum-claims-ui
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run ui/streamlit_app.py --server.port $PORT --server.address 0.0.0.0
    envVars:
      - key: API_BASE_URL
        fromService: { type: web, name: plum-claims-api, envVarKey: RENDER_EXTERNAL_URL }
```

- [ ] **Step 2: README.md** — quickstart (venv, two run commands, `python -m app.eval`), architecture summary linking `docs/`, deployed URLs, env vars table, screenshot, note about Render cold start.
- [ ] **Step 3:** Push to GitHub, create Render Blueprint deploy, set `GEMINI_API_KEY` in dashboard (Sumanth does both — walk him through).
- [ ] **Step 4: Verify deployed:** `curl https://plum-claims-api.onrender.com/health`; open UI URL; run eval page.
- [ ] **Step 5: STOP — Sumanth commits (`chore: render deploy config and readme`).**

---

### Task 21: Final docs — architecture, contracts, eval report

**Files:**
- Create: `docs/architecture.md`, `docs/contracts.md`; regenerate `docs/eval_report.md`

- [ ] **Step 1: `docs/architecture.md`** — adapt the spec (`docs/superpowers/specs/2026-06-12-claims-pipeline-design.md`) into the graded deliverable: components & interactions (embed the HLD/Mermaid diagrams from `...-diagrams.md`), why this design, considered-and-rejected table, failure handling, the 5 documented assumptions, limitations + 10x scaling section.
- [ ] **Step 2: `docs/contracts.md`** — adapt spec §4: for each of the 7 agents + LLMClient + Repository + Orchestrator: accepts / produces / errors raised / fatal-vs-degradable, matching the shipped code signatures exactly (verify against the code, not the spec).
- [ ] **Step 3:** `python -m app.eval` → fresh `docs/eval_report.md`; spot-check 12/12 and that traces render.
- [ ] **Step 4:** Full suite: `pytest -q` all green. Coverage sanity: `pytest --cov=app -q` (no hard threshold; eyeball that core/agents are well covered).
- [ ] **Step 5: STOP — Sumanth commits (`docs: architecture, contracts, final eval report`) and records the demo video** (script: TC001 early-stop in UI → upload flow approval with trace → eval page 12/12 → talk through deterministic-core + trace-first decisions).

---

## Self-Review Notes

- **Spec coverage:** all 6 non-negotiables and 5 deliverables map to tasks (1-16 system, 17-18 vision path, 19 UI, 20 deploy, 21 docs/eval/video). All 12 TCs are asserted in Task 16's suite; TC001-TC012 each have a dedicated agent-level test earlier.
- **Type consistency check done:** `ClaimOutcome.status` is `"COMPLETED"|"STOPPED"`; `DocVerdict.detected_type` is `str` (StrEnum values compare equal to strings); `ExtractionRecord.data` is a plain dict everywhere downstream (agents index with `.get`).
- **Known risk:** TC008's expected reasons are only `PER_CLAIM_EXCEEDED` while our pipeline also runs (and passes) sub-limit checks — eval asserts expected ⊆ produced, so safe. TC012 exclusion match relies on the keyword table — covered by `test_tc012_excluded_condition`.
- **Plan ordering rationale:** repository (14) lands after orchestrator (13) because the orchestrator takes it as an optional dependency; API (15) wires everything; eval (16) is the acceptance gate before any LLM/UI/deploy work — the system is fully demonstrable in mock mode from Task 16 onward.







