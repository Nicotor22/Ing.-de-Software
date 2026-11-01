import logging
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import AUTHLY_APP_ID, cargar_clave_publica
from .database import get_db
from .models import Usuario
from .roles import ROL_ADMIN, ROL_INVESTIGADOR, ROL_PUBLICO  # noqa: F401 (los usan otros módulos)
from .services import usuarios as servicio_usuarios

logger = logging.getLogger(__name__)

CLAVE_PUBLICA = cargar_clave_publica()  # si falta el archivo, la app no arranca
if not AUTHLY_APP_ID:
    logger.warning("AUTHLY_APP_ID no está definido: NO se valida a qué aplicación pertenece el token")

esquema_bearer = HTTPBearer(auto_error=False)  # habilita el botón "Authorize" en /docs


def verificar_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            CLAVE_PUBLICA,
            algorithms=["RS256"],  # fijo: nunca se acepta otro algoritmo
            options={"require": ["exp", "sub"]},
            leeway=10,  # tolera unos segundos de diferencia entre relojes
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token expiró: volvé a iniciar sesión")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Authly atiende a varias aplicaciones con la misma clave: hay que comprobar
    # que el token sea para ESTA aplicación
    if AUTHLY_APP_ID and payload.get("app_id") != AUTHLY_APP_ID:
        raise HTTPException(status_code=401, detail="El token no corresponde a esta aplicación")
    try:
        payload["sub"] = str(UUID(str(payload["sub"])))  # solo normaliza el texto del sub
    except ValueError:
        raise HTTPException(status_code=401, detail="Token inválido")
    return payload


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if credenciales is None:
        raise HTTPException(
            status_code=401,
            detail="No autenticado: falta el token (Authorization: Bearer ...)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verificar_token(credenciales.credentials)
    usuario = servicio_usuarios.obtener_o_crear_por_id_externo(db, payload["sub"])
    if not usuario.rol.vigente:
        raise HTTPException(status_code=403, detail="Tu rol fue dado de baja: consultá a un Administrador")
    return usuario


def rol_actual(usuario: Usuario = Depends(usuario_actual)) -> str:
    """Es lo que usa el catálogo (CU-13): no hace falta tocar ese código."""
    return usuario.rol.nombre