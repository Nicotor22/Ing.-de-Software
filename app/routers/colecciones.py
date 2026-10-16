from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Coleccion
from ..schemas import ColeccionIn, ColeccionOut
from ..services import colecciones as servicio

router = APIRouter(prefix="/colecciones", tags=["CU-05 - Colecciones"])


@router.post("", response_model=ColeccionOut, status_code=201)
def crear_coleccion(datos: ColeccionIn, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.crear_coleccion(db, datos))


@router.get("", response_model=list[ColeccionOut])
def listar_colecciones(
    q: str | None = Query(None, description="Texto a buscar en el nombre"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    consulta = select(Coleccion).order_by(Coleccion.nombre)
    if q:
        consulta = consulta.where(Coleccion.nombre.ilike(f"%{q}%"))
    return [servicio.a_dto(c) for c in db.scalars(consulta.limit(limit)).all()]


@router.get("/{coleccion_id}", response_model=ColeccionOut)
def obtener_coleccion(coleccion_id: int, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.obtener_coleccion(db, coleccion_id))


@router.put("/{coleccion_id}", response_model=ColeccionOut)
def actualizar_coleccion(coleccion_id: int, datos: ColeccionIn, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.actualizar_coleccion(db, coleccion_id, datos))