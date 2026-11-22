"""Subtema: Pobreza y rezago.

datos (una fila por municipio de Yucatán) necesita:
    municipio      str
    pobreza_2010   float  % de población en pobreza (CONEVAL)
    pobreza_2020   float
    grado_rezago   str    "Muy bajo", "Bajo", "Medio", "Alto", "Muy alto" (IRS 2020)
Los puntos bajo la diagonal son municipios donde la pobreza bajó.
"""
import plotly.graph_objects as go

ORDEN = ["Muy bajo", "Bajo", "Medio", "Alto", "Muy alto"]
COLORES = {"Muy bajo": "#1d9e75", "Bajo": "#8fcf9f", "Medio": "#f2c14e",
           "Alto": "#e8833a", "Muy alto": "#c0392b"}


def figura(datos) -> go.Figure:
    fig = go.Figure()
    lim = [0, 100]
    fig.add_trace(go.Scatter(x=lim, y=lim, mode="lines", name="Sin cambio",
                             line=dict(color="#999", dash="dash"), hoverinfo="skip"))
    for g in ORDEN:
        s = datos[datos["grado_rezago"] == g]
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=s["pobreza_2010"], y=s["pobreza_2020"], mode="markers", name=f"Rezago {g.lower()}",
            marker=dict(size=10, color=COLORES[g], line=dict(width=0.5, color="#333")),
            text=s["municipio"],
            hovertemplate="%{text}<br>2010: %{x:.1f}%<br>2020: %{y:.1f}%<extra></extra>",
        ))
    top = datos.nlargest(5, "pobreza_2020")
    for _, r in top.iterrows():
        fig.add_annotation(x=r["pobreza_2010"], y=r["pobreza_2020"], text=r["municipio"],
                           showarrow=True, arrowhead=0, ax=25, ay=-20, font=dict(size=11))
    fig.add_annotation(x=95, y=8, text="Pobreza bajó ↓", showarrow=False, xanchor="right",
                       font=dict(color="#666"))
    fig.update_layout(
        title="Pobreza y rezago",
        xaxis=dict(title="Población en pobreza, 2010 (%)", range=[0, 100]),
        yaxis=dict(title="Población en pobreza, 2020 (%)", range=[0, 100], scaleanchor="x"),
        template="plotly_white", legend=dict(title="Rezago social 2020"),
    )
    return fig
