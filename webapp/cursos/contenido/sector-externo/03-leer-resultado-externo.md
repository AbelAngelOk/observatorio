---
slug: leer-resultado-externo
titulo: Leer el gráfico: Resultado externo
resumen: El único gráfico del grupo. Dos barras por trimestre.
minutos: 8
panel: externo
---

Con lo anterior, ya podés leer el único gráfico de este grupo.

### Cómo leerlo

- **Dos barras por trimestre**: exportado e importado. Cuando la barra de exportaciones supera a la de importaciones, hay superávit comercial ese trimestre.
- **Tiene 2-3 meses de rezago**: el trimestre más reciente del gráfico no es, casi nunca, el trimestre calendario más reciente.
- **Es trimestral, no mensual**: no busques el dato de un mes puntual, no existe en esta serie.

Con este gráfico cerrás el curso. Es corto porque el grupo tiene un solo indicador — pero ya sabés de dónde sale, con qué convención se mide, y cómo se conecta con la deuda y las cuentas públicas del país.

```tablero
titulo: Resultado externo — comercio exterior
panel: externo
unidad: Millones de USD · trimestral, con 2-3 meses de rezago · desde 2003

## suma
- Exportaciones a valor FOB (mercadería puesta a bordo, sin flete ni seguro)

## resta
- Importaciones a valor CIF (mercadería más flete y seguro hasta destino)

## incluye
- Todo el comercio de bienes del país con el resto del mundo, medido por el INDEC (ICA)

## excluye
- Servicios (turismo, fletes, software) — esos entran en la cuenta corriente, no en este gráfico
- Rentas y transferencias con el exterior — ídem
- Los movimientos de capital y financieros (eso es la cuenta financiera, otra cosa)

## si_sube
El país vendió más al resto del mundo de lo que le compró ese trimestre: entran más dólares comerciales de los que salen.

## si_baja
El país compró más de lo que vendió: el faltante de dólares hay que cubrirlo con reservas o con deuda externa nueva.

## trampas
- Exportaciones (FOB) e importaciones (CIF) no se valúan con el mismo criterio exacto — es la convención internacional estándar, no un error del sitio.
- No incluye servicios, rentas ni transferencias — eso es la cuenta corriente, un número más amplio.
- Tiene 2-3 meses de rezago: el trimestre más reciente del gráfico no es el más reciente del calendario.
```
