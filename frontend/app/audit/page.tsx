"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { fetchMerchants, fetchAuditEvents } from "@/lib/api";
import { formatDate, shortId } from "@/lib/format";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { PulseLoader } from "@/components/PulseLoader";

const EVENT_TYPE_OPTIONS = [
  { value: "CASE_DETECTED", label: "Case Detected" },
  { value: "RECOVERY_SCORE_CALCULATED", label: "Recovery Score Calculated" },
  { value: "DIAGNOSIS_COMPLETED", label: "Diagnosis Completed" },
  { value: "STRATEGY_SELECTED", label: "Strategy Selected" },
  { value: "POLICY_DECISION", label: "Policy Decision" },
  { value: "ACTION_EXECUTED", label: "Action Executed" },
  { value: "VERIFICATION_COMPLETED", label: "Verification Completed" },
  { value: "CASE_RECOVERED", label: "Case Recovered" },
  { value: "HUMAN_DECISION_SUBMITTED", label: "Human Decision Submitted" },
];

export default function AuditTrailPage() {
  const [eventType, setEventType] = useState("");

  const { data: merchants } = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
  });
  const merchantId = merchants?.[0]?.id;

  const { data, isLoading } = useQuery({
    queryKey: ["audit-events", merchantId, eventType],
    queryFn: () =>
      fetchAuditEvents(merchantId!, { event_type: eventType || undefined, limit: 100 }),
    enabled: !!merchantId,
  });

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text">Audit Trail</h1>
        <p className="text-sm text-text-muted mt-1">
          Every event REVIVE has recorded, across every case, fully searchable.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <Select
          options={EVENT_TYPE_OPTIONS}
          placeholder="All event types"
          value={eventType}
          onChange={(e) => setEventType(e.target.value)}
        />
        {data && (
          <p className="text-xs text-text-faint ml-auto tabular-nums">
            {data.total_count.toLocaleString("en-IN")} events
          </p>
        )}
      </div>

      <Card className="p-0 overflow-hidden">
        {isLoading ? (
          <PulseLoader label="Loading audit trail..." />
        ) : !data || data.events.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <p className="text-sm text-text-muted">No audit events recorded yet.</p>
            <p className="text-xs text-text-faint">
              Run the backfill script (
              <code className="font-mono">python -m scripts.backfill_audit_trail</code>) to
              populate historical events.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {data.events.map((e) => (
              <div
                key={e.id}
                className="px-5 py-3 flex items-start gap-4 transition-colors duration-150 ease-out hover:bg-surface-raised"
              >
                <p className="text-xs font-mono text-text-faint w-40 shrink-0 pt-0.5">
                  {formatDate(e.created_at)}
                </p>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm text-text font-medium">
                      {e.event_type.replace(/_/g, " ")}
                    </p>
                    <span className="text-xs text-text-faint">{e.actor}</span>
                  </div>
                  {e.result && <p className="text-xs text-text-muted mt-0.5">{e.result}</p>}
                </div>
                <Link
                  href={`/cases/${e.case_id}?from=audit-trail`}
                  className="text-xs font-mono text-accent hover:underline shrink-0"
                >
                  {shortId(e.case_id)}
                </Link>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}