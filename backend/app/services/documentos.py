import uuid
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..models import Documento, Obra, TipoDocumento
from ..schemas import DocumentoIn
from ..supabase_client import BUCKET_DOCUMENTOS, BUCKET_PUBLICO, get_supabase

TIPO_ACTA = "Acta de Donación"
TIPO_PRESTAMO = "Documentación de Préstamo"
TIPO_INFORME = "Informe de Restauración"
TIPO_FOTO = "Foto"

MIME_PERMITIDOS = {
    "image/jpeg": ("JPG", ".jpg"),
    "image/png": ("PNG", ".png"),
    "image/webp": ("WEBP", ".webp"),
    "application/pdf": ("PDF", ".pdf"),
}
MAX_BYTES = 15 * 1024 * 1024  # 15 MB


def formato_desde_url(url: str) -> str | None:
    partes = url.split("?")[0].rsplit(".", 1)
    extension = partes[-1].lower() if len(partes) == 2 else ""
    return {"jpg": "JPG", "jpeg": "JPG", "png": "PNG", "webp": "WEBP", "pdf": "PDF"}.get(extension)


def resolver_url_visible(doc: Documento) -> str:
    """Si está en el bucket privado, genera una URL firmada temporal por 10 minutos."""
    if doc.bucket == BUCKET_DOCUMENTOS and doc.ruta_storage:
        try:
            sb = get_supabase()
            res = sb.storage.from_(BUCKET_DOCUMENTOS).create_signed_url(doc.ruta_storage, 600)
            return res.get("signedURL") or res.get("signedUrl") or doc.url
        except Exception:
            return doc.url
    return doc.url


def a_dto(doc: Documento) -> dict:
    url_final = resolver_url_visible(doc)
    return {
        "id": doc.id,
        "id_obra": doc.id_obra,
        "id_tipo_documento": doc.id_tipo_documento,
        "tipo": doc.tipo.nombre,
        "url": url_final,
        "formato": formato_desde_url(doc.ruta_storage or doc.url),
    }


def _guardar(db: Session) -> None:
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


def id_tipo_por_nombre(db: Session, nombre: str) -> uuid.UUID:
    tipo = db.scalars(select(TipoDocumento).where(TipoDocumento.nombre == nombre)).first()
    if tipo is None:
        raise HTTPException(
            status_code=500, detail=f"Falta el tipo de documento '{nombre}' en la base"
        )
    return tipo.id


def agregar_documento(
    db: Session,
    obra: Obra,
    id_tipo,
    url: str,
    formato: str | None = None,
    bucket: str | None = None,
    ruta_storage: str | None = None,
) -> Documento:
    if db.get(TipoDocumento, id_tipo) is None:
        raise HTTPException(status_code=404, detail="El tipo de documento no existe")
    documento = Documento(
        id_tipo_documento=id_tipo,
        url=url,
        bucket=bucket,
        ruta_storage=ruta_storage,
    )
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


async def subir_archivo_supabase(
    db: Session,
    id_obra: uuid.UUID,
    id_tipo_documento: uuid.UUID,
    archivo: UploadFile,
    marcar_digitalizada: bool = False,
) -> Documento:
    obra = db.get(Obra, id_obra)
    if obra is None:
        raise HTTPException(status_code=404, detail="La obra no existe")

    tipo = db.get(TipoDocumento, id_tipo_documento)
    if tipo is None:
        raise HTTPException(status_code=404, detail="El tipo de documento no existe")

    if archivo.content_type not in MIME_PERMITIDOS:
        raise HTTPException(
            status_code=422,
            detail="Formato no admitido. Subí JPG, PNG, WEBP o PDF.",
        )

    contenido = await archivo.read()
    if not contenido:
        raise HTTPException(status_code=422, detail="El archivo está vacío")
    if len(contenido) > MAX_BYTES:
        raise HTTPException(status_code=422, detail="El archivo supera el límite de 15 MB")

    _, ext = MIME_PERMITIDOS[archivo.content_type]
    es_publico = tipo.nombre in (TIPO_FOTO, "Catálogo Digital")
    bucket = BUCKET_PUBLICO if es_publico else BUCKET_DOCUMENTOS
    ruta_storage = f"obras/{id_obra}/{uuid.uuid4()}{ext}"

    sb = get_supabase()
    try:
        sb.storage.from_(bucket).upload(
            path=ruta_storage,
            file=contenido,
            file_options={"content-type": archivo.content_type, "upsert": "false"},
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error al subir a Supabase Storage: {exc}")

    if es_publico:
        url_guardada = sb.storage.from_(bucket).get_public_url(ruta_storage)
    else:
        url_guardada = f"supabase://{bucket}/{ruta_storage}"

    try:
        documento = agregar_documento(
            db,
            obra,
            id_tipo_documento,
            url=url_guardada,
            bucket=bucket,
            ruta_storage=ruta_storage,
        )
        if marcar_digitalizada:
            obra.digitalizada = True
        db.commit()
    except Exception:
        db.rollback()
        try:
            sb.storage.from_(bucket).remove([ruta_storage])
        except Exception:
            pass
        raise HTTPException(
            status_code=500, detail="Error al registrar en la base; se revirtió el archivo subido"
        )

    db.refresh(documento)
    return documento


def listar_documentos(db: Session, id_obra: uuid.UUID) -> list[Documento]:
    if db.get(Obra, id_obra) is None:
        raise HTTPException(status_code=404, detail="La obra no existe")
    consulta = (
        select(Documento)
        .where(Documento.id_obra == id_obra, Documento.fecha_baja.is_(None))
        .order_by(Documento.id)
    )
    return list(db.scalars(consulta).all())

def eliminar_documento(db: Session, id_documento: uuid.UUID) -> None:
    doc = db.get(Documento, id_documento)
    if doc is None or doc.fecha_baja is not None:
        raise HTTPException(status_code=404, detail="El documento no existe o ya fue eliminado")

    # Si estaba guardado en Supabase Storage, lo borramos del bucket
    if doc.bucket and doc.ruta_storage:
        try:
            sb = get_supabase()
            sb.storage.from_(doc.bucket).remove([doc.ruta_storage])
        except Exception:
            pass  # Si ya no existía en Storage, continuamos igual con la baja en DB

    doc.fecha_baja = datetime.now(timezone.utc)
    obra = db.get(Obra, doc.id_obra)

    # Si era una foto y la obra se queda sin fotos activas, quitamos la marca de digitalizada
    if obra and doc.tipo.nombre == TIPO_FOTO:
        quedan_fotos = any(
            d.id != doc.id
            and d.fecha_baja is None
            and d.url.split("?")[0].lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            for d in obra.documentos
        )
        if not quedan_fotos:
            obra.digitalizada = False

    _guardar(db)