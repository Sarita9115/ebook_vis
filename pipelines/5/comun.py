"""Equipo 5 · Conexiones y catálogo de fuentes compartidos por ingesta, plata, oro, validación y catálogo.

- Bronce: MinIO, bucket `bronze`, ruta `5/{dataset}/fecha=AAAA-MM-DD/{archivo}` (la que pide el readme).
- Plata y oro: PostgreSQL, esquemas `plata` y `oro`, una tabla por conjunto con prefijo `5.`.

Las credenciales salen de las variables de entorno (Airflow) o, si no están, del `.env` de la raíz.
Fuera de Docker, MinIO y PostgreSQL se buscan en localhost. Sin rutas locales.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd
from minio import Minio
from sqlalchemy import URL, Engine, create_engine, inspect

RAIZ = Path(__file__).resolve().parents[2]
EQUIPO = 5
BUCKET = "bronze"
PENINSULA = {4: "Campeche", 23: "Quintana Roo", 31: "Yucatán"}  # clave INEGI -> nombre

INEGI = "https://www.inegi.org.mx/contenidos/programas/ccpv"
YUC = "https://www.yucatan.gob.mx/docs/transparencia/cuenta_publica/2025"

# dataset -> dónde está. `url=None`: no hay descarga directa; el archivo se sube a mano a bronce.
DATASETS = {
    "educacion_05": dict(
        institucion="INEGI", url=None, archivo="educacion_05.xlsx",
        enlace="https://www.inegi.org.mx/app/tabulados/interactivos/?pxq=Educacion_Educacion_05_0f341dd6-e247-4d7f-b644-d74afd1e361f",
        manual="Exporta a XLSX el tabulado interactivo Educacion_05 (enlace del catálogo) y súbelo a bronze/5/educacion_05/fecha=AAAA-MM-DD/."),
    "censo_1990": dict(
        institucion="INEGI", archivo="CPyV90_Nal_Caracteristicas_educativas.xlsx",
        url=f"{INEGI}/1990/tabulados/CPyV90_Nal_Caracteristicas_educativas.xlsx"),
    "pobreza_municipal": dict(
        institucion="CONEVAL", archivo="pobreza_municipal.csv",
        url=("https://www.datos.gob.mx/dataset/b6981ccc-083b-4e57-ba6f-d800a7398fa8/resource/"
             "6e409e3a-aa08-45f5-b84b-f5d8cc6fafa8/download/pobreza_municipal.csv")),
    "irs_coneval": dict(
        institucion="CONEVAL", archivo="IRS_ent_mun_2000_2020.zip",
        url="https://www.coneval.org.mx/Medicion/Documents/IRS_2020/IRS_ent_mun_2000_2020.zip"),
    "iter_2020_yuc": dict(
        institucion="INEGI", archivo="iter_31_cpv2020_csv.zip",
        url=f"{INEGI}/2020/datosabiertos/iter/iter_31_cpv2020_csv.zip"),
    "iter_2010_nal": dict(
        institucion="INEGI", archivo="iter_nal_2010_csv.zip",
        url=f"{INEGI}/2010/datosabiertos/iter_nal_2010_csv.zip"),
    "cuenta_publica_tomo2": dict(
        institucion="Gobierno de Yucatán", archivo="TII_pe.pdf", url=f"{YUC}/TII_pe.pdf"),
    "cuenta_publica_tomo6": dict(
        institucion="Gobierno de Yucatán", archivo="TVI_cp_comp_2025.pdf", url=f"{YUC}/TVI_cp_comp_2025.pdf"),
    "gasto_educacion_captura": dict(
        institucion="Gobierno de Yucatán", url=None, archivo="gasto_educacion_2025.csv",
        enlace=f"{YUC}/TII_pe.pdf",
        manual=("Los PDF no se leen solos: transcribe de los Tomos II y VI un CSV con columnas "
                "origen,destino,monto_millones,fuente_tomo,pagina y súbelo.")),
}

# viz_id -> fuentes. La primaria no se repite dentro del equipo; la secundaria sí puede repetirse.
SUBTEMAS = {
    "treinta_anos": dict(titulo="Treinta años aprendiendo", primaria="educacion_05",
                         secundarias=["censo_1990", "irs_coneval"]),
    "pobreza_rezago": dict(titulo="Pobreza y rezago", primaria="pobreza_municipal",
                           secundarias=["irs_coneval"]),
    "la_casa_cambio": dict(titulo="La casa cambió", primaria="iter_2020_yuc",
                           secundarias=["iter_2010_nal"]),
    "lo_que_se_invirtio": dict(titulo="Lo que se invirtió", primaria="cuenta_publica_tomo2",
                               secundarias=["cuenta_publica_tomo6", "educacion_05"]),
}
# Datasets que debe haber en bronce para cada capa.
USADOS_PLATA = ["educacion_05", "censo_1990", "pobreza_municipal", "irs_coneval", "iter_2020_yuc",
                "iter_2010_nal", "gasto_educacion_captura"]


def env() -> dict:
    valores = {}
    ruta = RAIZ / ".env"
    if ruta.exists():
        for linea in ruta.read_text().splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip().strip("'\"")
    return {**valores, **os.environ}


def norm(texto) -> str:
    """Minúsculas, sin acentos ni espacios repetidos (para comparar nombres)."""
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip().lower()


def exigir(condicion, mensaje):
    if not condicion:
        raise ValueError(mensaje)


# ---------------------------------------------------------------- PostgreSQL (plata y oro)
@lru_cache(maxsize=None)
def motor() -> Engine:
    e = env()
    url = e.get("DATABASE_URL") or URL.create(
        "postgresql+psycopg2", username=e.get("POSTGRES_USER"), password=e.get("POSTGRES_PASSWORD"),
        host=e.get("POSTGRES_HOST", "localhost"), port=int(e.get("POSTGRES_PORT", 5432)),
        database=e.get("POSTGRES_DB"))
    return create_engine(url, pool_pre_ping=True)


def escribir(esquema: str, tablas: dict[str, pd.DataFrame]) -> None:
    """Reemplaza las tablas en una sola transacción: se confirman todas o ninguna."""
    with motor().begin() as con:
        for nombre, df in tablas.items():
            df.to_sql(nombre, con, schema=esquema, if_exists="replace", index=False)


def leer_tabla(esquema: str, nombre: str) -> pd.DataFrame:
    if not inspect(motor()).has_table(nombre, schema=esquema):
        raise LookupError(f'No existe {esquema}."{nombre}". Corre antes la capa anterior del equipo 5.')
    return pd.read_sql_table(nombre, motor(), schema=esquema)


# ---------------------------------------------------------------- MinIO (bronce)
@lru_cache(maxsize=None)
def minio() -> Minio:
    e = env()
    return Minio(e.get("MINIO_ENDPOINT", "localhost:9000"), access_key=e.get("MINIO_ROOT_USER"),
                 secret_key=e.get("MINIO_ROOT_PASSWORD"), secure=False)


def _objetos(dataset: str):
    return [o for o in minio().list_objects(BUCKET, prefix=f"{EQUIPO}/{dataset}/", recursive=True)
            if not o.object_name.endswith("/")]


def ultima_fecha(dataset: str) -> str | None:
    """Última carpeta fecha=AAAA-MM-DD de bronze/5/{dataset}/, o None."""
    fechas = {m.group(1) for o in _objetos(dataset) if (m := re.search(r"fecha=(\d{4}-\d{2}-\d{2})/", o.object_name))}
    return max(fechas) if fechas else None


def bajar(dataset: str) -> tuple[str, dict[str, bytes]]:
    """(fecha, {nombre de archivo: bytes}) de la última carga del dataset."""
    fecha = ultima_fecha(dataset)
    if fecha is None:
        manual = DATASETS.get(dataset, {}).get("manual", "")
        raise FileNotFoundError(
            f"No hay archivos en bronze/{EQUIPO}/{dataset}/fecha=AAAA-MM-DD/. "
            f"Corre la ingesta o súbelo a mano en MinIO. {manual}")
    salida = {}
    for o in _objetos(dataset):
        if f"fecha={fecha}/" in o.object_name:
            r = minio().get_object(BUCKET, o.object_name)
            try:
                salida[o.object_name.split("/")[-1]] = r.read()
            finally:
                r.close()
                r.release_conn()
    return fecha, salida


def archivo(archivos: dict[str, bytes], sufijo: str) -> bytes:
    nombres = [n for n in archivos if n.lower().endswith(sufijo)]
    exigir(nombres, f"No hay ningún archivo {sufijo} en bronce. Hay: {list(archivos)}")
    return archivos[max(nombres, key=lambda n: len(archivos[n]))]


def metadatos(dataset: str) -> dict:
    """fecha-obtencion, origen y sha256 que dejó la ingesta junto al objeto."""
    fecha = ultima_fecha(dataset)
    exigir(fecha, f"{dataset} no está en bronce.")
    obj = next(o for o in _objetos(dataset) if f"fecha={fecha}/" in o.object_name)
    st = minio().stat_object(BUCKET, obj.object_name)
    meta = {k.lower().removeprefix("x-amz-meta-"): v for k, v in (st.metadata or {}).items()}
    return {"fecha_obtencion": meta.get("fecha-obtencion", fecha), "origen": meta.get("origen"),
            "sha256": meta.get("sha256"), "tamano_bytes": st.size, "archivo": obj.object_name.split("/")[-1]}


def sha256_de(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def leer_csv_texto(datos: bytes, **kw) -> pd.DataFrame:
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(datos), dtype=str, encoding=enc, **kw)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 1, "no se pudo decodificar")
