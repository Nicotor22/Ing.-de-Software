from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import MovimientoIn, MovimientoOut
from ..services import movimientos as servicio

router = APIRouter(prefix="/movimientos", tags=["CU-04 - Movimientos"])


@router.post("", response_model=MovimientoOut, status_code=201)
def registrar_movimiento(datos: MovimientoIn, db: Session = Depends(get_db)):
    return servicio.registrar_movimiento(db, datos)


@router.get("", response_model=list[MovimientoOut])
def historial(id_obra: int | None = None, db: Session = Depends(get_db)):
    return servicio.historial(db, id_obra)