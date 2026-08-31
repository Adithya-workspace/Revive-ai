"""
REVIVE AI — Demo Mode support routes (Phase 18, Sections 37-38)

create-case seeds ONE fresh, unprocessed source record so every stage
of the pipeline has real, live work to do during a demo — since the
full synthetic dataset has already been processed end-to-end, running
the real pipeline buttons against it would show "0 new" every time.
This is clearly demo-generated data, never mixed into the real
synthetic dataset or its metrics.
"""

import random
import uuid
from datetime import datetime, timezone, timedelta, date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Merchant, Customer, Transaction, CheckoutSession, Invoice

router = APIRouter(prefix="/demo", tags=["demo"])

FAILURE_REASONS = ["insufficient_funds", "card_declined", "network_error", "bank_timeout", "expired_card"]


@router.post("/create-case/{merchant_id}")
def create_demo_case(merchant_id: str, db: Session = Depends(get_db)):
    """
    Creates ONE fresh, unprocessed source record (transaction, checkout
    session, or invoice) for an existing customer, so the demo
    walkthrough always has live work for the pipeline buttons to do.
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

from evaluation.run_evaluation import (
    compute_revive_attempted_metrics,
    build_comparison,
)
from app.services.analytics import get_full_analytics
from app.services.baseline import compute_baseline_metrics


@router.post("/run-evaluation/{merchant_id}")
def run_evaluation_live(merchant_id: str, db: Session = Depends(get_db)):
    """
    Same evaluation logic as `python -m evaluation.run_evaluation`,
    callable live from the demo page so judges can trigger it without
    touching a terminal.
    """
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