"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { fetchMerchants, fetchEscalations } from "@/lib/api";
import { formatCurrency, formatPercent, formatDate, shortId } from "@/lib/format";
import { Card } from "@/components/ui/Card";
import { PulseLoader } from "@/components/PulseLoader";
import { ErrorState } from "@/components/ui/ErrorState";
import { ShieldAlert, ArrowRight } from "lucide-react";

export default function EscalationsPage() {
  const { data: merchants } = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
  });
  const merchantId = merchants?.[0]?.id;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["escalations", merchantId],
    queryFn: () => fetchEscalations(merchantId!, 100),
    enabled: !!merchantId,
  });

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text">Escalations</h1>
        <p className="text-sm text-text-muted mt-1">
          Cases waiting on your review before REVIVE can act.
        </p>
      </div>

      {isLoading ? (
        <PulseLoader label="Loading escalations..." />
      ) : isError ? (
        <ErrorState message="Couldn't load escalations." />
      ) : !data || data.escalations.length === 0 ? (
        <Card className="py-16 text-center">
          <ShieldAlert size={28} className="mx-auto text-text-faint mb-3" />
          <p className="text-sm text-text-muted">
            Nothing needs your review right now. All approved and rejected cases
            are handled automatically.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-text-faint">
            {data.total_count} case{data.total_count !== 1 ? "s" : ""} waiting on review
          </p>
          {data.escalations.map((e) => (
            <Link key={e.case_id} href={`/cases/${e.case_id}?from=escalations`}>
              <Card
                hoverable
                className="animate-fade-in-up flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs text-accent">
                      {shortId(e.case_id)}
                    </span>
                    <span className="text-sm text-text font-medium">
                      {e.customer_name}
                    </span>
                    <span className="text-xs text-text-faint capitalize">
                      {e.scenario?.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="text-sm text-text-muted mt-1.5">{e.policy_reason}</p>
                  <p className="text-xs text-text-faint mt-1">
                    Recommended: {e.recommended_action.replace(/_/g, " ")} ·{" "}
                    {formatPercent(e.confidence)} confidence
                  </p>
                </div>
                <div className="flex items-center justify-between sm:justify-end gap-4 shrink-0">
                  <p className="font-mono tabular-nums text-lg font-semibold text-at-risk">
                    {formatCurrency(e.amount_at_risk || 0)}
                  </p>
                  <ArrowRight size={16} className="text-text-faint" />
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}