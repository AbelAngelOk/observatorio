---
slug: leer-deuda-neta
titulo: Leer el gráfico: Deuda neta
resumen: El cuarto de los seis. Consolidada menos reservas.
minutos: 7
panel: neta
---

Con la cuenta del capítulo anterior, ya podés leer este gráfico.

### Cómo leerlo

- **Compará su forma con la de la consolidada**, capítulo 5. Si las dos líneas se mueven parecido, las reservas no estuvieron determinando la diferencia ese período. Si se separan, mirá el gráfico de reservas para entender por qué.
- **Una caída acá no siempre es buena noticia.** Puede bajar porque la deuda consolidada cayó (bueno) o porque las reservas subieron (también bueno) — pero conviene mirar los dos componentes por separado antes de sacar una conclusión de un solo número.

```tablero
titulo: Deuda neta
panel: neta
unidad: Millones de USD · anual · desde 2003

## suma
- Deuda consolidada del año (Tesoro + Banco Central)

## resta
- Reservas internacionales del BCRA, a fin de ese mismo año

## incluye
- Todo lo que incluye la deuda consolidada, con las reservas restadas

## excluye
- Los mismos límites que la consolidada: no resta tenencias intra-sector público
- Cualquier activo del Estado que no sean las reservas del BCRA (no entran, por ejemplo, empresas públicas o inmuebles)

## si_sube
La deuda consolidada creció más rápido que las reservas, o las reservas cayeron mientras la deuda consolidada se mantuvo.

## si_baja
Las reservas crecieron más rápido que la deuda, o la deuda consolidada cayó (por pago o por licuación cambiaria) mientras las reservas se sostuvieron.

## trampas
- Hereda el límite de la consolidada: no es la cifra "neta" exacta de otras consultoras, que pueden restar otras cosas.
- Que la deuda neta baje no siempre es una buena noticia si el motivo fue una caída de las reservas, no de la deuda.
- Es un dato de fin de año, no un promedio ni algo en tiempo real.
```
