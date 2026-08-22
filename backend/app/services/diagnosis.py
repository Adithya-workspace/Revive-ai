"""
REVIVE AI — Diagnosis Orchestrator (Phase 7)

Routes each case to rules-based diagnosis where possible, and LLM
diagnosis only for genuinely ambiguous cases (Section 8). Idempotent —
only diagnoses cases that don't already have a diagnosis.

IMPORTANT: the max_llm_calls cap is enforced BEFORE any LLM call is
made, for every scenario. Diagnoses are committed incrementally (every
20 rows) rather than all at the end, to avoid Neon idle-connection
timeouts during long LLM-bound runs, and so a crash partway through
only loses the current small batch — the idempotency check means a
re-run picks up right where it left off.
"""

import time
import uuid
from datetime import datetime, timezone
from collections import defaultdict
from sqlalchemy.orm import Session

from app.models import RevenueRiskCase, Transaction, Invoice, CheckoutSession, Diagnosis, Customer
from app.services.diagnosis_rules import (
    diagnose_failed_payment_by_rules,
    diagnose_overdue_receivable_by_rules,
)
from app.services.diagnosis_llm import diagnose_with_llm, fallback_diagnosis

SECONDS_BETWEEN_LLM_CALLS = 2.5
COMMIT_EVERY_N_DIAGNOSES = 20


def _load_already_diagnosed_case_ids(db: Session, merchant_id: uuid.UUID) -> set[uuid.UUID]:
    diagnosed = (
        db.query(Diagnosis.case_id)
        .join(RevenueRiskCase, RevenueRiskCase.id == Diagnosis.case_id)
        .filter(RevenueRiskCase.merchant_id == merchant_id)
        .all()
    )
    return {case_id for (case_id,) in diagnosed}


class DiagnosisContext:
    def __init__(self, db: Session, merchant_id: uuid.UUID):
        print("Preloading transactions...", flush=True)
        self.transactions_by_id = {
            t.id: t for t in db.query(Transaction).filter(Transaction.merchant_id == merchant_id).all()
        }

        print("Preloading invoices...", flush=True)
        all_invoices = db.query(Invoice).filter(Invoice.merchant_id == merchant_id).all()
        self.invoices_by_id = {inv.id: inv for inv in all_invoices}

        self.invoices_by_customer = defaultdict(list)
        for inv in all_invoices:
            if inv.customer_id:
                self.invoices_by_customer[inv.customer_id].append(inv)

        print("Preloading checkout sessions...", flush=True)
        self.sessions_by_id = {
            s.id: s for s in db.query(CheckoutSession).filter(CheckoutSession.merchant_id == merchant_id).all()
        }

        print("Preloading customers...", flush=True)
        self.customers_by_id = {
            c.id: c for c in db.query(Customer).filter(Customer.merchant_id == merchant_id).all()
        }

        print("Preload complete.\n", flush=True)


def _build_checkout_context(case: RevenueRiskCase, ctx: DiagnosisContext) -> dict:
    session = ctx.sessions_by_id.get(case.source_id)
    customer = ctx.customers_by_id.get(case.customer_id) if case.customer_id else None

    minutes_inactive = None
    if session and session.started_at and session.last_activity_at:
        delta = session.last_activity_at - session.started_at
        minutes_inactive = round(delta.total_seconds() / 60, 1)

    return {
        "scenario": "checkout_abandonment",
        "amount_at_risk": float(case.amount_at_risk),
        "minutes_between_start_and_last_activity": minutes_inactive,
        "customer_name": customer.name if customer else "unknown",
        "case_priority": case.priority,
    }


def _build_overdue_context(case: RevenueRiskCase, ctx: DiagnosisContext) -> dict:
    invoice = ctx.invoices_by_id.get(case.source_id)
    customer = ctx.customers_by_id.get(case.customer_id) if case.customer_id else None

    days_overdue = None
    if invoice and invoice.due_date:
        days_overdue = (datetime.now(timezone.utc).date() - invoice.due_date).days

    past_invoices = ctx.invoices_by_customer.get(case.customer_id, [])
    paid_count = sum(1 for inv in past_invoices if inv.status == "paid")
    overdue_count = sum(1 for inv in past_invoices if inv.status == "overdue")

    return {
        "scenario": "overdue_receivable",
        "amount_at_risk": float(case.amount_at_risk),
        "days_overdue": days_overdue,
        "customer_name": customer.name if customer else "unknown",
        "customer_past_paid_invoices": paid_count,
        "customer_past_overdue_invoices": overdue_count,
        "case_priority": case.priority,
    }


def _build_failed_payment_context(case: RevenueRiskCase, ctx: DiagnosisContext) -> dict:
    txn = ctx.transactions_by_id.get(case.source_id)
    customer = ctx.customers_by_id.get(case.customer_id) if case.customer_id else None

    return {
        "scenario": "failed_payment",
        "amount_at_risk": float(case.amount_at_risk),
        "failure_reason": txn.failure_reason if txn else "unknown",
        "retry_count": txn.retry_count if txn else 0,
        "customer_name": customer.name if customer else "unknown",
        "case_priority": case.priority,
    }


def try_resolve_by_rules(case: RevenueRiskCase, ctx: DiagnosisContext) -> tuple[dict | None, dict | None]:
    """
    Attempts to resolve a case using ONLY deterministic rules — makes no
    LLM call. Returns (rule_result, llm_context):
      - (result_dict, None)  -> resolved by rules, no LLM needed
      - (None, context_dict) -> ambiguous, this context should go to the LLM
      - (None, None)         -> unknown scenario, use fallback
    """
    if case.scenario == "failed_payment":
        txn = ctx.transactions_by_id.get(case.source_id)
        rule_result = diagnose_failed_payment_by_rules(txn.failure_reason if txn else None)
        if rule_result:
            return rule_result, None
        return None, _build_failed_payment_context(case, ctx)

    elif case.scenario == "overdue_receivable":
        invoice = ctx.invoices_by_id.get(case.source_id)
        rule_result = diagnose_overdue_receivable_by_rules(invoice.due_date) if invoice else None
        if rule_result:
            return rule_result, None
        return None, _build_overdue_context(case, ctx)

    elif case.scenario == "checkout_abandonment":
        return None, _build_checkout_context(case, ctx)

    return None, None


def run_diagnosis(db: Session, merchant_id: uuid.UUID, max_llm_calls: int = 50) -> dict:
    already_diagnosed = _load_already_diagnosed_case_ids(db, merchant_id)

    open_cases = (
        db.query(RevenueRiskCase)
        .filter(
            RevenueRiskCase.merchant_id == merchant_id,
            RevenueRiskCase.status == "open",
        )
        .all()
    )

    cases_to_diagnose = [c for c in open_cases if c.id not in already_diagnosed]

    print(f"{len(cases_to_diagnose)} cases need diagnosis "
          f"({len(open_cases) - len(cases_to_diagnose)} already diagnosed).\n", flush=True)

    ctx = DiagnosisContext(db, merchant_id)

    total_new = 0
    rules_count = 0
    llm_count = 0
    llm_calls_made = 0
    skipped_due_to_cap = 0
    uncommitted_count = 0

    total = len(cases_to_diagnose)
    for i, case in enumerate(cases_to_diagnose, 1):
        if i % 250 == 0:
            print(f"Progress: {i}/{total} cases processed... "
                  f"(rules={rules_count}, llm={llm_count}, skipped={skipped_due_to_cap})", flush=True)

        rule_result, llm_context = try_resolve_by_rules(case, ctx)

        if rule_result is not None:
            result = rule_result
            rules_count += 1

        elif llm_context is not None:
            if llm_calls_made >= max_llm_calls:
                skipped_due_to_cap += 1
                continue

            try:
                result = diagnose_with_llm(llm_context)
            except Exception as e:
                result = fallback_diagnosis(f"LLM diagnosis failed: {str(e)}")

            llm_calls_made += 1
            llm_count += 1
            time.sleep(SECONDS_BETWEEN_LLM_CALLS)

        else:
            result = fallback_diagnosis(f"Unknown scenario type: {case.scenario}")
            rules_count += 1

        diagnosis_row = Diagnosis(
            id=uuid.uuid4(),
            case_id=case.id,
            diagnosis=result["diagnosis"],
            confidence=result["confidence"],
            evidence=result["evidence"],
            recommended_next_step=result["recommended_next_step"],
            reasoning_summary=result["reasoning_summary"],
            diagnosis_source=result["diagnosis_source"],
        )
        db.add(diagnosis_row)
        total_new += 1
        uncommitted_count += 1

        if uncommitted_count >= COMMIT_EVERY_N_DIAGNOSES:
            db.commit()
            print(f"  (committed {total_new} so far)", flush=True)
            uncommitted_count = 0

    print(f"\nFinal commit for remaining diagnoses...", flush=True)
    db.commit()
    print("Committed.", flush=True)

    return {
        "diagnosis_completed_at": datetime.now(timezone.utc).isoformat(),
        "merchant_id": str(merchant_id),
        "cases_diagnosed": total_new,
        "diagnosed_by_rules": rules_count,
        "diagnosed_by_llm": llm_count,
        "skipped_due_to_llm_cap": skipped_due_to_cap,
        "llm_call_cap": max_llm_calls,
    }