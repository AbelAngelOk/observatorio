"""
Genera el PDF del certificado de un curso aprobado.

Por que fpdf2 y no armarlo a mano (como los diagramas SVG del frontend): el
formato PDF es binario y no vale la pena reinventarlo -- a diferencia de un
SVG (XML plano) o de un hash (una funcion de stdlib), no hay un atajo
razonable. fpdf2 es puro Python, sin dependencias del sistema (nada de
wkhtmltopdf ni un motor de navegador), y sus fuentes "core" (Helvetica,
Times) cubren los acentos del espanol sin tener que empaquetar una tipografia.

El nombre que aparece en el certificado es SIEMPRE nombre_completo tal como
esta en la base -- es justamente el campo que se le pide al usuario al
registrarse para esto.
"""

from datetime import datetime, timezone

from fpdf import FPDF

# Paleta del sitio (ver index.html :root) para que el PDF no desentone.
NAVY = (39, 56, 74)        # --paper
STEEL = (79, 109, 137)     # --gold (el acento del tema, pese al nombre)
BEIGE = (239, 227, 211)    # --ink
CREMA = (252, 251, 246)    # --panel

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha_es(momento: datetime) -> str:
    return f"{momento.day} de {MESES[momento.month - 1]} de {momento.year}"


def generar_certificado(nombre_completo: str, curso_titulo: str, puntaje: int) -> bytes:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    ancho, alto = pdf.w, pdf.h

    # Fondo beige + panel central color crema, como el sitio (--ink / --panel).
    pdf.set_fill_color(*BEIGE)
    pdf.rect(0, 0, ancho, alto, style="F")
    margen = 12
    pdf.set_fill_color(*CREMA)
    pdf.rect(margen, margen, ancho - 2 * margen, alto - 2 * margen, style="F")

    # Doble borde decorativo.
    pdf.set_draw_color(*STEEL)
    pdf.set_line_width(0.8)
    pdf.rect(margen, margen, ancho - 2 * margen, alto - 2 * margen)
    pdf.set_line_width(0.3)
    pdf.rect(margen + 3, margen + 3, ancho - 2 * (margen + 3), alto - 2 * (margen + 3))

    pdf.set_text_color(*STEEL)
    pdf.set_font("helvetica", "", 12)
    pdf.set_xy(0, 28)
    pdf.cell(ancho, 8, "OBSERVATORIO DE MACROECONOMÍA ARGENTINA", align="C")

    pdf.set_text_color(*NAVY)
    pdf.set_font("times", "B", 30)
    pdf.set_xy(0, 44)
    pdf.cell(ancho, 14, "Certificado de finalización", align="C")

    pdf.set_font("helvetica", "", 13)
    pdf.set_xy(0, 68)
    pdf.cell(ancho, 8, "Se certifica que", align="C")

    pdf.set_font("times", "B", 26)
    pdf.set_xy(20, 80)
    pdf.multi_cell(ancho - 40, 12, nombre_completo, align="C")

    pdf.set_font("helvetica", "", 13)
    pdf.set_xy(0, 102)
    pdf.cell(ancho, 8, "completó y aprobó el curso", align="C")

    pdf.set_font("times", "B", 19)
    pdf.set_xy(20, 113)
    pdf.multi_cell(ancho - 40, 10, curso_titulo, align="C")

    pdf.set_font("helvetica", "", 12)
    pdf.set_xy(0, 132)
    pdf.cell(ancho, 8,
             f"del módulo de cursos del observatorio, con un puntaje de {puntaje}%.",
             align="C")

    pdf.set_font("helvetica", "", 10.5)
    pdf.set_text_color(90, 100, 110)
    pdf.set_xy(0, alto - margen - 16)
    pdf.cell(ancho, 6, _fecha_es(datetime.now(timezone.utc)), align="C")
    pdf.set_font("helvetica", "I", 8.5)
    pdf.set_xy(0, alto - margen - 10)
    pdf.cell(ancho, 6,
             "Certificado de finalización de un curso propio del sitio, generado automáticamente. "
             "No constituye un título ni una certificación oficial.", align="C")

    return bytes(pdf.output())
