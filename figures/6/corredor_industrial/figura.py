"""Concentración industrial en el corredor Mérida, Umán y Hunucmá

viz_id: 6.corredor_industrial

Recibe la tabla de oro (GeoDataFrame en EPSG:4326, formato largo con columna
`capa`) y arma tres paneles:

1. s7_mapa_industria: establecimientos de manufactura y de transporte y
   almacenamiento con 11 o más personas en Mérida, Umán y Hunucmá (2026).
   El tamaño del punto es el personal aproximado.
2. Dona con la parte del personal aproximado que reúne el corredor en 2026.
3. s7_concentracion: % del personal por grupo en los cortes 2018, 2019, 2020
   y 2026. No hay cortes de 2021 a 2025: ese tramo va punteado.

Cada grupo conserva su color en los tres paneles. El mapa se dibuja en ejes
cartesianos (lon/lat con escala corregida), sin teselas externas.
"""

import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots

TITULO = "Concentración industrial en el corredor Mérida, Umán y Hunucmá"
RESTO = "Resto del estado"
GRUPOS = ["Mérida", "Umán", "Hunucmá", RESTO]
CORREDOR = ["Mérida", "Umán", "Hunucmá"]

# Paleta del ebook: verde de monte, caliza, agua de cenote y terracota.
TERRACOTA = "#C2562F"
CENOTE = "#1F7A80"
MONTE = "#2F5D3A"
CALIZA = "#CBBF9F"
CALIZA_OSCURA = "#9C8F6E"
CALIZA_FONDO = "#F2EDE1"
TINTA = "#2B2A26"
TINTA_SUAVE = "#6B6457"
REJILLA = "#ECE6D8"
FONDO = "#FFFFFF"

COLOR = {"Mérida": TERRACOTA, "Umán": CENOTE, "Hunucmá": MONTE, RESTO: CALIZA_OSCURA}


def _rgba(hex_color: str, alfa: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alfa})"


def _exteriores(geometrias):
    xs, ys = [], []
    for geom in geometrias:
        if geom is None or geom.is_empty:
            continue
        for p in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom]):
            x, y = p.exterior.coords.xy
            xs += list(x) + [None]
            ys += list(y) + [None]
    return xs, ys


def _pct(valor: float) -> str:
    """Entero arriba de 10 %; un decimal abajo, para no borrar a Hunucmá."""
    return f"{valor:.0f}%" if valor >= 10 else f"{valor:.1f}%"


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    part = datos[datos["capa"] == "participacion"].copy()
    part["anio"] = part["anio"].astype(int)
    anios = sorted(part["anio"].unique())
    actual = anios[-1]
    continuos = [a for a in anios if a <= 2020]
    ultimo_continuo = continuos[-1]
    pct = part.pivot_table(index="anio", columns="grupo", values="pct")[GRUPOS]
    corredor_actual = pct.loc[actual, CORREDOR].sum()

    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[[{"type": "xy", "rowspan": 2}, {"type": "domain"}], [None, {"type": "xy"}]],
        column_widths=[0.54, 0.46],
        row_heights=[0.44, 0.56],
        horizontal_spacing=0.06,
        vertical_spacing=0.14,
        subplot_titles=(
            f"Establecimientos industriales y logísticos del corredor ({actual})",
            f"Personal ocupado aproximado ({actual})",
            "% del personal por corte",
        ),
    )

    # 1. Mapa del corredor
    contornos = datos[datos["capa"] == "contorno"]
    for _, fila in contornos.iterrows():
        xs, ys = _exteriores([fila.geometry])
        fig.add_trace(
            go.Scatter(
                x=xs, y=ys, mode="lines", fill="toself", fillcolor=CALIZA_FONDO,
                line=dict(color=CALIZA, width=1.2), hoverinfo="skip", showlegend=False,
            ),
            row=1, col=1,
        )
    # Nombres en la parte sur de cada municipio, lejos de la nube de puntos.
    for _, fila in contornos.iterrows():
        x_min, y_min, x_max, y_max = fila.geometry.bounds
        fig.add_annotation(
            x=fila.geometry.centroid.x, y=y_min + 0.2 * (y_max - y_min),
            text=f"<b>{fila['grupo']}</b>", showarrow=False, xref="x", yref="y",
            font=dict(size=12, color=TINTA_SUAVE),
        )

    puntos = datos[datos["capa"] == "establecimiento"].sort_values("personal_aprox", ascending=False)
    maximo = float(puntos["personal_aprox"].max())
    for grupo in CORREDOR:
        p = puntos[puntos["grupo"] == grupo]
        fig.add_trace(
            go.Scatter(
                x=p.geometry.x, y=p.geometry.y, mode="markers", name=grupo,
                legendgroup=grupo, showlegend=False,
                marker=dict(
                    size=p["personal_aprox"], sizemode="area", sizeref=2 * maximo / 26 ** 2,
                    sizemin=3, color=_rgba(COLOR[grupo], 0.7),
                    line=dict(color=FONDO, width=0.6),
                ),
                customdata=p[["sector", "per_ocu"]].values,
                hovertemplate=f"{grupo}<br>%{{customdata[0]}}<br>%{{customdata[1]}}<extra></extra>",
            ),
            row=1, col=1,
        )

    x0, y0, x1, y1 = contornos.total_bounds
    lat = (y0 + y1) / 2
    fig.update_xaxes(row=1, col=1, range=[x0 - 0.02, x1 + 0.02], visible=False,
                     scaleanchor="y", scaleratio=math.cos(math.radians(lat)), constrain="domain")
    fig.update_yaxes(row=1, col=1, range=[y0 - 0.02, y1 + 0.02], visible=False, constrain="domain")

    # 2. Dona
    valores = [pct.loc[actual, g] for g in GRUPOS]
    fig.add_trace(
        go.Pie(
            labels=GRUPOS, values=valores, hole=0.62, sort=False, direction="clockwise",
            rotation=0, marker=dict(colors=[COLOR[g] for g in GRUPOS], line=dict(color=FONDO, width=2)),
            text=[f"{g} {_pct(v)}" for g, v in zip(GRUPOS, valores)], textinfo="text",
            textposition="outside",
            title=dict(
                text=f"<b>{corredor_actual:.0f}%</b><br><span style='font-size:11px'>en el corredor</span>",
                position="middle center", font=dict(size=22, color=TINTA),
            ),
            textfont=dict(size=11, color=TINTA), showlegend=False,
            hovertemplate="%{label}<br>%{value:.1f} % del personal aproximado<extra></extra>",
        ),
        row=1, col=2,
    )
    dominio = fig.data[-1].domain

    # 3. Concentración por corte
    for grupo in GRUPOS:
        color = COLOR[grupo]
        ancho = 3 if grupo == "Mérida" else 2
        fig.add_trace(
            go.Scatter(
                x=continuos, y=[pct.loc[a, grupo] for a in continuos], mode="lines+markers",
                line=dict(color=color, width=ancho), marker=dict(size=7, color=color),
                name=grupo, showlegend=False,
                hovertemplate=f"{grupo} · %{{x}}<br>%{{y:.1f}} %<extra></extra>",
            ),
            row=2, col=2,
        )
        fig.add_trace(
            go.Scatter(
                x=[ultimo_continuo, actual], y=[pct.loc[ultimo_continuo, grupo], pct.loc[actual, grupo]],
                mode="lines+markers", line=dict(color=color, width=ancho, dash="dot"),
                marker=dict(size=[0, 7], color=color), showlegend=False,
                hovertemplate=f"{grupo} · %{{x}}<br>%{{y:.1f}} %<extra></extra>",
            ),
            row=2, col=2,
        )

    # Rótulos directos en el último corte, separados para que no se encimen.
    finales = sorted(((pct.loc[actual, g], g) for g in GRUPOS), reverse=True)
    posiciones, separacion = [], 6.5
    for valor, _ in finales:
        y = valor if not posiciones else min(valor, posiciones[-1] - separacion)
        posiciones.append(y)
    for (valor, grupo), y in zip(finales, posiciones):
        fig.add_annotation(
            x=actual, y=y, xref="x2", yref="y2", text=f"<b>{grupo} {_pct(valor)}</b>",
            showarrow=False, xanchor="left", xshift=9, font=dict(size=11, color=COLOR[grupo]),
        )

    fig.add_shape(
        type="line", xref="x2", yref="y2 domain", x0=ultimo_continuo + 0.5, x1=ultimo_continuo + 0.5,
        y0=0, y1=1, line=dict(color=TINTA_SUAVE, width=1, dash="dot"),
    )
    fig.update_xaxes(
        row=2, col=2, tickvals=anios, ticktext=[str(a) for a in anios], range=[anios[0] - 0.4, actual + 3.6],
        showgrid=False, tickfont=dict(size=11, color=TINTA), zeroline=False,
    )
    fig.update_yaxes(
        row=2, col=2, range=[0, 70], dtick=20, ticksuffix="%", showgrid=True, gridcolor=REJILLA,
        zeroline=False, tickfont=dict(size=10, color=TINTA_SUAVE),
    )

    for anotacion, x in zip(fig.layout.annotations, (0, dominio.x[0], fig.layout.xaxis2.domain[0])):
        anotacion.update(x=x, xanchor="left", font=dict(size=13, color=TINTA))

    fig.update_layout(
        title=dict(text=TITULO, x=0, xanchor="left", font=dict(size=17, color=TINTA)),
        font=dict(family="Open Sans, Verdana, Arial, sans-serif", color=TINTA),
        paper_bgcolor=FONDO,
        plot_bgcolor=FONDO,
        margin=dict(l=20, r=20, t=90, b=30),
        hoverlabel=dict(bgcolor=FONDO, font=dict(color=TINTA)),
        height=760,
    )
    return fig
