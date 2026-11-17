from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session
from uuid import UUID

from ..auth import usuario_actual
from ..database import get_db
from ..schemas import DigitalizacionIn, ObraOut
from ..services import digitalizacion as servicio
from ..services import documentos as servicio_docs
from ..services import obras as servicio_obras

router = APIRouter(prefix="/obras", tags=["CU-12 - Digitalización"])


@router.post("/{obra_id}/digitalizacion/validar")
def validar_digitalizacion(obra_id: UUID, datos: DigitalizacionIn, db: Session = Depends(get_db)):
    return servicio.validar_digitalizacion(db, obra_id, datos)


@router.post("/{obra_id}/digitalizacion", response_model=ObraOut)
def digitalizar_obra(obra_id: UUID, datos: DigitalizacionIn, db: Session = Depends(get_db)):
    return servicio_obras.a_dto(servicio.digitalizar_obra(db, obra_id, datos))


@router.post("/{obra_id}/digitalizacion/subir", response_model=ObraOut)
async def digitalizar_obra_archivo(
    obra_id: UUID,
    archivo: UploadFile = File(...),
    _=Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    obra = servicio_obras.obtener_obra(db, obra_id)
    id_tipo_foto = servicio_docs.id_tipo_por_nombre(db, servicio_docs.TIPO_FOTO)

    # Si ya tenía fotos anteriores, las damos de baja para reemplazarla por la nueva
    for doc_viejo in list(obra.documentos):
        if doc_viejo.fecha_baja is None and doc_viejo.id_tipo_documento == id_tipo_foto:
            servicio_docs.eliminar_documento(db, doc_viejo.id)

    await servicio_docs.subir_archivo_supabase(
        db, obra_id, id_tipo_foto, archivo, marcar_digitalizada=True
    )
    return servicio_obras.a_dto(servicio_obras.obtener_obra(db, obra_id))