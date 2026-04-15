"""
auth.py — Gestión de sesiones y tokens
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Responsabilidad:
    Gestiona los tokens de sesión activos en memoria.
    Cuando el usuario hace login se genera un token UUID único.
    Cuando hace logout el token se elimina, invalidando la sesión.

    Además, cuando el usuario cierra sesión, se borran todos los
    registros de ventas y productos que subió durante su sesión
    (comportamiento solicitado por Joaquín en el Discord).

    NOTA: Este sistema de sesiones en memoria es suficiente para
    el alcance del proyecto (demo académica). En producción se
    usaría JWT con firma o almacenamiento de sesiones en Redis.
"""

import uuid
import bcrypt
from database import get_connection


# Almacén de sesiones activas: { token: username }
# Se pierde al reiniciar el servidor, lo cual es el comportamiento deseado
_active_sessions: dict[str, str] = {}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su hash bcrypt.

    Parámetros:
        plain_password (str): Contraseña introducida por el usuario.
        hashed_password (str): Hash almacenado en la base de datos.

    Retorna:
        bool: True si coinciden, False si no.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def authenticate_user(username: str, password: str) -> bool:
    """
    Consulta la tabla 'usuarios' en Supabase y verifica las credenciales.

    Parámetros:
        username (str): Nombre de usuario.
        password (str): Contraseña en texto plano.

    Retorna:
        bool: True si las credenciales son correctas, False si no.
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT password FROM usuarios WHERE username = %s",
                (username,)
            )
            row = cur.fetchone()
        conn.close()

        if not row:
            return False  # Usuario no existe

        return verify_password(password, row["password"])

    except Exception as e:
        print(f"[AUTH] Error al autenticar usuario: {e}")
        return False


def create_session(username: str) -> str:
    """
    Crea una nueva sesión para el usuario y devuelve el token generado.

    Parámetros:
        username (str): Nombre del usuario que ha iniciado sesión.

    Retorna:
        str: Token UUID único de sesión.
    """
    token = str(uuid.uuid4())
    _active_sessions[token] = username
    print(f"[AUTH] Sesión creada para '{username}' — token: {token[:8]}...")
    return token


def get_session_user(token: str) -> str | None:
    """
    Devuelve el nombre de usuario asociado a un token activo.

    Parámetros:
        token (str): Token de sesión del cliente.

    Retorna:
        str | None: Username si la sesión existe, None si no.
    """
    return _active_sessions.get(token)


def destroy_session(token: str) -> str | None:
    """
    Elimina la sesión activa y limpia los datos de BD del usuario.
    Esta es la lógica de 'cerrar sesión borra los datos' que pidió Joaquín.

    Parámetros:
        token (str): Token de sesión a invalidar.

    Retorna:
        str | None: Username si la sesión existía, None si no.
    """
    username = _active_sessions.pop(token, None)

    if username:
        print(f"[AUTH] Sesión destruida para '{username}'.")
        _clear_user_data()

    return username


def _clear_user_data() -> None:
    """
    Borra todos los registros de ventas, productos y predicciones de la BD.
    Se llama automáticamente al cerrar sesión.

    NOTA: Borra toda la BD porque el sistema es monousuario en esta fase.
    Cuando haya múltiples usuarios reales, habría que filtrar por id_usuario.
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # Borrar en orden inverso a las FK para evitar violaciones de restricción
            cur.execute("DELETE FROM predicciones;")
            cur.execute("DELETE FROM ventas;")
            cur.execute("DELETE FROM productos;")
        conn.commit()
        conn.close()
        print("[AUTH] Datos de la BD borrados al cerrar sesión.")
    except Exception as e:
        print(f"[AUTH] Error al limpiar datos de BD: {e}")


def is_valid_token(token: str) -> bool:
    """
    Comprueba si un token de sesión es válido.

    Parámetros:
        token (str): Token a verificar.

    Retorna:
        bool: True si el token es válido, False si no.
    """
    return token in _active_sessions
