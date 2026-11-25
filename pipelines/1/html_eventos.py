"""Extractor mínimo de metadatos de páginas HTML descargadas (equipo 1).

Convierte cada archivo .html en una fila con título, fecha de publicación,
texto limpio y cifras candidatas ("10 jóvenes", "23 estudiantes"...). Las
cifras candidatas son una ayuda para capturar el evento: la fila final la
revisa una persona antes de entrar a la tabla de oro.

Uso:
    python pipelines/1/html_eventos.py CARPETA_HTML SALIDA.csv
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

_CIFRA = re.compile(r"\b(\d{1,3}(?:[.,]\d{3})*|\d+)\s+(estudiantes|alumnos|jóvenes|profesores|docentes|niñas|niños|personas)\b", re.I)
_FECHA_URL = re.compile(r"/(20\d{2})/(\d{2})/(\d{2})/")


def _meta(sopa: BeautifulSoup, *claves: str) -> str | None:
    for clave in claves:
        tag = sopa.find("meta", attrs={"property": clave}) or sopa.find("meta", attrs={"name": clave})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


def extraer(ruta: str | Path) -> dict:
    html = Path(ruta).read_text(encoding="utf-8", errors="ignore")
    sopa = BeautifulSoup(html, "lxml")
    for t in sopa(["script", "style", "nav", "footer", "header"]):
        t.decompose()
    titulo = _meta(sopa, "og:title") or (sopa.title.get_text(strip=True) if sopa.title else None)
    fecha = _meta(sopa, "article:published_time", "datePublished", "date")
    url = _meta(sopa, "og:url") or (sopa.find("link", rel="canonical") or {}).get("href")
    if not fecha and url:
        m = _FECHA_URL.search(url)
        fecha = "-".join(m.groups()) if m else None
    texto = " ".join(p.get_text(" ", strip=True) for p in sopa.find_all(["p", "li", "h1", "h2", "h3"]))
    cifras = [f"{n} {u.lower()}" for n, u in _CIFRA.findall(texto)]
    return {
        "archivo": Path(ruta).name,
        "titulo": titulo,
        "fecha_publicacion": (fecha or "")[:10] or None,
        "url": url,
        "cifras_candidatas": "; ".join(cifras) or None,
        "texto": texto,
    }


def carpeta_a_tabla(carpeta: str | Path) -> pd.DataFrame:
    filas = [extraer(p) for p in sorted(Path(carpeta).glob("*.htm*"))]
    return pd.DataFrame(filas)


if __name__ == "__main__":
    carpeta, salida = sys.argv[1:3]
    carpeta_a_tabla(carpeta).to_csv(salida, index=False, encoding="utf-8")
