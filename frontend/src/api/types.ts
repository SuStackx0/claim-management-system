// TypeScript mirror of app/models/domain.py — the API contract.

export type DecisionStatus = "APPROVED" | "PARTIAL" | "REJECTED" | "MANUAL_REVIEW";
export type ClaimStatus = "COMPLETED" | "STOPPED";
export type TraceStatus = "PASS" | "FAIL" | "DEGRADED" | "SKIPPED";

export interface Member {
  member_id: string;
  name: string;
  relationship: string;
}

export interface Decision {
  status: DecisionStatus;
  approved_amount: number;
  reasons: string[];
  confidence: number;
  member_message: string;
  ops_summary: string;
}

export interface TraceCheck {
  check: string;
  result: string;
  rule_ref?: string | null;
  detail?: unknown;
}

export interface ConfidenceEntry {
  factor: number;
  reason: string;
}

export interface TraceStep {
  step: string;
  agent: string;
  status: TraceStatus;
  duration_ms: number;
  checks?: TraceCheck[];
  error?: unknown;
  confidence_entries?: ConfidenceEntry[];
}

export interface Trace {
  steps?: TraceStep[];
  [key: string]: unknown;
}

// Returned by POST /claims, /claims/upload and GET /claims/{id}.
export interface ClaimOutcome {
  claim_id: string;
  status: ClaimStatus;
  decision: Decision | null;
  member_message: string;
  trace: Trace;
}

// One entry from GET /claims — a stored row. Shape is loose (repo-defined);
// we render it generically, but these fields are reliably present.
export interface ClaimRow {
  claim_id: string;
  [key: string]: unknown;
}

export interface EvalCase {
  case_id: string;
  case_name: string;
  passed: boolean;
  expected_decision: string | null;
  produced_decision: string | null;
  pipeline_status?: string;
  approved_amount?: number | null;
  confidence?: number | null;
  member_message: string;
  failures: string[];
  trace: Trace;
}

export interface EvalReport {
  passed: number;
  failed: number;
  cases: EvalCase[];
}

export interface ClaimSubmissionPayload {
  member_id: string;
  policy_id: string;
  claim_category: string;
  treatment_date: string;
  claimed_amount: number;
  hospital_name: string | null;
}
