"""Participación estudiantil y comunidad

viz_id: 1.participacion_estudiantil

Línea de tiempo de lo que hicieron los estudiantes de la UPY dentro y fuera del
campus. Cada fila es un tipo de actividad (competencia, divulgación en la
comunidad); cada punto, un evento. El área del círculo es el número de
estudiantes que reporta la fuente; el rombo sin relleno marca un evento sin
cifra publicada. No se muestran nombres de personas.

`datos` es la tabla de oro (pipelines/1/participacion_estudiantil.py).
"""

import pandas as pd
import plotly.graph_objects as go

TITULO = "Participación estudiantil y comunidad"
COLORES = {"Competencia": "#3a6ea5", "Divulgación en la comunidad": "#e9a23b"}
COLOR_OTROS = "#7a7a7a"
PX_MAX = 46


def _vacia(mensaje: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=TITULO,
        annotations=[dict(text=mensaje, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)],
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    if datos is None or len(datos) == 0:
        return _vacia("Sin datos para mostrar")

    d = datos.copy()
    d["fecha"] = pd.to_datetime(d["fecha"])
    maximo = float(d["estudiantes"].max()) if d["estudiantes"].notna().any() else 1.0
    sizeref = 2.0 * maximo / (PX_MAX ** 2)
    hover = ("<b>%{customdata[0]}</b><br>%{x|%d %b %Y} · %{customdata[3]}<br>Estudiantes: %{customdata[1]}"
             "<br>%{customdata[2]}<extra></extra>")

    fig = go.Figure()
    for tipo in list(d["tipo"].drop_duplicates()):
        color = COLORES.get(tipo, COLOR_OTROS)
        sub = d[d["tipo"] == tipo]
        con = sub[sub["estudiantes"].notna()]
        sin = sub[sub["estudiantes"].isna()]
        if not con.empty:
            fig.add_trace(go.Scatter(
                x=con["fecha"], y=con["tipo"], mode="markers+text", name=tipo, legendgroup=tipo,
                marker=dict(size=con["estudiantes"], sizemode="area", sizeref=sizeref, sizemin=8,
                            color=color, opacity=0.8, line=dict(width=1, color="white")),
                text=[f"{int(v)}" for v in con["estudiantes"]], textposition="middle right",
                customdata=list(zip(con["titulo"], con["estudiantes"].astype(int), con["nota"], con["lugar"])),
                hovertemplate=hover,
            ))
        if not sin.empty:
            fig.add_trace(go.Scatter(
                x=sin["fecha"], y=sin["tipo"], mode="markers", name=tipo, legendgroup=tipo, showlegend=con.empty,
                marker=dict(size=14, symbol="diamond-open", color=color, line=dict(width=2, color=color)),
                customdata=list(zip(sin["titulo"], ["sin cifra publicada"] * len(sin), sin["nota"], sin["lugar"])),
                hovertemplate=hover,
            ))

    fig.update_layout(
        title=TITULO,
        xaxis=dict(title="Fecha", showgrid=True, gridcolor="#e6e6e6"),
        yaxis=dict(automargin=True, title=""),
        legend=dict(orientation="h", x=0, y=-0.2, title_text="", itemsizing="constant"),
        margin=dict(l=20, r=30, t=70, b=130), height=420, width=1000, plot_bgcolor="white",
        annotations=[dict(
            x=0, y=-0.44, xref="paper", yref="paper", xanchor="left", showarrow=False, align="left",
            text="El área del círculo es proporcional al número de estudiantes que reporta la fuente. El rombo marca un evento sin cifra publicada.",
            font=dict(size=11, color="#555"),
        )],
    )
    return fig
