"""
Tests for the Policy / Guardrail Engine (Phase 9) — the safety boundary
between AI proposals and real actions. These tests are the most
important in the suite: if the policy engine has a bug, the whole
"AI proposes, policy disposes" guarantee breaks down.
"""

import uuid
from datetime import date
from app.models import RevenueRiskCase, RecoveryAction, Transaction, Policy
from app.policies.engine import evaluate_policy, PASSIVE_ACTIONS, RETRY_ACTIONS


def make_case(merchant, customer, amount=1000, scenario="failed_payment"):
    return RevenueRiskCase(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        customer_id=customer.id,
        scenario=scenario,
        source_type="transaction",
        source_id=uuid.uuid4(),
        amount_at_risk=amount,
        priority="low",
        status="open",
    )


def make_action(case, action="RETRY_PAYMENT", confidence=0.9):
    return RecoveryAction(
        id=uuid.uuid4(),
        case_id=case.id,
        action=action,
        reason="test reason",
        expected_value=float(case.amount_at_risk) * 0.5,
        confidence=confidence,
        strategy_source="rules",
    )


DEFAULT_POLICY_VALUES = {
    "max_automatic_retries": "2",
    "max_automatic_action_amount": "5000",
    "min_confidence_for_automatic_action": "0.60",
}


def test_passive_actions_are_always_approved(db, merchant, customer):
    case = make_case(merchant, customer)
    action = make_action(case, action="ESCALATE_TO_HUMAN", confidence=0.1)  # deliberately bad confidence

    decision, reason = evaluate_policy(action, case, retry_count=0, policy_values=DEFAULT_POLICY_VALUES)

    assert decision == "APPROVED"
    assert "passive action" in reason.lower()


def test_stop_recovery_is_always_approved(db, merchant, customer):
    case = make_case(merchant, customer, amount=999999)  # deliberately huge amount
    action = make_action(case, action="STOP_RECOVERY_ATTEMPTS", confidence=0.1)

    decision, _ = evaluate_policy(action, case, retry_count=0, policy_values=DEFAULT_POLICY_VALUES)

    assert decision == "APPROVED"


def test_retry_action_rejected_when_at_retry_cap(db, merchant, customer):
    case = make_case(merchant, customer, amount=1000)
    action = make_action(case, action="RETRY_PAYMENT", confidence=0.9)

    # retry_count == max_automatic_retries (2) should be rejected
    decision, reason = evaluate_policy(action, case, retry_count=2, policy_values=DEFAULT_POLICY_VALUES)

    assert decision == "REJECTED"
    assert "retries" in reason.lower()


def test_retry_action_approved_when_under_retry_cap(db, merchant, customer):
    case = make_case(merchant, customer, amount=1000)
    action = make_action(case, action="RETRY_PAYMENT", confidence=0.9)

    decision, _ = evaluate_policy(action, case, retry_count=1, policy_values=DEFAULT_POLICY_VALUES)

    assert decision == "APPROVED"


def test_high_amount_requires_human_even_with_high_confidence(db, merchant, customer):
    case = make_case(merchant, customer, amount=10000)  # above the 5000 ceiling
    action = make_action(case, action="SEND_PAYMENT_REMINDER", confidence=0.95)

    decision, reason = evaluate_policy(action, case, retry_count=0, policy_values=DEFAULT_POLICY_VALUES)

    assert decision == "NEEDS_HUMAN"
    assert "ceiling" in reason.lower()


def test_low_confidence_requires_human_even_with_low_amount(db, merchant, customer):
    case = make_case(merchant, customer, amount=1000)
    action = make_action(case, action="SEND_PAYMENT_REMINDER", confidence=0.3)  # below 0.60 floor

    decision, reason = evaluate_policy(action, case, retry_count=0, policy_values=DEFAULT_POLICY_VALUES)

    assert decision == "NEEDS_HUMAN"
    assert "confidence" in reason.lower()


def test_action_approved_when_all_checks_pass(db, merchant, customer):
    case = make_case(merchant, customer, amount=1000)
    action = make_action(case, action="SEND_PAYMENT_REMINDER", confidence=0.9)

    decision, reason = evaluate_policy(action, case, retry_count=0, policy_values=DEFAULT_POLICY_VALUES)

    assert decision == "APPROVED"
    assert "passes all policy checks" in reason.lower()


def test_policy_uses_live_values_not_hardcoded_constants(db, merchant, customer):
    """
    Confirms the policy engine actually reads from the policy_values
    dict it's given, rather than hardcoded numbers — this is what makes
    policies admin-configurable per Section 29.
    """
    case = make_case(merchant, customer, amount=1000)
    action = make_action(case, action="SEND_PAYMENT_REMINDER", confidence=0.9)

    # With a much stricter ceiling, the same case should now need human review
    strict_policy_values = {**DEFAULT_POLICY_VALUES, "max_automatic_action_amount": "500"}

    decision, _ = evaluate_policy(action, case, retry_count=0, policy_values=strict_policy_values)

    assert decision == "NEEDS_HUMAN"


def test_delayed_retry_is_also_subject_to_retry_cap(db, merchant, customer):
    """DELAYED_RETRY should be treated the same as RETRY_PAYMENT for the cap."""
    case = make_case(merchant, customer, amount=1000)
    action = make_action(case, action="DELAYED_RETRY", confidence=0.9)

    decision, _ = evaluate_policy(action, case, retry_count=3, policy_values=DEFAULT_POLICY_VALUES)

    assert decision == "REJECTED"


def test_passive_and_retry_action_sets_are_disjoint():
    """Sanity check on the constants themselves — no action should be in both sets."""
    assert PASSIVE_ACTIONS.isdisjoint(RETRY_ACTIONS)