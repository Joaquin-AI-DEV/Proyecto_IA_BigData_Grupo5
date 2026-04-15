“””
main.py — Punto de entrada del backend FastAPI
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Responsabilidad:
Configura la aplicación FastAPI, registra todos los routers,
habilita CORS y sirve el frontend (index.html) directamente
desde http://localhost:8000

Uso:
Desde la carpeta src/backend/:
uvicorn main:app –reload –port 8000

```
Luego abrir http://localhost:8000 en el navegador — carga el index.html automáticamente.
```

“””

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Importar los routers de cada módulo

from routes.auth_routes import router as auth_router
from routes.upload_routes import router as upload_router
from routes.dashboard_routes import router as dashboard_router

# –– Crear la aplicación ––

app = FastAPI(
title=“StockPulse API”,
description=“Backend del sistema de predicción de demanda StockPulse.”,
version=“1.0.0”,
)

# –– CORS ––

# Necesario para que el navegador permita llamadas desde el frontend

# al backend. En producción se limitaría a la URL del frontend real.

app.add_middleware(
CORSMiddleware,
allow_origins=[”*”],        # En desarrollo permitimos cualquier origen
allow_credentials=True,
allow_methods=[”*”],
allow_headers=[”*”],
)

# –– Registrar routers de la API ––

app.include_router(auth_router)       # /api/auth/login, /api/auth/logout
app.include_router(upload_router)     # /api/upload
app.include_router(dashboard_router)  # /api/dashboard/…

# –– Servir el frontend ––

# Ruta a la carpeta frontend relativa a src/backend/

FRONTEND_DIR = os.path.join(os.path.dirname(**file**), “..”, “frontend”)

# Montar archivos estáticos (styles.css, app.js) bajo /static

app.mount(”/static”, StaticFiles(directory=FRONTEND_DIR), name=“static”)

@app.get(”/”)
def serve_frontend():
“””
Sirve el index.html al abrir http://localhost:8000 en el navegador.
Así no hace falta abrir el HTML manualmente — uvicorn lo sirve todo.
“””
return FileResponse(os.path.join(FRONTEND_DIR, “index.html”))
