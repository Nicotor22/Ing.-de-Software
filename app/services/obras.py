from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import Autor, Obra, ObraAutor, Ubicacion
from ..schemas import ObraIn, ObraCreateIn
from . import documentos as docs


def a_dto(obra: Obra) -> dict:
    return {
        "id": obra.id,
        "titulo": obra.titulo,
        "tecnica": obra.tecnica,
        "alto": obra.alto,
        "ancho": obra.ancho,
        "profundidad": obra.profundidad,
        "periodo": obra.periodo,
        "estado_conservacion": obra.estado_conservacion,
        "modo_ingreso": obra.modo_ingreso,
        "digitalizada": obra.digitalizada,
        "id_coleccion": obra.id_coleccion,
        "id_ubicacion_actual": obra.id_ubicacion_actual,
        "autores": [
            {
                "id_autor": oa.id_autor,
                "nombre": oa.autor.nombre,
                "fecha_creacion": oa.fecha_creacion,
                "fecha_finalizacion": oa.fecha_finalizacion,
            }
            for oa in obra.autores
        ],
    }


def obtener_obra(db: Session, obra_id: int) -> Obra:
    obra = db.get(Obra, obra_id)
    if obra is None:
        raise HTTPException(status_code=404, detail="La obra no existe")
    return obra


def _validar_referencias(db: Session, datos: ObraIn) -> None:
    if db.get(Ubicacion, datos.id_ubicacion_actual) is None:
        raise HTTPException(status_code=404, detail="La ubicación indicada no existe")

    ids = [a.id_autor for a in datos.autores]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="Hay autores repetidos en la selección")

    existentes = set(db.scalars(select(Autor.id).where(Autor.id.in_(ids))))
    faltantes = sorted(set(ids) - existentes)
    if faltantes:
        raise HTTPException(status_code=404, detail=f"No existen los autores con id: {faltantes}")

def _guardar(db: Session) -> None:
    """Un único commit; si falla, se deshace todo (garantía mínima del CU-01)."""
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar la obra; no se registró ningún dato",
        )

def crear_obra(db: Session, datos: ObraCreateIn) -> Obra:
    _validar_referencias(db, datos)

    obra = Obra(**datos.model_dump(exclude={"autores", "acta_donacion"}))
    obra.autores = [ObraAutor(**a.model_dump()) for a in datos.autores]

    if datos.acta_donacion:  # CU-01, paso 3: se invoca CU-03 sin commit propio
        docs.agregar_documento(
            db, obra, docs.id_tipo_por_nombre(db, docs.TIPO_ACTA),
            datos.acta_donacion.url, datos.acta_donacion.formato,
        )

    db.add(obra)
    _guardar(db)
    db.refresh(obra)
    return obra

def actualizar_obra(db: Session, obra_id: int, datos: ObraIn) -> Obra:
    obra = obtener_obra(db, obra_id)
    if datos.id_ubicacion_actual != obra.id_ubicacion_actual:
        raise HTTPException(
            status_code=422,
            detail="La ubicación de una obra se cambia registrando un movimiento (CU-04), "
                   "no editando su ficha",
        )
    _validar_referencias(db, datos)  # antes de modificar nada

    # Datos propios de la obra
    for campo, valor in datos.model_dump(exclude={"autores"}).items():
        setattr(obra, campo, valor)

    # Autores: se compara lo que hay con lo que llega
    actuales = {oa.id_autor: oa for oa in obra.autores}
    nuevos_ids = set()
    for a in datos.autores:
        nuevos_ids.add(a.id_autor)
        if a.id_autor in actuales:
            # ya estaba: solo se actualizan las fechas de la relación
            actuales[a.id_autor].fecha_creacion = a.fecha_creacion
            actuales[a.id_autor].fecha_finalizacion = a.fecha_finalizacion
        else:
            # autor nuevo para esta obra
            obra.autores.append(ObraAutor(**a.model_dump()))

    for id_autor, relacion in actuales.items():
        if id_autor not in nuevos_ids:
            obra.autores.remove(relacion)  # cascade delete-orphan borra la fila

    _guardar(db)
    db.refresh(obra)
    return obra