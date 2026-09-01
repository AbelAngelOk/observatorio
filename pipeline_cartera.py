"""
Pipeline experimental: historia de la cartera de deuda en pesos por tipo de tasa.

Lee la hoja A.1.4 ("Por moneda y tasa") del boletin trimestral de cada anio y
saca la composicion de la deuda en MONEDA LOCAL en dos categorias que la fuente
publica de forma consistente:

    cartera_cer       = deuda ajustable por CER     / total moneda local
    cartera_tasa_fija = deuda NO ajustable por CER  / total moneda local

Las dos suman 100% de la deuda en pesos. El "dolar linked" NO se puede separar
de esta hoja (no es una fila propia), asi que esa serie no se backfillea.

Toma un corte anual (31/12) por cada archivo deuda_publica_31-12-AAAA.xlsx, desde
2014 (lo mas atras que publica Finanzas). Antes de esa fecha la deuda en pesos
era marginal y el desglose no es comparable.

EXPERIMENTAL: depende del layout del Excel y descarga un archivo por anio. No
corre en el cron.

Uso:
    python pipeline_cartera.py
"""

import datetime as dt
import os

import requests
import openpyxl

import core

NOMBRE = "cartera"
BASE = "https://www.argentina.gob.ar/sites/default/files/deuda_publica_31-12-{anio}.xlsx"
UA = {"User-Agent": "Mozilla/5.0"}
DESDE = 2014


def _fila_valor(ws, prefijo):
    """Primer numero de la primera fila cuyo texto empieza con `prefijo`."""
    pref = prefijo.upper()
    for row in ws.iter_rows(min_row=10, max_row=40):
        for c in row:
            if isinstance(c.value, str) and c.value.strip().upper().startswith(pref):
                nums = [x.value for x in row if isinstance(x.value, (int, float))]
                return nums[0] if nums else None
    return None


def parse_cartera(xlsx_path: str):
    """Devuelve (pct_cer, pct_no_cer) de la deuda en pesos, o None si no cuadra."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    hoja = next((s for s in wb.sheetnames if s.replace(".", "").upper() == "A14"), None)
    if hoja is None:
        return None
    ws = wb[hoja]
    local = _fila_valor(ws, "Moneda local")
    cer = _fila_valor(ws, "Deuda ajustable por CER")
    no_cer = _fila_valor(ws, "Deuda no ajustable por CER")
    if not local or cer is None or no_cer is None:
        return None
    return round(cer / local * 100, 1), round(no_cer / local * 100, 1)


def main() -> int:
    anio_actual = dt.date.today().year
    with core.corrida(NOMBRE) as ctx:
        n = 0
        cargados = []
        for anio in range(DESDE, anio_actual + 1):
            url = BASE.format(anio=anio)
            try:
                r = requests.get(url, timeout=90, headers=UA)
                if r.status_code != 200:
                    continue
                tmp = f"_tmp_cartera_{anio}.xlsx"
                with open(tmp, "wb") as f:
                    f.write(r.content)
                try:
                    res = parse_cartera(tmp)
                finally:
                    os.remove(tmp)
                if not res:
                    continue
                pct_cer, pct_no_cer = res
                fecha = f"{anio}-12-31"
                n += core.insertar_observacion(ctx.conn, "cartera_cer", fecha, pct_cer, fuente_url=url)
                n += core.insertar_observacion(ctx.conn, "cartera_tasa_fija", fecha, pct_no_cer, fuente_url=url)
                cargados.append(str(anio))
            except requests.RequestException:
                continue
        ctx.nuevas += n
        print(f"   cartera {len(cargados)} anios leidos ({', '.join(cargados)}), {n} nuevos o revisados")
        total = ctx.nuevas

    print(f"OK cartera: {total} observaciones nuevas o revisadas.")
    return total


if __name__ == "__main__":
    main()
