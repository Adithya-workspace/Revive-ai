import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("revenue_risk_cases.id"), nullable=False)

    diagnosis = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)

    # List of short strings explaining what evidence supports this diagnosis
    evidence = Column(JSONB, nullable=False, default=list)

    recommended_next_step = Column(String, nullable=True)
    reasoning_summary = Column(Text, nullable=True)

    # "rules" | "llm" — never falsely label an LLM diagnosis as rules, or vice versa
    diagnosis_source = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))