"""Tabla de oro de 6.atraccion_capital.

Atracción de capital, empleo y evolución de las unidades económicas en Yucatán.

Fuentes (bronce: bronze/6/<dataset>/fecha=AAAA-MM-DD/):

- Primaria:   Secretaría de Economía, inversión extranjera directa por entidad federativa
              (ied_entidad: s3_ied.csv, cifras acumuladas por trimestre).
- Secundaria: INEGI, DENUE de Yucatán, un corte por dataset (denue_yucatan_2018 a denue_yucatan_2026;
              cada uno como zip del INEGI o CSV).

Plata:
- plata."6.atraccion_capital_ied"    IED acumulada y flujo por entidad, año y trimestre (las 32 entidades y el total).
- plata."6.atraccion_capital_denue"  establecimientos de Yucatán por corte y rango de personal ocupado.

Oro: formato largo, una fila por serie, entidad y año.
- "ied":      IED anual, millones de dólares, de Yucatán, Campeche y Quintana Roo en años de cuatro trimestres,
              con `lugar` entre los 32 estados por IED acumulada y `de_estados`.
- "unidades": unidades económicas de Yucatán en cada corte del DENUE.
- "empleo":   personal ocupado estimado de Yucatán (punto medio de cada rango del DENUE).
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


VIZ_ID = "6.atraccion_capital"
SUBTEMA = "atraccion_capital"
ANIOS_DENUE = list(range(2018, 2027))
DENUE = {f"denue_yucatan_{a}": a for a in ANIOS_DENUE}
DATASETS = ["ied_entidad", *DENUE]
TABLA_IED = f"{VIZ_ID}_ied"
TABLA_DENUE = f"{VIZ_ID}_denue"

# Descarga directa de cortes del DENUE (patrón de la descarga masiva del INEGI). Si falla, se suben a mano.
_DENUE_URL = "https://www.inegi.org.mx/contenidos/masiva/denue/"
URLS = {f"denue_yucatan_{a}": {f"denue_31_11{a % 100}_csv.zip": f"{_DENUE_URL}denue_31_11{a % 100}_csv.zip"}
        for a in range(2021, 2025)}

FUENTE_PRIMARIA = "Secretaría de Economía, inversión extranjera directa por entidad federativa"
FUENTE_SECUNDARIA = "INEGI, DENUE, unidades económicas y personal ocupado estimado de Yucatán (cortes 2018 a 2026)"
INSTITUCION = "Secretaría de Economía e INEGI"
RESPONSABLE = "Arturo"


def ingesta(fecha: str | None = None, carpeta_local: str | Path | None = None) -> dict:
    return L.ingerir(alm, DATASETS, fecha, carpeta_local, URLS)


def _ied(carpeta: Path) -> pd.DataFrame:
    """El archivo trae cifras ACUMULADAS dentro de cada año; el flujo de cada trimestre es la resta con el anterior.

    Las cifras se revisan con el tiempo: algunos flujos salen negativos (desinversión o ajuste, no error de lectura).
    """
    archivos = L.buscar(carpeta, "csv")
    if not archivos:
        raise FileNotFoundError("En bronce no hay un CSV de IED en ied_entidad")
    d = L.leer_csv(archivos[0])
    if "pais_origen" in d.columns:  # versión de la SE desglosada por país de origen: se queda el total
        d = d[d.pais_origen.astype(str).str.strip().str.lower() == "total"]
    d["entidad"] = d.entidad_federativa.str.strip()
    d[["anio", "trim"]] = d.anio_trim.astype(str).str.split("-", expand=True).astype(int)
    d = d.rename(columns={"ied_mdd": "acumulado_mdd"})[["entidad", "anio", "trim", "acumulado_mdd"]]
    d = d.sort_values(["entidad", "anio", "trim"]).reset_index(drop=True)
    d["flujo_mdd"] = d.groupby(["entidad", "anio"]).acumulado_mdd.diff().fillna(d.acumulado_mdd)
    return d


def plata(prefijo: dict | None = None) -> int:
    """Bronce -> plata."6.atraccion_capital_ied" y plata."6.atraccion_capital_denue"."""
    p = prefijo if isinstance(prefijo, dict) else {}
    fechas = []
    with alm.crudos("ied_entidad", p.get("ied_entidad")) as (carpeta, fecha):
        ied = _ied(carpeta)
    fechas.append(fecha)

    partes = []
    for dataset, anio in DENUE.items():
        with alm.crudos(dataset, p.get(dataset)) as (carpeta, fecha):
            d = L.leer_denue(carpeta, ("id", "per_ocu"))
        fechas.append(fecha)
        g = d.groupby("per_ocu", dropna=False).size().rename("establecimientos").reset_index()
        g["personas"] = g.per_ocu.map(L.PERSONAS)
        partes.append(g.assign(anio=anio))
    denue = pd.concat(partes, ignore_index=True)[["anio", "per_ocu", "personas", "establecimientos"]]

    obtencion = max(fechas)
    alm.cargar({TABLA_IED: ied.assign(fecha_obtencion=obtencion),
                TABLA_DENUE: denue.assign(fecha_obtencion=obtencion)}, alm.ESQUEMA_PLATA)
    return len(ied) + len(denue)


def _sin_acentos(s) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn").lower().strip()


def oro_desde_plata(t: pd.DataFrame, denue: pd.DataFrame) -> pd.DataFrame:
    ultimo = t.sort_values("trim").groupby(["entidad", "anio"]).tail(1)  # el acumulado del último trimestre es el año
    anual = ultimo.rename(columns={"acumulado_mdd": "ied_mdd", "trim": "trimestres"})
    anual = anual[anual.trimestres == 4]
    est = anual[~anual.entidad.str.lower().str.startswith("total")].copy()
    est["clave"] = est.entidad.map(_sin_acentos)
    acum = est.groupby("clave").ied_mdd.sum().sort_values(ascending=False)
    lugar = {k: i + 1 for i, k in enumerate(acum.index)}
    nombres = {_sin_acentos(e): e for e in L.PENINSULA}
    ied = est[est.clave.isin(nombres)].copy()
    ied["entidad"] = ied.clave.map(nombres)
    ied["lugar"] = ied.clave.map(lugar)
    ied["de_estados"] = len(acum)
    ied["serie"] = "ied"
    ied = ied.rename(columns={"ied_mdd": "valor"})[["serie", "entidad", "anio", "valor", "lugar", "de_estados"]]

    # unidades económicas y personal ocupado estimado de Yucatán, un valor por corte del DENUE
    denue = denue.assign(empleo=denue.personas * denue.establecimientos)
    g = denue.groupby("anio").agg(unidades=("establecimientos", "sum"), empleo=("empleo", "sum")).reset_index()
    filas = []
    for r in g.itertuples():
        filas.append(dict(serie="unidades", entidad="Yucatán", anio=int(r.anio), valor=float(r.unidades)))
        filas.append(dict(serie="empleo", entidad="Yucatán", anio=int(r.anio), valor=float(r.empleo)))
    d = pd.concat([ied, pd.DataFrame(filas)], ignore_index=True).sort_values(["serie", "entidad", "anio"])
    return d.reset_index(drop=True)


def oro() -> float:
    """plata -> oro."6.atraccion_capital"."""
    t = alm.leer(TABLA_IED, alm.ESQUEMA_PLATA)
    denue = alm.leer(TABLA_DENUE, alm.ESQUEMA_PLATA)
    tabla = oro_desde_plata(t, denue)
    tabla.insert(0, "viz_id", VIZ_ID)
    tabla["fuente_primaria"] = FUENTE_PRIMARIA
    tabla["fuente_secundaria"] = FUENTE_SECUNDARIA
    tabla["institucion"] = INSTITUCION
    tabla["fecha_obtencion"] = str(t["fecha_obtencion"].iloc[0])
    tabla["responsable"] = RESPONSABLE
    alm.cargar({VIZ_ID: tabla}, alm.ESQUEMA_ORO)
    return valor_referencia(tabla)


def valor_referencia(oro: pd.DataFrame) -> float:
    """IED acumulada de Yucatán de los años completos (2018 a 2025), millones de dólares (valor del catálogo)."""
    d = oro[(oro["serie"] == "ied") & (oro["entidad"] == "Yucatán")]
    return round(float(d["valor"].sum()), 1)
