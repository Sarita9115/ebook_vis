"""Cada tipo de negocio situado en cada reserva natural

viz_id: 2.negocios_en_reservas

Tabla de oro (`datos`): filas separadas por la columna `tipo`.
  tipo = "burbuja"   reserva, tema (tipo de negocio), negocios (unidades del DENUE a menos de 5 km de la
                     reserva, asignadas a su reserva más cercana), lon, lat (posición de la burbuja),
                     ancla_lon, ancla_lat (punto de la reserva; difiere de lon/lat si la burbuja se movió)
  tipo = "reserva" / "estado" / "vecino"   polígonos de fondo en EPSG:4326 (geometry)

Fuente primaria: DENUE (INEGI). Secundaria: Áreas Naturales Protegidas federales (CONANP).
"""

import math

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

TITULO = "Cada tipo de negocio situado en cada reserva natural"

MAR, TIERRA, VECINO, ANP, ANP_BORDE = "#A9D8DC", "#EFE6E1", "#C9CDD1", "#7CC47F", "#2E7D32"
TEXTO, SUAVE = "#1B2A3A", "#5A6876"
LETRA = "DejaVu Sans, Helvetica Neue, Arial, sans-serif"
ORDEN = ["Pesca y mariscos", "Construcción y materiales", "Hoteles y turismo",
         "Gasolina, gas y químicos", "Campo y ganado", "Basura y reciclaje"]
COLOR_TEMA = {"Pesca y mariscos": "#1E88E5", "Hoteles y turismo": "#FB8C00",
              "Construcción y materiales": "#8D6E63", "Gasolina, gas y químicos": "#7E57C2",
              "Campo y ganado": "#F9A825", "Basura y reciclaje": "#607D8B"}
NOMBRE_CORTO = {"Manglares de Nichupté": "Nichupté", "Manglares de Puerto Morelos": "Pto. Morelos",
                "San Buenaventura": "S. Buenaventura", "Cenote Aerolito": "C. Aerolito",
                "Laguna de Términos": "L. de Términos"}
MINIMO = 5            # en cada mapa se omiten las reservas con menos de 5 negocios de ese tipo
DIAM_MAX = 58         # diámetro en píxeles de la burbuja más grande
CAJA = (-92.5, -85.75, 17.75, 22.45)


def _xy(geoms):
    xs, ys = [], []
    for g in geoms:
        if g is None or g.is_empty:
            continue
        for p in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
            x, y = p.exterior.xy
            xs += list(x) + [None]
            ys += list(y) + [None]
    return xs, ys


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = make_subplots(rows=2, cols=3, horizontal_spacing=0.015, vertical_spacing=0.035)
    fig.update_layout(
        title=dict(text=f"<b>{TITULO}</b>", x=0.01, xanchor="left", y=0.975, font=dict(size=23, color=TEXTO)),
        width=1500, height=900, paper_bgcolor="white", plot_bgcolor=MAR, showlegend=False,
        font=dict(family=LETRA, size=13, color=TEXTO), margin=dict(l=15, r=15, t=105, b=15),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13)))
    if datos is None or len(datos) == 0:
        return fig
    fig.add_annotation(xref="paper", yref="paper", x=0, y=1.065, xanchor="left", showarrow=False,
                       text=f"Negocios a menos de 5 km de cada reserva, separados por tipo. Todos los mapas usan la "
                            f"misma escala (se omiten reservas con menos de {MINIMO}).",
                       font=dict(size=14.5, color=SUAVE))

    burb = datos[datos["tipo"] == "burbuja"]
    fondo = {t: _xy(datos.loc[datos["tipo"] == t, "geometry"]) for t in ("vecino", "estado", "reserva")}
    vmax = max(float(burb["negocios"].max()), 1.0)
    lon0, lon1, lat0, lat1 = CAJA
    ratio = 1 / math.cos(math.radians(20))

    for i, tema in enumerate(ORDEN):
        fila, col = i // 3 + 1, i % 3 + 1
        color = COLOR_TEMA[tema]
        for capa, relleno, borde, ancho, op in [("vecino", VECINO, "white", 0.6, 1), ("estado", TIERRA, "white", 1.2, 1),
                                                 ("reserva", ANP, ANP_BORDE, 0.5, 0.7)]:
            xs, ys = fondo[capa]
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=relleno, opacity=op,
                                     line=dict(color=borde, width=ancho), hoverinfo="skip"), row=fila, col=col)
        t = burb[(burb["tema"] == tema) & (burb["negocios"] >= MINIMO)].sort_values("negocios", ascending=False)

        # línea entre la reserva y la burbuja cuando se movió para no encimarse
        movidas = t[(t["lon"] != t["ancla_lon"]) | (t["lat"] != t["ancla_lat"])]
        lx, ly = [], []
        for r in movidas.itertuples():
            lx += [r.ancla_lon, r.lon, None]
            ly += [r.ancla_lat, r.lat, None]
        fig.add_trace(go.Scatter(x=lx, y=ly, mode="lines", line=dict(color="#6B7780", width=0.9), hoverinfo="skip"),
                      row=fila, col=col)
        fig.add_trace(go.Scatter(x=movidas["ancla_lon"], y=movidas["ancla_lat"], mode="markers", hoverinfo="skip",
                                 marker=dict(size=4, color="#6B7780")), row=fila, col=col)

        # burbujas: área proporcional al número de negocios
        diam = DIAM_MAX * np.sqrt(t["negocios"] / vmax)
        grande = diam >= 26
        fig.add_trace(go.Scatter(
            x=t["lon"], y=t["lat"], mode="markers",
            marker=dict(size=diam, color=color, opacity=0.92, line=dict(color="white", width=1.5)),
            customdata=list(zip(t["reserva"], t["negocios"])),
            hovertemplate=f"<b>%{{customdata[0]}}</b><br>%{{customdata[1]:,}} negocios de {tema.lower()} "
                          "a menos de 5 km<extra></extra>"), row=fila, col=col)
        # número dentro de la burbuja grande, al lado de la chica; nombre corto de la reserva
        for r, d, g in zip(t.itertuples(), diam, grande):
            nombre = NOMBRE_CORTO.get(r.reserva, r.reserva)
            al_este = r.lon > -86.6
            if g:
                fig.add_annotation(x=r.lon, y=r.lat, xref=f"x{i + 1 if i else ''}", yref=f"y{i + 1 if i else ''}",
                                   text=f"<b>{int(r.negocios):,}</b>", showarrow=False,
                                   font=dict(size=11, color="white"))
            fig.add_annotation(x=r.lon, y=r.lat, xref=f"x{i + 1 if i else ''}", yref=f"y{i + 1 if i else ''}",
                               text=(f"<b><i>{nombre}</i></b>" if g else
                                     f"<b>{int(r.negocios):,}</b> <i>{nombre}</i>"),
                               showarrow=False, xanchor="center" if g else ("right" if al_este else "left"),
                               yanchor="top" if g else "middle", yshift=-(d / 2 + 2) if g else 0,
                               xshift=0 if g else (-(d / 2 + 3) if al_este else d / 2 + 3),
                               font=dict(size=9, color=ANP_BORDE if g else color),
                               bgcolor="rgba(255,255,255,0.55)", borderpad=0)

        ref = "" if i == 0 else str(i + 1)
        fig.add_annotation(xref=f"x{ref} domain", yref=f"y{ref} domain", x=0.015, y=0.975, xanchor="left",
                           yanchor="top", showarrow=False, text=f"<b>{tema}</b>", font=dict(size=14, color="white"),
                           bgcolor=color, borderpad=4)
        fig.add_annotation(xref=f"x{ref} domain", yref=f"y{ref} domain", x=0.985, y=0.03, xanchor="right",
                           yanchor="bottom", showarrow=False,
                           text=f"<b>{int(t['negocios'].sum()):,} negocios cerca de reservas</b>",
                           font=dict(size=11.5, color=TEXTO), bgcolor="rgba(255,255,255,0.7)")
        fig.update_xaxes(visible=False, range=[lon0, lon1], row=fila, col=col)
        fig.update_yaxes(visible=False, range=[lat0, lat1], scaleanchor=f"x{ref}", scaleratio=ratio, row=fila, col=col)
        fig.add_shape(type="rect", xref=f"x{ref} domain", yref=f"y{ref} domain", x0=0, x1=1, y0=0, y1=1,
                      line=dict(color=color, width=2))
    return fig
