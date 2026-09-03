"use client";

import { useState } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { useQuery } from "@tanstack/react-query";
import { fetchMerchants } from "@/lib/api";
import { Menu, X } from "lucide-react";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const { data: merchants } = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
  });

  const merchant = merchants?.[0];

  return (
    <div className="flex min-h-screen bg-ink">
      {/* Mobile overlay — closes the drawer when tapped */}
      {mobileNavOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      {/* Sidebar: fixed drawer on mobile, static column on desktop */}
      <div
        className={`fixed inset-y-0 left-0 z-40 transition-transform duration-200 ease-out lg:static lg:translate-x-0 ${
          mobileNavOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <Sidebar onNavigate={() => setMobileNavOpen(false)} />
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <TopBar
          merchantName={merchant?.name}
          merchantId={merchant?.id}
          onMenuClick={() => setMobileNavOpen(true)}
        />
        <main className="flex-1 p-4 sm:p-6 overflow-x-hidden">{children}</main>
      </div>
    </div>
  );
}