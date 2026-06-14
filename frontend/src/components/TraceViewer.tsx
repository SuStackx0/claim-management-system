// Decision trace timeline — ported from render.py render_trace().
// Each step is a collapsible row showing checks, confidence factors and errors.
// Check `detail` / `error` payloads are arbitrary objects; we render them as
// clean humanized key/value rows rather than dumping raw JSON.

import { useState } from "react";
import type { Trace, TraceStep, TraceStatus } from "../api/types";

const TRACE_ICONS: Record<TraceStatus, string> = {
  PASS: "✅", FAIL: "❌", DEGRADED: "⚠️", SKIPPED: "⏭️",
};
const TRACE_THEME: Record<TraceStatus, { color: string; bg: string }> = {
  PASS:     { color: "#1A5C3A", bg: "#ECFAF3" },
  FAIL:     { color: "#8B1A1A", bg: "#FEF0F0" },
  DEGRADED: { color: "#7A4A10", bg: "#FEF7E8" },
  SKIPPED:  { color: "#4A4540", bg: "#EDE9E2" },
};
const ORDER: TraceStatus[] = ["PASS", "FAIL", "DEGRADED", "SKIPPED"];

// snake_case / camelCase / kebab-case -> "Title Case"
function humanize(key: string): string {
  return key
    .replace(/[_-]+/g, " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function Scalar({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === "")
    return <span className="pc-muted">—</span>;
  if (typeof value === "boolean")
    return <span>{value ? "Yes" : "No"}</span>;
  if (typeof value === "number")
    return <span>{Number.isInteger(value) ? value.toLocaleString("en-IN") : String(value)}</span>;
  return <span>{String(value)}</span>;
}

// Recursively render an arbitrary value as readable rows — never raw JSON.
function DetailView({ value }: { value: unknown }) {
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="pc-muted">none</span>;
    const allScalar = value.every((x) => !isObject(x) && !Array.isArray(x));
    if (allScalar)
      return <span>{value.map((x) => (x == null ? "—" : String(x))).join(", ")}</span>;
    return (
      <ul className="pc-kv-list">
        {value.map((item, i) => (
          <li key={i}><DetailView value={item} /></li>
        ))}
      </ul>
    );
  }

  if (isObject(value)) {
    const entries = Object.entries(value);
    if (entries.length === 0) return <span className="pc-muted">—</span>;
    return (
      <dl className="pc-kv">
        {entries.map(([k, v]) => (
          <div className="pc-kv-row" key={k}>
            <dt className="pc-kv-key">{humanize(k)}</dt>
            <dd className="pc-kv-val">
              {isObject(v) || Array.isArray(v) ? <DetailView value={v} /> : <Scalar value={v} />}
            </dd>
          </div>
        ))}
      </dl>
    );
  }

  return <Scalar value={value} />;
}

function StepRow({ step }: { step: TraceStep }) {
  const [open, setOpen] = useState(false);
  const theme = TRACE_THEME[step.status] ?? { color: "#4A4540", bg: "#EDE9E2" };
  const icon = TRACE_ICONS[step.status] ?? "•";
  const checks = step.checks ?? [];
  const conf = step.confidence_entries ?? [];

  return (
    <div className="pc-step">
      <button className="pc-step-head" onClick={() => setOpen((o) => !o)} type="button">
        <span className="pc-step-dot" style={{ color: theme.color, background: theme.bg }}>
          {icon}
        </span>
        <span>
          <span className="pc-step-name">{step.step}</span>{" "}
          <span className="pc-step-meta">
            · {step.agent} · {step.duration_ms} ms · {step.status}
          </span>
        </span>
        <span className="pc-step-meta" style={{ marginLeft: "auto" }}>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="pc-step-body">
          {checks.length > 0 && (
            <div className="pc-checks">
              {checks.map((c, i) => (
                <div className="pc-check" key={i}>
                  <div className="pc-check-head">
                    <strong>{c.check}</strong>
                    <span className="pc-muted">→ {c.result}</span>
                    {c.rule_ref ? <code className="pc-mono pc-rule">{c.rule_ref}</code> : null}
                  </div>
                  {c.detail != null && (
                    <div className="pc-detail"><DetailView value={c.detail} /></div>
                  )}
                </div>
              ))}
            </div>
          )}

          {step.error != null && (
            <div className="pc-error-box">
              <div className="pc-error-title">Error</div>
              <DetailView value={step.error} />
            </div>
          )}

          {conf.map((e, i) => (
            <div key={i} className="pc-step-meta">
              confidence ×{e.factor} — {e.reason}
            </div>
          ))}

          {checks.length === 0 && conf.length === 0 && step.error == null && (
            <div className="pc-step-meta">No additional detail.</div>
          )}
        </div>
      )}
    </div>
  );
}

export default function TraceViewer({ trace }: { trace?: Trace }) {
  const steps = trace?.steps ?? [];
  if (steps.length === 0) return null;

  const counts: Partial<Record<TraceStatus, number>> = {};
  for (const s of steps) counts[s.status] = (counts[s.status] ?? 0) + 1;

  return (
    <div>
      <h3 className="pc-section-title">Decision trace</h3>
      <div className="pc-chiprow">
        {ORDER.filter((k) => counts[k]).map((k) => {
          const th = TRACE_THEME[k];
          return (
            <span key={k} className="pc-pill" style={{ color: th.color, background: th.bg }}>
              {TRACE_ICONS[k]} {counts[k]} {k.toLowerCase()}
            </span>
          );
        })}
      </div>
      {steps.map((s, i) => (
        <StepRow key={i} step={s} />
      ))}
    </div>
  );
}
