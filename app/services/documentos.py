from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import Documento, Obra, TipoDocumento
from ..schemas import DocumentoIn

TIPO_ACTA = "Acta de Donación"  # tiene que coincidir con el nombre precargado
TIPO_PRESTAMO = "Documentación de Préstamo"  # tiene que coincidir con el nombre precargado


def a_dto(doc: Documento) -> dict:
    return {
        "id": doc.id,
        "id_obra": doc.id_obra,
        "id_tipo_documento": doc.id_tipo_documento,
        "tipo": doc.tipo.nombre,
        "url": doc.url,
        "formato": doc.formato,
    }


def _guardar(db: Session) -> None:
    """Un único commit; si falla, el archivo no queda vinculado (garantía mínima del CU-03)."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="La obra ya no está disponible; se canceló la operación"
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="No se pudo vincular el archivo; no se guardó ningún dato"
        )


def id_tipo_por_nombre(db: Session, nombre: str) -> int:
    tipo = db.scalars(select(TipoDocumento).where(TipoDocumento.nombre == nombre)).first()
    if tipo is None:
        raise HTTPException(
            status_code=500, detail=f"Falta el tipo de documento '{nombre}' en la base"
        )
    return tipo.id


def agregar_documento(
    db: Session, obra: Obra, id_tipo: int, url: str, formato: str
) -> Documento:
    """
    Paso 6 del CU-03. NO hace commit: lo hace quien la llama, para que todo ocurra en una
    sola transacción (la reutilizan Gestionar Obra y, más adelante, Préstamo y Restauración).
    """
    if db.get(TipoDocumento, id_tipo) is None:
        raise HTTPException(status_code=404, detail="El tipo de documento no existe")
    documento = Documento(id_tipo_documento=id_tipo, url=url, formato=formato)
    obra.documentos.append(documento)
    return documento


def registrar_documento(db: Session, datos: DocumentoIn) -> Documento:
    obra = db.get(Obra, datos.id_obra)
    if obra is None:
        raise HTTPException(status_code=404, detail="La obra no existe")
    documento = agregar_documento(db, obra, datos.id_tipo_documento, datos.url, datos.formato)
    _guardar(db)
    db.refresh(documento)
    return documento


def listar_documentos(db: Session, id_obra: int) -> list[Documento]:
    if db.get(Obra, id_obra) is None:
        raise HTTPException(status_code=404, detail="La obra no existe")
    consulta = select(Documento).where(Documento.id_obra == id_obra).order_by(Documento.id)
    return list(db.scalars(consulta).all())