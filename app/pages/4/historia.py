"""Páginas del capítulo 4: una por cada parte de la historia, en la ficha de su subtema (/v/4/<subtema>).
Si la historia no puede cargarse, la ficha genérica de subtema sigue respondiendo en esas rutas."""

import importlib.util
from pathlib import Path

import dash
from dash import html

_historia = None
try:
    ruta = Path(__file__).resolve().parents[2] / "historias" / "equipo4.py"
    spec = importlib.util.spec_from_file_location("historia_equipo4", ruta)
    _historia = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_historia)
except Exception:
    _historia = None


def _sin_historia():
    return html.Div(className="indice", children=[
        html.A("Volver al recorrido", href="/"),
        html.P("4 · El capital que llega de fuera", className="kicker"),
        html.H1("El dinero que llega de fuera"),
        html.P("Esta parte de la historia todavía no puede mostrarse en esta página."),
    ])


def _seguro(construir):
    """Si las tablas de oro no responden (por ejemplo, PostgreSQL apagado), muestra el aviso en vez de una página
    en blanco."""
    try:
        return construir()
    except Exception:
        return _sin_historia()


if _historia is not None:
    for _subtema, _num, _titulo in _historia.PARTES:
        dash.register_page(
            f"{__name__}.{_subtema}",
            path=_historia.ruta_parte(_subtema),
            name=_titulo,
            title=f"{_titulo} · El dinero que llega de fuera",
            order=40 + _num,
            layout=lambda _s=_subtema, **_: _seguro(lambda: _historia.layout_parte(_s)),
        )
