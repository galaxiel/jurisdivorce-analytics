"""Endpoint du simulateur « Mon Cas » / La Boussole (Module 2 du cahier des charges)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import BoussoleReport, BoussoleRequest
from ..services.predictor import compute_report

router = APIRouter(prefix="/api/boussole", tags=["boussole"])


@router.post("", response_model=BoussoleReport)
def boussole(req: BoussoleRequest, db: Session = Depends(get_db)):
    return compute_report(db, req)
