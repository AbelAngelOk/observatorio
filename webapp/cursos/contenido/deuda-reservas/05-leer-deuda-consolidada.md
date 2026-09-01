---
slug: leer-deuda-consolidada
titulo: Leer el gráfico: Deuda consolidada
resumen: El segundo. La deuda del Tesoro más la del Banco Central, en una sola línea.
minutos: 8
panel: consolidada
---

Este gráfico no sale de una fuente única: se construye acá, sumando dos series, año a año.

### Cómo se arma

- **Deuda bruta del Tesoro** (capítulo anterior), ya en dólares.
- **Pasivos remunerados del Banco Central**: Leliq, Lebac, títulos y pases pasivos, tomados a fin de diciembre de cada año y convertidos a dólares al tipo de cambio oficial de ese cierre.

Las dos se suman. El resultado es cuánto debe, en conjunto, el Estado consolidado — Tesoro más Banco Central.

### El límite que hay que conocer

Este cálculo **no resta las tenencias cruzadas dentro del propio sector público** —por ejemplo, Letras Intransferibles que el Tesoro le debe al Banco Central—, porque esa información no se publica como una serie que se pueda tomar directo. Es una aproximación razonable, no una cifra oficial ni definitiva: puede diferir un poco de la que citan consultoras como EcoGo o medios como Chequeado, que usan otros criterios de qué restar.

### Por qué en 2025 se parece tanto a la deuda bruta

Si comparás este gráfico con el anterior, vas a ver que en los años más recientes las dos líneas casi se tocan. No es un error: los pasivos remunerados del Banco Central cayeron a casi cero (se eliminaron las Leliq, y los pases pasivos migraron a un instrumento del Tesoro, que ya cuenta dentro de la deuda bruta). Cuando el BCRA casi no tiene deuda propia, consolidada y bruta convergen.

```tablero
titulo: Deuda consolidada
panel: consolidada
unidad: Millones de USD, al TC oficial de fin de año · anual · desde 2002

## suma
- Deuda bruta del Tesoro (el gráfico anterior)
- Pasivos remunerados del Banco Central (Leliq/Lebac/títulos + pases pasivos), a dólar oficial de fin de diciembre

## resta
Nada — es una suma de dos deudas, no una resta. La que sí resta es la deuda neta, más adelante.

## incluye
- La Administración Central, vía la deuda bruta
- El Banco Central, específicamente sus pasivos remunerados de fin de año

## excluye
- Provincias y municipios
- Las tenencias cruzadas dentro del sector público (no se restan: no hay una serie limpia para hacerlo)

## si_sube
El Tesoro, el Banco Central, o los dos, aumentaron su deuda con costo financiero durante el año.

## si_baja
Se redujo la deuda de alguno de los dos — o, como pasó en 2025, los pasivos remunerados del BCRA casi desaparecieron.

## trampas
- Es una aproximación, no la cifra exacta de Chequeado o EcoGo: no resta tenencias intra-sector público.
- Que consolidada y bruta converjan no significa que "se escondió" deuda del BCRA — significa que el BCRA casi no tiene pasivos remunerados hoy.
- Se mide a cierre de diciembre, no es un promedio del año.
```
