from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import EstadoPrestamo, Prestamo, PrestamoObra


def prestamo_activo(db: Session, id_obra: int) -> Prestamo | None:
    consulta = (
        select(Prestamo)
        .join(PrestamoObra, PrestamoObra.id_prestamo == Prestamo.id)
        .where(PrestamoObra.id_obra == id_obra, Prestamo.estado == EstadoPrestamo.ACTIVO)
    )
    return db.scalars(consulta).first()


def en_restauracion(db: Session, id_obra: int) -> bool:
    # TODO (CU-08): consultar si la obra tiene una restauración en curso.
    return False