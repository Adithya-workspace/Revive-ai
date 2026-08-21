import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)

    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, nullable=False, default="INR")

    due_date = Column(Date, nullable=False)

    # e.g. "pending", "paid", "overdue"
    status = Column(String, nullable=False, default="pending")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))