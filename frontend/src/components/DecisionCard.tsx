// Claim outcome card — ported from render.py render_decision().
// Handles both STOPPED outcomes and full decisions, then renders the trace.

import type { ClaimOutcome, DecisionStatus } from "../api/types";
import StatusPill from "./StatusPill";
import TraceViewer from "./TraceViewer";

const DECISION_CONFIG: Record<DecisionStatus, { alert: string; label: string; icon: string }> = {
  APPROVED:      { alert: "pc-alert-success", label: "APPROVED",         icon: "✅" },
  PARTIAL:       { alert: "pc-alert-warning", label: "PARTIAL APPROVAL", icon: "🟡" },
  REJECTED:      { alert: "pc-alert-error",   label: "REJECTED",         icon: "❌" },
  MANUAL_REVIEW: { alert: "pc-alert-info",    label: "MANUAL REVIEW",    icon: "🔵" },
};

function confidenceLabel(c: number) {
  if (c >= 0.85) return "High";
  if (c >= 0.6) return "Medium";
  return "Low";
}
function confidenceColor(c: number) {
  if (c >= 0.85) return "#15803d";
  if (c >= 0.6) return "#b45309";
  return "#b91c1c";
}
const inr = (n: number) => `₹${n.toLocaleString("en-IN")}`;

export default function DecisionCard({ outcome }: { outcome: ClaimOutcome }) {
  if (outcome.status === "STOPPED" || !outcome.decision) {
    const msg = outcome.member_message;
    return (
      <div>
        <div className="pc-card" style={{ borderLeft: "4px solid #94a3b8" }}>
          <div className="pc-hero">
            <StatusPill status="STOPPED" />
          </div>
          <div className="pc-callout" style={{ marginTop: ".6rem" }}>{msg}</div>
        </div>
        <div className="pc-alert pc-alert-error" style={{ marginTop: ".75rem" }}>
          Claim stopped — <strong>{msg}</strong>
        </div>
        <div style={{ marginTop: "1rem" }}>
          <TraceViewer trace={outcome.trace} />
        </div>
      </div>
    );
  }

  const d = outcome.decision;
  const cfg = DECISION_CONFIG[d.status] ?? DECISION_CONFIG.MANUAL_REVIEW;
  const pct = Math.min(Math.round(d.confidence * 100), 100);
  const cc = confidenceColor(d.confidence);

  return (
    <div>
      <div className="pc-card">
        <div className="pc-hero">
          <StatusPill status={d.status} text={cfg.label} />
          <div className="pc-hero-amt">
            {inr(d.approved_amount)}
            <small>Approved amount</small>
          </div>
          <div style={{ flex: 1, minWidth: 160 }}>
            <div className="pc-meter-label">
              <span>Confidence</span>
              <span style={{ color: cc, fontWeight: 650 }}>
                {pct}% · {confidenceLabel(d.confidence)}
              </span>
            </div>
            <div className="pc-meter">
              <span style={{ width: `${pct}%`, background: cc }} />
            </div>
          </div>
        </div>
        <div className="pc-callout" style={{ marginTop: ".8rem" }}>{d.member_message}</div>
      </div>

      <div className={`pc-alert ${cfg.alert}`} style={{ marginTop: ".75rem" }}>
        <strong>{cfg.icon} {cfg.label}</strong> — Approved {inr(d.approved_amount)} · Confidence{" "}
        {pct}%
        <div style={{ marginTop: ".4rem" }}>{d.member_message}</div>
      </div>

      {d.reasons.length > 0 && (
        <div className="pc-card" style={{ marginTop: ".75rem" }}>
          <div className="pc-label" style={{ marginBottom: ".4rem" }}>Reasons</div>
          <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
            {d.reasons.map((r, i) => (
              <li key={i} style={{ margin: ".15rem 0", fontSize: ".9rem" }}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      <hr className="pc-divider" />
      <TraceViewer trace={outcome.trace} />
    </div>
  );
}
