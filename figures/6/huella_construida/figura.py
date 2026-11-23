"""Huella construida, altura y densidad empresarial de Mérida

viz_id: 6.huella_construida

Recibe la tabla de oro (formato largo con columna `capa`) y dibuja dos curvas
de concentración sobre la malla de 200 m de 6.relieve_5m: % acumulado de celdas
urbanas, ordenadas de mayor a menor huella construida o altura edificada,
contra % acumulado de negocios del DENUE. La diagonal punteada es el reparto
parejo. Los puntos marcan el 10% de celdas.
"""

import plotly.graph_objects as go

TITULO = "Huella construida, altura y densidad empresarial de Mérida"

MONTE = "#2F5D3A"
CENOTE = "#1F7A80"
CALIZA_OSCURA = "#9C8F6E"
TINTA = "#2B2A26"
TINTA_SUAVE = "#6B6457"
REJILLA = "#ECE6D8"
FONDO = "#FFFFFF"

COLOR = {"Huella": MONTE, "Altura": CENOTE}
ROTULO = {"Huella": "10% más construido", "Altura": "10% más alto"}
NOMBRE = {"Huella": "Huella construida", "Altura": "Altura edificada"}


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    curvas = datos[datos["capa"] == "curva"]
    puntos = datos[datos["capa"] == "punto"].set_index("criterio")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[0, 100], y=[0, 100], mode="lines", line=dict(color=CALIZA_OSCURA, width=1.5, dash="dot"),
        name="Reparto parejo", hoverinfo="skip",
    ))
    for criterio in ("Huella", "Altura"):
        c = curvas[curvas["criterio"] == criterio]
        fig.add_trace(go.Scatter(
            x=c["pct_celdas"], y=c["pct_negocios"], mode="lines", name=NOMBRE[criterio],
            line=dict(color=COLOR[criterio], width=3),
            hovertemplate=f"{NOMBRE[criterio]}<br>%{{x:.1f}}% de celdas: %{{y:.1f}}% de negocios<extra></extra>",
        ))

    for criterio, desplazamiento in (("Huella", (-50, -210)), ("Altura", (40, 34))):
        p = puntos.loc[criterio]
        fig.add_trace(go.Scatter(
            x=[p["pct_celdas"]], y=[p["pct_negocios"]], mode="markers", showlegend=False,
            marker=dict(size=12, color=COLOR[criterio], line=dict(color=FONDO, width=2)),
            hovertemplate=f"{ROTULO[criterio]}: %{{y:.1f}}% de negocios<extra></extra>",
        ))
        fig.add_annotation(
            x=p["pct_celdas"], y=p["pct_negocios"], ax=desplazamiento[0], ay=desplazamiento[1],
            text=f"<b>{ROTULO[criterio]}:{'<br>' if criterio == 'Huella' else ' '}{p['pct_negocios']:.0f}% de negocios</b>",
            showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=COLOR[criterio],
            font=dict(size=12, color=COLOR[criterio]), xanchor="left", align="left", bgcolor="rgba(255,255,255,0.85)",
        )

    fig.add_shape(type="line", x0=10, x1=10, y0=0, y1=100, line=dict(color=REJILLA, width=1.5), layer="below")
    n_celdas = int(puntos["celdas_urbanas"].iloc[0])
    n_negocios = int(puntos["negocios"].iloc[0])
    fig.update_xaxes(
        title=dict(text=f"% acumulado de celdas urbanas de 200 m ({n_celdas:,}), de mayor a menor", font=dict(size=12)),
        range=[0, 100], dtick=10, ticksuffix="%", showgrid=True, gridcolor=REJILLA, zeroline=False,
        tickfont=dict(size=11, color=TINTA_SUAVE), linecolor=TINTA_SUAVE,
    )
    fig.update_yaxes(
        title=dict(text=f"% acumulado de negocios ({n_negocios:,})", font=dict(size=12)),
        range=[0, 101], dtick=20, ticksuffix="%", showgrid=True, gridcolor=REJILLA, zeroline=False,
        tickfont=dict(size=11, color=TINTA_SUAVE), linecolor=TINTA_SUAVE,
    )
    fig.update_layout(
        title=dict(text=TITULO, x=0, xanchor="left", font=dict(size=17, color=TINTA)),
        font=dict(family="Open Sans, Verdana, Arial, sans-serif", color=TINTA),
        paper_bgcolor=FONDO, plot_bgcolor=FONDO,
        legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", font=dict(size=12)),
        margin=dict(l=70, r=30, t=100, b=60),
        hoverlabel=dict(bgcolor=FONDO, font=dict(color=TINTA)),
        height=640,
    )
    return fig
