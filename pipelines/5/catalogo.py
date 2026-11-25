"""Equipo 5 · Catálogo: deja en PostgreSQL (oro."5.catalogo") qué fuente alimenta cada visualización.

Cada fila: viz_id, papel (primaria/secundaria), dataset, institucion, archivo, origen, fecha_obtencion, sha256.
El catalog/catalog.csv del repositorio (enlaces, valor de referencia, tolerancia) se mantiene en git.

Uso:  python pipelines/5/catalogo.py
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


def publicar() -> dict[str, pd.DataFrame]:
    filas = []
    for sub, s in comun.SUBTEMAS.items():
        for papel, ds in [("primaria", s["primaria"]), *[("secundaria", x) for x in s["secundarias"]]]:
            try:
                m = comun.metadatos(ds)
            except Exception:
                m = {}
            filas.append({"viz_id": f"5.{sub}", "papel": papel, "dataset": ds,
                          "institucion": comun.DATASETS[ds]["institucion"], "archivo": m.get("archivo"),
                          "origen": m.get("origen") or comun.DATASETS[ds].get("url") or comun.DATASETS[ds].get("enlace"),
                          "fecha_obtencion": m.get("fecha_obtencion"), "sha256": m.get("sha256")})
    t = {"5.catalogo": pd.DataFrame(filas)}
    comun.escribir("oro", t)
    return t


if __name__ == "__main__":
    print(publicar()["5.catalogo"].to_string())
