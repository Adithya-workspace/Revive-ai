"""
REVIVE AI — On-demand Analytics (Phase 13)

Run from the backend/ directory with the venv active:
    python -m scripts.run_analytics
"""

import json

from app.database import SessionLocal
from app.services.analytics import get_full_analytics
from app.models import Merchant


def run():
    db = SessionLocal()

    try:
        merchant = db.query(Merchant).first()

        if not merchant:
            print("❌ No merchant found.")
            return

        print(f"Analytics for merchant: {merchant.name} ({merchant.id})\n")

        summary = get_full_analytics(db, merchant.id)

        print(json.dumps(summary, indent=2))

    finally:
        db.close()


if __name__ == "__main__":
    run()