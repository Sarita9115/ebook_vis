"""Tabla de oro de 6.obra_publica.

Obra pública e infraestructura para el desarrollo económico por municipio de Yucatán.

Fuentes (bronce: bronze/6/<dataset>/fecha=AAAA-MM-DD/):

- Primaria:   SSOP Yucatán, mapa de obras (obras_ssop: obras_mapa_<año>.json).
- Secundaria: INEGI, Encuesta Intercensal 2025 (poblacion_eic2025: eic2025_poblacion_31.xlsx), Marco
              Geoestadístico (marco_geoestadistico: capa municipal, zip o archivos sueltos) e INPC (inpc: CSV mensual).

Plata:
- plata."6.obra_publica"            una fila por obra, con el municipio que le toca por su ubicación.
- plata."6.obra_publica_municipios" capa municipal de Yucatán (geometría EPSG:4326).
- plata."6.obra_publica_poblacion"  población de cada municipio.
- plata."6.obra_publica_inpc"       INPC promedio por año.

Oro: una fila por municipio con `poblacion`, `monto` (pesos de 2025, sin la obra que pesa más de 10% del total),
`obras` y `geometry` (EPSG:4326, simplificada para el mapa).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import re

import numpy as np
import pandas as pd


def _cargar(nombre: str, archivo: str):
    """Carga un módulo hermano de pipelines/6/ por ruta (la carpeta "6" no es un paquete)."""
    if nombre not in sys.modules:
        spec = importlib.util.spec_from_file_location(nombre, Path(__file__).with_name(archivo))
        modulo = importlib.util.module_from_spec(spec)
        sys.modules[nombre] = modulo
        spec.loader.exec_module(modulo)
    return sys.modules[nombre]


alm = _cargar("e6_almacen", "_almacen.py")
L = _cargar("e6_limpieza", "_limpieza.py")


VIZ_ID = "6.obra_publica"
SUBTEMA = "obra_publica"
DATASETS = ["obras_ssop", "marco_geoestadistico", "poblacion_eic2025", "inpc"]
TABLA_OBRAS = VIZ_ID
TABLA_MUNICIPIOS = f"{VIZ_ID}_municipios"
TABLA_POBLACION = f"{VIZ_ID}_poblacion"
TABLA_INPC = f"{VIZ_ID}_inpc"
ANIO_BASE_PESOS = 2025
SIMPLIFICAR = 0.002  # grados, para el mapa

FUENTE_PRIMARIA = "Secretaría de Obras Públicas de Yucatán (SSOP), mapa de obras"
FUENTE_SECUNDARIA = "INEGI, Encuesta Intercensal 2025 (población), INPC y Marco Geoestadístico"
INSTITUCION = "SSOP Yucatán e INEGI"
RESPONSABLE = "Arturo"


def ingesta(fecha: str | None = None, carpeta_local: str | Path | None = None) -> dict:
    return L.ingerir(alm, DATASETS, fecha, carpeta_local)


def _capa_municipal(carpeta: Path):
    """Municipios de Yucatán (CVE_MUN de 3 dígitos, NOMGEO, geometry) en el CRS original del Marco Geoestadístico."""
    import geopandas as gpd

    capas = L.buscar(carpeta, "shp", r"mun")
    if not capas:
        raise FileNotFoundError("El Marco Geoestadístico en bronce no trae una capa municipal (*mun*.shp)")
    mun = gpd.read_file(capas[0])
    if "CVE_ENT" in mun.columns:
        mun = mun[mun.CVE_ENT.astype(str).str.zfill(2) == "31"]
    mun = mun.copy()
    mun["CVE_MUN"] = mun["CVE_MUN"].astype(str).str[-3:].str.zfill(3)
    return mun[["CVE_MUN", "NOMGEO", "geometry"]].reset_index(drop=True)


def _a_numero(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[$,\s]", "", regex=True), errors="coerce")


def _punto_representativo(coords):
    """Una obra puede traer 1 punto o cientos (calles, caminos). Se usa el promedio de los puntos válidos."""
    lat, lng = [], []
    for q in coords or []:
        try:
            a, b = float(q["lat"]), float(q["lng"])
        except (KeyError, TypeError, ValueError):
            continue
        if L.BBOX_YUCATAN["lat"][0] <= a <= L.BBOX_YUCATAN["lat"][1] and L.BBOX_YUCATAN["lng"][0] <= b <= L.BBOX_YUCATAN["lng"][1]:
            lat.append(a)
            lng.append(b)
    if not lat:
        return pd.Series({"lat": np.nan, "lng": np.nan, "n_puntos": 0})
    return pd.Series({"lat": float(np.mean(lat)), "lng": float(np.mean(lng)), "n_puntos": len(lat)})


def _obras(carpeta: Path, mun) -> pd.DataFrame:
    import json

    import geopandas as gpd

    archivos = L.buscar(carpeta, "json", r"obras_mapa_")
    if not archivos:
        raise FileNotFoundError("En bronce no hay archivos obras_mapa_<año>.json")
    partes = []
    for a in archivos:
        df = pd.json_normalize(json.loads(a.read_text(encoding="utf-8-sig")))
        df["costo_num"] = _a_numero(df["obra.costo"])
        pts = df["coord"].apply(_punto_representativo)
        df = pd.concat([df, pts], axis=1).sort_values(["obra.obraid", "n_puntos"], ascending=[True, False])
        # El mismo obraid se repite en varias filas (una por contrato o punto): se queda el costo mayor.
        agg = df.groupby("obra.obraid").agg(
            anio=("obra.anio", "first"), nombre=("obra.nombre", "first"), tipo=("obra.apertura", "first"),
            dependencia=("obra.dependencia", "first"), estatus=("obra.estatus", "first"),
            avfisico=("obra.avfisico", "first"), avfinan=("obra.avfinan", "first"),
            finicio=("obra.finicio", "first"), ftermino=("obra.ftermino", "first"),
            costo=("costo_num", "max"), lat=("lat", "first"), lng=("lng", "first"), n_puntos=("n_puntos", "first"),
        ).reset_index().rename(columns={"obra.obraid": "obraid"})
        partes.append(agg)
    obras = pd.concat(partes, ignore_index=True)
    obras["anio"] = pd.to_numeric(obras["anio"], errors="coerce").astype("Int64")
    for c in ("avfisico", "avfinan"):
        obras[c] = pd.to_numeric(obras[c], errors="coerce")
    for c in ("finicio", "ftermino"):
        obras[c] = pd.to_datetime(obras[c], format="%d/%m/%Y", errors="coerce")
    obras["costo_cero"] = obras["costo"].fillna(0).eq(0)  # «sin monto», no «gratis»
    obras["nombre"] = obras["nombre"].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    obras = obras.reset_index(drop=True)

    # Municipio por ubicación: dentro del polígono o, en costa y límites, el más cercano a menos de 3 km.
    con = obras.dropna(subset=["lat", "lng"])
    pts = gpd.GeoDataFrame(con, geometry=gpd.points_from_xy(con.lng, con.lat), crs=4326).to_crs(mun.crs)
    j = gpd.sjoin(pts, mun, how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    fuera = j[j["NOMGEO"].isna()]
    if len(fuera):
        cerca = gpd.sjoin_nearest(pts.loc[fuera.index], mun, how="left", max_distance=3000)
        cerca = cerca[~cerca.index.duplicated(keep="first")]
        j.loc[cerca.index, ["CVE_MUN", "NOMGEO"]] = cerca[["CVE_MUN", "NOMGEO"]].values
    obras["cve_mun"] = pd.Series(j["CVE_MUN"], index=j.index).reindex(obras.index)
    obras["municipio"] = pd.Series(j["NOMGEO"], index=j.index).reindex(obras.index).fillna("Sin ubicación")
    return obras.sort_values(["anio", "obraid"]).reset_index(drop=True)


def _inpc(carpeta: Path) -> pd.DataFrame:
    archivos = L.buscar(carpeta, "csv")
    if not archivos:
        raise FileNotFoundError("En bronce no hay un CSV del INPC")
    meses = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10,
             "Nov": 11, "Dic": 12}
    filas = []
    for linea in archivos[0].read_text(encoding="latin-1").splitlines():
        m = re.match(r'"(\w{3}) (\d{4})","([\d.]+)"', linea.strip())
        if m and m.group(1) in meses:
            filas.append((int(m.group(2)), meses[m.group(1)], float(m.group(3))))
    if not filas:
        raise ValueError("No encontré filas «Mes AAAA»,«valor» en el CSV del INPC")
    d = pd.DataFrame(filas, columns=["anio", "mes", "inpc"])
    return d.groupby("anio").agg(inpc_promedio=("inpc", "mean"), meses=("mes", "count")).reset_index()


def plata(prefijo: dict | None = None) -> int:
    """Bronce -> las cuatro tablas de plata del subtema."""
    p = prefijo if isinstance(prefijo, dict) else {}
    fechas = []
    with alm.crudos("marco_geoestadistico", p.get("marco_geoestadistico")) as (carpeta, fecha):
        mun = _capa_municipal(carpeta)
    fechas.append(fecha)
    with alm.crudos("obras_ssop", p.get("obras_ssop")) as (carpeta, fecha):
        obras = _obras(carpeta, mun)
    fechas.append(fecha)
    with alm.crudos("poblacion_eic2025", p.get("poblacion_eic2025")) as (carpeta, fecha):
        poblacion = L.poblacion_municipio(alm.buscar(carpeta, "eic2025_poblacion_31.xlsx"))
    fechas.append(fecha)
    with alm.crudos("inpc", p.get("inpc")) as (carpeta, fecha):
        inpc = _inpc(carpeta)
    fechas.append(fecha)

    ll = mun.to_crs(4326).rename(columns={"CVE_MUN": "cve_mun", "NOMGEO": "municipio"})
    obtencion = max(fechas)
    alm.cargar({TABLA_OBRAS: obras.assign(fecha_obtencion=obtencion),
                TABLA_MUNICIPIOS: ll.assign(fecha_obtencion=obtencion),
                TABLA_POBLACION: poblacion.assign(fecha_obtencion=obtencion),
                TABLA_INPC: inpc.assign(fecha_obtencion=obtencion)}, alm.ESQUEMA_PLATA)
    return len(obras)


def oro_desde_plata(obras, pob, inpc, mun):
    """Monto de obra por municipio en pesos de 2025. Una obra que pesa más de 10% del total se excluye."""
    import geopandas as gpd

    base = float(inpc.loc[inpc.anio == ANIO_BASE_PESOS, "inpc_promedio"].iloc[0])
    inpc = inpc.assign(factor=base / inpc.inpc_promedio)
    o = obras.merge(inpc[["anio", "factor"]], on="anio", how="left")
    o = o[o.cve_mun.notna() & ~o.costo_cero.astype(bool) & o.costo.gt(0) & o.factor.notna()].copy()
    o["monto_real"] = o.costo * o.factor
    o = o.drop(o[o.monto_real > 0.10 * o.monto_real.sum()].index)
    por = o.groupby("cve_mun").agg(monto=("monto_real", "sum"), obras=("obraid", "size")).reset_index()
    d = pob.merge(por, on="cve_mun", how="left").fillna({"monto": 0, "obras": 0})
    d = d[["cve_mun", "municipio", "poblacion", "monto", "obras"]]
    m = mun[["cve_mun", "geometry"]].copy()
    m["geometry"] = m.geometry.simplify(SIMPLIFICAR, preserve_topology=True)
    out = m.merge(d, on="cve_mun", how="inner")[["cve_mun", "municipio", "poblacion", "monto", "obras", "geometry"]]
    return gpd.GeoDataFrame(out, geometry="geometry", crs=4326)


def oro() -> float:
    """plata -> oro."6.obra_publica"."""
    obras = alm.leer(TABLA_OBRAS, alm.ESQUEMA_PLATA)
    tabla = oro_desde_plata(obras, alm.leer(TABLA_POBLACION, alm.ESQUEMA_PLATA),
                            alm.leer(TABLA_INPC, alm.ESQUEMA_PLATA), alm.leer(TABLA_MUNICIPIOS, alm.ESQUEMA_PLATA))
    tabla.insert(0, "viz_id", VIZ_ID)
    tabla["fuente_primaria"] = FUENTE_PRIMARIA
    tabla["fuente_secundaria"] = FUENTE_SECUNDARIA
    tabla["institucion"] = INSTITUCION
    tabla["fecha_obtencion"] = str(obras["fecha_obtencion"].iloc[0])
    tabla["responsable"] = RESPONSABLE
    alm.cargar({VIZ_ID: tabla}, alm.ESQUEMA_ORO)
    return valor_referencia(tabla)


def valor_referencia(oro: pd.DataFrame) -> float:
    """Pesos de 2025 de obra por habitante en el estado (valor del catálogo)."""
    return float(oro["monto"].sum() / oro["poblacion"].sum())
