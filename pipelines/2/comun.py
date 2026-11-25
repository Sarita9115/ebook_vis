"""Equipo 2 · Conexiones compartidas por ingesta, plata y oro.

- Bronce: MinIO, bucket `bronze`, prefijo `2/<dataset>/fecha=AAAA-MM-DD/<archivo>`.
- Plata y oro: PostgreSQL (con PostGIS), esquemas `plata` y `oro`, una tabla por conjunto con prefijo `2.`.

Las credenciales salen de las variables de entorno (Airflow) o, si no están, del `.env` de la raíz (el mismo
que usa docker compose). Fuera de Docker, MinIO y PostgreSQL se buscan en localhost.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

import geopandas as gpd
import pandas as pd
from sqlalchemy import URL, Engine, create_engine, inspect, text

RAIZ = Path(__file__).resolve().parents[2]
BUCKET = "bronze"
EQUIPO = "2"


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
    """Reemplaza las tablas en una sola transacción: se confirman todas o ninguna.

    Un GeoDataFrame se guarda con su geometría en PostGIS; un DataFrame, como tabla normal.
    """
    with motor().begin() as con:
        for nombre, df in tablas.items():
            con.execute(text(f'DROP TABLE IF EXISTS {esquema}."{nombre}" CASCADE'))
            if isinstance(df, gpd.GeoDataFrame):
                df.to_postgis(nombre, con, schema=esquema, if_exists="replace", index=False)
            else:
                pd.DataFrame(df).to_sql(nombre, con, schema=esquema, if_exists="replace", index=False)


def leer_tabla(esquema: str, nombre: str) -> pd.DataFrame:
    """Lee una tabla; si tiene columna `geometry` la devuelve como GeoDataFrame."""
    if not inspect(motor()).has_table(nombre, schema=esquema):
        raise LookupError(f'No existe {esquema}."{nombre}". Corre antes la capa {esquema} del equipo 2.')
    with motor().connect() as con:
        columnas = set(con.execute(text("SELECT column_name FROM information_schema.columns "
                                        "WHERE table_schema = :e AND table_name = :t"),
                                   {"e": esquema, "t": nombre}).scalars())
    consulta = f'SELECT * FROM {esquema}."{nombre}"'
    with motor().connect() as con:
        if "geometry" in columnas:
            return gpd.read_postgis(text(consulta), con, geom_col="geometry")
        return pd.read_sql(text(consulta), con)


# ---------------------------------------------------------------- MinIO (bronce)


@lru_cache(maxsize=None)
def minio():
    from minio import Minio

    e = env()
    return Minio(e.get("MINIO_ENDPOINT", "localhost:9000"), access_key=e.get("MINIO_ROOT_USER"),
                 secret_key=e.get("MINIO_ROOT_PASSWORD"), secure=False)


def subir(dataset: str, nombre: str, contenido: bytes, origen: str, fecha: date | None = None) -> str:
    """Copia el archivo tal cual a `bronze/2/<dataset>/fecha=AAAA-MM-DD/<nombre>`.

    Idempotente: si la versión más reciente de ese archivo tiene el mismo contenido (sha256), no lo sube.
    """
    fecha = fecha or date.today()
    sha = hashlib.sha256(contenido).hexdigest()
    previo = ultimos(dataset).get(nombre)
    if previo and previo["sha256"] == sha:
        return f"{BUCKET}/{previo['objeto']} (sin cambios)"
    objeto = f"{EQUIPO}/{dataset}/fecha={fecha.isoformat()}/{nombre}"
    minio().put_object(BUCKET, objeto, io.BytesIO(contenido), len(contenido),
                       metadata={"fecha-obtencion": fecha.isoformat(), "origen": origen, "sha256": sha})
    return f"{BUCKET}/{objeto} (subido)"


def ultimos(dataset: str) -> dict[str, dict]:
    """Versión más reciente de cada archivo de un dataset: {nombre: {objeto, fecha, origen, sha256}}."""
    vistos: dict[str, dict] = {}
    for obj in minio().list_objects(BUCKET, prefix=f"{EQUIPO}/{dataset}/", recursive=True):
        m = re.match(rf"{EQUIPO}/{re.escape(dataset)}/fecha=(\d{{4}}-\d{{2}}-\d{{2}})/(.+)$", obj.object_name)
        if not m:
            continue
        fecha, nombre = m.groups()
        if nombre not in vistos or fecha > vistos[nombre]["fecha"]:
            vistos[nombre] = {"objeto": obj.object_name, "fecha": fecha}
    for info in vistos.values():
        st = minio().stat_object(BUCKET, info["objeto"])
        meta = {k.lower().removeprefix("x-amz-meta-"): v for k, v in (st.metadata or {}).items()}
        info.update(origen=meta.get("origen", ""), sha256=meta.get("sha256", ""))
    return vistos


def bajar(objeto: str) -> bytes:
    """Lee un objeto del bronce completo en memoria."""
    r = minio().get_object(BUCKET, objeto)
    try:
        return r.read()
    finally:
        r.close()
        r.release_conn()
