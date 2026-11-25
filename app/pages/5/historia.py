"""Página del capítulo 5. Si la historia no puede cargarse, igual deja el vínculo."""

import importlib.util
from pathlib import Path

import dash
from dash import html

dash.register_page(
    __name__,
    path="/5",
    name="Más años en el aula, ¿mejor vida en casa?",
    title="Más años en el aula, ¿mejor vida en casa?",
    order=50,
)

_historia = None
try:
    ruta = Path(__file__).resolve().parents[2] / "historias" / "equipo5.py"
    spec = importlib.util.spec_from_file_location("historia_equipo5", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    _historia = modulo.layout
except Exception:
    _historia = None


def layout():
    if _historia is not None:
        return _historia()
    return html.Div(className="indice", children=[
        html.A("Volver al recorrido", href="/"),
        html.P("3 · La vida en casa", className="kicker"),
        html.H1("Más años en el aula, ¿mejor vida en casa?"),
        html.P("La historia de este capítulo todavía no puede mostrarse en esta página."),
    ])
