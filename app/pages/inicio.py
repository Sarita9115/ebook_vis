"""Portada: los seis capítulos y sus subtemas, en el orden del storytelling."""

import dash
from dash import html

try:
    from app.recorrido import CAPITULOS, enlace
except ImportError:
    from recorrido import CAPITULOS, enlace

dash.register_page(__name__, path="/", name="Los aluxes del Mayab", title="Los aluxes del Mayab", order=0)

ALT = {
    "1": "Flamencos en la ría de Celestún y un jaguar entre los manglares.",
    "2": "Calle de fachadas amarillas, rosas y azules con familias caminando.",
    "3": "Casa maya de palma con hamaca y dos niños con mochila rumbo a la escuela.",
    "4": "Muelle de Progreso con barcos de carga y grúas sobre el mar turquesa.",
    "5": "Vista aérea de la cuadrícula de Mérida y naves industriales junto a la selva.",
    "6": "Estudiantes en un campus universitario probando un brazo robótico.",
}


def _tarjeta(c):
    return html.Article(
        className="tarjeta",
        **{"data-tema": c["orden"]},
        children=[
            html.Div(className="tarjeta-imagen", children=[
                html.Img(src=c["imagen"], alt=ALT[c["orden"]]),
            ]),
            html.Span(c["orden"], className="numeral", **{"aria-hidden": "true"}),
            html.Div(className="tarjeta-texto", children=[
                html.P(f"{c['apertura']} · Equipo {c['equipo']}", className="kicker"),
                html.H2(c["titulo"]),
                html.P(c["pregunta"], className="pregunta"),
                html.A(c["capitulo"][1], href=c["capitulo"][0], className="historia") if c.get("capitulo") else None,
                html.Ol(children=[
                    html.Li(html.A(titulo, href=enlace(c["equipo"], slug)))
                    for slug, titulo in c["subtemas"]
                ]),
            ]),
        ],
    )


def layout():
    return html.Div(className="indice", children=[
        html.Header(className="portada-mayab", children=[
            html.Div(className="portada-texto", children=[
                html.P("Un recorrido por la península", className="kicker"),
                html.H1("Los aluxes del Mayab"),
                html.P("El Mayab es esta tierra. El relato mira qué se cuida y qué cambia.", className="bajada"),
                html.A("Empezar el recorrido", href="#recorrido", className="boton"),
            ]),
        ]),
        html.Div(className="greca", **{"aria-hidden": "true"}),
        html.Div(id="recorrido", className="rejilla", children=[_tarjeta(c) for c in CAPITULOS]),
        html.P("La UPY mira el mismo Mayab que acaban de recorrer los mapas.", className="cierre"),
    ])
