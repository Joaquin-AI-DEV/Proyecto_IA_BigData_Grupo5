import numpy as np


def build_features(df):
    """
    Aqui creamos todas las features que le damos al modelo
    para que aprenda los patrones de ventas.
    """
    df = df.sort_values("fecha")

    # -- Lags: ventas de dias anteriores para que el modelo sepa que paso antes --
    for lag in [1, 3, 7, 14, 21, 30]:
        df[f"lag_{lag}"] = df["ventas"].shift(lag)

    # -- Medias moviles: para suavizar y ver tendencias --
    for win in [3, 7, 14, 21, 30]:
        df[f"media_{win}"] = df["ventas"].rolling(win).mean()

    # -- Desviacion estandar movil: mide cuanto varian las ventas --
    for win in [7, 14, 30]:
        df[f"std_{win}"] = df["ventas"].rolling(win).std()

    # -- Cosas del calendario --
    df["dia_semana"]  = df["fecha"].dt.dayofweek
    df["dia_mes"]     = df["fecha"].dt.day
    df["mes"]         = df["fecha"].dt.month
    df["semana_anio"] = df["fecha"].dt.isocalendar().week.astype(int)
    df["trimestre"]   = df["fecha"].dt.quarter
    df["es_finde"]    = df["dia_semana"].isin([5, 6]).astype(int)

    # -- Tendencia: cuantos dias han pasado desde el inicio --
    df["tendencia"] = (df["fecha"] - df["fecha"].min()).dt.days

    # Quitamos las filas que tienen NaN por los shifts y rollings
    df = df.dropna()

    return df


def tratar_outliers(df, columna="ventas"):
    """
    Los outliers nos fastidian el modelo, asi que los capeamos.
    Usamos el metodo IQR: si un valor se pasa mucho del rango normal,
    lo recortamos al limite. Asi no perdemos filas pero tampoco
    nos distorsionan las predicciones.
    """
    q1 = df[columna].quantile(0.25)
    q3 = df[columna].quantile(0.75)
    iqr = q3 - q1

    limite_bajo = q1 - 1.5 * iqr
    limite_alto = q3 + 1.5 * iqr

    antes = len(df[(df[columna] < limite_bajo) | (df[columna] > limite_alto)])
    print(f"  Outliers detectados: {antes}")
    print(f"  Rango permitido: [{limite_bajo:.0f}, {limite_alto:.0f}]")

    # Capeamos en vez de eliminar (clip), para no perder dias
    df[columna] = df[columna].clip(lower=limite_bajo, upper=limite_alto)

    return df


def aplicar_log(df, columna="ventas"):
    """
    Aplicamos log1p a las ventas para que la distribucion sea mas normal.
    log1p es log(1+x) para evitar problemas con el 0.
    Esto ayuda a que los modelos entrenen mejor cuando los datos estan
    muy sesgados (muchos valores bajos y pocos muy altos).
    """
    print(f"  Skewness antes del log: {df[columna].skew():.2f}")
    df[columna] = np.log1p(df[columna])
    print(f"  Skewness despues del log: {df[columna].skew():.2f}")
    return df
