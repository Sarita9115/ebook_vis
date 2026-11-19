"""Efecto económico de la apertura al exterior

viz_id: 4.apertura_exterior
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Efecto económico de la apertura al exterior")
    return fig
