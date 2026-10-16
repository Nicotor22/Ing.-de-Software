from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Autor
from ..schemas import AutorIn, AutorOut
from ..services import autores as servicio

router = APIRouter(prefix="/autores", tags=["Carga de datos - Autores"])


@router.post("", response_model=AutorOut, status_code=201)
def crear_autor(
    datos: AutorIn, confirmar_duplicado: bool = False, db: Session = Depends(get_db)
):
    return servicio.a_dto(servicio.crear_autor(db, datos, confirmar_duplicado))


@router.get("", response_model=list[AutorOut])
def listar_autores(
    q: str | None = Query(None, description="Texto a buscar en el nombre (autocompletado)"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    consulta = select(Autor).order_by(Autor.nombre)
    if q:
        consulta = consulta.where(Autor.nombre.ilike(f"%{q}%"))
    return db.scalars(consulta.limit(limit)).all()


@router.get("/{autor_id}", response_model=AutorOut)
def obtener_autor(autor_id: int, db: Session = Depends(get_db)):
    autor = db.get(Autor, autor_id)
    if autor is None:
        raise HTTPException(status_code=404, detail="El autor no existe")
    return autor

@router.put("/{autor_id}", response_model=AutorOut)
def actualizar_autor(
    autor_id: int,
    datos: AutorIn,
    confirmar_duplicado: bool = False,
    db: Session = Depends(get_db),
):
    return servicio.a_dto(servicio.actualizar_autor(db, autor_id, datos, confirmar_duplicado))