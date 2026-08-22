"""
REVIVE AI — Action Execution Layer (Phase 10)

Executes ONLY policy-APPROVED actions. Every outcome is honestly labeled
SIMULATED (real Razorpay test-mode integration is deferred to Phase 15,
per the original roadmap) — never presented as if it were a real API
call. See docs/ARCHITECTURE.md Section 5 for the REAL/TEST/SIMULATED
distinction this follows.

Idempotent via a unique constraint on ActionResult.recovery_action_id —
re-running this never double-executes an action. Batch-loads everything
upfront; commits incrementally, following the same discipline as every
prior phase.
"""

import random
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import RevenueRiskCase, RecoveryAction, ActionResult

COMMIT_EVERY_N = 100

# Actions where an outcome (success/failed) can be determined immediately
# in simulation, grounded in the case's own recovery_probability rather
# than arbitrary randomness.
IMMEDIATE_OUTCOME_ACTIONS = {"RETRY_PAYMENT", "DELAYED_RETRY"}

# Actions where the real-world outcome depends on a customer response
# that hasn't happened yet — status starts "pending" and Verification
# (Phase 11) is what later resolves it.
PENDING_OUTCOME_ACTIONS = {
    "SEND_PAYMENT_REMINDER",
    "SEND_CHECKOUT_RECOVERY_MESSAGE",
    "SEND_OVERDUE_REMINDER",
    "TRACK_PROMISE_TO_PAY",
}

# Passive actions never get an ActionResult — there's nothing to execute
PASSIVE_ACTIONS = {"ESCALATE_TO_HUMAN", "STOP_RECOVERY_ATTEMPTS"}


def _load_already_executed_action_ids(db: Session, merchant_id: uuid.UUID) -> set[uuid.UUID]:
    existing = (
        db.query(ActionResult.recovery_action_id)
        .join(RecoveryAction, RecoveryAction.id == ActionResult.recovery_action_id)
        .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
        .filter(RevenueRiskCase.merchant_id == merchant_id)
        .all()
    )
    return {rid for (rid,) in existing}


def simulate_execution(action_row: RecoveryAction, case: RevenueRiskCase) -> dict:
    """
    Produces a SIMULATED outcome for one approved action. Immediate-
    outcome actions (retries) roll against the case's actual recovery
    probability, so simulated results are grounded in real scoring data
    rather than arbitrary chance. Never claims REAL or TEST mode.
    """
    action = action_row.action

    if action in IMMEDIATE_OUTCOME_ACTIONS:
        recovery_probability = case.recovery_probability if case.recovery_probability is not None else 0.5
        succeeded = random.random() < recovery_probability

        return {
            "mode": "SIMULATED",
            "status": "success" if succeeded else "failed",
            "result_detail": (
                f"Simulated {action.lower()} outcome, drawn against this case's "
                f"recovery_probability of {recovery_probability:.2f}. "
                f"Result: {'succeeded' if succeeded else 'failed'}. "
                "No real Razorpay call was made (deferred to Phase 15)."
            ),
        }

    if action in PENDING_OUTCOME_ACTIONS:
        return {
            "mode": "SIMULATED",
            "status": "pending",
            "result_detail": (
                f"Simulated {action.lower()} — message/notification dispatch simulated. "
                "Outcome depends on subsequent customer behavior and will be resolved "
                "by the Verification stage (Phase 11), not assumed here."
            ),
        }

    # Shouldn't reach here given the passive-action filter upstream, but
    # never silently execute an unrecognized action.
    return {
        "mode": "SIMULATED",
        "status": "failed",
        "result_detail": f"Unrecognized action type '{action}' — not executed.",
    }


def run_action_executor(db: Session, merchant_id: uuid.UUID) -> dict:
    already_executed = _load_already_executed_action_ids(db, merchant_id)

    print("Loading APPROVED actions...", flush=True)
    approved_actions = (
        db.query(RecoveryAction)
        .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
        .filter(
            RevenueRiskCase.merchant_id == merchant_id,
            RecoveryAction.policy_decision == "APPROVED",
            RecoveryAction.action.notin_(PASSIVE_ACTIONS),
        )
        .all()
    )
    to_execute = [a for a in approved_actions if a.id not in already_executed]

    print(f"{len(to_execute)} approved actions need execution "
          f"({len(approved_actions) - len(to_execute)} already executed).\n", flush=True)

    print("Preloading cases...", flush=True)
    case_ids = [a.case_id for a in to_execute]
    cases_by_id = {
        c.id: c for c in db.query(RevenueRiskCase).filter(RevenueRiskCase.id.in_(case_ids)).all()
    }
    print("Preload complete.\n", flush=True)

    total_executed = 0
    uncommitted = 0
    status_counts: dict[str, int] = {}

    for i, action_row in enumerate(to_execute, 1):
        if i % 250 == 0:
            print(f"Progress: {i}/{len(to_execute)}...", flush=True)

        case = cases_by_id.get(action_row.case_id)
        if case is None:
            continue

        outcome = simulate_execution(action_row, case)

        result_row = ActionResult(
            id=uuid.uuid4(),
            recovery_action_id=action_row.id,
            mode=outcome["mode"],
            status=outcome["status"],
            result_detail=outcome["result_detail"],
        )
        db.add(result_row)

        status_counts[outcome["status"]] = status_counts.get(outcome["status"], 0) + 1
        total_executed += 1
        uncommitted += 1

        if uncommitted >= COMMIT_EVERY_N:
            db.commit()
            print(f"  (committed {total_executed} so far)", flush=True)
            uncommitted = 0

    db.commit()

    return {
        "execution_completed_at": datetime.now(timezone.utc).isoformat(),
        "merchant_id": str(merchant_id),
        "actions_executed": total_executed,
        "status_breakdown": status_counts,
        "mode": "SIMULATED",
        "note": "Real Razorpay test-mode integration deferred to Phase 15 per project roadmap.",
    }