"""
REVIVE AI — On-demand Verification (Phase 11)

Run from the backend/ directory with the venv active:
    python -m scripts.run_verification
"""

import json

from app.database import SessionLocal
from app.services.verification import run_verification
from app.models import Merchant


def run():
    db = SessionLocal()

    try:
        merchant = db.query(Merchant).first()

        if not merchant:
            print("❌ No merchant found.")
            return

        print(f"Running verification for merchant: {merchant.name} ({merchant.id})\n")

        summary = run_verification(db, merchant.id)

        print("\n" + json.dumps(summary, indent=2))

    finally:
        db.close()


if __name__ == "__main__":
    run()