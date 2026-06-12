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
    opd_key: str        # canonical lowercase key into opd_categories (for rule_refs)
    rules: CategoryRules
    required_docs: list[str]
    optional_docs: list[str]
