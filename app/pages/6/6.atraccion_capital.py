"""Página de 6.atraccion_capital: Fábrica de IED.

Escena: fábrica industrial con chimeneas, bandas y engranajes en movimiento.
Al hacer clic se abre una ventana con la figura de
figures/6/atraccion_capital/figura.py (la misma del PDF).
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
SUBTEMA = "atraccion_capital"
VIZ_ID = "6.atraccion_capital"
P = "e6-ied"

dash.register_page(
    __name__,
    path="/6/atraccion_capital",
    name="Atracción de capital y empleo",
    title="Atracción de capital, empleo y evolución de unidades económicas · Equipo 6",
    viz_id=VIZ_ID,
    order=603,
)


def _lectura() -> str:
    return ("La inversión extranjera directa en la península muestra brechas entre entidades y picos puntuales, "
            "mientras que en Yucatán el número de unidades económicas y el personal ocupado estimado del DENUE "
            "mantienen una trayectoria de expansión sostenida entre 2018 y 2026.")


def layout(**_):
    titulo = e6.catalogo(SUBTEMA).get("subtema", "Atracción de capital, empleo y evolución de las unidades económicas")
    return e6.pagina(
        e6.encabezado(SUBTEMA, "Fábrica de IED"),
        html.Div(className="e6-escenario", children=[
            html.Div(className="e6-escena", children=[
                html.Button(
                    id=f"{P}-abrir", n_clicks=0, className="e6-objeto",
                    title="Activar producción y abrir los datos de IED, empleo y DENUE",
                    **{"aria-label": "Activar producción y abrir los datos de IED, empleo y DENUE"},
                    children=html.Img(src=dash.get_asset_url("6/escenas/fabrica.svg"),
                                      alt="Fábrica de IED y crecimiento con engranajes y bandas transportadoras"),
                ),
                html.Span(className="e6-pulso", style={"left": "26.7%", "top": "73%"}),
                html.P("Haz clic en la fábrica para activar la producción y revelar la IED, el empleo y el ritmo del DENUE.",
                       className="e6-pista", style={"right": "3%", "bottom": "4%"}),
            ]),
        ]),
        e6.ventana(P, titulo, e6.grafica(P, altura=920, ancho_minimo=1040)),
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