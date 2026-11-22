"""Impacto por municipio ocasionado por la cría de cerdo en la península

viz_id: 2.cria_de_cerdo

Tabla de oro (`datos`): una fila por geometría (EPSG:4326), separada por la columna `tipo`.
  tipo = "municipio"  cve_ent, nombre, cerdos (existencias al 15 sep 2022), unidades (unidades de
                      producción con porcinos), cerdos_por_unidad, granja_grande, geometry
  tipo = "reserva"    nombre, cerdos_entorno (cerdos de los municipios que tocan la reserva o su franja
                      de 10 km), municipios_entorno, municipio_top, cerdos_municipio_top, geometry
  tipo = "franja"     contorno de la franja de 10 km alrededor de las reservas
  tipo = "vecino" / "estado"   capas de contexto (países vecinos y contorno estatal)

Granja grande = municipio con al menos 10 mil cerdos y más de 1 000 cerdos por unidad de producción.
Fuente primaria: Censo Agropecuario 2022 (INEGI). Secundaria: Áreas Naturales Protegidas federales (CONANP).
"""

import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots

TITULO = "Impacto por municipio ocasionado por la cría de cerdo en la península"

MAR, VECINO, TEXTO, SUAVE, AGUA = "#A9D8DC", "#B9BDC2", "#1B2A3A", "#4A5868", "#3E7C86"
ANP, ANP_BORDE, ACENTO, CERDO = "#43A047", "#1B5E20", "#C2185B", "#F4A6B8"
LETRA = "DejaVu Sans, Helvetica Neue, Arial, sans-serif"
CLASES = [  # cerdos por municipio
    (0, 1_000, "#FBEFF2", "Menos de 1 mil"),
    (1_000, 10_000, "#F6C9D4", "1 mil – 10 mil"),
    (10_000, 50_000, "#EC8FA8", "10 mil – 50 mil"),
    (50_000, 100_000, "#D9466F", "50 mil – 100 mil"),
    (100_000, 10**12, "#8E0E3C", "Más de 100 mil"),
]
TOP_N = 6
# posición (lon, lat) de las etiquetas para que no se encimen
POS_TOP = {"Mérida": (-89.95, 21.42), "Maxcanú": (-90.50, 20.62), "Opichén": (-90.20, 20.22),
           "Muna": (-89.05, 20.38), "Abalá": (-89.20, 20.68), "Yaxcabá": (-88.75, 20.22)}
POS_ANP = {"Calakmul": (-89.75, 18.20), "Balam Kú": (-90.30, 18.45), "Balam Kin": (-90.05, 19.15),
           "Los Petenes": (-90.75, 20.30), "Ría Celestún": (-90.75, 21.00), "Ría Lagartos": (-88.15, 21.72),
           "Yum Balam": (-87.30, 21.65), "Sian Ka'an": (-87.05, 19.95), "Uaymil": (-87.65, 18.85),
           "Bala'an K'aax": (-88.85, 19.10), "Laguna de Términos": (-91.25, 18.25),
           "Otoch Ma'ax Yetel Kooh": (-87.85, 20.95), "Dzibilchaltún": (-89.15, 21.45), "Nuevo Uxmal": (-89.70, 19.92)}
CIUDADES = [("Campeche", -90.53, 19.85), ("Cancún", -86.85, 21.16), ("Chetumal", -88.30, 18.50),
            ("Valladolid", -88.20, 20.69)]
CAJA = (-92.6, -86.6, 17.75, 21.75)   # lon_min, lon_max, lat_min, lat_max


def _miles(v):
    return f"{v / 1e6:.1f} M" if v >= 1e6 else f"{v / 1e3:,.0f} mil"


def _anillos(geom, huecos=False):
    """Coordenadas x, y de un (multi)polígono o línea, separadas por None."""
    xs, ys = [], []
    if geom is None or geom.is_empty:
        return xs, ys
    t = geom.geom_type
    if t in ("LineString", "LinearRing"):
        partes = [geom]
    elif t == "MultiLineString":
        partes = list(geom.geoms)
    else:
        partes = []
        for p in (geom.geoms if t == "MultiPolygon" else [geom]):
            partes += [p.exterior] + (list(p.interiors) if huecos else [])
    for a in partes:
        x, y = a.xy
        xs += list(x) + [None]
        ys += list(y) + [None]
    return xs, ys


def _poligonos(fig, geoms, relleno, borde, ancho, nombre=None, leyenda=False, opacidad=1.0, **kw):
    xs, ys = [], []
    for g in geoms:
        x, y = _anillos(g)
        xs += x
        ys += y
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself" if relleno else None, fillcolor=relleno,
                             line=dict(color=borde, width=ancho), opacity=opacidad, hoverinfo="skip",
                             name=nombre, showlegend=leyenda, legendgroup=nombre, **kw), row=1, col=1)


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = make_subplots(rows=1, cols=2, column_widths=[0.74, 0.26], horizontal_spacing=0.09)
    fig.update_layout(
        title=dict(text=f"<b>{TITULO}</b>", x=0.01, xanchor="left", y=0.97, font=dict(size=23, color=TEXTO)),
        width=1500, height=900, paper_bgcolor="white", plot_bgcolor=MAR,
        font=dict(family=LETRA, size=13, color=TEXTO), margin=dict(l=20, r=30, t=110, b=30),
        legend=dict(x=0.775, y=1.0, xanchor="left", yanchor="top", bgcolor="#F7F8FA", bordercolor="#C9D1D9",
                    borderwidth=1, font=dict(size=12.5), title=dict(text="<b>¿Cómo leer el mapa?</b>"),
                    tracegroupgap=2),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13)))
    if datos is None or len(datos) == 0:
        return fig
    fig.add_annotation(xref="paper", yref="paper", x=0, y=1.06, xanchor="left", showarrow=False,
                       text="Península de Yucatán · Cerdos por municipio y reservas naturales federales",
                       font=dict(size=15, color=SUAVE))

    mun = datos[datos["tipo"] == "municipio"]
    res = datos[datos["tipo"] == "reserva"]

    # fondo: países vecinos
    _poligonos(fig, datos.loc[datos["tipo"] == "vecino", "geometry"], VECINO, "white", 0.8)

    # municipios por clase de cerdos
    for lo, hi, color, etiqueta in CLASES:
        sub = mun[(mun["cerdos"] >= lo) & (mun["cerdos"] < hi)]
        _poligonos(fig, sub.geometry, color, "white", 0.4, nombre=f"{etiqueta} cerdos ({len(sub)} mun.)",
                   leyenda=True, legendgrouptitle=dict(text="Cerdos por municipio") if lo == 0 else None)
    # contorno estatal
    _poligonos(fig, datos.loc[datos["tipo"] == "estado", "geometry"], None, "#5F6B76", 1.4)
    # franja de 10 km y reservas
    _poligonos(fig, datos.loc[datos["tipo"] == "franja", "geometry"], None, ANP_BORDE, 1, nombre="Franja de 10 km "
               "alrededor de la reserva", leyenda=True)
    fig.data[-1].line.dash = "dash"
    _poligonos(fig, res.geometry, ANP, ANP_BORDE, 1, nombre="Reserva natural (ANP)", leyenda=True, opacidad=0.85)

    # lectura al pasar el cursor: un punto invisible por municipio y por reserva
    pm = mun.geometry.representative_point()
    fig.add_trace(go.Scatter(
        x=pm.x, y=pm.y, mode="markers", marker=dict(size=10, opacity=0), showlegend=False,
        customdata=list(zip(mun["nombre"], mun["cerdos"], mun["unidades"], mun["cerdos_por_unidad"].round())),
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:,} cerdos<br>%{customdata[2]:,} unidades de "
                      "producción<br>%{customdata[3]:,} cerdos por unidad<extra></extra>"), row=1, col=1)
    pr = res.geometry.representative_point()
    fig.add_trace(go.Scatter(
        x=pr.x, y=pr.y, mode="markers", marker=dict(size=12, opacity=0), showlegend=False,
        customdata=list(zip(res["nombre"], res["cerdos_entorno"], res["municipios_entorno"], res["municipio_top"],
                            res["cerdos_municipio_top"])),
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:,} cerdos en los %{customdata[2]} municipios a "
                      "menos de 10 km<br>El que más: %{customdata[3]} (%{customdata[4]:,})<extra></extra>"),
        row=1, col=1)

    # granjas grandes
    gg = mun[mun["granja_grande"].astype(bool)]
    pg = gg.geometry.representative_point()
    fig.add_trace(go.Scatter(
        x=pg.x, y=pg.y, mode="markers", name="Granjas grandes (más de 1 000 cerdos por granja, en promedio)",
        marker=dict(symbol="circle", size=15, color=CERDO, line=dict(color="#B0305A", width=2)),
        customdata=list(zip(gg["nombre"], gg["cerdos_por_unidad"].round())),
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:,} cerdos por unidad de producción<extra></extra>"),
        row=1, col=1)

    # municipios con más cerdos
    for _, r in mun.nlargest(TOP_N, "cerdos").iterrows():
        p = r.geometry.representative_point()
        tx, ty = POS_TOP.get(r["nombre"], (p.x, p.y + 0.17))
        fig.add_annotation(x=p.x, y=p.y, ax=tx, ay=ty, axref="x", ayref="y", xref="x", yref="y",
                           text=f"<b>{r['nombre']}<br>{_miles(r['cerdos'])} cerdos</b>", showarrow=True,
                           arrowhead=0, arrowwidth=1, arrowcolor=ACENTO, font=dict(size=11, color=ACENTO),
                           bgcolor="rgba(255,255,255,0.75)", borderpad=1)

    # nombres de reservas (en el mapa, no en la leyenda)
    expuestas = set(res.nlargest(5, "cerdos_entorno")["nombre"])
    for _, r in res.iterrows():
        if r["nombre"] not in POS_ANP:
            continue
        p = r.geometry.representative_point()
        tx, ty = POS_ANP[r["nombre"]]
        lejos = math.hypot(tx - p.x, ty - p.y) > 0.22
        fig.add_annotation(x=p.x if lejos else tx, y=p.y if lejos else ty, ax=tx, ay=ty, axref="x", ayref="y",
                           xref="x", yref="y", showarrow=lejos, arrowhead=0, arrowwidth=0.8, arrowcolor=ANP_BORDE,
                           text=f"<b><i>{r['nombre']}</i></b>", bgcolor="rgba(255,255,255,0.6)",
                           font=dict(size=12 if r["nombre"] in expuestas else 10.5,
                                     color="#0D3B12" if r["nombre"] in expuestas else "#1E5B23"))

    # mares, estados y ciudades
    for t, x, y, tam, color, estilo in [("GOLFO DE MÉXICO", -91.2, 21.25, 15, AGUA, "i"),
                                        ("MAR CARIBE", -86.95, 19.3, 15, AGUA, "i"),
                                        ("YUCATÁN", -88.55, 21.35, 17, "#7C8892", "b"),
                                        ("CAMPECHE", -90.75, 18.95, 17, "#7C8892", "b"),
                                        ("QUINTANA<br>ROO", -88.45, 19.55, 17, "#7C8892", "b")]:
        fig.add_annotation(x=x, y=y, xref="x", yref="y", text=f"<{estilo}>{t}</{estilo}>", showarrow=False,
                           font=dict(size=tam, color=color))
    fig.add_trace(go.Scatter(x=[c[1] for c in CIUDADES], y=[c[2] for c in CIUDADES], mode="markers+text",
                             text=[f"<b>{c[0]}</b>" for c in CIUDADES], textposition="top center",
                             textfont=dict(size=12, color=TEXTO), hoverinfo="skip", showlegend=False,
                             marker=dict(size=8, color=TEXTO, line=dict(color="white", width=1.5))), row=1, col=1)

    lon0, lon1, lat0, lat1 = CAJA
    fig.update_xaxes(visible=False, range=[lon0, lon1], row=1, col=1)
    fig.update_yaxes(visible=False, range=[lat0, lat1], scaleanchor="x", scaleratio=1 / math.cos(math.radians(20)),
                     row=1, col=1)

    # barras: reservas más expuestas
    top = res.nlargest(5, "cerdos_entorno").iloc[::-1]
    fig.add_trace(go.Bar(
        x=top["cerdos_entorno"], y=[f"<b><i>{n}</i></b>" for n in top["nombre"]], orientation="h",
        marker_color=ACENTO, text=[f"<b>{_miles(v)}</b>" for v in top["cerdos_entorno"]], textposition="outside",
        cliponaxis=False, showlegend=False, width=0.6,
        customdata=list(zip(top["municipios_entorno"], top["municipio_top"], top["cerdos_municipio_top"])),
        hovertemplate="%{x:,} cerdos en %{customdata[0]} municipios<br>El que más: %{customdata[1]} "
                      "(%{customdata[2]:,})<extra></extra>"), row=1, col=2)
    fig.update_xaxes(visible=False, range=[0, top["cerdos_entorno"].max() * 1.35], row=1, col=2)
    fig.update_yaxes(tickfont=dict(size=12.5, color=TEXTO), showline=True, linecolor="#9AA3AB", row=1, col=2)
    fig.layout.xaxis2.domain = [0.80, 0.99]
    fig.layout.yaxis2.domain = [0.0, 0.36]
    fig.update_layout({"plot_bgcolor": MAR})
    fig.add_shape(type="rect", xref="x2 domain", yref="y2 domain", x0=0, x1=1, y0=0, y1=1, fillcolor="white",
                  line=dict(width=0), layer="below")
    fig.add_annotation(xref="paper", yref="paper", x=0.775, y=0.44, xanchor="left", yanchor="bottom", showarrow=False,
                       align="left", text="<b>RESERVAS MÁS EXPUESTAS</b><br><span style='font-size:11px;color:"
                                          f"{SUAVE}'>Cerdos en los municipios a menos de 10 km de la reserva</span>",
                       font=dict(size=14, color=TEXTO))
    return fig
