from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Merchant

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.get("")
def list_merchants(db: Session = Depends(get_db)):
    merchants = db.query(Merchant).all()
    return [{"id": str(m.id), "name": m.name, "email": m.email} for m in merchants]