"""
REVIVE AI — Policy / Guardrail Engine (Phase 9)

THE SAFETY BOUNDARY. This module contains ZERO LLM calls and ZERO calls
into diagnosis/strategy logic — it only reads policy values from the
database and applies pure deterministic rules against a proposed action.

"AI proposes, policy disposes" — this is the "disposes" half.

Every decision is one of:
  APPROVED    — action may proceed automatically
  NEEDS_HUMAN — action requires human approval before proceeding
  REJECTED    — action is not permitted at all under current policy

Idempotent — only evaluates RecoveryActions that don't yet have a
policy_decision. Batch-loads everything upfront; commits incrementally.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import RevenueRiskCase, RecoveryAction, Transaction, Policy

COMMIT_EVERY_N = 100

# Actions that never touch money or contact a customer automatically —
# there's nothing to authorize, they're always approved.
PASSIVE_ACTIONS = {"ESCALATE_TO_HUMAN", "STOP_RECOVERY_ATTEMPTS"}

# Actions that involve retrying a payment, subject to the retry cap
RETRY_ACTIONS = {"RETRY_PAYMENT", "DELAYED_RETRY"}


def _load_policy_values(db: Session) -> dict[str, str]:
    """One query, loads all policy key-value pairs into a dict."""
    policies = db.query(Policy).all()
    return {p.key: p.value for p in policies}


def evaluate_policy(
    action_row: RecoveryAction,
    case: RevenueRiskCase,
    retry_count: int,
    policy_values: dict[str, str],
) -> tuple[str, str]:
    """
    Applies deterministic policy rules to a single proposed action.
    Returns (decision, reason). No LLM involvement whatsoever.
    """
    action = action_row.action

    if action in PASSIVE_ACTIONS:
        return "APPROVED", f"'{action}' is a passive action — no automatic execution to authorize."

    max_retries = int(policy_values.get("max_automatic_retries", 2))
    max_amount = float(policy_values.get("max_automatic_action_amount", 5000))
    min_confidence = float(policy_values.get("min_confidence_for_automatic_action", 0.60))

    if action in RETRY_ACTIONS and retry_count >= max_retries:
        return "REJECTED", (
            f"Action '{action}' rejected: transaction has already reached "
            f"{retry_count} retries, at or above the policy cap of {max_retries}."
        )

    amount = float(case.amount_at_risk)

    if amount >= max_amount:
        return "NEEDS_HUMAN", (
            f"Amount at risk (₹{amount:,.2f}) meets or exceeds the automatic action "
            f"ceiling (₹{max_amount:,.2f}) — human approval required before proceeding."
        )

    if action_row.confidence < min_confidence:
        return "NEEDS_HUMAN", (
            f"Confidence ({action_row.confidence:.2f}) is below the minimum "
            f"({min_confidence:.2f}) required for automatic action — human approval required."
        )

    return "APPROVED", (
        f"Action '{action}' passes all policy checks: retry count {retry_count} "
        f"< cap {max_retries}, amount ₹{amount:,.2f} < ceiling ₹{max_amount:,.2f}, "
        f"confidence {action_row.confidence:.2f} >= minimum {min_confidence:.2f}."
    )


def run_policy_engine(db: Session, merchant_id: uuid.UUID) -> dict:
    print("Loading policy values...", flush=True)
    policy_values = _load_policy_values(db)
    print(f"Loaded {len(policy_values)} policy values: {policy_values}\n", flush=True)

    print("Loading unevaluated recovery actions...", flush=True)
    pending_actions = (
        db.query(RecoveryAction)
        .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
        .filter(
            RevenueRiskCase.merchant_id == merchant_id,
            RecoveryAction.policy_decision.is_(None),
        )
        .all()
    )
    print(f"Found {len(pending_actions)} actions needing a policy decision.\n", flush=True)

    print("Preloading cases and transactions...", flush=True)
    case_ids = [a.case_id for a in pending_actions]
    cases_by_id = {
        c.id: c for c in db.query(RevenueRiskCase).filter(RevenueRiskCase.id.in_(case_ids)).all()
    }
    txn_retry_counts = {
        t.id: t.retry_count
        for t in db.query(Transaction).filter(Transaction.merchant_id == merchant_id).all()
    }
    print("Preload complete.\n", flush=True)

    decision_counts: dict[str, int] = {}
    uncommitted = 0
    total_evaluated = 0

    for i, action_row in enumerate(pending_actions, 1):
        if i % 500 == 0:
            print(f"Progress: {i}/{len(pending_actions)}...", flush=True)

        case = cases_by_id.get(action_row.case_id)
        if case is None:
            continue

        retry_count = 0
        if case.scenario == "failed_payment":
            retry_count = txn_retry_counts.get(case.source_id, 0)

        decision, reason = evaluate_policy(action_row, case, retry_count, policy_values)

        action_row.policy_decision = decision
        action_row.policy_reason = reason

        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        total_evaluated += 1
        uncommitted += 1

        if uncommitted >= COMMIT_EVERY_N:
            db.commit()
            print(f"  (committed {total_evaluated} so far)", flush=True)
            uncommitted = 0

    db.commit()

    return {
        "policy_run_completed_at": datetime.now(timezone.utc).isoformat(),
        "merchant_id": str(merchant_id),
        "actions_evaluated": total_evaluated,
        "decision_breakdown": decision_counts,
        "policy_values_used": policy_values,
    }