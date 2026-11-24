"""Tabla de oro de 6.huella_construida.

Huella construida, altura y densidad empresarial de Mérida.

Usa la misma malla de 200 m en EPSG:32616 que 6.relieve_5m y las mismas
fuentes (MDE de 5 m de INEGI, huellas de Overture y DENUE de mayo de 2026).
La malla se arma con las funciones de `relieve_5m.py`, así que las dos
visualizaciones comparten celdas, alturas y conteos.

Curvas de concentración, solo con celdas urbanas (al menos 5% del área
construida: 2,000 m² de huella de Overture por celda, el umbral de la malla
compartida en `relieve_5m.HUELLA_MINIMA_M2`):

1. Se ordenan las celdas de mayor a menor por un criterio:
   - `Huella`: m² de huella construida en la celda;
   - `Altura`: altura edificada de la celda (MDS - MDT por edificio,
     promedio ponderado por la huella).
2. Eje x: % acumulado de celdas urbanas. Eje y: % acumulado de los negocios
   del DENUE que caen en celdas urbanas.
3. El punto de 10% es la parte de los negocios que reúne el 10% de celdas con
   más huella (o más altura). Una celda sin altura medida queda al final.

La tabla de oro es un DataFrame en formato largo con `capa`:

- `curva`: puntos de las dos curvas, cada 0.5% de celdas;
- `punto`: el valor exacto en 10% de celdas para cada criterio.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

VIZ_ID = "6.huella_construida"
RESPONSABLE = "Gio Soriano"
PASO_PCT = 0.5
CORTE_PCT = 10.0
CRITERIOS = {"Huella": "huella_m2", "Altura": "altura_m"}


def _relieve():
    ruta = Path(__file__).with_name("relieve_5m.py")
    spec = importlib.util.spec_from_file_location("relieve_5m", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


relieve = _relieve()
FUENTE_PRIMARIA = (
    "Overture Maps Foundation: huellas de edificios (tema buildings); "
    "INEGI: DENUE, corte de mayo de 2026, Yucatán"
)
FUENTE_SECUNDARIA = relieve.FUENTE_PRIMARIA
INSTITUCION = relieve.INSTITUCION


def curva(celdas: pd.DataFrame, columna: str) -> pd.DataFrame:
    """% acumulado de celdas contra % acumulado de negocios, de mayor a menor."""
    orden = celdas.sort_values([columna, "negocios"], ascending=[False, False], na_position="last")
    n = len(orden)
    acumulado = orden["negocios"].cumsum().to_numpy()
    total = acumulado[-1]
    x = np.concatenate([[0.0], 100 * np.arange(1, n + 1) / n])
    y = np.concatenate([[0.0], 100 * acumulado / total])
    return pd.DataFrame({"pct_celdas": x, "pct_negocios": y})


def en_corte(c: pd.DataFrame, pct: float = CORTE_PCT) -> float:
    return float(np.interp(pct, c["pct_celdas"], c["pct_negocios"]))


def curvas_desde_malla(celdas: pd.DataFrame) -> pd.DataFrame:
    urbanas = celdas[celdas["huella_m2"] >= relieve.HUELLA_MINIMA_M2].copy()
    urbanas["negocios"] = urbanas["negocios"].astype(int)
    rejilla = np.arange(0, 100 + PASO_PCT / 2, PASO_PCT)
    filas = []
    for nombre, columna in CRITERIOS.items():
        c = curva(urbanas, columna)
        filas.append(pd.DataFrame({
            "capa": "curva", "criterio": nombre, "pct_celdas": rejilla,
            "pct_negocios": np.interp(rejilla, c["pct_celdas"], c["pct_negocios"]),
        }))
        filas.append(pd.DataFrame([{
            "capa": "punto", "criterio": nombre, "pct_celdas": CORTE_PCT,
            "pct_negocios": en_corte(c),
            "celdas_urbanas": len(urbanas), "negocios": int(urbanas["negocios"].sum()),
            "celdas_en_corte": int(np.ceil(len(urbanas) * CORTE_PCT / 100)),
        }]))
    return pd.concat(filas, ignore_index=True)


def construir_oro(malla: pd.DataFrame | None = None, dir_cartas: Path | None = None,
                  ruta_edificios: Path | None = None, ruta_denue: Path | None = None,
                  fecha_obtencion: str | None = None, verbose: bool = True) -> pd.DataFrame:
    """`malla`: capa `celda` de la tabla de oro de 6.relieve_5m. Si no se pasa,
    se arma desde los crudos con las mismas funciones."""
    if malla is None:
        malla, _ = relieve.construir_malla(dir_cartas, ruta_edificios, ruta_denue, verbose)
        if fecha_obtencion is None:
            primera = sorted(Path(dir_cartas).rglob("*_ms.xyz"))[0]
            fecha_obtencion = pd.Timestamp(primera.stat().st_mtime, unit="s").date().isoformat()
    else:
        if "capa" in malla.columns:
            if fecha_obtencion is None:
                fecha_obtencion = str(malla["fecha_obtencion"].iloc[0])
            malla = malla[malla["capa"] == "celda"]

    oro = curvas_desde_malla(malla)
    oro["pct_celdas"] = oro["pct_celdas"].round(3)
    oro["pct_negocios"] = oro["pct_negocios"].round(3)
    for c in ("celdas_urbanas", "negocios", "celdas_en_corte"):
        oro[c] = oro[c].astype("Int64")
    oro.insert(0, "viz_id", VIZ_ID)
    oro["fuente_primaria"] = FUENTE_PRIMARIA
    oro["fuente_secundaria"] = FUENTE_SECUNDARIA
    oro["institucion"] = INSTITUCION
    oro["fecha_obtencion"] = fecha_obtencion
    oro["responsable"] = RESPONSABLE
    return oro


def resumen(oro: pd.DataFrame) -> pd.DataFrame:
    return oro[oro["capa"] == "punto"][["criterio", "pct_celdas", "pct_negocios", "celdas_en_corte",
                                        "celdas_urbanas", "negocios"]].reset_index(drop=True)


def valor_referencia(oro: pd.DataFrame) -> float:
    """% de negocios en el 10% de celdas urbanas con más huella construida."""
    fila = oro[(oro["capa"] == "punto") & (oro["criterio"] == "Huella")].iloc[0]
    return round(float(fila["pct_negocios"]), 1)
