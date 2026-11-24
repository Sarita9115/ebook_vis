"""Atracción de capital, empleo y evolución de las unidades económicas en Yucatán

viz_id: 6.atraccion_capital

Tabla de oro (`datos`): una fila por entidad y año (solo años con los cuatro trimestres).
  entidad     Yucatán, Campeche o Quintana Roo
  anio        año de la cifra
  ied_mdd     inversión extranjera directa acumulada en el año, millones de dólares
  lugar       lugar de la entidad entre los 32 estados por IED acumulada en todo el periodo
  de_estados  número de estados comparados (32)

Fuente primaria: Secretaría de Economía, inversión extranjera directa por entidad federativa.
Fuente secundaria: DENUE (INEGI), solo como contexto en la lectura (unidades económicas por entidad).
El lugar nacional se calcula en la limpieza, con los 32 estados; en la tabla solo quedan las tres entidades de la península.
"""

import plotly.graph_objects as go

TITULO = "Atracción de capital, empleo y evolución de las unidades económicas en Yucatán"

TERRACOTA, MONTE, CENOTE = "#d9622b", "#1f8a70", "#2b7a9b"
CALIZA, TEXTO, TEXTO_2, REJILLA = "#f7f4ec", "#1d2a22", "#4f5b52", "#e4dfd2"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"
COLOR = {"Yucatán": TERRACOTA, "Campeche": CENOTE, "Quintana Roo": MONTE}


def _n(x):
    return f"{x:,.0f}".replace(",", " ")


def _separar(valores, minimo):
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
        font=dict(family=LETRA, size=14, color=TEXTO), margin=dict(l=80, r=270, t=110, b=70),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13), bordercolor=REJILLA))
    if datos is None or len(datos) == 0:
        return fig
    d = datos.copy().sort_values(["entidad", "anio"])
    fin = int(d.anio.max())

    finales, lugar = {}, {}
    for ent in ("Quintana Roo", "Campeche", "Yucatán"):
        s = d[d.entidad == ent]
        if s.empty:
            continue
        yuc = ent == "Yucatán"
        fig.add_trace(go.Scatter(
            x=s.anio, y=s.ied_mdd, mode="lines+markers", showlegend=False,
            line=dict(color=COLOR[ent], width=4 if yuc else 2.5),
            marker=dict(size=9 if yuc else 6, color=COLOR[ent], line=dict(color="white", width=1.5)),
            hovertemplate=f"<b>{ent}</b><br>%{{x}}: %{{y:,.0f}} millones de dólares<extra></extra>"))
        ult = s[s.anio == s.anio.max()].iloc[0]
        finales[ent] = float(ult.ied_mdd)
        lugar[ent] = (int(s.lugar.iloc[0]), int(s.de_estados.iloc[0]))

    yv = d.ied_mdd
    rango = float(yv.max() - min(yv.min(), 0)) or 1.0
    pos = _separar(finales, rango * 0.09)
    for ent, y in pos.items():
        l, de = lugar[ent]
        fig.add_annotation(x=fin, y=y, xref="x", yref="y", showarrow=False, xanchor="left", xshift=10, align="left",
                           text=f"<b>{ent}</b><br>lugar {l} de {de} estados", font=dict(size=13, color=COLOR[ent]), bgcolor="rgba(247,244,236,0.85)")

    # pico de Yucatán
    y = d[d.entidad == "Yucatán"]
    if not y.empty:
        p = y.loc[y.ied_mdd.idxmax()]
        fig.add_annotation(x=p.anio, y=p.ied_mdd, xref="x", yref="y", showarrow=False, yshift=18,
                           text=f"<b>{_n(p.ied_mdd)}</b> en {int(p.anio)}", font=dict(size=13, color=TERRACOTA))

    fig.add_annotation(xref="paper", yref="paper", x=0, y=1.0, yshift=14, xanchor="left", yanchor="bottom", showarrow=False,
                       text="Inversión extranjera directa por año, millones de dólares", font=dict(size=14, color=TEXTO_2))
    anios = sorted(d.anio.unique())
    fig.update_xaxes(tickmode="array", tickvals=anios, showgrid=False, linecolor=TEXTO_2, tickfont=dict(size=12, color=TEXTO_2),
                     range=[min(anios) - 0.4, fin + 0.4])
    fig.update_yaxes(gridcolor=REJILLA, zeroline=True, zerolinecolor=TEXTO_2, zerolinewidth=1, tickfont=dict(size=12, color=TEXTO_2))
    return fig
