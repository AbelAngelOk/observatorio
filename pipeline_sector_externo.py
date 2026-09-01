"""
Pipeline del sector externo (INDEC, via API de series de datos.gob.ar).

Reemplaza los puntos que estaban cargados a mano por las series oficiales
completas: cuenta corriente pasa de 8 trimestres a ~80, y deuda externa de 4
puntos a ~75.

Por que arrancan en 2006 y no en 2000: el INDEC publica balanza de pagos y
posicion de inversion internacional bajo la metodologia del MBP6, cuya serie
empieza en el primer trimestre de 2006. Las cifras anteriores existen con otra
metodologia y NO son empalmables sin un ajuste que no vamos a inventar.

La serie de deuda externa de la API llega hasta el ultimo trimestre publicado en
el catalogo (hoy, IV-2024). Los trimestres mas recientes que ya teniamos cargados
a mano conviven sin problema: cada uno es una fecha distinta.

Uso:
    python pipeline_sector_externo.py
"""

import core

NOMBRE = "sector_externo"

# slug en la base            -> (id de serie en la API, frecuencia)
SERIES = {
    "cuenta_corriente":       ("160.2_TL_CUENNTE_0_T_22", "trimestral"),  # 2006 -> hoy
    "cuenta_corriente_anual": ("160.1_TL_CUENNTE_0_A_22", "anual"),       # 2006 -> hoy
    "deuda_externa_bruta":    ("161.1_TL_DEUDRNA_0_0_19", "trimestral"),  # 2006 -> IV-2024
    # Comercio exterior (Intercambio Comercial Argentino), trimestral desde 1992.
    "exportaciones":          ("74.2_IET_0_T_16", "trimestral"),          # expo totales FOB
    "importaciones":          ("74.2_IIT_0_T_25", "trimestral"),          # impo totales CIF
}


def main() -> int:
    with core.corrida(NOMBRE) as ctx:
        for slug, (serie_api, frecuencia) in SERIES.items():
            # saltear_ceros solo para la anual: al colapsar los trimestres, la API
            # devuelve el anio en curso todavia vacio como 0.
            core.ingerir_serie_api(ctx, slug, serie_api, frecuencia,
                                   start_date="2003-01-01",
                                   saltear_ceros=(frecuencia == "anual"))
        nuevas = ctx.nuevas

    print(f"OK sector externo: {nuevas} observaciones nuevas o revisadas.")
    return nuevas


if __name__ == "__main__":
    main()
