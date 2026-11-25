"""Tabla de oro de 6.corredor_industrial.

Concentración industrial en el corredor Mérida, Umán y Hunucmá.

Fuentes (todas de Yucatán, clave 31; el DENUE nacional no se usa):

- Primaria: DENUE, corte de mayo de 2026, Yucatán (denue_31_csv.zip, INEGI).
- Secundaria: DENUE Yucatán, cortes de noviembre de 2018, 2019 y 2020:
  https://www.inegi.org.mx/contenidos/masiva/denue/{AAAA}_11/denue_31_11{AA}_csv.zip
- Secundaria: Encuesta Intercensal 2025, población por municipio de Yucatán
  (eic2025_poblacion_31.xlsx, hoja 02).
- Límites: División política municipal 2023 (INEGI, vía CONABIO, mun23gw.zip),
  que es el Marco Geoestadístico municipal en un archivo descargable.

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
  mun23gw.zip a bronze/6/corredor_industrial/fecha=AAAA-MM-DD/. Un DENUE
  que traiga entidades distintas de Yucatán se rechaza al pasar a plata.
- `plata()`:   carga plata."6.corredor_industrial.denue" (manufactura y
  transporte con 11 o más personas, puntos en EPSG:32616),
  ".poblacion" y ".municipios" (los tres del corredor, EPSG:32616).
- `oro()`:     agrega desde plata y carga oro."6.corredor_industrial".

Nota: `denue_31_csv.zip` es el corte vigente del INEGI. El catálogo se fijó
con el de mayo de 2026; si el INEGI ya publicó otro, la cifra puede moverse
y la validación lo señalará.

Prueba local (opcional y explícita): `ingesta(carpeta_local=...)` o la variable
E6_CRUDOS_CORREDOR_INDUSTRIAL suben una carpeta de crudos a bronce en vez de
descargar (lo que falte se descarga de su URL); `construir_oro(dir_crudos,
ruta_municipios)` arma el oro en memoria desde rutas dadas.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import io
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
CORTE_VIGENTE = "denue_31_csv.zip"  # nombre con el que el INEGI publica el corte actual
CSV_EN_ZIP = "conjunto_de_datos/denue_inegi_31_.csv"
EIC = "eic2025_poblacion_31.xlsx"

URLS = {
    2018: "https://www.inegi.org.mx/contenidos/masiva/denue/2018_11/denue_31_1118_csv.zip",
    2019: "https://www.inegi.org.mx/contenidos/masiva/denue/2019_11/denue_31_1119_csv.zip",
    2020: "https://www.inegi.org.mx/contenidos/masiva/denue/2020_11/denue_31_1120_csv.zip",
    2026: "https://www.inegi.org.mx/contenidos/masiva/denue/denue_31_csv.zip",
    "eic": "https://www.inegi.org.mx/contenidos/programas/eic/2025/tabulados/eic2025_poblacion_31.xlsx",
    "mun23": "http://www.conabio.gob.mx/informacion/gis/maps/geo/mun23gw.zip",
}

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
    """Lee el CSV del ZIP por entidad; detecta UTF-8 o Latin-1."""
    with zipfile.ZipFile(ruta_zip) as zf:
        crudo = zf.read(CSV_EN_ZIP)
    try:
        crudo.decode("utf-8")
        codificacion = "utf-8"
    except UnicodeDecodeError:
        codificacion = "latin-1"
    df = pd.read_csv(io.BytesIO(crudo), dtype=str, encoding=codificacion)
    faltan = {"codigo_act", "per_ocu", "cve_ent", "cve_mun", "latitud", "longitud"} - set(df.columns)
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
    ruta = dir_crudos / CORTES[anio]
    if not ruta.exists() and anio == ANIO_ACTUAL and (dir_crudos / CORTE_VIGENTE).exists():
        ruta = dir_crudos / CORTE_VIGENTE
    return ruta


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

    ruta_municipios = Path(ruta_municipios) if ruta_municipios else alm.buscar(dir_crudos, "mun23gw.shp")
    mun = gpd.read_file(ruta_municipios, encoding="utf-8")
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

def ingesta(fecha: str | None = None, carpeta_local: str | Path | None = None) -> str:
    """Fuentes con enlace directo -> bronce.

    Si se da una carpeta de crudos (argumento o E6_CRUDOS_CORREDOR_INDUSTRIAL),
    se sube esa carpeta y solo se descarga lo que le falte.
    """
    urls = {Path(URLS[k]).name: URLS[k] for k in (*CORTES, "eic", "mun23")}
    local = alm.carpeta_local(DATASET, carpeta_local)
    if local is None:
        return alm.ingestar_urls(DATASET, urls, fecha)
    destino = alm.ingestar_carpeta_local(DATASET, local, fecha)
    if (local / CORTES[ANIO_ACTUAL]).exists():  # el corte fechado sustituye al vigente
        urls.pop(CORTE_VIGENTE)
    alm.completar_urls(destino, urls)
    return destino


def plata(prefijo: str | None = None) -> int:
    """Bronce -> plata."6.corredor_industrial.*"."""
    with alm.crudos(DATASET, prefijo, filtro=r"\.(zip|xlsx)$", bajar_zips=True) as (carpeta, fecha):
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
