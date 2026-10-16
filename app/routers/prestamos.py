from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import EstadoPrestamo, Prestamo
from ..schemas import PrestamoIn, PrestamoOut, DevolucionIn
from ..services import prestamos as servicio

router = APIRouter(prefix="/prestamos", tags=["CU-06 - Préstamos"])


@router.post("", response_model=PrestamoOut, status_code=201)
def registrar_prestamo(datos: PrestamoIn, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.registrar_prestamo(db, datos))


@router.get("", response_model=list[PrestamoOut])
def listar_prestamos(
    estado: EstadoPrestamo | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    consulta = select(Prestamo).order_by(Prestamo.id.desc())
    if estado:
        consulta = consulta.where(Prestamo.estado == estado)
    return [servicio.a_dto(p) for p in db.scalars(consulta.limit(limit)).all()]


@router.get("/{prestamo_id}", response_model=PrestamoOut)
def obtener_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.obtener_prestamo(db, prestamo_id))

@router.post("/{prestamo_id}/devolucion", response_model=PrestamoOut)
def registrar_devolucion(prestamo_id: int, datos: DevolucionIn, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.registrar_devolucion(db, prestamo_id, datos))