"""
run_pipeline.py — Orquestador del pipeline de datos
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Responsabilidad:
    Punto de entrada único del pipeline end-to-end.
    Ejecuta en orden:
        1. Ingesta            → ingest.py
        2. Limpieza           → clean.py
        3. Carga de datos BD  → load_db.py (productos + ventas)
        4. Entrenamiento ML   → models/train_model.py
        5. Carga predicciones → load_db.py (tabla predicciones, para el dashboard)

    También guarda una copia del dataset limpio en data/processed/
    que consume el módulo de ML.

Uso:
    python src/pipeline/run_pipeline.py --input data/raw/online_retail.xlsx
    python src/pipeline/run_pipeline.py --input data/raw/online_retail.csv
"""

import argparse
import os
import sys

# Añadimos la raíz del proyecto al path para poder hacer imports con "src.*"
# desde cualquier sitio (útil cuando lo ejecutáis desde la raíz del repo).
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# get_connection vive en src/backend/database.py y lo reutilizamos aquí.
from src.backend.database import get_connection
from src.pipeline.ingest import load_dataset
from src.pipeline.clean import clean_and_normalize, split_productos_ventas
from src.pipeline.load_db import (
    create_tables,
    insert_productos,
    insert_ventas,
    insert_predicciones,
    close_connection,
)
from src.models.train_model import run_training


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
        5. Conecta a Supabase, crea tablas e inserta productos y ventas.
        6. Entrena el modelo Ridge sobre el CSV limpio.
        7. Inserta las predicciones en la tabla 'predicciones' para el dashboard.

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
    print("\n>>> PASO 5: Inserción en Supabase (productos + ventas)")
    conn = None
    try:
        conn = get_connection()
        # create_tables hace DROP + CREATE, así cada ejecución refleja
        # exactamente el CSV de entrada y garantiza el esquema correcto.
        create_tables(conn)
        insert_productos(conn, df_productos)
        insert_ventas(conn, df_ventas)

        # ---- PASO 6: ENTRENAMIENTO DEL MODELO ----
        # Encadenamos el train_model aquí: entrena Ridge y nos devuelve el
        # DataFrame de predicciones listo para subirlo a BD.
        print("\n>>> PASO 6: Entrenamiento del modelo (Ridge)")
        df_pred = run_training(PROCESSED_PATH)

        # ---- PASO 7: INSERCIÓN DE PREDICCIONES EN BD ----
        # Push final: el dashboard leerá esta tabla para pintar las gráficas.
        print("\n>>> PASO 7: Inserción de predicciones en Supabase")
        insert_predicciones(conn, df_pred)
    except Exception as e:
        print(f"\n[ERROR] Fallo durante la fase BD/entrenamiento: {e}")
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
