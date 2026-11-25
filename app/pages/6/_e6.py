"""Piezas compartidas por las páginas del Equipo 6 (Dinámica empresarial).

Dash no registra este archivo como página porque empieza con "_".

Qué hace:

- Lee la tabla de oro de cada visualización. Primero intenta el esquema `oro`
  de PostgreSQL (lo que dice la arquitectura); si la conexión no está
  configurada o falla, usa la copia de prueba `local_avances/oro_<subtema>.parquet`.
- Importa `figura(datos)` desde `figures/6/<subtema>/figura.py`, sin
  redibujarla, y guarda la figura en caché mientras la tabla no cambie.
- Arma las piezas de la plantilla: encabezado, ventana con la figura y la
  ficha con fuentes, fecha y responsable (de oro) y la lectura (del catálogo).

Variable de entorno opcional:

    ORO_DB_URL=postgresql+psycopg2://usuario:clave@host:5432/vis

La tabla se busca como oro."<viz_id>" (por ejemplo, oro."6.gasto_publico").
"""

from __future__ import annotations

import csv
import importlib.util
import logging
import os
import time
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html

RAIZ = Path(__file__).resolve().parents[3]
LOCAL = RAIZ / "local_avances"
CATALOGO = RAIZ / "catalog" / "catalog.csv"
EQUIPO = "6"
REFRESCO_BD_S = 300

log = logging.getLogger("equipo6")

# Orden de las escenas del capítulo, para la navegación entre páginas.
ESCENAS = [
    ("densidad_unidades", "/6/densidad_unidades", "Puerta DENUE / SAIC"),
    ("aporte_pib", "/6/aporte_pib", "Bóveda del PIB"),
    ("atraccion_capital", "/6/atraccion_capital", "Fábrica de IED"),
    ("obra_publica", "/6/obra_publica", "Obras y Municipios"),
    ("gasto_publico", "/6/gasto_publico", "Palacio de Presupuesto"),
    ("cambio_suelo", "/6/cambio_suelo", "Expansión Mérida–Progreso"),
    ("corredor_industrial", "/6/corredor_industrial", "Corredor Industrial"),
    ("relieve_5m", "/6/relieve_5m", "Monumento a la Patria"),
    ("huella_construida", "/6/huella_construida", "Fuente de la Ixtabay"),
]

GRAFICA_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

def _leer_bd(viz_id: str):
    url = os.environ.get("ORO_DB_URL")
    if not url:
        return None
    try:
        import geopandas as gpd
        from sqlalchemy import create_engine, inspect

        motor = create_engine(url)
        columnas = {c["name"] for c in inspect(motor).get_columns(viz_id, schema="oro")}
        consulta = f'SELECT * FROM oro."{viz_id}"'
        if "geometry" in columnas:
            return gpd.read_postgis(consulta, motor, geom_col="geometry")
        return pd.read_sql(consulta, motor)
    except Exception as error:  # la página no se cae: pasa al respaldo local
        log.warning("No se pudo leer oro.%s en PostgreSQL (%s); uso la copia local.", viz_id, error)
        return None


def _leer_local(subtema: str):
    ruta = LOCAL / f"oro_{subtema}.parquet"
    if not ruta.exists():
        raise FileNotFoundError(
            f"No está la tabla de oro de prueba {ruta.relative_to(RAIZ)}. "
            f"Corre local_avances/test_{subtema}.py para generarla."
        )
    try:
        import geopandas as gpd
        return gpd.read_parquet(ruta)
    except Exception:
        return pd.read_parquet(ruta)  # tabla sin geometría


def _sello(subtema: str) -> tuple:
    """Cambia cuando la tabla puede haber cambiado; invalida la caché."""
    if os.environ.get("ORO_DB_URL"):
        return ("bd", int(time.time() // REFRESCO_BD_S))
    ruta = LOCAL / f"oro_{subtema}.parquet"
    return ("local", ruta.stat().st_mtime if ruta.exists() else 0)


@lru_cache(maxsize=16)
def _oro(subtema: str, sello: tuple):
    datos = _leer_bd(f"{EQUIPO}.{subtema}")
    if datos is None:
        datos = _leer_local(subtema)
    return datos


def oro(subtema: str):
    return _oro(subtema, _sello(subtema))


@lru_cache(maxsize=8)
def _modulo_figura(subtema: str):
    ruta = RAIZ / "figures" / EQUIPO / subtema / "figura.py"
    spec = importlib.util.spec_from_file_location(f"figura_{EQUIPO}_{subtema}", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@lru_cache(maxsize=16)
def _figura(subtema: str, sello: tuple) -> go.Figure:
    return _modulo_figura(subtema).figura(_oro(subtema, sello))


def figura(subtema: str) -> go.Figure:
    """La misma figura del PDF, o un aviso si falta la tabla de oro."""
    try:
        return _figura(subtema, _sello(subtema))
    except Exception as error:
        log.exception("Falló la figura %s.%s", EQUIPO, subtema)
        aviso = go.Figure()
        aviso.add_annotation(text=str(error), showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper",
                             font=dict(size=14, color="#6B6457"))
        aviso.update_layout(xaxis_visible=False, yaxis_visible=False, plot_bgcolor="#FFFFFF",
                            paper_bgcolor="#FFFFFF", height=320)
        return aviso


@lru_cache(maxsize=1)
def _catalogo() -> dict:
    with open(CATALOGO, newline="", encoding="utf-8") as f:
        return {fila["viz_id"]: fila for fila in csv.DictReader(f)}


def catalogo(subtema: str) -> dict:
    return _catalogo().get(f"{EQUIPO}.{subtema}", {})


def valor_catalogo(subtema: str) -> float | None:
    try:
        return float(catalogo(subtema).get("valor_referencia") or "nan")
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Piezas de la plantilla
# ---------------------------------------------------------------------------

def encabezado(subtema: str, escena: str) -> html.Header:
    titulo = catalogo(subtema).get("subtema", subtema)
    return html.Header(className="e6-encabezado", children=[
        html.P(f"Equipo 6 · Dinámica empresarial · {escena}", className="e6-antetitulo"),
        html.H1(titulo, className="e6-titulo"),
    ])


def ficha(subtema: str, lectura: str) -> html.Section:
    """Lectura breve, fuentes, fecha de obtención y responsable."""
    campos = []
    try:
        fila = oro(subtema).iloc[0]
        for etiqueta, columna in (
            ("Fuente primaria", "fuente_primaria"),
            ("Fuente secundaria", "fuente_secundaria"),
            ("Institución", "institucion"),
            ("Fecha de obtención", "fecha_obtencion"),
            ("Responsable del procesamiento", "responsable"),
        ):
            if columna in fila.index and pd.notna(fila[columna]):
                campos += [html.Dt(etiqueta), html.Dd(str(fila[columna]))]
    except Exception as error:
        campos = [html.Dt("Datos"), html.Dd(str(error))]
    return html.Section(className="e6-ficha", children=[
        html.P(lectura, className="e6-lectura"),
        html.Dl(campos, className="e6-fuentes"),
    ])


def grafica(prefijo: str, altura: int, ancho_minimo: int = 0) -> html.Div:
    """Contenedor de la figura; se llena al abrir la escena."""
    estilo = {"minWidth": f"{ancho_minimo}px"} if ancho_minimo else {}
    return html.Div(className="e6-grafica-marco", children=html.Div(style=estilo, children=dcc.Loading(
        type="circle", color="#1F7A80",
        children=dcc.Graph(id=f"{prefijo}-grafica", config=GRAFICA_CONFIG,
                           style={"height": f"{altura}px"}, figure=_vacia(altura)),
    )))


def _vacia(altura: int) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(xaxis_visible=False, yaxis_visible=False, plot_bgcolor="#FFFFFF",
                      paper_bgcolor="#FFFFFF", height=altura, margin=dict(l=0, r=0, t=0, b=0))
    return fig


def ventana(prefijo: str, titulo: str, contenido) -> html.Div:
    """Ventana emergente con barra de título, como en los bocetos."""
    return html.Div(id=f"{prefijo}-ventana", className="e6-ventana", children=[
        html.Div(className="e6-velo", id=f"{prefijo}-velo", n_clicks=0),
        html.Div(className="e6-dialogo", role="dialog", **{"aria-modal": "true", "aria-label": titulo}, children=[
            html.Div(className="e6-barra", children=[
                html.Span(titulo, className="e6-barra-titulo"),
                html.Button("×", id=f"{prefijo}-cerrar", className="e6-cerrar", n_clicks=0,
                            title="Cerrar", **{"aria-label": "Cerrar"}),
            ]),
            html.Div(className="e6-dialogo-cuerpo", children=contenido),
        ]),
    ])


def navegacion(subtema: str) -> html.Nav:
    i = [s for s, _, _ in ESCENAS].index(subtema)
    enlaces = []
    if i > 0:
        enlaces.append(dcc.Link(f"← {ESCENAS[i - 1][2]}", href=ESCENAS[i - 1][1], className="e6-nav-enlace"))
    else:
        enlaces.append(html.Span())
    if i < len(ESCENAS) - 1:
        enlaces.append(dcc.Link(f"{ESCENAS[i + 1][2]} →", href=ESCENAS[i + 1][1], className="e6-nav-enlace"))
    return html.Nav(enlaces, className="e6-nav")


def pagina(*hijos) -> html.Div:
    return html.Div(className="e6", children=html.Div(className="e6-pagina", children=list(hijos)))
