# Frontend: decisiones técnicas

Este documento cubre las decisiones de *cómo está armado* el frontend al agregar cuentas y cursos. La
parte de gráficos (Chart.js, `lineaTemporal()`, cómputo de stats) ya está documentada en
[ARQUITECTURA.md](ARQUITECTURA.md#el-front) y no se repite acá.

## Sin framework, sin build step

Todo el frontend es JavaScript sin transpilar, cargado con `<script>` sueltos. No hay React, Vue,
webpack, ni `npm run build`. La razón es de continuidad, no de principio: el sitio **ya era así** —
un `index.html` de una sola pieza con Chart.js por CDN — antes de que existieran cuentas o cursos.
Meter un framework para dos pantallas de login y un lector de capítulos habría significado inventar un
pipeline de build nuevo para un feature acotado, a cambio de un beneficio (gestión de estado
declarativa, componentes) que este tamaño de UI no necesita. La decisión se revisa si el frontend
crece mucho más — hoy no se justifica.

## Cómo se dividió el código

| Dónde | Qué tiene |
|---|---|
| [index.html](../index.html) | El núcleo original: markup, CSS y el `<script>` de gráficos + routing (~2000 líneas, todo inline). |
| [assets/cuenta.js](../assets/cuenta.js) | Todo lo nuevo de cuentas: login, registro, perfil. |
| [assets/cursos.js](../assets/cursos.js) | Índice de cursos, lector de capítulos, diagramas SVG y la evaluación de opción múltiple. |
| [assets/certificaciones.js](../assets/certificaciones.js) | La vista "Certificaciones": estado por curso y descarga del PDF. |

El criterio para no seguir haciendo crecer el archivo gigante fue simple: **el código nuevo va en
`assets/*.js`**, y lo que se toca de `index.html` se limita al `<nav>`, las secciones `<section
class="view">` nuevas y una pequeña API de routing que se explica abajo. El resto del archivo
original —gráficos, stats, toggle de presidencias— no se movió.

## Routing del lado del cliente

El sitio tiene URLs reales — `/cursos`, `/indicadores/fiscal`, `/cursos/deuda-reservas/capitulos/leer-reservas`
— que sobreviven a un F5 y andan con atrás/adelante del navegador. No hay `location.hash`: se usa la
History API (`pushState`/`popstate`), y el servidor coopera con un *fallback* (ver
[app.py](../app.py)): cualquier `GET` que no matchea `/api/*`, `/data/*` ni `/assets/*` devuelve el
mismo `index.html`, y es JS, no el servidor, quien decide qué vista corresponde a esa URL.

```js
var VISTAS = { home:"view-home", about:"view-about", indicadores:"view-indicadores",
               auth:"view-auth", perfil:"view-perfil",
               cursos:"view-cursos", capitulo:"view-capitulo",
               evaluacion:"view-evaluacion", certificaciones:"view-certificaciones" };

function mostrarVista(nombre){
  document.querySelectorAll(".view").forEach(v => v.classList.remove("visible"));
  document.getElementById(VISTAS[nombre] || "view-home").classList.add("visible");
  ...
}
```

Cada vista sigue siendo un `<section class="view" id="view-...">`; `mostrarVista()` solo agrega/saca
la clase `.visible` — de eso no cambió nada. Lo que se agregó es la capa que traduce una URL a una
vista, en la misma IIFE de `index.html` ([index.html:1192](../index.html)):

```js
function analizarRuta(path){ ... }        // "/cursos/x/capitulos/y" -> {vista, curso, capitulo}
function render(path){ ... }              // analiza, llama mostrarVista(), dispara eventos
function navegar(path, opciones){ ... }    // pushState (o replaceState) + render()
function fijarRuta(path){ ... }            // solo sincroniza la URL, sin re-renderizar
```

Las rutas hoy:

| Ruta | Vista | Quién la resuelve |
|---|---|---|
| `/` | home | este router, directo |
| `/quienes-somos` | about | este router, directo |
| `/indicadores[/<panel>]` | indicadores | este router, directo (`seleccionarPanel()`) |
| `/cuenta` | auth | este router, directo |
| `/cursos` | cursos (catálogo) | `assets/cursos.js`, vía evento |
| `/cursos/<curso>` | cursos (índice) | `assets/cursos.js`, vía evento |
| `/cursos/<curso>/capitulos/<cap>` | capitulo | `assets/cursos.js`, vía evento |
| `/cursos/<curso>/evaluacion` | evaluacion | `assets/cursos.js`, vía evento |
| `/certificaciones` | certificaciones | `assets/certificaciones.js`, vía evento |
| `/perfil` | perfil | `assets/cuenta.js`, vía evento |

**Por qué dos formas de tocar la URL** (`navegar` vs. `fijarRuta`): `cursos`/`capitulo`/`evaluacion`,
`certificaciones` y `perfil` guardan su propio estado (qué curso, qué capítulo, si hay sesión) en
`assets/cursos.js`, `assets/certificaciones.js` y `assets/cuenta.js`, no en este router. Cuando esos
módulos deciden por su cuenta qué mostrar (el usuario hizo clic en un capítulo dentro del lector),
solo necesitan que la barra de direcciones quede al día — `fijarRuta()`, sin disparar un re-render.
Cuando la navegación viene de afuera (un clic en el nav, atrás/adelante, un link pegado en el
navegador), el router **no sabe** qué hay en esa URL: reparte la pregunta con un evento y deja que el
módulo dueño de ese estado responda:

```js
document.dispatchEvent(new CustomEvent("ruta-cursos",
  { detail: { curso, capitulo, evaluacion } }));   // cursos, capitulo Y evaluacion caen aca
document.dispatchEvent(new CustomEvent("ruta-certificaciones"));
document.dispatchEvent(new CustomEvent("ruta-perfil"));   // perfil depende de si hay sesion
```

`assets/cursos.js` escucha `"ruta-cursos"` para abrir el catálogo, un curso, un capítulo o la
evaluación (el mismo evento cubre los tres, con `evaluacion:true` cuando la URL termina en
`/evaluacion`) — y de paso ya no necesita cargar nada al arrancar: si nadie visita `/cursos`, ese
archivo no pide datos. `assets/certificaciones.js` escucha `"ruta-certificaciones"`: pide
`GET /api/certificaciones` directo (sin esperar ningún chequeo de sesión propio, porque el servidor ya
decide por la cookie) y, si falla, redirige a `/cuenta`. `assets/cuenta.js` escucha `"ruta-perfil"`,
pero no puede resolverlo de inmediato en la primera carga: todavía no sabe si hay sesión (esa
respuesta es asíncrona). Guarda el pedido en una bandera y lo resuelve en cuanto el chequeo de sesión
contesta — si no hay usuario, redirige a `/cuenta` con `{reemplazar:true}` (`replaceState`, para que
"atrás" no vuelva a la URL sin permiso).

`certificaciones` y `perfil` resuelven el "¿hay sesión?" de dos formas distintas, y las dos son
deliberadas: `certificaciones.js` deja que el propio `fetch` a `/api/certificaciones` conteste (si da
`401`, no hay sesión, sin importar el estado local); `cuenta.js`, para `/perfil`, no tiene un fetch
equivalente — depende del objeto `usuario` que ya tiene cacheado en memoria, así que sí necesita
esperar a que ese caché se resuelva antes de poder contestar.

### El gotcha de `window.Router`

El listener que conecta los botones `[data-view]` con la navegación se engancha **una sola vez**, al
cargar la página:

```js
document.querySelectorAll("[data-view]").forEach(function(btn){
  ...
  btn.addEventListener("click", function(){ navegar(RUTA_VISTA[btn.dataset.view] || "/"); });
});
```

Cualquier botón que `assets/cuenta.js`, `assets/cursos.js` o `assets/certificaciones.js` inyecten
**después** de ese momento —el nombre del usuario en el header, "continuar donde quedaste", los
botones "ver el gráfico" de un tablero, "descargar certificado"— no tiene ese listener. Por eso
`index.html` expone una API mínima, después de armar todo lo demás ([index.html:1356](../index.html)):

```js
window.Router = { mostrarVista, seleccionarPanel, navegar, fijarRuta };
```

Los tres módulos nuevos navegan llamando `Router.navegar("/perfil")` o `Router.fijarRuta(...)`
directamente, en vez de depender del listener automático. Es aditivo a propósito: nada del código de
gráficos lee `window.Router`, así que agregarlo no le cambió el comportamiento a lo que ya funcionaba.

## Scripts clásicos, no ES modules

```html
<script src="assets/cuenta.js"></script>
<script src="assets/cursos.js"></script>
<script src="assets/certificaciones.js"></script>
```

Sin `type="module"` y sin `defer`, a propósito. Dos razones:

1. **Scope global compartido.** El `<script>` principal de `index.html` declara sus helpers (incluido
   `window.Router`) en el scope global de la página. Con `type="module"`, cada archivo tiene su propio
   scope de módulo — `assets/cuenta.js` dejaría de ver esos helpers sin un `import` explícito, que a
   su vez exigiría que `index.html` los exportara como módulo también.
2. **Orden de carga y `Chart.register()`.** `index.html` ya tiene, en el código de gráficos, un
   registro de un plugin de Chart.js que depende de correr en un momento preciso del ciclo de carga
   (ver [ARQUITECTURA.md](ARQUITECTURA.md#el-front)). Los módulos ES difieren su ejecución hasta
   después del parseo del documento; scripts clásicos sin `defer` corren en el orden en que aparecen,
   que es lo que este timing necesita.

`window.ApiCuenta` (en `cuenta.js`) es, en el mismo espíritu, la única superficie que `cursos.js` usa
de `cuenta.js` — un wrapper de `fetch` con `credentials:"same-origin"` para llamar a `/api/auth/*`.

## CSS: variables de tema

```css
:root{
  /* Tema claro, beige como eje. */
  --ink:#efe3d3;        /* fondo de página */
  --panel:#fcfbf6;      /* tarjetas */
  --panel-alt:#e7d8c2;  /* hover / menús / recuadros */
  --paper:#27384a;      /* texto principal (navy) */
  --muted:#5b6b7b;      /* texto secundario */
  --gold:#4f6d89;       /* acento */
  --teal:#4f6d89;       /* positivo */
  --brick:#a2503a;      /* negativo */
  --line: / --line-strong:  /* bordes */
}
```

Un único tema claro, sin modo oscuro. No es una limitación técnica de las custom properties (agregar
un bloque `@media (prefers-color-scheme: dark)` que redefina estas variables sería mecánico) — es que
nadie lo pidió, y hacerlo bien (elegir una paleta oscura que siga leyéndose igual de bien, no solo
invertir colores) es trabajo real que no se justificaba para este alcance. Los componentes nuevos
(`.tab`, `.form`, `.ficha`, `.tablero`, `.bloque-diagrama`) usan las mismas variables que ya usaba el
resto del sitio, así que heredan el tema sin CSS adicional de paleta.

## Navegación agrupada

El dropdown de indicadores pasó de 11 ítems planos y numerados a **3 grupos temáticos**, con
encabezados que son `<div>` en vez de `<button>` — a propósito, para que no hereden el `:hover` de
`.idx-item` y no parezca que se pueden clickear ([index.html:458-459](../index.html)):

```html
<div class="idx-group">Deuda y reservas</div>
<button class="idx-item" data-panel="deuda">Deuda pública bruta</button>
...
<div class="idx-group">Cuentas públicas</div>
<button class="idx-item" data-panel="fiscal">Resultado fiscal</button>
...
<div class="idx-group">Sector externo</div>
<button class="idx-item" data-panel="externo">Resultado externo</button>
```

El header sumó dos entradas: el botón **Cursos** (`data-view="cursos"`) y `#auth-slot`, un `<div>`
vacío que `assets/cuenta.js` puebla en runtime según haya sesión o no (nombre del usuario + menú, o
botón "Ingresar").

## SVG a mano para los diagramas del curso

Los diagramas de `assets/cursos.js` (relaciones de "conjuntos" o "flujo", ver
[CURSOS.md](CURSOS.md#arquitectura-de-contenido-markdown-no-base-de-datos-ni-python)) se dibujan
armando elementos SVG directamente en JS, sin librería de diagramación (D3, mermaid, etc.). Son
exactamente dos formas fijas, controladas enteramente por nosotros — la complejidad de sumar una
librería para eso no se paga.

## Nunca `innerHTML` de contenido dinámico

Regla del proyecto, aplicada de punta a punta en `cursos.js`: el contenido que viene del servidor (los
bloques de un capítulo) se arma con `createElement` + `textContent`, nunca con `innerHTML`. Hoy el
contenido es 100% de confianza (lo escribimos nosotros en los `.md`), así que no hay un vector de XSS
real todavía — pero mantener la regla es la salvaguarda barata para el día en que eso deje de ser
cierto.

## Qué no tiene el frontend

- **Gestión de estado tipo Redux/Zustand** — no hace falta: cada IIFE (la de gráficos, la de cuentas,
  la de cursos) mantiene su propio estado en variables de módulo.
- **Tests automatizados de UI** — se verificó manualmente en el navegador durante el desarrollo
  (incluido un arnés de Chrome headless para regresión de los 12 gráficos); no hay una suite
  persistente en el repo.
- **Diseño responsive verificado a fondo** — no se probó exhaustivamente en pantallas chicas.
- **Título de pestaña por vista** — `document.title` queda fijo en todas las rutas; compartir un link
  no cambia lo que se ve en la pestaña o en el historial del navegador.
- **Página 404 propia** — una URL que no matchea ningún patrón conocido (`/algo-inventado`) cae al
  fallback igual que cualquier otra y el router la resuelve como Home, en vez de mostrar un aviso de
  "no encontrado".
