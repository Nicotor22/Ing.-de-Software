from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import Movimiento, Obra, Ubicacion
from ..schemas import MovimientoIn
from .disponibilidad import prestamo_activo


def aplicar_movimiento(
    db: Session, obra: Obra, id_destino: int, motivo: str, responsable: str
) -> Movimiento:
    """
    Paso 6 del CU-04. NO hace commit: lo hace quien la llama, para que todo ocurra
    en una sola transacción. Préstamo y Restauración la van a reutilizar (<<include>>).
    """
    movimiento = Movimiento(
        id_obra=obra.id,
        id_ubicacion_origen=obra.id_ubicacion_actual,  # se lee ANTES de cambiarla
        id_ubicacion_destino=id_destino,
        fecha=date.today(),
        motivo=motivo,
        responsable=responsable,
    )
    db.add(movimiento)
    obra.id_ubicacion_actual = id_destino
    return movimiento


def _validar_obra_movible(db: Session, obra: Obra) -> None:
    if prestamo_activo(db, obra.id) is not None:
        raise HTTPException(
            status_code=409,
            detail="La obra está prestada: su ubicación la gestiona el préstamo "
                   "y no puede moverse manualmente",
        )
    # TODO (CU-08): impedir también el movimiento manual si está en restauración.


def _guardar(db: Session) -> None:
    """Un único commit; si falla, se deshace todo y el historial previo queda intacto."""
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar el movimiento; no se guardó ningún dato",
        )


def registrar_movimiento(db: Session, datos: MovimientoIn) -> Movimiento:
    # with_for_update bloquea la fila de la obra en PostgreSQL: evita que dos traslados
    # simultáneos lean el mismo origen y dejen el historial inconsistente
    obra = db.get(Obra, datos.id_obra, with_for_update=True)
    if obra is None:
        raise HTTPException(status_code=404, detail="La obra no existe")

    _validar_obra_movible(db, obra)

    if db.get(Ubicacion, datos.id_ubicacion_destino) is None:
        raise HTTPException(status_code=404, detail="La ubicación seleccionada no es válida")
    if obra.id_ubicacion_actual == datos.id_ubicacion_destino:
        raise HTTPException(status_code=422, detail="La obra ya se encuentra en esa ubicación")

    movimiento = aplicar_movimiento(
        db, obra, datos.id_ubicacion_destino, datos.motivo, datos.responsable
    )
    _guardar(db)
    db.refresh(movimiento)
    return movimiento


def historial(db: Session, id_obra: int | None = None) -> list[Movimiento]:
    if id_obra is not None and db.get(Obra, id_obra) is None:
        raise HTTPException(status_code=404, detail="La obra no existe")
    consulta = select(Movimiento).order_by(Movimiento.id.desc())  # el más reciente primero
    if id_obra is not None:
        consulta = consulta.where(Movimiento.id_obra == id_obra)
    return list(db.scalars(consulta).all())