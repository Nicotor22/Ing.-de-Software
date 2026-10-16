from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Obra
from ..schemas import ObraIn, ObraOut, ObraCreateIn
from ..services import obras as servicio

router = APIRouter(prefix="/obras", tags=["CU-01 - Obras"])


@router.post("", response_model=ObraOut, status_code=201)
def crear_obra(datos: ObraCreateIn, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.crear_obra(db, datos))


@router.get("", response_model=list[ObraOut])
def listar_obras(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    obras = db.scalars(select(Obra).order_by(Obra.id).limit(limit).offset(offset)).all()
    return [servicio.a_dto(o) for o in obras]


@router.get("/{obra_id}", response_model=ObraOut)
def obtener_obra(obra_id: int, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.obtener_obra(db, obra_id))

@router.put("/{obra_id}", response_model=ObraOut)
def actualizar_obra(obra_id: int, datos: ObraIn, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.actualizar_obra(db, obra_id, datos))