"""Página de 6.huella_construida: Fuente de la Ixtabay.

Escena: la fuente de la Ixtabay con una puerta en el basamento. "Abrir
historia de densidad" abre las puertas (animación CSS) y revela la curva de
concentración de figures/6/huella_construida/figura.py.
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
SUBTEMA = "huella_construida"
VIZ_ID = "6.huella_construida"
P = "e6-huella"

# Puerta del basamento dentro de ixtabay.svg (1200 x 750): x 545-655, y 562-692.
PORTAL = {"left": "45.4167%", "top": "74.9333%", "width": "9.1667%", "height": "17.3333%"}

dash.register_page(
    __name__,
    path="/6/huella_construida",
    name="Huella construida y densidad empresarial",
    title="Huella construida, altura y densidad empresarial de Mérida · Equipo 6",
    viz_id=VIZ_ID,
    order=609,
)


def _lectura() -> str:
    try:
        puntos = e6.oro(SUBTEMA)
        puntos = puntos[puntos["capa"] == "punto"].set_index("criterio")["pct_negocios"]
        return (f"¿Los negocios siguen a los edificios? El 10% de las celdas más construidas reúne "
                f"{puntos['Huella']:.0f}% de los negocios; el 10% con edificios más altos, {puntos['Altura']:.0f}%. "
                "Los negocios se reparten con la huella de la ciudad más que con su altura.")
    except Exception:
        return "¿Los negocios siguen a los edificios? Se reparten con la huella de la ciudad más que con su altura."


def layout(**_):
    titulo = e6.catalogo(SUBTEMA).get("subtema", "Huella construida")
    asset = dash.get_asset_url
    return e6.pagina(
        e6.encabezado(SUBTEMA, "Fuente de la Ixtabay"),
        html.Div(id=f"{P}-escenario", className="e6-escenario e6-puertas", children=[
            html.Div(className="e6-escena", children=[
                html.Img(src=asset("6/escenas/ixtabay.svg"), className="e6-fondo",
                         alt="Fuente de la Ixtabay, con una puerta cerrada en el basamento"),
                html.Div(className="e6-portal", style=PORTAL, children=[
                    html.Div(className="e6-luz"),
                    html.Div(className="e6-hoja e6-hoja--izq",
                             children=html.Img(src=asset("6/escenas/ixtabay_puerta_izq.svg"), alt="")),
                    html.Div(className="e6-hoja e6-hoja--der",
                             children=html.Img(src=asset("6/escenas/ixtabay_puerta_der.svg"), alt="")),
                ]),
                html.Button("Abrir historia de densidad", id=f"{P}-abrir", n_clicks=0, className="e6-cartel",
                            style={"right": "4%", "bottom": "6%"}, **{"aria-controls": f"{P}-revelado"}),
            ]),
            html.Div(id=f"{P}-revelado", className="e6-revelado", children=html.Div(
                className="e6-revelado-interior", children=html.Div(className="e6-tarjeta", children=[
                    html.Div(className="e6-tarjeta-barra", children=[
                        html.Span(titulo, className="e6-barra-titulo"),
                        html.Button("×", id=f"{P}-cerrar", n_clicks=0, className="e6-cerrar",
                                    title="Cerrar las puertas", **{"aria-label": "Cerrar"}),
                    ]),
                    e6.grafica(P, altura=640, ancho_minimo=640),
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
    return e6.figura(SUBTEMA), True
