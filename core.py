"""
Nucleo de ingesta del observatorio: lo que comparten todos los pipelines.

Antes cada pipeline traia su propia copia de insertar_observacion(); ahora la
unica version vive aca. Dos piezas importan:

  * insertar_observacion() -- solo escribe si el dato CAMBIO respecto del valor
    vigente. Es lo que hace que la ingesta diaria sea idempotente (ver abajo).
  * fetch_serie_datos_gob() -- cliente de la API de series de datos.gob.ar, ya
    normalizado. Cualquier indicador que este en ese catalogo se ingiere en tres
    lineas, sin scraping ni parseo de Excel.

Uso tipico de un pipeline:

    import core
    puntos = core.fetch_serie_datos_gob("92.2_RESERVAS_IRES_0_0_32_40")
    with core.corrida("reservas") as ctx:
        conn = ctx.conn
        for p in puntos:
            ctx.nuevas += core.insertar_observacion(
                conn, "reservas_internacionales", p["fecha"], p["valor"],
                fuente_url=core.url_serie("92.2_RESERVAS_IRES_0_0_32_40"))
"""

import calendar
import math
import sqlite3
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("observatorio.db")
API_SERIES = "https://apis.datos.gob.ar/series/api/series/"


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise SystemExit(
            f"No encontre {DB_PATH}. Corre primero 'python init_db.py' para crear la base."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# --------------------------------------------------------------------------
# Escritura en la base
# --------------------------------------------------------------------------

def insertar_observacion(conn, serie_slug: str, fecha: str, valor: float,
                          fuente_url: str = None, es_provisorio: bool = False,
                          vintage: str = None) -> int:
    """Inserta una observacion SOLO si el dato es nuevo o cambio de valor.

    Devuelve 1 si escribio una fila, 0 si no habia nada que escribir.

    Esta guarda es lo que permite correr la ingesta todos los dias. Sin ella,
    como el UNIQUE de observaciones incluye el vintage y el vintage es la hora
    de la corrida, cada corrida diaria reinsertaria la serie entera: una serie
    de 80 puntos generaria ~29.000 filas por anio, todas con el mismo valor,
    haciendo pasar por "revision" algo que nunca cambio.

    Con la guarda, el vintage recupera su significado real: hay una fila nueva
    cuando, y solo cuando, la fuente efectivamente revisó el numero. El
    historial de revisiones queda limpio y auditable.
    """
    fila = conn.execute("SELECT id FROM series WHERE slug = ?", (serie_slug,)).fetchone()
    if fila is None:
        raise ValueError(
            f"Serie desconocida: '{serie_slug}'. Agregala en schema.sql antes de ingerirla."
        )
    serie_id = fila["id"]

    vigente = conn.execute(
        "SELECT valor FROM ultimo_vintage WHERE serie_id = ? AND fecha = ?",
        (serie_id, fecha),
    ).fetchone()

    if vigente is not None and math.isclose(vigente["valor"], valor, rel_tol=1e-9):
        return 0  # el dato no se movio: no hay revision que registrar

    # El OR IGNORE cubre el caso del vintage fijo (la semilla de init_db.py):
    # si esa misma fila ya existe, no la duplica.
    cur = conn.execute(
        """INSERT OR IGNORE INTO observaciones
           (serie_id, fecha, valor, vintage, es_provisorio, fuente_url)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (serie_id, fecha, valor, vintage or ahora(), int(es_provisorio), fuente_url),
    )
    return cur.rowcount


def fin_de_periodo(fecha_iso: str, frecuencia: str) -> str:
    """La API fecha cada punto al INICIO del periodo (un trimestre es 2024-01-01);
    la base usa el FIN (2024-03-31). Sin esta conversion, un mismo trimestre
    entraria dos veces: una por la API y otra por los puntos cargados a mano.
    """
    if frecuencia == "diaria":
        return fecha_iso
    anio, mes, _ = (int(x) for x in fecha_iso.split("-"))
    if frecuencia == "anual":
        return f"{anio}-12-31"
    if frecuencia == "trimestral":
        mes += 2                      # la API marca el mes de inicio: 1, 4, 7, 10
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    return f"{anio}-{mes:02d}-{ultimo_dia:02d}"


def ingerir_serie_api(ctx, serie_slug: str, serie_api: str, frecuencia: str,
                      factor: float = 1.0, start_date: str = "2000-01-01",
                      desde: str = None, saltear_ceros: bool = False) -> int:
    """Atajo para el caso comun: traer una serie de datos.gob.ar y volcarla a un
    slug de la base.

    frecuencia    -- 'diaria' | 'mensual' | 'trimestral' | 'anual'. Fecha cada
                     punto al cierre del periodo (ver fin_de_periodo).
    factor        -- conversion de unidad (la API suele dar millones de pesos y
                     varias de nuestras series estan en miles de millones).
    desde         -- ignora los puntos anteriores a esta fecha, para no pisar un
                     tramo que ya cubre otra serie de mejor granularidad.
    saltear_ceros -- descarta puntos con valor 0. Al agregar una serie trimestral
                     a anual, la API crea un bucket para el anio en curso aunque
                     todavia no tenga trimestres, y lo devuelve como 0. Un saldo
                     anual de exactamente 0 no existe en la practica, asi que para
                     esas series conviene saltearlos.
    """
    puntos = fetch_serie_datos_gob(serie_api, start_date=start_date)
    nuevas = 0
    for p in puntos:
        if saltear_ceros and p["valor"] == 0:
            continue
        fecha = fin_de_periodo(p["fecha"], frecuencia)
        if desde and fecha < desde:
            continue
        nuevas += insertar_observacion(
            ctx.conn, serie_slug, fecha, p["valor"] * factor,
            fuente_url=url_serie(serie_api), es_provisorio=False,
        )
    ctx.nuevas += nuevas
    print(f"   {serie_slug:<30} {len(puntos):>5} en la fuente, {nuevas:>5} nuevos o revisados")
    return nuevas


def leer_serie(conn, serie_slug: str) -> dict:
    """Devuelve {fecha: valor} con los valores vigentes de una serie. Lo usan
    las series calculadas (las que salen de combinar otras, como cualquier
    ratio sobre el PBI).
    """
    return {
        r["fecha"]: r["valor"]
        for r in conn.execute(
            """SELECT uv.fecha, uv.valor FROM ultimo_vintage uv
               JOIN series s ON s.id = uv.serie_id
               WHERE s.slug = ? ORDER BY uv.fecha""",
            (serie_slug,),
        )
    }


def valor_de_diciembre(serie_mensual_o_diaria: dict) -> dict:
    """De un {fecha: valor} con datos mensuales/diarios, devuelve {anio-12-31:
    valor de diciembre}. Sirve para llevar series de mayor frecuencia a un corte
    anual de cierre (lo que usan los calculos de deuda consolidada/neta).
    """
    por_anio = {}
    for fecha, valor in sorted(serie_mensual_o_diaria.items()):
        if fecha[5:7] == "12":
            por_anio[f"{fecha[:4]}-12-31"] = valor
    return por_anio


BLUELYTICS_URL = "https://api.bluelytics.com.ar/v2/evolution.json"


def fetch_dolar_blue_mensual() -> list[dict]:
    """Promedio mensual del dolar blue (venta) desde Bluelytics, una API PUBLICA
    pero NO oficial. El blue no lo publica ningun organismo del Estado, asi que no
    esta en datos.gob.ar; Bluelytics es la fuente de facto, diaria desde 2011.

    Devuelve [{fecha: AAAA-MM-ultimo_dia, valor: promedio del mes}].
    """
    import requests

    resp = requests.get(BLUELYTICS_URL, timeout=30, headers={"User-Agent": "observatorio"})
    resp.raise_for_status()

    suma, cuenta = {}, {}
    for d in resp.json():
        if d.get("source") != "Blue" or d.get("value_sell") is None:
            continue
        mes = d["date"][:7]              # AAAA-MM
        suma[mes] = suma.get(mes, 0) + d["value_sell"]
        cuenta[mes] = cuenta.get(mes, 0) + 1

    puntos = []
    for mes in sorted(suma):
        anio, m = mes.split("-")
        ultimo = calendar.monthrange(int(anio), int(m))[1]
        puntos.append({"fecha": f"{mes}-{ultimo:02d}", "valor": round(suma[mes] / cuenta[mes], 2)})
    return puntos


# --------------------------------------------------------------------------
# Lectura de fuentes
# --------------------------------------------------------------------------

LIMIT_API = 5000  # tope duro por request que impone datos.gob.ar


def url_serie(serie_id: str, start_date: str = "1990-01-01") -> str:
    """URL legible de la serie, para guardar como fuente_url de cada dato."""
    return (f"{API_SERIES}?ids={serie_id}&format=json&limit={LIMIT_API}"
            f"&start_date={start_date}")


def fetch_serie_datos_gob(serie_id: str, start_date: str = "1990-01-01") -> list[dict]:
    """Trae una serie de la API de series de tiempo de datos.gob.ar y la
    normaliza a [{fecha, valor}, ...], ordenada y sin nulos.

    Es HTTP y JSON: no hay robots.txt de por medio ni archivos que parsear. Si
    el indicador que queres esta en ese catalogo, este es el camino.

    Para encontrar el id de una serie:
        https://apis.datos.gob.ar/series/api/search/?q=<lo que busques>

    PAGINA los resultados, y no es opcional: la API corta en 5000 registros por
    request y NO avisa que trunco. Reservas es una serie diaria desde 2003, o
    sea >8000 puntos: pidiendola de una sola vez se obtienen los primeros 5000 y
    la serie "termina" en 2016. Ese bug estuvo vivo en el front del sitio, que
    mostraba un valor de 2016 como si fuera el ultimo dato.

    CUIDADO tambien con lo que devuelve el buscador del catalogo: para "resultado
    primario" trae series REM, que son la *encuesta de expectativas de mercado*
    del BCRA, no el dato fiscal publicado. Confirma que la serie sea el dato real
    y no un pronostico antes de ingerirla.
    """
    import requests  # solo los pipelines necesitan requests; init/export no

    puntos = []
    offset = 0
    while True:
        resp = requests.get(
            API_SERIES,
            params={"ids": serie_id, "format": "json", "limit": LIMIT_API,
                    "start": offset, "start_date": start_date},
            timeout=30,
        )
        resp.raise_for_status()
        pagina = resp.json().get("data", [])

        puntos += [
            {"fecha": fila[0], "valor": float(fila[1])}
            for fila in pagina
            if fila[1] is not None
        ]
        if len(pagina) < LIMIT_API:
            break
        offset += LIMIT_API

    if not puntos:
        raise RuntimeError(f"La serie '{serie_id}' vino vacia desde datos.gob.ar.")

    puntos.sort(key=lambda p: p["fecha"])
    return puntos


# --------------------------------------------------------------------------
# Registro de corridas
# --------------------------------------------------------------------------

@contextmanager
def corrida(pipeline: str):
    """Envuelve la corrida de un pipeline y la deja registrada en la tabla
    'ingestas', pase lo que pase.

    Sin esto, un job diario desatendido que empieza a fallar no avisa nada: la
    pagina simplemente se congela en el ultimo dato bueno y nadie se entera.
    """
    conn = get_conn()
    ctx = _Corrida(conn)
    inicio = ahora()
    try:
        yield ctx
    except Exception:
        conn.rollback()
        _registrar(conn, pipeline, inicio, "error", 0, traceback.format_exc(limit=3))
        conn.commit()
        conn.close()
        raise
    else:
        _registrar(conn, pipeline, inicio, "ok", ctx.nuevas, None)
        conn.commit()
        conn.close()


class _Corrida:
    def __init__(self, conn):
        self.conn = conn
        self.nuevas = 0


def _registrar(conn, pipeline, inicio, estado, filas_nuevas, mensaje):
    conn.execute(
        """INSERT INTO ingestas (pipeline, inicio, fin, estado, filas_nuevas, mensaje)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (pipeline, inicio, ahora(), estado, filas_nuevas, mensaje),
    )
