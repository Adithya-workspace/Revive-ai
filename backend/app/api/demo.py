"""
REVIVE AI — Demo Mode support routes (Phase 18, Sections 37-38)

create-case seeds ONE fresh, unprocessed source record so every stage
of the pipeline has real, live work to do during a demo — since the
full synthetic dataset has already been processed end-to-end, running
the real pipeline buttons against it would show "0 new" every time.
This is clearly demo-generated data, tracked in DemoSeededRecord so it
can be cleanly reset without ever touching the real synthetic dataset.
"""

import random
import uuid
from datetime import datetime, timezone, timedelta, date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Merchant,
    Customer,
    Transaction,
    CheckoutSession,
    Invoice,
    DemoSeededRecord,
    RevenueRiskCase,
    Diagnosis,
    RecoveryAction,
    ActionResult,
    AuditEvent,
)

router = APIRouter(prefix="/demo", tags=["demo"])

FAILURE_REASONS = ["insufficient_funds", "card_declined", "network_error", "bank_timeout", "expired_card"]

SCENARIO_TO_SOURCE_TYPE = {
    "failed_payment": "transaction",
    "checkout_abandonment": "checkout_session",
    "overdue_receivable": "invoice",
}


@router.post("/create-case/{merchant_id}")
def create_demo_case(merchant_id: str, db: Session = Depends(get_db)):
    """
    Creates ONE fresh, unprocessed source record (transaction, checkout
    session, or invoice) for an existing customer, so the demo
    walkthrough always has live work for the pipeline buttons to do.
    Tracked in DemoSeededRecord so it can be reset later.
    """
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    customer = db.query(Customer).filter(Customer.merchant_id == merchant_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="No customer found for this merchant")

    scenario = random.choice(["failed_payment", "checkout_abandonment", "overdue_receivable"])
    amount = round(random.uniform(500, 8000), 2)

    if scenario == "failed_payment":
        record = Transaction(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            customer_id=customer.id,
            amount=amount,
            currency="INR",
            status="failed",
            failure_reason=random.choice(FAILURE_REASONS),
            retry_count=0,
        )
    elif scenario == "checkout_abandonment":
        started = datetime.now(timezone.utc) - timedelta(minutes=random.randint(10, 60))
        record = CheckoutSession(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            customer_id=customer.id,
            amount=amount,
            currency="INR",
            status="abandoned",
            started_at=started,
            last_activity_at=started + timedelta(minutes=random.randint(1, 20)),
        )
    else:
        record = Invoice(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            customer_id=customer.id,
            amount=amount,
            currency="INR",
            due_date=date.today() - timedelta(days=random.randint(5, 60)),
            status="overdue",
        )

    db.add(record)
    db.flush()

    tracker = DemoSeededRecord(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        source_type=SCENARIO_TO_SOURCE_TYPE[scenario],
        source_id=record.id,
    )
    db.add(tracker)
    db.commit()

    return {
        "success": True,
        "scenario": scenario,
        "amount": amount,
        "customer_name": customer.name,
        "message": (
            f"Created one fresh, unprocessed {scenario.replace('_', ' ')} record "
            f"(demo-generated, not part of the main synthetic dataset). "
            f"Click 'Run Revenue Scan' next to detect it."
        ),
    }


@router.post("/reset/{merchant_id}")
def reset_demo_data(merchant_id: str, db: Session = Depends(get_db)):
    """
    Removes every record Demo Mode has created — and only those —
    so practicing the walkthrough never permanently drifts your
    official evaluation numbers away from the real synthetic dataset.
    """
    tracked_records = (
        db.query(DemoSeededRecord)
        .filter(DemoSeededRecord.merchant_id == merchant_id)
        .all()
    )

    removed_cases = 0
    removed_source_records = 0

    for record in tracked_records:
        case = (
            db.query(RevenueRiskCase)
            .filter(RevenueRiskCase.source_id == record.source_id)
            .first()
        )

        if case:
            actions = db.query(RecoveryAction).filter(RecoveryAction.case_id == case.id).all()
            for action in actions:
                db.query(ActionResult).filter(ActionResult.recovery_action_id == action.id).delete()
            db.query(RecoveryAction).filter(RecoveryAction.case_id == case.id).delete()
            db.query(Diagnosis).filter(Diagnosis.case_id == case.id).delete()
            db.query(AuditEvent).filter(AuditEvent.case_id == case.id).delete()
            db.delete(case)
            removed_cases += 1

        if record.source_type == "transaction":
            db.query(Transaction).filter(Transaction.id == record.source_id).delete()
        elif record.source_type == "checkout_session":
            db.query(CheckoutSession).filter(CheckoutSession.id == record.source_id).delete()
        elif record.source_type == "invoice":
            db.query(Invoice).filter(Invoice.id == record.source_id).delete()
        removed_source_records += 1

        db.delete(record)

    db.commit()

    return {
        "success": True,
        "removed_cases": removed_cases,
        "removed_source_records": removed_source_records,
        "message": (
            f"Removed {removed_source_records} demo-generated record(s) and "
            f"{removed_cases} associated case(s). Your real synthetic dataset "
            "and its metrics are untouched."
        ),
    }


@router.post("/run-evaluation/{merchant_id}")
def run_evaluation_live(merchant_id: str, db: Session = Depends(get_db)):
    """
    Same evaluation logic as `python -m evaluation.run_evaluation`,
    callable live from the demo page so judges can trigger it without
    touching a terminal.
    """
    from evaluation.run_evaluation import compute_revive_attempted_metrics, build_comparison
    from app.services.analytics import get_full_analytics
    from app.services.baseline import compute_baseline_metrics

    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    revive_metrics = get_full_analytics(db, merchant_id)
    revive_attempted = compute_revive_attempted_metrics(db, merchant_id)
    baseline_metrics = compute_baseline_metrics(db, merchant_id)
    comparison = build_comparison(revive_metrics, baseline_metrics, revive_attempted)

    return {
        "revive_metrics": revive_metrics,
        "revive_attempted_metrics": revive_attempted,
        "baseline_metrics": baseline_metrics,
        "comparison": comparison,
    }