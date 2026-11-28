"""Equipo 4 · Plata: del bronce (MinIO, bronze/4/) a tablas limpias en PostgreSQL, esquema `plata`.

Plata limpia y tipa; no arma nada específico de una figura (eso es oro). Tablas:

- plata."4.bronce_archivos"      catálogo del bronce leído: archivo, fecha de obtención, origen, sha256.
- plata."4.ied_entidad_pais_trim" IED por entidad, país de origen y trimestre (SE), recortada a la península.
- plata."4.ce_municipio"          Censos Económicos (INEGI): totales por municipio de Yucatán, años 2018 y 2023.
- plata."4.ied_yucatan_trim_dm"   IED trimestral de Yucatán según la API de Data México (SE), en mdd.
- plata."4.remesas_yucatan_dm"    Remesas anuales de Yucatán según la API de Data México (Banxico), en mdd.
- plata."4.promesa_empleo_yucatan" Empleos prometidos (anuncio 2022) y registrados en el IMSS (documental).
- plata."4.<archivo xlsx>"        cada xlsx del equipo, con el texto en doble codificación reparado.
                                  ied_por_entidad_2018_2025 conserva las 32 entidades: oro calcula el lugar
                                  de Yucatán en el país.

Todas se escriben en una sola transacción.

Uso:  python pipelines/4/plata.py
"""
from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

import pandas as pd


def _comun():
    if "equipo4_comun" not in sys.modules:
        spec = importlib.util.spec_from_file_location("equipo4_comun", Path(__file__).with_name("comun.py"))
        sys.modules["equipo4_comun"] = m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    return sys.modules["equipo4_comun"]


comun = _comun()
ESQUEMA = "plata"
PENINSULA = ["Campeche", "Yucatán", "Quintana Roo"]

XLSX = [
    "ied_por_entidad_2018_2025.xlsx",
    "ied_yucatan_anual.xlsx",
    "ied_yucatan_origen.xlsx",
    "turismo_derrama_1T_2020_2026.xlsx",
    "turismo_derrama_trimestral_nacional_internacional.xlsx",
    "turismo_comparativos_4T_y_anual.xlsx",
    "02_llegada_turistas_ocupacion_yucatan.xlsx",
]
SE_CSV = "b2026_01t_act_ef_origen.csv"
CE_2019 = "inegi/ce2019_yuc_csv.zip"
CE_2024 = "inegi/conjunto_de_datos_ce_yuc_2024_csv.zip"
DM_IED = "datamexico/ied_yucatan_trimestral.json"
DM_REMESAS = "datamexico/remesas_yucatan_anual.json"
PROMESA = "documental/promesa_empleo_yucatan.json"


def _reparar_texto(v):
    """Repara texto en doble codificación (YucatÃ¡n -> Yucatán)."""
    if isinstance(v, str) and "Ã" in v:
        try:
            return v.encode("latin-1").decode("utf-8")
        except UnicodeError:
            return v
    return v


def plata_xlsx(nombre: str) -> pd.DataFrame:
    return pd.read_excel(comun.bajar(nombre)).map(_reparar_texto)


def plata_ied_entidad_pais_trim() -> pd.DataFrame:
    d = pd.read_csv(comun.bajar(SE_CSV), encoding="utf-8-sig")
    d = d[d.entidad_federativa.isin(PENINSULA)].copy()
    d["anio"] = d.anio_trim.str[:4].astype(int)
    d["trimestre"] = d.anio_trim.str[5:].astype(int)
    return d[["entidad_federativa", "pais_origen", "anio_trim", "anio", "trimestre", "ied_mdd"]]


def _totales_municipio(zip_nombre: str, csv_interno: str, col_ent: str, col_mun: str) -> pd.DataFrame:
    with zipfile.ZipFile(comun.bajar(zip_nombre)) as z, z.open(csv_interno) as f:
        d = pd.read_csv(f, dtype=str, encoding="utf-8-sig", index_col=False,
                        usecols=[col_ent, col_mun, "CODIGO", "ID_ESTRATO", "UE", "H001A", "A111A"])
    d = d.apply(lambda s: s.str.strip())
    total = d.CODIGO.fillna("").isin(["", "TOTAL DE SECTOR"]) & d.ID_ESTRATO.fillna("").eq("")
    d = d[total & d[col_mun].fillna("").ne("")]
    return pd.DataFrame({"cve_mun": d[col_mun].str.zfill(3), "ue": d.UE.astype(float),
                         "personal": d.H001A.astype(float), "produccion_mdp": d.A111A.astype(float)})


def plata_ce_municipio() -> pd.DataFrame:
    """Una fila por municipio y año de referencia: unidades económicas, personal ocupado y producción bruta."""
    a = _totales_municipio(CE_2019, "conjunto_de_datos/ce2019_yuc.csv", "ENTIDAD", "MUNICIPIO").assign(anio=2018)
    b = _totales_municipio(CE_2024, "conjunto_de_datos/tr_ce_yuc_2024.csv", "E03", "E04").assign(anio=2023)
    with zipfile.ZipFile(comun.bajar(CE_2024)) as z, z.open("catalogos/tc_entidad_municipio.csv") as f:
        cat = pd.read_csv(f, dtype=str, encoding="utf-8-sig")
    cat = cat[cat.E03 == "31"][["E04", "NOM_MUN"]].rename(columns={"E04": "cve_mun", "NOM_MUN": "municipio"})
    d = pd.concat([a, b]).merge(cat, on="cve_mun", how="left")
    return d[["anio", "cve_mun", "municipio", "ue", "personal", "produccion_mdp"]]


def _registros_datamexico(nombre: str) -> pd.DataFrame:
    """La API responde {"data": [...]} (o directamente la lista de registros)."""
    import json
    crudo = json.load(comun.bajar(nombre))
    return pd.DataFrame(crudo["data"] if isinstance(crudo, dict) else crudo)


def plata_ied_trim_dm() -> pd.DataFrame:
    """Una fila por trimestre: IED de Yucatán en millones de dólares (la API ya la publica en mdd)."""
    d = _registros_datamexico(DM_IED)
    t = d["Quarter"].astype(str)  # "2022-Q2"
    return pd.DataFrame({"anio": t.str[:4].astype(int), "trimestre": t.str[-1].astype(int),
                         "ied_mdd": d["Investment"].astype(float)}).sort_values(["anio", "trimestre"])


def plata_remesas_dm() -> pd.DataFrame:
    """Una fila por año: remesas recibidas en Yucatán. La API las publica en dólares; aquí en millones."""
    d = _registros_datamexico(DM_REMESAS)
    return pd.DataFrame({"anio": d["Year"].astype(int),
                         "remesas_mdd": d["Remittance Amount"].astype(float) / 1e6}).sort_values("anio")


def plata_promesa_empleo() -> pd.DataFrame:
    """Empleos prometidos en el anuncio de 2022 y empleos formales registrados en el IMSS (fuente documental)."""
    import json
    return pd.DataFrame(json.load(comun.bajar(PROMESA)))


def bronce_archivos() -> pd.DataFrame:
    nombres = [SE_CSV, CE_2019, CE_2024, DM_IED, DM_REMESAS, PROMESA, *XLSX]
    return pd.DataFrame([{"archivo": n, "objeto": f"{comun.BUCKET}/{comun.objeto(n)}", **comun.metadatos(n)}
                         for n in nombres])


def construir() -> dict[str, pd.DataFrame]:
    tablas = {
        "4.bronce_archivos": bronce_archivos(),
        "4.ied_entidad_pais_trim": plata_ied_entidad_pais_trim(),
        "4.ce_municipio": plata_ce_municipio(),
        "4.ied_yucatan_trim_dm": plata_ied_trim_dm(),
        "4.remesas_yucatan_dm": plata_remesas_dm(),
        "4.promesa_empleo_yucatan": plata_promesa_empleo(),
        **{f"4.{Path(n).stem}": plata_xlsx(n) for n in XLSX},
    }
    comun.escribir(ESQUEMA, tablas)
    return tablas


if __name__ == "__main__":
    for nombre, df in construir().items():
        print(f'{ESQUEMA}."{nombre}"{"":{56 - len(nombre)}} {len(df):6} filas')
