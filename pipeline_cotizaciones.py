"""
Pipeline de cotizaciones y pasivos del BCRA (series de apoyo).

Carga tres series que por si solas no tienen panel, pero que otros calculos
necesitan:

  * dolar_blue   -- para expresar el resultado fiscal en dolares (panel 07).
                    Fuente NO oficial (Bluelytics): el blue no lo publica el Estado.
  * dolar_oficial-- TC A3500 de cierre de mes, para valuar los pasivos del BCRA
                    en dolares al construir la deuda consolidada.
  * pasivos_bcra -- pasivos remunerados del BCRA (titulos + pases), el componente
                    que se suma a la deuda bruta para llegar a la consolidada.

Es un pipeline de API (datos.gob.ar + Bluelytics), confiable, corre en el cron.

Uso:
    python pipeline_cotizaciones.py
"""

import core

NOMBRE = "cotizaciones"

TC_OFICIAL = "168.1_T_CAMBI500_D_0_0_17"     # A3500 diario
BCRA_TITULOS = "300.1_AP_PAS_TITCRA_0_M_28"  # Leliq/Lebac/Nobac, MILES de $, mensual
BCRA_PASES = "331.1_PASES_REDESES__41"       # Pases, millones de $, signo de factor monetario


def _fin_de_mes(puntos: list[dict]) -> dict:
    """De una serie diaria [{fecha,valor}], deja el ultimo dato habil de cada
    mes: {AAAA-MM-ultimo: valor}."""
    ult = {}
    for p in sorted(puntos, key=lambda x: x["fecha"]):
        ult[p["fecha"][:7]] = p  # el ultimo de cada mes pisa a los anteriores
    salida = {}
    for mes, p in ult.items():
        anio, m = mes.split("-")
        import calendar
        dia = calendar.monthrange(int(anio), int(m))[1]
        salida[f"{mes}-{dia:02d}"] = p["valor"]
    return salida


def main() -> int:
    blue = core.fetch_dolar_blue_mensual()
    oficial = _fin_de_mes(core.fetch_serie_datos_gob(TC_OFICIAL, start_date="2002-01-01"))
    titulos = core.fetch_serie_datos_gob(BCRA_TITULOS, start_date="2002-01-01")
    pases = core.fetch_serie_datos_gob(BCRA_PASES, start_date="2002-01-01")

    # pasivos remunerados = titulos (miles->millones) + pases cuando son pasivo.
    # El pase entra como factor de la base monetaria: negativo = absorbio pesos
    # (pasivo remunerado). Solo contamos esos.
    pas_pases = {p["fecha"][:7]: max(0.0, -p["valor"]) for p in pases}
    pasivos = {}
    for t in titulos:
        mes = t["fecha"][:7]
        pasivos[mes] = t["valor"] / 1000.0 + pas_pases.get(mes, 0.0)
    for mes, v in pas_pases.items():          # meses con pases pero sin titulos
        pasivos.setdefault(mes, v)

    with core.corrida(NOMBRE) as ctx:
        n = 0
        for p in blue:
            n += core.insertar_observacion(ctx.conn, "dolar_blue", p["fecha"], p["valor"],
                                            fuente_url=core.BLUELYTICS_URL)
        ctx.nuevas += n
        print(f"   {'dolar_blue':<22}{len(blue):>5} meses, {n:>5} nuevos o revisados (Bluelytics)")

        n = 0
        for fecha, v in oficial.items():
            n += core.insertar_observacion(ctx.conn, "dolar_oficial", fecha, v,
                                            fuente_url=core.url_serie(TC_OFICIAL))
        ctx.nuevas += n
        print(f"   {'dolar_oficial':<22}{len(oficial):>5} meses, {n:>5} nuevos o revisados (A3500)")

        n = 0
        for mes, v in sorted(pasivos.items()):
            anio, m = mes.split("-")
            import calendar
            fecha = f"{mes}-{calendar.monthrange(int(anio), int(m))[1]:02d}"
            n += core.insertar_observacion(ctx.conn, "pasivos_bcra", fecha, round(v, 1),
                                            fuente_url=core.url_serie(BCRA_TITULOS))
        ctx.nuevas += n
        print(f"   {'pasivos_bcra':<22}{len(pasivos):>5} meses, {n:>5} nuevos o revisados (titulos+pases)")
        total = ctx.nuevas

    print(f"OK cotizaciones: {total} observaciones nuevas o revisadas.")
    return total


if __name__ == "__main__":
    main()
