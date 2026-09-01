"""
Registro de cursos + validador.

El contenido se valida AL IMPORTAR: si a un tablero le falta "si_baja" o un
capitulo apunta a un panel que no existe, el servidor no arranca. Es preferible
fallar de entrada y ruidoso que servir un capitulo roto en produccion.

Para chequear el contenido sin levantar nada:
    python -m webapp.cursos
"""

from .cargador import cargar_curso

CURSOS = {
    "cuentas-publicas": cargar_curso("cuentas-publicas"),
    "deuda-reservas": cargar_curso("deuda-reservas"),
    "sector-externo": cargar_curso("sector-externo"),
}

# Los data-panel que existen en index.html. Un capitulo (o un tablero) que
# apunte a otra cosa generaria un boton "ver el grafico" que no lleva a
# ningun lado.
PANELES = {"deuda", "consolidada", "externa", "neta", "cartera", "reservas",
           "residencia", "fiscal", "externo", "gemelos", "gasto", "impositiva"}

TIPOS_BLOQUE = {"p", "h3", "lista", "formula", "nota", "tablero", "diagrama"}
CAMPOS_TABLERO = ("suma", "resta", "incluye", "excluye", "si_sube", "si_baja")
FORMAS_DIAGRAMA = {"conjuntos", "flujo"}
MIN_PREGUNTAS = 5


def validar() -> list[str]:
    """Devuelve la lista de problemas encontrados (vacia = todo bien)."""
    problemas = []
    for slug_curso, curso in CURSOS.items():
        vistos = set()
        if not curso.get("capitulos"):
            problemas.append(f"{slug_curso}: no tiene capitulos")
            continue

        for i, cap in enumerate(curso["capitulos"]):
            ref = f"{slug_curso}/{cap.get('slug', f'#{i}')}"
            for campo in ("slug", "titulo", "resumen", "bloques"):
                if not cap.get(campo):
                    problemas.append(f"{ref}: falta '{campo}'")

            if cap.get("slug") in vistos:
                problemas.append(f"{ref}: slug duplicado")
            vistos.add(cap.get("slug"))

            if cap.get("panel") and cap["panel"] not in PANELES:
                problemas.append(f"{ref}: panel desconocido '{cap['panel']}'")

            for j, b in enumerate(cap.get("bloques", [])):
                tipo = b.get("tipo")
                if tipo not in TIPOS_BLOQUE:
                    problemas.append(f"{ref} bloque {j}: tipo desconocido '{tipo}'")
                elif tipo == "lista" and not b.get("items"):
                    problemas.append(f"{ref} bloque {j}: lista vacia")
                elif tipo == "tablero":
                    for campo in CAMPOS_TABLERO:
                        if not b.get(campo):
                            problemas.append(f"{ref} bloque {j}: tablero sin '{campo}'")
                    if b.get("panel") not in PANELES:
                        problemas.append(f"{ref} bloque {j}: tablero con panel invalido")
                elif tipo == "diagrama":
                    forma = b.get("forma")
                    if forma not in FORMAS_DIAGRAMA:
                        problemas.append(f"{ref} bloque {j}: diagrama con 'forma' inválida '{forma}'")
                    elif forma == "conjuntos":
                        if not b.get("contenedor"):
                            problemas.append(f"{ref} bloque {j}: diagrama de conjuntos sin 'contenedor'")
                        if not b.get("partes"):
                            problemas.append(f"{ref} bloque {j}: diagrama de conjuntos sin 'partes'")
                    elif forma == "flujo":
                        nodos = b.get("nodos") or []
                        flechas = b.get("flechas") or []
                        if len(nodos) < 2:
                            problemas.append(f"{ref} bloque {j}: diagrama de flujo con menos de 2 nodos")
                        if not flechas:
                            problemas.append(f"{ref} bloque {j}: diagrama de flujo sin flechas")
                        for f in flechas:
                            if f.get("de") not in nodos or f.get("a") not in nodos:
                                problemas.append(
                                    f"{ref} bloque {j}: flecha '{f.get('de')} -> {f.get('a')}' "
                                    f"referencia un nodo que no esta en 'nodos'")
                elif tipo in ("p", "h3", "formula", "nota") and not b.get("texto"):
                    problemas.append(f"{ref} bloque {j}: '{tipo}' sin texto")

        problemas += _validar_evaluacion(slug_curso, curso.get("evaluacion"))
    return problemas


def _validar_evaluacion(slug_curso: str, ev: dict | None) -> list[str]:
    """Todo curso publicado necesita evaluacion: es lo que habilita el
    certificado, y un curso sin ella dejaria esa promesa rota en silencio."""
    ref = f"{slug_curso}/_evaluacion.md"
    if ev is None:
        return [f"{ref}: falta -- todo curso necesita una evaluacion"]

    problemas = []
    aprobacion = ev.get("aprobacion")
    if not isinstance(aprobacion, int) or not (1 <= aprobacion <= 100):
        problemas.append(f"{ref}: 'aprobacion' invalida ({aprobacion!r}), tiene que ser 1-100")

    preguntas = ev.get("preguntas") or []
    if len(preguntas) < MIN_PREGUNTAS:
        problemas.append(f"{ref}: solo {len(preguntas)} preguntas, hacen falta al menos {MIN_PREGUNTAS}")

    for i, p in enumerate(preguntas):
        pref = f"{ref} pregunta {i}"
        if not p.get("enunciado"):
            problemas.append(f"{pref}: falta 'enunciado'")
        opciones = p.get("opciones") or []
        if len(opciones) < 2:
            problemas.append(f"{pref}: necesita al menos 2 'opcion'")
        correcta = p.get("correcta")
        if not isinstance(correcta, int) or not (0 <= correcta < len(opciones)):
            problemas.append(f"{pref}: 'correcta' ({correcta!r}) no es un indice valido de sus opciones")
    return problemas


def resumen_curso(curso: dict) -> dict:
    """Metadatos del curso, sin el contenido de los capitulos ni las
    respuestas correctas de la evaluacion."""
    ev = curso.get("evaluacion")
    return {
        "slug": curso["slug"],
        "titulo": curso["titulo"],
        "resumen": curso["resumen"],
        "grupo": curso.get("grupo"),
        "n_capitulos": len(curso["capitulos"]),
        "minutos": sum(c.get("minutos", 0) for c in curso["capitulos"]),
        "n_preguntas": len(ev["preguntas"]) if ev else 0,
        "umbral_aprobacion": ev["aprobacion"] if ev else None,
    }


_problemas = validar()
if _problemas:
    raise RuntimeError("Contenido de cursos invalido:\n  - " + "\n  - ".join(_problemas))


if __name__ == "__main__":
    p = validar()
    print("\n".join(p) if p else
          f"OK: {len(CURSOS)} curso(s), "
          f"{sum(len(c['capitulos']) for c in CURSOS.values())} capitulos, sin problemas.")
