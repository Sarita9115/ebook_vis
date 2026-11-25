"""Tabla de oro de 6.aporte_pib.

Aporte del sector empresarial al PIB estatal y regional. El sector empresarial se representa con el
sector 71 del SCIAN (servicios de esparcimiento culturales y deportivos).

Fuentes (bronce: bronze/6/pibe/fecha=AAAA-MM-DD/):

- Primaria:   INEGI, PIB por entidad federativa (PIBE), año base 2018: pibe_*.xlsx de Nacional, Campeche,
              Quintana Roo y Yucatán.
- Secundaria: INEGI, DENUE (unidades económicas por entidad, solo contexto de la lectura).

Plata: plata."6.aporte_pib" con todas las actividades, entidades y años de los cuatro archivos.
Oro: una fila por entidad, actividad ("71" o "VAB"), año y `constantes` (millones de pesos de 2018).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

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

VIZ_ID = "6.aporte_pib"
SUBTEMA = "aporte_pib"
DATASETS = ["pibe"]
TABLA_PLATA = VIZ_ID

FUENTE_PRIMARIA = "INEGI, PIB por entidad federativa (PIBE), año base 2018"
FUENTE_SECUNDARIA = "INEGI, DENUE (unidades económicas por entidad, solo contexto de la lectura)"
INSTITUCION = "INEGI"
RESPONSABLE = "Arturo"


def ingesta(fecha: str | None = None, carpeta_local: str | Path | None = None) -> dict:
    return L.ingerir(alm, DATASETS, fecha, carpeta_local)


def plata(prefijo: dict | None = None) -> int:
    """Bronce -> plata."6.aporte_pib"."""
    p = prefijo if isinstance(prefijo, dict) else {}
    with alm.crudos("pibe", p.get("pibe")) as (carpeta, fecha):
        archivos = L.buscar(carpeta, "xlsx", r"^pibe_")
        if not archivos:
            raise FileNotFoundError("En bronce no hay archivos pibe_*.xlsx")
        tabla = pd.concat([L.leer_pibe(a) for a in archivos], ignore_index=True)
    tabla["fecha_obtencion"] = fecha
    alm.cargar({TABLA_PLATA: tabla}, alm.ESQUEMA_PLATA)
    return len(tabla)


def oro_desde_plata(plata_pibe: pd.DataFrame) -> pd.DataFrame:
    d = plata_pibe[plata_pibe.actividad_codigo.isin(["VAB", "71"])][["entidad", "actividad_codigo", "anio", "constantes"]]
    d = d.sort_values(["entidad", "actividad_codigo", "anio"]).reset_index(drop=True)
    d.insert(0, "viz_id", VIZ_ID)
    d["fuente_primaria"] = FUENTE_PRIMARIA
    d["fuente_secundaria"] = FUENTE_SECUNDARIA
    d["institucion"] = INSTITUCION
    d["fecha_obtencion"] = str(plata_pibe["fecha_obtencion"].iloc[0])
    d["responsable"] = RESPONSABLE
    return d


def oro() -> float:
    """plata -> oro."6.aporte_pib"."""
    tabla = oro_desde_plata(alm.leer(TABLA_PLATA, alm.ESQUEMA_PLATA))
    alm.cargar({VIZ_ID: tabla}, alm.ESQUEMA_ORO)
    return valor_referencia(tabla)


def valor_referencia(oro: pd.DataFrame) -> float:
    """Sector 71 de Yucatán en 2024, millones de pesos de 2018 (valor del catálogo)."""
    d = oro[(oro["entidad"] == "Yucatán") & (oro["actividad_codigo"] == "71") & (oro["anio"] == 2024)]
    return float(d["constantes"].iloc[0])
