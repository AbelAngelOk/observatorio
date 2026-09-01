"""Endpoints de cuentas: /api/auth/*"""

import os
import sqlite3

from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel

from . import auth
from .db import get_conn

router = APIRouter(prefix="/api/auth", tags=["auth"])

# OJO: una cookie Secure sobre http://localhost la descarta el navegador EN
# SILENCIO — el sintoma es "el login no hace nada" sin ningun error ni en la
# consola ni en el server. Por eso el default es apagado (dev en http) y en
# produccion detras de HTTPS se prende con OBS_COOKIE_SECURE=1.
COOKIE_SEGURA = os.environ.get("OBS_COOKIE_SECURE", "0") == "1"


class RegistroIn(BaseModel):
    email: str
    nombre_completo: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class PasswordIn(BaseModel):
    actual: str
    nueva: str


def _set_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        auth.COOKIE, token,
        max_age=auth.DIAS_SESION * 24 * 3600,
        httponly=True,      # el JS de la pagina no puede leerla: frena el robo por XSS
        samesite="lax",     # no viaja en requests cross-site: frena CSRF basico
        secure=COOKIE_SEGURA,
        path="/",
    )


def usuario_actual(conn: sqlite3.Connection, token: str | None) -> sqlite3.Row:
    """Exige sesion valida. Lanza 401 si no hay."""
    u = auth.usuario_de_token(conn, token)
    if u is None:
        raise HTTPException(status_code=401, detail="Necesitás iniciar sesión.")
    return u


def _publico(u: sqlite3.Row) -> dict:
    """Lo unico que sale del servidor sobre un usuario. Nunca el hash."""
    return {"id": u["id"], "email": u["email"], "nombre_completo": u["nombre_completo"]}


@router.post("/registro", status_code=201)
def registro(datos: RegistroIn, response: Response):
    error = auth.validar_registro(datos.email, datos.nombre_completo, datos.password)
    if error:
        raise HTTPException(status_code=400, detail=error)

    conn = get_conn()
    try:
        if auth.buscar_por_email(conn, datos.email):
            raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email.")
        uid = auth.crear_usuario(conn, datos.email, datos.nombre_completo, datos.password)
        _set_cookie(response, auth.crear_sesion(conn, uid))
        return _publico(auth.buscar_por_email(conn, datos.email))
    finally:
        conn.close()


@router.post("/login")
def login(datos: LoginIn, response: Response):
    conn = get_conn()
    try:
        if auth.bloqueado(conn, datos.email):
            raise HTTPException(
                status_code=429,
                detail=f"Demasiados intentos fallidos. Esperá {auth.VENTANA_MIN} minutos.")

        u = auth.buscar_por_email(conn, datos.email)
        # Mismo mensaje Y mismo tiempo de respuesta si el email no existe o si
        # la clave esta mal. Lo primero evita regalar una lista de emails
        # validos; lo segundo evita el mismo regalo por via del cronometro:
        # sin el hash dummy, "no existe" responde al instante y "clave mala"
        # tarda los ~100ms del scrypt.
        if u is None:
            auth.quemar_tiempo()
            auth.registrar_fallo(conn, datos.email)
            raise HTTPException(status_code=401, detail="Email o contraseña incorrectos.")
        if not auth.verificar(datos.password, u["password_hash"]):
            auth.registrar_fallo(conn, datos.email)
            raise HTTPException(status_code=401, detail="Email o contraseña incorrectos.")

        auth.limpiar_intentos(conn, datos.email)
        _set_cookie(response, auth.crear_sesion(conn, u["id"]))
        return _publico(u)
    finally:
        conn.close()


@router.post("/logout", status_code=204)
def logout(response: Response, sesion: str | None = Cookie(default=None)):
    conn = get_conn()
    try:
        auth.borrar_sesion(conn, sesion)
    finally:
        conn.close()
    response.delete_cookie(auth.COOKIE, path="/")


@router.get("/yo")
def yo(sesion: str | None = Cookie(default=None)):
    conn = get_conn()
    try:
        return _publico(usuario_actual(conn, sesion))
    finally:
        conn.close()


@router.post("/password", status_code=204)
def password(datos: PasswordIn, response: Response, sesion: str | None = Cookie(default=None)):
    conn = get_conn()
    try:
        u = usuario_actual(conn, sesion)
        if not auth.verificar(datos.actual, u["password_hash"]):
            raise HTTPException(status_code=400, detail="La contraseña actual no es correcta.")
        if len(datos.nueva or "") < auth.MIN_PASSWORD:
            raise HTTPException(
                status_code=400,
                detail=f"La nueva contraseña necesita al menos {auth.MIN_PASSWORD} caracteres.")

        auth.cambiar_password(conn, u["id"], datos.nueva)
        # cambiar_password cierra todas las sesiones; le damos una nueva a este
        # navegador para que no lo expulse su propio cambio de clave.
        _set_cookie(response, auth.crear_sesion(conn, u["id"]))
    finally:
        conn.close()
