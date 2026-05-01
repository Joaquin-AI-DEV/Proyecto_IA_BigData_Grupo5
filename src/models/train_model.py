"""
train_model.py
Proyecto StockPulse - Grupo 5
Autor: Deninson Tapia

Modelo definitivo: Ridge regularizado sobre ventas agregadas a frecuencia
MENSUAL. Esta version corrige problemas de la iteracion anterior:

  1. Sin data leakage: las medias moviles usan shift(1), de modo que ninguna
     feature incluye el valor del mes que estamos prediciendo.
  2. Prediccion mensual, no diaria: el orquestador del pipeline pedia
     "predecir el proximo mes", asi que agregamos por mes (MS) en lugar de
     por dia. La metrica reportada es la del mes completo.
  3. Eliminamos el ultimo mes si esta incompleto, para no contaminar la
     metrica con un punto basado en pocos dias.
  4. Modelo simple (Ridge alpha=10) coherente con el tamano del dataset
     (~12 meses utiles, sumamente pocos para algo mas complejo).

Salidas:
  - src/models/saved/ridge_model.pkl
  - src/models/saved/scaler.pkl
  - data/results/predicciones_ridge.csv (fecha mensual, real, predicho)
  - data/results/prediccion_ridge.png
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

# --- Hiperparametros ---
# Ridge con alpha=10: misma regularizacion que el modelo de Fase 2,
# adecuada para un dataset pequeno (regularizacion fuerte evita overfit).
ALPHA = 10.0
# 80/20 temporal. Con 9-12 meses utiles esto deja 2-3 meses de test.
TEST_RATIO = 0.20

FEATURES = [
    "lag_1", "lag_2", "lag_3",
    "media_3",
    "mes", "trimestre", "tendencia",
]
TARGET = "ventas"


def load_and_aggregate(filepath):
    """
    Carga el CSV de ventas limpias y agrega a frecuencia mensual.

    Pasos:
      1. Lee el CSV (granularidad: una fila por linea de venta).
      2. Suma las unidades vendidas por dia.
      3. Resamplea a inicio de mes (MS) sumando los dias.
      4. Descarta el ultimo mes si tiene menos de 25 dias de cobertura,
         para no introducir un punto sesgado a la baja.
    """
    print(f"Cargando dataset: {filepath}")
    df = pd.read_csv(filepath, parse_dates=["fecha_venta"], low_memory=False)

    # Sumar a nivel diario primero (asi controlamos cobertura por mes)
    daily = (
        df.groupby("fecha_venta")["unidades_vendidas"]
        .sum()
        .reset_index()
        .rename(columns={"fecha_venta": "fecha", "unidades_vendidas": "ventas"})
        .set_index("fecha")
        .sort_index()
    )

    # Cobertura: cuantos dias distintos hay en cada mes
    dias_por_mes = daily.resample("MS").apply(lambda s: s.shape[0])

    # Suma mensual de unidades
    mensual = (
        daily.resample("MS")["ventas"]
        .sum()
        .to_frame()
        .reset_index()
    )

    # Descartar meses con cobertura < 25 dias (el ultimo mes incompleto)
    cobertura = dias_por_mes["ventas"].reset_index(drop=True)
    mensual = mensual[cobertura >= 25].reset_index(drop=True)

    print(f"Serie mensual: {len(mensual)} meses "
          f"({mensual['fecha'].min().date()} -> {mensual['fecha'].max().date()})")
    return mensual


def prepare_data(df):
    """
    Outliers -> log -> features -> split temporal.
    """
    print("\n--- Preprocesamiento ---")

    print("Tratando outliers:")
    df = tratar_outliers(df, "ventas")

    print("Aplicando transformacion log:")
    df = aplicar_log(df, "ventas")

    df = build_features(df)

    n_test  = max(1, int(round(len(df) * TEST_RATIO)))
    n_train = len(df) - n_test

    train = df.iloc[:n_train]
    test  = df.iloc[n_train:]

    print(f"Train: {len(train)} meses | Test: {len(test)} meses")

    return train, test


def train_and_evaluate(train, test):
    """Entrena Ridge y evalua sobre el conjunto de test mensual."""

    X_train, y_train = train[FEATURES], train[TARGET]
    X_test,  y_test  = test[FEATURES],  test[TARGET]

    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc  = scaler.transform(X_test)

    print(f"\nEntrenando Ridge (alpha={ALPHA})...")
    modelo = Ridge(alpha=ALPHA)
    modelo.fit(X_train_sc, y_train)

    # Deshacer log para reportar metricas en escala de unidades reales
    y_pred_log  = modelo.predict(X_test_sc)
    y_pred_real = np.expm1(np.clip(y_pred_log, 0, None))
    y_test_real = np.expm1(y_test)

    rmse = np.sqrt(mean_squared_error(y_test_real, y_pred_real))
    mae  = mean_absolute_error(y_test_real, y_pred_real)
    r2   = r2_score(y_test_real, y_pred_real)

    print(f"\n--- Resultados modelo definitivo (mensual) ---")
    print(f"  RMSE: {rmse:.2f}")
    print(f"  MAE:  {mae:.2f}")
    print(f"  R2:   {r2:.4f}")

    return modelo, scaler, y_test_real, y_pred_real, test["fecha"]


def save_model(modelo, scaler):
    os.makedirs(MODEL_DIR, exist_ok=True)

    model_path  = os.path.join(MODEL_DIR, "ridge_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")

    joblib.dump(modelo, model_path)
    joblib.dump(scaler, scaler_path)

    print(f"\nModelo guardado en: {model_path}")
    print(f"Scaler guardado en: {scaler_path}")


def save_predictions(fechas, y_real, y_pred):
    os.makedirs(RESULTS_DIR, exist_ok=True)

    df_pred = pd.DataFrame({
        "fecha":            fechas.values,
        "ventas_reales":    y_real.values,
        "ventas_predichas": y_pred,
    })

    pred_path = os.path.join(RESULTS_DIR, "predicciones_ridge.csv")
    df_pred.to_csv(pred_path, index=False)
    print(f"Predicciones guardadas en: {pred_path}")


def plot_results(fechas, y_real, y_pred):
    """Grafica mensual: real vs prediccion."""
    fig, ax = plt.subplots(figsize=(13, 5))

    ax.plot(fechas, y_real.values, label="Real", color="black",
            linewidth=2, marker="o")
    ax.plot(fechas, y_pred, label="Ridge (prediccion)", color="#e74c3c",
            linestyle="--", linewidth=2, marker="s")

    ax.set_title("Modelo definitivo (Ridge, mensual) - Prediccion vs Ventas reales",
                 fontsize=13)
    ax.set_xlabel("Mes")
    ax.set_ylabel("Unidades vendidas (mes)")
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


def run_training(filepath):
    """
    Pipeline completo de entrenamiento. Devuelve el DataFrame de
    predicciones (fecha mensual, ventas_reales, ventas_predichas) que
    consume el orquestador del pipeline.
    """
    df_monthly = load_and_aggregate(filepath)
    train, test = prepare_data(df_monthly)

    modelo, scaler, y_real, y_pred, fechas = train_and_evaluate(train, test)

    save_model(modelo, scaler)
    save_predictions(fechas, y_real, y_pred)
    plot_results(fechas, y_real, y_pred)

    return pd.DataFrame({
        "fecha":            pd.to_datetime(fechas.values).date,
        "ventas_reales":    y_real.values,
        "ventas_predichas": y_pred,
    })


def main(filepath):
    run_training(filepath)
    print("\nTodo listo!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default=DEFAULT_INPUT,
                        help="Ruta al CSV limpio")
    args = parser.parse_args()
    main(args.input)
