"""
Endpoints de cursos y progreso.

Criterio: el CONTENIDO es publico y el PROGRESO requiere cuenta. Esconder un
curso de datos abiertos detras de un login contradice el proposito del sitio;
la cuenta sirve para llevar el registro de lo leido, no para dar acceso.
"""

import sqlite3

from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel

from . import auth
from .certificados import generar_certificado
from .cursos import CURSOS, resumen_curso
from .db import get_conn
from .rutas_auth import usuario_actual

router = APIRouter(prefix="/api", tags=["cursos"])


def _curso(slug: str) -> dict:
    curso = CURSOS.get(slug)
    if curso is None:
        raise HTTPException(status_code=404, detail="No existe ese curso.")
    return curso


def _completados(conn: sqlite3.Connection, usuario_id: int, curso_slug: str) -> set[str]:
    return {r["capitulo_slug"] for r in conn.execute(
        "SELECT capitulo_slug FROM progreso WHERE usuario_id = ? AND curso_slug = ?",
        (usuario_id, curso_slug))}


def _progreso(curso: dict, hechos: set[str]) -> dict:
    caps = curso["capitulos"]
    siguiente = next((c["slug"] for c in caps if c["slug"] not in hechos), None)
    return {
        "completados": [c["slug"] for c in caps if c["slug"] in hechos],
        "total": len(caps),
        "porcentaje": round(len(hechos & {c["slug"] for c in caps}) / len(caps) * 100),
        "siguiente": siguiente,        # None = curso terminado
    }


def _curso_completo(curso: dict, hechos: set[str]) -> bool:
    return {c["slug"] for c in curso["capitulos"]} <= hechos


def _estado_evaluacion(conn: sqlite3.Connection, usuario_id: int, curso_slug: str) -> dict:
    fila = conn.execute(
        "SELECT puntaje, aprobado, intentos, completado_en FROM evaluaciones "
        "WHERE usuario_id = ? AND curso_slug = ?", (usuario_id, curso_slug)).fetchone()
    if fila is None:
        return {"intentos": 0, "aprobado": False, "puntaje": None, "completado_en": None}
    return {"intentos": fila["intentos"], "aprobado": bool(fila["aprobado"]),
            "puntaje": fila["puntaje"], "completado_en": fila["completado_en"]}


def _registrar_intento(conn: sqlite3.Connection, usuario_id: int, curso_slug: str,
                        puntaje: int, aprobado: bool) -> None:
    fila = conn.execute(
        "SELECT aprobado FROM evaluaciones WHERE usuario_id = ? AND curso_slug = ?",
        (usuario_id, curso_slug)).fetchone()
    if fila is None:
        conn.execute(
            """INSERT INTO evaluaciones (usuario_id, curso_slug, puntaje, aprobado, intentos, completado_en)
               VALUES (?, ?, ?, ?, 1, ?)""",
            (usuario_id, curso_slug, puntaje, int(aprobado), auth.ahora()))
    else:
        # "aprobado" es pegajoso: un intento peor despues de haber aprobado no
        # te quita el certificado ya ganado (ver el comentario en el schema).
        ya_aprobado = bool(fila["aprobado"])
        conn.execute(
            """UPDATE evaluaciones SET puntaje = ?, aprobado = ?, intentos = intentos + 1, completado_en = ?
               WHERE usuario_id = ? AND curso_slug = ?""",
            (puntaje, int(aprobado or ya_aprobado), auth.ahora(), usuario_id, curso_slug))
    conn.commit()


@router.get("/cursos")
def listar():
    return [resumen_curso(c) for c in CURSOS.values()]


@router.get("/cursos/{slug}")
def detalle(slug: str, sesion: str | None = Cookie(default=None)):
    """Curso completo: metadatos + todos los capitulos con su contenido.

    Se manda entero en una sola respuesta (son ~14 capitulos de texto, decenas
    de KB): evita un request por capitulo y hace instantaneo el paso al
    siguiente, que es el gesto central del lector.
    """
    curso = _curso(slug)
    conn = get_conn()
    try:
        u = auth.usuario_de_token(conn, sesion)          # sesion OPCIONAL
        hechos = _completados(conn, u["id"], slug) if u else set()
        # Solo si ademas hay evaluacion y el usuario ya termino el curso: es
        # lo unico que necesita el indice del curso para ofrecer "Rendir
        # evaluacion" o "Descargar certificado" sin otro request aparte.
        evaluacion = None
        if u and curso.get("evaluacion") and _curso_completo(curso, hechos):
            evaluacion = _estado_evaluacion(conn, u["id"], slug)
    finally:
        conn.close()

    return {
        **resumen_curso(curso),
        "capitulos": [
            {**cap, "completado": cap["slug"] in hechos} for cap in curso["capitulos"]
        ],
        "progreso": _progreso(curso, hechos) if u else None,
        "evaluacion": evaluacion,
    }


@router.put("/cursos/{slug}/capitulos/{cap_slug}/completado")
def completar(slug: str, cap_slug: str, sesion: str | None = Cookie(default=None)):
    curso = _curso(slug)
    if not any(c["slug"] == cap_slug for c in curso["capitulos"]):
        raise HTTPException(status_code=404, detail="No existe ese capítulo.")

    conn = get_conn()
    try:
        u = usuario_actual(conn, sesion)                  # sesion REQUERIDA
        conn.execute(
            """INSERT INTO progreso (usuario_id, curso_slug, capitulo_slug, completado_en)
               VALUES (?, ?, ?, ?)
               ON CONFLICT DO NOTHING""",               # idempotente
            (u["id"], slug, cap_slug, auth.ahora()))
        conn.commit()
        return _progreso(curso, _completados(conn, u["id"], slug))
    finally:
        conn.close()


@router.delete("/cursos/{slug}/capitulos/{cap_slug}/completado")
def descompletar(slug: str, cap_slug: str, sesion: str | None = Cookie(default=None)):
    curso = _curso(slug)
    conn = get_conn()
    try:
        u = usuario_actual(conn, sesion)
        conn.execute(
            "DELETE FROM progreso WHERE usuario_id = ? AND curso_slug = ? AND capitulo_slug = ?",
            (u["id"], slug, cap_slug))
        conn.commit()
        return _progreso(curso, _completados(conn, u["id"], slug))
    finally:
        conn.close()


@router.get("/progreso")
def progreso_global(sesion: str | None = Cookie(default=None)):
    """Progreso del usuario en todos los cursos. Lo usa el perfil."""
    conn = get_conn()
    try:
        u = usuario_actual(conn, sesion)
        return {slug: _progreso(curso, _completados(conn, u["id"], slug))
                for slug, curso in CURSOS.items()}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Evaluaciones y certificados.
#
# A diferencia de los capitulos (contenido publico), la evaluacion SI requiere
# sesion desde que se puede verla: a diferencia de leer, rendir sin poder
# quedar identificado no tiene sentido -- el unico fin de la evaluacion es
# habilitar un certificado con tu nombre.
#
# Ademas exige el curso 100% completo (ver _curso_completo): certificar a
# alguien que no paso por el contenido vaciaria el certificado de sentido.
# ---------------------------------------------------------------------------

def _evaluacion(slug: str) -> dict:
    curso = _curso(slug)
    ev = curso.get("evaluacion")
    if ev is None:
        raise HTTPException(status_code=404, detail="Este curso no tiene evaluación.")
    return ev


def _exigir_curso_completo(conn: sqlite3.Connection, usuario_id: int, slug: str, curso: dict) -> None:
    if not _curso_completo(curso, _completados(conn, usuario_id, slug)):
        raise HTTPException(
            status_code=403,
            detail="Completá todos los capítulos del curso para poder rendir la evaluación.")


@router.get("/cursos/{slug}/evaluacion")
def ver_evaluacion(slug: str, sesion: str | None = Cookie(default=None)):
    curso = _curso(slug)
    ev = _evaluacion(slug)
    conn = get_conn()
    try:
        u = usuario_actual(conn, sesion)
        _exigir_curso_completo(conn, u["id"], slug, curso)
        return {
            "titulo": curso["titulo"],
            "umbral": ev["aprobacion"],
            # nunca se manda 'correcta': quien rinde no debe poder leer el
            # indice de la respuesta correcta abriendo la pestaña de red.
            "preguntas": [{"enunciado": p["enunciado"], "opciones": p["opciones"]}
                          for p in ev["preguntas"]],
            "estado": _estado_evaluacion(conn, u["id"], slug),
        }
    finally:
        conn.close()


class RespuestasIn(BaseModel):
    respuestas: list[int]


@router.post("/cursos/{slug}/evaluacion")
def rendir_evaluacion(slug: str, datos: RespuestasIn, sesion: str | None = Cookie(default=None)):
    curso = _curso(slug)
    ev = _evaluacion(slug)
    preguntas = ev["preguntas"]

    if len(datos.respuestas) != len(preguntas):
        raise HTTPException(status_code=400, detail="Faltan respuestas.")
    for r, p in zip(datos.respuestas, preguntas):
        if not (0 <= r < len(p["opciones"])):
            raise HTTPException(status_code=400, detail="Hay una respuesta inválida.")

    conn = get_conn()
    try:
        u = usuario_actual(conn, sesion)
        _exigir_curso_completo(conn, u["id"], slug, curso)

        correctas = sum(1 for r, p in zip(datos.respuestas, preguntas) if r == p["correcta"])
        total = len(preguntas)
        puntaje = round(correctas / total * 100)
        aprobado = puntaje >= ev["aprobacion"]
        _registrar_intento(conn, u["id"], slug, puntaje, aprobado)

        return {"puntaje": puntaje, "correctas": correctas, "total": total,
                "aprobado": aprobado, "umbral": ev["aprobacion"]}
    finally:
        conn.close()


@router.get("/cursos/{slug}/certificado")
def descargar_certificado(slug: str, sesion: str | None = Cookie(default=None)):
    curso = _curso(slug)
    _evaluacion(slug)  # 404 temprano si el curso no tiene evaluacion
    conn = get_conn()
    try:
        u = usuario_actual(conn, sesion)
        estado = _estado_evaluacion(conn, u["id"], slug)
        if not estado["aprobado"]:
            raise HTTPException(status_code=403, detail="Todavía no aprobaste la evaluación de este curso.")
        pdf = generar_certificado(u["nombre_completo"], curso["titulo"], estado["puntaje"])
    finally:
        conn.close()

    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="certificado-{slug}.pdf"'})


@router.get("/certificaciones")
def certificaciones(sesion: str | None = Cookie(default=None)):
    """Estado de evaluacion/certificado en cada curso que tiene una. Alimenta
    la seccion "Certificaciones", separada de "Cursos" en el nav."""
    conn = get_conn()
    try:
        u = usuario_actual(conn, sesion)
        resultado = []
        for slug, curso in CURSOS.items():
            ev = curso.get("evaluacion")
            if ev is None:
                continue
            hechos = _completados(conn, u["id"], slug)
            resultado.append({
                "slug": slug,
                "titulo": curso["titulo"],
                "grupo": curso.get("grupo"),
                "umbral": ev["aprobacion"],
                "progreso": _progreso(curso, hechos),
                "curso_completo": _curso_completo(curso, hechos),
                "evaluacion": _estado_evaluacion(conn, u["id"], slug),
            })
        return resultado
    finally:
        conn.close()
