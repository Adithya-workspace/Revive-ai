"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchMerchants, fetchAnalytics } from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/format";
import { Card } from "@/components/ui/Card";
import { PulseLoader } from "@/components/PulseLoader";
import { ErrorState } from "@/components/ui/ErrorState";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const STATUS_COLORS: Record<string, string> = {
  APPROVED: "#3fb68a",
  NEEDS_HUMAN: "#e8a33d",
  REJECTED: "#e2574c",
};

export default function AnalyticsPage() {
  const { data: merchants } = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
  });
  const merchantId = merchants?.[0]?.id;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["analytics-page", merchantId],
    queryFn: () => fetchAnalytics(merchantId!),
    enabled: !!merchantId,
  });

  if (isLoading) {
    return <PulseLoader label="Loading analytics..." />;
  }

  if (isError || !data) {
    return <ErrorState message="Couldn't load analytics." />;
  }

  const scenarioChartData = data.by_scenario.map((s) => ({
    name: s.scenario.replace(/_/g, " "),
    "At Risk": s.total_at_risk,
    "Recovered": s.recovered,
  }));

  const policyChartData = Object.entries(data.policy_decisions).map(([key, value]) => ({
    name: key.replace(/_/g, " "),
    value,
    color: STATUS_COLORS[key] || "#6c8cff",
  }));

  const actionChartData = Object.entries(data.action_breakdown)
    .map(([key, value]) => ({ name: key.replace(/_/g, " "), count: value }))
    .sort((a, b) => b.count - a.count);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text">Analytics</h1>
        <p className="text-sm text-text-muted mt-1">
          Recovery performance across every scenario, policy decision, and action type.
        </p>
      </div>

      <Card>
        <h2 className="font-display text-sm font-semibold text-text mb-4">
          Revenue at Risk vs Recovered, by Scenario
        </h2>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={scenarioChartData} margin={{ left: -10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#232b33" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: "#8a96a3", fontSize: 11 }}
              axisLine={{ stroke: "#232b33" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#8a96a3", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`}
              width={50}
            />
            <Tooltip
              contentStyle={{
                background: "#171d24",
                border: "1px solid #232b33",
                borderRadius: 8,
                fontSize: 13,
              }}
              formatter={(value) => formatCurrency(Number(value))}
            />
            <Bar dataKey="At Risk" fill="#e8a33d" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Recovered" fill="#3fb68a" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card>
          <h2 className="font-display text-sm font-semibold text-text mb-4">
            Policy Decisions
          </h2>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={policyChartData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={2}
              >
                {policyChartData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "#171d24",
                  border: "1px solid #232b33",
                  borderRadius: 8,
                  fontSize: 13,
                }}
              />
              <Legend
                verticalAlign="bottom"
                iconType="circle"
                wrapperStyle={{ fontSize: 12, color: "#8a96a3" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <h2 className="font-display text-sm font-semibold text-text mb-4">
            Actions by Type
          </h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={actionChartData} layout="vertical" margin={{ left: 10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#232b33" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fill: "#8a96a3", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fill: "#8a96a3", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                width={110}
              />
              <Tooltip
                contentStyle={{
                  background: "#171d24",
                  border: "1px solid #232b33",
                  borderRadius: 8,
                  fontSize: 13,
                }}
              />
              <Bar dataKey="count" fill="#6c8cff" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card>
        <h2 className="font-display text-sm font-semibold text-text mb-4">
          Verification Outcomes
        </h2>
        <div className="flex flex-wrap gap-6 sm:gap-8">
          {Object.entries(data.verification_breakdown).map(([outcome, count]) => (
            <div key={outcome}>
              <p className="font-mono tabular-nums text-2xl font-semibold text-text">
                {count}
              </p>
              <p className="text-xs text-text-muted capitalize mt-1">
                {outcome.replace(/_/g, " ")}
              </p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}