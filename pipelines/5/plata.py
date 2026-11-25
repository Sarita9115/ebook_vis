"""Equipo 5 · Plata: del bronce (MinIO, bronze/5/) a tablas limpias en PostgreSQL, esquema `plata`.

Plata limpia, tipa y recorta a Campeche, Yucatán y Quintana Roo; no arma nada específico de una figura.
Tablas (todas en una sola transacción):

- plata."5.bronce_archivos"   qué se leyó de bronce: dataset, archivo, fecha de obtención, origen, sha256
- plata."5.educacion_05"      entidad, sexo, anio, valor (grado promedio de escolaridad, INEGI)
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


# ------------------------------------------------------------------ Educacion_05
# El Censo 1990 (tabulados de conteos, sin 'grado promedio') se guarda en bronce y se registra en
# plata."5.bronce_archivos"; no se transforma aquí.
def _es_anio(v) -> bool:
    try:
        n = float(v)
        return n == int(n) and 1990 <= int(n) <= 2035
    except (TypeError, ValueError):
        return False


def leer_inegi_ancho(datos: bytes) -> pd.DataFrame:
    """Educacion_05 (XLSX exportado de INEGI) -> entidad, sexo, anio, valor, solo de la península.

    Diseño real: una fila con los años (cada año repetido 3 veces), la fila siguiente con
    Total / Mujeres / Hombres, y debajo una fila por entidad (nombre en la primera columna).
    """
    hojas = pd.read_excel(io.BytesIO(datos), sheet_name=None, header=None, dtype=object)
    for nombre, crudo in hojas.items():
        fila = next((i for i in range(min(len(crudo), 60))
                     if sum(_es_anio(v) for v in crudo.iloc[i]) >= 3), None)
        if fila is None or fila + 1 >= len(crudo):
            continue
        sexos = {"total": "Total", "mujeres": "Mujeres", "hombres": "Hombres"}
        cols = {j: (int(float(a)), sexos[norm(b)]) for j, (a, b) in enumerate(zip(crudo.iloc[fila], crudo.iloc[fila + 1]))
                if _es_anio(a) and norm(b) in sexos}
        if not cols:
            continue
        print(f"hoja {nombre}: años en la fila {fila}, {len(cols)} columnas de datos")
        filas = []
        for _, r in crudo.iloc[fila + 2:].iterrows():
            ent = ENTIDADES.get(norm(re.sub(r"^\d+\s*", "", str(r.iloc[0]))))   # recorte a la península
            if not ent:
                continue
            for j, (anio, sexo) in cols.items():
                v = pd.to_numeric(r.iloc[j], errors="coerce")
                if pd.notna(v):
                    filas.append((ent, sexo, anio, float(v)))
        d = pd.DataFrame(filas, columns=["entidad", "sexo", "anio", "valor"])
        if not d.empty:
            return d
    raise ValueError("Educacion_05: no encontré la fila de años con Total/Mujeres/Hombres debajo, "
                     "ni las entidades Campeche, Quintana Roo o Yucatán. Revisa el XLSX.")


# ------------------------------------------------------------------ Pobreza municipal e IRS
COL_POBREZA = {
    "entidad": ["entidad_federativa", "entidad", "nom_ent", "nombre_entidad"],
    "municipio": ["municipio", "nom_mun", "nombre_municipio"],
    "anio": ["anio", "ano", "periodo", "year", "anio_medicion", "ano_medicion", "medicion", "anio_estimacion"],
    "pobreza": ["pobreza", "pobreza_porcentaje", "porcentaje_pobreza", "pobreza_pct", "pobreza_p"],
}


def _col(df, claves, que):
    for c in claves:
        if c in df.columns:
            return c
    raise KeyError(f"No encontré la columna de {que}. Columnas del archivo: {list(df.columns)}. "
                   "Ajusta COL_POBREZA en plata.py.")


def _cve_mun(clave_mun, clave_ent):
    """Clave INEGI de 5 dígitos como entero (31001 = Abalá); acepta '1001', '001' o '31001'."""
    c = pd.to_numeric(clave_mun, errors="coerce")
    return c.where(c >= 1000, c + pd.to_numeric(clave_ent, errors="coerce") * 1000)


def limpia_pobreza(datos: bytes) -> pd.DataFrame:
    df = comun.leer_csv_texto(datos)
    df.columns = [norm(c).replace(" ", "_") for c in df.columns]
    print("columnas pobreza_municipal:", list(df.columns)[:8], "...")
    ca, cp, cm = (_col(df, COL_POBREZA[k], k) for k in ("anio", "pobreza", "municipio"))
    exigir("clave_entidad" in df.columns and "clave_municipio" in df.columns,
           f"El CSV de pobreza debe traer clave_entidad y clave_municipio; trae {list(df.columns)[:10]}")
    df["ent"] = pd.to_numeric(df["clave_entidad"], errors="coerce")
    df = df[df["ent"].isin(list(comun.PENINSULA))].copy()               # recorte a la península
    df["entidad"] = df["ent"].astype(int).map(comun.PENINSULA)
    df["anio"] = pd.to_numeric(df[ca].astype(str).str[:4], errors="coerce")   # 'periodo' = 2020-01-01
    df["pobreza_pct"] = pd.to_numeric(df[cp].str.replace(",", "."), errors="coerce")
    if df["pobreza_pct"].max() <= 1.0:
        df["pobreza_pct"] *= 100
    df["municipio"] = df[cm].str.strip()
    df["municipio_norm"] = df["municipio"].map(norm)
    df["cve_mun"] = _cve_mun(df["clave_municipio"], df["ent"])
    return df.dropna(subset=["anio", "pobreza_pct"])[
        ["entidad", "cve_mun", "municipio", "municipio_norm", "anio", "pobreza_pct"]]


def _buscar(cols, incluye, excluye=()):
    for c in cols:
        n = norm(c)
        if incluye in n and not any(x in n for x in excluye):
            return c
    return None


def leer_irs(datos: bytes) -> pd.DataFrame:
    """ZIP del CONEVAL con un XLSX por año -> entidad, municipio, anio, irs, grado_rezago (península).

    Hoja 'Municipios' de cada XLSX: encabezado en 2-3 filas (los rótulos pueden estar en cualquiera),
    y una fila por municipio con la clave de entidad (04, 23, 31) en la primera columna.
    """
    filas, vistos = [], []
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        for info in z.infolist():
            m = re.search(r"(20\d{2})", info.filename)
            if not (info.filename.lower().endswith((".xlsx", ".xls")) and m):
                continue
            anio = int(m.group(1))
            hojas = pd.read_excel(io.BytesIO(z.read(info)), sheet_name=None, header=None, dtype=object)
            for nombre, crudo in hojas.items():
                r0 = next((i for i in range(min(len(crudo), 30))
                           if any(norm(v).startswith("clave entidad") for v in crudo.iloc[i] if isinstance(v, str))), None)
                if r0 is None:
                    continue
                etiquetas = {j: norm(" ".join(str(crudo.iat[i, j]) for i in range(r0, r0 + 3)
                                              if pd.notna(crudo.iat[i, j])))
                             for j in range(crudo.shape[1])}
                vistos.append(f"{info.filename}/{nombre}: " + " | ".join(f"{j}={e[:40]}" for j, e in etiquetas.items() if e))

                def col(incluye, excluye=()):
                    return next((j for j, e in etiquetas.items() if incluye in e and not any(x in e for x in excluye)), None)

                ck = col("clave municipio")
                cm = col("municipio", ("clave", "lugar", "numero"))
                ci = col("indice de rezago")
                cg = col("grado de rezago")
                if None in (ck, cm, ci, cg):
                    continue
                datos_h = crudo.iloc[r0 + 2:]
                clave = pd.to_numeric(datos_h.iloc[:, 0], errors="coerce")
                datos_h = datos_h[clave.isin(list(comun.PENINSULA))]      # recorte a la península
                clave = clave[datos_h.index].astype(int)
                print(f"IRS {anio} ({nombre}): {len(datos_h)} filas de la península")
                filas.append(pd.DataFrame({
                    "entidad": clave.map(comun.PENINSULA).values,
                    "cve_mun": _cve_mun(datos_h.iloc[:, ck], clave).values,
                    "municipio": datos_h.iloc[:, cm].astype(str).str.strip().values, "anio": anio,
                    "irs": pd.to_numeric(datos_h.iloc[:, ci], errors="coerce").values,
                    "grado_rezago": datos_h.iloc[:, cg].astype(str).str.strip().str.capitalize().values}))
                break
    exigir(filas, "No pude leer ningún XLSX del ZIP del IRS. Se busca 'Clave entidad' y rótulos de municipio, "
                  "índice y grado de rezago. Rótulos encontrados:\n" + "\n".join(vistos[:4]))
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


def _limpia_col(c) -> str:
    return str(c).replace("\ufeff", "").replace("ï»¿", "").strip().upper()


def leer_iter(datos: bytes) -> pd.DataFrame:
    """ZIP del ITER -> localidades de la península (sin renglones de totales) con ámbito rural/urbano."""
    pedidas = set(BASE_ITER) | set(INDICADORES_ITER.values()) | {"TVIVPARHAB"}   # TVIVPARHAB: base real de los VPH_*
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        info = max((i for i in z.infolist() if i.filename.lower().endswith(".csv")), key=lambda i: i.file_size)
        for enc in ("utf-8-sig", "latin-1"):
            try:
                partes = []
                with z.open(info) as f:
                    for ch in pd.read_csv(f, dtype=str, encoding=enc, chunksize=200_000, na_values=["*", "N/D"],
                                          usecols=lambda c: _limpia_col(c) in pedidas):
                        ch.columns = [_limpia_col(c) for c in ch.columns]
                        ch["ENTIDAD"] = pd.to_numeric(ch["ENTIDAD"], errors="coerce")
                        partes.append(ch[ch["ENTIDAD"].isin(comun.PENINSULA)])   # recorte a la península
                break
            except UnicodeDecodeError:
                continue
    df = pd.concat(partes, ignore_index=True)
    faltan = sorted(pedidas - {"TVIVPARHAB"} - set(df.columns))
    exigir(not faltan, f"El ITER no trae las columnas {faltan}. Revisa el diccionario de datos y ajusta "
                       "INDICADORES_ITER en plata.py.")
    base = "TVIVPARHAB" if "TVIVPARHAB" in df.columns else "VIVPAR_HAB"
    print(f"ITER: base de viviendas = {base}")
    for c in ["POBTOT", "VIVPAR_HAB", base, *INDICADORES_ITER.values()]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["VIV_BASE"] = df[base]
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
