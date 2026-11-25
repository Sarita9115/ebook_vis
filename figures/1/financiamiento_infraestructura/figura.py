"""Financiamiento e infraestructura: flujos trimestrales y activos registrados.

viz_id: 1.financiamiento_infraestructura

Columnas de `datos`: tipo, concepto, periodo, valor. Valores de tipo:
flujo (comparativo enero-marzo 2025/2026) y activo (saldo al 31-mar-2026).
Los datos base proceden del reporte contable oficial de la UPY del primer
trimestre de 2026, que incluye cifras comparativas de 2025.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_DATOS_BASE = [
    {"tipo": "flujo", "concepto": "Ingresos de gestión", "periodo": "1T 2025", "valor": 6682191.46},
    {"tipo": "flujo", "concepto": "Ingresos de gestión", "periodo": "1T 2026", "valor": 1017270.25},
    {"tipo": "flujo", "concepto": "Transferencias y subsidios", "periodo": "1T 2025", "valor": 25828042.86},
    {"tipo": "flujo", "concepto": "Transferencias y subsidios", "periodo": "1T 2026", "valor": 4159677.00},
    {"tipo": "flujo", "concepto": "Gastos de funcionamiento", "periodo": "1T 2025", "valor": 35090992.38},
    {"tipo": "flujo", "concepto": "Gastos de funcionamiento", "periodo": "1T 2026", "valor": 6888099.67},
    {"tipo": "flujo", "concepto": "Gastos totales", "periodo": "1T 2025", "valor": 52524695.18},
    {"tipo": "flujo", "concepto": "Gastos totales", "periodo": "1T 2026", "valor": 10151311.39},
    {"tipo": "activo", "concepto": "Bienes inmuebles e infraestructura", "periodo": "31-mar-2026", "valor": 115042865.47},
    {"tipo": "activo", "concepto": "Bienes muebles", "periodo": "31-mar-2026", "valor": 79113504.48},
    {"tipo": "activo", "concepto": "Activos intangibles", "periodo": "31-mar-2026", "valor": 16830421.25},
    {"tipo": "activo", "concepto": "Depreciación acumulada", "periodo": "31-mar-2026", "valor": -101199132.08},
]


def figura(datos=None) -> go.Figure:
    """Devuelve una comparación financiera trimestral y un corte de activos."""
    if datos is None or (hasattr(datos, "empty") and datos.empty):
        df = pd.DataFrame(_DATOS_BASE)
    else:
        df = datos.copy() if hasattr(datos, "copy") else pd.DataFrame(datos)
        requeridas = {"tipo", "concepto", "periodo", "valor"}
        faltantes = requeridas.difference(df.columns)
        if faltantes:
            raise ValueError(f"A datos le faltan columnas: {', '.join(sorted(faltantes))}")

    flujos = df[df["tipo"] == "flujo"]
    activos = df[df["tipo"] == "activo"]
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Flujos del primer trimestre (millones de pesos)", "Saldos de activos al 31 de marzo de 2026 (millones de pesos)"),
        specs=[[{"type": "xy"}, {"type": "xy"}]],
        column_widths=[0.56, 0.44], horizontal_spacing=0.15,
    )
    for periodo, color in [("1T 2025", "#94A3B8"), ("1T 2026", "#6D28D9")]:
        parte = flujos[flujos["periodo"] == periodo]
        fig.add_trace(go.Bar(
            name=periodo, x=parte["concepto"], y=parte["valor"] / 1_000_000,
            marker_color=color, text=(parte["valor"] / 1_000_000).round(2),
            texttemplate="%{text:.2f}", textposition="outside",
            hovertemplate="%{x}<br>%{y:.2f} millones de pesos<extra>" + periodo + "</extra>",
        ), row=1, col=1)
    activos = activos.sort_values("valor")
    fig.add_trace(go.Bar(
        x=activos["valor"] / 1_000_000, y=activos["concepto"], orientation="h",
        marker_color=["#D97706" if v < 0 else "#0F766E" for v in activos["valor"]],
        text=(activos["valor"] / 1_000_000).round(2), texttemplate="%{text:.2f}",
        textposition="outside",
        hovertemplate="%{y}<br>%{x:.2f} millones de pesos<extra></extra>",
        showlegend=False,
    ), row=1, col=2)
    fig.update_layout(
        title=dict(text="Financiamiento e infraestructura de la UPY", x=0.02),
        template="plotly_white", height=570, barmode="group",
        margin=dict(l=35, r=35, t=105, b=150), legend=dict(orientation="h", y=1.08, x=0.02),
        annotations=list(fig.layout.annotations) + [dict(
            x=0.01, y=-0.31, xref="paper", yref="paper", showarrow=False,
            text="Los flujos comparan enero-marzo de cada año; no son presupuestos anuales autorizados. Los activos son saldos contables, no inversión ejercida en el trimestre. En el flujo de inversión se reportaron $0 en 1T 2026 y $317,993.26 en 1T 2025 para bienes muebles.",
            font=dict(size=10, color="#475569"), align="left",
        )],
    )
    fig.update_yaxes(title_text="Millones de pesos", row=1, col=1, showgrid=True, gridcolor="#E2E8F0")
    fig.update_xaxes(title_text="Millones de pesos", row=1, col=2, showgrid=True, gridcolor="#E2E8F0")
    return fig
