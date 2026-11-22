"""Pipeline 3.instituciones_educativas: de los archivos crudos a la tabla de oro.

Primaria  : INEGI, DENUE (Yucatán, mayo 2026). Servicios educativos, SCIAN 6111-6113.
Secundaria: SEP, Catálogo de centros de trabajo de Yucatán (centros activos).

La consulta del DENUE se limita a la entidad 31 (no se usa el archivo nacional).
Se recorta al municipio de Mérida, que es el mapa de la figura. De la fuente
de la SEP se descartan todas las columnas de contacto (CURP, RFC, nombres,
correos, teléfonos): la tabla solo lleva conteos, tipo, sostenimiento y posición.

Uso:
    python pipelines/3/instituciones_educativas.py RUTA_DENUE_CSV RUTA_CATALOGO_CCT SALIDA.csv
"""

from __future__ import annotations

import sys

import pandas as pd

VIZ_ID = "3.instituciones_educativas"
CVE_ENT, CVE_MUN, MUNICIPIO = 31, 50, "Mérida"
FUENTE_PRIMARIA = "INEGI · DENUE Yucatán 05-2026, servicios educativos"
FUENTE_SECUNDARIA = "SEP · Catálogo de centros de trabajo, Yucatán"
FECHA_OBTENCION = "2026-11-11"
RESPONSABLE = "Joel Alejandro Perez Yupit"


def _grupo_denue(nombre: str) -> str:
    n = nombre.lower()
    if "necesidades especiales" in n:
        return "Especial"
    if "combinan" in n:
        return "Combinada / otros"
    if "superior" in n and "media superior" not in n:
        return "Superior"
    if "media" in n:
        return "Media superior"
    return "Básica"  # preescolar, primaria y secundaria


def _sostenimiento_denue(nombre: str) -> str:
    return "Público" if "sector público" in nombre.lower() else "Privado"


def _grupo_cct(nivel: str) -> str:
    return {"BÁSICA": "Básica", "MEDIA SUPERIOR": "Media superior", "SUPERIOR": "Superior",
            "ESPECIAL": "Especial"}.get(str(nivel).upper(), "Combinada / otros")


def construir_oro(ruta_denue: str, ruta_catalogo: str) -> pd.DataFrame:
    d = pd.read_csv(ruta_denue, encoding="latin-1", low_memory=False,
                    usecols=["id", "codigo_act", "nombre_act", "per_ocu", "cve_ent", "cve_mun",
                             "nomb_asent", "latitud", "longitud"])
    d = d[(d.cve_ent == CVE_ENT) & (d.cve_mun == CVE_MUN)]
    d = d[d.codigo_act.astype(str).str[:4].isin(["6111", "6112", "6113"])].dropna(subset=["latitud", "longitud"])
    a = pd.DataFrame({
        "fuente": "DENUE",
        "id_registro": d["id"].astype(str),
        "nivel_grupo": d.nombre_act.map(_grupo_denue),
        "sostenimiento": d.nombre_act.map(_sostenimiento_denue),
        "tamano": d.per_ocu,
        "colonia": d.nomb_asent,
        "lat": d.latitud, "lon": d.longitud,
    })

    c = pd.read_csv(ruta_catalogo, low_memory=False,
                    usecols=["cv_cct", "c_tipo", "c_estatus", "inmueble_cv_mun", "inmueble_c_nom_asen",
                             "sostenimiento_c_control", "tiponivelsub_c_servicion1", "latitud", "longitud"])
    c = c[(c.inmueble_cv_mun == CVE_MUN) & (c.c_estatus == "ACTIVO")
          & c.c_tipo.isin(["ESCUELA", "PLANTEL (MEDIA SUPERIOR)"])
          & (c.latitud > 19) & (c.longitud < -86)]
    b = pd.DataFrame({
        "fuente": "SEP",
        "id_registro": c.cv_cct.astype(str),
        "nivel_grupo": c.tiponivelsub_c_servicion1.map(_grupo_cct),
        "sostenimiento": c.sostenimiento_c_control.str.capitalize().replace({"Público": "Público"}),
        "tamano": None,
        "colonia": c.inmueble_c_nom_asen,
        "lat": c.latitud, "lon": c.longitud,
    })

    oro = pd.concat([a, b], ignore_index=True)
    oro.insert(0, "viz_id", VIZ_ID)
    oro["cve_entidad"], oro["cve_municipio"], oro["municipio"] = CVE_ENT, CVE_MUN, MUNICIPIO
    oro["fuente_primaria"] = FUENTE_PRIMARIA
    oro["fuente_secundaria"] = FUENTE_SECUNDARIA
    oro["institucion"] = "INEGI / SEP"
    oro["fecha_obtencion"] = FECHA_OBTENCION
    oro["responsable"] = RESPONSABLE
    return oro


if __name__ == "__main__":
    ruta_denue, ruta_catalogo, salida = sys.argv[1:4]
    construir_oro(ruta_denue, ruta_catalogo).to_csv(salida, index=False, encoding="utf-8")
