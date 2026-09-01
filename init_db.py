"""
Crea observatorio.db a partir de schema.sql y carga las observaciones que
fueron verificadas a mano contra comunicados oficiales (los puntos sueltos que
todavia no tienen un pipeline que los traiga solo).

Es idempotente y seguro de correr sobre una base que ya existe: el esquema usa
CREATE ... IF NOT EXISTS, y la semilla entra siempre con el mismo vintage. Por
eso tambien sirve para migrar una base vieja cuando se agrega una tabla nueva.

Uso:
    python init_db.py            # crea la base y carga la semilla
    python actualizar.py         # corre los pipelines y exporta a data/
"""

import sqlite3
from pathlib import Path

import core
from core import insertar_observacion  # la unica version vive en core.py

DB_PATH = core.DB_PATH
SCHEMA_PATH = Path("schema.sql")

# Vintage fijo para la semilla, en vez de la fecha de corrida. Dos razones:
# 1) el UNIQUE de observaciones incluye el vintage, asi que con now() cada
#    corrida de este script volveria a insertar la semilla entera como si
#    fueran revisiones nuevas;
# 2) ultimo_vintage resuelve por MAX(vintage), asi que un vintage viejo hace
#    que cualquier dato que cargue un pipeline real pise al punto manual.
VINTAGE_SEMILLA = "2000-01-01T00:00:00+00:00"


def get_conn() -> sqlite3.Connection:
    # No usa core.get_conn() porque este script es el unico que puede correr
    # cuando la base todavia no existe.
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema():
    conn = get_conn()
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()


# Semilla: los puntos verificados a mano, para no arrancar con la base vacia.
# Los pipelines van agregando (y revisando) el resto. Correr este script de
# nuevo es inofensivo: la semilla entra siempre con VINTAGE_SEMILLA.
#
# reservas_internacionales no esta aca a proposito: la trae entera
# pipeline_reservas.py desde la API.
SEMILLA = {
    "deuda_publica_bruta": [
        ("2023-11-30", 425294), ("2023-12-31", 370664), ("2024-03-31", 403044),
        ("2024-10-31", 462553), ("2024-12-31", 466686), ("2025-01-31", 467788),
        ("2025-05-31", 461019), ("2025-06-30", 465355), ("2025-10-31", 442196),
        ("2025-12-31", 455067),
    ],
    "resultado_primario": [
        ("2024-07-31", 908.3), ("2024-12-31", -1301.0), ("2025-04-30", 846.0),
        ("2025-09-30", 697.0), ("2026-03-31", 930.3), ("2026-04-30", 632.8),
    ],
    "resultado_financiero": [
        ("2024-07-31", -601.0), ("2024-12-31", -1557.3), ("2025-04-30", 572.3),
        ("2025-09-30", 309.6), ("2026-03-31", 484.8), ("2026-04-30", 268.1),
    ],
    "gasto_nacion": [
        ("2023-12-31", 6218.4), ("2024-12-31", 11172.2), ("2026-03-31", 10911.1),
    ],
    "cuenta_corriente": [
        ("2024-03-31", 176), ("2024-06-30", 3732), ("2024-09-30", 1401), ("2024-12-31", 1029),
        ("2025-03-31", -5191), ("2025-06-30", -3016), ("2025-09-30", -1581), ("2025-12-31", 2294),
    ],
    "deuda_externa_bruta": [
        ("2022-03-31", 274355), ("2025-09-30", 316935), ("2025-12-31", 319522), ("2026-03-31", 321783),
    ],
    "presion_tributaria": [
        ("2024-12-31", 22.5), ("2025-12-31", 21.4),
    ],
    "deuda_consolidada": [
        ("2023-11-30", 495599), ("2024-12-31", 477169),
    ],
    "deuda_neta": [
        ("2023-11-30", 290000), ("2025-06-30", 282000),
    ],
    "cartera_cer": [
        ("2025-06-30", 55.9),
    ],
    "cartera_tasa_fija": [
        ("2025-06-30", 42.0),
    ],
    "cartera_dolar_linked": [
        ("2025-06-30", 2.1),
    ],
    "resultado_primario_anual_pbi": [
        ("2023-12-31", -2.9), ("2024-12-31", 1.8), ("2025-12-31", 1.4),
    ],
    "cuenta_corriente_anual": [
        ("2023-12-31", -20956), ("2024-12-31", 6285), ("2025-12-31", -7582),
    ],
}


def cargar_semilla():
    conn = get_conn()
    total = nuevas = 0
    for slug, puntos in SEMILLA.items():
        for fecha, valor in puntos:
            nuevas += insertar_observacion(
                conn, slug, fecha, valor,
                fuente_url="cargado manualmente desde el chat", es_provisorio=True,
                vintage=VINTAGE_SEMILLA)
            total += 1
    conn.commit()
    conn.close()
    print(f"OK: {nuevas} observaciones nuevas de {total} en la semilla "
          f"({total - nuevas} ya estaban) -> {DB_PATH}")


if __name__ == "__main__":
    init_schema()
    cargar_semilla()
