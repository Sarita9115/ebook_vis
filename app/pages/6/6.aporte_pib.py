"""Página de 6.aporte_pib: Bóveda del PIB.

Escena: Edificio de la Dinámica Empresarial con la bóveda del PIB en arco.
Al hacer clic en "Abrir bóveda" las dos hojas se abren (animación CSS) y
despliegan la figura de figures/6/aporte_pib/figura.py.
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
SUBTEMA = "aporte_pib"
VIZ_ID = "6.aporte_pib"
P = "e6-pib"

# Arco de la bóveda dentro de boveda.svg (1200 x 750): x 570-750, y 270-480.
PORTAL = {"left": "47.5%", "top": "36%", "width": "15%", "height": "28%"}

dash.register_page(
    __name__,
    path="/6/aporte_pib",
    name="Aporte del sector empresarial al PIB",
    title="Aporte del sector empresarial al PIB estatal y regional · Equipo 6",
    viz_id=VIZ_ID,
    order=602,
)


def _lectura() -> str:
    return ("Entre 2003 y 2024, el sector 71 (servicios de esparcimiento culturales, deportivos y recreativos) "
            "muestra trayectorias distintas en la península. La comparación en precios constantes de 2018 "
            "contrasta su crecimiento acumulado y su peso dentro del valor agregado bruto estatal y nacional.")


def layout(**_):
    titulo = e6.catalogo(SUBTEMA).get("subtema", "Aporte del sector empresarial al PIB estatal y regional")
    asset = dash.get_asset_url
    return e6.pagina(
        e6.encabezado(SUBTEMA, "Bóveda del PIB"),
        html.Div(id=f"{P}-escenario", className="e6-escenario e6-puertas", children=[
            html.Div(className="e6-escena", children=[
                html.Img(src=asset("6/escenas/boveda.svg"), className="e6-fondo",
                         alt="Edificio de la Dinámica Empresarial con la bóveda del PIB cerrada"),
                html.Div(className="e6-portal", style=PORTAL, children=[
                    html.Div(className="e6-luz"),
                    html.Div(className="e6-hoja e6-hoja--izq",
                             children=html.Img(src=asset("6/escenas/boveda_puerta_izq.svg"), alt="")),
                    html.Div(className="e6-hoja e6-hoja--der",
                             children=html.Img(src=asset("6/escenas/boveda_puerta_der.svg"), alt="")),
                ]),
                html.Button("Abrir bóveda", id=f"{P}-abrir", n_clicks=0, className="e6-cartel",
                            style={"right": "4%", "bottom": "6%"}, **{"aria-controls": f"{P}-revelado"}),
            ]),
            html.Div(id=f"{P}-revelado", className="e6-revelado", children=html.Div(
                className="e6-revelado-interior", children=html.Div(className="e6-tarjeta", children=[
                    html.Div(className="e6-tarjeta-barra", children=[
                        html.Span(titulo, className="e6-barra-titulo"),
                        html.Button("×", id=f"{P}-cerrar", n_clicks=0, className="e6-cerrar",
                                    title="Cerrar la bóveda", **{"aria-label": "Cerrar"}),
                    ]),
                    e6.grafica(P, altura=720, ancho_minimo=1100),
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