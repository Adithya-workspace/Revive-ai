"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchMerchants, fetchAnalytics } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { PulseLoader } from "@/components/PulseLoader";
import { formatCurrency } from "@/lib/format";



function KpiCard({
  label,
  value,
  sublabel,
  accent = "text",
}: {
  label: string;
  value: string;
  sublabel?: string;
  accent?: "text" | "recovered" | "at-risk" | "accent";
}) {
  const accentClass = {
    text: "text-text",
    recovered: "text-recovered",
    "at-risk": "text-at-risk",
    accent: "text-accent",
  }[accent];

  return (
    <Card className="animate-fade-in-up">
      <p className="text-xs font-medium text-text-muted uppercase tracking-wide">{label}</p>
      <p className={`font-mono tabular-nums text-2xl font-semibold mt-2 ${accentClass}`}>
        {value}
      </p>
      {sublabel && <p className="text-xs text-text-faint mt-1">{sublabel}</p>}
    </Card>
  );
}

export default function DashboardPage() {
  const { data: merchants } = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
  });

  const merchantId = merchants?.[0]?.id;

  const { data: analytics, isLoading } = useQuery({
    queryKey: ["analytics", merchantId],
    queryFn: () => fetchAnalytics(merchantId!),
    enabled: !!merchantId,
  });

  if (isLoading || !analytics) {
    return <PulseLoader label="Loading dashboard..." />;
  }

  const { overview, by_scenario, policy_decisions } = analytics;

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text">Dashboard</h1>
        <p className="text-sm text-text-muted mt-1">
          Real-time overview of revenue at risk and recovery performance.
        </p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <KpiCard
          label="Revenue at Risk"
          value={formatCurrency(overview.total_revenue_at_risk)}
          sublabel={`${overview.total_cases} cases detected`}
          accent="at-risk"
        />
        <KpiCard
          label="Potentially Recoverable"
          value={formatCurrency(overview.potentially_recoverable_revenue)}
          sublabel="Expected value across strategy"
          accent="accent"
        />
        <KpiCard
          label="Revenue Recovered"
          value={formatCurrency(overview.recovered_revenue)}
          sublabel={`${overview.recovered_cases} cases confirmed`}
          accent="recovered"
        />
        <KpiCard
          label="Recovery Rate"
          value={`${(overview.recovery_rate * 100).toFixed(1)}%`}
          sublabel="Recovered / recoverable"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <h2 className="font-display text-sm font-semibold text-text mb-4">By Scenario</h2>
          <div className="space-y-3">
            {by_scenario.map((s) => (
              <div key={s.scenario} className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-text capitalize">
                    {s.scenario.replace(/_/g, " ")}
                  </p>
                  <p className="text-xs text-text-faint">
                    {s.recovered_count} / {s.case_count} recovered
                  </p>
                </div>
                <p className="font-mono tabular-nums text-sm text-recovered">
                  {(s.recovery_rate * 100).toFixed(1)}%
                </p>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h2 className="font-display text-sm font-semibold text-text mb-4">Policy Decisions</h2>
          <div className="space-y-3">
            {Object.entries(policy_decisions).map(([decision, count]) => (
              <div key={decision} className="flex items-center justify-between">
                <p className="text-sm text-text-muted">{decision.replace(/_/g, " ")}</p>
                <p className="font-mono tabular-nums text-sm text-text">{count}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}