"""
REVIVE AI — Revenue Detection Layer (Phase 5)

Deterministic, rule-based detection of revenue-at-risk events.
No LLM involved anywhere in this file — per Section 7 of the spec,
detection must be reliable and fully explainable.

Idempotency is handled by loading all existing (source_type, source_id)
pairs ONCE per run, into an in-memory set, rather than querying the
database once per candidate record. With thousands of records, the
per-record approach means thousands of network round trips to Neon —
this batched approach means one.

run_detection() is the single entry point — both the API route and the
CLI script call this same function, so detection behaves identically
regardless of how it's triggered (on-demand now, scheduled later).
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import Transaction, CheckoutSession, Invoice, RevenueRiskCase


def determine_priority(amount: float) -> str:
    """Deterministic priority tiering based on amount at risk."""
    if amount >= 10000:
        return "high"
    elif amount >= 2000:
        return "medium"
    else:
        return "low"


def _load_existing_case_keys(db: Session, merchant_id: uuid.UUID) -> set[tuple[str, uuid.UUID]]:
    """
    One query, loads every (source_type, source_id) pair that already has
    a case, for this merchant. Used as an in-memory lookup instead of a
    per-record database query.
    """
    existing = (
        db.query(RevenueRiskCase.source_type, RevenueRiskCase.source_id)
        .filter(RevenueRiskCase.merchant_id == merchant_id)
        .all()
    )
    return {(source_type, source_id) for source_type, source_id in existing}


def detect_failed_payments(
    db: Session, merchant_id: uuid.UUID, existing_keys: set
) -> list[RevenueRiskCase]:
    """Rule: any transaction with status == 'failed' is revenue at risk."""
    new_cases = []

    failed_transactions = (
        db.query(Transaction)
        .filter(
            Transaction.merchant_id == merchant_id,
            Transaction.status == "failed",
        )
        .all()
    )

    for txn in failed_transactions:
        if ("transaction", txn.id) in existing_keys:
            continue

        amount = float(txn.amount)
        case = RevenueRiskCase(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            customer_id=txn.customer_id,
            scenario="failed_payment",
            source_type="transaction",
            source_id=txn.id,
            amount_at_risk=txn.amount,
            priority=determine_priority(amount),
            status="open",
        )
        db.add(case)
        new_cases.append(case)
        existing_keys.add(("transaction", txn.id))  # prevent dupes within this same run

    return new_cases


def detect_checkout_abandonment(
    db: Session, merchant_id: uuid.UUID, existing_keys: set
) -> list[RevenueRiskCase]:
    """Rule: any checkout session with status == 'abandoned' is revenue at risk."""
    new_cases = []

    abandoned_sessions = (
        db.query(CheckoutSession)
        .filter(
            CheckoutSession.merchant_id == merchant_id,
            CheckoutSession.status == "abandoned",
        )
        .all()
    )

    for session in abandoned_sessions:
        if ("checkout_session", session.id) in existing_keys:
            continue

        amount = float(session.amount)
        case = RevenueRiskCase(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            customer_id=session.customer_id,
            scenario="checkout_abandonment",
            source_type="checkout_session",
            source_id=session.id,
            amount_at_risk=session.amount,
            priority=determine_priority(amount),
            status="open",
        )
        db.add(case)
        new_cases.append(case)
        existing_keys.add(("checkout_session", session.id))

    return new_cases


def detect_overdue_receivables(
    db: Session, merchant_id: uuid.UUID, existing_keys: set
) -> list[RevenueRiskCase]:
    """Rule: any invoice with status == 'overdue' is revenue at risk."""
    new_cases = []

    overdue_invoices = (
        db.query(Invoice)
        .filter(
            Invoice.merchant_id == merchant_id,
            Invoice.status == "overdue",
        )
        .all()
    )

    for invoice in overdue_invoices:
        if ("invoice", invoice.id) in existing_keys:
            continue

        amount = float(invoice.amount)
        case = RevenueRiskCase(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            customer_id=invoice.customer_id,
            scenario="overdue_receivable",
            source_type="invoice",
            source_id=invoice.id,
            amount_at_risk=invoice.amount,
            priority=determine_priority(amount),
            status="open",
        )
        db.add(case)
        new_cases.append(case)
        existing_keys.add(("invoice", invoice.id))

    return new_cases


def run_detection(db: Session, merchant_id: uuid.UUID) -> dict:
    """
    Single entry point for the whole detection layer.
    Runs all three rules, commits the results, and returns a summary.

    This is the function to call from anywhere detection needs to be
    triggered — an API route, a CLI script, or (later) a scheduled job.
    """
    existing_keys = _load_existing_case_keys(db, merchant_id)

    failed_payment_cases = detect_failed_payments(db, merchant_id, existing_keys)
    checkout_cases = detect_checkout_abandonment(db, merchant_id, existing_keys)
    overdue_cases = detect_overdue_receivables(db, merchant_id, existing_keys)

    db.commit()

    total_new_cases = len(failed_payment_cases) + len(checkout_cases) + len(overdue_cases)
    total_amount_at_risk = sum(
        float(c.amount_at_risk)
        for c in (failed_payment_cases + checkout_cases + overdue_cases)
    )

    return {
        "scan_completed_at": datetime.now(timezone.utc).isoformat(),
        "merchant_id": str(merchant_id),
        "new_cases_created": {
            "failed_payment": len(failed_payment_cases),
            "checkout_abandonment": len(checkout_cases),
            "overdue_receivable": len(overdue_cases),
            "total": total_new_cases,
        },
        "total_amount_at_risk_detected": round(total_amount_at_risk, 2),
    }