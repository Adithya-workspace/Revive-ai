"""
REVIVE AI — Verification Layer (Phase 11)

THE ONLY PLACE in the system allowed to mark a case "recovered".
Per Section 13 of the spec: an action having executed is not the same
as revenue actually being recovered. This module checks for genuine
confirmation before updating case status.

Two verification paths:
  1. Immediate-outcome actions (retries) — the outcome was already
     determined during execution (Phase 10), grounded in the case's
     real recovery_probability. Verification here means writing that
     outcome back to the actual source record (Transaction/Invoice)
     and THEN updating the case — the source-of-truth update is what
     makes this "verified" rather than just "attempted."
  2. Pending actions (reminders/messages) — no outcome exists yet.
     Verification simulates whether the customer "responded" by now,
     again grounded in recovery_probability, since this is a SIMULATED
     system with no real customers to actually respond.

Idempotent — only processes ActionResults where verified = False.
Batch-loads everything upfront; commits incrementally.
"""

import random
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import RevenueRiskCase, RecoveryAction, ActionResult, Transaction, Invoice

COMMIT_EVERY_N = 100

IMMEDIATE_OUTCOME_STATUSES = {"success", "failed"}


def _load_unverified_results(db: Session, merchant_id: uuid.UUID) -> list[ActionResult]:
    return (
        db.query(ActionResult)
        .join(RecoveryAction, RecoveryAction.id == ActionResult.recovery_action_id)
        .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
        .filter(
            RevenueRiskCase.merchant_id == merchant_id,
            ActionResult.verified == False,  # noqa: E712
        )
        .all()
    )


def verify_immediate_outcome(result: ActionResult) -> tuple[str, str]:
    """
    For retries that already had a success/failed outcome from
    execution: verification confirms it by writing the outcome back to
    the source record (done by the caller) and translating it into a
    verified_outcome. No new randomness introduced here — we're
    confirming what execution already determined, not re-rolling it.
    """
    if result.status == "success":
        return "recovered", (
            "Verified: simulated payment retry succeeded and source transaction "
            "status was updated to reflect the successful payment."
        )
    else:
        return "not_recovered", (
            "Verified: simulated payment retry failed. Source transaction status "
            "remains failed — no revenue recovered from this attempt."
        )


def verify_pending_outcome(case: RevenueRiskCase) -> tuple[str, str]:
    """
    For reminder/message-based actions with no immediate outcome: this
    is where we simulate whether "enough time has passed and the
    customer responded." Since there's no real customer, this draw is
    grounded in the case's actual recovery_probability — the same
    transparent score used everywhere else in the system, not a fresh
    arbitrary number.
    """
    recovery_probability = case.recovery_probability if case.recovery_probability is not None else 0.5
    responded = random.random() < recovery_probability

    if responded:
        return "recovered", (
            f"Verified: simulated customer response received after reminder/message. "
            f"Draw grounded in case recovery_probability of {recovery_probability:.2f}."
        )
    else:
        return "not_recovered", (
            f"Verified: no simulated customer response yet after reminder/message. "
            f"Draw grounded in case recovery_probability of {recovery_probability:.2f}. "
            "Case remains open for further follow-up or stopping-rule evaluation."
        )


def run_verification(db: Session, merchant_id: uuid.UUID) -> dict:
    print("Loading unverified action results...", flush=True)
    unverified = _load_unverified_results(db, merchant_id)
    print(f"Found {len(unverified)} results needing verification.\n", flush=True)

    print("Preloading cases, transactions, invoices...", flush=True)
    recovery_action_ids = [r.recovery_action_id for r in unverified]
    actions_by_id = {
        a.id: a for a in db.query(RecoveryAction).filter(RecoveryAction.id.in_(recovery_action_ids)).all()
    }
    case_ids = [a.case_id for a in actions_by_id.values()]
    cases_by_id = {
        c.id: c for c in db.query(RevenueRiskCase).filter(RevenueRiskCase.id.in_(case_ids)).all()
    }
    transactions_by_id = {
        t.id: t for t in db.query(Transaction).filter(Transaction.merchant_id == merchant_id).all()
    }
    invoices_by_id = {
        i.id: i for i in db.query(Invoice).filter(Invoice.merchant_id == merchant_id).all()
    }
    print("Preload complete.\n", flush=True)

    total_verified = 0
    outcome_counts: dict[str, int] = {}
    uncommitted = 0

    for i, result in enumerate(unverified, 1):
        if i % 250 == 0:
            print(f"Progress: {i}/{len(unverified)}...", flush=True)

        action_row = actions_by_id.get(result.recovery_action_id)
        if action_row is None:
            continue
        case = cases_by_id.get(action_row.case_id)
        if case is None:
            continue

        if result.status in IMMEDIATE_OUTCOME_STATUSES:
            outcome, detail = verify_immediate_outcome(result)

            # Write the outcome back to the actual source record —
            # this is what makes it "verified" rather than just "attempted."
            if case.scenario == "failed_payment":
                txn = transactions_by_id.get(case.source_id)
                if txn:
                    txn.status = "success" if outcome == "recovered" else "failed"

        else:  # "pending"
            outcome, detail = verify_pending_outcome(case)

            if outcome == "recovered":
                if case.scenario == "overdue_receivable":
                    invoice = invoices_by_id.get(case.source_id)
                    if invoice:
                        invoice.status = "paid"
                # checkout_abandonment has no further source status to update
                # beyond the case itself — a completed checkout isn't modeled
                # as a separate record in this schema.

        result.verified = True
        result.verified_outcome = outcome
        result.verified_at = datetime.now(timezone.utc)
        result.verification_detail = detail

        # Only verification is allowed to set a case to "recovered" —
        # this is the enforcement point for that rule.
        if outcome == "recovered":
            case.status = "recovered"

        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        total_verified += 1
        uncommitted += 1

        if uncommitted >= COMMIT_EVERY_N:
            db.commit()
            print(f"  (committed {total_verified} so far)", flush=True)
            uncommitted = 0

    db.commit()

    return {
        "verification_completed_at": datetime.now(timezone.utc).isoformat(),
        "merchant_id": str(merchant_id),
        "results_verified": total_verified,
        "outcome_breakdown": outcome_counts,
    }