import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class DemoSeededRecord(Base):
    """
    Tracks every source record created by Demo Mode (create-case,
    simulate-api-failure's fallback case builder), so 'Reset Demo Data'
    can cleanly remove exactly these and nothing from the real
    synthetic dataset.
    """
    __tablename__ = "demo_seeded_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    source_type = Column(String, nullable=False)  # "transaction" | "checkout_session" | "invoice"
    source_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))