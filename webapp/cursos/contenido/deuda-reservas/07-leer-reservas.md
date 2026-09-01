---
slug: leer-reservas
titulo: Leer el gráfico: Reservas internacionales
resumen: El más denso de los seis, y el único con serie diaria completa.
minutos: 8
panel: reservas
---

Este es el único gráfico del observatorio con una serie diaria completa y un pipeline propio que la actualiza sola, todos los días, desde 2003.

### Cómo leerlo

- **Elegí la ventana de tiempo primero.** El gráfico tiene tres rangos: 2 años, 5 años y la serie completa. Para ver una tendencia reciente, el rango corto sirve mejor que la serie entera, que aplasta las variaciones de los últimos meses.
- **Mirá la variación de 12 meses**, no el dato de un solo día: las reservas se mueven todos los días hábiles por operaciones normales del mercado, y un salto de un día puede ser ruido.
- **El máximo y el mínimo históricos** ya están calculados sobre la serie completa y verificada — no hace falta desplazarse por 20 años de gráfico para encontrarlos.

### Una advertencia que vale la pena conocer

Este panel tuvo, en el pasado, un error real que ilustra un riesgo general de trabajar con datos: antes consultaba la API del gobierno **en vivo, desde el navegador de cada visitante**. Esa API corta las respuestas en 5.000 registros y no avisa que las cortó. Como la serie de reservas es diaria (miles de puntos), el gráfico terminaba mostrando datos solo hasta 2016, y el recuadro de "último dato" mostraba, en la práctica, un valor de hace diez años — con un "máximo histórico" también trunco (unos US$ 52.700 millones, cuando el máximo real llegó a unos US$ 77.500 millones). Nadie lo notó durante meses, porque el gráfico no daba ningún error: simplemente mostraba números viejos con total normalidad.

Hoy el pipeline que trae los datos pagina correctamente y la base guarda la serie entera, así que el problema está corregido. Queda como ejemplo de que un gráfico puede estar mal sin ningún síntoma visible, si la fuente que lo alimenta corta silenciosamente.

```tablero
titulo: Reservas internacionales del BCRA
panel: reservas
unidad: Millones de USD · diaria (días hábiles) · desde 2003

## suma
- Oro y divisas en poder del Banco Central
- Depósitos en el exterior y otros activos externos líquidos del BCRA

## resta
Nada — es un stock de activos, no un neteo. Las "reservas netas" son un cálculo distinto (restan pasivos en dólares del BCRA) que este panel no muestra.

## incluye
- Todo lo que el BCRA reporta como reservas internacionales brutas en su balance diario

## excluye
- Los pasivos en moneda extranjera del Banco Central (swaps, encajes en dólares de los bancos)
- Las reservas de otros países o de bancos privados

## si_sube
El Banco Central compró más divisas de las que vendió — por ejemplo, por un superávit comercial liquidado en el mercado oficial, un préstamo de un organismo, o un swap.

## si_baja
El Banco Central vendió divisas — para contener el tipo de cambio, para pagar deuda, o por pagos a organismos internacionales.

## trampas
- Es la única serie del sitio con historia diaria completa y automatizada; los demás paneles son más livianos en densidad de datos.
- "Brutas" no es lo mismo que "netas" — este panel muestra brutas, sin restar los pasivos en dólares del BCRA.
- Este panel tuvo un error histórico real por truncamiento silencioso de una API externa (ver el capítulo). Ya está corregido, pero es un buen recordatorio de revisar siempre de dónde sale un dato.
```
