"""Equipo 4 · Inversión extranjera en Yucatán: del bronce a las tablas de oro.

El oro vive en PostgreSQL (servicio `postgres` del docker-compose), esquema `oro`, una tabla por visualización:
oro."4.ied_por_pais", oro."4.censos_economicos", etc. Cada tabla lleva las columnas de metadatos que pide la
arquitectura (viz_id, fuentes, institución, fecha, responsable). La conexión sale del `.env` de la raíz o de
`DATABASE_URL`.

Mientras MinIO no tenga los archivos, el bronce es la carpeta `datos/4/` (fuera de Git).

Uso:  docker compose up -d postgres
      python pipelines/4/oro.py        # reconstruye y publica todas las tablas de oro
"""
from __future__ import annotations

import os
import urllib.request
import zipfile
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sqlalchemy import URL, Engine, create_engine, inspect

RAIZ = Path(__file__).resolve().parents[2]
BRONCE = Path(os.environ.get("EQUIPO4_DATOS", RAIZ / "datos" / "4"))
ESQUEMA = "oro"
CONTEXTO = "4.turismo_contexto"  # tabla auxiliar: cifras de llegadas que cita el texto de la historia

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
}

INEGI_URL = {
    "inegi/ce2019_yuc_csv.zip":
        "https://www.inegi.org.mx/contenidos/programas/ce/2019/Datosabiertos/ce2019_yuc_csv.zip",
    "inegi/conjunto_de_datos_ce_yuc_2024_csv.zip":
        "https://www.inegi.org.mx/contenidos/programas/ce/2024/datosabiertos/conjunto_de_datos_ce_yuc_2024_csv.zip",
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


def _bronce(nombre: str) -> Path:
    ruta = BRONCE / nombre
    if not ruta.exists() and nombre in INEGI_URL:  # fuente con enlace directo: el proceso la descarga
        ruta.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(INEGI_URL[nombre], ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"Falta el archivo de bronce {ruta}")
    return ruta


def _metadatos(df: pd.DataFrame, viz_id: str) -> pd.DataFrame:
    m = META[viz_id]
    fecha = max(datetime.fromtimestamp(_bronce(a).stat().st_mtime).date() for a in m["archivos"])
    return df.assign(viz_id=viz_id, fuente_primaria=m["fuente_primaria"], fuente_secundaria=m["fuente_secundaria"],
                     institucion=m["institucion"], fecha_obtencion=fecha.isoformat(), responsable=m["responsable"])


def _xlsx(nombre: str) -> pd.DataFrame:
    """Lee un XLSX de Dalila y repara el texto que viene en doble codificación (YucatÃ¡n -> Yucatán)."""
    df = pd.read_excel(_bronce(nombre))

    def arreglar(v):
        if isinstance(v, str) and "Ã" in v:
            try:
                return v.encode("latin-1").decode("utf-8")
            except UnicodeError:
                return v
        return v
    return df.map(arreglar)


# ---------------------------------------------------------------- 4.ied_por_pais
def oro_ied_por_pais() -> pd.DataFrame:
    """Una fila por país de origen y año (2018-2025) con la IED neta hacia Yucatán, en millones de dólares."""
    d = pd.read_csv(_bronce("b2026_01t_act_ef_origen.csv"), encoding="utf-8-sig")
    d = d[(d.entidad_federativa == "Yucatán") & (d.pais_origen != "Total")].copy()
    d["anio"] = d.anio_trim.str[:4].astype(int)
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
def _totales_municipio(zip_nombre: str, csv_interno: str, col_ent: str, col_mun: str) -> pd.DataFrame:
    with zipfile.ZipFile(_bronce(zip_nombre)) as z, z.open(csv_interno) as f:
        d = pd.read_csv(f, dtype=str, encoding="utf-8-sig", index_col=False,
                        usecols=[col_ent, col_mun, "CODIGO", "ID_ESTRATO", "UE", "H001A", "A111A"])
    d = d.apply(lambda s: s.str.strip())
    total = d.CODIGO.fillna("").isin(["", "TOTAL DE SECTOR"]) & d.ID_ESTRATO.fillna("").eq("")
    d = d[total & d[col_mun].fillna("").ne("")]
    return pd.DataFrame({"cve_mun": d[col_mun].str.zfill(3), "ue": d.UE.astype(float),
                         "personal": d.H001A.astype(float), "produccion_mdp": d.A111A.astype(float)})


def oro_censos_economicos() -> pd.DataFrame:
    """Una fila por municipio de Yucatán: unidades, personal y producción bruta en 2018 (CE 2019) y 2023 (CE 2024)."""
    a = _totales_municipio("inegi/ce2019_yuc_csv.zip", "conjunto_de_datos/ce2019_yuc.csv", "ENTIDAD", "MUNICIPIO")
    b = _totales_municipio("inegi/conjunto_de_datos_ce_yuc_2024_csv.zip", "conjunto_de_datos/tr_ce_yuc_2024.csv",
                           "E03", "E04")
    with zipfile.ZipFile(_bronce("inegi/conjunto_de_datos_ce_yuc_2024_csv.zip")) as z, \
            z.open("catalogos/tc_entidad_municipio.csv") as f:
        cat = pd.read_csv(f, dtype=str, encoding="utf-8-sig")
    cat = cat[cat.E03 == "31"][["E04", "NOM_MUN"]].rename(columns={"E04": "cve_mun", "NOM_MUN": "municipio"})
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


def contexto_turismo() -> pd.DataFrame:
    """Llegadas y ocupación (SEFOTUR, nov 2025): secundaria que da cifras para el texto de la historia."""
    return _xlsx("02_llegada_turistas_ocupacion_yucatan.xlsx")


CONSTRUCTORES = {
    "4.ied_por_pais": oro_ied_por_pais,
    "4.censos_economicos": oro_censos_economicos,
    "4.ied_ranking_origen": oro_ied_ranking_origen,
    "4.turismo_derrama": oro_turismo_derrama,
}


CONSTRUCTORES = {**CONSTRUCTORES, CONTEXTO: contexto_turismo}


# ---------------------------------------------------------------- conexión a PostgreSQL (esquema oro)
def _env() -> dict:
    """Variables de entorno, completadas con el `.env` de la raíz (el mismo que usa docker compose)."""
    valores = {}
    ruta = RAIZ / ".env"
    if ruta.exists():
        for linea in ruta.read_text().splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip().strip("'\"")
    return {**valores, **os.environ}


@lru_cache(maxsize=None)
def motor() -> Engine:
    """Motor de SQLAlchemy hacia el PostgreSQL del docker compose. `DATABASE_URL` tiene prioridad."""
    e = _env()
    url = e.get("DATABASE_URL") or URL.create(
        "postgresql+psycopg2", username=e.get("POSTGRES_USER"), password=e.get("POSTGRES_PASSWORD"),
        host=e.get("POSTGRES_HOST", "localhost"), port=int(e.get("POSTGRES_PORT", 5432)),
        database=e.get("POSTGRES_DB"))
    return create_engine(url, pool_pre_ping=True)


def construir(*viz_ids: str) -> dict[str, pd.DataFrame]:
    """Reconstruye las tablas de oro pedidas (todas si no se indica ninguna) y las publica en el esquema oro.

    Primero se calculan todas en memoria; después se escriben en una sola transacción: o se confirman todas
    o PostgreSQL no queda con cambios parciales. Es idempotente: cada ejecución reemplaza las tablas.
    """
    tablas = {v: CONSTRUCTORES[v]() for v in (viz_ids or CONSTRUCTORES)}
    with motor().begin() as con:
        for v, df in tablas.items():
            df.to_sql(v, con, schema=ESQUEMA, if_exists="replace", index=False)
    return tablas


def leer(viz_id: str) -> pd.DataFrame:
    """Lee la tabla de oro vigente desde PostgreSQL; si no existe todavía, la construye y la publica."""
    if not inspect(motor()).has_table(viz_id, schema=ESQUEMA):
        return construir(viz_id)[viz_id]
    return pd.read_sql_table(viz_id, motor(), schema=ESQUEMA)


if __name__ == "__main__":
    for v, df in construir().items():
        print(f"{ESQUEMA}.\"{v}\"{'':{26 - len(v)}} {len(df):5} filas  ({date.today()})")
