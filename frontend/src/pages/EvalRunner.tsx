import { useState } from "react";
import { apiPost } from "../api/client";
import type { EvalReport } from "../api/types";
import StatusPill from "../components/StatusPill";
import TraceViewer from "../components/TraceViewer";

const TOTAL = 12;

export default function EvalRunner() {
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState<EvalReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runEval() {
    setRunning(true);
    setError(null);
    setReport(null);
    try {
      const result = await apiPost<EvalReport>("/eval/run");
      setReport(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  const total = report ? report.cases.length : TOTAL;
  const passed = report ? report.passed : 0;
  const failed = report ? report.failed : 0;
  const rate = total > 0 ? passed / total : 0;
  const summaryColor =
    passed === total
      ? "#15803d"
      : passed >= total * 0.8
        ? "#b45309"
        : "#b91c1c";

  return (
    <div>
      <h1>Eval — 12 Assignment Test Cases</h1>
      <p className="pc-caption">
        Runs all 12 predefined cases through the pipeline and checks each
        decision against its expected outcome.
      </p>
      <hr className="pc-divider" />

      <button className="pc-btn" disabled={running} onClick={runEval}>
        Run all 12 test cases
      </button>

      {running && (
        <div className="pc-card">
          <div>
            <span className="pc-spinner" />
            Running evaluation suite · 12 cases · ~3 minutes
          </div>
          <div className="pc-muted">
            Each case is submitted to the live pipeline and its decision is
            compared against the expected outcome. Results appear below when
            complete.
          </div>
        </div>
      )}

      {error && <div className="pc-alert pc-alert-error">{error}</div>}

      {report && (
        <div>
          <div className="pc-card">
            <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
              <div>
                <div
                  className="pc-summary-num"
                  style={{ color: summaryColor }}
                >
                  {passed} / {total}
                </div>
                <div className="pc-summary-sub">test cases passed</div>
              </div>
              <div style={{ flex: 1, minWidth: 220 }}>
                <div className="pc-meter-label">
                  <span>Pass rate</span>
                  <span style={{ color: summaryColor, fontWeight: 650 }}>
                    {Math.round(rate * 100)}%
                  </span>
                </div>
                <div className="pc-meter">
                  <span
                    style={{
                      width: rate * 100 + "%",
                      background: summaryColor,
                    }}
                  />
                </div>
                <div className="pc-summary-sub">
                  {passed} passed · {failed} failed
                </div>
              </div>
            </div>
          </div>

          <h2 className="pc-section-title">Per-case results</h2>

          {report.cases.map((c) => (
            <div key={c.case_id}>
              <div className="pc-case">
                <StatusPill
                  status={c.passed ? "APPROVED" : "REJECTED"}
                  text={c.passed ? "PASS" : "FAIL"}
                />
                <span className="pc-case-id">{c.case_id}</span>
                <span style={{ fontWeight: 600 }}>{c.case_name}</span>
                <span className="pc-muted">expected</span>
                <span className="pc-mono">{c.expected_decision ?? "—"}</span>
                <span className="pc-muted">got</span>
                <span className="pc-mono">{c.produced_decision ?? "—"}</span>
              </div>
              <details>
                <summary className="pc-btn-ghost">Details</summary>
                <div className="pc-label">Member message</div>
                <div className="pc-callout">{c.member_message}</div>
                {c.failures.length > 0 && (
                  <>
                    <div className="pc-label">Mismatches</div>
                    <div className="pc-alert pc-alert-error">
                      {c.failures.join("; ")}
                    </div>
                  </>
                )}
                <TraceViewer trace={c.trace} />
              </details>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
