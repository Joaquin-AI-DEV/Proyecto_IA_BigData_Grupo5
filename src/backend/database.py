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
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()


def get_connection():
    """
    Crea y devuelve una conexión a PostgreSQL en Supabase.

    Retorna:
        psycopg2.connection: Conexión activa con cursor tipo diccionario.

    Excepciones:
        psycopg2.OperationalError: Si no hay conexión o las credenciales son incorrectas.
    """
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 6543)),
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres.nbamabcfxtcltbzxuncg"),
        password=os.getenv("DB_PASSWORD"),
        sslmode="require",
        cursor_factory=RealDictCursor,
    )
    return conn
