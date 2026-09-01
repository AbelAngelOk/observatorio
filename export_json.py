"""
Exporta cada serie de observatorio.db a data/<slug>.json, en el mismo
formato {indicador, unidad, fuente, datos: [{fecha, valor}, ...]} que ya
usan los pipelines existentes. index.html puede pasar a leer estos archivos
via fetch() en vez de tener los arrays de datos escritos a mano en el JS.

Uso:
    python export_json.py
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path("observatorio.db")
OUTPUT_DIR = Path("data")


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    slugs = [r["slug"] for r in conn.execute("SELECT DISTINCT slug FROM series ORDER BY slug")]

    OUTPUT_DIR.mkdir(exist_ok=True)
    for slug in slugs:
        rows = conn.execute(
            """SELECT fecha, valor, es_provisorio, fuente_url
               FROM series_con_datos WHERE slug = ? ORDER BY fecha""",
            (slug,),
        ).fetchall()

        if not rows:
            continue

        meta = conn.execute(
            """SELECT nombre, unidad, metodologia, fuente_nombre, tipo_acceso
               FROM series_con_datos WHERE slug = ? LIMIT 1""",
            (slug,),
        ).fetchone()

        payload = {
            "indicador": meta["nombre"],
            "unidad": meta["unidad"],
            "metodologia": meta["metodologia"],
            "fuente": meta["fuente_nombre"],
            "tipo_acceso_fuente": meta["tipo_acceso"],
            "datos": [
                {
                    "fecha": r["fecha"],
                    "valor": r["valor"],
                    "provisorio": bool(r["es_provisorio"]),
                }
                for r in rows
            ],
        }

        out_path = OUTPUT_DIR / f"{slug}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"OK: {slug} -> {out_path} ({len(rows)} observaciones)")

    exportar_meta(conn)
    conn.close()


def exportar_meta(conn):
    """Escribe data/_meta.json con el estado de la ultima corrida de cada
    pipeline. El sitio lo usa para mostrar la fecha real de los datos: antes el
    encabezado mostraba new Date(), o sea la fecha de hoy, aunque la ingesta
    estuviera rota hace dos semanas.
    """
    ingestas = [dict(r) for r in conn.execute(
        "SELECT pipeline, inicio, estado, filas_nuevas FROM ultima_ingesta ORDER BY pipeline"
    )]
    exitosas = [i["inicio"] for i in ingestas if i["estado"] == "ok"]

    meta = {
        "ultima_ingesta_ok": max(exitosas) if exitosas else None,
        "pipelines": ingestas,
    }
    (OUTPUT_DIR / "_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: _meta.json (ultima ingesta OK: {meta['ultima_ingesta_ok'] or 'nunca'})")


if __name__ == "__main__":
    main()
