"""
Conexion a app.db, la base de la aplicacion web.

No reusa core.get_conn() a proposito: esa funcion abre observatorio.db con ruta
RELATIVA y hace raise SystemExit si el archivo falta. Las dos cosas son veneno
en un servidor: el cwd de uvicorn puede ser cualquiera, y un SystemExit dentro
de un handler HTTP tumba el worker en vez de devolver un error.

Aca todo es al reves: ruta absoluta anclada al archivo, y si la base no existe
se crea.
"""

import sqlite3
from pathlib import Path

# Anclado al repo, no al cwd: uvicorn puede arrancar desde cualquier carpeta.
RAIZ = Path(__file__).resolve().parent.parent
DB_PATH = RAIZ / "app.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema_app.sql"


def get_conn() -> sqlite3.Connection:
    """Conexion nueva por request. SQLite no comparte conexiones entre hilos."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_app_db() -> None:
    """Crea o migra app.db. Idempotente (el esquema es CREATE IF NOT EXISTS),
    asi que se llama en cada arranque del servidor."""
    conn = sqlite3.connect(DB_PATH)
    # WAL: permite leer mientras se escribe. Con varios requests concurrentes
    # sobre la misma base, el modo journal por defecto da 'database is locked'.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
