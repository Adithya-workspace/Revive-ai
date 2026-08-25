"""
REVIVE AI — Pytest configuration (Phase 16)

CRITICAL: this file redirects DATABASE_URL to TEST_DATABASE_URL before
any app module is imported. This ensures tests never touch the real
Neon database — they run against a completely separate `revive_test`
database instead.

Each test gets a fresh transaction that's rolled back at the end, so
tests never leak data into each other and never need manual cleanup.
"""

import os
import uuid
import pytest
from dotenv import load_dotenv

# --- Redirect to the test database BEFORE importing anything from app ---
load_dotenv()
test_db_url = os.getenv("TEST_DATABASE_URL")
if not test_db_url:
    raise RuntimeError(
        "TEST_DATABASE_URL is not set in backend/.env. "
        "Tests must run against a separate database, never the real one."
    )
os.environ["DATABASE_URL"] = test_db_url

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Merchant, Customer  # noqa: F401 — ensures all models register with Base


@pytest.fixture(scope="session")
def engine():
    """One engine for the whole test session, pointed at revive_test."""
    eng = create_engine(test_db_url)
    Base.metadata.create_all(bind=eng)  # create all tables if they don't exist yet
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    """
    Each test gets its own transaction, rolled back after the test
    finishes — so tests never see each other's data and never need
    manual cleanup between runs.
    """
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def merchant(db):
    """A fresh test merchant, available to any test that needs one."""
    m = Merchant(
        id=uuid.uuid4(),
        name="Test Merchant",
        email=f"test-{uuid.uuid4()}@example.com",  # unique per test run
    )
    db.add(m)
    db.flush()
    return m


@pytest.fixture()
def customer(db, merchant):
    """A fresh test customer belonging to the test merchant."""
    c = Customer(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        name="Test Customer",
        email="testcustomer@example.com",
        phone="9999999999",
    )
    db.add(c)
    db.flush()
    return c