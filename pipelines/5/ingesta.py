"""Equipo 5 · Ingesta: lleva las fuentes crudas a bronce (MinIO, bronze/5/{dataset}/fecha=AAAA-MM-DD/).

No transforma nada. Cada objeto guarda en sus metadatos: fecha-obtencion, origen y sha256.
Es idempotente: si el dataset ya está en bronce, no se vuelve a descargar. Las fuentes sin descarga
directa (Educacion_05 y la captura del gasto) se suben a mano; si faltan, la tarea falla y dice cuáles.

Uso:  docker compose up -d minio minio-init
      python pipelines/5/ingesta.py
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import urllib.request
from datetime import date
from pathlib import Path


def _comun():
    if "equipo5_comun" not in sys.modules:
        spec = importlib.util.spec_from_file_location("equipo5_comun", Path(__file__).with_name("comun.py"))
        sys.modules["equipo5_comun"] = m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    return sys.modules["equipo5_comun"]


comun = _comun()


def _descargar(url: str) -> tuple[str, str]:
    """Baja `url` a un archivo temporal (sin cargarlo entero en memoria) y devuelve (ruta, sha256)."""
    import hashlib
    h = hashlib.sha256()
    peticion = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(peticion, timeout=600) as r, tempfile.NamedTemporaryFile(delete=False) as f:
        while bloque := r.read(1 << 20):
            f.write(bloque)
            h.update(bloque)
    return f.name, h.hexdigest()


def ingerir() -> dict[str, str]:
    cliente = comun.minio()
    if not cliente.bucket_exists(comun.BUCKET):
        raise RuntimeError(f"No existe el bucket {comun.BUCKET}; levanta minio y minio-init del compose.")
    resultado, faltan = {}, []
    for dataset, d in comun.DATASETS.items():
        previa = comun.ultima_fecha(dataset)
        if previa:
            resultado[dataset] = f"ya en bronce (fecha={previa})"
            continue
        if not d["url"]:
            faltan.append(f"- {dataset}: {d['manual']}")
            resultado[dataset] = "FALTA (subir a mano)"
            continue
        hoy = date.today().isoformat()
        ruta, sha = _descargar(d["url"])
        try:
            cliente.fput_object(comun.BUCKET, f"{comun.EQUIPO}/{dataset}/fecha={hoy}/{d['archivo']}", ruta,
                                metadata={"fecha-obtencion": hoy, "origen": d["url"], "sha256": sha})
        finally:
            os.unlink(ruta)
        resultado[dataset] = f"descargado (fecha={hoy})"
    if faltan:
        raise FileNotFoundError("Faltan archivos que no se descargan solos:\n" + "\n".join(faltan))
    return resultado


if __name__ == "__main__":
    print(ingerir())
