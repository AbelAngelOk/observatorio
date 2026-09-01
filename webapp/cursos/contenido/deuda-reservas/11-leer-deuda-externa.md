---
slug: leer-deuda-externa
titulo: Leer el gráfico: Deuda externa bruta
resumen: El quinto de los seis. Toda la economía, medida por el INDEC.
minutos: 8
panel: externa
---

Con el criterio del capítulo anterior, ya podés leer este gráfico.

### Cómo leerlo

- **Es de toda la economía**, no solo del Estado — tenelo presente antes de citarlo como si fuera "la deuda del país" en el sentido de deuda pública.
- **Tiene 2-3 meses de rezago**: el trimestre más reciente en el gráfico casi nunca es el trimestre calendario más reciente.
- **Los dos recuadros de "% del PBI" están fijos**, no se recalculan del gráfico: la base todavía no tiene cargado el PBI trimestral que haría falta para ese cociente. Son cifras tomadas del informe del INDEC, no un cálculo de este sitio.

```tablero
titulo: Deuda externa bruta
panel: externa
unidad: Millones de USD, valor nominal · trimestral · desde 2006

## suma
- Pasivos de todos los sectores residentes (gobierno general, Banco Central, empresas financieras y no financieras, hogares) frente a acreedores no residentes

## resta
Nada — es un stock bruto, a valor nominal, sin descontar activos externos del país.

## incluye
- Gobierno, Banco Central, empresas y hogares: toda la economía, no solo el Tesoro
- Metodología MBP6 del INDEC (posición de inversión internacional)

## excluye
- Pasivos entre residentes (deuda del Tesoro con un banco argentino, por ejemplo, no cuenta acá)
- Los activos externos del país (eso sería una posición neta, otro concepto)

## si_sube
El país en su conjunto tomó más deuda con no residentes de la que pagó.

## si_baja
Se pagó más deuda externa de la que se tomó. A diferencia de la deuda pública, acá una devaluación pesa menos: la serie ya está en dólares nominales.

## trampas
- No es lo mismo que la deuda pública bruta: esa la mide Finanzas por quién la emitió (solo el Tesoro); esta la mide el INDEC por quién es el acreedor (toda la economía). No son subconjunto una de la otra.
- El % del PBI que muestra el panel es una cifra fija, tomada del informe del INDEC — no se recalcula de los datos de este sitio.
- Tiene 2-3 meses de rezago: el trimestre más reciente casi nunca es el más reciente del calendario.
```
