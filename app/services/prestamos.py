from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import Coleccion, EstadoPrestamo, Obra, Prestamo, PrestamoObra, Ubicacion
from ..schemas import PrestamoIn
from . import documentos as docs
from .disponibilidad import en_restauracion, prestamo_activo
from .movimientos import aplicar_movimiento


def a_dto(p: Prestamo) -> dict:
    return {
        "id": p.id,
        "tipo": p.tipo,
        "nombre_prestatario": p.nombre_prestatario,
        "contacto_prestatario": p.contacto_prestatario,
        "fecha_inicio": p.fecha_inicio,
        "fecha_devolucion_prevista": p.fecha_devolucion_prevista,
        "fecha_devolucion_real": p.fecha_devolucion_real,
        "condiciones": p.condiciones,
        "estado": p.estado,
        "obras": [{"id_obra": po.id_obra, "titulo": po.obra.titulo} for po in p.obras],
    }


def obtener_prestamo(db: Session, prestamo_id: int) -> Prestamo:
    prestamo = db.get(Prestamo, prestamo_id)
    if prestamo is None:
        raise HTTPException(status_code=404, detail="El préstamo no existe")
    return prestamo


def _resolver_obras(db: Session, datos: PrestamoIn) -> list[int]:
    """Paso 1: obras sueltas + las obras de cada colección (sin repetidas)."""
    ids = dict.fromkeys(datos.obra_ids)  # dict para conservar el orden y evitar repetidas
    for cid in dict.fromkeys(datos.coleccion_ids):
        coleccion = db.get(Coleccion, cid)
        if coleccion is None:
            raise HTTPException(status_code=404, detail=f"La colección {cid} no existe")
        for obra in coleccion.obras:
            ids[obra.id] = None
    if not ids:
        raise HTTPException(status_code=422, detail="La selección no incluye ninguna obra")
    return list(ids)


def _no_disponibles(db: Session, obras: list[Obra]) -> list[dict]:
    """Paso 3: ni préstamo activo ni restauración."""
    resultado = []
    for obra in obras:
        if prestamo_activo(db, obra.id) is not None:
            motivo = "ya está prestada"
        elif en_restauracion(db, obra.id):
            motivo = "está en restauración"
        else:
            continue
        resultado.append({"id_obra": obra.id, "titulo": obra.titulo, "motivo": motivo})
    return resultado


def registrar_prestamo(db: Session, datos: PrestamoIn) -> Prestamo:
    # ---- Validaciones: todavía no se escribe nada ----
    if db.get(Ubicacion, datos.id_ubicacion_destino) is None:
        raise HTTPException(status_code=404, detail="La ubicación de destino no existe")

    ids = _resolver_obras(db, datos)

    # Se bloquean las filas de las obras (siempre en el mismo orden) y RECIÉN DESPUÉS
    # se mira la disponibilidad: así dos préstamos simultáneos no toman la misma obra
    obras = list(
        db.scalars(select(Obra).where(Obra.id.in_(ids)).order_by(Obra.id).with_for_update())
    )
    faltantes = sorted(set(ids) - {o.id for o in obras})
    if faltantes:
        raise HTTPException(status_code=404, detail=f"No existen las obras con id: {faltantes}")

    no_disponibles = _no_disponibles(db, obras)
    if no_disponibles:
        raise HTTPException(
            status_code=409,
            detail={"mensaje": "Hay obras que no están disponibles para prestar",
                    "obras": no_disponibles},
        )

    ya_ahi = [o.id for o in obras if o.id_ubicacion_actual == datos.id_ubicacion_destino]
    if ya_ahi:
        raise HTTPException(
            status_code=422,
            detail=f"Las obras {ya_ahi} ya están en la ubicación de destino indicada",
        )

    id_tipo_doc = docs.id_tipo_por_nombre(db, docs.TIPO_PRESTAMO) if datos.documentacion else None

    # ---- Escritura: todo en una única transacción ----
    prestamo = Prestamo(
        tipo=datos.tipo,
        nombre_prestatario=datos.nombre_prestatario,
        contacto_prestatario=datos.contacto_prestatario,
        fecha_inicio=datos.fecha_inicio,
        fecha_devolucion_prevista=datos.fecha_devolucion_prevista,
        condiciones=datos.condiciones,
        estado=EstadoPrestamo.ACTIVO,
    )
    prestamo.obras = [PrestamoObra(id_obra=o.id) for o in obras]

    try:
        db.add(prestamo)
        db.flush()  # envía los cambios SIN confirmarlos: sirve para conocer prestamo.id
        for obra in obras:
            # <<include>> Registrar Movimiento (automático, sin commit propio)
            aplicar_movimiento(
                db, obra, datos.id_ubicacion_destino,
                f"Préstamo n.º {prestamo.id}", datos.responsable,
            )
            if datos.documentacion:  # <<include>> Vincular Documentación Multimedia
                docs.agregar_documento(
                    db, obra, id_tipo_doc, datos.documentacion.url, datos.documentacion.formato
                )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar el préstamo; no se guardó ningún dato",
        )
    db.refresh(prestamo)
    return prestamo