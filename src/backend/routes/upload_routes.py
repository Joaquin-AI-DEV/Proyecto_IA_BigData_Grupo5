"""
routes/upload_routes.py — Endpoint de carga y procesamiento de datos
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Endpoints:
    POST /api/upload → Recibe CSV/XLSX, lanza el pipeline y devuelve resultado

Flujo:
    1. Validar token de sesión
    2. Guardar el archivo temporalmente
    3. Ejecutar run_pipeline() (ingest → clean → load_db)
    4. Eliminar el archivo temporal
    5. Devolver resultado al frontend
"""

import os
import shutil
import tempfile
from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Form
from auth import get_session_user

# Importar el orquestador del pipeline de Sergio
import sys
# Ruta absoluta — funciona independientemente del directorio de trabajo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "..", "..", ".."))

from src.pipeline.run_pipeline import run_pipeline

router = APIRouter(prefix="/api", tags=["Carga de datos"])

# Extensiones de archivo permitidas
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
MAX_FILE_SIZE_MB = 50


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    username: str = Form(...),
    authorization: str = Header(None)
):
    """
    Recibe un archivo CSV o XLSX, ejecuta el pipeline de datos y
    almacena los resultados en Supabase.

    Parámetros (form-data):
        file     : Archivo CSV o XLSX
        username : Nombre del usuario (para logging)

    Header requerido:
        Authorization: Bearer <token>

    Retorna:
        {
            "message": "Archivo procesado correctamente.",
            "filas_procesadas": 524878,
            "filename": "online_retail.xlsx"
        }
    """

    # 1. Validar sesión
    token = _extract_token(authorization)
    session_user = get_session_user(token)
    if not session_user:
        raise HTTPException(status_code=401, detail="Sesión no válida o expirada.")

    # 2. Validar extensión del archivo
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no válido: '{ext}'. Solo se permiten .csv y .xlsx"
        )

    # 3. Guardar archivo en directorio temporal del sistema operativo
    tmp_file = None
    try:
        # Crear archivo temporal con la extensión correcta
        with tempfile.NamedTemporaryFile(
            suffix=ext, delete=False, mode="wb"
        ) as tmp:
            tmp_file = tmp.name
            content = await file.read()

            # Validar tamaño (50 MB máximo)
            if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail=f"Archivo demasiado grande. Máximo {MAX_FILE_SIZE_MB}MB."
                )

            tmp.write(content)

        print(f"[UPLOAD] Archivo temporal guardado en: {tmp_file}")
        print(f"[UPLOAD] Usuario: {session_user} — Archivo: {file.filename}")

        # 4. Ejecutar el pipeline de datos
        result = run_pipeline(tmp_file)

        # 5. Devolver respuesta al frontend
        return {
            "message": "Archivo procesado correctamente.",
            "filename": file.filename,
        }

    except HTTPException:
        raise  # Re-lanzar excepciones HTTP que ya preparamos arriba

    except Exception as e:
        print(f"[UPLOAD] Error procesando archivo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el archivo: {str(e)}"
        )

    finally:
        # 6. Limpiar siempre el archivo temporal, pase lo que pase
        if tmp_file and os.path.exists(tmp_file):
            os.remove(tmp_file)
            print(f"[UPLOAD] Archivo temporal eliminado: {tmp_file}")


def _extract_token(authorization: str | None) -> str:
    """Extrae el token del header Authorization: Bearer <token>."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de sesión requerido.")
    return authorization.split(" ", 1)[1]
