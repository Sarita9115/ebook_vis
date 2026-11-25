"""Equipo 5 · Oro: de plata (PostgreSQL, esquema `plata`) a las tablas que dibuja cada figura (esquema `oro`).

Oro lee solo de plata. Una tabla por visualización: oro."5.treinta_anos", oro."5.pobreza_rezago",
oro."5.la_casa_cambio" y oro."5.lo_que_se_invirtio". Cada una trae las columnas que usa
figures/5/{subtema}/figura.py más los metadatos que pide la arquitectura: viz_id, fuente_primaria,
fuente_secundaria, institucion, fecha_obtencion y responsable.

Uso:  python pipelines/5/oro.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


def _comun():
    if "equipo5_comun" not in sys.modules:
        spec = importlib.util.spec_from_file_location("equipo5_comun", Path(__file__).with_name("comun.py"))
        sys.modules["equipo5_comun"] = m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    return sys.modules["equipo5_comun"]


comun = _comun()
norm = comun.norm
ESQUEMA = "oro"
RESPONSABLE = comun.env().get("RESPONSABLE_EQUIPO5", "Yeimy")
TITULOS = {k: v["titulo"] for k, v in comun.SUBTEMAS.items()}


def _plata(nombre: str) -> pd.DataFrame:
    return comun.leer_tabla("plata", f"5.{nombre}")


def _con_meta(df: pd.DataFrame, subtema: str, fechas: pd.DataFrame) -> pd.DataFrame:
    s = comun.SUBTEMAS[subtema]
    prim = comun.DATASETS[s["primaria"]]
    f = fechas.loc[fechas["dataset"] == s["primaria"], "fecha_obtencion"]
    fecha = f.iloc[0] if len(f) else fechas["fecha_obtencion"].max()   # PDF primarios: fecha de la captura
    df = df.copy()
    df.insert(0, "viz_id", f"5.{subtema}")
    df["fuente_primaria"] = s["primaria"]
    df["fuente_secundaria"] = ", ".join(s["secundarias"])
    df["institucion"] = prim["institucion"]
    df["fecha_obtencion"] = fecha
    df["responsable"] = RESPONSABLE
    return df


def oro_treinta_anos() -> pd.DataFrame:
    d = _plata("educacion_05").rename(columns={"valor": "grado_promedio"})
    out = d[["anio", "entidad", "sexo", "grado_promedio"]].drop_duplicates(["anio", "entidad", "sexo"])
    return out.sort_values(["entidad", "sexo", "anio"]).reset_index(drop=True)


def oro_pobreza_rezago() -> pd.DataFrame:
    p, i = _plata("pobreza_municipal"), _plata("irs_municipal")
    anios = [2010, 2015, 2020]
    p = p[(p["entidad"] == "Yucatán") & p["anio"].isin(anios)]
    i = i[(i["entidad"] == "Yucatán") & i["anio"].isin(anios)]
    d = p.merge(i[["cve_mun", "anio", "irs", "grado_rezago"]], on=["cve_mun", "anio"], how="inner")
    print(f"pobreza: {len(p)} filas, IRS: {len(i)}, unidas: {len(d)}")
    return d[["municipio", "anio", "irs", "pobreza_pct", "grado_rezago"]].sort_values(["anio", "municipio"]).reset_index(drop=True)


def _porcentajes_iter(df: pd.DataFrame, anio: int) -> pd.DataFrame:
    from_plata = df[df["entidad"] == "Yucatán"]
    filas = []
    for ambito, g in from_plata.groupby("ambito"):
        for nombre, col in __import__("itertools").chain(_indicadores().items()):
            c = col.lower()
            ok = g[c].notna() & g["viv_base"].notna()      # los '*' (confidencial) no cuentan
            den = g.loc[ok, "viv_base"].sum()
            if den > 0:
                filas.append((nombre, anio, ambito, round(100 * g.loc[ok, c].sum() / den, 2)))
    return pd.DataFrame(filas, columns=["indicador", "anio", "ambito", "porcentaje"])


def _indicadores() -> dict:
    ruta = Path(__file__).with_name("plata.py")
    spec = importlib.util.spec_from_file_location("equipo5_plata_ind", ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.INDICADORES_ITER


def oro_la_casa_cambio() -> pd.DataFrame:
    return pd.concat([_porcentajes_iter(_plata("iter_2010"), 2010), _porcentajes_iter(_plata("iter_2020"), 2020)],
                     ignore_index=True)


def oro_lo_que_se_invirtio() -> pd.DataFrame:
    d = _plata("gasto_educacion_2025")
    return d[["origen", "destino", "monto_millones", "fuente_tomo", "pagina"]]


CONSTRUCTORES = {"treinta_anos": oro_treinta_anos, "pobreza_rezago": oro_pobreza_rezago,
                 "la_casa_cambio": oro_la_casa_cambio, "lo_que_se_invirtio": oro_lo_que_se_invirtio}


def version(*viz_ids: str) -> tuple:
    """Huella barata de las tablas de oro, para saber si cambiaron sin volver a leerlas (la usa la página)."""
    ids = viz_ids or tuple(f"5.{s}" for s in CONSTRUCTORES)
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
    """Lee la tabla de oro vigente desde PostgreSQL (la deja el DAG equipo_5)."""
    return comun.leer_tabla(ESQUEMA, viz_id)


def construir() -> dict[str, pd.DataFrame]:
    fechas = _plata("bronce_archivos")
    tablas = {f"5.{sub}": _con_meta(fn(), sub, fechas) for sub, fn in CONSTRUCTORES.items()}
    comun.escribir(ESQUEMA, tablas)
    return tablas


if __name__ == "__main__":
    for n, d in construir().items():
        print(n, len(d), "filas")
