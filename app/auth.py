"""
Autenticación PROVISORIA.

El login real lo hace otro equipo y los roles los define el CU-15. Mientras tanto el rol llega
en el header `X-Rol` (publico | investigador | administrador). Cualquiera puede mandar
cualquier valor: sirve solo para desarrollo. Cuando exista el login real, hay que reemplazar
solamente el cuerpo de `rol_actual`; el resto de la aplicación no se entera.
"""
from fastapi import Header, HTTPException

ROL_ADMIN = "Administrador"
ROL_INVESTIGADOR = "Investigador"
ROL_PUBLICO = "Público General"

# El header va sin tildes ni espacios para no depender de cómo lo codifique cada cliente
_ROLES_POR_HEADER = {
    "administrador": ROL_ADMIN,
    "investigador": ROL_INVESTIGADOR,
    "publico": ROL_PUBLICO,
}


def rol_actual(x_rol: str | None = Header(default=None)) -> str:
    rol = _ROLES_POR_HEADER.get((x_rol or "").strip().lower())
    if rol is None:
        raise HTTPException(status_code=401, detail="No autenticado: falta un rol válido")
    return rol