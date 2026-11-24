"""Ficha de un subtema. El vínculo del menú llega aquí cuando todavía no hay página propia."""

import dash
from dash import html

try:
    from app.recorrido import ficha
except ImportError:
    from recorrido import ficha

dash.register_page(
    __name__,
    path_template="/v/<equipo>/<slug>",
    name="Subtema",
    title="Subtema · Los aluxes del Mayab",
    order=100,
)


def layout(equipo=None, slug=None, **_):
    capitulo, numero, titulo = ficha(equipo, slug)
    if capitulo is None:
        return html.Div(className="indice", children=[
            html.A("Volver al recorrido", href="/"),
            html.H1("Este subtema no está en la historia"),
        ])
    return html.Div(className="indice", children=[
        html.A("Volver al recorrido", href="/"),
        html.P(f"{capitulo['orden']} · {capitulo['titulo']}", className="kicker"),
        html.H1(f"{numero}. {titulo}"),
        html.P("La figura de este subtema todavía no está montada en su página."),
    ])
