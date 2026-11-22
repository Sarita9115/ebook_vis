"""Subtema: Lo que se invierte hoy.

datos (Cuenta Pública 2025, Yucatán) necesita:
    ejecutor        str    "Secretaría de Educación", "COBAY", "CONALEP",
                           "CECyTEY", "IEAEY", "ITS", "UT", "UPY"
    nivel           str    "Básica", "Media superior", "Superior", "Adultos"
    monto_millones  float  gasto ejercido, millones de pesos
"""
import plotly.graph_objects as go

COLORES = {"Básica": "#1d9e75", "Media superior": "#5b9bd5",
           "Superior": "#7f77dd", "Adultos": "#e8833a"}


def figura(datos) -> go.Figure:
    d = datos.sort_values("monto_millones")
    total = d["monto_millones"].sum()
    fig = go.Figure(go.Bar(
        x=d["monto_millones"], y=d["ejecutor"], orientation="h",
        marker_color=[COLORES.get(n, "#999") for n in d["nivel"]],
        text=[f"${v:,.0f} M ({v / total:.0%})" for v in d["monto_millones"]],
        textposition="outside", customdata=d["nivel"], showlegend=False,
        hovertemplate="%{y} (%{customdata})<br>$%{x:,.1f} millones<extra></extra>",
    ))
    for n, c in COLORES.items():
        fig.add_trace(go.Bar(x=[None], y=[None], name=n, marker_color=c))
    fig.update_layout(
        title="Lo que se invierte hoy",
        xaxis=dict(title="Millones de pesos ejercidos, 2025", range=[0, d["monto_millones"].max() * 1.3]),
        yaxis=dict(title=None), template="plotly_white",
        legend=dict(orientation="h", y=-0.2), barmode="overlay",
    )
    return fig
