"""Subtema: Treinta años aprendiendo.

datos (tabla de oro, formato largo) necesita estas columnas:
    anio            int    1990, 2000, 2005, ... 2025 (1990 sale del Censo 1990)
    entidad         str    solo Campeche, Quintana Roo y Yucatán
    sexo            str    "Total", "Hombres", "Mujeres"
    grado_promedio  float  años de escolaridad, población de 15 años y más
"""
import plotly.graph_objects as go

ESTADOS = ["Campeche", "Quintana Roo", "Yucatán"]
COLORES = {"Campeche": "#8a8a8a", "Quintana Roo": "#5b9bd5", "Yucatán": "#1d9e75"}


def figura(datos) -> go.Figure:
    d = datos[(datos["sexo"] == "Total") & (datos["entidad"].isin(ESTADOS))]
    d = d.sort_values("anio")
    fig = go.Figure()
    for e in ESTADOS:
        s = d[d["entidad"] == e]
        if s.empty:
            continue
        es_yuc = e == "Yucatán"
        fig.add_trace(go.Scatter(
            x=s["anio"], y=s["grado_promedio"], name=e, mode="lines+markers",
            line=dict(width=4 if es_yuc else 2, color=COLORES[e]),
            marker=dict(size=8 if es_yuc else 5),
            opacity=1 if es_yuc else 0.65,
            hovertemplate=e + " · %{x}: %{y:.1f} años<extra></extra>",
        ))
        ult = s.iloc[-1]
        fig.add_annotation(
            x=ult["anio"], y=ult["grado_promedio"], text=f"{ult['grado_promedio']:.1f}",
            showarrow=False, xanchor="left", xshift=8,
            font=dict(color=COLORES[e], size=13 if es_yuc else 11),
        )
    y = d[d["entidad"] == "Yucatán"]
    if len(y) >= 2:
        ganancia = y.iloc[-1]["grado_promedio"] - y.iloc[0]["grado_promedio"]
        fig.add_annotation(
            xref="paper", yref="paper", x=0.01, y=0.97, showarrow=False, xanchor="left",
            text=f"Yucatán ganó {ganancia:.1f} años de escuela desde {int(y.iloc[0]['anio'])}",
            font=dict(size=13),
        )
    fig.update_layout(
        title="Treinta años aprendiendo",
        yaxis_title="Grado promedio de escolaridad (años)",
        xaxis=dict(title=None, dtick=5),
        template="plotly_white", legend=dict(orientation="h", y=-0.15),
        margin=dict(r=60),
    )
    return fig
