"""Página de 6.corredor_industrial: Corredor Industrial.

Escena: las naves del corredor Mérida, Umán y Hunucmá. Al hacer clic se abre
una ventana con la figura de figures/6/corredor_industrial/figura.py.
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
SUBTEMA = "corredor_industrial"
VIZ_ID = "6.corredor_industrial"
P = "e6-corredor"

dash.register_page(
    __name__,
    path="/6/corredor_industrial",
    name="Corredor industrial",
    title="Concentración industrial en el corredor Mérida, Umán y Hunucmá · Equipo 6",
    viz_id=VIZ_ID,
    order=607,
)


def _lectura() -> str:
    v = e6.valor_catalogo(SUBTEMA)
    if v is None:
        return "Dónde se instala la industria, vista con los establecimientos industriales del DENUE."
    return (f"Mérida, Umán y Hunucmá reúnen {v:.0f}% del personal ocupado aproximado en manufactura, "
            "transporte y almacenamiento de Yucatán, en establecimientos con 11 o más personas (DENUE, mayo de 2026).")


def layout(**_):
    titulo = e6.catalogo(SUBTEMA).get("subtema", "Corredor industrial")
    return e6.pagina(
        e6.encabezado(SUBTEMA, "Corredor Industrial"),
        html.Div(className="e6-escenario", children=[
            html.Div(className="e6-escena e6-escena--700", children=[
                html.Button(
                    id=f"{P}-abrir", n_clicks=0, className="e6-objeto",
                    title="Abrir el mapa y la concentración del corredor",
                    **{"aria-label": "Abrir el mapa y la concentración del corredor industrial"},
                    children=html.Img(src=dash.get_asset_url("6/escenas/naves.svg"),
                                      alt="Naves industriales del corredor Mérida, Umán y Hunucmá"),
                ),
                html.Span(className="e6-pulso", style={"left": "46%", "top": "66%"}),
                html.P("Haz clic en las naves industriales para abrir el mapa del corredor y su concentración.",
                       className="e6-pista", style={"right": "3%", "top": "6%"}),
            ]),
        ]),
        e6.ventana(P, titulo, e6.grafica(P, altura=760, ancho_minimo=980)),
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
    return e6.figura(SUBTEMA), True
