from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.verification import run_verification
from app.models import Merchant

router = APIRouter(prefix="/verification", tags=["verification"])


@router.post("/run/{merchant_id}")
def run_verify(merchant_id: str, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    return run_verification(db, merchant.id)