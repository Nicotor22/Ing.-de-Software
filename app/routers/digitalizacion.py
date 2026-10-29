from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import DigitalizacionIn, ObraOut
from ..services import digitalizacion as servicio
from ..services import obras as servicio_obras

router = APIRouter(prefix="/obras", tags=["CU-12 - Digitalización"])


@router.post("/{obra_id}/digitalizacion/validar")
def validar_digitalizacion(obra_id: int, datos: DigitalizacionIn, db: Session = Depends(get_db)):
    return servicio.validar_digitalizacion(db, obra_id, datos)


@router.post("/{obra_id}/digitalizacion", response_model=ObraOut)
def digitalizar_obra(obra_id: int, datos: DigitalizacionIn, db: Session = Depends(get_db)):
    return servicio_obras.a_dto(servicio.digitalizar_obra(db, obra_id, datos))