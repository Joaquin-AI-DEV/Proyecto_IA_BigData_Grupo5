"""
train_model.py
Proyecto StockPulse - Grupo 5
Autor: Deninson Tapia

Este es el script del modelo definitivo.
Despues de comparar Ridge, Random Forest y Gradient Boosting
en compare_models.py, Ridge fue el ganador asi que aqui
lo entrenamos, guardamos el modelo y exportamos las predicciones
para que Jimmy las use en el dashboard.

Modelo elegido: Ridge (alpha=10.0)
Motivo: mejor RMSE, MAE y R2 en la comparacion. Ademas con
un dataset tan pequeno (~220 dias de train) un modelo simple
generaliza mejor que los ensemble.
"""

import os
import sys

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import joblib

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from src.models.features import build_features, tratar_outliers, aplicar_log


# --- Rutas ---
DEFAULT_INPUT = os.path.join("data", "processed", "ventas_limpias.csv")
RESULTS_DIR   = os.path.join("data", "results")
MODEL_DIR     = os.path.join("src", "models", "saved")

# --- El modelo ganador ---
ALPHA = 10.0
TEST_RATIO = 0.20

FEATURES = [
    "lag_1", "lag_3", "lag_7", "lag_14", "lag_21", "lag_30",
    "media_3", "media_7", "media_14", "media_21", "media_30",
    "std_7", "std_14", "std_30",
    "dia_semana", "dia_mes", "mes", "semana_anio", "trimestre",
    "es_finde", "tendencia",
]
TARGET = "ventas"


def load_and_aggregate(filepath):
    """Cargamos el csv y agrupamos por dia."""
    print(f"Cargando dataset: {filepath}")
    df = pd.read_csv(filepath, parse_dates=["fecha_venta"], low_memory=False)

    daily = (
        df.groupby("fecha_venta")["unidades_vendidas"]
        .sum()
        .reset_index()
        .rename(columns={"fecha_venta": "fecha", "unidades_vendidas": "ventas"})
        .sort_values("fecha")
    )

    print(f"Serie temporal: {len(daily)} dias "
          f"({daily['fecha'].min().date()} -> {daily['fecha'].max().date()})")
    return daily


def prepare_data(df):
    """
    Mismo preprocesamiento que en compare_models:
    outliers -> log -> features -> split temporal
    """
    print("\n--- Preprocesamiento ---")

    print("Tratando outliers:")
    df = tratar_outliers(df, "ventas")

    print("Aplicando transformacion log:")
    df = aplicar_log(df, "ventas")

    df = build_features(df)

    # Split temporal
    n_test  = int(len(df) * TEST_RATIO)
    n_train = len(df) - n_test

    train = df.iloc[:n_train]
    test  = df.iloc[n_train:]

    print(f"Train: {len(train)} dias | Test: {len(test)} dias")

    return train, test


def train_and_evaluate(train, test):
    """Entrenamos Ridge y evaluamos."""

    X_train, y_train = train[FEATURES], train[TARGET]
    X_test,  y_test  = test[FEATURES],  test[TARGET]

    # Escalamos features (Ridge lo necesita por la regularizacion)
    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc  = scaler.transform(X_test)

    # Entrenamos
    print(f"\nEntrenando Ridge (alpha={ALPHA})...")
    modelo = Ridge(alpha=ALPHA)
    modelo.fit(X_train_sc, y_train)

    # Predicciones en escala real (deshacemos el log)
    y_pred_log  = modelo.predict(X_test_sc)
    y_pred_real = np.expm1(np.clip(y_pred_log, 0, None))
    y_test_real = np.expm1(y_test)

    # Metricas
    rmse = np.sqrt(mean_squared_error(y_test_real, y_pred_real))
    mae  = mean_absolute_error(y_test_real, y_pred_real)
    r2   = r2_score(y_test_real, y_pred_real)

    print(f"\n--- Resultados modelo definitivo ---")
    print(f"  RMSE: {rmse:.2f}")
    print(f"  MAE:  {mae:.2f}")
    print(f"  R2:   {r2:.4f}")

    return modelo, scaler, y_test_real, y_pred_real, test["fecha"]


def save_model(modelo, scaler):
    """Guardamos el modelo y el scaler para poder usarlos despues."""
    os.makedirs(MODEL_DIR, exist_ok=True)

    model_path  = os.path.join(MODEL_DIR, "ridge_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")

    joblib.dump(modelo, model_path)
    joblib.dump(scaler, scaler_path)

    print(f"\nModelo guardado en: {model_path}")
    print(f"Scaler guardado en: {scaler_path}")


def save_predictions(fechas, y_real, y_pred):
    """
    Exportamos las predicciones a CSV para que se puedan usar
    en el dashboard o en la memoria del proyecto.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)

    df_pred = pd.DataFrame({
        "fecha":           fechas.values,
        "ventas_reales":   y_real.values,
        "ventas_predichas": y_pred,
    })

    pred_path = os.path.join(RESULTS_DIR, "predicciones_ridge.csv")
    df_pred.to_csv(pred_path, index=False)
    print(f"Predicciones guardadas en: {pred_path}")


def plot_results(fechas, y_real, y_pred):
    """Grafica del modelo definitivo: real vs prediccion."""
    fig, ax = plt.subplots(figsize=(13, 5))

    ax.plot(fechas, y_real.values, label="Real", color="black", linewidth=1.5)
    ax.plot(fechas, y_pred, label="Ridge (prediccion)", color="#e74c3c",
            linestyle="--", linewidth=2)

    ax.set_title("Modelo definitivo (Ridge) - Prediccion vs Ventas reales", fontsize=13)
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Unidades vendidas")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=30)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    plot_path = os.path.join(RESULTS_DIR, "prediccion_ridge.png")
    plt.savefig(plot_path, dpi=150)
    print(f"Grafica guardada en: {plot_path}")
    plt.close()


def main(filepath):
    df_daily = load_and_aggregate(filepath)
    train, test = prepare_data(df_daily)

    modelo, scaler, y_real, y_pred, fechas = train_and_evaluate(train, test)

    save_model(modelo, scaler)
    save_predictions(fechas, y_real, y_pred)
    plot_results(fechas, y_real, y_pred)

    print("\nTodo listo!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default=DEFAULT_INPUT, help="Ruta al CSV limpio")
    args = parser.parse_args()
    main(args.input)
