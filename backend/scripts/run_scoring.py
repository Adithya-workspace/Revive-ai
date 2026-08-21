"""
REVIVE AI — On-demand Recovery Scoring (Phase 6)

Run from the backend/ directory with the venv active:
    python -m scripts.run_scoring
"""

import json

from app.database import SessionLocal
from app.services.scoring import run_scoring
from app.models import Merchant


def run():
    db = SessionLocal()

    try:
        merchant = db.query(Merchant).first()

        if not merchant:
            print("❌ No merchant found. Run the synthetic data generator first.")
            return

        print(f"Running recovery scoring for merchant: {merchant.name} ({merchant.id})\n")

        summary = run_scoring(db, merchant.id)

        print(json.dumps(summary, indent=2))

    finally:
        db.close()


if __name__ == "__main__":
    run()
    