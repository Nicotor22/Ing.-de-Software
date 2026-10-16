from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ubicacion
from ..schemas import UbicacionIn, UbicacionOut

router = APIRouter(prefix="/Ubicaciones", tags=["Carga de datos - Ubicaciones"])

@router.post("", response_model=UbicacionOut, status_code=201)
def crear_ubicacion(
    datos: UbicacionIn,
    confirmar_duplicado: bool = False,
    db: Session = Depends(get_db),
):
    # Extensión del paso 4: el nombre ya existe -> se advierte y no se guarda
    existente = db.scalars(
        select(Ubicacion).where(func.lower(Ubicacion.nombre) == datos.nombre.lower())
    ).first()
    if existente and not confirmar_duplicado:
        raise HTTPException(
            status_code=409,
            detail={
                "mensaje": "Ya existe un autor con ese nombre",
                "ubicacion_existente": {"id": existente.id, "nombre": existente.nombre},
            },
        )

    ubicacion = Ubicacion(**datos.model_dump())
    db.add(ubicacion)
    db.commit()
    db.refresh(ubicacion)
    return ubicacion

@router.get("", response_model=list[UbicacionOut])
def listar_ubicaciones(
    q: str | None = Query(None, description="Texto a buscar en el nombre (autocompletado)"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    consulta = select(Ubicacion).order_by(Ubicacion.nombre)
    if q:
        consulta = consulta.where(Ubicacion.nombre.ilike(f"%{q}%"))
    return db.scalars(consulta.limit(limit)).all()


@router.get("/{ubicacion_id}", response_model=UbicacionOut)
def obtener_ubicacion(ubicacion_id: int, db: Session = Depends(get_db)):
    ubicacion = db.get(Ubicacion, ubicacion_id)
    if ubicacion is None:
        raise HTTPException(status_code=404, detail="la ubicacion no existe")
    return ubicacion