from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import EstadoRestauracion, Restauracion
from ..schemas import ArchivoIn, RestauracionIn, RestauracionOut, RegresoRestauracionIn
from ..services import restauraciones as servicio

router = APIRouter(prefix="/restauraciones", tags=["CU-09 - Restauraciones"])


@router.post("", response_model=RestauracionOut, status_code=201)
def registrar_restauracion(datos: RestauracionIn, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.registrar_restauracion(db, datos))


@router.get("", response_model=list[RestauracionOut])
def listar_restauraciones(
    id_obra: int | None = None,
    estado: EstadoRestauracion | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    consulta = select(Restauracion).order_by(Restauracion.id.desc())  # historial: la última primero
    if id_obra is not None:
        consulta = consulta.where(Restauracion.id_obra == id_obra)
    if estado:
        consulta = consulta.where(Restauracion.estado == estado)
    return [servicio.a_dto(r) for r in db.scalars(consulta.limit(limit)).all()]


@router.get("/{restauracion_id}", response_model=RestauracionOut)
def obtener_restauracion(restauracion_id: int, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.obtener_restauracion(db, restauracion_id))


@router.post("/{restauracion_id}/informe", response_model=RestauracionOut)
def adjuntar_informe(restauracion_id: int, archivo: ArchivoIn, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.adjuntar_informe(db, restauracion_id, archivo))

@router.post("/{restauracion_id}/regreso", response_model=RestauracionOut)
def registrar_regreso(
    restauracion_id: int, datos: RegresoRestauracionIn, db: Session = Depends(get_db)
):
    return servicio.a_dto(servicio.registrar_regreso(db, restauracion_id, datos))