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

from app.models import RevenueRiskCase, RecoveryAction, ActionResult, Transaction

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

def simulate_api_failure(db: Session, merchant_id: uuid.UUID, case_id: uuid.UUID | None = None) -> dict:
    """
    Demonstrates graceful failure handling per Section 17.

    If case_id points to an existing APPROVED action with no result yet,
    fails that one directly. Otherwise, builds a brand-new demo case
    from scratch — using the REAL scoring, diagnosis-rules, strategy,
    and policy functions (never faked) — guaranteed to land as
    APPROVED, so this demo is always runnable regardless of what state
    the rest of the database is in. Only the final execution step is
    deliberately made to fail, to demonstrate the safety guarantees:

      - Idempotency: refuses to create a duplicate result for the same action.
      - The case is never marked recovered as a result of a failure.
      - The failure is logged distinctly from a legitimate customer decline.
    """
    from app.models import AuditEvent, Customer, Diagnosis
    from app.services.scoring import score_case
    from app.services.diagnosis_rules import diagnose_failed_payment_by_rules
    from app.services.strategy import determine_strategy
    from app.policies.engine import evaluate_policy, _load_policy_values

    action_row = None

    if case_id:
        already_has_result_subquery = db.query(ActionResult.recovery_action_id).subquery()
        action_row = (
            db.query(RecoveryAction)
            .filter(
                RecoveryAction.case_id == case_id,
                RecoveryAction.policy_decision == "APPROVED",
                RecoveryAction.action.notin_(PASSIVE_ACTIONS),
                RecoveryAction.id.notin_(already_has_result_subquery),
            )
            .first()
        )

    if action_row is None:
        # Build a fresh, self-contained demo case using the real pipeline
        # functions, guaranteed to resolve to APPROVED.
        customer = db.query(Customer).filter(Customer.merchant_id == merchant_id).first()
        if customer is None:
            return {"success": False, "message": "No customer found for this merchant to attach a demo case to."}

        demo_txn = Transaction(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            customer_id=customer.id,
            amount=2500,  # deliberately under the automatic-action ceiling
            currency="INR",
            status="failed",
            failure_reason="insufficient_funds",  # deterministic, high-confidence rule
            retry_count=0,
        )
        db.add(demo_txn)
        db.flush()

        demo_case = RevenueRiskCase(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            customer_id=customer.id,
            scenario="failed_payment",
            source_type="transaction",
            source_id=demo_txn.id,
            amount_at_risk=demo_txn.amount,
            priority="medium",
            status="open",
        )
        db.add(demo_case)
        db.flush()

        score_result = score_case(demo_case, customer_success_rates={}, transaction_retry_counts={})
        demo_case.recovery_probability = score_result["recovery_probability"]

        rule_result = diagnose_failed_payment_by_rules("insufficient_funds")
        demo_diagnosis = Diagnosis(
            id=uuid.uuid4(),
            case_id=demo_case.id,
            diagnosis=rule_result["diagnosis"],
            confidence=rule_result["confidence"],
            evidence=rule_result["evidence"],
            recommended_next_step=rule_result["recommended_next_step"],
            reasoning_summary=rule_result["reasoning_summary"],
            diagnosis_source="rules",
        )
        db.add(demo_diagnosis)
        db.flush()

        strategy_decision = determine_strategy(demo_case, demo_diagnosis)
        action_row = RecoveryAction(
            id=uuid.uuid4(),
            case_id=demo_case.id,
            action=strategy_decision["action"],
            reason=strategy_decision["reason"],
            expected_value=strategy_decision["expected_value"],
            confidence=strategy_decision["confidence"],
            strategy_source="rules",
        )
        db.add(action_row)
        db.flush()

        policy_values = _load_policy_values(db)
        decision, reason = evaluate_policy(action_row, demo_case, retry_count=0, policy_values=policy_values)
        action_row.policy_decision = decision
        action_row.policy_reason = reason
        db.flush()

        if decision != "APPROVED":
            db.rollback()
            return {
                "success": False,
                "message": (
                    f"Demo case unexpectedly resolved to '{decision}' instead of APPROVED "
                    "— this shouldn't happen given the fixed demo parameters. No changes were made."
                ),
            }

    # Deliberately simulate the failure — models a real infra failure
    # (gateway timeout), never a fabricated customer decline.
    result_row = ActionResult(
        id=uuid.uuid4(),
        recovery_action_id=action_row.id,
        mode="SIMULATED",
        status="failed",
        result_detail=(
            "SIMULATED infrastructure failure: external payment gateway did not "
            "respond (connection timeout). This is NOT a customer decline — "
            "REVIVE's own attempt to reach the gateway failed. No duplicate "
            "action was taken; this case remains eligible for a policy-governed "
            "retry or escalation on the next pipeline run."
        ),
    )
    db.add(result_row)

    audit_event = AuditEvent(
        case_id=action_row.case_id,
        event_type="ACTION_EXECUTION_API_FAILURE",
        actor="system:action_executor",
        result="failed",
        event_metadata={
            "action": action_row.action,
            "simulated_error": "connection_timeout",
            "note": "Demo-triggered failure simulation, not a real gateway call.",
        },
    )
    db.add(audit_event)

    db.commit()

    case = db.query(RevenueRiskCase).filter(RevenueRiskCase.id == action_row.case_id).first()

    return {
        "success": True,
        "case_id": str(action_row.case_id),
        "action": action_row.action,
        "message": (
            "Simulated an external API failure during execution. The case was "
            "NOT marked recovered, no duplicate action was created, and the "
            "failure is recorded in the audit trail as an infrastructure "
            "failure — distinct from a customer decline."
        ),
        "case_status_after_failure": case.status if case else None,
    }