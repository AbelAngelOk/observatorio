# Pipelines de ingesta

Un pipeline hace tres cosas: trae lo que publica el organismo, lo normaliza a `{fecha, valor}` y lo
escribe en `observatorio.db`. **Nunca escribe JSON directamente** — de eso se encarga `export_json.py`
después, y `actualizar.py` lo llama solo.

Todos comparten [core.py](../core.py), que es donde vive la lógica de escritura y el cliente de la API.

## El estado real

| Pipeline | Fuente | Estado |
|---|---|---|
| [pipeline_reservas.py](../pipeline_reservas.py) | API de series | ✅ Confiable. Reservas diarias, 2003 →. |
| [pipeline_cotizaciones.py](../pipeline_cotizaciones.py) | API de series + Bluelytics | ✅ Confiable. Blue, oficial y pasivos BCRA. |
| [pipeline_sector_externo.py](../pipeline_sector_externo.py) | API de series (INDEC) | ✅ Confiable. Cuenta corriente, deuda externa, expo/impo. |
| [pipeline_fiscal.py](../pipeline_fiscal.py) | API de series (Hacienda + INDEC) | ✅ Confiable. Fiscal (ARS y USD), PBI, ratios % PBI. |
| [pipeline_recaudacion.py](../pipeline_recaudacion.py) | API de series (Hacienda) | ✅ Confiable. Recaudación 2000 → y presión tributaria. |
| [pipeline_deuda_publica.py](../pipeline_deuda_publica.py) | Excel mensual de Finanzas | ⚠️ **Experimental.** Layout de .xlsx. |
| [pipeline_gasto_nacion.py](../pipeline_gasto_nacion.py) | CSV de Presupuesto | ⚠️ **Experimental.** CSV en host con robots.txt. |
| [pipeline_deuda_historica.py](../pipeline_deuda_historica.py) | Excel trimestral (hoja A.2.5) | ⚠️ **Experimental.** Backfill anual + consolidada/neta. |
| [pipeline_cartera.py](../pipeline_cartera.py) | Excel trimestral (hoja A.1.4) | ⚠️ **Experimental.** Un archivo por año. |
| [pipeline_deuda_residencia.py](../pipeline_deuda_residencia.py) | Excel trimestral (hoja A.4.5) | ⚠️ **Experimental.** Residentes / no residentes, 1994 →. |

Los cinco primeros salen de fuentes con contrato estable (API de series + Bluelytics) y corren en la
ingesta diaria. Los cuatro experimentales dependen de scraping de un archivo cuyo formato puede cambiar,
así que **no corren en el cron**: un job desatendido no debería meter en la base el resultado de un
parseo roto. Ya fueron confirmados contra el archivo real, pero se corren a pedido:
`python actualizar.py --incluir-experimentales`.

## El mapa de fuentes

Cada serie y de dónde sale. Los `id` de la API se buscan en
`https://apis.datos.gob.ar/series/api/search/?q=<texto>`.

| Serie | `id` de la API / fuente | Desde |
|---|---|---|
| `reservas_internacionales` | `92.2_RESERVAS_IRES_0_0_32_40` | 2003 |
| `recaudacion_nacional` | `172.3_TL_RECAION_M_0_0_17` | 2000 |
| `resultado_primario` / `_financiero` | `452.3_RESULTADO_RIO/ERO...` (IMIG) | 2016 |
| `pbi_anual` / `pbi_usd_anual` | `9.1_PPC_2004_A_22` / `9.1_PDPC_2004_A_30` | 2004 |
| `cuenta_corriente` (trim/anual) | `160.2_TL_CUENNTE_0_T_22` / `160.1_..._A_22` | 2006 |
| `deuda_externa_bruta` | `161.1_TL_DEUDRNA_0_0_19` | 2006 |
| `exportaciones` / `importaciones` | `74.2_IET_0_T_16` / `74.2_IIT_0_T_25` (ICA) | 2003 |
| `dolar_blue` | Bluelytics `api.bluelytics.com.ar/v2/evolution.json` | 2011 |
| `dolar_oficial` | `168.1_T_CAMBI500_D_0_0_17` (A3500) | 2002 |
| `pasivos_bcra` | `300.1_AP_PAS_TITCRA` + `331.1_PASES_REDESES` | 2002 |
| `deuda_publica_bruta` | boletín mensual A.1 (2019+) + trimestral A.2.5 (1993-2018) | 1993 |
| `cartera_cer` / `cartera_tasa_fija` | boletín trimestral, hoja A.1.4 | 2014 |
| `gasto_nacion_anual` / `_pbi` | CSV `serie_pib_anual.csv` | 2004 |
| `deuda_no_residentes` / `deuda_residentes` | boletín trimestral, hoja A.4.5 | 1994 |

Dos trampas verificadas: (1) el **dólar blue no está en datos.gob.ar** (no es oficial) — se toma de
Bluelytics, marcado como fuente no oficial. (2) `resultado primario` en el buscador devuelve primero
series **REM** (expectativas de mercado del BCRA), no el dato fiscal — las series IMIG (`452.*`) son el
dato real.

## Series calculadas (cálculo propio, no oficiales)

| Serie | Fórmula |
|---|---|
| `resultado_primario_usd` / `_financiero_usd` | resultado ARS ÷ dólar blue del mes |
| `gasto_nacion_pbi` | gasto ÷ PBI (del mismo CSV) |
| `presion_tributaria_nacional` | recaudación anual ÷ PBI |
| `resultado_primario_anual_pbi` | resultado primario anual ÷ PBI |
| `cuenta_corriente_pbi` | cuenta corriente anual ÷ PBI en USD |
| `deuda_consolidada` | deuda bruta + pasivos BCRA ÷ TC oficial (fin de año) |
| `deuda_neta` | consolidada − reservas |

La consolidada/neta son aproximaciones: **no** restan las tenencias intra-sector público (Letras
Intransferibles, Adelantos Transitorios), que no se publican como serie limpia. Se documentan como tal.

## El contrato

```python
import core

core.insertar_observacion(conn, serie_slug, fecha, valor, fuente_url=None, es_provisorio=False)
```

- **`serie_slug`** tiene que existir en la tabla `series` ([schema.sql](../schema.sql)); si no, tira
  `ValueError`.
- **`fecha`** en `YYYY-MM-DD`. Convención de la base: las series mensuales usan el último día del mes;
  las anuales, el 31/12.
- **`fuente_url`** es la URL exacta de donde salió ese número. No es decorativo: es lo que permite
  auditar un dato meses después.
- **Solo escribe si el dato cambió.** Devuelve 1 si insertó, 0 si el valor ya estaba y es idéntico.
  Esto es lo que hace posible correr la ingesta todos los días: sin el guard, como el `UNIQUE` incluye
  el `vintage` y el `vintage` es la hora de la corrida, cada corrida diaria reinsertaría la serie
  entera como si cada punto hubiera sido revisado. Ver
  [ARQUITECTURA.md](ARQUITECTURA.md#el-guard-de-cambio-lo-que-hace-posible-la-ingesta-diaria).

Y para que la corrida quede registrada en la bitácora (con su error, si falla):

```python
with core.corrida("mi_pipeline") as ctx:
    for punto in puntos:
        ctx.nuevas += core.insertar_observacion(ctx.conn, slug, punto["fecha"], punto["valor"])
```

## El camino fácil: la API de series

Si el indicador está en el catálogo de datos.gob.ar, el pipeline entero son tres líneas — sin
scraping, sin Excel, sin `robots.txt`:

```python
puntos = core.fetch_serie_datos_gob("92.2_RESERVAS_IRES_0_0_32_40")
```

Para buscar el id: `https://apis.datos.gob.ar/series/api/search/?q=<lo que busques>`.
Copiá [pipeline_reservas.py](../pipeline_reservas.py), que es el modelo.

**Dos trampas verificadas, las dos caras:**

1. **La API corta en 5000 registros y no avisa que truncó.** `fetch_serie_datos_gob()` pagina por eso.
   Si escribís tu propio fetch y te olvidás, vas a publicar una serie que "termina" hace años sin
   ningún síntoma: exactamente lo que le pasaba al panel de reservas de este sitio.
2. **El buscador devuelve series REM como si fueran datos.** Buscando "resultado primario" lo único
   que aparece son series del **Relevamiento de Expectativas de Mercado** — pronósticos de consultoras,
   no el dato fiscal publicado. Confirmá siempre que la serie sea el dato real antes de ingerirla.

---

## `pipeline_deuda_publica.py` — deuda pública bruta

**Fuente:** boletín mensual de deuda de la Secretaría de Finanzas. Un `.xlsx` cuyo nombre cambia todos
los meses, publicado en una página de índice. No hay API, no hay endpoint estable: hay que resolver
el link vigente contra el HTML de la página.

**Cómo funciona:** `find_latest_excel_url()` busca links `.xlsx` en la página de índice →
`download_excel()` lo baja → `parse_serie(xlsx, ["deuda", "bruta"])` busca la fila cuya etiqueta
contenga todas esas palabras y la cruza con la fila de fechas → escribe cada punto en la base.

**Qué falta confirmar antes de confiar en él:**

1. **`find_latest_excel_url()` se queda con el primer `.xlsx` de la página.** Si la página lista varios
   adjuntos, el primero puede no ser el boletín. Verificá qué URL devuelve antes de creerle.
2. **`parse_serie()` asume que las fechas están en la fila 1** de la hoja, y elige la hoja cuyo nombre
   contenga "serie" (o la primera). Abrí el Excel una vez y confirmalo:
   ```python
   import openpyxl
   wb = openpyxl.load_workbook("_tmp_deuda.xlsx", data_only=True)
   print(wb.sheetnames)
   ws = wb[wb.sheetnames[0]]
   for row in ws.iter_rows(min_row=1, max_row=8, max_col=6):
       print([c.value for c in row])
   ```
3. **Las etiquetas de fila cambian entre publicaciones.** El match es "que la celda contenga todas
   estas palabras", así que una fila nueva llamada *"deuda bruta en moneda extranjera"* también matchea
   `["deuda", "bruta"]` y podría ganarle a la que buscabas.

**Aperturas que se pueden agregar** (el dict `INDICADORES` ya está preparado): deuda por moneda, por
residencia, por instrumento. Cada una necesita su `slug` en `schema.sql` primero.

**Lo que NO puede salir de acá:** `deuda_consolidada` y `deuda_neta` no son filas de este Excel, son
cálculos (deuda bruta + pasivos remunerados del BCRA, neto de reservas). Para automatizarlos hace falta
primero un pipeline de pasivos del BCRA, y después un paso derivado que lea las dos series de la base y
escriba el resultado.

---

## `pipeline_gasto_nacion.py` — gasto anual de la Nación

**Fuente:** "Serie anual con gastos, recursos y PIB" de la Subsecretaría de Presupuesto, publicada como
CSV plano en datos.gob.ar (dataset `sspre_195`). Es la fuente más cómoda del proyecto: no hay Excel que
parsear.

Escribe en **`gasto_nacion_anual`**, que es una serie distinta de `gasto_nacion` (los puntos mensuales
verificados a mano que muestra el panel 10). Hoy `gasto_nacion_anual` no alimenta ningún panel: para
que aparezca en el sitio hay que agregarle un panel al HTML, o cambiar el panel 10 para que la lea.

**Qué falta confirmar:**

1. **El separador y el encoding están adivinados** (`sep=";"`, `encoding="latin-1"`, lo típico de las
   publicaciones de Presupuesto). Si `pandas` tira un error de parseo, es esto.
2. **Los nombres de columna también.** `normalize()` busca una columna que contenga "anio"/"ano" y otra
   que contenga "gasto". Descomentá el `print(df.columns.tolist())` que ya está en el código y confirmá
   contra el CSV real.
3. **Cuál columna de gasto.** El CSV trae gasto, recursos y PBI; puede haber más de una columna con
   "gasto" en el nombre (primario, total, corriente…). El `next()` se queda con la primera que aparezca.

---

## `pipeline_deuda_residencia.py` — deuda por residencia del acreedor

**Fuente:** hoja **A.4.5 ("Por residencia del tenedor")** del boletín trimestral de deuda de la
Secretaría de Finanzas — el mismo archivo que usa `pipeline_cartera.py`, otra hoja.

**Por qué es el más barato de los experimentales:** esa hoja trae **la serie histórica entera
(1994 → hoy, 116 puntos) en una sola tabla**, así que alcanza con descargar el boletín más reciente.
No hace falta un archivo por año como en `pipeline_cartera.py`.

Escribe dos series que **suman el total** de esa hoja:

```
deuda_no_residentes = columna "Deuda Externa"   (acreedores del exterior)
deuda_residentes    = columna "Deuda Interna"   (acreedores locales)
```

**Qué mide y qué no** — es lo más importante de este pipeline, porque el nombre de la hoja induce a
tres confusiones distintas:

1. **Es deuda BRUTA de la Administración Central, no la consolidada.** No incluye los pasivos
   remunerados del BCRA (eso es `deuda_consolidada`).
2. **No es "deuda con terceros".** La línea de residentes incluye las tenencias del **propio sector
   público** (ANSES/FGS, BCRA). Finanzas no publica el intra-sector público como serie limpia —la misma
   limitación que ya arrastra `deuda_consolidada`—, así que no se puede restar.
3. **No es la deuda externa del panel 03.** Aquella la mide el **INDEC** y abarca a toda la economía
   (gobierno, BCRA, empresas y hogares); esta es solo la Administración Central, medida por Finanzas.

Dos detalles más de la fuente, ya contemplados en el parser: la hoja **excluye la deuda elegible
pendiente de reestructuración**, así que su total es algo menor que `deuda_publica_bruta`; y el primer
trimestre de 2002 viene con `n/d` en la apertura, así que ese punto se saltea (116 puntos de 117 filas).

**Cómo se protege del layout:** ubica la hoja por su título (`"RESIDENCIA DEL TENEDOR"`) si el código
`A.4.5` cambiara, ubica las columnas leyendo la fila de encabezados en vez de asumir B/C/D/E, y
**valida que `externa + interna` reconstruya el total publicado** (tolerancia 1%) — si esa igualdad se
rompe, aborta en vez de escribir números mal interpretados.

**Unidades:** la hoja publica en *miles de millones* de USD y la base guarda *millones*, así que el
pipeline multiplica por 1000.

---

## Agregar una serie nueva

1. **`schema.sql`** — agregá la fuente en `fuentes` (si es nueva) y la serie en `series`, con su `slug`,
   unidad y, si es un cálculo, `es_calculada = 1` y la nota de `metodologia`.
2. **`python init_db.py`** — aplica el esquema nuevo sin tocar los datos existentes.
3. **Escribí el pipeline**: copiá [pipeline_reservas.py](../pipeline_reservas.py) si la fuente está en
   la API; si no, mirá los experimentales. Registralo en el dict `PIPELINES` de
   [actualizar.py](../actualizar.py) (arranca como experimental hasta que lo confirmes contra la
   fuente real).
4. **`python actualizar.py --solo <nombre>`** → los datos entran a la base y salen a `data/<slug>.json`.
5. **`index.html`** — agregá el `<li>` al índice, la `<section class="panel">` con sus canvas e ids de
   stats, y la función `render<Panel>()`. Copiá el panel más parecido: los helpers (`barrasSimple`,
   `fetchSerie`, `setStat`, `fmtUSD_M`…) ya están.

---

## La ingesta diaria

[.github/workflows/ingesta.yml](../.github/workflows/ingesta.yml) corre `python actualizar.py` todos
los días a las 09:00 UTC y commitea la base **solo si algo cambió**. Los pipelines experimentales
quedan afuera.

Si un pipeline falla, el error queda guardado y el job se ve rojo:

```sql
SELECT pipeline, estado, filas_nuevas, mensaje FROM ultima_ingesta;
```

Correr esto todos los días sobre fuentes que publican una vez por mes es intencional: es más barato
chequear de más que perderse una publicación o una revisión. Como la ingesta solo escribe cuando el
dato cambió, las corridas de más no cuestan nada.

**Nota legal.** Los dos hosts de los pipelines experimentales (`argentina.gob.ar` y
`dgsiaf-repo.mecon.gob.ar`) tienen `robots.txt` restrictivo para crawlers genéricos. Una descarga
puntual con `requests` desde infraestructura propia es una petición HTTP normal y funciona, pero
**revisá los términos y condiciones antes de automatizarlo**, y no le pegues más seguido de lo que
publican. La API de series (`apis.datos.gob.ar`), que es la que usa la ingesta diaria, es pública y
está pensada para consumo programático.
