"""Obra pública e infraestructura para el desarrollo económico por municipio

viz_id: 6.obra_publica

Tabla de oro (`datos`): GeoDataFrame (EPSG:4326), una fila por municipio de Yucatán.
  cve_mun     clave del municipio (3 dígitos)
  municipio   nombre
  poblacion   habitantes (Encuesta Intercensal 2025, INEGI)
  monto       suma de obra pública con ubicación y monto publicado, pesos constantes de 2025 (ya sin obras gigantes)
  obras       número de obras que suman ese monto
  geometry    polígono del municipio

Fuente primaria: SSOP Yucatán, mapa de obras. Fuente secundaria: INEGI (población e INPC).
La figura no lee archivos: todo el cálculo por habitante sale de estas columnas.
"""

import math

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

TITULO = "Obra pública e infraestructura para el desarrollo económico por municipio"

MONTE, TERRACOTA, GRIS = "#1f8a70", "#d9622b", "#9a9a90"
CALIZA, TEXTO, TEXTO_2, REJILLA = "#f7f4ec", "#1d2a22", "#4f5b52", "#e4dfd2"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"
PALETA = ["#f6dccb", "#efc2a8", "#e48a5a", "#d9622b", "#a8431a"]   # de menos a más pesos por habitante
SIN_OBRA = "#e4dfd0"
RATIO = 1 / math.cos(math.radians(20.8))


def _p(x):
    return f"{x:,.0f}".replace(",", " ")


def _contorno(geom):
    xs, ys = [], []
    for p in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom]):
        for anillo in [p.exterior, *p.interiors]:
            x, y = anillo.xy
            xs += list(x) + [None]
            ys += list(y) + [None]
    return xs, ys


def _limites(geoms, dist_max=0.4):
    """(x0, x1, y0, y1) del cuerpo continental: ignora islas y arrecifes lejanos (p. ej. Alacranes)."""
    from shapely.ops import unary_union
    piezas = [p for g in geoms for p in (g.geoms if g.geom_type == "MultiPolygon" else [g])]
    grandes = [p for p in piezas if p.area >= 0.05] or [max(piezas, key=lambda p: p.area)]
    cuerpo = unary_union(grandes)
    cerca = [p for p in piezas if p.distance(cuerpo) <= dist_max]
    return (min(p.bounds[0] for p in cerca), max(p.bounds[2] for p in cerca),
            min(p.bounds[1] for p in cerca), max(p.bounds[3] for p in cerca))


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = make_subplots(rows=1, cols=2, column_widths=[0.5, 0.5], horizontal_spacing=0.07)
    fig.update_layout(
        title=dict(text=TITULO, x=0, xanchor="left", y=0.98, yanchor="top", font=dict(size=22, color=TEXTO), pad=dict(l=10)),
        width=1400, height=760, paper_bgcolor=CALIZA, plot_bgcolor=CALIZA, showlegend=False,
        font=dict(family=LETRA, size=14, color=TEXTO), margin=dict(l=20, r=30, t=120, b=120),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13), bordercolor=REJILLA))
    if datos is None or len(datos) == 0:
        return fig

    d = datos.copy()
    d["pc"] = d.monto / d.poblacion
    con = d[d.monto > 0]
    total_pc = d.monto.sum() / d.poblacion.sum()

    # clases por cuantiles de los municipios con obra
    cortes = [c for c in np.unique(np.round(np.quantile(con.pc, [0.2, 0.4, 0.6, 0.8]), -1)) if c > 0]
    d["clase"] = [-1 if m == 0 else int(np.searchsorted(cortes, v, side="right")) for m, v in zip(d.monto, d.pc)]
    lim = [0, *cortes, math.inf]
    etiquetas = {k: (f"Menos de {_p(lim[1])}" if k == 0 else f"Más de {_p(lim[-2])}" if lim[k + 1] == math.inf
                     else f"{_p(lim[k])} a {_p(lim[k + 1])}") for k in range(len(lim) - 1)}
    etiquetas[-1] = "Sin obra con monto publicado"
    colores = {k: PALETA[min(k, len(PALETA) - 1)] for k in range(len(lim) - 1)}
    colores[-1] = SIN_OBRA

    # ---- mapa ----
    for r in d.itertuples():
        xs, ys = _contorno(r.geometry)
        txt = (f"<b>{r.municipio}</b><br>{_p(r.poblacion)} habitantes<br>" +
               (f"{_p(r.pc)} pesos por habitante<br>{int(r.obras)} obras, {_p(r.monto / 1e6)} millones" if r.monto > 0
                else "Sin obra con monto publicado"))
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=colores[r.clase], line=dict(color=CALIZA, width=0.6),
                                 showlegend=False, text=txt, hoveron="fills", hoverinfo="text"), row=1, col=1)
    x0, x1, y0, y1 = _limites(d.geometry)
    fig.update_xaxes(visible=False, range=[x0 - 0.05, x1 + 0.05], row=1, col=1)
    fig.update_yaxes(visible=False, range=[y0 - 0.05, y1 + 0.05], scaleanchor="x", scaleratio=RATIO, row=1, col=1)

    # ---- dispersión: habitantes contra pesos por habitante ----
    merida = d[d.municipio.str.contains("Mérida", na=False)]
    merida = merida.iloc[0] if len(merida) else None
    resto = con if merida is None else con[con.cve_mun != merida.cve_mun]
    fig.add_trace(go.Scatter(x=resto.poblacion, y=resto.pc, mode="markers", showlegend=False,
                             marker=dict(color=MONTE, size=9, opacity=0.7, line=dict(color=CALIZA, width=0.8)),
                             text=[f"<b>{r.municipio}</b><br>{_p(r.poblacion)} habitantes<br>{_p(r.pc)} pesos por habitante" for r in resto.itertuples()],
                             hoverinfo="text"), row=1, col=2)
    if merida is not None and merida.monto > 0:
        fig.add_trace(go.Scatter(x=[merida.poblacion], y=[merida.pc], mode="markers", showlegend=False,
                                 marker=dict(color=TERRACOTA, size=14, line=dict(color=CALIZA, width=1)),
                                 text=[f"<b>{merida.municipio}</b><br>{_p(merida.poblacion)} habitantes<br>{_p(merida.pc)} pesos por habitante"],
                                 hoverinfo="text"), row=1, col=2)
    fig.add_hline(y=total_pc, line=dict(color=GRIS, width=1.2, dash="dash"), row=1, col=2)
    fig.add_annotation(x=0.72, xref="x2 domain", y=math.log10(total_pc), yref="y2", text=f"Promedio estatal: {_p(total_pc)}",
                       showarrow=False, xanchor="left", yanchor="bottom", yshift=3, font=dict(size=12, color=TEXTO_2))
    top, bajo = con.sort_values("pc").iloc[-1], con.sort_values("pc").iloc[0]
    vistos = set()
    for f, dx, dy, col in ((merida, 14, 14, TERRACOTA), (top, 12, 10, TEXTO), (bajo, 12, -14, TEXTO)):
        if f is None or f.monto <= 0 or f.cve_mun in vistos:
            continue
        vistos.add(f.cve_mun)
        extra = f"<br>{int(f.obras)} obras, {_p(f.monto / 1e6)} millones" if f.cve_mun == top.cve_mun and f.pc > 5 * total_pc else ""
        fig.add_annotation(x=math.log10(f.poblacion), y=math.log10(f.pc), xref="x2", yref="y2", text=f"<b>{f.municipio}</b>{extra}",
                           showarrow=False, xshift=dx, yshift=dy, xanchor="left", align="left", font=dict(size=12, color=col))
    fig.update_xaxes(type="log", title=dict(text="Habitantes (escala logarítmica)", font=dict(size=13, color=TEXTO_2)),
                     tickvals=[1000, 3000, 10000, 30000, 100000, 1000000], ticktext=["1 000", "3 000", "10 000", "30 000", "100 000", "1 000 000"],
                     gridcolor=REJILLA, row=1, col=2)
    fig.update_yaxes(type="log", title=dict(text="Pesos por habitante (logarítmica)", font=dict(size=13, color=TEXTO_2)),
                     tickvals=[10, 100, 1000, 10000, 100000], ticktext=["10", "100", "1 000", "10 000", "100 000"],
                     gridcolor=REJILLA, row=1, col=2)

    # subtítulos de cada panel
    fig.add_annotation(text="<b>Pesos por habitante, por municipio</b>", xref="x domain", yref="paper", x=0, y=1.02, showarrow=False,
                       xanchor="left", yanchor="bottom", font=dict(size=14))
    fig.add_annotation(text="<b>Tamaño del municipio y obra por habitante</b>", xref="x2 domain", yref="paper", x=0, y=1.02, showarrow=False,
                       xanchor="left", yanchor="bottom", font=dict(size=14))
    # leyenda del mapa, como texto y en orden, debajo del mapa
    orden = sorted(set(d.clase) - {-1}) + ([-1] if (d.clase == -1).any() else [])
    item = lambda k: f"<span style='color:{colores[k]}'>■</span> {etiquetas[k]}"
    fig.add_annotation(text="<b>Pesos por habitante (pesos de 2025)</b><br>" + "     ".join(item(k) for k in orden[:3]) + "<br>" + "     ".join(item(k) for k in orden[3:]),
                       xref="paper", yref="paper", x=0, y=-0.03, xanchor="left", yanchor="top", showarrow=False, align="left",
                       font=dict(size=13, color=TEXTO_2))
    return fig
