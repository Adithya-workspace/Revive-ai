"use client";

import { useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { fetchMerchants, fetchCaseDetail, submitHumanDecision } from "@/lib/api";
import { formatCurrency, formatPercent, formatDate, shortId } from "@/lib/format";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PulseLoader } from "@/components/PulseLoader";
import { ErrorState } from "@/components/ui/ErrorState";
import { ArrowLeft, CheckCircle2, XCircle } from "lucide-react";


const BACK_DESTINATIONS: Record<string, { label: string; path: string }> = {
    "revenue-at-risk": { label: "Revenue at Risk", path: "/revenue-at-risk" },
    "recovery-cases": { label: "Recovery Cases", path: "/cases" },
    "actions": { label: "Actions", path: "/actions" },
    "escalations": { label: "Escalations", path: "/escalations" },
    "audit-trail": { label: "Audit Trail", path: "/audit" },
  };
  
  export default function CaseDetailPage() {
    const params = useParams<{ id: string }>();
    const searchParams = useSearchParams();
    const caseId = params.id as string;
    const queryClient = useQueryClient();
  
    const fromKey = searchParams.get("from") || "revenue-at-risk";
    const backDestination = BACK_DESTINATIONS[fromKey] || BACK_DESTINATIONS["revenue-at-risk"];
  const [approverNote, setApproverNote] = useState("");

  const { data: merchants } = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
  });
  const merchantId = merchants?.[0]?.id;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["case-detail", merchantId, caseId],
    queryFn: () => fetchCaseDetail(merchantId!, caseId),
    enabled: !!merchantId,
  });

  const decisionMutation = useMutation({
    mutationFn: (decision: "APPROVED" | "REJECTED") =>
      submitHumanDecision(merchantId!, caseId, decision, approverNote || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["case-detail", merchantId, caseId] });
      setApproverNote("");
    },
  });

  if (isLoading) {
    return <PulseLoader label="Loading case..." />;
  }

  if (isError || !data) {
    return <ErrorState message="Couldn't load this case." />;
  }

  const { case: c, customer, diagnosis, strategy, policy, action_result, audit_trail } = data;

  return (
    <div className="space-y-6 max-w-5xl">
        <div>
        <Link
          href={backDestination.path}
          className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text transition-colors duration-150"
        >
          <ArrowLeft size={14} />
          Back to {backDestination.label}
        </Link>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-display text-2xl font-semibold text-text">
              Case {shortId(c.id)}
            </h1>
            <StatusBadge value={c.status} />
          </div>
          <p className="text-sm text-text-muted mt-1 capitalize">
            {c.scenario.replace(/_/g, " ")} · Detected {formatDate(c.created_at)}
          </p>
        </div>
        <div className="text-right">
          <p className="font-mono tabular-nums text-2xl font-semibold text-text">
            {formatCurrency(c.amount_at_risk)}
          </p>
          <p className="text-xs text-text-faint mt-1">
            {c.recovery_probability !== null
              ? `${formatPercent(c.recovery_probability)} recovery probability`
              : "Not yet scored"}
          </p>
        </div>
      </div>

      {/* Human approval banner — only shown when actually needed */}
      {policy?.needs_human_decision && (
        <Card className="border-at-risk/40 bg-at-risk-dim animate-fade-in-up">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-at-risk">Needs your review</p>
              <p className="text-sm text-text-muted mt-1">{policy.reason}</p>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            <input
              type="text"
              placeholder="Optional note (visible in audit trail)"
              value={approverNote}
              onChange={(e) => setApproverNote(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-faint focus:border-accent transition-colors duration-150"
            />
            <div className="flex gap-3">
              <Button
                variant="primary"
                onClick={() => decisionMutation.mutate("APPROVED")}
                disabled={decisionMutation.isPending}
                className="!bg-recovered"
              >
                <CheckCircle2 size={16} />
                Approve
              </Button>
              <Button
                variant="secondary"
                onClick={() => decisionMutation.mutate("REJECTED")}
                disabled={decisionMutation.isPending}
              >
                <XCircle size={16} />
                Reject
              </Button>
            </div>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <h2 className="font-display text-sm font-semibold text-text mb-3">Customer</h2>
          {customer ? (
            <div className="space-y-1 text-sm">
              <p className="text-text">{customer.name}</p>
              <p className="text-text-muted">{customer.email}</p>
              <p className="text-text-muted">{customer.phone}</p>
            </div>
          ) : (
            <p className="text-sm text-text-faint">No customer on record</p>
          )}
        </Card>

        <Card>
          <h2 className="font-display text-sm font-semibold text-text mb-3">Action Result</h2>
          {action_result ? (
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 rounded bg-surface-raised text-text-muted font-mono">
                  {action_result.mode}
                </span>
                <StatusBadge value={action_result.status} />
              </div>
              <p className="text-text-muted text-xs">{action_result.result_detail}</p>
              {action_result.verified && (
                <p className="text-xs text-text-faint pt-1 border-t border-border mt-2">
                  Verified: {action_result.verification_detail}
                </p>
              )}
            </div>
          ) : (
            <p className="text-sm text-text-faint">Not yet executed</p>
          )}
        </Card>
      </div>

      <Card>
        <h2 className="font-display text-sm font-semibold text-text mb-3">Diagnosis</h2>
        {diagnosis ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm text-text">{diagnosis.diagnosis}</p>
              <span className="text-xs px-2 py-0.5 rounded bg-surface-raised text-text-muted font-mono">
                {diagnosis.diagnosis_source} · {formatPercent(diagnosis.confidence)}
              </span>
            </div>
            <p className="text-sm text-text-muted">{diagnosis.reasoning_summary}</p>
            {diagnosis.evidence?.length > 0 && (
              <ul className="space-y-1 pt-2 border-t border-border">
                {diagnosis.evidence.map((e: string, i: number) => (
                  <li key={i} className="text-xs text-text-faint flex gap-2">
                    <span className="text-text-faint">·</span> {e}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <p className="text-sm text-text-faint">Not yet diagnosed</p>
        )}
      </Card>

      <Card>
        <h2 className="font-display text-sm font-semibold text-text mb-3">
          Strategy & Policy
        </h2>
        {strategy ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm text-text font-medium">
                {strategy.action.replace(/_/g, " ")}
              </p>
              <p className="font-mono tabular-nums text-sm text-recovered">
                Expected: {formatCurrency(strategy.expected_value)}
              </p>
            </div>
            <p className="text-sm text-text-muted">{strategy.reason}</p>
            {policy && (
              <div className="pt-3 border-t border-border flex items-start gap-3">
                <StatusBadge value={policy.decision} />
                <p className="text-xs text-text-faint">{policy.reason}</p>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-text-faint">Not yet strategized</p>
        )}
      </Card>

      <Card>
        <h2 className="font-display text-sm font-semibold text-text mb-3">Audit Trail</h2>
        {audit_trail.length > 0 ? (
          <div className="space-y-3">
            {audit_trail.map((e: any, i: number) => (
              <div key={i} className="flex gap-3 text-sm">
                <p className="text-text-faint text-xs font-mono w-32 shrink-0 pt-0.5">
                  {formatDate(e.created_at)}
                </p>
                <div>
                  <p className="text-text">
                    {e.event_type.replace(/_/g, " ")}
                    <span className="text-text-faint ml-2 text-xs">{e.actor}</span>
                  </p>
                  {e.result && <p className="text-text-muted text-xs mt-0.5">{e.result}</p>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-text-faint">
            No audit events recorded yet for this case.
          </p>
        )}
      </Card>
    </div>
  );
}