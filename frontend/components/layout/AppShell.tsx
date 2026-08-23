"use client";

import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { useQuery } from "@tanstack/react-query";
import { fetchMerchants } from "@/lib/api";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { data: merchants } = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
  });

  const merchant = merchants?.[0];

  return (
    <div className="flex min-h-screen bg-ink">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar merchantName={merchant?.name} />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}