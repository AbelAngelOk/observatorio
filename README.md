# Observatorio — Macroeconomía Argentina

Boletín de series históricas de la macroeconomía argentina: **12 indicadores** de deuda, reservas,
sector externo y cuentas públicas, construidos a partir de fuentes oficiales y publicados como un
sitio estático de una sola página.

La apuesta del proyecto no es tener muchos números, sino **decir con precisión de dónde sale cada
número y cuánto vale**. Una serie oficial continua y una foto de dos puntos calculada por una
consultora no valen lo mismo, y acá no se mezclan: cada panel dice explícitamente cuál es cuál.

---

## Arranque rápido

```powershell
pip install -r requirements.txt
python init_db.py                  # crea observatorio.db y carga la semilla verificada a mano
python actualizar.py               # corre los pipelines y exporta a data/
python -m uvicorn app:app --port 8000
# abrir http://localhost:8000
```

> **No abras `index.html` con doble clic.** La página lee sus datos con `fetch()`, y bajo `file://`
> el navegador lo bloquea: verías todos los paneles en rojo. Tiene que servirse por HTTP.
> Los detalles y el resto de los problemas típicos están en [docs/EJECUCION.md](docs/EJECUCION.md).

El servidor ([app.py](app.py)) reemplaza al viejo `python -m http.server`: sirve el sitio **y** la API
de cuentas y cursos. Los pipelines de ingesta no cambiaron en nada.

En producción no se corre nada a mano: **[la ingesta corre sola todos los días](.github/workflows/ingesta.yml)**
a las 06:00 ART y commitea la base solo si alguna fuente publicó algo nuevo.

---

## Los 12 indicadores

| # | Panel | Qué muestra | Fuente | Cobertura |
|---|---|---|---|---|
| 01 | Deuda pública bruta | Stock en USD | Finanzas (trimestral hist. + mensual) | **1993 →** |
| 02 | Deuda consolidada | Bruta + pasivos BCRA (cálculo propio) | Finanzas + BCRA | **Anual, 2002 →** |
| 03 | Deuda externa bruta | Stock en USD | INDEC vía API | **Trimestral, 2006 →** |
| 04 | Deuda neta | Consolidada − reservas (cálculo propio) | Finanzas + BCRA | **Anual, 2003 →** |
| 05 | Cartera de deuda en pesos | CER vs no-CER, barras apiladas | Finanzas (boletín A.1.4) | **Anual, 2014 →** |
| 06 | Reservas internacionales | Stock diario en USD | BCRA vía API | **Diaria, 2003 →** |
| 07 | Resultado fiscal | Primario y financiero **en USD (blue)** | IMIG Hacienda + Bluelytics | **Mensual, 2016 →** |
| 08 | Resultado externo | **Exportado vs importado** (barras) | INDEC vía API | **Trimestral, 2003 →** |
| 09 | Déficits gemelos | Fiscal y cuenta corriente, **% PBI, unificado** | Derivado de 07 + 08 | Anual, 2016 → |
| 10 | Gasto de la Nación | **% del PBI** | CSV de Presupuesto | **Anual, 2004 →** |
| 11 | Carga impositiva | Recaudación ÷ PBI | Hacienda + INDEC (cálculo) | **Anual, 2004 →** |
| 12 | Deuda por acreedor | Residentes vs **no residentes** (2 líneas) | Finanzas (boletín A.4.5) | **Trimestral, 1994 →** |

Casi todos los paneles son series históricas que arrancan entre 2003 y 2019 (lo más atrás que llega
cada fuente oficial). El catálogo completo, con la calidad de cada serie y las advertencias
metodológicas, está en [docs/DATOS.md](docs/DATOS.md).

---

## Cómo está armado

```
fuentes oficiales ──► pipelines ──► observatorio.db ──► export_json.py ──► data/*.json ──► index.html
 (API, Excel, CSV)     (Python)      (SQLite, la          (snapshot)                         (Chart.js)
                           ▲          FUENTE DE VERDAD)
                           │
                    actualizar.py, una vez por día (GitHub Actions)
```

**Los 12 paneles leen de la base.** Ninguno consulta una API externa desde el navegador: si aparece
un `fetch()` a un host de terceros en `index.html`, es un bug.

La pieza de diseño que importa: la base **nunca pisa una observación**. Cuando un valor cambia entra
una fila nueva con su propio *vintage*, porque INDEC y Finanzas republican cifras "provisorias" hacia
atrás y perder ese historial de revisiones sería perder información. La vista `ultimo_vintage`
resuelve cuál es el valor vigente hoy, y la ingesta **solo escribe si el dato efectivamente cambió**
— que es lo que permite correrla todos los días sin inflar la base.
Todo explicado en [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

---

## Mapa de archivos

| Archivo | Qué es |
|---|---|
| [index.html](index.html) | El sitio entero: markup, estilos y gráficos (Chart.js por CDN). Sin build step. |
| [schema.sql](schema.sql) | Esquema SQLite: series, observaciones, bitácora de ingestas. |
| [core.py](core.py) | El núcleo de ingesta: escritura idempotente en la base + cliente de la API de datos.gob.ar. |
| [actualizar.py](actualizar.py) | **El runner.** Corre los pipelines y exporta. Es lo que dispara el cron. |
| [init_db.py](init_db.py) | Crea (o migra) la base y carga las observaciones verificadas a mano. |
| [export_json.py](export_json.py) | Vuelca cada serie a `data/<slug>.json`, más `_meta.json` con el estado de la ingesta. |
| [pipeline_reservas.py](pipeline_reservas.py) | Reservas por API. **El pipeline modelo**: copialo para agregar otro. |
| [pipeline_cotizaciones.py](pipeline_cotizaciones.py) | Dólar blue (Bluelytics), oficial y pasivos del BCRA. |
| [pipeline_sector_externo.py](pipeline_sector_externo.py) | Cuenta corriente, deuda externa y expo/impo (INDEC vía API). |
| [pipeline_fiscal.py](pipeline_fiscal.py) | Resultado fiscal (ARS y USD), PBI y ratios % PBI. |
| [pipeline_recaudacion.py](pipeline_recaudacion.py) | Recaudación y presión tributaria calculada. |
| [pipeline_deuda_publica.py](pipeline_deuda_publica.py) | Boletín mensual de deuda (Excel). **Experimental**. |
| [pipeline_gasto_nacion.py](pipeline_gasto_nacion.py) | Gasto anual y gasto % PBI (CSV). **Experimental**. |
| [pipeline_deuda_historica.py](pipeline_deuda_historica.py) | Deuda anual 1993-2018 + consolidada/neta. **Experimental**. |
| [pipeline_cartera.py](pipeline_cartera.py) | Composición de deuda en pesos por año (Excel). **Experimental**. |
| [pipeline_deuda_residencia.py](pipeline_deuda_residencia.py) | Deuda bruta por residencia del acreedor, hoja A.4.5 (Excel). **Experimental**. |
| [.github/workflows/ingesta.yml](.github/workflows/ingesta.yml) | La ingesta diaria automática. |
| [app.py](app.py) | **El servidor.** Sirve el sitio y la API. Reemplaza a `http.server`. |
| [webapp/](webapp/) | Cuentas de usuario (`auth.py`), cursos y su contenido (`cursos/`), certificados en PDF (`certificados.py`). |
| [assets/](assets/) | JS del frontend nuevo: cuenta, cursos y certificaciones. |
| `observatorio.db`, `data/` | Generados. Se rehacen con los comandos del arranque rápido. |
| `app.db` | **Usuarios y progreso.** Nunca se versiona (está en `.gitignore`) y no se puede regenerar. |

---

## Cursos

Además de los gráficos, el sitio tiene un módulo de cursos que enseña a interpretarlos: **uno por
cada grupo temático** del menú de indicadores.

| Curso | Grupo | Capítulos | Lectura |
|---|---|---|---|
| Cuentas públicas | Cuentas públicas | 15 | ~99 min |
| Deuda y reservas | Deuda y reservas | 14 | ~95 min |
| Sector externo | Sector externo | 4 | ~22 min |

Cada uno lleva de cero a poder leer los gráficos de su grupo. Cada capítulo que explica un gráfico
termina con un **tablero**: qué suma y qué resta la cuenta, qué incluye y qué deja afuera, qué
significa que suba o que baje, y las trampas al leerlo. Varios capítulos incluyen además un
**diagrama** (SVG chico, sin librerías) para mostrar cómo se relacionan un par de entidades — por
ejemplo, que el Estado contiene a la Nación, las provincias y los municipios, o que la deuda
consolidada es la suma de la deuda del Tesoro y la del Banco Central.

El contenido es de lectura libre. Con una cuenta, además, se guarda qué capítulos completaste, curso
por curso — la vista "Cursos" abre en un catálogo con los tres, cada uno con su propia barra de
avance.

**Al terminar los capítulos de un curso se habilita su evaluación**: preguntas de opción múltiple que,
aprobadas con 70% o más, dan un **certificado descargable en PDF** con tu nombre completo. Esto vive en
una sección aparte del menú, **Certificaciones**, con el estado de cada curso y el botón de descarga.
El detalle completo —el DSL de las preguntas, el esquema, los endpoints, cómo se arma el PDF— está en
[docs/CURSOS.md](docs/CURSOS.md#evaluaciones-y-certificados).

**El contenido vive en Markdown**, un archivo por capítulo, en
[webapp/cursos/contenido/](webapp/cursos/contenido/) (una carpeta por curso, ej.
[cuentas-publicas/](webapp/cursos/contenido/cuentas-publicas/)). El prefijo numérico del nombre de
archivo (`00-`, `01-`, …) define el orden — renombrar el archivo reordena el curso sin afectar el
progreso guardado de nadie, porque el `slug` real vive en el front matter, no en el nombre. Formato
de un capítulo:

````markdown
---
slug: mi-capitulo
titulo: Título del capítulo
resumen: Una línea que aparece en el índice.
minutos: 6
panel: fiscal          # opcional: si el capítulo explica un gráfico, cuál
---

Párrafos en markdown simple: **negrita**, ### subtítulos, listas con "- ",
notas con "> ". Dos bloques especiales con fences:

```tablero
titulo: ...
panel: fiscal
unidad: ...

## suma
- item
- item

## si_sube
Texto libre.
```

```diagrama
forma: conjuntos        # o "flujo"
contenedor: Estado
parte: Nación
parte: Provincias
```
````

El parser (`webapp/cursos/cargador.py`) es un archivo chico y sin dependencias nuevas: la sintaxis es
un subconjunto fijo que nosotros mismos escribimos, así que no hace falta una librería de Markdown.
Un tablero al que le falta un campo, o un diagrama con un nodo mal escrito, frena el arranque del
servidor en vez de romperse en producción. Para validar el contenido sin levantar nada:

```powershell
python -m webapp.cursos
```

## Documentación

**El observatorio de datos:**
- [docs/EJECUCION.md](docs/EJECUCION.md) — cómo se corre, qué esperar, y qué hacer cuando algo falla.
- [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) — flujo de datos, modelo de la base, el diseño por *vintage*.
- [docs/DATOS.md](docs/DATOS.md) — catálogo de las 17 series y la calidad de cada una.
- [docs/PIPELINES.md](docs/PIPELINES.md) — cómo ingerir datos nuevos y qué falta confirmar antes de confiar en los pipelines.

**La webapp (cuentas y cursos):**
- [docs/WEBAPP.md](docs/WEBAPP.md) — el stack (FastAPI, SQLite, vanilla JS) y por qué cada pieza.
- [docs/AUTENTICACION.md](docs/AUTENTICACION.md) — cómo funcionan el registro, el login y las sesiones.
- [docs/CURSOS.md](docs/CURSOS.md) — qué es el módulo de cursos, a nivel de producto y de arquitectura.
- [docs/FRONTEND.md](docs/FRONTEND.md) — decisiones técnicas del frontend: routing, sin framework, theming.
