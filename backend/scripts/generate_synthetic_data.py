"""
REVIVE AI — Synthetic Data Generator (Phase 4)

Generates a realistic, reproducible dataset of merchants, customers,
transactions, checkout sessions, and invoices, using behavioral archetypes
so downstream detection/scoring/evaluation has meaningful correlations
to work with — not pure randomness.

Run from the backend/ directory with the venv active:
    python -m scripts.generate_synthetic_data
"""

import random
import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker

from app.database import SessionLocal, engine, Base
from app.models import Merchant, Customer, Transaction, CheckoutSession, Invoice

# --- Reproducibility -------------------------------------------------------
DATA_SEED = 42
random.seed(DATA_SEED)
fake = Faker()
Faker.seed(DATA_SEED)

# --- Scale -------------------------------------------------------------
NUM_CUSTOMERS = 870
TARGET_TRANSACTIONS = 6500
TARGET_CHECKOUT_SESSIONS = 2200
TARGET_INVOICES = 1300

# --- Archetypes --------------------------------------------------------
# Each archetype defines behavior probabilities used when generating
# that customer's events. Weights must sum to 1.0.
ARCHETYPES = {
    "reliable": 0.45,
    "occasional_failure": 0.20,
    "chronic_failure": 0.08,
    "checkout_abandoner": 0.10,
    "b2b_slow_payer": 0.10,
    "b2b_non_payer": 0.07,
}

FAILURE_REASONS = [
    "insufficient_funds",
    "card_declined",
    "network_error",
    "bank_timeout",
    "expired_card",
]

CURRENCY = "INR"


def weighted_archetype() -> str:
    return random.choices(
        population=list(ARCHETYPES.keys()),
        weights=list(ARCHETYPES.values()),
        k=1,
    )[0]


def random_past_datetime(max_days_ago: int = 180) -> datetime:
    days_ago = random.randint(0, max_days_ago)
    seconds_offset = random.randint(0, 86400)
    return datetime.now(timezone.utc) - timedelta(days=days_ago, seconds=seconds_offset)


def make_amount() -> float:
    # Skewed toward smaller amounts with occasional large ones, like real
    # transaction distributions.
    return round(random.choice([
        random.uniform(200, 2000),
        random.uniform(2000, 10000),
        random.uniform(10000, 50000),
    ]), 2)


def generate_transactions_for_customer(customer: Customer, archetype: str) -> list[Transaction]:
    transactions = []
    num_txns = random.randint(3, 15)

    for _ in range(num_txns):
        created_at = random_past_datetime()

        if archetype == "reliable":
            status = "success" if random.random() < 0.95 else "failed"
        elif archetype == "occasional_failure":
            status = "success" if random.random() < 0.75 else "failed"
        elif archetype == "chronic_failure":
            status = "success" if random.random() < 0.35 else "failed"
        else:
            # checkout_abandoner / b2b archetypes still make some direct
            # transaction attempts too, just less central to their behavior
            status = "success" if random.random() < 0.80 else "failed"

        failure_reason = random.choice(FAILURE_REASONS) if status == "failed" else None
        retry_count = random.randint(0, 2) if status == "failed" else 0

        transactions.append(Transaction(
            id=uuid.uuid4(),
            merchant_id=customer.merchant_id,
            customer_id=customer.id,
            amount=make_amount(),
            currency=CURRENCY,
            status=status,
            failure_reason=failure_reason,
            retry_count=retry_count,
            created_at=created_at,
            updated_at=created_at,
        ))

    return transactions


def generate_checkout_sessions_for_customer(customer: Customer, archetype: str) -> list[CheckoutSession]:
    sessions = []

    if archetype == "checkout_abandoner":
        num_sessions = random.randint(4, 10)
        abandon_rate = 0.75
    else:
        num_sessions = random.randint(0, 3)
        abandon_rate = 0.25

    for _ in range(num_sessions):
        started_at = random_past_datetime()
        abandoned = random.random() < abandon_rate

        if abandoned:
            status = "abandoned"
            # Abandoned sessions went quiet at some point after starting
            last_activity_at = started_at + timedelta(minutes=random.randint(1, 45))
        else:
            status = "completed"
            last_activity_at = started_at + timedelta(minutes=random.randint(1, 15))

        sessions.append(CheckoutSession(
            id=uuid.uuid4(),
            merchant_id=customer.merchant_id,
            customer_id=customer.id,
            amount=make_amount(),
            currency=CURRENCY,
            status=status,
            started_at=started_at,
            last_activity_at=last_activity_at,
        ))

    return sessions


def generate_invoices_for_customer(customer: Customer, archetype: str) -> list[Invoice]:
    invoices = []

    if archetype in ("b2b_slow_payer", "b2b_non_payer"):
        num_invoices = random.randint(2, 6)
    else:
        num_invoices = random.randint(0, 1)

    for _ in range(num_invoices):
        created_at = random_past_datetime()
        due_date = (created_at + timedelta(days=random.choice([15, 30, 45]))).date()

        if archetype == "b2b_non_payer":
            status = "overdue" if random.random() < 0.85 else "paid"
        elif archetype == "b2b_slow_payer":
            status = "paid" if random.random() < 0.70 else "overdue"
        else:
            status = "paid" if random.random() < 0.90 else "overdue"

        invoices.append(Invoice(
            id=uuid.uuid4(),
            merchant_id=customer.merchant_id,
            customer_id=customer.id,
            amount=make_amount(),
            currency=CURRENCY,
            due_date=due_date,
            status=status,
            created_at=created_at,
        ))

    return invoices


def run():
    print(f"Starting synthetic data generation (seed={DATA_SEED})...")

    # Make sure all tables exist (safety net; Alembic is the real source of truth)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # --- Reset: clear any previously generated data first ---------------
        # Delete children before parents to respect foreign key constraints.
        print("Clearing any existing synthetic data...")
        db.query(Invoice).delete()
        db.query(CheckoutSession).delete()
        db.query(Transaction).delete()
        db.query(Customer).delete()
        db.query(Merchant).delete()
        db.commit()
        print("Cleared.\n")

        
        # --- Merchant ------------------------------------------------------
        merchant = Merchant(
            id=uuid.uuid4(),
            name="Demo Retailer Pvt Ltd",
            email="ops@demoretailer.test",
        )
        db.add(merchant)
        db.flush()  # get merchant.id without committing yet
        print(f"Created merchant: {merchant.name} ({merchant.id})")

        # --- Customers -------------------------------------------------------
        customers = []
        archetype_counts = {key: 0 for key in ARCHETYPES}

        for _ in range(NUM_CUSTOMERS):
            archetype = weighted_archetype()
            archetype_counts[archetype] += 1

            customer = Customer(
                id=uuid.uuid4(),
                merchant_id=merchant.id,
                name=fake.name(),
                email=fake.email(),
                phone=fake.phone_number(),
            )
            db.add(customer)
            customers.append((customer, archetype))

        db.flush()  # get all customer.id values
        print(f"Created {len(customers)} customers.")
        print("Archetype distribution:")
        for k, v in archetype_counts.items():
            print(f"  {k}: {v}")

        # --- Transactions / Checkout Sessions / Invoices --------------------
        all_transactions = []
        all_sessions = []
        all_invoices = []

        for customer, archetype in customers:
            all_transactions.extend(generate_transactions_for_customer(customer, archetype))
            all_sessions.extend(generate_checkout_sessions_for_customer(customer, archetype))
            all_invoices.extend(generate_invoices_for_customer(customer, archetype))

        db.add_all(all_transactions)
        db.add_all(all_sessions)
        db.add_all(all_invoices)

        db.commit()

        total_events = len(all_transactions) + len(all_sessions) + len(all_invoices)

        print("\n--- Generation complete ---")
        print(f"Transactions:      {len(all_transactions)}")
        print(f"Checkout sessions: {len(all_sessions)}")
        print(f"Invoices:          {len(all_invoices)}")
        print(f"TOTAL EVENTS:      {total_events}")

        if total_events < 10000:
            print(f"\n⚠️  Total events ({total_events}) is below the 10,000 target from Section 18.")
            print("   Consider increasing NUM_CUSTOMERS or per-customer ranges.")
        else:
            print(f"\n✅ Meets the 10,000+ event requirement (Section 18).")

    except Exception as e:
        db.rollback()
        print("❌ Generation failed, rolled back all changes.")
        print(e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()