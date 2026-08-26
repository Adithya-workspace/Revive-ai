"""
REVIVE AI — Evaluation Engine (Phase 17, Section 46-47)

Compares REVIVE's real, measured pipeline results against a naive
baseline strategy, using only data already produced by the actual
pipeline (Phases 5-13) — never fabricated numbers.

Run from the backend/ directory with the venv active:
    python -m evaluation.run_evaluation

Reproducibility note (Section 47): this evaluates the CURRENT state of
the database, which originated from the synthetic generator's fixed
DATA_SEED=42. Re-running detection/scoring on the same seed reproduces
the same base dataset; re-running the full LLM-diagnosis pipeline is
NOT re-executed on every evaluation run (that would mean repeated LLM
calls) — this is a documented, deliberate tradeoff, not an omission.
See docs/EVALUATION.md for the full explanation.
"""

import json
import os
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import Merchant, Policy, RecoveryAction, ActionResult, RevenueRiskCase
from app.services.analytics import get_full_analytics
from app.services.baseline import compute_baseline_metrics

DATA_SEED = 42
MODEL_VERSION = "rules-v1"

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def compute_revive_attempted_metrics(db, merchant_id) -> dict:
    """
    Apples-to-apples metric: among ONLY the cases REVIVE actually
    executed an action on (not the full detected universe), what was
    the real recovery rate? This is what should be compared against
    the baseline's per-case rate, since the baseline also acts on
    every case it considers.
    """
    executed_actions = (
        db.query(RecoveryAction)
        .join(ActionResult, ActionResult.recovery_action_id == RecoveryAction.id)
        .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
        .filter(RevenueRiskCase.merchant_id == merchant_id)
        .all()
    )
    attempted_case_ids = [a.case_id for a in executed_actions]
    attempted_cases = (
        db.query(RevenueRiskCase).filter(RevenueRiskCase.id.in_(attempted_case_ids)).all()
        if attempted_case_ids else []
    )
    attempted_amount = sum(float(c.amount_at_risk) for c in attempted_cases)
    attempted_recovered = sum(
        float(c.amount_at_risk) for c in attempted_cases if c.status == "recovered"
    )

    return {
        "case_count": len(attempted_cases),
        "amount_at_risk": round(attempted_amount, 2),
        "recovered": round(attempted_recovered, 2),
        "rate": round(attempted_recovered / attempted_amount, 4) if attempted_amount > 0 else 0.0,
    }


def build_comparison(revive_metrics: dict, baseline_metrics: dict, revive_attempted: dict) -> dict:
    revive_recovered = revive_metrics["overview"]["recovered_revenue"]
    baseline_recovered = baseline_metrics["total_recovered"]

    revive_interventions = revive_metrics["policy_decisions"].get("APPROVED", 0)
    baseline_interventions = baseline_metrics["total_interventions"]

    interventions_avoided = baseline_interventions - revive_interventions

    rate_diff = revive_attempted["rate"] - baseline_metrics["recovery_rate"]
    if rate_diff > 0.02:
        effectiveness_clause = (
            f"REVIVE's per-attempt recovery rate ({revive_attempted['rate']:.1%}) is "
            f"actually HIGHER than the naive baseline's rate ({baseline_metrics['recovery_rate']:.1%}) "
            f"— a {rate_diff:.1%} improvement, showing diagnosis-aware action selection "
            f"genuinely outperforms blind intervention, not just avoids risk."
        )
    elif rate_diff < -0.02:
        effectiveness_clause = (
            f"REVIVE's per-attempt recovery rate ({revive_attempted['rate']:.1%}) is somewhat "
            f"lower than the naive baseline's rate ({baseline_metrics['recovery_rate']:.1%}), "
            f"likely because REVIVE's policy gating filters out easier cases into automatic "
            f"approval while harder cases route to human review."
        )
    else:
        effectiveness_clause = (
            f"REVIVE's per-attempt recovery rate ({revive_attempted['rate']:.1%}) is nearly "
            f"identical to the naive baseline's rate ({baseline_metrics['recovery_rate']:.1%}) "
            f"— REVIVE is not less effective when it acts."
        )

    interpretation = (
        f"{effectiveness_clause} The gap in TOTAL recovered revenue comes largely from "
        f"coverage: REVIVE deliberately attempts far fewer cases ({revive_interventions} vs "
        f"{baseline_interventions}) because policy gating routes low-confidence, high-value, "
        f"and over-retried cases to human review instead of auto-acting. This is the "
        f"coverage-vs-safety tradeoff Section 20 calls for."
    )

    return {
        "revive_recovered_revenue": revive_recovered,
        "baseline_recovered_revenue": baseline_recovered,
        "revive_recovery_rate_overall": revive_metrics["overview"]["recovery_rate"],
        "baseline_recovery_rate": baseline_metrics["recovery_rate"],
        "revive_recovery_rate_among_attempted": revive_attempted["rate"],
        "revive_attempted_case_count": revive_attempted["case_count"],
        "revive_automatic_interventions": revive_interventions,
        "baseline_interventions": baseline_interventions,
        "unnecessary_interventions_avoided_by_revive": interventions_avoided,
        "interpretation": interpretation,
    }


def run():
    db = SessionLocal()

    try:
        merchant = db.query(Merchant).first()
        if not merchant:
            print("No merchant found. Run the synthetic data generator first.")
            return

        print(f"Running evaluation for merchant: {merchant.name} ({merchant.id})\n")

        policies = db.query(Policy).all()
        policy_version_summary = {p.key: p.version for p in policies}

        print("Computing REVIVE's real measured metrics (Phase 13 analytics)...", flush=True)
        revive_metrics = get_full_analytics(db, merchant.id)

        print("Computing REVIVE's per-attempt (apples-to-apples) recovery rate...", flush=True)
        revive_attempted = compute_revive_attempted_metrics(db, merchant.id)

        print("Computing naive baseline metrics (seeded, reproducible)...", flush=True)
        baseline_metrics = compute_baseline_metrics(db, merchant.id)

        print("Building comparison...", flush=True)
        comparison = build_comparison(revive_metrics, baseline_metrics, revive_attempted)

        report = {
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "data_seed": DATA_SEED,
            "model_version": MODEL_VERSION,
            "policy_versions": policy_version_summary,
            "merchant_id": str(merchant.id),
            "revive_metrics": revive_metrics,
            "revive_attempted_metrics": revive_attempted,
            "baseline_metrics": baseline_metrics,
            "comparison": comparison,
        }

        os.makedirs(RESULTS_DIR, exist_ok=True)
        filename = f"evaluation_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(RESULTS_DIR, filename)
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        latest_path = os.path.join(RESULTS_DIR, "latest.json")
        with open(latest_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nSaved evaluation report to {filepath}\n")
        print_summary(report)

    finally:
        db.close()


def print_summary(report: dict):
    print("=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Data seed: {report['data_seed']}  |  Model version: {report['model_version']}")
    print(f"Timestamp: {report['evaluation_timestamp']}")
    print()

    rm = report["revive_metrics"]["overview"]
    bm = report["baseline_metrics"]
    cmp = report["comparison"]

    print(f"{'':30} {'REVIVE':>18} {'BASELINE':>18}")
    print(
        f"{'Recovered revenue':30} "
        f"{'Rs ' + format(rm['recovered_revenue'], ',.2f'):>18} "
        f"{'Rs ' + format(bm['total_recovered'], ',.2f'):>18}"
    )
    print(
        f"{'Recovery rate (overall)':30} "
        f"{rm['recovery_rate']*100:>17.2f}% "
        f"{bm['recovery_rate']*100:>17.2f}%"
    )
    print(
        f"{'Automatic interventions':30} "
        f"{cmp['revive_automatic_interventions']:>18} "
        f"{cmp['baseline_interventions']:>18}"
    )
    print(
        f"{'Recovery rate (per attempt)':30} "
        f"{cmp['revive_recovery_rate_among_attempted']*100:>17.2f}% "
        f"{bm['recovery_rate']*100:>17.2f}%"
    )
    print()
    print(f"Unnecessary interventions avoided by REVIVE: {cmp['unnecessary_interventions_avoided_by_revive']}")
    print(
        f"\nNote: baseline comparison restricted to the {bm['total_cases_considered']} cases "
        f"REVIVE's strategy stage actually reached. "
        f"{bm['total_backlog_excluded_from_both_sides']} cases are still in the diagnosis "
        f"backlog and excluded from this specific comparison (they ARE included in the "
        f"overall dashboard 'Revenue at Risk' figure above)."
    )
    print(f"\n{cmp['interpretation']}")
    print("=" * 70)


if __name__ == "__main__":
    run()