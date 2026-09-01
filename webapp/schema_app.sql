-- Esquema de app.db: la base de la APLICACION WEB (usuarios, sesiones, cursos).
--
-- Deliberadamente separada de observatorio.db, que guarda las series. Tres
-- razones concretas:
--   1. El workflow de ingesta commitea observatorio.db al repo. Si los hashes de
--      contrasena vivieran ahi, se publicarian en GitHub.
--   2. docs/EJECUCION.md documenta "borra observatorio.db para empezar de cero".
--      Eso no puede llevarse puestas las cuentas de los usuarios.
--   3. Las series son append-only por vintage (nunca UPDATE); estas tablas son
--      mutables normales. Son dos filosofias distintas de datos.
--
-- app.db esta en .gitignore y no la toca ni init_db.py ni el cron.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id              INTEGER PRIMARY KEY,
    -- COLLATE NOCASE: el email es el identificador y nadie espera que
    -- Ana@mail.com y ana@mail.com sean cuentas distintas.
    email           TEXT NOT NULL UNIQUE COLLATE NOCASE,
    nombre_completo TEXT NOT NULL,
    -- Formato autodescriptivo "scrypt$n$r$p$salt_b64$hash_b64": permite subir
    -- los parametros de costo en el futuro sin invalidar los hashes viejos.
    password_hash   TEXT NOT NULL,
    creado_en       TEXT NOT NULL,
    actualizado_en  TEXT
);

CREATE TABLE IF NOT EXISTS sesiones (
    -- Se guarda sha256(token) en hex, NO el token. Si alguien se lleva una copia
    -- de app.db no se lleva sesiones vivas: no puede invertir el sha256.
    -- Aca sha256 pelado alcanza (a diferencia de las contrasenas) porque el
    -- token tiene 256 bits de entropia real: no hay diccionario que probar.
    token_hash  TEXT PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    creada_en   TEXT NOT NULL,
    expira_en   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sesiones_usuario ON sesiones(usuario_id);

-- Un renglon por capitulo completado. La ausencia de fila = pendiente.
-- No hay FK a los cursos porque el contenido vive en Python versionado, no en
-- la base: los slugs son el contrato entre ambos.
CREATE TABLE IF NOT EXISTS progreso (
    usuario_id     INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    curso_slug     TEXT NOT NULL,
    capitulo_slug  TEXT NOT NULL,
    completado_en  TEXT NOT NULL,
    PRIMARY KEY (usuario_id, curso_slug, capitulo_slug)
);

-- Freno simple a la fuerza bruta: se cuentan los fallos recientes por email.
CREATE TABLE IF NOT EXISTS intentos_login (
    email   TEXT NOT NULL,
    cuando  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_intentos_email ON intentos_login(email, cuando);

-- Disenada para el "olvide mi contrasena", que hoy NO esta implementado (no hay
-- envio de mail). Queda lista para enchufar el flujo sin migrar nada.
CREATE TABLE IF NOT EXISTS tokens_reset (
    token       TEXT PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    creado_en   TEXT NOT NULL,
    expira_en   TEXT NOT NULL,
    usado_en    TEXT
);

-- Un renglon por (usuario, curso): el ULTIMO intento de la evaluacion de ese
-- curso. "aprobado" es pegajoso -- una vez en 1 no vuelve a 0, aunque un
-- intento posterior de peor puntaje lo pise -- porque el certificado, una vez
-- ganado, no deberia poder perderse por rendir de nuevo. "puntaje" en cambio
-- SI se pisa en cada intento: es "como te fue la ultima vez", no el record.
-- Igual que progreso: sin FK al contenido, el curso_slug es el contrato.
CREATE TABLE IF NOT EXISTS evaluaciones (
    usuario_id     INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    curso_slug     TEXT NOT NULL,
    puntaje        INTEGER NOT NULL,   -- % de respuestas correctas del ultimo intento
    aprobado       INTEGER NOT NULL,   -- 0/1, pegajoso (ver arriba)
    intentos       INTEGER NOT NULL DEFAULT 1,
    completado_en  TEXT NOT NULL,
    PRIMARY KEY (usuario_id, curso_slug)
);
