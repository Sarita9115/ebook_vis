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

Etapas (Airflow, dags/equipo_6.py):

- `ingesta()`: descarga los tres CSV de las URLs oficiales a
  bronze/6/gasto_publico/fecha=AAAA-MM-DD/.
- `plata()`:   lee la partición vigente de bronce y carga
  plata."6.gasto_publico" (los tres cortes al grano año × trimestre ×
  finalidad × dependencia, con la columna `corte`).
- `oro()`:     lee plata, verifica que los cortes III y IV de 2025 coincidan y
  carga oro."6.gasto_publico".

Prueba local (opcional y explícita): `ingesta(carpeta_local=...)` o la variable
E6_CRUDOS_GASTO_PUBLICO suben una carpeta de crudos a bronce en vez de
descargar; `construir_oro(dir_crudos)` arma el oro en memoria desde una carpeta dada.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from pathlib import Path

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

VIZ_ID = "6.gasto_publico"
DATASET = "gasto_publico"
TABLA_PLATA = VIZ_ID

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


def verificar_cortes(plata: pd.DataFrame, tolerancia: float = 0.01) -> None:
    """Los trimestres I a III de 2025 deben ser iguales en el corte III y en el IV."""
    def suma(corte):
        d = plata[(plata["corte"] == corte) & (plata["trimestre"] < 4)]
        return d.groupby(["trimestre", "finalidad"])["ejercido_mdp"].sum()

    dif = (suma("2025_t3") - suma("2025_t4")).abs().max()
    if pd.isna(dif) or dif > tolerancia:
        raise ValueError(f"Los cortes III y IV de 2025 difieren hasta {dif:.2f} mdp")


def construir_plata(dir_crudos: Path, fecha_obtencion: str | None = None) -> pd.DataFrame:
    """Los tres cortes, limpios y agregados al grano de la figura, con la columna `corte`."""
    dir_crudos = Path(dir_crudos)
    partes = []
    for corte, archivo in ARCHIVOS.items():
        g = _agrupar(leer_crudo(dir_crudos / archivo))
        g.insert(0, "corte", corte)
        partes.append(g)
    if fecha_obtencion is None:
        mtime = (dir_crudos / ARCHIVOS["2025_t4"]).stat().st_mtime
        fecha_obtencion = dt.date.fromtimestamp(mtime).isoformat()
    plata = pd.concat(partes, ignore_index=True)
    plata["fecha_obtencion"] = fecha_obtencion
    return plata


def oro_desde_plata(plata: pd.DataFrame) -> pd.DataFrame:
    """Tabla de oro a partir de plata."6.gasto_publico"."""
    verificar_cortes(plata)
    fecha_obtencion = str(plata["fecha_obtencion"].iloc[0])
    oro = plata[plata["corte"].isin(["2024_t4", "2025_t4"])].drop(columns=["corte", "fecha_obtencion"])
    oro = oro.reset_index(drop=True)
    oro["ejercido_mdp"] = oro["ejercido_mdp"].round(6)

    oro.insert(0, "viz_id", VIZ_ID)
    oro["fuente_primaria"] = FUENTE_PRIMARIA
    oro["fuente_secundaria"] = FUENTE_SECUNDARIA
    oro["institucion"] = INSTITUCION
    oro["fecha_obtencion"] = fecha_obtencion
    oro["responsable"] = RESPONSABLE
    return oro.sort_values(["anio", "trimestre", "finalidad", "dependencia"]).reset_index(drop=True)


def construir_oro(dir_crudos: Path, fecha_obtencion: str | None = None) -> pd.DataFrame:
    """Prueba local: crudos -> plata -> oro en memoria."""
    return oro_desde_plata(construir_plata(dir_crudos, fecha_obtencion))


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


# ---------------------------------------------------------------------------
# Etapas del DAG
# ---------------------------------------------------------------------------

def ingesta(fecha: str | None = None, carpeta_local: str | Path | None = None) -> str:
    """Fuentes con enlace directo -> bronce.

    Si se da una carpeta de crudos (argumento o E6_CRUDOS_GASTO_PUBLICO), se sube
    esa carpeta y solo se descarga lo que le falte.
    """
    urls = {ARCHIVOS[k]: URLS[k] for k in ARCHIVOS}
    local = alm.carpeta_local(DATASET, carpeta_local)
    if local is None:
        return alm.ingestar_urls(DATASET, urls, fecha)
    destino = alm.ingestar_carpeta_local(DATASET, local, fecha)
    alm.completar_urls(destino, urls)
    return destino


def plata(prefijo: str | None = None) -> int:
    """Bronce -> plata."6.gasto_publico"."""
    with alm.crudos(DATASET, prefijo) as (carpeta, fecha):
        tabla = construir_plata(carpeta, fecha)
    alm.cargar({TABLA_PLATA: tabla}, alm.ESQUEMA_PLATA)
    return len(tabla)


def oro() -> float:
    """plata -> oro."6.gasto_publico". Devuelve la cifra que se contrasta con el catálogo."""
    tabla = oro_desde_plata(alm.leer(TABLA_PLATA, alm.ESQUEMA_PLATA))
    alm.cargar({VIZ_ID: tabla}, alm.ESQUEMA_ORO)
    return valor_referencia(tabla)


if __name__ == "__main__":
    # Prueba local explícita: python pipelines/6/gasto_publico.py <carpeta_de_crudos>
    if len(sys.argv) < 2:
        sys.exit("Uso: gasto_publico.py <carpeta_de_crudos>  (en producción corre el DAG equipo_6)")
    tabla = construir_oro(Path(sys.argv[1]))
    print(tabla.head())
    print(resumen_fomento(tabla))
    print("valor_referencia:", valor_referencia(tabla))
