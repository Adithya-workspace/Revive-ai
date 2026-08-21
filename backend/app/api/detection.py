"""
REVIVE AI — Detection API routes (Phase 5)

Exposes the detection layer as an on-demand HTTP endpoint, ready for
the frontend's future "Run Revenue Scan" button (Section 37).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.detection.rules import run_detection
from app.models import Merchant

router = APIRouter(prefix="/detection", tags=["detection"])


@router.post("/run-scan/{merchant_id}")
def run_scan(merchant_id: str, db: Session = Depends(get_db)):
    """
    Triggers an on-demand revenue risk scan for a given merchant.
    Returns a summary of newly-created cases.
    """
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    summary = run_detection(db, merchant.id)
    return summary