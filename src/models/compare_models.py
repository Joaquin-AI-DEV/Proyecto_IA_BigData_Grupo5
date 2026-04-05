"""
compare_models.py
Proyecto StockPulse - Grupo 5
Autor: Deninson Tapia

Comparamos tres modelos para ver cuál predice mejor las ventas diarias:
- Regresión Lineal (como baseline)
- Random Forest
- Gradient Boosting

Usamos RMSE, MAE y R2 para comparar resultados.
"""

import argparse
import os
import sys

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from src.models.features import build_features


DEFAULT_INPUT = os.path.join("data", "processed", "ventas_limpias.csv")
RESULTS_DIR   = os.path.join("data", "results")

MODELS = {
    "Regresión Lineal":  LinearRegression(),
    "Random Forest":     RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1),
    "Gradient Boosting": GradientBoostingRegressor(n_estimators=200, max_depth=4,
                                                    learning_rate=0.05, random_state=42),
}

FEATURES = ["lag_7", "lag_30", "media_7", "media_30", "dia_semana", "mes", "es_finde"]
TARGET   = "ventas"


def load_and_aggregate(filepath):
    print(f"Cargando dataset: {filepath}")
    df = pd.read_csv(filepath, parse_dates=["fecha_venta"])

    # Agrupamos por día y sumamos las unidades vendidas
    daily = (
        df.groupby("fecha_venta")["unidades_vendidas"]
        .sum()
        .reset_index()
        .rename(columns={"fecha_venta": "fecha", "unidades_vendidas": "ventas"})
        .sort_values("fecha")
    )

    print(f"Serie temporal: {len(daily)} días "
          f"({daily['fecha'].min().date()} → {daily['fecha'].max().date()})")
    return daily


def prepare_data(df, test_ratio):
    df = build_features(df)

    # Split cronológico (no aleatorio, porque es serie temporal)
    n_test  = int(len(df) * test_ratio)
    n_train = len(df) - n_test

    train = df.iloc[:n_train]
    test  = df.iloc[n_train:]

    print(f"Train: {len(train)} días | Test: {len(test)} días")

    X_train, y_train = train[FEATURES], train[TARGET]
    X_test,  y_test  = test[FEATURES],  test[TARGET]

    return X_train, y_train, X_test, y_test, test["fecha"]


def evaluate(y_true, y_pred):
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae  = mean_absolute_error(y_true, y_pred)
    r2   = r2_score(y_true, y_pred)
    return {"RMSE": round(rmse, 2), "MAE": round(mae, 2), "R²": round(r2, 4)}


def run_comparison(filepath, test_ratio):

    df_daily = load_and_aggregate(filepath)
    X_train, y_train, X_test, y_test, fechas_test = prepare_data(df_daily, test_ratio)

    resultados   = {}
    predicciones = {}

    print("\n" + "─" * 55)
    print(f"  {'Modelo':<22}  {'RMSE':>8}  {'MAE':>8}  {'R²':>8}")
    print("─" * 55)

    for nombre, modelo in MODELS.items():
        modelo.fit(X_train, y_train)
        y_pred = modelo.predict(X_test)
        y_pred = np.clip(y_pred, 0, None)

        metricas = evaluate(y_test, y_pred)
        resultados[nombre]   = metricas
        predicciones[nombre] = y_pred

        print(f"  {nombre:<22}  {metricas['RMSE']:>8}  {metricas['MAE']:>8}  {metricas['R²']:>8}")

    print("─" * 55)

    mejor = min(resultados, key=lambda m: resultados[m]["RMSE"])
    print(f"\nMejor modelo (menor RMSE): {mejor}")

    # Guardar tabla de resultados
    os.makedirs(RESULTS_DIR, exist_ok=True)
    df_res = pd.DataFrame(resultados).T
    df_res.index.name = "modelo"
    results_path = os.path.join(RESULTS_DIR, "comparacion_modelos.csv")
    df_res.to_csv(results_path)
    print(f"Resultados guardados en: {results_path}")

    _plot_predictions(fechas_test, y_test, predicciones, mejor)


def _plot_predictions(fechas, y_true, predicciones, mejor):
    fig, ax = plt.subplots(figsize=(13, 5))

    ax.plot(fechas, y_true.values, label="Real", color="black", linewidth=1.5, zorder=5)

    colores = ["#e74c3c", "#2980b9", "#27ae60"]
    estilos = ["--", "-.", ":"]

    for (nombre, y_pred), color, estilo in zip(predicciones.items(), colores, estilos):
        lw = 2.2 if nombre == mejor else 1.4
        ax.plot(fechas, y_pred, label=nombre, color=color, linestyle=estilo, linewidth=lw)

    ax.set_title("Comparación de modelos — Predicción de ventas diarias", fontsize=13)
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Unidades vendidas")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=30)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    plot_path = os.path.join(RESULTS_DIR, "comparacion_modelos.png")
    plt.savefig(plot_path, dpi=150)
    print(f"Gráfica guardada en: {plot_path}")
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=str,
        default=DEFAULT_INPUT,
        help="Ruta al CSV limpio",
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.20,
        help="Porcentaje de datos para test (por defecto 0.20)",
    )
    args = parser.parse_args()
    run_comparison(args.input, args.test_ratio)