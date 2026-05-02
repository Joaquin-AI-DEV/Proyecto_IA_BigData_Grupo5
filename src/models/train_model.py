"""
train_model.py
Proyecto StockPulse - Grupo 5
Autor: Deninson Tapia

Modelo definitivo: Ridge regularizado sobre ventas mensuales agregadas.
Producto del modelo (segun requisito del equipo): 12 predicciones para los
12 meses del ano siguiente al ultimo dato disponible (YYYY+1).

Pasos:
  1. Backtest: split temporal 80/20, alpha tuneado por TimeSeriesSplit +
     GridSearchCV, metricas RMSE/MAE/R^2 sobre el test (escala real).
     R^2 << 1.0 confirma que no hay data leakage.
  2. Refit: Ridge se reentrena sobre toda la serie historica con la
     misma estrategia de tuneo (alpha por CV temporal).
  3. Forecast recursivo: se generan predicciones mes a mes hasta
     diciembre de YYYY+1. Cada paso usa los ultimos 3 valores
     (historicos o ya predichos) como lags. Se descarta cualquier
     mes intermedio que pertenezca al ano historico (p.ej. el ultimo
     mes incompleto que se descarto en load_and_aggregate).

Salidas:
  - src/models/saved/ridge_model.pkl   (modelo refit sobre todos los datos)
  - src/models/saved/scaler.pkl
  - data/results/predicciones_ridge.csv (12 filas, una por mes de YYYY+1)
  - data/results/prediccion_ridge.png   (historico real + forecast)
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
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
import joblib

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from src.models.features import build_features, tratar_outliers, aplicar_log


# --- Rutas ---
DEFAULT_INPUT = os.path.join("data", "processed", "ventas_limpias.csv")
RESULTS_DIR   = os.path.join("data", "results")
MODEL_DIR     = os.path.join("src", "models", "saved")

# --- Hiperparametros ---
ALPHA_GRID = [0.01, 0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0]
ALPHA = 10.0  # fallback cuando hay menos de 6 meses utiles
TEST_RATIO = 0.20

FEATURES = [
    "lag_1", "lag_2", "lag_3",
    "media_3", "std_3", "diff_1",
    "mes", "trimestre", "tendencia",
    "mes_sin", "mes_cos",
]
TARGET = "ventas"


def load_and_aggregate(filepath):
    """
    Carga el CSV de ventas limpias y agrega a frecuencia mensual (MS),
    descartando meses con cobertura < 25 dias para no introducir un mes
    incompleto sesgado a la baja.
    """
    print(f"Cargando dataset: {filepath}")
    df = pd.read_csv(filepath, parse_dates=["fecha_venta"], low_memory=False)

    daily = (
        df.groupby("fecha_venta")["unidades_vendidas"]
        .sum()
        .reset_index()
        .rename(columns={"fecha_venta": "fecha", "unidades_vendidas": "ventas"})
        .set_index("fecha")
        .sort_index()
    )

    dias_por_mes = daily.resample("MS").apply(lambda s: s.shape[0])

    mensual = (
        daily.resample("MS")["ventas"]
        .sum()
        .to_frame()
        .reset_index()
    )

    cobertura = dias_por_mes["ventas"].reset_index(drop=True)
    mensual = mensual[cobertura >= 25].reset_index(drop=True)

    print(f"Serie mensual: {len(mensual)} meses "
          f"({mensual['fecha'].min().date()} -> {mensual['fecha'].max().date()})")
    return mensual


def prepare_data(df):
    """Outliers -> log -> features -> split temporal 80/20."""
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


def _select_ridge(X_sc, y):
    """
    Selecciona alpha por TimeSeriesSplit + GridSearchCV.
    Fallback a alpha=10 cuando hay <6 meses (CV deja de ser fiable).
    """
    n = len(X_sc)

    if n < 6:
        print(f"  Pocos meses ({n}): Ridge(alpha={ALPHA}) sin CV.")
        modelo = Ridge(alpha=ALPHA)
        modelo.fit(X_sc, y)
        return modelo, ALPHA

    n_splits = min(4, max(2, n - 2))
    tscv = TimeSeriesSplit(n_splits=n_splits)

    grid = GridSearchCV(
        estimator=Ridge(),
        param_grid={"alpha": ALPHA_GRID},
        scoring="neg_root_mean_squared_error",
        cv=tscv,
        n_jobs=1,
    )
    print(f"  GridSearchCV Ridge alpha (TimeSeriesSplit, n_splits={n_splits})...")
    grid.fit(X_sc, y)

    alpha_sel = grid.best_params_["alpha"]
    cv_rmse   = -grid.best_score_
    print(f"  alpha optimo: {alpha_sel}  |  RMSE CV (log): {cv_rmse:.4f}")

    return grid.best_estimator_, alpha_sel


def train_and_evaluate(train, test):
    """
    Backtest sobre el split temporal: entrena en train, evalua en test.
    Las metricas reportadas son la prueba de que el modelo no tiene
    leakage (R^2 muy por debajo de 1.0 sobre datos no vistos).
    """
    X_train, y_train = train[FEATURES], train[TARGET]
    X_test,  y_test  = test[FEATURES],  test[TARGET]

    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc  = scaler.transform(X_test)

    print("\n--- Backtest (entrena en train, evalua en test) ---")
    modelo, _ = _select_ridge(X_train_sc, y_train)

    y_pred_log  = modelo.predict(X_test_sc)
    y_pred_real = np.expm1(np.clip(y_pred_log, 0, None))
    y_test_real = np.expm1(y_test)

    rmse = np.sqrt(mean_squared_error(y_test_real, y_pred_real))
    mae  = mean_absolute_error(y_test_real, y_pred_real)
    r2   = r2_score(y_test_real, y_pred_real)

    print(f"  RMSE: {rmse:.2f}")
    print(f"  MAE:  {mae:.2f}")
    print(f"  R2:   {r2:.4f}")
    if r2 > 0.99:
        print("  [WARN] R2 sospechosamente alto: revisar leakage en features.")

    return modelo, scaler, y_test_real, y_pred_real, test["fecha"]


def _refit_full(df_all):
    """Reentrena Ridge sobre TODOS los meses utiles (post-features)."""
    X_all, y_all = df_all[FEATURES], df_all[TARGET]
    scaler_full = StandardScaler()
    X_all_sc = scaler_full.fit_transform(X_all)
    print("\n--- Refit sobre todos los meses utiles ---")
    modelo_full, alpha_sel = _select_ridge(X_all_sc, y_all)
    return modelo_full, scaler_full, alpha_sel


def _build_row_features(ventas_log, fecha_step, tendencia):
    """
    Replica build_features pero para UNA sola fila futura, sin pasar por
    dropna. Mantiene 1:1 las definiciones de features.py.
    """
    return {
        "lag_1":     ventas_log[-1],
        "lag_2":     ventas_log[-2],
        "lag_3":     ventas_log[-3],
        "media_3":   float(np.mean(ventas_log[-3:])),
        "std_3":     float(np.std(ventas_log[-3:], ddof=1)),
        "diff_1":    ventas_log[-1] - ventas_log[-2],
        "mes":       int(fecha_step.month),
        "trimestre": (int(fecha_step.month) - 1) // 3 + 1,
        "tendencia": int(tendencia),
        "mes_sin":   float(np.sin(2 * np.pi * fecha_step.month / 12.0)),
        "mes_cos":   float(np.cos(2 * np.pi * fecha_step.month / 12.0)),
    }


def _forecast_year_plus_1(df_all, modelo, scaler):
    """
    Forecast recursivo: produce predicciones para los 12 meses de YYYY+1,
    donde YYYY es el ano del ultimo mes con datos historicos.

    df_all: DataFrame post-features y post-log con columna 'ventas' en
    escala log (lo que sale de prepare_data + concat).
    """
    df_all = df_all.sort_values("fecha").reset_index(drop=True)
    ventas_log = list(df_all[TARGET].values)
    last_date = pd.Timestamp(df_all["fecha"].iloc[-1])
    target_year = int(last_date.year) + 1
    next_tend = int(df_all["tendencia"].iloc[-1]) + 1

    # Generar fechas mensuales desde el siguiente mes hasta diciembre de YYYY+1.
    # Se predicen tambien los meses intermedios del ano historico (si los hay)
    # solo como pasos para alimentar los lags del primer mes de YYYY+1.
    fechas_iter = []
    fecha = (last_date + pd.offsets.MonthBegin(1)).normalize()
    while fecha.year <= target_year:
        fechas_iter.append(fecha)
        fecha = fecha + pd.offsets.MonthBegin(1)

    rows = []
    for fecha_step in fechas_iter:
        feats = _build_row_features(ventas_log, fecha_step, next_tend)
        X_new = pd.DataFrame([feats], columns=FEATURES)
        X_new_sc = scaler.transform(X_new)
        y_log = float(modelo.predict(X_new_sc)[0])
        y_log = max(0.0, y_log)  # clip para evitar valores negativos en log
        ventas_log.append(y_log)
        next_tend += 1
        rows.append({
            "fecha":            fecha_step,
            "ventas_predichas": float(np.expm1(y_log)),
        })

    df_forecast = pd.DataFrame(rows)
    df_year = df_forecast[df_forecast["fecha"].dt.year == target_year].reset_index(drop=True)

    if len(df_year) != 12:
        print(f"  [WARN] Esperaba 12 meses para {target_year}, hay {len(df_year)}.")

    return df_year[["fecha", "ventas_predichas"]]


def save_model(modelo, scaler):
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path  = os.path.join(MODEL_DIR, "ridge_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    joblib.dump(modelo, model_path)
    joblib.dump(scaler, scaler_path)
    print(f"\nModelo guardado en: {model_path}")
    print(f"Scaler guardado en: {scaler_path}")


def save_predictions(fechas, y_real, y_pred):
    """
    Guarda CSV de predicciones (12 filas, una por mes de YYYY+1).
    Acepta tanto Series como listas/arrays para mantener compatibilidad.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    fechas_arr = list(fechas.values) if hasattr(fechas, "values") else list(fechas)
    y_real_arr = list(y_real.values) if hasattr(y_real, "values") else list(y_real)
    y_pred_arr = list(y_pred.values) if hasattr(y_pred, "values") else list(y_pred)

    df_pred = pd.DataFrame({
        "fecha":            fechas_arr,
        "ventas_reales":    y_real_arr,
        "ventas_predichas": y_pred_arr,
    })

    pred_path = os.path.join(RESULTS_DIR, "predicciones_ridge.csv")
    df_pred.to_csv(pred_path, index=False)
    print(f"Predicciones guardadas en: {pred_path}")


def plot_results(fechas_hist, y_hist_real, fechas_fut, y_fut_pred):
    """Grafica: serie historica real + forecast 12 meses YYYY+1."""
    fig, ax = plt.subplots(figsize=(13, 5))

    ax.plot(fechas_hist, y_hist_real, label="Historico (real)", color="black",
            linewidth=2, marker="o")
    ax.plot(fechas_fut, y_fut_pred, label="Forecast 12 meses (Ridge)", color="#e74c3c",
            linestyle="--", linewidth=2, marker="s")

    ax.set_title("Forecast 12 meses YYYY+1 sobre la serie historica", fontsize=13)
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
    Pipeline completo: backtest -> refit -> forecast YYYY+1.

    Devuelve un DataFrame de 12 filas (una por mes de YYYY+1) con columnas
    (fecha, ventas_reales, ventas_predichas). Lo consume run_pipeline.py
    para hacer cross-merge por SKU (cuota historica) y obtener 12
    predicciones por producto.

    Para los meses futuros NO existen ventas reales, asi que
    ventas_reales = ventas_predichas como placeholder (es la unica
    convencion compatible con el orquestador actual). La metrica honesta
    del modelo se imprime en el bloque de Backtest, justo antes del refit:
    si ese R^2 fuera ~1.0 seria senal de leakage.
    """
    df_monthly = load_and_aggregate(filepath)
    train, test = prepare_data(df_monthly)

    # 1) Backtest temporal: imprime RMSE/MAE/R2 reales (sin leakage).
    train_and_evaluate(train, test)

    # 2) Refit sobre toda la historia para forecast en produccion.
    df_all = pd.concat([train, test], ignore_index=True)
    modelo_full, scaler_full, _ = _refit_full(df_all)

    # 3) Forecast recursivo de los 12 meses de YYYY+1.
    df_year = _forecast_year_plus_1(df_all, modelo_full, scaler_full)
    target_year = int(df_year["fecha"].dt.year.iloc[0])
    print(f"\n--- Forecast {len(df_year)} meses para {target_year} ---")
    for _, r in df_year.iterrows():
        print(f"  {r['fecha'].strftime('%Y-%m')}: {r['ventas_predichas']:.0f}")

    # 4) Persistencia: modelo refit + CSV + grafica.
    save_model(modelo_full, scaler_full)

    fechas_fut = list(pd.to_datetime(df_year["fecha"].values))
    y_fut      = df_year["ventas_predichas"].values

    save_predictions(
        fechas=[d.date() for d in fechas_fut],
        y_real=y_fut,
        y_pred=y_fut,
    )

    y_hist_real = np.expm1(df_all[TARGET].values)
    plot_results(
        fechas_hist=df_all["fecha"].values,
        y_hist_real=y_hist_real,
        fechas_fut=fechas_fut,
        y_fut_pred=y_fut,
    )

    # 5) DataFrame para el orquestador (12 filas).
    return pd.DataFrame({
        "fecha":            [d.date() for d in fechas_fut],
        "ventas_reales":    y_fut,
        "ventas_predichas": y_fut,
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
