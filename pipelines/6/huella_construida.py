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

Etapas (Airflow, dags/equipo_6.py):

- `ingesta()`: igual que 6.relieve_5m, sobre bronze/6/huella_construida/.
  Usa lo que ya esté en bronce o lo baja de Drive (E6_GDRIVE_HUELLA_CONSTRUIDA);
  si no hay ninguno de los dos, reutiliza la partición vigente de
  bronze/6/relieve_5m/ (son las mismas fuentes).
- `plata()`:   toma la malla de plata."6.relieve_5m.malla" (si no existe, la
  arma desde bronce) y carga sus celdas urbanas en
  plata."6.huella_construida.celdas_urbanas".
- `oro()`:     calcula las curvas desde plata y carga oro."6.huella_construida".
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

VIZ_ID = "6.huella_construida"
DATASET = "huella_construida"
TABLA_PLATA = f"{VIZ_ID}.celdas_urbanas"
log = logging.getLogger("equipo6.huella_construida")
RESPONSABLE = "Gio Soriano"
PASO_PCT = 0.5
CORTE_PCT = 10.0
CRITERIOS = {"Huella": "huella_m2", "Altura": "altura_m"}


def _relieve():
    if "e6_relieve_5m" not in sys.modules:
        ruta = Path(__file__).with_name("relieve_5m.py")
        spec = importlib.util.spec_from_file_location("e6_relieve_5m", ruta)
        modulo = importlib.util.module_from_spec(spec)
        sys.modules["e6_relieve_5m"] = modulo
        spec.loader.exec_module(modulo)
    return sys.modules["e6_relieve_5m"]


relieve = _relieve()
alm = relieve.alm
# La primaria es solo Overture: el DENUE es la primaria de 6.corredor_industrial y
# no puede repetirse como primaria dentro del equipo; aquí es secundaria.
FUENTE_PRIMARIA = "Overture Maps Foundation: huellas de edificios (tema buildings)"
FUENTE_SECUNDARIA = (
    "INEGI: DENUE, corte de mayo de 2026, Yucatán; " + relieve.FUENTE_PRIMARIA
)
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
        if fecha_obtencion is None and "fecha_obtencion" in malla.columns:
            fecha_obtencion = str(malla["fecha_obtencion"].iloc[0])
        if "capa" in malla.columns:
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


# ---------------------------------------------------------------------------
# Etapas del DAG
# ---------------------------------------------------------------------------

def ingesta(fecha: str | None = None, carpeta_local: str | Path | None = None) -> str:
    return relieve.ingesta_conjunto(DATASET, fecha, carpeta_local, respaldo=relieve.DATASET)


def plata(prefijo: str | None = None) -> int:
    """Celdas urbanas de la malla compartida -> plata."6.huella_construida.celdas_urbanas"."""
    tabla_malla = relieve.TABLAS_PLATA["malla"]
    # La malla compartida sirve si los crudos son los de relieve_5m (prefijo de ese
    # conjunto o sin prefijo). Si huella_construida trae crudos propios, se rearma.
    compartida = prefijo is None or prefijo.startswith(alm.prefijo(relieve.DATASET))
    if compartida and alm.existe(tabla_malla, alm.ESQUEMA_PLATA):
        log.info("Uso la malla de plata.%s", tabla_malla)
        malla = alm.leer(tabla_malla, alm.ESQUEMA_PLATA)
    else:
        malla = relieve.plata_conjunto(DATASET, prefijo, respaldo=relieve.DATASET)["malla"]
    urbanas = malla[malla["huella_m2"] >= relieve.HUELLA_MINIMA_M2]
    columnas = ["fila", "columna", "x_utm", "y_utm", "huella_m2", "altura_m", "negocios",
                "fecha_obtencion", "geometry"]
    urbanas = urbanas[columnas].reset_index(drop=True)
    alm.cargar({TABLA_PLATA: urbanas}, alm.ESQUEMA_PLATA)
    return len(urbanas)


def oro() -> float:
    """plata -> oro."6.huella_construida". Devuelve la cifra que se contrasta con el catálogo."""
    tabla = construir_oro(malla=alm.leer(TABLA_PLATA, alm.ESQUEMA_PLATA))
    alm.cargar({VIZ_ID: tabla}, alm.ESQUEMA_ORO)
    return valor_referencia(tabla)
