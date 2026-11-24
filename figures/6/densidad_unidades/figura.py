"""Distribución y densidad nacional de unidades económicas

viz_id: 6.densidad_unidades

Tabla de oro (`datos`): dos tipos de fila, separados por la columna `tipo`.
  tipo = "celda"   una fila por celda de 0.02 grados (unos 2 km) de la península
      entidad, celda_lng, celda_lat, unidades (DENUE, corte de mayo de 2026),
      unidades_entidad (total de la entidad), poblacion_entidad (Encuesta Intercensal 2025)
  tipo = "limite"  una fila por entidad con su contorno
      entidad, geometry (polígono o multipolígono en EPSG:4326)

Fuente primaria: DENUE (INEGI). Fuente secundaria: Encuesta Intercensal 2025 (INEGI).
Contorno de las entidades: Natural Earth 1:10m (dominio público), solo como capa de contexto.
El dato nacional ya viene recortado a Campeche, Yucatán y Quintana Roo.
"""

import math

import numpy as np
import plotly.graph_objects as go

TITULO = "Distribución y densidad nacional de unidades económicas"

GRIS = "#9a9a90"
CALIZA, TEXTO, TEXTO_2, REJILLA = "#f7f4ec", "#1d2a22", "#4f5b52", "#e4dfd2"
RELLENO, BORDE = "#efeadc", "#b9b4a4"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"
ESCALA = ["#c6e4d6", "#80bea3", "#2f8c70", "#165a46", "#0a2f24"]

# Ciudades de referencia (latitud, longitud, lado de la etiqueta). Solo se rotulan si hay unidades en su celda.
CIUDADES = {"Mérida": (20.97, -89.62, "der"), "Cancún": (21.16, -86.85, "izq"), "Playa del Carmen": (20.63, -87.07, "izq"),
            "Campeche": (19.85, -90.53, "der"), "Ciudad del Carmen": (18.65, -91.84, "der"), "Chetumal": (18.50, -88.30, "der")}


def _n(x):
    return f"{x:,.0f}".replace(",", " ")


def _contorno(geom):
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
        title=dict(text=TITULO, x=0, xanchor="left", y=0.97, yanchor="top", font=dict(size=22, color=TEXTO), pad=dict(l=10)),
        width=1100, height=820, paper_bgcolor=CALIZA, plot_bgcolor=CALIZA, showlegend=False,
        font=dict(family=LETRA, size=14, color=TEXTO), margin=dict(l=20, r=30, t=80, b=20),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13), bordercolor=REJILLA))
    if datos is None or len(datos) == 0:
        return fig
    celdas = datos[datos.tipo == "celda"].sort_values("unidades")
    limites = datos[datos.tipo == "limite"]

    # contorno de las entidades como contexto
    for r in limites.itertuples():
        xs, ys = _contorno(r.geometry)
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=RELLENO, line=dict(color=BORDE, width=1),
                                 hoverinfo="skip", showlegend=False))

    # celdas: punto con tamaño y color según unidades (logarítmico); las más densas quedan encima
    lg = np.log10(celdas.unidades.values)
    zmax = float(lg.max())
    ticks = [t for t in (0, 1, 2, 3, 4) if t <= zmax + 0.01]
    fig.add_trace(go.Scatter(
        x=celdas.celda_lng, y=celdas.celda_lat, mode="markers", showlegend=False,
        marker=dict(size=3 + 3.5 * lg, color=lg, cmin=0, cmax=zmax, opacity=0.92, line=dict(color=CALIZA, width=0.5),
                    colorscale=[[i / (len(ESCALA) - 1), c] for i, c in enumerate(ESCALA)],
                    colorbar=dict(title=dict(text="unidades por celda<br>(escala logarítmica)", font=dict(size=12, color=TEXTO_2)),
                                  tickvals=ticks, ticktext=[_n(10 ** t) for t in ticks], thickness=14, len=0.4, y=0.3,
                                  outlinewidth=0, tickfont=dict(size=12, color=TEXTO_2))),
        text=[f"<b>{e}</b><br>{_n(u)} unidades en esta celda de 2 km" for e, u in zip(celdas.entidad, celdas.unidades)],
        hoverinfo="text"))

    # ciudades: etiqueta con la celda más densa en un radio de ~6 km
    for nombre, (lat, lng, lado) in CIUDADES.items():
        cerca = celdas[(abs(celdas.celda_lat - lat) <= 0.06) & (abs(celdas.celda_lng - lng) <= 0.06)]
        if cerca.empty or cerca.unidades.max() < 300:
            continue
        der = lado == "der"
        fig.add_annotation(x=lng, y=lat, xref="x", yref="y", showarrow=False, align="left" if der else "right",
                           xanchor="left" if der else "right", xshift=14 if der else -14, yshift=16,
                           text=f"<b>{nombre}</b><br>{_n(cerca.unidades.max())} en una celda",
                           font=dict(size=12, color=TEXTO), bgcolor="rgba(247,244,236,0.8)")

    # unidades por cada 1 000 habitantes, por entidad
    e = (celdas.drop_duplicates("entidad")[["entidad", "unidades_entidad", "poblacion_entidad"]]
         .assign(pm=lambda t: t.unidades_entidad / t.poblacion_entidad * 1000).sort_values("pm", ascending=False))
    filas = "<br>".join(f"{r.entidad}: <b>{r.pm:.1f}</b>  ({_n(r.unidades_entidad)} unidades)" for r in e.itertuples())
    fig.add_annotation(xref="paper", yref="paper", x=0.01, y=0.97, xanchor="left", yanchor="top", showarrow=False, align="left",
                       text=f"<b>Unidades por cada 1 000 habitantes</b><br>{filas}", font=dict(size=13, color=TEXTO_2))

    x0, x1 = float(celdas.celda_lng.min()) - 0.1, float(celdas.celda_lng.max()) + 0.1
    y0, y1 = float(celdas.celda_lat.min()) - 0.1, float(celdas.celda_lat.max()) + 0.1
    fig.update_xaxes(visible=False, range=[x0, x1])
    fig.update_yaxes(visible=False, range=[y0, y1], scaleanchor="x", scaleratio=1 / math.cos(math.radians(20)))
    return fig
