"""IED hacia Yucatán por año, ranking y origen (2018-2025)

viz_id: 4.ied_ranking_origen

Tabla de oro (`datos`): tabla larga con una columna `serie`:
  anual         IED de Yucatán por año (categoria = año, valor en millones de dólares, lugar entre 32 entidades)
  participacion Yucatán / total nacional por año, en %
  ranking_2025  IED 2025 de cada entidad (categoria = entidad, valor, lugar)
  origen        acumulado 2018-1T 2026 de los principales países (ficha SE)
Cifras originales publicadas al 4T de cada año (no las revisiones posteriores).

Cuatro paneles: IED anual, participación nacional, las 8 entidades que más reciben más Yucatán, y origen.

Fuente primaria: Secretaría de Economía, estadística oficial de la IED y reportes CNIE.
Secundarias: SETY/SEFOET, Yucatán en Cifras; ficha estatal SE 1T 2026 (Portal de Datos Abiertos).
"""
import sys
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import estilo_equipo4 as e  # noqa: E402

TITULO = "IED hacia Yucatán por año, ranking y origen (2018-2025)"
PANELES = ["IED en Yucatán por año (millones de dólares)", "Participación en la IED nacional (%)",
           "IED 2025 por entidad: las 8 primeras y Yucatán (mdd)", "Origen acumulado 2018–1T 2026 (mdd)"]


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

    # En ejes de categoría las anotaciones van por posición: un año como "2022" se leería como índice.
    # 1 · IED anual
    a = s["anual"]
    pico = a.valor.idxmax()
    fig.add_trace(go.Bar(x=a.categoria, y=a.valor, marker=dict(color=e.AZUL, cornerradius=4), opacity=op[1],
                         customdata=a.lugar, width=0.62,
                         hovertemplate="<b>%{x}</b><br>%{y:,.1f} mdd<br>Lugar %{customdata:.0f} de 32<extra></extra>"),
                  row=1, col=1)
    fig.add_annotation(x=pico, y=a.valor[pico], xref="x", yref="y", ax=-110, ay=45, showarrow=True,
                       arrowhead=0, arrowwidth=1, arrowcolor=e.TINTA_3, align="right", opacity=op[1],
                       text=f"<b>{a.categoria[pico]}</b>: {a.valor[pico]:,.0f} mdd,<br>"
                            f"{a.valor[pico] / a.drop(pico).valor.mean():.1f} veces<br>el promedio de los demás años",
                       font=dict(family=e.LETRA, size=12, color=e.TINTA))

    # 2 · Participación nacional
    p = s["participacion"]
    fig.add_trace(go.Scatter(x=p.categoria, y=p.valor, mode="lines+markers", opacity=op[2],
                             line=dict(color=e.NARANJA, width=2), marker=dict(size=8, color=e.NARANJA,
                                                                             line=dict(color="white", width=2)),
                             hovertemplate="<b>%{x}</b><br>%{y:.2f} % de la IED nacional<extra></extra>"),
                  row=1, col=2)
    for i in (p.valor.idxmax(), len(p) - 1):
        fig.add_annotation(x=i, y=p.valor[i], xref="x2", yref="y2", showarrow=False, yshift=14,
                           text=f"{p.valor[i]:.2f} %", opacity=op[2],
                           font=dict(family=e.LETRA, size=12, color=e.TINTA))

    # 3 · Ranking 2025: las 8 primeras + Yucatán resaltado
    r = s["ranking_2025"].sort_values("lugar")
    r = r[(r.lugar <= 8) | (r.categoria == "Yucatán")].iloc[::-1]
    yuc = r.categoria.eq("Yucatán")
    fig.add_trace(go.Bar(y=[f"{c}  " for c in r.categoria], x=r.valor, orientation="h", opacity=op[3],
                         marker=dict(color=[e.AZUL if y else e.GRIS for y in yuc], cornerradius=3),
                         customdata=r.lugar,
                         hovertemplate="<b>%{y}</b><br>%{x:,.1f} mdd · lugar %{customdata:.0f}<extra></extra>"),
                  row=2, col=1)
    fy = r[yuc].iloc[0]
    fig.add_annotation(x=fy.valor, y="Yucatán  ", xref="x3", yref="y3", ax=120, ay=-6, showarrow=True,
                       arrowhead=0, arrowwidth=1, arrowcolor=e.TINTA_3, xanchor="left", opacity=op[3],
                       text=f"Yucatán: {fy.valor:,.1f} mdd, lugar {fy.lugar:.0f} de 32",
                       font=dict(family=e.LETRA, size=12, color=e.TINTA))

    # 4 · Origen acumulado
    o = s["origen"].sort_values("valor", ascending=False)
    fig.add_trace(go.Bar(x=o.categoria, y=o.valor, marker=dict(color=e.AGUA, cornerradius=4), width=0.5,
                         opacity=op[4], text=[f"{v:,.0f}" for v in o.valor], textposition="outside",
                         textfont=dict(family=e.LETRA, size=12, color=e.TINTA), cliponaxis=False,
                         hovertemplate="<b>%{x}</b><br>%{y:,.0f} mdd acumulados<extra></extra>"),
                  row=2, col=2)

    fig.update_yaxes(rangemode="tozero")
    fig.update_yaxes(ticksuffix=" %", row=1, col=2)
    fig.update_yaxes(showgrid=False, row=2, col=1)
    fig.update_xaxes(showgrid=True, gridcolor=e.REJILLA, row=2, col=1)
    fig.update_xaxes(type="category")
    fig.update_xaxes(type="linear", row=2, col=1)
    fig.update_layout(bargap=0.3, margin=dict(l=40, r=40, t=100, b=50))
    return fig
