"""
REVIVE AI — Cases API routes (Phase 14 support)

Read endpoints for the frontend: list cases (with filters, for the
Revenue at Risk table) and get one case's full detail (for the case
detail page, Section 26).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import RevenueRiskCase, Diagnosis, RecoveryAction, ActionResult, Customer, AuditEvent

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("/{merchant_id}")
def list_cases(
    merchant_id: str,
    status: Optional[str] = Query(default=None),
    scenario: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    db: Session = Depends(get_db),
):
    query = db.query(RevenueRiskCase).filter(RevenueRiskCase.merchant_id == merchant_id)

    if status:
        query = query.filter(RevenueRiskCase.status == status)
    if scenario:
        query = query.filter(RevenueRiskCase.scenario == scenario)
    if priority:
        query = query.filter(RevenueRiskCase.priority == priority)

    total_count = query.count()
    cases = query.order_by(RevenueRiskCase.created_at.desc()).offset(offset).limit(limit).all()

    case_ids = [c.id for c in cases]
    customer_ids = [c.customer_id for c in cases if c.customer_id]

    customers_by_id = {
        cust.id: cust for cust in db.query(Customer).filter(Customer.id.in_(customer_ids)).all()
    } if customer_ids else {}

    # Latest diagnosis + action per case, for the recommended-action column
    diagnoses_by_case = {
        d.case_id: d for d in db.query(Diagnosis).filter(Diagnosis.case_id.in_(case_ids)).all()
    }
    actions_by_case = {
        a.case_id: a for a in db.query(RecoveryAction).filter(RecoveryAction.case_id.in_(case_ids)).all()
    }

    results = []
    for case in cases:
        customer = customers_by_id.get(case.customer_id)
        diagnosis = diagnoses_by_case.get(case.id)
        action = actions_by_case.get(case.id)

        results.append({
            "id": str(case.id),
            "customer_name": customer.name if customer else "Unknown",
            "scenario": case.scenario,
            "amount_at_risk": float(case.amount_at_risk),
            "recovery_probability": case.recovery_probability,
            "priority": case.priority,
            "status": case.status,
            "recommended_action": action.action if action else None,
            "diagnosis": diagnosis.diagnosis if diagnosis else None,
            "policy_decision": action.policy_decision if action else None,
            "created_at": case.created_at.isoformat() if case.created_at else None,
        })

    return {
        "total_count": total_count,
        "returned_count": len(results),
        "offset": offset,
        "limit": limit,
        "cases": results,
    }


@router.get("/{merchant_id}/{case_id}")
def get_case_detail(merchant_id: str, case_id: str, db: Session = Depends(get_db)):
    case = (
        db.query(RevenueRiskCase)
        .filter(RevenueRiskCase.id == case_id, RevenueRiskCase.merchant_id == merchant_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    customer = db.query(Customer).filter(Customer.id == case.customer_id).first() if case.customer_id else None
    diagnosis = db.query(Diagnosis).filter(Diagnosis.case_id == case.id).order_by(Diagnosis.created_at.desc()).first()
    action = db.query(RecoveryAction).filter(RecoveryAction.case_id == case.id).first()
    action_result = (
        db.query(ActionResult).filter(ActionResult.recovery_action_id == action.id).first()
        if action else None
    )
    audit_events = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case.id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )

    return {
        "case": {
            "id": str(case.id),
            "scenario": case.scenario,
            "amount_at_risk": float(case.amount_at_risk),
            "recovery_probability": case.recovery_probability,
            "priority": case.priority,
            "status": case.status,
            "created_at": case.created_at.isoformat() if case.created_at else None,
        },
        "customer": {
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
        } if customer else None,
        "diagnosis": {
            "diagnosis": diagnosis.diagnosis,
            "confidence": diagnosis.confidence,
            "evidence": diagnosis.evidence,
            "reasoning_summary": diagnosis.reasoning_summary,
            "diagnosis_source": diagnosis.diagnosis_source,
        } if diagnosis else None,
        "strategy": {
            "action": action.action,
            "reason": action.reason,
            "expected_value": action.expected_value,
            "confidence": action.confidence,
        } if action else None,
        "policy": {
            "decision": action.policy_decision,
            "reason": action.policy_reason,
        } if action and action.policy_decision else None,
        "action_result": {
            "mode": action_result.mode,
            "status": action_result.status,
            "result_detail": action_result.result_detail,
            "verified": action_result.verified,
            "verified_outcome": action_result.verified_outcome,
            "verification_detail": action_result.verification_detail,
        } if action_result else None,
        "audit_trail": [
            {
                "event_type": e.event_type,
                "actor": e.actor,
                "result": e.result,
                "metadata": e.event_metadata,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in audit_events
        ],
    }