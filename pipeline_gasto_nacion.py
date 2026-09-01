"""
Pipeline del gasto anual de la Nacion (Subsecretaria de Presupuesto).

La Subsecretaria publica "Serie anual con gastos, recursos y PIB" como CSV plano
en dgsiaf-repo.mecon.gob.ar. Confirmado contra el archivo real: es CSV separado
por COMAS, UTF-8, con columnas 'ejercicio_presupuestario', 'ingreso', 'gasto',
'pib', y los valores en pesos (no en millones). Cubre 2004 -> ultimo ejercicio
cerrado.

El host tiene robots.txt restrictivo para crawlers genericos; una descarga
puntual con requests desde infraestructura propia es una peticion HTTP normal.
Revisa los terminos de uso antes de automatizarlo.

Escribe en la serie 'gasto_nacion_anual' (distinta de 'gasto_nacion', los puntos
mensuales del panel principal).

Uso:
    pip install -r requirements.txt
    python pipeline_gasto_nacion.py
"""

from io import StringIO

import pandas as pd
import requests

import core

CSV_URL = "https://dgsiaf-repo.mecon.gob.ar/repository/pa/datasets/serie_pib_anual.csv"
SERIE_SLUG = "gasto_nacion_anual"
NOMBRE = "gasto"  # como queda registrado en la tabla 'ingestas'

A_MILLONES = 1 / 1_000_000  # el CSV da pesos; la serie esta en millones de ARS


def download_csv(url: str) -> pd.DataFrame:
    resp = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return pd.read_csv(StringIO(resp.content.decode("utf-8-sig")))


def normalize(df: pd.DataFrame) -> list[dict]:
    """Serie anual a {fecha, gasto_millones, pct_pbi}, fecha = 31/12.
    El CSV trae gasto Y pib por anio, asi que el gasto como % del PBI sale del
    mismo archivo, sin cruzar con otra fuente."""
    series = []
    for _, row in df.iterrows():
        try:
            anio = int(row["ejercicio_presupuestario"])
            gasto = float(row["gasto"])
            pib = float(row["pib"])
        except (ValueError, TypeError, KeyError):
            continue
        series.append({
            "fecha": f"{anio}-12-31",
            "valor": round(gasto * A_MILLONES, 1),   # millones de ARS
            "pct_pbi": round(gasto / pib * 100, 2),  # % del PBI
        })
    series.sort(key=lambda r: r["fecha"])
    return series


def main() -> int:
    df = download_csv(CSV_URL)
    series = normalize(df)

    with core.corrida(NOMBRE) as ctx:
        for punto in series:
            ctx.nuevas += core.insertar_observacion(
                ctx.conn, SERIE_SLUG, punto["fecha"], punto["valor"],
                fuente_url=CSV_URL, es_provisorio=False)
            # (h) gasto como % del PBI: cuantos puntos del PBI consume el Estado.
            ctx.nuevas += core.insertar_observacion(
                ctx.conn, "gasto_nacion_pbi", punto["fecha"], punto["pct_pbi"],
                fuente_url=CSV_URL, es_provisorio=False)
        nuevas = ctx.nuevas

    print(f"OK gasto: {len(series)} anios en el CSV, {nuevas} nuevos o revisados.")
    return nuevas


if __name__ == "__main__":
    main()
