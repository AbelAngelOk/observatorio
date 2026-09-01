"""
Autenticacion: hash de contrasenas y sesiones.

Sin dependencias externas. El hashing usa hashlib.scrypt (stdlib, verificado en
este entorno) en vez de bcrypt/passlib: una dependencia menos que auditar y
mantener, y scrypt es una funcion de derivacion moderna y resistente a GPU.

Las sesiones son tokens opacos guardados en la base, no JWT. Dos motivos:
cerrar sesion realmente invalida el token (con JWT habria que mantener una lista
negra igual), y no hay que custodiar ninguna clave secreta de firma.
"""

import base64
import hashlib
import hmac
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from .db import get_conn

# Parametros de scrypt. n=2^14 es el punto usual entre seguridad y latencia:
# ~50-100ms por hash, tolerable en login y caro para quien ataque por fuerza bruta.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
DKLEN = 32
DIAS_SESION = 30

# Freno a la fuerza bruta.
MAX_INTENTOS = 8
VENTANA_MIN = 15

COOKIE = "sesion"


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


# --------------------------------------------------------------------------
# Contrasenas
# --------------------------------------------------------------------------

def hashear(password: str) -> str:
    """Devuelve 'scrypt$n$r$p$salt_b64$hash_b64'. El formato lleva sus propios
    parametros para poder endurecerlos manana sin romper los hashes de hoy."""
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                        n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=DKLEN)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(dk)}"


def verificar(password: str, guardado: str) -> bool:
    """Comparacion en tiempo constante: comparar con == filtra informacion por
    el tiempo que tarda en fallar."""
    try:
        algo, n, r, p, salt_b64, hash_b64 = guardado.split("$")
        if algo != "scrypt":
            return False
        dk = hashlib.scrypt(password.encode("utf-8"),
                            salt=base64.b64decode(salt_b64),
                            n=int(n), r=int(r), p=int(p),
                            dklen=len(base64.b64decode(hash_b64)))
        return hmac.compare_digest(dk, base64.b64decode(hash_b64))
    except (ValueError, TypeError):
        return False


# Hash de descarte contra el que se verifica cuando el email NO existe. Sin
# esto el login es un oraculo de emails registrados: responder al instante
# ("no existe") vs tardar ~100ms en hashear ("existe pero la clave esta mal")
# es una diferencia medible desde afuera. Con esto, ambos casos tardan igual.
_HASH_DUMMY = hashear("contrasena que nadie usa jamas")


def quemar_tiempo() -> None:
    """Consume el mismo tiempo que una verificacion real."""
    verificar("x", _HASH_DUMMY)


# --------------------------------------------------------------------------
# Validacion de entrada
# --------------------------------------------------------------------------

RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8


def validar_registro(email: str, nombre: str, password: str) -> str | None:
    """Devuelve un mensaje de error, o None si esta todo bien."""
    if not RE_EMAIL.match((email or "").strip()):
        return "Ingresá un email válido."
    if len((nombre or "").strip()) < 2:
        return "Ingresá tu nombre completo."
    if len(password or "") < MIN_PASSWORD:
        return f"La contraseña necesita al menos {MIN_PASSWORD} caracteres."
    return None


# --------------------------------------------------------------------------
# Usuarios
# --------------------------------------------------------------------------

def crear_usuario(conn: sqlite3.Connection, email: str, nombre: str, password: str) -> int:
    cur = conn.execute(
        """INSERT INTO usuarios (email, nombre_completo, password_hash, creado_en)
           VALUES (?, ?, ?, ?)""",
        (email.strip().lower(), nombre.strip(), hashear(password), ahora()),
    )
    conn.commit()
    return cur.lastrowid


def buscar_por_email(conn: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM usuarios WHERE email = ?",
                        (email.strip().lower(),)).fetchone()


def cambiar_password(conn: sqlite3.Connection, usuario_id: int, nueva: str) -> None:
    conn.execute("UPDATE usuarios SET password_hash = ?, actualizado_en = ? WHERE id = ?",
                 (hashear(nueva), ahora(), usuario_id))
    # Cerrar las demas sesiones al cambiar la clave: si alguien la robo, este es
    # el momento en que lo echamos.
    conn.execute("DELETE FROM sesiones WHERE usuario_id = ?", (usuario_id,))
    conn.commit()


# --------------------------------------------------------------------------
# Fuerza bruta
# --------------------------------------------------------------------------

def bloqueado(conn: sqlite3.Connection, email: str) -> bool:
    desde = (datetime.now(timezone.utc) - timedelta(minutes=VENTANA_MIN)).isoformat()
    n = conn.execute("SELECT COUNT(*) FROM intentos_login WHERE email = ? AND cuando > ?",
                     (email.strip().lower(), desde)).fetchone()[0]
    return n >= MAX_INTENTOS


def registrar_fallo(conn: sqlite3.Connection, email: str) -> None:
    conn.execute("INSERT INTO intentos_login (email, cuando) VALUES (?, ?)",
                 (email.strip().lower(), ahora()))
    conn.commit()


def limpiar_intentos(conn: sqlite3.Connection, email: str) -> None:
    conn.execute("DELETE FROM intentos_login WHERE email = ?", (email.strip().lower(),))
    conn.commit()


# --------------------------------------------------------------------------
# Sesiones
# --------------------------------------------------------------------------

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def crear_sesion(conn: sqlite3.Connection, usuario_id: int) -> str:
    """Devuelve el token en claro (va a la cookie). En la base queda su sha256."""
    token = secrets.token_urlsafe(32)          # 256 bits de entropia
    expira = (datetime.now(timezone.utc) + timedelta(days=DIAS_SESION)).isoformat()
    conn.execute("""INSERT INTO sesiones (token_hash, usuario_id, creada_en, expira_en)
                    VALUES (?, ?, ?, ?)""",
                 (_hash_token(token), usuario_id, ahora(), expira))
    conn.commit()
    return token


def usuario_de_token(conn: sqlite3.Connection, token: str | None) -> sqlite3.Row | None:
    if not token:
        return None
    return conn.execute(
        """SELECT u.* FROM sesiones s
           JOIN usuarios u ON u.id = s.usuario_id
           WHERE s.token_hash = ? AND s.expira_en > ?""",
        (_hash_token(token), ahora()),
    ).fetchone()


def borrar_sesion(conn: sqlite3.Connection, token: str | None) -> None:
    if token:
        conn.execute("DELETE FROM sesiones WHERE token_hash = ?", (_hash_token(token),))
        conn.commit()


def purgar_vencidas(conn: sqlite3.Connection) -> None:
    """Housekeeping de arranque: sesiones vencidas e intentos viejos."""
    conn.execute("DELETE FROM sesiones WHERE expira_en < ?", (ahora(),))
    limite = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    conn.execute("DELETE FROM intentos_login WHERE cuando < ?", (limite,))
    conn.commit()
