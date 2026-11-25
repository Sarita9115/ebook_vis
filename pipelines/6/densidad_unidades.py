"""Tabla de oro de 6.densidad_unidades.

Distribución y densidad de unidades económicas en la península (Yucatán, Campeche, Quintana Roo).

Fuentes (bronce: bronze/6/<dataset>/fecha=AAAA-MM-DD/):

- Primaria:   INEGI, DENUE, corte 2026 de Yucatán, Campeche y Quintana Roo
              (denue_yucatan_2026, denue_campeche_2026, denue_quintana_roo_2026; zip del INEGI o CSV).
- Secundaria: INEGI, Encuesta Intercensal 2025, población por entidad (poblacion_eic2025:
              eic2025_poblacion_31.xlsx, _04.xlsx y _23.xlsx).
- Contorno:   limites_peninsula (limites_peninsula.geojson, Natural Earth, campo `entidad`).

Plata:
- plata."6.densidad_unidades"            un establecimiento por fila: entidad, id, codigo_act, cve_mun, lat, lng
                                         (coordenadas fuera de la zona en nulo).
- plata."6.densidad_unidades_poblacion"  población total por entidad.
- plata."6.densidad_unidades_limites"    contorno por entidad (geometría EPSG:4326).

Oro: dos tipos de fila, separados por `tipo`.
- "celda":  celda de 0.02 grados (unos 2 km) con `unidades`, la `entidad` que más aporta y los totales de la
            entidad (`unidades_entidad`, `poblacion_entidad`).
- "limite": `entidad` y `geometry` (polígono o multipolígono EPSG:4326).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

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

VIZ_ID = "6.densidad_unidades"
SUBTEMA = "densidad_unidades"
DENUE = {"denue_yucatan_2026": "Yucatán", "denue_campeche_2026": "Campeche", "denue_quintana_roo_2026": "Quintana Roo"}
DATASETS = [*DENUE, "poblacion_eic2025", "limites_peninsula"]
TABLA_DENUE = f"{VIZ_ID}"
TABLA_POBLACION = f"{VIZ_ID}_poblacion"
TABLA_LIMITES = f"{VIZ_ID}_limites"
CELDA = 0.02  # grados

FUENTE_PRIMARIA = "INEGI, Directorio Estadístico Nacional de Unidades Económicas (DENUE), corte 2026 de Yucatán, Campeche y Quintana Roo"
FUENTE_SECUNDARIA = "INEGI, Encuesta Intercensal 2025 (población por entidad)"
INSTITUCION = "INEGI"
RESPONSABLE = "Arturo"


def ingesta(fecha: str | None = None, carpeta_local: str | Path | None = None) -> dict:
    """Los cinco datasets deben estar en bronce (los sube Producción); la tarea falla con la lista de lo que falte."""
    return L.ingerir(alm, DATASETS, fecha, carpeta_local)


def plata(prefijo: dict | None = None) -> int:
    """Bronce -> plata."6.densidad_unidades" y sus dos tablas de apoyo."""
    import geopandas as gpd

    p = prefijo if isinstance(prefijo, dict) else {}
    partes, fechas = [], []
    for dataset, entidad in DENUE.items():
        with alm.crudos(dataset, p.get(dataset)) as (carpeta, fecha):
            bbox = L.BBOX_YUCATAN if entidad == "Yucatán" else L.BBOX_PENINSULA
            d = L.leer_denue(carpeta, ("id", "codigo_act", "cve_mun", "latitud", "longitud"), bbox)
        fechas.append(fecha)
        partes.append(d.assign(entidad=entidad))
    denue = pd.concat(partes, ignore_index=True)[["entidad", "id", "codigo_act", "cve_mun", "lat", "lng"]]

    with alm.crudos("poblacion_eic2025", p.get("poblacion_eic2025")) as (carpeta, fecha):
        poblacion = pd.DataFrame([
            {"cve_ent": clave, "entidad": nombre,
             "poblacion": L.poblacion_entidad(alm.buscar(carpeta, f"eic2025_poblacion_{clave}.xlsx"), clave)}
            for clave, nombre in L.ENTIDADES.items()])
    fechas.append(fecha)

    with alm.crudos("limites_peninsula", p.get("limites_peninsula")) as (carpeta, fecha):
        limites = gpd.read_file(alm.buscar(carpeta, "*.geojson"))[["entidad", "geometry"]].set_crs(4326, allow_override=True)
    fechas.append(fecha)

    obtencion = max(fechas)
    alm.cargar({TABLA_DENUE: denue.assign(fecha_obtencion=obtencion),
                TABLA_POBLACION: poblacion.assign(fecha_obtencion=obtencion),
                TABLA_LIMITES: limites.assign(fecha_obtencion=obtencion)}, alm.ESQUEMA_PLATA)
    return len(denue)


def oro_desde_plata(denue: pd.DataFrame, poblacion: pd.DataFrame, limites) -> "gpd.GeoDataFrame":
    import geopandas as gpd

    pob = poblacion.set_index("entidad").poblacion
    celdas, entidades = [], []
    for nombre in L.PENINSULA:
        d = denue[denue.entidad == nombre]
        entidades.append({"entidad": nombre, "unidades_entidad": len(d), "poblacion_entidad": int(pob[nombre])})
        c = d.dropna(subset=["lat", "lng"]).copy()
        c["celda_lng"] = (np.floor(c.lng / CELDA) * CELDA + CELDA / 2).round(4)
        c["celda_lat"] = (np.floor(c.lat / CELDA) * CELDA + CELDA / 2).round(4)
        g = c.groupby(["celda_lng", "celda_lat"]).size().rename("unidades").reset_index()
        g["entidad"] = nombre
        celdas.append(g)
    celdas = pd.concat(celdas, ignore_index=True)
    # una celda que toca dos entidades se queda con la suma y con la entidad que más aporta
    celdas = (celdas.sort_values("unidades", ascending=False)
              .groupby(["celda_lng", "celda_lat"], as_index=False)
              .agg(unidades=("unidades", "sum"), entidad=("entidad", "first")))
    celdas = celdas.merge(pd.DataFrame(entidades), on="entidad", how="left").assign(tipo="celda", geometry=None)
    lim = pd.DataFrame({"entidad": limites.entidad.values, "geometry": list(limites.geometry), "tipo": "limite"})
    d = pd.concat([celdas, lim], ignore_index=True)
    return gpd.GeoDataFrame(d, geometry="geometry", crs=4326)


def oro() -> float:
    """plata -> oro."6.densidad_unidades". Devuelve la cifra que se contrasta con el catálogo."""
    denue = alm.leer(TABLA_DENUE, alm.ESQUEMA_PLATA)
    tabla = oro_desde_plata(denue, alm.leer(TABLA_POBLACION, alm.ESQUEMA_PLATA), alm.leer(TABLA_LIMITES, alm.ESQUEMA_PLATA))
    tabla.insert(0, "viz_id", VIZ_ID)
    tabla["fuente_primaria"] = FUENTE_PRIMARIA
    tabla["fuente_secundaria"] = FUENTE_SECUNDARIA
    tabla["institucion"] = INSTITUCION
    tabla["fecha_obtencion"] = str(denue["fecha_obtencion"].iloc[0])
    tabla["responsable"] = RESPONSABLE
    alm.cargar({VIZ_ID: tabla}, alm.ESQUEMA_ORO)
    return valor_referencia(tabla)


def valor_referencia(oro: pd.DataFrame) -> float:
    """Unidades económicas de Yucatán en el DENUE 2026 (valor del catálogo)."""
    d = oro[(oro["tipo"] == "celda") & (oro["entidad"] == "Yucatán")]
    return float(d["unidades_entidad"].iloc[0])
