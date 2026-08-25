"""
Tests for the deterministic revenue detection layer (Phase 5).
"""

import uuid
from datetime import date, timedelta
from app.models import Transaction, CheckoutSession, Invoice, RevenueRiskCase
from app.detection.rules import run_detection, determine_priority


def test_determine_priority_tiers_correctly():
    assert determine_priority(500) == "low"
    assert determine_priority(1999.99) == "low"
    assert determine_priority(2000) == "medium"
    assert determine_priority(9999.99) == "medium"
    assert determine_priority(10000) == "high"
    assert determine_priority(50000) == "high"


def test_detects_failed_transaction_as_case(db, merchant, customer):
    txn = Transaction(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        customer_id=customer.id,
        amount=1500,
        currency="INR",
        status="failed",
        failure_reason="insufficient_funds",
        retry_count=0,
    )
    db.add(txn)
    db.flush()

    summary = run_detection(db, merchant.id)

    assert summary["new_cases_created"]["failed_payment"] == 1
    case = db.query(RevenueRiskCase).filter(RevenueRiskCase.source_id == txn.id).first()
    assert case is not None
    assert case.scenario == "failed_payment"
    assert case.source_type == "transaction"
    assert float(case.amount_at_risk) == 1500
    assert case.priority == "low"


def test_successful_transaction_does_not_create_a_case(db, merchant, customer):
    txn = Transaction(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        customer_id=customer.id,
        amount=1500,
        currency="INR",
        status="success",
    )
    db.add(txn)
    db.flush()

    summary = run_detection(db, merchant.id)

    assert summary["new_cases_created"]["failed_payment"] == 0


def test_detects_abandoned_checkout_as_case(db, merchant, customer):
    session = CheckoutSession(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        customer_id=customer.id,
        amount=3000,
        currency="INR",
        status="abandoned",
    )
    db.add(session)
    db.flush()

    summary = run_detection(db, merchant.id)

    assert summary["new_cases_created"]["checkout_abandonment"] == 1
    case = db.query(RevenueRiskCase).filter(RevenueRiskCase.source_id == session.id).first()
    assert case.scenario == "checkout_abandonment"
    assert case.priority == "medium"


def test_detects_overdue_invoice_as_case(db, merchant, customer):
    invoice = Invoice(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        customer_id=customer.id,
        amount=12000,
        currency="INR",
        due_date=date.today() - timedelta(days=10),
        status="overdue",
    )
    db.add(invoice)
    db.flush()

    summary = run_detection(db, merchant.id)

    assert summary["new_cases_created"]["overdue_receivable"] == 1
    case = db.query(RevenueRiskCase).filter(RevenueRiskCase.source_id == invoice.id).first()
    assert case.scenario == "overdue_receivable"
    assert case.priority == "high"


def test_detection_is_idempotent(db, merchant, customer):
    txn = Transaction(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        customer_id=customer.id,
        amount=1500,
        currency="INR",
        status="failed",
        failure_reason="card_declined",
    )
    db.add(txn)
    db.flush()

    first_run = run_detection(db, merchant.id)
    second_run = run_detection(db, merchant.id)

    assert first_run["new_cases_created"]["total"] == 1
    assert second_run["new_cases_created"]["total"] == 0

    total_cases = db.query(RevenueRiskCase).filter(RevenueRiskCase.source_id == txn.id).count()
    assert total_cases == 1