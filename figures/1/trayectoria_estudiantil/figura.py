"""Trayectoria estudiantil: matrícula, composición por programa y egreso.

viz_id: 1.trayectoria_estudiantil

Columnas de `datos`: tipo, categoria, valor, periodo. Valores admitidos en tipo:
matricula_programa, matricula_total, sexo, egresados.
Los valores predeterminados provienen de Data México (2022) y de la Gaceta
SIIDETEY/SIIES (matrícula reportada durante 2023).
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_DATOS_BASE = [
    {"tipo": "matricula_programa", "categoria": "Robótica Computacional", "valor": 241, "periodo": "2022"},
    {"tipo": "matricula_programa", "categoria": "Ingeniería en Datos", "valor": 142, "periodo": "2022"},
    {"tipo": "matricula_programa", "categoria": "Sistemas Embebidos Computacionales", "valor": 98, "periodo": "2022"},
    {"tipo": "matricula_total", "categoria": "2022", "valor": 481, "periodo": "Data México"},
    {"tipo": "matricula_total", "categoria": "2023", "valor": 530, "periodo": "Gaceta SIIDETEY"},
    {"tipo": "sexo", "categoria": "Hombres", "valor": 389, "periodo": "2022"},
    {"tipo": "sexo", "categoria": "Mujeres", "valor": 92, "periodo": "2022"},
    {"tipo": "egresados", "categoria": "Egresados", "valor": 62, "periodo": "2022"},
]


def figura(datos=None) -> go.Figure:
    """Construye una figura con los datos de matrícula y egreso disponibles."""
    if datos is None or (hasattr(datos, "empty") and datos.empty):
        df = pd.DataFrame(_DATOS_BASE)
    else:
        df = datos.copy() if hasattr(datos, "copy") else pd.DataFrame(datos)
        requeridas = {"tipo", "categoria", "valor", "periodo"}
        faltantes = requeridas.difference(df.columns)
        if faltantes:
            raise ValueError(f"A datos le faltan columnas: {', '.join(sorted(faltantes))}")

    programas = df[df["tipo"] == "matricula_programa"].copy()
    totales = df[df["tipo"] == "matricula_total"].copy()
    sexos = df[df["tipo"] == "sexo"].copy()
    egresados = df[df["tipo"] == "egresados"]

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=("Matrícula por programa (2022)", "Registros de matrícula", "Composición por sexo (2022)"),
        specs=[[{"type": "xy"}, {"type": "xy"}, {"type": "domain"}]],
        column_widths=[0.39, 0.30, 0.31], horizontal_spacing=0.11,
    )
    programas = programas.sort_values("valor")
    fig.add_trace(go.Bar(
        x=programas["valor"], y=programas["categoria"], orientation="h",
        marker_color="#6D28D9", text=programas["valor"], textposition="outside",
        hovertemplate="%{y}: %{x} estudiantes<extra></extra>", name="Matrícula por programa",
    ), row=1, col=1)
    totales = totales.sort_values("categoria")
    fig.add_trace(go.Bar(
        x=totales["categoria"], y=totales["valor"],
        marker_color=["#0F766E", "#14B8A6"], text=totales["valor"], textposition="outside",
        customdata=totales["periodo"],
        hovertemplate="%{x}: %{y} estudiantes<br>Fuente: %{customdata}<extra></extra>",
        name="Matrícula reportada",
    ), row=1, col=2)
    if not sexos.empty:
        fig.add_trace(go.Pie(
            labels=sexos["categoria"], values=sexos["valor"], hole=0.58,
            marker=dict(colors=["#6D28D9", "#F59E0B"]),
            textinfo="label+percent", hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
            showlegend=False,
        ), row=1, col=3)
    total_egresados = int(egresados["valor"].iloc[0]) if not egresados.empty else 62
    fig.add_annotation(x=0.84, y=0.5, xref="paper", yref="paper", showarrow=False,
                       text=f"<b>{total_egresados}</b><br>egresados reportados<br>en 2022",
                       font=dict(size=14, color="#334155"), align="center")
    fig.update_layout(
        title=dict(text="Trayectoria estudiantil en la UPY: matrícula y egreso", x=0.02),
        template="plotly_white", height=500, margin=dict(l=30, r=35, t=105, b=105),
        showlegend=False,
        annotations=list(fig.layout.annotations) + [dict(
            x=0.01, y=-0.23, xref="paper", yref="paper", showarrow=False,
            text="Comparación contextual: 481 corresponde a matrícula 2022 de Data México; 530 es la matrícula reportada como actual en la Gaceta SIIDETEY de 2023. No es una serie anual homogénea.",
            font=dict(size=10, color="#475569"), align="left",
        )],
    )
    fig.update_xaxes(title_text="Estudiantes", row=1, col=1, showgrid=True, gridcolor="#E2E8F0")
    fig.update_yaxes(title_text="", row=1, col=1)
    fig.update_yaxes(title_text="Estudiantes", row=1, col=2, showgrid=True, gridcolor="#E2E8F0")
    return fig
