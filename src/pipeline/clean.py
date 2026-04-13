"""
clean.py — Capa de limpieza y normalización de datos
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Responsabilidad:
    Recibe el DataFrame en bruto de la capa de ingesta y aplica:
      1. Eliminación de cancelaciones (InvoiceNo que empieza por 'C')
      2. Eliminación de filas con Quantity <= 0 (devoluciones)
      3. Eliminación de filas con UnitPrice <= 0
      4. Eliminación de duplicados exactos
      5. Gestión de nulos (Description y CustomerID)
      6. Normalización del formato de fechas a YYYY-MM-DD
      7. Normalización de texto (Description, StockCode)
      8. Cálculo de total_venta = Quantity * UnitPrice
      9. Renombrado de columnas al esquema interno del proyecto

    Al final devuelve dos DataFrames listos para insertar:
      - df_productos: columnas del modelo Productos
      - df_ventas:    columnas del modelo Ventas
"""

import pandas as pd


def clean_and_normalize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica todas las operaciones de limpieza sobre el DataFrame bruto.

    Parámetros:
        df (pd.DataFrame): DataFrame original cargado por ingest.py.

    Retorna:
        pd.DataFrame: DataFrame limpio y normalizado.
    """

    filas_inicio = len(df)
    print(f"[LIMPIEZA] Iniciando con {filas_inicio} filas.")

    # --- 1. Eliminar cancelaciones (InvoiceNo empieza por 'C') ---
    # Las facturas canceladas tienen 'C' como prefijo en el número de factura
    df = df[~df["InvoiceNo"].astype(str).str.startswith("C")]
    print(f"[LIMPIEZA] Tras eliminar cancelaciones: {len(df)} filas.")

    # --- 2. Eliminar filas con Quantity <= 0 (devoluciones y errores) ---
    df = df[df["Quantity"] > 0]
    print(f"[LIMPIEZA] Tras filtrar Quantity > 0: {len(df)} filas.")

    # --- 3. Eliminar filas con UnitPrice <= 0 (registros corruptos) ---
    df = df[df["UnitPrice"] > 0]
    print(f"[LIMPIEZA] Tras filtrar UnitPrice > 0: {len(df)} filas.")

    # --- 4. Eliminar duplicados exactos ---
    antes_dup = len(df)
    df = df.drop_duplicates()
    print(f"[LIMPIEZA] Duplicados eliminados: {antes_dup - len(df)}.")

    # --- 5. Gestión de nulos ---

    # Description: rellenar nulos con 'Sin descripción'
    df["Description"] = df["Description"].fillna("Sin descripción")

    # CustomerID: rellenar nulos con 0 (cliente anónimo / sin registro)
    # Se convierte a int después de rellenar para evitar decimales
    df["CustomerID"] = df["CustomerID"].fillna(0).astype(int)

    print(f"[LIMPIEZA] Nulos gestionados en Description y CustomerID.")

    # --- 6. Normalización de fechas a formato YYYY-MM-DD ---
    # InvoiceDate ya viene como datetime, extraemos solo la parte de fecha
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"]).dt.date
    print(f"[LIMPIEZA] Fechas normalizadas a formato DATE.")

    # --- 7. Normalización de texto ---

    # Description: strip de espacios, capitalización consistente
    df["Description"] = (
        df["Description"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # StockCode: convertir a string, eliminar espacios
    df["StockCode"] = df["StockCode"].astype(str).str.strip().str.upper()

    print(f"[LIMPIEZA] Texto normalizado en Description y StockCode.")

    # --- 8. Calcular total_venta ---
    df["total_venta"] = (df["Quantity"] * df["UnitPrice"]).round(2)

    # --- 9. Renombrar columnas al esquema interno ---
    df = df.rename(columns={
        "StockCode":    "id_producto",
        "Description":  "nombre",
        "InvoiceDate":  "fecha_venta",
        "Quantity":     "unidades_vendidas",
        "UnitPrice":    "precio_unitario",
        "InvoiceNo":    "id_venta_original",
    })

    print(f"[LIMPIEZA] Pipeline completado. Filas finales: {len(df)} (de {filas_inicio} originales).")
    print(f"[LIMPIEZA] Filas eliminadas en total: {filas_inicio - len(df)}.")

    return df


def split_productos_ventas(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Separa el DataFrame limpio en las dos tablas del modelo de datos:
      - Productos (catálogo único de productos)
      - Ventas (registros de transacciones)

    Parámetros:
        df (pd.DataFrame): DataFrame limpio devuelto por clean_and_normalize().

    Retorna:
        tuple: (df_productos, df_ventas)
    """

    # --- Tabla Productos ---
    # Un producto único se identifica por id_producto (StockCode)
    # Se mantiene el precio unitario más reciente si hay variación
    df_productos = (
        df[["id_producto", "nombre", "precio_unitario"]]
        .sort_values("precio_unitario", ascending=False)
        .drop_duplicates(subset=["id_producto"], keep="first")
        .reset_index(drop=True)
    )

    # Añadir categoría vacía (el dataset no tiene categoría; se puede enriquecer)
    df_productos["categoria"] = "Sin categoría"

    # Reordenar columnas según el modelo de BD
    df_productos = df_productos[["id_producto", "nombre", "categoria", "precio_unitario"]]

    print(f"[SPLIT] Productos únicos: {len(df_productos)}")

    # --- Tabla Ventas ---
    # Cada fila es una línea de transacción de venta
    df_ventas = df[[
        "id_venta_original",
        "id_producto",
        "fecha_venta",
        "unidades_vendidas",
        "total_venta",
    ]].copy().reset_index(drop=True)

    print(f"[SPLIT] Registros de ventas: {len(df_ventas)}")

    return df_productos, df_ventas
