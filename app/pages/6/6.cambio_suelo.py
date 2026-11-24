"""Página de 6.cambio_suelo: Expansión Mérida–Progreso.

Escena: el monte visto desde arriba, con la costa de Progreso al norte. Un
deslizador convierte el monte en traza urbana (de Mérida hacia Progreso) y, al
llegar al final, despliega la figura de figures/6/cambio_suelo/figura.py.
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
SUBTEMA = "cambio_suelo"
VIZ_ID = "6.cambio_suelo"
P = "e6-suelo"

dash.register_page(
    __name__,
    path="/6/cambio_suelo",
    name="Cambio de uso del suelo",
    title="Cambio de uso del suelo y expansión urbana · Equipo 6",
    viz_id=VIZ_ID,
    order=606,
)


def _lectura() -> str:
    v = e6.valor_catalogo(SUBTEMA)
    if v is None:
        return "El crecimiento ya cambia el suelo."
    return (f"Entre la serie VI (2014) y la serie VII (2018) de uso del suelo, Yucatán sumó {v:.0f} km² "
            "netos de suelo urbano. La mayor parte salió de selva y de tierras agrícolas.")


def layout(**_):
    titulo = e6.catalogo(SUBTEMA).get("subtema", "Cambio de uso del suelo")
    asset = dash.get_asset_url
    return e6.pagina(
        e6.encabezado(SUBTEMA, "Expansión Mérida–Progreso"),
        html.Div(id=f"{P}-escenario", className="e6-escenario e6-transicion", style={"--avance": 0}, children=[
            html.Div(className="e6-escena e6-escena--600", children=[
                html.Img(src=asset("6/escenas/monte.svg"), className="e6-capa-monte",
                         alt="Monte de Yucatán visto desde arriba, con la costa al norte"),
                html.Img(src=asset("6/escenas/ciudad.svg"), className="e6-capa-ciudad",
                         alt="Traza urbana de Mérida extendida hacia Progreso"),
                html.Div(className="e6-frente"),
                html.P("Monte · 2014", className="e6-anio e6-anio--antes"),
                html.P("Ciudad · 2018", className="e6-anio e6-anio--despues"),
            ]),
            html.Div(className="e6-control", children=[
                html.P("Desliza para ver cómo el monte se convierte en ciudad, de Mérida hacia Progreso.",
                       className="e6-control-texto"),
                html.Div(className="e6-deslizador", children=dcc.Slider(
                    id=f"{P}-deslizador", min=0, max=100, step=1, value=0,
                    marks={0: "2014 · serie VI", 100: "2018 · serie VII"},
                    tooltip=None, updatemode="mouseup", allow_direct_input=False,
                )),
                html.Button("Ver la gráfica", id=f"{P}-ver", n_clicks=0, className="e6-boton"),
            ]),
            html.Div(id=f"{P}-revelado", className="e6-revelado", children=html.Div(
                className="e6-revelado-interior", children=html.Div(className="e6-tarjeta", children=[
                    html.Div(className="e6-tarjeta-barra", children=html.Span(titulo, className="e6-barra-titulo")),
                    e6.grafica(P, altura=760, ancho_minimo=980),
                ]),
            )),
        ]),
        dcc.Store(id=f"{P}-cargada", data=False),
        e6.ficha(SUBTEMA, _lectura()),
        e6.navegacion(SUBTEMA),
    )


# El avance visual corre en el navegador: mientras se arrastra (drag_value) y
# cuando el valor cambia sin arrastrar (botón "Ver la gráfica").
clientside_callback(
    ClientsideFunction(namespace="e6", function_name="avance"),
    Output(f"{P}-escenario", "style"),
    Output(f"{P}-escenario", "className"),
    Input(f"{P}-deslizador", "drag_value"),
    Input(f"{P}-deslizador", "value"),
    State(f"{P}-escenario", "className"),
    prevent_initial_call=True,
)

clientside_callback(
    ClientsideFunction(namespace="e6", function_name="completar"),
    Output(f"{P}-deslizador", "value"),
    Input(f"{P}-ver", "n_clicks"),
    prevent_initial_call=True,
)


@callback(
    Output(f"{P}-grafica", "figure"),
    Output(f"{P}-cargada", "data"),
    Input(f"{P}-deslizador", "value"),
    State(f"{P}-cargada", "data"),
    prevent_initial_call=True,
)
def cargar(valor, cargada):
    if cargada or (valor or 0) < 100:
        return no_update, no_update
    return e6.figura(SUBTEMA), True
