"""
REVIVE AI — Recovery Strategy Agent (Phase 8)

Takes each case's existing diagnosis and recovery score, and applies
deterministic business-override rules (Section 10) to arrive at a final
recommended action from the fixed ALLOWED_ACTIONS registry. This stage
makes NO LLM calls — it only re-evaluates the diagnosis's suggestion
against business guardrails (confidence, recovery probability, amount).

Idempotent — only strategizes cases that don't already have a
RecoveryAction. Batch-loads all needed data upfront and commits
incrementally, avoiding the N+1 query and idle-connection issues hit
in earlier phases.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import RevenueRiskCase, Diagnosis, RecoveryAction
from app.constants import ALLOWED_ACTIONS

COMMIT_EVERY_N = 100

# Business override thresholds — transparent, tunable constants
LOW_CONFIDENCE_THRESHOLD = 0.50
LOW_RECOVERY_PROBABILITY_THRESHOLD = 0.15
HIGH_VALUE_ESCALATION_THRESHOLD = 50000


def _load_already_strategized_case_ids(db: Session, merchant_id: uuid.UUID) -> set[uuid.UUID]:
    existing = (
        db.query(RecoveryAction.case_id)
        .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
        .filter(RevenueRiskCase.merchant_id == merchant_id)
        .all()
    )
    return {case_id for (case_id,) in existing}


def _load_latest_diagnoses(db: Session, merchant_id: uuid.UUID) -> dict[uuid.UUID, Diagnosis]:
    """
    One query: loads every diagnosis for this merchant's cases, keeping
    only the most recent one per case_id (in case a case was ever
    re-diagnosed).
    """
    all_diagnoses = (
        db.query(Diagnosis)
        .join(RevenueRiskCase, RevenueRiskCase.id == Diagnosis.case_id)
        .filter(RevenueRiskCase.merchant_id == merchant_id)
        .order_by(Diagnosis.created_at.asc())
        .all()
    )
    # Later entries overwrite earlier ones, leaving the latest per case_id
    latest_by_case = {}
    for d in all_diagnoses:
        latest_by_case[d.case_id] = d
    return latest_by_case


def determine_strategy(case: RevenueRiskCase, diagnosis: Diagnosis) -> dict:
    """
    Applies deterministic override rules on top of the diagnosis's
    recommended_next_step. Returns the final action decision — never
    calls the LLM, never invents an action outside ALLOWED_ACTIONS.
    """
    recovery_probability = case.recovery_probability if case.recovery_probability is not None else 0.5
    amount = float(case.amount_at_risk)
    expected_value = round(amount * recovery_probability, 2)

    proposed_action = diagnosis.recommended_next_step
    if proposed_action not in ALLOWED_ACTIONS:
        proposed_action = "ESCALATE_TO_HUMAN"  # safety net for any stale/invalid value

    # --- Override rules, applied in priority order ---

    if diagnosis.confidence < LOW_CONFIDENCE_THRESHOLD:
        return {
            "action": "ESCALATE_TO_HUMAN",
            "reason": (
                f"Diagnosis confidence ({diagnosis.confidence:.2f}) is below the "
                f"{LOW_CONFIDENCE_THRESHOLD} threshold — routing to human review rather "
                "than acting on a low-confidence automated diagnosis."
            ),
            "expected_value": expected_value,
            "confidence": diagnosis.confidence,
        }

    if recovery_probability < LOW_RECOVERY_PROBABILITY_THRESHOLD:
        return {
            "action": "STOP_RECOVERY_ATTEMPTS",
            "reason": (
                f"Recovery probability ({recovery_probability:.2f}) is below the "
                f"{LOW_RECOVERY_PROBABILITY_THRESHOLD} threshold — further automated "
                "attempts are unlikely to be worthwhile."
            ),
            "expected_value": expected_value,
            "confidence": diagnosis.confidence,
        }

    if amount >= HIGH_VALUE_ESCALATION_THRESHOLD:
        return {
            "action": "ESCALATE_TO_HUMAN",
            "reason": (
                f"Amount at risk (₹{amount:,.2f}) meets or exceeds the high-value "
                f"escalation threshold (₹{HIGH_VALUE_ESCALATION_THRESHOLD:,.2f}) — "
                "requires human authorization regardless of diagnosis confidence."
            ),
            "expected_value": expected_value,
            "confidence": diagnosis.confidence,
        }

    # No override triggered — trust the diagnosis's suggestion
    return {
        "action": proposed_action,
        "reason": f"Following diagnosis recommendation: {diagnosis.reasoning_summary or diagnosis.diagnosis}",
        "expected_value": expected_value,
        "confidence": diagnosis.confidence,
    }


def run_strategy(db: Session, merchant_id: uuid.UUID) -> dict:
    already_strategized = _load_already_strategized_case_ids(db, merchant_id)

    open_cases = (
        db.query(RevenueRiskCase)
        .filter(
            RevenueRiskCase.merchant_id == merchant_id,
            RevenueRiskCase.status == "open",
        )
        .all()
    )

    cases_to_process = [c for c in open_cases if c.id not in already_strategized]

    print(f"{len(cases_to_process)} cases need strategy "
          f"({len(open_cases) - len(cases_to_process)} already strategized).", flush=True)

    print("Loading latest diagnoses...", flush=True)
    diagnoses_by_case = _load_latest_diagnoses(db, merchant_id)
    print(f"Loaded diagnoses for {len(diagnoses_by_case)} cases.\n", flush=True)

    total_new = 0
    uncommitted = 0
    skipped_no_diagnosis = 0
    action_counts: dict[str, int] = {}

    total = len(cases_to_process)
    for i, case in enumerate(cases_to_process, 1):
        if i % 500 == 0:
            print(f"Progress: {i}/{total} cases processed...", flush=True)

        diagnosis = diagnoses_by_case.get(case.id)
        if diagnosis is None:
            # Case hasn't been diagnosed yet (Phase 7 backlog) — skip for
            # now, it'll be picked up once diagnosis runs for it.
            skipped_no_diagnosis += 1
            continue

        decision = determine_strategy(case, diagnosis)

        action_row = RecoveryAction(
            id=uuid.uuid4(),
            case_id=case.id,
            action=decision["action"],
            reason=decision["reason"],
            expected_value=decision["expected_value"],
            confidence=decision["confidence"],
            strategy_source="rules",
        )
        db.add(action_row)
        total_new += 1
        uncommitted += 1

        action_counts[decision["action"]] = action_counts.get(decision["action"], 0) + 1

        if uncommitted >= COMMIT_EVERY_N:
            db.commit()
            print(f"  (committed {total_new} so far)", flush=True)
            uncommitted = 0

    db.commit()

    total_expected_value = (
        db.query(RecoveryAction)
        .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
        .filter(RevenueRiskCase.merchant_id == merchant_id)
        .all()
    )
    sum_expected_value = round(sum(r.expected_value for r in total_expected_value), 2)

    return {
        "strategy_completed_at": datetime.now(timezone.utc).isoformat(),
        "merchant_id": str(merchant_id),
        "cases_strategized": total_new,
        "skipped_no_diagnosis_yet": skipped_no_diagnosis,
        "action_breakdown": action_counts,
        "total_expected_recoverable_value": sum_expected_value,
    }