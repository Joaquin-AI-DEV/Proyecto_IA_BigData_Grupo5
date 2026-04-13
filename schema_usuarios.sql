-- =============================================================
-- schema_usuarios.sql
-- Proyecto: StockPulse
-- Descripción: Crea la tabla de usuarios para autenticación.
--              Ejecutar en Supabase → SQL Editor.
-- =============================================================

-- Tabla de usuarios del sistema
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario  SERIAL          PRIMARY KEY,
    username    VARCHAR(50)     NOT NULL UNIQUE,
    -- Contraseña almacenada como hash bcrypt (NUNCA texto plano)
    password    VARCHAR(255)    NOT NULL,
    created_at  TIMESTAMP       DEFAULT NOW()
);

-- Insertar el usuario admin inicial con la contraseña hasheada.
-- El hash corresponde a 'admin123' generado con bcrypt (rounds=12).
-- Una vez el sistema esté en producción, cambiar esta contraseña
-- desde el propio backend o eliminando y recreando el usuario.
INSERT INTO usuarios (username, password)
VALUES (
    'admin',
    '$2b$12$hNDo9S/3e4J0M29bQH5aSuY0HjZsCahaCxcBDVuLJI3xUcsK.gF3m'
)
ON CONFLICT (username) DO NOTHING;

-- Verificar inserción
SELECT id_usuario, username, created_at FROM usuarios;
