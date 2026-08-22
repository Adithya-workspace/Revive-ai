"""
REVIVE AI — Seed Initial Policies (Phase 9)

Run from the backend/ directory with the venv active:
    python -m scripts.seed_policies

Idempotent — safe to re-run; updates existing policies rather than
duplicating them if a key already exists.
"""

from app.database import SessionLocal
from app.models import Policy

INITIAL_POLICIES = [
    {
        "key": "max_automatic_retries",
        "value": "2",
        "description": "Maximum number of automatic retry attempts allowed for a failed payment before requiring escalation.",
    },
    {
        "key": "max_automatic_action_amount",
        "value": "5000",
        "description": "Maximum amount (INR) for which an action can be taken fully automatically. Above this, human approval is required.",
    },
    {
        "key": "min_confidence_for_automatic_action",
        "value": "0.60",
        "description": "Minimum diagnosis/strategy confidence required to allow an action to proceed automatically.",
    },
]


def run():
    db = SessionLocal()
    try:
        for policy_def in INITIAL_POLICIES:
            existing = db.query(Policy).filter(Policy.key == policy_def["key"]).first()
            if existing:
                existing.value = policy_def["value"]
                existing.description = policy_def["description"]
                existing.version += 1
                print(f"Updated policy: {policy_def['key']} = {policy_def['value']} (v{existing.version})")
            else:
                new_policy = Policy(
                    key=policy_def["key"],
                    value=policy_def["value"],
                    description=policy_def["description"],
                    version=1,
                )
                db.add(new_policy)
                print(f"Created policy: {policy_def['key']} = {policy_def['value']} (v1)")

        db.commit()
        print("\nPolicies seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    run()