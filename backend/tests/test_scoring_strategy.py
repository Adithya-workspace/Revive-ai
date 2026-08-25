"""
Tests for Recovery Scoring (Phase 6) and Strategy (Phase 8).
"""

import uuid
from datetime import datetime, timezone, timedelta
from app.models import RevenueRiskCase, Transaction, Diagnosis
from app.services.scoring import score_case, SCENARIO_BASELINE, MIN_SCORE, MAX_SCORE
from app.services.strategy import (
    determine_strategy,
    LOW_CONFIDENCE_THRESHOLD,
    LOW_RECOVERY_PROBABILITY_THRESHOLD,
    HIGH_VALUE_ESCALATION_THRESHOLD,
)


# --- Scoring tests -------------------------------------------------------

def make_case(merchant, customer, amount=1000, scenario="failed_payment", created_at=None):
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
        created_at=created_at or datetime.now(timezone.utc),
    )


def test_score_never_exceeds_bounds(db, merchant, customer):
    case = make_case(merchant, customer, amount=100)
    result = score_case(case, customer_success_rates={}, transaction_retry_counts={})

    assert MIN_SCORE <= result["recovery_probability"] <= MAX_SCORE


def test_score_is_labeled_as_rules_never_ml(db, merchant, customer):
    """
    Section 9 requires the score source to be honestly labeled — this
    must never say "ml" since it's a deterministic formula.
    """
    case = make_case(merchant, customer)
    result = score_case(case, customer_success_rates={}, transaction_retry_counts={})

    assert result["score_source"] == "rules"


def test_higher_customer_success_rate_increases_score(db, merchant, customer):
    case_a = make_case(merchant, customer, scenario="failed_payment")
    case_b = make_case(merchant, customer, scenario="failed_payment")

    low_success = score_case(case_a, {customer.id: 0.1}, {})
    high_success = score_case(case_b, {customer.id: 0.95}, {})

    assert high_success["recovery_probability"] > low_success["recovery_probability"]


def test_retry_count_decreases_score(db, merchant, customer):
    case = make_case(merchant, customer, scenario="failed_payment")
    txn_id = case.source_id

    no_retries = score_case(case, {}, {txn_id: 0})
    many_retries = score_case(case, {}, {txn_id: 3})

    assert many_retries["recovery_probability"] < no_retries["recovery_probability"]


def test_older_case_scores_lower_than_fresh_case(db, merchant, customer):
    fresh_case = make_case(merchant, customer, created_at=datetime.now(timezone.utc))
    old_case = make_case(
        merchant, customer, created_at=datetime.now(timezone.utc) - timedelta(days=30)
    )

    fresh_score = score_case(fresh_case, {}, {})
    old_score = score_case(old_case, {}, {})

    assert old_score["recovery_probability"] < fresh_score["recovery_probability"]


def test_high_amount_case_scores_lower_than_low_amount(db, merchant, customer):
    low_amount_case = make_case(merchant, customer, amount=1000)
    high_amount_case = make_case(merchant, customer, amount=60000)

    low_score = score_case(low_amount_case, {}, {})
    high_score = score_case(high_amount_case, {}, {})

    assert high_score["recovery_probability"] < low_score["recovery_probability"]


def test_scenario_baselines_are_ordered_as_designed():
    """
    failed_payment should have the highest baseline, overdue_receivable
    the lowest — this reflects real recovery patterns per Section 9.
    """
    assert SCENARIO_BASELINE["failed_payment"] > SCENARIO_BASELINE["checkout_abandonment"]
    assert SCENARIO_BASELINE["checkout_abandonment"] > SCENARIO_BASELINE["overdue_receivable"]


# --- Strategy tests --------------------------------------------------------

def make_diagnosis(case, confidence=0.8, next_step="RETRY_PAYMENT"):
    return Diagnosis(
        id=uuid.uuid4(),
        case_id=case.id,
        diagnosis="test diagnosis",
        confidence=confidence,
        evidence=["test evidence"],
        recommended_next_step=next_step,
        reasoning_summary="test reasoning",
        diagnosis_source="rules",
    )


def test_low_confidence_diagnosis_forces_escalation(db, merchant, customer):
    case = make_case(merchant, customer, amount=1000)
    case.recovery_probability = 0.8
    diagnosis = make_diagnosis(case, confidence=LOW_CONFIDENCE_THRESHOLD - 0.1)

    decision = determine_strategy(case, diagnosis)

    assert decision["action"] == "ESCALATE_TO_HUMAN"


def test_low_recovery_probability_forces_stop(db, merchant, customer):
    case = make_case(merchant, customer, amount=1000)
    case.recovery_probability = LOW_RECOVERY_PROBABILITY_THRESHOLD - 0.05
    diagnosis = make_diagnosis(case, confidence=0.9)

    decision = determine_strategy(case, diagnosis)

    assert decision["action"] == "STOP_RECOVERY_ATTEMPTS"


def test_high_value_forces_escalation_even_with_good_confidence(db, merchant, customer):
    case = make_case(merchant, customer, amount=HIGH_VALUE_ESCALATION_THRESHOLD + 1000)
    case.recovery_probability = 0.8
    diagnosis = make_diagnosis(case, confidence=0.95)

    decision = determine_strategy(case, diagnosis)

    assert decision["action"] == "ESCALATE_TO_HUMAN"


def test_normal_case_follows_diagnosis_recommendation(db, merchant, customer):
    case = make_case(merchant, customer, amount=1000)
    case.recovery_probability = 0.7
    diagnosis = make_diagnosis(case, confidence=0.9, next_step="SEND_PAYMENT_REMINDER")

    decision = determine_strategy(case, diagnosis)

    assert decision["action"] == "SEND_PAYMENT_REMINDER"


def test_expected_value_is_amount_times_probability(db, merchant, customer):
    case = make_case(merchant, customer, amount=1000)
    case.recovery_probability = 0.5
    diagnosis = make_diagnosis(case, confidence=0.9)

    decision = determine_strategy(case, diagnosis)

    assert decision["expected_value"] == 500.0


def test_strategy_never_invents_action_outside_registry(db, merchant, customer):
    """
    Even if a diagnosis somehow had a stale/invalid recommended_next_step,
    strategy must fall back safely rather than propagate it.
    """
    case = make_case(merchant, customer, amount=1000)
    case.recovery_probability = 0.7
    diagnosis = make_diagnosis(case, confidence=0.9, next_step="SOME_INVALID_ACTION")

    decision = determine_strategy(case, diagnosis)

    from app.constants import ALLOWED_ACTIONS
    assert decision["action"] in ALLOWED_ACTIONS