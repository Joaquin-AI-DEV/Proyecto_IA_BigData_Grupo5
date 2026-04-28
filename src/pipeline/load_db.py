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


def insert_predicciones(conn, df_pred: pd.DataFrame, batch_size: int = 5000) -> None:
    """
    Inserta las predicciones per-producto en la tabla 'predicciones'.

    El modelo se entrena sobre la serie agregada diaria por robustez
    estadística (la mayoría de SKUs tienen histórico escaso). El
    orquestador run_pipeline.py descompone las predicciones globales
    per-producto aplicando la cuota histórica de ventas de cada SKU y
    pasa aquí el DataFrame ya explotado.

    Parámetros:
        conn: Conexión activa de psycopg2.
        df_pred (pd.DataFrame): Columnas requeridas:
            id_producto, fecha, unidades_predichas, unidades_vendidas, confianza
        batch_size (int): Filas por lote. Necesario porque el cross-join
            de SKUs × días predichos genera cientos de miles de filas.
    """
    if df_pred is None or df_pred.empty:
        print("[DB] No hay predicciones que insertar.")
        return

    records = [
        (
            row.id_producto,
            row.fecha,
            int(round(row.unidades_predichas)),
            int(round(row.unidades_vendidas)),
            float(row.confianza) if row.confianza is not None else None,
        )
        for row in df_pred.itertuples(index=False)
    ]

    sql = """
        INSERT INTO predicciones
            (id_producto, fecha_prediccion, unidades_predichas,
             unidades_vendidas, confianza_modelo)
        VALUES %s;
    """

    total = len(records)
    insertados = 0
    with conn.cursor() as cur:
        for inicio in range(0, total, batch_size):
            lote = records[inicio: inicio + batch_size]
            execute_values(cur, sql, lote)
            insertados += len(lote)
            print(f"[DB] Predicciones insertadas: {insertados}/{total}...")
    conn.commit()
    print(f"[DB] Total predicciones insertadas: {total} registros.")


def close_connection(conn) -> None:
    """
    Cierra la conexión a la base de datos de forma limpia.

    Parámetros:
        conn: Conexión activa de psycopg2.
    """
    if conn and not conn.closed:
        conn.close()
        print("[DB] Conexión cerrada correctamente.")
