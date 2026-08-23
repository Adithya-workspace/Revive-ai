from app.database import SessionLocal
from app.models import Merchant, RevenueRiskCase, Diagnosis, RecoveryAction, ActionResult, AuditEvent

db = SessionLocal()

print("Merchants:", db.query(Merchant).count())
print("RevenueRiskCases:", db.query(RevenueRiskCase).count())
print("  - open:", db.query(RevenueRiskCase).filter(RevenueRiskCase.status == "open").count())
print("  - recovered:", db.query(RevenueRiskCase).filter(RevenueRiskCase.status == "recovered").count())
print("Diagnoses:", db.query(Diagnosis).count())
print("RecoveryActions:", db.query(RecoveryAction).count())
print("ActionResults:", db.query(ActionResult).count())
print("AuditEvents:", db.query(AuditEvent).count())

db.close()