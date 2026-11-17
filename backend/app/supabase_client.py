import os
from supabase import Client, create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")

BUCKET_PUBLICO = "museo_publico"
BUCKET_DOCUMENTOS = "museo_documentos"


def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SECRET_KEY en el entorno")
    return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)