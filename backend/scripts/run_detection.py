"""
REVIVE AI — On-demand Revenue Scan (Phase 5)

Run from the backend/ directory with the venv active:
    python -m scripts.run_detection
"""

import json

from app.database import SessionLocal
from app.detection.rules import run_detection
from app.models import Merchant


def run():
    print("Step 1: Opening database session...", flush=True)
    db = SessionLocal()

    try:
        print("Step 2: Querying for merchant...", flush=True)
        merchant = db.query(Merchant).first()

        if not merchant:
            print("❌ No merchant found. Run the synthetic data generator first:")
            print("   python -m scripts.generate_synthetic_data")
            return

        print(f"Step 3: Found merchant: {merchant.name} ({merchant.id})", flush=True)
        print("Step 4: Calling run_detection()...", flush=True)

        summary = run_detection(db, merchant.id)

        print("Step 5: run_detection() completed.", flush=True)
        print(json.dumps(summary, indent=2))

    finally:
        db.close()


if __name__ == "__main__":
    run()