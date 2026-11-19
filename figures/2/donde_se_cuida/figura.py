"""Dónde se cuida la península

viz_id: 2.donde_se_cuida
"""

import plotly.graph_objects as go


def figura(datos) -> go.Figure:
    """Construye la figura de Plotly a partir de la tabla de oro."""
    fig = go.Figure()
    fig.update_layout(title="Dónde se cuida la península")
    return fig
