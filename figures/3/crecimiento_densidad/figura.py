"""Crecimiento poblacional y densidad territorial

viz_id: 3.crecimiento_densidad
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Crecimiento poblacional y densidad territorial")
    return fig
