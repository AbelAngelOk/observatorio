"""Valida el contenido de los cursos sin levantar el servidor.

    python -m webapp.cursos

Pensado como paso previo al deploy: el import de webapp.cursos ya falla si hay
un problema, pero aca el error se lee entero y con codigo de salida.
"""

import sys

from . import CURSOS, validar

problemas = validar()
if problemas:
    print("Contenido invalido:")
    print("\n".join(f"  - {p}" for p in problemas))
    sys.exit(1)

print(f"OK: {len(CURSOS)} curso(s), "
      f"{sum(len(c['capitulos']) for c in CURSOS.values())} capitulos, sin problemas.")
for c in CURSOS.values():
    tableros = sum(1 for cap in c["capitulos"]
                   for b in cap["bloques"] if b["tipo"] == "tablero")
    diagramas = sum(1 for cap in c["capitulos"]
                    for b in cap["bloques"] if b["tipo"] == "diagrama")
    ev = c.get("evaluacion")
    n_preguntas = len(ev["preguntas"]) if ev else 0
    print(f"   {c['slug']}: {len(c['capitulos'])} capitulos, {tableros} tableros, "
          f"{diagramas} diagramas, ~{sum(x.get('minutos', 0) for x in c['capitulos'])} min de lectura, "
          f"{n_preguntas} preguntas (aprueba con {ev['aprobacion'] if ev else '?'}%)")
