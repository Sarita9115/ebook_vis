"""Equipo 4 · Oro: de plata (PostgreSQL, esquema `plata`) a las tablas que dibuja cada figura (esquema `oro`).

Oro lee solo de plata; nunca del bronce. Una tabla por visualización: oro."4.ied_por_pais",
oro."4.censos_economicos", etc., más oro."4.turismo_contexto" (cifras que cita el texto de la historia).
Cada tabla lleva las columnas de metadatos que pide la arquitectura (viz_id, fuentes, institución, fecha de
obtención, responsable). La fecha de obtención sale del catálogo del bronce (plata."4.bronce_archivos").

Flujo completo:  python pipelines/4/ingesta.py   # fuentes -> MinIO bronze/4/
                 python pipelines/4/plata.py     # MinIO -> plata.*
                 python pipelines/4/oro.py       # plata.* -> oro.*
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import pandas as pd


def _comun():
    if "equipo4_comun" not in sys.modules:
        spec = importlib.util.spec_from_file_location("equipo4_comun", Path(__file__).with_name("comun.py"))
        sys.modules["equipo4_comun"] = m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    return sys.modules["equipo4_comun"]


comun = _comun()
ESQUEMA = "oro"
CONTEXTO = "4.turismo_contexto"  # tabla auxiliar: cifras de llegadas que cita el texto de la historia


def _plata(nombre: str) -> pd.DataFrame:
    return comun.leer_tabla("plata", nombre)

# ---------------------------------------------------------------- metadatos de cada visualización
META = {
    "4.ied_por_pais": dict(
        fuente_primaria="Secretaría de Economía – IED por entidad federativa y país de origen (datos.gob.mx), "
                        "corte 1T 2026",
        fuente_secundaria="Secretaría de Economía – Ficha estatal Yucatán 1T 2026 (principales países de origen)",
        institucion="Secretaría de Economía", responsable="Jorge",
        archivos=["b2026_01t_act_ef_origen.csv"]),
    "4.censos_economicos": dict(
        fuente_primaria="INEGI – Censos Económicos 2024, datos abiertos de Yucatán",
        fuente_secundaria="INEGI – Censos Económicos 2019, datos abiertos de Yucatán",
        institucion="INEGI", responsable="Jorge",
        archivos=["inegi/conjunto_de_datos_ce_yuc_2024_csv.zip", "inegi/ce2019_yuc_csv.zip"]),
    "4.ied_ranking_origen": dict(
        fuente_primaria="Secretaría de Economía – Estadística oficial de la IED y reportes CNIE (cifras originales "
                        "al 4T de cada año)",
        fuente_secundaria="SETY/SEFOET – Yucatán en Cifras; Portal de Datos Abiertos (ficha SE 1T 2026)",
        institucion="Secretaría de Economía", responsable="Dalila Ku",
        archivos=["ied_por_entidad_2018_2025.xlsx", "ied_yucatan_anual.xlsx", "ied_yucatan_origen.xlsx"]),
    "4.turismo_derrama": dict(
        fuente_primaria="SEFOTUR – Boletín de derrama económica 1T 2026 (serie 1T 2020-2026)",
        fuente_secundaria="SEFOTUR – Boletines 4T 2025 y trimestral nacional/internacional; "
                          "SEFOTUR – Llegada de turistas y ocupación (nov 2025)",
        institucion="SEFOTUR Yucatán", responsable="Dalila Ku",
        archivos=["turismo_derrama_1T_2020_2026.xlsx", "turismo_derrama_trimestral_nacional_internacional.xlsx",
                  "turismo_comparativos_4T_y_anual.xlsx", "02_llegada_turistas_ocupacion_yucatan.xlsx"]),
    "4.pulso_ied": dict(
        fuente_primaria="Secretaría de Economía – Data México: IED por estado y trimestre (API pública), Yucatán",
        fuente_secundaria="Secretaría de Economía – Estadística oficial de la IED por entidad federativa "
                          "(cifras anuales 2018-2025)",
        institucion="Secretaría de Economía", responsable="Yazira Hernández Rives",
        archivos=["datamexico/ied_yucatan_trimestral.json", "ied_por_entidad_2018_2025.xlsx"]),
    "4.promesa_resultado": dict(
        fuente_primaria="Gobierno de Yucatán – Anuncio de 245 proyectos de inversión privada (22 de junio de 2022)",
        fuente_secundaria="IMSS – Trabajadores asegurados en Yucatán, empleos generados oct 2018-abr 2024 "
                          "(boletín del Gobierno de Yucatán, mayo 2024)",
        institucion="Gobierno de Yucatán / IMSS", responsable="Yazira Hernández Rives",
        archivos=["promesa_empleo_yucatan.xlsx"]),
    "4.remesas_ied": dict(
        fuente_primaria="Banco de México – Ingresos por remesas por entidad (API pública de Data México), Yucatán",
        fuente_secundaria="Secretaría de Economía – Estadística oficial de la IED por entidad federativa "
                          "(cifras anuales 2018-2025)",
        institucion="Banco de México / Secretaría de Economía", responsable="Yazira Hernández Rives",
        archivos=["datamexico/remesas_yucatan_anual.json", "ied_por_entidad_2018_2025.xlsx"]),
}

# Coordenadas (lat, lon) de cada país para el mapa de flujos; Mérida es el destino.
MERIDA = (20.97, -89.62)
COORD = {
    "Estados Unidos de América": (39.5, -108.0), "Canadá": (55.0, -96.0), "España": (40.2, -3.7),
    "Francia": (46.6, 2.4), "China, República Popular de": (35.0, 104.0), "Reino Unido de la Gran Bretaña e "
    "Irlanda del Norte": (53.0, -1.5), "Alemania": (51.0, 10.4), "Países Bajos": (52.2, 5.5),
    "Bélgica": (50.6, 4.6), "Suiza": (46.8, 8.2), "Italia": (42.8, 12.5), "Irlanda": (53.3, -8.0),
    "Jamaica": (18.1, -77.3), "Cuba": (21.8, -79.0), "Panamá": (8.6, -80.1), "Honduras": (14.8, -86.6),
    "Colombia": (4.6, -74.1), "Venezuela, República Bolivariana de": (7.1, -66.2), "Ecuador": (-1.5, -78.4),
    "Perú": (-9.2, -75.0), "Brasil": (-10.8, -52.9), "Chile": (-33.5, -70.7), "Argentina": (-34.6, -64.0),
    "Japón": (36.2, 138.3), "Corea, República de": (36.5, 127.9), "Australia": (-25.3, 133.8),
    "Emiratos Árabes Unidos": (24.0, 54.0), "Jordania": (31.2, 36.5), "Nueva Zelandia": (-41.0, 174.0),
    "India": (22.0, 79.0), "Guatemala": (15.6, -90.3), "Hungría": (47.1, 19.5),
}
CORTO = {
    "Estados Unidos de América": "Estados Unidos", "China, República Popular de": "China",
    "Reino Unido de la Gran Bretaña e Irlanda del Norte": "Reino Unido",
    "Venezuela, República Bolivariana de": "Venezuela", "Corea, República de": "Corea del Sur",
    "Emiratos Árabes Unidos": "Emiratos Árabes",
}


def _metadatos(df: pd.DataFrame, viz_id: str) -> pd.DataFrame:
    m = META[viz_id]
    catalogo = _plata("4.bronce_archivos").set_index("archivo")
    fecha = max(catalogo.loc[a, "fecha_obtencion"] for a in m["archivos"])
    return df.assign(viz_id=viz_id, fuente_primaria=m["fuente_primaria"], fuente_secundaria=m["fuente_secundaria"],
                     institucion=m["institucion"], fecha_obtencion=fecha, responsable=m["responsable"])


def _xlsx(nombre: str) -> pd.DataFrame:
    """Tabla de plata que corresponde a un xlsx del equipo (ya con el texto reparado)."""
    return _plata(f"4.{Path(nombre).stem}")


# ---------------------------------------------------------------- 4.ied_por_pais
def oro_ied_por_pais() -> pd.DataFrame:
    """Una fila por país de origen y año (2018-2025) con la IED neta hacia Yucatán, en millones de dólares."""
    d = _plata("4.ied_entidad_pais_trim")
    d = d[(d.entidad_federativa == "Yucatán") & (d.pais_origen != "Total")].copy()
    trimestres = d.groupby("anio").anio_trim.nunique()
    d = d[d.anio.between(2018, 2025)]
    g = d.groupby(["pais_origen", "anio"], as_index=False).ied_mdd.sum()
    g = g[g.ied_mdd.abs() >= 0.005].rename(columns={"pais_origen": "pais"})
    g["pais_corto"] = g.pais.map(CORTO).fillna(g.pais)
    g["lat"] = g.pais.map(lambda p: COORD.get(p, (None, None))[0])
    g["lon"] = g.pais.map(lambda p: COORD.get(p, (None, None))[1])
    g["anio_completo"] = g.anio.map(trimestres).eq(4)
    g["dest_lat"], g["dest_lon"] = MERIDA
    return _metadatos(g.sort_values(["anio", "ied_mdd"], ascending=[True, False]), "4.ied_por_pais")


# ---------------------------------------------------------------- 4.censos_economicos
def oro_censos_economicos() -> pd.DataFrame:
    """Una fila por municipio de Yucatán: unidades, personal y producción bruta en 2018 (CE 2019) y 2023 (CE 2024)."""
    ce = _plata("4.ce_municipio")
    cat = ce[["cve_mun", "municipio"]].dropna().drop_duplicates("cve_mun")
    a = ce[ce.anio == 2018][["cve_mun", "ue", "personal", "produccion_mdp"]]
    b = ce[ce.anio == 2023][["cve_mun", "ue", "personal", "produccion_mdp"]]
    m = a.merge(b, on="cve_mun", suffixes=("_2018", "_2023")).merge(cat, on="cve_mun")
    for v in ("ue", "personal", "produccion_mdp"):
        m[f"cambio_{v}_pct"] = (m[f"{v}_2023"] / m[f"{v}_2018"] - 1) * 100
    x, y = m.cambio_ue_pct, m.cambio_personal_pct
    m["cuadrante"] = "Expansión"
    m.loc[(x < 0) & (y >= 0), "cuadrante"] = "Concentración"
    m.loc[(x >= 0) & (y < 0), "cuadrante"] = "Fragmentación"
    m.loc[(x < 0) & (y < 0), "cuadrante"] = "Retroceso"
    m["cve_geo"] = "31" + m.cve_mun
    return _metadatos(m.sort_values("personal_2023", ascending=False), "4.censos_economicos")


# ---------------------------------------------------------------- 4.ied_ranking_origen
def oro_ied_ranking_origen() -> pd.DataFrame:
    """Tabla larga para los cuatro paneles: serie (anual, participacion, ranking_2025, origen), categoria, valor."""
    ent = _xlsx("ied_por_entidad_2018_2025.xlsx")
    anual = _xlsx("ied_yucatan_anual.xlsx")
    origen = _xlsx("ied_yucatan_origen.xlsx")
    nac = ent[ent.entidad == "TOTAL NACIONAL"].iloc[0]
    yuc = ent[ent.entidad == "Yucatán"].iloc[0]
    filas = []
    for a in range(2018, 2026):
        col = f"ied_{a}_mdd"
        filas.append(("anual", str(a), yuc[col], None))
        filas.append(("participacion", str(a), yuc[col] / nac[col] * 100, None))
    estados = ent[ent.entidad != "TOTAL NACIONAL"][["entidad", "ied_2025_mdd"]]
    estados = estados.sort_values("ied_2025_mdd", ascending=False).reset_index(drop=True)
    estados["lugar"] = estados.index + 1
    for r in estados.itertuples():
        filas.append(("ranking_2025", r.entidad, r.ied_2025_mdd, r.lugar))
    ficha = origen[origen.periodo.astype(str).str.startswith("2018")]
    for r in ficha.itertuples():
        filas.append(("origen", r.pais_origen, float(r.ied_mdd), None))
    df = pd.DataFrame(filas, columns=["serie", "categoria", "valor", "lugar"])
    # Contraste con el reporte estatal (secundaria): lugar entre 32 entidades por año.
    lugares = anual.dropna(subset=["lugar_entre_32_entidades"])
    df = df.merge(lugares.assign(categoria=lugares.anio.astype(str), serie="anual")
                  [["serie", "categoria", "lugar_entre_32_entidades"]], on=["serie", "categoria"], how="left")
    df["lugar"] = df.lugar.fillna(df.pop("lugar_entre_32_entidades"))
    return _metadatos(df, "4.ied_ranking_origen")


# ---------------------------------------------------------------- 4.turismo_derrama
def oro_turismo_derrama() -> pd.DataFrame:
    """Tabla larga: serie (derrama_1t, gasto_1t, derrama_nacional, derrama_internacional, pct_internacional)."""
    t1 = _xlsx("turismo_derrama_1T_2020_2026.xlsx")
    tq = _xlsx("turismo_derrama_trimestral_nacional_internacional.xlsx")
    filas = []
    for r in t1.itertuples():
        filas += [("derrama_1t", str(r.anio), r.derrama_total_millones_pesos, "millones de pesos"),
                  ("gasto_1t", str(r.anio), r.gasto_promedio_diario_pesos, "pesos")]
    for r in tq.itertuples():
        p = f"{r.trimestre} {r.anio}"
        filas += [("derrama_nacional", p, r.derrama_nacionales_pesos / 1e6, "millones de pesos"),
                  ("derrama_internacional", p, r.derrama_internacionales_pesos / 1e6, "millones de pesos"),
                  ("pct_internacional", p, r.pct_turistas_noche_internacionales, "%")]
    return _metadatos(pd.DataFrame(filas, columns=["serie", "periodo", "valor", "unidad"]), "4.turismo_derrama")


# ---------------------------------------------------------------- 4.pulso_ied
def _ied_anual_se() -> pd.Series:
    """IED anual de Yucatán según la estadística oficial de la SE (secundaria), indexada por año."""
    ent = _xlsx("ied_por_entidad_2018_2025.xlsx")
    yuc = ent[ent.entidad == "Yucatán"].iloc[0]
    return pd.Series({a: float(yuc[f"ied_{a}_mdd"]) for a in range(2018, 2026) if f"ied_{a}_mdd" in yuc})


def oro_pulso_ied() -> pd.DataFrame:
    """Una fila por trimestre desde 2020: IED de Yucatán (Data México) y, como contraste, el total anual oficial."""
    d = _plata("4.ied_yucatan_trim_dm")
    d = d[d.anio >= 2020].copy()
    d["periodo"] = d.anio.astype(str) + "-T" + d.trimestre.astype(str)
    d["ied_anual_mdd"] = d.groupby("anio").ied_mdd.transform("sum")
    d["ied_anual_se_mdd"] = d.anio.map(_ied_anual_se())
    return _metadatos(d.reset_index(drop=True), "4.pulso_ied")


# ---------------------------------------------------------------- 4.promesa_resultado
def oro_promesa_resultado() -> pd.DataFrame:
    """Dos filas: empleos prometidos en el anuncio de 2022 y empleos formales registrados en el IMSS."""
    d = _xlsx("promesa_empleo_yucatan.xlsx")
    d = d[d.concepto.isin(["prometido", "registrado_imss"])].copy()
    prometido = float(d.loc[d.concepto == "prometido", "empleos"].iloc[0])
    d["pct_de_lo_prometido"] = d.empleos / prometido * 100
    return _metadatos(d.reset_index(drop=True), "4.promesa_resultado")


# ---------------------------------------------------------------- 4.remesas_ied
def oro_remesas_ied() -> pd.DataFrame:
    """Una fila por año completo (2020 en adelante): remesas (Banxico) e IED (SE) recibidas por Yucatán, en mdd."""
    r = _plata("4.remesas_yucatan_dm")
    ied = _ied_anual_se()
    d = r[r.anio.between(2020, int(ied.index.max()))].copy()
    d["ied_mdd"] = d.anio.map(ied)
    d["veces"] = d.remesas_mdd / d.ied_mdd
    return _metadatos(d.dropna(subset=["ied_mdd"]).reset_index(drop=True), "4.remesas_ied")


def contexto_turismo() -> pd.DataFrame:
    """Llegadas y ocupación (SEFOTUR, nov 2025): secundaria que da cifras para el texto de la historia."""
    return _xlsx("02_llegada_turistas_ocupacion_yucatan.xlsx")


CONSTRUCTORES = {
    "4.ied_por_pais": oro_ied_por_pais,
    "4.censos_economicos": oro_censos_economicos,
    "4.ied_ranking_origen": oro_ied_ranking_origen,
    "4.turismo_derrama": oro_turismo_derrama,
    "4.pulso_ied": oro_pulso_ied,
    "4.promesa_resultado": oro_promesa_resultado,
    "4.remesas_ied": oro_remesas_ied,
    CONTEXTO: contexto_turismo,
}


def construir(*viz_ids: str) -> dict[str, pd.DataFrame]:
    """Reconstruye las tablas de oro pedidas (todas si no se indica ninguna) y las publica en el esquema oro.

    Primero se calculan todas en memoria; después se escriben en una sola transacción: o se confirman todas
    o PostgreSQL no queda con cambios parciales. Es idempotente: cada ejecución reemplaza las tablas.
    """
    tablas = {v: CONSTRUCTORES[v]() for v in (viz_ids or CONSTRUCTORES)}
    comun.escribir(ESQUEMA, tablas)
    return tablas


def version(*viz_ids: str) -> tuple:
    """Huella barata de las tablas de oro, para saber si cambiaron sin volver a leerlas.

    Cambia cuando una tabla se reemplaza (su oid es otro: así publica `construir`) y cuando se insertan,
    modifican o borran filas en su lugar (cambian el conteo o el xmin máximo, p. ej. una fuente en streaming).
    """
    ids = viz_ids or tuple(CONSTRUCTORES)
    with comun.motor().connect() as con:
        oids = dict(con.exec_driver_sql(
            "select relname, oid from pg_class where relnamespace = 'oro'::regnamespace and relkind = 'r'").all())
        existentes = [v for v in ids if v in oids]
        filas = {}
        if existentes:
            consulta = " union all ".join(
                f"""select '{v.replace("'", "''")}', count(*), max(xmin::text::bigint) """
                f'''from {ESQUEMA}."{v.replace('"', '""')}"''' for v in existentes)
            filas = {n: (c, x) for n, c, x in con.exec_driver_sql(consulta).all()}
    return tuple((v, oids.get(v), *filas.get(v, (None, None))) for v in ids)


def leer(viz_id: str) -> pd.DataFrame:
    """Lee la tabla de oro vigente desde PostgreSQL; si no existe todavía, la construye desde plata."""
    try:
        return comun.leer_tabla(ESQUEMA, viz_id)
    except LookupError:
        return construir(viz_id)[viz_id]


if __name__ == "__main__":
    for v, df in construir().items():
        print(f"{ESQUEMA}.\"{v}\"{'':{26 - len(v)}} {len(df):5} filas  ({date.today()})")
