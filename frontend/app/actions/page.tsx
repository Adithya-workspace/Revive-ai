"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { fetchMerchants, fetchActions } from "@/lib/api";
import { formatCurrency, formatPercent, formatDate, shortId } from "@/lib/format";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PulseLoader } from "@/components/PulseLoader";

const ACTION_OPTIONS = [
  { value: "RETRY_PAYMENT", label: "Retry Payment" },
  { value: "DELAYED_RETRY", label: "Delayed Retry" },
  { value: "SEND_PAYMENT_REMINDER", label: "Send Payment Reminder" },
  { value: "SEND_CHECKOUT_RECOVERY_MESSAGE", label: "Send Checkout Recovery Message" },
  { value: "SEND_OVERDUE_REMINDER", label: "Send Overdue Reminder" },
  { value: "TRACK_PROMISE_TO_PAY", label: "Track Promise to Pay" },
  { value: "ESCALATE_TO_HUMAN", label: "Escalate to Human" },
  { value: "STOP_RECOVERY_ATTEMPTS", label: "Stop Recovery Attempts" },
];

export default function ActionsPage() {
  const [actionType, setActionType] = useState("");

  const { data: merchants } = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
  });
  const merchantId = merchants?.[0]?.id;

  const { data, isLoading } = useQuery({
    queryKey: ["actions-page", merchantId, actionType],
    queryFn: () =>
      fetchActions(merchantId!, { action_type: actionType || undefined, limit: 100 }),
    enabled: !!merchantId,
  });

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text">Actions</h1>
        <p className="text-sm text-text-muted mt-1">
          Every recovery action REVIVE has proposed, and its execution outcome.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <Select
          options={ACTION_OPTIONS}
          placeholder="All action types"
          value={actionType}
          onChange={(e) => setActionType(e.target.value)}
        />
        {data && (
          <p className="text-xs text-text-faint ml-auto tabular-nums">
            {data.total_count.toLocaleString("en-IN")} actions
          </p>
        )}
      </div>

      <Card className="p-0 overflow-hidden">
        {isLoading ? (
          <PulseLoader label="Loading actions..." />
        ) : !data || data.actions.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-sm text-text-muted">No actions match this filter.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs font-medium text-text-faint uppercase tracking-wide">
                  <th className="px-5 py-3">Case</th>
                  <th className="px-5 py-3">Customer</th>
                  <th className="px-5 py-3">Action</th>
                  <th className="px-5 py-3 text-right">Confidence</th>
                  <th className="px-5 py-3">Mode</th>
                  <th className="px-5 py-3">Result</th>
                  <th className="px-5 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {data.actions.map((a) => (
                  <tr
                    key={a.id}
                    className="border-b border-border last:border-0 transition-colors duration-150 ease-out hover:bg-surface-raised"
                  >
                    <td className="px-5 py-3">
                      <Link
                        href={`/cases/${a.case_id}`}
                        className="font-mono text-xs text-accent hover:underline"
                      >
                        {shortId(a.case_id)}
                      </Link>
                    </td>
                    <td className="px-5 py-3 text-text">{a.customer_name}</td>
                    <td className="px-5 py-3 text-text-muted text-xs">
                      {a.action.replace(/_/g, " ")}
                    </td>
                    <td className="px-5 py-3 text-right font-mono tabular-nums text-text-muted">
                      {formatPercent(a.confidence)}
                    </td>
                    <td className="px-5 py-3">
                      {a.execution_mode ? (
                        <span className="text-xs px-2 py-0.5 rounded bg-surface-raised text-text-muted font-mono">
                          {a.execution_mode}
                        </span>
                      ) : (
                        <span className="text-xs text-text-faint">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge value={a.execution_status} />
                    </td>
                    <td className="px-5 py-3 text-text-faint text-xs">
                      {formatDate(a.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}