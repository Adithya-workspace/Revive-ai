"use client";

import { useMutation } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Play, CheckCircle2, Loader2 } from "lucide-react";

interface DemoStepProps {
  stepNumber: number;
  title: string;
  description: string;
  buttonLabel: string;
  onRun: () => Promise<unknown>;
  formatResult?: (result: any) => string;
}

export function DemoStep({
  stepNumber,
  title,
  description,
  buttonLabel,
  onRun,
  formatResult,
}: DemoStepProps) {
  const mutation = useMutation({ mutationFn: onRun });

  return (
    <Card className="animate-fade-in-up">
      <div className="flex items-start gap-4">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-dim text-accent text-sm font-mono font-semibold">
          {stepNumber}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-display text-sm font-semibold text-text">{title}</h3>
          <p className="text-sm text-text-muted mt-1">{description}</p>

          <div className="mt-3 flex items-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
            >
              {mutation.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Play size={14} />
              )}
              {buttonLabel}
            </Button>
            {mutation.isSuccess && (
              <span className="inline-flex items-center gap-1 text-xs text-recovered">
                <CheckCircle2 size={13} /> Done
              </span>
            )}
            {mutation.isError && (
              <span className="text-xs text-critical">Failed — check console</span>
            )}
          </div>

          {mutation.isSuccess && (
            <pre className="mt-3 rounded-lg bg-surface-raised border border-border p-3 text-xs text-text-muted font-mono overflow-x-auto whitespace-pre-wrap">
              {formatResult ? formatResult(mutation.data) : JSON.stringify(mutation.data, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </Card>
  );
}