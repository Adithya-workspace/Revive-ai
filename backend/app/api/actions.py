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

from pydantic import BaseModel
from app.actions.executor import simulate_api_failure


class SimulateFailureRequest(BaseModel):
    case_id: str | None = None


@router.post("/simulate-api-failure/{merchant_id}")
def simulate_failure(
    merchant_id: str,
    body: SimulateFailureRequest = SimulateFailureRequest(),
    db: Session = Depends(get_db),
):
    case_id = body.case_id if body.case_id else None
    return simulate_api_failure(db, merchant_id, case_id=case_id)