"""Pipeline 3.educacion_superior: de los archivos crudos a la tabla de oro.

Primaria  : SEP, Educación superior escolarizada 2024-2025 (datos.gob.mx, CSV por escuela).
Secundaria: ANUIES, Anuario Estadístico de Educación Superior 2025-2026 (XLSX por entidad).

El dato nacional se recorta a Campeche (04), Yucatán (31) y Quintana Roo (23)
antes de salir. La tabla resultante es la que recibe `figura(datos)`.

Uso:
    python pipelines/3/educacion_superior.py RUTA_CSV RUTA_XLSX SALIDA.csv [RUTA_CATALOGO_CCT]
"""

from __future__ import annotations

import sys
import unicodedata

import pandas as pd

VIZ_ID = "3.educacion_superior"
PENINSULA = {4: "Campeche", 23: "Quintana Roo", 31: "Yucatán"}
FUENTE_PRIMARIA = "SEP · Educación superior escolarizada 2024-2025 (datos.gob.mx)"
FUENTE_SECUNDARIA = "ANUIES · Anuario Estadístico de Educación Superior 2025-2026"
INSTITUCION = "SEP / ANUIES"
FECHA_OBTENCION = "2026-11-11"
RESPONSABLE = "Joel Alejandro Perez Yupit"

# Posición de la cabecera municipal (grados decimales, EPSG:4326).
# Yucatán se calcula con la mediana de los centros de trabajo del catálogo SEP.
# Campeche y Quintana Roo no traen coordenadas en los archivos recibidos:
# son valores de referencia aproximados de la cabecera municipal.
CABECERAS_APROX = {
    (4, 1): (20.37, -90.05), (4, 2): (19.845, -90.525), (4, 3): (18.645, -91.825),
    (4, 4): (19.355, -90.72), (4, 5): (20.175, -90.13), (4, 6): (19.745, -89.845),
    (4, 7): (18.255, -92.09), (4, 9): (18.61, -90.74), (4, 10): (18.50, -89.40),
    (4, 11): (18.18, -91.04), (4, 13): (20.31, -90.06),
    (23, 1): (20.51, -86.95), (23, 2): (19.58, -88.05), (23, 3): (21.23, -86.73),
    (23, 4): (18.50, -88.30), (23, 5): (21.16, -86.85), (23, 6): (19.75, -88.71),
    (23, 8): (20.63, -87.08), (23, 9): (20.21, -87.47), (23, 10): (18.68, -88.39),
    (23, 11): (20.85, -86.88),
}

NIVELES = {
    "tec": ("alumnos_tec_esc", "tec_hom_esc", "tec_muj_esc", "ni_tec_total_esc", "egre_tec_total_esc"),
    "lic": ("alumnos_lic_esc", "lic_hom_esc", "lic_muj_esc", "ni_lic_total_esc", "egre_lic_total_esc"),
    "normal": ("alumnos_lic_esc_normal", "normal_hom_esc", "normal_muj_esc", "ni_normal_total_esc", "egre_normal_total_esc"),
    "pos": ("alum_pos_esc", "pos_hombres_esc", "pos_mujeres_esc", "ni_pos_totales_esc", "egre_pos_total_esc"),
}


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn").upper()


def _centroides_yucatan(ruta_catalogo: str | None) -> dict[int, tuple[float, float]]:
    if not ruta_catalogo:
        return {}
    cat = pd.read_csv(ruta_catalogo, usecols=["inmueble_cv_mun", "latitud", "longitud"], low_memory=False)
    cat = cat[(cat.latitud > 19) & (cat.longitud < -86)]
    med = cat.groupby("inmueble_cv_mun")[["latitud", "longitud"]].median()
    return {int(k): (v.latitud, v.longitud) for k, v in med.iterrows()}


def construir_oro(ruta_csv: str, ruta_xlsx: str, ruta_catalogo: str | None = None) -> pd.DataFrame:
    esc = pd.read_csv(ruta_csv)
    esc = esc[esc.cve_entidad.isin(PENINSULA)].copy()  # recorte a la península

    for nivel, (mat, hom, muj, ni, eg) in NIVELES.items():
        esc[f"mat_{nivel}"] = esc[mat].fillna(0)
        esc[f"hom_{nivel}"] = esc[hom].fillna(0)
        esc[f"muj_{nivel}"] = esc[muj].fillna(0)
        esc[f"ni_{nivel}"] = esc[ni].fillna(0)
        esc[f"eg_{nivel}"] = esc[eg].fillna(0)
    suma = lambda p: esc[[f"{p}_{n}" for n in NIVELES]].sum(axis=1)  # noqa: E731
    esc["matricula"], esc["mujeres"], esc["hombres"] = suma("mat"), suma("muj"), suma("hom")
    esc["nuevo_ingreso"], esc["egresados"] = suma("ni"), suma("eg")

    # --- municipio, ciclo 2024-2025
    mun = (
        esc.groupby(["cve_entidad", "entidad", "cve_municipio", "municipio"], as_index=False)
        .agg(matricula=("matricula", "sum"), mujeres=("mujeres", "sum"), hombres=("hombres", "sum"),
             nuevo_ingreso=("nuevo_ingreso", "sum"), egresados=("egresados", "sum"),
             escuelas=("escuela", "nunique"))
    )
    cy = _centroides_yucatan(ruta_catalogo)

    def _pos(r):
        clave = (int(r.cve_entidad), int(r.cve_municipio))
        if r.cve_entidad == 31 and int(r.cve_municipio) in cy:
            return cy[int(r.cve_municipio)]
        return CABECERAS_APROX.get(clave, (None, None))

    mun[["lat", "lon"]] = mun.apply(lambda r: pd.Series(_pos(r)), axis=1)
    mun["coord_origen"] = mun.apply(
        lambda r: "mediana de centros de trabajo SEP" if r.cve_entidad == 31 else "cabecera municipal aproximada", axis=1)
    mun["nivel"], mun["ciclo"] = "municipio", "2024-2025"

    # --- entidad, ciclo 2024-2025 (suma del mismo CSV)
    ent_a = mun.groupby(["cve_entidad", "entidad"], as_index=False)[
        ["matricula", "mujeres", "hombres", "nuevo_ingreso", "egresados"]].sum()
    ent_a["nivel"], ent_a["ciclo"] = "entidad", "2024-2025"

    # --- entidad, ciclo 2025-2026 (Anuario ANUIES)
    anu = pd.read_excel(ruta_xlsx)
    anu["clave"] = anu["ENTIDAD"].map(_sin_acentos)
    filas = []
    for cve, nombre in PENINSULA.items():
        r = anu[anu.clave == _sin_acentos(nombre)].iloc[0]
        filas.append({"cve_entidad": cve, "entidad": nombre, "matricula": r["Matrícula Total"],
                      "mujeres": r["Matrícula Mujeres"], "hombres": r["Matrícula Hombres"],
                      "nuevo_ingreso": r["Nuevo Ingreso Total"], "egresados": r["Egresados Total"],
                      "nivel": "entidad", "ciclo": "2025-2026"})
    ent_b = pd.DataFrame(filas)

    oro = pd.concat([mun, ent_a, ent_b], ignore_index=True)
    oro["viz_id"] = VIZ_ID
    oro["fuente_primaria"] = FUENTE_PRIMARIA
    oro["fuente_secundaria"] = FUENTE_SECUNDARIA
    oro["institucion"] = INSTITUCION
    oro["fecha_obtencion"] = FECHA_OBTENCION
    oro["responsable"] = RESPONSABLE
    cols = ["viz_id", "nivel", "ciclo", "cve_entidad", "entidad", "cve_municipio", "municipio", "lat", "lon",
            "coord_origen", "escuelas", "matricula", "mujeres", "hombres", "nuevo_ingreso", "egresados",
            "fuente_primaria", "fuente_secundaria", "institucion", "fecha_obtencion", "responsable"]
    return oro[cols]


if __name__ == "__main__":
    ruta_csv, ruta_xlsx, salida = sys.argv[1:4]
    catalogo = sys.argv[4] if len(sys.argv) > 4 else None
    construir_oro(ruta_csv, ruta_xlsx, catalogo).to_csv(salida, index=False, encoding="utf-8")
