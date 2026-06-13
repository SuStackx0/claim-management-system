import { useEffect, useState } from "react";
import { apiGet } from "../api/client";
import type { ClaimRow, ClaimOutcome } from "../api/types";
import DecisionCard from "../components/DecisionCard";

function columnsFor(rows: ClaimRow[]): string[] {
  const keys = new Set<string>();
  for (const row of rows) {
    for (const key of Object.keys(row)) keys.add(key);
  }
  keys.delete("claim_id");
  return ["claim_id", ...Array.from(keys)];
}

function cellText(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function ReviewClaims() {
  const [rows, setRows] = useState<ClaimRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ClaimOutcome | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  function loadClaims() {
    setLoading(true);
    setError(null);
    apiGet<ClaimRow[]>("/claims")
      .then((data) => setRows(data))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadClaims();
  }, []);

  function selectClaim(claimId: string) {
    if (selectedId === claimId) {
      setSelectedId(null);
      setDetail(null);
      setDetailError(null);
      return;
    }
    setSelectedId(claimId);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    apiGet<ClaimOutcome>("/claims/" + claimId)
      .then((data) => setDetail(data))
      .catch((e: unknown) =>
        setDetailError(e instanceof Error ? e.message : String(e))
      )
      .finally(() => setDetailLoading(false));
  }

  const columns = columnsFor(rows);

  return (
    <div>
      <h1>Claims Review</h1>
      <p className="pc-caption">
        Browse every submitted claim and inspect the full AI pipeline decision for
        each.
      </p>
      <hr className="pc-divider" />

      {loading && <span className="pc-spinner" />}

      {!loading && error && (
        <div className="pc-alert pc-alert-error">{error}</div>
      )}

      {!loading && !error && rows.length === 0 && (
        <div className="pc-alert pc-alert-info">
          No claims have been submitted yet. Head to <strong>Submit Claim</strong> to
          create your first one.
        </div>
      )}

      {!loading && !error && rows.length > 0 && (
        <>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <span className="pc-section-title">All claims · {rows.length}</span>
            <button className="pc-btn pc-btn-ghost" onClick={loadClaims}>
              Refresh
            </button>
          </div>

          <div className="pc-table-wrap">
            <table className="pc-table">
              <thead>
                <tr>
                  {columns.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const id = row.claim_id;
                  const isSelected = id === selectedId;
                  return (
                    <tr
                      key={id}
                      className={isSelected ? "clickable selected" : "clickable"}
                      onClick={() => selectClaim(id)}
                    >
                      {columns.map((col) => (
                        <td
                          key={col}
                          style={{
                            maxWidth: 280,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          {cellText(row[col])}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {selectedId && (
            <>
              <hr className="pc-divider" />
              <h2 className="pc-section-title">Inspect a claim</h2>
              {detailLoading && <span className="pc-spinner" />}
              {!detailLoading && detailError && (
                <div className="pc-alert pc-alert-error">{detailError}</div>
              )}
              {!detailLoading && !detailError && detail && (
                <DecisionCard outcome={detail} />
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
