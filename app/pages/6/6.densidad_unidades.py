"""Página de 6.densidad_unidades: Puerta DENUE / SAIC.

Escena: fachada comercial con puertas dobles DENUE / SAIC. Al abrir las puertas
(animación CSS) se despliega la figura de figures/6/densidad_unidades/figura.py.
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
SUBTEMA = "densidad_unidades"
VIZ_ID = "6.densidad_unidades"
P = "e6-denue"

# Acceso de la fachada dentro de denue.svg (1200 x 750): x 660-840, y 435-660.
PORTAL = {"left": "55%", "top": "58%", "width": "15%", "height": "30%"}

dash.register_page(
    __name__,
    path="/6/densidad_unidades",
    name="Densidad de unidades económicas",
    title="Distribución y densidad nacional de unidades económicas · Equipo 6",
    viz_id=VIZ_ID,
    order=601,
)


def _lectura() -> str:
    return ("La actividad económica de la península se concentra en las capitales y corredores turísticos. "
            "El mapa muestra la densidad de unidades económicas del DENUE por celda de 2 km y su proporción "
            "por cada 1 000 habitantes en Yucatán, Campeche y Quintana Roo.")


def layout(**_):
    titulo = e6.catalogo(SUBTEMA).get("subtema", "Distribución y densidad nacional de unidades económicas")
    asset = dash.get_asset_url
    return e6.pagina(
        e6.encabezado(SUBTEMA, "Puerta DENUE / SAIC"),
        html.Div(id=f"{P}-escenario", className="e6-escenario e6-puertas", children=[
            html.Div(className="e6-escena", children=[
                html.Img(src=asset("6/escenas/denue.svg"), className="e6-fondo",
                         alt="Fachada comercial con acceso DENUE y SAIC"),
                html.Div(className="e6-portal", style=PORTAL, children=[
                    html.Div(className="e6-luz"),
                    html.Div(className="e6-hoja e6-hoja--izq",
                             children=html.Img(src=asset("6/escenas/denue_puerta_izq.svg"), alt="")),
                    html.Div(className="e6-hoja e6-hoja--der",
                             children=html.Img(src=asset("6/escenas/denue_puerta_der.svg"), alt="")),
                ]),
                html.Button("Abrir puerta DENUE / SAIC", id=f"{P}-abrir", n_clicks=0, className="e6-cartel",
                            style={"left": "4%", "bottom": "6%"}, **{"aria-controls": f"{P}-revelado"}),
            ]),
            html.Div(id=f"{P}-revelado", className="e6-revelado", children=html.Div(
                className="e6-revelado-interior", children=html.Div(className="e6-tarjeta", children=[
                    html.Div(className="e6-tarjeta-barra", children=[
                        html.Span(titulo, className="e6-barra-titulo"),
                        html.Button("×", id=f"{P}-cerrar", n_clicks=0, className="e6-cerrar",
                                    title="Cerrar la puerta", **{"aria-label": "Cerrar"}),
                    ]),
                    e6.grafica(P, altura=840, ancho_minimo=980),
                ]),
            )),
        ]),
        dcc.Store(id=f"{P}-cargada", data=False),
        e6.ficha(SUBTEMA, _lectura()),
        e6.navegacion(SUBTEMA),
    )


clientside_callback(
    ClientsideFunction(namespace="e6", function_name="puertas"),
    Output(f"{P}-escenario", "className"),
    Input(f"{P}-abrir", "n_clicks"),
    Input(f"{P}-cerrar", "n_clicks"),
    State(f"{P}-escenario", "className"),
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