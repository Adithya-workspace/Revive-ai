import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("revenue_risk_cases.id"), nullable=False)

    event_type = Column(String, nullable=False)  # e.g. "CASE_DETECTED", "DIAGNOSIS_COMPLETED"
    actor = Column(String, nullable=False)  # "system:detection" | "system:diagnosis_llm" | "system:policy_engine" etc.
    result = Column(String, nullable=True)  # short outcome summary
    event_metadata = Column(JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))