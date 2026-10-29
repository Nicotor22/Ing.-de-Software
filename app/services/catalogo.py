from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..auth import ROL_ADMIN, ROL_INVESTIGADOR, ROL_PUBLICO
from ..models import Documento, Obra, ObraAutor, Exposicion

MENSAJE_SIN_RESULTADOS = (
    "No hay obras que coincidan con los filtros aplicados. "
    "Probá ampliar la búsqueda (por ejemplo, quitando algún filtro)."
)

# Tipos de documento visibles por rol. Los nombres tienen que coincidir con los precargados.
TIPOS_PUBLICO = {"Foto"}
TIPOS_INVESTIGADOR = TIPOS_PUBLICO | {
    "Catálogo Digital", "Certificado de Autenticidad", "Informe de Restauración",
}
TIPOS_VISIBLES = {
    ROL_PUBLICO: TIPOS_PUBLICO,
    ROL_INVESTIGADOR: TIPOS_INVESTIGADOR,
    ROL_ADMIN: None,  # None = todos
}


def a_dto(obra: Obra, rol: str) -> dict:
    """
    Se arma el diccionario SOLO con los campos del nivel del rol: lo que no corresponde nunca
    entra, ni siquiera como null (extensión del paso 4: no se insinúan datos ocultos).
    Un rol desconocido recibe el nivel más restrictivo.
    """
    visibles = TIPOS_VISIBLES.get(rol, TIPOS_PUBLICO)
    dto = {
        "id": obra.id,
        "titulo": obra.titulo,
        "autores": [oa.autor.nombre for oa in obra.autores],
        "periodo": obra.periodo,
        "documentos": [
            {"tipo": d.tipo.nombre, "url": d.url, "formato": d.formato}
            for d in obra.documentos
            if visibles is None or d.tipo.nombre in visibles
        ],
    }
    if rol not in (ROL_INVESTIGADOR, ROL_ADMIN):
        return dto

    dto.update(
        {
            "tecnica": obra.tecnica,
            "alto": obra.alto,
            "ancho": obra.ancho,
            "profundidad": obra.profundidad,
            "estado_conservacion": obra.estado_conservacion,
            "coleccion": obra.coleccion.nombre if obra.coleccion else None,
        }
    )
    if rol != ROL_ADMIN:
        return dto

    dto.update(
        {
            "modo_ingreso": obra.modo_ingreso,
            "ubicacion_actual": obra.ubicacion_actual.nombre,
        }
    )
    return dto


def _con_relaciones(consulta):
    return consulta.options(
        selectinload(Obra.autores).selectinload(ObraAutor.autor),
        selectinload(Obra.documentos).selectinload(Documento.tipo),
        selectinload(Obra.coleccion),
        selectinload(Obra.ubicacion_actual),
    )


def buscar_obras(
    db: Session,
    rol: str,
    *,
    autor_id: int | None,
    tecnica: str | None,
    periodo: str | None,
    coleccion_id: int | None,
    limit: int,
    offset: int,
) -> dict:
    tecnica = tecnica.strip() if tecnica else None
    periodo = periodo.strip() if periodo else None

    # Solo obras digitalizadas (CU-12 las habilita para consulta pública)
    consulta = select(Obra).where(Obra.digitalizada.is_(True))
    if autor_id is not None:
        consulta = consulta.where(Obra.autores.any(ObraAutor.id_autor == autor_id))
    if tecnica:
        consulta = consulta.where(Obra.tecnica.ilike(f"%{tecnica}%"))
    if periodo:
        # PROVISORIO: igual que en el reporte (CU-11) hasta definir qué es "periodo"
        consulta = consulta.where(func.lower(Obra.periodo) == periodo.lower())
    if coleccion_id is not None:
        consulta = consulta.where(Obra.id_coleccion == coleccion_id)

    total = db.scalar(select(func.count()).select_from(consulta.subquery()))
    if total == 0:
        # Extensión del paso 3. Un id inexistente también termina acá: no se revela nada
        return {"total": 0, "resultados": [], "mensaje": MENSAJE_SIN_RESULTADOS}

    obras = db.scalars(
        _con_relaciones(consulta.order_by(Obra.titulo, Obra.id)).limit(limit).offset(offset)
    ).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "resultados": [a_dto(o, rol) for o in obras],
    }


def detalle_obra(db: Session, rol: str, obra_id: int) -> dict:
    consulta = _con_relaciones(
        select(Obra).where(Obra.id == obra_id, Obra.digitalizada.is_(True))
    )
    obra = db.scalars(consulta).first()
    if obra is None:
        # Una obra sin digitalizar se trata igual que una inexistente: no se insinúa nada
        raise HTTPException(status_code=404, detail="La obra no existe en el catálogo")
    return a_dto(obra, rol)

def listar_exposiciones_virtuales(db: Session) -> dict:
    exposiciones = db.scalars(
        select(Exposicion)
        .where(Exposicion.publicada_virtual.is_(True))
        .order_by(Exposicion.fecha_inicio.desc())
    ).all()
    return {
        "total": len(exposiciones),
        "resultados": [
            {"id": e.id, "nombre": e.nombre, "fecha_inicio": e.fecha_inicio, "fecha_fin": e.fecha_fin}
            for e in exposiciones
        ],
    }

def detalle_exposicion_virtual(db: Session, rol: str, exposicion_id: int) -> dict:
    exposicion = db.get(Exposicion, exposicion_id)
    if exposicion is None or not exposicion.publicada_virtual:
        # Una exposición sin publicar se trata igual que una inexistente
        raise HTTPException(status_code=404, detail="La exposición virtual no existe")

    ids = [eo.id_obra for eo in exposicion.obras]
    # Solo obras digitalizadas, y con el nivel de detalle del rol (igual que el catálogo)
    obras = db.scalars(
        _con_relaciones(
            select(Obra).where(Obra.id.in_(ids), Obra.digitalizada.is_(True))
        ).order_by(Obra.titulo, Obra.id)
    ).all()
    return {
        "id": exposicion.id,
        "nombre": exposicion.nombre,
        "fecha_inicio": exposicion.fecha_inicio,
        "fecha_fin": exposicion.fecha_fin,
        "obras": [a_dto(o, rol) for o in obras],
    }