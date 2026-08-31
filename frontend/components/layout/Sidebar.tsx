"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  AlertTriangle,
  FolderKanban,
  Users,
  Zap,
  ShieldAlert,
  BarChart3,
  ScrollText,
  Settings,
  PlayCircle,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/demo", label: "Demo Mode", icon: PlayCircle },
  { href: "/revenue-at-risk", label: "Revenue at Risk", icon: AlertTriangle },
  { href: "/cases", label: "Recovery Cases", icon: FolderKanban },
  { href: "/customers", label: "Customers", icon: Users },
  { href: "/actions", label: "Actions", icon: Zap },
  { href: "/escalations", label: "Escalations", icon: ShieldAlert },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/audit", label: "Audit Trail", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 shrink-0 border-r border-border bg-surface flex flex-col h-screen sticky top-0">
      <div className="px-5 py-6 border-b border-border">
        <div className="flex items-center gap-2">
          <svg width="22" height="22" viewBox="0 0 22 22" className="text-accent">
            <path
              d="M1 11 H7 L9 5 L12 17 L14 11 H21"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
          </svg>
          <span className="font-display font-semibold text-[15px] tracking-tight text-text">
            REVIVE AI
          </span>
        </div>
        <p className="text-[11px] text-text-faint mt-1 pl-[30px]">Revenue Recovery</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150 ease-out ${
                isActive
                  ? "bg-accent-dim text-accent"
                  : "text-text-muted hover:text-text hover:bg-surface-raised"
              }`}
            >
              <Icon
                size={17}
                className={`transition-transform duration-150 ease-out ${
                  isActive ? "" : "group-hover:translate-x-0.5"
                }`}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-5 py-4 border-t border-border">
        <p className="text-[11px] text-text-faint">
          TEST MODE
        </p>
      </div>
    </aside>
  );
}