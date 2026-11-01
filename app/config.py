import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

AUTHLY_PUBLIC_KEY_PATH = Path(
    os.getenv("AUTHLY_PUBLIC_KEY_PATH", RAIZ / "claves" / "authly_public.pem")
)
AUTHLY_APP_ID = os.getenv("AUTHLY_APP_ID")  # el id de NUESTRA aplicación en Authly


def cargar_clave_publica() -> str:
    if not AUTHLY_PUBLIC_KEY_PATH.exists():
        raise RuntimeError(f"No se encontró la clave pública de Authly en {AUTHLY_PUBLIC_KEY_PATH}")
    return AUTHLY_PUBLIC_KEY_PATH.read_text()