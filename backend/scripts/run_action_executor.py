"""
REVIVE AI — On-demand Action Execution (Phase 10)

Run from the backend/ directory with the venv active:
    python -m scripts.run_action_executor
"""

import json

from app.database import SessionLocal
from app.actions.executor import run_action_executor
from app.models import Merchant


def run():
    db = SessionLocal()

    try:
        merchant = db.query(Merchant).first()

        if not merchant:
            print("❌ No merchant found.")
            return

        print(f"Running action executor for merchant: {merchant.name} ({merchant.id})\n")

        summary = run_action_executor(db, merchant.id)

        print("\n" + json.dumps(summary, indent=2))

    finally:
        db.close()


if __name__ == "__main__":
    run()