from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
result = db.execute(text(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name='revenue_risk_cases' AND column_name='last_scored_at'"
))
print('Column exists:', result.fetchone() is not None)
db.close()