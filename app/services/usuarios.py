from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Rol, Usuario
from ..roles import ROL_PUBLICO


def a_dto(u: Usuario) -> dict:
    return {
        "id": u.id,
        "id_externo": u.id_externo,
        "nombre": u.nombre,
        "id_rol": u.id_rol,
        "rol": u.rol.nombre,
    }


def obtener_o_crear_por_id_externo(db: Session, id_externo: str) -> Usuario:
    """
    Primer acceso: quien ya se autenticó en Authly pero todavía no existe en el museo
    entra con el rol de menor privilegio (Público General); un Administrador lo puede promover.
    """
    consulta = select(Usuario).where(Usuario.id_externo == id_externo)
    usuario = db.scalars(consulta).first()
    if usuario is not None:
        return usuario

    rol = db.scalars(select(Rol).where(Rol.nombre == ROL_PUBLICO)).first()
    if rol is None or not rol.vigente:
        raise HTTPException(status_code=500, detail="Falta configurar el rol Público General")
    db.add(Usuario(id_externo=id_externo, id_rol=rol.id))
    try:
        db.commit()
    except IntegrityError:  # otra petición lo creó justo al mismo tiempo
        db.rollback()
    return db.scalars(consulta).one()