"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchPolicies, fetchMerchants } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { PulseLoader } from "@/components/PulseLoader";
import { ShieldCheck } from "lucide-react";

export default function SettingsPage() {
  const { data: merchants } = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
  });

  const { data: policies, isLoading } = useQuery({
    queryKey: ["policies"],
    queryFn: fetchPolicies,
  });

  const merchant = merchants?.[0];

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text">Settings</h1>
        <p className="text-sm text-text-muted mt-1">
          Merchant details and the policy limits governing automatic recovery actions.
        </p>
      </div>

      <Card>
        <h2 className="font-display text-sm font-semibold text-text mb-3">Merchant</h2>
        {merchant ? (
          <div className="space-y-1 text-sm">
            <p className="text-text">{merchant.name}</p>
            <p className="text-text-muted">{merchant.email}</p>
          </div>
        ) : (
          <p className="text-sm text-text-faint">Loading...</p>
        )}
      </Card>

      <Card>
        <div className="flex items-center gap-2 mb-1">
          <ShieldCheck size={16} className="text-accent" />
          <h2 className="font-display text-sm font-semibold text-text">
            Policy Guardrails
          </h2>
        </div>
        <p className="text-xs text-text-faint mb-4">
          These deterministic limits govern every automatic recovery action — the AI
          proposes, these policies dispose. Read-only in this build.
        </p>

        {isLoading ? (
          <PulseLoader label="Loading policies..." />
        ) : !policies || policies.length === 0 ? (
          <p className="text-sm text-text-faint">No policies configured.</p>
        ) : (
          <div className="divide-y divide-border">
            {policies.map((p) => (
              <div key={p.key} className="py-4 flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm text-text font-medium">
                    {p.key.replace(/_/g, " ")}
                  </p>
                  <p className="text-xs text-text-muted mt-1">{p.description}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="font-mono tabular-nums text-lg font-semibold text-accent">
                    {p.value}
                  </p>
                  <p className="text-xs text-text-faint mt-0.5">v{p.version}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <h2 className="font-display text-sm font-semibold text-text mb-2">Environment</h2>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-1 rounded bg-surface-raised text-text-muted font-mono">
            SIMULATION
          </span>
          <p className="text-xs text-text-faint">
            All actions run in simulated mode. Real Razorpay test-mode integration is a
            separate, later build phase.
          </p>
        </div>
      </Card>
    </div>
  );
}