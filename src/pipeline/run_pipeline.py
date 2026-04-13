"""
run_pipeline.py — Orquestador del pipeline de datos
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Responsabilidad:
    Punto de entrada único del pipeline de datos.
    Ejecuta en orden las tres capas:
        1. Ingesta   → ingest.py
        2. Limpieza  → clean.py
        3. Carga BD  → load_db.py

    También guarda una copia del dataset limpio en data/processed/
    para que el módulo de ML (Deninson) pueda usarlo sin tocar la BD.

Uso:
    python src/pipeline/run_pipeline.py --input data/raw/online_retail.xlsx
    python src/pipeline/run_pipeline.py --input data/raw/online_retail.csv
"""

import argparse
import os
import sys
import pandas as pd

# Añadir el directorio raíz al path para importar módulos del proyecto
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.pipeline.ingest import load_dataset
from src.pipeline.clean import clean_and_normalize, split_productos_ventas
from src.pipeline.load_db import (
    get_connection,
    create_tables,
    insert_productos,
    insert_ventas,
    close_connection,
)


# Ruta donde se guarda el dataset procesado para el módulo ML
PROCESSED_PATH = os.path.join("data", "processed", "ventas_limpias.csv")


def run_pipeline(filepath: str) -> None:
    """
    Ejecuta el pipeline completo de datos.

    Pasos:
        1. Carga el dataset desde la ruta indicada.
        2. Aplica limpieza y normalización.
        3. Separa en tablas Productos y Ventas.
        4. Guarda el dataset limpio como CSV para el módulo ML.
        5. Conecta a Supabase, crea tablas si no existen e inserta los datos.

    Parámetros:
        filepath (str): Ruta al archivo CSV o XLSX de entrada.
    """

    print("\n" + "=" * 60)
    print("   STOCKPULSE — Pipeline de datos")
    print("=" * 60 + "\n")

    # ---- PASO 1: INGESTA ----
    print(">>> PASO 1: Ingesta de datos")
    df_raw = load_dataset(filepath)

    # ---- PASO 2: LIMPIEZA ----
    print("\n>>> PASO 2: Limpieza y normalización")
    df_clean = clean_and_normalize(df_raw)

    # ---- PASO 3: SEPARACIÓN EN TABLAS ----
    print("\n>>> PASO 3: Separación en tablas Productos / Ventas")
    df_productos, df_ventas = split_productos_ventas(df_clean)

    # ---- PASO 4: GUARDAR CSV LIMPIO PARA ML ----
    print("\n>>> PASO 4: Guardando dataset limpio para módulo ML")
    os.makedirs(os.path.dirname(PROCESSED_PATH), exist_ok=True)
    df_clean.to_csv(PROCESSED_PATH, index=False, encoding="utf-8")
    print(f"[PIPELINE] Dataset limpio guardado en: {PROCESSED_PATH}")

    # ---- PASO 5: INSERCIÓN EN BASE DE DATOS ----
    print("\n>>> PASO 5: Inserción en Supabase (PostgreSQL)")
    conn = None
    try:
        conn = get_connection()
        create_tables(conn)
        insert_productos(conn, df_productos)
        insert_ventas(conn, df_ventas)
    except Exception as e:
        print(f"\n[ERROR] Fallo durante la inserción en BD: {e}")
        print("[INFO] Los datos limpios sí se guardaron en data/processed/")
        raise
    finally:
        close_connection(conn)

    print("\n" + "=" * 60)
    print("   Pipeline completado con éxito.")
    print("=" * 60 + "\n")


# ---- Punto de entrada por línea de comandos ----
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="StockPulse — Pipeline de ingesta, limpieza y carga de datos."
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Ruta al archivo de datos (CSV o XLSX). Ej: data/raw/online_retail.xlsx",
    )
    args = parser.parse_args()
    run_pipeline(args.input)
