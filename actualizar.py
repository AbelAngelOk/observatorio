"""
Runner de la ingesta: el unico comando que necesita el cron.

Corre los pipelines habilitados, deja cada corrida registrada en la tabla
'ingestas' (con su error si fallo), y despues exporta a data/*.json para que el
sitio quede sincronizado con la base. Esto ultimo importa: la base y el sitio se
desincronizan en silencio si alguien actualiza una y se olvida de la otra.

Un pipeline que falla no tumba a los demas: se registra el error, se sigue, y al
final el script sale con codigo != 0 para que el job se vea rojo en CI.

Uso:
    python actualizar.py                            # solo los pipelines confiables
    python actualizar.py --incluir-experimentales   # tambien deuda y gasto
    python actualizar.py --solo reservas
"""

import argparse
import importlib
import sys
import traceback

import export_json

# Un pipeline es "experimental" mientras su parseo dependa de un archivo cuyo
# layout puede cambiar sin aviso (un Excel, un CSV de un host suelto). No corren
# en la ingesta diaria: un job desatendido no deberia poder meter en la base el
# resultado de un scraping que se rompio en silencio. Ver docs/PIPELINES.md.
#
# Los que salen de la API de series de datos.gob.ar son confiables: JSON
# estable, con contrato. Corren todos los dias.
#
# Los modulos se importan solo cuando se los va a correr: los experimentales
# necesitan openpyxl y pandas, y no queremos que la ingesta diaria se caiga
# porque falta una dependencia que ningun pipeline de API usa.
PIPELINES = {
    # nombre           modulo                       experimental
    "reservas":        ("pipeline_reservas",        False),
    "cotizaciones":    ("pipeline_cotizaciones",    False),  # blue, oficial, pasivos BCRA
    "sector_externo":  ("pipeline_sector_externo",  False),  # cuenta cte, deuda ext, expo/impo
    "fiscal":          ("pipeline_fiscal",          False),  # usa blue + cuenta cte + pbi
    "recaudacion":     ("pipeline_recaudacion",     False),
    "deuda":           ("pipeline_deuda_publica",   True),   # boletin mensual Excel
    "gasto":           ("pipeline_gasto_nacion",    True),   # CSV de un host con robots.txt
    "deuda_historica": ("pipeline_deuda_historica", True),   # A.2.5 + consolidada/neta
    "cartera":         ("pipeline_cartera",         True),   # A.1.4 por anio
    "deuda_residencia": ("pipeline_deuda_residencia", True), # A.4.5 residentes/no residentes
}

# El orden respeta las dependencias entre series calculadas:
#   - fiscal necesita dolar_blue (cotizaciones) y cuenta_corriente_anual (sector_externo);
#   - recaudacion necesita pbi_anual (lo carga fiscal);
#   - deuda_historica (consolidada/neta) necesita deuda bruta (boletin + su backfill),
#     pasivos_bcra + dolar_oficial (cotizaciones) y reservas -> va al final.
ORDEN = ["reservas", "cotizaciones", "sector_externo", "fiscal", "recaudacion",
         "deuda", "gasto", "deuda_historica", "cartera", "deuda_residencia"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--incluir-experimentales", action="store_true",
                    help="corre tambien los pipelines cuyo parseo no esta confirmado")
    ap.add_argument("--solo", metavar="NOMBRE",
                    help="corre un unico pipeline (ignora si es experimental)")
    args = ap.parse_args()

    if args.solo:
        if args.solo not in PIPELINES:
            raise SystemExit(f"Pipeline desconocido: '{args.solo}'. "
                             f"Conocidos: {', '.join(PIPELINES)}")
        elegidos = [args.solo]
    else:
        elegidos = [
            nombre for nombre in ORDEN
            if not PIPELINES[nombre][1] or args.incluir_experimentales
        ]

    print(f"Pipelines a correr: {', '.join(elegidos)}\n")

    fallidos = []
    for nombre in elegidos:
        try:
            modulo = importlib.import_module(PIPELINES[nombre][0])
            modulo.main()
        except Exception:
            # core.corrida() ya dejo el error asentado en la tabla 'ingestas';
            # aca solo lo mostramos y seguimos con el proximo pipeline.
            fallidos.append(nombre)
            print(f"FALLO {nombre}:\n{traceback.format_exc(limit=3)}", file=sys.stderr)

    print()
    export_json.main()

    if fallidos:
        raise SystemExit(f"\nTerminado con errores en: {', '.join(fallidos)}")
    print("\nListo: base actualizada y data/*.json sincronizados.")


if __name__ == "__main__":
    main()
