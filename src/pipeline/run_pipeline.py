"""
run_pipeline.py — Orquestador del pipeline de datos
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Responsabilidad:
    Punto de entrada único del pipeline end-to-end.
    Ejecuta en orden:
        1. Ingesta               → ingest.py
        2. Limpieza              → clean.py
        3. Carga de datos BD     → load_db.py (productos + ventas)
        4. Entrenamiento ML      → models/train_model.py (modelo agregado)
        5. Descomposición per-SKU → cuota histórica sobre predicción global
        6. Carga de predicciones → load_db.py (tabla predicciones per-producto)

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
        # DataFrame de predicciones globales (columnas: fecha, ventas_reales,
        # ventas_predichas) listo para descomponer per-producto.
        print("\n>>> PASO 6: Entrenamiento del modelo (Ridge)")
        df_pred = run_training(PROCESSED_PATH)

        # ---- PASO 7: DESCOMPOSICIÓN PER-PRODUCTO ----
        # El modelo predice demanda diaria agregada; el dashboard la espera
        # por SKU. Repartimos cada predicción global entre los productos
        # según su cuota histórica de ventas, de forma que la tabla
        # predicciones tenga una fila por (id_producto, fecha).
        print("\n>>> PASO 7: Descomposición per-producto por cuota histórica")
        from sklearn.metrics import r2_score

        cuotas = df_ventas.groupby("id_producto")["unidades_vendidas"].sum()
        cuotas = (cuotas / cuotas.sum()).rename("cuota").reset_index()
        print(f"[PIPELINE] Cuotas calculadas para {len(cuotas)} productos.")

        # R² del modelo como "confianza" para el KPI del dashboard.
        # Se clipa a [0,1] porque el frontend lo pinta como porcentaje.
        r2 = float(r2_score(df_pred["ventas_reales"], df_pred["ventas_predichas"]))
        confianza = max(0.0, min(1.0, r2))
        print(f"[PIPELINE] R² del modelo = {r2:.4f} → confianza = {confianza:.4f}")

        df_pred_exp = df_pred.merge(cuotas, how="cross")
        df_pred_exp["unidades_predichas"] = (
            df_pred_exp["ventas_predichas"] * df_pred_exp["cuota"]
        ).round()
        df_pred_exp["unidades_vendidas"] = (
            df_pred_exp["ventas_reales"] * df_pred_exp["cuota"]
        ).round()
        df_pred_exp["confianza"] = confianza
        df_pred_exp = df_pred_exp[
            ["id_producto", "fecha", "unidades_predichas",
             "unidades_vendidas", "confianza"]
        ]
        print(f"[PIPELINE] Filas de predicciones a insertar: {len(df_pred_exp)}")

        # ---- PASO 8: INSERCIÓN DE PREDICCIONES EN BD ----
        # Push final: el dashboard leerá esta tabla para pintar las gráficas.
        print("\n>>> PASO 8: Inserción de predicciones en Supabase")
        insert_predicciones(conn, df_pred_exp)
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
