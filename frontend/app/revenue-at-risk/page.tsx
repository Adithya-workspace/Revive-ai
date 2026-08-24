"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { fetchMerchants, fetchCases } from "@/lib/api";
import { formatCurrency, formatPercent, formatDate, shortId } from "@/lib/format";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PulseLoader } from "@/components/PulseLoader";
import { Button } from "@/components/ui/Button";
import { ChevronLeft, ChevronRight } from "lucide-react";

const SCENARIO_OPTIONS = [
  { value: "failed_payment", label: "Failed Payment" },
  { value: "checkout_abandonment", label: "Checkout Abandonment" },
  { value: "overdue_receivable", label: "Overdue Receivable" },
];

const PRIORITY_OPTIONS = [
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

const STATUS_OPTIONS = [
  { value: "open", label: "Open" },
  { value: "recovered", label: "Recovered" },
  { value: "escalated", label: "Escalated" },
  { value: "stopped", label: "Stopped" },
];

const PAGE_SIZE = 25;

export default function RevenueAtRiskPage() {
  const [scenario, setScenario] = useState("");
  const [priority, setPriority] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);

  const { data: merchants } = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
  });
  const merchantId = merchants?.[0]?.id;

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["cases", merchantId, scenario, priority, status, page],
    queryFn: () =>
      fetchCases(merchantId!, {
        scenario: scenario || undefined,
        priority: priority || undefined,
        status: status || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
    enabled: !!merchantId,
  });

  const totalPages = data ? Math.ceil(data.total_count / PAGE_SIZE) : 0;

  function resetToFirstPage(setter: (v: string) => void) {
    return (value: string) => {
      setter(value);
      setPage(0);
    };
  }

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text">Revenue at Risk</h1>
        <p className="text-sm text-text-muted mt-1">
          Every case detected by REVIVE, with recommended action and current status.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <Select
          options={SCENARIO_OPTIONS}
          placeholder="All scenarios"
          value={scenario}
          onChange={(e) => resetToFirstPage(setScenario)(e.target.value)}
        />
        <Select
          options={PRIORITY_OPTIONS}
          placeholder="All priorities"
          value={priority}
          onChange={(e) => resetToFirstPage(setPriority)(e.target.value)}
        />
        <Select
          options={STATUS_OPTIONS}
          placeholder="All statuses"
          value={status}
          onChange={(e) => resetToFirstPage(setStatus)(e.target.value)}
        />
        {data && (
          <p className="text-xs text-text-faint ml-auto tabular-nums">
            {data.total_count.toLocaleString("en-IN")} cases
          </p>
        )}
      </div>

      <Card className="p-0 overflow-hidden">
        {isLoading ? (
          <PulseLoader label="Loading cases..." />
        ) : !data || data.cases.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-sm text-text-muted">No cases match these filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs font-medium text-text-faint uppercase tracking-wide">
                  <th className="px-5 py-3">Case</th>
                  <th className="px-5 py-3">Customer</th>
                  <th className="px-5 py-3">Type</th>
                  <th className="px-5 py-3 text-right">Amount at Risk</th>
                  <th className="px-5 py-3 text-right">Recovery Prob.</th>
                  <th className="px-5 py-3">Priority</th>
                  <th className="px-5 py-3">Recommended Action</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Detected</th>
                </tr>
              </thead>
              <tbody>
                {data.cases.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-border last:border-0 transition-colors duration-150 ease-out hover:bg-surface-raised"
                  >
                    <td className="px-5 py-3">
                      <Link
                        href={`/cases/${c.id}`}
                        className="font-mono text-xs text-accent hover:underline"
                      >
                        {shortId(c.id)}
                      </Link>
                    </td>
                    <td className="px-5 py-3 text-text">{c.customer_name}</td>
                    <td className="px-5 py-3 text-text-muted capitalize">
                      {c.scenario.replace(/_/g, " ")}
                    </td>
                    <td className="px-5 py-3 text-right font-mono tabular-nums text-text">
                      {formatCurrency(c.amount_at_risk)}
                    </td>
                    <td className="px-5 py-3 text-right font-mono tabular-nums text-text-muted">
                      {c.recovery_probability !== null
                        ? formatPercent(c.recovery_probability)
                        : "—"}
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge value={c.priority} />
                    </td>
                    <td className="px-5 py-3 text-text-muted text-xs">
                      {c.recommended_action ? c.recommended_action.replace(/_/g, " ") : "Not yet strategized"}
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge value={c.status} />
                    </td>
                    <td className="px-5 py-3 text-text-faint text-xs">
                      {formatDate(c.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {data && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-text-faint">
            Page {page + 1} of {totalPages}
            {isFetching && <span className="ml-2 text-accent">Updating...</span>}
          </p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              <ChevronLeft size={14} />
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
            >
              Next
              <ChevronRight size={14} />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}