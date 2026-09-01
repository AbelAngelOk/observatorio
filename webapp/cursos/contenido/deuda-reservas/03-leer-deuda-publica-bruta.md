---
slug: leer-deuda-publica-bruta
titulo: Leer el gráfico: Deuda pública bruta
resumen: El primero de los seis. Un stock en dólares, al tipo de cambio oficial.
minutos: 8
panel: deuda
---

Con las dos piezas anteriores —qué es un stock, y por quién se mide— ya podés leer este gráfico.

### Cómo leerlo, en orden

- **La serie tiene dos tramos.** Anual de 1993 a 2018 (un punto por año, a fin de año) y mensual desde 2019. No lo leas como si fuera todo mensual: antes de 2019 solo hay una foto por año.
- **Está en dólares al tipo de cambio oficial**, no al blue. Esto importa porque una devaluación grande cambia el valor en dólares de la porción de deuda emitida en pesos, sin que se haya emitido ni pagado un peso de deuda nueva.
- **"Bruta" es literal**: no se le resta ningún activo del Estado. Eso es lo que la distingue de la deuda neta, más adelante en este curso.

### La caída de diciembre de 2023

Es el ejemplo más claro de por qué importa el tipo de cambio: entre noviembre y diciembre de 2023 la línea cae fuerte. No fue un pago ni una quita — fue la devaluación de diciembre de 2023, que licuó, medido en dólares, el valor de la porción de la deuda que estaba emitida en pesos. La deuda en pesos, en pesos, no cambió; en dólares, sí.

```tablero
titulo: Deuda pública bruta
panel: deuda
unidad: Millones de USD, al dólar oficial · anual (1993-2018) y mensual (2019 →)

## suma
- Bonos y letras emitidos por el Tesoro
- Préstamos de organismos internacionales (FMI y otros)
- Deuda con otros organismos del propio Estado

## resta
Nada. "Bruta" significa exactamente eso: no se descuenta ningún activo del Estado. La que sí resta algo es la deuda neta, más adelante en este curso.

## incluye
- Solo la Administración Central de la Nación
- Todos los instrumentos: bonos, letras, préstamos, deuda con organismos públicos

## excluye
- Provincias y municipios
- Los pasivos del Banco Central — eso es la deuda consolidada, el próximo gráfico
- Los activos del Estado — por eso es "bruta" y no "neta"

## si_sube
El Tesoro tomó más deuda nueva de la que canceló, o el tipo de cambio oficial subió, inflando en dólares el valor de la porción de deuda emitida en pesos.

## si_baja
Se pagó más deuda de la que se emitió — o, el caso más frecuente en la serie, una devaluación licuó en dólares el valor de la deuda en pesos, como en diciembre de 2023. Eso no significa que se haya cancelado deuda.

## trampas
- La caída de dic-2023 (y la de 2002) no es desendeudamiento: es la devaluación licuando en dólares la parte en pesos.
- Está al dólar oficial, no al blue — no es comparable directo con el panel de Resultado fiscal, que sí usa blue.
- "Anual" es un stock a fin de año, no una variación interanual — esa es el recuadro aparte, "Variación último año".
```
