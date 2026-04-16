"""
load_db.py — Capa de almacenamiento: inserción en Supabase (PostgreSQL)
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Responsabilidad:
    Recibe los DataFrames limpios (productos y ventas) y los inserta
    en la base de datos Supabase usando psycopg2 (PostgreSQL).

    También contiene la función de creación de tablas si no existen,
    lo que permite arrancar el sistema desde cero con una sola ejecución.

Configuración necesaria (archivo environment/.env en la raíz del proyecto):
    DB_HOST     = <host de Supabase, p.ej. aws-0-eu-west-1.pooler.supabase.com>
    DB_PORT     = 6543
    DB_NAME     = postgres
    DB_USER     = <usuario del proyecto Supabase>
    DB_PASSWORD = <contraseña del proyecto Supabase>

Nota sobre Supabase:
    Se eligió Supabase (PostgreSQL) frente a MySQL/XAMPP porque ofrece
    una instancia gratuita accesible remotamente, lo que facilita la
    integración con el dashboard y el modelo de predicción sin depender
    de que un servidor local esté levantado.
"""

import pandas as pd
from psycopg2.extras import execute_values


def create_tables(conn) -> None:
    """
    Recrea desde cero las tres tablas del modelo de datos.

    Primero hace DROP TABLE IF EXISTS ... CASCADE para eliminar versiones
    antiguas del esquema (por ejemplo si una ejecución previa creó
    id_producto como INTEGER en lugar de VARCHAR) y a continuación las
    crea con el esquema correcto. De esta forma el esquema del código
    es siempre la única fuente de verdad.

    Como el pipeline ya reescribe todo el dataset en cada ejecución,
    borrar las tablas no supone pérdida de información real.

    Tablas creadas:
        - productos
        - ventas
        - predicciones (vacía, para uso del módulo de ML)

    Parámetros:
        conn: Conexión activa de psycopg2.
    """

    sql_create = """
        -- Se eliminan antes de crear para garantizar el esquema correcto
        DROP TABLE IF EXISTS predicciones, ventas, productos CASCADE;

        -- Tabla de productos (catálogo)
        CREATE TABLE productos (
            id_producto     VARCHAR(20)     PRIMARY KEY,
            nombre          VARCHAR(255)    NOT NULL,
            categoria       VARCHAR(100)    DEFAULT 'Sin categoría',
            precio_unitario DECIMAL(10, 2)  NOT NULL
        );

        -- Tabla de ventas (transacciones históricas)
        CREATE TABLE ventas (
            id_venta            SERIAL          PRIMARY KEY,
            id_venta_original   VARCHAR(20),
            id_producto         VARCHAR(20)     REFERENCES productos(id_producto),
            fecha_venta         DATE            NOT NULL,
            unidades_vendidas   INT             NOT NULL CHECK (unidades_vendidas > 0),
            total_venta         DECIMAL(10, 2)  NOT NULL
        );

        -- Tabla de predicciones (la rellena el módulo ML de Deninson)
        CREATE TABLE predicciones (
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
    print("[DB] Tablas recreadas desde cero: productos, ventas, predicciones.")


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


def insert_predicciones(conn, df_pred: pd.DataFrame) -> None:
    """
    Vuelca las predicciones del modelo agregado (diario, sin id_producto)
    en la tabla 'predicciones' para que el dashboard las consuma.

    Idempotente: antes de insertar elimina las filas previas de este modelo
    agregado (aquellas con id_producto IS NULL), para que múltiples
    ejecuciones del pipeline no dupliquen registros.

    Parámetros:
        conn: Conexión activa de psycopg2.
        df_pred (pd.DataFrame): Columnas fecha, ventas_reales, ventas_predichas.
    """
    if df_pred is None or df_pred.empty:
        print("[DB] No hay predicciones que insertar.")
        return

    # id_producto = None porque el modelo es agregado (predice la demanda
    # diaria total, no por producto). Ver memoria Fase 2 para la justificación.
    records = [
        (
            None,
            row.fecha,
            int(round(row.ventas_predichas)),
            int(round(row.ventas_reales)),
            None,
        )
        for row in df_pred.itertuples(index=False)
    ]

    with conn.cursor() as cur:
        cur.execute("DELETE FROM predicciones WHERE id_producto IS NULL;")
        execute_values(
            cur,
            """
            INSERT INTO predicciones
                (id_producto, fecha_prediccion, unidades_predichas,
                 unidades_vendidas, confianza_modelo)
            VALUES %s;
            """,
            records,
        )
    conn.commit()
    print(f"[DB] Predicciones insertadas: {len(records)} registros.")


def close_connection(conn) -> None:
    """
    Cierra la conexión a la base de datos de forma limpia.

    Parámetros:
        conn: Conexión activa de psycopg2.
    """
    if conn and not conn.closed:
        conn.close()
        print("[DB] Conexión cerrada correctamente.")
