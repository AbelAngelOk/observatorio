# Ejecución

Todo lo de este documento está verificado corriéndolo, no leyéndolo. Los comandos son de PowerShell
en Windows; en Linux/macOS son los mismos cambiando `python` por `python3` si hace falta.

## Requisitos

| | |
|---|---|
| **Python** | 3.9 o superior. Verificado con 3.13.14. |
| **Dependencias** | **Ninguna** para levantar el sitio: `init_db.py` y `export_json.py` usan solo la stdlib. `requests`, `openpyxl` y `pandas` hacen falta **únicamente** para los pipelines ([requirements.txt](../requirements.txt)). |
| **Internet** | Sí, en el navegador: Chart.js viene de un CDN, las tipografías de Google Fonts, y el panel de reservas consulta la API de datos.gob.ar en vivo. |

**Todos los comandos se corren desde la raíz del repo.** Los scripts abren `observatorio.db` y
`schema.sql` por ruta relativa: desde otra carpeta fallan o te crean una base vacía donde no va.

---

## Ruta A — levantar el sitio

Es lo que necesitás el 90 % de las veces. Tres comandos:

```powershell
pip install -r requirements.txt   # solo la primera vez
python init_db.py                 # crea la base + la semilla verificada a mano
python actualizar.py              # corre los pipelines y exporta a data/
python -m uvicorn app:app --port 8000
```

> **Cambió el comando de arranque.** Antes era `python -m http.server 8000`. Ahora el sitio lo sirve
> [app.py](../app.py), porque además del HTML y los JSON expone la API de cuentas y cursos, que
> necesita guardar cosas del lado del servidor. Para desarrollo, agregá `--reload`.

Y abrir **http://localhost:8000**.

Qué hace cada uno:

1. **`init_db.py`** — ejecuta `schema.sql` (crea tablas, vistas, y las semillas de fuentes y series) y
   carga las 52 observaciones verificadas a mano. Es **idempotente**, y por eso también sirve de
   migración: correlo cuando el esquema cambia y aplica lo nuevo sin tocar los datos.

   ```
   OK: 52 observaciones nuevas de 52 en la semilla (0 ya estaban) -> observatorio.db
   ```
   La segunda vez: `OK: 0 observaciones nuevas de 52 en la semilla (52 ya estaban)`.

2. **`actualizar.py`** — el runner. Corre los pipelines confiables (hoy: reservas), deja cada corrida
   registrada en la tabla `ingestas`, y al final llama solo a `export_json.py`. **Es el mismo comando
   que corre el cron.** La primera vez baja los ~8.500 puntos diarios de reservas; a partir de ahí,
   solo lo que cambió.

   ```
   OK reservas: 8567 puntos en la fuente, 8567 nuevos o revisados.
   OK: reservas_internacionales -> data\reservas_internacionales.json (8567 observaciones)
   ```
   Correlo de nuevo sin que la fuente haya publicado nada y vas a ver **`0 nuevos o revisados`**. Eso
   es lo correcto: significa que la ingesta diaria no ensucia la base.

   Si solo querés re-exportar sin tocar la red: `python export_json.py`.

3. **`python -m http.server 8000`** — cualquier servidor estático sirve; este viene con Python.

### Por qué no alcanza con abrir el archivo

Hacer doble clic en `index.html` **no funciona**, y es la confusión número uno con este repo.

La página trae sus datos con `fetch("data/deuda_publica_bruta.json")`. Bajo el esquema `file://`, el
navegador trata cada archivo local como un origen opaco y bloquea ese `fetch` por CORS. Resultado:
diez de los once paneles muestran el cartel rojo *"No se pudo cargar data/…"*, y el único que anda es
Reservas, porque va por HTTPS contra una API externa y no toca el disco.

Servirlo por HTTP —aunque sea desde tu propia máquina— resuelve el problema entero.

---

## Ruta B — la ingesta automática

En producción nadie corre nada a mano: **[.github/workflows/ingesta.yml](../.github/workflows/ingesta.yml)
corre `python actualizar.py` todos los días a las 09:00 UTC** (06:00 ART) y commitea `observatorio.db`
y `data/` solo si algo cambió. También se dispara a mano desde la pestaña *Actions*.

> **Prerrequisito:** el proyecto tiene que estar en un repo de GitHub. Hoy **ni siquiera es un repo
> git** (`git init`, crear el repo, `git push`). Hasta que eso pase, el workflow existe pero no
> corre nunca.

Los pipelines **experimentales** (deuda y gasto) **no** entran en la corrida diaria: su parseo no fue
confirmado contra el archivo real de la fuente, y un job desatendido no debería poder meter en la base
el resultado de un parseo que nadie verificó. Para correrlos a mano:

```powershell
python actualizar.py --incluir-experimentales
python actualizar.py --solo deuda
```

Antes de habilitarlos en el cron, leé el checklist de [PIPELINES.md](PIPELINES.md).

### Ver si la ingesta está viva

```powershell
python -c "import sqlite3; c=sqlite3.connect('observatorio.db'); c.row_factory=sqlite3.Row; [print(dict(r)) for r in c.execute('SELECT * FROM ultima_ingesta')]"
```

O más simple: el encabezado del sitio dice **"DATOS ACTUALIZADOS AL &lt;fecha&gt;"**, que sale de la
última ingesta exitosa (`data/_meta.json`). Si esa fecha se quedó atrás, la ingesta está rota.

---

## Verificación: qué tenés que ver

Con el sitio servido en `http://localhost:8000`:

- El **encabezado** dice "DATOS ACTUALIZADOS AL" con la fecha de la última ingesta exitosa (no la de hoy).
- El panel que abre por defecto es **06 · Reservas**, con la serie diaria completa desde 2003 (8.500+
  puntos) y los botones de rango (2 años / 5 años / serie completa) funcionando.
- Los **12 paneles del índice** muestran su gráfico, sin ningún cartel rojo.
- Los recuadros de stats de cada panel arrancan en `—` y se completan al abrir el panel (los paneles
  se renderizan al hacer clic, no todos de entrada). Sus números **coinciden con el gráfico**, porque
  se calculan de los mismos datos.

Cifras de control: reservas `Último dato ≈ US$ 47.656M` (jun-2026) y `Máximo histórico ≈ US$ 77.481M`;
deuda pública `Último dato ≈ US$ 483.855M` (serie mensual desde 2019); presión tributaria
`≈ 21,5% del PBI` para 2025.

> Si reservas te muestra **US$ 31.274M** como último dato y **US$ 52.654M** como máximo, estás viendo
> la versión vieja de la página: esos números salían de la API truncada en 5000 registros y
> corresponden a **2016**. Ver [ARQUITECTURA.md](ARQUITECTURA.md#la-base-es-la-única-fuente-de-verdad).

---

## Cuando algo falla

**Un panel muestra "No se pudo cargar data/…json".**
El `fetch` no encontró el archivo. En orden: (1) ¿abriste la página por `http://localhost:8000` y no
con doble clic? (2) ¿existe `data/` al lado de `index.html`? (3) ¿corriste `export_json.py` después
del último cambio en la base? Un `python export_json.py` de nuevo y refrescar suele alcanzar.

**El panel de reservas está vacío.**
Ya no consulta ninguna API desde el navegador: lee `data/reservas_internacionales.json` como los
demás. Si falta, corré `python actualizar.py`.

**El encabezado dice "sin ingesta registrada".**
Nunca corriste `actualizar.py` en esta base, así que no hay nada en la tabla `ingestas`.

**La página se ve sin estilos o sin gráficos.**
Chart.js y las tipografías vienen de CDNs. Sin internet, o con un bloqueador agresivo, no cargan.

**`ModuleNotFoundError: No module named 'openpyxl'` (o `pandas`).**
Estás corriendo un pipeline experimental sin sus dependencias: `pip install -r requirements.txt`.
La ingesta diaria (`actualizar.py` sin flags) **no** los importa, así que no se cae por esto — solo
necesita `requests`. `init_db.py` y `export_json.py` no necesitan nada.

**`export_json.py` imprime menos de 15 líneas.**
La base está incompleta. Corré `python init_db.py` y después `python actualizar.py`.

**"No encontre observatorio.db" al correr un pipeline.**
Los pipelines no crean la base, solo escriben en ella. `python init_db.py` primero.

**Un pipeline falla y no sé por qué.**
El traceback quedó guardado: `SELECT pipeline, estado, mensaje FROM ultima_ingesta`.

**Empezar de cero.**
Borrá `observatorio.db` y `data/`, y volvé a la ruta A. Los dos son artefactos generados: la semilla
vive en `init_db.py` y el resto lo vuelven a traer los pipelines. Lo único que se pierde es el
**historial de revisiones** (los vintages viejos), que no está en ningún otro lado.

> ⚠️ **No confundas las dos bases.** Borrar `observatorio.db` es inofensivo: se regenera.
> Borrar **`app.db`** borra **todas las cuentas de usuario y su progreso en los cursos**, y no se
> puede deshacer: no hay ninguna fuente de la que reconstruirla.

---

## Las dos bases de datos

| | `observatorio.db` | `app.db` |
|---|---|---|
| Guarda | series, observaciones, ingestas | usuarios, sesiones, progreso |
| ¿Se versiona? | **Sí**, la commitea el cron | **Nunca** (está en `.gitignore`) |
| ¿Se puede borrar? | Sí, se regenera | **No**, se pierden las cuentas |
| Quién escribe | los pipelines (batch) | el servidor (`app.py`) |

Están separadas justamente por eso: el workflow de ingesta hace `git add observatorio.db`, así que
si los usuarios vivieran ahí, **los hashes de contraseña terminarían publicados en GitHub**.

### Cuentas: qué mirar si algo falla

**"El login no hace nada", sin error en la consola ni en el servidor.**
Es casi siempre la cookie. Una cookie `Secure` sobre `http://localhost` el navegador la descarta
**en silencio**. En desarrollo tiene que estar apagada (es el default). En producción, detrás de
HTTPS, se prende con la variable de entorno `OBS_COOKIE_SECURE=1`.

**Se me olvidó la contraseña.**
Hoy no hay recuperación por email (requiere SMTP). Se puede cambiar estando logueado, desde *Tu
cuenta*. Las tablas para el flujo de reseteo ya están creadas para enchufarlo más adelante.

**Cambié el contenido de un curso y el servidor no arranca.**
Es a propósito: el contenido se valida al importar, así que un tablero al que le falta un campo
frena el arranque en vez de romperse en producción. Para ver el detalle:
`python -m webapp.cursos`.
