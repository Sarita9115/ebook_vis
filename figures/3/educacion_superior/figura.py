"""Evolución de la población con educación superior

viz_id: 3.educacion_superior

Mapa de burbujas de la península (Campeche, Yucatán y Quintana Roo). Cada
burbuja es un municipio con matrícula de educación superior escolarizada en el
ciclo 2024-2025; el birrete marca el lugar y el área de la burbuja, la matrícula.
A la derecha, la matrícula por entidad en los dos ciclos disponibles.

Fuente primaria  : SEP, Educación superior escolarizada 2024-2025 (datos.gob.mx).
Fuente secundaria: ANUIES, Anuario Estadístico de Educación Superior 2025-2026.

`datos` es la tabla de oro (pipelines/3/educacion_superior.py): una fila por
municipio (nivel="municipio", ciclo 2024-2025) y por entidad (nivel="entidad",
ciclos 2024-2025 y 2025-2026).
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

TITULO = "Evolución de la población con educación superior"
COLOR_BURBUJA = "#1f6f8b"
COLORES_CICLO = {"2024-2025": "#9ecae1", "2025-2026": "#08519c"}
PX_MAX = 62  # diámetro en píxeles de la burbuja más grande


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

    mun = datos[datos["nivel"] == "municipio"].dropna(subset=["lat", "lon"])
    ent = datos[datos["nivel"] == "entidad"]
    if mun.empty:
        return _vacia("Sin datos municipales para mostrar")
    mun = mun.sort_values("matricula", ascending=False)

    fig = make_subplots(
        rows=1, cols=2, column_widths=[0.64, 0.36], horizontal_spacing=0.03,
        specs=[[{"type": "geo"}, {"type": "xy"}]],
        subplot_titles=("Matrícula por municipio, ciclo 2024-2025", "Matrícula por entidad"),
    )

    maximo = float(mun["matricula"].max())
    sizeref = 2.0 * maximo / (PX_MAX ** 2)
    hover = (
        "<b>%{customdata[0]}</b>, %{customdata[1]}<br>"
        "Matrícula: %{customdata[2]:,.0f}<br>"
        "Nuevo ingreso: %{customdata[3]:,.0f}<br>"
        "Egresados: %{customdata[4]:,.0f}<br>"
        "Escuelas: %{customdata[5]:,.0f}<extra></extra>"
    )
    custom = np.column_stack([mun["municipio"], mun["entidad"], mun["matricula"],
                              mun["nuevo_ingreso"], mun["egresados"], mun["escuelas"]])

    fig.add_trace(go.Scattergeo(
        lat=mun["lat"], lon=mun["lon"], mode="markers", name="Matrícula",
        marker=dict(size=mun["matricula"], sizemode="area", sizeref=sizeref, sizemin=5,
                    color=COLOR_BURBUJA, opacity=0.45, line=dict(width=0.8, color=COLOR_BURBUJA)),
        customdata=custom, hovertemplate=hover, showlegend=False,
    ), row=1, col=1)

    # El birrete marca cada municipio y crece con la matrícula.
    tam_birrete = 11 + 17 * np.sqrt(mun["matricula"] / maximo)
    fig.add_trace(go.Scattergeo(
        lat=mun["lat"], lon=mun["lon"], mode="text", text=["🎓"] * len(mun),
        textfont=dict(size=list(tam_birrete)), customdata=custom, hovertemplate=hover,
        showlegend=False, name="Birrete",
    ), row=1, col=1)

    # Rótulo solo de los municipios más grandes, para no saturar el mapa.
    top = mun.head(6)
    fig.add_trace(go.Scattergeo(
        lat=top["lat"], lon=top["lon"], mode="text", text=top["municipio"],
        textposition="bottom center", textfont=dict(size=11, color="#222"),
        hoverinfo="skip", showlegend=False,
    ), row=1, col=1)

    # Panel derecho: matrícula por entidad en cada ciclo.
    for ciclo, color in COLORES_CICLO.items():
        sub = ent[ent["ciclo"] == ciclo].sort_values("entidad")
        if sub.empty:
            continue
        fig.add_trace(go.Bar(
            x=sub["entidad"], y=sub["matricula"], name=ciclo, marker_color=color,
            text=[f"{v:,.0f}" for v in sub["matricula"]], textposition="outside",
            hovertemplate="%{x}, " + ciclo + "<br>Matrícula: %{y:,.0f}<extra></extra>",
        ), row=1, col=2)
    fig.update_yaxes(title_text="Estudiantes", tickformat=",", row=1, col=2)
    fig.update_xaxes(showgrid=False, row=1, col=2)

    fig.update_layout(
        title=TITULO,
        geo=dict(
            scope="north america", resolution=50, projection_type="mercator",
            lonaxis=dict(range=[-92.6, -86.2]), lataxis=dict(range=[17.7, 21.9]),
            showland=True, landcolor="#f3efe6", showocean=True, oceancolor="#e3eef5",
            showcountries=True, countrycolor="#9a9a9a", showcoastlines=True, coastlinecolor="#7a8a96",
            showsubunits=True, subunitcolor="#b5b5b5", showlakes=False,
        ),
        barmode="group", bargap=0.25,
        legend=dict(orientation="h", x=0.67, y=-0.1, title_text="Ciclo escolar"),
        margin=dict(l=20, r=20, t=90, b=120), height=620, width=1180,
        annotations=list(fig.layout.annotations) + [
            dict(
                x=0.0, y=-0.22, xref="paper", yref="paper", xanchor="left", showarrow=False, align="left",
                text=("El área de la burbuja es proporcional a la matrícula. El ciclo 2024-2025 cubre solo la modalidad "
                      "escolarizada (SEP); el 2025-2026 es el total del Anuario ANUIES, por lo que no se leen como serie continua."),
                font=dict(size=11, color="#555"),
            )
        ],
    )
    return fig
