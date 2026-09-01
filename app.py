"""
Servidor del observatorio: sirve el sitio y expone la API de cuentas y cursos.

Reemplaza a `python -m http.server`:

    python -m uvicorn app:app --reload --port 8000

Por que hay un backend: guardar usuarios y su progreso en los cursos exige algo
que persista del lado del servidor. Los pipelines de ingesta NO cambian: siguen
siendo batch y siguen escribiendo observatorio.db y data/*.json por su cuenta.

SEGURIDAD - lo que este archivo NO hace, y es a proposito:
    NO monta la raiz del proyecto como archivos estaticos.
Montar "/" con StaticFiles(directory=RAIZ) serviria por HTTP, a cualquiera:
app.db (usuarios y hashes de contrasena), observatorio.db, todo el codigo
fuente y .github/. Se exponen SOLO los tres caminos que el sitio necesita:
index.html, /data y /assets.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from webapp import auth
from webapp.db import get_conn, init_app_db
from webapp.rutas_auth import router as router_auth
from webapp.rutas_cursos import router as router_cursos

RAIZ = Path(__file__).resolve().parent
INDEX = RAIZ / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_app_db()
    conn = get_conn()
    try:
        auth.purgar_vencidas(conn)
    finally:
        conn.close()
    yield


app = FastAPI(title="Observatorio — Macroeconomía Argentina", lifespan=lifespan)

# --- API (se registra ANTES que los estaticos: un mount se traga todo lo que
# venga despues bajo su prefijo) ---
app.include_router(router_auth)
app.include_router(router_cursos)


# --- Sitio ---
@app.get("/", include_in_schema=False)
def home():
    return FileResponse(INDEX)


# Solo estas dos carpetas quedan expuestas. `data/` son las series publicas que
# ya consumia el front por fetch(); `assets/` es el JS y CSS del sitio.
app.mount("/data", StaticFiles(directory=RAIZ / "data"), name="data")
app.mount("/assets", StaticFiles(directory=RAIZ / "assets"), name="assets")


# --- Fallback para las rutas del cliente ---
# El sitio tiene URLs reales (/cursos, /indicadores/fiscal, /cursos/<slug>/...)
# que resuelve el router de JS en index.html, no este servidor. Para que abrir
# esas URLs directo -- o recargar la pagina estando en una -- funcione igual
# que "/", cualquier GET que no matcheo antes (API, /data, /assets, todos
# registrados arriba) devuelve el mismo index.html; el router de JS lee
# location.pathname y muestra la vista que corresponda. Tiene que ir al final:
# si estuviera antes que los mounts, se comeria /data/* y /assets/* tambien.
@app.get("/{ruta_cliente:path}", include_in_schema=False)
def spa_fallback(ruta_cliente: str):
    return FileResponse(INDEX)
