"""Página de 6.obra_publica: Obras y Municipios.

Escena: obra vial y construcción urbana con maquinaria y equipo de topografía.
Al hacer clic se abre una ventana con la figura de
figures/6/obra_publica/figura.py (la misma del PDF).
"""

import importlib.util
import sys
from pathlib import Path

import dash
from dash import ClientsideFunction, Input, Output, State, callback, clientside_callback, dcc, html, no_update


def _e6():
    if "e6_comun" not in sys.modules:
        spec = importlib.util.spec_from_file_location("e6_comun", Path(__file__).with_name("_e6.py"))
        modulo = importlib.util.module_from_spec(spec)
        sys.modules["e6_comun"] = modulo
        spec.loader.exec_module(modulo)
    return sys.modules["e6_comun"]


e6 = _e6()
SUBTEMA = "obra_publica"
VIZ_ID = "6.obra_publica"
P = "e6-obras"

dash.register_page(
    __name__,
    path="/6/obra_publica",
    name="Obra pública e infraestructura",
    title="Obra pública e infraestructura por municipio · Equipo 6",
    viz_id=VIZ_ID,
    order=604,
)


def _lectura() -> str:
    return ("La inversión estatal en obra pública se reparte de forma desigual entre los 106 municipios de Yucatán. "
            "El mapa y la gráfica de dispersión contrastan el gasto por habitante en pesos constantes de 2025 "
            "frente al tamaño poblacional de cada municipio.")


def layout(**_):
    titulo = e6.catalogo(SUBTEMA).get("subtema", "Obra pública e infraestructura para el desarrollo económico por municipio")
    return e6.pagina(
        e6.encabezado(SUBTEMA, "Obras y Municipios"),
        html.Div(className="e6-escenario", children=[
            html.Div(className="e6-escena", children=[
                html.Button(
                    id=f"{P}-abrir", n_clicks=0, className="e6-objeto",
                    title="Abrir el gasto en obra pública por habitante y su distribución municipal",
                    **{"aria-label": "Abrir el gasto en obra pública por habitante y su distribución municipal"},
                    children=html.Img(src=dash.get_asset_url("6/escenas/obras.svg"),
                                      alt="Obras y Municipios: avenida en construcción con maquinaria, grúa y topógrafos"),
                ),
                html.Span(className="e6-pulso", style={"left": "59%", "top": "82%"}),
                html.P("Haz clic en la obra para ver el gasto por habitante y su distribución en los municipios.",
                       className="e6-pista", style={"right": "3%", "bottom": "4%"}),
            ]),
        ]),
        e6.ventana(P, titulo, e6.grafica(P, altura=780, ancho_minimo=1100)),
        dcc.Store(id=f"{P}-cargada", data=False),
        e6.ficha(SUBTEMA, _lectura()),
        e6.navegacion(SUBTEMA),
    )


clientside_callback(
    ClientsideFunction(namespace="e6", function_name="ventana"),
    Output(f"{P}-ventana", "className"),
    Input(f"{P}-abrir", "n_clicks"),
    Input(f"{P}-cerrar", "n_clicks"),
    Input(f"{P}-velo", "n_clicks"),
    prevent_initial_call=True,
)


@callback(
    Output(f"{P}-grafica", "figure"),
    Output(f"{P}-cargada", "data"),
    Input(f"{P}-abrir", "n_clicks"),
    State(f"{P}-cargada", "data"),
    prevent_initial_call=True,
)
def cargar(_, cargada):
    if cargada:
        return no_update, no_update
    fig = e6.figura(SUBTEMA)
    fig.update_layout(width=None, autosize=True)  # ocupa el ancho de la ventana (el PDF conserva el ancho fijo)
    return fig, True