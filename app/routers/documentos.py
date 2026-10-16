from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import TipoDocumento
from ..schemas import DocumentoIn, DocumentoOut, TipoDocumentoOut
from ..services import documentos as servicio

router = APIRouter(tags=["CU-03 - Documentos"])


@router.get("/tipos-documento", response_model=list[TipoDocumentoOut])
def listar_tipos(db: Session = Depends(get_db)):
    return db.scalars(select(TipoDocumento).order_by(TipoDocumento.id)).all()


@router.post("/documentos", response_model=DocumentoOut, status_code=201)
def vincular_documento(datos: DocumentoIn, db: Session = Depends(get_db)):
    return servicio.a_dto(servicio.registrar_documento(db, datos))


@router.get("/documentos", response_model=list[DocumentoOut])
def listar_documentos(id_obra: int, db: Session = Depends(get_db)):
    return [servicio.a_dto(d) for d in servicio.listar_documentos(db, id_obra)]