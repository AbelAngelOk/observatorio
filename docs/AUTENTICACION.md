# Cuentas: registro, login y SQLite

## Qué puede hacer un usuario, a nivel de producto

- **Registrarse** con email, nombre completo y contraseña. Queda con sesión iniciada al toque —
  no hay verificación de email por ahora.
- **Iniciar sesión** y quedar reconocido en el sitio durante 30 días (no hace falta loguearse cada vez
  que se vuelve).
- **Ver su perfil**: nombre, email, y una barra de progreso por cada curso que empezó.
- **Cambiar su contraseña.**
- **Cerrar sesión.**
- **Leer el curso sin cuenta.** El login solo hace falta para que el sitio recuerde qué capítulos ya
  completó (ver [CURSOS.md](CURSOS.md)).

Lo que **no** existe todavía: recuperar la contraseña por email (la tabla `tokens_reset` está
preparada, falta el envío de mail — necesita SMTP), verificación de email, y borrar la propia cuenta.

## El modelo de datos

`app.db` tiene 5 tablas ([webapp/schema_app.sql](../webapp/schema_app.sql)):

```sql
usuarios        (id, email UNIQUE COLLATE NOCASE, nombre_completo, password_hash, creado_en, actualizado_en)
sesiones        (token_hash PRIMARY KEY, usuario_id, creada_en, expira_en)
progreso        (usuario_id, curso_slug, capitulo_slug, completado_en)  -- PK compuesta
intentos_login  (email, cuando)
tokens_reset    (token PRIMARY KEY, usuario_id, creado_en, expira_en, usado_en)  -- diseñada, sin usar
```

Dos detalles que no son obvios leyendo solo los nombres de columna:

- **`email` es `COLLATE NOCASE`** — `Ana@mail.com` y `ana@mail.com` son la misma cuenta, porque nadie
  espera que no lo sean.
- **`sesiones` no guarda el token, guarda su hash** (`token_hash`). Ver más abajo.

## Contraseñas

### Por qué scrypt y no bcrypt

El hashing usa `hashlib.scrypt`, de la librería estándar de Python — no `bcrypt` ni `passlib`. Es una
decisión de superficie de dependencias: scrypt está en la stdlib desde Python 3.6 y ya está verificado
que funciona en este entorno, así que cero paquetes nuevos que auditar o que puedan dejar de mantenerse.
Es además una función de derivación moderna, resistente a ataques por GPU (a diferencia de un hash
rápido como SHA-256 solo).

### Parámetros y formato ([webapp/auth.py](../webapp/auth.py))

```python
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1     # n=16384: ~50-100ms por hash
DKLEN = 32
```

`n=2**14` es el punto de equilibrio entre seguridad y latencia: suficientemente caro como para que
probar contraseñas por fuerza bruta sea costoso, suficientemente rápido como para no notarse en un
login normal.

El hash se guarda en un **formato autodescriptivo**:

```
scrypt$16384$8$1$<salt en base64>$<hash en base64>
```

Los propios parámetros viajan con el hash. Eso permite subir `n` en el futuro (hardware más rápido =
`n` más alto) sin invalidar los hashes ya guardados — `verificar()` lee los parámetros de cada hash
individual, no usa los de la constante actual.

La verificación (`auth.verificar`) usa `hmac.compare_digest`, comparación en **tiempo constante**:
comparar con `==` filtra información porque Python corta la comparación en el primer byte que no
coincide, y ese timing es medible desde afuera.

### El ataque de timing sobre el login

Hay una segunda fuga de timing, más sutil, que el proyecto mitiga explícitamente. Sin cuidado, un
intento de login con un email que **no existe** responde al instante (no hay nada que hashear), y un
intento con el email correcto pero la clave mal responde ~50-100ms después (el tiempo que tarda
`scrypt`). Esa diferencia deja adivinar, midiendo el tiempo de respuesta, qué emails están
registrados — sin necesitar el mensaje de error.

La mitigación es un hash "de descarte" calculado una vez al importar el módulo
(`_HASH_DUMMY = hashear("contraseña que nadie usa jamás")`). Cuando el email no existe, el código llama
`auth.quemar_tiempo()`, que verifica igual contra ese hash dummy — así el camino "no existe" tarda lo
mismo que el camino "existe pero la clave está mal". El mensaje de error, además, es idéntico en los
dos casos: `"Email o contraseña incorrectos."`.

## Sesiones: por qué token opaco y no JWT

La sesión es un token aleatorio de 256 bits (`secrets.token_urlsafe(32)`), no un JWT firmado. Dos
razones concretas:

1. **Cerrar sesión de verdad.** Con JWT, "cerrar sesión" no invalida el token — sigue siendo válido
   hasta que expira, a menos que se mantenga una lista negra en el servidor (que es, en la práctica,
   reinventar esta misma tabla). Acá, `logout` hace un `DELETE` de la fila y el token deja de servir
   en el próximo request.
2. **No hay clave de firma que custodiar.** Un JWT firmado necesita un secreto que, si se filtra,
   permite forjar sesiones de cualquier usuario. Un token opaco no tiene ese punto único de falla.

**La base no guarda el token, guarda `sha256(token)` en hex** (columna `token_hash`). Si alguien
consigue una copia de `app.db`, no se lleva sesiones utilizables: no puede invertir el sha256 para
recuperar el token que hay que mandar en la cookie. Acá alcanza con sha256 sin salt (a diferencia de
las contraseñas) porque el token tiene 256 bits de entropía real generados por `secrets` — no hay
diccionario de tokens humanos que probar, que es justamente el ataque contra el que sí hace falta
protegerse en las contraseñas.

La sesión dura **30 días fijos desde el login** (`DIAS_SESION = 30`). Importante: no se renueva sola
con el uso — `usuario_de_token()` solo *lee* `expira_en`, nunca la extiende. Un usuario activo todos
los días igual tiene que volver a loguearse a los 30 días del último login.

### La cookie

```python
resp.set_cookie(auth.COOKIE, token,
    max_age=auth.DIAS_SESION * 24 * 3600,
    httponly=True,      # el JS de la página no puede leerla: frena robo por XSS
    samesite="lax",     # no viaja en requests cross-site: frena CSRF básico
    secure=COOKIE_SEGURA,
    path="/")
```

`COOKIE_SEGURA` sale de la variable de entorno `OBS_COOKIE_SECURE` (`"0"` por defecto). El motivo de
que no esté prendida por defecto es una trampa real: una cookie `Secure` sobre `http://localhost` el
navegador la descarta **en silencio** — no hay ningún error, ni en la consola ni en el servidor, el
síntoma es simplemente "el login no hace nada". En producción, detrás de HTTPS, se activa con
`OBS_COOKIE_SECURE=1`. Más detalle de este síntoma en
[EJECUCION.md](EJECUCION.md#cuando-algo-falla).

## Fuerza bruta

La tabla `intentos_login` guarda un renglón por intento de login fallido (email + timestamp). El
límite: **8 fallos en 15 minutos** por email (`MAX_INTENTOS = 8`, `VENTANA_MIN = 15`) → `429 Too Many
Requests`. Un login exitoso limpia el contador de ese email (`limpiar_intentos`). El housekeeping de
arranque (`purgar_vencidas`, llamado desde el `lifespan` de `app.py`) borra intentos de más de un día
y sesiones ya vencidas.

**Límite honesto**: el freno es por email, no por IP. Un atacante que rota emails no lo dispara; lo
que sí evita es que alguien pruebe miles de contraseñas contra una cuenta puntual.

## Al cambiar la contraseña

`cambiar_password()` hace dos cosas en la misma transacción: actualiza el hash **y** borra todas las
sesiones de ese usuario (`DELETE FROM sesiones WHERE usuario_id = ?`). Es la respuesta a "alguien
tiene mi contraseña vieja y una sesión abierta en otro dispositivo": cambiar la clave lo saca. El
endpoint `POST /api/auth/password` le da inmediatamente una sesión nueva al navegador que hizo el
cambio, para que ese cambio de clave no expulse también a quien la está cambiando.

## Endpoints ([webapp/rutas_auth.py](../webapp/rutas_auth.py))

| Método | Path | Body | Respuesta | Notas |
|---|---|---|---|---|
| POST | `/api/auth/registro` | `{email, nombre_completo, password}` | `201` + cookie | `409` si el email ya existe. `400` si falla `validar_registro` (email inválido, nombre <2 caracteres, contraseña <8). |
| POST | `/api/auth/login` | `{email, password}` | `200` + cookie | `401` genérico (email o clave mal, mismo mensaje y mismo tiempo). `429` si está bloqueado por fuerza bruta. |
| POST | `/api/auth/logout` | — | `204` | Borra la sesión en base y la cookie. |
| GET | `/api/auth/yo` | — | `200` `{id, email, nombre_completo}` | `401` sin sesión válida. |
| POST | `/api/auth/password` | `{actual, nueva}` | `204` + cookie nueva | `400` si `actual` no coincide o `nueva` <8 caracteres. Cierra las demás sesiones. |

Ningún endpoint devuelve nunca el hash de la contraseña: `_publico()` en `rutas_auth.py` es el único
punto que serializa un usuario hacia afuera, y solo expone `id`, `email`, `nombre_completo`.

## Seguridad: qué se cubre y qué no

**Cubierto explícitamente:**
- Timing attack sobre el login (email inexistente vs. clave incorrecta) — hash dummy.
- Robo de sesión por XSS — cookie `httponly`, el JS de la página no puede leer el token.
- CSRF básico — `SameSite=Lax` evita que la cookie viaje en requests iniciados desde otro sitio.
- Fuerza bruta dirigida a una cuenta — `intentos_login`, 8/15min.
- Filtración de `app.db` — hashes de contraseña con scrypt+salt, tokens de sesión solo como sha256.

**No implementado:**
- Recuperación de contraseña por email (tablas listas, falta SMTP).
- 2FA.
- Rate limiting por IP (solo por email).
- Token CSRF explícito — se confía en `SameSite=Lax`, que no cubre todos los escenarios (por ejemplo,
  no protege si el sitio tuviera un endpoint mutante accesible por `GET`, pero todos los que mutan acá
  son `POST`/`DELETE`).
- Forzar HTTPS desde la app — depende de cómo se despliegue (`OBS_COOKIE_SECURE` asume que ya hay TLS
  delante).

## SQLite: por qué así

Ver también [WEBAPP.md](WEBAPP.md#dos-bases-de-datos-no-una) para el porqué de tener `app.db` separada
de `observatorio.db`. Acá lo específico de cómo se usa:

- **Conexión nueva por request** ([webapp/db.py](../webapp/db.py)) — SQLite no comparte conexiones
  entre hilos, y uvicorn puede atender requests en hilos distintos.
- **Ruta absoluta, anclada al archivo** (`Path(__file__).resolve().parent.parent / "app.db"`) — a
  propósito **no** reutiliza `core.get_conn()` (el helper que usan los pipelines), que abre
  `observatorio.db` con ruta relativa y hace `raise SystemExit` si falta el archivo. Las dos cosas son
  inaceptables en un servidor: el directorio de trabajo de uvicorn puede ser cualquiera, y un
  `SystemExit` dentro de un handler HTTP tumba el worker entero en vez de devolver un error al cliente.
- **`PRAGMA journal_mode = WAL`**, solo en `app.db` — permite leer mientras se escribe. Con varios
  requests concurrentes sobre la misma base (varios usuarios logueándose a la vez), el modo journal
  por defecto de SQLite da `database is locked`; WAL lo evita para el patrón de uso normal de un
  sitio chico.
- **`PRAGMA foreign_keys = ON`** en cada conexión — las FKs (`sesiones.usuario_id`, `progreso.usuario_id`
  → `usuarios(id) ON DELETE CASCADE`) no se aplican solas en SQLite si no se prende este pragma
  explícitamente por conexión.
- **Esquema idempotente** (`CREATE TABLE IF NOT EXISTS`) aplicado en cada arranque del servidor
  (`init_app_db()`, llamado desde el `lifespan` de [app.py](../app.py)) — no hay sistema de migraciones
  todavía; agregar una columna nueva a futuro va a necesitar `ALTER TABLE` manual.
