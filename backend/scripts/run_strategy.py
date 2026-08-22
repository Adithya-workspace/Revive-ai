"""
REVIVE AI — On-demand Strategy Run (Phase 8)

Run from the backend/ directory with the venv active:
    python -m scripts.run_strategy
"""

import json

from app.database import SessionLocal
from app.services.strategy import run_strategy
from app.models import Merchant


def run():
    db = SessionLocal()

    try:
        merchant = db.query(Merchant).first()

        if not merchant:
            print("❌ No merchant found.")
            return

        print(f"Running strategy for merchant: {merchant.name} ({merchant.id})\n")

        summary = run_strategy(db, merchant.id)

        print("\n" + json.dumps(summary, indent=2))

    finally:
        db.close()


if __name__ == "__main__":
    run()