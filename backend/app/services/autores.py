from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import Autor
from ..schemas import AutorIn


def a_dto(autor: Autor) -> dict:
    return {
        "id": autor.id,
        "nombre": autor.nombre,
        "nacionalidad": autor.nacionalidad,
        "periodo": autor.periodo,
        "tecnica_habitual": autor.tecnica_habitual,
        "biografia": autor.biografia,
    }


def obtener_autor(db: Session, autor_id: int) -> Autor:
    autor = db.get(Autor, autor_id)
    if autor is None:
        raise HTTPException(status_code=404, detail="El autor no existe")
    return autor


def _guardar(db: Session) -> None:
    """Un único commit; si falla, se deshace todo (garantía mínima del CU-02)."""
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar el autor; no se registró ningún dato",
        )


def _verificar_duplicado(
    db: Session, nombre: str, confirmar_duplicado: bool, excluir_id: int | None = None
) -> None:
    """Extensión del CU-02: si el nombre ya existe se advierte, salvo que se confirme."""
    if confirmar_duplicado:
        return
    consulta = select(Autor).where(func.lower(Autor.nombre) == nombre.lower())
    if excluir_id is not None:
        consulta = consulta.where(Autor.id != excluir_id)  # no compararse consigo mismo
    existente = db.scalars(consulta).first()
    if existente:
        raise HTTPException(
            status_code=409,
            detail={
                "mensaje": "Ya existe un autor con ese nombre",
                "autor_existente": {"id": existente.id, "nombre": existente.nombre},
            },
        )


def crear_autor(db: Session, datos: AutorIn, confirmar_duplicado: bool = False) -> Autor:
    _verificar_duplicado(db, datos.nombre, confirmar_duplicado)
    autor = Autor(**datos.model_dump())
    db.add(autor)
    _guardar(db)
    db.refresh(autor)
    return autor


def actualizar_autor(
    db: Session, autor_id: int, datos: AutorIn, confirmar_duplicado: bool = False
) -> Autor:
    autor = obtener_autor(db, autor_id)
    _verificar_duplicado(db, datos.nombre, confirmar_duplicado, excluir_id=autor.id)
    for campo, valor in datos.model_dump().items():
        setattr(autor, campo, valor)
    _guardar(db)
    db.refresh(autor)
    return autor