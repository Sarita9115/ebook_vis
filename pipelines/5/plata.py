"""Equipo 5 · Plata: del bronce (MinIO, bronze/5/) a tablas limpias en PostgreSQL, esquema `plata`.

Plata limpia, tipa y recorta a Campeche, Yucatán y Quintana Roo; no arma nada específico de una figura.
Tablas (todas en una sola transacción):

- plata."5.bronce_archivos"   qué se leyó de bronce: dataset, archivo, fecha de obtención, origen, sha256
- plata."5.educacion_05"      entidad, sexo, anio, valor (grado promedio de escolaridad, INEGI)
- plata."5.grado_1990"        entidad, sexo, anio, valor (Censo 1990)
- plata."5.pobreza_municipal" municipio, anio, pobreza_pct (CONEVAL)
- plata."5.irs_municipal"     municipio, anio, irs, grado_rezago (CONEVAL)
- plata."5.iter_2020", plata."5.iter_2010"  localidades con las variables de vivienda, con ámbito rural/urbano
- plata."5.gasto_educacion_2025"  flujos del gasto (captura de los Tomos II y VI)

Los lectores de INEGI y CONEVAL se escribieron sin ver los archivos reales: si un nombre de columna no
coincide, la tarea falla y el mensaje lista las columnas encontradas. Ahí se ajusta.

Uso:  python pipelines/5/plata.py
"""
from __future__ import annotations

import importlib.util
import io
import logging
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd


def _comun():
    if "equipo5_comun" not in sys.modules:
        spec = importlib.util.spec_from_file_location("equipo5_comun", Path(__file__).with_name("comun.py"))
        sys.modules["equipo5_comun"] = m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    return sys.modules["equipo5_comun"]


comun = _comun()
norm, exigir = comun.norm, comun.exigir
log = logging.getLogger(__name__)
ESQUEMA = "plata"
ENTIDADES = {norm(n): n for n in comun.PENINSULA.values()}   # 'yucatan' -> 'Yucatán'


# ------------------------------------------------------------------ Educacion_05 y Censo 1990
def _es_anio(v) -> bool:
    try:
        n = float(v)
        return n == int(n) and 1990 <= int(n) <= 2035
    except (TypeError, ValueError):
        return False


def leer_inegi_ancho(datos: bytes) -> pd.DataFrame:
    """Tabulado de INEGI en XLSX (años en columnas) -> entidad, sexo, anio, valor, de la península."""
    hojas = pd.read_excel(io.BytesIO(datos), sheet_name=None, header=None, dtype=object)
    for nombre, crudo in hojas.items():
        fila = next((i for i in range(min(len(crudo), 80))
                     if sum(_es_anio(v) for v in crudo.iloc[i]) >= 3), None)
        if fila is None:
            continue
        print(f"hoja {nombre}: encabezado de años en la fila {fila}")
        cols = {j: int(float(v)) for j, v in enumerate(crudo.iloc[fila]) if _es_anio(v)}
        primera = min(cols)
        sexos = {"total", "hombres", "mujeres"}
        entidad, filas = None, []
        for _, r in crudo.iloc[fila + 1:].iterrows():
            etiquetas = [str(x).strip() for x in r.iloc[:primera] if pd.notna(x) and str(x).strip()]
            if not etiquetas:
                continue
            if norm(etiquetas[-1]) in sexos:
                sexo = etiquetas[-1].capitalize()
                if len(etiquetas) >= 2:
                    entidad = etiquetas[0]
            else:
                entidad, sexo = etiquetas[0], "Total"
            for j, anio in cols.items():
                v = pd.to_numeric(r.iloc[j], errors="coerce")
                if pd.notna(v) and entidad:
                    filas.append((re.sub(r"^\d+\s*", "", entidad), sexo, anio, float(v)))
        d = pd.DataFrame(filas, columns=["entidad", "sexo", "anio", "valor"])
        d["entidad"] = d["entidad"].map(norm).map(ENTIDADES)        # recorte a la península
        d = d.dropna(subset=["entidad"])
        if not d.empty:
            return d
    raise ValueError("No encontré, en el XLSX de Educacion_05, una fila de encabezado con años (2000, 2005...) "
                     "ni las entidades de la península. Revisa el archivo y ajusta leer_inegi_ancho().")


def leer_grado_1990(datos: bytes) -> pd.DataFrame:
    """Grado promedio de escolaridad de la península en 1990 (Censo 1990)."""
    hojas = pd.read_excel(io.BytesIO(datos), sheet_name=None, header=None, dtype=object)
    for h in hojas.values():
        pos = [(i, j) for i in range(len(h)) for j in range(h.shape[1])
               if isinstance(h.iat[i, j], str) and "grado promedio" in norm(h.iat[i, j])]
        if not pos:
            continue
        j0, filas = pos[0][1], []
        for i in range(len(h)):
            ent = ENTIDADES.get(norm(re.sub(r"^\d+\s*", "", str(h.iat[i, 0]))))
            v = pd.to_numeric(h.iat[i, j0], errors="coerce")
            if ent and pd.notna(v):
                filas.append((ent, "Total", 1990, float(v)))
        if filas:
            return pd.DataFrame(filas, columns=["entidad", "sexo", "anio", "valor"]).drop_duplicates("entidad")
    raise ValueError("No encontré 'grado promedio' de las entidades de la península en el XLSX del Censo 1990. "
                     "Abre el archivo, localiza la tabla y ajusta leer_grado_1990().")


# ------------------------------------------------------------------ Pobreza municipal e IRS
COL_POBREZA = {
    "entidad": ["entidad_federativa", "entidad", "nom_ent", "nombre_entidad"],
    "municipio": ["municipio", "nom_mun", "nombre_municipio"],
    "anio": ["anio", "ano", "periodo", "year"],
    "pobreza": ["pobreza", "pobreza_porcentaje", "porcentaje_pobreza", "pobreza_pct", "pobreza_p"],
}


def _col(df, claves, que):
    for c in claves:
        if c in df.columns:
            return c
    raise KeyError(f"No encontré la columna de {que}. Columnas del archivo: {list(df.columns)}. "
                   "Ajusta COL_POBREZA en plata.py.")


def limpia_pobreza(datos: bytes) -> pd.DataFrame:
    df = comun.leer_csv_texto(datos)
    df.columns = [norm(c).replace(" ", "_") for c in df.columns]
    print("columnas pobreza_municipal:", list(df.columns))
    ce, cm, ca, cp = (_col(df, COL_POBREZA[k], k) for k in ("entidad", "municipio", "anio", "pobreza"))
    df["entidad"] = df[ce].map(norm).map(ENTIDADES)
    df = df.dropna(subset=["entidad"]).copy()                      # recorte a la península
    df["anio"] = pd.to_numeric(df[ca], errors="coerce")
    df["pobreza_pct"] = pd.to_numeric(df[cp].str.replace(",", "."), errors="coerce")
    if df["pobreza_pct"].max() <= 1.0:
        df["pobreza_pct"] *= 100
    df["municipio"] = df[cm].str.strip()
    df["municipio_norm"] = df["municipio"].map(norm)
    return df.dropna(subset=["anio", "pobreza_pct"])[["entidad", "municipio", "municipio_norm", "anio", "pobreza_pct"]]


def _buscar(cols, incluye, excluye=()):
    for c in cols:
        n = norm(c)
        if incluye in n and not any(x in n for x in excluye):
            return c
    return None


def leer_irs(datos: bytes) -> pd.DataFrame:
    """ZIP del CONEVAL con un XLSX por año -> entidad, municipio, anio, irs, grado_rezago (península)."""
    filas = []
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        for info in z.infolist():
            m = re.search(r"(20\d{2})", info.filename)
            if not (info.filename.lower().endswith((".xlsx", ".xls")) and m):
                continue
            anio = int(m.group(1))
            hojas = pd.read_excel(io.BytesIO(z.read(info)), sheet_name=None, header=None, dtype=object)
            for crudo in hojas.values():
                fila = next((i for i in range(min(len(crudo), 40))
                             if any(isinstance(v, str) and "grado de rezago" in norm(v) for v in crudo.iloc[i])), None)
                if fila is None:
                    continue
                df = crudo.iloc[fila + 1:].copy()
                df.columns = [str(c).strip() for c in crudo.iloc[fila]]
                cm = _buscar(df.columns, "municipio", ("clave", "lugar"))
                ce = _buscar(df.columns, "entidad", ("clave",))
                ci = _buscar(df.columns, "indice de rezago")
                cg = _buscar(df.columns, "grado de rezago")
                if not (cm and ci and cg and ce):
                    continue
                df = df.assign(_ent=df[ce].map(norm).map(ENTIDADES)).dropna(subset=["_ent", cm])
                print(f"IRS {anio}: {len(df)} municipios de la península")
                filas.append(pd.DataFrame({
                    "entidad": df["_ent"], "municipio": df[cm].astype(str).str.strip(), "anio": anio,
                    "irs": pd.to_numeric(df[ci], errors="coerce"),
                    "grado_rezago": df[cg].astype(str).str.strip().str.capitalize()}))
                break
    exigir(filas, "No pude leer ningún XLSX del ZIP del IRS. Se busca una fila con 'grado de rezago', "
                  "'índice de rezago', 'municipio' y 'entidad'. Revisa y ajusta leer_irs().")
    out = pd.concat(filas)
    out["municipio_norm"] = out["municipio"].map(norm)
    return out.dropna(subset=["irs"])


# ------------------------------------------------------------------ ITER (viviendas)
# VERIFICA estos nombres contra el diccionario de datos del ITER de cada censo.
INDICADORES_ITER = {
    "Agua entubada": "VPH_AGUADV", "Energía eléctrica": "VPH_C_ELEC", "Piso firme": "VPH_PISODT",
    "Acceso a Internet": "VPH_INTER", "Celular": "VPH_CEL", "Computadora": "VPH_PC",
}
BASE_ITER = ["ENTIDAD", "MUN", "NOM_MUN", "LOC", "NOM_LOC", "POBTOT", "VIVPAR_HAB"]
RURAL_MENOS_DE = 2500   # habitantes: criterio habitual de INEGI para localidad rural


def leer_iter(datos: bytes) -> pd.DataFrame:
    """ZIP del ITER -> localidades de la península (sin renglones de totales) con ámbito rural/urbano."""
    pedidas = set(BASE_ITER) | set(INDICADORES_ITER.values())
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        info = max((i for i in z.infolist() if i.filename.lower().endswith(".csv")), key=lambda i: i.file_size)
        for enc in ("utf-8-sig", "latin-1"):
            try:
                partes = []
                with z.open(info) as f:
                    for ch in pd.read_csv(f, dtype=str, encoding=enc, chunksize=200_000, na_values=["*", "N/D"],
                                          usecols=lambda c: c.strip().upper() in pedidas):
                        ch.columns = [c.strip().upper() for c in ch.columns]
                        ch["ENTIDAD"] = pd.to_numeric(ch["ENTIDAD"], errors="coerce")
                        partes.append(ch[ch["ENTIDAD"].isin(comun.PENINSULA)])   # recorte a la península
                break
            except UnicodeDecodeError:
                continue
    df = pd.concat(partes, ignore_index=True)
    faltan = sorted(pedidas - set(df.columns))
    exigir(not faltan, f"El ITER no trae las columnas {faltan}. Revisa el diccionario de datos y ajusta "
                       "INDICADORES_ITER en plata.py.")
    for c in ["POBTOT", "VIVPAR_HAB", *INDICADORES_ITER.values()]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[pd.to_numeric(df["LOC"], errors="coerce") != 0].copy()     # fuera los renglones de totales
    df["entidad"] = df["ENTIDAD"].astype(int).map(comun.PENINSULA)
    df["ambito"] = df["POBTOT"].map(lambda p: None if pd.isna(p) else ("Rural" if p < RURAL_MENOS_DE else "Urbano"))
    return df.dropna(subset=["ambito"]).drop(columns=["ENTIDAD"]).rename(columns=str.lower)


# ------------------------------------------------------------------ Gasto (captura de los Tomos II y VI)
def limpia_gasto(datos: bytes) -> pd.DataFrame:
    df = comun.leer_csv_texto(datos)
    df.columns = [norm(c).replace(" ", "_") for c in df.columns]
    exigir({"origen", "destino", "monto_millones"} <= set(df.columns),
           f"El CSV de gasto debe traer origen, destino, monto_millones; trae {list(df.columns)}")
    df["monto_millones"] = pd.to_numeric(df["monto_millones"].str.replace(",", ""), errors="coerce")
    df["origen"], df["destino"] = df["origen"].str.strip(), df["destino"].str.strip()
    vacios = df[df["monto_millones"].isna()]["destino"].tolist()
    exigir(not vacios, f"Faltan montos en el CSV de gasto para: {vacios}. Llena toda la plantilla.")
    for c in ("fuente_tomo", "pagina"):
        if c not in df.columns:
            df[c] = None
    return df[["origen", "destino", "monto_millones", "fuente_tomo", "pagina"]]


# ------------------------------------------------------------------ construcción de la capa
def construir() -> dict[str, pd.DataFrame]:
    fuentes, tablas, procedencia = {}, {}, []
    for ds in comun.USADOS_PLATA:
        fecha, archivos = comun.bajar(ds)
        fuentes[ds] = archivos
        m = comun.metadatos(ds)
        procedencia.append((ds, m["archivo"], m["fecha_obtencion"], m["origen"], m["sha256"], m["tamano_bytes"]))
    tablas["5.bronce_archivos"] = pd.DataFrame(
        procedencia, columns=["dataset", "archivo", "fecha_obtencion", "origen", "sha256", "tamano_bytes"])
    tablas["5.educacion_05"] = leer_inegi_ancho(comun.archivo(fuentes["educacion_05"], ".xlsx"))
    tablas["5.grado_1990"] = leer_grado_1990(comun.archivo(fuentes["censo_1990"], ".xlsx"))
    tablas["5.pobreza_municipal"] = limpia_pobreza(comun.archivo(fuentes["pobreza_municipal"], ".csv"))
    tablas["5.irs_municipal"] = leer_irs(comun.archivo(fuentes["irs_coneval"], ".zip"))
    tablas["5.iter_2020"] = leer_iter(comun.archivo(fuentes["iter_2020_yuc"], ".zip"))
    tablas["5.iter_2010"] = leer_iter(comun.archivo(fuentes["iter_2010_nal"], ".zip"))
    tablas["5.gasto_educacion_2025"] = limpia_gasto(comun.archivo(fuentes["gasto_educacion_captura"], ".csv"))
    comun.escribir(ESQUEMA, tablas)
    return tablas


if __name__ == "__main__":
    for n, d in construir().items():
        print(n, len(d), "filas")
