---
slug: leer-carga-impositiva
titulo: Leer el gráfico: Carga impositiva
resumen: El primero de los cuatro. Recaudación nacional sobre PBI, año por año.
minutos: 7
panel: impositiva
---

Ya tenés todo lo necesario: sabés qué es la recaudación, qué es el PBI y por qué se dividen. Este gráfico es exactamente ese cociente, un punto por año desde 2004.

Cada punto responde a la pregunta: **de cada 100 pesos producidos ese año, ¿cuántos se llevó la Nación en impuestos?** La serie se mueve en torno al 20% del PBI.

### Un número propio, no oficial

Ningún organismo publica "la presión tributaria" como serie oficial. El observatorio la calcula dividiendo dos series que sí son oficiales. Otros la calculan distinto y les da distinto: **IARAF** estima 21,4% para 2025 y **Econviews** cerca de 25%, porque parten de una base de tributos más amplia. No es que uno esté mal: miden cosas levemente distintas.

> Antes de citar cualquier número de presión tributaria —el de acá o el de un diario— preguntá qué impuestos incluye y si suma a las provincias. Sin eso, el número no significa nada.

```tablero
titulo: Carga impositiva
panel: impositiva
unidad: % del PBI · anual · desde 2004

## suma
- IVA, Ganancias y demás impuestos internos (DGI)
- Derechos de exportación e importación (aduana, DGA)
- Aportes y contribuciones a la seguridad social
- Débitos y créditos, combustibles y tributos menores

## resta
- Nada se resta: es recaudación bruta, no neta de devoluciones ni de coparticipación a provincias

## incluye
- Todos los tributos que cobra el nivel nacional
- El PBI a precios corrientes del mismo año, como denominador

## excluye
- Ingresos Brutos y sellos: son provinciales
- Tasas municipales (ABL, seguridad e higiene)
- La economía informal, que no tributa pero sí está estimada en el PBI

## si_sube
El Estado nacional se lleva una porción mayor de lo que produce el país. Puede ser por más impuestos o mejor cobranza — pero también por una recesión, si el PBI cae más rápido que la recaudación.

## si_baja
El Estado nacional se lleva una porción menor. Puede ser una baja de impuestos, más evasión, o una economía que crece más rápido de lo que crece la recaudación.

## trampas
- No es "la presión tributaria total" del país: falta todo el nivel provincial y municipal. El número real que paga un contribuyente es bastante más alto.
- Es un cálculo propio del observatorio, no una cifra oficial. Distintas consultoras publican valores distintos y todos pueden ser correctos según qué incluyan.
- El PBI se revisa: un mismo año puede cambiar de valor años después.
```
