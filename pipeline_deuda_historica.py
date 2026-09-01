"""
Pipeline experimental: deuda historica y deuda consolidada / neta.

Hace dos cosas, ambas apoyadas en el boletin TRIMESTRAL de la deuda (distinto
del mensual):

1. BACKFILL de deuda bruta anual 2003-2018. La hoja A.2.5 del boletin trae la
   "Serie de deuda del SPN por anio" desde 1992, en millones de USD. Cargamos los
   anios anteriores a 2019 (de 2019 en adelante ya los trae el boletin mensual,
   con mejor granularidad).

2. Construccion de deuda_consolidada y deuda_neta, anual, a partir de series que
   ya estan en la base:
      consolidada = deuda_bruta_USD + pasivos_bcra_ARS / TC_oficial   (cierre de anio)
      neta        = consolidada - reservas
   Es la "cuenta del analista" (misma logica que Chequeado / EcoGo). LIMITE
   conocido: NO resta las tenencias intra-sector publico (Letras Intransferibles,
   Adelantos Transitorios), que no se publican como serie limpia. Es una
   aproximacion, y asi esta etiquetada en schema.sql.

Es EXPERIMENTAL: depende del layout del Excel trimestral. No corre en el cron.
Tiene que correr DESPUES de pipeline_deuda_publica (boletin mensual),
pipeline_cotizaciones (pasivos + TC) y pipeline_reservas.

Uso:
    python pipeline_deuda_historica.py
"""

import datetime as dt
import io
import os
import re

import requests
import openpyxl

import core

NOMBRE = "deuda_historica"
TRIM_PAGE = "https://www.argentina.gob.ar/economia/finanzas/datos-trimestrales-de-la-deuda"
# La hoja A.2.5 ("serie de deuda por anio 1992/2019") existe en los boletines
# hasta ~2019 y fue eliminada en los mas recientes. Como esa serie es historia
# estatica (no cambia), usamos un archivo fijo conocido que la contiene y que
# cubre justo el rango que backfilleamos (<2019). Si algun dia cae, se busca en
# la pagina otro que tenga A.2.5.
FILE_CON_A25 = "https://www.argentina.gob.ar/sites/default/files/deuda_publica_31-12-2019.xlsx"
TMP = "_tmp_deuda_trim.xlsx"
UA = {"User-Agent": "Mozilla/5.0"}


def find_file_con_a25() -> str:
    """Devuelve una URL de boletin trimestral que tenga la hoja A.2.5. Primero el
    archivo fijo conocido; si no responde, el mas nuevo de la pagina que la tenga."""
    try:
        if requests.head(FILE_CON_A25, timeout=30, headers=UA).status_code == 200:
            return FILE_CON_A25
    except requests.RequestException:
        pass
    r = requests.get(TRIM_PAGE, timeout=45, headers=UA)
    r.raise_for_status()
    files = set(re.findall(
        r'(https://www\.argentina\.gob\.ar/sites/default/files/deuda_publica_[0-9-]+[^"\'#]*\.xlsx)',
        r.text))
    def clave(u):
        m = re.search(r'(\d{2})-(\d{2})-(\d{4})', u)
        return (m.group(3), m.group(2), m.group(1)) if m else ("0", "0", "0")
    for url in sorted(files, key=clave, reverse=True):
        try:
            resp = requests.get(url, timeout=90, headers=UA)
            wb = openpyxl.load_workbook(io.BytesIO(resp.content), data_only=True, read_only=True)
            if any(s.replace(".", "").replace(" ", "") == "A25" for s in wb.sheetnames):
                return url
        except Exception:
            continue
    raise RuntimeError("Ningun boletin trimestral disponible tiene la hoja A.2.5.")


def parse_serie_anual(xlsx_path: str) -> list[dict]:
    """Lee la hoja A.2.5, fila 'I- TOTAL DEUDA PUBLICA BRUTA', alineada con la
    fila de fechas. Devuelve [{fecha: AAAA-12-31, valor: millones USD}]."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    hoja = next((s for s in wb.sheetnames if s.replace(".", "").replace(" ", "") == "A25"), None)
    if hoja is None:
        raise RuntimeError("El boletin no tiene la hoja A.2.5 (serie anual).")
    ws = wb[hoja]

    fila_fechas = max(ws.iter_rows(min_row=1, max_row=15),
                      key=lambda row: sum(1 for c in row if isinstance(c.value, dt.datetime)))
    anios = {c.column: c.value.year for c in fila_fechas if isinstance(c.value, dt.datetime)}

    fila_total = None
    for row in ws.iter_rows(min_row=1, max_row=40):
        for c in row:
            if isinstance(c.value, str) and c.value.strip().upper().startswith("I- TOTAL DEUDA"):
                fila_total = row
                break
        if fila_total:
            break
    if fila_total is None:
        raise RuntimeError("No encontre la fila 'I- TOTAL DEUDA PUBLICA BRUTA' en A.2.5.")

    puntos = []
    for c in fila_total:
        if c.column in anios and isinstance(c.value, (int, float)):
            puntos.append({"fecha": f"{anios[c.column]}-12-31", "valor": round(float(c.value), 1)})
    puntos.sort(key=lambda r: r["fecha"])
    return puntos


def calcular_consolidada_neta(ctx):
    """consolidada = bruta_USD + pasivos_bcra_ARS/TC_oficial ; neta = consolidada - reservas.
    Todo al cierre de cada anio (Dic)."""
    bruta = core.valor_de_diciembre(core.leer_serie(ctx.conn, "deuda_publica_bruta"))
    pasivos = core.valor_de_diciembre(core.leer_serie(ctx.conn, "pasivos_bcra"))   # millones ARS
    tc = core.valor_de_diciembre(core.leer_serie(ctx.conn, "dolar_oficial"))       # ARS/USD
    reservas = core.valor_de_diciembre(core.leer_serie(ctx.conn, "reservas_internacionales"))  # M USD

    nc = nn = 0
    for fecha, bruta_usd in sorted(bruta.items()):
        if fecha not in pasivos or fecha not in tc:
            continue
        consolidada = bruta_usd + pasivos[fecha] / tc[fecha]
        nc += core.insertar_observacion(ctx.conn, "deuda_consolidada", fecha, round(consolidada, 1))
        if fecha in reservas:
            neta = consolidada - reservas[fecha]
            nn += core.insertar_observacion(ctx.conn, "deuda_neta", fecha, round(neta, 1))
    ctx.nuevas += nc + nn
    print(f"   {'deuda_consolidada':<22}{nc:>5} nuevos o revisados (bruta + pasivos BCRA / TC)")
    print(f"   {'deuda_neta':<22}{nn:>5} nuevos o revisados (consolidada - reservas)")


def main() -> int:
    url = find_file_con_a25()
    r = requests.get(url, timeout=90, headers=UA)
    r.raise_for_status()
    with open(TMP, "wb") as f:
        f.write(r.content)

    try:
        serie = parse_serie_anual(TMP)
        with core.corrida(NOMBRE) as ctx:
            # backfill solo < 2019 (2019+ lo cubre el boletin mensual con mejor detalle)
            n = 0
            for p in serie:
                if p["fecha"] >= "2019-01-01":
                    continue
                n += core.insertar_observacion(ctx.conn, "deuda_publica_bruta", p["fecha"],
                                               p["valor"], fuente_url=url, es_provisorio=False)
            ctx.nuevas += n
            print(f"   {'deuda_publica_bruta':<22}{n:>5} nuevos o revisados (backfill A.2.5, <2019)")

            calcular_consolidada_neta(ctx)
            total = ctx.nuevas
    finally:
        if os.path.exists(TMP):
            os.remove(TMP)

    print(f"OK deuda historica: {total} observaciones nuevas o revisadas.")
    return total


if __name__ == "__main__":
    main()
