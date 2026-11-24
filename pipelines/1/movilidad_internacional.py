"""Pipeline 1.movilidad_internacional: eventos de movilidad y colaboración de la UPY.

Primaria  : Texas A&M, Yucatán Initiative Project y su nota de ingeniería sobre ELCIR (HTML).
Secundaria: nota de prensa sobre el campamento de ciberseguridad en Cardiff (HTML).

Cada evento lleva la URL exacta de la página de la que salió la cifra. Las filas
son las que se pudieron contrastar con la página; los eventos que falten del
formato T1 (portal de la UPY, Canadá, IRAP 2026) se agregan con
`pipelines/1/html_eventos.py` sobre los HTML descargados y una revisión manual.
"""

from __future__ import annotations

import pandas as pd

VIZ_ID = "1.movilidad_internacional"
FUENTE_PRIMARIA = "Texas A&M · Yucatán Initiative Project, programa ELCIR (HTML)"
FUENTE_SECUNDARIA = "Posta · campamento de ciberseguridad en Gales (HTML)"
INSTITUCION = "Universidad Politécnica de Yucatán"
FECHA_OBTENCION = "2026-11-22"
RESPONSABLE = "Joel Alejandro Perez Yupit"

# precision: dia | mes | año  (cuando la página no da el día exacto)
# sentido: Entrante (llegan a Yucatán) | Saliente (viajan desde Yucatán) | Convenio
# participantes_total: cifra que reporta la fuente; participantes_upy: la parte de la UPY, si la fuente la separa.
EVENTOS = [
    dict(evento_id="elcir-2016", fecha="2016-05-15", precision="dia", titulo="ELCIR 2016: estudiantes de Texas A&M visitan Yucatán",
         tipo="Intercambio académico", institucion_aliada="Texas A&M University", pais="Estados Unidos",
         sentido="Entrante", participantes_total=46, participantes_upy=None, nota="Visita del 15 al 27 de mayo de 2016; 46 estudiantes de Texas A&M.",
         fuente_url="https://yucatan-initiative.tamu.edu/programa-de-introduccion-a-la-investigacion-para-el-aprendizaje-comunitario-en-ingenieria"),
    dict(evento_id="elcir-2018", fecha="2018-05-11", precision="dia", titulo="ELCIR 2018: curso de investigación en la UPY",
         tipo="Intercambio académico", institucion_aliada="Texas A&M University", pais="Estados Unidos",
         sentido="Entrante", participantes_total=24, participantes_upy=None, nota="24 estudiantes de Texas A&M cursan Introducción a la investigación en la UPY, del 11 al 27 de mayo de 2018.",
         fuente_url="https://yucatan-initiative.tamu.edu/new-university-yucatan-hosts-engineering-students"),
    dict(evento_id="elcir-2019", fecha="2019-09-02", precision="dia", titulo="ELCIR 2019: estudiantes de Yucatán presentan en Texas A&M",
         tipo="Intercambio académico", institucion_aliada="Texas A&M University", pais="Estados Unidos",
         sentido="Saliente", participantes_total=17, participantes_upy=None, nota="17 estudiantes de Yucatán (UPY, Marista, ITPE) viajan a Texas A&M; el 2 de septiembre presentan sus propuestas de investigación.",
         fuente_url="https://engineering.tamu.edu/news/2019/09/building-bridges-program-unites-texas-and-mexico-in-research.html"),
    dict(evento_id="cardiff-carta-2024", fecha="2024-01-29", precision="dia", titulo="Carta de intención UPY – Cardiff University",
         tipo="Convenio", institucion_aliada="Cardiff University", pais="Gales (Reino Unido)",
         sentido="Convenio", participantes_total=None, participantes_upy=None, nota="Firma de la carta de intención; enfoque en investigación en ciberseguridad.",
         fuente_url="https://www.posta.com.mx/mexico/jovenes-yucatecos-participan-en-campamento-de-ciberseguridad-en-gales/vl1602446"),
    dict(evento_id="cardiff-campamento-2024", fecha="2024-08-01", precision="mes", titulo="Campamento de ciberseguridad en Cardiff",
         tipo="Campamento", institucion_aliada="Cardiff University", pais="Gales (Reino Unido)",
         sentido="Saliente", participantes_total=10, participantes_upy=6, nota="Grupo de 10 yucatecos (5 estudiantes y 5 profesores); 6 son de la UPY: 4 estudiantes y 2 profesores.",
         fuente_url="https://www.posta.com.mx/mexico/jovenes-yucatecos-participan-en-campamento-de-ciberseguridad-en-gales/vl1602446"),
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
