"""Unidades económicas de impacto ambiental o relación con la biodiversidad

viz_id: 2.unidades_en_reservas

Tabla de oro (`datos`): filas separadas por la columna `tipo`.
  tipo = "burbuja"   reserva, negocios (unidades económicas del DENUE con actividad que puede dañar la
                     naturaleza, a menos de 5 km de la reserva y asignadas a su reserva más cercana),
                     tema_principal, lon, lat (posición de la burbuja), ancla_lon, ancla_lat (punto de la reserva)
  tipo = "reserva" / "estado" / "vecino"   polígonos de fondo en EPSG:4326 (geometry)

Se dibujan las reservas con 40 o más unidades cerca y, para contrastar, las grandes reservas de selva
(Calakmul, Balam Kú, Balam Kin, Bala'an K'aax), que casi no tienen negocios alrededor.
Fuente primaria: Áreas Naturales Protegidas federales (CONANP). Secundaria: DENUE (INEGI).
"""

import math

import numpy as np
import plotly.graph_objects as go

TITULO = "Unidades económicas de impacto ambiental o relación con la biodiversidad"

MAR, TIERRA, VECINO, ANP, ANP_BORDE = "#A9D8DC", "#EFE6E1", "#C9CDD1", "#7CC47F", "#2E7D32"
BURBUJA, TEXTO, SUAVE, AGUA = "#E53935", "#1B2A3A", "#5A6876", "#3E7C86"
LETRA = "DejaVu Sans, Helvetica Neue, Arial, sans-serif"
CONTRASTE = ["Calakmul", "Balam Kú", "Balam Kin", "Bala'an K'aax"]
DIAM_MAX = 110        # diámetro en píxeles de la burbuja más grande
REFERENCIAS = [1000, 300, 50]
CAJA = (-92.5, -85.75, 17.75, 22.25)


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
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=f"<b>{TITULO}</b>", x=0.01, xanchor="left", y=0.975, font=dict(size=23, color=TEXTO)),
        width=1500, height=880, paper_bgcolor="white", plot_bgcolor=MAR, showlegend=False,
        font=dict(family=LETRA, size=13, color=TEXTO), margin=dict(l=20, r=20, t=110, b=20),
        xaxis=dict(domain=[0, 0.72]),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13)))
    if datos is None or len(datos) == 0:
        return fig
    fig.add_annotation(xref="paper", yref="paper", x=0, y=1.07, xanchor="left", showarrow=False,
                       text="¿Cuántos negocios rodean a cada reserva? Cada burbuja es una reserva natural: mientras "
                            "más grande, más negocios que pueden dañar la naturaleza hay a menos de 5 km.",
                       font=dict(size=14.5, color=SUAVE))

    for capa, relleno, borde, ancho, op in [("vecino", VECINO, "white", 0.8, 1), ("estado", TIERRA, "white", 1.6, 1),
                                             ("reserva", ANP, ANP_BORDE, 0.6, 0.7)]:
        xs, ys = _xy(datos.loc[datos["tipo"] == capa, "geometry"])
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=relleno, opacity=op,
                                 line=dict(color=borde, width=ancho), hoverinfo="skip"))

    for t, x, y, tam, color, estilo in [("GOLFO DE MÉXICO", -91.6, 21.55, 14, AGUA, "i"),
                                        ("MAR CARIBE", -86.75, 18.7, 14, AGUA, "i"),
                                        ("YUCATÁN", -88.9, 20.75, 16, "#A99C95", "b"),
                                        ("CAMPECHE", -90.35, 19.1, 16, "#A99C95", "b"),
                                        ("QUINTANA<br>ROO", -88.35, 19.25, 16, "#A99C95", "b")]:
        fig.add_annotation(x=x, y=y, text=f"<{estilo}>{t}</{estilo}>", showarrow=False, font=dict(size=tam, color=color))

    b = datos[datos["tipo"] == "burbuja"].sort_values("negocios", ascending=False)
    vmax = max(float(b["negocios"].max()), 1.0)

    movidas = b[(b["lon"] != b["ancla_lon"]) | (b["lat"] != b["ancla_lat"])]
    lx, ly = [], []
    for r in movidas.itertuples():
        lx += [r.ancla_lon, r.lon, None]
        ly += [r.ancla_lat, r.lat, None]
    fig.add_trace(go.Scatter(x=lx, y=ly, mode="lines", line=dict(color="#6B7780", width=1), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=movidas["ancla_lon"], y=movidas["ancla_lat"], mode="markers", hoverinfo="skip",
                             marker=dict(size=5, color="#6B7780")))

    con = b[b["negocios"] > 0]
    diam = DIAM_MAX * np.sqrt(con["negocios"] / vmax)
    fig.add_trace(go.Scatter(
        x=con["lon"], y=con["lat"], mode="markers",
        marker=dict(size=diam, color=BURBUJA, opacity=0.92, line=dict(color="white", width=1.5)),
        customdata=list(zip(con["reserva"], con["negocios"], con["tema_principal"])),
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:,} negocios a menos de 5 km<br>"
                      "Tipo más común: %{customdata[2]}<extra></extra>"))
    sin = b[b["negocios"] == 0]
    fig.add_trace(go.Scatter(x=sin["lon"], y=sin["lat"], mode="markers", hovertemplate="<b>%{text}</b><br>"
                             "0 negocios a menos de 5 km<extra></extra>", text=sin["reserva"],
                             marker=dict(size=9, color="white", line=dict(color=BURBUJA, width=1.5))))

    for r in b.itertuples():
        d = DIAM_MAX * math.sqrt(r.negocios / vmax)
        dentro = d >= 28
        if dentro:
            fig.add_annotation(x=r.lon, y=r.lat, text=f"<b>{int(r.negocios):,}</b>", showarrow=False,
                               font=dict(size=13 if d > 50 else 11, color="white"))
        else:
            fig.add_annotation(x=r.lon, y=r.lat, text=f"<b>{int(r.negocios):,}</b>", showarrow=False, xanchor="left",
                               xshift=max(d, 9) / 2 + 3, font=dict(size=11, color=BURBUJA),
                               bgcolor="rgba(255,255,255,0.6)", borderpad=0)
        fig.add_annotation(x=r.lon, y=r.lat, text=f"<b><i>{r.reserva}</i></b>", showarrow=False, yanchor="top",
                           yshift=-(max(d, 9) / 2 + 3), font=dict(size=10.5, color=ANP_BORDE),
                           bgcolor="rgba(255,255,255,0.55)", borderpad=0)

    lon0, lon1, lat0, lat1 = CAJA
    fig.update_xaxes(visible=False, range=[lon0, lon1])
    fig.update_yaxes(visible=False, range=[lat0, lat1], scaleanchor="x", scaleratio=1 / math.cos(math.radians(20)))

    # panel derecho: cómo leer + la más rodeada contra la más tranquila
    x0 = 0.75
    fig.add_shape(type="rect", xref="paper", yref="paper", x0=x0, x1=1, y0=0, y1=1, fillcolor="#F7F8FA",
                  line=dict(color="#D5DBE1", width=1.5), layer="below")
    nota = lambda y, txt, tam=13, color=TEXTO, dx=0.02: fig.add_annotation(  # noqa: E731
        xref="paper", yref="paper", x=x0 + dx, y=y, xanchor="left", yanchor="middle", showarrow=False,
        align="left", text=txt, font=dict(size=tam, color=color))
    nota(0.95, "<b>¿CÓMO LEER EL MAPA?</b>", 14)
    # burbujas de referencia apiladas sobre la misma base (mismo tamaño que en el mapa)
    alto_px = (880 - 130)
    base_y = 0.68
    for v in REFERENCIAS:
        d = DIAM_MAX * math.sqrt(v / vmax)
        cy = base_y + (d / 2) / alto_px
        fig.add_shape(type="circle", xref="paper", yref="paper", xsizemode="pixel", ysizemode="pixel",
                      xanchor=x0 + 0.08, yanchor=cy, x0=-d / 2, x1=d / 2, y0=-d / 2, y1=d / 2,
                      line=dict(color=BURBUJA, width=1.4))
        top = base_y + d / alto_px
        fig.add_shape(type="line", xref="paper", yref="paper", x0=x0 + 0.08, x1=x0 + 0.16, y0=top, y1=top,
                      line=dict(color="#9AA3AB", width=0.8, dash="dot"))
        nota(top, f"{v:,} negocios", 12, dx=0.165)
    fig.add_shape(type="rect", xref="paper", yref="paper", x0=x0 + 0.02, x1=x0 + 0.045, y0=0.56, y1=0.59,
                  fillcolor=ANP, line=dict(color=ANP_BORDE, width=1), opacity=0.8)
    nota(0.575, "<b>Reserva natural (ANP)</b>", 12.5, dx=0.055)

    mas = b.iloc[0]
    tranq = b[b["reserva"].isin(CONTRASTE)].sort_values("negocios").iloc[0] if b["reserva"].isin(CONTRASTE).any() \
        else b.iloc[-1]
    nota(0.47, "<b>LA MÁS RODEADA</b>", 12, SUAVE)
    nota(0.42, f"<b><i>{mas['reserva']}</i></b>", 17, ANP_BORDE)
    nota(0.37, f"<b>{int(mas['negocios']):,} negocios cerca</b>", 14, BURBUJA)
    nota(0.29, "<b>LA MÁS TRANQUILA</b>", 12, SUAVE)
    nota(0.24, f"<b><i>{tranq['reserva']}</i></b>", 17, ANP_BORDE)
    n = int(tranq["negocios"])
    nota(0.19, f"<b>{n:,} negocio{'s' if n != 1 else ''} cerca</b>", 14, ANP_BORDE)
    nota(0.07, "<i>Las burbujas fuera de su reserva se movieron<br>para que no se encimen (la línea las une).</i>",
         11, SUAVE)
    return fig
