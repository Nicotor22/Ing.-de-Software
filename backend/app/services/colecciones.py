from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import Coleccion, Obra
from ..schemas import ColeccionIn


def a_dto(coleccion: Coleccion) -> dict:
    return {
        "id": coleccion.id,
        "nombre": coleccion.nombre,
        "descripcion": coleccion.descripcion,
        "obras": [{"id_obra": o.id, "titulo": o.titulo} for o in coleccion.obras],
    }


def obtener_coleccion(db: Session, coleccion_id: int) -> Coleccion:
    coleccion = db.get(Coleccion, coleccion_id)
    if coleccion is None:
        raise HTTPException(status_code=404, detail="La colección no existe")
    return coleccion


def _guardar(db: Session) -> None:
    """Un único commit; si falla, se deshace todo (garantía mínima del CU-05)."""
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar la colección; no se registró ningún cambio",
        )


def _verificar_nombre(db: Session, nombre: str, excluir_id: int | None = None) -> None:
    """Paso 4 (extensión): el nombre es único y NO hay opción de confirmar."""
    consulta = select(Coleccion).where(func.lower(Coleccion.nombre) == nombre.lower())
    if excluir_id is not None:
        consulta = consulta.where(Coleccion.id != excluir_id)
    existente = db.scalars(consulta).first()
    if existente:
        raise HTTPException(
            status_code=409,
            detail={
                "mensaje": "Ya existe una colección con ese nombre. Elegí otro",
                "coleccion_existente": {"id": existente.id, "nombre": existente.nombre},
            },
        )


def _cargar_obras(db: Session, obra_ids: list[int], coleccion_id: int | None = None) -> list[Obra]:
    """Pasos 3 y 5: las obras existen y ninguna pertenece a OTRA colección."""
    if len(obra_ids) != len(set(obra_ids)):
        raise HTTPException(status_code=422, detail="Hay obras repetidas en la selección")

    obras = list(db.scalars(select(Obra).where(Obra.id.in_(obra_ids))))
    faltantes = sorted(set(obra_ids) - {o.id for o in obras})
    if faltantes:
        raise HTTPException(status_code=404, detail=f"No existen las obras con id: {faltantes}")

    en_otra = [
        {
            "id_obra": o.id,
            "titulo": o.titulo,
            "coleccion_actual": {"id": o.coleccion.id, "nombre": o.coleccion.nombre},
        }
        for o in obras
        if o.id_coleccion is not None and o.id_coleccion != coleccion_id
    ]
    if en_otra:
        raise HTTPException(
            status_code=409,
            detail={"mensaje": "Hay obras que ya pertenecen a otra colección", "obras": en_otra},
        )
    return obras


def crear_coleccion(db: Session, datos: ColeccionIn) -> Coleccion:
    # Se valida todo ANTES de escribir
    _verificar_nombre(db, datos.nombre)
    obras = _cargar_obras(db, datos.obra_ids)

    coleccion = Coleccion(nombre=datos.nombre, descripcion=datos.descripcion)
    coleccion.obras = obras
    db.add(coleccion)
    _guardar(db)
    db.refresh(coleccion)
    return coleccion


def actualizar_coleccion(db: Session, coleccion_id: int, datos: ColeccionIn) -> Coleccion:
    coleccion = obtener_coleccion(db, coleccion_id)
    _verificar_nombre(db, datos.nombre, excluir_id=coleccion.id)
    obras = _cargar_obras(db, datos.obra_ids, coleccion_id=coleccion.id)

    coleccion.nombre = datos.nombre
    coleccion.descripcion = datos.descripcion
    # La lista es la composición FINAL: las obras que ya no están quedan con
    # id_coleccion = NULL, o sea "sin colección" (extensión del paso 3)
    coleccion.obras = obras
    _guardar(db)
    db.refresh(coleccion)
    return coleccion