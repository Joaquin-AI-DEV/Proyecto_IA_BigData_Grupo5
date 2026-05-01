"""
load_db.py — Capa de almacenamiento: inserción en Supabase (PostgreSQL)
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Responsabilidad:
    Recibe los DataFrames limpios (productos y ventas) y los inserta
    en la base de datos Supabase usando psycopg2 (PostgreSQL).

    También contiene la función de inicialización de tablas, que crea
    las tablas si no existen y vacía su contenido antes de cada carga.

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

Cambios Fase 3:
    - create_tables() ya no hace DROP TABLE.
      Ahora crea las tablas solo si no existen (CREATE TABLE IF NOT EXISTS)
      y las vacía con TRUNCATE ... RESTART IDENTITY CASCADE antes de cada
      carga. Esto preserva el esquema, los índices y las Foreign Keys, y
      es la práctica estándar en pipelines de recarga completa.
"""

import pandas as pd
from psycopg2.extras import execute_values


def create_tables(conn) -> None:
    """
    Garantiza que las tres tablas del modelo existen y están vacías
    antes de iniciar la carga.

    Estrategia Fase 3 — TRUNCATE en lugar de DROP + CREATE:
        En Fase 2 se usaba DROP TABLE ... CASCADE seguido de CREATE TABLE.
        Eso funcionaba pero tenía dos inconvenientes:
          1. Destruía el esquema (índices, constraints) en cada ejecución.
          2. Era más lento porque PostgreSQL tenía que recompilar el catálogo.

        Ahora usamos:
          - CREATE TABLE IF NOT EXISTS: crea la tabla solo la primera vez.
          - TRUNCATE ... RESTART IDENTITY CASCADE: borra todos los datos,
            reinicia los contadores SERIAL y respeta el orden de FK
            (CASCADE vacía primero las tablas hijas).

        El resultado es el mismo desde el punto de vista del pipeline
        (tablas siempre limpias antes de insertar) pero el esquema
        permanece intacto entre ejecuciones.

    Tablas gestionadas:
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

    # TRUNCATE en orden inverso al de las FK para respetar la integridad
    # referencial: primero las tablas hijas, luego la tabla padre.
    # RESTART IDENTITY reinicia los contadores SERIAL (id_venta, id_prediccion).
    # CASCADE propaga el vaciado a cualquier tabla que dependa de las anteriores.
    sql_truncate = """
        TRUNCATE TABLE predicciones, ventas, productos
        RESTART IDENTITY CASCADE;
    """

    with conn.cursor() as cur:
        # Paso 1: crear tablas si no existen
        cur.execute(sql_create)
        conn.commit()
        print("[DB] Tablas verificadas (CREATE IF NOT EXISTS).")

        # Paso 2: vaciar datos manteniendo el esquema intacto
        cur.execute(sql_truncate)
    conn.commit()
    print("[DB] Tablas vaciadas con TRUNCATE RESTART IDENTITY CASCADE.")


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
