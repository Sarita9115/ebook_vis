"""Página del capítulo 4. Si las figuras no pueden cargarse, igual deja el vínculo."""

import importlib.util
from pathlib import Path

import dash
from dash import html

dash.register_page(
    __name__,
    path="/4",
    name="El capital que llega de fuera",
    title="El dinero que llega de fuera",
    order=40,
)

_historia = None
try:
    ruta = Path(__file__).resolve().parents[2] / "historias" / "equipo4.py"
    spec = importlib.util.spec_from_file_location("historia_equipo4", ruta)
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
        html.P("4 · El capital que llega de fuera", className="kicker"),
        html.H1("El dinero que llega de fuera"),
        html.P("La historia de este capítulo todavía no puede mostrarse en esta página."),
    ])
