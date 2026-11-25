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
  "251 y más personas". El último no tiene punto medio. Se usa 375, el punto
  medio de 251 a 500; es el valor que reproduce las cifras del boceto.
- Manufactura es SCIAN 31 a 33 y transporte y almacenamiento, 48 y 49.

La tabla de oro es un GeoDataFrame en EPSG:4326, en formato largo con `capa`:

- `participacion`:   personal aproximado y % por grupo (Mérida, Umán, Hunucmá,
                     Resto del estado) en cada corte.
- `establecimiento`: puntos del corte 2026 dentro del corredor.
- `contorno`:        polígonos simplificados de los tres municipios.
"""

from __future__ import annotations

import datetime as dt
import io
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

VIZ_ID = "6.corredor_industrial"
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


def construir_oro(dir_crudos: Path, ruta_municipios: Path, fecha_obtencion: str | None = None) -> gpd.GeoDataFrame:
    """Lee los crudos y devuelve la tabla de oro de 6.corredor_industrial."""
    dir_crudos = Path(dir_crudos)
    filtrados = {anio: filtrar(leer_denue(dir_crudos / archivo)) for anio, archivo in CORTES.items()}
    poblacion = leer_poblacion(dir_crudos / EIC)

    filas = []
    for anio, d in filtrados.items():
        g = d.groupby("grupo").agg(establecimientos=("id", "size"), personal_aprox=("personal_aprox", "sum"))
        g = g.reindex(GRUPOS).fillna(0)
        g["pct"] = 100 * g["personal_aprox"] / g["personal_aprox"].sum()
        g["anio"] = anio
        filas.append(g.reset_index())
    part = pd.concat(filas, ignore_index=True)
    part["poblacion_2025"] = part["grupo"].map(poblacion)
    part["capa"] = "participacion"
    part["geometry"] = None

    actual = filtrados[ANIO_ACTUAL]
    actual = actual[actual["grupo"] != RESTO].copy()
    actual["latitud"] = pd.to_numeric(actual["latitud"])
    actual["longitud"] = pd.to_numeric(actual["longitud"])
    puntos = gpd.GeoDataFrame(
        actual[["grupo", "sector", "per_ocu", "personal_aprox"]].assign(anio=ANIO_ACTUAL),
        geometry=gpd.points_from_xy(actual["longitud"], actual["latitud"]),
        crs=CRS_PUBLICACION,
    )
    puntos["capa"] = "establecimiento"

    mun = gpd.read_file(ruta_municipios, encoding="utf-8")
    mun = mun[(mun["CVE_ENT"] == CVE_ENT_YUCATAN) & mun["CVE_MUN"].isin(CORREDOR)].to_crs(CRS_TRABAJO)
    if len(mun) != len(CORREDOR):
        raise ValueError("No se encontraron los tres municipios del corredor")
    mun["geometry"] = mun.geometry.simplify(TOLERANCIA_CONTORNO_M, preserve_topology=True)
    contornos = mun.to_crs(CRS_PUBLICACION).assign(grupo=lambda m: m["CVE_MUN"].map(CORREDOR))
    contornos = contornos[["grupo", "geometry"]]
    contornos["capa"] = "contorno"

    oro = gpd.GeoDataFrame(
        pd.concat([part, puntos, contornos], ignore_index=True),
        geometry="geometry",
        crs=CRS_PUBLICACION,
    )
    oro["pct"] = oro["pct"].round(4)
    oro["anio"] = oro["anio"].astype("Int64")

    if fecha_obtencion is None:
        mtime = (dir_crudos / CORTES[ANIO_ACTUAL]).stat().st_mtime
        fecha_obtencion = dt.date.fromtimestamp(mtime).isoformat()

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


def resumen(oro: pd.DataFrame) -> pd.DataFrame:
    """% del personal aproximado por grupo y corte, más el total del corredor."""
    p = oro[oro["capa"] == "participacion"].pivot_table(index="anio", columns="grupo", values="pct")
    p = p[GRUPOS]
    p["Corredor"] = p[["Mérida", "Umán", "Hunucmá"]].sum(axis=1)
    return p.round(1)


def valor_referencia(oro: pd.DataFrame) -> float:
    """% del personal aproximado del corredor en 2026 (valor del catálogo)."""
    return float(round(resumen(oro).loc[ANIO_ACTUAL, "Corredor"], 1))


def validar(oro: pd.DataFrame, tolerancia: float = 1.5) -> None:
    """Contrasta 2026 contra las cifras del boceto (Mérida 59, Umán 12, Hunucmá 2, Resto 27, corredor 73)."""
    boceto = {"Mérida": 59, "Umán": 12, "Hunucmá": 2, RESTO: 27, "Corredor": 73}
    real = resumen(oro).loc[ANIO_ACTUAL]
    fuera = {k: round(real[k], 1) for k, v in boceto.items() if abs(real[k] - v) > tolerancia}
    if fuera:
        raise ValueError(f"2026 no coincide con el boceto: {fuera}")


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[2]
    crudos = Path(sys.argv[1]) if len(sys.argv) > 1 else raiz / "local_avances/datos_crudos/corredor_industrial"
    municipios = raiz / "local_avances/datos_crudos/cambio_suelo/mun23gw/mun23gw.shp"
    tabla = construir_oro(crudos, municipios)
    validar(tabla)
    print(resumen(tabla))
    print("valor_referencia:", valor_referencia(tabla))
