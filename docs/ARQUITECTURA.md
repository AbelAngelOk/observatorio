# Arquitectura

## El flujo, de punta a punta

```
   FUENTES                      INGESTA                  ALMACEN        PUBLICACION      SITIO
 ┌────────────────────┐     ┌────────────────┐      ┌─────────────┐  ┌───────────┐  ┌──────────┐
 │ API datos.gob.ar   │────►│ pipeline_      │─┐    │             │  │           │  │          │
 │ (reservas, BCRA)   │     │ reservas.py    │ │    │             │  │           │  │          │
 └────────────────────┘     └────────────────┘ │    │             │  │           │  │          │
                                               │    │             │  │           │  │          │
 ┌────────────────────┐     ┌────────────────┐ │    │ observatorio│  │ export_   │  │ data/    │
 │ Boletín de deuda   │────►│ pipeline_      │ ├───►│ .db         │─►│ json.py   │─►│ *.json   │
 │ (.xlsx, Finanzas)  │     │ deuda_publica  │ │    │ (SQLite)    │  │           │  │ + _meta  │
 └────────────────────┘     └────────────────┘ │    │             │  └───────────┘  └────┬─────┘
                                               │    │  FUENTE DE  │                      │
 ┌────────────────────┐     ┌────────────────┐ │    │   VERDAD    │                      ▼
 │ Serie gasto/PBI    │────►│ pipeline_      │ │    │             │                 ┌──────────┐
 │ (.csv, Presupuesto)│     │ gasto_nacion   │ │    │             │                 │index.html│
 └────────────────────┘     └────────────────┘ │    │             │                 │ Chart.js │
                                               │    │             │                 └──────────┘
 ┌────────────────────┐     ┌────────────────┐ │    │             │
 │ Cifras verificadas │────►│ init_db.py     │─┘    │             │
 │ a mano             │     │ (semilla)      │      └─────────────┘
 └────────────────────┘     └────────────────┘
                              ▲
                              │  todo esto lo dispara  actualizar.py,  una vez por día
                              │  (.github/workflows/ingesta.yml)
```

## La base es la única fuente de verdad

**Los 12 paneles leen `data/<slug>.json`. Ninguno consulta una API externa desde el navegador.**
Si aparece un `fetch()` a un host de terceros en `index.html`, es un bug.

Esto no siempre fue así: reservas —el panel principal— le pegaba en vivo a `apis.datos.gob.ar` desde
el navegador del visitante. Se migró a la base, y en el camino apareció el motivo por el que ese
atajo era una mala idea: **la API corta en 5000 registros y no avisa que truncó**. Como la serie es
diaria desde 2003 (8.500+ puntos), el front venía mostrando datos hasta 2016 y presentaba un valor de
hace diez años como "último dato" — y el "máximo histórico" también estaba mal, porque el máximo real
caía fuera de la ventana truncada. Nadie lo notó durante meses.
El pipeline pagina y la base guarda la serie entera; el front solo dibuja lo que la base ya validó.

El precio es que el sitio muestra un snapshot, no datos al segundo. Con la ingesta corriendo a
diario, el desfasaje máximo es de 24 horas — irrelevante para indicadores que las fuentes publican
una vez por mes. A cambio: el sitio funciona aunque la API esté caída, y cada número quedó auditado
antes de publicarse.

## El modelo de datos

Tres tablas y dos vistas, en [schema.sql](../schema.sql).

**`fuentes`** — de dónde sale cada cosa. Lo importante es `tipo_acceso` (`api` / `csv` / `scraping` /
`manual`), que es lo que determina cuánto trabajo cuesta actualizar esa serie, y `frecuencia`.

**`series`** — el catálogo de indicadores. La clave real es el `slug` (`deuda_publica_bruta`), que es
el identificador que viaja por todo el sistema: es el nombre del archivo en `data/`, es lo que pide
`fetchSerie()` en el HTML, y es lo que los pipelines pasan a `insertar_observacion()`. Dos campos
que vale la pena mirar: `es_calculada` (1 = no es una serie que publique un organismo, sale de
combinar otras) y `metodologia`, una nota libre que viaja hasta el JSON exportado.

**`observaciones`** — los números. `(serie_id, fecha, valor)` más tres campos de trazabilidad:
`vintage`, `es_provisorio` y `fuente_url`.

## La decisión de diseño: append-only por vintage

**Nunca se hace `UPDATE` sobre una observación.** Cuando un valor cambia, se hace un `INSERT` con un
`vintage` nuevo (el timestamp de la corrida que lo trajo).

El motivo es concreto: el INDEC publica un trimestre como "provisorio" y meses después lo republica
corregido. Si el pipeline pisara el valor viejo, se perdería que hubo una revisión y de cuánto fue.
Con este esquema conviven las dos versiones de la misma `(serie, fecha)`, y la vista
**`ultimo_vintage`** (`MAX(vintage)` por serie y fecha) responde "cuál es el valor vigente hoy" sin
borrar nada. La vista **`series_con_datos`** encima junta serie + fuente + valor vigente, y es
exactamente lo que consume `export_json.py`.

### El guard de cambio: lo que hace posible la ingesta diaria

`core.insertar_observacion()` **solo escribe si el dato es nuevo o cambió** respecto del valor
vigente. Si la fuente publica lo mismo de siempre, no inserta nada y devuelve 0.

Sin ese guard, la ingesta diaria destruiría la base. El `UNIQUE` incluye el vintage y el vintage es
la hora de la corrida, así que **cada corrida diaria reinsertaría la serie entera**: reservas, con
8.567 puntos, generaría ~3 millones de filas por año, todas con el mismo valor, haciendo pasar por
"revisión" algo que nunca cambió.

Con el guard, `vintage` recupera su significado: hay una fila nueva cuando —y solo cuando— la fuente
efectivamente revisó el número. Corroborado: sobre 8.567 puntos con uno solo alterado, la ingesta
inserta exactamente **1** fila, deja las dos versiones conviviendo y `ultimo_vintage` devuelve la
correcta.

**La semilla usa un vintage centinela viejo y fijo** (`VINTAGE_SEMILLA = "2000-01-01T00:00:00+00:00"`
en [init_db.py](../init_db.py)). Como los pipelines escriben con el timestamp de hoy, cualquier dato
oficial que carguen **supersede automáticamente** al punto que se había cargado a mano para esa misma
fecha, sin que haya que borrar la semilla.

## La bitácora de ingestas

Un job diario que falla en silencio es peor que no tener job: la página se congela en el último dato
bueno y nadie se entera. Por eso cada corrida queda asentada en la tabla **`ingestas`** (pipeline,
inicio, fin, estado, filas nuevas, y el traceback si falló), y la vista **`ultima_ingesta`** da el
estado actual de cada pipeline.

`export_json.py` vuelca eso a `data/_meta.json`, y el sitio lo usa para el sello del encabezado:
**"Datos actualizados al …"** es la fecha de la última ingesta exitosa. Antes ese sello mostraba
`new Date()` — o sea, la fecha de hoy, aunque la ingesta estuviera rota hacía dos semanas.

## El contrato del JSON

`export_json.py` escribe un archivo por serie que tenga al menos una observación. Series declaradas
pero vacías simplemente no generan archivo (hoy: `deficit_gemelos_fiscal` y `gasto_nacion_anual`).

```json
{
  "indicador": "Deuda publica bruta",
  "unidad": "millones de USD",
  "metodologia": null,
  "fuente": "Boletin mensual de deuda",
  "tipo_acceso_fuente": "scraping",
  "datos": [
    { "fecha": "2023-11-30", "valor": 425294.0, "provisorio": true }
  ]
}
```

`datos` viene ordenado por fecha ascendente, y el front asume eso: toma `rows[rows.length-1]` como
"último dato" sin volver a ordenar.

## El front

`index.html` es un solo archivo: markup, CSS y JS inline, Chart.js por CDN, sin build step ni
dependencias de npm. Los 12 paneles leen su serie de `data/<slug>.json`; ninguno consulta una API
externa desde el navegador.

Los paneles se renderizan **de forma perezosa**: `renderDeuda()`, `renderFiscal()`, etc. se disparan
al hacer clic en el índice, cada uno una sola vez (un flag `xRendered` lo garantiza). Por eso los
recuadros de stats arrancan en `—` y se completan al abrir el panel.

Las series ahora traen decenas o cientos de puntos (reservas, ~8.500), así que los paneles densos usan
`lineaTemporal()`, un helper que dibuja una línea, oculta los marcadores cuando hay muchos puntos y
ralea las etiquetas del eje X. Los pocos paneles de 1-3 puntos siguen usando `barrasSimple()`.

Los stats **no están escritos a mano**: cada `render*()` los calcula desde las mismas filas que
alimentan su gráfico, con los helpers compartidos (`fmtUSD_M`, `setStat`, `puntoAnioAnterior`, …) que
están al principio del `<script>`. Así no pueden desfasarse del gráfico. Las pocas cifras que **no**
son derivables de la base quedan fijas en el HTML y están marcadas con un comentario `ESTATICO` —
están listadas en [DATOS.md](DATOS.md#cifras-que-siguen-siendo-estáticas).

Sobre el color de los stats hay dos criterios distintos, a propósito:

- **`tonoBaja`** (deuda, presión tributaria): bajar es la buena noticia → verde.
- **`tonoSigno`** (resultado fiscal, cuenta corriente, reservas): el signo ya dice todo → superávit
  verde, déficit rojo.
- **El gasto en pesos corrientes va sin color**: con inflación alta, una suba nominal no significa
  nada por sí sola, y pintarla de rojo sería editorializar sin base.
