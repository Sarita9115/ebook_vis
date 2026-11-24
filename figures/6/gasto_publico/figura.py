"""Gasto público estatal y fomento económico: hacia dónde va el presupuesto de Yucatán

viz_id: 6.gasto_publico

Recibe la tabla de oro (grano año × trimestre × finalidad × dependencia, con
`ejercido_mdp` en millones de pesos) y arma tres paneles:

1. Sankey del ejercido del último año: del total a las cuatro finalidades.
2. Dependencias que ejercen la finalidad Desarrollo económico ese año.
3. Desarrollo económico por trimestre, último año contra el anterior; la
   etiqueta de cada barra es su parte del gasto de ese trimestre.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

TITULO = "Gasto público estatal y fomento económico: hacia dónde va el presupuesto de Yucatán"
FINALIDAD_ECONOMICA = "Desarrollo económico"

# Paleta del ebook: verde de monte, caliza y agua de cenote.
MONTE = "#2F5D3A"
MONTE_CLARO = "#6E9A6B"
CALIZA = "#CBBF9F"
CALIZA_OSCURA = "#9C8F6E"
CENOTE = "#1F7A80"
TINTA = "#2B2A26"
TINTA_SUAVE = "#6B6457"
REJILLA = "#ECE6D8"
FONDO = "#FFFFFF"

ORDEN_FINALIDADES = [
    "Desarrollo social",
    "Otras no clasificadas",
    "Gobierno",
    "Desarrollo económico",
]
# Rótulo visible de cada finalidad (la tabla de oro guarda el nombre del CONAC).
ROTULO_FINALIDAD = {
    "Otras no clasificadas": "Municipios y deuda",
}
NOTA_FINALIDAD = {
    "Otras no clasificadas": "Otras no clasificadas: participaciones a municipios y deuda pública",
}
MAX_DEPENDENCIAS = 6


def _rgba(hex_color: str, alfa: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alfa})"


def _mdp(valor: float) -> str:
    return f"{valor:,.0f} mdp"


def _corto(dependencia: str) -> str:
    for prefijo in ("Secretaría de ", "Secretaría "):
        if dependencia.startswith(prefijo):
            return dependencia[len(prefijo):].capitalize()
    return dependencia


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    anio = int(datos["anio"].max())
    anio_prev = anio - 1
    actual = datos[datos["anio"] == anio]
    total = actual["ejercido_mdp"].sum()

    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[[{"type": "domain", "colspan": 2}, None], [{"type": "xy"}, {"type": "xy"}]],
        row_heights=[0.56, 0.44],
        column_widths=[0.52, 0.48],
        vertical_spacing=0.13,
        horizontal_spacing=0.2,
        subplot_titles=(
            f"Cómo se repartió el gasto ejercido en {anio}: {_mdp(total)}",
            f"Quién ejerce el desarrollo económico ({anio})",
            "Desarrollo económico por trimestre",
        ),
    )

    # 1. Sankey: total -> finalidades
    por_finalidad = actual.groupby("finalidad")["ejercido_mdp"].sum()
    finalidades = [f for f in ORDEN_FINALIDADES if f in por_finalidad.index]
    colores_nodo = [CENOTE]
    rotulos = []
    for f in finalidades:
        v = por_finalidad[f]
        parte = 100 * v / total
        detalle = f"{parte:.1f} de cada 100 pesos" if f == FINALIDAD_ECONOMICA else f"{parte:.1f} %"
        rotulos.append(f"<b>{ROTULO_FINALIDAD.get(f, f)}</b><br>{_mdp(v)} · {detalle}")
        colores_nodo.append(MONTE if f == FINALIDAD_ECONOMICA else CALIZA)

    # Posiciones fijas: los rótulos van a la derecha de cada nodo, fuera de los flujos.
    # Los nodos de finalidad se apilan de arriba abajo, con un hueco mínimo para que
    # los rótulos de dos líneas de los nodos chicos no se encimen.
    alto_util, hueco_min, alto_rotulo = 0.80, 0.05, 0.13
    alturas = [alto_util * por_finalidad[f] / total for f in finalidades]
    centros, cursor = [], 0.0
    for i, h in enumerate(alturas):
        if i:
            separacion = max(hueco_min, alto_rotulo - (alturas[i - 1] + h) / 2)
            cursor += separacion
        centros.append(cursor + h / 2)
        cursor += h
    desfase = (1 - cursor) / 2
    centros = [c + desfase for c in centros]
    x_final = 0.70
    nodo_x = [0.001] + [x_final] * len(finalidades)
    nodo_y = [0.5] + centros
    notas = ["Total del año"] + [NOTA_FINALIDAD.get(f, f) for f in finalidades]

    fig.add_trace(
        go.Sankey(
            arrangement="fixed",
            valueformat=",.0f",
            valuesuffix=" mdp",
            node=dict(
                label=[""] * (len(finalidades) + 1),
                x=nodo_x,
                y=nodo_y,
                color=colores_nodo,
                customdata=notas,
                hovertemplate="%{customdata}<br>%{value}<extra></extra>",
                pad=18,
                thickness=22,
                line=dict(color=FONDO, width=1),
            ),
            link=dict(
                source=[0] * len(finalidades),
                target=list(range(1, len(finalidades) + 1)),
                value=[por_finalidad[f] for f in finalidades],
                color=[
                    _rgba(MONTE, 0.55) if f == FINALIDAD_ECONOMICA else _rgba(CALIZA, 0.45)
                    for f in finalidades
                ],
                customdata=[100 * por_finalidad[f] / total for f in finalidades],
                hovertemplate="%{value}<br>%{customdata:.1f} % del total<extra></extra>",
            ),
            textfont=dict(color=TINTA, size=12),
        ),
        row=1,
        col=1,
    )

    dominio_y = fig.data[0].domain.y
    for rotulo, centro in zip(rotulos, centros):
        fig.add_annotation(
            text=rotulo,
            xref="paper",
            yref="paper",
            x=x_final + 0.035,
            y=dominio_y[1] - centro * (dominio_y[1] - dominio_y[0]),
            xanchor="left",
            yanchor="middle",
            align="left",
            showarrow=False,
            font=dict(size=12, color=TINTA),
        )

    # 2. Dependencias dentro de Desarrollo económico
    eco = actual[actual["finalidad"] == FINALIDAD_ECONOMICA]
    por_dep = eco.groupby("dependencia")["ejercido_mdp"].sum().sort_values(ascending=False)
    principales = por_dep[por_dep > 0].head(MAX_DEPENDENCIAS)
    resto = por_dep.drop(principales.index).sum()
    nombres = [_corto(d) for d in principales.index]
    completos = list(principales.index)
    valores = list(principales.values)
    if abs(resto) >= 0.005:
        nombres.append("Otras dependencias")
        completos.append("Otras dependencias")
        valores.append(resto)
    eco_total = por_dep.sum()

    fig.add_trace(
        go.Bar(
            x=valores[::-1],
            y=nombres[::-1],
            orientation="h",
            marker=dict(color=MONTE, line=dict(color=FONDO, width=1)),
            text=[f"{v:,.0f}" for v in valores[::-1]],
            textposition="outside",
            textfont=dict(color=TINTA, size=11),
            cliponaxis=False,
            customdata=[[c, 100 * v / eco_total] for c, v in zip(completos[::-1], valores[::-1])],
            hovertemplate="%{customdata[0]}<br>%{x:,.1f} mdp"
            "<br>%{customdata[1]:.1f} % del desarrollo económico<extra></extra>",
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    # 3. Desarrollo económico por trimestre, año anterior contra actual
    tot_trim = datos.groupby(["anio", "trimestre"])["ejercido_mdp"].sum()
    eco_trim = (
        datos[datos["finalidad"] == FINALIDAD_ECONOMICA]
        .groupby(["anio", "trimestre"])["ejercido_mdp"]
        .sum()
    )
    for a, color in ((anio_prev, CALIZA_OSCURA), (anio, MONTE)):
        if a not in eco_trim.index.get_level_values(0):
            continue
        serie = eco_trim.loc[a].sort_index()
        partes = [100 * serie[t] / tot_trim.loc[(a, t)] for t in serie.index]
        fig.add_trace(
            go.Bar(
                name=str(a),
                x=[f"{t}T" for t in serie.index],
                y=serie.values,
                marker=dict(color=color, line=dict(color=FONDO, width=2)),
                text=[f"{p:.1f} %" for p in partes],
                textposition="outside",
                textfont=dict(color=TINTA_SUAVE, size=10),
                cliponaxis=False,
                customdata=partes,
                hovertemplate=f"{a} · %{{x}}<br>%{{y:,.1f}} mdp"
                "<br>%{customdata:.1f} % del gasto del trimestre<extra></extra>",
            ),
            row=2,
            col=2,
        )

    fig.update_xaxes(
        row=2, col=1, showgrid=True, gridcolor=REJILLA, zeroline=False,
        title_text="millones de pesos", title_font=dict(size=11, color=TINTA_SUAVE),
        tickfont=dict(color=TINTA_SUAVE, size=10), tickformat=",.0f", rangemode="tozero",
        domain=[0.22, 0.5],
    )
    fig.update_yaxes(row=2, col=1, tickfont=dict(color=TINTA, size=11), ticksuffix="  ")
    fig.update_xaxes(row=2, col=2, tickfont=dict(color=TINTA, size=11))
    fig.update_yaxes(
        row=2, col=2, showgrid=True, gridcolor=REJILLA, zeroline=False,
        title_text="millones de pesos", title_font=dict(size=11, color=TINTA_SUAVE),
        tickfont=dict(color=TINTA_SUAVE, size=10), tickformat=",.0f", rangemode="tozero",
    )

    # Títulos de panel alineados a la izquierda de cada panel.
    for anotacion, x in zip(fig.layout.annotations, (0, 0, fig.layout.xaxis2.domain[0] - 0.06)):
        anotacion.update(x=x, xanchor="left", font=dict(size=13, color=TINTA))

    fig.update_layout(
        title=dict(text=TITULO, x=0, xanchor="left", font=dict(size=17, color=TINTA)),
        font=dict(family="Open Sans, Verdana, Arial, sans-serif", color=TINTA),
        paper_bgcolor=FONDO,
        plot_bgcolor=FONDO,
        barmode="group",
        bargap=0.3,
        bargroupgap=0.08,
        legend=dict(
            orientation="h",
            x=1,
            xanchor="right",
            y=fig.layout.yaxis2.domain[1] + 0.045,
            yanchor="bottom",
            font=dict(size=11, color=TINTA),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=20, r=40, t=80, b=40),
        hoverlabel=dict(bgcolor=FONDO, font=dict(color=TINTA)),
        height=860,
    )
    return fig
