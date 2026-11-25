"""Almacén compartido por los pipelines del Equipo 6: MinIO y PostgreSQL/PostGIS.

- MinIO (S3): buckets `bronze` y `raster`, bajo el prefijo del equipo
  `6/{dataset}/fecha=AAAA-MM-DD/` (sección 4 de la arquitectura).
- PostgreSQL/PostGIS: esquemas `plata` y `oro`. Cada carga reemplaza por
  completo las tablas del conjunto dentro de una sola transacción: o se
  confirma todo o no queda ningún cambio parcial.

Variables de entorno:

    MINIO_ENDPOINT        http://minio:9000 por omisión (acepta también "minio:9000")
    MINIO_ROOT_USER       usuario de MinIO
    MINIO_ROOT_PASSWORD   clave de MinIO
    ORO_DB_URL            URL SQLAlchemy completa; si no está, se usa DATABASE_URL
                          (la que define docker-compose para el scheduler) o se
                          arma con POSTGRES_HOST (postgres), POSTGRES_PORT (5432),
                          POSTGRES_USER, POSTGRES_PASSWORD y POSTGRES_DB.
    E6_TMP                carpeta para archivos temporales (opcional)
    E6_CRUDOS_<DATASET>   solo pruebas: carpeta de crudos que la ingesta sube a
                          bronce en vez de descargar (no hay ruta por omisión)
    CATALOG_CSV           ruta de catalog/catalog.csv (opcional)

La carpeta "6" no es un paquete de Python: los pipelines cargan este archivo
por ruta y queda registrado como `e6_almacen`.

Las dependencias pesadas (minio, sqlalchemy, geopandas, requests, gdown) se
importan dentro de cada función, así que este módulo se puede importar sin
ellas (por ejemplo, al parsear el DAG o en las pruebas locales).
"""

from __future__ import annotations

import csv
import datetime as dt
import logging
import os
import re
import shutil
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote_plus, urlparse

log = logging.getLogger("equipo6.almacen")

EQUIPO = "6"
BUCKET_BRONZE = "bronze"
BUCKET_RASTER = "raster"
ESQUEMA_PLATA = "plata"
ESQUEMA_ORO = "oro"
RAIZ_REPO = Path(__file__).resolve().parents[2]
_PATRON_FECHA = re.compile(r"fecha=(\d{4}-\d{2}-\d{2})/")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def hoy() -> str:
    return dt.date.today().isoformat()


@contextmanager
def carpeta_temporal(prefijo: str = "e6_"):
    """Carpeta temporal que se borra al salir."""
    base = os.environ.get("E6_TMP") or None
    if base:
        Path(base).mkdir(parents=True, exist_ok=True)
    ruta = Path(tempfile.mkdtemp(prefix=prefijo, dir=base))
    try:
        yield ruta
    finally:
        shutil.rmtree(ruta, ignore_errors=True)


def descargar_url(url: str, destino: Path, timeout: int = 120) -> Path:
    """Descarga un archivo por HTTP(S) en streaming, sin cargarlo en memoria."""
    import requests

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_suffix(destino.suffix + ".parcial")
    log.info("Descargando %s", url)
    with requests.get(url, stream=True, timeout=timeout,
                      headers={"User-Agent": "visualizacion-yucatan/1.0"}) as r:
        r.raise_for_status()
        with open(parcial, "wb") as f:
            for bloque in r.iter_content(chunk_size=1 << 20):
                f.write(bloque)
    parcial.replace(destino)
    log.info("  %s (%.1f MB)", destino.name, destino.stat().st_size / 1e6)
    return destino


def descargar_drive(origen: str, destino: Path) -> Path:
    """Descarga de Google Drive con gdown. `origen` es URL de archivo, de carpeta o un ID."""
    import gdown

    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    if "/folders/" in origen:
        gdown.download_folder(url=origen, output=str(destino), quiet=False, use_cookies=False)
    else:
        es_url = origen.startswith("http")
        salida = gdown.download(url=origen if es_url else None, id=None if es_url else origen,
                                output=str(destino) + os.sep, quiet=False, fuzzy=True)
        if not salida:
            raise RuntimeError(f"gdown no pudo descargar {origen}")
    return destino


def extraer_zips(carpeta: Path) -> list[Path]:
    """Abre cada ZIP en una carpeta con su mismo nombre. El ZIP se conserva."""
    salidas = []
    for z in sorted(Path(carpeta).rglob("*.zip")):
        dentro = z.with_suffix("")
        if not dentro.exists():
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dentro)
        salidas.append(dentro)
    return salidas


def buscar(carpeta: Path, patron: str, requerido: bool = True) -> Path | None:
    """Primer archivo que cumple el patrón glob (recursivo)."""
    hallados = sorted(Path(carpeta).rglob(patron))
    if not hallados:
        if requerido:
            raise FileNotFoundError(f"No hay {patron} en {carpeta}")
        return None
    return hallados[0]


# ---------------------------------------------------------------------------
# MinIO
# ---------------------------------------------------------------------------

def minio():
    from minio import Minio

    endpoint = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    if "://" not in endpoint:
        endpoint = "http://" + endpoint
    u = urlparse(endpoint)
    usuario = os.environ.get("MINIO_ROOT_USER")
    clave = os.environ.get("MINIO_ROOT_PASSWORD")
    if not usuario or not clave:
        raise RuntimeError("Faltan MINIO_ROOT_USER / MINIO_ROOT_PASSWORD")
    return Minio(u.netloc, access_key=usuario, secret_key=clave, secure=u.scheme == "https")


def prefijo(dataset: str, fecha: str | None = None) -> str:
    """`6/{dataset}/fecha=AAAA-MM-DD/` (o `6/{dataset}/` sin fecha)."""
    base = f"{EQUIPO}/{dataset}/"
    return base + (f"fecha={fecha}/" if fecha else "")


def listar(prefijo_s3: str, bucket: str = BUCKET_BRONZE) -> list[str]:
    cliente = minio()
    if not cliente.bucket_exists(bucket):
        return []
    return [o.object_name for o in cliente.list_objects(bucket, prefix=prefijo_s3, recursive=True)
            if not o.is_dir]


def prefijo_vigente(dataset: str, bucket: str = BUCKET_BRONZE) -> str | None:
    """Partición `fecha=` más reciente del conjunto; si los archivos se subieron
    sin fecha (consola de MinIO), devuelve el prefijo del conjunto; None si no hay nada."""
    objetos = listar(prefijo(dataset), bucket)
    if not objetos:
        return None
    fechas = sorted({m.group(1) for o in objetos if (m := _PATRON_FECHA.search(o))})
    return prefijo(dataset, fechas[-1]) if fechas else prefijo(dataset)


def fecha_de_prefijo(prefijo_s3: str) -> str:
    m = _PATRON_FECHA.search(prefijo_s3)
    return m.group(1) if m else hoy()


def subir_carpeta(carpeta: Path, prefijo_s3: str, bucket: str = BUCKET_BRONZE) -> list[str]:
    """Sube todos los archivos de `carpeta` respetando su estructura relativa."""
    cliente = minio()
    if not cliente.bucket_exists(bucket):
        cliente.make_bucket(bucket)
    subidos = []
    for ruta in sorted(p for p in Path(carpeta).rglob("*") if p.is_file()):
        if ruta.name.endswith(".parcial"):
            continue
        nombre = prefijo_s3 + ruta.relative_to(carpeta).as_posix()
        cliente.fput_object(bucket, nombre, str(ruta))
        subidos.append(nombre)
    log.info("Subidos %d archivos a s3://%s/%s", len(subidos), bucket, prefijo_s3)
    return subidos


def subir_archivo(ruta: Path, nombre: str, bucket: str = BUCKET_BRONZE) -> str:
    cliente = minio()
    if not cliente.bucket_exists(bucket):
        cliente.make_bucket(bucket)
    cliente.fput_object(bucket, nombre, str(ruta))
    return nombre


def bajar_prefijo(prefijo_s3: str, destino: Path, bucket: str = BUCKET_BRONZE,
                  filtro: re.Pattern | None = None) -> Path:
    """Descarga los objetos de un prefijo a `destino`, con su estructura relativa."""
    cliente = minio()
    destino = Path(destino)
    n = 0
    for nombre in listar(prefijo_s3, bucket):
        relativo = nombre[len(prefijo_s3):]
        if filtro and not filtro.search(relativo):
            continue
        cliente.fget_object(bucket, nombre, str(destino / relativo))
        n += 1
    if n == 0:
        raise FileNotFoundError(f"s3://{bucket}/{prefijo_s3} no tiene archivos")
    log.info("Bajados %d archivos de s3://%s/%s", n, bucket, prefijo_s3)
    return destino


def ingestar_urls(dataset: str, urls: dict[str, str], fecha: str | None = None,
                  abrir_zips: bool = True) -> str:
    """Descarga cada URL y la deja en bronce con la fecha de obtención.

    `urls` mapea nombre de archivo en bronce -> URL oficial. Los ZIP se abren
    y su contenido se sube junto al original (sección 4.1).
    """
    destino_s3 = prefijo(dataset, fecha or hoy())
    completar_urls(destino_s3, urls, abrir_zips)
    return destino_s3


def completar_urls(prefijo_s3: str, urls: dict[str, str], abrir_zips: bool = True) -> list[str]:
    """Descarga a `prefijo_s3` solo los archivos de `urls` que todavía no están ahí."""
    presentes = {o[len(prefijo_s3):] for o in listar(prefijo_s3)}
    faltan = {n: u for n, u in urls.items() if n not in presentes}
    if not faltan:
        return []
    with carpeta_temporal() as tmp:
        for nombre, url in faltan.items():
            descargar_url(url, tmp / nombre)
        if abrir_zips:
            extraer_zips(tmp)
        subir_carpeta(tmp, prefijo_s3)
    return list(faltan)


def carpeta_local(dataset: str, carpeta: str | Path | None = None) -> Path | None:
    """Carpeta de crudos para una prueba local, solo si se da explícitamente.

    Se toma del argumento o de la variable E6_CRUDOS_<DATASET>; no hay ruta por
    omisión. Devuelve None si no se pidió.
    """
    valor = carpeta or os.environ.get(f"E6_CRUDOS_{dataset.upper()}")
    if not valor:
        return None
    ruta = Path(valor)
    if not ruta.is_dir():
        raise FileNotFoundError(f"La carpeta de crudos de {dataset} no existe: {ruta}")
    return ruta


def ingestar_carpeta_local(dataset: str, carpeta: Path, fecha: str | None = None) -> str:
    """Prueba local: sube una carpeta de crudos al bronce, como haría la consola de MinIO.

    Los ZIP que no tengan su carpeta abierta al lado se abren y se suben junto
    al original. Después de esto, plata lee de bronce igual que en producción.
    """
    carpeta = Path(carpeta)
    destino_s3 = prefijo(dataset, fecha or hoy())
    subir_carpeta(carpeta, destino_s3)
    for z in sorted(carpeta.rglob("*.zip")):
        if z.with_suffix("").is_dir():
            continue
        with carpeta_temporal() as tmp:
            with zipfile.ZipFile(z) as zf:
                zf.extractall(tmp)
            subir_carpeta(tmp, destino_s3 + z.relative_to(carpeta).with_suffix("").as_posix() + "/")
    return destino_s3


@contextmanager
def crudos(dataset: str, prefijo_s3: str | None = None, filtro: str | None = None,
           bajar_zips: bool = False):
    """Entrega (carpeta_temporal, fecha_obtencion) con la partición de bronce de un conjunto.

    La partición es `prefijo_s3` o la vigente (la `fecha=` más reciente); la
    fecha de obtención sale de ese prefijo. Los ZIP cuyo contenido ya está
    abierto en bronce no se bajan, salvo `bajar_zips=True`; los que se bajan
    se abren en la carpeta temporal.
    """
    p = prefijo_s3 or prefijo_vigente(dataset)
    if p is None:
        raise FileNotFoundError(f"No hay archivos de {dataset} en s3://{BUCKET_BRONZE}/{prefijo(dataset)}; "
                                f"corre primero la ingesta")
    objetos = [o[len(p):] for o in listar(p)]
    # Carpetas presentes (todas las ancestras), para saber qué ZIP ya está abierto.
    abiertos = {"/".join(o.split("/")[:i]) for o in objetos for i in range(1, o.count("/") + 1)}
    patron = re.compile(filtro) if filtro else None
    elegidos = [o for o in objetos
                if (not patron or patron.search(o))
                and (bajar_zips or not (o.endswith(".zip") and o[:-4] in abiertos))]
    if not elegidos:
        raise FileNotFoundError(f"s3://{BUCKET_BRONZE}/{p} no tiene los archivos esperados")
    cliente = minio()
    with carpeta_temporal() as tmp:
        for o in elegidos:
            cliente.fget_object(BUCKET_BRONZE, p + o, str(tmp / o))
        log.info("Bajados %d archivos de s3://%s/%s", len(elegidos), BUCKET_BRONZE, p)
        extraer_zips(tmp)
        yield tmp, fecha_de_prefijo(p)


def resumen_bronce(dataset: str) -> dict | None:
    """Formatos y peso de la partición vigente de bronce, para el catálogo."""
    p = prefijo_vigente(dataset)
    if p is None:
        return None
    cliente = minio()
    objetos = list(cliente.list_objects(BUCKET_BRONZE, prefix=p, recursive=True))
    formatos = sorted({Path(o.object_name).suffix.lstrip(".").lower() for o in objetos if Path(o.object_name).suffix})
    return {"prefijo_bronce": p, "formato": ", ".join(formatos),
            "peso_mb": round(sum(o.size or 0 for o in objetos) / 1e6, 1)}


def fuente_drive(dataset: str) -> str | None:
    """Enlace de Drive para un conjunto: variable `E6_GDRIVE_<DATASET>` o, si alguna
    fila del catálogo de ese viz_id tiene un `enlace` de drive.google.com, ese enlace."""
    valor = os.environ.get(f"E6_GDRIVE_{dataset.upper()}")
    if valor:
        return valor
    for fila in filas_catalogo():
        if fila["viz_id"] == f"{EQUIPO}.{dataset}" and "drive.google.com" in (fila.get("enlace") or ""):
            return fila["enlace"]
    return None


# ---------------------------------------------------------------------------
# PostgreSQL / PostGIS
# ---------------------------------------------------------------------------

def url_bd() -> str:
    url = os.environ.get("ORO_DB_URL") or os.environ.get("DATABASE_URL")
    if url:
        return url
    usuario = os.environ.get("POSTGRES_USER")
    clave = os.environ.get("POSTGRES_PASSWORD")
    base = os.environ.get("POSTGRES_DB")
    if not (usuario and clave and base):
        raise RuntimeError("Falta ORO_DB_URL o POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB")
    host = os.environ.get("POSTGRES_HOST", "postgres")
    puerto = os.environ.get("POSTGRES_PORT", "5432")
    return f"postgresql+psycopg2://{quote_plus(usuario)}:{quote_plus(clave)}@{host}:{puerto}/{base}"


_MOTOR = None


def motor():
    global _MOTOR
    if _MOTOR is None:
        from sqlalchemy import create_engine
        _MOTOR = create_engine(url_bd(), pool_pre_ping=True)
    return _MOTOR


def _es_geo(df) -> bool:
    try:
        import geopandas as gpd
    except ImportError:
        return False
    return isinstance(df, gpd.GeoDataFrame) and df.geometry.name in df.columns


def cargar(tablas: dict, esquema: str) -> list[str]:
    """Reemplaza por completo `esquema."<nombre>"` para cada tabla, en UNA transacción.

    Si cualquiera falla, PostgreSQL revierte todas (el DDL es transaccional),
    así que una nueva ejecución no deja cargas parciales ni filas acumuladas.
    """
    from sqlalchemy import text

    if esquema not in (ESQUEMA_PLATA, ESQUEMA_ORO):
        raise ValueError(f"Esquema no permitido: {esquema}")
    nombres = []
    with motor().begin() as con:
        con.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{esquema}"'))
        for nombre, df in tablas.items():
            con.execute(text(f'DROP TABLE IF EXISTS "{esquema}"."{nombre}" CASCADE'))
            if _es_geo(df):
                df.to_postgis(nombre, con, schema=esquema, if_exists="fail", index=False)
            else:
                df.to_sql(nombre, con, schema=esquema, if_exists="fail", index=False, method="multi",
                          chunksize=5_000)
            nombres.append(f'{esquema}."{nombre}"')
    log.info("Cargadas %s", ", ".join(nombres))
    return nombres


def existe(nombre: str, esquema: str) -> bool:
    from sqlalchemy import inspect
    return inspect(motor()).has_table(nombre, schema=esquema)


def leer(nombre: str, esquema: str):
    """Lee `esquema."<nombre>"`; devuelve GeoDataFrame si tiene columna de geometría."""
    import pandas as pd
    from sqlalchemy import text

    with motor().connect() as con:
        geom = con.execute(text(
            "SELECT f_geometry_column FROM geometry_columns "
            "WHERE f_table_schema = :e AND f_table_name = :t LIMIT 1"
        ), {"e": esquema, "t": nombre}).scalar()
    consulta = f'SELECT * FROM "{esquema}"."{nombre}"'
    if geom:
        import geopandas as gpd
        return gpd.read_postgis(consulta, motor(), geom_col=geom)
    return pd.read_sql(consulta, motor())


def srid(nombre: str, esquema: str) -> int | None:
    from sqlalchemy import text
    with motor().connect() as con:
        return con.execute(text(
            "SELECT srid FROM geometry_columns WHERE f_table_schema = :e AND f_table_name = :t LIMIT 1"
        ), {"e": esquema, "t": nombre}).scalar()


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------

def ruta_catalogo() -> Path:
    candidatos = [os.environ.get("CATALOG_CSV"), "/opt/airflow/catalog/catalog.csv",
                  RAIZ_REPO / "catalog" / "catalog.csv"]
    for c in candidatos:
        if c and Path(c).exists():
            return Path(c)
    raise FileNotFoundError("No se encontró catalog/catalog.csv (define CATALOG_CSV)")


def filas_catalogo() -> list[dict]:
    """Todas las filas del catálogo: hay una por fuente (primaria y secundarias)."""
    with open(ruta_catalogo(), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def catalogo() -> dict[str, dict]:
    """viz_id -> fila de la fuente primaria (la que trae valor_referencia y tolerancia)."""
    elegidas: dict[str, dict] = {}
    for fila in filas_catalogo():
        actual = elegidas.get(fila["viz_id"])
        if actual is None or (fila.get("papel") == "primaria" and actual.get("papel") != "primaria"):
            elegidas[fila["viz_id"]] = fila
    return elegidas




# Recuadro de Campeche, Yucatán y Quintana Roo en EPSG:4326, con sus islas
# (Arrecife Alacranes 22.6°N, Cayo Arcas, Cozumel, Banco Chinchorro).
PENINSULA_4326 = (-92.8, 17.5, -86.4, 22.8)
TABLA_VALIDACION = f"{EQUIPO}.validacion"


def validar_oro(viz_id: str, valor_referencia) -> dict:
    """Valida oro."<viz_id>" contra el catálogo (secciones 4.3 y 5 de la arquitectura).

    La cifra se contrasta solo con `valor_referencia` ± `tolerancia` de la fila
    primaria de catalog/catalog.csv. `valor_referencia` es la función del
    pipeline que calcula la cifra publicada desde la tabla de oro. Devuelve un
    dict con `estado` validado/rechazado, los motivos y los metadatos que el
    catálogo publica; no lanza excepción para reportar todos los subtemas juntos.
    """
    import math

    fila = catalogo().get(viz_id)
    motivos = []
    resultado = {"viz_id": viz_id, "valor_publicado": None, "valor_referencia": None,
                 "tolerancia": None, "estado": "rechazado", "motivos": motivos,
                 "fecha_obtencion": None, "responsable": None, "institucion": None, "crs": None}
    if not fila:
        motivos.append("no está en el catálogo")
        return resultado
    try:
        referencia = float(fila["valor_referencia"])
        tolerancia = float(fila["tolerancia"])
    except (TypeError, ValueError):
        motivos.append("el catálogo no trae valor_referencia y tolerancia")
        return resultado
    resultado.update(valor_referencia=referencia, tolerancia=tolerancia)

    if not existe(viz_id, ESQUEMA_ORO):
        motivos.append(f'no existe oro."{viz_id}"')
        return resultado
    tabla = leer(viz_id, ESQUEMA_ORO)
    if tabla.empty:
        motivos.append("la tabla de oro está vacía")
        return resultado

    valor = float(valor_referencia(tabla))
    resultado["valor_publicado"] = valor
    if math.isnan(valor) or abs(valor - referencia) > tolerancia:
        motivos.append(f"cifra {valor} fuera de {referencia} ± {tolerancia}")

    # Metadatos obligatorios de la tabla de oro.
    if set(tabla.get("viz_id", [])) != {viz_id}:
        motivos.append("la columna viz_id no coincide")
    for columna in ("fuente_primaria", "fuente_secundaria", "institucion", "fecha_obtencion", "responsable"):
        if columna not in tabla or tabla[columna].isna().any() or (tabla[columna].astype(str).str.strip() == "").any():
            motivos.append(f"falta {columna}")
        elif columna in resultado:
            resultado[columna] = str(tabla[columna].iloc[0])

    # Sistema de coordenadas y recorte a la península.
    codigo = srid(viz_id, ESQUEMA_ORO)
    resultado["crs"] = f"EPSG:{codigo}" if codigo else "sin geometría"
    if codigo is not None and codigo != 4326:
        motivos.append(f"SRID {codigo}; se esperaba 4326")
    if codigo is not None:
        geom = tabla.geometry.dropna()
        if len(geom):
            x0, y0, x1, y1 = geom.total_bounds
            p = PENINSULA_4326
            if x0 < p[0] or y0 < p[1] or x1 > p[2] or y1 > p[3]:
                caja = ", ".join(f"{float(v):.3f}" for v in (x0, y0, x1, y1))
                motivos.append(f"la geometría sale de la península (Campeche, Yucatán, Quintana Roo): {caja}")

    # Reglas de fuentes del catálogo.
    filas_equipo = [f for f in filas_catalogo() if f["equipo"] == fila["equipo"]]
    if not any(f["viz_id"] == viz_id and f.get("papel") == "secundaria" for f in filas_equipo):
        motivos.append("el catálogo no registra fuente secundaria")
    misma_primaria = {f["viz_id"] for f in filas_equipo
                      if f.get("papel") == "primaria" and f.get("enlace") == fila.get("enlace")}
    if fila.get("enlace") and len(misma_primaria) > 1:
        motivos.append(f"la fuente primaria se repite en el equipo: {sorted(misma_primaria)}")
    if not motivos:
        resultado["estado"] = "validado"
    return resultado


def guardar_validacion(resultados: dict[str, dict], run_id: str) -> None:
    """Guarda los resultados de una corrida en plata."6.validacion" (reemplaza esa corrida)."""
    import json
    from sqlalchemy import text

    with motor().begin() as con:
        con.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{ESQUEMA_PLATA}"'))
        con.execute(text(
            f'CREATE TABLE IF NOT EXISTS "{ESQUEMA_PLATA}"."{TABLA_VALIDACION}" '
            "(run_id text, viz_id text, estado text, resultado jsonb, creado timestamptz DEFAULT now())"
        ))
        con.execute(text(f'DELETE FROM "{ESQUEMA_PLATA}"."{TABLA_VALIDACION}" WHERE run_id = :r'), {"r": run_id})
        for viz_id, r in resultados.items():
            con.execute(text(
                f'INSERT INTO "{ESQUEMA_PLATA}"."{TABLA_VALIDACION}" (run_id, viz_id, estado, resultado) '
                "VALUES (:r, :v, :e, CAST(:j AS jsonb))"
            ), {"r": run_id, "v": viz_id, "e": r["estado"], "j": json.dumps(r, default=str)})


def leer_validacion(run_id: str) -> dict[str, dict]:
    from sqlalchemy import text

    if not existe(TABLA_VALIDACION, ESQUEMA_PLATA):
        return {}
    with motor().connect() as con:
        filas = con.execute(text(
            f'SELECT viz_id, resultado FROM "{ESQUEMA_PLATA}"."{TABLA_VALIDACION}" WHERE run_id = :r'
        ), {"r": run_id}).fetchall()
    return {v: r for v, r in filas}


# Campos mínimos de la sección 9 que catalog/catalog.csv no trae como columna.
COLUMNAS_EXTRA_CATALOGO = {
    "formato": "text", "peso_mb": "double precision", "fecha_obtencion": "text", "responsable": "text",
    "institucion": "text", "crs": "text", "confidencial": "text", "prefijo_bronce": "text",
    "valor_publicado": "double precision", "motivos": "text", "fecha_validacion": "timestamptz",
}


def publicar_catalogo(resultados: dict[str, dict], bronce: dict[str, dict] | None = None) -> int:
    """Reemplaza las filas del equipo en oro.catalogo en una transacción.

    Toma todas las filas del equipo de catalog/catalog.csv (primarias y
    secundarias). A las de cada viz_id validado en esta corrida les pone su
    estado, la cifra publicada y los metadatos de oro (fecha de obtención,
    responsable, institución, CRS); a la fila primaria, además, formato y peso
    de su partición de bronce (`bronce`: viz_id -> resumen_bronce). No toca
    las filas de otros equipos.
    """
    from sqlalchemy import text

    bronce = bronce or {}
    filas = [f for f in filas_catalogo() if f["equipo"] == EQUIPO]
    if not filas:
        return 0
    columnas_csv = list(filas[0].keys())
    ahora = dt.datetime.now(dt.timezone.utc)
    todas = columnas_csv + list(COLUMNAS_EXTRA_CATALOGO)
    nombres = ", ".join(f'"{c}"' for c in todas)
    marcas = ", ".join(f":c{i}" for i in range(len(todas)))
    with motor().begin() as con:
        con.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{ESQUEMA_ORO}"'))
        definicion = ", ".join(f'"{c}" text' for c in columnas_csv)
        con.execute(text(f'CREATE TABLE IF NOT EXISTS "{ESQUEMA_ORO}".catalogo ({definicion})'))
        for c in columnas_csv:
            con.execute(text(f'ALTER TABLE "{ESQUEMA_ORO}".catalogo ADD COLUMN IF NOT EXISTS "{c}" text'))
        for c, tipo in COLUMNAS_EXTRA_CATALOGO.items():
            con.execute(text(f'ALTER TABLE "{ESQUEMA_ORO}".catalogo ADD COLUMN IF NOT EXISTS "{c}" {tipo}'))
        con.execute(text(f'DELETE FROM "{ESQUEMA_ORO}".catalogo WHERE equipo = :e'), {"e": EQUIPO})
        insertar = text(f'INSERT INTO "{ESQUEMA_ORO}".catalogo ({nombres}) VALUES ({marcas})')
        for fila in filas:
            valores = dict(fila)
            r = resultados.get(fila["viz_id"])
            if r:
                valores.update(
                    estado=r["estado"], valor_publicado=r.get("valor_publicado"),
                    motivos="; ".join(r.get("motivos") or []) or None, fecha_validacion=ahora,
                    fecha_obtencion=r.get("fecha_obtencion"), responsable=r.get("responsable"),
                    institucion=r.get("institucion"), crs=r.get("crs"), confidencial="no",
                )
                if fila.get("papel") == "primaria" and bronce.get(fila["viz_id"]):
                    valores.update(bronce[fila["viz_id"]])
            con.execute(insertar, {f"c{i}": valores.get(c) for i, c in enumerate(todas)})
    log.info("oro.catalogo: %d filas del equipo %s publicadas", len(filas), EQUIPO)
    return len(filas)
