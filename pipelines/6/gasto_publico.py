"""Tabla de oro de 6.gasto_publico.

Gasto público estatal y fomento económico: hacia dónde va el presupuesto de Yucatán.

Fuentes (Gobierno del Estado de Yucatán, datos abiertos de egresos):

- Primaria:   Datos_abiertos_triemstre_4_2025.csv  (ejercicio 2025, trimestres I a IV)
- Secundaria: egresos_IVTrim_2024.csv              (ejercicio 2024, comparación)
- Secundaria: Datos_abiertos_triemstre_3_2025.csv  (corte al III trimestre; solo
  se usa para verificar que los trimestres I a III de 2025 no cambiaron)

Lo que se sabe de los crudos (verificado al descargarlos):

- Los tres archivos son CSV ASCII, separados por coma, con 14 columnas iguales:
  ANIO, TIPO_GASTO, RAMO, TIPO_PROG, CLASIF_FUN, CLASIF_ADMIN, CLASIF_SECTOR, ENT,
  FUENTE DE FINANCIAMIENTO, GENERICA, PROG_NOPROG, SECTOR, EJERCIDO, TRIM.
- EJERCIDO es el monto de cada trimestre (no acumulado). Cada combinación aparece
  una vez por trimestre; el trimestre todavía no reportado viene en cero.
- El archivo no declara la unidad. Por su orden de magnitud (56,713 en 2025) es
  millones de pesos corrientes; así se rotula.
- CLASIF_FUN trae la finalidad de la clasificación funcional del CONAC:
  01 Gobierno, 02 Desarrollo social, 03 Desarrollo económico y 04 Otras no
  clasificadas (participaciones a municipios y deuda pública).
- Hay montos negativos (reintegros y ajustes). Se conservan: forman parte del
  ejercido que publica la fuente.

La tabla de oro queda al grano año × trimestre × finalidad × dependencia (RAMO).
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

VIZ_ID = "6.gasto_publico"

URL_BASE = "https://www.yucatan.gob.mx/docs/transparencia/datos_abiertos/"
ARCHIVOS = {
    "2025_t4": "Datos_abiertos_triemstre_4_2025.csv",
    "2025_t3": "Datos_abiertos_triemstre_3_2025.csv",
    "2024_t4": "egresos_IVTrim_2024.csv",
}
URLS = {
    "2025_t4": URL_BASE + "2025/Datos_abiertos_triemstre_4_2025.csv",
    "2025_t3": URL_BASE + "2025/Datos_abiertos_triemstre_3_2025.csv",
    "2024_t4": URL_BASE + "egresos_IVTrim_2024.csv",
}

FUENTE_PRIMARIA = "Gobierno de Yucatán: Egresos 4.º trimestre 2025 (datos abiertos)"
FUENTE_SECUNDARIA = (
    "Gobierno de Yucatán: Egresos 4.º trimestre 2024 y 3.er trimestre 2025 (datos abiertos)"
)
INSTITUCION = "Gobierno del Estado de Yucatán"
RESPONSABLE = "Gio Soriano"

COLUMNAS_CRUDAS = [
    "ANIO", "TIPO_GASTO", "RAMO", "TIPO_PROG", "CLASIF_FUN", "CLASIF_ADMIN",
    "CLASIF_SECTOR", "ENT", "FUENTE DE FINANCIAMIENTO", "GENERICA",
    "PROG_NOPROG", "SECTOR", "EJERCIDO", "TRIM",
]

TRIMESTRES = {"I TRIM": 1, "II TRIM": 2, "III TRIM": 3, "IV TRIM": 4}

FINALIDADES = {
    "01": "Gobierno",
    "02": "Desarrollo social",
    "03": "Desarrollo económico",
    "04": "Otras no clasificadas",
}
FINALIDAD_ECONOMICA = "Desarrollo económico"

# Los crudos vienen en mayúsculas y sin acentos. Solo se restituyen acentos.
_ACENTOS = {
    "secretaria": "Secretaría", "economia": "Economía", "turistico": "Turístico",
    "administracion": "Administración", "tecnologia": "Tecnología",
    "innovacion": "Innovación", "educacion": "Educación", "publica": "Pública",
    "publicas": "Públicas", "autonoma": "Autónoma", "yucatan": "Yucatán",
    "fiscalia": "Fiscalía", "investigacion": "Investigación",
    "participacion": "Participación", "agencia": "Agencia",
}
_MINUSCULAS = {"de", "del", "la", "las", "los", "y", "e", "el", "a", "para", "en"}


def _etiqueta(texto: str) -> str:
    palabras = []
    for i, p in enumerate(str(texto).strip().lower().split()):
        limpio = p.strip(",")
        if limpio in _ACENTOS:
            nueva = _ACENTOS[limpio]
        elif i > 0 and limpio in _MINUSCULAS:
            nueva = limpio
        else:
            nueva = limpio.capitalize()
        palabras.append(nueva + ("," if p.endswith(",") else ""))
    return " ".join(palabras)


def leer_crudo(ruta: Path) -> pd.DataFrame:
    """Lee un CSV de egresos y valida que traiga las columnas esperadas."""
    df = pd.read_csv(ruta, dtype=str, encoding="utf-8")
    faltan = set(COLUMNAS_CRUDAS) - set(df.columns)
    if faltan:
        raise ValueError(f"{ruta.name}: faltan columnas {sorted(faltan)}")
    df["EJERCIDO"] = pd.to_numeric(df["EJERCIDO"], errors="raise")
    df["trimestre"] = df["TRIM"].str.strip().map(TRIMESTRES)
    if df["trimestre"].isna().any():
        raise ValueError(f"{ruta.name}: trimestre no reconocido")
    df["finalidad"] = df["CLASIF_FUN"].str[:2].map(FINALIDADES)
    if df["finalidad"].isna().any():
        raise ValueError(f"{ruta.name}: finalidad no reconocida")
    return df


def _agrupar(df: pd.DataFrame) -> pd.DataFrame:
    g = (
        df.groupby(["ANIO", "trimestre", "finalidad", "RAMO"], as_index=False)["EJERCIDO"]
        .sum()
        .rename(columns={"ANIO": "anio", "RAMO": "dependencia", "EJERCIDO": "ejercido_mdp"})
    )
    g["anio"] = g["anio"].astype(int)
    g["trimestre"] = g["trimestre"].astype(int)
    g["dependencia"] = g["dependencia"].map(_etiqueta)
    return g


def verificar_cortes(t3: pd.DataFrame, t4: pd.DataFrame, tolerancia: float = 0.01) -> None:
    """Los trimestres I a III de 2025 deben ser iguales en el corte III y en el IV."""
    a = t3[t3["trimestre"] < 4].groupby(["trimestre", "finalidad"])["EJERCIDO"].sum()
    b = t4[t4["trimestre"] < 4].groupby(["trimestre", "finalidad"])["EJERCIDO"].sum()
    dif = (a - b).abs().max()
    if dif > tolerancia:
        raise ValueError(f"Los cortes III y IV de 2025 difieren hasta {dif:.2f} mdp")


def construir_oro(dir_crudos: Path, fecha_obtencion: str | None = None) -> pd.DataFrame:
    """Lee los tres crudos y devuelve la tabla de oro de 6.gasto_publico."""
    dir_crudos = Path(dir_crudos)
    t4_2025 = leer_crudo(dir_crudos / ARCHIVOS["2025_t4"])
    t3_2025 = leer_crudo(dir_crudos / ARCHIVOS["2025_t3"])
    t4_2024 = leer_crudo(dir_crudos / ARCHIVOS["2024_t4"])
    verificar_cortes(t3_2025, t4_2025)

    oro = pd.concat([_agrupar(t4_2024), _agrupar(t4_2025)], ignore_index=True)
    oro["ejercido_mdp"] = oro["ejercido_mdp"].round(6)

    if fecha_obtencion is None:
        mtime = (dir_crudos / ARCHIVOS["2025_t4"]).stat().st_mtime
        fecha_obtencion = dt.date.fromtimestamp(mtime).isoformat()

    oro.insert(0, "viz_id", VIZ_ID)
    oro["fuente_primaria"] = FUENTE_PRIMARIA
    oro["fuente_secundaria"] = FUENTE_SECUNDARIA
    oro["institucion"] = INSTITUCION
    oro["fecha_obtencion"] = fecha_obtencion
    oro["responsable"] = RESPONSABLE
    return oro.sort_values(["anio", "trimestre", "finalidad", "dependencia"]).reset_index(drop=True)


def resumen_fomento(oro: pd.DataFrame) -> pd.DataFrame:
    """Monto y porcentaje de la finalidad Desarrollo económico por año."""
    total = oro.groupby("anio")["ejercido_mdp"].sum()
    eco = oro[oro["finalidad"] == FINALIDAD_ECONOMICA].groupby("anio")["ejercido_mdp"].sum()
    return pd.DataFrame({
        "total_mdp": total.round(2),
        "desarrollo_economico_mdp": eco.round(2),
        "porcentaje": (100 * eco / total).round(2),
    })


def valor_referencia(oro: pd.DataFrame, anio: int = 2025) -> float:
    """Porcentaje del ejercido anual que va a Desarrollo económico (valor del catálogo)."""
    return float(resumen_fomento(oro).loc[anio, "porcentaje"])


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[2]
    crudos = Path(sys.argv[1]) if len(sys.argv) > 1 else raiz / "local_avances/datos_crudos/gasto_publico"
    tabla = construir_oro(crudos)
    print(tabla.head())
    print(resumen_fomento(tabla))
    print("valor_referencia:", valor_referencia(tabla))
