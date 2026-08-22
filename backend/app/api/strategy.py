from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.strategy import run_strategy
from app.models import Merchant

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.post("/run/{merchant_id}")
def run_strat(merchant_id: str, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    return run_strategy(db, merchant.id)