"""Equipo 4 · Ingesta: lleva las fuentes crudas al bronce (MinIO, bronze/4/), sin transformarlas.

- Archivos entregados por el equipo (datos/4/): se suben tal cual. La fecha de obtención es la fecha del archivo.
- INEGI (Censos Económicos): se descargan directo de la URL oficial al bucket, sin pasar por la carpeta.

Cada objeto guarda en sus metadatos: fecha-obtencion, origen y sha256. Es idempotente: un objeto que ya está en
bronce con el mismo contenido no se vuelve a subir, y los de INEGI no se vuelven a descargar.

Uso:  docker compose up -d minio minio-init
      python pipelines/4/ingesta.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path


def _comun():
    if "equipo4_comun" not in sys.modules:
        spec = importlib.util.spec_from_file_location("equipo4_comun", Path(__file__).with_name("comun.py"))
        sys.modules["equipo4_comun"] = m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    return sys.modules["equipo4_comun"]


comun = _comun()
DATOS = Path(comun.env().get("EQUIPO4_DATOS", comun.RAIZ / "datos" / "4"))

# Archivos que el equipo deja en datos/4/ para que la ingesta los suba.
ARCHIVOS_LOCALES = [
    "b2026_01t_act_ef_origen.csv",
    "ied_por_entidad_2018_2025.xlsx",
    "ied_yucatan_anual.xlsx",
    "ied_yucatan_origen.xlsx",
    "turismo_derrama_1T_2020_2026.xlsx",
    "turismo_derrama_trimestral_nacional_internacional.xlsx",
    "turismo_comparativos_4T_y_anual.xlsx",
    "02_llegada_turistas_ocupacion_yucatan.xlsx",
]

# Fuentes con descarga directa: nombre en bronce -> URL oficial.
ARCHIVOS_WEB = {
    "inegi/ce2019_yuc_csv.zip":
        "https://www.inegi.org.mx/contenidos/programas/ce/2019/Datosabiertos/ce2019_yuc_csv.zip",
    "inegi/conjunto_de_datos_ce_yuc_2024_csv.zip":
        "https://www.inegi.org.mx/contenidos/programas/ce/2024/datosabiertos/conjunto_de_datos_ce_yuc_2024_csv.zip",
}


def _existente(nombre: str) -> dict | None:
    try:
        return comun.metadatos(nombre)
    except Exception as e:  # minio.error.S3Error NoSuchKey
        if getattr(e, "code", None) == "NoSuchKey":
            return None
        raise


def _subir(nombre: str, contenido: bytes, fecha: date, origen: str) -> str:
    sha = hashlib.sha256(contenido).hexdigest()
    previo = _existente(nombre)
    if previo and previo["sha256"] == sha:
        return "sin cambios"
    comun.minio().put_object(
        comun.BUCKET, comun.objeto(nombre), io.BytesIO(contenido), len(contenido),
        metadata={"fecha-obtencion": fecha.isoformat(), "origen": origen, "sha256": sha})
    return "actualizado" if previo else "subido"


def ingerir() -> dict[str, str]:
    cliente = comun.minio()
    if not cliente.bucket_exists(comun.BUCKET):
        raise RuntimeError(f"No existe el bucket {comun.BUCKET}; levanta minio y minio-init del compose.")
    resultado = {}
    for nombre in ARCHIVOS_LOCALES:
        ruta = DATOS / nombre
        if not ruta.exists():
            raise FileNotFoundError(f"Falta {ruta}: la ingesta la sube desde datos/4/")
        fecha = datetime.fromtimestamp(ruta.stat().st_mtime).date()
        resultado[nombre] = _subir(nombre, ruta.read_bytes(), fecha, f"datos/4/{nombre}")
    for nombre, url in ARCHIVOS_WEB.items():
        if _existente(nombre):
            resultado[nombre] = "ya estaba en bronce"
            continue
        with urllib.request.urlopen(url, timeout=300) as r:
            resultado[nombre] = _subir(nombre, r.read(), date.today(), url)
    return resultado


if __name__ == "__main__":
    for nombre, estado in ingerir().items():
        print(f"{comun.BUCKET}/{comun.objeto(nombre):60} {estado}")
