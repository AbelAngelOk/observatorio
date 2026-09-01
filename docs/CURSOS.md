# El módulo de cursos

## Qué es, a nivel de producto

El observatorio muestra gráficos; el módulo de cursos enseña a **leerlos**. Son cursos cortos,
divididos en capítulos, pensados para alguien sin formación económica — uno por cada grupo temático
del menú de indicadores:

| Curso (`slug`) | Grupo | Capítulos | Lectura | Gráficos que enseña a leer |
|---|---|---|---|---|
| `cuentas-publicas` | Cuentas públicas | 15 | ~99 min | Carga impositiva, Gasto de la Nación, Resultado fiscal, Déficits gemelos |
| `deuda-reservas` | Deuda y reservas | 14 | ~95 min | Deuda pública bruta, Deuda consolidada, Reservas internacionales, Deuda neta, Deuda externa, Cartera de deuda en pesos |
| `sector-externo` | Sector externo | 4 | ~22 min | Resultado externo |

`sector-externo` es deliberadamente corto: el grupo tiene un solo gráfico, así que el curso no se
estira para parecerse a los otros dos — va directo a lo que hace falta para leerlo, con dos capítulos
de contexto que lo conectan con la cuenta corriente y con los otros dos cursos.

Dos piezas de contenido hacen el trabajo pedagógico:

- **El tablero** — al final de cada capítulo que explica un gráfico, una ficha fija con: qué **suma**
  y qué **resta** la cuenta, qué **incluye** y qué **excluye**, qué significa que la línea **suba** o
  **baje**, y las **trampas** habituales al leerla. Es lo que convierte "leí sobre el resultado
  fiscal" en "puedo abrir ese gráfico y decir algo correcto sobre él" — cierra la distancia entre la
  teoría del capítulo y el gráfico real.
- **El diagrama** — un dibujo chico (SVG) para las dos o tres relaciones que son más fáciles de ver
  que de leer: por ejemplo, que el Estado *contiene* a la Nación, las provincias y los municipios.

Y, al terminar, una tercera pieza que cierra el curso: **la evaluación**, un examen de opción múltiple
que, aprobado, habilita un **certificado descargable en PDF** con el nombre de quien lo rindió — ver
[Evaluaciones y certificados](#evaluaciones-y-certificados) más abajo.

**Acceso**: el contenido de los capítulos es de lectura libre, sin cuenta. Solo hace falta una cuenta
para que el sitio **recuerde** qué capítulos ya completaste — la decisión de producto es que una
cuenta sirve para llevar un registro, no para dar acceso a datos que ya son públicos. La evaluación es
la excepción: rendirla exige sesión, porque su único fin es emitir un certificado con tu nombre, y eso
no tiene sentido de forma anónima. El detalle de esa decisión está en el docstring de
[webapp/rutas_cursos.py](../webapp/rutas_cursos.py).

## Arquitectura de contenido: Markdown, no base de datos ni Python

Cada capítulo es un archivo `.md` en
[webapp/cursos/contenido/cuentas-publicas/](../webapp/cursos/contenido/cuentas-publicas/). La base de
datos **no** guarda el contenido del curso — solo el progreso (qué capítulos completó cada usuario).
Los slugs de capítulo son el único contrato entre los dos mundos.

**Por qué Markdown**: es prosa larga que se escribe y revisa como texto, no como código ni como filas
de una tabla. **Por qué no una librería de Markdown** (`markdown`, `mistune`, etc.): la sintaxis que
usan los capítulos es un subconjunto chico y fijo que escribimos nosotros mismos (no hay input de
terceros que pueda traer sintaxis inesperada), así que un parser propio de ~150 líneas
([webapp/cursos/cargador.py](../webapp/cursos/cargador.py)) alcanza y evita sumar una dependencia al
proyecto.

### Orden de archivos vs. identidad de capítulo

El nombre del archivo lleva un prefijo numérico (`00-`, `01-`, …) que define el **orden** — se
recorren con `sorted(base.glob("*.md"))`. Pero el `slug` real de cada capítulo vive en su *front
matter*, no en el nombre de archivo. Consecuencia concreta: **renombrar o reordenar archivos nunca
rompe el progreso guardado de nadie**, porque la tabla `progreso` guarda `capitulo_slug`, no un nombre
de archivo ni una posición.

### El formato de un archivo

```markdown
---
slug: mi-capitulo
titulo: Título del capítulo
resumen: Una línea que aparece en el índice.
minutos: 6
panel: fiscal          # opcional: si el capítulo explica un gráfico, cuál
---

Párrafos en markdown simple: **negrita**, ### subtítulos, listas con "- ",
notas con "> ".

```tablero
titulo: ...
panel: fiscal
unidad: ...

## suma
- item
- item

## si_sube
Texto libre (una o más líneas: se unen en un párrafo).
```

```diagrama
forma: conjuntos        # o "flujo"
contenedor: Estado
parte: Nación
parte: Provincias
```
```

### El parser, por dentro

`_parse_front_matter` corta cada línea del bloque `---` en la clave y el valor con
`str.partition(":")`, que solo separa en el **primer** `:` — así un título como
`"Leer el gráfico: Deuda"` conserva su propio `:` en vez de romperse.

El cuerpo se recorre con `_parse_cuerpo`, que alterna entre markdown simple (párrafos, `### h3`,
listas `- `, notas `> `) y los dos *fences* especiales, en el orden en que aparecen:

| Bloque | Tipo | Campos |
|---|---|---|
| Párrafo | `p` | `texto` |
| `### título` | `h3` | `texto` |
| `- item` | `lista` | `items` |
| `> nota` | `nota` | `texto` |
| ` ```tablero ` | `tablero` | `titulo`, `panel`, `unidad` + secciones `## suma`/`## resta`/`## incluye`/`## excluye`/`## si_sube`/`## si_baja`/`## trampas` |
| ` ```diagrama ` | `diagrama` | `forma` (`conjuntos` o `flujo`) + campos propios de cada forma |

**Un detalle real que se rompió y se corrigió mientras se escribía esta documentación**: el DSL del
diagrama declara su forma con la clave `forma:`, **no** `tipo:`, aunque a simple vista parecería más
natural usar `tipo:`. La razón está anotada en el propio código
([cargador.py:152-156](../webapp/cursos/cargador.py)): `tipo` ya está reservado para el tipo de
**bloque** (`"diagrama"`, el mismo campo que usan `p`/`h3`/`lista`/`tablero` para decir qué son). Si
el DSL también usara `tipo:` para la forma del diagrama, esa línea del contenido pisaría el
`"tipo": "diagrama"` que ya puso el parser. El módulo docstring tenía un ejemplo desactualizado que
todavía mostraba `tipo: conjuntos` — quedaba inconsistente con el propio parser y se corrigió al
preparar esta documentación.

`_parse_diagrama` tiene dos formas:

- **`conjuntos`** — un `contenedor` y una o más `parte` (repetible) — pensado para relaciones de
  inclusión, tipo Venn: "el Estado contiene a la Nación, las provincias y los municipios".
- **`flujo`** — uno o más `nodo` (repetible) y una o más `flecha` (repetible, sintaxis `flecha: A ->
  B`, se parte en `{de, a}`) — pensado para relaciones de caja y flecha.

## Validación al importar

`webapp/cursos/__init__.py` carga el curso y lo valida **al momento del import**:

```python
CURSOS = {"cuentas-publicas": cargar_curso("cuentas-publicas")}
...
_problemas = validar()
if _problemas:
    raise RuntimeError("Contenido de cursos invalido:\n  - " + "\n  - ".join(_problemas))
```

Si algo del contenido está roto, **el servidor no arranca**. Es una decisión deliberada: es preferible
fallar de entrada, ruidoso, que servir un capítulo a medio romper en producción. `validar()` chequea,
entre otras cosas:

- que cada capítulo tenga `slug`, `titulo`, `resumen` y `bloques`, y que el `slug` no esté repetido;
- que el `panel` de un capítulo (si lo tiene) exista en el conjunto real de `data-panel` del sitio
  (`PANELES`, hardcodeado en `__init__.py` a partir de los 12 indicadores) — evita un botón "ver el
  gráfico" que no lleve a ningún lado;
- que un tablero tenga los 6 campos obligatorios (`suma`, `resta`, `incluye`, `excluye`, `si_sube`,
  `si_baja`) y un `panel` válido;
- que un diagrama de `conjuntos` tenga `contenedor` y al menos una `parte`; que uno de `flujo` tenga
  al menos 2 `nodos` y al menos una `flecha`, y que cada flecha referencie nodos que existen.

Para correr esta validación sin levantar el servidor:

```powershell
python -m webapp.cursos
```

## El modelo de progreso en SQLite

Una sola tabla, en `app.db` (ver [AUTENTICACION.md](AUTENTICACION.md) para el resto del esquema):

```sql
CREATE TABLE progreso (
    usuario_id     INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    curso_slug     TEXT NOT NULL,
    capitulo_slug  TEXT NOT NULL,
    completado_en  TEXT NOT NULL,
    PRIMARY KEY (usuario_id, curso_slug, capitulo_slug)
);
```

**Un renglón = un capítulo completado.** La ausencia de fila significa "pendiente" — no hay un estado
explícito "no completado" que mantener. **No hay clave foránea hacia el contenido del curso**, porque
el contenido vive en archivos versionados, no en la base; el `slug` es el único contrato, y por eso
importa tanto que un slug de capítulo nunca cambie una vez publicado (ver la sección de arriba sobre
prefijos de archivo vs. slugs).

Marcar como completado es idempotente (`INSERT ... ON CONFLICT DO NOTHING`): pedir completar el mismo
capítulo dos veces no falla ni duplica nada.

## Endpoints ([webapp/rutas_cursos.py](../webapp/rutas_cursos.py))

| Método | Path | Sesión | Qué hace |
|---|---|---|---|
| GET | `/api/cursos` | no | Lista de cursos con metadatos (`slug`, `titulo`, `n_capitulos`, `minutos`). |
| GET | `/api/cursos/{slug}` | opcional | Curso completo, **todos los capítulos en una sola respuesta**. Si hay sesión, cada capítulo trae `completado` y se agrega un bloque `progreso`. |
| PUT | `/api/cursos/{slug}/capitulos/{cap}/completado` | requerida | Marca el capítulo como completado. `404` si el capítulo no existe en el curso. |
| DELETE | `/api/cursos/{slug}/capitulos/{cap}/completado` | requerida | Lo desmarca. |
| GET | `/api/progreso` | requerida | Progreso del usuario en **todos** los cursos a la vez — lo usa la vista de perfil para las barras de progreso. |

`GET /api/cursos/{slug}` manda el curso entero (capítulos incluidos) de una vez, en lugar de un
endpoint por capítulo. La razón, documentada en el propio código: son del orden de una docena de
capítulos de texto, decenas de KB en total — nada que justifique un request por capítulo — y hace
instantáneo el paso de "Siguiente", que es el gesto central del lector.

`_progreso()` calcula, sobre la marcha, `completados` (lista de slugs), `total`, `porcentaje` y
`siguiente` (el primer capítulo sin completar, o `None` si el curso está terminado) — nada de esto se
guarda precalculado, sale de contar filas de `progreso` en cada request.

## El frontend ([assets/cursos.js](../assets/cursos.js))

**Regla dura del proyecto**: el contenido de los capítulos nunca se inyecta con `innerHTML`. Cada tipo
de bloque (`p`, `h3`, `lista`, `nota`, `formula`, `tablero`, `diagrama`) tiene su propia función que
arma el DOM con `createElement` + `textContent`. Hoy el contenido es 100% de confianza (lo escribimos
nosotros), así que el riesgo real de XSS es bajo — pero mantener esta regla incluso así es la
salvaguarda barata para el día en que el contenido deje de ser 100% propio.

Los diagramas se renderizan como SVG armado a mano en JS, no con una librería de diagramación: son
solo dos formas fijas (`conjuntos`, `flujo`) que nosotros controlamos, así que la complejidad de sumar
D3 o similar no se justifica.

El lector de capítulos muestra un capítulo por pantalla con navegación **Anterior / Siguiente**; avanzar
al siguiente es lo que dispara `PUT .../completado`. El índice de un curso muestra una barra de
progreso y tildes en los capítulos ya hechos.

Con más de un curso, `assets/cursos.js` tiene varias pantallas en cascada dentro de las vistas
`view-cursos`/`view-capitulo`/`view-evaluacion`: el **catálogo** (`pintarCatalogo()`, trae
`GET /api/cursos` + `GET /api/progreso` para mostrar una barra de avance por curso), el **índice de un
curso** (`pintarIndice()`, con un enlace "‹ Cursos" de vuelta al catálogo), el **lector de un
capítulo** y la **evaluación**. Cada una tiene su propia URL real (`/cursos`, `/cursos/<curso>`,
`/cursos/<curso>/capitulos/<cap>`, `/cursos/<curso>/evaluacion` — ver
[FRONTEND.md](FRONTEND.md#routing-del-lado-del-cliente)), sincronizada con `Router.fijarRuta()` en
cada transición; entrar por el nav siempre resetea al catálogo, igual que "Home". El link "Ingresá" que
aparece leyendo sin cuenta guarda la **URL real** del capítulo (`"/cursos/<curso>/capitulos/<cap>"`) en
`sessionStorage`, y tras loguearse `cuenta.js` solo hace `Router.navegar(esa_url)` — el router normal
se encarga de reabrir lo que corresponda, sin que `cuenta.js` necesite saber nada de cursos.

## Evaluaciones y certificados

### Qué es, a nivel de producto

Al terminar los capítulos de un curso, queda disponible una **evaluación**: preguntas de opción
múltiple sobre lo que enseñó el curso. Aprobarla con el umbral que define cada curso (hoy, **70%** en
los tres) habilita descargar un **certificado en PDF** con el nombre completo de la cuenta, el título
del curso y la fecha. Es justamente para esto que el registro pide "nombre completo" y no solo un
alias: es el nombre que va a aparecer en el certificado.

Esto vive en una vista aparte del sitio, **Certificaciones** — separada de "Cursos" en el menú —, un
panel por curso con el estado de cada evaluación (sin rendir, último intento sin aprobar, aprobada) y
el botón de descarga cuando corresponde.

Dos reglas de producto, ambas deliberadas:

- **Hay que terminar el 100% de los capítulos antes de poder ver o rendir la evaluación.** Certificar a
  alguien que no pasó por el contenido vaciaría el certificado de sentido. El servidor lo exige
  (`403` si falta algún capítulo), no solo el frontend.
- **Aprobar es "pegajoso".** Una vez que aprobás, el certificado queda disponible aunque vuelvas a
  rendir y te vaya peor esa segunda vez — rendir de nuevo no te lo puede quitar. El **puntaje** que se
  muestra sí es el del último intento (ver el esquema, más abajo).

### El contenido: preguntas en Markdown, igual que los capítulos

Cada curso que tiene evaluación (hoy, los tres) trae un archivo reservado `_evaluacion.md` en su
carpeta de contenido, con el mismo trato que `_curso.md`: no es un capítulo, `cargar_curso()` lo excluye
explícitamente de la lista de capítulos. Front matter con el umbral de aprobación, cuerpo con una o más
preguntas usando un fence nuevo, `pregunta`:

```markdown
---
aprobacion: 70
---

```pregunta
enunciado: ¿Qué mide la deuda pública bruta?
opcion: Lo que debe el Tesoro, sin descontar activos
opcion: Lo que debe toda la economía al exterior
opcion: El resultado fiscal acumulado
correcta: 0
```
```

`opcion` es repetible y se acumula en una lista, en el orden en que aparece — ese orden es el que
indexa `correcta` (0 = la primera opción escrita). Se usa el **índice**, nunca el texto de la
respuesta, para no tener que comparar strings al corregir. El parser (`_parse_pregunta` en
[cargador.py](../webapp/cursos/cargador.py)) es la misma idea que `_parse_diagrama`: líneas
`clave: valor`, con una clave (`opcion`) tratada como repetible.

`webapp/cursos/__init__.py` exige, al validar, que **todo curso tenga una evaluación** con al menos 5
preguntas, cada una con `enunciado`, al menos 2 `opcion` y una `correcta` que sea un índice válido
dentro de sus propias opciones — un curso sin evaluación, o con una pregunta mal armada, frena el
arranque del servidor igual que un tablero incompleto.

### El esquema en SQLite

Una tabla más en `app.db`, junto a `progreso`:

```sql
CREATE TABLE evaluaciones (
    usuario_id     INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    curso_slug     TEXT NOT NULL,
    puntaje        INTEGER NOT NULL,   -- % de respuestas correctas del ULTIMO intento
    aprobado       INTEGER NOT NULL,   -- 0/1, pegajoso: nunca vuelve a 0 una vez en 1
    intentos       INTEGER NOT NULL DEFAULT 1,
    completado_en  TEXT NOT NULL,
    PRIMARY KEY (usuario_id, curso_slug)
);
```

Un renglón por `(usuario, curso)` — no uno por intento. `_registrar_intento()` en
[rutas_cursos.py](../webapp/rutas_cursos.py) hace el `UPDATE` a mano en vez de un `UPSERT` de SQL
directo, porque la regla "pegajosa" no es un simple reemplazo: `aprobado` nuevo es
`aprobado_de_este_intento OR aprobado_que_ya_tenía`, mientras que `puntaje` sí se pisa siempre con el
del intento actual.

### Endpoints

| Método | Path | Sesión | Qué hace |
|---|---|---|---|
| GET | `/api/cursos/{slug}/evaluacion` | requerida + curso 100% completo | Las preguntas **sin** el campo `correcta` (nunca se manda la respuesta al cliente), más el estado del usuario en esa evaluación. `403` si falta algún capítulo. |
| POST | `/api/cursos/{slug}/evaluacion` | requerida + curso 100% completo | Body `{"respuestas": [0, 2, 1, ...]}` (un índice por pregunta, mismo orden). Corrige **en el servidor**, guarda el intento, devuelve `{puntaje, correctas, total, aprobado, umbral}`. `400` si faltan respuestas o alguna está fuera de rango. |
| GET | `/api/cursos/{slug}/certificado` | requerida + evaluación aprobada | El PDF, con `Content-Disposition: attachment`. `403` si todavía no aprobaste. |
| GET | `/api/certificaciones` | requerida | Un resumen por curso (progreso, si está 100% completo, estado de la evaluación) — alimenta la vista "Certificaciones". |

El `GET /cursos/{slug}` (el mismo que trae el curso completo para el lector) también suma, si hay
sesión y el curso ya está 100% completo, un bloque `evaluacion` con el estado — así el índice del curso
puede ofrecer "Rendir evaluación" o "Descargar certificado" sin pedir nada aparte.

### El PDF ([webapp/certificados.py](../webapp/certificados.py))

Genera el certificado con **fpdf2**, la única dependencia nueva de todo el proyecto agregada para esto.
No es una excepción a "evitar dependencias": a diferencia de un hash de contraseña (stdlib) o un
diagrama (SVG a mano, XML plano), el formato PDF es binario y reimplementarlo no tiene un atajo
razonable — es la misma lógica por la que el proyecto sí usa FastAPI en vez de escribir un servidor
HTTP a mano. Las fuentes "core" de fpdf2 (Helvetica, Times) cubren los acentos del español sin
necesidad de empaquetar una tipografía.

El nombre que aparece en el certificado es siempre `usuarios.nombre_completo` tal como está en la
base — el campo que el registro pide justamente para esto (ver
[AUTENTICACION.md](AUTENTICACION.md)). El PDF lleva, a propósito, la aclaración *"No constituye un
título ni una certificación oficial"*: es un certificado de finalización de un curso propio del sitio,
no una acreditación formal.

### El frontend

Dos archivos nuevos/tocados:

- **[assets/cursos.js](../assets/cursos.js)** suma la pantalla de examen (`abrirEvaluacion()` /
  `pintarEvaluacion()` / `pintarResultado()`), alcanzable en `/cursos/<curso>/evaluacion` — la misma
  vía de eventos (`ruta-cursos`, con `evaluacion:true`) que ya resolvía curso/capítulo. El índice de un
  curso 100% completo cambia su botón principal de "Continuar donde quedaste" a "Rendir evaluación" o
  "Descargar certificado", según corresponda.
- **[assets/certificaciones.js](../assets/certificaciones.js)** — archivo nuevo, la vista
  "Certificaciones" en sí: un panel por curso con su estado, escuchando el evento `ruta-certificaciones`
  que dispara el router al entrar a `/certificaciones`. No duplica la lógica de rendir el examen (esa
  vive en `cursos.js`, que ya tiene el contenido del curso cargado); sus botones solo navegan a
  `/cursos/<curso>/evaluacion` o descargan el PDF.

**Descargar el PDF es un `fetch` + blob, no un `<a href>` directo** (repetido en los dos archivos, sin
compartir una función: es una utilidad chica y genérica que no es dominio de ninguno de los dos). La
razón: un link directo no manda la cookie de sesión de la misma forma confiable que `fetch` con
`credentials:"same-origin"`, y un `fetch` permite detectar un `403` (evaluación no aprobada, por
ejemplo por una carrera de estados) y avisar en el botón en vez de descargar una página de error como
si fuera el PDF.

## Cómo agregar contenido

Un curso nuevo: una carpeta en `webapp/cursos/contenido/<slug>/` con un `_curso.md` (metadatos, sin
cuerpo), un `_evaluacion.md` (obligatorio — ver arriba) y sumarla al diccionario `CURSOS` en
`webapp/cursos/__init__.py`. Un capítulo nuevo dentro de un curso existente: un archivo `NN-nombre.md`
más en esa carpeta, con el formato de arriba. En todos los casos, correr `python -m webapp.cursos`
antes de levantar el servidor para confirmar que el contenido pasa la validación.
