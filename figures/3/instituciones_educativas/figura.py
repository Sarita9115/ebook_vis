"""Disponibilidad de instituciones educativas en Yucatán

viz_id: 3.instituciones_educativas

Mapa de calor de Mérida. Verde = mayor concentración de instituciones,
amarillo = concentración media, rojo = casi no hay. Un selector cambia entre
las dos fuentes: DENUE (primaria) y el catálogo de centros de trabajo de la
SEP (secundaria).

Fuente primaria  : INEGI, DENUE Yucatán 2026, servicios educativos (SCIAN 6111-6113).
Fuente secundaria: SEP, Catálogo de centros de trabajo (centros activos).

`datos` es la tabla de oro (pipelines/3/instituciones_educativas.py): una fila
por institución, con `fuente` ("DENUE" o "SEP"), `lat` y `lon` en EPSG:4326.
"""

import plotly.graph_objects as go

TITULO = "Disponibilidad de instituciones educativas en Yucatán"
CENTRO_MERIDA = dict(lat=20.975, lon=-89.62)

# Rojo casi sin instituciones, amarillo concentración media, verde la mayor.
ESCALA = [
    [0.00, "rgba(215,48,39,0)"],
    [0.12, "rgba(215,48,39,0.55)"],
    [0.50, "rgba(254,224,60,0.75)"],
    [1.00, "rgba(26,152,80,0.90)"],
]
ETIQUETAS = {"DENUE": "DENUE (INEGI)", "SEP": "Centros de trabajo (SEP)"}


def _vacia(mensaje: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=TITULO,
        annotations=[dict(text=mensaje, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)],
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


def figura(datos, estilo_mapa: str = "carto-positron") -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    if datos is None or len(datos) == 0:
        return _vacia("Sin datos para mostrar")

    fig = go.Figure()
    fuentes = [f for f in ("DENUE", "SEP") if (datos["fuente"] == f).any()]
    conteos = {}
    for i, fuente in enumerate(fuentes):
        sub = datos[datos["fuente"] == fuente].dropna(subset=["lat", "lon"])
        conteos[fuente] = len(sub)
        fig.add_trace(go.Densitymap(
            lat=sub["lat"], lon=sub["lon"], z=[1] * len(sub), radius=20,
            colorscale=ESCALA, showscale=False, name=ETIQUETAS[fuente],
            hoverinfo="skip", visible=(i == 0),
        ))

    botones = [
        dict(label=ETIQUETAS[f], method="update",
             args=[{"visible": [j == i for j in range(len(fuentes))]},
                   {"annotations[0].text": _nota(f, conteos[f])}])
        for i, f in enumerate(fuentes)
    ]

    leyenda = (
        "<b>Concentración de instituciones</b><br>"
        "<span style='color:#1a9850'>■</span> Mayor concentración<br>"
        "<span style='color:#f4c20d'>■</span> Concentración media<br>"
        "<span style='color:#d73027'>■</span> Casi no hay"
    )
    fig.update_layout(
        title=TITULO,
        map=dict(style=estilo_mapa, center=CENTRO_MERIDA, zoom=10.6),
        updatemenus=[dict(type="buttons", direction="right", x=0.0, y=1.06, xanchor="left", buttons=botones)],
        annotations=[
            dict(text=_nota(fuentes[0], conteos[fuentes[0]]), x=0.0, y=-0.04, xref="paper", yref="paper",
                 xanchor="left", yanchor="top", showarrow=False, font=dict(size=11, color="#555")),
            dict(text=leyenda, x=0.995, y=0.99, xref="paper", yref="paper", xanchor="right", yanchor="top",
                 showarrow=False, align="left", bgcolor="rgba(255,255,255,0.88)",
                 bordercolor="#bbb", borderwidth=1, borderpad=8, font=dict(size=12)),
        ],
        margin=dict(l=10, r=10, t=90, b=50), height=640, width=1000,
    )
    return fig


def _nota(fuente: str, n: int) -> str:
    return f"Municipio de Mérida · {n:,} instituciones según {ETIQUETAS[fuente]}. El color indica densidad relativa, no una cifra exacta."
