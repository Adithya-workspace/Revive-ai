from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.analytics import get_full_analytics
from app.models import Merchant

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/{merchant_id}")
def get_analytics(merchant_id: str, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    return get_full_analytics(db, merchant.id)