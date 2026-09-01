---
slug: leer-gasto-nacion
titulo: Leer el gráfico: Gasto de la Nación
resumen: El segundo de los cuatro. Cuántos puntos del PBI consume el Estado nacional.
minutos: 7
panel: gasto
---

Mismo procedimiento que con la carga impositiva, del otro lado del mostrador: el gasto primario dividido por el PBI, un punto por año desde 2004.

La lectura es directa: **cuántos puntos del producto consume el Estado nacional cada año**. La serie tiene una historia clara: un piso cerca del 13-14% del PBI a mediados de los 2000, un pico entre el 24% y el 26% entre 2015 y 2017, y una caída fuerte hasta cerca del 15-16% en 2024.

### Lo que el gráfico no dice

El gráfico muestra el tamaño, no la calidad ni la justicia del gasto. No dice si el gasto es "alto" o "bajo" —eso es una discusión política, no estadística— ni en qué se gastó. Un mismo 20% del PBI puede ser jubilaciones o subsidios a la energía.

> Tampoco incluye el gasto provincial ni municipal, que sumados son de un orden comparable al nacional. El gasto público argentino total es bastante mayor que esta línea.

```tablero
titulo: Gasto de la Nación
panel: gasto
unidad: % del PBI · anual · desde 2004

## suma
- Prestaciones sociales: jubilaciones, pensiones, AUH, asignaciones
- Salarios del sector público nacional
- Subsidios económicos (energía y transporte)
- Transferencias corrientes a provincias
- Gasto de capital (obra pública)
- Bienes, servicios y funcionamiento del Estado

## resta
- Los intereses de la deuda: por eso se llama gasto PRIMARIO

## incluye
- Todo el Sector Público Nacional: administración central, descentralizados, fondos fiduciarios, PAMI y empresas públicas
- El PBI del mismo año como denominador

## excluye
- Provincias y municipios — es solo la Nación
- Los intereses de la deuda
- El cuasifiscal: los intereses que paga el Banco Central por sus propios pasivos

## si_sube
El Estado nacional está gastando una porción mayor de lo que produce el país. Puede ser más gasto real, o un PBI que cayó (en una recesión el ratio sube solo).

## si_baja
El Estado consume menos puntos del producto. Puede ser un ajuste del gasto, o una economía que creció más rápido que el gasto — que es la forma indolora de bajarlo.

## trampas
- En recesión el ratio sube aunque el gasto real no se mueva: el denominador se achicó. Siempre mirá qué pasó con el PBI ese año.
- No incluye intereses. Un país puede bajar su gasto primario mientras su gasto total sube, si los intereses crecen.
- Es un dato anual: no sirve para juzgar un mes ni un trimestre concreto.
```
