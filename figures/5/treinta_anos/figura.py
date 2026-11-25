"""Treinta años aprendiendo
viz_id: 5.treinta_anos

Línea de Yucatán, 1990-2025, con el valor y el nivel escolar de cada punto
(boceto del equipo).

Tabla de oro (`datos`), formato largo:
    anio            año (1990 viene del Censo 1990)
    entidad         "Yucatán" (si vienen otras, se ignoran)
    sexo            "Total" (si vienen otros, se ignoran)
    grado_promedio  años de escolaridad, población de 15 años y más

La plantilla muestra fuentes, fecha y responsable; no van dentro de la figura.
"""
import pandas as pd
import plotly.graph_objects as go

TITULO = "Treinta años aprendiendo"
CALIZA, TEXTO, TEXTO_2 = "#f7f4ec", "#1d2a22", "#4f5b52"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"
REJILLA = "#e3dfd2"


def _nivel(x) -> str:
    """Etiqueta del boceto según el grado promedio."""
    if x < 6:
        return "Primaria<br>incompleta"
    if x < 7:
        return "Primaria<br>completa"
    if x < 9:
        return "Secundaria<br>incompleta"
    if x < 9.5:
        return "Secundaria<br>completa"
    return "Prepa<br>trunca"


def _base() -> dict:
    return dict(
        title=dict(text=TITULO, x=0, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=22, color=TEXTO), pad=dict(l=10)),
        width=1100, height=720, paper_bgcolor=CALIZA, plot_bgcolor=CALIZA,
        font=dict(family=LETRA, size=14, color=TEXTO),
        margin=dict(l=80, r=60, t=80, b=70),
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
    d["grado_promedio"] = pd.to_numeric(d["grado_promedio"], errors="coerce")
    d = d[(d["entidad"] == "Yucatán") & (d["sexo"] == "Total")]
    d = d.dropna(subset=["anio", "grado_promedio"]).sort_values("anio")
    if d.empty:
        return fig
    fig.add_trace(go.Scatter(
        x=d["anio"], y=d["grado_promedio"], mode="lines+markers+text",
        line=dict(color=TEXTO, width=3), marker=dict(size=11, color=TEXTO),
        text=[f"<b>{v:.1f}</b><br>{_nivel(v)}" for v in d["grado_promedio"]],
        textposition="top center", cliponaxis=False, showlegend=False,
        textfont=dict(size=13, color=TEXTO),
        hovertemplate="%{x:.0f}: %{y:.1f} años de escuela<extra></extra>",
    ))
    fig.update_xaxes(title="Años", tickmode="array", tickvals=list(d["anio"]),
                     range=[1987, 2028], showline=True, linecolor=TEXTO, ticks="outside",
                     showgrid=False, tickformat="d")
    fig.update_yaxes(title="Grado de escolaridad", range=[0, 12], tickvals=list(range(0, 12)),
                     showline=True, linecolor=TEXTO, ticks="outside", gridcolor=REJILLA,
                     zeroline=False)
    return fig
