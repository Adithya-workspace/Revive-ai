"""
REVIVE AI — Audit Trail Backfill (Phase 12)

Reconstructs audit_events for everything already produced by Phases
5-11, since those phases ran before this table existed. Going forward,
each service (detection, diagnosis, strategy, policy, actions,
verification) should also write its own events live — this script
covers the historical gap.

Idempotent: skips any case that already has audit events, so re-running
after adding new cases only backfills the new ones.

Run from the backend/ directory with the venv active:
    python -m scripts.backfill_audit_trail
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Merchant,
    RevenueRiskCase,
    Diagnosis,
    RecoveryAction,
    ActionResult,
    AuditEvent,
)

COMMIT_EVERY_N = 200


def _load_already_audited_case_ids(db: Session, merchant_id: uuid.UUID) -> set[uuid.UUID]:
    audited = (
        db.query(AuditEvent.case_id)
        .join(RevenueRiskCase, RevenueRiskCase.id == AuditEvent.case_id)
        .filter(RevenueRiskCase.merchant_id == merchant_id)
        .distinct()
        .all()
    )
    return {case_id for (case_id,) in audited}


def build_events_for_case(
    case: RevenueRiskCase,
    diagnosis: Diagnosis | None,
    action: RecoveryAction | None,
    result: ActionResult | None,
) -> list[AuditEvent]:
    """
    Reconstructs the ordered event trail for a single case from whatever
    data exists for it. A case might only have gotten as far as detection
    (no diagnosis yet), and that's reflected honestly — we never invent
    an event for a stage the case hasn't actually reached.
    """
    events = []

    events.append(AuditEvent(
        id=uuid.uuid4(),
        case_id=case.id,
        event_type="CASE_DETECTED",
        actor="system:detection",
        result=f"scenario={case.scenario}, priority={case.priority}",
        event_metadata={
            "amount_at_risk": float(case.amount_at_risk),
            "source_type": case.source_type,
        },
        created_at=case.created_at,
    ))

    if case.recovery_probability is not None:
        if case.last_scored_at is not None:
            score_timestamp = case.last_scored_at
            timestamp_note = "actual scoring timestamp"
        else:
            score_timestamp = case.created_at
            timestamp_note = "approximate — real scoring timestamp not captured historically"

        events.append(AuditEvent(
            id=uuid.uuid4(),
            case_id=case.id,
            event_type="RECOVERY_SCORE_CALCULATED",
            actor="system:scoring",
            result=f"recovery_probability={case.recovery_probability}",
            event_metadata={"score_source": "rules", "timestamp_note": timestamp_note},
            created_at=score_timestamp,
        ))

    if diagnosis is not None:
        events.append(AuditEvent(
            id=uuid.uuid4(),
            case_id=case.id,
            event_type="DIAGNOSIS_COMPLETED",
            actor=f"system:diagnosis_{diagnosis.diagnosis_source}",
            result=diagnosis.diagnosis,
            event_metadata={
                "confidence": diagnosis.confidence,
                "evidence": diagnosis.evidence,
                "recommended_next_step": diagnosis.recommended_next_step,
                "diagnosis_source": diagnosis.diagnosis_source,
            },
            created_at=diagnosis.created_at,
        ))

    if action is not None:
        events.append(AuditEvent(
            id=uuid.uuid4(),
            case_id=case.id,
            event_type="STRATEGY_SELECTED",
            actor="system:strategy",
            result=action.action,
            event_metadata={
                "reason": action.reason,
                "expected_value": action.expected_value,
                "confidence": action.confidence,
            },
            created_at=action.created_at,
        ))

        if action.policy_decision is not None:
            events.append(AuditEvent(
                id=uuid.uuid4(),
                case_id=case.id,
                event_type="POLICY_DECISION",
                actor="system:policy_engine",
                result=action.policy_decision,
                event_metadata={"policy_reason": action.policy_reason},
                created_at=action.created_at,
            ))

    if result is not None:
        events.append(AuditEvent(
            id=uuid.uuid4(),
            case_id=case.id,
            event_type="ACTION_EXECUTED",
            actor="system:action_executor",
            result=result.status,
            event_metadata={
                "mode": result.mode,
                "result_detail": result.result_detail,
            },
            created_at=result.executed_at,
        ))

        if result.verified:
            events.append(AuditEvent(
                id=uuid.uuid4(),
                case_id=case.id,
                event_type="VERIFICATION_COMPLETED",
                actor="system:verification",
                result=result.verified_outcome,
                event_metadata={"verification_detail": result.verification_detail},
                created_at=result.verified_at,
            ))

    if case.status == "recovered":
        events.append(AuditEvent(
            id=uuid.uuid4(),
            case_id=case.id,
            event_type="CASE_RECOVERED",
            actor="system:verification",
            result="recovered",
            event_metadata={"amount_at_risk": float(case.amount_at_risk)},
            created_at=result.verified_at if result else case.updated_at,
        ))

    return events


def run():
    db = SessionLocal()

    try:
        merchant = db.query(Merchant).first()
        if not merchant:
            print("❌ No merchant found.")
            return

        print(f"Backfilling audit trail for merchant: {merchant.name} ({merchant.id})\n", flush=True)

        already_audited = _load_already_audited_case_ids(db, merchant.id)

        print("Preloading cases, diagnoses, actions, results...", flush=True)
        all_cases = db.query(RevenueRiskCase).filter(RevenueRiskCase.merchant_id == merchant.id).all()
        cases_to_process = [c for c in all_cases if c.id not in already_audited]

        diagnoses_by_case = {
            d.case_id: d for d in db.query(Diagnosis)
            .join(RevenueRiskCase, RevenueRiskCase.id == Diagnosis.case_id)
            .filter(RevenueRiskCase.merchant_id == merchant.id)
            .order_by(Diagnosis.created_at.asc())
            .all()
        }
        actions_by_case = {
            a.case_id: a for a in db.query(RecoveryAction)
            .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
            .filter(RevenueRiskCase.merchant_id == merchant.id)
            .all()
        }
        results_by_action_id = {
            r.recovery_action_id: r for r in db.query(ActionResult)
            .join(RecoveryAction, RecoveryAction.id == ActionResult.recovery_action_id)
            .join(RevenueRiskCase, RevenueRiskCase.id == RecoveryAction.case_id)
            .filter(RevenueRiskCase.merchant_id == merchant.id)
            .all()
        }
        print(f"{len(cases_to_process)} cases need audit backfill "
              f"({len(all_cases) - len(cases_to_process)} already audited).\n", flush=True)

        total_events = 0
        uncommitted = 0

        for i, case in enumerate(cases_to_process, 1):
            if i % 500 == 0:
                print(f"Progress: {i}/{len(cases_to_process)}...", flush=True)

            diagnosis = diagnoses_by_case.get(case.id)
            action = actions_by_case.get(case.id)
            result = results_by_action_id.get(action.id) if action else None

            events = build_events_for_case(case, diagnosis, action, result)
            for event in events:
                db.add(event)
            total_events += len(events)
            uncommitted += len(events)

            if uncommitted >= COMMIT_EVERY_N:
                db.commit()
                print(f"  (committed {total_events} events so far)", flush=True)
                uncommitted = 0

        db.commit()

        print(f"\nBackfill complete: {total_events} audit events created "
              f"across {len(cases_to_process)} cases.")

    finally:
        db.close()


if __name__ == "__main__":
    run()