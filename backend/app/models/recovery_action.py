import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("revenue_risk_cases.id"), nullable=False)

    action = Column(String, nullable=False)  # one of ALLOWED_ACTIONS
    reason = Column(Text, nullable=False)
    expected_value = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)

    # "rules" — this stage never calls an LLM directly; it applies
    # deterministic override logic on top of the diagnosis's suggestion
    strategy_source = Column(String, nullable=False, default="rules")

    # Filled in by the Policy Engine in Phase 9 — nullable for now
    policy_decision = Column(String, nullable=True)
    policy_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))