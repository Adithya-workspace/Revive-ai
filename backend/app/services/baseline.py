"""
REVIVE AI — Baseline Comparison (Phase 17, Section 19)

Simulates a naive baseline strategy: intervene on EVERY case REVIVE
actually processed with one generic action, no diagnosis, no policy
gating, no retry caps. Success is drawn against the SAME real
recovery_probability score each case already has (fair — not an
invented number), but the baseline gets no benefit from diagnosis-aware
action selection or policy discrimination.

IMPORTANT: this is restricted to cases that have a RecoveryAction —
i.e., cases REVIVE's own strategy stage actually reached. Cases still
sitting in an undiagnosed backlog are excluded from BOTH sides of the
comparison, since including them would let the baseline take credit
for cases REVIVE was never given the chance to act on. That backlog
count is reported separately, never hidden.

Uses a fixed random seed so results are reproducible across runs,
matching Section 47.
"""

import random
import uuid
from sqlalchemy.orm import Session

from app.models import RevenueRiskCase, RecoveryAction

BASELINE_SEED = 42  # same DATA_SEED as the synthetic generator, for consistency


def compute_baseline_metrics(db: Session, merchant_id: uuid.UUID) -> dict:
    rng = random.Random(BASELINE_SEED)

    # Only cases REVIVE's strategy stage actually reached — a fair,
    # same-universe comparison. Cases without a RecoveryAction yet
    # (the diagnosis backlog) are excluded from both sides.
    cases = (
        db.query(RevenueRiskCase)
        .join(RecoveryAction, RecoveryAction.case_id == RevenueRiskCase.id)
        .filter(
            RevenueRiskCase.merchant_id == merchant_id,
            RevenueRiskCase.recovery_probability.isnot(None),
        )
        .order_by(RevenueRiskCase.id)
        .all()
    )

    total_backlog_excluded = (
        db.query(RevenueRiskCase)
        .filter(
            RevenueRiskCase.merchant_id == merchant_id,
            RevenueRiskCase.status == "open",
        )
        .outerjoin(RecoveryAction, RecoveryAction.case_id == RevenueRiskCase.id)
        .filter(RecoveryAction.id.is_(None))
        .count()
    )

    total_cases_considered = len(cases)
    total_interventions = total_cases_considered

    total_amount_at_risk = 0.0
    total_recovered = 0.0
    recovered_count = 0
    by_scenario: dict = {}

    for case in cases:
        amount = float(case.amount_at_risk)
        probability = float(case.recovery_probability)
        total_amount_at_risk += amount

        succeeded = rng.random() < probability

        scenario_bucket = by_scenario.setdefault(
            case.scenario, {"cases": 0, "recovered": 0, "amount_at_risk": 0.0, "recovered_amount": 0.0}
        )
        scenario_bucket["cases"] += 1
        scenario_bucket["amount_at_risk"] += amount

        if succeeded:
            total_recovered += amount
            recovered_count += 1
            scenario_bucket["recovered"] += 1
            scenario_bucket["recovered_amount"] += amount

    recovery_rate = (total_recovered / total_amount_at_risk) if total_amount_at_risk > 0 else 0.0

    return {
        "strategy": "baseline_naive_always_intervene",
        "description": (
            "Naive baseline: one generic action attempted on every case REVIVE's "
            "strategy stage actually reached (same universe as REVIVE, for a fair "
            "comparison), no diagnosis-driven action selection, no policy gating. "
            "Success drawn against each case's real recovery_probability score."
        ),
        "seed": BASELINE_SEED,
        "total_cases_considered": total_cases_considered,
        "total_interventions": total_interventions,
        "total_backlog_excluded_from_both_sides": total_backlog_excluded,
        "total_amount_at_risk": round(total_amount_at_risk, 2),
        "total_recovered": round(total_recovered, 2),
        "recovered_count": recovered_count,
        "recovery_rate": round(recovery_rate, 4),
        "by_scenario": {
            scenario: {
                "cases": v["cases"],
                "recovered": v["recovered"],
                "amount_at_risk": round(v["amount_at_risk"], 2),
                "recovered_amount": round(v["recovered_amount"], 2),
            }
            for scenario, v in by_scenario.items()
        },
    }