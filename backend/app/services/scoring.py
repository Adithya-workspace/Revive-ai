"""
REVIVE AI — Recovery Scoring (Phase 6)

Deterministic, fully-explainable recovery probability scoring.
Per Section 9 of the spec: this is a RULES-BASED baseline, not ML or LLM
reasoning, and every score is labeled as such.

Performance note: all data needed for scoring (customer transaction
history, source transaction retry counts) is loaded ONCE per run, into
in-memory lookups. Updated scores are written back using
psycopg2.extras.execute_values, which sends a genuine small number of
batched SQL statements instead of one UPDATE per row — this is what
makes updating thousands of cases take seconds instead of minutes.
"""

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import psycopg2.extras

from app.models import RevenueRiskCase, Transaction


# --- Baselines and weights (transparent, tunable constants) ----------------

SCENARIO_BASELINE = {
    "failed_payment": 0.65,
    "checkout_abandonment": 0.45,
    "overdue_receivable": 0.35,
}

RETRY_PENALTY_PER_ATTEMPT = 0.15
CASE_AGE_PENALTY_PER_DAY = 0.01
CASE_AGE_PENALTY_CAP = 0.20

AMOUNT_MEDIUM_THRESHOLD = 10000
AMOUNT_MEDIUM_PENALTY = 0.05
AMOUNT_HIGH_THRESHOLD = 50000
AMOUNT_HIGH_PENALTY = 0.10

MIN_SCORE = 0.05
MAX_SCORE = 0.95


def _build_customer_success_rates(db: Session, merchant_id: uuid.UUID) -> dict[uuid.UUID, float]:
    transactions = (
        db.query(Transaction.customer_id, Transaction.status)
        .filter(Transaction.merchant_id == merchant_id)
        .all()
    )

    totals = defaultdict(int)
    successes = defaultdict(int)

    for customer_id, status in transactions:
        totals[customer_id] += 1
        if status == "success":
            successes[customer_id] += 1

    return {cid: successes[cid] / totals[cid] for cid in totals}


def _build_transaction_retry_counts(db: Session, merchant_id: uuid.UUID) -> dict[uuid.UUID, int]:
    transactions = (
        db.query(Transaction.id, Transaction.retry_count)
        .filter(Transaction.merchant_id == merchant_id)
        .all()
    )
    return {txn_id: retry_count for txn_id, retry_count in transactions}


def _get_case_age_days(case: RevenueRiskCase) -> int:
    now = datetime.now(timezone.utc)
    created_at = case.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return (now - created_at).days


def score_case(
    case: RevenueRiskCase,
    customer_success_rates: dict,
    transaction_retry_counts: dict,
) -> dict:
    factors = {}

    score = SCENARIO_BASELINE.get(case.scenario, 0.5)
    factors["scenario_baseline"] = {"scenario": case.scenario, "value": score}

    success_rate = customer_success_rates.get(case.customer_id)
    if success_rate is not None:
        adjustment = (success_rate - 0.5) * 0.3
        score += adjustment
        factors["customer_success_rate"] = {
            "success_rate": round(success_rate, 3),
            "adjustment": round(adjustment, 3),
        }
    else:
        factors["customer_success_rate"] = {"success_rate": None, "adjustment": 0.0}

    retry_count = 0
    if case.scenario == "failed_payment":
        retry_count = transaction_retry_counts.get(case.source_id, 0)

    if retry_count > 0:
        adjustment = -1 * retry_count * RETRY_PENALTY_PER_ATTEMPT
        score += adjustment
        factors["retry_penalty"] = {"retry_count": retry_count, "adjustment": round(adjustment, 3)}
    else:
        factors["retry_penalty"] = {"retry_count": 0, "adjustment": 0.0}

    age_days = _get_case_age_days(case)
    age_penalty = -1 * min(age_days * CASE_AGE_PENALTY_PER_DAY, CASE_AGE_PENALTY_CAP)
    score += age_penalty
    factors["case_age"] = {"age_days": age_days, "adjustment": round(age_penalty, 3)}

    amount = float(case.amount_at_risk)
    amount_penalty = 0.0
    if amount >= AMOUNT_HIGH_THRESHOLD:
        amount_penalty = -1 * AMOUNT_HIGH_PENALTY
    elif amount >= AMOUNT_MEDIUM_THRESHOLD:
        amount_penalty = -1 * AMOUNT_MEDIUM_PENALTY
    score += amount_penalty
    factors["amount_at_risk"] = {"amount": amount, "adjustment": round(amount_penalty, 3)}

    final_score = max(MIN_SCORE, min(MAX_SCORE, score))

    return {
        "recovery_probability": round(final_score, 3),
        "score_source": "rules",
        "factors": factors,
    }


def _bulk_write_scores(db: Session, updates: list[tuple[uuid.UUID, float]]) -> None:
    """
    Writes all (case_id, recovery_probability) pairs to the database in a
    small number of batched round trips, using psycopg2's execute_values
    against a raw UPDATE ... FROM (VALUES ...) statement. Also stamps
    last_scored_at with the current time — since this bypasses the ORM,
    it needs to be set explicitly here rather than relying on any
    onupdate hook (which only fires on ORM-tracked writes).
    """
    if not updates:
        return

    now = datetime.now(timezone.utc)
    raw_conn = db.connection().connection
    cursor = raw_conn.cursor()

    query = """
        UPDATE revenue_risk_cases AS r
        SET recovery_probability = v.prob,
            last_scored_at = %(now)s
        FROM (VALUES %%s) AS v(id, prob)
        WHERE r.id = v.id
    """ % {"now": "%(now)s"}

    # execute_values doesn't support extra named params alongside VALUES
    # cleanly, so we bind `now` into each row tuple instead.
    updates_with_timestamp = [(case_id, prob, now) for case_id, prob in updates]

    query = """
        UPDATE revenue_risk_cases AS r
        SET recovery_probability = v.prob,
            last_scored_at = v.scored_at
        FROM (VALUES %s) AS v(id, prob, scored_at)
        WHERE r.id = v.id
    """

    psycopg2.extras.execute_values(
        cursor,
        query,
        updates_with_timestamp,
        template="(%s::uuid, %s::float, %s::timestamptz)",
        page_size=500,
    )

    db.commit()


def run_scoring(db: Session, merchant_id: uuid.UUID) -> dict:
    print("Loading open cases...", flush=True)
    open_cases = (
        db.query(RevenueRiskCase)
        .filter(
            RevenueRiskCase.merchant_id == merchant_id,
            RevenueRiskCase.status == "open",
        )
        .all()
    )
    print(f"Loaded {len(open_cases)} open cases.", flush=True)

    print("Building customer success rate lookup...", flush=True)
    customer_success_rates = _build_customer_success_rates(db, merchant_id)
    print(f"Built success rates for {len(customer_success_rates)} customers.", flush=True)

    print("Building transaction retry count lookup...", flush=True)
    transaction_retry_counts = _build_transaction_retry_counts(db, merchant_id)
    print(f"Built retry counts for {len(transaction_retry_counts)} transactions.", flush=True)

    print("Scoring cases (in memory, no further queries)...", flush=True)
    scored_count = 0
    probability_sum = 0.0
    updates = []

    for case in open_cases:
        result = score_case(case, customer_success_rates, transaction_retry_counts)
        updates.append((case.id, result["recovery_probability"]))
        scored_count += 1
        probability_sum += result["recovery_probability"]

    print(f"Writing {len(updates)} scores to the database (batched, single round trip class)...", flush=True)
    _bulk_write_scores(db, updates)
    print("Committed.", flush=True)

    avg_probability = (probability_sum / scored_count) if scored_count else 0.0

    return {
        "scoring_completed_at": datetime.now(timezone.utc).isoformat(),
        "merchant_id": str(merchant_id),
        "cases_scored": scored_count,
        "average_recovery_probability": round(avg_probability, 3),
        "score_source": "rules",
    }