"""
REVIVE AI — Deterministic Diagnosis Rules (Phase 7)

Handles the clear-cut diagnosis cases with no LLM involvement, per
Section 8 of the spec. Returns None when a case is genuinely ambiguous
and should be escalated to LLM reasoning instead.
"""

from datetime import date


# Known failure reasons and their deterministic diagnoses.
# Confidence reflects how directly the reason explains the failure.
FAILED_PAYMENT_DIAGNOSES = {
    "insufficient_funds": {
        "diagnosis": "Insufficient funds at time of charge",
        "confidence": 0.92,
        "recommended_next_step": "DELAYED_RETRY",
    },
    "expired_card": {
        "diagnosis": "Card expired",
        "confidence": 0.95,
        "recommended_next_step": "SEND_PAYMENT_REMINDER",
    },
    "card_declined": {
        "diagnosis": "Card declined by issuing bank",
        "confidence": 0.85,
        "recommended_next_step": "SEND_PAYMENT_REMINDER",
    },
    "network_error": {
        "diagnosis": "Transient network or gateway error",
        "confidence": 0.75,
        "recommended_next_step": "RETRY_PAYMENT",
    },
    "bank_timeout": {
        "diagnosis": "Bank gateway timeout",
        "confidence": 0.75,
        "recommended_next_step": "RETRY_PAYMENT",
    },
}


def diagnose_failed_payment_by_rules(failure_reason: str | None) -> dict | None:
    """
    Returns a deterministic diagnosis if the failure_reason is a known,
    directly-explainable cause. Returns None if the reason is missing or
    unrecognized, signaling that LLM reasoning should be used instead.
    """
    if failure_reason is None:
        return None

    template = FAILED_PAYMENT_DIAGNOSES.get(failure_reason)
    if template is None:
        return None

    return {
        "diagnosis": template["diagnosis"],
        "confidence": template["confidence"],
        "evidence": [f"transaction.failure_reason = '{failure_reason}'"],
        "recommended_next_step": template["recommended_next_step"],
        "reasoning_summary": (
            f"Directly mapped from the recorded failure reason '{failure_reason}'."
        ),
        "diagnosis_source": "rules",
    }


def diagnose_overdue_receivable_by_rules(due_date: date, today: date | None = None) -> dict | None:
    """
    Buckets overdue invoices by days overdue. Early/moderate overdue
    cases are diagnosed deterministically. Chronic (very long overdue)
    cases return None, since they warrant LLM reasoning over the
    customer's broader payment history rather than a generic bucket.
    """
    if today is None:
        today = date.today()

    days_overdue = (today - due_date).days

    if days_overdue <= 15:
        return {
            "diagnosis": "Early overdue — likely administrative delay",
            "confidence": 0.80,
            "evidence": [f"invoice is {days_overdue} days overdue"],
            "recommended_next_step": "SEND_OVERDUE_REMINDER",
            "reasoning_summary": (
                f"Invoice is only {days_overdue} days past due — most early-overdue "
                "invoices resolve without escalation."
            ),
            "diagnosis_source": "rules",
        }
    elif days_overdue <= 45:
        return {
            "diagnosis": "Moderate overdue — possible cash flow constraint",
            "confidence": 0.65,
            "evidence": [f"invoice is {days_overdue} days overdue"],
            "recommended_next_step": "TRACK_PROMISE_TO_PAY",
            "reasoning_summary": (
                f"Invoice is {days_overdue} days overdue, past the typical early-delay "
                "window, suggesting a genuine cash flow issue rather than an oversight."
            ),
            "diagnosis_source": "rules",
        }
    else:
        # Chronic overdue — ambiguous enough to warrant LLM reasoning
        # over the customer's full payment history.
        return None