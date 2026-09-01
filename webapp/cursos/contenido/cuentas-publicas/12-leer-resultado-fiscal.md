---
slug: leer-resultado-fiscal
titulo: Leer el gráfico: Resultado fiscal
resumen: El tercero de los cuatro. Dos líneas, una línea de cero y diez años de historia.
minutos: 8
panel: fiscal
---

Este es el gráfico más denso del grupo, y ya tenés todas las piezas: dos líneas (primario y financiero), frecuencia mensual desde 2016, en dólares blue, base caja.

### Cómo leerlo, en orden

- **Primero la línea de cero.** Todo lo que está arriba es superávit; abajo, déficit. Es la referencia que ordena la lectura.
- **Después la brecha entre las dos líneas.** Esa distancia son los intereses de la deuda de ese mes.
- **Después la tendencia**, no el mes suelto. Un mes malo puede ser estacional; seis meses seguidos son una política.
- **Al final, los picos.** Diciembre siempre cae: aguinaldo y concentración de pagos.

La serie empieza en 2016 porque esa es la cobertura del informe mensual que publica la Secretaría de Hacienda (el IMIG). No es que antes no hubiera datos: están en otro formato y con otra metodología, y empalmarlos daría una serie que parece continua sin serlo.

```tablero
titulo: Resultado fiscal del SPN
panel: fiscal
unidad: Millones de USD (dólar blue) · mensual · desde 2016

## suma
- Ingresos tributarios: IVA, Ganancias, retenciones, combustibles, débitos y créditos
- Aportes y contribuciones a la seguridad social
- Rentas de la propiedad e ingresos de capital

## resta
- Prestaciones sociales: jubilaciones, pensiones, AUH
- Salarios del sector público nacional
- Subsidios económicos (energía y transporte)
- Transferencias a provincias y gasto de capital
- Intereses de la deuda — SOLO en la línea del resultado financiero

## incluye
- Todo el Sector Público Nacional (administración central, descentralizados, fondos fiduciarios, PAMI, empresas públicas)
- Base caja: se cuenta cuando la plata se mueve, no cuando se devenga la obligación

## excluye
- Provincias y municipios: es solo la Nación
- El Banco Central y sus pasivos remunerados (eso está en el panel Deuda consolidada)
- La deuda flotante: facturas devengadas y todavía no pagadas
- Los intereses, en la línea del resultado primario

## si_sube
El mes cerró con superávit, o con menos déficit: al Estado le entró más de lo que gastó. No necesitó deuda nueva ni emisión para cubrir ese mes.

## si_baja
Déficit, o déficit más grande: faltó plata. Ese faltante se cubre con deuda o con emisión, así que reaparece más adelante — en el stock de deuda o en la inflación.

## trampas
- Diciembre da peor todos los años por el aguinaldo. Comparar diciembre contra noviembre no dice nada; contra el diciembre anterior, sí.
- Está en dólares blue: un salto del tipo de cambio achica el número sin que haya cambiado nada en pesos.
- Primario positivo con financiero negativo es normal, no un error: la diferencia son los intereses.
- Base caja: postergar pagos mejora el mes sin mejorar el fondo.
```
