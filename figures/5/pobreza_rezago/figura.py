"""Pobreza y rezago
viz_id: 5.pobreza_rezago

Semillas con raíces (boceto del equipo): cada municipio es un punto cuya raíz
llega hasta el suelo (0 %). Control de año 2010 - 2015 - 2020.

Tabla de oro (`datos`), formato largo, una fila por municipio y año:
    municipio     nombre del municipio
    anio          2010, 2015 o 2020
    irs           Índice de Rezago Social (valor numérico, CONEVAL)
    pobreza_pct   porcentaje de población en pobreza (CONEVAL)
    grado_rezago  "Muy bajo", "Bajo", "Medio", "Alto" o "Muy alto"

La plantilla muestra fuentes, fecha y responsable; no van dentro de la figura.
"""
import pandas as pd
import plotly.graph_objects as go

TITULO = "Pobreza y rezago"
CALIZA, TEXTO, TEXTO_2 = "#f7f4ec", "#1d2a22", "#4f5b52"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"
REJILLA = "#e3dfd2"
ORDEN = ["Muy bajo", "Bajo", "Medio", "Alto", "Muy alto"]
COLORES = {"Muy bajo": "#1d9e75", "Bajo": "#8fcf9f", "Medio": "#f2c14e",
           "Alto": "#e8833a", "Muy alto": "#c0392b"}


def _base() -> dict:
    return dict(
        title=dict(text=TITULO, x=0, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=22, color=TEXTO), pad=dict(l=10)),
        width=1100, height=720, paper_bgcolor=CALIZA, plot_bgcolor=CALIZA,
        font=dict(family=LETRA, size=14, color=TEXTO),
        margin=dict(l=80, r=60, t=80, b=120),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13)),
    )


def _trazas(d):
    xs, ys = [], []
    for _, r in d.iterrows():
        xs += [r["irs"], r["irs"], None]
        ys += [0, r["pobreza_pct"], None]
    raices = go.Scatter(x=xs, y=ys, mode="lines", showlegend=False, hoverinfo="skip",
                        line=dict(color=TEXTO_2, width=1))
    semillas = go.Scatter(
        x=d["irs"], y=d["pobreza_pct"], mode="markers", showlegend=False,
        marker=dict(size=11, line=dict(width=0.8, color=TEXTO),
                    color=[COLORES.get(g, "#999999") for g in d["grado_rezago"]]),
        text=d["municipio"], customdata=d["grado_rezago"],
        hovertemplate="<b>%{text}</b><br>Rezago %{customdata} (IRS %{x:.2f})"
                      "<br>Pobreza %{y:.1f}%<extra></extra>",
    )
    return [raices, semillas]


def _notas(d):
    """Recuadro del municipio con más pobreza, más 'semilla' y 'raíz' como en el boceto."""
    d = d.reset_index(drop=True)
    r = d.loc[d["pobreza_pct"].idxmax()]
    med = d.iloc[(d["pobreza_pct"] - d["pobreza_pct"].median()).abs().values.argmin()]
    estilo = dict(showarrow=True, arrowhead=2, arrowwidth=1.2, arrowcolor=TEXTO_2,
                  font=dict(size=13, color=TEXTO))
    return [
        dict(x=r["irs"], y=r["pobreza_pct"], ax=-100, ay=20, align="left",
             text=(f"<b>{r['municipio']}</b><br>Pobreza: {r['pobreza_pct']:.1f}%"
                   f"<br>IRS: {r['grado_rezago']}"),
             bgcolor="white", bordercolor=TEXTO, **estilo),
        dict(x=med["irs"], y=med["pobreza_pct"], ax=-50, ay=-40, text="<i>semilla</i>", **estilo),
        dict(x=r["irs"], y=r["pobreza_pct"] / 2, ax=60, ay=0, text="<i>raíz</i>", **estilo),
    ]


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(**_base())
    if datos is None or len(datos) == 0:
        return fig
    d = datos.copy()
    for c in ["anio", "irs", "pobreza_pct"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["anio", "irs", "pobreza_pct"])
    if d.empty:
        return fig
    anios = sorted(d["anio"].unique())
    por_anio = {a: d[d["anio"] == a] for a in anios}
    ultimo = anios[-1]
    for t in _trazas(por_anio[ultimo]):
        fig.add_trace(t)
    for g in ORDEN:  # entradas de leyenda
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=g,
                                 marker=dict(size=11, color=COLORES[g])))
    fig.frames = [go.Frame(name=str(int(a)), data=_trazas(por_anio[a]), traces=[0, 1],
                           layout=dict(annotations=_notas(por_anio[a])))
                  for a in anios]
    fig.update_layout(
        annotations=_notas(por_anio[ultimo]),
        legend=dict(title=dict(text="Rezago social")),
        sliders=[dict(
            active=len(anios) - 1, pad=dict(t=40),
            currentvalue=dict(prefix="Año: ", font=dict(size=15, color=TEXTO)),
            steps=[dict(label=str(int(a)), method="animate",
                        args=[[str(int(a))], dict(mode="immediate",
                                                  frame=dict(duration=300, redraw=True),
                                                  transition=dict(duration=0))])
                   for a in anios])],
    )
    fig.update_xaxes(title="Índice de Rezago Social (IRS)", showline=True, linecolor=TEXTO,
                     ticks="outside", gridcolor=REJILLA, zeroline=False)
    fig.update_yaxes(title="Población en pobreza (%)", range=[0, 105], showline=True,
                     linecolor=TEXTO, ticks="outside", gridcolor=REJILLA, zeroline=False)
    return fig
