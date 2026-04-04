"""
ingest.py — Capa de ingesta de datos
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Responsabilidad:
    Carga el dataset original (CSV o XLSX) y lo devuelve como DataFrame de Pandas.
    Valida que las columnas necesarias existan antes de continuar el pipeline.
"""

import pandas as pd
import os


# Columnas mínimas que debe tener el dataset de entrada
REQUIRED_COLUMNS = {
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
}


def load_dataset(filepath: str) -> pd.DataFrame:
    """
    Carga un archivo CSV o XLSX y lo devuelve como DataFrame.

    Parámetros:
        filepath (str): Ruta absoluta o relativa al archivo de datos.

    Retorna:
        pd.DataFrame: Dataset cargado sin procesar.

    Excepciones:
        FileNotFoundError: Si el archivo no existe en la ruta indicada.
        ValueError: Si la extensión no es CSV ni XLSX.
        ValueError: Si faltan columnas obligatorias.
    """

    # Verificar que el archivo existe
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No se encontró el archivo: {filepath}")

    extension = os.path.splitext(filepath)[1].lower()

    # Cargar según el formato del archivo
    if extension == ".csv":
        print(f"[INGESTA] Cargando CSV: {filepath}")
        df = pd.read_csv(filepath, encoding="utf-8", low_memory=False)

    elif extension == ".xlsx":
        print(f"[INGESTA] Cargando XLSX: {filepath}")
        df = pd.read_excel(filepath, engine="openpyxl")

    else:
        raise ValueError(f"Formato no soportado: '{extension}'. Usa CSV o XLSX.")

    print(f"[INGESTA] Dataset cargado: {df.shape[0]} filas, {df.shape[1]} columnas.")

    # Validar que las columnas necesarias existen
    _validate_columns(df)

    return df


def _validate_columns(df: pd.DataFrame) -> None:
    """
    Comprueba que el DataFrame contiene todas las columnas requeridas.

    Parámetros:
        df (pd.DataFrame): DataFrame a validar.

    Excepciones:
        ValueError: Lista las columnas que faltan si no están todas presentes.
    """
    columnas_presentes = set(df.columns)
    columnas_faltantes = REQUIRED_COLUMNS - columnas_presentes

    if columnas_faltantes:
        raise ValueError(
            f"[INGESTA] Faltan columnas obligatorias en el dataset: {columnas_faltantes}"
        )

    print(f"[INGESTA] Validación de columnas OK.")
