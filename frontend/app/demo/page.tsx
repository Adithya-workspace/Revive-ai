"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  fetchMerchants,
  createDemoCase,
  runDetectionScan,
  runScoring,
  runDiagnosis,
  runStrategy,
  runPolicyEngine,
  runActionExecutor,
  runVerification,
  simulateApiFailure,
  runLiveEvaluation,
} from "@/lib/api";
import { DemoStep } from "@/components/DemoStep";
import { Card } from "@/components/ui/Card";
import { formatCurrency, formatPercent } from "@/lib/format";
import { ArrowRight, ExternalLink } from "lucide-react";

export default function DemoModePage() {
  const { data: merchants } = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
  });
  const merchantId = merchants?.[0]?.id;

  if (!merchantId) return null;

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="font-display text-2xl font-semibold text-text">Demo Mode</h1>
        <p className="text-sm text-text-muted mt-1">
          A guided walkthrough of the full REVIVE pipeline — DETECT → SCORE → DIAGNOSE →
          STRATEGIZE → AUTHORIZE → ACT → VERIFY — run live, on a fresh case, so every step
          shows real work happening.
        </p>
      </div>

      <Card className="bg-accent-dim border-accent/30">
        <p className="text-sm text-text">
          <strong>How to use this:</strong> click each step below in order. Step 1 creates a
          brand-new, unprocessed case (clearly demo-generated, separate from the main
          10,600-event synthetic dataset) so every subsequent step has genuine live work to
          do — the full dataset has already been fully processed, so running these against
          it directly would show &quot;0 new&quot; every time.
        </p>
      </Card>

      <DemoStep
        stepNumber={1}
        title="Create a fresh demo case"
        description="Seeds one new, unprocessed revenue event (failed payment, abandoned checkout, or overdue invoice) for a real customer."
        buttonLabel="Create Demo Case"
        onRun={() => createDemoCase(merchantId)}
        formatResult={(r) =>
          `Created a ${r.scenario.replace(/_/g, " ")} of ${formatCurrency(r.amount)} for ${r.customer_name}.`
        }
      />

      <DemoStep
        stepNumber={2}
        title="Run Revenue Scan (Detection)"
        description="Deterministic rules scan for at-risk revenue — no LLM involved. This should now detect the case you just created."
        buttonLabel="Run Revenue Scan"
        onRun={() => runDetectionScan(merchantId)}
        formatResult={(r) =>
          `Detected ${r.new_cases_created.total} new case(s). Total amount at risk detected: ${formatCurrency(r.total_amount_at_risk_detected)}.`
        }
      />

      <DemoStep
        stepNumber={3}
        title="Calculate Recovery Score"
        description="A transparent, rules-based formula estimates recovery probability — explicitly labeled as rules, never falsely called ML."
        buttonLabel="Run Scoring"
        onRun={() => runScoring(merchantId)}
        formatResult={(r) =>
          `Scored ${r.cases_scored} case(s). Average recovery probability: ${formatPercent(r.average_recovery_probability)}.`
        }
      />

      <DemoStep
        stepNumber={4}
        title="Diagnose Root Cause"
        description="Deterministic rules resolve clear-cut cases instantly; genuinely ambiguous cases (like checkout abandonment) get LLM reasoning via Groq, capped here to keep the demo fast."
        buttonLabel="Run Diagnosis"
        onRun={() => runDiagnosis(merchantId, 3)}
        formatResult={(r) =>
          `Diagnosed ${r.cases_diagnosed} case(s) — ${r.diagnosed_by_rules} by rules, ${r.diagnosed_by_llm} by LLM.`
        }
      />

      <DemoStep
        stepNumber={5}
        title="Select Recovery Strategy"
        description="Applies override rules on top of the diagnosis (low confidence → escalate, low probability → stop, high value → escalate) — no LLM calls in this stage."
        buttonLabel="Run Strategy"
        onRun={() => runStrategy(merchantId)}
        formatResult={(r) =>
          `Strategized ${r.cases_strategized} case(s). Total expected recoverable value: ${formatCurrency(r.total_expected_recoverable_value)}.`
        }
      />

      <DemoStep
        stepNumber={6}
        title="Policy Engine: Authorize or Reject"
        description="THE safety boundary. Pure deterministic rules — retry caps, amount ceilings, confidence floors — decide APPROVED, NEEDS_HUMAN, or REJECTED. Zero LLM involvement."
        buttonLabel="Run Policy Engine"
        onRun={() => runPolicyEngine(merchantId)}
        formatResult={(r) => `Evaluated ${r.actions_evaluated} action(s): ${JSON.stringify(r.decision_breakdown)}.`}
      />

      <DemoStep
        stepNumber={7}
        title="Execute Approved Actions"
        description="Only policy-APPROVED actions execute. Every result is honestly labeled SIMULATED — real Razorpay test-mode integration is a separate, later phase."
        buttonLabel="Run Action Executor"
        onRun={() => runActionExecutor(merchantId)}
        formatResult={(r) => `Executed ${r.actions_executed} action(s): ${JSON.stringify(r.status_breakdown)}.`}
      />

      <DemoStep
        stepNumber={8}
        title="Verify the Real Outcome"
        description="A case is marked recovered ONLY here, after checking the real source record or a probability-grounded simulated response — never assumed earlier in the pipeline."
        buttonLabel="Run Verification"
        onRun={() => runVerification(merchantId)}
        formatResult={(r) => `Verified ${r.results_verified} result(s): ${JSON.stringify(r.outcome_breakdown)}.`}
      />

      <DemoStep
        stepNumber={9}
        title="Simulate a Graceful Failure"
        description="Deliberately fails an action mid-execution to prove: no duplicate action, the case is never falsely marked recovered, and the failure is logged distinctly from a customer decline."
        buttonLabel="Simulate API Failure"
        onRun={() => simulateApiFailure(merchantId)}
        formatResult={(r) => `${r.message} Case status after failure: ${r.case_status_after_failure}.`}
      />

      <Card>
        <div className="flex items-start gap-4">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-dim text-accent text-sm font-mono font-semibold">
            10
          </div>
          <div className="flex-1">
            <h3 className="font-display text-sm font-semibold text-text">
              Explore the Audit Trail
            </h3>
            <p className="text-sm text-text-muted mt-1">
              Every event above was logged — including the graceful failure, distinctly
              labeled as an infrastructure issue, not a customer decline.
            </p>
            <Link
              href="/audit"
              className="mt-3 inline-flex items-center gap-1.5 text-sm text-accent hover:underline"
            >
              Open Audit Trail <ExternalLink size={13} />
            </Link>
          </div>
        </div>
      </Card>

      <DemoStep
        stepNumber={11}
        title="Run Full Evaluation"
        description="Compares REVIVE's real measured results against a naive 'act on everything' baseline — the same logic as the CLI evaluation engine, triggered live."
        buttonLabel="Run Full Evaluation"
        onRun={() => runLiveEvaluation(merchantId)}
        formatResult={(r) =>
          `REVIVE recovered ${formatCurrency(r.revive_metrics.overview.recovered_revenue)} ` +
          `(${formatPercent(r.comparison.revive_recovery_rate_among_attempted)} per-attempt rate) vs baseline ` +
          `${formatCurrency(r.baseline_metrics.total_recovered)} (${formatPercent(r.baseline_metrics.recovery_rate)}). ` +
          `Unnecessary interventions avoided: ${r.comparison.unnecessary_interventions_avoided_by_revive}.`
        }
      />

      <Card className="bg-recovered-dim border-recovered/30">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-display text-sm font-semibold text-text">
              Walkthrough complete
            </h3>
            <p className="text-sm text-text-muted mt-1">
              Head to the Dashboard to see the full picture, or open any case from Revenue
              at Risk to see its complete story end to end.
            </p>
          </div>
          <Link href="/">
            <div className="flex items-center gap-1.5 text-sm text-recovered hover:underline shrink-0">
              Go to Dashboard <ArrowRight size={14} />
            </div>
          </Link>
        </div>
      </Card>
    </div>
  );
}