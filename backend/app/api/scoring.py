"""
REVIVE AI — Scoring API routes (Phase 6)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.scoring import run_scoring
from app.models import Merchant

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.post("/run/{merchant_id}")
def run_score(merchant_id: str, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    summary = run_scoring(db, merchant.id)
    return summary