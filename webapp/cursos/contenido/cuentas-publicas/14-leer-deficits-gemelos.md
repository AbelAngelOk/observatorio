---
slug: leer-deficits-gemelos
titulo: Leer el gráfico: Déficits gemelos
resumen: El cuarto y último. Las dos cuentas del país en un solo eje.
minutos: 8
panel: gemelos
---

Este gráfico junta lo que venimos viendo: el **resultado fiscal primario** y el **saldo de cuenta corriente**, los dos como % del PBI y en el mismo eje, con la línea de cero.

### Qué es la hipótesis de los déficits gemelos

La idea, que viene de la macroeconomía clásica, es que ambos déficits tienden a moverse juntos: un Estado que gasta de más empuja la demanda, se importa más, y la cuenta corriente se deteriora. De ahí lo de "gemelos".

**Pero no es una ley.** En la serie argentina las dos líneas coinciden en signo en algunos años y se separan en otros. Cuando se separan, la hipótesis simplemente no se cumple ese año — puede haber superávit fiscal con déficit externo, por ejemplo si el país crece y las importaciones crecen más rápido que las exportaciones.

### Qué se puede concluir y qué no

- **Sí**: ver si las dos cuentas del país están o no bajo cero al mismo tiempo, que es una señal de fragilidad.
- **Sí**: identificar los años en que se desacoplan, que suelen ser los interesantes.
- **No**: deducir que una causa la otra. Que se muevan juntas es correlación, no causalidad.
- **No**: comparar la magnitud de las dos líneas como si fueran lo mismo. Son % del PBI, pero de cuentas distintas.

Con este gráfico cerrás el curso. Si podés mirar los cuatro y decir de dónde sale cada número, qué incluye y qué deja afuera, ya leés las cuentas públicas mejor que la mayoría de los titulares que las comentan.

```tablero
titulo: Déficits gemelos
panel: gemelos
unidad: % del PBI · anual · las dos series en el mismo eje

## suma
- Línea fiscal: ingresos totales del SPN
- Línea externa: exportaciones, servicios cobrados, rentas y transferencias recibidas

## resta
- Línea fiscal: gasto primario (sin intereses)
- Línea externa: importaciones, servicios pagados, rentas giradas al exterior

## incluye
- Fiscal: solo el Sector Público Nacional
- Externa: el país entero — Estado, empresas y familias
- Ambas divididas por el PBI del mismo año

## excluye
- Fiscal: provincias, municipios, intereses de la deuda y el Banco Central
- Externa: los movimientos de capital (eso es la cuenta financiera, otra cosa)
- Cualquier relación de causa y efecto entre las dos líneas: el gráfico no la demuestra

## si_sube
La cuenta correspondiente mejora. Si suben las dos y cruzan el cero hacia arriba, el país tiene superávit gemelo: le sobra en sus cuentas internas y externas a la vez.

## si_baja
La cuenta empeora. Si caen las dos bajo cero, hay déficits gemelos: el Estado necesita financiamiento y el país necesita divisas al mismo tiempo. Es la combinación frágil.

## trampas
- Que se muevan juntas no prueba que una cause la otra.
- La línea fiscal es solo la Nación; la externa es todo el país. No cubren el mismo universo.
- La fiscal usa el resultado primario: no incluye intereses. Con ellos, el rojo fiscal es mayor.
- La cuenta corriente original es trimestral y acá está anualizada para poder compararla.
```
