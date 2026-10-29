from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import Exposicion
from .exposiciones import obtener_exposicion


def _clasificar(exposicion: Exposicion) -> tuple[list[dict], list[dict]]:
    """Separa las obras de la exposición en digitalizadas y faltantes."""
    digitalizadas, faltantes = [], []
    for eo in exposicion.obras:
        info = {"id_obra": eo.id_obra, "titulo": eo.obra.titulo}
        (digitalizadas if eo.obra.digitalizada else faltantes).append(info)
    return digitalizadas, faltantes


def validar_publicacion(db: Session, exposicion_id: int) -> dict:
    """Pasos 1 y 2 sin guardar nada: lo que el administrador ve antes de confirmar."""
    exposicion = obtener_exposicion(db, exposicion_id)
    digitalizadas, faltantes = _clasificar(exposicion)
    return {
        "ya_publicada": exposicion.publicada_virtual,
        "digitalizadas": digitalizadas,
        "faltantes": faltantes,
        "completa": not faltantes,
    }


def publicar(db: Session, exposicion_id: int, solo_digitalizadas: bool) -> dict:
    """Paso 5: se repite la validación (algo pudo cambiar) y se publica."""
    # Se bloquea la exposición: dos publicaciones simultáneas no pueden pasar las dos
    exposicion = db.get(Exposicion, exposicion_id, with_for_update=True)
    if exposicion is None:
        raise HTTPException(status_code=404, detail="La exposición no existe")
    if exposicion.publicada_virtual:
        raise HTTPException(status_code=409, detail="La exposición virtual ya está publicada")

    digitalizadas, faltantes = _clasificar(exposicion)
    if not digitalizadas:
        raise HTTPException(
            status_code=422,
            detail={
                "mensaje": "Ninguna obra de la exposición está digitalizada: no hay nada para publicar",
                "faltantes": faltantes,
            },
        )
    if faltantes and not solo_digitalizadas:
        # Extensión del paso 2: se advierte cuáles faltan; se puede publicar solo con las
        # digitalizadas (solo_digitalizadas=true) o posponer (no volver a llamar)
        raise HTTPException(
            status_code=409,
            detail={
                "mensaje": "Hay obras sin digitalizar. Podés publicar solo con las "
                           "digitalizadas o posponer la publicación",
                "faltantes": faltantes,
                "digitalizadas": digitalizadas,
            },
        )

    try:
        exposicion.publicada_virtual = True
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo publicar la exposición virtual; no se guardó ningún cambio. "
                   "Podés reintentar",
        )
    return {"id_exposicion": exposicion.id, "publicada_virtual": True,
            "visibles": digitalizadas, "omitidas": faltantes}