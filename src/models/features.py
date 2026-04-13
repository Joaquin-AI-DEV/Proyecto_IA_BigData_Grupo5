def build_features(df):
    df = df.sort_values("fecha")
    df["lag_7"]  = df["ventas"].shift(7)
    df["lag_30"] = df["ventas"].shift(30)
    df["media_7"]  = df["ventas"].rolling(7).mean()
    df["media_30"] = df["ventas"].rolling(30).mean()
    df["dia_semana"] = df["fecha"].dt.dayofweek
    df["mes"]        = df["fecha"].dt.month
    df["es_finde"]   = df["dia_semana"].isin([5, 6]).astype(int)
    return df.dropna()
