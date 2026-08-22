import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ActionResult(Base):
    __tablename__ = "action_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recovery_action_id = Column(UUID(as_uuid=True), ForeignKey("recovery_actions.id"), unique=True, nullable=False)

    # "REAL" | "TEST" | "SIMULATED" — never claim more reality than actually happened
    mode = Column(String, nullable=False, default="SIMULATED")

    # "success" | "failed" | "pending" — "pending" means awaiting verification (Phase 11)
    status = Column(String, nullable=False)

    result_detail = Column(Text, nullable=True)

    executed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))