"""Equipo 4 · Conexiones compartidas por ingesta, plata y oro.

- Bronce: MinIO, bucket `bronze`, prefijo `4/`.
- Plata y oro: PostgreSQL, esquemas `plata` y `oro`, una tabla por conjunto con prefijo `4.`.

Las credenciales salen de las variables de entorno (Airflow) o, si no están, del `.env` de la raíz (mismo
archivo que usa docker compose). Fuera de Docker, MinIO y PostgreSQL se buscan en localhost.
"""
from __future__ import annotations

import io
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
from minio import Minio
from sqlalchemy import URL, Engine, create_engine, inspect

RAIZ = Path(__file__).resolve().parents[2]
BUCKET = "bronze"
PREFIJO = "4/"


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


# ---------------------------------------------------------------- PostgreSQL (plata y oro)
@lru_cache(maxsize=None)
def motor() -> Engine:
    """Motor hacia la base del proyecto. `DATABASE_URL` tiene prioridad."""
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
        raise LookupError(f'No existe {esquema}."{nombre}". Corre antes la capa {esquema} del equipo 4.')
    return pd.read_sql_table(nombre, motor(), schema=esquema)


# ---------------------------------------------------------------- MinIO (bronce)
@lru_cache(maxsize=None)
def minio() -> Minio:
    e = env()
    return Minio(e.get("MINIO_ENDPOINT", "localhost:9000"), access_key=e.get("MINIO_ROOT_USER"),
                 secret_key=e.get("MINIO_ROOT_PASSWORD"), secure=False)


def objeto(nombre: str) -> str:
    """Nombre del objeto en el bucket: bronze/4/<nombre>."""
    return PREFIJO + nombre


def bajar(nombre: str) -> io.BytesIO:
    """Lee un archivo de bronce completo en memoria."""
    r = minio().get_object(BUCKET, objeto(nombre))
    try:
        return io.BytesIO(r.read())
    finally:
        r.close()
        r.release_conn()


def metadatos(nombre: str) -> dict:
    """Metadatos que la ingesta guardó junto al objeto (fecha de obtención, origen, sha256)."""
    st = minio().stat_object(BUCKET, objeto(nombre))
    meta = {k.lower().removeprefix("x-amz-meta-"): v for k, v in (st.metadata or {}).items()}
    return {"fecha_obtencion": meta.get("fecha-obtencion"), "origen": meta.get("origen"),
            "sha256": meta.get("sha256"), "tamano_bytes": st.size}
