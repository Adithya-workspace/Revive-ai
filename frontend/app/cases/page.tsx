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

const POLICY_OPTIONS = [
  { value: "APPROVED", label: "Approved" },
  { value: "NEEDS_HUMAN", label: "Needs Human" },
  { value: "REJECTED", label: "Rejected" },
];

export default function RecoveryCasesPage() {
  const [policyDecision, setPolicyDecision] = useState("");

  const { data: merchants } = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
  });
  const merchantId = merchants?.[0]?.id;

  const { data, isLoading } = useQuery({
    queryKey: ["actions", merchantId, policyDecision],
    queryFn: () =>
      fetchActions(merchantId!, {
        policy_decision: policyDecision || undefined,
        limit: 100,
      }),
    enabled: !!merchantId,
  });

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text">Recovery Cases</h1>
        <p className="text-sm text-text-muted mt-1">
          Every case with a strategized recovery action, and where it stands in the pipeline.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <Select
          options={POLICY_OPTIONS}
          placeholder="All policy decisions"
          value={policyDecision}
          onChange={(e) => setPolicyDecision(e.target.value)}
        />
        {data && (
          <p className="text-xs text-text-faint ml-auto tabular-nums">
            {data.total_count.toLocaleString("en-IN")} cases
          </p>
        )}
      </div>

      <Card className="p-0 overflow-hidden">
        {isLoading ? (
          <PulseLoader label="Loading recovery cases..." />
        ) : !data || data.actions.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-sm text-text-muted">No cases match this filter.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs font-medium text-text-faint uppercase tracking-wide">
                  <th className="px-5 py-3">Case</th>
                  <th className="px-5 py-3">Customer</th>
                  <th className="px-5 py-3">Action</th>
                  <th className="px-5 py-3 text-right">Expected Value</th>
                  <th className="px-5 py-3">Policy</th>
                  <th className="px-5 py-3">Execution</th>
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
                    <td className="px-5 py-3 text-right font-mono tabular-nums text-recovered">
                      {formatCurrency(a.expected_value)}
                    </td>
                    <td className="px-5 py-3">
                      {a.policy_decision ? (
                        <StatusBadge value={a.policy_decision} />
                      ) : (
                        <span className="text-xs text-text-faint">Pending</span>
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