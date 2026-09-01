"""
Pipeline fiscal (Secretaria de Hacienda + INDEC, via API de series).

Trae el resultado primario y financiero mensuales del Sector Publico Nacional,
que hasta ahora eran 6 puntos cargados a mano y pasan a ser la serie mensual
completa (~113 meses).

La fuente es el IMIG (Informe Mensual de Ingresos y Gastos) de Hacienda. OJO con
esto: si buscas "resultado primario" en el catalogo de datos.gob.ar, lo primero
que aparece son series REM, que son la ENCUESTA DE EXPECTATIVAS DE MERCADO del
BCRA -- pronosticos de consultoras, no el dato publicado. Las series 452.* del
IMIG son el dato real. Confundirlas seria publicar predicciones como si fueran
hechos.

Empieza en 2016 porque esa es la serie que publica Hacienda en el catalogo; los
anios anteriores existen en los boletines viejos, no en la API.

Tambien carga el PBI corriente (serie de apoyo, sin panel propio) y con el
calcula el resultado primario anual como % del PBI, que es lo que consume el
panel de deficits gemelos.

Uso:
    python pipeline_fiscal.py
"""

import core

NOMBRE = "fiscal"

RESULTADO_PRIMARIO_M   = "452.3_RESULTADO_RIO_0_M_18_54"  # mensual, millones de ARS
RESULTADO_FINANCIERO_M = "452.3_RESULTADO_ERO_0_M_20_25"  # mensual, millones de ARS
RESULTADO_PRIMARIO_A   = "452.2_RESULTADO_RIO_0_T_18_1"   # anual,   millones de ARS
PBI_ANUAL              = "9.1_PPC_2004_A_22"              # anual,   millones de ARS corrientes
PBI_USD_ANUAL          = "9.1_PDPC_2004_A_30"             # anual,   millones de USD corrientes

# La base expresa el resultado fiscal en miles de millones; la API, en millones.
A_MILES_DE_MILLONES = 1 / 1000


def _calcular_ratio(ctx, slug_destino, numerador_por_fecha, denom_por_fecha, factor=100, etiqueta=""):
    """Escribe una serie calculada = numerador/denominador*factor, solo donde
    existen las dos. Devuelve cuantas filas nuevas escribio."""
    n = 0
    for fecha, num in numerador_por_fecha.items():
        den = denom_por_fecha.get(fecha)
        if not den:
            continue
        n += core.insertar_observacion(ctx.conn, slug_destino, fecha, round(num / den * factor, 2))
    ctx.nuevas += n
    print(f"   {slug_destino:<30} {n:>5} nuevos o revisados {etiqueta}")
    return n


def main() -> int:
    with core.corrida(NOMBRE) as ctx:
        core.ingerir_serie_api(ctx, "resultado_primario", RESULTADO_PRIMARIO_M,
                               "mensual", factor=A_MILES_DE_MILLONES)
        core.ingerir_serie_api(ctx, "resultado_financiero", RESULTADO_FINANCIERO_M,
                               "mensual", factor=A_MILES_DE_MILLONES)
        core.ingerir_serie_api(ctx, "pbi_anual", PBI_ANUAL, "anual")
        core.ingerir_serie_api(ctx, "pbi_usd_anual", PBI_USD_ANUAL, "anual")

        # (e) Resultado fiscal en dolares blue: ARS del mes / blue promedio del mes.
        # Las series ARS estan en miles de millones; el blue en ARS/USD; el
        # resultado en millones de USD = (mM ARS * 1000) / blue.
        blue = core.leer_serie(ctx.conn, "dolar_blue")
        for slug_ars, slug_usd in [("resultado_primario", "resultado_primario_usd"),
                                    ("resultado_financiero", "resultado_financiero_usd")]:
            serie_ars = core.leer_serie(ctx.conn, slug_ars)
            en_usd = {f: v * 1000 / blue[f] for f, v in serie_ars.items() if f in blue}
            _calcular_ratio(ctx, slug_usd, en_usd, {f: 1 for f in en_usd}, factor=1,
                            etiqueta="(ARS/blue del mes)")

        # (g) Ratios anuales sobre PBI para los deficits gemelos.
        pbi = core.leer_serie(ctx.conn, "pbi_anual")
        pbi_usd = core.leer_serie(ctx.conn, "pbi_usd_anual")

        primario_anual = core.fetch_serie_datos_gob(RESULTADO_PRIMARIO_A, start_date="2000-01-01")
        prim_por_fecha = {core.fin_de_periodo(p["fecha"], "anual"): p["valor"] for p in primario_anual}
        _calcular_ratio(ctx, "resultado_primario_anual_pbi", prim_por_fecha, pbi,
                        etiqueta="(resultado primario / pbi_anual)")

        cc_anual = core.leer_serie(ctx.conn, "cuenta_corriente_anual")  # USD
        _calcular_ratio(ctx, "cuenta_corriente_pbi", cc_anual, pbi_usd,
                        etiqueta="(cuenta corriente / pbi_usd)")
        total = ctx.nuevas

    print(f"OK fiscal: {total} observaciones nuevas o revisadas.")
    return total


if __name__ == "__main__":
    main()
