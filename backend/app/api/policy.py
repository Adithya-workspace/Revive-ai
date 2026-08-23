from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.policies.engine import run_policy_engine
from app.models import Merchant

router = APIRouter(prefix="/policy", tags=["policy"])


@router.post("/run/{merchant_id}")
def run_policy(merchant_id: str, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    return run_policy_engine(db, merchant.id)