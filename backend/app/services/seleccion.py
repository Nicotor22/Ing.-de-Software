from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Coleccion


def resolver_obras(db: Session, obra_ids: list[int], coleccion_ids: list[int]) -> list[int]:
    """Obras sueltas + las de cada colección en este momento, sin repetidas."""
    ids = dict.fromkeys(obra_ids)  # dict para conservar el orden y evitar repetidas
    for cid in dict.fromkeys(coleccion_ids):
        coleccion = db.get(Coleccion, cid)
        if coleccion is None:
            raise HTTPException(status_code=404, detail=f"La colección {cid} no existe")
        for obra in coleccion.obras:
            ids[obra.id] = None
    if not ids:
        raise HTTPException(status_code=422, detail="La selección no incluye ninguna obra")
    return list(ids)