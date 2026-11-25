"""Pipeline 1.participacion_estudiantil: actividades de estudiantes de la UPY dentro y fuera del campus.

Primaria  : Diario de Yucatán, nota sobre RoboKaan en Ucú (HTML).
Secundaria: Secretaría de Ciencia de Yucatán, resultados del Concurso de Robótica 2025 (PDF).

Se registran conteos, categorías y lugar. No se publican nombres de personas.
Los demás eventos del formato T1 (Mayabótica, talleres de programación para
niñas y niños) se agregan con `pipelines/1/html_eventos.py` y revisión manual.
"""

from __future__ import annotations

import pandas as pd

VIZ_ID = "1.participacion_estudiantil"
FUENTE_PRIMARIA = "Diario de Yucatán · «Llevan ciencia y robótica a Ucú» (HTML)"
FUENTE_SECUNDARIA = "SECIHTI Yucatán · Ganadores del Concurso de Robótica 2025 (PDF)"
INSTITUCION = "Universidad Politécnica de Yucatán"
FECHA_OBTENCION = "2026-11-22"
RESPONSABLE = "Joel Alejandro Perez Yupit"

EVENTOS = [
    dict(evento_id="concurso-robotica-2025", fecha="2025-11-01", precision="mes", titulo="Concurso de Robótica Yucatán 2025: podios en robot ratón",
         tipo="Competencia", lugar="Yucatán", estudiantes=2,
         nota="La UPY ocupa el 1.er y el 2.º lugar de la categoría Robot ratón (fecha: publicación de resultados).",
         fuente_url="https://ciencia.yucatan.gob.mx/wp-content/uploads/2025/11/Ganadores-robotica-2025.pdf"),
    dict(evento_id="robokaan-puebla-2026", fecha="2026-07-01", precision="año", titulo="Torneo Mexicano de Robótica: 2.º lugar en drones autónomos",
         tipo="Competencia", lugar="Puebla", estudiantes=None,
         nota="El equipo RoboKaan queda en 2.º lugar en la categoría de drones autónomos, en el camino al RoboChallenge 2026 (el día exacto no aparece en la nota).",
         fuente_url="https://www.yucatan.com.mx/yucatan/2026/08/10/llevan-ciencia-y-robotica-a-ucu.html"),
    dict(evento_id="robokaan-ucu-2026", fecha="2026-08-10", precision="dia", titulo="RoboKaan lleva la robótica a la plaza de Ucú",
         tipo="Divulgación en la comunidad", lugar="Ucú, Yucatán", estudiantes=23,
         nota="Demostración pública para niños, jóvenes y familias; el equipo tiene 23 estudiantes de Robótica Computacional y Sistemas Embebidos Computacionales.",
         fuente_url="https://www.yucatan.com.mx/yucatan/2026/08/10/llevan-ciencia-y-robotica-a-ucu.html"),
]


def construir_oro() -> pd.DataFrame:
    oro = pd.DataFrame(EVENTOS)
    oro["fecha"] = pd.to_datetime(oro["fecha"])
    oro.insert(0, "viz_id", VIZ_ID)
    oro["fuente_primaria"] = FUENTE_PRIMARIA
    oro["fuente_secundaria"] = FUENTE_SECUNDARIA
    oro["institucion"] = INSTITUCION
    oro["fecha_obtencion"] = FECHA_OBTENCION
    oro["responsable"] = RESPONSABLE
    return oro.sort_values("fecha").reset_index(drop=True)


if __name__ == "__main__":
    import sys
    construir_oro().to_csv(sys.argv[1], index=False, encoding="utf-8")
