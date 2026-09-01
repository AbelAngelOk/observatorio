"""
Pipeline de recaudacion y presion tributaria (Hacienda + INDEC, via API de series).

Trae la recaudacion tributaria nacional mensual, que es la serie mas larga que
conseguimos de todo el proyecto: arranca en 1997.

Con ella calcula la presion tributaria como recaudacion acumulada del anio sobre
PBI corriente del anio. Eso reemplaza los 2 puntos sueltos que teniamos por una
serie de dos decadas.

ADVERTENCIA sobre el numero calculado: NO es una serie oficial y NO va a coincidir
exactamente con la estimacion de IARAF que muestra el panel hoy (21,4% para 2025),
porque IARAF usa otra base de tributos. Por eso vive en su propio slug
(presion_tributaria_nacional) y no pisa la serie de IARAF: son dos mediciones
distintas de la misma idea, y el sitio muestra las dos.

El PBI arranca en 2004 (base 2004 del INDEC), asi que aunque la recaudacion llegue
hasta 1997, el ratio solo se puede calcular desde 2004.

Uso:
    python pipeline_recaudacion.py
"""

import core

NOMBRE = "recaudacion"

RECAUDACION_M = "172.3_TL_RECAION_M_0_0_17"  # mensual, millones de ARS, desde 1997


def main() -> int:
    with core.corrida(NOMBRE) as ctx:
        core.ingerir_serie_api(ctx, "recaudacion_nacional", RECAUDACION_M, "mensual")

        # Presion tributaria = recaudacion acumulada del anio / PBI del anio.
        # Solo se calcula para los anios COMPLETOS: con 7 meses de recaudacion y
        # el PBI de todo el anio saldria un numero absurdamente bajo.
        recaudacion = core.leer_serie(ctx.conn, "recaudacion_nacional")
        pbi = core.leer_serie(ctx.conn, "pbi_anual")

        acumulado, meses = {}, {}
        for fecha, valor in recaudacion.items():
            anio = fecha[:4]
            acumulado[anio] = acumulado.get(anio, 0) + valor
            meses[anio] = meses.get(anio, 0) + 1

        nuevas = 0
        for anio, total in sorted(acumulado.items()):
            fecha = f"{anio}-12-31"
            if meses[anio] < 12 or fecha not in pbi:
                continue
            pct = total / pbi[fecha] * 100
            nuevas += core.insertar_observacion(
                ctx.conn, "presion_tributaria_nacional", fecha, round(pct, 2),
                fuente_url=core.url_serie(RECAUDACION_M), es_provisorio=False,
            )
        ctx.nuevas += nuevas
        print(f"   {'presion_tributaria_nacional':<30} {len(acumulado):>5} anios, "
              f"{nuevas:>5} nuevos o revisados (recaudacion / pbi_anual)")
        total = ctx.nuevas

    print(f"OK recaudacion: {total} observaciones nuevas o revisadas.")
    return total


if __name__ == "__main__":
    main()
