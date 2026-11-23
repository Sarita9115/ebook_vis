"""Agrega el CSV consolidado del RIISP (SINAC 2008–2023) por residencia materna."""

from collections import Counter

import pandas as pd


def agregar_nacimientos(csv):
    """Lee la base de forma incremental y devuelve solo conteos de Yucatán."""
    campos = ["ENT_RES", "MUN_RES", "DATE_NACH"]
    conteos = Counter()
    for bloque in pd.read_csv(
        csv, usecols=campos, dtype=str, encoding="latin-1", chunksize=250_000,
    ):
        entidad = pd.to_numeric(bloque["ENT_RES"], errors="coerce")
        residentes = bloque.loc[entidad.eq(31)].copy()
        municipio = pd.to_numeric(residentes["MUN_RES"], errors="coerce")
        fecha = pd.to_datetime(residentes["DATE_NACH"].str.strip(),
                               format="%m/%d/%Y", errors="coerce")
        validos = municipio.between(1, 106) & fecha.dt.year.between(2008, 2023)
        subtotales = residentes.loc[validos].groupby(
            [municipio[validos].astype(int), fecha[validos].dt.year, fecha[validos].dt.month]
        ).size()
        conteos.update(subtotales.to_dict())

    # El consolidado cubre años completos. Ausencia de registros en un mes
    # cuenta como cero dentro de cada año y municipio presente en la fuente.
    filas = [
        (f"31{municipio:03}", anio, mes, conteos[municipio, anio, mes])
        for municipio, anio in sorted({(m, a) for m, a, _ in conteos})
        for mes in range(1, 13)
    ]
    return pd.DataFrame(filas, columns=["clave_municipio", "anio", "mes", "nacimientos"])


def preparar_oro(conteos, municipios):
    """Une el agregado a un catálogo local con nombre y coordenadas WGS84."""
    campos = ["clave_municipio", "municipio", "lat", "lon"]
    catalogo = municipios[campos].copy()
    catalogo["clave_municipio"] = catalogo["clave_municipio"].astype(str)
    oro = conteos.merge(catalogo, on="clave_municipio", how="left", validate="many_to_one")
    sin_geografia = oro[campos[1:]].isna().any(axis=1)
    if sin_geografia.any():
        faltantes = sorted(oro.loc[sin_geografia, "clave_municipio"].unique())
        raise ValueError(f"Falta nombre o coordenadas para los municipios {faltantes}.")
    return oro.assign(viz_id="3.natalidad")
