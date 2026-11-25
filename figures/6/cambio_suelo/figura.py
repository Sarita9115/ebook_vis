"""Cambio de uso del suelo y expansión urbana en Yucatán y la zona metropolitana de Mérida

viz_id: 6.cambio_suelo

Recibe la tabla de oro (GeoDataFrame en EPSG:4326, formato largo con columna
`capa`) y arma tres paneles:

1. s6_transiciones: Sankey de la cobertura de la serie VI (2014) que pasó a
   urbano en la serie VII (2018), separada en ZM Mérida–Progreso y resto del estado.
2. s6_mapa_cambio: Yucatán con el suelo urbano previo y el nuevo.
3. Acercamiento a la ZM Mérida–Progreso con las mismas capas.

Los mapas se dibujan como polígonos en ejes cartesianos (lon/lat con la escala
corregida por la latitud), así no dependen de teselas externas al exportar.
"""

import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots

TITULO = "Cambio de uso del suelo y expansión urbana en Yucatán y la zona metropolitana de Mérida"
URBANO = "Urbano"
AMBITO_ZM = "ZM Mérida–Progreso"
AMBITO_RESTO = "Resto de Yucatán"
AMBITO_ESTADO = "Yucatán"

# Paleta del ebook: verde de monte, caliza, agua de cenote y terracota.
MONTE = "#2F5D3A"
MONTE_CLARO = "#86A56C"
CALIZA_FONDO = "#EFE9DA"
CALIZA = "#CBBF9F"
CALIZA_OSCURA = "#A08F66"
PIEDRA = "#9A938A"
CENOTE = "#1F7A80"
TERRACOTA = "#C2562F"
TERRACOTA_CLARA = "#E39A74"
TINTA = "#2B2A26"
TINTA_SUAVE = "#6B6457"
FONDO = "#FFFFFF"

COLOR_ORIGEN = {
    "Selva y vegetación secundaria": MONTE,
    "Agricultura": CALIZA_OSCURA,
    "Pastizal": MONTE_CLARO,
    "Otras coberturas": PIEDRA,
}
COLOR_AMBITO = {AMBITO_ZM: TERRACOTA, AMBITO_RESTO: TERRACOTA_CLARA}
# Orígenes con menos de esta área se juntan en "Otras coberturas".
MIN_KM2_ORIGEN = 2.0


def _rgba(hex_color: str, alfa: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alfa})"


def _anillos(geometrias):
    """Separa exteriores e interiores de (Multi)Polygon en listas lon/lat con None."""
    ext_x, ext_y, int_x, int_y = [], [], [], []
    for geom in geometrias:
        if geom is None or geom.is_empty:
            continue
        poligonos = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for p in poligonos:
            x, y = p.exterior.coords.xy
            ext_x += list(x) + [None]
            ext_y += list(y) + [None]
            for anillo in p.interiors:
                x, y = anillo.coords.xy
                int_x += list(x) + [None]
                int_y += list(y) + [None]
    return ext_x, ext_y, int_x, int_y


def _poligonos(fig, geometrias, relleno, fondo, linea, ancho, nombre, mostrar, fila, grupo):
    ext_x, ext_y, int_x, int_y = _anillos(geometrias)
    fig.add_trace(
        go.Scatter(
            x=ext_x, y=ext_y, mode="lines", fill="toself", fillcolor=relleno,
            line=dict(color=linea, width=ancho), name=nombre, legendgroup=grupo,
            showlegend=mostrar, hoverinfo="skip",
        ),
        row=fila, col=2,
    )
    if int_x and fondo:
        fig.add_trace(
            go.Scatter(
                x=int_x, y=int_y, mode="lines", fill="toself", fillcolor=fondo,
                line=dict(width=0), showlegend=False, hoverinfo="skip",
            ),
            row=fila, col=2,
        )


def _limites_continentales(geometrias):
    """Recuadro del polígono más grande: deja fuera arrecifes y cayos del encuadre."""
    partes = []
    for geom in geometrias:
        if geom is None or geom.is_empty:
            continue
        partes += list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    return max(partes, key=lambda g: g.area).bounds


def _apilar(valores, total, alto_util=0.78, hueco_min=0.05, alto_rotulo=0.11):
    """Centros verticales (0 arriba) de nodos apilados, con hueco para sus rótulos."""
    alturas = [alto_util * v / total for v in valores]
    centros, cursor = [], 0.0
    for i, h in enumerate(alturas):
        if i:
            cursor += max(hueco_min, alto_rotulo - (alturas[i - 1] + h) / 2)
        centros.append(cursor + h / 2)
        cursor += h
    desfase = (1 - cursor) / 2
    return [c + desfase for c in centros]


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    serie_origen = datos["serie_origen"].dropna().iloc[0]
    serie_destino = datos["serie_destino"].dropna().iloc[0]
    anio_o = serie_origen.split("(")[-1].rstrip(")")
    anio_d = serie_destino.split("(")[-1].rstrip(")")

    t = datos[datos["capa"] == "transicion"]
    ganado = t[(t["origen"] != URBANO) & (t["destino"] == URBANO)].copy()
    urb_vi = t[t["origen"] == URBANO].groupby("ambito")["km2"].sum()
    urb_vii = t[t["destino"] == URBANO].groupby("ambito")["km2"].sum()
    neto = (urb_vii - urb_vi).to_dict()
    neto_estado = urb_vii.sum() - urb_vi.sum()
    bruto = ganado.groupby("ambito")["km2"].sum().to_dict()
    bruto_estado = ganado["km2"].sum()

    por_origen = ganado.groupby("origen")["km2"].sum()
    menores = por_origen[por_origen < MIN_KM2_ORIGEN].index
    ganado["origen_fig"] = ganado["origen"].where(~ganado["origen"].isin(menores), "Otras coberturas")
    detalle_otras = ", ".join(sorted(m.lower() for m in menores))

    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[[{"type": "domain", "rowspan": 2}, {"type": "xy"}], [None, {"type": "xy"}]],
        column_widths=[0.52, 0.48],
        row_heights=[0.5, 0.5],
        horizontal_spacing=0.04,
        vertical_spacing=0.1,
        subplot_titles=(
            f"De dónde salieron los {bruto_estado:,.0f} km² que se volvieron urbanos ({anio_o} → {anio_d})",
            f"Yucatán: +{neto_estado:,.0f} km² urbanos netos",
            f"{AMBITO_ZM}: +{neto.get(AMBITO_ZM, 0):,.0f} km² netos",
        ),
    )

    # 1. Sankey: cobertura previa -> ámbito donde se urbanizó
    origen_km2 = ganado.groupby("origen_fig")["km2"].sum()
    origenes = [o for o in COLOR_ORIGEN if o in origen_km2.index]
    origenes += sorted(set(origen_km2.index) - set(origenes))
    ambitos = [a for a in (AMBITO_ZM, AMBITO_RESTO) if a in bruto]
    flujos = ganado.groupby(["origen_fig", "ambito"])["km2"].sum()

    centros_o = _apilar([origen_km2[o] for o in origenes], bruto_estado)
    centros_a = _apilar([bruto[a] for a in ambitos], bruto_estado, hueco_min=0.08)
    x_izq, x_der = 0.36, 0.64
    n_o = len(origenes)

    fig.add_trace(
        go.Sankey(
            arrangement="fixed",
            valueformat=",.1f",
            valuesuffix=" km²",
            node=dict(
                label=[""] * (n_o + len(ambitos)),
                x=[x_izq] * n_o + [x_der] * len(ambitos),
                y=centros_o + centros_a,
                color=[COLOR_ORIGEN.get(o, PIEDRA) for o in origenes]
                + [COLOR_AMBITO[a] for a in ambitos],
                customdata=[
                    f"{o} ({detalle_otras})" if o == "Otras coberturas" else o for o in origenes
                ] + [f"{a}: nuevo urbano" for a in ambitos],
                hovertemplate="%{customdata}<br>%{value}<extra></extra>",
                pad=12,
                thickness=18,
                line=dict(color=FONDO, width=1),
            ),
            link=dict(
                source=[origenes.index(o) for o, _ in flujos.index],
                target=[n_o + ambitos.index(a) for _, a in flujos.index],
                value=list(flujos.values),
                color=[_rgba(COLOR_ORIGEN.get(o, PIEDRA), 0.45) for o, _ in flujos.index],
                hovertemplate="%{source.customdata} → %{target.customdata}"
                "<br>%{value}<extra></extra>",
            ),
        ),
        row=1,
        col=1,
    )
    dominio = fig.data[0].domain
    ancho_dom = dominio.x[1] - dominio.x[0]
    alto_dom = dominio.y[1] - dominio.y[0]

    def _rotulo(texto, x_nodo, centro, lado):
        fig.add_annotation(
            text=texto, xref="paper", yref="paper",
            x=dominio.x[0] + ancho_dom * (x_nodo + (-0.03 if lado == "izq" else 0.07)),
            y=dominio.y[1] - centro * alto_dom,
            xanchor="right" if lado == "izq" else "left", yanchor="middle",
            align="right" if lado == "izq" else "left", showarrow=False,
            font=dict(size=12, color=TINTA),
        )

    for o, c in zip(origenes, centros_o):
        v = origen_km2[o]
        _rotulo(f"<b>{o}</b><br>{v:,.1f} km² · {100 * v / bruto_estado:.0f} %", x_izq, c, "izq")
    for a, c in zip(ambitos, centros_a):
        _rotulo(f"<b>{a}</b><br>{bruto[a]:,.1f} km² nuevos", x_der, c, "der")

    # 2 y 3. Mapas
    capas = {c: datos[datos["capa"] == c] for c in ("contorno", "urbano_previo", "urbano_nuevo")}
    estado = capas["contorno"][capas["contorno"]["ambito"] == AMBITO_ESTADO].geometry
    zm = capas["contorno"][capas["contorno"]["ambito"] == AMBITO_ZM].geometry

    for fila in (1, 2):
        primera = fila == 1
        _poligonos(fig, estado, CALIZA_FONDO, None, CALIZA, 0.8, AMBITO_ESTADO, False, fila, "estado")
        _poligonos(fig, capas["urbano_previo"].geometry, CALIZA, CALIZA_FONDO, CALIZA, 0.4,
                   f"Urbano en {anio_o}", primera, fila, "previo")
        _poligonos(fig, capas["urbano_nuevo"].geometry, TERRACOTA, None, TERRACOTA, 0.6,
                   f"Nuevo urbano {anio_o}–{anio_d}", primera, fila, "nuevo")
        ext_x, ext_y, _, _ = _anillos(zm)
        fig.add_trace(
            go.Scatter(
                x=ext_x, y=ext_y, mode="lines", line=dict(color=CENOTE, width=1.6),
                name=AMBITO_ZM, legendgroup="zm", showlegend=primera, hoverinfo="skip",
            ),
            row=fila, col=2,
        )

    def _ajustar(fila, limites, margen):
        x0, y0, x1, y1 = limites
        lat = (y0 + y1) / 2
        fig.update_xaxes(row=fila, col=2, range=[x0 - margen, x1 + margen], visible=False,
                         scaleanchor=f"y{'' if fila == 1 else fila}",
                         scaleratio=math.cos(math.radians(lat)), constrain="domain")
        fig.update_yaxes(row=fila, col=2, range=[y0 - margen, y1 + margen], visible=False,
                         constrain="domain")

    _ajustar(1, _limites_continentales(estado), 0.04)
    _ajustar(2, _limites_continentales(zm), 0.015)

    # Títulos de panel alineados a la izquierda de cada panel.
    for anotacion, x in zip(fig.layout.annotations, (0, fig.layout.xaxis.domain[0],
                                                     fig.layout.xaxis2.domain[0])):
        anotacion.update(x=x, xanchor="left", font=dict(size=13, color=TINTA))

    fig.update_layout(
        title=dict(text=TITULO, x=0, xanchor="left", font=dict(size=17, color=TINTA)),
        font=dict(family="Open Sans, Verdana, Arial, sans-serif", color=TINTA),
        paper_bgcolor=FONDO,
        plot_bgcolor=FONDO,
        legend=dict(
            orientation="h", x=1, xanchor="right", y=-0.02, yanchor="top",
            font=dict(size=11, color=TINTA), bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=20, r=20, t=90, b=50),
        hoverlabel=dict(bgcolor=FONDO, font=dict(color=TINTA)),
        height=760,
    )
    return fig
