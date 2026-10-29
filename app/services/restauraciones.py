from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import EstadoRestauracion, Obra, Restauracion, Ubicacion
from ..schemas import ArchivoIn, RestauracionIn, RegresoRestauracionIn
from . import documentos as docs
from .disponibilidad import en_restauracion, prestamo_activo
from .movimientos import aplicar_movimiento


def a_dto(r: Restauracion) -> dict:
    return {
        "id": r.id,
        "id_obra": r.id_obra,
        "fecha_inicio": r.fecha_inicio,
        "fecha_prevista_devolucion": r.fecha_prevista_devolucion,
        "fecha_regreso_real": r.fecha_regreso_real,
        "tecnica_aplicada": r.tecnica_aplicada,
        "responsable": r.responsable,
        "estado": r.estado,
        "id_documento_informe": r.id_documento_informe,
        "informe_pendiente": r.id_documento_informe is None,
    }


def obtener_restauracion(db: Session, restauracion_id: int) -> Restauracion:
    restauracion = db.get(Restauracion, restauracion_id)
    if restauracion is None:
        raise HTTPException(status_code=404, detail="La restauración no existe")
    return restauracion


def registrar_restauracion(db: Session, datos: RestauracionIn) -> Restauracion:
    # ---- Validaciones: todavía no se escribe nada ----
    # Se bloquea la obra ANTES de mirar su situación (como en el préstamo)
    obra = db.get(Obra, datos.id_obra, with_for_update=True)
    if obra is None:
        raise HTTPException(status_code=404, detail="La obra no existe")
    if db.get(Ubicacion, datos.id_ubicacion_destino) is None:
        raise HTTPException(status_code=404, detail="La ubicación de destino no existe")
    if obra.id_ubicacion_actual == datos.id_ubicacion_destino:
        raise HTTPException(status_code=422, detail="La obra ya se encuentra en esa ubicación")
    if prestamo_activo(db, obra.id) is not None:
        raise HTTPException(
            status_code=409,
            detail="La obra está prestada: no puede enviarse a restauración hasta ser devuelta",
        )
    if en_restauracion(db, obra.id):
        raise HTTPException(status_code=409, detail="La obra ya tiene una restauración activa")

    id_tipo_informe = docs.id_tipo_por_nombre(db, docs.TIPO_INFORME) if datos.informe else None

    # ---- Escritura: todo en una única transacción ----
    restauracion = Restauracion(
        id_obra=obra.id,
        fecha_inicio=datos.fecha_inicio,
        fecha_prevista_devolucion=datos.fecha_prevista_devolucion,
        tecnica_aplicada=datos.tecnica_aplicada,
        responsable=datos.responsable,
        estado=EstadoRestauracion.ACTIVA,
    )
    try:
        db.add(restauracion)
        db.flush()  # para conocer restauracion.id y usarlo en el motivo del movimiento

        if datos.informe:  # <<include>> Vincular Documentación Multimedia
            documento = docs.agregar_documento(
                db, obra, id_tipo_informe, datos.informe.url, datos.informe.formato
            )
            restauracion.informe = documento  # el informe es de ESTA obra y del tipo correcto

        # <<include>> Registrar Movimiento (automático): salida hacia el taller
        aplicar_movimiento(
            db, obra, datos.id_ubicacion_destino,
            f"Restauración n.º {restauracion.id}", datos.responsable,
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar la restauración; no se guardó ningún dato",
        )
    db.refresh(restauracion)
    return restauracion


def adjuntar_informe(db: Session, restauracion_id: int, archivo: ArchivoIn) -> Restauracion:
    """Completa un 'informe pendiente' (extensión del paso 3)."""
    restauracion = db.get(Restauracion, restauracion_id, with_for_update=True)
    if restauracion is None:
        raise HTTPException(status_code=404, detail="La restauración no existe")
    if restauracion.id_documento_informe is not None:
        raise HTTPException(status_code=409, detail="La restauración ya tiene un informe vinculado")

    obra = db.get(Obra, restauracion.id_obra)
    id_tipo = docs.id_tipo_por_nombre(db, docs.TIPO_INFORME)
    try:
        documento = docs.agregar_documento(db, obra, id_tipo, archivo.url, archivo.formato)
        restauracion.informe = documento
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="No se pudo vincular el informe; no se guardó ningún dato"
        )
    db.refresh(restauracion)
    return restauracion

def registrar_regreso(
    db: Session, restauracion_id: int, datos: RegresoRestauracionIn
) -> Restauracion:
    # Se bloquea la restauración: si llegan dos regresos a la vez, el segundo espera,
    # ve que ya está finalizada y se rechaza
    restauracion = db.get(Restauracion, restauracion_id, with_for_update=True)
    if restauracion is None:
        raise HTTPException(status_code=404, detail="La restauración no existe")

    # Paso 3 (extensión): tiene que estar activa
    if restauracion.estado != EstadoRestauracion.ACTIVA:
        raise HTTPException(
            status_code=409, detail="La restauración ya no está activa (fue finalizada antes)"
        )
    if datos.fecha_regreso_real < restauracion.fecha_inicio:
        raise HTTPException(
            status_code=422,
            detail="La fecha de regreso no puede ser anterior a la de inicio de la restauración",
        )
    if db.get(Ubicacion, datos.id_ubicacion_destino) is None:
        raise HTTPException(status_code=404, detail="La ubicación de destino no existe")

    obra = db.get(Obra, restauracion.id_obra, with_for_update=True)
    if obra.id_ubicacion_actual == datos.id_ubicacion_destino:
        raise HTTPException(
            status_code=422,
            detail="La obra ya está en esa ubicación (el taller): elegí la sala o el depósito al que vuelve",
        )

    try:
        # <<include>> Registrar Movimiento (automático, sin commit propio)
        aplicar_movimiento(
            db, obra, datos.id_ubicacion_destino,
            f"Regreso de la restauración n.º {restauracion.id}", datos.responsable,
        )
        restauracion.estado = EstadoRestauracion.FINALIZADA
        restauracion.fecha_regreso_real = datos.fecha_regreso_real
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar el regreso; la restauración sigue activa",
        )
    db.refresh(restauracion)
    return restauracion