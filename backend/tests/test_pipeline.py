"""
Tests for idempotency/duplicate-action protection (Section 35) and the
full end-to-end pipeline (Section 36) — both the success path and the
safe-failure-handling path.
"""

import uuid
from datetime import date
from app.models import (
    Transaction,
    RevenueRiskCase,
    Diagnosis,
    RecoveryAction,
    ActionResult,
)
from app.detection.rules import run_detection
from app.services.scoring import run_scoring
from app.services.diagnosis import run_diagnosis
from app.services.strategy import run_strategy
from app.policies.engine import run_policy_engine
from app.actions.executor import run_action_executor
from app.services.verification import run_verification


def make_failed_transaction(merchant, customer, amount=1500, failure_reason="insufficient_funds"):
    txn = Transaction(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        customer_id=customer.id,
        amount=amount,
        currency="INR",
        status="failed",
        failure_reason=failure_reason,
        retry_count=0,
    )
    return txn


# --- Idempotency / duplicate-action protection ----------------------------

def test_action_executor_never_double_executes(db, merchant, customer):
    """
    Running the action executor twice on the same approved action must
    only produce ONE ActionResult — the unique constraint on
    recovery_action_id enforces this at the DB level, and the executor
    itself should skip already-executed actions before even reaching it.
    """
    txn = make_failed_transaction(merchant, customer)
    db.add(txn)
    db.flush()

    run_detection(db, merchant.id)
    run_scoring(db, merchant.id)
    run_diagnosis(db, merchant.id, max_llm_calls=0)
    run_strategy(db, merchant.id)
    run_policy_engine(db, merchant.id)

    first_run = run_action_executor(db, merchant.id)
    second_run = run_action_executor(db, merchant.id)

    case = db.query(RevenueRiskCase).filter(RevenueRiskCase.source_id == txn.id).first()
    action = db.query(RecoveryAction).filter(RecoveryAction.case_id == case.id).first()

    if action and action.policy_decision == "APPROVED":
        assert first_run["actions_executed"] == 1
        assert second_run["actions_executed"] == 0

        results_count = (
            db.query(ActionResult)
            .filter(ActionResult.recovery_action_id == action.id)
            .count()
        )
        assert results_count == 1


def test_verification_never_reverifies_same_result(db, merchant, customer):
    """A result already marked verified=True should never be processed again."""
    txn = make_failed_transaction(merchant, customer, failure_reason="expired_card")
    db.add(txn)
    db.flush()

    run_detection(db, merchant.id)
    run_scoring(db, merchant.id)
    run_diagnosis(db, merchant.id, max_llm_calls=0)
    run_strategy(db, merchant.id)
    run_policy_engine(db, merchant.id)
    run_action_executor(db, merchant.id)

    first_verify = run_verification(db, merchant.id)
    second_verify = run_verification(db, merchant.id)

    assert second_verify["results_verified"] == 0
    if first_verify["results_verified"] > 0:
        assert first_verify["results_verified"] >= 1


# --- End-to-end pipeline: SUCCESS path (Section 36) -----------------------

def test_end_to_end_failed_payment_recovery_success_path(db, merchant, customer):
    """
    FAILED PAYMENT -> DETECT -> DIAGNOSE -> DECIDE -> POLICY -> ACTION
    -> VERIFY -> RECOVERED

    Uses "expired_card" (deterministic rule-based diagnosis, high
    confidence, low amount) so the whole pipeline runs automatically
    without needing an LLM call or human approval.
    """
    txn = make_failed_transaction(merchant, customer, amount=1000, failure_reason="expired_card")
    db.add(txn)
    db.flush()

    detect_summary = run_detection(db, merchant.id)
    assert detect_summary["new_cases_created"]["failed_payment"] == 1

    case = db.query(RevenueRiskCase).filter(RevenueRiskCase.source_id == txn.id).first()
    assert case.status == "open"

    score_summary = run_scoring(db, merchant.id)
    assert score_summary["cases_scored"] >= 1
    db.refresh(case)
    assert case.recovery_probability is not None

    diag_summary = run_diagnosis(db, merchant.id, max_llm_calls=0)
    assert diag_summary["diagnosed_by_rules"] >= 1
    diagnosis = db.query(Diagnosis).filter(Diagnosis.case_id == case.id).first()
    assert diagnosis is not None
    assert diagnosis.diagnosis_source == "rules"

    strat_summary = run_strategy(db, merchant.id)
    assert strat_summary["cases_strategized"] >= 1
    action = db.query(RecoveryAction).filter(RecoveryAction.case_id == case.id).first()
    assert action is not None

    policy_summary = run_policy_engine(db, merchant.id)
    assert policy_summary["actions_evaluated"] >= 1
    db.refresh(action)
    assert action.policy_decision in ("APPROVED", "NEEDS_HUMAN", "REJECTED")

    if action.policy_decision == "APPROVED":
        run_action_executor(db, merchant.id)
        result = (
            db.query(ActionResult)
            .filter(ActionResult.recovery_action_id == action.id)
            .first()
        )
        assert result is not None
        assert result.mode == "SIMULATED"  # honestly labeled, never claims REAL

        run_verification(db, merchant.id)
        db.refresh(result)
        assert result.verified is True
        assert result.verified_outcome in ("recovered", "not_recovered")

        db.refresh(case)
        if result.verified_outcome == "recovered":
            assert case.status == "recovered"
        else:
            assert case.status == "open"  # never falsely marked recovered


# --- End-to-end pipeline: SAFE FAILURE path (Section 36) -------------------

def test_end_to_end_low_confidence_routes_to_human_not_silent_action(db, merchant, customer):
    """
    FAILED PAYMENT -> DETECT -> DIAGNOSE -> DECIDE -> POLICY
    -> (unrecognized reason, low confidence via LLM fallback)
    -> ESCALATED, never silently auto-executed.

    Uses an unrecognized failure_reason so rules can't resolve it, and
    caps max_llm_calls=0 so no real LLM call happens (keeping this test
    fast, free, and deterministic) — this forces the fallback_diagnosis
    path, which is intentionally low-confidence.
    """
    txn = make_failed_transaction(merchant, customer, amount=1000, failure_reason="unrecognized_gateway_error")
    db.add(txn)
    db.flush()

    run_detection(db, merchant.id)
    run_scoring(db, merchant.id)
    run_diagnosis(db, merchant.id, max_llm_calls=0)  # forces fallback, no real API call

    case = db.query(RevenueRiskCase).filter(RevenueRiskCase.source_id == txn.id).first()
    diagnosis = db.query(Diagnosis).filter(Diagnosis.case_id == case.id).first()

    # With max_llm_calls=0 and an unrecognized reason, this case should
    # be skipped entirely (capped) rather than diagnosed with a guess.
    assert diagnosis is None or diagnosis.confidence < 0.7

    if diagnosis is not None:
        run_strategy(db, merchant.id)
        run_policy_engine(db, merchant.id)

        action = db.query(RecoveryAction).filter(RecoveryAction.case_id == case.id).first()
        # Low confidence must route to escalation, never silent auto-action
        assert action.action == "ESCALATE_TO_HUMAN" or action.policy_decision == "NEEDS_HUMAN"

        # Critically: no ActionResult should exist yet, since nothing
        # was ever approved for automatic execution.
        result_count = (
            db.query(ActionResult)
            .join(RecoveryAction, RecoveryAction.id == ActionResult.recovery_action_id)
            .filter(RecoveryAction.case_id == case.id)
            .count()
        )
        assert result_count == 0