"""
Carga el contenido de un curso desde archivos Markdown.

Cada curso vive en webapp/cursos/contenido/<slug>/, con:
    _curso.md          metadatos del curso (front matter, sin cuerpo)
    00-xxx.md, 01-yyy.md, ...   un archivo por capitulo

El prefijo numerico del nombre de archivo define el ORDEN de los capitulos
(por eso se recorren con sorted()); el slug real de cada capitulo va en su
front matter, no en el nombre de archivo, asi que renombrar el archivo para
reordenar NO afecta el progreso guardado de nadie.

Formato de cada archivo:

    ---
    slug: mi-capitulo
    titulo: Titulo del capitulo
    resumen: Una linea.
    minutos: 6
    panel: fiscal          (opcional; vacio si el capitulo no muestra un grafico)
    ---

    Parrafos en markdown simple: **negrita**, ### subtitulos, listas con "- ",
    notas con "> ". Bloques especiales con fences:

    ```formula
    texto de la formula
    ```

    ```tablero
    titulo: ...
    panel: fiscal
    unidad: ...

    ## suma
    - item
    - item

    ## si_sube
    texto libre (una o mas lineas, se unen en un parrafo)
    ```

    ```diagrama
    forma: conjuntos       (o "flujo"; NO se llama "tipo" -- ver nota abajo)
    contenedor: Estado
    parte: Nación
    parte: Provincias
    ```

Por que Markdown y no Python: el contenido es prosa larga que se edita como
texto, no como codigo. Por que no una libreria de Markdown: la sintaxis que
usamos es un subconjunto chico y fijo (nosotros escribimos todo el contenido,
no hay input de terceros), asi que un parser de ~100 lineas alcanza y evita
sumar una dependencia al proyecto.

La EVALUACION de un curso (si tiene) vive aparte, en un archivo reservado
_evaluacion.md dentro de la misma carpeta -- mismo trato que _curso.md, no es
un capitulo. Front matter con el umbral de aprobacion, cuerpo con una o mas
preguntas de opcion multiple:

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

"correcta" es el indice (arranca en 0) de la opcion correcta dentro de la
lista de "opcion" repetidas, en el orden en que aparecen. El indice, nunca el
texto de la respuesta, para no tener que comparar strings.
"""

import re
from pathlib import Path

CONTENIDO_DIR = Path(__file__).resolve().parent / "contenido"

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?\n)---\s*\n?(.*)\Z", re.S)
_FENCE_RE = re.compile(r"(?ms)^```(\w+)\n(.*?)\n```[ \t]*$")
_TABLERO_SECCION_RE = re.compile(r"(?m)^##\s+(\w+)\s*$")


def _parse_front_matter(texto: str) -> tuple[dict, str]:
    """(metadatos, cuerpo). El front matter es 'clave: valor' por linea, sin
    anidamiento: alcanza con lo que usan los capitulos. partition(":") corta
    solo en el PRIMER ':', asi que un titulo como 'Leer el gráfico: Deuda'
    conserva su propio ':' intacto."""
    m = _FRONT_MATTER_RE.match(texto)
    if not m:
        return {}, texto
    bloque, cuerpo = m.groups()
    meta = {}
    for linea in bloque.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        clave, _, valor = linea.partition(":")
        meta[clave.strip()] = valor.strip() or None
    return meta, cuerpo


def _parse_markdown_simple(texto: str) -> list[dict]:
    """Parrafos, ### subtitulos, listas "- " y notas "> ", fuera de los fences."""
    bloques, parrafo, lista, nota = [], [], [], []

    def cerrar_parrafo():
        if parrafo:
            bloques.append({"tipo": "p", "texto": " ".join(parrafo).strip()})
            parrafo.clear()

    def cerrar_lista():
        if lista:
            bloques.append({"tipo": "lista", "items": list(lista)})
            lista.clear()

    def cerrar_nota():
        if nota:
            bloques.append({"tipo": "nota", "texto": " ".join(nota).strip()})
            nota.clear()

    for linea in texto.splitlines():
        linea = linea.rstrip()
        if not linea.strip():
            cerrar_parrafo(); cerrar_lista(); cerrar_nota()
        elif linea.startswith("### "):
            cerrar_parrafo(); cerrar_lista(); cerrar_nota()
            bloques.append({"tipo": "h3", "texto": linea[4:].strip()})
        elif linea.startswith("- "):
            cerrar_parrafo(); cerrar_nota()
            lista.append(linea[2:].strip())
        elif linea.startswith("> "):
            cerrar_parrafo(); cerrar_lista()
            nota.append(linea[2:].strip())
        else:
            cerrar_lista(); cerrar_nota()
            parrafo.append(linea.strip())
    cerrar_parrafo(); cerrar_lista(); cerrar_nota()
    return bloques


def _parse_tablero(texto: str) -> dict:
    """Cabecera 'clave: valor' + secciones '## clave' con lista o parrafo."""
    partes = _TABLERO_SECCION_RE.split(texto)
    cabecera, resto = partes[0], partes[1:]

    meta = {}
    for linea in cabecera.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        clave, _, valor = linea.partition(":")
        meta[clave.strip()] = valor.strip()

    secciones = {}
    for i in range(0, len(resto), 2):
        clave, cuerpo = resto[i], resto[i + 1]
        lineas = [l.strip() for l in cuerpo.splitlines() if l.strip()]
        es_lista = lineas and all(l.startswith("- ") for l in lineas)
        secciones[clave] = [l[2:].strip() for l in lineas] if es_lista else " ".join(lineas)

    return {"tipo": "tablero", **meta, **secciones}


def _parse_diagrama(texto: str) -> dict:
    """Lineas 'clave: valor'; 'parte', 'nodo' y 'flecha' son repetibles y se
    acumulan en listas. 'flecha: A -> B' se parte en {de, a}.

    OJO: la forma del diagrama se declara como 'forma: conjuntos' (no 'tipo:'),
    porque 'tipo' ya esta reservado para el tipo de BLOQUE ("diagrama" mismo,
    el mismo campo que usan p/h3/lista/tablero). Si el DSL tambien usara
    'tipo:' para su propio subtipo, la linea del contenido pisaria el
    "tipo": "diagrama" del bloque."""
    d: dict = {"tipo": "diagrama"}
    partes, nodos, flechas = [], [], []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        clave, _, valor = linea.partition(":")
        clave, valor = clave.strip(), valor.strip()
        if clave == "parte":
            partes.append(valor)
        elif clave == "nodo":
            nodos.append(valor)
        elif clave == "flecha":
            de, _, a = valor.partition("->")
            flechas.append({"de": de.strip(), "a": a.strip()})
        else:
            d[clave] = valor
    if partes:
        d["partes"] = partes
    if nodos:
        d["nodos"] = nodos
    if flechas:
        d["flechas"] = flechas
    return d


def _parse_pregunta(texto: str) -> dict:
    """Lineas 'clave: valor'; 'opcion' es repetible y se acumula en una lista,
    en el orden en que aparece (ese orden es el que indexa 'correcta').
    'enunciado' puede tener su propio ':' -- partition() lo conserva, igual
    que en el resto del parser."""
    d: dict = {"tipo": "pregunta"}
    opciones = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        clave, _, valor = linea.partition(":")
        clave, valor = clave.strip(), valor.strip()
        if clave == "opcion":
            opciones.append(valor)
        else:
            d[clave] = valor
    d["opciones"] = opciones
    if "correcta" in d:
        try:
            d["correcta"] = int(d["correcta"])
        except ValueError:
            pass  # queda como string; el validador de __init__.py lo va a marcar
    return d


_PARSERS_FENCE = {"tablero": _parse_tablero, "diagrama": _parse_diagrama, "pregunta": _parse_pregunta}


def _parse_cuerpo(texto: str) -> list[dict]:
    """Alterna entre markdown simple y los fences especiales, en el orden en
    que aparecen en el archivo."""
    bloques, pos = [], 0
    for m in _FENCE_RE.finditer(texto):
        bloques += _parse_markdown_simple(texto[pos:m.start()])
        lang, contenido = m.group(1), m.group(2)
        if lang == "formula":
            bloques.append({"tipo": "formula", "texto": contenido.strip()})
        else:
            parser = _PARSERS_FENCE.get(lang)
            bloques.append(parser(contenido) if parser else
                           {"tipo": "formula", "texto": contenido.strip()})
        pos = m.end()
    bloques += _parse_markdown_simple(texto[pos:])
    return bloques


def cargar_capitulo(ruta: Path) -> dict:
    meta, cuerpo = _parse_front_matter(ruta.read_text(encoding="utf-8"))
    cap = {
        "slug": meta.get("slug"),
        "titulo": meta.get("titulo"),
        "resumen": meta.get("resumen"),
        "minutos": int(meta["minutos"]) if meta.get("minutos") else 0,
        "bloques": _parse_cuerpo(cuerpo),
    }
    if meta.get("panel"):
        cap["panel"] = meta["panel"]
    return cap


def cargar_evaluacion(slug_dir: str) -> dict | None:
    """None si el curso no tiene _evaluacion.md -- la evaluacion es opcional
    a nivel de parser aunque el validador de __init__.py la exija para todos
    los cursos publicados hoy (ver ahi el porque)."""
    ruta = CONTENIDO_DIR / slug_dir / "_evaluacion.md"
    if not ruta.exists():
        return None
    meta, cuerpo = _parse_front_matter(ruta.read_text(encoding="utf-8"))
    preguntas = [b for b in _parse_cuerpo(cuerpo) if b.get("tipo") == "pregunta"]
    return {
        "aprobacion": int(meta["aprobacion"]) if meta.get("aprobacion") else 70,
        "preguntas": preguntas,
    }


def cargar_curso(slug_dir: str) -> dict:
    base = CONTENIDO_DIR / slug_dir
    meta_curso, _ = _parse_front_matter((base / "_curso.md").read_text(encoding="utf-8"))
    capitulos = [
        cargar_capitulo(archivo)
        for archivo in sorted(base.glob("*.md"))
        if archivo.name not in ("_curso.md", "_evaluacion.md")
    ]
    return {**meta_curso, "capitulos": capitulos, "evaluacion": cargar_evaluacion(slug_dir)}
