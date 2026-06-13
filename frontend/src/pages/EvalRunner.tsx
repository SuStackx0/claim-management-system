import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api/client";
import type { EvalCase, EvalCaseSummary } from "../api/types";
import StatusPill from "../components/StatusPill";
import TraceViewer from "../components/TraceViewer";

// Per-card running state keyed by case_id.
type RunningMap = Record<string, boolean>;
// Per-card result keyed by case_id.
type ResultMap = Record<string, EvalCase>;
// Per-card error keyed by case_id.
type ErrorMap = Record<string, string>;

export default function EvalRunner() {
  const [cases, setCases] = useState<EvalCaseSummary[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [running, setRunning] = useState<RunningMap>({});
  const [results, setResults] = useState<ResultMap>({});
  const [errors, setErrors] = useState<ErrorMap>({});

  useEffect(() => {
    apiGet<EvalCaseSummary[]>("/eval/cases")
      .then((data) => setCases(data))
      .catch((e) => setListError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoadingList(false));
  }, []);

  async function runCase(caseId: string) {
    setRunning((prev) => ({ ...prev, [caseId]: true }));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[caseId];
      return next;
    });
    try {
      const result = await apiPost<EvalCase>(`/eval/run/${caseId}`);
      setResults((prev) => ({ ...prev, [caseId]: result }));
    } catch (e) {
      setErrors((prev) => ({
        ...prev,
        [caseId]: e instanceof Error ? e.message : String(e),
      }));
    } finally {
      setRunning((prev) => ({ ...prev, [caseId]: false }));
    }
  }

  // Derive summary stats from cards that have been run.
  const ranIds = Object.keys(results);
  const passedCount = ranIds.filter((id) => results[id].passed).length;
  const failedCount = ranIds.length - passedCount;
  const allPassed = ranIds.length > 0 && passedCount === ranIds.length;

  return (
    <div>
      <h1>Eval — 12 Assignment Test Cases</h1>
      <p className="pc-caption">
        Each card runs one case through the <strong>real Groq vision pipeline</strong>{" "}
        on generated document images. Expect ~10–40s per case — run them
        individually and results appear in the card when complete.
      </p>
      <hr className="pc-divider" />

      {/* Summary bar — only visible once at least one card has been run */}
      {ranIds.length > 0 && (
        <div className="pc-card" style={{ marginBottom: "1.5rem" }}>
          <div className="pc-eval-summary">
            <div className="pc-eval-summary-stat">
              <span
                className="pc-summary-num"
                style={{ color: allPassed ? "#15803d" : "#b91c1c" }}
              >
                {passedCount} / {ranIds.length}
              </span>
              <div className="pc-muted" style={{ fontSize: "0.8rem" }}>
                run so far
              </div>
            </div>
            <div className="pc-eval-summary-meter">
              <div className="pc-meter-label">
                <span>Pass rate</span>
                <span style={{ fontWeight: 650 }}>
                  {Math.round((passedCount / ranIds.length) * 100)}%
                </span>
              </div>
              <div className="pc-meter">
                <span
                  style={{
                    width: (passedCount / ranIds.length) * 100 + "%",
                    background: allPassed ? "#15803d" : "#b91c1c",
                  }}
                />
              </div>
              <div className="pc-muted" style={{ fontSize: "0.8rem" }}>
                {passedCount} passed · {failedCount} failed ·{" "}
                {cases.length - ranIds.length} not yet run
              </div>
            </div>
          </div>
        </div>
      )}

      {/* List loading / error states */}
      {loadingList && (
        <div className="pc-card" style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <span className="pc-spinner" />
          <span className="pc-muted">Loading test cases…</span>
        </div>
      )}

      {listError && <div className="pc-alert pc-alert-error">{listError}</div>}

      {!loadingList && !listError && cases.length === 0 && (
        <div className="pc-alert pc-alert-info">No eval cases are configured.</div>
      )}

      {/* Per-case grid */}
      {!loadingList && !listError && cases.length > 0 && (
        <div className="pc-eval-grid">
          {cases.map((summary) => {
            const isRunning = !!running[summary.case_id];
            const result = results[summary.case_id];
            const cardError = errors[summary.case_id];
            const stopsEarly = summary.expected.decision == null;

            const stateClass = isRunning
              ? "is-running"
              : result
              ? result.passed
                ? "is-pass"
                : "is-fail"
              : "";

            return (
              <div key={summary.case_id} className={`pc-card pc-eval-card ${stateClass}`}>
                <div className="pc-eval-card-head">
                  <span className="pc-case-id">{summary.case_id}</span>
                  {result && (
                    <StatusPill
                      status={result.passed ? "APPROVED" : "REJECTED"}
                      text={result.passed ? "PASS" : "FAIL"}
                    />
                  )}
                </div>

                <div className="pc-eval-name">{summary.case_name}</div>

                <div className="pc-eval-expected">
                  Expected:{" "}
                  <span className="pc-mono">
                    {stopsEarly ? "stops early" : summary.expected.decision ?? "—"}
                  </span>
                  {summary.expected.approved_amount != null && (
                    <span> · ₹{summary.expected.approved_amount.toLocaleString()}</span>
                  )}
                </div>

                <button
                  className="pc-btn pc-btn-full"
                  disabled={isRunning}
                  onClick={() => runCase(summary.case_id)}
                >
                  {isRunning ? (
                    <>
                      <span className="pc-spinner" />
                      Running vision pipeline…
                    </>
                  ) : result ? (
                    "Re-run live"
                  ) : (
                    "Run live"
                  )}
                </button>

                {cardError && (
                  <div className="pc-alert pc-alert-error">{cardError}</div>
                )}

                {result && !isRunning && (
                  <div style={{ marginTop: "0.85rem" }}>
                    <div className="pc-eval-facts">
                      <span>
                        <span className="pc-muted">Produced: </span>
                        <span className="pc-mono">
                          {result.produced_decision ??
                            (result.pipeline_status === "STOPPED" ? "stopped early" : "—")}
                        </span>
                      </span>
                      {result.approved_amount != null && (
                        <span>
                          <span className="pc-muted">Amount: </span>
                          <span className="pc-mono">
                            ₹{result.approved_amount.toLocaleString()}
                          </span>
                        </span>
                      )}
                      {result.confidence != null && (
                        <span>
                          <span className="pc-muted">Confidence: </span>
                          <span className="pc-mono">
                            {(result.confidence * 100).toFixed(0)}%
                          </span>
                        </span>
                      )}
                    </div>

                    <div className="pc-callout" style={{ fontSize: "0.85rem" }}>
                      {result.member_message}
                    </div>

                    {result.failures.length > 0 && (
                      <div
                        className="pc-alert pc-alert-error"
                        style={{ fontSize: "0.82rem" }}
                      >
                        {result.failures.join(" · ")}
                      </div>
                    )}

                    <details>
                      <summary className="pc-eval-trace-toggle">Pipeline trace ▾</summary>
                      <TraceViewer trace={result.trace} />
                    </details>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
