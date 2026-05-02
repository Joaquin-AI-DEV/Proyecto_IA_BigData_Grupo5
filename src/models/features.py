import numpy as np


def build_features(df):
    """
    Genera las features mensuales que ve el modelo.

    Importante: todas las features derivadas de 'ventas' usan shift(1)
    o lags >=1, asi nunca incluimos el valor del mes que estamos
    intentando predecir (sin data leakage).
    """
    df = df.sort_values("fecha").reset_index(drop=True)

    # -- Lags mensuales: ventas de meses anteriores --
    # 1, 2, 3 capturan tendencia corta; 12 capturaria estacionalidad anual
    # pero con solo ~13 meses de historico no es viable, asi que lo omitimos.
    for lag in [1, 2, 3]:
        df[f"lag_{lag}"] = df["ventas"].shift(lag)

    # -- Medias moviles con shift(1) para evitar leakage --
    # rolling(N).mean() incluiria el mes actual en la ventana, lo desplazamos
    # para que la media solo use meses estrictamente anteriores.
    for win in [3]:
        df[f"media_{win}"] = df["ventas"].shift(1).rolling(win).mean()

    # -- Volatilidad reciente: dispersion de los 3 meses previos.
    # Da al modelo una pista sobre la incertidumbre del nivel actual
    # (igualmente sin leakage por el shift(1)).
    df["std_3"] = df["ventas"].shift(1).rolling(3).std()

    # -- Momentum corto: aceleracion entre los dos meses previos.
    # Captura si la serie venia subiendo o bajando justo antes del mes a predecir.
    df["diff_1"] = df["ventas"].shift(1) - df["ventas"].shift(2)

    # -- Calendario (no dependen del target, no hay leakage posible) --
    df["mes"]       = df["fecha"].dt.month
    df["trimestre"] = df["fecha"].dt.quarter

    # Codificacion ciclica del mes: evita que enero (1) y diciembre (12)
    # parezcan extremos lejanos para un modelo lineal y captura mejor
    # la estacionalidad sin requerir un lag_12 (que con <13 meses no existe).
    df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12.0)
    df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12.0)

    # Tendencia: numero de meses desde el inicio de la serie
    df["tendencia"] = np.arange(len(df))

    # Filas sin lags suficientes (los primeros meses) se descartan
    df = df.dropna().reset_index(drop=True)

    return df


def tratar_outliers(df, columna="ventas"):
    """
    Capeo IQR de outliers. A nivel mensual hay muy pocos puntos asi que
    raramente activa, pero lo dejamos por consistencia con el resto del
    proyecto y por si en el futuro se amplia el historico.

    Multiplicador 3.0 (Tukey "far-outliers"): con <=12 meses la IQR es muy
    estrecha y el limite estandar 1.5 podia recortar picos legitimos
    (p.ej. noviembre/diciembre en retail), perjudicando la prediccion.
    """
    q1 = df[columna].quantile(0.25)
    q3 = df[columna].quantile(0.75)
    iqr = q3 - q1

    limite_bajo = q1 - 3.0 * iqr
    limite_alto = q3 + 3.0 * iqr

    detectados = len(df[(df[columna] < limite_bajo) | (df[columna] > limite_alto)])
    print(f"  Outliers detectados: {detectados}")
    print(f"  Rango permitido: [{limite_bajo:.0f}, {limite_alto:.0f}]")

    df[columna] = df[columna].clip(lower=limite_bajo, upper=limite_alto)

    return df


def aplicar_log(df, columna="ventas"):
    """
    log1p para reducir el sesgo de la distribucion. Las ventas mensuales
    son grandes en magnitud (decenas de miles de unidades) y la transformacion
    estabiliza la varianza, ayudando a Ridge.
    """
    print(f"  Skewness antes del log: {df[columna].skew():.2f}")
    df[columna] = np.log1p(df[columna])
    print(f"  Skewness despues del log: {df[columna].skew():.2f}")
    return df
