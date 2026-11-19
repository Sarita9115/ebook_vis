"""Aporte del sector empresarial al PIB estatal y regional

viz_id: 6.aporte_pib
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Aporte del sector empresarial al PIB estatal y regional")
    return fig
