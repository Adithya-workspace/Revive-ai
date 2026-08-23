import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Float
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class RevenueRiskCase(Base):
    __tablename__ = "revenue_risk_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)

    # "failed_payment" | "checkout_abandonment" | "overdue_receivable"
    scenario = Column(String, nullable=False)

    # Polymorphic link back to the originating record.
    # source_type: "transaction" | "checkout_session" | "invoice"
    # source_id: the matching row's id in that table (validated in application code,
    # not enforced by a DB foreign key — see docs/LIMITATIONS.md)
    source_type = Column(String, nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=False)

    amount_at_risk = Column(Numeric(10, 2), nullable=False)

    # "low" | "medium" | "high"
    priority = Column(String, nullable=False, default="medium")

    recovery_probability = Column(Float, nullable=True)

    # "open" | "recovered" | "escalated" | "stopped"
    status = Column(String, nullable=False, default="open")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_scored_at = Column(DateTime(timezone=True), nullable=True)