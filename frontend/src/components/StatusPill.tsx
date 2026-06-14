// Status pill — ported from render.py _STATUS_THEME / status_pill().

interface Theme {
  label: string;
  icon: string;
  color: string;
  bg: string;
  border: string;
}

const STATUS_THEME: Record<string, Theme> = {
  APPROVED:      { label: "Approved",      icon: "✅", color: "#1A5C3A", bg: "#ECFAF3", border: "#7DD3A8" },
  PARTIAL:       { label: "Partial",       icon: "🟡", color: "#7A4A10", bg: "#FEF7E8", border: "#D4A853" },
  REJECTED:      { label: "Rejected",      icon: "❌", color: "#8B1A1A", bg: "#FEF0F0", border: "#D98080" },
  MANUAL_REVIEW: { label: "Manual Review", icon: "🔍", color: "#5E4A24", bg: "#FBF5E9", border: "#C9A962" },
  STOPPED:       { label: "Stopped",       icon: "⏹",  color: "#4A4540", bg: "#EDE9E2", border: "#C0B8AD" },
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
