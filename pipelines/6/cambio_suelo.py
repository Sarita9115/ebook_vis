"""Tabla de oro de 6.cambio_suelo.

Cambio de uso del suelo y expansión urbana en Yucatán y la zona metropolitana de Mérida.

Fuentes (todas con enlace directo):

- Primaria: Uso del suelo y vegetación 1:250 000, serie VII (INEGI), en el geoportal
  de CONABIO: http://www.conabio.gob.mx/informacion/gis/maps/geo/usv250s7gw.zip
  Fotointerpretación sobre geomedianas Landsat con año base 2018.
- Secundaria: la misma carta, serie VI (imágenes Landsat 2014):
  http://www.conabio.gob.mx/informacion/gis/maps/geo/usv250s6gw.zip
- Secundaria: IDEFOR (CONAFOR), Mapa de cobertura del suelo de Yucatán 2020 v1.1.
  Solo sirve de contraste del área urbana; no entra a la figura.
- Límites: División política municipal 2023 (INEGI, vía CONABIO, mun23gw.zip).
  Da el contorno de Yucatán (CVE_ENT 31) y de la ZM Mérida–Progreso.

Lo que se sabe de los crudos (verificado al abrirlos):

- Las dos series son el continuo nacional en EPSG:4326, con los campos
  DESCRIPCIO, COV_, COV_ID y codigo. Se leen solo dentro del recuadro de
  Yucatán y se recortan al contorno estatal antes de cualquier cálculo.
- Los .dbf declaran ISO-8859-1, pero el texto está en UTF-8.
- La serie VI llama "URBANO CONSTRUIDO" a lo que la VII llama "ASENTAMIENTOS
  HUMANOS". Las dos van al grupo Urbano.

Las áreas e intersecciones se calculan en EPSG:32616 (UTM 16N). Se descartan los
cruces menores a 0.01 km². La geometría de oro sale simplificada en EPSG:4326.

La tabla de oro es un GeoDataFrame en formato largo con una columna `capa`:

- `transicion`:   km² de cada par (grupo serie VI → grupo serie VII) por ámbito.
- `urbano_nuevo`: polígonos que eran no urbanos en la serie VI y urbanos en la VII.
- `urbano_previo`: área urbana de la serie VI, como fondo del mapa.
- `contorno`:     contorno de Yucatán y de la ZM Mérida–Progreso.

Etapas (Airflow, dags/equipo_6.py):

- `ingesta()`: descarga usv250s7gw.zip, usv250s6gw.zip y mun23gw.zip de
  CONABIO a bronze/6/cambio_suelo/fecha=AAAA-MM-DD/ y los abre junto al ZIP.
  IDEFOR no tiene archivo directo (es una capa de GeoNode); solo se descarga
  si se define E6_IDEFOR_URL con el enlace del ZIP.
- `plata()`:   recorta las series VI y VII y los municipios a Yucatán, en
  EPSG:32616, y carga plata."6.cambio_suelo.ambitos", ".usv_vi" y ".usv_vii".
- `oro()`:     cruza las series desde plata y carga oro."6.cambio_suelo".

Prueba local (opcional y explícita): `ingesta(carpeta_local=...)` o la variable
E6_CRUDOS_CAMBIO_SUELO suben una carpeta de crudos a bronce en vez de
descargar; `construir_oro(dir_crudos)` arma el oro en memoria desde una carpeta dada.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import os
import sys
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

VIZ_ID = "6.cambio_suelo"
DATASET = "cambio_suelo"
TABLAS_PLATA = {"ambitos": f"{VIZ_ID}.ambitos", "usv_vi": f"{VIZ_ID}.usv_vi", "usv_vii": f"{VIZ_ID}.usv_vii"}
CRS_TRABAJO = 32616
CRS_PUBLICACION = 4326
CVE_ENT_YUCATAN = "31"
MIN_KM2 = 0.01

# ZM de Mérida según la delimitación de CONAPO 2015 (incluye Progreso).
MUNICIPIOS_ZM = {
    "31013": "Conkal",
    "31041": "Kanasín",
    "31050": "Mérida",
    "31059": "Progreso",
    "31100": "Ucú",
    "31101": "Umán",
}
AMBITO_ZM = "ZM Mérida–Progreso"
AMBITO_RESTO = "Resto de Yucatán"
AMBITO_ESTADO = "Yucatán"

URLS = {
    "usv_s7": "http://www.conabio.gob.mx/informacion/gis/maps/geo/usv250s7gw.zip",
    "usv_s6": "http://www.conabio.gob.mx/informacion/gis/maps/geo/usv250s6gw.zip",
    "idefor_2020": "https://idefor.cnf.gob.mx/layers/geonode:mc2020v11_mx_yuc_vis",
    "mun23": "http://www.conabio.gob.mx/informacion/gis/maps/geo/mun23gw.zip",
}
RUTAS = {
    "usv_s6": "usv250s6gw/usv250s6gw.shp",
    "usv_s7": "usv250s7gw/usv250s7gw.shp",
    "idefor_2020": "idefor_mc2020v11_yuc_shp/mc2020v11_mx_yuc_vis.shp",
    "mun23": "mun23gw/mun23gw.shp",
}

FUENTE_PRIMARIA = "INEGI: Uso del suelo y vegetación 1:250 000, serie VII (geoportal CONABIO)"
FUENTE_SECUNDARIA = (
    "INEGI: Uso del suelo y vegetación 1:250 000, serie VI (geoportal CONABIO); "
    "IDEFOR (CONAFOR): Mapa de cobertura del suelo de Yucatán 2020 v1.1"
)
INSTITUCION = "INEGI y CONABIO"
RESPONSABLE = "Gio Soriano"

ANIO_SERIE = {"VI": 2014, "VII": 2018}

URBANO = "Urbano"
GRUPOS = [
    "Selva y vegetación secundaria",
    "Manglar, petén y costa",
    "Pastizal",
    "Agricultura",
    "Sin vegetación",
    "Agua",
    URBANO,
]

# Simplificación (metros, en UTM) antes de pasar a EPSG:4326.
TOLERANCIA_CONTORNO_M = 250
TOLERANCIA_URBANO_M = 30


def grupo(descripcion: str) -> str:
    """Asigna cada clase de la carta USV a un grupo de la figura."""
    d = descripcion.upper()
    if d in {"URBANO CONSTRUIDO", "ASENTAMIENTOS HUMANOS"}:
        return URBANO
    if d in {"AGUA", "CUERPO DE AGUA"}:
        return "Agua"
    if d in {"SIN VEGETACIÓN APARENTE", "ÁREA DESPROVISTA DE VEGETACIÓN", "DESPROVISTO DE VEGETACIÓN"}:
        return "Sin vegetación"
    if d.startswith("PASTIZAL") and "HALÓFILO" not in d:
        return "Pastizal"
    if d.startswith("AGRICULTURA") or d in {"BOSQUE CULTIVADO", "PALMAR INDUCIDO", "ACUÍCOLA"}:
        return "Agricultura"
    if ("MANGLAR" in d or "PETÉN" in d or d in {
        "TULAR", "VEGETACIÓN HALÓFILA HIDRÓFILA", "PASTIZAL HALÓFILO",
        "VEGETACIÓN DE DUNAS COSTERAS", "SABANA",
    }):
        return "Manglar, petén y costa"
    if "SELVA" in d:
        return "Selva y vegetación secundaria"
    raise ValueError(f"Clase USV sin grupo asignado: {descripcion!r}")


def leer_limites(dir_crudos: Path) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Devuelve (municipios de Yucatán, ámbitos ZM/Resto) en UTM 16N."""
    mun = gpd.read_file(dir_crudos / RUTAS["mun23"], encoding="utf-8")
    yuc = mun[mun["CVE_ENT"] == CVE_ENT_YUCATAN].copy()
    if len(yuc) != 106:
        raise ValueError(f"Se esperaban 106 municipios de Yucatán, hay {len(yuc)}")
    faltan = set(MUNICIPIOS_ZM) - set(yuc["CVEGEO"])
    if faltan:
        raise ValueError(f"Faltan municipios de la ZM: {sorted(faltan)}")
    yuc = yuc.to_crs(CRS_TRABAJO)
    yuc["ambito"] = yuc["CVEGEO"].map(lambda c: AMBITO_ZM if c in MUNICIPIOS_ZM else AMBITO_RESTO)
    ambitos = yuc.dissolve("ambito", as_index=False)[["ambito", "geometry"]]
    return yuc, ambitos


def leer_usv(ruta: Path, ambitos: gpd.GeoDataFrame, serie: str) -> gpd.GeoDataFrame:
    """Lee una serie USV solo dentro de Yucatán y la corta por ámbito."""
    bbox = tuple(ambitos.to_crs(CRS_PUBLICACION).total_bounds)
    g = gpd.read_file(ruta, encoding="utf-8", bbox=bbox)
    if "DESCRIPCIO" not in g.columns:
        raise ValueError(f"{ruta.name}: falta DESCRIPCIO")
    g = g.to_crs(CRS_TRABAJO)
    g[f"grupo_{serie}"] = g["DESCRIPCIO"].map(grupo)
    g = g[[f"grupo_{serie}", "geometry"]]
    return gpd.overlay(g, ambitos, how="intersection", keep_geom_type=True)


def cruzar(s6: gpd.GeoDataFrame, s7: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Intersección serie VI × serie VII dentro del mismo ámbito, en UTM 16N."""
    cruce = gpd.overlay(s6, s7, how="intersection", keep_geom_type=True)
    cruce = cruce[cruce["ambito_1"] == cruce["ambito_2"]].rename(columns={"ambito_1": "ambito"})
    cruce = cruce.drop(columns="ambito_2")
    cruce["km2"] = cruce.area / 1e6
    return cruce[cruce["km2"] >= MIN_KM2].copy()


def _publicar(g: gpd.GeoDataFrame, tolerancia: float) -> gpd.GeoDataFrame:
    g = g.copy()
    g["geometry"] = g.geometry.simplify(tolerancia, preserve_topology=True)
    g = g[~g.geometry.is_empty]
    return g.to_crs(CRS_PUBLICACION)


def construir_plata(dir_crudos: Path, fecha_obtencion: str | None = None) -> dict[str, gpd.GeoDataFrame]:
    """Ámbitos y series VI y VII recortadas a Yucatán, en EPSG:32616."""
    dir_crudos = Path(dir_crudos)
    _, ambitos = leer_limites(dir_crudos)
    s6 = leer_usv(dir_crudos / RUTAS["usv_s6"], ambitos, "VI")
    s7 = leer_usv(dir_crudos / RUTAS["usv_s7"], ambitos, "VII")
    if fecha_obtencion is None:
        mtime = (dir_crudos / RUTAS["usv_s7"]).stat().st_mtime
        fecha_obtencion = dt.date.fromtimestamp(mtime).isoformat()
    tablas = {"ambitos": ambitos, "usv_vi": s6, "usv_vii": s7}
    for g in tablas.values():
        g["fecha_obtencion"] = fecha_obtencion
    return tablas


def oro_desde_plata(ambitos: gpd.GeoDataFrame, s6: gpd.GeoDataFrame,
                    s7: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Tabla de oro a partir de las tres tablas de plata (EPSG:32616)."""
    fecha_obtencion = str(s7["fecha_obtencion"].iloc[0])
    ambitos = ambitos.drop(columns="fecha_obtencion", errors="ignore").to_crs(CRS_TRABAJO)
    s6 = s6.drop(columns="fecha_obtencion", errors="ignore").to_crs(CRS_TRABAJO)
    s7 = s7.drop(columns="fecha_obtencion", errors="ignore").to_crs(CRS_TRABAJO)
    cruce = cruzar(s6, s7)

    transiciones = (
        cruce.groupby(["ambito", "grupo_VI", "grupo_VII"], as_index=False)["km2"].sum()
        .rename(columns={"grupo_VI": "origen", "grupo_VII": "destino"})
    )
    transiciones["capa"] = "transicion"
    transiciones["geometry"] = None

    nuevo = cruce[(cruce["grupo_VI"] != URBANO) & (cruce["grupo_VII"] == URBANO)]
    nuevo = nuevo.dissolve(["ambito", "grupo_VI"], as_index=False, aggfunc={"km2": "sum"})
    nuevo = _publicar(nuevo, TOLERANCIA_URBANO_M).rename(columns={"grupo_VI": "origen"})
    nuevo["destino"] = URBANO
    nuevo["capa"] = "urbano_nuevo"

    previo = s6[s6["grupo_VI"] == URBANO].dissolve("ambito", as_index=False)
    previo["km2"] = previo.area / 1e6
    previo = _publicar(previo[["ambito", "km2", "geometry"]], TOLERANCIA_URBANO_M)
    previo["origen"] = URBANO
    previo["capa"] = "urbano_previo"

    estado = ambitos.dissolve()
    estado["ambito"] = AMBITO_ESTADO
    contornos = pd.concat([estado, ambitos[ambitos["ambito"] == AMBITO_ZM]], ignore_index=True)
    contornos["km2"] = contornos.area / 1e6
    contornos = _publicar(contornos[["ambito", "km2", "geometry"]], TOLERANCIA_CONTORNO_M)
    contornos["capa"] = "contorno"

    oro = gpd.GeoDataFrame(
        pd.concat([transiciones, nuevo, previo, contornos], ignore_index=True),
        geometry="geometry",
        crs=CRS_PUBLICACION,
    )
    oro["serie_origen"] = f"VI ({ANIO_SERIE['VI']})"
    oro["serie_destino"] = f"VII ({ANIO_SERIE['VII']})"
    oro["km2"] = oro["km2"].round(4)

    oro.insert(0, "viz_id", VIZ_ID)
    oro["fuente_primaria"] = FUENTE_PRIMARIA
    oro["fuente_secundaria"] = FUENTE_SECUNDARIA
    oro["institucion"] = INSTITUCION
    oro["fecha_obtencion"] = fecha_obtencion
    oro["responsable"] = RESPONSABLE
    columnas = [
        "viz_id", "capa", "ambito", "origen", "destino", "km2", "serie_origen",
        "serie_destino", "fuente_primaria", "fuente_secundaria", "institucion",
        "fecha_obtencion", "responsable", "geometry",
    ]
    return oro[columnas]


def construir_oro(dir_crudos: Path, fecha_obtencion: str | None = None) -> gpd.GeoDataFrame:
    """Prueba local: crudos -> plata -> oro en memoria."""
    p = construir_plata(dir_crudos, fecha_obtencion)
    return oro_desde_plata(p["ambitos"], p["usv_vi"], p["usv_vii"])


def resumen_urbano(oro: pd.DataFrame) -> pd.DataFrame:
    """km² urbanos ganados (bruto), perdidos y netos por ámbito y para todo Yucatán."""
    t = oro[oro["capa"] == "transicion"]
    filas = {}
    for ambito, sub in [(AMBITO_ESTADO, t)] + list(t.groupby("ambito")):
        ganado = sub[(sub["origen"] != URBANO) & (sub["destino"] == URBANO)]["km2"].sum()
        perdido = sub[(sub["origen"] == URBANO) & (sub["destino"] != URBANO)]["km2"].sum()
        urb_vi = sub[sub["origen"] == URBANO]["km2"].sum()
        urb_vii = sub[sub["destino"] == URBANO]["km2"].sum()
        filas[ambito] = {
            "urbano_serie_VI_km2": urb_vi,
            "urbano_serie_VII_km2": urb_vii,
            "ganado_bruto_km2": ganado,
            "perdido_km2": perdido,
            "neto_km2": urb_vii - urb_vi,
        }
    return pd.DataFrame(filas).T.round(2)


def valor_referencia(oro: pd.DataFrame) -> float:
    """km² urbanos netos ganados en Yucatán entre la serie VI y la VII (valor del catálogo)."""
    return float(resumen_urbano(oro).loc[AMBITO_ESTADO, "neto_km2"])


def urbano_idefor_2020(dir_crudos: Path) -> float:
    """km² de la clase 30 Urbano y Construido de IDEFOR 2020, para contraste."""
    g = gpd.read_file(Path(dir_crudos) / RUTAS["idefor_2020"], encoding="utf-8")
    urbano = g[g["ID_SAMOF"] == 30].to_crs(CRS_TRABAJO)
    return round(float(urbano.area.sum() / 1e6), 2)


# ---------------------------------------------------------------------------
# Etapas del DAG
# ---------------------------------------------------------------------------

def ingesta(fecha: str | None = None, carpeta_local: str | Path | None = None) -> str:
    """Fuentes con enlace directo -> bronce.

    Si se da una carpeta de crudos (argumento o E6_CRUDOS_CAMBIO_SUELO), se sube
    esa carpeta y solo se descarga lo que le falte.
    """
    urls = {Path(URLS[k]).name: URLS[k] for k in ("usv_s7", "usv_s6", "mun23")}
    if os.environ.get("E6_IDEFOR_URL"):
        urls["idefor_mc2020v11_yuc_shp.zip"] = os.environ["E6_IDEFOR_URL"]
    local = alm.carpeta_local(DATASET, carpeta_local)
    if local is None:
        return alm.ingestar_urls(DATASET, urls, fecha)
    destino = alm.ingestar_carpeta_local(DATASET, local, fecha)
    alm.completar_urls(destino, urls)
    return destino


def plata(prefijo: str | None = None) -> int:
    """Bronce -> plata."6.cambio_suelo.*"."""
    with alm.crudos(DATASET, prefijo, filtro=r"^(usv250s[67]gw|mun23gw)") as (carpeta, fecha):
        tablas = construir_plata(carpeta, fecha)
    alm.cargar({TABLAS_PLATA[k]: g for k, g in tablas.items()}, alm.ESQUEMA_PLATA)
    return sum(len(g) for g in tablas.values())


def oro() -> float:
    """plata -> oro."6.cambio_suelo". Devuelve la cifra que se contrasta con el catálogo."""
    p = {k: alm.leer(t, alm.ESQUEMA_PLATA) for k, t in TABLAS_PLATA.items()}
    tabla = oro_desde_plata(p["ambitos"], p["usv_vi"], p["usv_vii"])
    alm.cargar({VIZ_ID: tabla}, alm.ESQUEMA_ORO)
    return valor_referencia(tabla)


if __name__ == "__main__":
    # Prueba local explícita: python pipelines/6/cambio_suelo.py <carpeta_de_crudos>
    if len(sys.argv) < 2:
        sys.exit("Uso: cambio_suelo.py <carpeta_de_crudos>  (en producción corre el DAG equipo_6)")
    crudos = Path(sys.argv[1])
    tabla = construir_oro(crudos)
    print(tabla.drop(columns="geometry").groupby("capa").size())
    print(resumen_urbano(tabla))
    print("valor_referencia:", valor_referencia(tabla))
    print("IDEFOR 2020, urbano y construido (km²):", urbano_idefor_2020(crudos))
