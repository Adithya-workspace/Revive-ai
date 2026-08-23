const STATUS_STYLES: Record<string, { bg: string; text: string; dot: string }> = {
    recovered: { bg: "bg-recovered-dim", text: "text-recovered", dot: "bg-recovered" },
    open: { bg: "bg-accent-dim", text: "text-accent", dot: "bg-accent" },
    escalated: { bg: "bg-at-risk-dim", text: "text-at-risk", dot: "bg-at-risk" },
    stopped: { bg: "bg-critical-dim", text: "text-critical", dot: "bg-critical" },
    APPROVED: { bg: "bg-recovered-dim", text: "text-recovered", dot: "bg-recovered" },
    NEEDS_HUMAN: { bg: "bg-at-risk-dim", text: "text-at-risk", dot: "bg-at-risk" },
    REJECTED: { bg: "bg-critical-dim", text: "text-critical", dot: "bg-critical" },
    high: { bg: "bg-critical-dim", text: "text-critical", dot: "bg-critical" },
    medium: { bg: "bg-at-risk-dim", text: "text-at-risk", dot: "bg-at-risk" },
    low: { bg: "bg-surface-raised", text: "text-text-muted", dot: "bg-text-faint" },
  };
  
  export function StatusBadge({ value }: { value: string }) {
    const style = STATUS_STYLES[value] || STATUS_STYLES.low;
  
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${style.bg} ${style.text}`}
      >
        <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
        {value.replace(/_/g, " ").toLowerCase()}
      </span>
    );
  }