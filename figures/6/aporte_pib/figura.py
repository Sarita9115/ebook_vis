"""Aporte del sector empresarial al PIB estatal y regional

viz_id: 6.aporte_pib

El sector empresarial se representa con el sector 71 del SCIAN (servicios de esparcimiento culturales y deportivos).

Tabla de oro (`datos`): una fila por entidad, actividad y año (PIBE, base 2018, millones de pesos constantes).
  entidad            Yucatán, Campeche, Quintana Roo o Nacional
  actividad_codigo   "71" (sector de esparcimiento) o "VAB" (valor agregado bruto total, solo para calcular el porcentaje)
  anio               2003 a 2024
  constantes         millones de pesos a precios de 2018

Fuente primaria: PIB por entidad federativa (PIBE), INEGI.
Fuente secundaria: DENUE (INEGI), solo como contexto en la lectura (unidades económicas por entidad).
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

TITULO = "Aporte del sector empresarial al PIB estatal y regional"

TERRACOTA, MONTE, CENOTE, GRIS = "#d9622b", "#1f8a70", "#2b7a9b", "#8a8a80"
CALIZA, TEXTO, TEXTO_2, REJILLA = "#f7f4ec", "#1d2a22", "#4f5b52", "#e4dfd2"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"
COLOR = {"Yucatán": TERRACOTA, "Campeche": CENOTE, "Quintana Roo": MONTE, "Nacional": GRIS}
ORDEN = ("Nacional", "Campeche", "Quintana Roo", "Yucatán")
BASE = 2003


def _n(x):
    return f"{x:,.0f}".replace(",", " ")


def _separar(valores, minimo):
    """Empuja etiquetas que se encimarían, sin cambiar su orden."""
    orden = sorted(valores, key=valores.get)
    pos = {k: valores[k] for k in orden}
    for _ in range(40):
        movido = False
        for a, b in zip(orden, orden[1:]):
            if pos[b] - pos[a] < minimo:
                m = (pos[a] + pos[b]) / 2
                pos[a], pos[b] = m - minimo / 2, m + minimo / 2
                movido = True
        if not movido:
            break
    return pos


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.24,
                        subplot_titles=("Crecimiento del sector (índice 2003 = 100)", "Aporte al valor agregado bruto (%)"))
    fig.update_layout(
        title=dict(text=TITULO, x=0, xanchor="left", y=0.97, yanchor="top", font=dict(size=22, color=TEXTO), pad=dict(l=10)),
        separators=". ", width=1400, height=680, paper_bgcolor=CALIZA, plot_bgcolor=CALIZA, showlegend=False,
        font=dict(family=LETRA, size=14, color=TEXTO), margin=dict(l=60, r=170, t=120, b=80),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13), bordercolor=REJILLA))
    fig.update_annotations(font=dict(size=14, color=TEXTO_2))
    if datos is None or len(datos) == 0:
        return fig
    d = datos.copy()
    fin = int(d.anio.max())

    def serie(ent, cod):
        s = d[(d.entidad == ent) & (d.actividad_codigo == cod)].sort_values("anio").set_index("anio").constantes
        return s if len(s) else None

    idx, pct, finales_i, finales_p, mon = {}, {}, {}, {}, {}
    for ent in ORDEN:
        s71, vab = serie(ent, "71"), serie(ent, "VAB")
        if s71 is None or BASE not in s71.index:
            continue
        idx[ent] = s71 / s71[BASE] * 100
        finales_i[ent] = float(idx[ent][fin])
        mon[ent] = float(s71[fin])
        if vab is not None:
            pct[ent] = (s71 / vab * 100).dropna()
            finales_p[ent] = float(pct[ent][fin])

    for col, (ser, nombre) in enumerate(((idx, "índice"), (pct, "porcentaje")), start=1):
        for ent in ORDEN:
            if ent not in ser:
                continue
            s = ser[ent]
            yuc = ent == "Yucatán"
            fmt = "%{y:.0f}" if col == 1 else "%{y:.2f}%"
            fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", showlegend=False,
                                     line=dict(color=COLOR[ent], width=4 if yuc else 2.5),
                                     hovertemplate=f"<b>{ent}</b>, sector 71<br>%{{x}}: {fmt}<extra></extra>"), row=1, col=col)
        fig.update_xaxes(range=[BASE - 0.5, fin + 0.5], tick0=BASE, dtick=7, showgrid=False, linecolor=TEXTO_2,
                         tickfont=dict(size=12, color=TEXTO_2), row=1, col=col)
        fig.update_yaxes(gridcolor=REJILLA, zeroline=False, tickfont=dict(size=12, color=TEXTO_2), row=1, col=col)
    fig.add_hline(y=100, line=dict(color=TEXTO_2, width=1), row=1, col=1)
    fig.update_yaxes(ticksuffix="%", row=1, col=2)

    # etiquetas al final de cada línea
    if finales_i:
        rango = max(finales_i.values()) - min(min(finales_i.values()), 100)
        for ent, y in _separar(finales_i, max(rango, 20) * 0.11).items():
            fig.add_annotation(x=fin, y=y, xref="x", yref="y", showarrow=False, xanchor="left", xshift=8, align="left",
                               text=f"<b>{ent}</b> {finales_i[ent]:.0f}<br>{_n(mon[ent])} millones", bgcolor="rgba(247,244,236,0.85)",
                               font=dict(size=12, color=COLOR[ent] if ent != "Nacional" else TEXTO_2))
    if finales_p:
        rango = max(finales_p.values()) - min(finales_p.values())
        for ent, y in _separar(finales_p, max(rango, 0.05) * 0.14).items():
            fig.add_annotation(x=fin, y=y, xref="x2", yref="y2", showarrow=False, xanchor="left", xshift=8,
                               text=f"<b>{ent}</b> {finales_p[ent]:.2f}%", bgcolor="rgba(247,244,236,0.85)",
                               font=dict(size=12, color=COLOR[ent] if ent != "Nacional" else TEXTO_2))
    return fig
