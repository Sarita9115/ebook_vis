"""Equipo 2 · Plata: del bronce (MinIO, bronze/2/) a tablas limpias en PostgreSQL (esquema `plata`, EPSG:32616).

Tablas que deja (fuentes de las figuras de Esaú):

    plata."2.municipios"       municipios de Campeche, Yucatán y Quintana Roo, con `key` = CVE_ENT|nombre normalizado
    plata."2.vecinos"          países vecinos (capa de fondo de los mapas)
    plata."2.anp"              ANP federales principalmente terrestres (≥ 20 %) que tocan la península
    plata."2.censo_porcino"    cerdos y unidades de producción por municipio (Censo Agropecuario 2022)
    plata."2.denue_impacto"    negocios del DENUE con actividad que puede dañar la naturaleza, con su `tema`
    plata."2.cicy_flora"       colectas del Herbario CICY en la península (especie, municipio, estado)
    plata."2.bronce_archivos"  qué archivo de bronce se usó, con su fecha de obtención y origen

Cada ejecución reemplaza todas las tablas en una sola transacción. Uso:  python pipelines/2/plata.py
"""
from __future__ import annotations

import importlib.util
import io
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd


def _comun():
    if "equipo2_comun" not in sys.modules:
        spec = importlib.util.spec_from_file_location("equipo2_comun", Path(__file__).with_name("comun.py"))
        sys.modules["equipo2_comun"] = m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    return sys.modules["equipo2_comun"]


comun = _comun()
ESQUEMA = "plata"
CRS_M = "EPSG:32616"      # UTM 16N, distancias en metros
CRS_WEB = "EPSG:4326"
PENINSULA = ("04", "23", "31")

# Temas de negocio (mismos patrones que mapa_burbujas_reservas.ipynb)
TEMAS = [
    ("Gasolina, gas y químicos", r"peligros|gasolina|diesel|gas l\. p|gas natural|combustible|petróleo|petrol|"
                                 r"petroquímic|químic|pesticida|gases industriales|fabricación de fertilizantes"),
    ("Basura y reciclaje", r"desecho|remediación de residuos"),
    ("Campo y ganado", r"agropecuari|agricultura|alimentos para animales|agrícola|ganado|ganadería|"
                       r"plaguicida|matanza|carne de|embutidos|aserr|aprovechamiento forestal|fumigación|riego|harina"),
    ("Construcción y materiales", r"construcción|edificación|cemento|concreto|tabique|cantera|yeso|fabricación de cal|"
                                  r"minería|minerales no metálicos|urbanización|terrenos"),
    ("Pesca y mariscos", r"pesca|pescados|mariscos|camaron|acuicultura|sardina|túnidos"),
    ("Hoteles y turismo", r"hotel|casas amueblados|marinas turísticas"),
]


def norm(s) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()


def tema(clase) -> str | None:
    c = str(clase).lower()
    for nombre, patron in TEMAS:
        if re.search(patron, c):
            return nombre
    return None


# ---------------------------------------------------------------- lectura del bronce


class _Bronce:
    """Lleva la cuenta de qué objetos del bronce se leyeron, para plata."2.bronce_archivos"."""

    def __init__(self):
        self.usados = []

    def archivos(self, dataset: str, solo_fecha_reciente: bool = False) -> dict[str, dict]:
        hay = comun.ultimos(dataset)
        if not hay:
            raise LookupError(f"No hay archivos en bronze/2/{dataset}/. Corre antes la ingesta del equipo 2.")
        if solo_fecha_reciente:
            reciente = max(i["fecha"] for i in hay.values())
            hay = {n: i for n, i in hay.items() if i["fecha"] == reciente}
        return hay

    def leer(self, dataset: str, nombre: str) -> bytes:
        info = self.archivos(dataset).get(nombre)
        if info is None:
            raise LookupError(f"Falta bronze/2/{dataset}/…/{nombre}. Corre antes la ingesta del equipo 2.")
        self.usados.append(dict(dataset=dataset, archivo=nombre, objeto=info["objeto"],
                                fecha_obtencion=info["fecha"], origen=info["origen"]))
        return comun.bajar(info["objeto"])

    def capa(self, dataset: str, nombre: str, hermanos: tuple[str, ...] = ()) -> gpd.GeoDataFrame:
        """Lee un vector (GeoJSON o SHP con sus archivos hermanos) desde el bronce."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(nombre).stem
            for n in (nombre, *[f"{base}.{x}" for x in hermanos]):
                if n in self.archivos(dataset) or n == nombre:
                    (Path(tmp) / n).write_bytes(self.leer(dataset, n))
            return gpd.read_file(Path(tmp) / nombre)


# ---------------------------------------------------------------- tablas


def _municipios(b: _Bronce) -> gpd.GeoDataFrame:
    mun = b.capa("marco_geo", "municipios_peninsula.geojson").to_crs(CRS_M)
    mun = mun[mun["CVE_ENT"].isin(PENINSULA)].copy()
    mun["key"] = mun["CVE_ENT"] + "|" + mun["NOMGEO"].map(norm)
    return mun[["CVE_ENT", "NOMGEO", "key", "geometry"]].reset_index(drop=True)


def _vecinos(b: _Bronce) -> gpd.GeoDataFrame:
    base = b.capa("marco_geo", "basemap_peninsula.geojson").to_crs(CRS_M)
    return base[base["grupo"] == "vecino"][["geometry"]].reset_index(drop=True)


def _anp(b: _Bronce, mun: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    shp = next(n for n in b.archivos("anp_conanp") if n.lower().endswith(".shp"))
    anp = b.capa("anp_conanp", shp, hermanos=("shx", "dbf", "prj", "cpg")).to_crs(CRS_M)
    anp = anp[anp.intersects(mun.union_all().buffer(15_000))]
    anp = anp[anp["S_TERRES"] / (anp["S_TERRES"] + anp["S_MARINA"]) >= 0.2].copy()
    anp["NOMBRE"] = anp["NOMBRE"].str.replace("Dzibilchantún", "Dzibilchaltún")
    return anp[["NOMBRE", "S_TERRES", "S_MARINA", "geometry"]].reset_index(drop=True)


def _cuadro(contenido: bytes, col_valor: int, nombre: str) -> pd.DataFrame:
    """Cuadros del Censo Agropecuario 2022: solo filas municipales de 04, 23 y 31."""
    t = pd.read_excel(io.BytesIO(contenido), header=None)
    filas = t[t[0].astype(str).str.match(r"^(04|23|31) ") & t[1].notna()]
    return pd.DataFrame({
        "CVE_ENT": filas[0].str[:2].values,
        "municipio": filas[1].values,
        nombre: pd.to_numeric(filas[col_valor], errors="coerce").fillna(0).astype(int).values,
    })


def _censo_porcino(b: _Bronce) -> pd.DataFrame:
    cerdos = _cuadro(b.leer("censo_agropecuario", "ca2022_gan25.xlsx"), 3, "cerdos")      # existencias
    unidades = _cuadro(b.leer("censo_agropecuario", "ca2022_gan24.xlsx"), 5, "unidades")  # unidades con porcinos
    censo = cerdos.merge(unidades, on=["CVE_ENT", "municipio"])
    censo["key"] = censo["CVE_ENT"] + "|" + censo["municipio"].map(norm)
    return censo


def _denue(b: _Bronce) -> gpd.GeoDataFrame:
    """Todos los CSV de la lectura más reciente del DENUE, con su tema; solo los que tienen tema y coordenadas."""
    partes = []
    for nombre in sorted(b.archivos("denue", solo_fecha_reciente=True)):
        if nombre.lower().endswith(".csv"):
            partes.append(pd.read_csv(io.BytesIO(b.leer("denue", nombre)), encoding="utf-8-sig", low_memory=False))
    d = pd.concat(partes, ignore_index=True)
    d.columns = [c.replace("﻿", "").strip() for c in d.columns]
    if "Id" in d.columns:
        d = d.drop_duplicates("Id")
    d["Latitud"] = pd.to_numeric(d["Latitud"], errors="coerce")
    d["Longitud"] = pd.to_numeric(d["Longitud"], errors="coerce")
    d["tema"] = d["Clase_actividad"].map(tema)
    d = d.dropna(subset=["tema", "Latitud", "Longitud"])
    cols = [c for c in ("Id", "Nombre", "Clase_actividad", "Estrato", "Latitud", "Longitud", "tema") if c in d]
    g = gpd.GeoDataFrame(d[cols], geometry=gpd.points_from_xy(d["Longitud"], d["Latitud"]), crs=CRS_WEB)
    return g.to_crs(CRS_M).reset_index(drop=True)


def _cicy(b: _Bronce) -> pd.DataFrame:
    f = pd.read_csv(io.BytesIO(b.leer("cicy_flora", "cicy_flora_peninsula_yucatan.csv")),
                    encoding="utf-8-sig", low_memory=False)
    cols = ["Anio_Colecta", "Familia", "Genero", "Especie", "Municipio", "Estado_Normalizado"]
    return f[cols].copy()


def construir() -> dict[str, pd.DataFrame]:
    """Reconstruye todas las tablas de plata del equipo 2 y las publica en una sola transacción."""
    b = _Bronce()
    mun = _municipios(b)
    tablas = {
        "2.municipios": mun,
        "2.vecinos": _vecinos(b),
        "2.anp": _anp(b, mun),
        "2.censo_porcino": _censo_porcino(b),
        "2.denue_impacto": _denue(b),
        "2.cicy_flora": _cicy(b),
    }
    tablas["2.bronce_archivos"] = pd.DataFrame(b.usados).drop_duplicates(["dataset", "archivo"])
    comun.escribir(ESQUEMA, tablas)
    return tablas


if __name__ == "__main__":
    for nombre, df in construir().items():
        print(f'{ESQUEMA}."{nombre}"{"":{24 - len(nombre)}} {len(df):6} filas')
