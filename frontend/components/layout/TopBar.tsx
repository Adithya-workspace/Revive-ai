"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/Button";
import { Play, Loader2, CheckCircle2, XCircle, Menu } from "lucide-react";
import { runDetectionScan } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

export function TopBar({
  merchantName,
  merchantId,
  onMenuClick,
}: {
  merchantName?: string;
  merchantId?: string;
  onMenuClick?: () => void;
}) {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const mutation = useMutation({
    mutationFn: () => runDetectionScan(merchantId!),
    onSuccess: (data) => {
      setFeedback({
        type: "success",
        text: `${data.new_cases_created.total} new case(s) — ${formatCurrency(data.total_amount_at_risk_detected)} at risk.`,
      });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
      queryClient.invalidateQueries({ queryKey: ["analytics-page"] });
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      setTimeout(() => setFeedback(null), 6000);
    },
    onError: () => {
      setFeedback({ type: "error", text: "Scan failed — check the backend is running." });
      setTimeout(() => setFeedback(null), 6000);
    },
  });

  return (
    <header className="h-16 border-b border-border bg-ink/80 backdrop-blur-sm sticky top-0 z-10 flex items-center justify-between px-4 sm:px-6 gap-3">
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMenuClick}
          className="lg:hidden shrink-0 p-1.5 rounded-lg text-text-muted hover:text-text hover:bg-surface-raised transition-colors duration-150"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
        <div className="min-w-0">
          <p className="text-sm font-medium text-text truncate">
            {merchantName || "Loading merchant..."}
          </p>
          <p className="text-xs text-text-faint hidden sm:block">Simulation environment</p>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {feedback && (
          <span
            className={`hidden sm:inline-flex items-center gap-1.5 text-xs ${
              feedback.type === "success" ? "text-recovered" : "text-critical"
            }`}
          >
            {feedback.type === "success" ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
            {feedback.text}
          </span>
        )}
        <Button
          variant="primary"
          size="sm"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !merchantId}
        >
          {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          <span className="hidden sm:inline">Run Full Scan</span>
        </Button>
      </div>
    </header>
  );
}