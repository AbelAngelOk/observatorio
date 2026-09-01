# Catálogo de datos

32 series declaradas en [schema.sql](../schema.sql), 31 con datos (~11.100 observaciones), 1 vacía.
Este documento existe para responder una sola pregunta antes de que alguien cite un número de este
sitio: **¿qué tan sólido es?**

La mayoría de los indicadores pasó de ser una muestra de un puñado de puntos a ser una **serie
histórica completa desde los 2000**, gracias a que se encontró cada serie en una fuente programática
(ver [PIPELINES.md](PIPELINES.md#el-mapa-de-fuentes)). Lo que sigue es el estado después de eso.

## Los cuatro niveles de confianza

No todos los indicadores valen lo mismo, y mezclarlos sin avisar sería el error más grave que puede
cometer un proyecto como este.

### 1. Serie histórica completa, ingesta automática — se lee como una trayectoria

Series continuas traídas por un pipeline que corre todos los días. Son el corazón del sitio.

| Serie | Cobertura | Fuente | Panel |
|---|---|---|---|
| `reservas_internacionales` | Diaria, **2003 →** (8.582 pts) | BCRA vía API de series | 06 |
| `recaudacion_nacional` | Mensual, **2000 →** (318 pts) | Hacienda vía API | (apoyo) |
| `resultado_primario` / `resultado_financiero` | Mensual, **2016 →** (126 pts c/u) | IMIG Hacienda vía API | 07 |
| `exportaciones` / `importaciones` | Trimestral, **2003 →** (94 pts) | INDEC ICA vía API | 08 |
| `deuda_externa_bruta` | Trimestral, **2006 →** (77 pts) | INDEC vía API | 03 |
| `deuda_publica_bruta` | Anual 1993-2018 + mensual **2019 →** (123 pts) | Finanzas (trimestral + mensual) | 01 |
| `deuda_no_residentes` / `deuda_residentes` | Trimestral, **1994 →** (116 pts c/u) | Finanzas (boletín trimestral, hoja A.4.5) | 12 |
| `gasto_nacion_pbi` | Anual, **2004 →** (22 pts) | CSV de Presupuesto | 10 |
| `dolar_blue` / `dolar_oficial` | Mensual (blue 2011→, oficial 2002→) | Bluelytics / A3500 | (apoyo, panel 07) |

Las fechas de inicio no son arbitrarias: es lo más atrás que llega cada fuente oficial. Reservas
arranca en 2003, cuenta corriente y deuda externa en 2006 (metodología MBP6 del INDEC), el PBI en
2004 (año base), el resultado fiscal mensual del IMIG en 2016. Ir más atrás exigiría empalmar
metodologías distintas, que es justo lo que este proyecto evita.

> **Ojo con las cifras viejas de reservas.** Antes el panel consultaba la API en vivo desde el
> navegador, y **la API corta en 5000 registros sin avisar**: como la serie es diaria, la página
> mostraba datos hasta 2016 y daba como "último dato" un valor de hace diez años (US$ 31.274M), con un
> "máximo histórico" igual de falso (US$ 52.654M, cuando el real es US$ 77.481M). El pipeline pagina;
> las cifras de ahora son las correctas.

### 2. Serie calculada — sale de combinar dos series oficiales

No la publica ningún organismo, pero se deriva de series que sí son oficiales y están en la base.

| Serie | Cómo se calcula | Cobertura | Panel |
|---|---|---|---|
| `resultado_primario_usd` / `_financiero_usd` | resultado ARS ÷ dólar blue del mes | Mensual, 2016 → | 07 |
| `gasto_nacion_pbi` | gasto ÷ PBI (mismo CSV) | Anual, 2004 → | 10 |
| `presion_tributaria_nacional` | recaudación anual ÷ PBI | Anual, 2004 → | 11 |
| `resultado_primario_anual_pbi` | resultado primario anual ÷ PBI | Anual, 2016 → | 09 |
| `cuenta_corriente_pbi` | cuenta corriente anual ÷ PBI USD | Anual, 2006 → | 09 |
| `cartera_cer` / `cartera_tasa_fija` | ajustable CER / no-CER ÷ deuda en pesos (hoja A.1.4) | Anual, 2014 → | 05 |
| `deuda_consolidada` | deuda bruta + pasivos BCRA ÷ TC oficial | Anual, 2002 → | 02 |
| `deuda_neta` | consolidada − reservas | Anual, 2003 → | 04 |

`presion_tributaria_nacional` da 21,5% para 2025, cerca del 21,4% de IARAF — pero no es el mismo
número ni la misma definición (ver nivel 3). Que estén cerca valida el cálculo.

**La consolidada/neta son aproximaciones**: no restan las tenencias intra-sector público (Letras
Intransferibles, Adelantos Transitorios), que no se publican como serie limpia. Por eso pueden diferir
de las cifras que citan Chequeado o EcoGo. En 2025 la consolidada ≈ la bruta, porque los pasivos
remunerados del BCRA cayeron a ~0 (se eliminaron las Leliq y los pases pasaron a LEFI del Tesoro, que
ya están dentro de la deuda bruta).

### 3. Cálculo de terceros / muestra a mano — **poco denso, no oficial**

| Serie | Qué es | Puntos | Panel |
|---|---|---|---|
| `presion_tributaria` | Estimación de IARAF sobre datos de ARCA | 2 | 11 (nota al pie) |
| `cartera_dolar_linked` | Dato puntual OPC (no separable en la serie histórica) | 1 | 05 (nota al pie) |
| `gasto_nacion` | Muestra mensual verificada a mano (histórica) | 3 | — (reemplazado por % PBI) |

El **dólar blue** (`dolar_blue`) también entra acá en cuanto a confianza de fuente: es de Bluelytics,
una API pública pero **no oficial** — ningún organismo del Estado publica el paralelo. Se usa para el
panel 07 y está marcado como tal.

### Series declaradas sin datos

| Serie | Estado |
|---|---|
| `deficit_gemelos_fiscal` | **Huérfana.** Quedó duplicada por `resultado_primario_anual_pbi`, que es la que usa el panel 09. Candidata a borrarse del esquema. |

No genera archivo en `data/` — `export_json.py` saltea las series sin observaciones.

---

## Cómo se consiguió tanta historia

La clave fue la **API de series de tiempo de datos.gob.ar** (`apis.datos.gob.ar/series/api/`), que
agrega en un solo lugar series de INDEC, BCRA y Hacienda como JSON, sin scraping. Casi todo salió de
ahí; el detalle de cada `id` de serie está en [PIPELINES.md](PIPELINES.md#el-mapa-de-fuentes). Dos
excepciones que no están en la API y siguen siendo scraping:

- **Deuda pública bruta**: solo existe como boletín en Excel de la Secretaría de Finanzas.
- **Gasto anual**: un CSV suelto de la Subsecretaría de Presupuesto.

Y una trampa que costó ver: buscar "resultado primario" en el catálogo devuelve primero series **REM**
(la *encuesta de expectativas de mercado* del BCRA, o sea pronósticos de consultoras). El dato fiscal
real es la serie **IMIG** de Hacienda. Ingerir la REM por error habría sido publicar predicciones como
si fueran hechos.

---

## Advertencias metodológicas

Están en los pies de cada panel del sitio; acá quedan juntas para poder citarlas.

**La caída de la deuda en dic-2023 no es desendeudamiento.** Entre nov-2023 y dic-2023 la deuda bruta
cae fuerte. Eso es la devaluación de diciembre de 2023, que licuó el valor **en dólares** de la
porción de deuda emitida en pesos. No se pagó ni se canceló nada.

**Los pesos son corrientes, sin ajustar por inflación.** `resultado_primario`, `resultado_financiero`
y `gasto_nacion_anual` están en pesos nominales. Comparar dos períodos distantes en términos reales
exige deflactarlos primero — el sitio no lo hace, y por eso las variaciones nominales del gasto se
muestran **sin color**: una suba de tres dígitos en un año de inflación de tres dígitos no dice, por
sí sola, si el gasto real subió o bajó.

**Hay dos presiones tributarias, y no coinciden.** El panel muestra `presion_tributaria_nacional`
(cálculo propio: recaudación nacional ÷ PBI, ~21,5% para 2025). IARAF estima 21,4% y Econviews ~25%
para el mismo año, según qué base de tributos usan. Antes de citar cualquiera, mirá la definición.

**Deuda pública bruta ≠ deuda externa bruta.** La primera la mide Finanzas por emisor (Administración
Central). La segunda la mide el INDEC por residencia del acreedor, y abarca a toda la economía
—gobierno, BCRA, empresas y hogares—. No son subconjuntos una de la otra ni son comparables.

**El panel 12 (deuda por acreedor) no es ninguna de esas dos, y no es "deuda con terceros".** Es la
deuda **bruta de la Administración Central** partida por residencia del acreedor, según la hoja A.4.5
del boletín de Finanzas. Tres advertencias que hay que tener juntas antes de citarlo:

- **No es la consolidada**: no incluye los pasivos remunerados del BCRA.
- **"Residentes" incluye al propio Estado.** Esa línea contiene las tenencias de ANSES/FGS y del BCRA,
  porque el intra-sector público no se publica como serie limpia (la misma razón por la que
  `deuda_consolidada` tampoco lo resta). Leerla como "deuda con acreedores privados locales" es un
  error: el corte residentes/no residentes **no** equivale a "deuda con terceros".
- **Excluye los holdouts.** La hoja deja afuera la deuda elegible pendiente de reestructuración, así
  que su total es algo menor que el de `deuda_publica_bruta` (panel 01). Las dos cifras no cierran
  exactamente, y es esperable.

Además, el corte por residencia es una **estimación de Finanzas** construida sobre las cuentas
internacionales del INDEC —así lo aclara la propia hoja—, no un censo de tenedores.

**Los déficits gemelos no comparten unidad.** El panel 09 pone el resultado fiscal (% del PBI) y el
externo (millones de USD) en **dos gráficos separados** a propósito: meterlos en uno con dos ejes
haría que la comparación visual mienta.

---

## Cifras que siguen siendo estáticas

Casi todos los recuadros de stats se calculan desde los datos (ver
[ARQUITECTURA.md](ARQUITECTURA.md#el-front)). Quedan dos escritas a mano en `index.html`, marcadas ahí
con un comentario `ESTATICO`:

| Panel | Cifra | Por qué no se deriva |
|---|---|---|
| 03 Deuda externa | `% del PBI (I-26) = 46,9%` y `Mínimo % PBI (IV-24) = 39,1%` | El PBI de la base es anual; el ratio sobre PBI de una serie trimestral necesitaría el PBI trimestral, que no está cargado. |
| 07 Resultado fiscal | `Resultado 2024 = Financiero +0,3% PBI` | Ídem: ratio sobre PBI de una serie mensual/nominal. |

Ahora que el PBI anual está en la base, el resto de los ratios sobre PBI (presión tributaria, resultado
primario anual) **sí se calculan solos** — ver el nivel 2 más arriba. Para que estas dos últimas
también se deriven haría falta cargar el PBI trimestral (`9.2_PPC_2004_T_22`, que está en la API).
(Los recuadros `Frecuencia`, `Cobertura` y `Formato de la fuente` son metadatos, no cifras.)
