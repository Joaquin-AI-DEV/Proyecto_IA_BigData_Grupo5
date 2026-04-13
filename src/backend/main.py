"""
main.py — Punto de entrada del backend FastAPI
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Responsabilidad:
    Configura la aplicación FastAPI, registra todos los routers
    y habilita CORS para que el frontend (index.html) pueda
    comunicarse con la API desde el navegador.

Uso:
    Desde la carpeta src/backend/:
        uvicorn main:app --reload --port 8000

    El frontend apunta a http://localhost:8000 (variable API_BASE en app.js).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importar los routers de cada módulo
from routes.auth_routes import router as auth_router
from routes.upload_routes import router as upload_router
from routes.dashboard_routes import router as dashboard_router


# ---- Crear la aplicación ----
app = FastAPI(
    title="StockPulse API",
    description="Backend del sistema de predicción de demanda StockPulse.",
    version="1.0.0",
)


# ---- CORS ----
# Necesario para que el navegador permita llamadas desde el frontend
# al backend. En producción se limitaría a la URL del frontend real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # En desarrollo permitimos cualquier origen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Registrar routers ----
app.include_router(auth_router)       # /api/auth/login, /api/auth/logout
app.include_router(upload_router)     # /api/upload
app.include_router(dashboard_router)  # /api/dashboard/...


# ---- Health check ----
@app.get("/")
def root():
    """Endpoint de comprobación: confirma que el servidor está corriendo."""
    return {"status": "ok", "proyecto": "StockPulse", "version": "1.0.0"}
