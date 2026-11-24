"""Movilidad y colaboración internacional

viz_id: 1.movilidad_internacional
El formato de fuentes agrupa los enlaces de este equipo en siete títulos.
Esta carpeta sigue el título del relato y no abre una carpeta extra.

Línea de tiempo por institución aliada: cada punto es un evento (intercambio,
campamento o convenio). El área del círculo es el número de participantes que
reporta la fuente; el color indica si llegan a Yucatán o viajan desde Yucatán.
Un rombo sin relleno marca un convenio o un evento sin cifra publicada.

`datos` es la tabla de oro (pipelines/1/movilidad_internacional.py).
"""

import pandas as pd
import plotly.graph_objects as go

TITULO = "Movilidad y colaboración internacional"
COLORES = {"Entrante": "#2a9d8f", "Saliente": "#e76f51", "Convenio": "#6c757d"}
ETIQUETA_SENTIDO = {
    "Entrante": "Llegan a Yucatán",
    "Saliente": "Viajan desde Yucatán",
    "Convenio": "Convenio o carta de intención",
}
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
    d["aliado"] = d["institucion_aliada"] + " · " + d["pais"]
    orden = list(d.sort_values("fecha")["aliado"].drop_duplicates())
    maximo = float(d["participantes_total"].max()) if d["participantes_total"].notna().any() else 1.0
    sizeref = 2.0 * maximo / (PX_MAX ** 2)

    fig = go.Figure()
    for sentido, color in COLORES.items():
        sub = d[d["sentido"] == sentido]
        if sub.empty:
            continue
        con_cifra = sub[sub["participantes_total"].notna()]
        sin_cifra = sub[sub["participantes_total"].isna()]
        hover = ("<b>%{customdata[0]}</b><br>%{x|%d %b %Y}<br>Participantes: %{customdata[1]}<br>%{customdata[2]}"
                 "<extra></extra>")
        if not con_cifra.empty:
            fig.add_trace(go.Scatter(
                x=con_cifra["fecha"], y=con_cifra["aliado"], mode="markers+text", name=ETIQUETA_SENTIDO[sentido],
                marker=dict(size=con_cifra["participantes_total"], sizemode="area", sizeref=sizeref, sizemin=8,
                            color=color, opacity=0.8, line=dict(width=1, color="white")),
                text=[f"{int(v)}" for v in con_cifra["participantes_total"]], textposition="middle right",
                customdata=list(zip(con_cifra["titulo"], con_cifra["participantes_total"].astype(int), con_cifra["nota"])),
                hovertemplate=hover,
            ))
        if not sin_cifra.empty:
            fig.add_trace(go.Scatter(
                x=sin_cifra["fecha"], y=sin_cifra["aliado"], mode="markers", name=ETIQUETA_SENTIDO[sentido],
                legendgroup=sentido, showlegend=con_cifra.empty,
                marker=dict(size=14, symbol="diamond-open", color=color, line=dict(width=2, color=color)),
                customdata=list(zip(sin_cifra["titulo"], ["sin cifra publicada"] * len(sin_cifra), sin_cifra["nota"])),
                hovertemplate=hover,
            ))

    fig.update_layout(
        title=TITULO,
        xaxis=dict(title="Año", showgrid=True, gridcolor="#e6e6e6"),
        yaxis=dict(categoryorder="array", categoryarray=orden[::-1], automargin=True, title=""),
        legend=dict(orientation="h", x=0, y=-0.18, title_text="", itemsizing="constant"),
        margin=dict(l=20, r=30, t=70, b=130), height=460, width=1000, plot_bgcolor="white",
        annotations=[dict(
            x=0, y=-0.42, xref="paper", yref="paper", xanchor="left", showarrow=False, align="left",
            text="El área del círculo es proporcional al número de participantes que reporta la fuente. El rombo marca un convenio o un evento sin cifra.",
            font=dict(size=11, color="#555"),
        )],
    )
    return fig
