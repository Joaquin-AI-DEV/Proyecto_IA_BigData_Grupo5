"""
routes/auth_routes.py — Endpoints de autenticación
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Endpoints:
    POST /api/auth/login   → Valida credenciales y devuelve token
    POST /api/auth/logout  → Invalida token y borra datos de BD
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from auth import authenticate_user, create_session, destroy_session

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


# ---- Modelos de request ----

class LoginRequest(BaseModel):
    """Cuerpo de la petición de login."""
    username: str
    password: str


# ---- Endpoints ----

@router.post("/login")
def login(body: LoginRequest):
    """
    Autentica al usuario contra la tabla 'usuarios' de Supabase.
    Si las credenciales son correctas, devuelve un token de sesión.

    Retorna:
        {
            "token": "uuid-del-token",
            "username": "admin"
        }
    """
    # Validar que los campos no estén vacíos
    if not body.username.strip() or not body.password:
        raise HTTPException(status_code=400, detail="Rellena todos los campos.")

    # Verificar credenciales contra la BD
    if not authenticate_user(body.username.strip(), body.password):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")

    # Crear sesión y devolver token
    token = create_session(body.username.strip())
    return {"token": token, "username": body.username.strip()}


@router.post("/logout")
def logout(authorization: str = Header(None)):
    """
    Cierra la sesión del usuario.
    Invalida el token y borra los datos de la BD (comportamiento solicitado).

    Header requerido:
        Authorization: Bearer <token>
    """
    token = _extract_token(authorization)

    username = destroy_session(token)

    if not username:
        # Si el token no existía, simplemente respondemos OK
        # (el frontend puede llamar a logout aunque la sesión ya expiró)
        return {"message": "Sesión cerrada."}

    return {"message": f"Sesión de '{username}' cerrada. Datos eliminados."}


# ---- Helper ----

def _extract_token(authorization: str | None) -> str:
    """
    Extrae el token del header 'Authorization: Bearer <token>'.

    Excepciones:
        HTTPException 401: Si el header no existe o tiene formato incorrecto.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de sesión requerido.")
    return authorization.split(" ", 1)[1]