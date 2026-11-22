"""Subtema: La casa cambió.

datos (formato largo, Yucatán, ITER 2010 y 2020) necesita:
    indicador   str    p. ej. "Piso firme", "Agua entubada", "Drenaje",
                       "Electricidad", "Computadora", "Internet"
    anio        int    2010 o 2020
    porcentaje  float  % de viviendas particulares habitadas
"""
import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    p = datos.pivot_table(index="indicador", columns="anio", values="porcentaje")
    p = p.sort_values(2020)
    fig = go.Figure()
    for ind, r in p.iterrows():
        fig.add_trace(go.Scatter(x=[r[2010], r[2020]], y=[ind, ind], mode="lines",
                                 line=dict(color="#bbb", width=4), showlegend=False,
                                 hoverinfo="skip"))
    for anio, color in [(2010, "#c0392b"), (2020, "#1d9e75")]:
        fig.add_trace(go.Scatter(
            x=p[anio], y=p.index, mode="markers+text", name=str(anio),
            marker=dict(size=14, color=color),
            text=[f"{v:.0f}%" for v in p[anio]],
            textposition="middle left" if anio == 2010 else "middle right",
            hovertemplate="%{y} · " + str(anio) + ": %{x:.1f}%<extra></extra>",
        ))
    fig.update_layout(
        title="La casa cambió",
        xaxis=dict(title="Viviendas con el servicio (%)", range=[0, 112]),
        yaxis=dict(title=None), template="plotly_white",
        legend=dict(orientation="h", y=-0.2),
    )
    return fig
