from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import date

from ..models import EstadoPrestamo, Prestamo, PrestamoObra, EstadoRestauracion, Restauracion


def prestamo_activo(db: Session, id_obra: int) -> Prestamo | None:
    consulta = (
        select(Prestamo)
        .join(PrestamoObra, PrestamoObra.id_prestamo == Prestamo.id)
        .where(PrestamoObra.id_obra == id_obra, Prestamo.estado == EstadoPrestamo.ACTIVO)
    )
    return db.scalars(consulta).first()


def restauracion_en_curso(db: Session, id_obra: int) -> dict | None:
    """Si la obra tiene una restauración activa devuelve su fecha prevista; si no, None."""
    restauracion = db.scalars(
        select(Restauracion).where(
            Restauracion.id_obra == id_obra,
            Restauracion.estado == EstadoRestauracion.ACTIVA,
        )
    ).first()
    if restauracion is None:
        return None
    return {"fecha_prevista": restauracion.fecha_prevista_devolucion}


def en_restauracion(db: Session, id_obra: int) -> bool:
    return restauracion_en_curso(db, id_obra) is not None