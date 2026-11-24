"""Tabla de oro de 6.relieve_5m.

Relieve y altura edificada de la zona metropolitana de Mérida vistos desde
modelos de elevación de 5 m.

Fuentes:

- Primaria: INEGI, Modelos Digitales de Elevación de 5 m (tipo superficie, MDS,
  y tipo terreno, MDT) a partir de imágenes de satélite, cartas 1:10 000.
  Se usan 15 cartas en parejas `fXXXXXX_ms.xyz` / `fXXXXXX_mt.xyz`.
- Secundaria: Overture Maps Foundation, tema buildings (huellas de edificios).
- Secundaria: INEGI, DENUE, corte de mayo de 2026, Yucatán (clave 31).

Lo que se sabe de los crudos (verificado al abrirlos):

- Cada XYZ es texto con "x y z" separados por espacio, en UTM zona 16 norte
  (ITRF08 época 2010.0, alturas NAVD88), centros de celda a 5 m (x.5).
  Se trata como EPSG:32616; la diferencia ITRF08 contra WGS84 es submétrica.
- Las carpetas no siempre dicen si traen MDS o MDT; manda el nombre del
  archivo (`_ms` o `_mt`).
- Cada carta trae 150 m de traslape con sus vecinas. Cada píxel de 5 m se
  toma solo una vez, de la primera carta que lo trae.
- La cobertura de las 15 cartas no es un rectángulo: hay huecos en las
  esquinas. Solo entran a la malla las celdas cubiertas por el MDE.

Método:

1. El MDE se procesa carta por carta (no se arma el mosaico de 5 m en memoria).
   Altura sobre el terreno = MDS - MDT. Los valores negativos son ruido de la
   correlación fotogramétrica y se descartan.
2. Altura de cada edificio de Overture: mediana de los píxeles de 5 m cuyo
   centro cae dentro de la huella. Si la huella es tan chica que no contiene
   ningún centro de píxel, se toma el píxel donde cae su punto representativo.
   El % de edificios de menos de 5 m se calcula sobre estos edificios, antes
   de agregar a la malla.
3. Malla compartida de 200 m en EPSG:32616, alineada a múltiplos de 200 m.
   Cada edificio se asigna a la celda de su punto representativo. Por celda:
   huella construida (m²), altura edificada (promedio de las alturas de sus
   edificios, ponderado por la huella), relieve (MDT medio) y negocios del
   DENUE. Celdas urbanas: las que tienen al menos 5% de su área construida
   (2,000 m² de huella de Overture en la celda de 200 x 200 m). El % de
   edificios de menos de 5 m se calcula con los edificios de esas celdas.

La tabla de oro es un GeoDataFrame en EPSG:4326, en formato largo con `capa`:

- `celda`:   una fila por celda de 200 m (polígono), urbana o no.
- `resumen`: una fila con el % de edificios de menos de 5 m y los conteos.

El ráster de 5 m nunca sale del pipeline: la tabla de oro solo trae la malla.
"""

from __future__ import annotations

import datetime as dt
import io
import re
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

VIZ_ID = "6.relieve_5m"
CRS_TRABAJO = 32616
CRS_PUBLICACION = 4326
CVE_ENT_YUCATAN = "31"

RESOLUCION_M = 5
CELDA_M = 200
PIXELES_POR_CELDA = (CELDA_M // RESOLUCION_M) ** 2
COBERTURA_MINIMA = 0.95  # fracción de la celda con MDE para entrar a la malla
UMBRAL_ALTURA_M = 5.0
HUELLA_MINIMA_PCT = 5.0  # celda urbana: >= 5% del área construida
HUELLA_MINIMA_M2 = HUELLA_MINIMA_PCT / 100 * CELDA_M ** 2  # 2,000 m²
LOTE_PUNTOS = 250_000

URLS = {
    "mde": "https://www.inegi.org.mx/app/geo2/elevacionesmex/",
    "overture": "https://docs.overturemaps.org/guides/buildings/",
    "denue": "https://www.inegi.org.mx/contenidos/masiva/denue/denue_31_csv.zip",
}

FUENTE_PRIMARIA = (
    "INEGI: Modelos Digitales de Elevación de 5 m, tipo superficie y tipo terreno "
    "(imágenes de satélite), 15 cartas 1:10 000 de la zona metropolitana de Mérida"
)
FUENTE_SECUNDARIA = (
    "Overture Maps Foundation: huellas de edificios (tema buildings); "
    "INEGI: DENUE, corte de mayo de 2026, Yucatán"
)
INSTITUCION = "INEGI; Overture Maps Foundation"
RESPONSABLE = "Gio Soriano"

PATRON_XYZ = re.compile(r"^(f\d{2}c\d{2}[a-f]\d)_(ms|mt)\.xyz$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# MDE
# ---------------------------------------------------------------------------

def listar_cartas(dir_cartas: Path) -> dict[str, dict[str, Path]]:
    """Empareja los XYZ por carta según el nombre del archivo, no de la carpeta."""
    cartas: dict[str, dict[str, Path]] = {}
    for ruta in sorted(Path(dir_cartas).rglob("*.xyz")):
        m = PATRON_XYZ.match(ruta.name)
        if m:
            cartas.setdefault(m.group(1).upper(), {})[m.group(2).lower()] = ruta
    incompletas = [c for c, r in cartas.items() if set(r) != {"ms", "mt"}]
    if incompletas:
        raise ValueError(f"Cartas sin pareja MDS/MDT: {incompletas}")
    if not cartas:
        raise FileNotFoundError(f"No hay archivos *_ms.xyz / *_mt.xyz en {dir_cartas}")
    return cartas


def leer_xyz(ruta: Path) -> pd.DataFrame:
    df = pd.read_csv(ruta, sep=r"\s+", header=None, names=["x", "y", "z"],
                     dtype={"x": "float64", "y": "float64", "z": "float32"}, engine="c")
    if df.empty:
        raise ValueError(f"{ruta.name}: archivo vacío")
    return df


def extension_xyz(ruta: Path) -> tuple[float, float, float, float]:
    """Extensión de un XYZ sin guardarlo entero (solo x y y)."""
    xy = pd.read_csv(ruta, sep=r"\s+", header=None, usecols=[0, 1], dtype="float64", engine="c")
    return xy[0].min(), xy[1].min(), xy[0].max(), xy[1].max()


class Reticula:
    """Reticula global de 5 m alineada a la malla de 200 m."""

    def __init__(self, x0: float, y0: float, x1: float, y1: float):
        self.x0 = np.floor(x0 / CELDA_M) * CELDA_M
        self.y0 = np.floor(y0 / CELDA_M) * CELDA_M
        self.columnas = int(np.ceil((x1 - self.x0) / CELDA_M))
        self.filas = int(np.ceil((y1 - self.y0) / CELDA_M))
        lado = CELDA_M // RESOLUCION_M
        self.nx, self.ny = self.columnas * lado, self.filas * lado
        self.tomado = np.zeros((self.ny, self.nx), dtype=bool)

    def indices(self, x, y):
        ix = np.floor((np.asarray(x) - self.x0) / RESOLUCION_M).astype(np.int64)
        iy = np.floor((np.asarray(y) - self.y0) / RESOLUCION_M).astype(np.int64)
        return ix, iy

    def celda(self, x, y):
        col = np.floor((np.asarray(x) - self.x0) / CELDA_M).astype(np.int64)
        fil = np.floor((np.asarray(y) - self.y0) / CELDA_M).astype(np.int64)
        return fil, col


def ndsm_carta(rutas: dict[str, Path], reticula: Reticula) -> pd.DataFrame:
    """MDS - MDT de una carta, solo en píxeles que ninguna carta anterior tomó.

    Devuelve x, y del centro del píxel, mdt y altura (NaN si es negativa).
    """
    ms = leer_xyz(rutas["ms"])
    mt = leer_xyz(rutas["mt"])
    for df in (ms, mt):
        df["ix"], df["iy"] = reticula.indices(df["x"], df["y"])
    pix = mt[["x", "y", "ix", "iy", "z"]].rename(columns={"z": "mdt"}).merge(
        ms[["ix", "iy", "z"]].rename(columns={"z": "mds"}), on=["ix", "iy"], how="inner"
    )
    del ms, mt
    dentro = (pix.ix >= 0) & (pix.ix < reticula.nx) & (pix.iy >= 0) & (pix.iy < reticula.ny)
    pix = pix[dentro]
    nuevo = ~reticula.tomado[pix.iy.values, pix.ix.values]
    pix = pix[nuevo].reset_index(drop=True)
    reticula.tomado[pix.iy.values, pix.ix.values] = True
    altura = (pix["mds"] - pix["mdt"]).astype("float32")
    pix["altura"] = altura.where(altura >= 0)
    return pix[["x", "y", "ix", "iy", "mdt", "altura"]]


# ---------------------------------------------------------------------------
# Edificios
# ---------------------------------------------------------------------------

def leer_edificios(ruta: Path) -> gpd.GeoDataFrame:
    edif = gpd.read_parquet(ruta, columns=["id", "geometry"]).to_crs(CRS_TRABAJO)
    edif = edif[edif.geometry.notna() & ~edif.geometry.is_empty].reset_index(drop=True)
    edif["area_m2"] = edif.geometry.area
    punto = edif.geometry.representative_point()
    edif["px"], edif["py"] = punto.x.values, punto.y.values
    return edif


def alturas_edificios(cartas: dict[str, dict[str, Path]], edif: gpd.GeoDataFrame,
                      reticula: Reticula, verbose: bool = True) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Recorre las cartas una por una.

    Devuelve:
    - DataFrame por edificio con `altura_m` (mediana) y `pixeles`;
    - pixeles con MDE por celda (cobertura) y suma de MDT por celda.
    """
    arbol = shapely.STRtree(edif.geometry.values)
    pares_edif, pares_h = [], []
    respaldo = np.full(len(edif), np.nan, dtype="float32")
    cobertura = np.zeros((reticula.filas, reticula.columnas), dtype=np.int64)
    suma_mdt = np.zeros((reticula.filas, reticula.columnas), dtype=np.float64)
    pix_ix_edif, pix_iy_edif = reticula.indices(edif["px"].values, edif["py"].values)
    en_reticula = (pix_ix_edif >= 0) & (pix_ix_edif < reticula.nx) & (pix_iy_edif >= 0) & (pix_iy_edif < reticula.ny)
    buscado = pix_iy_edif * reticula.nx + pix_ix_edif
    lado = CELDA_M // RESOLUCION_M

    for n, (carta, rutas) in enumerate(sorted(cartas.items()), 1):
        pix = ndsm_carta(rutas, reticula)
        fil, col = pix.iy.values // lado, pix.ix.values // lado
        np.add.at(cobertura, (fil, col), 1)
        np.add.at(suma_mdt, (fil, col), pix["mdt"].values.astype(np.float64))

        validos = pix[pix["altura"].notna()]
        # Píxel bajo el punto representativo, para huellas sin centros de píxel.
        clave = validos.iy.values.astype(np.int64) * reticula.nx + validos.ix.values
        orden = np.argsort(clave)
        clave, alt_ord = clave[orden], validos["altura"].values[orden]
        if len(clave):
            pos = np.clip(np.searchsorted(clave, buscado), 0, len(clave) - 1)
            hallado = en_reticula & (clave[pos] == buscado)
            respaldo[hallado] = alt_ord[pos[hallado]]

        # Centros de píxel dentro de huellas.
        xs, ys, hs = validos["x"].values, validos["y"].values, validos["altura"].values
        for i in range(0, len(xs), LOTE_PUNTOS):
            puntos = shapely.points(xs[i:i + LOTE_PUNTOS], ys[i:i + LOTE_PUNTOS])
            idx_p, idx_e = arbol.query(puntos, predicate="within")
            pares_edif.append(idx_e.astype(np.int32))
            pares_h.append(hs[i:i + LOTE_PUNTOS][idx_p])
            del puntos
        if verbose:
            print(f"  [{n:>2}/{len(cartas)}] {carta}: {len(pix):,} píxeles nuevos, "
                  f"{len(pix) - len(validos):,} negativos descartados", flush=True)
        del pix, validos

    pares = pd.DataFrame({"edif": np.concatenate(pares_edif), "h": np.concatenate(pares_h)})
    por_edif = pares.groupby("edif")["h"].agg(["median", "size"])
    alturas = pd.DataFrame({"altura_m": np.nan, "pixeles": 0}, index=edif.index)
    alturas.loc[por_edif.index, "altura_m"] = por_edif["median"].values
    alturas.loc[por_edif.index, "pixeles"] = por_edif["size"].values
    sin_pixel = alturas["pixeles"].eq(0)
    alturas.loc[sin_pixel, "altura_m"] = respaldo[sin_pixel.values]
    return alturas, cobertura, suma_mdt


# ---------------------------------------------------------------------------
# DENUE
# ---------------------------------------------------------------------------

def leer_denue_puntos(ruta: Path) -> gpd.GeoDataFrame:
    """Establecimientos del DENUE Yucatán con coordenadas (CSV suelto o ZIP)."""
    ruta = Path(ruta)
    if ruta.suffix.lower() == ".zip":
        with zipfile.ZipFile(ruta) as zf:
            crudo = zf.read("conjunto_de_datos/denue_inegi_31_.csv")
    else:
        crudo = ruta.read_bytes()
    try:
        texto = crudo.decode("utf-8")
    except UnicodeDecodeError:
        texto = crudo.decode("latin-1")
    df = pd.read_csv(io.StringIO(texto), dtype=str, usecols=["id", "cve_ent", "cve_mun", "latitud", "longitud"])
    if set(df["cve_ent"].unique()) != {CVE_ENT_YUCATAN}:
        raise ValueError(f"{ruta.name}: trae entidades distintas de Yucatán")
    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
    df = df.dropna(subset=["latitud", "longitud"])
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitud, df.latitud),
                            crs=CRS_PUBLICACION).to_crs(CRS_TRABAJO)


# ---------------------------------------------------------------------------
# Malla y tabla de oro
# ---------------------------------------------------------------------------

def construir_malla(dir_cartas: Path, ruta_edificios: Path, ruta_denue: Path,
                    verbose: bool = True) -> tuple[pd.DataFrame, dict]:
    """Malla de 200 m en EPSG:32616 (DataFrame) y cifras por edificio."""
    cartas = listar_cartas(dir_cartas)
    extensiones = np.array([extension_xyz(r["mt"]) for r in cartas.values()])
    x0, y0 = extensiones[:, 0].min(), extensiones[:, 1].min()
    x1, y1 = extensiones[:, 2].max(), extensiones[:, 3].max()
    reticula = Reticula(x0, y0, x1, y1)
    if verbose:
        print(f"{len(cartas)} cartas; retícula {reticula.filas} x {reticula.columnas} celdas de {CELDA_M} m")

    edif = leer_edificios(ruta_edificios)
    alturas, cobertura, suma_mdt = alturas_edificios(cartas, edif, reticula, verbose)
    del reticula.tomado
    edif = edif.drop(columns="geometry").join(alturas)
    edif["fila"], edif["columna"] = reticula.celda(edif["px"], edif["py"])

    # Solo celdas cubiertas por el MDE; los edificios fuera de ellas no cuentan.
    filas, columnas = np.indices(cobertura.shape)
    malla = pd.DataFrame({
        "fila": filas.ravel(), "columna": columnas.ravel(),
        "cobertura": cobertura.ravel() / PIXELES_POR_CELDA,
        "mdt_m": np.where(cobertura.ravel() > 0, suma_mdt.ravel() / np.maximum(cobertura.ravel(), 1), np.nan),
    })
    malla = malla[malla["cobertura"] >= COBERTURA_MINIMA].reset_index(drop=True)
    dentro = edif.merge(malla[["fila", "columna"]], on=["fila", "columna"], how="inner")

    con_altura = dentro[dentro["altura_m"].notna()]
    dentro["h_x_area"] = dentro["altura_m"] * dentro["area_m2"]
    dentro["area_con_h"] = dentro["area_m2"].where(dentro["altura_m"].notna())
    agg = dentro.groupby(["fila", "columna"]).agg(
        edificios=("id", "size"), huella_m2=("area_m2", "sum"),
        h_x_area=("h_x_area", "sum"), area_con_h=("area_con_h", "sum"),
        menores_5m=("altura_m", lambda s: int((s < UMBRAL_ALTURA_M).sum())),
    ).reset_index()
    agg["altura_m"] = agg["h_x_area"] / agg["area_con_h"].where(agg["area_con_h"] > 0)
    malla = malla.merge(agg.drop(columns=["h_x_area", "area_con_h"]), on=["fila", "columna"], how="left")

    denue = leer_denue_puntos(ruta_denue)
    fil_d, col_d = reticula.celda(denue.geometry.x.values, denue.geometry.y.values)
    negocios = pd.DataFrame({"fila": fil_d, "columna": col_d}).value_counts().rename("negocios").reset_index()
    malla = malla.merge(negocios, on=["fila", "columna"], how="left")

    for c in ("edificios", "menores_5m", "negocios"):
        malla[c] = malla[c].fillna(0).astype(int)
    malla["huella_m2"] = malla["huella_m2"].fillna(0.0)
    malla["huella_pct"] = 100 * malla["huella_m2"] / CELDA_M ** 2
    malla["urbana"] = malla["huella_m2"] >= HUELLA_MINIMA_M2
    malla["x_utm"] = reticula.x0 + (malla["columna"] + 0.5) * CELDA_M
    malla["y_utm"] = reticula.y0 + (malla["fila"] + 0.5) * CELDA_M

    menores_malla = int((con_altura["altura_m"] < UMBRAL_ALTURA_M).sum())
    urbanas = malla.loc[malla["urbana"], ["fila", "columna"]]
    con_altura = con_altura.merge(urbanas, on=["fila", "columna"], how="inner")
    menores = int((con_altura["altura_m"] < UMBRAL_ALTURA_M).sum())
    cifras = {
        "cartas": len(cartas),
        "edificios_overture": len(edif),
        "edificios_en_malla": len(dentro),
        "pct_menores_5m_toda_la_malla": 100 * menores_malla / int(dentro["altura_m"].notna().sum()),
        "edificios_con_altura": len(con_altura),
        "edificios_sin_altura": int(dentro["altura_m"].isna().sum()),
        "edificios_por_respaldo": int((con_altura["pixeles"] == 0).sum()),
        "edificios_menores_5m": menores,
        "pct_menores_5m": 100 * menores / len(con_altura),
        "altura_mediana_m": float(con_altura["altura_m"].median()),
        "negocios_denue_yucatan": len(denue),
        "negocios_en_malla": int(malla["negocios"].sum()),
        "negocios_en_celdas_urbanas": int(malla.loc[malla.urbana, "negocios"].sum()),
        "celdas": len(malla),
        "celdas_urbanas": int(malla["urbana"].sum()),
        "filas": int(malla["fila"].max() - malla["fila"].min() + 1),
        "columnas": int(malla["columna"].max() - malla["columna"].min() + 1),
        "origen_utm": (float(reticula.x0), float(reticula.y0)),
    }
    return malla, cifras


def _poligonos(malla: pd.DataFrame) -> gpd.GeoSeries:
    medio = CELDA_M / 2
    cajas = shapely.box(malla.x_utm - medio, malla.y_utm - medio, malla.x_utm + medio, malla.y_utm + medio)
    return gpd.GeoSeries(cajas, crs=CRS_TRABAJO).to_crs(CRS_PUBLICACION)


def construir_oro(dir_cartas: Path, ruta_edificios: Path, ruta_denue: Path,
                  fecha_obtencion: str | None = None, verbose: bool = True) -> gpd.GeoDataFrame:
    malla, cifras = construir_malla(dir_cartas, ruta_edificios, ruta_denue, verbose)

    celdas = malla.copy()
    celdas["capa"] = "celda"
    for c in ("huella_m2", "huella_pct", "altura_m", "mdt_m", "cobertura"):
        celdas[c] = celdas[c].round(3)
    geom = _poligonos(celdas)

    resumen = pd.DataFrame([{
        "capa": "resumen",
        "edificios": cifras["edificios_con_altura"],
        "menores_5m": cifras["edificios_menores_5m"],
        "pct_menores_5m": round(cifras["pct_menores_5m"], 2),
        "altura_mediana_m": round(cifras["altura_mediana_m"], 2),
        "negocios": cifras["negocios_en_malla"],
        "celdas": cifras["celdas"],
        "celdas_urbanas": cifras["celdas_urbanas"],
    }])
    oro = pd.concat([celdas, resumen], ignore_index=True)
    oro = gpd.GeoDataFrame(oro, geometry=list(geom) + [None], crs=CRS_PUBLICACION)
    for c in ("fila", "columna", "edificios", "menores_5m", "negocios", "celdas", "celdas_urbanas"):
        oro[c] = oro[c].astype("Int64")
    oro["urbana"] = oro["urbana"].astype("boolean")

    if fecha_obtencion is None:
        primera = sorted(Path(dir_cartas).rglob("*_ms.xyz"))[0]
        fecha_obtencion = dt.date.fromtimestamp(primera.stat().st_mtime).isoformat()
    oro.insert(0, "viz_id", VIZ_ID)
    oro["fuente_primaria"] = FUENTE_PRIMARIA
    oro["fuente_secundaria"] = FUENTE_SECUNDARIA
    oro["institucion"] = INSTITUCION
    oro["fecha_obtencion"] = fecha_obtencion
    oro["responsable"] = RESPONSABLE
    columnas = [
        "viz_id", "capa", "fila", "columna", "x_utm", "y_utm", "cobertura", "urbana",
        "edificios", "menores_5m", "huella_m2", "huella_pct", "altura_m", "mdt_m", "negocios",
        "pct_menores_5m", "altura_mediana_m", "celdas", "celdas_urbanas",
        "fuente_primaria", "fuente_secundaria", "institucion", "fecha_obtencion", "responsable", "geometry",
    ]
    oro = oro[columnas]
    oro.attrs["cifras"] = cifras
    return oro


def valor_referencia(oro: pd.DataFrame) -> float:
    """% de edificios de menos de 5 m (calculado por edificio, no por celda)."""
    fila = oro[oro["capa"] == "resumen"].iloc[0]
    return round(float(fila["pct_menores_5m"]), 1)
