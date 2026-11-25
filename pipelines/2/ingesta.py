"""Equipo 2 · Ingesta: deja las fuentes crudas en el bronce (MinIO, `bronze/2/<dataset>/fecha=AAAA-MM-DD/`).

Fuentes de las figuras de Esaú (herbario_cicy, cria_de_cerdo, negocios_en_reservas, unidades_en_reservas):

    denue               DENUE de Campeche, Yucatán y Quintana Roo (CSV)
    cicy_flora          Herbario CICY, colectas de plantas vasculares de la península (CSV)
    censo_agropecuario  Censo Agropecuario 2022, cuadros ca2022_gan24 y ca2022_gan25 (XLSX)
    anp_conanp          Áreas Naturales Protegidas federales de CONANP (SHP con sus archivos)
    marco_geo           Municipios de la península y capa de países vecinos (GeoJSON)

`ingerir()` es la tarea del DAG. Si hay `DENUE_TOKEN` en el entorno, vuelve a consultar el DENUE por entidad
(solo las tres de la península) y deja la lectura del día en `bronze/2/denue/fecha=<hoy>/`: es la fuente que
se refresca. Después revisa que cada dataset tenga sus archivos en bronce; si falta alguno, falla con la lista.

Los archivos sin descarga directa los sube Producción desde la carpeta de Drive (consola de MinIO) o, con
MinIO levantado, cualquiera con:

    python pipelines/2/ingesta.py subir "<carpeta con los archivos>"

que busca en esa carpeta los archivos de la tabla `DATASETS` y los sube a su prefijo, sin transformarlos.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd


def _comun():
    if "equipo2_comun" not in sys.modules:
        spec = importlib.util.spec_from_file_location("equipo2_comun", Path(__file__).with_name("comun.py"))
        sys.modules["equipo2_comun"] = m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    return sys.modules["equipo2_comun"]


comun = _comun()

DENUE_API = "https://www.inegi.org.mx/app/api/denue/v1/consulta"
ENTIDADES = {"04": "campeche", "23": "quintana_roo", "31": "yucatan"}

# dataset -> archivos que necesita (con comodín para el DENUE) y origen que se guarda en los metadatos
DATASETS = {
    "denue": dict(archivos=["*.csv"], origen="https://www.inegi.org.mx/servicios/api_denue.html"),
    "cicy_flora": dict(archivos=["cicy_flora_peninsula_yucatan.csv"],
                       origen="http://datos.cicy.mx/?q=node/70/dataset/download"),
    "censo_agropecuario": dict(archivos=["ca2022_gan24.xlsx", "ca2022_gan25.xlsx"],
                               origen="https://www.inegi.org.mx/programas/ca/2022/#tabulados"),
    "anp_conanp": dict(archivos=[f"232-ANP_ITRF08_19162026.{x}" for x in ("shp", "shx", "dbf", "prj", "cpg")],
                       origen="http://sig.conanp.gob.mx/website/pagsig/info_shape.htm"),
    "marco_geo": dict(archivos=["municipios_peninsula.geojson", "basemap_peninsula.geojson"],
                      origen="https://www.inegi.org.mx/temas/mg/"),
}
OPCIONALES = {"232-ANP_ITRF08_19162026.cpg"}
DENUE_SUBIBLES = ("denue_peninsula_impacto_biodiversidad.csv", "denue_04_", "denue_23_", "denue_31_")


# ---------------------------------------------------------------- DENUE en línea (fuente que se refresca)


def _denue_entidad(cve: str, token: str, paso: int = 1000, pausa: float = 0.3) -> pd.DataFrame:
    filas, ini = [], 1
    while True:
        url = f"{DENUE_API}/BuscarEntidad/todos/{cve}/{ini}/{ini + paso - 1}/{token}"
        with urllib.request.urlopen(url, timeout=120) as r:
            lote = json.loads(r.read().decode("utf-8"))
        if not lote:
            break
        filas.extend(lote)
        if len(lote) < paso:
            break
        ini += paso
        time.sleep(pausa)
    return pd.DataFrame(filas)


def refrescar_denue(token: str) -> dict[str, str]:
    """Consulta el DENUE de las tres entidades y sube cada CSV del día a bronze/2/denue/fecha=<hoy>/."""
    resultado = {}
    for cve, nombre in ENTIDADES.items():
        df = _denue_entidad(cve, token)
        if df.empty:
            raise RuntimeError(f"El DENUE no devolvió registros para la entidad {cve}.")
        contenido = df.to_csv(index=False).encode("utf-8")
        archivo = f"denue_{cve}_{nombre}.csv"
        resultado[archivo] = comun.subir("denue", archivo, contenido, DATASETS["denue"]["origen"])
    return resultado


# ---------------------------------------------------------------- tarea del DAG


def faltantes() -> dict[str, list[str]]:
    """Archivos requeridos que todavía no están en bronce, por dataset."""
    falta = {}
    for dataset, d in DATASETS.items():
        hay = comun.ultimos(dataset)
        if d["archivos"] == ["*.csv"]:
            if not any(n.lower().endswith(".csv") for n in hay):
                falta[dataset] = ["al menos un CSV"]
            continue
        f = [a for a in d["archivos"] if a not in hay and a not in OPCIONALES]
        if f:
            falta[dataset] = f
    return falta


def ingerir() -> dict[str, str]:
    cliente = comun.minio()
    if not cliente.bucket_exists(comun.BUCKET):
        raise RuntimeError(f"No existe el bucket {comun.BUCKET}; levanta minio y minio-init del compose.")
    resultado = {}
    token = comun.env().get("DENUE_TOKEN")
    if token:
        resultado.update(refrescar_denue(token))
    falta = faltantes()
    if falta:
        detalle = "; ".join(f"{d}: {', '.join(a)}" for d, a in falta.items())
        raise RuntimeError(f"Faltan archivos del equipo 2 en bronze/2/ ({detalle}). "
                           "Súbelos desde la carpeta de Drive con `python pipelines/2/ingesta.py subir <carpeta>`.")
    for dataset in DATASETS:
        for nombre, info in comun.ultimos(dataset).items():
            resultado.setdefault(f"{dataset}/{nombre}", f"{comun.BUCKET}/{info['objeto']}")
    return resultado


# ---------------------------------------------------------------- carga inicial desde una carpeta


def _dataset_de(archivo: Path) -> str | None:
    n = archivo.name
    if n.startswith(DENUE_SUBIBLES) and n.endswith(".csv"):
        return "denue"
    for dataset, d in DATASETS.items():
        if n in d["archivos"]:
            return dataset
    return None


def subir_carpeta(carpeta: str | Path) -> dict[str, str]:
    """Busca en `carpeta` (y subcarpetas) los archivos de DATASETS y los sube tal cual a su prefijo."""
    resultado = {}
    for archivo in sorted(Path(carpeta).rglob("*")):
        if archivo.is_file() and (dataset := _dataset_de(archivo)):
            clave = f"{dataset}/{archivo.name}"
            if clave not in resultado:
                resultado[clave] = comun.subir(dataset, archivo.name, archivo.read_bytes(),
                                               DATASETS[dataset]["origen"])
    return resultado


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "subir":
        for k, v in subir_carpeta(sys.argv[2]).items():
            print(f"{k:55} {v}")
        falta = faltantes()
        print("Todo en bronce." if not falta else f"Faltan: {falta}")
    else:
        for k, v in ingerir().items():
            print(f"{k:55} {v}")
