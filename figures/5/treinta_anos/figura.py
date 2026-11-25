"""Treinta años aprendiendo
viz_id: 5.treinta_anos

Línea de Yucatán, 1990-2025, con el valor y el nivel escolar de cada punto
(boceto del equipo). Líneas de referencia punteadas marcan cuántos años
corresponden a cada nivel, hasta la licenciatura.

Tabla de oro (`datos`), formato largo:
    anio            año (1990 viene del Censo 1990)
    entidad         "Yucatán" (si vienen otras, se ignoran)
    sexo            "Total" (si vienen otros, se ignoran)
    grado_promedio  años de escolaridad, población de 15 años y más

Convención del equipo (no es una clasificación de INEGI): el dato es el
promedio de años de toda la población de 15 años y más. Se toma un nivel como
completo en su hito (6 primaria, 9 secundaria, 12 prepa, 16 licenciatura) y
hasta medio año después; si el promedio pasa de ahí, ya empezó el siguiente
nivel y se etiqueta como "trunca" o "incompleta".

La plantilla muestra fuentes, fecha y responsable; no van dentro de la figura.
"""
import pandas as pd
import plotly.graph_objects as go

TITULO = "Treinta años aprendiendo"
CALIZA, TEXTO, TEXTO_2 = "#f7f4ec", "#1d2a22", "#4f5b52"
LETRA = "Source Sans 3, Helvetica Neue, Helvetica, Arial, sans-serif"
REJILLA = "#e3dfd2"

# (años del hito, nombre del nivel completado)
HITOS = [(6, "Primaria completa"), (9, "Secundaria completa"),
         (12, "Prepa completa"), (16, "Licenciatura completa")]
MEDIO = 0.5  # holgura (años) para seguir llamando "completo" a un nivel


def _nivel(x) -> str:
    """Etiqueta del nivel según el grado promedio."""
    if x < 6:
        return "Primaria<br>incompleta"
    if x < 6 + MEDIO:
        return "Primaria<br>completa"
    if x < 9:
        return "Secundaria<br>incompleta"
    if x < 9 + MEDIO:
        return "Secundaria<br>completa"
    if x < 12:
        return "Prepa<br>trunca"
    if x < 12 + MEDIO:
        return "Prepa<br>completa"
    if x < 16:
        return "Licenciatura<br>trunca"
    return "Licenciatura<br>completa"


def _base() -> dict:
    return dict(
        title=dict(text=TITULO, x=0, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=22, color=TEXTO), pad=dict(l=10)),
        width=1100, height=720, paper_bgcolor=CALIZA, plot_bgcolor=CALIZA,
        font=dict(family=LETRA, size=14, color=TEXTO),
        margin=dict(l=80, r=150, t=80, b=70),
        hoverlabel=dict(bgcolor="white", font=dict(family=LETRA, color=TEXTO, size=13)),
    )


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(**_base())
    if datos is None or len(datos) == 0:
        return fig
    d = datos.copy()
    d["anio"] = pd.to_numeric(d["anio"], errors="coerce")
    d["grado_promedio"] = pd.to_numeric(d["grado_promedio"], errors="coerce")
    d = d[(d["entidad"] == "Yucatán") & (d["sexo"] == "Total")]
    d = d.dropna(subset=["anio", "grado_promedio"]).sort_values("anio")
    if d.empty:
        return fig

    # Referencias: cuántos años de escuela son cada nivel (fuera del área, a la derecha).
    for anios, nombre in HITOS:
        fig.add_hline(y=anios, line_dash="dot", line_width=1, line_color=TEXTO_2)
        fig.add_annotation(xref="paper", x=1.01, yref="y", y=anios, text=f"{anios} años<br>{nombre}",
                           showarrow=False, xanchor="left", font=dict(size=12, color=TEXTO_2))

    fig.add_trace(go.Scatter(
        x=d["anio"], y=d["grado_promedio"], mode="lines+markers+text",
        line=dict(color=TEXTO, width=3), marker=dict(size=11, color=TEXTO),
        text=[f"<b>{v:.1f}</b><br>{_nivel(v)}" for v in d["grado_promedio"]],
        textposition="top center", cliponaxis=False, showlegend=False,
        textfont=dict(size=13, color=TEXTO),
        hovertemplate="%{x:.0f}: %{y:.1f} años de escuela<extra></extra>",
    ))
    # Flecha hacia la licenciatura: no es una proyección, solo lo que falta (16 - último dato).
    ult = d.iloc[-1]
    meta = HITOS[-1][0]
    if ult["grado_promedio"] < meta:
        x_fin = ult["anio"] + 2.5
        fig.add_annotation(x=x_fin, y=meta, ax=ult["anio"], ay=ult["grado_promedio"],
                           xref="x", yref="y", axref="x", ayref="y", text="",
                           showarrow=True, arrowhead=2, arrowwidth=2.5, arrowcolor=TEXTO_2)
        fig.add_annotation(x=ult["anio"] - 1.5, y=(ult["grado_promedio"] + meta) / 2 + 1,
                           xref="x", yref="y", xanchor="right", showarrow=False, align="right",
                           text=f"<b>Faltan {meta - ult['grado_promedio']:.1f} años</b><br>"
                                f"para licenciatura completa",
                           font=dict(size=14, color=TEXTO))
    fig.update_xaxes(title="Años", tickmode="array", tickvals=list(d["anio"]),
                     range=[1987, 2031], showline=True, linecolor=TEXTO, ticks="outside",
                     showgrid=False, tickformat="d")
    fig.update_yaxes(title="Grado de escolaridad (años)", range=[0, 17.5],
                     tickvals=list(range(0, 18, 2)), showline=True, linecolor=TEXTO,
                     ticks="outside", gridcolor=REJILLA, zeroline=False)
    return fig
