"""Página de 6.relieve_5m: Monumento a la Patria.

Escena: el Monumento a la Patria con su reja. "Ver relieves de la ciudad"
abre la reja (animación CSS) y revela la superficie 3D de
figures/6/relieve_5m/figura.py. El navegador solo recibe la malla de 200 m.
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
SUBTEMA = "relieve_5m"
VIZ_ID = "6.relieve_5m"
P = "e6-relieve"

# Arco de la entrada dentro de patria.svg (1200 x 750): x 520-680, y 400-620.
PORTAL = {"left": "43.3333%", "top": "53.3333%", "width": "13.3333%", "height": "29.3333%"}

dash.register_page(
    __name__,
    path="/6/relieve_5m",
    name="Relieve y altura edificada",
    title="Relieve y altura edificada de Mérida · Equipo 6",
    viz_id=VIZ_ID,
    order=608,
)


def _lectura() -> str:
    v = e6.valor_catalogo(SUBTEMA)
    cifra = f"{v:.0f}% de sus edificios mide" if v is not None else "la mayoría de sus edificios mide"
    return (f"Mérida es una ciudad baja: {cifra} menos de 5 m. En la superficie, la altura es la de los "
            "edificios y el color, el número de negocios en cada celda de 200 m.")


def layout(**_):
    titulo = e6.catalogo(SUBTEMA).get("subtema", "Relieve y altura edificada")
    asset = dash.get_asset_url
    return e6.pagina(
        e6.encabezado(SUBTEMA, "Monumento a la Patria"),
        html.Div(id=f"{P}-escenario", className="e6-escenario e6-puertas", children=[
            html.Div(className="e6-escena", children=[
                html.Img(src=asset("6/escenas/patria.svg"), className="e6-fondo",
                         alt="Monumento a la Patria, con su reja cerrada"),
                html.Div(className="e6-portal", style=PORTAL, children=[
                    html.Div(className="e6-luz"),
                    html.Div(className="e6-hoja e6-hoja--izq",
                             children=html.Img(src=asset("6/escenas/patria_reja_izq.svg"), alt="")),
                    html.Div(className="e6-hoja e6-hoja--der",
                             children=html.Img(src=asset("6/escenas/patria_reja_der.svg"), alt="")),
                ]),
                html.Button("Ver relieves de la ciudad", id=f"{P}-abrir", n_clicks=0, className="e6-cartel",
                            style={"right": "4%", "bottom": "6%"}, **{"aria-controls": f"{P}-revelado"}),
            ]),
            html.Div(id=f"{P}-revelado", className="e6-revelado", children=html.Div(
                className="e6-revelado-interior", children=html.Div(className="e6-tarjeta", children=[
                    html.Div(className="e6-tarjeta-barra", children=[
                        html.Span(titulo, className="e6-barra-titulo"),
                        html.Button("×", id=f"{P}-cerrar", n_clicks=0, className="e6-cerrar",
                                    title="Cerrar la reja", **{"aria-label": "Cerrar"}),
                    ]),
                    e6.grafica(P, altura=800),
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
