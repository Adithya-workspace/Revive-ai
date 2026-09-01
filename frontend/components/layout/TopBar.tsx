"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/Button";
import { Play, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { runDetectionScan } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

export function TopBar({ merchantName, merchantId }: { merchantName?: string; merchantId?: string }) {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const mutation = useMutation({
    mutationFn: () => runDetectionScan(merchantId!),
    onSuccess: (data) => {
      setFeedback({
        type: "success",
        text: `${data.new_cases_created.total} new case(s) found — ${formatCurrency(data.total_amount_at_risk_detected)} at risk.`,
      });
      // Refresh anything on screen that depends on case/analytics data
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
    <header className="h-16 border-b border-border bg-ink/80 backdrop-blur-sm sticky top-0 z-10 flex items-center justify-between px-6 gap-4">
      <div className="min-w-0">
        <p className="text-sm font-medium text-text truncate">
          {merchantName || "Loading merchant..."}
        </p>
        <p className="text-xs text-text-faint">Simulation environment</p>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        {feedback && (
          <span
            className={`inline-flex items-center gap-1.5 text-xs ${
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
          Run Full Scan
        </Button>
      </div>
    </header>
  );
}