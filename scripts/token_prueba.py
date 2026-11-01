"""
Genera un token de PRUEBA firmado con una clave propia (NO es de Authly).

    python -m scripts.token_prueba              # usuario de prueba por defecto
    python -m scripts.token_prueba <sub-uuid>   # otro usuario de prueba

La primera vez crea claves/prueba_privada.pem y claves/prueba_publica.pem.
Para que la API acepte estos tokens, en la misma ventana donde corre uvicorn:

    $env:AUTHLY_PUBLIC_KEY_PATH = "claves\\prueba_publica.pem"

Nunca subas la clave privada de prueba a un repositorio.
"""
import os
import sys
import time
import uuid
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

CARPETA = Path(__file__).resolve().parent.parent / "claves"
PRIVADA = CARPETA / "prueba_privada.pem"
PUBLICA = CARPETA / "prueba_publica.pem"
SUB_POR_DEFECTO = "11111111-1111-4111-8111-111111111111"


def asegurar_claves() -> None:
    if PRIVADA.exists() and PUBLICA.exists():
        return
    CARPETA.mkdir(exist_ok=True)
    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    PRIVADA.write_bytes(
        clave.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    PUBLICA.write_bytes(
        clave.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def generar_token(sub: str, app_id: str, horas: int = 8) -> str:
    ahora = int(time.time())
    payload = {
        "sub": sub,
        "type": "user",
        "org_id": str(uuid.uuid4()),
        "app_id": app_id,
        "iat": ahora,
        "exp": ahora + horas * 3600,
    }
    return jwt.encode(payload, PRIVADA.read_text(), algorithm="RS256")


if __name__ == "__main__":
    asegurar_claves()
    sub = sys.argv[1] if len(sys.argv) > 1 else SUB_POR_DEFECTO
    app_id = os.getenv("AUTHLY_APP_ID", "app-de-prueba")
    print(f"sub:   {sub}")
    print(f"token: {generar_token(sub, app_id)}")