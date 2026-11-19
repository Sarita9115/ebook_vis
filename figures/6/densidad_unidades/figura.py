"""Distribución y densidad nacional de unidades económicas

viz_id: 6.densidad_unidades
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Distribución y densidad nacional de unidades económicas")
    return fig
