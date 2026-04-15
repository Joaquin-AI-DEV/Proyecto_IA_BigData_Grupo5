"""
load_db.py — Capa de almacenamiento: inserción en Supabase (PostgreSQL)
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Responsabilidad:
    Recibe los DataFrames limpios (productos y ventas) y los inserta
    en la base de datos Supabase usando psycopg2 (PostgreSQL).

    También contiene la función de creación de tablas si no existen,
    lo que permite arrancar el sistema desde cero con una sola ejecución.

Configuración necesaria (archivo .env en la raíz del proyecto):
    DB_HOST     = <host de Supabase, p.ej. db.xxxx.supabase.co>
    DB_PORT     = 5432
    DB_NAME     = postgres
    DB_USER     = postgres
    DB_PASSWORD = <contraseña del proyecto Supabase>

Nota sobre Supabase:
    Se eligió Supabase (PostgreSQL) frente a MySQL/XAMPP porque ofrece
    una instancia gratuita accesible remotamente, lo que facilita la
    integración con el dashboard y el modelo de predicción sin depender
    de que un servidor local esté levantado.
"""

import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from database import get_connection


# Cargar variables de entorno desde el archivo .env
load_dotenv()


def create_tables(conn) -> None:
    """
    Crea las tres tablas del modelo de datos si no existen ya.

    Tablas creadas:
        - productos
        - ventas
        - predicciones (vacía, para uso del módulo de ML)

    Parámetros:
        conn: Conexión activa de psycopg2.
    """

    sql_create = """
        -- Tabla de productos (catálogo)
        CREATE TABLE IF NOT EXISTS productos (
            id_producto     VARCHAR(20)     PRIMARY KEY,
            nombre          VARCHAR(255)    NOT NULL,
            categoria       VARCHAR(100)    DEFAULT 'Sin categoría',
            precio_unitario DECIMAL(10, 2)  NOT NULL
        );

        -- Tabla de ventas (transacciones históricas)
        CREATE TABLE IF NOT EXISTS ventas (
            id_venta            SERIAL          PRIMARY KEY,
            id_venta_original   VARCHAR(20),
            id_producto         VARCHAR(20)     REFERENCES productos(id_producto),
            fecha_venta         DATE            NOT NULL,
            unidades_vendidas   INT             NOT NULL CHECK (unidades_vendidas > 0),
            total_venta         DECIMAL(10, 2)  NOT NULL
        );

        -- Tabla de predicciones (la rellena el módulo ML de Deninson)
        CREATE TABLE IF NOT EXISTS predicciones (
            id_prediccion       SERIAL          PRIMARY KEY,
            id_producto         VARCHAR(20)     REFERENCES productos(id_producto),
            fecha_prediccion    DATE            NOT NULL,
            unidades_predichas  INT,
            unidades_vendidas   INT,
            confianza_modelo    DECIMAL(5, 4)
        );
    """

    with conn.cursor() as cur:
        cur.execute(sql_create)
    conn.commit()
    print("[DB] Tablas creadas o ya existentes: productos, ventas, predicciones.")


def insert_productos(conn, df_productos: pd.DataFrame) -> None:
    """
    Inserta el catálogo de productos en la tabla 'productos'.
    Usa ON CONFLICT DO NOTHING para evitar errores por duplicados
    si el pipeline se ejecuta varias veces.

    Parámetros:
        conn: Conexión activa de psycopg2.
        df_productos (pd.DataFrame): DataFrame con columnas:
            id_producto, nombre, categoria, precio_unitario
    """

    # Convertir a lista de tuplas para la inserción en lote
    records = list(df_productos.itertuples(index=False, name=None))

    sql = """
        INSERT INTO productos (id_producto, nombre, categoria, precio_unitario)
        VALUES %s
        ON CONFLICT (id_producto) DO NOTHING;
    """

    with conn.cursor() as cur:
        execute_values(cur, sql, records)
    conn.commit()

    print(f"[DB] Productos insertados: {len(records)} registros.")


def insert_ventas(conn, df_ventas: pd.DataFrame, batch_size: int = 5000) -> None:
    """
    Inserta los registros de ventas en la tabla 'ventas' por lotes.
    Se inserta por lotes para no saturar la memoria ni la conexión
    con un dataset de más de 500.000 filas.

    Parámetros:
        conn: Conexión activa de psycopg2.
        df_ventas (pd.DataFrame): DataFrame con columnas:
            id_venta_original, id_producto, fecha_venta,
            unidades_vendidas, total_venta
        batch_size (int): Número de filas por lote. Por defecto 5.000.
    """

    total = len(df_ventas)
    insertados = 0

    sql = """
        INSERT INTO ventas
            (id_venta_original, id_producto, fecha_venta, unidades_vendidas, total_venta)
        VALUES %s;
    """

    with conn.cursor() as cur:
        # Iterar en lotes para no bloquear memoria
        for inicio in range(0, total, batch_size):
            lote = df_ventas.iloc[inicio: inicio + batch_size]
            records = list(lote.itertuples(index=False, name=None))
            execute_values(cur, sql, records)
            insertados += len(records)
            print(f"[DB] Ventas insertadas: {insertados}/{total}...")

    conn.commit()
    print(f"[DB] Total ventas insertadas: {insertados} registros.")


def close_connection(conn) -> None:
    """
    Cierra la conexión a la base de datos de forma limpia.

    Parámetros:
        conn: Conexión activa de psycopg2.
    """
    if conn and not conn.closed:
        conn.close()
        print("[DB] Conexión cerrada correctamente.")
