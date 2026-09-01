---
slug: leer-cartera
titulo: Leer el gráfico: Cartera de deuda en pesos
resumen: El sexto y último. Cómo se reparte la deuda en pesos, año a año.
minutos: 8
panel: cartera
---

Con la distinción del capítulo anterior, ya podés leer este último gráfico del curso.

### Cómo leerlo

- **Es un reparto, no un monto.** Cada barra suma 100% entre las categorías — no dice si la deuda en pesos, en total, creció o cayó ese año, solo cómo se compuso.
- **Es solo la deuda en pesos.** No mezcles esta cifra con el total de deuda bruta en dólares del capítulo 3 — son dos preguntas distintas sobre dos porciones distintas de la deuda.
- **Sale de un boletín trimestral en Excel**, no de una API — es de las fuentes menos automatizadas del sitio, y el pipeline que la trae está marcado como experimental.

Con este gráfico cerrás el curso. Si podés mirar los seis y decir de dónde sale cada número, quién lo mide y qué incluye y qué deja afuera, ya leés la deuda y las reservas del país mejor que la mayoría de los titulares que las comentan.

```tablero
titulo: Cartera de deuda en pesos, por tipo de activo
panel: cartera
unidad: % de la deuda en pesos · corte trimestral, serie anual · desde 2014

## suma
- Deuda ajustable por CER (indexada a la inflación)
- Deuda a tasa fija, variable o cero (no ajustable por CER)

## resta
Nada — es una composición que suma 100%, no una resta.

## incluye
- Solo la deuda del Tesoro emitida en pesos
- El desglose CER vs. no-CER tal como lo publica el boletín trimestral de Finanzas (hoja A.1.4)

## excluye
- La deuda en moneda extranjera (no tiene "ajuste CER"; está en la deuda bruta total, pero no en este desglose)
- Los dólar-linked, tan chicos que el sitio los muestra como una nota al pie, no como serie completa

## si_sube
La porción CER de la deuda en pesos creció: el Estado se protegió de licuar la deuda con inflación, pero se comprometió a pagar más si los precios suben mucho.

## si_baja
Más de la deuda en pesos quedó a tasa fija o variable: el Estado, o el mercado, prefirió no atarse a la inflación futura.

## trampas
- Es un reparto porcentual, no un monto: no dice si la deuda total en pesos subió o bajó.
- El dato "dólar linked" es un punto suelto (jun-25), no una serie — no se puede comparar con otros años.
- Sale de un Excel trimestral, no de una API: el pipeline que la trae es experimental, no corre en la ingesta diaria automática.
```
