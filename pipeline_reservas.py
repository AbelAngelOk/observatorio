"""
Pipeline de reservas internacionales del BCRA.

Es el pipeline modelo del proyecto: la fuente es la API de series de tiempo de
datos.gob.ar, o sea HTTP + JSON, sin scraping, sin Excel y sin robots.txt de por
medio. Si un indicador nuevo esta en ese catalogo, se copia este archivo y se
cambia el id de serie.

Hasta ahora esta serie NO pasaba por la base: el navegador del visitante le
pegaba en vivo a la API desde index.html. Eso rompia la premisa de que la base
es la fuente de verdad, y hacia que el panel principal del sitio dependiera de
que una API externa estuviera arriba justo cuando alguien entra. Ahora la serie
se ingiere aca y el front la lee de data/reservas_internacionales.json como a
todas las demas.

Uso:
    pip install -r requirements.txt
    python pipeline_reservas.py
    python export_json.py        # o directamente: python actualizar.py
"""

import core

SERIE_API = "92.2_RESERVAS_IRES_0_0_32_40"  # diaria, la que consumia el front
SERIE_SLUG = "reservas_internacionales"

NOMBRE = "reservas"  # como queda registrado en la tabla 'ingestas'


def main() -> int:
    with core.corrida(NOMBRE) as ctx:
        core.ingerir_serie_api(ctx, SERIE_SLUG, SERIE_API, "diaria")
        nuevas = ctx.nuevas

    print(f"OK reservas: {nuevas} nuevos o revisados.")
    return nuevas


if __name__ == "__main__":
    main()
