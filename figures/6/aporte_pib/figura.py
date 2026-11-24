"""Aporte del sector empresarial al PIB estatal y regional

viz_id: 6.aporte_pib

Tabla de oro (`datos`): una fila por entidad, actividad y año (PIBE, base 2018, millones de pesos constantes).
  entidad            Yucatán, Campeche, Quintana Roo o Nacional
  actividad_codigo   "VAB" (valor agregado bruto total) o "71" (servicios de esparcimiento culturales y deportivos)
  anio               2003 a 2024
  constantes         millones de pesos a precios de 2018

Fuente primaria: PIB por entidad federativa (PIBE), INEGI.
Fuente secundaria: DENUE (INEGI), solo como contexto en la lectura (unidades económicas por entidad).
"""

import plotly.graph_objects as go

TITULO = "Aporte del sector empresarial al PIB estatal y regional"

TERRACOTA, MONTE, CENOTE, GRIS = "#d9622b", "#1f8a70", "#2b7a9b", "#8a8a80"
CALIZA, TEXTO, TEXTO_2, REJILLA = "#f7f4ec", "#1d2a22", "#4f5b52", "#e4dfd2"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"

COLOR = {"Yucatán": TERRACOTA, "Campeche": CENOTE, "Quintana Roo": MONTE, "Nacional": GRIS}
BASE = 2003


def _separar(valores, minimo):
    """Empuja etiquetas que se encimarían, sin cambiar su orden. valores: {nombre: y}."""
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
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=TITULO, x=0, xanchor="left", y=0.97, yanchor="top", font=dict(size=22, color=TEXTO), pad=dict(l=10)),
        separators=". ", width=1100, height=680, paper_bgcolor=CALIZA, plot_bgcolor=CALIZA, showlegend=False,
        font=dict(family=LETRA, size=14, color=TEXTO), margin=dict(l=70, r=250, t=110, b=70),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13), bordercolor=REJILLA))
    if datos is None or len(datos) == 0:
        return fig
    d = datos.copy()
    fin = int(d.anio.max())

    def indice(ent, cod):
        s = d[(d.entidad == ent) & (d.actividad_codigo == cod)].sort_values("anio").set_index("anio").constantes
        if BASE not in s.index or s.empty:
            return None
        return s / s[BASE] * 100

    series, finales = {}, {}
    for ent in ("Nacional", "Campeche", "Quintana Roo", "Yucatán"):
        s = indice(ent, "VAB")
        if s is None:
            continue
        series[ent] = s
        finales[ent] = float(s[fin])
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, mode="lines", name=ent, showlegend=False,
            line=dict(color=COLOR[ent], width=4 if ent == "Yucatán" else 2.5, dash="solid"),
            hovertemplate=f"<b>{ent}</b>, actividad total<br>%{{x}}: %{{y:.0f}} (2003 = 100)<extra></extra>"))

    s71 = indice("Yucatán", "71")
    if s71 is not None:
        series["Yucatán, esparcimiento"] = s71
        finales["Yucatán, esparcimiento"] = float(s71[fin])
        fig.add_trace(go.Scatter(
            x=s71.index, y=s71.values, mode="lines", name="Esparcimiento", showlegend=False,
            line=dict(color=TERRACOTA, width=3, dash="dot"),
            hovertemplate="<b>Yucatán, esparcimiento (sector 71)</b><br>%{x}: %{y:.0f} (2003 = 100)<extra></extra>"))

    if not series:
        return fig
    ymax = max(max(s.max() for s in series.values()), 100)
    ymin = min(min(s.min() for s in series.values()), 100)
    paso = (ymax - ymin) * 0.075
    pos = _separar(finales, paso)
    nombres = {"Yucatán, esparcimiento": "Yucatán, esparcimiento<br>(sector 71)", "Nacional": "Nacional"}
    for k, y in pos.items():
        col = COLOR.get(k, TERRACOTA)
        fig.add_annotation(x=fin, y=y, xref="x", yref="y", showarrow=False, xanchor="left", xshift=10, align="left",
                           text=f"<b>{nombres.get(k, k)}</b>  {finales[k]:.0f}", font=dict(size=13, color=col if k != "Nacional" else TEXTO_2), bgcolor="rgba(247,244,236,0.85)")

    # referencia: 2020
    fig.add_vline(x=2020, line=dict(color=REJILLA, width=1.5, dash="dot"))
    fig.add_annotation(x=2020, y=1.0, xref="x", yref="paper", text="2020", showarrow=False, yanchor="bottom", font=dict(size=12, color=TEXTO_2))
    fig.add_hline(y=100, line=dict(color=TEXTO_2, width=1))

    fig.add_annotation(xref="paper", yref="paper", x=0, y=1.0, yshift=14, xanchor="left", yanchor="bottom", showarrow=False,
                       text=f"Valor agregado bruto en pesos constantes, índice {BASE} = 100", font=dict(size=14, color=TEXTO_2))
    fig.update_xaxes(range=[BASE - 0.5, fin + 0.5], tick0=BASE, dtick=3, showgrid=False, linecolor=TEXTO_2, tickfont=dict(size=12, color=TEXTO_2))
    fig.update_yaxes(range=[min(ymin, 100) * 0.9, ymax * 1.05], gridcolor=REJILLA, zeroline=False, tickfont=dict(size=12, color=TEXTO_2))
    return fig
