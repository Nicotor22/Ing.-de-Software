from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Exposicion
from ..schemas import (
    ExposicionCreadaOut, ExposicionIn, ExposicionOut, ValidacionExposicionOut,
)
from ..services import exposiciones as servicio

router = APIRouter(prefix="/exposiciones", tags=["CU-08 - Exposiciones"])


@router.post("/validar", response_model=ValidacionExposicionOut)
def validar_exposicion(datos: ExposicionIn, db: Session = Depends(get_db)):
    return servicio.validar_exposicion(db, datos)


@router.post("", response_model=ExposicionCreadaOut, status_code=201)
def crear_exposicion(datos: ExposicionIn, db: Session = Depends(get_db)):
    exposicion, excluidas, advertencias = servicio.crear_exposicion(db, datos)
    return {
        "exposicion": servicio.a_dto(exposicion),
        "excluidas": excluidas,
        "advertencias": advertencias,
    }


@router.get("", response_model=list[ExposicionOut])
def listar_exposiciones(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    consulta = select(Exposicion).order_by(Exposicion.fecha_inicio.desc()).limit(limit)
    return [servicio.a_dto(e) for e in db.scalars(consulta).all()]


@router.get("/{exposicion_id}", response_model=ExposicionOut)
def obtener_exposicion(exposicion_id: int, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.obtener_exposicion(db, exposicion_id))