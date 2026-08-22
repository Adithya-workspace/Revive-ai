"""
REVIVE AI — Diagnosis API routes (Phase 7)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.diagnosis import run_diagnosis
from app.models import Merchant

router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])


@router.post("/run/{merchant_id}")
def run_diag(
    merchant_id: str,
    max_llm_calls: int = Query(default=50, ge=0, le=500),
    db: Session = Depends(get_db),
):
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    summary = run_diagnosis(db, merchant.id, max_llm_calls=max_llm_calls)
    return summary