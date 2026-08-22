"""
REVIVE AI — On-demand Diagnosis (Phase 7)

Run from the backend/ directory with the venv active:
    python -m scripts.run_diagnosis

Defaults to a small max_llm_calls cap to keep Groq free-tier usage
predictable while testing. Increase --limit once you're confident it
works correctly.
"""

import json
import sys

from app.database import SessionLocal
from app.services.diagnosis import run_diagnosis
from app.models import Merchant


def run():
    max_llm_calls = 50
    if len(sys.argv) > 1:
        max_llm_calls = int(sys.argv[1])

    db = SessionLocal()

    try:
        merchant = db.query(Merchant).first()

        if not merchant:
            print("❌ No merchant found. Run the synthetic data generator first.")
            return

        print(f"Running diagnosis for merchant: {merchant.name} ({merchant.id})")
        print(f"Max LLM calls this run: {max_llm_calls}\n")

        summary = run_diagnosis(db, merchant.id, max_llm_calls=max_llm_calls)

        print("\n" + json.dumps(summary, indent=2))

    finally:
        db.close()


if __name__ == "__main__":
    run()