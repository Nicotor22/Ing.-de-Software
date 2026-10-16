from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import date

from ..models import EstadoPrestamo, Prestamo, PrestamoObra


def prestamo_activo(db: Session, id_obra: int) -> Prestamo | None:
    consulta = (
        select(Prestamo)
        .join(PrestamoObra, PrestamoObra.id_prestamo == Prestamo.id)
        .where(PrestamoObra.id_obra == id_obra, Prestamo.estado == EstadoPrestamo.ACTIVO)
    )
    return db.scalars(consulta).first()


def restauracion_en_curso(db: Session, id_obra: int) -> dict | None:
    """
    Si la obra está en restauración devuelve {"fecha_prevista": date | None}; si no, None.
    TODO (CU-09): consultar la tabla de restauraciones cuando exista.
    """
    return None


def en_restauracion(db: Session, id_obra: int) -> bool:
    return restauracion_en_curso(db, id_obra) is not None