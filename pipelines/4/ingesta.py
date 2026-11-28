"""Equipo 4 · Ingesta: lleva las fuentes crudas al bronce (MinIO, bronze/4/), sin transformarlas.

- Archivos entregados por el equipo (datos/4/): se suben tal cual. La fecha de obtención es la fecha del archivo.
- INEGI (Censos Económicos): se descargan directo de la URL oficial al bucket, sin pasar por la carpeta.
- Fuentes documentales (cifras de un comunicado, sin archivo descargable): la ingesta las escribe en bronce
  como JSON con el enlace de cada cifra. No hay que subir nada a mano.
- Data México (API pública de la Secretaría de Economía): se vuelve a consultar en cada corrida. Si la
  respuesta cambió, el objeto se reemplaza con la fecha del día: es la fuente en streaming del equipo
  (IED trimestral de Yucatán y remesas de Banxico por entidad).

Cada objeto guarda en sus metadatos: fecha-obtencion, origen y sha256. Es idempotente: un objeto que ya está en
bronce con el mismo contenido no se vuelve a subir, y los de INEGI no se vuelven a descargar.

Uso:  docker compose up -d minio minio-init
      python pipelines/4/ingesta.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
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


# API de Data México (Secretaría de Economía): se consultan en cada corrida (streaming).
DATAMEXICO = "https://www.economia.gob.mx/apidatamexico/tesseract/data.jsonrecords"
ARCHIVOS_API = {
    "datamexico/ied_yucatan_trimestral.json":
        f"{DATAMEXICO}?cube=fdi_2_state_investment&drilldowns=Quarter&measures=Investment&State=31",
    "datamexico/remesas_yucatan_anual.json":
        f"{DATAMEXICO}?cube=banxico_mun_income_remittances&drilldowns=Year,State&measures=Remittance+Amount"
        "&State=31",
}


# Fuentes documentales: cifras publicadas en un comunicado, sin base de datos descargable. La ingesta las
# escribe en bronce como JSON, con el enlace de cada cifra; no dependen de ningún archivo local.
DOCUMENTALES = {
    "documental/promesa_empleo_yucatan.json": [
        dict(concepto="prometido", empleos=278000, proyectos=245, inversion_mdp=108000,
             periodo="cartera anunciada a junio de 2022", fecha_dato="2022-06-22",
             fuente="Gobierno de Yucatán, anuncio de inversiones (La Jornada Maya, 22 jun 2022)",
             enlace="https://www.lajornadamaya.mx/yucatan/198088/"
                    "anuncian-inversion-de-mas-de-2-mil-800-mdp-para-generar-empleos-de-yucatan",
             nota="Empleos directos e indirectos que generarían más de 245 proyectos de inversión privada "
                  "(más de 108 mil mdp)."),
        dict(concepto="registrado_imss", empleos=67976, proyectos=None, inversion_mdp=None,
             periodo="oct 2018 - abr 2024", fecha_dato="2024-05-08",
             fuente="IMSS, trabajadores asegurados en Yucatán (vía Gobierno de Yucatán)",
             enlace="https://vocero.com.mx/?p=380036",
             nota="Empleos formales nuevos ante el IMSS en la administración 2018-2024, corte abril 2024 "
                  "(437,516 asegurados)."),
    ],
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
    for nombre, registros in DOCUMENTALES.items():
        contenido = json.dumps(registros, ensure_ascii=False, indent=1).encode("utf-8")
        enlaces = " ; ".join(r["enlace"] for r in registros)
        resultado[nombre] = _subir(nombre, contenido, date.fromisoformat(max(r["fecha_dato"] for r in registros)),
                                   enlaces)
    for nombre, url in ARCHIVOS_API.items():
        with urllib.request.urlopen(url, timeout=120) as r:
            resultado[nombre] = _subir(nombre, r.read(), date.today(), url)
    return resultado


if __name__ == "__main__":
    for nombre, estado in ingerir().items():
        print(f"{comun.BUCKET}/{comun.objeto(nombre):60} {estado}")
