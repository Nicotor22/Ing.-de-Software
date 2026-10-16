from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import Exposicion, ExposicionObra, Obra, Ubicacion
from ..schemas import ExposicionIn
from .disponibilidad import prestamo_activo, restauracion_en_curso
from .seleccion import resolver_obras


def a_dto(e: Exposicion) -> dict:
    return {
        "id": e.id,
        "nombre": e.nombre,
        "fecha_inicio": e.fecha_inicio,
        "fecha_fin": e.fecha_fin,
        "id_ubicacion": e.id_ubicacion,
        "publicada_virtual": e.publicada_virtual,
        "obras": [{"id_obra": eo.id_obra, "titulo": eo.obra.titulo} for eo in e.obras],
    }


def obtener_exposicion(db: Session, exposicion_id: int) -> Exposicion:
    exposicion = db.get(Exposicion, exposicion_id)
    if exposicion is None:
        raise HTTPException(status_code=404, detail="La exposición no existe")
    return exposicion


def _verificar_superposicion(db: Session, datos: ExposicionIn) -> None:
    """Paso 3: dos exposiciones en la misma sala no pueden tener fechas que se crucen."""
    consulta = select(Exposicion).where(
        Exposicion.id_ubicacion == datos.id_ubicacion,
        Exposicion.fecha_inicio <= datos.fecha_fin,
        Exposicion.fecha_fin >= datos.fecha_inicio,
    )
    conflictos = db.scalars(consulta).all()
    if conflictos:
        raise HTTPException(
            status_code=409,
            detail={
                "mensaje": "Hay otra exposición en la misma sala con fechas superpuestas",
                "conflictos": [
                    {
                        "id": c.id,
                        "nombre": c.nombre,
                        "fecha_inicio": c.fecha_inicio.isoformat(),
                        "fecha_fin": c.fecha_fin.isoformat(),
                    }
                    for c in conflictos
                ],
            },
        )


def _evaluar_obras(db: Session, obras: list[Obra], fecha_inicio) -> tuple[list, list, list]:
    """Paso 3: qué obras se incluyen, cuáles se excluyen y cuáles llevan advertencia."""
    incluibles, excluidas, advertencias = [], [], []
    for obra in obras:
        if prestamo_activo(db, obra.id) is not None:  # prestada: sin excepción
            excluidas.append({"id_obra": obra.id, "titulo": obra.titulo, "motivo": "está prestada"})
            continue

        restauracion = restauracion_en_curso(db, obra.id)
        if restauracion is not None:
            prevista = restauracion["fecha_prevista"]
            # Solo se incluye si vuelve ANTES del inicio (igual al inicio no alcanza)
            if prevista is not None and prevista < fecha_inicio:
                advertencias.append(
                    f"La obra '{obra.titulo}' está en restauración; se incluye porque su "
                    f"devolución prevista ({prevista}) es anterior al inicio de la exposición"
                )
            else:
                motivo = (
                    "está en restauración y su devolución prevista es posterior al inicio"
                    if prevista is not None
                    else "está en restauración y no tiene fecha prevista de devolución"
                )
                excluidas.append({"id_obra": obra.id, "titulo": obra.titulo, "motivo": motivo})
                continue
        incluibles.append(obra)
    return incluibles, excluidas, advertencias


def _preparar(db: Session, datos: ExposicionIn, bloquear: bool):
    """
    Todo el paso 3. Con bloquear=True (al crear) se bloquean la sala y las obras hasta el
    final de la transacción, para que nadie las tome a la vez.
    """
    if db.get(Ubicacion, datos.id_ubicacion, with_for_update=bloquear) is None:
        raise HTTPException(status_code=404, detail="La sala indicada no existe")
    # TODO (tu equipo): validar que la ubicación admita exposiciones cuando exista el "tipo"

    _verificar_superposicion(db, datos)

    ids = resolver_obras(db, datos.obra_ids, datos.coleccion_ids)
    consulta = select(Obra).where(Obra.id.in_(ids)).order_by(Obra.id)
    if bloquear:
        consulta = consulta.with_for_update()
    obras = list(db.scalars(consulta))
    faltantes = sorted(set(ids) - {o.id for o in obras})
    if faltantes:
        raise HTTPException(status_code=404, detail=f"No existen las obras con id: {faltantes}")

    incluibles, excluidas, advertencias = _evaluar_obras(db, obras, datos.fecha_inicio)
    if not incluibles:
        raise HTTPException(
            status_code=422,
            detail={"mensaje": "Ninguna de las obras seleccionadas puede incluirse",
                    "excluidas": excluidas},
        )
    return incluibles, excluidas, advertencias


def validar_exposicion(db: Session, datos: ExposicionIn) -> dict:
    """Pasos 1 a 3 sin guardar nada: lo que el administrador ve antes de confirmar."""
    incluibles, excluidas, advertencias = _preparar(db, datos, bloquear=False)
    return {
        "incluidas": [{"id_obra": o.id, "titulo": o.titulo} for o in incluibles],
        "excluidas": excluidas,
        "advertencias": advertencias,
    }


def crear_exposicion(db: Session, datos: ExposicionIn):
    """Paso 6: se repite la validación (algo pudo cambiar) y se guarda TODO junto."""
    incluibles, excluidas, advertencias = _preparar(db, datos, bloquear=True)

    exposicion = Exposicion(
        nombre=datos.nombre,
        fecha_inicio=datos.fecha_inicio,
        fecha_fin=datos.fecha_fin,
        id_ubicacion=datos.id_ubicacion,
        publicada_virtual=False,
    )
    # Instantánea: estas son las obras de la exposición desde ahora
    exposicion.obras = [ExposicionObra(id_obra=o.id) for o in incluibles]

    try:
        db.add(exposicion)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar la exposición; no se guardó ningún dato",
        )
    db.refresh(exposicion)
    return exposicion, excluidas, advertencias