"""Herbario CICY, plantas vasculares

viz_id: 2.herbario_cicy
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Herbario CICY, plantas vasculares")
    return fig
