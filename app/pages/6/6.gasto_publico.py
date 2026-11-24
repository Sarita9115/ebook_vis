"""Página de 6.gasto_publico: Palacio de Presupuesto.

Escena: el palacio de la Secretaría de Fomento. Al hacer clic se abre una
ventana con la figura de figures/6/gasto_publico/figura.py (la misma del PDF).
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
SUBTEMA = "gasto_publico"
VIZ_ID = "6.gasto_publico"
P = "e6-gasto"

dash.register_page(
    __name__,
    path="/6/gasto_publico",
    name="Gasto público y fomento económico",
    title="Gasto público estatal y fomento económico · Equipo 6",
    viz_id=VIZ_ID,
    order=605,
)


def _lectura() -> str:
    v = e6.valor_catalogo(SUBTEMA)
    if v is None:
        return "A qué se destina el gasto que sostiene la obra pública del estado."
    return (f"De cada 100 pesos que ejerció el gobierno de Yucatán en 2025, {v:.1f} se destinaron "
            "a desarrollo económico. El resto se fue a desarrollo social, gobierno, municipios y deuda.")


def layout(**_):
    titulo = e6.catalogo(SUBTEMA).get("subtema", "Gasto público")
    return e6.pagina(
        e6.encabezado(SUBTEMA, "Palacio de Presupuesto"),
        html.Div(className="e6-escenario", children=[
            html.Div(className="e6-escena", children=[
                html.Button(
                    id=f"{P}-abrir", n_clicks=0, className="e6-objeto",
                    title="Abrir el flujo del gasto y el fomento económico",
                    **{"aria-label": "Abrir el flujo del gasto y el fomento económico"},
                    children=html.Img(src=dash.get_asset_url("6/escenas/palacio.svg"),
                                      alt="Palacio de Presupuesto, sede de la Secretaría de Fomento"),
                ),
                html.Span(className="e6-pulso", style={"left": "50%", "top": "62%"}),
                html.P("Haz clic en el palacio para revelar el flujo del gasto y el fomento económico.",
                       className="e6-pista", style={"left": "3%", "bottom": "4%"}),
            ]),
        ]),
        e6.ventana(P, titulo, e6.grafica(P, altura=860, ancho_minimo=980)),
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
