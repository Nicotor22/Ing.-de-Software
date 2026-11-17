from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from ..auth import usuario_actual
from ..database import get_db
from ..models import TipoDocumento
from ..schemas import DocumentoIn, DocumentoOut, TipoDocumentoOut
from ..services import documentos as servicio

router = APIRouter(tags=["CU-03 - Documentos"])


@router.get("/tipos-documento", response_model=list[TipoDocumentoOut])
def listar_tipos(db: Session = Depends(get_db)):
    return db.scalars(select(TipoDocumento).order_by(TipoDocumento.id)).all()


@router.post("/documentos", response_model=DocumentoOut, status_code=201)
def vincular_documento(
    datos: DocumentoIn,
    _=Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    return servicio.a_dto(servicio.registrar_documento(db, datos))


@router.post("/documentos/subir", response_model=DocumentoOut, status_code=201)
async def subir_documento(
    id_obra: UUID = Form(...),
    id_tipo_documento: UUID = Form(...),
    archivo: UploadFile = File(...),
    _=Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    doc = await servicio.subir_archivo_supabase(
        db, id_obra, id_tipo_documento, archivo, marcar_digitalizada=False
    )
    return servicio.a_dto(doc)


@router.get("/documentos", response_model=list[DocumentoOut])
def listar_documentos(
    id_obra: UUID,
    _=Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    return [servicio.a_dto(d) for d in servicio.listar_documentos(db, id_obra)]

@router.delete("/documentos/{id_documento}", status_code=204)
def borrar_documento(
    id_documento: UUID,
    _=Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    servicio.eliminar_documento(db, id_documento)