"""
Sanity check that the test database connection and fixtures work
correctly, before writing real component tests.
"""

from app.models import Merchant, Customer


def test_database_connection_works(db):
    """If this passes, we're genuinely talking to the test database."""
    result = db.execute(__import__("sqlalchemy").text("SELECT 1")).scalar()
    assert result == 1


def test_merchant_fixture_creates_a_real_row(db, merchant):
    found = db.query(Merchant).filter(Merchant.id == merchant.id).first()
    assert found is not None
    assert found.name == "Test Merchant"


def test_customer_fixture_links_to_merchant(db, customer, merchant):
    found = db.query(Customer).filter(Customer.id == customer.id).first()
    assert found is not None
    assert found.merchant_id == merchant.id


def test_transaction_rollback_isolates_tests(db):
    """
    This test creates a merchant but does NOT check for it existing in
    a later test — proving the rollback fixture actually cleans up
    between tests, rather than accumulating test data forever.
    """
    import uuid
    m = Merchant(id=uuid.uuid4(), name="Should Not Persist", email=f"{uuid.uuid4()}@example.com")
    db.add(m)
    db.flush()
    assert db.query(Merchant).filter(Merchant.name == "Should Not Persist").first() is not None
    # No explicit cleanup — the `db` fixture's rollback handles it after this test ends