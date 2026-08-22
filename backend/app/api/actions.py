from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.actions.executor import run_action_executor
from app.models import Merchant

router = APIRouter(prefix="/actions", tags=["actions"])


@router.post("/run/{merchant_id}")
def run_actions(merchant_id: str, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    return run_action_executor(db, merchant.id)