"""Dónde se cuida la península

viz_id: 2.donde_se_cuida

Mapa coroplético de los municipios de Yucatán, coloreados por población total
(Censo de Población y Vivienda 2020). La escala es logarítmica porque Mérida
concentra una parte enorme de la población y aplastaría al resto.

Tabla de oro (`datos`): una fila por municipio.
    nombre                       nombre del municipio (nomgeo)
    pob_total                    población total
    pob_femenina                 población femenina
    pob_masculina                población masculina
    total_viviendas_habitadas    viviendas habitadas
    geometry                     polígono o multipolígono en EPSG:4326

Fuente: INEGI, Marco Geoestadístico (diciembre de 2025) y Censo 2020.
La plantilla muestra fuentes, fecha y responsable; no van dentro de la figura.
"""

import math

import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sample_colorscale
from shapely.ops import unary_union

TITULO = "Dónde se cuida la península"

CALIZA, TEXTO, TEXTO_2 = "#f7f4ec", "#1d2a22", "#4f5b52"
BORDE = "#f7f4ec"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"
ESCALA = ["#c6e4d6", "#80bea3", "#2f8c70", "#165a46", "#0a2f24"]

# Tolerancia de simplificación en grados (~200 m). Producción ya simplifica al
# pasar a oro; esto solo protege a la figura si llega una geometría pesada.
SIMPLIFICA = 0.002

# Una parte del mapa a más de estos grados (~33 km) del cuerpo principal no cuenta
# para el encuadre; se dibuja, pero queda fuera de la vista.
LEJOS_GRADOS = 0.3

COLUMNAS_NUM = ["pob_total", "pob_femenina", "pob_masculina", "total_viviendas_habitadas"]


def _n(x) -> str:
    return f"{x:,.0f}".replace(",", " ")


def _contorno(geom):
    """Convierte un polígono o multipolígono en listas x, y con None entre anillos."""
    xs, ys = [], []
    for p in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom]):
        for anillo in [p.exterior, *p.interiors]:
            x, y = anillo.xy
            xs += list(x) + [None]
            ys += list(y) + [None]
    return xs, ys


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=TITULO, x=0, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=22, color=TEXTO), pad=dict(l=10)),
        width=1100, height=720, paper_bgcolor=CALIZA, plot_bgcolor=CALIZA,
        font=dict(family=LETRA, size=14, color=TEXTO),
        margin=dict(l=20, r=80, t=80, b=20),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13)),
    )
    if datos is None or len(datos) == 0:
        return fig

    df = datos.copy()
    # Las cifras de INEGI pueden llegar como texto ("1701").
    for c in COLUMNAS_NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["pob_total"])
    df = df[df["pob_total"] > 0].reset_index(drop=True)
    if df.empty:
        return fig

    geoms = [g.simplify(SIMPLIFICA, preserve_topology=True) for g in df.geometry]

    lg = df["pob_total"].map(math.log10)
    zmin, zmax = float(lg.min()), float(lg.max())
    rango = (zmax - zmin) or 1.0
    escala = [[i / (len(ESCALA) - 1), c] for i, c in enumerate(ESCALA)]
    colores = sample_colorscale(escala, [(v - zmin) / rango for v in lg])
    ticks = [t for t in range(0, 8) if zmin - 0.01 <= t <= zmax + 0.01]

    # Un polígono por municipio, con su color y su hover.
    for r, geom, color in zip(df.itertuples(), geoms, colores):
        x, y = _contorno(geom)
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines", fill="toself", fillcolor=color,
            line=dict(color=BORDE, width=0.8), showlegend=False,
            text=(f"<b>{r.nombre}</b><br>Población: {_n(r.pob_total)}"
                  f"<br>Mujeres: {_n(r.pob_femenina)} · Hombres: {_n(r.pob_masculina)}"
                  f"<br>Viviendas habitadas: {_n(r.total_viviendas_habitadas)}"),
            hoveron="fills", hoverinfo="text",
        ))

    # Traza invisible que solo sirve para dibujar la barra de color.
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", showlegend=False, hoverinfo="skip",
        marker=dict(
            color=[zmin], cmin=zmin, cmax=zmax, colorscale=escala, showscale=True,
            colorbar=dict(
                title=dict(text="Población<br>(escala logarítmica)", font=dict(size=12, color=TEXTO_2)),
                tickvals=ticks, ticktext=[_n(10 ** t) for t in ticks],
                thickness=14, len=0.5, y=0.3, outlinewidth=0,
                tickfont=dict(size=12, color=TEXTO_2)),
        ),
    ))

    # Etiqueta para los tres municipios más poblados, con línea guía y hacia lados
    # distintos (los más poblados suelen ser vecinos y se taparían).
    desplaza = [(-90, -45), (90, -45), (90, 45)]
    top = df.nlargest(3, "pob_total")
    for (i, nombre), (ax, ay) in zip(zip(top.index, top["nombre"]), desplaza):
        pt = geoms[i].representative_point()
        fig.add_annotation(x=pt.x, y=pt.y, xref="x", yref="y", text=f"<b>{nombre}</b>",
                           showarrow=True, arrowhead=0, arrowwidth=1.5, arrowcolor="#9a9a90",
                           axref="pixel", ayref="pixel", ax=ax, ay=ay,
                           font=dict(size=12, color=TEXTO), bgcolor="rgba(247,244,236,0.9)")

    # Encuadre: se ignoran las islas lejanas (p. ej. el Arrecife Alacranes, en Progreso,
    # a más de un grado de la costa), que dejarían el mapa chico y descentrado.
    partes = [p for g in geoms for p in (g.geoms if g.geom_type == "MultiPolygon" else [g])]
    total = sum(p.area for p in partes)
    nucleo = unary_union([p for p in partes if p.area >= 0.01 * total] or partes)
    grandes = [p for p in partes if p.distance(nucleo) <= LEJOS_GRADOS] or partes
    x0, y0 = min(p.bounds[0] for p in grandes), min(p.bounds[1] for p in grandes)
    x1, y1 = max(p.bounds[2] for p in grandes), max(p.bounds[3] for p in grandes)
    fig.update_xaxes(visible=False, range=[x0 - 0.05, x1 + 0.05])
    fig.update_yaxes(visible=False, range=[y0 - 0.05, y1 + 0.05], scaleanchor="x",
                     scaleratio=1 / math.cos(math.radians((y0 + y1) / 2)))
    return fig