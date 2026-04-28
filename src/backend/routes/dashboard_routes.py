"""
routes/dashboard_routes.py — Endpoints de datos para el dashboard
Proyecto: StockPulse
Autor: Sergio Romero (Data Engineer)

Endpoints:
    GET /api/dashboard/kpis                  → KPIs globales (ventas totales, unidades, productos)
    GET /api/dashboard/productos             → Lista de productos para el selector
    GET /api/dashboard/ventas/{id_producto}  → Ventas del último mes por producto
    GET /api/dashboard/predicciones/{id}     → Predicciones por producto (de la tabla predicciones)

Estos endpoints son los que Jimmy Chen necesita para alimentar los gráficos del frontend.
"""

from fastapi import APIRouter, HTTPException, Header
from database import get_connection
from auth import get_session_user

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


# ---- Helpers ----

def _extract_token(authorization: str | None) -> str:
    """Extrae y valida el token del header Authorization."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de sesión requerido.")
    return authorization.split(" ", 1)[1]


def _require_session(authorization: str | None) -> str:
    """Valida que la sesión sea activa. Retorna el username."""
    token = _extract_token(authorization)
    user = get_session_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Sesión no válida o expirada.")
    return user


# ---- Endpoints ----

@router.get("/kpis")
def get_kpis(authorization: str = Header(None)):
    """
    Devuelve los KPIs globales para las tarjetas del dashboard:
      - Total de ventas (suma de total_venta)
      - Total de unidades vendidas
      - Número de productos distintos en el dataset

    Retorna:
        {
            "ventas_totales": 8887.25,
            "unidades_totales": 521243,
            "productos_distintos": 3684
        }
    """
    _require_session(authorization)

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    ROUND(SUM(total_venta)::numeric, 2)  AS ventas_totales,
                    SUM(unidades_vendidas)                AS unidades_totales
                FROM ventas;
            """)
            row_ventas = cur.fetchone()

            cur.execute("SELECT COUNT(*) AS total FROM productos;")
            row_productos = cur.fetchone()

        conn.close()

        return {
            "ventas_totales": float(row_ventas["ventas_totales"] or 0),
            "unidades_totales": int(row_ventas["unidades_totales"] or 0),
            "productos_distintos": int(row_productos["total"] or 0),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener KPIs: {str(e)}")


@router.get("/productos")
def get_productos(authorization: str = Header(None)):
    """
    Devuelve la lista de productos disponibles para el selector del dashboard.

    Retorna:
        [
            { "id_producto": "85123A", "nombre": "WHITE HANGING HEART..." },
            ...
        ]
    """
    _require_session(authorization)

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id_producto, nombre
                FROM productos
                ORDER BY nombre
                LIMIT 500;
            """)
            rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener productos: {str(e)}")


@router.get("/ventas/{id_producto}")
def get_ventas_producto(id_producto: str, authorization: str = Header(None)):
    """
    Devuelve las ventas diarias del último mes para un producto concreto.
    Utilizado por el gráfico 'Ventas último mes' del dashboard.

    Parámetros:
        id_producto (str): Código del producto (StockCode del dataset).

    Retorna:
        {
            "fechas": ["2011-11-01", "2011-11-02", ...],
            "unidades": [45, 30, 62, ...]
        }
    """
    _require_session(authorization)

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    fecha_venta,
                    SUM(unidades_vendidas) AS unidades
                FROM ventas
                WHERE id_producto = %s
                  AND fecha_venta >= (
                      SELECT MAX(fecha_venta) - INTERVAL '30 days'
                      FROM ventas
                      WHERE id_producto = %s
                  )
                GROUP BY fecha_venta
                ORDER BY fecha_venta;
            """, (id_producto, id_producto))
            rows = cur.fetchall()
        conn.close()

        return {
            "fechas":   [str(row["fecha_venta"]) for row in rows],
            "unidades": [int(row["unidades"]) for row in rows],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener ventas: {str(e)}")


@router.get("/predicciones/{id_producto}")
def get_predicciones_producto(id_producto: str, authorization: str = Header(None)):
    """
    Devuelve las predicciones generadas por el modelo ML (Deninson)
    para un producto concreto. Alimenta el gráfico 'Predicción próximo mes'.

    Parámetros:
        id_producto (str): Código del producto.

    Retorna:
        {
            "fechas":     ["2011-12-01", "2011-12-02", ...],
            "predichas":  [50, 43, 67, ...],
            "confianza":  0.87
        }
    """
    _require_session(authorization)

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    fecha_prediccion,
                    unidades_predichas,
                    confianza_modelo
                FROM predicciones
                WHERE id_producto = %s
                ORDER BY fecha_prediccion;
            """, (id_producto,))
            rows = cur.fetchall()
        conn.close()

        if not rows:
            # El modelo aún no ha generado predicciones para este producto
            return {"fechas": [], "predichas": [], "confianza": None}

        # La confianza del modelo se toma como el promedio de todas las predicciones
        confianza_media = sum(
            float(r["confianza_modelo"]) for r in rows if r["confianza_modelo"]
        ) / len(rows)

        return {
            "fechas":    [str(row["fecha_prediccion"]) for row in rows],
            "predichas": [int(row["unidades_predichas"] or 0) for row in rows],
            "confianza": round(confianza_media, 4),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener predicciones: {str(e)}")


# Endpoint para la predicción global (modelo agregado diario, sin id_producto).
# Lo consume el dashboard para el gráfico "ventas reales vs predichas".
@router.get("/predicciones-globales")
def get_predicciones_globales(authorization: str = Header(None)):
    """
    Devuelve la serie temporal de predicciones del modelo agregado (Ridge).
    Cada fila representa un día con sus ventas reales y predichas (sin producto).

    Retorna:
        {
            "fechas":    ["2011-11-01", ...],
            "reales":    [123, 145, ...],
            "predichas": [130, 140, ...]
        }
    """
    _require_session(authorization)

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # Filtramos por id_producto IS NULL: así aislamos las predicciones
            # del modelo agregado y no las mezclamos con posibles predicciones
            # per-producto que se añadan en el futuro.
            cur.execute("""
                SELECT fecha_prediccion, unidades_vendidas, unidades_predichas
                FROM predicciones
                WHERE id_producto IS NULL
                ORDER BY fecha_prediccion;
            """)
            rows = cur.fetchall()
        conn.close()

        return {
            "fechas":    [str(r["fecha_prediccion"]) for r in rows],
            "reales":    [int(r["unidades_vendidas"] or 0) for r in rows],
            "predichas": [int(r["unidades_predichas"] or 0) for r in rows],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener predicciones globales: {str(e)}")


@router.get("/inversion/{id_producto}")
def get_inversion_producto(id_producto: str, authorization: str = Header(None)):
    """
    Calcula la inversión prevista para el próximo mes combinando
    predicciones de unidades con el precio unitario del producto.

    Retorna:
        {
            "fechas":    ["2011-12-01", ...],
            "inversion": [125.50, 98.20, ...]
        }
    """
    _require_session(authorization)

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # Precio unitario del producto
            cur.execute(
                "SELECT precio_unitario FROM productos WHERE id_producto = %s",
                (id_producto,)
            )
            prod = cur.fetchone()

            if not prod:
                return {"fechas": [], "inversion": []}

            precio = float(prod["precio_unitario"])

            # Predicciones del modelo
            cur.execute("""
                SELECT fecha_prediccion, unidades_predichas
                FROM predicciones
                WHERE id_producto = %s
                ORDER BY fecha_prediccion;
            """, (id_producto,))
            rows = cur.fetchall()

        conn.close()

        return {
            "fechas":    [str(r["fecha_prediccion"]) for r in rows],
            "inversion": [round((r["unidades_predichas"] or 0) * precio, 2) for r in rows],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al calcular inversión: {str(e)}")
 