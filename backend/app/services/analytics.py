"""
REVIVE AI — Analytics (Phase 13)

Pure aggregation over data already produced by earlier phases. No new
pipeline logic, no LLM calls — every number here is a real query result,
directly traceable to the underlying cases/diagnoses/actions/results.
"""

import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import RevenueRiskCase, RecoveryAction, ActionResult


def get_overview_metrics(db: Session, merchant_id: uuid.UUID) -> dict:
    total_revenue_at_risk = (
        db.query(func.coalesce(func.sum(RevenueRiskCase.amount_at_risk), 0))
        .filter(RevenueRiskCase.merchant_id == merchant_id)
        .scalar()
    )

    potentially_recoverable = (
        db.query(func.coalesce(func.sum(RecoveryAction.expected_value), 0))
        .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
        .filter(RevenueRiskCase.merchant_id == merchant_id)
        .scalar()
    )

    recovered_revenue = (
        db.query(func.coalesce(func.sum(RevenueRiskCase.amount_at_risk), 0))
        .filter(
            RevenueRiskCase.merchant_id == merchant_id,
            RevenueRiskCase.status == "recovered",
        )
        .scalar()
    )

    recovered_count = (
        db.query(func.count(RevenueRiskCase.id))
        .filter(
            RevenueRiskCase.merchant_id == merchant_id,
            RevenueRiskCase.status == "recovered",
        )
        .scalar()
    )

    total_cases = (
        db.query(func.count(RevenueRiskCase.id))
        .filter(RevenueRiskCase.merchant_id == merchant_id)
        .scalar()
    )

    open_cases = (
        db.query(func.count(RevenueRiskCase.id))
        .filter(
            RevenueRiskCase.merchant_id == merchant_id,
            RevenueRiskCase.status == "open",
        )
        .scalar()
    )

    recovery_rate = (
        float(recovered_revenue) / float(potentially_recoverable)
        if potentially_recoverable and float(potentially_recoverable) > 0
        else 0.0
    )

    return {
        "total_revenue_at_risk": round(float(total_revenue_at_risk), 2),
        "potentially_recoverable_revenue": round(float(potentially_recoverable), 2),
        "recovered_revenue": round(float(recovered_revenue), 2),
        "recovery_rate": round(recovery_rate, 4),
        "total_cases": total_cases,
        "recovered_cases": recovered_count,
        "open_cases": open_cases,
    }


def get_scenario_breakdown(db: Session, merchant_id: uuid.UUID) -> list[dict]:
    """Same core metrics as overview, grouped by scenario type."""
    scenarios = ["failed_payment", "checkout_abandonment", "overdue_receivable"]
    results = []

    for scenario in scenarios:
        total_at_risk = (
            db.query(func.coalesce(func.sum(RevenueRiskCase.amount_at_risk), 0))
            .filter(
                RevenueRiskCase.merchant_id == merchant_id,
                RevenueRiskCase.scenario == scenario,
            )
            .scalar()
        )

        recovered = (
            db.query(func.coalesce(func.sum(RevenueRiskCase.amount_at_risk), 0))
            .filter(
                RevenueRiskCase.merchant_id == merchant_id,
                RevenueRiskCase.scenario == scenario,
                RevenueRiskCase.status == "recovered",
            )
            .scalar()
        )

        case_count = (
            db.query(func.count(RevenueRiskCase.id))
            .filter(
                RevenueRiskCase.merchant_id == merchant_id,
                RevenueRiskCase.scenario == scenario,
            )
            .scalar()
        )

        recovered_count = (
            db.query(func.count(RevenueRiskCase.id))
            .filter(
                RevenueRiskCase.merchant_id == merchant_id,
                RevenueRiskCase.scenario == scenario,
                RevenueRiskCase.status == "recovered",
            )
            .scalar()
        )

        recovery_rate = (
            float(recovered) / float(total_at_risk)
            if total_at_risk and float(total_at_risk) > 0
            else 0.0
        )

        results.append({
            "scenario": scenario,
            "total_at_risk": round(float(total_at_risk), 2),
            "recovered": round(float(recovered), 2),
            "recovery_rate": round(recovery_rate, 4),
            "case_count": case_count,
            "recovered_count": recovered_count,
        })

    return results


def get_policy_breakdown(db: Session, merchant_id: uuid.UUID) -> dict:
    rows = (
        db.query(RecoveryAction.policy_decision, func.count(RecoveryAction.id))
        .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
        .filter(RevenueRiskCase.merchant_id == merchant_id)
        .group_by(RecoveryAction.policy_decision)
        .all()
    )
    return {decision or "not_yet_evaluated": count for decision, count in rows}


def get_action_breakdown(db: Session, merchant_id: uuid.UUID) -> dict:
    rows = (
        db.query(RecoveryAction.action, func.count(RecoveryAction.id))
        .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
        .filter(RevenueRiskCase.merchant_id == merchant_id)
        .group_by(RecoveryAction.action)
        .all()
    )
    return {action: count for action, count in rows}


def get_verification_breakdown(db: Session, merchant_id: uuid.UUID) -> dict:
    rows = (
        db.query(ActionResult.verified_outcome, func.count(ActionResult.id))
        .join(RecoveryAction, RecoveryAction.id == ActionResult.recovery_action_id)
        .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
        .filter(
            RevenueRiskCase.merchant_id == merchant_id,
            ActionResult.verified == True,  # noqa: E712
        )
        .group_by(ActionResult.verified_outcome)
        .all()
    )
    return {outcome: count for outcome, count in rows}


def get_full_analytics(db: Session, merchant_id: uuid.UUID) -> dict:
    return {
        "overview": get_overview_metrics(db, merchant_id),
        "by_scenario": get_scenario_breakdown(db, merchant_id),
        "policy_decisions": get_policy_breakdown(db, merchant_id),
        "action_breakdown": get_action_breakdown(db, merchant_id),
        "verification_breakdown": get_verification_breakdown(db, merchant_id),
    }