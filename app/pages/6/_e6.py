"""Piezas compartidas por las páginas del Equipo 6 (Dinámica empresarial).

Dash no registra este archivo como página porque empieza con "_".

Qué hace:

- Lee la tabla de oro de cada visualización solo del esquema `oro` de
  PostgreSQL/PostGIS (secciones 4.3 y 7 de la arquitectura): oro."<viz_id>",
  por ejemplo oro."6.gasto_publico". No hay copia local de respaldo: si la base
  no contesta o la tabla no existe, la página lo dice de forma explícita.
- Lee el título y la cifra de la lectura de oro.catalogo (sección 9), fila
  primaria del viz_id.
- Importa `figura(datos)` desde `figures/6/<subtema>/figura.py`, sin
  redibujarla, y guarda la figura en caché mientras la tabla no cambie.
- Arma las piezas de la plantilla: encabezado, ventana con la figura y la
  ficha con fuentes, fecha y responsable (de oro) y la lectura.

Conexión: la misma que los pipelines (pipelines/6/_almacen.py): ORO_DB_URL,
o DATABASE_URL, o POSTGRES_HOST (postgres), POSTGRES_PORT (5432),
POSTGRES_USER, POSTGRES_PASSWORD y POSTGRES_DB.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
import time
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html

RAIZ = Path(__file__).resolve().parents[3]
ALMACEN = RAIZ / "pipelines" / "6" / "_almacen.py"
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
# Datos (solo PostgreSQL, esquema oro)
# ---------------------------------------------------------------------------

class ErrorOro(RuntimeError):
    """La página no pudo leer el esquema `oro` de PostgreSQL."""


def _almacen():
    """El conector de los pipelines del equipo, cargado por ruta."""
    if "e6_almacen" not in sys.modules:
        spec = importlib.util.spec_from_file_location("e6_almacen", ALMACEN)
        modulo = importlib.util.module_from_spec(spec)
        sys.modules["e6_almacen"] = modulo
        spec.loader.exec_module(modulo)
    return sys.modules["e6_almacen"]


def _sello() -> int:
    """Cambia cada REFRESCO_BD_S segundos; invalida la caché de tablas y figuras."""
    return int(time.time() // REFRESCO_BD_S)


def _consultar(descripcion: str, funcion):
    """Ejecuta una lectura de PostgreSQL y convierte cualquier falla en ErrorOro."""
    alm = _almacen()
    try:
        alm.url_bd()
    except RuntimeError as error:
        raise ErrorOro(f"No hay conexión configurada a PostgreSQL: {error}") from error
    try:
        return funcion(alm)
    except ErrorOro:
        raise
    except Exception as error:
        raise ErrorOro(f"PostgreSQL no contestó al leer {descripcion} ({type(error).__name__}: {error})") from error


@lru_cache(maxsize=16)
def _oro(subtema: str, sello: int):
    viz_id = f"{EQUIPO}.{subtema}"

    def leer(alm):
        if not alm.existe(viz_id, "oro"):
            raise ErrorOro(f'No existe la tabla oro."{viz_id}" en PostgreSQL. Corre el DAG equipo_6.')
        datos = alm.leer(viz_id, "oro")
        if datos.empty:
            raise ErrorOro(f'La tabla oro."{viz_id}" está vacía.')
        return datos

    return _consultar(f'oro."{viz_id}"', leer)


def oro(subtema: str):
    """Tabla de oro del subtema. Lanza ErrorOro si la base no contesta o la tabla no existe."""
    return _oro(subtema, _sello())


@lru_cache(maxsize=8)
def _modulo_figura(subtema: str):
    ruta = RAIZ / "figures" / EQUIPO / subtema / "figura.py"
    spec = importlib.util.spec_from_file_location(f"figura_{EQUIPO}_{subtema}", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@lru_cache(maxsize=16)
def _figura(subtema: str, sello: int) -> go.Figure:
    return _modulo_figura(subtema).figura(_oro(subtema, sello))


def figura(subtema: str) -> go.Figure:
    """La misma figura del PDF. Si oro no se puede leer, muestra el error tal cual."""
    try:
        return _figura(subtema, _sello())
    except Exception as error:
        log.exception("Falló la figura %s.%s", EQUIPO, subtema)
        aviso = go.Figure()
        aviso.add_annotation(text=f"No se pudo mostrar la figura: {error}", showarrow=False,
                             x=0.5, y=0.5, xref="paper", yref="paper", font=dict(size=14, color="#9B2C2C"))
        aviso.update_layout(xaxis_visible=False, yaxis_visible=False, plot_bgcolor="#FFFFFF",
                            paper_bgcolor="#FFFFFF", height=320)
        return aviso


@lru_cache(maxsize=4)
def _catalogo(sello: int) -> dict:
    """viz_id -> fila primaria del equipo en oro.catalogo."""
    def leer(alm):
        if not alm.existe("catalogo", "oro"):
            raise ErrorOro("No existe la tabla oro.catalogo en PostgreSQL. Corre el DAG equipo_6.")
        from sqlalchemy import text
        with alm.motor().connect() as con:
            tabla = pd.read_sql(text("SELECT * FROM oro.catalogo WHERE equipo = :e"), con, params={"e": EQUIPO})
        filas = {}
        for fila in tabla.to_dict("records"):
            actual = filas.get(fila["viz_id"])
            if actual is None or (fila.get("papel") == "primaria" and actual.get("papel") != "primaria"):
                filas[fila["viz_id"]] = fila
        return filas

    return _consultar("oro.catalogo", leer)


def estado_bd() -> str | None:
    """None si oro.catalogo se puede leer; si no, el mensaje de error para mostrarlo."""
    try:
        _catalogo(_sello())
        return None
    except ErrorOro as error:
        return str(error)


def catalogo(subtema: str) -> dict:
    """Fila primaria del subtema en oro.catalogo; {} si no se pudo leer (la página muestra el error)."""
    try:
        return _catalogo(_sello()).get(f"{EQUIPO}.{subtema}", {})
    except ErrorOro as error:
        log.error("%s", error)
        return {}


def valor_catalogo(subtema: str) -> float | None:
    try:
        valor = float(catalogo(subtema).get("valor_referencia") or "nan")
    except (TypeError, ValueError):
        return None
    return None if pd.isna(valor) else valor


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
    """Ventana emergente con barra de título."""
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
    """Contenedor de la escena. Si oro no se puede leer, lo avisa arriba de la página."""
    error = estado_bd()
    alerta = [html.Div(f"No se pudo leer el esquema oro de PostgreSQL: {error}",
                       className="e6-alerta", role="alert",
                       style={"background": "#FDECEC", "color": "#9B2C2C", "padding": "12px 16px",
                              "border": "1px solid #9B2C2C", "borderRadius": "6px", "margin": "12px 0"})] if error else []
    return html.Div(className="e6", children=html.Div(className="e6-pagina", children=alerta + list(hijos)))
