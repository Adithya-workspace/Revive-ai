"""
REVIVE AI — On-demand Policy Evaluation (Phase 9)

Run from the backend/ directory with the venv active:
    python -m scripts.run_policy_engine
"""

import json

from app.database import SessionLocal
from app.policies.engine import run_policy_engine
from app.models import Merchant


def run():
    db = SessionLocal()

    try:
        merchant = db.query(Merchant).first()

        if not merchant:
            print("❌ No merchant found.")
            return

        print(f"Running policy engine for merchant: {merchant.name} ({merchant.id})\n")

        summary = run_policy_engine(db, merchant.id)

        print("\n" + json.dumps(summary, indent=2))

    finally:
        db.close()


if __name__ == "__main__":
    run()