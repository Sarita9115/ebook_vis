"""Turismo y derrama económica

viz_id: 4.turismo_derrama

Tabla de oro (`datos`): tabla larga con una columna `serie`:
  derrama_1t            derrama del primer trimestre por año, millones de pesos (2020-2026)
  gasto_1t              gasto promedio diario del primer trimestre, pesos
  derrama_nacional      derrama trimestral de turistas nacionales, millones de pesos (1T 2025-1T 2026)
  derrama_internacional derrama trimestral de turistas internacionales, millones de pesos
  pct_internacional     % de turistas-noche internacionales por trimestre
Columnas: serie, periodo, valor, unidad, y los metadatos.

Fuente primaria: SEFOTUR, boletín de derrama económica 1T 2026 (serie 1T 2020-2026).
Secundarias: SEFOTUR, boletines 4T 2025 y trimestral nacional/internacional; llegada de turistas y ocupación.
"""
import sys
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import estilo_equipo4 as e  # noqa: E402

TITULO = "Turismo y derrama económica"
PANELES = ["Derrama del primer trimestre (millones de pesos)", "Gasto promedio diario del primer trimestre (pesos)",
           "Derrama trimestral por origen del turista (millones de pesos)", "Turistas-noche internacionales (%)"]


def figura(datos, paso: int | None = None) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro.

    paso (1-4) resalta un panel para la lectura guiada; None muestra los cuatro por igual.
    """
    fig = make_subplots(rows=2, cols=2, subplot_titles=PANELES, vertical_spacing=0.17, horizontal_spacing=0.1)
    e.base(fig, TITULO, alto=760)
    e.titulos_izquierda(fig, 4)
    if datos is None or len(datos) == 0:
        return fig
    op = {k: e.opacidad(paso is None or paso == k) for k in range(1, 5)}
    s = {n: g.reset_index(drop=True) for n, g in datos.groupby("serie")}

    # 1 · Derrama 1T por año
    d = s["derrama_1t"]
    fig.add_trace(go.Bar(x=d.periodo, y=d.valor, marker=dict(color=e.AGUA, cornerradius=4), width=0.62,
                         opacity=op[1], hovertemplate="<b>1T %{x}</b><br>%{y:,.0f} millones de pesos<extra></extra>"),
                  row=1, col=1)
    ini, fin = d.iloc[0], d.iloc[-1]
    k_piso = int(d.valor.idxmin())
    piso = d.loc[k_piso]
    # En ejes de categoría las anotaciones van por posición: un año como "2021" se leería como índice.
    fig.add_annotation(x=k_piso, y=piso.valor, xref="x", yref="y", yshift=12, showarrow=False,
                       text="pandemia", opacity=op[1], font=dict(family=e.LETRA, size=11.5, color=e.TINTA_3))
    fig.add_annotation(x=len(d) - 1, y=fin.valor, xref="x", yref="y", ax=-120, ay=-8, showarrow=True,
                       arrowhead=0, arrowwidth=1, arrowcolor=e.TINTA_3, xanchor="right", opacity=op[1],
                       text=f"<b>{fin.valor / ini.valor:.1f}×</b> la derrama<br>de 1T {ini.periodo}",
                       font=dict(family=e.LETRA, size=12, color=e.TINTA))

    # 2 · Gasto diario 1T
    g = s["gasto_1t"]
    fig.add_trace(go.Scatter(x=g.periodo, y=g.valor, mode="lines+markers", opacity=op[2],
                             line=dict(color=e.TINTA_2, width=2),
                             marker=dict(size=8, color=e.TINTA_2, line=dict(color="white", width=2)),
                             hovertemplate="<b>1T %{x}</b><br>$%{y:,.0f} por turista al día<extra></extra>"),
                  row=1, col=2)
    for i in (0, len(g) - 1):
        fig.add_annotation(x=i, y=g.valor[i], xref="x2", yref="y2", showarrow=False, yshift=14,
                           text=f"${g.valor[i]:,.0f}", opacity=op[2], font=dict(family=e.LETRA, size=12, color=e.TINTA))

    # 3 · Derrama trimestral apilada: nacionales + internacionales (2 px de papel entre segmentos)
    n, i_ = s["derrama_nacional"], s["derrama_internacional"]
    for serie, color, nombre in [(n, e.AZUL, "Nacionales"), (i_, e.NARANJA, "Internacionales")]:
        fig.add_trace(go.Bar(x=serie.periodo, y=serie.valor, name=nombre, opacity=op[3], width=0.62,
                             marker=dict(color=color, line=dict(color=e.PAPEL, width=2)),
                             hovertemplate=f"<b>%{{x}}</b><br>{nombre}: %{{y:,.0f}} millones de pesos<extra></extra>"),
                      row=2, col=1)
    ultimo = len(n) - 1
    fig.add_annotation(x=ultimo, y=n.valor.iloc[-1] / 2, xref="x3", yref="y3", text="Nacionales", showarrow=False,
                       opacity=op[3], font=dict(family=e.LETRA, size=12, color="white"))
    fig.add_annotation(x=ultimo, y=n.valor.iloc[-1] + i_.valor.iloc[-1] / 2, xref="x3", yref="y3",
                       text="Internac.", showarrow=False, opacity=op[3],
                       font=dict(family=e.LETRA, size=12, color="white"))

    # 4 · % turistas-noche internacionales
    p = s["pct_internacional"]
    fig.add_trace(go.Scatter(x=p.periodo, y=p.valor, mode="lines+markers", opacity=op[4],
                             line=dict(color=e.NARANJA, width=2),
                             marker=dict(size=8, color=e.NARANJA, line=dict(color="white", width=2)),
                             hovertemplate="<b>%{x}</b><br>%{y:.1f} % internacionales<extra></extra>"),
                  row=2, col=2)
    k = p.valor.idxmax()
    fig.add_annotation(x=int(k), y=p.valor[k], xref="x4", yref="y4", showarrow=False, yshift=14,
                       text=f"{p.valor[k]:.1f} %", opacity=op[4], font=dict(family=e.LETRA, size=12, color=e.TINTA))

    fig.update_layout(barmode="stack", bargap=0.3, margin=dict(l=50, r=40, t=100, b=50))
    fig.update_xaxes(type="category")
    fig.update_yaxes(rangemode="tozero")
    fig.update_yaxes(rangemode="normal", tickprefix="$", row=1, col=2)
    fig.update_yaxes(range=[0, 40], ticksuffix=" %", row=2, col=2)
    return fig
