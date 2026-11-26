"""Tabla de oro de 6.corredor_industrial.

Concentración industrial en el corredor Mérida, Umán y Hunucmá.

Fuentes (todas de Yucatán, clave 31; el DENUE nacional no se usa):

- Primaria: DENUE, corte de mayo de 2026, Yucatán (INEGI, URL fechada):
  https://www.inegi.org.mx/contenidos/masiva/denue/2026_05/denue_31_0526_csv.zip
- Secundaria: DENUE Yucatán, cortes de noviembre de 2018, 2019 y 2020:
  https://www.inegi.org.mx/contenidos/masiva/denue/{AAAA}_11/denue_31_11{AA}_csv.zip
- Secundaria: Encuesta Intercensal 2025, población por municipio de Yucatán
  (eic2025_poblacion_31.xlsx, hoja 02).
- Límites: División política municipal 2023 (INEGI, vía CONABIO, mun23gw.zip),
  que es el Marco Geoestadístico municipal en un archivo descargable. Si
  CONABIO no responde, el Marco Geoestadístico 2023 de Yucatán directo del
  INEGI (31_yucatan.zip, capa conjunto_de_datos/31mun): mismo trazo.

Lo que se sabe de los crudos (verificado al abrirlos):

- Cada ZIP trae conjunto_de_datos/denue_inegi_31_.csv. El de 2018 viene en
  UTF-8 y los demás en Latin-1. El corte de 2026 agrega la columna `clee`.
- `per_ocu` trae rangos: 0 a 5, 6 a 10, 11 a 30, 31 a 50, 51 a 100, 101 a 250 y
  "251 y más personas". El último no tiene límite superior. Se usa 375, el
  punto medio de 251 a 500 (supuesto documentado; el contraste de la cifra
  final es contra `valor_referencia` ± `tolerancia` del catálogo).
- Manufactura es SCIAN 31 a 33 y transporte y almacenamiento, 48 y 49.

La tabla de oro es un GeoDataFrame en EPSG:4326, en formato largo con `capa`:

- `participacion`:   personal aproximado y % por grupo (Mérida, Umán, Hunucmá,
                     Resto del estado) en cada corte.
- `establecimiento`: puntos del corte 2026 dentro del corredor.
- `contorno`:        polígonos simplificados de los tres municipios.

Etapas (Airflow, dags/equipo_6.py):

- `ingesta()`: descarga los cuatro DENUE de Yucatán, la Intercensal 2025 y
  los límites a bronze/6/corredor_industrial/fecha=AAAA-MM-DD/. Si la
  partición ya existe, valida cada archivo en MinIO y vuelve a bajar los que
  falten o no sirvan (p. ej. una página HTML guardada como .zip). Un DENUE
  que traiga entidades distintas de Yucatán se rechaza al pasar a plata.
- `plata()`:   carga plata."6.corredor_industrial.denue" (manufactura y
  transporte con 11 o más personas, puntos en EPSG:32616),
  ".poblacion" y ".municipios" (los tres del corredor, EPSG:32616).
- `oro()`:     agrega desde plata y carga oro."6.corredor_industrial".

Nota: `denue_31_csv.zip` (sin fecha) es el corte vigente del INEGI y cambia
con cada publicación: desde el 21/11/2026 es el de noviembre de 2026, con los
encabezados en mayúsculas. Por eso se usa la URL fechada del corte de mayo de
2026, con el que se fijó el valor del catálogo. El INEGI responde 200 con una
página HTML cuando un archivo no existe; `alm.descargar_url` lo rechaza.

Prueba local (opcional y explícita): `ingesta(carpeta_local=...)` o la variable
E6_CRUDOS_CORREDOR_INDUSTRIAL suben una carpeta de crudos a bronce en vez de
descargar (lo que falte se descarga de su URL); `construir_oro(dir_crudos,
ruta_municipios)` arma el oro en memoria desde rutas dadas.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import io
import logging
import re
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd


def _cargar_almacen():
    """Carga pipelines/6/_almacen.py por ruta (la carpeta "6" no es un paquete)."""
    if "e6_almacen" not in sys.modules:
        spec = importlib.util.spec_from_file_location("e6_almacen", Path(__file__).with_name("_almacen.py"))
        modulo = importlib.util.module_from_spec(spec)
        sys.modules["e6_almacen"] = modulo
        spec.loader.exec_module(modulo)
    return sys.modules["e6_almacen"]


alm = _cargar_almacen()
log = logging.getLogger("equipo6.corredor_industrial")

VIZ_ID = "6.corredor_industrial"
DATASET = "corredor_industrial"
TABLAS_PLATA = {"denue": f"{VIZ_ID}.denue", "poblacion": f"{VIZ_ID}.poblacion",
                "municipios": f"{VIZ_ID}.municipios"}
CRS_TRABAJO = 32616
CRS_PUBLICACION = 4326
CVE_ENT_YUCATAN = "31"

CORTES = {
    2018: "denue_31_1118_csv.zip",
    2019: "denue_31_1119_csv.zip",
    2020: "denue_31_1120_csv.zip",
    2026: "denue_31_0526_csv.zip",
}
ANIO_ACTUAL = 2026
CSV_EN_ZIP = "conjunto_de_datos/denue_inegi_31_.csv"
COLUMNAS_DENUE = {"id", "codigo_act", "per_ocu", "cve_ent", "cve_mun", "latitud", "longitud"}
EIC = "eic2025_poblacion_31.xlsx"
MUN23 = "mun23gw.zip"
MG2023 = "mg2023_31_yucatan.zip"  # nombre en bronce del ZIP del Marco Geoestadístico 2023

URLS = {
    2018: "https://www.inegi.org.mx/contenidos/masiva/denue/2018_11/denue_31_1118_csv.zip",
    2019: "https://www.inegi.org.mx/contenidos/masiva/denue/2019_11/denue_31_1119_csv.zip",
    2020: "https://www.inegi.org.mx/contenidos/masiva/denue/2020_11/denue_31_1120_csv.zip",
    # Corte fechado: denue_31_csv.zip (sin fecha) es el corte vigente y desde el
    # 21/11/2026 ya es el de noviembre de 2026 (encabezados en mayúsculas, otras cifras).
    2026: "https://www.inegi.org.mx/contenidos/masiva/denue/2026_05/denue_31_0526_csv.zip",
    "eic": "https://www.inegi.org.mx/contenidos/programas/eic/2025/tabulados/eic2025_poblacion_31.xlsx",
    "mun23": "http://www.conabio.gob.mx/informacion/gis/maps/geo/mun23gw.zip",
    # Respaldo de los límites: mismo trazo que mun23gw (verificado), directo del INEGI.
    "mg2023": ("https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/"
               "productos/geografia/marcogeo/794551067314/31_yucatan.zip"),
}
LIMITES = {MUN23: URLS["mun23"], MG2023: URLS["mg2023"]}  # en orden de preferencia

FUENTE_PRIMARIA = "INEGI: DENUE, corte de mayo de 2026, Yucatán"
FUENTE_SECUNDARIA = (
    "INEGI: DENUE Yucatán, cortes de noviembre de 2018, 2019 y 2020; "
    "Encuesta Intercensal 2025, población por municipio de Yucatán"
)
INSTITUCION = "INEGI"
RESPONSABLE = "Gio Soriano"

SCIAN = {"31": "Manufactura", "32": "Manufactura", "33": "Manufactura",
         "48": "Transporte y almacenamiento", "49": "Transporte y almacenamiento"}
PUNTO_MEDIO = {
    "11 a 30 personas": 20.5,
    "31 a 50 personas": 40.5,
    "51 a 100 personas": 75.5,
    "101 a 250 personas": 175.5,
    "251 y más personas": 375.0,
}
CORREDOR = {"050": "Mérida", "101": "Umán", "038": "Hunucmá"}
RESTO = "Resto del estado"
GRUPOS = ["Mérida", "Umán", "Hunucmá", RESTO]

TOLERANCIA_CONTORNO_M = 60


def leer_denue(ruta_zip: Path) -> pd.DataFrame:
    """Lee el CSV del ZIP por entidad; detecta UTF-8 o Latin-1.

    Los encabezados se pasan a minúsculas: el INEGI los publica en minúsculas
    (2018 a mayo de 2026) o en mayúsculas (noviembre de 2026).
    """
    with zipfile.ZipFile(ruta_zip) as zf:
        crudo = zf.read(CSV_EN_ZIP)
    try:
        crudo.decode("utf-8")
        codificacion = "utf-8"
    except UnicodeDecodeError:
        codificacion = "latin-1"
    df = pd.read_csv(io.BytesIO(crudo), dtype=str, encoding=codificacion)
    df.columns = [c.strip().lower() for c in df.columns]
    faltan = COLUMNAS_DENUE - set(df.columns)
    if faltan:
        raise ValueError(f"{ruta_zip.name}: faltan columnas {sorted(faltan)}")
    if set(df["cve_ent"].unique()) != {CVE_ENT_YUCATAN}:
        raise ValueError(f"{ruta_zip.name}: trae entidades distintas de Yucatán")
    return df


def filtrar(df: pd.DataFrame) -> pd.DataFrame:
    """Manufactura y transporte con 11 o más personas, con personal aproximado."""
    rangos = set(df["per_ocu"].dropna().unique())
    nuevos = {r for r in rangos if r not in PUNTO_MEDIO and not r.startswith(("0 a", "6 a"))}
    if nuevos:
        raise ValueError(f"Rangos de personal no reconocidos: {sorted(nuevos)}")
    d = df[df["codigo_act"].str[:2].isin(SCIAN) & df["per_ocu"].isin(PUNTO_MEDIO)].copy()
    d["sector"] = d["codigo_act"].str[:2].map(SCIAN)
    d["personal_aprox"] = d["per_ocu"].map(PUNTO_MEDIO)
    d["grupo"] = d["cve_mun"].map(CORREDOR).fillna(RESTO)
    return d


def leer_poblacion(ruta: Path) -> pd.Series:
    """Población 2025 por grupo (hoja 02, fila Total / Valor)."""
    hoja = pd.read_excel(ruta, sheet_name="02", header=None)
    total = hoja[(hoja[2] == "Total") & (hoja[3] == "Valor")]
    mun = total[total[1].astype(str).str.match(r"^\d{3} ")]
    pob_mun = pd.Series(mun[4].astype(float).values, index=mun[1].astype(str).str[:3])
    estado = total[total[1].astype(str).str.strip().isin(["Total", "Estatal", "31 Yucatán"])]
    pob_estado = float(estado[4].iloc[0]) if len(estado) else float(pob_mun.sum())
    pob = {CORREDOR[c]: pob_mun[c] for c in CORREDOR}
    pob[RESTO] = pob_estado - sum(pob.values())
    return pd.Series(pob)


def _archivo_corte(dir_crudos: Path, anio: int) -> Path:
    return dir_crudos / CORTES[anio]


def ruta_limites(dir_crudos: Path) -> Path:
    """mun23gw.shp (CONABIO) o, si no está, 31mun.shp del Marco Geoestadístico 2023."""
    return (alm.buscar(dir_crudos, "mun23gw.shp", requerido=False)
            or alm.buscar(dir_crudos, "31mun.shp"))


# ---------------------------------------------------------------------------
# Validación de crudos (antes de dar por buena una partición de bronce)
# ---------------------------------------------------------------------------

def validar_denue(ruta: Path) -> None:
    alm.validar_archivo(ruta)
    with zipfile.ZipFile(ruta) as zf:
        if CSV_EN_ZIP not in zf.namelist():
            raise ValueError(f"{ruta.name}: no trae {CSV_EN_ZIP}")
        with zf.open(CSV_EN_ZIP) as f:
            cabecera = f.readline().decode("latin-1")
    columnas = {c.strip().strip('"').lower() for c in cabecera.split(",")}
    if faltan := COLUMNAS_DENUE - columnas:
        raise ValueError(f"{ruta.name}: faltan columnas {sorted(faltan)}")


def validar_eic(ruta: Path) -> None:
    alm.validar_archivo(ruta)
    if "02" not in pd.ExcelFile(ruta).sheet_names:
        raise ValueError(f"{ruta.name}: no trae la hoja 02")


def validar_limites(ruta: Path) -> None:
    alm.validar_archivo(ruta)
    with zipfile.ZipFile(ruta) as zf:
        nombres = {n.lower() for n in zf.namelist()}
    base = "mun23gw" if ruta.name == MUN23 else "conjunto_de_datos/31mun"
    if faltan := [e for e in (".shp", ".shx", ".dbf") if base + e not in nombres]:
        raise ValueError(f"{ruta.name}: faltan {[base + e for e in faltan]}")


def validar_crudo(ruta: Path) -> None:
    """Valida un crudo de bronce según su nombre; lanza excepción si no sirve."""
    nombre = Path(ruta).name
    if nombre.startswith("denue_"):
        validar_denue(ruta)
    elif nombre == EIC:
        validar_eic(ruta)
    elif nombre in LIMITES:
        validar_limites(ruta)
    else:
        alm.validar_archivo(ruta)


def construir_plata(dir_crudos: Path, ruta_municipios: Path | None = None,
                    fecha_obtencion: str | None = None) -> dict[str, pd.DataFrame]:
    """DENUE filtrado (puntos en EPSG:32616), población por grupo y municipios del corredor."""
    dir_crudos = Path(dir_crudos)
    partes = []
    for anio in CORTES:
        d = filtrar(leer_denue(_archivo_corte(dir_crudos, anio)))
        d["anio"] = anio
        partes.append(d[["anio", "id", "cve_mun", "grupo", "sector", "per_ocu", "personal_aprox",
                         "latitud", "longitud"]])
    denue = pd.concat(partes, ignore_index=True)
    denue["latitud"] = pd.to_numeric(denue["latitud"], errors="coerce")
    denue["longitud"] = pd.to_numeric(denue["longitud"], errors="coerce")
    con_xy = denue["latitud"].notna() & denue["longitud"].notna()
    geom = gpd.GeoSeries(gpd.points_from_xy(denue["longitud"], denue["latitud"]), crs=CRS_PUBLICACION)
    denue = gpd.GeoDataFrame(denue, geometry=geom.where(con_xy, None), crs=CRS_PUBLICACION).to_crs(CRS_TRABAJO)

    poblacion = leer_poblacion(dir_crudos / EIC).rename("poblacion_2025").rename_axis("grupo").reset_index()

    ruta_municipios = Path(ruta_municipios) if ruta_municipios else ruta_limites(dir_crudos)
    # mun23gw viene en UTF-8 sin .cpg; el Marco Geoestadístico declara su codificación en .cpg.
    mun = gpd.read_file(ruta_municipios, **({"encoding": "utf-8"} if ruta_municipios.stem == "mun23gw" else {}))
    mun = mun[(mun["CVE_ENT"] == CVE_ENT_YUCATAN) & mun["CVE_MUN"].isin(CORREDOR)].to_crs(CRS_TRABAJO)
    if len(mun) != len(CORREDOR):
        raise ValueError("No se encontraron los tres municipios del corredor")
    mun = mun.assign(grupo=mun["CVE_MUN"].map(CORREDOR))[["CVE_MUN", "grupo", "geometry"]]

    if fecha_obtencion is None:
        mtime = _archivo_corte(dir_crudos, ANIO_ACTUAL).stat().st_mtime
        fecha_obtencion = dt.date.fromtimestamp(mtime).isoformat()
    tablas = {"denue": denue, "poblacion": poblacion, "municipios": mun.reset_index(drop=True)}
    for t in tablas.values():
        t["fecha_obtencion"] = fecha_obtencion
    return tablas


def oro_desde_plata(denue: pd.DataFrame, poblacion: pd.DataFrame,
                    municipios: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Tabla de oro a partir de las tres tablas de plata."""
    fecha_obtencion = str(denue["fecha_obtencion"].iloc[0])
    pob = poblacion.set_index("grupo")["poblacion_2025"]

    filas = []
    for anio in CORTES:
        d = denue[denue["anio"] == anio]
        g = d.groupby("grupo").agg(establecimientos=("id", "size"), personal_aprox=("personal_aprox", "sum"))
        g = g.reindex(GRUPOS).fillna(0)
        g["pct"] = 100 * g["personal_aprox"] / g["personal_aprox"].sum()
        g["anio"] = anio
        filas.append(g.reset_index())
    part = pd.concat(filas, ignore_index=True)
    part["poblacion_2025"] = part["grupo"].map(pob)
    part["capa"] = "participacion"
    part["geometry"] = None

    actual = denue[(denue["anio"] == ANIO_ACTUAL) & (denue["grupo"] != RESTO)]
    puntos = gpd.GeoDataFrame(
        pd.DataFrame(actual[["grupo", "sector", "per_ocu", "personal_aprox"]]).assign(anio=ANIO_ACTUAL),
        geometry=gpd.points_from_xy(actual["longitud"], actual["latitud"]),
        crs=CRS_PUBLICACION,
    )
    puntos["capa"] = "establecimiento"

    mun = municipios.to_crs(CRS_TRABAJO).copy()
    mun["geometry"] = mun.geometry.simplify(TOLERANCIA_CONTORNO_M, preserve_topology=True)
    contornos = mun.to_crs(CRS_PUBLICACION)[["grupo", "geometry"]]
    contornos["capa"] = "contorno"

    oro = gpd.GeoDataFrame(
        pd.concat([part, puntos, contornos], ignore_index=True),
        geometry="geometry",
        crs=CRS_PUBLICACION,
    )
    oro["pct"] = oro["pct"].round(4)
    oro["anio"] = oro["anio"].astype("Int64")

    oro.insert(0, "viz_id", VIZ_ID)
    oro["fuente_primaria"] = FUENTE_PRIMARIA
    oro["fuente_secundaria"] = FUENTE_SECUNDARIA
    oro["institucion"] = INSTITUCION
    oro["fecha_obtencion"] = fecha_obtencion
    oro["responsable"] = RESPONSABLE
    columnas = [
        "viz_id", "capa", "anio", "grupo", "sector", "per_ocu", "establecimientos",
        "personal_aprox", "pct", "poblacion_2025", "fuente_primaria", "fuente_secundaria",
        "institucion", "fecha_obtencion", "responsable", "geometry",
    ]
    return oro[columnas]


def construir_oro(dir_crudos: Path, ruta_municipios: Path, fecha_obtencion: str | None = None) -> gpd.GeoDataFrame:
    """Prueba local: crudos -> plata -> oro en memoria."""
    p = construir_plata(dir_crudos, ruta_municipios, fecha_obtencion)
    return oro_desde_plata(p["denue"], p["poblacion"], p["municipios"])


def resumen(oro: pd.DataFrame) -> pd.DataFrame:
    """% del personal aproximado por grupo y corte, más el total del corredor."""
    p = oro[oro["capa"] == "participacion"].pivot_table(index="anio", columns="grupo", values="pct")
    p = p[GRUPOS]
    p["Corredor"] = p[["Mérida", "Umán", "Hunucmá"]].sum(axis=1)
    return p.round(1)


def valor_referencia(oro: pd.DataFrame) -> float:
    """% del personal aproximado del corredor en 2026 (valor del catálogo)."""
    return float(round(resumen(oro).loc[ANIO_ACTUAL, "Corredor"], 1))


# ---------------------------------------------------------------------------
# Etapas del DAG
# ---------------------------------------------------------------------------

def _completar_limites(destino: str) -> None:
    """Deja en bronce un ZIP de límites municipales válido: mun23gw.zip (CONABIO)
    o, si CONABIO no responde, el Marco Geoestadístico 2023 del INEGI."""
    malos = alm.invalidos_en_bronce(destino, LIMITES, validar_crudo)
    if len(malos) < len(LIMITES):
        return  # al menos uno ya está y es válido
    errores = []
    for nombre, url in LIMITES.items():
        try:
            alm.completar_urls(destino, {nombre: url}, validar=validar_crudo)
            return
        except Exception as error:
            log.warning("No se pudo bajar %s de %s: %s", nombre, url, error)
            errores.append(f"{url}: {type(error).__name__}: {error}")
    raise RuntimeError("No se pudieron obtener los límites municipales: " + " | ".join(errores))


def ingesta(fecha: str | None = None, carpeta_local: str | Path | None = None) -> str:
    """Fuentes con enlace directo -> bronce/6/corredor_industrial/fecha=AAAA-MM-DD/.

    Aunque la partición `fecha=` ya exista, cada archivo esperado (cuatro DENUE,
    la Intercensal y los límites) se baja de MinIO y se valida: ZIP o XLSX
    íntegro, el CSV del DENUE con sus columnas, la hoja 02 de la Intercensal y
    el shapefile completo. Lo que falta o no sirve se borra y se descarga de
    nuevo; una página HTML en lugar del archivo hace fallar la ingesta.

    Si se da una carpeta de crudos (argumento o E6_CRUDOS_CORREDOR_INDUSTRIAL),
    se sube esa carpeta y se aplica la misma revisión.
    """
    urls = {Path(URLS[k]).name: URLS[k] for k in CORTES}
    urls[EIC] = URLS["eic"]
    local = alm.carpeta_local(DATASET, carpeta_local)
    destino = (alm.ingestar_carpeta_local(DATASET, local, fecha) if local is not None
               else alm.prefijo(DATASET, fecha or alm.hoy()))
    descargados = alm.completar_urls(destino, urls, validar=validar_crudo)
    _completar_limites(destino)
    log.info("%s: bronce verificado en %s (descargados de nuevo: %s)", DATASET, destino, descargados or "ninguno")
    return destino


def plata(prefijo: str | None = None) -> int:
    """Bronce -> plata."6.corredor_industrial.*"."""
    nombres = [*CORTES.values(), EIC, *LIMITES]
    filtro = "^(" + "|".join(re.escape(n) for n in nombres) + ")$"
    with alm.crudos(DATASET, prefijo, filtro=filtro, bajar_zips=True) as (carpeta, fecha):
        tablas = construir_plata(carpeta, None, fecha)
    alm.cargar({TABLAS_PLATA[k]: t for k, t in tablas.items()}, alm.ESQUEMA_PLATA)
    return sum(len(t) for t in tablas.values())


def oro() -> float:
    """plata -> oro."6.corredor_industrial". Devuelve la cifra que se contrasta con el catálogo."""
    p = {k: alm.leer(t, alm.ESQUEMA_PLATA) for k, t in TABLAS_PLATA.items()}
    tabla = oro_desde_plata(p["denue"], p["poblacion"], p["municipios"])
    alm.cargar({VIZ_ID: tabla}, alm.ESQUEMA_ORO)
    return valor_referencia(tabla)


if __name__ == "__main__":
    # Prueba local explícita: python pipelines/6/corredor_industrial.py <crudos> <mun23gw.shp>
    if len(sys.argv) < 3:
        sys.exit("Uso: corredor_industrial.py <carpeta_de_crudos> <mun23gw.shp>  "
                 "(en producción corre el DAG equipo_6)")
    tabla = construir_oro(Path(sys.argv[1]), Path(sys.argv[2]))
    print(resumen(tabla))
    print("valor_referencia:", valor_referencia(tabla))
