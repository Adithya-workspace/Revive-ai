"""
REVIVE AI — Remaining list endpoints for frontend screens

Customers, Actions, Escalations, Policies, Audit Events.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import (
    Customer,
    RevenueRiskCase,
    RecoveryAction,
    ActionResult,
    Policy,
    AuditEvent,
    Transaction,
)

router = APIRouter(tags=["lists"])


# --- Customers -------------------------------------------------------------

@router.get("/customers/{merchant_id}")
def list_customers(
    merchant_id: str,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    db: Session = Depends(get_db),
):
    customers = (
        db.query(Customer)
        .filter(Customer.merchant_id == merchant_id)
        .order_by(Customer.name.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    total_count = db.query(Customer).filter(Customer.merchant_id == merchant_id).count()

    customer_ids = [c.id for c in customers]

    cases = (
        db.query(RevenueRiskCase)
        .filter(RevenueRiskCase.customer_id.in_(customer_ids))
        .all()
    )
    cases_by_customer: dict = {}
    for case in cases:
        cases_by_customer.setdefault(case.customer_id, []).append(case)

    results = []
    for customer in customers:
        customer_cases = cases_by_customer.get(customer.id, [])
        total_at_risk = sum(float(c.amount_at_risk) for c in customer_cases)
        recovered = sum(float(c.amount_at_risk) for c in customer_cases if c.status == "recovered")

        results.append({
            "id": str(customer.id),
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "case_count": len(customer_cases),
            "total_at_risk": round(total_at_risk, 2),
            "recovered": round(recovered, 2),
        })

    return {
        "total_count": total_count,
        "returned_count": len(results),
        "offset": offset,
        "limit": limit,
        "customers": results,
    }


@router.get("/customers/{merchant_id}/{customer_id}")
def get_customer_detail(merchant_id: str, customer_id: str, db: Session = Depends(get_db)):
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.merchant_id == merchant_id)
        .first()
    )
    if not customer:
        return {"error": "Customer not found"}

    cases = db.query(RevenueRiskCase).filter(RevenueRiskCase.customer_id == customer.id).all()
    transactions = db.query(Transaction).filter(Transaction.customer_id == customer.id).all()

    success_count = sum(1 for t in transactions if t.status == "success")

    return {
        "customer": {
            "id": str(customer.id),
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
        },
        "stats": {
            "total_transactions": len(transactions),
            "successful_transactions": success_count,
            "success_rate": round(success_count / len(transactions), 3) if transactions else None,
            "total_cases": len(cases),
            "recovered_cases": sum(1 for c in cases if c.status == "recovered"),
        },
        "cases": [
            {
                "id": str(c.id),
                "scenario": c.scenario,
                "amount_at_risk": float(c.amount_at_risk),
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in cases
        ],
    }


# --- Actions -----------------------------------------------------------

@router.get("/actions/{merchant_id}")
def list_actions(
    merchant_id: str,
    action_type: Optional[str] = Query(default=None),
    policy_decision: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    db: Session = Depends(get_db),
):
    query = (
        db.query(RecoveryAction)
        .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
        .filter(RevenueRiskCase.merchant_id == merchant_id)
    )

    if action_type:
        query = query.filter(RecoveryAction.action == action_type)
    if policy_decision:
        query = query.filter(RecoveryAction.policy_decision == policy_decision)

    total_count = query.count()
    actions = query.order_by(RecoveryAction.created_at.desc()).offset(offset).limit(limit).all()

    action_ids = [a.id for a in actions]
    case_ids = [a.case_id for a in actions]

    results_by_action = {
        r.recovery_action_id: r
        for r in db.query(ActionResult).filter(ActionResult.recovery_action_id.in_(action_ids)).all()
    }
    cases_by_id = {
        c.id: c for c in db.query(RevenueRiskCase).filter(RevenueRiskCase.id.in_(case_ids)).all()
    }
    customer_ids = [c.customer_id for c in cases_by_id.values() if c.customer_id]
    customers_by_id = {
        c.id: c for c in db.query(Customer).filter(Customer.id.in_(customer_ids)).all()
    } if customer_ids else {}

    results = []
    for action in actions:
        case = cases_by_id.get(action.case_id)
        customer = customers_by_id.get(case.customer_id) if case and case.customer_id else None
        result = results_by_action.get(action.id)

        results.append({
            "id": str(action.id),
            "case_id": str(action.case_id),
            "customer_name": customer.name if customer else "Unknown",
            "action": action.action,
            "expected_value": action.expected_value,
            "confidence": action.confidence,
            "policy_decision": action.policy_decision,
            "execution_status": result.status if result else "not_executed",
            "execution_mode": result.mode if result else None,
            "created_at": action.created_at.isoformat() if action.created_at else None,
        })

    return {
        "total_count": total_count,
        "returned_count": len(results),
        "offset": offset,
        "limit": limit,
        "actions": results,
    }


# --- Escalations -------------------------------------------------------

@router.get("/escalations/{merchant_id}")
def list_escalations(
    merchant_id: str,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    db: Session = Depends(get_db),
):
    """Cases whose action is currently sitting at NEEDS_HUMAN — the human review queue."""
    query = (
        db.query(RecoveryAction)
        .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
        .filter(
            RevenueRiskCase.merchant_id == merchant_id,
            RecoveryAction.policy_decision == "NEEDS_HUMAN",
        )
    )

    total_count = query.count()
    actions = query.order_by(RecoveryAction.created_at.desc()).offset(offset).limit(limit).all()

    case_ids = [a.case_id for a in actions]
    cases_by_id = {
        c.id: c for c in db.query(RevenueRiskCase).filter(RevenueRiskCase.id.in_(case_ids)).all()
    }
    customer_ids = [c.customer_id for c in cases_by_id.values() if c.customer_id]
    customers_by_id = {
        c.id: c for c in db.query(Customer).filter(Customer.id.in_(customer_ids)).all()
    } if customer_ids else {}

    results = []
    for action in actions:
        case = cases_by_id.get(action.case_id)
        customer = customers_by_id.get(case.customer_id) if case and case.customer_id else None

        results.append({
            "case_id": str(action.case_id),
            "customer_name": customer.name if customer else "Unknown",
            "scenario": case.scenario if case else None,
            "amount_at_risk": float(case.amount_at_risk) if case else None,
            "recommended_action": action.action,
            "reason": action.reason,
            "policy_reason": action.policy_reason,
            "confidence": action.confidence,
            "created_at": action.created_at.isoformat() if action.created_at else None,
        })

    return {
        "total_count": total_count,
        "returned_count": len(results),
        "offset": offset,
        "limit": limit,
        "escalations": results,
    }


# --- Policies ------------------------------------------------------------

@router.get("/policies")
def list_policies(db: Session = Depends(get_db)):
    policies = db.query(Policy).order_by(Policy.key.asc()).all()
    return [
        {
            "key": p.key,
            "value": p.value,
            "description": p.description,
            "version": p.version,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in policies
    ]


# --- Audit Events --------------------------------------------------------

@router.get("/audit-events/{merchant_id}")
def list_audit_events(
    merchant_id: str,
    event_type: Optional[str] = Query(default=None),
    case_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    db: Session = Depends(get_db),
):
    query = (
        db.query(AuditEvent)
        .join(RevenueRiskCase, RevenueRiskCase.id == AuditEvent.case_id)
        .filter(RevenueRiskCase.merchant_id == merchant_id)
    )

    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)
    if case_id:
        query = query.filter(AuditEvent.case_id == case_id)

    total_count = query.count()
    events = query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total_count": total_count,
        "returned_count": len(events),
        "offset": offset,
        "limit": limit,
        "events": [
            {
                "id": str(e.id),
                "case_id": str(e.case_id),
                "event_type": e.event_type,
                "actor": e.actor,
                "result": e.result,
                "metadata": e.event_metadata,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }