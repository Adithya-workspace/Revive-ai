"use client";

import { Button } from "@/components/ui/Button";
import { Play } from "lucide-react";

export function TopBar({ merchantName }: { merchantName?: string }) {
  return (
    <header className="h-16 border-b border-border bg-ink/80 backdrop-blur-sm sticky top-0 z-10 flex items-center justify-between px-6">
      <div>
        <p className="text-sm font-medium text-text">
          {merchantName || "Loading merchant..."}
        </p>
        <p className="text-xs text-text-faint">Simulation environment</p>
      </div>

      <Button variant="primary" size="sm">
        <Play size={14} />
        Run Full Scan
      </Button>
    </header>
  );
}