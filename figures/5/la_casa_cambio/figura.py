"""La casa cambió
viz_id: 5.la_casa_cambio

Barras espalda con espalda, rural a la izquierda y urbano a la derecha
(boceto del equipo): 2010 en blanco y 2020 rayado.

Tabla de oro (`datos`), formato largo, Yucatán, ITER 2010 y 2020:
    indicador   "Agua entubada", "Energía eléctrica", "Piso firme",
                "Acceso a Internet", "Bienes (celular/PC)"
    anio        2010 o 2020
    ambito      "Rural" o "Urbano"
    porcentaje  % de viviendas particulares habitadas

La plantilla muestra fuentes, fecha y responsable; no van dentro de la figura.
"""
import pandas as pd
import plotly.graph_objects as go

TITULO = "La casa cambió"
CALIZA, TEXTO, TEXTO_2 = "#f7f4ec", "#1d2a22", "#4f5b52"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"
REJILLA = "#e3dfd2"
INDICADORES = ["Agua entubada", "Energía eléctrica", "Piso firme",
               "Acceso a Internet", "Bienes (celular/PC)"]
ESTILO = {
    2010: dict(color="white", line=dict(color=TEXTO, width=1.5)),
    2020: dict(color="white", line=dict(color=TEXTO, width=1.5),
               pattern=dict(shape="/", fgcolor=TEXTO, bgcolor="white", size=7)),
}


def _base() -> dict:
    return dict(
        title=dict(text=TITULO, x=0, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=22, color=TEXTO), pad=dict(l=10)),
        width=1100, height=720, paper_bgcolor=CALIZA, plot_bgcolor=CALIZA,
        font=dict(family=LETRA, size=14, color=TEXTO),
        margin=dict(l=170, r=60, t=110, b=130),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13)),
    )


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(**_base())
    if datos is None or len(datos) == 0:
        return fig
    d = datos.copy()
    d["anio"] = pd.to_numeric(d["anio"], errors="coerce")
    d["porcentaje"] = pd.to_numeric(d["porcentaje"], errors="coerce")
    d = d.dropna(subset=["anio", "porcentaje"])
    if d.empty:
        return fig
    orden = [i for i in INDICADORES if i in set(d["indicador"])]
    if not orden:
        orden = list(dict.fromkeys(d["indicador"]))
    for ambito, signo in [("Rural", -1), ("Urbano", 1)]:
        for anio in (2010, 2020):
            s = d[(d["ambito"] == ambito) & (d["anio"] == anio)]
            s = s.drop_duplicates("indicador").set_index("indicador").reindex(orden)
            vals = list(s["porcentaje"])
            fig.add_trace(go.Bar(
                y=orden, x=[signo * v for v in vals], orientation="h",
                name=str(anio), legendgroup=str(anio), showlegend=(ambito == "Rural"),
                offsetgroup=str(anio), marker=ESTILO[anio],
                text=["" if v != v else f"{v:.0f}%" for v in vals],
                textposition="outside", customdata=vals,
                hovertemplate="%{y} · " + ambito + " " + str(anio)
                              + ": %{customdata:.1f}%<extra></extra>",
            ))
    for texto, x in [("<b>Hogar rural</b>", -55), ("<b>Hogar urbano</b>", 55)]:
        fig.add_annotation(xref="x", yref="paper", x=x, y=1.07, text=texto,
                           showarrow=False, font=dict(size=17, color=TEXTO))
    r20 = d[(d["ambito"] == "Rural") & (d["anio"] == 2020)]
    if not r20.empty:
        m = r20.loc[r20["porcentaje"].idxmin()]
        fig.add_annotation(
            xref="paper", yref="paper", x=0.5, y=-0.2, showarrow=False,
            text=f"El mayor rezago rural en 2020 está en {m['indicador'].lower()} "
                 f"(solo {m['porcentaje']:.0f}%)",
            font=dict(size=14, color=TEXTO_2))
    fig.update_layout(
        barmode="group", bargap=0.35,
        legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"),
    )
    fig.update_xaxes(range=[-125, 125], tickvals=[-100, -50, 0, 50, 100],
                     ticktext=["100", "50", "0", "50", "100"],
                     title="Viviendas con el servicio (%)", gridcolor=REJILLA, zeroline=True,
                     zerolinecolor=TEXTO, zerolinewidth=1.5)
    fig.update_yaxes(autorange="reversed", title=None)
    return fig
