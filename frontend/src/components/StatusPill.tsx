// Status pill — ported from render.py _STATUS_THEME / status_pill().

interface Theme {
  label: string;
  icon: string;
  color: string;
  bg: string;
  border: string;
}

const STATUS_THEME: Record<string, Theme> = {
  APPROVED:      { label: "Approved",      icon: "✅", color: "#15803d", bg: "#dcfce7", border: "#86efac" },
  PARTIAL:       { label: "Partial",       icon: "🟡", color: "#b45309", bg: "#fef3c7", border: "#fcd34d" },
  REJECTED:      { label: "Rejected",      icon: "❌", color: "#b91c1c", bg: "#fee2e2", border: "#fca5a5" },
  MANUAL_REVIEW: { label: "Manual Review", icon: "🔵", color: "#1d4ed8", bg: "#dbeafe", border: "#93c5fd" },
  STOPPED:       { label: "Stopped",       icon: "⏹", color: "#475569", bg: "#e2e8f0", border: "#cbd5e1" },
};

export default function StatusPill({ status, text }: { status: string; text?: string }) {
  const t = STATUS_THEME[status] ?? STATUS_THEME.MANUAL_REVIEW;
  return (
    <span
      className="pc-pill"
      style={{ color: t.color, background: t.bg, borderColor: t.border }}
    >
      {t.icon} {text ?? t.label}
    </span>
  );
}
