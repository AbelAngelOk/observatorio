# La webapp: stack y arquitectura

Este documento es la puerta de entrada a la mitad del proyecto que **no** es el observatorio de datos
(eso está en [ARQUITECTURA.md](ARQUITECTURA.md), [DATOS.md](DATOS.md) y [PIPELINES.md](PIPELINES.md)).
Acá se explica la capa que se agregó encima: **cuentas de usuario** y **cursos**, y las decisiones de
stack detrás de las dos.

## Qué es, a nivel de producto

Hasta acá el sitio era "mirar gráficos". La webapp le agrega una segunda cosa: **aprender a leerlos**.
Un usuario se registra, hace un curso corto por capítulos que le enseña qué significa cada gráfico del
observatorio, y el sitio recuerda qué capítulos ya completó — para que pueda cerrar la pestaña y
retomar después sin perder el lugar.

Las tres piezas nuevas:

- **Cuentas de usuario** — registro, login, perfil, cambio de contraseña. Documentado en
  [AUTENTICACION.md](AUTENTICACION.md).
- **Cursos** — tres cursos, uno por cada grupo temático del menú de indicadores (*Cuentas públicas*,
  *Deuda y reservas*, *Sector externo*), enseñan a leer los gráficos de su grupo. Documentado en
  [CURSOS.md](CURSOS.md).
- **Certificaciones** — cada curso termina en una evaluación de opción múltiple; aprobarla habilita un
  certificado en PDF con el nombre de la cuenta. Vive en una vista aparte del menú, "Certificaciones".
  Documentado junto con los cursos, en [CURSOS.md](CURSOS.md#evaluaciones-y-certificados).

Ninguna toca el observatorio de datos: los 12 paneles siguen leyendo `data/*.json` como siempre, y la
ingesta diaria no sabe que la webapp existe.

## El stack, y por qué cada pieza

| Capa | Elección | Por qué |
|---|---|---|
| Backend | **FastAPI + uvicorn** | Tipado de request/response con Pydantic sin escribir validación a mano, `/docs` autogenerada, y permite mezclar handlers `async def` (I/O) con `def` normales (CPU) — necesario porque el hashing de contraseñas bloquea el hilo (ver [AUTENTICACION.md](AUTENTICACION.md#por-qué-scrypt-y-no-bcrypt)). |
| Persistencia | **SQLite vía `sqlite3` de la stdlib, sin ORM** | El resto del proyecto ya es SQLite crudo (`observatorio.db`); sumar SQLAlchemy hubiera sido una capa de abstracción para ~5 tablas con queries simples. Un sitio de nicho no necesita Postgres. |
| Contraseñas | **`hashlib.scrypt`, stdlib** | Cero dependencias de criptografía de terceros que auditar (nada de `bcrypt`/`passlib`). Detalle completo en [AUTENTICACION.md](AUTENTICACION.md). |
| Sesiones | **Token opaco en tabla, no JWT** | Permite invalidar una sesión de verdad (`DELETE` de una fila) sin mantener una blocklist, y no hay clave de firma que administrar. |
| Frontend | **JavaScript vanilla, sin framework, sin build step** | El sitio ya era así — un solo `index.html` con Chart.js por CDN. Meter React/Vue para dos pantallas de login y un lector de capítulos hubiera significado inventar un pipeline de build para un feature acotado. Detalle en [FRONTEND.md](FRONTEND.md). |
| Contenido del curso | **Markdown versionado, no base de datos** | Es prosa larga que se edita como texto. Detalle en [CURSOS.md](CURSOS.md). |
| Certificado en PDF | **fpdf2** | La única dependencia nueva agregada después del arranque inicial. A diferencia de un hash (stdlib) o un diagrama (SVG a mano), el PDF es un formato binario sin un atajo razonable para reimplementarlo — mismo criterio por el que el proyecto usa FastAPI en vez de un servidor HTTP escrito a mano. Detalle en [CURSOS.md](CURSOS.md#el-pdf-webappcertificadospy). |

Todo esto agregó pocas dependencias pesadas: `requirements.txt` suma `fastapi`, `uvicorn` y `fpdf2`
—las tres justificadas por lo mismo, evitar reimplementar algo que no tiene un atajo razonable—, más
`fonttools`, que arrastra `fpdf2` como dependencia propia.

## Dos bases de datos, no una

```
observatorio.db   →  series, observaciones, ingestas.  Se commitea. Se puede borrar y se regenera.
app.db            →  usuarios, sesiones, progreso.      NUNCA se commitea. Si se borra, se pierden cuentas reales.
```

La separación no es un capricho: el workflow de ingesta hace `git add observatorio.db` todos los días.
Si los hashes de contraseña vivieran en esa base, terminarían publicados en el repo. `app.db` está en
`.gitignore`, no la toca `init_db.py`, y ningún pipeline sabe que existe. La tabla comparativa completa
está en [EJECUCION.md](EJECUCION.md#las-dos-bases-de-datos).

Ambas usan el mismo motor (SQLite) pero con filosofías de escritura opuestas: `observatorio.db` es
*append-only por vintage* (nunca se pisa una fila — ver [ARQUITECTURA.md](ARQUITECTURA.md)); `app.db`
es una base transaccional normal, con `UPDATE` y `DELETE` sin culpa, porque una contraseña vieja o una
sesión cerrada no tienen ningún valor histórico que preservar.

## Mapa de archivos de la webapp

| Archivo | Qué es |
|---|---|
| [app.py](../app.py) | El servidor. Monta la API y sirve `index.html`, `data/` y `assets/` — **y nada más** (ver más abajo). |
| [webapp/db.py](../webapp/db.py) | Conexión a `app.db`: ruta absoluta, modo WAL, creación idempotente. |
| [webapp/auth.py](../webapp/auth.py) | Hashing, sesiones, fuerza bruta. Sin conocimiento de HTTP. |
| [webapp/rutas_auth.py](../webapp/rutas_auth.py) | Los 5 endpoints de `/api/auth/*`, cookies, códigos de error. |
| [webapp/cursos/](../webapp/cursos/) | El registro de cursos, el parser de Markdown y el contenido. |
| [webapp/rutas_cursos.py](../webapp/rutas_cursos.py) | Endpoints de `/api/cursos/*`, `/api/progreso`, `/api/certificaciones`. |
| [webapp/certificados.py](../webapp/certificados.py) | Arma el PDF del certificado con fpdf2. |
| [webapp/schema_app.sql](../webapp/schema_app.sql) | El esquema de `app.db`. |
| [assets/cuenta.js](../assets/cuenta.js) | UI de registro, login y perfil. |
| [assets/cursos.js](../assets/cursos.js) | UI del índice de curso, el lector de capítulos, la evaluación y los diagramas SVG. |
| [assets/certificaciones.js](../assets/certificaciones.js) | UI de la vista "Certificaciones": estado y descarga por curso. |

## El camino de un request

```
navegador
   │  GET /                          → FileResponse(index.html)
   │  GET /cursos/deuda-reservas     ┐
   │  GET /indicadores/fiscal        │→ fallback: mismo index.html (200) -- lo resuelve
   │  GET /perfil                    │  el router de JS, no el servidor (ver FRONTEND.md)
   │  GET /app.db, /cualquier-otra   ┘
   │  GET /data/fiscal.json          → StaticFiles (solo lee data/)
   │  GET /assets/cursos.js          → StaticFiles (solo lee assets/)
   │
   │  POST /api/auth/login           ┐
   │  GET  /api/auth/yo              │
   │  POST /api/cursos/.../completado│→ FastAPI router → webapp/db.get_conn() → app.db
   └  ...                            ┘   (una conexión SQLite nueva por request)
```

**Decisión de seguridad concreta**: `app.py` **no** monta la raíz del proyecto como estáticos.
`StaticFiles(directory=RAIZ)` serviría por HTTP, a cualquiera, `app.db` (usuarios y hashes),
`observatorio.db`, y todo el código fuente. Solo quedan expuestos `/data` y `/assets`; cualquier otra
ruta —incluida `/app.db` o `/webapp/auth.py`— cae en el *fallback* de rutas del cliente (ver
[FRONTEND.md](FRONTEND.md#routing-del-lado-del-cliente)) y devuelve `200` con el **HTML de
`index.html`**, nunca el archivo pedido. Verificado: pedir `/app.db` por HTTP trae el shell del sitio,
no los bytes de la base.

## Qué no tiene, todavía

- **Recuperación de contraseña por email** — las tablas están listas (`tokens_reset`), falta el envío
  de mail (necesita SMTP).
- **2FA.**
- **Roles o permisos** — toda cuenta es igual a cualquier otra.
- **Tema oscuro** — el sitio tiene un único tema claro (ver [FRONTEND.md](FRONTEND.md)).
