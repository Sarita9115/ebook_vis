"""Limpieza y utilidades compartidas por los subtemas 1 a 4 del Equipo 6.

Lo usan densidad_unidades.py, aporte_pib.py, atraccion_capital.py y obra_publica.py. La carpeta "6" no es un
paquete: cada pipeline carga este archivo por ruta y queda registrado como `e6_limpieza`.

Todo lee archivos que ya se bajaron de bronce a una carpeta temporal (`alm.crudos`); nada abre rutas locales.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

BBOX_YUCATAN = dict(lat=(19.4, 21.8), lng=(-91.0, -87.3))
BBOX_PENINSULA = dict(lat=(17.5, 21.9), lng=(-92.6, -86.5))  # lo que cae fuera son coordenadas erróneas del DENUE
ENTIDADES = {"31": "Yucatán", "04": "Campeche", "23": "Quintana Roo"}
PENINSULA = ("Yucatán", "Campeche", "Quintana Roo")

# Personal ocupado: el DENUE solo da rangos. Se usa el punto medio; el último rango (251 y más) es un supuesto.
PERSONAS = {"0 a 5 personas": 3, "6 a 10 personas": 8, "11 a 30 personas": 20, "31 a 50 personas": 40,
            "51 a 100 personas": 75, "101 a 250 personas": 175, "251 y más personas": 400}


# ---------------------------------------------------------------- ingesta
def ingerir(alm, datasets, fecha=None, carpeta_local=None, urls=None) -> dict[str, str]:
    """Deja cada dataset en bronce y devuelve {dataset: prefijo}. Falla con la lista de lo que falte.

    - Si ya hay una partición en bronce (la subió Producción desde la consola de MinIO), la usa.
    - Si se da `carpeta_local` (solo pruebas), sube la subcarpeta con el nombre del dataset.
    - Si no está y hay enlace directo en `urls`, lo descarga con la fecha de obtención.
    """
    urls = urls or {}
    raiz = Path(carpeta_local) if carpeta_local else None
    destino, faltan = {}, []
    for d in datasets:
        if raiz is not None and (raiz / d).is_dir():
            destino[d] = alm.ingestar_carpeta_local(d, raiz / d, fecha)
            continue
        p = alm.prefijo_vigente(d)
        if p is None and urls.get(d):
            try:
                p = alm.ingestar_urls(d, urls[d], fecha)
            except Exception as e:  # sin red, enlace caído o sitio que bloquea la descarga
                alm.log.warning("No se pudo descargar %s: %s", d, e)
                p = None
        if p is None:
            faltan.append(d)
        else:
            destino[d] = p
    if faltan:
        rutas = "\n".join(f"  {alm.BUCKET_BRONZE}/{alm.prefijo(d, 'AAAA-MM-DD')}" for d in faltan)
        raise FileNotFoundError(f"Faltan {len(faltan)} datasets en bronce. Súbelos con esta ruta:\n{rutas}")
    return destino


def buscar(carpeta: Path, extension: str, patron: str | None = None) -> list[Path]:
    """Archivos con esa extensión (sin distinguir mayúsculas: el INEGI entrega .CSV y .XLSX) cuyo nombre cumple el patrón."""
    ext = "." + extension.lower().lstrip(".")
    return sorted(p for p in Path(carpeta).rglob("*") if p.is_file() and p.suffix.lower() == ext
                  and (patron is None or re.search(patron, p.name, re.I)))


# ---------------------------------------------------------------- DENUE
def csv_denue(carpeta: Path) -> Path:
    """El CSV principal del DENUE en una carpeta (suelto o dentro del zip abierto): el más grande.

    Ignora diccionarios, catálogos, metadatos y cualquier archivo que no sea CSV.
    """
    candidatos = [p for p in Path(carpeta).rglob("*") if p.is_file() and p.suffix.lower() == ".csv"
                  and not re.search(r"diccionario|catalogo|metadato", "/".join(p.parts[-3:]), re.I)]
    if not candidatos:
        raise FileNotFoundError(f"No hay un CSV del DENUE en {carpeta}")
    return max(candidatos, key=lambda p: p.stat().st_size)


def leer_csv(ruta: Path, **opciones) -> pd.DataFrame:
    for codificacion in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return pd.read_csv(ruta, encoding=codificacion, **opciones)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"No se pudo leer {Path(ruta).name} con ninguna codificación conocida.")


def leer_denue(carpeta: Path, columnas: tuple, bbox: dict | None = None) -> pd.DataFrame:
    """Columnas pedidas del DENUE; con `bbox`, las coordenadas fuera de la zona quedan en nulo."""
    d = leer_csv(csv_denue(carpeta), dtype=str, usecols=lambda c: c in columnas)
    if "id" in d:
        d["id"] = pd.to_numeric(d["id"], errors="coerce")
    if "cve_mun" in d:
        d["cve_mun"] = d["cve_mun"].str.strip().str.zfill(3)
    if "codigo_act" in d:
        d["codigo_act"] = d["codigo_act"].str.strip().str.zfill(6)
    if "per_ocu" in d:
        d["per_ocu"] = d["per_ocu"].str.strip()
    if bbox is not None:
        d["lat"] = pd.to_numeric(d["latitud"], errors="coerce")
        d["lng"] = pd.to_numeric(d["longitud"], errors="coerce")
        fuera = ~(d.lat.between(*bbox["lat"]) & d.lng.between(*bbox["lng"]))
        d.loc[fuera, ["lat", "lng"]] = np.nan
        d = d.drop(columns=["latitud", "longitud"])
    return d


# ---------------------------------------------------------------- Encuesta Intercensal 2025
def poblacion_entidad(ruta: Path, clave: str) -> int:
    """Población total de la entidad: hoja 04, fila «Total / Valor»."""
    x = pd.read_excel(ruta, sheet_name="04", header=None)
    f = x[(x[0].fillna("").astype(str).str.match(rf"^{clave}\s")) & (x[1] == "Total") & (x[2] == "Valor")]
    if f.empty:
        raise ValueError(f"No encontré la fila Total/Valor de la entidad {clave} en la hoja 04 de {Path(ruta).name}.")
    return int(float(f.iloc[0, 3]))


def poblacion_municipio(ruta: Path) -> pd.DataFrame:
    x = pd.read_excel(ruta, sheet_name="02", header=None)
    x = x[(x[2] == "Total") & (x[1].astype(str) != "Total")]  # fila total de edad por municipio
    val = x[x[3] == "Valor"].set_index(1)
    err = x[x[3] == "Error estándar"].set_index(1)
    filas = []
    for nombre, r in val.iterrows():
        m = re.match(r"(\d{3})\s+(.*?)(\*?)$", str(nombre).strip())
        if m:
            filas.append({"cve_mun": m.group(1), "municipio": m.group(2).strip(), "poblacion": int(float(r[4])),
                          "error_estandar": float(err.loc[nombre, 4]), "municipio_censado": bool(m.group(3))})
    d = pd.DataFrame(filas)
    if d.empty:
        raise ValueError("No encontré municipios en la hoja 02 de la Encuesta Intercensal de Yucatán.")
    return d


# ---------------------------------------------------------------- PIBE
BLOQUES = [  # (columna, patrón del título del bloque)
    ("constantes", r"^millones de pesos a precios de 2018$"),
    ("corrientes", r"^millones de pesos$"),
    ("var_const_pct", r"^variación porcentual anual en valores constantes$"),
    ("var_corr_pct", r"^variación porcentual anual en valores corrientes$"),
]
_ES_TITULO = re.compile(r"^(millones|variación|estructura|contribución|índice)", re.I)
_ES_SECTOR = re.compile(r"^(\d{2}(?:-\d{2})?)\s-\s(.*)$")


def _anio(v):
    m = re.match(r"^(\d{4})", str(v).strip())
    return int(m.group(1)) if m else None


def leer_pibe(ruta: Path) -> pd.DataFrame:
    x = pd.read_excel(ruta, sheet_name="Tabulado", header=None)
    entidad = str(x.iloc[2, 0]).split("/")[-1].strip()
    entidad = "Nacional" if entidad.lower().startswith("estados unidos") else entidad
    fila_anios = x.index[x[0].fillna("").astype(str).str.strip() == "Concepto"][0]
    anios = {j: _anio(x.iloc[fila_anios, j]) for j in range(1, x.shape[1]) if _anio(x.iloc[fila_anios, j])}
    revisada = {j: str(x.iloc[fila_anios, j]).strip().endswith("R") for j in anios}

    etiqueta = x[0].fillna("").astype(str).str.replace("_", "", regex=False).str.strip()
    valores = x.iloc[:, 1:].apply(pd.to_numeric, errors="coerce").notna().any(axis=1)
    inicios = [i for i in range(len(x)) if (not valores.iloc[i]) and _ES_TITULO.match(etiqueta.iloc[i])]
    inicios.append(len(x))

    tablas = []
    for k, ini in enumerate(inicios[:-1]):
        columna = None
        for col, patron in BLOQUES:
            if re.match(patron, etiqueta.iloc[ini], re.I):
                columna = col
        if columna is None:
            continue
        filas = []
        for i in range(ini + 1, inicios[k + 1]):
            et = etiqueta.iloc[i]
            if et.startswith("aB.1bP"):
                codigo, act, nivel = "PIB", "Producto interno bruto", "pib"
            elif et.lower().startswith("actividad económica total"):
                codigo, act, nivel = "VAB", "Valor agregado bruto total", "total"
            elif et.lower() in ("actividades primarias", "actividades secundarias", "actividades terciarias"):
                codigo, act, nivel = et.split()[-1][:3].upper(), et.capitalize(), "gran_actividad"
            else:
                m = _ES_SECTOR.match(et)
                if not m:
                    continue
                codigo, act, nivel = m.group(1), m.group(2).strip(), "sector"
            for j, a in anios.items():
                filas.append(dict(entidad=entidad, actividad_codigo=codigo, actividad=act, nivel=nivel, anio=a,
                                  **{columna: pd.to_numeric(x.iloc[i, j], errors="coerce")}))
        tablas.append(pd.DataFrame(filas))
    if not tablas:
        raise ValueError(f"No pude reconocer los bloques del PIBE en {Path(ruta).name}.")
    base = tablas[0]
    for t in tablas[1:]:
        base = base.merge(t, on=["entidad", "actividad_codigo", "actividad", "nivel", "anio"], how="outer")
    base["cifra_revisada"] = base.anio.map({a: revisada[j] for j, a in anios.items()})
    return base
