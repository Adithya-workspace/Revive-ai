"""
REVIVE AI — Shared Constants

Single source of truth for the allowed action registry (Section 10).
No component — not diagnosis, not strategy, not the LLM — may invent
an action outside this list.
"""

ALLOWED_ACTIONS = {
    "RETRY_PAYMENT",
    "DELAYED_RETRY",
    "SEND_PAYMENT_REMINDER",
    "SEND_CHECKOUT_RECOVERY_MESSAGE",
    "SEND_OVERDUE_REMINDER",
    "TRACK_PROMISE_TO_PAY",
    "ESCALATE_TO_HUMAN",
    "STOP_RECOVERY_ATTEMPTS",
}