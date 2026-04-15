"""
database.py — Gestión de conexión a Supabase (PostgreSQL)
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Responsabilidad:
    Provee una función de conexión centralizada para que todos los
    módulos del backend usen la misma configuración sin repetir código.
    Las credenciales se cargan desde el archivo .env en la raíz del proyecto.
"""

import os
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Resolver la ruta al .env de forma independiente al CWD.
# Estructura: <proyecto>/src/backend/database.py  →  <proyecto>/environment/.env
ENV_PATH = Path(__file__).resolve().parents[2] / "environment" / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def get_connection():
    """
    Crea y devuelve una conexión a PostgreSQL en Supabase.

    Retorna:
        psycopg2.connection: Conexión activa con cursor tipo diccionario.

    Excepciones:
        RuntimeError: Si faltan variables obligatorias en el .env.
        psycopg2.OperationalError: Si no hay conexión o las credenciales son incorrectas.
    """
    host     = os.getenv("DB_HOST")
    user     = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if not (host and user and password):
        raise RuntimeError(
            f"Faltan variables en {ENV_PATH}. Requeridas: DB_HOST, DB_USER, DB_PASSWORD. "
            "Copia environment/.env.example a environment/.env y rellénalo."
        )

    return psycopg2.connect(
        host=host,
        port=int(os.getenv("DB_PORT", 6543)),
        dbname=os.getenv("DB_NAME", "postgres"),
        user=user,
        password=password,
        sslmode="require",
        cursor_factory=RealDictCursor,
    )
