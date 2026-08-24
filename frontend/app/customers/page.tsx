"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchMerchants, fetchCustomers } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { Card } from "@/components/ui/Card";
import { PulseLoader } from "@/components/PulseLoader";

export default function CustomersPage() {
  const { data: merchants } = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
  });
  const merchantId = merchants?.[0]?.id;

  const { data, isLoading } = useQuery({
    queryKey: ["customers", merchantId],
    queryFn: () => fetchCustomers(merchantId!, 100),
    enabled: !!merchantId,
  });

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text">Customers</h1>
        <p className="text-sm text-text-muted mt-1">
          Every customer with revenue-risk history, and how much has been recovered.
        </p>
      </div>

      <Card className="p-0 overflow-hidden">
        {isLoading ? (
          <PulseLoader label="Loading customers..." />
        ) : !data || data.customers.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-sm text-text-muted">No customers found.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs font-medium text-text-faint uppercase tracking-wide">
                  <th className="px-5 py-3">Name</th>
                  <th className="px-5 py-3">Email</th>
                  <th className="px-5 py-3">Phone</th>
                  <th className="px-5 py-3 text-right">Cases</th>
                  <th className="px-5 py-3 text-right">Total at Risk</th>
                  <th className="px-5 py-3 text-right">Recovered</th>
                </tr>
              </thead>
              <tbody>
                {data.customers.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-border last:border-0 transition-colors duration-150 ease-out hover:bg-surface-raised"
                  >
                    <td className="px-5 py-3 text-text">{c.name}</td>
                    <td className="px-5 py-3 text-text-muted text-xs">{c.email}</td>
                    <td className="px-5 py-3 text-text-muted text-xs">{c.phone}</td>
                    <td className="px-5 py-3 text-right font-mono tabular-nums text-text">
                      {c.case_count}
                    </td>
                    <td className="px-5 py-3 text-right font-mono tabular-nums text-at-risk">
                      {formatCurrency(c.total_at_risk)}
                    </td>
                    <td className="px-5 py-3 text-right font-mono tabular-nums text-recovered">
                      {formatCurrency(c.recovered)}
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